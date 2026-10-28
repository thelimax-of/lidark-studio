"""Vídeos longos: SEO de busca, capítulos, miniaturas para teste A/B e Shorts tirados do longo."""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import Any

from PIL import Image
from sqlmodel import select

from . import llm
from .config import MEDIA_DIR
from .db import session
from .jobs import JobContext, enqueue, handler
from .models import Channel, Publication, Script, Video

log = logging.getLogger("lidark.longform")


# ================================================================ SEO de busca

def search_terms(topic: str, extra: list[str] | None = None, limit: int = 12) -> list[str]:
    """O que as pessoas realmente digitam no YouTube sobre o tema (autocompletar do YouTube, Brasil)."""
    from .radar import youtube_suggestions
    words = [w for w in re.sub(r"[^\wÀ-ú ]", " ", topic).split() if len(w) > 3]
    seeds = [topic] + [" ".join(words[:2]), " ".join(words[:3])] + list(extra or [])
    out: list[str] = []
    for q in dict.fromkeys(s.strip() for s in seeds if s and s.strip()):
        for s in youtube_suggestions(q.lower()):
            if s not in out:
                out.append(s)
        if len(out) >= limit:
            break
    return out[:limit]


def seo_block(ch: Channel, topic: str, extra: list[str] | None = None) -> str:
    terms = search_terms(topic, extra)
    if not terms:
        return ""
    return f"""SEO DE BUSCA (vídeo longo vive de busca no YouTube e no Google). Termos que o público REALMENTE pesquisa:
{chr(10).join('- ' + t for t in terms)}
- O TÍTULO deve conter o termo de busca mais forte e relevante (de preferência no começo), continuando chamativo e honesto.
- A primeira frase da DESCRIÇÃO repete o termo principal de forma natural; inclua 2-3 variações ao longo do texto.
- TAGS: os termos acima que tiverem relação real com o vídeo."""


# ================================================================ capítulos

def _fmt(x: float) -> str:
    x = int(x)
    return f"{x // 3600}:{x % 3600 // 60:02d}:{x % 60:02d}" if x >= 3600 else f"{x // 60}:{x % 60:02d}"


def chapters_from_scenes(scenes: list[dict[str, Any]], title: str) -> list[dict[str, Any]]:
    """Agrupa as cenas (com tempo) em 5-8 capítulos com títulos curtos. Regras do YouTube: 1º em 0:00, ≥3, ≥10s cada."""
    listing = "\n".join(f"[{i}] {_fmt(s['start'])} {s['text'][:140]}" for i, s in enumerate(scenes))
    data = llm.complete_json(f"""Vídeo do YouTube: "{title}". Abaixo, as cenas com o tempo em que começam.
Divida o vídeo em 5 a 8 CAPÍTULOS por assunto. Cada capítulo começa numa cena; o primeiro na cena 0.
Títulos de capítulo: 2 a 5 palavras, informativos e com termos que alguém buscaria (sem numeração, sem emoji).
{listing}
Responda JSON: {{"chapters": [{{"scene": 0, "title": "..."}}]}}""", temperature=0.3)
    out: list[dict[str, Any]] = []
    for c in sorted(data.get("chapters", []) if isinstance(data, dict) else [], key=lambda c: int(c.get("scene", 0))):
        i = int(c.get("scene", 0))
        if not 0 <= i < len(scenes) or not c.get("title"):
            continue
        start = 0.0 if not out else float(scenes[i]["start"])
        if out and start - out[-1]["start"] < 12:
            continue
        out.append({"start": round(start, 1), "title": str(c["title"])[:60]})
    return out if len(out) >= 3 else []


def chapters_text(chapters: list[dict[str, Any]]) -> str:
    return "Capítulos:\n" + "\n".join(f"{_fmt(c['start'])} {c['title']}" for c in chapters)


def add_chapters_to_published(video_id: int, ctx: JobContext | None = None) -> list[dict[str, Any]]:
    """Gera capítulos para um vídeo longo já publicado e atualiza a descrição dele no YouTube."""
    from .community import _account
    from .publish import _yt_client, _yt_creds
    with session() as s:
        v = s.get(Video, video_id)
        sc = s.get(Script, v.script_id)
        pub = s.exec(select(Publication).where(Publication.video_id == video_id, Publication.status == "published")).first()
    scenes = (v.assets or {}).get("scenes") or []
    chapters = (v.assets or {}).get("chapters") or chapters_from_scenes(scenes, sc.title)
    if not chapters:
        raise RuntimeError("não foi possível montar capítulos para este vídeo")
    with session() as s:
        db = s.get(Video, video_id)
        db.assets = {**(db.assets or {}), "chapters": chapters}
        s.add(db)
        s.commit()
    if ctx:
        ctx.log(chapters_text(chapters))
    if not pub or not pub.external_id:
        return chapters
    acc = _account(v.channel_id)
    yt = _yt_client(_yt_creds(acc))
    item = (yt.videos().list(part="snippet", id=pub.external_id).execute().get("items") or [None])[0]
    if not item:
        raise RuntimeError("vídeo não encontrado no YouTube")
    sn = item["snippet"]
    desc = re.sub(r"\n*Capítulos:\n(?:\d+:\d{2}(?::\d{2})? .*\n?)+", "\n", sn.get("description", "")).strip()
    parts = desc.split("\n\n", 1)  # capítulos logo depois do 1º parágrafo
    new_desc = parts[0] + "\n\n" + chapters_text(chapters) + ("\n\n" + parts[1] if len(parts) > 1 else "")
    body = {"id": pub.external_id, "snippet": {"title": sn["title"], "categoryId": sn.get("categoryId", "27"),
                                                "description": new_desc[:4900], "tags": sn.get("tags", []),
                                                "defaultLanguage": sn.get("defaultLanguage", "pt-BR")}}
    yt.videos().update(part="snippet", body=body).execute()
    if ctx:
        ctx.log("Descrição do vídeo atualizada no YouTube com os capítulos")
    return chapters


@handler("add_chapters")
def job_add_chapters(ctx: JobContext) -> dict:
    return {"chapters": add_chapters_to_published(ctx.ref_id, ctx)}


# ================================================================ miniaturas para teste A/B

def subject_box(path: Path) -> tuple[float, float, float, float] | None:
    """Caixa (normalizada) do assunto principal da foto, pela IA de visão."""
    try:
        im = Image.open(path).convert("RGB")
        im.thumbnail((768, 768))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        data = llm.vision_json("""Onde está o ASSUNTO PRINCIPAL desta imagem (pessoa, rosto, objeto ou região de destaque)?
Responda JSON com a caixa em frações da largura/altura (0 a 1): {"box": [x1, y1, x2, y2]}""", [buf.getvalue()])
        b = [float(x) for x in (data.get("box") or [])]
        if len(b) == 4 and 0 <= b[0] < b[2] <= 1 and 0 <= b[1] < b[3] <= 1 and (b[2] - b[0]) * (b[3] - b[1]) < 0.85:
            return b[0], b[1], b[2], b[3]
    except Exception as e:  # noqa: BLE001
        log.info("subject_box: %s", e)
    return None


def thumb_texts(sc: Script, n: int = 3) -> list[str]:
    base = (sc.thumbnail_text or sc.title.replace("#Shorts", "")).strip()
    try:
        data = llm.complete_json(f"""Vídeo do YouTube: "{sc.title}". Gancho: "{sc.hook}".
Crie {n} textos de MINIATURA bem diferentes entre si (2 a 4 palavras cada, em português, MAIÚSCULAS):
um de curiosidade, um com um número/dado REAL do vídeo (só se existir — nunca invente), um provocativo.
Honestos com o conteúdo. Não repita o título.
Responda JSON: {{"texts": ["...", "...", "..."]}}""", temperature=0.9)
        texts = [str(t).strip()[:40] for t in data.get("texts", []) if str(t).strip()]
    except Exception:  # noqa: BLE001
        texts = []
    out = [base] + [t for t in texts if t.upper() != base.upper()]
    return out[:n] if len(out) >= n else (out + [base] * n)[:n]


def make_ab_thumbnails(video_id: int, ctx: JobContext | None = None) -> list[str]:
    """3 miniaturas diferentes (foto, texto, layout, destaque) para o 'Testar e comparar' do YouTube Studio."""
    from .render.thumbnail import make_thumbnail
    with session() as s:
        v = s.get(Video, video_id)
        sc = s.get(Script, v.script_id)
        ch = s.get(Channel, v.channel_id)
    vertical = v.format == "short"
    bgs = _thumb_backgrounds(v, sc, 2)
    if not bgs:
        raise RuntimeError("o vídeo não tem fotos reais para montar miniaturas")
    texts = thumb_texts(sc)
    folder = MEDIA_DIR / ch.slug / f"video_{video_id}"
    out = []
    # A = miniatura original do vídeo (o controle do teste)
    if v.thumbnail_path and (MEDIA_DIR / v.thumbnail_path).exists():
        a = folder / "thumb_a.jpg"
        a.write_bytes((MEDIA_DIR / v.thumbnail_path).read_bytes())
        out.append(str(a.relative_to(MEDIA_DIR)))
        if ctx:
            ctx.log(f"Miniatura A: a original (“{(sc.thumbnail_text or sc.title)[:40]}”)")
    for i, bg_path in enumerate(bgs[:3 - len(out)]):
        k = len(out)
        box = subject_box(bg_path)
        # sem saber onde está o assunto, o mascote fica de fora (para não cobrir o principal)
        variant = [3, 6][i % 2] if box else 4 + (i % 2) * 5
        p = make_thumbnail(Image.open(bg_path).convert("RGB"), texts[k], ch.theme or {}, folder / f"thumb_{'abc'[k]}.jpg",
                           vertical, variant=variant, subject=box, ring=bool(box))
        out.append(str(p.relative_to(MEDIA_DIR)))
        if ctx:
            ctx.log(f"Miniatura {'ABC'[k]}: “{texts[k]}”" + (" + destaque no assunto" if box else " (IA de visão indisponível: sem destaque)"))
    with session() as s:
        db = s.get(Video, video_id)
        db.assets = {**(db.assets or {}), "thumbs_ab": out}
        s.add(db)
        s.commit()
    return out


def _thumb_backgrounds(v: Video, sc: Script, n: int) -> list[Path]:
    """Fotos do vídeo que melhor representam o TEMA (não a cena): a IA escolhe pelos rótulos das imagens."""
    picks, seen = [], set()
    for p in ((v.assets or {}).get("images") or []):
        if p and p.get("path") and Path(p["path"]).exists() and p.get("url") not in seen and int(p.get("score") or 0) >= 60:
            seen.add(p.get("url"))
            picks.append(p)
    if not picks:
        return []
    listing = "\n".join(f"[{i}] {p.get('label', '')} — {p.get('reason', '')[:100]}" for i, p in enumerate(picks[:40]))
    try:
        data = llm.complete_json(f"""Vídeo: "{sc.title}" (tema: {sc.hook[:150]}).
Quais fotos abaixo dariam a MINIATURA mais clicável e fiel ao tema? Prefira imagens que mostram o assunto central
(o fenômeno, o lugar, a pessoa principal), fortes e legíveis em tamanho pequeno. Evite imagens secundárias.
{listing}
Responda JSON: {{"best": [índices na ordem de preferência]}}""", temperature=0.2)
        order = [i for i in data.get("best", []) if isinstance(i, int) and 0 <= i < len(picks)]
    except Exception:  # noqa: BLE001
        order = []
    order += [i for i in sorted(range(len(picks)), key=lambda i: -int(picks[i].get("score") or 0)) if i not in order]
    return [Path(picks[i]["path"]) for i in order[:n]]


@handler("thumb_variants")
def job_thumb_variants(ctx: JobContext) -> dict:
    return {"thumbs": make_ab_thumbnails(ctx.ref_id, ctx)}


# ================================================================ Shorts tirados do vídeo longo

def shorts_from_long(video_id: int, ctx: JobContext | None = None, count: int = 3) -> list[int]:
    """Escolhe 2-3 trechos autossuficientes do longo e escreve um Short novo para cada (que leva ao vídeo completo)."""
    from . import content, variety
    from .content import channel_brief
    with session() as s:
        v = s.get(Video, video_id)
        sc = s.get(Script, v.script_id)
        ch = s.get(Channel, v.channel_id)
        pub = s.exec(select(Publication).where(Publication.video_id == video_id, Publication.status == "published")).first()
    body = "\n".join(f"[{i}] {x.get('text', '')}" for i, x in enumerate(sc.scenes))
    words = content.target_words(ch, "short")  # Short enxuto (~45s, ou a duração fixada no canal)
    data = llm.complete_json(f"""{channel_brief(ch)}

VÍDEO LONGO: "{sc.title}"
ROTEIRO (cenas numeradas):
{body}

Escolha os {count} momentos MAIS fortes e autossuficientes deste vídeo (cada um entendível sozinho) e escreva um
SHORT vertical NOVO para cada (não copie frases; reescreva para o formato curto):
- {words - 10} a {words + 10} palavras de narração (Short enxuto, sem enrolação), 7 a 10 cenas, gancho forte na 1ª frase.
- Só fatos que estão no roteiro do longo. Anos e números em algarismos.
- Termine convidando para o vídeo completo no canal (ex.: "a história completa está no vídeo longo do canal") e com um
  pedido curto para seguir — essa é a última frase.
- Cada cena com "visual": {{"kind": "real", "query": "busca curta em inglês", "query_pt": "em português"}}, "emphasis": [1-2 palavras], "label".
Responda JSON: {{"shorts": [{{"title": "título do Short (máx 70)", "hook": "1ª frase", "scenes": [{{"text": "...", "visual": {{...}}, "emphasis": ["..."], "label": "..."}}],
  "description": "2 frases", "tags": ["..."], "hashtags": ["#..."], "thumbnail_text": "2-4 palavras"}}]}}""", temperature=0.8)
    created = []
    for it in (data.get("shorts", []) if isinstance(data, dict) else [])[:count]:
        scenes = content.clean_ending([x for x in it.get("scenes", []) if isinstance(x, dict) and x.get("text")], ch.cta)
        if len(scenes) < 5:
            continue
        plan = variety.plan(ch, "short")
        plan.update({"from_long": pub.url if pub else "", "from_long_video": video_id,
                     "series": (sc.variety or {}).get("series") or plan.get("series")})
        with session() as s:
            new = Script(channel_id=ch.id, idea_id=sc.idea_id, format="short", title=str(it.get("title", sc.title))[:200],
                         hook=it.get("hook", scenes[0]["text"]), scenes=scenes, description=it.get("description", ""),
                         tags=it.get("tags", []), hashtags=it.get("hashtags", []), thumbnail_text=it.get("thumbnail_text", ""),
                         sources=sc.sources, variety=plan, status="approved")
            s.add(new)
            s.commit()
            s.refresh(new)
        created.append(new.id)
        enqueue("render_video", title=f"Vídeo (do longo): {new.title}", channel_id=ch.id, ref_id=new.id)
        if ctx:
            ctx.log(f"Short criado a partir do longo: {new.title}")
    return created


@handler("shorts_from_long")
def job_shorts_from_long(ctx: JobContext) -> dict:
    return {"scripts": shorts_from_long(ctx.ref_id, ctx)}
