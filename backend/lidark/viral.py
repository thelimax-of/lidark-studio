"""Laboratório viral pré-post: antes de publicar, uma nota de potencial viral para o roteiro/vídeo pronto.

- Nota = previsão do modelo do canal (learning.predict, quando existir) + checagens objetivas (título, gancho,
  miniatura, duração, ritmo, originalidade, fatos, final que puxa comentário).
- Comparação com os Shorts campeões do canal (longform.champions).
- 3 alternativas de título + texto de miniatura numa única chamada à IA, cada uma com a nota do modelo.
- Aplicar com um clique: atualiza o roteiro e as publicações ainda agendadas (o vídeo no YouTube só muda se pedir).

Variedade (política anti produção em massa): as alternativas são pedidas em estilos DIFERENTES entre si e dos
títulos recentes do canal — nada de forçar todos os vídeos na mesma fórmula do campeão.
"""
from __future__ import annotations

import logging
import re
import statistics
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel, select

from . import llm
from .db import session
from .models import Channel, Publication, Script, Video, now

log = logging.getLogger("lidark.viral")


class ViralReport(SQLModel, table=True):
    """Última análise do laboratório viral de um roteiro (sugestões da IA e o que foi aplicado)."""
    script_id: int = Field(primary_key=True)
    channel_id: int = Field(default=0, index=True)
    suggestions: list = Field(default_factory=list, sa_column=Column(JSON))
    applied: list = Field(default_factory=list, sa_column=Column(JSON))  # [{at, field, before, after}]
    updated_at: datetime = Field(default_factory=now)


_ready = False


def _ensure() -> None:
    global _ready
    if not _ready:
        from .db import engine
        ViralReport.__table__.create(engine, checkfirst=True)
        _ready = True


# ---------------------------------------------------------------- modelo de aprendizado (outro módulo, opcional)

def predict(channel_id: int, title: str, hook: str = "", fmt: str = "short") -> dict[str, Any] | None:
    try:
        from . import learning  # type: ignore[attr-defined]
        r = learning.predict(channel_id, title, hook=hook, fmt=fmt)
        return r if isinstance(r, dict) else None
    except Exception as e:  # noqa: BLE001
        log.debug("learning.predict indisponível: %s", e)
        return None


def learning_context(channel_id: int, purpose: str) -> str:
    try:
        from . import learning  # type: ignore[attr-defined]
        return str(learning.prompt_context(channel_id, purpose) or "")
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------- utilidades

def clean_title(t: str) -> str:
    return re.sub(r"\s*#shorts\b", "", t or "", flags=re.I).strip()


def resolve(script_id: int | None = None, video_id: int | None = None) -> tuple[Script, Video | None, Channel]:
    with session() as s:
        v = s.get(Video, video_id) if video_id else None
        sid = v.script_id if v else script_id
        sc = s.get(Script, sid) if sid else None
        if not sc:
            raise ValueError("roteiro não encontrado")
        if v is None:
            v = s.exec(select(Video).where(Video.script_id == sc.id).order_by(Video.id.desc())).first()
        ch = s.get(Channel, sc.channel_id)
    return sc, v, ch


CURIOSITY = ("por que", "porque", "como", "o que", "segredo", "ninguém", "nunca", "verdade", "real", "mistério",
             "escondid", "proibid", "esquecid", "ninguem", "estranh", "impossível", "maior", "menor", "único",
             "primeiro", "último", "quase", "quem", "onde", "qual")
WEAK_OPENERS = ("olá", "oi ", "fala galera", "neste vídeo", "nesse vídeo", "hoje eu", "hoje vamos", "hoje vou",
                "bem-vindo", "bem vindo", "você sabia", "voce sabia", "e aí")
TENSION = ("mas", "porém", "só que", "ninguém", "nunca", "até que", "de repente", "o problema", "errado", "mentira",
           "?", "segredo", "proibid")


def _words(t: str) -> list[str]:
    return re.findall(r"[\wÀ-ú]+", t or "")


def _has_number(t: str) -> bool:
    return bool(re.search(r"\d", t or ""))


def _caps_ratio(t: str) -> float:
    letters = [c for c in (t or "") if c.isalpha()]
    return sum(c.isupper() for c in letters) / max(1, len(letters))


def _seconds(sc: Script, v: Video | None) -> float:
    if v and v.duration:
        return float(v.duration)
    sec = (sc.variety or {}).get("seconds")
    if sec:
        return float(sec)
    from .content import count_words
    return count_words(sc.scenes or []) / 2.6  # ~2,6 palavras/s na narração


def _title_features(t: str) -> dict[str, Any]:
    t = clean_title(t)
    low = t.lower()
    return {"len": len(t), "number": _has_number(t), "question": "?" in t,
            "curiosity": any(w in low for w in CURIOSITY)}


# ---------------------------------------------------------------- campeões do canal

def champions(channel_id: int, n: int = 5) -> list[dict[str, Any]]:
    try:
        from .longform import champions as _ch
        rows = _ch(channel_id, 12)
    except Exception as e:  # noqa: BLE001
        log.info("campeões: %s", e)
        return []
    best = [r for r in rows if r.get("champion")] or rows
    return [{"title": r["title"], "views": r["views"], "retention": r.get("retention"), "score": r.get("score"),
             "url": r.get("url"), "thumbnail": r.get("thumbnail"), "reasons": r.get("reasons", [])} for r in best[:n]]


def _best_duration(channel_id: int, fmt: str) -> tuple[float, float] | None:
    """Faixa de duração (s) dos Shorts que mais rendem no canal: mediana das views por faixa de 10 s."""
    if fmt != "short":
        return None
    try:
        from .analytics import performance_table
        rows = [r for r in performance_table(channel_id) if 0 < (r.get("duration") or 0) <= 180 and r["views"] > 0]
    except Exception:  # noqa: BLE001
        return None
    if len(rows) < 8:
        return None
    bands: dict[int, list[int]] = {}
    for r in rows:
        bands.setdefault(int(r["duration"] // 10), []).append(r["views"])
    ok = {b: statistics.median(v) for b, v in bands.items() if len(v) >= 3}
    if len(ok) < 2:
        return None
    b = max(ok, key=ok.get)
    return b * 10.0, b * 10.0 + 10


# ---------------------------------------------------------------- checagens

def checks(sc: Script, v: Video | None, ch: Channel) -> list[dict[str, Any]]:
    fmt = sc.format or "short"
    title = clean_title(sc.title)
    tf = _title_features(title)
    scenes = sc.scenes or []
    first = (scenes[0].get("text", "") if scenes else "") or sc.hook or ""
    hook = (sc.hook or first).strip()
    last = (scenes[-1].get("text", "") if scenes else "")
    out: list[dict[str, Any]] = []

    def add(cid: str, ok: bool, label: str, detail: str, fix: str, weight: int = 10, field: str = "") -> None:
        out.append({"id": cid, "ok": bool(ok), "label": label, "detail": detail, "fix": "" if ok else fix,
                    "weight": weight, "field": field})

    max_len = 55 if fmt == "short" else 65
    add("title_len", tf["len"] <= max_len, "Título curto e direto", f"{tf['len']} caracteres (ideal ≤ {max_len})",
        "Corte o título: a parte que importa precisa caber antes do corte no celular.", 12, "title")
    add("title_hook", tf["number"] or tf["question"] or tf["curiosity"], "Título com gatilho de curiosidade",
        "tem número, pergunta ou lacuna de curiosidade" if (tf["number"] or tf["question"] or tf["curiosity"])
        else "não tem número, pergunta nem lacuna de curiosidade",
        "Abra uma lacuna honesta (por que / como / o que ninguém conta) ou traga um número real do vídeo.", 12, "title")
    caps = _caps_ratio(title)
    add("title_caps", caps < 0.5, "Sem exagero de MAIÚSCULAS", f"{round(caps * 100)}% em maiúsculas",
        "Deixe só 1-2 palavras em maiúsculas; título todo em caixa alta parece spam.", 5, "title")
    hw = len(_words(first))
    add("hook_fast", hw <= (18 if fmt == "short" else 30), "Gancho entra rápido",
        f"1ª fala com {hw} palavras", "Encurte a primeira frase: a promessa do vídeo nos primeiros 2 segundos.", 12, "hook")
    low = hook.lower()
    weak = next((w for w in WEAK_OPENERS if low.startswith(w)), None)
    add("hook_opener", not weak, "Sem abertura batida", f"começa com “{weak.strip()}”" if weak else "abertura própria",
        "Comece direto no fato mais estranho ou na pergunta — sem apresentação.", 10, "hook")
    add("hook_tension", any(w in low for w in TENSION) or _has_number(hook), "Gancho com tensão",
        "tem contraste, pergunta ou número" if any(w in low for w in TENSION) or _has_number(hook)
        else "o gancho só afirma, sem conflito", "Coloque um contraste (“mas…”, “ninguém percebeu…”) ou um número real.",
        10, "hook")
    tt = (sc.thumbnail_text or "").strip()
    tw = len(_words(tt))
    add("thumb_text", 1 <= tw <= 4 and tt.lower() != title.lower(), "Texto da miniatura curto",
        f"“{tt}” ({tw} palavras)" if tt else "sem texto de miniatura",
        "Use 2-4 palavras que completam o título (não repita o título).", 8, "thumbnail_text")
    sec = _seconds(sc, v)
    band = _best_duration(ch.id, fmt)
    if fmt == "short":
        if band:
            ok = band[0] - 5 <= sec <= band[1] + 5
            add("duration", ok, "Duração na faixa que mais rende", f"{sec:.0f} s · melhor faixa do canal: {band[0]:.0f}-{band[1]:.0f} s",
                "Ajuste a duração para perto da faixa campeã (corte cenas fracas ou aprofunde).", 8)
        else:
            add("duration", sec <= 60, "Short enxuto", f"{sec:.0f} s",
                "Shorts mais curtos são vistos até o fim (e de novo) com mais frequência — corte o que não for essencial.", 8)
    if scenes:
        wps = statistics.mean(len(_words(x.get("text", ""))) for x in scenes)
        lim = 26 if fmt == "short" else 70
        add("pace", wps <= lim, "Ritmo de cenas", f"{wps:.0f} palavras por cena (ideal ≤ {lim})",
            "Quebre cenas longas: troca de imagem a cada frase segura a retenção.", 6)
    try:
        from .variety import repetition_problems
        probs = repetition_problems(ch.id, sc.title, sc.hook, scenes, exclude_id=sc.id)
    except Exception:  # noqa: BLE001
        probs = []
    add("original", not probs, "Diferente dos vídeos recentes", "; ".join(probs[:2]) if probs else "nada repetido",
        "Mude o ângulo/título/gancho — vídeos parecidos entre si são o que o YouTube chama de conteúdo inautêntico.", 10)
    unresolved = len(((sc.claims or {}).get("unresolved")) or [])
    add("facts", unresolved == 0, "Fatos confirmados", f"{unresolved} afirmação(ões) sem fonte" if unresolved else "tudo checado",
        "Corrija ou remova as afirmações sem fonte antes de publicar.", 8)
    ends = "?" in last[-120:] or any(w in last.lower() for w in ("comente", "comenta", "conta aqui", "qual você", "você acha"))
    add("ending", ends, "Final puxa comentário", "termina com pergunta/convite" if ends else "o final não pede resposta",
        "Feche com uma pergunta específica sobre o tema (gera comentários e o algoritmo distribui mais).", 6)
    return out


def _heuristic_score(items: list[dict[str, Any]]) -> int:
    tot = sum(i["weight"] for i in items) or 1
    return round(100 * sum(i["weight"] for i in items if i["ok"]) / tot)


def _blend(pred: dict[str, Any] | None, heur: int) -> int:
    try:
        p = float((pred or {}).get("score"))
    except (TypeError, ValueError):
        return heur
    if not 0 <= p <= 100:
        return heur
    return round(0.6 * p + 0.4 * heur)


def compare(title: str, champs: list[dict[str, Any]]) -> dict[str, Any]:
    if not champs:
        return {}
    feats = [_title_features(c["title"]) for c in champs]
    me = _title_features(title)
    return {
        "title_len": {"mine": me["len"], "champions": round(statistics.mean(f["len"] for f in feats))},
        "number": {"mine": me["number"], "champions": round(100 * sum(f["number"] for f in feats) / len(feats))},
        "question": {"mine": me["question"], "champions": round(100 * sum(f["question"] for f in feats) / len(feats))},
        "curiosity": {"mine": me["curiosity"], "champions": round(100 * sum(f["curiosity"] for f in feats) / len(feats))},
    }


def _report_row(script_id: int) -> ViralReport | None:
    _ensure()
    with session() as s:
        return s.get(ViralReport, script_id)


def analyze(script_id: int | None = None, video_id: int | None = None) -> dict[str, Any]:
    sc, v, ch = resolve(script_id, video_id)
    fmt = sc.format or "short"
    items = checks(sc, v, ch)
    heur = _heuristic_score(items)
    pred = predict(ch.id, clean_title(sc.title), sc.hook or "", fmt)
    champs = champions(ch.id)
    rep = _report_row(sc.id)
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.video_id == v.id)).all() if v else []
    return {
        "script": {"id": sc.id, "title": sc.title, "hook": sc.hook, "thumbnail_text": sc.thumbnail_text, "format": fmt,
                   "status": sc.status, "seconds": round(_seconds(sc, v)), "channel_id": ch.id, "channel": ch.name},
        "video": {"id": v.id, "status": v.status, "thumbnail_path": v.thumbnail_path, "path": v.path} if v else None,
        "publications": [{"id": p.id, "status": p.status, "title": p.title, "url": p.url,
                          "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None} for p in pubs],
        "score": _blend(pred, heur), "heuristic": heur, "prediction": pred,
        "checks": items, "checklist": [i for i in items if not i["ok"]],
        "champions": champs, "compare": compare(sc.title, champs),
        "suggestions": rep.suggestions if rep else [], "applied": rep.applied if rep else [],
        "hook_editable": not v or v.status in ("failed",),
    }


# ---------------------------------------------------------------- alternativas (1 chamada de IA)

def suggest(script_id: int | None = None, video_id: int | None = None) -> list[dict[str, Any]]:
    from .content import channel_brief, existing_titles
    sc, v, ch = resolve(script_id, video_id)
    fmt = sc.format or "short"
    items = checks(sc, v, ch)
    fails = "\n".join(f"- {i['label']}: {i['detail']} → {i['fix']}" for i in items if not i["ok"]) or "- (nenhum)"
    champs = champions(ch.id)
    champ_txt = "\n".join(f"- “{c['title']}” — {c['views']} views" + (f", retenção {c['retention']:.0f}%" if c.get("retention") else "")
                          for c in champs) or "(o canal ainda não tem campeões)"
    recent = [t for t in existing_titles(ch.id, 30) if t != sc.title][:20]
    narr = " ".join(x.get("text", "") for x in (sc.scenes or []))[:1800]
    extra = learning_context(ch.id, "titles")
    data = llm.complete_json(f"""{channel_brief(ch)}

VÍDEO PRONTO PARA PUBLICAR ({'Short vertical' if fmt == 'short' else 'vídeo longo'}):
TÍTULO ATUAL: {clean_title(sc.title)}
TEXTO ATUAL DA MINIATURA: {sc.thumbnail_text or '(nenhum)'}
GANCHO (1ª fala): {sc.hook}
NARRAÇÃO: {narr}

PROBLEMAS ENCONTRADOS:
{fails}

SHORTS CAMPEÕES DO CANAL (o que o público deste canal já provou que clica — inspire-se no PORQUÊ, não copie a fórmula):
{champ_txt}

TÍTULOS RECENTES DO CANAL (não repita estrutura nem palavras de abertura):
{chr(10).join('- ' + t for t in recent) or '(nenhum)'}
{extra}

Crie 3 alternativas de TÍTULO + TEXTO DE MINIATURA para ESTE vídeo, cada uma num ESTILO DIFERENTE
(ex.: pergunta, número real, contraste/revelação, personagem) — diferentes entre si e dos títulos recentes.
Regras: 100% fiel ao conteúdo da narração (nada que o vídeo não entregue, nenhum número inventado);
título ≤ {55 if fmt == 'short' else 65} caracteres com o termo principal no começo; miniatura com 2-4 palavras em
MAIÚSCULAS que COMPLETAM o título (não repetem). Se o gancho tiver problema, sugira um gancho melhor (1 frase, ≤ 16 palavras).
Responda JSON: {{"options": [{{"title": "...", "thumbnail_text": "...", "style": "pergunta|numero|contraste|personagem|outro",
"why": "por que deve render mais (1 frase)"}}], "hook": "gancho sugerido ou vazio"}}""", temperature=0.9)
    opts = []
    for o in (data.get("options") or [])[:3] if isinstance(data, dict) else []:
        t = str(o.get("title") or "").strip()[:100]
        if not t:
            continue
        p = predict(ch.id, t, sc.hook or "", fmt)
        opts.append({"title": t, "thumbnail_text": str(o.get("thumbnail_text") or "").strip()[:40],
                     "style": str(o.get("style") or ""), "why": str(o.get("why") or "")[:300],
                     "prediction": p, "features": _title_features(t)})
    hook = str((data or {}).get("hook") or "").strip()[:200] if isinstance(data, dict) else ""
    if hook:
        opts.append({"hook": hook, "why": "gancho mais direto", "prediction": predict(ch.id, clean_title(sc.title), hook, fmt)})
    _ensure()
    with session() as s:
        rep = s.get(ViralReport, sc.id) or ViralReport(script_id=sc.id, channel_id=ch.id)
        rep.suggestions = opts
        rep.updated_at = now()
        s.add(rep)
        s.commit()
    return opts


# ---------------------------------------------------------------- aplicar com um clique

def apply(script_id: int, title: str | None = None, thumbnail_text: str | None = None, hook: str | None = None,
          rethumb: bool = True, youtube: bool = False) -> dict[str, Any]:
    """Atualiza o roteiro e as publicações agendadas. Miniatura já renderizada é refeita com o texto novo
    (Estúdio de miniaturas). youtube=True também troca o título de um vídeo já publicado (registrado no piloto)."""
    from .jobs import enqueue
    sc, v, ch = resolve(script_id)
    changes: list[dict[str, Any]] = []
    at = datetime.now(timezone.utc).isoformat()
    with session() as s:
        db = s.get(Script, sc.id)
        if title and clean_title(title) != clean_title(db.title):
            new = clean_title(title)[:100]
            if re.search(r"#shorts\b", db.title or "", re.I):
                new = f"{new} #Shorts"
            changes.append({"at": at, "field": "title", "before": db.title, "after": new})
            db.title = new
        if thumbnail_text is not None and thumbnail_text.strip() and thumbnail_text.strip() != (db.thumbnail_text or ""):
            changes.append({"at": at, "field": "thumbnail_text", "before": db.thumbnail_text, "after": thumbnail_text.strip()[:40]})
            db.thumbnail_text = thumbnail_text.strip()[:40]
        if hook and hook.strip() != (db.hook or "").strip():
            if v and v.status not in ("failed",):
                raise ValueError("o vídeo já foi renderizado: trocar o gancho exige gerar o vídeo de novo")
            scenes = list(db.scenes or [])
            if scenes and (scenes[0].get("text", "").strip() == (db.hook or "").strip() or not db.hook):
                scenes[0] = {**scenes[0], "text": hook.strip()}
                db.scenes = scenes
            changes.append({"at": at, "field": "hook", "before": db.hook, "after": hook.strip()})
            db.hook = hook.strip()
        if changes:
            db.version += 1
            s.add(db)
        pubs_changed = 0
        if v and any(c["field"] == "title" for c in changes):
            for p in s.exec(select(Publication).where(Publication.video_id == v.id,
                                                      Publication.status.in_(("scheduled", "failed")))).all():
                p.title = db.title
                s.add(p)
                pubs_changed += 1
        s.commit()
        new_title = db.title
    out: dict[str, Any] = {"changes": changes, "publications_updated": pubs_changed}
    if v and rethumb and any(c["field"] == "thumbnail_text" for c in changes) and v.status in ("ready", "review", "published"):
        j = enqueue("thumb_studio", title=f"Miniaturas: {clean_title(new_title)[:60]}", channel_id=ch.id, ref_id=v.id,
                    payload={"texts": [thumbnail_text.strip()], "auto_pick": v.status != "published"})
        out["thumb_job"] = j.id
    if youtube and v and any(c["field"] == "title" for c in changes):
        from .autogrowth import retitle_published
        out["youtube"] = retitle_published(v.id, new_title, reason="laboratório viral (manual)")
    if changes:
        _ensure()
        with session() as s:
            rep = s.get(ViralReport, sc.id) or ViralReport(script_id=sc.id, channel_id=ch.id)
            rep.applied = [*(rep.applied or []), *changes][-30:]
            rep.updated_at = now()
            s.add(rep)
            s.commit()
    return out


def queue(channel_id: int | None = None, limit: int = 30) -> list[dict[str, Any]]:
    """Vídeos/roteiros prontos (ainda não publicados) para passar no laboratório, com a nota rápida (sem IA)."""
    out = []
    with session() as s:
        q = select(Video).where(Video.status.in_(("ready", "review")))
        if channel_id:
            q = q.where(Video.channel_id == channel_id)
        vids = s.exec(q.order_by(Video.id.desc()).limit(limit)).all()
        q2 = select(Script).where(Script.status.in_(("draft", "approved")))
        if channel_id:
            q2 = q2.where(Script.channel_id == channel_id)
        drafts = s.exec(q2.order_by(Script.id.desc()).limit(limit)).all()
    seen = set()
    for v in vids:
        seen.add(v.script_id)
    rows: list[tuple[Script | None, Video | None]] = []
    with session() as s:
        rows += [(s.get(Script, v.script_id), v) for v in vids]
    rows += [(sc, None) for sc in drafts if sc.id not in seen]
    chans: dict[int, Channel] = {}
    for sc, v in rows[:limit]:
        if not sc:
            continue
        if sc.channel_id not in chans:
            with session() as s:
                chans[sc.channel_id] = s.get(Channel, sc.channel_id)
        ch = chans[sc.channel_id]
        try:
            items = checks(sc, v, ch)
        except Exception as e:  # noqa: BLE001
            log.info("checagem %s: %s", sc.id, e)
            continue
        out.append({"script_id": sc.id, "video_id": v.id if v else None, "channel_id": sc.channel_id, "title": sc.title,
                    "format": sc.format, "stage": v.status if v else f"roteiro ({sc.status})",
                    "thumbnail_path": v.thumbnail_path if v else "", "heuristic": _heuristic_score(items),
                    "fails": sum(not i["ok"] for i in items)})
    return out
