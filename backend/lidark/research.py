"""Pesquisa na internet: Wikipédia, busca web (DuckDuckGo), Google News RSS e extração de páginas."""
from __future__ import annotations

import hashlib
import json
import logging
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import quote

import feedparser
import httpx

from .config import CACHE_DIR, USER_AGENT

log = logging.getLogger("lidark.research")
UA = {"User-Agent": USER_AGENT}
_cache_dir = CACHE_DIR / "research"
_cache_dir.mkdir(parents=True, exist_ok=True)


def _cached(key: str, fn, ttl_ok: bool = True):
    p = _cache_dir / (hashlib.sha1(key.encode()).hexdigest() + ".json")
    if ttl_ok and p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    data = fn()
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


# ---------------------------------------------------------------- Wikipédia

def wiki_search(query: str, lang: str = "pt", limit: int = 5) -> list[dict[str, Any]]:
    def run():
        r = httpx.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=20, params={
            "action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json",
        })
        r.raise_for_status()
        return [{"title": h["title"], "url": f"https://{lang}.wikipedia.org/wiki/{quote(h['title'].replace(' ', '_'))}",
                 "snippet": _strip_html(h.get("snippet", ""))} for h in r.json()["query"]["search"]]
    try:
        return _cached(f"wikisearch:{lang}:{query}:{limit}", run)
    except Exception as e:  # noqa: BLE001
        log.warning("wiki_search: %s", e)
        return []


def wiki_extract(title: str, lang: str = "pt", chars: int = 6000) -> str:
    def run():
        r = httpx.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=20, params={
            "action": "query", "prop": "extracts", "explaintext": 1, "titles": title,
            "format": "json", "redirects": 1,
        })
        r.raise_for_status()
        pages = r.json()["query"]["pages"]
        return next(iter(pages.values())).get("extract", "")
    try:
        return _cached(f"wikiext:{lang}:{title}", run)[:chars]
    except Exception as e:  # noqa: BLE001
        log.warning("wiki_extract: %s", e)
        return ""


def wiki_on_this_day(lang: str = "pt") -> list[dict[str, Any]]:
    """Eventos 'neste dia' — ótima fonte de pautas históricas."""
    import datetime as dt
    d = dt.date.today()
    try:
        r = httpx.get(f"https://api.wikimedia.org/feed/v1/wikipedia/{lang}/onthisday/events/{d.month:02d}/{d.day:02d}",
                      headers=UA, timeout=20)
        r.raise_for_status()
        out = []
        for ev in r.json().get("events", [])[:40]:
            pages = ev.get("pages") or [{}]
            out.append({"title": f"{ev.get('year')}: {ev.get('text')}", "year": ev.get("year"),
                        "url": pages[0].get("content_urls", {}).get("desktop", {}).get("page", ""),
                        "snippet": pages[0].get("extract", "")[:400]})
        return out
    except Exception as e:  # noqa: BLE001
        log.warning("onthisday: %s", e)
        return []


def wiki_random_featured(lang: str = "pt", n: int = 10) -> list[dict[str, Any]]:
    try:
        r = httpx.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=20, params={
            "action": "query", "list": "random", "rnnamespace": 0, "rnlimit": n, "format": "json"})
        r.raise_for_status()
        return [{"title": p["title"]} for p in r.json()["query"]["random"]]
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------- Web

def web_search(query: str, limit: int = 8, region: str = "br-pt") -> list[dict[str, Any]]:
    def run():
        from ddgs import DDGS
        with DDGS() as d:
            return [{"title": x.get("title", ""), "url": x.get("href", ""), "snippet": x.get("body", "")}
                    for x in d.text(query, region=region, max_results=limit)]
    try:
        return _cached(f"ddg:{region}:{query}:{limit}", run)
    except Exception as e:  # noqa: BLE001
        log.warning("web_search: %s", e)
        return []


def news_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    try:
        feed = feedparser.parse(httpx.get(url, headers=UA, timeout=20).text)
        return [{"title": e.title, "url": e.link, "snippet": _strip_html(e.get("summary", "")),
                 "published": e.get("published", "")} for e in feed.entries[:limit]]
    except Exception as e:  # noqa: BLE001
        log.warning("news_search: %s", e)
        return []


def fetch_page_text(url: str, chars: int = 5000) -> str:
    def run():
        import trafilatura
        r = httpx.get(url, headers={**UA, "User-Agent": "Mozilla/5.0"}, timeout=25, follow_redirects=True)
        r.raise_for_status()
        return trafilatura.extract(r.text, include_comments=False, include_tables=False) or ""
    try:
        return _cached(f"page:{url}", run)[:chars]
    except Exception as e:  # noqa: BLE001
        log.info("fetch_page_text %s: %s", url, e)
        return ""


def gather_dossier(topic: str, lang: str = "pt", max_sources: int = 6) -> dict[str, Any]:
    """Junta material de várias fontes sobre um tema: base para roteiro e checagem."""
    wiki_hits = wiki_search(topic, lang, 3)
    web_hits = web_search(topic, 8)
    sources: list[dict[str, Any]] = []
    for h in wiki_hits[:2]:
        sources.append({**h, "kind": "wikipedia", "text": wiki_extract(h["title"], lang, 5000)})
    good_web = [h for h in web_hits if h["url"] and not any(b in h["url"] for b in _BLOCKED_DOMAINS)]
    with ThreadPoolExecutor(4) as ex:
        texts = list(ex.map(lambda h: fetch_page_text(h["url"], 4000), good_web[:max_sources]))
    for h, t in zip(good_web, texts):
        if len(t) > 300:
            sources.append({**h, "kind": "web", "text": t})
    return {"topic": topic, "sources": sources[:max_sources + 2]}


_BLOCKED_DOMAINS = ("youtube.com", "tiktok.com", "instagram.com", "facebook.com", "pinterest.", "x.com", "twitter.com")


def _strip_html(s: str) -> str:
    from bs4 import BeautifulSoup
    return BeautifulSoup(s, "html.parser").get_text(" ", strip=True)


def shuffle(xs: list) -> list:
    xs = list(xs)
    random.shuffle(xs)
    return xs
