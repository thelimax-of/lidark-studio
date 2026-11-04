"""Objetos desenhados à mão. Origem no ponto de apoio (base) ou no ponto de pega, quando vão na mão."""
from __future__ import annotations

from .base import L, ln


def moeda(r=10, cor='#d8b24a', cor2='#f2d67a'):
    return f'<g><ellipse cy="{r * .3:.1f}" rx="{r}" ry="{r * .5:.1f}" fill="#8e6f24" {ln(1.6)}/><ellipse rx="{r}" ry="{r * .5:.1f}" fill="{cor}" {ln(1.6)}/><ellipse cx="{-r * .2:.1f}" cy="{-r * .08:.1f}" rx="{r * .45:.1f}" ry="{r * .18:.1f}" fill="{cor2}"/></g>'


def moeda_frente(r=14):
    return f'<circle r="{r}" fill="#d8b24a" {ln(2)}/><circle r="{r * .72:.1f}" fill="none" stroke="#a8842e" stroke-width="2"/><path d="M{-r * .4:.1f} {-r * .4:.1f}A{r * .6:.1f} {r * .6:.1f} 0 0 1 {r * .3:.1f} {-r * .5:.1f}" fill="none" stroke="#f7e6a6" stroke-width="2.6" stroke-linecap="round"/>'


def pilha(n, r=10, x=0, y=0):
    return f'<g transform="translate({x} {y})"><ellipse cx="3" cy="{r * .4:.1f}" rx="{r + 5}" ry="{r * .55:.1f}" fill="#2a1c14" opacity=".35"/>' + ''.join(f'<g transform="translate(0 {-i * 4.2:.1f})">{moeda(r)}</g>' for i in range(n)) + '</g>'


def conta_mesa(texto='R$ 187,40'):
    """Conta de luz deitada na mesa, virada para quem está sentado (texto de ponta-cabeça para a câmera)."""
    return f'''<ellipse cx="4" cy="6" rx="70" ry="24" fill="#2a1c14" opacity=".3" filter="url(#b3)"/>
<g transform="rotate(178) scale(1 .62)"><path d="M-62-40H58L66 40H-54z" fill="#fbfaf2" {ln(2.4)}/><path d="M-48-28h52v10h-52z" fill="#d84035"/><path d="M-46-6h88M-44 8h70" stroke="#9aa0a8" stroke-width="3"/><text x="4" y="30" text-anchor="middle" font-family="Arial Black" font-size="14" fill="#b02c22">{texto}</text></g>'''


def conta_mao():
    return f'''<g transform="translate(14 -2) rotate(-6)"><rect x="-4" y="-46" width="74" height="96" fill="#fbfaf2" {ln(2.2)}/><rect x="4" y="-38" width="42" height="9" fill="#d84035"/><path d="M4-20h56M4-8h56M4 4h38" stroke="#9aa0a8" stroke-width="2.6"/></g>'''


def cofrinho(s=1):
    return f'''<g transform="scale({s})"><ellipse cx="4" cy="4" rx="46" ry="9" fill="#2a1c14" opacity=".35" filter="url(#b3)"/>
<path d="M-30-18l-4 24h12l2-24zM14-18l-2 24h12l4-24z" fill="#d9788e" {ln(2.2)}/>
<path d="M-40-30C-44-58-10-68 16-62C34-58 42-40 36-24C28-4-34-6-40-30z" fill="#ee8ea0" {ln(2.6)}/>
<path d="M-28-46C-20-56-6-60 6-59" stroke="#ffd6df" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M-34-20C-22-8 18-8 34-26C22-4-28-6-34-20z" fill="#c9667c"/>
<path d="M-14-63h24" {ln(4)}/><circle cx="24" cy="-40" r="3" fill="{L}"/><path d="M34-34c8 0 12 6 4 11" fill="#ee8ea0" {ln(2.4)}/><path d="M18-58l6-12 8 10z" fill="#ee8ea0" {ln(2.4)}/></g>'''


def cofrinho_mao():
    return f'<g transform="translate(26 24) rotate(-6) scale(.66)">{cofrinho()}</g>'


def botao(r=10):
    return f'<circle r="{r}" fill="#3f83c9" {ln(2)}/><circle r="{r * .66:.1f}" fill="none" stroke="#7fb4e6" stroke-width="2"/><circle cx="-2.6" cy="-2.6" r="1.7" fill="{L}"/><circle cx="2.6" cy="-2.6" r="1.7" fill="{L}"/><circle cx="-2.6" cy="2.6" r="1.7" fill="{L}"/><circle cx="2.6" cy="2.6" r="1.7" fill="{L}"/>'


def brigadeiro(r=11, q=False):
    c = '#23120f' if q else '#5a3220'
    gr = ''.join(f'<rect x="{x}" y="{y}" width="3" height="1.8" fill="{"#555" if q else "#f0c23a" if (x + y) % 3 else "#f4f0e0"}" transform="rotate({x * 7} {x} {y})"/>' for x, y in [(-6, -5), (2, -7), (6, -1), (-3, 1), (3, 4), (-7, 3), (0, -3)])
    forminha = f'<path d="M{-r - 1} 2L{-r + 3} {r + 2}H{r - 3}L{r + 1} 2z" fill="#c8513a" {ln(1.8)}/><path d="M{-r + 4} 4l1 {r - 3}M-2 4v{r - 3}M{r - 5} 4l-1 {r - 3}" stroke="#8f3322" stroke-width="1.6"/>'
    return f'<g>{forminha}<circle cy="-2" r="{r}" fill="{c}" {ln(2)}/>{gr}<ellipse cx="-4" cy="-7" rx="3.4" ry="2" fill="#fff" opacity=".35"/></g>'


def brigadeiro_mao():
    return f'<g transform="translate(25 -6) scale(.9)">{brigadeiro()}</g>'


def colher():
    return f'''<g transform="translate(14 0) rotate(90)"><rect x="-52" y="-3.5" width="100" height="7" rx="3.5" fill="#b98347" {ln(1.9)}/><ellipse cx="54" cy="0" rx="13" ry="8" fill="#c99457" {ln(1.9)}/></g>'''


def lapis():
    return f'<g transform="rotate(-70)"><path d="M-46-4H42L58 0L42 4H-46z" fill="#e8b73a" {ln(1.9)}/><path d="M42-4L58 0L42 4z" fill="#ecd8b4" {ln(1.5)}/><path d="M52-1.5L58 0L52 1.5z" fill="{L}"/><rect x="-52" y="-4" width="8" height="8" fill="#d8707a" {ln(1.5)}/></g>'


def placa_r2():
    return f'''<g transform="rotate(90)"><rect x="-4" y="-110" width="8" height="150" fill="#b98347" {ln(2)}/><g transform="translate(0 -128) rotate(-2)"><rect x="-58" y="-40" width="116" height="74" rx="4" fill="#f6efd8" {ln(2.6)}/><text y="4" text-anchor="middle" font-family="'Arial Black',Arial" font-size="32" fill="#c0392b">R$ 2</text><text y="26" text-anchor="middle" font-family="Arial" font-weight="700" font-size="14" fill="#3a2c28">BRIGADEIRO</text></g></g>'''


def caixa_isopor(cheia=True, s=1):
    """Caixinha com alça de pescoço, presa à frente do corpo; tampa aberta para trás."""
    b = ''
    if cheia:
        for r, y in enumerate((-30, -22)):
            for i in range(5):
                b += f'<g transform="translate({-40 + i * 20 + r * 10 - (5 if r else 0)} {y}) scale(.74)">{brigadeiro()}</g>'
    return f'''<g transform="scale({s})"><path d="M-58-28H58L64-62H-64z" fill="#fbfbf6" {ln(2.4)}/><path d="M-50-34H50L54-55H-54z" fill="#dfe6e8"/>
{b}<path d="M-58-26H58L54 22H-54z" fill="#f4f4ee" {ln(2.6)}/><path d="M-52-14H-30M-46 2H-16M10-12H44M24 8H48" stroke="#d9dcd6" stroke-width="3"/>
<path d="M-58-26H58" stroke="#bfc6c6" stroke-width="3"/></g>'''


def alca(xe=-48, xd=48, y0=-110, y1=-30):
    return f'<path d="M{xe} {y1}L-14 {y0}M{xd} {y1}L18 {y0}" fill="none" stroke="#6e4a2f" stroke-width="4.5" stroke-linecap="round"/>'


def bola(r=46):
    """Bola gasta do Caio: costuras e arranhões."""
    pent = ''
    import math
    P = lambda cx, cy, rr, rot=0: ' '.join(f'{cx + rr * math.cos(math.radians(a + rot)):.1f},{cy + rr * math.sin(math.radians(a + rot)):.1f}' for a in range(-90, 270, 72))
    k = r / 46
    pent += f'<polygon points="{P(0, 0, 15 * k)}" fill="{L}"/>'
    for a in range(-90, 270, 72):
        x = 34 * k * math.cos(math.radians(a))
        y = 34 * k * math.sin(math.radians(a))
        pent += f'<polygon points="{P(x, y, 12 * k, a + 36)}" fill="{L}"/>'
        xa = 16 * k * math.cos(math.radians(a))
        ya = 16 * k * math.sin(math.radians(a))
        pent += f'<path d="M{xa:.1f} {ya:.1f}L{x * .68:.1f} {y * .68:.1f}" stroke="{L}" stroke-width="2"/>'
    return f'''<g><clipPath id="clipBola{r}"><circle r="{r}"/></clipPath><circle r="{r}" fill="#f1ece0"/><g clip-path="url(#clipBola{r})">{pent}<path d="M{-r} 0A{r} {r} 0 0 0 {r} 0A{r * 1.2:.1f} {r * .9:.1f} 0 0 1 {-r} 0z" fill="#b4a78c" opacity=".3" transform="rotate(30)"/><ellipse cx="{-r * .35:.1f}" cy="{-r * .45:.1f}" rx="{r * .3:.1f}" ry="{r * .16:.1f}" fill="#fff" opacity=".7" transform="rotate(-30)"/></g><circle r="{r}" fill="none" {ln(2.6)}/></g>'''


def bola_mao():
    return f'<g transform="translate(40 -4)">{bola(34)}</g>'


def nota(valor='10', cor='#c98a3c'):
    return f'''<g><rect x="-34" y="-17" width="68" height="34" rx="2" fill="{cor}" {ln(2)}/><rect x="-29" y="-12" width="58" height="24" fill="none" stroke="#fff" stroke-opacity=".55" stroke-width="1.6"/><circle r="9" fill="#fff" opacity=".35"/><text y="5" text-anchor="middle" font-family="'Arial Black',Arial" font-size="14" fill="#3a2410">{valor}</text></g>'''


def nota_mao():
    return f'<g transform="translate(56 -2)">{nota("R$ 12")}</g>'


def nota_mao_virada():
    """A mesma nota na mão de quem olha para o outro lado: o texto não sai espelhado."""
    return f'<g transform="translate(56 -2) scale(-1 1)">{nota("R$ 12")}</g>'


def envelope(s=1, aberto=False):
    return f'''<g transform="scale({s})"><ellipse cx="4" cy="6" rx="76" ry="16" fill="#2a1c14" opacity=".35" filter="url(#b3)"/>
<g transform="scale(1 .7)"><path d="M-72-44H72V36H-72z" fill="#e7d3a6" {ln(2.6)}/><path d="M-72-44L0 8L72-44" fill="none" {ln(2.4)}/><path d="M-72 36L-16-8M72 36L16-8" fill="none" stroke="#b79e6c" stroke-width="2.4"/></g>
<text text-anchor="middle" font-family="'Comic Sans MS',cursive" font-weight="700" font-size="17" fill="#2f4f8a" transform="translate(0 14) rotate(180)">pra mãe</text></g>'''


def envelope_mao():
    return f'<g transform="translate(36 -2) rotate(4)"><rect x="-44" y="-26" width="88" height="56" fill="#e7d3a6" {ln(2.4)}/><path d="M-44-26L0 8L44-26" fill="none" {ln(2.2)}/></g>'


def mochila_chao():
    return f'''<g><ellipse cy="4" rx="60" ry="9" fill="#140e18" opacity=".32" filter="url(#b3)"/><path d="M-46 0C-58-50-50-112-4-118C46-118 56-56 46 0z" fill="#c8513a" {ln(2.6)}/><path d="M-36-8C-42-34-36-50-30-54H32C38-46 40-24 36-8z" fill="#a33f2c" {ln(2.2)}/><path d="M-30-74H32" {ln(3)}/><path d="M-16-118C-14-136 18-136 18-118" fill="none" {ln(5)}/></g>'''


def icone(k, s=38):
    z = s / 56
    if k == 'conta':
        d = f'<rect x="-22" y="-26" width="44" height="52" fill="#fbfaf2" {ln(2)}/><rect x="-16" y="-20" width="30" height="8" fill="#d8403a"/><path d="M-16-3h32M-16 8h32M-16 17h18" stroke="#9aa0a8" stroke-width="3.4"/>'
    elif k == 'cofrinho':
        d = f'<g transform="translate(0 22) scale(.68)">{cofrinho()}</g>'
    elif k == 'bola':
        d = f'<g transform="scale(.56)">{bola(46)}</g>'
    elif k == 'queimado':
        d = f'<g transform="scale(1.7)">{brigadeiro(11, True)}</g>'
    elif k == 'celular':
        d = f'<rect x="-13" y="-25" width="26" height="50" rx="4" fill="#20222a" {ln(2)}/><rect x="-10" y="-21" width="20" height="40" fill="#8fd0e8"/>'
    elif k == 'bicicleta':
        d = f'<g fill="none" {ln(3)}><circle cx="-14" cy="9" r="11"/><circle cx="16" cy="9" r="11"/><path d="M-14 9L-3-8H10L16 9M-3-8L2 9L10-8M-6-13H1M7-13H14" stroke="#e0672f"/></g>'
    elif k == 'camisa':
        d = f'<path d="M-9-22L-24-13-17-2-11-6V23H11V-6L17-2 24-13 9-22C5-17-5-17-9-22z" fill="#d9d4c6" {ln(2.2)}/><circle cx="1" cy="1" r="4" fill="#20222a"/>'
    elif k == 'camisa_azul':
        d = f'<path d="M-9-22L-24-13-17-2-11-6V23H11V-6L17-2 24-13 9-22C5-17-5-17-9-22z" fill="#d9d4c6" {ln(2.2)}/><circle cx="1" cy="1" r="5" fill="#2f5fd8"/>'
    elif k == 'pao':
        d = f'<path d="M-24 14C-34-16 28-24 30 12C31 22-20 24-24 14z" fill="#d9a05a" {ln(2.2)}/><path d="M-6-6l5 10M8-8l5 11" stroke="#a8743a" stroke-width="2.6"/>'
    elif k == 'alvo':
        d = f'<circle r="24" fill="#e8503a" {ln(2.2)}/><circle r="15" fill="#fff"/><circle r="7" fill="#e8503a"/>'
    elif k == 'pizza':
        d = f'<path d="M-24-18H24L0 26z" fill="#f0c23a" {ln(2.2)}/><circle cx="-6" cy="-6" r="4" fill="#c8513a"/><circle cx="8" cy="-8" r="4" fill="#c8513a"/><circle cx="1" cy="8" r="4" fill="#c8513a"/>'
    elif k == 'dinheiro':
        d = f'<rect x="-26" y="-15" width="52" height="30" rx="2" fill="#7fae6a" {ln(2.2)}/><circle r="8" fill="#fff" opacity=".5"/>'
    elif k == 'chefe':
        d = f'<circle r="24" fill="#e8503a" {ln(2.2)}/><path d="M-13-9L-3-4M13-9L3-4M-10 10C-4 4 4 4 10 10" fill="none" {ln(3)}/>'
    elif k == 'lista':
        d = f'<rect x="-18" y="-24" width="36" height="48" fill="#fbf6e6" {ln(2)}/><path d="M-11-13h22M-11-3h22M-11 7h14" stroke="#2a3a7a" stroke-width="3"/>'
    elif k == 'melancia':
        d = f'<path d="M-24-6A24 24 0 0 0 24-6z" fill="#2f8a4a" {ln(2.2)}/><path d="M-19-6A19 19 0 0 0 19-6z" fill="#e8504a"/>'
    elif k == 'brigadeiro':
        d = f'<g transform="scale(1.7)">{brigadeiro(11)}</g>'
    else:
        d = ''
    return f'<g transform="scale({z:.3f})">{d}</g>'


def celular_mao():
    """Celular em pé, seguro pela base: dedos da frente passam por cima."""
    return f'<g transform="translate(25 -3) rotate(-4)"><rect x="-15" y="-58" width="30" height="66" rx="5" fill="#20222a" {ln(2)}/><rect x="-12" y="-54" width="24" height="56" rx="2" fill="#8fd0e8"/><path d="M-9-44h18M-9-34h12" stroke="#fff" stroke-width="3"/></g>'


def caneta_mao():
    return f'<g transform="translate(20 0) rotate(66)"><rect x="-30" y="-3" width="52" height="6" rx="2" fill="#2f5fa8" {ln(1.6)}/><path d="M22-3L34 0L22 3z" fill="#e8e3d4" {ln(1.4)}/></g>'


def pizza_mao():
    return f'<g transform="translate(62 -8)"><path d="M-60-6H58L52-16H-54z" fill="#e8b56a" {ln(2.2)}/><rect x="-60" y="-6" width="118" height="16" fill="#d29a4e" {ln(2.2)}/><text y="7" text-anchor="middle" font-family="Arial Black,Arial" font-size="11" fill="#7a2f1e">PIZZA</text></g>'


def notas_mao():
    return f'<g transform="translate(30 -6) rotate(-14)"><rect x="-4" y="-14" width="54" height="26" rx="2" fill="#7fae6a" {ln(1.8)}/><rect x="-2" y="-17" width="54" height="26" rx="2" fill="#c98a3c" {ln(1.8)}/><circle cx="25" cy="-4" r="6" fill="#fff" opacity=".4"/></g>'


def camisa_mao():
    return f'<g transform="translate(26 0)"><path d="M-4-74C-10-86 8-90 10-80" fill="none" {ln(2.6)}/><path d="M0-70L-46-46L-30-30H30L46-46z" fill="#b98347" {ln(2)}/><path d="M-24-46L-66-16L-46 14L-32 2V96H32V2L46 14L66-16L24-46C14-30-14-30-24-46z" fill="#e9e2d2" {ln(2.6)}/><circle cx="-8" cy="22" r="7" fill="#20222a"/></g>'


def pao_mao():
    return f'<g transform="translate(28 -2)"><path d="M-22 12C-30-14 24-22 30 8C32 18-18 22-22 12z" fill="#d9a05a" {ln(2.2)}/><path d="M-6-4l5 9M8-8l5 10" stroke="#a8743a" stroke-width="2.4"/></g>'


MAO = dict(camisa=camisa_mao(), pao=pao_mao(), celular=celular_mao(), caneta=caneta_mao(), pizza=pizza_mao(), notas=notas_mao())
