"""Cache em memória com TTL + stale-while-revalidate (dados lentos de fora, ex.: YouTube Analytics).

- fresco (< ttl): devolve na hora;
- velho (< stale): devolve o velho na hora e atualiza numa thread em segundo plano (uma por chave);
- ausente/expirado: calcula na hora. Erro também fica guardado por `error_ttl` (não martela a API a cada request).
`invalidate(prefix)` só marca como velho (o próximo request continua rápido e dispara a atualização).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from fastapi.responses import JSONResponse

try:
    import orjson
except ImportError:  # pragma: no cover — sem orjson fica o json padrão
    orjson = None

log = logging.getLogger("lidark.cache")


class FastJSON(JSONResponse):
    """JSON com orjson (bem mais rápido nas listas grandes); mesmo formato do JSONResponse."""

    def render(self, content: Any) -> bytes:
        if orjson is None:
            return super().render(content)
        return orjson.dumps(content, option=orjson.OPT_NON_STR_KEYS | orjson.OPT_SERIALIZE_NUMPY)

_lock = threading.Lock()
_data: dict[str, tuple[float, Any, BaseException | None]] = {}  # chave → (quando, valor, erro)
_refreshing: set[str] = set()
_key_locks: dict[str, threading.Lock] = {}
_dirty: set[str] = set()  # invalidadas: servem o valor velho e atualizam em segundo plano


def get(key: str, fn: Callable[[], Any], ttl: float = 900, stale: float = 86400, error_ttl: float = 120) -> Any:
    t = time.time()
    with _lock:
        hit = _data.get(key)
    if hit:
        at, val, err = hit
        age = t - at
        if err is not None:
            if age < error_ttl:
                raise err
        elif age < ttl and key not in _dirty:
            return val
        elif age < stale:
            _refresh_bg(key, fn)
            return val
    with _lock:
        klock = _key_locks.setdefault(key, threading.Lock())
    with klock:  # dois requests juntos na mesma chave: só um vai à API, o outro espera e reaproveita
        with _lock:
            hit2 = _data.get(key)
        if hit2 and hit2 is not hit and hit2[2] is None:
            return hit2[1]
        return _compute(key, fn)


def _compute(key: str, fn: Callable[[], Any]) -> Any:
    try:
        val = fn()
    except Exception as e:  # noqa: BLE001
        with _lock:
            old = _data.get(key)
            if old and old[2] is None:  # tinha valor bom: mantém (fica velho) em vez de trocar por erro
                return old[1]
            _data[key] = (time.time(), None, e)
        raise
    with _lock:
        _data[key] = (time.time(), val, None)
        _dirty.discard(key)
    return val


def _refresh_bg(key: str, fn: Callable[[], Any]) -> None:
    with _lock:
        if key in _refreshing:
            return
        _refreshing.add(key)

    def run():
        try:
            val = fn()
            with _lock:
                _data[key] = (time.time(), val, None)
                _dirty.discard(key)
        except Exception as e:  # noqa: BLE001 — fica o valor velho
            log.warning("cache %s: falha ao atualizar: %s", key, e)
        finally:
            with _lock:
                _refreshing.discard(key)

    threading.Thread(target=run, daemon=True, name=f"cache:{key}"[:60]).start()


def invalidate(prefix: str = "") -> None:
    """Marca como velho (mantém o valor para servir enquanto atualiza); erros guardados são descartados."""
    with _lock:
        for k in [k for k in _data if k.startswith(prefix)]:
            if _data[k][2] is not None:
                del _data[k]
            else:
                _dirty.add(k)


def drop(prefix: str = "") -> None:
    with _lock:
        for k in [k for k in _data if k.startswith(prefix)]:
            del _data[k]
            _dirty.discard(k)


def stats() -> dict[str, Any]:
    t = time.time()
    with _lock:
        return {k: {"age_s": round(t - at), "dirty": k in _dirty, "error": str(err)[:120] if err else None} for k, (at, _v, err) in _data.items()}


# ---------------------------------------------------------------- gancho de fim de tarefa

_JOB_HOOKS: dict[str, list[Callable[[dict], None]]] = {}
_hook_installed = False


def on_job_done(kind: str, fn: Callable[[dict], None]) -> None:
    """Registra fn(job_dict) para quando uma tarefa `kind` terminar com sucesso."""
    _JOB_HOOKS.setdefault(kind, []).append(fn)
    install_job_hook()


def job_finished(data: dict) -> None:
    """Chamar quando uma tarefa termina (recebe o job_dict). Idempotente e nunca levanta."""
    if data.get("status") != "done":
        return
    for fn in _JOB_HOOKS.get(data.get("kind") or "", []):
        try:
            fn(data)
        except Exception as e:  # noqa: BLE001
            log.warning("gancho de %s: %s", data.get("kind"), e)


def install_job_hook() -> None:
    """Escuta os eventos "job" do barramento (jobs.bus) sem mexer em jobs.py: todo fim de tarefa passa por ali."""
    global _hook_installed
    if _hook_installed:
        return
    from . import jobs
    orig = jobs.bus.publish

    def publish(event: str, data: dict[str, Any]) -> None:
        orig(event, data)
        if event == "job" and isinstance(data, dict) and data.get("status") == "done" and data.get("finished_at"):
            job_finished(data)

    jobs.bus.publish = publish  # type: ignore[method-assign]
    _hook_installed = True
