"""Inspetor de qualidade: revisa o vídeo PRONTO antes de ir ao ar.

Checagens: duração mínima, encerramento sem "enrolação", final do roteiro (CTA, sem reticências),
volume (LUFS) e silêncios, sincronia das legendas e uma revisão visual por IA (um quadro por cena).
Reprovado → o vídeo fica "Revisar" e não é publicado automaticamente.
"""
from __future__ import annotations

import io
import logging
import re
import subprocess
from pathlib import Path
from typing import Any


from . import llm
from .config import MEDIA_DIR
from .content import CTA_WORDS, OUTRO_SECONDS
from .db import session
from .jobs import JobContext, handler
from .media import ffmpeg_exe
from .models import Channel, Script, Video, now

log = logging.getLogger("lidark.inspector")


def _check(name: str, level: str, detail: str) -> dict[str, str]:
    return {"name": name, "level": level, "detail": detail}


def audio_stats(path: Path, narration_end: float) -> dict[str, Any]:
    """Volume integrado (LUFS), pico e silêncios longos durante a narração."""
    r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(path), "-t", f"{narration_end:.2f}",
                        "-af", "ebur128=peak=true,silencedetect=noise=-42dB:d=1.6", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore", timeout=600)
    err = r.stderr
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
    silences = [float(x) for x in re.findall(r"silence_duration: ([\d.]+)", err)]
    return {"lufs": float(lufs[-1]) if lufs else None, "peak": float(peak[-1]) if peak else None, "silences": silences}


def sample_frames(path: Path, times: list[float], size: tuple[int, int] = (360, 640)) -> list[bytes]:
    import av
    out: list[bytes] = []
    with av.open(str(path)) as c:
        s = c.streams.video[0]
        for t in times:
            c.seek(int(t / s.time_base), stream=s, any_frame=False, backward=True)
            for f in c.decode(s):
                if float(f.pts * s.time_base) >= t - 0.05:
                    im = f.to_image()
                    im.thumbnail(size)
                    b = io.BytesIO()
                    im.save(b, "JPEG", quality=80)
                    out.append(b.getvalue())
                    break
    return out


def visual_review(path: Path, scenes: list[dict[str, Any]], vertical: bool) -> list[dict[str, Any]]:
    """IA de visão olha um quadro do meio de cada cena procurando defeitos."""
    if not llm.has_vision() or not scenes:
        return []
    times = [min(s["end"] - 0.2, s["start"] + max(0.6, (s["end"] - s["start"]) * 0.55)) for s in scenes]
    frames = sample_frames(path, times, (360, 640) if vertical else (640, 360))
    results: list[dict[str, Any]] = []
    for i in range(0, len(frames), 6):
        batch = frames[i:i + 6]
        texts = "\n".join(f"Quadro {i + k + 1}: narração diz \"{scenes[i + k]['text'][:140]}\"" for k in range(len(batch)))
        prompt = f"""Você é o controle de qualidade de um canal do YouTube. Estes são {len(batch)} quadros de um vídeo
{'vertical (Short)' if vertical else 'horizontal'}, na ordem. O texto do topo, a legenda no meio/baixo e o mascote
desenhado são elementos normais do layout.
{texts}

Para cada quadro, aponte APENAS problemas reais:
- texto cortado na borda, sobreposto ou ilegível; elementos se sobrepondo à legenda
- imagem distorcida, esticada, muito pixelada, com marca d'água, ou tela vazia/erro de renderização
- imagem que claramente NÃO tem relação com a narração
- conteúdo impróprio para anunciantes: violência explícita, cadáveres, nudez, símbolos nazistas/extremistas
severity: 0 = ok, 1 = detalhe, 2 = problema visível, 3 = grave (impróprio ou quebrado)
Responda JSON: {{"frames": [{{"severity": 0, "problem": ""}}]}}"""
        try:
            data = llm.vision_json(prompt, batch)
            items = data.get("frames", []) if isinstance(data, dict) else data
        except Exception as e:  # noqa: BLE001
            log.warning("revisão visual: %s", e)
            items = []
        for k in range(len(batch)):
            it = items[k] if k < len(items) and isinstance(items[k], dict) else {}
            results.append({"scene": i + k + 1, "severity": int(it.get("severity", 0) or 0),
                            "problem": str(it.get("problem", ""))[:200]})
    return results


def _estimate_scenes(sc: Script, narr: float) -> list[dict[str, Any]]:
    """Vídeos antigos (sem tempos gravados): estima as cenas pela proporção de palavras."""
    texts = [x.get("text", "") for x in (sc.scenes or []) if x.get("text")]
    total = sum(len(t.split()) for t in texts) or 1
    out, t0 = [], 0.0
    for t in texts:
        d = narr * len(t.split()) / total
        out.append({"start": t0, "end": t0 + d, "text": t})
        t0 += d
    return out


def inspect(ch: Channel, sc: Script, video: Video) -> dict[str, Any]:
    a = video.assets or {}
    path = MEDIA_DIR / video.path
    vertical = video.format == "short"
    checks: list[dict[str, str]] = []
    dur = float(video.duration or a.get("duration") or 0)
    narr = float(a.get("narration_end") or 0)

    # 1) duração
    need = 60.0 if vertical else (ch.long_minutes or 6) * 60 * 0.85
    checks.append(_check("Duração", "ok" if dur >= need else "fail",
                         f"{dur:.0f}s (mínimo {need:.0f}s)"))
    # 2) encerramento
    tail = dur - narr if narr else 0
    # vídeo longo: tela final de 20 s para os elementos finais do YouTube (render/endcard.py) é esperada
    max_tail = OUTRO_SECONDS + 3.3 if vertical else 20.0 + 1.0
    checks.append(_check("Encerramento", "ok" if tail <= max_tail else "fail",
                         f"tela final com {tail:.1f}s"))
    # 3) final do roteiro
    last = ((sc.scenes or [{}])[-1].get("text") or "").strip()
    has_cta = any(w in last.lower() for w in CTA_WORDS) or (ch.cta and ch.cta.lower()[:15] in last.lower())
    dangling = last.endswith(("...", "…"))
    checks.append(_check("Final do roteiro", "fail" if dangling else ("ok" if has_cta else "warn"),
                         "termina com reticências" if dangling else ("termina no CTA" if has_cta else "sem chamada final")))
    # 4) áudio
    if path.exists() and narr:
        st = audio_stats(path, narr)
        lufs = st["lufs"]
        if lufs is None:
            checks.append(_check("Volume", "warn", "não foi possível medir"))
        else:
            lvl = "ok" if -19 <= lufs <= -10 else ("warn" if -23 <= lufs <= -8 else "fail")
            checks.append(_check("Volume", lvl, f"{lufs:.1f} LUFS (ideal entre -19 e -10)"))
        if st["peak"] is not None and st["peak"] > -0.5:
            checks.append(_check("Pico de áudio", "warn", f"{st['peak']:.1f} dBFS (risco de estourar)"))
        long_sil = [x for x in st["silences"] if x >= 1.6]
        checks.append(_check("Silêncios", "ok" if not long_sil else ("warn" if len(long_sil) == 1 else "fail"),
                             "nenhum silêncio longo" if not long_sil else f"{len(long_sil)} silêncio(s) de até {max(long_sil):.1f}s"))
    else:
        checks.append(_check("Arquivo", "fail", "vídeo não encontrado"))
    # 5) legendas
    cap = a.get("captions") or {}
    if cap:
        diff = abs((cap.get("last_word_end") or 0) - narr)
        same = cap.get("script_words") == cap.get("timed_words")
        lvl = "ok" if same and diff <= 1.5 else ("warn" if diff <= 3 else "fail")
        checks.append(_check("Sincronia das legendas", lvl,
                             f"{cap.get('timed_words')}/{cap.get('script_words')} palavras, fim a {diff:.1f}s da voz"))
    # 6) revisão visual
    scenes_t = a.get("scenes") or _estimate_scenes(sc, narr)
    vis = visual_review(path, scenes_t, vertical) if path.exists() else []
    if vis:
        bad = [v for v in vis if v["severity"] >= 3]
        mid = [v for v in vis if v["severity"] == 2]
        lvl = "fail" if bad else ("warn" if mid else "ok")
        det = "; ".join(f"cena {v['scene']}: {v['problem']}" for v in (bad + mid)[:4]) or f"{len(vis)} cenas revisadas, sem problemas"
        checks.append(_check("Revisão visual (IA)", lvl, det))
    else:
        checks.append(_check("Revisão visual (IA)", "warn", "não executada (sem IA de visão)"))

    fails = [c for c in checks if c["level"] == "fail"]
    warns = [c for c in checks if c["level"] == "warn"]
    score = max(0, 100 - 30 * len(fails) - 8 * len(warns))
    return {"passed": not fails, "score": score, "checks": checks, "visual": vis,
            "checked_at": now().isoformat()}


def run_inspection(video_id: int, ctx: JobContext | None = None) -> dict[str, Any]:
    with session() as s:
        v = s.get(Video, video_id)
        sc = s.get(Script, v.script_id)
        ch = s.get(Channel, v.channel_id)
    if ctx:
        ctx.update(None, "Inspetor de qualidade revisando o vídeo")
    qa = inspect(ch, sc, v)
    with session() as s:
        v = s.get(Video, video_id)
        v.assets = {**(v.assets or {}), "qa": qa}
        if v.status in ("ready", "review"):
            v.status = "ready" if qa["passed"] else "review"
        s.add(v)
        s.commit()
    if ctx:
        lines = [f"{'✓' if c['level'] == 'ok' else '⚠' if c['level'] == 'warn' else '✗'} {c['name']}: {c['detail']}" for c in qa["checks"]]
        ctx.log("Inspeção: " + ("APROVADO" if qa["passed"] else "REPROVADO") + f" (nota {qa['score']})\n" + "\n".join(lines))
    return qa


@handler("inspect_video")
def job_inspect(ctx: JobContext) -> dict:
    qa = run_inspection(ctx.ref_id, ctx)
    return {"passed": qa["passed"], "score": qa["score"]}

