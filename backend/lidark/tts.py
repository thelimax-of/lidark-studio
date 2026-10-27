"""Narração: Microsoft Neural (edge-tts, grátis/ilimitado) e Gemini TTS (expressivo, com rotação de chaves).

Toda síntese devolve o caminho do áudio e, quando disponível, o tempo de cada palavra.
Se o Gemini falhar (cota), cai automaticamente para o edge-tts.
"""
from __future__ import annotations

import asyncio
import base64
import functools
import logging
import wave
from pathlib import Path
from typing import Any

import httpx

from . import config, llm
from .media import run_ffmpeg

log = logging.getLogger("lidark.tts")

GEMINI_VOICES = {
    "Charon": "Informativo, grave", "Orus": "Firme", "Fenrir": "Empolgado", "Puck": "Animado",
    "Kore": "Firme (feminina)", "Aoede": "Leve (feminina)", "Zephyr": "Brilhante (feminina)",
    "Leda": "Jovem (feminina)", "Iapetus": "Claro", "Enceladus": "Sussurrado", "Algenib": "Rouco",
    "Rasalgethi": "Informativo", "Alnilam": "Firme", "Schedar": "Equilibrado", "Sadaltager": "Conhecedor",
    "Gacrux": "Maduro (feminina)", "Achird": "Amigável", "Zubenelgenubi": "Casual", "Sadachbia": "Animado",
    "Umbriel": "Tranquilo", "Algieba": "Suave", "Despina": "Suave (feminina)", "Erinome": "Claro (feminina)",
    "Laomedeia": "Animada (feminina)", "Autonoe": "Brilhante (feminina)", "Callirrhoe": "Tranquila (feminina)",
    "Vindemiatrix": "Gentil (feminina)", "Sulafat": "Calorosa (feminina)", "Achernar": "Suave (feminina)",
    "Pulcherrima": "Direta (feminina)",
}


@functools.lru_cache
def _edge_voices() -> list[dict[str, Any]]:
    import edge_tts
    vs = asyncio.run(edge_tts.list_voices())
    return [v for v in vs if v["Locale"].startswith("pt-")]


def list_voices(provider: str) -> list[dict[str, str]]:
    if provider == "gemini":
        return [{"id": k, "label": f"{k} — {v}"} for k, v in GEMINI_VOICES.items()]
    try:
        return [{"id": v["ShortName"], "label": f"{v['ShortName'].split('-')[-1].replace('Neural', '')} "
                                               f"({v['Locale']}, {'masc.' if v['Gender'] == 'Male' else 'fem.'})"}
                for v in _edge_voices()]
    except Exception as e:  # noqa: BLE001
        log.warning("edge voices: %s", e)
        return [{"id": "pt-BR-AntonioNeural", "label": "Antonio (pt-BR, masc.)"},
                {"id": "pt-BR-FranciscaNeural", "label": "Francisca (pt-BR, fem.)"},
                {"id": "pt-BR-ThalitaMultilingualNeural", "label": "Thalita (pt-BR, fem.)"}]


def synthesize(text: str, out: Path, *, provider: str = "edge", voice: str = "", rate: str = "+0%",
               style: str = "") -> dict[str, Any]:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if provider == "gemini":
        try:
            return _gemini(text, out, voice or "Charon", style)
        except Exception as e:  # noqa: BLE001
            log.warning("Gemini TTS falhou (%s) — usando Microsoft Neural", e)
            voice = "pt-BR-AntonioNeural"
    return _edge(text, out, voice or "pt-BR-AntonioNeural", rate)


# ---------------------------------------------------------------- edge-tts

def _edge(text: str, out: Path, voice: str, rate: str) -> dict[str, Any]:
    import edge_tts

    async def run():
        words = []
        comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
        with open(out, "wb") as f:
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    st = chunk["offset"] / 1e7
                    words.append({"w": chunk["text"], "start": st, "end": st + chunk["duration"] / 1e7})
        return words

    for attempt in range(3):
        try:
            words = asyncio.run(run())
            if out.stat().st_size > 1000:
                return {"path": str(out), "words": words or None, "provider": "edge", "voice": voice}
        except Exception as e:  # noqa: BLE001
            log.warning("edge-tts tentativa %s: %s", attempt + 1, e)
    raise RuntimeError("Falha na síntese de voz (edge-tts)")


# ---------------------------------------------------------------- narração dirigida (edge-tts)
#
# Em vez de ler o roteiro todo num ritmo só, divide em frases e dirige cada uma como um narrador:
# gancho mais rápido, pausa antes das revelações, respiro depois de perguntas, números mais devagar.
# Frases "normais" seguidas continuam juntas numa chamada só (fala fluida).

REVEAL = ("mas ", "só que", "porém", "contudo", "na verdade", "a verdade", "acontece que", "e foi aí", "foi aí que",
          "o detalhe", "o problema", "e o mais", "o mais incrível", "o mais estranho", "só tem um", "e então")
SR = 24000


def _beats(scenes: list[str]) -> list[dict[str, Any]]:
    """Frases com direção: delta de velocidade (%) e pausa antes (s)."""
    import re
    out: list[dict[str, Any]] = []
    last = len(scenes) - 1
    for si, sc in enumerate(scenes):
        for k, snt in enumerate(x for x in re.split(r"(?<=[.!?…])\s+", sc.strip()) if x):
            low = snt.lower().lstrip("\"'“ ")
            rate, pause = 0, 0.16 if k else 0.24  # respiro normal entre frases / um pouco maior entre cenas
            if si == 0:
                rate = 4  # gancho com energia
            if low.startswith(REVEAL):
                rate, pause = -5, 0.5  # revelação: pausa dramática e mais devagar
            elif re.search(r"\d{3,}|\d+\s*(mil|milh|bilh|%)", low):
                rate = min(rate, -3)  # números e datas: clareza
            if si == last and k == 0 and si > 0:
                pause = 0.35  # respiro antes do encerramento
            if out and (out[-1]["text"].rstrip().endswith(("?", "…", "...")) or out[-1]["text"].rstrip().endswith("!")):
                pause = max(pause, 0.38)  # deixa a pergunta / o choque assentar
            out.append({"text": snt, "rate": rate, "pause": pause})
    return out


def _chunks(beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Junta frases seguidas com o mesmo ritmo e sem pausa especial (menos chamadas, fala mais natural)."""
    out: list[dict[str, Any]] = []
    for b in beats:
        if out and b["rate"] == out[-1]["rate"] and b["pause"] <= 0.24:
            out[-1]["text"] += " " + b["text"]
        else:
            out.append(dict(b))
    return out


def _trim(x, thr: float = 0.012) -> tuple[Any, int]:
    import numpy as np
    idx = np.where(np.abs(x) > thr)[0]
    if not len(idx):
        return x[:0], 0
    a, b = max(0, idx[0] - int(0.02 * SR)), min(len(x), idx[-1] + int(0.06 * SR))
    return x[a:b], a


def synthesize_directed(scenes: list[str], out: Path, voice: str, rate: str = "+0%") -> dict[str, Any]:
    """Narração dirigida frase a frase (só Microsoft Neural, que devolve o tempo de cada palavra)."""
    import numpy as np
    from .media import decode_audio
    try:
        base = int(rate.strip().rstrip("%"))
    except ValueError:
        base = 0
    chunks = _chunks(_beats(scenes))
    tmp = out.parent / "_beats"
    tmp.mkdir(parents=True, exist_ok=True)
    pcm, words, t = [], [], 0.0
    for i, c in enumerate(chunks):
        r = _edge(c["text"], tmp / f"b{i:03d}.mp3", voice, f"{base + c['rate']:+d}%")
        x, cut = _trim(decode_audio(r["path"], SR))
        gap = c["pause"] if i else 0.0
        pcm.append(np.zeros(int(gap * SR), np.float32))
        t += gap
        off = t - cut / SR
        for w in r.get("words") or []:
            words.append({"w": w["w"], "start": max(t, w["start"] + off), "end": max(t, w["end"] + off)})
        pcm.append(x.astype(np.float32))
        t += len(x) / SR
    audio = np.concatenate(pcm + [np.zeros(int(0.15 * SR), np.float32)])
    wav = out.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    for f in tmp.glob("*"):
        f.unlink(missing_ok=True)
    return {"path": str(wav), "words": words or None, "provider": "edge", "voice": voice,
            "directed": {"chunks": len(chunks), "pauses": sum(1 for c in chunks if c["pause"] >= 0.35)}}


# ---------------------------------------------------------------- Gemini

def _gemini(text: str, out: Path, voice: str, style: str) -> dict[str, Any]:
    s = config.load_settings()
    keys = s["gemini_api_keys"]
    if not keys:
        raise RuntimeError("sem chave Gemini")
    prompt = f"{style.strip()}:\n{text}" if style.strip() else text
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    model = s["gemini_tts_model"]
    last = None
    for key in keys:
        ck = f"gemini-tts:{key[-6:]}"
        if llm._is_cool(ck):
            continue
        r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                       headers={"x-goog-api-key": key}, json=body, timeout=300)
        if r.status_code == 429:
            llm._cool(ck, 60 * 30)
            last = "429"
            continue
        if r.status_code != 200:
            last = f"{r.status_code} {r.text[:200]}"
            continue
        part = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]
        pcm = base64.b64decode(part["data"])
        wav = out.with_suffix(".wav")
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)
        if out.suffix != ".wav":
            run_ffmpeg(["-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k", str(out)])
            wav.unlink(missing_ok=True)
        return {"path": str(out), "words": None, "provider": "gemini", "voice": voice}
    raise RuntimeError(f"Gemini TTS indisponível: {last}")
