"""Roteirista do Modo História: UM pedido ao LLM por episódio (cota apertada) → episódio em JSON.

Formato do episódio (normalizado por normalize()):
{
  "title", "thumbnail_text", "description", "hashtags": [], "tags": [],
  "arc_title", "part": 1, "mission": {"title", "subtitle", "hours" | "minutes"},
  "clock": {"mode", "start": "06:00", "day_labels": [...]}, "objectives": ["...", ...],
  "beats": [{"speaker": "narrador" | <id do personagem>, "text", "emotion", "time", "impact", "pause",
             "visual": {"kind": scene|layered|insert, "desc" (inglês, para a imagem), "place", "chars": [{"id","pose"}], "tags": []},
             "widget": {"type", "data"}, "fx": [], "chip", "highlight", "objective_done"}],
  "cliffhanger", "memory", "next_hook", "facts": [], "episode_style"
}
Memória da série: data/story/<slug>/series.json (arcos → partes, com resumo e gancho de cada parte).
Fatos: o texto final passa pela checagem frase a frase já existente (content.check_claims) antes do render.
"""
from __future__ import annotations

import json
import random
import re
import threading
import time
from typing import Any

from .. import llm, research
from ..models import Channel, Idea
from .bible import COMMON_POSES, STORY_DIR

_lock = threading.Lock()

EPISODE_STYLES = {
    "sobrevivencia": "Sobrevivência com prazo: o protagonista precisa aguentar/escapar até o fim do cronômetro.",
    "corrida": "Corrida contra o tempo: chegar a um lugar/entregar algo antes que um fato real aconteça.",
    "investigacao": "Investigação: o protagonista junta pistas reais (documentos, notícias, testemunhas) para entender o que está acontecendo.",
    "diario": "Diário de bordo: o episódio avança por horários marcados, como anotações de um diário, até a virada.",
    "dilema": "Dilema: o protagonista precisa escolher entre duas saídas; a escolha certa depende de um fato real que o espectador aprende.",
}
WIDGET_DOC = {
    "mission": 'cartão "NOVA MISSÃO" (data: {} — usa a missão do episódio)',
    "objectives": "lista de objetivos que vão sendo marcados (data: {})",
    "newspaper": 'jornal da época (data: {"date": "...", "headline": "1-2 palavras", "headline2": "1-2 palavras", "sub": "linha fina curta"})',
    "telegram": 'telegrama/bilhete datilografado (data: {"header": "TELEGRAMA", "text": "até 18 palavras"})',
    "console": 'console de missão (data: {"title": "...", "lines": ["linha de telemetria curta", ...até 5]})',
    "notebook": 'caderno de laboratório (data: {"title": "...", "lines": ["anotação curta", ...até 4]})',
    "scoreboard": 'placar (data: {"home": "TIME", "away": "TIME", "score_home": 0, "score_away": 1})',
    "chat": 'conversa de mensagens (data: {"messages": [{"from": "nome", "text": "..."}, {"me": true, "audio": true}]})',
    "map": 'mapa com rota (data: {"label": "LUGAR"})',
    "inventory": 'recursos (data: {"items": [{"label": "ÁGUA", "from": 3, "value": 2, "max": 3}]})',
    "alert": 'alerta vermelho (data: {"kicker": "...", "title": "2-3 palavras", "body": "até 6 palavras"})',
    "countdown": 'número gigante (data: {"value": "70:00", "label": "HORAS PELA FRENTE"})',
}


DEVICE_DOC = {
    "tv": 'TV com plantão (data: {"tag": "PLANTÃO", "headline": "manchete curta", "ticker": "letreiro", "anchor": "nome FICTÍCIO do âncora"}) — a fala do beat sai da TV: speaker "tv"',
    "radio": 'rádio (data: {"station": "nome FICTÍCIO da rádio"}) — o locutor fala pelo rádio: speaker "radio"',
    "phone": 'celular (data: {"mode": "lock|alert|chat|call", "app": "...", "title": "...", "body": "até 16 palavras", "messages": [{"from": "nome", "text": "..."}, {"audio": true}]}) — se for áudio de voz ou chamada, speaker "phone"',
    "comms": 'rádio de bordo (data: {"channel": "CANAL 2 · CONTROLE", "from": "quem fala"}) — speaker "comms"',
    "monitor": 'monitor de computador (data: {"title": "...", "values": [números REAIS da explicação], "lines": ["..."]})',
    "newsboy": 'jornaleiro gritando na rua (data: {"cry": "EXTRA! EXTRA!", "headline": "manchete"}) — speaker "newsboy" grita a manchete',
    "proclamation": 'edital colado no muro (data: {"title": "EDITAL", "text": "o texto oficial resumido"}) — speaker "proclamation" lê o edital',
}


# ================================================================ memória da série

def _series_path(slug: str):
    return STORY_DIR / slug / "series.json"


def series(slug: str) -> dict[str, Any]:
    p = _series_path(slug)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {"arcs": []}


def _save_series(slug: str, d: dict[str, Any]) -> None:
    p = _series_path(slug)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def open_arc(slug: str, max_parts: int = 4) -> dict[str, Any] | None:
    """Arco em andamento que ainda pede continuação (última parte terminou em gancho)."""
    for a in reversed(series(slug).get("arcs") or []):
        if a.get("status") == "open" and len(a.get("parts") or []) < int(a.get("max_parts") or max_parts):
            return a
    return None


def record_part(slug: str, arc_id: str, part: dict[str, Any], *, arc_title: str = "", idea_id: int | None = None,
                topic: str = "", max_parts: int = 4, close: bool = False) -> dict[str, Any]:
    with _lock:
        d = series(slug)
        arc = next((a for a in d["arcs"] if a["id"] == arc_id), None)
        if arc is None:
            arc = {"id": arc_id, "title": arc_title, "topic": topic, "idea_id": idea_id, "parts": [], "status": "open",
                   "max_parts": max_parts, "created": time.time()}
            d["arcs"].append(arc)
        arc["parts"] = [p for p in arc["parts"] if p.get("n") != part.get("n")] + [part]
        arc["parts"].sort(key=lambda p: p.get("n", 0))
        if close or len(arc["parts"]) >= int(arc.get("max_parts") or max_parts):
            arc["status"] = "closed"
        _save_series(slug, d)
        return arc


def recent_usage(slug: str, n: int = 8) -> dict[str, list[str]]:
    """O que os últimos episódios usaram (missão, estilo, widgets, abertura) → o próximo varia."""
    parts = [p for a in series(slug).get("arcs") or [] for p in a.get("parts") or []]
    parts.sort(key=lambda p: p.get("created", 0))
    parts = parts[-n:]
    return {"missions": [p.get("mission", "") for p in parts], "styles": [p.get("style", "") for p in parts],
            "widgets": [w for p in parts for w in p.get("widgets", [])], "titles": [p.get("title", "") for p in parts]}


# ================================================================ prompt

def _words(seconds: float, rate_pct: int = 5, beats: int = 11) -> tuple[int, int]:
    """Palavras que cabem: fala do narrador (≈2,4 p/s na velocidade da voz) menos as pausas entre falas e o fim."""
    wps = 2.4 * (1 + rate_pct / 100)
    hi = int((seconds - 2.5 - 0.38 * beats) * wps)
    return max(60, int(hi * 0.85)), hi


def build_prompt(ch: Channel, b: dict[str, Any], fmt: str, *, topic: str, facts: list[str], dossier: str,
                 arc: dict[str, Any] | None, plan: dict[str, Any], seconds: float, rng: random.Random) -> tuple[str, dict[str, Any]]:
    use = recent_usage(b["slug"])
    style_opts = [k for k in EPISODE_STYLES if k not in use["styles"][-2:]] or list(EPISODE_STYLES)
    style = rng.choice(style_opts)
    allowed = [w for w in (b.get("hud") or {}).get("widgets") or [] if w in WIDGET_DOC]
    recent_w = use["widgets"][-14:]
    fresh = sorted(allowed, key=lambda w: (recent_w.count(w), rng.random()))
    n_widgets = rng.randint(4, 6) if fmt == "short" else 14
    from .bible import voice_for
    try:
        rp = int(str(voice_for(b, "narrador").get("rate") or "+0%").strip().rstrip("%"))
    except ValueError:
        rp = 0
    lo, hi = _words(seconds, rp, 11 if fmt == "short" else int(seconds / 4.5))
    chars = "\n".join(f'  - id "{c["id"]}": {c["name"]} ({c.get("role", "")})' for c in b.get("characters") or [])
    poses = ", ".join(b.get("poses") or list(COMMON_POSES))
    part_n = (len(arc["parts"]) + 1) if arc else 1
    prev = ""
    if arc:
        prev = "\n".join(f"  Parte {p['n']}: {p.get('summary', '')} | GANCHO: {p.get('cliffhanger', '')}" for p in arc["parts"][-3:])
        prev = f"""
ESTE EPISÓDIO CONTINUA O ARCO "{arc.get('title')}" — é a PARTE {part_n}. O que já aconteceu:
{prev}
Comece resolvendo/retomando o gancho da parte anterior em 1 frase (sem "na parte anterior..." longo) e avance a história."""
    widgets_doc = "\n".join(f'  - "{w}": {WIDGET_DOC[w]}' for w in fresh)
    devs = [d for d in (b.get("hud") or {}).get("devices") or [] if d in DEVICE_DOC]
    devices_doc = "\n".join(f'  - "{d}": {DEVICE_DOC[d]}' for d in devs) or "  (nenhum nesta série)"
    missions = ", ".join(b.get("missions") or [])
    avoid_m = ", ".join(x for x in use["missions"][-4:] if x) or "(nenhuma)"
    opening = plan.get("opening_type") or "impact"
    long_block = ""
    if fmt == "long":
        long_block = f"""
FORMATO LONGO ({seconds / 60:.0f} min): organize em 4 a 7 CAPÍTULOS; cada capítulo é uma MISSÃO nova do mesmo evento.
Marque o 1º beat de cada capítulo com "chapter": "título do capítulo (2-5 palavras)" e "mission": {{"title": "...", "subtitle": "..."}}
e ponha nele o widget "mission". Cada capítulo fecha com um mini-gancho para o próximo."""
    prompt = f"""Você é roteirista de uma série narrativa ilustrada para o canal "{ch.name}" ({ch.niche}).
FORMATO: história em série, estilo jogo de sobrevivência com HUD (relógio, missão, objetivos, cartões na tela), narrada
em português do Brasil, para {"YouTube Shorts (vertical)" if fmt == "short" else "vídeo longo no YouTube"}.
SÉRIE: "{b.get('series_title')}". PREMISSA: {b.get('premise')}
PERSONAGENS (ficcionais, nossos):
{chars}
POSES DISPONÍVEIS: {poses}
{prev}
TEMA/EVENTO REAL DESTE {"EPISÓDIO" if not arc else "ARCO"}: {topic}
FATOS CONFIRMADOS (use SÓ estes e o material abaixo para datas, nomes, números; nada inventado):
{chr(10).join('- ' + f for f in facts[:14]) or '(veja o material)'}
MATERIAL DE PESQUISA:
{dossier[:5000] or '(sem material extra)'}

REGRAS DE VERDADE: a moldura ("se você acordasse em...", o protagonista, os vizinhos, as falas) é ficção e pode ser
inventada; MAS todo evento, data, lugar, número, lei e pessoa real citados precisam ser exatos e estar nos fatos/material.
Nunca atribua a pessoas reais falas que não estão documentadas. Na dúvida, deixe de fora.

ESTILO DO EPISÓDIO: {EPISODE_STYLES[style]}
MISSÃO: invente uma missão curta em MAIÚSCULAS (2-4 palavras) que combine com o evento (exemplos do tom: {missions}).
PRAZO: "hours" (ou "minutes") SÓ quando a missão É um prazo e o título diz isso (ex.: "SOBREVIVA 72H" → hours 72,
"ANTES DO TOQUE DE RECOLHER" → minutes até o toque). Missão sem prazo (ex.: "ATRAVESSE A CIDADE"): NÃO mande hours.
O prazo precisa caber nos fatos (ex.: a revolta durou ~6 dias; 72h de sobrevivência no auge faz sentido).
NÃO repita as missões recentes: {avoid_m}.
ABERTURA ({opening}): a 1ª frase prende em 2 segundos — {'um impacto/cena no meio da ação' if opening == 'impact' else 'uma pergunta/situação que deixa o espectador curioso'}; o hook já diz o prazo/o perigo.
TAMANHO: entre {lo} e {hi} palavras faladas no total (narração + falas), em {10 if fmt == 'short' else 40} a {13 if fmt == 'short' else 90} beats (cada beat com 6 a 16 palavras: uma ideia por beat, a imagem troca a cada beat).
Frases curtas, presente do indicativo, ritmo de trailer. 1 a 3 falas curtas de personagens (até 14 palavras cada).
FIM: o último beat é o GANCHO (cliffhanger real do evento) + chamada curta para seguir o canal e ver a parte {part_n + 1}
(ex.: "Segue o canal pra ver se o Zé sai dessa na parte {part_n + 1}.") — use "segue" ou "siga".
VISUAL de cada beat ("visual"):
  - "kind": "scene" (ilustração com personagem em ação), "layered" (cenário vazio + personagem posado por cima) ou
    "insert" (close de objeto/documento/detalhe, sem personagem). Varie: ~50% scene, ~30% layered, ~20% insert.
  - "desc": descrição da IMAGEM em INGLÊS (o que se vê, época, luz, enquadramento), sem texto escrito na imagem.
  - "place": nome curto do lugar em inglês (ex.: "rented room", "tram avenue") — repita o mesmo nome quando for o mesmo lugar.
  - "chars": [{{"id": "...", "pose": uma das poses}}] (vazio em insert), "tags": 2-4 palavras-chave em português.
WIDGETS (use {n_widgets} no episódio, os mais frescos primeiro; cada um num beat diferente):
{widgets_doc}
APARELHOS DA ÉPOCA (use 2 ou 3 no episódio, em beats diferentes, como momento de tela cheia: "device": {{"type": "...", "data": {{...}}}};
a fala do beat SAI do aparelho quando o speaker é o próprio aparelho — notícia, locutor, áudio de voz, pregão):
{devices_doc}
Nada de aparelho fora da época (em 1904 não existe TV nem celular). Nomes de jornais/rádios/âncoras são FICTÍCIOS.
Outras deixas por beat (opcionais): "fx" (lista: dust, smoke, rain, fire, embers, candle, alarm, flash, night, stars,
bubbles, confetti), "impact": true (batida forte), "chip": "etiqueta curta de contexto", "highlight": {{"label": "..."}}
(caixa em volta do PERSONAGEM na tela; label = nome + estado, ex.: "ZÉ · SEM SAÍDA"), "objective_done": índice do objetivo cumprido, "time": horário da história ("07:40";
no futebol, minuto do jogo "32"; no espaço, tempo de missão "55:54").
{long_block}
Responda APENAS JSON:
{{"title": "título chamativo com 'Parte {part_n}' no fim (até 70 caracteres)", "thumbnail_text": "2-4 palavras",
"description": "2-3 frases + convite para a série", "hashtags": ["#..."], "tags": ["..."],
"arc_title": "nome do arco (o evento)", "mission": {{"title": "...", "subtitle": "lugar, mês e ano", "hours": 72}},
"clock": {{"start": "06:00", "day_labels": ["QUI 10/11/1904"]}}, "objectives": ["3 objetivos curtos"],
"beats": [{{"speaker": "narrador", "text": "...", "emotion": "tensao", "visual": {{...}}, "widget": {{"type": "mission", "data": {{}}}}}}],
"cliffhanger": "o gancho em 1 frase", "memory": "resumo do que aconteceu (2 frases) para a próxima parte",
"next_hook": "o que a próxima parte vai mostrar", "facts": ["cada afirmação factual usada, com data/nome"]}}"""
    return prompt, {"style": style, "part": part_n, "words": [lo, hi]}


# ================================================================ normalização

def normalize(data: dict[str, Any], b: dict[str, Any], fmt: str, max_words: int) -> dict[str, Any]:
    devs = set((b.get("hud") or {}).get("devices") or [])
    ids = {c["id"] for c in b.get("characters") or []} | ({"tv", "radio", "phone", "comms", "newsboy", "proclamation"} & devs)
    allowed_w = set((b.get("hud") or {}).get("widgets") or []) | {"mission", "objectives", "endcard"}
    beats = []
    for x in data.get("beats") or []:
        if not isinstance(x, dict) or not str(x.get("text") or "").strip():
            continue
        spk = str(x.get("speaker") or "narrador").strip().lower()
        if spk not in ids:
            spk = "narrador"
        v = x.get("visual") if isinstance(x.get("visual"), dict) else {}
        kind = v.get("kind") if v.get("kind") in ("scene", "layered", "insert") else "scene"
        chars = [c for c in (v.get("chars") or []) if isinstance(c, dict) and c.get("id") in ids and c.get("id") not in devs][:3]
        dev = x.get("device") if isinstance(x.get("device"), dict) and x["device"].get("type") in devs else None
        if kind == "insert":
            chars = []
        w = x.get("widget") if isinstance(x.get("widget"), dict) else None
        if w and w.get("type") not in allowed_w:
            w = None
        beats.append({**{k: x[k] for k in ("emotion", "time", "impact", "pause", "chip", "highlight", "objective_done", "fx",
                                           "chapter", "mission") if x.get(k) not in (None, "", [])},
                      "speaker": spk, "text": re.sub(r"\s+", " ", str(x["text"])).strip(),
                      "visual": {"kind": kind, "desc": str(v.get("desc") or "")[:400], "place": str(v.get("place") or "")[:60],
                                 "chars": [{"id": c["id"], "pose": str(c.get("pose") or "front")} for c in chars],
                                 "tags": [str(t).lower() for t in (v.get("tags") or [])][:5]},
                      "widget": w, **({"device": {"type": dev["type"], "data": dev.get("data") or {}}} if dev else {})})
    # mantém o tamanho: corta beats do meio sem widget/objetivo até caber (nunca o 1º nem o último)
    def total() -> int:
        return sum(len(bb["text"].split()) for bb in beats)
    while fmt == "short" and total() > max_words and len(beats) > 6:
        cand = [i for i in range(1, len(beats) - 1) if not beats[i].get("widget") and beats[i].get("objective_done") is None
                and beats[i]["speaker"] == "narrador"]
        if not cand:
            break
        beats.pop(max(cand, key=lambda i: len(beats[i]["text"].split())))
    m = data.get("mission") if isinstance(data.get("mission"), dict) else {}
    out = {k: data.get(k) for k in ("title", "thumbnail_text", "description", "arc_title", "cliffhanger", "memory", "next_hook")}
    out.update(hashtags=[str(h) for h in (data.get("hashtags") or [])][:5], tags=[str(t) for t in (data.get("tags") or [])][:15],
               facts=[str(f) for f in (data.get("facts") or [])][:20],
               mission=_mission(m),
               clock=data.get("clock") if isinstance(data.get("clock"), dict) else {},
               objectives=[str(o)[:44] for o in (data.get("objectives") or [])][:4], beats=beats)
    if beats and not any((bb.get("widget") or {}).get("type") == "mission" for bb in beats[:2]):
        beats[0]["widget"] = beats[0].get("widget") or {"type": "mission", "data": {}}
    return out


# ================================================================ pedido

def write_episode(ch: Channel, b: dict[str, Any], fmt: str = "short", *, idea: Idea | None = None, topic: str = "",
                  arc: dict[str, Any] | None = None, plan: dict[str, Any] | None = None, seconds: float | None = None,
                  log=None) -> dict[str, Any]:
    plan = plan or {}
    rng = random.Random(f"{ch.id}-{time.time()}")
    if seconds is None:
        seconds = float(plan.get("seconds") or 0) if fmt == "short" else (ch.long_minutes or 8) * 60
        if fmt == "short":  # Modo História pede 45-60 s
            seconds = max(45.0, min(60.0, seconds or rng.uniform(46, 58)))
    if arc and arc.get("idea_id") and idea is None:
        from ..db import session
        with session() as s:
            idea = s.get(Idea, arc["idea_id"])
    topic = topic or (arc or {}).get("topic") or (f"{idea.title}. {idea.summary}" if idea else "")
    facts = [f"{f.get('claim')}" + (f" ({f.get('note')})" if f.get("note") else "") for f in (idea.facts if idea else [])
             if f.get("verdict") in ("confirmado", "parcial")]
    dossier = ""
    srcs: list[dict[str, Any]] = []
    try:
        d = research.gather_dossier((idea.title if idea else topic)[:160], max_sources=4)
        srcs = [{"title": x.get("title", ""), "url": x["url"]} for x in d.get("sources") or [] if x.get("url")]
        dossier = "\n\n".join(f"[{s['title']}] {s['text'][:1600]}" for s in d.get("sources") or [])
    except Exception as e:  # noqa: BLE001
        if log:
            log(f"pesquisa extra falhou ({e}) — seguindo com os fatos da pauta")
    prompt, meta = build_prompt(ch, b, fmt, topic=topic, facts=facts, dossier=dossier, arc=arc, plan=plan, seconds=seconds, rng=rng)
    data = llm.complete_json(prompt, temperature=0.75, required=("beats", "title"), timeout=180)
    ep = normalize(data, b, fmt, meta["words"][1] + 8)
    ep.update(part=meta["part"], episode_style=meta["style"], seconds_target=round(seconds), words=meta["words"],
              topic=topic, idea_id=idea.id if idea else None, sources=srcs)
    if not ep["beats"]:
        raise llm.LLMError("roteiro de episódio sem beats")
    return ep


DEADLINE_WORDS = ("SOBREVIVA", "ANTES", "AGUENTE", "ATÉ", "EM ", "RESISTA", "ESCAPE ANTES", "CHEGUE ANTES")


def _mission(m: dict[str, Any]) -> dict[str, Any]:
    """Prazo só quando a missão é um prazo: o título diz as horas (\"72H\") ou é de corrida contra o tempo."""
    title = str(m.get("title") or "SOBREVIVA").upper()[:28]
    out: dict[str, Any] = {"title": title, "subtitle": str(m.get("subtitle") or "")[:60]}
    hours = m.get("hours") if isinstance(m.get("hours"), (int, float)) and 0 < m["hours"] <= 240 else None
    mins = m.get("minutes") if isinstance(m.get("minutes"), (int, float)) and 0 < m["minutes"] <= 600 else None
    in_title = re.search(r"(\d+)\s*H\b", title)
    if in_title:
        out["hours"] = int(in_title.group(1))
    elif hours and any(w in title for w in DEADLINE_WORDS) and hours <= 96:
        out["hours"] = hours
    elif mins and any(w in title for w in DEADLINE_WORDS):
        out["minutes"] = mins
    return out
