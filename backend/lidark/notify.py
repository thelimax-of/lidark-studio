"""Avisos no celular via ntfy (app grátis, sem cadastro): o sistema publica num tópico secreto e o celular assina.

Avisa: vídeo pronto / para revisar, falhas, publicação no ar, comentários novos e um resumo diário.

Central de notificações do painel: todo aviso também vira uma linha na tabela Notification (mesmo com o ntfy
desligado) e sai ao vivo no /api/events como evento "notification" (o sino da barra de cima).
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel, select

from . import config
from .models import now

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
    if event != "daily":  # o resumo diário é só do celular; o resto também vai para o sino do painel
        try:
            record(event or "info", title, message, link=click or EVENT_LINKS.get(event, ""))
        except Exception as e:  # noqa: BLE001
            log.warning("notificação não registrada: %s", e)
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


# ================================================================ central de notificações (sino do painel)

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # failed | ready | review | published | comments | breakout | flop | quota | ypp | autopilot | info
    kind: str = Field(default="info", index=True)
    title: str = ""
    body: str = Field(default="", sa_column=Column(Text))
    link: str = ""  # rota do painel (/videos) ou URL externa (YouTube)
    channel_id: Optional[int] = Field(default=None, index=True)
    key: str = Field(default="", index=True)  # evita repetir o mesmo aviso (ex.: "breakout:123")
    read: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=now, index=True)


EVENT_LINKS = {"failed": "/fila", "ready": "/videos", "review": "/videos", "published": "/publicacao",
               "comments": "/comentarios"}
_ready = False


def _ensure() -> None:
    """Cria a tabela na hora se o banco foi criado antes deste módulo ser carregado."""
    global _ready
    if not _ready:
        from .db import engine
        Notification.__table__.create(engine, checkfirst=True)
        _ready = True


def item(n: Notification) -> dict[str, Any]:
    at = n.created_at
    if at is not None and at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "link": n.link,
            "created_at": at.isoformat() if at else None, "read": bool(n.read), "channel_id": n.channel_id}


def record(kind: str, title: str, body: str = "", *, link: str = "", channel_id: int | None = None,
           key: str = "") -> dict[str, Any] | None:
    """Grava a notificação e manda ao vivo para o painel. Com `key`, a mesma notificação nunca se repete."""
    from .db import session
    _ensure()
    with session() as s:
        if key and s.exec(select(Notification).where(Notification.key == key)).first():
            return None
        n = Notification(kind=kind[:30], title=title[:200], body=(body or "")[:4000], link=(link or "")[:500],
                         channel_id=channel_id, key=key[:200])
        s.add(n)
        s.commit()
        s.refresh(n)
        d = item(n)
    try:
        from .jobs import bus
        bus.publish("notification", d)
    except Exception:  # noqa: BLE001
        pass
    return d


def exists(key: str) -> bool:
    from .db import session
    _ensure()
    with session() as s:
        return s.exec(select(Notification.id).where(Notification.key == key)).first() is not None


def push(kind: str, title: str, body: str = "", *, link: str = "", channel_id: int | None = None, key: str = "",
         phone: bool = True, tags: list[str] | None = None, priority: int = 3) -> dict[str, Any] | None:
    """Notificação do painel + (se ligado) aviso no celular. Nunca levanta erro."""
    try:
        d = record(kind, title, body, link=link, channel_id=channel_id, key=key)
    except Exception as e:  # noqa: BLE001
        log.warning("notificação: %s", e)
        return None
    if d and phone and enabled(kind):
        msg: dict[str, Any] = {"topic": topic(), "title": title[:120], "message": (body or title)[:3500],
                               "tags": tags or [], "priority": priority}
        if link.startswith("http"):
            msg["click"] = link
        try:
            httpx.post(config.get("ntfy_server") or "https://ntfy.sh", json=msg, timeout=15)
        except Exception as e:  # noqa: BLE001
            log.warning("aviso não enviado: %s", e)
    return d


def list_items(limit: int = 30, unread_only: bool = False, kind: str = "", channel_id: int | None = None) -> dict[str, Any]:
    from sqlmodel import func
    from .db import session
    _ensure()
    with session() as s:
        q = select(Notification)
        if unread_only:
            q = q.where(Notification.read == False)  # noqa: E712
        if kind:
            q = q.where(Notification.kind.in_(kind.split(",")))
        if channel_id:
            q = q.where(Notification.channel_id == channel_id)
        rows = s.exec(q.order_by(Notification.id.desc()).limit(max(1, min(limit, 500)))).all()
        unread = s.exec(select(func.count()).select_from(Notification).where(Notification.read == False)).one()  # noqa: E712
    return {"items": [item(n) for n in rows], "unread": int(unread)}


def mark_read(ids: list[int] | None = None, all_: bool = False) -> int:
    from sqlalchemy import update
    from .db import session
    _ensure()
    q = update(Notification).where(Notification.read == False)  # noqa: E712
    if not all_:
        if not ids:
            return 0
        q = q.where(Notification.id.in_([int(i) for i in ids]))
    with session() as s:
        n = s.exec(q.values(read=True)).rowcount
        s.commit()
    return int(n or 0)


def prune(days: int = 60) -> None:
    """Notificações lidas com mais de 60 dias saem do banco."""
    from sqlalchemy import delete
    from .db import session
    _ensure()
    with session() as s:
        s.exec(delete(Notification).where(Notification.created_at < datetime.now(timezone.utc) - timedelta(days=days),
                                          Notification.read == True))  # noqa: E712
        s.commit()


# ---------------------------------------------------------------- varredura (o que não passa pelo send)

def scan_jobs(minutes: int = 15) -> int:
    """Avisos que nascem na fila: IA sem cota (tarefas adiadas) e falhas de tipos que não avisam pelo ntfy."""
    from .db import session
    from .jobs import NOTIFY_FAILS
    from .models import Job
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    n = 0
    with session() as s:
        waiting = s.exec(select(Job).where(Job.status == "queued", Job.stage.like("Sem cota de IA%"))).all()
        failed = s.exec(select(Job).where(Job.status == "failed", Job.finished_at >= since)).all()
    if waiting:
        hour = datetime.now().strftime("%Y-%m-%d %H")
        names = ", ".join(sorted({j.title[:50] for j in waiting})[:5])
        n += bool(record("quota", f"IA sem cota: {len(waiting)} tarefa(s) esperando",
                         f"Gemini/GLM sem cota agora — as tarefas tentam de novo sozinhas a cada 20 min. {names}",
                         link="/fila", key=f"quota:{hour}"))
    quiet = NOTIFY_FAILS | {"collect_metrics", "fetch_comments", "verify_idea", "score_idea", "seed_comment"}
    for j in failed:
        if j.kind in quiet:
            continue  # já avisados pelo send() (ou rotineiros demais para o sino)
        first = (j.error or "").split("\n")[0][:300]
        n += bool(record("failed", f"Falhou: {j.title[:80]}", first, link="/fila", channel_id=j.channel_id,
                         key=f"jobfail:{j.id}"))
    return n
