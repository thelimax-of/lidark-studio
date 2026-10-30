"""Séries do Modo História (canal dedicado): UMA pauta → TODAS as partes, em ordem, com votação do público.

Ciclo de uma série (arco em data/story/<slug>/series.json, plano em plans/<idea_id>.json):
1. abrir: a pauta-série vira um arco com o plano parte a parte (seasons.py)
2. escrever: a parte k+1 só depois da k (trava "writing"); cada parte usa o plano + a memória REAL das anteriores
   (elenco, lugares, roupa, relógio/cronômetro contínuos, callbacks). Parte com DECISÃO A/B: a seguinte espera a
   votação (publicação + 6-20 h) — votos dos comentários (1 por pessoa, sem o próprio canal) + enquete digitada à mão
3. agendar: as partes entram nos horários do canal ESTRITAMENTE em ordem (nunca duas da mesma série no mesmo horário);
   no máximo 2 séries intercaladas; playlist da série (variety["series"]) e descrições ligando anterior/próxima
4. fim: "FIM DA SÉRIE · próxima: …" e a versão completa (16:9, capítulos = partes) como o longo da semana
tick() roda no agendador (a cada ~20 min) e mantém ~2 séries no cano para os 3 horários/dia nunca ficarem vazios.
"""
from __future__ import annotations

import copy
import logging
import re
import threading
import time
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import select

from ..db import session
from ..jobs import enqueue
from ..models import Channel, Comment, Idea, Job, Publication, Script, Video, now
from . import seasons, writer

log = logging.getLogger("lidark.story.series")
_lock = threading.RLock()
MAX_OPEN = 2           # séries intercaladas no máximo
BUFFER = 3             # partes escritas e ainda não publicadas que o cano tenta manter
MIN_VOTES = 5          # abaixo disso vale o padrão do plano
LONG_EVERY_DAYS = 6.5  # versão completa: no máximo uma por semana


# ================================================================ arcos

def arcs(slug: str) -> list[dict[str, Any]]:
    return [a for a in writer.series(slug).get("arcs") or [] if a.get("series")]


def get_arc(slug: str, arc_id: str) -> dict[str, Any] | None:
    return next((a for a in writer.series(slug).get("arcs") or [] if a.get("id") == arc_id), None)


def update_arc(slug: str, arc_id: str, fn) -> dict[str, Any] | None:
    with _lock:
        d = writer.series(slug)
        for a in d.get("arcs") or []:
            if a.get("id") == arc_id:
                fn(a)
                writer._save_series(slug, d)
                return a
    return None


def open_arc(ch: Channel, idea: Idea) -> dict[str, Any] | None:
    plan = seasons.load_plan(ch.slug, idea.id)
    if not plan:
        return None
    arc_id = f"serie_{idea.id}"
    with _lock:
        d = writer.series(ch.slug)
        if any(a.get("id") == arc_id for a in d.get("arcs") or []):
            return get_arc(ch.slug, arc_id)
        d.setdefault("arcs", []).append({"id": arc_id, "series": True, "title": plan["title"], "idea_id": idea.id,
                                         "topic": f"{plan['title']}. {plan['logline']}", "plan": plan, "parts": [],
                                         "status": "open", "max_parts": plan["parts_count"], "created": time.time(),
                                         "clock_elapsed": 0.0})
        writer._save_series(ch.slug, d)
    with session() as s:
        db = s.get(Idea, idea.id)
        if db and db.status in ("new", "approved"):
            db.status = "scripted"
            s.add(db)
            s.commit()
    log.info("série aberta: %s (%s partes)", plan["title"], plan["parts_count"])
    return get_arc(ch.slug, arc_id)


def open_series(slug: str) -> list[dict[str, Any]]:
    return sorted([a for a in arcs(slug) if a.get("status") == "open"], key=lambda a: a.get("created", 0))


def _part(arc: dict[str, Any], n: int) -> dict[str, Any] | None:
    return next((p for p in arc.get("parts") or [] if p.get("n") == n), None)


def blocked(arc: dict[str, Any]) -> str | None:
    """Por que a próxima parte do arco ainda não pode ser escrita (None = pode)."""
    n = len(arc.get("parts") or []) + 1
    if n > int(arc.get("max_parts") or 0):
        return "série completa"
    w = arc.get("writing") or {}
    if w and time.time() - float(w.get("t") or 0) < 1800:
        return f"parte {w.get('n')} sendo escrita"
    prev = _part(arc, n - 1)
    if prev and prev.get("decision") and not prev.get("choice"):
        until = prev.get("vote_until")
        return f"votação da parte {n - 1} aberta" + (f" até {datetime.fromtimestamp(until):%d/%m %H:%M}" if until else " (a parte ainda não foi ao ar)")
    return None


def claim_next(ch: Channel, idea_id: int | None = None) -> tuple[dict[str, Any], int] | None:
    """Escolhe o que escrever agora: (1) a pauta pedida, (2) a próxima parte livre das séries abertas (ordem de
    criação, até MAX_OPEN), (3) abre a melhor pauta-série nova se houver menos de MAX_OPEN abertas."""
    with _lock:
        if idea_id:
            a = next((x for x in arcs(ch.slug) if x.get("idea_id") == idea_id), None)
            if a is None:
                with session() as s:
                    idea = s.get(Idea, idea_id)
                if idea and seasons.load_plan(ch.slug, idea.id):
                    a = open_arc(ch, idea)
            if a and a.get("status") == "open" and not blocked(a):
                return _claim(ch.slug, a)
        opened = open_series(ch.slug)
        for a in opened[:MAX_OPEN]:
            if not blocked(a):
                return _claim(ch.slug, a)
        if len(opened) < MAX_OPEN:
            for idea in seasons.pending_series(ch):
                a = open_arc(ch, idea)
                if a and not blocked(a):
                    return _claim(ch.slug, a)
    return None


def _claim(slug: str, a: dict[str, Any]) -> tuple[dict[str, Any], int]:
    n = len(a.get("parts") or []) + 1
    a2 = update_arc(slug, a["id"], lambda x: x.update(writing={"n": n, "t": time.time()}))
    return a2, n


def release(slug: str, arc_id: str) -> None:
    update_arc(slug, arc_id, lambda x: x.pop("writing", None))


# ================================================================ roteiro da parte

def bible_with_cast(b: dict[str, Any], arc: dict[str, Any]) -> dict[str, Any]:
    """Bíblia + personagem novo da série (descrição e voz fixas durante a série inteira)."""
    b2 = copy.deepcopy(b)
    have = {c["id"] for c in b2.get("characters") or []}
    for c in (arc.get("plan") or {}).get("newcomers") or []:
        if c["id"] not in have:
            b2.setdefault("characters", []).append(c)
    return b2


def series_block(arc: dict[str, Any], n: int, b: dict[str, Any]) -> str:
    plan = arc["plan"]
    P = plan["parts"]
    cur = P[n - 1]
    total = len(P)
    outline = "\n".join(f"  {'→' if p['n'] == n else ' '} Parte {p['n']}: {p['title']} — {p['goal']}" for p in P)
    cast_ids = [c["id"] for c in plan.get("cast") or []] + [c["id"] for c in plan.get("newcomers") or []]
    cast = ", ".join(f'"{c["id"]}" ({c["name"]})' for c in bible_with_cast(b, arc).get("characters") or [] if c["id"] in cast_ids)
    lines = [f"""SÉRIE PLANEJADA: "{plan['title']}" — {plan['logline']} ({plan['setting']}). {total} partes. ESTA É A PARTE {n} DE {total}.
ESQUELETO DA SÉRIE:
{outline}
ESTA PARTE: objetivo: {cur['goal']} | obstáculo: {cur['obstacle']} | virada: {cur['twist']} | gancho final: {cur['cliffhanger']}
ELENCO DA SÉRIE (use só estes ids como speaker): {cast}. Mesmas roupas, mesmos lugares e o mesmo tom das partes anteriores.
MISSÃO DA SÉRIE (igual em todas as partes): {plan['mission']['title']}{(' — prazo de ' + str(plan['mission'].get('hours')) + 'h') if plan['mission'].get('hours') else ''}.
TÍTULO: exatamente "{plan['title']} — Parte {n}".
NÃO leia horários em voz alta (o relógio já aparece na tela): use "time" nos beats, não no texto."""]
    if cur.get("tip"):
        lines.append(f'DICA REAL DESTA PARTE (verdadeira e segura): {cur["tip"]} — o beat que FALA a dica (não o que a anuncia) leva "tip": true.')
    if n >= 2:
        prev = _part(arc, n - 1) or {}
        lines.append("ABERTURA: o 1º beat é uma frase de recap começando com \"No episódio anterior…\" (marque \"recap\": true), "
                     f"resumindo: {prev.get('summary') or prev.get('cliffhanger') or ''}")
        if prev.get("clock_end"):
            lines.append(f"RELÓGIO: a parte anterior terminou às {prev['clock_end']} ({prev.get('day_label') or ''}); "
                         "\"clock.start\" desta parte continua de lá (nunca volta no tempo).")
        if prev.get("choice"):
            opt = (prev.get("decision") or {}).get("options", {}).get(prev["choice"], "")
            br = (prev.get("decision") or {}).get("branches", {}).get(prev["choice"], "")
            if prev.get("decided_by") == "votos":
                lines.append(f"DECISÃO DO PÚBLICO: venceu {prev['choice']} ({opt}). Logo depois do recap, diga \"Vocês escolheram: {opt}\" "
                             f"e siga esse caminho: {br}")
            else:
                lines.append(f"CAMINHO ESCOLHIDO: {opt}. Siga: {br} (não diga que houve votação).")
    if cur.get("decision"):
        d = cur["decision"]
        lines.append(f"DECISÃO NO FIM DESTA PARTE: antes do CTA, o narrador pergunta \"{d['question']}\" — A: {d['options']['A']} ou "
                     f"B: {d['options']['B']} — e pede para comentar A ou B. O gancho fica no momento da escolha.")
    if n == total:
        lines.append(f"FINAL DA SÉRIE: resolva a missão e feche a história; termine anunciando a próxima série: {plan.get('finale_tease') or 'uma nova aventura do Zé'}.")
    else:
        lines.append(f"FIM: gancho forte + CTA para seguir o canal e ver a parte {n + 1}.")
    return "\n".join(lines)


def after_written(ch: Channel, arc: dict[str, Any], n: int, ep: dict[str, Any], script_id: int) -> None:
    """Guarda a parte na memória da série (resumo, gancho, relógio, decisão) e libera a próxima."""
    from .director import _hm
    plan = arc["plan"]
    cur = plan["parts"][n - 1]
    beats = ep.get("beats") or []
    times = [b.get("time") for b in beats if b.get("time")]
    start = _hm((ep.get("clock") or {}).get("start"))
    end = _hm(times[-1]) if times else None
    elapsed = 0.0
    if start is not None and end is not None:
        elapsed = float((end - start) % 1440)
    day_labels = (ep.get("clock") or {}).get("day_labels") or []

    def upd(a: dict[str, Any]) -> None:
        a["parts"] = [p for p in a.get("parts") or [] if p.get("n") != n] + [{
            "n": n, "script_id": script_id, "title": ep.get("title"), "summary": ep.get("memory") or "",
            "cliffhanger": ep.get("cliffhanger") or "", "next": ep.get("next_hook") or "", "mission": plan["mission"]["title"],
            "style": ep.get("episode_style"), "widgets": sorted({(x.get("widget") or {}).get("type") for x in beats if x.get("widget")} - {None}),
            "decision": cur.get("decision"), "clock_end": times[-1] if times else None, "day_label": day_labels[-1] if day_labels else "",
            "created": time.time()}]
        a["parts"].sort(key=lambda p: p["n"])
        a["clock_elapsed"] = float(a.get("clock_elapsed") or 0) + elapsed
        a.pop("writing", None)
        if len(a["parts"]) >= int(a.get("max_parts") or 0):
            a["status"] = "written"  # todas escritas; segue publicando
    update_arc(ch.slug, arc["id"], upd)


def end_label(arc: dict[str, Any], n: int, ch: Channel) -> str:
    total = int(arc.get("max_parts") or 0)
    if n < total:
        return f"PARTE {n} · CONTINUA…"
    nxt = next((i.title for i in seasons.pending_series(ch) if i.id != arc.get("idea_id")), "")
    return f"FIM DA SÉRIE · próxima: {nxt}"[:60] if nxt else "FIM DA SÉRIE"


# ================================================================ votação (comentários + enquete digitada)

def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


VOTE_WORDS = r"(opcao|opção|letra|alternativa|vai de|vou de|time|escolho|voto|vote|fico com|caminho|equipe)"


def parse_vote(text: str, options: dict[str, str]) -> str | None:
    """Voto num comentário: "A", "b!", "letra A", "vou de B", "time A", ou as palavras da opção ("telhado").
    O "a" minúsculo solto é artigo em português — só conta como voto quando é o comentário inteiro ou vem depois
    de uma palavra de voto; o "A" maiúsculo solto no meio da frase também conta."""
    raw = (text or "").strip()
    t = _norm(raw)
    toks = re.findall(r"[a-z0-9]+", t)
    hits = set()
    for k in ("A", "B"):
        kl = k.lower()
        if toks == [kl] or re.search(VOTE_WORDS + r"\s+" + kl + r"", t) or re.search(r"(?<![\w])" + k + r"(?![\w])", raw[1:])                 or re.match(k + r"(\W|$)", raw) and not re.match(k + r"\s+[a-zà-ú]{2,}", raw):
            hits.add(k)
    if not hits:
        for k, label in (options or {}).items():
            words = re.findall(r"[a-z]{4,}", _norm(label))
            if words and all(w in t for w in words[:2]):
                hits.add(k)
    return hits.pop() if len(hits) == 1 else None


def count_votes(ch: Channel, part: dict[str, Any]) -> dict[str, Any]:
    ext = part.get("external_id")
    opts = (part.get("decision") or {}).get("options") or {}
    by_author: dict[str, str] = {}
    if ext:
        with session() as s:
            rows = s.exec(select(Comment).where(Comment.video_id == ext).order_by(Comment.published_at)).all()
        for c in rows:
            if c.status == "seed" or c.kind == "canal" or (c.author or "").strip().lower() in {ch.name.lower(), (ch.handle or "").lower()}:
                continue
            v = parse_vote(c.text, opts)
            if v:
                by_author[c.author or c.yt_id] = v  # 1 voto por pessoa (vale o último)
    com = {"A": sum(1 for v in by_author.values() if v == "A"), "B": sum(1 for v in by_author.values() if v == "B")}
    man = part.get("poll_manual") or {}
    tot = {k: com[k] + int(man.get(k) or 0) for k in ("A", "B")}
    return {"comments": com, "manual": {k: int(man.get(k) or 0) for k in ("A", "B")}, "total": tot,
            "voters": len(by_author) + int(man.get("A") or 0) + int(man.get("B") or 0)}


def vote_wait_hours(ch: Channel) -> float:
    slots = len(ch.posting_slots or []) or 3
    return max(6.0, min(20.0, 24.0 / slots * 2))


def decide(ch: Channel, arc: dict[str, Any], n: int, force: bool = False) -> dict[str, Any] | None:
    p = _part(arc, n)
    if not p or not p.get("decision") or p.get("choice"):
        return None
    if not force and (not p.get("vote_until") or time.time() < float(p["vote_until"])):
        return None
    v = count_votes(ch, p)
    t = v["total"]
    if v["voters"] >= MIN_VOTES and t["A"] != t["B"]:
        choice, by = ("A" if t["A"] > t["B"] else "B"), "votos"
    else:
        choice, by = p["decision"].get("default", "A"), "padrão"

    def upd(a: dict[str, Any]) -> None:
        q = _part(a, n)
        q.update(votes=v, choice=choice, decided_by=by, decided_at=time.time())
    update_arc(ch.slug, arc["id"], upd)
    log.info("série %s parte %s: escolha %s (%s) %s", arc["title"], n, choice, by, v["total"])
    return {"choice": choice, "by": by, "votes": v}


def set_manual_poll(ch: Channel, arc_id: str, n: int, counts: dict[str, int]) -> dict[str, Any] | None:
    def upd(a: dict[str, Any]) -> None:
        q = _part(a, n)
        if q:
            q["poll_manual"] = {k: max(0, int(counts.get(k) or 0)) for k in ("A", "B")}
    a = update_arc(ch.slug, arc_id, upd)
    p = _part(a, n) if a else None
    return count_votes(ch, p) if p else None


def vote_comment(sc: Script) -> str | None:
    """Comentário fixado das partes com decisão (gancho para community.seed_text)."""
    st = (sc.variety or {}).get("story") or {}
    d = st.get("decision")
    if not d:
        return None
    return f"🗳️ {d['question']} Comenta A ou B! A: {d['options']['A']} · B: {d['options']['B']} — a próxima parte segue o que vocês escolherem."[:300]


def community_poll(sc: Script) -> dict[str, Any] | None:
    st = (sc.variety or {}).get("story") or {}
    d = st.get("decision")
    if not d:
        return None
    return {"question": d["question"][:100], "options": [f"A: {d['options']['A']}"[:30], f"B: {d['options']['B']}"[:30]],
            "image": f"Quadro do fim da parte {st.get('part')}: o Zé diante da escolha (use a miniatura do vídeo)", "story_vote": True}


# ================================================================ agenda em ordem + links

def _slot_times(ch: Channel, after: datetime, days: int = 10) -> list[datetime]:
    """Horários do canal (ex.: 12:00, 18:00, 21:00 de Brasília) a partir de `after`."""
    from ..posting_times import TZ
    out = []
    base = after.astimezone(TZ)
    for d in range(days):
        day = (base + timedelta(days=d)).date()
        for sl in ch.posting_slots or ["12:00", "18:00", "21:00"]:
            m = re.match(r"^(\d{1,2}):(\d{2})$", str(sl).strip())
            if not m:
                continue
            t = datetime(day.year, day.month, day.day, int(m.group(1)), int(m.group(2)), tzinfo=TZ)
            if t > base:
                out.append(t.astimezone(timezone.utc))
    return sorted(out)


def _taken(ch: Channel) -> list[datetime]:
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.channel_id == ch.id,
                                                Publication.status.in_(["scheduled", "uploading", "published"]))).all()
    out = []
    for p in pubs:
        t = p.scheduled_at or p.published_at
        if t:
            out.append(t if t.tzinfo else t.replace(tzinfo=timezone.utc))
    return out


class _Log:
    def __init__(self, fn=None) -> None:
        self.fn = fn or (lambda m: log.info(m))

    def log(self, m: str) -> None:
        self.fn(m)


def schedule_ready(ch: Channel, log_fn=None, force: bool = False) -> int:
    """Agenda as partes prontas (vídeo renderizado e aprovado), estritamente em ordem, uma por horário livre.
    Só com o piloto automático do canal ligado (ou force): com ele desligado, você publica à mão."""
    from ..pipeline import _schedule_publication
    if not (ch.auto_pilot or force):
        return 0
    done = 0
    taken = _taken(ch)
    last_any = max(taken) if taken else now()
    for a in sorted(arcs(ch.slug), key=lambda x: x.get("created", 0)):
        prev_time = None
        for p in sorted(a.get("parts") or [], key=lambda q: q["n"]):
            if p.get("scheduled_at"):
                prev_time = datetime.fromisoformat(p["scheduled_at"])
                continue
            with session() as s:
                v = s.exec(select(Video).where(Video.script_id == p.get("script_id"))).first()
            if not v or v.status != "ready":
                break  # parte k não está pronta: as seguintes esperam (ordem estrita)
            after = max([now() + timedelta(minutes=40)] + ([prev_time + timedelta(hours=1)] if prev_time else []))
            when = next((t for t in _slot_times(ch, after) if all(abs((t - x).total_seconds()) > 3600 for x in taken)), None)
            if when is None:
                break
            _schedule_publication(v.id, when.isoformat(), _Log(log_fn))
            with session() as s:
                pubs = s.exec(select(Publication).where(Publication.video_id == v.id)).all()
                real = min((x.scheduled_at for x in pubs if x.scheduled_at), default=None)
            if not pubs:
                break
            real = real if (real and real.tzinfo) else (real.replace(tzinfo=timezone.utc) if real else when)
            taken.append(real)
            prev_time = real
            n = p["n"]
            update_arc(ch.slug, a["id"], lambda x, n=n, real=real, ids=[x.id for x in pubs]: _part(x, n).update(
                scheduled_at=real.isoformat(), publication_ids=ids))
            done += 1
            last_any = max(last_any, real)
    return done


def _refresh_published(ch: Channel) -> None:
    """Partes que foram ao ar: URL, id, prazo da votação, enquete pronta no checklist e links anterior/próxima."""
    for a in arcs(ch.slug):
        for p in a.get("parts") or []:
            if not p.get("publication_ids") or p.get("external_id"):
                continue
            with session() as s:
                pubs = [s.get(Publication, i) for i in p["publication_ids"]]
            live = next((x for x in pubs if x and x.status == "published" and x.external_id), None)
            if not live:
                continue
            pa = live.published_at or now()
            pa = pa if pa.tzinfo else pa.replace(tzinfo=timezone.utc)
            vu = (pa + timedelta(hours=vote_wait_hours(ch))).timestamp() if p.get("decision") else None
            n = p["n"]
            update_arc(ch.slug, a["id"], lambda x, n=n: _part(x, n).update(
                external_id=live.external_id, url=live.url, published_at=pa.isoformat(), publication_id=live.id,
                **({"vote_until": vu} if vu else {})))
            if p.get("decision"):
                _prefill_poll(live.id, p.get("script_id"))
            try:
                link_parts(ch, a["id"], n)
            except Exception as e:  # noqa: BLE001
                log.warning("links da série: %s", e)


def _prefill_poll(pub_id: int, script_id: int | None) -> None:
    """Enquete da aba Posts já com a pergunta A/B da parte (o checklist do Studio mostra pronta para colar)."""
    try:
        from ..studio_checklist import StudioChecklist, _ensure
        _ensure()
        with session() as s:
            sc = s.get(Script, script_id) if script_id else None
            poll = community_poll(sc) if sc else None
            if not poll:
                return
            row = s.get(StudioChecklist, pub_id)
            pub = s.get(Publication, pub_id)
            if row is None:
                row = StudioChecklist(publication_id=pub_id, channel_id=pub.channel_id if pub else 0)
            row.poll = poll
            s.add(row)
            s.commit()
    except Exception as e:  # noqa: BLE001
        log.warning("enquete da série: %s", e)


def link_parts(ch: Channel, arc_id: str, n: int) -> None:
    """Descrições: a parte n ganha "◀ Parte anterior" e a parte n-1 ganha "▶ Próxima parte" (videos.update, 50 + 1 unidades)."""
    from .. import quota
    from ..models import Account
    from ..publish import _yt_client, _yt_creds
    a = get_arc(ch.slug, arc_id)
    cur, prev = _part(a, n), _part(a, n - 1)
    if not cur or not cur.get("external_id"):
        return
    with session() as s:
        acc = s.exec(select(Account).where(Account.channel_id == ch.id, Account.platform == "youtube")).first()
    if not acc or not acc.credentials:
        return
    yt = _yt_client(_yt_creds(acc))
    todo = []
    if prev and prev.get("url") and not cur.get("linked_prev"):
        todo.append((cur, f"◀ Parte anterior ({prev['n']}): {prev['url']}", "linked_prev"))
    if prev and prev.get("external_id") and not prev.get("linked_next") and cur.get("url"):
        todo.append((prev, f"▶ Próxima parte ({cur['n']}): {cur['url']}", "linked_next"))
    for part, line, flag in todo:
        if not quota.guard("videos.update", 51):
            return
        r = yt.videos().list(part="snippet", id=part["external_id"]).execute()
        quota.spend(1, "list")
        items = r.get("items") or []
        if not items:
            continue
        sn = items[0]["snippet"]
        if line not in (sn.get("description") or ""):
            sn["description"] = (line + "\n\n" + (sn.get("description") or ""))[:4900]
            yt.videos().update(part="snippet", body={"id": part["external_id"], "snippet": {
                k: sn[k] for k in ("title", "description", "categoryId", "tags", "defaultLanguage", "defaultAudioLanguage") if k in sn}}).execute()
            quota.spend(50, "videos.update")
        nn = part["n"]
        update_arc(ch.slug, arc_id, lambda x, nn=nn, flag=flag: _part(x, nn).update({flag: True}))


# ================================================================ versão completa (longo semanal)

def make_long(ch: Channel, arc: dict[str, Any], log_fn=None) -> int | None:
    """Junta as partes num episódio longo 16:9 (capítulos = partes): tira recaps e CTAs do meio, mantém o final."""
    beats: list[dict[str, Any]] = []
    first_story: dict[str, Any] = {}
    srcs: list = []
    for p in sorted(arc.get("parts") or [], key=lambda q: q["n"]):
        with session() as s:
            sc = s.get(Script, p.get("script_id"))
        if not sc:
            return None
        st = (sc.variety or {}).get("story") or {}
        first_story = first_story or st
        srcs += sc.sources or []
        bs = [dict(b) for b in sc.scenes or [] if not b.get("recap")]
        last_part = p["n"] == len(arc["parts"])
        if bs and not last_part:  # tira o CTA ("segue o canal…") e a pergunta A/B das partes do meio
            t = re.sub(r"[^.!?…]*\b(segue|siga|inscreva|comenta|comente)\b[^.!?…]*[.!?…]?", "", bs[-1]["text"], flags=re.I).strip()
            if t:
                bs[-1]["text"] = t
            else:
                bs.pop()
        if bs:
            bs[0]["chapter"] = f"Parte {p['n']}: {(p.get('title') or '').split('—')[-1].strip() or arc['title']}"[:60]
            for b in bs[1:]:  # só um cartão de missão por capítulo
                if (b.get("widget") or {}).get("type") == "mission":
                    b.pop("widget", None)
        beats += bs
    if not beats:
        return None
    plan = arc["plan"]
    story = {**{k: v for k, v in first_story.items() if k in ("mission", "clock", "objectives")},
             "title": f"{arc['title']} — Versão completa", "part": 0, "arc_title": arc["title"], "end_label": "FIM DA SÉRIE",
             "series_arc": arc["id"], "long_of_series": True}
    with session() as s:
        sc = Script(channel_id=ch.id, idea_id=arc.get("idea_id"), format="long", title=story["title"][:200], hook=beats[0]["text"],
                    scenes=beats, description=f"A série completa: {plan['logline']}\n\nTodas as partes de \"{arc['title']}\" num vídeo só.",
                    tags=["serie", plan["genre"]], hashtags=[], thumbnail_text=arc["title"][:28], sources=srcs[:6],
                    variety={"structure": "historia", "series": arc["title"], "story": story, "loop": False}, status="approved")
        s.add(sc)
        s.commit()
        s.refresh(sc)
    update_arc(ch.slug, arc["id"], lambda x: x.update(long={"script_id": sc.id, "at": time.time()}))
    enqueue("story_assets", title=f"Imagens (versão completa): {arc['title']}", channel_id=ch.id, ref_id=sc.id,
            payload={"auto_render": True, "publish_long": True})
    if log_fn:
        log_fn(f"Versão completa de “{arc['title']}” na fila (roteiro #{sc.id}, {len(beats)} falas)")
    return sc.id


def _last_long_at(ch: Channel) -> float:
    return max([float((a.get("long") or {}).get("at") or 0) for a in arcs(ch.slug)] or [0.0])


# ================================================================ tick do agendador

def _jobs_busy(ch: Channel, kinds: tuple[str, ...]) -> bool:
    with session() as s:
        return bool(s.exec(select(Job).where(Job.channel_id == ch.id, Job.kind.in_(kinds),
                                             Job.status.in_(["queued", "running"]))).first())


def tick() -> dict[str, Any]:
    """Mantém os canais dedicados andando: publicação → votos → agenda em ordem → escrever adiante → novas séries → longo."""
    out: dict[str, Any] = {}
    with session() as s:
        chans = s.exec(select(Channel)).all()
    for ch in chans:
        if not seasons.dedicated(ch):
            continue
        try:
            out[ch.slug] = _tick_channel(ch)
        except Exception as e:  # noqa: BLE001
            log.exception("séries %s: %s", ch.slug, e)
    return out


def _tick_channel(ch: Channel) -> dict[str, Any]:
    from .. import focus
    r: dict[str, Any] = {}
    _refresh_published(ch)
    for a in arcs(ch.slug):
        for p in a.get("parts") or []:
            if p.get("decision") and not p.get("choice"):
                d = decide(ch, a, p["n"])
                if d:
                    r.setdefault("decided", []).append({a["title"]: d["choice"]})
    if not ch.auto_pilot:  # piloto desligado: só acompanha votos/links; não escreve adiante nem agenda
        r["autopilot"] = False
        return r
    r["scheduled"] = schedule_ready(ch)
    # séries totalmente publicadas → fechar e preparar a versão completa (longo da semana)
    for a in arcs(ch.slug):
        parts = a.get("parts") or []
        if a.get("status") in ("open", "written") and len(parts) >= int(a.get("max_parts") or 99) and all(p.get("external_id") for p in parts):
            update_arc(ch.slug, a["id"], lambda x: x.update(status="closed"))
            a["status"] = "closed"
        if (a.get("status") == "closed" and not a.get("long") and "long" in (ch.formats or [])
                and time.time() - _last_long_at(ch) > LONG_EVERY_DAYS * 86400 and not _jobs_busy(ch, ("story_assets", "story_render"))):
            make_long(ch, a)
            r["long"] = a["title"]
            break
    if focus.paused(ch):
        return r
    # cano: partes escritas e ainda não publicadas
    unpublished = sum(1 for a in arcs(ch.slug) for p in a.get("parts") or [] if not p.get("external_id"))
    r["buffer"] = unpublished
    if unpublished < BUFFER and not _jobs_busy(ch, ("story_episode",)):
        if any(not blocked(a) for a in open_series(ch.slug)[:MAX_OPEN]) or (len(open_series(ch.slug)) < MAX_OPEN and seasons.pending_series(ch)):
            enqueue("story_episode", title=f"Modo História (série): {ch.name}", channel_id=ch.id, payload={"series_mode": True})
            r["writing"] = True
    # estoque de pautas-série: sempre ~2 séries no cano (uma publicando, uma sendo escrita/à espera)
    stock = len(seasons.pending_series(ch)) + len(open_series(ch.slug))
    if stock < MAX_OPEN + 1 and not _jobs_busy(ch, ("story_series_ideas",)):
        enqueue("story_series_ideas", title=f"Planejar séries: {ch.name}", channel_id=ch.id, payload={"count": 2})
        r["planning"] = True
    return r


def overview(ch: Channel) -> dict[str, Any]:
    """Para o painel: séries (abertas, em publicação, fechadas) com partes, votos e próximos passos + pautas-série."""
    ser = []
    for a in sorted(arcs(ch.slug), key=lambda x: -x.get("created", 0)):
        parts = []
        written = {p["n"]: p for p in a.get("parts") or []}
        for pp in (a.get("plan") or {}).get("parts") or []:
            w = written.get(pp["n"]) or {}
            vid = None
            if w.get("script_id"):
                with session() as s:
                    v = s.exec(select(Video).where(Video.script_id == w["script_id"])).first()
                vid = {"id": v.id, "status": v.status, "thumbnail": v.thumbnail_path, "path": v.path} if v else None
            st = "planejada"
            if w:
                st = "escrita"
            if vid and vid["status"] == "ready":
                st = "pronta"
            if w.get("scheduled_at"):
                st = "agendada"
            if w.get("external_id"):
                st = "no ar"
            votes = count_votes(ch, w) if (w.get("decision") and w.get("external_id")) else None
            parts.append({**{k: pp.get(k) for k in ("n", "title", "goal", "cliffhanger", "decision", "tip")},
                          "status": st, "script_id": w.get("script_id"), "video": vid, "scheduled_at": w.get("scheduled_at"),
                          "url": w.get("url"), "choice": w.get("choice"), "decided_by": w.get("decided_by"),
                          "vote_until": w.get("vote_until"), "votes": votes, "poll_manual": w.get("poll_manual")})
        ser.append({"id": a["id"], "title": a["title"], "idea_id": a.get("idea_id"), "status": a.get("status"),
                    "genre": (a.get("plan") or {}).get("genre"), "logline": (a.get("plan") or {}).get("logline"),
                    "mission": (a.get("plan") or {}).get("mission"), "parts": parts, "blocked": blocked(a) if a.get("status") == "open" else None,
                    "long": a.get("long"), "newcomers": (a.get("plan") or {}).get("newcomers")})
    pend = [{"idea_id": i.id, "title": i.title, "status": i.status, "plan": seasons.load_plan(ch.slug, i.id)} for i in seasons.pending_series(ch)]
    return {"series": ser, "pending": pend, "vote_wait_hours": vote_wait_hours(ch)}
