"""Biblioteca de objetos. Todo objeto: caixa 200x200, base no meio embaixo; na tela vira <g> com origem no ponto de apoio.
O que faltar o LLM desenha em SVG; sanitizar() só deixa formas simples, e a biblioteca cresce em data/story/quadro_objetos.json.
"""
from __future__ import annotations

import json
import re
import threading
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .base import L, ln

_lock = threading.Lock()


def plain(t: Any) -> str:
    return unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower().strip()


def _o(s: str) -> str:
    return f'<g transform="translate(-100 -200)">{s}</g>'


def _maquina():
    return _o(f'''<rect x="16" y="160" width="172" height="26" rx="4" fill="#6e4a30" {ln(3)}/><path d="M30 160V128H70V70C70 44 90 34 118 34H164C180 34 188 46 188 62V96C188 108 178 112 168 112H156V132H176V160z" fill="#2b2f3a" {ln(3.4)}/>
<path d="M92 112H150C156 112 158 116 158 122V128H92z" fill="#f3efe6" {ln(2.4)}/><path d="M82 70C100 58 150 58 176 68" fill="none" stroke="#d8b24a" stroke-width="5"/><text x="128" y="96" text-anchor="middle" font-family="Georgia" font-style="italic" font-size="15" fill="#d8b24a">Lidia</text>
<g data-vida="y:5:18:0"><rect x="42" y="128" width="8" height="26" fill="#d8d8d0" {ln(1.6)}/><path d="M46 154v12" {ln(2)}/></g><circle cx="182" cy="84" r="16" fill="#b8bcc4" {ln(3)}/><rect x="104" y="22" width="16" height="16" rx="3" fill="#c8513a" {ln(2)}/><path d="M112 22V12" {ln(2.4)}/><path d="M112 14C80 16 60 40 46 128" fill="none" stroke="#c8513a" stroke-width="1.6"/><path d="M30 186L24 196M176 186L182 196" {ln(5)}/>''')


def _vestido(cor="#d84a6a", cor2="#a83050"):
    return _o(f'''<path d="M100 14C96 4 110 0 112 8" fill="none" {ln(2.6)}/><path d="M100 18L62 30L74 38H126L138 30z" fill="#b98347" {ln(2.4)}/><path d="M78 34C80 48 84 56 86 60C70 92 44 150 26 192H174C156 150 130 92 114 60C116 56 120 48 122 34C112 44 88 44 78 34z" fill="{cor}" {ln(3)}/>
<path d="M86 60C94 66 106 66 114 60" fill="none" stroke="{cor2}" stroke-width="4"/><path d="M78 110C72 140 60 170 54 190M122 110C128 140 140 170 146 190M100 80V190" fill="none" stroke="{cor2}" stroke-width="3"/>{"".join(f'<circle cx="{x}" cy="{y}" r="4" fill="#fff"/>' for x, y in ((80, 130), (120, 124), (64, 170), (100, 152), (136, 172), (100, 104)))}''')


def _simples(s):
    return lambda: _o(s)


C = {"f": 'fill="', }
BASE: dict[str, Any] = {
    "maquina de costura": dict(f=_maquina, tam=1.0, alias=["maquina de costura", "maquina", "maquininha"], pega=False),
    "vestido": dict(f=_vestido, tam=1.0, alias=["vestido", "vestidinho", "saia caipira"]),
    "tesoura": dict(f=_simples(f'<path d="M60 30L120 130M140 30L80 130" {ln(7)}/><circle cx="66" cy="160" r="26" fill="none" stroke="#c8513a" stroke-width="10"/><circle cx="134" cy="160" r="26" fill="none" stroke="#c8513a" stroke-width="10"/><circle cx="100" cy="94" r="5" fill="#d8d8d0"/>'), tam=.4, alias=["tesoura"]),
    "linha": dict(f=_simples(f'<rect x="60" y="150" width="80" height="20" fill="#b98347" {ln(2.6)}/><rect x="60" y="40" width="80" height="20" fill="#b98347" {ln(2.6)}/><rect x="68" y="60" width="64" height="90" fill="#2f6fa8" {ln(2.6)}/><path d="M68 80l64 12M68 104l64 12M68 128l64 12" stroke="#1f4f88" stroke-width="3"/>'), tam=.3, alias=["linha", "carretel"]),
    "ferro de passar": dict(f=_simples(f'<path d="M20 170C24 120 70 100 130 100H178V170z" fill="#c8513a" {ln(3)}/><path d="M16 170H182V186H12z" fill="#b8bcc4" {ln(3)}/><path d="M90 100C96 62 170 62 172 100" fill="none" {ln(10)}/>'), tam=.5, alias=["ferro de passar", "ferro"]),
    "flores": dict(f=_simples(f'<path d="M100 196L80 110M100 196L100 100M100 196L124 112" {ln(4)}/>' + "".join(f'<circle cx="{x}" cy="{y}" r="26" fill="{c}" {ln(2.6)}/><circle cx="{x}" cy="{y}" r="9" fill="#f0c23a"/>' for x, y, c in ((72, 84, "#e8504a"), (130, 80, "#f0a0c0"), (100, 50, "#e87a2a"))) + f'<path d="M64 130L136 130L110 170H90z" fill="#3f8a55" {ln(2.6)}/>'), tam=.6, alias=["flor", "flores", "buque", "rosa"]),
    "perfume": dict(f=_simples(f'<rect x="56" y="80" width="88" height="110" rx="10" fill="#e8b0c8" {ln(3)}/><rect x="84" y="50" width="32" height="30" fill="#d8b24a" {ln(2.6)}/><circle cx="62" cy="50" r="16" fill="#3a3a40" {ln(2.6)}/><path d="M76 56H84" {ln(3)}/><path d="M70 96V170" stroke="#fff" stroke-width="7" opacity=".6"/>'), tam=.35, alias=["perfume"]),
    "espelho de mao": dict(f=_simples(f'<ellipse cx="100" cy="74" rx="56" ry="68" fill="#c9e4ee" {ln(4)}/><path d="M72 104L120 40" stroke="#fff" stroke-width="10" opacity=".6"/><rect x="90" y="140" width="20" height="58" rx="6" fill="#c8513a" {ln(3)}/>'), tam=.45, alias=["espelho"]),
    "batom": dict(f=_simples(f'<rect x="72" y="110" width="56" height="84" fill="#20222a" {ln(3)}/><rect x="78" y="80" width="44" height="30" fill="#d8b24a" {ln(2.6)}/><path d="M84 80V40L116 24V80z" fill="#d82a4a" {ln(2.6)}/>'), tam=.25, alias=["batom"]),
    "carta": dict(f=_simples(f'<rect x="20" y="60" width="160" height="110" fill="#fbf6e6" {ln(3)}/><path d="M20 60L100 124L180 60" fill="none" {ln(3)}/><circle cx="100" cy="124" r="13" fill="#c0392b" {ln(2)}/>'), tam=.5, alias=["carta", "bilhete", "envelope", "convite"]),
    "celular": dict(f=_simples(f'<rect x="60" y="20" width="80" height="170" rx="12" fill="#20222a" {ln(3)}/><rect x="68" y="34" width="64" height="140" fill="#8fd0e8"/>'), tam=.3, alias=["celular", "telefone", "zap", "whatsapp", "aplicativo"]),
    "notebook": dict(f=_simples(f'<rect x="36" y="50" width="128" height="94" rx="5" fill="#20222a" {ln(3)}/><rect x="46" y="60" width="108" height="74" fill="#6fb4dc"/><path d="M20 144H180L190 172H10z" fill="#b8bcc4" {ln(3)}/>'), tam=.7, alias=["notebook", "computador"]),
    "livro": dict(f=_simples(f'<path d="M100 60C70 40 40 40 16 50V170C40 160 70 160 100 180C130 160 160 160 184 170V50C160 40 130 40 100 60z" fill="#fbf6e6" {ln(3)}/><path d="M100 60V180" {ln(2.4)}/><path d="M32 76H84M32 100H84M32 124H84M116 76H168M116 100H168M116 124H168" stroke="#9aa0a8" stroke-width="4"/>'), tam=.45, alias=["livro", "caderno", "apostila"]),
    "mochila": dict(f=_simples(f'<path d="M40 190C24 130 34 60 100 50C166 60 176 130 160 190z" fill="#2f7a6b" {ln(3)}/><path d="M56 110H144V170H56z" fill="#225e52" {ln(2.6)}/><path d="M76 50C78 26 122 26 124 50" fill="none" {ln(6)}/>'), tam=.6, alias=["mochila", "bolsa"]),
    "chave": dict(f=_simples(f'<circle cx="64" cy="70" r="40" fill="none" stroke="#d8b24a" stroke-width="16"/><path d="M92 98L170 176M140 146L160 126M156 162L176 142" stroke="#d8b24a" stroke-width="14"/>'), tam=.25, alias=["chave", "chaves"]),
    "bolo": dict(f=_simples(f'<rect x="30" y="100" width="140" height="84" fill="#fbf6e6" {ln(3)}/><path d="M30 100C50 90 60 126 80 106C100 92 120 128 140 106C150 96 160 100 170 100V90H30z" fill="#f0a0c0" {ln(3)}/><path d="M100 90V60" {ln(5)}/>'), tam=.6, alias=["bolo", "torta"]),
    "panela": dict(f=_simples(f'<path d="M34 90V170C34 186 166 186 166 170V90z" fill="#9aa3a8" {ln(3)}/><ellipse cx="100" cy="90" rx="66" ry="16" fill="#5c5f66" {ln(3)}/><path d="M166 104H198" {ln(9)}/>'), tam=.6, alias=["panela", "caldeirao"]),
    "xicara": dict(f=_simples(f'<path d="M50 90V160C60 186 130 186 140 160V90z" fill="#fbfaf2" {ln(3)}/><path d="M140 106C176 100 176 150 140 146" fill="none" {ln(7)}/><ellipse cx="95" cy="90" rx="45" ry="11" fill="#5a3722" {ln(3)}/>'), tam=.25, alias=["xicara", "cafe", "caneca"]),
    "pente": dict(f=_simples(f'<rect x="20" y="70" width="160" height="30" rx="6" fill="#c8513a" {ln(3)}/>' + "".join(f'<rect x="{x}" y="100" width="7" height="44" fill="#c8513a" {ln(1.6)}/>' for x in range(26, 172, 13))), tam=.3, alias=["pente", "escova"]),
    "halter": dict(f=_simples(f'<rect x="60" y="88" width="80" height="20" fill="#8e9599" {ln(3)}/><rect x="20" y="60" width="44" height="76" rx="8" fill="#20222a" {ln(3)}/><rect x="136" y="60" width="44" height="76" rx="8" fill="#20222a" {ln(3)}/>'), tam=.4, alias=["halter", "peso"]),
    "mala": dict(f=_simples(f'<rect x="30" y="70" width="140" height="116" rx="12" fill="#7a4a2f" {ln(3)}/><path d="M70 70V48H130V70" fill="none" {ln(7)}/><path d="M30 120H170" {ln(2.6)}/>'), tam=.7, alias=["mala", "maleta"]),
    "guarda-chuva": dict(f=_simples(f'<path d="M12 100C20 40 180 40 188 100z" fill="#2f5fd8" {ln(3)}/><path d="M100 100V170C100 192 72 192 72 172" fill="none" {ln(6)}/>'), tam=.7, alias=["guarda-chuva", "guarda chuva"]),
    "dinheiro": dict(f=_simples(f'<rect x="20" y="60" width="160" height="84" rx="4" fill="#7fae6a" {ln(3)}/><circle cx="100" cy="102" r="26" fill="#fff" opacity=".5"/><rect x="34" y="72" width="132" height="60" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="3"/>'), tam=.35, alias=["nota", "notas", "dinheiro", "pagamento"]),
    "bola": dict(f=_simples(f'<circle cx="100" cy="110" r="78" fill="#f1ece0" {ln(3)}/><path d="M100 74L134 98L122 138H78L66 98z" fill="{L}"/><path d="M100 74V34M134 98L170 84M122 138L146 170M78 138L54 170M66 98L30 84" {ln(3)}/>'), tam=.5, alias=["bola"]),
    "violao": dict(f=_simples(f'<path d="M100 190C50 190 40 150 64 124C50 96 74 74 90 86V10H110V86C126 74 150 96 136 124C160 150 150 190 100 190z" fill="#c98a3c" {ln(3)}/><circle cx="100" cy="134" r="14" fill="#3a2410"/>'), tam=.9, alias=["violao"]),
    "carteira de motorista": dict(f=_simples(f'<rect x="20" y="60" width="160" height="96" rx="6" fill="#bfe0c8" {ln(3)}/><rect x="32" y="74" width="50" height="62" fill="#fbf6e6" {ln(2)}/><path d="M96 84H168M96 104H168M96 124H140" stroke="#5a7a60" stroke-width="5"/>'), tam=.3, alias=["carteira de motorista", "habilitacao", "cnh"]),
    "diploma": dict(f=_simples(f'<rect x="20" y="50" width="160" height="110" fill="#fbf6e6" {ln(3)}/><path d="M40 80H160M50 104H150M60 128H140" stroke="#9aa0a8" stroke-width="5"/><circle cx="150" cy="150" r="16" fill="#c0392b" {ln(2)}/>'), tam=.5, alias=["diploma", "certificado", "contrato"]),
    "peruca": dict(f=_simples(f'<path d="M30 180C10 70 60 24 100 24C150 24 190 70 170 180C160 130 150 90 100 84C50 90 40 130 30 180z" fill="#d8a23a" {ln(3)}/>'), tam=.5, alias=["peruca"]),
    "chapeu": dict(f=_simples(f'<path d="M60 130C60 70 70 50 100 50C130 50 140 70 140 130z" fill="#6e4a30" {ln(3)}/><ellipse cx="100" cy="134" rx="84" ry="18" fill="#6e4a30" {ln(3)}/>'), tam=.4, alias=["chapeu"]),
}


def _arq() -> Path:
    from lidark.config import DATA_DIR
    return DATA_DIR / "story" / "quadro_objetos.json"


def carregar_lib() -> dict[str, Any]:
    p = _arq()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def guardar(nome: str, svg: str, tam: float, alias: list[str], autor: str = "llm") -> None:
    with _lock:
        d = carregar_lib()
        d[plain(nome)] = dict(svg=svg, tam=tam, alias=[plain(a) for a in alias] or [plain(nome)], autor=autor)
        p = _arq()
        p.parent.mkdir(parents=True, exist_ok=True)
        q = p.with_suffix(".tmp")
        q.write_text(json.dumps(d, ensure_ascii=False, indent=0), encoding="utf-8")
        q.replace(p)


TAGS = {"svg", "g", "path", "circle", "ellipse", "rect", "polygon", "polyline", "line"}
ATTR = {"d", "cx", "cy", "r", "rx", "ry", "x", "y", "x1", "y1", "x2", "y2", "width", "height", "points", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "transform", "opacity"}
COR = re.compile(r"^(#[0-9a-fA-F]{3,8}|none|[a-zA-Z]{3,20})$")


def sanitizar(svg: str) -> str | None:
    """Só formas simples; sem script, sem style, sem referência externa. Devolve os filhos prontos ou None."""
    s = re.sub(r"```\w*", "", str(svg or "")).strip()
    s = re.sub(r'\sxmlns(:\w+)?="[^"]*"', "", s)
    if not s.lower().startswith("<svg"):
        s = f"<svg>{s}</svg>"
    try:
        raiz = ET.fromstring(s)
    except ET.ParseError:
        return None
    formas = 0

    def lim(el: ET.Element) -> str:
        nonlocal formas
        tag = el.tag.split("}")[-1].lower()
        if tag not in TAGS:
            return ""
        at = []
        for k, v in el.attrib.items():
            k = k.split("}")[-1].lower()
            v = str(v)
            if k not in ATTR or "url(" in v.lower() or "javascript" in v.lower():
                continue
            if k in ("fill", "stroke") and not COR.match(v.strip()):
                continue
            at.append(f'{k}="{v.replace(chr(34), "")}"')
        filhos = "".join(lim(x) for x in el)
        if tag == "svg":
            return filhos
        if tag != "g":
            formas += 1
        return f'<{tag} {" ".join(at)}>{filhos}</{tag}>'
    corpo = lim(raiz)
    return corpo if formas >= 3 and len(corpo) < 12000 else None


def achar(nome: str) -> tuple[str, dict[str, Any]] | None:
    n = plain(nome)
    lib = carregar_lib()
    for k, v in lib.items():
        if n == k or n in v.get("alias", []):
            return k, dict(svg=v["svg"], tam=v.get("tam", .6), alias=v.get("alias", []), llm=True)
    for k, v in BASE.items():
        if n == plain(k) or n in [plain(a) for a in v["alias"]]:
            return k, dict(svg=v["f"](), tam=v["tam"], alias=v["alias"], llm=False)
    return None


def svg_de(nome: str) -> tuple[str, float] | None:
    a = achar(nome)
    if not a:
        return None
    d = a[1]
    return (d["svg"] if not d["llm"] else f'<g transform="translate(-100 -200)">{d["svg"]}</g>'), float(d["tam"])


def todos_alias() -> dict[str, str]:
    o = {}
    for k, v in BASE.items():
        for a in v["alias"]:
            o[plain(a)] = k
    for k, v in carregar_lib().items():
        for a in v.get("alias", []):
            o[plain(a)] = k
    return o
