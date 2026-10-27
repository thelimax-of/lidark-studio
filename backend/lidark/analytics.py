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
