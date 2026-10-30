"""Tarefas da fila do Modo História.

story_episode  (leve)   escreve o episódio (1 pedido ao LLM) + checagem frase a frase → Script; enfileira story_assets
story_assets   (leve)   gera as imagens novas que cabem na cota e guarda no banco; sem banco e sem cota → espera a cota
story_render   (pesada) Video normal + render + inspetor + agendamento (mesmo fim do render_video)
story_pregen   (leve)   gasta a sobra da cota do dia crescendo os bancos (folhas de personagem primeiro)
story_seed     (leve)   copia as imagens do protótipo aprovado para o banco do Ouro do Passado

Ganchos para o resto do sistema (o líder liga — ver relatório):
- wants_story(ch, fmt, idea) / divert(ctx, ch, idea, fmt): piloto automático manda uma fração das pautas para cá
"""
from __future__ import annotations

import random
import time

from sqlmodel import select

from ..db import session
from ..jobs import JobContext, enqueue, handler
from ..models import Channel, Idea, Script, Video
from . import bank, bible as B, planner, providers, writer

DEFAULT_SHARE = {"short": 0.25, "long": 0.15}  # fração dos vídeos do piloto que viram Modo História
YPP_WINDOW, YPP_MAX = 10, 0.34  # nunca mais de ~1/3 dos últimos 10 roteiros do canal no mesmo formato


def _channel(cid: int) -> Channel:
    with session() as s:
        ch = s.get(Channel, cid)
    if not ch:
        raise RuntimeError(f"Canal {cid} não existe")
    return ch


def _wait_for_quota(ctx: JobContext, why: str) -> dict:
    """Sem imagem possível agora: agenda uma cópia desta tarefa para depois que a cota da Cloudflare zera
    (00:00 UTC = 21:00 Brasília) — a fila só pega tarefas com _not_before vencido. Nunca falha o episódio."""
    until = providers.cf_reset_at().timestamp() + 600
    waits = int(ctx.payload.get("_story_wait", 0)) + 1
    if waits > 3:
        raise RuntimeError(f"{why} (esperou {waits - 1} vezes)")
    from ..models import Job
    with session() as s:
        j = s.get(Job, ctx.job_id)
        kind, title, cid, ref = j.kind, j.title, j.channel_id, j.ref_id
    payload = {k: v for k, v in ctx.payload.items() if not k.startswith("_")}
    payload.update(_not_before=until, _story_wait=waits)
    nj = enqueue(kind, title=title, channel_id=cid, ref_id=ref, payload=payload)
    ctx.log(f"{why} — tarefa #{nj.id} tenta de novo às {time.strftime('%H:%M', time.localtime(until))}")
    return {"waiting": True, "next_job": nj.id}


# ================================================================ decisão do piloto

def story_share(ch: Channel, fmt: str) -> float:
    b = B.load(ch.slug)
    if b.get("enabled") is False:
        return 0.0
    try:
        return float(b.get("share", DEFAULT_SHARE.get(fmt, 0.2)))
    except (TypeError, ValueError):
        return DEFAULT_SHARE.get(fmt, 0.2)


def ready(ch: Channel) -> tuple[bool, str]:
    """O canal consegue produzir um episódio agora? (protagonista com poses no banco, ou cota para gerar)."""
    b = B.load(ch.slug)
    if not b.get("characters"):
        return False, "bíblia sem personagens"
    hero = b["characters"][0]["id"]
    has_bank = bool(bank.find(ch.slug, "pose", char=hero, limit=1)) or bool(bank.find(ch.slug, "scene", char=hero, limit=1))
    if has_bank:
        return True, "banco pronto"
    if providers.PROVIDERS["cf_lucid"].available() or providers.images_left_today() >= 6:
        return True, "banco vazio, mas há cota para gerar"
    return False, "banco vazio e sem cota de imagem hoje"


def wants_story(ch: Channel, fmt: str, idea: Idea | None = None) -> bool:
    """Sorteio com freio: fração configurada por canal, nunca acima de ~1/3 dos últimos roteiros (YPP), e só se o
    canal está pronto (banco/cota). A pauta precisa ser um evento/caso narrável (não lista/comparação)."""
    share = story_share(ch, fmt)
    if share <= 0:
        return False
    if B.load(ch.slug).get("dedicated"):  # canal só de histórias (ex.: Zé na Fuga): toda pauta vira episódio
        return True
    with session() as s:
        rows = s.exec(select(Script).where(Script.channel_id == ch.id).order_by(Script.id.desc()).limit(YPP_WINDOW)).all()
    recent = [(r.variety or {}).get("structure") for r in rows]
    if recent and recent.count("historia") / max(1, len(recent)) >= YPP_MAX:
        return False
    if recent[:1] == ["historia"] and writer.open_arc(ch.slug) is None:
        return False  # dois seguidos só quando é continuação de arco
    if idea is not None and any(t in (idea.tags or []) for t in ("mito_verdade",)):
        return False
    ok, _ = ready(ch)
    if not ok:
        return False
    if writer.open_arc(ch.slug):  # arco aberto: a parte seguinte tem prioridade (o público espera)
        return random.random() < min(0.9, share * 2.5)
    return random.random() < share


def divert(ctx: JobContext, ch: Channel, idea: Idea | None, fmt: str) -> dict:
    """Chamado pelo write_script: troca o roteiro normal por um episódio (mesmo auto_render/publish_at).
    Canal dedicado: o horário de Short escreve a próxima parte da série certa; o de longo vira a versão completa."""
    from . import seasons
    if seasons.dedicated(ch) and fmt == "long":
        from . import series as S
        a = next((x for x in S.arcs(ch.slug) if x.get("status") == "closed" and not x.get("long")), None)
        if a:
            return {"long_script": S.make_long(ch, a, ctx.log)}
        ctx.log("Canal de séries: o longo da semana é a versão completa de uma série terminada — nenhuma terminou ainda")
        return {"msg": "sem série completa para o longo"}
    payload = {k: ctx.payload[k] for k in ("auto_render", "publish_at") if ctx.payload.get(k)}
    payload.update(format=fmt, idea_id=idea.id if idea else None)
    j = enqueue("story_episode", title=f"Modo História: {ch.name}", channel_id=ch.id, ref_id=idea.id if idea else None,
                payload=payload)
    ctx.log(f"Esta pauta virou episódio do Modo História (tarefa #{j.id})")
    return {"story_job": j.id}


# ================================================================ tarefas

@handler("story_episode")
def job_story_episode(ctx: JobContext) -> dict:
    ch = _channel(ctx.channel_id)
    b = B.load(ch.slug)
    p = ctx.payload
    fmt = p.get("format") or "short"
    from .. import variety
    from . import seasons
    if fmt == "short" and (p.get("series_mode") or seasons.dedicated(ch)) and not p.get("topic"):
        return _series_episode(ctx, ch, b)
    arc = None if (p.get("new_arc") or p.get("topic")) else writer.open_arc(ch.slug)
    idea = None
    iid = p.get("idea_id") or ctx.ref_id
    if arc and arc.get("idea_id"):
        iid = arc["idea_id"]
    if iid:
        with session() as s:
            idea = s.get(Idea, iid)
    if idea is None and not p.get("topic") and not arc:
        with session() as s:
            idea = s.exec(select(Idea).where(Idea.channel_id == ch.id, Idea.status.in_(["approved", "new"]),
                                             Idea.fact_status == "verified").order_by(Idea.score.desc())).first()
        if idea is None:
            enqueue("discover_ideas", title="Buscar pautas (Modo História)", channel_id=ch.id, payload={"count": 6, "format": fmt})
            return {"msg": "sem pauta verificada — buscando pautas"}
    ctx.update(0.1, "Escrevendo o episódio" + (f" (parte {len(arc['parts']) + 1} de “{arc.get('title')}”)" if arc else ""))
    plan = variety.plan(ch, fmt)
    ep = writer.write_episode(ch, b, fmt, idea=idea, topic=p.get("topic", ""), arc=arc, plan=plan, log=ctx.log)
    ctx.log(f"Episódio: {ep.get('title')} · {len(ep['beats'])} beats · {sum(len(x['text'].split()) for x in ep['beats'])} palavras"
            f" · estilo {ep.get('episode_style')} · missão {ep['mission'].get('title')}")
    story = {k: v for k, v in ep.items() if k != "beats"}
    var = {**plan, "structure": "historia", "series": b.get("series_title"), "music_mood": "suspense dark cinematic",
           "loop": False, "story": story}
    with session() as s:
        sc = Script(channel_id=ch.id, idea_id=idea.id if idea else None, format=fmt, title=(ep.get("title") or "Episódio")[:200],
                    hook=ep["beats"][0]["text"], scenes=ep["beats"], description=ep.get("description") or "",
                    tags=ep.get("tags") or [], hashtags=ep.get("hashtags") or [], thumbnail_text=ep.get("thumbnail_text") or "",
                    sources=(idea.sources if idea and idea.sources else ep.get("sources") or []), variety=var, status="approved")
        s.add(sc)
        if idea and idea.status in ("new", "approved"):
            db_idea = s.get(Idea, idea.id)
            db_idea.status = "scripted"
            s.add(db_idea)
        s.commit()
        s.refresh(sc)
    ctx.update(0.55, "Checando os fatos frase por frase")
    check_story_claims(ch, sc.id, idea, ctx.log)
    arc_id = (arc or {}).get("id") or f"arc_{int(time.time())}"
    writer.record_part(ch.slug, arc_id, {
        "n": ep["part"], "script_id": sc.id, "title": ep.get("title"), "summary": ep.get("memory") or "",
        "cliffhanger": ep.get("cliffhanger") or "", "next": ep.get("next_hook") or "", "mission": ep["mission"].get("title"),
        "style": ep.get("episode_style"), "widgets": sorted({(x.get("widget") or {}).get("type") for x in ep["beats"] if x.get("widget")}),
        "created": time.time()}, arc_title=ep.get("arc_title") or "", idea_id=idea.id if idea else None, topic=ep.get("topic", ""),
        max_parts=int(b.get("max_parts") or (4 if fmt == "short" else 1)))
    nxt = {k: p[k] for k in ("auto_render", "publish_at") if p.get(k)}
    enqueue("story_assets", title=f"Imagens: {sc.title}", channel_id=ch.id, ref_id=sc.id, payload=nxt)
    return {"script_id": sc.id, "part": ep["part"]}




def _series_episode(ctx: JobContext, ch: Channel, b: dict) -> dict:
    """Canal dedicado: escreve a PRÓXIMA parte da série certa (plano + memória real das partes anteriores)."""
    from .. import variety
    from . import series as S
    cl = S.claim_next(ch, ctx.payload.get("idea_id") or ctx.ref_id)
    if not cl:
        motivos = "; ".join(f"{a['title']}: {S.blocked(a)}" for a in S.open_series(ch.slug)) or "sem pauta-série pronta"
        ctx.log(f"Nada para escrever agora ({motivos})")
        return {"msg": motivos}
    arc, n = cl
    plan_s = arc["plan"]
    try:
        b2 = S.bible_with_cast(b, arc)
        with session() as s:
            idea = s.get(Idea, arc["idea_id"]) if arc.get("idea_id") else None
        ctx.update(0.1, f"Escrevendo “{plan_s['title']}” — parte {n} de {plan_s['parts_count']}")
        vplan = variety.plan(ch, "short")
        block = S.series_block(arc, n, b2)
        arc_w = {**arc, "parts": [x for x in arc.get("parts") or [] if x["n"] < n]}
        ep = writer.write_episode(ch, b2, "short", idea=idea, topic=arc.get("topic", ""), arc=arc_w, plan=vplan, log=ctx.log,
                                  series_block=block, research_ok=bool(plan_s.get("real_history")) or bool(plan_s["parts"][n - 1].get("tip")),
                                  research_query="" if plan_s.get("real_history") else
                                  f"{plan_s['parts'][n - 1].get('tip')} dica defesa civil cruz vermelha como se preparar")
        cur = plan_s["parts"][n - 1]
        ep.update(part=n, title=f"{plan_s['title']} — Parte {n}", mission=plan_s["mission"], series_arc=arc["id"],
                  series_title=plan_s["title"], parts_total=plan_s["parts_count"], decision=cur.get("decision"),
                  end_label=S.end_label(arc, n, ch), arc_title=plan_s["title"])
        ep["clock"] = {**(ep.get("clock") or {}), "elapsed_before": float(arc.get("clock_elapsed") or 0)}
        ctx.log(f"Parte {n}: {len(ep['beats'])} falas · {sum(len(x['text'].split()) for x in ep['beats'])} palavras"
                + (f" · decisão A/B: {cur['decision']['question']}" if cur.get("decision") else ""))
        story = {k: v for k, v in ep.items() if k != "beats"}
        var = {**vplan, "structure": "historia", "series": plan_s["title"], "music_mood": "suspense dark cinematic", "loop": False,
               "story": story}
        with session() as s:
            sc = Script(channel_id=ch.id, idea_id=idea.id if idea else None, format="short", title=ep["title"][:200],
                        hook=ep["beats"][0]["text"], scenes=ep["beats"], description=ep.get("description") or "",
                        tags=ep.get("tags") or [], hashtags=ep.get("hashtags") or [], thumbnail_text=ep.get("thumbnail_text") or "",
                        sources=(idea.sources if idea and idea.sources else ep.get("sources") or []), variety=var, status="approved")
            s.add(sc)
            s.commit()
            s.refresh(sc)
        vc = S.vote_comment(sc)
        if vc:
            with session() as s:
                db = s.get(Script, sc.id)
                db.variety = {**(db.variety or {}), "pinned_comment": vc}
                s.add(db)
                s.commit()
        if plan_s.get("real_history"):
            ctx.update(0.55, "Checando os fatos (série de história real)")
            check_story_claims(ch, sc.id, idea, ctx.log)
        elif any(x.get("tip") for x in ep["beats"]):
            ctx.update(0.55, "Checando a dica real de sobrevivência")
            check_story_claims(ch, sc.id, idea, ctx.log, only_tips=True)
        S.after_written(ch, arc, n, ep, sc.id)
    except BaseException:
        S.release(ch.slug, arc["id"])
        raise
    enqueue("story_assets", title=f"Imagens: {sc.title}", channel_id=ch.id, ref_id=sc.id,
            payload={"auto_render": True, "series_part": True})
    return {"script_id": sc.id, "series": plan_s["title"], "part": n}


def check_story_claims(ch: Channel, script_id: int, idea: Idea | None, log=print, only_tips: bool = False) -> dict:
    """Checagem frase a frase só nas falas FACTUAIS (narrador e aparelhos: jornal, rádio, edital...). Falas de
    personagens ficcionais são moldura e não são "corrigidas" (antes o checador trocava "Dona Maria" por "alguém").
    A chamada final (segue/siga) é preservada mesmo quando a frase do gancho é corrigida."""
    import re
    from .. import content
    with session() as s:
        sc = s.get(Script, script_id)
    chars = {c["id"] for c in B.load(ch.slug).get("characters") or []}
    if only_tips:  # ficção: só a dica real (precisa ser verdadeira e segura)
        tips = [i for i, b in enumerate(sc.scenes or []) if b.get("tip")]
        # o roteirista às vezes marca a frase que ANUNCIA a dica: confere também a seguinte
        idx = sorted({j for i in tips for j in (i, i + 1) if j < len(sc.scenes or []) and
                      (sc.scenes[j].get("speaker", "narrador") not in chars or j == i)})
    else:
        idx = [i for i, b in enumerate(sc.scenes or []) if b.get("speaker", "narrador") not in chars]
    if not idx:
        return {}
    srcs = sc.sources
    if only_tips:
        try:
            from .. import research
            q = " ".join(sc.scenes[i]["text"] for i in idx)[:160]
            srcs = [{"title": x.get("title", ""), "url": x["url"]} for x in research.gather_dossier(q, max_sources=4)["sources"]]
        except Exception:  # noqa: BLE001
            srcs = []
    tmp = Script(channel_id=sc.channel_id, title=sc.title, scenes=[sc.scenes[i] for i in idx], variety=sc.variety,
                 sources=srcs)
    try:
        r = content.check_claims(ch, tmp, idea)
    except Exception as e:  # noqa: BLE001
        log(f"Checagem frase a frase não rodou ({e}) — revise os fatos")
        return {}
    scenes = [dict(x) for x in sc.scenes]
    cta = re.compile(r"\b(segue|siga|inscreva|se inscreve)\b", re.I)
    fixed = []
    if r.get("sources", 0) >= 2:  # sem fontes de verdade, "corrigir" só estraga o texto
        for k, txt in r["fixes"].items():
            i = idx[k]
            old = scenes[i].get("text", "")
            cta_s = [x for x in re.split(r"(?<=[.!?…])\s+", old) if cta.search(x)]
            if cta_s and not cta.search(txt):
                txt = (txt.rstrip() + " " + " ".join(cta_s)).strip()
            scenes[i] = {**scenes[i], "text": txt}
            fixed.append(i + 1)
    items = r["items"]
    for c in items:  # número da cena no roteiro inteiro
        if isinstance(c.get("scene"), int) and 1 <= c["scene"] <= len(idx):
            c["scene"] = idx[c["scene"] - 1] + 1
    bad = [c for c in items if c.get("verdict") in ("sem_fonte", "contradiz")]
    with session() as s:
        db = s.get(Script, script_id)
        db.scenes = scenes
        db.claims = {"sig": content.scenes_sig(scenes), "items": items, "fixed": len(fixed),
                     "unresolved": [c for c in bad if c.get("scene") not in fixed], "sources": r.get("sources", 0)}
        s.add(db)
        s.commit()
    log(f"Fatos: {len(items) - len(bad)}/{len(items)} confirmados nas fontes ({r.get('sources', 0)} fontes)"
        + (f" · cenas corrigidas: {fixed}" if fixed else ""))
    return r


@handler("story_assets")
def job_story_assets(ctx: JobContext) -> dict:
    with session() as s:
        sc = s.get(Script, ctx.ref_id)
    if sc is None:
        return {"msg": "roteiro sumiu"}
    ch = _channel(sc.channel_id)
    b = B.load(ch.slug)
    from .engine import episode_of
    ep = episode_of(sc)
    pl = planner.plan(ch.slug, b, ep, sc.format or "short", seed=sc.id)
    ctx.log(f"Plano: {len(pl['needs'])} imagens possíveis, {pl['new']} novas agora (alvo {planner.target_new(sc.format, len(ep['beats']))}"
            f", capacidade de hoje {providers.images_left_today()})")
    if pl["new"]:
        r = planner.generate_needs(ch.slug, b, pl, log=ctx.log, check=ctx.check)
        ctx.log(f"Novas: {r['made']} · falharam/sem cota: {r['failed']} (essas vêm do banco)")
    vis, _, missing = planner.resolve(ch.slug, b, ep, pl, episode_no=sc.id, seed=sc.id)
    if any(v is None for v in vis):
        return _wait_for_quota(ctx, "Sem imagens no banco do canal e sem cota agora")
    with session() as s:
        db = s.get(Script, sc.id)
        v = dict(db.variety or {})
        v["story"] = {**(v.get("story") or {}), "asset_plan": pl}
        db.variety = v
        s.add(db)
        s.commit()
    if ctx.payload.get("auto_render", True):
        enqueue("story_render", title=f"Vídeo (história): {sc.title}", channel_id=ch.id, ref_id=sc.id,
                payload={k: ctx.payload[k] for k in ("publish_at", "publish_long") if ctx.payload.get(k)})
    return {"new": pl["new"], "missing": len(missing)}


@handler("story_render")
def job_story_render(ctx: JobContext) -> dict:
    """Mesmo fim do render_video (Video, inspetor, agendamento), com o motor do Modo História."""
    from .engine import produce_story
    with session() as s:
        sc = s.get(Script, ctx.ref_id)
        ch = s.get(Channel, sc.channel_id)
        old = s.get(Video, ctx.payload["_video_id"]) if ctx.payload.get("_video_id") else None
        if old and old.status == "rendering":
            video = old
        else:
            video = Video(channel_id=ch.id, script_id=sc.id, format=sc.format, status="rendering")
            s.add(video)
            s.commit()
            s.refresh(video)
    ctx.save_payload(_video_id=video.id)
    try:
        out = produce_story(ch, sc, video.id, ctx)
    except BaseException as e:
        with session() as s:
            v = s.get(Video, video.id)
            if v:
                if isinstance(e, Exception):
                    v.status, v.error = "failed", str(e)[:2000]
                    s.add(v)
                else:
                    s.delete(v)
                s.commit()
        raise
    with session() as s:
        v = s.get(Video, video.id)
        v.status = "ready"
        v.path, v.thumbnail_path, v.duration, v.assets = out["path"], out["thumbnail"], out["duration"], out["assets"]
        s.add(v)
        db_sc = s.get(Script, sc.id)
        if db_sc:
            db_sc.status = "produced"
            s.add(db_sc)
        if sc.idea_id:
            idea = s.get(Idea, sc.idea_id)
            if idea:
                idea.status = "produced"
                s.add(idea)
        s.commit()
    # memória da série: liga a parte ao vídeo
    try:
        d = writer.series(ch.slug)
        for a in d.get("arcs") or []:
            for p in a.get("parts") or []:
                if p.get("script_id") == sc.id:
                    p["video_id"] = video.id
        writer._save_series(ch.slug, d)
    except Exception:  # noqa: BLE001
        pass
    from ..inspector import run_inspection
    try:
        qa = run_inspection(video.id, ctx)
    except Exception as e:  # noqa: BLE001
        ctx.log(f"Inspetor falhou ({e}) — vídeo marcado para revisão")
        qa = {"passed": False}
    st = (sc.variety or {}).get("story") or {}
    if st.get("series_arc") and not st.get("long_of_series"):
        # parte de série: a agenda é sempre em ordem (a parte k nunca sai antes da k-1) — quem agenda é series.py
        from . import series as S
        if qa.get("passed"):
            n = S.schedule_ready(ch, ctx.log)
            ctx.log(f"Série: {n} parte(s) agendada(s) em ordem" if n else "Série: esperando a parte anterior ficar pronta para agendar")
        else:
            ctx.log("Parte REPROVADA no inspetor — a série espera você revisar em Vídeos (as próximas não passam na frente)")
    elif ctx.payload.get("publish_long") or st.get("long_of_series"):
        if qa.get("passed"):
            from .. import posting_times
            from ..models import now as _now
            from ..pipeline import _schedule_publication
            from datetime import timedelta
            when = posting_times.next_free(ch, _now() + timedelta(hours=3), "long")
            _schedule_publication(video.id, when.isoformat(), ctx)
    elif ctx.payload.get("publish_at"):
        if qa.get("passed"):
            from ..pipeline import _schedule_publication
            _schedule_publication(video.id, ctx.payload["publish_at"], ctx)
        else:
            ctx.log("Vídeo REPROVADO no inspetor — não foi agendado. Revise em Vídeos.")
    try:
        from .. import notify
        notify.safe(f"🎬 Episódio pronto · {ch.name}", sc.title, event="ready" if qa.get("passed") else "review", tags=["clapper"])
    except Exception:  # noqa: BLE001
        pass
    return {"video_id": video.id, "qa": qa.get("passed")}


@handler("story_pregen")
def job_story_pregen(ctx: JobContext) -> dict:
    """Cresce os bancos com a cota que sobrou: folhas de personagem que faltam, depois cenários da bíblia."""
    from .bible import COMMON_POSES
    max_n = int(ctx.payload.get("max", 40))
    only = ctx.payload.get("channel_id") or ctx.channel_id
    with session() as s:
        chans = [c for c in s.exec(select(Channel)).all() if not only or c.id == only]
    todo = []
    if ctx.payload.get("regen") and chans:  # refazer UM asset (mesmo personagem/pose ou lugar, outra semente)
        ch = chans[0]
        b = B.load(ch.slug)
        a = bank.get(ch.slug, ctx.payload["regen"]) or {}
        c = B.character(b, a.get("char", "")) if a.get("char") else None
        if a.get("type") == "pose" and c:
            need = {"type": "pose", "char": c["id"], "pose": a.get("pose") or "front", "size": (768, 1024), "kind": "sheet",
                    "tags": [c["id"]], "prompt": B.pose_prompt(b, c, a.get("pose") or "front"), "seed": random.randint(1, 2 ** 30)}
        elif a.get("prompt"):
            need = {"type": a["type"], "size": tuple(a.get("size") or (720, 1280)), "kind": "location" if a["type"] == "location" else "scene",
                    "tags": a.get("tags") or [], "prompt": a["prompt"], "seed": random.randint(1, 2 ** 30), "char": a.get("char", ""),
                    "pose": a.get("pose", "")}
        else:
            return {"msg": "asset sem prompt (veio do protótipo) — gere um novo pelo episódio"}
        pl = {"needs": [{**need, "beat": 0, "role": "main", "generate": True}]}
        r = planner.generate_needs(ch.slug, b, pl, log=ctx.log, check=ctx.check)
        if not r["made"]:
            bank.update(ch.slug, ctx.payload["regen"], disabled=False)
            ctx.log("Sem cota agora — o asset antigo voltou a valer")
        return r
    for ch in chans:
        b = B.load(ch.slug)
        if b.get("enabled") is False:
            continue
        boot = bool(ctx.payload.get("bootstrap"))
        for c in (b.get("characters") or [])[:1 if boot else None]:
            have = {a.get("pose") for a in bank.find(ch.slug, "pose", char=c["id"], limit=60)}
            if boot and len(have) >= 4:
                continue  # partida: só o protagonista, só até ter 4 poses
            for pose in (b.get("poses") or list(COMMON_POSES))[:4 if boot else None]:
                if not any(a.get("pose") == pose for a in bank.find(ch.slug, "pose", char=c["id"], limit=40)):
                    pri = 100 if c is b["characters"][0] else 80
                    todo.append((pri - (b.get("poses") or []).index(pose) if pose in (b.get("poses") or []) else pri, ch, b, {
                        "type": "pose", "char": c["id"], "pose": pose, "size": (768, 1024), "kind": "sheet", "tags": [c["id"]],
                        "prompt": B.pose_prompt(b, c, pose), "seed": int(c.get("seed") or 1) + planner._seed(pose) % 997}))
        have_tags = {t for a in bank.load(ch.slug) if a["type"] == "location" for t in a.get("tags") or []}
        for loc in ([] if boot else b.get("locations") or []):
            key = loc.split(" with ")[0].lower()
            if key not in have_tags:
                todo.append((40, ch, b, {"type": "location", "size": (720, 1280), "kind": "location", "tags": [key],
                                         "prompt": B.location_prompt(b, loc), "place": key}))
    todo.sort(key=lambda x: -x[0])
    made = 0
    for _, ch, b, need in todo[:max_n]:
        if providers.images_left_today() + planner._lucid_left() <= 0:
            ctx.log("Cota de imagens do dia acabou")
            break
        ctx.update(made / max(1, min(max_n, len(todo))), f"{ch.name}: {need['type']} {need.get('char', '')} {need.get('pose', need.get('place', ''))}")
        pl = {"needs": [{**need, "beat": 0, "role": "main", "generate": True}]}
        r = planner.generate_needs(ch.slug, b, pl, log=ctx.log, check=ctx.check)
        made += r["made"]
    return {"made": made, "pending": max(0, len(todo) - made)}


@handler("story_seed")
def job_story_seed(ctx: JobContext) -> dict:
    ctx.update(0.2, "Copiando o protótipo aprovado para o banco do Ouro do Passado")
    r = bank.seed_prototype()
    ctx.log(f"{r['added']} assets adicionados · {r['stats']}")
    return r
