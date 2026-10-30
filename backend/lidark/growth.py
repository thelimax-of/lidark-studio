"""Crescimento: laboratório de experimentos, campanhas sazonais e progresso para a monetização (YPP)."""
from __future__ import annotations

import logging
import random
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from sqlmodel import select

from .db import session
from .models import Channel, Idea, Script, Video

log = logging.getLogger("lidark.growth")

# ================================================================ laboratório de experimentos
#
# Cada vídeo sai com escolhas sorteadas (variety.plan). Aqui cruzamos essas escolhas com o desempenho
# real de cada vídeo publicado para descobrir o que funciona — e o sorteio passa a favorecer o vencedor.

def _look(key: str) -> Callable[[dict], Any]:
    return lambda p: (p.get("look") or {}).get(key)


def _secs(p: dict) -> str | None:
    from .variety import duration_band
    return duration_band(p.get("seconds"))  # mesma faixa (curto/medio/longo) que o sorteio usa


DIMENSIONS: dict[str, tuple[str, Callable[[dict], Any]]] = {
    "structure": ("Estrutura narrativa", lambda p: p.get("structure")),
    "hook_style": ("Tipo de gancho", lambda p: p.get("hook_style")),
    "title_style": ("Padrão de título", lambda p: p.get("title_style")),
    "graphics": ("Dose de gráficos", lambda p: p.get("graphics")),
    "duration": ("Duração do Short", _secs),
    "grade": ("Tratamento de cor", _look("grade")),
    "caption": ("Estilo de legenda", _look("caption")),
    "intro": ("Abertura", _look("intro")),
    "outro": ("Encerramento", _look("outro")),
    "thumb_variant": ("Layout da miniatura", lambda p: p.get("thumb_variant")),
}

LABELS: dict[str, dict[str, str]] = {
    "hook_style": {"correcao": "Correção de mito", "pergunta": "Pergunta", "numero": "Número chocante", "contraintuitivo": "Contraintuitivo",
                   "cena": "Cena narrada", "desafio": "Desafio", "consequencia": "Consequência primeiro"},
    "title_style": {"lacuna": "Lacuna", "busca": "Pergunta de busca", "pergunta": "Pergunta", "afirmacao": "Afirmação", "numero": "Número", "o_dia": "“O dia em que”",
                    "nome": "Nome + revelação", "contraste": "Contraste"},
    "graphics": {"poucas": "Poucos gráficos", "médias": "Gráficos médios", "muitas": "Muitos gráficos"},
    "grade": {"neutro": "Neutro", "quente": "Quente", "frio": "Frio", "contraste": "Contraste", "sepia": "Sépia", "filme": "Filme"},
    "caption": {"classic": "Caixa clássica", "highlight": "Pílula na palavra", "karaoke": "Karaokê", "bold": "Palavra a palavra"},
    "intro": {"typed": "Texto digitado", "words": "Palavra gigante", "band": "Faixa de cinema", "punch": "Zoom com flash"},
    "outro": {"classic": "Clássico", "handle": "@ gigante", "minimal": "Minimalista"},
    "duration": {"curto": "Curto (até 38s)", "medio": "Médio (39–50s)", "longo": "Longo (51s+)"},
}

MIN_N = 2  # mínimo de vídeos por opção para considerar o resultado


def _rows(channel_id: int) -> list[dict[str, Any]]:
    """Vídeos publicados com desempenho + o plano de variedade que os gerou."""
    from .analytics import performance_table
    try:
        rows = performance_table(channel_id)
    except Exception as e:  # noqa: BLE001
        log.info("experimentos: %s", e)
        return []
    out = []
    with session() as s:
        for r in rows:
            vid = r.get("video_id")
            v = s.get(Video, vid) if isinstance(vid, int) else None
            sc = s.get(Script, v.script_id) if v else None
            if sc and sc.variety and r.get("perf") is not None:
                out.append({**r, "plan": sc.variety, "format": sc.format})
    return out


def experiments(channel_id: int) -> dict[str, Any]:
    rows = _rows(channel_id)
    if not rows:
        return {"videos": 0, "dimensions": [], "lessons": []}
    base_perf = sum(r["perf"] for r in rows) / len(rows)
    base_ret = sum(r["retention"] for r in rows) / len(rows)
    dims, lessons = [], []
    for key, (label, get) in DIMENSIONS.items():
        acc: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            v = get(r["plan"])
            if v not in (None, ""):
                acc[str(v)].append(r)
        if not acc:
            continue
        from .variety import STRUCTURES
        names = LABELS.get(key) or ({k: v["name"] for k, v in STRUCTURES.items()} if key == "structure" else {})
        opts = []
        for opt, rs in acc.items():
            opts.append({"key": opt, "label": names.get(opt, opt), "n": len(rs),
                         "perf": round(sum(x["perf"] for x in rs) / len(rs)),
                         "retention": round(sum(x["retention"] for x in rs) / len(rs), 1),
                         "views": round(sum(x["views"] for x in rs) / len(rs))})
        opts.sort(key=lambda o: (-(o["n"] >= MIN_N), -o["perf"]))
        valid = [o for o in opts if o["n"] >= MIN_N]
        winner = valid[0] if len(valid) >= 2 else None
        if winner:
            lift = winner["perf"] - base_perf
            if lift >= 8:
                lessons.append(f"{label}: “{winner['label']}” rende mais (desempenho {winner['perf']} vs média {base_perf:.0f}; "
                               f"retenção {winner['retention']}% vs {base_ret:.0f}%, {winner['n']} vídeos)")
            loser = valid[-1]
            if base_perf - loser["perf"] >= 10:
                lessons.append(f"{label}: “{loser['label']}” rende menos (desempenho {loser['perf']}, {loser['n']} vídeos)")
        dims.append({"key": key, "label": label, "options": opts, "winner": winner["key"] if winner else None})
    # lições: as do aprendizado bayesiano (normalizadas pela idade, com confiança) substituem as médias simples acima,
    # que com 2 vídeos por opção "achavam" vencedores por acaso; as médias continuam na tabela do painel
    try:
        from .learning import _get_state, _lessons
        bayes = [x["text"] for x in _lessons(_get_state(), channel_id, None, 8)]
    except Exception as e:  # noqa: BLE001
        log.info("lições bayesianas: %s", e)
        bayes = None
    return {"videos": len(rows), "base_perf": round(base_perf), "base_retention": round(base_ret, 1),
            "dimensions": dims, "lessons": bayes if bayes is not None else lessons, "naive_lessons": lessons}


def dimension_weights(channel_id: int) -> dict[str, dict[str, float]]:
    """{dimensão: {opção: peso}} para o sorteio do variety.py (50 = neutro). Vem do bandit bayesiano (learning.py:
    Thompson sampling com prior compartilhado entre canais, views normalizadas pela idade); se ele falhar, cai na média
    simples antiga, só com opções testadas o bastante."""
    try:
        from .learning import recommend_variety
        return recommend_variety(channel_id)
    except Exception as e:  # noqa: BLE001
        log.info("pesos bayesianos: %s", e)
    out: dict[str, dict[str, float]] = {}
    for d in experiments(channel_id).get("dimensions", []):
        w = {o["key"]: float(o["perf"]) for o in d["options"] if o["n"] >= MIN_N}
        if len(w) >= 2:
            out[d["key"]] = w
    return out


# ================================================================ campanhas sazonais

ENEM_DAY = date(2026, 11, 8)  # 1º dia do ENEM 2026 (Linguagens, Ciências Humanas e Redação) — edital do Inep


def default_campaigns(ch: Channel) -> list[dict[str, Any]]:
    """Campanhas sugeridas automaticamente para o nicho (ex.: canal de história do ENEM)."""
    txt = f"{ch.niche} {ch.editorial_guide} {ch.description}".lower()
    if "enem" not in txt:
        return []
    return [
        {"id": "enem-revisao-2026", "name": "Revisão ENEM de História", "start": "2026-10-27",
         "end": ENEM_DAY.isoformat(), "share": 0.7, "active": True,
         "focus": "os temas de História que mais caem no ENEM (Brasil Colônia, Império, Era Vargas, Ditadura, "
                  "Revolução Industrial, Guerras Mundiais, Guerra Fria, Antiguidade), explicados como revisão "
                  "rápida e memorável para a prova, com o que costuma ser cobrado"},
        {"id": "enem-correcao-2026", "name": "Correção ENEM 2026", "start": (ENEM_DAY + timedelta(days=1)).isoformat(),
         "end": (ENEM_DAY + timedelta(days=14)).isoformat(), "share": 0.6, "active": True,
         "focus": "as questões de História que caíram no ENEM 2026: o contexto histórico por trás de cada questão "
                  "e a resposta explicada (só fatos confirmados por fontes)"},
    ]


def ensure_campaigns(ch: Channel) -> list[dict[str, Any]]:
    if ch.campaigns:
        return ch.campaigns
    camps = default_campaigns(ch)
    if camps:
        with session() as s:
            db = s.get(Channel, ch.id)
            db.campaigns = camps
            s.add(db)
            s.commit()
    return camps


def active_campaign(ch: Channel, today: date | None = None) -> dict[str, Any] | None:
    today = today or date.today()
    for c in ensure_campaigns(ch):
        try:
            if c.get("active", True) and date.fromisoformat(c["start"]) <= today <= date.fromisoformat(c["end"]):
                return c
        except (KeyError, ValueError):
            continue
    return None


def campaign_tag(c: dict[str, Any]) -> str:
    return f"campanha:{c['id']}"


def campaign_of(idea: Idea | None, ch: Channel) -> dict[str, Any] | None:
    if not idea:
        return None
    for c in ch.campaigns or []:
        if campaign_tag(c) in (idea.tags or []):
            return c
    return None


def wants_campaign(ch: Channel) -> dict[str, Any] | None:
    """Sorteia se o próximo vídeo do piloto automático entra na campanha ativa."""
    c = active_campaign(ch)
    return c if c and random.random() < float(c.get("share", 0.6)) else None


# ================================================================ progresso para a monetização (YPP)

# Limites da Central de Ajuda do YouTube ("Shorts monetization policies" / requisitos do YPP), conferidos em 10/2026.
# São regras de política, não dados da API: podem mudar — revise aqui se o YouTube anunciar outra coisa.
# - Shorts contam por VIEWS ENGAJADAS (desde 31/03/2025 "views" conta todo início/replay e não serve p/ monetizar);
# - views de anúncio pago (tráfego ADVERTISING), Shorts privados/não listados e bots não são views qualificadas;
# - só views do feed do Shorts dividem receita de anúncios;
# - a partir de 01/02/2027: novas inscrições precisam de 20 mi de views qualificadas de Shorts em 90 dias (ou 8.000 h)
#   e quem já é parceiro precisa manter 10 mi/90 dias para continuar na divisão de receita dos Shorts.
RULES_2027 = date(2027, 2, 1)
YPP = {
    "basic": {"label": "Nível básico (Clube, Super Thanks, compras)", "subs": 500, "hours": 3000, "shorts_views": 3_000_000},
    "full": {"label": "Monetização completa (anúncios) — regra até 31/01/2027", "subs": 1000, "hours": 4000,
             "shorts_views": 10_000_000, "until": (RULES_2027 - timedelta(days=1)).isoformat()},
    "full_2027": {"label": "Monetização completa — novas inscrições a partir de 01/02/2027", "subs": 1000, "hours": 8000,
                  "shorts_views": 20_000_000, "from": RULES_2027.isoformat()},
}
YPP_KEEP_SHORTS_2027 = 10_000_000  # parceiro precisa manter isso em 90 dias p/ seguir com receita de Shorts (desde 01/02/2027)
YPP_NOTES = [
    "Shorts: só conta a view ENGAJADA (o número “views” do YouTube inclui todo início/replay).",
    "Views vindas de anúncio pago (promoção) não são qualificadas — ficam fora do progresso.",
    "Só views do feed do Shorts dividem receita de anúncios.",
    "A partir de 01/02/2027: 20 mi views qualificadas/90 dias (ou 8.000 h) p/ entrar; parceiros precisam manter 10 mi/90 dias.",
    "Limites tirados da Central de Ajuda do YouTube — podem mudar; o YouTube confirma tudo na revisão do canal.",
]


def _by_type(ya, start: date, end: date) -> dict[str, dict[str, float]]:
    """Por tipo de conteúdo: views brutas, engajadas, qualificadas (engajadas sem anúncio pago) e minutos."""
    q = dict(ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
             dimensions="creatorContentType,insightTrafficSourceType")
    try:
        rows = ya.reports().query(metrics="views,engagedViews,estimatedMinutesWatched", **q).execute().get("rows", []) or []
    except Exception as e:  # noqa: BLE001  (sem engagedViews: usa as views brutas, marcado como estimativa)
        log.warning("ypp engagedViews: %s", e)
        rows = [[t, src, v, None, m] for t, src, v, m in
                ya.reports().query(metrics="views,estimatedMinutesWatched", **q).execute().get("rows", []) or []]
    out: dict[str, dict[str, float]] = {}
    for t, src, v, e, m in rows:
        d = out.setdefault(str(t).lower(), {"views": 0.0, "engaged": 0.0, "qualified": 0.0, "minutes": 0.0,
                                            "minutes_qualified": 0.0, "ads_views": 0.0, "feed_engaged": 0.0,
                                            "estimated": e is None})
        eng = float(v if e is None else e)
        d["views"] += float(v)
        d["engaged"] += eng
        d["minutes"] += float(m)
        if src == "ADVERTISING":  # promoção paga: não é view qualificada
            d["ads_views"] += float(v)
        else:
            d["qualified"] += eng
            d["minutes_qualified"] += float(m)
        if src == "SHORTS":  # feed do Shorts: o único que divide receita de anúncios
            d["feed_engaged"] += eng
    return out


def ypp_status(ch: Channel) -> dict[str, Any]:
    from .analytics import daily_analytics
    from .models import Account
    from .publish import _yt_client, _yt_creds
    with session() as s:
        acc = s.exec(select(Account).where(Account.channel_id == ch.id, Account.platform == "youtube")).first()
    if not acc or not acc.credentials:
        return {"connected": False}
    ya = _yt_client(_yt_creds(acc), "youtubeAnalytics", "v2")
    today = date.today()
    y365 = _by_type(ya, today - timedelta(days=365), today)
    d90 = _by_type(ya, today - timedelta(days=90), today)
    d28 = _by_type(ya, today - timedelta(days=28), today)

    def longs(d: dict, k: str = "minutes_qualified") -> float:
        return sum(v[k] for t, v in d.items() if "short" not in t)

    def shorts(d: dict, k: str = "qualified") -> float:
        return sum(v[k] for t, v in d.items() if "short" in t)

    # horas: vídeos longos sem anúncio pago; Shorts: views engajadas sem anúncio pago
    hours = longs(y365) / 60
    shorts90 = shorts(d90)
    hours_rate = longs(d28) / 60 / 28  # horas/dia
    shorts_rate = shorts(d28) / 28  # views qualificadas/dia
    try:
        subs_rate = sum(r["subs"] for r in daily_analytics(ch.id, 28)["rows"]) / 28
    except Exception:  # noqa: BLE001
        subs_rate = 0.0
    subs = int((ch.stats or {}).get("subscribers") or 0)

    def eta(have: float, need: float, rate: float) -> int | None:
        if have >= need:
            return 0
        return int((need - have) / rate) + 1 if rate > 0 else None

    tiers = {}
    for key, t in YPP.items():
        if t.get("until") and today.isoformat() > t["until"]:
            continue  # regra antiga já expirou
        subs_eta = eta(subs, t["subs"], subs_rate)
        hours_eta = eta(hours, t["hours"], hours_rate)
        # janela móvel de 90 dias: no ritmo atual, a janela estabiliza em 90 × views/dia
        steady = shorts_rate * 90
        shorts_eta = 0 if shorts90 >= t["shorts_views"] else (eta(shorts90, t["shorts_views"], shorts_rate) if steady >= t["shorts_views"] else None)
        path = min((x for x in (hours_eta, shorts_eta) if x is not None), default=None)
        total = None if (subs_eta is None or path is None) else max(subs_eta, path)
        tiers[key] = {**t, "subs_eta": subs_eta, "hours_eta": hours_eta, "shorts_eta": shorts_eta,
                      "eta_days": total, "eta_date": (today + timedelta(days=total)).isoformat() if total is not None else None,
                      "shorts_per_day_needed": round(t["shorts_views"] / 90)}
    raw90, eng90 = shorts(d90, "views"), shorts(d90, "engaged")
    return {"connected": True, "updated_at": datetime.now(timezone.utc).isoformat(), "subs": subs, "hours_12m": round(hours, 1),
            "hours_12m_raw": round(longs(y365, "minutes") / 60, 1),
            # shorts_views_90d = views QUALIFICADAS (engajadas, sem anúncio pago) — é o que vale p/ o YPP
            "shorts_views_90d": int(shorts90), "shorts_raw_views_90d": int(raw90), "shorts_engaged_views_90d": int(eng90),
            "shorts_ads_views_90d": int(shorts(d90, "ads_views")), "shorts_feed_engaged_90d": int(shorts(d90, "feed_engaged")),
            "engaged_rate": round(100 * eng90 / raw90, 1) if raw90 else None,
            "engaged_estimated": any(v.get("estimated") for v in d90.values()),
            "rates": {"subs_per_day": round(subs_rate, 2), "hours_per_day": round(hours_rate, 2),
                      "shorts_views_per_day": round(shorts_rate), "shorts_raw_views_per_day": round(shorts(d28, "views") / 28)},
            "keep_shorts_2027": YPP_KEEP_SHORTS_2027, "rules_from": RULES_2027.isoformat(), "notes": YPP_NOTES,
            "tiers": tiers}


def ypp_cached(ch: Channel, max_age_h: float = 6) -> dict[str, Any]:
    cur = (ch.stats or {}).get("ypp") or {}
    try:
        fresh = cur and datetime.fromisoformat(cur["updated_at"]) > datetime.now(timezone.utc) - timedelta(hours=max_age_h)
    except (KeyError, ValueError):
        fresh = False
    if fresh:
        return cur
    try:
        res = ypp_status(ch)
    except Exception as e:  # noqa: BLE001
        log.warning("ypp: %s", e)
        return {**cur, "error": str(e)[:300]} if cur else {"connected": True, "error": str(e)[:300]}
    if res.get("connected"):
        with session() as s:
            db = s.get(Channel, ch.id)
            db.stats = {**(db.stats or {}), "ypp": res}
            s.add(db)
            s.commit()
    return res
