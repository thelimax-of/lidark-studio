"""Cenários compostos: um cômodo ou fachada é gerado de parâmetros (classe, paleta, parede, piso, janela, luz, hora, clima)
e recebe mobília posicionada com lógica. Nada de fotografia fixa: a mesma receita com outra semente é outro lugar.
Mundo: x de 0 a 720, chão em y=800 (interior) ou 860 (exterior). compor(tipo, semente, ...) devolve as camadas do gerador.
"""
from __future__ import annotations

import colorsys
import random
from typing import Any

from .base import L, ln

_W = 2000


def _hls(h: float, l: float, s: float) -> str:
    return "#%02x%02x%02x" % tuple(int(max(0, min(1, x)) * 255) for x in colorsys.hls_to_rgb(h % 1, l, s))


def paleta(seed: int, classe: str = "media") -> dict[str, str]:
    r = random.Random(seed)
    h = r.random()
    sat = {"pobre": .16, "media": .2, "rica": .12}.get(classe, .2)
    luz = {"pobre": .66, "media": .74, "rica": .84}.get(classe, .74)
    a = (h + r.choice((.08, .5, .42, .58))) % 1
    return dict(parede=_hls(h, luz, sat), parede2=_hls(h, luz - .08, sat), rodape=_hls(h, luz - .34, sat * .8), acento=_hls(a, .46, .34), acento2=_hls(a, .34, .32), madeira=_hls(r.uniform(.05, .1), r.uniform(.3, .42), .36),
                madeira2=_hls(r.uniform(.05, .1), r.uniform(.22, .3), .36), piso=_hls(r.uniform(.06, .12), r.uniform(.45, .6), r.uniform(.12, .3)), piso2=_hls(r.uniform(.06, .12), r.uniform(.34, .44), r.uniform(.1, .26)), tecido=_hls(r.random(), .5, .3), id=f"{h:.2f}{classe}")


def _r(x, y, w, h, f, s=2.4, rx=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{f}" {ln(s)}/>'


def _e(x, y, rx, ry, f, s=2.4):
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{f}" {ln(s)}/>'


def _p(d, f="none", s=2.4):
    return f'<path d="{d}" fill="{f}" {ln(s)}/>'


def _t(x, y, t, tam, c, a="middle"):
    return f'''<text x="{x}" y="{y}" font-family="'Arial Black',Arial" font-size="{tam}" fill="{c}" text-anchor="{a}">{t}</text>'''


def _sombra(x, y, rx):
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{max(6, rx * .08):.0f}" fill="#140e18" opacity=".3" filter="url(#b6)"/>'


# ================================================================ paredes e pisos

def parede(tipo: str, pal: dict[str, str], h: int = 800, r: random.Random | None = None) -> str:
    s = f'<rect x="-640" y="-600" width="{_W}" height="{h + 600}" fill="{pal["parede"]}"/>'
    r = r or random.Random(1)
    if tipo == "azulejo":
        ini = r.choice((430, 520))
        s += "".join(f'<rect x="{-640 + c * 44}" y="{ini + l * 44}" width="44" height="44" fill="{pal["parede2"] if (l + c) % 2 else pal["parede"]}" stroke="{pal["rodape"]}" stroke-opacity=".3"/>' for l in range(int((h - ini) / 44) + 1) for c in range(46))
    elif tipo == "listras":
        s += "".join(f'<rect x="{-640 + i * 60}" y="-600" width="30" height="{h + 600}" fill="{pal["parede2"]}"/>' for i in range(34))
    elif tipo == "tijolo":
        s += "".join(f'<rect x="{-640 + c * 56 + (l % 2) * 28}" y="{-60 + l * 26}" width="56" height="26" fill="{pal["parede2"] if (c * 3 + l) % 4 else pal["parede"]}" stroke="{pal["rodape"]}" stroke-opacity=".5"/>' for l in range(int(h / 26) + 3) for c in range(36))
    elif tipo == "tabuas":
        s += "".join(f'<rect x="{-640 + i * 58}" y="-600" width="58" height="{h + 600}" fill="{pal["madeira"] if i % 3 else pal["madeira2"]}" {ln(2)}/>' for i in range(36))
    elif tipo == "descascada":
        for _ in range(16):
            x, y = r.randint(0, 720), r.randint(60, h - 60)
            s += f'<path d="M{x} {y}l{r.randint(20, 60)} {r.randint(-16, 12)}l{r.randint(-10, 20)} {r.randint(14, 40)}l{r.randint(-60, -20)} {r.randint(-8, 14)}z" fill="{pal["parede2"]}" stroke="{pal["rodape"]}" stroke-opacity=".4"/>'
    elif tipo == "painel":
        s += "".join(_r(-640 + i * 180 + 14, 200, 152, 200, pal["parede2"], 1.4) + _r(-640 + i * 180 + 14, 440, 152, 310, pal["parede2"], 1.4) for i in range(12))
    elif tipo == "meia":
        s += f'<rect x="-640" y="500" width="{_W}" height="{h - 500}" fill="{pal["acento"]}" opacity=".55"/><rect x="-640" y="494" width="{_W}" height="10" fill="{pal["rodape"]}"/>'
    s += f'<rect x="-640" y="{h - 14}" width="{_W}" height="16" fill="{pal["rodape"]}" {ln(2)}/>'
    return s


def piso(tipo: str, pal: dict[str, str], y0: int = 800, cx: int = 360) -> str:
    s = f'<rect x="-640" y="{y0}" width="{_W}" height="1100" fill="{pal["piso"]}"/>'
    if tipo == "tabua":
        s += "".join(f'<path d="M{cx + k * 44} {y0}L{cx + k * 130} 1600" stroke="{pal["piso2"]}" stroke-width="3"/>' for k in range(-20, 21))
    elif tipo in ("xadrez", "ceramica"):
        rows = [y0, y0 + 40, y0 + 90, y0 + 150, y0 + 226, y0 + 320, y0 + 440, y0 + 600, y0 + 820, y0 + 1100]
        for i in range(len(rows) - 1):
            a, b = rows[i], rows[i + 1]
            for c in range(-26, 27):
                X = lambda y, k: cx + k * 60 * (.72 + (y - y0) / 330)
                f = pal["piso2"] if (i + c) % 2 and tipo == "xadrez" else pal["piso"]
                s += f'<path d="M{X(a, c):.0f} {a}L{X(a, c + 1):.0f} {a}L{X(b, c + 1):.0f} {b}L{X(b, c):.0f} {b}z" fill="{f}" stroke="{pal["piso2"]}" stroke-width="1.5"/>'
    elif tipo == "carpete":
        s += f'<rect x="-640" y="{y0}" width="{_W}" height="1100" fill="{pal["acento2"]}" opacity=".7"/>'
    elif tipo == "cimento":
        s += "".join(f'<path d="M{x} {y}l{x % 70 + 30} 8" stroke="{pal["piso2"]}" stroke-width="3"/>' for x, y in ((90, y0 + 50), (420, y0 + 100), (260, y0 + 190), (580, y0 + 240), (130, y0 + 320), (500, y0 + 380)))
    return s


def janela(x: int, y: int, w: int, h: int, hora: str, pal: dict[str, str], cortina: bool = True, grade: bool = False) -> str:
    ceu = {"noite": "#1a2450", "tarde": "#f0a56a", "dia": "#a6d8f0", "chuva": "#6a7686"}.get(hora, "#a6d8f0")
    s = _r(x, y, w, h, ceu, 4)
    if hora == "noite":
        s += f'<circle cx="{x + w * .7:.0f}" cy="{y + 40}" r="13" fill="#f2eccb"/>'
    s += f'<path d="M{x} {y + h}v-{h * .3:.0f}h{w * .3:.0f}v-{h * .12:.0f}h{w * .3:.0f}v{h * .06:.0f}h{w * .4:.0f}v{h * .36:.0f}z" fill="#000" opacity=".2"/>'
    s += _p(f"M{x + w / 2} {y}V{y + h}M{x} {y + h / 2}H{x + w}", s=3.4) + _r(x - 10, y + h, w + 20, 12, pal["parede2"], 2.6)
    if grade:
        s += "".join(f'<path d="M{a} {y}V{y + h}" {ln(5)}/>' for a in range(x + 18, x + w, 26))
    if cortina:
        c = pal["tecido"]
        s += f'<g data-vida="rot:.5:.8:0:{x}:{y}">{_p(f"M{x - 12} {y - 8}C{x + 22} {y + 60} {x + 8} {y + h - 50} {x + 14} {y + h - 6}H{x - 18}V{y - 8}z", c)}</g>'
        s += f'<g data-vida="rot:.5:.9:1:{x + w}:{y}">{_p(f"M{x + w + 12} {y - 8}C{x + w - 22} {y + 60} {x + w - 8} {y + h - 50} {x + w - 14} {y + h - 6}H{x + w + 18}V{y - 8}z", c)}</g>'
        s += f'<path d="M{x - 18} {y - 10}H{x + w + 18}" stroke="{pal["madeira2"]}" stroke-width="7" stroke-linecap="round"/>'
    return s


# ================================================================ mobília: cada função desenha com base em (x, y) no chão

def m_cama(x, y, p): return _sombra(x, y, 180) + _r(x - 170, y - 74, 340, 74, p["madeira2"]) + _r(x - 180, y - 120, 22, 120, p["madeira"]) + _p(f"M{x - 160} {y - 112}H{x + 170}V{y - 60}H{x - 160}z", p["tecido"]) + _r(x - 156, y - 136, 96, 30, "#f1ece0", 2.4, 12)
def m_sofa(x, y, p): return _sombra(x, y, 160) + _r(x - 150, y - 170, 300, 100, p["acento"], 2.6, 22) + _r(x - 164, y - 110, 328, 90, p["acento2"], 2.6, 20) + _r(x - 180, y - 136, 44, 116, p["acento"], 2.6, 16) + _r(x + 136, y - 136, 44, 116, p["acento"], 2.6, 16) + _r(x - 150, y - 22, 16, 22, p["madeira2"]) + _r(x + 134, y - 22, 16, 22, p["madeira2"])
def m_mesa(x, y, p): return _sombra(x, y, 130) + _r(x - 130, y - 124, 260, 16, p["madeira"]) + _r(x - 120, y - 108, 16, 108, p["madeira2"]) + _r(x + 104, y - 108, 16, 108, p["madeira2"])
def m_estante(x, y, p):
    s = _sombra(x, y, 90) + _r(x - 84, y - 420, 168, 420, p["madeira"])
    r = random.Random(x + y)
    for k in range(4):
        yy = y - 90 - k * 92
        s += _r(x - 78, yy, 156, 8, p["madeira2"], 1.8)
        a = x - 72
        while a < x + 56:
            w = r.randint(12, 24)
            h = r.randint(44, 72)
            s += _r(a, yy - h, w, h, _hls(r.random(), .5, .5), 1.8)
            a += w + 2
    return s
def m_fogao(x, y, p): return _sombra(x, y, 90) + _r(x - 80, y - 190, 160, 190, "#ecebe4") + _r(x - 86, y - 202, 172, 12, "#3b3a40") + _r(x - 62, y - 130, 124, 94, "#3a3a40") + "".join(f'<circle cx="{x - 52 + i * 26}" cy="{y - 164}" r="8" fill="#d9d6cc" {ln(1.8)}/>' for i in range(5))
def m_geladeira(x, y, p): return _sombra(x, y, 90) + _r(x - 78, y - 400, 156, 400, _hls(.55, .9, .1), 3, 12) + _p(f"M{x - 78} {y - 262}H{x + 78}", s=3) + _r(x - 62, y - 330, 9, 56, "#8e9599", 2) + _r(x - 62, y - 240, 9, 90, "#8e9599", 2)
def m_pia(x, y, p): return _sombra(x, y, 120) + _r(x - 120, y - 170, 240, 170, p["acento2"]) + _r(x - 130, y - 182, 260, 14, "#d8d2c2") + _p(f"M{x - 10} {y - 182}v-34c0-16 26-16 26 0v8", s=5) + _p(f"M{x} {y - 170}V{y}M{x - 60} {y - 170}V{y}M{x + 60} {y - 170}V{y}", s=2)
def m_armario(x, y, p): return _sombra(x, y, 120) + _r(x - 110, y - 470, 220, 470, p["madeira"]) + _p(f"M{x} {y - 470}V{y}", s=3) + f'<circle cx="{x - 12}" cy="{y - 240}" r="5" fill="#d8b24a"/><circle cx="{x + 12}" cy="{y - 240}" r="5" fill="#d8b24a"/>'
def m_tv(x, y, p): return _sombra(x, y, 90) + _r(x - 90, y - 60, 180, 60, p["madeira2"]) + _r(x - 100, y - 190, 200, 124, "#20222a", 3, 6) + f'<rect x="{x - 90}" y="{y - 180}" width="180" height="104" fill="#6fb4dc" data-vida="brilho:.6:1:5"/>'
def m_quadro(x, y, p):
    r = random.Random(x * 7 + y)
    return _r(x - 44, y - 34, 88, 68, p["madeira2"], 3) + _r(x - 36, y - 26, 72, 52, _hls(r.random(), .7, .4), 1.8) + _p(f"M{x - 36} {y + 18}l24-22 16 12 16-20 20 30", _hls(r.random(), .4, .4), 1.8)
def m_planta(x, y, p): return _sombra(x, y, 50) + _p(f"M{x - 28} {y - 70}H{x + 28}L{x + 20} {y}H{x - 20}z", p["acento2"]) + _p(f"M{x} {y - 70}C{x - 60} {y - 110} {x - 70} {y - 170} {x - 26} {y - 190}C{x - 14} {y - 150} {x - 6} {y - 110} {x} {y - 70}zM{x} {y - 70}C{x + 40} {y - 120} {x + 70} {y - 150} {x + 40} {y - 210}C{x + 10} {y - 180} {x - 6} {y - 120} {x} {y - 70}z", "#3f8a55")
def m_cadeira(x, y, p): return _sombra(x, y, 50) + _r(x - 40, y - 190, 12, 190, p["madeira2"]) + _r(x + 30, y - 100, 12, 100, p["madeira2"]) + _r(x - 46, y - 112, 92, 14, p["madeira"])
def m_barbeiro(x, y, p): return _sombra(x, y, 70) + _p(f"M{x - 12} {y - 80}H{x + 12}V{y - 8}H{x - 12}z", "#8e9599") + _e(x, y - 6, 56, 10, "#5c5f66") + _r(x - 54, y - 240, 100, 150, "#7a2f22", 2.6, 14) + _r(x - 66, y - 106, 136, 30, "#7a2f22", 2.6, 10) + _r(x - 78, y - 160, 18, 60, "#c8c8c0") + _r(x + 56, y - 160, 18, 60, "#c8c8c0")
def m_espelho(x, y, p): return _r(x - 70, y - 90, 140, 180, "#c9e4ee", 4, 8) + _p(f"M{x - 50} {y + 40}L{x + 10} {y - 74}", s=0) + f'<path d="M{x - 50} {y + 60}L{x + 20} {y - 70}" stroke="#fff" stroke-width="14" opacity=".5"/>' + _r(x - 90, y + 96, 180, 12, p["madeira"])
def m_secador(x, y, p): return _sombra(x, y, 60) + _r(x - 6, y - 170, 12, 170, "#8e9599") + _e(x + 10, y - 200, 62, 46, p["acento"]) + _r(x - 56, y - 122, 120, 40, p["acento2"], 2.4, 10)
def m_barra(x, y, p): return _sombra(x, y, 90) + _r(x - 90, y - 90, 12, 90, "#3a3a40") + _r(x + 78, y - 90, 12, 90, "#3a3a40") + f'<path d="M{x - 130} {y - 94}H{x + 130}" {ln(8)}/>' + _r(x - 118, y - 130, 16, 76, "#20222a", 2, 4) + _r(x + 102, y - 130, 16, 76, "#20222a", 2, 4)
def m_esteira(x, y, p): return _sombra(x, y, 120) + _p(f"M{x - 120} {y}L{x + 100} {y - 26}L{x + 120} {y}z", "#2a2a30") + _r(x + 92, y - 210, 14, 190, "#6a7080") + _r(x + 60, y - 226, 76, 30, "#2a2a30", 2.4, 6)
def m_maca(x, y, p): return _sombra(x, y, 150) + _r(x - 150, y - 112, 300, 30, "#dfe9ec", 2.6, 8) + _r(x - 130, y - 82, 12, 82, "#8e9599") + _r(x + 118, y - 82, 12, 82, "#8e9599") + _r(x - 150, y - 138, 80, 26, "#fbfbf6", 2.4, 8)
def m_soro(x, y, p): return _sombra(x, y, 40) + _r(x - 4, y - 300, 8, 300, "#8e9599") + _r(x - 24, y - 300, 48, 10, "#8e9599") + _r(x - 22, y - 290, 30, 50, "#cfe9f2", 2, 8)
def m_biombo(x, y, p): return _sombra(x, y, 110) + "".join(_r(x - 110 + i * 74, y - 300, 72, 290, p["parede2"], 2.4) for i in range(3))
def m_banco_igreja(x, y, p): return _sombra(x, y, 150) + _r(x - 150, y - 160, 300, 70, p["madeira"]) + _r(x - 160, y - 90, 320, 18, p["madeira2"]) + _r(x - 150, y - 72, 18, 72, p["madeira2"]) + _r(x + 132, y - 72, 18, 72, p["madeira2"])
def m_altar(x, y, p): return _sombra(x, y, 140) + _r(x - 130, y - 150, 260, 150, "#f4efe2") + _r(x - 150, y - 164, 300, 16, p["acento"]) + _p(f"M{x - 8} {y - 330}h16v50h34v16h-34v100h-16v-100h-34v-16h34z", "#d8b24a")
def m_vitral(x, y, p):
    r = random.Random(x)
    s = f'<path d="M{x - 66} {y + 120}V{y - 40}A66 66 0 0 1 {x + 66} {y - 40}V{y + 120}z" fill="#e8dcb8" {ln(4)}/>'
    for i in range(8):
        s += f'<path d="M{x} {y - 40}L{x - 66 + i * 19} {y + 120}L{x - 47 + i * 19} {y + 120}z" fill="{_hls(r.random(), .55, .6)}" {ln(1.8)}/>'
    return s
def m_mesa_bar(x, y, p): return _sombra(x, y, 80) + _e(x, y - 110, 76, 16, "#d94a3a") + _r(x - 6, y - 104, 12, 104, "#8e9599") + _e(x, y, 44, 8, "#8e9599") + _r(x - 14, y - 150, 28, 40, "#b8e0a0", 2, 4)
def m_balcao(x, y, p): return _sombra(x, y, 240) + _r(x - 230, y - 180, 460, 180, p["acento2"]) + _r(x - 244, y - 196, 488, 18, p["madeira"]) + "".join(_p(f"M{x - 150 + i * 100} {y - 178}V{y}", s=2) for i in range(4))
def m_prateleira(x, y, p):
    r = random.Random(x * 3 + y)
    s = _r(x - 140, y - 430, 280, 430, p["madeira2"])
    for k in range(4):
        yy = y - 86 - k * 96
        s += _r(x - 134, yy, 268, 8, p["madeira"], 1.8)
        for i in range(7):
            c = _hls(r.random(), .55, .55)
            h = r.randint(36, 64)
            s += _r(x - 124 + i * 37, yy - h, 28, h, c, 1.8, 3)
    return s
def m_caixa(x, y, p): return _sombra(x, y, 120) + _r(x - 120, y - 130, 240, 130, "#3a3f4c") + _r(x - 130, y - 142, 260, 14, "#8e9599") + _r(x + 30, y - 210, 74, 66, "#20222a", 2.4, 4) + _r(x + 38, y - 202, 58, 42, "#9fd08a", 1.8)
def m_garrafas(x, y, p):
    r = random.Random(x)
    s = _r(x - 150, y - 8, 300, 10, p["madeira"], 2)
    for i in range(9):
        c = _hls(r.random(), .4, .5)
        s += _p(f"M{x - 136 + i * 34} {y - 8}v-62c0-14 8-16 8-30h10c0 14 8 16 8 30v62z", c, 2)
    return s
def m_tela(x, y, p): return _r(x - 300, y - 240, 600, 300, "#e8f0f8", 4) + f'<rect x="{x - 300}" y="{y - 240}" width="600" height="300" fill="#7fa8d8" data-vida="brilho:.3:.9:2.4"/>'
def m_poltronas(x, y, p): return "".join(_r(x + i * 116 - 56, y - 110, 100, 110, "#7a2f3a", 2.6, 16) + _r(x + i * 116 - 66, y - 50, 120, 44, "#5a1f2a", 2.6, 10) for i in range(-3, 4))
def m_pc(x, y, p): return _r(x - 110, y - 100, 220, 12, p["madeira"]) + _r(x - 100, y - 88, 12, 88, p["madeira2"]) + _r(x + 88, y - 88, 12, 88, p["madeira2"]) + _r(x - 66, y - 214, 132, 98, "#20222a", 2.6, 4) + f'<rect x="{x - 58}" y="{y - 206}" width="116" height="80" fill="#3fd17a" data-vida="brilho:.6:1:6"/>' + _r(x - 8, y - 116, 16, 16, "#3a3a40") + _r(x - 56, y - 110, 112, 8, "#d9d6cc", 1.8)
def m_mesa_escritorio(x, y, p): return _sombra(x, y, 140) + _r(x - 140, y - 124, 280, 14, "#d9d6cc") + _r(x - 130, y - 110, 100, 110, "#8e9599") + _r(x + 116, y - 110, 12, 110, "#8e9599") + _r(x - 40, y - 218, 110, 84, "#20222a", 2.6, 4) + f'<rect x="{x - 32}" y="{y - 210}" width="94" height="66" fill="#6fb4dc"/>'
def m_lousa(x, y, p): return _r(x - 180, y - 80, 360, 200, "#2f6a4a", 4) + _r(x - 180, y + 120, 360, 10, p["madeira"]) + _p(f"M{x - 140} {y - 40}h200M{x - 140} {y}h150M{x - 140} {y + 40}h230", s=3).replace(L, "#e8e4d6")
def m_carteira(x, y, p): return _sombra(x, y, 60) + _r(x - 54, y - 96, 108, 12, p["madeira"]) + _r(x - 44, y - 84, 8, 84, "#6a7080") + _r(x + 36, y - 84, 8, 84, "#6a7080")
def m_baloes(x, y, p):
    r = random.Random(x + 3)
    return "".join(f'<path d="M{x + i * 54} {y + 90}v130" {ln(1.6)}/>' + _e(x + i * 54, y + 60 - i * 8, 34, 42, _hls(r.random(), .58, .7)) for i in range(-2, 3))
def m_bolo(x, y, p): return _sombra(x, y, 80) + _r(x - 90, y - 110, 180, 110, "#fbf6e6") + _r(x - 60, y - 190, 120, 40, "#f0b8c8") + _r(x - 80, y - 152, 160, 42, "#f7d8e0") + _p(f"M{x} {y - 190}v-20", s=4)
def m_guirlanda(x, y, p): return f'<path d="M{x - 300} {y}Q{x} {y + 90} {x + 300} {y}" fill="none" stroke="{p["acento"]}" stroke-width="8"/>' + "".join(_p(f"M{x - 280 + i * 62} {y + 34 - abs(i - 4.5) * 8}l14 34 14-34z", _hls(i * .13, .6, .7), 2) for i in range(10))
def m_arco(x, y, p): return f'<path d="M{x - 140} {y}V{y - 320}A140 140 0 0 1 {x + 140} {y - 320}V{y}" fill="none" stroke="#3f8a55" stroke-width="26"/>' + "".join(f'<circle cx="{x - 140 + i * 40}" cy="{y - 330 - (140 - abs(i - 7) * 20) * .9:.0f}" r="11" fill="#f0b8c8" {ln(1.8)}/>' for i in range(15))
def m_grade(x, y, p): return _r(x - 150, y - 420, 300, 420, "#2a2a30") + "".join(f'<path d="M{x - 130 + i * 40} {y - 420}V{y}" stroke="#8e9599" stroke-width="10"/>' for i in range(7))
def m_mesa_del(x, y, p): return m_mesa_escritorio(x, y, p) + _r(x + 76, y - 150, 52, 26, "#fbf6e6", 2)
def m_macaco(x, y, p): return _sombra(x, y, 150) + _r(x - 130, y - 330, 20, 330, "#c8513a") + _r(x + 110, y - 330, 20, 330, "#c8513a") + _r(x - 140, y - 340, 280, 22, "#c8513a") + "".join(_r(x - 96 + i * 40, y - 318, 16, 90, "#8e9599", 2) for i in range(5))
def m_ferramentas(x, y, p): return _r(x - 150, y - 90, 300, 180, p["madeira"], 3) + _p(f"M{x - 110} {y - 60}v90M{x - 60} {y - 60}v110M{x} {y - 60}v80M{x + 50} {y - 60}v100M{x + 100} {y - 60}v70", s=6)
def m_pneu(x, y, p): return _e(x, y - 40, 56, 40, "#20222a", 3) + _e(x, y - 40, 24, 16, "#6a7080", 2)
def m_janela_onibus(x, y, p): return "".join(_r(x + i * 200 - 90, y, 180, 170, "#a6d8f0", 4, 12) for i in range(-3, 4))
def m_banco_onibus(x, y, p): return _sombra(x, y, 60) + _r(x - 46, y - 220, 92, 120, p["acento"], 2.6, 14) + _r(x - 56, y - 110, 112, 26, p["acento2"], 2.6, 8) + _r(x - 8, y - 86, 16, 86, "#8e9599")
def m_barras(x, y, p): return "".join(f'<path d="M{x + i * 220} -600V{y}" stroke="{L}" stroke-width="12"/><path d="M{x + i * 220} -600V{y}" stroke="#d8d8d0" stroke-width="7"/>' for i in range(-2, 3))
def m_ponto(x, y, p): return _r(x - 180, y - 330, 12, 330, "#6a7080") + _r(x + 168, y - 330, 12, 330, "#6a7080") + _p(f"M{x - 210} {y - 330}H{x + 210}L{x + 190} {y - 370}H{x - 190}z", p["acento"]) + _r(x - 150, y - 110, 300, 16, p["madeira"]) + _r(x + 196, y - 400, 10, 400, "#6a7080") + _e(x + 201, y - 410, 36, 36, "#2f6fa8") + _t(x + 201, y - 400, "BUS", 18, "#fff")
def m_guarda_sol(x, y, p): return _sombra(x, y, 110) + f'<path d="M{x} {y}V{y - 330}" {ln(6)}/>' + _p(f"M{x - 170} {y - 320}Q{x} {y - 460} {x + 170} {y - 320}z", p["acento"]) + _p(f"M{x - 60} {y - 320}Q{x} {y - 460} {x + 60} {y - 320}z", "#fbf6e6")
def m_cerca(x, y, p): return "".join(_r(x + i * 44 - 8, y - 120, 16, 120, p["madeira"], 2) for i in range(-10, 11)) + _r(x - 460, y - 96, 920, 12, p["madeira2"], 2) + _r(x - 460, y - 50, 920, 12, p["madeira2"], 2)
def m_arvore(x, y, p): return _sombra(x, y, 110) + _p(f"M{x - 18} {y}C{x - 12} {y - 80} {x - 16} {y - 150} {x - 26} {y - 220}H{x + 26}C{x + 16} {y - 150} {x + 14} {y - 80} {x + 22} {y}z", p["madeira2"]) + f'<g data-vida="rot:.8:1.1:0:{x}:{y - 220}">{_p(f"M{x - 140} {y - 280}C{x - 170} {y - 370} {x - 110} {y - 450} {x - 50} {y - 430}C{x - 30} {y - 510} {x + 80} {y - 500} {x + 90} {y - 430}C{x + 160} {y - 440} {x + 180} {y - 340} {x + 140} {y - 280}C{x + 160} {y - 220} {x + 80} {y - 190} {x + 40} {y - 214}C{x} {y - 180} {x - 80} {y - 190} {x - 90} {y - 224}C{x - 120} {y - 216} {x - 140} {y - 250} {x - 140} {y - 280}z", _hls(.32, .36, .42))}</g>'
def m_varal(x, y, p):
    r = random.Random(x)
    s = _r(x - 300, y - 340, 10, 340, p["madeira"]) + _r(x + 290, y - 340, 10, 340, p["madeira"]) + _p(f"M{x - 295} {y - 330}Q{x} {y - 300} {x + 295} {y - 330}")
    for i in range(5):
        c = _hls(r.random(), .55, .55)
        s += _p(f"M{x - 220 + i * 100} {y - 318}h60l10 30-14 4v70h-52v-70l-14-4z", c, 2)
    return s
def m_muro(x, y, p): return _r(x - 640, y - 200, 1600, 200, p["parede2"], 2.6) + "".join(_p(f"M{x - 640 + i * 120} {y - 200}V{y}", s=1.4) for i in range(14))
def m_barraca(x, y, p): return _sombra(x, y, 180) + _r(x - 170, y - 110, 340, 110, p["madeira"]) + _r(x - 180, y - 320, 12, 320, p["madeira2"]) + _r(x + 168, y - 320, 12, 320, p["madeira2"]) + "".join(_p(f"M{x - 196 + i * 56} {y - 320}h56l-6 60h-44z", p["acento"] if i % 2 else "#fbf6e6") for i in range(7)) + "".join(f'<circle cx="{x - 120 + i * 40}" cy="{y - 124}" r="18" fill="{_hls(.08 + i * .07, .55, .7)}" {ln(2)}/>' for i in range(7))
def m_porta(x, y, p): return _r(x - 66, y - 300, 132, 300, p["madeira"], 3) + _r(x - 50, y - 280, 100, 120, p["madeira2"], 2) + _r(x - 50, y - 140, 100, 124, p["madeira2"], 2) + f'<circle cx="{x + 46}" cy="{y - 150}" r="6" fill="#d8b24a" {ln(1.8)}/>'
def m_cortina_palco(x, y, p): return _p(f"M{x - 360} -600H{x - 200}C{x - 240} {y - 300} {x - 240} {y - 200} {x - 260} {y}H{x - 360}zM{x + 360} -600H{x + 200}C{x + 240} {y - 300} {x + 240} {y - 200} {x + 260} {y}H{x + 360}z", "#7a1f2a")
def m_manequim(x, y, p): return _sombra(x, y, 50) + _r(x - 5, y - 100, 10, 100, p["madeira2"]) + _e(x, y - 4, 34, 7, p["madeira2"]) + _p(f"M{x - 40} {y - 290}C{x - 30} {y - 250} {x - 26} {y - 200} {x - 34} {y - 120}H{x + 34}C{x + 26} {y - 200} {x + 30} {y - 250} {x + 40} {y - 290}C{x + 10} {y - 300} {x - 10} {y - 300} {x - 40} {y - 290}z", "#d9c8a4")
def m_tecidos(x, y, p):
    r = random.Random(x * 5)
    return _r(x - 130, y - 330, 260, 330, p["madeira2"]) + "".join(_r(x - 120 + i * 40, y - 318 + (i % 2) * 8, 36, 300, _hls(r.random(), .55, .55), 1.8, 8) for i in range(6))
def m_placa(x, y, p, txt="ABERTO"): return _r(x - 6, y - 140, 12, 140, p["madeira2"]) + _r(x - 90, y - 220, 180, 84, p["acento"], 3, 4) + _t(x, y - 166, txt, 26, "#fff")
def m_lampada(x, y, p): return f'<path d="M{x} -600V{y}" {ln(3)}/>' + _p(f"M{x - 50} {y + 56}C{x - 44} {y + 18} {x - 22} {y} {x} {y}C{x + 22} {y} {x + 44} {y + 18} {x + 50} {y + 56}z", p["acento"]) + _e(x, y + 56, 50, 9, "#ffefb8")
def m_fluorescente(x, y, p): return _r(x - 110, y, 220, 16, "#fbfbf6", 2.4, 6)
def m_lustre(x, y, p): return f'<path d="M{x} -600V{y}" {ln(3)}/>' + _p(f"M{x - 80} {y + 40}Q{x} {y - 20} {x + 80} {y + 40}z", "#d8b24a") + "".join(f'<circle cx="{x - 70 + i * 28}" cy="{y + 54}" r="7" fill="#fff4c8" {ln(1.6)}/>' for i in range(6))
def m_ventilador(x, y, p): return _r(x - 5, y - 120, 10, 120, "#6a7080") + f'<g transform="translate({x} {y - 140})"><g data-vida="gira:360:0">{_p("M0 0C-14-36 14-36 0 0M0 0C36-14 36 14 0 0M0 0C14 36-14 36 0 0M0 0C-36 14-36-14 0 0", "#bfc6c6")}</g></g>'
def m_infiltracao(x, y, p): return _p(f"M{x - 80} {y}c40 50 120 30 160 70c-40 40-140 20-170-10z", p["parede2"], 0)
def m_fios(x, y, p): return f'<path d="M-640 {y}C0 {y + 60} 300 {y + 30} 1360 {y}" fill="none" {ln(2.2)}/>'
def m_tanque(x, y, p): return _sombra(x, y, 80) + _r(x - 80, y - 130, 160, 130, "#b6b2a6") + _p(f"M{x - 70} {y - 130}v-14h140v14", "#d4d0c4")
def m_carro(x, y, p): return _sombra(x, y, 170) + _p(f"M{x - 168} {y - 34}C{x - 170} {y - 60} {x - 150} {y - 74} {x - 118} {y - 78}L{x - 74} {y - 128}C{x - 60} {y - 140} {x + 60} {y - 140} {x + 96} {y - 122}L{x + 132} {y - 82}C{x + 160} {y - 78} {x + 174} {y - 66} {x + 172} {y - 36}C{x + 172} {y - 20} {x + 160} {y - 14} {x + 148} {y - 14}H{x - 152}C{x - 162} {y - 14} {x - 168} {y - 22} {x - 168} {y - 34}z", p["acento"]) + _p(f"M{x - 62} {y - 122}H{x - 8}V{y - 82}H{x - 98}zM{x + 4} {y - 122}H{x + 50}L{x + 104} {y - 82}H{x + 4}z", "#c7dde6") + f'<circle cx="{x - 108}" cy="{y - 14}" r="28" fill="#1d1d22" {ln(2.6)}/><circle cx="{x + 108}" cy="{y - 14}" r="28" fill="#1d1d22" {ln(2.6)}/>'
def m_casa(x, y, p, w=300):
    r = random.Random(x * 11 + y)
    c = _hls(r.random(), .62, .4)
    return _r(x - w / 2, y - 300, w, 300, c, 3) + _p(f"M{x - w / 2 - 12} {y - 300}L{x} {y - 400}L{x + w / 2 + 12} {y - 300}z", _hls(r.uniform(0, .1), .4, .45)) + _r(x + 30, y - 200, 76, 200, p["madeira"], 2.6) + _r(x - 110, y - 230, 92, 92, "#9fc0cc", 2.6)
def m_predio(x, y, p, w=200, h=620):
    r = random.Random(x * 13)
    c = _hls(r.random(), .6, .2)
    return _r(x - w / 2, y - h, w, h, c, 3) + "".join(_r(x - w / 2 + 18 + i * 58, y - h + 20 + j * 72, 40, 50, "#f7cf6a" if r.random() < .4 else "#3a3f4c", 1.8) for i in range(3) for j in range(int(h / 72) - 1))
def m_morro(x, y, p): return _p(f"M{x - 700} {y}C{x - 400} {y - 320} {x - 200} {y - 200} {x} {y - 280}C{x + 240} {y - 380} {x + 500} {y - 160} {x + 800} {y}z", _hls(.3, .42, .3), 2.4)


M = {k[2:]: v for k, v in list(globals().items()) if k.startswith("m_")}


# ================================================================ exteriores

def ceu(hora: str, clima: str, seed: int) -> str:
    g = {"dia": ("#6fb4dc", "#d6eef2"), "tarde": ("#e88a5a", "#f8cf8a"), "noite": ("#101636", "#3a3f73"), "chuva": ("#4a5468", "#8d98a6")}["chuva" if clima == "chuva" else hora]
    i = f"c{hora}{clima}"
    s = f'<linearGradient id="{i}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{g[0]}"/><stop offset="1" stop-color="{g[1]}"/></linearGradient><rect x="-640" y="-600" width="{_W}" height="1600" fill="url(#{i})"/>'
    if hora == "dia" and clima != "chuva":
        s += '<circle cx="130" cy="230" r="46" fill="#fff0b8"/>'
    if hora == "noite":
        s += '<circle cx="560" cy="210" r="30" fill="#f2eccb"/>'
    r = random.Random(seed)
    nuv = "".join(f'<path transform="translate({r.randint(-300, 1000)} {r.randint(140, 340)}) scale({r.uniform(.6, 1.3):.2f})" d="M-70 20C-92 20-96-6-72-10C-74-34-40-42-26-24C-14-52 34-46 36-16C62-20 76 18 48 20z" fill="{"#3e4556" if clima == "chuva" else "#fff"}" opacity=".85"/>' for _ in range(4))
    return s + f'<g data-vida="anda:4:0:400">{nuv}</g>'


def chao_ext(tipo: str, pal: dict[str, str], y: int = 860) -> str:
    if tipo == "areia":
        return f'<rect x="-640" y="{y}" width="{_W}" height="1000" fill="#e8d4a0"/>' + "".join(f'<ellipse cx="{a}" cy="{b}" rx="60" ry="8" fill="#d6be88"/>' for a, b in ((100, y + 80), (480, y + 150), (250, y + 260), (620, y + 300)))
    if tipo == "grama":
        return f'<rect x="-640" y="{y}" width="{_W}" height="1000" fill="#6a9a50"/>' + "".join(f'<path d="M{a} {b}l6-16 6 16" fill="none" stroke="#4f7f3c" stroke-width="3"/>' for a in range(-200, 900, 66) for b in (y + 60, y + 170, y + 300))
    if tipo == "terra":
        return f'<rect x="-640" y="{y}" width="{_W}" height="1000" fill="#a98a5e"/>' + "".join(f'<ellipse cx="{a}" cy="{b}" rx="50" ry="10" fill="#8f7248"/>' for a, b in ((80, y + 90), (420, y + 150), (600, y + 240), (220, y + 320)))
    return (f'<rect x="-640" y="{y}" width="{_W}" height="170" fill="#b9b3a4"/>' + "".join(f'<path d="M{k * 100} {y}L{k * 118 - 40} {y + 170}" stroke="#9f9a8c" stroke-width="2.4"/>' for k in range(-8, 18)) +
            f'<rect x="-640" y="{y + 170}" width="{_W}" height="16" fill="#d8d3c4" {ln(2.4)}/><rect x="-640" y="{y + 186}" width="{_W}" height="900" fill="#4c4d56"/>' + "".join(f'<rect x="{k * 220}" y="{y + 340}" width="120" height="10" fill="#e8e4d6" opacity=".75"/>' for k in range(-4, 8)))


def _mar(y):
    return f'<rect x="-640" y="{y - 150}" width="{_W}" height="160" fill="#3f9fc0"/><g data-vida="x:14:1:0"><path d="M-640 {y - 60}q60-12 120 0t120 0t120 0t120 0t120 0t120 0t120 0t120 0t120 0t120 0t120 0t120 0" fill="none" stroke="#dff2f8" stroke-width="5"/></g>'


# ================================================================ receitas: tipo -> composição.
# fundo/parede = (móvel, x, y do chão ou da parede); frente = à frente dos atores; ext = fachada/exterior

R: dict[str, dict[str, Any]] = {
    "casa_pobre": dict(classe="pobre", parede=("descascada", "azulejo"), piso=("cimento", "ceramica"), teto=("lampada",), opcoes=[["cama", "mesa", "fogao"], ["fogao", "geladeira", "mesa"], ["cama", "tv", "planta"]], parede_itens=["quadro", "infiltracao"]),
    "casa_media": dict(classe="media", parede=("meia", "listras", "liso"), piso=("ceramica", "tabua"), teto=("lampada", "fluorescente"), opcoes=[["sofa", "tv", "planta"], ["sofa", "estante", "planta"], ["estante", "mesa", "planta"]], parede_itens=["quadro", "quadro"]),
    "casa_rica": dict(classe="rica", parede=("painel", "liso"), piso=("tabua", "carpete"), teto=("lustre",), opcoes=[["sofa", "estante", "planta"], ["estante", "sofa", "planta"]], parede_itens=["quadro", "espelho"], janela="grande"),
    "barraco": dict(classe="pobre", parede=("tabuas",), piso=("cimento",), teto=("lampada",), opcoes=[["cama", "tanque"], ["mesa", "fogao"]], parede_itens=[]),
    "apartamento": dict(classe="media", parede=("liso", "listras"), piso=("tabua", "ceramica"), teto=("fluorescente",), opcoes=[["sofa", "tv"], ["cama", "armario"], ["mesa", "geladeira", "pia"]], parede_itens=["quadro"]),
    "cozinha": dict(classe="media", parede=("azulejo",), piso=("xadrez", "ceramica"), teto=("lampada",), opcoes=[["fogao", "pia", "geladeira"], ["pia", "fogao", "geladeira"], ["geladeira", "fogao", "pia"]], parede_itens=[]),
    "quarto": dict(classe="media", parede=("listras", "liso", "meia"), piso=("tabua", "carpete"), teto=("lampada",), opcoes=[["cama", "armario"], ["armario", "cama"], ["cama", "estante"]], parede_itens=["quadro"]),
    "quintal": dict(ext=True, chao="terra", fundo=[("muro", 360), ("varal", 360), ("tanque", 620), ("planta", 90)]),
    "igreja": dict(classe="media", parede=("liso", "painel"), piso=("ceramica",), teto=("lustre",), opcoes=[["altar"]], parede_itens=["vitral", "vitral"], frente=[("banco_igreja", 180), ("banco_igreja", 560)], sem_janela=True),
    "salao": dict(classe="media", parede=("listras", "liso"), piso=("xadrez",), teto=("fluorescente",), opcoes=[["secador", "barbeiro", "secador"]], parede_itens=["espelho", "espelho"]),
    "barbearia": dict(classe="pobre", parede=("azulejo", "meia"), piso=("xadrez",), teto=("fluorescente",), opcoes=[["barbeiro", "barbeiro"]], parede_itens=["espelho", "espelho"]),
    "atelie": dict(classe="media", parede=("liso", "listras"), piso=("tabua",), teto=("lampada",), opcoes=[["tecidos", "manequim", "mesa"], ["manequim", "tecidos", "armario"]], parede_itens=["quadro"]),
    "academia": dict(classe="media", parede=("liso", "meia"), piso=("cimento", "carpete"), teto=("fluorescente",), opcoes=[["esteira", "barra", "esteira"], ["barra", "esteira"]], parede_itens=["espelho"]),
    "hospital": dict(classe="media", parede=("meia", "liso"), piso=("ceramica",), teto=("fluorescente",), opcoes=[["maca", "soro", "biombo"], ["biombo", "maca", "soro"]], parede_itens=[]),
    "consultorio": dict(classe="media", parede=("liso",), piso=("ceramica",), teto=("fluorescente",), opcoes=[["mesa_escritorio", "maca"], ["maca", "mesa_escritorio"]], parede_itens=["quadro"]),
    "onibus": dict(classe="media", parede=("liso",), piso=("cimento",), teto=(), opcoes=[["banco_onibus", "banco_onibus", "banco_onibus"]], janela="onibus", barras=True),
    "metro": dict(classe="media", parede=("liso",), piso=("cimento",), teto=("fluorescente",), opcoes=[["banco_onibus", "banco_onibus", "banco_onibus"]], janela="onibus", barras=True, escuro=True),
    "praia": dict(ext=True, chao="areia", mar=True, fundo=[("guarda_sol", 560), ("guarda_sol", 90)]),
    "sitio": dict(ext=True, chao="grama", fundo=[("morro", 360), ("arvore", 110), ("cerca", 360)]),
    "feira": dict(ext=True, chao="calcada", fundo=[("casa", 60), ("casa", 660), ("barraca", 200), ("barraca", 580)]),
    "mercado": dict(classe="media", parede=("liso",), piso=("ceramica",), teto=("fluorescente",), opcoes=[["prateleira", "prateleira", "caixa"], ["caixa", "prateleira", "prateleira"]], parede_itens=[]),
    "boteco": dict(classe="pobre", parede=("azulejo", "descascada"), piso=("xadrez", "cimento"), teto=("lampada",), opcoes=[["balcao"], ["mesa_bar", "balcao"]], parede_itens=["garrafas"], fundos=["garrafas"]),
    "restaurante": dict(classe="rica", parede=("painel", "listras"), piso=("tabua",), teto=("lustre",), opcoes=[["mesa_bar", "mesa_bar", "planta"]], parede_itens=["quadro", "quadro"]),
    "cinema": dict(classe="media", parede=("liso",), piso=("carpete",), teto=(), opcoes=[[]], parede_itens=["tela"], frente=[("poltronas", 360)], sem_janela=True, escuro=True),
    "praca": dict(ext=True, chao="calcada", fundo=[("predio", 40), ("predio", 690), ("arvore", 130), ("arvore", 600), ("banco_igreja", 360)]),
    "delegacia": dict(classe="pobre", parede=("meia", "descascada"), piso=("cimento",), teto=("fluorescente",), opcoes=[["grade", "mesa_del"]], parede_itens=["quadro"]),
    "oficina": dict(classe="pobre", parede=("tijolo", "descascada"), piso=("cimento",), teto=("fluorescente",), opcoes=[["macaco", "pneu"]], parede_itens=["ferramentas"]),
    "lan_house": dict(classe="pobre", parede=("liso", "listras"), piso=("ceramica",), teto=("fluorescente",), opcoes=[["pc", "pc", "pc"]], parede_itens=[]),
    "escola": dict(classe="media", parede=("meia",), piso=("tabua", "ceramica"), teto=("fluorescente",), opcoes=[["carteira", "carteira", "carteira"]], parede_itens=["lousa"]),
    "escritorio": dict(classe="media", parede=("liso", "painel"), piso=("carpete",), teto=("fluorescente",), opcoes=[["mesa_escritorio", "mesa_escritorio"], ["mesa_escritorio", "planta", "estante"]], parede_itens=["quadro"]),
    "festa": dict(classe="media", parede=("liso", "listras"), piso=("ceramica",), teto=("lampada",), opcoes=[["mesa", "planta"]], parede_itens=["baloes", "baloes"], aereo=["guirlanda"]),
    "casamento": dict(classe="rica", parede=("painel",), piso=("carpete",), teto=("lustre",), opcoes=[["arco"]], parede_itens=[], frente=[("banco_igreja", 170), ("banco_igreja", 570)], aereo=["guirlanda"]),
    "ponto_onibus": dict(ext=True, chao="calcada", fundo=[("predio", 90), ("casa", 620), ("fios", 280), ("ponto", 360)]),
    "rua": dict(ext=True, chao="calcada", fundo=[("casa", 100), ("casa", 430), ("casa", 760), ("fios", 280)]),
    "bairro_nobre": dict(ext=True, chao="calcada", fundo=[("predio", 90), ("predio", 620), ("arvore", 360), ("carro", 560)]),
    "palco": dict(classe="media", parede=("liso",), piso=("tabua",), teto=(), opcoes=[[]], parede_itens=[], aereo=[], cortina=True, sem_janela=True, escuro=True),
}


def compor(tipo: str = "casa_media", semente: int = 1, hora: str = "dia", clima: str = "bom", classe: str | None = None, **_: Any) -> dict[str, Any]:
    tipo = tipo if tipo in R else "casa_media"
    rc = R[tipo]
    rng = random.Random(f"{tipo}{semente}")
    cl = classe or rc.get("classe", "media")
    pal = paleta(semente, cl)
    if rc.get("ext"):
        ch = rc["chao"]
        y0 = 860
        fundo = ""
        rec = list(rc["fundo"])
        if rc.get("mar"):
            fundo += _mar(y0)
        for it in rec:
            n, x = it[0], it[1]
            dx = rng.randint(-34, 34) if n not in ("fios", "muro", "cerca", "morro") else 0
            fundo += M[n](x + dx, (280 if n == "fios" else y0 - 6), pal)
        sc: dict[str, Any] = dict(ceu=ceu(hora, clima, semente), fundo=chao_ext(ch, pal, y0) + fundo, meio="", frente="", luz=_luz(hora, clima, True))
        if clima == "chuva":
            from .cenarios import _chuva
            sc["frente"] = _chuva()
        sc["chao"] = y0
        return sc
    y0 = 800
    p_t = rng.choice(rc["parede"])
    pi = rng.choice(rc["piso"])
    op = list(rng.choice(rc["opcoes"]))
    fundo = parede(p_t, pal, y0, rng) + piso(pi, pal, y0)
    jan = rc.get("janela")
    xs = [190, 400, 610] if len(op) >= 3 else [190, 560] if len(op) == 2 else [360]
    if rc.get("escuro"):
        pal = {**pal, "parede": _hls(.65, .16, .25), "parede2": _hls(.65, .2, .25), "rodape": _hls(.65, .1, .2)}
        fundo = parede(p_t, pal, y0, rng) + piso(pi, pal, y0)
    centrais = {"tela", "lousa", "garrafas", "ferramentas"}
    tem_central = bool(centrais & set(rc.get("parede_itens") or []))
    if jan == "onibus":
        fundo += m_janela_onibus(360, 250, pal)
    jx = -999
    if jan != "onibus" and not rc.get("sem_janela") and not tem_central:
        jx = rng.choice((60, 260, 460))
        w = 300 if jan == "grande" else rng.choice((170, 210))
        fundo += janela(jx, rng.randint(170, 220), w, rng.randint(190, 240), "chuva" if clima == "chuva" else hora, pal, cortina=cl != "pobre" or rng.random() < .4, grade=cl == "pobre" and rng.random() < .3)
    for k, n in enumerate(rc.get("parede_itens") or []):
        if n == "tela":
            fundo += m_tela(360, 460, pal)
        elif n == "lousa":
            fundo += m_lousa(360, 300, pal)
        elif n == "garrafas":
            fundo += m_garrafas(360, 380, pal)
        elif n == "ferramentas":
            fundo += m_ferramentas(360, 300, pal)
        elif n == "baloes":
            fundo += m_baloes(120 + k * 480, 180, pal)
        else:
            livres = [x for x in (110, 300, 490, 640) if abs(x - (jx + 100)) > 230]  # nada na frente da janela
            fundo += M[n](livres[k % len(livres)] if livres else 620, rng.randint(280, 340), pal)
    for n, x in zip(op, xs):
        fundo += M[n](x + rng.randint(-16, 16), y0 + 6, pal)
    aereo = "".join(M[n](360, 150, pal) for n in rc.get("aereo") or [])
    if rc.get("barras"):
        aereo += m_barras(360, 800, pal)
    if rc.get("cortina"):
        aereo += m_cortina_palco(360, 800, pal)
    t = rc.get("teto") or ()
    if t:
        n = rng.choice(t)
        aereo += M[n](rng.choice((270, 360, 450)), {"lampada": 170, "fluorescente": 150, "lustre": 150}[n], pal)
    fr = "".join(M[n](x, 1120, pal) for n, x in rc.get("frente") or [])
    return dict(fundo=fundo + aereo, meio="", frente=fr, luz=_luz("noite" if rc.get("escuro") else hora, clima, False), chao=y0)


def _luz(hora, clima, ext):
    if clima == "chuva":
        return '<rect x="-640" y="-600" width="2000" height="2600" fill="#1c2438" opacity=".42" style="mix-blend-mode:multiply"/>'
    if hora == "noite":
        return f'<rect x="-640" y="-600" width="2000" height="2600" fill="#1c2452" opacity="{.5 if ext else .3}" style="mix-blend-mode:multiply"/>'
    if hora == "tarde":
        return '<rect x="-640" y="-600" width="2000" height="2600" fill="#ffb46a" opacity=".2" style="mix-blend-mode:soft-light"/>'
    return ""


def detalhe(cor: str = "#a9784c", cor2: str = "#8d6238", **_: Any) -> dict[str, Any]:
    """Fundo do plano de detalhe: a superfície do lugar, com veios."""
    s = f'<rect x="-300" y="-300" width="1400" height="1900" fill="{cor}"/>' + "".join(f'<path d="M-300 {y}C100 {y + 12} 500 {y - 12} 1100 {y}" fill="none" stroke="{cor2}" stroke-width="3"/>' for y in range(-200, 1600, 70))
    return dict(fundo=s, meio="", frente="", luz="")
