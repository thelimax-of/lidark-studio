"""Motor do Modo História: falas (multi-voz) → imagens (novas + banco) → diretor → render → miniatura.

produce_story(ch, sc, video_id, ctx) tem o MESMO contrato de production.produce_video (devolve path/thumbnail/
duration/assets relativos a MEDIA_DIR), então o Video normal, o inspetor, a publicação e a miniatura funcionam igual.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from .. import tts
from ..config import MEDIA_DIR
from ..media import audio_duration
from ..models import Channel, Script
from . import bank, bible as B, director, planner

log = logging.getLogger("lidark.story.engine")


def is_story(sc: Script) -> bool:
    return (sc.variety or {}).get("structure") == "historia"


def _pct(s: str) -> int:
    try:
        return int(str(s or "+0%").strip().rstrip("%"))
    except ValueError:
        return 0


def synth_lines(ch: Channel, b: dict[str, Any], beats: list[dict[str, Any]], workdir: Path, rate: str = "") -> list[dict[str, Any]]:
    """Uma faixa por beat: narrador na voz do canal (com emoção por fala), personagens nas vozes da bíblia."""
    out = []
    chars = {c["id"]: c for c in b.get("characters") or []}
    base_rate = _pct(rate or b.get("narrator_rate") or ch.voice_rate)
    d = workdir / "voz"
    d.mkdir(parents=True, exist_ok=True)
    for i, bt in enumerate(beats):
        text = bt["text"]
        spk = bt.get("speaker", "narrador")
        c = chars.get(spk)
        emo = str(bt.get("emotion") or "").lower()
        de, dp = tts.EMOTION.get(emo, (0, 0))
        if c:
            voice, r, pitch, provider = c.get("voice") or "pt-BR-FranciscaNeural", _pct(c.get("rate")) + de, c.get("pitch") or "+0Hz", "edge"
        else:
            voice, r, pitch, provider = (b.get("narrator_voice") or ch.voice_name or "pt-BR-AntonioNeural"), base_rate + de, f"{dp:+d}Hz", ch.voice_provider or "edge"
        key = hashlib.sha1(f"{text}|{voice}|{r}|{pitch}|{provider}".encode()).hexdigest()[:12]
        p = d / f"{i:02d}_{key}.mp3"
        if not p.exists() or p.stat().st_size < 1000:
            if provider == "edge" or c:
                tts._edge(text, p, voice, f"{r:+d}%", pitch)
            else:
                tts.synthesize(text, p, provider=provider, voice=voice, rate=f"{r:+d}%", style=ch.voice_style)
        out.append({"audio": str(p), "dur": round(audio_duration(p), 3), "speaker": spk})
    return out


def episode_of(sc: Script) -> dict[str, Any]:
    st = dict((sc.variety or {}).get("story") or {})
    st["beats"] = [dict(x) for x in sc.scenes or []]
    st.setdefault("title", sc.title)
    st.setdefault("thumbnail_text", sc.thumbnail_text)
    return st


def produce_story(ch: Channel, sc: Script, video_id: int, ctx: Any) -> dict[str, Any]:
    from ..render import story as R
    b = B.load(ch.slug)
    ep = episode_of(sc)
    fmt = sc.format or "short"
    vertical = fmt == "short"
    W, H = (720, 1280) if vertical else (1280, 720)
    workdir = MEDIA_DIR / ch.slug / f"video_{video_id}"
    workdir.mkdir(parents=True, exist_ok=True)
    ctx.update(0.03, "Vozes do episódio")
    lines = synth_lines(ch, b, ep["beats"], workdir, (sc.variety or {}).get("voice_rate", ""))
    ctx.log(f"{len(lines)} falas ({sum(1 for x in lines if x['speaker'] != 'narrador')} de personagens), {sum(x['dur'] for x in lines):.1f}s")
    # imagens: plano feito na etapa de assets (story_assets) ou agora, com a cota do momento
    pl = (sc.variety or {}).get("story", {}).get("asset_plan")
    ep_no = int(sc.id or 0)
    if not pl:
        ctx.update(0.08, "Planejando imagens (novas × banco)")
        pl = planner.plan(ch.slug, b, ep, fmt, seed=ep_no)
        if pl["new"]:
            ctx.log(f"Gerando {pl['new']} imagens novas (cota grátis do dia)")
            planner.generate_needs(ch.slug, b, pl, log=ctx.log, check=ctx.check)
    recent = _recent_eps(ch.slug, ep_no)
    visuals, used, missing = planner.resolve(ch.slug, b, ep, pl, episode_no=ep_no, recent_eps=recent, seed=ep_no)
    if any(v is None for v in visuals):
        raise RuntimeError("Banco de imagens vazio para este canal e sem cota para gerar — rode 'Gerar banco' quando a cota voltar")
    bank.mark_used(ch.slug, used, ep_no)
    por = {}
    for c in b.get("characters") or []:
        pr = bank.find(ch.slug, "portrait", char=c["id"], limit=1)
        if pr:
            por[c["id"]] = {**pr[0], "file": str(bank.file_path(ch.slug, pr[0]["file"]))}
    part = int(ep.get("part") or 1)
    label = f"PARTE {part} · CONTINUA…"
    spec = director.direct(ep, visuals, lines, b, W=W, H=H, fps=30, seed=ep_no * 31 + part, part_label=label, portraits=por)
    (workdir / "story_spec.json").write_text(json.dumps({k: v for k, v in spec.items() if not k.startswith("_")}, ensure_ascii=False,
                                                       default=str), encoding="utf-8")
    ctx.update(0.15, f"Desenhando {len(spec['shots'])} tomadas")
    out = workdir / f"{ch.slug}_{video_id}.mp4"
    music_bed = None
    try:
        from .. import music
        music_bed = music.ambient_track(spec["duration"] + 1, seed=ep_no, mood=(sc.variety or {}).get("music_mood") or "suspense dark")
    except Exception as e:  # noqa: BLE001
        ctx.log(f"Trilha base indisponível ({e}) — só o drone")
    if not vertical:
        spec["output_size"] = [1920, 1080]
    r = R.render(spec, out, workdir / "render", progress=lambda p: ctx.update(0.15 + 0.8 * p), check=ctx.check, music_bed=music_bed)
    ctx.log(f"Render: {r['frames']} quadros em {r['seconds']}s · {r['loudness'].get('measured_lufs')} → -14 LUFS")
    thumb = R.thumbnail(spec, spec["hero_t"], ep.get("thumbnail_text") or sc.title, workdir / "thumb.jpg", part_label=f"PARTE {part}")
    images = []
    for aid in dict.fromkeys(used):
        a = bank.get(ch.slug, aid) or {}
        images.append({"kind": "ai", "source": a.get("source", ""), "asset": aid, "type": a.get("type")})
    assets = {
        "template": "historia", "duration": spec["duration"], "narration_end": spec["narration_end"], "images": images,
        "scenes": [{"start": ln["start"], "end": ln["end"], "text": ln["text"], "visual": "historia"} for ln in spec["lines"]],
        "story": {"shots": len(spec["shots"]), "new_images": sum(1 for n in pl["needs"] if n.get("asset")),
                  "reused": len(set(used)) - sum(1 for n in pl["needs"] if n.get("asset")), "widgets": sorted({w["type"] for w in spec["widgets"]}),
                  "part": part, "missing": missing, "render_seconds": r["seconds"]},
        "audio": {"loudness": r["loudness"]}, "loop": False, "opening_type": (sc.variety or {}).get("opening_type"),
        "chapters": _chapters(ep, spec) if not vertical else [],
    }
    (workdir / "assets.json").write_text(json.dumps(assets, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"path": str(out.relative_to(MEDIA_DIR)), "thumbnail": str(thumb.relative_to(MEDIA_DIR)),
            "duration": spec["duration"], "assets": assets}


def _chapters(ep: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for bt, ln in zip(ep["beats"], spec["lines"]):
        if bt.get("chapter") and (not out or ln["start"] - out[-1]["start"] >= 12):
            out.append({"start": 0.0 if not out else round(ln["start"], 1), "title": str(bt["chapter"])[:60]})
    return out if len(out) >= 3 else []


def _recent_eps(slug: str, ep_no: int, n: int = 4) -> set[int]:
    eps = set()
    for a in bank.load(slug):
        for e in a.get("episodes") or []:
            if e != ep_no:
                eps.add(e)
    return set(sorted(eps)[-n:])
