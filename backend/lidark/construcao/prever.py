"""Testa uma cena-mestra: narra o exemplo, renderiza 12 quadros e mostra onde está a prévia.

Uso, a partir de backend: python -m lidark.construcao.prever <chave>
Um render por vez, para não esgotar a memória: quem chega depois espera na fila.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time

from . import BASE, projeto as P

TRAVA = BASE / ".prever.lock"
LIMITE = 900  # uma trava mais velha que isso sobrou de um teste que morreu


def _travar() -> None:
    while True:
        try:
            os.close(os.open(TRAVA, os.O_CREAT | os.O_EXCL))
            return
        except FileExistsError:
            try:
                if time.time() - TRAVA.stat().st_mtime > LIMITE:
                    TRAVA.unlink(missing_ok=True)
                    continue
            except OSError:
                pass
            time.sleep(3)


def main(k: str) -> int:
    m = P._mestre(k)
    pid = "teste-" + k.replace("_", "-")
    (BASE / pid).mkdir(parents=True, exist_ok=True)
    arq = BASE / pid / "projeto.json"
    if arq.exists():
        p = P.ler(pid)
    else:
        p = {**P.PADRAO, "id": pid, "channel_id": 5, "tema": m["tema"], "titulo": f"Teste {k}", "criado": ""}
    p.update(falas=m["exemplo"], mestre=k, modo="mestre", rate=m["rate"], zoom=m["zoom"], teste=True)
    P.salvar(p)
    P.escrever_cena(p, P.gerar_espec(p))
    _travar()
    try:
        r = subprocess.run([sys.executable, "-m", "lidark.construcao.render", str(P.pasta(pid)), "previa"], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=600)
    finally:
        TRAVA.unlink(missing_ok=True)
    print(r.stdout[-700:], r.stderr[-900:])
    print("PREVIA", P.pasta(pid) / "previa.jpg")
    return r.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
