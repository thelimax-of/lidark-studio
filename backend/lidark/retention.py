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


def curve_quality(curve: list[list[float]], duration: float) -> dict[str, Any]:
    """Números da curva para o aprendizado (learning.py): retenção aos 3s, no meio e no fim (relativa ao início)
    e o "desempenho relativo de retenção" do YouTube (0-1; 0,5 = típico de vídeos de duração parecida)."""
    if not curve or not duration:
        return {}
    s = summarize(curve, duration, None)
    rel = [r[2] for r in curve if len(r) > 2]
    out = {k: s[k] for k in ("hook", "mid", "end") if k in s}
    if rel:
        out["relative"] = round(sum(rel) / len(rel), 3)
        out["relative_hook"] = round(sum(rel[:5]) / len(rel[:5]), 3)
    return out


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

    # 5) quedas concentradas nos cortes de cena (curva × tempos de corte)
    try:
        cd = cut_drops(rows)
        cr = cut_rule(channel_id, rows)
        if cr:
            ratio = (cd.get("first_cut_drop") or cd.get("other_cut_drop") or 0) / max(cd.get("base_drop") or 0.05, 0.05)
            cands.append({"cat": "cut", "score": ratio - 1, "n": cd.get("videos", 0), "key": "first_cut"
                          if cd.get("first_cut_cluster") else "cuts", "text": cr})
    except Exception as e:  # noqa: BLE001
        log.info("quedas nos cortes %s: %s", channel_id, e)

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


# ================================================================ SINAIS POR VÍDEO (YouTube Analytics, em cache)
# De onde veio o público (feed do Shorts, busca, sugeridos, navegação...), inscritos × não inscritos e aparelho
# (celular × TV × computador). Poucas consultas: 3 por vídeo, só vídeos de 1-60 dias, no máximo 1x a cada ~20 h
# (1x por semana depois de 14 dias; congelado depois de 60). A cota do Analytics é separada da API de dados (10 mil).

SIGNALS_PATH = None  # definido na 1ª chamada (CACHE_DIR/learning_signals.json)
SIG_MAX_PER_CHANNEL = 25
TRAFFIC_LABELS = {"SHORTS": "Feed do Shorts", "YT_SEARCH": "Busca do YouTube", "RELATED_VIDEO": "Vídeos sugeridos",
                  "SUBSCRIBER": "Inscrições/feed de inscritos", "YT_CHANNEL": "Página do canal", "YT_OTHER_PAGE": "Outras páginas",
                  "NO_LINK_OTHER": "Direto/desconhecido", "EXT_URL": "Sites externos", "PLAYLIST": "Playlists",
                  "NOTIFICATION": "Notificações", "END_SCREEN": "Tela final", "HASHTAGS": "Hashtags",
                  "SOUND_PAGE": "Página do som", "ADVERTISING": "Anúncios", "YT_PLAYLIST_PAGE": "Página de playlist",
                  "ANNOTATION": "Cards", "CAMPAIGN_CARD": "Cards de campanha", "SHORTS_CONTENT_LINKS": "Links em Shorts",
                  "VIDEO_REMIXES": "Remixes", "LIVE_REDIRECT": "Redirecionamento de live"}
TRAFFIC_GROUP = {"SHORTS": "feed", "YT_SEARCH": "search", "RELATED_VIDEO": "suggested", "SUBSCRIBER": "browse",
                 "YT_CHANNEL": "browse", "NOTIFICATION": "browse", "YT_OTHER_PAGE": "browse", "PLAYLIST": "browse",
                 "YT_PLAYLIST_PAGE": "browse", "END_SCREEN": "suggested", "HASHTAGS": "search", "EXT_URL": "external",
                 "NO_LINK_OTHER": "external", "ADVERTISING": "ads"}
GROUP_LABELS = {"ads": "anúncios pagos", "feed": "feed do Shorts", "search": "busca", "suggested": "sugeridos", "browse": "inscritos/navegação",
                "external": "externo/direto", "other": "outras"}


def _sig_path():
    from .config import CACHE_DIR
    return CACHE_DIR / "learning_signals.json"


def load_signals() -> dict[str, Any]:
    import json
    try:
        return json.loads(_sig_path().read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _q(ya, vid: str, start: str, metrics: str, dims: str = "") -> list[list]:
    import datetime as _d
    kw = dict(ids="channel==MINE", startDate=start, endDate=_d.date.today().isoformat(), metrics=metrics,
              filters=f"video=={vid}")
    if dims:
        kw["dimensions"] = dims
    return ya.reports().query(**kw).execute().get("rows") or []


def fetch_signals(ya, vid: str, start: str) -> dict[str, Any]:
    """3 consultas: origem de tráfego (views e engajadas), inscritos × não inscritos, aparelho."""
    out: dict[str, Any] = {}
    try:
        traffic = {}
        for src, v, e, m in _q(ya, vid, start, "views,engagedViews,estimatedMinutesWatched", "insightTrafficSourceType"):
            traffic[str(src)] = {"views": int(v or 0), "engaged": int(e or 0), "minutes": float(m or 0)}
        out["traffic"] = traffic
        out["totals"] = {"views": sum(x["views"] for x in traffic.values()),
                         "engaged": sum(x["engaged"] for x in traffic.values())}
    except Exception as e:  # noqa: BLE001
        out["traffic_error"] = str(e)[:160]
    try:
        out["subscribed"] = {str(k): {"views": int(v or 0), "engaged": int(e or 0), "avg_pct": float(p or 0)}
                             for k, v, e, p in _q(ya, vid, start, "views,engagedViews,averageViewPercentage", "subscribedStatus")}
    except Exception as e:  # noqa: BLE001
        out["subscribed_error"] = str(e)[:160]
    try:
        out["device"] = {str(k): int(v or 0) for k, v in _q(ya, vid, start, "views", "deviceType")}
    except Exception as e:  # noqa: BLE001
        out["device_error"] = str(e)[:160]
    return out


def collect_signals(max_per_channel: int = SIG_MAX_PER_CHANNEL, budget_s: float = 240) -> dict[str, int]:
    """Atualiza o cache de sinais dos vídeos que precisam (pouco chamado: seguro rodar a cada coleta de 3 h)."""
    import json
    import time
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime, timedelta, timezone

    from .publish import _yt_client, _yt_creds
    t0 = time.time()
    cache = load_signals()
    now_ = datetime.now(timezone.utc)
    done = {"videos": 0, "calls": 0, "errors": 0}
    with session() as s:
        accs = [a for a in s.exec(select(Account).where(Account.platform == "youtube")).all() if a.credentials]
        pubs = s.exec(select(Publication).where(Publication.platform == "youtube", Publication.status == "published")).all()
    for acc in accs:
        if time.time() - t0 > budget_s:
            break
        due = []
        for p in pubs:
            if p.channel_id != acc.channel_id or not p.external_id or not p.published_at:
                continue
            born = p.published_at if p.published_at.tzinfo else p.published_at.replace(tzinfo=timezone.utc)
            age_d = (now_ - born).total_seconds() / 86400
            if age_d < 1 or age_d > 60:
                continue
            c = cache.get(p.external_id) or {}
            last = c.get("at", 0)
            gap_h = (time.time() - last) / 3600
            if c and c.get("final"):
                continue
            if not c or (age_d <= 14 and gap_h >= 20) or (age_d > 14 and gap_h >= 24 * 7):
                due.append((age_d, p, (born - timedelta(days=1)).date().isoformat()))
        due.sort(key=lambda x: x[0])  # os mais novos primeiro (é onde a decisão importa)
        due = due[:max_per_channel]
        if not due:
            continue
        try:
            creds = _yt_creds(acc)
        except Exception as e:  # noqa: BLE001
            log.info("sinais %s: %s", acc.channel_id, e)
            continue

        def one(item):
            age_d, p, start = item
            try:
                return p, age_d, fetch_signals(_yt_client(creds, "youtubeAnalytics", "v2"), p.external_id, start)
            except Exception as e:  # noqa: BLE001
                return p, age_d, {"error": str(e)[:160]}

        with ThreadPoolExecutor(4) as ex:
            for p, age_d, sig in ex.map(one, due):
                done["calls"] += 3
                if sig.get("error") or sig.get("traffic_error"):
                    done["errors"] += 1
                cache[p.external_id] = {**sig, "at": time.time(), "age_h": round(age_d * 24, 1),
                                        "pub_id": p.id, "channel_id": p.channel_id, "final": age_d > 59}
                done["videos"] += 1
    if done["videos"]:
        _sig_path().write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return done


def signal_features(sig: dict[str, Any] | None) -> dict[str, Any]:
    """Resumo dos sinais de um vídeo (frações 0-1) para o aprendizado e o diagnóstico."""
    if not sig or not sig.get("traffic"):
        return {}
    tr = sig["traffic"]
    tot = sum(x["views"] for x in tr.values()) or 0
    if tot < 20:
        return {"views_an": tot}
    groups: dict[str, int] = {g: 0 for g in ("feed", "search", "suggested", "browse", "external", "ads", "other")}
    for src, x in tr.items():
        g = TRAFFIC_GROUP.get(src, "other")
        groups[g] = groups.get(g, 0) + x["views"]
    top = max(tr.items(), key=lambda kv: kv[1]["views"])
    # engajadas ÷ views ORGÂNICAS: views de anúncio pago (ADVERTISING) distorcem a razão e não contam para o YPP
    org = {k: x for k, x in tr.items() if k != "ADVERTISING"}
    ov = sum(x["views"] for x in org.values())
    eng = sum(x["engaged"] for x in org.values())
    feed = tr.get("SHORTS") or {}
    out: dict[str, Any] = {"views_an": ov, "views_ads": tot - ov, "engaged_an": eng,
                           "top_source": top[0], "top_source_label": TRAFFIC_LABELS.get(top[0], top[0].title()),
                           **{f"share_{g}": round(v / tot, 3) for g, v in groups.items()}}
    if ov >= 20:
        out["engaged_ratio_an"] = round(eng / ov, 3)
    if feed.get("views", 0) >= 20:
        out["feed_engaged_ratio"] = round(feed["engaged"] / feed["views"], 3)
    sub = sig.get("subscribed") or {}
    sv = sum(x["views"] for x in sub.values())
    if sv >= 20:
        out["share_subscribed"] = round((sub.get("SUBSCRIBED") or {}).get("views", 0) / sv, 3)
        uns = sub.get("UNSUBSCRIBED") or {}
        if uns.get("views", 0) >= 20:
            out["unsub_engaged_ratio"] = round(uns["engaged"] / uns["views"], 3)
    dev = sig.get("device") or {}
    dv = sum(dev.values())
    if dv >= 20:
        out["share_mobile"] = round(dev.get("MOBILE", 0) / dv, 3)
        out["share_tv"] = round(dev.get("TV", 0) / dv, 3)
        out["share_desktop"] = round(dev.get("DESKTOP", 0) / dv, 3)
    return out


# ================================================================ MAPA DE QUEDAS × CORTES DE CENA
# Cruza a curva de retenção de cada Short com os tempos de corte das cenas: as quedas se concentram no 1º corte?

def _curve_at_s(curve: list[list[float]], duration: float, t: float) -> float:
    """audienceWatchRatio no segundo t (interpolado)."""
    x = t / duration
    pts = sorted((r[0], r[1]) for r in curve)
    if x <= pts[0][0]:
        return pts[0][1]
    for (a, va), (b, vb) in zip(pts, pts[1:]):
        if a <= x <= b:
            return va + (vb - va) * ((x - a) / (b - a) if b > a else 0)
    return pts[-1][1]


def cut_drops(rows: list[dict[str, Any]] | None = None, channel_id: int | None = None, max_s: int = 60) -> dict[str, Any]:
    """Para cada Short com curva e cenas: queda por segundo (pontos % do público inicial) e onde caem os cortes.
    Agrega em segundos absolutos (0-60 s) e mede se a queda logo depois de cada corte é maior que a do resto."""
    rows = rows if rows is not None else (channel_retention(channel_id) if channel_id else [])
    bins = [{"s": i, "drop": [], "cuts": 0} for i in range(max_s)]
    near_first, near_any, base, first_cut_t = [], [], [], []
    per_video = []
    for r in rows:
        dur = float(r.get("duration") or 0)
        curve = r.get("curve") or []
        cuts = [float(x["end"]) for x in (r.get("scenes") or [])[:-1] if 0.3 < float(x["end"]) < dur - 0.5]
        if not curve or dur <= 0 or dur > 180 or not cuts:
            continue
        start = max(_curve_at_s(curve, dur, 0.0), 0.01)
        n = min(int(dur), max_s)
        drop = [(_curve_at_s(curve, dur, i) - _curve_at_s(curve, dur, i + 1)) / start * 100 for i in range(n)]
        for i, d in enumerate(drop):
            bins[i]["drop"].append(d)
        for c in cuts:
            if int(c) < max_s:
                bins[int(c)]["cuts"] += 1
        first = cuts[0]
        first_cut_t.append(first)
        # janela de 1,5 s depois do corte × média por segundo do vídeo de 2 s ao fim (sem o swipe dos 2 primeiros s)
        def win(t: float) -> float:
            a = max(0.0, t - 0.25)
            return (_curve_at_s(curve, dur, a) - _curve_at_s(curve, dur, a + 1.5)) / start * 100 / 1.5
        tail = [d for i, d in enumerate(drop) if i >= 2 and all(abs(i - c) > 1.5 for c in cuts)]
        b = _mean(tail) if tail else None
        f = win(first)
        o = [win(c) for c in cuts[1:]]
        if b is not None:
            base.append(b)
            near_first.append(f)
            near_any += o
            per_video.append({"publication_id": r.get("publication_id"), "title": r.get("title", ""), "first_cut": round(first, 2),
                              "drop_first_cut": round(f, 2), "drop_other_cuts": round(_mean(o), 2) if o else None,
                              "drop_base": round(b, 2), "hook_drop": round(sum(drop[:2]), 1)})
    heat = [{"s": x["s"], "drop": round(_mean(x["drop"]), 2) if x["drop"] else None, "videos": len(x["drop"]),
             "cuts": x["cuts"]} for x in bins if x["drop"]]
    out: dict[str, Any] = {"videos": len(per_video), "heatmap": heat, "per_video": per_video[:40]}
    if len(per_video) >= 3:
        bf, bo, bb = _mean(near_first), _mean(near_any) if near_any else None, _mean(base)
        out.update({"first_cut_drop": round(bf, 2), "other_cut_drop": None if bo is None else round(bo, 2),
                    "base_drop": round(bb, 2), "first_cut_median_s": round(sorted(first_cut_t)[len(first_cut_t) // 2], 1),
                    "share_first_cut_worse": round(sum(1 for v in per_video if v["drop_first_cut"] > 1.5 * max(v["drop_base"], 0.05))
                                                   / len(per_video), 2)})
        out["first_cut_cluster"] = bool(bf > 1.8 * max(bb, 0.05) and out["share_first_cut_worse"] >= 0.6)
        out["other_cut_cluster"] = bool(bo is not None and bo > 1.5 * max(bb, 0.05) and len(near_any) >= 6)
    return out


def _br(txt: str) -> str:
    """Números com vírgula decimal (5.6 → 5,6)."""
    import re as _re
    return _re.sub(r"(\d)\.(\d)", r"\1,\2", txt)


def cut_rule(channel_id: int, rows: list[dict[str, Any]] | None = None) -> str:
    """Regra objetiva quando as quedas se concentram nos cortes (entra no prompt do roteirista e nas lições)."""
    c = cut_drops(rows, channel_id)
    if c.get("first_cut_cluster"):
        return _br(f"O público sai no 1º CORTE (~{c['first_cut_median_s']:.1f}s): ali a queda é {c['first_cut_drop']:.1f} pontos/s × "
                f"{c['base_drop']:.1f} no resto ({c['videos']} Shorts; em {round(c['share_first_cut_worse'] * 100)}% deles). "
                "Não corte de cena antes de entregar a promessa do gancho: segure a 1ª imagem até ~3s e faça o 1º corte "
                "num movimento (zoom/texto entrando), nunca numa tela parada ou de contexto.")
    if c.get("other_cut_cluster"):
        return _br(f"As quedas se concentram logo depois dos cortes de cena ({c['other_cut_drop']:.1f} × {c['base_drop']:.1f} "
                f"pontos/s, {c['videos']} Shorts): emende as cenas com a frase continuando por cima do corte (sem pausa).")
    return ""
