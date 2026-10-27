"""Ampliação de fotos com IA (Real-ESRGAN compacto, licença BSD-3) — fotos pequenas ficam nítidas em tela cheia.

Modelo: assets/models/realesr-general-x4v3.onnx (amplia 4x; treinado para fotos reais com ruído e compressão).
Roda no processador via ONNX Runtime, em blocos (pouca memória). O resultado fica em cache ao lado do original.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np
from PIL import Image

log = logging.getLogger("lidark.upscale")

MODEL = Path(__file__).resolve().parents[1] / "assets" / "models" / "realesr-general-x4v3.onnx"
MIN_SIDE = 1100  # abaixo disso a foto fica borrada num vídeo de 1080 de largura
TARGET_SIDE = 1600  # depois de ampliar, reduz para esse lado menor (equilíbrio nitidez × peso)
MAX_INPUT_PIXELS = 1600 * 1600  # fotos já grandes não precisam
TILE, PAD = 192, 12
AI_WEIGHT = 0.75

_sess = None
_lock = threading.Lock()


def _session():
    global _sess
    with _lock:
        if _sess is None:
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            _sess = ort.InferenceSession(str(MODEL), opts, providers=["CPUExecutionProvider"])
    return _sess


def _run_x4(rgb: np.ndarray) -> np.ndarray:
    """Amplia 4x em blocos com sobreposição (evita emendas e limita a memória)."""
    sess = _session()
    h, w, _ = rgb.shape
    src = rgb.astype(np.float32) / 255.0
    out = np.zeros((h * 4, w * 4, 3), np.float32)
    for y in range(0, h, TILE):
        for x in range(0, w, TILE):
            y0, x0 = max(0, y - PAD), max(0, x - PAD)
            y1, x1 = min(h, y + TILE + PAD), min(w, x + TILE + PAD)
            tile = src[y0:y1, x0:x1].transpose(2, 0, 1)[None]
            res = sess.run(None, {"input": tile})[0][0].transpose(1, 2, 0)
            ty, tx = (y - y0) * 4, (x - x0) * 4
            th, tw = min(TILE, h - y) * 4, min(TILE, w - x) * 4
            out[y * 4:y * 4 + th, x * 4:x * 4 + tw] = res[ty:ty + th, tx:tx + tw]
    return (np.clip(out, 0, 1) * 255).round().astype(np.uint8)


def enhance(path: str | Path) -> Path:
    """Devolve a versão HD da foto (ou a própria, se já for grande o bastante / se algo falhar)."""
    path = Path(path)
    hd = path.with_name(path.stem + "_hd.jpg")
    if hd.exists():
        return hd
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            if min(im.size) >= MIN_SIDE or im.width * im.height > MAX_INPUT_PIXELS or not MODEL.exists():
                return path
            ai = Image.fromarray(_run_x4(np.asarray(im)))
            # mistura com a ampliação comum: mantém a textura da foto original (sem cara de "plástico")
            big = Image.blend(im.resize(ai.size, Image.BICUBIC), ai, AI_WEIGHT)
        s = TARGET_SIDE / min(big.size)
        if s < 1:
            big = big.resize((round(big.width * s), round(big.height * s)), Image.LANCZOS)
        big.save(hd, "JPEG", quality=92)
        return hd
    except Exception as e:  # noqa: BLE001
        log.warning("ampliação falhou (%s): %s", path.name, e)
        return path
