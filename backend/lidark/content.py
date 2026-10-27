"""Inteligência editorial: geração de pautas, nota 0-100, roteiro, checagem de fatos e revisão."""
from __future__ import annotations

import json
import logging
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


def learning_context(channel_id: int, limit: int = 8) -> str:
    """Resumo do que funcionou/não funcionou — o 'aprendizado' do canal."""
    from .analytics import performance_table
    with session() as s:
        insights = s.exec(select(Insight).where(Insight.channel_id == channel_id, Insight.kind != "retention")
                          .order_by(Insight.created_at.desc()).limit(5)).all()
        retention = s.exec(select(Insight).where(Insight.channel_id == channel_id, Insight.kind == "retention")
                           .order_by(Insight.created_at.desc()).limit(6)).all()
    rows = performance_table(channel_id)
    parts = []
    if rows:
        top = sorted(rows, key=lambda r: r["perf"], reverse=True)
        fmt = lambda r: f"- \"{r['title']}\" → {r['views']} views, {r['likes']} curtidas, retenção {r['retention']:.0f}% (desempenho {r['perf']}/100, nota prevista {r['predicted']})"  # noqa: E731
        parts.append("VÍDEOS QUE MAIS PERFORMARAM:\n" + "\n".join(fmt(r) for r in top[:limit // 2]))
        if len(top) > 4:
            parts.append("VÍDEOS QUE MENOS PERFORMARAM:\n" + "\n".join(fmt(r) for r in top[-(limit // 2):]))
    if insights:
        parts.append("APRENDIZADOS:\n" + "\n".join(f"- {i.text}" for i in insights))
    if retention:
        parts.append("LIÇÕES DE RETENÇÃO (dados reais de quanto o público assiste — siga à risca):" + chr(10) +
                     chr(10).join(f"- {i.text}" for i in retention))
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


# ================================================================ PAUTAS

def discover_ideas(ch: Channel, count: int = 10, seed: str = "", fmt: str = "short",
                   campaign: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Busca inspiração na internet e propõe pautas novas (sem repetir as já existentes)."""
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
    prompt = f"""{channel_brief(ch)}

{learning_context(ch.id)}

MATERIAL DE INSPIRAÇÃO ENCONTRADO NA INTERNET:
{chr(10).join(material) or '(nenhum)'}

{('PEDIDO DO CRIADOR: ' + seed) if seed else ''}
{_campaign_block(camp, bool(campaign))}
{_validated_topics(ch.id) if fmt == 'long' else ''}

PAUTAS JÁ USADAS (NÃO repita nem faça variações óbvias):
{chr(10).join('- ' + t for t in used[:120]) or '(nenhuma)'}

Proponha {count} pautas de {'vídeos curtos verticais (60-75s)' if fmt == 'short' else 'vídeos longos (5-8 min)'} para este canal.
Cada pauta precisa ser um fato REAL e verificável, com um ângulo surpreendente, e ligada a temas que caem no ENEM quando fizer sentido.
Pense no gancho dos 2 primeiros segundos.
VARIEDADE: espalhe as pautas por épocas, regiões do mundo e tipos de assunto diferentes (pessoas, lugares, objetos, eventos, costumes, ciência); no máximo 2 do mesmo período ou tema, e evite os temas dos títulos já usados.

Responda JSON: {{"ideas": [{{"title": "título chamativo (máx 70 caracteres)", "angle": "o ângulo/gancho que torna isso irresistível", "summary": "resumo factual em 2-3 frases", "enem_link": "conteúdo do ENEM relacionado", "search_terms": ["termos para pesquisar fontes"], "campaign": true/false (se a pauta é da campanha ativa), "from_short": "título do Short que inspirou (só para vídeos longos, senão vazio)"}}]}}"""
    data = llm.complete_json(prompt, temperature=0.95)
    return data.get("ideas", []) if isinstance(data, dict) else data


def _campaign_block(camp: dict[str, Any] | None, all_in: bool) -> str:
    if not camp:
        return ""
    share = 100 if all_in else int(float(camp.get("share", 0.6)) * 100)
    return (f"CAMPANHA ATIVA: \"{camp['name']}\" (até {camp.get('end')}). Pelo menos {share}% das pautas devem ser sobre: "
            f"{camp.get('focus')}. Marque essas pautas com \"campaign\": true.")


def _validated_topics(channel_id: int) -> str:
    """Shorts que mais performaram: temas já validados pelo público, ótimos para virar vídeo longo."""
    try:
        from .analytics import performance_table
        rows = [r for r in performance_table(channel_id) if (r.get("duration") or 0) <= 70 or "#shorts" in r["title"].lower()]
    except Exception:  # noqa: BLE001
        return ""
    top = sorted(rows, key=lambda r: -r["perf"])[:6]
    if not top:
        return ""
    return ("TEMAS VALIDADOS (Shorts que mais performaram): transforme pelo menos metade das pautas em versões LONGAS e "
            "aprofundadas destes assuntos, com fatos novos que não couberam no Short (preencha \"from_short\"):" + chr(10) +
            chr(10).join(f"- {r['title']} ({r['views']} views, desempenho {r['perf']})" for r in top))


SCORE_CRITERIA = {
    "gancho": "Força do gancho nos 2 primeiros segundos",
    "curiosidade": "Quão surpreendente / 'eu não sabia disso'",
    "relevancia": "Relevância para o público (ENEM/estudantes) e para o nicho",
    "emocao": "Carga emocional (choque, indignação, admiração, humor)",
    "visual": "Potencial de imagens fortes e reais",
    "compartilhamento": "Chance de ser compartilhado/salvo/comentado",
    "originalidade": "Pouco explorado por outros canais",
    "veracidade": "Facilidade de comprovar com fontes confiáveis",
}
SCORE_WEIGHTS = {"gancho": 0.2, "curiosidade": 0.18, "relevancia": 0.12, "emocao": 0.12,
                 "visual": 0.1, "compartilhamento": 0.12, "originalidade": 0.08, "veracidade": 0.08}


def score_idea(ch: Channel, title: str, angle: str, summary: str) -> dict[str, Any]:
    from .analytics import calibrate_score
    crit = "\n".join(f"- {k}: {v}" for k, v in SCORE_CRITERIA.items())
    prompt = f"""{channel_brief(ch)}

HISTÓRICO REAL DO CANAL (use para calibrar sua nota — aprenda com o que deu certo e errado):
{learning_context(ch.id)}

Avalie a pauta abaixo como um estrategista de conteúdo viral exigente. Seja crítico: 50 é mediano, 80+ só para pautas excepcionais.

PAUTA: {title}
ÂNGULO: {angle}
RESUMO: {summary}

Critérios (0-100 cada):
{crit}

Responda JSON: {{"criteria": {{"gancho": 0, ...}}, "reason": "justificativa curta e direta", "improvements": ["como deixar a pauta mais forte"], "better_title": "um título ainda melhor"}}"""
    data = llm.complete_json(prompt, temperature=0.3)
    crits = {k: int(max(0, min(100, float(data.get("criteria", {}).get(k, 50))))) for k in SCORE_WEIGHTS}
    raw = round(sum(crits[k] * w for k, w in SCORE_WEIGHTS.items()))
    final = calibrate_score(ch.id, raw)
    return {"score": final, "raw_score": raw, "criteria": crits, "reason": data.get("reason", ""),
            "improvements": data.get("improvements", []), "better_title": data.get("better_title", "")}


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

DESMENTIDO DE MITO: se a premissa da pauta for FALSA, avalie se ela daria um bom vídeo DESMENTINDO uma crença
popular (formato "mito × verdade": o vídeo responde "não" e mostra o que realmente aconteceu, com provas).
Só vale se (1) a crença é de fato difundida entre o público, e (2) as fontes acima mostram claramente a verdade.
Se a pauta só AFIRMA algo errado sem ser uma crença conhecida, "possible" é false.
Responda JSON: {{"facts": [{{"claim": "...", "verdict": "confirmado|parcial|falso|sem_fonte", "sources": [1,2], "note": "correção ou detalhe"}}], "overall": "verified|disputed|unverified", "corrected_summary": "resumo corrigido e preciso",
  "debunk": {{"possible": true/false, "popular": true/false, "myth": "a crença popular, em 1 frase", "truth": "o que as fontes mostram, com datas/nomes/números", "sources": [1,2]}}}}"""
    data = llm.complete_json(prompt, temperature=0.1)
    facts = []
    for f in data.get("facts", []):
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
    seconds = plan.get("seconds") or (ch.short_seconds if fmt == "short" else ch.long_minutes * 60)
    words = target_words(ch, fmt, plan.get("seconds"))
    dossier = research.gather_dossier(idea.title, max_sources=5)
    material = "\n\n".join(f"[{i + 1}] {s['title']} ({s['url']})\n{s['text'][:3000]}"
                           for i, s in enumerate(dossier["sources"]))
    facts = "\n".join(f"- {f['claim']} → {f['verdict']} {f.get('note', '')}" for f in idea.facts) or "(sem checagem prévia)"
    visual_rule = {
        "real": 'Todas as cenas devem usar "kind": "real" (fotos/pinturas/documentos reais da internet).',
        "ai": 'Todas as cenas devem usar "kind": "ai" (imagem gerada por IA, com prompt detalhado em inglês).',
        "mixed": 'Use "real" quando existir foto/pintura/documento real do assunto (pessoas, lugares, objetos históricos) e "ai" para reconstruir cenas que não têm registro fotográfico.',
    }[ch.visual_mode]
    scene_secs = "3 a 5" if fmt == "short" else "6 a 10"
    prompt = f"""{channel_brief(ch)}

{learning_context(ch.id)}

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

Escreva o roteiro de um vídeo {'CURTO VERTICAL' if fmt == 'short' else 'LONGO HORIZONTAL'} com NO MÍNIMO {words} palavras de narração no total (≈{seconds}s) — conte as palavras; roteiro curto é reprovado.
Use {'9 a 12' if fmt == 'short' else '25 a 40'} cenas.
REGRAS:
- Primeira frase = GANCHO brutal no estilo pedido em VARIEDADE, sem "Olá", sem "Você sabia" genérico.
- Frases curtas, linguagem falada brasileira, ritmo acelerado, um fato surpreendente a cada ~10s.
- SÓ use fatos confirmados pelas fontes. Datas, nomes e números precisos.
- Escreva anos e números em ALGARISMOS (1942, 25 mil), nunca por extenso — a narração lê certo e a legenda fica curta.
- {('Ligue ao ENEM de forma natural e variada (nem sempre com a mesma frase) quando fizer sentido.' if 'enem' in (ch.niche + ch.editorial_guide).lower() else '')}
- Final com virada/reflexão e, por ÚLTIMO, o CTA curto descrito em VARIEDADE. O roteiro TERMINA no CTA: nada depois dele (sem "Mas afinal...", sem pergunta solta, sem reticências).
- Divida em cenas de {scene_secs} segundos de fala. Cada cena tem UMA imagem.
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
- {('LOOP: a última frase da história (logo antes do CTA) retoma a imagem ou a ideia do gancho, para o replay automático emendar no começo. CTA curto: no máximo 12 palavras.' if fmt == 'short' else 'CTA curto e natural, sem encerramento longo.')}
SEO (o feed mostra só ~40-60 caracteres do título):
- TÍTULO: no máximo 60 caracteres; o ASSUNTO (nome, lugar, objeto) e a tensão nas 3-4 PRIMEIRAS palavras. Escrita normal (só a 1ª letra maiúscula); no máximo UMA palavra em CAIXA ALTA para dar ênfase. Nada que o vídeo não entregue.
- DESCRIÇÃO: a 1ª frase resume o vídeo com os termos que alguém digitaria na busca, de forma natural (sem lista de palavras-chave).
- TAGS: 5 a 10, incluindo variações e erros de digitação comuns do assunto principal.
- HASHTAGS: 2 ou 3, específicas do assunto (nada genérico como #viral ou #fyp).

Responda JSON:
{{"title": "título final otimizado (máx 60 caracteres, assunto nas primeiras palavras)",
  "hook": "primeira frase",
  "scenes": [{{"text": "narração da cena", "visual": {{"kind": "real|ai|timeline|counter|map|dossier|versus|quote|list", "query": "...", "query_pt": "...", "prompt": "...", "data": {{}}}}, "emphasis": ["..."], "label": "..."}}],
  "description": "descrição única para o YouTube, 2-3 frases escritas do zero para ESTE vídeo (sem frases-padrão)",
  "tags": ["5 a 10 tags"],
  "hashtags": ["#2a3hashtags"],
  "thumbnail_text": "texto de 2-4 palavras para a thumbnail"}}"""
    data = llm.complete_json(prompt, temperature=0.8)
    data["sources"] = [{"title": s["title"], "url": s["url"]} for s in dossier["sources"]]
    data["variety"] = plan
    return data


def improve_hook(ch: Channel, data: dict[str, Any], plan: dict[str, Any], log=lambda m: None) -> dict[str, Any]:
    """Laboratório de gancho: 3 alternativas para a 1ª frase + um juiz escolhe a que mais prende (inclui a original)."""
    from .variety import HOOKS
    scenes = data.get("scenes") or []
    if len(scenes) < 2:
        return data
    first, second = scenes[0].get("text", ""), scenes[1].get("text", "")
    try:
        alts = llm.complete_json(f"""{channel_brief(ch)}

Vídeo: "{data.get('title', '')}"
Cena 1 (abertura atual): "{first}"
Cena 2 (vem logo depois): "{second}"

Escreva 3 versões ALTERNATIVAS da cena 1 (a abertura que decide se a pessoa para de rolar o feed).
- Cada uma com o mesmo número aproximado de palavras ({len(first.split())}), fala natural brasileira, ritmo rápido.
- Uma no estilo {HOOKS.get(plan.get('hook_style', ''), 'forte')}, as outras em estilos diferentes entre si.
- Precisa levar naturalmente à cena 2 e usar SÓ fatos do roteiro. Sem "Olá", sem "Você sabia" genérico, sem clickbait mentiroso.
Responda JSON: {{"hooks": ["...", "...", "..."]}}""", temperature=0.9).get("hooks", [])
        cands = [first] + [h for h in alts if isinstance(h, str) and h.strip()][:3]
        if len(cands) < 2:
            return data
        listing = chr(10).join(f"{i + 1}. {h}" for i, h in enumerate(cands))
        judge = llm.complete_json(f"""Você é um especialista em retenção de Shorts/YouTube. Público: {ch.audience}.
Qual abertura faz mais gente PARAR de rolar e assistir até o fim? Avalie curiosidade imediata, clareza em 2 segundos,
tensão/promessa, especificidade (nomes, números) e honestidade (não promete o que o vídeo não entrega).
Depois dela vem: "{second}"

{listing}

Responda JSON: {{"scores": [nota 0-100 para cada, na ordem], "best": número da melhor, "why": "motivo curto"}}""", temperature=0.2)
        scores = [int(x) for x in judge.get("scores", [])][:len(cands)]
        best = max(range(len(scores)), key=lambda i: scores[i]) if scores else 0
        log(f"Laboratório de gancho: notas {scores} → opção {best + 1}" + (" (original)" if best == 0 else "") +
            (f" — {judge.get('why')}" if judge.get("why") else ""))
        if best > 0:
            scenes = [dict(scenes[0], text=cands[best])] + scenes[1:]
            data = {**data, "scenes": scenes, "hook": cands[best]}
        data["hook_lab"] = {"candidates": cands, "scores": scores, "best": best}
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
    prompt = f"""{channel_brief(ch)}

Você é editor-chefe e checador de fatos. Avalie o roteiro abaixo.
TÍTULO: {script.title}
ROTEIRO:
{text}

FONTES: {', '.join(s['url'] for s in script.sources[:8])}

1) Liste qualquer afirmação possivelmente FALSA, imprecisa ou exagerada (com correção).
   Também marque como problema qualquer frase solta/pendurada depois do CTA final ou frase terminando em reticências.
2) Dê nota 0-100 para: gancho, ritmo, clareza, retenção, precisão.
3) Sugira melhorias objetivas.
Responda JSON: {{"issues": [{{"scene": 1, "claim": "...", "problem": "...", "fix": "..."}}], "scores": {{"gancho": 0, "ritmo": 0, "clareza": 0, "retencao": 0, "precisao": 0}}, "overall": 0, "suggestions": ["..."]}}"""
    return llm.complete_json(prompt, temperature=0.2)


def rewrite_scene(ch: Channel, script: Script, index: int, instruction: str) -> dict[str, Any]:
    scene = script.scenes[index]
    prompt = f"""{channel_brief(ch)}
Roteiro: {script.title}
Cena atual (JSON): {scene}
Contexto anterior: {script.scenes[index - 1]['text'] if index > 0 else '(início)'}
Instrução: {instruction}
Reescreva SOMENTE esta cena mantendo o mesmo formato JSON (text, visual, emphasis)."""
    return llm.complete_json(prompt, temperature=0.7)


def apply_fixes(ch: Channel, script: Script, issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aplica as correções do revisor no roteiro mantendo a estrutura das cenas."""
    if not issues:
        return script.scenes
    prompt = f"""Corrija o roteiro aplicando as correções listadas. Mantenha estilo, tamanho e estrutura JSON das cenas.
CENAS: {script.scenes}
CORREÇÕES: {issues}
Responda JSON: {{"scenes": [...]}}"""
    data = llm.complete_json(prompt, temperature=0.2)
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

    def is_cta(snt: str) -> bool:
        low = snt.lower()
        return any(w in low for w in CTA_WORDS) or (cta_key and cta_key in low)

    for i, snt in enumerate(sents):
        if is_cta(snt):
            sents = sents[:i + 1]
            break
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
    seconds = seconds or ((ch.short_seconds or 65) if fmt == "short" else (ch.long_minutes or 6) * 60)
    return int((seconds - OUTRO_SECONDS) * speech_rate(ch)) + 4


def count_words(scenes: list[dict[str, Any]]) -> int:
    return sum(len((s.get("text") or "").split()) for s in scenes)


def expand_script(ch: Channel, title: str, scenes: list[dict[str, Any]], missing: int,
                  facts_hint: str = "") -> list[dict[str, Any]]:
    """Acrescenta cenas novas (fatos reais) antes do final para atingir a duração mínima."""
    n_new = max(1, round(missing / 18))
    prompt = f"""{channel_brief(ch)}

O roteiro abaixo ("{title}") está CURTO: faltam cerca de {missing} palavras de narração.
Acrescente {n_new} cena(s) NOVA(S) com fatos REAIS, específicos e surpreendentes sobre o mesmo tema
(datas, nomes, números, consequências, curiosidades pouco conhecidas), inseridas ANTES da cena final.
Não repita o que já foi dito, não altere o gancho nem a cena final (CTA). Cada cena nova com 15-25 palavras,
no mesmo formato JSON das existentes (text, visual com kind "real" + query/query_pt em inglês/português, emphasis, label).
{('Fatos de apoio: ' + facts_hint) if facts_hint else ''}

ROTEIRO ATUAL (JSON): {json.dumps(scenes, ensure_ascii=False)}

Responda JSON: {{"scenes": [roteiro COMPLETO com as cenas novas incluídas]}}"""
    data = llm.complete_json(prompt, temperature=0.6)
    new = data.get("scenes") if isinstance(data, dict) else (data if isinstance(data, list) else None)
    new = [x for x in (new or []) if isinstance(x, dict) and x.get("text")]
    if not new or count_words(new) <= count_words(scenes):
        raise ValueError(f"a IA devolveu {count_words(new)} palavras (antes {count_words(scenes)})")
    return clean_ending(new, ch.cta)


def ensure_length(ch: Channel, title: str, scenes: list[dict[str, Any]], fmt: str, log=lambda m: None,
                  facts_hint: str = "", rounds: int = 3, seconds: float | None = None) -> list[dict[str, Any]]:
    target = target_words(ch, fmt, seconds)
    for _ in range(rounds):
        have = count_words(scenes)
        if have >= target * 0.95:
            break
        log(f"Roteiro curto ({have} de ~{target} palavras) — acrescentando cenas")
        try:
            scenes = expand_script(ch, title, scenes, target - have, facts_hint)
        except Exception as e:  # noqa: BLE001
            log(f"Expansão não funcionou ({e}) — tentando de novo")
    return scenes
