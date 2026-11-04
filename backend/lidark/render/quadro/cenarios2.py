"""Cenários e objetos da série "O Encontro". Registra tudo em cenarios.CENARIOS."""
from __future__ import annotations

import textwrap

from . import cenarios, itens, personagens
from .base import L, ln
from .cenarios import _txt, _piso_tabua, _nuvem, _carro

NA_CABECA = {}
DEFS = '''<linearGradient id="night" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16214a"/><stop offset="1" stop-color="#3a3f73"/></linearGradient>
<linearGradient id="qzParede" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d9c8a4"/><stop offset="1" stop-color="#c7b48e"/></linearGradient>
<linearGradient id="manha" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#9fd2ec"/><stop offset="1" stop-color="#fbe6b8"/></linearGradient>
<radialGradient id="qzSol" gradientUnits="userSpaceOnUse" cx="250" cy="420" r="640"><stop offset="0" stop-color="#ffe6a8" stop-opacity=".5"/><stop offset="1" stop-color="#ffe6a8" stop-opacity="0"/></radialGradient>
<radialGradient id="qzNoite" gradientUnits="userSpaceOnUse" cx="420" cy="560" r="800"><stop offset=".2" stop-color="#141a3e" stop-opacity=".12"/><stop offset=".6" stop-color="#141a3e" stop-opacity=".55"/><stop offset="1" stop-color="#0c1030" stop-opacity=".88"/></radialGradient>
<radialGradient id="geloLuz"><stop offset="0" stop-color="#e8f6ff" stop-opacity=".9"/><stop offset="1" stop-color="#e8f6ff" stop-opacity="0"/></radialGradient>
<linearGradient id="padParede" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f0dcb4"/><stop offset="1" stop-color="#e2c896"/></linearGradient>
<radialGradient id="padNoite" gradientUnits="userSpaceOnUse" cx="400" cy="500" r="780"><stop offset=".25" stop-color="#141a3e" stop-opacity="0"/><stop offset=".65" stop-color="#141a3e" stop-opacity=".42"/><stop offset="1" stop-color="#0c1030" stop-opacity=".8"/></radialGradient>
<linearGradient id="hallP" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bfc4bd"/><stop offset="1" stop-color="#a6aca4"/></linearGradient>
<radialGradient id="chefeF"><stop offset="0" stop-color="#e8503a"/><stop offset="1" stop-color="#7a1f18"/></radialGradient>'''


def neutro(cor='#d8cfc0'):
    return dict(fundo=f'<rect x="-400" y="-400" width="1600" height="2200" fill="{cor}"/><rect x="-400" y="1190" width="1600" height="700" fill="#b9ae9c"/><path d="M-400 1190H1200" {ln(2)}/>', meio='', frente='', luz='')


def bicicleta(s=1):
    """Vista de lado, ponto de apoio no chão, entre as rodas. Rodas com raios que giram."""
    roda = lambda x: (f'<g transform="translate({x} -120)"><circle r="118" fill="none" stroke="{L}" stroke-width="13"/><circle r="118" fill="none" stroke="#4a4a52" stroke-width="7"/>'
                      f'<g data-vida="gira:540:0"><path d="M-112 0H112M0-112V112M-80-80L80 80M-80 80L80-80" stroke="#8a8f98" stroke-width="2.4"/></g><circle r="12" fill="#3a3a42" {ln(2.4)}/></g>')
    q = '#e0672f'
    tb = lambda d: f'<path d="{d}" fill="none" stroke="{L}" stroke-width="15" stroke-linecap="round" stroke-linejoin="round"/><path d="{d}" fill="none" stroke="{q}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>'
    return (f'<g transform="scale({s})"><ellipse cy="4" rx="310" ry="15" fill="#101016" opacity=".32" filter="url(#b6)"/>{roda(-170)}{roda(200)}'
            f'{tb("M-170-120L-40-325M-170-120L30-100L140-300M-40-325L140-300M30-100L-40-325M200-120L140-300L128-378")}'
            f'<path d="M-92-340C-56-352-14-350 12-338C-10-326-60-326-92-340z" fill="#2a2830" {ln(2.4)}/>'
            f'<path d="M128-378L190-392" stroke="{L}" stroke-width="13" stroke-linecap="round"/><path d="M128-378L190-392" stroke="#3a3a42" stroke-width="7" stroke-linecap="round"/>'
            f'<circle cx="30" cy="-100" r="24" fill="#3a3a42" {ln(2.4)}/><path d="M10-104L-62-30" stroke="#3a3a42" stroke-width="0"/></g>')


def bicicleta_parada(s=1):
    return bicicleta(s).replace('data-vida="gira:540:0"', '')


def geladeira_aberta():
    """Porta aberta, luz fria, uma garrafa e a plaquinha ESPERANÇA."""
    return f'''<ellipse cx="0" cy="214" rx="100" ry="40" fill="url(#geloLuz)"/><path d="M-70-210H78V212H-70z" fill="#f3f8fb" {ln(3)}/><rect x="-58" y="-198" width="124" height="398" fill="#e6f1f6" {ln(2)}/><path d="M-58-70H66M-58 60H66" stroke="#b9cdd8" stroke-width="5"/>
<g transform="translate(-22 56)"><path d="M-14 0V-74C-14-88-6-92-6-104H6C6-92 14-88 14-74V0z" fill="#b9e3f2" {ln(2.4)}/><path d="M-14-46H14V0H-14z" fill="#7fc4e2"/><rect x="-7" y="-114" width="14" height="10" fill="#2f6fa8" {ln(2)}/></g>
<g transform="translate(28 -92) rotate(-4)"><path d="M-6-22L0-30L6-22" fill="none" {ln(1.8)}/><rect x="-48" y="-22" width="96" height="36" rx="3" fill="#fff0a0" {ln(2.4)}/><text y="4" text-anchor="middle" font-family="'Arial Black',Arial" font-size="12.5" fill="#b02c22">ESPERANÇA</text></g>
<path d="M-70-210L-160-180V238L-70 212z" fill="#dfe6ea" {ln(3)}/><path d="M-82-120h-58M-82-40h-58" stroke="#b9c4ca" stroke-width="4"/><rect x="-154" y="40" width="14" height="70" rx="6" fill="#8e9599" {ln(2.2)}/>'''


def _gel_fechada():
    return f'<path d="M-70-210H78V212H-70z" fill="#eef2f1" {ln(3)}/><path d="M-70-96H78" {ln(2.6)}/><rect x="-56" y="-160" width="10" height="50" rx="5" fill="#8e9599" {ln(2.2)}/><rect x="-56" y="-76" width="10" height="70" rx="5" fill="#8e9599" {ln(2.2)}/><rect x="10" y="-180" width="40" height="44" fill="#fff0a0" transform="rotate(4 30 -158)" {ln(2)}/>'


def quartinho(hora='manha', mesa='frente'):
    noite = hora == 'noite'
    jan = 'url(#night)' if noite else 'url(#manha)'
    fora = '<circle cx="330" cy="250" r="16" fill="#f2eccb"/>' if noite else _nuvem(280, 240, .5) + _nuvem(200, 300, .4)
    pre = f'<path d="M150 400V330h40v-30h60v50h50v-24h50v74z" fill="{"#101636" if noite else "#c9b88f"}"/>'
    bol = ''.join(f'<path d="M{x} {y}c10-12 22-8 26 2c-8 6-20 8-26-2z" fill="#b7a27c"/>' for x, y in [(60, 120), (640, 150), (880, 90), (500, 620)])
    fundo = f'''<rect x="-400" y="-500" width="2000" height="1320" fill="url(#qzParede)"/>{bol}<rect x="-400" y="786" width="2000" height="16" fill="#6a5240" {ln(2)}/>{_piso_tabua(520, '#9a7858', '#86664a')}
<rect x="140" y="200" width="230" height="210" fill="{jan}" {ln(4)}/>{fora}{pre}<path d="M255 200V410M140 305H370" {ln(4)}/><rect x="128" y="408" width="254" height="14" fill="#efe4c4" {ln(2.8)}/>
<g data-vida="rot:.5:.8:0:120:190"><path d="M124 192C150 250 132 330 140 396H110V192z" fill="#7fa08a" {ln(2.4)}/></g><g data-vida="rot:.5:.9:1:386:190"><path d="M384 192C358 250 376 330 368 392L400 396V192z" fill="#7fa08a" {ln(2.4)}/></g><path d="M112 186H398" stroke="#6e4a2f" stroke-width="8" stroke-linecap="round"/>
<g transform="translate(470 250)"><rect x="-34" y="0" width="68" height="84" fill="#f7f1e0" {ln(2.4)}/><rect x="-34" y="0" width="68" height="20" fill="#c8513a" {ln(2.4)}/>{_txt(0, 15, "SEGUNDA", 11, "#fff")}{_txt(0, 62, "26", 34, L)}</g>
<g transform="translate(240 860)"><ellipse cy="10" rx="240" ry="14" fill="#140e18" opacity=".32" filter="url(#b6)"/><path d="M-226-70H220V4H-226z" fill="#6a4a34" {ln(2.8)}/><path d="M-230-120C-230-136-216-140-200-140H210C226-140 232-126 232-112V-66H-230z" fill="#4f7f8f" {ln(2.8)}/><path d="M-100-140V-66M40-140V-66" stroke="#3f6a78" stroke-width="16"/><path d="M-226-140C-232-176-214-190-184-190H-112C-84-190-78-170-84-140z" fill="#f1ece0" {ln(2.6)}/></g>'''
    g = f'<g transform="translate(650 594)"><g data-obj="gel_fechada">{_gel_fechada()}</g></g>'
    arm = f'''<g transform="translate(930 800)"><ellipse cy="6" rx="150" ry="10" fill="#140e18" opacity=".32" filter="url(#b6)"/><rect x="-136" y="-540" width="272" height="540" fill="#8a6548" {ln(3)}/><path d="M0-540V-30" {ln(3)}/><rect x="-136" y="-30" width="272" height="30" fill="#6e4a30" {ln(2.6)}/><circle cx="-14" cy="-280" r="6" fill="#d8b24a" {ln(2)}/><circle cx="14" cy="-280" r="6" fill="#d8b24a" {ln(2)}/><path d="M-110-500V-70M110-500V-70" stroke="#6e4a30" stroke-width="3" opacity=".7"/></g>'''
    cad = f'<path d="M398 700H420L424 960H402zM610 700H588L584 960H606z" fill="#7a5238" {ln(3)}/>'
    tab = f'''<path d="M372 712H640L654 744H358z" fill="#b98a58" {ln(3)}/><path d="M358 744H654V760H358z" fill="#8f6440" {ln(2.8)}/><path d="M376 760L366 1000H388L404 760zM634 760L646 1000H624L608 760z" fill="#6e4a30" {ln(3)}/>'''
    if noite:
        lz = '<rect x="-400" y="-500" width="2000" height="2300" fill="url(#qzNoite)" style="mix-blend-mode:multiply"/>'
    else:
        lz = '<rect x="-400" y="-500" width="2000" height="2300" fill="url(#qzSol)" style="mix-blend-mode:soft-light"/>'
    return dict(defs=DEFS, fundo=fundo + g + arm, meio=cad + (tab if mesa == 'atras' else ''), frente='' if mesa == 'atras' else tab, luz=lz)


def garrafa_cena():
    return geladeira_aberta()


def padaria(hora='dia'):
    noite = hora == 'noite'
    prat = ''
    for y in (300, 410, 520):
        prat += f'<rect x="300" y="{y}" width="440" height="12" fill="#8a6548" {ln(2.6)}/>'
        for x in range(320, 720, 62):
            prat += f'<g transform="translate({x} {y - 4})"><path d="M-24 0C-28-24 26-30 28 0z" fill="#d9a05a" {ln(2.2)}/><path d="M-10-14l6 10M4-18l6 12" stroke="#a8743a" stroke-width="2.6"/></g>'
    fundo = f'''<rect x="-400" y="-500" width="2000" height="1320" fill="url(#padParede)"/><rect x="-400" y="640" width="2000" height="160" fill="#c8513a"/><rect x="-400" y="634" width="2000" height="10" fill="#f7efdc" {ln(2)}/>
<rect x="-400" y="786" width="2000" height="16" fill="#6a5240" {ln(2)}/>{cenarios.piso_quadriculado(380)}
<rect x="40" y="180" width="210" height="330" fill="{'url(#night)' if noite else 'url(#manha)'}" {ln(4)}/><path d="M145 180V510M40 340H250" {ln(4)}/>
<rect x="300" y="195" width="440" height="70" rx="6" fill="#7a3b24" {ln(3)}/>{_txt(520, 248, "PADARIA", 48, "#fbf0d4")}{prat}
<g transform="translate(90 620)"><rect x="-44" y="0" width="88" height="110" rx="4" fill="#f7efdc" {ln(2.4)}/>{_txt(0, 34, "PÃO", 20, "#b02c22")}{_txt(0, 78, "R$ 1", 28, "#b02c22")}</g>'''
    balc = f'''<path d="M330 640H860V830H330z" fill="#d9c8a4" {ln(3.2)}/><path d="M318 620H872V644H318z" fill="#8a6548" {ln(3)}/><path d="M340 640V830M470 640V830M600 640V830M730 640V830" stroke="#b9a67e" stroke-width="4"/>
<g transform="translate(700 620)"><rect x="-70" y="-74" width="140" height="74" rx="6" fill="#dfe9ec" opacity=".7" {ln(2.6)}/><path d="M-54-14C-58-34-22-40-20-14zM-8-14C-12-34 24-40 26-14z" fill="#d9a05a" {ln(2)}/></g>
<g transform="translate(420 620)"><rect x="-44" y="-44" width="88" height="44" rx="4" fill="#3a3f4c" {ln(2.6)}/><rect x="-34" y="-36" width="68" height="16" fill="#9fd08a"/></g>
<ellipse cx="596" cy="850" rx="310" ry="16" fill="#140e18" opacity=".3" filter="url(#b6)"/>'''
    lz = '<rect x="-400" y="-500" width="2000" height="2300" fill="url(#padNoite)" style="mix-blend-mode:multiply"/>' if noite else ''
    return dict(defs=DEFS, fundo=fundo, meio='', frente=balc, luz=lz)


def rua_dia():
    sc = cenarios.rua('poente')
    sc['ceu'] = sc['ceu'].replace('ceuPoente', 'ceuSol').replace('#f4a878', '#ffffff').replace('<circle cx="120" cy="420" r="52" fill="#ffe2a0"/>', '<circle cx="120" cy="240" r="46" fill="#fff0a0"/>').replace('<circle cx="120" cy="420" r="210" fill="url(#solG)"/>', '<circle cx="120" cy="240" r="190" fill="url(#solG)"/>')
    sc['luz'] = ''
    sc['frente'] = ''
    return sc


def _melancia(x, y, s=1):
    return f'<g transform="translate({x} {y}) scale({s})"><ellipse cy="26" rx="46" ry="10" fill="#140e18" opacity=".3"/><ellipse rx="46" ry="30" fill="#2f8a4a" {ln(2.6)}/><path d="M-30-14C-36 0-36 12-28 20M-8-28C-14-8-14 10-8 28M14-28C20-8 20 10 14 28M32-14C38 0 38 10 30 18" fill="none" stroke="#1f6a38" stroke-width="5"/></g>'


def _fatia(x, y, r=0, s=1):
    return f'<g transform="translate({x} {y}) rotate({r}) scale({s})"><path d="M-40 0A40 40 0 0 0 40 0z" fill="#2f8a4a" {ln(2.4)}/><path d="M-33 0A33 33 0 0 0 33 0z" fill="#f4f0d8"/><path d="M-29 0A29 29 0 0 0 29 0z" fill="#e8504a"/><path d="M-12 8l2 5M4 12l1 5M16 6l2 5" stroke="#241c22" stroke-width="3" stroke-linecap="round"/></g>'


def feira(destruida=False):
    sc = rua_dia()
    x, y = 620, 1000
    tol = ''.join(f'<path d="M{i * 64 - 220} -300H{i * 64 - 156}L{i * 64 - 160} -226H{i * 64 - 224}z" fill="{"#e8503a" if i % 2 else "#fbf0d4"}" {ln(2.4)}/>' for i in range(7))
    placa = f'<g transform="translate(0 -210)"><rect x="-110" y="-32" width="220" height="64" rx="4" fill="#fbf0d4" {ln(2.8)}/>{_txt(0, -2, "MELANCIA", 28, "#2f7a4a")}{_txt(0, 24, "R$ 5", 20, "#b02c22")}</g>'
    if not destruida:
        b = (f'<g transform="translate({x} {y})"><ellipse cy="6" rx="270" ry="14" fill="#140e18" opacity=".3" filter="url(#b6)"/><path d="M-210-300V0M210-300V0" stroke="{L}" stroke-width="12"/><path d="M-210-300V0M210-300V0" stroke="#8a6548" stroke-width="7"/>{tol}'
             f'<rect x="-230" y="-110" width="460" height="110" fill="#8a6548" {ln(3)}/>{placa}{_melancia(-140, -140)}{_melancia(-40, -140)}{_melancia(60, -140)}{_melancia(150, -136, .9)}{_melancia(-90, -180, .9)}{_melancia(10, -182, .9)}{_melancia(100, -176, .86)}</g>')
    else:
        b = (f'<g transform="translate({x} {y})"><ellipse cy="6" rx="300" ry="16" fill="#140e18" opacity=".3" filter="url(#b6)"/><path d="M-210-210L-250 0M240-120L190 0" stroke="{L}" stroke-width="12"/><path d="M-210-210L-250 0M240-120L190 0" stroke="#8a6548" stroke-width="7"/>'
             f'<g transform="translate(-40 0) rotate(12)">{tol}</g><path d="M-250-60L-30-20L-60 0H-270zM30-30L230-70L210 0H10z" fill="#8a6548" {ln(3)}/><g transform="translate(150 -70) rotate(22) scale(.8)">{placa}</g></g>')
        b += _fatia(420, 1060, 20) + _fatia(540, 1090, -30, 1.1) + _fatia(720, 1050, 60) + _fatia(830, 1090, -10) + _fatia(330, 1100, 80, .9) + _melancia(880, 1020, .8)
        b += ''.join(f'<ellipse cx="{a}" cy="{c}" rx="{r}" ry="{r * .3:.0f}" fill="#e8504a" opacity=".7"/>' for a, c, r in [(500, 1120, 50), (680, 1120, 70), (800, 1130, 40)])
    sc['meio'] = sc['meio'] + b
    return sc


def hall():
    fundo = f'''<rect x="-400" y="-500" width="2000" height="1320" fill="url(#hallP)"/><rect x="-400" y="786" width="2000" height="16" fill="#6a6e68" {ln(2)}/>{cenarios.piso_quadriculado(360)}
<g transform="translate(290 0)"><rect x="-120" y="240" width="240" height="560" fill="#8e9599" {ln(3)}/><rect x="-104" y="256" width="102" height="544" fill="#b8bcc0" {ln(2.6)}/><rect x="2" y="256" width="102" height="544" fill="#b8bcc0" {ln(2.6)}/>
<rect x="-44" y="194" width="88" height="36" rx="4" fill="#20222a" {ln(2)}/>{_txt(0, 220, "T", 22, "#e8503a")}
<g transform="translate(0 500) rotate(-6)"><rect x="-120" y="-54" width="240" height="108" fill="#fff0a0" {ln(3)}/>{_txt(0, -6, "ELEVADOR", 32, "#b02c22")}{_txt(0, 36, "QUEBRADO", 34, "#b02c22")}<rect x="-30" y="-64" width="60" height="18" fill="#e8d98a" opacity=".9"/></g></g>
<g transform="translate(620 0)"><rect x="-90" y="300" width="180" height="500" fill="#6e4a30" {ln(3)}/><rect x="-74" y="316" width="148" height="484" fill="#3a3238" {ln(2.4)}/><path d="M-74 800L-20 640H74V800z" fill="#6a6e68"/><path d="M-60 780h120M-44 740h110M-30 700h100M-18 664h90" stroke="#3a3238" stroke-width="5"/><rect x="-70" y="250" width="140" height="40" rx="4" fill="#2f7a4a" {ln(2.4)}/>{_txt(0, 278, "ESCADA", 24, "#fff")}</g>'''
    return dict(defs=DEFS, fundo=fundo, meio='', frente='', luz='')


def escada():
    deg = ''
    for i in range(14):
        x, y = -40 + i * 58, 1120 - i * 46
        deg += f'<path d="M{x} {y}h58v46h-58z" fill="#b6b2a6" {ln(2.6)}/><path d="M{x} {y}h58v8h-58z" fill="#d4d0c4"/>'
    corr = f'<path d="M-60 880L800 200" stroke="{L}" stroke-width="13"/><path d="M-60 880L800 200" stroke="#8a6548" stroke-width="7"/>' + ''.join(f'<path d="M{20 + i * 110} {820 - i * 87}v110" stroke="{L}" stroke-width="5"/>' for i in range(7))
    fundo = f'<rect x="-400" y="-500" width="2000" height="2300" fill="url(#hallP)"/><path d="M-400 1000L1200 -240" stroke="#8e9490" stroke-width="60" opacity=".5"/><g transform="translate(610 440)"><circle r="60" fill="#2f7a4a" {ln(3)}/>{_txt(0, 22, "8º", 54, "#fff")}</g><g transform="translate(600 900)"><rect x="-92" y="-40" width="184" height="80" fill="#fbf6e6" {ln(2.4)}/>{_txt(0, -6, "FALTAM", 22, "#b02c22")}{_txt(0, 26, "4 ANDARES", 26, "#b02c22")}</g>'
    return dict(defs=DEFS, fundo=fundo, meio=deg, frente=corr, luz='')


def porta_801():
    fundo = f'''<rect x="-400" y="-500" width="2000" height="1320" fill="url(#hallP)"/><rect x="-400" y="786" width="2000" height="16" fill="#6a6e68" {ln(2)}/>{cenarios.piso_quadriculado(360)}
<g transform="translate(470 0)"><rect x="-130" y="230" width="260" height="570" fill="#6e4a30" {ln(3)}/><rect x="-114" y="246" width="228" height="554" fill="#ecdcb8" {ln(2.6)}/><rect x="-60" y="330" width="120" height="150" fill="#c8513a" {ln(2.2)}/><rect x="-40" y="262" width="80" height="40" rx="3" fill="#fbf6e6" {ln(2.2)}/>{_txt(0, 292, "801", 26, L)}</g>
<g transform="translate(470 830)"><path d="M-130 -14H130L150 20H-150z" fill="#8a6548" {ln(2.6)}/>{_txt(0, 12, "BEM-VINDO", 22, "#fbf0d4")}</g>
<g transform="translate(120 460)"><rect x="-50" y="-30" width="100" height="60" fill="#fbf6e6" {ln(2.2)}/>{_txt(0, 12, "8º", 34, L)}</g>'''
    return dict(defs=DEFS, fundo=fundo, meio='', frente='', luz='')


def chefe_fundo():
    raios = ''.join(f'<path d="M0 0L{-90} -1100H90z" fill="#ffb03a" opacity=".2" transform="rotate({a})"/>' for a in range(0, 360, 30))
    return dict(defs=DEFS, fundo=f'<rect x="-400" y="-500" width="2000" height="2300" fill="url(#chefeF)"/><g transform="translate(360 640)"><g data-vida="gira:14:0">{raios}</g></g>', meio='', frente='', luz='')


def _bolha(y, txt, ele, de):
    ls = textwrap.wrap(txt, 17)
    h = 34 + 50 * len(ls)
    w = 44 + max(len(l) for l in ls) * 21
    x = 556 - w if ele else 164
    c, tc = ('#2f9e62', '#fff') if ele else ('#e9edf0', '#20222a')
    t = ''.join(f'<text x="{x + 20}" y="{y + 54 + i * 50}" font-family="Arial" font-weight="700" font-size="38" fill="{tc}">{l}</text>' for i, l in enumerate(ls))
    return f'<g data-obj="{de}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="{c}"/>{t}</g>', h


def mao_zoom(tipo='punho', pele='#e9b98f', somb='#c98f68', item=''):
    m = personagens.maos(pele, somb)[tipo]
    return f'<g transform="scale(6.2)"><path d="M-3-7.4L-120-13V13L-3 7.4z" fill="{pele}" {ln(1.6)}/>{m[0]}{item}{m[1]}</g>'


def ins_celular(contato='Bia', retrato='bia', msgs=(), ele=False, horas='07:42'):
    y = 356
    bolhas = ''
    for i, (lado, t) in enumerate(msgs):
        b, h = _bolha(y, t, lado == 'ele', f'm{i}')
        bolhas += b
        y += h + 22
    r = f'<g transform="translate(206 282) scale(.46)">{personagens.retrato(retrato)}</g>' if retrato else ''
    fone = f'''<g data-vida="y:0:1:0"><rect x="122" y="176" width="476" height="1000" rx="56" fill="#16171d" {ln(5)}/><rect x="140" y="194" width="440" height="964" rx="40" fill="#f6f8f9"/><rect x="290" y="204" width="140" height="26" rx="13" fill="#16171d"/>
<rect x="140" y="236" width="440" height="88" fill="#fff"/><path d="M140 324H580" stroke="#d6dbdf" stroke-width="2"/><circle cx="206" cy="282" r="33" fill="#f4e6c8"/>{r}{_txt(252, 278, contato, 30, "#20222a", "start", "Arial")}{_txt(252, 306, "online", 20, "#2f9e62", "start", "Arial")}{_txt(528, 216, horas, 18, "#fff", "middle", "Arial")}
{bolhas}<rect x="164" y="1076" width="372" height="56" rx="28" fill="#fff" {ln(2)}/><g data-obj="digitando" display="none">{_txt(188, 1114, "claro", 28, "#20222a", "start", "Arial")}</g></g>'''
    fundo = '<rect x="-300" y="-300" width="1400" height="1900" fill="#6a7f7a"/><rect x="-300" y="-300" width="1400" height="1900" fill="#16171d" opacity=".32"/>'
    mao = f'<g transform="translate(600 1215) rotate(-112)">{mao_zoom("punho")}</g>'
    return dict(defs=DEFS, fundo=fundo, meio=fone, frente=mao, luz='')


def ins_conta(titulo='O ENCONTRO', sub='sábado, 7 da noite', linhas=None, total=None, tenho=None):
    """Caderno com uma conta. linhas = [[nome, valor]], até 4; total e tenho são textos prontos."""
    lin = ''.join(f'<path d="M112 {y}H620" stroke="#9fc0dc" stroke-width="2.4"/>' for y in range(350, 1120, 72))
    esp = ''.join(f'<ellipse cx="92" cy="{y}" rx="13" ry="7" fill="#c6cdd2" {ln(1.8)}/>' for y in range(290, 1160, 56))
    f = lambda s: f"font-family=\"'Comic Sans MS','Segoe Print',cursive\" font-weight=\"700\" font-size=\"{s}\" fill=\"#2a3a7a\""
    L_ = [(a, b, 486 + i * 72) for i, (a, b) in enumerate(linhas or [('Jantar', '120'), ('Camisa sem furo', '40'), ('Perfume', '30'), ('Carro ida e volta', '60')])][:4]
    total = total or 'R$ 250'
    tenho = tenho or 'R$ 11,40'
    tam = 54 if len(titulo) <= 13 else max(30, int(54 * 13 / len(titulo)))
    linhas = ''.join(f'<g data-obj="l{i}" display="none"><text x="150" y="{y}" {f(38)}>{a}</text><text x="600" y="{y}" text-anchor="end" {f(38)}>R$ {b}</text></g>' for i, (a, b, y) in enumerate(L_))
    pg = f'''<ellipse cx="376" cy="770" rx="360" ry="520" fill="#2a1c14" opacity=".3" filter="url(#b14)"/><g transform="rotate(-2 360 700)"><rect x="74" y="242" width="566" height="930" rx="10" fill="#fbf8ee" {ln(3)}/><path d="M138 242V1172" stroke="#e8b0b0" stroke-width="2.4"/>{lin}{esp}
<text x="370" y="332" text-anchor="middle" {f(tam)}>{titulo}</text><text x="370" y="412" text-anchor="middle" font-family="'Comic Sans MS',cursive" font-size="30" fill="#2a3a7a">{sub}</text>{linhas}
<g data-obj="l4" display="none"><path d="M150 722H604" stroke="#2a3a7a" stroke-width="5"/><text x="150" y="782" {f(46)}>TOTAL</text><text x="600" y="782" text-anchor="end" font-family="'Comic Sans MS',cursive" font-weight="700" font-size="46" fill="#b02c22">{total}</text></g>
<g data-obj="l5" display="none"><text x="150" y="870" {f(38)}>Tenho</text><text x="600" y="870" text-anchor="end" {f(38)}>{tenho}</text></g></g>'''
    return dict(defs=DEFS, fundo=cenarios._madeira(), meio=pg, frente='', luz='<rect x="-300" y="-200" width="1400" height="1900" fill="#ffe6a8" opacity=".2" style="mix-blend-mode:soft-light"/>')


def mao_escreve():
    """Mão com caneta; a origem é a ponta da caneta."""
    return f'<g transform="rotate(-128) translate(-210 -190)">{mao_zoom("punho", item=itens.caneta_mao())}</g>'


def ins_camisa():
    c = '#e9e2d2'
    cam = f'''<ellipse cx="370" cy="1000" rx="280" ry="24" fill="#2a1c14" opacity=".28" filter="url(#b9)"/><path d="M360 188C340 150 390 130 400 160" fill="none" {ln(6)}/><path d="M360 200L170 262L196 300H524L550 262z" fill="#b98347" {ln(4)}/>
<path d="M270 262L60 400L150 560L220 500V980H500V500L570 560L660 400L450 262C420 310 300 310 270 262z" fill="{c}" {ln(5)}/><path d="M270 262C300 330 420 330 450 262" fill="none" stroke="#c9c0ac" stroke-width="10"/><path d="M360 330V980" stroke="#c9c0ac" stroke-width="4"/>{''.join(f'<circle cx="360" cy="{y}" r="9" fill="#d6cdb8" {ln(2.4)}/>' for y in (400, 560, 720, 880))}
<g data-obj="furo"><path d="M300 610C312 586 346 590 354 612C362 636 332 654 310 644C296 638 294 622 300 610z" fill="#20222a" {ln(3)}/></g><g data-obj="azul" display="none"><path d="M292 606C306 576 352 582 362 610C372 642 332 664 304 650C286 642 284 622 292 606z" fill="#2f5fd8" {ln(3)}/><path d="M304 600l-14-16M352 596l16-16M360 640l18 12" stroke="#2f5fd8" stroke-width="5" stroke-linecap="round"/></g>'''
    return dict(defs=DEFS, fundo='<rect x="-300" y="-300" width="1400" height="1900" fill="#8a6548"/><path d="M360-300V1600" stroke="#6e4a30" stroke-width="10"/><rect x="-300" y="150" width="1400" height="12" fill="#c9c4b4" stroke="#241c22" stroke-width="3"/>', meio=cam, frente='', luz='')


def ins_bolso():
    n = lambda x, y, r, c, v: f'<g transform="translate({x} {y}) rotate({r}) scale(3.2)">{itens.nota(v, c)}</g>'
    return dict(defs=DEFS, fundo=cenarios._madeira(base='#3a4a68', veio='#2c3852'), meio=n(250, 520, -14, '#c98a3c', '10') + n(460, 600, 10, '#7fae6a', '5') + n(330, 760, 4, '#8f7fc0', '2') + n(520, 820, -8, '#8f7fc0', '1') , frente='', luz='')


NA_CABECA['melancia'] = f'<g transform="translate(330 376) rotate(-18) scale(1.1)"><path d="M-46 0A46 46 0 0 0 46 0z" fill="#2f8a4a" {ln(3)}/><path d="M-38 0A38 38 0 0 0 38 0z" fill="#f4f0d8"/><path d="M-33 0A33 33 0 0 0 33 0z" fill="#e8504a"/><path d="M-12 9l2 6M6 13l1 6M18 7l2 6" stroke="#241c22" stroke-width="4" stroke-linecap="round"/></g>'
NA_CABECA['capacete'] = f'<path d="M262 428C266 368 306 334 352 334C402 334 438 368 442 424C400 408 318 408 262 428z" fill="#f0c23a" {ln(3)}/><path d="M340 340V410M372 338V408" stroke="#241c22" stroke-width="3" opacity=".4"/>'


def caderno_mesa():
    return f'<ellipse cx="4" cy="6" rx="60" ry="9" fill="#2a1c14" opacity=".3"/><path d="M-52-9H46L58 8H-44z" fill="#fbf8ee" {ln(2.2)}/><path d="M-3-9L5 8" {ln(1.8)}/><path d="M-40-3h30M-36 2h30M12-3h30M14 2h30" stroke="#2a3a7a" stroke-width="1.8"/>'


def alca_termica():
    return f'<path d="M-30-200C-42-160-42-120-38-92" fill="none" stroke="{L}" stroke-width="11" stroke-linecap="round"/><path d="M-30-200C-42-160-42-120-38-92" fill="none" stroke="#e0502f" stroke-width="7" stroke-linecap="round"/>'


def mochila_termica():
    return f'<rect x="-104" y="-180" width="84" height="108" rx="8" fill="#e0502f" {ln(2.6)}/><rect x="-94" y="-170" width="64" height="30" rx="4" fill="#fbf0d4"/><text x="-62" y="-150" text-anchor="middle" font-family="Arial Black,Arial" font-size="13" fill="#b02c22">ZÉ</text>'


def assento(alt=175, largura=90, cor='#94694a'):
    """Assento neutro do tamanho certo para quem senta: a base fica no chão do ator."""
    return (f'<ellipse cy="5" rx="{largura * .7:.0f}" ry="8" fill="#140e18" opacity=".3" filter="url(#b3)"/><path d="M{-largura / 2} {-alt + 14}L{-largura / 2 + 8} 0H{-largura / 2 + 22}L{-largura / 2 + 22} {-alt + 14}zM{largura / 2} {-alt + 14}L{largura / 2 - 8} 0H{largura / 2 - 22}L{largura / 2 - 22} {-alt + 14}z" fill="#6e4a30" {ln(2.4)}/>'
            f'<rect x="{-largura / 2 - 6}" y="{-alt}" width="{largura + 12}" height="16" rx="5" fill="{cor}" {ln(2.6)}/>')


from . import lugares  # noqa: E402

cenarios.CENARIOS.update(composto=lugares.compor, detalhe=lugares.detalhe, neutro=neutro, quartinho=quartinho, padaria=padaria, rua_dia=rua_dia, feira=feira, hall=hall, escada=escada, porta_801=porta_801, chefe_fundo=chefe_fundo,
                         ins_celular=ins_celular, ins_conta=ins_conta, ins_camisa=ins_camisa, ins_bolso=ins_bolso)
