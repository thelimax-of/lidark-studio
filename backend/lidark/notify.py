"""Avisos no celular via ntfy (app grátis, sem cadastro): o sistema publica num tópico secreto e o celular assina.

Avisa: vídeo pronto / para revisar, falhas, publicação no ar, comentários novos e um resumo diário.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from . import config

log = logging.getLogger("lidark.notify")


def topic() -> str:
    t = config.get("ntfy_topic") or ""
    if not t:  # gera um tópico secreto (quem souber o nome recebe os avisos — por isso é aleatório)
        t = f"lidark-{secrets.token_urlsafe(9).replace('_', '').replace('-', '').lower()}"
        config.save_settings({"ntfy_topic": t})
    return t


def enabled(event: str = "") -> bool:
    if not config.get("ntfy_enabled"):
        return False
    return not event or event not in (config.get("ntfy_muted") or [])


def send(title: str, message: str, *, event: str = "", tags: list[str] | None = None, priority: int = 3,
         click: str = "", force: bool = False) -> bool:
    if not force and not enabled(event):
        return False
    body: dict[str, Any] = {"topic": topic(), "title": title[:120], "message": message[:3500],
                            "tags": tags or [], "priority": priority}
    if click:
        body["click"] = click
    try:
        r = httpx.post(config.get("ntfy_server") or "https://ntfy.sh", json=body, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("aviso não enviado: %s", e)
        return False


def safe(*a, **kw) -> None:
    """Nunca deixa um aviso derrubar a tarefa que o disparou."""
    try:
        send(*a, **kw)
    except Exception as e:  # noqa: BLE001
        log.warning("aviso: %s", e)


# ---------------------------------------------------------------- resumo diário

def daily_summary() -> str:
    from sqlmodel import func, select
    from .db import session
    from .models import Channel, Comment, Idea, Job, Publication, Video
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    lines = []
    with session() as s:
        for ch in s.exec(select(Channel)).all():
            made = s.exec(select(func.count()).select_from(Video).where(Video.channel_id == ch.id, Video.created_at >= since,
                                                                        Video.status.in_(["ready", "review", "published"]))).one()
            pubs = s.exec(select(Publication).where(Publication.channel_id == ch.id, Publication.status == "published",
                                                    Publication.published_at >= since)).all()
            review = s.exec(select(func.count()).select_from(Video).where(Video.channel_id == ch.id, Video.status == "review")).one()
            ideas = s.exec(select(func.count()).select_from(Idea).where(Idea.channel_id == ch.id, Idea.status.in_(["new", "approved"]),
                                                                        Idea.fact_status == "verified")).one()
            com = s.exec(select(func.count()).select_from(Comment).where(Comment.channel_id == ch.id, Comment.status == "new")).one()
            subs = (ch.stats or {}).get("subscribers", 0)
            part = [f"▸ {ch.name} · {subs} inscritos",
                    f"  {made} vídeo(s) produzido(s) · {len(pubs)} publicado(s)" + (f" · {review} para revisar" if review else ""),
                    f"  {ideas} pauta(s) confirmada(s) em estoque" + (f" · {com} comentário(s) para responder" if com else "")]
            for p in pubs[:3]:
                part.append(f"  ✓ {p.title.replace('#Shorts', '').strip()[:60]}")
            lines.append("\n".join(part))
        fails = s.exec(select(Job).where(Job.status == "failed", Job.finished_at >= since)).all()
    if fails:
        lines.append(f"⚠ {len(fails)} tarefa(s) falharam nas últimas 24 h: " + ", ".join(sorted({j.kind for j in fails})))
    return "\n\n".join(lines) or "Sem atividade nas últimas 24 h."


def send_daily() -> None:
    safe("Resumo do dia · Lidark", daily_summary(), event="daily", tags=["bar_chart"], priority=2)
