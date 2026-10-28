"""Processo auxiliar do render paralelo (ver core._render_parallel).

Uso: python -m lidark.render.worker <timeline.pkl> <k>
Recria o template a partir da linha do tempo (mesma semente → mesma direção/sorteios), desenha os trechos
k, k+N, k+2N... (CHUNK quadros cada) e escreve os pixels RGB crus na saída padrão, na ordem.
"""
from __future__ import annotations

import importlib
import math
import os
import pickle
import queue
import sys
import threading


def main() -> None:
    job, k = sys.argv[1], int(sys.argv[2])
    # a saída padrão vira canal só de pixels: qualquer print perdido (de bibliotecas) vai para o log de erros
    out = os.fdopen(os.dup(1), "wb")
    os.dup2(2, 1)
    with open(job, "rb") as f:
        d = pickle.load(f)
    tl = d["tl"]
    cls = getattr(importlib.import_module(d["module"]), d["cls"])
    template = cls(tl)
    if d["setup"] and hasattr(template, "_setup_direction"):
        template._setup_direction()
    from .core import render_frame

    n, chunk, workers = int(d["n"]), int(d["chunk"]), int(d["workers"])
    q: queue.Queue = queue.Queue(maxsize=max(1, int(d.get("ahead", 12))))
    failed: list[BaseException] = []

    def writer() -> None:
        try:
            while True:
                b = q.get()
                if b is None:
                    break
                out.write(b)
            out.flush()
        except BaseException as e:  # noqa: BLE001 — processo principal fechou o cano (cancelado/erro)
            failed.append(e)

    th = threading.Thread(target=writer, daemon=True)
    th.start()

    def put(item) -> None:
        while True:
            if failed:
                os._exit(3)
            try:
                q.put(item, timeout=1)
                return
            except queue.Full:
                continue

    for c in range(k, math.ceil(n / chunk), workers):
        for i in range(c * chunk, min(n, (c + 1) * chunk)):
            put(render_frame(tl, template, i).tobytes())
    put(None)
    th.join()
    if failed:
        os._exit(3)
    out.close()


if __name__ == "__main__":
    main()
