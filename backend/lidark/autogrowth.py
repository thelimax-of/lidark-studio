"""Piloto automático de crescimento: a cada 30 min, por canal, age sozinho dentro de limites seguros e registra
cada ação como notificação (sino do painel) e no histórico (página "Piloto de crescimento").

Automações (cada uma liga/desliga por canal):
- posting_times: muda o canal para horários automáticos quando já há dados suficientes (uma vez só)
- breakouts: vídeo estourando → pauta de continuação (outro ângulo do mesmo tema, não uma cópia)
- long_version: Short campeão → vídeo longo (o "Short campeão → longo" do longform), no máximo 1 por semana
- seed_comments: garante o comentário do canal que puxa conversa nos vídeos novos (e avisa para fixar)
- retitle_flops: fracasso claro após 48 h → troca o título UMA vez (teste A/B, com antes/depois registrado)
- trend_stock: estoque de pautas atento às tendências (radar em dia e pautas urgentes aprovadas)

Os avisos de estouro/fracasso e marcos do YPP saem sempre (são só informação); as ações só com o piloto ligado.
Política de variedade: continuações e títulos novos são pedidos com ângulo/estilo DIFERENTE do original.
"""
from __future__ import annotations

import logging
import statistics
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel, func, select

from . import notify
from .db import session
from .jobs import enqueue
from .models import Channel, Comment, Idea, Job, Publication, Script, Video, now

log = logging.getLogger("lidark.autogrowth")


class AutoGrowthConfig(SQLModel, table=True):
    channel_id: int = Field(primary_key=True)
    toggles: dict = Field(default_factory=dict, sa_column=Column(JSON))
    state: dict = Field(default_factory=dict, sa_column=Column(JSON))  # marcos já vistos, última rodada...
    updated_at: datetime = Field(default_factory=now)


class GrowthAction(SQLModel, table=True):
    """Histórico do piloto: o que foi feito, quando e com que resultado (título antes/depois, etc.)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: int = Field(index=True)
    kind: str = Field(index=True)  # posting_times | followup | long | seed | retitle | trend_radar | trend_approve
    ref: str = Field(default="", index=True)  # publicação/vídeo/pauta a que se refere
    title: str = ""
    data: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = "done"  # done | testing | better | worse | neutral | failed
    created_at: datetime = Field(default_factory=now, index=True)
    updated_at: datetime = Field(default_factory=now)


AUTOMATIONS = {
    "posting_times": {"label": "Melhores horários pelos dados",
                      "desc": "Quando houver Shorts medidos o bastante, passa o canal para horários automáticos (uma vez)."},
    "breakouts": {"label": "Continuação de vídeo que estourou",
                  "desc": "Vídeo bem acima da mediana do canal → cria pauta de continuação com outro ângulo do tema."},
    "long_version": {"label": "Short campeão → vídeo longo",
                     "desc": "Short campeão vira roteiro de vídeo longo em capítulos (você revisa antes de renderizar). Máx. 1/semana."},
    "seed_comments": {"label": "Comentário do canal nos vídeos novos",
                      "desc": "Garante o comentário que puxa conversa e avisa para fixar (a API do YouTube não deixa fixar sozinho)."},
    "retitle_flops": {"label": "Novo título para fracassos claros",
                      "desc": "Após 48 h muito abaixo da mediana, troca o título UMA vez e mede antes/depois. Máx. 1/dia."},
    "trend_stock": {"label": "Estoque de pautas com tendências",
                    "desc": "Mantém o radar em dia e aprova pautas de tendência urgentes já checadas (máx. 2/dia)."},
}
DEFAULTS = {k: True for k in AUTOMATIONS}
LIMITS = {"retitle_per_day": 1, "followups_per_week": 3, "long_per_week": 1, "trend_approve_per_day": 2}
BREAKOUT_X = 2.5  # views na mesma idade ≥ 2,5× a mediana do canal
FLOP_X = 0.3  # ≤ 30% da mediana em 48 h
MIN_BASE = 5  # vídeos com medição para formar a mediana

SUBS_MARKS = [100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
SHORTS_MARKS = [100_000, 500_000, 1_000_000, 3_000_000, 5_000_000, 10_000_000]
HOURS_MARKS = [100, 500, 1000, 3000, 4000]

_ready = False
_lock = threading.Lock()


def _ensure() -> None:
    global _ready
    if not _ready:
        from .db import engine
        for t in (AutoGrowthConfig, GrowthAction):
            t.__table__.create(engine, checkfirst=True)
        _ready = True


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def clean(t: str) -> str:
    import re
    return re.sub(r"\s*#shorts\b", "", t or "", flags=re.I).strip()


# ---------------------------------------------------------------- configuração por canal

def get_config(channel_id: int) -> AutoGrowthConfig:
    _ensure()
    with session() as s:
        cfg = s.get(AutoGrowthConfig, channel_id)
        if cfg is None:
            cfg = AutoGrowthConfig(channel_id=channel_id, toggles={}, state={})
            s.add(cfg)
            s.commit()
            s.refresh(cfg)
        return cfg


def settings(ch: Channel) -> dict[str, Any]:
    t = get_config(ch.id).toggles or {}
    enabled = t.get("enabled")
    return {"enabled": bool(ch.auto_pilot) if enabled is None else bool(enabled), "enabled_default": enabled is None,
            **{k: bool(t.get(k, v)) for k, v in DEFAULTS.items()}}


def set_settings(channel_id: int, patch: dict[str, Any]) -> dict[str, Any]:
    _ensure()
    with session() as s:
        cfg = s.get(AutoGrowthConfig, channel_id) or AutoGrowthConfig(channel_id=channel_id, toggles={}, state={})
        t = dict(cfg.toggles or {})
        for k, v in patch.items():
            if k == "enabled" or k in AUTOMATIONS:
                t[k] = None if v is None else bool(v)
        cfg.toggles = t
        cfg.updated_at = now()
        s.add(cfg)
        s.commit()
        ch = s.get(Channel, channel_id)
    return settings(ch)


def _state_update(channel_id: int, **kw: Any) -> dict[str, Any]:
    _ensure()
    with session() as s:
        cfg = s.get(AutoGrowthConfig, channel_id) or AutoGrowthConfig(channel_id=channel_id, toggles={}, state={})
        cfg.state = {**(cfg.state or {}), **kw}
        s.add(cfg)
        s.commit()
        return cfg.state


# ---------------------------------------------------------------- histórico

def log_action(channel_id: int, kind: str, title: str, ref: str = "", data: dict | None = None, status: str = "done",
               body: str = "", link: str = "/piloto-automatico", notify_: bool = True) -> int:
    _ensure()
    with session() as s:
        a = GrowthAction(channel_id=channel_id, kind=kind, ref=str(ref), title=title[:200], data=data or {}, status=status)
        s.add(a)
        s.commit()
        s.refresh(a)
    if notify_:
        notify.push("autopilot", f"🤖 {title}", body, link=link, channel_id=channel_id, key=f"action:{a.id}", phone=False)
    return a.id


def _done(channel_id: int, kind: str, ref: str) -> bool:
    _ensure()
    with session() as s:
        return s.exec(select(GrowthAction.id).where(GrowthAction.channel_id == channel_id, GrowthAction.kind == kind,
                                                    GrowthAction.ref == str(ref))).first() is not None


def _count_since(channel_id: int, kind: str, hours: float) -> int:
    _ensure()
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    with session() as s:
        return int(s.exec(select(func.count()).select_from(GrowthAction).where(
            GrowthAction.channel_id == channel_id, GrowthAction.kind == kind, GrowthAction.created_at >= since,
            GrowthAction.status != "failed")).one())


def actions(channel_id: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
    _ensure()
    with session() as s:
        q = select(GrowthAction)
        if channel_id:
            q = q.where(GrowthAction.channel_id == channel_id)
        rows = s.exec(q.order_by(GrowthAction.id.desc()).limit(max(1, min(limit, 300)))).all()
    return [{"id": a.id, "channel_id": a.channel_id, "kind": a.kind, "ref": a.ref, "title": a.title, "data": a.data,
             "status": a.status, "created_at": _utc(a.created_at).isoformat()} for a in rows]


# ---------------------------------------------------------------- estouros e fracassos

def _learning_breakouts() -> list[dict[str, Any]]:
    try:
        from . import learning  # type: ignore[attr-defined]
        r = learning.breakouts(hours=48)
        return [x for x in (r or []) if isinstance(x, dict)]
    except Exception as e:  # noqa: BLE001
        log.debug("learning.breakouts indisponível: %s", e)
        return []


def performance(channel_id: int) -> dict[str, list[dict[str, Any]]]:
    """Estouros (≥ 2,5× a mediana na mesma idade, até 7 dias) e fracassos claros (≤ 30% da mediana em 48 h)."""
    from .posting_times import early_views
    rows = early_views(channel_id, 60)
    out: dict[str, list[dict[str, Any]]] = {"breakouts": [], "flops": []}
    for short in (True, False):
        grp = [r for r in rows if r["short"] == short]
        for r in grp:
            if r["age_hours"] > 24 * 7:
                continue
            h = 48 if r["age_hours"] >= 48 else 24 if r["age_hours"] >= 24 else None  # antes de 24 h: só o modelo (6 h é ruído)
            mine = r.get(f"v{h}") if h else None
            base = [x[f"v{h}"] for x in grp if x is not r and x.get(f"v{h}") is not None] if h else []
            if mine is None or len(base) < MIN_BASE:
                continue
            med = statistics.median(base)
            ratio = mine / med if med else 0
            item = {**r, "at_hours": h, "at_views": mine, "median": round(med), "ratio": round(ratio, 1)}
            if ratio >= BREAKOUT_X and mine >= 150:
                out["breakouts"].append(item)
            elif h == 48 and med >= 50 and ratio <= FLOP_X:
                out["flops"].append(item)
    # o modelo de aprendizado (se existir) também aponta estouros
    known = {b["publication_id"] for b in out["breakouts"]}
    for b in _learning_breakouts():
        pid = b.get("publication_id") or b.get("pub_id")
        if b.get("channel_id") != channel_id or not pid or pid in known:
            continue
        row = next((r for r in rows if r["publication_id"] == pid), None)
        if row and (b.get("status") or b.get("kind")) == "breakout" and (b.get("views") or 0) >= 150:
            out["breakouts"].append({**row, "ratio": b.get("x_normal"), "median": b.get("expected_now"),
                                     "at_hours": round(b.get("age_h") or row["age_hours"]), "at_views": b.get("views"),
                                     "proj_7d": b.get("proj_7d"), "source": "modelo"})
    return out


def _alert_perf(ch: Channel, perf: dict[str, list[dict[str, Any]]]) -> None:
    for b in perf["breakouts"]:
        notify.push("breakout", f"🚀 Estourando · {ch.name}",
                    f"{clean(b['title'])}\n{b['at_views'] or b['views']} views" + (f" em {b['at_hours']} h" if b.get("at_hours") else "")
                    + (f" — {b['ratio']}× a mediana do canal" if b.get("ratio") else ""),
                    link=b.get("url") or "/metricas", channel_id=ch.id, key=f"breakout:{b['publication_id']}",
                    tags=["rocket"], priority=4)
    for f in perf["flops"]:
        notify.push("flop", f"📉 Abaixo do esperado · {ch.name}",
                    f"{clean(f['title'])}\n{f['at_views']} views em 48 h (mediana do canal: {f['median']})",
                    link="/metricas", channel_id=ch.id, key=f"flop:{f['publication_id']}", phone=False)


# ---------------------------------------------------------------- ações

def _busy(channel_id: int, kind: str) -> list[Job]:
    with session() as s:
        return s.exec(select(Job).where(Job.channel_id == channel_id, Job.kind == kind,
                                        Job.status.in_(("queued", "running")))).all()


def act_followups(ch: Channel, perf: dict[str, list[dict[str, Any]]]) -> None:
    for b in perf["breakouts"]:
        ref = str(b["publication_id"])
        if _done(ch.id, "followup", ref) or _count_since(ch.id, "followup", 24 * 7) >= LIMITS["followups_per_week"]:
            continue
        t = clean(b["title"])
        seed = (f"CONTINUAÇÃO de um vídeo do canal que estourou: “{t}” ({b.get('ratio') or '?'}× a mediana). "
                "Proponha a próxima pergunta que o público vai querer responder depois desse vídeo — mesmo tema, "
                "OUTRO ângulo, estrutura e título diferentes (não é um remake). Fatos verificáveis.")
        j = enqueue("discover_ideas", title=f"Continuação do vídeo que estourou: {t[:50]}", channel_id=ch.id,
                    payload={"count": 2, "seed": seed, "format": "short"})
        log_action(ch.id, "followup", f"Pauta de continuação · {t[:60]}", ref,
                   {"job_id": j.id, "ratio": b.get("ratio"), "views": b.get("views")},
                   body=f"“{t}” está {b.get('ratio') or 'bem'}× acima da mediana: 2 pautas de continuação na fila.", link="/pautas")


def act_long_version(ch: Channel) -> None:
    if "long" not in (ch.formats or []):
        return
    if _count_since(ch.id, "long", 24 * 7) >= LIMITS["long_per_week"] or _busy(ch.id, "champion_long"):
        return
    from .longform import champions
    for c in champions(ch.id, 8):
        if not c.get("champion") or c.get("long_status") or c.get("confidence") == "baixa":
            continue
        if _done(ch.id, "long", c["key"]):
            continue
        j = enqueue("champion_long", title=f"Short campeão → vídeo longo: {c['title'][:60]}", channel_id=ch.id,
                    payload={"key": c["key"]})
        log_action(ch.id, "long", f"Short campeão → longo · {c['title'][:60]}", c["key"],
                   {"job_id": j.id, "score": c.get("score"), "views": c.get("views")},
                   body="Roteiro longo em capítulos sendo escrito — revise em Roteiros antes de renderizar.", link="/roteiros")
        return


def act_seed_comments(ch: Channel) -> None:
    from .community import _account, can_write
    if ch.seed_comment_off or not can_write(_account(ch.id)):
        return
    t0 = datetime.now(timezone.utc)
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.channel_id == ch.id, Publication.status == "published",
                                                Publication.platform == "youtube",
                                                Publication.published_at >= t0 - timedelta(hours=72))).all()
        seeds = {c.video_id: c for c in s.exec(select(Comment).where(Comment.channel_id == ch.id, Comment.status == "seed")).all()}
        waiting = {j.ref_id for j in s.exec(select(Job).where(Job.kind == "seed_comment", Job.channel_id == ch.id,
                                                             Job.status.in_(("queued", "running")))).all()}
    for p in pubs:
        live = _utc(p.published_at)
        if not p.external_id or p.privacy != "public" or not live or t0 - live < timedelta(minutes=45):
            continue
        c = seeds.get(p.external_id)
        if c:
            if not c.pinned and not notify.exists(f"pin:{c.id}"):
                from .community import pin_url
                notify.push("comments", f"📌 Fixe o comentário · {ch.name}", f"{clean(p.title)}\n{c.text}",
                            link=pin_url(p.external_id, c.yt_id), channel_id=ch.id, key=f"pin:{c.id}", phone=False)
            continue
        if p.id in waiting or _done(ch.id, "seed", str(p.id)):
            continue
        j = enqueue("seed_comment", title=f"Comentário do canal: {clean(p.title)[:60]}", channel_id=ch.id, ref_id=p.id)
        log_action(ch.id, "seed", f"Comentário que puxa conversa · {clean(p.title)[:60]}", str(p.id), {"job_id": j.id},
                   body="O vídeo estava sem o comentário do canal — postando agora.", notify_=False)


def _new_title(ch: Channel, pub: Publication, sc: Script | None) -> str:
    from . import llm
    from .content import channel_brief, existing_titles
    narr = " ".join(x.get("text", "") for x in (sc.scenes or []))[:1500] if sc else (pub.description or "")[:1000]
    champs = []
    try:
        from .viral import champions as _champs
        champs = _champs(ch.id, 4)
    except Exception:  # noqa: BLE001
        pass
    recent = [t for t in existing_titles(ch.id, 20)][:15]
    data = llm.complete_json(f"""{channel_brief(ch)}

Este vídeo do canal foi MUITO pior que a mediana nas primeiras 48 h. Título atual: "{clean(pub.title)}"
Narração: {narr}
Campeões do canal (o que o público clica): {'; '.join(c['title'] for c in champs) or '(nenhum)'}
Títulos recentes (não repita a estrutura): {'; '.join(recent)}

Escreva UM título novo, num estilo DIFERENTE do atual, 100% fiel ao que o vídeo entrega (nada inventado),
com o termo principal no começo e uma lacuna de curiosidade honesta. Máx. 55 caracteres. Sem hashtags.
Responda JSON: {{"title": "...", "why": "..."}}""", temperature=0.8)
    t = clean(str((data or {}).get("title") or ""))[:90]
    return t if t and t.lower() != clean(pub.title).lower() else ""


def retitle_published(video_id: int | None, title: str, reason: str = "", publication_id: int | None = None,
                      channel_id: int | None = None) -> dict[str, Any]:
    """Troca o título do vídeo publicado no YouTube (mantém descrição/tags) e registra o antes/depois."""
    from .community import YT_DAILY_QUOTA, YT_RESERVE, _account, yt_units_today
    from .publish import _yt_client, _yt_creds
    from . import config
    with session() as s:
        if publication_id:
            pub = s.get(Publication, publication_id)
        else:
            pub = s.exec(select(Publication).where(Publication.video_id == video_id, Publication.status == "published",
                                                   Publication.platform == "youtube")).first()
    if not pub or not pub.external_id:
        return {"ok": False, "error": "vídeo não publicado no YouTube"}
    quota = int(config.get("yt_daily_quota") or YT_DAILY_QUOTA)
    if yt_units_today() + 60 > quota - YT_RESERVE:
        return {"ok": False, "error": "cota do YouTube quase no fim hoje"}
    acc = _account(pub.channel_id)
    if not acc or not acc.credentials:
        return {"ok": False, "error": "canal sem login do YouTube"}
    try:
        yt = _yt_client(_yt_creds(acc))
        item = (yt.videos().list(part="snippet", id=pub.external_id).execute().get("items") or [None])[0]
        if not item:
            return {"ok": False, "error": "vídeo não encontrado no YouTube"}
        sn = item["snippet"]
        before = sn["title"]
        new = clean(title)[:95]
        if "#shorts" in before.lower() and len(new) <= 86:
            new = f"{new} #Shorts"
        body = {"id": pub.external_id, "snippet": {"title": new, "categoryId": sn.get("categoryId", "27"),
                                                   "description": sn.get("description", ""), "tags": sn.get("tags", []),
                                                   "defaultLanguage": sn.get("defaultLanguage", "pt-BR")}}
        yt.videos().update(part="snippet", body=body).execute()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)[:300]}
    with session() as s:
        p = s.get(Publication, pub.id)
        p.title = new
        s.add(p)
        s.commit()
    from .posting_times import early_views
    row = next((r for r in early_views(pub.channel_id, 90) if r["publication_id"] == pub.id), {})
    aid = log_action(pub.channel_id, "retitle", f"Título trocado · {clean(new)[:60]}", str(pub.id),
                     {"before": before, "after": new, "reason": reason, "views_before": row.get("views", 0),
                      "age_hours_before": row.get("age_hours"), "at": datetime.now(timezone.utc).isoformat()},
                     status="testing", body=f"Antes: {clean(before)}\nDepois: {clean(new)}\n{reason}".strip(),
                     link=pub.url or "/metricas")
    return {"ok": True, "before": before, "after": new, "action_id": aid}


def act_retitle(ch: Channel, perf: dict[str, list[dict[str, Any]]]) -> None:
    for f in perf["flops"]:
        if _count_since(ch.id, "retitle", 24) >= LIMITS["retitle_per_day"]:
            return
        ref = str(f["publication_id"])
        if _done(ch.id, "retitle", ref) or not f.get("video_id"):  # só vídeos feitos aqui; uma vez por vídeo
            continue
        with session() as s:
            pub = s.get(Publication, f["publication_id"])
            v = s.get(Video, pub.video_id) if pub and pub.video_id else None
            sc = s.get(Script, v.script_id) if v else None
        if not pub:
            continue
        try:
            title = _new_title(ch, pub, sc)
        except Exception as e:  # noqa: BLE001
            log.info("título novo: %s", e)
            return
        if not title:
            continue
        r = retitle_published(None, title, f"fracasso claro: {f['at_views']} views em 48 h vs mediana {f['median']}",
                              publication_id=pub.id)
        if not r.get("ok"):
            log_action(ch.id, "retitle", f"Troca de título não feita · {clean(pub.title)[:50]}", ref, {"error": r.get("error")},
                       status="failed", notify_=False)
        return


def evaluate_retitles() -> None:
    """48 h depois da troca: compara views/hora antes × depois e registra o resultado."""
    from .posting_times import early_views
    _ensure()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    with session() as s:
        rows = s.exec(select(GrowthAction).where(GrowthAction.kind == "retitle", GrowthAction.status == "testing",
                                                 GrowthAction.created_at <= cutoff)).all()
    for a in rows:
        d = dict(a.data or {})
        cur = next((r for r in early_views(a.channel_id, 120) if str(r["publication_id"]) == a.ref), None)
        if not cur:
            continue
        before_rate = (d.get("views_before") or 0) / max(1.0, d.get("age_hours_before") or 48)
        hours_after = max(1.0, cur["age_hours"] - (d.get("age_hours_before") or 48))
        after_rate = max(0, cur["views"] - (d.get("views_before") or 0)) / hours_after
        # Shorts perdem ritmo com a idade: "melhorou" = ritmo depois ≥ 60% do de antes (sem a troca cairia bem mais)
        ratio = after_rate / before_rate if before_rate else (2.0 if after_rate else 0)
        status = "better" if ratio >= 0.6 else "neutral" if ratio >= 0.3 else "worse"
        d.update(views_after=cur["views"], rate_before=round(before_rate, 2), rate_after=round(after_rate, 2),
                 ratio=round(ratio, 2))
        with session() as s:
            db = s.get(GrowthAction, a.id)
            db.status, db.data, db.updated_at = status, d, now()
            s.add(db)
            s.commit()
        label = {"better": "ajudou", "neutral": "pouco efeito", "worse": "não ajudou"}[status]
        notify.push("autopilot", f"🧪 Teste de título: {label}",
                    f"{clean(d.get('after', ''))}\n{d['rate_before']} → {d['rate_after']} views/h", link="/piloto-automatico",
                    channel_id=a.channel_id, key=f"retitle-result:{a.id}", phone=False)


def act_trend_stock(ch: Channel) -> None:
    from . import focus, radar
    snap = radar.snapshot(ch.id)
    try:
        age_h = (datetime.now(timezone.utc) - datetime.fromisoformat(snap["at"])).total_seconds() / 3600 if snap.get("at") else 999
    except ValueError:
        age_h = 999
    if age_h > 30 and focus.radar_today(ch) and not _busy(ch.id, "trend_radar") and _count_since(ch.id, "trend_radar", 20) == 0:
        j = enqueue("trend_radar", title=f"Radar de tendências: {ch.name}", channel_id=ch.id)
        log_action(ch.id, "trend_radar", f"Radar de tendências atualizado · {ch.name}", "", {"job_id": j.id},
                   body="O radar estava com mais de 30 h — buscando o que está subindo agora.", link="/tendencias", notify_=False)
    left = LIMITS["trend_approve_per_day"] - _count_since(ch.id, "trend_approve", 24)
    if left <= 0:
        return
    since = datetime.now(timezone.utc) - timedelta(hours=72)
    with session() as s:
        cands = s.exec(select(Idea).where(Idea.channel_id == ch.id, Idea.origin == "trend", Idea.status == "new",
                                          Idea.fact_status == "verified", Idea.created_at >= since)
                       .order_by(Idea.score.desc())).all()
    for i in cands:
        if left <= 0:
            break
        urgent = any(str(t).startswith("urgência: alta") for t in (i.tags or []))
        if not urgent or (i.score or 0) < ch.min_score_to_produce - 10:
            continue
        with session() as s:
            db = s.get(Idea, i.id)
            db.status = "approved"
            s.add(db)
            s.commit()
        left -= 1
        log_action(ch.id, "trend_approve", f"Pauta de tendência aprovada · {i.title[:60]}", str(i.id), {"score": i.score},
                   body="Assunto em alta e fatos checados: entra na frente da fila do piloto automático.", link="/pautas")


def act_posting_times(ch: Channel) -> None:
    from . import posting_times
    if posting_times.settings(ch)["mode"] == "auto" or _done(ch.id, "posting_times", "auto"):
        return
    r = posting_times.suggest(ch.id)
    if not r.get("uses_data") or r.get("samples", 0) < 8 or not r.get("slots"):
        return
    with session() as s:
        db = s.get(Channel, ch.id)
        db.schedule = {**(db.schedule or {}), "mode": "auto"}
        s.add(db)
        s.commit()
    log_action(ch.id, "posting_times", f"Horários automáticos ligados · {ch.name}", "auto",
               {"slots": r["slots"], "samples": r["samples"]},
               body=f"{r['samples']} Shorts medidos: os horários agora seguem os dados ({', '.join(r['slots'])}). "
                    "Volte para fixos em Canais → Agenda se preferir.", link=f"/canais/{ch.id}")


# ---------------------------------------------------------------- marcos do YPP

def check_milestones(ch: Channel) -> None:
    stats = ch.stats or {}
    ypp = stats.get("ypp") or {}
    vals = {"subs": (int(stats.get("subscribers") or 0), SUBS_MARKS, "inscritos"),
            "shorts": (int(ypp.get("shorts_views_90d") or 0), SHORTS_MARKS, "views qualificadas de Shorts (90 dias)"),
            "hours": (float(ypp.get("hours_12m") or 0), HOURS_MARKS, "horas assistidas (12 meses)")}
    st = get_config(ch.id).state or {}
    seen = dict(st.get("marks") or {})
    first = not st.get("marks_init")
    for k, (val, marks, label) in vals.items():
        top = max([m for m in marks if val >= m], default=0)
        if top > int(seen.get(k) or 0):
            if not first:
                fmt = f"{top:,}".replace(",", ".")
                notify.push("ypp", f"🏆 {ch.name}: {fmt} {label}", f"Agora: {f'{val:,.0f}'.replace(',', '.')}. "
                            "Acompanhe o caminho até a monetização em Crescimento.", link=f"/canais/{ch.id}",
                            channel_id=ch.id, key=f"ypp:{ch.id}:{k}:{top}", tags=["trophy"], priority=4)
            seen[k] = top
    _state_update(ch.id, marks=seen, marks_init=True)


# ---------------------------------------------------------------- rodada

def tick_channel(ch: Channel) -> dict[str, Any]:
    from . import focus
    cfg = settings(ch)
    done: list[str] = []
    try:
        perf = performance(ch.id)
        _alert_perf(ch, perf)
    except Exception as e:  # noqa: BLE001
        log.warning("autogrowth %s desempenho: %s", ch.name, e)
        perf = {"breakouts": [], "flops": []}
    try:
        check_milestones(ch)
    except Exception as e:  # noqa: BLE001
        log.info("marcos %s: %s", ch.name, e)
    if not cfg["enabled"] or focus.paused(ch):
        return {"channel_id": ch.id, "active": False}
    steps = [("posting_times", lambda: act_posting_times(ch)), ("breakouts", lambda: act_followups(ch, perf)),
             ("long_version", lambda: act_long_version(ch)), ("seed_comments", lambda: act_seed_comments(ch)),
             ("retitle_flops", lambda: act_retitle(ch, perf)), ("trend_stock", lambda: act_trend_stock(ch))]
    for key, fn in steps:
        if not cfg.get(key):
            continue
        try:
            fn()
            done.append(key)
        except Exception as e:  # noqa: BLE001
            log.warning("autogrowth %s/%s: %s", ch.name, key, e)
    _state_update(ch.id, last_tick=datetime.now(timezone.utc).isoformat(),
                  last_perf={"breakouts": len(perf["breakouts"]), "flops": len(perf["flops"])})
    return {"channel_id": ch.id, "active": True, "ran": done}


def tick() -> list[dict[str, Any]]:
    """Chamado pelo agendador a cada 30 min."""
    if not _lock.acquire(blocking=False):
        return []
    try:
        _ensure()
        with session() as s:
            chans = s.exec(select(Channel).order_by(Channel.id)).all()
        out = [tick_channel(ch) for ch in chans]
        try:
            evaluate_retitles()
        except Exception as e:  # noqa: BLE001
            log.warning("avaliação de títulos: %s", e)
        try:
            notify.scan_jobs(40)
        except Exception as e:  # noqa: BLE001
            log.info("varredura de tarefas: %s", e)
        return out
    finally:
        _lock.release()


def run_async() -> bool:
    if _lock.locked():
        return False
    threading.Thread(target=tick, daemon=True, name="autogrowth").start()
    return True


def overview() -> list[dict[str, Any]]:
    _ensure()
    with session() as s:
        chans = s.exec(select(Channel).order_by(Channel.id)).all()
    out = []
    for ch in chans:
        cfg = get_config(ch.id)
        try:
            perf = performance(ch.id)
        except Exception:  # noqa: BLE001
            perf = {"breakouts": [], "flops": []}
        out.append({"channel_id": ch.id, "name": ch.name, "auto_pilot": ch.auto_pilot, "focus": ch.focus,
                    "settings": settings(ch), "last_tick": (cfg.state or {}).get("last_tick"),
                    "breakouts": [{k: b.get(k) for k in ("publication_id", "title", "url", "views", "ratio", "age_hours")}
                                  for b in perf["breakouts"]],
                    "flops": [{k: f.get(k) for k in ("publication_id", "title", "url", "views", "ratio", "median")}
                              for f in perf["flops"]],
                    "week": {k: _count_since(ch.id, k, 24 * 7) for k in ("followup", "long", "seed", "retitle", "trend_approve")}})
    return out
