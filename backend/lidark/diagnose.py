"""“Por que flopou”: diagnóstico em português simples de cada vídeo a partir de 48 h no ar.

Compara o vídeo com o normal do PRÓPRIO canal (mesmo formato), usando o que o aprendizado já mede:
- desempenho na mesma idade (x o normal, curva típica do learning.py);
- engajadas ÷ views (quem não deslizou) e retenção aos 3 s → GANCHO;
- retenção no meio em relação ao começo → MEIO;
- quedas concentradas no 1º corte de cena (retention.cut_drops) → CORTE;
- retenção normal mas poucas views (e quase nada vindo do feed/sugeridos) → TEMA/DISTRIBUIÇÃO;
- vídeo longo com retenção normal e poucas views → MINIATURA/TÍTULO (o CTR de impressões não existe na API pública do
  Analytics: o diagnóstico manda conferir no Studio).
Cada causa traz evidência (números) e uma ação sugerida. Os flops (< 0,6x o normal) viram notificação (uma por vídeo).
"""
from __future__ import annotations

import json
import logging
import math
import statistics
from typing import Any

from .config import CACHE_DIR

log = logging.getLogger("lidark.diagnose")
SENT_PATH = CACHE_DIR / "diagnose_sent.json"
MIN_AGE_H = 48
NOTIFY_MAX_AGE_H = 120
FLOP_X = 0.6
LOW_X = 0.85


def _med(xs: list[float]) -> float | None:
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if len(xs) >= 3 else None


def _pct(v: float) -> str:
    return f"{round(v * 100)}%"


def _baselines(recs: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, float | None]]:
    from .learning import _er
    groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for r in recs:
        groups.setdefault((r["channel_id"], r.get("format") or "short"), []).append(r)
    out = {}
    for k, rs in groups.items():
        ret = [r.get("retention") or {} for r in rs]
        out[k] = {"er": _med([_er(r) for r in rs]),
                  "hook": _med([x.get("hook") for x in ret]),
                  "mid_rel": _med([x["mid"] / x["hook"] for x in ret if x.get("hook") and x.get("mid") is not None]),
                  "end": _med([x.get("end") for x in ret]),
                  "feed": _med([(r.get("signals") or {}).get("share_feed") for r in rs]),
                  "n": len(rs)}
    return out


def _best_opening(st: dict[str, Any], cid: int) -> str:
    try:
        from .learning import audience_signals
        for d in audience_signals(st, cid)["by_dimension"]:
            if d["key"] == "opening_type":
                ok = [o for o in d["options"] if o["n_er"] >= 2 and o["engaged_ratio"] is not None]
                if len(ok) >= 2:
                    return ok[0]["label"]
    except Exception:  # noqa: BLE001
        pass
    return ""


def diagnose_record(r: dict[str, Any], base: dict[str, Any], st: dict[str, Any], cut: dict[str, Any] | None = None) -> dict[str, Any]:
    from .learning import _er
    x = None if r.get("rel") is None else math.exp(r["rel"])
    fmt = r.get("format") or "short"
    ret = r.get("retention") or {}
    sg = r.get("signals") or {}
    er = _er(r)
    causes: list[dict[str, Any]] = []
    partial = er is None and not ret.get("hook")

    # GANCHO: muita gente deslizou / saiu nos 3 primeiros segundos
    hook_gap = 0.0
    ev = []
    if er is not None and base.get("er"):
        g = (base["er"] - er) / base["er"]
        if g >= 0.12:
            hook_gap = max(hook_gap, g)
            ev.append(f"só {_pct(er)} das views ficaram (engajadas) × {_pct(base['er'])} no normal do canal")
    if ret.get("hook") and base.get("hook"):
        g = (base["hook"] - ret["hook"]) / max(base["hook"], 1)
        if g >= 0.1:
            hook_gap = max(hook_gap, g)
            ev.append(f"retém {ret['hook']:.0f}% aos 3s × {base['hook']:.0f}% no normal")
    if hook_gap:
        best = _best_opening(st, r["channel_id"]) if fmt == "short" else ""
        act = ("Refaça a abertura: o fato mais forte (número, nome ou cena) nas 5 primeiras palavras e imagem em "
               "movimento já no 1º segundo." + (f" No canal, a abertura que mais segura é “{best}”." if best else ""))
        if cut and cut.get("first_cut_cluster"):
            act += f" E não corte de cena antes de ~3s: o canal perde público no 1º corte (~{cut['first_cut_median_s']:.1f}s)."
        causes.append({"key": "hook", "label": "Gancho (o público deslizou)", "severity": round(hook_gap, 2),
                       "evidence": "; ".join(ev), "action": act})

    # MEIO: caiu muito depois do gancho
    if ret.get("hook") and ret.get("mid") is not None and base.get("mid_rel"):
        mr = ret["mid"] / ret["hook"]
        g = (base["mid_rel"] - mr) / max(base["mid_rel"], 0.05)
        if g >= 0.15:
            causes.append({"key": "middle", "label": "Meio (perdeu público depois do gancho)", "severity": round(g, 2),
                           "evidence": f"do começo ao meio sobra {_pct(mr)} de quem passou dos 3s × {_pct(base['mid_rel'])} no normal",
                           "action": "Ponha uma virada ou um fato novo no meio, corte enrolação e divida cenas longas "
                                     "(mais de ~25 palavras). Guarde a revelação mais forte para depois do meio."})

    # TEMA / DISTRIBUIÇÃO: segurou o público, mas o YouTube quase não mostrou
    ret_ok = (er is None or not base.get("er") or er >= 0.92 * base["er"]) and \
             (not ret.get("hook") or not base.get("hook") or ret["hook"] >= base["hook"] - 5)
    if x is not None and x < LOW_X and ret_ok and not partial:
        if fmt == "long":
            causes.append({"key": "thumbnail", "label": "Miniatura/título (pouca gente clicou)", "severity": round(1 - x, 2),
                           "evidence": f"{x:.1f}x o normal na mesma idade com retenção normal".replace(".", ","),
                           "action": "Troque a miniatura e o título (teste A/B no Studio). O CTR de impressões não sai na "
                                     "API pública: confira em Studio → Análises → Alcance."})
        else:
            feed = sg.get("share_feed")
            evid = f"{x:.1f}x o normal na mesma idade, mas quem viu ficou".replace(".", ",")
            if sg.get("views_an") is not None:
                evid += f"; o feed do Shorts entregou {sg.get('views_an')} views" + (f" ({_pct(feed)} do total)" if feed is not None else "")
            causes.append({"key": "topic", "label": "Tema/distribuição (o YouTube quase não mostrou)", "severity": round(1 - x, 2),
                           "evidence": evid,
                           "action": "O tema não puxou o feed. Não insista na mesma história: troque o ângulo ou use um tema do "
                                     "radar/almanaque. Se o tema é forte, reposte só com título e abertura novos daqui a semanas."})
    causes.sort(key=lambda c: -c["severity"])
    status = "sem dados" if x is None else "flop" if x < FLOP_X else "abaixo" if x < LOW_X else "ok"
    if status == "ok":
        summary = f"Não flopou: {x:.1f}x o normal do canal na mesma idade.".replace(".", ",", 1)
    elif not causes:
        summary = ("Ainda sem dados do Analytics para apontar a causa (chegam com ~2 dias de atraso)." if partial else
                   "Abaixo do normal, sem uma causa clara nos números (variação normal).")
    else:
        c = causes[0]
        summary = f"Causa principal: {c['label'][:1].lower() + c['label'][1:]} — {c['evidence']}. Ação: {c['action']}"
    return {"pub_id": r["pub_id"], "channel_id": r["channel_id"], "title": r["title"], "url": r.get("url"),
            "format": fmt, "age_h": round(r.get("age_h") or 0, 1), "views": r.get("views"),
            "x_normal": None if x is None else round(x, 2), "status": status, "causes": causes, "summary": summary,
            "partial": partial, "engaged_ratio": er, "hook_3s": ret.get("hook"),
            "top_source": sg.get("top_source_label")}


def diagnose(channel_id: int | None = None, min_age_h: float = MIN_AGE_H, max_age_h: float = 24 * 30,
             limit: int = 30) -> list[dict[str, Any]]:
    from .learning import _get_state
    from .retention import cut_drops
    st = _get_state()
    recs = st.get("records") or []
    base = _baselines(recs)
    cuts: dict[int, dict[str, Any]] = {}
    out = []
    for r in sorted(recs, key=lambda r: r["published_at"], reverse=True):
        if channel_id is not None and r["channel_id"] != channel_id:
            continue
        if not (min_age_h <= (r.get("age_h") or 0) <= max_age_h):
            continue
        cid = r["channel_id"]
        if cid not in cuts:
            try:
                cuts[cid] = cut_drops(channel_id=cid)
            except Exception:  # noqa: BLE001
                cuts[cid] = {}
        out.append(diagnose_record(r, base.get((cid, r.get("format") or "short")) or {}, st, cuts[cid]))
        if len(out) >= limit:
            break
    return out


def _sent() -> set[int]:
    try:
        return set(json.loads(SENT_PATH.read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return set()


def scan(notify_: bool = True) -> dict[str, Any]:
    """Diagnostica os vídeos de 48-120 h e avisa (uma vez por vídeo) os que floparam. Chamado pelo learning.refresh."""
    rows = diagnose(None, MIN_AGE_H, NOTIFY_MAX_AGE_H, limit=200)
    sent = _sent()
    notified = 0
    for d in rows:
        if d["status"] != "flop" or d["pub_id"] in sent:
            continue
        if d["partial"] or not d["causes"]:  # sem Analytics (atraso ~2 dias / canal sem login) não chuta a causa
            continue
        if notify_:
            try:
                from . import notify
                notify.send(f"Por que flopou: {d['title'][:70]}", d["summary"], event="diagnose", tags=["mag"])
            except Exception as e:  # noqa: BLE001
                log.info("aviso de diagnóstico: %s", e)
                continue
        sent.add(d["pub_id"])
        notified += 1
    if notified:
        SENT_PATH.write_text(json.dumps(sorted(sent)), encoding="utf-8")
    return {"checked": len(rows), "notified": notified}
