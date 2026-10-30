"""API do Modo História: bíblias das séries, banco de assets, episódios, cota grátis de imagens e configuração."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import select

from . import jobs
from .db import session
from .models import Channel, Job, Script, Video
from .story import bank, bible as B, gpu, jobs as story_jobs, providers, writer  # noqa: F401 (registra as tarefas story_*)
from .story import seasons, series  # noqa: F401 (registra story_series_ideas)

router = APIRouter(prefix="/api/story")


def _ch(cid: int) -> Channel:
    with session() as s:
        ch = s.get(Channel, cid)
    if not ch:
        raise HTTPException(404, f"Canal {cid} não encontrado")
    return ch


def _asset_out(cid: int, a: dict[str, Any]) -> dict[str, Any]:
    out = {k: a.get(k) for k in ("id", "type", "char", "pose", "tags", "size", "source", "uses", "episodes", "note",
                                 "disabled", "created", "orientation")}
    out["has_eyes"] = bool(a.get("eyes"))
    out["url"] = f"/api/story/{cid}/file/{a['file']}"
    if a.get("fg"):
        out["fg_url"] = f"/api/story/{cid}/file/{a['fg']}"
    return out


# ================================================================ visão geral

@router.get("/overview")
def overview():
    with session() as s:
        chans = s.exec(select(Channel).order_by(Channel.id)).all()
        recent = s.exec(select(Script).order_by(Script.id.desc()).limit(300)).all()
    out = []
    for ch in chans:
        b = B.load(ch.slug)
        ok, why = story_jobs.ready(ch)
        eps = [r for r in recent if r.channel_id == ch.id and (r.variety or {}).get("structure") == "historia"]
        arc = writer.open_arc(ch.slug)
        hero = (b.get("characters") or [{}])[0]
        poses = {a.get("pose") for a in bank.find(ch.slug, "pose", char=hero.get("id", ""), limit=60)}
        out.append({"id": ch.id, "name": ch.name, "slug": ch.slug, "color": ch.color, "series_title": b.get("series_title"),
                    "enabled": b.get("enabled", True), "share": story_jobs.story_share(ch, "short"), "ready": ok, "why": why,
                    "bank": bank.stats(ch.slug), "episodes": len(eps),
                    "hero": {"id": hero.get("id"), "name": hero.get("name"), "poses_have": len(poses - {None}),
                             "poses_want": len(b.get("poses") or [])},
                    "open_arc": {"title": arc.get("title"), "parts": len(arc.get("parts") or []), "max": arc.get("max_parts")} if arc else None})
    return {"channels": out, "capacity": providers.capacity(), "gpu": gpu.holder(), "conf": providers.public_conf()}


@router.get("/capacity")
def capacity():
    return {"capacity": providers.capacity(), "gpu": gpu.holder()}


@router.get("/config")
def get_config():
    return providers.public_conf()


@router.put("/config")
def put_config(data: dict[str, Any]):
    return providers.save_conf(data)


# ================================================================ bíblia

@router.get("/{cid}/bible")
def get_bible(cid: int):
    ch = _ch(cid)
    return B.load(ch.slug)


@router.put("/{cid}/bible")
def put_bible(cid: int, data: dict[str, Any]):
    ch = _ch(cid)
    return B.save(ch.slug, data)


@router.post("/{cid}/bible/reset")
def reset_bible(cid: int):
    ch = _ch(cid)
    p = B.path(ch.slug)
    if p.exists():
        p.unlink()
    return B.load(ch.slug)


# ================================================================ banco

@router.get("/{cid}/bank")
def get_bank(cid: int, type: str = "", char: str = ""):
    ch = _ch(cid)
    items = [a for a in bank.load(ch.slug) if (not type or a["type"] == type) and (not char or a.get("char") == char)]
    items.sort(key=lambda a: -float(a.get("created") or 0))
    return {"items": [_asset_out(cid, a) for a in items], "stats": bank.stats(ch.slug)}


@router.get("/{cid}/file/{path:path}")
def bank_file(cid: int, path: str):
    ch = _ch(cid)
    root = (B.STORY_DIR / ch.slug).resolve()
    f = (root / path).resolve()
    if root not in f.parents or not f.is_file():
        raise HTTPException(404, "arquivo não encontrado")
    return FileResponse(f, headers={"Cache-Control": "public, max-age=86400"})


@router.patch("/{cid}/bank/{aid}")
def patch_asset(cid: int, aid: str, data: dict[str, Any]):
    ch = _ch(cid)
    a = bank.update(ch.slug, aid, **data)
    if not a:
        raise HTTPException(404, "asset não encontrado")
    return _asset_out(cid, a)


@router.delete("/{cid}/bank/{aid}")
def delete_asset(cid: int, aid: str):
    ch = _ch(cid)
    if not bank.remove(ch.slug, aid):
        raise HTTPException(404, "asset não encontrado")
    return {"ok": True}


@router.post("/{cid}/bank/{aid}/regenerate")
def regenerate(cid: int, aid: str):
    """Pose/cenário ruim: desativa e gera outro igual (mesmo personagem/pose, outra semente) quando houver cota."""
    ch = _ch(cid)
    a = bank.get(ch.slug, aid)
    if not a:
        raise HTTPException(404, "asset não encontrado")
    bank.update(ch.slug, aid, disabled=True)
    j = jobs.enqueue("story_pregen", title=f"Refazer {a['type']} {a.get('char', '')} {a.get('pose', '')}".strip(), channel_id=cid,
                     payload={"channel_id": cid, "max": 1, "regen": aid})
    return {"job_id": j.id}


@router.post("/{cid}/sheet")
def build_sheet(cid: int, data: Optional[dict[str, Any]] = None):
    """Gera o que falta do banco do canal (folhas de personagem primeiro, depois cenários da bíblia)."""
    _ch(cid)
    j = jobs.enqueue("story_pregen", title="Banco do Modo História", channel_id=cid,
                     payload={"channel_id": cid, "max": int((data or {}).get("max", 20))})
    return {"job_id": j.id}


@router.post("/seed")
def seed():
    j = jobs.enqueue("story_seed", title="Banco do Modo História: protótipo aprovado")
    return {"job_id": j.id}


@router.post("/pregen")
def pregen(data: Optional[dict[str, Any]] = None):
    j = jobs.enqueue("story_pregen", title="Modo História: crescer bancos com a cota que sobrou",
                     payload={"max": int((data or {}).get("max", 40))})
    return {"job_id": j.id}


# ================================================================ episódios

@router.get("/{cid}/episodes")
def episodes(cid: int, limit: int = 30):
    ch = _ch(cid)
    with session() as s:
        rows = [r for r in s.exec(select(Script).where(Script.channel_id == cid).order_by(Script.id.desc()).limit(400)).all()
                if (r.variety or {}).get("structure") == "historia"][:limit]
        vids = {v.script_id: v for v in s.exec(select(Video).where(Video.script_id.in_([r.id for r in rows] or [0]))).all()}
        running = s.exec(select(Job).where(Job.kind.in_(["story_episode", "story_assets", "story_render"]),
                                           Job.status.in_(["queued", "running"]), Job.channel_id == cid)).all()
    out = []
    for r in rows:
        st = (r.variety or {}).get("story") or {}
        v = vids.get(r.id)
        out.append({"script_id": r.id, "title": r.title, "part": st.get("part"), "arc": st.get("arc_title"),
                    "mission": (st.get("mission") or {}).get("title"), "style": st.get("episode_style"), "beats": len(r.scenes or []),
                    "words": sum(len((x.get("text") or "").split()) for x in r.scenes or []), "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "video": {"id": v.id, "status": v.status, "path": v.path, "thumbnail": v.thumbnail_path, "duration": v.duration,
                              "story": (v.assets or {}).get("story"), "qa": ((v.assets or {}).get("qa") or {}).get("passed")} if v else None})
    return {"episodes": out, "arcs": writer.series(ch.slug).get("arcs", [])[-10:],
            "jobs": [jobs.job_dict(j) for j in running]}


@router.post("/{cid}/episode")
def new_episode(cid: int, data: Optional[dict[str, Any]] = None):
    """Gerar episódio: continua o arco aberto (se houver) ou começa um novo com a melhor pauta verificada / tema dado."""
    ch = _ch(cid)
    d = data or {}
    fmt = d.get("format") or "short"
    payload = {"format": fmt, "auto_render": d.get("auto_render", True)}
    for k in ("topic", "idea_id", "new_arc", "publish_at"):
        if d.get(k):
            payload[k] = d[k]
    j = jobs.enqueue("story_episode", title=f"Modo História: {ch.name}", channel_id=cid, ref_id=d.get("idea_id"), payload=payload)
    return {"job_id": j.id}


@router.post("/{cid}/episodes/{sid}/render")
def rerender(cid: int, sid: int):
    _ch(cid)
    j = jobs.enqueue("story_render", title="Vídeo (história): refazer", channel_id=cid, ref_id=sid)
    return {"job_id": j.id}


@router.get("/{cid}/arcs")
def arcs(cid: int):
    ch = _ch(cid)
    return writer.series(ch.slug)


@router.post("/{cid}/arcs/{arc_id}/close")
def close_arc(cid: int, arc_id: str):
    ch = _ch(cid)
    d = writer.series(ch.slug)
    for a in d.get("arcs") or []:
        if a["id"] == arc_id:
            a["status"] = "closed"
    writer._save_series(ch.slug, d)
    return {"ok": True}


# ================================================================ séries (canal dedicado)

@router.get("/{cid}/series")
def series_overview(cid: int):
    ch = _ch(cid)
    return {"dedicated": seasons.dedicated(ch), **series.overview(ch)}


@router.get("/{cid}/plans/{idea_id}")
def get_plan(cid: int, idea_id: int):
    ch = _ch(cid)
    p = seasons.load_plan(ch.slug, idea_id)
    if not p:
        raise HTTPException(404, "esta pauta não é uma série planejada")
    arc = next((a for a in series.arcs(ch.slug) if a.get("idea_id") == idea_id), None)
    return {"plan": p, "arc_id": arc["id"] if arc else None, "status": arc.get("status") if arc else "não começou"}


@router.post("/{cid}/series/new")
def new_series(cid: int, data: Optional[dict[str, Any]] = None):
    _ch(cid)
    d = data or {}
    j = jobs.enqueue("story_series_ideas", title="Planejar séries", channel_id=cid,
                     payload={"count": int(d.get("count") or 2), "seed": str(d.get("seed") or "")})
    return {"job_id": j.id}


@router.post("/{cid}/series/{idea_id}/start")
def start_series(cid: int, idea_id: int):
    """Produzir a pauta-série: abre o arco e escreve a parte 1 (as seguintes vêm em ordem pelo tick)."""
    _ch(cid)
    j = jobs.enqueue("story_episode", title="Modo História: começar série", channel_id=cid, ref_id=idea_id,
                     payload={"series_mode": True, "idea_id": idea_id})
    return {"job_id": j.id}


@router.post("/{cid}/series/tick")
def series_tick(cid: int):
    ch = _ch(cid)
    if not seasons.dedicated(ch):
        raise HTTPException(400, "canal não é dedicado ao Modo História")
    return series._tick_channel(ch)


@router.post("/{cid}/arcs/{arc_id}/parts/{n}/poll")
def set_poll(cid: int, arc_id: str, n: int, data: dict[str, Any]):
    """Resultado da enquete da aba Posts digitado à mão (soma com os votos dos comentários)."""
    ch = _ch(cid)
    r = series.set_manual_poll(ch, arc_id, n, {"A": int(data.get("A") or 0), "B": int(data.get("B") or 0)})
    if r is None:
        raise HTTPException(404, "parte não encontrada")
    return r


@router.post("/{cid}/arcs/{arc_id}/parts/{n}/decide")
def decide_now(cid: int, arc_id: str, n: int):
    """Fecha a votação agora (sem esperar o prazo) e libera a próxima parte."""
    ch = _ch(cid)
    a = series.get_arc(ch.slug, arc_id)
    if not a:
        raise HTTPException(404, "série não encontrada")
    return series.decide(ch, a, n, force=True) or {"msg": "nada a decidir"}


@router.post("/{cid}/arcs/{arc_id}/long")
def series_long(cid: int, arc_id: str):
    ch = _ch(cid)
    a = series.get_arc(ch.slug, arc_id)
    if not a:
        raise HTTPException(404, "série não encontrada")
    sid = series.make_long(ch, a)
    if not sid:
        raise HTTPException(400, "a série ainda não tem todas as partes escritas")
    return {"script_id": sid}
