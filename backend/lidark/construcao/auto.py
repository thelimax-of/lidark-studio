"""Gerador automático "como funciona": tema → roteiro → atos com peças da biblioteca → cena.
Uso, a partir de backend: python -m lidark.construcao.auto "<tema>" <pasta> [previa|mudo]
Nada aqui publica; o resultado fica na pasta.
"""
from __future__ import annotations

import json
import re
import subprocess
import unicodedata
import sys
import uuid
from pathlib import Path
from typing import Any

from .. import llm
from . import MOTOR, caderno

BIB = MOTOR / "biblioteca"
FUNDOS = {"campo", "rua", "sala", "oficina", "mar", "espaco", "cidade", "corte", "estudio"}
ERROS = {"", "treme", "apaga", "chuva"}
MUNDOS = {"campo", "rua", "sala", "oficina", "mar", "espaco", "cidade", "estudio"}
SYS_J = "Responda só JSON válido."


def catalogo() -> dict[str, dict[str, str]]:
    """Nome, categoria e descrição de todos os itens, lidos da biblioteca carregada de verdade."""
    arq = BIB / "catalogo.json"
    fontes = [BIB / "base.js", *sorted((BIB / "itens").glob("*.js"))]
    if arq.exists() and arq.stat().st_mtime > max(f.stat().st_mtime for f in fontes):
        return json.loads(arq.read_text(encoding="utf-8"))
    from playwright.sync_api import sync_playwright
    pag = BIB / "catalogo_tmp.html"
    pag.write_text("<!doctype html><meta charset=utf8><div id=c></div><div id=hud></div><div id=leg></div><script>window.ZOOM=1;window.DADOS={falas:[{t:0,dur:1,texto:'x',words:[]}],total:1,cauda:0,destaque:[]}</script><script>" + (MOTOR / "kit.bundle.js").read_text(encoding="utf-8") + "</script>" + "".join(f"<script>try{{{f.read_text(encoding='utf-8')}}}catch(e){{console.log(e)}}</script>" for f in fontes), encoding="utf-8")
    try:
        with sync_playwright() as p:
            n = p.chromium.launch(channel="msedge")
            pg = n.new_page()
            pg.goto(pag.as_uri())
            cat = pg.evaluate("Object.fromEntries(Object.entries(PC.R).map(([k,v])=>[k,{cat:v.cat,desc:v.desc}]))")
            n.close()
    finally:
        pag.unlink(missing_ok=True)
    arq.write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")
    return cat


def roteiro(tema: str) -> dict[str, Any]:
    fb = ""
    for _ in range(4):
        r = llm.complete_json(f"""Escreva a narração original de um vídeo curto que explica {tema}, falando direto com "você".
Formato: a primeira fala começa com "Se você" e mostra uma ideia simples que parece resolver. Depois de 8 a 9 falas de ciclo, cada uma assim: "Mas [problema real e concreto]. Então você [solução]. Esse é o [nome técnico]." (ou Essa é a). A última fala começa com "Parabéns, você construiu" e termina com uma pergunta para os comentários.
De 170 a 210 palavras. Frases curtas de conversa, comparações do dia a dia, informação correta, sem algarismos.{fb}
Pedido {uuid.uuid4().hex[:8]}.
JSON: {{"titulo": "...", "titulo_curto": "o assunto em até 3 palavras, com ! no fim", "falas": ["..."], "nomes": ["nome técnico de cada fala do meio, na ordem"]}}""", system=SYS_J, temperature=.7)
        r = getattr(r, "data", r)
        f = [str(x).strip() for x in r.get("falas", [])] if isinstance(r, dict) else []
        n = sum(len(x.split()) for x in f)
        err = []
        if not 9 <= len(f) <= 12:
            err.append(f"tem {len(f)} falas")
        if not 150 <= n <= 250:
            err.append(f"tem {n} palavras, use de 170 a 210")
        if f and not f[0].startswith("Se você"):
            err.append("a primeira fala não começa com Se você")
        if f and not f[-1].startswith("Parabéns, você construiu"):
            err.append("a última fala não começa como pedido")
        if sum(1 for x in f[1:-1] if "Então" in x) < len(f) - 3:
            err.append("faltou o Então nos ciclos")
        if f and "Mas " in f[0]:
            err.append("a primeira fala não pode ter Mas: é só a ideia inicial, em uma frase")
        if sum(1 for x in f[1:-1] if re.search(r"(Esse é o|Essa é a|Esses são os|Essas são as) ", x)) < len(f) - 3:
            err.append("cada ciclo termina com Esse é o nome, ou Essa é a nome, concordando em gênero")
        if not err:
            return revisar(tema, r)
        fb = "\nA versão anterior foi recusada: " + "; ".join(err)
    raise RuntimeError("A IA não seguiu o roteiro: " + "; ".join(err))


def revisar(tema: str, r: dict[str, Any]) -> dict[str, Any]:
    """Segunda leitura: corrige fatos e concordância sem mudar o formato. Se a revisão quebrar o formato, fica o original."""
    x = llm.complete_json(f"""Você é um revisor rigoroso. Tema: {tema}. {caderno.para_prompt(tema, "roteiro", 5)}Corrija erros de fato, de lógica entre problema e solução e de concordância destas falas. Mantenha o formato, o número de falas, as palavras Mas, Então e Esse é o/Essa é a, e o tamanho parecido. O nome técnico de cada ciclo tem que ser o certo para aquela solução.
{json.dumps(r["falas"], ensure_ascii=False)}
JSON: {{"falas": [...], "nomes": ["nome técnico de cada fala do meio, com acentos e espaços"]}}""", system=SYS_J, temperature=.1)
    x = getattr(x, "data", x)
    f = x.get("falas", []) if isinstance(x, dict) else []
    if len(f) == len(r["falas"]) and f[0].startswith("Se você") and f[-1].startswith("Parabéns, você construiu"):
        r.update(falas=[str(q).strip() for q in f], nomes=x.get("nomes") or r.get("nomes", []))
    return r


VAZIAS = set("como para com uma por que mas entao voce esse essa esses essas isso mais muito cada todo toda quando onde seu sua dos das nos nas pelo pela ele ela eles elas tem sem sao foi ser vai ainda agora depois".split())


def _raizes(x: str) -> set[str]:
    x = unicodedata.normalize("NFD", x.lower()).encode("ascii", "ignore").decode()
    return {w[:5] for w in re.findall(r"[a-z]{4,}", x) if w not in VAZIAS}


def objetos(tema: str, falas: list[str]) -> dict[int, list[str]]:
    """Ponte entre a ideia e a peça: que objetos físicos uma ilustração de cada fala mostraria?"""
    r = llm.complete_json(f"""Tema: {tema}. Para cada fala, liste de 3 a 5 objetos físicos concretos, em palavras simples, que apareceriam numa ilustração dela. Ideias abstratas viram objetos: juros vira moeda e banco; sustentação vira asa e avião.
{chr(10).join(f'{i}: {f}' for i, f in enumerate(falas))}
JSON: {{"objetos": [["...", "..."], ...]}}""", system=SYS_J, temperature=.2)
    r = getattr(r, "data", r)
    o = r.get("objetos", []) if isinstance(r, dict) else []
    return {i: [str(x) for x in o[i]] if i < len(o) and isinstance(o[i], list) else [] for i in range(len(falas))}


def candidatos(tema: str, falas: list[str], cat: dict[str, dict[str, str]], obj: dict[int, list[str]], n: int = 8) -> dict[int, list[str]]:
    """Cada fala recebe poucas peças: pesa o nome da peça, depois a descrição."""
    nome = {k: _raizes(k.split("_", 1)[-1].replace("_", " ")) | _raizes(k.replace("_", " ")) for k, v in cat.items() if v["cat"] != "pessoas"}
    desc = {k: _raizes(cat[k]["desc"]) for k in nome}
    rt = _raizes(tema)
    out = {}
    for i, f in enumerate(falas):
        ro = _raizes(" ".join(obj.get(i, [])))
        rf = _raizes(f)
        nota = {k: 6 * len(nome[k] & ro) + 3 * len(nome[k] & rf) + 2 * len(desc[k] & ro) + 2 * len(nome[k] & rt) for k in nome}
        out[i] = [k for k in sorted(nota, key=lambda k: -nota[k])[:n] if nota[k] >= 3]
    return out


class FaltamPecas(RuntimeError):
    """O tema pede peças que a biblioteca não tem. O sistema avisa em vez de inventar."""
    def __init__(self, faltam: list[str]):
        super().__init__("Faltam peças na biblioteca: " + ", ".join(faltam))
        self.faltam = faltam


def atos(tema: str, falas: list[str], nomes: list[str]) -> tuple[str, list[dict[str, Any]]]:
    cat = catalogo()
    obj = objetos(tema, falas)
    cand = candidatos(tema, falas, cat, obj)
    lista = "\n".join(f"{k}: {cat[k]['desc']}" for k in dict.fromkeys(x for v in cand.values() for x in v))
    porf = "\n".join(f"{i}: {f}\n   candidatas: {', '.join(cand[i]) or 'nenhuma'}" for i, f in enumerate(falas))
    fb = ""
    for _ in range(4):
        r = llm.complete_json(f"""Monte as cenas de um vídeo sobre {tema}. É UM ÚNICO cenário que cresce: cada fala acrescenta peças e a câmera anda até elas. Tudo que entra fica em cena até o fim.
Peças disponíveis (nome: descrição):
{lista}

Falas (índice: texto) e as peças candidatas de cada uma:
{porf}

Devolva "mundo": um de {sorted(MUNDOS)}. Para cada fala um ato: {{"fala": i, "erroNome": problema em até 2 palavras ou "", "erro": "", "treme", "apaga" ou "chuva", "itens": [de 1 a 3 {{"item": nome do catálogo, "palavra": palavra exata da fala, "qtd": de 1 a 5, "acao": "cai" para peças que descem, "desliza" para peças que chegam de lado, "cresce" só para o que sobe do chão, como torre ou planta, "dirige" para veículos}}], "repete": true quando a fala fala da mesma peça do ato anterior e não entra peça nova, "fluxo": true quando algo corre entre as peças, "falta": "" ou o nome do objeto concreto que a fala pede e não existe no catálogo}}.
Regra principal: use as candidatas da própria fala; a peça tem que ser o que a fala cita. Substituto parecido não vale: tanque no lugar de aterro é erro. Nunca use peça sem relação só para preencher. Sem peça certa: use repete ou preencha falta.
JSON: {{"mundo": "...", "atos": [...]}}{fb}
Pedido {uuid.uuid4().hex[:8]}.""", system=SYS_J, temperature=.3)
        r = getattr(r, "data", r)
        at = r.get("atos", []) if isinstance(r, dict) else []
        mundo = r.get("mundo") if isinstance(r, dict) else None
        err = []
        if mundo not in MUNDOS:
            err.append("mundo inválido")
        if len(at) != len(falas):
            err.append(f"são {len(falas)} atos, vieram {len(at)}")
        for i, a in enumerate(at):
            a["erro"] = a.get("erro") if a.get("erro") in ERROS else ""
            if i and i < len(falas) - 1 and i - 1 < len(nomes):
                a["nome"] = nomes[i - 1]
            ruins = [x.get("item") for x in a.get("itens", []) if x.get("item") not in cat]
            if ruins:
                err.append(f"ato {i}: itens fora do catálogo {ruins}")
            for x in a.get("itens", []):
                if x.get("palavra") and x["palavra"].lower() not in falas[i].lower():
                    x.pop("palavra")
        if not err:
            ruins = julgar(tema, falas, at, cat, obj)
            for i, _ in ruins:  # peça sem relação sai: a fala fica na peça anterior, vista de outro ângulo
                if 0 <= i < len(at):
                    at[i].update(itens=[], repete=True)
            if not at[0].get("itens"):  # a abertura pega a primeira peça aprovada
                prox = next((a for a in at[1:] if a.get("itens")), None)
                if prox:
                    at[0].update(itens=prox["itens"], repete=False)
                    prox.update(itens=[], repete=True)
            vistos: set[str] = set()
            for a in at:
                a["itens"] = [x for x in a.get("itens", []) if not (x["item"] in vistos or vistos.add(x["item"]))]
                a["repete"] = not a["itens"]
            novos = sum(1 for a in at if a.get("itens"))
            print("JUIZ", len(ruins), "recusadas,", novos, "peças novas", flush=True)
            if novos >= 3:
                return mundo, at
            err.append("sobraram poucas peças ligadas às falas: " + "; ".join(m for _, m in ruins[:4]))
        fb = "\nA versão anterior foi recusada: " + "; ".join(err[:8])
    if any("sem relação" in x for x in err):  # o juiz recusou tudo: é falta de peça, não erro de formato
        raise FaltamPecas(err[:3])
    raise RuntimeError("A IA não montou as cenas: " + "; ".join(err[:8]))


def julgar(tema: str, falas: list[str], at: list[dict[str, Any]], cat: dict[str, dict[str, str]], obj: dict[int, list[str]]) -> list[tuple[int, str]]:
    """Juiz separado: recusa só a peça sem relação com o assunto da fala."""
    rt, linhas = _raizes(tema), []
    for i, a in enumerate(at):
        rf = _raizes(falas[i] + " " + " ".join(obj.get(i, []))) | rt
        duv = [cat[x["item"]]["desc"] for x in a.get("itens", []) if not a.get("repete") and not (_raizes(x["item"].split("_", 1)[-1].replace("_", " ")) & rf)]
        if duv:  # peça que bate por palavra com a fala ou o tema não vai a julgamento
            linhas.append(f"{i}: \"{falas[i]}\" -> " + ", ".join(duv))
    if not linhas:
        return []
    r = llm.complete_json("""Para cada linha, marque só as peças sem relação com o assunto da fala, como sofá numa fala sobre asa de avião, ou tanque de água numa fala sobre aterro.
Não reprove por nível de detalhe nem por estilo. A peça do próprio assunto do vídeo sempre vale, e peça diretamente ligada à fala também. Comparações da fala, como "é como uma bomba", não precisam aparecer.
""" + "\n".join(linhas) + '\nJSON: {"ruins": [{"fala": índice, "motivo": "curto"}]}', system=SYS_J, temperature=0)
    r = getattr(r, "data", r)
    return [(int(x.get("fala", -1)), str(x.get("motivo"))) for x in (r.get("ruins", []) if isinstance(r, dict) else [])]


MASC = {"sistema", "problema", "mapa", "dia", "clima", "planeta", "caixa eletrônico", "caminhão compactador", "gerador", "cofre", "contêiner"}


def _artigo(nome: str) -> str:
    n = nome.lower()
    if n in MASC or n.split()[0] in MASC:
        return "Esse é o"
    p = n.split()[0]
    if p in {"juros", "servidores"}:
        return "Esses são os"
    if p in {"torre", "rede", "ponte", "fonte", "chave", "ponte", "fibra"}:
        return "Essa é a"
    return "Essa é a" if re.search(r"(a|ção|são|gem|dade)$", p) and not p.endswith(("ema", "oma")) else "Esse é o"


def concordar(falas: list[str], etapas: list[dict[str, Any]]) -> list[str]:
    """Fecha cada ciclo com o nome certo, no gênero certo: não depende da IA."""
    out = []
    for f, e in zip(falas, etapas):
        if e.get("nome"):
            nm = e["nome"]
            f = re.sub(r"\s*(Esse|Essa|Esses|Essas) (é|são) (o|a|os|as) [^.!?]*[.!?]\s*$", "", f).rstrip()
            sigla = nm.isupper()
            f = f"{f} {_artigo(nm)} {nm if sigla else nm[0].lower() + nm[1:]}."
        out.append(f)
    return out


def receitas() -> dict[str, dict[str, Any]]:
    return json.loads((BIB / "receitas.json").read_text(encoding="utf-8"))


def receita_do_tema(tema: str) -> str | None:
    pal = _raizes(tema)
    nota = {k: len(pal & _raizes(v["chaves"])) for k, v in receitas().items()}
    k = max(nota, key=nota.get, default=None)
    return k if k and nota[k] else None


def validar_receitas() -> list[str]:
    cat = catalogo()
    return [f"{k}: {i[0]}" for k, v in receitas().items() for e in v["etapas"] for i in e.get("itens", []) if i[0] not in cat]


def narrar(k: str) -> dict[str, Any]:
    """As peças já estão certas: a IA só escreve a narração, etapa por etapa."""
    rec = receitas()[k]
    et = rec["etapas"]
    pede = "\n".join(f"Fala {i}: {e['o']}" + (f'. Termina com "Esse é o {e["nome"]}." ou "Essa é a {e["nome"]}."' if e.get("nome") else "") for i, e in enumerate(et))
    fb = ""
    for _ in range(5):
        r = llm.complete_json(f"""Escreva a narração original de um vídeo curto sobre {rec["tema"]}, falando direto com "você". Exatamente {len(et)} falas, nesta ordem:
{pede}

A fala 0 é uma frase só, começa com "Se você" e não tem "Mas". As do meio seguem: "Mas [problema concreto]. Então você [solução]. Esse é o [nome]." A última começa com "Parabéns, você construiu" e termina com uma pergunta para os comentários.
{caderno.para_prompt(rec["tema"] + " " + pede, "roteiro")}{fb}
Pedido {uuid.uuid4().hex[:8]}.
JSON: {{"titulo": "...", "falas": ["..."]}}""", system=SYS_J, temperature=.7)
        r = getattr(r, "data", r)
        f = [str(x).strip() for x in r.get("falas", [])] if isinstance(r, dict) else []
        n = sum(len(x.split()) for x in f)
        err = []
        if len(f) != len(et):
            err.append(f"tem {len(f)} falas, precisa de {len(et)}")
        elif not f[0].startswith("Se você") or "Mas " in f[0] or not f[-1].startswith("Parabéns, você construiu"):
            err.append("primeira ou última fala fora do formato")
        else:
            falt = [e["nome"] for x, e in zip(f, et) if e.get("nome") and _raizes(e["nome"]) and not (_raizes(e["nome"]) & _raizes(x))]
            if falt:
                err.append(f"faltou citar {falt}")
            if sum("Então" in x for x in f[1:-1]) < len(f) - 3:
                err.append("faltou o Então")
        if not 165 <= n <= 240:
            err.append(f"tem {n} palavras, use de 170 a 210: explique mais o motivo de cada problema")
        err += caderno.checar(f)
        if not err:
            r = revisar(rec["tema"], r)
            r["falas"] = concordar(r["falas"], et)
            return r
        fb = "\nA versão anterior foi recusada: " + "; ".join(err)
    raise RuntimeError("A IA não seguiu a receita: " + "; ".join(err))


def atos_receita(k: str) -> tuple[str, list[dict[str, Any]]]:
    rec = receitas()[k]
    at = []
    for i, e in enumerate(rec["etapas"]):
        a = {x: e[x] for x in ("erro", "erroNome", "fluxo", "nome", "efeito", "rio", "repete", "bicoX", "bicoY", "bicoZ") if x in e}
        a.update(fala=i, itens=[{"item": n, "acao": ac, "qtd": q} for n, ac, q in e.get("itens", [])])
        at.append(a)
    return rec["mundo"], at


def montar(tema: str, pasta: Path) -> dict[str, Any]:
    k = receita_do_tema(tema)
    if not k:
        raise FaltamPecas([f"não há receita para {tema}"])
    r = narrar(k)
    mundo, at = atos_receita(k)
    r["titulo_curto"] = receitas()[k]["final"]
    pasta.mkdir(parents=True, exist_ok=True)
    p = {"id": pasta.name, "tema": tema, "titulo": r.get("titulo", tema), "voz": "pt-BR-ThalitaMultilingualNeural", "rate": "+8%", "zoom": 1, "cauda": 5, "destaque": [], "falas": r["falas"]}
    (pasta / "projeto.json").write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    e = {"mundo": mundo, "atos": at, "final": "" if "ALGO" in str(r.get("titulo_curto") or "").upper() else str(r.get("titulo_curto") or ""), "rede": bool(receitas()[k].get("rede")), "semente": sum(map(ord, tema)) % 97 + 3}
    (pasta / "espec.json").write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")
    escrever(pasta, e)
    return p


def escrever(pasta: Path, e: dict[str, Any]) -> None:
    js = [(BIB / "base.js").read_text(encoding="utf-8")] + [f.read_text(encoding="utf-8") for f in sorted((BIB / "itens").glob("*.js"))]
    (pasta / "cena.js").write_text(f"window.ESPEC={json.dumps(e, ensure_ascii=False)};\n" + "\n".join(js) + "\n" + (BIB / "motor.js").read_text(encoding="utf-8"), encoding="utf-8")


if __name__ == "__main__":
    pasta = Path(sys.argv[2])
    if not (pasta / "espec.json").exists():
        print(json.dumps(montar(sys.argv[1], pasta)["falas"], ensure_ascii=False, indent=0))
    else:
        escrever(pasta, json.loads((pasta / "espec.json").read_text(encoding="utf-8")))
    modo = sys.argv[3] if len(sys.argv) > 3 else "previa"
    sys.exit(subprocess.run([sys.executable, "-m", "lidark.construcao.render", str(pasta), modo]).returncode)
