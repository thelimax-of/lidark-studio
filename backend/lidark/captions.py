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
    return [{"w": r["w"], "start": float(r["start"]), "end": float(r["end"])} for r in align(words, timed, float(total))]


# ---------------------------------------------------------------- destaque semântico das legendas
#
# Cada palavra da legenda ganha um "tipo" de destaque: ênfase pedida pelo roteiro (delivery.emphasis / emphasis),
# data, número ou nome próprio. O template pinta cada tipo conforme o look sorteado para o vídeo
# (ver OuroTemplate._hi_color). Há um teto de destaques por cena: legenda toda colorida não destaca nada.

MONTHS = {"janeiro", "fevereiro", "marco", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
          "novembro", "dezembro", "seculo", "seculos", "decada", "decadas", "milenio"}
NUMBER_WORDS = {"dois", "duas", "tres", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze",
                "quinze", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa",
                "cem", "cento", "duzentos", "trezentos", "quinhentos", "mil", "milhao", "milhoes", "bilhao", "bilhoes",
                "trilhao", "trilhoes", "metade", "dobro", "triplo", "dezenas", "centenas", "milhares"}
# palavras que costumam vir com maiúscula sem serem nomes (início de frase já é ignorado à parte)
NOT_NAMES = {"eu", "voce", "voces", "ele", "ela", "eles", "elas", "nos", "isso", "esse", "essa", "este", "esta",
             "mas", "um", "uma", "segue", "siga", "comenta", "deus", "shorts"}
PRIORITY = {"emph": 0, "date": 1, "num": 2, "name": 3}


def _is_date(nw: str, prev: str, nxt: str) -> bool:
    if nw in MONTHS or re.fullmatch(r"1\d{3}|20\d{2}", nw):
        return True
    return bool(re.fullmatch(r"\d{1,2}", nw)) and norm(prev) in ("dia", "em") and norm(nxt) == "de"


def highlight_kinds(words: list[str], emphasis: set[str] | None = None) -> list[str]:
    """Tipo de destaque de cada palavra de UMA cena: 'emph' | 'date' | 'num' | 'name' | ''."""
    emphasis = emphasis or set()
    kinds: list[str] = []
    for i, w in enumerate(words):
        nw = norm(w)
        prev = words[i - 1] if i else ""
        nxt = words[i + 1] if i + 1 < len(words) else ""
        k = ""
        if not nw:
            pass
        elif nw in emphasis:
            k = "emph"
        elif _is_date(nw, prev, nxt):
            k = "date"
        elif any(c.isdigit() for c in nw) or "%" in w or nw in NUMBER_WORDS:
            k = "num"
        elif len(nw) >= 3 and nw not in NOT_NAMES:
            core = w.strip("\"'“”‘’()[]¿¡#")
            sentence_start = i == 0 or prev.rstrip().endswith((".", "!", "?", ":", "…", "—"))
            if core[:1].isupper() and (not sentence_start or (core.isupper() and len(core) >= 3)):
                k = "name"
        kinds.append(k)
    # teto: no máximo ~1 destaque a cada 4 palavras (mínimo 2 por cena), pela prioridade do tipo
    cap = max(2, len(words) // 4)
    marked = sorted((i for i, k in enumerate(kinds) if k), key=lambda i: (PRIORITY[kinds[i]], i))
    keep = set(marked[:cap])
    # nomes compostos ("Dom Pedro", "Santos Dumont") ficam inteiros se a 1ª parte entrou
    for i in sorted(keep):
        j = i + 1
        while kinds[i] == "name" and j < len(kinds) and kinds[j] == "name":
            keep.add(j)
            j += 1
    return [k if i in keep else "" for i, k in enumerate(kinds)]
