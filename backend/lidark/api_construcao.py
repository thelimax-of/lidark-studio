"""API do motor 3D do Parte por Parte."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlmodel import select

from . import jobs
from .construcao import projeto as P
from .construcao import semanal as _semanal  # noqa: F401  registra a tarefa semanal
from .db import session
from .models import Channel, Job, Video

router = APIRouter(prefix="/api/construcao")
CANAL_SLUG = "ze-na-fuga"  # slug interno do canal Parte por Parte


def _get(pid: str) -> dict[str, Any]:
    try:
        return P.ler(pid)
    except (OSError, ValueError) as e:
        raise HTTPException(404, "Projeto não encontrado") from e


@router.get("/projetos")
def projetos(channel_id: int | None = None):
    out = [p for p in P.listar() if not p.get("teste") and (channel_id is None or p.get("channel_id") == channel_id)]
    with session() as s:
        for p in out:
            v = s.get(Video, p["video_id"]) if p.get("video_id") else None
            if v:
                p.update(video_path=v.path, capa_path=v.thumbnail_path, duracao=v.duration)
            j = s.get(Job, p["job_id"]) if p.get("job_id") else None
            if j and j.status in ("queued", "running"):
                p.update(progresso=j.progress, etapa=j.stage)
            elif j and p["status"] in ("criando", "renderizando"):  # tarefa acabou sem atualizar o projeto
                p.update(status="erro", erro=j.error[:300] or "A tarefa foi interrompida")
    return out


@router.get("/estado")
def estado():
    with session() as s:
        ch = s.exec(select(Channel).where(Channel.slug == CANAL_SLUG)).first()
    return {"miniatura_bloqueada": bool(ch and ch.thumbs_blocked)}


@router.post("/projetos")
def criar(data: dict[str, Any]):
    tema = str(data.get("tema", "")).strip()
    if len(tema) < 3:
        raise HTTPException(400, "Informe o tema")
    with session() as s:
        ch = s.exec(select(Channel).where(Channel.slug == CANAL_SLUG)).first()
    if not ch:
        raise HTTPException(400, "Canal Parte por Parte não encontrado")
    p = P.novo(ch.id, tema)
    return jobs.job_dict(P.claude_job(p)) | {"projeto": p["id"]}


@router.get("/biblioteca")
def biblioteca():
    return P.biblioteca()


@router.put("/projetos/{pid}")
def editar(pid: str, data: dict[str, Any]):
    p = _get(pid)
    for k in ("titulo", "descricao", "falas", "destaque", "tags"):
        if k in data:
            p[k] = data[k]
    return P.salvar(p)


@router.post("/projetos/{pid}/cena")
def refazer_cena(pid: str):
    return jobs.job_dict(P.claude_job(_get(pid)))


@router.post("/projetos/{pid}/chat")
def chat(pid: str, data: dict[str, Any]):
    p = _get(pid)
    msg = str(data.get("mensagem", "")).strip()
    if not msg:
        raise HTTPException(400, "Escreva o ajuste")
    if p["status"] in ("criando", "renderizando"):
        raise HTTPException(409, "Espere terminar a tarefa atual")
    return jobs.job_dict(P.chat_job(p, msg))


@router.post("/projetos/{pid}/render")
def render(pid: str):
    p = _get(pid)
    if not (P.pasta(pid) / "cena.js").exists():
        raise HTTPException(400, "A cena ainda não existe")
    return jobs.job_dict(P.render_job(p))


@router.get("/projetos/{pid}/previa")
def previa(pid: str):
    f = P.pasta(pid) / "previa.jpg"
    if not f.exists():
        raise HTTPException(404, "Sem prévia")
    return FileResponse(f, headers={"Cache-Control": "no-store"})


@router.post("/semanal")
def semanal(data: dict[str, Any]):
    """Roda o vídeo longo da semana agora. Sem "publicar": true, ele fica pronto em Vídeos para conferir."""
    return jobs.job_dict(jobs.enqueue("construcao_semanal", title="Vídeo longo da semana: Parte por Parte", payload={k: data[k] for k in ("ids", "pasta", "publicar") if k in data}))
