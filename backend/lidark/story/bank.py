"""Banco de assets do Modo História (por canal): poses recortadas, cenários vazios, cenas prontas, objetos e retratos.

data/story/<slug>/bank.json  — índice [{id, type, char, pose, tags, file, ...}]
data/story/<slug>/assets/    — arquivos (originais + derivados: recorte RGBA, fundo sem personagem, máscara)

Tipos:
- pose      personagem recortado (RGBA, aparado), com olhos (piscar) e "pés" (âncora embaixo)
- location  cenário vazio (sem personagem) — fundo das cenas em camadas
- scene     ilustração pronta com personagem; ganha fg (personagem RGBA) + plate (fundo preenchido) → paralaxe 2.5D
- prop      objeto recortado (RGBA) para entrar por cima da cena
- insert    imagem de detalhe (objeto/documento) em tela cheia
- portrait  rosto para a caixa de diálogo (recortado de uma pose/cena)

O banco é para a IDENTIDADE dos personagens e para a velocidade; o planejador prefere imagens novas por episódio
quando há cota, e o banco cobre o resto (sempre as menos usadas recentemente).
"""
from __future__ import annotations

import json
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from PIL import Image

from . import cutout
from .bible import STORY_DIR

_lock = threading.RLock()
TYPES = ("pose", "location", "scene", "prop", "insert", "portrait")


def _dir(slug: str) -> Path:
    return STORY_DIR / slug


def _index_path(slug: str) -> Path:
    return _dir(slug) / "bank.json"


def load(slug: str) -> list[dict[str, Any]]:
    p = _index_path(slug)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return []


def _save(slug: str, items: list[dict[str, Any]]) -> None:
    p = _index_path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def file_path(slug: str, rel: str) -> Path:
    return _dir(slug) / rel


def get(slug: str, aid: str) -> dict[str, Any] | None:
    return next((a for a in load(slug) if a["id"] == aid), None)


def _orient(size: tuple[int, int]) -> str:
    w, h = size
    return "v" if h > w * 1.15 else ("h" if w > h * 1.15 else "sq")


# ================================================================ entrada no banco

def ingest(slug: str, src: Path | Image.Image, type_: str, *, tags: list[str] | None = None, char: str = "",
           pose: str = "", source: str = "", prompt: str = "", seed: int | None = None, need_eyes: bool = True,
           note: str = "") -> dict[str, Any] | None:
    """Processa e guarda um asset. Pose que não passa na validação devolve {"rejected": motivos} (não entra)."""
    assert type_ in TYPES, type_
    img = src if isinstance(src, Image.Image) else Image.open(src)
    img.load()
    aid = f"{type_[:3]}_{time.strftime('%y%m%d')}_{uuid.uuid4().hex[:6]}"
    d = _dir(slug) / "assets" / type_
    d.mkdir(parents=True, exist_ok=True)
    rec: dict[str, Any] = {"id": aid, "type": type_, "char": char, "pose": pose, "tags": sorted({t.lower() for t in tags or []}),
                           "source": source, "prompt": prompt[:1500], "seed": seed, "created": time.time(), "uses": 0,
                           "episodes": [], "note": note}
    if type_ == "pose":
        res = cutout.cutout(img)
        if res is None:  # sem fundo verde: recorte grosseiro NUNCA entra no banco de poses (fica "colado" no vídeo)
            return {"rejected": ["pose sem fundo verde (chroma key) — recorte limpo impossível"]}
        rgba = res[0]
        ok, why, _ = cutout.validate_pose(rgba, need_eyes=need_eyes)
        if not ok:
            return {"rejected": why}
        cut, bb = cutout.trim(rgba)
        eyes = cutout.detect_eyes(cut.convert("RGB"), cut.getchannel("A")) if need_eyes else None
        cutout.save_rgba(cut, d / f"{aid}.png")
        rec.update(file=f"assets/{type_}/{aid}.png", size=list(cut.size), eyes=eyes, orientation=_orient(cut.size), clean=True)
    elif type_ == "prop":
        res = cutout.cutout(img)
        if res is None:
            return {"rejected": ["objeto sem fundo verde"]}
        cut, _ = cutout.trim(res[0])
        cutout.save_rgba(cut, d / f"{aid}.png")
        rec.update(file=f"assets/{type_}/{aid}.png", size=list(cut.size), orientation=_orient(cut.size))
    elif type_ == "portrait":
        rgb = img.convert("RGBA") if img.mode == "RGBA" else img.convert("RGB")
        rgb.save(d / f"{aid}.png")
        rec.update(file=f"assets/{type_}/{aid}.png", size=list(rgb.size), orientation="sq")
    else:  # location, scene, insert
        rgb = cutout.scrub_signature(img.convert("RGB"))
        rgb.save(d / f"{aid}.png")
        rec.update(file=f"assets/{type_}/{aid}.png", size=list(rgb.size), orientation=_orient(rgb.size))
        if type_ == "scene":
            try:
                sp = cutout.split_scene(rgb)
            except Exception:  # noqa: BLE001
                sp = None
            if sp:
                fg, plate = sp
                cutout.save_rgba(fg, d / f"{aid}_fg.png")
                plate.save(d / f"{aid}_plate.jpg", quality=92)
                rec.update(fg=f"assets/{type_}/{aid}_fg.png", plate=f"assets/{type_}/{aid}_plate.jpg")
                rec["eyes"] = cutout.detect_eyes(rgb, fg.getchannel("A")) if need_eyes else None
            else:
                rec["eyes"] = None
    with _lock:
        items = load(slug)
        items.append(rec)
        _save(slug, items)
    return rec


def add_portrait_from(slug: str, asset: dict[str, Any]) -> dict[str, Any] | None:
    """Retrato quadrado (cabeça e ombros) a partir de uma pose/cena com olhos detectados."""
    e = asset.get("eyes")
    if not e:
        return None
    src = Image.open(file_path(slug, asset["file"])).convert("RGBA")
    (x0, y0), (x1, y1) = e["eyes"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    side = max(120, abs(x1 - x0) * 4.4)
    box = (int(cx - side / 2), int(cy - side * 0.5), int(cx + side / 2), int(cy + side * 0.5))
    bg = src.crop(box)
    rec = ingest(slug, bg, "portrait", tags=asset.get("tags", []), char=asset.get("char", ""), pose=asset.get("pose", ""),
                 source=f"from:{asset['id']}")
    if rec and not rec.get("rejected"):
        ey = {"eyes": [[x0 - box[0], y0 - box[1]], [x1 - box[0], y1 - box[1]]], "r": e["r"], "skin": e.get("skin")}
        _set(slug, rec["id"], eyes=ey)
        rec["eyes"] = ey
    return rec


def remove(slug: str, aid: str) -> bool:
    with _lock:
        items = load(slug)
        hit = next((a for a in items if a["id"] == aid), None)
        if not hit:
            return False
        for k in ("file", "fg", "plate"):
            if hit.get(k):
                file_path(slug, hit[k]).unlink(missing_ok=True)
        _save(slug, [a for a in items if a["id"] != aid])
    return True


def update(slug: str, aid: str, **kw: Any) -> dict[str, Any] | None:
    with _lock:
        items = load(slug)
        for a in items:
            if a["id"] == aid:
                a.update({k: v for k, v in kw.items() if k in ("tags", "note", "char", "pose", "disabled")})
                _save(slug, items)
                return a
    return None


# ================================================================ busca e reaproveitamento

def find(slug: str, type_: str, *, tags: list[str] | None = None, char: str = "", pose: str = "", orientation: str = "",
         exclude: set[str] | None = None, recent_eps: set[int] | None = None, limit: int = 8) -> list[dict[str, Any]]:
    """Candidatos do banco por ordem de preferência: mais tags em comum, menos usados, fora dos episódios recentes."""
    want = {t.lower() for t in tags or []}
    out = []
    for a in load(slug):
        if a["type"] != type_ or a.get("disabled") or (exclude and a["id"] in exclude):
            continue
        if char and a.get("char") != char:
            continue
        score = 0.0
        if pose:
            score += 6 if a.get("pose") == pose else 0
        score += 3 * len(want & set(a.get("tags") or []))
        if orientation and a.get("orientation") not in (orientation, "sq"):
            score -= 4
        score -= 0.6 * float(a.get("uses") or 0)
        if recent_eps and set(a.get("episodes") or []) & recent_eps:
            score -= 5
        out.append((score, a))
    out.sort(key=lambda x: -x[0])
    return [a for _, a in out[:limit]]


def mark_used(slug: str, ids: list[str], episode: int) -> None:
    ids_set = set(ids)
    with _lock:
        items = load(slug)
        for a in items:
            if a["id"] in ids_set:
                a["uses"] = int(a.get("uses") or 0) + 1
                eps = list(a.get("episodes") or [])
                if episode not in eps:
                    eps.append(episode)
                a["episodes"] = eps[-30:]
        _save(slug, items)


def stats(slug: str) -> dict[str, Any]:
    items = load(slug)
    by: dict[str, int] = {}
    for a in items:
        by[a["type"]] = by.get(a["type"], 0) + 1
    return {"total": len(items), "by_type": by}


# ================================================================ semente: protótipo aprovado (Ouro do Passado, 1904)

PROTO_DIR = Path(r"C:\Users\DANIEL~1\AppData\Local\Temp\claude\C--Users-Daniel-de-Lima-Documents-Projetos-lidark-channel"
                 r"\e9bd72e5-1cfa-48f1-a5c4-33c5c4cecba6\scratchpad\story\img")
PROTO = [  # arquivo, tipo, personagem, pose, tags
    ("street_11", "location", "", "", ["rua", "bonde", "1904", "rio", "revolta", "noite", "barricada", "street"]),
    ("street_22", "location", "", "", ["rua", "bonde", "1904", "rio", "revolta", "barricada", "street"]),
    ("wake_44", "scene", "ze", "sitting", ["quarto", "acordar", "1904", "manha", "janela", "cama"]),
    ("wake_33", "scene", "ze", "sitting", ["quarto", "acordar", "1904", "manha", "janela", "cama"]),
    ("paper_33", "scene", "ze", "reading", ["jornal", "1904", "noticia", "casa", "mesa"]),
    ("paper_44", "scene", "ze", "reading", ["jornal", "1904", "noticia", "casa", "mesa"]),
    ("paper_11", "scene", "ze", "back", ["jornal", "1904", "noticia", "casa", "costas"]),
    ("window_11", "scene", "ze", "window", ["janela", "soldados", "1904", "casa", "medo"]),
    ("window_22", "scene", "ze", "window", ["janela", "soldados", "1904", "casa"]),
    ("rubble_33", "scene", "ze", "front", ["demolicao", "cortico", "bota-abaixo", "1904", "rua", "escombros"]),
    ("rubble_44", "scene", "ze", "front", ["demolicao", "cortico", "bota-abaixo", "1904", "rua", "escombros"]),
    ("rubble_11", "scene", "ze", "back", ["demolicao", "cortico", "bota-abaixo", "1904", "rua", "escombros", "costas"]),
    ("rubble_22", "scene", "ze", "back", ["demolicao", "cortico", "bota-abaixo", "1904", "rua", "costas"]),
    ("candle_11", "scene", "ze", "sitting", ["noite", "vela", "medo", "estado de sitio", "1904", "casa", "escuro"]),
    ("candle_22", "scene", "ze", "sitting", ["noite", "vela", "1904", "casa", "escuro", "calmo"]),
    ("maria_lucid-origin", "portrait", "maria", "front", ["vizinha", "maria", "1904"]),
]
# (não usado) recortes de cena por IA ficam com borda ruim — poses só nascem de geração em fundo verde
PROTO_POSES = [("rubble_33", "front"), ("paper_33", "reading"), ("window_11", "arms_up"), ("candle_22", "sitting"),
               ("rubble_44", "worried"), ("paper_11", "back"), ("rubble_22", "back_walk")]


def seed_prototype(slug: str = "ouro-do-passado", src_dir: Path = PROTO_DIR) -> dict[str, Any]:
    """Copia as imagens do protótipo aprovado (Zé, Dona Maria, Rio 1904) para o banco do canal. Idempotente."""
    have = {a.get("note") for a in load(slug)}
    added, rejected = [], []
    for name, type_, char, pose, tags in PROTO:
        p = src_dir / f"{name}.png"
        if not p.exists() or f"proto:{name}" in have:
            continue
        rec = ingest(slug, p, type_, tags=tags, char=char, pose=pose, source="cf_lucid (protótipo)", note=f"proto:{name}")
        if rec and not rec.get("rejected"):
            added.append(rec["id"])
            if type_ == "portrait":  # o retrato da Maria já é um rosto: detecta olhos para piscar no diálogo
                e = cutout.detect_eyes(Image.open(p).convert("RGB"))
                if e:
                    _set(slug, rec["id"], eyes=e)
    for name, pose in ([] if True else PROTO_POSES):  # recortes de cena NÃO viram pose (borda ruim) — só fundo verde
        p = src_dir / f"{name}.png"
        if not p.exists() or f"proto-pose:{name}" in have:
            continue
        rec = ingest(slug, p, "pose", tags=["1904", "ze"], char="ze", pose=pose, source="recorte do protótipo",
                     note=f"proto-pose:{name}", need_eyes=pose not in ("back", "back_walk"))
        if rec and rec.get("rejected"):
            rejected.append({name: rec["rejected"]})
        elif rec:
            added.append(rec["id"])
    # retrato do Zé para a caixa de diálogo
    if not any(a["type"] == "portrait" and a.get("char") == "ze" for a in load(slug)):
        for a in sorted(load(slug), key=lambda x: x.get("note") != "proto:rubble_33"):
            if a["type"] == "scene" and a.get("char") == "ze" and a.get("eyes") and a.get("pose") == "front":
                r = add_portrait_from(slug, a)
                if r and not r.get("rejected"):
                    added.append(r["id"])
                break
    return {"added": len(added), "rejected": rejected, "stats": stats(slug)}


def _set(slug: str, aid: str, **kw: Any) -> None:
    with _lock:
        items = load(slug)
        for a in items:
            if a["id"] == aid:
                a.update(kw)
        _save(slug, items)


def copy_into(slug: str, rel: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path(slug, rel), dest)
    return dest
