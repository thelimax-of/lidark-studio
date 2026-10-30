"""Voz local (EXPERIMENTAL, DESLIGADA por padrão): Chatterbox Multilingual (pt) rodando na própria máquina.

Por que fica num ambiente Python SEPARADO e num processo à parte
-----------------------------------------------------------------
- o Chatterbox exige PyTorch (+2,5 GB) e fixa versões antigas de numpy/transformers: instalado no venv do servidor
  ele derrubaria o numpy 2.x que o render usa. Por isso ele vive em data/voice_local/venv.
- o modelo é carregado num subprocesso que gera a narração e SAI: RAM e VRAM voltam inteiras para o render
  (carregar/descarregar em volta do uso). Antes de abrir, checa RAM e VRAM livres; sem folga, recusa e a produção
  cai na voz Microsoft Neural (nunca trava um vídeo).

Ética: a voz de referência do canal só pode ser a SUA própria ou uma voz licenciada (marcada no canal em
theme.voice_ref_consent = "own" | "licensed"). Nunca clonar pessoas reais. Sem referência, usa a voz padrão do modelo.

Status medido nesta máquina (RTX 3050 6 GB, 7,7 GB de RAM): ver `python -m lidark.voice_local status`.
Instalação (manual, ~6 GB entre PyTorch e o modelo; só quando quiser testar):
    py -3.11 -m venv data\\voice_local\\venv
    data\\voice_local\\venv\\Scripts\\pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
    data\\voice_local\\venv\\Scripts\\pip install chatterbox-tts
    python -m lidark.voice_local test     (baixa o modelo em data/voice_local/hf e gera uma frase de 10 s)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from . import config

log = logging.getLogger("lidark.voice_local")

ROOT = config.DATA_DIR / "voice_local"
REFS = ROOT / "refs"
HF_HOME = ROOT / "hf"
VENV_PY = ROOT / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
MIN_RAM_MB = 4200  # modelo (~2 GB) + PyTorch/CUDA (~1,5 GB) + folga para o servidor continuar vivo
MIN_VRAM_MB = 3500
TIMEOUT_S = 900
TEST_SENTENCE = ("Você sabia que, em mil oitocentos e oitenta e oito, uma única assinatura mudou a história do Brasil "
                 "para sempre? Fica comigo até o final, porque o detalhe mais estranho vem agora.")

RUNNER = r'''
import json, sys, re
job = json.load(open(sys.argv[1], encoding="utf-8"))
import torch, torchaudio
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
dev = "cuda" if torch.cuda.is_available() else "cpu"
model = ChatterboxMultilingualTTS.from_pretrained(device=dev)
parts, cur = [], ""
for s in re.split(r"(?<=[.!?…])\s+", job["text"].strip()):
    if cur and len(cur) + len(s) > 240:
        parts.append(cur); cur = s
    else:
        cur = (cur + " " + s).strip()
if cur:
    parts.append(cur)
out = []
gap = torch.zeros(1, int(model.sr * 0.14))
for p in parts:
    kw = dict(language_id="pt", exaggeration=float(job.get("exaggeration", 0.5)), cfg_weight=float(job.get("cfg", 0.5)))
    if job.get("ref"):
        kw["audio_prompt_path"] = job["ref"]
    with torch.inference_mode():
        wav = model.generate(p, **kw)
    out += [wav.cpu(), gap]
torchaudio.save(job["out"], torch.cat(out, dim=1), model.sr)
print(json.dumps({"ok": True, "sr": model.sr, "parts": len(parts), "device": dev}))
'''


def _free_vram_mb() -> float | None:
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=10)
        return float(r.stdout.strip().splitlines()[0])
    except Exception:  # noqa: BLE001
        return None


def ref_path(ch: Any) -> str | None:
    """Arquivo de voz de referência do canal — só com consentimento marcado (voz própria ou licenciada)."""
    th = getattr(ch, "theme", None) or {}
    name = str(th.get("voice_ref") or "").strip()
    if not name or th.get("voice_ref_consent") not in ("own", "licensed"):
        return None
    p = Path(name)
    if not p.is_absolute():
        p = REFS / p.name  # só arquivos dentro de data/voice_local/refs
    return str(p) if p.exists() else None


def status() -> dict[str, Any]:
    from .render.core import free_ram_mb
    reasons: list[str] = []
    enabled = bool(config.get("local_voice_enabled"))
    if not enabled:
        reasons.append("desligada em Configurações (local_voice_enabled)")
    installed = VENV_PY.exists()
    if not installed:
        reasons.append(f"ambiente do Chatterbox não instalado ({VENV_PY.parent.parent})")
    ram, vram = free_ram_mb(), _free_vram_mb()
    if ram is not None and ram < MIN_RAM_MB:
        reasons.append(f"RAM livre {ram:.0f} MB < {MIN_RAM_MB} MB")
    if vram is not None and vram < MIN_VRAM_MB:
        reasons.append(f"VRAM livre {vram:.0f} MB < {MIN_VRAM_MB} MB")
    if vram is None:
        reasons.append("GPU NVIDIA não encontrada (na CPU seria lento demais)")
    return {"enabled": enabled, "installed": installed, "free_ram_mb": ram, "free_vram_mb": vram,
            "model_cached": (HF_HOME / "hub").exists() and any((HF_HOME / "hub").glob("models--*chatterbox*")),
            "ready": not reasons, "reasons": reasons, "refs_dir": str(REFS)}


def available() -> bool:
    return bool(status()["ready"])


def synthesize(text: str, out: Path, ref: str | None = None, exaggeration: float = 0.5,
               cfg: float = 0.5, force: bool = False) -> dict[str, Any]:
    """Gera a narração num subprocesso (carrega o modelo, gera, sai). Erro → quem chamou cai no edge-tts."""
    st = status()
    if not force and not st["ready"]:
        raise RuntimeError("; ".join(st["reasons"]))
    if not VENV_PY.exists():
        raise RuntimeError("ambiente do Chatterbox não instalado")
    out = Path(out)
    wav = out.with_suffix(".wav")
    ROOT.mkdir(parents=True, exist_ok=True)
    runner = ROOT / "runner.py"
    runner.write_text(RUNNER, encoding="utf-8")
    job = out.with_name(out.stem + "_local_job.json")
    job.write_text(json.dumps({"text": text, "out": str(wav), "ref": ref, "exaggeration": exaggeration, "cfg": cfg},
                              ensure_ascii=False), encoding="utf-8")
    env = {**os.environ, "HF_HOME": str(HF_HOME), "PYTHONIOENCODING": "utf-8",
           "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}
    flags = (subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS) if os.name == "nt" else 0
    t0 = time.time()
    try:
        r = subprocess.run([str(VENV_PY), str(runner), str(job)], capture_output=True, text=True, env=env,
                           timeout=TIMEOUT_S, creationflags=flags, encoding="utf-8", errors="ignore")
    finally:
        job.unlink(missing_ok=True)
    if r.returncode != 0 or not wav.exists() or wav.stat().st_size < 10000:
        raise RuntimeError("Chatterbox falhou: " + (r.stderr or r.stdout)[-800:])
    from .media import audio_duration
    dur = audio_duration(wav)
    log.info("voz local: %.1fs de áudio em %.0fs", dur, time.time() - t0)
    return {"path": str(wav), "words": None, "provider": "local",
            "voice": "chatterbox-mtl" + ("/ref" if ref else ""), "gen_seconds": round(time.time() - t0, 1)}


def selftest(out_dir: Path | None = None) -> dict[str, Any]:
    """Frase de ~10 s: confiável = gera, dura 6–20 s e não é silêncio."""
    import numpy as np
    from .media import decode_audio
    out_dir = Path(out_dir or (ROOT / "test"))
    out_dir.mkdir(parents=True, exist_ok=True)
    r = synthesize(TEST_SENTENCE, out_dir / "teste.wav", force=True)
    x = decode_audio(r["path"], 24000)
    dur = len(x) / 24000
    rms = float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0
    return {**r, "duration": round(dur, 2), "rms": round(rms, 4), "reliable": 6 <= dur <= 20 and rms > 0.01}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    print(json.dumps(selftest() if cmd == "test" else status(), ensure_ascii=False, indent=2, default=str))
