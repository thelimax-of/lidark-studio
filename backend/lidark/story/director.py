"""Diretor: transforma episódio (falas + deixas) + imagens escolhidas + áudios em "spec" de render.

- linha do tempo: cada fala no seu tempo real (duração do áudio) + respiro
- tomadas: cada fala vira 1-3 tomadas (troca visual a cada ~2-3 s): plano aberto, punch-in no rosto, detalhe,
  pan; com imagens alternativas da mesma fala quando há
- câmera por tomada no "palco" (imagem em cover-fit), personagens em camadas com entrada/olhar/pulo/fala
- widgets com janela de tempo (missão, jornal, diálogo, alerta...), relógio da história coerente com o cronômetro
- SFX: whoosh nos cortes, impacto nos cartões, ding nos objetivos, riser antes do gancho, digitação no diálogo
Tudo sorteado com a semente do episódio (variedade contra "conteúdo repetitivo"), mas reprodutível.
"""
from __future__ import annotations

import random
import re
from typing import Any

from PIL import Image

ALLOWED_FX = {"dust", "smoke", "rain", "fire", "embers", "flicker", "candle", "alarm", "flash", "stars", "bubbles",
              "confetti", "night"}
CENTER_WIDGETS = {"mission", "newspaper", "telegram", "console", "notebook", "alert", "countdown"}


def _hm(s: Any) -> int | None:
    m = re.match(r"\s*(\d{1,2})[:h](\d{2})", str(s or ""))
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def _stage(path: str, W: int, H: int) -> tuple[float, float, float]:
    with Image.open(path) as im:
        iw, ih = im.size
    s = max(W / iw, H / ih)
    return iw * s, ih * s, s


def direct(ep: dict[str, Any], visuals: list[dict[str, Any]], lines: list[dict[str, Any]], bible: dict[str, Any], *,
           W: int = 720, H: int = 1280, fps: int = 30, seed: int = 1, part_label: str = "",
           portraits: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """ep["beats"][i] ↔ visuals[i] ({"mode": scene|layered|insert, "bg": asset, "chars": [...], "alts": [...]})
    ↔ lines[i] ({"audio", "dur", "speaker"})."""
    rng = random.Random(seed)
    beats = ep["beats"]
    hud = bible.get("hud") or {}
    portraits = portraits or {}
    vertical = H > W
    # ------------------------------------------------------------ tempos das falas
    t = 0.12
    L = []
    for i, (b, ln) in enumerate(zip(beats, lines)):
        gap = 0.26 + (0.25 if b.get("pause") else 0.0) + rng.uniform(0, 0.08)
        L.append({**ln, "start": round(t, 3), "end": round(t + ln["dur"], 3), "speaker": b.get("speaker", "narrador"),
                  "text": b.get("text", "")})
        t += ln["dur"] + gap
    narration_end = L[-1]["end"]
    tail = 1.5
    total = narration_end + tail
    # ------------------------------------------------------------ tomadas
    shots: list[dict[str, Any]] = []
    target = rng.uniform(2.2, 3.0)
    for i, (b, v, ln) in enumerate(zip(beats, visuals, L)):
        b0 = ln["start"] if i else 0.0
        b1 = L[i + 1]["start"] if i + 1 < len(L) else total
        span = b1 - b0
        n = max(1, min(3, round(span / target)))
        if span < 1.9:
            n = 1
        cuts = [b0 + span * k / n for k in range(n)]
        if n > 1:  # cortes um pouco irregulares (ritmo humano)
            cuts = [cuts[0]] + [c + rng.uniform(-0.25, 0.25) for c in cuts[1:]]
        options = [v] + [a for a in (v.get("alts") or [])]
        framings = _framings(v, n, rng)
        for k in range(n):
            s0 = cuts[k]
            s1 = cuts[k + 1] if k + 1 < n else b1
            vis = options[k % len(options)] if k < len(options) else v
            fr = framings[k] if vis is v else "wide"
            sh = _shot(vis, fr, s0, s1 - s0, W, H, rng, b, speaker=ln["speaker"], first_in_beat=(k == 0))
            sh["beat"] = i
            sh["transition"] = ("cut" if k else rng.choices(["cut", "dissolve", "whip"], (5, 3, 2))[0]) if shots else "cut"
            shots.append(sh)
    # ------------------------------------------------------------ widgets
    widgets: list[dict[str, Any]] = []
    sfx: list[dict[str, Any]] = []
    amb: list[dict[str, Any]] = []
    iv, wv = rng.randrange(3), rng.randrange(4)
    mission = ep.get("mission") or {}
    objs = [o for o in (ep.get("objectives") or []) if o][:4]
    done_at: dict[int, float] = {}
    for i, b in enumerate(beats):
        od = b.get("objective_done")
        if isinstance(od, int) and 0 <= od < len(objs):
            done_at[od] = L[i]["start"] + 0.6
    for i, (b, ln) in enumerate(zip(beats, L)):
        s0, s1 = ln["start"], (L[i + 1]["start"] if i + 1 < len(L) else narration_end + 0.4)
        wdg = b.get("widget") or {}
        typ = wdg.get("type") if isinstance(wdg, dict) else None
        data = dict(wdg.get("data") or {}) if isinstance(wdg, dict) else {}
        if typ == "mission":  # no longo, cada capítulo traz a própria missão
            m = b.get("mission") if isinstance(b.get("mission"), dict) else mission
            data = {"title": m.get("title") or mission.get("title", "NOVA MISSÃO"), "subtitle": m.get("subtitle") or mission.get("subtitle", ""),
                    **({"label": f"CAPÍTULO · {str(b['chapter']).upper()[:30]}"} if b.get("chapter") else {}), **data}
        if typ == "objectives":
            data = {"items": [{"text": o, "done_at": (done_at[k] - (s0 + 0.1)) if k in done_at else None}
                              for k, o in enumerate(objs)], **data}
        if typ == "newspaper" and not data.get("name"):
            names = hud.get("paper_names") or ["Gazeta"]
            data["name"] = names[seed % len(names)]
        if typ == "countdown" and mission.get("hours"):
            # o número gigante sai do MESMO relógio da missão (nunca contradiz o cronômetro do canto)
            data["value"] = None
        if typ:
            t0 = s0 + (1.0 if (typ == "mission" and i == 0) else 0.05 if typ in ("mission", "newspaper", "alert", "countdown") else 0.15)
            t1 = max(s1, t0 + 2.4) if typ not in ("countdown",) else s1 + 0.2
            widgets.append({"type": typ, "t0": round(t0, 3), "t1": round(min(t1, total), 3), "data": data})
            if typ in ("mission", "alert", "newspaper", "countdown", "tv", "scoreboard"):
                sfx.append({"t": t0 + (0.35 if typ == "newspaper" else 0.2), "kind": "impact", "variant": iv, "gain": 0.5})
            if typ in ("phone", "chat"):
                sfx.append({"t": t0 + 0.15, "kind": "notify", "gain": 0.35})
            if typ == "radio":
                amb.append({"kind": "static", "t0": t0, "t1": t0 + 0.8})
            if typ in ("console", "notebook", "telegram"):
                sfx.append({"t": t0 + 0.3, "t1": min(t1, t0 + 2.6), "kind": "typing"})
        # diálogo: toda fala de personagem ganha caixa com retrato + digitação
        spk = ln["speaker"]
        if spk not in ("narrador", "narrator", ""):
            ch = next((c for c in bible.get("characters") or [] if c.get("id") == spk), None)
            por = portraits.get(spk) or {}
            widgets.append({"type": "dialogue", "t0": ln["start"], "t1": round(ln["end"] + 0.35, 3),
                            "data": {"who": (b.get("who") or (ch or {}).get("name") or spk) + (f" · {ch.get('role')}" if ch and ch.get("role") and rng.random() < 0.5 else ""),
                                     "text": b.get("text", ""), "portrait": por.get("file"), "eyes": por.get("eyes")}})
            sfx.append({"t": ln["start"], "t1": ln["end"] - 0.3, "kind": "typing"})
        if b.get("chip"):
            widgets.append({"type": "chip", "t0": s0 + 0.2, "t1": s1, "data": {"text": str(b["chip"])[:48].upper(), "y": 0.13 if vertical else 0.1}})
        if b.get("highlight"):
            hl = b["highlight"] if isinstance(b["highlight"], dict) else {"label": str(b["highlight"])}
            tgt = _highlight_target(hl, visuals[i], bible)
            if tgt:  # só destaca o que dá para localizar na tela (personagem); objeto solto fica sem caixa
                widgets.append({"type": "highlight", "t0": s0 + 0.5, "t1": s1, "data": {"target": tgt,
                                                                                       "label": str(hl.get("label", ""))[:30]}})
                sfx.append({"t": s0 + 0.55, "kind": "impact", "variant": (iv + 1) % 3, "gain": 0.32})
        for f in b.get("fx") or []:
            if f == "alarm":
                sfx.append({"t": s0, "t1": s1, "kind": "alarm", "gain": 0.16})
            if f == "rain":
                amb.append({"kind": "rain", "t0": s0, "t1": s1})
        if b.get("impact"):
            sfx.append({"t": s0 + 0.02, "kind": "impact", "variant": iv, "gain": 0.45})
        if b.get("crowd"):
            amb.append({"kind": "crowd", "t0": s0, "t1": s1})
    for k, ta in done_at.items():
        sfx.append({"t": ta, "kind": "ding", "variant": k % 4, "gain": 0.3})
    # whoosh nos cortes entre falas (não em todos)
    last = -9.0
    for sh in shots[1:]:
        if sh["transition"] in ("whip", "dissolve") or (sh["start"] - last > 3.5 and rng.random() < 0.5):
            sfx.append({"t": max(0.0, sh["start"] - 0.22), "kind": "whoosh", "variant": wv if rng.random() < 0.7 else rng.randrange(4),
                        "gain": 0.3})
            last = sh["start"]
    climax = L[-1]["start"] if len(L) > 2 else None
    if climax:
        sfx.append({"t": max(0.0, climax - 1.3), "kind": "riser", "variant": 0, "gain": 0.22})
    sfx.append({"t": 0.05, "kind": "riser", "variant": 0, "gain": 0.18})
    # fim: selo "PARTE N · CONTINUA…"
    widgets.append({"type": "endcard", "t0": round(narration_end - 0.6, 3), "t1": total,
                    "data": {"text": part_label or "CONTINUA…", "sub": ep.get("end_sub", "")}})
    sfx.append({"t": narration_end - 0.4, "kind": "ding", "variant": 1, "gain": 0.32})
    # ------------------------------------------------------------ colisões: etiqueta (chip) foge do que já está na tela
    def overlaps(w: dict[str, Any], kinds: set[str]) -> bool:
        return any(o is not w and o["type"] in kinds and o["t0"] < w["t1"] and o["t1"] > w["t0"] for o in widgets)
    for w in widgets:
        if w["type"] != "chip":
            continue
        if overlaps(w, {"objectives", "phone", "scoreboard", "inventory"}):
            w["data"]["y"] = 0.3 if overlaps(w, {"dialogue", "tv", "endcard"}) else (0.62 if not vertical else 0.84)
        elif overlaps(w, CENTER_WIDGETS) and not vertical:
            w["data"]["y"] = 0.85
    # ------------------------------------------------------------ relógio
    clock = _clock(ep, beats, L, hud, mission)
    if clock.get("countdown_min"):
        from ..render.story_hud import clk_minute
        for w in widgets:
            if w["type"] == "countdown" and not w["data"].get("value"):
                left = max(0, int(clock["countdown_min"] - clk_minute(clock, w["t0"])))
                w["data"]["value"] = f"{left // 60:02d}:{left % 60:02d}"
                w["data"].setdefault("label", "HORAS PELA FRENTE")
    # escurece o fundo quando um cartão central está na tela
    for sh in shots:
        cover = sum(max(0.0, min(sh["start"] + sh["dur"], w["t1"]) - max(sh["start"], w["t0"]))
                    for w in widgets if w["type"] in CENTER_WIDGETS)
        if cover > sh["dur"] * 0.5:
            sh["dim"] = max(sh.get("dim", 0.0), 0.3)
        if any(w["type"] == "dialogue" and w["t0"] < sh["start"] + sh["dur"] and w["t1"] > sh["start"] for w in widgets):
            sh["dim"] = max(sh.get("dim", 0.0), 0.18)
    mood = {"root": rng.choice([49.0, 55.0, 58.3, 61.7]), "drone_gain": rng.uniform(0.04, 0.06),
            "bed_gain": rng.uniform(0.45, 0.6), "tick": bool(clock.get("countdown_min")) and rng.random() < 0.6}
    hero = max(shots, key=lambda s: (s.get("hero", 0), s["dur"]))
    return {"W": W, "H": H, "fps": fps, "seed": seed, "duration": round(total, 3), "narration_end": round(narration_end, 3),
            "grade": hud.get("grade", ""), "hud": hud, "shots": shots, "widgets": widgets, "lines": L, "sfx": sfx,
            "ambience": amb, "clock": clock, "music": mood, "climax_at": climax, "fade_in": 0.0,
            "hero_t": round(hero["start"] + hero["dur"] * 0.6, 2)}


def _clock(ep: dict[str, Any], beats: list[dict[str, Any]], L: list[dict[str, Any]], hud: dict[str, Any],
           mission: dict[str, Any]) -> dict[str, Any]:
    c = ep.get("clock") or {}
    mode = c.get("mode") or hud.get("clock") or "date"
    start = _hm(c.get("start")) if mode in ("date", "lab") else 0
    start = start if start is not None else 6 * 60
    rate = {"date": 1.0, "lab": 1.0, "match": 0.5, "met": 1 / 60}.get(mode, 1.0)
    segs = []
    labels = []
    for b, ln in zip(beats, L):
        if isinstance(b.get("mission"), dict) and b["mission"].get("title"):
            labels.append({"t": ln["start"], "mission": str(b["mission"]["title"])[:22].upper()})
        tm = b.get("time")
        if tm is None:
            continue
        if mode in ("date", "lab"):
            v = _hm(tm)
            if v is None:
                continue
            m = v - start
            while m < 0:
                m += 1440
        else:
            try:
                m = float(str(tm).replace("'", "").strip()) if mode == "match" else _met(tm)
            except ValueError:
                continue
        segs.append({"t": ln["start"], "min": m, "rate": rate})
    if not segs or segs[0]["t"] > 0.01:
        segs.insert(0, {"t": 0.0, "min": 0.0 if mode in ("date", "lab") else (segs[0]["min"] if segs else 0.0), "rate": rate})
    for i in range(1, len(segs)):  # o relógio da história nunca volta
        prev = segs[i - 1]
        at = prev["min"] + (segs[i]["t"] - prev["t"]) * prev["rate"]
        if segs[i]["min"] < at:
            segs[i]["min"] = at
    segs[-1]["rate"] = 0.0 if mode in ("date", "lab") and len(segs) > 2 else segs[-1]["rate"]  # último trecho congela
    hours = mission.get("hours")
    cd = None
    try:
        cd = float(hours) * 60 if hours else (float(mission.get("minutes")) if mission.get("minutes") else None)
    except (TypeError, ValueError):
        cd = None
    return {"mode": mode, "label": c.get("label", ""), "day_labels": c.get("day_labels") or [], "start_min": start,
            "segments": segs, "countdown_min": cd, "countdown_from": 4.0, "mission": str(mission.get("title", "MISSÃO"))[:22].upper(),
            "minute_offset": float(c.get("minute", 0) or 0), "mission_labels": labels}


def _highlight_target(hl: dict[str, Any], v: dict[str, Any] | None, bible: dict[str, Any]) -> str | None:
    if not v:
        return None
    label = str(hl.get("label") or "").lower()
    chars = {c["id"]: c for c in bible.get("characters") or []}
    named = [cid for cid, c in chars.items() if c.get("name", "").lower().split()[-1] in label or cid in label]
    if v.get("mode") == "layered":
        ids = [c.get("id") for c in v.get("chars") or []]
        for cid in named:
            if cid in ids:
                return f"id:{cid}"
        return "char:0" if ids and not named and str(hl.get("target", "")).startswith("char") else None
    bg_char = (v.get("bg") or {}).get("char")
    if (v.get("bg") or {}).get("eyes") and bg_char and (bg_char in named or not named):
        return "face"
    return None


def _met(tm: Any) -> float:
    p = [float(x) for x in re.findall(r"\d+", str(tm))]
    if len(p) >= 3:
        return p[0] * 60 + p[1] + p[2] / 60
    if len(p) == 2:
        return p[0] * 60 + p[1]
    return p[0] if p else 0.0


def _framings(v: dict[str, Any], n: int, rng: random.Random) -> list[str]:
    has_face = bool((v.get("bg") or {}).get("eyes")) or any(c.get("eyes") for c in v.get("chars") or [])
    opts = ["wide"]
    pool = (["face", "medium", "detail", "pan"] if has_face else ["detail", "pan", "medium"])
    rng.shuffle(pool)
    return (opts + pool)[:n] if n > 1 else [rng.choice(["wide", "wide", "pan"] + (["medium"] if has_face else []))]


def _shot(v: dict[str, Any], framing: str, start: float, dur: float, W: int, H: int, rng: random.Random,
          beat: dict[str, Any], speaker: str, first_in_beat: bool) -> dict[str, Any]:
    bg = v["bg"]
    SW, SH, s = _stage(bg["file"], W, H)
    sh: dict[str, Any] = {"start": round(start, 3), "dur": round(dur, 3), "bg": {"file": bg["file"], "eyes": bg.get("eyes") if v.get("mode") != "layered" else None},
                          "fx": [f for f in (beat.get("fx") or []) if f in ALLOWED_FX], "impacts": [], "drift_zoom": rng.uniform(0.04, 0.08)}
    if beat.get("impact") and first_in_beat:
        sh["impacts"].append(0.05)
        if "flash" not in sh["fx"] and rng.random() < 0.4:
            sh["fx"].append("flash")
    cx, cy, z = SW / 2, SH / 2, 1.0
    chars = []
    if v.get("mode") == "layered":
        n = len(v.get("chars") or [])
        slots = {1: [0.5], 2: [0.3, 0.72], 3: [0.2, 0.5, 0.8]}.get(n, [0.5] * n)
        for j, c in enumerate(v.get("chars") or []):
            a = c["asset"]
            hfrac = float(c.get("h") or (0.6 if n == 1 else 0.52))
            x = float(c.get("x") or slots[j])
            ent = c.get("enter") or ("none" if not first_in_beat else rng.choice(["none", "none", "slide_l" if x < 0.5 else "slide_r", "pop"]))
            look = c.get("look") or ("right" if x < 0.45 and n > 1 else ("left" if x > 0.55 and n > 1 else ""))
            chars.append({"file": a["file"], "eyes": a.get("eyes"), "id": c.get("id", ""), "x": x, "y": float(c.get("y") or 0.97),
                          "h": hfrac, "flip": bool(c.get("flip")), "enter": ent, "t_in": 0.0, "look": look,
                          "talk": c.get("id") == speaker, "jumps": [0.1] if beat.get("impact") and first_in_beat else [],
                          "phase": rng.uniform(0, 3), "sway": rng.uniform(0, 3) * (W / 720)})
        sh["chars"] = chars
        sh["parallax"] = rng.uniform(0.55, 0.75)
    if bg.get("pan_ok", True) and SW > W * 1.25 and framing in ("wide", "pan"):
        # imagem mais larga que o quadro (ex.: quadrada num Short): passeia na horizontal
        d = (SW - W) * rng.uniform(0.5, 0.9) * rng.choice([-1, 1])
        sh["pan"] = [d, 0.0]
        sh["pan_ease"] = True
    elif framing == "pan":
        z = 1.25
        sh["pan"] = [rng.choice([-1, 1]) * W * 0.12, rng.choice([-1, 1]) * H * 0.06]
    if framing == "face":
        fx_ = _face(v, SW, SH, s, W, H)
        if fx_:
            cx, cy = fx_
            z = rng.uniform(1.6, 2.0)
            cy += H * 0.08 / z
    elif framing == "medium":
        fx_ = _face(v, SW, SH, s, W, H)
        if fx_:
            cx, cy = fx_[0], fx_[1] + H * 0.16
            z = rng.uniform(1.25, 1.45)
    elif framing == "detail":
        cx = SW * rng.uniform(0.25, 0.75)
        cy = SH * rng.uniform(0.45, 0.8)
        z = rng.uniform(1.5, 2.1)
    keys = [[0.0, cx, cy, z]]
    # punch-in no meio de uma tomada longa (corte rápido para plano fechado)
    if dur > 3.2 and framing == "wide" and rng.random() < 0.55:
        f = _face(v, SW, SH, s, W, H)
        if f:
            keys.append([round(dur * rng.uniform(0.5, 0.65), 2), f[0], f[1] + H * 0.05, rng.uniform(1.6, 1.9)])
            sh["impacts"].append(keys[-1][0])
    sh["cam"] = keys
    sh["hero"] = 2 if (framing in ("wide", "medium") and _face(v, SW, SH, s, W, H)) else (1 if framing == "wide" else 0)
    return sh


def _face(v: dict[str, Any], SW: float, SH: float, s: float, W: int = 720, H: int = 1280) -> tuple[float, float] | None:
    """Centro dos olhos no palco (px), para cena pronta ou para o 1º personagem em camadas."""
    if v.get("mode") != "layered":
        e = (v.get("bg") or {}).get("eyes")
        if e:
            (x0, y0), (x1, y1) = e["eyes"]
            return (x0 + x1) / 2 * s, (y0 + y1) / 2 * s
        return None
    for c in v.get("chars") or []:
        a = c["asset"]
        e = a.get("eyes")
        if not e:
            continue
        n = len(v.get("chars") or [])
        slots = {1: [0.5], 2: [0.3, 0.72], 3: [0.2, 0.5, 0.8]}.get(n, [0.5] * n)
        j = (v.get("chars") or []).index(c)
        hfrac = float(c.get("h") or (0.6 if n == 1 else 0.52))
        x = float(c.get("x") or slots[j])
        aw, ah = a["size"]
        hh = H * hfrac
        sc = hh / ah
        X, Y = SW / 2 + (x - 0.5) * W, SH / 2 + (float(c.get("y") or 0.97) - 0.5) * H
        (ex0, ey0), (ex1, ey1) = e["eyes"]
        ex = (ex0 + ex1) / 2
        ey = (ey0 + ey1) / 2
        if c.get("flip"):
            ex = aw - ex
        return X + (ex - aw / 2) * sc, Y - hh + ey * sc
    return None
