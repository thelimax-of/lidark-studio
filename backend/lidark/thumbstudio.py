"""Estúdio de miniaturas: várias versões para um vídeo (fotos, textos e layouts diferentes), prévia como aparece
no feed do YouTube (no painel) e escolha com um clique — troca a miniatura do vídeo e, se já publicado, no YouTube.

Usa o mesmo desenho das miniaturas do render (render/thumbnail.make_thumbnail) e as escolhas de foto/texto do
teste A/B dos vídeos longos (longform). Cada variação muda foto, texto e layout — nada de miniaturas em série.
"""
from __future__ import annotations

import logging
import random
import shutil
import subprocess
from pathlib import Path
from typing import Any

from sqlmodel import select

from .config import MEDIA_DIR
from .db import session
from .jobs import JobContext, handler
from .models import Account, Channel, Publication, Script, Video

log = logging.getLogger("lidark.thumbstudio")
LAYOUTS = [0, 3, 6, 1, 2, 5, 9, 7, 4, 8]  # bits do variant: lado do texto, faixa, mascote, palavra destacada


def _rel(p: Path) -> str:
    return str(p.relative_to(MEDIA_DIR))


def _load(video_id: int) -> tuple[Video, Script, Channel]:
    with session() as s:
        v = s.get(Video, video_id)
        if not v:
            raise ValueError("vídeo não encontrado")
        return v, s.get(Script, v.script_id), s.get(Channel, v.channel_id)


def _frames(v: Video, n: int) -> list[Path]:
    """Sem fotos guardadas: tira quadros do próprio vídeo (20%, 45%, 70%)."""
    from .media import ffmpeg_exe
    src = MEDIA_DIR / v.path if v.path else None
    if not src or not src.exists():
        return []
    folder = src.parent / "studio"
    folder.mkdir(exist_ok=True)
    out = []
    dur = v.duration or 30
    for i, f in enumerate((0.2, 0.45, 0.7)[:n]):
        p = folder / f"frame_{i}.jpg"
        if not p.exists():
            try:
                subprocess.run([ffmpeg_exe(), "-y", "-ss", f"{dur * f:.2f}", "-i", str(src), "-frames:v", "1", "-q:v", "2", str(p)],
                               capture_output=True, timeout=60, check=False)
            except Exception as e:  # noqa: BLE001
                log.info("quadro do vídeo: %s", e)
        if p.exists():
            out.append(p)
    return out


def backgrounds(v: Video, sc: Script, n: int = 3) -> list[Path]:
    from .longform import _thumb_backgrounds
    try:
        bgs = _thumb_backgrounds(v, sc, n)
    except Exception as e:  # noqa: BLE001
        log.info("fotos da miniatura: %s", e)
        bgs = []
    if len(bgs) < n:  # imagens de IA ou de nota baixa também servem de fundo
        for im in sorted((v.assets or {}).get("images") or [], key=lambda x: -int(x.get("score") or 0)):
            p = Path(im.get("path") or "")
            if im.get("path") and p.exists() and p not in bgs:
                bgs.append(p)
            if len(bgs) >= n:
                break
    if not bgs:
        bgs = _frames(v, n)
    return bgs[:n]


def generate(video_id: int, count: int = 6, texts: list[str] | None = None, vision: bool = True,
             ctx: JobContext | None = None) -> list[dict[str, Any]]:
    from PIL import Image
    from .longform import subject_box, thumb_texts
    from .render.thumbnail import make_thumbnail
    v, sc, ch = _load(video_id)
    vertical = v.format == "short"
    say = ctx.log if ctx else log.info
    if ctx:
        ctx.update(0.05, "Escolhendo as fotos")
    bgs = backgrounds(v, sc, 3)
    pool = [t.strip()[:40] for t in (texts or []) if t and t.strip()]
    if len(pool) < 3:
        if ctx:
            ctx.update(0.2, "Criando textos de miniatura")
        pool += [t for t in thumb_texts(sc, 3) if t.upper() not in {p.upper() for p in pool}]
    pool = list(dict.fromkeys(pool))[:4] or [(sc.thumbnail_text or sc.title)[:40]]
    boxes: dict[Path, Any] = {}
    if vision:
        for i, b in enumerate(bgs):
            if ctx:
                ctx.update(0.3 + 0.2 * i / max(1, len(bgs)), "Achando o assunto principal das fotos")
            boxes[b] = subject_box(b)
    folder = MEDIA_DIR / ch.slug / f"video_{video_id}" / "studio"
    folder.mkdir(parents=True, exist_ok=True)
    rng = random.Random(video_id * 7 + len(list(folder.glob("v*.jpg"))))
    layouts = LAYOUTS[:]
    rng.shuffle(layouts)
    stamp = rng.randint(1000, 9999)
    out: list[dict[str, Any]] = []
    for i in range(max(1, min(count, 9))):
        bg = bgs[i % len(bgs)] if bgs else None
        text = pool[i % len(pool)]
        box = boxes.get(bg) if bg else None
        variant = layouts[i % len(layouts)]
        if not box and variant % 5 != 4 and variant & 1 == 0:
            variant = 4  # sem saber onde está o assunto, o mascote fica de fora (não cobre o principal)
        p = folder / f"v{stamp}_{i}.jpg"
        try:
            make_thumbnail(Image.open(bg).convert("RGB") if bg else None, text, ch.theme or {}, p, vertical,
                           variant=variant, subject=box, ring=bool(box) and i % 2 == 0)
        except Exception as e:  # noqa: BLE001
            say(f"Variação {i + 1} falhou: {e}")
            continue
        out.append({"path": _rel(p), "text": text, "variant": variant, "photo": bg.name if bg else "",
                    "ring": bool(box) and i % 2 == 0})
        if ctx:
            ctx.update(0.5 + 0.45 * (i + 1) / count, f"Miniatura {i + 1}/{count}: “{text}”")
    with session() as s:
        db = s.get(Video, video_id)
        st = dict((db.assets or {}).get("thumb_studio") or {})
        st["options"] = (out + [o for o in st.get("options", []) if (MEDIA_DIR / o["path"]).exists()])[:18]
        db.assets = {**(db.assets or {}), "thumb_studio": st}
        s.add(db)
        s.commit()
    return out


def state(video_id: int) -> dict[str, Any]:
    v, sc, ch = _load(video_id)
    st = (v.assets or {}).get("thumb_studio") or {}
    opts = [o for o in st.get("options", []) if (MEDIA_DIR / o["path"]).exists()]
    ab = [{"path": p, "text": "", "variant": -1, "ab": True} for p in (v.assets or {}).get("thumbs_ab") or []
          if (MEDIA_DIR / p).exists()]
    with session() as s:
        pub = s.exec(select(Publication).where(Publication.video_id == video_id, Publication.status == "published")).first()
    return {"video": {"id": v.id, "format": v.format, "status": v.status, "thumbnail_path": v.thumbnail_path,
                      "duration": v.duration, "title": sc.title, "thumbnail_text": sc.thumbnail_text},
            "channel": {"id": ch.id, "name": ch.name, "avatar_url": ch.avatar_url, "handle": ch.handle,
                        "subscribers": (ch.stats or {}).get("subscribers"), "thumbs_blocked": ch.thumbs_blocked},
            "original": st.get("original") or v.thumbnail_path, "picked": st.get("picked"), "history": st.get("history", []),
            "options": opts, "ab": ab,
            "published": {"url": pub.url, "external_id": pub.external_id, "views": None} if pub else None}


def pick(video_id: int, path: str, youtube: bool = True) -> dict[str, Any]:
    """Escolhe a miniatura: vira a miniatura do vídeo (próximo envio) e, se já publicado, é enviada ao YouTube."""
    from .models import now
    v, sc, ch = _load(video_id)
    src = (MEDIA_DIR / path).resolve()
    if not src.is_file() or MEDIA_DIR.resolve() not in src.parents:
        raise ValueError("miniatura não encontrada")
    with session() as s:
        db = s.get(Video, video_id)
        st = dict((db.assets or {}).get("thumb_studio") or {})
        if not st.get("original") and db.thumbnail_path and (MEDIA_DIR / db.thumbnail_path).exists():
            orig = MEDIA_DIR / db.thumbnail_path
            keep = orig.parent / "thumb_original.jpg"
            if not keep.exists():
                shutil.copyfile(orig, keep)
            st["original"] = _rel(keep)
        st["picked"] = path
        st["history"] = [*st.get("history", []), {"at": now().isoformat(), "path": path, "before": db.thumbnail_path}][-20:]
        db.thumbnail_path = path
        db.assets = {**(db.assets or {}), "thumb_studio": st}
        s.add(db)
        s.commit()
        pub = s.exec(select(Publication).where(Publication.video_id == video_id, Publication.status == "published",
                                               Publication.platform == "youtube")).first()
        acc = s.get(Account, pub.account_id) if pub else None
    out: dict[str, Any] = {"thumbnail_path": path, "youtube": None}
    if youtube and pub and pub.external_id and acc and acc.credentials:
        out["youtube"] = set_on_youtube(acc, pub.external_id, src, ch)
    return out


def set_on_youtube(acc: Account, external_id: str, path: Path, ch: Channel) -> dict[str, Any]:
    from googleapiclient.http import MediaFileUpload
    from .publish import _set_thumbs_blocked, _yt_client, _yt_creds
    try:
        yt = _yt_client(_yt_creds(acc))
        yt.thumbnails().set(videoId=external_id, media_body=MediaFileUpload(str(path), mimetype="image/jpeg")).execute()
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "verif" in msg.lower() or "forbidden" in msg.lower():
            _set_thumbs_blocked(ch.id, True)
            msg = "o canal precisa ser verificado por telefone em youtube.com/verify para aceitar miniaturas"
        return {"ok": False, "error": msg[:300]}
    if ch.thumbs_blocked:
        _set_thumbs_blocked(ch.id, False)
    return {"ok": True}


def restore(video_id: int) -> dict[str, Any]:
    v, _, _ = _load(video_id)
    orig = ((v.assets or {}).get("thumb_studio") or {}).get("original")
    if not orig:
        return {"thumbnail_path": v.thumbnail_path}
    return pick(video_id, orig)


@handler("thumb_studio")
def job_thumb_studio(ctx: JobContext) -> dict:
    p = ctx.payload
    opts = generate(ctx.ref_id, int(p.get("count") or 6), p.get("texts") or None, bool(p.get("vision", True)), ctx)
    res: dict[str, Any] = {"options": opts}
    if p.get("auto_pick") and opts:  # texto novo vindo do laboratório viral: já usa a 1ª versão com ele
        res["picked"] = pick(ctx.ref_id, opts[0]["path"], youtube=bool(p.get("youtube")))
        ctx.log(f"Miniatura trocada: {opts[0]['path']}")
    return res
