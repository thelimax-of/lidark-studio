"""Comunidade: comentários do público (resposta sugerida pela IA, você aprova), ligação Shorts ↔ vídeos longos
e o comentário do próprio canal que puxa conversa logo após publicar."""
from __future__ import annotations

import logging
import random
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlmodel import select

from . import llm
from .db import session
from .jobs import JobContext, enqueue, handler
from .models import Account, Channel, Comment, Idea, Job, Publication, Script, Video, now

log = logging.getLogger("lidark.community")

WRITE_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"


def _account(channel_id: int) -> Account | None:
    with session() as s:
        return s.exec(select(Account).where(Account.channel_id == channel_id, Account.platform == "youtube")).first()


def can_write(acc: Account | None) -> bool:
    return bool(acc and WRITE_SCOPE in ((acc.credentials or {}).get("scopes") or []))


def _yt(acc: Account):
    from .publish import _yt_client, _yt_creds
    return _yt_client(_yt_creds(acc))


# ================================================================ comentários

def fetch_comments(ch: Channel, ctx: JobContext | None = None) -> int:
    acc = _account(ch.id)
    if not acc or not acc.credentials or not ch.youtube_id:
        return 0
    yt = _yt(acc)
    resp = yt.commentThreads().list(part="snippet,replies", allThreadsRelatedToChannelId=ch.youtube_id,
                                    maxResults=50, order="time", textFormat="plainText").execute()
    with session() as s:
        known = set(s.exec(select(Comment.yt_id).where(Comment.channel_id == ch.id)).all())
        seeds = {c.yt_id: c.id for c in s.exec(select(Comment).where(Comment.channel_id == ch.id, Comment.status == "seed")).all()}
        titles = {p.external_id: p.title for p in s.exec(select(Publication).where(Publication.channel_id == ch.id)).all()}
    new = []
    for th in resp.get("items", []):
        if th["id"] in seeds:  # comentário-semente do canal: atualiza curtidas e respostas
            _seed_stats(seeds[th["id"]], th)
            continue
        if th["id"] in known:
            continue
        top = th["snippet"]["topLevelComment"]["snippet"]
        if (top.get("authorChannelId") or {}).get("value") == ch.youtube_id:
            continue  # comentário do próprio canal
        replies = (th.get("replies") or {}).get("comments") or []
        answered = any((r["snippet"].get("authorChannelId") or {}).get("value") == ch.youtube_id for r in replies)
        vid = th["snippet"].get("videoId") or top.get("videoId") or ""
        new.append(Comment(channel_id=ch.id, yt_id=th["id"], video_id=vid, video_title=titles.get(vid, ""),
                           author=top.get("authorDisplayName", ""), author_avatar=top.get("authorProfileImageUrl", ""),
                           text=top.get("textDisplay") or top.get("textOriginal", ""), likes=int(top.get("likeCount") or 0),
                           published_at=_dt(top.get("publishedAt")), status="replied" if answered else "new"))
    if new:
        with session() as s:
            for c in new:
                s.add(c)
            s.commit()
        try:
            suggest_replies(ch, ctx)
        except Exception as e:  # noqa: BLE001
            log.warning("sugestão de resposta (%s): %s", ch.name, e)
        try:  # perguntas do público viram pautas ("respondendo @fulano")
            ideas_from_comments(ch, ctx)
        except Exception as e:  # noqa: BLE001
            log.warning("pautas de comentários (%s): %s", ch.name, e)
    if ctx:
        ctx.log(f"{len(new)} comentário(s) novo(s)")
    waiting = [c for c in new if c.status == "new"]
    if waiting:
        from . import notify
        notify.safe(f"💬 {len(waiting)} comentário(s) novo(s) · {ch.name}",
                    "\n".join(f"{c.author}: {c.text[:90]}" for c in waiting[:4]), event="comments", tags=["speech_balloon"])
    return len(new)


def _seed_stats(comment_id: int, th: dict) -> None:
    top = th["snippet"]["topLevelComment"]["snippet"]
    with session() as s:
        c = s.get(Comment, comment_id)
        c.likes, c.replies = int(top.get("likeCount") or 0), int(th["snippet"].get("totalReplyCount") or 0)
        s.add(c)
        s.commit()


def _dt(iso: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def suggest_replies(ch: Channel, ctx: JobContext | None = None, only: int | None = None) -> None:
    with session() as s:
        q = select(Comment).where(Comment.channel_id == ch.id, Comment.status == "new", Comment.suggestion == "")
        if only:
            q = q.where(Comment.id == only)
        pending = s.exec(q.limit(20)).all()
    if not pending:
        return
    from .content import channel_brief
    listing = "\n".join(f"[{i}] (vídeo: {c.video_title or c.video_id}) {c.author}: {c.text[:500]}" for i, c in enumerate(pending))
    data = llm.complete_json(f"""{channel_brief(ch)}

Você cuida dos comentários do canal. Para cada comentário abaixo, classifique e escreva uma resposta na voz do canal.
REGRAS da resposta: curta (até 220 caracteres), calorosa e natural, em português do Brasil; responda perguntas com fatos
corretos (se não tiver certeza, diga que vai pesquisar); agradeça correções com humildade; quando fizer sentido, puxe a
conversa com um fato extra curto ou uma pergunta específica (respostas viram mais comentários, e comentários ajudam o
vídeo a ser recomendado); se o comentário sugerir um tema, diga que anotou (sem prometer data); NUNCA invente fatos,
nunca peça inscrição em toda resposta, sem links, no máximo 1 emoji; varie as aberturas (não comece todas com "Valeu").
Spam, golpe, ofensa ou propaganda → kind "spam" e resposta vazia.

COMENTÁRIOS:
{listing}

Responda JSON: {{"items": [{{"i": 0, "kind": "pergunta|elogio|correcao|sugestao|critica|spam|outro", "reply": "..."}}]}}""",
                             temperature=0.6)
    data = getattr(data, "data", data)
    by_i = {int(x.get("i", -1)): x for x in (data.get("items", []) if isinstance(data, dict) else [])}
    with session() as s:
        for i, c in enumerate(pending):
            x = by_i.get(i)
            if not x:
                continue
            db = s.get(Comment, c.id)
            db.kind = str(x.get("kind", "outro"))[:20]
            db.suggestion = str(x.get("reply", ""))[:500]
            if db.kind == "spam":
                db.status = "ignored"
            s.add(db)
        s.commit()


# ================================================================ perguntas do público → pautas

COMMENT_IDEAS_PER_DAY = 2  # por canal: o público inspira, mas não toma conta da fila


def _seen_file():
    from .config import CACHE_DIR
    return CACHE_DIR / "comment_ideas_seen.json"


def _seen() -> set[str]:
    import json
    try:
        return set(json.loads(_seen_file().read_text(encoding="utf-8")))
    except Exception:  # noqa: BLE001
        return set()


def _mark_seen(ids: set[str]) -> None:
    import json
    keep = sorted(_seen() | ids)[-5000:]
    try:
        _seen_file().write_text(json.dumps(keep), encoding="utf-8")
    except OSError:
        pass


def handle_of(author: str) -> str:
    a = " ".join((author or "").split()).strip()
    return a if a.startswith("@") else ("@" + a if a else "um espectador")


def ideas_from_comments(ch: Channel, ctx: JobContext | None = None) -> list[int]:
    """Perguntas reais do público viram pautas (origem "comment", ângulo "respondendo @fulano"): limite diário,
    sem repetir comentário nem tema já existente. Cada pauta ainda passa pela checagem de fatos e pela nota."""
    from .content import channel_brief, existing_titles
    from .variety import _jaccard, _tokens
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    with session() as s:
        mine = s.exec(select(Idea).where(Idea.channel_id == ch.id, Idea.origin == "comment")).all()
        cands = s.exec(select(Comment).where(Comment.channel_id == ch.id, Comment.kind == "pergunta",
                                             Comment.status.in_(["new", "replied"]))
                       .order_by(Comment.created_at.desc()).limit(60)).all()
    done_today = sum(1 for i in mine if i.created_at and (i.created_at if i.created_at.tzinfo
                                                         else i.created_at.replace(tzinfo=timezone.utc)) >= start)
    left = COMMENT_IDEAS_PER_DAY - done_today
    if left <= 0:
        return []
    used = {str(t)[11:] for i in mine for t in (i.tags or []) if str(t).startswith("comentario:")} | _seen()
    week = datetime.now(timezone.utc) - timedelta(days=7)
    cands = [c for c in cands if c.yt_id not in used and len((c.text or "").strip()) >= 15
             and (c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=timezone.utc)) >= week]
    cands.sort(key=lambda c: -c.likes)
    cands = cands[:10]
    if not cands:
        return []
    titles = existing_titles(ch.id, 150)
    listing = "\n".join(f"[{i}] (no vídeo \"{c.video_title or c.video_id}\") {handle_of(c.author)}: {c.text[:400]}"
                        for i, c in enumerate(cands))
    data = llm.complete_json(f"""{channel_brief(ch)}

Perguntas que o público deixou nos comentários do canal:
{listing}

Quais destas perguntas merecem um VÍDEO PRÓPRIO do canal respondendo? Só as que: são sobre o assunto do canal (não sobre
a voz, o programa usado, o canal em si), têm resposta factual verificável, interessam a mais gente além de quem
perguntou, não são respondidas no próprio vídeo comentado e não são ofensivas nem pedidos de opinião política.
Na dúvida, deixe de fora. Para cada escolhida, proponha a pauta do vídeo-resposta (Short).
Pautas que o canal já tem (não repita):
{chr(10).join('- ' + t for t in titles[:80]) or '(nenhuma)'}

Responda JSON: {{"ideas": [{{"i": 0, "title": "título de 35-50 caracteres, assunto concreto no começo",
  "angle": "a pergunta central e o que o vídeo revela", "summary": "o que se sabe (2-3 frases factuais)"}}]}}""",
                             temperature=0.4)
    _mark_seen({c.yt_id for c in cands})  # avaliados: não gastam cota de novo no próximo ciclo
    known = [set(_tokens(t)) for t in titles]
    created: list[int] = []
    for it in (data.get("ideas") or []) if isinstance(data, dict) else []:
        if len(created) >= left or not isinstance(it, dict):
            break
        try:
            c = cands[int(it.get("i"))]
        except (TypeError, ValueError, IndexError):
            continue
        title = str(it.get("title") or "").replace("#Shorts", "").strip()[:200]
        tok = set(_tokens(title))
        if not title or any(tok and _jaccard(tok, k) >= 0.5 for k in known):
            continue
        who = handle_of(c.author)
        with session() as s:
            idea = Idea(channel_id=ch.id, title=title, format="short", origin="comment", status="new",
                        angle=f"Respondendo {who}: {str(it.get('angle') or c.text)[:400]}",
                        summary=str(it.get("summary") or c.text)[:1200],
                        tags=[f"comentario:{c.yt_id}", f"autor:{who}"[:80], f"pergunta:{c.text.strip()[:160]}"])
            s.add(idea)
            s.commit()
            s.refresh(idea)
        known.append(tok)
        created.append(idea.id)
        enqueue("manual_idea", title=f"Checar pauta (pergunta de {who}): {title}", channel_id=ch.id, ref_id=idea.id)
        if ctx:
            ctx.log(f"Pergunta de {who} virou pauta: {title}")
    return created


def reply(comment_id: int, text: str) -> None:
    with session() as s:
        c = s.get(Comment, comment_id)
    acc = _account(c.channel_id)
    if not can_write(acc):
        raise RuntimeError("Reconecte o canal (Canais → Reconectar) para liberar a permissão de responder comentários")
    __import__("lidark.quota", fromlist=["x"]).spend(50, "comment")  # medidor de cota diária
    _yt(acc).comments().insert(part="snippet", body={"snippet": {"parentId": c.yt_id, "textOriginal": text}}).execute()
    with session() as s:
        db = s.get(Comment, comment_id)
        db.status, db.reply, db.replied_at = "replied", text, now()
        s.add(db)
        s.commit()


@handler("fetch_comments")
def job_fetch_comments(ctx: JobContext) -> dict:
    with session() as s:
        chans = [s.get(Channel, ctx.channel_id)] if ctx.channel_id else s.exec(select(Channel)).all()
    total = 0
    for ch in chans:
        if ch and ch.youtube_id:
            try:
                total += fetch_comments(ch, ctx)
            except Exception as e:  # noqa: BLE001
                ctx.log(f"{ch.name}: {e}")
            try:  # refaz o que ficou sem sugestão: a IA pode ter falhado quando o comentário chegou
                suggest_replies(ch, ctx)
            except Exception as e:  # noqa: BLE001
                ctx.log(f"{ch.name}: sugestão de resposta falhou: {e}")
    return {"new": total}


# ================================================================ Shorts ↔ vídeo longo

def _related(pub: Publication, others: list[Publication]) -> list[Publication]:
    """A IA escolhe quais vídeos falam do mesmo assunto (nunca liga vídeos sem relação)."""
    if not others:
        return []
    listing = "\n".join(f"[{i}] {p.title}" for i, p in enumerate(others[:30]))
    data = llm.complete_json(f"""Vídeo publicado: "{pub.title}"
Quais vídeos abaixo são sobre o MESMO assunto ou um assunto diretamente ligado (mesmo personagem, evento, lugar ou fenômeno)?
Seja rigoroso: na dúvida, não inclua.
{listing}
Responda JSON: {{"related": [índices]}}""", temperature=0.1)
    idx = [i for i in (data.get("related", []) if isinstance(data, dict) else []) if isinstance(i, int) and 0 <= i < len(others)]
    return [others[i] for i in idx][:5]


def crosslink(pub_id: int, ctx: JobContext | None = None) -> int:
    """Depois de publicar: Short → comenta o link do vídeo longo do mesmo assunto; longo → comenta nos Shorts relacionados."""
    with session() as s:
        pub = s.get(Publication, pub_id)
        video = s.get(Video, pub.video_id) if pub and pub.video_id else None
        sc = s.get(Script, video.script_id) if video else None
        ch = s.get(Channel, pub.channel_id) if pub else None
        pubs = s.exec(select(Publication).where(Publication.channel_id == pub.channel_id, Publication.status == "published",
                                                Publication.id != pub_id)).all() if pub else []
        fmt_of = {}
        for p in pubs:
            v = s.get(Video, p.video_id) if p.video_id else None
            fmt_of[p.id] = v.format if v else ("short" if "/shorts/" in (p.url or "") or (p.duration or 0) <= 180 else "long")
    if not pub or not video or not pub.external_id:
        return 0
    acc = _account(pub.channel_id)
    if not can_write(acc):
        if ctx:
            ctx.log("Ligação Short ↔ longo: reconecte o canal para liberar a permissão de comentar")
        return 0
    yt = _yt(acc)
    done = 0
    if video.format == "short":
        longs = [p for p in pubs if fmt_of[p.id] == "long" and p.url]
        var = (sc.variety or {}) if sc else {}
        # Short tirado de um longo: o longo de origem é certo (não depende da IA achar a relação)
        known = [p for p in longs if p.url == var.get("from_long") or (var.get("from_long_video") and p.video_id == var["from_long_video"])]
        for lp in (known or _related(pub, longs))[:1]:
            text = f"🎬 Quer a história completa? Vídeo longo no canal: {lp.title.strip()} → {lp.url}"
            __import__("lidark.quota", fromlist=["x"]).spend(50, "comment")  # medidor de cota diária
            yt.commentThreads().insert(part="snippet", body={"snippet": {"videoId": pub.external_id, "topLevelComment": {
                "snippet": {"textOriginal": text}}}}).execute()
            _mark(pub.id, lp.external_id)
            done += 1
    else:
        shorts = [p for p in pubs if fmt_of[p.id] == "short" and p.external_id and pub.external_id not in (p.links or [])]
        src = ((sc.variety or {}) if sc else {}).get("from_short_ext")  # longo nascido de um Short campeão: ele primeiro
        first = [p for p in shorts if src and p.external_id == src]
        for sp in first + _related(pub, [p for p in shorts if p not in first])[:5 - len(first)]:
            text = f"🎬 Saiu o vídeo completo sobre isso: {pub.title.strip()} → {pub.url}"
            __import__("lidark.quota", fromlist=["x"]).spend(50, "comment")  # medidor de cota diária
            yt.commentThreads().insert(part="snippet", body={"snippet": {"videoId": sp.external_id, "topLevelComment": {
                "snippet": {"textOriginal": text}}}}).execute()
            _mark(sp.id, pub.external_id)
            done += 1
    if ctx:
        ctx.log(f"Ligação Short ↔ longo: {done} comentário(s) com link")
    return done


def _mark(pub_id: int, other_ext: str) -> None:
    with session() as s:
        p = s.get(Publication, pub_id)
        p.links = list(dict.fromkeys((p.links or []) + [other_ext]))
        s.add(p)
        s.commit()


@handler("crosslink")
def job_crosslink(ctx: JobContext) -> dict:
    return {"links": crosslink(ctx.ref_id, ctx)}


# ================================================================ comentário do canal (puxa conversa)
# A API do YouTube deixa o canal comentar (commentThreads.insert, escopo youtube.force-ssl, 50 unidades),
# mas NÃO tem como fixar comentário — você fixa com um clique pelo link que aparece em Comentários.

SEED_STYLES: dict[str, str] = {
    "pergunta": "uma pergunta ESPECÍFICA sobre um detalhe concreto do vídeo (um nome, número, lugar ou decisão citado) "
                "que dê vontade de responder. Nada genérico como \"o que você achou?\"",
    "escolha": "um \"A ou B?\": duas opções concretas tiradas do próprio assunto (dois personagens, duas decisões, "
               "duas teorias, dois lugares) para a pessoa escolher um lado e defender",
    "proximo": "pergunte qual deve ser o próximo tema do canal",
    "opiniao": "uma afirmação discutível (mas respeitosa e verdadeira) ligada ao vídeo, chamando quem discorda pra conversa",
    "vivencia": "pergunte sobre a vivência da pessoa ligada ao tema (já esteve lá, já ouviu essa história, conhece alguém, "
                "o que faria no lugar do personagem)",
}
_SEED_BANNED = re.compile(r"https?://|www\.|\.com\b|inscrev|curt[aei]|\blike|sininho|notifica|compartilh|link na", re.I)
# Cota: 10.000 unidades/dia por projeto do Google Cloud (todos os canais dividem). O envio de vídeo (videos.insert)
# tem balde próprio (100 envios/dia, 1 unidade cada); miniatura, playlist e comentários custam 50 cada nos 10.000.
YT_DAILY_QUOTA = 10_000
YT_COST = {"publish": 100, "comment": 50}  # publish = miniatura + playlist da série
YT_RESERVE = 1000  # sempre sobra para miniaturas/playlists dos próximos envios e leituras de métricas


def _seed_ideas(ch: Channel, fmt: str, exclude_title: str) -> list[str]:
    """Pautas reais da fila para o "qual o próximo?" — só oferece o que o canal pode mesmo produzir."""
    with session() as s:
        rows = s.exec(select(Idea).where(Idea.channel_id == ch.id, Idea.status.in_(["new", "approved"]), Idea.format == fmt)
                      .order_by(Idea.score.desc()).limit(6)).all()
    return [i.title for i in rows if i.title.strip().lower() != exclude_title.strip().lower()][:3]


def _recent_seeds(channel_id: int, n: int = 8) -> list[Comment]:
    with session() as s:
        return list(s.exec(select(Comment).where(Comment.channel_id == channel_id, Comment.status == "seed")
                           .order_by(Comment.created_at.desc()).limit(n)).all())


def _pick_style(pub_id: int, recent: list[Comment], has_ideas: bool) -> str:
    """Alterna o estilo: nunca repete os 2 últimos do canal; "próximo tema" só de vez em quando."""
    rng = random.Random(pub_id * 7919 + int(time.time() // 3600))
    last = [c.seed_style for c in recent[:2]]
    weights = {"pergunta": 1.0, "escolha": 1.0, "opiniao": 0.7, "vivencia": 0.8, "proximo": 0.6 if has_ideas else 0.25}
    opts = [k for k in weights if k not in last] or list(weights)
    return rng.choices(opts, weights=[weights[k] for k in opts])[0]


def _clean_seed(text: str) -> str:
    text = re.sub(r"#\w+", "", str(text or "")).strip().strip('"“”').strip()
    return re.sub(r"\s{2,}", " ", text)[:400]


def seed_text(pub_id: int, style: str | None = None) -> tuple[str, str]:
    """Gera (sem postar) o comentário do canal para o vídeo: (texto, estilo). Texto vazio = não deu para gerar."""
    from .content import channel_brief
    from .variety import _jaccard, _tokens
    with session() as s:
        pub = s.get(Publication, pub_id)
        ch = s.get(Channel, pub.channel_id) if pub else None
        video = s.get(Video, pub.video_id) if pub and pub.video_id else None
        sc = s.get(Script, video.script_id) if video else None
    if not pub or not ch:
        return "", ""
    from .story.series import vote_comment  # parte de série com decisão A/B: o comentário fixado é a votação
    if sc is not None and (fixed := vote_comment(sc)):
        return fixed, "escolha"
    fmt = video.format if video else ("short" if (pub.duration or 0) <= 70 else "long")
    title = (sc.title if sc else pub.title).replace("#Shorts", "").strip()
    body = (sc.full_text if sc else pub.description or "")[:3000]
    recent = _recent_seeds(ch.id)
    ideas = _seed_ideas(ch, fmt, title)
    style = style if style in SEED_STYLES else _pick_style(pub_id, recent, len(ideas) >= 2)
    rng = random.Random(pub_id)
    size = rng.choice(["uma frase curta", "uma ou duas frases", "duas frases curtas"])
    emoji = rng.choice(["sem emoji", "no máximo 1 emoji", "sem emoji"])
    how = SEED_STYLES[style]
    if style == "proximo":
        how += (": ofereça estas opções reais da fila (pode resumir os títulos) e peça o voto → " + " | ".join(ideas[:2])
                if len(ideas) >= 2 else ": deixe a pessoa sugerir, dando um exemplo concreto do nicho")
    avoid = "\n".join(f"- {c.text[:160]}" for c in recent[:6]) or "(nenhum ainda)"
    draft = str(((sc.variety or {}) if sc else {}).get("pinned_comment") or "").strip()
    prompt = f"""{channel_brief(ch)}

Você é quem cuida do canal e vai deixar o PRIMEIRO comentário no vídeo que acabou de sair, para puxar conversa
nos comentários (o canal vai fixar esse comentário no topo).

VÍDEO ({'Short' if fmt == 'short' else 'vídeo longo'}): "{title}"
GANCHO: {(sc.hook if sc else '')[:300]}
ROTEIRO:
{body}

O COMENTÁRIO DEVE SER: {how}.
Tamanho: {size}, até 260 caracteres, {emoji}.
{('IDEIA DO ROTEIRISTA (aproveite só se encaixar no formato pedido acima; pode reescrever): ' + draft) if draft else ''}
O QUE FAZ AS PESSOAS RESPONDEREM: um detalhe concreto do vídeo (nome, número, decisão), uma resposta fácil de dar em
poucas palavras, e um lado para defender. Pergunta aberta demais ("o que acharam?") não recebe resposta.
REGRAS: escreva no idioma do canal ({ch.language}), natural, como gente de verdade — na voz do canal, não de robô;
use só fatos que estão no roteiro; sem links, sem hashtags; NUNCA peça curtida, inscrição, sininho ou compartilhamento;
não comece com "E aí, galera", "Fala, pessoal" nem "Comenta aí"; não repita a abertura nem a estrutura destes
comentários recentes do canal:
{avoid}

Responda JSON: {{"text": "..."}}"""
    recent_tok = [set(_tokens(c.text)) for c in recent]
    for attempt in range(3):
        data = llm.complete_json(prompt, temperature=0.85 + 0.1 * attempt)
        text = _clean_seed(data.get("text", "") if isinstance(data, dict) else "")
        if not text or len(text) < 15 or _SEED_BANNED.search(text):
            continue
        if any(_jaccard(set(_tokens(text)), r) > 0.5 for r in recent_tok):
            continue  # parecido demais com um comentário recente do canal
        return text, style
    return "", style


def _quota_day_start() -> datetime:
    """A cota do YouTube zera à meia-noite do horário do Pacífico (devolve em UTC)."""
    from zoneinfo import ZoneInfo
    t = datetime.now(ZoneInfo("America/Los_Angeles")).replace(hour=0, minute=0, second=0, microsecond=0)
    return t.astimezone(timezone.utc)


def yt_units_today() -> int:
    """Estimativa das unidades da API do YouTube gastas hoje no balde de 10.000 (miniaturas, playlists, comentários,
    respostas, ligações Short ↔ longo) + folga de leituras."""
    from sqlmodel import func
    start = _quota_day_start()
    with session() as s:
        jobs_ = s.exec(select(Job).where(Job.kind.in_(["publish", "crosslink"]), Job.status == "done",
                                         Job.finished_at >= start)).all()
        seeds = s.exec(select(func.count()).select_from(Comment).where(Comment.status == "seed", Comment.created_at >= start)).one()
        replies = s.exec(select(func.count()).select_from(Comment).where(Comment.replied_at >= start)).one()
    units = sum(YT_COST["publish"] if j.kind == "publish" else YT_COST["comment"] * int((j.result or {}).get("links") or 0)
                for j in jobs_)
    from . import quota  # medidor central (quota.py) — vale o maior dos dois
    return max(quota.used(), units + YT_COST["comment"] * (int(seeds) + int(replies)) + 300)


def _seed_later(pub: Publication, at: datetime, tries: int, why: str) -> None:
    j = enqueue("seed_comment", title=f"Comentário do canal: {pub.title.replace('#Shorts', '').strip()[:60]}",
                channel_id=pub.channel_id, ref_id=pub.id, payload={"_not_before": at.timestamp(), "tries": tries})
    with session() as s:
        db = s.get(Job, j.id)
        db.stage = f"{why} — posta às {at.astimezone():%d/%m %H:%M}"
        s.add(db)
        s.commit()


def post_seed(pub_id: int, ctx: JobContext | None = None) -> dict:
    """Posta o comentário do canal no vídeo publicado (uma vez por vídeo) e avisa para fixar."""
    from . import config
    say = ctx.log if ctx else log.info
    with session() as s:
        pub = s.get(Publication, pub_id)
        ch = s.get(Channel, pub.channel_id) if pub else None
        done = s.exec(select(Comment).where(Comment.status == "seed", Comment.video_id == pub.external_id)).first() \
            if pub and pub.external_id else None
    if not pub or not ch or pub.status != "published" or not pub.external_id:
        return {"skipped": "vídeo não publicado"}
    if done:
        return {"skipped": "já comentado", "comment_id": done.id}
    if ch.seed_comment_off or pub.privacy != "public":
        return {"skipped": "desligado no canal" if ch.seed_comment_off else "vídeo não é público"}
    acc = _account(ch.id)
    if not can_write(acc):
        say("Comentário do canal: reconecte o canal (Canais → Reconectar) para liberar a permissão de comentar")
        return {"skipped": "sem permissão de comentar"}
    tries = int((ctx.payload if ctx else {}).get("tries", 0))
    quota = int(config.get("yt_daily_quota") or YT_DAILY_QUOTA)
    used = yt_units_today()
    if used + YT_COST["comment"] > quota - YT_RESERVE:
        from zoneinfo import ZoneInfo
        reset = datetime.now(ZoneInfo("America/Los_Angeles")).replace(hour=0, minute=20, second=0, microsecond=0) + timedelta(days=1)
        say(f"Cota do YouTube quase no fim (~{used}/{quota} unidades hoje): o comentário fica para depois da renovação")
        _seed_later(pub, reset, tries, "Cota do YouTube no fim")
        return {"postponed": "cota"}
    text, style = seed_text(pub.id)
    if not text:
        say("Comentário do canal: a IA não gerou um texto bom o bastante — pulado")
        return {"skipped": "sem texto"}
    from googleapiclient.errors import HttpError
    try:
        __import__("lidark.quota", fromlist=["x"]).spend(50, "comment")  # medidor de cota diária
        resp = _yt(acc).commentThreads().insert(part="snippet", body={"snippet": {"videoId": pub.external_id, "topLevelComment": {
            "snippet": {"textOriginal": text}}}}).execute()
    except HttpError as e:
        reason = ""
        try:
            reason = (e.error_details or [{}])[0].get("reason", "")
        except Exception:  # noqa: BLE001
            pass
        if (e.resp.status >= 500 or reason in ("videoNotFound", "processingFailure", "forbidden")) and tries < 3:
            say(f"Comentário do canal: YouTube recusou agora ({reason or e.resp.status}) — tenta de novo em 30 min")
            _seed_later(pub, now() + timedelta(minutes=30), tries + 1, "Vídeo ainda processando")
            return {"postponed": reason or str(e.resp.status)}
        say(f"Comentário do canal não postado: {reason or e}")
        return {"skipped": reason or "erro do YouTube"}
    with session() as s:
        c = Comment(channel_id=ch.id, yt_id=resp.get("id", ""), video_id=pub.external_id, video_title=pub.title, author=ch.name,
                    author_avatar=ch.avatar_url, text=text, published_at=now(), kind="canal", status="seed", seed_style=style)
        s.add(c)
        s.commit()
        s.refresh(c)
    say(f"Comentário do canal ({style}): {text}")
    from . import notify
    notify.safe(f"📌 Fixe o comentário · {ch.name}", f"{pub.title.replace('#Shorts', '').strip()}\n{text}", event="comments",
                tags=["pushpin"], click=pin_url(pub.external_id, c.yt_id))
    return {"comment_id": c.id, "style": style}


def pin_url(video_id: str, comment_id: str) -> str:
    """Abre o vídeo com o comentário destacado no topo: ⋮ → Fixar."""
    return f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}"


@handler("seed_comment")
def job_seed_comment(ctx: JobContext) -> dict:
    return post_seed(ctx.ref_id, ctx)


def after_publish(pub_id: int, channel_id: int) -> None:
    enqueue("crosslink", title="Ligar Short ↔ vídeo longo", channel_id=channel_id, ref_id=pub_id)
    with session() as s:
        pub = s.get(Publication, pub_id)
        ch = s.get(Channel, channel_id)
    if not pub or not ch or ch.seed_comment_off or pub.privacy != "public" or not can_write(_account(channel_id)):
        return
    # vídeo agendado fica privado até ir ao ar (não aceita comentário): espera a estreia + alguns minutos
    live = pub.published_at or now()
    live = live if live.tzinfo else live.replace(tzinfo=timezone.utc)
    _seed_later(pub, max(live, now()) + timedelta(minutes=8), 0, "Esperando o vídeo ir ao ar")
