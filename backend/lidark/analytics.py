"""Métricas, desempenho e aprendizado do canal."""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from sqlmodel import select

from .db import session
from .models import Idea, Insight, MetricSnapshot, Publication, Script, Video

log = logging.getLogger("lidark.analytics")


def latest_metrics(channel_id: int | None = None) -> dict[int, MetricSnapshot]:
    """Última leitura de métricas por publicação."""
    with session() as s:
        q = select(MetricSnapshot).order_by(MetricSnapshot.captured_at)
        if channel_id:
            q = q.where(MetricSnapshot.channel_id == channel_id)
        out: dict[int, MetricSnapshot] = {}
        for m in s.exec(q).all():
            out[m.publication_id] = m
        return out


def performance_table(channel_id: int) -> list[dict[str, Any]]:
    """Uma linha por vídeo publicado (somando plataformas) com nota de desempenho 0-100 relativa ao canal."""
    metrics = latest_metrics(channel_id)
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.channel_id == channel_id,
                                                Publication.status == "published")).all()
        by_video: dict[int, dict[str, Any]] = defaultdict(lambda: {"views": 0, "likes": 0, "comments": 0,
                                                                   "shares": 0, "retention": [], "platforms": []})
        titles: dict = {}
        extra: dict = {}
        for p in pubs:
            m = metrics.get(p.id)
            key = p.video_id if p.video_id else f"ext:{p.external_id or p.id}"
            titles[key] = p.title
            extra[key] = {"url": p.url, "thumbnail": p.thumbnail_url, "published_at": p.published_at.isoformat() if p.published_at else None,
                          "duration": p.duration, "privacy": p.privacy}
            row = by_video[key]
            row["platforms"].append(p.platform)
            if m:
                row["views"] += m.views
                row["likes"] += m.likes
                row["comments"] += m.comments
                row["shares"] += m.shares
                if m.avg_view_percentage:
                    row["retention"].append(m.avg_view_percentage)
                row["watch"] = row.get("watch", 0.0) + (m.watch_time_minutes or 0)
                row["avd"] = max(row.get("avd", 0.0), m.avg_view_duration or 0)
                if "engaged_views" in (m.raw or {}):  # só leituras do Analytics trazem views engajadas
                    row["engaged"] = row.get("engaged", 0) + (m.engaged_views or 0)
        rows = []
        for vid, r in by_video.items():
            v = s.get(Video, vid) if isinstance(vid, int) else None
            sc = s.get(Script, v.script_id) if v else None
            idea = s.get(Idea, sc.idea_id) if sc and sc.idea_id else None
            rows.append({
                "video_id": vid, "title": sc.title if sc else titles.get(vid, str(vid)),
                "views": r["views"], "likes": r["likes"], "comments": r["comments"], "shares": r["shares"],
                "retention": sum(r["retention"]) / len(r["retention"]) if r["retention"] else 0.0,
                "predicted": idea.score if idea else None, "platforms": r["platforms"],
                "watch_minutes": r.get("watch", 0.0), "avg_duration": r.get("avd", 0.0), **extra.get(vid, {}),
                # views engajadas = as que contam p/ monetizar Shorts (ausente se ainda não houve leitura do Analytics)
                **({"engaged_views": r["engaged"],
                    "engaged_rate": round(100 * r["engaged"] / r["views"], 1) if r["views"] else None} if "engaged" in r else {}),
            })
    _rank(rows)
    return rows


def _rank(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    n = len(rows)

    def pct(key):
        order = sorted(range(n), key=lambda i: rows[i][key])
        res = [0.0] * n
        for rank, i in enumerate(order):
            res[i] = 100 * rank / max(1, n - 1)
        return res

    pv, pl, pr = pct("views"), pct("likes"), pct("retention")
    for i, r in enumerate(rows):
        eng = (r["likes"] + 2 * r["comments"] + 3 * r["shares"]) / max(1, r["views"])
        r["engagement"] = round(eng * 100, 2)
        r["perf"] = round(0.5 * pv[i] + 0.25 * pl[i] + 0.25 * pr[i]) if n > 1 else 50


def calibrate_score(channel_id: int, raw: int) -> int:
    """Ajusta a nota da IA usando regressão (nota prevista × desempenho real) dos vídeos já publicados."""
    pts = [(r["predicted"], r["perf"]) for r in performance_table(channel_id) if r["predicted"] is not None]
    if len(pts) < 5:
        return raw
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    var = sum((x - mx) ** 2 for x in xs)
    if var == 0:
        return raw
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var
    b = my - a * mx
    weight = min(0.5, len(pts) / 40)  # quanto mais histórico, mais confia na calibração
    return int(max(0, min(100, round((1 - weight) * raw + weight * (a * raw + b)))))


def generate_insights(channel_id: int, min_hours: float = 0) -> list[str]:
    """Pede para a IA encontrar padrões nos vídeos do canal e salva como aprendizados."""
    from datetime import timedelta
    from . import llm
    from .models import now
    if min_hours:
        with session() as s:
            last = s.exec(select(Insight).where(Insight.channel_id == channel_id).order_by(Insight.created_at.desc())).first()
        if last and last.created_at and last.created_at.replace(tzinfo=now().tzinfo) > now() - timedelta(hours=min_hours):
            return []
    rows = performance_table(channel_id)
    if len(rows) < 3:
        return []
    table = "\n".join(f"- \"{r['title']}\" | views {r['views']} | curtidas {r['likes']} | coment {r['comments']} | "
                      f"retenção {r['retention']:.0f}%" + (f" | nota prevista {r['predicted']}" if r['predicted'] is not None else "") + f" | desempenho {r['perf']}"
                      for r in sorted(rows, key=lambda r: -r["perf"]))
    data = llm.complete_json(f"""Você é analista de dados de um canal de vídeos curtos. Analise a tabela e extraia
de 4 a 8 aprendizados ACIONÁVEIS (temas, tipos de gancho, formatos de título, duração) que expliquem o desempenho.
Se houver "nota prevista", diga onde ela errou mais; se não houver, não comente sobre isso.
{table}
Responda JSON: {{"insights": ["..."]}}""", temperature=0.3)
    items = data.get("insights", []) if isinstance(data, dict) else []
    with session() as s:
        if items:  # substitui os aprendizados anteriores (não acumula repetidos)
            for old in s.exec(select(Insight).where(Insight.channel_id == channel_id, Insight.kind == "pattern")).all():
                s.delete(old)
        for t in items:
            s.add(Insight(channel_id=channel_id, kind="pattern", text=t))
        s.commit()
    return items


def daily_analytics(channel_id: int, days: int = 28) -> dict[str, Any]:
    """Série diária do canal direto do YouTube Analytics (views, minutos assistidos, inscritos)."""
    from datetime import date, timedelta
    from .models import Account
    from .publish import _yt_client, _yt_creds
    with session() as s:
        acc = s.exec(select(Account).where(Account.channel_id == channel_id, Account.platform == "youtube")).first()
    if not acc or not acc.credentials:
        return {"rows": [], "connected": False}
    ya = _yt_client(_yt_creds(acc), "youtubeAnalytics", "v2")
    end = date.today()
    start = end - timedelta(days=days)
    r = ya.reports().query(ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
                           metrics="views,estimatedMinutesWatched,subscribersGained,likes,shares",
                           dimensions="day", sort="day").execute()
    rows = [{"day": d, "views": v, "minutes": m, "subs": sg, "likes": lk, "shares": sh} for d, v, m, sg, lk, sh in r.get("rows", []) or []]
    return {"rows": rows, "connected": True}


# ================================================================ todos os canais

def _channels() -> list:
    from .models import Channel
    with session() as s:
        return s.exec(select(Channel).order_by(Channel.id)).all()


def performance_all() -> list[dict[str, Any]]:
    """Tabela de desempenho de todos os canais juntos (a nota de desempenho continua relativa a cada canal)."""
    out: list[dict[str, Any]] = []
    for ch in _channels():
        for r in performance_table(ch.id):
            out.append({**r, "channel_id": ch.id, "channel_name": ch.name})
    return out


def _channel_summary(ch, days: int) -> dict[str, Any]:
    """Resumo de um canal para a visão geral: período (YouTube Analytics) + vídeos (última leitura de métricas)."""
    from datetime import timedelta
    from .models import now
    rows = performance_table(ch.id)
    seen = [r for r in rows if r["views"]]
    views_all = sum(r["views"] for r in rows)
    inter = sum(r["likes"] + r["comments"] + r["shares"] for r in rows)
    ret = [r["retention"] for r in rows if r["retention"] > 0]
    since = now() - timedelta(days=days)
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.channel_id == ch.id, Publication.status == "published")).all()
    recent = [p for p in pubs if p.published_at and p.published_at.replace(tzinfo=since.tzinfo) >= since]
    out: dict[str, Any] = {
        "id": ch.id, "name": ch.name, "avatar_url": ch.avatar_url, "color": (ch.theme or {}).get("gold") or ch.color,
        "subscribers": (ch.stats or {}).get("subscribers", 0), "total_views": (ch.stats or {}).get("views", 0),
        "videos": len(rows), "published_period": len(recent),
        "views_per_video": round(views_all / len(seen)) if seen else 0,
        "avg_retention": round(sum(ret) / len(ret), 1) if ret else 0.0,
        "engagement_rate": round(100 * inter / views_all, 2) if views_all else 0.0,
        "likes_total": sum(r["likes"] for r in rows), "comments_total": sum(r["comments"] for r in rows),
        "connected": False, "error": "", "daily": [],
    }
    if any("engaged_views" in r for r in rows):
        out["engaged_views_total"] = sum(r.get("engaged_views") or 0 for r in rows)
    try:
        d = daily_analytics(ch.id, days)
        out["connected"], out["daily"] = d.get("connected", False), d.get("rows", [])
    except Exception as e:  # noqa: BLE001 — um canal com erro não derruba os outros
        log.warning("analytics de %s: %s", ch.name, e)
        out["connected"], out["error"] = True, str(e)[:300]
    period = {k: sum(r.get(k) or 0 for r in out["daily"]) for k in ("views", "minutes", "subs", "likes", "shares")}
    if any("engaged_views" in r for r in out["daily"]):
        period["engaged_views"] = sum(r.get("engaged_views") or 0 for r in out["daily"])
    out["period"] = period
    return out


def overview(days: int = 28, channel_id: int | None = None) -> dict[str, Any]:
    """Visão de todos os canais (ou de um): totais do período, comparação por canal e views diárias por canal."""
    from concurrent.futures import ThreadPoolExecutor
    chans = [c for c in _channels() if not channel_id or c.id == channel_id]
    with ThreadPoolExecutor(max_workers=4) as ex:  # o YouTube Analytics é consultado canal a canal
        summaries = list(ex.map(lambda c: _channel_summary(c, days), chans))
    by_day: dict[str, dict[str, Any]] = {}
    for sm in summaries:
        for r in sm.pop("daily"):
            d = by_day.setdefault(r["day"], {"day": r["day"], "views": 0, "minutes": 0, "subs": 0, "likes": 0, "shares": 0})
            for k in ("views", "minutes", "subs", "likes", "shares", "engaged_views"):
                if k in r:
                    d[k] = d.get(k, 0) + (r[k] or 0)
            d[f"c{sm['id']}"] = d.get(f"c{sm['id']}", 0) + (r.get("views") or 0)
    keys = {k for sm in summaries for k in sm["period"]}
    totals = {k: sum(sm["period"].get(k, 0) for sm in summaries) for k in keys}
    totals.update({
        "subscribers": sum(sm["subscribers"] or 0 for sm in summaries),
        "total_views": sum(sm["total_views"] or 0 for sm in summaries),
        "published_period": sum(sm["published_period"] for sm in summaries),
        "comments_total": sum(sm["comments_total"] for sm in summaries),
    })
    return {"days": days, "channels": summaries, "daily": [by_day[k] for k in sorted(by_day)], "totals": totals,
            "errors": [{"channel_id": sm["id"], "name": sm["name"], "error": sm["error"]} for sm in summaries if sm["error"]]}
