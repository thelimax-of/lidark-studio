"""API do crescimento automático: notificações (sino), laboratório viral, radar de tendências ao vivo,
estúdio de miniaturas e piloto automático de crescimento."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from . import autogrowth, jobs, notify, radar, thumbstudio, viral
from .db import session
from .models import Channel, Idea, Job

router = APIRouter(prefix="/api")


def _channel(cid: int) -> Channel:
    with session() as s:
        ch = s.get(Channel, cid)
    if not ch:
        raise HTTPException(404, f"Canal {cid} não encontrado")
    return ch


# ================================================================ notificações

@router.get("/notifications")
def notifications(limit: int = 30, unread: bool = False, kind: str = "", channel_id: Optional[int] = None):
    return notify.list_items(limit, unread, kind, channel_id)


@router.post("/notifications/read")
def notifications_read(data: dict[str, Any]):
    n = notify.mark_read(data.get("ids") or [], bool(data.get("all")))
    return {"ok": True, "updated": n, "unread": notify.list_items(1)["unread"]}


# ================================================================ laboratório viral

@router.get("/viral/queue")
def viral_queue(channel_id: Optional[int] = None, limit: int = 30):
    return viral.queue(channel_id, max(1, min(limit, 100)))


@router.get("/viral/script/{sid}")
def viral_script(sid: int):
    try:
        return viral.analyze(script_id=sid)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/viral/video/{vid}")
def viral_video(vid: int):
    try:
        return viral.analyze(video_id=vid)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/viral/script/{sid}/suggest")
def viral_suggest(sid: int):
    try:
        return {"suggestions": viral.suggest(script_id=sid)}
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(503, f"IA indisponível agora: {str(e)[:200]}")


@router.post("/viral/script/{sid}/apply")
def viral_apply(sid: int, data: dict[str, Any]):
    try:
        return viral.apply(sid, title=data.get("title"), thumbnail_text=data.get("thumbnail_text"), hook=data.get("hook"),
                           rethumb=bool(data.get("rethumb", True)), youtube=bool(data.get("youtube")))
    except ValueError as e:
        raise HTTPException(400, str(e))


# ================================================================ radar de tendências

def _radar_job(cid: int) -> Job | None:
    with session() as s:
        return s.exec(select(Job).where(Job.kind == "trend_radar", Job.channel_id == cid,
                                        Job.status.in_(("queued", "running")))).first()


@router.get("/trends")
def trends(channel_id: int):
    ch = _channel(channel_id)
    snap = radar.snapshot(ch.id)
    j = _radar_job(ch.id)
    return {**snap, "channel_id": ch.id, "keywords": snap.get("keywords") or (ch.radar or {}).get("keywords") or [],
            "ideas": radar.trend_ideas(ch.id, 30), "job": jobs.job_dict(j) if j else None}


@router.get("/trends/all")
def trends_all(top: int = 5):
    with session() as s:
        chans = s.exec(select(Channel).order_by(Channel.id)).all()
    out = []
    for ch in chans:
        snap = radar.snapshot(ch.id)
        out.append({"channel_id": ch.id, "name": ch.name, "at": snap.get("at"),
                    "top": (snap.get("ranked") or [])[:max(1, min(top, 20))],
                    "ideas_new": sum(1 for i in radar.trend_ideas(ch.id, 30) if i["status"] in ("new", "approved"))})
    return out


@router.post("/trends/{cid}/refresh")
def trends_refresh(cid: int, data: Optional[dict[str, Any]] = None):
    ch = _channel(cid)
    j = _radar_job(cid)
    if j:
        return jobs.job_dict(j)
    data = data or {}
    payload: dict[str, Any] = {"count": int(data.get("count") or 6)}
    if data.get("ideas") is False:
        payload["ideas"] = False
    return jobs.job_dict(jobs.enqueue("trend_radar", title=f"Radar de tendências: {ch.name}", channel_id=cid, payload=payload))


@router.post("/trends/{cid}/idea")
def trends_idea(cid: int, data: dict[str, Any]):
    """Transforma um item do radar numa pauta (a IA pesquisa, checa os fatos e dá nota antes de entrar na fila)."""
    _channel(cid)
    title = str(data.get("title") or "").strip()
    if not title:
        raise HTTPException(400, "Informe o assunto")
    evidence = str(data.get("evidence") or "")[:280]
    with session() as s:
        idea = Idea(channel_id=cid, title=title[:200], angle=str(data.get("angle") or ""), format=data.get("format") or "short",
                    summary=str(data.get("summary") or title), origin="trend",
                    tags=[f"🔥 {evidence}" if evidence else "🔥 radar", f"urgência: {data.get('urgency') or 'alta'}"])
        s.add(idea)
        s.commit()
        s.refresh(idea)
    j = jobs.enqueue("manual_idea", title=f"Validar pauta de tendência: {idea.title}", channel_id=cid, ref_id=idea.id)
    return {"idea_id": idea.id, "job_id": j.id}


# ================================================================ estúdio de miniaturas

@router.get("/thumbs/{vid}")
def thumbs_state(vid: int):
    try:
        return thumbstudio.state(vid)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/thumbs/{vid}/generate")
def thumbs_generate(vid: int, data: Optional[dict[str, Any]] = None):
    data = data or {}
    st = thumbs_state(vid)
    texts = [str(t)[:40] for t in (data.get("texts") or []) if str(t).strip()][:4]
    j = jobs.enqueue("thumb_studio", title=f"Estúdio de miniaturas: {viral.clean_title(st['video']['title'])[:60]}",
                     channel_id=st["channel"]["id"], ref_id=vid,
                     payload={"count": max(2, min(int(data.get("count") or 6), 9)), "texts": texts,
                              "vision": bool(data.get("vision", True))})
    return jobs.job_dict(j)


@router.post("/thumbs/{vid}/pick")
def thumbs_pick(vid: int, data: dict[str, Any]):
    try:
        return thumbstudio.pick(vid, str(data.get("path") or ""), youtube=bool(data.get("youtube", True)))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/thumbs/{vid}/restore")
def thumbs_restore(vid: int):
    try:
        return thumbstudio.restore(vid)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ================================================================ piloto automático de crescimento

@router.get("/autogrowth")
def autogrowth_overview():
    return {"automations": autogrowth.AUTOMATIONS, "limits": autogrowth.LIMITS, "channels": autogrowth.overview()}


@router.put("/autogrowth/{cid}")
def autogrowth_settings(cid: int, data: dict[str, Any]):
    _channel(cid)
    return autogrowth.set_settings(cid, data)


@router.get("/autogrowth/actions")
def autogrowth_actions(channel_id: Optional[int] = None, limit: int = 50):
    return autogrowth.actions(channel_id, limit)


@router.post("/autogrowth/run")
def autogrowth_run():
    return {"started": autogrowth.run_async()}


@router.post("/autogrowth/retitle")
def autogrowth_retitle(data: dict[str, Any]):
    """Troca manual de título de um vídeo publicado (registrada no histórico do piloto, com antes/depois)."""
    title = str(data.get("title") or "").strip()
    if not title or not data.get("publication_id"):
        raise HTTPException(400, "Informe a publicação e o título novo")
    return autogrowth.retitle_published(None, title, "troca manual", publication_id=int(data["publication_id"]))
