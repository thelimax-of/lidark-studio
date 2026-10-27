"""Radar de tendências: descobre o que está em alta no nicho e vira pautas com nota.

Fontes (gratuitas, sem gastar cota da API do YouTube):
- Sugestões de busca do YouTube para as palavras-chave do canal (o que as pessoas estão digitando)
- Vídeos do nicho com muitas visualizações (busca do YouTube via yt-dlp)
- Vídeos "virais" de concorrentes (muito acima da média do próprio concorrente)
- Google Trends Brasil (assuntos do dia — a IA só usa o que tiver ligação com o nicho)
"""
from __future__ import annotations

import logging
import statistics
from concurrent.futures import ThreadPoolExecutor
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
    try:
        f = feedparser.parse(httpx.get("https://trends.google.com/trending/rss?geo=BR", timeout=20, headers=UA).text)
        return [e.title for e in f.entries[:25]]
    except Exception:  # noqa: BLE001
        return []


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
    trends = google_trends_br()
    return {"keywords": kws, "suggestions": sugg, "top_videos": hits[:25], "viral": viral, "trends": trends}


def signals_to_ideas(ch: Channel, sig: dict[str, Any], count: int = 6) -> list[dict[str, Any]]:
    used = content.existing_titles(ch.id)
    sug = "\n".join(f"- {k}: {', '.join(v)}" for k, v in sig["suggestions"].items() if v)
    top = "\n".join(f"- “{t}” — {v:,} views ({c})".replace(",", ".") for t, v, c, _ in sig["top_videos"][:20])
    vir = "\n".join(f"- “{x['title']}” — {x['views']:,} views ({x['ratio']}x a média do canal {c.split('/')[-1]})".replace(",", ".")
                    for c, xs in sig["viral"].items() for x in xs)
    prompt = f"""{content.channel_brief(ch)}

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
            f"{sum(len(v) for v in sig['viral'].values())} virais de concorrentes, {len(sig['trends'])} tendências")
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
    for i, iid in enumerate(created):
        ctx.update(0.65 + 0.3 * i / max(1, len(created)), f"Avaliando pauta de tendência {i + 1}/{len(created)}")
        _score(ch, iid, ctx)
        enqueue("verify_idea", title="Checar fatos da pauta", channel_id=ch.id, ref_id=iid)
    ctx.log(f"{len(created)} pautas de tendência criadas")
    return {"ideas": created}
