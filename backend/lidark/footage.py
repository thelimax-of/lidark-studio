"""Filmagens reais nas cenas (B-roll): NASA (domínio público), Wikimedia Commons (só domínio público/CC0)
e Pexels Vídeos (se houver chave). Nada de baixar o arquivo inteiro: tira quadros direto da internet,
a IA de visão avalia (com o mesmo filtro de segurança das fotos) e só o trecho escolhido é recortado.
"""
from __future__ import annotations

import hashlib
import logging
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import httpx

from . import config
from .config import CACHE_DIR, USER_AGENT
from .media import ffmpeg_exe

log = logging.getLogger("lidark.footage")
UA = {"User-Agent": USER_AGENT}
CLIPS = CACHE_DIR / "clips"
CLIPS.mkdir(parents=True, exist_ok=True)
MIN_SCORE = 72  # filmagem só entra se for claramente boa para o trecho (senão fica a foto)


# ================================================================ busca

def nasa_videos(query: str, n: int = 3) -> list[dict[str, Any]]:
    try:
        r = httpx.get("https://images-api.nasa.gov/search", headers=UA, timeout=25,
                      params={"q": query, "media_type": "video", "page_size": n * 2})
        items = r.json().get("collection", {}).get("items", [])
    except Exception as e:  # noqa: BLE001
        log.info("nasa vídeo: %s", e)
        return []
    out = []
    for it in items:
        d = (it.get("data") or [{}])[0]
        nid = d.get("nasa_id")
        if not nid:
            continue
        try:
            files = [x["href"] for x in httpx.get(f"https://images-api.nasa.gov/asset/{nid}", headers=UA,
                                                  timeout=25).json()["collection"]["items"]]
        except Exception:  # noqa: BLE001
            continue
        url = next((f for suf in ("~large.mp4", "~medium.mp4", "~orig.mp4") for f in files if f.endswith(suf)), None)
        if url:
            out.append({"source": "nasa", "url": url.replace("http://", "https://"), "title": d.get("title", ""),
                        "page": f"https://images.nasa.gov/details/{nid}", "license": "NASA (domínio público)"})
        if len(out) >= n:
            break
    return out


def commons_videos(query: str, n: int = 3) -> list[dict[str, Any]]:
    from .visuals import license_free
    try:
        r = httpx.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=25, params={
            "action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:video",
            "gsrnamespace": 6, "gsrlimit": n * 3, "prop": "videoinfo", "viprop": "url|size|extmetadata|derivatives"})
        pages = (r.json().get("query") or {}).get("pages") or {}
    except Exception as e:  # noqa: BLE001
        log.info("commons vídeo: %s", e)
        return []
    out = []
    for p in pages.values():
        vi = (p.get("videoinfo") or [{}])[0]
        lic = ((vi.get("extmetadata") or {}).get("LicenseShortName") or {}).get("value", "")
        c = {"source": "commons", "license": lic, "url": vi.get("url", "")}
        if not vi.get("url") or not license_free(c):
            continue
        ders = [d for d in vi.get("derivatives", []) if "webm" in d.get("type", "") and d.get("height")]
        best = min(ders, key=lambda d: abs(int(d["height"]) - 1080), default=None)
        out.append({**c, "url": best["src"] if best else vi["url"], "title": p.get("title", "").replace("File:", ""),
                    "page": vi.get("descriptionurl", ""), "duration": float(vi.get("duration") or 0)})
        if len(out) >= n:
            break
    return out


def pexels_videos(query: str, n: int = 3) -> list[dict[str, Any]]:
    key = config.get("pexels_api_key")
    if not key:
        return []
    try:
        r = httpx.get("https://api.pexels.com/videos/search", headers={"Authorization": key}, timeout=25,
                      params={"query": query, "per_page": n})
        vids = r.json().get("videos", [])
    except Exception as e:  # noqa: BLE001
        log.info("pexels vídeo: %s", e)
        return []
    out = []
    for v in vids:
        files = sorted((f for f in v.get("video_files", []) if f.get("height")), key=lambda f: abs(f["height"] - 1080))
        if files:
            out.append({"source": "pexels", "url": files[0]["link"], "title": v.get("url", ""), "page": v.get("url", ""),
                        "license": "Pexels", "duration": float(v.get("duration") or 0)})
    return out


def candidates(query: str, query_pt: str = "") -> list[dict[str, Any]]:
    from .visuals import SPACE_WORDS
    space = any(w in f" {query.lower()} {query_pt.lower()} " for w in SPACE_WORDS)
    c = (nasa_videos(query, 3) if space else []) + commons_videos(query, 3) + pexels_videos(query, 2)
    if len(c) < 2 and query_pt:
        c += commons_videos(query_pt, 2)
    return c


# ================================================================ ffmpeg direto da URL

def duration(url: str) -> float:
    try:
        p = subprocess.run([ffmpeg_exe(), "-hide_banner", "-user_agent", USER_AGENT, "-i", url],
                           capture_output=True, text=True, timeout=40)
        m = re.search(r"Duration: (\d+):(\d+):(\d+\.?\d*)", p.stderr)
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def grab(url: str, t: float, out: Path) -> Path | None:
    try:
        subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-user_agent", USER_AGENT,
                        "-ss", f"{t:.2f}", "-i", url, "-frames:v", "1", "-q:v", "3", str(out)],
                       capture_output=True, timeout=60)
        return out if out.exists() and out.stat().st_size > 3000 else None
    except Exception:  # noqa: BLE001
        return None


def cut(url: str, start: float, secs: float, w: int, h: int, out: Path) -> Path | None:
    """Recorta só o trecho, já no tamanho do vídeo final (cobre a tela), 30 fps, sem áudio."""
    vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30,setsar=1"
    try:
        subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", "-user_agent", USER_AGENT,
                        "-ss", f"{start:.2f}", "-i", url, "-t", f"{secs:.2f}", "-an", "-vf", vf,
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", str(out)],
                       capture_output=True, timeout=240)
        return out if out.exists() and out.stat().st_size > 20000 else None
    except Exception:  # noqa: BLE001
        return None


# ================================================================ escolha para a cena

def pick_scene_clip(scene: dict[str, Any], context: str, need: float, size: tuple[int, int],
                    used: set[str], log_fn=lambda m: None) -> dict[str, Any] | None:
    """Melhor filmagem para a cena (ou None — aí a cena fica com foto)."""
    from .visuals import judge_images
    v = scene.get("visual") or {}
    query = v.get("video_query") or v.get("query") or scene.get("label") or scene.get("text", "")[:60]
    cands = [c for c in candidates(query, v.get("query_pt", "")) if c["url"] not in used][:4]
    if not cands:
        log_fn("sem filmagem livre de crédito — usando foto")
        return None
    key = hashlib.sha1(query.encode()).hexdigest()[:10]

    def sample(ic):
        i, c = ic
        d = c.get("duration") or duration(c["url"])
        if d < 2:
            return []
        c["duration"] = d
        times = [d * 0.5] if d < need * 3 else [max(3.0, d * f) for f in (0.3, 0.6)]
        frames = []
        for k, t in enumerate(times):
            f = grab(c["url"], min(t, max(0.0, d - 1)), CLIPS / f"{key}_{i}_{k}.jpg")
            if f:
                frames.append((c, t, f))
        return frames

    with ThreadPoolExecutor(4) as ex:
        frames = [f for fs in ex.map(sample, enumerate(cands)) for f in fs]
    if not frames:
        return None
    scores = []
    for i in range(0, len(frames), 6):
        batch = frames[i:i + 6]
        scores += judge_images(scene.get("text", ""), context, [f for _, _, f in batch])
    best_i = max(range(len(frames)), key=lambda i: scores[i]["score"])
    c, t, still = frames[best_i]
    sc = scores[best_i]
    if sc["score"] < MIN_SCORE:
        log_fn(f"filmagem com nota {sc['score']} (mínimo {MIN_SCORE}) — usando foto")
        return None
    secs = need + 0.8
    start = max(0.0, min(t - secs / 2, c["duration"] - secs))
    out = cut(c["url"], start, secs, size[0], size[1], CLIPS / f"{key}_{hashlib.sha1(c['url'].encode()).hexdigest()[:8]}_{int(start)}.mp4")
    if not out:
        log_fn("falha ao recortar a filmagem — usando foto")
        return None
    used.add(c["url"])
    log_fn(f"Filmagem real ({c['source']}) nota {sc['score']}: {c['title'][:50]}")
    return {"kind": "video", "path": str(still), "clip": str(out), "score": sc["score"], "label": sc.get("label", ""),
            "source": c["source"], "license": c["license"], "url": c["url"], "page": c.get("page", ""),
            "reason": sc.get("reason", ""), "clip_start": round(start, 1)}
