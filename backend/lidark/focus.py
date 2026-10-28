"""Modo foco: quanto o piloto automático produz em cada canal (Foco · Normal · Reduzido · Pausado).

O dono decide o modo de cada canal; aqui só aplicamos o efeito e SUGERIMOS um modo pelos dados reais
(views nas primeiras 24 h, views engajadas, inscritos/dia e a tendência dos últimos 14 dias). Nada muda sozinho.

Efeitos:
- Foco: +1 Short/dia nos horários automáticos, estoque maior de pautas e passa na frente na fila.
- Normal: como sempre.
- Reduzido: metade dos Shorts (mínimo 1/dia), estoque menor, radar a cada 3 dias e vai para o fim da fila.
- Pausado: sem pautas, roteiros, renders ou agendamentos automáticos. Publicações já agendadas saem
  normalmente (cancele na tela de Publicação se quiser); métricas e comentários continuam sendo coletados.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Any

from sqlmodel import select

from .db import session
from .models import Channel, MetricSnapshot, Publication, Video

MODES: dict[str, dict[str, Any]] = {
    "foco": {"label": "Foco", "priority": 2, "per_day": +1, "ideas_min": 10, "ideas_batch": 10,
             "hint": "Mais Shorts por dia (horários automáticos), mais pautas em estoque e prioridade na fila."},
    "normal": {"label": "Normal", "priority": 0, "per_day": 0, "ideas_min": 6, "ideas_batch": 8,
               "hint": "Produção padrão do piloto automático."},
    "reduzido": {"label": "Reduzido", "priority": -1, "per_day": -1, "ideas_min": 3, "ideas_batch": 4,
                 "hint": "Metade dos Shorts (mín. 1/dia), menos pautas, radar a cada 3 dias e fim da fila."},
    "pausado": {"label": "Pausado", "priority": -2, "per_day": None, "ideas_min": 0, "ideas_batch": 0,
                "hint": "Nada novo é produzido. Agendados ainda saem; métricas e comentários seguem."},
}
# tarefas de produção que seguem a prioridade do canal (publicar/métricas/comentários nunca são afetadas)
PRODUCTION_KINDS = {"autopilot", "discover_ideas", "manual_idea", "verify_idea", "write_script", "review_script",
                    "render_video", "inspect_video", "thumb_variants", "shorts_from_long", "trend_radar"}
WINDOW_DAYS = 14


def mode(ch: Channel | None) -> str:
    m = (getattr(ch, "focus", "") or "normal").lower()
    return m if m in MODES else "normal"


def mode_of(channel_id: int | None) -> str:
    if not channel_id:
        return "normal"
    with session() as s:
        return mode(s.get(Channel, channel_id))


def paused(ch: Channel | int | None) -> bool:
    return (mode_of(ch) if isinstance(ch, int) or ch is None else mode(ch)) == "pausado"


def job_priority(kind: str, channel_id: int | None) -> int:
    """Prioridade inicial de uma tarefa nova na fila (maior passa na frente)."""
    if kind not in PRODUCTION_KINDS or not channel_id:
        return 0
    try:
        return MODES[mode_of(channel_id)]["priority"]
    except Exception:  # noqa: BLE001 — nunca impede a tarefa de entrar na fila
        return 0


def adjust_per_day(ch: Channel, per_day: int) -> int:
    """Shorts/dia nos horários automáticos conforme o modo (as travas de canal novo continuam valendo depois)."""
    m = mode(ch)
    if m == "foco":
        return min(8, per_day + 1)
    if m == "reduzido":
        return max(1, per_day // 2)
    return per_day


def filter_slots(ch: Channel, slots: list[str], auto: bool) -> list[str]:
    """Horários que o piloto usa: pausado = nenhum; reduzido com horários fixos = metade dos Shorts."""
    m = mode(ch)
    if m == "pausado":
        return []
    if m != "reduzido" or auto:  # no modo automático o corte já veio de adjust_per_day
        return slots
    longs = [x for x in slots if "long" in str(x).lower()]
    shorts = sorted(x for x in slots if x not in longs)
    return shorts[::2] + longs  # um sim, um não (sempre sobra pelo menos 1)


def ideas_stock(ch: Channel) -> tuple[int, int]:
    """(mínimo em estoque, quantas buscar quando faltar)."""
    cfg = MODES[mode(ch)]
    return cfg["ideas_min"], cfg["ideas_batch"]


def radar_today(ch: Channel, day: datetime | None = None) -> bool:
    m = mode(ch)
    if m == "pausado":
        return False
    if m == "reduzido":
        return (day or datetime.now()).toordinal() % 3 == 0
    return True


def set_mode(channel_id: int, new: str) -> str:
    """Troca o modo e reposiciona na fila as tarefas de produção ainda esperando (as que não foram movidas à mão)."""
    from .models import Job
    if new not in MODES:
        raise ValueError(f"modo inválido: {new}")
    with session() as s:
        ch = s.get(Channel, channel_id)
        if not ch:
            raise ValueError("canal não encontrado")
        old = mode(ch)
        ch.focus = new
        s.add(ch)
        before, after = MODES[old]["priority"], MODES[new]["priority"]
        for j in s.exec(select(Job).where(Job.channel_id == channel_id, Job.status == "queued")).all():
            if j.kind in PRODUCTION_KINDS and j.priority == before:
                j.priority = after
                s.add(j)
        s.commit()
    try:  # horários automáticos dependem do modo: recalcula no próximo minuto
        from . import posting_times
        posting_times._cache.pop(channel_id, None)
    except Exception:  # noqa: BLE001
        pass
    return new


# ================================================================ sugestão pelos dados

def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def _value_at(snaps: list[MetricSnapshot], t: datetime, field: str = "views") -> float | None:
    """Última leitura até `t` (None se a primeira leitura já é depois)."""
    best = None
    for m in snaps:
        if _utc(m.captured_at) <= t:
            best = getattr(m, field, 0) or 0
    return best


def channel_stats(ch: Channel) -> dict[str, Any]:
    """Números do canal nos últimos 14 dias, só com dados locais (snapshots de métricas)."""
    from .posting_times import _is_short, _views_at
    nowu = datetime.now(timezone.utc)
    since = nowu - timedelta(days=WINDOW_DAYS)
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.channel_id == ch.id, Publication.status == "published")).all()
        fmt = {v.id: v.format for v in s.exec(select(Video).where(Video.channel_id == ch.id)).all()}
        snaps: dict[int, list[MetricSnapshot]] = {}
        for m in s.exec(select(MetricSnapshot).where(MetricSnapshot.channel_id == ch.id).order_by(MetricSnapshot.captured_at)).all():
            snaps.setdefault(m.publication_id, []).append(m)
    # o mesmo vídeo em 2 contas conta uma vez (fica a publicação com mais views)
    def last_views(p: Publication) -> int:
        return (snaps.get(p.id) or [MetricSnapshot(views=0)])[-1].views or 0
    by_key: dict[Any, Publication] = {}
    for p in pubs:
        k = p.video_id or p.external_id or p.id
        if k not in by_key or last_views(p) > last_views(by_key[k]):
            by_key[k] = p
    pubs = list(by_key.values())
    recent = [p for p in pubs if p.published_at and _utc(p.published_at) >= since]
    measured = []  # (publicado em, views 24 h)
    for p in recent:
        if not _is_short(p, fmt):
            continue
        v = _views_at(_utc(p.published_at), snaps.get(p.id, []), 24)
        if v is not None:
            measured.append((_utc(p.published_at), v))
    measured.sort()
    v24 = [v for _, v in measured]
    # tendência: metade mais nova dos vídeos medidos × metade mais antiga
    trend = trend_old = trend_new = None
    if len(v24) >= 4:
        half = len(v24) // 2
        trend_old, trend_new = round(median(v24[:half])), round(median(v24[-half:]))
        trend = round((trend_new + 1) / (trend_old + 1), 2)
    # views ganhas nos últimos 3 dias (pulso do canal agora)
    t3 = nowu - timedelta(days=3)
    gained = 0.0
    for p in pubs:
        sn = snaps.get(p.id) or []
        if not sn:
            continue
        base = 0 if p.published_at and _utc(p.published_at) >= t3 else _value_at(sn, t3)
        if base is None:
            base = sn[0].views  # leituras começaram depois: conta só o que deu para ver
        gained += max(0, (sn[-1].views or 0) - base)
    latest = [snaps[p.id][-1] for p in recent if snaps.get(p.id)]
    views_rec = sum(m.views or 0 for m in latest)
    eng = [m for m in latest if "engaged_views" in (m.raw or {})]
    eng_views, eng_base = sum(m.engaged_views or 0 for m in eng), sum(m.views or 0 for m in eng)
    ypp = (ch.stats or {}).get("ypp") or {}
    engaged_rate = round(100 * eng_views / eng_base, 1) if eng_base else ypp.get("engaged_rate")
    subs_gained = sum(m.subscribers_gained or 0 for m in latest)
    first = min([_utc(p.published_at) for p in recent if p.published_at] or [nowu])
    span = max(1.0, min(WINDOW_DAYS, (nowu - first).total_seconds() / 86400))
    subs_day = round(subs_gained / span, 2) if subs_gained else (ypp.get("rates") or {}).get("subs_per_day")
    return {
        "videos_14d": len(recent), "measured_24h": len(v24),
        "median_views_24h": round(median(v24)) if v24 else None,
        "views_per_video": round(views_rec / len(latest)) if latest else 0,
        "engaged_per_video": round(eng_views / len(eng)) if eng else None,
        "engaged_rate": engaged_rate, "subs_per_day": subs_day,
        "views_3d": round(gained), "trend": trend, "trend_old": trend_old, "trend_new": trend_new,
    }


def _fmt(n: float | None) -> str:
    if n is None:
        return "—"
    return f"{n:,.0f}".replace(",", ".") if abs(n) >= 10 or n == int(n) else f"{n:.1f}".replace(".", ",")


def _decide(st: dict[str, Any], best: float | None) -> tuple[str, str, str]:
    """(modo sugerido, motivo em português claro, confiança baixa|média|alta)."""
    n, med, trend = st["measured_24h"], st["median_views_24h"], st["trend"]
    er, subs, v3 = st["engaged_rate"], st["subs_per_day"], st["views_3d"]
    bits = []
    if med is not None:
        bits.append(f"mediana de {_fmt(med)} views nas primeiras 24 h ({n} Shorts medidos)")
    if st["engaged_per_video"] is not None:
        bits.append(f"{_fmt(st['engaged_per_video'])} views engajadas por vídeo")
    if er is not None:
        bits.append(f"{_fmt(er)}% das views são engajadas")
    if subs:
        bits.append(f"+{_fmt(subs)} inscrito/dia")
    bits.append(f"{_fmt(v3)} views nos últimos 3 dias")
    # tendência só conta com diferença real (de 2 para 6 views é ruído, não "+200%")
    diff = (st["trend_new"] - st["trend_old"]) if trend is not None else 0
    rising, falling = trend is not None and trend >= 1.3 and diff >= 10, trend is not None and trend < 0.7 and diff <= -10
    if trend is not None:
        bits.append(f"vídeos mais novos com mediana de {_fmt(st['trend_new'])} views em 24 h contra {_fmt(st['trend_old'])} dos anteriores"
                    + (" (subindo)" if rising else " (caindo)" if falling else ""))
    data = "; ".join(bits)
    conf = "baixa" if n < 5 else "média" if n < 10 else "alta"
    rel = (med + 1) / (best + 1) if best is not None and med is not None else 1.0
    if n >= 2 and med is not None and rel < 0.15 and v3 < 50:  # pouco dado, mas a distância para o melhor é enorme
        return "reduzido", f"Ainda com poucos dados, mas muito abaixo dos outros canais ({round(rel * 100)}% do melhor): {data}.", "baixa"
    if n < 3 or med is None:
        return "normal", f"Ainda cedo: só {n} Short(s) com 24 h medidas nos últimos {WINDOW_DAYS} dias. Mantenha o ritmo até ter dados ({data}).", "baixa"
    weak_eng = er is not None and er < 10
    if rel >= 0.6 and not falling and v3 > 0:
        why = "o melhor desempenho entre os canais" if rel >= 0.99 else f"{round(rel * 100)}% do melhor canal"
        return "foco", f"Concentre aqui: {why} — {data}.", conf
    if n >= 6 and med < 10 and v3 < 10 and not rising:
        return "pausado", f"Quase sem alcance: {data}. Pausar libera a fila para os canais que respondem; dá para voltar quando quiser.", conf
    if rel < 0.25 or (v3 < 10 and not rising) or (weak_eng and rel < 0.5):
        tail = " Os vídeos novos estão melhorando, então reduzir (em vez de pausar) mantém o teste vivo." if rising else ""
        return "reduzido", f"Retorno bem abaixo dos outros canais ({round(rel * 100)}% do melhor): {data}.{tail}", conf
    if falling:
        return "normal", f"Desempenho razoável mas caindo: {data}. Vale observar antes de dar mais foco.", conf
    return "normal", f"Desempenho intermediário ({round(rel * 100)}% do melhor): {data}.", conf


def suggest_all() -> list[dict[str, Any]]:
    """Modo atual + modo sugerido (com o porquê) de cada canal. Só sugere: quem decide é o dono."""
    with session() as s:
        chans = s.exec(select(Channel).order_by(Channel.id)).all()
    stats = {c.id: channel_stats(c) for c in chans}
    ok = [st["median_views_24h"] for st in stats.values() if st["measured_24h"] >= 3 and st["median_views_24h"] is not None]
    best = max(ok) if ok else None
    out = []
    for c in chans:
        sug, reason, conf = _decide(stats[c.id], best)
        cur = mode(c)
        out.append({"channel_id": c.id, "name": c.name, "mode": cur, "label": MODES[cur]["label"],
                    "suggested": sug, "suggested_label": MODES[sug]["label"], "reason": reason, "confidence": conf,
                    "matches": sug == cur, "stats": stats[c.id]})
    return out


def modes_meta() -> list[dict[str, Any]]:
    return [{"id": k, "label": v["label"], "hint": v["hint"]} for k, v in MODES.items()]
