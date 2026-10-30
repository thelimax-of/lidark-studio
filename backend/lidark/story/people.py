"""Cenário do Modo História é só lugar/paisagem: o SD 1.5 às vezes desobedece o "no people" e põe gente realista no
fundo. A checagem usa o CLIP no worker local da GPU (entende ilustração; o detector de pedestres do OpenCV é feito para
foto). Corte 0,6: nas imagens do banco, pessoas reais deram 0,65-1,0 e um jipe sozinho deu 0,54."""
from __future__ import annotations

import base64
import io
import logging

import httpx
from PIL import Image

log = logging.getLogger("lidark.story.people")
THRESHOLD = 0.6


def has_people(img: Image.Image) -> str:
    """'' se a imagem parece vazia de gente; "pessoa (0.93)" se não. Sem worker no ar, não bloqueia."""
    from .providers import conf
    try:
        buf = io.BytesIO()
        img.convert("RGB").resize((336, int(336 * img.height / max(1, img.width)))).save(buf, "PNG")
        r = httpx.post(conf().get("local_url", "http://127.0.0.1:8770").rstrip("/") + "/people",
                       json={"image": base64.b64encode(buf.getvalue()).decode()}, timeout=120)
        p = float(r.json().get("person", 0)) if r.status_code == 200 else 0.0
        return f"pessoa ({p:.2f})" if p >= THRESHOLD else ""
    except Exception as e:  # noqa: BLE001 — a checagem nunca derruba a geração
        log.info("checagem de pessoas indisponível: %s", e)
        return ""
