"""Radar de tendências: descobre o que está em alta no nicho e vira pautas com nota.

Ao vivo (API do YouTube com a conta conectada do canal, poucas unidades de cota):
- Mais vistos do Brasil na categoria do canal e busca do nicho nas últimas 72 h, por views/hora ("subindo agora")

Fontes (gratuitas, sem gastar cota da API do YouTube):
- Sugestões de busca do YouTube para as palavras-chave do canal (o que as pessoas estão digitando)
- Vídeos do nicho com muitas visualizações (busca do YouTube via yt-dlp)
- Vídeos "virais" de concorrentes (muito acima da média do próprio concorrente)
- Google Trends Brasil (assuntos do dia — a IA só usa o que tiver ligação com o nicho)
"""
from __future__ import annotations

import json
import logging
import re
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

import feedparser
import httpx

from . import content, llm
from .db import session
from .jobs import JobContext, enqueue, handler
from .models import Channel, Idea

log = logging.getLogger("lidark.radar")
UA = {"User-Agent": "Mozilla/5.0"}


def _ydl(limit: int | None = None):
    import yt_dlp
    class _Quiet:
        def debug(self, msg): pass
        def info(self, msg): pass
        def warning(self, msg): pass
        def error(self, msg): log.debug(msg)

    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": "in_playlist", "ignoreerrors": True,
            "socket_timeout": 20, "logger": _Quiet()}
    if limit:
        opts["playlistend"] = limit  # só os mais recentes (canais grandes têm milhares de vídeos)
    try:
        return yt_dlp.YoutubeDL({**opts, "js_runtimes": {"node": {}}})
    except Exception:  # noqa: BLE001
        return yt_dlp.YoutubeDL(opts)


def ensure_keywords(ch: Channel) -> list[str]:
    radar = dict(ch.radar or {})
    if radar.get("keywords"):
        return radar["keywords"]
    data = llm.complete_json(f"""Canal do YouTube sobre: {ch.niche}. Público: {ch.audience}.
Liste 8 palavras-chave de BUSCA em português (2-3 palavras cada) que o público desse nicho digita no YouTube.
Responda JSON: {{"keywords": ["..."]}}""", temperature=0.4)
    kws = [k for k in (data.get("keywords") or []) if isinstance(k, str)][:8]
    with session() as s:
        db = s.get(Channel, ch.id)
        db.radar = {**(db.radar or {}), "keywords": kws}
        s.add(db)
        s.commit()
    return kws


def youtube_suggestions(q: str) -> list[str]:
    try:
        r = httpx.get("https://suggestqueries.google.com/complete/search", timeout=15, headers=UA,
                      params={"client": "firefox", "ds": "yt", "hl": "pt-BR", "gl": "BR", "q": q})
        return [x for x in r.json()[1] if x.lower() != q.lower()][:8]
    except Exception:  # noqa: BLE001
        return []


def youtube_search(q: str, n: int = 15) -> list[dict[str, Any]]:
    with _ydl() as y:
        info = y.extract_info(f"ytsearch{n}:{q}", download=False) or {}
    out = []
    for e in info.get("entries") or []:
        if not e:
            continue
        out.append({"title": e.get("title", ""), "views": int(e.get("view_count") or 0),
                    "channel": e.get("channel") or e.get("uploader") or "", "channel_url": e.get("channel_url") or "",
                    "duration": e.get("duration") or 0, "url": e.get("url") or ""})
    return out


def competitor_outliers(url: str, limit: int = 25) -> list[dict[str, Any]]:
    """Vídeos de um concorrente com views muito acima da mediana dele (o que viralizou)."""
    base = url if url.startswith("http") else f"https://www.youtube.com/{url if url.startswith('@') else '@' + url}"
    items = []
    with _ydl(limit) as y:
        for tab in ("shorts", "videos"):
            info = y.extract_info(f"{base.rstrip('/')}/{tab}", download=False) or {}
            for e in (info.get("entries") or [])[:limit]:
                if e and e.get("view_count"):
                    items.append({"title": e.get("title", ""), "views": int(e["view_count"]), "tab": tab})
    if len(items) < 5:
        return []
    med = statistics.median(x["views"] for x in items) or 1
    out = [dict(x, ratio=round(x["views"] / med, 1)) for x in items if x["views"] >= 3 * med]
    return sorted(out, key=lambda x: -x["ratio"])[:6]


def google_trends_br() -> list[str]:
    return [t["title"] for t in google_trends_detail()]


def google_trends_detail() -> list[dict[str, Any]]:
    """Assuntos do dia no Google Trends Brasil, com a busca aproximada e a manchete que puxou."""
    try:
        f = feedparser.parse(httpx.get("https://trends.google.com/trending/rss?geo=BR", timeout=20, headers=UA).text)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for e in f.entries[:25]:
        traffic = str(e.get("ht_approx_traffic") or "")
        try:
            n = int(re.sub(r"\D", "", traffic) or 0)
        except ValueError:
            n = 0
        out.append({"title": e.get("title", ""), "traffic": traffic, "traffic_n": n,
                    "news": e.get("ht_news_item_title", ""), "news_url": e.get("ht_news_item_url", ""),
                    "picture": e.get("ht_picture", "")})
    return out


# ---------------------------------------------------------------- "subindo agora" (API do YouTube, contas conectadas)

SEARCH_COST = 100  # search.list gasta 100 unidades; videos.list, 1


def _hours_since(iso: str) -> float:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return 9999.0
    return max(1.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600)


def _yt_for(channel_id: int):
    from .community import _account
    from .publish import _yt_client, _yt_creds
    acc = _account(channel_id)
    if not acc or not acc.credentials:
        return None
    return _yt_client(_yt_creds(acc))


def _video_rows(yt, ids: list[str], source: str) -> list[dict[str, Any]]:
    if not ids:
        return []
    items = yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids[:50])).execute().get("items") or []
    out = []
    for it in items:
        sn, st = it.get("snippet") or {}, it.get("statistics") or {}
        views = int(st.get("viewCount") or 0)
        age = _hours_since(sn.get("publishedAt") or "")
        dur = _iso_dur(((it.get("contentDetails") or {}).get("duration")) or "")
        out.append({"id": it["id"], "title": sn.get("title", ""), "channel": sn.get("channelTitle", ""),
                    "views": views, "likes": int(st.get("likeCount") or 0), "comments": int(st.get("commentCount") or 0),
                    "age_hours": round(age, 1), "vph": round(views / age), "duration": dur, "short": 0 < dur <= 180,
                    "thumbnail": ((sn.get("thumbnails") or {}).get("medium") or {}).get("url", ""),
                    "url": f"https://youtube.com/{'shorts/' if 0 < dur <= 180 else 'watch?v='}{it['id']}", "source": source})
    return out


def _iso_dur(s: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def youtube_rising(ch: Channel, kws: list[str], hours: int = 72) -> list[dict[str, Any]]:
    """O que está subindo AGORA: mais vistos do Brasil na categoria do canal + busca do nicho nas últimas 72 h,
    ordenados por views/hora. Só gasta a busca (100 unidades) se a cota do dia tiver folga."""
    try:
        yt = _yt_for(ch.id)
    except Exception as e:  # noqa: BLE001
        log.info("radar: sem API do YouTube (%s)", e)
        return []
    if yt is None:
        return []
    rows: list[dict[str, Any]] = []
    try:
        pop = yt.videos().list(part="id", chart="mostPopular", regionCode="BR", videoCategoryId=ch.yt_category or "27",
                               maxResults=25).execute().get("items") or []
        rows += _video_rows(yt, [i["id"] for i in pop], "em alta na categoria (BR)")
    except Exception as e:  # noqa: BLE001
        log.info("radar mostPopular: %s", e)
    try:
        from . import config
        from .community import YT_DAILY_QUOTA, YT_RESERVE, yt_units_today
        quota = int(config.get("yt_daily_quota") or YT_DAILY_QUOTA)
        if kws and yt_units_today() + SEARCH_COST + 200 < quota - YT_RESERVE:
            after = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
            res = yt.search().list(part="id", q="|".join(kws[:5]), type="video", order="viewCount", regionCode="BR",
                                   relevanceLanguage="pt", publishedAfter=after, maxResults=25).execute().get("items") or []
            ids = [r["id"]["videoId"] for r in res if (r.get("id") or {}).get("videoId")]
            rows += _video_rows(yt, ids, "busca do nicho (72 h)")
    except Exception as e:  # noqa: BLE001
        log.info("radar search: %s", e)
    kw_tokens = {w for k in kws for w in re.findall(r"[\wÀ-ú]{4,}", k.lower())}
    seen, out = set(), []
    for r in sorted(rows, key=lambda x: -x["vph"]):
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        hits = sum(1 for w in kw_tokens if w in r["title"].lower())
        r["niche"] = r["source"].startswith("busca") or hits > 0
        out.append(r)
    return out[:40]


def rank_signals(sig: dict[str, Any]) -> list[dict[str, Any]]:
    """Uma lista única do que está em alta para o canal, com nota 0-100 (ritmo, ligação com o nicho, fonte)."""
    import math
    items: list[dict[str, Any]] = []
    for r in sig.get("rising") or []:
        heat = min(100, round(18 * math.log10(max(10, r["vph"]))))  # 100 v/h → 36 · 10 mil v/h → 72 · 300 mil → ~100
        items.append({"kind": "rising", "title": r["title"], "detail": f"{r['vph']:,} views/h · {r['channel']}".replace(",", "."),
                      "url": r["url"], "thumbnail": r.get("thumbnail", ""), "views": r["views"], "vph": r["vph"],
                      "short": r.get("short"), "niche": bool(r.get("niche")),
                      "score": min(100, heat + 20) if r.get("niche") else round(heat * 0.5), "source": r["source"]})
    for c, xs in (sig.get("viral") or {}).items():
        for x in xs:
            items.append({"kind": "competitor", "title": x["title"], "detail": f"{x['ratio']}× a média de {c.split('/')[-1]}",
                          "url": "", "views": x["views"], "score": min(100, round(40 + 8 * x["ratio"])), "source": "concorrente"})
    for k, v in (sig.get("suggestions") or {}).items():
        for i, q in enumerate(v[:4]):
            items.append({"kind": "search", "title": q, "detail": f"buscado no YouTube (de “{k}”)", "url": "",
                          "score": 55 - 4 * i, "source": "autocompletar"})
    for t in sig.get("trends_detail") or []:
        items.append({"kind": "google", "title": t["title"], "detail": f"{t['traffic']} buscas · {t['news'][:80]}".strip(" ·"),
                      "url": t.get("news_url", ""), "score": min(60, 20 + round(6 * math.log10(max(10, t["traffic_n"])))),
                      "source": "Google Trends BR"})
    items.sort(key=lambda x: -x["score"])
    return items[:60]


# ---------------------------------------------------------------- foto do radar (painel "Tendências")

def _snap_path(channel_id: int):
    from .config import DATA_DIR
    folder = DATA_DIR / "radar"
    folder.mkdir(exist_ok=True)
    return folder / f"{channel_id}.json"


def save_snapshot(channel_id: int, data: dict[str, Any]) -> None:
    _snap_path(channel_id).write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")


def snapshot(channel_id: int) -> dict[str, Any]:
    try:
        return json.loads(_snap_path(channel_id).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def gather_signals(ch: Channel, ctx: JobContext | None = None) -> dict[str, Any]:
    kws = ensure_keywords(ch)[:6]
    if ctx:
        ctx.update(0.1, f"Radar: pesquisando {len(kws)} palavras-chave")
    with ThreadPoolExecutor(4) as ex:
        sugg = dict(zip(kws, ex.map(youtube_suggestions, kws)))
        searches = dict(zip(kws, ex.map(lambda k: youtube_search(k, 15), kws)))
    hits = sorted({(v["title"], v["views"], v["channel"], v["channel_url"]) for vs in searches.values() for v in vs},
                  key=lambda x: -x[1])
    # concorrentes: os que mais aparecem com muitas views (se o usuário não definiu)
    comps = list((ch.radar or {}).get("competitors") or [])
    if not comps:
        score: dict[str, int] = {}
        for _, views, _, curl in hits:
            if curl and views >= 50_000:
                score[curl] = score.get(curl, 0) + 1
        comps = [c for c, _ in sorted(score.items(), key=lambda x: -x[1])[:5]]
        names = {curl: name for _, _, name, curl in hits if curl in comps}
        with session() as s:
            db = s.get(Channel, ch.id)
            db.radar = {**(db.radar or {}), "competitors": comps,
                        "competitor_names": {**(db.radar or {}).get("competitor_names", {}), **names}}
            s.add(db)
            s.commit()
    if ctx:
        ctx.update(0.4, f"Radar: analisando {len(comps)} concorrentes")
    with ThreadPoolExecutor(3) as ex:
        viral = dict(zip(comps, ex.map(lambda c: competitor_outliers(c), comps[:6])))
    trends_detail = google_trends_detail()
    if ctx:
        ctx.update(0.5, "Radar: o que está subindo agora no YouTube")
    rising = youtube_rising(ch, kws)
    return {"keywords": kws, "suggestions": sugg, "top_videos": hits[:25], "viral": viral,
            "trends": [t["title"] for t in trends_detail], "trends_detail": trends_detail, "rising": rising}


def signals_to_ideas(ch: Channel, sig: dict[str, Any], count: int = 6) -> list[dict[str, Any]]:
    used = content.existing_titles(ch.id)
    sug = "\n".join(f"- {k}: {', '.join(v)}" for k, v in sig["suggestions"].items() if v)
    top = "\n".join(f"- “{t}” — {v:,} views ({c})".replace(",", ".") for t, v, c, _ in sig["top_videos"][:20])
    vir = "\n".join(f"- “{x['title']}” — {x['views']:,} views ({x['ratio']}x a média do canal {c.split('/')[-1]})".replace(",", ".")
                    for c, xs in sig["viral"].items() for x in xs)
    rising = "\n".join(f"- “{r['title']}” — {r['vph']:,} views/hora, {r['views']:,} views em {r['age_hours']:.0f} h ({r['channel']}; {r['source']})".replace(",", ".")
                       for r in (sig.get("rising") or [])[:20] if r.get("niche") or r["vph"] > 20000)
    prompt = f"""{content.channel_brief(ch)}

SUBINDO AGORA NO YOUTUBE BRASIL (views por hora desde a publicação):
{rising or '(nada)'}

SINAIS DO QUE ESTÁ EM ALTA AGORA NO NICHO:
O QUE AS PESSOAS ESTÃO BUSCANDO NO YOUTUBE (autocompletar):
{sug or '(nada)'}

VÍDEOS DO NICHO COM MAIS VISUALIZAÇÕES:
{top or '(nada)'}

VÍDEOS QUE VIRALIZARAM EM CANAIS CONCORRENTES (muito acima da média deles):
{vir or '(nada)'}

ASSUNTOS EM ALTA NO BRASIL HOJE (Google Trends — use SÓ se tiver ligação real com o nicho):
{', '.join(sig['trends']) or '(nada)'}

PAUTAS JÁ USADAS (não repita):
{chr(10).join('- ' + t for t in used[:120]) or '(nenhuma)'}

Com base nesses sinais, proponha {count} pautas que aproveitam o interesse do momento, com um ÂNGULO PRÓPRIO
(não copie títulos de outros canais). Fatos reais e verificáveis.
Responda JSON: {{"ideas": [{{"title": "...", "angle": "...", "summary": "...", "trend_evidence": "qual sinal motivou (cite números)", "urgency": "alta|media"}}]}}"""
    data = llm.complete_json(prompt, temperature=0.8)
    return (data.get("ideas") or []) if isinstance(data, dict) else []


@handler("trend_radar")
def job_trend_radar(ctx: JobContext) -> dict:
    from .pipeline import _score
    with session() as s:
        ch = s.get(Channel, ctx.channel_id)
    sig = gather_signals(ch, ctx)
    ctx.log(f"Sinais: {sum(len(v) for v in sig['suggestions'].values())} buscas, {len(sig['top_videos'])} vídeos, "
            f"{sum(len(v) for v in sig['viral'].values())} virais de concorrentes, {len(sig['trends'])} tendências, "
            f"{len(sig.get('rising') or [])} subindo agora")
    snap = {"at": datetime.now(timezone.utc).isoformat(), "keywords": sig["keywords"], "ranked": rank_signals(sig),
            "rising": sig.get("rising") or [], "trends": sig.get("trends_detail") or [], "suggestions": sig["suggestions"],
            "viral": sig["viral"], "ideas": snapshot(ch.id).get("ideas", [])[-30:]}
    save_snapshot(ch.id, snap)
    if ctx.payload.get("ideas") is False:  # só atualizar o painel "Tendências"
        return {"ranked": len(snap["ranked"])}
    ctx.update(0.6, "Radar: transformando tendências em pautas")
    with session() as s:
        ch = s.get(Channel, ctx.channel_id)
    ideas = signals_to_ideas(ch, sig, ctx.payload.get("count", 6))
    created = []
    with session() as s:
        for it in ideas:
            idea = Idea(channel_id=ch.id, title=str(it.get("title", ""))[:200], angle=it.get("angle", ""),
                        summary=it.get("summary", ""), format="short", origin="trend",
                        tags=[f"🔥 {it.get('trend_evidence', '')}"[:300], f"urgência: {it.get('urgency', 'media')}"])
            s.add(idea)
            s.commit()
            s.refresh(idea)
            created.append(idea.id)
    snap["ideas"] = (snap["ideas"] + created)[-30:]
    save_snapshot(ch.id, snap)
    for i, iid in enumerate(created):
        ctx.update(0.65 + 0.3 * i / max(1, len(created)), f"Avaliando pauta de tendência {i + 1}/{len(created)}")
        _score(ch, iid, ctx)
        enqueue("verify_idea", title="Checar fatos da pauta", channel_id=ch.id, ref_id=iid)
    ctx.log(f"{len(created)} pautas de tendência criadas")
    hot = [it for it in ideas if str(it.get("urgency", "")).startswith("alta")]
    if created:
        try:
            from . import notify
            notify.record("trend", f"🔥 {len(created)} pauta(s) de tendência · {ch.name}",
                          "\n".join(f"• {str(it.get('title', ''))[:80]}" for it in (hot or ideas)[:4]),
                          link="/tendencias", channel_id=ch.id, key=f"radar:{ctx.job_id}")
        except Exception:  # noqa: BLE001
            pass
    return {"ideas": created}


def trend_ideas(channel_id: int, limit: int = 30) -> list[dict[str, Any]]:
    """Pautas nascidas do radar (mais novas primeiro), com status de produção — para gerar com um clique."""
    from sqlmodel import select
    with session() as s:
        rows = s.exec(select(Idea).where(Idea.channel_id == channel_id, Idea.origin == "trend")
                      .order_by(Idea.id.desc()).limit(limit)).all()
    out = []
    for i in rows:
        tags = i.tags or []
        out.append({"id": i.id, "title": i.title, "angle": i.angle, "summary": i.summary, "format": i.format,
                    "status": i.status, "score": i.score, "fact_status": i.fact_status,
                    "evidence": next((t[2:] for t in tags if str(t).startswith("🔥")), ""),
                    "urgency": next((t.split(":", 1)[1].strip() for t in tags if str(t).startswith("urgência:")), ""),
                    "created_at": i.created_at.isoformat() if i.created_at else None})
    return out
