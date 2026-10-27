"""Cenas animadas com dados (no lugar de uma foto): linha do tempo, contador, mapa, ficha/dossiê,
mito × verdade, citação, lista e texto cinético. Desenhadas dentro do cartão do template.

Cada gráfico recebe `data` (gerado pela IA no roteiro) e é renderizado quadro a quadro.
"""
from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from .core import clamp, ease_in_out, ease_out_back, ease_out_cubic, fit_cover, font, rgba, rounded_mask, wrap

GEO = Path(__file__).resolve().parents[2] / "assets" / "geo"
KINDS = {"timeline", "counter", "map", "dossier", "versus", "quote", "list", "bigtext"}
SERIF, SANS, SANS_XB = "Cinzel.ttf", "FiraSans-Bold.ttf", "FiraSans-ExtraBold.ttf"
SS = 2


class Palette:
    def __init__(self, th: dict):
        self.ink = rgba(th.get("ink", "#0c3223"))
        self.gold = rgba(th.get("gold", "#d9a53a"))
        self.gold_l = rgba(th.get("gold_light", "#f2c862"))
        self.red = rgba(th.get("stamp_myth", "#b8322a"))
        self.green = rgba(th.get("stamp_truth", "#1d7a45"))
        self.muted = (120, 108, 84, 255)
        self.line = (205, 188, 158, 255)
        self.paper = (240, 228, 205, 255)
        self.white = (255, 252, 244, 255)
        self.dark = bool(th.get("_dark"))
        self.panel_ink = rgba(th.get("ink", "#0c3223"))  # texto sobre papel/painéis claros (sempre escuro)
        self.chip_bg = self.ink
        self.chip_fg = self.white
        if self.dark:  # versão para fundo escuro (template "livre", sem cartão)
            self.ink = (246, 238, 218, 255)
            self.muted = (176, 190, 176, 255)
            self.line = (64, 104, 88, 255)
            self.chip_bg = self.gold
            self.chip_fg = self.panel_ink


class Graphic:
    """Base: gera uma imagem RGBA (w×h) do conteúdo do cartão no tempo local t."""

    def __init__(self, data: dict[str, Any], w: int, h: int, k: float, theme: dict, words=None, start: float = 0.0,
                 image: Image.Image | None = None):
        self.d = data or {}
        self.w, self.h, self.k = w, h, k
        self.p = Palette(theme)
        self.words = words or []
        self.start = start
        self.image = image
        th = theme or {}
        self.fonts = (th.get("font_title", SERIF), th.get("font_caption", SANS_XB), th.get("font_ui", SANS))

    # utilidades -------------------------------------------------------------
    def canvas(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        img = Image.new("RGBA", (self.w * SS, self.h * SS), (0, 0, 0, 0))
        return img, ImageDraw.Draw(img)

    def done(self, img: Image.Image) -> Image.Image:
        return img.reduce(SS)

    def f(self, name: str, size: float, weight: int | None = None):
        name = {SERIF: self.fonts[0], SANS_XB: self.fonts[1], SANS: self.fonts[2]}.get(name, name)
        return font(name, int(size * self.k * SS), weight)

    def S(self, v: float) -> float:
        return v * self.k * SS

    def center_v(self, img: Image.Image, content_h: float) -> Image.Image:
        """Recentraliza na vertical um conteúdo desenhado a partir do topo (altura em px finais)."""
        dy = int((self.h - content_h) / 2)
        if dy <= 2:
            return img
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(img.crop((0, 0, img.width, img.height - dy)), (0, dy))
        return out

    def word_time(self, needle: str, default: float) -> float:
        """Momento (local) em que a narração fala `needle` — para sincronizar revelações."""
        n = _norm(needle)
        if n:
            for w in self.words:
                if n[:6] and _norm(w.text).startswith(n[:6]):
                    return max(0.0, w.start - self.start)
        return default

    def render(self, t: float, dur: float) -> Image.Image:
        raise NotImplementedError


# ================================================================ linha do tempo

class Timeline(Graphic):
    def render(self, t, dur):
        img, d = self.canvas()
        p = self.p
        ev = (self.d.get("events") or [])[:5]
        n = max(1, len(ev))
        W, H = self.w * SS, self.h * SS
        title = self.d.get("title", "")
        if title:
            a = clamp(t / 0.3)
            d.text((W / 2, H * 0.5 - self.S(190)), title.upper(), font=self.f(SERIF, 40, 800), fill=(*p.ink[:3], int(255 * a)), anchor="mm")
        y = H * 0.5
        x0, x1 = self.S(150), W - self.S(150)
        lp = ease_out_cubic(t / 0.6)
        d.line((x0, y, x0 + (x1 - x0) * lp, y), fill=p.line, width=int(self.S(8)))
        times = [self.word_time(str(e.get("year", "")), 0.35 + i * (dur - 0.9) / n) for i, e in enumerate(ev)]
        times = [max(0.35, tt) for tt in times]
        active = max([i for i, tt in enumerate(times) if t >= tt] or [-1])
        if active >= 0:
            xa = x0 + (x1 - x0) * (active / max(1, n - 1) if n > 1 else 0.5)
            fill_p = ease_out_cubic((t - times[active]) / 0.4)
            xprev = x0 + (x1 - x0) * ((active - 1) / max(1, n - 1)) if active > 0 else x0
            d.line((x0, y, xprev + (xa - xprev) * fill_p, y), fill=p.gold, width=int(self.S(8)))
        slot = (x1 - x0) / max(1, n - 1) if n > 1 else (x1 - x0)
        for i, e in enumerate(ev):
            if t < times[i]:
                continue
            q = t - times[i]
            x = x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0.5)
            s = ease_out_back(q / 0.35)
            r = self.S(20) * s
            is_act = i == active
            if is_act:
                pr = self.S(20) + self.S(22) * ((q * 1.4) % 1)
                al = int(140 * (1 - (q * 1.4) % 1))
                d.ellipse((x - pr, y - pr, x + pr, y + pr), outline=(*p.gold[:3], al), width=int(self.S(4)))
            d.ellipse((x - r, y - r, x + r, y + r), fill=p.gold if is_act else p.gold_l, outline=p.ink, width=int(self.S(4)))
            a = int(255 * clamp(q / 0.3))
            up = (1 - ease_out_cubic(q / 0.4)) * self.S(30)
            d.text((x, y - self.S(70) + up), str(e.get("year", "")), font=self.f(SERIF, 54 if is_act else 44, 900),
                   fill=(*(p.ink if is_act else p.muted)[:3], a), anchor="mm")
            fl = self.f(SANS, 27)
            lines = wrap(fl, str(e.get("label", "")), min(self.S(270), max(self.S(150), slot * 0.9)))[:3]
            for li, ln in enumerate(lines):
                d.text((x, y + self.S(62) + li * self.S(34) - up), ln, font=fl, fill=(*p.ink[:3], a), anchor="mm")
        return self.done(img)


# ================================================================ contador

class Counter(Graphic):
    def render(self, t, dur):
        img, d = self.canvas()
        p = self.p
        W, H = self.w * SS, self.h * SS
        val = self.d.get("value", 0)
        try:
            v = float(str(val).replace(".", "").replace(",", "."))
        except ValueError:
            v = 0
        cp = ease_out_cubic((t - 0.15) / 1.3)
        cur = v * cp
        txt = f"{self.d.get('prefix', '')}{_fmt_num(cur, v)}{self.d.get('suffix', '')}"
        icons = int(v) if (self.d.get("icons", True) and 1 < v <= 30 and float(v).is_integer()) else 0
        ny = H * (0.36 if icons else 0.42)
        pop = 1 + 0.08 * math.sin(math.pi * clamp((t - 1.45) / 0.25))
        final = f"{self.d.get('prefix', '')}{_fmt_num(v, v)}{self.d.get('suffix', '')}"
        fz = 190.0
        while fz > 60 and self.f(SERIF, fz, 900).getlength(final) > W - self.S(90):
            fz -= 6
        fz *= pop
        d.text((W / 2 + self.S(5), ny + self.S(7)), txt, font=self.f(SERIF, fz, 900), fill=(*p.gold[:3], 200), anchor="mm")
        d.text((W / 2, ny), txt, font=self.f(SERIF, fz, 900), fill=p.ink, anchor="mm")
        la = clamp((t - 0.6) / 0.4)
        fl = self.f(SANS_XB, 36)
        for i, ln in enumerate(wrap(fl, str(self.d.get("label", "")), W - self.S(140))[:2]):
            d.text((W / 2, ny + self.S(130) + i * self.S(44)), ln, font=fl, fill=(*p.ink[:3], int(255 * la)), anchor="mm")
        if icons:
            per_row = min(icons, 10)
            rows = math.ceil(icons / per_row)
            size = min(self.S(70), (W - self.S(120)) / per_row)
            y0 = H * 0.78 - (rows - 1) * size * 0.55
            mark = self.d.get("mark", "")
            for i in range(icons):
                ti = 0.3 + 1.2 * i / icons
                if t < ti:
                    continue
                s = ease_out_back((t - ti) / 0.3)
                cx = W / 2 + (i % per_row - (per_row - 1) / 2) * size
                cy = y0 + (i // per_row) * size * 1.1
                _person(d, cx, cy, size * 0.42 * s, p.ink)
                if mark == "x" and t > 1.6 + i * 0.05:
                    _xmark(d, cx, cy, size * 0.35, p.red, self.S(5))
        return self.done(img)


# ================================================================ mapa

@lru_cache(maxsize=4)
def _geo(name: str) -> list[tuple[str, str, list[list[tuple[float, float]]]]]:
    data = json.loads((GEO / name).read_text(encoding="utf-8"))
    out = []
    for f in data["features"]:
        pr = f["properties"]
        code = pr.get("sigla") or pr.get("ISO_A2") or ""
        nm = pr.get("name") or pr.get("NAME_PT") or pr.get("NAME") or ""
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        rings = []
        for poly in polys:
            ring = poly[0]
            step = max(1, len(ring) // 400)  # simplificação
            rings.append([(x, y) for x, y in ring[::step]])
        out.append((code.upper(), nm, rings))
    return out


class MapG(Graphic):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        scope = (self.d.get("scope") or "brasil").lower()
        self.world = scope not in ("brasil", "brazil", "br")
        self.feats = _geo("world.geojson" if self.world else "brazil-states.geojson")
        hl = [str(x).upper() for x in (self.d.get("highlight") or [])]
        self.hl = set(hl)
        # enquadramento
        if self.world and self.hl:
            pts = [pt for c, _, rs in self.feats if c in self.hl for r in rs for pt in r]
            pts = pts or [pt for _, _, rs in self.feats for r in rs for pt in r]
        else:
            pts = [pt for _, _, rs in self.feats for r in rs for pt in r]
        lons, lats = [x for x, _ in pts], [y for _, y in pts]
        pad = 12 if self.world else 0.6
        self.box = (min(lons) - pad, min(lats) - pad * 0.6, max(lons) + pad, max(lats) + pad * 0.6)
        self.base = self._base()

    def proj(self, lon: float, lat: float) -> tuple[float, float]:
        x0, y0, x1, y1 = self.box
        W, H = self.w * SS, self.h * SS
        top = self.S(80) if self.d.get("title") else self.S(20)
        aw, ah = W - self.S(30), H - top - self.S(90)
        kx = math.cos(math.radians((y0 + y1) / 2))
        sw, sh = (x1 - x0) * kx, (y1 - y0)
        s = min(aw / sw, ah / sh)
        ox = (W - sw * s) / 2
        oy = top + (ah - sh * s) / 2
        return ox + (lon - x0) * kx * s, oy + (y1 - lat) * s

    def _base(self) -> Image.Image:
        img, d = self.canvas()
        p = self.p
        for code, _, rings in self.feats:
            for r in rings:
                pts = [self.proj(x, y) for x, y in r]
                if len(pts) > 2:
                    d.polygon(pts, fill=(228, 212, 182, 255) if not p.dark else (32, 82, 66, 255),
                              outline=(150, 130, 96, 255) if not p.dark else (96, 140, 118, 255))
        return img

    def render(self, t, dur):
        p = self.p
        img = self.base.copy()
        d = ImageDraw.Draw(img)
        W, H = self.w * SS, self.h * SS
        if self.d.get("title"):
            d.text((W / 2, self.S(55)), str(self.d["title"]).upper(), font=self.f(SERIF, 36, 800), fill=p.ink, anchor="mm")
        hp = ease_in_out((t - 0.3) / 0.6)
        if self.hl and hp > 0:
            for code, _, rings in self.feats:
                if code in self.hl:
                    for r in rings:
                        pts = [self.proj(x, y) for x, y in r]
                        if len(pts) > 2:
                            d.polygon(pts, fill=(*p.gold[:3], int(255 * hp)), outline=p.ink, width=int(self.S(3)))
        # pino
        pin = self.d.get("pin")
        if not pin and self.hl:
            pts = [pt for c, _, rs in self.feats if c in self.hl for r in rs for pt in r]
            if pts:
                pin = [sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)]
        if pin:
            px, py = self.proj(float(pin[0]), float(pin[1]))
            tp = t - 0.8
            if tp > 0:
                for k in range(2):
                    q = ((tp * 0.9 + k * 0.5) % 1)
                    rr = self.S(14) + self.S(60) * q
                    d.ellipse((px - rr, py - rr * 0.45, px + rr, py + rr * 0.45), outline=(*p.red[:3], int(200 * (1 - q))), width=int(self.S(4)))
                drop = (1 - _bounce(tp / 0.6)) * self.S(140)
                _pin(d, px, py - drop, self.S(30), p.red, p.ink)
        lab = self.d.get("label")
        if lab and t > 1.0:
            a = ease_out_cubic((t - 1.0) / 0.35)
            fl = self.f(SANS_XB, 32)
            tw = fl.getlength(lab)
            y = H - self.S(60) + (1 - a) * self.S(20)
            d.rounded_rectangle((W / 2 - tw / 2 - self.S(22), y - self.S(30), W / 2 + tw / 2 + self.S(22), y + self.S(30)),
                                self.S(30), fill=(*p.chip_bg[:3], int(235 * a)))
            d.text((W / 2, y), lab, font=fl, fill=(*p.chip_fg[:3], int(255 * a)), anchor="mm")
        out = self.done(img)
        sc = 0.94 + 0.06 * ease_out_cubic(t / 0.5)
        if sc < 0.999:
            z = out.resize((int(self.w * sc), int(self.h * sc)), Image.BILINEAR)
            o = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
            o.alpha_composite(z, ((self.w - z.width) // 2, (self.h - z.height) // 2))
            out = o
        return out


# ================================================================ ficha / dossiê

class Dossier(Graphic):
    def render(self, t, dur):
        img, d = self.canvas()
        p = self.p
        W, H = self.w * SS, self.h * SS
        m = self.S(36)
        has_photo = self.image is not None and self.d.get("_photo", True)
        tw0 = W - m - (m + self.S(36) + self.S(250) + self.S(60) if has_photo else m + self.S(40)) - self.S(30)
        n_name = len(wrap(self.f(SERIF, 40, 900), str(self.d.get("name", "")).upper(), tw0)[:2])
        n_fields = len((self.d.get("fields") or [])[:5])
        fields_end = m + self.S(140) + n_name * self.S(50) + (self.S(76) if self.d.get("nickname") else 0) + n_fields * self.S(100)
        photo_end = m + self.S(110) + self.S(320) + self.S(50) if has_photo else 0
        bottom = min(H - m, max(fields_end, photo_end, m + self.S(420)) + self.S(30))
        self._content_h = (bottom + m) / SS
        d.rectangle((m, m, W - m, bottom), fill=p.paper, outline=(170, 146, 104, 255), width=int(self.S(3)))
        for yy in range(int(m + self.S(120)), int(bottom - self.S(10)), int(self.S(48))):
            d.line((m + self.S(20), yy, W - m - self.S(20), yy), fill=(222, 204, 172, 255), width=int(self.S(2)))
        hd = self.d.get("header", "FICHA HISTÓRICA")
        d.text((m + self.S(28), m + self.S(44)), hd, font=self.f(SERIF, 30, 900), fill=p.muted, anchor="lm")
        d.line((m + self.S(28), m + self.S(78), W - m - self.S(28), m + self.S(78)), fill=p.panel_ink, width=int(self.S(3)))
        # foto presa com clipe
        px0 = m + self.S(36)
        pw_, ph_ = self.S(250), self.S(320)
        py0 = m + self.S(110)
        if self.image is not None and self.d.get("_photo", True):
            a = ease_out_back((t - 0.1) / 0.45)
            if a > 0:
                ph = fit_cover(self.image, int(pw_ / SS), int(ph_ / SS)).convert("L").convert("RGBA")
                ph = ph.resize((int(pw_), int(ph_)))
                fr = Image.new("RGBA", (int(pw_ + self.S(20)), int(ph_ + self.S(20))), (250, 246, 236, 255))
                fr.alpha_composite(ph, (int(self.S(10)), int(self.S(10))))
                fr = fr.rotate(-3 * a, expand=True, resample=Image.BICUBIC)
                img.alpha_composite(fr, (int(px0), int(py0 + (1 - a) * self.S(40))))
                cx = px0 + pw_ / 2
                d.rounded_rectangle((cx - self.S(14), py0 - self.S(22), cx + self.S(14), py0 + self.S(46)), self.S(14),
                                    outline=(120, 120, 120, 255), width=int(self.S(5)))
            tx = px0 + pw_ + self.S(60)
        else:
            tx = m + self.S(40)
        name = str(self.d.get("name", ""))
        nick = str(self.d.get("nickname", ""))
        tw = W - m - tx - self.S(30)
        y = m + self.S(140)
        a = clamp((t - 0.3) / 0.3)
        for ln in wrap(self.f(SERIF, 40, 900), name.upper(), tw)[:2]:
            d.text((tx, y), ln, font=self.f(SERIF, 40, 900), fill=(*p.panel_ink[:3], int(255 * a)), anchor="lm")
            y += self.S(50)
        if nick:
            d.text((tx, y + self.S(6)), f"“{nick}”", font=self.f(SANS_XB, 40), fill=(*p.gold[:3], int(255 * clamp((t - 0.5) / 0.3))), anchor="lm")
            y += self.S(70)
        fields = (self.d.get("fields") or [])[:5]
        fk, fv = self.f(SANS, 24), self.f(SANS_XB, 30)
        for i, fld in enumerate(fields):
            k_, v_ = (fld[0], fld[1]) if isinstance(fld, (list, tuple)) and len(fld) >= 2 else (fld.get("k", ""), fld.get("v", "")) if isinstance(fld, dict) else ("", str(fld))
            t0 = 0.8 + i * max(0.35, (dur - 2.2) / max(1, len(fields)))
            if t < t0:
                break
            chars = int(len(str(v_)) * clamp((t - t0) / 0.5))
            d.text((tx, y), str(k_).upper(), font=fk, fill=p.muted, anchor="lm")
            for li, ln in enumerate(wrap(fv, str(v_)[:chars], tw)[:2]):
                d.text((tx, y + self.S(34) + li * self.S(36)), ln, font=fv, fill=p.panel_ink, anchor="lm")
            y += self.S(100)
        out = self.done(img)
        st = self.d.get("stamp")
        if st:
            from .fx import stamp, stamp_anim
            t0 = max(1.2, dur - 1.4)
            if t >= t0:
                s_img, op = stamp_anim(stamp(str(st).upper(), "#b8322a", int(50 * self.k), 12), t - t0)
                if s_img is not None:
                    s_img = s_img.copy()
                    s_img.putalpha(s_img.getchannel("A").point(lambda v: int(v * op * 0.9)))
                    out.alpha_composite(s_img, (int(self.w * 0.26 - s_img.width / 2), int(self._content_h - 36 * self.k - s_img.height / 2 - 30 * self.k)))
        return self.center_v(out, self._content_h)


# ================================================================ mito × verdade

class Versus(Graphic):
    def render(self, t, dur):
        img, d = self.canvas()
        p = self.p
        W, H = self.w * SS, self.h * SS
        L, R_ = self.d.get("left") or {}, self.d.get("right") or {}
        tr = self.word_time(R_.get("cue", "verdade"), dur * 0.45)
        tr = clamp(tr, 0.8, max(0.9, dur - 1.0))
        gap = self.S(24)
        pw = (W - self.S(60) - gap) / 2
        fl0 = self.f(SANS_XB, 33)
        n_lines = max(len(wrap(fl0, str((L if k == 0 else R_).get("text", "")), pw - self.S(50))[:6]) for k in (0, 1))
        ph = self.S(80 + 110 + 120 + 40) + n_lines * self.S(44)
        top = max(self.S(20), (H - ph) / 2)
        for side, data, t0, col, icon in ((0, L, 0.15, p.red, "x"), (1, R_, tr, p.green, "check")):
            if t < t0:
                continue
            q = t - t0
            a = ease_out_back(q / 0.4)
            x = self.S(30) + side * (pw + gap)
            y0, y1 = top, top + ph
            dim = side == 0 and t > tr + 0.3
            panel = (*((235, 222, 198) if not dim else (226, 214, 192)), 255)
            off = (1 - a) * self.S(60) * (1 if side else -1)
            d.rounded_rectangle((x + off, y0, x + pw + off, y1), self.S(22), fill=panel, outline=col, width=int(self.S(5)))
            d.rounded_rectangle((x + off, y0, x + pw + off, y0 + self.S(80)), self.S(22), fill=col)
            d.rectangle((x + off, y0 + self.S(50), x + pw + off, y0 + self.S(80)), fill=col)
            d.text((x + pw / 2 + off, y0 + self.S(42)), str(data.get("title", "MITO" if side == 0 else "VERDADE")).upper(),
                   font=self.f(SERIF, 40, 900), fill=p.white, anchor="mm")
            ic = y0 + self.S(190)
            s = ease_out_back((q - 0.2) / 0.35)
            if s > 0:
                (_xmark if icon == "x" else _check)(d, x + pw / 2 + off, ic, self.S(60) * s, col, self.S(14))
            fl = self.f(SANS_XB, 33)
            for li, ln in enumerate(wrap(fl, str(data.get("text", "")), pw - self.S(50))[:6]):
                d.text((x + pw / 2 + off, ic + self.S(120) + li * self.S(44)), ln, font=fl,
                       fill=(*p.panel_ink[:3], 140 if dim else 255), anchor="mm")
            if dim:
                d.line((x + self.S(30), y0 + self.S(120), x + pw - self.S(30), y1 - self.S(40)), fill=(*p.red[:3], 150), width=int(self.S(6)))
        return self.done(img)


# ================================================================ citação

class Quote(Graphic):
    def render(self, t, dur):
        img, d = self.canvas()
        p = self.p
        W, H = self.w * SS, self.h * SS
        a = ease_out_back(t / 0.4)
        d.text((self.S(90), self.S(120)), "“", font=self.f(SERIF, 220 * a + 1, 900), fill=p.gold, anchor="mm")
        text = str(self.d.get("text", ""))
        words = text.split()
        n = int(len(words) * clamp((t - 0.3) / max(0.6, dur * 0.65)))
        size = 62 if len(text) < 80 else 52 if len(text) < 140 else 42
        fq = self.f(SERIF, size, 700)
        lines = wrap(fq, text, W - self.S(170))
        while len(lines) > 7 and size > 32:
            size -= 4
            fq = self.f(SERIF, size, 700)
            lines = wrap(fq, text, W - self.S(170))
        y = H / 2 - len(lines) * self.S(size * 1.3) / 2
        shown = 0
        for ln in lines:
            ws = ln.split()
            part = " ".join(ws[:max(0, n - shown)])
            shown += len(ws)
            d.text((self.S(90), y), part, font=fq, fill=p.ink, anchor="lm")
            y += self.S(size * 1.3)
        au = self.d.get("author")
        if au and t > dur * 0.7:
            aa = clamp((t - dur * 0.7) / 0.4)
            d.text((W - self.S(80), y + self.S(40)), f"— {au}", font=self.f(SANS_XB, 32), fill=(*p.gold[:3], int(255 * aa)), anchor="rm")
        return self.done(img)


# ================================================================ lista

class ListG(Graphic):
    def render(self, t, dur):
        img, d = self.canvas()
        p = self.p
        W, H = self.w * SS, self.h * SS
        items = (self.d.get("items") or [])[:5]
        title = self.d.get("title", "")
        block = (self.S(80) if title else 0) + len(items) * self.S(120)
        y = max(self.S(60), (H - block) / 2)
        if title:
            d.text((W / 2, y), str(title).upper(), font=self.f(SERIF, 38, 900), fill=(*p.ink[:3], int(255 * clamp(t / 0.3))), anchor="mm")
            y += self.S(80)
        fl = self.f(SANS_XB, 34)
        step = self.S(120)
        for i, it in enumerate(items):
            t0 = self.word_time(str(it).split()[0] if str(it).split() else "", 0.4 + i * (dur - 1) / max(1, len(items)))
            t0 = max(0.3, t0)
            if t < t0:
                continue
            q = t - t0
            a = ease_out_cubic(q / 0.35)
            x = self.S(70) - (1 - a) * self.S(60)
            cy = y + step * i + step / 2
            s = ease_out_back(q / 0.3)
            d.ellipse((x - self.S(24) * s, cy - self.S(24) * s, x + self.S(24) * s, cy + self.S(24) * s), fill=p.gold, outline=p.ink, width=int(self.S(3)))
            _check(d, x, cy, self.S(13) * s, p.ink, self.S(5))
            for li, ln in enumerate(wrap(fl, str(it), W - self.S(170))[:2]):
                d.text((x + self.S(50), cy + (li - 0.5 * (len(wrap(fl, str(it), W - self.S(170))[:2]) - 1)) * self.S(42)), ln,
                       font=fl, fill=(*p.ink[:3], int(255 * a)), anchor="lm")
        return self.done(img)


# ================================================================ texto cinético

class BigText(Graphic):
    def render(self, t, dur):
        img, d = self.canvas()
        p = self.p
        W, H = self.w * SS, self.h * SS
        text = str(self.d.get("text", "")).upper()
        words = text.split()
        size = 110 if len(text) < 12 else 84 if len(text) < 22 else 64
        fb = self.f(SERIF, size, 900)
        lines = wrap(fb, text, W - self.S(100))
        lh = self.S(size * 1.1)
        y = H * 0.45 - (len(lines) - 1) * lh / 2
        wi = 0
        for ln in lines:
            ws = ln.split()
            total = sum(fb.getlength(w) for w in ws) + fb.getlength(" ") * (len(ws) - 1)
            x = W / 2 - total / 2
            for w in ws:
                t0 = 0.12 + wi * 0.22
                q = t - t0
                if q >= 0:
                    s = ease_out_back(q / 0.3, 2.2)
                    ww = fb.getlength(w)
                    fz = self.f(SERIF, size * (1.6 - 0.6 * min(1, s)), 900)
                    col = p.red if self.d.get("color") == "red" else p.ink
                    d.text((x + ww / 2, y), w, font=fz, fill=(*col[:3], int(255 * clamp(q / 0.12))), anchor="mm")
                x += fb.getlength(w) + fb.getlength(" ")
                wi += 1
            y += lh
        sub = self.d.get("sub")
        if sub:
            t0 = 0.12 + len(words) * 0.22 + 0.2
            a = clamp((t - t0) / 0.35)
            fs = self.f(SANS_XB, 40)
            d.text((W / 2, y + self.S(30) + (1 - a) * self.S(20)), str(sub), font=fs, fill=(*p.gold[:3], int(255 * a)), anchor="mm")
        return self.done(img)


CLASSES = {"timeline": Timeline, "counter": Counter, "map": MapG, "dossier": Dossier, "versus": Versus,
           "quote": Quote, "list": ListG, "bigtext": BigText}


def make(kind: str, data: dict, w: int, h: int, k: float, theme: dict, words=None, start=0.0, image=None) -> Graphic | None:
    cls = CLASSES.get(kind)
    return cls(data, w, h, k, theme, words, start, image) if cls else None


# ================================================================ ícones

def _person(d: ImageDraw.ImageDraw, cx, cy, s, col):
    d.ellipse((cx - s * 0.32, cy - s * 0.95, cx + s * 0.32, cy - s * 0.31), fill=col)
    d.rounded_rectangle((cx - s * 0.55, cy - s * 0.22, cx + s * 0.55, cy + s * 0.85), int(s * 0.35), fill=col)


def _xmark(d, cx, cy, s, col, w):
    d.line((cx - s, cy - s, cx + s, cy + s), fill=col, width=int(w))
    d.line((cx - s, cy + s, cx + s, cy - s), fill=col, width=int(w))


def _check(d, cx, cy, s, col, w):
    d.line([(cx - s, cy), (cx - s * 0.3, cy + s * 0.7), (cx + s, cy - s * 0.7)], fill=col, width=int(w), joint="curve")


def _pin(d, x, y, r, col, ink):
    d.polygon([(x - r * 0.72, y - r * 1.55), (x + r * 0.72, y - r * 1.55), (x, y)], fill=col)
    d.ellipse((x - r, y - r * 2.6, x + r, y - r * 0.6), fill=col, outline=ink, width=int(r * 0.12))
    d.ellipse((x - r * 0.38, y - r * 1.98, x + r * 0.38, y - r * 1.22), fill=(255, 250, 240, 255))


def _bounce(p: float) -> float:
    p = clamp(p)
    if p < 0.65:
        return ease_out_cubic(p / 0.65)
    q = (p - 0.65) / 0.35
    return 1 - 0.08 * math.sin(math.pi * q)


def _fmt_num(cur: float, target: float) -> str:
    if float(target).is_integer():
        return f"{int(round(cur)):,}".replace(",", ".")
    return f"{cur:.1f}".replace(".", ",")


def _norm(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s)


REQUIRED = {
    "timeline": lambda d: len(d.get("events") or []) >= 2,
    "counter": lambda d: _is_num(d.get("value")),
    "map": lambda d: bool(d.get("highlight") or d.get("pin")),
    "dossier": lambda d: bool(d.get("name")),
    "versus": lambda d: bool((d.get("left") or {}).get("text") and (d.get("right") or {}).get("text")),
    "quote": lambda d: bool(d.get("text")),
    "list": lambda d: len(d.get("items") or []) >= 2,
    "bigtext": lambda d: bool(d.get("text")),
}


def _is_num(v) -> bool:
    try:
        float(str(v).replace(".", "").replace(",", "."))
        return True
    except (TypeError, ValueError):
        return False


def normalize(visual: dict) -> dict | None:
    """Aceita dados dentro de visual["data"] ou soltos no próprio visual; devolve None se incompletos."""
    kind = visual.get("kind")
    if kind not in KINDS:
        return None
    data = dict(visual.get("data") or {})
    for k, v in visual.items():
        if k not in ("kind", "data", "query", "query_pt", "prompt") and k not in data:
            data[k] = v
    return data if REQUIRED[kind](data) else None
