"""API da publicação 2: cota do YouTube, idiomas (localizations), legendas oficiais, espaço entre canais irmãos,
checklist do YouTube Studio e aprovação pelo celular. Tudo sob /api/publish2."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from sqlmodel import select

from . import jobs, notify, quota, studio_checklist
from .channels import publish_prefs, set_publish_prefs
from .db import session
from .models import Channel, Publication, Video

router = APIRouter(prefix="/api/publish2")


def _channel(cid: int) -> Channel:
    with session() as s:
        ch = s.get(Channel, cid)
    if not ch:
        raise HTTPException(404, f"Canal {cid} não encontrado")
    return ch


def _pub(pid: int) -> Publication:
    with session() as s:
        p = s.get(Publication, pid)
    if not p:
        raise HTTPException(404, "Publicação não encontrada")
    return p


# ================================================================ cota do YouTube

@router.get("/quota")
def quota_status():
    return quota.status()


@router.put("/quota/settings")
def quota_settings(data: dict[str, Any]):
    return quota.save_settings(data)


# ================================================================ preferências por canal

@router.get("/prefs/{cid}")
def get_prefs(cid: int):
    _channel(cid)
    from .posting_times import sister_gap
    return {**publish_prefs(cid), "sister_gap_hours": sister_gap()}


@router.put("/prefs/{cid}")
def put_prefs(cid: int, data: dict[str, Any]):
    _channel(cid)
    if "sister_gap_hours" in data:  # global (vale para todos os canais)
        import json
        from .channels import PUBLISH_PREFS_PATH, _all_publish_prefs
        d = _all_publish_prefs()
        d["_global"] = {**(d.get("_global") or {}), "sister_gap_hours": max(0.0, min(6.0, float(data["sister_gap_hours"])))}
        PUBLISH_PREFS_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    out = set_publish_prefs(cid, data)
    from .posting_times import sister_gap
    return {**out, "sister_gap_hours": sister_gap()}


# ================================================================ horário: canais irmãos

@router.get("/slot-check")
def slot_check(channel_id: int, when: str, format: str = "short"):  # noqa: A002
    """O horário escolhido bate com outro post do canal ou de um canal irmão (< 2 h)? Sugere o próximo livre."""
    from . import posting_times
    ch = _channel(channel_id)
    try:
        t = datetime.fromisoformat(when.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, "horário inválido")
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    why = posting_times.conflict(ch, t, format)
    nxt = posting_times.next_free(ch, t, format) if why else None
    return {"conflict": why, "suggestion": nxt.isoformat() if nxt else None,
            "sister_gap_hours": posting_times.sister_gap()}


# ================================================================ idiomas e legendas

@router.post("/localize/{pid}")
def localize_pub(pid: int, data: Optional[dict[str, Any]] = None):
    """Título/descrição em inglês e espanhol num vídeo já publicado. Por padrão só simula (dry_run)."""
    from .localize import push_existing
    _pub(pid)
    return push_existing(pid, dry_run=(data or {}).get("dry_run", True) is not False)


@router.get("/captions/{video_id}/srt", response_class=PlainTextResponse)
def captions_srt(video_id: int, lang: str = "pt-BR"):
    """O .srt que seria enviado (pt-BR sem custo; en/es usam uma tradução em cache)."""
    from .localize import build_srts
    r = build_srts(video_id, [lang])
    srt = (r.get("srt") or {}).get(lang)
    if not srt:
        raise HTTPException(404, r.get("error") or "sem legenda")
    return PlainTextResponse(srt, media_type="text/plain; charset=utf-8")


@router.post("/captions/{pid}")
def captions_pub(pid: int, data: Optional[dict[str, Any]] = None):
    """Envia (ou, com dry_run, só gera os .srt de) as legendas oficiais de uma publicação. Envio real vai pela fila."""
    p = _pub(pid)
    data = data or {}
    langs = data.get("langs") or publish_prefs(p.channel_id).get("captions_langs")
    if data.get("dry_run", True) is not False:
        from .localize import upload_captions
        return upload_captions(pid, langs, dry_run=True)
    j = jobs.enqueue("upload_captions", title=f"Legendas oficiais: {p.title.replace('#Shorts', '').strip()[:60]}",
                     channel_id=p.channel_id, ref_id=pid, payload={"langs": langs})
    return jobs.job_dict(j)


# ================================================================ checklist do YouTube Studio

@router.get("/checklist")
def checklist_summary(channel_id: Optional[int] = None):
    return {str(k): v for k, v in studio_checklist.summary(channel_id).items()}


@router.get("/checklist/{pid}")
def checklist_get(pid: int):
    try:
        return studio_checklist.build(pid)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/checklist/by-video/{video_id}")
def checklist_by_video(video_id: int):
    with session() as s:
        p = s.exec(select(Publication).where(Publication.video_id == video_id, Publication.status == "published",
                                             Publication.platform == "youtube")).first()
    if not p:
        raise HTTPException(404, "Vídeo ainda não publicado")
    return studio_checklist.build(p.id)


@router.post("/checklist/{pid}/toggle")
def checklist_toggle(pid: int, data: dict[str, Any]):
    try:
        return studio_checklist.toggle(pid, str(data.get("item") or ""), bool(data.get("done", True)))
    except ValueError as e:
        raise HTTPException(404, str(e))


# ================================================================ aprovação pelo celular

@router.get("/approval")
def approval_status():
    return {**notify.approval_status(), "items": notify.pending_approvals()}


@router.post("/approval/start")
def approval_start():
    return notify.start_lan_server()


@router.post("/approval/scan")
def approval_scan():
    return {"sent": notify.scan_approvals()}


@router.post("/approval/{kind}/{oid}/{action}")
def approval_decide(kind: str, oid: int, action: str):
    """Mesma decisão dos botões do celular, pelo painel (local, sem token)."""
    try:
        return notify.decide(kind, oid, action, source="painel")
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/video/{video_id}/publication")
def video_publication(video_id: int):
    with session() as s:
        v = s.get(Video, video_id)
        p = s.exec(select(Publication).where(Publication.video_id == video_id, Publication.status == "published")).first() if v else None
    return {"publication_id": p.id if p else None}
