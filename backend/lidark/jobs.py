"""Fila de tarefas persistente (SQLite) com workers em threads e eventos em tempo real.

GPU e CPU pesada são serializadas na fila "render"; pesquisa/LLM rodam na fila "light".
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import traceback
from typing import Any, Callable

from sqlmodel import select

from .db import session
from .models import Job, now

log = logging.getLogger("lidark.jobs")

HANDLERS: dict[str, Callable[["JobContext"], dict | None]] = {}
HEAVY_KINDS = {"render_video"}


def handler(kind: str):
    def deco(fn):
        HANDLERS[kind] = fn
        return fn
    return deco


class Cancelled(Exception):
    pass


# ---------------------------------------------------------------- eventos (SSE)

class EventBus:
    def __init__(self) -> None:
        self._subs: list[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        with self._lock:
            self._subs.append((asyncio.get_running_loop(), q))
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            self._subs = [(l, x) for l, x in self._subs if x is not q]

    def publish(self, event: str, data: dict[str, Any]) -> None:
        with self._lock:
            subs = list(self._subs)
        for loop, q in subs:
            try:
                loop.call_soon_threadsafe(_put_nowait, q, {"event": event, "data": data})
            except RuntimeError:
                pass


def _put_nowait(q: asyncio.Queue, item: Any) -> None:
    if not q.full():
        q.put_nowait(item)


bus = EventBus()


def job_dict(j: Job) -> dict[str, Any]:
    return {
        "id": j.id, "kind": j.kind, "channel_id": j.channel_id, "ref_id": j.ref_id, "title": j.title,
        "status": j.status, "progress": j.progress, "stage": j.stage, "error": j.error,
        "result": j.result, "created_at": j.created_at.isoformat() if j.created_at else None,
        "started_at": j.started_at.isoformat() if j.started_at else None,
        "finished_at": j.finished_at.isoformat() if j.finished_at else None,
    }


# ---------------------------------------------------------------- contexto

class JobContext:
    def __init__(self, job: Job) -> None:
        self.job_id = job.id
        self.payload = job.payload or {}
        self.channel_id = job.channel_id
        self.ref_id = job.ref_id
        self._last_emit = 0.0

    def update(self, progress: float | None = None, stage: str | None = None, log_line: str | None = None) -> None:
        with session() as s:
            j = s.get(Job, self.job_id)
            if j is None:
                return
            if j.status == "cancelled":
                raise Cancelled()
            if progress is not None:
                j.progress = max(0.0, min(1.0, progress))
            if stage is not None:
                j.stage = stage
            if log_line:
                j.log = (j.log or "") + f"[{time.strftime('%H:%M:%S')}] {log_line}\n"
            s.add(j)
            s.commit()
            data = job_dict(j)
        if log_line:
            log.info("job %s: %s", self.job_id, log_line)
        t = time.time()
        if stage or log_line or t - self._last_emit > 0.4:
            self._last_emit = t
            bus.publish("job", data)

    def log(self, msg: str) -> None:
        self.update(log_line=msg)


def enqueue(kind: str, *, title: str = "", channel_id: int | None = None, ref_id: int | None = None,
            payload: dict | None = None) -> Job:
    with session() as s:
        j = Job(kind=kind, title=title or kind, channel_id=channel_id, ref_id=ref_id, payload=payload or {})
        s.add(j)
        s.commit()
        s.refresh(j)
    bus.publish("job", job_dict(j))
    _wake.set()
    return j


def cancel(job_id: int) -> None:
    with session() as s:
        j = s.get(Job, job_id)
        if j and j.status in ("queued", "running"):
            j.status = "cancelled"
            j.finished_at = now()
            s.add(j)
            s.commit()
            bus.publish("job", job_dict(j))


# ---------------------------------------------------------------- workers

_wake = threading.Event()
_claim_lock = threading.Lock()


def _claim(heavy: bool) -> Job | None:
    with _claim_lock, session() as s:
        q = select(Job).where(Job.status == "queued").order_by(Job.id)
        for j in s.exec(q).all():
            if (j.payload or {}).get("_not_before", 0) > time.time():
                continue  # esperando a cota de IA voltar
            if (j.kind in HEAVY_KINDS) == heavy:
                j.status = "running"
                j.started_at = now()
                s.add(j)
                s.commit()
                s.refresh(j)
                return j
    return None


def _keep_awake(on: bool) -> None:
    """Impede o Windows de dormir enquanto uma tarefa roda (vale por thread)."""
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))
    except Exception:  # noqa: BLE001
        pass


def _run(job: Job) -> None:
    _keep_awake(True)
    try:
        _run_inner(job)
    finally:
        _keep_awake(False)


def _run_inner(job: Job) -> None:
    fn = HANDLERS.get(job.kind)
    ctx = JobContext(job)
    bus.publish("job", job_dict(job))
    try:
        if fn is None:
            raise RuntimeError(f"Tipo de tarefa desconhecido: {job.kind}")
        result = fn(ctx) or {}
        status, error = "done", ""
    except Cancelled:
        result, status, error = {}, "cancelled", ""
    except Exception as e:  # noqa: BLE001
        if _quota_exhausted(e) and _postpone(job):
            return
        log.exception("job %s falhou", job.id)
        result, status, error = {}, "failed", f"{e}\n\n{traceback.format_exc()[-3000:]}"
    with session() as s:
        j = s.get(Job, job.id)
        if j.status != "cancelled":
            j.status = status
        j.error = error
        j.result = result
        if status == "done":
            j.progress = 1.0
            j.stage = "Concluído"
        j.finished_at = now()
        s.add(j)
        s.commit()
        bus.publish("job", job_dict(j))


RETRY_MINUTES = 20
MAX_RETRIES = 6


def _quota_exhausted(e: Exception) -> bool:
    """Todas as IAs sem cota no momento (Gemini em espera, GLM 429...) — vale esperar e tentar de novo."""
    return type(e).__name__ == "LLMError" and "Nenhum LLM disponível" in str(e)


def _postpone(job: Job) -> bool:
    with session() as s:
        j = s.get(Job, job.id)
        if j is None or j.status == "cancelled":
            return False
        tries = int((j.payload or {}).get("_retries", 0))
        if tries >= MAX_RETRIES:
            return False
        at = time.time() + RETRY_MINUTES * 60
        j.payload = {**(j.payload or {}), "_retries": tries + 1, "_not_before": at}
        j.status, j.progress = "queued", 0.0
        j.stage = f"Sem cota de IA agora — tenta de novo às {time.strftime('%H:%M', time.localtime(at))}"
        j.log = (j.log or "") + f"[{time.strftime('%H:%M:%S')}] {j.stage} (tentativa {tries + 1}/{MAX_RETRIES})\n"
        s.add(j)
        s.commit()
        bus.publish("job", job_dict(j))
    log.info("job %s adiado: sem cota de IA", job.id)
    return True


def _worker(heavy: bool) -> None:
    while True:
        job = _claim(heavy)
        if job is None:
            _wake.wait(timeout=2)
            _wake.clear()
            continue
        _run(job)


def start_workers(light: int = 3) -> None:
    from .models import Video
    with session() as s:
        # vídeos que ficaram "renderizando" de uma execução interrompida (a tarefa recria o vídeo do zero)
        for v in s.exec(select(Video).where(Video.status == "rendering")).all():
            s.delete(v)
        s.commit()
    # Tarefas interrompidas por reinício voltam para a fila
    with session() as s:
        for j in s.exec(select(Job).where(Job.status == "running")).all():
            j.status = "queued"
            s.add(j)
        s.commit()
    threading.Thread(target=_worker, args=(True,), daemon=True, name="worker-render").start()
    for i in range(light):
        threading.Thread(target=_worker, args=(False,), daemon=True, name=f"worker-{i}").start()
