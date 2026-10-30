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
    return f"""SEO DE BUSCA (vídeo longo vive de busca e de "vídeos sugeridos"). Termos que o público REALMENTE pesquisa
(autocompletar do YouTube Brasil):
{chr(10).join('- ' + t for t in terms)}
- TÍTULO: o termo de busca mais forte e relevante nas primeiras palavras + uma lacuna de curiosidade honesta
  (ex.: "<termo>: o detalhe que ninguém te contou" — com palavras próprias). Máximo 60 caracteres.
- DESCRIÇÃO: a 1ª frase usa o termo principal de forma natural e diz o que a pessoa vai entender; depois 2-3 variações
  dos termos acima ao longo do texto (frases de verdade, nunca lista de palavras).
- Os títulos de CAPÍTULO também devem usar termos que alguém buscaria.
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
Títulos de capítulo: 2 a 5 palavras, com termos que alguém buscaria E que despertam curiosidade pelo trecho
(ex.: "O erro de Napoleão", não "Parte 2"); sem numeração, sem emoji, sem entregar a revelação do capítulo.
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
    # o roteirista já propôs alternativas no mesmo pedido do roteiro: usa sem gastar cota
    texts = [str(t).strip()[:40] for t in ((sc.variety or {}).get("thumb_options") or [])
             if str(t).strip() and 1 <= len(str(t).split()) <= 5]
    if len({t.upper() for t in texts} - {base.upper()}) < n - 1:
        from .content import THUMB_RULES, _learning
        guide = _learning(sc.channel_id, "thumbnail")
        try:
            data = llm.complete_json(f"""Vídeo do YouTube: "{sc.title}". Gancho: "{sc.hook}".
{('APRENDIZADO COM OS DADOS DO CANAL:' + chr(10) + guide) if guide else ''}
{THUMB_RULES}
Crie {n} textos de MINIATURA bem diferentes entre si (2 a 4 palavras cada, em português, MAIÚSCULAS), para um teste A/B:
um de curiosidade (lacuna), um com um número/dado REAL do vídeo (só se existir — nunca invente), um de emoção/contraste.
Honestos com o conteúdo. Não repita as palavras do título.
Responda JSON: {{"texts": ["...", "...", "..."]}}""", temperature=0.9, required=("texts",))
            texts += [str(t).strip()[:40] for t in data.get("texts", []) if str(t).strip()]
        except Exception:  # noqa: BLE001
            pass
    texts = list(dict.fromkeys(t.upper() for t in texts))
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
    from .content import HOOK_RULES, RETENTION_SHORT, THUMB_RULES, TITLE_RULES, TTS_RULES, channel_brief
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

Escolha os {count} momentos MAIS fortes e autossuficientes deste vídeo (cada um entendível sozinho: uma revelação,
uma virada, um número chocante, um personagem) e escreva um SHORT vertical NOVO para cada (não copie frases;
reescreva para o formato curto). Os {count} Shorts precisam ser diferentes entre si: aberturas com truques diferentes
(pergunta específica, número, cena no presente, afirmação contraintuitiva, consequência antes da causa).
- {words - 10} a {words + 10} palavras de narração (Short enxuto, sem enrolação), 7 a 10 cenas.
{HOOK_RULES}
{RETENTION_SHORT}
{TTS_RULES}
- Só fatos que estão no roteiro do longo.
- Termine convidando para o vídeo completo no canal (ex.: "a história completa está no vídeo longo do canal") e com um
  pedido curto para seguir — essa é a última frase. Antes dele, NÃO entregue tudo: deixe uma pergunta que o longo responde.
- Cada cena com "visual": {{"kind": "real", "query": "busca curta em inglês", "query_pt": "em português"}}, "emphasis": [1-2 palavras], "label".
{TITLE_RULES}
{THUMB_RULES}
Responda JSON: {{"shorts": [{{"title": "título do Short (35-50 caracteres)", "hook": "1ª frase", "scenes": [{{"text": "...", "visual": {{...}}, "emphasis": ["..."], "label": "..."}}],
  "description": "2 frases (a 1ª com o termo que alguém buscaria)", "tags": ["..."], "hashtags": ["#..."], "thumbnail_text": "2-4 palavras"}}]}}""",
                             temperature=0.8, required=("shorts",))
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


# ================================================================ Short campeão → vídeo longo
# Para o YPP o caminho realista é o de HORAS ASSISTIDAS (4.000 h em 12 meses; 8.000 h para quem se inscrever a partir
# de 01/02/2027) — e minutos de Shorts não contam. O Short vira funil: o tema que provou que prende o público ganha
# um vídeo longo de 8-12 min, aprofundado com fontes (fatos novos, não enchimento).

CHAMPION_MIN_HOURS = 24  # antes disso as views ainda estão subindo e o Analytics nem chegou
_W = {"reach": 0.40, "retention": 0.30, "interaction": 0.15, "subs": 0.10, "engaged": 0.05}


def _median(xs: list[float]) -> float:
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return 0.0
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def _vs_median(x: float, ref: float) -> float:
    """0-100: 50 = igual à mediana do canal, +25 a cada vez que dobra (−25 a cada metade)."""
    import math
    if ref <= 0:
        return 50.0
    return max(0.0, min(100.0, 50 + 25 * math.log2(max(x, ref / 16) / ref)))


def _short_candidates(channel_id: int) -> list[dict[str, Any]]:
    """Shorts publicados do canal com métricas (da tabela de desempenho) + dados para ligar o longo a eles."""
    from datetime import datetime, timezone
    from .analytics import latest_metrics, performance_table
    rows = performance_table(channel_id)
    metrics = latest_metrics(channel_id)
    out = []
    with session() as s:
        pubs = s.exec(select(Publication).where(Publication.channel_id == channel_id, Publication.status == "published")).all()
        subs: dict = {}
        ext: dict = {}
        for p in pubs:
            key = p.video_id if p.video_id else f"ext:{p.external_id or p.id}"
            m = metrics.get(p.id)
            subs[key] = subs.get(key, 0) + ((m.subscribers_gained or 0) if m else 0)
            if p.platform == "youtube" and p.external_id:
                ext[key] = p
        for r in rows:
            key = r["video_id"]
            v = s.get(Video, key) if isinstance(key, int) else None
            sc = s.get(Script, v.script_id) if v else None
            if v:
                if v.format != "short" or (sc and (sc.variety or {}).get("from_long")):
                    continue  # Short tirado de um longo: o tema já tem vídeo longo
            elif not ("/shorts/" in (r.get("url") or "") or 0 < (r.get("duration") or 0) <= 180):
                continue
            pub = ext.get(key)
            age_h = 0.0
            if r.get("published_at"):
                dt = datetime.fromisoformat(r["published_at"])
                age_h = (datetime.now(timezone.utc) - (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc))).total_seconds() / 3600
            out.append({**r, "key": str(key), "age_hours": round(age_h, 1), "subs": subs.get(key, 0),
                        "external_id": pub.external_id if pub else "", "publication_id": pub.id if pub else None,
                        "script_id": sc.id if sc else None,
                        "text": sc.full_text if sc else (pub.description if pub else "")})
    return out


def champions(channel_id: int, limit: int = 6) -> list[dict[str, Any]]:
    """Shorts campeões do canal: alcance (views/dia, relativo à mediana), retenção, views engajadas, interação e inscritos.

    Cada item traz a nota 0-100, os motivos em português, a confiança dos dados e se já virou vídeo longo."""
    import math
    cands = _short_candidates(channel_id)
    if not cands:
        return []
    for c in cands:
        days = max(1.0, c["age_hours"] / 24)
        c["_vel"] = c["views"] / math.sqrt(days)  # amortecido: Shorts ganham quase tudo nos 2 primeiros dias
        c["_int"] = (c["likes"] + 2 * c["comments"] + 3 * c["shares"]) / max(1, c["views"])
        c["_subs"] = 1000 * c["subs"] / max(1, c["views"])
    med = {k: _median([c[k] for c in cands]) for k in ("_vel", "_int", "_subs", "views")}
    eng = [c for c in cands if c.get("engaged_views") is not None and c["views"]]
    med_eng = _median([c["engaged_views"] / c["views"] for c in eng])
    status = _champion_status(channel_id)
    out = []
    for c in cands:
        # alcance: views totais e ritmo (views/√dias) contra a mediana dos Shorts do canal
        parts: dict[str, float] = {"reach": (_vs_median(c["views"], med["views"]) + _vs_median(c["_vel"], med["_vel"])) / 2}
        why = []
        if med["views"] and c["views"] >= 1.3 * med["views"]:
            why.append(f"{c['views'] / med['views']:.1f}× as views da mediana dos Shorts do canal")
        if c["retention"] > 0:  # % média assistida (Shorts passam de 100% quando o público assiste de novo)
            parts["retention"] = max(0.0, min(100.0, (c["retention"] - 40) * 1.25))  # 80% → 50 · 120% → 100
            if c["retention"] >= 75:
                why.append(f"retenção média de {c['retention']:.0f}%" + (" (assistem de novo)" if c["retention"] > 100 else ""))
        if c["views"] >= 30:
            parts["interaction"] = _vs_median(c["_int"], med["_int"])
            if med["_int"] and c["_int"] >= 1.5 * med["_int"]:
                why.append(f"engajamento {c['_int'] / med['_int']:.1f}× acima da mediana")
        if c in eng and len(eng) >= 2:  # views engajadas chegam com ~2 dias de atraso: só compara entre os que têm
            parts["engaged"] = _vs_median(c["engaged_views"] / c["views"], med_eng)
        if c["subs"] > 0:
            parts["subs"] = _vs_median(c["_subs"], med["_subs"] or c["_subs"] / 2)
            why.append(f"+{c['subs']} inscritos")
        missing_ret = "retention" not in parts
        if missing_ret:  # Analytics ainda não chegou (~2 dias): retenção neutra, para não premiar quem não tem dado
            parts["retention"] = 50.0
        wsum = sum(_W[k] for k in parts)
        score = round(sum(parts[k] * _W[k] for k in parts) / wsum)
        conf = "alta" if not missing_ret and c["views"] >= 300 else "média" if c["views"] >= 100 else "baixa"
        early = c["age_hours"] < CHAMPION_MIN_HOURS
        st = status.get(c["key"]) or {}
        out.append({
            "key": c["key"], "channel_id": channel_id, "title": c["title"].replace("#Shorts", "").replace("#shorts", "").strip(),
            "url": c.get("url"), "thumbnail": c.get("thumbnail"), "published_at": c.get("published_at"),
            "views": c["views"], "engaged_views": c.get("engaged_views"), "retention": round(c["retention"], 1),
            "likes": c["likes"], "comments": c["comments"], "shares": c["shares"], "subs": c["subs"],
            "score": score, "parts": {k: round(v) for k, v in parts.items() if not (k == "retention" and missing_ret)},
            "reasons": why, "confidence": conf,
            "early": early, "champion": score >= 55 and c["views"] >= max(100, med["views"]) and not early,
            "age_hours": c["age_hours"], **st,
        })
    out.sort(key=lambda x: (-x["champion"], -x["score"]))
    return out[:limit]


def champions_all(limit: int = 4) -> list[dict[str, Any]]:
    from .models import Channel as _Ch
    with session() as s:
        chans = s.exec(select(_Ch).order_by(_Ch.id)).all()
    out = []
    for ch in chans:
        out += [{**c, "channel_name": ch.name} for c in champions(ch.id, limit)]
    out.sort(key=lambda x: (-x["champion"], -x["score"]))
    return out


def _champion_status(channel_id: int) -> dict[str, dict[str, Any]]:
    """Shorts que já viraram (ou estão virando) vídeo longo: pauta → roteiro → vídeo."""
    from .models import Idea, Job
    out: dict[str, dict[str, Any]] = {}
    with session() as s:
        for j in s.exec(select(Job).where(Job.kind == "champion_long", Job.channel_id == channel_id,
                                          Job.status.in_(("queued", "running")))).all():
            out[str((j.payload or {}).get("key"))] = {"long_status": "working", "job_id": j.id}
        for idea in s.exec(select(Idea).where(Idea.channel_id == channel_id, Idea.format == "long")).all():
            key = next((t.split(":", 1)[1] for t in (idea.tags or []) if str(t).startswith("campeao:")), None)
            if not key or (key in out and idea.status in ("discarded", "rejected")):
                continue
            sc = s.exec(select(Script).where(Script.idea_id == idea.id).order_by(Script.id.desc())).first()
            v = s.exec(select(Video).where(Video.script_id == sc.id).order_by(Video.id.desc())).first() if sc else None
            st = ("discarded" if idea.status in ("discarded", "rejected") else "published" if v and v.status == "published"
                  else "video" if v else "script" if sc else "idea")
            if out.get(key, {}).get("long_status") == "working" and st in ("idea", "discarded"):
                continue
            out[key] = {"long_status": st, "idea_id": idea.id, "long_title": idea.title,
                        "script_id": sc.id if sc else None, "long_video_id": v.id if v else None}
    return out


def propose_long(channel_id: int, key: str, ctx: JobContext | None = None) -> dict[str, Any]:
    """Proposta de vídeo longo (8-12 min, em capítulos) que aprofunda o tema do Short campeão com fontes reais.

    Devolve {"viable": False, "reason"} quando as fontes não sustentam 8 min sem enchimento."""
    from . import content
    from .models import Channel as _Ch, Idea
    with session() as s:
        ch = s.get(_Ch, channel_id)
        long_titles = [i.title for i in s.exec(select(Idea).where(Idea.channel_id == channel_id, Idea.format == "long",
                                                                   Idea.status != "discarded")).all()]
    champ = next((c for c in _short_candidates(channel_id) if c["key"] == str(key)), None)
    if not champ:
        raise RuntimeError("Short não encontrado entre os publicados do canal")
    topic = champ["title"].replace("#Shorts", "").replace("#shorts", "").strip()
    if ctx:
        ctx.update(0.1, "Pesquisando fontes para aprofundar o tema")
    srcs = _research(ch, topic, champ.get("text") or "")
    if len(srcs) < 2:
        return {"viable": False, "reason": "fontes insuficientes para um vídeo longo sobre este tema", "short": topic}
    material = "\n\n".join(f"[{i + 1}] {x['title']} ({x['url']})\n{x['text'][:3500]}" for i, x in enumerate(srcs))
    perf = (f"{champ['views']} views" + (f", retenção {champ['retention']:.0f}%" if champ["retention"] else "")
            + (f", {champ['engaged_views']} views engajadas" if champ.get("engaged_views") is not None else ""))
    if ctx:
        ctx.update(0.4, "Planejando os capítulos do vídeo longo")
    guide = content._learning(channel_id, "ideas")
    data = llm.complete_json(f"""{content.channel_brief(ch)}
{(chr(10) + 'APRENDIZADO COM OS DADOS DO CANAL:' + chr(10) + guide + chr(10)) if guide else ''}
SHORT CAMPEÃO DO CANAL: "{topic}" ({perf}) — o público provou que quer este assunto.
NARRAÇÃO DO SHORT: {champ.get('text', '')[:1500] or '(indisponível)'}

FONTES DE PESQUISA:
{material}

VÍDEOS LONGOS JÁ PLANEJADOS NO CANAL (não repita):
{chr(10).join('- ' + t for t in long_titles[-40:]) or '(nenhum)'}

Planeje um VÍDEO LONGO (8 a 12 minutos, horizontal) que APROFUNDA o tema do Short para quem quer saber mais.
Regras:
- Algumas fontes podem ser de OUTRO assunto (homônimos, temas vizinhos, misticismo): liste em "relevant_sources" só as
  que tratam DIRETAMENTE do tema e são confiáveis, e use SOMENTE elas.
- Profundidade REAL: contexto, causas, personagens, desdobramentos, consequências e o que o Short não teve tempo de contar.
  Cada capítulo precisa de fatos ESPECÍFICOS das fontes acima (datas, nomes, números) — indique os números das fontes.
- Proibido enchimento: nada de repetir o Short, resumos redundantes, "curiosidades" genéricas ou especulação.
- Se as fontes NÃO sustentam pelo menos 8 minutos de conteúdo novo e verificável, responda "viable": false e explique.
- A duração ("minutes", 8 a 12) é proporcional ao material que existe de verdade.
- Título pensado para BUSCA (o termo que as pessoas pesquisam logo no começo) + lacuna de curiosidade honesta; máx 60
  caracteres. O longo não pode parecer repeteco do Short: prometa a parte da história que o Short não contou.
- 6 a 9 capítulos; o primeiro é um COLD OPEN com o momento mais intrigante (pode partir da pergunta que o Short deixou
  no ar). Cada capítulo abre com uma pergunta e termina com uma revelação + gancho para o próximo; o maior payoff fica
  para o último capítulo. Planeje re-ganchos fortes por volta de 1/3 e 2/3 do vídeo.
- "hook": a 1ª frase do vídeo, até 14 palavras, começando no conflito/no número/na cena (nunca "olá" ou "neste vídeo").
Responda JSON: {{"viable": true, "reason": "por que o tema rende (ou não) um vídeo longo", "relevant_sources": [1, 2, 3],
  "title": "...", "angle": "o fio condutor / a grande pergunta do vídeo", "summary": "resumo factual em 3-4 frases",
  "minutes": 10, "hook": "primeira frase do vídeo",
  "chapters": [{{"title": "2-5 palavras", "beats": "o que este capítulo mostra, com os fatos específicos", "sources": [1, 2]}}],
  "open_questions": ["perguntas que o Short levantou e o longo responde"], "search_terms": ["termos de busca"]}}""",
                             temperature=0.5)
    if not isinstance(data, dict):
        raise RuntimeError("a IA não devolveu uma proposta")
    ok = {i for i in (data.get("relevant_sources") or []) if isinstance(i, int)} or set(range(1, len(srcs) + 1))
    chapters = []
    for c in data.get("chapters") or []:
        idx = [i for i in (c.get("sources") or []) if isinstance(i, int) and 1 <= i <= len(srcs) and i in ok]
        if c.get("title") and c.get("beats") and idx:  # capítulo sem fonte = enchimento: sai
            chapters.append({"title": str(c["title"])[:60], "beats": str(c["beats"])[:600],
                             "sources": [srcs[i - 1]["url"] for i in idx]})
    out = {"short": topic, "short_key": str(key), "short_url": champ.get("url") or "", "short_ext": champ.get("external_id") or "",
           "title": str(data.get("title") or topic)[:100], "angle": str(data.get("angle") or ""),
           "summary": str(data.get("summary") or ""), "hook": str(data.get("hook") or ""), "chapters": chapters,
           "open_questions": [str(q) for q in (data.get("open_questions") or [])][:6],
           "search_terms": [str(q) for q in (data.get("search_terms") or [])][:8], "reason": str(data.get("reason") or ""),
           "sources": [{"title": x["title"], "url": x["url"]} for i, x in enumerate(srcs) if i + 1 in ok]}
    used = {u for c in chapters for u in c["sources"]}
    if not data.get("viable", True) or len(chapters) < 5 or len(used) < 3:
        return {**out, "viable": False,
                "reason": out["reason"] if not data.get("viable", True) else
                f"só {len(chapters)} capítulo(s) com fonte relevante" if len(chapters) < 5 else
                f"só {len(used)} fonte(s) relevante(s) sustentam o vídeo — pouco para 8 min sem enchimento"}
    # duração pelo material: ~1,5 min por capítulo com fonte, entre 8 e 12 min
    out["minutes"] = max(8, min(12, int(data.get("minutes") or 10), round(len(chapters) * 1.5)))
    out["viable"] = True
    return out


def _research(ch, title: str, text: str) -> list[dict[str, Any]]:
    """Fontes para o longo: o título do Short costuma ser chamariz ("Onde estão todos?") — a IA diz o nome real do assunto
    ("Paradoxo de Fermi") e 2 buscas complementares; junta tudo sem repetir."""
    from concurrent.futures import ThreadPoolExecutor
    from . import research
    queries = [title]
    try:
        data = llm.complete_json(f"""Short de um canal sobre {ch.niche}: "{title}".
Narração: {text[:900] or '(indisponível)'}
Qual é o ASSUNTO REAL do Short, com o nome pelo qual aparece em enciclopédias e livros? E quais 2 buscas trariam fontes
confiáveis para APROFUNDAR o assunto (causas, contexto, personagens, consequências)? Buscas curtas, em português.
Responda JSON: {{"topic": "...", "queries": ["...", "..."]}}""", temperature=0.2)
        queries = [str(q) for q in [data.get("topic")] + list(data.get("queries") or [])[:2] if q] or queries
    except Exception as e:  # noqa: BLE001
        log.info("assunto do Short: %s", e)
    with ThreadPoolExecutor(3) as ex:
        found = list(ex.map(lambda q: research.gather_dossier(q, max_sources=4)["sources"], queries))
    out, seen = [], set()
    for batch in zip(*[f + [None] * (8 - len(f)) for f in found]):  # intercala: a melhor fonte de cada busca primeiro
        for x in batch:
            if x and x["url"] not in seen:
                seen.add(x["url"])
                out.append(x)
    return out[:10]


def _outline_text(p: dict[str, Any]) -> str:
    return "\n".join(f"{i + 1}. {c['title']} — {c['beats']}" for i, c in enumerate(p["chapters"]))


def long_from_champion(channel_id: int, key: str, ctx: JobContext | None = None) -> dict[str, Any]:
    """Short campeão → pauta longa checada e com nota → roteiro longo em capítulos (você revisa antes de renderizar)."""
    from .models import Channel as _Ch, Idea
    from .pipeline import _apply_check, _enforce_facts, _score
    from . import content
    p = propose_long(channel_id, key, ctx)
    if not p.get("viable"):
        raise RuntimeError(f"Tema sem profundidade para 8+ min: {p.get('reason')}")
    if ctx:
        ctx.log(f"Proposta: “{p['title']}” · {p['minutes']} min · {len(p['chapters'])} capítulos\n{_outline_text(p)}")
    with session() as s:
        ch = s.get(_Ch, channel_id)
        idea = Idea(channel_id=channel_id, title=p["title"], format="long", origin="champion",
                    angle=f"{p['angle']}\n\nCAPÍTULOS PLANEJADOS:\n{_outline_text(p)}", summary=p["summary"],
                    sources=p["sources"], status="approved",
                    tags=[f"campeao:{key}", f"de_short:{p['short']}"[:120]])
        s.add(idea)
        s.commit()
        s.refresh(idea)
    if ctx:
        ctx.update(0.6, "Checando os fatos da pauta")
    r = content.verify_idea(ch, idea)
    with session() as s:
        db = s.get(Idea, idea.id)
        _apply_check(db, r)
        s.add(db)
        s.commit()
    if _enforce_facts(idea.id, ctx):
        raise RuntimeError("as fontes não confirmaram a premissa do vídeo longo — pauta descartada")
    _score(ch, idea.id, ctx)
    extra = f"""VÍDEO LONGO NASCIDO DE UM SHORT CAMPEÃO ("{p['short']}"): o público já provou interesse; agora entregue PROFUNDIDADE.
Siga estes capítulos (cada um com os fatos indicados, confirmados nas fontes — nada de enchimento ou repetição):
{_outline_text(p)}
Perguntas que o vídeo precisa responder: {'; '.join(p['open_questions']) or '(as do tema)'}
Gancho sugerido: {p['hook']}
Ritmo de vídeo longo: no fim de cada capítulo, deixe uma pergunta que o capítulo seguinte responde (segura o público);
nos primeiros 30 s confirme o tema do Short e prometa o que ele não contou (quem veio do Short precisa sentir que vale ficar).
O vídeo termina com uma TELA FINAL de 20 s: o CTA convida a assistir o próximo vídeo que aparece na tela e a se inscrever."""
    j = enqueue("write_script", title=f"Roteiro longo (Short campeão): {p['title']}", channel_id=channel_id, ref_id=idea.id,
                payload={"format": "long", "extra": extra,
                         "plan_extra": {"seconds": p["minutes"] * 60, "from_short": p["short_url"],
                                        "from_short_ext": p["short_ext"], "from_short_title": p["short"]}})
    if ctx:
        ctx.log(f"Roteiro longo na fila (tarefa #{j.id}) — revise em Roteiros antes de gerar o vídeo")
    return {"idea_id": idea.id, "write_job": j.id, "title": p["title"], "minutes": p["minutes"], "chapters": p["chapters"]}


@handler("champion_long")
def job_champion_long(ctx: JobContext) -> dict:
    return long_from_champion(ctx.channel_id, str(ctx.payload.get("key")), ctx)


# ================================================================ séries: maratona entre episódios

def series_episodes(channel_id: int, series: str) -> list[Publication]:
    """Vídeos LONGOS publicados da série, do mais antigo para o mais novo."""
    if not series:
        return []
    out = []
    with session() as s:
        for p in s.exec(select(Publication).where(Publication.channel_id == channel_id, Publication.platform == "youtube",
                                                  Publication.status == "published")).all():
            v = s.get(Video, p.video_id) if p.video_id else None
            sc = s.get(Script, v.script_id) if v else None
            if v and v.format == "long" and sc and (sc.variety or {}).get("series") == series and p.url:
                out.append(p)
    return sorted(out, key=_when)


def _when(p: Publication):
    return (p.published_at or p.created_at).replace(tzinfo=None)


def playlist_url(channel_id: int, series: str) -> str:
    from .models import Channel as _Ch
    with session() as s:
        pid = ((s.get(_Ch, channel_id).playlists or {}).get(series)) if series else None
    return f"https://www.youtube.com/playlist?list={pid}" if pid else ""


def series_block(sc: Script, video: Video) -> str:
    """Linhas de maratona na descrição de um vídeo longo: episódio anterior + playlist da série (+ o Short de origem)."""
    if video.format != "long":
        return ""
    var = sc.variety or {}
    series, lines = var.get("series") or "", []
    if series:
        prev = [p for p in series_episodes(sc.channel_id, series) if p.video_id != video.id]
        if prev:
            lines.append(f"◀ Episódio anterior: {prev[-1].title.strip()} → {prev[-1].url}")
        pl = playlist_url(sc.channel_id, series)
        if pl:
            lines.append(f"▶ Maratone a série “{series}”: {pl}")
    if var.get("from_short"):
        lines.append(f"⚡ A versão de 1 minuto (Short): {var['from_short']}")
    return "\n".join(lines)


_NEXT_RE = re.compile(r"^▶ Próximo episódio:.*$\n?", re.M)
_PL_RE = re.compile(r"^▶ Maratone a série.*$", re.M)
_FULL_RE = re.compile(r"^▶ Vídeo completo:.*$\n?", re.M)


def _insert_after_first(desc: str, line: str) -> str:
    parts = desc.strip().split("\n\n", 1)
    return parts[0] + "\n\n" + line + ("\n\n" + parts[1] if len(parts) > 1 else "")


def _update_desc(yt, video_ext: str, fn) -> bool:
    item = (yt.videos().list(part="snippet", id=video_ext).execute().get("items") or [None])[0]
    if not item:
        return False
    sn = item["snippet"]
    old = sn.get("description", "")
    new = fn(old)
    if new.strip() == old.strip():
        return False
    body = {"id": video_ext, "snippet": {"title": sn["title"], "categoryId": sn.get("categoryId", "27"),
                                         "description": new[:4900], "tags": sn.get("tags", []),
                                         "defaultLanguage": sn.get("defaultLanguage", "pt-BR")}}
    yt.videos().update(part="snippet", body=body).execute()
    return True


def binge_links(pub_id: int, ctx: JobContext | None = None) -> int:
    """Depois de publicar um longo: o episódio anterior ganha "▶ Próximo episódio" na descrição, o novo ganha o link
    da playlist (se a série acabou de nascer) e o Short campeão de origem ganha "▶ Vídeo completo" no topo."""
    from .community import _account
    from .publish import _yt_client, _yt_creds
    with session() as s:
        pub = s.get(Publication, pub_id)
        video = s.get(Video, pub.video_id) if pub and pub.video_id else None
        sc = s.get(Script, video.script_id) if video else None
    if not pub or not video or not sc or video.format != "long" or not pub.external_id:
        return 0
    acc = _account(pub.channel_id)
    if not acc or not acc.credentials:
        return 0
    yt = _yt_client(_yt_creds(acc))
    log = ctx.log if ctx else (lambda m: None)
    series, title, done = (sc.variety or {}).get("series") or "", pub.title.strip(), 0
    if series:
        prev = [p for p in series_episodes(pub.channel_id, series) if p.id != pub.id and _when(p) <= _when(pub)]
        if prev and prev[-1].external_id:
            line = f"▶ Próximo episódio: {title} → {pub.url}"
            if _update_desc(yt, prev[-1].external_id, lambda d: _insert_after_first(_NEXT_RE.sub("", d), line)):
                done += 1
                log(f"Episódio anterior agora aponta para este: {prev[-1].title[:60]}")
        pl = playlist_url(pub.channel_id, series)
        if pl:  # série que nasceu agora: a playlist só existe depois do envio
            line = f"▶ Maratone a série “{series}”: {pl}"
            if _update_desc(yt, pub.external_id, lambda d: d if _PL_RE.search(d) else _insert_after_first(d, line)):
                done += 1
                log("Link da playlist da série incluído na descrição")
    src = (sc.variety or {}).get("from_short_ext")
    if src:  # o Short campeão leva ao vídeo completo ("vídeo relacionado" do Shorts só dá para escolher no Studio)
        line = f"▶ Vídeo completo: {title} → {pub.url}"
        try:
            if _update_desc(yt, src, lambda d: line + "\n\n" + _FULL_RE.sub("", d).strip()):
                done += 1
                log("Short de origem agora leva ao vídeo completo (descrição)")
        except Exception as e:  # noqa: BLE001 — Short importado de outra conta etc.
            log(f"Descrição do Short de origem não atualizada: {e}")
    return done


@handler("binge_links")
def job_binge_links(ctx: JobContext) -> dict:
    return {"updated": binge_links(ctx.ref_id, ctx)}
