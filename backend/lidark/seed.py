"""Canal inicial: Ouro do Passado (recriado a partir dos vídeos publicados)."""
from sqlmodel import select

from .db import session
from .models import Channel

OURO_THEME = {
    "bg_center": "#16473a", "bg_edge": "#061915",
    "card": "#f5e9d9", "card_edge": "#e9dcc8", "card_line": "#d8a943",
    "gold": "#d9a53a", "gold_light": "#f2c862", "ink": "#0c3223",
    "caption_bg": "#121814", "caption_border": "#5a4a1f", "caption_text": "#f1efe6",
    "caption_dim": "#8d918a", "caption_hi": "#e9b440",
    "logo_letter": "P", "handle": "@ourodopassado", "slogan": "AQUI O PASSADO VALE OURO",
    "outro_title": "SEGUE PRA MAIS", "mascot": "clock", "step_label": "PASSO",
    "font_title": "Cinzel.ttf", "font_caption": "FiraSans-ExtraBold.ttf", "font_ui": "FiraSans-Bold.ttf",
}

OURO_GUIDE = """- Curiosidades históricas REAIS, com foco em temas que caem no ENEM (Brasil Colônia, Império, República, Era Vargas, Ditadura, Antiguidade, Idade Média, Revoluções, Guerras Mundiais, Guerra Fria).
- Formato "mito × verdade": a crença popular e depois a revelação surpreendente.
- Títulos em forma de pergunta provocativa (ex.: "Como Lampião foi morto na verdade?", "Cleópatra era mesmo egípcia?").
- Comparações com o presente para o estudante entender (ex.: "como um presidente brasileiro aprendendo tupi-guarani").
- Sempre citar as fontes na descrição.
- Slogan: "Aqui o passado vale ouro". Assinatura: "Uma história do passado todo dia"."""


def seed() -> None:
    with session() as s:
        ch = s.exec(select(Channel).where(Channel.slug == "ouro-do-passado")).first()
        if ch:
            changed = False
            if not ch.handle:
                ch.handle, changed = "@ourodopassado", True
            missing = {k: v for k, v in OURO_THEME.items() if k not in (ch.theme or {})}
            if missing:
                ch.theme, changed = {**(ch.theme or {}), **missing}, True
            if changed:
                s.add(ch)
                s.commit()
            return
        s.add(Channel(
            name="Ouro do Passado", slug="ouro-do-passado", handle="@ourodopassado",
            niche="curiosidades históricas para o ENEM",
            audience="estudantes de 15 a 24 anos se preparando para o ENEM e curiosos por história",
            description="Uma história do passado todo dia. Aqui o passado vale ouro.",
            editorial_guide=OURO_GUIDE,
            tone="intrigante, didático, revelador, frases curtas",
            formats=["short", "long"], short_seconds=65, long_minutes=6,
            voice_provider="edge", voice_name="pt-BR-AntonioNeural", voice_rate="+10%",
            visual_mode="mixed", template="livre", theme=OURO_THEME,
            default_hashtags=["#Shorts", "#HistóriaDoBrasil", "#ENEM", "#Curiosidades", "#História"],
            cta="Segue o Ouro do Passado pra mais!", color="#d9a53a",
        ))
        s.commit()
