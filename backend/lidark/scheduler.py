"""Agendador: publicações agendadas, piloto automático por horário e coleta de métricas."""
from __future__ import annotations

import json
import logging
import random
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import func, select

from . import config
from .config import DATA_DIR
from .db import session
from .jobs import enqueue
from .models import Channel, Idea, Job, Publication, now

log = logging.getLogger("lidark.scheduler")
STATE = DATA_DIR / "scheduler_state.json"
LEAD_MINUTES = 75  # produz o vídeo com antecedência ao horário de postagem
_sched: BackgroundScheduler | None = None


def _state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:  # noqa: BLE001
        return {}


def _save(st: dict) -> None:
    STATE.write_text(json.dumps(st))


# envia ao YouTube como privado antes do horário; o YouTube publica sozinho na hora (já processado em HD)
PRE_UPLOAD = timedelta(minutes=35)


def due_publications() -> None:
    with session() as s:
        due = s.exec(select(Publication).where(Publication.status == "scheduled",
                                               Publication.scheduled_at <= now() + PRE_UPLOAD)).all()
        for p in due:
            p.status = "uploading"
            s.add(p)
        s.commit()
    for p in due:
        enqueue("publish", title=f"Publicar no {p.platform}: {p.title}", channel_id=p.channel_id, ref_id=p.id)


WEEKDAYS = {"seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "sáb": 5, "dom": 6}
LEAD = {"short": timedelta(minutes=75), "long": timedelta(hours=4)}  # vídeo longo leva mais tempo para renderizar


def parse_slot(slot: str) -> tuple[int | None, int, int, str] | None:
    """'19:00' → Short todo dia · 'dom 18:00 longo' → vídeo longo aos domingos."""
    parts = slot.lower().replace(",", " ").split()
    day, fmt, hm = None, "short", None
    for p in parts:
        if p[:3] in WEEKDAYS:
            day = WEEKDAYS[p[:3]]
        elif p.startswith("long"):
            fmt = "long"
        elif ":" in p:
            hm = p
    if not hm:
        return None
    try:
        hh, mm = (int(x) for x in hm.split(":"))
    except ValueError:
        return None
    return day, hh, mm, fmt


def autopilot_tick() -> None:
    """Para cada canal no piloto automático, dispara a produção com antecedência a cada horário."""
    st = _state()
    local_now = datetime.now()
    with session() as s:
        chans = s.exec(select(Channel).where(Channel.auto_pilot == True)).all()  # noqa: E712
    from . import posting_times
    for ch in chans:
        auto = posting_times.settings(ch)["mode"] == "auto"
        try:
            slots = posting_times.auto_slots(ch) if auto else (ch.posting_slots or [])
        except Exception as e:  # noqa: BLE001
            log.warning("horários automáticos falharam (%s): usando os fixos", e)
            slots = ch.posting_slots or []
        for slot in slots:
            parsed = parse_slot(slot)
            if not parsed:
                continue
            day, hh, mm, fmt = parsed
            if fmt not in (ch.formats or ["short"]):
                continue
            target = local_now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if day is not None:
                target += timedelta(days=(day - target.weekday()) % 7)
            if target < local_now:
                target += timedelta(days=7 if day is not None else 1)
            if timedelta(0) <= target - local_now <= LEAD[fmt]:
                key = f"{ch.id}|{target:%Y-%m-%d %H:%M}|{fmt}"
                if st.get(key):
                    continue
                publish_at = (target + timedelta(minutes=random.randint(-12, 12))).astimezone()
                # sem rajadas: espaço mínimo entre posts e limite diário de canal novo
                pending = [datetime.fromisoformat(v) for k, v in st.items()
                           if k.startswith(f"{ch.id}|") and isinstance(v, str) and v[:1].isdigit()]
                why = posting_times.conflict(ch, publish_at, fmt, extra=pending)
                if why:
                    st[key] = "skip"
                    log.info("piloto automático pulou %s: %s", key, why)
                    continue
                st[key] = publish_at.isoformat()
                enqueue("autopilot", title=f"Piloto automático: {ch.name} ({slot}{' · auto' if auto else ''})", channel_id=ch.id,
                        payload={"publish_at": publish_at.isoformat(), "format": fmt})
                log.info("piloto automático disparado: %s", key)
    cutoff = (local_now - timedelta(days=8)).strftime("%Y-%m-%d")
    _save({k: v for k, v in st.items() if k.split("|")[1][:10] >= cutoff})


def keep_ideas_stocked() -> None:
    with session() as s:
        chans = s.exec(select(Channel).where(Channel.auto_pilot == True)).all()  # noqa: E712
        for ch in chans:
            n = s.exec(select(func.count()).select_from(Idea).where(
                Idea.channel_id == ch.id, Idea.status.in_(["new", "approved"]))).one()
            busy = s.exec(select(func.count()).select_from(Job).where(
                Job.channel_id == ch.id, Job.kind == "discover_ideas", Job.status.in_(["queued", "running"]))).one()
            if n < 6 and not busy:
                enqueue("discover_ideas", title=f"Repor pautas: {ch.name}", channel_id=ch.id, payload={"count": 8})
            from .growth import active_campaign, campaign_tag
            camp = active_campaign(ch)
            if camp and not busy:
                have = [i for i in s.exec(select(Idea).where(Idea.channel_id == ch.id, Idea.status.in_(["new", "approved"]))).all()
                        if campaign_tag(camp) in (i.tags or [])]
                if len(have) < 4:
                    enqueue("discover_ideas", title=f"Pautas da campanha: {camp['name']}", channel_id=ch.id,
                            payload={"count": 6, "campaign": camp["id"]})
            if "long" in (ch.formats or []) and not busy:
                nl = s.exec(select(func.count()).select_from(Idea).where(
                    Idea.channel_id == ch.id, Idea.format == "long", Idea.status.in_(["new", "approved"]))).one()
                if nl < 2:
                    enqueue("discover_ideas", title=f"Repor pautas longas: {ch.name}", channel_id=ch.id,
                            payload={"count": 4, "format": "long"})


def backup_db(keep: int = 14) -> None:
    """Cópia diária e consistente do banco (data/backups), guardando as últimas 14."""
    import sqlite3
    from .config import DB_PATH
    folder = DATA_DIR / "backups"
    folder.mkdir(exist_ok=True)
    dest = folder / f"lidark-{datetime.now():%Y-%m-%d}.db"
    if dest.exists():
        return
    src = sqlite3.connect(DB_PATH)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    for old in sorted(folder.glob("lidark-*.db"))[:-keep]:
        old.unlink(missing_ok=True)
    log.info("backup salvo: %s", dest.name)


def trend_radar_all() -> None:
    """Todo dia: radar de tendências para os canais conectados."""
    from .models import Account
    if not config.get("trend_radar_enabled"):
        return
    with session() as s:
        ids = {a.channel_id for a in s.exec(select(Account).where(Account.platform == "youtube")).all() if a.credentials}
        names = {c.id: c.name for c in s.exec(select(Channel)).all()}
    for cid in ids:
        enqueue("trend_radar", title=f"Radar de tendências: {names.get(cid, cid)}", channel_id=cid)


def cloud_backup() -> None:
    from .cloud import TOKEN
    if TOKEN.exists():
        enqueue("cloud_backup", title="Backup na nuvem (Google Drive)")


def fetch_comments() -> None:
    enqueue("fetch_comments", title="Buscar comentários novos")


def collect_metrics() -> None:
    enqueue("collect_metrics", title="Coletar métricas")


def start() -> None:
    global _sched
    if _sched:
        return
    _sched = BackgroundScheduler(daemon=True)
    _sched.add_job(due_publications, "interval", minutes=1, id="due", max_instances=1, coalesce=True)
    _sched.add_job(autopilot_tick, "interval", minutes=1, id="autopilot", max_instances=1, coalesce=True)
    _sched.add_job(keep_ideas_stocked, "interval", hours=3, id="ideas", max_instances=1, coalesce=True,
                   next_run_time=datetime.now() + timedelta(minutes=5))
    _sched.add_job(collect_metrics, "interval", hours=6, id="metrics", max_instances=1, coalesce=True,
                   next_run_time=datetime.now() + timedelta(minutes=2))
    _sched.add_job(trend_radar_all, "cron", hour=7, minute=0, id="radar", max_instances=1, coalesce=True)
    _sched.add_job(fetch_comments, "interval", hours=2, id="comments", max_instances=1, coalesce=True,
                   next_run_time=datetime.now() + timedelta(minutes=8))
    _sched.add_job(backup_db, "cron", hour=3, minute=0, id="backup", max_instances=1, coalesce=True)
    _sched.add_job(cloud_backup, "cron", hour=3, minute=20, id="cloud_backup", max_instances=1, coalesce=True)
    from .notify import send_daily
    _sched.add_job(send_daily, "cron", hour=21, minute=0, id="daily_summary", max_instances=1, coalesce=True)
    _sched.add_job(backup_db, "date", run_date=datetime.now() + timedelta(seconds=30), id="backup_boot")
    from .channels import sync_all
    _sched.add_job(sync_all, "interval", hours=12, id="sync", max_instances=1, coalesce=True)
    _sched.start()
    log.info("agendador iniciado")
