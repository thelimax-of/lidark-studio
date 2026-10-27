"""Tempo de cada palavra da narração.

- edge-tts já entrega os tempos (WordBoundary) → só alinhamos com o texto do roteiro (pontuação, destaque).
- Gemini/outras vozes → faster-whisper com timestamps por palavra, alinhado ao roteiro.
"""
from __future__ import annotations

import difflib
import logging
import re
import unicodedata
from typing import Any

from . import config

log = logging.getLogger("lidark.captions")
_model = None


def norm(w: str) -> str:
    w = unicodedata.normalize("NFKD", w.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", w)


def whisper_words(audio_path: str) -> list[dict[str, Any]]:
    global _model
    from faster_whisper import WhisperModel
    s = config.load_settings()
    if _model is None:
        device = s["whisper_device"]
        try:
            _model = WhisperModel(s["whisper_model"], device=device, compute_type="float16" if device == "cuda" else "int8")
        except Exception as e:  # noqa: BLE001
            log.warning("Whisper em %s falhou (%s), usando CPU", device, e)
            _model = WhisperModel(s["whisper_model"], device="cpu", compute_type="int8")
    segs, _ = _model.transcribe(audio_path, language="pt", word_timestamps=True, vad_filter=False, beam_size=5)
    out = []
    for seg in segs:
        for w in seg.words or []:
            out.append({"w": w.word.strip(), "start": float(w.start), "end": float(w.end)})
    return out


def align(script_words: list[str], timed: list[dict[str, Any]], total: float) -> list[dict[str, Any]]:
    """Projeta os tempos reconhecidos nas palavras exatas do roteiro (mantém grafia e pontuação)."""
    a = [norm(w) for w in script_words]
    b = [norm(t["w"]) for t in timed]
    res: list[dict[str, Any] | None] = [None] * len(script_words)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                t = timed[j1 + k]
                res[i1 + k] = {"w": script_words[i1 + k], "start": t["start"], "end": t["end"]}
        elif tag == "replace" and j2 > j1:
            # distribui o trecho reconhecido proporcionalmente entre as palavras do roteiro
            st, en = timed[j1]["start"], timed[j2 - 1]["end"]
            n = i2 - i1
            lens = [max(1, len(a[i1 + k])) for k in range(n)]
            tot = sum(lens)
            cur = st
            for k in range(n):
                d = (en - st) * lens[k] / tot
                res[i1 + k] = {"w": script_words[i1 + k], "start": cur, "end": cur + d}
                cur += d
    # preenche lacunas por interpolação
    for i, r in enumerate(res):
        if r is None:
            prev_end = next((res[j]["end"] for j in range(i - 1, -1, -1) if res[j]), 0.0)
            nxt = next(((j, res[j]["start"]) for j in range(i + 1, len(res)) if res[j]), (len(res), total))
            gap_words = nxt[0] - i
            d = max(0.05, (nxt[1] - prev_end) / max(1, gap_words))
            res[i] = {"w": script_words[i], "start": prev_end, "end": prev_end + d}
    # garante monotonicidade
    for i in range(1, len(res)):
        if res[i]["start"] < res[i - 1]["start"]:
            res[i]["start"] = res[i - 1]["end"]
        if res[i]["end"] < res[i]["start"]:
            res[i]["end"] = res[i]["start"] + 0.05
    return res  # type: ignore[return-value]


def word_timeline(text: str, audio_path: str, total: float, tts_words: list | None) -> list[dict[str, Any]]:
    words = text.split()
    if tts_words:
        timed = tts_words
    else:
        try:
            timed = whisper_words(audio_path)
        except Exception as e:  # noqa: BLE001
            log.warning("Whisper indisponível (%s) — tempos estimados", e)
            timed = []
    if not timed:
        # estimativa proporcional ao tamanho das palavras
        lens = [len(w) + 2 for w in words]
        tot = sum(lens)
        cur, out = 0.0, []
        for w, l in zip(words, lens):
            d = total * l / tot
            out.append({"w": w, "start": cur, "end": cur + d})
            cur += d
        return out
    return align(words, timed, total)
