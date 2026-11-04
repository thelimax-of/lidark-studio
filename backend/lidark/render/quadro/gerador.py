"""Recebe o JSON do episódio e devolve o MP4.

    python -m lidark.render.quadro.gerador EP.json SAIDA.mp4 --tmp PASTA [--quadros 1.2,3.4] [--so-html]

Uma só instância do navegador; os quadros vão direto para o x264.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from . import animacao, cenarios, cenarios2, itens, personagens, poses, som, ui
from .base import DEFS

FPS = 30
AMARELO, AZUL = '#ffd23f', '#5ec8ff'


def _mp3_dur(ff, p):
    r = subprocess.run([ff, '-hide_banner', '-i', str(p)], capture_output=True, text=True, encoding='utf-8', errors='ignore').stderr
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def narracao(ep, tmp, ff):
    """Sintetiza cada fala (com cache por texto) e mede a duração real."""
    from lidark import tts
    v = ep.get('voz', {})
    falas = []
    for c, cena in enumerate(ep['cenas']):
        for k, f in enumerate(cena.get('falas', [])):
            nome = hashlib.md5((f['texto'] + v.get('voice', '') + v.get('rate', '')).encode()).hexdigest()[:12]  # nome curto: caminho longo quebra no Windows
            o = tmp / f'voz_{nome}.mp3'
            jw = o.with_suffix('.json')
            if not o.exists() or o.stat().st_size < 500 or not jw.exists():
                try:
                    r = tts.synthesize(f.get('falado', f['texto']), o, provider=v.get('provider', 'edge'), voice=v.get('voice', 'pt-BR-AntonioNeural'), rate=v.get('rate', '+6%'))
                except Exception:  # noqa: BLE001
                    if not v.get('reserva'):
                        raise
                    r = tts.synthesize(f.get('falado', f['texto']), o, provider=v.get('provider', 'edge'), voice=v['reserva'], rate=v.get('rate', '+6%'))
                jw.write_text(json.dumps(r.get('words') or []), encoding='utf-8')
            f['_mp3'], f['_dur'], f['_words'] = o, _mp3_dur(ff, o), json.loads(jw.read_text(encoding='utf-8'))
    return falas


def carregar(ep_path):
    """Lê o episódio; se for dia de uma série, aplica o estado de abertura de serie.json."""
    p = Path(ep_path)
    ep = json.loads(p.read_text(encoding='utf-8-sig'))
    if not ep.get('serie'):
        return ep
    s = json.loads((p.parent / ep['serie']).read_text(encoding='utf-8-sig'))
    e = s['estado']
    assert e['dia_atual'] == ep['dia'], (e['dia_atual'], ep['dia'])
    ep.update(titulo=s['titulo'], meta=s['meta'], voz=s['voz'], valor_inicial=e['dinheiro'], hud_txt=s['hud'], selo_dia=f"DIA {ep['dia']} DE {s['dias']}")
    ep['inventario'] = [dict(icone=i) for i in e['itens']] + ep.get('inventario_extra', [])
    ep.setdefault('dias_abertura', e['dias_ate_sabado'])
    for c in ep['cenas']:
        c.setdefault('dias', ep['dias_abertura'])
    return ep


def tempos(ep):
    """Cena corrida: a fala seguinte começa quando a anterior acaba. "f2" = fim da fala 2, "i2" = início, "fim" = fim do plano."""
    gap = ep.get('gap_fala', .06)
    for c in ep['cenas']:
        fs = c.get('falas', [])
        if not c.get('auto'):
            continue
        t = c.get('ini', .08)
        for f in fs:
            t += f.get('antes', 0)
            f['t'] = round(t, 3)
            w = f.get('_words') or []
            f['_fim'] = round(t + (w[-1]['end'] + .06 if w else f['_dur']), 3)
            t = f['_fim'] + gap
        c['dur'] = round(t - gap + c.get('apos', .1), 3)

        def T(x, base=0.0):
            if not isinstance(x, str):
                return x
            m = re.match(r'([fi])(\d+)([+-][\d.]+)?$', x)
            if not m:
                raise ValueError(x)
            f = fs[int(m[2])]
            return round((f['_fim'] if m[1] == 'f' else f['t']) + float(m[3] or 0) - base, 3)
        for k in ('sfx', 'inv_novo', 'inv_perde'):
            for it in c.get(k, []):
                it[1] = T(it[1])
        for it in c.get('valor', []):
            it[0] = T(it[0])
        for it in c.get('ambiente', []):
            it[1] = T(it[1])
            it[2] = c['dur'] if it[2] == 'fim' else it[2]
        if 'meta_entra' in c:
            c['_meta_entra'] = T(c['meta_entra'])
        p0 = 0.0
        for i, pl in enumerate(c['planos']):
            ate = c['dur'] if i == len(c['planos']) - 1 else T(pl['ate'])
            pl['ate'] = ate
            d = ate - p0

            def L(x, p0=p0, d=d):
                return d if x == 'fim' else T(x, p0)
            for k in ('cam',):
                for it in pl.get(k, []):
                    it[0] = L(it[0])
            for a in pl.get('atores', []):
                for it in a.get('poses', []):
                    it[0] = L(it[0])
                for it in a.get('mov') or []:
                    it[0] = L(it[0])
            for o in pl.get('objetos', []):
                for it in o['chaves']:
                    it[0] = L(it[0])
            if pl.get('gato'):
                for it in pl['gato']['mov']:
                    it[0] = L(it[0])
                if isinstance(pl['gato'].get('corre'), str):
                    pl['gato']['corre'] = L(pl['gato']['corre'])
            for k, v in pl.get('riscos', {}).items():
                pl['riscos'][k] = [L(v[0]), L(v[1])]
            for k in ('toasts', 'selos', 'efeitos', 'dialogos'):
                for it in pl.get(k, []):
                    for q in ('de', 'ate'):
                        if q in it:
                            it[q] = L(it[q])
            for it in pl.get('tremor') or []:
                it[0], it[1] = L(it[0]), L(it[1])
            p0 = ate


def _pedaços(txt, chave, max_chars=15):
    """Quebra em 1 ou 2 palavras, respeitando o tamanho, com a palavra-chave colorida."""
    pal = txt.replace(',', ' ,').replace('.', ' .').replace(':', ' :').replace('?', ' ?').split()
    tokens = []
    for p in pal:
        if p in ',.:?':
            if tokens:
                tokens[-1] = (tokens[-1][0], True)
        else:
            tokens.append((p, False))
    out, cur = [], []
    for w, pausa in tokens:
        cur.append(w)
        n = sum(len(x) for x in cur) + len(cur) - 1
        if len(cur) == 2 or pausa or n > max_chars - 4:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    res = []
    for g in out:
        res.append([(w.upper(), AMARELO if w.lower().strip('.,:') in chave else '#fff') for w in g])
    return res


def montar(ep, tmp):
    """Traduz o JSON em marcação + dados do runtime."""
    extra_itens = {
        'cofrinho': itens.cofrinho_mao(), 'colher': itens.colher(), 'lapis': itens.lapis(), 'placa': itens.placa_r2(), 'brig': itens.brigadeiro_mao(),
        'bola': itens.bola_mao(), 'nota': itens.nota_mao(), 'notaV': itens.nota_mao_virada(), 'moedaM': f'<g transform="translate(30 -3)">{itens.moeda_frente(9)}</g>', 'envelope': itens.envelope_mao(), 'conta': itens.conta_mao()}
    extra_itens.update(itens.MAO)
    extra_itens.update(ep.get('itens_mao') or {})
    if ep.get('personagens'):
        from . import boneco
        personagens._registrar_tipos()
        for ident, pr in ep['personagens'].items():
            boneco.registrar(ident, pr)
    corpo_extra = {'termica': cenarios2.alca_termica(), 'caixa_cheia': f'<g transform="translate(26 -66)">{itens.alca()}{itens.caixa_isopor(True, .86)}</g>',
                   'caixa_vazia': f'<g transform="translate(26 -66)">{itens.alca()}{itens.caixa_isopor(False, .86)}</g>'}
    planos, html, defs, t = [], [], {}, 0.0
    toasts, selos, leg, dias, valor, inv, fades = [], [], [], [], [], [], []
    dialogos, meta_de = [], 0
    if ep.get('inventario'):
        for i, it in enumerate(ep['inventario']):
            inv.append(dict(it, ord=i, de=it.get('de', 0)))
    val = ep.get('valor_inicial', 0.0)
    valor.append([0, val])
    leg_id = 0
    for c, cena in enumerate(ep['cenas']):
        t0c = t
        dias.append([t0c, cena.get('dias', 0)])
        if '_meta_entra' in cena:
            meta_de = t0c + cena['_meta_entra']
        for (a, v) in cena.get('valor', []):
            valor.append([t0c + a, val])
            valor.append([t0c + a + cena.get('valor_dur', .8), v])
            val = v
        for it in cena.get('inv_novo', []):
            for k in inv:
                if k['icone'] == it[0]:
                    k['de'] = t0c + it[1]
        for it in cena.get('inv_perde', []):
            for k in inv:
                if k['icone'] == it[0]:
                    k['ate'] = t0c + it[1]
                    k['troca'] = len(it) > 2
        for f in cena.get('falas', []):
            ini = t0c + f['t']
            ped = _pedaços(f['texto'], set(x.lower() for x in f.get('chave', [])))
            tot = sum(sum(len(w) + 1 for w, _ in g) + 2 for g in ped)
            at = ini
            ws = f.get('_words') or []
            exato = len(ws) == sum(len(g) for g in ped)
            iw = 0
            for g in ped:
                d = f['_dur'] * (sum(len(w) + 1 for w, _ in g) + 2) / tot
                if exato:
                    at = ini + ws[iw]['start']
                    d = ws[iw + len(g)]['start'] - ws[iw]['start'] if iw + len(g) < len(ws) else ws[-1]['end'] - ws[iw]['start']
                    iw += len(g)
                y = f.get('y') or cena.get('leg_y', 1060)
                for pl in cena['planos']:
                    pass
                leg.append([round(at, 3), round(at + d, 3), g, y])
                at += d
            leg[-1][1] = round(leg[-1][1] + .22, 3)
        p0 = 0.0
        for pi, pl in enumerate(cena['planos']):
            i = len(planos)
            ate = pl.get('ate', cena['dur'])
            nomecen = pl.get('cenario', cena.get('cenario'))
            opc = pl.get('opc', {} if 'cenario' in pl else cena.get('opc', {}))
            if nomecen == 'final':
                sc = dict(fundo=_tela_final(ep['final']), frente='', meio='', luz='')
                sc['defs'] = ''
            else:
                sc = cenarios.CENARIOS[nomecen](**opc)
            if sc.get('defs'):
                defs[nomecen.split('_')[0]] = sc['defs']
            objs_tras, objs_frente, topo_objs = '', '', ''
            objs = []
            for o in pl.get('objetos', []):
                svg = _obj_svg(o)
                if svg is not None:
                    tag = f'<g data-obj="{o["id"]}" display="none">{svg}</g>'
                    cam = o.get('camada', 'frente')
                    if cam == 'tras':
                        objs_tras += tag
                    elif cam == 'topo':
                        topo_objs += tag
                    else:
                        objs_frente += tag
                ch = [list(k) for k in o['chaves']]
                objs.append(dict(id=o['id'], chaves=ch, linear=o.get('linear'), ease=o.get('ease'), traco=o.get('traco')))
            atores_svg, topo_svg, atores_d = '', '', []
            for k, a in enumerate(pl.get('atores', [])):
                track = [[x[0], poses.resolve(x[1]), (x[2] if len(x) > 2 else None)] for x in a['poses']]
                usados = {p.get('sN') for _, p, _ in track} | {p.get('sF') for _, p, _ in track}
                mapa = {n: v for n, v in extra_itens.items() if n in usados}
                peito = corpo_extra.get(a.get('caixa', ''), '')
                alvo = _ator(a['nome'], mapa, dict(mochila=a.get('mochila'), peito=peito, costas=cenarios2.mochila_termica() if a.get('caixa') == 'termica' else '', cabeca=cenarios2.NA_CABECA.get(a.get('na_cabeca', ''), '')))
                clip = ''
                if a.get('recorte'):
                    cid = f'rc{i}_{k}'
                    x, y, w, h = a['recorte']
                    defs[cid] = f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath>'
                    clip = f' clip-path="url(#{cid})"'
                atores_svg += f'<g{clip}><g class="ator{k}">{alvo[0]}</g></g>'
                topo_svg += f'<g class="topo{k}"></g>'
                atores_d.append(dict(nome=a['nome'], x=a.get('x', 0), y=a.get('y', 0), vira=a.get('vira', 1), escala=a.get('escala', 1), poses=track, mov=a.get('mov'), movLinear=a.get('mov_linear')))
            gato = ''
            if pl.get('gato'):
                gato = f'<g class="gato"><g class="gs">{personagens.gato_sentado()}</g><g class="gc" display="none">{personagens.gato_correndo()}</g></g>'
            efx = ''
            for k, f in enumerate(pl.get('efeitos', [])):
                efx += f'<g class="fx{k}" display="none">{_fx(f)}</g>'
            bl = ''.join(f'<g>{cenarios.desfocado(x)}</g>' for x in pl.get('desfocados', []))
            html.append(f'''<g class="plano" id="p{i}" display="none">{f'<g class="wS">{sc["ceu"]}</g>' if sc.get('ceu') else ''}<g class="w0">{sc['fundo']}</g>
<g class="w1">{sc.get('meio', '')}{objs_tras}{gato}{atores_svg}{sc.get('frente', '')}{objs_frente}{topo_svg}{topo_objs}{efx}{sc.get('luz', '')}</g>{f'<g class="wB">{bl}</g>' if bl else ''}</g>''')
            cam = pl.get('cam', [[0, 360, 640, 1]])
            planos.append(dict(t0=t0c + p0, t1=t0c + ate, cena0=t0c, cam=cam, atores=atores_d, objetos=objs, riscos=pl.get('riscos', {}), gato=pl.get('gato'), efeitos=pl.get('efeitos', []), tremor=pl.get('tremor'), semHud=pl.get('sem_hud')))
            for k in pl.get('toasts', []):
                toasts.append(dict(k, de=t0c + p0 + k['de'], ate=min(t0c + ate, t0c + p0 + k.get('ate', 99))))
            for k in pl.get('dialogos', []):
                import textwrap
                dialogos.append(dict(k, de=t0c + p0 + k['de'], ate=min(t0c + ate, t0c + p0 + k.get('ate', 99)), linhas=(textwrap.wrap(k['texto'], 26) + [''])[:2]))
            for k in pl.get('selos', []):
                selos.append(dict(k, de=t0c + p0 + k['de'], ate=min(t0c + ate, t0c + p0 + k.get('ate', 99))))
            # legenda do plano: posição própria
            if 'leg_y' in pl:
                for lg in leg:
                    if lg[0] >= t0c + p0 - 1e-3 and lg[0] < t0c + ate:
                        lg[3] = pl['leg_y']
            p0 = ate
        t = t0c + cena['dur']
    for a0, b0 in zip(leg, leg[1:]):
        a0[1] = min(a0[1], b0[0])
    valor.append([t + 1, val])
    d = dict(meta=ep['meta'], total=t, planos=planos, chars={k: _dados_char(k) for k in personagens.CHARS}, expr=personagens.EXPR_JS,
             hud=dict(dias=dias, valor=_mono(valor), barW=ui.BAR_W + 84), toasts=toasts, selos=selos, legendas=leg, valorFmt=ep.get('valor_fmt', 'brl'), valorSuf=ep.get('valor_suf', ''), dialogos=dialogos, metaDe=meta_de, toastY=150 if ep.get('selo_dia') else 108, itensInv=[{k: v for k, v in x.items()} for x in inv], fades=ep.get('fades', []))
    return html, defs, d


def _mono(v):
    v = sorted(v, key=lambda x: x[0])
    out = []
    for a in v:
        if out and abs(out[-1][0] - a[0]) < 1e-6:
            continue
        out.append(a)
    return out


def _dados_char(n):
    c = personagens.CHARS[n]
    return {**{k: c[k] for k in ('quadril', 'ombroN', 'ombroF', 'braco', 'wb', 'manga', 'coxa', 'perna', 'wp', 'short', 'pesc', 'k')}, 'curva': c.get('curva', 0)}


def _ator(nome, mapa, opc):
    return personagens.ator_svg(nome, mapa, opc)


def _obj_svg(o):
    if o.get('existente'):
        return None
    if 'svg' in o:
        return o['svg']
    k = o['item']
    if k == 'cadeira_gerada':
        return cenarios2.assento(*o.get('args', []))
    if hasattr(cenarios2, k):
        return getattr(cenarios2, k)(*o.get('args', []))
    f = dict(cofrinho=itens.cofrinho, botao=itens.botao, envelope=itens.envelope, bola=itens.bola, moeda=itens.moeda, placa_sopa=cenarios.placa_sopa, mao_lapis=cenarios.mao_lapis, banquinho=cenarios.banquinho, moeda_f=itens.moeda_frente,
             brigadeiro=itens.brigadeiro, placa=itens.placa_r2, caixa=itens.caixa_isopor, nota=itens.nota, conta=itens.conta_mesa)[k]
    r = f(*o.get('args', []))
    return r


def _fx(f):
    n = f.get('n', 14)
    if f['tipo'] in ('fumaca', 'vapor'):
        fill = 'url(#fumE)' if f.get('escura') else 'url(#fum)'
        return ''.join(f'<circle fill="{fill}" r="10" opacity="0"/>' for _ in range(n))
    if f['tipo'] == 'moedas':
        return ''.join(f'<g display="none">{itens.moeda_frente(f.get("r", 12))}</g>' for _ in range(n))
    if f['tipo'] == 'pingos':
        return ''.join('<ellipse fill="none" stroke="#dceaf6" stroke-width="2" opacity="0"/>' for _ in range(n))
    if f['tipo'] == 'faiscas':
        return ''.join('<circle r="9" fill="#ffd23f"/>' for _ in range(n))
    return ''


def _tela_final(fi):
    from .base import L, ln
    a, b = fi['a'], fi['b']
    W = 720
    fp = lambda t: min(72, int(280 / (max(1, len(t)) * .76)))
    listras = ''.join(f'<path d="M{x} -80L{x - 260} 1360" stroke="#fff" stroke-opacity=".035" stroke-width="44"/>' for x in range(0, 1100, 110))
    def lado(x, w, cor, cor2):
        return f'<rect x="{x}" y="-80" width="{w}" height="1440" fill="{cor}"/>'
    corpo = lado(0, 360, '#1d4f7a', '') + lado(360, 360, '#7a2f4a', '') + listras
    apaga = '<g data-obj="dimA"><rect x="0" y="226" width="356" height="1134" fill="#000" opacity=".42"/></g><g data-obj="dimB"><rect x="364" y="226" width="356" height="1134" fill="#000" opacity=".42"/></g>'
    corpo += f'<rect x="356" y="-80" width="8" height="1440" fill="#ffd23f"/>'
    corpo += f'''<g font-family="'Arial Black',Arial" text-anchor="middle"><rect x="150" y="166" width="420" height="52" rx="26" fill="#0b0d16" stroke="#ffd23f" stroke-width="4"/><text x="360" y="203" font-size="28" fill="#ffd23f">COMENTE UMA PALAVRA</text>
<text x="182" y="298" font-size="{fp(a['palavra'])}" fill="#ffd23f" style="paint-order:stroke" stroke="#0b0d16" stroke-width="8">{a['palavra']}</text><text x="540" y="298" font-size="{fp(b['palavra'])}" fill="#5ec8ff" style="paint-order:stroke" stroke="#0b0d16" stroke-width="8">{b['palavra']}</text>
<text x="182" y="336" font-size="21" fill="#fff" style="paint-order:stroke" stroke="#0b0d16" stroke-width="5">{a['sub']}</text><text x="540" y="336" font-size="21" fill="#fff" style="paint-order:stroke" stroke="#0b0d16" stroke-width="5">{b['sub']}</text>
<g data-vida="y:3:3:0"><circle cx="360" cy="436" r="32" fill="#0b0d16" stroke="#ffd23f" stroke-width="5"/><text x="360" y="450" font-size="36" fill="#fff">X</text></g></g>'''
    return corpo + apaga


def pagina(ep, tmp):
    html, defs, d = montar(ep, tmp)
    icones = {k['icone'] for k in sum([p.get('toasts', []) for c in ep['cenas'] for p in c['planos']], [])}
    nomes = {k['retrato'] for c in ep['cenas'] for p in c['planos'] for k in p.get('dialogos', [])}
    retratos = ''.join(f'<g data-r="{n}" display="none" transform="translate(105 80)">{personagens.retrato(n)}</g>' for n in nomes)
    pg = f'''<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:#000;overflow:hidden}}</style></head><body><svg id="root" xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 720 1280">{DEFS}<defs>{''.join(defs.values())}</defs><clipPath id="tela"><rect width="720" height="1280"/></clipPath><g clip-path="url(#tela)">{''.join(html)}</g>{ui.hud(ep)}{ui.camadas_topo(icones, retratos)}</svg>
<script>window.DADOS={json.dumps(d, ensure_ascii=False)};</script><script>{animacao.js()}</script><script>document.getElementById('inv').innerHTML={json.dumps(ui.inventario(d['itensInv']))};frame(0);</script></body></html>'''
    return pg, d


def renderizar(ep_path, saida, tmp, quadros=None, so_som=False):
    return produzir(carregar(ep_path), saida, tmp, quadros=quadros, so_som=so_som)


def produzir(ep, saida, tmp, quadros=None, so_som=False, progresso=None, cancelar=None, antes=None, miniatura=None):
    """Episódio já em memória -> MP4. progresso(0-1), cancelar() (levanta para interromper), antes(ep, total) depois
    de medir a voz e antes do render, miniatura=(tempo(ep), caminho)."""
    from lidark.media import ffmpeg_exe
    from playwright.sync_api import sync_playwright
    FF = ffmpeg_exe()
    t_ini = time.time()
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    narracao(ep, tmp, FF)
    tempos(ep)
    (tmp / 'ep_resolvido.json').write_text(json.dumps(ep, ensure_ascii=False, default=str), encoding='utf-8')
    pg_html, d = pagina(ep, tmp)
    hp = tmp / 'ep.html'
    hp.write_text(pg_html, encoding='utf-8')
    TOTAL = d['total']
    print('duração', round(TOTAL, 2), 'html KB', len(pg_html) // 1024)
    for c in ep['cenas']:
        for f in c.get('falas', []):
            print(' ', c.get('id'), f['t'], round(f['_dur'], 2), f['texto'][:50], 'ate', round(f['t'] + f['_dur'], 2), 'de', c['dur'])
    if antes:
        antes(ep, TOTAL)
    if so_som:
        return _final(ep, TOTAL, tmp, FF, saida)
    with sync_playwright() as p:
        b = p.chromium.launch(channel='msedge')
        pg = b.new_page(viewport={'width': 1080, 'height': 1920})
        er = []
        pg.on('pageerror', lambda e: er.append(str(e)))
        pg.on('console', lambda m: er.append(m.text) if m.type == 'error' else None)
        pg.goto(hp.as_uri())
        if er:
            print('ERROS', er[:3])
        cdp = pg.context.new_cdp_session(pg)
        if quadros is not None:
            for q in quadros:
                pg.evaluate('t=>frame(t)', q)
                (tmp / f'q_{q:07.3f}.jpg').write_bytes(base64.b64decode(cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 92})['data']))
            b.close()
            print('quadros ok', er[:3])
            return
        mudo = tmp / 'mudo.mp4'
        enc = subprocess.Popen([FF, '-y', '-v', 'error', '-f', 'image2pipe', '-c:v', 'mjpeg', '-framerate', str(FPS), '-i', '-', '-vf', 'format=yuv420p', '-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-crf', '14', '-threads', '3', str(mudo)], stdin=subprocess.PIPE)
        N = int(round(TOTAL * FPS))
        for n in range(N):
            pg.evaluate('t=>frame(t)', n / FPS)
            enc.stdin.write(base64.b64decode(cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 97, 'optimizeForSpeed': True})['data']))
            if n % 300 == 0:
                print('quadro', n, '/', N, flush=True)
            if n % 15 == 0:
                if cancelar:
                    cancelar()
                if progresso:
                    progresso(n / N)
        if miniatura:
            pg.evaluate("t=>{frame(t);for(const i of ['hudG','leg','item','selo','dlg'])document.getElementById(i).style.display='none'}", miniatura[0](ep))
            Path(miniatura[1]).write_bytes(base64.b64decode(cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 92})['data']))
        b.close()
        print('erros', er[:3])
    enc.stdin.close()
    enc.wait()
    r = _final(ep, TOTAL, tmp, FF, saida)
    r.update(frames=N, seconds=round(time.time() - t_ini, 1), duration=TOTAL)
    return r


def _final(ep, TOTAL, tmp, FF, saida):
    mudo = tmp / 'mudo.mp4'
    audio = som.mixar(ep, TOTAL, tmp, FF)
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    lim = 'alimiter=limit=0.5:attack=3:release=60:level=false'  # segura moedas e pancadas, senão o pico trava o ganho antes de -14
    r = subprocess.run([FF, '-hide_banner', '-i', str(audio), '-af', f'{lim},loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='ignore').stderr
    m = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    af = (f"{lim},loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000,alimiter=limit=0.78:attack=2:release=40:level=false")
    subprocess.run([FF, '-y', '-v', 'error', '-i', str(mudo), '-i', str(audio), '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-af', af, '-t', f'{TOTAL:.3f}', '-movflags', '+faststart', str(saida)], check=True)
    print('pronto', saida)
    return {'loudness': {'measured_lufs': m.get('input_i')}}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('ep')
    ap.add_argument('saida')
    ap.add_argument('--tmp', required=True)
    ap.add_argument('--quadros', default=None)
    ap.add_argument('--so-som', action='store_true')
    a = ap.parse_args()
    q = [float(x) for x in a.quadros.split(',')] if a.quadros else None
    renderizar(a.ep, a.saida, a.tmp, q, a.so_som)


if __name__ == '__main__':
    main()
