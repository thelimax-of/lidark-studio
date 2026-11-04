"""Caderno de regras do canal, com índice: cada agente recebe só as regras do assunto dele.

Regra: {"id", "area", "texto", "tags", "peso", "origem"}. Áreas: roteiro, cena, animacao, voz, som, capa, publicacao, geral.
O índice liga cada raiz de palavra às regras, então buscar não exige ler o caderno inteiro nem gastar tokens com ele.
Uso: python -m lidark.construcao.caderno buscar "<texto>" [area] | add <area> "<texto>" [origem] | lista [area]
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from . import MOTOR

ARQ = MOTOR / "biblioteca" / "caderno.json"
AREAS = {"roteiro", "cena", "animacao", "voz", "som", "capa", "publicacao", "geral"}
VAZIAS = set("como para com uma por que mas entao voce esse essa isso mais muito cada todo toda quando onde seu sua dos das nos nas pelo pela nao sem sao ser tem".split())
_mem: tuple[float, list[dict[str, Any]], dict[str, set[str]]] | None = None


def raizes(x: str) -> set[str]:
    x = unicodedata.normalize("NFD", x.lower()).encode("ascii", "ignore").decode()
    return {w[:5] for w in re.findall(r"[a-z0-9]{3,}", x) if w not in VAZIAS}


def _carregar() -> tuple[list[dict[str, Any]], dict[str, set[str]]]:
    """Lê uma vez e monta o índice; só refaz se o arquivo mudar."""
    global _mem
    if not ARQ.exists():
        return [], {}
    m = ARQ.stat().st_mtime
    if _mem and _mem[0] == m:
        return _mem[1], _mem[2]
    regras = json.loads(ARQ.read_text(encoding="utf-8"))
    idx: dict[str, set[str]] = defaultdict(set)
    for r in regras:
        for w in raizes(r["texto"] + " " + " ".join(r.get("tags", []))):
            idx[w].add(r["id"])
    _mem = (m, regras, idx)
    return regras, idx


def buscar(texto: str = "", area: str | None = None, limite: int = 8) -> list[dict[str, Any]]:
    """Regras gerais (peso 3) sempre vêm; o resto entra pelo índice, das mais ligadas ao assunto para as menos."""
    regras, idx = _carregar()
    por_id = {r["id"]: r for r in regras}
    nota: dict[str, int] = defaultdict(int)
    for w in raizes(texto):
        for i in idx.get(w, ()):
            nota[i] += 1
    pool = [r for r in regras if not area or r["area"] in (area, "geral")]
    pool.sort(key=lambda r: (-(r.get("peso", 1) >= 3), -nota[r["id"]], -r.get("peso", 1)))
    return [r for r in pool if r.get("peso", 1) >= 3 or nota[r["id"]]][:limite] if por_id else []


def para_prompt(texto: str, area: str, limite: int = 8) -> str:
    """Bloco curto para colar no pedido à IA. Vazio se nada se aplicar."""
    r = buscar(texto, area, limite)
    return "\nRegras do canal, obrigatórias:\n" + "\n".join(f"- {x['texto']}" for x in r) + "\n" if r else ""


def add(area: str, texto: str, origem: str = "dono do canal", tags: list[str] | None = None, peso: int = 2) -> dict[str, Any]:
    if area not in AREAS:
        raise ValueError(f"área inválida: {area}")
    regras, _ = _carregar()
    if any(raizes(r["texto"]) == raizes(texto) for r in regras):
        return next(r for r in regras if raizes(r["texto"]) == raizes(texto))
    r = {"id": f"{area[:3]}{len(regras) + 1:03d}", "area": area, "texto": texto.strip(), "tags": tags or [], "peso": peso, "origem": origem}
    ARQ.write_text(json.dumps([*regras, r], ensure_ascii=False, indent=1), encoding="utf-8")
    return r


def checar(falas: list[str], etapas: list[dict[str, Any]] | None = None) -> list[str]:
    """Regras que dá para conferir por código, sem gastar a IA."""
    texto, erros = " ".join(falas), []
    if re.search(r"\d", texto):
        erros.append("tem algarismos")
    if re.search(r"(Esse é o|Essa é a) [^.]*[A-Z_]{4,}", texto):
        erros.append("nome técnico em maiúsculas ou com sublinhado")
    longas = [f for f in falas if max((len(x.split()) for x in re.split(r"[.!?]", f)), default=0) > 18]
    if longas:
        erros.append(f"{len(longas)} falas com frase longa demais: máximo de dezoito palavras por frase")
    return erros


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "lista"
    if c == "buscar":
        for r in buscar(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None):
            print(r["id"], r["area"], r["texto"])
    elif c == "add":
        print(add(sys.argv[2], sys.argv[3], *(sys.argv[4:5])))
    else:
        a = sys.argv[2] if len(sys.argv) > 2 else None
        for r in _carregar()[0]:
            if not a or r["area"] == a:
                print(r["id"], r["area"], f"peso {r.get('peso', 1)}", r["texto"])
