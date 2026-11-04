"""Cenários fixos. Cada função devolve camadas com o mesmo mundo em todos os planos, então a cozinha da cena 1
é a mesma da cena 3 e da 8: só muda a câmera e a luz.

Camadas: ceu (paralaxe forte), fundo (paralaxe leve), meio (atrás dos atores), frente (na frente dos atores), luz.
"""
from __future__ import annotations

import random

from . import itens
from .base import L, ln


def _txt(x, y, t, s, c, a='middle', w='Arial Black', extra=''):
    return f'<text x="{x}" y="{y}" font-family="\'{w}\',Arial" font-size="{s}" fill="{c}" text-anchor="{a}" {extra}>{t}</text>'


# ==================== COZINHA
def azulejos(x0, x1):
    s = ''
    for r in range(9):
        for c in range(int((x1 - x0) / 40) + 1):
            s += f'<rect x="{x0 + c * 40}" y="{470 + r * 38}" width="40" height="38" fill="{"#a9c7bd" if (r + c) % 2 else "#b7d3c9"}" stroke="#8fada3" stroke-width="1"/>'
    return s


def piso_quadriculado(cx, x0=-300, x1=1600):
    s = f'<rect x="{x0}" y="800" width="{x1 - x0}" height="1000" fill="#7b5d48"/>'
    rows = [800, 838, 884, 942, 1016, 1110, 1230, 1380, 1560, 1800]
    for r in range(len(rows) - 1):
        y0, y1 = rows[r], rows[r + 1]
        for c in range(-26, 27):
            X = lambda y, k: cx + (k * 62) * (.72 + (y - 800) / 330)
            col = '#c9b48f' if (r + c) % 2 else '#8d6a50'
            s += f'<path d="M{X(y0, c):.1f} {y0}L{X(y0, c + 1):.1f} {y0}L{X(y1, c + 1):.1f} {y1}L{X(y1, c):.1f} {y1}z" fill="{col}"/>'
    return s


DEFS_COZINHA = '''<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e5c98e"/><stop offset="1" stop-color="#d6b67a"/></linearGradient>
<linearGradient id="night" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#16214a"/><stop offset="1" stop-color="#3a3f73"/></linearGradient>
<linearGradient id="fr" x1="0" x2="1"><stop offset="0" stop-color="#f4f5f2"/><stop offset="1" stop-color="#cfd3d2"/></linearGradient>
<linearGradient id="cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff0c0" stop-opacity=".36"/><stop offset="1" stop-color="#fff0c0" stop-opacity="0"/></linearGradient>
<radialGradient id="darkN" gradientUnits="userSpaceOnUse" cx="645" cy="660" r="860"><stop offset=".26" stop-color="#141a3e" stop-opacity="0"/><stop offset=".6" stop-color="#141a3e" stop-opacity=".46"/><stop offset="1" stop-color="#0c1030" stop-opacity=".86"/></radialGradient>
<radialGradient id="warmN" gradientUnits="userSpaceOnUse" cx="645" cy="620" r="440"><stop offset="0" stop-color="#ffd89a" stop-opacity=".55"/><stop offset=".6" stop-color="#ffbe6e" stop-opacity=".14"/><stop offset="1" stop-color="#ffbe6e" stop-opacity="0"/></radialGradient>
<radialGradient id="darkM" gradientUnits="userSpaceOnUse" cx="190" cy="520" r="760"><stop offset=".18" stop-color="#20264e" stop-opacity=".12"/><stop offset=".5" stop-color="#141a3e" stop-opacity=".6"/><stop offset="1" stop-color="#0a0e2a" stop-opacity=".9"/></radialGradient>
<radialGradient id="warmM" gradientUnits="userSpaceOnUse" cx="150" cy="500" r="300"><stop offset="0" stop-color="#ffb066" stop-opacity=".6"/><stop offset="1" stop-color="#ffb066" stop-opacity="0"/></radialGradient>
<linearGradient id="corredor" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2c2430"/><stop offset="1" stop-color="#4c3a3a"/></linearGradient>'''


def _fogao():
    q = ''.join(f'<circle cx="{78 + i * 26}" cy="612" r="9" fill="#d9d6cc" {ln(2)}/><path d="M{78 + i * 26} 605v7" {ln(2)}/>' for i in range(5))
    return f'''<ellipse cx="130" cy="806" rx="112" ry="8" fill="#2c2230" opacity=".3"/>
<rect x="40" y="552" width="180" height="12" rx="3" fill="#3b3a40" {ln(2.6)}/><rect x="44" y="564" width="172" height="240" fill="#ecebe4" {ln(2.8)}/>
<rect x="44" y="564" width="172" height="62" fill="#dedcd2" {ln(2.4)}/>{q}
<rect x="62" y="644" width="136" height="108" rx="8" fill="#3a3a40" {ln(2.6)}/><rect x="74" y="656" width="112" height="84" rx="4" fill="#20202a"/><path d="M84 662l28 0-22 70h-16z" fill="#fff" opacity=".1"/><rect x="72" y="634" width="116" height="9" rx="4.5" fill="#bfbdb4" {ln(2)}/>
<rect x="44" y="764" width="172" height="40" fill="#cfcdc4" {ln(2.4)}/>
<path d="M60 548h60M140 548h60" stroke="#17171c" stroke-width="7" stroke-linecap="round"/>'''


def _panela_estavel():
    return f'''<g><path d="M-58-6C-58 8-52 12-44 12H44C52 12 58 8 58-6V-46H-58z" fill="#9aa3a8" {ln(2.6)}/><ellipse cy="-46" rx="58" ry="12" fill="#5c5f66" {ln(2.6)}/><ellipse cy="-44" rx="50" ry="9" fill="#5a3220"/><path d="M-46-34V4" stroke="#d6dde0" stroke-width="7" stroke-linecap="round" opacity=".8"/><path d="M58-36h44" stroke="{L}" stroke-width="13" stroke-linecap="round"/><path d="M58-36h44" stroke="#4a3b35" stroke-width="8" stroke-linecap="round"/></g>'''


def _panela_frente():
    """Parede da frente da panela: a colher mergulha por trás dela."""
    return f'''<g transform="translate(160 540) scale(.76)"><path d="M-58-46C-58-30 58-30 58-46V-6C58 8 52 12 44 12H-44C-52 12-58 8-58-6z" fill="#9aa3a8" {ln(2.6)}/><path d="M-46-30V4" stroke="#d6dde0" stroke-width="7" stroke-linecap="round" opacity=".8"/></g>'''


def _balcao():
    return f'''<rect x="214" y="552" width="262" height="14" fill="#d8d2c2" {ln(2.8)}/><rect x="220" y="566" width="250" height="236" fill="#7c9a86" {ln(2.8)}/><path d="M300 566V802M390 566V802" {ln(2.6)}/><circle cx="288" cy="680" r="4" fill="{L}"/><circle cx="312" cy="680" r="4" fill="{L}"/><circle cx="378" cy="680" r="4" fill="{L}"/><circle cx="402" cy="680" r="4" fill="{L}"/>
<rect x="340" y="540" width="116" height="14" rx="4" fill="#9fa8ac" {ln(2.4)}/><path d="M396 540V516C396 500 420 500 420 516V522" fill="none" stroke="{L}" stroke-width="7"/><path d="M396 540V516C396 500 420 500 420 516V522" fill="none" stroke="#c0c6c9" stroke-width="3.6"/>
<g data-vida="brilho:.2:.9:1.2"><path d="M420 526v8" stroke="#bfe0f2" stroke-width="3" stroke-linecap="round"/></g>'''


def _janela_noite(dx):
    return f'''<g transform="translate({dx} 0)"><rect x="38" y="210" width="176" height="212" fill="url(#night)" {ln(4)}/>
<circle cx="164" cy="256" r="16" fill="#f2eccb"/><path d="M38 362L72 338V300h26v22l26-18v26l34-28v22l56-34v112H38z" fill="#101636"/>
<g fill="#f7cf6a"><rect x="78" y="350" width="9" height="11"/><rect x="104" y="362" width="9" height="11"/><rect x="138" y="346" width="9" height="11" data-vida="pisca:-.4:.5:0:.25"/><rect x="178" y="356" width="9" height="11"/></g>
<path d="M126 210V422M38 316H214" {ln(4)}/><rect x="28" y="420" width="196" height="16" fill="#f1e6c9" {ln(3)}/>
<path d="M30 200H222" stroke="#6e4a2f" stroke-width="8" stroke-linecap="round"/><g data-vida="rot:.5:.8:0:30:200"><path d="M34 204C60 260 44 340 50 410H22V204z" fill="#c8603f" {ln(2.6)}/></g><g data-vida="rot:.5:.9:1:222:200"><path d="M218 204C196 256 208 330 202 396L236 400V204z" fill="#c8603f" {ln(2.6)}/></g><path d="M28 240c6 50 2 110 4 160M226 240c-6 50-2 100-2 150" stroke="#9c4630" stroke-width="3" fill="none"/></g>'''


def _geladeira():
    return f'''<g transform="translate(300 0)"><ellipse cx="634" cy="812" rx="108" ry="12" fill="#2c2230" opacity=".35"/>
<path d="M534 226L548 208V810L534 800z" fill="#9aa1a4" {ln(3)}/><path d="M548 220Q548 206 562 206H708Q722 206 722 220V810H548z" fill="url(#fr)" {ln(3.4)}/><path d="M580 216L620 216L570 390H552z" fill="#fff" opacity=".35"/><path d="M548 392H722" {ln(3.4)}/><rect x="564" y="300" width="10" height="72" rx="5" fill="#8e9599" {ln(2.4)}/><rect x="564" y="414" width="10" height="120" rx="5" fill="#8e9599" {ln(2.4)}/>
<path d="M604 248h80v72h-80z" fill="#fff0a0" transform="rotate(3 644 284)" {ln(2.4)}/><text x="644" y="278" transform="rotate(3 644 284)" font-family="Arial" font-weight="700" font-size="13" text-anchor="middle" fill="#b02c22">PAGAR</text><text x="644" y="302" transform="rotate(3 644 284)" font-family="Arial Black" font-size="19" text-anchor="middle" fill="#b02c22">LUZ!</text><circle cx="644" cy="252" r="7" fill="#d84a3a" {ln(2)}/>
<rect x="598" y="430" width="62" height="78" fill="#fbfaf2" transform="rotate(-5 628 470)" {ln(2.2)}/><path d="M608 450h42M608 466h42M608 482h26" stroke="#9aa0a8" stroke-width="3" transform="rotate(-5 628 470)"/><circle cx="628" cy="434" r="6" fill="#3f8fd8" {ln(2)}/><circle cx="686" cy="460" r="12" fill="#f0c23a" {ln(2.2)}/></g>'''


def _porta():
    return f'''<rect x="1050" y="222" width="172" height="590" fill="#caa877" {ln(3)}/><rect x="1064" y="236" width="144" height="572" fill="url(#corredor)" {ln(2.8)}/>
<path d="M1064 808L1090 760H1182L1208 808z" fill="#5c4640" opacity=".8"/><rect x="1100" y="290" width="76" height="110" fill="#3a3238" {ln(2)}/><path d="M1138 290v110" {ln(2)}/>
'''


def _folha_porta():
    return f'''<path d="M1140 236H1208V808H1140z" fill="#b08a5c" {ln(2.8)}/><path d="M1140 236L1128 244V816L1140 808z" fill="#8f6e46" {ln(2.4)}/><rect x="1152" y="262" width="44" height="210" fill="#a57f52" {ln(2)}/><rect x="1152" y="510" width="44" height="270" fill="#a57f52" {ln(2)}/><circle cx="1148" cy="520" r="6" fill="#e0b23c" {ln(2)}/>'''


def _mesa_frente(extra=''):
    """A mesa aprovada: mesma madeira, mesmas sombras; objetos deitados, virados para quem senta."""
    dx = 285
    return f'''<g transform="translate({dx} -36)"><path d="M150 900L136 1180H160L194 900zM570 900L584 1180H560L526 900z" fill="#6e4a30" {ln(3.4)}/><ellipse cx="360" cy="1188" rx="280" ry="24" fill="#22161e" opacity=".3" filter="url(#b6)"/>
<path d="M126 806H594L632 880H88z" fill="#c79560" {ln(3.4)}/><path d="M88 880H632V906H88z" fill="#8f6440" {ln(3.4)}/><path d="M88 906H632V922H88z" fill="#1d1218" opacity=".32" filter="url(#b6)"/><path d="M126 806H594L606 830H114z" fill="#fff" opacity=".1"/>
<path d="M200 820L170 876M300 816L290 876M430 816L446 876M530 816L566 876" stroke="#ad7f4e" stroke-width="2.4"/><ellipse cx="350" cy="838" rx="190" ry="30" fill="#ffe3a8" opacity=".32" filter="url(#b14)"/></g>
<g transform="translate(508 788) scale(.74)"><ellipse cx="10" cy="40" rx="42" ry="9" fill="#34302e" opacity=".42" filter="url(#b3)"/><path d="M-27-6V38C-22 48 22 48 27 38V-6z" fill="#e8e4da" {ln(3)}/><path d="M27 6c20-2 20 26 0 24" fill="none" {ln(5)}/><ellipse cy="-6" rx="27" ry="8" fill="#5a3722" {ln(3)}/><path d="M-20 4V34" stroke="#fff" stroke-width="6" stroke-linecap="round" opacity=".7"/><path d="M12 2V36C14 40 18 40 24 36V-2z" fill="#bcb7ab" opacity=".6"/></g>
{extra}'''


def cozinha(luz='noite', mesa='contas', lampada=True, conta='R$ 187,40'):
    wall = f'''<rect x="-400" y="-500" width="2100" height="1300" fill="url(#wall)"/>{azulejos(-40, 1360)}<rect x="-400" y="462" width="2100" height="10" fill="#efe4c4" {ln(2)}/>
<rect x="-400" y="785" width="2100" height="16" fill="#8a6a4e" {ln(2)}/>{piso_quadriculado(645)}'''
    prat = f'''<g transform="translate(300 0)"><rect x="424" y="262" width="118" height="10" fill="#8a6a4e" {ln(2.6)}/><rect x="430" y="232" width="110" height="34" fill="#2c1a22" opacity=".14" filter="url(#b6)" transform="translate(-8 4)"/><rect x="436" y="226" width="30" height="36" rx="3" fill="#d9a24a" {ln()}/><rect x="474" y="212" width="26" height="50" rx="3" fill="#7fae8a" {ln()}/><path d="M508 262c0-26 6-36 12-36s12 10 12 36z" fill="#c9603f" {ln()}/>
<circle cx="480" cy="170" r="30" fill="#f7f1e0" {ln(4)}/><g data-vida="rot:2:6:0:480:170"><path d="M480 170V146" {ln(3)}/></g><path d="M480 170L494 178" {ln(4)}/><circle cx="480" cy="170" r="3" fill="{L}"/></g>'''
    utens = f'''<rect x="60" y="440" width="150" height="8" fill="#8a6a4e" {ln(2.4)}/><path d="M86 448v34M120 448v42M154 448v30" {ln(2.2)}/><ellipse cx="86" cy="490" rx="11" ry="13" fill="#b98347" {ln(2.2)}/><rect x="110" y="488" width="20" height="26" rx="4" fill="#9aa3a8" {ln(2.2)}/><path d="M144 478h20l-3 26h-14z" fill="#c9603f" {ln(2.2)}/>
<g transform="translate(286 416) rotate(-2)"><rect x="-40" y="-56" width="80" height="108" fill="#fbf6e6" {ln(2.2)}/><rect x="-14" y="-62" width="28" height="12" fill="#e8d98a" opacity=".9"/>{_txt(0, -34, "RECEITA", 11, "#7a3b24")}<path d="M-30-22h60M-30-10h60M-30 2h44" stroke="#b3a68a" stroke-width="2.4"/>{_txt(0, 26, "MEXER ATÉ", 9.5, "#b02c22")}{_txt(0, 38, "O PONTO", 9.5, "#b02c22")}</g>'''
    fundo = wall + prat + _janela_noite(300) + utens + _geladeira() + _porta() + _balcao() + _fogao()
    lamp = (f'<path d="M645 -520V292" {ln(3)}/><path d="M596 348C602 310 622 292 645 292C668 292 688 310 694 348z" fill="#c8603f" {ln(3)}/><ellipse cx="645" cy="348" rx="49" ry="9" fill="#ffefb8" {ln(2.4)}/>')
    cadeira = f'''<path d="M516 800H500L494 1050H516zM774 800H792L796 1050H776z" fill="#80583c" {ln(3)}/><rect x="494" y="762" width="302" height="30" rx="8" fill="#94694a" {ln(3)}/>'''
    meio = cadeira
    if luz == 'noite':
        cone = '<g data-vida="brilho:.86:1:7.3"><path d="M600 350L330 1000H980L690 350z" fill="url(#cone)"/></g>' if lampada else ''
        lz = '<rect x="-400" y="-500" width="2100" height="2300" fill="url(#darkN)" style="mix-blend-mode:multiply"/><rect x="-400" y="-500" width="2100" height="2300" fill="url(#warmN)" style="mix-blend-mode:soft-light"/>'
        frente = _panela_frente() + _folha_porta() + _mesa_frente(_itens_mesa(mesa, conta)) + lamp + cone
    else:
        lz = '<rect x="-400" y="-500" width="2100" height="2300" fill="url(#darkM)" style="mix-blend-mode:multiply"/><rect x="-400" y="-500" width="2100" height="2300" fill="url(#warmM)" style="mix-blend-mode:soft-light"/>'
        frente = _panela_frente() + _folha_porta() + _mesa_frente(_itens_mesa(mesa, conta)) + lamp
        fundo += f'''<g><rect x="222" y="520" width="50" height="34" rx="3" fill="#8a4a2c" {ln(2.2)}/><ellipse cx="247" cy="520" rx="25" ry="6" fill="#e8d4b8" {ln(2)}/>{_txt(247, 544, "CHOCO", 9, "#fff")}<rect x="284" y="524" width="40" height="30" rx="3" fill="#2f6fa8" {ln(2.2)}/><ellipse cx="304" cy="524" rx="20" ry="5" fill="#d6dde0" {ln(2)}/>{_txt(304, 544, "LEITE", 8, "#fff")}</g>'''
    panela = f'<g transform="translate(160 540) scale(.76)">{_panela_estavel()}</g>'
    return dict(defs=DEFS_COZINHA, fundo=fundo, meio=meio + _fogao_chama() + panela, frente=frente, luz=lz)


def _fogao_chama():
    return f'''<g class="chama" data-obj="chama" display="none"><g transform="translate(32 0)"><g data-vida="y:1.6:17:0"><path d="M96 548c-6-10 6-16 4-24c10 8 12 18 6 24zM122 548c-6-12 6-18 4-28c12 10 14 22 6 28zM148 548c-6-10 6-16 4-24c10 8 12 18 6 24z" fill="#4aa0f2" {ln(1.4, "#2f6fb8")}/><path d="M104 548c-3-5 3-8 2-12c5 4 6 9 3 12zM130 548c-3-6 3-9 2-14c6 5 7 11 3 14zM156 548c-3-5 3-8 2-12c5 4 6 9 3 12z" fill="#f2d84a"/></g></g></g>'''


def _itens_mesa(mesa, conta='R$ 187,40'):
    if mesa == 'contas':
        return f'''<g transform="translate(640 812)">{itens.conta_mesa(conta)}</g><g transform="translate(748 806)"><ellipse cx="4" cy="6" rx="52" ry="12" fill="#2a1c14" opacity=".28"/><path d="M-46-8H40L48 12H-40z" fill="#3a6a8a" {ln(2.2)}/><path d="M-6-8L-3 12" stroke="#fff" stroke-width="2"/></g>
{itens.pilha(4, 10, 556, 806)}{itens.pilha(2, 9, 590, 824)}{itens.pilha(1, 9, 716, 826)}{itens.pilha(3, 10, 690, 808)}'''
    if mesa == 'envelope':
        return f'''<g transform="translate(748 806)"><ellipse cx="4" cy="6" rx="52" ry="12" fill="#2a1c14" opacity=".28"/><path d="M-46-8H40L48 12H-40z" fill="#3a6a8a" {ln(2.2)}/><path d="M-6-8L-3 12" stroke="#fff" stroke-width="2"/></g>
<g data-obj="conta_paga"><g transform="translate(556 814)">{itens.conta_mesa(conta)}</g></g>'''
    return ''


# ==================== QUARTO
DEFS_QUARTO = '''<linearGradient id="qWall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7f9bb0"/><stop offset="1" stop-color="#6f8a9f"/></linearGradient>
<radialGradient id="qDark" gradientUnits="userSpaceOnUse" cx="680" cy="620" r="760"><stop offset=".2" stop-color="#141a3e" stop-opacity="0"/><stop offset=".55" stop-color="#141a3e" stop-opacity=".46"/><stop offset="1" stop-color="#0c1030" stop-opacity=".86"/></radialGradient>
<radialGradient id="qWarm" gradientUnits="userSpaceOnUse" cx="690" cy="640" r="340"><stop offset="0" stop-color="#ffdc9e" stop-opacity=".65"/><stop offset="1" stop-color="#ffbe6e" stop-opacity="0"/></radialGradient>
<linearGradient id="qDia" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffb46a" stop-opacity=".34"/><stop offset="1" stop-color="#3a3f73" stop-opacity=".3"/></linearGradient>
<linearGradient id="tarde" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e88a5a"/><stop offset="1" stop-color="#f5c98a"/></linearGradient>'''


def _piso_tabua(cx, cor='#8a6548', cor2='#7a573d', y0=800):
    s = f'<rect x="-400" y="{y0}" width="1900" height="1000" fill="{cor}"/>'
    for k in range(-16, 17):
        s += f'<path d="M{cx + k * 44} {y0}L{cx + k * 130} 1500" stroke="{cor2}" stroke-width="3"/>'
    for i, (y, x) in enumerate([(836, 120), (850, 520), (884, 250), (910, 640), (960, 90), (1000, 420), (1080, 700), (1150, 200)]):
        s += f'<path d="M{x} {y}h{70 + i * 8}" stroke="{cor2}" stroke-width="2.4"/>'
    return s


def quarto(hora='noite'):
    janela = 'url(#night)' if hora == 'noite' else 'url(#tarde)'
    lua = f'<circle cx="238" cy="282" r="20" fill="#f2eccb"/>' if hora == 'noite' else f'<circle cx="238" cy="392" r="30" fill="#ffe2a0"/>'
    predio = f'<path d="M90 420V360h40v-30h44v40h46v-20h60v70z" fill="{"#101636" if hora == "noite" else "#a8583c"}"/>'
    fundo = f'''<rect x="-400" y="-500" width="1900" height="1320" fill="url(#qWall)"/><rect x="-400" y="600" width="1900" height="200" fill="#5f7a8e"/><rect x="-400" y="596" width="1900" height="8" fill="#a9bccb"/>
<rect x="-400" y="786" width="1900" height="16" fill="#54402f" {ln(2)}/>{_piso_tabua(420)}
<path d="M58 120l14 26-8 24 20 30" fill="none" stroke="#5a7386" stroke-width="2.4"/><path d="M780 90l-16 30 10 20" fill="none" stroke="#5a7386" stroke-width="2.4"/>
<rect x="90" y="220" width="200" height="200" fill="{janela}" {ln(4)}/>{lua}{predio}<path d="M190 220V420M90 320H290" {ln(4)}/><rect x="78" y="418" width="224" height="14" fill="#d6dde0" {ln(2.8)}/>
<path d="M82 210H298" stroke="#54402f" stroke-width="7" stroke-linecap="round"/><g data-vida="rot:.5:.8:0:80:210"><path d="M84 214C110 270 92 340 100 400H72V214z" fill="#3f6a8a" {ln(2.4)}/></g><g data-vida="rot:.5:.9:1:300:210"><path d="M296 214C270 270 288 340 280 396L312 400V214z" fill="#3f6a8a" {ln(2.4)}/></g>
<g transform="translate(472 150) rotate(-2)"><rect width="130" height="176" fill="#f3efe0" {ln(2.6)}/><rect x="10" y="10" width="110" height="112" fill="#2f8a5a"/><path d="M28 34L44 22 58 26H72L86 22 102 34 92 50H84V100H46V50H38z" fill="#f0c23a" {ln(2)}/>{_txt(65, 80, "10", 26, "#2f3f6a")}{_txt(65, 152, "CRAQUE", 20, "#2f3f6a")}</g>
<g transform="translate(690 120)"><path d="M-6 0h12v8h-12z" fill="#d84a3a"/><rect x="-46" y="4" width="92" height="74" fill="#fbf6e6" {ln(2.2)}/>{_txt(0, 26, "PROVA", 11, "#2f3f6a")}{_txt(0, 44, "SEXTA", 14, "#b02c22")}<path d="M-34 56h68M-34 66h44" stroke="#b3a68a" stroke-width="2.4"/></g>
<rect x="478" y="400" width="260" height="12" fill="#8a6a4e" {ln(2.6)}/><path d="M500 412l8 24M716 412l-8 24" {ln(3)}/><path d="M486 396l250 2" stroke="#2c1a22" stroke-width="10" opacity=".14" filter="url(#b3)"/>
<rect x="498" y="344" width="16" height="56" fill="#c8513a" {ln(2.2)}/><rect x="516" y="350" width="14" height="50" fill="#3f83a6" {ln(2.2)}/><rect x="532" y="340" width="18" height="60" fill="#f0c23a" {ln(2.2)}/><rect x="552" y="352" width="13" height="48" fill="#6b9a6a" {ln(2.2)}/>
<g transform="translate(676 400)"><path d="M-14 0h28l-6-10h-16z" fill="#6e4a30" {ln(2)}/><path d="M-5-10v-14h10v14z" fill="#d8a93a" {ln(2)}/><path d="M-16-48h32c0 16-8 26-16 26s-16-10-16-26z" fill="#e8c24a" {ln(2.2)}/><path d="M-16-44c-10 0-10 12 2 14M16-44c10 0 10 12-2 14" fill="none" {ln(2)}/></g>'''
    bola_est = f'<g data-obj="bola_prat" transform="translate(612 352)">{itens.bola(44)}</g>'
    cama = f'''<ellipse cx="225" cy="872" rx="220" ry="14" fill="#140e18" opacity=".35" filter="url(#b6)"/>
<rect x="24" y="560" width="26" height="310" rx="4" fill="#7a5238" {ln(2.8)}/><rect x="412" y="670" width="20" height="200" rx="4" fill="#7a5238" {ln(2.8)}/>
<path d="M40 690H424V830H40z" fill="#6a4a34" {ln(2.8)}/><path d="M38 668C40 650 56 644 72 644H402C422 644 430 660 430 676V770C430 790 414 796 396 796H52C42 796 38 786 38 770z" fill="#c8513a" {ln(2.8)}/>
<path d="M140 648V796M260 648V796M360 648V796" stroke="#a33f2c" stroke-width="18"/><path d="M38 720C160 738 300 738 430 720" fill="none" stroke="#a33f2c" stroke-width="3"/>
<path d="M56 650C50 616 66 600 98 600H176C208 600 216 620 208 650z" fill="#f1ece0" {ln(2.6)}/><path d="M84 612C110 606 150 606 186 612" fill="none" stroke="#d3cdbd" stroke-width="3"/>'''
    mesa_q = f'''<path d="M488 668L478 924H500L516 668zM846 668L858 924H836L822 668z" fill="#6e4a30" {ln(3)}/><path d="M820 668H512V760H820z" fill="#5e4029" {ln(2.6)}/><rect x="540" y="690" width="256" height="58" fill="#7a5238" {ln(2.4)}/><rect x="640" y="710" width="56" height="8" rx="4" fill="#d8b24a" {ln(1.8)}/>
<path d="M470 640H866L858 668H478z" fill="#a9784c" {ln(3)}/><path d="M470 640H866L862 650H474z" fill="#fff" opacity=".12"/>'''
    mesa_q = f'<g transform="translate(0 50)">{mesa_q}</g>'
    sobre = f'''<g transform="translate(796 690)"><ellipse cx="0" cy="-2" rx="44" ry="7" fill="#2a1c14" opacity=".35"/><path d="M-34 0h68l-8-10h-52z" fill="#3a3f4c" {ln(2.4)}/><path d="M0-10L-30-92" stroke="{L}" stroke-width="8" stroke-linecap="round"/><path d="M0-10L-30-92" stroke="#6a7080" stroke-width="4" stroke-linecap="round"/><path d="M-30-92L-54-136" stroke="{L}" stroke-width="8" stroke-linecap="round"/><path d="M-30-92L-54-136" stroke="#6a7080" stroke-width="4"/><path d="M-96-108C-90-138-68-150-48-146C-34-142-28-128-34-110z" fill="#2f6fa8" {ln(2.4)}/><ellipse cx="-66" cy="-110" rx="32" ry="8" fill="#ffefb8" {ln(2)} transform="rotate(10 -66 -110)"/></g>
 <g transform="translate(690 678)"><path d="M-74 10L-62-10H64L72 10z" fill="#fbf6e6" {ln(2.2)}/><path d="M0-10L1 10" {ln(2)}/><path d="M-58-4h48M-60 3h50M12-4h44M12 3h46" stroke="#b6c4d4" stroke-width="1.6"/></g>
<g transform="translate(600 686) scale(.8)"><rect x="-34" y="-10" width="68" height="10" fill="#c8513a" {ln(2)}/><rect x="-30" y="-20" width="60" height="10" fill="#3f83a6" {ln(2)}/><rect x="-32" y="-29" width="64" height="9" fill="#f0c23a" {ln(2)}/></g>'''
    cadeira = f'''<path d="M446 800H426L416 950H438zM628 800H648L654 950H632z" fill="#80583c" {ln(3)}/><path d="M426 590H454L458 800H434z" fill="#94694a" {ln(3)}/><rect x="422" y="790" width="240" height="24" rx="6" fill="#94694a" {ln(3)}/>'''
    if hora == 'noite':
        lz = '<rect x="-400" y="-500" width="1900" height="2300" fill="url(#qDark)" style="mix-blend-mode:multiply"/><rect x="-400" y="-500" width="1900" height="2300" fill="url(#qWarm)" style="mix-blend-mode:soft-light"/>'
        cone = f'<g data-vida="brilho:.9:1:6"><path d="M700 580L560 710H860L760 580z" fill="#fff0c0" opacity=".2"/></g>'
    else:
        lz = '<rect x="-400" y="-500" width="1900" height="2300" fill="url(#qDia)" style="mix-blend-mode:multiply"/>'
        cone = ''
    mochila = f'<g transform="translate(360 960) scale(.9)">{itens.mochila_chao()}</g>'
    return dict(defs=DEFS_QUARTO, fundo=fundo + bola_est + cama, meio=cadeira, frente=mesa_q + sobre + cone + mochila, luz=lz)


# ==================== RUA / ESCOLA / OBRA: base comum
DEFS_RUA = '''<linearGradient id="ceuTarde" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6fb4dc"/><stop offset="1" stop-color="#f8dfae"/></linearGradient>
<linearGradient id="ceuSol" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4fa8e2"/><stop offset="1" stop-color="#d6eef2"/></linearGradient>
<linearGradient id="ceuChuva" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#4a5468"/><stop offset="1" stop-color="#8d98a6"/></linearGradient>
<linearGradient id="ceuPoente" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a5a94"/><stop offset=".6" stop-color="#e88a5a"/><stop offset="1" stop-color="#f8cf8a"/></linearGradient>
<radialGradient id="solG"><stop offset="0" stop-color="#fff6c4" stop-opacity=".95"/><stop offset=".35" stop-color="#ffe680" stop-opacity=".5"/><stop offset="1" stop-color="#ffe680" stop-opacity="0"/></radialGradient>
<linearGradient id="asf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#55565f"/><stop offset="1" stop-color="#3f4048"/></linearGradient>
<linearGradient id="asfM" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3c4250"/><stop offset="1" stop-color="#262a35"/></linearGradient>
<radialGradient id="tSol" gradientUnits="userSpaceOnUse" cx="110" cy="240" r="900"><stop offset="0" stop-color="#ffd27a" stop-opacity=".4"/><stop offset="1" stop-color="#ff9a5a" stop-opacity=".06"/></radialGradient>
<linearGradient id="tChuva" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f3a58" stop-opacity=".62"/><stop offset="1" stop-color="#1c2438" stop-opacity=".68"/></linearGradient>
<radialGradient id="tPoente" gradientUnits="userSpaceOnUse" cx="120" cy="560" r="980"><stop offset="0" stop-color="#ffb46a" stop-opacity=".22"/><stop offset="1" stop-color="#5a3f8a" stop-opacity=".42"/></radialGradient>'''


def _nuvem(x, y, s=1, c='#ffffff', o=.9):
    return f'<g transform="translate({x} {y}) scale({s})" opacity="{o}"><path d="M-70 20C-92 20-96-6-72-10C-74-34-40-42-26-24C-14-52 34-46 36-16C62-20 76 18 48 20z" fill="{c}"/></g>'


def _arvore(x, y, s=1, o='#3f8a55', o2='#2f6f44'):
    return f'''<g transform="translate({x} {y}) scale({s})"><ellipse cy="6" rx="86" ry="11" fill="#140e18" opacity=".3" filter="url(#b6)"/><path d="M-13 0C-9-60-11-110-19-160L19-160C11-110 9-60 15 0z" fill="#6e4a30" {ln(2.8)}/>
<g data-vida="rot:.8:1.1:0:0:-160"><path d="M-104-200C-132-260-84-320-40-310C-30-372 54-372 66-314C112-326 142-262 110-204C128-160 66-130 32-154C2-126-56-130-66-160C-88-156-104-176-104-200z" fill="{o}" {ln(2.8)}/><path d="M-66-222C-52-260-20-280 16-276M34-200C52-214 74-218 88-212" fill="none" stroke="{o2}" stroke-width="7" stroke-linecap="round"/></g></g>'''


def _carro(x, y, s=1, c='#c8513a', c2='#a33f2c', vira=1):
    return f'''<g transform="translate({x} {y}) scale({s * vira} {s})"><ellipse cy="4" rx="178" ry="14" fill="#101016" opacity=".4" filter="url(#b6)"/>
<path d="M-168-34C-170-60-150-74-118-78L-74-128C-66-136-50-140-34-140H52C70-140 86-132 96-122L132-82C160-78 174-66 172-36C172-20 160-14 148-14H-152C-162-14-168-22-168-34z" fill="{c}" {ln(3)}/>
<path d="M-62-122H-8V-82H-98zM4-122H50C62-122 74-116 82-108L104-82H4z" fill="#c7dde6" {ln(2.6)}/><path d="M-50-118L-74-86H-52L-30-118zM18-118L0-86H14L34-118z" fill="#fff" opacity=".5"/>
<path d="M-168-44H172" stroke="{c2}" stroke-width="5"/><path d="M-2-82V-18" {ln(2.4)}/><rect x="10" y="-68" width="22" height="6" rx="3" fill="{L}"/><rect x="-168" y="-44" width="20" height="12" rx="3" fill="#f7e8a6" {ln(2)}/><rect x="152" y="-46" width="20" height="12" rx="3" fill="#d8403a" {ln(2)}/>
<circle cx="-108" cy="-14" r="30" fill="#1d1d22" {ln(3)}/><circle cx="-108" cy="-14" r="13" fill="#b8bcc4" {ln(2)}/><circle cx="108" cy="-14" r="30" fill="#1d1d22" {ln(3)}/><circle cx="108" cy="-14" r="13" fill="#b8bcc4" {ln(2)}/></g>'''


def _calcada_rua(ym=840, yg=1000, yr=1016, chuva=False):
    """Calçada de cimento, meio-fio com espessura e asfalto."""
    p = '#b9b3a4' if not chuva else '#6e7482'
    p2 = '#9f9a8c' if not chuva else '#575d6b'
    s = f'<rect x="-500" y="{ym}" width="2400" height="{yg - ym}" fill="{p}"/>'
    for k in range(-12, 26):
        s += f'<path d="M{k * 100} {ym}L{k * 118 - 40} {yg}" stroke="{p2}" stroke-width="2.4"/>'
    s += f'<path d="M-500 {ym + 60}H1900" stroke="{p2}" stroke-width="2"/>'
    s += f'<rect x="-500" y="{yg}" width="2400" height="{yr - yg}" fill="{"#d8d3c4" if not chuva else "#878d99"}" {ln(2.4)}/>'
    s += f'<rect x="-500" y="{yr}" width="2400" height="900" fill="url(#{"asfM" if chuva else "asf"})"/><rect x="-500" y="{yr}" width="2400" height="10" fill="#101014" opacity=".4"/>'
    for k in range(-6, 16):
        s += f'<rect x="{k * 220}" y="{yr + 190}" width="120" height="10" fill="#e8e4d6" opacity=".75"/>'
    return s


def escola():
    ceu = f'''<rect x="-500" y="-500" width="2400" height="1500" fill="url(#ceuTarde)"/><circle cx="130" cy="240" r="170" fill="url(#solG)"/><circle cx="130" cy="240" r="46" fill="#fff0b8"/>
<g data-vida="anda:5:0:1200"><g transform="translate(-300 0)">{_nuvem(100, 130, 1.1)}{_nuvem(520, 80, .8)}{_nuvem(860, 190, 1)}</g></g>'''
    grades = ''.join(f'<path d="M{x} 612V840" stroke="{L}" stroke-width="5"/><path d="M{x} 612V840" stroke="#3a6a8a" stroke-width="3"/>' for x in range(208, 420, 21))
    fundo = f'''<path d="M-300 836V470H-40V400H560V470H1400V836z" fill="#eadcb8" {ln(3)}/><path d="M-300 700H1400V836H-300z" fill="#3f83a6" {ln(2.6)}/><path d="M-60 400L250 318 560 400z" fill="#b4553f" {ln(3)}/>
{''.join(f'<rect x="{x}" y="470" width="72" height="92" fill="#a9d2e2" {ln(2.6)}/><path d="M{x + 36} 470v92M{x} 516h72" {ln(2.2)}/><path d="M{x + 6} 476l24 0-20 80h-4z" fill="#fff" opacity=".4"/>' for x in (-20, 80, 470, 570, 690, 810, 930, 1050, 1170))}
<rect x="30" y="414" width="440" height="50" rx="4" fill="#2f6a8a" {ln(2.6)}/>{_txt(250, 448, "ESCOLA MUNICIPAL", 30, "#fbf6e6")}
<rect x="180" y="580" width="260" height="256" fill="#2d2a36" {ln(3)}/><rect x="190" y="592" width="240" height="244" fill="#4c4556"/><path d="M190 836L250 700H372L430 836z" fill="#8a8488"/><rect x="266" y="622" width="88" height="118" fill="#6e6470" {ln(2.2)}/><path d="M310 622v118" {ln(2)}/>
<path d="M186 840V608H208" fill="none" {ln(4)}/>'''
    meio = f'''<g transform="translate(1110 840)"><rect x="-90" y="-214" width="180" height="214" fill="#f3efe0" opacity="0"/></g>{_arvore(760, 846, 1.2)}
<g transform="translate(170 840)"><rect x="-9" y="-254" width="18" height="254" fill="#6a7080" {ln(2.6)}/><rect x="-13" y="-262" width="26" height="10" fill="#585e6c" {ln(2.4)}/></g><g transform="translate(450 840)"><rect x="-9" y="-254" width="18" height="254" fill="#6a7080" {ln(2.6)}/><rect x="-13" y="-262" width="26" height="10" fill="#585e6c" {ln(2.4)}/></g>
<g transform="translate(40 0)"><g fill="none">{''.join(f'<path d="M{x} 622V840" stroke="{L}" stroke-width="6"/><path d="M{x} 622V840" stroke="#3a6a8a" stroke-width="3.6"/>' for x in range(-100, 120, 22))}</g><rect x="-110" y="612" width="236" height="12" fill="#3a6a8a" {ln(2.4)}/></g>'''
    chao = _calcada_rua(838, 1030, 1048)
    frente = f'{_carro(830, 1262, 1.2, "#2f6fa8", "#255a8a", 1)}'
    lz = '<rect x="-500" y="-500" width="2400" height="2500" fill="url(#tSol)" style="mix-blend-mode:soft-light"/>'
    return dict(defs=DEFS_RUA, ceu=ceu, fundo=fundo + chao, meio=meio, frente=frente, luz=lz)


def obra():
    ceu = f'''<rect x="-500" y="-500" width="2400" height="1500" fill="url(#ceuSol)"/>
<g transform="translate(590 250)"><circle r="220" fill="url(#solG)"/><g data-vida="rot:6:.6:0:0:0">{''.join(f'<path d="M0-74L9-120L-9-120z" fill="#ffe680" transform="rotate({a})"/>' for a in range(0, 360, 30))}</g><circle r="56" fill="#fff0a0" {ln(2.4, "#f0c23a")}/></g>
<g data-vida="anda:3:0:1200"><g transform="translate(-300 0)">{_nuvem(300, 120, .8)}{_nuvem(800, 200, .6)}</g></g>'''
    laje = lambda y: f'<rect x="-120" y="{y}" width="640" height="26" fill="#b0aca0" {ln(2.8)}/>'
    pilar = lambda x, y: f'<rect x="{x}" y="{y}" width="30" height="124" fill="#a39f92" {ln(2.6)}/>'
    tij = ''
    for y in range(696, 830, 18):
        for i in range(-6, 16):
            tij += f'<rect x="{i * 44 + (22 if (y // 18) % 2 else 0) - 120}" y="{y}" width="44" height="18" fill="{"#c26a44" if (i + y) % 3 else "#b45c3a"}" stroke="#8e4a30" stroke-width="1.6"/>'
    esc = ''
    for x in (530, 626):
        esc += f'<path d="M{x} 180V830" stroke="{L}" stroke-width="9"/><path d="M{x} 180V830" stroke="#b8bcc4" stroke-width="5"/>'
    for y in (320, 470, 620):
        esc += f'<rect x="510" y="{y}" width="140" height="12" fill="#b98347" {ln(2.2)}/>'
    esc += f'<path d="M530 332L626 470M626 480L530 620" stroke="{L}" stroke-width="7"/><path d="M530 332L626 470M626 480L530 620" stroke="#b8bcc4" stroke-width="3.6"/>'
    fundo = f'''{laje(180)}{laje(330)}{laje(480)}{pilar(-60, 206)}{pilar(120, 206)}{pilar(300, 206)}{pilar(470, 206)}{pilar(-60, 356)}{pilar(120, 356)}{pilar(300, 356)}{pilar(470, 356)}{pilar(-60, 506)}{pilar(120, 506)}{pilar(300, 506)}{pilar(470, 506)}
<rect x="-110" y="206" width="600" height="124" fill="#2b2d38" opacity=".55"/><rect x="-110" y="356" width="600" height="124" fill="#2b2d38" opacity=".55"/><rect x="-110" y="506" width="600" height="190" fill="#2b2d38" opacity=".55"/>{tij}<path d="M-120 696H530" {ln(2.6)}/>
<path d="M260 180V100M240 120H280" {ln(3)}/><g transform="translate(-40 150)">{''.join(f'<path d="M{x} 30V-40" stroke="#7a3f2a" stroke-width="5"/>' for x in (0, 22, 44, 66))}</g>
{esc}<g data-vida="x:5:.7:0"><g><path d="M660 196H900V640H660z" fill="#2f8a6a" opacity=".82" {ln(2.4)}/><path d="M700 196V640M750 196V640M800 196V640M850 196V640" stroke="#1f6f52" stroke-width="3"/></g></g>
<rect x="940" y="500" width="170" height="330" fill="#d8d3c4" {ln(2.6)}/><path d="M940 500H1400V830H940z" fill="#c9c4b4" {ln(2.6)}/>
<rect x="-500" y="830" width="2400" height="900" fill="#a98a5e"/>
<g fill="#8f7248">{''.join(f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * .3:.1f}"/>' for x, y, r in [(70, 880, 40), (320, 910, 26), (560, 860, 34), (830, 930, 48), (150, 1010, 60), (640, 1040, 54), (980, 1000, 42), (370, 1150, 70), (800, 1190, 80), (60, 1220, 60)])}</g>
<rect x="-500" y="826" width="2400" height="10" fill="#6e5a3e" opacity=".5"/>'''
    placa = f'''<g transform="translate(888 846)"><rect x="-6" y="-170" width="12" height="172" fill="#6e4a30" {ln(2.4)}/><g transform="translate(0 -200)"><rect x="-92" y="-52" width="184" height="104" rx="4" fill="#f0c23a" {ln(2.8)}/>{_txt(0, -14, "OBRA", 34, L)}{_txt(0, 24, "USE CAPACETE", 18, L)}</g></g>'''
    bet = f'''<g transform="translate(140 874)"><ellipse cy="6" rx="118" ry="12" fill="#140e18" opacity=".32" filter="url(#b6)"/><path d="M-82 0L-52-70H52L82 0" fill="none" stroke="{L}" stroke-width="9"/><path d="M-82 0L-52-70H52L82 0" fill="none" stroke="#c8513a" stroke-width="5"/><circle cx="-82" cy="-6" r="19" fill="#1d1d22" {ln(2.6)}/><circle cx="82" cy="-6" r="19" fill="#1d1d22" {ln(2.6)}/>
<g transform="rotate(-24 0 -96)"><path d="M-48-146H48L72-102C74-66 54-44 0-44C-54-44-74-66-72-102z" fill="#d8703a" {ln(3)}/><path d="M-70-104H70" stroke="{L}" stroke-width="3.4"/><ellipse cy="-146" rx="48" ry="11" fill="#3a3238" {ln(2.8)}/></g></g>'''
    tijolos = lambda x, y, c=5, h=4: f'<g transform="translate({x} {y})"><ellipse cx="{c * 22}" cy="4" rx="{c * 26}" ry="9" fill="#140e18" opacity=".32" filter="url(#b3)"/>' + ''.join(f'<rect x="{i * 44 + (r % 2) * 11}" y="{-20 - r * 20}" width="44" height="20" fill="{"#c26a44" if (i + r) % 2 else "#b45c3a"}" {ln(2)}/>' for r in range(h) for i in range(c - (r % 2))) + '</g>'
    meio = f'''{placa}<g transform="translate(-20 0)">{bet}</g><g transform="translate(590 880)"><ellipse cy="8" rx="130" ry="13" fill="#140e18" opacity=".3" filter="url(#b6)"/><path d="M-120 0C-90-70-50-104 0-104C50-104 90-70 120 0z" fill="#c8a868" {ln(2.8)}/><path d="M-60-40C-30-70 20-80 50-60M-20 -20C10-34 50-32 72-20" fill="none" stroke="#a98a4e" stroke-width="3"/></g>'''
    bancos = tijolos(250, 992, 5, 3)
    lz = '<rect x="-500" y="-500" width="2400" height="2500" fill="#ffe2a0" opacity=".16" style="mix-blend-mode:soft-light"/>'
    return dict(defs=DEFS_RUA, ceu=ceu, fundo=fundo, meio=meio + bancos, frente='', luz=lz)


def _casa(x, w, cor, cor2, porta=True, num='', jan=True):
    s = f'<g transform="translate({x} 0)"><rect y="470" width="{w}" height="370" fill="{cor}" {ln(3)}/><path d="M-10 470L{w * .5} 380L{w + 10} 470z" fill="{cor2}" {ln(3)}/>'
    if jan:
        s += f'<rect x="{w * .12:.0f}" y="540" width="92" height="96" fill="#9fc0cc" {ln(2.8)}/><path d="M{w * .12 + 46:.0f} 540v96M{w * .12:.0f} 588h92" {ln(2.2)}/>'
    if porta:
        s += f'<rect x="{w * .62:.0f}" y="600" width="84" height="240" fill="#6e4a30" {ln(2.8)}/><circle cx="{w * .62 + 70:.0f}" cy="720" r="4" fill="#e0b23c"/>'
        if num:
            s += f'<rect x="{w * .62 + 20:.0f}" y="572" width="44" height="22" rx="2" fill="#fbf6e6" {ln(2)}/>' + _txt(w * .62 + 42, 590, num, 16, L)
    return s + '</g>'


def _chuva():
    return ('<g data-vida="cai:640:0:180"><rect x="-500" y="-700" width="2400" height="2800" fill="url(#chuva1)"/></g>'
            '<g data-vida="cai:430:0:130:40"><rect x="-500" y="-700" width="2400" height="2800" fill="url(#chuva2)"/></g>')


def rua(clima='chuva'):
    chuva = clima == 'chuva'
    gr = 'ceuChuva' if chuva else 'ceuPoente'
    nuvens = ''.join(_nuvem(x, y, s, '#3e4556' if chuva else '#f4a878', .95 if chuva else .7) for x, y, s in [(-100, 120, 1.6), (240, 80, 2), (640, 150, 1.7), (1000, 100, 2), (1300, 170, 1.5)])
    sol = '' if chuva else f'<circle cx="120" cy="420" r="210" fill="url(#solG)"/><circle cx="120" cy="420" r="52" fill="#ffe2a0"/>'
    ceu = f'<rect x="-500" y="-500" width="2400" height="1500" fill="url(#{gr})"/>{sol}<g data-vida="anda:2:0:400">{nuvens}</g>'
    casas = (_casa(-290, 300, '#d9a24a', '#8a4a2c') + _casa(30, 330, '#7fae8a', '#a33f2c', num='47') + _casa(380, 260, '#c97f6a', '#6e4a30', porta=False) + _casa(660, 320, '#8fb3cf', '#8a4a2c') + _casa(1000, 300, '#e0c98e', '#a33f2c'))
    muro = f'''<rect x="30" y="760" width="196" height="80" fill="#c9c4b4" {ln(2.6)}/><g fill="none">{''.join(f'<path d="M{x} 700V840" stroke="{L}" stroke-width="5"/>' for x in range(236, 360, 19))}</g><rect x="228" y="696" width="130" height="10" fill="#3a3f4c" {ln(2)}/><rect x="228" y="760" width="130" height="8" fill="#3a3f4c" {ln(2)}/>'''
    poste = f'''<g transform="translate(560 842)"><rect x="-7" y="-610" width="14" height="610" fill="#6a7080" {ln(2.6)}/><path d="M0-606C20-640 70-640 90-616" fill="none" stroke="{L}" stroke-width="8"/><path d="M0-606C20-640 70-640 90-616" fill="none" stroke="#6a7080" stroke-width="4"/><path d="M72-616H112L104-600H80z" fill="#3a3f4c" {ln(2.4)}/>{f'<ellipse cx="92" cy="-598" rx="20" ry="6" fill="#ffe2a0" data-vida="brilho:.7:1:9"/>' if not chuva else ''}</g>'''
    fios = f'<path d="M-400 290C0 340 300 310 560 236C800 300 1100 320 1600 280" fill="none" {ln(2.2)}/>'
    chao = _calcada_rua(838, 1002, 1020, chuva)
    extra = ''
    if chuva:
        extra = ''.join(f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * .16:.1f}" fill="#7f90a8" opacity=".5"/><ellipse cx="{x - 8}" cy="{y - 1}" rx="{r * .5:.1f}" ry="{r * .06:.1f}" fill="#d6e4f2" opacity=".5"/>' for x, y, r in [(150, 1092, 80), (520, 1140, 120), (840, 1070, 70), (300, 1230, 150), (760, 1280, 130), (430, 930, 60), (760, 960, 50)])
        extra += '<rect x="-500" y="1022" width="2400" height="26" fill="#a9c0d6" opacity=".25"/>'
    fundo = casas + muro + fios + chao + extra
    meio = poste
    frente = _carro(1000, 1270, 1.4, '#7a4a7a' if not chuva else '#5a4a6a', '#5f3a5f', -1)
    if chuva:
        frente += _chuva()
    if chuva:
        lz = '<rect x="-500" y="-500" width="2400" height="2500" fill="url(#tChuva)" style="mix-blend-mode:multiply"/>'
    else:
        lz = '<rect x="-500" y="-500" width="2400" height="2500" fill="url(#tPoente)" style="mix-blend-mode:multiply"/>'
    return dict(defs=DEFS_RUA, ceu=ceu, fundo=fundo, meio=meio, frente=frente, luz=lz)


# ==================== INSERTOS (planos fechados de objeto)
def _madeira(y0=-200, base='#a9784c', veio='#8d6238'):
    s = f'<rect x="-300" y="{y0}" width="1400" height="1900" fill="{base}"/>'
    random.seed(4)
    for i in range(30):
        y = y0 + i * 64
        s += f'<path d="M-300 {y}C100 {y + random.randint(-14, 14)} 500 {y + random.randint(-14, 14)} 1100 {y}" fill="none" stroke="{veio}" stroke-width="3"/>'
    return s


def ins_caderno():
    linhas = ''.join(f'<path d="M116 {y}H626" stroke="#9fc0dc" stroke-width="2.4"/>' for y in range(350, 1120, 72))
    esp = ''.join(f'<ellipse cx="96" cy="{y}" rx="13" ry="7" fill="#c6cdd2" {ln(1.8)}/>' for y in range(290, 1160, 56))
    pg = f'''<ellipse cx="376" cy="770" rx="360" ry="520" fill="#2a1c14" opacity=".3" filter="url(#b14)"/><g transform="rotate(-2 360 700)"><rect x="82" y="248" width="566" height="930" rx="10" fill="#d9d4c6" {ln(3)}/><rect x="78" y="242" width="566" height="930" rx="10" fill="#fbf8ee" {ln(3)}/><path d="M146 242V1172" stroke="#e8b0b0" stroke-width="2.4"/>{linhas}{esp}'''
    pap = lambda s: f"font-family=\"'Comic Sans MS','Segoe Print',cursive\" font-weight=\"700\" font-size=\"{s}\" fill=\"#2a3a7a\""
    pg += f'''<text x="370" y="332" text-anchor="middle" {pap(66)}>PLANO</text><path d="M260 348H480" stroke="#2a3a7a" stroke-width="4" stroke-linecap="round"/>
<g data-obj="l1"><text x="164" y="486" {pap(40)}>1. pedir emprestado</text></g>
<g data-obj="l2"><text x="164" y="630" {pap(40)}>2. ganhar na loteria</text></g>
<g data-obj="l3"><text x="164" y="774" {pap(40)}>3. vender brigadeiro</text></g>
<path data-risco="r1" pathLength="1" d="M156 472C280 462 430 476 594 462" fill="none" stroke="#c0392b" stroke-width="7" stroke-linecap="round"/>
<path data-risco="r2" pathLength="1" d="M156 616C280 606 430 620 594 606" fill="none" stroke="#c0392b" stroke-width="7" stroke-linecap="round"/>
<path data-risco="r3" pathLength="1" d="M580 740C540 696 240 692 158 738C110 772 150 806 300 812C460 816 610 806 596 760C592 744 570 728 540 722" fill="none" stroke="#2f9e62" stroke-width="7" stroke-linecap="round"/></g>'''
    return dict(fundo=_madeira() , frente='', meio=pg, luz='<rect x="-300" y="-200" width="1400" height="1900" fill="#ffd89a" opacity=".2" style="mix-blend-mode:soft-light"/>')


def mao_close(pele, somb):
    """Mão grande, vinda de baixo: uma silhueta só do pulso ao dedo, para planos fechados."""
    return f'''<path d="M-92 560C-84 300-70 170-64 90C-64 40-58 0-34-16L-40-88C-42-104-18-110-12-92L0-34L6-112C8-130 34-130 34-110L34-34L58-96C64-114 88-104 82-88L60-14C66 0 76 8 92-6L126-40C138-52 156-34 144-20L96 56C70 104 64 200 72 560z" fill="{pele}" {ln(5)}/>
<path d="M-48 110C-8 130 28 130 56 100" fill="none" stroke="{somb}" stroke-width="5" stroke-linecap="round"/><path d="M-30 30C0 60 30 50 52 20" fill="none" stroke="{somb}" stroke-width="5" stroke-linecap="round"/>'''


def ins_palma():
    sk, sd = '#c9915f', '#a87346'
    h = f'''<g transform="translate(372 760) rotate(-6) scale(1.5)"><path d="M-110 540C-96 300-92 220-96 120C-100 60-120 30-132-10C-140-34-108-48-96-26L-70 26C-66-20-66-70-70-110C-72-136-36-142-30-112L-20-30L-8-126C-6-152 30-150 30-122L26-30L50-108C58-132 90-120 84-96L62-8L92-62C106-84 134-66 122-44L78 60C62 100 70 200 88 540z" fill="{sk}" {ln(4)}/>
<path d="M-74 72C-30 40 30 44 62 72M-66 122C-30 92 24 88 58 110" fill="none" stroke="{sd}" stroke-width="5" stroke-linecap="round"/><path d="M-60 180C-20 200 30 196 66 170" fill="none" stroke="{sd}" stroke-width="4" stroke-linecap="round"/></g>'''
    moedas = f'''<g transform="translate(290 800) scale(1.6)">{itens.moeda(30)}</g><g transform="translate(420 770) scale(1.4)">{itens.moeda(26)}</g><g transform="translate(360 858) scale(1.2)">{itens.moeda(24, "#b8bcc4", "#e6e8ec")}</g><g transform="translate(470 866) scale(1.25)">{itens.botao(24)}</g>'''
    fundo = f'<rect x="-300" y="-300" width="1400" height="1900" fill="#2a2333"/><rect x="-300" y="-300" width="760" height="1900" fill="#3a2f33"/><path d="M460-300V1600" stroke="#caa877" stroke-width="40" filter="url(#b9)"/>'
    return dict(fundo=fundo, meio=h + f'<g data-obj="palma_m">{moedas}</g>', frente='', luz='<rect x="-300" y="-300" width="1400" height="1900" fill="#ffd89a" opacity=".14" style="mix-blend-mode:soft-light"/>')


def ins_panela():
    fundo = f'''<rect x="-300" y="-300" width="1400" height="1900" fill="#23232c"/><ellipse cx="360" cy="1100" rx="420" ry="150" fill="#3a3a40"/><ellipse cx="360" cy="1060" rx="340" ry="110" fill="#17171c"/>
<g data-vida="y:5:15:0"><path d="M120 1060c-20-50 30-70 16-120c50 40 56 90 30 120zM250 1080c-24-60 34-80 20-150c56 50 66 110 34 150zM400 1090c-20-60 34-80 20-150c56 50 66 110 34 150zM540 1060c-20-50 26-66 16-110c46 36 50 80 26 110z" fill="#4aa0f2" stroke="#2f6fb8" stroke-width="3"/><path d="M144 1060c-10-26 14-36 8-60c24 20 26 44 14 60zM276 1080c-12-30 16-40 10-70c28 24 30 52 16 70zM426 1090c-12-30 16-40 10-70c28 24 30 52 16 70zM560 1060c-10-26 12-34 8-54c22 18 24 40 12 54z" fill="#f2d84a"/></g>'''
    pan = f'''<path d="M60 560V960C60 1050 200 1080 360 1080C520 1080 660 1050 660 960V560z" fill="#9aa3a8" {ln(5)}/><path d="M110 640V990" stroke="#d6dde0" stroke-width="24" stroke-linecap="round" opacity=".8"/><path d="M570 620V1000C600 990 640 980 660 960V600z" fill="#6f777c"/>
<ellipse cx="360" cy="560" rx="300" ry="96" fill="#5c5f66" {ln(5)}/><ellipse cx="360" cy="572" rx="264" ry="76" fill="#3a3a40"/>'''
    massa = f'''<ellipse cx="360" cy="590" rx="256" ry="66" fill="#6e3f22"/><ellipse cx="320" cy="572" rx="130" ry="26" fill="#8a5630" opacity=".8"/><g data-vida="x:8:2.4:0"><path d="M150 590C210 560 300 620 380 580C440 560 520 600 566 586" fill="none" stroke="#4e2a16" stroke-width="10" stroke-linecap="round"/></g>'''
    preto = f'''<ellipse cx="360" cy="590" rx="256" ry="66" fill="#17110f"/><path d="M180 582l40 18 34-22 40 26 40-16 36 20 44-24 44 14" fill="none" stroke="#3a2c26" stroke-width="7"/>'''
    return dict(fundo=fundo, meio=pan, frente=f'<g data-obj="massa">{massa}</g><g data-obj="preto" opacity="0">{preto}</g>' + _chamas_close(), luz='<rect x="-300" y="-300" width="1400" height="1900" fill="#2a2f5a" opacity=".3" style="mix-blend-mode:multiply"/>')


def ins_receita():
    fundo = f'<g transform="translate(0 0)"><rect x="-300" y="-300" width="1400" height="1900" fill="#a9c7bd"/>'
    for r in range(-4, 16):
        for c in range(-3, 12):
            fundo += f'<rect x="{c * 120}" y="{r * 114}" width="120" height="114" fill="{"#a9c7bd" if (r + c) % 2 else "#b7d3c9"}" stroke="#8fada3" stroke-width="2"/>'
    fundo += '</g>'
    papel = f'''<g transform="rotate(-2 360 640)"><rect x="96" y="250" width="540" height="800" fill="#2a1c14" opacity=".28" filter="url(#b9)" transform="translate(10 12)"/><rect x="90" y="240" width="540" height="800" fill="#fbf6e6" {ln(3.5)}/><rect x="284" y="216" width="150" height="50" fill="#e8d98a" opacity=".9"/>
{_txt(360, 330, "BRIGADEIRO", 44, "#7a3b24")}<path d="M150 400H570M150 460H570M150 520H470" stroke="#b3a68a" stroke-width="5"/>
{_txt(360, 640, "Modo de fazer:", 34, "#7a3b24", w="Arial")}
<rect x="118" y="686" width="484" height="120" rx="8" fill="#ffe680" opacity=".85"/>{_txt(360, 766, "MEXER ATÉ O PONTO", 42, "#b02c22")}
<path d="M150 880H570M150 940H400" stroke="#b3a68a" stroke-width="5"/></g>'''
    return dict(fundo=fundo, meio=papel, frente='', luz='<rect x="-300" y="-300" width="1400" height="1900" fill="#20264e" opacity=".16" style="mix-blend-mode:multiply"/>')


def ins_fiado():
    pg = f'''<ellipse cx="376" cy="700" rx="340" ry="420" fill="#2a1c14" opacity=".3" filter="url(#b14)"/><g transform="rotate(3 360 640)"><rect x="110" y="260" width="500" height="780" rx="8" fill="#fbf8ee" {ln(3.5)}/>{''.join(f'<path d="M140 {y}H580" stroke="#9fc0dc" stroke-width="2.4"/>' for y in range(350, 1020, 62))}
<text x="360" y="330" text-anchor="middle" font-family="'Comic Sans MS',cursive" font-weight="700" font-size="46" fill="#2a3a7a">VENDAS — dia 1</text>
<text x="150" y="470" font-family="'Comic Sans MS',cursive" font-weight="700" font-size="40" fill="#2a3a7a">1 brigadeiro</text><text x="150" y="532" font-family="'Comic Sans MS',cursive" font-weight="700" font-size="40" fill="#2a3a7a">Prof. Marta</text><text x="570" y="470" text-anchor="end" font-family="'Comic Sans MS',cursive" font-weight="700" font-size="40" fill="#2a3a7a">R$ 2,00</text></g>'''
    return dict(fundo=_madeira(base='#c9a06c', veio='#ab8250'), meio=pg, frente='', luz='<rect x="-300" y="-200" width="1400" height="1900" fill="#ffd27a" opacity=".24" style="mix-blend-mode:soft-light"/>')


def ins_caixa():
    fundo = f'''<rect x="-300" y="-300" width="1400" height="1000" fill="#5a6474"/><rect x="-300" y="620" width="1400" height="1200" fill="#3c4250"/><path d="M-300 620H1100" stroke="#262a35" stroke-width="8"/>
<ellipse cx="360" cy="1090" rx="430" ry="70" fill="#7f90a8" opacity=".5"/>'''
    cx = f'''<ellipse cx="360" cy="1076" rx="330" ry="46" fill="#101016" opacity=".45" filter="url(#b9)"/><path d="M70 620H650L606 1060H114z" fill="#ecece6" {ln(5)}/><path d="M120 720H250M150 860H330M430 700H600M470 920H590" stroke="#cfd2cc" stroke-width="8"/><path d="M4 340H716L650 620H70z" fill="#fbfbf6" {ln(5)}/>
<path d="M48 364H672L622 600H98z" fill="#5a3a2a"/><path d="M70 420H650L620 590H100z" fill="#6e4a30"/><ellipse cx="300" cy="470" rx="170" ry="32" fill="#8e6a50" opacity=".8"/><g data-vida="x:6:2:0"><path d="M120 500C200 466 300 526 380 480S540 520 610 486" fill="none" stroke="#4e2f1e" stroke-width="9" stroke-linecap="round"/></g><g data-vida="x:5:1.6:1"><path d="M140 560C220 530 320 576 400 546S540 570 590 548" fill="none" stroke="#4e2f1e" stroke-width="7" stroke-linecap="round"/></g>
<g transform="translate(230 500) scale(3.4)">{_forminha()}</g><g transform="translate(470 530) scale(3.4)">{_forminha()}</g><g transform="translate(380 440) scale(2.8)">{_forminha()}</g>'''
    return dict(fundo=fundo, meio=cx, frente=_chuva(), luz='<rect x="-300" y="-300" width="1400" height="1900" fill="#2f3a58" opacity=".5" style="mix-blend-mode:multiply"/>')


def mao_lapis():
    sk, sd = '#c9915f', '#a87346'
    return f'''<path d="M84 16C150 110 300 320 470 620L1100 1700L760 1900L330 760C250 560 120 320 44 92z" fill="{sk}" {ln(5)}/>
<path d="M4-4L104-258L128-248L28 8L2 16z" fill="#e8b73a" {ln(4)}/><path d="M4-4L28 8L2 16z" fill="#ecd8b4" {ln(3)}/><path d="M104-258L114-282L138-272L128-248z" fill="#d8707a" {ln(4)}/>
<path d="M30-96C60-120 120-112 150-74C176-34 160 40 110 66C70 84 30 66 20 30C10-6 10-60 30-96z" fill="{sk}" {ln(5)}/>
<path d="M36-74C60-96 92-90 96-70C98-56 76-52 56-56C42-58 34-66 36-74zM26-28C50-52 96-46 100-26C102-12 76-8 54-12C38-14 24-20 26-28zM26 16C46-8 92-6 98 14C100 28 74 32 52 28C36 26 24 24 26 16z" fill="{sk}" {ln(4)}/>'''


def banquinho():
    return f'''<ellipse cy="6" rx="66" ry="9" fill="#140e18" opacity=".35" filter="url(#b3)"/><path d="M-44-40L-52 0H-38L-30-40zM44-40L52 0H38L30-40z" fill="#6e4a30" {ln(2.6)}/><rect x="-56" y="-50" width="112" height="14" rx="4" fill="#94694a" {ln(2.6)}/>'''


def _forminha():
    return f'<path d="M-14-2L-10 10H10L14-2z" fill="#c8513a" {ln(1.6)} transform="rotate(14)"/>'


def placa_sopa():
    return f'''<g><rect x="-6" y="0" width="12" height="150" fill="#b98347" {ln(2.4)}/><path d="M-190-190H192L184 8H-184z" fill="#f6efd8" {ln(3)}/>{_txt(0, -146, "PROMOÇÃO:", 36, "#c0392b")}{_txt(0, -96, "BRIGADEIRO", 40, "#3a2c28")}{_txt(0, -24, "SOPA", 62, "#2f6fa8")}</g>'''


def _chamas_close():
    return f'''<g transform="translate(0 44)"><g data-vida="y:5:15:0"><path d="M120 1060c-20-50 30-70 16-120c50 40 56 90 30 120zM250 1080c-24-60 34-80 20-150c56 50 66 110 34 150zM400 1090c-20-60 34-80 20-150c56 50 66 110 34 150zM540 1060c-20-50 26-66 16-110c46 36 50 80 26 110z" fill="#4aa0f2" stroke="#2f6fb8" stroke-width="3"/><path d="M144 1060c-10-26 14-36 8-60c24 20 26 44 14 60zM276 1080c-12-30 16-40 10-70c28 24 30 52 16 70zM426 1090c-12-30 16-40 10-70c28 24 30 52 16 70zM560 1060c-10-26 12-34 8-54c22 18 24 40 12 54z" fill="#f2d84a"/></g></g>'''


CENARIOS = dict(cozinha=cozinha, quarto=quarto, escola=escola, obra=obra, rua=rua, ins_caderno=ins_caderno, ins_palma=ins_palma,
                ins_panela=ins_panela, ins_receita=ins_receita, ins_fiado=ins_fiado, ins_caixa=ins_caixa)


def desfocado(tipo):
    """Objetos do primeiro plano, em coordenadas de tela."""
    if tipo == 'planta':
        return f'<g filter="url(#b6)"><path d="M-30 1280V1020C20 1000 60 1040 66 1110C100 1090 130 1130 120 1180C160 1180 170 1240 150 1280z" fill="#2f6b4a" {ln(3)}/><path d="M20 1280L30 1090M70 1280L90 1150M-4 1280V1040" stroke="#1f4d35" stroke-width="7" fill="none"/></g>'
    if tipo == 'cadeira':
        return f'<g filter="url(#b9)"><path d="M520 1280L560 960H640L650 1280z" fill="#5a3f2c"/><rect x="520" y="930" width="240" height="40" rx="10" fill="#6e4a30"/></g>'
    if tipo == 'cortina':
        return '<g filter="url(#b9)"><path d="M-30-20H90C60 300 90 700 60 1300H-30z" fill="#1d2440"/></g>'
    if tipo == 'tijolos':
        return f'<g filter="url(#b6)"><g transform="translate(-40 1180)">' + ''.join(f'<rect x="{i * 92 + (r % 2) * 36}" y="{r * 44}" width="92" height="44" fill="{"#a85a3a" if (i + r) % 2 else "#94502f"}" stroke="#2a1c14" stroke-width="3"/>' for r in range(3) for i in range(4)) + '</g></g>'
    if tipo == 'galho':
        return f'<g filter="url(#b6)"><path d="M760 90C640 120 560 170 500 250" fill="none" stroke="#3a2c20" stroke-width="16"/><path d="M640 140C600 100 560 110 540 130C570 160 620 170 640 140zM560 200C510 180 480 200 470 230C510 240 550 240 560 200zM720 120C700 180 720 210 740 220C770 190 760 140 720 120z" fill="#2f6b4a"/></g>'
    if tipo == 'gota':
        return ''.join(f'<ellipse cx="{x}" cy="{y}" rx="{r}" ry="{r * 1.4:.1f}" fill="#dceaf6" opacity=".22" filter="url(#b3)"/>' for x, y, r in [(70, 300, 16), (640, 240, 22), (610, 900, 18), (110, 1040, 26), (680, 560, 12), (40, 700, 14)])
    return ''
