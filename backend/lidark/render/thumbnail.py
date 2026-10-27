"""Miniatura (thumbnail) feita para clique: melhor foto do vídeo + texto de impacto + mascote surpreso."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .characters import make_mascot
from .core import fit_cover, font, hex2rgb, wrap


def _gradient(w: int, h: int, color: tuple[int, int, int], vertical: bool) -> Image.Image:
    """Escurece o lado do texto (esquerda no horizontal, topo no vertical)."""
    g = Image.new("L", (w if not vertical else 1, h if vertical else 1))
    n = h if vertical else w
    for i in range(n):
        v = (1 - i / n) if vertical else i / n  # vertical: escurece a parte de baixo (o rosto fica no alto)
        a = int(240 * max(0.0, 1 - v / (0.58 if vertical else 0.7)) ** 1.25)
        g.putpixel((0, i) if vertical else (i, 0), a)
    mask = g.resize((w, h), Image.BILINEAR)
    layer = Image.new("RGBA", (w, h), (*color, 255))
    layer.putalpha(mask)
    return layer


def _map_box(img: Image.Image, w: int, h: int, zoom: float, focus: tuple[float, float],
             box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Converte uma caixa normalizada da imagem original para a posição na miniatura (mesma conta do fit_cover)."""
    from .core import clamp
    s = max(w / img.width, h / img.height) * zoom
    cw, ch = w / s, h / s
    cx = clamp(focus[0] * img.width, cw / 2, img.width - cw / 2)
    cy = clamp(focus[1] * img.height, ch / 2, img.height - ch / 2)
    x0, y0 = cx - cw / 2, cy - ch / 2
    return ((box[0] * img.width - x0) * s, (box[1] * img.height - y0) * s,
            (box[2] * img.width - x0) * s, (box[3] * img.height - y0) * s)


def make_thumbnail(background: Image.Image | None, text: str, theme: dict, out: Path, vertical: bool,
                   variant: int = 0, subject: tuple[float, float, float, float] | None = None, ring: bool = False) -> Path:
    """variant muda o layout; subject (caixa normalizada do assunto principal) faz o texto e o mascote
    nunca cobrirem o assunto, e ring desenha um círculo de destaque em volta dele."""
    """variant muda o layout (lado do texto, destaque, faixa, mascote) para as miniaturas não saírem em série."""
    W, H = (1080, 1920) if vertical else (1280, 720)
    th = theme or {}
    flip = bool(variant & 1)          # horizontal: texto à direita · vertical: texto no topo
    band = bool(variant & 2)          # palavra-destaque numa faixa colorida
    no_mascot = variant % 5 == 4      # de vez em quando, só foto + texto
    pick_last = bool(variant & 4)     # destaca a última palavra em vez da mais longa
    dark = hex2rgb(th.get("bg_edge", "#061915"))
    zoom, focus = 1.06, (0.5, 0.62 if (vertical and flip) else 0.4)
    sbox = None
    if subject and background is not None:
        sx, sy = (subject[0] + subject[2]) / 2, (subject[1] + subject[3]) / 2
        if vertical:
            flip = sy > 0.5  # assunto embaixo → texto em cima
            focus = (sx, sy)
        else:
            flip = sx < 0.5  # assunto à esquerda → texto à direita
            focus = (sx, 0.5 if (subject[3] - subject[1]) > 0.6 else sy)
        sbox = _map_box(background, W, H, zoom, focus, subject)
    if background is not None:
        img = fit_cover(background, W, H, zoom=zoom, focus=focus).convert("RGBA")
    else:
        img = Image.new("RGBA", (W, H), (*hex2rgb(th.get("bg_center", "#16473a")), 255))
    # contraste e vinheta
    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 60)))
    grad = _gradient(W, H, dark, vertical)
    if flip:
        grad = ImageOps.flip(grad) if vertical else ImageOps.mirror(grad)
    img.alpha_composite(grad)
    d = ImageDraw.Draw(img)
    hi0 = hex2rgb(th.get("caption_hi") or th.get("gold", "#e9b440"))
    if ring and sbox:  # círculo de destaque em volta do assunto (aumenta o clique)
        x1, y1, x2, y2 = sbox
        pad = 0.12 * max(x2 - x1, y2 - y1)
        x1, y1, x2, y2 = max(8, x1 - pad), max(8, y1 - pad), min(W - 8, x2 + pad), min(H - 8, y2 + pad)
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((x1, y1, x2, y2), outline=(*hi0, 200), width=30)
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14)))
        d.ellipse((x1, y1, x2, y2), outline=(*hi0, 255), width=12)

    words = (text or "").upper().split()[:5] or ["VOCÊ", "SABIA?"]
    title_font = th.get("font_title", "Cinzel.ttf")
    hi = hex2rgb(th.get("caption_hi") or th.get("gold", "#e9b440"))
    box_w = W * (0.9 if vertical else 0.6)
    size = 210 if vertical else 132
    while size > 50:
        f = font(title_font, size, 900)
        lines = wrap(f, " ".join(words), box_w)
        if len(lines) <= (4 if vertical else 3) and all(f.getlength(l) <= box_w for l in lines):
            break
        size -= 6
    f = font(title_font, size, 900)
    lines = wrap(f, " ".join(words), box_w)
    lh = size * 1.08
    x0 = W * 0.06
    if vertical:
        y = (H * 0.10 if flip else H * 0.86 - len(lines) * lh) + lh / 2
    else:
        y = H / 2 - len(lines) * lh / 2 + lh / 2
    hi_word = words[-1] if pick_last else max(words, key=len)  # destaca a palavra mais forte
    stroke = max(4, size // 14)
    for ln in lines:
        x = (W - x0 - f.getlength(ln) if flip else x0) if not vertical else W / 2 - f.getlength(ln) / 2
        for wd in ln.split():
            color = (*hi, 255) if wd == hi_word else (255, 255, 255, 255)
            if band and wd == hi_word:
                bw = f.getlength(wd)
                d.rounded_rectangle((x - size * 0.12, y - lh * 0.5, x + bw + size * 0.12, y + lh * 0.46), radius=int(size * 0.12), fill=(*hi, 255))
                color = (12, 12, 16, 255)
            if not (band and wd == hi_word):
                d.text((x + 6, y + 8), wd, font=f, fill=(0, 0, 0, 170), anchor="lm")
            d.text((x, y), wd, font=f, fill=color, anchor="lm", stroke_width=stroke, stroke_fill=(10, 10, 14, 255))
            x += f.getlength(wd + " ")
        y += lh

    # mascote surpreso no canto
    m = None if no_mascot else make_mascot(th, 150, 7)
    if m is not None:
        mi, _ = m.frame(0.5, 4, 0.0, "surprise", 1.0)
        mi = mi.crop(mi.getbbox())
        target_h = H * (0.2 if vertical else 0.62)
        s = min(target_h / mi.height, (W * (0.42 if vertical else 0.34)) / mi.width)  # nunca invade o texto
        mi = mi.resize((int(mi.width * s), int(mi.height * s)), Image.LANCZOS)
        glow = Image.new("RGBA", mi.size, (0, 0, 0, 0))
        glow.putalpha(mi.getchannel("A").filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.6)))
        mx = int(W * 0.02) if (flip and not vertical) else int(W - mi.width - W * 0.02)
        if vertical:  # longe do texto, no canto
            my = int(H * 0.62) if flip else int(H * 0.52 - mi.height)
        else:
            my = int(H - mi.height - H * 0.02)
        if sbox and not (mx + mi.width < sbox[0] or mx > sbox[2] or my + mi.height < sbox[1] or my > sbox[3]):
            mi = None  # o mascote cobriria o assunto: fica de fora desta miniatura
    if m is not None and mi is not None:
        img.alpha_composite(glow, (mx, my + 10))
        img.alpha_composite(mi, (mx, my))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out, quality=90)
    return out
