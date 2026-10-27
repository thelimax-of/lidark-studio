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
    s = p.get("seconds")
    if not s:
        return None
    return "61–66s" if s <= 66 else ("67–72s" if s <= 72 else "73s+")


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
    "hook_style": {"pergunta": "Pergunta", "numero": "Número chocante", "contraintuitivo": "Contraintuitivo",
                   "cena": "Cena narrada", "desafio": "Desafio", "consequencia": "Consequência primeiro"},
    "title_style": {"pergunta": "Pergunta", "afirmacao": "Afirmação", "numero": "Número", "o_dia": "“O dia em que”",
                    "nome": "Nome + revelação", "contraste": "Contraste"},
    "graphics": {"poucas": "Poucos gráficos", "médias": "Gráficos médios", "muitas": "Muitos gráficos"},
    "grade": {"neutro": "Neutro", "quente": "Quente", "frio": "Frio", "contraste": "Contraste", "sepia": "Sépia", "filme": "Filme"},
    "caption": {"classic": "Caixa clássica", "highlight": "Pílula na palavra", "karaoke": "Karaokê", "bold": "Palavra a palavra"},
    "intro": {"typed": "Texto digitado", "words": "Palavra gigante", "band": "Faixa de cinema", "punch": "Zoom com flash"},
    "outro": {"classic": "Clássico", "handle": "@ gigante", "minimal": "Minimalista"},
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
    return {"videos": len(rows), "base_perf": round(base_perf), "base_retention": round(base_ret, 1),
            "dimensions": dims, "lessons": lessons}


def dimension_weights(channel_id: int) -> dict[str, dict[str, float]]:
    """{dimensão: {opção: desempenho médio}} só com opções testadas o bastante — usado no sorteio."""
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

YPP = {
    "basic": {"label": "Nível básico (Clube, Super Thanks, compras)", "subs": 500, "hours": 3000, "shorts_views": 3_000_000},
    "full": {"label": "Monetização completa (anúncios)", "subs": 1000, "hours": 4000, "shorts_views": 10_000_000},
}


def _by_type(ya, start: date, end: date) -> dict[str, dict[str, float]]:
    r = ya.reports().query(ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
                           metrics="views,estimatedMinutesWatched", dimensions="creatorContentType").execute()
    out: dict[str, dict[str, float]] = {}
    for t, v, m in r.get("rows", []) or []:
        out[str(t).lower()] = {"views": float(v), "minutes": float(m)}
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

    def long_minutes(d: dict) -> float:
        return sum(v["minutes"] for k, v in d.items() if "short" not in k)

    def short_views(d: dict) -> float:
        return sum(v["views"] for k, v in d.items() if "short" in k)

    hours = long_minutes(y365) / 60
    shorts90 = short_views(d90)
    hours_rate = long_minutes(d28) / 60 / 28  # horas/dia
    shorts_rate = short_views(d28) / 28  # views/dia
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
    return {"connected": True, "updated_at": datetime.now(timezone.utc).isoformat(), "subs": subs, "hours_12m": round(hours, 1),
            "shorts_views_90d": int(shorts90), "rates": {"subs_per_day": round(subs_rate, 2), "hours_per_day": round(hours_rate, 2),
                                                         "shorts_views_per_day": round(shorts_rate)},
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
