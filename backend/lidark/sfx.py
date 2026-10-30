"""Efeitos sonoros sintetizados na hora (nada baixado: zero risco de direitos autorais).

- whoosh nos cortes de cena, impact nas revelações (carimbos, "mas...", "a verdade é"), ding suave no desfecho
- cada vídeo sorteia a "dose" (leve / média / forte) e as variantes dos sons pela semente do título:
  dois vídeos seguidos do canal não soam iguais (variedade contra "conteúdo repetitivo")
- vídeo longo (assistido na TV) usa dose mais baixa e espaçada
- liga/desliga: global em Configurações (sfx_enabled) e por canal (theme.sfx = "off")
"""
from __future__ import annotations

import random
import wave
from pathlib import Path
from typing import Any

import numpy as np

from . import config

SR = 48000
_DIR = config.CACHE_DIR / "sfx"

DOSES = {  # chance de whoosh por corte, volume relativo, espaço mínimo entre whooshes (s)
    "leve": {"whoosh": 0.35, "gain": 0.75, "gap": 4.0},
    "media": {"whoosh": 0.6, "gain": 0.88, "gap": 2.5},
    "forte": {"whoosh": 0.9, "gain": 1.0, "gap": 1.4},
}
REVEAL_EMOTIONS = {"reveal", "revelacao", "revelação", "choque", "surpresa", "shock", "surprise", "impacto", "tensao",
                   "tensão"}
PAYOFF_EMOTIONS = {"payoff", "desfecho", "alivio", "alívio", "satisfacao", "satisfação", "triunfo"}


def enabled(ch: Any) -> bool:
    if not config.get("sfx_enabled"):
        return False
    return str(((getattr(ch, "theme", None) or {}).get("sfx") or "on")).lower() not in ("off", "0", "false", "no")


# ================================================================ síntese

def _write(path: Path, data: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    m = float(np.abs(data).max()) or 1.0
    pcm = (data / m * 0.85 * 32767).astype(np.int16)
    tmp = path.with_suffix(".tmp")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    tmp.replace(path)
    return path


def _onepole(x: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Passa-baixa de 1 polo com coeficiente variável no tempo (a ∈ (0,1])."""
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def _whoosh(v: int) -> np.ndarray:
    rng = np.random.default_rng(100 + v)
    dur = (0.38, 0.5, 0.62, 0.3)[v % 4]
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    up = v % 2 == 0  # sobe (abre) ou desce (fecha) o brilho do ruído
    sweep = t if up else 1 - t
    a_hi = 0.015 + 0.35 * sweep ** 1.6
    a_lo = 0.002 + 0.03 * sweep
    band = _onepole(noise, a_hi) - _onepole(noise, a_lo)  # passa-banda deslizante
    peak = 0.55 if up else 0.4
    env = np.where(t < peak, (t / peak) ** 2, ((1 - t) / (1 - peak)) ** 1.5)
    return band * env


def _impact(v: int) -> np.ndarray:
    rng = np.random.default_rng(200 + v)
    dur = (0.9, 1.2, 0.7)[v % 3]
    n = int(SR * dur)
    tt = np.arange(n) / SR
    f0 = (62, 48, 75)[v % 3]
    f = f0 * (1 + 1.4 * np.exp(-tt * 18))  # queda rápida de afinação (soco grave)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * (4.5 + v % 3))
    click = _onepole(rng.standard_normal(n), np.full(n, 0.25)) * np.exp(-tt * 40) * 0.7
    tail = _onepole(rng.standard_normal(n), np.full(n, 0.04)) * np.exp(-tt * 6) * 0.25
    return np.tanh((body + click + tail) * 1.6)


def _ding(v: int) -> np.ndarray:
    dur = 1.6
    n = int(SR * dur)
    tt = np.arange(n) / SR
    f0 = (988.0, 880.0, 1175.0, 784.0)[v % 4]
    partials = ((1.0, 1.0, 2.2), (2.76, 0.32, 4.0), (5.4, 0.12, 7.0), (2.0, 0.18, 3.0))
    sig = sum(a * np.sin(2 * np.pi * f0 * m * tt) * np.exp(-tt * d) for m, a, d in partials)
    attack = np.clip(tt / 0.006, 0, 1)
    return sig * attack


def _riser(v: int) -> np.ndarray:
    rng = np.random.default_rng(300 + v)
    dur = 0.9
    n = int(SR * dur)
    t = np.linspace(0, 1, n)
    noise = _onepole(rng.standard_normal(n), 0.02 + 0.4 * t ** 2)
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * t ** 2) / SR) * 0.25
    return (noise + tone) * t ** 2.2


SYNTHS = {"whoosh": (_whoosh, 4), "impact": (_impact, 3), "ding": (_ding, 4), "riser": (_riser, 1)}


def sound(kind: str, variant: int = 0) -> Path:
    """Arquivo WAV (48 kHz mono) do efeito, gerado uma vez e guardado no cache."""
    fn, nv = SYNTHS[kind]
    v = variant % nv
    p = _DIR / f"{kind}_{v}.wav"
    if not p.exists():
        _write(p, fn(v))
    return p


# ================================================================ plano de efeitos de um vídeo

def plan(seed: int, cuts: list[float], reveals: list[float], payoff: float | None, duration: float, *,
         vertical: bool = True, opening: str = "") -> dict[str, Any]:
    """Quais efeitos tocam e quando: [{t, kind, variant, gain}] + a dose sorteada para o vídeo."""
    rng = random.Random(seed * 7919 + 13)
    dose_name = rng.choices(list(DOSES), weights=(3, 4, 2) if vertical else (6, 3, 0))[0]
    dose = DOSES[dose_name]
    wv, iv, dv = rng.randrange(4), rng.randrange(3), rng.randrange(4)  # variantes "da casa" deste vídeo
    gap = dose["gap"] if vertical else max(6.0, dose["gap"] * 2.5)
    events: list[dict[str, Any]] = []
    busy: list[float] = []

    def free(t: float, d: float) -> bool:
        return all(abs(t - b) >= d for b in busy)

    if opening == "impact":
        events.append({"t": 0.0, "kind": "impact", "variant": iv, "gain": 0.5 * dose["gain"]})
        busy.append(0.0)
    for t in sorted(x for x in reveals if 0.2 < x < duration - 0.3)[:14]:
        if free(t, 1.2):
            events.append({"t": max(0.0, t - 0.03), "kind": "impact", "variant": iv, "gain": 0.42 * dose["gain"]})
            busy.append(t)
    last_w = -99.0
    for t in sorted(x for x in cuts if 0.3 < x < duration - 0.3):
        if t - last_w < gap or rng.random() > dose["whoosh"] or not free(t, 0.5):
            continue
        # o whoosh "chega" no corte: começa antes e termina logo depois
        var = wv if rng.random() < 0.75 else rng.randrange(4)
        events.append({"t": max(0.0, t - 0.22), "kind": "whoosh", "variant": var, "gain": 0.32 * dose["gain"]})
        last_w = t
        busy.append(t)
    if payoff is not None and 0.3 < payoff < duration - 0.5 and free(payoff, 0.8):
        events.append({"t": payoff + 0.05, "kind": "ding", "variant": dv, "gain": 0.22 * dose["gain"]})
    events.sort(key=lambda e: e["t"])
    return {"dose": dose_name, "events": events[:40]}


def reveal_times(scenes: list[dict[str, Any]], starts: list[float]) -> list[float]:
    """Começo das cenas de revelação: emoção pedida pelo roteiro ou frase que abre com "mas", "a verdade"..."""
    from .tts import REVEAL
    out = []
    for s, st in zip(scenes, starts):
        emo = str(((s.get("delivery") or {}).get("emotion") or "")).lower()
        low = (s.get("text") or "").lower().lstrip("\"'“ ")
        if emo in REVEAL_EMOTIONS or low.startswith(REVEAL):
            out.append(st)
    return out


def payoff_time(scenes: list[dict[str, Any]], starts: list[float]) -> float | None:
    """Desfecho: cena marcada como payoff no roteiro; senão a penúltima (antes do CTA) ou a última."""
    for s, st in zip(scenes, starts):
        if str(((s.get("delivery") or {}).get("emotion") or "")).lower() in PAYOFF_EMOTIONS:
            return st
    if len(starts) >= 4:
        return starts[-2]
    return starts[-1] if len(starts) >= 2 else None
