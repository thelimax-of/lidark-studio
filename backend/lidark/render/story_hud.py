"""Biblioteca de widgets de HUD do Modo História (estilo jogo), configurável por série e variada por episódio.

Cada widget desenha num "cartão" pequeno (RGBA do tamanho do widget, cacheado quando é estático) que entra no quadro
com alfa/deslocamento — rápido o bastante para 30 fps em CPU.

Estilos de série (hud["style"]): historia (papel/jornal de época), espaco (console de missão), futebol (rádio/placar),
laboratorio (caderno/ensaio). Cada widget usa as cores/fontes do HUD da série.

Widgets: clock (relógio da história + cronômetro da missão), mission, objectives, newspaper, telegram, console,
notebook, radio, scoreboard, tv, phone, chat, map, inventory, alert, countdown, chip, highlight, dialogue, endcard.
"""
from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .core import FONTS


# ================================================================ util

def ease(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def back(x: float) -> float:
    """Ease com leve passada do ponto (pop)."""
    x = max(0.0, min(1.0, x))
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def rgb(h: Any, a: int | None = None) -> tuple:
    if isinstance(h, (list, tuple)):
        t = tuple(int(v) for v in h)
    else:
        h = str(h).lstrip("#")
        t = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    if a is not None:
        return t[:3] + (int(a),)
    return t


@lru_cache(maxsize=256)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    for n in (name, "ChakraPetch-Bold.ttf", "Anton-Regular.ttf"):
        try:
            return ImageFont.truetype(str(FONTS / n), max(8, int(size)))
        except OSError:
            continue
    return ImageFont.load_default()


def fit(text: str, name: str, max_w: float, size: int, min_size: int = 12) -> ImageFont.FreeTypeFont:
    s = size
    while s > min_size:
        f = font(name, s)
        if f.getlength(text) <= max_w:
            return f
        s -= 2
    return font(name, min_size)


def wrap(text: str, f: ImageFont.FreeTypeFont, max_w: float) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if f.getlength(t) > max_w and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def fade(card: Image.Image, a: float) -> Image.Image:
    if a >= 0.999:
        return card
    c = card.copy()
    c.putalpha(c.getchannel("A").point(lambda v, a=a: int(v * a)))
    return c


def shadowed(card: Image.Image, blur: int = 12, alpha: float = 0.55, off: tuple[int, int] = (8, 12)) -> Image.Image:
    pad = blur * 2
    out = Image.new("RGBA", (card.width + pad * 2 + abs(off[0]), card.height + pad * 2 + abs(off[1])), (0, 0, 0, 0))
    sh = Image.new("RGBA", card.size, (0, 0, 0, 255))
    sh.putalpha(card.getchannel("A").point(lambda v: int(v * alpha)))
    out.alpha_composite(sh, (pad + off[0], pad + off[1]))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(card, (pad, pad))
    return out


class Hud:
    """Contexto de desenho: tamanho do quadro, escala (u = 1 em 720 px de largura útil) e tema da série."""

    def __init__(self, W: int, H: int, hud: dict[str, Any]) -> None:
        self.W, self.H = W, H
        self.vertical = H > W
        self.u = (W if self.vertical else H * 0.5625 * 1.25) / 720
        self.t = hud
        self.accent = rgb(hud.get("accent", "#f2ba40"))
        self.panel = rgb(hud.get("panel", [14, 13, 12, 220]))
        if len(self.panel) == 3:
            self.panel = self.panel + (220,)
        self.text = rgb(hud.get("text", "#ebe6dc"))
        self.danger = rgb(hud.get("danger", "#d63a30"))
        self.paper = rgb(hud.get("paper", "#ece2cc"))
        self.ink = (20, 18, 16)
        self.f_title = hud.get("font_title", "Anton-Regular.ttf")
        self.f_ui = hud.get("font_ui", "ChakraPetch-Bold.ttf")
        self.f_type = hud.get("font_type", "SpecialElite.ttf")
        self.f_paper = hud.get("font_paper", "PlayfairDisplay.ttf")
        self.style = hud.get("style", "historia")
        self._cache: dict[Any, Image.Image] = {}

    def s(self, v: float) -> int:
        return int(round(v * self.u))

    def F(self, which: str, size: float) -> ImageFont.FreeTypeFont:
        return font({"title": self.f_title, "ui": self.f_ui, "type": self.f_type, "paper": self.f_paper}.get(which, which),
                    self.s(size))

    def cached(self, key: Any, fn) -> Image.Image:
        c = self._cache.get(key)
        if c is None:
            if len(self._cache) > 300:
                self._cache.clear()
            c = self._cache[key] = fn()
        return c

    def put(self, base: Image.Image, card: Image.Image, x: float, y: float, a: float = 1.0) -> None:
        if a <= 0.01:
            return
        base.alpha_composite(fade(card, a), (int(x), int(y)))


# ================================================================ ícones desenhados (fontes não têm ◷ ◎)

def icon(d: ImageDraw.ImageDraw, kind: str, x: float, y: float, r: float, color: tuple) -> None:
    if kind == "clock":
        d.ellipse((x - r, y - r, x + r, y + r), outline=color, width=max(2, int(r / 4)))
        d.line((x, y, x, y - r * 0.6), fill=color, width=max(2, int(r / 5)))
        d.line((x, y, x + r * 0.45, y), fill=color, width=max(2, int(r / 5)))
    elif kind == "target":
        d.ellipse((x - r, y - r, x + r, y + r), outline=color, width=max(2, int(r / 4)))
        d.ellipse((x - r * 0.35, y - r * 0.35, x + r * 0.35, y + r * 0.35), fill=color)
    elif kind == "dot":
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    elif kind == "warn":
        d.polygon([(x, y - r), (x + r, y + r * 0.8), (x - r, y + r * 0.8)], fill=color)
    elif kind == "check":
        d.line([(x - r * 0.7, y), (x - r * 0.15, y + r * 0.6), (x + r * 0.8, y - r * 0.6)], fill=color, width=max(3, int(r / 3)))
    elif kind == "pin":
        d.ellipse((x - r, y - r * 1.6, x + r, y + r * 0.4), fill=color)
        d.polygon([(x - r * 0.7, y - r * 0.2), (x + r * 0.7, y - r * 0.2), (x, y + r * 1.4)], fill=color)
        d.ellipse((x - r * 0.4, y - r * 1.0, x + r * 0.4, y - r * 0.2), fill=(255, 255, 255))


# ================================================================ relógio + cronômetro (persistente)

def clock(h: Hud, base: Image.Image, now: float, clk: dict[str, Any]) -> None:
    """Relógio da história (data/hora, T+ da missão, minuto do jogo, hora do experimento) e o cronômetro da missão
    — sempre coerentes: o cronômetro é o total da missão menos o tempo de história que passou."""
    if not clk:
        return
    minute = clk_minute(clk, now)
    mode = clk.get("mode", "date")
    if mode == "match":
        mm = max(0, int(minute))
        half = "1º TEMPO" if mm < 45 else "2º TEMPO"
        main = f"{half}  {min(mm, 90 + 9):02d}'"
    elif mode == "met":
        tot = int(minute * 60)
        main = f"T+ {tot // 3600:02d}:{(tot // 60) % 60:02d}:{tot % 60:02d}"
    else:
        tod = int(clk.get("start_min", 360) + minute)
        day_off, tod = divmod(tod, 1440)
        labels = clk.get("day_labels") or []
        lab = labels[min(day_off, len(labels) - 1)] if labels else clk.get("label", "")
        main = f"{lab}  {tod // 60:02d}:{tod % 60:02d}".strip()
    f = h.F("ui", 18)
    key = ("clock", main)

    def card1() -> Image.Image:
        w = int(f.getlength(main)) + h.s(58)
        c = Image.new("RGBA", (w, h.s(40)), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, w - 1, c.height - 1), h.s(10), fill=h.panel)
        icon(d, "clock", h.s(20), c.height / 2, h.s(8), h.accent)
        d.text((h.s(36), c.height / 2), main, font=f, fill=h.accent, anchor="lm")
        return c
    x0, y0 = h.s(24), h.s(28) if h.vertical else h.s(22)
    h.put(base, h.cached(key, card1), x0, y0)
    tot = clk.get("countdown_min")
    if tot and now >= float(clk.get("countdown_from", 4.0)):
        left = max(0, int(tot - minute))
        mis = clk.get("mission", "MISSÃO")
        for lb in clk.get("mission_labels") or []:  # longo: o rótulo acompanha a missão do capítulo
            if lb["t"] <= now:
                mis = lb["mission"]
        txt = f"{mis}   {left // 60:02d}:{left % 60:02d}" if tot >= 120 else f"{mis}   {left:02d} MIN"
        a = ease((now - float(clk.get("countdown_from", 4.0))) / 0.4)

        def card2() -> Image.Image:
            w = int(f.getlength(txt)) + h.s(58)
            c = Image.new("RGBA", (w, h.s(40)), (0, 0, 0, 0))
            d = ImageDraw.Draw(c)
            low = left < tot * 0.15
            d.rounded_rectangle((0, 0, w - 1, c.height - 1), h.s(10), fill=h.panel,
                                outline=h.danger if low else None, width=h.s(2))
            icon(d, "target", h.s(20), c.height / 2, h.s(8), h.danger if low else h.text)
            d.text((h.s(36), c.height / 2), txt, font=f, fill=h.text, anchor="lm")
            return c
        h.put(base, h.cached(("cd", txt), card2), x0, y0 + h.s(46), a)


def clk_minute(clk: dict[str, Any], now: float) -> float:
    """Minutos de história passados no instante `now` (segmentos por cena: [{t, min, rate}])."""
    segs = clk.get("segments") or [{"t": 0.0, "min": 0.0, "rate": clk.get("rate", 1.0)}]
    cur = segs[0]
    for sg in segs:
        if sg["t"] <= now:
            cur = sg
    return float(cur["min"]) + max(0.0, now - float(cur["t"])) * float(cur.get("rate", 1.0))


# ================================================================ cartões grandes

def _big_panel(h: Hud, w: int, hgt: int, outline: tuple | None = None, fill: tuple | None = None) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    c = Image.new("RGBA", (w, hgt), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, w - 1, hgt - 1), h.s(18), fill=fill or (h.panel[:3] + (238,)), outline=outline or h.accent,
                        width=h.s(3))
    return c, d


def mission(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    a = ease((lt - 0.15) / 0.4) * (1 - ease((lt - (dur - 0.45)) / 0.4))
    if a <= 0:
        return
    title = str(data.get("title") or "NOVA MISSÃO").upper()
    sub = str(data.get("subtitle") or "")
    lab = str(data.get("label") or "MISSÃO PRINCIPAL").upper()

    def card() -> Image.Image:
        W = h.W - h.s(140) if h.vertical else int(h.W * 0.42)
        tag_f = h.F("ui", 18)
        tw = int(tag_f.getlength("NOVA MISSÃO")) + h.s(70)
        c = Image.new("RGBA", (W, h.s(300)), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        x0 = (W - tw) // 2
        d.rounded_rectangle((x0, 0, x0 + tw, h.s(42)), h.s(20), fill=h.panel[:3] + (235,), outline=h.accent, width=h.s(2))
        icon(d, "dot", x0 + h.s(24), h.s(21), h.s(6), h.accent)
        d.text((x0 + h.s(38), h.s(21)), "NOVA MISSÃO", font=tag_f, fill=h.accent, anchor="lm")
        p, pd = _big_panel(h, W, h.s(230))
        pd.text((W // 2, h.s(36)), lab, font=h.F("ui", 18), fill=h.text[:3] + (200,), anchor="mm")
        ft = fit(title, h.f_title, W - h.s(60), h.s(64), h.s(28))
        pd.text((W // 2, h.s(100)), title, font=ft, fill=h.accent, anchor="mm")
        if sub:
            fs = fit(sub, h.f_ui, W - h.s(120), h.s(22), h.s(14))
            sw = fs.getlength(sub)
            bx = (W - sw) / 2 - h.s(18)
            pd.rectangle((bx - h.s(8), h.s(160), bx + h.s(12), h.s(180)), outline=h.text, width=h.s(3))
            pd.text((bx + h.s(24), h.s(170)), sub, font=fs, fill=h.text, anchor="lm")
        c.alpha_composite(p, (0, h.s(56)))
        return shadowed(c)
    cd = h.cached(("mission", title, sub, lab), card)
    y = (h.H * 0.56 if h.vertical else h.H * 0.3) + (1 - a) * h.s(40)
    h.put(base, cd, (h.W - cd.width) / 2, y, a)


def objectives(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    items = [i if isinstance(i, dict) else {"text": str(i)} for i in (data.get("items") or [])][:4]
    if not items:
        return
    a = ease((lt - 0.1) / 0.35) * (1 - ease((lt - (dur - 0.35)) / 0.3))
    if a <= 0:
        return
    f = h.F("ui", 19)
    W = h.s(430)
    rows = []
    for it in items:
        done_at = it.get("done_at")
        done = done_at is not None and lt >= float(done_at)
        k = ease((lt - float(done_at)) / 0.25) if done_at is not None else 0
        rows.append((str(it.get("text", ""))[:42], done, k))
    key = ("obj", tuple((r[0], r[1], round(r[2], 1)) for r in rows))

    def card() -> Image.Image:
        hh = h.s(52) + len(rows) * h.s(42)
        c = Image.new("RGBA", (W, hh), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, W - 1, hh - 1), h.s(14), fill=h.panel)
        d.text((h.s(18), h.s(26)), "OBJETIVOS", font=h.F("ui", 16), fill=h.accent, anchor="lm")
        for i, (txt, done, k) in enumerate(rows):
            y = h.s(52) + i * h.s(42) + h.s(18)
            bx = h.s(18)
            d.rectangle((bx, y - h.s(11), bx + h.s(22), y + h.s(11)), outline=h.accent if done else h.text, width=h.s(3))
            if done:
                icon(d, "check", bx + h.s(11), y, h.s(11) * (0.6 + 0.4 * k), h.accent)
            col = h.text[:3] + ((140,) if done else (255,))
            d.text((bx + h.s(36), y), txt, font=fit(txt, h.f_ui, W - h.s(70), h.s(19), h.s(13)), fill=col, anchor="lm")
            if done:
                tw = f.getlength(txt) * k
                d.line((bx + h.s(36), y, bx + h.s(36) + min(tw, W - h.s(70)), y), fill=h.text[:3] + (170,), width=h.s(2))
        return c
    cd = h.cached(key, card)
    x = h.s(24) - (1 - a) * h.s(60)
    y = h.s(130) if h.vertical else h.s(120)
    h.put(base, cd, x, y, a)


def _paper_texture(c: Image.Image, step: int = 3) -> None:
    d = ImageDraw.Draw(c)
    for i in range(0, c.height, step):
        d.line((0, i, c.width, i), fill=(0, 0, 0, 10 if i % (step * 2) else 0))


def newspaper(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    a = ease((lt - 0.2) / 0.35)
    if a <= 0:
        return
    out = 1 - ease((lt - (dur - 0.3)) / 0.3)
    name = str(data.get("name") or "GAZETA")
    date = str(data.get("date") or "")
    h1 = str(data.get("headline") or data.get("headline1") or "").upper()
    h2 = str(data.get("headline2") or "").upper()
    sub = str(data.get("sub") or "")

    def card() -> Image.Image:
        pw, ph = h.s(560), h.s(420)
        p = Image.new("RGBA", (pw, ph), h.paper + (255,))
        d = ImageDraw.Draw(p)
        d.text((pw // 2, h.s(40)), name.upper(), font=fit(name.upper(), h.f_paper, pw - h.s(50), h.s(32)), fill=h.ink, anchor="mm")
        d.line((h.s(24), h.s(68), pw - h.s(24), h.s(68)), fill=h.ink, width=h.s(3))
        if date:
            d.text((pw // 2, h.s(86)), date, font=h.F("ui", 16), fill=(90, 80, 70), anchor="mm")
        y = h.s(160)
        for i, line in enumerate([x for x in (h1, h2) if x]):
            fh = fit(line, h.f_title, pw - h.s(50), h.s(66), h.s(28))
            d.text((pw // 2, y), line, font=fh, fill=h.danger if i == 1 else h.ink, anchor="mm")
            y += h.s(70)
        d.line((h.s(24), y - h.s(16), pw - h.s(24), y - h.s(16)), fill=h.ink, width=h.s(2))
        if sub:
            fs = font(h.f_paper, h.s(25))
            lines = wrap(sub, fs, pw - h.s(70))[:3]
            d.multiline_text((pw // 2, y + h.s(40)), "\n".join(lines), font=fs, fill=h.ink, anchor="mm", align="center",
                             spacing=h.s(6))
        _paper_texture(p)
        return p
    p = h.cached(("paper", name, h1, h2, sub, date), card)
    q = round(a * 12) / 12  # estados da animação quantizados → cache (rotacionar + sombra a cada quadro é caro)

    def posed() -> Image.Image:
        ang = (1 - q) * -14 + 3
        s = 0.6 + 0.4 * q
        r = p.rotate(ang, expand=True, resample=Image.BICUBIC)
        r = r.resize((max(1, int(r.width * s)), max(1, int(r.height * s))), Image.BILINEAR)
        return shadowed(r, blur=10)
    r = h.cached(("paperfx", name, h1, h2, sub, date, q), posed)
    h.put(base, r, (h.W - r.width) / 2, (h.H * 0.5 if h.vertical else h.H * 0.5) - r.height / 2, out)


def telegram(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    """Telegrama/bilhete de época: tira de papel com texto datilografado aparecendo."""
    a = ease((lt - 0.15) / 0.3) * (1 - ease((lt - (dur - 0.3)) / 0.3))
    if a <= 0:
        return
    txt = str(data.get("text") or "").upper()
    n = int(len(txt) * min(1.0, lt / max(0.4, min(2.8, dur * 0.6))))
    fw = font(h.f_type, h.s(26))
    W = h.s(560)
    lines = wrap(txt, fw, W - h.s(60))[:5]
    shown, left = [], n
    for ln in lines:
        shown.append(ln[:max(0, left)])
        left -= len(ln) + 1
    c = Image.new("RGBA", (W, h.s(70) + len(lines) * h.s(38)), h.paper + (255,))
    d = ImageDraw.Draw(c)
    d.text((h.s(24), h.s(26)), str(data.get("header") or "TELEGRAMA"), font=h.F("ui", 16), fill=(120, 100, 80), anchor="lm")
    for i, ln in enumerate(shown):
        d.text((h.s(28), h.s(56) + i * h.s(38)), ln, font=fw, fill=h.ink)
    _paper_texture(c)
    c = shadowed(c.rotate(-2, expand=True, resample=Image.BICUBIC), blur=8)
    h.put(base, c, (h.W - c.width) / 2, h.H * 0.42 + (1 - a) * h.s(30), a)


def console(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    """Console de missão (espaço): linhas de telemetria digitando, cursor, barra de status."""
    a = ease((lt - 0.1) / 0.3) * (1 - ease((lt - (dur - 0.3)) / 0.3))
    if a <= 0:
        return
    lines = [str(x).upper() for x in (data.get("lines") or [])][:6]
    W, fw = h.s(600), font("ChakraPetch-Bold.ttf", h.s(21))
    c = Image.new("RGBA", (W, h.s(80) + len(lines) * h.s(36)), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, W - 1, c.height - 1), h.s(12), fill=(4, 12, 24, 235), outline=h.accent, width=h.s(2))
    d.text((h.s(20), h.s(28)), str(data.get("title") or "CONTROLE DE MISSÃO").upper(), font=h.F("ui", 17), fill=h.accent, anchor="lm")
    for k in range(0, W, h.s(6)):
        d.point((k, h.s(50)), fill=h.accent)
    per = max(0.25, min(0.8, (dur - 0.8) / max(1, len(lines))))
    for i, ln in enumerate(lines):
        k = (lt - 0.3 - i * per) / per
        if k <= 0:
            break
        s = ln[:int(len(ln) * min(1, k * 1.4))]
        col = h.danger if any(w in ln for w in ("ALERTA", "FALHA", "PERIGO", "!")) else (180, 230, 255)
        d.text((h.s(20), h.s(62) + i * h.s(36)), "> " + s, font=fw, fill=col)
    h.put(base, c, (h.W - W) / 2, h.H * (0.5 if h.vertical else 0.45), a)


def notebook(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    """Caderno de laboratório: folha quadriculada, título, anotações escritas uma a uma, círculo no resultado."""
    a = ease((lt - 0.1) / 0.3) * (1 - ease((lt - (dur - 0.3)) / 0.3))
    if a <= 0:
        return
    lines = [str(x) for x in (data.get("lines") or [])][:5]
    W = h.s(560)
    hh = h.s(110) + len(lines) * h.s(46)
    c = Image.new("RGBA", (W, hh), (251, 251, 243, 255))
    d = ImageDraw.Draw(c)
    for x in range(0, W, h.s(24)):
        d.line((x, 0, x, hh), fill=(200, 225, 235, 255))
    for y in range(0, hh, h.s(24)):
        d.line((0, y, W, y), fill=(200, 225, 235, 255))
    d.line((h.s(60), 0, h.s(60), hh), fill=(240, 120, 110, 255), width=h.s(2))
    d.text((h.s(78), h.s(46)), str(data.get("title") or "EXPERIMENTO"), font=font(h.f_title, h.s(34)), fill=(31, 59, 77))
    per = max(0.3, (dur - 1.0) / max(1, len(lines)))
    fh = font("SpecialElite.ttf", h.s(26))
    for i, ln in enumerate(lines):
        k = (lt - 0.4 - i * per) / 0.4
        if k <= 0:
            break
        d.text((h.s(78), h.s(98) + i * h.s(46)), ln[:int(len(ln) * min(1, k))], font=fh, fill=(40, 50, 70))
    c = shadowed(c.rotate(1.5, expand=True, resample=Image.BICUBIC), blur=8)
    h.put(base, c, (h.W - c.width) / 2, h.H * 0.45 + (1 - a) * h.s(40), a)


def radio(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    """Transmissão de rádio (futebol): rádio antigo com 'AO VIVO', dial e ondas no ritmo da fala."""
    a = ease((lt - 0.1) / 0.3) * (1 - ease((lt - (dur - 0.3)) / 0.3))
    if a <= 0:
        return
    W, Hh = h.s(520), h.s(170)
    c = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, W - 1, Hh - 1), h.s(22), fill=(92, 52, 30, 245), outline=(40, 22, 12, 255), width=h.s(4))
    d.rounded_rectangle((h.s(18), h.s(18), W - h.s(160), Hh - h.s(18)), h.s(10), fill=(240, 222, 170, 255))
    for i in range(10):
        x = h.s(34) + i * (W - h.s(210)) / 9
        d.line((x, h.s(30), x, h.s(46 if i % 2 else 54)), fill=(60, 40, 20), width=h.s(2))
    nx = h.s(34) + (W - h.s(210)) * (0.5 + 0.08 * math.sin(lt * 0.7))
    d.line((nx, h.s(26), nx, Hh - h.s(30)), fill=h.danger, width=h.s(3))
    st = str(data.get("station") or "RÁDIO")
    d.text((h.s(34), Hh - h.s(46)), st.upper()[:22], font=h.F("ui", 18), fill=(60, 40, 20), anchor="lm")
    cx, cy = W - h.s(80), Hh // 2
    d.ellipse((cx - h.s(50), cy - h.s(50), cx + h.s(50), cy + h.s(50)), fill=(50, 30, 18), outline=(30, 16, 8), width=h.s(3))
    for i in range(9):
        amp = h.s(8 + 26 * abs(math.sin(lt * 8 + i * 0.9)))
        bx = cx - h.s(36) + i * h.s(9)
        d.rectangle((bx, cy - amp / 2, bx + h.s(4), cy + amp / 2), fill=h.accent)
    if int(lt * 2) % 2 == 0:
        d.rounded_rectangle((W - h.s(150), h.s(10), W - h.s(30), h.s(40)), h.s(8), fill=h.danger)
        d.text((W - h.s(90), h.s(25)), "AO VIVO", font=h.F("ui", 16), fill=(255, 255, 255), anchor="mm")
    h.put(base, shadowed(c, blur=8), (h.W - W) / 2 - h.s(20), h.H * (0.16 if h.vertical else 0.62) + (1 - a) * h.s(-30), a)


def scoreboard(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    a = ease((lt - 0.05) / 0.3)
    if a <= 0:
        return
    home, away = str(data.get("home") or "CASA")[:12].upper(), str(data.get("away") or "FORA")[:12].upper()
    sh, sa = data.get("score_home", 0), data.get("score_away", 0)
    change_at = data.get("change_at")
    if change_at is not None and lt < float(change_at):
        sh, sa = data.get("prev_home", sh), data.get("prev_away", sa)
    flash = change_at is not None and 0 <= lt - float(change_at) < 0.8 and int(lt * 8) % 2 == 0
    key = ("score", home, away, sh, sa, flash)

    def card() -> Image.Image:
        f = h.F("ui", 24)
        fs = h.F("title", 38)
        wh, wa = f.getlength(home), f.getlength(away)
        W = int(wh + wa + h.s(210))
        c = Image.new("RGBA", (W, h.s(64)), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, W - 1, h.s(63)), h.s(10), fill=(20, 20, 18, 235))
        d.text((h.s(18), h.s(32)), home, font=f, fill=h.text, anchor="lm")
        mid = h.s(18) + wh + h.s(20)
        d.rounded_rectangle((mid, h.s(6), mid + h.s(130), h.s(58)), h.s(8), fill=h.accent if flash else (245, 240, 225))
        d.text((mid + h.s(65), h.s(32)), f"{sh} × {sa}", font=fs, fill=h.ink, anchor="mm")
        d.text((mid + h.s(150), h.s(32)), away, font=f, fill=h.text, anchor="lm")
        return c
    cd = h.cached(key, card)
    h.put(base, cd, (h.W - cd.width) / 2, h.s(130 if h.vertical else 24) - (1 - a) * h.s(40), a)


def tv(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    """Plantão de TV: tarja 'PLANTÃO' + manchete + letreiro correndo."""
    a = ease((lt - 0.1) / 0.3) * (1 - ease((lt - (dur - 0.3)) / 0.3))
    if a <= 0:
        return
    head = str(data.get("headline") or "").upper()
    tick = str(data.get("ticker") or head)
    W = h.W
    c = Image.new("RGBA", (W, h.s(150)), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, h.s(190), h.s(48)), fill=h.danger)
    d.text((h.s(95), h.s(24)), str(data.get("tag") or "PLANTÃO"), font=h.F("title", 30), fill=(255, 255, 255), anchor="mm")
    d.rectangle((0, h.s(48), W, h.s(112)), fill=(245, 245, 245, 245))
    d.text((h.s(20), h.s(80)), head, font=fit(head, h.f_title, W - h.s(40), h.s(40), h.s(20)), fill=(15, 15, 20), anchor="lm")
    d.rectangle((0, h.s(112), W, h.s(148)), fill=(15, 20, 40, 240))
    ft = h.F("ui", 18)
    loop = (tick + "   •   ") * 4
    off = (lt * h.s(120)) % max(1, ft.getlength(tick + "   •   "))
    d.text((h.s(12) - off, h.s(130)), loop, font=ft, fill=(240, 240, 240), anchor="lm")
    h.put(base, c, -(1 - a) * W * 0.4, h.H * (0.66 if h.vertical else 0.72), a)


def phone(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    """Alerta de emergência no celular (notificação grande com vibração)."""
    a = ease((lt - 0.1) / 0.25) * (1 - ease((lt - (dur - 0.3)) / 0.3))
    if a <= 0:
        return
    title = str(data.get("title") or "ALERTA")
    body = str(data.get("body") or "")
    app = str(data.get("app") or "Alerta de emergência").upper()

    def card() -> Image.Image:
        W = h.s(600)
        fb = h.F("ui", 22)
        lines = wrap(body, fb, W - h.s(60))[:4]
        hh = h.s(120) + len(lines) * h.s(32)
        c = Image.new("RGBA", (W, hh), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, W - 1, hh - 1), h.s(26), fill=(250, 250, 252, 248))
        icon(d, "warn", h.s(38), h.s(36), h.s(14), h.danger)
        d.text((h.s(64), h.s(36)), app, font=h.F("ui", 16), fill=(110, 110, 120), anchor="lm")
        d.text((W - h.s(24), h.s(36)), "agora", font=h.F("ui", 16), fill=(140, 140, 150), anchor="rm")
        d.text((h.s(30), h.s(80)), title, font=fit(title, h.f_ui, W - h.s(60), h.s(28)), fill=(20, 20, 25), anchor="lm")
        for i, ln in enumerate(lines):
            d.text((h.s(30), h.s(108) + i * h.s(32)), ln, font=fb, fill=(50, 50, 60))
        return shadowed(c, blur=10)
    cd = h.cached(("phone", title, body, app), card)
    buzz = h.s(6) * math.sin(lt * 70) if lt < 0.6 else 0
    h.put(base, cd, (h.W - cd.width) / 2 + buzz, h.s(110) - (1 - a) * h.s(80), a)


def chat(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    """Conversa (mensagens/áudio): bolhas entrando uma a uma; 'audio': true vira mensagem de voz com ondas."""
    msgs = [m for m in (data.get("messages") or []) if isinstance(m, dict)][:4]
    if not msgs:
        return
    a = 1 - ease((lt - (dur - 0.3)) / 0.3)
    per = max(0.5, (dur - 0.6) / max(1, len(msgs)))
    fb = h.F("ui", 21)
    y = h.H * (0.3 if h.vertical else 0.25)
    for i, m in enumerate(msgs):
        k = ease((lt - 0.2 - i * per) / 0.25)
        if k <= 0:
            break
        me = bool(m.get("me"))
        maxw = h.W * 0.62
        if m.get("audio"):
            bw, bh = int(maxw * 0.8), h.s(64)
            c = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            d = ImageDraw.Draw(c)
            d.rounded_rectangle((0, 0, bw - 1, bh - 1), h.s(20), fill=(220, 248, 198, 250) if me else (255, 255, 255, 250))
            d.polygon([(h.s(22), h.s(20)), (h.s(22), h.s(44)), (h.s(42), h.s(32))], fill=(60, 60, 60))
            for j in range(26):
                amp = h.s(6 + 18 * abs(math.sin(j * 1.7 + (lt * 6 if k >= 1 else 0))))
                bx = h.s(56) + j * h.s(9)
                d.rectangle((bx, bh / 2 - amp / 2, bx + h.s(4), bh / 2 + amp / 2), fill=(90, 120, 90) if me else (120, 120, 130))
        else:
            lines = wrap(str(m.get("text", "")), fb, maxw - h.s(40))[:3]
            bw = int(max(fb.getlength(ln) for ln in lines) + h.s(40)) if lines else h.s(80)
            bh = h.s(24) + len(lines) * h.s(30) + (h.s(24) if m.get("from") and not me else 0)
            c = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
            d = ImageDraw.Draw(c)
            d.rounded_rectangle((0, 0, bw - 1, bh - 1), h.s(18), fill=(220, 248, 198, 250) if me else (255, 255, 255, 250))
            yy = h.s(12)
            if m.get("from") and not me:
                d.text((h.s(20), yy), str(m["from"]), font=h.F("ui", 17), fill=h.danger)
                yy += h.s(24)
            for j, ln in enumerate(lines):
                d.text((h.s(20), yy + j * h.s(30)), ln, font=fb, fill=(25, 25, 30))
        x = h.W - c.width - h.s(30) if me else h.s(30)
        h.put(base, shadowed(c, blur=6, alpha=0.35, off=(3, 5)), x + (1 - k) * (h.s(60) if me else -h.s(60)), y, a * k)
        y += c.height + h.s(16)


def map_card(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    """Mapa/minimapa estilizado: papel com ruas, rota tracejada animada e alfinete no destino."""
    a = ease((lt - 0.1) / 0.3) * (1 - ease((lt - (dur - 0.3)) / 0.3))
    if a <= 0:
        return
    W = h.s(420)
    label = str(data.get("label") or "")
    seed = sum(map(ord, label)) or 7

    def bgcard() -> Image.Image:
        import random
        rng = random.Random(seed)
        c = Image.new("RGBA", (W, W), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, W - 1, W - 1), h.s(16), fill=h.paper + (250,), outline=h.ink + (255,), width=h.s(3))
        for _ in range(14):
            if rng.random() < 0.5:
                y = rng.randint(h.s(20), W - h.s(20))
                d.line((h.s(10), y, W - h.s(10), y + rng.randint(-40, 40)), fill=(180, 165, 140), width=h.s(rng.choice([3, 5, 8])))
            else:
                x = rng.randint(h.s(20), W - h.s(20))
                d.line((x, h.s(10), x + rng.randint(-40, 40), W - h.s(10)), fill=(180, 165, 140), width=h.s(rng.choice([3, 5, 8])))
        d.polygon([(0, W * 0.75), (W * 0.3, W * 0.68), (W * 0.55, W), (0, W)], fill=(150, 185, 195, 255))
        _paper_texture(c, 4)
        return c
    c = h.cached(("mapbg", seed), bgcard).copy()
    d = ImageDraw.Draw(c)
    p0, p1 = (W * 0.2, W * 0.78), (W * 0.74, W * 0.28)
    k = ease((lt - 0.3) / max(0.5, dur * 0.5))
    steps = 30
    for i in range(int(steps * k)):
        if i % 2:
            continue
        t0, t1 = i / steps, (i + 1) / steps
        bend = lambda t: (p0[0] + (p1[0] - p0[0]) * t + math.sin(t * 3.1) * W * 0.12, p0[1] + (p1[1] - p0[1]) * t)  # noqa: E731
        d.line((*bend(t0), *bend(t1)), fill=h.danger, width=h.s(5))
    icon(d, "dot", p0[0], p0[1], h.s(9), h.ink)
    if k > 0.95:
        icon(d, "pin", p1[0], p1[1], h.s(16), h.danger)
    if label:
        f = fit(label.upper(), h.f_ui, W - h.s(40), h.s(20))
        tw = f.getlength(label.upper())
        d.rounded_rectangle((W / 2 - tw / 2 - h.s(12), h.s(14), W / 2 + tw / 2 + h.s(12), h.s(50)), h.s(8), fill=h.ink + (230,))
        d.text((W / 2, h.s(32)), label.upper(), font=f, fill=h.paper, anchor="mm")
    c = shadowed(c.rotate(-3, expand=True, resample=Image.BICUBIC), blur=8)
    h.put(base, c, h.W - c.width - h.s(10) + (1 - a) * h.s(80), h.H * (0.2 if h.vertical else 0.15), a)


def inventory(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    """Barra de recursos (ÁGUA 2/3, OXIGÊNIO 78%...): barras que descem/sobem animadas."""
    items = [i for i in (data.get("items") or []) if isinstance(i, dict)][:3]
    if not items:
        return
    a = ease((lt - 0.1) / 0.3) * (1 - ease((lt - (dur - 0.3)) / 0.3))
    if a <= 0:
        return
    W = h.s(330)
    hh = h.s(20) + len(items) * h.s(48)
    c = Image.new("RGBA", (W, hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, W - 1, hh - 1), h.s(12), fill=h.panel)
    for i, it in enumerate(items):
        mx = float(it.get("max") or 100)
        v0, v1 = float(it.get("from", it.get("value", 0))), float(it.get("value", 0))
        v = v0 + (v1 - v0) * ease((lt - 0.5) / 1.2)
        frac = max(0.0, min(1.0, v / mx))
        y = h.s(14) + i * h.s(48)
        lab = str(it.get("label", ""))[:16].upper()
        d.text((h.s(14), y + h.s(4)), lab, font=h.F("ui", 15), fill=h.text)
        val = f"{int(round(v))}/{int(mx)}" if mx <= 20 else f"{int(round(v))}%"
        d.text((W - h.s(14), y + h.s(4)), val, font=h.F("ui", 15), fill=h.text, anchor="ra")
        d.rounded_rectangle((h.s(14), y + h.s(26), W - h.s(14), y + h.s(38)), h.s(5), fill=(255, 255, 255, 40))
        col = h.danger if frac < 0.25 else h.accent
        d.rounded_rectangle((h.s(14), y + h.s(26), h.s(14) + max(h.s(10), (W - h.s(28)) * frac), y + h.s(38)), h.s(5), fill=col)
    h.put(base, c, h.W - W - h.s(24) + (1 - a) * h.s(60), h.s(28) if h.vertical else h.s(22), a)


def alert(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    a = ease((lt - 0.15) / 0.3) * (1 - ease((lt - (dur - 0.4)) / 0.4))
    if a <= 0:
        return
    kick, title, body = str(data.get("kicker") or "").upper(), str(data.get("title") or "").upper(), str(data.get("body") or "")

    def card() -> Image.Image:
        W = h.W - h.s(160) if h.vertical else int(h.W * 0.4)
        c = Image.new("RGBA", (W, h.s(280)), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, h.s(30), W - 1, h.s(279)), h.s(16), fill=(18, 8, 8, 242), outline=h.danger, width=h.s(4))
        d.ellipse((W // 2 - h.s(30), 0, W // 2 + h.s(30), h.s(60)), fill=h.danger)
        d.text((W // 2, h.s(30)), "!", font=h.F("title", 46), fill=(255, 255, 255), anchor="mm")
        if kick:
            d.text((W // 2, h.s(96)), kick, font=fit(kick, h.f_ui, W - h.s(40), h.s(18)), fill=h.danger, anchor="mm")
        d.text((W // 2, h.s(160)), title, font=fit(title, h.f_title, W - h.s(50), h.s(60), h.s(24)), fill=(255, 255, 255), anchor="mm")
        if body:
            fb = fit(body, h.f_ui, W - h.s(50), h.s(22), h.s(14))
            d.text((W // 2, h.s(225)), body, font=fb, fill=(220, 210, 200), anchor="mm")
        return shadowed(c)
    cd = h.cached(("alert", kick, title, body), card)
    s = back(min(1.0, (lt - 0.15) / 0.35)) if lt < 0.6 else 1.0
    if abs(s - 1) > 0.01 and s > 0:
        cd = cd.resize((max(1, int(cd.width * s)), max(1, int(cd.height * s))), Image.BILINEAR)
    h.put(base, cd, (h.W - cd.width) / 2, h.H * 0.42 - cd.height / 2 + h.s(60), a)


def countdown(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    a = ease((lt - 0.1) / 0.35)
    if a <= 0:
        return
    val, lab = str(data.get("value") or ""), str(data.get("label") or "").upper()
    s = back(min(1.0, (lt - 0.1) / 0.4))
    f = h.F("title", 150 * max(0.3, s))
    d = ImageDraw.Draw(base, "RGBA")
    al = int(255 * a)
    cy = h.H * (0.48 if h.vertical else 0.45)
    d.text((h.W / 2, cy), val, font=f, fill=h.accent[:3] + (al,), anchor="mm", stroke_width=h.s(5), stroke_fill=h.ink + (al,))
    if lab:
        d.text((h.W / 2, cy + h.s(100)), lab, font=fit(lab, h.f_ui, h.W - h.s(80), h.s(26)), fill=h.text[:3] + (al,), anchor="mm",
               stroke_width=h.s(2), stroke_fill=h.ink + (al,))


def chip(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    a = ease((lt - 0.2) / 0.3) * (1 - ease((lt - (dur - 0.25)) / 0.25))
    if a <= 0:
        return
    text = str(data.get("text") or "")
    if not text:
        return

    def card() -> Image.Image:
        f = fit(text, h.f_ui, h.W - h.s(120), h.s(22), h.s(14))
        tw = f.getlength(text)
        c = Image.new("RGBA", (int(tw + h.s(40)), h.s(44)), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, c.width - 1, c.height - 1), h.s(8), fill=h.accent + (255,))
        d.text((c.width / 2, c.height / 2), text, font=f, fill=h.ink, anchor="mm")
        return c
    cd = h.cached(("chip", text), card)
    y = float(data.get("y", 0.12)) * h.H
    h.put(base, cd, (h.W - cd.width) / 2, y, a)


def highlight(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any], box: tuple | None) -> None:
    """Caixa com brilho + etiqueta em volta de algo da cena (box em pixels do quadro, já com a câmera aplicada)."""
    if not box:
        return
    a = ease((lt - float(data.get("at", 0.3))) / 0.3) * (1 - ease((lt - (dur - 0.25)) / 0.25))
    if a <= 0:
        return
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(h.s(12), x0), max(h.s(60), y0)
    x1, y1 = min(h.W - h.s(12), x1), min(h.H - h.s(12), y1)
    if x1 - x0 < h.s(40) or y1 - y0 < h.s(40):
        return
    lay = Image.new("RGBA", (x1 - x0 + h.s(40), y1 - y0 + h.s(40)), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle((h.s(20), h.s(20), lay.width - h.s(20), lay.height - h.s(20)), h.s(10), outline=h.accent + (255,), width=h.s(5))
    glow = lay.filter(ImageFilter.GaussianBlur(h.s(9)))
    glow.alpha_composite(lay)
    h.put(base, glow, x0 - h.s(20), y0 - h.s(20), a)
    label = str(data.get("label") or "").upper()
    if label:
        f = h.F("ui", 22)
        tw = f.getlength(label)
        c = Image.new("RGBA", (int(tw + h.s(26)), h.s(34)), h.accent + (255,))
        ImageDraw.Draw(c).text((h.s(13), h.s(17)), label, font=f, fill=h.ink, anchor="lm")
        h.put(base, c, min(x0, h.W - c.width - h.s(10)), max(h.s(110), y0 - h.s(42)), a)


def dialogue(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any], portrait: Image.Image | None,
             blink: bool = False) -> None:
    """Caixa de diálogo: retrato do personagem, nome, ondas de áudio e texto digitando com cursor."""
    a = ease(lt / 0.3)
    if a <= 0:
        return
    who, text = str(data.get("who") or "").upper(), str(data.get("text") or "")
    x0 = h.s(40)
    y0 = h.H * (0.70 if h.vertical else 0.66)
    bw = h.W - 2 * x0 if h.vertical else int(h.W * 0.62)
    if not h.vertical:
        x0 = (h.W - bw) // 2
    d = ImageDraw.Draw(base, "RGBA")
    ps = h.s(170)
    if portrait is not None:
        pr = h.cached(("portrait", id(portrait), ps), lambda: portrait.convert("RGBA").resize((ps, ps), Image.LANCZOS))
        if blink:
            pr = pr  # o piscar do retrato é feito antes (render) — aqui só posiciona
        fr = Image.new("RGBA", (ps + h.s(12), ps + h.s(12)), h.accent + (255,))
        inner = Image.new("RGBA", (ps, ps), h.panel[:3] + (255,))
        inner.alpha_composite(pr)
        fr.paste(inner, (h.s(6), h.s(6)))
        h.put(base, fr, x0 - h.s(6), y0 - ps - h.s(26) + (1 - a) * h.s(30), a)
    f_who = h.F("ui", 22)
    wx = x0 + (ps + h.s(16) if portrait is not None else 0)
    tw = f_who.getlength(who)
    d.rounded_rectangle((wx, y0 - h.s(50), wx + tw + h.s(24), y0 - h.s(16)), h.s(6), fill=h.accent + (int(255 * a),))
    d.text((wx + h.s(12), y0 - h.s(33)), who, font=f_who, fill=h.ink + (int(255 * a),), anchor="lm")
    talking = lt < dur - 0.4
    for i in range(22):
        hgt = h.s(6) + h.s(18) * abs(math.sin(lt * 9 + i * 0.7)) * (1 if talking else 0.2)
        bx = wx + tw + h.s(40) + i * h.s(9)
        if bx > x0 + bw - h.s(10):
            break
        d.rectangle((bx, y0 - h.s(33) - hgt / 2, bx + h.s(4), y0 - h.s(33) + hgt / 2), fill=h.accent + (int(255 * a),))
    box_h = h.s(190)
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + box_h), h.s(12), fill=h.panel[:3] + (int(235 * a),), outline=h.accent + (int(255 * a),),
                        width=h.s(3))
    ft = font(h.f_type, h.s(30))
    n = int(len(text) * min(1.0, lt / max(0.1, dur - 0.5)))
    lines = wrap(text[:n], ft, bw - h.s(48)) or [""]
    for i, ln in enumerate(lines[-4:]):
        d.text((x0 + h.s(24), y0 + h.s(22) + i * h.s(40)), ln, font=ft, fill=(240, 236, 226, int(255 * a)))
    if int(lt * 3) % 2 == 0:
        last = lines[-4:][-1]
        cx = x0 + h.s(24) + ft.getlength(last) + h.s(6)
        cy = y0 + h.s(22) + (len(lines[-4:]) - 1) * h.s(40)
        d.rectangle((cx, cy + h.s(4), cx + h.s(14), cy + h.s(32)), fill=h.accent + (int(255 * a),))


def endcard(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any]) -> None:
    a = ease((lt - 0.1) / 0.3)
    if a <= 0:
        return
    text = str(data.get("text") or "CONTINUA…").upper()
    sub = str(data.get("sub") or "")

    def card() -> Image.Image:
        f = fit(text, h.f_ui, h.W - h.s(100), h.s(26))
        tw = f.getlength(text)
        W = int(tw + h.s(60))
        hh = h.s(54) + (h.s(40) if sub else 0)
        c = Image.new("RGBA", (max(W, h.s(200)), hh), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, c.width - 1, h.s(53)), h.s(10), fill=h.accent + (255,))
        d.text((c.width / 2, h.s(27)), text, font=f, fill=h.ink, anchor="mm")
        if sub:
            d.text((c.width / 2, h.s(76)), sub, font=fit(sub, h.f_ui, c.width, h.s(19)), fill=h.text, anchor="mm",
                   stroke_width=h.s(2), stroke_fill=h.ink)
        return c
    cd = h.cached(("end", text, sub), card)
    h.put(base, cd, (h.W - cd.width) / 2, h.H * (0.8 if h.vertical else 0.78) + (1 - a) * h.s(30), a)


WIDGETS = {
    "mission": mission, "objectives": objectives, "newspaper": newspaper, "telegram": telegram, "console": console,
    "notebook": notebook, "radio": radio, "scoreboard": scoreboard, "tv": tv, "phone": phone, "chat": chat,
    "map": map_card, "inventory": inventory, "alert": alert, "countdown": countdown, "chip": chip, "endcard": endcard,
}
# widgets que ocupam o centro da tela (escurecem o fundo um pouco para leitura)
CENTER = {"mission", "newspaper", "telegram", "console", "notebook", "alert", "countdown"}
