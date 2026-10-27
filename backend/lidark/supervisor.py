"""Supervisor: mantém o servidor do Lidark sempre no ar.

- Sobe o servidor (uvicorn) em segundo plano, sem janela.
- Verifica a saúde a cada 20 s; se cair ou travar (3 falhas seguidas), reinicia.
- Só uma instância por vez (trava em data/supervisor.lock).

Uso: pythonw -m lidark.supervisor   (o atalho de inicialização do Windows chama isto)
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parents[1]
DATA = BACKEND.parent / "data"
LOGS = DATA / "logs"
LOGS.mkdir(parents=True, exist_ok=True)
HEALTH = "http://127.0.0.1:8765/api/health"
CREATE_NO_WINDOW = 0x08000000


def log(msg: str) -> None:
    with open(LOGS / "supervisor.log", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")


def healthy(timeout: float = 8) -> bool:
    try:
        return httpx.get(HEALTH, timeout=timeout).status_code == 200
    except Exception:  # noqa: BLE001
        return False


def single_instance():
    """Trava exclusiva: se outro supervisor já estiver rodando, este sai."""
    import msvcrt
    lock = open(DATA / "supervisor.lock", "a+")
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        sys.exit(0)
    return lock


def python_exe() -> str:
    exe = Path(sys.executable)
    # pythonw não tem console; o servidor usa python.exe (sem janela graças ao CREATE_NO_WINDOW)
    cand = exe.with_name("python.exe")
    return str(cand if cand.exists() else exe)


def run() -> None:
    _lock = single_instance()  # noqa: F841 — mantém a trava enquanto o processo vive
    log("supervisor iniciado")
    backoff = 3
    while True:
        if healthy(3):
            # já existe um servidor saudável (ex.: iniciado manualmente) — só observa
            time.sleep(30)
            continue
        out = open(LOGS / "server.log", "a", encoding="utf-8")
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        proc = subprocess.Popen([python_exe(), "-m", "uvicorn", "lidark.main:app", "--host", "127.0.0.1",
                                 "--port", "8765"], cwd=str(BACKEND), stdout=out, stderr=out, env=env,
                                creationflags=CREATE_NO_WINDOW)
        log(f"servidor iniciado (pid {proc.pid})")
        started, fails = time.time(), 0
        while True:
            time.sleep(20)
            if proc.poll() is not None:
                log(f"servidor encerrou (código {proc.returncode})")
                break
            if healthy():
                fails, backoff = 0, 3
            elif time.time() - started > 60:
                fails += 1
                log(f"servidor sem resposta ({fails}/3)")
                if fails >= 3:
                    proc.kill()
                    log("servidor reiniciado por travamento")
                    break
        out.close()
        time.sleep(backoff)
        backoff = min(60, backoff * 2)


if __name__ == "__main__":
    run()
