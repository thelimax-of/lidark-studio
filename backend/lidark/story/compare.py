"""Comparação de geradores de imagem no MESMO episódio (roteiro fixo, vozes e render do motor real).

    cd backend
    .venv/Scripts/python.exe -m lidark.story.compare --model sd15_lcm        --out "C:/Users/.../comparacao_modelos/2_sd15_local.mp4"
    .venv/Scripts/python.exe -m lidark.story.compare --model sdxl_lightning  --out ".../1_sdxl_local.mp4"
    .venv/Scripts/python.exe -m lidark.story.compare --model cf_lucid        --out ".../3_cloudflare_lucid.mp4"   (depois das 21:00)

Cada modelo usa um banco TEMPORÁRIO (slug "ze-na-fuga-cmp-<modelo>"), então o banco real do Zé na Fuga não é tocado.
- Local (sd15_lcm / sdxl_lightning): cenários e detalhes em txt2img; o Zé nasce do esboço procedural pintado em fundo
  verde (img2img) → chroma key → pose limpa composta no cenário (cor/luz casadas, rim light, sombra).
- cf_lucid: tudo pelo texto (o lucid desenha a cabeça-esfera), poses em fundo verde também.
Escreve <out>.mp4, <out>_folha.jpg (contact sheet) e <out>.json (tempos e contagens).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from PIL import Image

from . import bank, bible as B, director, engine, localgen, providers, sketch

SLUG = "ze-na-fuga"
STYLE_EXTRA = ""

EPISODE: dict[str, Any] = {
    "title": "Zé no Apocalipse Zumbi — Parte 1", "thumbnail_text": "ZUMBIS NA RUA?", "part": 1,
    "arc_title": "Zé no Apocalipse Zumbi",
    "mission": {"title": "SOBREVIVA 72H", "subtitle": "Seu prédio, sua cidade, agora", "hours": 72},
    "clock": {"mode": "date", "start": "07:00", "day_labels": ["SEGUNDA"]},
    "objectives": ["Trancar a porta", "Guardar água", "Falar com a Nina"],
    "beats": [
        {"speaker": "narrador", "text": "Sete da manhã. O Zé acorda com sirenes... e um silêncio esquisito lá fora.",
         "time": "07:00", "impact": True, "fx": ["dust"], "widget": {"type": "mission", "data": {}}, "emotion": "tensao"},
        {"speaker": "tv", "text": "Plantão urgente: um surto desconhecido se espalha pela cidade. Fiquem em casa e tranquem as portas.",
         "time": "07:04", "device": {"type": "tv", "data": {"tag": "PLANTÃO", "headline": "SURTO SE ESPALHA PELA CIDADE",
                                                           "ticker": "Autoridades pedem: fiquem em casa • não abram a porta para estranhos",
                                                           "anchor": "Rita Moraes · Jornal 24h"}}},
        {"speaker": "ze", "text": "Surto? Que surto? Ontem eu só fui comprar pão!", "time": "07:06", "emotion": "humor"},
        {"speaker": "narrador", "text": "Pela janela: carros abandonados. E alguém anda torto, bem devagar, no meio da rua.",
         "time": "07:12", "fx": ["smoke"], "highlight": {"label": "ANDANDO TORTO", "target": "street"}},
        {"speaker": "narrador", "text": "Nova regra: aguentar setenta e duas horas. Primeiro, trancar tudo.",
         "time": "07:20", "widget": {"type": "objectives", "data": {}}, "objective_done": 0},
        {"speaker": "narrador", "text": "Dica real: guarde pelo menos dois litros de água por pessoa, por dia. Encha garrafas e baldes antes que falte.",
         "time": "07:26", "widget": {"type": "inventory", "data": {"items": [{"label": "ÁGUA (LITROS)", "from": 0, "value": 6, "max": 12}]}},
         "objective_done": 1, "chip": "dica real de sobrevivência"},
        {"speaker": "nina", "text": "Zé! Tô presa no mercado da esquina. Não abre a porta pra ninguém, tá?", "time": "07:31",
         "device": {"type": "phone", "data": {"mode": "chat", "title": "Nina", "messages": [{"from": "Nina", "text": "Zé, tá aí??"}, {"audio": True}]}},
         "objective_done": 2},
        {"speaker": "ze", "text": "Nina?! Aguenta aí. Eu vou te buscar!", "time": "07:33", "impact": True},
        {"speaker": "narrador", "text": "Só que alguém bate na porta. Devagar. Três vezes.", "time": "07:41", "fx": ["night"],
         "widget": {"type": "alert", "data": {"kicker": "CORREDOR DO PRÉDIO", "title": "BATIDAS NA PORTA", "body": "Não abra."}},
         "sfx": [{"kind": "knock", "at": [1.6, 2.4, 3.2], "gain": 0.7}]},
        {"speaker": "narrador", "text": "Ainda faltam setenta e uma horas. Segue o canal pra ver quem está do outro lado.",
         "time": "07:45", "widget": {"type": "countdown", "data": {}}},
    ],
}

# o que gerar (mesma lista para todos os modelos)
ASSETS: dict[str, dict[str, Any]] = {
    "loc_bedroom": {"type": "location", "desc": "small modern apartment bedroom at early morning, unmade bed, window with blinds, red emergency light outside"},
    "loc_living": {"type": "location", "desc": "small modern apartment living room with a sofa and a TV on a rack, morning light, slightly messy"},
    "loc_street": {"type": "location", "desc": "view from an apartment window down to a city street with abandoned cars at dawn, empty sidewalks, thin smoke",
                   "silhouette": {"x": 0.63, "feet": 0.8, "h": 0.15}},
    "loc_street2": {"type": "location", "desc": "city avenue at ground level with abandoned cars and a crashed city bus at dawn, scattered papers, no people"},
    "loc_hallway": {"type": "location", "desc": "inside a small apartment entrance, closed wooden front door with a chain lock, dim warm lamp"},
    "loc_kitchen": {"type": "location", "desc": "small modern apartment kitchen with sink and counter, morning light"},
    "ins_water": {"type": "insert", "desc": "close-up of plastic water bottles, a filled bucket and a kettle on a kitchen floor, morning light, no people"},
    "ins_door": {"type": "insert", "desc": "close-up of a closed wooden apartment door at night seen from inside, a thin line of light under the door, ominous shadow"},
    "ins_tv": {"type": "insert", "desc": "close-up of a TV screen glowing blue in a dark living room, emergency broadcast colors, no readable text"},
    "ze_surprised": {"type": "pose", "char": "ze", "pose": "surprised"},
    "ze_worried": {"type": "pose", "char": "ze", "pose": "worried"},
    "ze_pointing": {"type": "pose", "char": "ze", "pose": "pointing"},
    "ze_front": {"type": "pose", "char": "ze", "pose": "front"},
}


def _bible_for(tmp: str) -> dict[str, Any]:
    b = B.load(SLUG)
    p = B.path(tmp)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {k: v for k, v in b.items() if k != "slug"}
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return B.load(tmp)


def make_assets(model: str, tmp: str, b: dict[str, Any], log=print) -> dict[str, Any]:
    """Gera e guarda no banco temporário. Devolve {nome: asset} + estatísticas de tempo."""
    have = {a.get("note"): a for a in bank.load(tmp)}
    out: dict[str, Any] = {}
    secs: list[float] = []
    fails: list[str] = []
    local = model in ("sd15_lcm", "sdxl_lightning")
    W, H = 720, 1280
    for i, (name, a) in enumerate(ASSETS.items()):
        if f"cmp:{name}" in have:
            out[name] = have[f"cmp:{name}"]
            continue
        t0 = time.time()
        rec = None
        seed = 5000 + i * 37
        if a["type"] == "pose":
            ch = B.character(b, a["char"])
            for attempt in range(3):
                if local:
                    r = localgen.pose_sheet(b, a["char"], a["pose"], int(ch.get("seed") or 1) + attempt * 101, model, log=log)
                    path = r[0] if r else None
                else:
                    path = providers.generate(B.pose_prompt(b, ch, a["pose"]), 768, 1024, int(ch.get("seed") or 1) + attempt * 101,
                                              "sheet", only=[model], log_fn=log)
                if not path:
                    continue
                rec = bank.ingest(tmp, path, "pose", tags=[a["char"]], char=a["char"], pose=a["pose"], source=model,
                                  note=f"cmp:{name}")
                if rec and rec.get("rejected"):
                    log(f"{name}: recusada ({', '.join(rec['rejected'])}) — outra semente")
                    rec = None
                    continue
                break
        else:
            prompt = B.location_prompt(b, a["desc"]) if a["type"] == "location" else \
                f"{b['style']}. Close-up detail shot, no people: {a['desc']}. No text, no letters"
            if local:
                path = providers.generate(prompt, W, H, seed, a["type"], only=["local"], model=model, log_fn=log)
            else:
                path = providers.generate(prompt, W, H, seed, "location" if a["type"] == "location" else "insert",
                                          only=[model], log_fn=log)
            boxes = []
            if path and a.get("silhouette"):
                img = Image.open(path).convert("RGB")
                sil = a["silhouette"]
                img, box = sketch.silhouette(img, sil["x"], sil["feet"], sil["h"])
                if local:  # integra o vulto na pintura (sem mudar o lugar dele)
                    p2 = providers.generate(prompt + ", a distant shambling dark figure walking on the street", W, H, seed + 1,
                                            "location", only=["local"], model=model, init=img, strength=0.35, log_fn=log)
                    img = Image.open(p2).convert("RGB") if p2 else img
                path = providers.GEN_DIR / f"cmp_{model}_{name}.png"
                img.save(path)
                boxes = [box]
            if path:
                rec = bank.ingest(tmp, path, "location" if a["type"] == "location" else "insert", tags=[name], source=model,
                                  note=f"cmp:{name}")
                if boxes and rec:
                    bank._set(tmp, rec["id"], boxes=boxes)
                    rec["boxes"] = boxes
        dt = time.time() - t0
        if rec:
            out[name] = rec
            secs.append(dt)
            log(f"{name}: ok em {dt:.1f}s")
        else:
            fails.append(name)
            log(f"{name}: FALHOU")
    # retrato do Zé para a caixa de diálogo
    if not bank.find(tmp, "portrait", char="ze", limit=1):
        for nm in ("ze_front", "ze_worried", "ze_surprised", "ze_pointing"):
            a = out.get(nm)
            if a and a.get("eyes"):
                bank.add_portrait_from(tmp, a)
                break
    return {"assets": out, "secs": secs, "fails": fails}


def visuals(tmp: str, A: dict[str, Any]) -> list[dict[str, Any]]:
    def F(n: str) -> dict[str, Any] | None:
        a = A.get(n)
        return {**a, "file": str(bank.file_path(tmp, a["file"]))} if a else None

    def lay(loc: str, pose: str, x: float = 0.5, flip: bool = False, alts: list | None = None) -> dict[str, Any]:
        p = F(pose)
        if p is None:  # sem pose limpa: cenário sozinho (nunca recorte ruim)
            return {"mode": "scene", "bg": F(loc), "alts": alts or []}
        return {"mode": "layered", "bg": F(loc), "chars": [{"asset": p, "id": "ze", "x": x, "flip": flip}], "alts": alts or []}

    def sc(n: str, alts: list | None = None) -> dict[str, Any]:
        return {"mode": "scene", "bg": F(n), "alts": alts or []}

    return [
        lay("loc_bedroom", "ze_surprised"),
        sc("loc_living", [sc("ins_tv")]),
        lay("loc_living", "ze_worried", 0.45, alts=[sc("ins_tv")]),
        sc("loc_street", [sc("loc_street2")]),
        lay("loc_hallway", "ze_pointing", 0.42),
        sc("ins_water", [lay("loc_kitchen", "ze_front", 0.6)]),
        sc("loc_kitchen"),
        lay("loc_living", "ze_pointing", 0.55, flip=True),
        sc("ins_door"),
        lay("loc_hallway", "ze_worried", 0.5),
    ]


def run(model: str, out: Path, log=print) -> dict[str, Any]:
    from ..db import session
    from ..models import Channel
    from ..render import story as R
    from ..media import ffmpeg_exe
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = f"{SLUG}-cmp-{model.replace('_', '-')}"
    b = _bible_for(tmp)
    t0 = time.time()
    g = make_assets(model, tmp, b, log)
    gen_total = time.time() - t0
    if model in ("sd15_lcm", "sdxl_lightning"):
        providers.PROVIDERS["local"].stop()  # libera VRAM/RAM antes do render
    with session() as s:
        ch = s.exec(__import__("sqlmodel").select(Channel).where(Channel.slug == SLUG)).first()
    ep = json.loads(json.dumps(EPISODE))
    work = providers.STORY_DIR / "_compare" / tmp
    lines = engine.synth_lines(ch, B.load(SLUG), ep["beats"], work)
    por = {}
    pr = bank.find(tmp, "portrait", char="ze", limit=1)
    if pr:
        por["ze"] = {**pr[0], "file": str(bank.file_path(tmp, pr[0]["file"]))}
    vis = visuals(tmp, g["assets"])
    for i, v in enumerate(vis):
        if v.get("bg") is None:  # asset que falhou: usa o vizinho
            vis[i] = next((x for x in vis if x.get("bg")), v)
    spec = director.direct(ep, vis, lines, b, seed=4242, part_label="PARTE 1 · CONTINUA…", portraits=por)
    t1 = time.time()
    music_bed = None
    try:
        from .. import music
        music_bed = music.ambient_track(spec["duration"] + 1, seed=7, mood="suspense dark cinematic")
    except Exception:  # noqa: BLE001
        pass
    r = R.render(spec, out, work / "render", music_bed=music_bed)
    R.thumbnail(spec, spec["hero_t"], ep["thumbnail_text"], out.with_name(out.stem + "_miniatura.jpg"), part_label="PARTE 1")
    render_s = time.time() - t1
    # contact sheet
    times = [round(spec["duration"] * k / 24, 2) for k in range(1, 24)]
    tiles = []
    import io
    for t in times:
        raw = subprocess.run([ffmpeg_exe(), "-v", "error", "-ss", str(t), "-i", str(out), "-frames:v", "1", "-f", "image2pipe",
                              "-vcodec", "png", "-"], capture_output=True).stdout
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        im.thumbnail((240, 427))
        tiles.append(im)
    S = Image.new("RGB", (240 * 8, 427 * 3))
    for i, t in enumerate(tiles):
        S.paste(t, ((i % 8) * 240, (i // 8) * 427))
    S.save(out.with_name(out.stem + "_folha.jpg"), quality=85)
    res = {"model": model, "images_ok": len(g["secs"]), "images_failed": g["fails"],
           "secs_per_image": round(sum(g["secs"]) / max(1, len(g["secs"])), 1), "generation_total_s": round(gen_total, 1),
           "render_s": round(render_s, 1), "duration_s": spec["duration"], "shots": len(spec["shots"]), "loudness": r["loudness"],
           "bank_slug": tmp}
    out.with_suffix(".json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    log(json.dumps(res, ensure_ascii=False))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=["sd15_lcm", "sdxl_lightning", "cf_lucid", "cf_schnell"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run(a.model, Path(a.out))
    _ = shutil
