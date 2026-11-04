"""Registro das séries do motor quadro: o que já foi usado para a próxima série evitar, em todos os canais.
Fica em data/story/quadro_registro.json. Dentro de uma série o lugar fixo pode voltar; entre séries, não."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from .objetos_compat import plain

_lock = threading.RLock()
CHAVES = ("premissas", "tipos", "composicoes", "paletas", "personagens", "nomes", "objetos", "gags", "huds", "titulos")


def _arq() -> Path:
    from ..config import DATA_DIR
    return DATA_DIR / "story" / "quadro_registro.json"


def carregar() -> dict[str, list[str]]:
    p = _arq()
    d: dict[str, Any] = {}
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            d = {}
    return {k: list(d.get(k) or []) for k in CHAVES}


def somar(serie: str, novos: dict[str, list[str]]) -> None:
    """Grava o que a série usou, com a origem, para o relatório mostrar de onde veio cada bloqueio."""
    with _lock:
        d = carregar()
        for k, v in novos.items():
            for x in v:
                if x and x not in d[k]:
                    d[k].append(x)
        o = {**d, "ultima_serie": serie}
        p = _arq()
        p.parent.mkdir(parents=True, exist_ok=True)
        q = p.with_suffix(".tmp")
        q.write_text(json.dumps(o, ensure_ascii=False, indent=0), encoding="utf-8")
        q.replace(p)


def ja_usado(reg: dict[str, list[str]], chave: str, valor: str) -> bool:
    n = plain(valor)
    return any(plain(x) == n for x in reg.get(chave, []))
