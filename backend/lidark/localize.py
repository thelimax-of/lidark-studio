"""Idiomas: título/descrição em inglês e espanhol (localizations do YouTube) e legendas oficiais (.srt).

- Tradução: UMA chamada barata de IA por vídeo (en + es juntos), guardada em Video.assets["localizations"]
  com a assinatura do texto de origem — o mesmo vídeo nunca traduz duas vezes.
- Legendas: o .srt sai do TEXTO EXATO do roteiro e dos MESMOS tempos de palavra das legendas queimadas no vídeo
  (checkpoint.json da renderização: tempos do edge-tts alinhados por captions.word_timeline). Sem os tempos do TTS,
  usa os tempos de cada cena (assets["scenes"]) e distribui as palavras pelo tamanho.
- Dublagem automática do YouTube: depende de defaultAudioLanguage (pt-BR) — o envio já manda; não há API para
  faixas de áudio, por isso vira item do checklist do Studio (studio_checklist.py).
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

from sqlmodel import select

from . import llm
from .config import MEDIA_DIR
from .db import session
from .models import Account, Publication, Script, Video

log = logging.getLogger("lidark.localize")

LANGS = {"en": "inglês (EUA)", "es": "espanhol (América Latina)"}
CAPTION_NAMES = {"pt-BR": "Português", "en": "English", "es": "Español"}
MAX_CUE_CHARS = 42
MAX_CUE_SECONDS = 4.2


def _sig(*parts: str) -> str:
    return hashlib.sha1("\x1f".join(parts).encode("utf-8")).hexdigest()[:16]


def _save_asset(video_id: int, key: str, value: Any) -> None:
    """Grava uma chave em Video.assets relendo o registro (outros módulos também escrevem em assets)."""
    with session() as s:
        v = s.get(Video, video_id)
        if v:
            v.assets = {**(v.assets or {}), key: value}
            s.add(v)
            s.commit()


# ================================================================ título e descrição

def translate_meta(video_id: int | None, title: str, description: str) -> dict[str, dict[str, str]]:
    """{"en": {"title", "description"}, "es": {...}} — do cache quando o texto não mudou."""
    title, description = (title or "").strip(), (description or "").strip()
    if not title:
        return {}
    sig = _sig(title, description)
    if video_id:
        with session() as s:
            v = s.get(Video, video_id)
        cached = ((v.assets or {}).get("localizations") or {}) if v else {}
        if cached.get("sig") == sig and cached.get("data"):
            return cached["data"]
    short = "#shorts" in title.lower()
    prompt = f"""Traduza o título e a descrição deste vídeo do YouTube (português do Brasil) para {LANGS['en']} e {LANGS['es']}.
Regras: tradução natural de YouTube (não literal), mesmo tom, sem inventar nada; mantenha nomes próprios, números,
links, hashtags e emojis exatamente como estão; título com até 95 caracteres{' e terminando em #Shorts' if short else ''}.

TÍTULO: {title}
DESCRIÇÃO:
{description[:2500]}

Responda JSON: {{"en": {{"title": "...", "description": "..."}}, "es": {{"title": "...", "description": "..."}}}}"""
    data = llm.complete_json(prompt, temperature=0.3, required=["en", "es"])
    out: dict[str, dict[str, str]] = {}
    for lang in LANGS:
        d = (data or {}).get(lang) if isinstance(data, dict) else None
        if isinstance(d, dict) and str(d.get("title") or "").strip():
            t = str(d["title"]).strip()[:100]
            if short and "#shorts" not in t.lower() and len(t) <= 91:
                t = f"{t} #Shorts"
            out[lang] = {"title": t, "description": str(d.get("description") or "").strip()[:4900]}
    if video_id and out:
        _save_asset(video_id, "localizations", {"sig": sig, "data": out})
    return out


def build_localizations(video: Video, title: str, core: str, full_desc: str) -> dict[str, dict[str, str]]:
    """Corpo `localizations` do videos.insert/update. A descrição traduzida = texto do vídeo traduzido + o resto
    da descrição original (fontes, créditos, capítulos e hashtags não mudam de idioma)."""
    tr = translate_meta(video.id if video else None, title, core)
    tail = full_desc.replace(core.strip(), "", 1).strip() if core.strip() and core.strip() in full_desc else ""
    out = {}
    for lang, d in tr.items():
        desc = d["description"] + (f"\n\n{tail}" if tail else "")
        out[lang] = {"title": d["title"][:100], "description": desc[:4900]}
    return out


def push_existing(pub_id: int, dry_run: bool = True) -> dict[str, Any]:
    """Vídeo já publicado: põe os títulos/descrições em inglês e espanhol (videos.update part=snippet,localizations).
    dry_run=True só mostra o que seria enviado (nenhuma chamada de escrita)."""
    from . import quota
    from .publish import _yt_client, _yt_creds
    with session() as s:
        pub = s.get(Publication, pub_id)
        acc = s.get(Account, pub.account_id) if pub else None
        video = s.get(Video, pub.video_id) if pub and pub.video_id else None
    if not pub or not pub.external_id or not acc:
        return {"ok": False, "error": "publicação sem vídeo no YouTube"}
    yt = _yt_client(_yt_creds(acc))
    proj = quota.project_of(acc)
    item = (yt.videos().list(part="snippet,localizations", id=pub.external_id).execute().get("items") or [None])[0]
    quota.spend(1, "list", proj)
    if not item:
        return {"ok": False, "error": "vídeo não encontrado no YouTube"}
    sn = item["snippet"]
    core = (pub.description or "").strip()
    if video:
        with session() as s:
            sc = s.get(Script, video.script_id)
        core = (sc.description if sc else "") or core
    locs = build_localizations(video, sn["title"], core or sn.get("description", ""), sn.get("description", ""))
    if not locs:
        return {"ok": False, "error": "tradução falhou"}
    body = {"id": pub.external_id,
            "snippet": {"title": sn["title"], "categoryId": sn.get("categoryId", "27"), "description": sn.get("description", ""),
                        "tags": sn.get("tags", []), "defaultLanguage": sn.get("defaultLanguage") or "pt-BR",
                        "defaultAudioLanguage": sn.get("defaultAudioLanguage") or "pt-BR"},
            "localizations": {**(item.get("localizations") or {}), **locs}}
    if dry_run:
        return {"ok": True, "dry_run": True, "body": body}
    if not quota.guard("videos.update", project=proj):
        return {"ok": False, "error": "cota do YouTube no limite — tente depois da renovação"}
    yt.videos().update(part="snippet,localizations", body=body).execute()
    quota.spend(quota.COSTS["videos.update"], "videos.update", proj)
    return {"ok": True, "languages": list(locs)}


# ================================================================ legendas (.srt)

def _workdir(video: Video) -> Path | None:
    if not video.path:
        return None
    return (MEDIA_DIR / video.path).parent


def word_timings(video: Video) -> tuple[list[dict[str, Any]], str]:
    """Palavras com tempo, exatamente como nas legendas queimadas. Devolve (palavras, origem)."""
    from . import captions
    assets = video.assets or {}
    scenes = assets.get("scenes") or []
    text = " ".join(str(sc.get("text") or "").strip() for sc in scenes).strip()
    if not text:
        with session() as s:
            sc = s.get(Script, video.script_id)
        scenes_src = (sc.scenes if sc else []) or []
        text = " ".join(str(x.get("text") or "").strip() for x in scenes_src).strip()
    if not text:
        return [], "sem texto"
    wd = _workdir(video)
    ck = {}
    if wd and (wd / "checkpoint.json").exists():
        try:
            ck = json.loads((wd / "checkpoint.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            ck = {}
    voice = ck.get("voice") or {}
    total = float(ck.get("narr_dur") or assets.get("narration_end") or video.duration or 0)
    if voice.get("words") and total:
        # mesmo cálculo da renderização (production.py → captions.word_timeline com os tempos do TTS): só alinha
        return captions.word_timeline(text, voice.get("path", ""), total, voice["words"]), "tts"
    if scenes and all("start" in x and "end" in x for x in scenes):  # tempos de cada cena da timeline
        out = []
        for x in scenes:
            ws = str(x.get("text") or "").split()
            if not ws:
                continue
            st, en = float(x["start"]), float(x["end"])
            lens = [len(w) + 2 for w in ws]
            tot = sum(lens)
            cur = st
            for w, l in zip(ws, lens):
                d = (en - st) * l / tot
                out.append({"w": w, "start": cur, "end": cur + d})
                cur += d
        return out, "cenas"
    return [], "sem tempos"


def _sentences(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    out, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.!?…]['\"”»)]*$", w["w"]) or (len(cur) > 24 and re.search(r"[,;:]$", w["w"])):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def _split_text(text: str, n_max: int = MAX_CUE_CHARS) -> list[str]:
    words, out, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > n_max:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def pt_cues(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cortes de legenda com os tempos reais de cada palavra (≤ 42 caracteres, ≤ 4,2 s, sem atravessar frases)."""
    cues = []
    for sent in _sentences(words):
        mine: list[dict[str, Any]] = []
        cur: list[dict[str, Any]] = []
        for w in sent:
            text = " ".join(x["w"] for x in cur + [w])
            if cur and (len(text) > MAX_CUE_CHARS or w["end"] - cur[0]["start"] > MAX_CUE_SECONDS):
                mine.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": " ".join(x["w"] for x in cur)})
                cur = []
            cur.append(w)
        if cur:
            last = {"start": cur[0]["start"], "end": cur[-1]["end"], "text": " ".join(x["w"] for x in cur)}
            prev = mine[-1] if mine else None
            if prev and len(last["text"]) < 12 and len(prev["text"]) + 1 + len(last["text"]) <= 56:
                prev.update(end=last["end"], text=f"{prev['text']} {last['text']}")  # sem sobra de 1 palavra sozinha
            else:
                mine.append(last)
        cues += mine
    return cues


def _fmt(t: float) -> str:
    ms = max(0, int(round(t * 1000)))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def to_srt(cues: list[dict[str, Any]]) -> str:
    lines = []
    for i, c in enumerate(cues):
        end = c["end"]
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else None
        end = min(end + 0.25, nxt - 0.02) if nxt is not None else end + 0.4  # respiro de leitura sem sobrepor
        end = max(end, c["start"] + 0.5)
        lines.append(f"{i + 1}\n{_fmt(c['start'])} --> {_fmt(end)}\n{c['text']}\n")
    return "\n".join(lines)


def translate_sentences(video_id: int, sentences: list[str]) -> dict[str, list[str]]:
    """Frases do roteiro em en/es (uma chamada; mesmo número de itens), com cache no vídeo."""
    sig = _sig(*sentences)
    with session() as s:
        v = s.get(Video, video_id)
    cached = ((v.assets or {}).get("caption_tr") or {}) if v else {}
    if cached.get("sig") == sig and cached.get("data"):
        return cached["data"]
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(sentences))
    prompt = f"""Traduza cada frase desta narração de vídeo (português do Brasil) para {LANGS['en']} e {LANGS['es']}.
Mantenha a MESMA quantidade de frases ({len(sentences)}) e a mesma ordem — uma tradução por frase, natural para
legenda, sem juntar nem dividir frases; nomes próprios e números como estão.

{numbered}

Responda JSON: {{"en": ["frase 1", ...], "es": ["frase 1", ...]}}"""
    data = llm.complete_json(prompt, temperature=0.2, required=["en", "es"])
    out = {}
    for lang in LANGS:
        arr = (data or {}).get(lang) if isinstance(data, dict) else None
        if isinstance(arr, list) and len(arr) == len(sentences):
            out[lang] = [re.sub(r"^\d+[.)]\s*", "", str(x)).strip() for x in arr]
    if out:
        _save_asset(video_id, "caption_tr", {"sig": sig, "data": out})
    return out


def build_srts(video_id: int, langs: list[str] | tuple[str, ...] = ("pt-BR", "en", "es")) -> dict[str, Any]:
    """{"source": "tts|cenas", "srt": {lang: texto}, "cues": n}. Traduções mantêm o tempo de cada frase e
    dividem o texto traduzido em cortes proporcionais ao tamanho."""
    with session() as s:
        video = s.get(Video, video_id)
    if not video:
        return {"srt": {}, "source": "", "error": "vídeo não encontrado"}
    words, source = word_timings(video)
    if not words:
        return {"srt": {}, "source": source, "error": "sem tempos de palavra"}
    out: dict[str, str] = {}
    cues = pt_cues(words)
    if "pt-BR" in langs:
        out["pt-BR"] = to_srt(cues)
    want = [x for x in langs if x in LANGS]
    if want:
        sents = _sentences(words)
        texts = [" ".join(w["w"] for w in s) for s in sents]
        tr = translate_sentences(video_id, texts)
        for lang in want:
            if lang not in tr:
                continue
            tcues = []
            for s_words, t in zip(sents, tr[lang]):
                st, en = s_words[0]["start"], s_words[-1]["end"]
                parts = _split_text(t) or [t]
                tot = sum(len(p) for p in parts) or 1
                cur = st
                for p in parts:
                    d = (en - st) * len(p) / tot
                    tcues.append({"start": cur, "end": cur + d, "text": p})
                    cur += d
            out[lang] = to_srt(tcues)
    return {"srt": out, "source": source, "cues": len(cues), "words": len(words)}


def write_srts(video_id: int, built: dict[str, Any]) -> dict[str, str]:
    """Salva os .srt na pasta do vídeo (ficam para baixar/conferir). Devolve {lang: caminho relativo em /media}."""
    with session() as s:
        video = s.get(Video, video_id)
    wd = _workdir(video) if video else None
    if not wd:
        return {}
    wd.mkdir(parents=True, exist_ok=True)
    paths = {}
    for lang, srt in (built.get("srt") or {}).items():
        p = wd / f"captions_{lang}.srt"
        p.write_text(srt, encoding="utf-8")
        paths[lang] = str(p.relative_to(MEDIA_DIR)).replace("\\", "/")
    return paths


def upload_captions(pub_id: int, langs: list[str], dry_run: bool = False, log_fn=None) -> dict[str, Any]:
    """captions.insert de cada idioma que ainda não subiu. Respeita a cota (400 unidades por idioma).
    Devolve {"sent": [...], "pending": [...], "skipped": motivo?}."""
    from googleapiclient.http import MediaInMemoryUpload
    from . import quota
    from .community import WRITE_SCOPE
    from .publish import _yt_client, _yt_creds
    say = log_fn or log.info
    with session() as s:
        pub = s.get(Publication, pub_id)
        acc = s.get(Account, pub.account_id) if pub else None
        video = s.get(Video, pub.video_id) if pub and pub.video_id else None
    if not pub or not video or not pub.external_id:
        return {"sent": [], "pending": [], "skipped": "publicação sem vídeo no YouTube"}
    done = dict((video.assets or {}).get("official_captions") or {})
    todo = [x for x in langs if x not in done]
    if not todo:
        return {"sent": [], "pending": [], "skipped": "legendas já enviadas"}
    built = build_srts(video.id, todo)
    paths = write_srts(video.id, built)
    if not built.get("srt"):
        return {"sent": [], "pending": [], "skipped": built.get("error") or "sem legendas"}
    if dry_run:
        return {"sent": [], "pending": todo, "dry_run": True, "files": paths, "source": built.get("source"),
                "preview": {k: v[:600] for k, v in built["srt"].items()}}
    if not acc or WRITE_SCOPE not in ((acc.credentials or {}).get("scopes") or []):
        return {"sent": [], "pending": todo, "skipped": "scope", "files": paths}
    yt = _yt_client(_yt_creds(acc))
    proj = quota.project_of(acc)
    sent, pending = [], []
    for lang in todo:
        srt = built["srt"].get(lang)
        if not srt:
            continue
        if not quota.guard("captions.insert", project=proj):
            pending.append(lang)
            continue
        body = {"snippet": {"videoId": pub.external_id, "language": lang, "name": CAPTION_NAMES.get(lang, lang), "isDraft": False}}
        media = MediaInMemoryUpload(srt.encode("utf-8"), mimetype="application/octet-stream", resumable=False)
        from googleapiclient.errors import HttpError
        try:
            resp = yt.captions().insert(part="snippet", body=body, media_body=media).execute()
        except HttpError as e:
            quota.spend(quota.COSTS["captions.insert"], "captions.insert", proj)  # chamada recusada também gasta
            msg = str(e)
            if e.resp.status == 403 and ("insufficient" in msg.lower() or "permission" in msg.lower()):
                if sent:
                    _save_asset(video.id, "official_captions", done)
                return {"sent": sent, "pending": [x for x in todo if x not in sent], "skipped": "scope", "files": paths}
            if e.resp.status == 403 and "quota" in msg.lower():
                pending += [x for x in todo if x not in sent and x not in pending]
                break
            raise
        quota.spend(quota.COSTS["captions.insert"], "captions.insert", proj)
        done[lang] = resp.get("id", "ok")
        sent.append(lang)
        say(f"Legenda oficial enviada: {CAPTION_NAMES.get(lang, lang)}")
    if sent:
        _save_asset(video.id, "official_captions", done)
    return {"sent": sent, "pending": pending, "files": paths, "source": built.get("source")}
