"""Canais: nascem do login do YouTube. Sincroniza perfil/vídeos/métricas e gera a identidade com IA
(nicho, público, tom, guia editorial, voz, paleta, fontes, mascote, modelo de vídeo)."""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Any

import httpx
from PIL import Image
from sqlmodel import select

from . import llm
from .config import MEDIA_DIR
from .db import session
from .jobs import JobContext, enqueue, handler
from .models import Account, Channel, MetricSnapshot, Publication, now

log = logging.getLogger("lidark.channels")

FONTS = {
    "Cinzel.ttf": "serifada clássica romana (história, antiguidade, épico)",
    "PlayfairDisplay.ttf": "serifada elegante (cultura, arte, luxo, biografias)",
    "Cormorant.ttf": "serifada refinada (literatura, filosofia)",
    "BebasNeue.ttf": "condensada impactante (esportes, fatos chocantes, rankings)",
    "Oswald.ttf": "condensada moderna (notícias, documentários, tecnologia)",
    "Anton-Regular.ttf": "bem pesada e grande (virais, curiosidades rápidas)",
    "Audiowide.ttf": "futurista arredondada (espaço, tecnologia, ficção científica)",
    "Exo2.ttf": "tecnológica forte (ciência, tecnologia, games)",
    "ChakraPetch-Bold.ttf": "futurista angular (tecnologia, hacking, cyberpunk)",
    "Creepster.ttf": "assustadora (terror, paranormal)",
    "SpecialElite.ttf": "máquina de escrever (crimes reais, mistérios, arquivos secretos)",
    "Righteous.ttf": "arredondada divertida (curiosidades leves, animais, infantil)",
    "Montserrat.ttf": "geométrica limpa (finanças, negócios, educação)",
    "Poppins-ExtraBold.ttf": "geométrica forte (motivação, finanças, lifestyle)",
}
CAPTION_FONTS = ["FiraSans-ExtraBold.ttf", "Poppins-ExtraBold.ttf", "Montserrat.ttf", "Nunito.ttf", "Oswald.ttf"]
VOICES = {"male": ["pt-BR-AntonioNeural"], "female": ["pt-BR-FranciscaNeural", "pt-BR-ThalitaMultilingualNeural"]}
PALETTE_KEYS = ["bg_center", "bg_edge", "card", "card_edge", "card_line", "gold", "gold_light", "ink",
                "caption_bg", "caption_border", "caption_text", "caption_dim", "caption_hi"]


# ================================================================ vínculo com o YouTube

def slugify(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "canal"


def attach_or_create(item: dict[str, Any], prefer_channel_id: int | None = None) -> tuple[int, bool]:
    """Liga o canal do YouTube a um canal do sistema (pelo ID, @ ou o canal escolhido) ou cria um novo.
    Retorna (id, criado_agora)."""
    yid = item.get("id", "")
    sn = item.get("snippet", {})
    handle = (sn.get("customUrl") or "").lower()
    if handle and not handle.startswith("@"):
        handle = "@" + handle
    with session() as s:
        ch = s.exec(select(Channel).where(Channel.youtube_id == yid)).first() if yid else None
        if not ch and handle:
            ch = next((c for c in s.exec(select(Channel)).all() if (c.handle or "").lower() == handle), None)
        if not ch and prefer_channel_id:
            ch = s.get(Channel, prefer_channel_id)
        created = ch is None
        if created:
            base, n = slugify(sn.get("title", "canal")), 2
            slug = base
            while s.exec(select(Channel).where(Channel.slug == slug)).first():
                slug, n = f"{base}-{n}", n + 1
            ch = Channel(name=sn.get("title", "Canal"), slug=slug, setup_status="pending", theme={})
        ch.youtube_id, ch.handle = yid, handle or ch.handle
        s.add(ch)
        s.commit()
        s.refresh(ch)
        return ch.id, created


def _yt_for_channel(channel_id: int):
    from .publish import _yt_client, _yt_creds
    with session() as s:
        acc = s.exec(select(Account).where(Account.channel_id == channel_id, Account.platform == "youtube")).first()
    if not acc or not acc.credentials:
        raise RuntimeError("Canal sem login do YouTube")
    return acc, _yt_client(_yt_creds(acc))


def sync_profile(channel_id: int) -> dict[str, Any]:
    acc, yt = _yt_for_channel(channel_id)
    r = yt.channels().list(part="snippet,statistics,brandingSettings,contentDetails", mine=True).execute()
    item = (r.get("items") or [{}])[0]
    sn, st, br = item.get("snippet", {}), item.get("statistics", {}), item.get("brandingSettings", {})
    thumbs = sn.get("thumbnails", {})
    avatar = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
    banner = (br.get("image") or {}).get("bannerExternalUrl", "")
    with session() as s:
        ch = s.get(Channel, channel_id)
        ch.name = sn.get("title", ch.name)
        handle = sn.get("customUrl", "")
        if handle:
            ch.handle = handle if handle.startswith("@") else "@" + handle
        # o Google bloqueia imagens carregadas de outros sites (429) → guarda cópia local
        ch.avatar_url = _cache_image(avatar, ch.slug, "avatar.jpg") or ch.avatar_url
        ch.banner_url = _cache_image(banner + "=w1280-fcrop64=1,00000000ffffffff" if banner else "", ch.slug, "banner.jpg") or ch.banner_url
        ch.yt_description = sn.get("description", "")
        ch.stats = {"subscribers": int(st.get("subscriberCount", 0)), "views": int(st.get("viewCount", 0)),
                    "videos": int(st.get("videoCount", 0)), "country": sn.get("country", ""),
                    "uploads": item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", "")}
        ch.synced_at = now()
        if ch.theme is not None and ch.handle:
            ch.theme = {**ch.theme, "handle": ch.handle}
        s.add(ch)
        s.commit()
        return ch.stats


def _cache_image(url: str, slug: str, name: str) -> str:
    if not url:
        return ""
    try:
        r = httpx.get(url, timeout=30, follow_redirects=True)
        r.raise_for_status()
        out = MEDIA_DIR / slug
        out.mkdir(parents=True, exist_ok=True)
        Image.open(io.BytesIO(r.content)).convert("RGB").save(out / name, quality=92)
        return f"/media/{slug}/{name}?v={int(now().timestamp())}"
    except Exception as e:  # noqa: BLE001
        log.warning("imagem do canal %s: %s", name, e)
        return ""


def _local_or_url(u: str) -> str:
    """Caminho local (para PIL) quando a imagem foi guardada no disco."""
    if u.startswith("/media/"):
        return str(MEDIA_DIR / u.split("?")[0][len("/media/"):])
    return u


def import_videos(channel_id: int, ctx: JobContext | None = None, limit: int = 400) -> int:
    """Importa os vídeos do canal (com estatísticas) pela API oficial."""
    acc, yt = _yt_for_channel(channel_id)
    with session() as s:
        uploads = (s.get(Channel, channel_id).stats or {}).get("uploads")
    if not uploads:
        return 0
    ids, token = [], None
    while len(ids) < limit:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=token).execute()
        ids += [it["contentDetails"]["videoId"] for it in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            break
    n = 0
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,statistics,contentDetails,status", id=",".join(ids[i:i + 50])).execute()
        for v in r.get("items", []):
            sn, st = v.get("snippet", {}), v.get("statistics", {})
            dur = _iso_dur(v.get("contentDetails", {}).get("duration", ""))
            with session() as s:
                pub = s.exec(select(Publication).where(Publication.platform == "youtube",
                                                       Publication.external_id == v["id"])).first()
                if not pub:
                    pub = Publication(channel_id=channel_id, video_id=None, account_id=acc.id, platform="youtube",
                                      status="published", external_id=v["id"])
                    n += 1
                pub.account_id = acc.id
                pub.title, pub.description = sn.get("title", ""), sn.get("description", "")
                pub.published_at = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00")) if sn.get("publishedAt") else None
                pub.duration = dur
                pub.privacy = v.get("status", {}).get("privacyStatus", "public")
                pub.url = f"https://youtube.com/shorts/{v['id']}" if dur <= 180 else f"https://youtu.be/{v['id']}"
                pub.thumbnail_url = ((sn.get("thumbnails") or {}).get("medium") or {}).get("url", "")
                s.add(pub)
                s.commit()
                s.refresh(pub)
                # mantém os dados de Analytics (retenção, tempo assistido) da leitura anterior
                prev = s.exec(select(MetricSnapshot).where(MetricSnapshot.publication_id == pub.id)
                              .order_by(MetricSnapshot.captured_at.desc())).first()
                keep = {k: getattr(prev, k) for k in ("shares", "saves", "subscribers_gained", "watch_time_minutes",
                                                      "avg_view_duration", "avg_view_percentage")} if prev else {}
                s.add(MetricSnapshot(publication_id=pub.id, channel_id=channel_id, platform="youtube",
                                     views=int(st.get("viewCount", 0)), likes=int(st.get("likeCount", 0)),
                                     comments=int(st.get("commentCount", 0)), **keep,
                                     raw={"source": "api", "format": "short" if dur <= 180 else "long"}))
                s.commit()
        if ctx:
            ctx.update(0.2 + 0.4 * min(1, (i + 50) / max(1, len(ids))), f"Importando vídeos {min(i + 50, len(ids))}/{len(ids)}")
    return n


def _iso_dur(s: str) -> float:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


# ================================================================ identidade com IA

def image_palette(url: str, n: int = 6) -> list[str]:
    if not url:
        return []
    try:
        src = _local_or_url(url)
        data = Path(src).read_bytes() if not src.startswith("http") else httpx.get(src, timeout=20, follow_redirects=True).content
        im = Image.open(io.BytesIO(data)).convert("RGB")
        im.thumbnail((200, 200))
        q = im.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
        pal = q.getpalette()[: n * 3]
        counts = sorted(q.getcolors() or [], reverse=True)
        return ["#%02x%02x%02x" % tuple(pal[i * 3: i * 3 + 3]) for _, i in counts[:n]]
    except Exception as e:  # noqa: BLE001
        log.info("paleta: %s", e)
        return []


def ai_identity(channel_id: int, parts: str = "all") -> dict[str, Any]:
    from .render.characters import KINDS
    with session() as s:
        ch = s.get(Channel, channel_id)
        titles = [p.title for p in s.exec(select(Publication).where(Publication.channel_id == channel_id)
                                          .order_by(Publication.published_at.desc())).all()][:40]
    hint = image_palette(ch.avatar_url) + image_palette(ch.banner_url, 4)
    prompt = f"""Você é diretor de criação de canais "dark" (sem rosto) no YouTube. Monte a identidade COMPLETA deste canal.

CANAL: {ch.name} ({ch.handle})
DESCRIÇÃO NO YOUTUBE: {ch.yt_description or '(vazia)'}
NICHO ATUAL (se definido): {ch.niche or '(descobrir pelos vídeos)'}
TÍTULOS DOS VÍDEOS JÁ PUBLICADOS:
{chr(10).join('- ' + t for t in titles) or '(canal novo, sem vídeos)'}
CORES DA FOTO/BANNER DO CANAL: {', '.join(hint) or '(sem imagem)'}

Escolha mascote entre: {', '.join(f'{k} = {v}' for k, v in KINDS.items())}
Escolha fonte de título entre: {', '.join(f'{k} = {v}' for k, v in FONTS.items())}
Escolha fonte de legenda entre: {', '.join(CAPTION_FONTS)}

Paleta: fundo escuro (bg_center um pouco mais claro que bg_edge), "card" claro (papel) com "ink" escuro de alto contraste,
"gold" = cor de destaque da marca, "caption_hi" = destaque das legendas (vivo, legível sobre caption_bg escuro).
Use as cores da foto/banner como base quando fizer sentido.

Responda JSON:
{{"niche": "...", "audience": "...", "tone": "...", "description": "proposta do canal em 1 frase",
"editorial_guide": "6-10 regras editoriais em tópicos (- ...), incluindo formato de título que funciona no nicho",
"image_style": "estilo das imagens de IA em inglês", "music_mood": "estilo de trilha em inglês (2-4 palavras)",
"default_hashtags": ["#..."], "cta": "chamada curta para seguir", "slogan": "SLOGAN CURTO EM MAIÚSCULAS",
"outro_title": "SEGUE PRA MAIS (ou equivalente)", "step_label": "PASSO (ou equivalente curto: PARTE, FATO, PISTA...)",
"logo_letter": "1 letra", "mascot": "tipo", "mascot_color": "#hex", "mascot_accent": "#hex",
"font_title": "arquivo.ttf", "font_caption": "arquivo.ttf",
"palette": {{{', '.join(f'"{k}": "#hex"' for k in PALETTE_KEYS)}}},
"stamp_myth": "#hex", "stamp_truth": "#hex",
"template": "livre ou ouro", "visual_mode": "real | mixed | ai",
"voice_gender": "male | female", "voice_rate": "+0% a +15%", "short_seconds": 60-75,
"format_tip": "formato de vídeo que mais funciona nesse nicho"}}"""
    data = llm.complete_json(prompt, temperature=0.7)
    if not isinstance(data, dict):
        raise RuntimeError("Resposta inválida da IA")
    _apply_identity(channel_id, data, parts)
    return data


def _hex(v: Any, default: str) -> str:
    return v if isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v) else default


def _lum(h: str) -> float:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def theme_from_identity(d: dict[str, Any], base: dict[str, Any] | None = None) -> dict[str, Any]:
    """Tema visual (paleta com garantias de contraste, mascote, fontes, textos) a partir da resposta da IA."""
    from .render.characters import KINDS
    from .seed import OURO_THEME
    th = dict(OURO_THEME)
    th.update(base or {})
    pal = d.get("palette") or {}
    for k in PALETTE_KEYS:
        th[k] = _hex(pal.get(k), th.get(k, OURO_THEME.get(k, "#888888")))
    # garantias de contraste
    if _lum(th["card"]) < 0.6:
        th["card"], th["card_edge"] = OURO_THEME["card"], OURO_THEME["card_edge"]
    if _lum(th["ink"]) > 0.3:
        th["ink"] = "#14161a"
    if _lum(th["bg_center"]) > 0.35:
        th["bg_center"], th["bg_edge"] = "#1b2430", "#0b0f14"
    if _lum(th["caption_bg"]) > 0.25:
        th["caption_bg"] = "#121417"
    th["stamp_myth"] = _hex(d.get("stamp_myth"), "#b8322a")
    th["stamp_truth"] = _hex(d.get("stamp_truth"), "#1d7a45")
    th["mascot"] = d.get("mascot") if d.get("mascot") in KINDS else th.get("mascot", "bulb")
    th["mascot_color"] = _hex(d.get("mascot_color"), th.get("mascot_color", ""))
    th["mascot_accent"] = _hex(d.get("mascot_accent"), th.get("mascot_accent", ""))
    if d.get("font_title") in FONTS:
        th["font_title"] = d["font_title"]
    if d.get("font_caption") in CAPTION_FONTS:
        th["font_caption"] = d["font_caption"]
    for k in ("slogan", "outro_title", "step_label", "logo_letter"):
        if d.get(k):
            th[k] = str(d[k])[:40] if k != "logo_letter" else str(d[k])[:1].upper()
    return th


def _apply_identity(channel_id: int, d: dict[str, Any], parts: str) -> None:
    with session() as s:
        ch = s.get(Channel, channel_id)
        if parts in ("all", "text"):
            for k in ("niche", "audience", "tone", "description", "image_style", "music_mood", "cta"):
                if d.get(k):
                    setattr(ch, k, str(d[k]))
            if d.get("editorial_guide"):
                g = d["editorial_guide"]
                ch.editorial_guide = "\n".join(g) if isinstance(g, list) else str(g)
            if isinstance(d.get("default_hashtags"), list):
                ch.default_hashtags = [h if h.startswith("#") else "#" + h for h in d["default_hashtags"]][:8]
            if d.get("voice_gender") in VOICES:
                ch.voice_provider, ch.voice_name = "edge", VOICES[d["voice_gender"]][0]
            if isinstance(d.get("voice_rate"), str) and re.fullmatch(r"[+-]\d{1,2}%", d["voice_rate"]):
                ch.voice_rate = d["voice_rate"]
            try:
                ch.short_seconds = max(60, min(90, int(d.get("short_seconds", ch.short_seconds))))
            except (TypeError, ValueError):
                pass
        if parts in ("all", "visual"):
            th = theme_from_identity(d, ch.theme)
            th["handle"] = ch.handle or th.get("handle", "")
            ch.theme = th
            ch.color = th["gold"]
            if d.get("template") in ("livre", "ouro"):
                ch.template = d["template"]
            if d.get("visual_mode") in ("real", "mixed", "ai"):
                from . import config
                # sem gerador de IA ativo, "100% IA" não faz sentido
                ch.visual_mode = "mixed" if d["visual_mode"] == "ai" and config.get("image_ai_provider") == "none" else d["visual_mode"]
        s.add(ch)
        s.commit()


# ================================================================ prévia do visual

def render_preview(channel_id: int) -> list[str]:
    """Gera 2 quadros de exemplo (abertura e cena) com o tema/mascote/modelo atuais do canal."""
    import numpy as np
    from .production import _template
    from .render.core import SceneT, Timeline, Word
    with session() as s:
        ch = s.get(Channel, channel_id)
    sample = None
    for url in (ch.banner_url, ch.avatar_url):
        if url:
            try:
                src = _local_or_url(url)
                data = Path(src).read_bytes() if not src.startswith("http") else httpx.get(src, timeout=20, follow_redirects=True).content
                sample = Image.open(io.BytesIO(data)).convert("RGB")
                break
            except Exception:  # noqa: BLE001
                pass
    if sample is None:  # canal sem banner: usa uma imagem real do nicho
        try:
            from . import visuals
            for c_ in visuals.find_candidates(ch.niche or ch.name, "", limit=4):
                f = visuals.download(c_["url"])
                if f:
                    sample = Image.open(f).convert("RGB")
                    break
        except Exception as e:  # noqa: BLE001
            log.info("prévia: %s", e)
    if sample is None:
        sample = Image.new("RGB", (1200, 800), (90, 90, 90))
    hook = f"Você sabia disso sobre {ch.niche or ch.name}?"
    words1 = [Word(w, i * 0.3, i * 0.3 + 0.28) for i, w in enumerate(hook.split())]
    t1 = len(words1) * 0.3 + 0.3
    body = "Isso muda tudo o que você achava que sabia."
    words2 = [Word(w, t1 + i * 0.3, t1 + i * 0.3 + 0.28, hi=(i == 3)) for i, w in enumerate(body.split())]
    t2 = t1 + len(words2) * 0.3 + 1.5
    scenes = [SceneT(0, 0, t1, hook, sample, "", 0, words1),
              SceneT(1, t1, t2, body, sample, "Exemplo", 1, words2)]
    dur = t2 + 2.4
    tl = Timeline(1080, 1920, 30, dur, t2, f"{ch.name}: prévia", scenes, 2, words1 + words2,
                  np.zeros(int(dur * 30) + 2, np.float32), ch.theme or {}, "short")
    tpl = _template(ch.template or "livre", tl)
    out_dir = MEDIA_DIR / ch.slug
    out_dir.mkdir(parents=True, exist_ok=True)
    urls = []
    for name, t in (("preview_a.jpg", t1 - 0.2), ("preview_b.jpg", t1 + 1.6)):
        img = tpl.frame(t, int(t * 30))
        img.thumbnail((540, 960))
        img.save(out_dir / name, quality=88)
        urls.append(f"/media/{ch.slug}/{name}?v={int(now().timestamp())}")
    return urls


# ================================================================ tarefa: configurar canal

@handler("setup_channel")
def job_setup_channel(ctx: JobContext) -> dict:
    cid = ctx.channel_id
    with session() as s:
        ch = s.get(Channel, cid)
        first_time = ch.setup_status == "pending"
        ch.setup_status = "configuring" if first_time else ch.setup_status
        s.add(ch)
        s.commit()
    ctx.update(0.05, "Sincronizando perfil do YouTube")
    stats = sync_profile(cid)
    ctx.log(f"{stats.get('subscribers')} inscritos · {stats.get('videos')} vídeos")
    ctx.update(0.2, "Importando vídeos e métricas")
    n = import_videos(cid, ctx)
    ctx.log(f"{n} vídeos novos importados")
    with session() as s:
        drafted = bool((s.get(Channel, cid).theme or {}).get("_draft_applied"))
    if drafted and not ctx.payload.get("identity"):
        ctx.log("Identidade do assistente \"Novo canal\" já aplicada — a IA não mexe nela")
    elif first_time or ctx.payload.get("identity"):
        ctx.update(0.65, "IA criando a identidade do canal")
        with session() as s:
            locked = bool((s.get(Channel, cid).theme or {}).get("_locked_visual"))
        try:
            ai_identity(cid, "text" if locked else ctx.payload.get("parts", "all"))
            ctx.log("Identidade gerada (nicho, voz, cores, fontes, mascote, modelo)")
        except Exception as e:  # noqa: BLE001
            ctx.log(f"Falha ao gerar identidade: {e}")
    ctx.update(0.9, "Gerando prévia do visual")
    try:
        render_preview(cid)
    except Exception as e:  # noqa: BLE001
        ctx.log(f"Prévia: {e}")
    with session() as s:
        ch = s.get(Channel, cid)
        ch.setup_status = "ready"
        s.add(ch)
        s.commit()
    from . import config
    if first_time and config.get("auto_ideas_on_setup"):
        enqueue("discover_ideas", title=f"Primeiras pautas: {ch.name}", channel_id=cid, payload={"count": 8})
    return {"imported": n}


@handler("channel_identity")
def job_identity(ctx: JobContext) -> dict:
    ctx.update(0.2, "IA criando a identidade do canal")
    ai_identity(ctx.channel_id, ctx.payload.get("parts", "all"))
    ctx.update(0.85, "Gerando prévia")
    render_preview(ctx.channel_id)
    return {}


def sync_all() -> None:
    with session() as s:
        ids = [a.channel_id for a in s.exec(select(Account).where(Account.platform == "youtube")).all() if a.credentials]
    for cid in set(ids):
        enqueue("setup_channel", title="Sincronizar canal", channel_id=cid)



