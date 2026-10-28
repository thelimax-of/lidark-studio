"""Tela final dos vídeos LONGOS (últimos 20 s): "assista o próximo" + inscrição, com o tema do canal.

A API do YouTube não cria telas finais nem cards (não existe recurso para isso na Data API v3), então o vídeo já sai
com o palco pronto: uma moldura 16:9 à esquerda (onde entra o elemento "vídeo/playlist") e um círculo à direita (onde
entra o elemento "inscrever-se") — no Studio é só encaixar os elementos em cima. Sem eles, a tela continua
completa (títulos + @ do canal). O mascote acena num canto, sem balão de fala e longe dos textos.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

from .core import clamp, ease_out_cubic, ellipsize, font, paste, rgba, supersampled
from .characters import make_mascot

END_SCREEN_SECONDS = 20.0  # máximo que o YouTube permite para a tela final (elementos só nos últimos 5-20 s)


class EndCard:
    def __init__(self, tpl):
        self.tpl = tpl
        tl, th = tpl.tl, tpl.th
        self.W, self.H, self.k = tpl.W, tpl.H, tpl.k
        self.t0 = tl.narration_end + 0.15
        k = self.k
        self.gold = th.get("gold", "#d9a53a")
        # áreas dos elementos do YouTube (em px do vídeo): vídeo 16:9 à esquerda, inscrição (círculo) à direita
        self.video_box = (int(250 * k), int(300 * k), int(1090 * k), int(300 * k + 840 * k * 9 / 16))
        self.sub_c, self.sub_r = (int(1480 * k), int(470 * k)), int(150 * k)
        self.base = self._base()
        fr = [self._frames(1.0), self._frames(0.45)]
        box = fr[0].getbbox() or (0, 0, self.W, self.H)  # só a área dos contornos (colar o quadro inteiro custa caro)
        self.frames_on, self.frames_xy = [f.crop(box) for f in fr], box[:2]
        seed = sum(ord(c) for c in tl.title)
        self.mascot = make_mascot(th, int(118 * k), seed + 7)
        self.mascot_xy = (int(1745 * k), int(1035 * k))  # canto inferior direito: pés na base, longe dos textos
        self._last: Image.Image | None = None

    # ---------------------------------------------------------------- estático

    def _base(self) -> Image.Image:
        """Fundo do tema + última foto do vídeo bem desfocada (continuidade) + títulos."""
        tpl, W, H, k = self.tpl, self.W, self.H, self.k
        th = tpl.th
        out = tpl.bg.copy().convert("RGBA")
        img = next((s.image for s in reversed(tpl.tl.scenes) if s.image is not None), None)
        if img is not None:
            ph = img.convert("RGB")
            s = max(W / ph.width, H / ph.height)
            ph = ph.resize((max(1, int(ph.width * s)), max(1, int(ph.height * s))), Image.BILINEAR)
            ph = ph.crop(((ph.width - W) // 2, (ph.height - H) // 2, (ph.width - W) // 2 + W, (ph.height - H) // 2 + H))
            ph = ph.filter(ImageFilter.GaussianBlur(28 * k)).convert("RGBA")
            ph.putalpha(55)
            out.alpha_composite(ph)
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))  # escurece as bordas: os elementos do YouTube ganham contraste
        ImageDraw.Draw(shade).rectangle((0, 0, W, H), fill=(0, 0, 0, 60))
        out.alpha_composite(shade)
        x0, y0, x1, y1 = self.video_box
        cx, cy = self.sub_c
        series = str(th.get("_series") or "").strip()
        handle = th.get("handle", "")
        cream, gold = (242, 232, 208, 255), rgba(self.gold)
        f_serif, f_ui = tpl.F_SERIF, tpl.F_B

        def draw(d: ImageDraw.ImageDraw, ss: float):
            vx = (x0 + x1) / 2
            fh = font(f_serif, int(60 * k * ss), 900)
            d.text((vx * ss, 222 * k * ss), th.get("end_next", "ASSISTA O PRÓXIMO"), font=fh, fill=cream, anchor="mm")
            fs = font(f_serif, int(52 * k * ss), 900)
            d.text((cx * ss, 222 * k * ss), th.get("end_subscribe", "INSCREVA-SE"), font=fs, fill=cream, anchor="mm")
            for (xa, xb) in ((vx - 70 * k, vx + 70 * k), (cx - 60 * k, cx + 60 * k)):  # filete dourado sob os títulos
                d.line((xa * ss, 262 * k * ss, xb * ss, 262 * k * ss), fill=gold, width=int(3 * k * ss))
            # fundo translúcido das áreas (o elemento do YouTube cobre por cima)
            d.rounded_rectangle((x0 * ss, y0 * ss, x1 * ss, y1 * ss), int(18 * k * ss), fill=(0, 0, 0, 120))
            r = self.sub_r
            d.ellipse(((cx - r) * ss, (cy - r) * ss, (cx + r) * ss, (cy + r) * ss), fill=(0, 0, 0, 120))
            # ícones discretos: ▶ no vídeo, sino na inscrição
            pr = 46 * k
            d.ellipse(((vx - pr) * ss, ((y0 + y1) / 2 - pr) * ss, (vx + pr) * ss, ((y0 + y1) / 2 + pr) * ss),
                      outline=(255, 255, 255, 70), width=int(4 * k * ss))
            my = (y0 + y1) / 2
            d.polygon([((vx - 14 * k) * ss, (my - 22 * k) * ss), ((vx - 14 * k) * ss, (my + 22 * k) * ss),
                       ((vx + 24 * k) * ss, my * ss)], fill=(255, 255, 255, 80))
            bw = 40 * k
            d.chord(((cx - bw) * ss, (cy - bw * 1.1) * ss, (cx + bw) * ss, (cy + bw * 1.1) * ss), 180, 360, fill=(255, 255, 255, 70))
            d.rectangle(((cx - bw) * ss, (cy - 2 * k) * ss, (cx + bw) * ss, (cy + 26 * k) * ss), fill=(255, 255, 255, 70))
            d.rounded_rectangle(((cx - bw * 1.3) * ss, (cy + 24 * k) * ss, (cx + bw * 1.3) * ss, (cy + 36 * k) * ss),
                                int(6 * k * ss), fill=(255, 255, 255, 70))
            d.ellipse(((cx - 10 * k) * ss, (cy + 38 * k) * ss, (cx + 10 * k) * ss, (cy + 58 * k) * ss), fill=(255, 255, 255, 70))
            # legenda das áreas: série (maratona) embaixo do vídeo, @ do canal embaixo do círculo
            if series:
                fl = font(f_ui, int(30 * k * ss))
                txt = ellipsize(fl, f"SÉRIE · {series.upper()}", (x1 - x0) * ss)
                d.text((vx * ss, (y1 + 58 * k) * ss), txt, font=fl, fill=gold, anchor="mm")
            if handle:
                fp = font(f_ui, int(34 * k * ss))
                tw = fp.getlength(handle) / ss
                py, px, ph_ = cy + self.sub_r + 70 * k, 28 * k, 26 * k
                d.rounded_rectangle(((cx - tw / 2 - px) * ss, (py - ph_) * ss, (cx + tw / 2 + px) * ss, (py + ph_) * ss),
                                    int(ph_ * ss), fill=gold)
                d.text((cx * ss, py * ss), handle, font=fp, fill=(26, 22, 10, 255), anchor="mm")
        out.alpha_composite(supersampled(W, H, draw, 2))
        return out

    def _frames(self, strength: float) -> Image.Image:
        """Contorno tracejado dourado das áreas (pulsa devagar, chamando o olho para os elementos)."""
        W, H, k = self.W, self.H, self.k
        x0, y0, x1, y1 = self.video_box
        cx, cy = self.sub_c
        col = (*rgba(self.gold)[:3], int(235 * strength))

        def draw(d: ImageDraw.ImageDraw, ss: float):
            w = max(2, int(4 * k * ss))
            dash, gap = 26 * k, 14 * k
            # retângulo tracejado
            for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
                n = math.hypot(bx - ax, by - ay)
                p = 0.0
                while p < n:
                    q = min(n, p + dash)
                    d.line(((ax + (bx - ax) * p / n) * ss, (ay + (by - ay) * p / n) * ss,
                            (ax + (bx - ax) * q / n) * ss, (ay + (by - ay) * q / n) * ss), fill=col, width=w)
                    p = q + gap
            # círculo tracejado
            r = self.sub_r
            steps = int(2 * math.pi * r / (dash + gap))
            for i in range(steps):
                a0 = 360 * i / steps
                d.arc(((cx - r) * ss, (cy - r) * ss, (cx + r) * ss, (cy + r) * ss), a0, a0 + 360 * dash / (dash + gap) / steps,
                      fill=col, width=w)
        return supersampled(W, H, draw, 2)

    # ---------------------------------------------------------------- quadro

    def frame(self, t: float, i: int) -> Image.Image:
        tpl, k = self.tpl, self.k
        tl = tpl.tl
        dt = t - self.t0
        a = ease_out_cubic(clamp(dt / 0.6))
        out = self.base.copy()
        tpl.particles.draw(out, t)
        pulse = 0.5 + 0.5 * math.sin(dt * 2 * math.pi / 2.4)
        paste(out, self.frames_on[1], self.frames_xy, a)
        paste(out, self.frames_on[0], self.frames_xy, a * pulse)
        pw = int(self.W * clamp(t / tl.duration))  # barra de progresso do tema
        if pw > 0:
            out.alpha_composite(Image.new("RGBA", (pw, max(4, int(7 * k))), rgba(self.gold)), (0, 0))
        if self.mascot is not None:  # acena e fica feliz; sem balão, no canto (nunca sobre títulos ou áreas)
            mood = "wave" if dt < 1.4 else "happy"
            m, (mdx, mdy) = self.mascot.frame(t, 0, 0.0, mood, 1.0)
            rise = (1 - ease_out_cubic(clamp((dt - 0.2) / 0.6))) * 260 * k
            x = self.mascot_xy[0] - self.mascot.cx + mdx
            y = self.mascot_xy[1] - m.height + mdy + rise
            out.alpha_composite(m, (int(x), int(y)))
        if a < 1:  # entra por cima do último quadro da narração
            if self._last is None:
                t_last = max(0.0, tl.narration_end - 0.05)
                self._last = tpl.frame(t_last, int(t_last * tl.fps)).convert("RGBA")
            out = Image.blend(self._last, out, a)
        return out.convert("RGB")
