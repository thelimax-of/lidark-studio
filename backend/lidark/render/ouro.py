"""Template "Ouro": recriação do visual do canal Ouro do Passado (vertical 9:16 e horizontal 16:9).

Fundo esmeralda · cabeçalho com título + "PASSO x/n" · barra de progresso dourada · cartão de pergaminho
com imagem emoldurada e etiqueta · legenda palavra a palavra · mascote relógio · tela final "SEGUE PRA MAIS".
"""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from .core import (SceneT, Timeline, clamp, ease_out_back, ease_out_cubic, ellipsize, fit_cover, font,
                   linear_gradient, paste, radial_gradient, rgba, rounded_mask, scaled, shadow, supersampled, wrap)
from . import fx, infographics
from .characters import make_mascot
from .mascot import plan_mouth

SERIF = "Cinzel.ttf"
SANS_XB = "FiraSans-ExtraBold.ttf"
SANS_B = "FiraSans-Bold.ttf"


class OuroTemplate:
    def __init__(self, tl: Timeline):
        self.tl = tl
        self.th = tl.theme
        self.F_SERIF = self.th.get("font_title", SERIF)
        self.F_XB = self.th.get("font_caption", SANS_XB)
        self.F_B = self.th.get("font_ui", SANS_B)
        W, H = tl.width, tl.height
        self.W, self.H = W, H
        self.vertical = H > W
        if self.vertical:
            k = W / 1080
            self.card = (int(66 * k), int(158 * k), int(1014 * k), int(910 * k))
            self.caption_cy = int(1010 * k)
            self.caption_maxw = int(940 * k)
            self.mascot_R = int(225 * k)
            self.mascot = make_mascot(self.th, self.mascot_R)
            self.mascot_c = (W / 2, int(1560 * k))
            self.header_y = int(78 * k)
            self.k = k
        else:
            k = H / 1080
            self.card = (int(70 * k), int(150 * k), int(1230 * k), int(880 * k))
            self.caption_cy = int(975 * k)
            self.caption_maxw = int(1150 * k)
            self.mascot_R = int(215 * k)
            self.mascot = make_mascot(self.th, self.mascot_R)
            self.mascot_c = (int(1580 * k), int(560 * k))
            self.header_y = int(70 * k)
            self.k = k
        # look sorteado pelo diretor de variedade (cor, legenda, abertura, encerramento, mascote)
        from .look import Look
        self.lk = dict(self.th.get("_look") or {})
        self.look = Look(self.lk, W, H, seed=len(tl.title) * 13 + len(tl.scenes))
        self.cap_style = self.lk.get("caption", "classic")
        self.cap_words = int(self.lk.get("caption_words", 4))
        self.cap_anim = self.lk.get("caption_anim", "pop")
        self.bg = self._background()
        self.card_img = self._card()
        self.coin_small = self._coin(int(32 * self.k))
        self.coin_big = self._coin(int(78 * self.k))
        self._title_cache: dict = {}

    # ================================================================ elementos estáticos

    def _background(self) -> Image.Image:
        W, H = self.W, self.H
        bg = radial_gradient(W, H, (W / 2, H * 0.42), self.th.get("bg_center", "#16473a"),
                             self.th.get("bg_edge", "#061915"), math.hypot(W, H) * 0.62)
        return bg.convert("RGBA")

    def _card(self) -> Image.Image:
        x1, y1, x2, y2 = self.card
        w, h = x2 - x1, y2 - y1
        k = self.k
        r = int(26 * k)
        pad = int(60 * k)
        out = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
        sh = shadow(w, h, r, int(22 * k), 150)
        out.alpha_composite(sh, (pad - sh.width // 2 + w // 2, pad - sh.height // 2 + h // 2 + int(14 * k)))
        body = linear_gradient(w, h, self.th.get("card", "#f5e9d9"), self.th.get("card_edge", "#e9dcc8")).convert("RGBA")
        # vinheta interna suave
        vig = Image.new("L", (w, h), 0)
        ImageDraw.Draw(vig).rounded_rectangle((0, 0, w, h), r, outline=60, width=int(40 * k))
        vig = vig.filter(ImageFilter.GaussianBlur(float(30 * k)))
        dark = Image.new("RGBA", (w, h), (120, 95, 60, 255))
        body = Image.composite(dark, body, vig.point(lambda v: int(v * 0.35)))
        body.putalpha(rounded_mask(w, h, r))
        out.alpha_composite(body, (pad, pad))

        def lines(d: ImageDraw.ImageDraw, ss: float):
            d.rounded_rectangle((2 * ss, 2 * ss, (w - 2) * ss, (h - 2) * ss), r * ss, outline=(26, 30, 28, 255), width=int(5 * k * ss))
            ins = 16 * k
            d.rounded_rectangle((ins * ss, ins * ss, (w - ins) * ss, (h - ins) * ss), int(16 * k * ss),
                                outline=rgba(self.th.get("card_line", "#d8a943")), width=int(3 * k * ss))
        out.alpha_composite(supersampled(w, h, lines, 2), (pad, pad))
        self.card_pad = pad
        return out

    def _coin(self, r: int) -> Image.Image:
        size = r * 2 + 8

        def draw(d: ImageDraw.ImageDraw, ss: float):
            c = size * ss / 2
            R = r * ss
            d.ellipse((c - R, c - R, c + R, c + R), fill=rgba(self.th.get("gold", "#d9a53a")), outline=(26, 30, 28, 255), width=int(max(2, r * 0.08) * ss))
            d.ellipse((c - R * 0.78, c - R * 0.78, c + R * 0.78, c + R * 0.78), outline=(90, 62, 15, 255), width=int(max(1, r * 0.05) * ss))
            for i in range(24):
                a = math.radians(i * 15)
                x, y = c + R * 0.89 * math.cos(a), c + R * 0.89 * math.sin(a)
                rr = R * 0.035
                d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(120, 84, 20, 255))
            f = font(self.F_SERIF, int(R * 1.05), 900)
            d.text((c, c + R * 0.04), self.th.get("logo_letter", "P"), font=f, fill=rgba(self.th.get("ink", "#0c3223")), anchor="mm")
        return supersampled(size, size, draw, 3)

    # ================================================================ elementos dinâmicos

    @lru_cache(maxsize=16)
    def _frame_shell(self, w: int, h: int) -> tuple[Image.Image, int, int]:
        """Moldura dourada + sombra (cacheada por tamanho). Retorna (img, pad, borda)."""
        k = self.k
        bw = max(3, int(7 * k))
        ow = max(2, int(3 * k))
        r = int(14 * k)
        pad = int(30 * k)
        out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
        sh = shadow(w, h, r, int(14 * k), 170)
        out.alpha_composite(sh, (pad + w // 2 - sh.width // 2, pad + h // 2 - sh.height // 2 + int(8 * k)))

        def frame(d: ImageDraw.ImageDraw, ss: float):
            d.rounded_rectangle((0, 0, (w - 1) * ss, (h - 1) * ss), r * ss, fill=(26, 30, 28, 255))
            d.rounded_rectangle((ow * ss, ow * ss, (w - 1 - ow) * ss, (h - 1 - ow) * ss), int((r - 2) * ss),
                                fill=rgba(self.th.get("gold", "#d9a53a")))
            d.line((ow * ss + r * ss, (ow + 2) * ss, (w - ow) * ss - r * ss, (ow + 2) * ss),
                   fill=rgba(self.th.get("gold_light", "#f2c862")), width=int(2 * ss))
        out.alpha_composite(supersampled(w, h, frame, 2), (pad, pad))
        return out, pad, bw + ow

    @lru_cache(maxsize=8)
    def _inner_mask(self, w: int, h: int) -> Image.Image:
        return rounded_mask(w, h, max(2, int(14 * self.k) - max(3, int(7 * self.k))))

    def _framed_image(self, scene_idx: int, w: int, h: int, zoom: float = 1.0,
                      focus: tuple[float, float] = (0.5, 0.42), t: float | None = None) -> Image.Image:
        """Imagem da cena com moldura dourada e sombra, em tamanho w×h, com zoom/foco (Ken Burns)."""
        sc = self.tl.scenes[scene_idx]
        shell, pad, b = self._frame_shell(w, h)
        iw, ih = w - 2 * b, h - 2 * b
        src = sc.clip.frame(t - sc.start) if (sc.clip is not None and t is not None) else None
        inner = fit_cover(src or sc.image, iw, ih, zoom=(1.0 if src else zoom), focus=focus).convert("RGBA")
        inner.putalpha(self._inner_mask(iw, ih))
        out = shell.copy()
        out.alpha_composite(inner, (pad + b, pad + b))
        return out

    def _image_box(self, img: Image.Image, intro: bool) -> tuple[int, int]:
        x1, y1, x2, y2 = self.card
        k = self.k
        if intro:
            maxw, maxh = (x2 - x1) * 0.42, (y2 - y1) * 0.42
        else:
            maxw, maxh = (x2 - x1) - 110 * k, (y2 - y1) - 130 * k
        ar = img.width / img.height
        ar = clamp(ar, 0.62, 1.9)
        w = min(maxw, maxh * ar)
        h = w / ar
        return int(w), int(h)

    @lru_cache(maxsize=32)
    def _label(self, text: str) -> Image.Image:
        k = self.k
        f = font(self.F_B, int(27 * k))
        tw = int(f.getlength(text))
        w, h = tw + int(32 * k), int(44 * k)

        def draw(d: ImageDraw.ImageDraw, ss: float):
            d.rounded_rectangle((0, 0, (w - 1) * ss, (h - 1) * ss), int(h / 2 * ss), fill=(20, 22, 21, 245),
                                outline=(250, 245, 230, 60), width=int(1 * ss))
            d.text((w / 2 * ss, h / 2 * ss), text, font=font(self.F_B, int(27 * k * ss)), fill=(245, 242, 232, 255), anchor="mm")
        return supersampled(w, h, draw, 2)

    def _caption_chunks(self) -> list[tuple[float, float, list]]:
        if hasattr(self, "_chunks"):
            return self._chunks
        chunks, cur = [], []
        f = font(self.F_XB, int(52 * self.k))
        for wd in self.tl.words:
            if self.tl.scenes and wd.start < self.tl.scenes[0].end and len(self.tl.scenes) > 1:
                continue  # gancho aparece no título do cartão
            test = cur + [wd]
            txt = " ".join(x.text for x in test)
            brk = cur and (len(test) > self.cap_words or f.getlength(txt) > self.caption_maxw * 0.92 or
                           cur[-1].text.endswith((".", "!", "?", ":", ";")) or (wd.start - cur[-1].end) > 0.45)
            if brk:
                chunks.append(cur)
                cur = [wd]
            else:
                cur = test
        if cur:
            chunks.append(cur)
        self._chunks = []
        for i, c in enumerate(chunks):
            end = chunks[i + 1][0].start if i + 1 < len(chunks) else c[-1].end + 0.6
            self._chunks.append((c[0].start, min(end, c[-1].end + 0.8), c))
        return self._chunks

    @lru_cache(maxsize=512)
    def _caption_img(self, chunk_idx: int, spoken: int) -> Image.Image:
        k = self.k
        _, _, words = self._caption_chunks()[chunk_idx]
        fsz = 62 if self.cap_style in ("karaoke", "bold") else 52  # sem caixa: letra maior
        f = font(self.F_XB, int(fsz * k))
        space = f.getlength(" ")
        lines = wrap(f, " ".join(w.text for w in words), self.caption_maxw - 60 * k)
        # mapeia palavras → linhas
        idx, rows = 0, []
        for ln in lines:
            n = len(ln.split())
            rows.append(words[idx: idx + n])
            idx += n
        lh = int(fsz * 1.27 * k)
        tw = max(sum(f.getlength(w.text) for w in r) + space * (len(r) - 1) for r in rows)
        padx, pady = int(30 * k), int(14 * k)
        w, h = int(tw + 2 * padx), int(lh * len(rows) + 2 * pady)
        th = self.th
        hi, white, dim = rgba(th.get("caption_hi", "#e9b440")), rgba(th.get("caption_text", "#f1efe6")), rgba(th.get("caption_dim", "#8d918a"))

        style = self.cap_style
        boxed = style in ("classic", "highlight")
        ink = (14, 14, 16, 255)

        def draw(d: ImageDraw.ImageDraw, ss: float):
            if boxed:
                d.rounded_rectangle((0, 0, (w - 1) * ss, (h - 1) * ss), int(16 * k * ss), fill=(*rgba(th.get("caption_bg", "#121814"))[:3], 238),
                                    outline=rgba(th.get("caption_border", "#5a4a1f")), width=int(2.5 * k * ss))
            fs = font(self.F_XB, int(fsz * k * ss))
            stroke = int(6 * k * ss)
            n = 0
            for ri, row in enumerate(rows):
                rw = sum(f.getlength(x.text) for x in row) + space * (len(row) - 1)
                x = (w - rw) / 2
                y = pady + lh * ri + lh / 2
                for wd in row:
                    ww = f.getlength(wd.text)
                    current = n == spoken - 1
                    if style == "highlight":  # palavra falada agora numa pílula colorida
                        if current:
                            d.rounded_rectangle(((x - 4 * k) * ss, (y - lh * 0.4) * ss, (x + ww + 4 * k) * ss, (y + lh * 0.38) * ss),
                                                int(10 * k * ss), fill=hi)
                        color = ink if current else (hi if wd.hi else white)
                        d.text((x * ss, y * ss), wd.text, font=fs, fill=color, anchor="lm")
                    elif style == "karaoke":  # sem caixa; contorno grosso, falado em destaque
                        color = hi if (n < spoken and (wd.hi or current)) else (white if n < spoken else (*white[:3], 150))
                        d.text((x * ss, y * ss), wd.text, font=fs, fill=color, anchor="lm", stroke_width=stroke, stroke_fill=ink)
                    elif style == "bold":  # sem caixa; só as palavras já faladas aparecem
                        if n < spoken:
                            color = hi if (wd.hi or current) else white
                            d.text(((x + 3 * k) * ss, (y + 5 * k) * ss), wd.text, font=fs, fill=(0, 0, 0, 150), anchor="lm")
                            d.text((x * ss, y * ss), wd.text, font=fs, fill=color, anchor="lm", stroke_width=stroke, stroke_fill=ink)
                    else:
                        color = hi if wd.hi else (white if n < spoken else dim)
                        d.text((x * ss, y * ss), wd.text, font=fs, fill=color, anchor="lm")
                    x += ww + space
                    n += 1
        return supersampled(w, h, draw, 2)

    def _draw_caption(self, out: Image.Image, t: float, cx: float) -> None:
        """Legenda do trecho atual, com a animação de entrada sorteada para o vídeo."""
        for ci, (st, en, words) in enumerate(self._caption_chunks()):
            if st - 0.05 <= t < en:
                spoken = sum(1 for w in words if w.start <= t + 0.03)
                img = self._caption_img(ci, spoken)
                p = t - st + 0.05
                dy, op = 0.0, 1.0
                if self.cap_anim == "rise":
                    dy, op = (1 - ease_out_cubic(p / 0.2)) * 28 * self.k, clamp(p / 0.12)
                elif self.cap_anim == "fade":
                    op = clamp(p / 0.15)
                elif self.cap_anim == "snap":
                    img = scaled(img, 1.0 + 0.06 * (1 - clamp(p / 0.08)))
                else:
                    img = scaled(img, 0.88 + 0.12 * ease_out_back(p / 0.18, 2.2))
                paste(out, img, (cx - img.width / 2, self.caption_cy - img.height / 2 + dy), op)
                break

    def _title_img(self, text: str, max_w: int, size: int) -> Image.Image:
        key = (text, max_w, size)
        if key in self._title_cache:
            return self._title_cache[key]
        f = font(self.F_SERIF, size, 800)
        lines = wrap(f, text.upper() if False else text, max_w)
        lh = int(size * 1.12)
        w, h = max_w, lh * len(lines) + 10

        def draw(d: ImageDraw.ImageDraw, ss: float):
            fs = font(self.F_SERIF, int(size * ss), 800)
            for i, ln in enumerate(lines):
                d.text((w / 2 * ss, (lh * i + lh / 2 + 4) * ss), ln, font=fs, fill=rgba(self.th.get("ink", "#0c3223")), anchor="mm")
        img = supersampled(w, h, draw, 2)
        if len(self._title_cache) > 200:
            self._title_cache.clear()
        self._title_cache[key] = img
        return img

    def _hook_line(self) -> str:
        """Manchete curta do gancho: texto da miniatura → 1ª frase curta da abertura → título."""
        import re
        tl = self.tl
        txt = (tl.hook or "").strip()
        if not txt and tl.scenes:
            first = re.split(r"(?<=[.!?])\s+", tl.scenes[0].text.strip())[0]
            txt = first if len(first.split()) <= 9 else ""
        if not txt:
            txt = re.sub(r"#\w+", "", tl.title).strip()
        ws = txt.split()
        if len(ws) > 9:
            txt = " ".join(ws[:8]).rstrip(",;:") + "…"
        return txt

    @lru_cache(maxsize=8)
    def _hook_img(self, kind: str, max_w: int, size: int) -> Image.Image:
        """Manchete do gancho em letra grande e alto contraste — nos Shorts já aparece no quadro 0 (antes do 1º deslize).
        kind: 'serif' (creme com sombra) · 'stroke' (branca com contorno) · 'gold' (destaque com contorno) · 'plain' (destaque liso)."""
        k = self.k
        serif = kind == "serif"
        text = self._hook_line() if serif else self._hook_line().upper()
        fname, wgt = (self.F_SERIF, 900) if serif else (self.F_XB, 900)  # 900: fontes variáveis (ex.: Montserrat) abrem finas
        while True:  # encolhe até caber em no máximo 3 linhas
            f = font(fname, size, wgt)
            lines = wrap(f, text, max_w)
            if len(lines) <= 3 or size <= 44 * k:
                break
            size = int(size * 0.9)
        stroke = 0 if kind == "plain" else max(2, int(size * (0.05 if serif else 0.085)))
        lh = int(size * 1.12)
        w = int(max(f.getlength(ln) for ln in lines) + 2 * stroke + 24 * k)
        h = int(lh * len(lines) + 2 * stroke + 16 * k)
        hi = rgba(self.th.get("caption_hi") or self.th.get("gold", "#e9b440"))
        fill = {"serif": (248, 236, 206, 255), "stroke": (250, 246, 236, 255)}.get(kind, hi)

        def draw(d: ImageDraw.ImageDraw, ss: float):
            fs = font(fname, int(size * ss), wgt)
            for i, ln in enumerate(lines):
                x, y = w / 2 * ss, (stroke + 8 * k + lh * i + lh / 2) * ss
                if serif:
                    d.text((x + 5 * k * ss, y + 6 * k * ss), ln, font=fs, fill=(0, 0, 0, 190), anchor="mm")
                d.text((x, y), ln, font=fs, fill=fill, anchor="mm", stroke_width=int(stroke * ss), stroke_fill=(8, 8, 10, 255))
        return supersampled(w, h, draw, 2)

    @lru_cache(maxsize=16)
    def _header(self, step: int) -> Image.Image:
        k, W = self.k, self.W
        h = int(80 * k)
        th = self.th

        def draw(d: ImageDraw.ImageDraw, ss: float):
            chip_w = 0
            if step and self.tl.steps:
                label = f"{th.get('step_label', 'PASSO')} {step}/{self.tl.steps}"
                fc = font(self.F_B, int(28 * k * ss))
                tw = fc.getlength(label) / ss
                dots = self.tl.steps
                chip_w = tw + 40 * k + dots * 20 * k + 12 * k
                x2 = W - 46 * k
                x1 = x2 - chip_w
                y1, y2 = h / 2 - 26 * k, h / 2 + 26 * k
                d.rounded_rectangle((x1 * ss, y1 * ss, x2 * ss, y2 * ss), int(26 * k * ss), fill=rgba(th.get("bg_edge", "#0a1e18"), 200),
                                    outline=rgba(th.get("gold", "#d9a53a"), 200), width=int(2 * k * ss))
                d.text(((x1 + 20 * k) * ss, h / 2 * ss), label, font=fc, fill=(240, 238, 228, 255), anchor="lm")
                for i in range(dots):
                    cx = x1 + 20 * k + tw + 18 * k + i * 20 * k
                    rr = 6.5 * k
                    col = rgba(th.get("gold", "#d9a53a")) if i < step else (70, 86, 78, 255)
                    d.ellipse(((cx - rr) * ss, (h / 2 - rr) * ss, (cx + rr) * ss, (h / 2 + rr) * ss), fill=col)
            ft = font(self.F_SERIF, int(34 * k * ss), 800)
            avail = W - 140 * k - chip_w - 70 * k
            title = ellipsize(font(self.F_SERIF, int(34 * k), 800), self.tl.title, avail)
            d.text((122 * k * ss, h / 2 * ss), title, font=ft, fill=(240, 232, 212, 255), anchor="lm")
        img = supersampled(W, h, draw, 2)
        paste(img, self.coin_small, (int(52 * k) - 4, h / 2 - self.coin_small.height / 2))
        return img

    @lru_cache(maxsize=1)
    def _outro(self) -> Image.Image:
        style = self.lk.get("outro", "classic")
        if style in ("handle", "minimal"):
            return self._outro_alt(style)
        k, W = self.k, self.W
        th = self.th
        h = int(420 * k)

        def draw(d: ImageDraw.ImageDraw, ss: float):
            y = 200 * k
            d.text((W / 2 * ss, y * ss), th.get("outro_title", "SEGUE PRA MAIS"), font=font(self.F_SERIF, int(62 * k * ss), 900),
                   fill=(242, 232, 208, 255), anchor="mm")
            fh = font(self.F_B, int(34 * k * ss))
            handle = th.get("handle", "")
            tw = fh.getlength(handle) / ss
            px, py = 28 * k, 26 * k
            y2 = y + 88 * k
            d.rounded_rectangle(((W / 2 - tw / 2 - px) * ss, (y2 - py) * ss, (W / 2 + tw / 2 + px) * ss, (y2 + py) * ss),
                                int(py * ss), fill=rgba(th.get("gold", "#d9a53a")))
            d.text((W / 2 * ss, y2 * ss), handle, font=fh, fill=(26, 22, 10, 255), anchor="mm")
            y3 = y2 + 78 * k
            fs = font(self.F_SERIF, int(25 * k * ss), 700)
            slogan = th.get("slogan", "")
            sw = fs.getlength(slogan) / ss
            d.text((W / 2 * ss, y3 * ss), slogan, font=fs, fill=(225, 214, 190, 255), anchor="mm")
            for sx in (-1, 1):
                xa = W / 2 + sx * (sw / 2 + 18 * k)
                xb = xa + sx * 70 * k
                d.line((xa * ss, y3 * ss, xb * ss, y3 * ss), fill=rgba(th.get("gold", "#d9a53a")), width=int(2 * k * ss))
        img = supersampled(W, h, draw, 2)
        paste(img, self.coin_big, (W / 2 - self.coin_big.width / 2, 200 * k - 150 * k - self.coin_big.height / 2 + 30 * k))
        return img

    def _outro_alt(self, style: str) -> Image.Image:
        """Encerramentos alternativos: @ gigante ('handle') ou só moeda + @ + slogan ('minimal')."""
        k, W = self.k, self.W
        th = self.th
        h = int(420 * k)
        handle = th.get("handle", "")
        gold = rgba(th.get("gold", "#d9a53a"))

        def draw(d: ImageDraw.ImageDraw, ss: float):
            if style == "handle":
                fh = font(self.F_XB, int(min(92, 1500 / max(8, len(handle))) * k * ss))
                d.text((W / 2 * ss, 190 * k * ss), handle, font=fh, fill=(250, 246, 234, 255), anchor="mm",
                       stroke_width=int(5 * k * ss), stroke_fill=(10, 10, 12, 255))
                fs = font(self.F_B, int(32 * k * ss))
                sub_ = th.get("outro_title", "SEGUE PRA MAIS")
                tw = fs.getlength(sub_) / ss
                y2 = 290 * k
                d.rounded_rectangle(((W / 2 - tw / 2 - 26 * k) * ss, (y2 - 28 * k) * ss, (W / 2 + tw / 2 + 26 * k) * ss, (y2 + 28 * k) * ss),
                                    int(28 * k * ss), fill=gold)
                d.text((W / 2 * ss, y2 * ss), sub_, font=fs, fill=(26, 22, 10, 255), anchor="mm")
            else:
                fh = font(self.F_B, int(40 * k * ss))
                d.text((W / 2 * ss, 250 * k * ss), handle, font=fh, fill=(245, 240, 226, 255), anchor="mm")
                fs = font(self.F_SERIF, int(26 * k * ss), 700)
                d.text((W / 2 * ss, 312 * k * ss), th.get("slogan", ""), font=fs, fill=(*gold[:3], 255), anchor="mm")
        img = supersampled(W, h, draw, 2)
        if style == "minimal":
            paste(img, self.coin_big, (W / 2 - self.coin_big.width / 2, 150 * k - self.coin_big.height / 2))
        return img

    # ================================================================ direção (animações variadas)

    def _setup_direction(self) -> None:
        tl, k = self.tl, self.k
        seed = sum(ord(c) for c in tl.title) * 31 + len(tl.scenes)
        self.plans = fx.plan_scenes(tl.scenes, seed)
        self.particles = fx.Particles(self.W, self.H, n=30 if self.vertical else 40, seed=seed)
        self.mouth = plan_mouth(tl.envelope, tl.fps)
        self.mascot = make_mascot(self.th, self.mascot_R, seed)
        # carimbos: (início, fim, imagem, centro)
        self.stamps: list[tuple[float, float, Image.Image, tuple[float, float]]] = []
        x1, y1, x2, y2 = self.card
        for sc, pl in zip(tl.scenes, self.plans):
            if sc.index == 0 and len(tl.scenes) > 1:
                continue
            if pl.badge:
                color = self.th.get("stamp_myth", "#b8322a") if pl.badge == "mito" else self.th.get("stamp_truth", "#1d7a45")
                img = fx.stamp(pl.badge.upper(), color, int(58 * k), 9 if pl.badge == "mito" else -8, self.F_SERIF)
                self.stamps.append((sc.start + 0.25, sc.end, img, (x2 - img.width / 2 - 34 * k, y1 + img.height / 2 + 26 * k)))
            if pl.year:
                ws = [w for w in sc.words if pl.year in w.text]
                t0 = ws[0].start if ws else sc.start + 0.5
                img = fx.stamp(pl.year, self.th.get("stamp_date", "#8f2a1f"), int(62 * k), -11, self.F_SERIF)
                self.stamps.append((t0, sc.end, img, (x2 - img.width / 2 - 70 * k, y2 - img.height / 2 - 60 * k)))
        self.impacts = [s[0] + 0.12 for s in self.stamps]
        gw, gh = (x2 - x1) - int(40 * k), (y2 - y1) - int(40 * k)
        self.graphics = {}
        for sc in tl.scenes:
            if sc.graphic and sc.graphic.get("kind") in infographics.KINDS:
                self.graphics[sc.index] = infographics.make(sc.graphic["kind"], sc.graphic.get("data") or {}, gw, gh, k,
                                                            self.th, sc.words, sc.start, sc.image)
        self._graphic_last: dict[int, Image.Image] = {}

    def _shake(self, t: float) -> tuple[float, float]:
        for t0 in self.impacts:
            dt = t - t0
            if 0 <= dt < 0.25:
                a = 9 * self.k * (1 - dt / 0.25)
                return a * math.sin(dt * 90), a * math.cos(dt * 70) * 0.6
        return 0.0, 0.0

    # ================================================================ quadro

    def frame(self, t: float, i: int) -> Image.Image:
        tl, k = self.tl, self.k
        if not hasattr(self, "plans"):
            self._setup_direction()
        out = self.bg.copy()
        self.particles.draw(out, t)
        in_outro = t >= tl.narration_end + 0.15
        sc = tl.scene_at(min(t, tl.narration_end - 0.01))
        is_intro = sc.index == 0 and len(tl.scenes) > 1

        pw = int(self.W * clamp(t / tl.duration))
        if pw > 0:
            out.alpha_composite(Image.new("RGBA", (pw, max(4, int(7 * k))), rgba(self.th.get("gold", "#d9a53a"))), (0, 0))

        if not is_intro or t > sc.start + 0.6:
            hdr_alpha = ease_out_cubic((t - sc.start - 0.6) / 0.4) if is_intro else 1.0
            paste(out, self._header(0 if (is_intro or in_outro) else sc.step),
                  (0, self.header_y - int(34 * k)), hdr_alpha)

        if in_outro:
            a = ease_out_cubic((t - tl.narration_end - 0.15) / 0.35)
            o = self._outro()
            cy = self.H * 0.42 if self.vertical else self.H * 0.45
            ox = 0 if self.vertical else -self.W * 0.14
            paste(out, o, (ox, cy - o.height / 2 + (1 - a) * 40 * k), a)
        else:
            self._draw_card(out, t, sc, is_intro, self._shake(t))

        # mascote com reações
        idx = min(i, len(self.mouth) - 1)
        talk = float(tl.envelope[idx]) if len(tl.envelope) else 0.0
        mouth = int(self.mouth[idx]) if len(self.mouth) else 0
        mood, mk = "normal", 0.0
        pl = self.plans[sc.index]
        local = t - sc.start
        if in_outro:
            dt = t - tl.narration_end - 0.15
            mood, mk, mouth, talk = ("wave", 1.0, 0, 0.0) if dt < 1.2 else ("happy", 1.0, 0, 0.0)
        elif pl.react == "surprise" and local < 0.8:
            mood, mk = "surprise", math.sin(math.pi * clamp(local / 0.8))
        if self.mascot is not None:
            m, (dx, dy) = self.mascot.frame(t, mouth, talk, mood, mk)
            out.alpha_composite(m, (int(self.mascot_c[0] - self.mascot.cx + dx), int(self.mascot_c[1] - self.mascot.cy + dy)))
        return out.convert("RGB")

    def _graphic_frame(self, sc: SceneT, t: float) -> Image.Image:
        g = self.graphics[sc.index]
        local = max(0.0, t - sc.start - fx.EXIT_DUR * 0.4)
        if t >= sc.end - 0.02 and sc.index in self._graphic_last:
            return self._graphic_last[sc.index]
        img = g.render(local, max(0.5, sc.end - sc.start - fx.EXIT_DUR * 0.4))
        if t >= sc.end - 0.05:
            self._graphic_last[sc.index] = img
        return img

    @lru_cache(maxsize=1)
    def _card_clip(self) -> Image.Image:
        x1, y1, x2, y2 = self.card
        ins = int(6 * self.k)
        m = Image.new("L", (x2 - x1, y2 - y1), 0)
        m.paste(rounded_mask(x2 - x1 - 2 * ins, y2 - y1 - 2 * ins, int(20 * self.k)), (ins, ins))
        return m

    def _place(self, out: Image.Image, img: Image.Image | None, cx: float, cy: float, op: float) -> None:
        if img is not None and op > 0.01:
            paste(out, img, (cx - img.width / 2, cy - img.height / 2), min(1.0, op))

    def _draw_card(self, out: Image.Image, t: float, sc: SceneT, is_intro: bool, shake: tuple[float, float]) -> None:
        tl, k = self.tl, self.k
        x1, y1, x2, y2 = self.card
        sx, sy = shake
        cw, ch = x2 - x1, y2 - y1
        paste(out, self.card_img, (x1 - self.card_pad + sx, y1 - self.card_pad + sy))
        local = t - sc.start
        dur = max(0.1, sc.end - sc.start)
        pl = self.plans[sc.index]

        if is_intro:
            spoken = [w for w in sc.words if w.start <= t + 0.05]
            text = " ".join(w.text for w in spoken)
            size = int((58 if len(sc.text) < 70 else 50) * k)
            if text:
                paste(out, self._title_img(text, int(cw - 120 * k), size), (x1 + 60 * k, y1 + 50 * k))
            if sc.image is not None:
                w, h = self._image_box(sc.image, True)
                if self.vertical:  # Shorts: a foto já entra grande e se mexendo no quadro 0
                    ar = clamp(sc.image.width / sc.image.height, 0.62, 1.9)
                    w = int(min(cw * 0.74, ch * 0.56 * ar))
                    h = int(w / ar)
                    grow = 0.82 + 0.18 * ease_out_cubic(local / min(dur, 1.5))
                    z = 1.18 - 0.1 * ease_out_cubic(local / 1.2) + 0.06 * local / dur
                else:
                    grow, z = 0.6 + 0.4 * ease_out_cubic(local / dur), 1 + 0.08 * local / dur
                fi = fx._scale(self._framed_image(sc.index, w, h, z), grow)
                self._place(out, fi, x1 + cw / 2, y1 + ch * 0.66, 1)
            if self.vertical:  # manchete do gancho entre o cartão e o mascote, legível desde o 1º quadro
                hk = self._hook_img("gold", int(self.caption_maxw), int(80 * k))
                hk = scaled(hk, 1 + 0.08 * (1 - ease_out_cubic(local / 0.3)))
                top_m = self.mascot_c[1] - self.mascot_R * 1.3
                self._place(out, hk, self.W / 2, (y2 + top_m) / 2, 1)
            return

        ccx, ccy = cw / 2, ch / 2 + 18 * k
        layer = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        # saída da imagem anterior
        prev = tl.scenes[sc.index - 1] if sc.index > 0 else None
        if prev is not None and prev.index > 0 and prev.index in self.graphics and pl.enter != "none" and local < fx.EXIT_DUR:
            gimg = self._graphic_frame(prev, prev.end - 0.01)
            img, dx, dy, op = fx.apply_exit(gimg, pl.exit if pl.exit != "shrink" else "out_up", local / fx.EXIT_DUR, self.W)
            self._place(layer, img, cw / 2 + dx, ch / 2 + dy, op)
        elif prev is not None and prev.index > 0 and pl.enter != "none" and local < fx.EXIT_DUR and prev.image is not None:
            ppl = self.plans[prev.index]
            w, h = self._image_box(prev.image, False)
            z, foc, _ = fx.motion_params(ppl.motion, 1.0, ppl.focus)
            img, dx, dy, op = fx.apply_exit(self._framed_image(prev.index, w, h, z, foc), pl.exit, local / fx.EXIT_DUR, self.W)
            self._place(layer, img, ccx + dx, ccy + dy, op)

        if sc.index in self.graphics:
            ep = (local - fx.EXIT_DUR * 0.4) / 0.35
            if ep >= 0:
                g = self._graphic_frame(sc, t)
                op = clamp(ep * 1.5)
                self._place(layer, g, cw / 2, ch / 2 + (1 - ease_out_cubic(ep)) * 30 * k, op)
        elif sc.image is not None:
            w, h = self._image_box(sc.image, False)
            # cenas que reaproveitam a imagem continuam o movimento da anterior
            base = sc
            while base.index > 1 and self.plans[base.index].enter == "none":
                base = tl.scenes[base.index - 1]
            bpl = self.plans[base.index]
            span = max(0.1, sc.end - base.start)
            z, foc, rot = fx.motion_params(bpl.motion, (t - base.start) / span, bpl.focus)
            delay = fx.EXIT_DUR * 0.5 if (base is sc and bpl.enter not in ("none", "flip", "iris")) else 0
            ep = (t - base.start - delay) / fx.ENTER_DUR.get(bpl.enter, 0.4)
            if bpl.enter == "zoom_reveal" and ep < 1:
                z *= 2.3 - 1.3 * ease_out_cubic(max(0.0, ep))
            if ep >= 0:
                img = self._framed_image(sc.index, w, h, z, foc, t)
                if abs(rot) > 0.05:
                    img = fx._rot(img, rot)
                img, dx, dy, op = fx.apply_enter(img, bpl.enter, ep)
                self._place(layer, img, ccx + dx, ccy + dy, op)
        layer.putalpha(ImageChops.multiply(layer.getchannel("A"), self._card_clip()))
        out.alpha_composite(layer, (int(x1 + sx), int(y1 + sy)))
        if sc.label and sc.index not in self.graphics:
            lb = self._label(sc.label)
            a = ease_out_cubic((local - 0.2) / 0.3)
            paste(out, lb, (x1 + 26 * k - (1 - a) * 30 * k + sx, y1 + 34 * k + sy), a)

        # carimbos (mito / verdade / ano)
        for t0, t1, img, (px, py) in self.stamps:
            if t0 <= t < t1:
                simg, op = fx.stamp_anim(img, t - t0)
                self._place(out, simg, px + sx, py + sy, op * 0.92)

        # legenda (não treme)
        self._draw_caption(out, t, x1 + cw / 2)
