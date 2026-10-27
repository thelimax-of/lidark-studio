"""Aprendizado pela retenção: curva segundo a segundo do YouTube Analytics cruzada com as cenas de cada vídeo.

- Coleta a curva (100 pontos) de cada vídeo publicado.
- Calcula: quanto segura nos 3 primeiros segundos (gancho), no meio e no fim; quais cenas mais perdem público.
- A IA transforma isso em lições ("ganchos assim seguram, cenas assim perdem") que alimentam o roteirista.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlmodel import select

from .db import session
from .models import Account, Insight, MetricSnapshot, Publication, Script, Video

log = logging.getLogger("lidark.retention")


def fetch_curve(ya, video_id: str) -> list[list[float]]:
    r = ya.reports().query(ids="channel==MINE", startDate="2015-01-01",
                           endDate=__import__("datetime").date.today().isoformat(),
                           metrics="audienceWatchRatio,relativeRetentionPerformance",
                           dimensions="elapsedVideoTimeRatio", filters=f"video=={video_id}").execute()
    return [[float(a), float(b), float(c)] for a, b, c in (r.get("rows") or [])]


def collect_curves(acc: Account, pubs: list[Publication]) -> dict[str, list[list[float]]]:
    """Curvas de retenção dos vídeos (só os que já têm público suficiente)."""
    from .publish import _yt_client, _yt_creds
    if not acc.credentials:
        return {}
    ya = _yt_client(_yt_creds(acc), "youtubeAnalytics", "v2")
    out = {}
    for p in pubs:
        if not p.external_id:
            continue
        try:
            curve = fetch_curve(ya, p.external_id)
            if len(curve) >= 20:
                out[p.external_id] = curve
        except Exception as e:  # noqa: BLE001
            log.info("curva %s: %s", p.external_id, e)
    return out


def value_at(curve: list[list[float]], ratio: float) -> float:
    if not curve:
        return 0.0
    best = min(curve, key=lambda r: abs(r[0] - ratio))
    return best[1]


def summarize(curve: list[list[float]], duration: float, scenes: list[dict[str, Any]] | None) -> dict[str, Any]:
    """Resumo da curva: gancho (3s), meio, fim e queda por cena."""
    if not curve or not duration:
        return {}
    start = max(value_at(curve, 0.01), 0.01)
    hook = value_at(curve, min(0.5, 3.0 / duration)) / start
    mid = value_at(curve, 0.5) / start
    end = value_at(curve, 0.95) / start
    per_scene = []
    for i, sc in enumerate(scenes or []):
        a, b = sc["start"] / duration, sc["end"] / duration
        if b - a < 0.01:
            continue
        va, vb = value_at(curve, a), value_at(curve, b)
        secs = max(0.5, sc["end"] - sc["start"])
        per_scene.append({"scene": i + 1, "text": sc.get("text", "")[:120], "visual": sc.get("visual", ""),
                          "drop_per_10s": round((va - vb) / start / secs * 10 * 100, 1)})
    worst = sorted(per_scene, key=lambda x: -x["drop_per_10s"])[:2]
    best = sorted(per_scene, key=lambda x: x["drop_per_10s"])[:1]
    return {"hook": round(hook * 100, 1), "mid": round(mid * 100, 1), "end": round(end * 100, 1),
            "worst_scenes": worst, "best_scenes": best, "scenes": per_scene}


def channel_retention(channel_id: int) -> list[dict[str, Any]]:
    """Uma linha por vídeo publicado com curva disponível."""
    rows = []
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.channel_id == channel_id,
                                                Publication.status == "published")).all()
        for p in pubs:
            snap = s.exec(select(MetricSnapshot).where(MetricSnapshot.publication_id == p.id)
                          .order_by(MetricSnapshot.captured_at.desc())).first()
            curve = None
            for m in s.exec(select(MetricSnapshot).where(MetricSnapshot.publication_id == p.id)
                            .order_by(MetricSnapshot.captured_at.desc()).limit(10)).all():
                if (m.raw or {}).get("retention_curve"):
                    curve = m.raw["retention_curve"]
                    break
            if not curve:
                continue
            v = s.get(Video, p.video_id) if p.video_id else None
            sc = s.get(Script, v.script_id) if v else None
            duration = (v.duration if v else 0) or p.duration or 0
            scenes = (v.assets or {}).get("scenes") if v else None
            if not scenes and sc and v:
                from .inspector import _estimate_scenes
                scenes = _estimate_scenes(sc, (v.assets or {}).get("narration_end") or duration)
            hook_text = (sc.scenes[0].get("text") if sc and sc.scenes else "") or ""
            rows.append({"publication_id": p.id, "title": p.title, "url": p.url, "duration": duration,
                         "views": snap.views if snap else 0, "hook_text": hook_text, "curve": curve,
                         "scenes": [{"start": x["start"], "end": x["end"], "text": x.get("text", "")[:80]} for x in (scenes or [])],
                         **summarize(curve, duration, scenes)})
    return rows


def generate_retention_insights(channel_id: int) -> list[str]:
    """IA compara ganchos e cenas que seguram × que perdem público e grava lições para o roteirista."""
    from . import llm
    rows = [r for r in channel_retention(channel_id) if r.get("hook")]
    if len(rows) < 2:
        return []
    lines = []
    for r in sorted(rows, key=lambda r: -r["end"]):
        worst = "; ".join(f"cena {w['scene']} ({w['visual'] or 'imagem'}) “{w['text']}” perde {w['drop_per_10s']}%/10s"
                          for w in r.get("worst_scenes", []))
        lines.append(f"- “{r['title']}” ({r['duration']:.0f}s, {r['views']} views) | gancho: “{r['hook_text'][:110]}” | "
                     f"retém {r['hook']}% aos 3s, {r['mid']}% no meio, {r['end']}% no fim | maiores quedas: {worst or '—'}")
    data = llm.complete_json(f"""Você analisa a RETENÇÃO de vídeos curtos de um canal do YouTube (quanto do público continua assistindo).
Dados por vídeo (do melhor para o pior final):
{chr(10).join(lines)}

Extraia de 4 a 7 lições PRÁTICAS para o roteirista, comparando os que seguram com os que perdem público:
que tipo de gancho segura nos 3 primeiros segundos, que tipo de cena/frase faz o público sair, ritmo, duração ideal,
tipo de visual (imagem, mapa, linha do tempo etc.) que segura melhor. Cite exemplos reais dos dados.
REGRA FIXA: a duração NÃO é negociável (Shorts precisam ter 60s ou mais para monetizar). NUNCA recomende vídeos mais
curtos; vídeos antigos com menos de 60s servem só para aprender sobre gancho, ritmo e conteúdo — o foco é como
manter o público até o fim de um vídeo de 60-70s (um fato novo a cada poucos segundos, viradas no meio etc.).
Responda JSON: {{"lessons": ["..."]}}""", temperature=0.3)
    lessons = [x for x in (data.get("lessons", []) if isinstance(data, dict) else []) if isinstance(x, str)][:7]
    if lessons:
        with session() as s:
            for old in s.exec(select(Insight).where(Insight.channel_id == channel_id, Insight.kind == "retention")).all():
                s.delete(old)
            for t in lessons:
                s.add(Insight(channel_id=channel_id, kind="retention", text=t,
                              data={"videos": len(rows), "avg_hook": round(sum(r["hook"] for r in rows) / len(rows), 1)}))
            s.commit()
    return lessons
