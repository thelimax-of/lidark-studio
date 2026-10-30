"""Diretor do motor vetorial: episódio (vetor_writer) + áudios das falas (engine.synth_lines) → spec do CONTRATO.md.

- 1 plano a cada 1,8–3 s em média, alternando aberto, close, detalhe e tela; cortes nas pausas da fala
- câmera sempre em movimento leve (nada de plano parado)
- legendas de 1 a 2 palavras, sincronizadas por timestamps quando existem, senão proporcional às sílabas
- carimbos, reações, placar (medidor, dia, inventário), SFX, ambiência e trilha
Tudo sorteado com a semente do episódio: reprodutível, mas cada vídeo tem abertura e sequência de planos próprias.
"""
from __future__ import annotations

import json
import random
import re
from typing import Any

from . import vetor_writer as VW

SET_W, SET_H = 720, 1280
CHAR_H = 620            # altura do boneco no contrato
FLOOR_Y = 1090
TAIL = 3.2              # tempo da tela de escolha depois da última fala
SCREEN_MAX = 3.4        # tela precisa de tempo de leitura, mas sem virar slide
SHOT_MAX = 3.0
SHOT_MIN = 1.0
STOP = {"a", "o", "as", "os", "e", "é", "de", "do", "da", "dos", "das", "no", "na", "nos", "nas", "em", "um", "uma", "uns", "umas",
        "que", "se", "por", "pra", "pro", "com", "ao", "à", "meu", "minha", "seu", "sua", "te", "me", "já", "não", "só", "mas"}
PATTERNS = (("wide", "close", "detail"), ("close", "wide", "detail", "close"), ("wide", "detail", "close", "close"),
            ("detail", "close", "wide"), ("close", "detail", "wide", "detail"))
REACT_BY_EXPR = {"scared": "sweat", "shock": "exclaim", "angry": "anger", "happy": "bulb", "sleepy": "zzz", "sad": "sweat"}
SLOTS_FLOOR = [(92, 1010), (628, 1010), (150, 960), (570, 960)]
SLOTS_WALL = [(120, 420), (600, 420), (360, 300), (140, 640), (580, 640), (360, 520)]
CAPTION = "#ffffff"
COLOR = {"yellow": "#ffd23f", "red": "#ff5a4d", "green": "#39d98a"}


# ================================================================ fala → palavras no tempo

def syllables(word: str) -> int:
    """Sílabas aproximadas (grupos de vogais); número falado leva mais tempo."""
    w = word.lower()
    if re.search(r"\d", w):
        return max(2, 2 * len(re.sub(r"\D", "", w)))
    return max(1, len(re.findall(r"[aeiouáéíóúâêôãõàüy]+", w)))


def word_times(ln: dict[str, Any]) -> list[dict[str, Any]]:
    """[{w, t0, t1, end}] da fala. Timestamps da voz (ln["words"]) mandam; sem eles, reparte a duração pelas sílabas e
    dá às pontuações o peso de uma pausa. end=True marca fim de frase/vírgula (ponto bom para o corte)."""
    if ln.get("words"):
        out = []
        for x in ln["words"]:
            w = str(x.get("w") or x.get("word") or "")
            out.append({"w": w, "t0": float(x.get("t0", x.get("start"))), "t1": float(x.get("t1", x.get("end"))), "end": bool(re.search(r"[.,!?…;:]$", w))})
        return out
    toks = str(ln.get("text") or "").split()
    if not toks:
        return []
    weights = [syllables(t) + (2.2 if re.search(r"[.!?…]$", t) else 1.2 if re.search(r"[,;:]$", t) else 0.0) for t in toks]
    k = float(ln["end"] - ln["start"]) / sum(weights)
    out, t = [], float(ln["start"])
    for tok, wt in zip(toks, weights):
        fala = syllables(tok) * k
        out.append({"w": tok, "t0": round(t, 3), "t1": round(t + fala, 3), "end": bool(re.search(r"[.,!?…;:]$", tok))})
        t += wt * k
    return out


def _bare(w: str) -> str:
    return re.sub(r"^[^\wÀ-ÿ%]+|[^\wÀ-ÿ%]+$", "", w)


def captions_for(words: list[dict[str, Any]], key: str, style: str) -> list[dict[str, Any]]:
    """Legendas de 1 a 2 palavras: palavrinha gruda na seguinte; a palavra de destaque fica sozinha e colorida."""
    keys = {VW._plain(k) for k in key.split()}
    out: list[dict[str, Any]] = []
    i = 0
    while i < len(words):
        a = _bare(words[i]["w"])
        grp = [words[i]]
        is_key = VW._plain(a) in keys
        if (a.lower() in STOP or len(a) <= 2) and not words[i]["end"] and i + 1 < len(words):
            b = _bare(words[i + 1]["w"])
            if len(a) + len(b) + 1 <= 15:
                grp.append(words[i + 1])
                is_key = is_key or VW._plain(b) in keys
        text = " ".join(_bare(g["w"]) for g in grp).upper()
        i += len(grp)
        if not text.strip():
            continue
        num = bool(re.search(r"\d", text))
        out.append({"t0": round(grp[0]["t0"], 3), "t1": round(words[i]["t0"] if i < len(words) else grp[-1]["t1"] + 0.12, 3), "text": text,
                    "color": COLOR.get(style, COLOR["yellow"]) if is_key else (COLOR["yellow"] if num else CAPTION)})
    return out


def _cut_points(b0: float, b1: float, n: int, words: list[dict[str, Any]]) -> list[float]:
    """Cortes internos do beat: alvo uniforme, puxado para a pausa da fala mais próxima (senão, início de palavra)."""
    pts = []
    pauses = [(w["t1"] + 0.03, w) for w in words if w["end"]]
    starts = [(w["t0"], w) for w in words]
    prev = b0
    for k in range(1, n):
        alvo = b0 + (b1 - b0) * k / n
        near = [p for p, _ in pauses if abs(p - alvo) < 0.55 and p - prev >= SHOT_MIN and b1 - p >= SHOT_MIN]
        if not near:
            near = [p for p, _ in starts if abs(p - alvo) < 0.4 and p - prev >= SHOT_MIN and b1 - p >= SHOT_MIN]
        c = min(near, key=lambda p: abs(p - alvo)) if near else alvo
        pts.append(round(c, 3))
        prev = c
    return pts


# ================================================================ câmera

def _clamp_cam(c: dict[str, float]) -> dict[str, float]:
    z = max(1.0, c["z"])
    hw, hh = SET_W / 2 / z, SET_H / 2 / z
    return {"x": round(min(SET_W - hw, max(hw, c["x"])), 1), "y": round(min(SET_H - hh, max(hh, c["y"])), 1), "z": round(z, 3)}


def _cam(kind: str, target: tuple[float, float] | None, rng: random.Random, tod: str, impact: bool) -> dict[str, Any]:
    """Toda câmera vai de um ponto a outro: aproxima, afasta ou desliza um pouco; só impacto sacode, e bem de leve."""
    if kind == "close" and target:
        z = rng.uniform(1.65, 2.05)
        a = {"x": target[0], "y": target[1] + 40, "z": z}
    elif kind == "detail" and target:
        z = rng.uniform(2.1, 2.6)
        a = {"x": target[0], "y": target[1], "z": z}
    else:
        a = {"x": SET_W / 2, "y": SET_H / 2, "z": rng.uniform(1.03, 1.08)}
    move = rng.choice(("push", "pull", "left", "right", "tilt"))
    b = dict(a)
    dz, d = rng.uniform(0.05, 0.12) * a["z"], rng.uniform(14, 30)
    if move == "push":
        b["z"] += dz
    elif move == "pull":
        a["z"] += dz
    elif move == "left":
        b["x"] -= d
        b["z"] += dz / 3
    elif move == "right":
        b["x"] += d
        b["z"] += dz / 3
    else:
        b["y"] += rng.choice((-1, 1)) * d
        b["z"] += dz / 3
    fr, to = _clamp_cam(a), _clamp_cam(b)
    if fr == to:  # preso na borda do cenário: garante movimento pelo zoom
        to["z"] = round(to["z"] + 0.05, 3)
        to = _clamp_cam(to)
    return {"from": fr, "to": to, "shake": 3 if impact else 0}


# ================================================================ encenação

class Stage:
    """Memória da encenação: o objeto que entrou num cenário fica onde está, e o elenco do beat ganha lugar fixo."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.props: dict[str, dict[str, dict[str, Any]]] = {}

    def place(self, st: str, pid: str, wall: bool = False, label: str = "") -> dict[str, Any]:
        room = self.props.setdefault(st, {})
        if pid not in room:
            pool = [p for p in (SLOTS_WALL if wall else SLOTS_FLOOR) if not any((x["x"], x["y"]) == p for x in room.values())]
            pool = pool or [p for p in SLOTS_FLOOR + SLOTS_WALL if not any((x["x"], x["y"]) == p for x in room.values())] or SLOTS_FLOOR
            x, y = self.rng.choice(pool)
            room[pid] = {"id": pid, "x": x, "y": y, "scale": round(self.rng.uniform(0.9, 1.25), 2), "state": {}}
        if label:
            room[pid]["label"] = label
        return room[pid]

    def in_room(self, st: str) -> list[dict[str, Any]]:
        return [dict(p) for p in list(self.props.get(st, {}).values())[-7:]]


def _cast(bt: dict[str, Any], states: dict[str, dict[str, Any]], rng: random.Random, enter: bool) -> list[dict[str, Any]]:
    n = len(bt.get("cast") or [])
    xs = {1: [360], 2: [235, 490], 3: [170, 360, 555]}.get(n, [])
    out = []
    for j, c in enumerate(bt.get("cast") or []):
        x = xs[j] + rng.randint(-18, 18)
        out.append({"char": c["char"], "x": x, "y": FLOOR_Y, "scale": 1 if n == 1 else 0.92, "pose": c.get("pose", "stand"), "expr": c.get("expr", "neutral"),
                    "hold": c.get("hold", ""), "flip": n > 1 and x > 360, "state": dict(states.get(c["char"]) or {}),
                    "enter": ("left" if x <= 360 else "right") if enter else "none"})
    return out


def _walking(sh: dict[str, Any], kind: str, way: int) -> None:
    """Quem anda ou corre sai do lugar, e a câmera acompanha: inteira no close, pela metade no plano aberto."""
    dur = sh["t1"] - sh["t0"]
    moved = 0.0
    for c in sh["cast"]:
        speed = WALK_SPEED.get(c.get("pose"))
        if speed:
            moved = min(speed * dur, 880.0) * c.get("scale", 1)
            c["move"] = [round(c["x"] - way * moved / 2), round(c["x"] + way * moved / 2)]
            c["enter"] = "none"
    if moved:
        follow = 1.0 if kind == "close" else 0.5
        cam = sh["cam"]
        mid = (cam["from"]["x"] + cam["to"]["x"]) / 2
        cam["from"] = _clamp_cam({**cam["from"], "x": mid - way * moved * follow / 2})
        cam["to"] = _clamp_cam({**cam["to"], "x": mid + way * moved * follow / 2})


def _focus(cast: list[dict[str, Any]], speaker: str) -> dict[str, Any] | None:
    return next((c for c in cast if c["char"] == speaker), cast[0] if cast else None)


def _face(c: dict[str, Any]) -> tuple[float, float]:
    return float(c["x"]), float(c["y"]) - CHAR_H * float(c["scale"]) * 0.86


def _feasible(bt: dict[str, Any], cast: list[dict[str, Any]], stage: Stage) -> list[str]:
    k = []
    if cast:
        k += ["wide", "close"]
    else:
        k += ["wide"]
    if bt.get("detail") or bt.get("gag") or stage.in_room(bt["set"]):
        k.append("detail")
    return k


def _shot_kinds(n: int, bt: dict[str, Any], feasible: list[str], walk: dict[str, Any], forced: str = "") -> list[str]:
    """Próximos n planos do padrão do episódio: nunca dois iguais em seguida se houver alternativa."""
    out: list[str] = []
    for k in range(n):
        if k == 0 and forced in feasible:
            out.append(forced)
            walk["last"] = forced
            continue
        for _ in range(len(walk["pat"]) + 1):
            c = walk["pat"][walk["i"] % len(walk["pat"])]
            walk["i"] += 1
            if c in feasible and (c != walk["last"] or len(feasible) == 1):
                out.append(c)
                walk["last"] = c
                break
        else:
            out.append(feasible[0])
            walk["last"] = feasible[0]
    return out


SHAKE_GAP = 12.0  # no máximo uma sacudida a cada 12 s
WALK_SPEED = {"walk": 250.0, "run": 520.0}  # px/s, perto do passo desenhado em chars.js
SCREEN_SFX = {"key": {"kind": "type", "gain": 0.3}, "tap": {"kind": "tick", "gain": 0.4}, "pop": {"kind": "notify", "gain": 0.16},
              "alert": {"kind": "beep", "gain": 0.2}, "shutter": {"kind": "tick", "gain": 0.6}}


def _transition(prev: dict[str, Any] | None, cur: dict[str, Any], bt: dict[str, Any], first_in_beat: bool, rng: random.Random) -> str:
    if prev is None:
        return "cut"
    if cur.get("screen") and not prev.get("screen"):
        return rng.choices(("slide", "cut", "glitch"), (5, 3, 1))[0]
    if prev.get("set") != cur.get("set"):
        return rng.choices(("whip", "iris", "slide", "flash"), (5, 2, 2, 1))[0]
    if bt.get("impact") and first_in_beat:
        return "flash"
    return "cut" if not first_in_beat else rng.choices(("cut", "whip"), (6, 1))[0]


def direct(ep: dict[str, Any], lines: list[dict[str, Any]], bible: dict[str, Any], *, W: int = 720, H: int = 1280, fps: int = 30, seed: int = 1,
           part_label: str = "") -> dict[str, Any]:
    """ep["beats"][i] ↔ lines[i] ({"audio", "dur", "speaker"}, opcional "words"). Devolve o spec do contrato."""
    rng = random.Random(seed)
    beats = ep["beats"]
    vt = ep.get("vetor") or {}
    start_state = vt.get("state_start") or VW.default_state(None)
    end_state = vt.get("state_end") or start_state
    picks = vt.get("picks") or {}
    # ------------------------------------------------------------ tempos das falas
    t = 0.12
    L: list[dict[str, Any]] = []
    for b, ln in zip(beats, lines):
        L.append({**ln, "start": round(t, 3), "end": round(t + float(ln["dur"]), 3), "speaker": b.get("speaker", "narrador"), "text": b.get("text", "")})
        t += float(ln["dur"]) + 0.12 + (0.22 if b.get("pause") else 0.0) + rng.uniform(0, 0.08)
    narration_end = L[-1]["end"]
    choice = _choice_block(ep)
    total = round(narration_end + (TAIL if choice else 2.0), 3)
    words = [word_times(ln) for ln in L]
    # ------------------------------------------------------------ planos
    stage = Stage(rng)
    walk: dict[str, Any] = {"pat": rng.choice(PATTERNS), "i": rng.randrange(4), "last": ""}
    target = rng.uniform(2.05, 2.6)
    states = {k: dict(v) for k, v in (start_state.get("chars") or {}).items()}
    shots: list[dict[str, Any]] = []
    opening = str(picks.get("opening") or "")
    last_set = ""
    last_shake = -SHAKE_GAP
    for i, (bt, ln) in enumerate(zip(beats, L)):
        for cid, cs in (bt.get("char_state") or {}).items():
            states.setdefault(cid, {}).update(cs)
        for p in bt.get("props") or []:
            stage.place(bt["set"], p)
        gag = bt.get("gag")
        if gag:
            stage.place(bt["set"], gag["prop"], wall=True, label=gag.get("label", ""))
        if bt.get("detail"):
            stage.place(bt["set"], bt["detail"])
        b0, b1 = (ln["start"] if i else 0.0), (L[i + 1]["start"] if i + 1 < len(L) else total)
        span = b1 - b0
        new_set = bt["set"] != last_set
        last_set = bt["set"]
        cast = _cast(bt, states, rng, new_set)
        scr = bt.get("screen")
        segments = _segments(b0, b1, span, scr, words[i], target, first=i == 0 and opening == "screen_first")
        feas = _feasible(bt, cast, stage)
        plain = [s for s in segments if not s[2]]
        forced = ""
        if i == 0:
            forced = {"close_first": "close", "detail_first": "detail", "wide_first": "wide"}.get(opening, "")
        kinds = iter(_shot_kinds(len(plain), bt, feas, walk, forced))
        way = rng.choice((-1, 1))
        for k, (s0, s1, is_scr) in enumerate(segments):
            kind = "screen" if is_scr else next(kinds)
            impact = bool(bt.get("impact")) and k == 0 and s0 - last_shake >= SHAKE_GAP
            if impact:
                last_shake = s0
            focus = _focus(cast, ln["speaker"])
            tgt = None
            if kind == "close" and focus:
                tgt = _face(focus)
            elif kind == "detail":
                pid = bt.get("detail") or (gag or {}).get("prop")
                room = stage.in_room(bt["set"])
                p = next((x for x in room if x["id"] == pid), rng.choice(room) if room else None)
                tgt = (float(p["x"]), float(p["y"])) if p else None
            cam = _cam(kind, tgt, rng, bt.get("tod", "day"), impact)
            sh = {"t0": round(s0, 3), "t1": round(s1, 3), "set": bt["set"], "tod": bt.get("tod", "day"), "set_state": dict(bt.get("set_state") or {}),
                  "cast": [] if kind == "detail" and (tgt or not focus) else [dict(c, enter=c["enter"] if k == 0 else "none") for c in cast],
                  "props": stage.in_room(bt["set"]), "fx": list(bt.get("fx") or []), "cam": cam,
                  "screen": {"type": scr["type"], "data": scr.get("data") or {}, "device": scr.get("device", "fullscreen"), "family": scr.get("family", "")} if is_scr else None,
                  "kind": kind, "beat": i}
            if kind in ("wide", "close"):
                _walking(sh, kind, way)
            sh["transition"] = _transition(shots[-1] if shots else None, sh, bt, k == 0, rng)
            shots.append(sh)
    # ------------------------------------------------------------ legendas, carimbos, reações, SFX
    captions, stamps, reactions, sfx, amb = _layers(beats, L, words, shots, rng, opening, total)
    climax = L[-1]["start"] if len(L) > 2 else None
    if climax:
        sfx.append({"t": round(max(0.0, climax - 1.3), 3), "kind": "riser", "variant": 0, "gain": 0.22})
    sfx.append({"t": 0.05, "kind": "riser", "variant": rng.randrange(2), "gain": 0.16})
    hud = _hud(beats, L, start_state, end_state, total)
    if choice:
        sfx.append({"t": round(narration_end + 0.1, 3), "kind": "impact", "variant": rng.randrange(3), "gain": 0.4})
        sfx.append({"t": round(narration_end + 0.5, 3), "kind": "ding", "variant": rng.randrange(4), "gain": 0.3})
    low = float(end_state.get("meter", {}).get("value", 100)) <= 25
    music = {"root": rng.choice([49.0, 55.0, 58.3, 61.7]), "drone_gain": rng.uniform(0.04, 0.06), "bed_gain": rng.uniform(0.42, 0.58),
             "tick": low or rng.random() < 0.3}
    spec = {"W": W, "H": H, "fps": fps, "duration": total, "seed": seed, "narration_end": round(narration_end, 3), "shots": shots, "captions": captions,
            "stamps": stamps, "reactions": reactions, "hud": hud, "lines": L, "sfx": sorted(sfx, key=lambda e: e["t"]), "ambience": amb, "music": music,
            "climax_at": climax, "end": {"choice": choice, "label": part_label or "CONTINUA…"}, "hero_t": _hero_t(shots)}
    return spec


def _segments(b0: float, b1: float, span: float, scr: dict[str, Any] | None, words: list[dict[str, Any]], target: float,
              *, first: bool = False) -> list[tuple[float, float, bool]]:
    """Fatia o beat em planos (início, fim, é_tela). Tela fica junto da fala que ela explica; o resto vira planos normais."""
    def plain(a: float, b: float) -> list[tuple[float, float, bool]]:
        length = b - a
        n = max(1, min(int(length // SHOT_MIN), max(round(length / target), -int(-length // SHOT_MAX))))
        wd = [w for w in words if a < w["t0"] < b]
        pts = [a] + _cut_points(a, b, n, wd) + [b]
        return [(pts[k], pts[k + 1], False) for k in range(len(pts) - 1)]
    if not scr:
        return plain(b0, b1)
    dur = min(span, SCREEN_MAX)
    if span - dur < SHOT_MIN:
        return [(b0, b1, True)] if span <= SCREEN_MAX + 0.4 else plain(b0, b1 - dur) + [(b1 - dur, b1, True)]
    if first or scr.get("device") != "hand":  # a tela abre antes da reação; na mão, o personagem pega o aparelho primeiro
        return [(b0, b0 + dur, True)] + plain(b0 + dur, b1)
    return plain(b0, b1 - dur) + [(b1 - dur, b1, True)]


def _shot_at(shots: list[dict[str, Any]], t: float) -> dict[str, Any] | None:
    return next((s for s in shots if s["t0"] <= t < s["t1"]), None)


def _layers(beats: list[dict[str, Any]], L: list[dict[str, Any]], words: list[list[dict[str, Any]]], shots: list[dict[str, Any]],
            rng: random.Random, opening: str, total: float) -> tuple[list, list, list, list, list]:
    captions: list[dict[str, Any]] = []
    stamps: list[dict[str, Any]] = []
    reacts: list[dict[str, Any]] = []
    sfx: list[dict[str, Any]] = []
    amb: list[dict[str, Any]] = []
    iv, wv = rng.randrange(3), rng.randrange(4)
    last_react = -9.0
    for i, (bt, ln, wd) in enumerate(zip(beats, L, words)):
        s0, s1 = ln["start"], ln["end"]
        nxt = L[i + 1]["start"] if i + 1 < len(L) else total
        key = bt.get("word", "")
        captions += captions_for(wd, key, bt.get("word_style", "yellow"))
        # carimbo: nasce quando a palavra é dita; em tela cheia ele atrapalharia a leitura, a legenda colorida basta
        at = next((w["t0"] for w in wd if VW._plain(_bare(w["w"])) in {VW._plain(k) for k in key.split()}), s0 + 0.25)
        sh = _shot_at(shots, at)
        if key and not (sh and sh.get("screen") and sh["screen"]["device"] == "fullscreen"):
            stamps.append({"t0": round(at, 3), "t1": round(min(at + 1.45, nxt), 3), "text": key, "x": rng.randint(230, 490), "y": rng.randint(230, 400),
                           "style": bt.get("word_style", "yellow")})
            st = bt.get("word_style")
            sfx.append({"t": round(at, 3), "kind": "impact" if st == "red" else "ding" if st == "green" else "whoosh", "variant": iv if st == "red" else wv,
                        "gain": 0.38 if st == "red" else 0.22})
        # reação: num plano com o personagem visível, no máximo uma a cada 2,5 s
        kind = bt.get("reaction")
        c0 = next((c for c in bt.get("cast") or [] if c["char"] == bt.get("speaker")), (bt.get("cast") or [None])[0])
        if c0 and not kind and rng.random() < 0.55:
            kind = REACT_BY_EXPR.get(c0.get("expr", ""))
        at_r = s0 + 0.2
        sh = _shot_at(shots, at_r)
        if kind and c0 and at_r - last_react >= 2.5 and sh and sh["kind"] in ("wide", "close"):
            reacts.append({"t0": round(at_r, 3), "t1": round(at_r + 1.2, 3), "kind": kind, "char": c0["char"]})
            last_react = at_r
        scr = bt.get("screen")
        if scr:
            sc = next((x for x in shots if x["beat"] == i and x.get("screen")), None)
            if sc:
                t0 = sc["t0"]
                fam = scr.get("family")
                if fam == "celular":
                    sfx.append({"t": round(t0 + 0.1, 3), "kind": "notify", "gain": 0.3})
                elif fam == "tv":
                    sfx.append({"t": round(t0 + 0.05, 3), "kind": "static", "gain": 0.2})
                else:
                    amb.append({"kind": "static", "t0": round(t0, 3), "t1": round(t0 + 0.8, 3)})
        if (bt.get("device") or {}).get("type") in ("radio", "comms"):
            amb.append({"kind": "crackle", "t0": s0, "t1": s1})
            sfx.append({"t": round(max(0.0, s0 - 0.2), 3), "kind": "beep", "gain": 0.2})
        if ln.get("silent"):
            k = ln.get("sfx") or "static"
            if k == "static":
                amb.append({"kind": "crackle", "t0": s0, "t1": s1})
                amb.append({"kind": "static", "t0": s0, "t1": round(s0 + 0.8, 3)})
            elif k == "alarm":
                sfx.append({"t": s0, "t1": s1, "kind": "alarm", "gain": 0.3})
            else:
                sfx.append({"t": round(s0 + 0.1, 3), "kind": k, "gain": 0.5})
        for f in bt.get("fx") or []:
            if f == "alarm":
                sfx.append({"t": s0, "t1": round(nxt, 3), "kind": "alarm", "gain": 0.14})
            elif f == "rain":
                amb.append({"kind": "rain", "t0": s0, "t1": round(nxt, 3)})
        if bt.get("crowd"):
            amb.append({"kind": "crowd", "t0": s0, "t1": round(nxt, 3)})
        if bt.get("impact"):
            sfx.append({"t": round(s0 + 0.02, 3), "kind": "impact", "variant": iv, "gain": 0.45})
        if bt.get("take"):
            sfx.append({"t": round(s0 + 0.8, 3), "kind": "ding", "variant": wv, "gain": 0.26})
    for a, b in zip(shots, shots[1:]):
        if b["transition"] in ("whip", "slide"):
            sfx.append({"t": round(max(0.0, b["t0"] - 0.18), 3), "kind": "whoosh", "variant": wv, "gain": 0.28})
        elif b["transition"] == "glitch":
            sfx.append({"t": b["t0"], "kind": "static", "gain": 0.3})
    if opening == "stamp_first" and stamps:  # abertura: a palavra do gancho já entra carimbada, antes da voz
        stamps[0]["t0"] = 0.08
        sfx.append({"t": 0.08, "kind": "impact", "variant": iv, "gain": 0.4})
    sfx += _screen_sounds(shots)
    return captions, stamps, reacts, sfx, amb


def _screen_sounds(shots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cada tecla, toque e alerta que a tela desenha vira som, no tempo em que aparece."""
    scr = [s for s in shots if s.get("screen")]
    out: list[dict[str, Any]] = []
    for sh, evs in zip(scr, VW.screen_timelines([(s["screen"]["type"], s["screen"]["data"]) for s in scr])):
        for e in evs:
            t = sh["t0"] + float(e.get("t") or 0)
            snd = SCREEN_SFX.get(e.get("kind"))
            if snd and t < sh["t1"]:
                out.append({"t": round(t, 3), **snd})
    return out


def _hud(beats: list[dict[str, Any]], L: list[dict[str, Any]], st0: dict[str, Any], st1: dict[str, Any], total: float) -> dict[str, Any]:
    m0, m1 = st0["meter"], st1.get("meter") or st0["meter"]
    keys = [[0, m0["value"]]]
    for bt, ln in zip(beats, L):
        if "meter" in bt and ln["end"] > keys[-1][0]:
            keys.append([ln["end"], bt["meter"]])
    keys.append([total, m1["value"]])
    meter = {"id": m0["id"], "label": m0["label"], "color": m0.get("color", "#39d98a"), "low": "#ff5a4d", "lowAt": 40, "keys": keys}
    inv = [{"t": 0, "item": i["item"], "label": i["label"]} for i in st0.get("inventory") or []]
    seen = {i["item"] for i in inv}
    for bt, ln in zip(beats, L):
        it = bt.get("take")
        if it and it["item"] not in seen:
            seen.add(it["item"])
            inv.append({"t": round(ln["start"] + 0.8, 3), "item": it["item"], "label": it["label"]})
    return {"meters": [meter], "counters": [{"id": "dia", "label": st1.get("day_label") or st0.get("day_label") or "DIA", "value": st1.get("day", st0.get("day", 1))}],
            "inventory": inv, "show": True}


def _choice_block(ep: dict[str, Any]) -> dict[str, Any] | None:
    """Escolha do fim: a do roteiro; em episódio sem ela, a decisão da série (opções já em palavras)."""
    c = (ep.get("vetor") or {}).get("choice")
    if c:
        return {k: c[k] for k in ("title", "a", "b") if k in c}
    d = ep.get("decision") if isinstance(ep.get("decision"), dict) else None
    opts = (d or {}).get("options") or {}
    if opts.get("A") and opts.get("B"):
        return {"title": "COMENTE UMA PALAVRA", "a": {"word": str(opts["A"]), "hint": ""}, "b": {"word": str(opts["B"]), "hint": ""}}
    return None


def _hero_t(shots: list[dict[str, Any]]) -> float:
    """Quadro da miniatura: close com expressão forte, longe da tela de escolha."""
    good = [s for s in shots[:-1] if s["kind"] in ("close", "wide") and s["cast"]] or shots
    best = max(good, key=lambda s: (s["kind"] == "close", any(c["expr"] in ("scared", "shock") for c in s["cast"]), s["t1"] - s["t0"]))
    return round((best["t0"] + best["t1"]) / 2, 2)


# ================================================================ verificação do spec

def validate(spec: dict[str, Any], cat: dict[str, Any] | None = None) -> list[str]:
    """Problemas do spec contra o contrato e as metas de ritmo (lista vazia = ok)."""
    bad: list[str] = []
    sh = spec["shots"]
    if abs(sh[0]["t0"]) > 1e-6 or abs(sh[-1]["t1"] - spec["duration"]) > 0.01:
        bad.append("planos não cobrem o vídeo inteiro")
    for a, b in zip(sh, sh[1:]):
        if abs(a["t1"] - b["t0"]) > 0.002:
            bad.append(f"buraco entre planos em {a['t1']}")
    avg = spec["duration"] / len(sh)
    if not 1.8 <= avg <= 3.0:
        bad.append(f"média de {avg:.2f} s por plano")
    for s in sh:
        if s["cam"]["from"] == s["cam"]["to"]:
            bad.append(f"câmera parada em {s['t0']}")
        if s["t1"] - s["t0"] > 3.9:
            bad.append(f"plano longo em {s['t0']}: {s['t1'] - s['t0']:.1f} s")
    rep = sum(1 for a, b in zip(sh, sh[1:]) if a["kind"] == b["kind"])
    if rep > len(sh) * 0.2:
        bad.append(f"{rep} planos repetem o tipo do anterior")
    scr = [s["screen"] for s in sh if s.get("screen")]
    if len(scr) < VW.MIN_SCREENS:
        bad.append(f"só {len(scr)} telas")
    fams = {s.get("family") for s in scr}
    if len(fams) < VW.MIN_FAMILIES:
        bad.append(f"só {len(fams)} famílias de telas: {fams}")
    for c in spec["captions"]:
        if len(c["text"].split()) > 2:
            bad.append(f"legenda longa: {c['text']}")
        if c["t1"] <= c["t0"]:
            bad.append(f"legenda sem duração: {c['text']}")
    for e in spec["sfx"]:
        if e["kind"] in ("typing", "alarm") and "t1" not in e:
            bad.append(f"{e['kind']} sem t1")
    if "highlight" in json.dumps(spec, ensure_ascii=False):
        bad.append("caixa highlight no spec")
    if cat:
        for s in sh:
            if s["set"] not in cat["sets"]:
                bad.append(f"cenário fora do catálogo: {s['set']}")
            for p in s["props"]:
                if p["id"] not in cat["props"]:
                    bad.append(f"objeto fora do catálogo: {p['id']}")
            if s.get("screen") and s["screen"]["type"] not in cat["screens"]:
                bad.append(f"tela fora do catálogo: {s['screen']['type']}")
    return sorted(set(bad))


# ================================================================ produção (chamada por engine.produce_story)

def produce(ch: Any, sc: Any, video_id: int, ctx: Any, b: dict[str, Any], ep: dict[str, Any]) -> dict[str, Any]:
    """Vídeo vetorial, sem nenhuma imagem gerada. Mesmo retorno de produce_story."""
    from ..config import MEDIA_DIR
    from ..render.vetor import engine as VE
    from .engine import synth_lines
    fmt = sc.format or "short"
    workdir = MEDIA_DIR / ch.slug / f"video_{video_id}"
    workdir.mkdir(parents=True, exist_ok=True)
    ctx.update(0.03, "Vozes do episódio")
    lines = synth_lines(ch, b, ep["beats"], workdir, (sc.variety or {}).get("voice_rate", ""))
    ctx.log(f"{len(lines)} falas ({sum(1 for x in lines if x['speaker'] != 'narrador')} de personagens), {sum(x['dur'] for x in lines):.1f}s")
    ep_no = int(sc.id or 0)
    part = int(ep.get("part") or 1)
    label = ep.get("end_label") or f"PARTE {part} · CONTINUA…"
    if fmt != "short":
        ctx.log("Motor vetorial desenha só 9:16: a versão longa sai vertical")
    spec = direct(ep, lines, b, seed=ep_no * 31 + part, part_label=label)
    for p in validate(spec, VW.catalog()):
        ctx.log(f"Spec vetorial: {p}")
    (workdir / "story_spec.json").write_text(json.dumps(spec, ensure_ascii=False, default=str), encoding="utf-8")
    ctx.update(0.15, f"Desenhando {len(spec['shots'])} planos")
    out = workdir / f"{ch.slug}_{video_id}.mp4"
    music_bed = None
    try:
        from .. import music
        music_bed = music.ambient_track(spec["duration"] + 1, seed=ep_no, mood=(sc.variety or {}).get("music_mood") or "suspense dark")
    except Exception as e:  # noqa: BLE001
        ctx.log(f"Trilha base indisponível ({e}) — só o drone")
    r = VE.render(spec, out, workdir / "render", progress=lambda p: ctx.update(0.15 + 0.8 * p), check=ctx.check, music_bed=music_bed)
    ctx.log(f"Render: {r['frames']} quadros em {r['seconds']}s · {r['loudness'].get('measured_lufs')} → -14 LUFS")
    thumb = _thumbnail(VE, spec, ep.get("thumbnail_text") or sc.title, workdir / "thumb.jpg")
    assets = {
        "template": "historia", "duration": spec["duration"], "narration_end": spec["narration_end"], "images": [],
        "scenes": [{"start": ln["start"], "end": ln["end"], "text": ln["text"], "visual": "vetor"} for ln in spec["lines"]],
        "story": {"shots": len(spec["shots"]), "new_images": 0, "reused": 0, "widgets": sorted({s["screen"]["type"] for s in spec["shots"] if s.get("screen")}),
                  "part": part, "missing": [], "render_seconds": r["seconds"], "render_style": "vetor"},
        "audio": {"loudness": r["loudness"]}, "loop": False, "opening_type": ((ep.get("vetor") or {}).get("picks") or {}).get("opening"), "chapters": [],
    }
    (workdir / "assets.json").write_text(json.dumps(assets, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"path": str(out.relative_to(MEDIA_DIR)), "thumbnail": str(thumb.relative_to(MEDIA_DIR)), "duration": spec["duration"], "assets": assets}


def _thumbnail(VE: Any, spec: dict[str, Any], text: str, path: Any) -> Any:
    """Miniatura do próprio motor: o quadro forte, sem legenda nem placar, com o texto como carimbo grande."""
    t = float(spec["hero_t"])
    s2 = {**spec, "captions": [], "reactions": [], "hud": {**spec["hud"], "show": False},
          "stamps": [{"t0": t - 2, "t1": t + 2, "text": str(text).upper()[:28], "x": 360, "y": 240, "style": "yellow"}]}
    im = VE.still(s2, t).convert("RGB")
    im.resize((1080, 1920)).save(path, quality=92)
    return path
