"""Melhores horários de postagem por canal, a partir dos dados (com um "palpite inicial" para canais novos).

A API do YouTube Analytics não informa "quando seu público está online" por hora. Então medimos o que dá:
quantas visualizações cada Short fez nas primeiras ~24 h (snapshots de métricas + Publication.published_at),
agrupado pela hora/dia da semana em que saiu (horário de Brasília). Com poucas amostras, o resultado é
puxado para um perfil típico de público brasileiro de Shorts (pico no almoço 11–13 h e à noite 18–21 h).

Também guarda as travas contra "rajadas": espaço mínimo entre posts e limite diário para canais novos.
"""
from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlmodel import select

from .db import session
from .models import Channel, MetricSnapshot, Publication, Video

TZ = ZoneInfo("America/Sao_Paulo")
WEEKDAY_NAMES = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

# Perfil típico de público brasileiro de Shorts (multiplicador relativo, 1.0 = média do dia).
PRIOR = [0.35, 0.2, 0.12, 0.1, 0.1, 0.15, 0.35, 0.55, 0.65, 0.7, 0.8, 1.0,
         1.15, 1.05, 0.85, 0.8, 0.85, 0.95, 1.1, 1.25, 1.3, 1.2, 0.95, 0.6]
WINDOW = (8, 22)  # só agenda entre 8 h e 22 h
HORIZON_H = 24  # janela da medição: views nas primeiras 24 h
KERNEL_SIGMA = 1.5  # suaviza entre horas vizinhas (amostras são poucas)
SHRINK_K = 4.0  # quantas "amostras equivalentes" o palpite inicial vale por hora
MIN_SAMPLES = 3  # abaixo disso, só o palpite inicial

DEFAULTS = {
    "mode": "manual",  # manual (horários fixos) | auto (pelos dados)
    "per_day": 2,  # Shorts por dia no modo automático
    "min_gap_hours": 3.5,  # espaço mínimo entre dois posts do canal
    "new_channel_cap": 3,  # máximo de Shorts/dia enquanto o canal é novo
    "new_channel_days": 30,  # até quantos dias o canal conta como "novo"
}


def settings(ch: Channel) -> dict[str, Any]:
    raw = getattr(ch, "schedule", None) or {}
    out = {**DEFAULTS, **{k: v for k, v in raw.items() if v not in (None, "")}}
    out["per_day"] = max(1, min(8, int(out["per_day"])))
    out["min_gap_hours"] = max(0.0, min(12.0, float(out["min_gap_hours"])))
    out["new_channel_cap"] = max(1, min(10, int(out["new_channel_cap"])))
    out["new_channel_days"] = max(0, int(out["new_channel_days"]))
    return out


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _is_short(p: Publication, fmt: dict[int, str]) -> bool:
    if p.video_id and p.video_id in fmt:
        return fmt[p.video_id] == "short"
    return not p.duration or p.duration <= 180


def _views_at(pub_at: datetime, snaps: list[MetricSnapshot], hours: float, field: str = "views") -> float | None:
    """Views em `hours` após publicar, interpolando entre snapshots. None se não houver medição perto disso."""
    pts = [(0.0, 0.0)]
    for m in snaps:
        age = (_utc(m.captured_at) - pub_at).total_seconds() / 3600
        val = getattr(m, field, 0) or 0
        if age > 0 and (val or field == "views"):
            pts.append((age, float(val)))
    pts.sort()
    if pts[-1][0] < hours * 0.75:  # ainda novo demais (ou sem medição): não dá para comparar
        return None
    for (a0, v0), (a1, v1) in zip(pts, pts[1:]):
        if a0 <= hours <= a1:
            if a1 > hours * 2:  # primeira leitura só depois de 48 h (vídeo importado): não serve
                return None
            return v0 + (v1 - v0) * (hours - a0) / (a1 - a0) if a1 > a0 else v1
    return pts[-1][1]  # última leitura entre 18 h e 24 h


def _channel_age_days(ch: Channel, pubs: list[Publication]) -> float:
    first = min([_utc(p.published_at) for p in pubs if p.published_at] + [_utc(ch.created_at)])
    return (datetime.now(timezone.utc) - first).total_seconds() / 86400


def _circ(a: float, b: float) -> float:
    d = abs(a - b) % 24
    return min(d, 24 - d)


def suggest(channel_id: int) -> dict[str, Any]:
    """Horários sugeridos (Brasília) + o porquê: amostras, peso dos dados × palpite e notas."""
    with session() as s:
        ch = s.get(Channel, channel_id)
        if not ch:
            return {}
        pubs = s.exec(select(Publication).where(Publication.channel_id == channel_id,
                                                Publication.status == "published")).all()
        fmt = {v.id: v.format for v in s.exec(select(Video).where(Video.channel_id == channel_id)).all()}
        snaps: dict[int, list[MetricSnapshot]] = {}
        for m in s.exec(select(MetricSnapshot).where(MetricSnapshot.channel_id == channel_id)).all():
            snaps.setdefault(m.publication_id, []).append(m)
    cfg = settings(ch)
    shorts = [p for p in pubs if p.published_at and _is_short(p, fmt)]
    times = sorted(_utc(p.published_at) for p in shorts)

    samples = []
    for p in shorts:
        at = _utc(p.published_at)
        v = _views_at(at, snaps.get(p.id, []), HORIZON_H)
        if v is None:
            continue
        # posts na mesma janela de 3 h dividem o teste inicial no feed: pesam menos
        crowd = sum(1 for t in times if t != at and abs((t - at).total_seconds()) < 3 * 3600)
        local = at.astimezone(TZ)
        eng = _views_at(at, snaps.get(p.id, []), HORIZON_H, "engaged_views")  # só informativo (nem toda leitura traz)
        samples.append({"publication_id": p.id, "title": p.title, "hour": local.hour + local.minute / 60,
                        "weekday": local.weekday(), "views_24h": round(v), "crowded": crowd,
                        "engaged_24h": round(eng) if eng is not None else None,
                        "weight": 1 / (1 + crowd)})
    use_data = len(samples) >= MIN_SAMPLES
    if samples:
        mean = sum(math.log1p(x["views_24h"]) for x in samples) / len(samples)
        for x in samples:
            x["rel"] = max(-1.1, min(1.1, math.log1p(x["views_24h"]) - mean))  # log do "quanto acima da média"
        # o que o palpite já esperava de cada hora sai da conta: os dados só corrigem o palpite
        pmean = sum(math.log(PRIOR[int(x["hour"])]) for x in samples) / len(samples)
        for x in samples:
            x["resid"] = max(-1.1, min(1.1, x["rel"] - (math.log(PRIOR[int(x["hour"])]) - pmean)))

    hours = []
    for h in range(24):
        kern = [x["weight"] * math.exp(-_circ(h, x["hour"]) ** 2 / (2 * KERNEL_SIGMA ** 2)) for x in samples] if use_data else []
        n = sum(kern)
        data_log = sum(k * x["rel"] for k, x in zip(kern, samples)) / n if n > 1e-6 else 0.0
        fix = sum(k * x["resid"] for k, x in zip(kern, samples)) / n if n > 1e-6 else 0.0
        alpha = n / (n + SHRINK_K)
        score = PRIOR[h] * math.exp(alpha * fix)  # palpite corrigido pelos dados, na proporção das amostras
        hours.append({"hour": h, "score": round(score, 3), "prior": PRIOR[h], "samples": round(n, 2),
                      "data_weight": round(alpha, 2), "data_mult": round(math.exp(data_log), 2) if n > 1e-6 else None})

    weekdays = []
    for d in range(7):
        xs = [x for x in samples if x["weekday"] == d]
        n = sum(x["weight"] for x in xs)
        mult = math.exp(sum(x["weight"] * x["rel"] for x in xs) / (n + SHRINK_K))  # encolhido para 1.0 com poucas amostras
        weekdays.append({"weekday": WEEKDAY_NAMES[d], "samples": len(xs), "mult": round(mult, 2)})

    age = _channel_age_days(ch, pubs)
    young = age < cfg["new_channel_days"]
    per_day = min(cfg["per_day"], cfg["new_channel_cap"]) if young else cfg["per_day"]
    picks = _pick(hours, per_day, cfg["min_gap_hours"])
    data_w = sum(hours[h]["data_weight"] for h in picks) / len(picks) if picks else 0
    basis = []
    if not use_data:
        basis.append(f"Só {len(samples)} Short(s) com medição de 24 h (mínimo {MIN_SAMPLES}): horários do perfil típico "
                     "do público brasileiro de Shorts (almoço 11–13 h e noite 18–21 h).")
    else:
        basis.append(f"{len(samples)} Shorts medidos nas primeiras 24 h, comparados pela hora em que saíram; "
                     f"nos horários escolhidos os dados corrigem o perfil típico com peso ~{round(data_w * 100)}%.")
    crowded = sum(1 for x in samples if x["crowded"])
    if crowded:
        basis.append(f"{crowded} desses vídeos saíram colados em outros (menos de 3 h) e pesam menos — rajadas dividem o teste inicial.")
    if young:
        basis.append(f"Canal novo ({age:.0f} dia(s)): no máximo {cfg['new_channel_cap']} Shorts/dia até {cfg['new_channel_days']} dias.")
    basis.append(f"Espaço mínimo entre posts: {cfg['min_gap_hours']:g} h. Fuso: Brasília.")
    return {"channel_id": channel_id, "name": ch.name, "mode": cfg["mode"], "settings": cfg,
            "slots": [f"{h:02d}:00" for h in sorted(picks)], "per_day": per_day,
            "young": young, "age_days": round(age, 1), "samples": len(samples), "uses_data": use_data,
            "basis": basis, "hours": hours, "weekdays": weekdays,
            "videos": sorted(({k: v for k, v in x.items() if k not in ("rel", "resid", "weight")} for x in samples),
                             key=lambda x: -x["views_24h"])[:30]}


def _pick(hours: list[dict], n: int, gap: float) -> list[int]:
    """Melhores horas da janela, respeitando o espaço mínimo entre elas."""
    ranked = sorted((h for h in hours if WINDOW[0] <= h["hour"] <= WINDOW[1]), key=lambda h: -h["score"])
    for g in (gap, gap * 0.75, gap * 0.5):  # se não couber, aperta o espaço aos poucos
        picks: list[int] = []
        for h in ranked:
            if all(_circ(h["hour"], p) >= g for p in picks):
                picks.append(h["hour"])
            if len(picks) >= n:
                return picks
    return picks


_cache: dict[int, tuple[float, dict]] = {}


def cached(channel_id: int, ttl: float = 3600) -> dict[str, Any]:
    hit = _cache.get(channel_id)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    out = suggest(channel_id)
    _cache[channel_id] = (time.time(), out)
    return out


def auto_slots(ch: Channel) -> list[str]:
    """Horários do piloto no modo automático: Shorts pelos dados + vídeos longos dos horários fixos."""
    longs = [x for x in ch.posting_slots or [] if "long" in str(x).lower()]
    r = cached(ch.id)
    if r.get("settings") != settings(ch):  # configuração mudou no painel: recalcula na hora
        _cache.pop(ch.id, None)
        r = cached(ch.id)
    return r.get("slots", []) + longs


# ---------------------------------------------------------------- travas contra rajadas

def _busy_times(channel_id: int) -> list[tuple[datetime, bool]]:
    """(horário UTC, é Short) de cada post publicado/agendado do canal nos últimos/próximos dias."""
    since = datetime.now(timezone.utc) - timedelta(days=2)
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.channel_id == channel_id,
                                                Publication.status.in_(["scheduled", "uploading", "published"]))).all()
        fmt = {v.id: v.format for v in s.exec(select(Video).where(Video.channel_id == channel_id)).all()}
    out, seen = [], set()
    for p in pubs:
        t = _utc(p.published_at if p.status == "published" else p.scheduled_at)
        key = p.video_id or p.external_id or p.id  # o mesmo vídeo em 2 contas conta uma vez
        if t and t >= since and key not in seen:
            seen.add(key)
            out.append((t, _is_short(p, fmt)))
    return out


def _guard(ch: Channel, extra: list[datetime] | None = None) -> tuple[dict, list, bool]:
    cfg = settings(ch)
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.channel_id == ch.id,
                                                Publication.status == "published")).all()
    busy = _busy_times(ch.id)
    # disparos do piloto que ainda não viraram publicação (os que já viraram estão a ±12 min de uma)
    busy += [(_utc(t), True) for t in extra or [] if all(abs(_utc(t) - b) > timedelta(minutes=20) for b, _ in busy)]
    return cfg, busy, _channel_age_days(ch, pubs) < cfg["new_channel_days"]


def _why(cfg: dict, busy: list, young: bool, when: datetime, fmt: str) -> str | None:
    gap = timedelta(hours=cfg["min_gap_hours"])
    for t, _ in busy:
        if abs(t - when) < gap:
            return f"outro post às {t.astimezone(TZ):%d/%m %H:%M} (espaço mínimo {cfg['min_gap_hours']:g} h)"
    if fmt == "short" and young:
        day = when.astimezone(TZ).date()
        n = sum(1 for t, short in busy if short and t.astimezone(TZ).date() == day)
        if n >= cfg["new_channel_cap"]:
            return f"canal novo já tem {n} Short(s) em {day:%d/%m} (limite {cfg['new_channel_cap']}/dia)"
    return None


def conflict(ch: Channel, when: datetime, fmt: str = "short", extra: list[datetime] | None = None) -> str | None:
    """Motivo para NÃO postar neste horário (espaço mínimo / limite diário de canal novo), ou None."""
    return _why(*_guard(ch, extra), _utc(when), fmt)


def next_free(ch: Channel, when: datetime, fmt: str = "short") -> datetime:
    """Primeiro horário a partir de `when` que respeita as travas (passos de 30 min, só dentro da janela)."""
    cfg, busy, young = _guard(ch)
    t = _utc(when)
    if not _why(cfg, busy, young, t, fmt):  # o horário pedido (mesmo fora da janela, se foi escolhido à mão)
        return t
    t = t.replace(minute=t.minute // 30 * 30, second=0, microsecond=0) + timedelta(minutes=30)  # segue em :00/:30
    for _ in range(14 * 48):
        if WINDOW[0] <= t.astimezone(TZ).hour <= WINDOW[1] and not _why(cfg, busy, young, t, fmt):
            return t
        t += timedelta(minutes=30)
    return _utc(when)
