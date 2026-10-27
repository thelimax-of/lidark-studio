"""Importa vídeos já publicados de um canal do YouTube (sem login), para não repetir pautas
e para o sistema aprender com as métricas reais (views, curtidas, comentários)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlmodel import select

from .db import session
from .jobs import JobContext, handler
from .models import Account, MetricSnapshot, Publication

log = logging.getLogger("lidark.importer")


def _ydl(opts: dict):
    import yt_dlp
    base = {"quiet": True, "no_warnings": True, "skip_download": True, "ignoreerrors": True}
    try:
        return yt_dlp.YoutubeDL({**base, "js_runtimes": {"node": {}}, **opts})
    except Exception:  # noqa: BLE001 — versões antigas não aceitam js_runtimes
        return yt_dlp.YoutubeDL({**base, **opts})


@handler("import_youtube")
def job_import_youtube(ctx: JobContext) -> dict:
    handle = ctx.payload["handle"].strip()
    base = handle if handle.startswith("http") else f"https://www.youtube.com/{handle if handle.startswith('@') else '@' + handle}"
    ctx.update(0.05, "Listando vídeos do canal")
    entries = []
    with _ydl({"extract_flat": "in_playlist"}) as y:
        for tab in ("shorts", "videos"):
            info = y.extract_info(f"{base}/{tab}", download=False) or {}
            for e in info.get("entries") or []:
                if e and e.get("id"):
                    entries.append((tab, e))
    ctx.log(f"{len(entries)} vídeos encontrados")
    with session() as s:
        acc = s.exec(select(Account).where(Account.channel_id == ctx.channel_id, Account.platform == "youtube")).first()
        if not acc:
            acc = Account(channel_id=ctx.channel_id, platform="youtube", display_name=f"{handle} (importado, sem login)",
                          external_id=handle)
            s.add(acc)
            s.commit()
            s.refresh(acc)
        acc_id = acc.id
    imported = 0
    for n, (tab, e) in enumerate(entries):
        ctx.update(0.1 + 0.85 * n / max(1, len(entries)), f"Lendo métricas {n + 1}/{len(entries)}")
        with _ydl({}) as y:
            d = y.extract_info(f"https://www.youtube.com/watch?v={e['id']}", download=False) or {}
        if not d:
            continue
        up = d.get("upload_date")
        when = datetime.strptime(up, "%Y%m%d").replace(tzinfo=timezone.utc) if up else None
        with session() as s:
            pub = s.exec(select(Publication).where(Publication.platform == "youtube", Publication.external_id == e["id"])).first()
            if not pub:
                pub = Publication(channel_id=ctx.channel_id, video_id=None, account_id=acc_id, platform="youtube",
                                  status="published", external_id=e["id"])
                imported += 1
            pub.title = d.get("title") or e.get("title") or ""
            pub.description = d.get("description") or ""
            pub.url = d.get("webpage_url") or f"https://www.youtube.com/watch?v={e['id']}"
            pub.published_at = when
            pub.duration = float(d.get("duration") or 0)
            pub.thumbnail_url = d.get("thumbnail") or ""
            s.add(pub)
            s.commit()
            s.refresh(pub)
            s.add(MetricSnapshot(publication_id=pub.id, channel_id=ctx.channel_id, platform="youtube",
                                 views=int(d.get("view_count") or 0), likes=int(d.get("like_count") or 0),
                                 comments=int(d.get("comment_count") or 0),
                                 raw={"source": "public", "format": "short" if tab == "shorts" else "long"}))
            s.commit()
    ctx.log(f"{imported} novos vídeos importados")
    return {"found": len(entries), "imported": imported}
