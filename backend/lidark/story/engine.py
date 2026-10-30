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


# filtros de "aparelho" (FFmpeg) — a voz soa saindo do dispositivo
DEVICE_AF = {
    "tv": "highpass=f=180,lowpass=f=6500,aecho=0.8:0.6:28|47:0.16|0.09",
    "radio": "highpass=f=450,lowpass=f=3000,acompressor=threshold=0.08:ratio=8:attack=5:release=80:makeup=2.5,asoftclip=type=tanh",
    "phone": "highpass=f=320,lowpass=f=3400,acompressor=threshold=0.1:ratio=6:attack=5:release=60:makeup=2",
    "comms": "highpass=f=300,lowpass=f=3000,acompressor=threshold=0.1:ratio=6:makeup=2,asoftclip=type=tanh",
    "newsboy": "aecho=0.8:0.7:70|150:0.22|0.12",
    "proclamation": "aecho=0.8:0.7:80|170:0.25|0.14",
}


def _gemini_ok_today() -> int:
    from . import providers
    led = providers._ledger().get("gemini_tts") or {}
    from datetime import datetime
    used = led.get("images", 0) if led.get("day") == datetime.now().strftime("%Y-%m-%d") else 0
    return max(0, int(providers.conf().get("gemini_tts_daily") or 0) - int(used))


def plan_voices(b: dict[str, Any], beats: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Decide o provedor de cada papel para o episódio INTEIRO: Gemini só se a cota do dia cobre todas as falas do
    papel; senão o papel todo vai de edge (nunca mistura vozes do mesmo personagem num episódio)."""
    count: dict[str, int] = {}
    for bt in beats:
        r = bt.get("speaker", "narrador") or "narrador"
        count[r] = count.get(r, 0) + 1
    left = _gemini_ok_today()
    out = {}
    for role in sorted(count, key=lambda r: (r != "narrador", count[r])):
        cfg = B.voice_for(b, role)
        if cfg.get("provider") == "gemini":
            if count[role] <= left:
                left -= count[role]
            else:
                cfg = _edge_fallback(b, role, cfg)
        out[role] = cfg
    return out


def _edge_fallback(b: dict[str, Any], role: str, cfg: dict[str, Any]) -> dict[str, Any]:
    fb = dict(cfg.get("fallback") or {})
    if not fb:
        c = B.character(b, role)
        base = B.DEFAULT_VOICES.get(role) or (
            {"voice": c.get("voice"), "rate": c.get("rate"), "pitch": c.get("pitch")} if c else B.DEFAULT_VOICES["narrador"])
        fb = {k: base.get(k) for k in ("voice", "rate", "pitch")}
    v = str(fb.get("voice") or "")
    if not v.startswith("pt-BR"):  # voz Kokoro (pf_*/pm_*) não existe no edge: usa a equivalente
        fb["voice"] = "pt-BR-FranciscaNeural" if v.startswith("pf_") else "pt-BR-AntonioNeural"
    return {**fb, "provider": "edge", "fallback_from": cfg.get("provider") or "gemini"}


def _kokoro_speed(cfg: dict[str, Any], emotion: str, narrator: bool) -> float:
    de, _ = tts.EMOTION.get(emotion, (0, 0)) if narrator else (0, 0)
    return round(float(cfg.get("speed") or 1.0) * (1 + de / 100), 3)


def _synth_one(text: str, cfg: dict[str, Any], out: Path, emotion: str, narrator: bool) -> None:
    if cfg.get("provider") == "kokoro":
        from .. import voice_kokoro
        voice_kokoro.synth_batch([{"text": text, "voice": cfg.get("voice") or "pf_dora",
                                   "speed": _kokoro_speed(cfg, emotion, narrator), "out": str(out)}])
        return
    if cfg.get("provider") == "gemini":
        style = cfg.get("style") or ""
        if emotion:
            style = (style + f". Emoção desta fala: {emotion}").strip(". ")
        tts._gemini(text, out, cfg.get("voice") or "Charon", style)
        from . import providers
        providers.record("gemini_tts", images=1)
        return
    de, dp = tts.EMOTION.get(emotion, (0, 0)) if narrator else (0, 0)
    r = _pct(cfg.get("rate")) + de
    pitch = cfg.get("pitch") or "+0Hz"
    try:
        p0 = int(str(pitch).replace("Hz", "")) + dp
        pitch = f"{p0:+d}Hz"
    except ValueError:
        pass
    tts._edge(text, out, cfg.get("voice") or "pt-BR-AntonioNeural", f"{r:+d}%", pitch)


def synth_lines(ch: Channel, b: dict[str, Any], beats: list[dict[str, Any]], workdir: Path, rate: str = "") -> list[dict[str, Any]]:
    """Uma faixa por beat, na voz do PAPEL (narrador, personagem, aparelho). Aparelhos recebem o filtro de áudio
    (TV, rádio, celular, rádio de bordo, rua). Papel em Gemini que falhar no meio é refeito INTEIRO em edge."""
    from ..media import run_ffmpeg
    d = workdir / "voz"
    d.mkdir(parents=True, exist_ok=True)
    plan = plan_voices(b, beats)
    paths: dict[int, Path] = {}
    roles: dict[str, list[int]] = {}
    for i, bt in enumerate(beats):
        if bt.get("silent"):  # aparelho só chia/apita: sem voz, só o tempo do efeito (o diretor põe o som)
            p = d / f"{i:02d}_silencio.wav"
            if not p.exists():
                run_ffmpeg(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "1.8", str(p)])
            paths[i] = p
            continue
        roles.setdefault(bt.get("speaker", "narrador") or "narrador", []).append(i)
    def _path(i: int, cfg: dict[str, Any]) -> Path:
        bt = beats[i]
        key = hashlib.sha1(f"{bt['text']}|{json.dumps(cfg, sort_keys=True)}|{bt.get('emotion')}".encode()).hexdigest()[:12]
        return d / f"{i:02d}_{key}{'.wav' if cfg.get('provider') == 'kokoro' else '.mp3'}"

    # Kokoro (local): todas as falas do episódio num processo só (o modelo carrega uma vez). Se falhar, os papéis
    # Kokoro inteiros vão para o edge — nunca metade de um personagem em cada voz.
    kjobs = [{"text": beats[i]["text"], "voice": plan[r].get("voice") or "pf_dora", "out": str(_path(i, plan[r])),
              "speed": _kokoro_speed(plan[r], str(beats[i].get("emotion") or "").lower(), r == "narrador")}
             for r, idxs in roles.items() if plan[r].get("provider") == "kokoro" for i in idxs]
    if kjobs:
        try:
            from .. import voice_kokoro
            voice_kokoro.synth_batch(kjobs)
        except Exception as e:  # noqa: BLE001
            log.warning("Kokoro indisponível (%s) — papéis Kokoro vão para o edge", e)
            for r in roles:
                if plan[r].get("provider") == "kokoro":
                    plan[r] = _edge_fallback(b, r, plan[r])
    for role, idxs in roles.items():
        cfg = plan[role]
        for attempt in range(2):
            try:
                for i in idxs:
                    bt = beats[i]
                    p = _path(i, cfg)
                    if not p.exists() or p.stat().st_size < 1000:
                        _synth_one(bt["text"], cfg, p, str(bt.get("emotion") or "").lower(), role == "narrador")
                    paths[i] = p
                break
            except Exception as e:  # noqa: BLE001
                if cfg.get("provider") != "gemini" or attempt:
                    raise
                log.warning("Gemini TTS falhou no papel %s (%s) — papel inteiro em edge", role, e)
                cfg = plan[role] = _edge_fallback(b, role, cfg)
    out = []
    for i, bt in enumerate(beats):
        role = bt.get("speaker", "narrador") or "narrador"
        p = paths[i]
        if bt.get("silent"):
            out.append({"audio": str(p), "dur": 1.8, "speaker": role, "voice": {}, "silent": True, "sfx": bt.get("sfx") or "static"})
            continue
        dev = (bt.get("device") or {}).get("type") if isinstance(bt.get("device"), dict) else None
        af = DEVICE_AF.get(role) or DEVICE_AF.get(dev or "")  # ex.: a Nina mandando áudio → voz dela com filtro de celular
        if af:
            q = p.with_name(p.stem + f"_{role}.wav")
            if not q.exists():
                run_ffmpeg(["-i", str(p), "-af", af, "-ar", "48000", "-ac", "1", str(q)])
            p = q
        out.append({"audio": str(p), "dur": round(audio_duration(p), 3), "speaker": role, "voice": plan[role]})
    return out


def episode_of(sc: Script, *, vetor_beats: bool = False) -> dict[str, Any]:
    st = dict((sc.variety or {}).get("story") or {})
    # motor vetorial não usa imagens: sem beats, a etapa story_assets planeja zero imagens e segue direto para o render
    st["beats"] = [] if st.get("render_style") == "vetor" and not vetor_beats else [dict(x) for x in sc.scenes or []]
    st.setdefault("title", sc.title)
    st.setdefault("thumbnail_text", sc.thumbnail_text)
    return st


def produce_story(ch: Channel, sc: Script, video_id: int, ctx: Any) -> dict[str, Any]:
    from ..render import story as R
    b = B.load(ch.slug)
    if b.get("render_style") == "vetor":
        from . import vetor_director
        return vetor_director.produce(ch, sc, video_id, ctx, b, episode_of(sc, vetor_beats=True))
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
    label = ep.get("end_label") or f"PARTE {part} · CONTINUA…"  # série: final = "FIM DA SÉRIE · próxima: …"
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
    thumb = R.thumbnail(spec, spec["hero_t"], ep.get("thumbnail_text") or sc.title, workdir / "thumb.jpg",
                        part_label=("SÉRIE COMPLETA" if ep.get("long_of_series") else f"PARTE {part}") if (part or ep.get("long_of_series")) else "")
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
