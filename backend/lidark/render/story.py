"""Render do Modo História (motion comic com HUD de jogo): PIL desenha os quadros → FFmpeg (h264_nvenc) codifica.

Entrada: o "spec" montado pelo diretor (lidark/story/director.py) — tomadas com fundo, personagens recortados,
câmera, efeitos e widgets — e as falas já sintetizadas. Nada aqui chama IA: é determinístico e rápido
(~1 s de render por 1 s de vídeo num Short 720x1280 no notebook).

Animação:
- câmera virtual por tomada (keys [t, cx, cy, z] no "palco"), cortes de punch-in, drift tipo Ken Burns,
  tremida nos impactos, chicote (whip) e dissolve entre tomadas
- camadas: fundo × personagens com paralaxe (o fundo anda/zoom menos), respiração/balanço, entrada (desliza/pop),
  pulo nos impactos, piscar e olhar para o lado (olhos de ponto detectados), fala balança no ritmo da voz
- efeitos: poeira, fumaça, chuva, brasas/fogo, vela tremendo, alarme vermelho, flash, estrelas, bolhas, confete, noite
- acabamento: gradação da série (aplicada uma vez nas imagens), vinheta + granulação pré-calculadas
Áudio: falas (multi-voz), trilha gerada (pad + drone tenso, com ducking), SFX sintetizados, -14 LUFS (2 passadas).
"""
from __future__ import annotations

import logging
import math
import random
import subprocess
import time
import wave
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ..media import ffmpeg_exe, video_encoder_args
from . import story_hud as HUD

log = logging.getLogger("lidark.render.story")
SR = 48000


# ================================================================ gradação e variantes de olhos

def grade(im: Image.Image, kind: str) -> Image.Image:
    """Gradação de cor da série — aplicada uma vez por imagem (não por quadro)."""
    if kind in ("", "none", None):
        return im
    mats = {
        "sepia": (1.04, 0.04, 0.0, 4, 0.02, 0.98, 0.0, 2, 0.0, 0.05, 0.88, -4),
        "cool": (0.94, 0.0, 0.04, -4, 0.0, 0.98, 0.04, 0, 0.0, 0.04, 1.08, 8),
        "warm": (1.06, 0.02, 0.0, 6, 0.0, 1.0, 0.0, 2, 0.0, 0.0, 0.92, -6),
        "clean": (1.02, 0.0, 0.0, 2, 0.0, 1.02, 0.0, 2, 0.0, 0.0, 1.02, 2),
    }
    m = mats.get(kind)
    if not m:
        return im
    if im.mode == "RGBA":
        a = im.getchannel("A")
        out = im.convert("RGB").convert("RGB", m)
        out.putalpha(a)
        return out
    return im.convert("RGB").convert("RGB", m)


def eye_variant(im: Image.Image, eyes: dict[str, Any] | None, mode: str) -> Image.Image:
    """mode: closed (piscar) | left | right (pupila desviada). Olhos de ponto: pinta a pele por cima e redesenha."""
    if not eyes or mode == "open":
        return im
    out = im.copy()
    d = ImageDraw.Draw(out)
    r = float(eyes["r"])
    skin = tuple(eyes.get("skin") or ()) or None
    for ex, ey in eyes["eyes"]:
        if skin is None:
            px = out.getpixel((int(min(out.width - 1, ex + r * 2.4)), int(ey)))
            sk = px[:3]
        else:
            sk = skin[:3]
        fill = sk + ((255,) if out.mode == "RGBA" else ())
        d.ellipse((ex - r - 2.5, ey - r - 2.5, ex + r + 2.5, ey + r + 2.5), fill=fill)
        ink = (40, 30, 25) + ((255,) if out.mode == "RGBA" else ())
        if mode == "closed":
            d.line((ex - r * 1.1, ey + 1, ex + r * 1.1, ey + 1), fill=ink, width=max(2, int(r / 3)))
        else:
            dx = (-1 if mode == "left" else 1) * r * 0.55
            d.ellipse((ex + dx - r * 0.85, ey - r * 0.85, ex + dx + r * 0.85, ey + r * 0.85), fill=ink)
    return out


def tint(im: Image.Image, k: float, color: tuple) -> Image.Image:
    """im*k + cor*(1-k) por tabela (LUT) — bem mais rápido que Image.blend em quadro cheio."""
    k = max(0.0, min(1.0, k))
    table = []
    for c in color[:3]:
        table += [int(v * k + c * (1 - k)) for v in range(256)]
    if im.mode == "RGBA":
        table += list(range(256))
    return im.point(table)


# ================================================================ fontes de imagem (cache por render)

class Src:
    """Imagem de fundo pronta para a câmera: cover-fit no palco (SW x SH ≥ quadro) + variantes de olhos."""

    def __init__(self, path: str, W: int, H: int, grade_kind: str, eyes: dict[str, Any] | None = None) -> None:
        im = Image.open(path)
        im.load()
        im = grade(im.convert("RGB"), grade_kind)
        s = max(W / im.width, H / im.height)
        self.s = s
        self.SW, self.SH = im.width * s, im.height * s
        self.im = im
        self.eyes = eyes
        self.var: dict[str, Image.Image] = {"open": im}

    def get(self, mode: str) -> Image.Image:
        if mode not in self.var:
            self.var[mode] = eye_variant(self.im, self.eyes, mode)
        return self.var[mode]

    def eyes_stage(self) -> tuple[float, float] | None:
        if not self.eyes:
            return None
        (x0, y0), (x1, y1) = self.eyes["eyes"]
        return ((x0 + x1) / 2 * self.s, (y0 + y1) / 2 * self.s)


class Cut:
    """Personagem recortado (RGBA aparado) com variantes de olhos e cache de tamanhos."""

    def __init__(self, path: str, grade_kind: str, eyes: dict[str, Any] | None) -> None:
        im = Image.open(path)
        im.load()
        self.im = grade(im.convert("RGBA"), grade_kind)
        self.eyes = eyes
        self.var: dict[str, Image.Image] = {"open": self.im}
        self.sized: dict[tuple, Image.Image] = {}

    def at(self, mode: str, h: int, flip: bool) -> Image.Image:
        key = (mode, h, flip)
        c = self.sized.get(key)
        if c is None:
            if mode not in self.var:
                self.var[mode] = eye_variant(self.im, self.eyes, mode)
            base = self.var[mode]
            w = max(1, int(base.width * h / base.height))
            c = base.resize((w, max(1, h)), Image.BILINEAR)
            if flip:
                c = c.transpose(Image.FLIP_LEFT_RIGHT)
            if len(self.sized) > 160:
                self.sized.clear()
            self.sized[key] = c
        return c


# ================================================================ efeitos

class FX:
    def __init__(self, W: int, H: int, seed: int) -> None:
        self.W, self.H = W, H
        rng = np.random.default_rng(seed)
        self.dust = rng.random((70, 4))
        self.embers = rng.random((40, 4))
        self.stars = rng.random((90, 3))
        self.bubbles = rng.random((26, 4))
        self.confetti = rng.random((70, 5))
        sm = []
        for k in range(3):
            m = Image.new("L", (260, 260), 0)
            ImageDraw.Draw(m).ellipse((40, 40, 220, 220), fill=110 - k * 20)
            sm.append(m.filter(ImageFilter.GaussianBlur(38)))
        self.smoke = []
        for m in sm:
            lay = Image.new("RGBA", m.size, (190, 180, 165, 0))
            lay.putalpha(m)
            self.smoke.append(lay)
        self._rain: Image.Image | None = None
        self._glow: Image.Image | None = None

    def rain(self) -> Image.Image:
        if self._rain is None:
            r = Image.new("RGBA", (self.W, self.H * 2), (0, 0, 0, 0))
            d = ImageDraw.Draw(r)
            rng = random.Random(5)
            for _ in range(int(self.W * self.H / 2600)):
                x, y = rng.uniform(0, self.W), rng.uniform(0, self.H * 2)
                ln = rng.uniform(18, 46)
                d.line((x, y, x - ln * 0.18, y + ln), fill=(200, 215, 235, rng.randint(50, 120)), width=1 + (rng.random() < 0.2))
            self._rain = r
        return self._rain

    def glow(self) -> Image.Image:
        if self._glow is None:
            g = Image.new("L", (1, 256))
            for y in range(256):
                g.putpixel((0, y), int(150 * (y / 255) ** 2.2))
            g = g.resize((self.W, self.H))
            lay = Image.new("RGBA", (self.W, self.H), (255, 120, 30, 0))
            lay.putalpha(g)
            self._glow = lay
        return self._glow

    def apply(self, base: Image.Image, now: float, lt: float, fx: list[str], impacts: list[float]) -> Image.Image:
        W, H = self.W, self.H
        if "night" in fx:
            base = tint(base, 0.62, (8, 12, 30))
        if "flicker" in fx or "candle" in fx:
            fl = 0.82 + 0.1 * math.sin(now * 13) + 0.06 * math.sin(now * 29 + 1)
            base = tint(base, fl, (10, 4, 2))
        if "fire" in fx:
            g = self.glow()
            a = 0.6 + 0.25 * math.sin(now * 9) + 0.15 * math.sin(now * 23)
            base.alpha_composite(HUD.fade(g, max(0.0, min(1.0, a))))
        if "alarm" in fx:
            pulse = 0.5 + 0.5 * math.sin(lt * 7)
            base.alpha_composite(Image.new("RGBA", (W, H), (200, 20, 10, int(60 * pulse))))
        d = ImageDraw.Draw(base, "RGBA")
        if "stars" in fx:
            for x, y, s in self.stars:
                tw = 0.5 + 0.5 * math.sin(now * (1 + 3 * s) + s * 20)
                rr = 0.8 + 1.6 * s
                d.ellipse((x * W - rr, y * H - rr, x * W + rr, y * H + rr), fill=(230, 240, 255, int(60 + 180 * tw)))
        if "dust" in fx or not fx:
            for x, y, s, ph in self.dust:
                px = (x * W + 25 * math.sin(now * 0.6 + ph * 6)) % W
                py = (y * H - now * (12 + 25 * s)) % H
                rr = 1 + 2.5 * s
                d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=(255, 236, 200, int(40 + 70 * s)))
        if "embers" in fx or "fire" in fx:
            for x, y, s, ph in self.embers:
                px = (x * W + 30 * math.sin(now * 1.3 + ph * 6)) % W
                py = H - ((y * H + now * (60 + 90 * s)) % H)
                rr = 1.5 + 2.5 * s
                d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=(255, 170, 60, int(120 + 120 * s)))
        if "bubbles" in fx:
            for x, y, s, ph in self.bubbles:
                px = (x * W + 18 * math.sin(now * 2 + ph * 6)) % W
                py = H - ((y * H + now * (40 + 60 * s)) % H)
                rr = 4 + 12 * s
                d.ellipse((px - rr, py - rr, px + rr, py + rr), outline=(220, 255, 245, 150), width=2)
        if "confetti" in fx:
            cols = [(239, 182, 48), (31, 107, 58), (200, 55, 45), (243, 231, 201)]
            for x, y, s, ph, c in self.confetti:
                px = (x * W + 40 * math.sin(now * 2 + ph * 6)) % W
                py = (y * H + now * (120 + 140 * s)) % H
                w = 4 + 6 * s
                d.rectangle((px, py, px + w, py + w * 0.5), fill=cols[int(c * 4) % 4] + (230,))
        if "smoke" in fx:
            for k in range(5):
                px = int((140 + k * 130 + now * 14 * (1 + k % 2)) % (W + 200) - 200)
                py = int(H * 0.64 - k * 90 - (now * 22 + k * 50) % 500)
                base.alpha_composite(self.smoke[k % 3], (px, py))
        if "rain" in fx:
            r = self.rain()
            off = int((now * 1400) % H)
            base.alpha_composite(r.crop((0, H - off, W, 2 * H - off)))
        for t0 in impacts:
            if "flash" in fx and 0 <= lt - t0 < 0.18:
                base.alpha_composite(Image.new("RGBA", (W, H), (255, 250, 240, int(170 * (1 - (lt - t0) / 0.18)))))
        return base


# ================================================================ quadro

class Renderer:
    def __init__(self, spec: dict[str, Any]) -> None:
        self.spec = spec
        self.W, self.H = int(spec["W"]), int(spec["H"])
        self.fps = int(spec.get("fps", 30))
        self.grade = spec.get("grade", "")
        self.hud = HUD.Hud(self.W, self.H, spec.get("hud") or {})
        self.fx = FX(self.W, self.H, int(spec.get("seed", 1)))
        self.shots = spec["shots"]
        self.total = float(spec["duration"])
        self.srcs: dict[str, Src] = {}
        self.cuts: dict[str, Cut] = {}
        self.portraits: dict[str, Image.Image] = {}
        self.env = spec.get("_env")  # envelope da voz por quadro (fala balança personagem)
        W, H = self.W, self.H
        rng = random.Random(int(spec.get("seed", 1)))
        vig = Image.radial_gradient("L").resize((W, H)).point(lambda v: int(min(255, v * 1.1) * 0.55))
        self.overlays = []
        for k in range(4):
            g = Image.effect_noise((W, H), 18).convert("L").point(lambda v: v // 10)
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            dark.putalpha(vig)
            lay.alpha_composite(dark)
            grain = Image.new("RGBA", (W, H), (255, 240, 210, 255))
            grain.putalpha(g)
            lay.alpha_composite(grain)
            self.overlays.append(lay)
        self.blink_phase = rng.uniform(0, 2.0)

    # --------------------------------------------------------- recursos
    def src(self, bg: dict[str, Any]) -> Src:
        k = bg["file"]
        if k not in self.srcs:
            self.srcs[k] = Src(k, self.W, self.H, self.grade, bg.get("eyes"))
        return self.srcs[k]

    def cut(self, c: dict[str, Any]) -> Cut:
        k = c["file"]
        if k not in self.cuts:
            self.cuts[k] = Cut(k, self.grade, c.get("eyes"))
        return self.cuts[k]

    def portrait(self, path: str) -> Image.Image:
        if path not in self.portraits:
            im = Image.open(path)
            im.load()
            self.portraits[path] = grade(im.convert("RGBA"), self.grade)
        return self.portraits[path]

    # --------------------------------------------------------- olhos
    def eye_mode(self, now: float, salt: float, look: str = "") -> str:
        period = 3.1 + (salt % 1.3)
        if ((now + self.blink_phase + salt * 0.37) % period) < 0.12:
            return "closed"
        if look in ("left", "right"):
            return look
        return "open"

    # --------------------------------------------------------- câmera
    def camera(self, sh: dict[str, Any], lt: float, S: Src) -> tuple[float, float, float]:
        keys = sh.get("cam") or [[0, S.SW / 2, S.SH / 2, 1.0]]
        k = max(i for i, c in enumerate(keys) if c[0] <= max(lt, 0)) if keys else 0
        _, cx, cy, z = keys[k]
        if k > 0 and lt - keys[k][0] < 0.18:
            a = HUD.ease((lt - keys[k][0]) / 0.18)
            _, px, py, pz = keys[k - 1]
            cx, cy, z = px + (cx - px) * a, py + (cy - py) * a, pz + (z - pz) * a
        seg_end = keys[k + 1][0] if k + 1 < len(keys) else sh["dur"]
        drift = (max(lt, 0) - keys[k][0]) / max(0.5, seg_end - keys[k][0])
        dz = float(sh.get("drift_zoom", 0.06))
        z *= 1 + dz * drift
        pan = sh.get("pan")
        if pan:  # pan contínuo (em px do palco) ao longo da tomada
            f = HUD.ease(lt / max(0.5, sh["dur"])) if sh.get("pan_ease") else max(0.0, min(1.0, lt / max(0.5, sh["dur"])))
            cx += pan[0] * (f - 0.5)
            cy += pan[1] * (f - 0.5)
        for t0 in sh.get("impacts") or []:
            if 0 <= lt - t0 < 0.4:
                amp = 10 * (1 - (lt - t0) / 0.4) * self.W / 720
                cx += amp * math.sin(lt * 90)
                cy += amp * math.cos(lt * 77)
        return cx, cy, z

    def crop(self, S: Src, mode: str, cx: float, cy: float, z: float) -> Image.Image:
        W, H = self.W, self.H
        z = max(1.0, z)
        cw, chh = W / z, H / z
        x0 = min(max(cx - cw / 2, 0), S.SW - cw)
        y0 = min(max(cy - chh / 2, 0), S.SH - chh)
        s = S.s
        box = (x0 / s, y0 / s, (x0 + cw) / s, (y0 + chh) / s)
        return S.get(mode).resize((W, H), Image.BICUBIC if z * s > 1.7 else Image.BILINEAR, box=box)

    # --------------------------------------------------------- tomada
    def shot_frame(self, i: int, now: float) -> Image.Image:
        sh = self.shots[i]
        lt = now - sh["start"]
        S = self.src(sh["bg"])
        cx, cy, z = self.camera(sh, lt, S)
        layered = bool(sh.get("chars"))
        par = float(sh.get("parallax", 0.7)) if layered else 1.0
        # fundo: com personagens em camadas, anda e dá zoom menos que eles (paralaxe)
        bcx = S.SW / 2 + (cx - S.SW / 2) * par
        bcy = S.SH / 2 + (cy - S.SH / 2) * par
        bz = 1 + (z - 1) * (0.75 if layered else 1.0)
        salt = i * 0.71
        base = self.crop(S, self.eye_mode(now, salt, sh["bg"].get("look", "")), bcx, bcy, bz).convert("RGBA")
        boxes: dict[str, tuple] = {}
        if layered:
            self.draw_chars(base, sh, lt, now, cx, cy, z, boxes)
        if sh["bg"].get("eyes") and not layered:
            es = S.eyes_stage()
            if es:
                fx_, fy_ = (es[0] - cx) * z + self.W / 2, (es[1] - cy) * z + self.H / 2
                rr = self.W * 0.28 * z
                boxes["face"] = (fx_ - rr, fy_ - rr * 0.9, fx_ + rr, fy_ + rr * 1.1)
        dim = float(sh.get("dim", 0.0))
        if dim > 0:
            base = tint(base, 1 - dim, (0, 0, 0))
        base = self.fx.apply(base, now, lt, sh.get("fx") or [], sh.get("impacts") or [])
        sh["_boxes"] = boxes
        return base

    def draw_chars(self, base: Image.Image, sh: dict[str, Any], lt: float, now: float, cx: float, cy: float, z: float,
                   boxes: dict[str, tuple]) -> None:
        W, H = self.W, self.H
        S = self.src(sh["bg"])
        sd = ImageDraw.Draw(base, "RGBA")
        for j, c in enumerate(sh["chars"]):
            C = self.cut(c)
            # posição no palco: x (fração da largura do palco), pés em y (fração da altura do palco)
            # em unidades do QUADRO a partir do centro do palco (igual no vertical e no horizontal)
            X = S.SW / 2 + (float(c.get("x", 0.5)) - 0.5) * W
            Y = S.SH / 2 + (float(c.get("y", 0.97)) - 0.5) * H
            hgt = H * float(c.get("h", 0.62))
            # entrada
            ent, k = c.get("enter", "none"), 1.0
            t_in = float(c.get("t_in", 0.0))
            if ent != "none":
                k = (lt - t_in) / 0.42
                if k <= 0:
                    continue
            off_x = 0.0
            scale = 1.0
            if ent in ("slide_l", "slide_r") and k < 1:
                off_x = (1 - HUD.back(k)) * (-1 if ent == "slide_l" else 1) * W * 0.6
            elif ent == "pop" and k < 1:
                scale = max(0.05, HUD.back(k))
            # idle: respiração + balanço; fala: balança com a voz
            ph = j * 1.7 + float(c.get("phase", 0))
            breathe = 1 + 0.012 * math.sin(now * 2 * math.pi / 3.2 + ph)
            bob = 3.0 * math.sin(now * 2 * math.pi / 1.6 + ph) * W / 720
            if c.get("talk") and self.env is not None:
                fi = min(len(self.env) - 1, int(now * self.fps))
                bob -= 8 * float(self.env[fi]) * W / 720
            jump = 0.0
            for t0 in c.get("jumps") or []:
                if 0 <= lt - t0 < 0.38:
                    jump = -math.sin(math.pi * (lt - t0) / 0.38) * hgt * 0.07
            sway = float(c.get("sway", 0.0)) * math.sin(now * 1.1 + ph)
            # câmera
            sx = (X + off_x + sway - cx) * z + W / 2
            sy = (Y + jump - cy) * z + H / 2 + bob
            ph_h = int(hgt * z * scale * breathe / 4) * 4  # quantiza p/ cache
            if ph_h < 8:
                continue
            mode = self.eye_mode(now, j * 1.3 + 0.4, c.get("look", ""))
            img = C.at(mode, ph_h, bool(c.get("flip")))
            x0, y0 = int(sx - img.width / 2), int(sy - img.height)
            # sombra no chão
            if c.get("shadow", True) and not c.get("no_floor"):
                sw = img.width * 0.62
                sd.ellipse((sx - sw / 2, sy - sw * 0.07, sx + sw / 2, sy + sw * 0.07), fill=(0, 0, 0, 70))
            if x0 > W or y0 > H or x0 + img.width < 0 or y0 + img.height < 0:
                continue
            base.alpha_composite(img, (x0, y0)) if (x0 >= 0 and y0 >= 0) else _paste_clip(base, img, x0, y0)
            boxes[f"char:{j}"] = (x0, y0, x0 + img.width, y0 + img.height)
            boxes.setdefault(f"id:{c.get('id', '')}", boxes[f"char:{j}"])

    # --------------------------------------------------------- widgets e quadro final
    def widgets(self, base: Image.Image, now: float, i: int) -> None:
        h = self.hud
        sh = self.shots[i]
        for w in self.spec.get("widgets") or []:
            t0, t1 = float(w["t0"]), float(w["t1"])
            if not (t0 <= now < t1):
                continue
            lt, dur, typ, data = now - t0, t1 - t0, w["type"], w.get("data") or {}
            if typ == "highlight":
                tgt = str(data.get("target", "char:0"))
                HUD.highlight(h, base, lt, dur, data, (sh.get("_boxes") or {}).get(tgt))
            elif typ == "dialogue":
                por = self.portrait(data["portrait"]) if data.get("portrait") else None
                if por is not None and data.get("eyes"):
                    mode = self.eye_mode(now, 5.5)
                    if mode == "closed":
                        por = eye_variant(por, data["eyes"], "closed")
                HUD.dialogue(h, base, lt, dur, data, por)
            else:
                fn = HUD.WIDGETS.get(typ)
                if fn:
                    fn(h, base, lt, dur, data)
        if not self.spec.get("no_clock"):
            HUD.clock(h, base, now, self.spec.get("clock") or {})

    def shot_at(self, now: float) -> int:
        idx = 0
        for i, sh in enumerate(self.shots):
            if sh["start"] <= now:
                idx = i
        return idx

    def frame(self, n: int, hud: bool = True) -> Image.Image:
        now = n / self.fps
        i = self.shot_at(now)
        f = self.shot_frame(i, now)
        sh = self.shots[i]
        nxt = sh["start"] + sh["dur"]
        tr = (self.shots[i + 1].get("transition") if i + 1 < len(self.shots) else None) or "cut"
        if tr == "dissolve" and now > nxt - 0.22:
            g = self.shot_frame(i + 1, now)
            f = Image.blend(f, g, HUD.ease((now - (nxt - 0.22)) / 0.22))
        elif tr == "whip" and now > nxt - 0.12:
            k = (now - (nxt - 0.12)) / 0.12
            f = _whip(f, k, self.W)
        if sh.get("transition") == "whip" and now - sh["start"] < 0.12:
            f = _whip(f, -(1 - (now - sh["start"]) / 0.12), self.W)
        if hud:
            self.widgets(f, now, i)
        f.alpha_composite(self.overlays[n % 4])
        rgb = f.convert("RGB")
        fade_in = float(self.spec.get("fade_in", 0.0))
        if fade_in and now < fade_in:
            rgb = Image.blend(Image.new("RGB", (self.W, self.H)), rgb, HUD.ease(now / fade_in))
        if now > self.total - 0.45:
            rgb = Image.blend(rgb, Image.new("RGB", (self.W, self.H)), HUD.ease((now - (self.total - 0.45)) / 0.45))
        return rgb


def _paste_clip(base: Image.Image, img: Image.Image, x0: int, y0: int) -> None:
    cx0, cy0 = max(0, -x0), max(0, -y0)
    cx1, cy1 = min(img.width, base.width - x0), min(img.height, base.height - y0)
    if cx1 > cx0 and cy1 > cy0:
        base.alpha_composite(img.crop((cx0, cy0, cx1, cy1)), (x0 + cx0, y0 + cy0))


def _whip(f: Image.Image, k: float, W: int) -> Image.Image:
    """Chicote: desloca e borra na horizontal (k em -1..1)."""
    off = int(W * 0.35 * k)
    sm = f.resize((W // 8, f.height // 8), Image.BILINEAR).filter(ImageFilter.BoxBlur(2))
    out = sm.resize(f.size, Image.BILINEAR)
    out = Image.blend(f, out, min(1.0, abs(k) * 1.6))
    if off:
        canvas = Image.new("RGBA", f.size, (0, 0, 0, 255))
        canvas.alpha_composite(out, (-off, 0) if off > 0 else (0, 0), (0, 0) if off > 0 else (-off, 0))
        out = canvas
    return out


# ================================================================ áudio

def _load(path: str | Path) -> np.ndarray:
    raw = subprocess.run([ffmpeg_exe(), "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def _put(buf: np.ndarray, x: np.ndarray, t: float, g: float = 1.0) -> None:
    i = int(max(0.0, t) * SR)
    j = min(len(buf), i + len(x))
    if i < len(buf) and j > i:
        buf[i:j] += x[: j - i] * g


def _synth(kind: str, rng: np.random.Generator) -> np.ndarray:
    if kind == "type":
        n = int(0.012 * SR)
        return (np.exp(-np.arange(n) / (0.002 * SR)) * rng.standard_normal(n) * 0.5).astype(np.float32)
    if kind == "beep":
        t = np.arange(int(0.16 * SR)) / SR
        return (np.sin(2 * np.pi * 880 * t) * np.minimum(1, (0.16 - t) / 0.02) * 0.35).astype(np.float32)
    if kind == "tick":
        n = int(0.02 * SR)
        t = np.arange(n) / SR
        return (np.sin(2 * np.pi * 2400 * t) * np.exp(-t / 0.003) * 0.4).astype(np.float32)
    if kind == "static":
        n = int(0.8 * SR)
        x = rng.standard_normal(n).astype(np.float32)
        x = np.convolve(x, np.ones(6) / 6, "same") * 0.12
        return x * np.minimum(1, np.arange(n) / (0.05 * SR)) * np.minimum(1, (n - np.arange(n)) / (0.2 * SR))
    if kind == "notify":
        t = np.arange(int(0.35 * SR)) / SR
        f = np.where(t < 0.12, 1320, 1760)
        return (np.sin(2 * np.pi * f * t) * np.exp(-((t % 0.12) / 0.08)) * 0.3).astype(np.float32)
    return np.zeros(1, np.float32)


def build_audio(spec: dict[str, Any], out: Path, music_bed: Path | None = None) -> tuple[Path, np.ndarray]:
    """Mix (voz + trilha + efeitos) em WAV 48 kHz; devolve também o envelope da voz por quadro (anima a fala)."""
    from .. import sfx as SFX
    total = float(spec["duration"])
    n = int(total * SR) + SR
    voice, fx, amb = np.zeros(n, np.float32), np.zeros(n, np.float32), np.zeros(n, np.float32)
    rng = np.random.default_rng(int(spec.get("seed", 1)))
    for ln in spec["lines"]:
        _put(voice, _load(ln["audio"]), ln["start"])
    tt = np.arange(n) / SR
    mood = spec.get("music") or {}
    # trilha: pad gerado (music.ambient_track) + drone tenso; cresce no cliffhanger
    music = np.zeros(n, np.float32)
    if music_bed and Path(music_bed).exists():
        bed = _load(music_bed)
        reps = int(math.ceil(n / max(1, len(bed))))
        music += np.tile(bed, reps)[:n] * float(mood.get("bed_gain", 0.55))
    root = float(mood.get("root", 55.0))
    drone = (0.5 * np.sin(2 * np.pi * root * tt) + 0.35 * np.sin(2 * np.pi * root * 1.498 * tt + 0.3 * np.sin(0.2 * tt))
             + 0.25 * np.sin(2 * np.pi * root * 2.005 * tt)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt))
    noise = np.convolve(rng.standard_normal(n).astype(np.float32), np.ones(400) / 400, "same") * 3
    music += (drone + noise).astype(np.float32) * float(mood.get("drone_gain", 0.05))
    music *= np.clip(tt / 1.5, 0, 1) * np.clip((total - tt) / 1.2, 0, 1)
    if spec.get("climax_at"):
        music *= np.where(tt > float(spec["climax_at"]), 1.5, 1.0).astype(np.float32)
    # tic-tac do relógio da missão (tensão) por baixo de tudo, se a série pede
    if mood.get("tick"):
        tk = _synth("tick", rng)
        for t in np.arange(1.0, total - 1.0, 1.0):
            _put(amb, tk, t, 0.18)
    for a in spec.get("ambience") or []:
        if a["kind"] == "rain":
            x = np.convolve(rng.standard_normal(int((a["t1"] - a["t0"]) * SR)).astype(np.float32), np.ones(3) / 3, "same") * 0.05
            x *= np.minimum(1, np.arange(len(x)) / (0.4 * SR)) * np.minimum(1, (len(x) - np.arange(len(x))) / (0.4 * SR))
            _put(amb, x, a["t0"])
        elif a["kind"] == "static":
            _put(amb, _synth("static", rng), a["t0"], 0.8)
        elif a["kind"] == "crowd":
            m = int((a["t1"] - a["t0"]) * SR)
            x = np.convolve(rng.standard_normal(m).astype(np.float32), np.ones(60) / 60, "same") * 1.4
            x *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.3 * np.arange(m) / SR)
            x *= np.minimum(1, np.arange(m) / (0.5 * SR)) * np.minimum(1, (m - np.arange(m)) / (0.5 * SR))
            _put(amb, x.astype(np.float32), a["t0"], 0.6)
    duck = np.convolve((np.abs(voice) > 0.02).astype(np.float32), np.ones(4800) / 4800, "same")
    music *= 1 - 0.55 * np.clip(duck * 3, 0, 1)
    for e in spec.get("sfx") or []:
        k = e["kind"]
        if k in ("whoosh", "impact", "ding", "riser"):
            _put(fx, _load(SFX.sound(k, int(e.get("variant", 0)))), e["t"], float(e.get("gain", 0.4)))
        elif k == "typing":
            click = _synth("type", rng)
            for t in np.arange(e["t"], e["t1"], 0.055):
                _put(fx, click, t, 0.22 * (0.6 + 0.4 * rng.random()))
        elif k == "alarm":
            bp = _synth("beep", rng)
            for t in np.arange(e["t"], e["t1"], 0.5):
                _put(fx, bp, t, float(e.get("gain", 0.3)))
        else:
            _put(fx, _synth(k, rng), e["t"], float(e.get("gain", 0.35)))
    mix = voice + music + fx + amb
    mix = mix[: int(total * SR)]
    mix /= max(1.0, float(np.abs(mix).max()) / 0.95)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    # envelope da voz por quadro (0..1)
    fps = int(spec.get("fps", 30))
    hop = SR // fps
    nf = int(total * fps) + 1
    env = np.zeros(nf, np.float32)
    for i in range(nf):
        seg = voice[i * hop:(i + 1) * hop]
        if len(seg):
            env[i] = float(np.sqrt(np.mean(seg ** 2)))
    ref = float(np.percentile(env[env > 0], 90)) if np.any(env > 0) else 1.0
    env = np.clip(env / max(1e-4, ref), 0, 1)
    return out, env


# ================================================================ encode

def render(spec: dict[str, Any], out: Path, workdir: Path, *, progress=None, check=None, music_bed: Path | None = None,
           gpu: bool = True) -> dict[str, Any]:
    """Áudio → quadros (pipe) → FFmpeg. Segura a trava de GPU (geração local não roda junto)."""
    from ..production import loudnorm_2pass
    from ..config import get as cfg
    workdir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    mix, env = build_audio(spec, workdir / "mix_raw.wav", music_bed)
    loud = loudnorm_2pass(mix, workdir / "mix.wav", float(cfg("loudness_target") or -14.0))
    spec["_env"] = env
    r = Renderer(spec)
    nframes = int(r.total * r.fps)
    upscale = spec.get("output_size")  # ex.: longo desenhado em 1280x720 e entregue em 1920x1080
    vf = ["-vf", f"scale={upscale[0]}:{upscale[1]}:flags=lanczos"] if upscale else []
    args = [ffmpeg_exe(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{r.W}x{r.H}", "-r", str(r.fps),
            "-i", "-", "-i", str(workdir / "mix.wav"), *vf, *video_encoder_args(), "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-movflags", "+faststart", "-shortest", str(out)]

    def encode() -> None:
        p = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            for n in range(nframes):
                if check and n % 30 == 0:
                    check()
                p.stdin.write(r.frame(n).tobytes())
                if progress and n % 45 == 0:
                    progress(n / nframes)
            p.stdin.close()
            err = p.stderr.read().decode(errors="ignore")
            if p.wait() != 0:
                raise RuntimeError("FFmpeg falhou: " + err[-800:])
        except BaseException:
            p.kill()
            raise

    if gpu:
        from ..story.gpu import gpu_lock
        with gpu_lock("render", timeout=1800):
            encode()
    else:
        encode()
    spec.pop("_env", None)
    return {"path": str(out), "frames": nframes, "seconds": round(time.time() - t0, 1), "loudness": loud,
            "fps": r.fps, "size": [r.W, r.H]}


def still(spec: dict[str, Any], t: float, hud: bool = False) -> Image.Image:
    """Um quadro avulso (miniatura/contact sheet)."""
    spec = dict(spec)
    spec.setdefault("_env", None)
    r = Renderer(spec)
    return r.frame(int(t * r.fps), hud=hud)


def thumbnail(spec: dict[str, Any], t: float, text: str, out: Path, part_label: str = "") -> Path:
    """Miniatura: quadro-herói (sem HUD) em 1080x1920 (ou 1920x1080) + texto grande com contorno + selo da parte."""
    im = still(spec, t, hud=False)
    W, H = (1080, 1920) if spec["H"] > spec["W"] else (1920, 1080)
    im = im.resize((W, H), Image.LANCZOS).convert("RGBA")
    h = HUD.Hud(W, H, spec.get("hud") or {})
    d = ImageDraw.Draw(im)
    grad = Image.new("L", (1, 256))
    for y in range(256):
        grad.putpixel((0, y), int(220 * max(0.0, (y - 150) / 105) ** 1.5))
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    dark.putalpha(grad.resize((W, H)))
    im.alpha_composite(dark)
    d = ImageDraw.Draw(im)
    txt = (text or "").upper().strip()
    f = HUD.fit(txt, h.f_title, W - h.s(70), h.s(120), h.s(40))
    lines = HUD.wrap(txt, f, W - h.s(70))[:3]
    y = H * (0.86 if H > W else 0.8) - len(lines) * f.size * 1.05
    for k, ln in enumerate(lines):
        col = h.accent if k == len(lines) - 1 else (255, 255, 255)
        d.text((W / 2, y + k * f.size * 1.08), ln, font=f, fill=col, anchor="mm", stroke_width=h.s(6), stroke_fill=(10, 10, 10))
    if part_label:
        fp = h.F("ui", 30)
        tw = fp.getlength(part_label)
        d.rounded_rectangle((h.s(40), h.s(60), h.s(40) + tw + h.s(40), h.s(118)), h.s(10), fill=h.accent)
        d.text((h.s(60), h.s(89)), part_label, font=fp, fill=(15, 15, 15), anchor="lm")
    out.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(out, quality=92)
    return out
