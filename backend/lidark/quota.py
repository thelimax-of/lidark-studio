"""Medidor da cota diária da YouTube Data API (por projeto do Google Cloud).

Cada projeto tem 10.000 unidades/dia, que zeram à meia-noite do horário do Pacífico. Todos os canais conectados
com o mesmo client_secret.json dividem o mesmo balde. Aqui cada chamada de escrita/leitura relevante registra o
que gastou e as tarefas perguntam antes de gastar:

    quota.can(400, "captions")   → pode enviar uma legenda agora?
    quota.spend(400, "captions.insert")

Prioridades (da mais importante para a menos): upload > metadata > captions > comments > metrics > search.
Passou de 80% do dia, só upload e metadata (miniatura, playlist, título/descrição) continuam; o resto fica para
depois da renovação (reset_at()). Ao cruzar 80% sai uma notificação (uma por projeto por dia).

Envio de vídeo (videos.insert): a tabela oficial fala em ~1.600 unidades, mas este sistema publica 18–20 vídeos/dia
no mesmo projeto sem nunca receber quotaExceeded — o envio está num balde próprio (limite de envios/dia). Por isso o
padrão é "separate": conta 1 envio no balde de envios e não desconta dos 10.000. Com upload_bucket = "shared", cada
envio desconta 1.600 do balde principal (modo conservador).
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from .config import DATA_DIR, SECRETS_DIR

log = logging.getLogger("lidark.quota")

STORE = DATA_DIR / "yt_quota.json"
PT = ZoneInfo("America/Los_Angeles")
DAILY_LIMIT = 10_000
SOFT_LINE = 0.8  # acima disso só o que é prioridade alta

# custo de cada tipo de chamada (unidades da Data API)
COSTS: dict[str, int] = {
    "upload": 1600,  # videos.insert (ver nota do balde de envios acima)
    "videos.update": 50,
    "thumbnail": 50,  # thumbnails.set
    "playlist": 50,  # playlists.insert / playlistItems.insert
    "captions.insert": 400,
    "comment": 50,  # commentThreads.insert / comments.insert
    "search": 100,
    "list": 1,  # qualquer *.list (videos, channels, playlistItems, captions)
}
PRIORITIES = ["upload", "metadata", "captions", "comments", "metrics", "search"]
KIND_PRIORITY = {"upload": "upload", "videos.update": "metadata", "thumbnail": "metadata", "playlist": "metadata",
                 "localizations": "metadata", "captions.insert": "captions", "captions": "captions",
                 "comment": "comments", "comments": "comments", "list": "metrics", "metrics": "metrics",
                 "search": "search"}
HIGH = {"upload", "metadata"}  # não esperam pelos 80%

DEFAULT_SETTINGS = {"daily_limit": DAILY_LIMIT, "upload_bucket": "separate", "upload_limit": 100}
_lock = threading.Lock()


# ---------------------------------------------------------------- armazenamento

def _load() -> dict[str, Any]:
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _save(d: dict[str, Any]) -> None:
    days = sorted((d.get("days") or {}).keys())
    for old in days[:-14]:  # guarda 2 semanas de histórico
        d["days"].pop(old, None)
    tmp = STORE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(STORE)


def settings() -> dict[str, Any]:
    raw = _load().get("settings") or {}
    out = {**DEFAULT_SETTINGS, **{k: v for k, v in raw.items() if v not in (None, "")}}
    try:
        from . import config
        if not raw.get("daily_limit") and config.get("yt_daily_quota"):
            out["daily_limit"] = int(config.get("yt_daily_quota"))
    except Exception:  # noqa: BLE001
        pass
    out["daily_limit"] = max(100, int(out["daily_limit"]))
    out["upload_limit"] = max(1, int(out["upload_limit"]))
    out["upload_bucket"] = "shared" if out["upload_bucket"] == "shared" else "separate"
    return out


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        d = _load()
        cur = dict(d.get("settings") or {})
        for k in DEFAULT_SETTINGS:
            if k in patch:
                cur[k] = patch[k]
        d["settings"] = cur
        _save(d)
    return settings()


# ---------------------------------------------------------------- projeto e dia

def project_of(acc_or_creds: Any = None) -> str:
    """Projeto do Google Cloud = número antes do '-' no client_id (todas as contas do mesmo client dividem a cota)."""
    creds = getattr(acc_or_creds, "credentials", acc_or_creds) if acc_or_creds is not None else None
    cid = (creds or {}).get("client_id") if isinstance(creds, dict) else None
    if not cid:
        try:
            raw = json.loads((SECRETS_DIR / "client_secret.json").read_text(encoding="utf-8"))
            cid = (raw.get("installed") or raw.get("web") or {}).get("client_id")
        except Exception:  # noqa: BLE001
            cid = None
    return str(cid).split("-")[0] if cid else "default"


def day_key(at: datetime | None = None) -> str:
    return (at or datetime.now(timezone.utc)).astimezone(PT).strftime("%Y-%m-%d")


def reset_at() -> datetime:
    """Próxima renovação da cota (meia-noite do Pacífico + 5 min de folga), em UTC."""
    t = datetime.now(PT).replace(hour=0, minute=5, second=0, microsecond=0) + timedelta(days=1)
    return t.astimezone(timezone.utc)


def _bucket(d: dict[str, Any], project: str) -> dict[str, Any]:
    day = d.setdefault("days", {}).setdefault(day_key(), {})
    return day.setdefault(project, {"units": 0, "uploads": 0, "kinds": {}, "warned": False, "deferred": 0})


# ---------------------------------------------------------------- uso

def used(project: str | None = None) -> int:
    p = project or project_of()
    b = ((_load().get("days") or {}).get(day_key()) or {}).get(p) or {}
    return int(b.get("units") or 0)


def uploads_today(project: str | None = None) -> int:
    p = project or project_of()
    b = ((_load().get("days") or {}).get(day_key()) or {}).get(p) or {}
    return int(b.get("uploads") or 0)


def _priority(priority: str | int) -> str:
    if isinstance(priority, int):
        return PRIORITIES[max(0, min(len(PRIORITIES) - 1, priority))]
    return KIND_PRIORITY.get(priority, priority if priority in PRIORITIES else "metrics")


def can(units: int, priority: str | int = "metadata", project: str | None = None) -> bool:
    """Dá para gastar `units` agora com esta prioridade? (alta prioridade só para no teto; o resto para nos 80%)"""
    cfg = settings()
    pr = _priority(priority)
    p = project or project_of()
    if pr == "upload" and cfg["upload_bucket"] == "separate":
        return uploads_today(p) < cfg["upload_limit"]
    total = used(p) + max(0, int(units))
    if total > cfg["daily_limit"]:
        return False
    return pr in HIGH or total <= cfg["daily_limit"] * SOFT_LINE


def spend(units: int, kind: str, project: str | None = None) -> int:
    """Registra o gasto (nunca levanta erro). Devolve o total do dia no projeto."""
    try:
        cfg = settings()
        p = project or project_of()
        with _lock:
            d = _load()
            b = _bucket(d, p)
            before = int(b["units"])
            add = max(0, int(units))
            if kind == "upload":
                b["uploads"] = int(b.get("uploads") or 0) + 1
                if cfg["upload_bucket"] == "separate":
                    add = 0
            b["units"] = before + add
            b["kinds"][kind] = int(b["kinds"].get(kind) or 0) + add
            if kind == "upload":
                b["kinds"]["upload_count"] = int(b["kinds"].get("upload_count") or 0) + 1
            cross = not b.get("warned") and before < cfg["daily_limit"] * SOFT_LINE <= b["units"]
            if cross:
                b["warned"] = True
            total = b["units"]
            _save(d)
        if cross:
            _warn(p, total, cfg["daily_limit"])
        return total
    except Exception as e:  # noqa: BLE001
        log.warning("cota: gasto não registrado (%s)", e)
        return 0


def note_deferred(kind: str, project: str | None = None) -> None:
    """Conta quantas chamadas ficaram para depois (aparece no painel)."""
    try:
        with _lock:
            d = _load()
            b = _bucket(d, project or project_of())
            b["deferred"] = int(b.get("deferred") or 0) + 1
            b.setdefault("deferred_kinds", {})[kind] = int((b.get("deferred_kinds") or {}).get(kind) or 0) + 1
            _save(d)
    except Exception:  # noqa: BLE001
        pass


def guard(kind: str, units: int | None = None, project: str | None = None) -> bool:
    """can() + registra o adiamento quando não pode. Uso: `if not quota.guard("captions.insert"): adiar`."""
    u = COSTS.get(kind, 1) if units is None else units
    ok = can(u, kind, project)
    if not ok:
        note_deferred(kind, project)
    return ok


def _warn(project: str, total: int, limit: int) -> None:
    try:
        from . import notify
        notify.push("quota", f"Cota do YouTube em {round(total / limit * 100)}%",
                    f"{total:,} de {limit:,} unidades usadas hoje (projeto {project}). Daqui até a renovação "
                    f"({reset_at().astimezone():%H:%M}), só envios e metadados; legendas, comentários, métricas e buscas "
                    "esperam a cota renovar.".replace(",", "."),
                    link="/publicacao", key=f"ytquota80:{project}:{day_key()}", tags=["warning"], priority=3)
    except Exception as e:  # noqa: BLE001
        log.warning("aviso de cota: %s", e)


def status() -> dict[str, Any]:
    cfg = settings()
    d = _load()
    today = (d.get("days") or {}).get(day_key()) or {}
    projects = []
    for p in sorted(set(today) | {project_of()}):
        b = today.get(p) or {}
        u = int(b.get("units") or 0)
        projects.append({
            "project": p, "used": u, "limit": cfg["daily_limit"], "pct": round(u / cfg["daily_limit"] * 100, 1),
            "soft_line": int(cfg["daily_limit"] * SOFT_LINE), "uploads": int(b.get("uploads") or 0),
            "upload_limit": cfg["upload_limit"], "kinds": b.get("kinds") or {}, "deferred": int(b.get("deferred") or 0),
            "deferred_kinds": b.get("deferred_kinds") or {},
            "allowed": [pr for pr in PRIORITIES if can(1, pr, p)],  # prioridades que ainda passam agora
        })
    history = [{"day": k, "used": sum(int((v or {}).get("units") or 0) for v in (d.get("days") or {}).get(k, {}).values())}
               for k in sorted((d.get("days") or {}).keys())]
    return {"day": day_key(), "reset_at": reset_at().isoformat(), "settings": cfg, "costs": COSTS,
            "priorities": PRIORITIES, "projects": projects, "history": history}
