"""Personagens gerados por parâmetro: idade, corpo, cabeça, rosto, cabelo, roupa e profissão.

registrar(id, params) cria uma entrada em personagens.CHARS com o mesmo braço, mão e ombro do elenco aprovado.
sortear(rng, usados) monta uma combinação nova; assinatura(p) identifica a aparência para o registro entre séries.
"""
from __future__ import annotations

import colorsys
import random
from typing import Any

from . import personagens as P
from .base import L, ln

IDADES = ("crianca", "adolescente", "jovem", "adulto", "meia_idade", "idoso")
CORPOS = ("magro", "medio", "gordo", "baixo", "alto", "curvado", "barrigudo", "forte")
PELES = (("#f2cfae", "#d3a582", "#fbe3c9"), ("#e9b98f", "#c98f68", "#f7d3ae"), ("#d9a074", "#b47c54", "#efc299"), ("#c98f62", "#a87346", "#e0b083"),
         ("#b87a4e", "#96603a", "#d09a6c"), ("#a56c44", "#83522f", "#c48e62"), ("#8e5a3a", "#6e4329", "#ad7650"), ("#6f4530", "#54321f", "#8c5f47"))
CABELOS = ("careca", "calvo", "curto", "cachos", "black", "coque", "rabo", "chanel", "topete", "longo", "franja", "trancas", "grisalho_lado")
CORES_CABELO = (("#2b1f1d", "#54403a"), ("#3a2c28", "#5a4840"), ("#6e3f26", "#9a6240"), ("#b08a4a", "#d8b878"), ("#8d8d8d", "#bdbdbd"), ("#e6e2d8", "#ffffff"), ("#7a2f22", "#a8503a"))
NARIZES = ("menino", "mulher", "homem", "batata", "adunco", "longo", "pontudo", "pequeno")
CRANIOS = ("homem", "mulher", "menino", "ovo", "quadrado", "largo", "fino", "pera")
ORELHAS = ("normal", "pequena", "grande", "abano")
DENTES = ("normal", "dentuco", "banguela", "aparelho")
SOBRANCELHAS = ("normal", "fina", "grossa", "monocelha")
BARBAS = ("", "", "bigode", "cavanhaque", "cheia", "rala")
ROUPAS = ("camiseta", "regata", "camisa", "casaco", "jaleco", "uniforme", "terno", "vestido", "avental", "macacao", "polo", "listrada")
PROFISSOES = {"costureira": ("avental", "#7a4a7a"), "barbeiro": ("avental", "#2f3f6a"), "medico": ("jaleco", "#fbfbf6"), "enfermeira": ("jaleco", "#bfe0dc"), "cozinheiro": ("avental", "#fbfbf6"),
              "motorista": ("camisa", "#3f5f8a"), "policial": ("uniforme", "#2a3a5a"), "professor": ("casaco", "#6b5a3a"), "advogado": ("terno", "#2b2f3a"), "porteiro": ("uniforme", "#4a5a4a"),
              "vendedor": ("polo", "#c8513a"), "faxineira": ("avental", "#3f83a6"), "mecanico": ("macacao", "#3a4a68"), "personal": ("regata", "#e0502f"), "padre": ("terno", "#1e1e22")}
CRANIO_EXTRA = {
    "ovo": "M284 450C282 400 312 366 352 366C392 366 420 402 420 456C420 500 408 534 388 548C370 560 346 560 328 548C302 532 286 494 284 450z",
    "quadrado": "M272 410C272 386 296 372 330 372H392C416 372 430 390 430 416V500C430 532 414 556 384 558H324C294 556 276 534 274 502z",
    "largo": "M262 470C258 410 298 376 350 376C404 376 444 410 442 470C442 512 420 548 384 556C352 562 316 560 292 540C272 524 264 500 262 470z",
    "fino": "M296 460C294 404 318 368 352 368C386 368 408 404 408 460C408 506 398 548 374 566C360 574 344 574 332 564C308 546 298 506 296 460z",
    "pera": "M300 440C300 396 322 372 352 372C384 372 404 396 404 440C430 470 438 510 416 538C396 562 322 568 296 540C270 512 276 468 300 440z",
}
NARIZ_EXTRA = {
    "batata": "M376 478C366 492 372 516 398 518C424 520 434 500 424 486C416 476 404 480 398 476",
    "adunco": "M384 470C400 482 418 502 412 514C404 524 390 516 384 510",
    "longo": "M384 472C392 500 420 524 438 520C446 516 442 506 430 504C416 500 408 488 402 476",
    "pontudo": "M384 476C396 490 422 500 436 500C424 508 402 510 390 504",
    "pequeno": "M394 492C392 500 398 504 404 502",
}


def _cor(rng: random.Random) -> str:
    h, s, l = rng.random(), rng.uniform(.2, .36), rng.uniform(.36, .52)
    return "#%02x%02x%02x" % tuple(int(x * 255) for x in colorsys.hls_to_rgb(h, l, s))


def cor_hue(h: float) -> str:
    return "#%02x%02x%02x" % tuple(int(x * 255) for x in colorsys.hls_to_rgb(h % 1, .44, .32))


def _esc(c: str, k: float) -> str:
    r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(x * k))) for x in (r, g, b))


def assinatura(p: dict[str, Any]) -> str:
    return "|".join(str(p.get(k)) for k in ("cranio", "nariz", "cabelo", "barba", "corpo", "pele"))


def sortear(rng: random.Random, usados: set[str] | None = None, **fixo: Any) -> dict[str, Any]:
    """Combinação nova: fixo vem da bíblia (idade, corpo, sexo...); o resto é sorteado sem repetir assinatura."""
    usados = usados if usados is not None else set()
    p: dict[str, Any] = {}
    for _ in range(400):
        sexo = fixo.get("sexo") or rng.choice(("f", "m"))
        idade = fixo.get("idade") or rng.choice(IDADES[2:])
        cab = fixo.get("cabelo") or rng.choice([c for c in CABELOS if not (sexo == "f" and c in ("careca", "calvo", "grisalho_lado")) and not (sexo == "m" and c in ("coque", "chanel", "longo", "trancas", "rabo")) and not (sexo == "f" and c in ("curto", "franja", "topete"))])
        p = dict(sexo=sexo, idade=idade, corpo=fixo.get("corpo") or rng.choice([x for x in CORPOS if not (x == "curvado" and idade != "idoso") and not (idade == "crianca" and x in ("alto", "forte", "barrigudo"))]), pele=int(fixo.get("pele") if fixo.get("pele") is not None else rng.randrange(len(PELES))),
                 cabelo=cab, cor_cabelo=int(fixo.get("cor_cabelo") if fixo.get("cor_cabelo") is not None else (rng.choice((4, 5)) if idade == "idoso" else rng.choice((0, 1, 2, 3, 6)) if idade in ("crianca", "adolescente", "jovem") else rng.randrange(len(CORES_CABELO)))),
                 cranio=fixo.get("cranio") or rng.choice(CRANIOS), nariz=fixo.get("nariz") or rng.choice(NARIZES), orelha=fixo.get("orelha") or rng.choice(ORELHAS),
                 dentes=fixo.get("dentes") or rng.choice(DENTES), sobrancelha=fixo.get("sobrancelha") or rng.choice(SOBRANCELHAS),
                 barba=fixo.get("barba") if fixo.get("barba") is not None else ("" if sexo == "f" or idade in ("crianca", "adolescente") else rng.choice(BARBAS)),
                 feio=bool(fixo.get("feio")), oculos=bool(fixo.get("oculos")) if fixo.get("oculos") is not None else rng.random() < .28, roupa=(fixo.get("roupa") if fixo.get("roupa") and not (fixo.get("roupa") == "vestido" and sexo == "m") else rng.choice([r for r in ROUPAS if r != "terno" and not (r == "vestido" and sexo == "m")])),
                 cor_roupa=fixo.get("cor_roupa") or _cor(rng), bermuda=fixo.get("bermuda") if fixo.get("bermuda") is not None else rng.random() < .3)
        if assinatura(p) not in usados:
            break
    usados.add(assinatura(p))
    return p


def _estampa(roupa: str, top: int, hem: int, cor: str) -> str:
    d = _esc(cor, .72)
    if roupa == "camisa":
        return f'<path d="M4 {top + 8}V{hem}" {ln(1.8, d)}/>' + "".join(f'<circle cx="9" cy="{top + 34 + i * 38}" r="2.6" fill="{d}"/>' for i in range(4))
    if roupa == "terno":
        return f'<path d="M-16 {top + 2}L4 {top + 74}L24 {top + 2}z" fill="#f4f1e6" {ln(1.8)}/><path d="M0 {top + 18}H8L12 {top + 66}L4 {top + 80}L-4 {top + 66}z" fill="#a33f2c" {ln(1.6)}/>'
    if roupa == "uniforme":
        return f'<rect x="-34" y="{top + 44}" width="24" height="16" rx="2" fill="{d}" {ln(1.4)}/><circle cx="26" cy="{top + 52}" r="7" fill="#e0b23c" {ln(1.4)}/>'
    if roupa == "jaleco":
        return f'<path d="M4 {top + 8}V{hem}" {ln(1.8, "#b9b9b0")}/><rect x="-34" y="{top + 56}" width="24" height="24" fill="none" {ln(1.6, "#b9b9b0")}/>'
    if roupa == "macacao":
        return f'<path d="M-22 {top}V{top + 66}M30 {top}V{top + 66}" stroke="{d}" stroke-width="12"/><rect x="-26" y="{top + 62}" width="60" height="40" rx="3" fill="{d}"/>'
    if roupa == "polo":
        return f'<path d="M-16 {top + 2}L4 {top + 34}L24 {top + 2}" fill="none" {ln(2)}/><rect x="-6" y="{top + 58}" width="22" height="8" fill="#fff" opacity=".8"/>'
    if roupa == "listrada":
        return "".join(f'<rect x="-100" y="{y}" width="200" height="12" fill="{d}"/>' for y in range(top + 30, hem, 30))
    if roupa == "vestido":
        return f'<path d="M-60 {top * .28:.0f}H64" {ln(2, d)}/>' + "".join(f'<circle cx="{x}" cy="{y}" r="4" fill="#fff" opacity=".7"/>' for x, y in ((-30, top + 60), (20, top + 96), (-14, -6), (30, 36), (-34, 62), (10, 96)))
    return ""


def _rosto(p: dict[str, Any], c: dict[str, Any]) -> str:
    x = ""
    if p.get("dentes") == "dentuco":
        x += f'<path d="M374 538h10v15h-10zM385 538h10v15h-10z" fill="#fbfaf2" {ln(2)}/>'
    if p.get("dentes") == "banguela":
        x += f'<rect x="372" y="536" width="9" height="11" fill="#fbfaf2" {ln(1.6)}/>'
    if p.get("dentes") == "aparelho":
        x += f'<path d="M362 536h36" stroke="#b8bcc4" stroke-width="5"/>' + "".join(f'<rect x="{v}" y="533" width="4" height="6" fill="#7a8088"/>' for v in range(364, 398, 8))
    if p.get("sobrancelha") == "monocelha":
        x += f'<path d="M370 436Q379 430 388 436" fill="none" stroke="{c["cor_sobr"]}" stroke-width="{c["sobr"]}" stroke-linecap="round"/>'
    b = p.get("barba")
    cc = c["cor_cabelo"]
    if b == "cavanhaque":
        x += f'<path d="M362 544C368 566 392 566 400 544C392 552 370 552 362 544z" fill="{cc}" {ln(2.2)}/>'
    if b == "cheia":
        x += f'<path d="M282 494C292 540 320 568 348 570C384 572 418 548 428 500C414 520 400 516 384 514C366 516 340 524 320 516C302 510 292 502 282 494z" fill="{cc}" {ln(2.4)}/>'
    if b == "rala":
        x += "".join(f'<circle cx="{a}" cy="{d}" r="2" fill="{cc}"/>' for a, d in ((330, 530), (346, 540), (362, 546), (380, 548), (396, 542), (340, 524), (372, 538), (410, 526)))
    return x


def construir(p: dict[str, Any]) -> dict[str, Any]:
    age = p.get("idade", "adulto")
    corpo = p.get("corpo", "medio")
    H = {"crianca": .68, "adolescente": .88, "jovem": 1.0, "adulto": 1.0, "meia_idade": .98, "idoso": .93}[age] * (.9 if p.get("sexo") == "f" and age not in ("crianca",) else 1)
    H *= {"baixo": .84, "alto": 1.14}.get(corpo, 1)
    G = {"magro": .78, "medio": 1, "gordo": 1.34, "baixo": 1.06, "alto": .94, "curvado": .9, "barrigudo": 1.08, "forte": 1.2}[corpo] * (.8 if age == "crianca" else .9 if age == "adolescente" else 1)
    if p.get("sexo") == "f":
        G *= .92
    q = round(345 * H)
    ty = -round(.59 * q)
    perna = (round(.505 * q), round(.47 * q))
    tw, ww, hw = round(64 * G), round(47 * G), round(47 * G)
    if corpo == "barrigudo":
        ww, hw = round(64 * G), round(56 * G)
    if corpo == "gordo":
        ww = round(72 * G * .9)
    oy = ty + 24
    bra = (abs(oy) + perna[0] / 2) * .8
    braco = (round(bra * .52), round(bra * .48))
    wb0 = 21 * (G ** .7) * H ** .5
    cor = p.get("cor_roupa", "#b4553f")
    roupa = p.get("roupa", "camiseta")
    longa = roupa in ("casaco", "jaleco", "terno", "macacao", "camisa")
    skin = PELES[int(p.get("pele", 1))]
    cc, cc2 = CORES_CABELO[int(p.get("cor_cabelo", 0))]
    hem = 150 if roupa == "vestido" else 12
    bermuda = p.get("bermuda") and roupa not in ("terno", "macacao", "vestido") or age == "crianca"
    corp = _esc(cor, .66) if roupa != "vestido" else skin[0]
    calca = {"vestido": skin[0], "macacao": cor, "terno": cor}.get(roupa) or ("#5a6073" if bermuda else "#39445f" if int(sum(map(ord, cor))) % 2 else "#4a4034")
    c: dict[str, Any] = dict(nariz=p.get("nariz"), cranio=p.get("cranio", "homem"), k=.56 if age != "crianca" else .6, pele=skin, cabelo=p.get("cabelo", "curto"), cor_cabelo=cc, cor_cabelo2=cc2, cor_sobr=cc if p.get("cabelo") not in ("careca",) else "#3a2c28",
                             sobr={"fina": 4, "grossa": 10, "monocelha": 9}.get(p.get("sobrancelha"), 6), blush="#d9694f" if p.get("sexo") == "f" or age == "crianca" else None,
                             roupa=(cor, _esc(cor, .78), _esc(cor, 1.24)), torso=P.torso_camiseta, tw=tw, ww=ww, hw=hw, ty=ty, hem=hem, pesc=(5, ty - 6), pesw=round(16 * G ** .6), quadril=q,
                             ombroN=(-round(tw * .9), oy), ombroF=(round(tw * .86), oy), braco=braco, wb=(round(wb0 * 1.16, 1), round(wb0 * .92, 1), round(wb0 * .74, 1)),
                             manga=(1.0 if longa else .4, round(wb0 * 1.9), round(wb0 * 1.28)) if roupa != "regata" else (.1, round(wb0 * 1.3), round(wb0 * 1.2)), cor_manga=cor,
                             coxa=(round(19 * G), round(24 * G)), perna=perna, wp=(round(35 * G), round(27 * G), round(20 * G ** .7)), short=(.56, round(38 * G), round(32 * G)) if bermuda else (1.0, round(37 * G), round(22 * G)) if roupa != "vestido" else (.02, 30, 30),
                             cor_short=calca, cor_shortD=_esc(calca, .78), pe=P.tenis("#d9d3c6", "#f3efe6", cor) if age in ("crianca", "adolescente", "jovem") or bermuda else (P.sapatilha(_esc(cor, .5)) if p.get("sexo") == "f" else P.bota(_esc(cor, .5), "#241c22")),
                             mao=round(1.16 * H ** .8 * (G ** .25), 2), curva=20 if corpo == "curvado" else 12 if age == "idoso" and int(sum(map(ord, p.get("cranio", "a")))) % 2 else 0,
                             orelha={"pequena": (8, 14), "grande": (15, 25), "abano": (22, 28)}.get(p.get("orelha"), (11, 19)), cab_esc=(1.06, 1.0) if corpo in ("gordo", "barrigudo") else (1, 1),
                             estampa=_estampa(roupa, ty, hem, cor), rugas=age in ("meia_idade", "idoso"), oculos=bool(p.get("oculos")), bigode=p.get("barba") == "bigode")
    if roupa == "avental":
        c["avental"] = _esc(cor, .85)
        c["roupa"] = ("#efe9db", "#d3ccba", "#fff")
        c["cor_manga"] = "#efe9db"
    if p.get("barba") == "cheia":
        c["barba"] = False
    if p.get("feio"):
        c["nariz_esc"] = 1.45
        c["orelha"] = (26, 31)
        c["cab_esc"] = (1.12, 1.04)
    c["extra_svg"] = _rosto(p, c)
    return c


def registrar(ident: str, p: dict[str, Any]) -> str:
    c = construir(p)
    c.setdefault("cor_shortD", c["cor_short"])
    P.CHARS[ident] = c
    return ident


def descrever(p: dict[str, Any]) -> str:
    return f'{p.get("idade")}, {p.get("corpo")}, cabelo {p.get("cabelo")}, nariz {p.get("nariz")}, roupa {p.get("roupa")}'
