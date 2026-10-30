"""Roteirista do motor vetorial (bible["render_style"] == "vetor"): episódio de ~1:15 a 1:30 pensado para ser DESENHADO.

Diferente de writer.py (que descreve imagens para gerar), aqui cada beat já diz o cenário, quem está em cena, a pose,
os objetos, a piada visual, a palavra de destaque e a tela que abre. Os nomes vêm das bibliotecas JS (V.docs de sets.js,
props.js e screens.js, lidos em tempo de execução); nome desconhecido vira o mais próximo do catálogo.

O que dá riqueza à série e é garantido aqui, não deixado à sorte do LLM:
- placar persistente (medidor, dia, inventário, sujeira/curativo) salvo em arc["vetor_state"][parte]
- pelo menos 5 telas de pelo menos 3 famílias (celular, TV/monitor, outro), coerentes com o mundo
- uma piada visual por cena; palavra de destaque por beat; nunca caixa highlight
- escolha do público por PALAVRA comentada, ligada à decisão A/B de series.py
Um pedido ao LLM por episódio (cota apertada); só falta de tela gera um segundo pedido, pequeno.
"""
from __future__ import annotations

import copy
import difflib
import json
import random
import re
import shutil
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import Any

from .. import llm
from ..models import Channel, Idea
from .writer import _SFX_ONLY, _SOUND_CUE, _mission, _words

VETOR_DIR = Path(__file__).resolve().parent.parent / "render" / "vetor"

POSES = ("stand", "walk", "run", "point", "hold", "hands_head", "sit", "crawl", "type", "fall", "float")
EXPRS = ("neutral", "scared", "happy", "angry", "sad", "shock", "sleepy")
TODS = ("day", "night", "alert")
FX = ("sparks", "smoke", "alarm", "steam", "floaters", "rain", "dust")
DEVICES = ("hand", "fullscreen", "tv_on_set")
STAMP_STYLES = ("yellow", "red", "green")
REACTIONS = ("sweat", "question", "exclaim", "heart", "anger", "bulb", "zzz")
VOICE_DEVICES = ("tv", "radio", "phone", "comms", "monitor", "newsboy", "proclamation")
FAMILIES = ("celular", "tv", "outro")
MIN_SCREENS, MIN_FAMILIES = 5, 3

# usado só enquanto as bibliotecas JS não existem; quando existem, valem os V.docs
FALLBACK = {
    "sets": ["station_corridor", "station_cockpit", "station_lab", "station_airlock", "station_storage"],
    "props": ["oxygen_tank", "tape", "toolbox", "flashlight", "backpack", "poster", "sticky_note", "plant", "mug"],
    "screens": ["phone_chat", "phone_lock", "phone_call", "tv_news", "monitor_alert", "monitor_status", "radio_panel", "map_card", "paper_note"],
}

# palavras comuns que o LLM escreve em português; os nomes do catálogo são em inglês
PT_EN = {"corredor": "corridor", "estacao": "station", "laboratorio": "lab", "cabine": "cockpit", "deposito": "storage", "almoxarifado": "storage",
         "fita": "tape", "tanque": "tank", "oxigenio": "oxygen", "lanterna": "flashlight", "mochila": "backpack", "extintor": "extinguisher",
         "celular": "phone", "telefone": "phone", "televisao": "tv", "radio": "radio", "cartaz": "poster", "bilhete": "note", "planta": "plant",
         "caneca": "mug", "mapa": "map", "caixa": "box", "ferramentas": "tools", "chave": "wrench", "mensagem": "chat", "alerta": "alert", "noticia": "news"}

# medidor e contador do placar por gênero da série
GENRE_HUD = {
    "espaco": ("o2", "OXIGÊNIO", "#39d98a", "DIA EM ÓRBITA"),
    "inverno": ("calor", "CALOR", "#ff9f43", "DIA DE NEVASCA"),
    "ilha": ("agua", "ÁGUA", "#4db8ff", "DIA NA ILHA"),
    "zumbi": ("energia", "ENERGIA", "#39d98a", "DIA DE SURTO"),
    "apagao": ("bateria", "BATERIA", "#ffd23f", "DIA SEM LUZ"),
}
DEFAULT_HUD = ("energia", "ENERGIA", "#39d98a", "DIA")

# variedade: cada vídeo muda estrutura, gancho, abertura e CTA (memória: anti produção em massa)
STRUCTURES = {
    "meio_da_acao": "começa no pior momento e volta 1 frase para explicar como chegou ali",
    "contagem": "cada bloco é um número caindo no medidor: o medidor manda no ritmo",
    "tentativas": "três tentativas de resolver: a 1ª falha engraçada, a 2ª piora, a 3ª quase dá certo",
    "telas_primeiro": "a história é contada primeiro pelas telas (mensagem, alerta, plantão); o Zé reage a elas",
    "dialogo": "dois personagens discutindo o que fazer, com o perigo crescendo atrás deles",
    "diario": "o Zé grava um diário do dia e a realidade desmente o que ele diz",
}
HOOKS = {
    "numero": "abre com um número assustador do placar",
    "pergunta": "abre com uma pergunta que obriga a ver o fim",
    "fala": "abre com uma fala curta do Zé em pânico, sem narrador",
    "tela": "abre com uma tela apitando uma má notícia",
    "absurdo": "abre com uma situação absurda e engraçada que logo fica perigosa",
}
OPENINGS = ("wide_first", "close_first", "detail_first", "screen_first", "stamp_first")
CTAS = ("Comenta {a} ou {b}: o Zé faz o que vocês mandarem.", "Agora é com você: {a} ou {b}? Escreve aí embaixo.",
        "{a} ou {b}? A palavra mais comentada vira a próxima parte.", "Se o Zé morrer, a culpa é sua: {a} ou {b}?",
        "Decide nos comentários: {a} ou {b}.")
CHOICE_TITLES = ("COMENTE UMA PALAVRA", "VOCÊ DECIDE", "O ZÉ OBEDECE: COMENTE", "ESCREVA NOS COMENTÁRIOS")


# ================================================================ catálogo (V.docs das bibliotecas JS)

def _balanced(txt: str, i: int) -> str:
    """Trecho entre chaves/colchetes a partir de txt[i], respeitando aspas."""
    if i >= len(txt) or txt[i] not in "{[":
        return ""
    depth, q = 0, ""
    j = i
    while j < len(txt):
        c = txt[j]
        if q:
            if c == "\\":
                j += 1
            elif c == q:
                q = ""
        elif c in "\"'`":
            q = c
        elif c in "{[":
            depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0:
                return txt[i:j + 1]
        j += 1
    return ""


def _js_field(obj: str, field: str) -> str:
    m = re.search(rf"""\b{field}\s*:\s*(["'`])((?:\\.|(?!\1).)*)\1""", obj, re.S)
    return m.group(2).replace("\\'", "'").replace('\\"', '"') if m else ""


def _js_data(obj: str) -> Any:
    m = re.search(r"\bdata\s*:\s*", obj)
    raw = _balanced(obj, m.end()) if m else ""
    if not raw:
        return {}
    s = re.sub(r"(?<![\"'\w])([A-Za-z_]\w*)\s*:", r'"\1":', raw)  # chaves JS sem aspas → JSON
    s = re.sub(r"'((?:\\.|[^'\\])*)'", lambda k: json.dumps(k.group(1), ensure_ascii=False), s)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    try:
        return json.loads(s)
    except ValueError:
        return raw[:300]  # exemplo fica como texto: ainda ensina o formato à IA


def _doc_entries(js: str, kind: str) -> dict[str, dict[str, Any]]:
    """Aceita V.docs.sets.nome = {...}, V.docs.sets["nome"] = {...} e V.docs.sets = {nome: {...}} / Object.assign."""
    out: dict[str, dict[str, Any]] = {}
    for m in re.finditer(rf"""V\.docs\.{kind}(?:\.(\w+)|\[["'](\w+)["']\])\s*=\s*""", js):
        obj = _balanced(js, m.end())
        if obj:
            out[m.group(1) or m.group(2)] = {"desc": _js_field(obj, "desc"), "data": _js_data(obj), "family": _js_field(obj, "family")}
    for m in re.finditer(rf"(?:V\.docs\.{kind}\s*=\s*|Object\.assign\(\s*V\.docs\.{kind}\s*,\s*)", js):
        blk = _balanced(js, m.end())
        i = 1
        while blk and i < len(blk):
            k = re.compile(r"""\s*,?\s*["']?(\w+)["']?\s*:\s*""").match(blk, i)
            if not k or blk[k.end():k.end() + 1] != "{":
                break
            obj = _balanced(blk, k.end())
            out.setdefault(k.group(1), {"desc": _js_field(obj, "desc"), "data": _js_data(obj), "family": _js_field(obj, "family")})
            i = k.end() + len(obj)
    return out


# as bibliotecas registram por funções auxiliares (def('nome', ...)): só rodando dá para ler V.docs de verdade
_DOCS_JS = r"""
const fs = require('fs'), path = require('path'), vm = require('vm');
const dir = process.argv[1], cl = (x, a, b) => Math.max(a, Math.min(b, x));
const V = {sets: {}, props: {}, screens: {}, chars: {}, docs: {}, missing: [], rnd: s => Math.abs(Math.sin(s * 12.9898) * 43758.5453) % 1,
           ease: x => x, cl, esc: x => String(x)};
const ctx = vm.createContext({window: {V}, V, console: {log() {}, warn() {}, error() {}}, Math, JSON, Object, Array, String, Number});
for (const f of ['runtime.js', 'chars.js', 'sets.js', 'props.js', 'screens.js']) {
  try { const p = path.join(dir, f); if (fs.existsSync(p)) vm.runInContext(fs.readFileSync(p, 'utf8'), ctx, {timeout: 5000}); } catch (e) {}
}
const R = ctx.window.V;
const pick = k => Object.fromEntries(Object.keys(R[k] || {}).map(n => [n, ((R.docs || {})[k] || {})[n] || {}]));
process.stdout.write(JSON.stringify({sets: pick('sets'), props: pick('props'), screens: pick('screens'), chars: Object.keys(R.chars || {})}));
"""
_docs_cache: tuple[Any, dict[str, Any]] | None = None


def _runtime_docs() -> dict[str, Any]:
    """Executa as bibliotecas no Node (com um V mínimo) e devolve o que registraram. Arquivo pela metade é só ignorado."""
    global _docs_cache
    node = shutil.which("node")
    files = sorted(VETOR_DIR.glob("*.js"))
    key = tuple((f.name, f.stat().st_mtime_ns) for f in files)
    if not node or not files:
        return {}
    if _docs_cache and _docs_cache[0] == key:
        return _docs_cache[1]
    try:
        r = subprocess.run([node, "-e", _DOCS_JS, str(VETOR_DIR)], capture_output=True, timeout=30, check=True)
        out = json.loads(r.stdout.decode("utf-8"))
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}
    _docs_cache = (key, out)
    return out


_TIMELINE_JS = _DOCS_JS.split("const R = ctx.window.V;")[0] + r"""
const T = ctx.window.V, items = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(items.map(([n, d]) => { try { return T.screenTimeline ? T.screenTimeline(n, d, {}) : []; } catch (e) { return []; } })));
"""


def screen_timelines(items: list[tuple[str, dict[str, Any]]]) -> list[list[dict[str, Any]]]:
    """Eventos sonoros de cada tela (V.screenTimeline). Sem Node, as telas ficam só com o som de abertura."""
    node = shutil.which("node")
    if not node or not items:
        return [[] for _ in items]
    try:
        r = subprocess.run([node, "-e", _TIMELINE_JS, str(VETOR_DIR)], input=json.dumps(items, ensure_ascii=False).encode("utf-8"),
                           capture_output=True, timeout=30, check=True)
        out = json.loads(r.stdout.decode("utf-8"))
    except (OSError, ValueError, subprocess.SubprocessError):
        return [[] for _ in items]
    return out if len(out) == len(items) else [[] for _ in items]


def catalog() -> dict[str, Any]:
    """Nomes e exemplos das bibliotecas JS como estão AGORA no disco; sem elas, a lista de reserva do contrato."""
    cat: dict[str, Any] = {"source": {}}
    live = _runtime_docs()
    for kind in ("sets", "props", "screens"):
        p = VETOR_DIR / f"{kind}.js"
        js = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
        docs = {k: {"desc": str(d.get("desc") or ""), "data": d.get("data") or {}, "family": str(d.get("family") or d.get("kind") or "")}
                for k, d in (live.get(kind) or {}).items()} or _doc_entries(js, kind)
        for nm in re.findall(rf"""V\.{kind}(?:\.(\w+)|\[["'](\w+)["']\])\s*=(?!=)""", js):
            docs.setdefault(nm[0] or nm[1], {"desc": "", "data": {}, "family": ""})
        cat["source"][kind] = "docs" if docs else "fallback"
        cat[kind] = docs or {n: {"desc": "", "data": {}, "family": ""} for n in FALLBACK[kind]}
    p = VETOR_DIR / "chars.js"
    js = p.read_text(encoding="utf-8", errors="replace") if p.exists() else ""
    cat["chars"] = sorted(set(live.get("chars") or []) | {a or c for a, c in re.findall(r"""V\.chars(?:\.(\w+)|\[["'](\w+)["']\])\s*=(?!=)""", js)})
    return cat


def family(name: str, cat: dict[str, Any] | None = None) -> str:
    """Família da tela: celular, tv (TV, monitor, console) ou outro (rádio, papel, mapa...)."""
    doc = ((cat or {}).get("screens") or {}).get(name) or {}
    f = _plain(str(doc.get("family") or ""))
    if f in ("phone", "celular", "mobile"):
        return "celular"
    if f in ("tv", "monitor", "computer", "console", "computador"):
        return "tv"
    if f:
        return "outro"
    n = name.lower()
    if re.match(r"(phone|cell|celular|mobile|whats|sms|app_|social|insta|tiktok|lock)", n):
        return "celular"
    if re.match(r"(tv|monitor|console|terminal|computer|pc_|laptop|cctv|camera|radar|scanner|dashboard|screen)", n):
        return "tv"
    return "outro"


def _plain(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower().strip()


def nearest(name: Any, options: list[str], default: str = "") -> str:
    """Nome do catálogo mais próximo do que a IA escreveu (igual, por pedaços ou por semelhança)."""
    if not options:
        return str(name or default)
    n = re.sub(r"[^a-z0-9]+", "_", _plain(str(name or ""))).strip("_")
    n = "_".join(PT_EN.get(w, w) for w in n.split("_"))
    if n in options:
        return n
    if not n:
        return default or options[0]
    toks = set(n.split("_"))

    def score(o: str) -> float:
        ot = set(o.lower().split("_"))
        return difflib.SequenceMatcher(None, n, o.lower()).ratio() + 1.2 * len(toks & ot) / max(1, len(toks | ot))
    return max(options, key=score)


# ================================================================ placar persistente

def genre_hud(arc: dict[str, Any] | None) -> tuple[str, str, str, str]:
    genre = _plain(str(((arc or {}).get("plan") or {}).get("genre") or ""))
    return next((v for k, v in GENRE_HUD.items() if k in genre), DEFAULT_HUD)


def default_state(arc: dict[str, Any] | None, n: int = 1) -> dict[str, Any]:
    mid, label, color, day_label = genre_hud(arc)
    return {"part": 0, "meter": {"id": mid, "label": label, "color": color, "value": 100 if n <= 1 else 60},
            "day": max(1, n), "day_label": day_label, "inventory": [], "chars": {"ze": {"dirt": 0.1 if n <= 1 else 0.3, "bandage": False}},
            "notes": [], "sets": [], "structures": [], "hooks": [], "openings": [], "ctas": []}


def load_state(arc: dict[str, Any] | None, n: int) -> dict[str, Any]:
    """Placar com que a parte n começa: o fim da parte anterior mais próxima (arc["vetor_state"])."""
    saved = (arc or {}).get("vetor_state") or {}
    prev = [int(k) for k in saved if str(k).isdigit() and int(k) < n]
    if prev:
        return {**default_state(arc, n), **copy.deepcopy(saved[str(max(prev))])}
    return default_state(arc, n)


def _commit_series(slug: str, arc: dict[str, Any], n: int, state: dict[str, Any], decision: dict[str, Any] | None) -> None:
    """Salva o placar e liga a decisão à série. A cópia do plano em memória (a mesma que jobs/series usam logo depois)
    também recebe a decisão: é assim que after_written, blocked, decide e count_votes passam a enxergá-la."""
    parts = (arc.get("plan") or {}).get("parts") or []
    if decision is not None and 0 < n <= len(parts):
        parts[n - 1]["decision"] = decision

    def upd(a: dict[str, Any]) -> None:
        a.setdefault("vetor_state", {})[str(n)] = state
        pp = (a.get("plan") or {}).get("parts") or []
        if decision is not None and 0 < n <= len(pp):
            pp[n - 1]["decision"] = decision
    from . import series as S
    S.update_arc(slug, arc["id"], upd)


# ================================================================ prompt

def _doc_lines(items: dict[str, dict[str, Any]], with_data: bool, limit: int) -> str:
    rows = []
    for k, d in list(items.items())[:limit]:
        row = f'  - "{k}"' + (f': {d["desc"]}' if d.get("desc") else "")
        if with_data and d.get("data"):
            row += f" | data ex.: {json.dumps(d['data'], ensure_ascii=False)[:240]}"
        rows.append(row)
    return "\n".join(rows)


def _world_rule(arc: dict[str, Any] | None, b: dict[str, Any]) -> str:
    setting = ((arc or {}).get("plan") or {}).get("setting") or b.get("premise") or ""
    return (f"MUNDO: {setting}\nCada aparelho tem de fazer sentido AQUI. Longe de torre (espaço, ilha, nevasca), o celular não tem sinal: "
            "ele só funciona com um motivo mostrado na história (Wi-Fi da estação, mensagem de casa que chegou atrasada, foto salva, lanterna, "
            "bateria acabando). Toda tela de celular leva \"why\" com esse motivo em poucas palavras. TV só onde existe TV ou uma transmissão "
            "que chega. Tela nunca é enfeite: traz uma informação que muda a cena ou uma piada.")


def build_prompt(ch: Channel, b: dict[str, Any], *, cat: dict[str, Any], state: dict[str, Any], topic: str, arc: dict[str, Any] | None,
                 n: int, seconds: float, words: tuple[int, int], n_beats: int, picks: dict[str, str], ask_choice: bool,
                 series_block: str = "") -> str:
    chars = "\n".join(f'  - id "{c["id"]}": {c["name"]} ({c.get("role", "")})' for c in b.get("characters") or [])
    devs = [d for d in (b.get("hud") or {}).get("devices") or [] if d in VOICE_DEVICES]
    screens = _doc_lines(cat["screens"], True, 60)
    fams = {f: [k for k in cat["screens"] if family(k, cat) == f] for f in FAMILIES}
    fam_txt = "; ".join(f"{f}: {', '.join(v[:12]) or '(nenhuma)'}" for f, v in fams.items())
    prev = ""
    if arc and not series_block:
        prev = "\n".join(f"  Parte {p['n']}: {p.get('summary', '')} | GANCHO: {p.get('cliffhanger', '')}" for p in (arc.get("parts") or [])[-3:])
        prev = f"O QUE JÁ ACONTECEU:\n{prev}"
    m = state["meter"]
    inv = ", ".join(f"{i['label']} ({i['item']})" for i in state["inventory"]) or "(vazio)"
    ch_state = "; ".join(f"{k}: sujeira {v.get('dirt', 0):.1f}{', com curativo' if v.get('bandage') else ''}" for k, v in state["chars"].items())
    notes = "\n".join(f"  - {x}" for x in state["notes"][-6:]) or "  (primeiro episódio)"
    used_sets = ", ".join(state["sets"][-6:]) or "(nenhum)"
    part_next = ""
    plan_parts = ((arc or {}).get("plan") or {}).get("parts") or []
    if n < len(plan_parts):
        part_next = f'A PRÓXIMA PARTE tem o objetivo: {plan_parts[n].get("goal", "")}. As duas opções levam a esse objetivo por caminhos diferentes.'
    choice_rule = f"""FIM COM ESCOLHA DO PÚBLICO (OBRIGATÓRIO): a história para no momento da decisão. Invente duas opções concretas, cada uma UMA
PALAVRA em maiúsculas (4 a 10 letras, sem espaço), fáceis de comentar e diferentes entre si, ex.: "FITA" x "SOLDA". {part_next}
O último beat pergunta exatamente sobre essas duas opções ("fita ou solda?"), nunca sobre outra coisa, diz as duas palavras em voz alta e pede para
comentar uma delas; devolva o bloco "choice".""" if ask_choice else \
        "FIM: este episódio não tem escolha do público; feche com o gancho ou com o desfecho que o esqueleto pede."
    return f"""Você é roteirista de uma série animada vertical para o canal "{ch.name}" ({ch.niche}), em português do Brasil.
O vídeo é DESENHADO quadro a quadro por um motor vetorial: tudo o que você pedir precisa existir nas listas abaixo.
SÉRIE: "{b.get('series_title')}". PREMISSA: {b.get('premise')}
TEMA: {topic}
PERSONAGENS:
{chars}
{prev}
{series_block}
Se o bloco acima pedir recap, resuma em até 8 palavras e varie a fórmula da frase.

{_world_rule(arc, b)}

PLACAR ATUAL (continua do episódio anterior e aparece na tela o tempo todo; não invente outro):
  {m['label']}: {m['value']}% · {state['day_label']}: {state['day']} · INVENTÁRIO: {inv}
  Estado: {ch_state}
  Fatos do mundo já estabelecidos, que continuam valendo:
{notes}
  Cenários já vistos (reuse os mesmos lugares quando for o mesmo lugar): {used_sets}

ESTRUTURA DESTE EPISÓDIO: {STRUCTURES[picks['structure']]}.
GANCHO: {HOOKS[picks['hook']]}. A 1ª frase prende em 2 segundos.{" O 1º beat já abre uma tela." if picks.get("opening") == "screen_first" else ""}
TAMANHO: cerca de {round(seconds)} s falados: {words[0]} a {words[1]} palavras no total, em {n_beats - 2} a {n_beats + 2} beats (6 a 14 palavras cada). Frases curtas, presente, ritmo
de trailer, humor leve: o Zé é medroso mas esperto. Pelo menos 3 falas de personagens, não só narração.
REGRA DO "text": é SEMPRE algo falado em voz alta; nunca descreva som. Para um aparelho só chiar/apitar: "text": "" e "sfx": "static"|"beep"|"knock"|"alarm".
NÃO escreva "o Zé sente medo" quando o desenho mostra isso: o narrador conta o que não se vê.
O NARRADOR NUNCA DESCREVE A TELA ("o monitor mostra", "o terminal exibe", "o rádio chia"): a tela aparece sozinha, e a fala faz a história andar
(o que isso significa, o que dá errado, o que o Zé decide). Toda fala traz fato novo; nada de encher linguiça.

CENÁRIOS ("set"):
{_doc_lines(cat['sets'], False, 40)}
OBJETOS ("props", "hold", "detail", "gag.prop", "take"):
{_doc_lines(cat['props'], False, 90)}
TELAS ("screen.type"), com os dados de cada uma:
{screens}
FAMÍLIAS DE TELAS: {fam_txt}
POSES: {', '.join(POSES)}. EXPRESSÕES: {', '.join(EXPRS)}. "tod": {', '.join(TODS)}. "fx": {', '.join(FX)}.
REAÇÕES: {', '.join(REACTIONS)}.

TELAS (OBRIGATÓRIO): pelo menos {MIN_SCREENS} beats com "screen", de pelo menos {MIN_FAMILIES} famílias diferentes. "device": "hand" (na mão do personagem),
"fullscreen" (a tela ocupa o vídeo) ou "tv_on_set" (aparelho dentro do cenário). Preencha "data" com textos da história, nunca com o exemplo.
Pelo menos UMA tela é TV de verdade (type começando com "tv_"), ex.: plantão na Terra falando do caso, comercial absurdo, previsão do tempo.
Se a fala do beat sai do aparelho (áudio, plantão, rádio), marque "voice_from_screen": true; a voz ganha o filtro do aparelho.
Speakers possíveis além dos personagens: "narrador"{''.join(f', "{d}"' for d in devs)}.
CADA PALAVRA IMPORTANTE VIRA IMAGEM: quando a fala cita um objeto, ele aparece. Use "detail": "nome do objeto" para um close nele e "word": a palavra
de 1 ou 2 termos que vira carimbo na tela (com "word_style": yellow|red|green). Todo beat tem "word".
UMA PIADA VISUAL POR CENA: a cada troca de cenário, um "gag": {{"prop": "objeto do fundo", "label": "texto curtinho engraçado", "note": "a piada"}}.
Ex.: cartaz "NÃO ABRA", planta de plástico regada, bilhete passivo-agressivo da Dona Cida. A piada é vista, não contada.
INVENTÁRIO: quando pegar algo, "take": {{"item": "objeto", "label": "NOME CURTO"}}; quando gastar, "use": "objeto". Só use o que está no inventário ou foi pego.
MEDIDOR: em 2 a 4 beats, "meter": novo valor de {m['label']} (a história justifica; ele tende a cair).
ESTADO: "char_state": {{"ze": {{"dirt": 0.5, "bandage": true}}}} quando o personagem se suja ou faz curativo.
Nunca use caixa de destaque em volta de personagem.
{choice_rule}

Responda APENAS JSON:
{{"title": "título", "thumbnail_text": "2-4 palavras", "description": "2-3 frases + convite", "hashtags": ["#..."], "tags": ["..."],
"arc_title": "nome do arco", "mission": {{"title": "MISSÃO CURTA", "subtitle": "lugar"}}, "objectives": ["3 objetivos curtos"],
"beats": [{{"speaker": "narrador", "text": "...", "emotion": "tensao", "set": "...", "tod": "alert",
  "cast": [{{"char": "ze", "pose": "hold", "expr": "scared", "hold": "tape"}}], "props": ["..."], "gag": {{"prop": "...", "label": "...", "note": "..."}},
  "fx": ["sparks"], "word": "MICROFURO", "word_style": "red", "detail": "...", "reaction": "sweat",
  "screen": {{"type": "...", "data": {{}}, "device": "hand", "why": "..."}}, "voice_from_screen": false,
  "take": {{"item": "...", "label": "..."}}, "use": "...", "meter": 44, "char_state": {{}}, "impact": true, "tip": false}}],
"choice": {{"question": "pergunta curta", "a": {{"word": "FITA", "hint": "o que acontece, sem spoiler", "branch": "o que a próxima parte mostra se ganhar"}},
           "b": {{"word": "SOLDA", "hint": "...", "branch": "..."}}, "default": "A"}},
"placar_fim": {{"day": {state['day']}, "notes": ["fato novo do mundo que a próxima parte precisa lembrar"]}},
"cliffhanger": "o gancho em 1 frase", "memory": "resumo em 2 frases para a próxima parte", "next_hook": "o que vem depois", "facts": []}}"""


# ================================================================ validação e correção

def _hold(v: Any, props: list[str]) -> str:
    return nearest(v, props) if v and str(v).lower() not in ("none", "null", "nada") else ""


def _clean_gag(g: Any, props: list[str]) -> dict[str, str] | None:
    if not isinstance(g, dict) or not g.get("prop"):
        return None
    return {"prop": nearest(g["prop"], props), "label": str(g.get("label") or "")[:26], "note": str(g.get("note") or "")[:120]}


def _clean_screen(sc: Any, cat: dict[str, Any], *, fallback_device: str = "fullscreen") -> dict[str, Any] | None:
    if isinstance(sc, str):
        sc = {"type": sc}
    if not isinstance(sc, dict) or not sc.get("type"):
        return None
    t = nearest(sc["type"], list(cat["screens"]))
    dev = sc.get("device") if sc.get("device") in DEVICES else fallback_device
    data = sc.get("data") if isinstance(sc.get("data"), dict) else {}
    return {"type": t, "data": data, "device": dev, "family": family(t, cat), **({"why": str(sc["why"])[:90]} if sc.get("why") else {})}


def normalize_beats(data: dict[str, Any], b: dict[str, Any], cat: dict[str, Any], state: dict[str, Any], *, max_words: int = 10**6,
                    warnings: list[str] | None = None) -> list[dict[str, Any]]:
    """Corrige o que veio do LLM: nomes fora do catálogo viram os mais próximos, enumerações inválidas o padrão,
    highlight some, celular sem motivo perde a tela (a garantia de telas repõe depois)."""
    warn = warnings if warnings is not None else []
    sets, props = list(cat["sets"]), list(cat["props"])
    char_ids = [c["id"] for c in b.get("characters") or []]
    devs = set((b.get("hud") or {}).get("devices") or []) & set(VOICE_DEVICES)
    hero = char_ids[0] if char_ids else "ze"
    drawn = set(cat.get("chars") or [])
    beats: list[dict[str, Any]] = []
    last_set = ""
    for x in data.get("beats") or []:
        if not isinstance(x, dict):
            continue
        text = re.sub(r"\s+", " ", str(x.get("text") or "")).strip()
        sfx = x.get("sfx") if isinstance(x.get("sfx"), str) else ""
        silent = bool(text and _SOUND_CUE.match(text)) or (not text and sfx in _SFX_ONLY)
        if not text and not silent:
            continue
        if silent:
            low = text.lower()
            sfx = sfx if sfx in _SFX_ONLY else ("beep" if "bip" in low else "knock" if "bat" in low else "alarm" if "alarme" in low else "static")
            text = ""
        spk = str(x.get("speaker") or "narrador").strip().lower()
        if spk not in char_ids and spk not in devs:
            spk = "narrador"
        st = nearest(x["set"], sets) if x.get("set") else (last_set or sets[0])
        if x.get("set") and st != x["set"]:
            warn.append(f'cenário "{x["set"]}" → "{st}"')
        last_set = st
        cast = []
        for c in (x.get("cast") or [])[:3]:
            if not isinstance(c, dict):
                continue
            cid = str(c.get("char") or c.get("id") or "").strip().lower()
            if cid not in char_ids:
                continue
            if drawn and cid not in drawn:  # sem boneco desenhado: a voz continua, o corpo fica de fora
                warn.append(f'personagem "{cid}" sem desenho em chars.js')
                continue
            cast.append({"char": cid, "pose": nearest(c.get("pose"), list(POSES), "stand"), "expr": c.get("expr") if c.get("expr") in EXPRS else "neutral",
                         "hold": _hold(c.get("hold"), props)})
        out: dict[str, Any] = {"speaker": spk, "text": text, "set": st, "tod": x.get("tod") if x.get("tod") in TODS else "day",
                               "cast": cast, "props": [nearest(p if isinstance(p, str) else (p or {}).get("id"), props) for p in (x.get("props") or [])[:4]],
                               "fx": [f for f in (x.get("fx") or []) if f in FX], "word": str(x.get("word") or "").strip().upper()[:18],
                               "word_style": x.get("word_style") if x.get("word_style") in STAMP_STYLES else "yellow"}
        if silent:
            out.update(silent=True, sfx=sfx)
        for k in ("emotion", "impact", "pause", "tip", "recap", "time", "crowd", "set_state"):
            if x.get(k) not in (None, "", [], False):
                out[k] = x[k]
        if x.get("detail"):
            out["detail"] = nearest(x["detail"], props)
        if x.get("reaction") in REACTIONS:
            out["reaction"] = x["reaction"]
        gag = _clean_gag(x.get("gag"), props)
        if gag:
            out["gag"] = gag
        sc = _clean_screen(x.get("screen"), cat)
        if sc and sc["family"] == "celular" and not sc.get("why"):
            warn.append(f'celular sem motivo removido: {sc["type"]}')
            sc = None
        if sc:
            out["screen"] = sc
            if x.get("voice_from_screen") or spk in VOICE_DEVICES:
                out["voice_from_screen"] = True
                # mesma chave lida por engine.synth_lines: a voz de quem fala passa pelo filtro do aparelho
                out["device"] = {"type": spk if spk in VOICE_DEVICES else {"celular": "phone", "tv": "tv"}.get(sc["family"], "radio")}
        if isinstance(x.get("take"), dict) and x["take"].get("item"):
            it = nearest(x["take"]["item"], props)
            out["take"] = {"item": it, "label": str(x["take"].get("label") or it).upper()[:14]}
        if x.get("use"):
            out["use"] = nearest(x["use"], props)
        if isinstance(x.get("meter"), (int, float)):
            out["meter"] = max(0, min(100, round(float(x["meter"]))))
        if isinstance(x.get("char_state"), dict):
            cs = {k: {"dirt": max(0.0, min(1.0, float(v.get("dirt", 0)))) if isinstance(v.get("dirt"), (int, float)) else None,
                      "bandage": v.get("bandage") if isinstance(v.get("bandage"), bool) else None}
                  for k, v in x["char_state"].items() if k in char_ids and isinstance(v, dict)}
            if cs:
                out["char_state"] = {k: {a: c for a, c in v.items() if c is not None} for k, v in cs.items()}
        beats.append(out)
    # todo beat tem alguém em cena ou um close; beat sem elenco herda o anterior (nunca cenário vazio por engano)
    for i, bt in enumerate(beats):
        if not bt["cast"] and not bt.get("detail") and not (bt.get("screen") and bt["screen"]["device"] == "fullscreen"):
            prev = next((beats[j]["cast"] for j in range(i - 1, -1, -1) if beats[j]["cast"]), None)
            bt["cast"] = copy.deepcopy(prev) if prev else [{"char": hero, "pose": "stand", "expr": "neutral", "hold": ""}]
    # mantém o tamanho: corta beats do meio sem tela nem placar (nunca o 1º nem os 2 últimos)
    def total() -> int:
        return sum(len(bb["text"].split()) for bb in beats)
    while total() > max_words and len(beats) > 8:
        cand = [i for i in range(1, len(beats) - 2) if not any(k in beats[i] for k in ("screen", "take", "use", "meter", "gag", "tip"))]
        if not cand:
            break
        beats.pop(max(cand, key=lambda i: len(beats[i]["text"].split())))
    return beats


def ensure_gags(beats: list[dict[str, Any]], cat: dict[str, Any], rng: random.Random) -> None:
    """Uma piada visual por cena (sequência no mesmo cenário): falta? Põe um objeto de fundo com uma etiqueta boba."""
    labels = ["NÃO ABRA", "FRÁGIL (TIPO O ZÉ)", "COCHILO AQUI", "SEGUNDA, DE NOVO?", "PERIGO: ZÉ", "DEVOLVER À CIDA", "NÃO É CAFÉ", "SORRIA, ESTÁ PIOR"]
    rng.shuffle(labels)
    names = list(cat["props"])
    pref = [k for k, d in cat["props"].items() if re.search(r"piada|gag|cartaz|poster|bilhete|note|sign|placa|plant|caneca|mug", f"{k} {d.get('desc', '')}", re.I)]
    i = 0
    while i < len(beats):
        j = i
        while j + 1 < len(beats) and beats[j + 1]["set"] == beats[i]["set"]:
            j += 1
        if not any(beats[k].get("gag") for k in range(i, j + 1)):
            beats[i]["gag"] = {"prop": rng.choice(pref or names), "label": labels[i % len(labels)], "note": "automática"}
        i = j + 1


def ensure_words(beats: list[dict[str, Any]]) -> None:
    """Todo beat falado tem palavra de destaque: número, ou a palavra mais longa da fala."""
    for bt in beats:
        if bt.get("silent") or bt.get("word"):
            continue
        ws = re.findall(r"\d+%?|[A-Za-zÀ-ÿ]{4,}", bt["text"])
        if ws:
            bt["word"] = max(ws, key=lambda w: (w[0].isdigit(), len(w))).upper()[:18]


def screen_problems(beats: list[dict[str, Any]], cat: dict[str, Any]) -> tuple[int, list[str]]:
    """Quantas telas faltam e quais famílias faltam (só exige as famílias que existem no catálogo)."""
    have = [bt["screen"]["family"] for bt in beats if bt.get("screen")]
    exists = {family(k, cat) for k in cat["screens"]}
    need_f = min(MIN_FAMILIES, len(exists))
    miss = [f for f in FAMILIES if f in exists and f not in have]
    miss = miss[:max(0, need_f - len(set(have)))]
    return max(0, MIN_SCREENS - len(have)), miss


def _free_beats(beats: list[dict[str, Any]]) -> list[int]:
    idx = [i for i, bt in enumerate(beats) if not bt.get("screen") and not bt.get("silent") and 0 < i < len(beats) - 1]
    return idx or [i for i, bt in enumerate(beats) if not bt.get("screen")]


def repair_prompt(beats: list[dict[str, Any]], cat: dict[str, Any], count: int, miss: list[str], arc: dict[str, Any] | None, b: dict[str, Any]) -> str:
    fala = "\n".join(f'  {i}: ({beats[i]["set"]}) {beats[i]["text"]}' for i in _free_beats(beats))
    fams = "; ".join(f"{f}: {', '.join(k for k in cat['screens'] if family(k, cat) == f)}" for f in miss) or "(qualquer família)"
    return f"""Este episódio animado precisa de mais {max(count, len(miss))} telas coerentes com a história.
{_world_rule(arc, b)}
Beats sem tela:
{fala}
Famílias que faltam: {fams}
Telas disponíveis:
{_doc_lines(cat['screens'], True, 60)}
Responda APENAS JSON: {{"screens": {{"<número do beat>": {{"type": "...", "data": {{}}, "device": "hand|fullscreen|tv_on_set", "why": "motivo, se for celular"}}}}}}"""


def _fill_text(d: Any, title: str, body: str) -> Any:
    """Troca os textos do exemplo pelos da fala (tela automática nunca mostra o texto de exemplo)."""
    if isinstance(d, dict):
        return {k: _fill_text(v, title, body) if k not in ("title", "headline", "tag", "label", "name") else title for k, v in d.items()}
    if isinstance(d, list):
        return [_fill_text(x, title, body) for x in d[:2]]
    if isinstance(d, str) and not d.startswith("#"):
        return body
    return d


def auto_screens(beats: list[dict[str, Any]], cat: dict[str, Any], rng: random.Random, warn: list[str]) -> None:
    """Último recurso, sem LLM: abre telas do catálogo com o texto da própria fala."""
    count, miss = screen_problems(beats, cat)
    free = _free_beats(beats)
    rng.shuffle(free)
    for f in miss + ["tv"] * max(0, count - len(miss)):
        if not free:
            break
        opts = [k for k in cat["screens"] if family(k, cat) == f] or list(cat["screens"])
        name = rng.choice(opts)
        i = free.pop()
        bt = beats[i]
        data = _fill_text(copy.deepcopy(cat["screens"][name].get("data") or {}), bt.get("word") or "ALERTA", bt["text"])
        bt["screen"] = {"type": name, "data": data if isinstance(data, dict) else {}, "device": "fullscreen", "family": family(name, cat)}
        if f == "celular":
            bt["screen"]["why"] = "mensagem salva no aparelho"
        warn.append(f"tela automática no beat {i}: {name}")


def ensure_tv(beats: list[dict[str, Any]], cat: dict[str, Any], rng: random.Random, warn: list[str]) -> None:
    """Todo episódio tem pelo menos uma TV de verdade: troca um monitor, ou abre num beat livre."""
    tvs = [k for k in cat["screens"] if k.startswith("tv_") and k != "tv_static"]
    if not tvs or any(bt.get("screen") and bt["screen"]["type"].startswith("tv_") for bt in beats):
        return
    swap = [i for i, bt in enumerate(beats) if bt.get("screen") and bt["screen"]["type"].startswith("monitor_") and not bt.get("voice_from_screen")]
    free = swap or _free_beats(beats)
    if not free:
        return
    i, name = rng.choice(free), rng.choice(tvs)
    bt = beats[i]
    data = _fill_text(copy.deepcopy(cat["screens"][name].get("data") or {}), bt.get("word") or "URGENTE", bt["text"])
    bt["screen"] = {"type": name, "data": data if isinstance(data, dict) else {}, "device": "fullscreen", "family": family(name, cat)}
    warn.append(f"TV garantida no beat {i}: {name}")


def clean_word(w: Any, fallback: str) -> str:
    """Palavra de voto: series.parse_vote casa palavras de 4+ letras nas opções."""
    s = re.sub(r"[^A-ZÀ-Ý]", "", str(w or "").upper())
    if len(s) >= 4:
        return s[:12]
    ws = sorted(re.findall(r"[A-Za-zÀ-ÿ]{4,}", fallback), key=len, reverse=True)
    return ws[0].upper()[:12] if ws else ""


def build_choice(data: dict[str, Any], planned: dict[str, Any] | None, rng: random.Random, tried: list[str]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Une o bloco "choice" do LLM à decisão do plano: devolve (choice para a tela, decision para series.py).
    As opções da decisão viram as próprias palavras, então "FITA" nos comentários já conta como voto (parse_vote)."""
    c = data.get("choice") if isinstance(data.get("choice"), dict) else {}
    pl_opts = (planned or {}).get("options") or {}
    side = {}
    for k in ("a", "b"):
        o = c.get(k) if isinstance(c.get(k), dict) else {"word": c.get(k)}
        word = clean_word(o.get("word"), str(pl_opts.get(k.upper()) or ""))
        side[k] = {"word": word, "hint": str(o.get("hint") or pl_opts.get(k.upper()) or "")[:70], "branch": str(o.get("branch") or "")[:300]}
    wa, wb = _plain(side["a"]["word"]), _plain(side["b"]["word"])
    if not wa or not wb or wa in wb or wb in wa:
        return None
    default = str(c.get("default") or (planned or {}).get("default") or "A").upper()
    branches = (planned or {}).get("branches") or {}
    decision = {"question": str((planned or {}).get("question") or c.get("question") or "O que o Zé faz?")[:160],
                "options": {"A": side["a"]["word"], "B": side["b"]["word"]}, "default": default if default in ("A", "B") else "A",
                "branches": {"A": branches.get("A") or side["a"]["branch"], "B": branches.get("B") or side["b"]["branch"]},
                "words": True}
    if pl_opts:
        decision["plan_options"] = {k: str(v)[:80] for k, v in pl_opts.items()}
    titles = [t for t in CHOICE_TITLES if t not in tried[-1:]] or list(CHOICE_TITLES)
    title = rng.choice(titles)
    choice = {"title": title, "question": decision["question"], "a": {"word": side["a"]["word"], "hint": side["a"]["hint"]},
              "b": {"word": side["b"]["word"], "hint": side["b"]["hint"]}}
    return choice, decision


def ensure_cta(beats: list[dict[str, Any]], choice: dict[str, Any], rng: random.Random, recent: list[str], last_set: str) -> str:
    """A última fala diz as duas palavras em voz alta; se não disser, entra uma chamada variada."""
    a, b = choice["a"]["word"], choice["b"]["word"]
    if beats and all(_plain(w) in _plain(beats[-1]["text"]) for w in (a, b)):
        return "roteiro"
    opts = [i for i in range(len(CTAS)) if str(i) not in recent[-2:]] or list(range(len(CTAS)))
    k = rng.choice(opts)
    cast = copy.deepcopy(beats[-1]["cast"]) if beats else []
    beats.append({"speaker": "narrador", "text": CTAS[k].format(a=a, b=b), "set": last_set, "tod": beats[-1]["tod"] if beats else "day",
                  "cast": cast, "props": [], "fx": [], "word": f"{a} OU {b}"[:18], "word_style": "yellow", "emotion": "tensao"})
    return str(k)


def advance_state(start: dict[str, Any], beats: list[dict[str, Any]], data: dict[str, Any], n: int, picks: dict[str, str],
                  rng: random.Random) -> dict[str, Any]:
    """Placar com que a parte termina, calculado do que aconteceu nos beats (não do que o LLM declarou)."""
    st = copy.deepcopy(start)
    st["part"] = n
    inv = {i["item"]: i for i in st["inventory"]}
    for bt in beats:
        if bt.get("take"):
            inv[bt["take"]["item"]] = dict(bt["take"])
        if bt.get("use"):
            inv.pop(bt["use"], None)
        for cid, cs in (bt.get("char_state") or {}).items():
            st["chars"].setdefault(cid, {"dirt": 0.1, "bandage": False}).update(cs)
    st["inventory"] = list(inv.values())
    vals = [bt["meter"] for bt in beats if "meter" in bt]
    if vals:
        st["meter"]["value"] = vals[-1]
    else:  # o medidor nunca fica parado num episódio: é o relógio da série
        st["meter"]["value"] = max(5, st["meter"]["value"] - rng.randint(4, 11))
    end = data.get("placar_fim") if isinstance(data.get("placar_fim"), dict) else {}
    day = end.get("day")
    if isinstance(day, (int, float)) and start["day"] <= day <= start["day"] + 3:
        st["day"] = int(day)
    notes = [str(x)[:120] for x in (end.get("notes") or []) if x][:3]
    st["notes"] = (st["notes"] + notes)[-8:]
    st["sets"] = list(dict.fromkeys(st["sets"] + [bt["set"] for bt in beats]))[-10:]
    for k, key in (("structure", "structures"), ("hook", "hooks"), ("opening", "openings"), ("cta", "ctas"), ("choice_title", "choices")):
        st[key] = (st.get(key, []) + [picks.get(k, "")])[-6:]
    return st


def pick_variety(state: dict[str, Any], rng: random.Random) -> dict[str, str]:
    def fresh(options: list[str], recent: list[str]) -> str:
        return rng.choice([o for o in options if o not in recent[-2:]] or options)
    return {"structure": fresh(list(STRUCTURES), state.get("structures", [])), "hook": fresh(list(HOOKS), state.get("hooks", [])),
            "opening": fresh(list(OPENINGS), state.get("openings", []))}


def finish(data: dict[str, Any], b: dict[str, Any], cat: dict[str, Any], state: dict[str, Any], *, n: int, picks: dict[str, str],
           rng: random.Random, ask_choice: bool, planned: dict[str, Any] | None, max_words: int = 10**6, fix_screens=None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Da resposta do LLM ao episódio pronto, sem nenhuma rede (o teste offline passa por aqui). `fix_screens(beats, count, miss)`
    é o segundo pedido opcional ao LLM. Devolve (episódio, decisão para a série)."""
    warn: list[str] = []
    beats = normalize_beats(data, b, cat, state, max_words=max_words, warnings=warn)
    if not beats:
        raise llm.LLMError("roteiro vetorial sem beats")
    ensure_words(beats)
    choice, decision = None, None
    if ask_choice:
        got = build_choice(data, planned, rng, state.get("choices", []))
        if got is None:
            warn.append("escolha inválida do LLM: duas palavras do fim foram recompostas")
            got = build_choice({"choice": {"a": {"word": "AVANCA"}, "b": {"word": "RECUA"}}}, planned, rng, [])
        choice, decision = got
        picks["choice_title"] = choice["title"]
        picks["cta"] =ensure_cta(beats, choice, rng, state.get("ctas", []), beats[-1]["set"])
        ensure_words(beats)
    ensure_gags(beats, cat, rng)
    count, miss = screen_problems(beats, cat)
    if (count or miss) and fix_screens:
        try:
            fixes = fix_screens(beats, count, miss) or {}
            for k, v in fixes.items():
                i = int(k)
                sc = _clean_screen(v, cat)
                if 0 <= i < len(beats) and sc and not beats[i].get("screen") and not (sc["family"] == "celular" and not sc.get("why")):
                    beats[i]["screen"] = sc
        except (llm.LLMError, ValueError, TypeError) as e:
            warn.append(f"pedido extra de telas falhou: {e}")
    auto_screens(beats, cat, rng, warn)
    ensure_tv(beats, cat, rng, warn)
    if picks.get("opening") == "screen_first" and not beats[0].get("screen"):
        picks["opening"] = "close_first"
    end = advance_state(state, beats, data, n, picks, rng)
    m = data.get("mission") if isinstance(data.get("mission"), dict) else {}
    ep: dict[str, Any] = {k: data.get(k) for k in ("title", "thumbnail_text", "description", "arc_title", "cliffhanger", "memory", "next_hook")}
    ep.update(hashtags=[str(h) for h in (data.get("hashtags") or [])][:5], tags=[str(t) for t in (data.get("tags") or [])][:15],
              facts=[str(f) for f in (data.get("facts") or [])][:20], mission=_mission(m), clock={},
              objectives=[str(o)[:44] for o in (data.get("objectives") or [])][:4], beats=beats, render_style="vetor",
              decision=decision,
              vetor={"state_start": state, "state_end": end, "choice": choice, "picks": picks, "warnings": warn[:30]})
    return ep, decision


# ================================================================ pedido

def write_episode(ch: Channel, b: dict[str, Any], fmt: str = "short", *, idea: Idea | None = None, topic: str = "",
                  arc: dict[str, Any] | None = None, plan: dict[str, Any] | None = None, seconds: float | None = None,
                  log=None, series_block: str = "", research_ok: bool = True, research_query: str = "") -> dict[str, Any]:
    """Mesma assinatura e mesmo retorno de writer.write_episode (ativado por ele quando render_style == "vetor")."""
    from .bible import voice_for
    plan = plan or {}
    rng = random.Random(f"{ch.id}-{time.time()}")
    lo_s, hi_s = (b.get("vetor_seconds") or [75, 90])[:2]
    seconds = float(seconds or rng.uniform(lo_s, hi_s))
    if arc and arc.get("idea_id") and idea is None:
        from ..db import session
        with session() as s:
            idea = s.get(Idea, arc["idea_id"])
    topic = topic or (arc or {}).get("topic") or (f"{idea.title}. {idea.summary}" if idea else "")
    n = len((arc or {}).get("parts") or []) + 1
    cat = catalog()
    if log:
        log("Catálogo vetorial: " + ", ".join(f"{k} {len(cat[k])} ({cat['source'][k]})" for k in ("sets", "props", "screens")))
    state = load_state(arc, n)
    picks = pick_variety(state, rng)
    parts = ((arc or {}).get("plan") or {}).get("parts") or []
    last = bool(parts) and n >= len(parts)
    planned = parts[n - 1].get("decision") if 0 < n <= len(parts) else None
    # votação só nas partes que o plano marcou (série sequencial não tem); bible["vetor_vote"] = false desliga no canal
    ask_choice = bool(arc) and bool(planned) and not last and b.get("vetor_vote", True) is not False
    try:
        rate = int(str(voice_for(b, "narrador").get("rate") or "+0%").strip().rstrip("%"))
    except ValueError:
        rate = 0
    n_beats = max(14, int(seconds / 3.9))
    lo, hi = _words(seconds, rate, n_beats)
    prompt = build_prompt(ch, b, cat=cat, state=state, topic=topic, arc=arc, n=n, seconds=seconds, words=(lo, hi), n_beats=n_beats,
                          picks=picks, ask_choice=ask_choice, series_block=series_block)
    data = llm.complete_json(prompt, temperature=0.8, required=("beats", "title"), timeout=180)

    def size(d: dict[str, Any]) -> tuple[int, int]:
        bb = [x for x in d.get("beats") or [] if isinstance(x, dict)]
        return len(bb), sum(len(str(x.get("text") or "").split()) for x in bb)
    # o LLM às vezes devolve um esboço curto: sem isso o episódio sai com 20 s em vez de 80
    for _ in range(2):
        got_beats, got_words = size(data)
        if got_beats >= n_beats * 0.75 and got_words >= lo * 0.8:
            break
        if log:
            log(f"Roteiro curto ({got_beats} beats, {got_words} palavras): pedindo de novo")
        again = llm.complete_json(prompt + f"\n\nATENÇÃO: sua resposta anterior veio curta demais ({got_beats} beats, {got_words} palavras). "
                                  f"Escreva o episódio INTEIRO: no mínimo {n_beats} beats e {lo} palavras de fala no total.",
                                  temperature=0.8, required=("beats", "title"), timeout=180)
        if size(again)[1] > got_words:
            data = again

    def fix(beats: list[dict[str, Any]], count: int, miss: list[str]) -> dict[str, Any]:
        r = llm.complete_json(repair_prompt(beats, cat, count, miss, arc, b), temperature=0.6, required=("screens",), timeout=90)
        return r.get("screens") if isinstance(r.get("screens"), dict) else {}
    ep, decision = finish(data, b, cat, state, n=n, picks=picks, rng=rng, ask_choice=ask_choice, planned=planned, max_words=hi + 10, fix_screens=fix)
    ep.update(part=n, episode_style=picks["structure"], seconds_target=round(seconds), words=[lo, hi], topic=topic,
              idea_id=idea.id if idea else None, sources=[])
    if log and ep["vetor"]["warnings"]:
        log(f"Roteiro vetorial corrigido: {'; '.join(ep['vetor']['warnings'][:6])}")
    if arc and arc.get("id"):
        _commit_series(ch.slug, arc, n, ep["vetor"]["state_end"], decision)
    return ep
