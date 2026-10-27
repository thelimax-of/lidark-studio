"""Template "Ouro Livre": sem cartão — a tela inteira é o palco.

- Fotos em tela cheia com Ken Burns + vinheta, polaroides flutuando sobre fundo desfocado, ou moldura dourada flutuante
- Infográficos soltos no fundo esmeralda (paleta escura)
- Transições de tela cheia: chicote, zoom, círculo, flash, deslize, fade
- Mascote livre: entra pela lateral, pula entre posições a cada cena (com estica-e-achata), aponta para o conteúdo,
  reage (surpresa/feliz), fala em balões e acena no final
Mantém a identidade do canal (cabeçalho, PASSO x/n, legendas, carimbos, tela final).
"""
from __future__ import annotations

import math
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from . import fx, infographics
from .core import (SceneT, Timeline, clamp, hex2rgb, ease_in_out, ease_out_back, ease_out_cubic, fit_cover, font, paste, rgba,
                   rounded_mask, scaled, shadow, supersampled, wrap)
from .characters import make_mascot
from .ouro import OuroTemplate

TRANS = ["whip", "zoom", "circle", "flash", "slide_up", "fade", "push", "blur", "wipe", "glitch"]
TR_DUR = 0.42
HOP = 0.55


class LivreTemplate(OuroTemplate):
    def __init__(self, tl: Timeline):
        super().__init__(tl)
        W, H, k = self.W, self.H, self.k
        if self.vertical:
            self.card = (int(40 * k), int(175 * k), int(1040 * k), int(1135 * k))
            self.caption_cy = int(1265 * k)
            self.caption_maxw = int(980 * k)
            self.spots = [(0.3, 0.865), (0.7, 0.865), (0.5, 0.87), (0.27, 0.85), (0.73, 0.85)]
            self.base_R = int(205 * k)
        else:
            self.card = (int(60 * k), int(140 * k), int(1260 * k), int(900 * k))
            self.caption_cy = int(985 * k)
            self.caption_maxw = int(1150 * k)
            self.spots = [(0.83, 0.62), (0.8, 0.45), (0.86, 0.7)]
            self.base_R = int(170 * k)
        mk = self.lk.get("mascot") or {}
        self.caption_cy += int(float(self.lk.get("caption_shift", 0)) * k)
        self.base_R = int(self.base_R * float(mk.get("scale", 1.0)))
        side = mk.get("side", "mixed")
        if side in ("left", "right") and len(self.spots) > 3:
            keep = [sp for sp in self.spots if (sp[0] <= 0.5 if side == "left" else sp[0] >= 0.5)]
            self.spots = keep if len(keep) >= 2 else self.spots
        self.mk = mk
        self.mascot_R = self.base_R
        self.mascot = make_mascot(self.th, self.base_R)
        self.vignette = self._vignette()

    # ================================================================ preparação

    def _vignette(self) -> Image.Image:
        W, H = self.W, self.H
        g = Image.new("L", (1, 256))
        for y in range(256):
            v = y / 255
            top = clamp((0.2 - v) / 0.2) ** 1.3 * 200
            bot = clamp((v - 0.55) / 0.45) ** 1.2 * 225
            g.putpixel((0, y), int(max(top, bot)))
        a = g.resize((W, H), Image.BILINEAR)
        v = Image.new("RGBA", (W, H), (*hex2rgb(self.th.get("bg_edge", "#061915")), 255))
        v.putalpha(a)
        return v

    def _setup_direction(self) -> None:
        super()._setup_direction()
        tl, k = self.tl, self.k
        rng = random.Random(sum(ord(c) for c in tl.title) * 7 + 3)
        x1, y1, x2, y2 = self.card
        dark = {**self.th, "_dark": True}
        self.graphics = {}
        for sc in tl.scenes:
            if sc.graphic and sc.graphic.get("kind") in infographics.KINDS:
                self.graphics[sc.index] = infographics.make(sc.graphic["kind"], sc.graphic.get("data") or {},
                                                            x2 - x1, y2 - y1, k, dark, sc.words, sc.start, sc.image)
        self.layouts, self.trans, self.spot_of, self.tilt = [], [], [], []
        last_lay, last_spot = "", -1
        for sc in tl.scenes:
            if sc.index == 0 and len(tl.scenes) > 1:
                lay = "intro"
            elif sc.index in self.graphics:
                lay = "graphic"
            else:
                im = sc.image
                ar = im.width / im.height if im is not None else 1.0
                # tela cheia só para imagens verticais/quadradas com resolução boa (senão o recorte destrói a foto)
                can_full = im is not None and ar <= (1.05 if self.vertical else 2.2) and                     min(im.width, im.height) >= (700 if self.vertical else 600) and (self.vertical or ar >= 1.2)
                opts = ["full", "polaroid", "float", "full"] if can_full else ["polaroid", "float"]
                lay = rng.choice([x for x in opts if x != last_lay] or opts)
            last_lay = lay
            self.layouts.append(lay)
            pool = [x for x in (self.lk.get("transitions") or TRANS) if x in TRANS] or TRANS
            self.trans.append(rng.choice(pool))
            if last_spot >= 0 and rng.random() < float(self.mk.get("stay", 0.0)):
                spot = last_spot  # às vezes fica onde está (menos pulos = ritmo diferente)
            else:
                spot = rng.choice([i for i in range(len(self.spots)) if i != last_spot])
            last_spot = spot
            self.spot_of.append(spot)
            self.tilt.append(rng.uniform(-4, 4))
        # cenas em que o mascote sai de cena (fotos em tela cheia ganham o quadro inteiro)
        self.hidden = set()
        if self.mk.get("hide"):
            for i, lay in enumerate(self.layouts):
                if lay == "full" and 0 < i < len(self.layouts) - 1 and (i - 1) not in self.hidden:
                    self.hidden.add(i)
        # balões de fala do mascote
        self.bubbles: list[tuple[float, float, str]] = []
        for sc, pl in zip(tl.scenes, self.plans):
            if sc.index == 0 and len(tl.scenes) > 1 and sc.text.strip().endswith("?"):
                self.bubbles.append((sc.end - 0.9, sc.end + 0.4, "?!"))
            elif pl.badge == "verdade" or (sc.graphic or {}).get("kind") == "versus":
                self.bubbles.append((sc.start + 0.5, sc.start + 1.9, "Olha isso!"))
            elif pl.badge == "mito":
                self.bubbles.append((sc.start + 0.6, sc.start + 1.8, "Será?"))
        self._frozen: dict[int, Image.Image] = {}

    # ================================================================ conteúdo de cada cena (tela inteira)

    @lru_cache(maxsize=24)
    def _blur_bg(self, idx: int) -> Image.Image:
        sc = self.tl.scenes[idx]
        small = fit_cover(sc.image, self.W // 6, self.H // 6).filter(ImageFilter.GaussianBlur(6))
        big = small.resize((self.W, self.H), Image.BILINEAR).convert("RGBA")
        dark = Image.new("RGBA", (self.W, self.H), (*hex2rgb(self.th.get("bg_edge", "#061915")), 165))
        big.alpha_composite(dark)
        return big

    @lru_cache(maxsize=1)
    def _graphic_shade(self) -> Image.Image:
        return Image.new("RGBA", (self.W, self.H), (*hex2rgb(self.th.get("bg_edge", "#061915")), 70))

    @lru_cache(maxsize=24)
    def _polaroid(self, idx: int) -> Image.Image:
        sc = self.tl.scenes[idx]
        k = self.k
        x1, y1, x2, y2 = self.card
        maxw, maxh = (x2 - x1) * 0.82, (y2 - y1) * 0.72
        ar = clamp(sc.image.width / sc.image.height, 0.7, 1.7)
        w = int(min(maxw, maxh * ar))
        h = int(w / ar)
        b, bb = int(26 * k), int(120 * k)
        card = Image.new("RGBA", (w + 2 * b, h + b + bb), (250, 247, 238, 255))
        card.paste(fit_cover(sc.image, w, h).convert("RGB"), (b, b))
        if sc.label:
            d = ImageDraw.Draw(card)
            d.text((card.width / 2, h + b + bb / 2), sc.label, font=font(self.F_XB, int(44 * k)),
                   fill=(40, 40, 36, 255), anchor="mm")
        pad = int(40 * k)
        out = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
        sh = shadow(card.width, card.height, 4, int(18 * k), 190)
        out.alpha_composite(sh, (pad + card.width // 2 - sh.width // 2, pad + card.height // 2 - sh.height // 2 + int(14 * k)))
        out.alpha_composite(card, (pad, pad))
        # fita adesiva
        tape = Image.new("RGBA", (int(180 * k), int(52 * k)), (238, 226, 190, 200))
        tape = tape.rotate(-6, expand=True)
        out.alpha_composite(tape, (out.width // 2 - tape.width // 2, pad - tape.height // 2))
        return out

    def _content(self, sc: SceneT, t: float) -> Image.Image:
        """Visual da cena (sem cabeçalho/legenda/mascote) em tela cheia."""
        W, H, k = self.W, self.H, self.k
        idx = sc.index
        lay = self.layouts[idx]
        pl = self.plans[idx]
        local = max(0.0, t - sc.start)
        dur = max(0.1, sc.end - sc.start)
        p = clamp(local / dur)
        x1, y1, x2, y2 = self.card
        acx, acy = (x1 + x2) / 2, (y1 + y2) / 2

        if sc.image is None and lay != "graphic":
            lay = "graphic_bg"
        if lay == "graphic_bg":
            out = self.bg.copy()
            self.particles.draw(out, t)
            return out
        if lay == "intro" and self.lk.get("intro", "typed") != "typed":
            return self._intro_alt(sc, t, p)
        if lay == "intro":
            out = fit_cover(sc.image, W, H, zoom=1.08 + 0.12 * p, focus=(0.5, 0.35)).convert("RGBA")
            out.alpha_composite(Image.new("RGBA", (W, H), (*hex2rgb(self.th.get("bg_edge", "#061915")), 150)))
            out.alpha_composite(self.vignette)
            spoken = [w for w in sc.words if w.start <= t + 0.05]
            text = " ".join(w.text for w in spoken)
            if text:
                size = int((84 if len(sc.text) < 60 else 70) * k)
                f = font(self.F_SERIF, size, 900)
                lines = wrap(f, text, W - 140 * k)
                lh = size * 1.15
                y = H * (0.34 if self.vertical else 0.4) - len(lines) * lh / 2
                d = ImageDraw.Draw(out)
                for ln in lines:
                    d.text((W / 2 + 4 * k, y + 5 * k), ln, font=f, fill=(0, 0, 0, 160), anchor="mm")
                    d.text((W / 2, y), ln, font=f, fill=(248, 236, 206, 255), anchor="mm")
                    y += lh
            return out

        if lay == "graphic":
            if sc.image is not None:  # foto do vídeo desfocada ao fundo (nunca fundo liso)
                out = self._blur_bg(idx).copy()
                out.alpha_composite(self._graphic_shade())
            else:
                out = self.bg.copy()
            self.particles.draw(out, t)
            g = self._graphic_frame(sc, t)
            paste(out, g, (x1, y1 + (1 - ease_out_cubic(local / 0.4)) * 40 * k), clamp(local / 0.25))
            return out

        z, foc, rot = fx.motion_params(pl.motion, p, pl.focus)
        if lay == "full":
            out = fit_cover(sc.image, W, H, zoom=z * 1.02, focus=foc).convert("RGBA")
            out.alpha_composite(self.vignette)
            return out

        out = self._blur_bg(idx).copy()
        self.particles.draw(out, t)
        if lay == "polaroid":
            img = self._polaroid(idx)
            ang = self.tilt[idx] + 1.2 * math.sin(t * 1.3)
            drop = 1 - ease_out_back(local / 0.5, 1.3)
            img = img.rotate(ang + drop * 12, resample=Image.BICUBIC, expand=True)
            paste(out, img, (acx - img.width / 2, acy - img.height / 2 - drop * 160 * k + 8 * k * math.sin(t * 1.7)))
        else:  # float: moldura dourada flutuante
            w, h = self._image_box(sc.image, False)
            w, h = int(w * 1.05), int(h * 1.05)
            img = self._framed_image(idx, w, h, z, foc)
            img = img.rotate(1.5 * math.sin(t * 1.1), resample=Image.BICUBIC, expand=True)
            s = 0.8 + 0.2 * ease_out_back(local / 0.45)
            img = scaled(img, s)
            paste(out, img, (acx - img.width / 2, acy - img.height / 2 + 10 * k * math.sin(t * 1.5)))
        return out

    def _intro_alt(self, sc: SceneT, t: float, p: float) -> Image.Image:
        """Aberturas alternativas: 'words' (palavra por palavra gigante), 'band' (faixa de cinema), 'punch' (zoom com flash)."""
        W, H, k = self.W, self.H, self.k
        style = self.lk.get("intro")
        edge = hex2rgb(self.th.get("bg_edge", "#061915"))
        hi = rgba(self.th.get("caption_hi") or self.th.get("gold", "#e9b440"))
        spoken = [w for w in sc.words if w.start <= t + 0.05]
        if style == "punch":
            z = 1.08 + 0.32 * (1 - ease_out_cubic(clamp((t - sc.start) / 0.6))) + 0.06 * p
        else:
            z = 1.1 + 0.1 * p
        out = fit_cover(sc.image, W, H, zoom=z, focus=(0.5, 0.38)).convert("RGBA")
        out.alpha_composite(Image.new("RGBA", (W, H), (*edge, 120 if style == "band" else 140)))
        out.alpha_composite(self.vignette)
        d = ImageDraw.Draw(out)
        if style == "words":  # só a palavra falada agora, enorme, no centro
            if spoken:
                wd = spoken[-1]
                age = t - wd.start
                size = int((150 if len(wd.text) < 9 else 112) * k)
                f = font(self.F_XB, size)
                s_ = 0.7 + 0.3 * ease_out_back(clamp(age / 0.16), 2.0)
                img = Image.new("RGBA", (int(W * 0.96), int(size * 1.6)), (0, 0, 0, 0))
                ImageDraw.Draw(img).text((img.width / 2, img.height / 2), wd.text.upper(), font=f,
                                         fill=hi if wd.hi else (250, 246, 236, 255), anchor="mm",
                                         stroke_width=int(8 * k), stroke_fill=(8, 8, 10, 255))
                img = scaled(img, s_)
                paste(out, img, (W / 2 - img.width / 2, H * (0.36 if self.vertical else 0.42) - img.height / 2))
            return out
        text = " ".join(w.text for w in spoken)
        if style == "band":  # faixa escura de cinema com o texto em caixa alta
            bh = int(H * (0.2 if self.vertical else 0.3))
            cy = int(H * (0.36 if self.vertical else 0.42))
            a = ease_out_cubic(clamp((t - sc.start) / 0.35))
            band = Image.new("RGBA", (W, int(bh * a) or 1), (8, 8, 10, 215))
            out.alpha_composite(band, (0, cy - band.height // 2))
            d.line((0, cy - band.height // 2, W, cy - band.height // 2), fill=hi, width=max(2, int(4 * k)))
            d.line((0, cy + band.height // 2, W, cy + band.height // 2), fill=hi, width=max(2, int(4 * k)))
            if text:
                size = int((62 if len(sc.text) < 70 else 52) * k)
                f = font(self.F_XB, size)
                lines = wrap(f, text.upper(), W - 120 * k)[-3:]
                y = cy - (len(lines) - 1) * size * 0.6
                for ln in lines:
                    d.text((W / 2, y), ln, font=f, fill=(248, 244, 232, 255), anchor="mm")
                    y += size * 1.2
            return out
        # punch: flash curto no começo + texto grande com contorno
        fl = 1 - clamp((t - sc.start) / 0.25)
        if fl > 0:
            out.alpha_composite(Image.new("RGBA", (W, H), (255, 250, 235, int(200 * fl))))
        if text:
            size = int((88 if len(sc.text) < 60 else 72) * k)
            f = font(self.F_XB, size)
            lines = wrap(f, text, W - 140 * k)
            y = H * (0.36 if self.vertical else 0.42) - (len(lines) - 1) * size * 0.58
            for ln in lines:
                d.text((W / 2, y), ln, font=f, fill=(250, 246, 236, 255), anchor="mm", stroke_width=int(7 * k), stroke_fill=(8, 8, 10, 255))
                y += size * 1.16
        return out

    def _frozen_end(self, sc: SceneT) -> Image.Image:
        if sc.index not in self._frozen:
            self._frozen[sc.index] = self._content(sc, sc.end - 0.01)
        return self._frozen[sc.index]

    # ================================================================ transições

    def _transition(self, a: Image.Image, b: Image.Image, kind: str, p: float, center: tuple[float, float]) -> Image.Image:
        W, H = self.W, self.H
        e = ease_in_out(p)
        if kind == "fade":
            return Image.blend(a, b, e)
        if kind == "flash":
            out = Image.blend(a, b, clamp((p - 0.35) / 0.3))
            fl = math.sin(math.pi * p)
            out.alpha_composite(Image.new("RGBA", (W, H), (255, 246, 220, int(210 * fl))))
            return out
        if kind == "whip":
            out = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            blur = 1 + 14 * math.sin(math.pi * p)

            def smear(im):
                sm = im.resize((max(8, int(W / blur)), H), Image.BILINEAR)
                return sm.resize((W, H), Image.BILINEAR)
            out.alpha_composite(smear(a), (int(-e * W), 0))
            out.alpha_composite(smear(b), (int(W - e * W), 0))
            return out
        if kind == "zoom":
            sa = scaled(a, 1 + 0.5 * e)
            out = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            out.alpha_composite(sa, (int((W - sa.width) / 2), int((H - sa.height) / 2)))
            sb = scaled(b, 0.8 + 0.2 * e)
            bb = sb.copy()
            bb.putalpha(int(255 * clamp(p * 1.6)))
            out.alpha_composite(bb, (int((W - sb.width) / 2), int((H - sb.height) / 2)))
            return out
        if kind == "circle":
            r = math.hypot(W, H) * e
            m = Image.new("L", (W, H), 0)
            ImageDraw.Draw(m).ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), fill=255)
            return Image.composite(b, a, m)
        if kind == "push":  # a sai pela esquerda empurrada por b
            out = Image.new("RGBA", (W, H), (0, 0, 0, 255))
            out.alpha_composite(a, (int(-e * W), 0))
            out.alpha_composite(b, (int(W - e * W), 0))
            return out
        if kind == "blur":  # dissolve passando por um desfoque
            bl = math.sin(math.pi * p) * 18
            mix = Image.blend(a, b, e)
            if bl > 1:
                small = mix.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(bl / 4))
                mix = small.resize((W, H), Image.BILINEAR)
            return mix
        if kind == "wipe":  # cortina diagonal com fio de luz
            m = Image.new("L", (W, H), 0)
            span = W + H
            x = -H + span * e
            ImageDraw.Draw(m).polygon([(x, 0), (x + H, H), (-H - 10, H), (-H - 10, 0)], fill=255)
            out = Image.composite(b, a, m)
            ImageDraw.Draw(out).line((x, 0, x + H, H), fill=rgba(self.th.get("gold", "#d9a53a")), width=max(3, int(8 * self.k)))
            return out
        if kind == "glitch":  # deslocamento RGB rápido
            base = a if p < 0.5 else b
            amp = int(math.sin(math.pi * p) * 34 * self.k)
            r, g, bch, al = base.split()
            r = ImageChops.offset(r, amp, 0)
            bch = ImageChops.offset(bch, -amp, 0)
            out = Image.merge("RGBA", (r, g, bch, al))
            if 0.35 < p < 0.65:
                strip = out.crop((0, int(H * 0.4), W, int(H * 0.52)))
                out.alpha_composite(strip, (amp * 2, int(H * 0.4)))
            return out
        # slide_up
        out = a.copy()
        out.alpha_composite(b, (0, int(H * (1 - e))))
        return out

    # ================================================================ mascote

    def _spot_xy(self, idx: int) -> tuple[float, float]:
        sx, sy = self.spots[self.spot_of[idx]]
        return sx * self.W, sy * self.H

    def _mascot_state(self, t: float, sc: SceneT, in_outro: bool) -> tuple[float, float, float, float, bool]:
        """(x, y, escala_x, escala_y, espelhar)."""
        W, H = self.W, self.H
        if in_outro:
            dt = t - self.tl.narration_end - 0.15
            x0, y0 = self._spot_xy(sc.index)
            xe, ye = (x0, y0) if self.mk.get("outro") == "stay" else (W / 2, H * (0.74 if self.vertical else 0.7))
            p = clamp(dt / HOP)
            x = x0 + (xe - x0) * ease_in_out(p)
            y = y0 + (ye - y0) * ease_in_out(p) - 180 * self.k * math.sin(math.pi * p)
            s = 1.25
            bounce = abs(math.sin(dt * 5)) * 30 * self.k if dt > HOP else 0
            return x, y - bounce, s, s, False
        local = t - sc.start
        tx, ty = self._spot_xy(sc.index)
        entry = self.mk.get("entry", "side")
        if sc.index == 0 or (entry == "late" and sc.index == 1 and local < 0.9):
            if entry == "late" and sc.index == 0:
                return tx, H * 1.6, 1.0, 1.0, False  # só aparece depois da abertura
            tt = local if entry == "late" else t
            p = clamp(tt / 0.8)
            if entry == "drop":
                y0 = -0.25 * H
                y = y0 + (ty - y0) * ease_out_back(p, 1.2)
                return tx, y, 1.0, 1.0, tx > W / 2
            if entry in ("rise", "late"):
                y0 = H * 1.25
                return tx, y0 + (ty - y0) * ease_out_back(p, 1.5), 1.0, 1.0, tx > W / 2
            fx_ = -0.3 * W
            x = fx_ + (tx - fx_) * ease_out_cubic(p)
            y = ty - 120 * self.k * math.sin(math.pi * p) * (1 - p)
            return x, y, 1.0, 1.0, x > W / 2
        if sc.index in self.hidden:  # desce para fora do quadro e volta na cena seguinte
            dur = max(0.1, sc.end - sc.start)
            q = min(clamp(local / 0.35), clamp((dur - local) / 0.35))
            return tx, ty + H * 0.35 * ease_in_out(q), 1.0, 1.0, tx > W / 2
        px, py = self._spot_xy(sc.index - 1)
        p = clamp(local / HOP)
        x = px + (tx - px) * ease_in_out(p)
        y = py + (ty - py) * ease_in_out(p) - 90 * self.k * math.sin(math.pi * p)
        sx_, sy_ = 1.0, 1.0
        if p < 1:
            sy_, sx_ = 1 + 0.08 * math.sin(math.pi * p), 1 - 0.05 * math.sin(math.pi * p)
        land = local - HOP
        if 0 <= land < 0.22:
            q = math.sin(math.pi * land / 0.22)
            sy_, sx_ = 1 - 0.14 * q, 1 + 0.1 * q
        return x, y, sx_, sy_, x > W / 2

    @lru_cache(maxsize=16)
    def _bubble(self, text: str) -> Image.Image:
        k = self.k
        f = font(self.F_XB, int(46 * k))
        tw = f.getlength(text)
        w, h = int(tw + 60 * k), int(96 * k)
        th = int(30 * k)

        def draw(d: ImageDraw.ImageDraw, ss: float):
            d.rounded_rectangle((3 * ss, 3 * ss, (w - 3) * ss, (h - 3) * ss), int(40 * k * ss), fill=(252, 248, 236, 255),
                                outline=(22, 26, 24, 255), width=int(5 * k * ss))
            d.polygon([(w * 0.22 * ss, (h - 8) * ss), (w * 0.12 * ss, (h + th - 4) * ss), (w * 0.38 * ss, (h - 8) * ss)],
                      fill=(252, 248, 236, 255), outline=(22, 26, 24, 255))
            d.rectangle((w * 0.22 * ss + 4, (h - 14) * ss, w * 0.38 * ss - 4, (h - 4) * ss), fill=(252, 248, 236, 255))
            d.text((w / 2 * ss, h / 2 * ss), text, font=font(self.F_XB, int(46 * k * ss)), fill=(22, 26, 24, 255), anchor="mm")
        return supersampled(w, h + th, draw, 2)

    # ================================================================ quadro

    def frame(self, t: float, i: int) -> Image.Image:
        tl, k = self.tl, self.k
        if not hasattr(self, "plans"):
            self._setup_direction()
        in_outro = t >= tl.narration_end + 0.15
        sc = tl.scene_at(min(t, tl.narration_end - 0.01))
        local = t - sc.start
        is_intro = sc.index == 0 and len(tl.scenes) > 1
        mx, my, msx, msy, mirror = self._mascot_state(t, sc, in_outro)

        if in_outro:
            out = self.bg.copy()
            self.particles.draw(out, t)
            a = ease_out_cubic((t - tl.narration_end - 0.15) / 0.35)
            o = self._outro()
            cy = self.H * (0.36 if self.vertical else 0.38)
            paste(out, o, (0, cy - o.height / 2 + (1 - a) * 40 * k), a)
            # transição da última cena para a tela final
            if a < 1:
                last = self._frozen_end(tl.scenes[-1]) if tl.scenes else out
                out = Image.blend(last, out, a)
        else:
            cur = self._content(sc, t)
            if sc.index > 0 and local < TR_DUR and not is_intro:
                prev = self._frozen_end(tl.scenes[sc.index - 1])
                out = self._transition(prev, cur, self.trans[sc.index], local / TR_DUR, (mx, my))
            else:
                out = cur

        # barra de progresso + cabeçalho
        pw = int(self.W * clamp(t / tl.duration))
        if pw > 0:
            out.alpha_composite(Image.new("RGBA", (pw, max(4, int(7 * k))), rgba(self.th.get("gold", "#d9a53a"))), (0, 0))
        if not is_intro or local > 0.6:
            hdr_alpha = ease_out_cubic((local - 0.6) / 0.4) if is_intro else 1.0
            paste(out, self._header(0 if (is_intro or in_outro) else sc.step), (0, self.header_y - int(34 * k)), hdr_alpha)

        if not in_outro and not is_intro:
            sh = self._shake(t)
            for t0, t1, img, (px, py) in self.stamps:
                if t0 <= t < t1:
                    simg, op = fx.stamp_anim(img, t - t0)
                    self._place(out, simg, px + sh[0], py + sh[1], op * 0.95)
            if self.layouts[sc.index] == "full" and sc.label:
                lb = self._label(sc.label)
                a = ease_out_cubic((local - 0.3) / 0.3)
                paste(out, lb, (40 * k - (1 - a) * 40 * k, self.card[1] + 10 * k), a)
            self._draw_caption(out, t, self.W / 2 if self.vertical else (self.card[0] + self.card[2]) / 2)

        if self.mascot is not None:
            # mascote
            idx = min(i, len(self.mouth) - 1)
            talk = float(tl.envelope[idx]) if len(tl.envelope) else 0.0
            mouth = int(self.mouth[idx]) if len(self.mouth) else 0
            pl = self.plans[sc.index]
            mood, mk = "normal", 0.0
            if in_outro:
                dt = t - tl.narration_end - 0.15
                mood, mk, mouth, talk = ("wave", 1.0, 0, 0.0) if dt < 1.3 else ("happy", 1.0, 0, 0.0)
            elif pl.react == "surprise" and HOP * 0.8 < local < HOP + 0.8:
                mood, mk = "surprise", math.sin(math.pi * clamp((local - HOP * 0.8) / 0.8))
            elif HOP < local < HOP + 1.6 and not is_intro:
                mood, mk = "point", 1.0
            m, (dx, dy) = self.mascot.frame(t, mouth, talk, mood, mk, mirror)
            if abs(msx - 1) > 0.01 or abs(msy - 1) > 0.01:
                m = m.resize((max(2, int(m.width * msx)), max(2, int(m.height * msy))), Image.BILINEAR)
            # nunca sobe por cima da legenda: o topo (coroa/luvas) fica abaixo dela
            if not in_outro and not is_intro and sc.index not in self.hidden:
                min_y = self.caption_cy + 70 * k + self.base_R * 1.2 * msy
                my = max(my, min_y - dy)
            cxm = self.mascot.cx * msx
            out.alpha_composite(m, (int(mx - cxm + dx), int(my - self.mascot.cy * msy + dy)))

        return out.convert("RGB")
