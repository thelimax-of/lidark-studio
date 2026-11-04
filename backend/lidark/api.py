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
from .cache import FastJSON
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


def _rows_json(rows) -> FastJSON:
    """Lista de modelos direto para JSON (mesmo formato do encoder do FastAPI, sem o passeio lento em Python)."""
    return FastJSON([r.model_dump(mode="json") for r in rows])


def _page(q, limit: Optional[int], offset: int, default: int):
    """limit/offset opcionais (?limit=&offset=); sem limit fica o teto antigo de cada lista."""
    n = default if limit is None else max(1, min(int(limit), 2000))
    return q.offset(max(0, int(offset))).limit(n)


# Campos pesados que ?slim=1 tira das listas (o detalhe de cada item continua completo)
IDEA_HEAVY = ("facts", "sources", "score_breakdown", "score_reason")
SCRIPT_HEAVY = ("scenes", "claims", "fact_check", "sources", "review_notes", "description")
VIDEO_ASSETS_KEEP = ("qa", "thumbs_ab", "duration", "template", "chapters", "narration_end")
CHANNEL_HEAVY = ("yt_description", "description", "editorial_guide", "radar", "series", "playlists", "campaigns")


def _idea_slim(i: Idea) -> dict[str, Any]:
    d = i.model_dump(mode="json", exclude=set(IDEA_HEAVY))
    sb = i.score_breakdown or {}
    d["facts_count"], d["sources_count"] = len(i.facts or []), len(i.sources or [])
    d["better_title"] = sb.get("better_title") if isinstance(sb, dict) else None
    return d


def _script_slim(sc: Script) -> dict[str, Any]:
    d = sc.model_dump(mode="json", exclude=set(SCRIPT_HEAVY))
    d["scenes_count"], d["fact_check_count"] = len(sc.scenes or []), len(sc.fact_check or [])
    return d


def _video_slim(d: dict[str, Any]) -> dict[str, Any]:
    a = d.get("assets") or {}
    d["assets"] = {k: a[k] for k in VIDEO_ASSETS_KEEP if k in a}
    return d


def _channel_slim(d: dict[str, Any]) -> dict[str, Any]:
    for k in CHANNEL_HEAVY:
        d.pop(k, None)
    st = d.get("stats") or {}
    d["stats"] = {k: v for k, v in st.items() if not isinstance(v, (dict, list))}  # sem ypp/traffic (têm rota própria)
    return d


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

def _channel_counts(s: Session) -> dict[int, dict[str, int]]:
    """Contagens de todos os canais em 4 consultas agrupadas (antes eram 4 por canal)."""
    def by(model, *conds) -> dict[int, int]:
        q = select(model.channel_id, func.count()).select_from(model)
        for c in conds:
            q = q.where(c)
        return dict(s.exec(q.group_by(model.channel_id)).all())
    parts = {"ideas": by(Idea, Idea.status == "new"), "scripts": by(Script, Script.status != "produced"),
             "videos": by(Video, Video.status == "ready"), "published": by(Publication, Publication.status == "published")}
    ids = {i for p in parts.values() for i in p}
    return {i: {k: p.get(i, 0) for k, p in parts.items()} for i in ids}


def _channels_payload(s: Session, slim: bool = False) -> list[dict[str, Any]]:
    counts = _channel_counts(s)
    connected = {a.channel_id for a in s.exec(select(Account).where(Account.platform == "youtube")).all() if a.credentials}
    out = []
    for ch in s.exec(select(Channel).order_by(Channel.id)).all():
        d = ch.model_dump()
        d["connected"] = ch.id in connected
        d["counts"] = counts.get(ch.id) or {"ideas": 0, "scripts": 0, "videos": 0, "published": 0}
        out.append(_channel_slim(d) if slim else d)
    return out


@router.get("/channels")
def list_channels(slim: bool = False, s: Session = Depends(get_session)):
    """?slim=1 tira textos longos e JSONs grandes (ver CHANNEL_HEAVY e stats.ypp/traffic) — bom para seletor/menu."""
    return _channels_payload(s, slim)


@router.get("/channels/{cid}")
def get_channel(cid: int, s: Session = Depends(get_session)):
    return _get(s, Channel, cid)


@router.put("/channels/{cid}")
def update_channel(cid: int, data: dict[str, Any], s: Session = Depends(get_session)):
    ch = _get(s, Channel, cid)
    _patch(ch, data, skip=("id", "created_at", "slug", "youtube_id", "synced_at", "stats", "setup_status",
                                "series", "playlists", "campaigns",  # mantidos pelo próprio sistema
                                "focus"))  # modo foco tem rota própria (um formulário antigo não o sobrescreve)
    s.add(ch)
    s.commit()
    s.refresh(ch)
    return ch


@router.get("/focus")
def focus_all():
    """Modo foco de cada canal + o modo sugerido pelos dados (só sugestão: quem troca é o dono)."""
    from . import focus
    return {"modes": focus.modes_meta(), "channels": focus.suggest_all()}


@router.put("/channels/{cid}/focus")
def set_channel_focus(cid: int, data: dict[str, Any], s: Session = Depends(get_session)):
    from . import focus
    _get(s, Channel, cid)
    if data.get("mode") not in focus.MODES:
        raise HTTPException(400, "Modo inválido")
    focus.set_mode(cid, data["mode"])
    return {"ok": True, "mode": data["mode"]}


@router.get("/channels/{cid}/posting-times")
def channel_posting_times(cid: int, s: Session = Depends(get_session)):
    """Melhores horários de postagem (Brasília) pelos dados do canal + o porquê."""
    from . import posting_times
    _get(s, Channel, cid)
    return posting_times.suggest(cid)


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


@router.post("/channels/{cid}/brandkit")
def channel_brandkit(cid: int, s: Session = Depends(get_session)):
    """Foto de perfil, capa e marca d'água desenhadas com o mascote e a paleta do canal."""
    from .brandkit import channel_kit
    _get(s, Channel, cid)
    return channel_kit(cid)


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
def list_ideas(channel_id: Optional[int] = None, status: Optional[str] = None, slim: bool = False,
               limit: Optional[int] = None, offset: int = 0, s: Session = Depends(get_session)):
    """?slim=1 tira facts/sources/score_breakdown/score_reason e põe facts_count, sources_count e better_title."""
    q = select(Idea)
    if channel_id:
        q = q.where(Idea.channel_id == channel_id)
    if status:
        q = q.where(Idea.status.in_(status.split(",")))
    rows = s.exec(_page(q.order_by(Idea.created_at.desc()), limit, offset, 500)).all()
    return FastJSON([_idea_slim(i) for i in rows]) if slim else _rows_json(rows)


@router.get("/ideas/{iid:int}")
def get_idea(iid: int, s: Session = Depends(get_session)):
    return _get(s, Idea, iid)


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
                     channel_id=cid, payload={k: data.get(k) for k in ("count", "seed", "format", "campaign", "mode", "parts") if data.get(k)})
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
def list_scripts(channel_id: Optional[int] = None, all: bool = False, slim: bool = False,
                 limit: Optional[int] = None, offset: int = 0, s: Session = Depends(get_session)):
    """?slim=1 tira scenes/claims/fact_check/sources/review_notes/description e põe scenes_count e fact_check_count."""
    q = select(Script)
    if not all:
        q = q.where(Script.status != "produced")  # roteiro que já virou vídeo some da lista
    if channel_id:
        q = q.where(Script.channel_id == channel_id)
    rows = s.exec(_page(q.order_by(Script.created_at.desc()), limit, offset, 300)).all()
    return FastJSON([_script_slim(x) for x in rows]) if slim else _rows_json(rows)


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
def list_videos(channel_id: Optional[int] = None, slim: bool = False, limit: Optional[int] = None, offset: int = 0,
                s: Session = Depends(get_session)):
    """?slim=1 deixa em assets só qa/thumbs_ab/duration/template/chapters/narration_end (sem images, scenes,
    image_credits, look, voice, music, captions) e tira a descrição das publicações. Sem slim: igual a antes."""
    q = select(Video, Script.title).join(Script, Script.id == Video.script_id)
    if channel_id:
        q = q.where(Video.channel_id == channel_id)
    rows = s.exec(_page(q.order_by(Video.id.desc()), limit, offset, 300)).all()
    pubs: dict[int, list] = {}
    if rows:  # publicações de todos os vídeos numa consulta só (antes: uma por vídeo)
        for p in s.exec(select(Publication).where(Publication.video_id.in_([v.id for v, _ in rows]))
                        .order_by(Publication.id)).all():
            pubs.setdefault(p.video_id, []).append(p.model_dump(mode="json", exclude={"description"} if slim else None))
    out = []
    for v, title in rows:
        d = v.model_dump()
        d["title"] = title
        d["publications"] = pubs.get(v.id, [])
        out.append(_video_slim(d) if slim else d)
    return FastJSON(out)  # vídeo em modo python (datas +00:00, como antes) e publicações em modo json ("Z", como antes)


@router.get("/videos/{vid:int}")
def get_video(vid: int, s: Session = Depends(get_session)):
    """Um vídeo completo (mesmo formato de um item de GET /videos sem slim)."""
    v = _get(s, Video, vid)
    d = v.model_dump()
    sc = s.get(Script, v.script_id)
    d["title"] = sc.title if sc else ""
    d["publications"] = s.exec(select(Publication).where(Publication.video_id == vid).order_by(Publication.id)).all()
    return d


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
def list_jobs(limit: int = 60, status: Optional[str] = None, channel_id: Optional[int] = None,
              s: Session = Depends(get_session)):
    """?status=queued,running e ?channel_id= filtram (opcionais)."""
    q = select(Job)
    if status:
        q = q.where(Job.status.in_(status.split(",")))
    if channel_id:
        q = q.where(Job.channel_id == channel_id)
    return [jobs.job_dict(j) for j in s.exec(q.order_by(Job.id.desc()).limit(max(1, min(limit, 1000)))).all()]


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
    payload = {k: v for k, v in (j.payload or {}).items() if not k.startswith("_")}  # controle interno não vai junto
    n = jobs.enqueue(j.kind, title=j.title, channel_id=j.channel_id, ref_id=j.ref_id, payload=payload)
    return jobs.job_dict(n)


@router.post("/jobs/{jid}/bump")
def bump_job(jid: int):
    """Passa a tarefa (na fila) para a frente."""
    jobs.bump(jid)
    return {"ok": True}


@router.get("/jobs-capacity")
def jobs_capacity(s: Session = Depends(get_session)):
    """Quanto o notebook consegue renderizar por dia × quanto os horários dos canais pedem."""
    done = s.exec(select(Job).where(Job.kind == "render_video", Job.status == "done")
                  .order_by(Job.id.desc()).limit(40)).all()
    queued = s.exec(select(Job).where(Job.kind == "render_video", Job.status.in_(["queued", "running"]))).all()
    refs = {j.ref_id for j in done + queued if j.ref_id}
    fmt = dict(s.exec(select(Script.id, Script.format).where(Script.id.in_(refs))).all()) if refs else {}
    mins: dict[str, list[float]] = {"short": [], "long": []}
    for j in done:
        f = fmt.get(j.ref_id)
        if f is not None and j.started_at and j.finished_at:
            m = (j.finished_at - j.started_at).total_seconds() / 60
            if 1 < m < 600:
                mins[f if f in mins else "short"].append(m)
    avg = {k: (sorted(v)[len(v) // 2] if v else (25.0 if k == "short" else 70.0)) for k, v in mins.items()}
    measured = {k: len(v) for k, v in mins.items()}
    rows, need = [], 0.0
    for ch in s.exec(select(Channel).order_by(Channel.id)).all():
        slots = [str(x) for x in ch.posting_slots or []]
        longs_week = sum("longo" in x.lower() for x in slots)
        shorts_day = (len(slots) - longs_week) if "short" in (ch.formats or []) else 0
        if (ch.schedule or {}).get("mode") == "auto" and "short" in (ch.formats or []):
            from .posting_times import settings as _sched_cfg
            shorts_day = _sched_cfg(ch)["per_day"]  # horários pelos dados: N Shorts/dia
        if "long" in (ch.formats or []) and not longs_week:
            longs_week = 1
        if "long" not in (ch.formats or []):
            longs_week = 0
        m = shorts_day * avg["short"] + longs_week / 7 * avg["long"]
        need += m
        rows.append({"channel_id": ch.id, "name": ch.name, "shorts_day": shorts_day, "longs_week": longs_week,
                     "minutes_day": round(m), "auto_pilot": ch.auto_pilot})
    q_min = 0.0
    for j in queued:
        q_min += avg["long" if fmt.get(j.ref_id) == "long" else "short"] * (1 - (j.progress or 0))
    return {"avg_minutes": {k: round(v, 1) for k, v in avg.items()}, "measured": measured, "channels": rows,
            "need_hours_day": round(need / 60, 1), "available_hours_day": 24,
            "usage": round(need / (24 * 60), 2), "queue_renders": len(queued), "queue_hours": round(q_min / 60, 1)}


# ================================================================ assistente "Novo canal"

@router.get("/brand-drafts")
def list_drafts(s: Session = Depends(get_session)):
    from .brandwizard import draft_dict
    from .models import BrandDraft
    return [draft_dict(d) for d in s.exec(select(BrandDraft).order_by(BrandDraft.id.desc()).limit(30)).all()]


@router.post("/brand-drafts")
def create_draft(data: dict[str, Any], s: Session = Depends(get_session)):
    from .brandwizard import draft_dict
    from .models import BrandDraft
    niche = str(data.get("niche") or "").strip()
    if len(niche) < 3:
        raise HTTPException(400, "Descreva o nicho do canal")
    d = BrandDraft(niche=niche, notes=str(data.get("notes") or "").strip())
    s.add(d)
    s.commit()
    s.refresh(d)
    jobs.enqueue("brand_propose", title=f"Novo canal: {niche[:50]}", ref_id=d.id)
    return draft_dict(d)


@router.get("/brand-drafts/{did}")
def get_draft(did: int, s: Session = Depends(get_session)):
    from .brandwizard import draft_dict
    from .models import BrandDraft
    return draft_dict(_get(s, BrandDraft, did))


@router.post("/brand-drafts/{did}/redo")
def redo_draft(did: int, s: Session = Depends(get_session)):
    from .models import BrandDraft
    d = _get(s, BrandDraft, did)
    d.options, d.chosen, d.texts, d.status = [], -1, {}, "draft"
    s.add(d)
    s.commit()
    return jobs.job_dict(jobs.enqueue("brand_propose", title=f"Novo canal: {d.niche[:50]}", ref_id=d.id))


@router.post("/brand-drafts/{did}/choose")
def choose_draft(did: int, data: dict[str, Any], s: Session = Depends(get_session)):
    from .models import BrandDraft
    d = _get(s, BrandDraft, did)
    i = int(data.get("index", -1))
    if not 0 <= i < len(d.options):
        raise HTTPException(400, "Opção inválida")
    d.chosen, d.texts = i, {}
    s.add(d)
    s.commit()
    return jobs.job_dict(jobs.enqueue("brand_texts", title=f"Textos do canal: {d.options[i]['name']}", ref_id=d.id))


@router.post("/brand-drafts/{did}/apply")
def apply_draft_to(did: int, data: dict[str, Any], s: Session = Depends(get_session)):
    from .brandwizard import apply_draft
    from .models import BrandDraft
    d = _get(s, BrandDraft, did)
    cid = int(data.get("channel_id") or 0)
    _get(s, Channel, cid)
    if d.chosen < 0 or not d.texts:
        raise HTTPException(400, "Escolha um nome e espere os textos ficarem prontos")
    apply_draft(did, cid)
    from .channels import render_preview
    render_preview(cid)
    return {"ok": True}


@router.delete("/brand-drafts/{did}")
def delete_draft(did: int, s: Session = Depends(get_session)):
    from .models import BrandDraft
    s.delete(_get(s, BrandDraft, did))
    s.commit()
    return {"ok": True}


@router.get("/system/restart")
def restart_status():
    return jobs.restart_status()


@router.post("/system/restart")
def restart(data: dict[str, Any] | None = None):
    """Reinicia o servidor quando ficar livre (nunca no meio de um render)."""
    return jobs.request_restart(when_idle=(data or {}).get("when_idle", True))


@router.post("/system/restart/cancel")
def restart_cancel():
    return jobs.cancel_restart()


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

    from .analytics import latest_metrics
    since = now() - timedelta(days=30)
    latest = latest_metrics(channel_id)  # só a última leitura de cada publicação sai do banco
    totals = {k: sum(getattr(m, k) for m in latest.values()) for k in ("views", "likes", "comments", "shares")}
    iq = select(Insight.text).order_by(Insight.id.desc()).limit(6)
    if channel_id:
        iq = iq.where(Insight.channel_id == channel_id)
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
        "insights": list(reversed(s.exec(iq).all())),
    }


@router.post("/channels/{cid}/import-youtube")
def import_youtube(cid: int, data: dict[str, Any], s: Session = Depends(get_session)):
    _get(s, Channel, cid)
    return jobs.job_dict(jobs.enqueue("import_youtube", title=f"Importar vídeos de {data['handle']}", channel_id=cid,
                                      payload={"handle": data["handle"]}))


@router.post("/channels/{cid}/metrics/sync")
def channel_metrics_sync(cid: int, s: Session = Depends(get_session)):
    ch = _get(s, Channel, cid)
    busy = s.exec(select(Job).where(Job.kind == "collect_metrics", Job.status.in_(("queued", "running")),
                                    (Job.channel_id == cid) | (Job.channel_id == None))).first()  # noqa: E711
    if busy:
        return jobs.job_dict(busy)
    return jobs.job_dict(jobs.enqueue("collect_metrics", title=f"Sincronizar métricas: {ch.name}", channel_id=cid))


@router.get("/channels/{cid}/performance")
def channel_performance(cid: int):
    from .analytics import performance_table
    return performance_table(cid)


@router.get("/channels/{cid}/analytics")
def channel_analytics(cid: int, days: int = 28, refresh: bool = False):
    """A consulta ao YouTube Analytics fica 15 min em cache; ?refresh=1 consulta de novo."""
    from . import cache
    from .analytics import daily_analytics
    if refresh:
        cache.drop(f"yt:daily:{cid}:")
    try:
        return daily_analytics(cid, days)
    except Exception as e:  # noqa: BLE001
        return {"rows": [], "connected": True, "error": str(e)[:300]}


@router.get("/overview")
def overview_api(days: int = 28, channel_id: Optional[int] = None, refresh: bool = False):
    """Todos os canais juntos: totais do período, comparação por canal e views diárias por canal.
    Em cache (Analytics 15 min; o cálculo vale até a próxima coleta/publicação); ?refresh=1 refaz tudo."""
    from .analytics import overview
    return overview(max(1, min(days, 365)), channel_id, refresh)


@router.get("/bootstrap")
def bootstrap(channel_id: Optional[int] = None, s: Session = Depends(get_session)):
    """Tudo que o painel precisa no primeiro carregamento, numa ida só:
    {channels: [canal slim + connected + counts], dashboard: <GET /dashboard>, jobs: [job_dict ativos (queued/running)],
     notifications_unread: int, restart: <GET /system/restart>}"""
    active = s.exec(select(Job).where(Job.status.in_(["queued", "running"])).order_by(Job.id.desc()).limit(200)).all()
    unread = 0
    try:
        from .notify import Notification
        unread = s.exec(select(func.count()).select_from(Notification).where(Notification.read == False)).one()  # noqa: E712
    except Exception:  # noqa: BLE001 — central de avisos ausente ou tabela ainda não criada
        s.rollback()
    return {"channels": _channels_payload(s, slim=True), "dashboard": dashboard(channel_id, s),
            "jobs": [jobs.job_dict(j) for j in active], "notifications_unread": unread,
            "restart": jobs.restart_status()}


@router.get("/system/cache")
def cache_stats():
    """Idade de cada entrada do cache em memória (diagnóstico)."""
    from . import cache
    return cache.stats()


@router.get("/performance")
def performance_api(channel_id: Optional[int] = None):
    from .analytics import performance_all, performance_table
    return performance_table(channel_id) if channel_id else performance_all()


@router.get("/channels/{cid}/retention")
def channel_retention_api(cid: int):
    from .retention import channel_retention
    return channel_retention(cid)


@router.post("/channels/{cid}/retention/insights")
def channel_retention_insights(cid: int):
    from .retention import generate_retention_insights
    return {"lessons": generate_retention_insights(cid)}


@router.get("/channels/{cid}/retention/rules")
def channel_retention_rules(cid: int):
    """Regras automáticas (calculadas das quedas por cena) que entram no prompt do roteirista."""
    from .retention import retention_rules
    return retention_rules(cid)


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


@router.get("/champions")
def champions_api(channel_id: Optional[int] = None, limit: int = 6):
    """Shorts campeões (alcance, retenção, views engajadas) que valem virar vídeo longo — o funil para horas assistidas."""
    from .longform import champions, champions_all
    return champions(channel_id, max(1, min(limit, 30))) if channel_id else champions_all(max(1, min(limit, 10)))


@router.post("/channels/{cid}/champions/long")
def champion_to_long(cid: int, data: dict[str, Any], s: Session = Depends(get_session)):
    """Transformar em vídeo longo: pesquisa, planeja capítulos com fontes, checa, dá nota e escreve o roteiro (sem renderizar)."""
    ch = _get(s, Channel, cid)
    key = str(data.get("key") or "")
    if not key:
        raise HTTPException(400, "Informe o Short")
    busy = s.exec(select(Job).where(Job.kind == "champion_long", Job.channel_id == cid,
                                    Job.status.in_(("queued", "running")))).all()
    for j in busy:
        if str((j.payload or {}).get("key")) == key:
            return jobs.job_dict(j)
    title = str(data.get("title") or "")[:60]
    return jobs.job_dict(jobs.enqueue("champion_long", title=f"Short campeão → vídeo longo: {title or ch.name}",
                                      channel_id=cid, payload={"key": key}))


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


@router.get("/channels/{cid}/enem")
def channel_enem(cid: int, s: Session = Depends(get_session)):
    """Pacote da campanha ENEM: pautas de História que mais caem, horários até a prova e status de cada uma."""
    from . import enem
    ch = s.get(Channel, cid)
    if not ch:
        raise HTTPException(404, "Canal não encontrado")
    return enem.pack(ch)


class EnemLaunchIn(BaseModel):
    keys: list[str]
    schedule_longs: bool = False


@router.post("/channels/{cid}/enem/launch")
def channel_enem_launch(cid: int, body: EnemLaunchIn, s: Session = Depends(get_session)):
    from . import enem
    ch = s.get(Channel, cid)
    if not ch:
        raise HTTPException(404, "Canal não encontrado")
    return enem.launch(ch, body.keys, body.schedule_longs)


@router.get("/comments")
def list_comments(channel_id: Optional[int] = None, status: str = "new", s: Session = Depends(get_session)):
    """Sem channel_id: caixa única com os comentários de todos os canais."""
    from .community import _account, can_write
    from .models import Comment

    def where(q):
        return q.where(Comment.channel_id == channel_id) if channel_id else q
    order = [Comment.pinned, Comment.published_at.desc()] if status == "seed" else [Comment.published_at.desc()]  # a fixar primeiro
    rows = s.exec(where(select(Comment).where(Comment.status == status))
                  .order_by(*order).limit(200 if not channel_id else 100)).all()
    counts = {st: s.exec(where(select(func.count()).select_from(Comment).where(Comment.status == st))).one()
              for st in ("new", "replied", "ignored", "seed")}
    counts["to_pin"] = s.exec(where(select(func.count()).select_from(Comment).where(Comment.status == "seed",
                                                                                  Comment.pinned == False))).one()  # noqa: E712
    ids = [channel_id] if channel_id else [c.id for c in s.exec(select(Channel)).all()]
    by_channel = {i: can_write(_account(i)) for i in ids}
    return {"items": rows, "counts": counts, "can_write": all(by_channel.values()) if by_channel else False,
            "can_write_by": by_channel}


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


@router.post("/comments/{cid}/suggest")
def comment_suggest(cid: int, s: Session = Depends(get_session)):
    """Gera na hora a resposta sugerida. Só preenche o texto: publicar continua sendo com você."""
    from .community import suggest_replies
    from .models import Comment
    c = s.get(Comment, cid)
    if not c:
        raise HTTPException(404, "Comentário não encontrado")
    ch = s.get(Channel, c.channel_id)
    if c.suggestion:
        c.suggestion = ""
        s.add(c)
        s.commit()
    try:
        suggest_replies(ch, only=cid)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"A IA não respondeu agora: {e}") from e
    s.expire_all()
    c = s.get(Comment, cid)
    if not c.suggestion and c.status == "new":
        raise HTTPException(502, "A IA não devolveu sugestão. Tente de novo.")
    return {"suggestion": c.suggestion, "status": c.status}


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


@router.post("/comments/{cid}/pinned")
def comment_pinned(cid: int, s: Session = Depends(get_session)):
    """Você fixou o comentário do canal no YouTube (a API não permite fixar) — sai da lista "a fixar"."""
    from .models import Comment
    c = s.get(Comment, cid)
    if not c:
        raise HTTPException(404, "Comentário não encontrado")
    c.pinned = not c.pinned
    s.add(c)
    s.commit()
    return {"pinned": c.pinned}


@router.post("/channels/{cid}/comments/refresh")
def comments_refresh(cid: int):
    return {"job_id": jobs.enqueue("fetch_comments", title="Buscar comentários novos", channel_id=cid).id}


@router.post("/comments/refresh")
def comments_refresh_all():
    return {"job_id": jobs.enqueue("fetch_comments", title="Buscar comentários novos (todos os canais)").id}


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


@router.post("/notify/test")
def notify_test():
    from . import notify
    ok = notify.send("🔔 Lidark Studio", "Avisos funcionando! Assim chegam: vídeo pronto, revisão, falhas, publicação, "
                     "comentários e o resumo das 21h.\n\n" + notify.daily_summary(), tags=["bell"], force=True)
    if not ok:
        raise HTTPException(400, "Não consegui enviar — confira a internet e o servidor ntfy")
    return {"ok": True, "topic": notify.topic()}


@router.get("/notify/topic")
def notify_topic():
    from . import notify
    return {"topic": notify.topic(), "server": config.get("ntfy_server") or "https://ntfy.sh"}


@router.get("/backup/status")
def backup_status():
    from . import cloud
    return cloud.status()


@router.post("/backup/drive/connect")
def backup_drive_connect():
    from . import cloud
    try:
        return cloud.connect()
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/backup/now")
def backup_now():
    from . import cloud
    try:
        return cloud.backup_now()
    except RuntimeError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/oauth/drive/callback", include_in_schema=False)
def drive_callback(state: str = "", code: str = "", error: str = ""):
    from fastapi.responses import HTMLResponse
    from . import cloud
    if error:
        msg, ok = f"Login cancelado: {error}", False
    else:
        try:
            cloud.callback(state, code)
            msg, ok = "Google Drive conectado! O primeiro backup começa agora — pode fechar esta janela.", True
            jobs.enqueue("cloud_backup", title="Backup na nuvem (Google Drive)")
        except Exception as e:  # noqa: BLE001
            msg, ok = f"Falha ao conectar: {e}", False
    color = "#3fb950" if ok else "#f85149"
    return HTMLResponse(f"""<!doctype html><meta charset="utf-8"><title>Lidark</title>
<body style="background:#09090b;color:#ededef;font-family:system-ui;display:grid;place-items:center;height:100vh;margin:0">
<div style="text-align:center"><div style="font-size:42px;color:{color}">{'✓' if ok else '✗'}</div><p>{msg}</p></div>
<script>setTimeout(()=>window.close(),{4000 if ok else 15000})</script></body>""")


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
    return _rows_json(s.exec(q.order_by(Publication.id.desc()).limit(300)).all())


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
