"""Interface: HUD só em cima (dias + juntado/meta), inventário, item novo, carimbo e legenda."""
from __future__ import annotations

from . import itens

FONTE = "'Arial Black',Arial"


def _caixa(w, h):
    return f'<rect width="{w}" height="{h}" rx="12" fill="#0b0d16" opacity=".95"/><rect x="1.5" y="1.5" width="{w - 3}" height="{h - 3}" rx="11" fill="none" stroke="#fff" stroke-opacity=".14" stroke-width="2"/>'


BAR_W = 396


def hud(ep=None):
    ep = ep or {}
    tx = ep.get('hud_txt', {})
    meta = ep.get('meta', 187.4)
    mtxt = f'META R$ {meta:.0f}' if float(meta).is_integer() else 'META R$ ' + f'{meta:.2f}'.replace('.', ',')
    if ep.get('valor_fmt') == 'num':
        mtxt = f"META {meta:.0f}{ep.get('valor_suf', '')}"
    selo = ep.get('selo_dia')
    pill = f'<g transform="translate(16 108)"><rect width="150" height="36" rx="18" fill="#ffd23f"/><text x="75" y="25" font-size="19" fill="#0b0d16">{selo}</text></g>' if selo else ''
    return f'''<g id="hudG" font-family="{FONTE}" text-anchor="middle">
<g transform="translate(16 16)">{_caixa(150, 84)}<text x="75" y="28" font-size="15" fill="#d7dbe6">{tx.get("dias", "DIAS")}</text><g transform="translate(75 66)"><text id="hDias" y="0" font-size="38" fill="#ffd23f">7</text></g></g>
<g transform="translate(176 16)">{_caixa(528, 84)}<text x="24" y="28" font-size="15" fill="#d7dbe6" text-anchor="start">{tx.get("valor", "JUNTADO")}</text><text id="hMeta" x="504" y="28" font-size="15" fill="#d7dbe6" text-anchor="end" data-t="{mtxt}">{mtxt}</text>
<text id="hVal" x="24" y="60" font-size="30" fill="#fff" text-anchor="start">R$ 0,00</text><text id="hPct" x="504" y="60" font-size="24" fill="#ffd23f" text-anchor="end">0%</text>
<rect x="24" y="69" width="{BAR_W + 84}" height="6" rx="3" fill="#fff" opacity=".14"/><rect id="hBar" x="24" y="69" width="0" height="6" rx="3" fill="#ffd23f"/></g>
<g id="inv"></g>{pill}</g>'''


def inventario(lista):
    """Quadradinhos permanentes, abaixo do placar."""
    s = ''
    for i, it in enumerate(lista):
        s += (f'<g data-i="{i}" display="none"><rect width="52" height="52" rx="9" fill="#3a3d4a" opacity=".95"/><rect x="1" y="1" width="50" height="50" rx="8" fill="none" stroke="#fff" stroke-opacity=".2" stroke-width="2"/>'
              f'<g transform="translate(26 26)">{itens.icone(it["icone"], 38)}</g>'
              f'<g class="x" display="none"><path d="M9 9L43 43M43 9L9 43" stroke="#ff4d43" stroke-width="7" stroke-linecap="round"/></g></g>')
    return s


def camadas_topo(icones, retratos=''):
    ic = ''.join(f'<g data-i="{k}" display="none" transform="translate(37 37)">{itens.icone(k, 52)}</g>' for k in icones)
    return f'''<g id="item" display="none" font-family="{FONTE}"><rect id="itemS" width="272" height="72" rx="12" fill="#0b0d16" opacity=".95"/><rect x="9" y="8" width="56" height="56" rx="8" fill="#fbfaf2"/><g id="itemI">{ic}</g>
<text id="itemT" x="78" y="28" font-size="13" fill="#ffd23f">NOVO ITEM</text><text id="itemN" x="78" y="56" font-size="22" fill="#fff"></text></g>
<g id="selo" display="none" font-family="{FONTE}" text-anchor="middle"><rect id="seloR" x="-128" y="-38" width="256" height="66" rx="8" fill="#b4231c"/><rect x="-122" y="-32" width="244" height="54" rx="5" fill="none" stroke="#fff" stroke-width="3"/><text id="seloT" y="6" font-size="30" fill="#fff"></text></g>
<g id="leg" font-family="{FONTE}" text-anchor="middle" style="paint-order:stroke" stroke="#0b0d16" stroke-width="13" stroke-linejoin="round"><text id="legT" x="0" y="0" font-size="64" style="paint-order:stroke"></text></g>
<g id="dlg" display="none" font-family="{FONTE}"><rect x="30" y="0" width="660" height="150" rx="14" fill="#0b0d16" opacity=".95" stroke="#ffd23f" stroke-width="3"/><rect x="46" y="16" width="118" height="118" rx="10" fill="#f4e6c8"/><g id="dlgR">{retratos}</g><text id="dlgN" x="182" y="46" font-size="22" fill="#ffd23f"></text><text id="dlgT0" x="182" y="86" font-size="26" fill="#fff"></text><text id="dlgT1" x="182" y="122" font-size="26" fill="#fff"></text></g>
<rect id="fade" width="720" height="1280" fill="#000" opacity="0" display="none"/>'''
