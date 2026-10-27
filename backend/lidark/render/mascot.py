"""Mascote do Ouro do Passado: relógio de bolso animado.

Fiel ao original: boca pequena que alterna sorriso / risco / "D" com língua no ritmo das sílabas
(com tempo mínimo de permanência para não tremer), piscadas e piscadelas, braço direito acenando
para cima, braço esquerdo pendurado, leve balanço e inclinação do corpo. Ganha reações:
surpresa (olhos arregalados + boca "O" + pulo), feliz (olhos ^^), aceno.
"""
from __future__ import annotations

import math
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from .core import font

INK = (22, 26, 24, 255)
GOLD = (233, 186, 82, 255)
GOLD_DARK = (190, 136, 38, 255)
GOLD_LIGHT = (250, 216, 128, 255)
FACE = (246, 236, 218, 255)
BODY = (205, 88, 58, 255)
CHEEK = (236, 166, 150, 170)
MOUTH = (110, 28, 26, 255)
TONGUE = (226, 96, 92, 255)
GLOVE = (236, 234, 228, 255)
GLOVE_LINE = (120, 120, 116, 255)
SS = 2

# estados de boca
SMILE, FLAT, OPEN_S, OPEN_M, O_SHAPE = 0, 1, 2, 3, 4


def plan_mouth(envelope: np.ndarray, fps: int) -> np.ndarray:
    """Converte o volume da voz em uma sequência de bocas com histerese e permanência mínima."""
    n = len(envelope)
    out = np.zeros(n, np.int8)
    hold_min = max(2, int(fps * 0.075))
    state, held, silence = SMILE, 0, 99
    for i in range(n):
        v = float(envelope[i])
        silence = silence + 1 if v < 0.12 else 0
        if silence > fps * 0.18:
            target = SMILE
        elif v < 0.22:
            target = FLAT
        elif v < 0.55:
            target = OPEN_S
        else:
            target = OPEN_M
        held += 1
        if target != state and held >= hold_min:
            if abs(target - state) > 1 and state != SMILE and target != SMILE:
                target = state + (1 if target > state else -1)
            state, held = target, 0
        out[i] = state
    return out


class ClockMascot:
    def __init__(self, radius: int = 230, seed: int = 0):
        self.R = radius
        self.w = int(radius * 3.7)
        self.h = int(radius * 3.0)
        self.cx = self.w * 0.5
        self.cy = radius * 1.38
        self.rng = np.random.default_rng(seed)
        self.face_dy = 0.0      # deslocamento vertical do rosto (fração de R)
        self.face_scale = 1.0   # escala dos traços do rosto
        self.has_hands = True   # ponteiros do relógio
        self.shoulder = 0.9     # distância dos ombros (fração de R)
        self._configure()
        self._static = self._draw_static()
        # piscadas em tempos irregulares + algumas piscadelas
        self.blinks: list[tuple[float, str]] = []
        t = 0.8
        while t < 900:
            kind = "wink" if self.rng.random() < 0.18 else "blink"
            self.blinks.append((t, kind))
            t += float(self.rng.uniform(2.2, 5.0))

    def _configure(self) -> None:
        """Subclasses ajustam rosto/ombros antes de desenhar."""

    # ================================================================ partes fixas

    def _draw_static(self) -> Image.Image:
        R, s = self.R * SS, SS
        cx, cy = self.cx * s, self.cy * s
        img = Image.new("RGBA", (self.w * s, self.h * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        ow = int(R * 0.03)
        kw, kh = R * 0.34, R * 0.12
        ky = cy - R * 1.14
        d.rectangle((cx - R * 0.07, ky + kh * 0.7, cx + R * 0.07, cy - R * 0.95), fill=GOLD_DARK, outline=INK, width=int(ow * 0.7))
        d.rounded_rectangle((cx - kw / 2, ky, cx + kw / 2, ky + kh), int(R * 0.03), fill=GOLD_LIGHT, outline=INK, width=int(ow * 0.8))
        for i in range(1, 7):
            x = cx - kw / 2 + kw * i / 7
            d.line((x, ky + kh * 0.25, x, ky + kh * 0.75), fill=GOLD_DARK, width=max(2, int(R * 0.012)))
        d.ellipse((cx - R + R * 0.06, cy - R + R * 0.09, cx + R + R * 0.06, cy + R + R * 0.09), fill=BODY, outline=INK, width=ow)
        d.ellipse((cx - R, cy - R, cx + R, cy + R), fill=GOLD, outline=INK, width=ow)
        d.ellipse((cx - R * 0.95, cy - R * 0.96, cx + R * 0.9, cy + R * 0.88), fill=GOLD_LIGHT)
        d.ellipse((cx - R * 0.92, cy - R * 0.91, cx + R * 0.92, cy + R * 0.93), fill=GOLD)
        fr = R * 0.8
        d.ellipse((cx - fr, cy - fr, cx + fr, cy + fr), fill=FACE, outline=INK, width=int(ow * 0.8))
        for k in range(60):
            if k in (0, 15, 45):
                continue
            a = math.radians(k * 6 - 90)
            big = k % 5 == 0
            r1, r2 = fr * (0.87 if big else 0.93), fr * 0.975
            d.line((cx + r1 * math.cos(a), cy + r1 * math.sin(a), cx + r2 * math.cos(a), cy + r2 * math.sin(a)),
                   fill=INK, width=max(1, int(R * (0.014 if big else 0.007))))
        f = font("Cinzel.ttf", int(R * 0.105), 800)
        for txt, ang in (("XII", -90), ("III", 0), ("IX", 180)):
            a = math.radians(ang)
            d.text((cx + fr * 0.76 * math.cos(a), cy + fr * 0.76 * math.sin(a)), txt, font=f, fill=INK, anchor="mm")
        return img.resize((self.w, self.h), Image.LANCZOS)

    # ================================================================ rosto

    @lru_cache(maxsize=512)
    def _face(self, mouth: int, eyes: str, hand_q: int) -> Image.Image:
        R, s = self.R * SS * self.face_scale, SS
        cx, cy = self.cx * s, (self.cy + self.face_dy * self.R) * s
        img = Image.new("RGBA", (self.w * s, self.h * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        lw = max(2, int(R * 0.016))
        wig = (hand_q - 2) * 1.2
        for ang, ln, wd in () if not self.has_hands else ((-38 + wig, 0.42, 0.045), (32 - wig * 0.5, 0.56, 0.04)):
            a = math.radians(ang) - math.pi / 2
            x2, y2 = cx + R * ln * math.cos(a), cy + R * ln * math.sin(a)
            nx, ny = -math.sin(a) * R * wd, math.cos(a) * R * wd
            d.polygon([(cx + nx, cy + ny), (x2, y2), (cx - nx, cy - ny)], fill=GOLD, outline=INK, width=lw)
        if self.has_hands:
            d.ellipse((cx - R * 0.045, cy - R * 0.045, cx + R * 0.045, cy + R * 0.045), fill=GOLD, outline=INK, width=lw)
        ex, ey = R * 0.27, cy - R * 0.01
        ew, eh = R * 0.075, R * 0.115
        if eyes == "surprise":
            ew, eh = R * 0.09, R * 0.14
        for side in (-1, 1):
            x = cx + side * ex
            closed = eyes == "closed" or (eyes == "wink" and side == 1)
            if eyes == "happy":
                d.arc((x - ew * 1.1, ey - eh * 0.6, x + ew * 1.1, ey + eh * 0.9), 200, 340, fill=INK, width=int(lw * 2.2))
            elif closed:
                d.line((x - ew * 1.1, ey + eh * 0.15, x + ew * 1.1, ey + eh * 0.15), fill=INK, width=int(lw * 2))
            else:
                h = eh * (0.5 if eyes == "half" else 1)
                d.ellipse((x - ew, ey - h, x + ew, ey + h), fill=INK)
                hr = ew * 0.38
                d.ellipse((x + ew * 0.05, ey - h * 0.62, x + ew * 0.05 + hr * 1.6, ey - h * 0.62 + hr * 1.6), fill=(255, 255, 255, 255))
        for side in (-1, 1):
            x, y = cx + side * R * 0.43, cy + R * 0.13
            d.ellipse((x - R * 0.095, y - R * 0.055, x + R * 0.095, y + R * 0.055), fill=CHEEK)
        my, mw = cy + R * 0.3, R * 0.13
        if mouth == SMILE:
            d.arc((cx - mw, my - R * 0.1, cx + mw, my + R * 0.05), 22, 158, fill=INK, width=int(lw * 1.6))
        elif mouth == FLAT:
            d.arc((cx - mw * 0.9, my - R * 0.035, cx + mw * 0.9, my + R * 0.03), 10, 170, fill=INK, width=int(lw * 1.7))
        elif mouth == O_SHAPE:
            d.ellipse((cx - mw * 0.45, my - R * 0.03, cx + mw * 0.45, my + R * 0.11), fill=MOUTH, outline=INK, width=lw)
        else:
            oh = R * (0.055 if mouth == OPEN_S else 0.085)
            w = mw * (1.0 if mouth == OPEN_S else 1.05)
            d.chord((cx - w, my - oh, cx + w, my + oh), 0, 180, fill=MOUTH, outline=INK, width=lw)
            tw = w * 0.5
            d.chord((cx - tw, my + oh * 0.3, cx + tw, my + oh * 1.3), 180, 360, fill=TONGUE)
            d.line((cx - w, my, cx + w, my), fill=INK, width=int(lw * 1.2))
        return img.resize((self.w, self.h), Image.LANCZOS)

    # ================================================================ braços

    @lru_cache(maxsize=1024)
    def _arms(self, right: int, left: int) -> Image.Image:
        R, s = self.R * SS, SS
        cx, cy = self.cx * s, self.cy * s
        img = Image.new("RGBA", (self.w * s, self.h * s), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        lw = int(R * 0.034)
        for side, ang in ((1, right), (-1, left)):
            sx, sy = cx + side * R * self.shoulder, cy + R * 0.18
            L = R * 0.95
            a = math.radians(ang)
            hx, hy = sx + side * L * math.cos(a) * 0.75, sy - L * math.sin(a)
            bend = R * 0.28 * (1 if ang > 0 else -1)
            mx, my = sx + side * R * 0.32, (sy + hy) / 2 + bend * 0.4
            pts = [((1 - u) ** 2 * sx + 2 * (1 - u) * u * mx + u * u * hx,
                    (1 - u) ** 2 * sy + 2 * (1 - u) * u * my + u * u * hy) for u in np.linspace(0, 1, 24)]
            d.line(pts, fill=INK, width=lw, joint="curve")
            gr = R * 0.105
            d.ellipse((hx - gr, hy - gr, hx + gr, hy + gr), fill=GLOVE, outline=INK, width=int(lw * 0.55))
            for k in (-1, 0, 1):
                d.line((hx - gr * 0.42, hy + k * gr * 0.3 - gr * 0.14, hx + gr * 0.42, hy + k * gr * 0.3 + gr * 0.14),
                       fill=GLOVE_LINE, width=max(2, int(lw * 0.3)))
        return img.resize((self.w, self.h), Image.BILINEAR)

    # ================================================================ quadro

    def eyes_at(self, t: float, mood: str) -> str:
        if mood in ("surprise", "happy"):
            return mood
        for bt, kind in self.blinks:
            if bt > t + 0.2:
                break
            dt = t - bt
            if 0 <= dt < 0.14:
                if kind == "wink":
                    return "wink" if dt < 0.12 else "open"
                return "half" if dt < 0.03 or dt > 0.1 else "closed"
        return "open"

    def frame(self, t: float, mouth: int, talk: float, mood: str = "normal",
              mood_k: float = 0.0, mirror: bool = False) -> tuple[Image.Image, tuple[float, float]]:
        """mood: normal | surprise | happy | wave ; mood_k ∈ [0,1] intensidade."""
        if mood == "surprise" and mood_k > 0.3:
            mouth = O_SHAPE
        eyes = self.eyes_at(t, mood if mood_k > 0.3 else "normal")
        hand_q = int((t * 2) % 2 * 2) + 1
        wave = 0.5 + 0.5 * math.sin(t * 2.4)
        right = 15 + 50 * wave + 12 * talk
        left = -62 + 8 * math.sin(t * 1.3 + 0.7)
        if mood == "point":
            right = 58 + 5 * math.sin(t * 3.2) + 6 * talk
        if mood == "wave":
            right = 55 + 25 * math.sin(t * 9) * mood_k + 10 * (1 - mood_k)
        if mood == "surprise":
            right += 25 * mood_k
            left += 70 * mood_k
        out = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        arms = self._arms(int(round(right / 2) * 2), int(round(left / 2) * 2))
        if mirror:  # só os braços viram (o mostrador continua legível)
            arms = arms.transpose(Image.FLIP_LEFT_RIGHT)
        out.alpha_composite(arms)
        out.alpha_composite(self._static)
        out.alpha_composite(self._face(int(mouth), eyes, hand_q))
        tilt = 2.2 * math.sin(t * 1.15) + (4 * math.sin(t * 20) * mood_k if mood == "surprise" else 0)
        if abs(tilt) > 0.15:
            out = out.rotate(tilt, resample=Image.BICUBIC, center=(self.cx, self.cy))
        dy = math.sin(t * 2 * math.pi * 0.85) * self.R * 0.022 - talk * self.R * 0.02
        if mood == "surprise":
            dy -= self.R * 0.18 * math.sin(math.pi * min(1.0, mood_k))
        return out, (0.0, dy)
