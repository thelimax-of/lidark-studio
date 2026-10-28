"""Publicação e métricas no YouTube (Data API v3 + Analytics API).

Conexão: OAuth "app para computador" com retorno em http://localhost:8765/api/oauth/youtube/callback
"""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlmodel import select

from .config import MEDIA_DIR, SECRETS_DIR
from .db import session
from .jobs import JobContext, handler
from .models import Account, Channel, Insight, MetricSnapshot, Publication, Script, Video, now

log = logging.getLogger("lidark.publish")

YT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",  # playlists das séries
    "https://www.googleapis.com/auth/youtube.force-ssl",  # responder comentários e ligar Shorts ↔ longos
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]
YT_REDIRECT = "http://localhost:8765/api/oauth/youtube/callback"
_pending: dict[str, dict[str, Any]] = {}  # state → {platform, channel_id, verifier}


# ================================================================ conexão

def start_connect(platform: str, channel_id: int | None = None) -> dict:
    if platform == "youtube":
        return _yt_start(channel_id)
    raise HTTPException(400, "Plataforma não suportada")


# ---------------------------------------------------------------- YouTube

def _yt_flow(state: str | None = None):
    from google_auth_oauthlib.flow import Flow
    cs = SECRETS_DIR / "client_secret.json"
    if not cs.exists():
        raise HTTPException(400, "Coloque o client_secret.json do Google Cloud em data/secrets/")
    flow = Flow.from_client_secrets_file(str(cs), scopes=YT_SCOPES, state=state)
    flow.redirect_uri = YT_REDIRECT
    return flow


def _yt_start(channel_id: int | None) -> dict:
    state = secrets.token_urlsafe(16)
    flow = _yt_flow(state)
    url, _ = flow.authorization_url(access_type="offline", prompt="consent", include_granted_scopes="true")
    _pending[state] = {"platform": "youtube", "channel_id": channel_id, "verifier": getattr(flow, "code_verifier", None)}
    return {"auth_url": url}


def yt_callback(state: str, code: str) -> str:
    import os
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")  # retorno local em http://localhost
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    info = _pending.pop(state, None)
    if not info:
        raise HTTPException(400, "Sessão de login expirada — tente conectar de novo")
    flow = _yt_flow(state)
    if info.get("verifier"):
        flow.code_verifier = info["verifier"]
    flow.fetch_token(code=code)
    creds = flow.credentials
    yt = _yt_client(json.loads(creds.to_json()))
    me = yt.channels().list(part="snippet,statistics", mine=True).execute()
    item = (me.get("items") or [{}])[0]
    if not item.get("id"):
        raise HTTPException(400, "Essa conta Google não tem canal no YouTube — escolha o canal na tela de login")
    name = item.get("snippet", {}).get("title", "YouTube")
    from .channels import attach_or_create
    from .jobs import enqueue
    channel_id, created = attach_or_create(item, info.get("channel_id"))
    if created:  # canal planejado no assistente "Novo canal"? aplica a identidade pronta antes da configuração
        from .brandwizard import apply_draft, find_draft_for
        draft = find_draft_for(name, item.get("snippet", {}).get("customUrl", ""))
        if draft:
            apply_draft(draft.id, channel_id)
    with session() as s:
        acc = s.exec(select(Account).where(Account.channel_id == channel_id, Account.platform == "youtube")).first()
        if not acc:
            acc = Account(channel_id=channel_id, platform="youtube")
        acc.display_name, acc.external_id = name, item["id"]
        acc.credentials = json.loads(creds.to_json())
        acc.connected_at = now()
        s.add(acc)
        s.commit()
    enqueue("setup_channel", title=f"{'Configurar' if created else 'Sincronizar'} canal: {name}", channel_id=channel_id)
    return name


def _yt_client(creds_json: dict, api: str = "youtube", version: str = "v3"):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials.from_authorized_user_info({k: v for k, v in creds_json.items() if not k.startswith("_")})
    return build(api, version, credentials=creds, cache_discovery=False)


def _yt_creds(acc: Account) -> dict:
    if not acc.credentials:
        raise RuntimeError("Conta do YouTube importada sem login — conecte em Canais → Contas")
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    extra = {k: v for k, v in acc.credentials.items() if k.startswith("_")}
    c = Credentials.from_authorized_user_info({k: v for k, v in acc.credentials.items() if not k.startswith("_")})
    if not c.valid and c.refresh_token:
        c.refresh(Request())
        with session() as s:
            a = s.get(Account, acc.id)
            a.credentials = {**json.loads(c.to_json()), **extra}
            s.add(a)
            s.commit()
    return json.loads(c.to_json())


def go_live_at(pub: Publication) -> datetime | None:
    """Horário em que o YouTube deve tornar o vídeo público sozinho (vídeo enviado antes como privado)."""
    when = pub.scheduled_at
    if pub.privacy != "public" or when is None:
        return None
    when = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
    return when if (when - now()).total_seconds() >= 5 * 60 else None


def _has_ai_imagery(video: Video) -> bool:
    """O YouTube exige o selo "conteúdo alterado ou sintético" para cenas realistas geradas por IA.
    Fotos de arquivo, gráficos animados e o mascote cartoon não precisam. Na dúvida (sem registro), declara."""
    imgs = (video.assets or {}).get("images")
    if not isinstance(imgs, list) or not imgs:
        return True
    return any(not isinstance(p, dict) or p.get("kind") not in ("real", "graphic", "reuse", "video", None) for p in imgs)


def _hashtags(title: str, fmt: str, script_tags: list[str], channel_tags: list[str]) -> str:
    """Poucas hashtags (3 no máximo): muitas parecem spam e diluem o assunto. Prioriza as do roteiro."""
    seen, out = set(), []
    for h in script_tags + channel_tags:
        h = "#" + str(h).strip().lstrip("#").replace(" ", "")
        if len(h) > 1 and h.lower() not in seen and h.lower() != "#shorts" and h.lower() not in title.lower():
            seen.add(h.lower())
            out.append(h)
    if fmt == "short":
        return " ".join((["#Shorts"] if "#shorts" not in title.lower() else []) + out[:2])
    return " ".join(out[:3])


def yt_upload(acc: Account, pub: Publication, video: Video, sc: Script, ch: Channel, ctx: JobContext) -> tuple[str, str]:
    from googleapiclient.http import MediaFileUpload
    yt = _yt_client(_yt_creds(acc))
    title = pub.title[:95]
    tags = list(dict.fromkeys(sc.tags or []))[:25]
    hashtags = _hashtags(title, video.format, sc.hashtags or [], ch.default_hashtags or [])
    desc = _description(pub.description or sc.description, sc, video, hashtags)
    status: dict[str, Any] = {"privacyStatus": pub.privacy, "selfDeclaredMadeForKids": False,
                              "containsSyntheticMedia": _has_ai_imagery(video)}
    live = go_live_at(pub)
    if live:
        status.update(privacyStatus="private", publishAt=live.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"))
        ctx.log(f"Enviado como privado; o YouTube publica às {live.astimezone():%H:%M}")
    body = {
        "snippet": {"title": title, "description": desc[:4900], "tags": tags, "categoryId": ch.yt_category or "27",
                    "defaultLanguage": "pt-BR", "defaultAudioLanguage": "pt-BR"},
        "status": status,
    }
    media = MediaFileUpload(str(MEDIA_DIR / video.path), chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            ctx.update(0.1 + 0.8 * status.progress(), f"Enviando ao YouTube {int(status.progress() * 100)}%")
    vid = resp["id"]
    if video.thumbnail_path:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(MEDIA_DIR / video.thumbnail_path),
                                                                        mimetype="image/jpeg")).execute()
            ctx.log("Miniatura enviada")
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "verif" in msg.lower() or "forbidden" in msg.lower():
                msg = "o canal precisa ser verificado por telefone em youtube.com/verify para aceitar miniaturas"
                _set_thumbs_blocked(ch.id, True)  # próximos vídeos longos ganham a capa no 1º quadro
            ctx.log(f"Miniatura não enviada: {msg}")
        else:
            if ch.thumbs_blocked:
                _set_thumbs_blocked(ch.id, False)
    series = (sc.variety or {}).get("series")
    if series:
        try:
            _add_to_series(yt, acc, ch, series, vid, ctx)
        except Exception as e:  # noqa: BLE001
            ctx.log(f"Playlist da série não atualizada: {e}")
    url = f"https://youtube.com/shorts/{vid}" if video.format == "short" else f"https://youtu.be/{vid}"
    return vid, url


def _add_to_series(yt, acc: Account, ch: Channel, series: str, vid: str, ctx: JobContext) -> None:
    """Coloca o vídeo na playlist da série (cria a playlist na primeira vez)."""
    scopes = (acc.credentials or {}).get("scopes") or []
    if "https://www.googleapis.com/auth/youtube" not in scopes:
        ctx.log("Playlists: reconecte o canal (Canais → Reconectar) para liberar a permissão de playlists")
        return
    with session() as s:
        playlists = dict((s.get(Channel, ch.id).playlists or {}))
    pid = playlists.get(series)
    if not pid:
        body = {"snippet": {"title": series, "description": f"Série do canal {ch.name}: {series}.",
                            "defaultLanguage": "pt-BR"}, "status": {"privacyStatus": "public"}}
        pid = yt.playlists().insert(part="snippet,status", body=body).execute()["id"]
        with session() as s:
            db = s.get(Channel, ch.id)
            db.playlists = {**(db.playlists or {}), series: pid}
            s.add(db)
            s.commit()
        ctx.log(f"Playlist criada: {series}")
    yt.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": pid, "resourceId": {
        "kind": "youtube#video", "videoId": vid}}}).execute()
    ctx.log(f"Adicionado à série “{series}”")


def yt_metrics(acc: Account, pubs: list[Publication]) -> dict[str, dict[str, Any]]:
    ids = [p.external_id for p in pubs if p.external_id]
    out: dict[str, dict[str, Any]] = {}
    if not ids or not acc.credentials:
        return out
    creds = _yt_creds(acc)
    yt = _yt_client(creds)
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="statistics", id=",".join(ids[i:i + 50])).execute()
        for it in r.get("items", []):
            st = it.get("statistics", {})
            out[it["id"]] = {"views": int(st.get("viewCount", 0)), "likes": int(st.get("likeCount", 0)),
                             "comments": int(st.get("commentCount", 0))}
    try:
        ya = _yt_client(creds, "youtubeAnalytics", "v2")
        wanted = set(ids)
        # engagedViews = views que contam p/ monetizar Shorts (desde 31/03/2025 "views" conta todo início/replay)
        rep = ya.reports().query(
            ids="channel==MINE", startDate="2015-01-01", endDate=datetime.now(timezone.utc).date().isoformat(),
            metrics="views,engagedViews,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,shares",
            dimensions="video", sort="-views", maxResults=200).execute()
        for row in rep.get("rows", []) or []:
            vid, _v, engaged, mins, avd, avp, subs, shares = row
            if vid in wanted:
                out.setdefault(vid, {}).update({"engaged_views": int(engaged or 0), "watch_time_minutes": mins,
                                                "avg_view_duration": avd, "avg_view_percentage": avp,
                                                "subscribers_gained": subs, "shares": shares})
    except Exception as e:  # noqa: BLE001
        log.warning("YouTube Analytics: %s", e)
    return out


# origens de tráfego agrupadas como importam p/ a monetização: só o feed do Shorts divide receita de anúncios,
# e views vindas de anúncio pago (ADVERTISING) não são "qualificadas" (Central de Ajuda do YouTube)
TRAFFIC_GROUPS = {"SHORTS": "shorts_feed", "YT_SEARCH": "search", "ADVERTISING": "ads"}


def yt_traffic(acc: Account, days: int = 90) -> dict[str, Any]:
    """Views × views engajadas por origem de tráfego (feed do Shorts / busca / anúncios / outras) no canal."""
    ya = _yt_client(_yt_creds(acc), "youtubeAnalytics", "v2")
    end = datetime.now(timezone.utc).date()
    rep = ya.reports().query(ids="channel==MINE", startDate=(end - timedelta(days=days)).isoformat(), endDate=end.isoformat(),
                             metrics="views,engagedViews", dimensions="creatorContentType,insightTrafficSourceType").execute()
    groups: dict[str, dict[str, int]] = {}
    for ctype, src, v, e in rep.get("rows", []) or []:
        key = ("short_" if "short" in str(ctype).lower() else "long_") + TRAFFIC_GROUPS.get(src, "other")
        g = groups.setdefault(key, {"views": 0, "engaged_views": 0})
        g["views"] += int(v or 0)
        g["engaged_views"] += int(e or 0)
    return {"days": days, "updated_at": datetime.now(timezone.utc).isoformat(), "groups": groups,
            "sources": [{"type": str(c).lower(), "source": src, "views": int(v or 0), "engaged_views": int(e or 0)}
                        for c, src, v, e in rep.get("rows", []) or []]}


# ================================================================ textos

def _set_thumbs_blocked(channel_id: int, blocked: bool) -> None:
    with session() as s:
        c = s.get(Channel, channel_id)
        if c and c.thumbs_blocked != blocked:
            c.thumbs_blocked = blocked
            s.add(c)
            s.commit()


def _description(desc: str, sc: Script, video: Video, hashtags: str) -> str:
    parts = [desc.strip()]
    if (sc.variety or {}).get("from_long"):
        parts.insert(0, f"▶ Vídeo completo: {sc.variety['from_long']}")
    try:  # vídeo longo: episódio anterior + playlist da série (maratona) + o Short de origem
        from .longform import series_block
        parts.append(series_block(sc, video))
    except Exception as e:  # noqa: BLE001
        log.warning("links da série: %s", e)
    chapters = (video.assets or {}).get("chapters") or []
    if len(chapters) >= 3:
        fmt = lambda x: f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{int(x % 60):02d}" if x >= 3600 else f"{int(x // 60)}:{int(x % 60):02d}"  # noqa: E731
        parts.append("Capítulos:\n" + "\n".join(f"{fmt(c['start'])} {c['title']}" for c in chapters))
    srcs = [s.get("url") for s in (sc.sources or []) if s.get("url")][:6]
    if srcs and "Fontes" not in desc:
        parts.append("Fontes:\n" + "\n".join(f"• {u}" for u in srcs))
    # créditos só das fotos que exigem atribuição (CC BY/BY-SA, em canais que aceitam); o resto dispensa
    from .visuals import FREE_MARKERS
    need = []
    for p in (video.assets or {}).get("images") or []:
        if not isinstance(p, dict) or p.get("kind") != "real" or p.get("source") in ("nasa", "pexels", "cleveland", "smithsonian"):
            continue
        lic = (p.get("license") or "").lower()
        if lic and not any(m in lic for m in FREE_MARKERS):
            line = f"• {p.get('credit') or 'Autor desconhecido'} — {p.get('license')} — {p.get('page') or p.get('url')}"
            if line not in need:
                need.append(line)
    if need:
        parts.append("Créditos das imagens:\n" + "\n".join(need[:15]))
    parts.append(hashtags)
    return "\n\n".join(p for p in parts if p)


# ================================================================ tarefas

UPLOADERS = {"youtube": yt_upload}
METRICS = {"youtube": yt_metrics}


@handler("publish")
def job_publish(ctx: JobContext) -> dict:
    with session() as s:
        pub = s.get(Publication, ctx.ref_id)
        acc = s.get(Account, pub.account_id)
        video = s.get(Video, pub.video_id)
        sc = s.get(Script, video.script_id)
        ch = s.get(Channel, pub.channel_id)
        qa = (video.assets or {}).get("qa") or {}
        if qa and not qa.get("passed") and not ctx.payload.get("force"):
            pub.status, pub.error = "failed", "Vídeo reprovado no inspetor de qualidade (aprove manualmente em Vídeos)"
            s.add(pub)
            s.commit()
            raise RuntimeError(pub.error)
        pub.status = "uploading"
        s.add(pub)
        s.commit()
    ctx.update(0.05, f"Publicando no {acc.platform}")
    try:
        ext, url = UPLOADERS[acc.platform](acc, pub, video, sc, ch, ctx)
    except Exception as e:
        with session() as s:
            p = s.get(Publication, pub.id)
            p.status, p.error = "failed", str(e)[:2000]
            s.add(p)
            s.commit()
        raise
    live = go_live_at(pub) if acc.platform == "youtube" else None
    with session() as s:
        p = s.get(Publication, pub.id)
        p.status, p.external_id, p.url, p.published_at, p.error = "published", ext, url, live or now(), ""
        s.add(p)
        v = s.get(Video, video.id)
        v.status = "published"
        s.add(v)
        s.commit()
    ctx.log(f"Publicado: {url or ext}")
    from . import notify
    if live:
        notify.safe(f"📅 Enviado · {ch.name}", f"{pub.title.replace('#Shorts', '').strip()}\nVai ao ar às {live.astimezone():%H:%M}",
                    event="published", tags=["calendar"], click=url or "")
    else:
        notify.safe(f"✅ No ar · {ch.name}", pub.title.replace("#Shorts", "").strip(), event="published", tags=["white_check_mark"],
                    click=url or "")
    if acc.platform == "youtube":
        from .community import after_publish
        after_publish(pub.id, pub.channel_id)
        if video.format == "long":  # maratona: episódio anterior → este, playlist e o Short campeão de origem → este
            from .jobs import enqueue as _enq
            _enq("binge_links", title=f"Links da série: {pub.title[:60]}", channel_id=pub.channel_id, ref_id=pub.id)
        from .focus import paused
        if video.format == "long" and not (sc.variety or {}).get("from_long") and not paused(pub.channel_id):
            from .jobs import enqueue
            enqueue("shorts_from_long", title=f"Shorts a partir do longo: {pub.title[:60]}", channel_id=pub.channel_id,
                    ref_id=video.id)
    return {"url": url, "id": ext}


@handler("collect_metrics")
def job_collect_metrics(ctx: JobContext) -> dict:
    from .analytics import generate_insights
    only = ctx.channel_id  # sincronização manual de um canal (botão em Métricas); sem canal = todos
    with session() as s:
        q = select(Account)
        if only:
            q = q.where(Account.channel_id == only)
        accs = s.exec(q).all()
    total = 0
    if only and any(a.platform == "youtube" and a.credentials for a in accs):
        ctx.update(0.02, "Atualizando inscritos e views do canal")
        try:
            from .channels import sync_profile
            from .growth import ypp_cached
            sync_profile(only)
            with session() as s:
                ypp_cached(s.get(Channel, only), 0)
        except Exception as e:  # noqa: BLE001
            ctx.log(f"Perfil do canal: {e}")
    for n, acc in enumerate(accs):
        if not acc.credentials or acc.platform not in METRICS:
            continue
        with session() as s:
            pubs = s.exec(select(Publication).where(Publication.account_id == acc.id,
                                                    Publication.status == "published")).all()
        if acc.platform == "youtube":
            # vídeos importados (sem login) do mesmo canal passam a ser medidos pela conta conectada
            with session() as s:
                pubs += s.exec(select(Publication).where(Publication.channel_id == acc.channel_id,
                                                         Publication.platform == "youtube",
                                                         Publication.account_id != acc.id,
                                                         Publication.status == "published")).all()
        ctx.update(n / max(1, len(accs)), f"Coletando métricas: {acc.platform} {acc.display_name}")
        try:
            data = METRICS[acc.platform](acc, pubs)
        except Exception as e:  # noqa: BLE001
            ctx.log(f"{acc.platform}: {e}")
            continue
        if acc.platform == "youtube":  # origens de tráfego do canal (views × engajadas; anúncios não contam p/ YPP)
            try:
                traffic = yt_traffic(acc)
                with session() as s:
                    c = s.get(Channel, acc.channel_id)
                    if c:
                        c.stats = {**(c.stats or {}), "traffic": traffic}
                        s.add(c)
                        s.commit()
            except Exception as e:  # noqa: BLE001
                ctx.log(f"Origens de tráfego: {e}")
        if acc.platform == "youtube":  # curva de retenção segundo a segundo
            from .retention import collect_curves
            for vid_id, curve in collect_curves(acc, pubs).items():
                data.setdefault(vid_id, {})["retention_curve"] = curve
        with session() as s:
            for p in pubs:
                m = data.get(p.external_id)
                if not m:
                    continue
                s.add(MetricSnapshot(publication_id=p.id, channel_id=p.channel_id, platform=p.platform,
                                     **{k: v for k, v in m.items() if k in MetricSnapshot.model_fields}, raw=m))
                total += 1
            s.commit()
    ctx.log(f"{total} leituras de métricas salvas")
    with session() as s:
        chans = [only] if only else [c.id for c in s.exec(select(Channel)).all()]
    from .retention import generate_retention_insights
    for cid in chans:
        try:
            with session() as s:
                last = s.exec(select(Insight).where(Insight.channel_id == cid, Insight.kind == "retention")
                              .order_by(Insight.created_at.desc())).first()
            if not last or (now() - last.created_at.replace(tzinfo=now().tzinfo)).total_seconds() > 20 * 3600:
                lessons = generate_retention_insights(cid)
                if lessons:
                    ctx.log(f"Canal {cid}: {len(lessons)} lições de retenção atualizadas")
        except Exception as e:  # noqa: BLE001
            ctx.log(f"Retenção canal {cid}: {e}")
        try:
            generate_insights(cid, min_hours=20)
        except Exception as e:  # noqa: BLE001
            ctx.log(f"Aprendizados canal {cid}: {e}")
    return {"snapshots": total}
