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

from . import captions, music, sfx, tts, visuals
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
LOOP_TAIL = 0.3  # Short em loop: tempo depois da última palavra (o fim funde no 1º quadro)
LOOP_XFADE = 0.5  # duração da fusão de imagem e som do fim para o começo


def _voice_sig(scenes: list[dict[str, Any]]) -> str:
    """Assinatura da narração: texto + direção (delivery). Sem delivery é igual à assinatura antiga."""
    from . import content
    sig = content.scenes_sig(scenes)
    dl = [s.get("delivery") for s in scenes]
    if any(dl):
        import hashlib
        sig += hashlib.sha1(json.dumps(dl, sort_keys=True, default=str).encode()).hexdigest()[:8]
    return sig


def tv_metrics(template: Any) -> dict[str, Any]:
    """Tamanhos de texto do layout (px) para a checagem de legibilidade na TV do inspetor."""
    k = float(getattr(template, "k", 1.0))
    H = int(getattr(template, "H", 1080))
    style = getattr(template, "cap_style", "classic")
    cap = (62 if style in ("karaoke", "bold") else 52) * k
    card = getattr(template, "card", None)
    W = int(getattr(template, "W", 1920))
    return {"H": H, "W": W, "caption_px": round(cap, 1),
            "caption_cx": int((card[0] + card[2]) / 2) if card else W // 2,
            "caption_cy": int(getattr(template, "caption_cy", 0)), "caption_maxw": int(getattr(template, "caption_maxw", 0)),
            "small_text_px": round(min(27, 28, 34) * k, 1),  # etiqueta da cena / PASSO x/n / título do cabeçalho
            "caption_boxed": style in ("classic", "highlight")}


def produce_video(ch: Channel, sc: Script, video_id: int, ctx: JobContext) -> dict[str, Any]:
    if (sc.variety or {}).get("structure") == "historia":  # episódio do Modo História tem motor próprio
        from .story.engine import produce_story
        return produce_story(ch, sc, video_id, ctx)
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

    # etapas prontas ficam salvas: se o servidor reiniciar no meio, o vídeo continua de onde parou
    ck_path = workdir / "checkpoint.json"
    try:
        ck: dict[str, Any] = json.loads(ck_path.read_text(encoding="utf-8")) if ck_path.exists() else {}
    except (OSError, ValueError):
        ck = {}
    import threading
    ck_lock = threading.Lock()

    def save_ck() -> None:
        with ck_lock:
            ck_path.write_text(json.dumps(ck, ensure_ascii=False, default=str), encoding="utf-8")

    facts_hint = ""
    if sc.idea_id:
        from .models import Idea
        with session() as s_:
            idea = s_.get(Idea, sc.idea_id)
        facts_hint = "; ".join(f.get("claim", "") for f in (idea.facts if idea else []) if f.get("verdict") == "confirmado")

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
            try:  # narração dirigida: ritmo e pausas de narrador, frase a frase (+ delivery de cada cena)
                v = tts.synthesize_directed(scenes, workdir / "voice.wav", ch.voice_name, rate)
                return v, audio_duration(v["path"])
            except Exception as e:  # noqa: BLE001
                ctx.log(f"Narração dirigida falhou ({e}) — gravando em ritmo único")
        style = (ch.voice_style + ". Faça uma pausa curta antes das revelações, deixe as perguntas respirarem, "
                 "fale datas e números com clareza e comece o gancho com energia. " + tts.delivery_hint(scenes)).strip()
        ref = None
        if ch.voice_provider == "local":
            from . import voice_local
            ref = voice_local.ref_path(ch) if ch.voice_name == "ref" else None
        v = tts.synthesize(full_text, workdir / "voice.mp3", provider=ch.voice_provider, voice=ch.voice_name,
                           rate=rate, style=style, ref=ref)
        if ch.voice_provider == "local" and v.get("provider") != "local":
            ctx.log("Voz local indisponível agora (RAM/VRAM/instalação) — narração com Microsoft Neural")
        return v, audio_duration(v["path"])

    # Short em loop (o roteiro pediu: a última frase emenda na primeira): sem tela final, o fim funde no 1º quadro
    wants_loop = bool(plan.get("loop") or (scenes and scenes[-1].get("loop")))
    loop = bool(vertical and wants_loop and config.get("loop_enabled")
                and str((ch.theme or {}).get("loop_ok") or "on") != "off")
    outro_s = LOOP_TAIL if loop else OUTRO_SECONDS
    if loop:
        ctx.log("Short em loop: sem tela final — o fim emenda no começo (imagem e som)")
    base_rate = plan.get("voice_rate") or ch.voice_rate
    # Short: segue a duração sorteada no plano (sem piso de 60s — Shorts não têm duração mínima para monetizar)
    min_total = max(20.0, float(plan.get("seconds") or ch.short_seconds or 45) - 4) if vertical else float(ch.long_minutes or 6) * 60 * 0.9
    cached = ck.get("voice") if ck.get("voice_sig") == _voice_sig(scenes) else None
    if cached and Path(cached["path"]).exists():
        voice, narr_dur = cached, float(ck["narr_dur"])
        ctx.log(f"Narração reaproveitada da etapa anterior ({narr_dur:.1f}s)")
    else:
        voice, narr_dur = record(base_rate)
    for _ in range(0 if cached else 2):  # narração real ainda curta → acrescenta conteúdo e regrava (nunca enche com tela final)
        if narr_dur + outro_s >= min_total:
            break
        wps = max(1.5, len(full_text.split()) / max(1.0, narr_dur))
        missing = int((min_total - narr_dur - outro_s) * wps) + 6
        ctx.log(f"Narração curta ({narr_dur:.1f}s) — acrescentando ~{missing} palavras ao roteiro")
        try:
            more = content.expand_script(ch, sc.title, expanded, missing, facts_hint)
        except Exception as e:  # noqa: BLE001
            ctx.log(f"Expansão não funcionou: {e}")
            continue
        expanded = more
        save_scenes(expanded)
        scenes = prep(expanded)
        full_text = " ".join(s["text"].strip() for s in scenes)
        voice, narr_dur = record(base_rate)
    gap = min_total - narr_dur - outro_s
    if not cached and 0 < gap <= narr_dur * 0.06 and voice.get("provider") == "edge":  # ajuste fino imperceptível (≤ 6%)
        cur = int((base_rate or "+0%").strip("%") or 0)
        new_rate = cur - int(gap / narr_dur * 100) - 1
        voice, narr_dur = record(f"{new_rate:+d}%")
        ctx.log(f"Ajuste fino de velocidade: {new_rate:+d}%")
    if not cached:
        ck.update(voice=voice, narr_dur=narr_dur, voice_sig=_voice_sig(scenes), picks={})
        save_ck()
    ctx.log(f"Narração: {voice['provider']} / {voice['voice']} — {narr_dur:.1f}s ({len(full_text.split())} palavras)")
    if (voice.get("directed") or {}).get("delivery"):
        dd = voice["directed"]
        ctx.log(f"Direção do roteiro aplicada em {dd['delivery']} cena(s) ({dd.get('emphasis_beats', 0)} ênfase(s) com micro-pausa)")

    # 2) tempo de cada palavra --------------------------------------------------
    ctx.update(0.1, "Sincronizando legendas palavra por palavra")
    timed = captions.word_timeline(full_text, voice["path"], narr_dur, voice.get("words"))
    words: list[Word] = []
    scene_words: list[list[Word]] = []
    idx = 0
    for s in scenes:
        n = len(s["text"].split())
        emph_src = list(s.get("emphasis") or []) + list((s.get("delivery") or {}).get("emphasis") or [])
        emph = {captions.norm(x) for e in emph_src for x in str(e).split() if captions.norm(x)}
        seg = timed[idx: idx + n]
        kinds = captions.highlight_kinds([tw["w"] for tw in seg], emph)  # datas, números, nomes e ênfases
        ws = [Word(tw["w"], tw["start"], tw["end"], bool(kd), kd) for tw, kd in zip(seg, kinds)]
        idx += n
        words += ws
        scene_words.append(ws)
    narration_end = float(max(narr_dur, words[-1].end if words else narr_dur))
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

    stats = {"hd": 0, "clips": 0, "fallback_graphics": 0}
    clip_lock = threading.Lock()
    max_clips = 3 if vertical else 8  # filmagem é ouro, mas foto bem escolhida também segura — sem exagero
    max_fallback = max(2, int(len(scenes) * 0.3))  # cenas que podem virar gráfico por falta de foto boa
    footage_on = bool(ch.footage or config.get("footage_enabled"))
    min_q = int(config.get("image_min_quality"))

    def _clip_slot() -> bool:
        with clip_lock:
            if stats["clips"] >= max_clips:
                return False
            stats["clips"] += 1
            return True

    def _scene_key(s: dict[str, Any]) -> str:
        import hashlib
        return hashlib.sha1(json.dumps([s.get("text"), s.get("visual")], sort_keys=True, default=str).encode()).hexdigest()[:12]

    def _usable(r: dict[str, Any] | None) -> bool:
        if not r:
            return False
        if r.get("kind") == "graphic":
            return True
        return bool((r.get("clip") and Path(r["clip"]).exists()) or (r.get("path") and Path(r["path"]).exists()))

    def pick(i_s):
        ctx.check()  # cancelada: cenas que ainda estavam na fila nem começam
        i, s = i_s
        prev = (ck.get("picks") or {}).get(str(i))
        if prev and prev.get("key") == _scene_key(s) and _usable(prev.get("pick")):
            done[0] += 1
            if prev["pick"].get("url"):
                used_urls.add(prev["pick"]["url"])
            return prev["pick"]
        r = _pick_fresh(i, s)
        with ck_lock:
            ck.setdefault("picks", {})[str(i)] = {"key": _scene_key(s), "pick": r}
        save_ck()
        return r

    def _try_clip(i: int, s: dict[str, Any]) -> dict[str, Any] | None:
        if not (footage_on and _clip_slot()):
            return None
        from . import footage
        ws = scene_words[i] if i < len(scene_words) else []
        need = (ws[-1].end - ws[0].start + 0.4) if ws else 4.0
        try:
            rv = footage.pick_scene_clip(s, context, need, (W, H), used_urls, log_fn=lambda m: ctx.log(f"Cena {i + 1}: {m}"))
        except Exception as e:  # noqa: BLE001
            rv = None
            ctx.log(f"Cena {i + 1}: filmagem falhou ({e}) — usando foto")
        if not rv:
            with clip_lock:
                stats["clips"] -= 1  # não achou: libera a vaga para outra cena
        return rv

    def _fallback_graphic(i: int, s: dict[str, Any]) -> dict[str, Any] | None:
        with clip_lock:
            if stats["fallback_graphics"] >= max_fallback:
                return None
            stats["fallback_graphics"] += 1
        try:
            v = content.scene_graphic(ch, sc.title, s, facts_hint)
        except Exception as e:  # noqa: BLE001
            v = None
            ctx.log(f"Cena {i + 1}: gráfico de reserva falhou ({e})")
        if v:
            ctx.log(f"Cena {i + 1}: sem foto boa — virou gráfico animado ({v['kind']})")
            return {"kind": "graphic", "graphic": v["kind"], "visual": v, "fallback": True}
        with clip_lock:
            stats["fallback_graphics"] -= 1
        return None

    def _pick_fresh(i, s):
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
        if wants_video and kind == "real":
            rv = _try_clip(i, s)
            if rv:
                done[0] += 1
                ctx.update(0.15 + 0.4 * done[0] / len(scenes), f"Imagens: {done[0]}/{len(scenes)}")
                return rv
        r = visuals.pick_scene_image(s, context, ch.image_style, ai_size, ch.visual_mode,
                                     log_fn=lambda m: ctx.log(f"Cena {i + 1}: {m}"), used=used_urls,
                                     credit_ok=ch.image_credit_ok)
        if kind == "real" and (not r or r.get("score", 0) < min_q):
            # foto fraca: tenta filmagem real; senão a cena vira gráfico animado (nunca imagem errada)
            rv = None if wants_video else _try_clip(i, s)
            alt = rv or _fallback_graphic(i, s)
            if alt:
                r = alt
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

    ex = ThreadPoolExecutor(3)
    try:
        picks = list(ex.map(pick, enumerate(scenes)))
    finally:  # erro/cancelamento: não espera as outras cenas terminarem
        ex.shutdown(wait=False, cancel_futures=True)
    for i, p in enumerate(picks):
        if p and p.get("fallback") and p.get("visual"):
            scenes[i] = {**scenes[i], "visual": p["visual"]}
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
        st.end = float(scene_ts[i + 1].start if i + 1 < n else narration_end)
    # a tela final pode completar no máximo 3s (nunca fica repetindo o encerramento)
    duration = narration_end + OUTRO_SECONDS + min(3.0, max(0.0, min_total - narration_end - OUTRO_SECONDS))
    if loop:  # sem tela final: só o respiro da fusão com o começo
        duration = narration_end + LOOP_TAIL
    if sc.format == "long" and not vertical:  # tela final de 20 s ("assista o próximo" + inscrição) p/ os elementos do YouTube
        from .render.endcard import END_SCREEN_SECONDS
        duration = narration_end + 0.15 + END_SCREEN_SECONDS
    if vertical and duration < min_total - 6:
        ctx.log(f"⚠ Vídeo com {duration:.0f}s (planejado ≈{min_total + 4:.0f}s) — roteiro ficou curto mesmo após expansão")
    if vertical and duration > 180:
        ctx.log(f"⚠ Vídeo com {duration:.0f}s — passa de 3 min e não conta como Short")

    # 5) direção de animação + envelope da voz (boca do mascote) ----------------------------
    env = _envelope(voice["path"], duration)
    op0 = (scenes[0].get("opening") or {}) if scenes and isinstance(scenes[0].get("opening"), dict) else {}
    opening = str(plan.get("opening_type") or op0.get("type") or "")
    # texto da abertura pedido pelo roteiro (1º ~2 s) tem prioridade sobre o texto da miniatura
    hook = str(op0.get("onscreen") or "").strip() or (sc.thumbnail_text or "").strip()
    tl = Timeline(W, H, FPS, duration, narration_end, sc.title, scene_ts, steps, words, env,
                  {**(ch.theme or {}), "_look": plan.get("look") or {}, "_series": plan.get("series") or "",
                   "_opening": opening}, sc.format,
                  hook=hook[:80], loop=LOOP_XFADE if loop else 0.0)
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
    starts = [st.start for st in scene_ts]
    fx_plan = {"dose": "off", "events": []}
    if sfx.enabled(ch):
        fx_plan = sfx.plan(sum(ord(c) for c in sc.title) + video_id, starts[1:],
                           impacts + sfx.reveal_times(scenes, starts), sfx.payoff_time(scenes, starts), duration,
                           vertical=vertical, opening=opening)
        ctx.log(f"Efeitos sonoros: dose {fx_plan['dose']} ({len(fx_plan['events'])} efeitos)")
    audio_info = _mix_audio(voice["path"], track["path"] if track else None, duration, ch.music_volume, final_audio,
                            fx_plan["events"], loop_tail=LOOP_XFADE if loop else 0.0)
    if audio_info.get("measured_lufs") is not None:
        ctx.log(f"Mix normalizado: {audio_info['target_lufs']:.0f} LUFS (antes {audio_info['measured_lufs']:.1f}), "
                f"pico real ≤ {audio_info['true_peak']:.1f} dBTP")

    # 7) render -------------------------------------------------------------------------
    out = workdir / f"{ch.slug}_{video_id}.mp4"
    ctx.update(0.62, "Renderizando vídeo")
    # a busca da imagem da miniatura (rede + IA de visão) corre enquanto o vídeo renderiza
    thumb_ex = ThreadPoolExecutor(1)
    thumb_bg = thumb_ex.submit(thumbnail_background, sc, scenes, context, ch, used_urls, ctx)
    try:
        render(tl, template, out, final_audio, progress=lambda p: ctx.update(0.62 + 0.35 * p, f"Renderizando vídeo {int(p * 100)}%"))
    finally:
        thumb_ex.shutdown(wait=False, cancel_futures=True)

    # 8) thumbnail -----------------------------------------------------------------------
    from .render.thumbnail import make_thumbnail
    # miniatura: a imagem da abertura representa o título; senão, a de maior nota
    best = 0 if (picks and picks[0] and picks[0].get("path") and picks[0].get("score", 0) >= 60) else         max((k for k, p in enumerate(picks) if p and p.get("path")), key=lambda k: picks[k].get("score", 0), default=None)
    bg_img = thumb_bg.result() or         (images[best] if best is not None else next((im for im in images if im is not None), None))
    thumb_text = (sc.thumbnail_text or sc.title.replace("#Shorts", "")).strip()
    thumb = make_thumbnail(bg_img, thumb_text, ch.theme or {}, workdir / "thumb.jpg", vertical,
                           variant=int(plan.get("thumb_variant", video_id)))
    ctx.log(f"Miniatura criada: “{thumb_text}”")
    if not vertical and ch.thumbs_blocked:
        try:
            _cover_intro(out, thumb, W, H)
            ctx.log("Canal sem miniatura personalizada: capa aplicada no 1º segundo do vídeo")
        except Exception as e:  # noqa: BLE001
            ctx.log(f"Capa no 1º quadro não aplicada: {e}")

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
                     "last_word_end": words[-1].end if words else 0.0,
                     "highlights": {k: sum(1 for w in words if w.kind == k) for k in ("emph", "date", "num", "name")},
                     "highlight_mode": getattr(template, "hl_mode", "")},
        "audio": {**audio_info, "sfx_dose": fx_plan["dose"], "sfx": len(fx_plan["events"])},
        "loop": loop, "opening_type": opening,
        "tv": tv_metrics(template),
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


def _cover_intro(video: Path, thumb: Path, w: int, h: int, secs: float = 1.0) -> None:
    """Mostra a miniatura no começo do vídeo (some com um fade) — o YouTube costuma oferecer quadros do vídeo
    como capa quando o canal não pode enviar miniatura. A narração continua por baixo, sem atraso."""
    from .media import video_encoder_args
    tmp = video.with_name(video.stem + "_capa.mp4")
    run_ffmpeg(["-i", str(video), "-loop", "1", "-t", f"{secs + 0.5:.2f}", "-i", str(thumb), "-filter_complex",
                f"[1:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},format=rgba,"
                f"fade=t=out:st={secs:.2f}:d=0.45:alpha=1[c];[0:v][c]overlay=0:0:eof_action=pass[v]",
                "-map", "[v]", "-map", "0:a", *video_encoder_args(), "-c:a", "copy", "-movflags", "+faststart", str(tmp)])
    tmp.replace(video)


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


TRUE_PEAK = -1.5  # alvo do loudnorm; a margem de 0,5 dB absorve o AAC → arquivo final ≤ -1 dBTP


def _mix_audio(voice: str, track: str | None, duration: float, music_vol: float, out: Path,
               events: list[dict[str, Any]] | None = None, loop_tail: float = 0.0) -> dict[str, Any]:
    """Voz + trilha com ducking (sidechain pela voz) + efeitos (sfx.plan) → loudnorm em 2 passadas.

    Loop: a trilha não tem fade; começa adiantada `loop_tail` s e, no fim, funde no próprio começo — quando o
    vídeo recomeça, o som continua exatamente de onde estava. O ducking fica "segurado" na emenda."""
    inputs = ["-i", voice]
    filters = ["[0:a]aresample=48000,loudnorm=I=-16:TP=-1.5:LRA=11,apad[v0]"]
    mix = ["[v0]"]
    idx = 1
    D = float(duration)
    if track:
        vol = f"volume={music_vol * 2.2:.3f}"
        inputs += ["-stream_loop", "-1", "-i", track]
        if loop_tail:
            o = float(loop_tail)
            inputs += ["-i", track]
            filters.append(f"[{idx}:a]aresample=48000,atrim=start={o:.3f},asetpts=PTS-STARTPTS,{vol},atrim=0:{D:.3f},"
                           f"afade=t=out:st={D - o:.3f}:d={o:.3f}[mbody]")
            filters.append(f"[{idx + 1}:a]aresample=48000,atrim=0:{o:.3f},asetpts=PTS-STARTPTS,{vol},"
                           f"afade=t=in:d={o:.3f},adelay={int((D - o) * 1000)}:all=1[mhead]")
            filters.append("[mbody][mhead]amix=inputs=2:normalize=0:duration=longest[mus]")
            # chave do ducking: voz + um tom inaudível (só na chave) na emenda → a música não "sobe" antes de recomeçar
            filters.append(f"aevalsrc=0.12*sin(2*PI*220*t):s=48000:d={o + 0.2:.3f},adelay={int((D - o) * 1000)}:all=1[hold]")
            filters.append("[v0]asplit=2[voice][vk0]")
            filters.append("[vk0][hold]amix=inputs=2:normalize=0:duration=first[vkey]")
            idx += 2
        else:
            filters.append(f"[{idx}:a]aresample=48000,{vol},afade=t=in:d=0.8,"
                           f"afade=t=out:st={max(0, D - 1.8):.2f}:d=1.8,atrim=0:{D:.2f}[mus]")
            filters.append("[v0]asplit=2[voice][vkey]")
            idx += 1
        filters.append("[mus][vkey]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=300[ducked]")
        mix = ["[voice]", "[ducked]"]
    # efeitos: um arquivo por (tipo, variante), repartido com asplit
    events = [e for e in (events or []) if 0 <= e["t"] < D]
    groups: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for e in events:
        groups.setdefault((e["kind"], int(e.get("variant", 0))), []).append(e)
    for g, ((kind, var), evs) in enumerate(groups.items()):
        inputs += ["-i", str(sfx.sound(kind, var))]
        labels = [f"s{g}_{j}" for j in range(len(evs))]
        filters.append(f"[{idx}:a]aresample=48000,asplit={len(evs)}" + "".join(f"[{x}]" for x in labels)
                       if len(evs) > 1 else f"[{idx}:a]aresample=48000[{labels[0]}]")
        for x, e in zip(labels, evs):
            filters.append(f"[{x}]adelay={int(e['t'] * 1000)}:all=1,volume={float(e.get('gain', 0.3)):.3f}[{x}d]")
            mix.append(f"[{x}d]")
        idx += 1
    filters.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=longest,atrim=0:{D:.3f}[out]")
    premix = out.with_name(out.stem + "_premix.wav")
    run_ffmpeg([*inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-ac", "2",
                "-c:a", "pcm_f32le", str(premix)])
    try:
        return loudnorm_2pass(premix, out, float(config.get("loudness_target") or -14.0))
    finally:
        premix.unlink(missing_ok=True)


def loudnorm_2pass(src: Path, out: Path, target: float = -14.0, tp: float = TRUE_PEAK) -> dict[str, Any]:
    """Normalização EBU R128 em duas passadas: mede o mix inteiro e aplica um ganho único (linear) até o alvo;
    se o ganho estouraria o pico real, o loudnorm limita sozinho (modo dinâmico)."""
    import re
    import subprocess
    from .media import ffmpeg_exe
    base = f"loudnorm=I={target:.1f}:TP={tp:.1f}:LRA=18"
    r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(src), "-af", base + ":print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=900)
    m = None
    blocks = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr)
    if blocks:
        try:
            m = json.loads(blocks[-1])
        except ValueError:
            m = None
    if m and all(m.get(k) not in (None, "-inf", "inf") for k in ("input_i", "input_tp", "input_lra", "input_thresh")):
        af = (f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
              f"measured_thresh={m['input_thresh']}:offset={m.get('target_offset', '0')}:linear=true")
        mode = "2pass"
    else:  # medição falhou (áudio mudo?): 1 passada dinâmica
        af, mode = base, "1pass"
    run_ffmpeg(["-i", str(src), "-af", af + ",aresample=48000", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(out)])
    return {"target_lufs": target, "true_peak": tp, "mode": mode,
            "measured_lufs": float(m["input_i"]) if m and mode == "2pass" else None,
            "measured_tp": float(m["input_tp"]) if m and mode == "2pass" else None}


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
