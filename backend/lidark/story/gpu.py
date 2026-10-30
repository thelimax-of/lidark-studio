"""Trava de GPU entre processos: geração de imagem local (SD no RTX 3050 6 GB) e render/encode não podem
disputar a placa ao mesmo tempo (falta VRAM e os dois ficam lentos).

Protocolo (o worker local, em outro processo/venv, usa o MESMO arquivo):
    arquivo  data/story/gpu.lock
    trava    msvcrt.locking(fd, LK_NBLCK, 1) no byte 0 (Windows) / fcntl.flock(fd, LOCK_EX|LOCK_NB) (outros)
    dono     data/story/gpu.owner (json {"owner", "pid", "since"}) — só informativo, para o painel
Quem não conseguir a trava espera (tentando a cada 0,5 s) até `timeout`; estourou → segue sem a trava
(render nunca trava a produção para sempre) e registra no log.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from contextlib import contextmanager
from typing import Iterator

from ..config import DATA_DIR

log = logging.getLogger("lidark.story.gpu")
LOCK_PATH = DATA_DIR / "story" / "gpu.lock"
OWNER_PATH = DATA_DIR / "story" / "gpu.owner"
_local = threading.Lock()  # dentro do mesmo processo, threads também fazem fila


def _try_lock(fd: int) -> bool:
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(fd: int) -> None:
    try:
        if os.name == "nt":
            import msvcrt
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


@contextmanager
def gpu_lock(owner: str, timeout: float = 1800, poll: float = 0.5, on_wait=None) -> Iterator[bool]:
    """with gpu_lock("render") as got: ...  — got=False se esperou `timeout` e seguiu sem a trava."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    if not _local.acquire(timeout=timeout):
        log.warning("GPU: %s esperou %.0fs (thread local) e seguiu sem trava", owner, timeout)
        yield False
        return
    fd = os.open(str(LOCK_PATH), os.O_RDWR | os.O_CREAT)
    got = False
    try:
        warned = False
        while True:
            if _try_lock(fd):
                got = True
                break
            if time.time() - t0 > timeout:
                log.warning("GPU: %s esperou %.0fs e seguiu sem a trava", owner, timeout)
                break
            if on_wait and not warned:
                warned = True
                try:
                    on_wait(holder())
                except Exception:  # noqa: BLE001
                    pass
            time.sleep(poll)
        if got:
            try:
                OWNER_PATH.write_text(json.dumps({"owner": owner, "pid": os.getpid(), "since": time.time()}), encoding="utf-8")
            except OSError:
                pass
        yield got
    finally:
        if got:
            try:
                OWNER_PATH.unlink(missing_ok=True)
            except OSError:
                pass
            _unlock(fd)
        os.close(fd)
        _local.release()


def holder() -> dict | None:
    """Quem está com a GPU agora (None = livre)."""
    if not OWNER_PATH.exists():
        return None
    try:
        return json.loads(OWNER_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
