"""Avisos no celular via ntfy (app grátis, sem cadastro): o sistema publica num tópico secreto e o celular assina.

Avisa: vídeo pronto / para revisar, falhas, publicação no ar, comentários novos e um resumo diário.

Central de notificações do painel: todo aviso também vira uma linha na tabela Notification (mesmo com o ntfy
desligado) e sai ao vivo no /api/events como evento "notification" (o sino da barra de cima).
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel, select

from . import config
from .models import now

log = logging.getLogger("lidark.notify")


def topic() -> str:
    t = config.get("ntfy_topic") or ""
    if not t:  # gera um tópico secreto (quem souber o nome recebe os avisos — por isso é aleatório)
        t = f"lidark-{secrets.token_urlsafe(9).replace('_', '').replace('-', '').lower()}"
        config.save_settings({"ntfy_topic": t})
    return t


def enabled(event: str = "") -> bool:
    if not config.get("ntfy_enabled"):
        return False
    return not event or event not in (config.get("ntfy_muted") or [])


def send(title: str, message: str, *, event: str = "", tags: list[str] | None = None, priority: int = 3,
         click: str = "", force: bool = False) -> bool:
    if event != "daily":  # o resumo diário é só do celular; o resto também vai para o sino do painel
        try:
            record(event or "info", title, message, link=click or EVENT_LINKS.get(event, ""))
        except Exception as e:  # noqa: BLE001
            log.warning("notificação não registrada: %s", e)
    if not force and not enabled(event):
        return False
    body: dict[str, Any] = {"topic": topic(), "title": title[:120], "message": message[:3500],
                            "tags": tags or [], "priority": priority}
    if click:
        body["click"] = click
    try:
        r = httpx.post(config.get("ntfy_server") or "https://ntfy.sh", json=body, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("aviso não enviado: %s", e)
        return False


def safe(*a, **kw) -> None:
    """Nunca deixa um aviso derrubar a tarefa que o disparou."""
    try:
        send(*a, **kw)
    except Exception as e:  # noqa: BLE001
        log.warning("aviso: %s", e)


# ---------------------------------------------------------------- resumo diário

def daily_summary() -> str:
    from sqlmodel import func, select
    from .db import session
    from .models import Channel, Comment, Idea, Job, Publication, Video
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    lines = []
    with session() as s:
        for ch in s.exec(select(Channel)).all():
            made = s.exec(select(func.count()).select_from(Video).where(Video.channel_id == ch.id, Video.created_at >= since,
                                                                        Video.status.in_(["ready", "review", "published"]))).one()
            pubs = s.exec(select(Publication).where(Publication.channel_id == ch.id, Publication.status == "published",
                                                    Publication.published_at >= since)).all()
            review = s.exec(select(func.count()).select_from(Video).where(Video.channel_id == ch.id, Video.status == "review")).one()
            ideas = s.exec(select(func.count()).select_from(Idea).where(Idea.channel_id == ch.id, Idea.status.in_(["new", "approved"]),
                                                                        Idea.fact_status == "verified")).one()
            com = s.exec(select(func.count()).select_from(Comment).where(Comment.channel_id == ch.id, Comment.status == "new")).one()
            subs = (ch.stats or {}).get("subscribers", 0)
            part = [f"▸ {ch.name} · {subs} inscritos",
                    f"  {made} vídeo(s) produzido(s) · {len(pubs)} publicado(s)" + (f" · {review} para revisar" if review else ""),
                    f"  {ideas} pauta(s) confirmada(s) em estoque" + (f" · {com} comentário(s) para responder" if com else "")]
            for p in pubs[:3]:
                part.append(f"  ✓ {p.title.replace('#Shorts', '').strip()[:60]}")
            lines.append("\n".join(part))
        fails = s.exec(select(Job).where(Job.status == "failed", Job.finished_at >= since)).all()
    if fails:
        lines.append(f"⚠ {len(fails)} tarefa(s) falharam nas últimas 24 h: " + ", ".join(sorted({j.kind for j in fails})))
    return "\n\n".join(lines) or "Sem atividade nas últimas 24 h."


def send_daily() -> None:
    safe("Resumo do dia · Lidark", daily_summary(), event="daily", tags=["bar_chart"], priority=2)


# ================================================================ central de notificações (sino do painel)

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # failed | ready | review | published | comments | breakout | flop | quota | ypp | autopilot | info
    kind: str = Field(default="info", index=True)
    title: str = ""
    body: str = Field(default="", sa_column=Column(Text))
    link: str = ""  # rota do painel (/videos) ou URL externa (YouTube)
    channel_id: Optional[int] = Field(default=None, index=True)
    key: str = Field(default="", index=True)  # evita repetir o mesmo aviso (ex.: "breakout:123")
    read: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=now, index=True)


EVENT_LINKS = {"diagnose": "/metricas", "failed": "/fila", "ready": "/videos", "review": "/videos", "published": "/publicacao",
               "comments": "/comentarios", "checklist": "/videos", "approval": "/notificacoes"}
_ready = False


def _ensure() -> None:
    """Cria a tabela na hora se o banco foi criado antes deste módulo ser carregado."""
    global _ready
    if not _ready:
        from .db import engine
        Notification.__table__.create(engine, checkfirst=True)
        _ready = True


def item(n: Notification) -> dict[str, Any]:
    at = n.created_at
    if at is not None and at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    return {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body, "link": n.link,
            "created_at": at.isoformat() if at else None, "read": bool(n.read), "channel_id": n.channel_id,
            "key": n.key or ""}


def record(kind: str, title: str, body: str = "", *, link: str = "", channel_id: int | None = None,
           key: str = "") -> dict[str, Any] | None:
    """Grava a notificação e manda ao vivo para o painel. Com `key`, a mesma notificação nunca se repete."""
    from .db import session
    _ensure()
    with session() as s:
        if key and s.exec(select(Notification).where(Notification.key == key)).first():
            return None
        n = Notification(kind=kind[:30], title=title[:200], body=(body or "")[:4000], link=(link or "")[:500],
                         channel_id=channel_id, key=key[:200])
        s.add(n)
        s.commit()
        s.refresh(n)
        d = item(n)
    try:
        from .jobs import bus
        bus.publish("notification", d)
    except Exception:  # noqa: BLE001
        pass
    return d


def exists(key: str) -> bool:
    from .db import session
    _ensure()
    with session() as s:
        return s.exec(select(Notification.id).where(Notification.key == key)).first() is not None


def push(kind: str, title: str, body: str = "", *, link: str = "", channel_id: int | None = None, key: str = "",
         phone: bool = True, tags: list[str] | None = None, priority: int = 3, actions: list[dict] | None = None,
         attach: str = "", click: str = "") -> dict[str, Any] | None:
    """Notificação do painel + (se ligado) aviso no celular. Nunca levanta erro.
    actions = botões do ntfy (até 3: {"action": "http"|"view", "label", "url", ...}); attach = URL de imagem."""
    try:
        d = record(kind, title, body, link=link, channel_id=channel_id, key=key)
    except Exception as e:  # noqa: BLE001
        log.warning("notificação: %s", e)
        return None
    if d and phone and enabled(kind):
        msg: dict[str, Any] = {"topic": topic(), "title": title[:120], "message": (body or title)[:3500],
                               "tags": tags or [], "priority": priority}
        if click or link.startswith("http"):
            msg["click"] = click or link
        if actions:
            msg["actions"] = actions[:3]
        if attach:
            msg["attach"] = attach
        try:
            httpx.post(config.get("ntfy_server") or "https://ntfy.sh", json=msg, timeout=15)
        except Exception as e:  # noqa: BLE001
            log.warning("aviso não enviado: %s", e)
    return d


def list_items(limit: int = 30, unread_only: bool = False, kind: str = "", channel_id: int | None = None) -> dict[str, Any]:
    from sqlmodel import func
    from .db import session
    _ensure()
    with session() as s:
        q = select(Notification)
        if unread_only:
            q = q.where(Notification.read == False)  # noqa: E712
        if kind:
            q = q.where(Notification.kind.in_(kind.split(",")))
        if channel_id:
            q = q.where(Notification.channel_id == channel_id)
        rows = s.exec(q.order_by(Notification.id.desc()).limit(max(1, min(limit, 500)))).all()
        unread = s.exec(select(func.count()).select_from(Notification).where(Notification.read == False)).one()  # noqa: E712
    return {"items": [item(n) for n in rows], "unread": int(unread)}


def mark_read(ids: list[int] | None = None, all_: bool = False) -> int:
    from sqlalchemy import update
    from .db import session
    _ensure()
    q = update(Notification).where(Notification.read == False)  # noqa: E712
    if not all_:
        if not ids:
            return 0
        q = q.where(Notification.id.in_([int(i) for i in ids]))
    with session() as s:
        n = s.exec(q.values(read=True)).rowcount
        s.commit()
    return int(n or 0)


def prune(days: int = 60) -> None:
    """Notificações lidas com mais de 60 dias saem do banco."""
    from sqlalchemy import delete
    from .db import session
    _ensure()
    with session() as s:
        s.exec(delete(Notification).where(Notification.created_at < datetime.now(timezone.utc) - timedelta(days=days),
                                          Notification.read == True))  # noqa: E712
        s.commit()


# ---------------------------------------------------------------- varredura (o que não passa pelo send)

def scan_jobs(minutes: int = 15) -> int:
    """Avisos que nascem na fila: IA sem cota (tarefas adiadas) e falhas de tipos que não avisam pelo ntfy."""
    from .db import session
    from .jobs import NOTIFY_FAILS
    from .models import Job
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    n = 0
    with session() as s:
        waiting = s.exec(select(Job).where(Job.status == "queued", Job.stage.like("Sem cota de IA%"))).all()
        failed = s.exec(select(Job).where(Job.status == "failed", Job.finished_at >= since)).all()
    if waiting:
        hour = datetime.now().strftime("%Y-%m-%d %H")
        names = ", ".join(sorted({j.title[:50] for j in waiting})[:5])
        n += bool(record("quota", f"IA sem cota: {len(waiting)} tarefa(s) esperando",
                         f"Gemini/GLM sem cota agora — as tarefas tentam de novo sozinhas a cada 20 min. {names}",
                         link="/fila", key=f"quota:{hour}"))
    quiet = NOTIFY_FAILS | {"collect_metrics", "fetch_comments", "verify_idea", "score_idea", "seed_comment"}
    for j in failed:
        if j.kind in quiet:
            continue  # já avisados pelo send() (ou rotineiros demais para o sino)
        first = (j.error or "").split("\n")[0][:300]
        n += bool(record("failed", f"Falhou: {j.title[:80]}", first, link="/fila", channel_id=j.channel_id,
                         key=f"jobfail:{j.id}"))
    return n


# ================================================================ aprovação pelo celular (mesma rede Wi-Fi)
#
# Roteiros esperando revisão, vídeos reprovados no inspetor e miniaturas novas chegam no ntfy com botões
# "Aprovar" / "Recusar" (ação http do ntfy: o PRÓPRIO celular chama o notebook) e "Abrir no painel" (página
# simples com os mesmos botões). O painel principal só escuta em 127.0.0.1; para o celular alcançar o notebook sobe
# um servidor pequeno, separado, na porta 8766 da rede local, que só entende estas rotas e só com token:
#   POST /a/<tipo>/<id>/<acao>?t=<token>   (tipo: script | video | thumb · acao: approve | reject)
#   GET  /r/<tipo>/<id>?t=<token>          página com o item e os botões
#   GET  /img/<video_id>?t=<token>         a miniatura candidata (anexo do aviso)
# Token = HMAC-SHA256(segredo aleatório de 32 bytes guardado em data/phone_approval.json, "tipo:id:acao"): cada link
# só serve para aquele item e aquela ação; sem token (ou token errado) → 403.
# LIMITAÇÃO: só funciona com o celular no MESMO Wi-Fi do notebook (o IP é da rede local, 192.168.x.x). Fora de casa
# (4G/outra rede) os botões falham — aprove pelo painel. Na 1ª vez o Windows pode perguntar se libera o Python na
# rede privada: aceite (rede privada). O IP do notebook pode mudar (DHCP): os avisos novos já saem com o IP atual.

APPROVAL_PATH = config.DATA_DIR / "phone_approval.json"
APPROVAL_PORT = 8766
_approval_lock = __import__("threading").Lock()
_lan_server: Any = None


def _approval_state() -> dict[str, Any]:
    import json
    try:
        d = json.loads(APPROVAL_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        d = {}
    if not d.get("secret"):
        d["secret"] = secrets.token_hex(32)
        _approval_save(d)
    return d


def _approval_save(d: dict[str, Any]) -> None:
    import json
    APPROVAL_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def approval_token(kind: str, obj_id: int, action: str) -> str:
    import hashlib
    import hmac
    return hmac.new(_approval_state()["secret"].encode(), f"{kind}:{int(obj_id)}:{action}".encode(), hashlib.sha256).hexdigest()[:40]


def approval_check(kind: str, obj_id: int, action: str, token: str | None) -> bool:
    import hmac
    return bool(token) and hmac.compare_digest(approval_token(kind, obj_id, action), str(token))


def lan_ip() -> str:
    """IP do notebook na rede local (sem enviar nada: o UDP connect só escolhe a interface)."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:  # noqa: BLE001
        return "127.0.0.1"
    finally:
        s.close()


def lan_base() -> str:
    port = int(_approval_state().get("port") or APPROVAL_PORT)
    return f"http://{lan_ip()}:{port}"


def approval_links(kind: str, obj_id: int) -> dict[str, str]:
    b = lan_base()
    return {a: f"{b}/a/{kind}/{obj_id}/{a}?t={approval_token(kind, obj_id, a)}" for a in ("approve", "reject")} | {
        "view": f"{b}/r/{kind}/{obj_id}?t={approval_token(kind, obj_id, 'view')}",
        "img": f"{b}/img/{obj_id}?t={approval_token('thumb', obj_id, 'img')}"}


def request_approval(kind: str, obj_id: int, title: str, body: str, *, channel_id: int | None = None,
                     image: bool = False, candidate: str = "") -> dict[str, Any] | None:
    """Aviso com botões Aprovar/Recusar (uma vez por item). candidate = caminho da miniatura proposta (thumb)."""
    key = f"approval:{kind}:{obj_id}"
    if exists(key):
        return None
    if candidate:
        with _approval_lock:
            d = _approval_state()
            d.setdefault("candidates", {})[str(obj_id)] = candidate
            _approval_save(d)
    links = approval_links(kind, obj_id)
    actions = [{"action": "http", "label": "Aprovar", "url": links["approve"], "method": "POST", "clear": True},
               {"action": "http", "label": "Recusar", "url": links["reject"], "method": "POST", "clear": True},
               {"action": "view", "label": "Abrir no painel", "url": links["view"]}]
    return push("approval", title, body + "\n(Botões funcionam com o celular no mesmo Wi-Fi do notebook.)",
                link="/notificacoes", channel_id=channel_id, key=key, actions=actions, click=links["view"],
                attach=links["img"] if image else "", tags=["ballot_box_with_check"], priority=4)


def decision(kind: str, obj_id: int) -> dict[str, Any] | None:
    return (_approval_state().get("decided") or {}).get(f"{kind}:{obj_id}")


def decide(kind: str, obj_id: int, action: str, source: str = "painel") -> dict[str, Any]:
    """Executa Aprovar/Recusar. Idempotente: a 2ª decisão sobre o mesmo item só devolve a primeira."""
    from .db import session
    from .jobs import enqueue
    from .models import Script, Video
    if kind not in ("script", "video", "thumb") or action not in ("approve", "reject"):
        raise ValueError("ação inválida")
    prev = decision(kind, obj_id)
    if prev:
        return {**prev, "already": True}
    msg = ""
    with session() as s:
        if kind == "script":
            sc = s.get(Script, obj_id)
            if not sc:
                raise ValueError("roteiro não encontrado")
            if action == "approve":
                sc.status = "approved"
                s.add(sc)
                s.commit()
                enqueue("render_video", title=f"Vídeo: {sc.title}", channel_id=sc.channel_id, ref_id=sc.id)
                msg = f"Roteiro aprovado — vídeo em produção: {sc.title}"
            else:
                sc.status = "rejected"
                s.add(sc)
                s.commit()
                msg = f"Roteiro recusado: {sc.title}"
        elif kind == "video":
            v = s.get(Video, obj_id)
            if not v:
                raise ValueError("vídeo não encontrado")
            if action == "approve":
                qa = dict((v.assets or {}).get("qa") or {})
                qa.update({"passed": True, "manual": True})
                v.assets = {**(v.assets or {}), "qa": qa}
                if v.status == "review":
                    v.status = "ready"
                msg = "Vídeo aprovado (liberado para publicar)"
            else:
                if v.status in ("review", "ready"):
                    v.status, v.error = "failed", "Recusado na aprovação pelo celular"
                msg = "Vídeo recusado"
            s.add(v)
            s.commit()
    if kind == "thumb":
        cand = (_approval_state().get("candidates") or {}).get(str(obj_id))
        if action == "approve" and cand:
            from .thumbstudio import pick
            r = pick(obj_id, cand, youtube=True)  # se o vídeo já estiver no ar, a miniatura vai para o YouTube
            msg = "Miniatura aprovada" + (" e enviada ao YouTube" if (r.get("youtube") or {}).get("ok") else "")
        elif action == "approve":
            msg = "Miniatura sem candidata salva — escolha no Estúdio de thumbs"
        else:
            msg = "Miniatura recusada (fica a atual)"
    out = {"kind": kind, "id": obj_id, "action": action, "source": source, "message": msg,
           "at": datetime.now(timezone.utc).isoformat()}
    with _approval_lock:
        d = _approval_state()
        d.setdefault("decided", {})[f"{kind}:{obj_id}"] = out
        if len(d["decided"]) > 500:
            d["decided"] = dict(list(d["decided"].items())[-400:])
        _approval_save(d)
    try:  # a notificação do sino sai das pendentes
        from .db import session as _s
        with _s() as s:
            n = s.exec(select(Notification).where(Notification.key == f"approval:{kind}:{obj_id}")).first()
            if n and not n.read:
                n.read = True
                s.add(n)
                s.commit()
    except Exception:  # noqa: BLE001
        pass
    try:
        from .jobs import bus
        bus.publish("notification", {"id": 0, "kind": "approval", "title": msg, "body": "", "link": "", "read": True})
    except Exception:  # noqa: BLE001
        pass
    return out


def pending_approvals() -> list[dict[str, Any]]:
    """Itens que já foram para o celular e ainda não têm decisão (o painel mostra os mesmos botões)."""
    from .db import session
    _ensure()
    decided = _approval_state().get("decided") or {}
    with session() as s:
        rows = s.exec(select(Notification).where(Notification.kind == "approval").order_by(Notification.id.desc()).limit(100)).all()
    out = []
    for n in rows:
        parts = (n.key or "").split(":")
        if len(parts) == 3 and f"{parts[1]}:{parts[2]}" not in decided:
            out.append({**item(n), "approval_kind": parts[1], "object_id": int(parts[2])})
    return out


def scan_approvals(limit: int = 5) -> int:
    """A cada 10 min: roteiros esperando revisão, vídeos reprovados e miniaturas novas sem escolha → aviso com botões."""
    if not enabled("approval"):
        return 0
    from .channels import publish_prefs
    from .db import session
    from .models import Job, Script, Video
    since = datetime.now(timezone.utc) - timedelta(days=3)
    settle = datetime.now(timezone.utc) - timedelta(minutes=10)
    sent = 0
    with session() as s:
        scripts = s.exec(select(Script).where(Script.status == "draft", Script.created_at >= since,
                                              Script.created_at <= settle).order_by(Script.id.desc()).limit(30)).all()
        has_video = {v.script_id for v in s.exec(select(Video).where(Video.script_id.in_([x.id for x in scripts]))).all()} if scripts else set()
        busy = {j.ref_id for j in s.exec(select(Job).where(Job.kind.in_(["render_video", "review_script"]),
                                                           Job.status.in_(["queued", "running"]))).all()}
        review = s.exec(select(Video).where(Video.status == "review", Video.created_at >= since)).all()
        ready = s.exec(select(Video).where(Video.status == "ready", Video.created_at >= since)).all()
        titles = {x.id: x.title for x in s.exec(select(Script).where(Script.id.in_([v.script_id for v in review + ready]))).all()} \
            if review or ready else {}
    for sc in scripts:
        if sent >= limit:
            break
        if sc.id in has_video or sc.id in busy or not publish_prefs(sc.channel_id).get("phone_approval"):
            continue
        hook = (sc.hook or "")[:160]
        if request_approval("script", sc.id, f"Roteiro para aprovar: {sc.title[:80]}",
                            f"Gancho: {hook}\nAprovar = produzir o vídeo agora.", channel_id=sc.channel_id):
            sent += 1
    for v in review:
        if sent >= limit:
            break
        if not publish_prefs(v.channel_id).get("phone_approval"):
            continue
        qa = (v.assets or {}).get("qa") or {}
        bad = "; ".join(c.get("detail", "") for c in qa.get("checks") or [] if c.get("level") == "bad")[:200]
        if request_approval("video", v.id, f"Vídeo reprovado no inspetor: {titles.get(v.script_id, '')[:70]}",
                            f"{bad or 'O inspetor de qualidade reprovou.'}\nAprovar = liberar para publicar.",
                            channel_id=v.channel_id, image=False):
            sent += 1
    for v in ready:
        if sent >= limit:
            break
        st = (v.assets or {}).get("thumb_studio") or {}
        opts = [o for o in st.get("options") or [] if o.get("path")]
        if not opts or st.get("picked") or not publish_prefs(v.channel_id).get("phone_approval"):
            continue
        if request_approval("thumb", v.id, f"Miniatura nova: {titles.get(v.script_id, '')[:70]}",
                            f"Texto: {opts[0].get('text', '')}\nAprovar = usar esta miniatura no vídeo.",
                            channel_id=v.channel_id, image=True, candidate=opts[0]["path"]):
            sent += 1
    return sent


def _page(title: str, body: str, ok: bool = True) -> bytes:
    import html
    color = "#3ecf8e" if ok else "#ff6b6b"
    return (f"<!doctype html><html lang=pt-BR><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Lidark</title><body style='background:#0b0f0e;color:#e9ece8;font-family:system-ui;margin:0;padding:20px'>"
            f"<h2 style='color:{color};font-size:20px'>{html.escape(title)}</h2>{body}</body></html>").encode("utf-8")


def _view_html(kind: str, obj_id: int) -> bytes:
    import html
    from .db import session
    from .models import Script, Video
    name, extra = "", ""
    with session() as s:
        if kind == "script":
            sc = s.get(Script, obj_id)
            name = sc.title if sc else ""
            if sc:
                extra = "<p style='color:#aab'>" + html.escape(" ".join(x.get("text", "") for x in sc.scenes or [])[:1500]) + "</p>"
        else:
            v = s.get(Video, obj_id)
            sc = s.get(Script, v.script_id) if v else None
            name = sc.title if sc else f"Vídeo #{obj_id}"
            if kind == "thumb":
                extra = f"<img src='/img/{obj_id}?t={approval_token('thumb', obj_id, 'img')}' style='max-width:100%;border-radius:10px'>"
    prev = decision(kind, obj_id)
    links = approval_links(kind, obj_id)
    btn = "display:inline-block;padding:14px 22px;margin:6px 8px 0 0;border-radius:10px;border:0;font-size:16px;color:#fff"
    buttons = (f"<p style='color:#8a9690'>Já decidido: {html.escape(prev['message'])}</p>" if prev else
               f"<form method=post action='{html.escape(links['approve'])}' style='display:inline'><button style='{btn};background:#1d7a45'>Aprovar</button></form>"
               f"<form method=post action='{html.escape(links['reject'])}' style='display:inline'><button style='{btn};background:#b8322a'>Recusar</button></form>")
    label = {"script": "Roteiro", "video": "Vídeo reprovado no inspetor", "thumb": "Miniatura"}[kind]
    return _page(f"{label}: {name}", extra + buttons)


def _lan_handler():
    from http.server import BaseHTTPRequestHandler
    from urllib.parse import parse_qs, urlparse

    class H(BaseHTTPRequestHandler):
        server_version = "Lidark"

        def log_message(self, fmt, *args):  # noqa: A003
            log.info("aprovação (rede local) %s: " + fmt, self.client_address[0], *args)

        def _send(self, code: int, body: bytes, ctype: str = "text/html; charset=utf-8") -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _route(self, method: str) -> None:
            u = urlparse(self.path)
            parts = [p for p in u.path.split("/") if p]
            tok = (parse_qs(u.query).get("t") or [""])[0]
            try:
                if len(parts) == 4 and parts[0] == "a" and parts[3] in ("approve", "reject") and parts[2].isdigit():
                    kind, oid, act_ = parts[1], int(parts[2]), parts[3]
                    if not approval_check(kind, oid, act_, tok):
                        return self._send(403, _page("Link inválido", "<p>Token ausente ou errado.</p>", False))
                    r = decide(kind, oid, act_, source="celular")
                    return self._send(200, _page(r["message"] + (" (já estava decidido)" if r.get("already") else ""), ""))
                if method == "GET" and len(parts) == 3 and parts[0] == "r" and parts[2].isdigit():
                    if not approval_check(parts[1], int(parts[2]), "view", tok):
                        return self._send(403, _page("Link inválido", "<p>Token ausente ou errado.</p>", False))
                    return self._send(200, _view_html(parts[1], int(parts[2])))
                if method == "GET" and len(parts) == 2 and parts[0] == "img" and parts[1].isdigit():
                    oid = int(parts[1])
                    if not approval_check("thumb", oid, "img", tok):
                        return self._send(403, b"forbidden", "text/plain")
                    cand = (_approval_state().get("candidates") or {}).get(str(oid))
                    p = (config.MEDIA_DIR / cand).resolve() if cand else None
                    if not p or not p.is_file() or config.MEDIA_DIR.resolve() not in p.parents:
                        return self._send(404, b"not found", "text/plain")
                    return self._send(200, p.read_bytes(), "image/jpeg")
            except ValueError as e:
                return self._send(400, _page("Não deu", f"<p>{e}</p>", False))
            except Exception as e:  # noqa: BLE001
                log.warning("aprovação pelo celular: %s", e)
                return self._send(500, _page("Erro", "<p>Veja o painel.</p>", False))
            return self._send(404, b"not found", "text/plain")

        def do_GET(self):  # noqa: N802
            self._route("GET")

        def do_POST(self):  # noqa: N802
            self._route("POST")

    return H


def start_lan_server() -> dict[str, Any]:
    """Sobe (uma vez) o servidor de aprovação na rede local. Só as rotas com token acima — o painel continua local."""
    global _lan_server
    if _lan_server is not None:
        return {"running": True, "url": lan_base()}
    import threading
    from http.server import ThreadingHTTPServer
    port = int(_approval_state().get("port") or APPROVAL_PORT)
    try:
        srv = ThreadingHTTPServer(("0.0.0.0", port), _lan_handler())
    except OSError as e:
        log.warning("servidor de aprovação na porta %s não subiu: %s", port, e)
        return {"running": False, "error": str(e)}
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True, name="phone-approval").start()
    _lan_server = srv
    log.info("aprovação pelo celular em %s (mesma rede Wi-Fi)", lan_base())
    return {"running": True, "url": lan_base()}


def approval_status() -> dict[str, Any]:
    return {"running": _lan_server is not None, "url": lan_base(), "ntfy_enabled": bool(config.get("ntfy_enabled")),
            "muted": "approval" in (config.get("ntfy_muted") or []), "pending": len(pending_approvals()),
            "note": "Os botões Aprovar/Recusar do celular só funcionam no MESMO Wi-Fi do notebook (IP da rede local). "
                    "Fora de casa, aprove pelo painel. Se o Windows perguntar, libere o Python na rede privada."}
