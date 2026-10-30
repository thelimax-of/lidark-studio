"""Worker de geração de imagem LOCAL (GPU) — roda no venv isolado data/imggen/venv, NÃO no servidor.

    data/imggen/venv/Scripts/python.exe backend/lidark/story/gpu_worker.py --port 8770 --idle 240

Contrato HTTP (127.0.0.1 apenas):
    GET  /capacity  → {"ok", "model", "loaded", "images_per_hour", "secs_per_image", "queue", "busy"}
    POST /generate  json {prompt, negative, width, height, seed, kind, model?, steps?,
                          init_image? (PNG base64), strength?}  → image/png
    POST /shutdown  → encerra (libera VRAM/RAM)
Modelos: "sd15_lcm" (DreamShaper-8 + LCM LoRA, 6 passos, ~3 s/img em 512x896, 3,2 GB VRAM)
         "sdxl_lightning" (SDXL base + SDXL-Lightning 4 passos, cpu offload — só se couber na RAM)
Só um modelo carregado por vez. Trava de GPU: data/story/gpu.lock (mesmo protocolo de lidark/story/gpu.py) durante
cada geração — o render espera. Sai sozinho depois de --idle segundos sem pedido (RAM é curta no notebook).
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = Path(os.environ.get("LIDARK_DATA", ROOT / "data"))
os.environ.setdefault("HF_HOME", str(DATA / "imggen" / "hf"))
LOCK = DATA / "story" / "gpu.lock"
OWNER = DATA / "story" / "gpu.owner"

STATE = {"model": None, "pipe": None, "img2img": None, "name": "", "last": time.time(), "busy": False, "queue": 0,
         "secs": {}, "count": 0}
GEN_LOCK = threading.Lock()


# ---------------------------------------------------------------- trava de GPU entre processos
_CLIP: dict = {}
_PEOPLE_TXT = ["an illustration of a person", "an illustration of a human face",
               "a picture of an empty place with no people", "a close-up of an object with no people"]


def people_score(b64: str) -> float:
    """Probabilidade (0-1) de haver pessoa/rosto na imagem — CLIP ViT-B/32 em data/imggen/models/clip (~0,3 GB de VRAM)."""
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor
    if not _CLIP:
        d = Path(__file__).resolve().parents[3] / "data" / "imggen" / "models" / "clip"
        _CLIP["m"] = CLIPModel.from_pretrained(str(d), torch_dtype=torch.float16).to("cuda").eval()
        _CLIP["p"] = CLIPProcessor.from_pretrained(str(d))
    img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
    x = _CLIP["p"](text=_PEOPLE_TXT, images=img, return_tensors="pt", padding=True).to("cuda")
    with torch.no_grad():
        pr = _CLIP["m"](**{k: (v.half() if v.dtype == torch.float32 else v) for k, v in x.items()}).logits_per_image.softmax(-1)[0]
    return round(float(pr[0] + pr[1]), 3)


class GpuLock:
    def __enter__(self):
        import msvcrt
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        self.fd = os.open(str(LOCK), os.O_RDWR | os.O_CREAT)
        t0 = time.time()
        while True:
            try:
                os.lseek(self.fd, 0, 0)
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                self.got = True
                break
            except OSError:
                if time.time() - t0 > 1800:
                    self.got = False
                    break
                time.sleep(0.5)
        if self.got:
            OWNER.write_text(json.dumps({"owner": "image-local", "pid": os.getpid(), "since": time.time()}), encoding="utf-8")
        return self

    def __exit__(self, *a):
        import msvcrt
        if self.got:
            try:
                OWNER.unlink()
            except OSError:
                pass
            os.lseek(self.fd, 0, 0)
            msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
        os.close(self.fd)


# ---------------------------------------------------------------- modelos
def _unload():
    import gc
    import torch
    STATE.update(pipe=None, img2img=None, model=None)
    gc.collect()
    torch.cuda.empty_cache()


def load(name: str):
    import torch
    if STATE["model"] == name:
        return
    _unload()
    t = time.time()
    if name == "sdxl_lightning":
        from diffusers import EulerDiscreteScheduler, StableDiffusionXLImg2ImgPipeline, StableDiffusionXLPipeline
        # pesos baixados direto (curl) em data/imggen/models — o download do hub pelo Python era lento demais
        models = Path(__file__).resolve().parents[3] / "data" / "imggen" / "models"
        pipe = StableDiffusionXLPipeline.from_pretrained(str(models / "sdxl-base"), torch_dtype=torch.float16,
                                                         variant="fp16", local_files_only=True)
        pipe.load_lora_weights(str(models / "lightning" / "sdxl_lightning_4step_lora.safetensors"))
        pipe.fuse_lora()
        pipe.unload_lora_weights()
        pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config, timestep_spacing="trailing")
        # tudo na GPU (sem offload para a RAM): UNet e text encoders guardados em FP8 (calculam em FP16) e o VAE
        # "fp16-fix" (sem upcast fp32). Medido na RTX 3050 6 GB: 3,5 GB carregado, pico 4,05 GB, ~5 s por 768x1344.
        from diffusers import AutoencoderKL
        from diffusers.hooks import apply_layerwise_casting
        pipe.unet.enable_layerwise_casting(storage_dtype=torch.float8_e4m3fn, compute_dtype=torch.float16)
        for te in (pipe.text_encoder_2, pipe.text_encoder):
            apply_layerwise_casting(te, storage_dtype=torch.float8_e4m3fn, compute_dtype=torch.float16,
                                    skip_modules_pattern=("embed", "norm", "position"))
        pipe.vae = AutoencoderKL.from_pretrained(str(models / "vae-fp16-fix"), torch_dtype=torch.float16)
        pipe.vae.config.force_upcast = False
        pipe.to("cuda")
        pipe.vae.enable_tiling()
        i2i = StableDiffusionXLImg2ImgPipeline(**pipe.components)
        STATE.update(native=(768, 1344), steps=4, cfg=1.0)
    else:
        from diffusers import LCMScheduler, StableDiffusionImg2ImgPipeline, StableDiffusionPipeline
        pipe = StableDiffusionPipeline.from_pretrained("Lykon/dreamshaper-8", torch_dtype=torch.float16, variant="fp16",
                                                       safety_checker=None, local_files_only=True).to("cuda")
        pipe.scheduler = LCMScheduler.from_config(pipe.scheduler.config)
        pipe.load_lora_weights("latent-consistency/lcm-lora-sdv1-5")
        pipe.fuse_lora()
        i2i = StableDiffusionImg2ImgPipeline(**pipe.components)
        STATE.update(native=(512, 896), steps=6, cfg=1.5)
    STATE.update(model=name, pipe=pipe, img2img=i2i)
    print(f"[worker] {name} carregado em {time.time() - t:.0f}s", flush=True)


def _native(w: int, h: int) -> tuple[int, int]:
    """Tamanho nativo do modelo com a mesma proporção (múltiplo de 8/64)."""
    nw, nh = STATE["native"]
    area = nw * nh
    ar = w / h
    gw = int((area * ar) ** 0.5)
    gh = int(gw / ar)
    m = 64 if STATE["model"] == "sdxl_lightning" else 8
    return max(m, gw // m * m), max(m, gh // m * m)


def generate(req: dict):
    import torch
    from PIL import Image
    name = req.get("model") or ARGS.model
    load(name)
    w, h = int(req.get("width") or 720), int(req.get("height") or 1280)
    gw, gh = _native(w, h)
    steps = int(req.get("steps") or STATE["steps"])
    cfg = STATE["cfg"]
    g = torch.Generator("cuda").manual_seed(int(req.get("seed") or 1) % (2 ** 31 - 1))
    neg = req.get("negative") if cfg > 1 else None
    t = time.time()
    with GpuLock():
        if req.get("init_image"):
            init = Image.open(io.BytesIO(base64.b64decode(req["init_image"]))).convert("RGB").resize((gw, gh), Image.LANCZOS)
            strength = float(req.get("strength") or 0.5)
            n = max(steps, int(round(steps / max(0.2, strength))))  # passos efetivos ≈ steps
            img = STATE["img2img"](req["prompt"], negative_prompt=neg, image=init, strength=strength, num_inference_steps=n,
                                   guidance_scale=cfg, generator=g).images[0]
        else:
            img = STATE["pipe"](req["prompt"], negative_prompt=neg, width=gw, height=gh, num_inference_steps=steps,
                                guidance_scale=cfg, generator=g).images[0]
        torch.cuda.synchronize()
    dt = time.time() - t
    STATE["secs"].setdefault(name, []).append(dt)
    STATE["secs"][name] = STATE["secs"][name][-20:]
    STATE["count"] += 1
    if (gw, gh) != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue(), dt


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code: int, obj: dict):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        STATE["last"] = time.time()
        if self.path.startswith("/capacity"):
            sec = STATE["secs"].get(STATE["model"] or ARGS.model) or []
            spi = sum(sec) / len(sec) if sec else {"sd15_lcm": 3.5, "sdxl_lightning": 25.0}.get(ARGS.model, 10.0)
            return self._json(200, {"ok": True, "model": STATE["model"] or ARGS.model, "loaded": bool(STATE["model"]),
                                    "secs_per_image": round(spi, 1), "images_per_hour": int(3600 / max(1.0, spi) * 0.8),
                                    "queue": STATE["queue"], "busy": STATE["busy"], "generated": STATE["count"]})
        self._json(404, {"error": "?"})

    def do_POST(self):
        STATE["last"] = time.time()
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path.startswith("/shutdown"):
            self._json(200, {"ok": True})
            threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)), daemon=True).start()
            return
        if self.path.startswith("/people"):  # cenário/objeto tem gente? (CLIP, entende ilustração)
            try:
                with GEN_LOCK:
                    return self._json(200, {"person": people_score(body["image"])})
            except Exception as e:  # noqa: BLE001
                return self._json(500, {"error": str(e)[:300]})
        if not self.path.startswith("/generate"):
            return self._json(404, {"error": "?"})
        STATE["queue"] += 1
        try:
            with GEN_LOCK:
                STATE["busy"] = True
                png, dt = generate(body)
        except Exception as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            return self._json(500, {"error": str(e)[:500]})
        finally:
            STATE["queue"] -= 1
            STATE["busy"] = False
            STATE["last"] = time.time()
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("X-Seconds", f"{dt:.2f}")
        self.send_header("Content-Length", str(len(png)))
        self.end_headers()
        self.wfile.write(png)


def idle_watch():
    while True:
        time.sleep(10)
        if not STATE["busy"] and STATE["queue"] == 0 and time.time() - STATE["last"] > ARGS.idle:
            print("[worker] ocioso — saindo para liberar a GPU/RAM", flush=True)
            os._exit(0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8770)
    ap.add_argument("--model", default="sd15_lcm")
    ap.add_argument("--idle", type=int, default=240)
    ARGS = ap.parse_args()
    threading.Thread(target=idle_watch, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", ARGS.port), H)
    print(f"[worker] ouvindo em 127.0.0.1:{ARGS.port} (modelo padrão {ARGS.model})", flush=True)
    sys.stdout.flush()
    srv.serve_forever()
