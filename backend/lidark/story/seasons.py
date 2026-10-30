"""Pautas-SÉRIE para canais dedicados ao Modo História (ex.: Zé na Fuga).

Cada pauta é uma série inteira, planejada antes de escrever: título da série, logline, gênero/cenário, missão (com prazo
quando faz sentido), elenco (Zé + coadjuvantes + no máximo 1 personagem novo com descrição/voz fixas), número de partes
(3 a 6 Shorts) e o ROTEIRO-ESQUELETO parte a parte (objetivo, obstáculo, virada, gancho; 1-2 pontos de DECISÃO A/B para
o público votar, nunca no final; a última parte resolve a missão e anuncia a próxima série).

O plano fica em data/story/<slug>/plans/<idea_id>.json e a pauta (Idea) ganha as tags "serie", "genero:<g>", "partes:<n>".
Gêneros giram (zumbi, alien, ilha, casa assombrada, apagão, fim da internet, desastre natural, momento real da
história...) e o pedido evita repetir o que as séries anteriores fizeram (variedade = segurança no YPP).
Séries de HISTÓRIA REAL passam pela checagem de fatos da pauta (verify_idea); ficção não (só as dicas reais).
"""
from __future__ import annotations

import json
import random
import re
import time
from pathlib import Path
from typing import Any

from sqlmodel import select

from .. import llm
from ..db import session
from ..jobs import JobContext, enqueue, handler
from ..models import Channel, Idea
from . import bible as B

GENRES = {
    "zumbi": "apocalipse zumbi (sem gore: ameaça, fuga, abrigo)",
    "alien": "invasão alienígena / sinal do espaço",
    "ilha": "sobreviver numa ilha deserta",
    "assombrada": "casa assombrada / mistério sobrenatural leve",
    "apagao": "apagão geral na cidade",
    "internet": "o fim da internet / tudo digital para",
    "desastre": "desastre natural (enchente, terremoto, tempestade, onda de calor)",
    "historia": "um momento REAL da história do Brasil ou do mundo, sem tragédia com vítimas (fatos e datas exatos)",
    "espaco": "preso numa estação espacial / missão no espaço",
    "floresta": "perdido na floresta / trilha que deu errado",
    "deserto": "atravessar um deserto",
    "inverno": "nevasca / frio extremo",
}
VOICES_NEW = {"m": [("pt-BR-AntonioNeural", "-10Hz", "-4%"), ("pt-BR-AntonioNeural", "+22Hz", "+6%")],
              "f": [("pt-BR-FranciscaNeural", "+4Hz", "+2%"), ("pt-BR-ThalitaMultilingualNeural", "+0Hz", "+0%")]}


def dedicated(ch: Channel) -> bool:
    b = B.load(ch.slug)
    return bool(b.get("dedicated")) and b.get("enabled", True) is not False


def plans_dir(slug: str) -> Path:
    return B.STORY_DIR / slug / "plans"


def load_plan(slug: str, idea_id: int) -> dict[str, Any] | None:
    p = plans_dir(slug) / f"{idea_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except ValueError:
        return None


def save_plan(slug: str, idea_id: int, plan: dict[str, Any]) -> None:
    d = plans_dir(slug)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{idea_id}.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")


def all_plans(slug: str) -> list[dict[str, Any]]:
    out = []
    for p in sorted(plans_dir(slug).glob("*.json")) if plans_dir(slug).exists() else []:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            d["idea_id"] = int(p.stem)
            out.append(d)
        except (ValueError, OSError):
            pass
    return out


def _recent(slug: str) -> tuple[list[str], list[str]]:
    plans = sorted(all_plans(slug), key=lambda p: p.get("created", 0))
    return [p.get("genre", "") for p in plans][-6:], [p.get("title", "") for p in plans][-12:]


# ================================================================ normalização do plano

def normalize_plan(d: dict[str, Any], b: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(d, dict) or not d.get("title") or not isinstance(d.get("parts"), list):
        return None
    parts = [p for p in d["parts"] if isinstance(p, dict) and (p.get("goal") or p.get("title"))][:6]
    if len(parts) < 3:
        return None
    known = {c["id"] for c in b.get("characters") or []}
    cast, newcomers = [], []
    for c in d.get("cast") or []:
        if not isinstance(c, dict):
            continue
        cid = re.sub(r"[^a-z0-9_]", "", str(c.get("id") or "").lower())[:20]
        if cid in known:
            cast.append({"id": cid})
        elif cid and c.get("desc") and len(newcomers) < 1:  # no máximo 1 personagem novo por série
            g = "f" if str(c.get("gender") or c.get("voice_hint") or "").lower().startswith(("f", "mulher", "fem")) else "m"
            v = random.Random(cid).choice(VOICES_NEW[g])
            newcomers.append({"id": cid, "name": str(c.get("name") or cid.title())[:24], "role": str(c.get("role") or "")[:30],
                              "desc": str(c["desc"])[:400], "eyes": "dots", "seed": random.randint(10000, 99999),
                              "voice": v[0], "pitch": v[1], "rate": v[2], "one_off": True})
    if not any(c["id"] == (b.get("characters") or [{}])[0].get("id") for c in cast):
        cast.insert(0, {"id": (b.get("characters") or [{"id": "ze"}])[0]["id"]})
    decisions = 0
    out_parts = []
    for i, p in enumerate(parts):
        dec = p.get("decision") if isinstance(p.get("decision"), dict) else None
        last = i == len(parts) - 1
        if dec and not last and decisions < 2 and isinstance(dec.get("options"), dict) and {"A", "B"} <= set(dec["options"]):
            decisions += 1
            dec = {"question": str(dec.get("question") or "")[:120], "options": {k: str(dec["options"][k])[:40] for k in ("A", "B")},
                   "default": "A" if str(dec.get("default") or "A").upper() != "B" else "B",
                   "branches": {k: str((dec.get("branches") or {}).get(k) or "")[:300] for k in ("A", "B")}}
        else:
            dec = None
        out_parts.append({"n": i + 1, "title": str(p.get("title") or f"Parte {i + 1}")[:60], "goal": str(p.get("goal") or "")[:300],
                          "obstacle": str(p.get("obstacle") or "")[:300], "twist": str(p.get("twist") or "")[:300],
                          "cliffhanger": str(p.get("cliffhanger") or "")[:300], "tip": str(p.get("tip") or "")[:240],
                          "decision": dec})
    m = d.get("mission") if isinstance(d.get("mission"), dict) else {}
    from .writer import _mission
    genre = str(d.get("genre") or "").lower()
    genre = genre if genre in GENRES else next((g for g in GENRES if g in genre), "misterio")
    return {"title": str(d["title"])[:70], "logline": str(d.get("logline") or "")[:300], "genre": genre,
            "setting": str(d.get("setting") or "")[:300], "real_history": bool(d.get("real_history")) or genre == "historia",
            "real_event": str(d.get("real_event") or "")[:200], "mission": _mission(m), "cast": cast, "newcomers": newcomers,
            "parts_count": len(out_parts), "parts": out_parts, "finale_tease": str(d.get("finale_tease") or "")[:200],
            "created": time.time()}


# ================================================================ pedido ao LLM

def generate(ch: Channel, count: int = 2, seed_hint: str = "", log=print) -> list[dict[str, Any]]:
    b = B.load(ch.slug)
    used_g, used_t = _recent(ch.slug)
    pool = [g for g in GENRES if g not in used_g[-3:]] or list(GENRES)
    rng = random.Random(time.time())
    rng.shuffle(pool)
    want = pool[:count]
    chars = "\n".join(f'  - id "{c["id"]}": {c["name"]} ({c.get("role", "")}) — {c["desc"][:120]}' for c in b.get("characters") or [])
    prompt = f"""Você planeja SÉRIES para o canal de Shorts "{ch.name}" (série "{b.get('series_title')}").
PREMISSA DO CANAL: {b.get('premise')}
ELENCO FIXO:
{chars}
Crie {count} SÉRIES NOVAS, uma para cada gênero: {', '.join(GENRES[g] for g in want)}.
{('Ideia do dono para considerar: ' + seed_hint) if seed_hint else ''}
NÃO repita títulos/temas recentes: {'; '.join(t for t in used_t if t) or '(nenhum)'}.
Cada série:
- "title": "Zé no/na ..." (até 50 caracteres, chamativo, sem clickbait mentiroso), "genre" (um de: {', '.join(GENRES)}),
  "logline" (1 frase), "setting" (onde/quando), "real_history" (true só se for um evento REAL — aí datas/fatos exatos),
  "real_event" (qual evento, se for real), "mission": {{"title": "MISSÃO EM MAIÚSCULAS", "subtitle": "...", "hours": 72}}
  (hours SÓ se a missão for um prazo e o título disser, ex.: "SOBREVIVA 72H").
- "cast": [{{"id": "ze"}}, {{"id": "nina"}}...] + no máximo 1 personagem NOVO: {{"id": "curto", "name": "...", "role": "...",
  "gender": "m|f", "desc": "descrição VISUAL em inglês no estilo do canal (cabeça-esfera creme com dois olhinhos de ponto, roupa)"}}
- "parts": 3 a 6 partes (a história decide). Cada parte: {{"title", "goal", "obstacle", "twist", "cliffhanger",
  "tip": "uma dica REAL, realista e SEGURA de sobrevivência quando couber (ou vazio)",
  "decision": null OU {{"question": "pergunta curta ao público", "options": {{"A": "...", "B": "..."}}, "default": "A",
  "branches": {{"A": "o que acontece se A", "B": "o que acontece se B"}}}}}}.
  Use 1 ou 2 decisões por série (em partes do meio, NUNCA na última).
  A última parte RESOLVE a missão e deixa um gancho para a próxima série ("finale_tease").
REGRAS: suspense sem gore; nada que ensine algo perigoso; série de HISTÓRIA REAL só com eventos marcantes que NÃO
sejam tragédias com vítimas reais (nada de incêndios, desabamentos, naufrágios, massacres ou acidentes com mortos como
cenário de aventura — respeito às vítimas e às famílias); humor leve (o Zé é medroso mas esperto); dicas de
sobrevivência verdadeiras e seguras; em série de história real, nada inventado sobre pessoas/datas reais.
Responda JSON: {{"series": [{{...}}, {{...}}]}}"""
    data = llm.complete_json(prompt, temperature=0.9, required=("series",), timeout=180)
    out = []
    for d in (data.get("series") or []) if isinstance(data, dict) else []:
        p = normalize_plan(d, b)
        if p:
            out.append(p)
    log(f"{len(out)} série(s) planejada(s): " + " | ".join(f"{p['title']} ({p['parts_count']} partes)" for p in out))
    return out


def create_ideas(ch: Channel, plans: list[dict[str, Any]]) -> list[int]:
    ids = []
    for p in plans:
        parts_txt = " → ".join(f"P{x['n']}: {x['title']}" for x in p["parts"])
        with session() as s:
            idea = Idea(channel_id=ch.id, title=p["title"], angle=p["logline"], summary=f"{p['setting']}. {parts_txt}"[:2000],
                        format="short", origin="auto", status="new", score=82,
                        fact_status="pending" if p["real_history"] else "verified",
                        score_reason=f"Série de {p['parts_count']} partes · gênero {p['genre']}"
                                     + (f" · {sum(1 for x in p['parts'] if x.get('decision'))} decisão(ões) do público" if any(x.get('decision') for x in p['parts']) else ""),
                        tags=["serie", f"genero:{p['genre']}", f"partes:{p['parts_count']}"] + (["historia_real"] if p["real_history"] else []))
            s.add(idea)
            s.commit()
            s.refresh(idea)
            ids.append(idea.id)
        save_plan(ch.slug, idea.id, p)
        if p["real_history"]:
            enqueue("verify_idea", title=f"Checar fatos da série: {p['title']}", channel_id=ch.id, ref_id=idea.id)
    return ids


def pending_series(ch: Channel) -> list[Idea]:
    """Pautas-série ainda não começadas (aprovadas primeiro, depois pela nota)."""
    with session() as s:
        rows = s.exec(select(Idea).where(Idea.channel_id == ch.id, Idea.status.in_(["approved", "new"]),
                                         Idea.fact_status == "verified")).all()
    rows = [r for r in rows if "serie" in (r.tags or []) and load_plan(ch.slug, r.id)]
    return sorted(rows, key=lambda r: (r.status != "approved", -(r.score or 0), r.id))


def discover(ctx: JobContext, ch: Channel) -> dict:
    """Desvio do discover_ideas para canais dedicados: pautas viram SÉRIES planejadas."""
    n = max(1, min(3, int(ctx.payload.get("count") or 2)))
    ctx.update(0.1, "Planejando séries (pautas que rendem várias partes)")
    plans = generate(ch, n, ctx.payload.get("seed", ""), ctx.log)
    ids = create_ideas(ch, plans)
    return {"ideas": ids, "series": [p["title"] for p in plans]}


@handler("story_series_ideas")
def job_series_ideas(ctx: JobContext) -> dict:
    with session() as s:
        ch = s.get(Channel, ctx.channel_id)
    return discover(ctx, ch)
