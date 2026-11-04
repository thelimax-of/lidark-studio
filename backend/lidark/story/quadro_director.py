"""Diretor do motor quadro: episódio compilado por quadro_writer -> MP4, miniatura e assets, sem nenhuma imagem gerada.
Mesmo retorno de engine.produce_story e de vetor_director.produce."""
from __future__ import annotations

import copy
import json
from typing import Any

from PIL import Image, ImageDraw, ImageFont

COBERTURA_MIN = 85.0


def _texto_atual(mot: dict[str, Any], beats: list[dict[str, Any]]) -> None:
    """A checagem de fatos pode ter corrigido falas no roteiro salvo: elas valem sobre o episódio compilado."""
    for bt in beats:
        try:
            mot["cenas"][bt["cena"]]["falas"][bt["fala"]]["texto"] = bt["text"]
        except (KeyError, IndexError, TypeError):
            continue


def cobertura(ep: dict[str, Any], total: float) -> float:
    return round(sum(f.get("_dur", 0) for c in ep["cenas"] for f in c.get("falas", [])) / max(total, .1) * 100, 1)


def _miniatura(caminho: Any, texto: str) -> None:
    im = Image.open(caminho).convert("RGB")
    d = ImageDraw.Draw(im)
    t = str(texto).upper()[:26]
    tam = 118
    fonte = ImageFont.truetype("ariblk.ttf", tam)
    while d.textlength(t, font=fonte) > 980 and tam > 54:
        tam -= 6
        fonte = ImageFont.truetype("ariblk.ttf", tam)
    d.text((540, 230), t, font=fonte, fill="#ffd23f", stroke_width=12, stroke_fill="#0b0d16", anchor="mm")
    im.save(caminho, quality=92)


def produce(ch: Any, sc: Any, video_id: int, ctx: Any, b: dict[str, Any], ep: dict[str, Any]) -> dict[str, Any]:
    from ..config import MEDIA_DIR
    from ..render.quadro import conferencia, gerador
    from .quadro_writer import voz_de
    q = ep.get("quadro") or {}
    if not q.get("episodio"):
        raise RuntimeError("Roteiro sem episódio do motor quadro: reescreva o episódio")
    mot = copy.deepcopy(q["episodio"])
    _texto_atual(mot, ep.get("beats") or [])
    mot["voz"] = voz_de(b)  # a bíblia vale na hora do render, sempre com o limite de velocidade
    fmt = sc.format or "short"
    if fmt != "short":
        ctx.log("Motor quadro desenha só 9:16: a versão longa sai vertical")
    workdir = MEDIA_DIR / ch.slug / f"video_{video_id}"
    tmp = workdir / "quadro"
    tmp.mkdir(parents=True, exist_ok=True)
    out = workdir / f"{ch.slug}_{video_id}.mp4"
    thumb = workdir / "thumb.jpg"
    ctx.update(0.03, f"Voz do episódio ({mot['voz']['voice']}, {mot['voz']['rate']})")
    medido: dict[str, float] = {}

    def antes(e: dict[str, Any], total: float) -> None:
        medido.update(total=total, cob=cobertura(e, total))
        ctx.log(f"{len(ep.get('beats') or [])} falas · {total:.1f}s · voz cobre {medido['cob']}%")
        if not 88 <= total <= 118:
            raise RuntimeError(f"Duração fora do padrão ({total:.1f}s): reescreva o episódio")
        if total > 110:
            ctx.log(f"Passou de 110 s ({total:.1f}s): mantido, sem acelerar a voz")
        if medido["cob"] < COBERTURA_MIN:
            raise RuntimeError(f"Voz cobre só {medido['cob']}% (mínimo {COBERTURA_MIN:.0f}%)")
        ctx.update(0.15, f"Desenhando {sum(len(c['planos']) for c in e['cenas'])} planos")
    r = gerador.produzir(mot, out, tmp, progresso=lambda p: ctx.update(0.15 + 0.8 * p), cancelar=ctx.check, antes=antes, miniatura=(hero, thumb))
    ctx.log(f"Render: {r['frames']} quadros em {r['seconds']}s · {r['loudness'].get('measured_lufs')} → -14 LUFS")
    v = conferencia.medir_voz(tmp / "voz.wav", r["duration"])
    ctx.log(f"Voz medida: {v['cobertura_pct']}%, pausa máxima {v['pausa_max_s']}s")
    if v["cobertura_pct"] < COBERTURA_MIN or v["pausas_acima_1_2s"]:
        raise RuntimeError(f"Narração fora do padrão: {json.dumps(v, ensure_ascii=False)[:300]}")
    _miniatura(thumb, ep.get("thumbnail_text") or sc.title)
    planos = sum(len(c["planos"]) for c in mot["cenas"])
    t = 0.0
    scenes = []
    for c in mot["cenas"]:
        for f in c["falas"]:
            scenes.append({"start": round(t + f["t"], 2), "end": round(t + f["t"] + f.get("_dur", 0), 2), "text": f["texto"], "visual": "quadro"})
        t += c["dur"]
    assets = {
        "template": "historia", "duration": r["duration"], "narration_end": v["ultima_fala_s"], "images": [], "scenes": scenes,
        "story": {"shots": planos, "new_images": 0, "reused": 0, "widgets": [], "part": int(ep.get("part") or 1), "missing": [], "render_seconds": r["seconds"],
                  "render_style": "quadro", "voz": {"cobertura_pct": v["cobertura_pct"], "pausa_max_s": v["pausa_max_s"]}},
        "audio": {"loudness": r["loudness"]}, "loop": False, "opening_type": None, "chapters": [],
    }
    (workdir / "assets.json").write_text(json.dumps(assets, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"path": str(out.relative_to(MEDIA_DIR)), "thumbnail": str(thumb.relative_to(MEDIA_DIR)), "duration": r["duration"], "assets": assets}


def hero(m: dict[str, Any]) -> float:
    """Quadro forte da miniatura: perto do fim da penúltima cena, onde a gag e o dilema costumam estar."""
    cs = m["cenas"]
    return sum(c["dur"] for c in cs[:-2]) + cs[-2]["dur"] * .6
