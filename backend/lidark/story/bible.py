"""Bíblia da série de cada canal: estilo de arte, paleta, época/cenário, personagens recorrentes (descrição VERBATIM +
semente fixa = consistência), vozes e HUD. Fica em data/story/<slug>/bible.json (editável no painel); quando não
existe, nasce destes padrões.

Originalidade: o GÊNERO (história em série com HUD de missão) é livre; personagens, estilo e roteiros são nossos.
Nada de copiar personagem, nome, layout ou texto de outro criador.
"""
from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Any

from ..config import DATA_DIR

STORY_DIR = DATA_DIR / "story"
_lock = threading.Lock()

COMMON_POSES = {
    "front": "standing, front view, arms relaxed at the sides, calm neutral expression",
    "worried": "standing, front view, hands clasped near chest, worried expression, eyebrows raised",
    "surprised": "standing, front view, both hands on the sides of the head, shocked expression",
    "pointing": "standing, three-quarter view, pointing forward with the right arm extended",
    "running": "running to the right, side view, dynamic pose, one leg forward",
    "thinking": "standing, three-quarter view, one hand on the chin, thinking",
    "talking": "standing, three-quarter view, one hand open gesturing while explaining",
    "sitting": "sitting on the floor hugging the knees, front view",
    "back": "standing, back view, looking away into the distance",
    "celebrating": "jumping with both fists raised, happy",
}

# --------------------------------------------------------------------------------------------- padrões por canal
DEFAULTS: dict[str, dict[str, Any]] = {
    "ouro-do-passado": {
        "series_title": "Acordei no Passado",
        "premise": ("Zé, um rapaz comum, acorda de repente num momento decisivo da história do Brasil e do mundo e tem "
                    "um prazo para sobreviver/cumprir a missão. Cada arco é um evento REAL (datas, nomes e fatos exatos, "
                    "úteis para o ENEM); Zé e os vizinhos são ficcionais e só vivem o que de fato aconteceu."),
        "style": ("flat 2D storybook illustration, muted earthy palette of teal, ochre, cream and brown, clean ink outlines, "
                  "soft painterly shading, cinematic lighting, detailed period setting, no text, no signature"),
        "palette": ["#2f4a46", "#c99a4b", "#efe3c8", "#5a3b25", "#f2ba40"],
        "era": "varia por arco (ex.: Rio de Janeiro, novembro de 1904)",
        "narrator_voice": "", "narrator_rate": "+4%",
        "characters": [
            {"id": "ze", "name": "Zé", "role": "protagonista", "seed": 19041,
             "desc": ("a young man whose head is a perfectly round smooth cream-colored sphere with two small black dot eyes "
                      "and a tiny simple mouth, no hair, brown newsboy cap, white collared shirt with rolled sleeves, dark "
                      "brown suspenders, dark grey trousers, brown leather shoes"),
             "eyes": "dots", "voice": "pt-BR-AntonioNeural", "pitch": "+14Hz", "rate": "+6%"},
            {"id": "maria", "name": "Dona Maria", "role": "vizinha", "seed": 19042,
             "desc": ("an elderly neighbor lady whose head is a smooth round cream-colored sphere with two small black dot eyes, "
                      "grey hair in a bun, long dark brown dress with a white apron, shawl over the shoulders"),
             "eyes": "dots", "voice": "pt-BR-FranciscaNeural", "pitch": "-6Hz", "rate": "-4%"},
        ],
        "poses": ["front", "worried", "surprised", "pointing", "running", "thinking", "sitting", "back"],
        "hud": {"style": "historia", "accent": "#f2ba40", "panel": [14, 13, 12, 220], "text": "#ebe6dc", "danger": "#d63a30",
                "paper": "#ece2cc", "font_title": "Anton-Regular.ttf", "font_ui": "ChakraPetch-Bold.ttf",
                "font_type": "SpecialElite.ttf", "font_paper": "PlayfairDisplay.ttf", "paper_names":
                ["Gazeta do Povo Carioca", "Correio da Rua", "Folha do Largo", "O Mensageiro Popular"],
                "clock": "date", "grade": "sepia",
                "widgets": ["mission", "objectives", "newspaper", "dialogue", "highlight", "alert", "countdown", "map",
                            "inventory", "telegram", "chip", "endcard"],
                "devices": ["newsboy", "proclamation"]},
        "missions": ["SOBREVIVA 72H", "CHEGUE AO PORTO", "ATRAVESSE A CIDADE", "ENTREGUE A CARTA", "PROTEJA A FAMÍLIA",
                     "ESCAPE ANTES DO TOQUE DE RECOLHER", "DESCUBRA O QUE ACONTECEU"],
        "locations": ["narrow cobblestone street with old townhouses", "simple rented room with a wooden bed and a window",
                      "crowded public square", "harbor with sailing ships", "tram line avenue", "candle-lit tenement corridor"],
    },
    "sinal-do-cosmos": {
        "series_title": "Missão: Sinal",
        "premise": ("A cadete Iara e o robô Bit vivem, como passageiros invisíveis, missões espaciais REAIS (Apollo 13, "
                    "Voyager, Estação Espacial, sondas em Marte...). Tudo que acontece com as naves, datas, horários e "
                    "números é real; Iara e Bit são o ponto de vista ficcional do espectador."),
        "style": ("flat 2D retro-futurist graphic novel illustration, deep navy, violet and teal palette with warm amber "
                  "highlights, clean ink outlines, soft glow lighting, grainy texture, no text, no signature"),
        "palette": ["#0d1633", "#3b2a6b", "#1f8a8a", "#f59e0b", "#e8e6f7"],
        "era": "missões espaciais reais (1960 até hoje)",
        "narrator_voice": "", "narrator_rate": "+3%",
        "characters": [
            {"id": "iara", "name": "Iara", "role": "protagonista", "seed": 2021,
             "desc": ("a young woman cadet astronaut with a simple round cartoon face, light tan skin, two small black dot "
                      "eyes, short curly dark hair, chunky white and orange retro space suit with a round collar ring and a "
                      "small blue mission patch, white boots"),
             "eyes": "dots", "voice": "pt-BR-ThalitaMultilingualNeural", "pitch": "+0Hz", "rate": "+4%"},
            {"id": "bit", "name": "Bit", "role": "parceiro", "seed": 2022,
             "desc": ("a small boxy friendly maintenance robot, rounded white metal body, a round bright cyan screen as its "
                      "face showing two black dot eyes, two short antennas, small treads instead of legs"),
             "eyes": "dots", "voice": "pt-BR-FranciscaNeural", "pitch": "+40Hz", "rate": "+12%"},
        ],
        "poses": ["front", "worried", "surprised", "pointing", "thinking", "talking", "back", "celebrating"],
        "hud": {"style": "espaco", "accent": "#4fd1ff", "panel": [8, 14, 30, 225], "text": "#e6f1ff", "danger": "#ff4d4d",
                "paper": "#0f1c33", "font_title": "Audiowide.ttf", "font_ui": "ChakraPetch-Bold.ttf",
                "font_type": "ChakraPetch-Bold.ttf", "font_paper": "Exo2.ttf", "paper_names": ["CONSOLE DE MISSÃO"],
                "clock": "met", "grade": "cool",
                "widgets": ["mission", "objectives", "console", "dialogue", "highlight", "alert", "countdown", "inventory",
                            "chip", "endcard"],
                "devices": ["comms", "tv", "phone"]},
        "missions": ["VOLTE PARA CASA", "MANTENHA O SINAL", "POUSE COM SEGURANÇA", "CONSERTE A NAVE", "ECONOMIZE OXIGÊNIO",
                     "CHEGUE À ÓRBITA"],
        "locations": ["cramped spacecraft cabin with switches and round windows", "mission control room with rows of consoles",
                      "view of Earth from orbit", "lunar surface under black sky", "launch pad at dawn",
                      "dark space with a distant probe"],
    },
    "placar-historico": {
        "series_title": "Gandula do Tempo",
        "premise": ("Dudu, um gandula curioso, aparece à beira do campo em jogos e momentos REAIS da história do futebol. "
                    "Placar, minutos, escalações e fatos são reais e conferidos; Dudu e o narrador de rádio Seu Arlindo são "
                    "ficcionais."),
        "style": ("flat 2D vintage sports poster illustration, warm sunlit palette of grass green, cream, red and gold, "
                  "halftone print texture, bold ink outlines, dynamic angles, no text, no signature"),
        "palette": ["#1f6b3a", "#f3e7c9", "#c8372d", "#efb630", "#20201e"],
        "era": "partidas reais (1930 até hoje)",
        "narrator_voice": "", "narrator_rate": "+6%",
        "characters": [
            {"id": "dudu", "name": "Dudu", "role": "protagonista", "seed": 1950,
             "desc": ("a young ball boy whose head is a round classic brown leather football with stitched panels and two "
                      "small black dot eyes painted on a cream panel, white cotton jersey with green collar, black shorts, "
                      "long white socks, black boots"),
             "eyes": "dots", "voice": "pt-BR-AntonioNeural", "pitch": "+18Hz", "rate": "+8%"},
            {"id": "arlindo", "name": "Seu Arlindo", "role": "narrador de rádio", "seed": 1951,
             "desc": ("a chubby middle-aged radio announcer with a simple round cartoon face, two small black dot eyes, "
                      "big black moustache, slicked hair, beige suit with a bow tie, holding a vintage microphone"),
             "eyes": "dots", "voice": "pt-BR-AntonioNeural", "pitch": "-8Hz", "rate": "+16%"},
        ],
        "poses": ["front", "worried", "surprised", "pointing", "running", "celebrating", "thinking", "back"],
        "hud": {"style": "futebol", "accent": "#efb630", "panel": [16, 22, 16, 225], "text": "#f3ecd8", "danger": "#e04434",
                "paper": "#f0e6c8", "font_title": "Anton-Regular.ttf", "font_ui": "Oswald.ttf", "font_type": "SpecialElite.ttf",
                "font_paper": "PlayfairDisplay.ttf", "paper_names": ["Folha do Gramado", "O Arquibancada", "Diário da Bola"],
                "clock": "match", "grade": "warm",
                "widgets": ["mission", "scoreboard", "newspaper", "dialogue", "highlight", "alert", "countdown",
                            "objectives", "chip", "endcard"],
                "devices": ["radio", "tv"]},
        "missions": ["NÃO PERCA O LANCE", "CHEGUE AO ESTÁDIO", "ENTREGUE A BOLA", "SOBREVIVA AOS 90 MINUTOS",
                     "DESCUBRA O SEGREDO DO TIME"],
        "locations": ["packed old stadium stands", "grass pitch seen from the touchline", "old radio booth above the stands",
                      "locker room with wooden benches", "city street celebrating with flags"],
    },
    "laboratorio-diario": {
        "series_title": "Missão Cotidiano",
        "premise": ("Gota, uma cientista minúscula, enfrenta desafios do dia a dia vistos pela ciência: encolhida na cozinha, "
                    "dentro do corpo, num dia sem dormir. A ciência (números, processos, causas) é real e conferida; a "
                    "aventura é a moldura."),
        "style": ("clean flat 2D vector-like illustration, bright mint, white and coral palette, soft shadows, friendly "
                  "science cartoon look, simple shapes, no text, no signature"),
        "palette": ["#82d1a0", "#ffffff", "#ff7a6b", "#1f3b4d", "#ffd166"],
        "era": "hoje, ciência do cotidiano",
        "narrator_voice": "", "narrator_rate": "+8%",
        "characters": [
            {"id": "gota", "name": "Gota", "role": "protagonista", "seed": 3301,
             "desc": ("a small scientist whose head is a smooth light-blue water droplet shape with two small black dot eyes "
                      "and a tiny smile, white lab coat, round safety goggles pushed up on the head, mint green gloves, "
                      "coral sneakers"),
             "eyes": "dots", "voice": "pt-BR-ThalitaMultilingualNeural", "pitch": "+10Hz", "rate": "+6%"},
            {"id": "prof", "name": "Professor Átomo", "role": "mentor", "seed": 3302,
             "desc": ("an old friendly scientist with a simple round cartoon face, two small black dot eyes, white bushy "
                      "eyebrows and moustache, bald head, round glasses, mint sweater under a lab coat"),
             "eyes": "dots", "voice": "pt-BR-AntonioNeural", "pitch": "-10Hz", "rate": "-2%"},
        ],
        "poses": ["front", "worried", "surprised", "pointing", "thinking", "talking", "running", "celebrating"],
        "hud": {"style": "laboratorio", "accent": "#5fe0a0", "panel": [14, 28, 36, 220], "text": "#effaf4", "danger": "#ff6b5b",
                "paper": "#fbfbf3", "font_title": "Righteous.ttf", "font_ui": "ChakraPetch-Bold.ttf",
                "font_type": "SpecialElite.ttf", "font_paper": "Nunito.ttf", "paper_names": ["CADERNO DE LABORATÓRIO"],
                "clock": "lab", "grade": "clean",
                "widgets": ["mission", "objectives", "notebook", "dialogue", "highlight", "alert", "countdown", "inventory",
                            "chip", "endcard"],
                "devices": ["monitor", "phone", "tv"]},
        "missions": ["SOBREVIVA À COZINHA", "AGUENTE 24H SEM DORMIR", "ATRAVESSE O CORPO", "DESCUBRA O VENENO",
                     "ESFRIE A BEBIDA EM 5 MIN"],
        "locations": ["giant kitchen counter seen from a tiny perspective", "inside the human body with red blood vessels",
                      "bright school laboratory bench", "bedroom at night with a glowing phone", "supermarket aisle"],
    },
}

# Vozes por PAPEL (narrador, cada personagem, aparelhos). provider: edge (ilimitado) | gemini (melhor, com "style",
# cota grátis curta). O provedor é escolhido UMA vez por episódio e papel (nunca mistura no mesmo papel).
# Personagem sem entrada aqui usa voice/pitch/rate da própria ficha.
DEFAULT_VOICES: dict[str, dict[str, Any]] = {
    # narradora: Kokoro Dora (local, ilimitada) — escolha do usuário em 30/10; vozes multilíngues erram a pronúncia
    "narrador": {"provider": "kokoro", "voice": "pf_dora", "speed": 1.0,
                 "fallback": {"voice": "pt-BR-FranciscaNeural", "rate": "-6%", "pitch": "-6Hz"},
                 "style": "Narradora brasileira de série de suspense, voz próxima e envolvente, ritmo firme"},
    "tv": {"provider": "edge", "voice": "pt-BR-FranciscaNeural", "rate": "+6%", "pitch": "+0Hz", "style": "Âncora de telejornal em plantão urgente"},
    "radio": {"provider": "edge", "voice": "pt-BR-AntonioNeural", "rate": "+16%", "pitch": "+6Hz", "style": "Locutor de rádio esportivo empolgado"},
    "phone": {"provider": "edge", "voice": "pt-BR-ThalitaMultilingualNeural", "rate": "+4%", "pitch": "+0Hz", "style": "Mensagem de voz gravada no celular"},
    "comms": {"provider": "edge", "voice": "pt-BR-AntonioNeural", "rate": "+2%", "pitch": "-2Hz", "style": "Controle de missão falando pelo rádio, calmo e técnico"},
    "newsboy": {"provider": "edge", "voice": "pt-BR-AntonioNeural", "rate": "+12%", "pitch": "+26Hz", "style": "Menino jornaleiro gritando na rua"},
    "proclamation": {"provider": "edge", "voice": "pt-BR-AntonioNeural", "rate": "-6%", "pitch": "-14Hz", "style": "Arauto lendo um edital oficial em voz alta"},
}
DEVICE_ROLES = {"tv", "radio", "phone", "comms", "newsboy", "proclamation", "monitor"}
for _b in DEFAULTS.values():
    _b["voices"] = copy.deepcopy(DEFAULT_VOICES)

GENERIC = copy.deepcopy(DEFAULTS["ouro-do-passado"])
GENERIC.update(series_title="Missão", premise="Histórias em série com fatos reais e um protagonista ficcional.",
               characters=[], locations=[])


def path(slug: str) -> Path:
    return STORY_DIR / slug / "bible.json"


def load(slug: str) -> dict[str, Any]:
    p = path(slug)
    base = copy.deepcopy(DEFAULTS.get(slug, GENERIC))
    if p.exists():
        try:
            saved = json.loads(p.read_text(encoding="utf-8"))
            base.update(saved)
            base["hud"] = {**(DEFAULTS.get(slug, GENERIC).get("hud") or {}), **(saved.get("hud") or {})}
            base["voices"] = {**DEFAULT_VOICES, **(saved.get("voices") or {})}
        except ValueError:
            pass
    base["slug"] = slug
    return base


def save(slug: str, data: dict[str, Any]) -> dict[str, Any]:
    allowed = set(DEFAULTS["ouro-do-passado"]) | {"enabled", "share", "notes", "voices", "max_parts", "dedicated", "image_model", "hero_source", "short_seconds", "render_style", "vetor_vote", "quadro_voice", "quadro_vote", "quadro_dias"}
    with _lock:
        cur = load(slug)
        for k, v in data.items():
            if k in allowed:
                cur[k] = v
        p = path(slug)
        p.parent.mkdir(parents=True, exist_ok=True)
        cur.pop("slug", None)
        p.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    return load(slug)


def character(b: dict[str, Any], cid: str) -> dict[str, Any] | None:
    return next((c for c in b.get("characters") or [] if c.get("id") == cid), None)


def pose_prompt(b: dict[str, Any], ch: dict[str, Any], pose: str) -> str:
    """Prompt de UMA pose em fundo verde puro (chroma key). Descrição verbatim + estilo fixo = consistência."""
    p = COMMON_POSES.get(pose, pose)
    return (f"{b['style']}. Full body character, {p}: {ch['desc']}. Single character, centered, the whole body visible "
            "with margin around it, isolated on a flat solid pure green #00ff00 background, no shadow on the background, "
            "no props, no text, no signature, no watermark")


def location_prompt(b: dict[str, Any], desc: str) -> str:
    return (f"{b['style']}. Empty environment background, no people, no characters: {desc}. Wide establishing view with "
            "depth, room for characters in the lower half, no text, no signature, no watermark")


def scene_prompt(b: dict[str, Any], desc: str, chars: list[dict[str, Any]]) -> str:
    who = " ".join(f"{c['name']} is {c['desc']}." for c in chars)
    return f"{b['style']}. {desc}. {who} No text, no signature, no watermark"


def prop_prompt(b: dict[str, Any], desc: str) -> str:
    return (f"{b['style']}. A single object: {desc}. Centered, isolated on a flat solid pure green #00ff00 background, "
            "no text, no signature, no watermark")


def voice_for(b: dict[str, Any], role: str) -> dict[str, Any]:
    """Configuração de voz de um papel (narrador, id de personagem ou aparelho)."""
    v = (b.get("voices") or {}).get(role)
    if v:
        return dict(v)
    c = character(b, role)
    if c:
        return {"provider": c.get("provider", "edge"), "voice": c.get("voice") or "pt-BR-FranciscaNeural",
                "rate": c.get("rate") or "+0%", "pitch": c.get("pitch") or "+0Hz", "style": c.get("style", "")}
    return dict(DEFAULT_VOICES.get(role) or DEFAULT_VOICES["narrador"])
