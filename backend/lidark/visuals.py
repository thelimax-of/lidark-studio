"""Imagens das cenas: busca de fotos reais (Wikimedia Commons, Wikipédia, Openverse, Pexels),
geração por IA (Pollinations/Flux, Gemini) e controle de qualidade com IA de visão.
"""
from __future__ import annotations

import hashlib
import io
import logging
import random
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from PIL import Image

from . import config, llm
from .config import CACHE_DIR, USER_AGENT

log = logging.getLogger("lidark.visuals")
UA = {"User-Agent": USER_AGENT}
IMG_CACHE = CACHE_DIR / "images"
IMG_CACHE.mkdir(parents=True, exist_ok=True)


# ================================================================ busca de fotos reais

def commons_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    try:
        r = httpx.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=25, params={
            "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
            "gsrsearch": f"filetype:bitmap {query}", "gsrlimit": limit,
            "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1280,
        })
        pages = (r.json().get("query") or {}).get("pages") or {}
    except Exception as e:  # noqa: BLE001
        log.warning("commons: %s", e)
        return []
    out = []
    for p in sorted(pages.values(), key=lambda x: x.get("index", 0)):
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png", "image/webp", "image/tiff"):
            continue
        md = ii.get("extmetadata") or {}
        out.append({
            "source": "commons", "url": ii.get("thumburl") or ii.get("url"), "page": ii.get("descriptionurl"),
            "width": ii.get("width", 0), "height": ii.get("height", 0), "title": p.get("title", ""),
            "license": (md.get("LicenseShortName") or {}).get("value", ""),
            "credit": _strip((md.get("Artist") or {}).get("value", "")),
        })
    return out


def wikipedia_images(query: str, lang: str = "pt", limit: int = 4) -> list[dict[str, Any]]:
    """Imagem principal dos artigos mais relevantes (ótimo para pessoas, lugares e eventos)."""
    try:
        r = httpx.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=25, params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": query, "gsrlimit": limit,
            "prop": "pageimages", "piprop": "original|name", "pilicense": "any",
        })
        pages = (r.json().get("query") or {}).get("pages") or {}
    except Exception as e:  # noqa: BLE001
        log.warning("wikipedia images: %s", e)
        return []
    out = []
    for p in sorted(pages.values(), key=lambda x: x.get("index", 0)):
        o = p.get("original")
        if o and not o["source"].lower().endswith((".svg", ".gif")):
            out.append({"source": "wikipedia", "url": _thumb(o["source"], 1280), "page": f"https://{lang}.wikipedia.org/wiki/{quote(p['title'])}",
                        "width": o.get("width", 0), "height": o.get("height", 0), "title": p["title"],
                        "license": "ver página", "credit": "Wikipedia/Wikimedia Commons"})
    return out


def openverse_search(query: str, limit: int = 8) -> list[dict[str, Any]]:
    try:
        params = {"q": query, "page_size": limit, "mature": "false"}
        if config.get("no_attribution_only"):
            params["license"] = "cc0,pdm"
        r = httpx.get("https://api.openverse.org/v1/images/", headers=UA, timeout=25, params=params)
        res = r.json().get("results", [])
    except Exception as e:  # noqa: BLE001
        log.warning("openverse: %s", e)
        return []
    return [{"source": "openverse", "url": x["url"], "page": x.get("foreign_landing_url"), "width": x.get("width") or 0,
             "height": x.get("height") or 0, "title": x.get("title", ""),
             "license": f"{x.get('license', '').upper()} {x.get('license_version', '')}".strip(),
             "credit": x.get("creator") or ""} for x in res]


def nasa_search(query: str, limit: int = 6) -> list[dict[str, Any]]:
    """Acervo de imagens da NASA (domínio público) — excelente para espaço, astronomia e ciência."""
    try:
        r = httpx.get("https://images-api.nasa.gov/search", headers=UA, timeout=25,
                      params={"q": query, "media_type": "image", "page_size": limit})
        items = r.json().get("collection", {}).get("items", [])
    except Exception as e:  # noqa: BLE001
        log.warning("nasa: %s", e)
        return []
    out = []
    for it in items[:limit]:
        d = (it.get("data") or [{}])[0]
        href = (it.get("links") or [{}])[0].get("href", "")
        if not href:
            continue
        big = href.replace("~thumb", "~large").replace("~small", "~large").replace("~medium", "~large")
        out.append({"source": "nasa", "url": big, "page": f"https://images.nasa.gov/details/{d.get('nasa_id', '')}",
                    "width": 0, "height": 0, "title": d.get("title", ""), "license": "NASA (domínio público)",
                    "credit": d.get("center") or "NASA"})
    return out


def cleveland_search(query: str, limit: int = 6) -> list[dict[str, Any]]:
    """Museu de Arte de Cleveland — acervo aberto CC0 (pinturas, gravuras, objetos e fotos históricas)."""
    try:
        r = httpx.get("https://openaccess-api.clevelandart.org/api/artworks/", headers=UA, timeout=25,
                      params={"q": query, "has_image": 1, "cc0": 1, "limit": limit})
        data = r.json().get("data", [])
    except Exception as e:  # noqa: BLE001
        log.warning("cleveland: %s", e)
        return []
    out = []
    for d in data:
        img = (d.get("images") or {}).get("web") or {}
        if not img.get("url") or d.get("share_license_status") != "CC0":
            continue
        out.append({"source": "cleveland", "url": img["url"], "page": d.get("url", ""), "width": int(img.get("width") or 0),
                    "height": int(img.get("height") or 0), "title": d.get("title", ""), "license": "CC0",
                    "credit": "Cleveland Museum of Art"})
    return out


def smithsonian_search(query: str, limit: int = 6) -> list[dict[str, Any]]:
    """Smithsonian Open Access — só itens CC0. Chave grátis em api.data.gov (sem chave usa DEMO_KEY, limitada)."""
    key = config.get("smithsonian_api_key") or "DEMO_KEY"
    try:
        r = httpx.get("https://api.si.edu/openaccess/api/v1.0/search", headers=UA, timeout=25,
                      params={"q": f"{query} AND online_media_type:Images", "api_key": key, "rows": limit * 2})
        rows = (r.json().get("response") or {}).get("rows", [])
    except Exception as e:  # noqa: BLE001
        log.warning("smithsonian: %s", e)
        return []
    out = []
    for x in rows:
        dnr = (x.get("content") or {}).get("descriptiveNonRepeating") or {}
        for m in (dnr.get("online_media") or {}).get("media", [])[:1]:
            if (m.get("usage") or {}).get("access") != "CC0" or not m.get("content"):
                continue
            url = m["content"] + ("&max=1600" if "deliveryService" in m["content"] else "")
            out.append({"source": "smithsonian", "url": url, "page": dnr.get("record_link", ""), "width": 0, "height": 0,
                        "title": x.get("title", ""), "license": "CC0", "credit": dnr.get("data_source", "Smithsonian")})
        if len(out) >= limit:
            break
    return out


SPACE_WORDS = ("space", "planet", "star", "galaxy", "nebula", "black hole", "moon", "mars", "jupiter", "saturn", "venus",
               "mercury", "neptune", "uranus", "sun", "solar", "comet", "asteroid", "orbit", "astronaut", "rocket", "nasa",
               "universe", "cosmos", "telescope", "hubble", "webb", "supernova", "eclipse", "meteor", "espaço", "planeta",
               "estrela", "galáxia", "nebulosa", "buraco negro", "lua", "marte", "universo", "astronauta", "foguete",
               "cometa", "asteroide", "telescópio", "eclipse", "meteoro", "sol ")


def pexels_search(query: str, limit: int = 6, orientation: str = "landscape") -> list[dict[str, Any]]:
    key = config.get("pexels_api_key")
    if not key:
        return []
    try:
        r = httpx.get("https://api.pexels.com/v1/search", headers={"Authorization": key}, timeout=20,
                      params={"query": query, "per_page": limit, "orientation": orientation})
        return [{"source": "pexels", "url": p["src"]["large2x"], "page": p["url"], "width": p["width"],
                 "height": p["height"], "title": p.get("alt", ""), "license": "Pexels", "credit": p["photographer"]}
                for p in r.json().get("photos", [])]
    except Exception as e:  # noqa: BLE001
        log.warning("pexels: %s", e)
        return []


FREE_MARKERS = ("public domain", "domínio público", "dominio publico", "pd-", "pd ", "cc0", "cc-zero", "pdm",
                "no restrictions", "no known copyright", "publicdomain")


def license_free(c: dict[str, Any]) -> bool:
    """True se a imagem pode ser usada SEM dar crédito (domínio público, CC0, NASA, Pexels)."""
    if c.get("source") in ("nasa", "pexels", "cleveland", "smithsonian"):
        return True
    lic = (c.get("license") or "").lower()
    if c.get("source") == "wikipedia" and lic in ("", "ver página"):
        lic = commons_license(c["url"]).lower()
        c["license"] = lic or c.get("license", "")
    return any(m in lic for m in FREE_MARKERS)


def commons_license(url: str) -> str:
    """Licença de um arquivo do Wikimedia Commons a partir da URL da imagem."""
    from urllib.parse import unquote
    parts = url.split("/")
    name = unquote(parts[-2] if "/thumb/" in url else parts[-1])
    try:
        r = httpx.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=20, params={
            "action": "query", "format": "json", "titles": f"File:{name}", "prop": "imageinfo", "iiprop": "extmetadata"})
        pages = (r.json().get("query") or {}).get("pages") or {}
        page = next(iter(pages.values()), {})
        md = ((page.get("imageinfo") or [{}])[0]).get("extmetadata") or {}
        return (md.get("LicenseShortName") or {}).get("value", "")
    except Exception:  # noqa: BLE001
        return ""


def find_candidates(query: str, query_pt: str = "", limit: int = 8, credit_ok: bool = False) -> list[dict[str, Any]]:
    cands: list[dict[str, Any]] = []
    only_free = bool(config.get("no_attribution_only")) and not credit_ok  # canal que aceita crédito na descrição

    def add(items: list[dict[str, Any]]) -> None:
        cands.extend(c for c in items if not only_free or license_free(c))

    if query_pt:
        add(wikipedia_images(query_pt, "pt", 3))
    if any(w in f" {query.lower()} {query_pt.lower()} " for w in SPACE_WORDS):
        add(nasa_search(query, 6))
    museum: list[dict[str, Any]] = []
    if not any(w in f" {query.lower()} " for w in SPACE_WORDS):
        # acervos de museus (CC0): pinturas, gravuras, objetos e fotos de época — mais raras que as do Commons
        museum = cleveland_search(query, 2) + smithsonian_search(query, 2)
    add(commons_search(query, 12 if only_free else 10))
    if len(cands) < 3 and query_pt:
        add(commons_search(query_pt, 10))
    if len(cands) < 3:
        # consulta mais curta: as 3 palavras mais significativas
        short = " ".join(sorted(query.split(), key=len, reverse=True)[:3])
        add(commons_search(short, 10))
    if len(cands) < 6:
        add(wikipedia_images(query, "en", 3))

    if len(cands) < 6:
        add(openverse_search(query, 10))
    if len(cands) < 4:
        add(pexels_search(query))
    seen, out, extra = set(), [], []
    for c in cands + museum:
        if not c.get("url") or c["url"] in seen:
            continue
        if c.get("width") and c["width"] < 400:
            continue
        seen.add(c["url"])
        (extra if c in museum else out).append(c)
    keep = min(3, len(extra), max(1, limit // 3))  # reserva vagas para os museus sem tirar o lugar das fotos principais
    return out[:limit - keep] + extra[:keep]


# ================================================================ download

def download(url: str) -> Path | None:
    p = IMG_CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".jpg")
    if p.exists() and p.stat().st_size > 2000:
        return p
    for attempt in range(3):
        try:
            r = httpx.get(url, headers=UA, timeout=60, follow_redirects=True)
            if r.status_code == 429:
                time.sleep(3 + attempt * 4)
                continue
            r.raise_for_status()
            im = Image.open(io.BytesIO(r.content))
            im = _flatten(im)
            if min(im.size) < 300:
                return None
            im.save(p, "JPEG", quality=93)
            return p
        except Exception as e:  # noqa: BLE001
            log.info("download %s: %s", url[:80], e)
            time.sleep(1)
    return None


def _flatten(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (240, 232, 220))
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


# ================================================================ IA de visão (controle de qualidade)

def _thumb_bytes(p: Path, size: int = 512) -> bytes:
    im = Image.open(p).convert("RGB")
    im.thumbnail((size, size))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=80)
    return b.getvalue()


def judge_images(scene_text: str, context: str, paths: list[Path], ai: bool = False) -> list[dict[str, Any]]:
    """Nota 0-100 para cada imagem: relevância ao que está sendo narrado, qualidade, problemas."""
    if not paths:
        return []
    if not llm.has_vision():
        return [{"score": 75, "relevance": 75, "quality": 75, "reason": "sem IA de visão (configure o Gemini)"} for _ in paths]
    extra = ("Para imagens geradas por IA, penalize forte: mãos/rostos deformados, texto ilegível, "
             "anacronismos (objetos modernos), aparência artificial/plástica.") if ai else \
        ("Penalize forte: assunto ERRADO (ex.: lugar/pessoa homônima de outro país), marca d'água, "
         "logotipos, montagens, imagens modernas para fatos antigos, diagramas/tabelas/textos, baixa resolução.")
    extra += (" NOTA 0 obrigatória para: suásticas, símbolos nazistas/extremistas em destaque, violência gráfica, "
              "cadáveres, nudez, crianças em perigo — o vídeo vai para o YouTube e precisa ser seguro para anunciantes.")
    prompt = f"""Você é editor de imagens de um canal de história. O vídeo é sobre: {context}
A narração deste trecho diz: "{scene_text}"
Avalie cada uma das {len(paths)} imagens (na ordem enviada) para ilustrar ESTE trecho.
{extra}
Responda JSON: {{"images": [{{"relevance": 0-100, "quality": 0-100, "problems": "...", "label": "rótulo curto de 1-3 palavras em português descrevendo a imagem"}}]}}"""
    try:
        data = llm.vision_json(prompt, [_thumb_bytes(p) for p in paths])
        items = data.get("images", []) if isinstance(data, dict) else data
    except Exception as e:  # noqa: BLE001
        log.warning("judge_images: %s", e)
        return [{"score": 55, "relevance": 55, "quality": 55, "reason": f"falha na avaliação: {e}"} for _ in paths]
    out = []
    for i in range(len(paths)):
        it = items[i] if i < len(items) else {}
        rel, q = float(it.get("relevance", 50)), float(it.get("quality", 50))
        out.append({"score": round(0.65 * rel + 0.35 * q), "relevance": rel, "quality": q,
                    "reason": it.get("problems", ""), "label": it.get("label", "")})
    return out


# ================================================================ geração por IA

def generate_ai(prompt: str, width: int, height: int, seed: int | None = None) -> Path | None:
    provider = config.get("image_ai_provider")
    if provider == "none":
        return None
    seed = seed if seed is not None else random.randint(1, 10**9)
    key = hashlib.sha1(f"{provider}|{prompt}|{width}x{height}|{seed}".encode()).hexdigest()
    p = IMG_CACHE / f"ai_{key}.jpg"
    if p.exists():
        return p
    try:
        if provider == "gemini":
            data = _gemini_image(prompt, width, height)
        else:
            data = _pollinations(prompt, width, height, seed)
        if not data:
            return None
        im = _flatten(Image.open(io.BytesIO(data)))
        im.save(p, "JPEG", quality=94)
        return p
    except Exception as e:  # noqa: BLE001
        log.warning("geração IA falhou: %s", e)
        return None


def _pollinations(prompt: str, w: int, h: int, seed: int) -> bytes | None:
    url = f"https://image.pollinations.ai/prompt/{quote(prompt[:900])}"
    params = {"width": w, "height": h, "seed": seed, "model": config.get("pollinations_model"),
              "nologo": "true", "private": "true", "enhance": "false"}
    for attempt in range(4):
        try:
            r = httpx.get(url, params=params, timeout=180, follow_redirects=True, headers=UA)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                return r.content
            log.info("pollinations %s: %s", r.status_code, r.text[:120])
        except httpx.HTTPError as e:
            log.info("pollinations: %s", e)
        time.sleep(6 * (attempt + 1))
    return None


def _gemini_image(prompt: str, w: int, h: int) -> bytes | None:
    import base64
    s = config.load_settings()
    ratio = "9:16" if h > w * 1.3 else "16:9" if w > h * 1.3 else "4:3" if w > h else "3:4" if h > w else "1:1"
    for key in s["gemini_api_keys"]:
        r = httpx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image:generateContent",
                       headers={"x-goog-api-key": key}, timeout=180, json={
                           "contents": [{"parts": [{"text": prompt}]}],
                           "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": ratio}}})
        if r.status_code != 200:
            continue
        for part in r.json()["candidates"][0]["content"]["parts"]:
            if "inlineData" in part:
                return base64.b64decode(part["inlineData"]["data"])
    return None


# ================================================================ orquestração por cena

def _gather(queries: list[str], exclude: set[str], limit: int = 12, credit_ok: bool = False) -> list[dict[str, Any]]:
    """Junta candidatos de várias buscas (pt e en), sem repetir e sem imagens já usadas no vídeo."""
    seen, out = set(exclude), []
    for q in queries:
        if not q:
            continue
        for c in find_candidates(q, q if _looks_pt(q) else "", limit=8, credit_ok=credit_ok):
            if c["url"] in seen:
                continue
            seen.add(c["url"])
            out.append(c)
            if len(out) >= limit:
                return out
    return out


def _looks_pt(q: str) -> bool:
    return bool(re.search(r"[ãõçáéíóúâêô]|\b(de|da|do|dos|das|na|no|em)\b", q.lower()))


def _judge_pool(cands: list[dict[str, Any]], text: str, context: str, log_fn) -> list[tuple[dict, Path, dict]]:
    files = [(c, download(c["url"])) for c in cands]
    files = [(c, f) for c, f in files if f]
    scored = []
    for i in range(0, len(files), 6):  # avalia em lotes (uma chamada de visão por lote)
        batch = files[i:i + 6]
        for (c, f), sc in zip(batch, judge_images(text, context, [f for _, f in batch])):
            scored.append((c, f, sc))
    scored.sort(key=lambda x: -x[2]["score"])
    return scored


def _alt_queries(text: str, context: str, tried: list[str]) -> list[str]:
    try:
        data = llm.complete_json(f"""Preciso de uma IMAGEM REAL (foto de arquivo, pintura histórica, documento, mapa antigo ou objeto)
para ilustrar este trecho de vídeo. Contexto: {context}
Trecho: "{text}"
Buscas que já falharam: {tried}
Sugira 4 buscas CURTAS e concretas (2-4 palavras) para o Wikimedia Commons: 2 em inglês e 2 em português,
focando no objeto/pessoa/lugar/evento que pode ter foto real (não em ações abstratas).
Responda JSON: {{"queries": ["...", "...", "...", "..."]}}""", temperature=0.4)
        return [q for q in (data.get("queries") or []) if isinstance(q, str)][:4]
    except Exception:  # noqa: BLE001
        return []


def pick_scene_image(scene: dict[str, Any], context: str, image_style: str, size: tuple[int, int],
                     mode: str, log_fn=lambda m: None, used: set[str] | None = None,
                     credit_ok: bool = False) -> dict[str, Any] | None:
    """Escolhe a melhor imagem para a cena: várias buscas de fotos reais, novas buscas sugeridas pela IA
    e, se habilitado, geração por IA. Nunca devolve imagem abaixo da nota mínima."""
    min_q = int(config.get("image_min_quality"))
    used = used if used is not None else set()
    v = scene.get("visual") or {}
    kind = "ai" if mode == "ai" else ("real" if mode == "real" else v.get("kind", "real"))
    text = scene.get("text", "")
    best: dict[str, Any] | None = None

    def consider(scored):
        nonlocal best
        if scored:
            c, f, sc = scored[0]
            cand = {"path": str(f), "kind": "real", "score": sc["score"], "label": sc.get("label", ""),
                    "source": c["source"], "page": c.get("page"), "license": c.get("license"), "url": c["url"],
                    "credit": c.get("credit"), "reason": sc.get("reason", "")}
            if not best or cand["score"] > best["score"]:
                best = cand
            log_fn(f"Foto real ({c['source']}) nota {sc['score']}: {c.get('title', '')[:60]}")

    if kind == "real" or config.get("image_ai_provider") == "none":
        queries = [v.get("query"), v.get("query_pt"), scene.get("label"),
                   " ".join((scene.get("emphasis") or [])[:3])]
        queries = list(dict.fromkeys(q.strip() for q in queries if q and q.strip()))
        consider(_judge_pool(_gather(queries, used, credit_ok=credit_ok), text, context, log_fn))
        if not best or best["score"] < min_q:
            alt = _alt_queries(text, context, queries)
            if alt:
                log_fn(f"Tentando novas buscas: {', '.join(alt)}")
                consider(_judge_pool(_gather(alt, used | ({best["url"]} if best else set()), credit_ok=credit_ok), text, context, log_fn))

    if (not best or best["score"] < min_q) and config.get("image_ai_provider") != "none" and mode != "real":
        prompt = v.get("prompt") or f"{text}. {image_style}"
        if image_style and image_style.lower()[:20] not in prompt.lower():
            prompt = f"{prompt}, {image_style}"
        prompt += ", no text, no watermark, no letters"
        for attempt in range(3):
            f = generate_ai(prompt, *size)
            if not f:
                continue
            sc = judge_images(text, context, [f], ai=True)[0]
            log_fn(f"Imagem IA tentativa {attempt + 1}: nota {sc['score']}")
            cand = {"path": str(f), "kind": "ai", "score": sc["score"], "label": sc.get("label", ""),
                    "source": config.get("image_ai_provider"), "prompt": prompt, "reason": sc.get("reason", "")}
            if not best or cand["score"] > best["score"]:
                best = cand
            if sc["score"] >= min_q:
                break

    if best and best.get("score", 0) < HARD_MIN:
        log_fn(f"Melhor imagem com nota {best.get('score')} — descartada (mínimo {HARD_MIN})")
        return None
    if best and best.get("url"):
        used.add(best["url"])
    return best


HARD_MIN = 45  # abaixo disso a imagem nunca é usada


def _thumb(url: str, width: int) -> str:
    """Converte URL original do upload.wikimedia em miniatura (evita baixar TIFFs gigantes)."""
    if "upload.wikimedia.org" not in url or "/thumb/" in url:
        return url
    parts = url.split("/")
    try:
        i = parts.index("commons") if "commons" in parts else parts.index("wikipedia") + 1
    except ValueError:
        return url
    name = parts[-1]
    base = "/".join(parts[: i + 1]) + "/thumb/" + "/".join(parts[i + 1:])
    suffix = f"/{width}px-{name}" + (".jpg" if name.lower().endswith((".tif", ".tiff")) else "")
    return base + suffix


def _strip(html: str) -> str:
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)[:120]
