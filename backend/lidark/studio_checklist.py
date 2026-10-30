"""Checklist do YouTube Studio: o que a API não faz, por vídeo publicado, com link direto para a tela certa.

Itens (conforme o formato e o nicho):
- Testar e comparar (longo): as 3 miniaturas A/B e até 3 títulos já gerados (thumbstudio / laboratório viral)
- Vídeo relacionado (Short): o melhor vídeo longo do canal sobre o mesmo assunto
- Tela final (longo): sugestão de vídeo para a tela final
- Dublagem automática (longo de espaço/ciência): conferir/ligar em Idiomas
- Fixar o comentário do canal
- Enquete na aba Posts: texto sugerido
Cada item pode ser marcado como feito (fica salvo na tabela studiochecklist).
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel, select

from .db import session
from .models import Channel, Comment, MetricSnapshot, Publication, Script, Video, now

log = logging.getLogger("lidark.studio_checklist")

SCIENCE_HINTS = ("espa", "cosmo", "astro", "univers", "cienc", "fisic", "quimic", "biolog", "science", "space", "planet")
STOP = set("a o os as um uma de do da dos das e em no na nos nas que por para com sem se sua seu como mais o que é foi "
           "the of and to in shorts voce isso esse essa este esta quem qual quando onde porque ja nao sim muito".split())


class StudioChecklist(SQLModel, table=True):
    publication_id: int = Field(primary_key=True)
    channel_id: int = Field(default=0, index=True)
    done: dict = Field(default_factory=dict, sa_column=Column(JSON))  # item → ISO do momento em que foi marcado
    poll: dict = Field(default_factory=dict, sa_column=Column(JSON))  # {"question", "options": [...]}
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)


_ready = False


def _ensure() -> None:
    global _ready
    if not _ready:
        from .db import engine
        StudioChecklist.__table__.create(engine, checkfirst=True)
        _ready = True


def _norm(t: str) -> str:
    return unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()


def _tokens(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{3,}", _norm(t)) if w not in STOP}


def _clean(t: str) -> str:
    return re.sub(r"\s*#shorts\b", "", t or "", flags=re.I).strip()


def is_science(ch: Channel) -> bool:
    txt = _norm(f"{ch.niche} {ch.slug} {ch.name}")
    return any(h in txt for h in SCIENCE_HINTS)


def _is_long(pub: Publication, video: Video | None) -> bool:
    if video:
        return video.format == "long"
    return bool(pub.duration and pub.duration > 180)


def _views(pub_ids: list[int]) -> dict[int, int]:
    if not pub_ids:
        return {}
    out: dict[int, int] = {}
    with session() as s:
        for m in s.exec(select(MetricSnapshot).where(MetricSnapshot.publication_id.in_(pub_ids))
                        .order_by(MetricSnapshot.captured_at)).all():
            out[m.publication_id] = int(m.views or 0)
    return out


def best_long_for(pub: Publication, sc: Script | None) -> dict[str, Any] | None:
    """Melhor vídeo longo publicado do canal para ligar a este Short (mesmo assunto; desempate por views)."""
    from_long = ((sc.variety or {}).get("from_long") if sc else "") or ""
    with session() as s:
        cands = s.exec(select(Publication).where(Publication.channel_id == pub.channel_id, Publication.status == "published",
                                                 Publication.id != pub.id, Publication.external_id != "")).all()
        fmt = {v.id: v.format for v in s.exec(select(Video).where(Video.channel_id == pub.channel_id)).all()}
    longs = [p for p in cands if (fmt.get(p.video_id) == "long") if p.video_id] + \
            [p for p in cands if not p.video_id and (p.duration or 0) > 180]
    if not longs:
        return None
    for p in longs:  # Short tirado de um longo: o longo de origem sempre ganha
        if from_long and p.external_id and p.external_id in from_long:
            return {"publication_id": p.id, "title": _clean(p.title), "url": p.url, "external_id": p.external_id,
                    "why": "vídeo longo de onde este Short saiu"}
    mine = _tokens(f"{pub.title} {' '.join((sc.tags or []) if sc else [])} {(sc.hook if sc else '')}")
    views = _views([p.id for p in longs])
    top = max(views.values() or [1]) or 1

    def score(p: Publication) -> float:
        t = _tokens(p.title)
        overlap = len(mine & t) / max(1, len(mine | t)) if mine and t else 0.0
        return overlap * 3 + (views.get(p.id, 0) / top)

    best = max(longs, key=score)
    shared = sorted(mine & _tokens(best.title))[:4]
    return {"publication_id": best.id, "title": _clean(best.title), "url": best.url, "external_id": best.external_id,
            "why": ("mesmo assunto (" + ", ".join(shared) + ")") if shared else "vídeo longo mais visto do canal"}


def _poll(pub: Publication, sc: Script | None, ch: Channel, row: StudioChecklist) -> dict[str, Any]:
    if row.poll.get("question"):
        return row.poll
    title = _clean(pub.title)
    poll: dict[str, Any] = {}
    try:  # uma chamada barata, guardada (o checklist abre várias vezes)
        from . import llm
        narr = " ".join(x.get("text", "") for x in ((sc.scenes if sc else []) or []))[:1200]
        data = llm.complete_json(f"""Canal do YouTube "{ch.name}" ({ch.niche}). Vídeo novo: "{title}".
Narração: {narr}
Escreva UMA enquete para a aba Posts do canal que faça quem viu o vídeo votar e quem não viu ficar curioso.
Pergunta ≤ 100 caracteres, 2 a 4 opções curtas (≤ 30 caracteres cada), em português do Brasil, só com fatos do vídeo,
sem pedir curtida/inscrição. Responda JSON: {{"question": "...", "options": ["...", "..."]}}""", temperature=0.7)
        if isinstance(data, dict) and data.get("question") and isinstance(data.get("options"), list):
            poll = {"question": str(data["question"])[:100],
                    "options": [str(o)[:30] for o in data["options"] if str(o).strip()][:4]}
    except Exception as e:  # noqa: BLE001
        log.info("enquete: %s", e)
    if len(poll.get("options") or []) < 2:
        poll = {"question": f"Vocês já sabiam disso? {title}"[:100],
                "options": ["Já sabia!", "Não fazia ideia", "Quero a parte 2"]}
    with session() as s:
        db = s.get(StudioChecklist, pub.id)
        if db:
            db.poll = poll
            s.add(db)
            s.commit()
    return poll


def _load(pub_id: int) -> tuple[Publication, Video | None, Script | None, Channel, StudioChecklist]:
    _ensure()
    with session() as s:
        pub = s.get(Publication, pub_id)
        if not pub:
            raise ValueError("publicação não encontrada")
        video = s.get(Video, pub.video_id) if pub.video_id else None
        sc = s.get(Script, video.script_id) if video else None
        ch = s.get(Channel, pub.channel_id)
        row = s.get(StudioChecklist, pub_id)
        if not row:
            row = StudioChecklist(publication_id=pub_id, channel_id=pub.channel_id)
            s.add(row)
            s.commit()
            s.refresh(row)
    return pub, video, sc, ch, row


def item_ids(pub: Publication, video: Video | None, ch: Channel) -> list[str]:
    long = _is_long(pub, video)
    ids = ["test_compare", "end_screen"] if long else ["related_video"]
    if long and is_science(ch):
        ids.append("dubbing")
    ids += ["pin_comment", "community_poll"]
    return ids


def build(pub_id: int, with_poll: bool = True) -> dict[str, Any]:
    pub, video, sc, ch, row = _load(pub_id)
    ext = pub.external_id
    edit = f"https://studio.youtube.com/video/{ext}/edit" if ext else ""
    long = _is_long(pub, video)
    items: list[dict[str, Any]] = []
    ids = item_ids(pub, video, ch)
    assets = (video.assets or {}) if video else {}
    if "test_compare" in ids:
        thumbs = [p for p in assets.get("thumbs_ab") or []][:3]
        if len(thumbs) < 3:
            opts = ((assets.get("thumb_studio") or {}).get("options") or [])
            thumbs += [o["path"] for o in opts if o.get("path") and o["path"] not in thumbs][:3 - len(thumbs)]
        titles = [_clean(pub.title)]
        try:
            from .viral import _report_row
            rep = _report_row(sc.id) if sc else None
            titles += [_clean(o["title"]) for o in (rep.suggestions if rep else []) if o.get("title")]
        except Exception:  # noqa: BLE001
            pass
        titles = list(dict.fromkeys(t for t in titles if t))[:3]
        items.append({"id": "test_compare", "label": "Testar e comparar",
                      "detail": "No Studio: Detalhes → Miniatura → Testar e comparar. Envie as 3 miniaturas"
                                + (" e os títulos" if len(titles) > 1 else "") + "; o YouTube fica com a que gera mais tempo assistido.",
                      "link": edit, "thumbs": thumbs, "titles": titles,
                      "hint": "" if thumbs else "Gere as 3 miniaturas em Vídeos → Miniaturas para teste A/B"})
    if "related_video" in ids:
        rel = best_long_for(pub, sc)
        items.append({"id": "related_video", "label": "Vídeo relacionado do Short",
                      "detail": ("No Studio: Detalhes → Vídeo relacionado → escolha “" + rel["title"] + "” (" + rel["why"] + ").")
                      if rel else "O canal ainda não tem vídeo longo publicado para ligar a este Short.",
                      "link": edit, "related": rel, "disabled": not rel})
    if "end_screen" in ids:
        rel = None
        try:
            with session() as s:
                others = s.exec(select(Publication).where(Publication.channel_id == pub.channel_id, Publication.status == "published",
                                                          Publication.id != pub.id, Publication.external_id != "")
                                .order_by(Publication.published_at.desc())).all()
                fmt = {v.id: v.format for v in s.exec(select(Video).where(Video.channel_id == pub.channel_id)).all()}
            longs = [p for p in others if fmt.get(p.video_id) == "long" or (not p.video_id and (p.duration or 0) > 180)] or others
            vw = _views([p.id for p in longs[:40]])
            if longs:
                best = max(longs[:40], key=lambda p: vw.get(p.id, 0))
                rel = {"title": _clean(best.title), "url": best.url}
        except Exception:  # noqa: BLE001
            pass
        items.append({"id": "end_screen", "label": "Tela final",
                      "detail": "No Studio: Detalhes → Tela final → modelo com “Inscrever-se” + “Melhor para o espectador”"
                                + (f" ou o vídeo “{rel['title']}”" if rel else "") + " nos últimos 20 s.",
                      "link": edit, "related": rel})
    if "dubbing" in ids:
        items.append({"id": "dubbing", "label": "Conferir/ligar dublagem automática",
                      "detail": "No Studio: Idiomas → Dublagem automática. O vídeo saiu com áudio em pt-BR (defaultAudioLanguage); "
                                "confira se as dublagens em inglês/espanhol foram geradas e publique ou ligue a opção.",
                      "link": f"https://studio.youtube.com/video/{ext}/translations" if ext else ""})
    if "pin_comment" in ids:
        with session() as s:
            c = s.exec(select(Comment).where(Comment.status == "seed", Comment.video_id == ext)).first() if ext else None
        from .community import pin_url
        items.append({"id": "pin_comment", "label": "Fixar o comentário do canal",
                      "detail": (f"Abra o vídeo, no comentário do canal toque ⋮ → Fixar: “{c.text[:140]}”") if c
                      else "O comentário do canal ainda não foi postado (sai alguns minutos depois de o vídeo ir ao ar).",
                      "link": pin_url(ext, c.yt_id) if c else (pub.url or ""), "auto_done": bool(c and c.pinned),
                      "disabled": not c})
    if "community_poll" in ids:
        poll = _poll(pub, sc, ch, row) if with_poll else (row.poll or {})
        handle = (ch.handle or "").strip()
        items.append({"id": "community_poll", "label": "Enquete na aba Posts",
                      "detail": "Crie uma enquete no canal (aba Posts) para puxar quem ainda não viu o vídeo.",
                      "link": f"https://www.youtube.com/{handle}/posts" if handle.startswith("@")
                      else (f"https://www.youtube.com/channel/{ch.youtube_id}/posts" if ch.youtube_id else ""),
                      "poll": poll})
    for it in items:
        it["done"] = bool(row.done.get(it["id"])) or bool(it.get("auto_done"))
        it["done_at"] = row.done.get(it["id"])
    active = [i for i in items if not i.get("disabled")]
    return {"publication": {"id": pub.id, "title": _clean(pub.title), "url": pub.url, "external_id": ext,
                            "studio": edit, "format": "long" if long else "short", "channel_id": pub.channel_id,
                            "video_id": pub.video_id,
                            "published_at": pub.published_at.isoformat() if pub.published_at else None},
            "items": items, "done": sum(1 for i in active if i["done"]), "total": len(active)}


def toggle(pub_id: int, item: str, done: bool) -> dict[str, Any]:
    _ensure()
    _load(pub_id)
    with session() as s:
        row = s.get(StudioChecklist, pub_id)
        d = dict(row.done or {})
        if done:
            d[item] = now().isoformat()
        else:
            d.pop(item, None)
        row.done, row.updated_at = d, now()
        s.add(row)
        s.commit()
    if item == "pin_comment":  # marcar "fixado" também atualiza o comentário-semente
        with session() as s:
            pub = s.get(Publication, pub_id)
            c = s.exec(select(Comment).where(Comment.status == "seed", Comment.video_id == pub.external_id)).first() \
                if pub and pub.external_id else None
            if c and c.pinned != done:
                c.pinned = done
                s.add(c)
                s.commit()
    return build(pub_id, with_poll=False)


def summary(channel_id: int | None = None, limit: int = 80) -> dict[int, dict[str, int]]:
    """{publication_id: {done, total}} dos vídeos publicados pelo sistema (sem chamar IA)."""
    _ensure()
    with session() as s:
        q = select(Publication).where(Publication.status == "published", Publication.video_id != None,  # noqa: E711
                                      Publication.external_id != "")
        if channel_id:
            q = q.where(Publication.channel_id == channel_id)
        pubs = s.exec(q.order_by(Publication.id.desc()).limit(limit)).all()
        vids = {v.id: v for v in s.exec(select(Video).where(Video.id.in_([p.video_id for p in pubs]))).all()} if pubs else {}
        chans = {c.id: c for c in s.exec(select(Channel)).all()}
        rows = {r.publication_id: r for r in s.exec(select(StudioChecklist).where(
            StudioChecklist.publication_id.in_([p.id for p in pubs]))).all()} if pubs else {}
        seeds = {c.video_id: c.pinned for c in s.exec(select(Comment).where(Comment.status == "seed")).all()}
        pinned = {k for k, v in seeds.items() if v}
        with_long = {p.channel_id for p in s.exec(select(Publication).join(Video, Video.id == Publication.video_id).where(
            Publication.status == "published", Video.format == "long")).all()}
        with_long |= {p.channel_id for p in s.exec(select(Publication).where(
            Publication.status == "published", Publication.video_id == None, Publication.duration > 180)).all()}  # noqa: E711
    out = {}
    for p in pubs:
        ch = chans.get(p.channel_id)
        if not ch:
            continue
        ids = [i for i in item_ids(p, vids.get(p.video_id), ch)  # mesmos itens "ativos" do build()
               if not (i == "related_video" and p.channel_id not in with_long) and not (i == "pin_comment" and p.external_id not in seeds)]
        done = set((rows.get(p.id).done or {}) if rows.get(p.id) else {})
        if p.external_id in pinned:
            done.add("pin_comment")
        out[p.id] = {"done": len([i for i in ids if i in done]), "total": len(ids), "video_id": p.video_id}
    return out


def notify_after_publish(pub_id: int) -> None:
    """Notificação no sino depois de publicar: o que falta fazer à mão no Studio (abre o checklist no painel)."""
    from . import notify
    data = build(pub_id, with_poll=False)
    p = data["publication"]
    lines = [f"• {i['label']}" for i in data["items"] if not i.get("disabled")]
    notify.push("checklist", f"Checklist do Studio · {p['title'][:70]}", "Falta fazer no YouTube Studio:\n" + "\n".join(lines),
                link=f"/videos?checklist={pub_id}", channel_id=p["channel_id"], key=f"checklist:{pub_id}", phone=False)
