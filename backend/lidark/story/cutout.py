"""Recortes e checagens das imagens do Modo História (tudo local, CPU, grátis).

- chroma_key: pose gerada em fundo verde puro (#00ff00) → RGBA sem franja verde (despill)
- matte: recorte por IA local (U²-Net pequeno, u2netp, 4,6 MB, Apache-2.0) — serve para poses sem fundo verde
  e para separar uma cena pronta em "personagem" + "fundo" (2.5D: paralaxe entre as camadas)
- detect_eyes: olhos de ponto (bolinhas escuras com entorno claro e liso) → piscar e olhar para os lados
- validate_pose: a pose presta? (cobertura do recorte, corpo inteiro dentro do quadro, olhos achados)
- scrub_signature: some com a "assinatura" falsa que os modelos desenham no canto de baixo
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

from ..config import CACHE_DIR

log = logging.getLogger("lidark.story.cutout")
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
MODEL_PATH = CACHE_DIR / "models" / "u2netp.onnx"
_sess = None
_sess_lock = threading.Lock()


# ================================================================ recorte por IA (u2netp)

def _session():
    global _sess
    with _sess_lock:
        if _sess is None:
            if not MODEL_PATH.exists():
                import httpx
                MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
                r = httpx.get(MODEL_URL, follow_redirects=True, timeout=120)
                r.raise_for_status()
                MODEL_PATH.write_bytes(r.content)
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 2
            _sess = ort.InferenceSession(str(MODEL_PATH), opts, providers=["CPUExecutionProvider"])
        return _sess


def matte(img: Image.Image) -> Image.Image:
    """Máscara (L, 0-255) do assunto principal. Curva dura no meio para não deixar o fundo "fantasma"."""
    rgb = img.convert("RGB")
    x = np.asarray(rgb.resize((320, 320), Image.BILINEAR)).astype(np.float32) / 255
    x = (x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]
    x = x.transpose(2, 0, 1)[None].astype(np.float32)
    s = _session()
    o = s.run(None, {s.get_inputs()[0].name: x})[0][0, 0]
    o = (o - o.min()) / (o.max() - o.min() + 1e-6)
    m = Image.fromarray((o * 255).astype(np.uint8)).resize(rgb.size, Image.BICUBIC)
    a = np.asarray(m).astype(np.float32) / 255
    a = np.clip((a - 0.35) / 0.3, 0, 1)  # fundo semitransparente vira 0; bordas continuam suaves
    m = Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.8))
    return m


# ================================================================ chroma key

def green_ratio(img: Image.Image) -> float:
    """Fração da BORDA da imagem que é verde de chroma (diz se a imagem foi mesmo gerada em fundo verde)."""
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    border = np.concatenate([a[:6].reshape(-1, 3), a[-6:].reshape(-1, 3), a[:, :6].reshape(-1, 3), a[:, -6:].reshape(-1, 3)])
    r, g, b = border[:, 0], border[:, 1], border[:, 2]
    return float(np.mean((g > 120) & (g > r + 50) & (g > b + 50)))


def chroma_key(img: Image.Image) -> Image.Image:
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx = np.maximum(r, b)
    spill = g - mx  # quanto o verde passa dos outros canais
    alpha = 1 - np.clip((spill - 35) / 55, 0, 1)
    alpha[(g > 150) & (r < 120) & (b < 120)] = 0
    # despill: puxa o verde das bordas para o nível dos outros canais
    g2 = np.where(spill > 0, mx + np.clip(spill, 0, None) * 0.15, g)
    out = np.dstack([r, g2, b, alpha * 255]).clip(0, 255).astype(np.uint8)
    im = Image.fromarray(out, "RGBA")
    al = im.getchannel("A").filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.7))
    im.putalpha(al)
    return im


def cutout(img: Image.Image) -> Image.Image:
    """RGBA do personagem/objeto: chroma key se o fundo é verde, senão recorte por IA."""
    if green_ratio(img) > 0.6:
        im = chroma_key(img)
        cov = float(np.mean(np.asarray(im.getchannel("A")) > 128))
        if 0.03 < cov < 0.8:
            return im
    rgba = img.convert("RGBA")
    rgba.putalpha(matte(img))
    return rgba


def trim(rgba: Image.Image, pad: int = 4) -> tuple[Image.Image, tuple[int, int, int, int]]:
    bb = rgba.getchannel("A").point(lambda v: 255 if v > 24 else 0).getbbox()
    if not bb:
        return rgba, (0, 0, rgba.width, rgba.height)
    x0, y0, x1, y1 = max(0, bb[0] - pad), max(0, bb[1] - pad), min(rgba.width, bb[2] + pad), min(rgba.height, bb[3] + pad)
    return rgba.crop((x0, y0, x1, y1)), (x0, y0, x1, y1)


# ================================================================ olhos

def detect_eyes(img: Image.Image, alpha: Image.Image | None = None) -> dict[str, Any] | None:
    """Dois olhos de ponto: bolinhas escuras, quase redondas, com entorno claro e liso (a cabeça), lado a lado.
    Devolve {"eyes": [[x, y], [x, y]], "r": raio, "skin": [r, g, b]} em pixels da imagem, ou None."""
    import cv2
    rgb = np.asarray(img.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    H, W = gray.shape
    al = np.asarray(alpha) if alpha is not None else None
    y_max = H
    if al is not None:  # olhos ficam na parte de cima do recorte (botões da camisa não contam)
        rows = np.nonzero((al > 128).any(axis=1))[0]
        if rows.size:
            y_max = rows[0] + 0.45 * (rows[-1] - rows[0])
    best = None
    for thr in (70, 95, 50):
        dark = (gray < thr).astype(np.uint8)
        dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
        n, lab, stats, cents = cv2.connectedComponentsWithStats(dark, 8)
        cands = []
        rmin, rmax = max(2.5, W * 0.004), W * 0.05
        for i in range(1, n):
            x, y, w, h, area = stats[i]
            if w < 3 or h < 3:
                continue
            r = (w + h) / 4
            if not (rmin <= r <= rmax) or not (0.45 <= w / h <= 2.2) or area / (w * h) < 0.5:
                continue
            cx, cy = cents[i]
            if al is not None and (al[int(cy), int(cx)] < 128 or cy > y_max):
                continue
            # anel em volta: precisa ser claro e liso (a "pele" da cabeça)
            R0, R1 = int(r * 1.6), int(r * 2.8)
            ys, xs = np.ogrid[max(0, int(cy) - R1):min(H, int(cy) + R1 + 1), max(0, int(cx) - R1):min(W, int(cx) + R1 + 1)]
            d2 = (ys - cy) ** 2 + (xs - cx) ** 2
            ring = (d2 >= R0 * R0) & (d2 <= R1 * R1)
            patch = gray[max(0, int(cy) - R1):min(H, int(cy) + R1 + 1), max(0, int(cx) - R1):min(W, int(cx) + R1 + 1)]
            vals = patch[ring]
            if vals.size < 10:
                continue
            mean, std = float(vals.mean()), float(vals.std())
            if mean < 105 or std > 38 or mean - thr < 55:
                continue
            cands.append((cx, cy, r, mean, std, area))
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                a, b = cands[i], cands[j]
                ra = (a[2] + b[2]) / 2
                dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
                if dy > max(3.0, 1.3 * ra) or not (2.5 * ra <= dx <= max(24 * ra, W * 0.2)) or max(a[5], b[5]) / max(1, min(a[5], b[5])) > 2.3:
                    continue
                # entre os olhos e logo abaixo deles tem que ser "pele" lisa (cabeça), não gola/botões/roupa
                x0, x1 = sorted((a[0], b[0]))
                yc = (a[1] + b[1]) / 2
                pad = ra * 1.8
                seg = gray[int(max(0, yc - ra)):int(min(H, yc + ra * 2.5)), int(x0 + pad):int(max(x0 + pad + 1, x1 - pad))]
                if seg.size < 6 or float(seg.std()) > 34 or float(seg.mean()) < 105:
                    continue
                score = (a[3] + b[3]) / 2 - (a[4] + b[4]) - dy * 2 + ra * 0.5 - float(seg.std())
                if best is None or score > best[0]:
                    best = (score, a, b, ra)
        if best:
            break
    if not best:
        return None
    _, a, b, r = best
    left, right = sorted([a, b], key=lambda c: c[0])
    # cor da pele: mediana do anel, à direita/esquerda dos olhos
    sx = int(min(W - 1, right[0] + r * 2.4))
    sy = int(right[1])
    skin = rgb[max(0, sy - 2):sy + 3, max(0, sx - 2):sx + 3].reshape(-1, 3)
    skin = [int(v) for v in np.median(skin, axis=0)] if skin.size else [230, 220, 190]
    return {"eyes": [[round(left[0], 1), round(left[1], 1)], [round(right[0], 1), round(right[1], 1)]], "r": round(float(r), 1),
            "skin": skin}


# ================================================================ validação

def validate_pose(rgba: Image.Image, need_eyes: bool = True) -> tuple[bool, list[str], dict[str, Any] | None]:
    """Pose recortada presta? (antes de trim). Devolve (ok, motivos, olhos)."""
    al = np.asarray(rgba.getchannel("A")) > 128
    cov = float(al.mean())
    why = []
    if not 0.04 <= cov <= 0.75:
        why.append(f"recorte com cobertura estranha ({cov:.0%})")
    # corpo cortado na borda (lateral/topo): muito alfa encostado na borda
    edge = max(al[:, :3].mean(), al[:, -3:].mean(), al[:3].mean())
    if edge > 0.25:
        why.append("personagem cortado na borda")
    eyes = detect_eyes(rgba.convert("RGB"), rgba.getchannel("A")) if need_eyes else None
    if need_eyes and not eyes:
        why.append("olhos não encontrados")
    return (not why), why, eyes


# ================================================================ limpeza

def scrub_signature(img: Image.Image) -> Image.Image:
    """Assinaturas falsas nos cantos de baixo (comuns no lucid-origin): acha traços finos escuros/claros na faixa
    inferior dos cantos e pinta por cima com inpaint."""
    import cv2
    rgb = np.asarray(img.convert("RGB")).copy()
    H, W = rgb.shape[:2]
    band = int(H * 0.085)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = np.zeros((H, W), np.uint8)
    changed = False
    for x0, x1 in ((0, int(W * 0.42)), (int(W * 0.58), W)):
        roi = gray[H - band:, x0:x1]
        strokes = np.maximum(cv2.morphologyEx(roi, cv2.MORPH_BLACKHAT, k), cv2.morphologyEx(roi, cv2.MORPH_TOPHAT, k))
        m = (strokes > 38).astype(np.uint8)
        dens = m.mean()
        if 0.004 < dens < 0.16:
            ys, xs = np.nonzero(m)
            if xs.size and (xs.max() - xs.min()) < (x1 - x0) * 0.95:
                mask[H - band:, x0:x1] = cv2.dilate(m, np.ones((5, 5), np.uint8)) * 255
                changed = True
    if not changed:
        return img
    out = cv2.inpaint(rgb, mask, 5, cv2.INPAINT_TELEA)
    return Image.fromarray(out)


def split_scene(img: Image.Image) -> tuple[Image.Image, Image.Image] | None:
    """Cena pronta → (personagem RGBA no tamanho da cena, fundo com o buraco preenchido). Serve para paralaxe
    discreta (o fundo anda menos que o personagem). None se não houver um assunto claro."""
    import cv2
    m = matte(img)
    a = np.asarray(m)
    cov = float((a > 128).mean())
    if not 0.05 <= cov <= 0.6:
        return None
    fg = img.convert("RGBA")
    fg.putalpha(m)
    rgb = np.asarray(img.convert("RGB"))
    H, W = rgb.shape[:2]
    hole = cv2.dilate((a > 40).astype(np.uint8) * 255, np.ones((15, 15), np.uint8))
    s = 4  # inpaint em 1/4 (rápido e com borrão macio), recolocado só no buraco
    small = cv2.resize(rgb, (W // s, H // s), interpolation=cv2.INTER_AREA)
    hs = cv2.resize(hole, (W // s, H // s), interpolation=cv2.INTER_NEAREST)
    filled = cv2.inpaint(small, hs, 9, cv2.INPAINT_TELEA)
    filled = cv2.GaussianBlur(cv2.resize(filled, (W, H), interpolation=cv2.INTER_CUBIC), (0, 0), 3)
    hm = cv2.GaussianBlur(hole, (0, 0), 4).astype(np.float32)[..., None] / 255
    plate = (rgb * (1 - hm) + filled * hm).astype(np.uint8)
    return fg, Image.fromarray(plate)


def save_rgba(rgba: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba.save(path, optimize=False, compress_level=3)
    return path
