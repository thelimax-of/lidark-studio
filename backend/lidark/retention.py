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


def fetch_curve(ya, video_id: str, start: str = "2015-01-01") -> list[list[float]]:
    # start = data de publicação: com "2015-01-01" a API leva ~30s por vídeo; desde a publicação, ~1s (mesma curva)
    r = ya.reports().query(ids="channel==MINE", startDate=start,
                           endDate=__import__("datetime").date.today().isoformat(),
                           metrics="audienceWatchRatio,relativeRetentionPerformance",
                           dimensions="elapsedVideoTimeRatio", filters=f"video=={video_id}").execute()
    return [[float(a), float(b), float(c)] for a, b, c in (r.get("rows") or [])]


def collect_curves(acc: Account, pubs: list[Publication]) -> dict[str, list[list[float]]]:
    """Curvas de retenção dos vídeos (só os que já têm público suficiente)."""
    from .publish import _yt_client, _yt_creds
    if not acc.credentials:
        return {}
    from concurrent.futures import ThreadPoolExecutor
    creds = _yt_creds(acc)

    def one(p: Publication) -> tuple[str, list[list[float]]]:
        start = ((p.published_at or p.created_at) - __import__("datetime").timedelta(days=1)).date().isoformat()             if (p.published_at or p.created_at) else "2015-01-01"
        try:  # um cliente por thread (o httplib2 do cliente do Google não é seguro entre threads)
            return p.external_id, fetch_curve(_yt_client(creds, "youtubeAnalytics", "v2"), p.external_id, start)
        except Exception as e:  # noqa: BLE001
            log.info("curva %s: %s", p.external_id, e)
            return p.external_id, []

    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(one, [p for p in pubs if p.external_id]))
    return {vid: curve for vid, curve in res if len(curve) >= 20}


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
                          "start": sc["start"], "end": sc["end"], "words": len((sc.get("text") or "").split()),
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
            if scenes and sc:  # tipo de visual vindo do roteiro quando o render não gravou
                kinds = {x.get("text", ""): (x.get("visual") or {}).get("kind", "") for x in (sc.scenes or [])
                         if isinstance(x.get("visual"), dict)}
                scenes = [x if x.get("visual") else {**x, "visual": kinds.get(x.get("text", ""), "")} for x in scenes]
            hook_text = (sc.scenes[0].get("text") if sc and sc.scenes else "") or ""
            rows.append({"publication_id": p.id, "title": p.title, "url": p.url, "duration": duration,
                         "views": snap.views if snap else 0, "hook_text": hook_text, "curve": curve,
                         "variety": {k: (sc.variety or {}).get(k) for k in ("structure", "hook_style")} if sc else {},
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
Shorts NÃO têm duração mínima para monetizar: a receita vem das views engajadas (quem não pula). A duração é testada
automaticamente em faixas (≈30-65s), então foque em como segurar o público até o fim (um fato novo a cada poucos
segundos, viradas no meio, cortar enrolação etc.); se os dados mostrarem que os mais curtos retêm melhor, diga isso.
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


# ================================================================ REGRAS AUTOMÁTICAS
# Diferente das lições (texto livre da IA), aqui o código mede quais características de cena perdem mais público
# e transforma só os achados com amostra suficiente em restrições objetivas para o roteirista.

RULE_MIN_VIDEOS = 4   # vídeos com curva + cenas antes de confiar em qualquer regra
RULE_MIN_SCENES = 6   # cenas (de pelo menos 3 vídeos) em cada lado da comparação
RULE_MAX = 4

VISUAL_LABELS = {"real": "foto/vídeo real", "ai": "imagem de IA", "image": "imagem", "timeline": "linha do tempo",
                 "counter": "contador", "map": "mapa", "dossier": "dossiê", "versus": "mito × verdade",
                 "quote": "citação", "list": "lista"}


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _ratio(a: float, b: float) -> float:
    return a / b if b > 0.5 else 0.0  # quedas quase nulas (ou negativas, re-assistidas) não dão razão confiável


def _compare(group: list[dict], rest: list[dict]) -> dict[str, Any] | None:
    """Média de queda do grupo × resto, só se os dois lados têm amostra (cenas e vídeos) suficiente."""
    if len(group) < RULE_MIN_SCENES or len(rest) < RULE_MIN_SCENES:
        return None
    if len({x["video"] for x in group}) < 3:
        return None
    a, b = _mean([x["drop"] for x in group]), _mean([x["drop"] for x in rest])
    # excesso relativo à média do próprio vídeo: neutraliza vídeos que perdem muito público em todas as cenas
    ea, eb = _mean([x["excess"] for x in group]), _mean([x["excess"] for x in rest])
    return {"a": round(a, 1), "b": round(b, 1), "diff": round(ea - eb, 1), "ratio": round(_ratio(a, b), 2),
            "n": len(group), "videos": len({x["video"] for x in group})}


def _scene_samples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        scs = [x for x in (r.get("scenes") or []) if "drop_per_10s" in x]
        if len(scs) < 4:
            continue
        n = len(scs)
        m = _mean([x["drop_per_10s"] for x in scs[1:]])  # média sem o gancho (o swipe inicial distorce)
        for k, x in enumerate(scs):
            pos = "hook" if k == 0 else "second" if k == 1 else "end" if k == n - 1 else "pre_cta" if k == n - 2 else "middle"
            vis = x.get("visual") or ""
            out.append({"video": r["publication_id"], "pos": pos, "visual": vis if isinstance(vis, str) else "",
                        "words": x.get("words") or len((x.get("text") or "").split()),
                        "drop": x["drop_per_10s"], "excess": x["drop_per_10s"] - m})
    return out


def retention_rules(channel_id: int, rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Regras determinísticas a partir das quedas por cena (visual, posição, tamanho) e do plano de variedade."""
    try:
        rows = rows if rows is not None else channel_retention(channel_id)
    except Exception as e:  # noqa: BLE001
        log.info("regras de retenção %s: %s", channel_id, e)
        rows = []
    samples = _scene_samples(rows)
    nvid = len({x["video"] for x in samples})
    base: dict[str, Any] = {"videos": nvid, "scenes": len(samples), "rules": [], "findings": []}
    if nvid < RULE_MIN_VIDEOS:
        base["status"] = (f"Amostra pequena: {nvid} vídeo(s) com curva e cenas registradas "
                          f"(mínimo {RULE_MIN_VIDEOS}). As regras aparecem quando houver dados suficientes.")
        return base
    cands: list[dict[str, Any]] = []
    body = [x for x in samples if x["pos"] not in ("hook", "end")]  # gancho e CTA têm dinâmica própria

    # 1) tipo de visual
    for kind in sorted({x["visual"] for x in body if x["visual"]}):
        c = _compare([x for x in body if x["visual"] == kind], [x for x in body if x["visual"] != kind])
        if not c:
            continue
        label = VISUAL_LABELS.get(kind, kind)
        if c["ratio"] >= 1.4 and c["diff"] >= 1.5:
            if kind == "real":
                act = "intercale com gráficos e nunca use duas seguidas"
            elif kind in ("ai", "image"):
                act = "prefira foto real ou gráfico e nunca use na cena 2"
            else:
                act = "no máximo 1 por vídeo e nunca na cena 2"
            cands.append({"cat": "visual", "score": c["ratio"] - 1, **c, "key": kind,
                          "text": f"Cenas de {label} perdem {c['ratio']:.1f}x mais público que as demais "
                                  f"({c['a']}% × {c['b']}% a cada 10s, {c['n']} cenas): {act}."})
        elif c["ratio"] and c["ratio"] <= 0.7 and c["diff"] <= -1.5:
            cands.append({"cat": "visual_best", "score": (1 - c["ratio"]) * 0.8, **c, "key": kind,
                          "text": f"Cenas de {label} seguram melhor (perdem {round((1 - c['ratio']) * 100)}% menos, "
                                  f"{c['n']} cenas): use nos momentos de virada, dentro da dose de gráficos do plano."})

    # 2) posição da cena (comparada com o miolo do vídeo)
    middle = [x for x in samples if x["pos"] == "middle"]
    acts = {"second": "A cena 2 é onde mais se perde público ({a}% × {b}% a cada 10s no meio): entregue o primeiro "
                      "fato surpreendente até ~6s e não gaste a cena 2 com contexto.",
            "pre_cta": "A penúltima cena perde {r:.1f}x mais que o meio ({a}% × {b}% a cada 10s): não resuma nem "
                       "desacelere antes do CTA, guarde ali a revelação mais forte.",
            "end": "A cena final perde {r:.1f}x mais que o meio ({a}% × {b}% a cada 10s): feche a última revelação e o "
                   "CTA numa frase curta, sem despedida."}
    for pos, tpl in acts.items():
        c = _compare([x for x in samples if x["pos"] == pos], middle)
        if c and c["ratio"] >= 1.3 and c["diff"] >= 1.5:
            cands.append({"cat": "position", "score": c["ratio"] - 1, **c, "key": pos,
                          "text": tpl.format(a=c["a"], b=c["b"], r=c["ratio"])})

    # 3) tamanho da cena em palavras (o corte que mais separa)
    best = None
    for t in (30, 25, 20, 15):
        c = _compare([x for x in body if x["words"] > t], [x for x in body if x["words"] <= t])
        if c and c["ratio"] >= 1.3 and c["diff"] >= 1.0 and (not best or c["ratio"] > best["ratio"]):
            best = {**c, "key": t}
    if best:
        cands.append({"cat": "length", "score": best["ratio"] - 1, **best,
                      "text": f"Cenas com mais de {best['key']} palavras perdem {best['ratio']:.1f}x mais público "
                              f"({best['n']} cenas): máximo {best['key']} palavras por cena — divida as longas em duas."})

    # 4) plano de variedade: só aponta o estilo fraco e como compensar (não proíbe — a variedade continua sorteando)
    from .variety import HOOKS, STRUCTURES
    for field, metric in (("hook_style", "hook"), ("structure", "end")):
        groups: dict[str, list[float]] = {}
        for r in rows:
            k = (r.get("variety") or {}).get(field)
            if k and r.get(metric) is not None:
                groups.setdefault(k, []).append(r[metric])
        ok = {k: v for k, v in groups.items() if len(v) >= 3}
        if len(ok) < 2:
            continue
        worst = min(ok, key=lambda k: _mean(ok[k]))
        a, b = _mean(ok[worst]), _mean([v for k, vs in ok.items() if k != worst for v in vs])
        if b - a < 8.0:  # pontos percentuais
            continue
        if field == "hook_style":
            text = (f"Ganchos no estilo '{worst}' ({HOOKS.get(worst, worst)}) seguram menos aos 3s ({a:.0f}% × {b:.0f}% "
                    f"dos outros, {len(ok[worst])} vídeos): quando o plano pedir esse estilo, ponha o fato concreto "
                    f"(número, nome ou data) nas 5 primeiras palavras.")
        else:
            text = (f"A estrutura '{STRUCTURES.get(worst, {}).get('name', worst)}' chega ao fim com menos público "
                    f"({a:.0f}% × {b:.0f}%, {len(ok[worst])} vídeos): nela, ponha uma virada clara no meio e um "
                    f"fato novo a cada ~8s.")
        cands.append({"cat": "plan", "score": (b - a) / max(b, 1), "a": round(a, 1), "b": round(b, 1),
                      "n": len(ok[worst]), "key": f"{field}:{worst}", "text": text})

    # no máximo uma regra por categoria, as mais fortes primeiro; "o que segura" só se sobrar espaço
    picked, seen = [], set()
    for c in sorted(cands, key=lambda c: (c["cat"] == "visual_best", -c["score"])):
        if c["cat"] in seen or len(picked) >= RULE_MAX:
            continue
        seen.add(c["cat"])
        picked.append(c)
    base["rules"] = [c["text"] for c in picked]
    base["findings"] = [{k: v for k, v in c.items() if k != "text"} for c in cands]
    base["status"] = "" if picked else "Nenhuma diferença forte o bastante entre tipos de cena ainda."
    return base


def retention_rules_prompt(channel_id: int) -> str:
    """Bloco pronto para o prompt do roteirista (vazio se não há regra confiável)."""
    rules = retention_rules(channel_id).get("rules") or []
    if not rules:
        return ""
    return ("REGRAS DE RETENÇÃO MEDIDAS NOS DADOS DO CANAL (calculadas das quedas reais por cena — obrigatórias, "
            "sem contrariar o plano de variedade):\n" + "\n".join(f"- {r}" for r in rules))
