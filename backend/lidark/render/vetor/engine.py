"""Motor vetorial: desenha cada quadro em SVG no Edge (sem GPU e sem geração de imagem) e entrega o vídeo.

O Playwright roda em processos à parte: isola o laço de eventos do servidor e divide o vídeo em trechos paralelos.
Como cada quadro é função pura de t, os trechos são independentes; no fim viram um arquivo só, com o áudio.
Cada trabalhador é este mesmo arquivo: `python engine.py --worker job.json`.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
JPEG_Q = 96
MAX_WORKERS = 4  # medido: acima de 4 o Edge disputa CPU e fica mais lento


def _prepare(page: Any, spec_path: str) -> None:
    page.set_viewport_size({"width": 720, "height": 1280})
    page.goto((HERE / "page.html").as_uri())
    page.evaluate("s=>V.load(s)", json.loads(Path(spec_path).read_text(encoding="utf-8")))


def _shot(cdp: Any) -> bytes:
    """Captura direta pelo CDP: bem mais rápida que page.screenshot e o JPEG 96 não mostra perda no traço."""
    import base64
    r = cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": JPEG_Q, "optimizeForSpeed": True})
    return base64.b64decode(r["data"])


def _worker(job_path: str) -> None:
    from playwright.sync_api import sync_playwright
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        page = b.new_page(viewport={"width": 720, "height": 1280})
        _prepare(page, job["spec"])
        cdp = page.context.new_cdp_session(page)
        cdp.send("Page.enable")
        if job["mode"] == "stills":
            for t, path in job["stills"]:
                page.evaluate("t=>V.render(t)", t)
                Path(path).write_bytes(_shot(cdp))
        else:
            fps = int(job["fps"])
            enc = subprocess.Popen([job["ffmpeg"], "-y", "-v", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", str(fps), "-i", "-",
                                    *job["enc"], "-an", job["out"]], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            for n in range(job["start"], job["end"]):
                page.evaluate("t=>V.render(t)", n / fps)
                enc.stdin.write(_shot(cdp))
                if (n - job["start"]) % 15 == 14:
                    print("f 15", flush=True)
            enc.stdin.close()
            if enc.wait() != 0:
                raise RuntimeError("FFmpeg do trecho falhou")
        info = page.evaluate("({missing:V.missing,errors:V.errors})")
        print("info " + json.dumps(info, ensure_ascii=False), flush=True)
        b.close()


def _spawn(job: dict[str, Any], path: Path) -> subprocess.Popen:
    path.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker", str(path)], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="ignore", creationflags=flags, env=env)


def _write_spec(spec: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(spec, ensure_ascii=False, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)), encoding="utf-8")


def _workers_default() -> int:
    return max(1, min(MAX_WORKERS, (os.cpu_count() or 4) // 2))


def _encode_frames(spec: dict[str, Any], workdir: Path, nframes: int, nworkers: int, progress, check) -> tuple[list[Path], dict[str, set]]:
    """Dispara um trabalhador por trecho e acompanha; devolve os trechos em ordem e o que faltou nas bibliotecas."""
    from ...media import ffmpeg_exe
    fps = int(spec.get("fps", 30))
    spec_path = workdir / "vetor_spec.json"
    _write_spec(spec, spec_path)
    # JPEG chega em faixa cheia BT.601: converte para o padrão de vídeo, senão as cores mudam no YouTube
    enc = ["-vf", "scale=in_range=pc:in_color_matrix=bt601:out_range=tv:out_color_matrix=bt709,format=yuv420p",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-threads", "2", "-profile:v", "high",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]
    size = max(fps, nframes // nworkers + 1)
    parts, procs = [], []
    done = [0]
    report: dict[str, set] = {"missing": set(), "errors": set()}
    lock = threading.Lock()

    def follow(p: subprocess.Popen) -> None:
        for ln in p.stdout:
            if ln.startswith("f "):
                with lock:
                    done[0] += int(ln.split()[1])
            elif ln.startswith("info "):
                inf = json.loads(ln[5:])
                with lock:
                    report["missing"].update(inf.get("missing") or [])
                    report["errors"].update(inf.get("errors") or [])

    start, k = 0, 0
    readers = []
    try:
        while start < nframes:
            end = min(nframes, start + size)
            part = workdir / f"vetor_part{k:02d}.mp4"
            job = {"mode": "frames", "spec": str(spec_path), "fps": fps, "start": start, "end": end, "out": str(part),
                   "ffmpeg": ffmpeg_exe(), "enc": enc}
            p = _spawn(job, workdir / f"vetor_job{k:02d}.json")
            th = threading.Thread(target=follow, args=(p,), daemon=True)
            th.start()
            readers.append(th)
            procs.append(p)
            parts.append(part)
            start, k = end, k + 1
        while any(p.poll() is None for p in procs):
            time.sleep(.5)
            if check:
                check()
            if progress:
                progress(min(.99, done[0] / max(1, nframes)))
            if any(p.poll() not in (None, 0) for p in procs):
                break
        for p in procs:
            if p.poll() not in (None, 0):
                raise RuntimeError("Trabalhador vetorial falhou: " + (p.stderr.read() or "")[-800:])
        for p in procs:
            p.wait()
        for th in readers:
            th.join(timeout=5)
    except BaseException:
        for p in procs:
            if p.poll() is None:
                p.kill()
        raise
    return parts, report


def render(spec: dict[str, Any], out: Path, workdir: Path, *, progress=None, check=None, music_bed: Path | None = None) -> dict[str, Any]:
    """Áudio (mesma mixagem do Modo História) → trechos em paralelo no Edge → junta tudo com o áudio."""
    import numpy as np

    from ...config import get as cfg
    from ...media import ffmpeg_exe
    from ...production import loudnorm_2pass
    from ...story.gpu import gpu_lock
    from ..story import build_audio
    workdir = Path(workdir)
    out = Path(out)
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    fps = int(spec.get("fps", 30))
    mix, env = build_audio(dict(spec, lines=spec.get("lines") or []), workdir / "mix_raw.wav", music_bed)
    loud = loudnorm_2pass(mix, workdir / "mix.wav", float(cfg("loudness_target") or -14.0))
    job = dict(spec)
    job["_env"] = [round(float(x), 3) for x in np.asarray(env)]
    nframes = int(float(spec["duration"]) * fps)
    nworkers = int(spec.get("_workers") or _workers_default())
    with gpu_lock("render", timeout=1800):
        parts, report = _encode_frames(job, workdir, nframes, nworkers, progress, check)
        lst = workdir / "vetor_parts.txt"
        lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
        r = subprocess.run([ffmpeg_exe(), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-i", str(workdir / "mix.wav"),
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", str(out)],
                           capture_output=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError("FFmpeg falhou: " + r.stderr.decode(errors="ignore")[-800:])
    for p in parts:
        p.unlink(missing_ok=True)
    return {"path": str(out), "frames": nframes, "seconds": round(time.time() - t0, 1), "loudness": loud, "fps": fps,
            "size": [int(spec.get("W", 720)), int(spec.get("H", 1280))], "missing": sorted(report["missing"]), "errors": sorted(report["errors"])}


def stills(spec: dict[str, Any], times: list[float]) -> list[Any]:
    """Vários quadros avulsos de uma vez (contact sheet): abre o Edge uma vez só."""
    import tempfile

    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        sp = d / "spec.json"
        _write_spec(spec, sp)
        paths = [str(d / f"s{i:03d}.jpg") for i in range(len(times))]
        p = _spawn({"mode": "stills", "spec": str(sp), "stills": [[float(t), q] for t, q in zip(times, paths)]}, d / "job.json")
        o, e = p.communicate(timeout=300)
        if p.returncode != 0:
            raise RuntimeError("Trabalhador vetorial falhou: " + (e or "")[-800:])
        out = []
        for q in paths:
            with Image.open(q) as im:
                out.append(im.convert("RGB").copy())
        return out


def still(spec: dict[str, Any], t: float):
    """Um quadro avulso como PIL.Image."""
    return stills(spec, [t])[0]


if __name__ == "__main__" and len(sys.argv) == 3 and sys.argv[1] == "--worker":
    _worker(sys.argv[2])
