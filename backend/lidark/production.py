"""Produção do vídeo: narração → tempos das palavras → imagens → trilha/efeitos → render → thumbnail."""
from __future__ import annotations

import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from . import captions, music, tts, visuals
from . import config
from .config import MEDIA_DIR
from .db import session
from .jobs import JobContext
from .media import audio_duration, decode_audio, run_ffmpeg
from .models import Channel, Script
from .render.core import Clip, SceneT, Timeline, Word, render
from .render.infographics import KINDS as GRAPHIC_KINDS

log = logging.getLogger("lidark.production")
FPS = 30
OUTRO_SECONDS = 2.4


def produce_video(ch: Channel, sc: Script, video_id: int, ctx: JobContext) -> dict[str, Any]:
    vertical = sc.format == "short"
    W, H = (1080, 1920) if vertical else (1920, 1080)
    workdir = MEDIA_DIR / ch.slug / f"video_{video_id}"
    workdir.mkdir(parents=True, exist_ok=True)
    from . import content
    from .render.infographics import normalize

    def prep(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = content.clean_ending([s for s in raw if s.get("text", "").strip()], ch.cta)  # vale p/ roteiros editados
        for i, s in enumerate(out):
            v = s.get("visual") or {}
            if v.get("kind") == "bigtext":  # cena só de texto não é mais usada: vira imagem
                txt = (v.get("data") or {}).get("text") or s.get("label") or ""
                out[i] = {**s, "visual": {"kind": "real", "query": v.get("query") or txt or s["text"][:60],
                                          "query_pt": v.get("query_pt") or txt}}
            elif v.get("kind") in GRAPHIC_KINDS:
                data = normalize(v)
                if data is None:
                    ctx.log(f"Cena {i + 1}: dados do gráfico '{v.get('kind')}' incompletos — usando imagem")
                    out[i] = {**s, "visual": {"kind": "real", "query": v.get("query") or s.get("label") or s["text"][:60],
                                              "query_pt": v.get("query_pt", "")}}
                else:
                    out[i] = {**s, "visual": {**v, "data": data}}
        return out

    def save_scenes(new_scenes: list[dict[str, Any]]) -> None:
        with session() as s_:
            db = s_.get(Script, sc.id)
            if db:
                db.scenes = new_scenes
                s_.add(db)
                s_.commit()

    # 0) roteiro com o tamanho certo (também corrige roteiros antigos/editados) ------------
    raw = sc.scenes
    plan = sc.variety or {}
    expanded = content.ensure_length(ch, sc.title, raw, sc.format, ctx.log, seconds=plan.get("seconds"))
    if expanded is not raw:
        save_scenes(expanded)
    scenes = prep(expanded)
    if not scenes:
        raise RuntimeError("Roteiro sem cenas")
    full_text = " ".join(s["text"].strip() for s in scenes)

    # 1) narração ------------------------------------------------------------
    ctx.update(0.03, "Gravando narração")

    def record(rate: str) -> tuple[dict[str, Any], float]:
        if ch.voice_provider == "edge":
            try:  # narração dirigida: ritmo e pausas de narrador, frase a frase
                v = tts.synthesize_directed([x["text"] for x in scenes], workdir / "voice.wav", ch.voice_name, rate)
                return v, audio_duration(v["path"])
            except Exception as e:  # noqa: BLE001
                ctx.log(f"Narração dirigida falhou ({e}) — gravando em ritmo único")
        style = (ch.voice_style + ". Faça uma pausa curta antes das revelações, deixe as perguntas respirarem, "
                 "fale datas e números com clareza e comece o gancho com energia.")
        v = tts.synthesize(full_text, workdir / "voice.mp3", provider=ch.voice_provider, voice=ch.voice_name,
                           rate=rate, style=style)
        return v, audio_duration(v["path"])

    base_rate = plan.get("voice_rate") or ch.voice_rate
    voice, narr_dur = record(base_rate)
    min_total = max(61.0, float(plan.get("seconds") or ch.short_seconds or 60) - 2) if vertical else float(ch.long_minutes or 6) * 60 * 0.9
    for _ in range(2):  # narração real ainda curta → acrescenta conteúdo e regrava (nunca enche com tela final)
        if narr_dur + OUTRO_SECONDS >= min_total:
            break
        wps = max(1.5, len(full_text.split()) / max(1.0, narr_dur))
        missing = int((min_total - narr_dur - OUTRO_SECONDS) * wps) + 6
        ctx.log(f"Narração curta ({narr_dur:.1f}s) — acrescentando ~{missing} palavras ao roteiro")
        try:
            more = content.expand_script(ch, sc.title, expanded, missing)
        except Exception as e:  # noqa: BLE001
            ctx.log(f"Expansão não funcionou: {e}")
            continue
        expanded = more
        save_scenes(expanded)
        scenes = prep(expanded)
        full_text = " ".join(s["text"].strip() for s in scenes)
        voice, narr_dur = record(base_rate)
    gap = min_total - narr_dur - OUTRO_SECONDS
    if 0 < gap <= narr_dur * 0.06 and voice.get("provider") == "edge":  # ajuste fino imperceptível (≤ 6%)
        cur = int((base_rate or "+0%").strip("%") or 0)
        new_rate = cur - int(gap / narr_dur * 100) - 1
        voice, narr_dur = record(f"{new_rate:+d}%")
        ctx.log(f"Ajuste fino de velocidade: {new_rate:+d}%")
    ctx.log(f"Narração: {voice['provider']} / {voice['voice']} — {narr_dur:.1f}s ({len(full_text.split())} palavras)")

    # 2) tempo de cada palavra --------------------------------------------------
    ctx.update(0.1, "Sincronizando legendas palavra por palavra")
    timed = captions.word_timeline(full_text, voice["path"], narr_dur, voice.get("words"))
    words: list[Word] = []
    scene_words: list[list[Word]] = []
    idx = 0
    for s in scenes:
        n = len(s["text"].split())
        emph = {captions.norm(x) for e in (s.get("emphasis") or []) for x in str(e).split()}
        ws = []
        for tw in timed[idx: idx + n]:
            nw = captions.norm(tw["w"])
            hi = bool(nw) and (nw in emph or any(c.isdigit() for c in nw))
            ws.append(Word(tw["w"], tw["start"], tw["end"], hi))
        idx += n
        words += ws
        scene_words.append(ws)
    narration_end = max(narr_dur, words[-1].end if words else narr_dur)
    if ch.voice_provider == "edge" and voice.get("words") and len(voice["words"]) < len(timed) * 0.7:
        ctx.log("Aviso: poucos tempos do TTS, alinhamento estimado")

    # 3) imagens ---------------------------------------------------------------
    ctx.update(0.15, f"Buscando e avaliando imagens ({len(scenes)} cenas)")
    tpl = plan.get("template") or ch.template or "ouro"
    if tpl == "ouro":
        ai_size = (1024, 768)
    else:
        ai_size = (768, 1344) if vertical else (1344, 768)
    context = f"{sc.title}. {sc.hook}"
    done = [0]
    used_urls: set[str] = recent_image_urls(ch.id, video_id)  # nunca repete foto de vídeos recentes
    if used_urls:
        ctx.log(f"Evitando {len(used_urls)} imagens já usadas em vídeos recentes")

    stats = {"hd": 0, "clips": 0}
    import threading
    clip_lock = threading.Lock()
    max_clips = 3 if vertical else 8  # filmagem é ouro, mas foto bem escolhida também segura — sem exagero

    def _clip_slot() -> bool:
        with clip_lock:
            if stats["clips"] >= max_clips:
                return False
            stats["clips"] += 1
            return True

    def pick(i_s):
        i, s = i_s
        kind = (s.get("visual") or {}).get("kind", "real")
        if kind in GRAPHIC_KINDS and kind != "dossier":
            done[0] += 1
            return {"kind": "graphic", "graphic": kind}
        if kind == "dossier":
            s = {**s, "visual": {**(s.get("visual") or {}), "kind": "real"}}
            r = visuals.pick_scene_image(s, context, ch.image_style, ai_size, "real",
                                         log_fn=lambda m: ctx.log(f"Cena {i + 1}: {m}"), used=used_urls)
            done[0] += 1
            return _hd(r) or {"kind": "graphic", "graphic": "dossier"}
        wants_video = s.get("video") or (s.get("visual") or {}).get("video")
        if wants_video and kind == "real" and config.get("footage_enabled") and _clip_slot():
            from . import footage
            ws = scene_words[i] if i < len(scene_words) else []
            need = (ws[-1].end - ws[0].start + 0.4) if ws else 4.0
            try:
                rv = footage.pick_scene_clip(s, context, need, (W, H), used_urls,
                                             log_fn=lambda m: ctx.log(f"Cena {i + 1}: {m}"))
            except Exception as e:  # noqa: BLE001
                rv = None
                ctx.log(f"Cena {i + 1}: filmagem falhou ({e}) — usando foto")
            if rv:
                done[0] += 1
                ctx.update(0.15 + 0.4 * done[0] / len(scenes), f"Imagens: {done[0]}/{len(scenes)}")
                return rv
            with clip_lock:
                stats["clips"] -= 1  # não achou: libera a vaga para outra cena
        r = visuals.pick_scene_image(s, context, ch.image_style, ai_size, ch.visual_mode,
                                     log_fn=lambda m: ctx.log(f"Cena {i + 1}: {m}"), used=used_urls)
        done[0] += 1
        ctx.update(0.15 + 0.4 * done[0] / len(scenes), f"Imagens: {done[0]}/{len(scenes)}")
        return _hd(r)

    def _hd(r):
        """Foto real pequena → versão ampliada com IA (nítida em tela cheia)."""
        if r and r.get("path") and r.get("kind") == "real":
            from .upscale import enhance
            hd = enhance(r["path"])
            if str(hd) != str(r["path"]):
                r = {**r, "orig_path": r["path"], "path": str(hd)}
                stats["hd"] += 1
        return r

    with ThreadPoolExecutor(3) as ex:
        picks = list(ex.map(pick, enumerate(scenes)))
    if stats["hd"]:
        ctx.log(f"{stats['hd']} foto(s) pequena(s) ampliada(s) com IA para ficarem nítidas em tela cheia")
    n_clips = sum(1 for p in picks if p and p.get("clip"))
    if n_clips:
        ctx.log(f"{n_clips} cena(s) com filmagem real")
    images: list[Image.Image | None] = []
    for i, p in enumerate(picks):
        if p and p.get("kind") == "graphic":
            images.append(images[-1] if images else None)
        elif p and p.get("path"):
            images.append(Image.open(p["path"]).convert("RGB"))
        else:
            images.append(None)  # preenchida abaixo com a foto aprovada mais próxima
            picks[i] = {"kind": "reuse"}
    if all(im is None for im in images) and not all((p or {}).get("kind") == "graphic" for p in picks):
        raise RuntimeError("Nenhuma imagem encontrada/gerada. Verifique a internet e a chave do Gemini.")
    # cenas sem imagem própria reaproveitam a foto aprovada mais próxima (com outro enquadramento)
    real_idx = [k for k, p in enumerate(picks) if p and p.get("path")]
    for i, p in enumerate(picks):
        if p and p.get("kind") == "reuse" and real_idx:
            j = min(real_idx, key=lambda k: (abs(k - i), k < i))
            images[i] = images[j]
            ctx.log(f"Cena {i + 1}: sem foto aprovada — reaproveitando a imagem da cena {j + 1}")
    first = next((im for im in images if im is not None), None)
    images = [im or first for im in images]

    # 4) cenas e passos -----------------------------------------------------------
    n = len(scenes)
    mids = list(range(1, n - 1)) if n > 3 else list(range(n))
    steps = 0 if n <= 3 else min(5, max(2, round(len(mids) / 3)))
    scene_ts: list[SceneT] = []
    for i, s in enumerate(scenes):
        ws = scene_words[i]
        start = 0.0 if i == 0 else (ws[0].start if ws else scene_ts[-1].end)
        step = 0
        if steps and i in mids:
            step = 1 + int(mids.index(i) * steps / len(mids))
        label = s.get("label") or (picks[i] or {}).get("label") or ""
        v = s.get("visual") or {}
        graphic = {"kind": v["kind"], "data": v.get("data") or {}} if v.get("kind") in GRAPHIC_KINDS else None
        if graphic and graphic["kind"] == "dossier":
            graphic["data"] = {**graphic["data"], "_photo": bool((picks[i] or {}).get("path"))}
        clip = Clip(picks[i]["clip"]) if (picks[i] or {}).get("clip") else None
        scene_ts.append(SceneT(i, start, 0, s["text"], images[i], label[:28], step, ws, str(s.get("fx") or ""), graphic, clip))
    for i, st in enumerate(scene_ts):
        st.end = scene_ts[i + 1].start if i + 1 < n else narration_end
    # a tela final pode completar no máximo 3s (nunca fica repetindo o encerramento)
    duration = narration_end + OUTRO_SECONDS + min(3.0, max(0.0, min_total - narration_end - OUTRO_SECONDS))
    if vertical and duration < 60:
        ctx.log(f"⚠ Vídeo com {duration:.0f}s (abaixo de 60s) — roteiro ficou curto mesmo após expansão")

    # 5) direção de animação + envelope da voz (boca do mascote) ----------------------------
    env = _envelope(voice["path"], duration)
    tl = Timeline(W, H, FPS, duration, narration_end, sc.title, scene_ts, steps, words, env, {**(ch.theme or {}), "_look": plan.get("look") or {}}, sc.format)
    template = _template(tpl, tl)
    impacts = list(getattr(template, "impacts", []))
    if hasattr(template, "_setup_direction"):
        template._setup_direction()
        impacts = list(template.impacts)

    # 6) áudio final: voz + trilha com ducking + efeitos sincronizados ------------------------
    ctx.update(0.58, "Mixando trilha sonora e efeitos")
    track = music.pick_track(ch.music_mood, duration, ch.slug, focus=plan.get("music_mood", ""))
    if track:
        ctx.log(f"Trilha: {track['title']} ({track['source']})")
    final_audio = workdir / "mix.wav"
    _mix_audio(voice["path"], track["path"] if track else None, [st.start for st in scene_ts[1:]],
               duration, ch.music_volume, final_audio, impacts)

    # 7) render -------------------------------------------------------------------------
    out = workdir / f"{ch.slug}_{video_id}.mp4"
    ctx.update(0.62, "Renderizando vídeo")
    render(tl, template, out, final_audio, progress=lambda p: ctx.update(0.62 + 0.35 * p, f"Renderizando vídeo {int(p * 100)}%"))

    # 8) thumbnail -----------------------------------------------------------------------
    from .render.thumbnail import make_thumbnail
    # miniatura: a imagem da abertura representa o título; senão, a de maior nota
    best = 0 if (picks and picks[0] and picks[0].get("path") and picks[0].get("score", 0) >= 60) else         max((k for k, p in enumerate(picks) if p and p.get("path")), key=lambda k: picks[k].get("score", 0), default=None)
    bg_img = thumbnail_background(sc, scenes, context, ch, used_urls, ctx) or         (images[best] if best is not None else next((im for im in images if im is not None), None))
    thumb_text = (sc.thumbnail_text or sc.title.replace("#Shorts", "")).strip()
    thumb = make_thumbnail(bg_img, thumb_text, ch.theme or {}, workdir / "thumb.jpg", vertical,
                           variant=int(plan.get("thumb_variant", video_id)))
    ctx.log(f"Miniatura criada: “{thumb_text}”")

    credits = []
    for i, p in enumerate(picks):
        if p and p.get("kind") == "real":
            credits.append(f"Cena {i + 1}: {p.get('credit') or p.get('source')} — {p.get('license') or ''} {p.get('page') or ''}".strip())
    assets = {
        "voice": voice | {"words": None}, "music": track, "images": picks, "image_credits": credits,
        "duration": duration, "narration_end": narration_end, "template": tpl,
        "chapters": _chapters(scenes, scene_ts) if not vertical else [], "look": plan.get("look") or {},
        "scenes": [{"start": st.start, "end": st.end, "text": st.text,
                    "visual": (st.graphic or {}).get("kind") or (picks[k] or {}).get("kind", "")}
                   for k, st in enumerate(scene_ts)],
        "captions": {"script_words": len(full_text.split()), "timed_words": len(words),
                     "last_word_end": words[-1].end if words else 0.0},
    }
    (workdir / "assets.json").write_text(json.dumps(assets, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    ctx.log(f"Vídeo pronto: {duration:.1f}s → {out.name}")
    return {"path": str(out.relative_to(MEDIA_DIR)), "thumbnail": str(thumb.relative_to(MEDIA_DIR)),
            "duration": duration, "assets": assets}


def thumbnail_background(sc: Script, scenes: list[dict[str, Any]], context: str, ch: Channel,
                         used: set[str], ctx: JobContext) -> Image.Image | None:
    """Busca uma imagem específica para a miniatura: a que melhor representa o TÍTULO (avaliada pela IA de visão)."""
    first = (scenes[0].get("visual") or {}) if scenes else {}
    title = sc.title.replace("#Shorts", "").strip()
    scene = {"text": f"Miniatura do vídeo: {title}", "label": sc.thumbnail_text,
             "visual": {"kind": "real", "query": first.get("query") or title, "query_pt": first.get("query_pt") or title}}
    try:
        r = visuals.pick_scene_image(scene, context, ch.image_style, (1280, 720), "real",
                                     log_fn=lambda m: ctx.log(f"Miniatura: {m}"), used=set())
        if r and r.get("path") and r.get("score", 0) >= 70:
            from .upscale import enhance
            return Image.open(enhance(r["path"])).convert("RGB")
    except Exception as e:  # noqa: BLE001
        ctx.log(f"Miniatura: busca falhou ({e})")
    return None


def recent_image_urls(channel_id: int, exclude_video: int, limit: int = 15) -> set[str]:
    """URLs das fotos usadas nos últimos vídeos do canal (para não repetir a mesma imagem)."""
    from sqlmodel import select
    from .models import Video
    with session() as s:
        vids = s.exec(select(Video).where(Video.channel_id == channel_id, Video.id != exclude_video)
                      .order_by(Video.id.desc()).limit(limit)).all()
    urls: set[str] = set()
    for v in vids:
        for p in (v.assets or {}).get("images") or []:
            if isinstance(p, dict) and p.get("url"):
                urls.add(p["url"])
    return urls


def _chapters(scenes: list[dict[str, Any]], scene_ts: list) -> list[dict[str, Any]]:
    """Capítulos do vídeo longo (o roteiro marca a 1ª cena de cada bloco com "chapter")."""
    out: list[dict[str, Any]] = []
    for s, st in zip(scenes, scene_ts):
        title = str(s.get("chapter") or "").strip()
        if not title:
            continue
        if out and st.start - out[-1]["start"] < 12:  # YouTube exige ≥10s por capítulo
            continue
        out.append({"start": 0.0 if not out else round(st.start, 1), "title": title[:60]})
    if out:
        out[0]["start"] = 0.0
    return out if len(out) >= 3 else []


def _template(name: str, tl: Timeline):
    if name == "livre":
        from .render.livre import LivreTemplate
        return LivreTemplate(tl)
    if name == "cinematic":
        from .render.cinematic import CinematicTemplate
        return CinematicTemplate(tl)
    from .render.ouro import OuroTemplate
    return OuroTemplate(tl)


def _mix_audio(voice: str, track: str | None, cuts: list[float], duration: float, music_vol: float, out: Path,
               impacts: list[float] | None = None) -> None:
    whoosh, pop, hit = music.sfx("whoosh"), music.sfx("pop"), music.sfx("impact")
    inputs = ["-i", voice]
    filters = ["[0:a]aresample=48000,loudnorm=I=-16:TP=-1.5:LRA=11,apad[v0]"]
    mix = ["[v0]"]
    idx = 1
    if track:
        inputs += ["-stream_loop", "-1", "-i", track]
        filters.append(f"[{idx}:a]aresample=48000,volume={music_vol * 2.2:.3f},afade=t=in:d=0.8,"
                       f"afade=t=out:st={max(0, duration - 1.8):.2f}:d=1.8,atrim=0:{duration:.2f}[mus]")
        filters.append("[v0]asplit=2[voice][vkey]")
        filters.append("[mus][vkey]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[ducked]")
        mix = ["[voice]", "[ducked]"]
        idx += 1
    inputs += ["-i", str(whoosh), "-i", str(pop), "-i", str(hit)]
    w_i, p_i, h_i = idx, idx + 1, idx + 2
    impacts = [x for x in (impacts or []) if x > 0.2][:20]
    if impacts:
        filters.append(f"[{h_i}:a]asplit={len(impacts)}" + "".join(f"[h{k}]" for k in range(len(impacts))))
        for k, c in enumerate(impacts):
            filters.append(f"[h{k}]adelay={int(max(0, c - 0.03) * 1000)}:all=1,volume=0.45[hd{k}]")
            mix.append(f"[hd{k}]")
    cuts = [c for c in cuts if c > 0.3][:40]
    if cuts:
        filters.append(f"[{w_i}:a]asplit={len(cuts)}" + "".join(f"[w{k}]" for k in range(len(cuts))))
        filters.append(f"[{p_i}:a]asplit={len(cuts)}" + "".join(f"[p{k}]" for k in range(len(cuts))))
        for k, c in enumerate(cuts):
            filters.append(f"[w{k}]adelay={int(max(0, c - 0.18) * 1000)}:all=1,volume=0.35[wd{k}]")
            filters.append(f"[p{k}]adelay={int((c + 0.05) * 1000)}:all=1,volume=0.30[pd{k}]")
            mix += [f"[wd{k}]", f"[pd{k}]"]
    filters.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{duration:.2f},"
                   "alimiter=limit=0.95[out]")
    run_ffmpeg([*inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-ac", "2", str(out)])


def _envelope(voice: str, duration: float) -> np.ndarray:
    sr = 24000
    data = decode_audio(voice, sr)
    hop = sr // FPS
    n = int(math.ceil(duration * FPS))
    env = np.zeros(n, np.float32)
    for i in range(n):
        seg = data[i * hop: (i + 1) * hop]
        if len(seg):
            env[i] = float(np.sqrt(np.mean(seg ** 2)))
    ref = np.percentile(env[env > 0], 90) if np.any(env > 0) else 1
    env = np.clip(env / (ref or 1), 0, 1)
    # suavização (ataque rápido, soltura lenta)
    sm = np.zeros_like(env)
    for i in range(n):
        prev = sm[i - 1] if i else 0
        sm[i] = env[i] if env[i] > prev else prev * 0.6 + env[i] * 0.4
    return sm
