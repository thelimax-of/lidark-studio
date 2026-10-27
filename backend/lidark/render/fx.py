"""Arsenal de animações: entradas/saídas de imagem, movimentos de câmera, carimbos, partículas.

Cada vídeo recebe uma "direção" própria (sorteada com semente) para nunca ficar repetitivo.
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from .core import clamp, ease_in_out, ease_out_back, ease_out_cubic, font, rgba, supersampled

ENTERS = ["pop", "slide_left", "slide_right", "drop", "flip", "develop", "zoom_reveal", "iris", "stamp_in", "blur_in", "rise"]
MOTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "float"]
ENTER_DUR = {"pop": 0.4, "slide_left": 0.45, "slide_right": 0.45, "drop": 0.6, "flip": 0.45, "develop": 0.9,
             "zoom_reveal": 1.1, "iris": 0.55, "stamp_in": 0.28, "blur_in": 0.5, "rise": 0.5}
EXIT_DUR = 0.3

YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-2][0-9])\b")
MYTH_WORDS = ("maioria acredita", "todo mundo acha", "todos acham", "dizem que", "mito", "lenda", "muita gente pensa",
              "você aprendeu", "aprendemos na escola", "se acredita")
TRUTH_WORDS = ("na verdade", "na real", "a verdade", "o que aconteceu de fato", "realidade", "mas não", "só que não")


@dataclass
class ScenePlan:
    enter: str
    motion: str
    exit: str
    badge: str = ""        # "" | mito | verdade
    year: str = ""         # carimbo de data
    react: str = ""        # reação do mascote: surprise | happy | wave
    focus: tuple[float, float] = (0.5, 0.42)


def plan_scenes(scenes, seed: int) -> list[ScenePlan]:
    rng = random.Random(seed)
    plans: list[ScenePlan] = []
    recent: list[str] = []
    prev_img = None
    for i, sc in enumerate(scenes):
        txt = sc.text.lower()
        fx = (getattr(sc, "fx", "") or "").lower()
        if getattr(sc, "graphic", None):
            enter = "graphic"
        elif sc.image is prev_img and i > 0 and not getattr(scenes[i - 1], "graphic", None):
            enter = "none"
        else:
            pool = [e for e in ENTERS if e not in recent[-3:]]
            enter = rng.choice(pool)
            recent.append(enter)
        prev_img = sc.image
        motion = rng.choice(MOTIONS)
        exit_ = {"slide_left": "out_left", "slide_right": "out_right", "drop": "out_down", "rise": "out_up"}.get(
            enter, rng.choice(["shrink", "out_left", "out_right", "out_down"]))
        badge = "mito" if (fx == "mito" or any(w in txt for w in MYTH_WORDS)) else \
            "verdade" if (fx == "verdade" or any(w in txt for w in TRUTH_WORDS)) else ""
        m = YEAR_RE.search(sc.text)
        year = m.group(1) if (m and i > 0) else ""
        if getattr(sc, "graphic", None):
            gk = sc.graphic.get("kind")
            year = ""
            badge = "" if gk == "versus" else badge
        react = "surprise" if badge == "verdade" else ""
        plans.append(ScenePlan(enter, motion, exit_, badge, year, react,
                               (rng.uniform(0.35, 0.65), rng.uniform(0.3, 0.5))))
    return plans


# ================================================================ entrada / saída

def apply_enter(img: Image.Image, kind: str, p: float) -> tuple[Image.Image | None, float, float, float]:
    """Retorna (imagem transformada, dx, dy, opacidade). p ∈ [0,1] progresso da entrada."""
    if kind in ("none", "") or p >= 1:
        return img, 0, 0, 1
    w, h = img.size
    if kind == "pop":
        s = 0.55 + 0.45 * ease_out_back(p)
        return _scale(img, s), 0, 0, clamp(p * 4)
    if kind == "slide_left":
        e = ease_out_cubic(p)
        return _rot(img, 6 * (1 - e)), -(1 - e) * w * 1.3, 0, 1
    if kind == "slide_right":
        e = ease_out_cubic(p)
        return _rot(img, -6 * (1 - e)), (1 - e) * w * 1.3, 0, 1
    if kind == "rise":
        e = ease_out_back(p, 1.2)
        return img, 0, (1 - e) * h * 0.9, clamp(p * 3)
    if kind == "drop":
        # foto caindo na mesa: vem de cima girada e "quica"
        e = _bounce(p)
        return _rot(img, -9 * (1 - ease_out_cubic(p)) + 1.2 * math.sin(p * 9) * (1 - p)), 0, -(1 - e) * h * 1.2, clamp(p * 5)
    if kind == "flip":
        sx = abs(math.cos(math.pi / 2 * (1 - ease_out_cubic(p))))
        nw = max(2, int(w * sx))
        im = img.resize((nw, h), Image.BILINEAR)
        if p < 0.5:
            im = _darken(im, 0.5 * (1 - p * 2))
        return im, 0, 0, 1
    if kind == "develop":
        # foto revelando: do branco/sépia até a cor original
        return _develop(img, ease_in_out(p)), 0, 0, clamp(p * 6)
    if kind == "blur_in":
        r = 14 * (1 - ease_out_cubic(p))
        im = img.filter(ImageFilter.GaussianBlur(r)) if r > 0.6 else img
        return _scale(im, 1.06 - 0.06 * ease_out_cubic(p)), 0, 0, clamp(p * 3)
    if kind == "iris":
        return _iris(img, ease_out_cubic(p)), 0, 0, 1
    if kind == "stamp_in":
        e = ease_out_cubic(p)
        return _scale(img, 1.5 - 0.5 * e), 0, 0, clamp(p * 2.5)
    # zoom_reveal é tratado no recorte (zoom interno), aqui só aparece
    return img, 0, 0, clamp(p * 5)


def apply_exit(img: Image.Image, kind: str, p: float, W: int) -> tuple[Image.Image | None, float, float, float]:
    e = ease_in_out(p) if kind == "shrink" else p * p
    w, h = img.size
    if kind == "out_left":
        return _rot(img, -5 * e), -e * W, 0, 1 - e * 0.3
    if kind == "out_right":
        return _rot(img, 5 * e), e * W, 0, 1 - e * 0.3
    if kind == "out_down":
        return _rot(img, 7 * e), 0, e * h * 1.6, 1 - e
    if kind == "out_up":
        return img, 0, -e * h * 1.5, 1 - e
    return _scale(img, 1 - 0.45 * e), 0, 0, 1 - e


def motion_params(kind: str, p: float, focus: tuple[float, float]) -> tuple[float, tuple[float, float], float]:
    """(zoom, foco, rotação) do recorte interno da imagem durante a cena (Ken Burns variado)."""
    e = ease_in_out(p)
    fx, fy = focus
    if kind == "zoom_in":
        return 1.0 + 0.12 * e, focus, 0
    if kind == "zoom_out":
        return 1.14 - 0.12 * e, focus, 0
    if kind == "pan_left":
        return 1.12, (0.62 - 0.24 * e, fy), 0
    if kind == "pan_right":
        return 1.12, (0.38 + 0.24 * e, fy), 0
    return 1.05, (fx + 0.02 * math.sin(p * 6), fy), 0.6 * math.sin(p * 5)


# ================================================================ carimbos e partículas

@lru_cache(maxsize=32)
def stamp(text: str, color: str, size: int, angle: float, face: str = "Cinzel.ttf") -> Image.Image:
    """Carimbo de tinta com textura irregular (estilo documento antigo)."""
    f = font(face, size, 900)
    tw = f.getlength(text)
    w, h = int(tw + size * 1.1), int(size * 1.75)

    def draw(d: ImageDraw.ImageDraw, ss: float):
        c = rgba(color)
        lw = max(3, int(size * 0.09)) * ss
        d.rounded_rectangle((lw, lw, (w - 1) * ss - lw, (h - 1) * ss - lw), int(size * 0.18 * ss), outline=c, width=int(lw))
        ins = size * 0.16 * ss + lw
        d.rounded_rectangle((ins, ins, w * ss - ins, h * ss - ins), int(size * 0.12 * ss), outline=c, width=int(lw * 0.45))
        d.text((w / 2 * ss, h / 2 * ss + size * 0.05 * ss), text, font=font(face, int(size * ss), 900), fill=c, anchor="mm")
    img = supersampled(w, h, draw, 2)
    # textura de tinta falhada
    rng = np.random.default_rng(len(text) * 7 + size)
    noise = rng.random((h, w))
    noise = Image.fromarray((noise > 0.22).astype(np.uint8) * 255, "L").filter(ImageFilter.GaussianBlur(0.8))
    a = ImageChops.multiply(img.getchannel("A"), noise.point(lambda v: 90 + int(v * 165 / 255)))
    img.putalpha(a)
    return img.rotate(angle, resample=Image.BICUBIC, expand=True)


def stamp_anim(img: Image.Image, p: float) -> tuple[Image.Image | None, float]:
    """Carimbo batendo: grande e transparente → tamanho final com impacto. Retorna (img, opacidade)."""
    if p <= 0:
        return None, 0
    e = ease_out_cubic(clamp(p / 0.35))
    s = 2.0 - 1.0 * e
    return _scale(img, s), clamp(p / 0.2)


class Particles:
    """Poeira dourada flutuando (sutil, dá profundidade e sensação premium)."""

    def __init__(self, W: int, H: int, n: int = 34, seed: int = 3, color=(242, 200, 98)):
        rng = random.Random(seed)
        self.W, self.H = W, H
        self.p = [(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(8, 26), rng.uniform(0.5, 1.6), rng.uniform(0, 6.28),
                   rng.choice([0, 1, 1, 2])) for _ in range(n)]
        self.sprites = [self._sprite(r, color) for r in (5, 8, 12)]

    @staticmethod
    def _sprite(r: int, color) -> Image.Image:
        s = r * 4
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(img).ellipse((s / 2 - r / 2, s / 2 - r / 2, s / 2 + r / 2, s / 2 + r / 2), fill=(*color, 255))
        return img.filter(ImageFilter.GaussianBlur(r / 2.2))

    def draw(self, out: Image.Image, t: float) -> None:
        for x0, y0, speed, tw, ph, si in self.p:
            y = (y0 - speed * t) % self.H
            x = x0 + 14 * math.sin(t * 0.4 + ph)
            a = 0.25 + 0.35 * (0.5 + 0.5 * math.sin(t * tw + ph))
            sp = self.sprites[si]
            if a > 0.05:
                m = sp.getchannel("A").point(lambda v, a=a: int(v * a))
                out.paste(sp, (int(x - sp.width / 2), int(y - sp.height / 2)), m)


# ================================================================ utilidades

def _scale(img: Image.Image, s: float) -> Image.Image:
    if abs(s - 1) < 0.004:
        return img
    return img.resize((max(2, int(img.width * s)), max(2, int(img.height * s))), Image.BILINEAR)


def _rot(img: Image.Image, deg: float) -> Image.Image:
    if abs(deg) < 0.05:
        return img
    return img.rotate(deg, resample=Image.BICUBIC, expand=True)


def _bounce(p: float) -> float:
    p = clamp(p)
    if p < 0.6:
        return ease_out_cubic(p / 0.6) * 1.0
    q = (p - 0.6) / 0.4
    return 1 - 0.06 * math.sin(math.pi * q) * (1 - q)


def _darken(img: Image.Image, k: float) -> Image.Image:
    a = img.getchannel("A")
    rgb = img.convert("RGB").point(lambda v: int(v * (1 - k)))
    rgb.putalpha(a)
    return rgb


def _develop(img: Image.Image, p: float) -> Image.Image:
    a = img.getchannel("A")
    rgb = img.convert("RGB")
    sep = ImageOps.colorize(ImageOps.grayscale(rgb), (60, 40, 20), (250, 236, 210))
    white = Image.new("RGB", rgb.size, (250, 244, 232))
    if p < 0.5:
        mix = Image.blend(white, sep, p * 2)
    else:
        mix = Image.blend(sep, rgb, (p - 0.5) * 2)
    mix.putalpha(a)
    return mix


def _iris(img: Image.Image, p: float) -> Image.Image:
    w, h = img.size
    r = math.hypot(w, h) / 2 * p
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).ellipse((w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r), fill=255)
    out = img.copy()
    out.putalpha(ImageChops.multiply(img.getchannel("A"), m))
    return out
