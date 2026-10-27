"""Biblioteca de mascotes: cada canal ganha um personagem próprio, com o mesmo motor de animação do Tic
(boca sincronizada com a voz, piscadas/piscadelas, braços que acenam e apontam, reações, pulos).

Use `make_mascot(theme, R, seed)`; o tipo vem de theme["mascot"] e as cores de theme["mascot_color"]/["mascot_accent"].
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from .core import hex2rgb
from .mascot import INK, SS, ClockMascot

KINDS = {
    "clock": "Relógio de bolso (história, tempo, curiosidades do passado)",
    "book": "Livro (educação, ENEM, literatura, história)",
    "planet": "Planeta com anel (espaço, astronomia, ciência)",
    "magnifier": "Lupa (mistérios, crimes reais, investigação)",
    "bulb": "Lâmpada (curiosidades, fatos, ideias, 'você sabia')",
    "brain": "Cérebro (psicologia, mente, comportamento, ciência)",
    "coin": "Moeda (finanças, economia, dinheiro, negócios)",
    "globe": "Globo terrestre (geografia, países, viagens, culturas)",
    "ghost": "Fantasminha (terror, paranormal, lendas urbanas)",
    "flask": "Frasco de laboratório (ciência, química, experimentos)",
    "ball": "Bola de futebol (futebol, Copas, craques, histórias da bola)",
    "trophy": "Troféu (esportes em geral, campeões, recordes, Olimpíadas)",
    "none": "Sem mascote",
}

DEFAULT_COLORS = {
    "clock": ("#e9ba52", "#cd583a"), "book": ("#2f6db5", "#f3e7c9"), "planet": ("#e98a3c", "#f2d27a"),
    "magnifier": ("#3b3f46", "#bfe3f2"), "bulb": ("#ffe27a", "#9aa3ad"), "brain": ("#f2a3b3", "#d97b90"),
    "coin": ("#f2c14e", "#c8922a"), "globe": ("#3a8fd6", "#5cbf6a"), "ghost": ("#f5f3ff", "#c9c2f0"),
    "flask": ("#dff3f2", "#38c172"), "ball": ("#f7f7f2", "#1d2024"), "trophy": ("#f2c14e", "#2f6b3a"),
}


def _rgba(h: str, a: int = 255):
    return (*hex2rgb(h), a)


def _shade(c, k: float):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3]) + (255,)


class CharacterMascot(ClockMascot):
    def __init__(self, kind: str, color: str, accent: str, radius: int = 230, seed: int = 0):
        self.kind = kind
        self.col = _rgba(color)
        self.acc = _rgba(accent)
        super().__init__(radius, seed)

    def _configure(self) -> None:
        self.has_hands = False
        cfg = {"book": (0.05, 1.1, 0.78), "planet": (-0.2, 1.15, 0.92), "magnifier": (-0.12, 1.05, 0.86),
               "bulb": (-0.12, 1.15, 0.82), "brain": (0.05, 1.15, 0.95), "coin": (0.0, 1.2, 0.92),
               "globe": (0.0, 1.15, 0.92), "ghost": (-0.05, 1.2, 0.82), "flask": (0.22, 1.0, 0.72),
               "ball": (0.05, 1.1, 0.92), "trophy": (-0.28, 0.95, 0.8)}
        self.face_dy, self.face_scale, self.shoulder = cfg.get(self.kind, (0.0, 1.1, 0.9))
        self.w = int(self.R * 4.0) if self.kind == "planet" else self.w
        self.cx = self.w * 0.5

    def _draw_static(self) -> Image.Image:
        R, s = self.R * SS, SS
        cx, cy = self.cx * s, self.cy * s
        img = Image.new("RGBA", (self.w * s, self.h * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        ow = int(R * 0.03)
        getattr(self, f"_body_{self.kind}")(d, img, cx, cy, R, ow)
        return img.resize((self.w, self.h), Image.LANCZOS)

    # ---------------------------------------------------------------- corpos

    def _body_book(self, d, img, cx, cy, R, ow):
        w, h = R * 1.42, R * 1.9
        x0, y0 = cx - w / 2, cy - h / 2
        d.rounded_rectangle((x0 + R * 0.08, y0 + R * 0.06, x0 + w + R * 0.1, y0 + h + R * 0.06), int(R * 0.1), fill=(245, 236, 214, 255), outline=INK, width=ow)
        for i in range(1, 5):  # páginas
            yy = y0 + R * 0.06 + h * i / 5
            d.line((x0 + w - R * 0.02, yy, x0 + w + R * 0.08, yy), fill=(190, 178, 150, 255), width=max(2, ow // 2))
        d.rounded_rectangle((x0, y0, x0 + w, y0 + h), int(R * 0.1), fill=self.col, outline=INK, width=ow)
        d.rectangle((x0 + ow, y0 + ow, x0 + R * 0.22, y0 + h - ow), fill=_shade(self.col, 0.72))
        d.line((x0 + R * 0.22, y0 + ow, x0 + R * 0.22, y0 + h - ow), fill=INK, width=max(2, ow // 2))
        d.rounded_rectangle((cx - R * 0.5, cy - R * 0.42, cx + R * 0.6, cy + R * 0.55), int(R * 0.08), fill=self.acc, outline=INK, width=max(2, ow // 2))
        d.line((cx - R * 0.35, y0 + R * 0.2, cx + R * 0.45, y0 + R * 0.2), fill=_shade(self.acc, 0.9), width=ow)

    def _body_planet(self, d, img, cx, cy, R, ow):
        ring = _shade(self.acc, 1.0)
        d.ellipse((cx - R * 1.42, cy - R * 0.35, cx + R * 1.42, cy + R * 0.42), outline=INK, width=int(R * 0.16))
        d.ellipse((cx - R * 1.39, cy - R * 0.32, cx + R * 1.39, cy + R * 0.39), outline=ring, width=int(R * 0.1))
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=self.col, outline=INK, width=ow)
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).ellipse((cx - R + ow, cy - R + ow, cx + R - ow, cy + R - ow), fill=255)
        bands = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(bands)
        for k, yy in enumerate((-0.62, -0.3, 0.55, 0.78)):
            bd.rectangle((0, cy + yy * R, img.width, cy + (yy + 0.1 + 0.04 * k) * R), fill=_shade(self.col, 0.85 if k % 2 else 1.12))
        img.paste(bands, (0, 0), Image.composite(bands.getchannel("A"), Image.new("L", img.size, 0), mask))
        # frente do anel (metade de baixo passa na frente do planeta)
        d.arc((cx - R * 1.42, cy - R * 0.35, cx + R * 1.42, cy + R * 0.42), 10, 170, fill=INK, width=int(R * 0.16))
        d.arc((cx - R * 1.39, cy - R * 0.32, cx + R * 1.39, cy + R * 0.39), 12, 168, fill=ring, width=int(R * 0.1))

    def _body_magnifier(self, d, img, cx, cy, R, ow):
        a = math.radians(45)
        hx0, hy0 = cx + R * 0.72 * math.cos(a), cy + R * 0.72 * math.sin(a)
        hx1, hy1 = cx + R * 1.45 * math.cos(a), cy + R * 1.45 * math.sin(a)
        d.line((hx0, hy0, hx1, hy1), fill=INK, width=int(R * 0.34))
        d.line((hx0, hy0, hx1, hy1), fill=(140, 92, 52, 255), width=int(R * 0.26))
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=self.col, outline=INK, width=ow)
        g = R * 0.8
        d.ellipse((cx - g, cy - g, cx + g, cy + g), fill=self.acc, outline=INK, width=max(2, ow // 2))
        d.arc((cx - g * 0.8, cy - g * 0.8, cx + g * 0.8, cy + g * 0.8), 200, 250, fill=(255, 255, 255, 255), width=int(R * 0.06))

    def _body_bulb(self, d, img, cx, cy, R, ow):
        d.rounded_rectangle((cx - R * 0.42, cy + R * 0.72, cx + R * 0.42, cy + R * 1.18), int(R * 0.08), fill=self.acc, outline=INK, width=ow)
        for k in range(3):
            yy = cy + R * (0.82 + 0.12 * k)
            d.line((cx - R * 0.42, yy, cx + R * 0.42, yy), fill=_shade(self.acc, 0.7), width=max(2, ow // 2))
        d.polygon([(cx - R * 0.5, cy + R * 0.45), (cx + R * 0.5, cy + R * 0.45), (cx + R * 0.42, cy + R * 0.76), (cx - R * 0.42, cy + R * 0.76)],
                  fill=self.col, outline=INK)
        d.ellipse((cx - R * 0.95, cy - R * 1.12, cx + R * 0.95, cy + R * 0.7), fill=self.col, outline=INK, width=ow)
        d.arc((cx - R * 0.7, cy - R * 0.9, cx + R * 0.7, cy + R * 0.5), 200, 245, fill=(255, 255, 255, 255), width=int(R * 0.07))

    def _body_brain(self, d, img, cx, cy, R, ow):
        rng = np.random.default_rng(5)
        lobes = [(-0.5, -0.45, 0.55), (0.1, -0.62, 0.55), (0.55, -0.35, 0.5), (-0.65, 0.15, 0.5), (0.65, 0.2, 0.5),
                 (-0.25, 0.5, 0.55), (0.3, 0.5, 0.55), (0.0, -0.05, 0.75)]
        for x, y, r in lobes:
            d.ellipse((cx + (x - r) * R, cy + (y - r) * R, cx + (x + r) * R, cy + (y + r) * R), fill=INK)
        for x, y, r in lobes:
            r2 = r - 0.035
            d.ellipse((cx + (x - r2) * R, cy + (y - r2) * R, cx + (x + r2) * R, cy + (y + r2) * R), fill=self.col)
        for _ in range(9):  # dobras
            x, y = rng.uniform(-0.8, 0.8), rng.uniform(-0.9, 0.85)
            if abs(x) < 0.45 and -0.3 < y < 0.5:
                continue
            d.arc((cx + (x - 0.2) * R, cy + (y - 0.12) * R, cx + (x + 0.2) * R, cy + (y + 0.12) * R),
                  rng.uniform(0, 180), rng.uniform(200, 340), fill=self.acc, width=max(3, ow // 2))
        d.line((cx, cy - R * 1.05, cx, cy - R * 0.55), fill=self.acc, width=max(3, ow // 2))

    def _body_coin(self, d, img, cx, cy, R, ow):
        d.ellipse((cx - R + R * 0.08, cy - R + R * 0.06, cx + R + R * 0.08, cy + R + R * 0.06), fill=self.acc, outline=INK, width=ow)
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=self.col, outline=INK, width=ow)
        d.ellipse((cx - R * 0.86, cy - R * 0.86, cx + R * 0.86, cy + R * 0.86), outline=self.acc, width=max(3, ow // 2))
        for i in range(36):
            a = math.radians(i * 10)
            x, y = cx + R * 0.93 * math.cos(a), cy + R * 0.93 * math.sin(a)
            d.ellipse((x - R * 0.025, y - R * 0.025, x + R * 0.025, y + R * 0.025), fill=self.acc)
        d.arc((cx - R * 0.75, cy - R * 0.75, cx + R * 0.75, cy + R * 0.75), 200, 250, fill=(255, 250, 220, 255), width=int(R * 0.06))

    def _body_globe(self, d, img, cx, cy, R, ow):
        d.arc((cx - R * 1.15, cy - R * 1.15, cx + R * 1.15, cy + R * 1.15), 100, 260, fill=INK, width=int(R * 0.1))
        d.arc((cx - R * 1.15, cy - R * 1.15, cx + R * 1.15, cy + R * 1.15), 102, 258, fill=(150, 110, 60, 255), width=int(R * 0.06))
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=self.col, outline=INK, width=ow)
        rng = np.random.default_rng(11)
        for bx, by, br in ((-0.45, -0.45, 0.32), (0.4, -0.3, 0.38), (-0.35, 0.5, 0.3), (0.5, 0.55, 0.22), (0.0, -0.85, 0.18)):
            pts = []
            for k in range(14):
                a = 2 * math.pi * k / 14
                rr = br * R * rng.uniform(0.7, 1.15)
                pts.append((cx + bx * R + rr * math.cos(a), cy + by * R + rr * math.sin(a) * 0.8))
            d.polygon(pts, fill=self.acc)
        for k in (-0.5, 0, 0.5):
            d.arc((cx - R * abs(k) - R * 0.15, cy - R, cx + R * abs(k) + R * 0.15, cy + R), 0, 360, fill=_shade(self.col, 0.85), width=max(2, ow // 3))
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=INK, width=ow)

    def _body_ghost(self, d, img, cx, cy, R, ow):
        top = cy - R * 1.05
        pts = [(cx - R * 0.95, cy)]
        for k in range(7):
            x = cx - R * 0.95 + R * 1.9 * k / 6
            pts.append((x, cy + R * (1.05 if k % 2 == 0 else 0.82)))
        pts.append((cx + R * 0.95, cy))
        d.polygon(pts, fill=self.col, outline=INK)
        d.ellipse((cx - R * 0.95, top, cx + R * 0.95, top + R * 1.9), fill=self.col, outline=INK, width=ow)
        d.rectangle((cx - R * 0.95 + ow, cy - R * 0.1, cx + R * 0.95 - ow, cy + R * 0.82), fill=self.col)
        d.line((cx - R * 0.95, cy - R * 0.05, cx - R * 0.95, cy + R * 1.0), fill=INK, width=ow)
        d.line((cx + R * 0.95, cy - R * 0.05, cx + R * 0.95, cy + R * 1.0), fill=INK, width=ow)
        d.line(pts[1:-1], fill=INK, width=ow, joint="curve")
        d.ellipse((cx + R * 0.35, top + R * 0.25, cx + R * 0.65, top + R * 0.45), fill=self.acc)

    def _body_flask(self, d, img, cx, cy, R, ow):
        neck_w, top = R * 0.38, cy - R * 1.15
        body = [(cx - neck_w / 2, top + R * 0.15), (cx + neck_w / 2, top + R * 0.15), (cx + neck_w / 2, cy - R * 0.35),
                (cx + R * 1.0, cy + R * 0.95), (cx - R * 1.0, cy + R * 0.95), (cx - neck_w / 2, cy - R * 0.35)]
        d.polygon(body, fill=self.col)
        liq = Image.new("L", img.size, 0)
        ImageDraw.Draw(liq).polygon(body, fill=255)
        fill = Image.new("RGBA", img.size, (0, 0, 0, 0))
        fd = ImageDraw.Draw(fill)
        fd.rectangle((0, cy - R * 0.05, img.width, img.height), fill=self.acc)
        for bx, by, br in ((-0.4, 0.4, 0.08), (0.2, 0.25, 0.06), (0.45, 0.6, 0.1), (-0.1, 0.7, 0.05)):
            fd.ellipse((cx + (bx - br) * R, cy + (by - br) * R, cx + (bx + br) * R, cy + (by + br) * R), fill=(255, 255, 255, 140))
        img.paste(fill, (0, 0), Image.composite(fill.getchannel("A"), Image.new("L", img.size, 0), liq))
        d.line(body + [body[0]], fill=INK, width=ow, joint="curve")
        d.rounded_rectangle((cx - neck_w * 0.75, top, cx + neck_w * 0.75, top + R * 0.18), int(R * 0.05), fill=self.col, outline=INK, width=ow)

    def _body_ball(self, d, img, cx, cy, R, ow):
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=self.col, outline=INK, width=ow)
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).ellipse((cx - R + ow, cy - R + ow, cx + R - ow, cy + R - ow), fill=255)
        patches = Image.new("RGBA", img.size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(patches)
        seam = _shade(self.col, 0.6)
        pent = []
        for k in range(5):  # gomos pretos na borda (o centro fica livre para o rosto) + costuras dos hexágonos
            a = math.radians(-90 + 72 * k + 36)
            px, py = cx + R * 0.86 * math.cos(a), cy + R * 0.86 * math.sin(a)
            pts = [(px + R * 0.27 * math.cos(a + math.radians(72 * j)), py + R * 0.27 * math.sin(a + math.radians(72 * j)))
                   for j in range(5)]
            pent.append(pts)
            pd.polygon(pts, fill=self.acc)
        for k in range(5):
            p1, p2 = pent[k], pent[(k + 1) % 5]
            m1 = max(p1, key=lambda q: -math.hypot(q[0] - p2[0][0], q[1] - p2[0][1]))
            m2 = min(p2, key=lambda q: math.hypot(q[0] - m1[0], q[1] - m1[1]))
            pd.line((m1, m2), fill=seam, width=max(2, ow // 2))
            pd.line((m1, (cx + (m1[0] - cx) * 0.62, cy + (m1[1] - cy) * 0.62)), fill=seam, width=max(2, ow // 2))
        img.paste(patches, (0, 0), Image.composite(patches.getchannel("A"), Image.new("L", img.size, 0), mask))
        d.arc((cx - R * 0.8, cy - R * 0.8, cx + R * 0.8, cy + R * 0.8), 200, 245, fill=(255, 255, 255, 255), width=int(R * 0.06))
        d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=INK, width=ow)

    def _body_trophy(self, d, img, cx, cy, R, ow):
        top, rim = cy - R * 1.05, R * 1.0
        for sgn in (-1, 1):  # alças
            box = (cx + sgn * R * 0.9 - R * 0.4, cy - R * 0.9, cx + sgn * R * 0.9 + R * 0.4, cy - R * 0.1)
            d.arc(box, 270 if sgn > 0 else 90, 90 if sgn > 0 else 270, fill=INK, width=int(R * 0.2))
            d.arc(box, 270 if sgn > 0 else 90, 90 if sgn > 0 else 270, fill=self.col, width=int(R * 0.12))
        d.rounded_rectangle((cx - R * 0.62, cy + R * 0.95, cx + R * 0.62, cy + R * 1.2), int(R * 0.05), fill=self.acc, outline=INK, width=ow)
        d.rectangle((cx - R * 0.42, cy + R * 0.8, cx + R * 0.42, cy + R * 0.97), fill=_shade(self.col, 0.8), outline=INK, width=ow)
        d.polygon([(cx - R * 0.14, cy + R * 0.3), (cx + R * 0.14, cy + R * 0.3), (cx + R * 0.24, cy + R * 0.82), (cx - R * 0.24, cy + R * 0.82)],
                  fill=_shade(self.col, 0.85), outline=INK)
        d.chord((cx - rim, top - R * 1.25, cx + rim, top + R * 1.45), 0, 180, fill=self.col, outline=INK, width=ow)
        d.rounded_rectangle((cx - rim - R * 0.06, top - R * 0.1, cx + rim + R * 0.06, top + R * 0.08), int(R * 0.04), fill=_shade(self.col, 1.12), outline=INK, width=ow)
        d.arc((cx - R * 0.8, top - R * 0.4, cx + R * 0.5, top + R * 1.3), 120, 165, fill=(255, 250, 225, 255), width=int(R * 0.06))


def make_mascot(theme: dict, radius: int, seed: int = 0) -> ClockMascot | None:
    kind = (theme or {}).get("mascot", "clock")
    if kind in ("", "none", None):
        return None
    if kind == "clock":
        return ClockMascot(radius, seed)
    if kind not in DEFAULT_COLORS:
        kind = "bulb"
    c, a = DEFAULT_COLORS[kind]
    return CharacterMascot(kind, theme.get("mascot_color") or c, theme.get("mascot_accent") or a, radius, seed)


def preview(kind: str, color: str | None = None, accent: str | None = None, size: int = 360, bg: str = "#16473a") -> Image.Image:
    """Miniatura do mascote (para a galeria do painel)."""
    m = make_mascot({"mascot": kind, "mascot_color": color, "mascot_accent": accent}, 150, 1)
    canvas = Image.new("RGBA", (size, size), (*hex2rgb(bg), 255))
    if m is None:
        return canvas
    img, _ = m.frame(0.4, 2, 0.5, "point", 1.0)
    img.thumbnail((size, size), Image.LANCZOS)
    canvas.alpha_composite(img, ((size - img.width) // 2, (size - img.height) // 2))
    return canvas
