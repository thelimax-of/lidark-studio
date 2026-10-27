"""Kit de marca do canal: foto de perfil, capa (banner) e marca d'água, a partir da identidade (tema).

Tudo desenhado localmente com o mascote e a paleta do canal — nada de IA de imagem, então sai igual
toda vez e combina com os vídeos. Tamanhos oficiais do YouTube:
- foto de perfil 800×800 (exibida em círculo);
- capa 2560×1440, com o conteúdo dentro da área segura de 1546×423 (o que aparece em qualquer tela);
- marca d'água 150×150 PNG transparente (Studio → Personalização → Marca).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .render.characters import make_mascot
from .render.core import font, hex2rgb, rgba
from .seed import OURO_THEME

SAFE_W, SAFE_H = 1546, 423


def _theme(theme: dict[str, Any] | None) -> dict[str, Any]:
    th = dict(OURO_THEME)
    th.update(theme or {})
    return th


def _radial(w: int, h: int, center: str, edge: str, cy: float = 0.5) -> Image.Image:
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * cy) / (h / 2)) ** 2)
    k = np.clip(r / 1.25, 0, 1)[..., None]
    c, e = np.array(hex2rgb(center), np.float32), np.array(hex2rgb(edge), np.float32)
    return Image.fromarray((c * (1 - k) + e * k).astype(np.uint8), "RGB").convert("RGBA")


def _mascot_img(th: dict[str, Any], height: int) -> Image.Image | None:
    m = make_mascot(th, 200, 3)
    if m is None:
        return None
    img, _ = m.frame(0.4, 0, 0.0, "happy", 1.0)
    img = img.crop(img.getbbox())
    return img.resize((int(img.width * height / img.height), height), Image.LANCZOS)


def _shadow(img: Image.Image, blur: int, alpha: int = 150) -> Image.Image:
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sh.putalpha(img.getchannel("A").point(lambda v: min(alpha, v)))
    return sh.filter(ImageFilter.GaussianBlur(float(blur)))


def _fit_font(name: str, text: str, max_w: int, max_size: int):
    size = max_size
    while size > 20:
        f = font(name, size)
        if f.getlength(text) <= max_w:
            return f
        size -= 4
    return font(name, size)


def _letter_badge(th: dict[str, Any], size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, size - 1, size - 1), fill=rgba(th["gold"]))
    f = font(th["font_title"], int(size * 0.62))
    d.text((size / 2, size / 2), th.get("logo_letter", "L")[:1], font=f, fill=rgba(th["ink"]), anchor="mm")
    return img


LOGO_STYLES = {
    "mascot": "Mascote no centro",
    "stacked": "Nome empilhado com brilho (só tipografia)",
    "monogram": "Iniciais grandes com anel e o nome em volta",
    "scoreboard": "Placar/painel com o nome dentro",
    "icon": "Cena temática: símbolo do nicho brilhando + nome embaixo (estilo Sinal do Cosmos)",
}


def _glow(layer: Image.Image, color: str, radius: int, strength: int = 2) -> Image.Image:
    g = Image.new("RGBA", layer.size, (*hex2rgb(color), 0))
    g.putalpha(layer.getchannel("A"))
    g = g.filter(ImageFilter.GaussianBlur(float(radius)))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    for _ in range(strength):
        out.alpha_composite(g)
    return out


def _initials(name: str) -> str:
    words = [w for w in name.split() if len(w) > 2] or name.split()
    return "".join(w[0] for w in words[:2]).upper() or "L"


def emblem(th: dict[str, Any], name: str, size: int, style: str) -> Image.Image:
    """Logo só tipográfica (sem mascote), em camada transparente para ir sobre o fundo."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gold, text = th["gold"], th.get("caption_text", "#ffffff")
    ui = th.get("font_ui", "FiraSans-Bold.ttf")
    c = size / 2
    words = name.upper().split()
    if style == "monogram":
        ini = _initials(name)
        d.ellipse((size * 0.2, size * 0.2, size * 0.8, size * 0.8), outline=rgba(gold), width=int(size * 0.012))
        f = _fit_font(th["font_title"], ini, int(size * 0.44), int(size * 0.36))
        tl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(tl).text((c, c), ini, font=f, fill=rgba(text), anchor="mm")
        img.alpha_composite(_glow(tl, gold, int(size * 0.02)))
        img.alpha_composite(tl)
        fs = font(ui, int(size * 0.056))
        label = " ".join(words)
        r = size * 0.36
        span = min(200, 13 * len(label))
        for i, ch in enumerate(label):  # nome em arco, no topo
            a = math.radians(-90 - span / 2 + span * (i + 0.5) / len(label))
            g = Image.new("RGBA", (int(size * 0.1), int(size * 0.1)), (0, 0, 0, 0))
            ImageDraw.Draw(g).text((g.width / 2, g.height / 2), ch, font=fs, fill=rgba(th["gold_light"]), anchor="mm")
            g = g.rotate(-math.degrees(a) - 90, resample=Image.BICUBIC)
            img.alpha_composite(g, (int(c + r * math.cos(a) - g.width / 2), int(c + r * math.sin(a) - g.height / 2)))
        for k, rr in ((-1, 0.018), (0, 0.027), (1, 0.018)):  # estrelinhas na base
            d.regular_polygon((c + k * size * 0.09, size * 0.86, size * rr), 5, fill=rgba(gold))
    elif style == "scoreboard":
        w, h = size * 0.74, size * 0.4
        x0, y0 = c - w / 2, c - h / 2 + size * 0.04
        d.rounded_rectangle((x0, y0, x0 + w, y0 + h), int(size * 0.04), fill=rgba("#0d0d10", 235), outline=rgba(gold), width=int(size * 0.014))
        d.rounded_rectangle((x0 + w * 0.16, y0 - size * 0.085, x0 + w * 0.84, y0 + size * 0.025), int(size * 0.02), fill=rgba(gold))
        f1 = _fit_font(th["font_title"], words[0], int(w * 0.58), int(size * 0.085))
        d.text((c, y0 - size * 0.03), words[0], font=f1, fill=rgba(th["ink"]), anchor="mm")
        rest = " ".join(words[1:]) or words[0]
        f2 = _fit_font(th["font_title"], rest, int(w * 0.86), int(size * 0.2))
        tl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(tl).text((c, y0 + h * 0.47), rest, font=f2, fill=rgba(th["caption_hi"]), anchor="mm")
        img.alpha_composite(_glow(tl, th["caption_hi"], int(size * 0.02)))
        img.alpha_composite(tl)
        for k in range(9):  # pontinhos de painel de LED
            x = x0 + w * (0.1 + 0.8 * k / 8)
            yy = y0 + h * 0.85
            d.ellipse((x - size * 0.008, yy - size * 0.008, x + size * 0.008, yy + size * 0.008), fill=rgba(gold, 170))
    else:  # stacked
        lines: list[str] = []
        for w in words:  # conectivos curtos ("E", "DA", "DO") vão junto da palavra seguinte
            if lines and len(lines[-1]) <= 3:
                lines[-1] += " " + w
            else:
                lines.append(w)
        if len(lines) > 3:
            lines = [" ".join(lines[:len(lines) // 2]), " ".join(lines[len(lines) // 2:])]
        tl = Image.new("RGBA", img.size, (0, 0, 0, 0))
        td = ImageDraw.Draw(tl)
        max_h = size * 0.5 / len(lines)  # o bloco inteiro cabe na metade do círculo
        fonts = []
        for ln in lines:
            f = _fit_font(th["font_title"], ln, int(size * 0.66), int(size * 0.26))
            while f.size > 20 and f.getbbox(ln)[3] - f.getbbox(ln)[1] > max_h:
                f = font(th["font_title"], f.size - 4)
            fonts.append(f)
        heights = [f.getbbox(ln)[3] - f.getbbox(ln)[1] for f, ln in zip(fonts, lines)]
        gap = size * 0.03
        total = sum(heights) + gap * (len(lines) - 1)
        y = c - total / 2
        for i, (f, ln, hh) in enumerate(zip(fonts, lines, heights)):
            td.text((c, y + hh / 2), ln, font=f, fill=rgba(text if i == 0 else th["caption_hi"]), anchor="mm")
            y += hh + gap
        img.alpha_composite(_glow(tl, gold, int(size * 0.025)))
        img.alpha_composite(tl)
        lw = size * 0.2
        for yy in (c - total / 2 - size * 0.07, c + total / 2 + size * 0.07):
            d.line((c - lw, yy, c - size * 0.04, yy), fill=rgba(gold), width=int(size * 0.01))
            d.line((c + size * 0.04, yy, c + lw, yy), fill=rgba(gold), width=int(size * 0.01))
            d.regular_polygon((c, yy, size * 0.022), 5, fill=rgba(gold))
    return img


def _logo(th: dict[str, Any], name: str, size: int) -> Image.Image:
    style = th.get("logo_style", "mascot")
    if style in LOGO_STYLES and style != "mascot":
        return emblem(th, name, size, style)
    m = _mascot_img(th, int(size * 0.62)) or _letter_badge(th, int(size * 0.62))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(m, ((size - m.width) // 2, (size - m.height) // 2 + int(size * 0.02)))
    return out


# ================================================================ estilo "cena" (igual ao Sinal do Cosmos)
# Fundo temático ocupando tudo + símbolo chapado e brilhante do nicho + nome embaixo em cor de contraste.
# Na capa: mesmo fundo, mascote à esquerda, nome com contorno, subtítulo, etiqueta e um elemento gigante cortado.

def _scene_bg(th: dict[str, Any], w: int, h: int, seed: int = 7) -> Image.Image:
    rng = np.random.default_rng(seed)
    img = _radial(w, h, th["bg_center"], th["bg_edge"], 0.45)
    s = min(w, h)
    neb = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    nd = ImageDraw.Draw(neb)
    for col in (th["gold"], th.get("mascot_accent", th["gold"]), th["bg_center"], th["gold"]):  # nebulosas suaves
        x, y, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.25, 0.5) * s
        nd.ellipse((x - r, y - r * 0.7, x + r, y + r * 0.7), fill=rgba(col, 34))
    img.alpha_composite(neb.filter(ImageFilter.GaussianBlur(float(s * 0.08))))
    deco = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    motif, light = th.get("motif", "particles"), hex2rgb(th["gold_light"])
    if motif == "lab":  # moléculas (hexágonos com átomos) espalhadas + bolhas subindo
        for _ in range(int(w * h / 90000)):
            x, y, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.02, 0.045) * s
            a0 = rng.uniform(0, math.pi / 3)
            pts = [(x + r * math.cos(a0 + k * math.pi / 3), y + r * math.sin(a0 + k * math.pi / 3)) for k in range(6)]
            al = int(rng.uniform(16, 40))
            dd.line(pts + [pts[0]], fill=(*light, al), width=max(2, int(s * 0.003)))
            for px, py in pts[::2]:
                dd.ellipse((px - r * 0.14, py - r * 0.14, px + r * 0.14, py + r * 0.14), fill=(*light, al + 20))
        for _ in range(int(w * h / 40000)):
            x, y, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.003, 0.012) * s
            dd.ellipse((x - r, y - r, x + r, y + r), outline=(*light, int(rng.uniform(40, 110))), width=max(1, int(r * 0.25)))
    elif motif == "chart":  # grade de gráfico + candles apagados + linha de preço
        step = s * 0.08
        for k in range(int(w / step) + 1):
            dd.line((k * step, 0, k * step, h), fill=(*light, 12), width=max(1, int(s * 0.0015)))
        for k in range(int(h / step) + 1):
            dd.line((0, k * step, w, k * step), fill=(*light, 12), width=max(1, int(s * 0.0015)))
        up, down = hex2rgb(th["gold"]), hex2rgb(th.get("bear", "#ef4444"))
        cw, y = s * 0.018, h * 0.62
        pts = []
        for k in range(int(w / (cw * 2.2))):
            x = k * cw * 2.2 + cw
            o = y
            y = min(h * 0.9, max(h * 0.1, y + rng.normal(-0.004, 0.03) * h))
            hi, lo = min(o, y) - rng.uniform(0.005, 0.03) * h, max(o, y) + rng.uniform(0.005, 0.03) * h
            col = up if y < o else down
            dd.line((x, hi, x, lo), fill=(*col, 34), width=max(1, int(cw * 0.15)))
            dd.rectangle((x - cw / 2, min(o, y), x + cw / 2, max(o, y) + 1), fill=(*col, 42))
            pts.append((x, y))
        if len(pts) > 1:
            dd.line(pts, fill=(*light, 40), width=max(2, int(s * 0.003)), joint="curve")
    for _ in range(int(w * h / 2500)):  # poeira/estrelas
        x, y, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0.4, 1.6) * s / 800
        dd.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, int(rng.uniform(40, 200))))
    img.alpha_composite(deco)
    return img


def _symbol_flask(th: dict[str, Any], size: int) -> Image.Image:
    S = size * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    c = S / 2
    liquid, glass, accent = th["gold"], th["gold_light"], th.get("logo_text", "#ffcf4a")
    orbit = Image.new("RGBA", (S, S), (0, 0, 0, 0))  # órbitas de átomo (o "anel" do planeta do Sinal)
    for ang in (-28, 28):
        o = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(o).ellipse((c - S * 0.46, c - S * 0.14, c + S * 0.46, c + S * 0.14), outline=rgba(accent), width=int(S * 0.02))
        orbit.alpha_composite(o.rotate(ang, resample=Image.BICUBIC, center=(c, c + S * 0.06)))
    od = ImageDraw.Draw(orbit)
    for ex, ey in ((c - S * 0.36, c - S * 0.12), (c + S * 0.4, c + S * 0.26)):
        od.ellipse((ex - S * 0.028, ey - S * 0.028, ex + S * 0.028, ey + S * 0.028), fill=rgba(accent))
    img.alpha_composite(_glow(orbit, accent, int(S * 0.02)))
    img.alpha_composite(orbit)

    fl = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fl)
    nw, top, base = S * 0.13, c - S * 0.34, c + S * 0.3
    body = [(c - nw / 2, top + S * 0.06), (c + nw / 2, top + S * 0.06), (c + nw / 2, c - S * 0.08),
            (c + S * 0.3, base - S * 0.03), (c + S * 0.27, base), (c - S * 0.27, base), (c - S * 0.3, base - S * 0.03),
            (c - nw / 2, c - S * 0.08)]
    fd.polygon(body, fill=rgba(glass, 60))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).polygon(body, fill=255)
    liq = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ld = ImageDraw.Draw(liq)
    ly = c + S * 0.04
    ld.rectangle((0, ly, S, S), fill=rgba(liquid))
    ld.ellipse((c - S * 0.2, ly - S * 0.02, c + S * 0.2, ly + S * 0.02), fill=rgba(glass))
    for bx, by, br in ((-0.08, 0.14, 0.03), (0.06, 0.2, 0.022), (0.12, 0.1, 0.016), (-0.02, 0.24, 0.014)):
        ld.ellipse((c + (bx - br) * S, c + (by - br) * S, c + (bx + br) * S, c + (by + br) * S), fill=(255, 255, 255, 170))
    fl.paste(liq, (0, 0), Image.composite(liq.getchannel("A"), Image.new("L", (S, S), 0), mask))
    fd.line(body + [body[0]], fill=rgba(glass), width=int(S * 0.018), joint="curve")
    fd.rounded_rectangle((c - nw * 0.8, top, c + nw * 0.8, top + S * 0.06), int(S * 0.015), fill=rgba(glass))
    fd.line((c - S * 0.2, base - S * 0.1, c - S * 0.12, c + S * 0.0), fill=(255, 255, 255, 150), width=int(S * 0.016))
    img.alpha_composite(_glow(fl, liquid, int(S * 0.03)))
    img.alpha_composite(fl)
    return img.resize((size, size), Image.LANCZOS)


def _symbol_chart(th: dict[str, Any], size: int) -> Image.Image:
    """Candles subindo + seta de alta + moeda (mercado/trade)."""
    S = size * 2
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    up, down, accent = th["gold"], th.get("bear", "#ef4444"), th.get("logo_text", "#facc15")
    ch = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(ch)
    base, cw = S * 0.78, S * 0.1
    candles = [(0.2, 0.62, 0.5, up), (0.34, 0.5, 0.58, down), (0.48, 0.52, 0.4, up), (0.62, 0.42, 0.3, up), (0.76, 0.32, 0.18, up)]
    for cx, o, c, col in candles:  # (x, abertura, fechamento) em fração da altura
        x = cx * S
        top, bot = min(o, c) * S, max(o, c) * S
        d.line((x, top - S * 0.05, x, bot + S * 0.05), fill=rgba(col), width=int(S * 0.014))
        d.rounded_rectangle((x - cw / 2, top, x + cw / 2, bot), int(S * 0.012), fill=rgba(col))
    d.line((S * 0.1, base, S * 0.9, base), fill=rgba(th["gold_light"], 160), width=int(S * 0.01))
    img.alpha_composite(_glow(ch, up, int(S * 0.025)))
    img.alpha_composite(ch)
    ar = Image.new("RGBA", (S, S), (0, 0, 0, 0))  # seta de alta cruzando os candles
    ad = ImageDraw.Draw(ar)
    path = [(S * 0.12, S * 0.66), (S * 0.36, S * 0.46), (S * 0.5, S * 0.54), (S * 0.8, S * 0.22)]
    ad.line(path, fill=rgba(accent), width=int(S * 0.03), joint="curve")
    tip, ang = path[-1], math.atan2(path[-1][1] - path[-2][1], path[-1][0] - path[-2][0])
    L = S * 0.09
    ad.polygon([(tip[0] + L * 0.6 * math.cos(ang), tip[1] + L * 0.6 * math.sin(ang)),
                (tip[0] + L * math.cos(ang + 2.4), tip[1] + L * math.sin(ang + 2.4)),
                (tip[0] + L * math.cos(ang - 2.4), tip[1] + L * math.sin(ang - 2.4))], fill=rgba(accent))
    img.alpha_composite(_glow(ar, accent, int(S * 0.02)))
    img.alpha_composite(ar)
    return img.resize((size, size), Image.LANCZOS)


SYMBOLS = {"flask": _symbol_flask, "chart": _symbol_chart}


def _symbol(th: dict[str, Any], size: int) -> Image.Image:
    fn = SYMBOLS.get(th.get("symbol", th.get("mascot", "")))
    if fn:
        return fn(th, size)
    return _mascot_img(th, size) or _letter_badge(th, size)


def _outlined(d: ImageDraw.ImageDraw, xy, text: str, f, fill: str, stroke: int, anchor: str) -> None:
    d.text((xy[0] + stroke * 0.6, xy[1] + stroke * 0.9), text, font=f, fill=(0, 0, 0, 150), anchor=anchor,
           stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    d.text(xy, text, font=f, fill=rgba(fill), anchor=anchor, stroke_width=stroke, stroke_fill=(10, 14, 20, 255))


def avatar_scene(th: dict[str, Any], name: str, size: int = 800) -> Image.Image:
    img = _scene_bg(th, size, size, 3)
    sym = _symbol(th, int(size * 0.6))
    img.alpha_composite(sym, ((size - sym.width) // 2, int(size * 0.07)))
    d = ImageDraw.Draw(img)
    words = name.upper().split()
    lines = [" ".join(words[:len(words) // 2 or 1]), " ".join(words[len(words) // 2 or 1:])] if len(words) > 1 else words
    f = min((_fit_font(th["font_title"], ln, int(size * 0.66), int(size * 0.12)) for ln in lines if ln), key=lambda x: x.size)
    y = size * 0.72
    for ln in [x for x in lines if x]:
        _outlined(d, (size / 2, y), ln, f, th.get("logo_text", "#ffcf4a"), max(2, size // 200), "mm")
        y += f.size * 1.08
    return img.convert("RGB")


def watermark_scene(th: dict[str, Any], size: int = 150) -> Image.Image:
    big = size * 4
    bg = _scene_bg(th, big, big, 3)
    sym = _symbol(th, int(big * 0.8))
    bg.alpha_composite(sym, ((big - sym.width) // 2, (big - sym.height) // 2))
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, big - 1, big - 1), fill=255)
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(bg, (0, 0), mask)
    return out.resize((size, size), Image.LANCZOS)


def banner_scene(th: dict[str, Any], name: str, tagline: str = "") -> Image.Image:
    W, H = 2560, 1440
    img = _scene_bg(th, W, H, 11)
    big = _symbol(th, 1500)  # elemento gigante cortado à direita (o planeta do Sinal)
    big.putalpha(big.getchannel("A").point(lambda v: int(v * 0.55)))
    img.alpha_composite(big, (W - 1000, H - 1150))
    cx, cy = W // 2, H // 2
    x0 = cx - SAFE_W // 2
    m = _mascot_img(th, int(SAFE_H * 0.92))
    text_x = x0 + 30
    if m is not None:
        mx, my = x0 + 10, cy - m.height // 2
        img.alpha_composite(_shadow(m, 14), (mx + 10, my + 16))
        img.alpha_composite(m, (mx, my))
        text_x = mx + m.width + 50
    max_w = x0 + SAFE_W - text_x - 10
    d = ImageDraw.Draw(img)
    f = _fit_font(th["font_title"], name.upper(), max_w, 170)
    _outlined(d, (text_x, cy - 20), name.upper(), f, th.get("logo_text", "#ffcf4a"), 6, "ls")
    sub = tagline or th.get("slogan", "").capitalize()
    fs = _fit_font(th.get("font_caption", "Poppins-ExtraBold.ttf"), sub, max_w, 58)
    _outlined(d, (text_x, cy + 62), sub, fs, "#ffffff", 3, "ls")
    badge = th.get("badge", "NOVOS VÍDEOS TODA SEMANA")
    fb = font(th.get("font_caption", "Poppins-ExtraBold.ttf"), 36)
    bw = fb.getlength(badge) + 70
    d.rounded_rectangle((text_x, cy + 100, text_x + bw, cy + 166), 33, fill=rgba(th["gold"]))
    d.text((text_x + bw / 2, cy + 133), badge, font=fb, fill=rgba(th["ink"]), anchor="mm")
    return img.convert("RGB")


def avatar(th: dict[str, Any], name: str = "", size: int = 800) -> Image.Image:
    if th.get("logo_style") == "icon":
        return avatar_scene(th, name, size)
    img = _radial(size, size, th["bg_center"], th["bg_edge"], 0.45)
    d = ImageDraw.Draw(img)
    ring = int(size * 0.035)
    d.ellipse((ring, ring, size - ring, size - ring), outline=rgba(th["gold"]), width=ring)
    m = _logo(th, name, size)
    img.alpha_composite(_shadow(m, size // 60), (size // 80, size // 50))
    img.alpha_composite(m)
    return img.convert("RGB")


def watermark(th: dict[str, Any], name: str = "", size: int = 150) -> Image.Image:
    if th.get("logo_style") == "icon":
        return watermark_scene(th, size)
    big = size * 4
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, big - 1, big - 1), fill=rgba(th["bg_center"], 235))
    d.ellipse((big * 0.03, big * 0.03, big * 0.97, big * 0.97), outline=rgba(th["gold"]), width=int(big * 0.05))
    img.alpha_composite(_logo(th, name, big))
    return img.resize((size, size), Image.LANCZOS)


def banner(th: dict[str, Any], name: str, handle: str = "", tagline: str = "") -> Image.Image:
    if th.get("logo_style") == "icon":
        return banner_scene(th, name, tagline)
    W, H = 2560, 1440
    img = _radial(W, H, th["bg_center"], th["bg_edge"], 0.5)
    deco = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(deco)
    gold = hex2rgb(th["gold"])
    for k in range(-8, 30):  # faixas diagonais discretas (só enfeite, fora da área segura não importa)
        x = k * 120
        dd.line((x, H, x + H * 0.6, 0), fill=(*gold, 14), width=28)
    cx, cy = W // 2, H // 2
    dd.ellipse((cx - 520, cy - 520, cx + 520, cy + 520), outline=(*gold, 26), width=6)
    dd.line((cx, 0, cx, H), fill=(*gold, 18), width=6)
    img.alpha_composite(deco)

    x0, y0 = cx - SAFE_W // 2, cy - SAFE_H // 2
    m = _mascot_img(th, int(SAFE_H * 0.95))
    text_x = x0 + 40
    if m is not None:
        mx, my = x0 + 10, cy - m.height // 2 + 6
        img.alpha_composite(_shadow(m, 14), (mx + 10, my + 16))
        img.alpha_composite(m, (mx, my))
        text_x = mx + m.width + 60
    max_w = x0 + SAFE_W - text_x - 20
    d = ImageDraw.Draw(img)
    title = name.upper()
    f = _fit_font(th["font_title"], title, max_w, 210)
    ty = cy - 30
    d.text((text_x + 6, ty + 8), title, font=f, fill=(0, 0, 0, 150), anchor="ls")
    d.text((text_x, ty), title, font=f, fill=rgba(th.get("caption_text", "#ffffff")), anchor="ls")
    tw = int(f.getlength(title))
    d.rounded_rectangle((text_x, ty + 26, text_x + min(tw, max_w), ty + 40), 7, fill=rgba(th["gold"]))
    sub = (tagline or th.get("slogan", "")).upper()
    if sub:
        fs = _fit_font(th.get("font_ui", "FiraSans-Bold.ttf"), sub, max_w, 62)
        d.text((text_x, ty + 112), sub, font=fs, fill=rgba(th["gold_light"]), anchor="ls")
    if handle:
        fh = font(th.get("font_ui", "FiraSans-Bold.ttf"), 44)
        d.text((text_x, ty + 176), handle, font=fh, fill=rgba(th.get("caption_dim", "#aaaaaa")), anchor="ls")
    return img.convert("RGB")


def sheet(av: Image.Image, bn: Image.Image, wm: Image.Image, th: dict[str, Any], name: str) -> Image.Image:
    """Prancha de revisão: capa como aparece no PC (área segura marcada), foto em círculo e marca d'água."""
    S = Image.new("RGB", (1600, 1180), hex2rgb("#111316"))
    d = ImageDraw.Draw(S)
    f = font("FiraSans-Bold.ttf", 34)
    d.text((40, 30), name, font=f, fill=(240, 240, 240))
    b = bn.resize((1520, 855))
    S.paste(b, (40, 90))
    k = 1520 / 2560
    sx0, sy0 = 40 + (2560 - SAFE_W) / 2 * k, 90 + (1440 - SAFE_H) / 2 * k
    d.rectangle((sx0, sy0, sx0 + SAFE_W * k, sy0 + SAFE_H * k), outline=(255, 80, 80), width=2)
    fs = font("FiraSans-Bold.ttf", 22)
    d.text((sx0 + 6, sy0 - 28), "área que aparece em todas as telas", font=fs, fill=(255, 120, 120))
    a = av.resize((200, 200))
    mask = Image.new("L", (200, 200), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 199, 199), fill=255)
    S.paste(a, (40, 965), mask)
    d.text((260, 1040), "foto de perfil", font=fs, fill=(200, 200, 200))
    frame = _radial(360, 200, "#3a3f46", "#1d2024").convert("RGB")
    frame.paste(wm, (360 - 160, 200 - 160), wm)
    S.paste(frame, (560, 965))
    d.text((940, 1040), "marca d'água sobre o vídeo", font=fs, fill=(200, 200, 200))
    pal = [th[k] for k in ("bg_center", "bg_edge", "gold", "gold_light", "card", "ink", "caption_hi")]
    for i, c in enumerate(pal):
        d.rounded_rectangle((1240 + i * 46, 1000, 1280 + i * 46, 1040), 6, fill=hex2rgb(c))
    return S


def render_kit(theme: dict[str, Any] | None, name: str, handle: str, out_dir: Path, tagline: str = "") -> dict[str, Path]:
    th = _theme(theme)
    out_dir.mkdir(parents=True, exist_ok=True)
    av, bn, wm = avatar(th, name), banner(th, name, handle, tagline), watermark(th, name)
    paths = {"avatar": out_dir / "foto_perfil_800.png", "banner": out_dir / "capa_2560x1440.jpg",
             "watermark": out_dir / "marca_dagua_150.png", "sheet": out_dir / "_revisao.jpg"}
    av.save(paths["avatar"])
    bn.save(paths["banner"], quality=93)
    wm.save(paths["watermark"])
    sheet(av, bn, wm, th, name).save(paths["sheet"], quality=90)
    return paths


def channel_kit(channel_id: int) -> dict[str, str]:
    """Gera o kit de um canal já conectado em data/media/<slug>/marca/."""
    from .config import MEDIA_DIR
    from .db import session
    from .models import Channel
    with session() as s:
        ch = s.get(Channel, channel_id)
        name, handle, theme, slug = ch.name, ch.handle or "", dict(ch.theme or {}), ch.slug
    paths = render_kit(theme, name, handle, MEDIA_DIR / slug / "marca")
    return {k: f"/media/{slug}/marca/{p.name}" for k, p in paths.items()}
