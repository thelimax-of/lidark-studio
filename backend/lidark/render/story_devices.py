"""Dispositivos do Modo História — a voz sai deles.

Momentos de tela cheia/inserts animados: TV (plantão com âncora e letreiro), rádio receptor (dial + LEDs de nível),
celular (bloqueio com notificação, alerta de emergência, conversa com áudio de voz, chamada recebida), rádio de bordo
(comms, espaço), monitor (laboratório), jornaleiro (pregão "EXTRA!") e edital. Entram deslizando, com brilho de tela,
scanlines e nível animado pela voz (lv = 0..1, envelope da fala do dispositivo naquele quadro).
O áudio de cada papel recebe o filtro do aparelho em render/story.py (DEVICE_AF).
"""
from __future__ import annotations

import math
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from .story_hud import Hud, _paper_texture, back, ease, fit, font, icon, place, shadowed, wrap


def _enter(lt: float, dur: float) -> tuple[float, float]:
    a = ease(lt / 0.35) * (1 - ease((lt - (dur - 0.3)) / 0.3))
    return a, back(min(1.0, lt / 0.45))


def _scanlines(c: Image.Image, box: tuple, step: int, alpha: int = 34) -> None:
    d = ImageDraw.Draw(c)
    for y in range(int(box[1]), int(box[3]), max(2, step)):
        d.line((box[0], y, box[2], y), fill=(0, 0, 0, alpha))


def _glow(c: Image.Image, box: tuple, color: tuple, r: int) -> Image.Image:
    pad = r * 2
    g = Image.new("RGBA", (c.width + 2 * pad, c.height + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(g).rounded_rectangle((box[0] + pad, box[1] + pad, box[2] + pad, box[3] + pad), r, fill=tuple(color[:3]) + (150,))
    g = g.filter(ImageFilter.GaussianBlur(r))
    g.alpha_composite(c, (pad, pad))
    return g


def tv_set(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any], lv: float = 0.0) -> None:
    a, k = _enter(lt, dur)
    if a <= 0:
        return
    retro = h.style in ("historia", "futebol", "espaco")
    W = h.s(640) if h.vertical else int(h.W * 0.56)
    Hh = int(W * 0.8)
    head = str(data.get("headline") or "").upper()
    tick = str(data.get("ticker") or head)
    tag = str(data.get("tag") or "PLANTÃO").upper()
    who = str(data.get("anchor") or "").upper()

    def body() -> Image.Image:
        c = Image.new("RGBA", (W, Hh + h.s(44)), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        col = (96, 62, 36, 255) if retro else (24, 24, 28, 255)
        d.rounded_rectangle((0, 0, W - 1, Hh - 1), h.s(34), fill=col, outline=(20, 14, 10, 255), width=h.s(4))
        if retro:
            for i in range(2):
                y = Hh * (0.3 + i * 0.25)
                d.ellipse((W - h.s(72), y, W - h.s(30), y + h.s(42)), fill=(40, 26, 16, 255))
            for x in (0.2, 0.74):
                d.rectangle((W * x, Hh, W * (x + 0.06), Hh + h.s(40)), fill=(40, 26, 16, 255))
        return c
    c = h.cached(("tvbody", W, retro), body).copy()
    d = ImageDraw.Draw(c)
    sx0, sy0 = h.s(30), h.s(30)
    sx1, sy1 = W - (h.s(100) if retro else h.s(30)), Hh - h.s(30)
    fl = 0.92 + 0.08 * math.sin(lt * 37)
    bgc = tuple(int(v * fl) for v in (70, 92, 116)) + (255,)
    d.rounded_rectangle((sx0, sy0, sx1, sy1), h.s(26 if retro else 8), fill=bgc)
    sw, shh = sx1 - sx0, sy1 - sy0
    s = shh / 330
    cx, top = sx0 + sw * 0.5, sy0 + shh * 0.14 - lv * h.s(2)
    d.ellipse((cx - 34 * s, top, cx + 34 * s, top + 70 * s), fill=(22, 28, 42, 255))
    d.rounded_rectangle((cx - 80 * s, top + 74 * s, cx + 80 * s, top + 200 * s), int(40 * s), fill=(22, 28, 42, 255))
    by = sy0 + shh * 0.6
    d.rectangle((sx0, by, sx0 + sw * 0.34, by + shh * 0.12), fill=h.danger + (255,))
    d.text((sx0 + sw * 0.17, by + shh * 0.06), tag, font=fit(tag, h.f_title, sw * 0.3, h.s(30)), fill=(255, 255, 255), anchor="mm")
    d.rectangle((sx0, by + shh * 0.12, sx1, by + shh * 0.27), fill=(245, 245, 245, 245))
    d.text((sx0 + h.s(12), by + shh * 0.195), head, font=fit(head, h.f_title, sw - h.s(24), h.s(32), h.s(14)), fill=(15, 15, 20), anchor="lm")
    if who:
        d.text((sx0 + sw * 0.36, by + shh * 0.06), who, font=fit(who, h.f_ui, sw * 0.6, h.s(16)), fill=(235, 235, 245), anchor="lm")
    ty = by + shh * 0.27
    d.rectangle((sx0, ty, sx1, sy1), fill=(15, 20, 40, 240))
    ft = h.F("ui", 16)
    unit = ft.getlength(tick + "   •   ")
    off = (lt * h.s(110)) % max(1.0, unit)
    band = Image.new("RGBA", (int(sx1 - sx0), max(1, int(sy1 - ty))), (0, 0, 0, 0))  # só dentro da tela
    ImageDraw.Draw(band).text((h.s(8) - off, band.height / 2), (tick + "   •   ") * 4, font=ft, fill=(240, 240, 240), anchor="lm")
    c.alpha_composite(band, (int(sx0), int(ty)))
    _scanlines(c, (sx0, sy0, sx1, sy1), h.s(3))
    c = _glow(c, (sx0, sy0, sx1, sy1), bgc, h.s(24))
    h.put(base, c, (h.W - c.width) / 2, place(h, data, 0.5, c.height) + (1 - k) * h.s(260), a)


def radio_set(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any], lv: float = 0.0) -> None:
    a, k = _enter(lt, dur)
    if a <= 0:
        return
    W = h.s(640) if h.vertical else int(h.W * 0.5)
    Hh = int(W * 0.56)
    st = str(data.get("station") or "RÁDIO").upper()[:22]
    dx0 = int(W * 0.5)

    def body() -> Image.Image:
        c = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, W - 1, Hh - 1), h.s(40), fill=(110, 64, 34, 255), outline=(50, 28, 14, 255), width=h.s(5))
        gx0, gy0, gx1, gy1 = h.s(26), h.s(26), int(W * 0.45), Hh - h.s(26)
        d.rounded_rectangle((gx0, gy0, gx1, gy1), h.s(24), fill=(60, 36, 20, 255))
        for yy in range(gy0 + h.s(14), gy1 - h.s(6), h.s(16)):
            for xx in range(gx0 + h.s(14), gx1 - h.s(6), h.s(16)):
                d.ellipse((xx - h.s(4), yy - h.s(4), xx + h.s(4), yy + h.s(4)), fill=(30, 18, 10, 255))
        d.rounded_rectangle((dx0, h.s(30), W - h.s(30), int(Hh * 0.45)), h.s(12), fill=(238, 220, 168, 255))
        for i, f in enumerate(("55", "60", "70", "80", "100", "130", "160")):
            x = dx0 + h.s(20) + i * (W - h.s(50) - dx0 - h.s(20)) / 6
            d.line((x, h.s(40), x, h.s(56)), fill=(70, 45, 20), width=h.s(2))
            d.text((x, h.s(72)), f, font=h.F("ui", 13), fill=(70, 45, 20), anchor="mm")
        d.text((dx0 + h.s(8), int(Hh * 0.45) + h.s(30)), st, font=fit(st, h.f_ui, W - dx0 - h.s(40), h.s(24)), fill=(240, 220, 170), anchor="lm")
        for i in range(2):
            cx = dx0 + h.s(50) + i * h.s(120)
            d.ellipse((cx - h.s(28), Hh - h.s(86), cx + h.s(28), Hh - h.s(30)), fill=(60, 36, 20, 255), outline=(30, 18, 10, 255), width=h.s(3))
        return c
    c = h.cached(("radiobody", W, st), body).copy()
    d = ImageDraw.Draw(c)
    nx = dx0 + h.s(20) + (W - h.s(70) - dx0) * (0.55 + 0.03 * math.sin(lt * 0.9))
    d.line((nx, h.s(34), nx, int(Hh * 0.45) - h.s(6)), fill=h.danger, width=h.s(3))
    lit = int(12 * min(1.0, lv * 1.15))
    for i in range(12):
        x = dx0 + h.s(10) + i * h.s(18)
        col = (90, 220, 90) if i < 8 else ((240, 200, 60) if i < 10 else (230, 60, 50))
        d.rectangle((x, int(Hh * 0.6), x + h.s(12), int(Hh * 0.6) + h.s(14)), fill=col + ((255,) if i < lit else (50,)))
    if int(lt * 2) % 2 == 0:
        d.ellipse((W - h.s(66), int(Hh * 0.6) - h.s(4), W - h.s(44), int(Hh * 0.6) + h.s(18)), fill=h.danger + (255,))
    c = shadowed(c, blur=12)
    shake = h.s(2) * lv * math.sin(lt * 80)
    h.put(base, c, (h.W - c.width) / 2 + shake, place(h, data, 0.5, c.height) + (1 - k) * h.s(220), a)


def phone_screen(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any], lv: float = 0.0) -> None:
    """mode: lock (notificação) | alert (alerta de emergência) | chat (mensagens + áudio de voz tocando) | call."""
    a, k = _enter(lt, dur)
    if a <= 0:
        return
    mode = str(data.get("mode") or "lock")
    PW = h.s(400) if h.vertical else int(h.H * 0.46)
    PH = int(PW * 2.0)
    c = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, PW - 1, PH - 1), h.s(54), fill=(14, 14, 18, 255), outline=(70, 70, 80, 255), width=h.s(3))
    sx0, sy0, sx1, sy1 = h.s(14), h.s(14), PW - h.s(14), PH - h.s(14)
    scr = (10, 20, 40) if mode != "alert" else (150, 14, 14)
    if mode == "alert":
        pul = 0.5 + 0.5 * math.sin(lt * 8)
        scr = (int(140 + 70 * pul), 14, 14)
    d.rounded_rectangle((sx0, sy0, sx1, sy1), h.s(42), fill=scr + (255,))
    d.rounded_rectangle((PW / 2 - h.s(46), sy0 + h.s(10), PW / 2 + h.s(46), sy0 + h.s(34)), h.s(12), fill=(0, 0, 0, 255))
    clk = str(data.get("clock") or "21:47")
    d.text((sx0 + h.s(30), sy0 + h.s(22)), clk, font=h.F("ui", 15), fill=(240, 240, 240), anchor="lm")
    cw = sx1 - sx0
    fb = h.F("ui", 19)
    if mode == "lock":
        d.text((PW / 2, sy0 + h.s(130)), clk, font=h.F("title", 76), fill=(240, 240, 250), anchor="mm")
        nk = ease((lt - 0.5) / 0.3)
        if nk > 0:
            ny = sy0 + h.s(230) - (1 - nk) * h.s(40)
            lines = wrap(str(data.get("body") or ""), fb, cw - h.s(60))[:4]
            nh = h.s(84) + len(lines) * h.s(27)
            d.rounded_rectangle((sx0 + h.s(14), ny, sx1 - h.s(14), ny + nh), h.s(22), fill=(240, 240, 245, int(235 * nk)))
            d.text((sx0 + h.s(34), ny + h.s(24)), str(data.get("app") or "Mensagens").upper(), font=h.F("ui", 14), fill=(110, 110, 120), anchor="lm")
            t = str(data.get("title") or "")
            d.text((sx0 + h.s(34), ny + h.s(52)), t, font=fit(t, h.f_ui, cw - h.s(60), h.s(21)), fill=(20, 20, 25), anchor="lm")
            for i, ln in enumerate(lines):
                d.text((sx0 + h.s(34), ny + h.s(72) + i * h.s(27)), ln, font=fb, fill=(50, 50, 60))
    elif mode == "alert":
        icon(d, "warn", PW / 2, sy0 + h.s(150), h.s(46), (255, 230, 80))
        app = str(data.get("app") or "ALERTA EXTREMO").upper()
        d.text((PW / 2, sy0 + h.s(240)), app, font=fit(app, h.f_title, cw - h.s(40), h.s(34)), fill=(255, 255, 255), anchor="mm")
        txt = (str(data.get("title") or "") + ". " + str(data.get("body") or "")).strip(". ")
        for i, ln in enumerate(wrap(txt, fb, cw - h.s(50))[:8]):
            d.text((PW / 2, sy0 + h.s(300) + i * h.s(30)), ln, font=fb, fill=(255, 240, 240), anchor="mm")
    elif mode == "call":
        name = str(data.get("title") or data.get("from") or "Desconhecido")
        d.text((PW / 2, sy0 + h.s(110)), "chamada recebida…", font=h.F("ui", 18), fill=(190, 200, 220), anchor="mm")
        r = h.s(70) * (1 + 0.05 * math.sin(lt * 6))
        d.ellipse((PW / 2 - r, sy0 + h.s(260) - r, PW / 2 + r, sy0 + h.s(260) + r), fill=(80, 100, 140, 255))
        d.text((PW / 2, sy0 + h.s(260)), name[:1].upper(), font=h.F("title", 70), fill=(255, 255, 255), anchor="mm")
        d.text((PW / 2, sy0 + h.s(370)), name, font=fit(name, h.f_ui, cw - h.s(40), h.s(30)), fill=(255, 255, 255), anchor="mm")
        for i, col in enumerate(((220, 60, 50), (60, 190, 90))):
            cx = PW / 2 + (-1 if i == 0 else 1) * h.s(90)
            rr = h.s(38) * (1 + (0.12 * abs(math.sin(lt * 5)) if i == 1 else 0))
            d.ellipse((cx - rr, sy1 - h.s(120) - rr, cx + rr, sy1 - h.s(120) + rr), fill=col + (255,))
    else:  # chat com áudio de voz
        d.rectangle((sx0, sy0 + h.s(44), sx1, sy0 + h.s(100)), fill=(30, 40, 60, 255))
        t = str(data.get("title") or data.get("from") or "Conversa")
        d.text((sx0 + h.s(24), sy0 + h.s(72)), t, font=fit(t, h.f_ui, cw - h.s(40), h.s(20)), fill=(240, 240, 250), anchor="lm")
        y = sy0 + h.s(120)
        msgs = [m for m in (data.get("messages") or []) if isinstance(m, dict)][:4] or [{"audio": True}]
        per = max(0.5, (dur - 0.5) / max(1, len(msgs)))
        for i, m in enumerate(msgs):
            if ease((lt - 0.2 - i * per * 0.5) / 0.25) <= 0:
                break
            me = bool(m.get("me"))
            bw = int(cw * 0.8)
            x = sx1 - bw - h.s(12) if me else sx0 + h.s(12)
            fill = (210, 245, 190, 255) if me else (245, 245, 250, 255)
            if m.get("audio"):
                bh = h.s(76)
                d.rounded_rectangle((x, y, x + bw, y + bh), h.s(20), fill=fill)
                cy = y + bh / 2 - h.s(4)
                who = str(m.get("from") or data.get("title") or "?")[:1].upper()
                ax = x + h.s(36)
                d.ellipse((ax - h.s(24), cy - h.s(24), ax + h.s(24), cy + h.s(24)), fill=(90, 160, 120, 255))
                d.text((ax, cy), who, font=h.F("title", 26), fill=(255, 255, 255), anchor="mm")
                start, total = 0.35, max(0.6, dur - 0.7)
                prog = min(1.0, max(0.0, (lt - start) / total))
                playing = 0 < prog < 1
                px = x + h.s(84)
                if playing:  # pausa
                    for dx in (0, h.s(10)):
                        d.rectangle((px + dx - h.s(2), cy - h.s(11), px + dx + h.s(4), cy + h.s(11)), fill=(70, 70, 80))
                else:  # play
                    d.polygon([(px - h.s(4), cy - h.s(13)), (px - h.s(4), cy + h.s(13)), (px + h.s(16), cy)], fill=(70, 70, 80))
                wx0, wx1 = x + h.s(112), x + bw - h.s(18)
                n = max(10, int((wx1 - wx0) / h.s(8)))
                for j in range(n):  # forma de onda FIXA (como num app); a parte já ouvida fica azul
                    amp = h.s(6) + h.s(22) * (0.35 + 0.65 * abs(math.sin(j * 1.37) * math.cos(j * 0.53)))
                    bx = wx0 + j * (wx1 - wx0) / n
                    d.rounded_rectangle((bx, cy - amp / 2, bx + h.s(4), cy + amp / 2), h.s(2),
                                        fill=(52, 150, 230) if j / n <= prog else (165, 170, 180))
                dot = wx0 + (wx1 - wx0) * prog
                d.ellipse((dot - h.s(7), cy - h.s(7), dot + h.s(7), cy + h.s(7)), fill=(52, 150, 230))
                secs = (lt - start) if playing else total
                d.text((wx0, y + bh - h.s(12)), f"0:{int(max(0, secs)):02d}", font=h.F("ui", 13), fill=(110, 115, 125), anchor="lm")
            else:
                lines = wrap(str(m.get("text", "")), fb, bw - h.s(30))[:4]
                bh = h.s(20) + len(lines) * h.s(27) + (h.s(22) if m.get("from") and not me else 0)
                d.rounded_rectangle((x, y, x + bw, y + bh), h.s(18), fill=fill)
                yy = y + h.s(10)
                if m.get("from") and not me:
                    d.text((x + h.s(16), yy), str(m["from"]), font=h.F("ui", 15), fill=h.danger)
                    yy += h.s(22)
                for j, ln in enumerate(lines):
                    d.text((x + h.s(16), yy + j * h.s(27)), ln, font=fb, fill=(25, 25, 30))
            y += bh + h.s(14)
    c = _glow(c, (sx0, sy0, sx1, sy1), scr, h.s(22))
    buzz = h.s(5) * math.sin(lt * 70) if (mode in ("alert", "call") and lt < 0.8) else 0
    h.put(base, c, (h.W - c.width) / 2 + buzz, place(h, data, 0.5, c.height) + (1 - k) * h.s(300), a)


def comms(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any], lv: float = 0.0) -> None:
    a, k = _enter(lt, dur)
    if a <= 0:
        return
    W = h.s(620) if h.vertical else int(h.W * 0.5)
    Hh = int(W * 0.5)
    c = Image.new("RGBA", (W, Hh), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, W - 1, Hh - 1), h.s(16), fill=(10, 18, 34, 240), outline=h.accent + (255,), width=h.s(3))
    ch = str(data.get("channel") or "CANAL 2 · CONTROLE").upper()
    d.text((h.s(20), h.s(28)), ch, font=fit(ch, h.f_ui, W * 0.7, h.s(19)), fill=h.accent, anchor="lm")
    for i in range(5):
        bh = h.s(6 + i * 6)
        on = i < 2 + int(3 * (0.6 + 0.4 * math.sin(lt * 1.7)))
        d.rectangle((W - h.s(110) + i * h.s(16), h.s(40) - bh, W - h.s(100) + i * h.s(16), h.s(40)), fill=h.accent + ((255,) if on else (60,)))
    ox0, oy0, ox1, oy1 = h.s(20), h.s(56), W - h.s(20), Hh - h.s(44)
    d.rectangle((ox0, oy0, ox1, oy1), fill=(4, 30, 26, 255))
    for x in range(ox0, ox1, h.s(30)):
        d.line((x, oy0, x, oy1), fill=(20, 70, 60, 255))
    mid = (oy0 + oy1) / 2
    pts = [(ox0 + (ox1 - ox0) * i / 79, mid + (oy1 - oy0) * 0.42 * (0.08 + lv) * math.sin(i * 0.9 + lt * 30) * math.sin(i * 0.13 + lt * 3))
           for i in range(80)]
    d.line(pts, fill=(90, 255, 200), width=h.s(3))
    who = str(data.get("from") or "")
    if who:
        d.text((h.s(20), Hh - h.s(22)), who.upper(), font=h.F("ui", 16), fill=(180, 230, 255), anchor="lm")
    _scanlines(c, (0, 0, W, Hh), h.s(3), 28)
    h.put(base, shadowed(c, blur=10), (h.W - W) / 2, place(h, data, 0.52, Hh) + (1 - k) * h.s(200), a)


def monitor(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any], lv: float = 0.0) -> None:
    a, k = _enter(lt, dur)
    if a <= 0:
        return
    W = h.s(640) if h.vertical else int(h.W * 0.55)
    Hh = int(W * 0.66)
    c = Image.new("RGBA", (W, Hh + h.s(70)), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, W - 1, Hh - 1), h.s(18), fill=(30, 34, 40, 255))
    d.polygon([(W / 2 - h.s(40), Hh), (W / 2 + h.s(40), Hh), (W / 2 + h.s(70), Hh + h.s(60)), (W / 2 - h.s(70), Hh + h.s(60))], fill=(50, 54, 60, 255))
    sx0, sy0, sx1, sy1 = h.s(18), h.s(18), W - h.s(18), Hh - h.s(18)
    d.rectangle((sx0, sy0, sx1, sy1), fill=(240, 248, 245, 255))
    title = str(data.get("title") or "RESULTADO")
    d.text((sx0 + h.s(16), sy0 + h.s(24)), title, font=fit(title, h.f_ui, sx1 - sx0 - h.s(30), h.s(22)), fill=(31, 59, 77), anchor="lm")
    vals = [float(v) for v in (data.get("values") or [3, 4, 4, 6, 9, 14, 22]) if isinstance(v, (int, float))][:12] or [1, 2, 3]
    mx = max(vals) or 1
    gx0, gy0, gx1, gy1 = sx0 + h.s(20), sy0 + h.s(60), sx1 - h.s(20), sy1 - h.s(70)
    d.line((gx0, gy1, gx1, gy1), fill=(160, 170, 175), width=h.s(2))
    kk = ease((lt - 0.3) / max(0.6, dur * 0.6))
    pts = [(gx0 + (gx1 - gx0) * i / max(1, len(vals) - 1), gy1 - (gy1 - gy0) * v / mx) for i, v in enumerate(vals)]
    n = max(2, int(len(pts) * kk) + 1)
    d.line(pts[:n], fill=h.danger, width=h.s(4))
    for x, y in pts[:n]:
        d.ellipse((x - h.s(5), y - h.s(5), x + h.s(5), y + h.s(5)), fill=h.danger)
    for i, ln in enumerate([str(x) for x in (data.get("lines") or [])][:2]):
        d.text((sx0 + h.s(16), sy1 - h.s(52) + i * h.s(26)), ln, font=h.F("ui", 17), fill=(50, 60, 80))
    c = _glow(c, (sx0, sy0, sx1, sy1), (200, 255, 230), h.s(16))
    h.put(base, c, (h.W - c.width) / 2, place(h, data, 0.5, c.height) + (1 - k) * h.s(220), a)


def newsboy(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any], lv: float = 0.0) -> None:
    a, k = _enter(lt, dur)
    if a <= 0:
        return
    head = str(data.get("headline") or "").upper()
    W = h.s(560)
    fh = font(h.f_title, h.s(48))

    def card() -> Image.Image:
        lines = wrap(head, fh, W - h.s(60))[:3]
        Hh = h.s(150) + len(lines) * h.s(58)
        c = Image.new("RGBA", (W, Hh), h.paper + (255,))
        d = ImageDraw.Draw(c)
        d.rectangle((0, 0, W, h.s(96)), fill=h.ink + (255,))
        d.text((W / 2, h.s(50)), str(data.get("cry") or "EXTRA! EXTRA!"), font=h.F("title", 58), fill=h.paper, anchor="mm")
        for i, ln in enumerate(lines):
            d.text((W / 2, h.s(140) + i * h.s(58)), ln, font=fh, fill=h.danger if i == len(lines) - 1 else h.ink, anchor="mm")
        _paper_texture(c)
        return shadowed(c.rotate(-3, expand=True, resample=Image.BICUBIC), blur=10)
    c = h.cached(("newsboy", head), card)
    sh = h.s(6) * lv * math.sin(lt * 60)
    h.put(base, c, (h.W - c.width) / 2 + sh, place(h, data, 0.5, c.height) + (1 - k) * h.s(200), a)


def proclamation(h: Hud, base: Image.Image, lt: float, dur: float, data: dict[str, Any], lv: float = 0.0) -> None:
    a, k = _enter(lt, dur)
    if a <= 0:
        return
    W = h.s(540)
    title = str(data.get("title") or "EDITAL").upper()
    fp = font(h.f_paper, h.s(26))
    lines = wrap(str(data.get("text") or ""), fp, W - h.s(80))[:6]

    def card() -> Image.Image:
        Hh = h.s(200) + len(lines) * h.s(38)
        c = Image.new("RGBA", (W, Hh), (236, 226, 196, 255))
        d = ImageDraw.Draw(c)
        d.rectangle((h.s(12), h.s(12), W - h.s(12), Hh - h.s(12)), outline=h.ink + (255,), width=h.s(3))
        d.text((W / 2, h.s(66)), title, font=fit(title, h.f_title, W - h.s(60), h.s(54)), fill=h.ink, anchor="mm")
        d.line((h.s(60), h.s(104), W - h.s(60), h.s(104)), fill=h.ink, width=h.s(2))
        for i, ln in enumerate(lines):
            d.text((W / 2, h.s(140) + i * h.s(38)), ln, font=fp, fill=h.ink, anchor="mm")
        d.ellipse((W - h.s(110), Hh - h.s(100), W - h.s(30), Hh - h.s(20)), fill=(170, 40, 30, 255))
        _paper_texture(c)
        return c
    c = h.cached(("procl", title, tuple(lines)), card).copy()
    per = max(0.4, (dur - 0.6) / max(1, len(lines)))
    cur = int((lt - 0.3) / per)
    if 0 <= cur < len(lines):
        y = h.s(158) + cur * h.s(38)
        ImageDraw.Draw(c).line((h.s(50), y, W - h.s(50), y), fill=h.danger + (200,), width=h.s(3))
    c = shadowed(c.rotate(2, expand=True, resample=Image.BICUBIC), blur=10)
    h.put(base, c, (h.W - c.width) / 2, place(h, data, 0.5, c.height) + (1 - k) * h.s(160), a)


DEVICES = {"tv": tv_set, "radio": radio_set, "phone": phone_screen, "comms": comms, "monitor": monitor,
           "newsboy": newsboy, "proclamation": proclamation}
