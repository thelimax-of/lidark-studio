"""Esboço procedural do personagem ("boneco") para o gerador LOCAL.

Os modelos locais (SD1.5/SDXL) não desenham "cabeça de esfera com dois olhinhos" só pelo texto — viram um rapaz comum.
Então desenhamos o boneco aqui (cabeça-esfera, boné, jaqueta, calça, tênis, mochila) na pose pedida, colocamos no
cenário (ou em fundo verde) e o modelo PINTA por cima (img2img com força média): a forma e as cores ficam iguais em
todo episódio (consistência) e o estilo vem do modelo. Depois os olhos de ponto são carimbados de novo, nítidos,
nas posições conhecidas — então o piscar sempre funciona.

Rosto e corpo SEMPRE virados para o mesmo lado (pedido do dono): poses de frente, 3/4 ou perfil inteiros.
"""
from __future__ import annotations

import math
import re
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

COLORS = {  # palavras da descrição → cor (fallback quando a bíblia não traz "sketch")
    "cream": "#efe3c8", "dark green": "#24412c", "olive": "#6b6a3a", "white": "#f2f0ea", "blue jeans": "#3d5a86",
    "jeans": "#3d5a86", "black": "#1d1d1f", "yellow": "#f2c230", "red": "#c8372d", "grey": "#8a8a8a", "purple": "#6b3f8f",
    "brown": "#6b4527", "flowered": "#d98aa0", "orange": "#e07a2a",
}

ZE = {"head": "#efe3c8", "cap": "#24412c", "jacket": "#6b6a3a", "shirt": "#f2f0ea", "pants": "#3d5a86", "shoes": "#f4f4f2",
      "backpack": "#1d1d1f", "skin": "#e9cfae", "hair": None}
DEFAULT_SPECS = {
    "ze": ZE,
    "nina": {"head": "#efe3c8", "cap": None, "hair": "#2a1d17", "jacket": "#f2c230", "shirt": "#f2c230", "pants": "#1d1d1f",
             "shoes": "#c8372d", "backpack": None, "skin": "#e9cfae"},
    "cida": {"head": "#efe3c8", "cap": None, "hair": "#b9b9b9", "jacket": "#6b3f8f", "shirt": "#d98aa0", "pants": "#4a4a55",
             "shoes": "#3a2a20", "backpack": None, "skin": "#e9cfae", "glasses": True},
}


def spec_for(ch: dict[str, Any]) -> dict[str, Any]:
    if ch.get("sketch"):
        return {**ZE, **ch["sketch"]}
    if ch.get("id") in DEFAULT_SPECS:
        return dict(DEFAULT_SPECS[ch["id"]])
    d = (ch.get("desc") or "").lower()
    sp = dict(ZE)
    for key, part in (("cap", "cap"), ("jacket", "jacket"), ("coat", "jacket"), ("trousers", "pants"), ("jeans", "pants"),
                      ("sneakers", "shoes"), ("shoes", "shoes")):
        m = re.search(r"((?:dark |light )?\w+) " + key, d)
        if m and m.group(1) in COLORS:
            sp[part] = COLORS[m.group(1)]
    if "cap" not in d:
        sp["cap"] = None
    if "backpack" not in d:
        sp["backpack"] = None
    return sp


def _rgb(h: str | None) -> tuple:
    h = (h or "#000000").lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _shade(c: tuple, k: float) -> tuple:
    return tuple(max(0, min(255, int(v * k))) for v in c)


def _limb(d: ImageDraw.ImageDraw, pts: list, w: float, col: tuple) -> None:
    d.line(pts, fill=col, width=int(w), joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=col)


# poses: ângulos/posições relativas (unidade = altura H do boneco). (ombro → cotovelo → mão), (quadril → joelho → pé)
POSES: dict[str, dict[str, Any]] = {
    "front": {"armL": [(-0.2, 0.36), (-0.23, 0.48), (-0.22, 0.6)], "armR": [(0.2, 0.36), (0.23, 0.48), (0.22, 0.6)],
              "legL": [(-0.07, 0.62), (-0.08, 0.79), (-0.08, 0.95)], "legR": [(0.07, 0.62), (0.08, 0.79), (0.08, 0.95)]},
    "worried": {"armL": [(-0.2, 0.36), (-0.17, 0.48), (-0.04, 0.47)], "armR": [(0.2, 0.36), (0.17, 0.48), (0.04, 0.47)],
                "legL": [(-0.06, 0.62), (-0.06, 0.79), (-0.07, 0.95)], "legR": [(0.06, 0.62), (0.06, 0.79), (0.07, 0.95)]},
    "surprised": {"armL": [(-0.2, 0.36), (-0.3, 0.26), (-0.2, 0.15)], "armR": [(0.2, 0.36), (0.3, 0.26), (0.2, 0.15)],
                  "legL": [(-0.07, 0.62), (-0.09, 0.79), (-0.1, 0.95)], "legR": [(0.07, 0.62), (0.09, 0.79), (0.1, 0.95)]},
    "pointing": {"armL": [(-0.2, 0.36), (-0.23, 0.48), (-0.21, 0.6)], "armR": [(0.2, 0.36), (0.33, 0.36), (0.46, 0.33)],
                 "legL": [(-0.07, 0.62), (-0.08, 0.79), (-0.09, 0.95)], "legR": [(0.07, 0.62), (0.1, 0.79), (0.12, 0.95)]},
    "running": {"armL": [(-0.2, 0.36), (-0.28, 0.45), (-0.2, 0.52)], "armR": [(0.2, 0.36), (0.29, 0.3), (0.34, 0.4)],
                "legL": [(-0.06, 0.62), (-0.2, 0.74), (-0.26, 0.9)], "legR": [(0.06, 0.62), (0.16, 0.76), (0.12, 0.95)]},
    "thinking": {"armL": [(-0.2, 0.36), (-0.2, 0.5), (-0.02, 0.5)], "armR": [(0.2, 0.36), (0.22, 0.45), (0.1, 0.33)],
                 "legL": [(-0.07, 0.62), (-0.08, 0.79), (-0.08, 0.95)], "legR": [(0.07, 0.62), (0.08, 0.79), (0.08, 0.95)]},
    "phone": {"armL": [(-0.2, 0.36), (-0.23, 0.48), (-0.22, 0.6)], "armR": [(0.2, 0.36), (0.2, 0.47), (0.08, 0.44)],
              "legL": [(-0.07, 0.62), (-0.08, 0.79), (-0.08, 0.95)], "legR": [(0.07, 0.62), (0.08, 0.79), (0.08, 0.95)]},
    "sitting": {"armL": [(-0.2, 0.36), (-0.2, 0.5), (-0.12, 0.6)], "armR": [(0.2, 0.36), (0.2, 0.5), (0.12, 0.6)],
                "legL": [(-0.08, 0.62), (-0.14, 0.66), (-0.12, 0.8)], "legR": [(0.08, 0.62), (0.14, 0.66), (0.12, 0.8)]},
}
POSES["talking"] = POSES["pointing"]
POSES["scared"] = POSES["surprised"]
POSES["back"] = POSES["front"]


def draw(spec: dict[str, Any], pose: str, H: int, flip: bool = False) -> tuple[Image.Image, dict[str, Any]]:
    """Boneco RGBA de altura H. Devolve (imagem, {"eyes": [[x,y],[x,y]], "r", "head": [x0,y0,x1,y1], "skin"})."""
    P = POSES.get(pose, POSES["front"])
    W = int(H * 1.0)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = W / 2

    def pt(p: tuple) -> tuple:
        return (cx + p[0] * H, p[1] * H)
    jacket, pants, shoes = _rgb(spec["jacket"]), _rgb(spec["pants"]), _rgb(spec["shoes"])
    skin, shirt = _rgb(spec.get("skin") or "#e9cfae"), _rgb(spec.get("shirt") or spec["jacket"])
    # pernas e tênis
    for leg in ("legL", "legR"):
        pts = [pt(p) for p in P[leg]]
        _limb(d, pts, H * 0.085, _shade(pants, 0.95 if leg == "legL" else 0.85))
        fx, fy = pts[-1]
        d.ellipse((fx - H * 0.06, fy - H * 0.03, fx + H * 0.06, fy + H * 0.04), fill=shoes, outline=_shade(shoes, 0.7), width=2)
    # mochila (atrás do tronco)
    if spec.get("backpack"):
        bp = _rgb(spec["backpack"])
        d.rounded_rectangle((cx - H * 0.2, H * 0.36, cx + H * 0.2, H * 0.6), int(H * 0.05), fill=_shade(bp, 1.0))
    # tronco (jaqueta aberta com camiseta)
    d.rounded_rectangle((cx - H * 0.17, H * 0.33, cx + H * 0.17, H * 0.64), int(H * 0.06), fill=jacket, outline=_shade(jacket, 0.6), width=2)
    d.polygon([(cx - H * 0.05, H * 0.34), (cx + H * 0.05, H * 0.34), (cx + H * 0.04, H * 0.63), (cx - H * 0.04, H * 0.63)], fill=shirt)
    if spec.get("backpack"):
        bp = _rgb(spec["backpack"])
        for sx in (-0.11, 0.11):
            d.line((cx + sx * H, H * 0.34, cx + sx * H * 0.9, H * 0.55), fill=bp, width=max(3, int(H * 0.02)))
    # braços (manga) e mãos
    for arm in ("armL", "armR"):
        pts = [pt(p) for p in P[arm]]
        _limb(d, pts, H * 0.07, _shade(jacket, 0.92 if arm == "armL" else 0.82))
        hx, hy = pts[-1]
        d.ellipse((hx - H * 0.032, hy - H * 0.032, hx + H * 0.032, hy + H * 0.032), fill=skin)
    if pose == "phone":
        hx, hy = pt(P["armR"][-1])
        d.rounded_rectangle((hx - H * 0.03, hy - H * 0.07, hx + H * 0.02, hy + H * 0.01), int(H * 0.008), fill=(30, 30, 34))
    # pescoço + cabeça-esfera com sombreado
    d.rectangle((cx - H * 0.03, H * 0.29, cx + H * 0.03, H * 0.35), fill=skin)
    r = H * 0.2
    hy = H * 0.185
    head = _rgb(spec["head"])
    sph = Image.new("RGBA", (int(2 * r), int(2 * r)), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sph)
    for k in range(14, 0, -1):  # sombreado radial simples (luz em cima à esquerda)
        f = k / 14
        col = _shade(head, 0.82 + 0.2 * (1 - f))
        rr = r * f
        ox, oy = -r * 0.18 * (1 - f), -r * 0.2 * (1 - f)
        sd.ellipse((r - rr + ox, r - rr + oy, r + rr + ox, r + rr + oy), fill=col)
    mask = Image.new("L", sph.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 2 * r - 1, 2 * r - 1), fill=255)
    sph.putalpha(mask)
    im.alpha_composite(sph, (int(cx - r), int(hy - r)))
    d.ellipse((cx - r, hy - r, cx + r, hy + r), outline=_shade(head, 0.55), width=max(2, int(H * 0.005)))
    if spec.get("hair"):
        hc = _rgb(spec["hair"])
        d.ellipse((cx - r * 0.55, hy - r * 1.28, cx + r * 0.55, hy - r * 0.6), fill=hc)
    if spec.get("cap"):
        cc = _rgb(spec["cap"])
        d.chord((cx - r * 0.98, hy - r * 1.02, cx + r * 0.98, hy + r * 0.5), 180, 360, fill=cc)
        d.ellipse((cx - r * 0.2, hy - r * 0.58, cx + r * 1.15, hy - r * 0.32), fill=_shade(cc, 0.8))
    # olhos de ponto + boquinha
    er = max(2.5, H * 0.012)
    ey = hy + r * 0.05
    eyes = [[cx - r * 0.33, ey], [cx + r * 0.33, ey]]
    for ex, eyy in eyes:
        d.ellipse((ex - er, eyy - er, ex + er, eyy + er), fill=(24, 20, 18))
    d.arc((cx - r * 0.12, hy + r * 0.3, cx + r * 0.12, hy + r * 0.45), 20, 160, fill=(60, 40, 30), width=max(2, int(H * 0.004)))
    if spec.get("glasses"):
        for ex, eyy in eyes:
            d.ellipse((ex - er * 3, eyy - er * 3, ex + er * 3, eyy + er * 3), outline=(40, 40, 40), width=2)
    meta = {"eyes": eyes, "r": er, "head": [cx - r, hy - r, cx + r, hy + r], "skin": list(head), "head_color": list(head)}
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
        meta["eyes"] = [[W - x, y] for x, y in reversed(meta["eyes"])]
        meta["head"] = [W - meta["head"][2], meta["head"][1], W - meta["head"][0], meta["head"][3]]
    return im, meta


def place(bg: Image.Image, fig: Image.Image, meta: dict[str, Any], x: float = 0.5, feet: float = 0.97,
          h: float = 0.6) -> tuple[Image.Image, dict[str, Any]]:
    """Cola o boneco no cenário (x = centro em fração da largura, pés em fração da altura, h = altura relativa).
    Sombra de contato leve; devolve a cena e os olhos/cabeça em pixels da cena."""
    out = bg.convert("RGB").copy()
    W, H = out.size
    fh = int(H * h)
    s = fh / fig.height
    f = fig.resize((max(1, int(fig.width * s)), fh), Image.LANCZOS)
    x0, y0 = int(W * x - f.width / 2), int(H * feet - fh)
    sh = Image.new("L", out.size, 0)
    ImageDraw.Draw(sh).ellipse((W * x - f.width * 0.25, H * feet - fh * 0.03, W * x + f.width * 0.25, H * feet + fh * 0.02), fill=110)
    out.paste((0, 0, 0), (0, 0), sh.filter(ImageFilter.GaussianBlur(fh * 0.02)))
    out.paste(f, (x0, y0), f)
    m = {"eyes": [[x0 + ex * s, y0 + ey * s] for ex, ey in meta["eyes"]], "r": meta["r"] * s,
         "head": [x0 + meta["head"][0] * s, y0 + meta["head"][1] * s, x0 + meta["head"][2] * s, y0 + meta["head"][3] * s],
         "skin": meta.get("skin"), "head_color": meta.get("head_color")}
    return out, m


def silhouette(bg: Image.Image, x: float, feet: float, h: float, color: tuple = (28, 30, 32)) -> tuple[Image.Image, list]:
    """Vulto curvado ao longe (ameaça sem gore). Devolve a cena e a caixa do vulto (fração do quadro)."""
    out = bg.convert("RGB").copy()
    W, H = out.size
    d = ImageDraw.Draw(out)
    fh = H * h
    cx, base = W * x, H * feet
    d.ellipse((cx - fh * 0.09, base - fh, cx + fh * 0.07, base - fh * 0.82), fill=color)
    d.polygon([(cx - fh * 0.14, base - fh * 0.84), (cx + fh * 0.1, base - fh * 0.82), (cx + fh * 0.12, base - fh * 0.4),
               (cx - fh * 0.12, base - fh * 0.42)], fill=color)
    d.line((cx - fh * 0.12, base - fh * 0.78, cx - fh * 0.3, base - fh * 0.55), fill=color, width=int(fh * 0.06))
    d.line((cx + fh * 0.08, base - fh * 0.78, cx + fh * 0.22, base - fh * 0.6), fill=color, width=int(fh * 0.06))
    d.line((cx - fh * 0.07, base - fh * 0.42, cx - fh * 0.12, base), fill=color, width=int(fh * 0.07))
    d.line((cx + fh * 0.07, base - fh * 0.42, cx + fh * 0.1, base), fill=color, width=int(fh * 0.07))
    return out, [(cx - fh * 0.32) / W, (base - fh * 1.02) / H, (cx + fh * 0.25) / W, (base + 4) / H]


def restamp_eyes(img: Image.Image, meta: dict[str, Any]) -> tuple[Image.Image, dict[str, Any]]:
    """Depois do img2img: o modelo costuma pintar olhos/sobrancelhas próprios perto dos nossos. Apaga a faixa dos olhos
    inteira com a cor da pele (amostrada na testa) e carimba os dois pontos nítidos de novo nas posições conhecidas."""
    out = img.convert("RGB").copy()
    d = ImageDraw.Draw(out)
    r = float(meta["r"])
    (x0, y0), (x1, y1) = meta["eyes"]
    hx0, hy0, hx1, hy1 = meta["head"]
    hr = (hx1 - hx0) / 2
    sx, sy = int((hx0 + hx1) / 2), int(y0 - hr * 0.22)
    sx, sy = max(0, min(out.width - 1, sx)), max(0, min(out.height - 1, sy))
    patch = out.crop((sx - 3, sy - 3, sx + 4, sy + 4)).resize((1, 1), Image.BOX)
    skin = patch.getpixel((0, 0))
    band = Image.new("L", out.size, 0)
    ImageDraw.Draw(band).ellipse((x0 - r * 4.5, y0 - r * 3.2, x1 + r * 4.5, y1 + r * 2.6), fill=255)
    out.paste(skin, (0, 0), band.filter(ImageFilter.GaussianBlur(r * 0.8)))
    for ex, ey in meta["eyes"]:
        d.ellipse((ex - r, ey - r, ex + r, ey + r), fill=(22, 18, 16))
    return out, {**meta, "skin": list(skin)}


def head_survived(img: Image.Image, meta: dict[str, Any], head_color: tuple | None = None) -> bool:
    """A cabeça-esfera continua lá depois do img2img? Região da testa com a cor da cabeça e lisa."""
    import numpy as np
    x0, y0, x1, y1 = [int(v) for v in meta["head"]]
    w = x1 - x0
    cx, cy, r = (x0 + x1) / 2, (y0 + y1) / 2, w / 2  # bochechas abaixo dos olhos (o topo é do boné)
    crop = np.asarray(img.convert("RGB").crop((int(cx - 0.6 * r), int(cy + 0.12 * r), int(cx + 0.6 * r), int(cy + 0.55 * r)))).astype(np.float32)
    if crop.size == 0:
        return False
    hc = np.array(head_color or meta.get("head_color") or (239, 227, 200), np.float32)
    dist = float(np.abs(crop.reshape(-1, 3).mean(0) - hc).mean())
    return dist < 55 and float(crop.std()) < 45


def distance_ok(meta: dict[str, Any]) -> bool:
    (x0, y0), (x1, y1) = meta["eyes"]
    return abs(x1 - x0) > 6 and math.isfinite(x0 + y0 + x1 + y1)


def stylize(fig: Image.Image, H: int) -> Image.Image:
    """Deixa o boneco com cara de pintura antes do img2img: contorno de nanquim, sombra lateral (cel shading) e textura.
    Esboço "vetorial" chapado faz o modelo devolver vetor chapado (ou inventar um humano)."""
    import numpy as np
    a = fig.getchannel("A")
    edge = a.filter(ImageFilter.MaxFilter(max(3, int(H * 0.008) | 1)))
    ink = Image.new("RGBA", fig.size, (28, 22, 18, 0))
    ink.putalpha(edge)
    out = Image.new("RGBA", fig.size, (0, 0, 0, 0))
    out.alpha_composite(ink)
    out.alpha_composite(fig)
    arr = np.asarray(out).astype(np.float32)
    h, w = arr.shape[:2]
    xs = np.linspace(1.08, 0.78, w)[None, :, None]  # luz da esquerda
    ys = np.linspace(1.05, 0.9, h)[:, None, None]
    rgb = arr[..., :3] * xs * ys
    rng = np.random.default_rng(3)
    noise = rng.normal(0, 7, (h // 4 + 1, w // 4 + 1, 1)).repeat(4, 0).repeat(4, 1)[:h, :w]
    rgb = (rgb + noise).clip(0, 255)
    out = Image.fromarray(np.dstack([rgb, arr[..., 3:]]).astype(np.uint8), "RGBA")
    return out.filter(ImageFilter.GaussianBlur(0.6))
