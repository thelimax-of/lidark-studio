"""Assistente "Novo canal": do nicho ao canal configurado.

1) propor: a IA monta a identidade do nicho + 3 opções de nome; cada opção ganha o kit visual no estilo das
   imagens do Sinal do Cosmos (fundo temático, símbolo brilhando, nome em destaque) — tarefa "brand_propose";
2) escolher: a IA escreve os textos do canal (bio, palavras-chave, playlists, linha editorial) e um TXT para
   copiar no YouTube Studio — tarefa "brand_texts";
3) conectar: quando o canal criado no YouTube é conectado (mesmo @ ou nome), a identidade é aplicada e travada —
   a configuração automática não troca nada e não cria pautas sozinha.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from sqlmodel import select

from . import llm
from .brandkit import SYMBOLS, render_kit
from .channels import CAPTION_FONTS, FONTS, PALETTE_KEYS, VOICES, _hex, theme_from_identity
from .config import MEDIA_DIR
from .db import session
from .jobs import JobContext, handler
from .models import BrandDraft, Channel

log = logging.getLogger("lidark.brandwizard")

MOTIFS = {"lab": "moléculas e bolhas (ciência)", "chart": "grade de gráfico e candles (dinheiro, mercado)",
          "particles": "partículas e nebulosas (genérico, espaço, mistério, história)"}
CATEGORIES = {"27": "Educação", "17": "Esportes", "28": "Ciência e tecnologia", "22": "Pessoas e blogs",
              "24": "Entretenimento", "19": "Viagens e eventos", "25": "Notícias e política"}


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", s)


def draft_dict(d: BrandDraft) -> dict[str, Any]:
    return {"id": d.id, "niche": d.niche, "notes": d.notes, "options": d.options, "chosen": d.chosen,
            "identity": d.identity, "texts": d.texts, "status": d.status, "channel_id": d.channel_id,
            "txt_url": f"/media/_novos/{d.id}/textos.txt" if d.texts else "",
            "created_at": d.created_at.isoformat() if d.created_at else None}


# ================================================================ 1) proposta

def _identity_prompt(niche: str, notes: str, taken: list[str]) -> str:
    from .render.characters import KINDS
    return f"""Você é diretor de criação de canais "dark" (sem rosto) do YouTube no Brasil.
Monte a identidade de um canal NOVO no nicho: {niche}
{('OBSERVAÇÕES DO DONO: ' + notes) if notes else ''}
NOMES JÁ USADOS PELO DONO (não repita nem imite): {', '.join(taken) or '(nenhum)'}

Crie 3 opções de nome bem diferentes entre si (curtas, fáceis de lembrar, sem marcas registradas de terceiros),
cada uma com @ (só letras minúsculas sem acento e números) e um slogan curto.
A identidade visual/editorial é a mesma para as 3 opções.

Mascote (aparece animado nos vídeos e na capa): {', '.join(f'{k} = {v}' for k, v in KINDS.items() if k != 'none')}
Símbolo da foto de perfil (brilhando no centro): {', '.join(SYMBOLS)} ou "mascot" (usa o mascote como símbolo)
Fundo temático: {', '.join(f'{k} = {v}' for k, v in MOTIFS.items())}
Fonte do nome: {', '.join(f'{k} = {v}' for k, v in FONTS.items())}
Fonte das legendas: {', '.join(CAPTION_FONTS)}
Categoria do YouTube: {', '.join(f'{k} = {v}' for k, v in CATEGORIES.items())}

Paleta: fundo escuro (bg_center um pouco mais claro que bg_edge), "gold" = cor de destaque da marca (viva),
"card" claro com "ink" escuro, "caption_hi" = destaque das legendas. "logo_text" = cor do NOME na foto de perfil,
contrastando com o fundo e com o "gold" (ex.: amarelo sobre fundo roxo).

Responda JSON:
{{"options": [{{"name": "...", "handle": "...", "tagline": "..."}}, {{...}}, {{...}}],
"niche": "nicho em 1 frase", "audience": "...", "tone": "...", "description": "proposta em 1 frase",
"image_style": "estilo das imagens em inglês", "music_mood": "trilha em inglês (2-4 palavras)",
"voice_gender": "male|female", "voice_rate": "+0% a +12%", "short_seconds": 60-75,
"mascot": "tipo", "mascot_color": "#hex", "mascot_accent": "#hex", "symbol": "...", "motif": "...",
"font_title": "arquivo.ttf", "font_caption": "arquivo.ttf", "logo_text": "#hex",
"palette": {{{', '.join(f'"{k}": "#hex"' for k in PALETTE_KEYS)}}},
"badge": "ETIQUETA CURTA DA CAPA (ex.: NOVOS VÍDEOS TODO DIA)", "step_label": "PASSO/FATO/PISTA...",
"yt_category": "27", "footage": true/false (true só se o nicho tem muita filmagem livre: espaço, ciência, natureza),
"image_credit_ok": true/false (true se fotos reais do nicho quase sempre exigem crédito: esportes, celebridades, música),
"formats": ["short", "long"], "posting_slots": ["HH:MM", "HH:MM"]}}"""


def _theme(idn: dict[str, Any], name: str, handle: str, tagline: str) -> dict[str, Any]:
    th = theme_from_identity(idn)
    th.update({
        "logo_style": "icon", "motif": idn.get("motif") if idn.get("motif") in MOTIFS else "particles",
        "symbol": idn.get("symbol") if idn.get("symbol") in SYMBOLS else th.get("mascot"),
        "logo_text": _hex(idn.get("logo_text"), "#ffd24a"), "badge": str(idn.get("badge") or "NOVOS VÍDEOS TODA SEMANA")[:32].upper(),
        "slogan": tagline.upper()[:40], "handle": handle, "logo_letter": (name[:1] or "L").upper(),
        "outro_title": "SEGUE PRA MAIS", "step_label": str(idn.get("step_label") or "PASSO")[:10].upper(),
    })
    return th


@handler("brand_propose")
def job_propose(ctx: JobContext) -> dict:
    with session() as s:
        d = s.get(BrandDraft, ctx.ref_id)
        taken = [c.name for c in s.exec(select(Channel)).all()]
    ctx.update(0.1, "IA criando nomes e identidade")
    idn = llm.complete_json(_identity_prompt(d.niche, d.notes, taken), temperature=0.8)
    opts = [o for o in (idn.get("options") or []) if isinstance(o, dict) and o.get("name")][:3]
    if not opts:
        raise RuntimeError("A IA não devolveu opções de nome — tente de novo")
    out_opts = []
    for i, o in enumerate(opts):
        name = str(o["name"]).strip()[:40]
        handle = "@" + (_plain(o.get("handle") or name) or f"canal{i + 1}")
        tagline = str(o.get("tagline") or "").strip()[:60]
        ctx.update(0.3 + 0.6 * i / len(opts), f"Desenhando o kit de “{name}”")
        folder = MEDIA_DIR / "_novos" / str(d.id) / str(i + 1)
        paths = render_kit(_theme(idn, name, handle, tagline), name, handle, folder, tagline)
        out_opts.append({"name": name, "handle": handle, "tagline": tagline,
                         "kit": {k: f"/media/_novos/{d.id}/{i + 1}/{p.name}" for k, p in paths.items()}})
    with session() as s:
        d = s.get(BrandDraft, ctx.ref_id)
        d.options, d.identity = out_opts, {k: v for k, v in idn.items() if k != "options"}
        s.add(d)
        s.commit()
    return {"options": len(out_opts)}


# ================================================================ 2) textos

@handler("brand_texts")
def job_texts(ctx: JobContext) -> dict:
    with session() as s:
        d = s.get(BrandDraft, ctx.ref_id)
    o = d.options[d.chosen]
    idn = d.identity
    ctx.update(0.2, "IA escrevendo bio, palavras-chave e linha editorial")
    prompt = f"""Escreva os textos do canal do YouTube "{o['name']}" ({o['handle']}), slogan "{o['tagline']}".
Nicho: {idn.get('niche')}. Público: {idn.get('audience')}. Tom: {idn.get('tone')}. Canal "dark" (sem rosto), em português do Brasil.

Regras:
- bio: 600-900 caracteres, com 3-4 emojis no máximo, frequência de vídeos e chamada pro sininho; termina com o slogan.
- bio_curta: até 150 caracteres (Instagram/TikTok), 3 linhas.
- keywords: palavras-chave do canal separadas por VÍRGULA, sem aspas, até 450 caracteres, começando pelo nome do canal.
- hashtags: 6 hashtags, a 1ª é o nome do canal.
- playlists: 6-7 séries de vídeos do nicho.
- editorial_guide: 8-10 regras em tópicos ("- ..."): fatos reais e verificáveis, formatos variados, gancho nos 2 primeiros segundos,
  títulos variados, o que NUNCA fazer no nicho (ex.: saúde → nenhum conselho médico; dinheiro → nenhuma recomendação de compra ou
  promessa de lucro; esportes → nada de trechos de transmissão), citar fontes.
- radar_keywords: 8-10 termos de busca para o radar de tendências.
Responda JSON: {{"bio": "...", "bio_curta": "...", "keywords": "...", "hashtags": ["#..."], "cta": "chamada final curta",
"comentario_fixado": "...", "playlists": ["..."], "editorial_guide": "- ...", "radar_keywords": ["..."]}}"""
    t = llm.complete_json(prompt, temperature=0.6)
    t["keywords"] = ", ".join(x.strip().strip('"') for x in re.split(r"[,\n]", str(t.get("keywords", ""))) if x.strip())[:480]
    with session() as s:
        d = s.get(BrandDraft, ctx.ref_id)
        d.texts, d.status = t, "chosen"
        s.add(d)
        s.commit()
    _write_txt(d)
    return {}


def _write_txt(d: BrandDraft) -> None:
    o, t, idn = d.options[d.chosen], d.texts, d.identity
    cat = str(idn.get("yt_category") or "27")
    txt = f"""==========================================================
 {o['name'].upper()} — textos para configurar o canal
==========================================================

NOME DO CANAL
{o['name']}

IDENTIFICADOR (@)
{o['handle']}

SLOGAN
{o['tagline']}

----------------------------------------------------------
BIO / DESCRIÇÃO (Studio → Personalização → Informações básicas)
----------------------------------------------------------

{t.get('bio', '')}

----------------------------------------------------------
BIO CURTA (Instagram / TikTok)
----------------------------------------------------------

{t.get('bio_curta', '')}

----------------------------------------------------------
PALAVRAS-CHAVE (Studio → Configurações → Canal) — cole a linha inteira
----------------------------------------------------------

{t.get('keywords', '')}

----------------------------------------------------------
HASHTAGS PADRÃO
----------------------------------------------------------

{' '.join(t.get('hashtags') or [])}

----------------------------------------------------------
CHAMADAS
----------------------------------------------------------

Fim de vídeo:      {t.get('cta', '')}
Comentário fixado: {t.get('comentario_fixado', '')}

----------------------------------------------------------
PLAYLISTS / SÉRIES
----------------------------------------------------------

{chr(10).join('- ' + p for p in t.get('playlists') or [])}

----------------------------------------------------------
CONFIGURAÇÕES NO YOUTUBE STUDIO
----------------------------------------------------------

País ........ Brasil
Idioma ...... Português (Brasil)
Categoria ... {CATEGORIES.get(cat, cat)}
Público ..... "Não, não é conteúdo para crianças"
Imagens ..... foto_perfil_800.png · capa_2560x1440.jpg · marca_dagua_150.png (pasta da opção {d.chosen + 1})

----------------------------------------------------------
LINHA EDITORIAL (o sistema segue nos roteiros)
----------------------------------------------------------

{t.get('editorial_guide', '')}
"""
    folder = MEDIA_DIR / "_novos" / str(d.id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "textos.txt").write_text(txt, encoding="utf-8")


# ================================================================ 3) aplicar no canal conectado

def find_draft_for(name: str, handle: str) -> BrandDraft | None:
    with session() as s:
        for d in s.exec(select(BrandDraft).where(BrandDraft.status == "chosen").order_by(BrandDraft.id.desc())).all():
            o = d.options[d.chosen] if 0 <= d.chosen < len(d.options) else {}
            if (handle and _plain(o.get("handle", "")) == _plain(handle)) or (_plain(o.get("name", "")) == _plain(name)):
                return d
    return None


def apply_draft(draft_id: int, channel_id: int) -> None:
    with session() as s:
        d = s.get(BrandDraft, draft_id)
        ch = s.get(Channel, channel_id)
        o, idn, t = d.options[d.chosen], d.identity, d.texts or {}
        th = _theme(idn, o["name"], ch.handle or o["handle"], o["tagline"])
        th.update({"_locked_visual": True, "_draft_applied": d.id})
        ch.theme, ch.color = th, th["gold"]
        for k in ("niche", "audience", "tone", "image_style", "music_mood"):
            if idn.get(k):
                setattr(ch, k, str(idn[k]))
        ch.description = o["tagline"]
        ch.editorial_guide = str(t.get("editorial_guide") or ch.editorial_guide)
        ch.cta = str(t.get("cta") or ch.cta)
        if t.get("hashtags"):
            ch.default_hashtags = [h if h.startswith("#") else "#" + h for h in t["hashtags"]][:8]
        if idn.get("voice_gender") in VOICES:
            ch.voice_provider, ch.voice_name = "edge", VOICES[idn["voice_gender"]][0]
        if isinstance(idn.get("voice_rate"), str) and re.fullmatch(r"[+-]\d{1,2}%", idn["voice_rate"]):
            ch.voice_rate = idn["voice_rate"]
        try:
            ch.short_seconds = max(60, min(90, int(idn.get("short_seconds") or ch.short_seconds)))
        except (TypeError, ValueError):
            pass
        fm = [f for f in idn.get("formats") or [] if f in ("short", "long")]
        ch.formats = fm or ["short", "long"]
        slots = [x for x in idn.get("posting_slots") or [] if re.fullmatch(r"\d{2}:\d{2}", str(x))]
        if slots:
            ch.posting_slots = slots[:3]
        ch.template, ch.templates, ch.visual_mode = "livre", ["livre", "ouro"], "real"
        ch.footage, ch.image_credit_ok = bool(idn.get("footage")), bool(idn.get("image_credit_ok"))
        ch.yt_category = str(idn.get("yt_category")) if str(idn.get("yt_category")) in CATEGORIES else "27"
        ch.radar = {**(ch.radar or {}), "keywords": [str(x) for x in t.get("radar_keywords") or []][:12]}
        d.status, d.channel_id = "applied", ch.id
        s.add(ch)
        s.add(d)
        s.commit()
    log.info("rascunho %s aplicado no canal %s", draft_id, channel_id)
