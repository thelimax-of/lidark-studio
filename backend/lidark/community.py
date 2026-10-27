"""Comunidade: comentários do público (resposta sugerida pela IA, você aprova) e ligação Shorts ↔ vídeos longos."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlmodel import select

from . import llm
from .db import session
from .jobs import JobContext, enqueue, handler
from .models import Account, Channel, Comment, Publication, Script, Video, now

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
        titles = {p.external_id: p.title for p in s.exec(select(Publication).where(Publication.channel_id == ch.id)).all()}
    new = []
    for th in resp.get("items", []):
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
        suggest_replies(ch, ctx)
    if ctx:
        ctx.log(f"{len(new)} comentário(s) novo(s)")
    return len(new)


def _dt(iso: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def suggest_replies(ch: Channel, ctx: JobContext | None = None) -> None:
    with session() as s:
        pending = s.exec(select(Comment).where(Comment.channel_id == ch.id, Comment.status == "new",
                                               Comment.suggestion == "").limit(20)).all()
    if not pending:
        return
    from .content import channel_brief
    listing = "\n".join(f"[{i}] (vídeo: {c.video_title or c.video_id}) {c.author}: {c.text[:500]}" for i, c in enumerate(pending))
    data = llm.complete_json(f"""{channel_brief(ch)}

Você cuida dos comentários do canal. Para cada comentário abaixo, classifique e escreva uma resposta na voz do canal.
REGRAS da resposta: curta (até 220 caracteres), calorosa e natural, em português do Brasil; responda perguntas com fatos
corretos (se não tiver certeza, diga que vai pesquisar); agradeça correções com humildade; incentive a conversa com uma
pergunta quando fizer sentido; NUNCA invente fatos, nunca peça inscrição em toda resposta, sem links, no máximo 1 emoji.
Spam, golpe, ofensa ou propaganda → kind "spam" e resposta vazia.

COMENTÁRIOS:
{listing}

Responda JSON: {{"items": [{{"i": 0, "kind": "pergunta|elogio|correcao|sugestao|critica|spam|outro", "reply": "..."}}]}}""",
                             temperature=0.6)
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


def reply(comment_id: int, text: str) -> None:
    with session() as s:
        c = s.get(Comment, comment_id)
    acc = _account(c.channel_id)
    if not can_write(acc):
        raise RuntimeError("Reconecte o canal (Canais → Reconectar) para liberar a permissão de responder comentários")
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
        ch = s.get(Channel, pub.channel_id) if pub else None
        pubs = s.exec(select(Publication).where(Publication.channel_id == pub.channel_id, Publication.status == "published",
                                                Publication.id != pub_id)).all() if pub else []
        fmt_of = {}
        for p in pubs:
            v = s.get(Video, p.video_id) if p.video_id else None
            fmt_of[p.id] = v.format if v else ("short" if (p.duration or 0) <= 70 else "long")
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
        for lp in _related(pub, longs)[:1]:
            text = f"🎬 Quer a história completa? Vídeo longo no canal: {lp.title.strip()} → {lp.url}"
            yt.commentThreads().insert(part="snippet", body={"snippet": {"videoId": pub.external_id, "topLevelComment": {
                "snippet": {"textOriginal": text}}}}).execute()
            _mark(pub.id, lp.external_id)
            done += 1
    else:
        shorts = [p for p in pubs if fmt_of[p.id] == "short" and p.external_id and pub.external_id not in (p.links or [])]
        for sp in _related(pub, shorts):
            text = f"🎬 Saiu o vídeo completo sobre isso: {pub.title.strip()} → {pub.url}"
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


def after_publish(pub_id: int, channel_id: int) -> None:
    enqueue("crosslink", title="Ligar Short ↔ vídeo longo", channel_id=channel_id, ref_id=pub_id)
