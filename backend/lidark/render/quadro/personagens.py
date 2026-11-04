"""Elenco. Cada personagem tem proporção real (adulto ~1:6,3 cabeças; Caio ~1:5,1) e o mesmo traço.

Coordenadas locais do ator: pés em (0,0), frente para +x (3/4), y negativo para cima.
A cabeça é desenhada no sistema do quadro aprovado (pivô no queixo, 345,570) e reduzida por `k`.
Braços e pernas não são peças: o runtime traça, a cada quadro, uma silhueta contínua
ombro-punho e quadril-tornozelo com comprimento fixo (cinemática inversa), então nada estica.
"""
from __future__ import annotations

from .base import L, ln

_id = [0]


def _uid() -> str:
    _id[0] += 1
    return f'u{_id[0]}'


# ---------- crânios e narizes por tipo (coordenadas do quadro aprovado)
CRANIO = {
    'menino': 'M276 470C272 412 304 378 350 378C396 378 426 408 426 458C428 490 420 516 402 536C386 552 362 558 340 554C312 550 292 534 284 508C280 496 276 484 276 470z',
    'mulher': 'M278 466C274 410 306 376 350 376C394 376 422 408 422 456C422 486 412 518 392 540C376 556 356 562 338 556C312 548 294 530 286 504C282 492 278 480 278 466z',
    'homem': 'M274 470C270 410 302 374 350 374C398 374 430 406 428 456C430 492 424 518 408 538C392 556 364 566 336 562C306 558 288 540 280 510C276 496 274 484 274 470z',
}
NARIZ = {
    'menino': 'M388 482C386 494 392 503 404 502C412 501 413 494 407 491',
    'mulher': 'M386 482C385 494 391 504 402 502C409 501 410 495 405 492',
    'homem': 'M380 482C380 498 392 510 408 508C420 506 422 494 412 490C404 488 398 488 392 482',
}
# Expressões: sobrancelhas, boca e pálpebra (0 aberta, 1 fechada)
_B = {
    'neutro': 'M334 436q18-9 38-2M386 435q14-7 28 2',
    'triste': 'M334 444q16-13 38-16M386 428q16 2 28 13',
    'bravo': 'M334 430q20 2 38 11M386 441q14-8 28-11',
    'alto': 'M334 424q18-10 38-3M386 423q14-8 28 3',
}
_M = {
    'neutro': ('M364 534C374 531 388 531 398 534', 0),
    'triste': ('M362 541C372 529 390 529 400 539', 0),
    'leve': ('M362 530C372 540 390 540 402 528', 0),
    'sorriso': ('M356 524C368 546 396 546 408 522', 0),
    'rindo': ('M354 520C372 530 394 530 410 518C406 556 362 560 354 520z', 1),
    'aberta': ('M370 533C370 520 394 520 394 533C394 548 370 548 370 533z', 1),
    'aperta': ('M360 536q7-6 13 0t13 0t13-1', 0),
    'chora': ('M360 538C372 526 392 526 402 538C396 546 368 546 360 538z', 1),
}
EXPR = {
    'neutro': dict(br='neutro', boca='neutro', lid=.16),
    'atento': dict(br='alto', boca='neutro', lid=.04),
    'triste': dict(br='triste', boca='triste', lid=.3),
    'preocupado': dict(br='triste', boca='neutro', lid=.24),
    'cansado': dict(br='triste', boca='neutro', lid=.42),
    'decidido': dict(br='bravo', boca='leve', lid=.14),
    'sorriso': dict(br='neutro', boca='sorriso', lid=.14),
    'alegre': dict(br='alto', boca='rindo', lid=.1),
    'surpreso': dict(br='alto', boca='aberta', lid=.0),
    'tosse': dict(br='bravo', boca='aberta', lid=.7),
    'aperto': dict(br='triste', boca='aperta', lid=.34),
    'emocionado': dict(br='triste', boca='chora', lid=.5),
    'calmo': dict(br='neutro', boca='leve', lid=.3),
    'bravo_c': dict(br='bravo', boca='neutro', lid=.12),
}
EXPR_JS = {k: dict(br=_B[v['br']], boca=_M[v['boca']][0], bf=_M[v['boca']][1], lid=v['lid']) for k, v in EXPR.items()}


def _nuvem(pts, fill, w=2.6):
    """Cabelo cacheado: contorno único da união de círculos."""
    a = ''.join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{L}" stroke-width="{w * 2}"/>' for x, y, r in pts)
    b = ''.join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>' for x, y, r in pts)
    return a + b


def cabelo(tipo, cor, cor2):
    """(atrás da cabeça, na frente da cabeça)"""
    if tipo == 'cachos':
        tras = _nuvem([(292, 430, 34), (316, 392, 36), (358, 372, 36), (402, 386, 32), (430, 420, 24), (278, 470, 22)], cor)
        fr = _nuvem([(300, 420, 22), (326, 396, 24), (362, 388, 24), (396, 398, 20), (420, 414, 15), (288, 456, 15)], cor, 1.3)
        fr += f'<path d="M318 384q10-8 20-2M368 378q12-4 20 6M300 408q6-10 16-10M404 398q8 0 12 8" fill="none" stroke="{cor2}" stroke-width="4.5" stroke-linecap="round"/>'
        return tras, fr
    if tipo == 'coque':
        tras = f'<circle cx="292" cy="372" r="34" fill="{cor}" {ln(3)}/><path d="M280 356q14-12 26-4M272 378q10 12 26 12" fill="none" stroke="{cor2}" stroke-width="4"/>'
        fr = (f'<path d="M272 482C252 412 296 358 352 358C402 358 432 392 428 440C420 416 404 404 384 402C360 416 322 418 300 428C292 444 286 464 272 482z" fill="{cor}" {ln(3)}/>'
              f'<path d="M314 380C340 370 372 372 396 386M300 400C324 386 350 384 372 392" fill="none" stroke="{cor2}" stroke-width="4" stroke-linecap="round"/>'
              f'<path d="M294 446C288 470 290 494 298 508" fill="none" stroke="{cor}" stroke-width="5" stroke-linecap="round"/>')
        return tras, fr
    if tipo == 'rabo':
        tras = (f'<path d="M292 372C250 372 232 420 240 470C246 510 262 530 272 540C282 500 300 470 300 430z" fill="{cor}" {ln(3)}/>'
                f'<path d="M262 420C256 450 258 484 268 510" fill="none" stroke="{cor2}" stroke-width="4" stroke-linecap="round"/>')
        fr = (f'<path d="M272 482C252 412 296 358 352 358C402 358 432 392 428 440C420 416 404 404 384 402C360 416 322 418 300 428C292 444 286 464 272 482z" fill="{cor}" {ln(3)}/>'
              f'<path d="M314 380C340 370 372 372 396 386" fill="none" stroke="{cor2}" stroke-width="4" stroke-linecap="round"/><path d="M290 372l-8 16" stroke="#e0672f" stroke-width="9" stroke-linecap="round"/>')
        return tras, fr
    if tipo == 'chanel':
        tras = f'<path d="M262 560C240 470 262 362 352 356C424 352 448 420 438 480L442 540C430 560 410 556 400 540H300C290 560 272 566 262 560z" fill="{cor}" {ln(3)}/>'
        fr = (f'<path d="M274 486C262 420 300 366 354 366C402 366 432 396 430 446C414 436 392 420 372 402C352 424 312 438 292 442C284 458 282 472 274 486z" fill="{cor}" {ln(3)}/>'
              f'<path d="M322 384C350 374 386 382 408 408" fill="none" stroke="{cor2}" stroke-width="4" stroke-linecap="round"/>')
        return tras, fr
    if tipo == 'curto':
        fr = (f'<path d="M272 476C258 412 298 360 352 360C400 360 432 388 430 434C422 416 408 406 392 404C370 396 342 396 324 408C306 418 296 440 292 462C286 466 278 470 272 476z" fill="{cor}" {ln(3)}/>'
              f'<path d="M318 382C340 372 372 374 398 388" fill="none" stroke="{cor2}" stroke-width="4" stroke-linecap="round"/>')
        return '', fr
    if tipo == 'capacete':
        fr = (f'<path d="M270 470C258 404 298 362 352 362C396 362 430 390 432 436C420 420 406 410 392 408C368 400 342 402 324 412C306 422 298 444 294 464z" fill="{cor}" {ln(3)}/>'
              f'<path d="M264 432C266 372 306 338 352 338C402 338 438 372 442 428C400 412 318 412 264 432z" fill="{cor2}" {ln(3)}/>'
              f'<path d="M256 436C312 412 404 410 462 432C466 438 462 444 454 442C402 424 316 426 264 446C256 448 252 442 256 436z" fill="{cor2}" {ln(3)}/>'
              f'<path d="M340 344V414M366 342V412" stroke="{L}" stroke-width="2.4" opacity=".35"/><path d="M300 368C320 352 344 348 362 350" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity=".6"/>')
        return '', fr
    if tipo in ('careca', 'calvo', 'grisalho_lado'):
        if tipo == 'careca':
            return '', f'<path d="M322 392q24-14 54-6" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" opacity=".5"/>'
        return '', f'<path d="M274 490C258 452 268 418 296 402C286 430 288 462 290 486z" fill="{cor}" {ln(2.6)}/><path d="M424 430C440 442 438 474 426 486C428 464 428 446 424 430z" fill="{cor}" {ln(2.6)}/>'
    if tipo == 'black':
        return _nuvem([(350, 370, 92), (268, 410, 54), (432, 410, 54), (296, 340, 56), (408, 340, 56)], cor), f'<path d="M292 462C300 416 330 402 362 402C396 402 416 416 424 440" fill="none" stroke="{cor}" stroke-width="16" stroke-linecap="round"/>'
    if tipo == 'topete':
        return '', f'<path d="M272 476C258 412 292 372 320 366C330 320 400 306 440 340C450 352 440 374 424 382C432 396 432 414 430 434C422 416 408 406 392 404C370 396 342 396 324 408C306 418 296 440 292 462z" fill="{cor}" {ln(3)}/><path d="M336 350C362 330 404 330 426 346" fill="none" stroke="{cor2}" stroke-width="5" stroke-linecap="round"/>'
    if tipo == 'longo':
        return f'<path d="M258 620C232 500 250 362 352 356C444 352 462 480 444 620C420 640 390 620 400 560H300C306 620 280 640 258 620z" fill="{cor}" {ln(3)}/>', f'<path d="M274 486C262 420 300 366 354 366C402 366 432 396 430 446C414 436 392 420 372 402C352 424 312 438 292 442C284 458 282 472 274 486z" fill="{cor}" {ln(3)}/>'
    if tipo == 'franja':
        return f'<path d="M262 540C244 460 264 362 352 356C424 352 448 420 438 500C420 520 300 530 262 540z" fill="{cor}" {ln(3)}/>', f'<path d="M278 450C276 400 310 366 354 366C400 366 428 400 426 448C400 436 380 440 362 436C336 444 304 438 278 450z" fill="{cor}" {ln(3)}/>'
    if tipo == 'trancas':
        tr = ''.join(f'<ellipse cx="{x}" cy="{y}" rx="16" ry="12" fill="{cor}" {ln(2.2)}/>' for x, y in ((266, 500), (262, 524), (258, 548), (254, 572), (438, 500), (442, 524), (446, 548), (450, 572)))
        return tr, f'<path d="M272 482C252 412 296 358 352 358C402 358 436 392 432 470C424 424 404 404 352 402C312 404 288 430 272 482z" fill="{cor}" {ln(3)}/><path d="M352 358V402" stroke="{cor2}" stroke-width="4"/>'
    return '', ''


def cabeca(c):
    """Cabeça com hooks: .cSo (sobrancelha), .cBo (boca), .cPu (pupilas), .cLi (pálpebras), .cPi (piscada)."""
    sk, sd, sh = c['pele']
    cr = CRANIO[c['cranio']]
    cid, e1, e2 = _uid(), _uid(), _uid()
    tras, fr = cabelo(c['cabelo'], c['cor_cabelo'], c['cor_cabelo2'])
    xe1, ye1, rx1, ry1 = 354, 464, 17, 19
    xe2, ye2, rx2, ry2 = 398, 464, 15, 18
    lid = lambda x, y, rx, ry, e: (f'<g clip-path="url(#{e})"><g class="cLi"><rect x="{x - rx - 3}" y="{y - ry - 46}" width="{2 * rx + 6}" height="46" fill="{sk}"/>'
                                   f'<path d="M{x - rx - 3} {y - ry}q{rx + 3} 7 {2 * rx + 6} 0" fill="{sk}" stroke="{L}" stroke-width="3"/></g></g>')
    extra = ''
    if c.get('oculos'):
        extra += f'<g fill="none" {ln(3)}><circle cx="354" cy="464" r="26"/><circle cx="400" cy="464" r="23"/><path d="M380 460h-2M328 460L280 450"/></g>'
    if c.get('bigode'):
        extra += f'<path d="M352 520C366 508 388 508 396 514C404 508 420 512 424 522C410 528 400 524 394 520C384 526 366 528 352 520z" fill="{c["cor_cabelo"]}" {ln(2.4)}/>'
    if c.get('brinco'):
        extra += f'<circle cx="279" cy="500" r="6" fill="#e0b23c" {ln(2.2)}/>'
    if c.get('barba'):
        extra += f'<path d="M286 508C300 536 320 552 342 554C362 556 386 552 402 536L410 518C396 526 380 516 362 520C340 524 312 520 286 508z" fill="{sd}" opacity=".55"/>'
    if c.get('rugas'):
        extra += f'<path d="M334 490q16 7 32 1M380 488q10 5 22 0" fill="none" stroke="{sd}" stroke-width="2.6" stroke-linecap="round"/>'
    return f'''{tras}
<ellipse cx="{278 - (c.get('orelha', (11, 19))[0] - 11) * .6:.0f}" cy="480" rx="{c.get('orelha', (11, 19))[0]}" ry="{c.get('orelha', (11, 19))[1]}" fill="{sk}" {ln(3)}/><path d="M275 472q6 8 0 16" fill="none" {ln(2.2)}/>
<clipPath id="{cid}"><path d="{cr}"/></clipPath><clipPath id="{e1}"><ellipse cx="{xe1}" cy="{ye1}" rx="{rx1}" ry="{ry1}"/></clipPath><clipPath id="{e2}"><ellipse cx="{xe2}" cy="{ye2}" rx="{rx2}" ry="{ry2}"/></clipPath>
<path d="{cr}" fill="{sk}"/>
<g clip-path="url(#{cid})"><path d="M268 372C288 430 282 500 318 570H258z" fill="{sd}" opacity=".5"/><ellipse cx="364" cy="406" rx="32" ry="9" fill="{sh}" opacity=".75"/>{f'<ellipse cx="340" cy="505" rx="17" ry="10" fill="{c["blush"]}" opacity=".45"/><ellipse cx="412" cy="503" rx="11" ry="9" fill="{c["blush"]}" opacity=".4"/>' if c.get('blush') else ''}</g>
<path d="{cr}" fill="none" {ln(3.2)}/>
<ellipse cx="{xe1}" cy="{ye1}" rx="{rx1}" ry="{ry1}" fill="#fff"/><ellipse cx="{xe2}" cy="{ye2}" rx="{rx2}" ry="{ry2}" fill="#fff"/>
<g class="cPu"><circle cx="360" cy="468" r="7.5" fill="{L}"/><circle cx="403" cy="468" r="7" fill="{L}"/><circle cx="358" cy="465" r="2.4" fill="#fff"/><circle cx="401" cy="465" r="2.2" fill="#fff"/></g>
{lid(xe1, ye1, rx1, ry1, e1)}{lid(xe2, ye2, rx2, ry2, e2)}
<ellipse cx="{xe1}" cy="{ye1}" rx="{rx1}" ry="{ry1}" fill="none" {ln(2.8)}/><ellipse cx="{xe2}" cy="{ye2}" rx="{rx2}" ry="{ry2}" fill="none" {ln(2.8)}/>
<g class="cPi" display="none"><ellipse cx="{xe1}" cy="{ye1}" rx="{rx1 + 1}" ry="{ry1 + 1}" fill="{sk}"/><ellipse cx="{xe2}" cy="{ye2}" rx="{rx2 + 1}" ry="{ry2 + 1}" fill="{sk}"/><path d="M{xe1 - rx1} {ye1 + 3}q{rx1} 8 {2 * rx1} 0M{xe2 - rx2} {ye2 + 3}q{rx2} 8 {2 * rx2} 0" fill="none" {ln(3.2)}/></g>
<path class="cSo" d="" fill="none" stroke="{c['cor_sobr']}" stroke-width="{c.get('sobr', 6)}" stroke-linecap="round"/>
<g transform="translate(398 490) scale({c.get('nariz_esc', 1)}) translate(-398 -490)"><path d="{NARIZ[c.get('nariz') or c['cranio']]}" fill="{sk}" {ln(2.8)}/></g>
<path class="cBo" d="" fill="none" {ln(3)}/>
{extra}{c.get('extra_svg', '')}{fr}
<g class="cLa" display="none"><path d="M340 486q7 12 0 18q-7-6 0-18z" fill="#a9dcf2" {ln(1.8)}/></g>'''


# ---------- mãos: origem no punho, apontando para +x, polegar para -y. Comprimento 46 na escala 1.
# Cada dedo é um traço redondo com contorno: não vira garra nem espaguete, e os dedos ficam separados.
PALMA = 'M-3-7C3-9 10-11 22-11C25-11 26-8 26 0C26 8 25 10 22 10C10 11 3 9-3 7z'


def _dedo(pts, w, sk):
    d = 'M' + 'L'.join(f'{x} {y}' for x, y in pts)
    return (f'<path d="{d}" fill="none" stroke="{L}" stroke-width="{w + 3.2}" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="none" stroke="{sk}" stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


def _mao(sk, dedos, polegar, w=5.6):
    base = f'<path d="{PALMA}" fill="{sk}" {ln(3.2)}/>'
    fs = ''.join(_dedo(p, w, sk) for p in dedos)
    pol = _dedo(polegar, 6.6, sk) if polegar else ''
    return base + fs + f'<path d="M-1-6C4-8 12-9.5 22-9.5L24 8.5C12 9.5 4 8-1 6z" fill="{sk}"/>' + pol


def maos(sk, sd):
    K = [-8, -2.8, 2.6, 7.6]
    li = f'fill="none" stroke="{sd}" stroke-width="1.6" stroke-linecap="round"'
    enrolados = lambda ys: [[(24, y), (31, y + 1), (29, y + 5)] for y in ys]
    return {
        'aberta': (_mao(sk, [[(24, K[0]), (44, -12)], [(24, K[1]), (47, -4.4)], [(24, K[2]), (46, 3.4)], [(24, K[3]), (41, 11)]], [(6, -7), (12, -13), (18, -18)]), ''),
        'relaxada': (_mao(sk, [[(24, y), (34, y + 1), (39, y + 5)] for y in K], [(7, -7), (14, -10), (21, -10)]), ''),
        'apoiada': (_mao(sk, [[(24, K[0]), (45, -7)], [(24, K[1]), (47, -2.4)], [(24, K[2]), (46, 2.4)], [(24, K[3]), (42, 7)]], [(8, -7), (15, -12), (23, -13)]), ''),
        'palma': (_mao(sk, [[(24, y), (38, y - 1), (45, y - 5)] for y in K], [(7, -7), (14, -13), (22, -15)]) + f'<path d="M6 3C11-3 17-3 21 0" {li}/>', ''),
        'dedo': (_mao(sk, [[(24, -8), (47, -9)]] + enrolados(K[1:]), [(7, -6), (14, -6), (22, -2)]), ''),
        'punho': (f'<path d="{PALMA}" fill="{sk}" {ln(3.2)}/>', ''.join(_dedo([(13, y), (24, y - .5), (29, y + 1.2)], 5.4, sk) for y in (-8, -2.8, 2.4, 7.4)) + _dedo([(7, -8), (15, -11), (23, -10)], 6.2, sk)),
        'pinca': (_mao(sk, [[(24, -8), (35, -11), (42, -6)]] + enrolados(K[1:]), None), _dedo([(7, -7), (18, -14), (30, -13), (41, -8)], 5.8, sk)),
    }


def tenis(cor, cor2, cor3):
    return (f'<path d="M-15-22C-16-10-18 0-16 4C-4 6 26 6 44 6C51 6 52-4 46-7C34-11 24-14 16-22z" fill="{cor}" {ln(2.4)}/>'
            f'<path d="M-17 1C0 3 30 4 50 2C52 6 50 9 44 9C20 10-4 9-16 8z" fill="{cor2}" {ln(2.2)}/>'
            f'<path d="M6-20l8 7M14-23l8 7M22-22l6 6" stroke="{cor3}" stroke-width="2.6" stroke-linecap="round"/>')


def bota(cor, cor2):
    return (f'<path d="M-16-32C-17-14-19 0-17 4C-2 7 28 6 44 6C53 6 53-6 47-10C36-14 22-16 16-32z" fill="{cor}" {ln(2.4)}/>'
            f'<path d="M-18 2C0 4 30 5 52 2L50 10H-18z" fill="{cor2}" {ln(2.2)}/>')


def sapatilha(cor):
    return f'<path d="M-14-14C-16-6-16 2-14 5C6 7 30 7 42 5C46 2 42-4 34-5C24-6 16-8 10-14z" fill="{cor}" {ln(2.4)}/>'


# ---------- troncos: origem no quadril
def _avental(c, top, hem):
    if not c.get('avental'):
        return c.get('estampa', '')
    a = c['avental']
    return (f'<path d="M-14 {top + 2}L-20 {top + 44}H30L24 {top + 2}" fill="none" stroke="{a}" stroke-width="6"/><path d="M-26 {top + 40}H36L46 {hem + 10}H-36z" fill="{a}" {ln(2.2)}/>'
            f'<rect x="-6" y="{top + 56}" width="26" height="12" rx="2" fill="#fbf6e6" {ln(1.4)}/><path d="M-36 {top * .22:.0f}H46" stroke="#fff" stroke-opacity=".5" stroke-width="3"/>')


def torso_camiseta(c):
    sw, hw, top, hem = c['tw'], c['hw'], c['ty'], c['hem']
    C, Cd, Cl = c['roupa']
    nw, ww = c['pesw'] + 4, c.get('ww', hw)
    p = (f'M{-nw} {top}C{-nw - 12} {top + 8} {-sw + 14} {top + 10} {-sw} {top + 26}C{-sw + 2} {top * .6:.0f} {-ww} {top * .38:.0f} {-ww} {top * .2:.0f}C{-ww} 0 {-hw} {hem * .4:.0f} {-hw - 2} {hem}'
         f'C-20 {hem + 5} 20 {hem + 5} {hw + 2} {hem}C{hw} {hem * .4:.0f} {ww} 0 {ww} {top * .2:.0f}C{ww} {top * .38:.0f} {sw - 2} {top * .6:.0f} {sw} {top + 26}C{sw - 14} {top + 10} {nw + 12} {top + 8} {nw} {top}z')
    cid = _uid()
    s = f'<clipPath id="{cid}"><path d="{p}"/></clipPath>'
    s += f'<path d="{p}" fill="{C}"/><g clip-path="url(#{cid})"><path d="M{-hw - 20} {top}H{-hw + 22}C{-hw + 6} {top * .5:.0f} {-hw + 14} {hem * -.1:.0f} {-hw + 8} {hem + 10}H{-hw - 20}z" fill="{Cd}" opacity=".5"/>'
    if c.get('listra'):
        s += f'<g transform="translate(12 {top + 62})"><path d="M0-15L4.4-4.6 15-4.6 6.6 2 9.6 12.6 0 6.4-9.6 12.6-6.6 2-15-4.6-4.4-4.6z" fill="{c["listra"]}" stroke="{Cd}" stroke-width="1.6" stroke-linejoin="round"/></g>'
    s += _avental(c, top, hem)
    s += f'<path d="M-8 {top + 58}c10 16 26 18 40 8M-22 {hem - 18}c14 10 34 10 52 2" fill="none" stroke="{Cd}" stroke-width="3.4" stroke-linecap="round"/></g>'
    s += f'<path d="{p}" fill="none" {ln(2.6)}/>'
    return s


def torso_sentado(c):
    """Camiseta de quem está sentado: cintura, costas curvas, barra no quadril sobre o assento e dobra na virilha."""
    sw, hw, top = c['tw'], c['hw'], c['ty']
    C, Cd, Cl = c['roupa']
    nw, ww = c['pesw'] + 4, c.get('ww', hw - 6)
    p = (f'M{-nw} {top}C{-nw - 12} {top + 8} {-sw + 14} {top + 10} {-sw} {top + 26}C{-sw + 2} {top * .62:.0f} {-ww} {top * .3:.0f} {-ww + 2} -16'
         f'C{-ww} -6 {-ww - 2} 0 {-ww + 2} 8C-14 14 26 10 {ww + 12} 2C{ww + 6} -14 {ww - 2} -28 {ww} -52C{ww} {top * .55:.0f} {sw - 4} {top + 44} {sw} {top + 26}C{sw - 14} {top + 10} {nw + 12} {top + 8} {nw} {top}z')
    cid = _uid()
    fundo = round(c['short'][1] / 2 + 7)
    s = (f'<path d="M{-ww - 2} -14C{-ww - 12} {fundo - 6} {-ww + 12} {fundo + 3} {-ww + 50} {fundo}H{ww}V-10z" fill="{c["cor_short"]}"/><path d="M{-ww - 2} -14C{-ww - 12} {fundo - 6} {-ww + 12} {fundo + 3} {-ww + 50} {fundo}" fill="none" {ln(2.6)}/>'
         f'<clipPath id="{cid}"><path d="{p}"/></clipPath><path d="{p}" fill="{C}"/><g clip-path="url(#{cid})"><path d="M{-hw - 20} {top * .55:.0f}C{-hw + 20} {top * .4:.0f} {-hw + 18} -30 {-hw + 22} 20H{-hw - 20}z" fill="{Cd}" opacity=".7"/>')
    if c.get('listra'):
        s += f'<g transform="translate(12 {top + 62})"><path d="M0-15L4.4-4.6 15-4.6 6.6 2 9.6 12.6 0 6.4-9.6 12.6-6.6 2-15-4.6-4.4-4.6z" fill="{c["listra"]}" stroke="{Cd}" stroke-width="1.6" stroke-linejoin="round"/></g>'
    s += _avental(c, top, 12)
    s += (f'<path d="M{hw + 2} -12C{hw - 22} -2 {hw - 46} -2 -6 -6M{hw - 8} -30C{hw - 26} -20 {hw - 42} -18 12 -20" fill="none" stroke="{Cd}" stroke-width="3.2" stroke-linecap="round"/></g>'
          f'<path d="{p}" fill="none" {ln(2.6)}/>')
    return s


def torso_casaco(c):
    """Blusa clara por dentro e casaquinho aberto (Dona Rita, professora)."""
    sw, hw, top, hem = c['tw'], c['hw'], c['ty'], c['hem']
    C, Cd, Cl = c['roupa']
    b = c['blusa']
    p = f'M-22 {top}C{-sw + 10} {top + 2} {-sw - 2} {top + 10} {-sw - 4} {top + 26}C{-hw + 6} {top * .5:.0f} {-hw} {hem * -.3:.0f} {-hw - 8} {hem}C-20 {hem + 6} 20 {hem + 6} {hw + 8} {hem}C{hw} {hem * -.3:.0f} {hw - 6} {top * .5:.0f} {sw + 2} {top + 26}C{sw} {top + 10} {sw - 10} {top + 2} 22 {top}z'
    cid = _uid()
    s = f'<clipPath id="{cid}"><path d="{p}"/></clipPath><path d="{p}" fill="{C}"/><g clip-path="url(#{cid})">'
    s += f'<path d="M{-hw - 20} {top}H{-hw + 16}C{-hw + 4} {top * .5:.0f} {-hw + 10} 0 {-hw + 2} {hem + 10}H{-hw - 20}z" fill="{Cd}" opacity=".85"/>'
    s += f'<path d="M-14 {top - 2}L-2 {hem + 8}H36L22 {top - 2}z" fill="{b}" {ln(2.2)}/><path d="M-1 {top + 70}C10 {top + 76} 24 {top + 76} 32 {top + 68}" fill="none" stroke="#bdb49c" stroke-width="3"/></g>'
    s += f'<path d="{p}" fill="none" {ln(2.6)}/>'
    return s


def torso_regata(c):
    return torso_camiseta(c)


def _neck(c):
    sk, sd, _ = c['pele']
    x, y = c['pesc']
    w = c['pesw']
    gola = c['roupa'][2]
    return (f'<path d="M{x - w} {y + 26}L{x - w + 2} {y - 14}H{x + w - 2}L{x + w} {y + 26}C{x + w - 6} {y + 36} {x - w + 6} {y + 36} {x - w} {y + 26}z" fill="{sk}" {ln(2.4)}/>'
            f'<path d="M{x - w + 3} {y - 12}C{x - 4} {y + 6} {x + w - 6} {y + 2} {x + w - 3} {y - 12}z" fill="{sd}"/>'
            f'<path d="M{x - w - 3} {y + 22}C{x - w + 6} {y + 42} {x + w - 6} {y + 42} {x + w + 3} {y + 22}" fill="none" stroke="{gola}" stroke-width="6" stroke-linecap="round"/><path d="M{x - w - 5} {y + 25}C{x - w + 5} {y + 47} {x + w - 5} {y + 47} {x + w + 5} {y + 25}" fill="none" {ln(1.8)}/>')


def mochila_tras(c):
    t = c['ty']
    return (f'<path d="M-58 {t + 24}C-96 {t + 30} -102 {t + 120} -86 {t + 160}C-70 {t + 172} -44 {t + 168} -36 {t + 150}z" fill="#c8513a" {ln(2.6)}/>'
            f'<path d="M-84 {t + 104}C-66 {t + 96} -52 {t + 100} -42 {t + 104}L-44 {t + 150}C-56 {t + 160} -74 {t + 160} -84 {t + 150}z" fill="#a33f2c" {ln(2.2)}/>')


def mochila_frente(c):
    t = c['ty']
    return f'<path d="M-30 {t + 6}C-44 {t + 40} -46 {t + 78} -42 {t + 104}" fill="none" stroke="{L}" stroke-width="12" stroke-linecap="round"/><path d="M-30 {t + 6}C-44 {t + 40} -46 {t + 78} -42 {t + 104}" fill="none" stroke="#c8513a" stroke-width="8" stroke-linecap="round"/>'


_MENINO_ROUPA = ('#3f83a6', '#2f6a8a', '#7fb7cf')
CHARS = {
    'caio': dict(cranio='menino', k=.56, pele=('#c9915f', '#a87346', '#e0b083'), cabelo='cachos', cor_cabelo='#2b1f1d', cor_cabelo2='#54403a', cor_sobr='#2b1f1d', sobr=7, blush='#d9694f',
                 roupa=_MENINO_ROUPA, torso=torso_camiseta, tw=44, hw=46, ty=-166, hem=26, pesc=(5, -172), pesw=15, listra='#f0c23a',
                 quadril=262, ombroN=(-38, -146), ombroF=(36, -146), braco=(84, 78), wb=(15, 13, 11), manga=(.46, 27, 25), cor_manga='#3f83a6',
                 coxa=(16, 20), perna=(130, 124), wp=(25, 18, 14), short=(.54, 30, 28), cor_short='#5a6073', cor_shortD='#454a5b', pe=tenis('#d9d3c6', '#f3efe6', '#a33f2c'), mao=0.86),
    'rita': dict(cranio='mulher', k=.55, pele=('#bf8558', '#9c6840', '#d8a678'), cabelo='coque', cor_cabelo='#33231f', cor_cabelo2='#7a665e', cor_sobr='#33231f', sobr=5.5, brinco=True, rugas=True,
                 roupa=('#7f3f55', '#642f42', '#a95f77'), torso=torso_casaco, blusa='#efe6d2', tw=46, hw=44, ty=-204, hem=30, pesc=(5, -210), pesw=14,
                 quadril=345, ombroN=(-42, -180), ombroF=(40, -180), braco=(108, 100), wb=(18, 15, 12), manga=(1.0, 21, 19), cor_manga='#7f3f55',
                 coxa=(18, 22), perna=(170, 160), wp=(32, 24, 17), short=(1.0, 33, 21), cor_short='#39445f', cor_shortD='#2c3550', pe=sapatilha('#3a3236'), mao=0.92),
    'prof': dict(cranio='mulher', k=.54, pele=('#e9b98f', '#c98f68', '#f7d3ae'), cabelo='chanel', cor_cabelo='#6e3f26', cor_cabelo2='#9a6240', cor_sobr='#6e3f26', sobr=5.5, oculos=True,
                 roupa=('#2f7a6b', '#225e52', '#4fa08f'), torso=torso_casaco, blusa='#fbf6e8', tw=44, hw=42, ty=-198, hem=28, pesc=(5, -204), pesw=13,
                 quadril=335, ombroN=(-40, -174), ombroF=(38, -174), braco=(104, 96), wb=(17, 14, 11), manga=(1.0, 20, 18), cor_manga='#2f7a6b',
                 coxa=(18, 22), perna=(166, 154), wp=(30, 23, 15), short=(1.0, 33, 30), cor_short='#4b4e68', cor_shortD='#3a3d55', pe=sapatilha('#4a2f22'), mao=0.90),
    'pedreiro1': dict(cranio='homem', k=.58, pele=('#8e5a3a', '#6e4329', '#ad7650'), cabelo='capacete', cor_cabelo='#1e1614', cor_cabelo2='#efc23a', cor_sobr='#1e1614', sobr=6.5, barba=True,
                      roupa=('#d8d3c6', '#b5ae9f', '#efeae0'), torso=torso_camiseta, tw=60, hw=56, ty=-216, hem=28, pesc=(5, -222), pesw=20,
                      quadril=360, ombroN=(-54, -192), ombroF=(50, -192), braco=(112, 106), wb=(23, 19, 15), manga=(.42, 31, 29), cor_manga='#d8d3c6',
                      coxa=(20, 26), perna=(176, 166), wp=(36, 28, 21), short=(1.0, 37, 24), cor_short='#3a4a68', cor_shortD='#2c3852', pe=bota('#6b4a2f', '#2a211d'), mao=1.05),
    'pedreiro2': dict(cranio='homem', k=.57, pele=('#dba677', '#b98158', '#efc299'), cabelo='capacete', cor_cabelo='#3a2c28', cor_cabelo2='#e0672f', cor_sobr='#3a2c28', sobr=6.5, bigode=True,
                      roupa=('#c9602f', '#a54a22', '#e6845a'), torso=torso_camiseta, tw=64, hw=66, ty=-210, hem=30, pesc=(5, -216), pesw=21,
                      quadril=350, ombroN=(-56, -186), ombroF=(54, -186), braco=(110, 104), wb=(24, 20, 16), manga=(.42, 32, 30), cor_manga='#c9602f',
                      coxa=(22, 28), perna=(170, 162), wp=(38, 29, 22), short=(1.0, 38, 25), cor_short='#55504a', cor_shortD='#403c37', pe=bota('#3f3a36', '#1f1b1a'), mao=1.05),
    'pedreiro3': dict(cranio='homem', k=.55, pele=('#c98f62', '#a87346', '#e0b083'), cabelo='capacete', cor_cabelo='#231a18', cor_cabelo2='#f3f1ea', cor_sobr='#231a18', sobr=6,
                      roupa=('#3f7f55', '#2f6642', '#68a97f'), torso=torso_camiseta, tw=54, hw=50, ty=-208, hem=28, pesc=(5, -214), pesw=17,
                      quadril=350, ombroN=(-50, -184), ombroF=(46, -184), braco=(108, 102), wb=(21, 17, 14), manga=(.42, 29, 27), cor_manga='#3f7f55',
                      coxa=(19, 25), perna=(172, 162), wp=(34, 26, 19), short=(1.0, 35, 23), cor_short='#3a4a68', cor_shortD='#2c3852', pe=bota('#6b4a2f', '#2a211d'), mao=1.00),
    'vizinho': dict(cranio='homem', k=.55, pele=('#a56c44', '#83522f', '#c48e62'), cabelo='curto', cor_cabelo='#1e1614', cor_cabelo2='#463632', cor_sobr='#1e1614', sobr=6,
                    roupa=('#6b6f3f', '#54582f', '#8f9458'), torso=torso_camiseta, tw=50, hw=46, ty=-200, hem=26, pesc=(5, -206), pesw=16,
                    quadril=335, ombroN=(-46, -176), ombroF=(44, -176), braco=(104, 98), wb=(19, 16, 13), manga=(.42, 27, 25), cor_manga='#6b6f3f',
                    coxa=(18, 23), perna=(166, 156), wp=(32, 25, 18), short=(1.0, 33, 22), cor_short='#2f3a55', cor_shortD='#242d44', pe=tenis('#e6e2d8', '#fbf8f0', '#2f6fa8'), mao=0.96),
    'crianca1': dict(cranio='menino', k=.5, pele=('#e3b088', '#c08a62', '#f4cfa8'), cabelo='curto', cor_cabelo='#7a4a26', cor_cabelo2='#a56c3c', cor_sobr='#7a4a26', sobr=6, blush='#e0806a',
                     roupa=('#f0f0ea', '#cfcfc6', '#fff'), torso=torso_camiseta, tw=38, hw=38, ty=-150, hem=22, pesc=(5, -156), pesw=12, listra='#2f6fa8',
                     quadril=240, ombroN=(-33, -132), ombroF=(32, -132), braco=(76, 70), wb=(13, 11, 10), manga=(.44, 22, 21), cor_manga='#f0f0ea',
                     coxa=(14, 18), perna=(120, 112), wp=(22, 16, 13), short=(.5, 27, 25), cor_short='#2f3f6a', cor_shortD='#233056', pe=tenis('#30333d', '#e6e2d8', '#e6e2d8'), mao=0.80),
    'crianca2': dict(cranio='mulher', k=.5, pele=('#7c4c30', '#5f3822', '#9a6a48'), cabelo='chanel', cor_cabelo='#1c1412', cor_cabelo2='#403030', cor_sobr='#1c1412', sobr=5,
                     roupa=('#f0f0ea', '#cfcfc6', '#fff'), torso=torso_camiseta, tw=36, hw=36, ty=-146, hem=22, pesc=(5, -152), pesw=11, listra='#2f6fa8',
                     quadril=232, ombroN=(-32, -128), ombroF=(30, -128), braco=(72, 68), wb=(12, 11, 9), manga=(.44, 21, 20), cor_manga='#f0f0ea',
                     coxa=(14, 18), perna=(116, 108), wp=(21, 15, 12), short=(.5, 26, 24), cor_short='#2f3f6a', cor_shortD='#233056', pe=tenis('#b83f58', '#e6e2d8', '#e6e2d8'), mao=0.80),
}


_JEANS, _JEANSD = '#39445f', '#2c3550'
CHARS['ze'] = dict(cranio='homem', k=.56, pele=('#e9b98f', '#c98f68', '#f7d3ae'), cabelo='curto', cor_cabelo='#3a2c28', cor_cabelo2='#5a4840', cor_sobr='#3a2c28', sobr=6.5,
                   roupa=('#b4553f', '#8f3f30', '#cc6c55'), torso=torso_camiseta, tw=66, ww=48, hw=48, ty=-206, hem=12, pesc=(5, -212), pesw=17,
                   quadril=350, ombroN=(-58, -182), ombroF=(54, -182), braco=(124, 116), wb=(25, 20, 16), manga=(.4, 39, 31), cor_manga='#b4553f',
                   coxa=(19, 24), perna=(176, 164), wp=(35, 27, 20), short=(1.0, 37, 22), cor_short=_JEANS, cor_shortD=_JEANSD, pe=tenis('#e6e2d8', '#fbf8f0', '#b4553f'), mao=1.16)
CHARS['bia'] = dict(cranio='mulher', k=.54, pele=('#b87a4e', '#96603a', '#d09a6c'), cabelo='rabo', cor_cabelo='#2a1a16', cor_cabelo2='#5a3f36', cor_sobr='#2a1a16', sobr=5.5, brinco=True, blush='#c9564a',
                    roupa=('#f4efe2', '#d6cfbc', '#fff'), torso=torso_camiseta, avental='#2f7a5a', tw=54, ww=37, hw=44, ty=-192, hem=14, pesc=(5, -198), pesw=13,
                    quadril=328, ombroN=(-47, -170), ombroF=(44, -170), braco=(112, 104), wb=(20, 16, 13), manga=(.38, 31, 25), cor_manga='#f4efe2',
                    coxa=(17, 22), perna=(166, 154), wp=(33, 24, 17), short=(1.0, 34, 22), cor_short='#3a3438', cor_shortD='#2c272b', pe=sapatilha('#2a2428'), mao=.98)
CHARS['chefe'] = dict(cranio='homem', k=.6, pele=('#d9a074', '#b47c54', '#efc299'), cabelo='curto', cor_cabelo='#2b2523', cor_cabelo2='#6a6460', cor_sobr='#1e1a18', sobr=10, bigode=True,
                      roupa=('#3f4a5c', '#2f3848', '#6a7890'), torso=torso_camiseta, tw=74, ww=70, hw=70, ty=-214, hem=30, pesc=(5, -220), pesw=24,
                      quadril=350, ombroN=(-64, -188), ombroF=(60, -188), braco=(122, 114), wb=(30, 25, 18), manga=(.42, 42, 36), cor_manga='#3f4a5c',
                      coxa=(24, 30), perna=(172, 162), wp=(42, 32, 24), short=(1.0, 44, 26), cor_short='#2b2f3a', cor_shortD='#22252e', pe=bota('#2a2523', '#141211'), mao=1.2)
CHARS['feirante'] = dict(CHARS['pedreiro3'], cabelo='curto', roupa=('#d8a23a', '#b4842a', '#efc466'), cor_manga='#d8a23a', cor_short='#4a4034', cor_shortD='#3a3228', bigode=True, ww=46, tw=58, mao=1.1)
CHARS['cliente'] = dict(CHARS['vizinho'], roupa=('#6a4f8a', '#533c70', '#8f73b0'), cor_manga='#6a4f8a', short=(.56, 34, 32), cor_short='#7a7a7a', cor_shortD='#606060', ww=42, tw=56, mao=1.08)
for _n in ('caio', 'crianca1', 'crianca2'):
    CHARS[_n]['tw'] += 4
for _c in CHARS.values():
    _c['wb'] = tuple(round(x * 1.16, 1) for x in _c['wb'])


def _confere_bracos():
    """Regra: pendurado, o punho não passa do meio da coxa."""
    for n, c in CHARS.items():
        ombro_y = c['quadril'] - c['ombroN'][1]
        meia_coxa = c['quadril'] - c['perna'][0] / 2
        assert sum(c['braco']) * .97 <= ombro_y - meia_coxa + c['quadril'] and ombro_y - sum(c['braco']) * .97 >= meia_coxa, n


_confere_bracos()


def _registrar_tipos():
    from . import boneco
    CRANIO.update(boneco.CRANIO_EXTRA)
    NARIZ.update(boneco.NARIZ_EXTRA)


def retrato(nome):
    """Cabeça solta, para a caixa de diálogo e o celular."""
    return f'<g transform="scale(.46) translate(-352 -470)">{cabeca(CHARS[nome])}</g>'


def ator_svg(nome: str, itens_mao: dict[str, str], opc: dict | None = None):
    """Devolve (tras, topo, dados): corpo do ator e grupo dos braços que passam sobre a camada da frente."""
    c = CHARS[nome]
    opc = opc or {}
    sk, sd, _ = c['pele']
    M = maos(sk, sd)
    mao_g = lambda lado: ''.join(
        f'<g data-m="{k}" display="none" transform="scale({c["mao"]})">{b}</g>' for k, (b, _f) in M.items())
    mao_f = lambda lado: ''.join(
        f'<g data-m="{k}" display="none" transform="scale({c["mao"]})">{f}</g>' for k, (_b, f) in M.items())
    props = lambda lado: ''.join(f'<g data-p="{k}" display="none">{v}</g>' for k, v in itens_mao.items())
    braco = lambda lado: (f'<g class="b{lado}"><g class="m{lado}">{mao_g(lado)}{props(lado)}{mao_f(lado)}</g>'
                          f'<path class="pS" fill="{sk}"/><path class="lS" fill="none" {ln(2.4)}/>'
                          f'<path class="pM" fill="{c["cor_manga"]}"/><path class="lM" fill="none" {ln(2.4)}/></g>')
    perna = lambda lado, cor, corD: (f'<g class="l{lado}"><path class="pS" fill="{sk}"/><path class="lS" fill="none" {ln(2.4)}/>'
                                     f'<path class="pM" fill="{corD if lado == "F" else cor}"/><path class="lM" fill="none" {ln(2.4)}/><g class="f{lado}">{c["pe"]}</g></g>')
    tr = f'<g class="tP">{c["torso"](c)}</g>'
    if c['torso'] is torso_camiseta:
        tr += f'<g class="tS" display="none">{torso_sentado(c)}</g>'
    extra_tras = extra_frente = ''
    if opc.get('mochila'):
        extra_tras, extra_frente = mochila_tras(c), mochila_frente(c)
    pend = opc.get('peito', '')
    extra_tras = opc.get('costas', '') + extra_tras
    na_cabeca = opc.get('cabeca', '')
    corpo = (f'<ellipse class="sombra" cx="0" cy="4" rx="{c["tw"] + 34}" ry="13" fill="#140e18" opacity=".38" filter="url(#b6)"/>'
             f'<g class="bFslot">{braco("F")}</g>{perna("F", c["cor_short"], c["cor_shortD"])}{perna("N", c["cor_short"], c["cor_shortD"])}'
             f'<path class="uF" fill="none" {ln(4.8)}/><path class="uN" fill="none" {ln(4.8)}/>'
             f'<g class="tor">{extra_tras}{_neck(c)}{tr}{extra_frente}{pend}</g>'
             f'<g class="cab"><g transform="scale({c["k"] * c.get('cab_esc', (1, 1))[0]:.3f} {c["k"] * c.get('cab_esc', (1, 1))[1]:.3f}) translate(-345 -570)">{cabeca(c)}{na_cabeca}</g></g>'
             f'<g class="bNslot">{braco("N")}</g>')
    dados = {k: c[k] for k in ('quadril', 'ombroN', 'ombroF', 'braco', 'wb', 'manga', 'coxa', 'perna', 'wp', 'short', 'pesc', 'k')}
    return corpo, dados


# ---------- gato Tião: mesmo gato do quadro aprovado
CINZA, CINZA2 = '#b8a292', '#e7dcd0'


def gato_sentado():
    return f'''<ellipse cx="0" cy="116" rx="96" ry="15" fill="#140e18" opacity=".42" filter="url(#b6)"/>
<g class="rabo"><path d="M54 108C104 102 104 42 76 28" fill="none" stroke="{L}" stroke-width="18" stroke-linecap="round"/><path d="M54 108C104 102 104 42 76 28" fill="none" stroke="#a79184" stroke-width="12" stroke-linecap="round"/></g>
<path d="M-60 112C-68 44-40-4 0-4C44-4 72 46 62 112z" fill="{CINZA}" {ln(3)}/><path d="M-20 112C-22 72-12 40 4 32C20 42 26 80 22 112z" fill="{CINZA2}"/>
<path d="M-44 112q10-16 30 0M18 112q18-16 34 0" fill="{CINZA2}" {ln(2.6)}/>
<g class="gcab"><path d="M-44-48L-50-92L-16-74M48-48L54-92L20-74" fill="{CINZA}" {ln(3)}/><path d="M-40-64L-43-82L-26-72M44-64L47-82L30-72" fill="#e8a6a6"/>
<path d="M-54-32C-56-68-28-82 2-82C32-82 60-68 58-32C56 0 32 16 2 16C-28 16-52 0-54-32z" fill="{CINZA}" {ln(3)}/>
<path d="M-20-80l6 16M2-82v18M24-80l-6 16" stroke="#8f7b6e" stroke-width="5" stroke-linecap="round"/>
<ellipse cx="-22" cy="-36" rx="16" ry="19" fill="#fff" {ln(2.6)}/><ellipse cx="26" cy="-36" rx="16" ry="19" fill="#fff" {ln(2.6)}/><g class="golho"><circle cx="-24" cy="-38" r="8" fill="{L}"/><circle cx="24" cy="-38" r="8" fill="{L}"/><circle cx="-27" cy="-42" r="3" fill="#fff"/><circle cx="21" cy="-42" r="3" fill="#fff"/></g>
<path d="M-4-12h12l-6 7z" fill="#d8767a" {ln(2)}/><path d="M2-5c-2 7-10 8-14 4M2-5c2 7 10 8 14 4" fill="none" {ln(2.4)}/><path d="M-60-16l-28-4M-60-4l-28 6M64-16l28-4M64-4l28 6" {ln(2)}/>
<g class="gpisca" display="none"><ellipse cx="-22" cy="-36" rx="17" ry="20" fill="{CINZA}"/><ellipse cx="26" cy="-36" rx="17" ry="20" fill="{CINZA}"/><path d="M-38-34q16 8 32 0M10-34q16 8 32 0" fill="none" {ln(3)}/></g></g>'''


def gato_correndo():
    """Vista de perfil, olhando para -x, em disparada (pelo arrepiado)."""
    return f'''<ellipse cx="0" cy="104" rx="120" ry="12" fill="#140e18" opacity=".35" filter="url(#b6)"/>
<g><path d="M92 34C140 18 150-20 138-52" fill="none" stroke="{L}" stroke-width="20" stroke-linecap="round"/><path d="M92 34C140 18 150-20 138-52" fill="none" stroke="#a79184" stroke-width="14" stroke-linecap="round"/><path d="M122-52l8-16M138-52V-72M152-46l10-14" {ln(3)}/></g>
<path d="M104 62C130 74 150 92 152 104L126 104C110 96 88 88 74 80z" fill="{CINZA}" {ln(3)}/>
<path d="M-74 66C-100 74-132 86-148 100L-124 106C-104 100-76 92-52 84z" fill="{CINZA}" {ln(3)}/>
<path d="M-82 44C-60 6 60 0 108 32C118 56 96 84 62 86C10 92-52 90-82 72z" fill="{CINZA}" {ln(3)}/>
<path d="M-40 18l-6-16M-10 12l-4-16M20 12l2-16M52 16l6-16M80 24l10-14" {ln(3)}/>
<path d="M-60 84C-28 70 36 70 76 84C30 92-24 92-60 84z" fill="{CINZA2}"/>
<g transform="translate(-92 16)"><path d="M-30-40L-36-76L-6-60M34-44L42-80L10-62" fill="{CINZA}" {ln(3)}/><path d="M-50-14C-52-50-24-62 2-62C30-62 54-46 52-14C50 14 28 28 0 28C-26 28-48 14-50-14z" fill="{CINZA}" {ln(3)}/>
<ellipse cx="-20" cy="-18" rx="17" ry="20" fill="#fff" {ln(2.6)}/><ellipse cx="22" cy="-18" rx="15" ry="19" fill="#fff" {ln(2.6)}/><circle cx="-26" cy="-18" r="5" fill="{L}"/><circle cx="16" cy="-18" r="5" fill="{L}"/>
<path d="M-12 8C-6 2 8 2 14 8C8 18-6 18-12 8z" fill="#5a1f28" {ln(2.4)}/><path d="M-54 2l-26-4M-54 12l-26 6" {ln(2)}/></g>'''
