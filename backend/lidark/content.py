"""Inteligência editorial: geração de pautas, nota 0-100, roteiro, checagem de fatos e revisão.

Os prompts seguem a prática atual dos canais que crescem no YouTube (gancho de 1-2 s, arquitetura de retenção com
re-ganchos e payoff, título curto com lacuna de curiosidade e verdade, thumbnail que completa o título) e se apoiam
no próprio canal: o aprendizado com dados (learning.py, quando existir), os títulos/ganchos que mais e menos
renderam e o plano de variedade de cada vídeo (variety.py — nunca um molde fixo).
"""
from __future__ import annotations

import json
import logging
import math
import threading
import time
from datetime import date
from typing import Any

from sqlmodel import select

from . import llm, research
from .db import session
from .models import Channel, Idea, Insight, Script

log = logging.getLogger("lidark.content")

WORDS_PER_SECOND = 2.7  # narração rápida pt-BR de shorts


def channel_brief(ch: Channel) -> str:
    return (
        f"CANAL: {ch.name}\nNICHO: {ch.niche}\nPÚBLICO: {ch.audience}\nIDIOMA: {ch.language}\n"
        f"TOM: {ch.tone}\nDESCRIÇÃO: {ch.description}\nGUIA EDITORIAL:\n{ch.editorial_guide}"
    )


def is_enem_channel(ch: Channel) -> bool:
    return "enem" in f"{ch.niche} {ch.editorial_guide} {ch.audience}".lower()


# ================================================================ aprendizado (dados do próprio canal)

def _learning(channel_id: int, purpose: str) -> str:
    """Orientação baseada em dados do módulo de aprendizado (opcional: sem ele, string vazia)."""
    try:
        from . import learning  # type: ignore[attr-defined]
        txt = learning.prompt_context(channel_id, purpose)
        return str(txt or "").strip()
    except Exception:  # noqa: BLE001 — módulo ausente ou sem dados: segue sem
        return ""


def predict(channel_id: int, title: str, hook: str = "", fmt: str = "short") -> dict[str, Any] | None:
    """Previsão de desempenho do módulo de aprendizado; None se indisponível."""
    try:
        from . import learning  # type: ignore[attr-defined]
        r = learning.predict(channel_id, title, hook, fmt)
        if (isinstance(r, dict) and isinstance(r.get("score"), (int, float)) and not math.isnan(float(r["score"]))
                and r.get("confidence") != "nenhuma"):  # sem dados o modelo devolve 50 fixo: não pesa
            return r
    except Exception:  # noqa: BLE001
        pass
    return None


def pred_weight(pred: dict[str, Any] | None, top: float = 0.45) -> float:
    """Quanto a previsão pesa na mistura com a nota da IA, pela confiança do modelo (palpite pesa pouco)."""
    if not pred:
        return 0.0
    return {"boa": top, "alta": top, "moderada": top * 0.75, "média": top * 0.75}.get(str(pred.get("confidence")), top * 0.4)


def blend_pred(base: float, pred: dict[str, Any] | None, top: float = 0.45) -> int:
    w = pred_weight(pred, top)
    return round((1 - w) * base + w * max(0.0, min(100.0, float(pred["score"])))) if w else round(base)


_perf_cache: dict[int, tuple[float, list[dict[str, Any]]]] = {}
_perf_lock = threading.Lock()


def _perf_rows(channel_id: int) -> list[dict[str, Any]]:
    """performance_table com cache de 2 min (a nota de cada pauta de um lote consulta o mesmo histórico)."""
    with _perf_lock:
        hit = _perf_cache.get(channel_id)
        if hit and time.time() - hit[0] < 120:
            return hit[1]
    try:
        from .analytics import performance_table
        rows = performance_table(channel_id)
    except Exception:  # noqa: BLE001
        rows = []
    with _perf_lock:
        _perf_cache[channel_id] = (time.time(), rows)
    return rows


def _hooks_by_video(rows: list[dict[str, Any]]) -> dict[Any, str]:
    from .models import Video
    out: dict[Any, str] = {}
    with session() as s:
        for r in rows:
            vid = r.get("video_id")
            v = s.get(Video, vid) if isinstance(vid, int) else None
            sc = s.get(Script, v.script_id) if v else None
            if sc and sc.hook:
                out[vid] = sc.hook.strip()
    return out


def performance_examples(channel_id: int, n_top: int = 5, n_bottom: int = 3) -> dict[str, list[dict[str, Any]]]:
    """Vencedores e perdedores do canal (título, gancho, views, retenção) — few-shot dos prompts."""
    rows = [r for r in _perf_rows(channel_id) if r.get("title")]
    if len(rows) < 3:
        return {"top": [], "bottom": []}
    ranked = sorted(rows, key=lambda r: r.get("perf") or 0, reverse=True)
    top = ranked[:n_top]
    bottom = [r for r in ranked[-n_bottom:] if r not in top] if len(ranked) >= n_top + 2 else []
    hooks = _hooks_by_video(top + bottom)

    def item(r: dict[str, Any]) -> dict[str, Any]:
        return {"title": str(r["title"]).replace("#Shorts", "").replace("#shorts", "").strip(), "views": r.get("views", 0),
                "retention": round(float(r.get("retention") or 0)), "perf": r.get("perf"), "hook": hooks.get(r.get("video_id"), "")}
    return {"top": [item(r) for r in top], "bottom": [item(r) for r in bottom]}


def examples_block(channel_id: int, purpose: str = "title") -> str:
    """Few-shot com os títulos/ganchos do próprio canal que mais e menos renderam."""
    ex = performance_examples(channel_id)
    if not ex["top"]:
        return ""
    if purpose == "hook":
        tops = [e for e in ex["top"] if e["hook"]]
        lines = [f"- \"{e['hook']}\" ({e['views']} views, retenção {e['retention']}%)" for e in tops]
        flops = [f"- \"{e['hook']}\" ({e['views']} views)" for e in ex["bottom"] if e["hook"]]
        if not lines:
            return ""
        return ("ABERTURAS QUE MAIS SEGURARAM O PÚBLICO NESTE CANAL (entenda o mecanismo, NÃO copie as palavras):\n"
                + "\n".join(lines) + ("\nABERTURAS QUE FRACASSARAM (evite o mecanismo):\n" + "\n".join(flops) if flops else ""))
    lines = [f"- \"{e['title']}\" → {e['views']} views" for e in ex["top"]]
    flops = [f"- \"{e['title']}\" → {e['views']} views" for e in ex["bottom"]]
    return ("TÍTULOS QUE MAIS TROUXERAM VIEWS NESTE CANAL (aprenda o padrão — assunto, lacuna, especificidade —, não copie):\n"
            + "\n".join(lines) + ("\nTÍTULOS QUE FRACASSARAM (evite o padrão):\n" + "\n".join(flops) if flops else ""))


def learning_context(channel_id: int, limit: int = 8, purpose: str = "script") -> str:
    """Resumo do que funcionou/não funcionou — o 'aprendizado' do canal."""
    with session() as s:
        insights = s.exec(select(Insight).where(Insight.channel_id == channel_id, Insight.kind != "retention")
                          .order_by(Insight.created_at.desc()).limit(5)).all()
        retention = s.exec(select(Insight).where(Insight.channel_id == channel_id, Insight.kind == "retention")
                           .order_by(Insight.created_at.desc()).limit(6)).all()
    rows = _perf_rows(channel_id)
    parts = []
    data_guide = _learning(channel_id, purpose)
    if data_guide:
        parts.append("APRENDIZADO COM OS DADOS REAIS DO CANAL (prioridade máxima — siga):\n" + data_guide)
    if rows:
        top = sorted(rows, key=lambda r: r["perf"], reverse=True)
        hooks = _hooks_by_video(top[:limit // 2]) if purpose in ("script", "hook") else {}
        fmt = lambda r: (f"- \"{r['title']}\" → {r['views']} views, {r['likes']} curtidas, retenção {r['retention']:.0f}% "  # noqa: E731
                         f"(desempenho {r['perf']}/100, nota prevista {r['predicted']})"
                         + (f" · abertura: \"{hooks[r['video_id']][:140]}\"" if r.get("video_id") in hooks else ""))
        parts.append("VÍDEOS QUE MAIS PERFORMARAM:\n" + "\n".join(fmt(r) for r in top[:limit // 2]))
        if len(top) > 4:
            parts.append("VÍDEOS QUE MENOS PERFORMARAM:\n" + "\n".join(fmt(r) for r in top[-(limit // 2):]))
    if insights:
        parts.append("APRENDIZADOS:\n" + "\n".join(f"- {i.text}" for i in insights))
    if retention:
        parts.append("LIÇÕES DE RETENÇÃO (dados reais de quanto o público assiste — siga à risca):" + chr(10) +
                     chr(10).join(f"- {i.text}" for i in retention))
    try:  # regras calculadas em código a partir das quedas por cena (complementam as lições da IA)
        from .retention import retention_rules_prompt
        rules = retention_rules_prompt(channel_id)
        if rules:
            parts.append(rules)
    except Exception:  # noqa: BLE001
        log.exception("regras de retenção")
    try:
        from .growth import experiments
        lessons = experiments(channel_id).get("lessons", [])
        if lessons:
            parts.append("RESULTADOS DOS EXPERIMENTOS DO CANAL (favoreça o que rende mais):" + chr(10) +
                         chr(10).join(f"- {x}" for x in lessons[:6]))
    except Exception:  # noqa: BLE001
        pass
    from .variety import STRUCTURES, structure_performance
    sp = structure_performance(channel_id)
    if len(sp) >= 2:
        parts.append("DESEMPENHO POR ESTRUTURA NARRATIVA (0-100):\n" + "\n".join(
            f"- {STRUCTURES[k]['name']}: {v:.0f}" for k, v in sorted(sp.items(), key=lambda x: -x[1]) if k in STRUCTURES))
    return "\n\n".join(parts) or "(ainda sem histórico de desempenho)"


def timing_context(ch: Channel) -> str:
    """O 'momento' da pauta: data de hoje e janelas de busca (campanha de revisão/correção do ENEM)."""
    today = date.today()
    dias = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
    lines = [f"HOJE: {today:%d/%m/%Y} ({dias[today.weekday()]})."]
    if is_enem_channel(ch):
        try:
            from .growth import ENEM_DAY
        except Exception:  # noqa: BLE001
            ENEM_DAY = date(2026, 11, 8)
        left = (ENEM_DAY - today).days
        if 0 <= left <= 45:
            lines.append(f"ENEM 2026: o 1º dia (Ciências Humanas) é em {ENEM_DAY:%d/%m} — faltam {left} dia(s). O público está "
                         "buscando REVISÃO de História agora ('o que mais cai no enem', 'revisão enem história', nomes dos "
                         "temas). Revisão rápida, memorável e com 'como cai na prova' tem o maior potencial do ano.")
        elif -14 <= left < 0:
            lines.append(f"O 1º dia do ENEM 2026 foi em {ENEM_DAY:%d/%m}: o público está buscando CORREÇÃO — as questões de "
                         "História que caíram, o contexto por trás delas e a resposta explicada (só fatos confirmados).")
    else:
        lines.append("Aniversários de eventos desta semana, notícias recentes do nicho e datas próximas dão bônus de 'momento'.")
    return "\n".join(lines)


# ================================================================ manual de YouTube (entra nos prompts)

HOOK_RULES = """GANCHO (a 1ª frase decide se a pessoa para de rolar — 1 a 2 segundos):
- Até 12 palavras faladas. Começa no CONFLITO, no número ou na imagem concreta — nunca em contexto, apresentação ou "neste vídeo".
- Use pelo menos 2 destes gatilhos: quebra de padrão (algo que soa errado/impossível), lacuna de curiosidade (pergunta que
  só o fim responde), stakes (o que estava em jogo: vidas, dinheiro, um país, um recorde), especificidade (nome, data, número).
- Precisa ser VERDADE e combinar com o título/thumbnail (quem clicou confirma em 2 s que está no vídeo certo). Se o vídeo
  desmonta um exagero ou mito, o gancho o apresenta como crença ("todo mundo acha que..."), nunca como fato.
- Números e anos em ALGARISMOS ("6 milhões", "1938").
- TESTE DO GENÉRICO: se a frase serviria para 10 vídeos diferentes, ela é vaga — reescreva com o detalhe que só ESTE vídeo tem.
  Vago: "A história de Tiradentes esconde um mistério incrível." Concreto: "Ninguém sabe como era o rosto de Tiradentes."
  Vago: "Soprar o café ativa um processo físico invisível." Concreto: o que exatamente acontece, com o detalhe surpreendente.
- Proibido: "Olá", "Fala, galera", "Você sabia que...", "Neste vídeo", "Hoje vamos falar", pergunta genérica ("já pensou?")."""

RETENTION_SHORT = """ARQUITETURA DE RETENÇÃO (Short):
- Cena 1 = gancho; cena 2 confirma a promessa e abre a PERGUNTA CENTRAL que só o final responde (open loop).
- RE-GANCHO a cada 2 cenas (~5-8 s): virada, número novo, contradição, "só que...", "e piorou", "mas o detalhe é outro" —
  varie as palavras; nunca a mesma muleta duas vezes no roteiro.
- Escada de tensão: cada fato mais forte que o anterior; o mais surpreendente fica para o fim (PAYOFF claro e satisfatório).
- Zero gordura: sem introdução, sem resumo do que vai ser dito, sem repetir informação, sem frase morna. Se uma frase pode
  sair sem perder nada, ela sai.
- LOOP para o replay: a última frase da história (logo antes do CTA) ecoa a imagem/palavra do gancho, para o começo do
  vídeo parecer a continuação do fim."""

RETENTION_LONG = """ARQUITETURA DE RETENÇÃO (vídeo longo — os primeiros 30 s decidem a curva inteira):
- COLD OPEN (0-30 s): comece no momento mais intrigante, sem vinheta e sem "olá"; em até 4 frases diga o que está em jogo
  e PROMETA o que o espectador vai entender no fim (e cumpra). Confirme logo o título/thumbnail.
- CAPÍTULOS como episódios: cada um abre com uma pergunta e termina com uma revelação + um gancho para o próximo
  ("mas isso ainda não explica por que..."). Nada de capítulo que só "contextualiza".
- RE-GANCHOS a cada ~45-60 s (virada, dado chocante, "e é aqui que tudo muda"); um re-gancho FORTE por volta de 1/3 e de 2/3
  do vídeo, onde a curva de retenção costuma cair.
- Ritmo: alterne trechos de narração rápida com uma frase curta e seca de impacto; personagens com nome e motivação.
- O maior payoff fica para o último capítulo; termine logo depois dele (sem recapitulação longa)."""

TTS_RULES = """NARRAÇÃO PARA VOZ SINTÉTICA (português do Brasil falado):
- Frases de 5 a 16 palavras, uma ideia por frase. Prefira ponto final a vírgulas em sequência.
- Escreva como se fala, no TOM do canal: voz ativa, verbos fortes, "você" para puxar o espectador para dentro da cena.
- Nada de parênteses, travessão de aposto, abreviações ("séc.", "aprox.", "EUA" → escreva "século", "cerca de", "Estados
  Unidos"), barras ou símbolos (/, &, +). Sigla só se o público conhece ou se for explicada na mesma frase.
- Anos e números em ALGARISMOS (1942, 25 mil, 10%), nunca por extenso — a narração lê certo e a legenda fica curta.
- Pergunta com "?" (a voz sobe a entonação); no máximo 2 exclamações no roteiro inteiro."""

TITLE_RULES = """TÍTULO (decide o clique; o feed mostra ~40-50 caracteres):
- Ideal 35 a 50 caracteres; máximo 60. O ASSUNTO concreto (nome, lugar, objeto, número) nas 3-4 primeiras palavras.
- Curiosidade + especificidade: abra uma lacuna que só o vídeo fecha, com um detalhe concreto. Ruim: "A história do Titanic".
  Bom: "O padeiro que sobreviveu ao Titanic bêbado".
- VERDADEIRO: tudo o que o título promete o vídeo entrega (de preferência já no começo). Nada de "chocante", "você não vai
  acreditar", "inacreditável" — o fato é que tem que chocar.
- Escrita normal (só a 1ª letra maiúscula), no máximo UMA palavra em CAIXA ALTA, sem emoji, sem hashtag, sem "#Shorts".
- Título e thumbnail se completam: não repetem as mesmas palavras."""

THUMB_RULES = """THUMBNAIL: texto de 2 a 4 palavras, legível num celular, que COMPLEMENTA o título (não repete): o número chocante,
o contraste, a emoção ou a pergunta curta que o título não disse. Fiel ao conteúdo."""

SEO_RULES = """DESCRIÇÃO, TAGS E HASHTAGS (busca e recomendação):
- DESCRIÇÃO: a 1ª frase (aparece na busca) reformula o gancho com os termos que alguém digitaria, de forma natural; a 2ª-3ª
  dizem o que a pessoa vai descobrir sem entregar o payoff. Escrita do zero para ESTE vídeo, sem lista de palavras-chave.
- TAGS: 5 a 10 — o assunto principal, variações, nomes próprios e erros de digitação comuns.
- HASHTAGS: 2 ou 3, específicas do assunto (nada genérico como #viral ou #fyp)."""

PINNED_RULES = """COMENTÁRIO FIXADO ("pinned_comment"): o 1º comentário do canal, que puxa respostas — uma pergunta ESPECÍFICA sobre um
detalhe do vídeo, um "A ou B?" com duas opções concretas, ou uma opinião discutível (respeitosa e verdadeira). Até 200
caracteres, sem links, sem hashtags, sem pedir curtida/inscrição."""


# ================================================================ PAUTAS

VIRAL_KEYS = ("busca", "curiosidade", "emocao", "momento")
VIRAL_WEIGHTS = {
    "short": {"busca": 0.15, "curiosidade": 0.40, "emocao": 0.30, "momento": 0.15},
    "long": {"busca": 0.35, "curiosidade": 0.30, "emocao": 0.15, "momento": 0.20},
}


def viral_score(viral: dict[str, Any] | None, fmt: str = "short") -> int:
    w = VIRAL_WEIGHTS["long" if fmt == "long" else "short"]
    v = viral if isinstance(viral, dict) else {}

    def num(k: str) -> float:
        try:
            return max(0.0, min(100.0, float(v.get(k, 50))))
        except (TypeError, ValueError):
            return 50.0
    return round(sum(num(k) * wk for k, wk in w.items()))


def discover_ideas(ch: Channel, count: int = 10, seed: str = "", fmt: str = "short",
                   campaign: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Busca inspiração na internet e propõe pautas novas (sem repetir as já existentes), ranqueadas por potencial
    viral (busca, curiosidade, emoção, momento) e, quando houver, pela previsão do módulo de aprendizado."""
    from .growth import active_campaign
    material: list[str] = []
    camp = campaign or active_campaign(ch)
    if campaign and not seed:
        seed = campaign.get("focus", "")
    if seed:
        for h in research.web_search(seed, 6) + research.wiki_search(seed, "pt", 4):
            material.append(f"- {h['title']}: {h.get('snippet', '')[:200]}")
    else:
        for ev in research.shuffle(research.wiki_on_this_day())[:12]:
            material.append(f"- (neste dia) {ev['title']}")
        for h in research.news_search(f"{ch.niche} curiosidade", 6):
            material.append(f"- (notícia) {h['title']}")
    used = existing_titles(ch.id)
    enem = is_enem_channel(ch)
    ask = count + min(4, max(2, count // 2))  # pede algumas a mais e fica com as de maior potencial
    fmt_txt = ("SHORTS verticais (30 a 60 s): UMA ideia só, que cabe numa frase e tem uma revelação forte no fim"
               if fmt == "short" else
               "VÍDEOS LONGOS (8 a 12 min): tema com profundidade real — personagens, viradas e consequências para capítulos — "
               "e um termo de busca forte")
    prompt = f"""{channel_brief(ch)}

{learning_context(ch.id, purpose='ideas')}

{examples_block(ch.id, 'title')}

{timing_context(ch)}

MATERIAL DE INSPIRAÇÃO ENCONTRADO NA INTERNET:
{chr(10).join(material) or '(nenhum)'}

{('PEDIDO DO CRIADOR: ' + seed) if seed else ''}
{_campaign_block(camp, bool(campaign))}
{_validated_topics(ch.id) if fmt == 'long' else ''}

PAUTAS JÁ USADAS (NÃO repita nem faça variações óbvias):
{chr(10).join('- ' + t for t in used[:120]) or '(nenhuma)'}

Você é o estrategista de pautas deste canal. Meta: sair de ~1 mil para 10 mil a 100 mil views por vídeo.
Proponha {ask} pautas de {fmt_txt}.

O QUE FAZ UMA PAUTA EXPLODIR (use como filtro):
1. LACUNA DE CURIOSIDADE concreta: a pauta cabe numa frase que cria uma pergunta que a pessoa PRECISA ver respondida.
2. ESPECIFICIDADE: um nome, número, data ou lugar real. Tema genérico ("curiosidades sobre o Egito") é reprovado.
3. FAMILIAR + SURPREENDENTE: parte de algo que o público já conhece (pessoa famosa, objeto do dia a dia, matéria da escola,
   clube, planeta, fenômeno) e revela o lado que ele não conhece.
4. EMOÇÃO forte: choque, injustiça, admiração, medo, orgulho, humor.
5. BUSCA e MOMENTO: algo que as pessoas pesquisam, uma data desta época, uma notícia, uma prova próxima.
6. VERDADE: fato real e verificável em fontes confiáveis; lenda só no formato "mito × verdade", desmentindo.
{'7. ENEM: ligue a temas que caem na prova de forma natural (preencha "enem_link").' if enem else ''}
VARIEDADE: espalhe as pautas por épocas, lugares e tipos de assunto diferentes (pessoas, lugares, objetos, eventos,
costumes, ciência, recordes); no máximo 2 do mesmo período ou tema, e evite os temas dos títulos já usados.

Para cada pauta, dê notas HONESTAS de 0 a 100 ("viral"): busca (alguém pesquisa isso?), curiosidade (quão "eu não sabia"),
emocao (carga emocional), momento (relação com hoje/esta semana/campanha). Calibre como um editor cético: 50 = mediano,
70 = bom, 85+ só para a melhor do lote (no máximo uma pauta com 85+ em cada critério). Notas infladas atrapalham a escolha.
O título não leva "#Shorts" (o sistema põe sozinho).

Responda JSON: {{"ideas": [{{"title": "título de 35-50 caracteres (máx 60), assunto concreto no começo, lacuna de curiosidade, verdadeiro",
  "hook": "a 1ª frase falada do vídeo (até 12 palavras), que para o dedo",
  "angle": "o ângulo que torna isso irresistível (a pergunta central e a revelação)",
  "summary": "resumo factual em 2-3 frases, com nomes, datas e números",
  "enem_link": "{'conteúdo do ENEM relacionado' if enem else 'deixe vazio'}",
  "search_terms": ["termos para pesquisar fontes"],
  "search_query": "o que alguém digitaria no YouTube para achar isso",
  "emotion": "choque|injustiça|admiração|medo|orgulho|humor|mistério",
  "viral": {{"busca": 0, "curiosidade": 0, "emocao": 0, "momento": 0}},
  "campaign": true/false (se a pauta é da campanha ativa),
  "from_short": "título do Short que inspirou (só para vídeos longos, senão vazio)"}}]}}"""
    data = llm.complete_json(prompt, temperature=0.95, required=("ideas",))
    ideas = data.get("ideas", []) if isinstance(data, dict) else data
    ideas = [i for i in (ideas or []) if isinstance(i, dict) and str(i.get("title") or "").strip()]
    return rank_ideas(ch, ideas, fmt, count, camp, bool(campaign))


def rank_ideas(ch: Channel, ideas: list[dict[str, Any]], fmt: str, count: int,
               camp: dict[str, Any] | None = None, all_in: bool = False) -> list[dict[str, Any]]:
    """Ordena por potencial: nota viral da IA + previsão do aprendizado (se houver). Mantém a cota da campanha."""
    for it in ideas:
        it["title"] = _clean_title(it.get("title"))
        if not enem_ok(ch, it):
            it["enem_link"] = ""
        it["viral_score"] = viral_score(it.get("viral"), fmt)
        pred = predict(ch.id, str(it.get("title", "")), str(it.get("hook", "")), fmt)
        it["predicted"] = pred
        it["rank_score"] = blend_pred(it["viral_score"], pred, 0.45)
    ranked = sorted(ideas, key=lambda x: -x["rank_score"])
    if camp and not all_in:
        need = math.ceil(float(camp.get("share", 0.6)) * count)
        camp_ideas = [x for x in ranked if x.get("campaign")][:need]
        rest = [x for x in ranked if x not in camp_ideas][:max(0, count - len(camp_ideas))]
        ranked = sorted(camp_ideas + rest, key=lambda x: -x["rank_score"])
    return ranked[:count]


def enem_ok(ch: Channel, it: dict[str, Any]) -> bool:
    link = str(it.get("enem_link") or "").strip().lower()
    return bool(link) and is_enem_channel(ch) and link not in ("deixe vazio", "-", "n/a", "nenhum")


def _campaign_block(camp: dict[str, Any] | None, all_in: bool) -> str:
    if not camp:
        return ""
    share = 100 if all_in else int(float(camp.get("share", 0.6)) * 100)
    return (f"CAMPANHA ATIVA: \"{camp['name']}\" (até {camp.get('end')}). Pelo menos {share}% das pautas devem ser sobre: "
            f"{camp.get('focus')}. Marque essas pautas com \"campaign\": true.")


def _validated_topics(channel_id: int) -> str:
    """Shorts que mais performaram: temas já validados pelo público, ótimos para virar vídeo longo."""
    rows = [r for r in _perf_rows(channel_id) if (r.get("duration") or 0) <= 70 or "#shorts" in r["title"].lower()]
    top = sorted(rows, key=lambda r: -r["perf"])[:6]
    if not top:
        return ""
    return ("TEMAS VALIDADOS (Shorts que mais performaram): transforme pelo menos metade das pautas em versões LONGAS e "
            "aprofundadas destes assuntos, com fatos novos que não couberam no Short (preencha \"from_short\"):" + chr(10) +
            chr(10).join(f"- {r['title']} ({r['views']} views, desempenho {r['perf']})" for r in top))


def existing_titles(channel_id: int, limit: int = 200) -> list[str]:
    from .models import Publication
    with session() as s:
        pubs = [t for t in s.exec(select(Publication.title).where(Publication.channel_id == channel_id)).all() if t]
        ideas = [t for t in s.exec(select(Idea.title).where(Idea.channel_id == channel_id)
                                   .order_by(Idea.created_at.desc()).limit(limit)).all()]
    seen, out = set(), []
    for t in pubs + ideas:
        k = t.lower().replace("#shorts", "").strip()
        if k not in seen:
            seen.add(k)
            out.append(t.replace("#Shorts", "").strip())
    return out


SCORE_CRITERIA = {
    "gancho": "Força do gancho nos 2 primeiros segundos (para o dedo de quem rola o feed?)",
    "curiosidade": "Lacuna de curiosidade: quão 'eu não sabia disso' / 'preciso saber o fim'",
    "relevancia": "Relevância para o público do canal e para o nicho",
    "emocao": "Carga emocional (choque, injustiça, admiração, medo, humor)",
    "visual": "Potencial de imagens fortes e reais",
    "compartilhamento": "Chance de ser compartilhado/salvo/comentado",
    "originalidade": "Pouco explorado por outros canais (ou ângulo novo de algo conhecido)",
    "veracidade": "Facilidade de comprovar com fontes confiáveis",
    "busca": "Alguém pesquisa isso no YouTube/Google? (termo de busca claro)",
    "momento": "Ligação com o momento: data, notícia, campanha, prova próxima",
}
SCORE_WEIGHTS = {"gancho": 0.17, "curiosidade": 0.16, "relevancia": 0.10, "emocao": 0.11, "visual": 0.08,
                 "compartilhamento": 0.11, "originalidade": 0.07, "veracidade": 0.08, "busca": 0.07, "momento": 0.05}


def score_idea(ch: Channel, title: str, angle: str, summary: str, fmt: str = "short") -> dict[str, Any]:
    from .analytics import calibrate_score
    crit = "\n".join(f"- {k}: {v}" for k, v in SCORE_CRITERIA.items())
    prompt = f"""{channel_brief(ch)}

HISTÓRICO REAL DO CANAL (use para calibrar sua nota — aprenda com o que deu certo e errado):
{learning_context(ch.id, purpose='ideas')}

{timing_context(ch)}

Avalie a pauta abaixo como um estrategista de conteúdo viral exigente do YouTube. Seja crítico: 50 é mediano, 80+ só para
pautas excepcionais (as que viram 100 mil views). Pense: alguém rolando o feed PARARIA por isso? Assistiria até o fim?
Mandaria para um amigo?

PAUTA: {title}
ÂNGULO: {angle}
RESUMO: {summary}

Critérios (0-100 cada):
{crit}

Responda JSON: {{"criteria": {{"gancho": 0, ...}}, "reason": "justificativa curta e direta",
  "improvements": ["como deixar a pauta mais forte (ângulo, especificidade, emoção)"],
  "better_title": "um título ainda melhor (35-50 caracteres, assunto no começo, verdadeiro)",
  "better_hook": "a 1ª frase falada ideal (até 12 palavras)"}}"""
    data = llm.complete_json(prompt, temperature=0.3, required=("criteria",))
    crits = {}
    for k in SCORE_WEIGHTS:
        try:
            crits[k] = int(max(0, min(100, float((data.get("criteria") or {}).get(k, 50)))))
        except (TypeError, ValueError):
            crits[k] = 50
    raw = round(sum(crits[k] * w for k, w in SCORE_WEIGHTS.items()))
    final = calibrate_score(ch.id, raw)
    pred = predict(ch.id, title, str(data.get("better_hook") or ""), fmt)
    final = blend_pred(final, pred, 0.4)  # previsão com dados reais do canal pesa junto (conforme a confiança)
    viral = {"busca": crits["busca"], "curiosidade": crits["curiosidade"], "emocao": crits["emocao"], "momento": crits["momento"]}
    return {"score": final, "raw_score": raw, "criteria": crits, "reason": data.get("reason", ""),
            "improvements": data.get("improvements", []), "better_title": data.get("better_title", ""),
            "better_hook": data.get("better_hook", ""), "prediction": pred,
            "viral": viral, "viral_score": viral_score(viral, fmt)}


def verify_idea(ch: Channel, idea: Idea) -> dict[str, Any]:
    """Pesquisa fontes e verifica se a premissa da pauta é verdadeira."""
    dossier = research.gather_dossier(idea.title + " " + idea.summary[:80], max_sources=5)
    srcs = dossier["sources"]
    if len(srcs) < 2:  # pouca coisa: tenta de novo com outra formulação (só o título, e o resumo)
        for q in (idea.title, idea.summary[:120]):
            more = research.gather_dossier(q, max_sources=5)["sources"] if q else []
            seen = {s["url"] for s in srcs}
            srcs += [s for s in more if s["url"] not in seen]
            if len(srcs) >= 3:
                break
        srcs = srcs[:6]
    if not srcs:
        return {"fact_status": "unverified", "facts": [], "sources": []}
    material = "\n\n".join(f"[{i + 1}] {s['title']} ({s['url']})\n{s['text'][:2500]}" for i, s in enumerate(srcs))
    prompt = f"""Você é um checador de fatos rigoroso (padrão agência de checagem).
PAUTA: {idea.title}
RESUMO: {idea.summary}

FONTES ENCONTRADAS:
{material}

Liste as afirmações centrais da pauta e verifique cada uma SOMENTE com base nas fontes acima.
Veredito: "confirmado" (2+ fontes concordam ou 1 fonte muito confiável), "parcial", "falso" ou "sem_fonte".
Atenção ao TÍTULO: se ele promete algo que as fontes não sustentam (exagero, número errado), aponte como "parcial" com a correção.

DESMENTIDO DE MITO: se a premissa da pauta for FALSA, avalie se ela daria um bom vídeo DESMENTINDO uma crença
popular (formato "mito × verdade": o vídeo responde "não" e mostra o que realmente aconteceu, com provas).
Só vale se (1) a crença é de fato difundida entre o público, e (2) as fontes acima mostram claramente a verdade.
Se a pauta só AFIRMA algo errado sem ser uma crença conhecida, "possible" é false.
Responda JSON: {{"facts": [{{"claim": "...", "verdict": "confirmado|parcial|falso|sem_fonte", "sources": [1,2], "note": "correção ou detalhe"}}], "overall": "verified|disputed|unverified", "corrected_summary": "resumo corrigido e preciso",
  "debunk": {{"possible": true/false, "popular": true/false, "myth": "a crença popular, em 1 frase", "truth": "o que as fontes mostram, com datas/nomes/números", "sources": [1,2]}}}}"""
    data = llm.complete_json(prompt, temperature=0.1, required=("facts",))
    facts = []
    for f in data.get("facts", []):
        if not isinstance(f, dict):
            continue
        idxs = [i for i in f.get("sources", []) if isinstance(i, int) and 1 <= i <= len(srcs)]
        facts.append({**f, "sources": [srcs[i - 1]["url"] for i in idxs]})
    verdicts = [f.get("verdict", "") for f in facts]
    if any(v == "falso" for v in verdicts):
        status = "disputed"
    elif verdicts and sum(v == "confirmado" for v in verdicts) >= max(1, len(verdicts) / 2):
        status = "verified"
    else:
        status = "unverified"
    out = {"fact_status": status, "facts": facts,
           "corrected_summary": data.get("corrected_summary", ""),
           "sources": [{"title": s["title"], "url": s["url"], "kind": s["kind"]} for s in srcs]}
    db = data.get("debunk") or {}
    truth_src = [i for i in db.get("sources", []) if isinstance(i, int) and 1 <= i <= len(srcs)]
    if status == "disputed" and db.get("possible") and db.get("popular") and db.get("truth") and db.get("myth") and truth_src:
        # premissa falsa, mas é um mito conhecido e as fontes mostram a verdade → vira pauta "mito × verdade"
        out.update(fact_status="verified", debunk={"myth": db["myth"], "truth": db["truth"],
                                                   "sources": [srcs[i - 1]["url"] for i in truth_src]},
                   corrected_summary=f"MITO: {db['myth']} VERDADE: {db['truth']}")
    return out


# ================================================================ ROTEIRO

def write_script(ch: Channel, idea: Idea, fmt: str | None = None, extra: str = "",
                 plan: dict[str, Any] | None = None) -> dict[str, Any]:
    from . import variety
    fmt = fmt or idea.format
    plan = plan or variety.plan(ch, fmt)
    if str(plan.get("cta_style")) == variety.NEXT_CTA and not plan.get("next_title"):
        nxt = variety.next_idea(ch, idea.id, fmt)
        if nxt:
            plan = {**plan, "next_idea": nxt.id, "next_title": nxt.title}
    mins = next((str(t)[8:] for t in idea.tags or [] if str(t).startswith("minutos:")), "")
    if fmt == "long" and mins and not plan.get("seconds"):  # duração pedida na pauta (ex.: revisão ENEM de 10 min)
        try:
            plan = {**plan, "seconds": int(float(mins) * 60)}
        except ValueError:
            pass
    seconds = plan.get("seconds") or ((ch.short_seconds or 45) if fmt == "short" else ch.long_minutes * 60)
    words = target_words(ch, fmt, plan.get("seconds"))
    dossier = research.gather_dossier(idea.title, max_sources=5)
    material = "\n\n".join(f"[{i + 1}] {s['title']} ({s['url']})\n{s['text'][:3000]}"
                           for i, s in enumerate(dossier["sources"]))
    facts = "\n".join(f"- {f['claim']} → {f['verdict']} {f.get('note', '')}" for f in idea.facts) or "(sem checagem prévia)"
    visual_rule = {
        "real": 'Todas as cenas devem usar "kind": "real" (fotos/pinturas/documentos reais da internet).',
        "ai": 'Todas as cenas devem usar "kind": "ai" (imagem gerada por IA, com prompt detalhado em inglês).',
        "mixed": 'Use "real" quando existir foto/pintura/documento real do assunto (pessoas, lugares, objetos históricos) e "ai" para reconstruir cenas que não têm registro fotográfico.',
    }.get(ch.visual_mode, 'Use "real" quando existir foto/pintura/documento real do assunto e "ai" para o resto.')
    scene_secs = "3 a 5" if fmt == "short" else "6 a 10"
    n_scenes = (f'{max(6, int(seconds) // 5)} a {max(6, int(seconds) // 5) + 3}' if fmt == 'short'
                else f'{max(25, int(seconds) // 15)} a {max(40, int(seconds) // 9)}')
    enem = is_enem_channel(ch)
    prompt = f"""{channel_brief(ch)}

{learning_context(ch.id, purpose='script')}

{examples_block(ch.id, 'title')}

PAUTA: {idea.title}
ÂNGULO: {idea.angle}
RESUMO VERIFICADO: {idea.summary}
CHECAGEM DE FATOS:
{facts}

FONTES DE PESQUISA:
{material or '(sem fontes — use apenas fatos amplamente documentados)'}

{variety.prompt_block(ch, plan, fmt)}
{_seo(ch, idea, fmt)}

{('INSTRUÇÕES EXTRAS: ' + extra) if extra else ''}

Você é o roteirista-chefe do canal, especialista em retenção no YouTube. Escreva o roteiro de um vídeo
{'CURTO VERTICAL' if fmt == 'short' else 'LONGO HORIZONTAL'} com NO MÍNIMO {words} palavras de narração no total (≈{seconds}s)
— conte as palavras; roteiro curto é reprovado. Use {n_scenes} cenas.{' Short enxuto: cada frase precisa segurar o público até o fim.' if fmt == 'short' else ''}

{HOOK_RULES}
(O estilo do gancho é o pedido em VARIEDADE; as regras acima valem para todos os estilos.)

{RETENTION_SHORT if fmt == 'short' else RETENTION_LONG}

{TTS_RULES}

FATOS E FORMA:
- SÓ use fatos confirmados pelas fontes. Datas, nomes e números precisos; nada inventado para "dar emoção".
- Mostre, não explique: cenas concretas (quem, onde, o que se via/ouvia) em vez de frases abstratas.
{'- Ligue ao ENEM de forma natural e variada (nem sempre com a mesma frase): o conceito, a causa/consequência ou como a questão costuma aparecer.' if enem else ''}
- Final com a revelação/virada e, por ÚLTIMO, o CTA curto descrito em VARIEDADE. O roteiro TERMINA no CTA: nada depois
  dele (sem "Mas afinal...", sem pergunta solta, sem reticências).
- {('CTA curto: no máximo 12 palavras, logo depois da frase de loop.' if fmt == 'short' else 'CTA curto e natural, sem encerramento longo.')}

CENAS E IMAGENS:
- Divida em cenas de {scene_secs} segundos de fala. Cada cena tem UMA imagem que mostra exatamente o que a narração diz.
- {visual_rule}
- Para "real": "query" = busca curta em INGLÊS para Wikimedia Commons (ex.: "Dom Pedro II portrait", "Canudos war 1897 photograph"), e "query_pt" em português.
- Para "ai": "prompt" em INGLÊS, muito detalhado, estilo: {ch.image_style}. Descreva época, roupas, luz, enquadramento {'vertical 9:16' if fmt == 'short' else '16:9'}. Nunca peça texto escrito na imagem.
- CENAS ANIMADAS COM DADOS: na proporção pedida em VARIEDADE, em vez de foto, use um gráfico animado quando houver dado concreto:
  * "timeline": datas em sequência → data: {{"title": "...", "events": [{{"year": "1898", "label": "até 4 palavras"}}]}} (2-4 eventos)
  * "counter": um número marcante → data: {{"value": 11, "prefix": "", "suffix": " min", "label": "o que o número significa", "icons": true se forem pessoas/coisas contáveis ≤30, "mark": "x" se foram mortos/perdidos}}
  * "map": um lugar → data: {{"scope": "brasil" ou "mundo", "highlight": ["SE"] (siglas de estados BR) ou ["EG"] (ISO-2 de países), "pin": [longitude, latitude], "label": "Local · Estado", "title": "contexto curto"}}
  * "dossier": apresentar uma pessoa → data: {{"header": "FICHA ...", "name": "nome completo", "nickname": "apelido", "fields": [["Nascimento", "..."], ["Título", "..."]], "stamp": "PROCURADO" ou outro carimbo curto opcional}} + "query"/"query_pt" para a foto da pessoa
  * "versus": mito × verdade (só se a ESTRUTURA pedir) → data: {{"left": {{"title": "Mito", "text": "..."}}, "right": {{"title": "Verdade", "text": "...", "cue": "palavra da narração que revela a verdade"}}
  * "quote": frase histórica real → data: {{"text": "...", "author": "..."}}
  * "list": 2-4 fatos/causas → data: {{"title": "...", "items": ["...", "..."]}}
  Nesses casos: "visual": {{"kind": "timeline", "data": {{...}}. Varie os tipos; nunca dois gráficos iguais seguidos. Dados SÓ de fatos confirmados.
- "emphasis": 1-3 palavras-chave da cena para destacar em dourado na legenda (palavras exatas do texto).
- "label": etiqueta curta (1-3 palavras) que descreve a imagem da cena, ex.: "Cangaceiros", "Ataque surpresa", "Reino Ptolemaico".

{TITLE_RULES}
- "title_options": 3 títulos com ângulos diferentes entre si, TODOS no formato "{variety.TITLES.get(str(plan.get('title_style')), 'chamativo')}"
  (formato sorteado para a variedade do canal — obrigatório); "title" = o melhor dos 3.

{THUMB_RULES}

{SEO_RULES}

{PINNED_RULES}

Responda JSON:
{{"title": "o melhor título (35-50 caracteres, máx 60, assunto nas primeiras palavras)",
  "title_options": ["...", "...", "..."],
  "hook": "primeira frase (= início da cena 1)",
  "scenes": [{{"text": "narração da cena", "visual": {{"kind": "real|ai|timeline|counter|map|dossier|versus|quote|list", "query": "...", "query_pt": "...", "prompt": "...", "data": {{}}}}, "emphasis": ["..."], "label": "..."}}],
  "description": "descrição única para o YouTube, 2-3 frases escritas do zero para ESTE vídeo (sem frases-padrão)",
  "tags": ["5 a 10 tags"],
  "hashtags": ["#2a3hashtags"],
  "thumbnail_text": "2-4 palavras que completam o título",
  "thumbnail_options": ["3 alternativas de 2-4 palavras, bem diferentes entre si"],
  "pinned_comment": "..."}}"""
    data = llm.complete_json(prompt, temperature=0.8, required=("scenes",))
    data["sources"] = [{"title": s["title"], "url": s["url"]} for s in dossier["sources"]]
    data = pick_title(ch, data, fmt)
    extras = {k: v for k, v in (("title_options", data.get("title_options")), ("thumb_options", data.get("thumbnail_options")),
                                ("pinned_comment", data.get("pinned_comment"))) if v}
    data["variety"] = {**plan, **extras}  # guardado no plano: miniaturas A/B e comentário do canal reaproveitam
    return data


def _clean_title(t: Any) -> str:
    t = str(t or "").replace("#Shorts", "").replace("#shorts", "").strip().strip('"“”').strip()
    return " ".join(t.split())


def pick_title(ch: Channel, data: dict[str, Any], fmt: str) -> dict[str, Any]:
    """Escolhe entre as opções de título sem gastar outra chamada de IA: previsão do aprendizado (se houver),
    preferência leve pela escolha do roteirista e penalidade para título longo demais para o feed."""
    main = _clean_title(data.get("title"))
    opts = [main] + [_clean_title(o) for o in (data.get("title_options") or []) if isinstance(o, str)]
    opts = [o for o in dict.fromkeys(opts) if o]
    if not opts:
        return data
    hook = str(data.get("hook") or "")
    scores: list[float] = []
    have_pred = False
    for i, o in enumerate(opts):
        pred = predict(ch.id, o, hook, fmt)
        # diferença prevista entre as opções, encolhida quando o modelo ainda é só um palpite
        base = 50.0 + (float(pred["score"]) - 50.0) * pred_weight(pred, 1.0) if pred else 50.0
        have_pred = have_pred or bool(pred)
        bonus = 4.0 if i == 0 else 0.0
        n = len(o)
        length_pen = 0.0 if n <= 50 else (4.0 if n <= 60 else 15.0 + (n - 60))
        scores.append(base + bonus - length_pen)
    best = max(range(len(opts)), key=lambda i: scores[i])
    data = {**data, "title": opts[best][:100], "title_options": opts}
    data["title_lab"] = {"options": opts, "scores": [round(s, 1) for s in scores], "best": best, "predicted": have_pred}
    return data


def improve_hook(ch: Channel, data: dict[str, Any], plan: dict[str, Any], log=lambda m: None) -> dict[str, Any]:
    """Laboratório de gancho: 3 alternativas para a 1ª frase, todas avaliadas junto com a original numa ÚNICA chamada
    (economiza cota); a previsão do aprendizado (se houver) entra na nota. Estilos recentes do canal ficam de fora."""
    from .variety import HOOKS, _tokens, recent_plans
    scenes = data.get("scenes") or []
    if len(scenes) < 2:
        return data
    first, second = scenes[0].get("text", ""), scenes[1].get("text", "")
    fmt = "short" if plan.get("duration") or len(scenes) <= 20 else "long"  # só o Short tem faixa de duração
    try:
        recent = recent_plans(ch.id, 10)
        recent_styles = [h.get("hook_style") for h in recent[:2] if h.get("hook_style")]
        cur = plan.get("hook_style", "")
        alt_styles = [k for k in HOOKS if k != cur and k not in recent_styles][:5] or [k for k in HOOKS if k != cur]
        recent_hooks = [" ".join(_tokens(h.get("hook") or "")[:3]) for h in recent if h.get("hook")]
        examples = examples_block(ch.id, "hook")
        styles_txt = "\n".join(f"  - {k}: {HOOKS[k]}" for k in [cur] + alt_styles if k in HOOKS)
        res = llm.complete_json(f"""{channel_brief(ch)}

{examples}

Vídeo: "{data.get('title', '')}"
Cena 1 (abertura atual, estilo "{cur}"): "{first}"
Cena 2 (vem logo depois): "{second}"

{HOOK_RULES}

TAREFA 1 — escreva 3 versões ALTERNATIVAS da cena 1, com cerca de {len(first.split())} palavras cada (±20%), fala natural
brasileira, que levem naturalmente à cena 2 e usem SÓ fatos do roteiro. Uma no estilo "{cur}" (mais forte que a atual) e as
outras em estilos diferentes desta lista:
{styles_txt}
TAREFA 2 — como especialista em retenção de {'Shorts' if fmt == 'short' else 'vídeos longos'} (público: {ch.audience}), dê nota
0-100 para CADA abertura — a original (índice 0) e as 3 novas (1 a 3): quantas pessoas PARAM de rolar e ficam? Avalie
lacuna de curiosidade imediata, clareza em 2 segundos, stakes, especificidade (nomes, números) e honestidade. Seja duro.

Responda JSON: {{"hooks": [{{"text": "...", "style": "chave do estilo"}}, ...3], "scores": [nota da original, nota 1, nota 2, nota 3], "why": "motivo curto da melhor"}}""",
                                temperature=0.8, required=("hooks",))
        alts = [h for h in (res.get("hooks") or []) if isinstance(h, dict) and str(h.get("text") or "").strip()][:3]
        cands = [first] + [str(h["text"]).strip() for h in alts]
        styles = [cur] + [str(h.get("style") or "") for h in alts]
        if len(cands) < 2:
            return data
        raw = res.get("scores") or []
        scores = []
        for i in range(len(cands)):
            try:
                scores.append(int(float(raw[i])))
            except (IndexError, TypeError, ValueError):
                scores.append(50 if i else 60)
        for i, c in enumerate(cands):
            scores[i] = blend_pred(scores[i], predict(ch.id, str(data.get("title") or ""), c, fmt), 0.4)
            if i and " ".join(_tokens(c)[:3]) in recent_hooks:
                scores[i] -= 25  # começa igual a um gancho recente do canal: anti-repetição
            n_ratio = len(c.split()) / max(1, len(first.split()))
            if i and not 0.6 <= n_ratio <= 1.5:
                scores[i] -= 15  # tamanho muito diferente desmonta o tempo da cena
        best = max(range(len(scores)), key=lambda i: scores[i])
        log(f"Laboratório de gancho: notas {scores} → opção {best + 1}" + (" (original)" if best == 0 else "") +
            (f" — {res.get('why')}" if res.get("why") else ""))
        if best > 0:
            scenes = [dict(scenes[0], text=cands[best])] + scenes[1:]
            data = {**data, "scenes": scenes, "hook": cands[best]}
            if styles[best] in HOOKS and isinstance(data.get("variety"), dict):
                # o experimento de estilos de gancho registra o estilo que de fato foi ao ar
                data["variety"] = {**data["variety"], "hook_style": styles[best], "hook_style_planned": cur}
        data["hook_lab"] = {"candidates": cands, "scores": scores, "best": best, "styles": styles}
    except Exception as e:  # noqa: BLE001
        log(f"Laboratório de gancho não rodou: {e}")
    return data


def _seo(ch: Channel, idea: Idea, fmt: str) -> str:
    if fmt != "long":
        return ""
    try:
        from .longform import seo_block
        return seo_block(ch, idea.title, [t for t in (idea.tags or []) if ":" not in t][:2])
    except Exception:  # noqa: BLE001
        return ""


def review_script(ch: Channel, script: Script) -> dict[str, Any]:
    """Segunda IA atua como editor-chefe: nota do roteiro + checagem final."""
    text = "\n".join(f"{i + 1}. {s.get('text', '')}" for i, s in enumerate(script.scenes))
    fmt = script.format or "short"
    prompt = f"""{channel_brief(ch)}

Você é editor-chefe e checador de fatos de um canal que precisa de 10 mil+ views por vídeo. Avalie o roteiro abaixo
({'Short vertical' if fmt == 'short' else 'vídeo longo'}).
TÍTULO: {script.title}
ROTEIRO:
{text}

FONTES: {', '.join(s['url'] for s in (script.sources or [])[:8])}

1) Liste qualquer afirmação possivelmente FALSA, imprecisa ou exagerada (com correção) — "type": "fato".
   Também marque qualquer frase solta/pendurada depois do CTA final ou frase terminando em reticências — "type": "final".
2) Retenção — "type": "retencao", só para problemas GRAVES e com a frase nova pronta em "fix" (mesmo tamanho):
   gancho fraco/genérico na cena 1; trecho de {'mais de 3 cenas' if fmt == 'short' else 'mais de 60 s'} sem virada ou dado novo;
   informação repetida; payoff que não responde a pergunta do começo; título que o vídeo não entrega.
3) Dê nota 0-100 para: gancho, ritmo, clareza, retenção, precisão.
4) Sugira melhorias objetivas.
Responda JSON: {{"issues": [{{"scene": 1, "type": "fato|final|retencao", "claim": "...", "problem": "...", "fix": "..."}}], "scores": {{"gancho": 0, "ritmo": 0, "clareza": 0, "retencao": 0, "precisao": 0}}, "overall": 0, "suggestions": ["..."]}}"""
    return llm.complete_json(prompt, temperature=0.2)


def rewrite_scene(ch: Channel, script: Script, index: int, instruction: str) -> dict[str, Any]:
    scene = script.scenes[index]
    prompt = f"""{channel_brief(ch)}
Roteiro: {script.title}
Cena atual (JSON): {json.dumps(scene, ensure_ascii=False)}
Contexto anterior: {script.scenes[index - 1]['text'] if index > 0 else '(início)'}
Instrução: {instruction}
{TTS_RULES}
Reescreva SOMENTE esta cena mantendo o mesmo formato JSON (text, visual, emphasis, label)."""
    return llm.complete_json(prompt, temperature=0.7, cache=False)


def apply_fixes(ch: Channel, script: Script, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aplica as correções do revisor no roteiro mantendo a estrutura das cenas."""
    if not issues:
        return script.scenes
    prompt = f"""Corrija o roteiro aplicando as correções listadas. Mantenha estilo, tamanho, ritmo de fala e a estrutura
JSON das cenas (mesmos campos; altere só o "text" e, se a correção exigir, "emphasis"). Não invente fatos novos.
CENAS: {json.dumps(script.scenes, ensure_ascii=False)}
CORREÇÕES: {json.dumps(issues, ensure_ascii=False)}
Responda JSON: {{"scenes": [...]}}"""
    data = llm.complete_json(prompt, temperature=0.2, required=("scenes",))
    scenes = data.get("scenes") if isinstance(data, dict) else None
    return scenes if scenes and len(scenes) >= len(script.scenes) // 2 else script.scenes


def scenes_sig(scenes: list[dict[str, Any]]) -> str:
    import hashlib
    return hashlib.sha1(" ".join((s.get("text") or "").strip() for s in scenes).encode()).hexdigest()[:16]


def check_claims(ch: Channel, script: Script, idea: Idea | None) -> dict[str, Any]:
    """Checagem frase a frase do roteiro FINAL contra as fontes: cada afirmação concreta (data, número, nome,
    evento, causa) precisa estar nas fontes. O que não estiver é corrigido ou retirado da cena."""
    urls: list[str] = []
    for u in [s.get("url") for s in (idea.sources if idea else [])] + [s.get("url") for s in script.sources or []] + \
             [u for f in (idea.facts if idea else []) for u in (f.get("sources") or [])]:
        if u and u not in urls:
            urls.append(u)
    srcs = []
    for u in urls[:6]:
        txt = research.fetch_page_text(u, 3500)
        if txt and len(txt) > 300:
            srcs.append({"url": u, "text": txt})
    if len(srcs) < 2:
        seen = {s["url"] for s in srcs}
        srcs += [{"url": s["url"], "text": s["text"][:3500]} for s in
                 research.gather_dossier(script.title.replace("#Shorts", ""), max_sources=4)["sources"] if s["url"] not in seen]
    if not srcs:
        return {"items": [], "fixes": {}, "sources": 0}
    material = "\n\n".join(f"[{i + 1}] {s['url']}\n{s['text']}" for i, s in enumerate(srcs[:6]))
    confirmed = "\n".join(f"- {f.get('claim')}" for f in (idea.facts if idea else []) if f.get("verdict") == "confirmado")
    scenes = "\n".join(f"{i + 1}. {s.get('text', '')}" for i, s in enumerate(script.scenes))
    prompt = f"""Você é checador de fatos de um canal sobre {ch.niche}. Confira o roteiro FINAL frase por frase.
TÍTULO: {script.title}
ROTEIRO (cenas numeradas):
{scenes}

FATOS JÁ CONFIRMADOS NA PAUTA:
{confirmed or '(nenhum)'}

FONTES:
{material}

1) Extraia TODAS as afirmações concretas: datas, números, nomes, lugares, eventos, citações, causas e consequências.
   Ignore opiniões, perguntas retóricas, comparações didáticas evidentes e a chamada final (CTA).
2) Para cada uma: "confirmado" (está nas fontes ou nos fatos confirmados), "sem_fonte" (as fontes não falam disso)
   ou "contradiz" (as fontes dizem outra coisa).
3) Para cada cena com afirmação "sem_fonte" ou "contradiz", reescreva o TEXTO INTEIRO da cena: corrija com o que as
   fontes dizem ou retire a afirmação. Mantenha o tom, o ritmo e o tamanho (±15% de palavras). Não invente nada novo.
Responda JSON: {{"claims": [{{"scene": 1, "claim": "...", "verdict": "confirmado|sem_fonte|contradiz", "source": 1, "note": "..."}}],
"fixes": [{{"scene": 1, "text": "texto novo da cena"}}]}}"""
    data = llm.complete_json(prompt, temperature=0.1)
    items = [c for c in (data.get("claims") or []) if isinstance(c, dict) and c.get("claim")]
    for c in items:
        k = c.get("source")
        c["source"] = srcs[k - 1]["url"] if isinstance(k, int) and 1 <= k <= len(srcs) else ""
    bad_scenes = {c.get("scene") for c in items if c.get("verdict") in ("sem_fonte", "contradiz")}
    fixes = {}
    for f in data.get("fixes") or []:
        idx, txt = f.get("scene"), (f.get("text") or "").strip()
        if isinstance(idx, int) and 1 <= idx <= len(script.scenes) and txt and idx in bad_scenes:
            old = script.scenes[idx - 1].get("text", "")
            if 0.5 <= len(txt.split()) / max(1, len(old.split())) <= 1.6:
                fixes[idx - 1] = txt
    return {"items": items, "fixes": fixes, "sources": len(srcs)}


def scene_graphic(ch: Channel, title: str, scene: dict[str, Any], facts_hint: str = "") -> dict[str, Any] | None:
    """Cena sem foto boa → gráfico animado com os dados DA PRÓPRIA narração (nada inventado). None se não couber."""
    from .render.infographics import normalize
    prompt = f"""Vídeo: {title} (canal sobre {ch.niche}).
Esta cena não tem foto boa. Transforme-a num gráfico animado usando SOMENTE informações que estão no texto da cena
(ou nos fatos confirmados abaixo). Nunca invente datas, números, nomes ou citações.
TEXTO DA CENA: {scene.get('text', '')}
FATOS CONFIRMADOS: {facts_hint or '(nenhum)'}

Tipos possíveis:
- "counter": um número marcante do texto → {{"value": 11, "prefix": "", "suffix": " km", "label": "o que o número significa"}}
- "timeline": 2-4 datas do texto → {{"title": "...", "events": [{{"year": "1904", "label": "até 4 palavras"}}]}}
- "map": um lugar citado → {{"scope": "brasil" ou "mundo", "highlight": ["SP"] (sigla de estado) ou ["US"] (ISO-2), "label": "Local"}}
- "list": 2-4 fatos/itens citados → {{"title": "...", "items": ["...", "..."]}}
- "quote": frase dita por alguém, literal no texto → {{"text": "...", "author": "..."}}
Se nenhum tipo couber com o que está no texto, responda {{"kind": "none"}}.
Responda JSON: {{"kind": "counter|timeline|map|list|quote|none", "data": {{...}}}}"""
    data = llm.complete_json(prompt, temperature=0.2)
    if not isinstance(data, dict) or data.get("kind") not in ("counter", "timeline", "map", "list", "quote"):
        return None
    v = {"kind": data["kind"], "data": data.get("data") or {}}
    norm = normalize(v)
    return {**v, "data": norm} if norm is not None else None


CTA_WORDS = ("segue", "siga", "inscreva", "se inscreve", "sininho", "curte", "compartilha", "comenta")


def clean_ending(scenes: list[dict[str, Any]], cta: str = "") -> list[dict[str, Any]]:
    """Garante que o vídeo termina no CTA: corta frases depois dele e frases penduradas com reticências."""
    import re
    if not scenes:
        return scenes
    last = dict(scenes[-1])
    sents = [x for x in re.split(r"(?<=[.!?…])\s+", (last.get("text") or "").strip()) if x]
    cta_key = " ".join(cta.lower().split()[:3])
    # palavra inteira: "persegue"/"consegue" não são CTA
    cta_re = re.compile(r"\b(" + "|".join(re.escape(w) for w in CTA_WORDS) + r")\b")

    def is_cta(snt: str) -> bool:
        low = snt.lower()
        return bool(cta_re.search(low)) or bool(cta_key and cta_key in low)

    # corta depois da ÚLTIMA frase de CTA: CTA de duas frases ("Comenta aí... Segue o canal!") fica inteiro
    hits = [i for i, snt in enumerate(sents) if is_cta(snt)]
    if hits:
        sents = sents[:hits[-1] + 1]
    while len(sents) > 1 and sents[-1].rstrip().endswith(("...", "…")):
        sents.pop()
    if sents and sents[-1].rstrip().endswith(("...", "…")):
        sents[-1] = sents[-1].rstrip(" .…") + "."
    last["text"] = " ".join(sents)
    return scenes[:-1] + [last]


OUTRO_SECONDS = 2.4


def speech_rate(ch: Channel) -> float:
    """Palavras por segundo da voz do canal (Microsoft Neural pt-BR ≈ 2,55 p/s em velocidade normal)."""
    try:
        pct = int((ch.voice_rate or "+0%").strip().rstrip("%"))
    except ValueError:
        pct = 0
    return 2.55 * (1 + pct / 100)


def target_words(ch: Channel, fmt: str, seconds: float | None = None) -> int:
    seconds = seconds or ((ch.short_seconds or 45) if fmt == "short" else (ch.long_minutes or 6) * 60)
    return int((seconds - OUTRO_SECONDS) * speech_rate(ch)) + 4


def count_words(scenes: list[dict[str, Any]]) -> int:
    return sum(len((s.get("text") or "").split()) for s in scenes)


def expand_script(ch: Channel, title: str, scenes: list[dict[str, Any]], missing: int,
                  facts_hint: str = "") -> list[dict[str, Any]]:
    """Acrescenta cenas novas (fatos reais) no MEIO da história, antes do fechamento, para atingir a duração mínima.

    O fechamento (virada/frase de loop + CTA) costuma ocupar as 2 últimas cenas; as cenas novas entram antes dele,
    no código — se a IA as colocasse entre a frase de fechamento e o CTA, o vídeo "terminava" duas vezes."""
    n_new = max(1, round(missing / 18))
    keep = 2 if len(scenes) >= 5 else 1
    body, closing = scenes[:-keep], scenes[-keep:]
    prompt = f"""{channel_brief(ch)}

O roteiro abaixo ("{title}") está CURTO: faltam cerca de {missing} palavras de narração.
Escreva {n_new} cena(s) NOVA(S) com fatos REAIS, específicos e surpreendentes sobre o mesmo tema
(datas, nomes, números, consequências, curiosidades pouco conhecidas). Elas entram no MEIO da história, logo depois
de "{(body[-1].get('text') or '')[-120:] if body else ''}" e antes do fechamento — então NÃO concluam, não façam reflexão
final, não retomem o gancho e não tenham CTA. Não repita o que já foi dito. Cada cena nova com 15-25 palavras e
funcionando como RE-GANCHO (uma virada ou um dado novo que aumenta a tensão — nunca enchimento),
no mesmo formato JSON das existentes (text, visual com kind "real" + query/query_pt em inglês/português, emphasis, label).
Frases curtas de fala, anos e números em algarismos.
{('Fatos de apoio: ' + facts_hint) if facts_hint else ''}

ROTEIRO ATUAL (JSON): {json.dumps(scenes, ensure_ascii=False)}

Responda JSON: {{"scenes": [SOMENTE as cenas novas]}}"""
    data = llm.complete_json(prompt, temperature=0.6, cache=False)
    new = data.get("scenes") if isinstance(data, dict) else (data if isinstance(data, list) else None)
    new = [x for x in (new or []) if isinstance(x, dict) and x.get("text")]
    known = {(x.get("text") or "").strip() for x in scenes}
    new = [x for x in new if (x.get("text") or "").strip() not in known]  # se a IA devolveu o roteiro inteiro
    if not new:
        raise ValueError("a IA não devolveu cenas novas")
    return clean_ending(body + new + closing, ch.cta)


def ensure_length(ch: Channel, title: str, scenes: list[dict[str, Any]], fmt: str, log=lambda m: None,
                  facts_hint: str = "", rounds: int = 3, seconds: float | None = None) -> list[dict[str, Any]]:
    target = target_words(ch, fmt, seconds)
    for _ in range(rounds):
        have = count_words(scenes)
        if have >= target * (0.88 if fmt == "short" else 0.95):  # Short: não enche de cena por poucas palavras
            break
        log(f"Roteiro curto ({have} de ~{target} palavras) — acrescentando cenas")
        try:
            scenes = expand_script(ch, title, scenes, target - have, facts_hint)
        except Exception as e:  # noqa: BLE001
            log(f"Expansão não funcionou ({e}) — tentando de novo")
    return scenes
