"""API REST do painel."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
import unicodedata
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlmodel import Session, func, select
from sse_starlette.sse import EventSourceResponse

from . import config, jobs, llm
from .db import get_session
from .models import (Account, Channel, Idea, Insight, Job, MetricSnapshot, Publication, Script, Video, now)

router = APIRouter(prefix="/api")


def slugify(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "canal"


def _get(s: Session, model, id_: int):
    obj = s.get(model, id_)
    if not obj:
        raise HTTPException(404, f"{model.__name__} {id_} não encontrado")
    return obj


def _patch(obj, data: dict[str, Any], skip=("id", "created_at")) -> None:
    fields = type(obj).model_fields
    for k, v in data.items():
        if k in skip or k not in fields:
            continue
        cur = getattr(obj, k, None)
        if isinstance(v, str) and (isinstance(cur, datetime) or "datetime" in str(fields[k].annotation)):
            try:  # datas chegam do painel como texto ISO
                v = datetime.fromisoformat(v.replace("Z", "+00:00")) if v else None
            except ValueError:
                continue
        setattr(obj, k, v)


# ================================================================ sistema

@router.get("/health")
def health():
    from .media import ffmpeg_info
    s = config.load_settings()
    return {
        "ok": True, "version": "2.0.0",
        "llm": {"gemini_keys": len(s["gemini_api_keys"]), "glm": bool(s["glm_api_key"]), "order": s["llm_order"],
                "usage": llm.usage_stats},
        "ffmpeg": ffmpeg_info(),
    }


@router.get("/settings")
def get_settings():
    return config.public_settings()


@router.put("/settings")
def put_settings(patch: dict[str, Any]):
    config.save_settings(patch)
    return config.public_settings()


@router.post("/settings/test-llm")
def test_llm(provider: str = "gemini"):
    try:
        r = llm.complete("Responda apenas: OK", prefer=provider, temperature=0)
        return {"ok": True, "provider": r.provider, "model": r.model, "text": r.text[:100]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


@router.get("/events")
async def events(request: Request):
    q = jobs.bus.subscribe()

    async def gen():
        try:
            yield {"event": "hello", "data": "{}"}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    item = await asyncio.wait_for(q.get(), timeout=15)
                    yield {"event": item["event"], "data": json.dumps(item["data"], default=str)}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
        finally:
            jobs.bus.unsubscribe(q)

    return EventSourceResponse(gen())


# ================================================================ canais

@router.get("/channels")
def list_channels(s: Session = Depends(get_session)):
    out = []
    for ch in s.exec(select(Channel).order_by(Channel.id)).all():
        d = ch.model_dump()
        acc = s.exec(select(Account).where(Account.channel_id == ch.id, Account.platform == "youtube")).first()
        d["connected"] = bool(acc and acc.credentials)
        d["counts"] = {
            "ideas": s.exec(select(func.count()).select_from(Idea).where(Idea.channel_id == ch.id, Idea.status == "new")).one(),
            "scripts": s.exec(select(func.count()).select_from(Script).where(Script.channel_id == ch.id, Script.status != "produced")).one(),
            "videos": s.exec(select(func.count()).select_from(Video).where(Video.channel_id == ch.id, Video.status == "ready")).one(),
            "published": s.exec(select(func.count()).select_from(Publication).where(Publication.channel_id == ch.id, Publication.status == "published")).one(),
        }
        out.append(d)
    return out


@router.get("/channels/{cid}")
def get_channel(cid: int, s: Session = Depends(get_session)):
    return _get(s, Channel, cid)


@router.put("/channels/{cid}")
def update_channel(cid: int, data: dict[str, Any], s: Session = Depends(get_session)):
    ch = _get(s, Channel, cid)
    _patch(ch, data, skip=("id", "created_at", "slug", "youtube_id", "synced_at", "stats", "setup_status",
                                "series", "playlists", "campaigns"))  # mantidos pelo próprio sistema
    s.add(ch)
    s.commit()
    s.refresh(ch)
    return ch


@router.delete("/channels/{cid}")
def delete_channel(cid: int, s: Session = Depends(get_session)):
    ch = _get(s, Channel, cid)
    s.delete(ch)
    s.commit()
    return {"ok": True}


@router.post("/youtube/connect")
def youtube_connect(channel_id: Optional[int] = None):
    """Inicia o login do Google. Sem channel_id = adicionar canal novo; com = reconectar/vincular."""
    from . import publish
    return publish.start_connect("youtube", channel_id)


@router.get("/channels/{cid}/music")
def channel_music(cid: int, s: Session = Depends(get_session)):
    from .config import MUSIC_DIR
    from .music import AUDIO_EXT
    from .music import MOODS
    ch = _get(s, Channel, cid)
    d = MUSIC_DIR / ch.slug
    files = sorted(p for p in d.rglob("*") if p.suffix.lower() in AUDIO_EXT) if d.exists() else []
    return {"moods": [{"key": k, **v} for k, v in MOODS.items()],
            "files": [{"name": p.name, "size": p.stat().st_size, "mood": p.parent.name if p.parent != d else ""} for p in files]}


@router.post("/channels/{cid}/music")
async def channel_music_upload(cid: int, request: Request, s: Session = Depends(get_session)):
    from .config import MUSIC_DIR
    from .music import AUDIO_EXT
    from .music import MOODS
    ch = _get(s, Channel, cid)
    form = await request.form()
    mood = request.query_params.get("mood", "")
    d = MUSIC_DIR / ch.slug / (mood if mood in MOODS else "")
    d.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in form.getlist("files"):
        name = re.sub(r"[^\w\-. ()]", "_", f.filename or "faixa.mp3")
        if Path(name).suffix.lower() not in AUDIO_EXT:
            continue
        (d / name).write_bytes(await f.read())
        saved.append(name)
    return {"saved": saved}


@router.delete("/channels/{cid}/music/{name}")
def channel_music_delete(cid: int, name: str, mood: str = "", s: Session = Depends(get_session)):
    from .config import MUSIC_DIR
    from .music import MOODS
    ch = _get(s, Channel, cid)
    base = (MUSIC_DIR / ch.slug).resolve()
    folder = base / mood if mood in MOODS else base
    p = (folder / name).resolve()
    if p.parent == folder and p.exists():
        p.unlink()
    return {"ok": True}


@router.post("/channels/{cid}/sync")
def channel_sync(cid: int, s: Session = Depends(get_session)):
    ch = _get(s, Channel, cid)
    return jobs.job_dict(jobs.enqueue("setup_channel", title=f"Sincronizar: {ch.name}", channel_id=cid))


@router.post("/channels/{cid}/identity")
def channel_identity(cid: int, data: dict[str, Any] | None = None, s: Session = Depends(get_session)):
    ch = _get(s, Channel, cid)
    parts = (data or {}).get("parts", "all")
    label = {"all": "identidade completa", "visual": "novo visual", "text": "nicho e estilo editorial"}.get(parts, parts)
    return jobs.job_dict(jobs.enqueue("channel_identity", title=f"IA: {label} — {ch.name}", channel_id=cid,
                                      payload={"parts": parts}))


@router.post("/channels/{cid}/preview")
def channel_preview(cid: int, s: Session = Depends(get_session)):
    from .channels import render_preview
    _get(s, Channel, cid)
    return {"urls": render_preview(cid)}


@router.get("/mascots")
def mascots():
    from .render.characters import DEFAULT_COLORS, KINDS
    return [{"id": k, "label": v, "colors": DEFAULT_COLORS.get(k, ("#e9ba52", "#cd583a"))} for k, v in KINDS.items()]


@router.get("/mascots/{kind}.png")
def mascot_png(kind: str, color: str = "", accent: str = "", bg: str = "16473a"):
    from fastapi.responses import Response
    import io
    from .render.characters import preview
    img = preview(kind, ("#" + color) if color else None, ("#" + accent) if accent else None, 300, "#" + bg)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "PNG")
    return Response(buf.getvalue(), media_type="image/png", headers={"Cache-Control": "max-age=3600"})


@router.get("/fonts")
def fonts():
    from .channels import CAPTION_FONTS, FONTS
    return {"title": [{"file": k, "label": v} for k, v in FONTS.items()], "caption": CAPTION_FONTS}


# ================================================================ pautas

class IdeaIn(BaseModel):
    channel_id: int
    title: str
    angle: str = ""
    summary: str = ""
    format: str = "short"


@router.get("/ideas")
def list_ideas(channel_id: Optional[int] = None, status: Optional[str] = None, s: Session = Depends(get_session)):
    q = select(Idea)
    if channel_id:
        q = q.where(Idea.channel_id == channel_id)
    if status:
        q = q.where(Idea.status.in_(status.split(",")))
    return s.exec(q.order_by(Idea.created_at.desc()).limit(500)).all()


@router.post("/ideas")
def create_idea(body: IdeaIn, s: Session = Depends(get_session)):
    idea = Idea(**{**body.model_dump(), "summary": body.summary or body.title}, origin="manual")
    s.add(idea)
    s.commit()
    s.refresh(idea)
    jobs.enqueue("manual_idea", title=f"Validar pauta: {idea.title}", channel_id=idea.channel_id, ref_id=idea.id)
    return idea


@router.post("/ideas/discover")
def discover(data: dict[str, Any]):
    cid = data["channel_id"]
    j = jobs.enqueue("discover_ideas", title="Buscar pautas" + (f": {data['seed']}" if data.get("seed") else ""),
                     channel_id=cid, payload={k: data.get(k) for k in ("count", "seed", "format") if data.get(k)})
    return jobs.job_dict(j)


@router.patch("/ideas/{iid}")
def patch_idea(iid: int, data: dict[str, Any], s: Session = Depends(get_session)):
    idea = _get(s, Idea, iid)
    _patch(idea, data)
    s.add(idea)
    s.commit()
    s.refresh(idea)
    return idea


@router.delete("/ideas/{iid}")
def delete_idea(iid: int, s: Session = Depends(get_session)):
    s.delete(_get(s, Idea, iid))
    s.commit()
    return {"ok": True}


@router.post("/ideas/{iid}/{action}")
def idea_action(iid: int, action: str, data: dict[str, Any] | None = None, s: Session = Depends(get_session)):
    idea = _get(s, Idea, iid)
    data = data or {}
    kinds = {"score": ("score_idea", "Avaliar"), "verify": ("verify_idea", "Checar fatos"),
             "script": ("write_script", "Roteiro")}
    if action not in kinds:
        raise HTTPException(400, "ação inválida")
    kind, label = kinds[action]
    if action == "script" and idea.status in ("new", "rejected"):
        idea.status = "approved"
        s.add(idea)
        s.commit()
    j = jobs.enqueue(kind, title=f"{label}: {idea.title}", channel_id=idea.channel_id, ref_id=idea.id, payload=data)
    return jobs.job_dict(j)


# ================================================================ roteiros

@router.get("/scripts")
def list_scripts(channel_id: Optional[int] = None, all: bool = False, s: Session = Depends(get_session)):
    q = select(Script)
    if not all:
        q = q.where(Script.status != "produced")  # roteiro que já virou vídeo some da lista
    if channel_id:
        q = q.where(Script.channel_id == channel_id)
    return s.exec(q.order_by(Script.created_at.desc()).limit(300)).all()


@router.get("/scripts/{sid}")
def get_script(sid: int, s: Session = Depends(get_session)):
    sc = _get(s, Script, sid)
    d = sc.model_dump()
    d["videos"] = s.exec(select(Video).where(Video.script_id == sid).order_by(Video.id.desc())).all()
    d["idea"] = s.get(Idea, sc.idea_id) if sc.idea_id else None
    return d


@router.put("/scripts/{sid}")
def update_script(sid: int, data: dict[str, Any], s: Session = Depends(get_session)):
    sc = _get(s, Script, sid)
    _patch(sc, data)
    sc.version += 1
    s.add(sc)
    s.commit()
    s.refresh(sc)
    return sc


@router.delete("/scripts/{sid}")
def delete_script(sid: int, s: Session = Depends(get_session)):
    s.delete(_get(s, Script, sid))
    s.commit()
    return {"ok": True}


@router.post("/scripts/{sid}/review")
def review(sid: int, data: dict[str, Any] | None = None, s: Session = Depends(get_session)):
    sc = _get(s, Script, sid)
    j = jobs.enqueue("review_script", title=f"Revisar: {sc.title}", channel_id=sc.channel_id, ref_id=sid,
                     payload=data or {})
    return jobs.job_dict(j)


@router.post("/scripts/{sid}/render")
def render(sid: int, s: Session = Depends(get_session)):
    sc = _get(s, Script, sid)
    sc.status = "approved"
    s.add(sc)
    s.commit()
    j = jobs.enqueue("render_video", title=f"Vídeo: {sc.title}", channel_id=sc.channel_id, ref_id=sid)
    return jobs.job_dict(j)


@router.post("/scripts/{sid}/scenes/{idx}/rewrite")
def rewrite(sid: int, idx: int, data: dict[str, Any], s: Session = Depends(get_session)):
    from . import content
    sc = _get(s, Script, sid)
    ch = _get(s, Channel, sc.channel_id)
    new = content.rewrite_scene(ch, sc, idx, data.get("instruction", "deixe mais impactante"))
    scenes = list(sc.scenes)
    scenes[idx] = {**scenes[idx], **new}
    sc.scenes = scenes
    s.add(sc)
    s.commit()
    return scenes[idx]


# ================================================================ vídeos

@router.get("/videos")
def list_videos(channel_id: Optional[int] = None, s: Session = Depends(get_session)):
    q = select(Video, Script).join(Script, Script.id == Video.script_id)
    if channel_id:
        q = q.where(Video.channel_id == channel_id)
    out = []
    for v, sc in s.exec(q.order_by(Video.id.desc()).limit(300)).all():
        d = v.model_dump()
        d["title"] = sc.title
        d["publications"] = s.exec(select(Publication).where(Publication.video_id == v.id)).all()
        out.append(d)
    return out


@router.post("/videos/{vid}/inspect")
def video_inspect(vid: int, s: Session = Depends(get_session)):
    v = _get(s, Video, vid)
    return jobs.job_dict(jobs.enqueue("inspect_video", title=f"Inspecionar vídeo #{vid}", channel_id=v.channel_id, ref_id=vid))


@router.post("/videos/{vid}/approve")
def video_approve(vid: int, s: Session = Depends(get_session)):
    """Aprovação manual: libera um vídeo reprovado pelo inspetor."""
    v = _get(s, Video, vid)
    qa = dict((v.assets or {}).get("qa") or {})
    qa.update({"passed": True, "manual": True})
    v.assets = {**(v.assets or {}), "qa": qa}
    if v.status == "review":
        v.status = "ready"
    s.add(v)
    s.commit()
    return {"ok": True}


@router.delete("/videos/{vid}")
def delete_video(vid: int, s: Session = Depends(get_session)):
    s.delete(_get(s, Video, vid))
    s.commit()
    return {"ok": True}


# ================================================================ tarefas

@router.get("/jobs")
def list_jobs(limit: int = 60, s: Session = Depends(get_session)):
    return [jobs.job_dict(j) for j in s.exec(select(Job).order_by(Job.id.desc()).limit(limit)).all()]


@router.get("/jobs/{jid}")
def get_job(jid: int, s: Session = Depends(get_session)):
    j = _get(s, Job, jid)
    return {**jobs.job_dict(j), "log": j.log, "payload": j.payload}


@router.post("/jobs/{jid}/cancel")
def cancel_job(jid: int):
    jobs.cancel(jid)
    return {"ok": True}


@router.post("/jobs/{jid}/retry")
def retry_job(jid: int, s: Session = Depends(get_session)):
    j = _get(s, Job, jid)
    n = jobs.enqueue(j.kind, title=j.title, channel_id=j.channel_id, ref_id=j.ref_id, payload=j.payload)
    return jobs.job_dict(n)


# ================================================================ painel geral

@router.get("/dashboard")
def dashboard(channel_id: Optional[int] = None, s: Session = Depends(get_session)):
    def cnt(model, *conds):
        q = select(func.count()).select_from(model)
        if channel_id and hasattr(model, "channel_id"):
            q = q.where(model.channel_id == channel_id)
        for c in conds:
            q = q.where(c)
        return s.exec(q).one()

    since = now() - timedelta(days=30)
    mq = select(MetricSnapshot)
    if channel_id:
        mq = mq.where(MetricSnapshot.channel_id == channel_id)
    latest: dict[int, MetricSnapshot] = {}
    for m in s.exec(mq.order_by(MetricSnapshot.captured_at)).all():
        latest[m.publication_id] = m
    totals = {k: sum(getattr(m, k) for m in latest.values()) for k in ("views", "likes", "comments", "shares")}
    return {
        "counts": {
            "ideas_new": cnt(Idea, Idea.status == "new"),
            "ideas_approved": cnt(Idea, Idea.status == "approved"),
            "scripts": cnt(Script, Script.status != "produced"),
            "videos_ready": cnt(Video, Video.status == "ready"),
            "published": cnt(Publication, Publication.status == "published"),
            "scheduled": cnt(Publication, Publication.status == "scheduled"),
            "jobs_running": cnt(Job, Job.status.in_(["queued", "running"])),
            "videos_30d": cnt(Video, Video.created_at >= since),
        },
        "totals": totals,
        "insights": [i.text for i in s.exec(select(Insight).where(Insight.channel_id == channel_id) if channel_id
                                            else select(Insight)).all()[-6:]],
    }


@router.post("/channels/{cid}/import-youtube")
def import_youtube(cid: int, data: dict[str, Any], s: Session = Depends(get_session)):
    _get(s, Channel, cid)
    return jobs.job_dict(jobs.enqueue("import_youtube", title=f"Importar vídeos de {data['handle']}", channel_id=cid,
                                      payload={"handle": data["handle"]}))


@router.get("/channels/{cid}/performance")
def channel_performance(cid: int):
    from .analytics import performance_table
    return performance_table(cid)


@router.get("/channels/{cid}/analytics")
def channel_analytics(cid: int, days: int = 28):
    from .analytics import daily_analytics
    try:
        return daily_analytics(cid, days)
    except Exception as e:  # noqa: BLE001
        return {"rows": [], "connected": True, "error": str(e)[:300]}


@router.get("/channels/{cid}/retention")
def channel_retention_api(cid: int):
    from .retention import channel_retention
    return channel_retention(cid)


@router.post("/channels/{cid}/retention/insights")
def channel_retention_insights(cid: int):
    from .retention import generate_retention_insights
    return {"lessons": generate_retention_insights(cid)}


@router.get("/channels/{cid}/insights")
def channel_insights(cid: int, s: Session = Depends(get_session)):
    return [{"text": i.text, "kind": i.kind, "created_at": i.created_at} for i in
            s.exec(select(Insight).where(Insight.channel_id == cid).order_by(Insight.created_at.desc()).limit(12)).all()]


@router.post("/videos/{vid}/chapters")
def video_chapters(vid: int):
    return {"job_id": jobs.enqueue("add_chapters", title="Capítulos no YouTube", ref_id=vid).id}


@router.post("/videos/{vid}/thumbs-ab")
def video_thumbs_ab(vid: int, s: Session = Depends(get_session)):
    v = _get(s, Video, vid)
    return {"job_id": jobs.enqueue("thumb_variants", title="Miniaturas A/B", channel_id=v.channel_id, ref_id=vid).id}


@router.post("/videos/{vid}/shorts-from-long")
def video_shorts_from_long(vid: int, s: Session = Depends(get_session)):
    v = _get(s, Video, vid)
    if v.format != "long":
        raise HTTPException(400, "Só vídeos longos")
    return {"job_id": jobs.enqueue("shorts_from_long", title="Shorts a partir do longo", channel_id=v.channel_id, ref_id=vid).id}


@router.get("/channels/{cid}/experiments")
def channel_experiments(cid: int):
    from .growth import experiments
    return experiments(cid)


@router.get("/channels/{cid}/ypp")
def channel_ypp(cid: int, refresh: bool = False, s: Session = Depends(get_session)):
    from .growth import ypp_cached
    ch = s.get(Channel, cid)
    if not ch:
        raise HTTPException(404, "Canal não encontrado")
    return ypp_cached(ch, 0 if refresh else 6)


@router.get("/channels/{cid}/campaigns")
def channel_campaigns(cid: int, s: Session = Depends(get_session)):
    from .growth import active_campaign, ensure_campaigns
    ch = s.get(Channel, cid)
    if not ch:
        raise HTTPException(404, "Canal não encontrado")
    camps = ensure_campaigns(ch)
    act = active_campaign(ch)
    return {"campaigns": [c for c in camps if c.get("id") != "_none"], "active": act["id"] if act else None}


class CampaignsIn(BaseModel):
    campaigns: list[dict[str, Any]]


@router.put("/channels/{cid}/campaigns")
def channel_campaigns_save(cid: int, body: CampaignsIn, s: Session = Depends(get_session)):
    ch = s.get(Channel, cid)
    if not ch:
        raise HTTPException(404, "Canal não encontrado")
    clean = []
    for i, c in enumerate(body.campaigns):
        if not c.get("name") or not c.get("start") or not c.get("end"):
            raise HTTPException(400, "Toda campanha precisa de nome, início e fim")
        clean.append({"id": c.get("id") or f"c{int(datetime.now().timestamp())}{i}", "name": str(c["name"])[:80],
                      "focus": str(c.get("focus", ""))[:1000], "start": str(c["start"])[:10], "end": str(c["end"])[:10],
                      "share": max(0.1, min(1.0, float(c.get("share", 0.6)))), "active": bool(c.get("active", True))})
    ch.campaigns = clean or [{"id": "_none", "name": "(sem campanhas)", "focus": "", "start": "2000-01-01",
                              "end": "2000-01-01", "share": 0.1, "active": False}]
    s.add(ch)
    s.commit()
    return {"campaigns": clean}


@router.get("/comments")
def list_comments(channel_id: int, status: str = "new", s: Session = Depends(get_session)):
    from .community import _account, can_write
    from .models import Comment
    rows = s.exec(select(Comment).where(Comment.channel_id == channel_id, Comment.status == status)
                  .order_by(Comment.published_at.desc()).limit(100)).all()
    counts = {st: s.exec(select(func.count()).select_from(Comment).where(Comment.channel_id == channel_id,
                                                                          Comment.status == st)).one()
              for st in ("new", "replied", "ignored")}
    return {"items": rows, "counts": counts, "can_write": can_write(_account(channel_id))}


class ReplyIn(BaseModel):
    text: str


@router.post("/comments/{cid}/reply")
def comment_reply(cid: int, body: ReplyIn):
    from .community import reply
    if not body.text.strip():
        raise HTTPException(400, "Resposta vazia")
    try:
        reply(cid, body.text.strip()[:1000])
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e
    return {"ok": True}


@router.post("/comments/{cid}/ignore")
def comment_ignore(cid: int, s: Session = Depends(get_session)):
    from .models import Comment
    c = s.get(Comment, cid)
    if not c:
        raise HTTPException(404, "Comentário não encontrado")
    c.status = "ignored"
    s.add(c)
    s.commit()
    return {"ok": True}


@router.post("/channels/{cid}/comments/refresh")
def comments_refresh(cid: int):
    return {"job_id": jobs.enqueue("fetch_comments", title="Buscar comentários novos", channel_id=cid).id}


@router.get("/channels/{cid}/variety")
def channel_variety(cid: int, s: Session = Depends(get_session)):
    from . import variety
    ch = s.get(Channel, cid)
    if not ch:
        raise HTTPException(404, "Canal não encontrado")
    acc = s.exec(select(Account).where(Account.channel_id == cid, Account.platform == "youtube")).first()
    scopes = ((acc.credentials or {}).get("scopes") or []) if acc else []
    return {**variety.report(ch), "playlists_enabled": "https://www.googleapis.com/auth/youtube" in scopes,
            "connected": bool(acc), "series_names": ch.series or {}, "playlists": ch.playlists or {}}


@router.post("/channels/{cid}/insights")
def channel_insights_run(cid: int):
    from .analytics import generate_insights
    return {"insights": generate_insights(cid)}


@router.post("/channels/{cid}/radar")
def run_radar(cid: int, s: Session = Depends(get_session)):
    ch = _get(s, Channel, cid)
    return jobs.job_dict(jobs.enqueue("trend_radar", title=f"Radar de tendências: {ch.name}", channel_id=cid))


@router.post("/channels/{cid}/autopilot")
def run_autopilot(cid: int, s: Session = Depends(get_session)):
    ch = _get(s, Channel, cid)
    return jobs.job_dict(jobs.enqueue("autopilot", title=f"Piloto automático: {ch.name}", channel_id=cid))


# ================================================================ vozes

@router.get("/voices")
def voices(provider: str = "edge"):
    from . import tts
    return tts.list_voices(provider)


@router.post("/voices/preview")
def voice_preview(data: dict[str, Any]):
    from . import tts
    from .config import MEDIA_DIR
    out = MEDIA_DIR / "previews" / f"{data['provider']}_{slugify(data['voice'])}.mp3"
    out.parent.mkdir(parents=True, exist_ok=True)
    tts.synthesize(data["text"], out, provider=data["provider"], voice=data["voice"],
                   rate=data.get("rate", "+0%"), style=data.get("style", ""))
    return {"url": f"/media/previews/{out.name}"}


# ================================================================ contas e publicações

@router.get("/accounts")
def list_accounts(channel_id: Optional[int] = None, s: Session = Depends(get_session)):
    q = select(Account)
    if channel_id:
        q = q.where(Account.channel_id == channel_id)
    return [{"id": a.id, "platform": a.platform, "display_name": a.display_name, "channel_id": a.channel_id,
             "external_id": a.external_id} for a in s.exec(q).all()]


@router.delete("/accounts/{aid}")
def delete_account(aid: int, s: Session = Depends(get_session)):
    s.delete(_get(s, Account, aid))
    s.commit()
    return {"ok": True}


@router.post("/accounts/connect/{platform}")
def connect_account(platform: str, channel_id: Optional[int] = None):
    from . import publish
    return publish.start_connect(platform, channel_id)


@router.get("/oauth/youtube/callback", include_in_schema=False)
def youtube_callback(state: str = "", code: str = "", error: str = ""):
    from fastapi.responses import HTMLResponse
    from . import publish
    if error:
        msg, ok = f"Login cancelado: {error}", False
    else:
        try:
            msg, ok = f"Canal “{publish.yt_callback(state, code)}” conectado!", True
        except Exception as e:  # noqa: BLE001
            msg, ok = f"Falha ao conectar: {e}", False
    color = "#34d399" if ok else "#f87171"
    return HTMLResponse(f"""<!doctype html><meta charset="utf-8"><title>Lidark</title>
<body style="background:#0b0f0e;color:#e9ece8;font-family:system-ui;display:grid;place-items:center;height:100vh;margin:0">
<div style="text-align:center"><div style="font-size:48px;color:{color}">{'✓' if ok else '✕'}</div>
<h2>{msg}</h2><p style="color:#8a9690">Pode fechar esta aba e voltar ao painel.</p></div>
<script>setTimeout(()=>window.close(),2500)</script></body>""")


@router.get("/publications")
def list_publications(channel_id: Optional[int] = None, s: Session = Depends(get_session)):
    q = select(Publication)
    if channel_id:
        q = q.where(Publication.channel_id == channel_id)
    return s.exec(q.order_by(Publication.id.desc()).limit(300)).all()


@router.post("/publications")
def create_publications(data: dict[str, Any], s: Session = Depends(get_session)):
    video = _get(s, Video, data["video_id"])
    sc = _get(s, Script, video.script_id)
    when = datetime.fromisoformat(data["scheduled_at"].replace("Z", "+00:00")) if data.get("scheduled_at") else None
    created = []
    for aid in data.get("account_ids", []):
        acc = _get(s, Account, aid)
        p = Publication(channel_id=video.channel_id, video_id=video.id, account_id=acc.id, platform=acc.platform,
                        title=sc.title, description=sc.description, privacy=data.get("privacy", "public"),
                        scheduled_at=when or now(), status="scheduled" if when else "uploading")
        s.add(p)
        s.commit()
        s.refresh(p)
        created.append(p.id)
        if not when:
            jobs.enqueue("publish", title=f"Publicar no {acc.platform}: {sc.title}", channel_id=video.channel_id, ref_id=p.id,
                         payload={"force": bool(data.get("force"))})
    return {"ok": True, "ids": created}
