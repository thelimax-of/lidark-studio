"""Trilha sonora sem direitos autorais + efeitos sonoros sintetizados.

Prioridade: biblioteca local (data/music/<estilo>/*.mp3 — ex.: faixas da Biblioteca de Áudio do YouTube)
→ Openverse (Jamendo/Freesound/ccMixter com licença que permite uso comercial).
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import wave
from pathlib import Path
from typing import Any

import httpx
import numpy as np

from .config import CACHE_DIR, MUSIC_DIR, USER_AGENT

log = logging.getLogger("lidark.music")
UA = {"User-Agent": USER_AGENT}
AUDIO_EXT = (".mp3", ".wav", ".ogg", ".m4a", ".flac")
_cache = CACHE_DIR / "music"
_cache.mkdir(parents=True, exist_ok=True)
_used_file = _cache / "_recent.json"


def library(channel_slug: str = "") -> list[Path]:
    """Músicas locais: primeiro as do canal (data/music/<canal>/), senão as compartilhadas (data/music/)."""
    if channel_slug:
        own = MUSIC_DIR / channel_slug
        files = [p for p in own.rglob("*") if p.suffix.lower() in AUDIO_EXT] if own.exists() else []
        if files:
            return files
    return [p for p in MUSIC_DIR.glob("*") if p.suffix.lower() in AUDIO_EXT] +         [p for d in MUSIC_DIR.iterdir() if d.is_dir() and d.name.startswith("_") for p in d.rglob("*") if p.suffix.lower() in AUDIO_EXT]


def _recent() -> list[str]:
    try:
        return json.loads(_used_file.read_text())
    except Exception:  # noqa: BLE001
        return []


def _mark_used(key: str) -> None:
    r = [key] + [x for x in _recent() if x != key]
    _used_file.write_text(json.dumps(r[:15]))


# climas da biblioteca do canal (data/music/<canal>/<clima>/): o nome da pasta vale estas palavras
MOODS = {
    "misterio": {"label": "Mistério / suspense", "words": "suspense mystery dark tension investig",
                 "yt": "Clima: Sombrio · Gênero: Cinematográfico ou Ambiente"},
    "epico": {"label": "Épico / dramático", "words": "epic cinematic dramatic documentary",
              "yt": "Clima: Dramático ou Inspirador · Gênero: Cinematográfico"},
    "emocao": {"label": "Emoção / piano", "words": "emotional piano tender nostalg sad",
               "yt": "Clima: Triste ou Calmo · Gênero: Clássico ou Ambiente"},
    "energia": {"label": "Energia / ritmo", "words": "energetic upbeat pulse drive",
                "yt": "Clima: Animado ou Feliz · Gênero: Eletrônica ou Pop"},
    "curiosidade": {"label": "Curiosidade / leve", "words": "curious playful light quirky",
                    "yt": "Clima: Funky ou Animado · Gênero: Infantil, Jazz ou Pop"},
}


def _mood_text(p: Path) -> str:
    return f"{str(p).lower()} {MOODS.get(p.parent.name, {}).get('words', '')}"


def pick_track(mood: str, min_seconds: float, channel_slug: str = "", focus: str = "") -> dict[str, Any] | None:
    """Escolhe uma trilha, evitando repetir as últimas usadas. `focus` (o clima pedido pelo roteiro)
    pesa 3× mais que o gosto geral do canal (`mood`)."""
    recent = set(_recent())
    words = [w for w in mood.lower().split() if len(w) > 2]
    fwords = [w for w in focus.lower().split() if len(w) > 2]
    local = library(channel_slug)
    if local:
        def score(p: Path) -> int:
            t = _mood_text(p)
            return 3 * sum(w in t for w in fwords) + sum(w in t for w in words)
        scored = sorted(local, key=lambda p: (-score(p), str(p) in recent, random.random()))
        p = scored[0]
        _mark_used(str(p))
        return {"path": str(p), "title": p.stem, "attribution": "", "source": "local"}
    mood = f"{mood} {focus}".strip()
    track = _openverse(mood, min_seconds, recent)
    if track:
        _mark_used(track["key"])
        return track
    # reserva: trilha ambiente sintetizada (livre de direitos, sem crédito)
    seed = random.randint(0, 9999)
    return {"path": str(ambient_track(min_seconds + 2, seed, mood)), "title": f"Ambiente gerado #{seed}",
            "attribution": "", "source": "gerada"}


def _openverse(mood: str, min_seconds: float, recent: set[str]) -> dict[str, Any] | None:
    words = [w for w in mood.lower().split() if len(w) > 3]
    queries = list(dict.fromkeys([mood] + words + ["ambient", "cinematic", "piano", "atmospheric", "drone"]))
    for q in queries:
        try:
            from . import config
            free = bool(config.get("no_attribution_only"))
            params = {"q": q, "page_size": 30}
            params.update({"license": "cc0,pdm"} if free else {"license_type": "commercial,modification",
                                                              "category": "music"})
            r = httpx.get("https://api.openverse.org/v1/audio/", headers=UA, timeout=60, params=params)
            allowed = ("cc0", "pdm") if free else ("by", "cc0", "pdm", "by-sa")
            res = [x for x in r.json().get("results", [])
                   if (x.get("duration") or 0) / 1000 >= min(min_seconds, 120) and x.get("url") not in recent
                   and (x.get("license") or "").lower() in allowed]
        except Exception as e:  # noqa: BLE001
            log.warning("openverse audio: %s", e)
            continue
        random.shuffle(res)
        for x in res[:4]:
            p = _cache / (hashlib.sha1(x["url"].encode()).hexdigest() + Path(x["url"]).suffix[:5])
            if not p.exists():
                try:
                    d = httpx.get(x["url"], headers=UA, timeout=90, follow_redirects=True)
                    d.raise_for_status()
                    p.write_bytes(d.content)
                except Exception as e:  # noqa: BLE001
                    log.info("download música: %s", e)
                    continue
            lic = (x.get("license") or "").upper()
            attribution = f"Música: \"{x.get('title')}\" por {x.get('creator')} ({'CC ' + lic if lic not in ('CC0', 'PDM') else 'domínio público'}) {x.get('foreign_landing_url', '')}"
            return {"path": str(p), "title": x.get("title"), "attribution": attribution, "source": x.get("source"), "key": x["url"]}
    return None


# ================================================================ efeitos sonoros procedurais

SR = 44100


def _write(path: Path, data: np.ndarray) -> Path:
    data = np.clip(data, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((data * 32767).astype(np.int16).tobytes())
    return path


def sfx(kind: str) -> Path:
    p = _cache / f"sfx_{kind}.wav"
    if p.exists():
        return p
    rng = np.random.default_rng(7)
    if kind == "whoosh":
        n = int(SR * 0.45)
        t = np.linspace(0, 1, n)
        noise = rng.standard_normal(n)
        # filtro passa-banda "deslizante" simples via média móvel variável
        out = np.zeros(n)
        acc = 0.0
        for i in range(n):
            a = 0.02 + 0.5 * t[i]
            acc = acc + a * (noise[i] - acc)
            out[i] = acc
        env = np.sin(np.pi * t) ** 1.5
        data = out * env * 0.9
    elif kind == "pop":
        n = int(SR * 0.12)
        t = np.arange(n) / SR
        f = 900 * np.exp(-t * 18) + 300
        data = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 35) * 0.6
    elif kind == "tick":
        n = int(SR * 0.05)
        t = np.arange(n) / SR
        data = np.sin(2 * np.pi * 2400 * t) * np.exp(-t * 120) * 0.5
    elif kind == "riser":
        n = int(SR * 0.8)
        t = np.arange(n) / SR
        f = 200 + 900 * (t / t[-1]) ** 2
        data = (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25 + rng.standard_normal(n) * 0.08) * (t / t[-1]) ** 2
    elif kind == "impact":
        n = int(SR * 0.9)
        t = np.arange(n) / SR
        data = (np.sin(2 * np.pi * 55 * t) * np.exp(-t * 5) + rng.standard_normal(n) * np.exp(-t * 25) * 0.4) * 0.8
    else:
        raise ValueError(kind)
    m = np.abs(data).max() or 1
    return _write(p, data / m * 0.8)


# ================================================================ trilha ambiente procedural

def _mood_layers(mood: str, n: int, sr: int, prog: list[int], chord_len: float, rng) -> np.ndarray | None:
    """Camadas que mudam o caráter da trilha conforme o clima pedido pela estrutura do roteiro."""
    m = mood.lower()
    t_all = np.arange(n) / sr
    out = np.zeros(n, np.float32)

    def hz(x):
        return 440.0 * 2 ** ((x - 69) / 12)

    def hit(at: float, f: float, dur: float, decay: float, amp: float, harm=(1.0,)):
        a = int(at * sr)
        if a >= n:
            return
        L = min(n - a, int(dur * sr))
        tt = np.arange(L) / sr
        sig = sum(np.sin(2 * np.pi * f * h * tt) / (i + 1) for i, h in enumerate(harm))
        out[a:a + L] += (sig * np.exp(-tt * decay) * amp).astype(np.float32)

    used = False
    secs = n / sr
    if any(w in m for w in ("energ", "upbeat", "drive", "pulse")):  # pulso rítmico (colcheias) + bumbo suave
        bpm = float(rng.choice([92, 100, 108]))
        beat = 60 / bpm
        k = 0
        while k * beat / 2 < secs:
            at = k * beat / 2
            root = prog[int(at // chord_len) % len(prog)]
            hit(at, hz(root + (12 if k % 4 == 2 else 0)), 0.3, 9, 0.5, (1.0, 2.0))
            if k % 2 == 0:
                hit(at, 55, 0.25, 18, 0.9)
            k += 1
        used = True
    if any(w in m for w in ("suspense", "myster", "tension", "investig")):  # tique-taque + grave pulsante
        step = float(rng.choice([0.5, 0.6]))
        k = 0
        while k * step < secs:
            hit(k * step, 2400 if k % 2 else 1800, 0.04, 120, 0.35)
            k += 1
        out += (np.sin(2 * np.pi * 41 * t_all) * (0.5 + 0.5 * np.sin(2 * np.pi * t_all / 2.4)) * 0.25).astype(np.float32)
        used = True
    if any(w in m for w in ("emotion", "piano", "tender", "nostalg")):  # arpejo tipo piano
        step = float(rng.choice([0.45, 0.55]))
        k = 0
        while k * step < secs:
            at = k * step
            root = prog[int(at // chord_len) % len(prog)]
            hit(at, hz(root + 12 + [0, 3, 7, 12, 7, 3][k % 6]), 2.2, 2.2, 0.35, (1.0, 2.0, 3.0))
            k += 1
        used = True
    if any(w in m for w in ("epic", "cinematic", "dramatic")):  # tambores graves nas trocas de acorde
        k = 0
        while k * chord_len / 2 < secs:
            hit(k * chord_len / 2, 62, 1.2, 4, 1.0, (1.0, 1.5))
            k += 1
        used = True
    return out if used else None


def ambient_track(seconds: float, seed: int = 0, mood: str = "") -> Path:
    """Pad cinematográfico (acordes lentos, graves suaves, brilho e eco). 100% gerado, sem direitos."""
    tag = hashlib.md5(mood.lower().encode()).hexdigest()[:6]
    p = _cache / f"ambient_{seed}_{int(seconds)}_{tag}.wav"
    if p.exists():
        return p
    sr = 32000
    rng = np.random.default_rng(seed)
    n = int(seconds * sr)
    t = np.arange(n) / sr
    dark = any(w in mood.lower() for w in ("dark", "myster", "horror", "space", "suspense", "terror"))
    # progressões em lá menor / ré menor (MIDI)
    progs = [[57, 53, 60, 55], [57, 60, 53, 52], [50, 53, 48, 55], [57, 52, 53, 48]]
    prog = progs[rng.integers(len(progs))]
    chord_len = 6.0 if not dark else 8.0
    out = np.zeros(n, np.float32)
    def note(m):
        return 440.0 * 2 ** ((m - 69) / 12)
    for ci in range(int(seconds // chord_len) + 2):
        root = prog[ci % len(prog)]
        minor = ci % len(prog) in (0, 1) or dark
        notes = [root - 12, root, root + (3 if minor else 4), root + 7, root + 12]
        a, b = int(ci * chord_len * sr), int(min(n, (ci + 1.6) * chord_len * sr))
        if a >= n:
            break
        tt = t[a:b] - t[a]
        L = len(tt)
        env = np.minimum(1, tt / 2.5) * np.minimum(1, (L / sr - tt) / 3.0)
        env = np.clip(env, 0, 1)
        seg = np.zeros(L, np.float32)
        for k, mnote in enumerate(notes):
            f = note(mnote)
            for det in (-0.12, 0.0, 0.11):  # coro (vozes desafinadas)
                ph = rng.uniform(0, 6.28)
                seg += (np.sin(2 * np.pi * f * (1 + det / 100) * tt + ph) * (0.5 if k == 0 else 0.22)).astype(np.float32)
        out[a:b] += seg * env.astype(np.float32)
    # brilho: notas suaves aleatórias tipo "sino"
    for _ in range(int(seconds / 3)):
        st = rng.uniform(0, seconds - 3)
        f = note(prog[0] + 24 + int(rng.choice([0, 3, 7, 10, 12])))
        a = int(st * sr)
        L = min(n - a, int(3 * sr))
        tt = np.arange(L) / sr
        out[a:a + L] += (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 1.6) * 0.06).astype(np.float32)
    # filtro passa-baixa simples + eco (reverb barato)
    lp = np.empty_like(out)
    acc = 0.0
    k = 0.08
    for i in range(n):
        acc += k * (out[i] - acc)
        lp[i] = acc
    wet = lp.copy()
    for delay, gain in ((0.13, 0.35), (0.29, 0.25), (0.47, 0.18), (0.71, 0.12)):
        d = int(delay * sr)
        wet[d:] += lp[:-d] * gain
    swell = 0.85 + 0.15 * np.sin(2 * np.pi * t / 17)
    mix = wet * swell
    extra = _mood_layers(mood, n, sr, prog, chord_len, rng)
    if extra is not None:
        mix = mix + extra * (np.abs(mix).max() or 1) / (np.abs(extra).max() or 1) * 0.45
    mix /= (np.abs(mix).max() or 1)
    mix *= 0.8
    fade = int(2 * sr)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    stereo = np.stack([mix, np.roll(mix, int(0.012 * sr))], axis=1)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.clip(stereo, -1, 1) * 32767).astype(np.int16).tobytes())
    return p
