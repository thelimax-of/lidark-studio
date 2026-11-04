"""Projetos do canal em disco, IA de roteiro e de cena, e tarefas de criação e render."""
from __future__ import annotations

import json
import re
import logging
import shutil
import subprocess
import sys
import time
import unicodedata
import uuid
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .. import llm
from ..config import MEDIA_DIR, ROOT
from ..db import session
from ..jobs import JobContext, enqueue, handler
from ..models import Channel, Script, Video
from . import BASE, MOTOR

log = logging.getLogger(__name__)
PY = sys.executable
TENTATIVAS = 4
CENARIOS = ("sitio", "praia", "serra", "cidade", "bairro")
NOTA_MIN = 8
NOTA_ACEITA = 6  # abaixo disso o vídeo não é entregue
BACKEND = ROOT / "backend"
PADRAO = {"voz": "pt-BR-AntonioNeural", "rate": "+8%", "destaque": [], "tags": [], "descricao": "", "status": "roteiro", "erro": "", "video_id": None}


def _slug(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = re.sub(r"[^a-z0-9]+", "-", "".join(c for c in s if not unicodedata.combining(c))).strip("-")
    return s[:50] or "projeto"


def pasta(pid: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]+", pid):
        raise ValueError("identificador inválido")
    return BASE / pid


def _ler_json(f: Path) -> dict[str, Any]:
    """No Windows a leitura falha se o arquivo estiver sendo trocado por salvar()."""
    for i in range(40):
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except PermissionError:
            if i == 39:
                raise
            time.sleep(.05)
    raise OSError(f)


def ler(pid: str) -> dict[str, Any]:
    return _ler_json(pasta(pid) / "projeto.json")


def salvar(p: dict[str, Any]) -> dict[str, Any]:
    """Grava com arquivo temporário próprio; no Windows a troca falha se outro processo estiver lendo."""
    d = pasta(p["id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / f"projeto.{uuid.uuid4().hex}.tmp"
    tmp.write_text(json.dumps(p, ensure_ascii=False, indent=1), encoding="utf-8")
    for i in range(20):
        try:
            tmp.replace(d / "projeto.json")
            return p
        except PermissionError:
            if i == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(.05)
    return p


def listar() -> list[dict[str, Any]]:
    if not BASE.exists():
        return []
    out = []
    for f in BASE.glob("*/projeto.json"):
        p = _ler_json(f)
        p["tem_cena"] = (f.parent / "cena.js").exists()
        p["tem_previa"] = (f.parent / "previa.jpg").exists()
        out.append(p)
    return sorted(out, key=lambda x: x.get("criado", ""), reverse=True)


def novo(cid: int, tema: str) -> dict[str, Any]:
    from ..models import now
    base = _slug(tema)
    pid, n = base, 2
    while pasta(pid).exists():
        pid, n = f"{base}-{n}", n + 1
    return salvar({**PADRAO, "id": pid, "channel_id": cid, "tema": tema, "titulo": f"Como construir {tema} do zero, parte por parte", "falas": [], "criado": now().isoformat()})


SYS_J = "Responda só JSON válido."
CATALOGO = """Elementos disponíveis, medidas em metros. x é a largura, z positivo é a frente e y é a altura. O centro da obra fica em x=0, z=0.
terra {x,z,l,p}: escavação. laje {x,z,y,l,p,a,mat}: placa ou base que se espalha. caixa {x,z,y,l,a,p,mat,ry}: bloco. pilar {x,z,y,a,l,mat}: sobe do chão.
parede {de:[x,z],ate:[x,z],y,alt,mat,vaos:[{pos,lar,base,alt}]}: tijolos em fiadas; pos é a distância a partir de "de". mat: tijolo, bloco ou cor #rrggbb.
cupula {x,y,z,r,mat}: abóbada de tijolos, como a de um forno. telhado {x,z,y,l,p,alt}: tesouras, ripas e telhas de duas águas sobre um retângulo l por p apoiado na altura y.
tabuas {x,z,y,l,p,n,mat,dir}: deck ou portão de tábuas. piso {x,z,y,l,p,mat,tam}: lajotas. degraus {x,z,l,n,alt,f,ry}. cilindro {x,z,y,r,a,mat}: tanque ou caixa-d'água.
tubo {pontos:[[x,y,z],...],r,mat}: cano. acabamento {de,ate,y,alt,vaos,cor}: chapisco, reboco ou pintura sobre uma parede; use as mesmas medidas da parede e nunca repita uma parede para isso. portao {x,z,y,l,a,mat}: portão de grades que abre. forro {x,z,y,l,a,p,cor}: revestimento oco de um tanque ou piscina, com fundo e quatro lados. Em piscina e tanque enterrado, use terra grande e forro com y negativo, nunca caixa. grelha {x,y,z,l,p}. porta {x,z,y,l,a,ry}. janela {x,z,y,l,a,ry}. agua {x,z,l,p,y0,y1}: água subindo. planta {x,z,y,h}.
mat aceita: concreto, madeira, metal, pedra, branco, preto, telha, vermelho, azul, verde, amarelo, areia, ceramica ou #rrggbb.
Efeitos de "uso" no clipe final: {t:"cachorro",de:[x,z],ate:[x,z]}; {t:"fogo",x,y,z}; {t:"fumaca",x,y,z}; {t:"comida",x,y,z}; {t:"chuva"}; {t:"pessoa",de:[x,z],ate:[x,z],cor}; {t:"abre",id}; {t:"ondas",x,y,z}; {t:"galinha",n}; {t:"mergulho",x,z,y} para piscina. Fogo e fumaça só em churrasqueira, forno, lareira e parecidos."""
TIPOS = set("cupula laje caixa pilar cilindro tubo grelha tabuas terra piso parede telhado porta janela degraus agua planta forro portao acabamento".split())
MODELOS = {'garagem': 'garagem', 'galinheiro': 'galinheiro', 'tanque': 'tanque peixes lago', 'forno': 'forno pizza lenha assar padaria', 'cobertura': 'varanda pergolado quiosque cobertura deck telheiro gazebo caramanchão coberta','churrasqueira': 'churrasqueira forno lareira fogão fogo tijolo', 'casinha': 'casinha cachorro abrigo quartinho depósito edícula', 'muro': 'muro portão cerca parede divisória fachada', 'piscina': 'piscina tanque lago fosso poço enterrado'}


def _pl(x: str) -> set[str]:
    return set(x.lower().split())


def _sem_acento(x: str) -> str:
    return unicodedata.normalize("NFD", x.lower()).encode("ascii", "ignore").decode()


def modelo_do_tema(tema: str) -> str | None:
    """Modelo feito à mão que serve para o tema. A obra sai dele, sem a IA desenhar nada."""
    pal = set(_sem_acento(tema).split())
    for k, v in MODELOS.items():
        if pal & set(_sem_acento(v).split()):
            return k
    return None


def mestre_do_tema(tema: str) -> str | None:
    """Cena-mestra feita à mão que serve para o tema: o nível mais alto de qualidade do gerador."""
    pal = set(_sem_acento(tema).split()) - {"um", "uma", "a", "o", "de", "do", "da"}
    ota = {f.stem: len(pal & set(_sem_acento(json.loads(f.read_text(encoding="utf-8"))["chaves"]).split())) for f in (MOTOR / "mestres").glob("*.json")}
    k = max(ota, key=ota.get, default=None)
    return k if k and ota[k] else None


def biblioteca() -> list[dict[str, Any]]:
    """Tudo o que o sistema faz sozinho, no nível mais alto."""
    out = []
    for f in sorted((MOTOR / "mestres").glob("*.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        out.append({"chave": f.stem, "tema": m["tema"], "categoria": m.get("categoria", "Obras")})
    return sorted(out, key=lambda x: (x["categoria"], x["tema"]))


def sabe_fazer(tema: str) -> bool:
    return bool(mestre_do_tema(tema) or modelo_do_tema(tema))


def _mestre(k: str) -> dict[str, Any]:
    return json.loads((MOTOR / "mestres" / f"{k}.json").read_text(encoding="utf-8"))


def roteiro_mestre(p: dict[str, Any], k: str) -> dict[str, Any]:
    """A cena já existe: a IA só escreve uma narração nova, curta e simples, por cima das etapas dela."""
    m, tema = _mestre(k), p["tema"]
    et, ex = m["etapas"], m["exemplo"]
    a, b = m["palavras"]
    pede = "\n".join(f"Fala {i}: " + ("mostra o erro de quem não faz, começando com \"Se você\"" if i == 0 else f"começa com \"Parabéns, você construiu\" e termina com uma pergunta para os comentários" if i == len(et) - 1 else f"{x['o']}; use a palavra exata \"{x['palavra']}\"") for i, x in enumerate(et))
    usada = any(q.get("mestre") == k and q["id"] != p["id"] and not q.get("teste") for q in listar())
    if not usada:  # primeira vez: a narração feita à mão é a melhor que existe
        r, f = {"titulo": f"Como construir {tema} do zero #Shorts"}, list(ex)
    else:
        fb, erro = "", ""
        for n in range(6):
            r = llm.complete_json(f"""Escreva a narração de um vídeo curto: construir {tema}, falando direto com "você".
    Exatamente {len(et)} falas, nesta ordem:
    {pede}

    Regras:
    - De {a} a {b} palavras no total. Frases curtas, de conversa. Uma criança de dez anos entende.
    - Cada termo técnico vem com uma explicação simples ou uma comparação do dia a dia, como "são as costelas do telhado".
    - Cada fala explica por que aquilo existe: o problema que resolve. Varie as ligações: Então, Mas, Só que, Agora.
    - Sem algarismos, medidas, porcentagens ou temperaturas.

    Este é o nível esperado. Não copie, escreva outras frases, comparações e outra pergunta final:
    {json.dumps(ex, ensure_ascii=False)}
    {fb}
    Pedido {uuid.uuid4().hex[:8]}.
    JSON: {{"titulo": "Como construir ... do zero #Shorts", "falas": ["..."]}}""", system=SYS_J, temperature=.75)
            r = getattr(r, "data", r)
            f = [str(x).strip() for x in r.get("falas", []) if str(x).strip()] if isinstance(r, dict) else []
            np = sum(len(x.split()) for x in f)
            falta = [x["palavra"] for i, x in enumerate(et) if x.get("palavra") and i < len(f) and x["palavra"] not in f[i].lower()]
            iguais = sum(1 for x, y in zip(f, ex) if SequenceMatcher(None, x, y).ratio() > .75)
            erro = ("" if len(f) == len(et) else f"tem {len(f)} falas, precisa de {len(et)}. ") + ("" if a - 10 <= np <= b + 15 else f"tem {np} palavras, precisa ter de {a} a {b}. ") + (f"faltaram as palavras {falta}. " if falta else "") + ("tem algarismos. " if re.search(r"\d", " ".join(f)) else "") + (f"{iguais} falas copiam o exemplo: reescreva com outras palavras e outras comparações. " if iguais > 3 else "") + ("" if f and f[0].startswith("Se você") and f[-1].startswith("Parabéns, você construiu") else "a primeira ou a última fala não começa como pedido. ")
            if not erro:
                break
            fb = f"\nA versão anterior foi recusada: {erro}"
        else:
            raise RuntimeError("A IA não seguiu a cena-mestra: " + erro)
    p.update(mestre=k, modo="mestre", titulo=f"Como construir {tema} do zero #Shorts", falas=f, rate=m["rate"], zoom=m["zoom"], destaque=[x["palavra"] for x in et if x.get("palavra")], tags=[re.sub(r"^(um|uma)\s+", "", tema), "como construir", "construção", "obra", "parte por parte", "animação 3D", *[x["palavra"] for x in et if x.get("palavra")][:4]], descricao=p.get("descricao") or f"Como construir {tema} do zero, parte por parte.\n\n{f[-1].split('!', 1)[-1].strip()}\n\nVídeo educativo em animação 3D, com o processo simplificado. Uma obra real precisa de projeto e de um profissional habilitado.\n\n#parteporparte #construcao #shorts")
    return salvar(p)


def _modelo(k: str) -> dict[str, Any]:
    return json.loads((MOTOR / "modelos" / f"{k}.json").read_text(encoding="utf-8"))


def gerar_roteiro(p: dict[str, Any]) -> dict[str, Any]:
    tema = p["tema"]
    if k_ := mestre_do_tema(tema):
        return roteiro_mestre(p, k_)
    c = llm.complete_json(f'Classifique o tema "{tema}". "obra": algo que um pedreiro constrói num quintal ou terreno, com tijolo, concreto, madeira, telhas ou canos. "objeto": um objeto físico que se monta com peças, como ventilador, liquidificador, bicicleta, relógio ou rádio. "nao": qualquer outra coisa. Responda JSON {{"tipo": "obra", "objeto" ou "nao"}}.', system=SYS_J, temperature=0)
    tipo = c_.get("tipo") if isinstance(c_ := getattr(c, "data", c), dict) else "obra"
    if tipo == "nao":
        raise ValueError(f"\"{tema}\" não é uma obra nem um objeto que se monta. Tente algo como garagem, forno, ventilador ou bicicleta.")
    p["modo"] = "objeto" if tipo == "objeto" else "obra"
    objeto = p["modo"] == "objeto"
    k = None if objeto else modelo_do_tema(tema)
    fixas = ""
    regra = "- De 11 a 13 falas, 250 a 300 palavras no total. Cada fala é uma etapa física visível" + (" da montagem: uma peça real do objeto, com nome técnico. O objeto é montado de pé, de baixo para cima: a fala 1 já é a base que fica no chão, a fala 2 é o que sustenta o resto, como coluna ou chassi, e cada peça seguinte se apoia no que já foi montado. Nada é montado no ar para depois ser posto na base." if objeto else " da obra, em ordem real.")
    if k:
        et = _modelo(k)["etapas"]
        fixas = "\n".join(f"Fala {i}: " + ("o erro de quem faz errado" if i == 0 else "os parabéns" if i == len(et) - 1 else f"etapa {x.get('rotulo')}, contendo a palavra exata \"{x.get('palavra')}\"") for i, x in enumerate(et))
        regra = f"- Exatamente {len(et)} falas, 250 a 300 palavras no total, nesta ordem, sem etapa a mais:\n{fixas}"
    r = None
    for _ in range(3):
        r = _pedir_roteiro(tema, regra, objeto)
        if not k or len(r.get("falas", [])) == len(_modelo(k)["etapas"]):
            break
    else:
        raise RuntimeError("A IA não seguiu as etapas da obra")
    p["modelo"] = k
    falas = [str(x).strip() for x in r.get("falas", []) if str(x).strip()]
    if len(falas) < 6:
        raise RuntimeError("A IA devolveu um roteiro curto demais")
    for _ in range(3):
        n = sum(len(f.split()) for f in falas)
        if n >= 255 and not re.search(r"\d", " ".join(falas)):
            break
        x = llm.complete_json(f"Este roteiro tem {n} palavras e precisa ter de 260 a 300. Deixe cada fala mais rica, com mais detalhes técnicos corretos e o motivo de cada etapa, sem nenhum algarismo nem medida exata, mantendo a mesma quantidade de falas, as mesmas etapas, a primeira e a última frase. Responda JSON {{\"falas\": [...]}}.\n{json.dumps(falas, ensure_ascii=False)}", system=SYS_J, temperature=.5)
        x = getattr(x, "data", x)
        if isinstance(x, dict) and len(x.get("falas", [])) == len(falas):
            falas = [str(f).strip() for f in x["falas"]]
    p.update(titulo=r.get("titulo") or p["titulo"], falas=falas, destaque=r.get("destaque", []), descricao=p.get("descricao") or (f"Como construir {tema} do zero, peça por peça.\n\n{falas[-1].split('!', 1)[-1].strip()}\n\nVídeo educativo em animação 3D, com o processo simplificado. Não mexa em aparelhos ligados na tomada: consertos elétricos pedem um profissional habilitado.\n\n#parteporparte #comofunciona #shorts" if objeto else f"Como construir {tema} do zero, etapa por etapa.\n\nVídeo educativo em animação 3D, com o processo simplificado. Uma obra real precisa de projeto e de um profissional habilitado."))
    if objeto and not p.get("tags"):
        p["tags"] = [re.sub(r"^(um|uma)\s+", "", tema), "como funciona", "como construir", "animação 3D", "parte por parte", *[str(x) for x in r.get("destaque", [])[:5]]]
    return salvar(p)


def _pedir_roteiro(tema: str, regra: str, objeto: bool = False) -> dict[str, Any]:
    abre = f"um montador constrói isso numa oficina, peça por peça, do zero" if objeto else "um pedreiro constrói isso num quintal, do zero"
    exs = """"Se você encaixar a lâmina direto no motor, sem vedação, o suco desce e queima tudo na primeira semana."
"Mas o motor sozinho aquece demais. Então, por baixo, você prende uma ventoinha que puxa ar frio."
"Parabéns, você construiu um liquidificador! Agora me diz: qual vitamina vai primeiro aí? Responde aqui.\"""" if objeto else """"Se você montar uma churrasqueira direto na terra, o peso e o calor racham tudo no primeiro ano."
"Mas o calor do fogo destruiria um tijolo comum. Então, por dentro, você assenta tijolos refratários."
"Parabéns, você construiu uma churrasqueira! Agora me diz: qual carne vai primeiro aí? Responde aqui.\""""
    r = llm.complete_json(f"""Tema: construir {tema}. Escreva a narração de um vídeo em que {abre}.
Estilo destes exemplos:
{exs}
Regras:
- Fala direto com "você". A primeira fala começa com "Se você" e já mostra um erro real de quem faz errado.
{regra}
- Varie as ligações: Então, Mas, Só que, Agora, Depois, Por fim. Cada etapa diz o nome técnico e por que ela existe.
- A última fala começa com "Parabéns, você construiu" e termina com uma pergunta para os comentários.
- Só informações corretas. Não cite temperaturas, porcentagens nem medidas exatas.
- "Por fim" só pode aparecer na penúltima fala.
JSON: {{"titulo": "Como construir ... do zero #Shorts", "falas": ["..."], "destaque": ["palavras técnicas ditas"]}}""", system=SYS_J, temperature=.6)
    return getattr(r, "data", r)


def reparar(e: Any, n: int) -> None:
    """Uma etapa por fala, nenhum elemento perdido e as etapas do meio cheias quando há sobra por perto."""
    if not isinstance(e, dict):
        return
    el = [x for x in e.get("elementos", []) if isinstance(x, dict) and x.get("id")]
    e["elementos"] = el
    ids = [x["id"] for x in el]
    por = {i: {"fala": i, "elementos": []} for i in range(n)}
    for t_ in e.get("etapas", []):
        if isinstance(t_, dict) and isinstance(t_.get("fala"), int) and 0 <= t_["fala"] < n:
            por[t_["fala"]].update({k: v for k, v in t_.items() if k != "elementos"})
            por[t_["fala"]]["elementos"] += [i for i in t_.get("elementos", []) if i in ids]
    por[0]["elementos"], por[n - 1]["elementos"], extra = [], [], por[0]["elementos"] + por[n - 1]["elementos"]
    usados = {i for t_ in por.values() for i in t_["elementos"]}
    fila = extra + [i for i in ids if i not in usados and i not in extra]
    meio = [por[i] for i in range(1, n - 1)]
    for i in fila:
        min(meio, key=lambda t_: len(t_["elementos"]))["elementos"].append(i)
    for k, t_ in enumerate(meio):
        if t_["elementos"]:
            continue
        viz = [q for q in meio if len(q["elementos"]) > 1]
        if viz:
            q = min(viz, key=lambda v: abs(meio.index(v) - k))
            t_["elementos"].append(q["elementos"].pop())
    e["etapas"] = [por[i] for i in range(n)]


def erros_espec(e: Any, n_falas: int) -> str:
    if not isinstance(e, dict):
        return "resposta inválida"
    el, et, r = e.get("elementos", []), e.get("etapas", []), []
    if len(el) < 8:
        r.append("poucos elementos")
    bad = {x.get("tipo") for x in el if isinstance(x, dict)} - TIPOS
    if bad:
        r.append(f"tipos inexistentes {bad}")
    ids = {x.get("id") for x in el if isinstance(x, dict)}
    usados = [i for t_ in et for i in t_.get("elementos", [])]
    if ids - set(usados):
        r.append(f"elementos sem etapa {sorted(map(str, ids - set(usados)))}")
    if sum(1 for t_ in et if 0 < t_.get("fala", 0) < n_falas - 1 and not t_.get("elementos")) > max(2, n_falas // 4):
        r.append("etapas demais sem elemento")
    return "; ".join(r)


CATALOGO_OBJ = """Todo item tem tipo "peca", id, forma, x, y, z (x,y,z é o CENTRO da peça, em metros), mat e, se quiser, vem:[dx,dy,dz], de onde a peça chega ao ser encaixada.
Formas:
cilindro {eixo:"x"|"y"|"z", r, r2, a}: cilindro de raio r e comprimento a ao longo do eixo; com r2 vira cone, e r2 é o raio na ponta positiva do eixo.
caixa {l, a, p, ry}: bloco de largura l (x), altura a (y) e profundidade p (z).
esfera {r, esc:[sx,sy,sz]}: esfera, achatada ou esticada por esc.
anel {eixo, r, tubo}: aro redondo.
bobina {eixo, r, a, tubo}: enrolamento de fio de cobre.
helice {eixo, r, n, passo}: hélice ou lâminas com n pás e cubo central.
grade {eixo, r, prof, lado, n, aneis}: grade de proteção abaulada com aros e raios. lado 1 abaula para a ponta positiva do eixo, -1 para a negativa. O aro fica no centro informado. Com prof 0 vira os raios de uma roda.
Além de peca, existe tubo {pontos:[[x,y,z],...], r, mat}: cabo ou cano.
mat: metal, cobre, preto, branco, vermelho, azul, verde, amarelo, madeira ou #rrggbb.
Efeitos de "uso" no clipe final: {t:"gira",ids:[peças que giram]}; {t:"oscila",ids:[TODAS as peças da parte que balança],x,z,amp}: balança em torno do eixo vertical em x,z; {t:"vento",x,y,z,r}: vento e papéis voando a partir de x,y,z para a frente; {t:"luz",x,y,z,r,cor}: acende uma luz em x,y,z e a oficina escurece, para lâmpadas e faróis; {t:"pessoa",de:[x,z],ate:[x,z],cor}."""
FORMAS = {"cilindro", "caixa", "esfera", "anel", "bobina", "helice", "grade"}


def _caixa_peca(e: dict[str, Any]) -> tuple[list[float], list[float]]:
    if e.get("tipo") == "tubo":
        pts, r_ = e.get("pontos") or [[0, 0, 0]], e.get("r", .03)
        return [min(q[i] for q in pts) - r_ for i in range(3)], [max(q[i] for q in pts) + r_ for i in range(3)]
    f, r_ = e.get("forma", "caixa"), e.get("r", .3)
    if f == "caixa":
        h = [e.get("l", .5) / 2, e.get("a", .3) / 2, e.get("p", .5) / 2]
    elif f == "esfera":
        h = [r_ * v for v in (e.get("esc") or [1, 1, 1])]
    else:
        ax = {"grade": e.get("prof", r_ * .35), "anel": e.get("tubo", .03), "helice": r_ * .14}.get(f, e.get("a", .3) / 2)
        rr = max(r_, e.get("r2", 0)) + (e.get("tubo", .03) if f == "anel" else 0)
        i = "xyz".index(e.get("eixo", "z")) if e.get("eixo", "z") in ("x", "y", "z") else 2
        h = [rr, rr, rr]
        h[i] = ax
    c = [e.get("x", 0), e.get("y", 0), e.get("z", 0)]
    return [c[i] - h[i] for i in range(3)], [c[i] + h[i] for i in range(3)]


def pecas_soltas(el: list[dict[str, Any]], folga: float = .05, chao: float | None = None) -> list[str]:
    """Peças que não se ligam ao chão por uma corrente de peças encostadas."""
    cx = {e["id"]: _caixa_peca(e) for e in el}
    chao = min(a[1] for a, _ in cx.values()) if chao is None else chao
    ligadas = {i for i, (a, _) in cx.items() if a[1] <= chao + .08}
    fila = list(ligadas)
    while fila:
        a0, b0 = cx[fila.pop()]
        for i, (a, b) in cx.items():
            if i not in ligadas and all(a[k] <= b0[k] + folga and b[k] >= a0[k] - folga for k in range(3)):
                ligadas.add(i)
                fila.append(i)
    return sorted(set(cx) - ligadas)


def _girar_objeto(e: dict[str, Any]) -> None:
    """Gira o objeto 90 graus em torno da vertical, para a lateral ficar de frente."""
    for q in e["elementos"]:
        if "pontos" in q:
            q["pontos"] = [[v[2], v[1], -v[0]] for v in q["pontos"]]
        q["x"], q["z"] = q.get("z", 0), -q.get("x", 0)
        if q.get("forma") == "caixa":
            q["l"], q["p"] = q.get("p", .5), q.get("l", .5)
        elif q.get("eixo") in ("x", "z"):
            q["eixo"] = "z" if q["eixo"] == "x" else "x"
        if isinstance(q.get("vem"), list) and len(q["vem"]) == 3:
            q["vem"] = [q["vem"][2], q["vem"][1], -q["vem"][0]]
    for f in e.get("uso", {}).get("efeitos", []):
        if isinstance(f, dict) and f.get("t") != "pessoa" and "x" in f:
            f["x"], f["z"] = f.get("z", 0), -f.get("x", 0)


def _ajustar_objeto(e: dict[str, Any]) -> None:
    """Põe o objeto no chão, com a altura que o enquadramento espera."""
    el = e["elementos"]
    cxs = [_caixa_peca(q) for q in el]
    lx, lz = (max(b[i] for _, b in cxs) - min(a[i] for a, _ in cxs) for i in (0, 2))
    if lz > lx * 1.2:  # comprido na direção da câmera: gira para mostrar o perfil
        _girar_objeto(e)
        cxs = [_caixa_peca(q) for q in el]
    y0 = min(a[1] for a, _ in cxs)
    maior = max(max(b[i] for _, b in cxs) - min(a[i] for a, _ in cxs) for i in range(3))
    s_ = 2.8 / maior if maior > 0 and not 2.3 <= maior <= 3.2 else 1
    for q in el:
        if "pontos" in q:
            q["pontos"] = [[v[0] * s_, (v[1] - y0) * s_, v[2] * s_] for v in q["pontos"]]
        q["y"] = (q.get("y", 0) - y0) * s_
        for c in ("x", "z", "r", "r2", "a", "l", "p", "tubo", "prof"):
            if c in q:
                q[c] *= s_
        if isinstance(q.get("vem"), list) and len(q["vem"]) == 3 and q["vem"][1] < 0:
            q["vem"][1] = -q["vem"][1]
    for f in e.get("uso", {}).get("efeitos", []):
        if isinstance(f, dict):
            for c in ("x", "z", "r"):
                if c in f and isinstance(f[c], (int, float)):
                    f[c] *= s_
            if "y" in f:
                f["y"] = (f["y"] - y0) * s_


def _ordenar_montagem(e: Any) -> None:
    """Peça sem apoio na sua etapa passa para a primeira etapa em que já tenha onde se apoiar."""
    try:
        el, ets = e["elementos"], sorted(e["etapas"], key=lambda v: v["fala"])
        por_id = {x["id"]: x for x in el}
        chao = min(_caixa_peca(x)[0][1] for x in el)
        if pecas_soltas(el, chao=chao):
            return  # solta na peça pronta: isso só a IA corrige
        ate: list[dict[str, Any]] = []
        for i, t_ in enumerate(ets[:-2]):
            ate += [por_id[k] for k in t_["elementos"] if k in por_id]
            ar = set(pecas_soltas(ate, chao=chao)) if ate else set()
            if ar:
                t_["elementos"] = [k for k in t_["elementos"] if k not in ar]
                ets[i + 1]["elementos"] = [k for k in ar if k in por_id] + ets[i + 1]["elementos"]
                ate = [x for x in ate if x["id"] not in ar]
    except (KeyError, TypeError, ValueError, IndexError):
        return


def erros_objeto(e: Any, n_falas: int) -> str:
    if not isinstance(e, dict):
        return "resposta inválida"
    el, r = e.get("elementos", []), []
    if len(el) < 14:
        r.append(f"só {len(el)} peças: faça de 16 a 24, somando detalhes reais do objeto, como parafusos grandes, anéis, botões e cabos")
    if {x.get("tipo") for x in el} - {"peca", "tubo"}:
        r.append("só existem os tipos peca e tubo")
    if {x.get("forma") for x in el if x.get("tipo") == "peca"} - FORMAS:
        r.append("forma inexistente")
    ids = {x.get("id") for x in el}
    if ids - {i for t_ in e.get("etapas", []) for i in t_.get("elementos", [])}:
        r.append("há peças sem etapa")
    if sum(1 for t_ in e.get("etapas", []) if t_.get("elementos")) < 6:
        r.append("a montagem precisa crescer em pelo menos 6 etapas")
    if not any(isinstance(x, dict) and x.get("t") in ("gira", "vento", "luz") for x in e.get("uso", {}).get("efeitos", [])):
        r.append("o uso não mostra o objeto funcionando: use gira, vento ou luz")
    if not r:
        try:
            cx = [_caixa_peca(x) for x in el]
            med = [max(b[i] for _, b in cx) - min(a[i] for a, _ in cx) for i in range(3)]
            y0 = min(a[1] for a, _ in cx)
            pe = [(a, b) for a, b in cx if a[1] <= y0 + .15]
            apoio = max(max(b[0] for _, b in pe) - min(a[0] for a, _ in pe), max(b[2] for _, b in pe) - min(a[2] for a, _ in pe))
            miudas = sum(1 for a, b in cx if max(b[i] - a[i] for i in range(3)) < .07 * max(med))
        except (TypeError, ValueError, KeyError, IndexError) as x:
            return f"medidas inválidas: {x}"
        if max(med[0], med[2]) < .4 * med[1]:
            r.append(f"objeto fino demais: tem {med[1]:.2f} de altura e só {max(med[0], med[2]):.2f} de largura. Mantenha a proporção real e engrosse as peças: é um objeto pequeno visto de perto, não um poste")
        if apoio < .35 * med[1]:
            r.append(f"a base tem só {apoio:.2f} para {med[1]:.2f} de altura e o objeto tombaria: alargue a base")
        if miudas > len(el) * .5:
            r.append(f"{miudas} peças são pequenas demais para aparecer no vídeo: aumente os detalhes, mais da metade das peças precisa ter ao menos 8% do tamanho do objeto")
    if not r:
        try:
            s_ = pecas_soltas(el)
        except (TypeError, ValueError, KeyError, IndexError) as x:
            return f"medidas inválidas: {x}"
        if s_:
            r.append(f"peças soltas no ar, que não encostam em nenhuma outra: {s_}. Mova cada uma até tocar a peça que a sustenta")
        else:
            chao = min(_caixa_peca(x)[0][1] for x in el)
            por_id, ate = {x["id"]: x for x in el}, []
            for t_ in sorted(e.get("etapas", []), key=lambda v: v.get("fala", 0)):
                ate += [por_id[i] for i in t_.get("elementos", []) if i in por_id]
                ar = pecas_soltas(ate, chao=chao) if ate else []
                if ar:
                    r.append(f"na etapa da fala {t_.get('fala')} as peças {ar} ficam no ar, porque o que as sustenta só entra depois. Em cada etapa tudo que já foi montado precisa estar ligado ao chão: a base e a estrutura vêm nas primeiras falas")
                    break
    return "; ".join(r)


def gerar_objeto(p: dict[str, Any], retorno: str = "") -> dict[str, Any]:
    tema, falas = p["tema"], p["falas"]
    exe = (MOTOR / "modelos" / "_objeto_exemplo.json").read_text(encoding="utf-8")
    msg = f"""Projete, peça por peça, o objeto deste vídeo: {tema}. Ele será montado numa oficina como uma maquete grande e tem que ser reconhecido à primeira vista.
Narração (índice: texto):
{chr(10).join(f'{i}: {f}' for i, f in enumerate(falas))}

{CATALOGO_OBJ}

Regras:
- A maior medida do objeto fica entre 2,4 e 2,9. Ele fica em pé no chão (a peça mais baixa toca y=0), centrado em x=0, z=0. Objeto comprido, como bicicleta, fica ao longo de x.
- Pense nas medidas reais do objeto e mantenha as proporções reais: nunca estique a altura para caber nas medidas. Calcule o centro de cada peça: toda peça encosta de verdade em outra e nada fica no ar.
- Objeto pequeno na vida real, como luminária ou liquidificador, vira uma maquete encorpada: mantém as proporções dele, com peças largas e bem visíveis, nunca um poste fino.
- Em cone, confira para que lado ele abre: r é a ponta negativa do eixo e r2 a ponta positiva. Uma cúpula de luminária abre para baixo.
- De 14 a 26 peças, com detalhe: use as formas certas, não troque tudo por caixa. Cores bonitas e diferentes para as partes, como num produto real.
- Uma etapa por fala, na mesma ordem, com "palavra" exata da fala. Cada peça entra numa etapa só, na etapa da fala que a cita. As falas 0 e a última não trazem peças.
- rotulo curto, em maiúsculas. "final" é o nome do objeto com PRONTO!, em maiúsculas.
- A montagem é sempre de pé e de baixo para cima: a cada etapa, tudo o que já entrou está ligado ao chão por peças encostadas. A base e a estrutura entram primeiro.
- Use "vem" para a peça chegar pelo lado certo do encaixe, nunca de baixo do chão. "uso" mostra o objeto funcionando de verdade com gira, vento ou luz, sempre com uma pessoa.

Exemplo aprovado de outro objeto, copie a organização e o nível de detalhe, sem copiar as peças:
{exe}

Responda só o JSON com as chaves final, elementos, etapas e uso."""
    fb = f"\n\nUma versão anterior foi reprovada por: {retorno}\nFaça uma versão nova, sem esses problemas." if retorno else ""
    for _ in range(4):
        e = llm.complete_json(f"{msg}{fb}\n\nProjeto {uuid.uuid4().hex[:8]}.", system=SYS_J, temperature=.5)
        e = getattr(e, "data", e)
        reparar(e, len(falas))
        _ordenar_montagem(e)
        er = erros_objeto(e, len(falas))
        if not er:
            break
        fb = f"\n\nA versão anterior foi recusada: {er}. Corrija."
    else:
        raise ValueError(er)
    _ajustar_objeto(e)
    u_ = e.setdefault("uso", {})
    u_["efeitos"] = [x for x in u_.get("efeitos", []) if isinstance(x, dict) and x.get("t") in ("gira", "oscila", "vento", "luz", "pessoa")]
    if not any(x["t"] == "pessoa" for x in u_["efeitos"]):
        u_["efeitos"].append({"t": "pessoa", "de": [3, 3], "ate": [1.6, 2.4], "cor": "#e8683f"})
    e.update(modo="objeto", cenario="oficina", paleta=sum(map(ord, p["id"])) % 4)
    return e


def gerar_espec(p: dict[str, Any], retorno: str = "") -> dict[str, Any]:
    if p.get("mestre"):
        m = _mestre(p["mestre"])
        n = sum(map(ord, p["id"]))
        return {"mestre": p["mestre"], "semente": 31 + n % 97, "variante": m["variantes"][n % len(m["variantes"])], "cauda": m["cauda"]}
    if p.get("modo") == "objeto":
        return gerar_objeto(p, retorno)
    tema, falas = p["tema"], p["falas"]
    k = p.get("modelo") or modelo_do_tema(tema)
    if k:
        m = _modelo(k)
        if len(m["etapas"]) == len(falas):
            for x in m["etapas"]:
                if x.get("palavra") and x["palavra"].lower() not in falas[x["fala"]].lower():
                    x.pop("palavra")
            m["cenario"] = proximo_cenario(p["id"])
            return m
    rank = sorted(MODELOS, key=lambda k: -len(_pl(MODELOS[k]) & _pl(tema)))
    EXE = "\n\n".join(f"Modelo aprovado ({k}):\n" + (MOTOR / "modelos" / f"{k}.json").read_text(encoding="utf-8") for k in rank[:2])
    CAT = CATALOGO
    msg = f"""Projete a obra deste vídeo usando somente os elementos do catálogo. Tema: {tema}.
Narração (índice: texto):
{chr(10).join(f'{i}: {f}' for i, f in enumerate(falas))}

{CAT}

Regras:
- Medidas reais de um quintal: a obra cabe em até 6 de largura, 5 de profundidade e 4,5 de altura, e tudo se encosta de verdade: parede em cima da laje usa y igual ao topo da laje, telhado apoia no topo das paredes ou pilares.
- Paredes em volta formam um volume fechado de verdade, com cantos que se tocam. Use vaos para porta e janela e coloque porta e janela exatamente no vão.
- Uma etapa por fala, na mesma ordem, com "palavra" exata da fala. Cada elemento entra numa etapa só. As falas 0 e a última não trazem elementos. A etapa de cada fala traz exatamente as peças que aquela fala narra: nunca adiante nem atrase uma peça. Fala que só explica um problema, sem peça nova, fica com elementos vazios.
- rotulo curto, em maiúsculas.
- "uso" mostra a obra funcionando, de 2 a 4 efeitos, sempre com uma pessoa.

- Use só os tipos do catálogo. Nunca invente tipo novo. Evite caixa: construa com parede, laje, pilar, telhado, piso e cupula, porque são os elementos bonitos.
- Para reboco e pintura use acabamento. Nunca ponha caixa sobre uma parede.
- Dê de 10 a 20 elementos. Paredes e telhado são o que mais impressiona: prefira eles a caixas.

Modelos aprovados: copie a organização e o detalhe, adaptando ao tema:
{EXE}

Responda só o JSON com as chaves final, elementos, etapas e uso."""
    fb = f"\n\nUma versão anterior foi reprovada por: {retorno}\nFaça uma versão nova, sem esses problemas." if retorno else ""
    for _ in range(3):
        e = llm.complete_json(msg + fb, system=SYS_J, temperature=.4)
        e = getattr(e, "data", e)
        reparar(e, len(falas))
        er = erros_espec(e, len(falas))
        if not er:
            break
        fb = f"\n\nA versão anterior foi recusada: {er}. Corrija."
    else:
        raise ValueError(er)
    if not re.search("churras|forno|lareira|fog", tema, re.I):
        e.setdefault("uso", {})["efeitos"] = [x for x in e.get("uso", {}).get("efeitos", []) if isinstance(x, dict) and x.get("t") not in ("fogo", "fumaca", "comida")]
    e["cenario"] = proximo_cenario(p["id"])
    return e


def proximo_cenario(pid: str) -> str:
    """Escolhe o cenário menos usado, sem repetir os dos vídeos mais recentes."""
    usados = []
    for f in sorted(BASE.glob("*/espec.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.parent.name == pid:
            continue
        try:
            usados.append(json.loads(f.read_text(encoding="utf-8")).get("cenario", "bairro"))
        except (OSError, ValueError):
            pass
    for c in CENARIOS:
        if c not in usados[:4]:
            return c
    return min(CENARIOS, key=usados.count)


def escrever_cena(p: dict[str, Any], e: dict[str, Any]) -> None:
    p["cauda"] = e.get("cauda", 5)
    salvar(p)
    d = pasta(p["id"])
    (d / "espec.json").write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf-8")
    (d / "cena.js").write_text(f"window.ESPEC={json.dumps(e, ensure_ascii=False)};\n" + (MOTOR / "mestres" / f"{e['mestre']}.js" if e.get("mestre") else MOTOR / "obra.js").read_text(encoding="utf-8"), encoding="utf-8")


P_CRITICA = """Estes 12 quadros são amostras, em ordem, de um vídeo vertical em que um pedreiro constrói {tema} num quintal.
O quadro 12 é o clipe final. As palavras grandes são a legenda animada, proposital: ignore o texto.
Avalie só a obra: dá para reconhecer {tema} pronto? A construção cresce de etapa em etapa? O último quadro mostra a obra pronta em uso? Há blocos tampando a obra, peças flutuando ou algo sem sentido?
Seja exigente: se a obra pronta parece só uma caixa ou um cubo e não dá para reconhecer {tema} sem ler o texto, a nota é no máximo 5.
Responda JSON: {{"nota": 0 a 10, "problemas": ["defeitos concretos e como corrigir"]}}"""


P_CRITICA_OBJ = """Estes 12 quadros são amostras, em ordem, de um vídeo vertical em que um montador constrói {tema} numa oficina, peça por peça.
O quadro 12 é o clipe final. As palavras grandes são a legenda animada, proposital: ignore o texto.
Avalie só o objeto: dá para reconhecer {tema} pronto sem ler o texto? As proporções são as de um objeto real? As peças se encaixam, sem nada flutuando, torto ou atravessado? O último quadro mostra funcionando?
Seja exigente: proporção errada ou peça solta dá no máximo 6.
Responda JSON: {{"nota": 0 a 10, "problemas": ["defeitos concretos e como corrigir"]}}"""


def avaliar(p: dict[str, Any]) -> tuple[float | None, str]:
    if not llm.has_vision():
        return None, ""
    try:
        r = llm.vision_json((P_CRITICA_OBJ if p.get("modo") == "objeto" else P_CRITICA).format(tema=p["tema"]), [(pasta(p["id"]) / "previa.jpg").read_bytes()])
        return float(r.get("nota", 0)), "; ".join(r.get("problemas", []))[:1200]
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:200]


def _rodar(mod: str, args: list[str], ctx: JobContext, a: float = 0, b: float = 1) -> tuple[int, str]:
    pr = subprocess.Popen([PY, "-m", mod, *args], cwd=BACKEND, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore")
    final = []
    for ln in pr.stdout:  # type: ignore[union-attr]
        ln = ln.strip()
        if ln.startswith("P "):
            _, n, q = ln.split()
            ctx.update(progress=a + (b - a) * int(n) / max(int(q), 1))
            try:
                ctx.check()
            except BaseException:
                pr.kill()
                raise
        elif ln:
            final.append(ln)
    return pr.wait(), "\n".join(final[-6:])


@handler("construcao_criar")
def job_criar(ctx: JobContext) -> dict:
    p = ler(ctx.payload["id"])
    try:
        if not p["falas"]:
            ctx.update(progress=.05, stage="Escrevendo o roteiro")
            p = gerar_roteiro(p)
        d, retorno, melhor, nota_m = pasta(p["id"]), "", None, -1.0
        for i in range(TENTATIVAS):
            ctx.check()
            ctx.update(progress=.1 + i * .18, stage=f"Projetando a obra (tentativa {i + 1} de {TENTATIVAS})")
            try:
                e = gerar_espec(p, retorno)
            except (ValueError, AttributeError, TypeError, llm.LLMError) as x:
                retorno = str(x)
                continue
            escrever_cena(p, e)
            ctx.update(stage=f"Conferindo a obra (tentativa {i + 1})")
            r, sai = _rodar("lidark.construcao.render", [str(d), "previa"], ctx)
            if r:
                retorno = "erro ao montar a cena: " + sai[-500:]
                continue
            nota, probs = avaliar(p)
            ctx.update(log_line=f"Tentativa {i + 1}: nota {nota}. {probs[:300]}")
            n = nota if nota is not None else 7.0
            if n > nota_m:
                nota_m, melhor = n, e
            if n >= NOTA_MIN or p.get("modelo") or p.get("mestre"):
                break
            retorno = probs or retorno
        if melhor is None:
            raise RuntimeError("Não foi possível projetar a obra: " + retorno[:300])
        if nota_m < NOTA_ACEITA and not p.get("mestre"):
            raise RuntimeError(f"A melhor versão ficou com nota {nota_m:g}, abaixo do mínimo de {NOTA_ACEITA}: {retorno[:300]}")
        escrever_cena(p, melhor)
        if melhor is not e:
            _rodar("lidark.construcao.render", [str(d), "previa"], ctx)
        p.update(erro="", nota=nota_m)
        salvar(p)
        return _render(p, ctx, .7, 1) | {"nota": nota_m}
    except Exception as e:  # noqa: BLE001
        p.update(status="erro", erro=str(e)[:500])
        salvar(p)
        raise


def capa(base_img: Path, texto: str, saida: Path) -> None:
    im = Image.open(base_img).convert("RGB")
    d = ImageDraw.Draw(im)
    F = "C:/Windows/Fonts/seguibl.ttf"
    pal = texto.upper().split()
    meio = max(1, len(pal) // 2)
    y = 1420  # abaixo do objeto, que a câmera mantém na parte de cima
    for s, cor in ((" ".join(pal[:meio]), "#ffd23f"), (" ".join(pal[meio:]), "white")):
        tam = 150
        while tam > 50 and d.textlength(s, font=ImageFont.truetype(F, tam)) > 950:
            tam -= 6
        fo = ImageFont.truetype(F, tam)
        d.text(((1080 - d.textlength(s, font=fo)) / 2, y), s, font=fo, fill=cor, stroke_width=max(9, tam // 11), stroke_fill="#14202e")
        y += tam + 30
    q = 93
    im.save(saida, quality=q, optimize=True)
    while saida.stat().st_size > 1_900_000 and q > 60:  # limite do YouTube para miniatura
        q -= 6
        im.save(saida, quality=q, optimize=True)


def registrar(p: dict[str, Any], mp4: Path, capa_img: Path, dur: float) -> int:
    """Cria roteiro e vídeo prontos no canal. Status ready: nada publica sozinho com o autopilot desligado."""
    with session() as s:
        ch = s.get(Channel, p["channel_id"])
        pasta_m = MEDIA_DIR / ch.slug / f"construcao_{p['id']}"
        pasta_m.mkdir(parents=True, exist_ok=True)
        dest, dcapa = pasta_m / "video.mp4", pasta_m / "capa.jpg"
        if mp4.resolve() != dest.resolve():
            shutil.copy2(mp4, dest)
        if capa_img.resolve() != dcapa.resolve():
            shutil.copy2(capa_img, dcapa)
        v = s.get(Video, p["video_id"]) if p.get("video_id") else None
        if v and v.status != "published":
            sc = s.get(Script, v.script_id)
            sc.title, sc.hook, sc.scenes = p["titulo"], p["falas"][0], [{"text": f} for f in p["falas"]]
            v.duration, v.status, v.assets = dur, "ready", {**(v.assets or {}), "duration": dur}
            s.add(sc)
            s.add(v)
            s.commit()
            return v.id
        sc = Script(channel_id=ch.id, format="short", title=p["titulo"], hook=p["falas"][0], scenes=[{"text": f} for f in p["falas"]], description=p.get("descricao", ""), tags=p.get("tags", []), hashtags=list(ch.default_hashtags or []), status="produced")
        s.add(sc)
        s.commit()
        s.refresh(sc)
        v = Video(channel_id=ch.id, script_id=sc.id, format="short", status="ready", path=str(dest.relative_to(MEDIA_DIR)), thumbnail_path=str(dcapa.relative_to(MEDIA_DIR)), duration=dur, assets={"template": "construcao", "duration": dur, "projeto": p["id"]})
        s.add(v)
        s.commit()
        s.refresh(v)
        return v.id


def _render(p: dict[str, Any], ctx: JobContext, a: float = 0, b: float = 1) -> dict:
    d = pasta(p["id"])
    meio = a + (b - a) * .9
    ctx.update(progress=a, stage="Renderizando o vídeo")
    if p.get("biblioteca"):  # feito à mão pelo Claude: alta qualidade
        r, sai = _rodar("lidark.construcao.motor.estudio.render_hq", [str(d)], ctx, a, meio)
    else:
        r, sai = _rodar("lidark.construcao.render", [str(d), "mudo"], ctx, a, meio)
    if r:
        raise RuntimeError(sai[-500:])
    ctx.update(progress=meio, stage="Som e música")
    out = d / "final.mp4"
    r, sai = _rodar("lidark.construcao.audio", [str(d / "tmp"), str(out)], ctx)
    if r:
        raise RuntimeError(sai[-500:])
    dur = json.loads((d / "tmp" / "audio.json").read_text(encoding="utf-8"))["total"]
    nome = re.sub(r"^como construir\s+(um |uma |o |a )?", "", p["tema"], flags=re.I)
    nome = re.sub(r"^(um|uma|o|a)\s+", "", nome, flags=re.I)
    capa(d / "tmp" / "capa_base.jpg", p.get("capa") or f"{nome} do zero", d / "capa.jpg")
    vid = registrar(p, out, d / "capa.jpg", dur)
    p.update(status="pronto", video_id=vid, erro="")
    salvar(p)
    return {"video_id": vid}


@handler("construcao_render")
def job_render(ctx: JobContext) -> dict:
    p = ler(ctx.payload["id"])
    try:
        return _render(p, ctx)
    except Exception as e:  # noqa: BLE001
        p.update(status="erro", erro=str(e)[:500])
        salvar(p)
        raise


P_CHAT = """Você ajusta um vídeo 3D vertical pronto, de acordo com o pedido do dono do canal. Faça somente o que foi pedido.

PEDIDO: {pedido}

TÍTULO: {titulo}
FALAS DA NARRAÇÃO (uma por item):
{falas}
ZOOM ATUAL: {zoom} (1 é o normal; maior afasta a câmera em todo o vídeo)
VELOCIDADE DA VOZ: {rate}
{espec}

Responda JSON:
{{"resposta": "frase curta dizendo o que você mudou", "titulo": null ou novo título, "falas": null ou a lista COMPLETA de falas alterada, "zoom": null ou novo número, "rate": null ou algo como "+12%", "espec": null ou o JSON COMPLETO da cena alterado}}
Use null no que não mudar. A espec lista elementos de obra em metros; você pode mudar medidas, cores, posição ou acrescentar elementos do mesmo tipo. Se o pedido não for possível, explique em "resposta" e deixe o resto null."""


@handler("construcao_chat")
def job_chat(ctx: JobContext) -> dict:
    from ..models import now
    p = ler(ctx.payload["id"])
    d = pasta(p["id"])
    backup = {k: p.get(k) for k in ("titulo", "falas", "zoom", "rate")}
    arq = d / "espec.json"
    espec = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None
    cena_ant = (d / "cena.js").read_text(encoding="utf-8")
    fala = lambda de, t: p.setdefault("chat", []).append({"de": de, "texto": t, "em": now().isoformat()})  # noqa: E731
    try:
        ctx.update(progress=.05, stage="Entendendo o pedido")
        txt = "Peças e etapas da cena em JSON:\n" + json.dumps(espec, ensure_ascii=False) if espec else "Esta cena foi feita à mão: só dá para mudar falas, zoom e velocidade da voz."
        r = llm.complete_json(P_CHAT.format(pedido=ctx.payload["mensagem"], titulo=p["titulo"], falas=json.dumps(p["falas"], ensure_ascii=False, indent=0), zoom=p.get("zoom") or 1, rate=p["rate"], espec=txt), system="Você responde só JSON válido.", temperature=.2)
        r = getattr(r, "data", r)
        mudou = False
        if r.get("titulo"):
            p["titulo"] = r["titulo"]
        if isinstance(r.get("falas"), list) and r["falas"] and r["falas"] != p["falas"]:
            p["falas"], mudou = [str(x).strip() for x in r["falas"]], True
        if r.get("zoom"):
            p["zoom"], mudou = max(.5, min(3, float(r["zoom"]))), True
        if r.get("rate"):
            p["rate"], mudou = str(r["rate"]), True
        if espec and isinstance(r.get("espec"), dict) and r["espec"].get("pecas"):
            escrever_cena(p, r["espec"])
            mudou = True
        if not mudou:
            fala("ia", r.get("resposta") or "Não encontrei nada para mudar.")
            p.update(status="pronto", erro="")
            salvar(p)
            return {}
        salvar(p)
        out = _render(p, ctx, .1, 1)
        fala("ia", r.get("resposta") or "Ajuste feito.")
        salvar(p)
        return out
    except Exception as e:  # noqa: BLE001
        p.update(**backup, status="pronto", erro="")
        (d / "cena.js").write_text(cena_ant, encoding="utf-8")
        if espec:
            arq.write_text(json.dumps(espec, ensure_ascii=False, indent=1), encoding="utf-8")
        fala("ia", f"Não consegui aplicar esse ajuste, então mantive o vídeo anterior. Motivo: {str(e)[:220]}")
        salvar(p)
        raise


def chat_job(p: dict[str, Any], msg: str) -> Any:
    from ..models import now
    p.setdefault("chat", []).append({"de": "voce", "texto": msg, "em": now().isoformat()})
    p.update(status="renderizando", erro="")
    j = enqueue("construcao_chat", title=f"Ajuste: {p['titulo']}", channel_id=p["channel_id"], payload={"id": p["id"], "mensagem": msg})
    p["job_id"] = j.id
    salvar(p)
    return j


def criar_job(p: dict[str, Any]) -> Any:
    p.update(status="criando", erro="")
    j = enqueue("construcao_criar", title=f"Criar: {p['tema']}", channel_id=p["channel_id"], payload={"id": p["id"]})
    p["job_id"] = j.id
    salvar(p)
    return j


P_CLAUDE = """Faça o vídeo "{tema}" do canal Parte por Parte. Pasta do projeto: {pasta}
Leia lidark/construcao/motor/estudio/GUIA.md e siga tudo, inclusive o teste visual obrigatório.
Escreva só dentro da pasta do projeto. Termine quando a cena estiver no nível do vídeo da internet."""
FERRAMENTAS = "Read,Write,Edit,Glob,Grep,Bash(.venv/Scripts/python.exe -m lidark.construcao.render:*),Bash(.venv/Scripts/python.exe -m lidark.construcao.caderno:*),Bash(node --check:*)"
LIMITE_CLAUDE = 3 * 3600
VOZ_CLAUDE = {"voz": "pt-BR-ThalitaMultilingualNeural", "rate": "+8%"}


def _claude(p: dict[str, Any], ctx: JobContext, prompt: str = "", ferramentas: str = FERRAMENTAS) -> None:
    exe = shutil.which("claude") or str(Path.home() / ".local" / "bin" / "claude.exe")
    d = pasta(p["id"])
    pr = subprocess.Popen([exe, "-p", prompt or P_CLAUDE.format(tema=p["tema"], pasta=d.as_posix()), "--add-dir", str(d), "--permission-mode", "acceptEdits", "--allowedTools", ferramentas, "--output-format", "text"], cwd=BACKEND, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="ignore")
    ini = time.time()
    while True:
        try:
            sai, _ = pr.communicate(timeout=5)
            break
        except subprocess.TimeoutExpired:
            try:
                ctx.check()
                if time.time() - ini > LIMITE_CLAUDE:
                    raise RuntimeError("O Claude passou do limite de tempo")
            except BaseException:
                pr.kill()
                raise
    (d / "claude.log").write_text(sai or "", encoding="utf-8")
    if pr.returncode:
        raise RuntimeError("O Claude não terminou: " + (sai or "")[-300:])


def aprender(p: dict[str, Any]) -> None:
    """Guarda o que este vídeo ensinou: a cena para ser reaproveitada, regras no caderno e peças novas na biblioteca."""
    from . import MOTOR, caderno
    d = pasta(p["id"])
    fe = MOTOR / "estudio" / "feitos" / p["id"]
    fe.mkdir(parents=True, exist_ok=True)
    shutil.copy2(d / "cena.js", fe / "cena.js")
    (fe / "resumo.json").write_text(json.dumps({k: p.get(k) for k in ("tema", "titulo", "falas", "destaque", "capa", "descricao", "tags")}, ensure_ascii=False, indent=1), encoding="utf-8")
    f = d / "aprendizado.json"
    if not f.exists():
        return
    ap = _ler_json(f)
    for r in ap.get("regras", []):
        if str(r.get("texto", "")).strip():
            caderno.add(str(r.get("area") or "cena"), str(r["texto"]).strip(), f"vídeo {p['id']}", list(r.get("tags") or []), 2)
    arq = MOTOR / "biblioteca" / "itens" / "aprendidas.js"
    txt = arq.read_text(encoding="utf-8") if arq.exists() else "// Peças que os vídeos feitos pelo Claude deixaram para os próximos.\n"
    node = shutil.which("node")
    for q in ap.get("pecas", []):
        nome, js = str(q.get("nome", "")), str(q.get("js", ""))
        if not node or not re.fullmatch(r"[a-z0-9_]+", nome) or f"PC.item('{nome}'" in txt or f"PC.item('{nome}'" not in js:
            continue
        bloco = "(() => { try { const { THREE, mat, add, box, cil, esf, sh } = K3, { PI, G, B, C, CZ, CX, E, T, tubo, forma, roda, luz, vidro, metal, VD } = PC.H;\n" + js + "\n} catch (e) { console.warn(e); } })();\n"
        t = d / "peca_teste.js"
        t.write_text(bloco, encoding="utf-8")
        if subprocess.run([node, "--check", str(t)], capture_output=True).returncode == 0:
            txt += bloco
        t.unlink(missing_ok=True)
    arq.write_text(txt, encoding="utf-8")


@handler("construcao_claude")
def job_claude(ctx: JobContext) -> dict:
    """Todo vídeo é feito à mão pelo Claude Code; o app só renderiza em alta qualidade e registra."""
    p = ler(ctx.payload["id"])
    try:
        ctx.update(progress=.05, stage="O Claude está fazendo o vídeo")
        _claude(p, ctx)
        p = ler(p["id"])
        if not p.get("falas") or not (pasta(p["id"]) / "cena.js").exists():
            raise RuntimeError("O Claude terminou sem entregar a narração e a cena")
        p.update(VOZ_CLAUDE, status="renderizando", erro="")
        salvar(p)
        out = _render(p, ctx, .4, 1)
        try:
            aprender(p)
        except Exception as e:  # noqa: BLE001
            log.warning("não guardou o aprendizado de %s: %s", p["id"], e)
        return out
    except Exception as e:  # noqa: BLE001
        p.update(status="erro", erro=str(e)[:500])
        salvar(p)
        raise


def claude_job(p: dict[str, Any]) -> Any:
    p.update(VOZ_CLAUDE, status="criando", erro="", etapa="Na fila", biblioteca=True, cauda=5, zoom=1)
    salvar(p)  # antes da fila: a tarefa pode começar na hora
    j = enqueue("construcao_claude", title=f"Claude: {p['tema']}", channel_id=p["channel_id"], payload={"id": p["id"]})
    p["job_id"] = j.id
    salvar(p)
    return j


def render_job(p: dict[str, Any]) -> Any:
    p.update(status="renderizando", erro="")
    j = enqueue("construcao_render", title=f"Vídeo: {p['titulo']}", channel_id=p["channel_id"], payload={"id": p["id"]})
    p["job_id"] = j.id
    salvar(p)
    return j
