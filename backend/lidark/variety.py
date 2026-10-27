"""Diretor de variedade: cada vídeo sai com estrutura, gancho, título, CTA, duração e ritmo diferentes.

O YouTube recusa/limita canais com conteúdo "inautêntico" (vídeos produzidos em massa, todos no mesmo molde).
Aqui sorteamos — sem repetir os usados recentemente e dando mais peso ao que performa — as escolhas
editoriais de cada roteiro. O plano fica salvo em Script.variety e é respeitado na produção.
"""
from __future__ import annotations

import random
import re
from collections import defaultdict
from typing import Any

from sqlmodel import select

from .db import session
from .models import Channel, Script

# ---------------------------------------------------------------- estruturas narrativas

STRUCTURES: dict[str, dict[str, Any]] = {
    "mito_verdade": {
        "mood": "curious playful", "series": "Mito ou Verdade?",
        "name": "Mito × Verdade", "formats": ("short", "long"),
        "how": "Abra com a crença popular (o 'mito'), crie dúvida e desmonte com provas, revelando a verdade no clímax.",
        "graphics": "Use 'versus' (mito × verdade) no clímax.",
    },
    "investigacao": {
        "mood": "suspense mystery", "series": "Casos e Enigmas",
        "name": "Investigação", "formats": ("short", "long"),
        "how": "Conte como um caso a ser resolvido: apresente o enigma, vá soltando pistas reais uma a uma e só revele a resposta no final.",
        "graphics": "Prefira 'dossier' para os envolvidos e 'map' para o local do caso. NÃO use 'versus'.",
    },
    "contagem": {
        "mood": "energetic upbeat", "series": "Top 3",
        "name": "Contagem regressiva", "formats": ("short", "long"),
        "how": "Estruture como 3 fatos (no longo: 5 a 7) em ordem crescente de impacto: 'número 3... número 2... e o número 1'. O último é o mais chocante.",
        "graphics": "Use 'list' ou 'counter' para marcar os itens. NÃO use 'versus'.",
    },
    "cronologia": {
        "mood": "epic cinematic", "series": "A História Acelerada",
        "name": "A história em ritmo acelerado", "formats": ("short", "long"),
        "how": "Conte a história do começo ao fim em ordem cronológica, rápida, com datas marcando cada virada, até um desfecho surpreendente.",
        "graphics": "Use 'timeline' pelo menos uma vez. NÃO use 'versus'.",
    },
    "personagem": {
        "mood": "emotional piano", "series": "Personagens Esquecidos",
        "name": "Personagem esquecido", "formats": ("short", "long"),
        "how": "Centre tudo numa pessoa real pouco conhecida (ou no lado desconhecido de alguém famoso): quem era, o que fez, por que foi esquecida.",
        "graphics": "Use 'dossier' para apresentar a pessoa e 'quote' se houver frase real dela. NÃO use 'versus'.",
    },
    "detalhe": {
        "mood": "curious mystery", "series": "Detalhes Escondidos",
        "name": "O detalhe escondido", "formats": ("short", "long"),
        "how": "Comece por algo familiar (um objeto, palavra, costume, imagem ou lugar famoso) e revele a história real e surpreendente por trás desse detalhe.",
        "graphics": "Prefira imagens reais fortes do objeto/lugar; um 'counter' ou 'map' se houver dado. NÃO use 'versus'.",
    },
    "in_media_res": {
        "mood": "tension dramatic", "series": "No Olho do Furacão",
        "name": "Começa no clímax", "formats": ("short", "long"),
        "how": "A primeira cena já é o momento mais dramático da história; depois volte no tempo ('mas como chegamos aqui?') e explique até fechar o círculo.",
        "graphics": "Use 'timeline' ou 'map' para situar o espectador depois do clímax. NÃO use 'versus'.",
    },
    "pergunta": {
        "mood": "curious upbeat", "series": "Pergunta Direta",
        "name": "Pergunta direta", "formats": ("short",),
        "how": "Responda a UMA pergunta que o público realmente faz, indo direto ao ponto, com 2 ou 3 provas concretas e uma conclusão inesperada.",
        "graphics": "Use 'list' com as provas ou 'counter' com o número-chave. NÃO use 'versus'.",
    },
    "comparacao": {
        "mood": "energetic curious", "series": "Questão de Escala",
        "name": "Comparação de escala", "formats": ("short", "long"),
        "how": "Explique o assunto comparando com algo do dia a dia do brasileiro (tamanho, preço, tempo, distância, população) para dar noção de escala.",
        "graphics": "Use 'counter' com os números comparados. NÃO use 'versus'.",
    },
    "e_se": {
        "mood": "epic dramatic", "series": "E se...?",
        "name": "E se...?", "formats": ("long",),
        "how": "Parta de uma pergunta 'e se...' sobre um momento decisivo, mas responda SÓ com fatos reais: o que quase aconteceu, o que de fato aconteceu e as consequências documentadas. Nada inventado.",
        "graphics": "Use 'timeline' para o que de fato aconteceu. NÃO use 'versus'.",
    },
}

HOOKS = {
    "pergunta": "uma pergunta provocadora que o espectador não sabe responder",
    "numero": "um número ou dado chocante logo na primeira frase",
    "contraintuitivo": "uma afirmação que contraria o que todo mundo acha",
    "cena": "uma cena narrada no presente, como se o espectador estivesse lá",
    "desafio": "um desafio direto ao espectador (ex.: 'aposto que você erra isso')",
    "consequencia": "a consequência surpreendente primeiro, a causa depois",
}

TITLES = {
    "pergunta": "pergunta curta e intrigante",
    "afirmacao": "afirmação forte e direta, sem ponto de interrogação",
    "numero": "começa com um número ou dado",
    "o_dia": "no formato 'O dia em que...' ou 'A vez em que...'",
    "nome": "começa com o nome do personagem/lugar seguido de uma revelação",
    "contraste": "contraste entre duas ideias (ex.: 'Era X, virou Y')",
}

CTA_STYLES = [
    "convite para seguir o canal ligado ao tema do vídeo",
    "promessa do que vem no próximo vídeo + pedido para seguir",
    "pergunta para o público responder nos comentários + seguir",
    "pedido para mandar o vídeo para alguém que precisa saber disso",
    "pedido curto e direto para se inscrever",
]

GRAPHIC_DOSES = [("poucas", "15 a 25%"), ("médias", "30 a 40%"), ("muitas", "45 a 55%")]

# ---------------------------------------------------------------- look visual (ver lidark/render/look.py)

LOOK_OPTIONS = {
    "grade": ["neutro", "quente", "frio", "contraste", "sepia", "filme"],
    "caption": ["classic", "highlight", "karaoke", "bold"],
    "caption_anim": ["pop", "rise", "fade", "snap"],
    "intro": ["typed", "words", "band", "punch"],
    "outro": ["classic", "handle", "minimal"],
}
TRANSITION_SETS = [
    ["whip", "zoom", "flash"], ["fade", "blur", "slide_up"], ["push", "wipe", "circle"],
    ["glitch", "whip", "push"], ["zoom", "circle", "fade", "flash"], ["wipe", "blur", "zoom"],
]


def pick_look(ch: Channel, hist: list[dict[str, Any]], rng: random.Random,
              dw: dict[str, dict[str, float]] | None = None) -> dict[str, Any]:
    dw = dw or {}
    prev = [h.get("look") or {} for h in hist]
    grades = list(LOOK_OPTIONS["grade"])
    if not any(w in (ch.niche or "").lower() for w in ("hist", "passado", "antig", "mito")):
        grades.remove("sepia")  # sépia só combina com canal de história
    look: dict[str, Any] = {"grade": _pick(grades, [p.get("grade", "") for p in prev], 2, dw.get("grade"), rng)}
    for key in ("caption", "caption_anim", "intro", "outro"):
        look[key] = _pick(LOOK_OPTIONS[key], [p.get(key, "") for p in prev], 1, dw.get(key), rng)
    look["grain"] = 0.06 if look["grade"] == "filme" else (0.035 if rng.random() < 0.3 else 0.0)
    look["caption_words"] = rng.choice([3, 4, 4, 5])
    look["caption_shift"] = rng.choice([-50, 0, 0, 40])
    ts = _pick([str(i) for i in range(len(TRANSITION_SETS))], [str(p.get("tset", "")) for p in prev], 2, None, rng)
    look["tset"] = ts
    look["transitions"] = TRANSITION_SETS[int(ts)]
    look["mascot"] = {
        "entry": rng.choice(["side", "drop", "rise", "late"]),
        "side": rng.choice(["mixed", "mixed", "left", "right"]),
        "stay": rng.choice([0.0, 0.25, 0.5]),
        "hide": rng.random() < 0.4,
        "scale": rng.choice([0.9, 1.0, 1.0, 1.1]),
        "outro": rng.choice(["center", "center", "stay"]),
    }
    return look


def series_names(ch: Channel) -> dict[str, str]:
    """Nome de série para cada estrutura, adaptado ao nicho do canal (gerado uma vez pela IA)."""
    names = dict(ch.series or {})
    if all(k in names for k in STRUCTURES):
        return names
    defaults = {k: v["series"] for k, v in STRUCTURES.items()}
    try:
        from . import llm
        data = llm.complete_json(
            f"Canal do YouTube: {ch.name} — nicho: {ch.niche}. Para cada formato abaixo, crie o nome de uma SÉRIE/playlist "
            f"curta (2-4 palavras, em {ch.language or 'português'}), chamativa e coerente com o nicho.\n"
            + "\n".join(f"- {k}: {v['name']} (ex.: {v['series']})" for k, v in STRUCTURES.items())
            + '\nResponda JSON: {"series": {"mito_verdade": "...", ...}}', temperature=0.6)
        got = data.get("series", {}) if isinstance(data, dict) else {}
        names = {k: str(got.get(k) or defaults[k])[:40] for k in STRUCTURES}
    except Exception:  # noqa: BLE001
        names = defaults
    from .db import session as _s
    with _s() as s:
        db = s.get(Channel, ch.id)
        if db:
            db.series = names
            s.add(db)
            s.commit()
    return names


# ---------------------------------------------------------------- histórico

def recent_plans(channel_id: int, limit: int = 12) -> list[dict[str, Any]]:
    with session() as s:
        rows = s.exec(select(Script).where(Script.channel_id == channel_id).order_by(Script.id.desc()).limit(limit)).all()
    return [{"title": r.title, "description": r.description, **(r.variety or {})} for r in rows]


def structure_performance(channel_id: int) -> dict[str, float]:
    """Desempenho médio (0-100) de cada estrutura narrativa nos vídeos publicados."""
    from .analytics import performance_table
    from .models import Video
    try:
        rows = performance_table(channel_id)
    except Exception:  # noqa: BLE001
        return {}
    acc: dict[str, list[float]] = defaultdict(list)
    with session() as s:
        for r in rows:
            vid = r.get("video_id")
            v = s.get(Video, vid) if isinstance(vid, int) else None
            sc = s.get(Script, v.script_id) if v else None
            st = (sc.variety or {}).get("structure") if sc else None
            if st and r.get("perf") is not None:
                acc[st].append(float(r["perf"]))
    return {k: sum(v) / len(v) for k, v in acc.items() if v}


def _pick(options: list[str], recent: list[str], avoid_last: int, weights: dict[str, float] | None = None,
          rng: random.Random | None = None) -> str:
    rng = rng or random.Random()
    pool = [o for o in options if o not in recent[:avoid_last]] or options
    # quanto mais tempo sem usar, maior a chance; desempenho real dá um bônus (sem nunca zerar a exploração)
    def w(o: str) -> float:
        age = recent.index(o) if o in recent else len(recent) + 2
        bonus = 1.0 + max(-0.5, min(1.0, ((weights or {}).get(o, 50) - 50) / 50))
        return (1 + age) * bonus
    return rng.choices(pool, weights=[w(o) for o in pool])[0]


def _opening(title: str) -> str:
    return " ".join(re.sub(r"[^\wÀ-ú ]", "", title.lower()).split()[:2])


# ---------------------------------------------------------------- plano do vídeo

def plan(ch: Channel, fmt: str) -> dict[str, Any]:
    rng = random.Random()
    hist = recent_plans(ch.id)
    perf = structure_performance(ch.id)
    try:
        from .growth import dimension_weights
        dw = dimension_weights(ch.id)  # o que já se provou melhor nos vídeos publicados
    except Exception:  # noqa: BLE001
        dw = {}
    structs = [k for k, v in STRUCTURES.items() if fmt in v["formats"]]
    structure = _pick(structs, [h.get("structure", "") for h in hist], 3, perf, rng)
    hook = _pick(list(HOOKS), [h.get("hook_style", "") for h in hist], 2, dw.get("hook_style"), rng)
    # título: evita o esquema mais usado ultimamente (ex.: tudo em pergunta)
    recent_titles = [h["title"] for h in hist if h.get("title")]
    q_share = sum(t.strip().rstrip("#Shorts").strip().endswith("?") for t in recent_titles[:6]) / max(1, len(recent_titles[:6]))
    title_opts = [t for t in TITLES if not (t == "pergunta" and q_share >= 0.5)]
    title = _pick(title_opts, [h.get("title_style", "") for h in hist], 2, dw.get("title_style"), rng)
    cta = _pick([str(i) for i in range(len(CTA_STYLES))], [h.get("cta_style", "") for h in hist], 2, None, rng)
    dose = _pick([d[0] for d in GRAPHIC_DOSES], [h.get("graphics", "") for h in hist], 1, dw.get("graphics"), rng)
    out: dict[str, Any] = {"structure": structure, "hook_style": hook, "title_style": title, "cta_style": cta, "graphics": dose}
    if fmt == "short":
        base = max(61, ch.short_seconds or 65)
        out["seconds"] = base + rng.choice([0, 0, 3, 6, 9, 12])
    try:  # variação leve de ritmo da voz (±3%), imperceptível como mudança de voz
        cur = int((ch.voice_rate or "+0%").strip().rstrip("%"))
        out["voice_rate"] = f"{cur + rng.choice([-3, -2, 0, 0, 2, 3]):+d}%"
    except ValueError:
        pass
    templates = [t for t in (ch.templates or []) if t in ("ouro", "livre")]
    if len(templates) > 1:
        out["template"] = _pick(templates, [h.get("template", "") for h in hist], 1, None, rng)
    st = STRUCTURES[structure]
    out["music_mood"] = st["mood"]
    out["look"] = pick_look(ch, hist, rng, dw)
    try:
        out["series"] = series_names(ch).get(structure) or st["series"]
    except Exception:  # noqa: BLE001
        out["series"] = st["series"]
    out["thumb_variant"] = _pick([str(i) for i in range(8)], [str(h.get("thumb_variant", "")) for h in hist], 3,
                                 dw.get("thumb_variant"), rng)
    out["avoid_openings"] = sorted({_opening(t) for t in recent_titles[:10] if t})
    return out


def prompt_block(ch: Channel, p: dict[str, Any], fmt: str) -> str:
    """Instruções de variedade que entram no prompt do roteiro."""
    st = STRUCTURES.get(p.get("structure", ""), STRUCTURES["mito_verdade"])
    dose = dict(GRAPHIC_DOSES).get(p.get("graphics", ""), "30 a 40%")
    hist = recent_plans(ch.id, 8)
    titles = "\n".join(f"  - {h['title']}" for h in hist if h.get("title")) or "  (nenhum)"
    desc_open = "\n".join(f"  - {h['description'][:70]}" for h in hist if h.get("description")) or "  (nenhuma)"
    cta_style = CTA_STYLES[int(p.get("cta_style", 0)) % len(CTA_STYLES)]
    chapters = ("" if fmt == "short" else """
- CAPÍTULOS: organize o vídeo em 5 a 8 blocos. A PRIMEIRA cena de cada bloco ganha o campo "chapter" com o título do
  capítulo (2-5 palavras, sem número). A cena 1 também tem "chapter". Cada bloco deve ter pelo menos 3 cenas.""")
    return f"""VARIEDADE (OBRIGATÓRIO — o canal não pode parecer feito em série):
- ESTRUTURA NARRATIVA DESTE VÍDEO: "{st['name']}". {st['how']} {st['graphics']}
- GANCHO: a primeira frase deve ser {HOOKS.get(p.get('hook_style', ''), 'forte')}.
- TÍTULO: {TITLES.get(p.get('title_style', ''), 'chamativo')}. NÃO comece o título com: {', '.join(repr(o) for o in p.get('avoid_openings', [])) or '(livre)'}.
- CTA final: {cta_style}. Escreva um CTA NOVO com as palavras do canal ({ch.name}), contendo "segue", "siga" ou "inscreva"; inspire-se em "{ch.cta}" sem copiá-lo.
- GRÁFICOS ANIMADOS: {dose} das cenas (o resto com imagens reais).
- Não reutilize frases de efeito, aberturas ou fechamentos dos vídeos recentes.{chapters}
TÍTULOS RECENTES DO CANAL (não imite a forma):
{titles}
DESCRIÇÕES RECENTES (a nova deve começar diferente e ser escrita do zero):
{desc_open}"""


def label(p: dict[str, Any] | None) -> str:
    return STRUCTURES.get((p or {}).get("structure", ""), {}).get("name", "")


# ---------------------------------------------------------------- trava anti-repetição

_STOP = set("a o as os um uma de da do das dos e é em no na nos nas que por para pra com como se sua seu mais foi era ao à "
            "isso essa esse este esta ele ela eles elas você voce não nao mas ou the of".split())


def _tokens(txt: str) -> list[str]:
    return [w for w in re.sub(r"[^\wÀ-ú ]", " ", (txt or "").lower()).split() if w not in _STOP and len(w) > 2]


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / max(1, len(a | b))


def _shingles(txt: str, n: int = 6) -> set[str]:
    w = re.sub(r"[^\wÀ-ú ]", " ", (txt or "").lower()).split()
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def repetition_problems(channel_id: int, title: str, hook: str, scenes: list[dict[str, Any]],
                        exclude_id: int | None = None, limit: int = 30) -> list[str]:
    """Compara um roteiro novo com os recentes do canal. Devolve os problemas encontrados (vazio = ok)."""
    with session() as s:
        q = select(Script).where(Script.channel_id == channel_id).order_by(Script.id.desc()).limit(limit + 1)
        rows = [r for r in s.exec(q).all() if r.id != exclude_id][:limit]
    probs: list[str] = []
    t_new = set(_tokens(title))
    body = " ".join(x.get("text", "") for x in scenes)
    sh_new = _shingles(body)
    hook_open = " ".join(_tokens(hook)[:3])
    phrase_hits: set[str] = set()
    for r in rows:
        if t_new and _jaccard(t_new, set(_tokens(r.title))) >= 0.5:
            probs.append(f"o tema/título está parecido demais com “{r.title}”")
        if hook_open and hook_open == " ".join(_tokens(r.hook)[:3]):
            probs.append(f"o gancho começa igual ao de “{r.title}”")
        # frases de efeito reaproveitadas (ignora o CTA, que é sempre parecido)
        old = " ".join(x.get("text", "") for x in (r.scenes or [])[:-1])
        phrase_hits |= sh_new & _shingles(old)
    if len(phrase_hits) >= 3:
        probs.append("frases repetidas de vídeos anteriores: " + "; ".join(f"“{p}”" for p in sorted(phrase_hits)[:4]))
    return list(dict.fromkeys(probs))[:5]


# ---------------------------------------------------------------- índice de variedade (painel)

def report(ch: Channel, n: int = 20) -> dict[str, Any]:
    with session() as s:
        rows = s.exec(select(Script).where(Script.channel_id == ch.id).order_by(Script.id.desc()).limit(n)).all()
    plans = [r.variety or {} for r in rows]
    planned = [p for p in plans if p.get("structure")]

    def dist(key: str, names: dict | None = None, src: list | None = None) -> list[dict[str, Any]]:
        c: dict[str, int] = defaultdict(int)
        for p in (src if src is not None else planned):
            v = p.get(key)
            if v not in (None, ""):
                c[str(v)] += 1
        return sorted(({"key": k, "label": (names or {}).get(k, k), "count": v} for k, v in c.items()), key=lambda x: -x["count"])

    titles = [r.title for r in rows]
    q_share = sum(t.replace("#Shorts", "").strip().endswith("?") for t in titles) / max(1, len(titles))
    openings: dict[str, int] = defaultdict(int)
    for t in titles:
        openings[_opening(t)] += 1
    rep_open = [k for k, v in openings.items() if v >= 3 and k]
    looks = [p.get("look") or {} for p in planned]
    structs = dist("structure", {k: v["name"] for k, v in STRUCTURES.items()})
    warnings = []
    if planned and structs and structs[0]["count"] / len(planned) > 0.4 and len(planned) >= 5:
        warnings.append(f"{structs[0]['label']} em {structs[0]['count']} dos últimos {len(planned)} roteiros")
    if q_share > 0.5 and len(titles) >= 4:
        warnings.append(f"{round(q_share * 100)}% dos títulos são perguntas")
    for o in rep_open:
        warnings.append(f"{openings[o]} títulos começam com “{o}”")
    # nota 0-100: quanto mais espalhadas as escolhas, maior
    def spread(d: list[dict[str, Any]], total: int, options: int) -> float:
        if not total or not d:
            return 0.0
        return min(1.0, len(d) / min(options, total)) * (1 - max(0.0, d[0]["count"] / total - 0.35))
    parts = [spread(structs, len(planned), len(STRUCTURES)),
             spread(dist("hook_style"), len(planned), len(HOOKS)),
             spread(dist("title_style"), len(planned), len(TITLES)),
             spread(dist("grade", src=looks), len(looks), len(LOOK_OPTIONS["grade"])),
             1 - max(0.0, q_share - 0.3)]
    score = round(100 * sum(parts) / len(parts)) if planned else None
    return {
        "total": len(rows), "planned": len(planned), "score": score, "warnings": warnings,
        "structures": structs, "hooks": dist("hook_style"), "titles": dist("title_style"),
        "grades": dist("grade", src=looks), "captions": dist("caption", src=looks),
        "series": dist("series"), "question_share": round(q_share * 100),
        "durations": [p.get("seconds") for p in planned if p.get("seconds")],
    }
