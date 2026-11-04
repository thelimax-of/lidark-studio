"""Roteirista do motor quadro (bible["render_style"] == "quadro"): um vídeo é um dia da história.

Duas etapas com LLM: bíblia da série (premissa, gente, lugares, HUD) e o dia, plano a plano, com a narração descrevendo
o que se vê. Não há catálogo de cenas prontas: personagens saem de parâmetros (render/quadro/boneco), lugares de receitas
com semente (render/quadro/lugares) e objetos da biblioteca ou desenhados pelo LLM (render/quadro/objetos).
Toda série consulta e alimenta quadro_registro: nada de casa, gente, paleta, gag ou objeto de destaque de outra série.
Reprovou nas regras ou no revisor: nova tentativa; sem aprovação, não há episódio.
"""
from __future__ import annotations

import copy
import json
import math
import random
import re
import textwrap
import time
from typing import Any

from .. import llm
from ..models import Channel, Idea
from . import quadro_registro as REG
from .objetos_compat import plain as _plain

VOZ = "pt-BR-ThalitaMultilingualNeural"
VOZ_RESERVA = "pt-BR-FranciscaNeural"
RATE_MAX = 8
RATE_PADRAO = 4
CHARS_MIN, CHARS_ALVO, CHARS_MAX = 1340, 1440, 1600  # narração sem a tela final: dá 90 a 110 s
PLANOS_MIN, PLANOS_MAX = 14, 30
NAO_OBJETO = {"parede", "barriga", "porta", "janela", "chao", "teto", "rosto", "mao", "dedo", "olho", "cabeca", "corredor", "rua", "vento", "vidro", "gaveta", "mensagem"}
DIAS_PADRAO = 6
PREMISSAS = ("dois adultos que se acham feios marcam um encontro às cegas", "sair do aluguel e conseguir a primeira casa", "voltar a estudar aos 50 anos", "largar um emprego ruim sem ter outro",
             "reconciliar uma família brigada antes de um aniversário", "perder a vergonha de cantar em público", "tirar a carteira de motorista depois de reprovar seis vezes", "abrir um negócio minúsculo na garagem",
             "aprender a nadar depois dos 60", "criança que quer ganhar o campeonato de pipa do bairro", "avó que descobre a internet e vira fenômeno do bairro")
ACOES = ("de_pe", "anda", "corre", "sentado", "mesa", "escreve", "segura", "aponta", "acena", "braco_alto", "levanta_mao", "ofegante", "caido", "abraca", "ri", "chora")
EMOCOES = ("neutro", "atento", "triste", "preocupado", "cansado", "decidido", "sorriso", "alegre", "surpreso", "aperto", "calmo", "bravo_c", "emocionado")
OBJ_ACOES = ("parado", "treme", "cai", "entra", "some", "rasga", "sobe")
SONS = ("moeda", "moedas", "carimbo", "pop", "lapis", "risco", "tosse", "trovao", "splash", "clique", "papel", "passo", "sucesso", "perda", "desce", "aviso", "vibra", "freio", "batida", "splat", "arfar", "ding", "teclas")
HERDADO = ("ze", "bia", "caio", "rita", "tiao", "esperanca", "furo azul", "melancia")
CORES = ("#b4231c", "#2f7a4a", "#2f5fd8", "#20222a", "#7a3b9a")
_NOMES = {0: "zero", 1: "um", 2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete", 8: "oito", 9: "nove", 10: "dez", 11: "onze", 12: "doze", 13: "treze",
          14: "quatorze", 15: "quinze", 16: "dezesseis", 17: "dezessete", 18: "dezoito", 19: "dezenove", 20: "vinte", 30: "trinta", 40: "quarenta", 50: "cinquenta", 60: "sessenta", 70: "setenta",
          80: "oitenta", 90: "noventa", 100: "cem", 200: "duzentos", 300: "trezentos", 400: "quatrocentos", 500: "quinhentos", 600: "seiscentos", 700: "setecentos", 800: "oitocentos", 900: "novecentos", 1000: "mil"}


def extenso(n: int) -> str:
    if n in _NOMES:
        return _NOMES[n]
    if n < 100:
        return f"{_NOMES[n // 10 * 10]} e {_NOMES[n % 10]}"
    if n < 200:
        return f"cento e {extenso(n - 100)}"
    if n < 1000:
        return f"{_NOMES[n // 100 * 100]} e {extenso(n % 100)}"
    if n < 2000:
        return f"mil e {extenso(n - 1000)}" if n % 1000 else "mil"
    return f"{extenso(n // 1000)} mil" + (f" e {extenso(n % 1000)}" if n % 1000 else "")


def reais(v: float) -> str:
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _num(v: Any, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


_MAPA: dict[str, int] = {}
_RX: Any = None


def _rx():
    global _RX
    if _RX is None:
        for i in range(1, 3000):
            k = _plain(extenso(i))
            _MAPA[k] = i
            _MAPA[k.replace("quatorze", "catorze")] = i
        alt = "|".join(sorted(map(re.escape, _MAPA), key=len, reverse=True))
        _RX = re.compile(rf"\b({alt})\b(?:\s+(reais|real|anos|ano|dias|dia|horas|hora|minutos|minuto|meses|mes|vezes|vez|por cento|centavos|mil))?(?:\s+e\s+({alt})\s+centavos)?")
    return _RX


def numeros_falados(txt: str) -> list[dict[str, Any]]:
    """Cada número dito na frase, com a unidade. É a lista do relatório e a base da validação."""
    return [dict(texto=m.group(0), valor=_MAPA[m[1]] + (_MAPA[m[3]] / 100 if m[3] else 0), unidade=m[2] or "") for m in _rx().finditer(_plain(txt))]


def checar_numeros(txt: str) -> list[str]:
    p = _plain(txt)
    out = []
    if re.search(r"\d", p):
        out.append(f'número em algarismo na narração: "{txt[:60]}"; escreva por extenso')
    alt = _rx().pattern.split("(")[1].split(")")[0]
    for m in re.finditer(rf"\b([a-z]+entos)\s+(?:e\s+)?(?={alt}\b)", p):  # "cinzentos cinquenta": palavra colada num número
        if m[1] not in ("duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"):
            out.append(f'"{m[1]}" colado a um número em "{txt[:60]}"')
    for n in numeros_falados(txt):
        if n["unidade"] in ("anos", "ano") and n["valor"] > 110:
            out.append(f'idade impossível: {n["texto"]}')
    for m in _rx().finditer(p):
        if not m[2] and re.search(r"\b(tinha|tem)\s+$", p[:m.start()]) and not re.match(r"\s+[a-z]{3,}", p[m.end():]):
            out.append(f'número sem unidade em "{txt[:60]}": diga anos, reais ou o que é')
    return out


# ================================================================ estado

def dias_total(arc: dict[str, Any] | None, b: dict[str, Any]) -> int:
    return int(((arc or {}).get("plan") or {}).get("parts_count") or (arc or {}).get("max_parts") or b.get("quadro_dias") or DIAS_PADRAO)


def load_state(arc: dict[str, Any] | None, n: int, b: dict[str, Any]) -> dict[str, Any] | None:
    saved = (arc or {}).get("quadro_state") or {}
    prev = [int(k) for k in saved if str(k).isdigit() and int(k) < n]
    if not prev:
        return None
    p = max(prev)
    st = copy.deepcopy(saved[str(p)])
    st.update(dia=n, dias_restantes=max(0, dias_total(arc, b) - n), escolha_vencedora=None)
    part = next((x for x in (arc or {}).get("parts") or [] if x.get("n") == p), None) or {}
    if part.get("choice"):
        st["escolha_vencedora"] = ((part.get("decision") or {}).get("options") or {}).get(part["choice"])
    return st


def _commit(slug: str, arc: dict[str, Any], n: int, state: dict[str, Any], decision: dict[str, Any] | None, bib: dict[str, Any]) -> None:
    parts = (arc.get("plan") or {}).get("parts") or []
    if decision is not None and 0 < n <= len(parts):
        parts[n - 1]["decision"] = decision

    def upd(a: dict[str, Any]) -> None:
        a.setdefault("quadro_state", {})[str(n)] = state
        a["quadro_biblia"] = bib
        pp = (a.get("plan") or {}).get("parts") or []
        if decision is not None and 0 < n <= len(pp):
            pp[n - 1]["decision"] = decision
    from . import series as S
    S.update_arc(slug, arc["id"], upd)


# ================================================================ etapa 1: bíblia

def _evitar(reg: dict[str, list[str]]) -> str:
    return (f"JÁ USADO EM OUTRAS SÉRIES, NÃO REPITA: nomes {reg['nomes'][-40:]}; lugares {reg['tipos'][-30:]}; objetos de destaque {reg['objetos'][-30:]}; "
            f"medidores {reg['huds'][-20:]}; títulos {reg['titulos'][-20:]}; premissas {reg['premissas'][-20:]}.")


def prompt_biblia(ch: Channel, b: dict[str, Any], tema: str, total: int, reg: dict[str, list[str]], tipos: list[str]) -> str:
    from ..render.quadro import boneco
    return f"""Você cria uma série de animação vertical brasileira, comédia humana de gente comum, narrada. Cada vídeo é um dia; são {total} dias.
PREMISSA PEDIDA: {tema}
{_evitar(reg)}

Crie tudo novo: nomes brasileiros incomuns, profissões, casas. O medidor do HUD mede o que a história realmente disputa. Dinheiro só se a história for de dinheiro. Exemplos de medidor: CORAGEM, VERGONHA, CHANCE COM ELA, EMPREGO, MESES SEM CHORAR, DÍVIDA.
Humor sem humilhar ninguém por grupo: a graça vem das situações. Quem é "feio" é feio de comédia e tem dignidade.

Responda só JSON:
{{"titulo": "...", "premissa": "2 frases", "desejo": "...", "obstaculo": "...", "arco_dias": ["uma frase por dia, {total} itens"],
 "hud": {{"nome": "até 14 letras", "unidade": "R$ ou % ou vazio", "inicio": 10, "meta": 100, "dinheiro": false}},
 "personagens": [{{"id": "minúsculo sem acento", "nome": "...", "anos": 34, "papel": "protagonista|par|rival|apoio", "sexo": "f|m", "idade": "{'|'.join(boneco.IDADES)}", "corpo": "{'|'.join(boneco.CORPOS)}",
   "feio": false, "roupa": "{'|'.join(boneco.ROUPAS)}", "profissao": "...", "jeito": "uma manha engraçada"}}],
 "lugares": [{{"id": "minúsculo", "tipo": "um destes: {', '.join(tipos)}", "dono": "de quem é", "hora": "dia|tarde|noite", "descricao": "curta"}}],
 "objetos": ["objetos concretos centrais da história"]}}
Regras: 3 a 5 personagens; 6 a 9 lugares de tipos diferentes; 4 a 8 objetos."""


def validar_biblia(d: dict[str, Any], reg: dict[str, list[str]], tipos: list[str]) -> list[str]:
    from ..render.quadro import lugares as LG
    prob: list[str] = []
    ps = [p for p in d.get("personagens") or [] if isinstance(p, dict)]
    ls = [x for x in d.get("lugares") or [] if isinstance(x, dict)]
    if not 3 <= len(ps) <= 5:
        prob.append("são precisos de 3 a 5 personagens")
    if len(ls) < 6:
        prob.append("são precisos pelo menos 6 lugares")
    if len({x.get("tipo") for x in ls}) < 5:
        prob.append("use pelo menos 5 tipos de lugar diferentes")
    for x in ls:
        if x.get("tipo") not in LG.R:
            prob.append(f'lugar "{x.get("tipo")}" não existe')
        elif x["tipo"] not in tipos:
            prob.append(f'o lugar "{x["tipo"]}" já foi usado em outra série')
    for p in ps:
        if REG.ja_usado(reg, "nomes", str(p.get("nome"))):
            prob.append(f'o nome {p.get("nome")} já foi usado')
        if _plain(p.get("nome")).split(" ")[0] in HERDADO:
            prob.append(f'{p.get("nome")} é de outra série')
    h = d.get("hud") if isinstance(d.get("hud"), dict) else {}
    if not str(h.get("nome") or "").strip():
        prob.append("falta o medidor do HUD")
    elif REG.ja_usado(reg, "huds", str(h.get("nome"))):
        prob.append(f'o medidor {h.get("nome")} já foi usado')
    if _num(h.get("meta")) <= _num(h.get("inicio")):
        prob.append("a meta do HUD precisa ser maior que o início")
    for o in d.get("objetos") or []:
        if REG.ja_usado(reg, "objetos", str(o)):
            prob.append(f'o objeto de destaque "{o}" já foi usado em outra série')
    if len(d.get("arco_dias") or []) < 2:
        prob.append("falta o arco dos dias")
    return prob


def materializar(d: dict[str, Any], reg: dict[str, list[str]], rng: random.Random, impedidos: list[str], tema: str = "") -> dict[str, Any]:
    """Sorteio controlado: aparência, sementes e paletas nunca repetem o registro."""
    from ..render.quadro import boneco, lugares as LG
    usados = set(reg["personagens"])
    bib = {k: d.get(k) for k in ("titulo", "premissa", "desejo", "obstaculo", "arco_dias", "objetos")}
    bib["hud"] = dict(d["hud"], nome=str(d["hud"]["nome"])[:14].upper())
    gente = {}
    h0 = rng.random()
    for p in d["personagens"]:
        ident = re.sub(r"\W", "", _plain(p.get("id") or p.get("nome")))[:16] or f"p{len(gente)}"
        fx: dict[str, Any] = {k: p[k] for k in ("sexo", "idade", "corpo", "roupa") if p.get(k)}
        if p.get("idade") not in boneco.IDADES:
            fx.pop("idade", None)
        if p.get("corpo") not in boneco.CORPOS:
            fx.pop("corpo", None)
        if p.get("roupa") not in boneco.ROUPAS:
            fx.pop("roupa", None)
        if p.get("feio") or (p.get("papel") in ("protagonista", "par") and re.search(r"\bfei[oa]s?\b", _plain(tema))):
            fx.update(feio=True, nariz=rng.choice(("batata", "adunco", "longo")), dentes=rng.choice(("dentuco", "banguela")), orelha="abano", sobrancelha=rng.choice(("monocelha", "grossa")), oculos=rng.random() < .6,
                      cabelo=rng.choice(("calvo", "topete", "black") if p.get("sexo") == "m" else ("black", "trancas", "coque")))
        antes = len(usados)
        fx["cor_roupa"] = boneco.cor_hue(h0 + len(gente) * .618)
        a = boneco.sortear(rng, usados, **fx)
        if len(usados) == antes:
            a = boneco.sortear(rng, usados)
        gente[ident] = dict(nome=str(p.get("nome"))[:24], anos=p.get("anos"), papel=p.get("papel"), jeito=p.get("jeito"), profissao=p.get("profissao"), aparencia=a)
    bib["personagens"] = gente
    lug = {}
    for x in d["lugares"]:
        tipo = x["tipo"]
        seed = rng.randint(1, 10 ** 6)
        for _ in range(500):
            pal = LG.paleta(seed, LG.R[tipo].get("classe", "media"))
            if f"{tipo}:{seed}" not in reg["composicoes"] and pal["id"] not in reg["paletas"]:
                break
            impedidos.append(f"paleta/composição repetida em {tipo} (semente {seed}): sorteada outra")
            seed = rng.randint(1, 10 ** 6)
        reg["paletas"].append(pal["id"])
        ident = re.sub(r"\W", "", _plain(x.get("id") or tipo))[:18] or tipo
        lug[ident] = dict(tipo=tipo, semente=seed, hora=x.get("hora") if x.get("hora") in ("dia", "tarde", "noite") else "dia", dono=x.get("dono"), descricao=x.get("descricao"), paleta=pal["id"])
    bib["lugares"] = lug
    return bib


def criar_biblia(ch: Channel, b: dict[str, Any], tema: str, total: int, reg: dict[str, list[str]], rng: random.Random, log, impedidos: list[str]) -> dict[str, Any]:
    from ..render.quadro import lugares as LG
    todos = [t for t in LG.R if t not in reg["tipos"]]
    if len(todos) < 10:  # catálogo gasto: libera os mais antigos, com semente nova
        todos = list(LG.R)
    impedidos += [f"lugar bloqueado por outra série: {t}" for t in LG.R if t not in todos]
    p = prompt_biblia(ch, b, tema, total, reg, todos)
    prob: list[str] = []
    d: dict[str, Any] = {}
    for t in range(4):
        d = llm.complete_json(p + (("\n\nRECUSADO:\n- " + "\n- ".join(prob[:10])) if prob else ""), temperature=.9 if not prob else .6, required=("titulo", "personagens", "lugares", "hud"), timeout=180)
        prob = validar_biblia(d, reg, todos)
        impedidos += [x for x in prob if "já" in x]
        if log:
            log(f"Bíblia, tentativa {t + 1}: {d.get('titulo')}" + (f"; recusada: {'; '.join(prob[:3])}" if prob else ""))
        if not prob:
            return materializar(d, reg, rng, impedidos, tema)
    raise llm.LLMError("Bíblia recusada: " + "; ".join(prob[:5]))


# ================================================================ objetos: desenhar o que falta

def desenhar(nomes: list[str], log=None) -> list[str]:
    """Pede ao LLM o desenho do que falta, sanitiza e guarda na biblioteca. Devolve o que continua faltando."""
    from ..render.quadro import objetos as O
    falta = [n for n in dict.fromkeys(nomes) if not O.achar(n)]
    for t in range(4):
        if not falta:
            break
        lote = falta[:5]
        p = f"""Desenhe em SVG estes objetos para um desenho animado brasileiro: {lote}.
Estilo fixo: traço escuro stroke="#241c22" stroke-width="3", cores chapadas, stroke-linejoin="round", sem degradê, sem texto, sem filtro.
Caixa 200x200. O objeto fica centralizado, com a base em y=190. Reconhecível de relance, de frente ou 3/4, com 6 a 25 formas, usando só path, circle, ellipse, rect, polygon, line.
Responda só JSON: {{"objetos": [{{"nome": "o nome pedido", "alias": ["sinônimos em português"], "tam": 0.2 a 1.0 (tamanho na cena; máquina 1, xícara 0.25), "svg": "<svg viewBox='0 0 200 200'>...</svg>"}}]}}"""
        r = llm.complete_json(p, temperature=.5, required=("objetos",), timeout=240)
        for o in r.get("objetos") or []:
            if not isinstance(o, dict):
                continue
            sv = O.sanitizar(o.get("svg"))
            nome = next((n for n in falta if _plain(n) == _plain(o.get("nome"))), None)
            if sv and nome:
                O.guardar(nome, sv, max(.15, min(1.1, _num(o.get("tam"), .5))), [nome] + [str(a) for a in o.get("alias") or []][:6])
                if log:
                    log(f"Objeto desenhado pelo LLM: {nome}")
        falta = [n for n in falta if not O.achar(n)]
    return falta


# ================================================================ etapa 2: o dia, plano a plano

def prompt_dia(ch: Channel, bib: dict[str, Any], n: int, total: int, st: dict[str, Any], ask_vote: bool, last: bool, reg: dict[str, list[str]]) -> str:
    gente = {k: f'{v["nome"]}, {v.get("anos")} anos, {v.get("profissao")}, {v.get("papel")}; {v.get("jeito")}' for k, v in bib["personagens"].items()}
    lug = {k: f'{v["tipo"]} de {v.get("dono")}, {v.get("descricao")}' for k, v in bib["lugares"].items()}
    h = bib["hud"]
    din = "Dinheiro é dito em reais e centavos, por extenso." if h.get("dinheiro") else "Esta história não é sobre dinheiro: não invente conta nem meta em reais."
    voto = (f"Termine num dilema real: o dia {n + 1} depende da escolha do público." if ask_vote else "Termine num gancho forte.") if not last else "Último dia: resolva a história."
    pass_ = ""
    if st.get("resumo"):
        pass_ = f"ATÉ AQUI: {st['resumo']}\n"
    if st.get("escolha_vencedora"):
        pass_ += f"O PÚBLICO ESCOLHEU: {st['escolha_vencedora']}. Comece por isso, com consequência real.\n"
    return f"""Escreva o DIA {n} DE {total} da série "{bib['titulo']}".
PREMISSA: {bib['premissa']} DESEJO: {bib['desejo']} OBSTÁCULO: {bib['obstaculo']}
ESTE DIA NO ARCO: {(bib.get('arco_dias') or [''] * n)[min(n - 1, len(bib.get('arco_dias') or [1]) - 1)]}
{pass_}PERSONAGENS (ids): {json.dumps(gente, ensure_ascii=False)}
LUGARES (ids): {json.dumps(lug, ensure_ascii=False)}
MEDIDOR: {h['nome']} começa hoje em {st['valor']:g}{h.get('unidade') or ''}, meta {h['meta']:g}.
{din}
{voto}

Narrador único, em terceira pessoa, que fala o tempo todo e DESCREVE O QUE SE VÊ em cada plano. Frases curtas, concretas, humor seco. Exemplo do tom:
"Toda manhã ele comprava um pão só. Não por economia. Era a única desculpa pra falar com a moça da padaria."
Toda frase tem sentido sozinha e continua a anterior: causa e efeito, sem frase solta. Números sempre por extenso e com unidade: "cinquenta e dois anos", "doze reais". Sem exclamação. Nunca peça comentário nem inscrição.

TAMANHO: {PLANOS_MIN + 2} a {PLANOS_MAX - 2} planos; soma da narração entre {CHARS_MIN + 60} e {CHARS_MAX - 60} caracteres, ou seja, de 50 a 70 caracteres por plano, uma frase curta só. A tela final é do sistema.
Mude de lugar pelo menos 5 vezes. Use ao menos 3 personagens. Varie o enquadramento. Cada objeto citado na narração aparece nesse plano, sendo usado.
Selo é opcional: só uma piada nascida desta história ou uma informação clara, até 22 letras, sem repetir a narração. Sem piada boa, deixe vazio. Faça de 3 a 7 selos no dia. Já usados, não repita: {reg['gags'][-40:]}.

Responda só JSON:
{{"title": "...", "thumbnail_text": "até 3 palavras", "description": "...", "hashtags": ["#..."], "tags": ["..."], "mission": {{"title": "EM MAIÚSCULAS", "subtitle": "..."}},
 "memory": "2 frases do que aconteceu", "cliffhanger": "...", "next_hook": "...",
 "choice": {{"question": "...", "a": {{"word": "UMA PALAVRA 4+ LETRAS", "hint": "até 20 letras", "branch": "..."}}, "b": {{"word": "...", "hint": "...", "branch": "..."}}, "default": "A"}},
 "planos": [{{"lugar": "id", "enquadramento": "geral|medio|close|detalhe", "narracao": "uma ou duas frases", "chave": ["palavra colorida"],
   "atores": [{{"id": "...", "acao": "{'|'.join(ACOES)}", "emocao": "{'|'.join(EMOCOES)}", "na_mao": "objeto ou vazio"}}],
   "objetos": [{{"nome": "...", "onde": "mesa|chao|centro", "acao": "{'|'.join(OBJ_ACOES)}"}}],
   "selo": "", "hud": 0, "dialogo": {{"quem": "id", "texto": "fala curta, opcional"}}, "som": "{'|'.join(SONS[:8])}|..."}}]}}
"detalhe" é close de um objeto, sem atores. "hud" é quanto o medidor muda neste plano; o narrador diz o motivo."""


def consertar(pl: list[dict[str, Any]], problemas: list[str], bib: dict[str, Any]) -> None:
    """Conserta só os planos apontados pelo revisor; o resto do dia fica como está."""
    txt = {str(i): {k: p.get(k) for k in ("lugar", "narracao", "atores")} for i, p in enumerate(pl)}
    r = llm.complete_json(f"""O revisor apontou estes problemas no roteiro:
- {chr(10).join("- " + x for x in problemas[:10])}
Corrija mudando o mínimo. Cada narração continua curta (até 75 caracteres), números por extenso. Lugares válidos: {list(bib["lugares"])}. Personagens válidos: {list(bib["personagens"])}.
Roteiro: {json.dumps(txt, ensure_ascii=False)}
Responda só JSON com os planos alterados: {{"planos": {{"7": {{"narracao": "...", "lugar": "...", "atores": [...]}}}}}}""", temperature=.3, required=("planos",), timeout=180, cache=False)
    for k, v in (r.get("planos") or {}).items():
        i = int(_num(k, -1))
        if 0 <= i < len(pl) and isinstance(v, dict):
            pl[i].update({a: b for a, b in v.items() if a in ("narracao", "lugar", "atores") and b})


def autocorrige(d: dict[str, Any], bib: dict[str, Any]) -> None:
    """O que é mecânico se conserta aqui, sem gastar outra tentativa do LLM."""
    prota = next((k for k, v in bib["personagens"].items() if v.get("papel") == "protagonista"), next(iter(bib["personagens"])))
    prev = None
    run = 0
    for p in [x for x in d.get("planos") or [] if isinstance(x, dict)]:
        ats = [a for a in p.get("atores") or [] if isinstance(a, dict)]
        if p.get("enquadramento") == "detalhe" and not p.get("objetos"):
            p["enquadramento"] = "medio"
        if p.get("enquadramento") != "detalhe" and not ats:
            if p.get("objetos"):
                p["enquadramento"] = "detalhe"
            else:
                p["atores"] = ats = [{"id": prota, "acao": "de_pe", "emocao": "neutro", "na_mao": ""}]
        s = str(p.get("selo") or "")
        pal = re.findall(r"[a-z]{4,}", _plain(s))
        if pal and (len(s.split()) < 2 or sum(1 for w in pal if w in _plain(p.get("narracao"))) * 2 > len(pal)):
            p["selo"] = ""
        c = (p.get("lugar"), p.get("enquadramento"), tuple(sorted(str(a.get("id")) for a in ats)))
        if c == prev and p.get("enquadramento") != "detalhe":
            p["enquadramento"] = {"close": "geral", "geral": "medio"}.get(str(p.get("enquadramento")), "close")
            c = (c[0], p["enquadramento"], c[2])
        run = run + 1 if prev and c[:2] == prev[:2] else 1
        if run > 2 and p.get("enquadramento") != "detalhe":
            p["enquadramento"] = {"close": "geral", "geral": "medio"}.get(str(p.get("enquadramento")), "close")
            c = (c[0], p["enquadramento"], c[2])
            run = 1
        prev = c
    dets = [p for p in d.get("planos") or [] if isinstance(p, dict) and p.get("enquadramento") == "detalhe"]
    for p in dets[7:]:  # detalhe demais vira plano com gente
        p["enquadramento"] = "geral"
        p["atores"] = [{"id": prota, "acao": "de_pe", "emocao": "neutro", "na_mao": ""}]


def ajustar_tamanho(d: dict[str, Any], log) -> None:
    """Reescreve só as narrações até caberem, sem mexer na estrutura dos planos."""
    pl = [x for x in d.get("planos") or [] if isinstance(x, dict)]
    if len(pl) < PLANOS_MIN:
        return
    alvo = CHARS_ALVO // len(pl)
    for _ in range(3):
        tot = sum(len(str(x.get("narracao") or "")) for x in pl)
        if CHARS_MIN <= tot <= CHARS_MAX:
            return
        acao = "ENCURTE" if tot > CHARS_MAX else "ALONGUE"
        r = llm.complete_json(f"""{acao} cada narração para cerca de {alvo} caracteres (nunca mais de {alvo + 14}), mantendo o sentido, a ordem, os nomes, os valores e os objetos citados.
Frases simples em português do Brasil. Números por extenso e com unidade. Devolva EXATAMENTE {len(pl)} itens.
{json.dumps({str(i): x.get("narracao") for i, x in enumerate(pl)}, ensure_ascii=False)}
Responda só JSON: {{"narracoes": {{"0": "...", "1": "..."}}}}""", temperature=.3, required=("narracoes",), timeout=180, cache=False)
        n = r.get("narracoes") if isinstance(r.get("narracoes"), dict) else {}
        for i, x in enumerate(pl):
            if str(n.get(str(i)) or "").strip():
                x["narracao"] = str(n[str(i)]).strip()
        if log:
            log(f"Ajuste de tamanho: {tot} -> {sum(len(str(x.get('narracao') or '')) for x in pl)} caracteres")


def prompt_texto(ch: Channel, bib: dict[str, Any], n: int, total: int, st: dict[str, Any], ask_vote: bool, last: bool, reg: dict[str, list[str]]) -> str:
    gente = {v["nome"]: f'{v.get("anos")} anos, {v.get("profissao")}, {v.get("papel")}; {v.get("jeito")}' for v in bib["personagens"].values()}
    lug = [f'{v["tipo"]} de {v.get("dono")}: {v.get("descricao")}' for v in bib["lugares"].values()]
    h = bib["hud"]
    din = "Todo dinheiro é dito em reais, por extenso, e as contas fecham." if h.get("dinheiro") else "Esta história NÃO é sobre dinheiro: não fale em reais."
    fim = "Último dia: resolva a história." if last else f"Termine num dilema com dois caminhos claros: o dia {n + 1} depende da escolha do público." if ask_vote else "Termine num gancho."
    pre = (f"ATÉ AQUI: {st['resumo']}\n" if st.get("resumo") else "") + (f"O PÚBLICO ESCOLHEU: {st['escolha_vencedora']}. Comece por isso, com consequência real.\n" if st.get("escolha_vencedora") else "")
    return f"""Você é roteirista de comédia brasileira. Escreva a narração do DIA {n} DE {total} da série "{bib['titulo']}": uma história contada por uma narradora, do começo ao fim, numa tacada só.
PREMISSA: {bib['premissa']} DESEJO: {bib['desejo']} OBSTÁCULO: {bib['obstaculo']}
ESTE DIA: {(bib.get('arco_dias') or [''] * n)[min(n - 1, len(bib.get('arco_dias') or [1]) - 1)]}
{pre}GENTE: {json.dumps(gente, ensure_ascii=False)}
LUGARES DISPONÍVEIS: {lug}
{din} {fim}

ESTE É O PADRÃO DE QUALIDADE (é de outra série: copie o ritmo, nunca o conteúdo):
"O Zé tinha vinte e nove anos, onze reais na conta e uma geladeira que guardava só água e esperança. Toda manhã ele comprava um pão só. Não por economia. Era a única desculpa pra falar com a Bia, da padaria. Nessa segunda, o celular vibrou. Era ela: sábado, sete da noite, a gente sai? O Zé respondeu claro em três segundos. Levou mais três pra lembrar que não tinha dinheiro nem pra pão na chapa. Às dez, subiu na bicicleta, que só freava quando tinha vontade. Subiu a pé. Chegou sem ar e sem alma. Foi aí que a bicicleta perdeu a vontade de frear."

REGRAS DA NARRAÇÃO:
- A história ANDA: em cada frase acontece algo novo, por causa da frase anterior. Personagem quer, tenta, dá errado, tenta outra coisa, piora, e no fim vem a virada.
- Toda hora uma piada seca, nascida da situação, geralmente no fim da frase ou numa frase curtinha depois.
- Fatos e ações, nunca enfeite. Proibido encher com adjetivo ("velho", "antigo", "pesado", "cheio de") e proibido descrever cenário à toa ou falar do cheiro da sala.
- Frases de 3 a 14 palavras, de vários tamanhos. Linguagem falada do Brasil ("pra", "tava").
- Números por extenso e sempre com unidade. Sem exclamação. Sem pedir comentário.
- Entre {CHARS_MIN + 60} e {CHARS_MAX - 60} caracteres, 16 a 26 frases, passando por pelo menos 5 lugares, com pelo menos 3 pessoas fazendo coisas.

Responda só JSON:
{{"texto": "a narração inteira", "title": "...", "thumbnail_text": "até 3 palavras", "description": "...", "hashtags": ["#..."], "tags": ["..."], "mission": {{"title": "EM MAIÚSCULAS", "subtitle": "..."}},
 "memory": "2 frases do que aconteceu", "cliffhanger": "...", "next_hook": "...",
 "choice": {{"question": "...", "a": {{"word": "UMA PALAVRA 4+ LETRAS", "hint": "até 20 letras", "branch": "..."}}, "b": {{"word": "...", "hint": "...", "branch": "..."}}, "default": "A"}}}}"""


def prompt_direcao(bib: dict[str, Any], frases: list[str], st: dict[str, Any], reg: dict[str, list[str]]) -> str:
    gente = {k: f'{v["nome"]}, {v.get("profissao")}' for k, v in bib["personagens"].items()}
    lug = {k: f'{v["tipo"]}: {v.get("descricao")}' for k, v in bib["lugares"].items()}
    h = bib["hud"]
    return f"""Você é o diretor de um desenho animado vertical. Para CADA frase da narração abaixo, defina um plano que MOSTRE exatamente o que a frase conta. A narração não muda.
FRASES: {json.dumps({i: f for i, f in enumerate(frases)}, ensure_ascii=False)}
PERSONAGENS (ids): {json.dumps(gente, ensure_ascii=False)}
LUGARES (ids): {json.dumps(lug, ensure_ascii=False)}
MEDIDOR {h['nome']}: começa em {st['valor']:g}{h.get('unidade') or ''}, meta {h['meta']:g}. "hud" é quanto ele muda no plano; use nos momentos que mudam a história{'; numa frase com valor em reais, o hud é esse valor' if h.get('dinheiro') else ''}.

Regras: quem a frase cita está em cena FAZENDO a ação: quase ninguém fica só sentado ou parado. Quando a frase cita um objeto, use "detalhe" com ele grande e agindo (rasga, cai, treme, some, entra) ou ponha na mão do personagem com acao "segura". Faça de 5 a 7 planos "detalhe" no dia. Todo objeto físico citado aparece: na mão ("na_mao") ou em "objetos", com ação. Mude de lugar quando a história muda. Varie enquadramento: geral, medio, close, detalhe (detalhe = close de objeto, sem atores). Use pelo menos 5 lugares e 3 personagens.
Selo: no máximo 4 no dia, cada um uma PIADA clara, que qualquer pessoa entende que comenta a imagem, de 2 a 5 palavras, até 22 letras, sem repetir palavra da frase. Sem piada boa, deixe vazio. Já usados: {reg['gags'][-40:]}.
Diálogo em caixa só quando a própria frase cita uma fala.

Responda só JSON com um item por frase, na mesma ordem:
{{"planos": [{{"frase": 0, "lugar": "id", "enquadramento": "geral|medio|close|detalhe", "chave": ["palavra da frase para colorir"],
 "atores": [{{"id": "...", "acao": "{'|'.join(ACOES)}", "emocao": "{'|'.join(EMOCOES)}", "na_mao": "objeto ou vazio"}}],
 "objetos": [{{"nome": "...", "onde": "mesa|chao|centro", "acao": "{'|'.join(OBJ_ACOES)}"}}], "selo": "", "hud": 0, "dialogo": {{"quem": "id", "texto": ""}}, "som": "{'|'.join(SONS)}"}}]}}"""


def frases_de(texto: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.?!])\s+", str(texto).strip()) if x.strip()]


def validar_texto(fs: list[str], reg: dict[str, list[str]], bib: dict[str, Any]) -> list[str]:
    prob: list[str] = []
    c = sum(len(x) + 1 for x in fs)
    if not CHARS_MIN <= c <= CHARS_MAX:
        prob.append(f"o texto tem {c} caracteres; escreva entre {CHARS_MIN + 60} e {CHARS_MAX - 60}")
    if not PLANOS_MIN <= len(fs) <= PLANOS_MAX:
        prob.append(f"são {len(fs)} frases; escreva de 16 a 26")
    for x in fs:
        prob += checar_numeros(x)
        if len(x) > 130:
            prob.append(f'frase longa demais: "{x[:50]}..."')
    t = _plain(" ".join(fs))
    if re.search(r"siga o canal|inscreva|comente|deixe seu", t):
        prob.append("tire o pedido ao público")
    if not bib["hud"].get("dinheiro") and re.search(r"\breais\b", t):
        prob.append("esta história não é de dinheiro: tire os reais")
    ws = set(re.findall(r"[a-z]{2,}", t))
    nomes = {_plain(v["nome"]).split(" ")[0] for v in bib["personagens"].values()}
    for w in HERDADO:
        if (w in ws or (" " in w and w in t)) and w not in nomes:
            prob.append(f'"{w}" é de outra série')
    return prob


def prompt_revisor(bib: dict[str, Any], planos: list[dict[str, Any]]) -> str:
    linhas = []
    for i, p in enumerate(planos):
        vis = [str(o.get("nome")) for o in p.get("objetos") or [] if isinstance(o, dict)] + [str(a.get("na_mao")) for a in p.get("atores") or [] if isinstance(a, dict) and a.get("na_mao")]
        linhas.append(f'{i}. [{p.get("lugar")}, visíveis: {vis}] {p.get("narracao")}')
    return f"""Você é revisor de roteiro, exigente, e não escreveu este texto. Ele é o texto final que vai para a voz.
SÉRIE: {bib['titulo']}. {bib['premissa']}
{chr(10).join(linhas)}

Avalie: faz sentido do começo ao fim? Cada frase segue da anterior? Há palavra sem sentido, número estranho (idade dita como idade, dinheiro como dinheiro), frase solta, contradição?
Objeto citado que não está em "visíveis" NÃO é problema: vai só em "faltam" (objeto físico, não lugar, pessoa nem parte do corpo).
Selos dos planos: {[(i, p.get("selo")) for i, p in enumerate(planos) if p.get("selo")]}. Em "selos_bons" liste só o número dos selos que qualquer pessoa entende de primeira e acha graça; na dúvida, não liste.
Responda só JSON: {{"faz_sentido": true|false, "nota": 0 a 10, "problemas": ["plano N: ..."], "faltam": [{{"plano": 0, "objeto": "nome no singular"}}], "selos_bons": [0]}}
Reprove (false) também se for só descrição sem acontecimento, sem nenhuma graça, ou se a imagem indicada não mostrar o que a frase conta; não reprove por gosto."""


def validar_dia(d: dict[str, Any], bib: dict[str, Any], st: dict[str, Any], reg: dict[str, list[str]]) -> list[str]:
    prob: list[str] = []
    pl = [p for p in d.get("planos") or [] if isinstance(p, dict)]
    if not PLANOS_MIN <= len(pl) <= PLANOS_MAX + 4:
        prob.append(f"são {len(pl)} planos; escreva de {PLANOS_MIN + 2} a {PLANOS_MAX - 2}")
    chars = sum(len(str(p.get("narracao") or "")) for p in pl)
    if not CHARS_MIN <= chars <= CHARS_MAX:
        prob.append(f"narração com {chars} caracteres; escreva entre {CHARS_MIN + 60} e {CHARS_MAX - 60}")
    gente, lugs = bib["personagens"], bib["lugares"]
    comp, em_cena, locais, prev = set(), set(), set(), None
    valor = float(st["valor"])
    h = bib["hud"]
    selos = 0
    for i, p in enumerate(pl):
        txt = str(p.get("narracao") or "")
        if not txt.strip():
            prob.append(f"plano {i} sem narração")
        prob += [f"plano {i}: {x}" for x in checar_numeros(txt)]
        if re.search(r"siga o canal|inscreva|comente|deixe seu", _plain(txt)):
            prob.append(f"plano {i}: tire o pedido ao público")
        ws = set(re.findall(r"[a-z]{2,}", _plain(txt)))
        for w in HERDADO:
            if w in ws or (" " in w and w in _plain(txt)):
                if w not in {_plain(v["nome"]).split(" ")[0] for v in gente.values()}:
                    prob.append(f'plano {i}: "{w}" é de outra série')
        if p.get("lugar") not in lugs:
            prob.append(f'plano {i}: lugar "{p.get("lugar")}" não existe; use {list(lugs)}')
        ids = tuple(sorted(str(a.get("id")) for a in p.get("atores") or [] if isinstance(a, dict)))
        for x in ids:
            if x not in gente:
                prob.append(f'plano {i}: personagem "{x}" não existe')
        em_cena |= set(ids)
        enq = p.get("enquadramento")
        locais.add(p.get("lugar"))
        c = (p.get("lugar"), enq, ids, tuple(sorted(_plain(o.get("nome")) for o in p.get("objetos") or [] if isinstance(o, dict))) if enq == "detalhe" else ())
        comp.add(c)
        if c == prev:
            prob.append(f"plano {i} repete a composição do anterior")
        prev = c
        if enq != "detalhe" and not ids:
            prob.append(f"plano {i} sem ninguém: use detalhe ou ponha alguém")
        if enq == "detalhe" and not (p.get("objetos") or []):
            prob.append(f"plano {i}: detalhe precisa de objeto")
        s = str(p.get("selo") or "").strip()
        if s:
            selos += 1
            if REG.ja_usado(reg, "gags", s):
                prob.append(f'selo "{s}" já foi usado')
            pal = [w for w in re.findall(r"[a-z]{4,}", _plain(s))]
            if pal and sum(1 for w in pal if w in _plain(txt)) * 2 > len(pal):
                prob.append(f'plano {i}: o selo "{s}" só repete a narração')
        valor = round(valor + _num(p.get("hud")), 2)
        if h.get("dinheiro") and _num(p.get("hud")):
            r = abs(_num(p.get("hud")))
            if not any(abs(x["valor"] - r) < .005 or abs(x["valor"] - valor) < .005 for x in numeros_falados(txt)):
                prob.append(f"plano {i}: o valor {r:.2f} não é dito na narração")
    pass_d = sum(1 for p in pl if p.get("enquadramento") == "detalhe")
    ativos = sum(1 for p in pl for a in p.get("atores") or [] if isinstance(a, dict) and (a.get("na_mao") or a.get("acao") not in ("de_pe", "sentado", "mesa")))
    if pass_d < 4:
        prob.append(f"só {pass_d} planos detalhe; faça de 5 a 7, com o objeto citado agindo")
    if ativos < len(pl) * .35:
        prob.append("gente demais parada: dê ações físicas e objetos na mão")
    if len(comp) < 8:
        prob.append(f"só {len(comp)} composições distintas; o mínimo é 8")
    if len(locais) < 5:
        prob.append(f"só {len(locais)} lugares; use pelo menos 5")
    if len(em_cena) < 3:
        prob.append(f"só {len(em_cena)} personagens em cena; o mínimo é 3")
    if selos > 9:
        prob.append("selos demais: deixe só os bons")
    if not h.get("dinheiro") and re.search(r"\breais\b", _plain(" ".join(str(p.get("narracao")) for p in pl))):
        prob.append("esta história não é de dinheiro: tire os reais da narração")
    return prob


def completar_objetos(pl: list[dict[str, Any]], faltam: list[Any]) -> list[str]:
    """Todo objeto da biblioteca citado na narração entra no plano; o revisor aponta o resto."""
    from ..render.quadro import objetos as O
    al = O.todos_alias()
    nomes = []
    for p in pl:
        p.setdefault("objetos", [])
        vis = {_plain(o.get("nome")) for o in p["objetos"] if isinstance(o, dict)} | {_plain(a.get("na_mao")) for a in p.get("atores") or [] if isinstance(a, dict)}
        t = _plain(p.get("narracao"))
        for a, k in al.items():
            if a in ("ferro", "peso", "nota", "bolsa", "linha", "cafe", "rosa", "flor", "conta") and len(a) < 6:
                continue
            if re.search(rf"\b{re.escape(a)}\b", t) and _plain(k) not in vis and a not in vis and len(a) > 3:
                vis.add(_plain(k))
                p["objetos"].append({"nome": k, "onde": "mesa", "acao": "parado"})
    for f in faltam or []:
        if not isinstance(f, dict):
            continue
        i = int(_num(f.get("plano"), -1))
        if 0 <= i < len(pl) and f.get("objeto") and not (NAO_OBJETO & set(_plain(f.get("objeto")).split())):
            pl[i]["objetos"].append({"nome": str(f["objeto"]), "onde": "mesa", "acao": "parado"})
            nomes.append(str(f["objeto"]))
    return nomes


# ================================================================ compilador

def _anim(acao: str, x: float, y: float, s: float) -> list[list[float]]:
    if acao == "treme":
        return [[i * .08, x + (3 if i % 2 else -3) * s, y, 0, s, 1] for i in range(60)]
    if acao == "cai":
        return [[0, x, y - 260, -30, s, 1], [.5, x, y, 12, s, 1], [.7, x, y, 0, s, 1]]
    if acao == "entra":
        return [[0, x, y, 0, .01, 1], [.3, x, y, 0, s, 1]]
    if acao == "some":
        return [[0, x, y, 0, s, 1], [1.2, x, y, 0, s, 1], [1.6, x, y, 0, s, 0]]
    if acao == "sobe":
        return [[0, x, y, 0, s, 1], [1, x, y - 34, 3, s, 1], [2, x, y, 0, s, 1], [3, x, y - 34, -3, s, 1], [4, x, y, 0, s, 1]]
    if acao == "rasga":
        return [[i * .07, x + (4 if i % 2 else -4) * s, y, 2 if i % 2 else -2, s, 1] for i in range(14)] + [[1.0, x, y, 0, s, 1]]
    return [[0, x, y, 0, s, 1]]


def _rasgo(x: float, y: float, s: float) -> dict[str, Any]:
    sv = f'<path d="M-6-120L10-96L-10-72L8-46L-8-20L6 0L-4 16" fill="none" stroke="#241c22" stroke-width="7" stroke-linejoin="round"/><path d="M-6-120L10-96L-10-72L8-46L-8-20L6 0L-4 16L-16-20L-22-46L-24-72L-22-96z" fill="#f4efe2" stroke="#241c22" stroke-width="2.4"/>'
    return dict(id=f"ras{int(x)}{int(y)}", svg=sv, camada="frente", chaves=[[0, x, y, 0, s, 0], [.8, x, y, 0, s, 0], [.9, x, y, 0, s, 1]])


def _pose(acao: str, em: str, c: dict[str, Any], slug: str) -> tuple[list[Any], bool]:
    """Devolve (trilha de poses, sentado à mesa)."""
    ex = {"ex": em} if em in EMOCOES else {}
    hq = round(c["quadril"] * .48)
    sent = {"q": [0, hq]}
    mao = {"sN": slug, "mN": "punho"} if slug else {}
    if acao == "sentado":
        return [[0, ["sentado", {**sent, **ex, "o": [5, 2]}]], [1.4, ["sentado", {**sent, **ex, "o": [7, 5]}]]], False
    if acao in ("mesa", "escreve"):
        k = {"sN": "caneta"} if acao == "escreve" else {"sN": "", "mN": "apoiada"}
        return [[0, ["sentado_mesa", {**sent, **ex, **k}]], [.8, ["sentado_mesa_soma", {**sent, **ex, **k}]]], True
    if acao == "anda":
        return [[0, ["anda", {**ex, "o": [6, 0], **mao}]]], False
    if acao == "corre":
        return [[0, ["corre", {**ex, **mao}]]], False
    if acao == "caido":
        return [[0, ["caido", {"q": [0, round(c["quadril"] * .78)], **ex}]]], False
    if acao == "ri":
        return [[0, ["de_pe", {"ex": "alegre", "o": [5, -2]}]], [1.0, ["de_pe", {"ex": "alegre", "hr": -6, "h": [0, -3]}]]], False
    if acao == "chora":
        return [[0, ["de_pe", {"ex": "emocionado", "lagrima": 1, "hr": 8, "h": [0, 4]}]]], False
    if acao == "abraca":
        return [[0, ["caio_abraca", {}]]], False
    if acao == "ofegante":
        return [[0, ["ofegante", ex]]], False
    if acao == "segura" or slug:
        return [[0, ["segura", {**ex, "sN": slug, "mN": "punho", "osc": {"N": [.03, .05, 2.6, 0]}}]], [1.6, ["segura", {**ex, "sN": slug, "mN": "punho", "o": [5, 8], "osc": {"N": [.03, .05, 2.6, 0]}}]]], False
    if acao in ("aponta", "acena", "braco_alto", "levanta_mao"):
        return [[0, ["de_pe", {**ex, "o": [6, 0]}]], [.5, [acao, ex]]], False
    return [[0, ["de_pe", {**ex, "o": [6, 1]}]], [1.0, ["de_pe", {**ex, "o": [8, 4]}]], [2.2, ["de_pe", {**ex, "o": [6, 1], "hr": 3}]]], False


def compilar(d: dict[str, Any], bib: dict[str, Any], st: dict[str, Any], choice: dict[str, Any], decision: dict[str, Any] | None, voz: dict[str, str], n: int) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    from ..render.quadro import boneco, cenarios2, lugares as LG, objetos as O
    pers = {k: v["aparencia"] for k, v in bib["personagens"].items()}
    cs = {k: boneco.construir(v) for k, v in pers.items()}
    from ..render.quadro import personagens as PP
    PP._registrar_tipos()
    h = bib["hud"]
    valor = float(st["valor"])
    cenas, mao_svg = [], {}
    usados_obj: list[str] = []
    planos = [p for p in d["planos"] if isinstance(p, dict)]
    for i, p in enumerate(planos):
        lug = bib["lugares"][p["lugar"]]
        ext = bool(LG.R[lug["tipo"]].get("ext"))
        chao = 1015 if ext else 950
        enq = p.get("enquadramento") if p.get("enquadramento") in ("geral", "medio", "close", "detalhe") else "medio"
        hora = lug["hora"]
        falas = [dict(texto=t.strip(), chave=[str(w).lower() for w in p.get("chave") or []][:3]) for t in re.split(r"(?<=[.?!])\s+", str(p["narracao"]).strip()) if t.strip()]
        ats = [a for a in p.get("atores") or [] if isinstance(a, dict) and a.get("id") in bib["personagens"]][:3]
        objs_pl = [o for o in p.get("objetos") or [] if isinstance(o, dict) and O.achar(o.get("nome"))]
        objs: list[dict[str, Any]] = []
        efeitos: list[dict[str, Any]] = []
        sfx: list[list[Any]] = []
        if enq == "detalhe" and objs_pl:
            pal = LG.paleta(lug["semente"])
            pl: dict[str, Any] = dict(cenario="composto", opc=dict(tipo=lug["tipo"], semente=lug["semente"], hora=hora), cam=[[0, 360, 700, 1.25], ["fim", 360, 710, 1.32]], desfocados=[])
            objs.append(dict(id=f"sup{i}", svg=f'<rect x="-500" y="0" width="1000" height="60" fill="{pal["madeira"]}" stroke="#241c22" stroke-width="3"/><rect x="-500" y="60" width="1000" height="900" fill="{pal["madeira2"]}"/>', camada="frente", chaves=[[0, 360, 860, 0, 1, 1]]))
            for j, o in enumerate(objs_pl[:2]):
                sv, tam = O.svg_de(o["nome"])
                x, y, s = (360, 880, 2.7) if len(objs_pl) == 1 else (210 + j * 300, 880, 1.6)
                objs.append(dict(id=f"o{i}_{j}", svg=sv, camada="frente", ease="B" if o.get("acao") == "entra" else None, chaves=_anim("treme" if o.get("acao") in (None, "", "parado") and i % 2 else "entra" if o.get("acao") in (None, "", "parado") else str(o.get("acao")), x, y, s)))
                usados_obj.append(o["nome"])
                if o.get("acao") == "rasga":
                    objs.append(_rasgo(x, y - 180, s * .9))
                    efeitos.append(dict(tipo="faiscas", de=.8, ate=1.4, x=x, y=y - 200, r=240, n=10))
                    sfx.append(["risco", "i0+.6"])
        else:
            xs = {1: [300], 2: [190, 500], 3: [130, 360, 590]}.get(len(ats), [360])
            atores = []
            mesa_x = None
            topo = 0.0
            for j, a in enumerate(ats):
                c = cs[a["id"]]
                slug = ""
                nm = a.get("na_mao")
                if nm and O.achar(nm):
                    sv, tam = O.svg_de(nm)
                    slug = "m" + re.sub(r"\W", "", _plain(nm))[:14]
                    z = max(.3, tam * .62)
                    mao_svg[slug] = f'<g transform="translate(32 34) scale({z:.2f})">{sv}</g>'
                    usados_obj.append(nm)
                x = xs[j]
                vira = 1 if x < 360 else -1
                esc = .9
                trilha, tem_mesa = _pose(str(a.get("acao")), str(a.get("emocao")), c, slug)
                ator: dict[str, Any] = dict(nome=a["id"], x=x, y=chao, escala=esc, vira=vira, poses=trilha)
                acao = a.get("acao")
                if acao in ("anda", "corre"):
                    ax = 760 if vira < 0 else -40
                    ator.pop("x")
                    ator.update(mov=[[0, ax, chao], [2.0 if acao == "anda" else 1.1, x, chao], ["fim", x, chao]], poses=trilha + [[2.0 if acao == "anda" else 1.1, ["de_pe", {"ex": a.get("emocao") or "neutro"}]]])
                    sfx.append(["passo", "i0+.3"])
                if acao in ("sentado", "mesa", "escreve"):
                    hq = round(c["quadril"] * .48)
                    objs.append(dict(id=f"as{i}_{j}", item="cadeira_gerada", args=[round((c["quadril"] - hq) * esc - 2), 92, LG.paleta(lug["semente"])["madeira"]], camada="tras", chaves=[[0, x - vira * 6, chao - 1, 0, 1, 1]]))
                if tem_mesa:
                    hq = round(c["quadril"] * .48)
                    alt = ((c["quadril"] - hq) + abs(c["ombroN"][1]) - .5 * sum(c["braco"])) * esc + 8
                    mesa_x = x + vira * (abs(c["ombroN"][0]) * .5 + .44 * sum(c["braco"]) * esc + 70)
                    topo = chao - alt
                    k = alt / 124
                    objs.append(dict(id=f"me{i}", svg=LG.m_mesa(0, 0, LG.paleta(lug["semente"])), camada="frente", chaves=[[0, mesa_x, chao + 4, 0, k, 1]]))
                atores.append(ator)
            for j, o in enumerate(objs_pl[:3]):
                sv, tam = O.svg_de(o["nome"])
                usados_obj.append(o["nome"])
                s = max(.5, tam * 1.5)
                if mesa_x is not None:
                    x, y = mesa_x + (j - .5 * (len(objs_pl) - 1)) * 120, topo
                elif o.get("onde") == "chao" or len(ats) >= 2 or ext or lug["tipo"] in ("onibus", "metro"):
                    x, y = (560 if len(ats) == 1 and xs[0] < 360 else 360) + j * 120 - 60 * (len(objs_pl) - 1), chao + 40
                else:
                    if j == 0:
                        objs.append(dict(id=f"me{i}", svg=LG.m_mesa(0, 0, LG.paleta(lug["semente"])), camada="tras", chaves=[[0, 580, chao - 10, 0, 1.15, 1]]))
                    x, y = 580 + (j - .5 * (len(objs_pl) - 1)) * 110, chao - 10 - 124 * 1.15
                objs.append(dict(id=f"o{i}_{j}", svg=sv, camada="frente", ease="B" if o.get("acao") == "entra" else None, chaves=_anim(str(o.get("acao")), x, y, s)))
                if o.get("acao") == "rasga":
                    objs.append(_rasgo(x, y - 90 * s, s))
                    sfx.append(["risco", "i0+.6"])
            ha = max((cs[a["id"]]["quadril"] * 1.75 * .9 * {"sentado": .74, "mesa": .74, "escreve": .74, "caido": .5}.get(str(a.get("acao")), 1) for a in ats), default=500)
            ax0 = xs[0] if ats else 360
            xm = sum(xs[:len(ats)]) / max(1, len(ats)) if ats else 360
            if enq == "geral" or not ats:
                d0 = 22 if i % 2 else -22
                cam = [[0, 360 + d0, 640, 1.0], ["fim", 360 - d0, 640, 1.06]]
            elif enq == "close":
                z = min(2.6, 1000 / max(ha, 300))
                cx = max(250, min(470, ax0))
                cy = chao - ha * .9 + 130 / z  # o rosto fica no terço de cima, abaixo do HUD
                cam = [[0, cx, cy, z], ["fim", cx, cy - 6, z * 1.06]]
            else:
                z = min(1.7, 800 / max(ha, 300))
                cx = max(230, min(490, xm))
                cy = chao - ha * .92 + 330 / z
                cam = [[0, cx, cy, z], ["fim", cx + 8, cy, z * 1.05]]
            pl = dict(cenario="composto", opc=dict(tipo=lug["tipo"], semente=lug["semente"], hora=hora, clima="chuva" if p.get("clima") == "chuva" else "bom"), cam=cam, atores=atores)
        pl.update(ate="fim", leg_y=1236, objetos=objs, efeitos=efeitos)
        s = str(p.get("selo") or "").strip().upper()[:24]
        if s:
            pl["selos"] = [dict(de=.5, ate=99, texto=s, x=360, y=1128, fonte=34, rot=random.Random(i).choice((-5, -3, 3, 4)), cor=CORES[i % len(CORES)])]
            sfx.append(["pop", "i0+.5"])
        dg = p.get("dialogo") if isinstance(p.get("dialogo"), dict) else {}
        if dg.get("texto") and dg.get("quem") in bib["personagens"]:
            pl["dialogos"] = [dict(de=.6, ate=99, nome=bib["personagens"][dg["quem"]]["nome"].upper()[:16], retrato=dg["quem"], texto=str(dg["texto"])[:50], y=880)]
        if p.get("som") in SONS:
            sfx.append([p["som"], "i0"])
        cena: dict[str, Any] = dict(id=f"p{i + 1}", auto=True, cenario=pl["cenario"], leg_y=1236, falas=falas, sfx=sfx, planos=[pl], ini=.04, apos=.04)
        dv = _num(p.get("hud"))
        if dv:
            valor = max(0.0, min(float(h["meta"]), round(valor + dv, 2)))
            cena.update(valor=[["i0+.3", valor]], valor_dur=.7)
            sfx.append(["moedas" if h.get("dinheiro") and dv > 0 else "sucesso" if dv > 0 else "desce", "i0+.3", .6])
        cenas.append(cena)
    a, bb = choice["a"], choice["b"]
    prota = next((k for k, v in bib["personagens"].items() if v.get("papel") == "protagonista"), next(iter(bib["personagens"])))
    outro = next(k for k in bib["personagens"] if k != prota)
    ult = f"A palavra mais comentada decide o dia {extenso(n + 1)}." if decision else "Comente a sua e diga por quê."
    cenas.append(dict(id="fim", auto=True, cenario="final", leg_y=1235, apos=1.1, falas=[dict(texto="Comente uma palavra.", chave=["palavra"]), dict(texto=f'{a["word"].capitalize()}: {a["hint"]}.', chave=[a["word"].lower()]),
                                                                                        dict(texto=f'{bb["word"].capitalize()}: {bb["hint"]}.', chave=[bb["word"].lower()]), dict(texto=ult, chave=[])],
                      sfx=[["pop", "i0"], ["pop", "i1"], ["pop", "i2"], ["ding", "i3+.5", .6]],
                      planos=[dict(ate="fim", cam=[[0, 360, 640, 1]], objetos=[dict(id="dimA", existente=True, chaves=[[0, 0, 0, 0, 1, 0], ["i2-.1", 0, 0, 0, 1, 0], ["i2+.1", 0, 0, 0, 1, 1], ["f2", 0, 0, 0, 1, 1], ["f2+.2", 0, 0, 0, 1, 0]]),
                                                                                  dict(id="dimB", existente=True, chaves=[[0, 0, 0, 0, 1, 0], ["i1-.1", 0, 0, 0, 1, 0], ["i1+.1", 0, 0, 0, 1, 1], ["f1", 0, 0, 0, 1, 1], ["f1+.2", 0, 0, 0, 1, 0]])],
                                   atores=[dict(nome=prota, x=170, y=1120, escala=.82, poses=[[0, ["de_pe", {"ex": "preocupado", "o": [6, 3]}]], ["i1", ["de_pe", {"ex": "atento", "o": [6, 6]}]]]),
                                           dict(nome=outro, x=545, y=1125, escala=.82, vira=-1, poses=[[0, ["de_pe", {"ex": "neutro", "o": [6, 1]}]], ["i2", ["de_pe", {"ex": "atento", "o": [6, 0]}]]])])]))
    din = bool(h.get("dinheiro"))
    ep = dict(dia=n, titulo=bib["titulo"], meta=float(h["meta"]), voz=voz, valor_inicial=float(st["valor"]), hud_txt=dict(dias="FALTAM", valor=str(h["nome"])[:14]), selo_dia=f"DIA {n} DE {st['dias_total']}", inventario=[], dias_abertura=st["dias_restantes"],
              musica="leve divertida", seed_musica=41 + n, gap_fala=.03, valor_fmt="brl" if din or h.get("unidade") == "R$" else "num", valor_suf="" if h.get("unidade") == "R$" else str(h.get("unidade") or ""), personagens=pers, itens_mao=mao_svg,
              final=dict(a=dict(palavra=a["word"], sub=a["hint"]), b=dict(palavra=bb["word"], sub=bb["hint"])), cenas=cenas)
    for c in cenas:
        c.setdefault("dias", st["dias_restantes"])
    fim = {**st, "valor": valor, "dia": n, "resumo": ((st.get("resumo") or "") + " " + str(d.get("memory") or ""))[-700:].strip(), "escolha_vencedora": None}
    return ep, fim, list(dict.fromkeys(usados_obj))


# ================================================================ pedido

def voz_de(b: dict[str, Any]) -> dict[str, str]:
    c = b.get("quadro_voice") if isinstance(b.get("quadro_voice"), dict) else {}
    r = int(_num(str(c.get("rate") or f"+{RATE_PADRAO}%").strip().rstrip("%"), RATE_PADRAO))
    r = max(-10, min(RATE_MAX, r))
    return {"provider": "edge", "voice": str(c.get("voice") or VOZ), "rate": f"{r:+d}%", "reserva": VOZ_RESERVA}


def write_episode(ch: Channel, b: dict[str, Any], fmt: str = "short", *, idea: Idea | None = None, topic: str = "", arc: dict[str, Any] | None = None, plan: dict[str, Any] | None = None,
                  seconds: float | None = None, log=None, series_block: str = "", research_ok: bool = True, research_query: str = "") -> dict[str, Any]:
    """Mesma assinatura e mesmo retorno de writer.write_episode (ativado por ele quando render_style == "quadro")."""
    from . import vetor_writer as VW
    from .writer import _mission
    rng = random.Random(f"{ch.id}-{time.time()}")
    reg = REG.carregar()
    impedidos: list[str] = []
    if arc and arc.get("idea_id") and idea is None:
        from ..db import session
        with session() as s:
            idea = s.get(Idea, arc["idea_id"])
    tema = topic or (arc or {}).get("topic") or (f"{idea.title}. {idea.summary}" if idea else "")
    if not tema:
        livres = [p for p in PREMISSAS if not REG.ja_usado(reg, "premissas", p)] or list(PREMISSAS)
        impedidos += [f"premissa já usada: {p}" for p in PREMISSAS if p not in livres]
        tema = rng.choice(livres)
    n = len((arc or {}).get("parts") or []) + 1
    total = dias_total(arc, b)
    bib = (arc or {}).get("quadro_biblia")
    nova = not bib
    if nova:
        bib = criar_biblia(ch, b, tema, total, reg, rng, log, impedidos)
        if arc and arc.get("id"):  # falhar no dia não joga a bíblia fora
            from . import series as S
            S.update_arc(ch.slug, arc["id"], lambda a: a.update(quadro_biblia=bib))
    st = load_state(arc, n, b) or dict(dia=n, dias_total=total, dias_restantes=max(0, total - n), valor=float(bib["hud"].get("inicio") or 0), escolha_vencedora=None, resumo="")
    parts = ((arc or {}).get("plan") or {}).get("parts") or []
    last = n >= total
    planned = parts[n - 1].get("decision") if 0 < n <= len(parts) else None
    sequencial = ((arc or {}).get("plan") or {}).get("mode") == "sequencial"
    ask_vote = bool(parts) and not last and not sequencial and b.get("quadro_vote", True) is not False
    prompt = prompt_texto(ch, bib, n, total, st, ask_vote, last, reg)
    data: dict[str, Any] = {}
    prob: list[str] = []
    rev: dict[str, Any] = {}
    sem_desenho: list[str] = []
    for t in range(7):
        p = prompt + (("\n\nSUA VERSÃO FOI REPROVADA:\n- " + "\n- ".join(prob[:12]) + "\nReescreva a narração inteira.") if prob else "")
        data = llm.complete_json(p, temperature=.9 if not prob else .7, required=("texto", "title", "choice"), timeout=240, cache=False)
        fs = frases_de(data["texto"])
        prob = validar_texto(fs, reg, bib)
        for k in ("a", "b"):
            c = (data.get("choice") or {}).get(k)
            if isinstance(c, dict):
                c["hint"] = re.sub(r"[.!]+$", "", textwrap.shorten(str(c.get("hint") or "").strip(), 22, placeholder=""))
                if not c["hint"]:
                    prob.append(f"choice.{k}.hint vazio ou longo demais")
        if log:
            log(f"Dia {n}, texto {t + 1}: {len(fs)} frases, {sum(len(x) for x in fs)} caracteres" + (f"; reprovado: {'; '.join(prob[:4])}" if prob else ""))
        if prob:
            continue
        pd = prompt_direcao(bib, fs, st, reg)
        for dt in range(3):
            r = llm.complete_json(pd + (("\n\nCORRIJA: " + "; ".join(prob[:10])) if prob else ""), temperature=.5, required=("planos",), timeout=240, cache=False)
            q = [x for x in r.get("planos") or [] if isinstance(x, dict)]
            if len(q) != len(fs):
                prob = [f"devolva exatamente {len(fs)} planos, um por frase"]
                continue
            for x, f in zip(q, fs):
                x["narracao"] = f
            data["planos"] = q
            autocorrige(data, bib)
            prob = validar_dia(data, bib, st, reg)
            if log:
                log(f"Direção {dt + 1}: {len(q)} planos" + (f"; reprovada: {'; '.join(prob[:4])}" if prob else ""))
            if not prob:
                break
        if prob:
            continue
        pl = [x for x in data["planos"] if isinstance(x, dict)]
        for rodada in range(5):
            rev = llm.complete_json(prompt_revisor(bib, pl), temperature=.2, required=("faz_sentido",), timeout=180, cache=False)
            pb = [str(x) for x in rev.get("problemas") or [] if not re.search(r"vis[ií]ve|consta|n[aã]o aparece", str(x))]
            if rev.get("faz_sentido") is True or not pb:
                rev["faz_sentido"] = True
                break
            if log:
                log(f"Revisor pediu conserto ({rodada + 1}): {'; '.join(pb[:3])[:300]}")
            consertar(pl, pb, bib)
            autocorrige(data, bib)
        else:
            prob = [f"revisor: {x}" for x in pb][:8]
            continue
        prob = validar_dia(data, bib, st, reg)
        if prob:
            continue
        bons = {int(_num(i, -1)) for i in rev.get("selos_bons") or []}
        for k, x in enumerate(pl):
            if k not in bons:
                x["selo"] = ""
        for x in [y for y in pl if y.get("selo")][3:]:
            x["selo"] = ""
        novos = completar_objetos(pl, rev.get("faltam"))
        pedidos = novos + [str(o.get("nome")) for x in pl for o in x.get("objetos") or [] if isinstance(o, dict)] + [str(a.get("na_mao")) for x in pl for a in x.get("atores") or [] if isinstance(a, dict) and a.get("na_mao")] + [str(o) for o in bib.get("objetos") or []]
        sem = desenhar(pedidos, log)
        sem = desenhar(sem, log) if sem else sem
        centrais = {_plain(o) for o in bib.get("objetos") or []}
        if centrais & {_plain(x) for x in sem}:
            prob = [f"objeto central sem desenho: {x}" for x in sem]
            continue
        sem_desenho += sem  # objeto secundário: sai do plano e fica no relatório, sem descartar o roteiro aprovado
        break
    if prob or not rev:
        raise llm.LLMError("Episódio quadro reprovado, sem vídeo: " + "; ".join(prob[:6]))
    got = VW.build_choice(data, planned, rng, [])
    if got is None:
        raise llm.LLMError("escolha final inválida: precisa de duas palavras diferentes de 4+ letras")
    choice, decision = got
    for k in ("a", "b"):
        choice[k]["hint"] = str((data["choice"].get(k) or {}).get("hint") or "é a escolha")
    if not ask_vote:
        decision = None
    ep_m, fim, obj = compilar(data, bib, st, choice, decision, voz_de(b), n)
    beats = [{"text": f["texto"], "speaker": "narrador", "cena": ci, "fala": fi} for ci, c in enumerate(ep_m["cenas"]) for fi, f in enumerate(c["falas"])]
    nums = [x["texto"] for bt in beats for x in numeros_falados(bt["text"])]
    gags = [str(x.get("selo")).strip() for x in data["planos"] if isinstance(x, dict) and str(x.get("selo") or "").strip()]
    from ..render.quadro import boneco
    REG.somar(bib["titulo"], dict(premissas=[tema] if nova else [], tipos=[v["tipo"] for v in bib["lugares"].values()], composicoes=[f'{v["tipo"]}:{v["semente"]}' for v in bib["lugares"].values()],
                                  paletas=[v["paleta"] for v in bib["lugares"].values()], personagens=[boneco.assinatura(v["aparencia"]) for v in bib["personagens"].values()], nomes=[v["nome"] for v in bib["personagens"].values()],
                                  objetos=[str(o) for o in bib.get("objetos") or []], gags=gags, huds=[bib["hud"]["nome"]], titulos=[bib["titulo"]]))
    m = data.get("mission") if isinstance(data.get("mission"), dict) else {}
    ep: dict[str, Any] = {k: data.get(k) for k in ("title", "thumbnail_text", "description", "arc_title", "cliffhanger", "memory", "next_hook")}
    ep.update(hashtags=[str(h) for h in (data.get("hashtags") or [])][:5], tags=[str(t) for t in (data.get("tags") or [])][:15], facts=[], mission=_mission(m), clock={}, objectives=[], beats=beats, render_style="quadro", decision=decision,
              part=n, episode_style=f"dia {n} de {total}", seconds_target=100, words=[0, 0], topic=tema, sources=[], idea_id=idea.id if idea else None,
              quadro={"episodio": ep_m, "biblia": bib, "state_start": st, "state_end": fim, "choice": choice, "revisor": rev, "numeros": nums, "gags": gags, "objetos": obj, "impedidos": impedidos[:60], "warnings": [f"objeto sem desenho, fora do plano: {x}" for x in sem_desenho]})
    if arc and arc.get("id"):
        _commit(ch.slug, arc, n, fim, decision, bib)
    return ep
