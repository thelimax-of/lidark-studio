"""Voz local Kokoro (grátis, ilimitada, sem internet) — vozes pt-BR pf_dora, pm_alex, pm_santa.

Roda no venv separado data/imggen/venv (torch + kokoro), em CPU, num processo que carrega o modelo uma vez e gera
todas as falas pedidas de uma vez (um episódio inteiro). Assim o servidor não carrega torch nem disputa a GPU.
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from .config import DATA_DIR

log = logging.getLogger("lidark.kokoro")
VENV_PY = DATA_DIR / "imggen" / "venv" / "Scripts" / "python.exe"
HF_HOME = DATA_DIR / "imggen" / "hf"
VOICES = {"pf_dora": "Dora (feminina)", "pm_alex": "Alex (masculina)", "pm_santa": "Santa (masculina)"}

WORKER = r'''
import json, sys, numpy as np, soundfile as sf
from kokoro import KPipeline
jobs = json.load(sys.stdin)
pipe = KPipeline(lang_code="p", device="cpu")
for j in jobs:
    audio = [a for _, _, a in pipe(j["text"], voice=j["voice"], speed=float(j.get("speed") or 1.0))]
    sf.write(j["out"], np.concatenate(audio) if audio else np.zeros(2400, "float32"), 24000)
    print("ok", j["out"], flush=True)
'''


def available() -> bool:
    return VENV_PY.exists()


def synth_batch(items: list[dict]) -> None:
    """items: [{text, voice, speed, out}] → grava cada WAV (24 kHz mono). Erro se o venv/modelo não existir."""
    todo = [i for i in items if not Path(i["out"]).exists() or Path(i["out"]).stat().st_size < 1000]
    if not todo:
        return
    if not available():
        raise RuntimeError("Kokoro não instalado (data/imggen/venv)")
    for i in todo:
        Path(i["out"]).parent.mkdir(parents=True, exist_ok=True)
    env = {**__import__("os").environ, "HF_HOME": str(HF_HOME), "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([str(VENV_PY), "-c", WORKER], input=json.dumps(todo, ensure_ascii=False), capture_output=True,
                       text=True, encoding="utf-8", env=env, timeout=60 + 30 * len(todo))
    missing = [i["out"] for i in todo if not Path(i["out"]).exists()]
    if r.returncode or missing:
        raise RuntimeError(f"Kokoro falhou: {(r.stderr or '')[-400:]}")
    log.info("Kokoro: %d falas geradas", len(todo))
