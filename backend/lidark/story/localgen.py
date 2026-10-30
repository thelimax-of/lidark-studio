"""Geração LOCAL com personagem consistente: cenário (txt2img) → boneco procedural colado (sketch.py) → img2img
pinta tudo no estilo da série → olhos de ponto carimbados de novo (piscar garantido).

Os modelos locais não sabem desenhar a cabeça-esfera pelo texto; por isso a forma vem do esboço e só o acabamento vem
do modelo. Força do img2img: o bastante para virar ilustração, pouco para não "humanizar" a cabeça.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

from . import bible as B, providers, sketch

STRENGTH = {"sd15_lcm": 0.48, "sdxl_lightning": 0.55}  # pose em fundo verde usa ~0,06 a menos
POSE_WORDS = {"front": "standing facing the viewer", "worried": "standing facing the viewer, worried", "surprised":
              "facing the viewer, both hands on the head, shocked", "pointing": "facing the viewer, pointing to the side",
              "running": "running, body and face turned the same way", "thinking": "facing the viewer, hand on chin",
              "phone": "facing the viewer, holding a smartphone", "sitting": "sitting, facing the viewer"}


def _save(img: Image.Image, meta: dict[str, Any], tag: str) -> Path:
    providers.GEN_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(tag.encode()).hexdigest()[:20]
    p = providers.GEN_DIR / f"lc_{key}.png"
    img.save(p)
    p.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return p


def background(b: dict[str, Any], place: str, w: int, h: int, seed: int, model: str, log=None) -> Image.Image | None:
    p = providers.generate(B.location_prompt(b, place), w, h, seed, "location", only=["local"], model=model, log_fn=log)
    return Image.open(p).convert("RGB") if p else None


def scene(b: dict[str, Any], char_id: str, pose: str, desc: str, place: str, w: int, h: int, seed: int, model: str, *,
          x: float = 0.5, size: float = 0.6, flip: bool = False, extras: list[dict[str, Any]] | None = None,
          bg: Image.Image | None = None, log=None) -> tuple[Path, dict[str, Any]] | None:
    """Cena com o personagem já dentro (nada de recorte colado no vídeo). extras: [{"kind": "silhouette", x, feet, h}]
    → caixas devolvidas em meta["boxes"] (fração do quadro) para o destaque (highlight)."""
    ch = B.character(b, char_id)
    if not ch:
        return None
    bg = bg or background(b, place, w, h, seed, model, log)
    if bg is None:
        return None
    boxes = []
    for e in extras or []:
        if e.get("kind") == "silhouette":
            bg, box = sketch.silhouette(bg, e.get("x", 0.7), e.get("feet", 0.7), e.get("h", 0.22))
            boxes.append(box)
    fig, m = sketch.draw(sketch.spec_for(ch), pose, 900, flip=flip)
    fig = sketch.stylize(fig, 900)
    comp, m = sketch.place(bg, fig, m, x=x, h=size)
    prompt = (f"{b['style']}. {desc}. {ch['name']} is {ch['desc']}, {POSE_WORDS.get(pose, pose)}, face and body facing "
              "the same direction. No text, no signature")
    s = STRENGTH.get(model, 0.5)
    p = providers.generate(prompt, w, h, seed + 1, "scene", only=["local"], init=comp, strength=s, model=model,
                           tag=f"scene|{char_id}|{pose}|{x}|{size}|{flip}", log_fn=log)
    if not p:
        return None
    raw = Image.open(p).convert("RGB")
    if not sketch.head_survived(raw, m):
        if log:
            log("a cabeça-esfera não sobreviveu ao img2img — imagem descartada")
        return None
    img, m = sketch.restamp_eyes(raw, m)
    meta = {"eyes": {"eyes": m["eyes"], "r": m["r"], "skin": m.get("skin")}, "boxes": boxes, "char": char_id, "pose": pose,
            "head": m["head"], "provider": "local", "model": model, "prompt": prompt, "strength": s}
    return _save(img, meta, f"{p}|eyes"), meta


def pose_sheet(b: dict[str, Any], char_id: str, pose: str, seed: int, model: str, log=None) -> tuple[Path, dict[str, Any]] | None:
    """Pose em fundo verde puro (para o banco de poses limpas, chroma key)."""
    ch = B.character(b, char_id)
    if not ch:
        return None
    w, h = 768, 1024
    bg = Image.new("RGB", (w, h), (0, 255, 0))
    fig, m = sketch.draw(sketch.spec_for(ch), pose, 900)
    fig = sketch.stylize(fig, 900)
    comp, m = sketch.place(bg, fig, m, x=0.5, feet=0.95, h=0.86)
    prompt = (f"{b['style']}. Full body character, {POSE_WORDS.get(pose, pose)}: {ch['desc']}. Isolated on a flat solid pure "
              "green #00ff00 background, no shadow, no text")
    p = providers.generate(prompt, w, h, seed, "sheet", only=["local"], init=comp, strength=STRENGTH.get(model, 0.5) - 0.08,
                           model=model, tag=f"pose|{char_id}|{pose}", log_fn=log)
    if not p:
        return None
    raw = Image.open(p).convert("RGB")
    if not sketch.head_survived(raw, m):
        if log:
            log(f"pose {pose}: a cabeça-esfera virou outra coisa — descartada")
        return None
    img, m = sketch.restamp_eyes(raw, m)
    meta = {"eyes": {"eyes": m["eyes"], "r": m["r"], "skin": m.get("skin")}, "char": char_id, "pose": pose, "model": model}
    return _save(img, meta, f"{p}|eyes"), meta
