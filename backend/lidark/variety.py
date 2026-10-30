"""Diretor de variedade: cada vídeo sai com estrutura, gancho, título, CTA, duração e ritmo diferentes.

O YouTube recusa/limita canais com conteúdo "inautêntico" (vídeos produzidos em massa, todos no mesmo molde).
Aqui sorteamos — sem repetir os usados recentemente e dando mais peso ao que performa — as escolhas
editoriais de cada roteiro. O plano fica salvo em Script.variety e é respeitado na produção.
"""
from __future__ import annotations

import random
import threading
import time
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
    "biografia": {
        "mood": "emotional cinematic", "series": "Vidas em 3 Atos",
        "name": "Vida em 3 atos", "formats": ("long",),
        "how": "Conte a vida de UMA pessoa real como um filme em 3 atos: (1) quem ela era e o que queria/o que a ameaçava; "
               "(2) a escalada — decisões, conflitos e a grande virada; (3) o desfecho e o legado (o que mudou por causa dela). "
               "Cada CAPÍTULO termina num cliffhanger real (uma decisão no ar, uma ameaça, uma pergunta que o capítulo seguinte "
               "responde). Mostre a pessoa com nome, idade, lugar e motivação; nada de biografia em lista de datas.",
        "graphics": "Use 'dossier' para apresentar a pessoa, 'timeline' na virada de cada ato e 'quote' só com frase real dela. NÃO use 'versus'.",
    },
}

HOOKS = {
    "pergunta": "uma pergunta provocadora e ESPECÍFICA que o espectador não sabe responder (com nome, lugar ou número — nunca 'você já pensou?')",
    "numero": "um número ou dado chocante logo nas primeiras palavras, com o que ele significa",
    "contraintuitivo": "uma afirmação que contraria o que todo mundo aprendeu ou acha (quebra de padrão)",
    "cena": "uma cena narrada no presente, como se o espectador estivesse lá, já no momento de tensão",
    "desafio": "um desafio direto ao espectador (ex.: 'aposto que você erra isso'), que ele só confere assistindo",
    "consequencia": "a consequência surpreendente primeiro, a causa depois (o espectador fica para saber o porquê)",
    "segredo": "algo escondido, esquecido ou proibido revelado (ex.: 'isso ficou fora dos livros por 50 anos') — só se for verdade",
    "stakes": "o que estava em jogo, em uma frase concreta (vidas, um país, um recorde, uma fortuna), antes de qualquer contexto",
    "correcao": "a correção de algo que a escola/o senso comum ensina errado (ex.: 'a escola te ensinou errado: ...'), com a "
                "verdade logo em seguida. SÓ vale se a crença for mesmo comum E as fontes mostrarem a verdade (cada frase será "
                "checada nas fontes); se o tema não tiver um equívoco real, use o estilo 'contraintuitivo' e informe em "
                "\"hook_style_used\"",
}
MYTH_HOOK = "correcao"  # gancho de correção de mito: passa pela checagem frase a frase (content.check_claims)

TITLES = {
    "pergunta": "pergunta curta e intrigante, com um elemento concreto (nome, lugar ou número)",
    "afirmacao": "afirmação forte e direta, sem ponto de interrogação",
    "numero": "começa com um número ou dado concreto",
    "o_dia": "no formato 'O dia em que...' ou 'A vez em que...'",
    "nome": "começa com o nome do personagem/lugar seguido de uma revelação",
    "contraste": "contraste entre duas ideias (ex.: 'Era X, virou Y')",
    "lacuna": "afirmação que esconde a peça-chave (ex.: 'O detalhe que derrubou o Império'), revelada só no vídeo",
    "busca": "no formato que as pessoas DIGITAM na busca, com o termo pesquisado no começo: 'O que foi X?', 'Por que X "
             "aconteceu?' ou 'X: resumo ...' (ex.: 'O que foi a Revolta da Vacina? Resumo para o ENEM') — sem perder a "
             "especificidade",
}
TITLE_FORMATS: dict[str, tuple[str, ...]] = {"busca": ("long",)}  # padrões só de um formato (o resto vale para os dois)

# ---------------------------------------------------------------- abertura do Short (os 2 primeiros segundos)
# A 1ª distribuição do Short depende de "assistiu × deslizou": testamos 3 tipos de abertura, medidos pelo aprendizado.
OPENING_TYPES: dict[str, dict[str, str]] = {
    "impact": {"name": "Frase de impacto",
               "how": "a 1ª frase falada é um soco — o fato/dado mais forte do vídeo, sem contexto; na tela só a legenda "
                      "(\"onscreen\" vazio)"},
    "question": {"name": "Pergunta na tela",
                 "how": "uma PERGUNTA curta e específica aparece ESCRITA na tela (\"onscreen\", até 7 palavras) junto com a "
                        "1ª frase falada; quem lê precisa ficar para saber a resposta"},
    "motion": {"name": "Movimento visual",
               "how": "os 2 primeiros segundos são um MOVIMENTO visual forte descrito em \"motion\" (zoom rápido num detalhe, "
                      "algo caindo/girando/explodindo, revelação de uma imagem) e a fala começa curta, colada na ação"},
}
LOOP_SHARE = 0.4  # fração dos Shorts com loop perfeito (a última frase emenda na primeira); nunca todos

NEXT_CTA = "1"  # estilo que anuncia o próximo vídeo: só com uma pauta real da fila


def next_idea(ch: Channel, current_idea_id: int | None, fmt: str):
    """Pauta que o vídeo vai anunciar como 'próximo': a de maior nota, com fatos confirmados, ainda na fila."""
    from .models import Idea
    with session() as s:
        rows = s.exec(select(Idea).where(Idea.channel_id == ch.id, Idea.status.in_(["new", "approved"]),
                                         Idea.fact_status == "verified")).all()
    rows = [i for i in rows if i.id != current_idea_id and i.score is not None and "prometida" not in (i.tags or [])]
    rows.sort(key=lambda i: (i.format != fmt, -(i.score or 0)))
    return rows[0] if rows else None


CTA_STYLES = [
    "convite para seguir o canal ligado ao tema do vídeo",
    "anúncio do PRÓXIMO VÍDEO (tema exato informado abaixo) + pedido para seguir",
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
    if names:
        # estrutura nova no código: completa só ela com o nome padrão (sem gastar cota) — renomear as séries que já
        # existem quebraria a ligação série → playlist (Channel.playlists) e a maratona entre episódios
        names = {**{k: defaults[k] for k in STRUCTURES if k not in names}, **names}
    else:
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
    return [{"title": r.title, "description": r.description, "hook": r.hook, **(r.variety or {})} for r in rows]


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


# ---------------------------------------------------------------- freio de segurança do YPP
# Política de "conteúdo inautêntico" (jul/2025): canal em que os vídeos saem do mesmo molde perde a monetização.
# Se uma escolha já ocupa 30% dos últimos 10 roteiros do canal, ela sai do sorteio até o histórico se espalhar.
YPP_WINDOW = 10
YPP_MAX_SHARE = 0.3


def _brake(options: list[str], recent: list[str]) -> list[str]:
    """Tira do sorteio as opções que, escolhidas de novo, passariam de 30% dos últimos 10 roteiros."""
    window = [r for r in recent[:YPP_WINDOW - 1] if r]
    if len(window) < 4:
        return options
    cap = YPP_MAX_SHARE * (len(window) + 1)
    ok = [o for o in options if window.count(o) + 1 <= cap]
    return ok or options


def _pick_loop(hist: list[dict[str, Any]], w: dict[str, float] | None, rng: random.Random) -> bool:
    """Loop perfeito em ~40% dos Shorts: o aprendizado inclina (25-55%), mas nunca vira regra — e não sai 3 seguidos."""
    prev = [bool(h.get("loop")) for h in hist if "loop" in h][:5]
    p = LOOP_SHARE
    if w:
        try:
            ratio = (float(w.get("sim", 50)) + 1) / (float(w.get("nao", 50)) + 1)
            p *= max(0.6, min(1.4, ratio))
        except (TypeError, ValueError):
            pass
    p = max(0.25, min(0.55, p))
    if len(prev) >= 2 and prev[0] and prev[1]:
        p = 0.1
    elif len(prev) >= 4 and not any(prev[:4]):
        p = 0.7
    return rng.random() < p


def dimension_options() -> dict[str, list[str]]:
    """Opções de cada dimensão sorteada aqui (o aprendizado lê esta lista; dimensão nova entra sozinha)."""
    return {"structure": list(STRUCTURES), "hook_style": list(HOOKS), "title_style": list(TITLES),
            "cta_style": [str(i) for i in range(len(CTA_STYLES))], "graphics": [d[0] for d in GRAPHIC_DOSES],
            "duration": list(DURATION_BANDS), "grade": LOOK_OPTIONS["grade"], "caption": LOOK_OPTIONS["caption"],
            "intro": LOOK_OPTIONS["intro"], "outro": LOOK_OPTIONS["outro"], "thumb_variant": [str(i) for i in range(8)],
            "opening_type": list(OPENING_TYPES), "loop": ["sim", "nao"]}


# dimensões novas (além das de growth.DIMENSIONS): rótulo, nomes das opções e como ler do Script.variety
EXTRA_DIMENSIONS: dict[str, dict[str, Any]] = {
    "opening_type": {"label": "Abertura do Short (2 s)", "names": {k: v["name"] for k, v in OPENING_TYPES.items()},
                     "get": lambda p: p.get("opening_type")},
    "loop": {"label": "Loop perfeito", "names": {"sim": "Com loop", "nao": "Sem loop"},
             "get": lambda p: None if "loop" not in p else ("sim" if p.get("loop") else "nao")},
}


def _blend(a: dict[str, float] | None, b: dict[str, float] | None, wb: float = 0.5) -> dict[str, float]:
    """Média ponderada de dois mapas {opção: peso} na escala do _pick (50 = neutro); opção só num lado fica com ele."""
    a, b = dict(a or {}), dict(b or {})
    out: dict[str, float] = {}
    for k in set(a) | set(b):
        try:
            if k in a and k in b:
                out[k] = (1 - wb) * float(a[k]) + wb * float(b[k])
            else:
                out[k] = float(a[k] if k in a else b[k])
        except (TypeError, ValueError):
            continue
    return out


def dimension_weights_blend(channel_id: int) -> dict[str, dict[str, float]]:
    """Pesos por dimensão: experimentos do growth.py (médias brutas) + bandit do learning.py (efeitos com incerteza,
    comparando vídeos na mesma idade). Os dois na escala do _pick; o _pick limita o bônus (0,5× a 2×) e a
    anti-repetição continua valendo — o aprendizado só inclina o sorteio, nunca fixa um molde."""
    try:
        from .growth import dimension_weights
        dw = dimension_weights(channel_id) or {}
    except Exception:  # noqa: BLE001
        dw = {}
    try:
        from . import learning  # type: ignore[attr-defined]
        lw = learning.recommend_variety(channel_id) or {}
    except Exception:  # noqa: BLE001 — módulo ausente/sem dados: só os experimentos
        lw = {}
    out: dict[str, dict[str, float]] = {}
    for dim in set(dw) | set(lw):
        # o bandit compara na mesma idade e com incerteza: pesa um pouco mais que a média bruta
        m = _blend(dw.get(dim) if isinstance(dw.get(dim), dict) else None,
                   lw.get(dim) if isinstance(lw.get(dim), dict) else None, 0.6)
        if m:
            out[dim] = {k: max(0.0, min(100.0, v)) for k, v in m.items()}
    return out


def _opening(title: str) -> str:
    return " ".join(re.sub(r"[^\wÀ-ú ]", "", title.lower()).split()[:2])


# ---------------------------------------------------------------- plano do vídeo

# Duração do Short em faixas (segundos, inclusive). Não há duração mínima para monetizar Shorts: a receita vem das
# views engajadas (quem não pula), então Shorts mais curtos tendem a reter melhor — o laboratório confirma por canal.
DURATION_BANDS: dict[str, tuple[int, int]] = {"curto": (30, 38), "medio": (40, 48), "longo": (55, 65)}
DURATION_PRIOR: dict[str, float] = {"curto": 80, "medio": 70, "longo": 30}  # antes de haver dados (50 = neutro)


def duration_band(seconds: Any) -> str | None:
    try:
        s = float(seconds)
    except (TypeError, ValueError):
        return None
    if s <= 0:
        return None
    return "curto" if s <= 38 else ("medio" if s <= 50 else "longo")


_reserved: dict[int, list[tuple[float, dict[str, Any]]]] = defaultdict(list)
_reserve_lock = threading.Lock()
RESERVE_SECONDS = 45 * 60


def plan(ch: Channel, fmt: str) -> dict[str, Any]:
    """Sorteia o plano já reservando as escolhas: roteiros escritos ao mesmo tempo enxergam uns aos outros
    (antes, dois roteiros paralelos podiam sair com o mesmo título/estrutura)."""
    with _reserve_lock:
        t = time.time()
        _reserved[ch.id] = [(ts, p) for ts, p in _reserved[ch.id] if t - ts < RESERVE_SECONDS]
        out = _plan(ch, fmt, [p for _, p in reversed(_reserved[ch.id])])
        _reserved[ch.id].append((t, out))
        return out


def _plan(ch: Channel, fmt: str, pending: list[dict[str, Any]]) -> dict[str, Any]:
    rng = random.Random()
    hist = pending + recent_plans(ch.id)
    dw = dimension_weights_blend(ch.id)  # o que já se provou melhor (experimentos + aprendizado com dados)
    perf = _blend(structure_performance(ch.id), dw.get("structure"))
    structs = [k for k, v in STRUCTURES.items() if fmt in v["formats"]]
    # freio do YPP: estrutura/gancho/título que já passam de 30% dos últimos 10 roteiros ficam de fora do sorteio
    rec_st = [h.get("structure", "") for h in hist]
    structure = _pick(_brake(structs, rec_st), rec_st, 3, perf, rng)
    rec_hook = [h.get("hook_style", "") for h in hist]
    hook = _pick(_brake(list(HOOKS), rec_hook), rec_hook, 2, dw.get("hook_style"), rng)
    # título: evita o esquema mais usado ultimamente (ex.: tudo em pergunta)
    recent_titles = [h["title"] for h in hist if h.get("title")]
    q_share = sum(t.strip().rstrip("#Shorts").strip().endswith("?") for t in recent_titles[:6]) / max(1, len(recent_titles[:6]))
    title_opts = [t for t in TITLES if not (t == "pergunta" and q_share >= 0.5) and fmt in TITLE_FORMATS.get(t, (fmt,))]
    rec_title = [h.get("title_style", "") for h in hist]
    title = _pick(_brake(title_opts, rec_title), rec_title, 2, dw.get("title_style"), rng)
    cta = _pick([str(i) for i in range(len(CTA_STYLES))], [h.get("cta_style", "") for h in hist], 2, dw.get("cta_style"), rng)
    dose = _pick([d[0] for d in GRAPHIC_DOSES], [h.get("graphics", "") for h in hist], 1, dw.get("graphics"), rng)
    out: dict[str, Any] = {"structure": structure, "hook_style": hook, "title_style": title, "cta_style": cta, "graphics": dose}
    if fmt == "short":
        if ch.short_seconds:  # duração fixada no canal: fica perto dela (Short nunca passa de 3 min)
            out["seconds"] = max(15, min(175, ch.short_seconds + rng.choice([-3, -2, 0, 0, 2, 3])))
        else:  # automático: a faixa de duração é um experimento, com prior favorecendo Shorts mais curtos
            band = _pick(list(DURATION_BANDS), [h.get("duration") or duration_band(h.get("seconds")) or "" for h in hist],
                         0, {**DURATION_PRIOR, **(dw.get("duration") or {})}, rng)
            out["seconds"] = rng.randint(*DURATION_BANDS[band])
        out["duration"] = duration_band(out["seconds"])
        # abertura dos 2 primeiros segundos: o roteirista escreve as 3 e o vídeo usa a sorteada (o aprendizado mede
        # quanto cada tipo segura o "assistiu × deslizou")
        shorts_hist = [h for h in hist if h.get("duration") or h.get("opening_type")]
        out["opening_type"] = _pick(list(OPENING_TYPES), [h.get("opening_type", "") for h in shorts_hist], 1,
                                    dw.get("opening_type"), rng)
        out["loop"] = _pick_loop(shorts_hist, dw.get("loop"), rng)
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
    hooks_open = "\n".join(f"  - {h['hook'][:90]}" for h in hist if h.get("hook")) or "  (nenhuma)"
    cta_style = CTA_STYLES[int(p.get("cta_style", 0)) % len(CTA_STYLES)]
    if str(p.get("cta_style")) == NEXT_CTA:
        if p.get("next_title"):
            cta_style += (f'. O PRÓXIMO VÍDEO do canal será sobre: "{p["next_title"]}". Anuncie EXATAMENTE esse tema '
                          "(pode reformular de forma chamativa, sem mudar o assunto). NUNCA invente outro tema")
        else:
            cta_style = CTA_STYLES[0]  # sem pauta confirmada na fila: não promete nada
    chapters = ("" if fmt == "short" else """
- CAPÍTULOS: organize o vídeo em 5 a 8 blocos. A PRIMEIRA cena de cada bloco ganha o campo "chapter" com o título do
  capítulo (2-5 palavras, sem número, com um termo que alguém pesquisaria). A cena 1 também tem "chapter". Cada bloco
  deve ter pelo menos 3 cenas.
- TELA FINAL: depois do CTA o vídeo mostra 20 s de tela final com "assista o próximo" e o botão de inscrição; o CTA
  pode apontar para ela (ex.: "o próximo vídeo está aqui na tela"), sem anunciar um tema que não foi indicado acima.""")
    if fmt == "long":
        chapters += "\n" + episode_block(p)
    else:
        chapters += "\n" + opening_block(p) + "\n" + loop_block(p)
    return f"""VARIEDADE (OBRIGATÓRIO — o canal não pode parecer feito em série):
- ESTRUTURA NARRATIVA DESTE VÍDEO: "{st['name']}". {st['how']} {st['graphics']}
  Adapte a estrutura ao tema (ex.: numa pauta de ciência, "cronologia" = a sequência do que acontece, segundo a segundo);
  NUNCA invente datas, nomes ou fatos só para encaixar na estrutura.
- GANCHO: a primeira frase deve ser {HOOKS.get(p.get('hook_style', ''), 'forte')}.
- TÍTULO: {TITLES.get(p.get('title_style', ''), 'chamativo')}. NÃO comece o título com: {', '.join(repr(o) for o in p.get('avoid_openings', [])) or '(livre)'}.
- CTA final: {cta_style}. NUNCA prometa um "próximo vídeo" além do indicado aqui. Escreva um CTA NOVO com as palavras do canal ({ch.name}), contendo "segue", "siga" ou "inscreva"; inspire-se em "{ch.cta}" sem copiá-lo.
- GRÁFICOS ANIMADOS: {dose} das cenas (o resto com imagens reais).
- Não reutilize frases de efeito, aberturas ou fechamentos dos vídeos recentes.{chapters}
TÍTULOS RECENTES DO CANAL (não imite a forma):
{titles}
ABERTURAS RECENTES (o gancho novo não pode começar igual nem repetir o mesmo truque):
{hooks_open}
DESCRIÇÕES RECENTES (a nova deve começar diferente e ser escrita do zero):
{desc_open}"""


def opening_block(p: dict[str, Any]) -> str:
    """Pedido das 3 aberturas do Short (uma de cada tipo) e qual delas o vídeo usa."""
    cur = p.get("opening_type") if p.get("opening_type") in OPENING_TYPES else "impact"
    kinds = "\n".join(f"    * \"{k}\" ({v['name']}): {v['how']}" for k, v in OPENING_TYPES.items())
    return f"""- ABERTURA (os 2 primeiros segundos decidem "assistiu × deslizou"): escreva em "opening_options" 3 aberturas
  bem diferentes, UMA de cada tipo:
{kinds}
  Cada uma com "text" (a 1ª frase falada, até 12 palavras, verdadeira), "onscreen" (texto na tela, pode ser vazio) e
  "motion" (o movimento visual dos 2 s, pode ser vazio). ESTE vídeo usa a do tipo "{cur}": a cena 1 começa EXATAMENTE
  com o "text" dela, e o "visual" da cena 1 combina com o "motion"/"onscreen" dela."""


def loop_block(p: dict[str, Any]) -> str:
    if p.get("loop"):
        return """- LOOP PERFEITO (este Short emenda o fim no começo): o CTA curto fica no fim da PENÚLTIMA cena. A ÚLTIMA cena
  (marque "loop": true nela) tem UMA frase curta que fica em aberto e se completa com a 1ª frase do vídeo — ao
  recomeçar, a emenda soa como uma frase só (ex.: última "E tudo isso aconteceu porque" → primeira "ninguém sabe como
  era o rosto de Tiradentes."). Sem CTA, sem reticências e sem pausa na última cena; a emenda precisa ser natural."""
    return """- FECHAMENTO: termine no payoff e no CTA (este Short NÃO é em loop: não force eco da 1ª frase no final)."""


def episode_block(p: dict[str, Any]) -> str:
    """Vídeo longo maratonável: o fim puxa o próximo episódio da série (só com pauta real da fila)."""
    series = p.get("series") or "do canal"
    if p.get("next_episode") and p.get("next_title"):
        return (f"- FIM DE EPISÓDIO (série maratonável \"{series}\"): antes do CTA, feche com um gancho para o PRÓXIMO "
                f"EPISÓDIO da série, que será sobre \"{p['next_title']}\" — uma pergunta ou cena em aberto desse tema que dê "
                "vontade de emendar, com palavras novas (nada de \"no próximo vídeo...\" genérico). NUNCA invente outro tema.\n"
                f"- DESCRIÇÃO: diga que o vídeo é um episódio da série \"{series}\" e convide a maratonar a playlist.")
    return (f"- FIM DE EPISÓDIO (série \"{series}\"): o último capítulo fecha a história e convida a continuar na série "
            "(\"tem mais episódios na tela final\"), sem prometer um tema específico.\n"
            f"- DESCRIÇÃO: diga que o vídeo é um episódio da série \"{series}\".")


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
    try:
        risk = ypp_risk(ch.id)
    except Exception:  # noqa: BLE001
        risk = {"risk": "ok", "reasons": []}
    return {
        "ypp_risk": risk,
        "total": len(rows), "planned": len(planned), "score": score, "warnings": warnings,
        "structures": structs, "hooks": dist("hook_style"), "titles": dist("title_style"),
        "grades": dist("grade", src=looks), "captions": dist("caption", src=looks),
        "series": dist("series"), "question_share": round(q_share * 100),
        "durations": [p.get("seconds") for p in planned if p.get("seconds")],
    }


# ---------------------------------------------------------------- risco de "conteúdo inautêntico" (YPP)

_RISK_DIMS = (("structure", "a mesma estrutura narrativa", YPP_MAX_SHARE),
              ("hook_style", "o mesmo tipo de gancho", YPP_MAX_SHARE),
              ("title_style", "o mesmo padrão de título", YPP_MAX_SHARE),
              ("opening_type", "o mesmo tipo de abertura", 0.6))


def _option_name(dim: str, key: str) -> str:
    if dim == "structure":
        return STRUCTURES.get(key, {}).get("name", key)
    if dim == "opening_type":
        return OPENING_TYPES.get(key, {}).get("name", key)
    return key


def ypp_risk(channel_id: int) -> dict[str, Any]:
    """Os últimos 10 roteiros do canal parecem feitos em série? {"risk": "ok|atencao|alto", "reasons": [...]}.

    Mede o que a política de conteúdo inautêntico do YouTube olha: o mesmo molde (estrutura, gancho, título, abertura)
    repetido, títulos que começam igual ou quase iguais. O sorteio (plan) já freia isso; aqui é o alarme do painel."""
    with session() as s:
        rows = s.exec(select(Script).where(Script.channel_id == channel_id).order_by(Script.id.desc())
                      .limit(YPP_WINDOW)).all()
    plans = [r.variety or {} for r in rows]
    reasons: list[str] = []
    level = 0
    for dim, lab, cap in _RISK_DIMS:
        vals = [str(p.get(dim)) for p in plans if p.get(dim) not in (None, "")]
        if len(vals) < 5:
            continue
        top = max(set(vals), key=vals.count)
        share = vals.count(top) / len(vals)
        if share > cap:
            reasons.append(f"{vals.count(top)} dos últimos {len(vals)} roteiros com {lab} "
                           f"({_option_name(dim, top)})")
            level += 2 if share >= max(0.5, cap + 0.2) else 1
    titles = [r.title.replace("#Shorts", "").strip() for r in rows if r.title]
    if len(titles) >= 5:
        op: dict[str, int] = defaultdict(int)
        for t in titles:
            k = _opening(t)
            if k:
                op[k] += 1
        for k, n in op.items():
            if n / len(titles) > YPP_MAX_SHARE:
                reasons.append(f"{n} dos últimos {len(titles)} títulos começam com “{k}”")
                level += 1
        toks = [set(_tokens(t)) for t in titles]
        twins = sum(1 for i in range(len(toks)) for j in range(i + 1, len(toks)) if toks[i] and _jaccard(toks[i], toks[j]) >= 0.5)
        if twins >= 2:
            reasons.append(f"{twins} pares de títulos quase iguais entre os últimos {len(titles)}")
            level += 1
    loops = [bool(p.get("loop")) for p in plans if "loop" in p]
    if len(loops) >= 5 and sum(loops) / len(loops) > 0.7:
        reasons.append(f"{sum(loops)} dos últimos {len(loops)} Shorts em loop (o loop deve ser exceção)")
        level += 1
    risk = "alto" if level >= 3 else "atencao" if level >= 1 else "ok"
    return {"risk": risk, "reasons": reasons, "window": len(rows)}


def overused(channel_id: int, dim: str, extra: list[dict[str, Any]] | None = None) -> set[str]:
    """Opções da dimensão que já passaram do limite de 30% nos últimos roteiros (para quem troca a escolha depois do
    sorteio, como o laboratório de gancho)."""
    vals = [str(h.get(dim) or "") for h in (extra or []) + recent_plans(channel_id, YPP_WINDOW)]
    window = [v for v in vals[:YPP_WINDOW - 1] if v]
    if len(window) < 4:
        return set()
    cap = YPP_MAX_SHARE * (len(window) + 1)
    return {v for v in set(window) if window.count(v) + 1 > cap}
