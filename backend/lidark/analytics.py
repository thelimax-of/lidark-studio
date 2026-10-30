"""Métricas, desempenho e aprendizado do canal."""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from sqlmodel import select

from . import cache
from .db import session
from .models import Idea, Insight, MetricSnapshot, Publication, Script, Video

log = logging.getLogger("lidark.analytics")

YT_TTL = 900  # segundos que uma resposta do YouTube Analytics vale como fresca


def register_hooks() -> None:
    """Coleta de métricas terminou: as séries do Analytics ficam velhas (atualizam no próximo acesso, sem esperar)."""
    cache.on_job_done("collect_metrics", lambda _d: cache.invalidate("yt:"))
    for kind in ("collect_metrics", "publish", "import_youtube", "setup_channel"):  # mudam números/canais da visão geral
        cache.on_job_done(kind, lambda _d: cache.drop("ov:"))  # recalcula na hora (é rápido: o Analytics continua em cache)


def latest_metrics(channel_id: int | None = None) -> dict[int, MetricSnapshot]:
    """Última leitura de métricas por publicação (só a última de cada uma sai do banco)."""
    from sqlalchemy import text
    where = "WHERE channel_id = :cid" if channel_id else ""
    ids_sql = text(f"""SELECT id FROM (SELECT id, ROW_NUMBER() OVER (PARTITION BY publication_id
                       ORDER BY captured_at DESC, id DESC) AS rn FROM metricsnapshot {where}) WHERE rn = 1""")
    with session() as s:
        ids = [r[0] for r in s.connection().execute(ids_sql, {"cid": channel_id} if channel_id else {})]
        if not ids:
            return {}
        return {m.publication_id: m for m in s.exec(select(MetricSnapshot).where(MetricSnapshot.id.in_(ids))).all()}


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
        # vídeo → roteiro → pauta numa consulta por tabela (antes eram 3 por linha)
        vids = [k for k in by_video if isinstance(k, int)]
        videos = {v.id: v for v in s.exec(select(Video).where(Video.id.in_(vids))).all()} if vids else {}
        sids = {v.script_id for v in videos.values() if v.script_id}
        scripts = {x.id: x for x in s.exec(select(Script).where(Script.id.in_(sids))).all()} if sids else {}
        iids = {x.idea_id for x in scripts.values() if x.idea_id}
        ideas = {x.id: x for x in s.exec(select(Idea).where(Idea.id.in_(iids))).all()} if iids else {}
        rows = []
        for vid, r in by_video.items():
            v = videos.get(vid) if isinstance(vid, int) else None
            sc = scripts.get(v.script_id) if v else None
            idea = ideas.get(sc.idea_id) if sc and sc.idea_id else None
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
    end = date.today()
    start = end - timedelta(days=days)

    def fetch() -> list[dict[str, Any]]:
        ya = _yt_client(_yt_creds(acc), "youtubeAnalytics", "v2")
        r = ya.reports().query(ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
                               metrics="views,estimatedMinutesWatched,subscribersGained,likes,shares",
                               dimensions="day", sort="day").execute()
        cache.drop("ov:")  # série nova do Analytics: a visão geral recalcula com ela
        return [{"day": d, "views": v, "minutes": m, "subs": sg, "likes": lk, "shares": sh}
                for d, v, m, sg, lk, sh in r.get("rows", []) or []]
    # a consulta ao Analytics fica em cache (15 min; velho é servido enquanto atualiza em segundo plano)
    rows = [dict(x) for x in cache.get(f"yt:daily:{channel_id}:{days}:{end.isoformat()}", fetch, ttl=YT_TTL)]
    # o Analytics só libera os dados com ~2-3 dias de atraso: os dias que faltam saem das nossas leituras por vídeo
    last = date.fromisoformat(rows[-1]["day"]) if rows else start - timedelta(days=1)
    rows += recent_estimate(channel_id, last + timedelta(days=1), end)
    return {"rows": rows, "connected": True}


def recent_estimate(channel_id: int, first, last) -> list[dict[str, Any]]:
    """Views/curtidas por dia (fuso local) de first a last, a partir das leituras de métricas de cada vídeo.
    O acumulado de cada vídeo é interpolado entre as leituras (de 0 na publicação até a 1ª leitura) e a diferença
    na virada de cada dia vira o valor do dia. Minutos/inscritos/compartilhamentos só o Analytics tem: ficam vazios."""
    from datetime import datetime, time, timedelta
    if first > last:
        return []
    tz = datetime.now().astimezone().tzinfo
    utc = lambda dt: dt if dt.tzinfo else dt.replace(tzinfo=__import__("datetime").timezone.utc)  # noqa: E731
    with session() as s:
        pubs = {p.id: p for p in s.exec(select(Publication).where(Publication.channel_id == channel_id,
                                                                  Publication.platform == "youtube")).all()}
        # só as colunas usadas (sem o JSON "raw" de cada leitura)
        snaps = s.exec(select(MetricSnapshot.publication_id, MetricSnapshot.captured_at, MetricSnapshot.views, MetricSnapshot.likes)
                       .where(MetricSnapshot.channel_id == channel_id, MetricSnapshot.platform == "youtube")
                       .order_by(MetricSnapshot.captured_at)).all()
    series: dict[int, list[tuple[datetime, int, int]]] = defaultdict(list)
    for pid, at, views, likes in snaps:
        if pid in pubs:
            series[pid].append((utc(at), views or 0, likes or 0))
    if not series:
        return []

    def cum(pts: list, born, t) -> tuple[float, float]:
        if t >= pts[-1][0]:
            return float(pts[-1][1]), float(pts[-1][2])  # depois da última leitura: ainda não sabemos
        prev = (born, 0, 0) if born and born < pts[0][0] else None
        for p in pts:
            if t < p[0]:
                if prev is None or t <= prev[0]:
                    return (0.0, 0.0) if prev else (float(p[1]), float(p[2]))
                f = (t - prev[0]) / (p[0] - prev[0])
                return prev[1] + f * (p[1] - prev[1]), prev[2] + f * (p[2] - prev[2])
            prev = p
        return float(pts[-1][1]), float(pts[-1][2])

    out = []
    d = first
    while d <= last:
        a = datetime.combine(d, time.min, tz)
        b = a + timedelta(days=1)
        v = lk = 0.0
        for pid, pts in series.items():
            born = utc(pubs[pid].published_at) if pubs[pid].published_at else None
            # sem leitura antes do dia e publicado antes dele: o ponto de partida é desconhecido
            if pts[0][0] > a and (born is None or born < a - timedelta(days=1)):
                continue
            (v0, l0), (v1, l1) = cum(pts, born, a), cum(pts, born, b)
            v, lk = v + max(0.0, v1 - v0), lk + max(0.0, l1 - l0)
        out.append({"day": d.isoformat(), "views": round(v), "likes": round(lk), "estimated": True})
        d += timedelta(days=1)
    return out


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


OVERVIEW_TTL = 120  # a visão geral só muda com coleta de métricas/publicação (que invalidam) — o TTL é só rede de segurança


def overview(days: int = 28, channel_id: int | None = None, refresh: bool = False) -> dict[str, Any]:
    """Visão de todos os canais (ou de um) — em cache; `refresh` refaz tudo (inclusive a consulta ao Analytics)."""
    if refresh:
        cache.drop("yt:")
        cache.drop("ov:")
    return cache.get(f"ov:{days}:{channel_id or 0}", lambda: _overview(days, channel_id), ttl=OVERVIEW_TTL, stale=3600)


def _overview(days: int = 28, channel_id: int | None = None) -> dict[str, Any]:
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
            if r.get("estimated"):
                d["estimated"] = True
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
