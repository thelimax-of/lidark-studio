"""Tarefas da fila: pautas → nota → checagem → roteiro → revisão → vídeo → publicação."""
from __future__ import annotations

import logging

from sqlmodel import select

from . import content
from .db import session
from .jobs import JobContext, enqueue, handler
from .models import Channel, Idea, Script, Video

log = logging.getLogger("lidark.pipeline")


def _channel(cid: int) -> Channel:
    with session() as s:
        ch = s.get(Channel, cid)
        if not ch:
            raise RuntimeError(f"Canal {cid} não existe")
        return ch


# ================================================================ PAUTAS

@handler("discover_ideas")
def job_discover(ctx: JobContext) -> dict:
    ch = _channel(ctx.channel_id)
    p = ctx.payload
    ctx.update(0.05, "Buscando inspiração na internet")
    from . import growth
    camp = next((c for c in growth.ensure_campaigns(ch) if c.get("id") == p.get("campaign")), None)
    act = camp or growth.active_campaign(ch)
    ideas = content.discover_ideas(ch, p.get("count", 8), p.get("seed", ""), p.get("format", "short"), camp)
    ctx.log(f"{len(ideas)} pautas propostas pela IA")
    created = []
    with session() as s:
        for it in ideas:
            idea = Idea(channel_id=ch.id, title=it.get("title", "")[:200], angle=it.get("angle", ""),
                        summary=it.get("summary", ""), format=p.get("format", "short"),
                        origin="manual" if p.get("seed") else "auto",
                        tags=([it.get("enem_link", "")] if it.get("enem_link") else []) +
                             ([growth.campaign_tag(act)] if act and (camp or it.get("campaign")) else []) +
                             ([f"de_short:{it['from_short']}"[:120]] if it.get("from_short") else []))
            s.add(idea)
            s.commit()
            s.refresh(idea)
            created.append(idea.id)
    for i, iid in enumerate(created):
        ctx.update(0.1 + 0.9 * i / max(1, len(created)), f"Avaliando pauta {i + 1}/{len(created)}")
        _score(ch, iid, ctx)
    if p.get("verify", True):
        for iid in created:
            enqueue("verify_idea", title="Checar fatos da pauta", channel_id=ch.id, ref_id=iid)
    return {"ideas": created}


def _score(ch: Channel, idea_id: int, ctx: JobContext | None = None) -> None:
    with session() as s:
        idea = s.get(Idea, idea_id)
    try:
        r = content.score_idea(ch, idea.title, idea.angle, idea.summary)
    except Exception as e:  # noqa: BLE001
        if ctx:
            ctx.log(f"Falha ao avaliar '{idea.title}': {e}")
        return
    with session() as s:
        idea = s.get(Idea, idea_id)
        idea.score = r["score"]
        idea.score_breakdown = {"criteria": r["criteria"], "raw": r["raw_score"],
                                "improvements": r["improvements"], "better_title": r["better_title"]}
        idea.score_reason = r["reason"]
        s.add(idea)
        s.commit()
    if ctx:
        ctx.log(f"Nota {r['score']} → {idea.title}")


@handler("score_idea")
def job_score(ctx: JobContext) -> dict:
    with session() as s:
        idea = s.get(Idea, ctx.ref_id)
    ch = _channel(idea.channel_id)
    ctx.update(0.2, "Avaliando potencial da pauta")
    _score(ch, idea.id, ctx)
    return {}


@handler("verify_idea")
def job_verify(ctx: JobContext) -> dict:
    with session() as s:
        idea = s.get(Idea, ctx.ref_id)
    ch = _channel(idea.channel_id)
    ctx.update(0.1, "Pesquisando fontes")
    r = content.verify_idea(ch, idea)
    with session() as s:
        idea = s.get(Idea, ctx.ref_id)
        _apply_check(idea, r)
        s.add(idea)
        s.commit()
    ctx.log(f"Checagem: {r['fact_status']} com {len(r['sources'])} fontes"
            + (" — premissa falsa, mas vira pauta mito × verdade" if r.get("debunk") else ""))
    _enforce_facts(ctx.ref_id, ctx)
    return {"fact_status": r["fact_status"]}


def _apply_check(idea: Idea, r: dict) -> None:
    idea.fact_status, idea.facts, idea.sources = r["fact_status"], r["facts"], r["sources"]
    if r.get("corrected_summary"):
        idea.summary = r["corrected_summary"]
    if r.get("debunk"):
        d = r["debunk"]
        idea.angle = f"Mito × verdade — muita gente acredita que {d['myth'][0].lower() + d['myth'][1:]} A verdade: {d['truth']}"
        idea.tags = list(dict.fromkeys((idea.tags or []) + ["mito_verdade"]))


def _enforce_facts(idea_id: int, ctx: JobContext | None = None) -> bool:
    """Pauta que as fontes contradizem ou não confirmam sai do painel. O título fica guardado (oculto)
    só para a IA não propor a mesma pauta de novo. Devolve True se descartou."""
    with session() as s:
        idea = s.get(Idea, idea_id)
        if not idea or idea.fact_status not in ("disputed", "unverified") or idea.status in ("scripted", "produced"):
            return False
        why = "fontes contradizem" if idea.fact_status == "disputed" else "fontes não confirmam"
        idea.status = "discarded"
        idea.score_reason = f"Descartada: {why}. " + (idea.score_reason or "")
        s.add(idea)
        s.commit()
        title = idea.title
    if ctx:
        ctx.log(f"Pauta descartada ({why}): {title}")
    return True


@handler("audit_ideas")
def job_audit_ideas(ctx: JobContext) -> dict:
    """Passa a limpo as pautas: dá nota às que não têm, rechecha as não confirmadas e descarta as falsas."""
    with session() as s:
        q = select(Idea).where(Idea.status.in_(["new", "approved"]))
        if ctx.channel_id:
            q = q.where(Idea.channel_id == ctx.channel_id)
        ids = [i.id for i in s.exec(q).all()]
    stats = {"avaliadas": 0, "checadas": 0, "descartadas": 0, "confirmadas": 0}
    for n, iid in enumerate(ids):
        with session() as s:
            idea = s.get(Idea, iid)
        ch = _channel(idea.channel_id)
        ctx.update(n / max(1, len(ids)), f"Pauta {n + 1}/{len(ids)}: {idea.title[:50]}")
        if idea.fact_status != "verified" and idea.fact_status != "disputed":
            r = content.verify_idea(ch, idea)
            with session() as s:
                db = s.get(Idea, iid)
                _apply_check(db, r)
                s.add(db)
                s.commit()
            stats["checadas"] += 1
            ctx.log(f"Checagem: {r['fact_status']} ({len(r['sources'])} fontes) — {idea.title[:60]}")
        if _enforce_facts(iid, ctx):
            stats["descartadas"] += 1
            continue
        stats["confirmadas"] += 1
        with session() as s:
            idea = s.get(Idea, iid)
        if idea.score is None:
            _score(ch, iid, ctx)
            stats["avaliadas"] += 1
    ctx.log(f"Resumo: {stats}")
    return stats


@handler("manual_idea")
def job_manual_idea(ctx: JobContext) -> dict:
    """O criador escreve a pauta: o sistema pesquisa, valida, melhora e dá nota."""
    with session() as s:
        idea = s.get(Idea, ctx.ref_id)
    ch = _channel(idea.channel_id)
    ctx.update(0.1, "Pesquisando e validando a sua ideia")
    r = content.verify_idea(ch, idea)
    with session() as s:
        idea = s.get(Idea, ctx.ref_id)
        _apply_check(idea, r)
        s.add(idea)
        s.commit()
    if _enforce_facts(idea.id, ctx):  # sua ideia também passa pela regra: sem confirmação nas fontes, sai
        return {"discarded": True}
    ctx.update(0.7, "Dando nota")
    _score(ch, idea.id, ctx)
    return {}


# ================================================================ ROTEIRO

@handler("write_script")
def job_write_script(ctx: JobContext) -> dict:
    with session() as s:
        idea = s.get(Idea, ctx.ref_id)
    ch = _channel(idea.channel_id)
    fmt = ctx.payload.get("format") or idea.format
    ctx.update(0.1, "Pesquisando fontes e escrevendo roteiro")
    from . import growth
    camp = growth.campaign_of(idea, ch)
    extra0 = ctx.payload.get("extra", "")
    if camp:
        extra0 = (extra0 + chr(10) + f"Este vídeo faz parte da campanha \"{camp['name']}\": {camp.get('focus')}").strip()
        from . import enem
        if enem.is_enem(camp):  # campanha de prova: SEO de revisão honesto (sem prometer questão garantida)
            extra0 += chr(10) + enem.seo_rules(fmt)
        ctx.payload["extra"] = extra0
    plan0 = None
    forced = next((str(t)[10:] for t in idea.tags or [] if str(t).startswith("estrutura:")), "")
    if forced and "mito_verdade" not in (idea.tags or []):  # estrutura escolhida na pauta (ex.: pacote ENEM)
        from . import variety as _v
        if fmt in _v.STRUCTURES.get(forced, {}).get("formats", ()):
            plan0 = _v.plan(ch, fmt)
            plan0.update(structure=forced, music_mood=_v.STRUCTURES[forced]["mood"])
    if "mito_verdade" in (idea.tags or []):
        from . import variety as _v
        plan0 = _v.plan(ch, fmt)
        plan0["structure"] = "mito_verdade"
        extra0 = (extra0 + chr(10) + "ESTA PAUTA DESMENTE UM MITO: apresente a crença popular e mostre, com as provas das fontes, "
                  "que ela é FALSA. Nunca afirme o mito como verdade. " + idea.summary).strip()
        ctx.payload["extra"] = extra0  # a reescrita anti-repetição também mantém a instrução
        ctx.log("Pauta mito × verdade: o roteiro vai desmentir a crença")
    if ctx.payload.get("plan_extra"):  # ex.: longo de um Short campeão (duração de 8-12 min e o Short de origem)
        from . import variety as _v
        plan0 = {**(plan0 or _v.plan(ch, fmt)), **ctx.payload["plan_extra"]}
    data = content.write_script(ch, idea, fmt, extra0, plan=plan0)
    from . import variety
    probs = variety.repetition_problems(ch.id, data.get("title", ""), data.get("hook", ""), data.get("scenes", []))
    if probs:  # trava anti-repetição: reescreve uma vez evitando o que ficou parecido
        ctx.log("Roteiro parecido com vídeos anteriores — reescrevendo: " + " | ".join(probs))
        ctx.update(0.3, "Reescrevendo para não repetir vídeos anteriores")
        extra = (ctx.payload.get("extra", "") + "\nEVITE REPETIR O CANAL: " + "; ".join(probs) +
                 ". Mude o ângulo, o gancho, o título e as frases.").strip()
        data = content.write_script(ch, idea, fmt, extra, plan=data.get("variety"))
        left = variety.repetition_problems(ch.id, data.get("title", ""), data.get("hook", ""), data.get("scenes", []))
        ctx.log("Reescrito: sem repetições" if not left else "Ainda parecido em: " + " | ".join(left))
    if camp:
        data["variety"] = {**(data.get("variety") or {}), "series": camp["name"], "campaign": camp["id"]}
    promised = (data.get("variety") or {}).get("next_idea")
    if promised:
        with session() as s:
            nx = s.get(Idea, promised)
            if nx:
                nx.tags = list(dict.fromkeys((nx.tags or []) + ["prometida"]))
                s.add(nx)
                s.commit()
                ctx.log(f"CTA anuncia o próximo vídeo: “{nx.title}” (vai ser produzido em seguida)")
    ctx.update(0.45, "Laboratório de gancho: testando aberturas")
    data = content.improve_hook(ch, data, data.get("variety") or {}, ctx.log)
    with session() as s:
        sc = Script(channel_id=ch.id, idea_id=idea.id, format=fmt, title=data.get("title", idea.title),
                    hook=data.get("hook", ""), scenes=content.clean_ending(data.get("scenes", []), ch.cta),
                    variety=data.get("variety", {}),
                    description=data.get("description", ""), tags=data.get("tags", []),
                    hashtags=data.get("hashtags", []), thumbnail_text=data.get("thumbnail_text", ""),
                    sources=data.get("sources", []))
        s.add(sc)
        idea = s.get(Idea, idea.id)
        idea.status = "scripted"
        s.add(idea)
        s.commit()
        s.refresh(sc)
    ctx.log(f"Roteiro criado com {len(sc.scenes)} cenas ({content.count_words(sc.scenes)} palavras)")
    if sc.variety:
        from . import variety
        ctx.log(f"Variedade: {variety.label(sc.variety)} · gancho {sc.variety.get('hook_style')} · título {sc.variety.get('title_style')}"
                f"{' · ' + str(sc.variety['seconds']) + 's' if sc.variety.get('seconds') else ''}")
    ctx.update(0.6, "Editor-chefe revisando e checando fatos")
    _review(ch, sc.id, ctx, auto_fix=True)
    _ensure_length(ch, sc.id, ctx)
    _check_claims(ch, sc.id, ctx)
    from . import focus
    if ctx.payload.get("auto_render") and focus.paused(ch.id):  # pausado no meio do caminho: roteiro fica salvo
        ctx.log("Canal pausado (modo foco): roteiro salvo, sem render automático")
    elif ctx.payload.get("auto_render"):
        enqueue("render_video", title=f"Vídeo: {sc.title}", channel_id=ch.id, ref_id=sc.id,
                payload={k: ctx.payload[k] for k in ("publish_at",) if ctx.payload.get(k)})
    return {"script_id": sc.id}


def _ensure_length(ch: Channel, script_id: int, ctx: JobContext) -> None:
    with session() as s:
        sc = s.get(Script, script_id)
        idea = s.get(Idea, sc.idea_id) if sc.idea_id else None
    hint = "; ".join(f.get("claim", "") for f in (idea.facts if idea else []) if f.get("verdict") == "confirmado")
    scenes = content.ensure_length(ch, sc.title, sc.scenes, sc.format, ctx.log, hint, seconds=(sc.variety or {}).get("seconds"))
    if scenes is not sc.scenes:
        with session() as s:
            db = s.get(Script, script_id)
            db.scenes = scenes
            s.add(db)
            s.commit()
        ctx.log(f"Roteiro final: {len(scenes)} cenas, {content.count_words(scenes)} palavras")


def _check_claims(ch: Channel, script_id: int, ctx: JobContext) -> None:
    """Checagem frase a frase. Só roda de novo se o texto mudou desde a última (ex.: roteiro editado à mão)."""
    with session() as s:
        sc = s.get(Script, script_id)
        idea = s.get(Idea, sc.idea_id) if sc.idea_id else None
    if (sc.claims or {}).get("sig") == content.scenes_sig(sc.scenes):
        return
    ctx.update(None, "Checando os fatos frase por frase")
    try:
        r = content.check_claims(ch, sc, idea)
    except Exception as e:  # noqa: BLE001
        ctx.log(f"Checagem frase a frase não rodou ({e}) — siga com atenção ao revisar")
        return
    scenes = [dict(x) for x in sc.scenes]
    for i, txt in r["fixes"].items():
        words = set(txt.lower().split())
        scenes[i] = {**scenes[i], "text": txt,
                     "emphasis": [e for e in scenes[i].get("emphasis") or [] if str(e).lower() in words]}
    items = r["items"]
    bad = [c for c in items if c.get("verdict") in ("sem_fonte", "contradiz")]
    fixed_scenes = {i + 1 for i in r["fixes"]}
    with session() as s:
        db = s.get(Script, script_id)
        db.scenes = scenes
        db.claims = {"sig": content.scenes_sig(scenes), "items": items, "fixed": len(r["fixes"]),
                     "unresolved": [c for c in bad if c.get("scene") not in fixed_scenes], "sources": r["sources"]}
        s.add(db)
        s.commit()
    ok = len(items) - len(bad)
    ctx.log(f"Fatos: {ok}/{len(items)} afirmações confirmadas nas fontes"
            + (f" · {len(r['fixes'])} cena(s) corrigida(s)" if r["fixes"] else ""))
    for c in bad:
        ctx.log(f"  ✗ cena {c.get('scene')}: “{c.get('claim')}” ({c.get('verdict')})"
                + (" → corrigida" if c.get("scene") in fixed_scenes else " → SEM CORREÇÃO, revise"))


def _review(ch: Channel, script_id: int, ctx: JobContext, auto_fix: bool) -> None:
    with session() as s:
        sc = s.get(Script, script_id)
    rv = content.review_script(ch, sc)
    issues = rv.get("issues", [])
    if auto_fix and issues:
        ctx.log(f"Corrigindo {len(issues)} pontos apontados pelo revisor")
        sc.scenes = content.clean_ending(content.apply_fixes(ch, sc, issues), ch.cta)
    with session() as s:
        db = s.get(Script, script_id)
        db.scenes = sc.scenes
        db.quality_score = int(rv.get("overall") or 0) or None
        db.fact_check = issues
        db.review_notes = "\n".join(f"• {x}" for x in rv.get("suggestions", []))
        s.add(db)
        s.commit()
    ctx.log(f"Nota do roteiro: {rv.get('overall')}")


@handler("review_script")
def job_review(ctx: JobContext) -> dict:
    with session() as s:
        sc = s.get(Script, ctx.ref_id)
    ch = _channel(sc.channel_id)
    ctx.update(0.2, "Revisando roteiro")
    _review(ch, sc.id, ctx, auto_fix=ctx.payload.get("auto_fix", False))
    return {}


# ================================================================ VÍDEO

@handler("render_video")
def job_render(ctx: JobContext) -> dict:
    from .production import produce_video
    with session() as s:
        sc = s.get(Script, ctx.ref_id)
        ch = s.get(Channel, sc.channel_id)
        old = s.get(Video, ctx.payload["_video_id"]) if ctx.payload.get("_video_id") else None
        if old and old.status == "rendering":  # retomando depois de um reinício: mesma pasta, etapas já feitas
            video = old
        else:
            video = Video(channel_id=ch.id, script_id=sc.id, format=sc.format, status="rendering")
            s.add(video)
            s.commit()
            s.refresh(video)
    if old is video:
        ctx.log(f"Retomando o vídeo #{video.id} (etapas prontas são reaproveitadas)")
    ctx.save_payload(_video_id=video.id)
    _check_claims(ch, sc.id, ctx)
    with session() as s:
        sc = s.get(Script, ctx.ref_id)
    from .jobs import Cancelled, video_in_use
    try:
        out = produce_video(ch, sc, video.id, ctx)
    except Cancelled:
        with session() as s:  # cancelado: não deixa vídeo "renderizando" para trás (mas não apaga o de outra tarefa)
            v = s.get(Video, video.id)
            if v and v.status == "rendering" and not video_in_use(s, video.id, ctx.job_id):
                s.delete(v)
                s.commit()
        raise
    except Exception as e:
        with session() as s:
            v = s.get(Video, video.id)
            if v and not video_in_use(s, video.id, ctx.job_id):
                v.status, v.error = "failed", str(e)
                s.add(v)
                s.commit()
        raise
    with session() as s:
        v = s.get(Video, video.id)
        if v is None or v.script_id != sc.id:  # registro sumiu durante o render: o arquivo está pronto, recria
            ctx.log(f"Registro do vídeo #{video.id} tinha sumido — recriado")
            v = Video(channel_id=ch.id, script_id=sc.id, format=sc.format)
        v.status = "ready"
        v.path, v.thumbnail_path, v.duration, v.assets = out["path"], out["thumbnail"], out["duration"], out["assets"]
        s.add(v)
        idea = s.get(Idea, sc.idea_id) if sc.idea_id else None
        if idea:
            idea.status = "produced"  # sai da lista de pautas (fica guardada só para não repetir o tema)
            s.add(idea)
        db_sc = s.get(Script, sc.id)
        if db_sc:
            db_sc.status = "produced"  # sai da lista de roteiros; o vídeo continua com acesso a ele
            s.add(db_sc)
        s.commit()
    if sc.format == "long":
        # vídeo longo: capítulos (se o roteiro não marcou) e 3 miniaturas para o teste A/B do YouTube Studio
        if not (out["assets"] or {}).get("chapters"):
            try:
                from .longform import chapters_from_scenes
                chs = chapters_from_scenes(out["assets"].get("scenes") or [], sc.title)
                if chs:
                    with session() as s:
                        v = s.get(Video, video.id)
                        v.assets = {**(v.assets or {}), "chapters": chs}
                        s.add(v)
                        s.commit()
                    ctx.log(f"{len(chs)} capítulos criados")
            except Exception as e:  # noqa: BLE001
                ctx.log(f"Capítulos não gerados: {e}")
        enqueue("thumb_variants", title=f"Miniaturas A/B: {sc.title}", channel_id=ch.id, ref_id=video.id)
    from .inspector import run_inspection
    try:
        qa = run_inspection(video.id, ctx)
    except Exception as e:  # noqa: BLE001
        ctx.log(f"Inspetor falhou ({e}) — vídeo marcado para revisão")
        qa = {"passed": False}
        with session() as s:
            v = s.get(Video, video.id)
            v.status = "review"
            s.add(v)
            s.commit()
    if ctx.payload.get("publish_at"):
        if qa.get("passed"):
            _schedule_publication(video.id, ctx.payload["publish_at"], ctx)
        else:
            ctx.log("Vídeo REPROVADO no inspetor — não foi agendado. Revise em Vídeos.")
    from . import notify
    when = ""
    if ctx.payload.get("publish_at") and qa.get("passed"):
        try:
            from datetime import datetime as _dt
            when = " · agendado para " + _dt.fromisoformat(ctx.payload["publish_at"]).astimezone().strftime("%d/%m %H:%M")
        except ValueError:
            pass
    if qa.get("passed"):
        notify.safe(f"🎬 Vídeo pronto · {ch.name}", f"{sc.title}{when}", event="ready", tags=["clapper"])
    else:
        notify.safe(f"⚠️ Vídeo para revisar · {ch.name}", f"{sc.title}\nO inspetor de qualidade reprovou — abra Vídeos no painel.",
                    event="review", tags=["warning"], priority=4)
    return {"video_id": video.id, "qa": qa.get("passed")}


def _schedule_publication(video_id: int, when_iso: str, ctx: JobContext) -> None:
    """Piloto automático: agenda o vídeo pronto em todas as contas do YouTube conectadas ao canal."""
    from datetime import datetime, timezone
    from .models import Account, Publication, now
    when = datetime.fromisoformat(when_iso).astimezone(timezone.utc)
    from . import focus
    with session() as s:
        vch = s.get(Video, video_id)
    if vch and focus.paused(vch.channel_id):
        ctx.log("Canal pausado (modo foco): vídeo pronto, mas não agendado — publique à mão se quiser")
        return
    try:  # o render pode atrasar/adiantar: confere de novo o espaço mínimo e o limite diário do canal
        from . import posting_times
        with session() as s:
            v0 = s.get(Video, video_id)
            ch0 = s.get(Channel, v0.channel_id)
        moved = posting_times.next_free(ch0, max(when, now()), v0.format or "short")
        if abs((moved - when).total_seconds()) > 60:
            ctx.log(f"Horário ajustado para {moved.astimezone(posting_times.TZ):%d/%m %H:%M} (evita posts colados)")
            when = moved
    except Exception as e:  # noqa: BLE001
        ctx.log(f"Checagem de espaçamento falhou ({e}) — mantendo o horário")
    with session() as s:
        v = s.get(Video, video_id)
        sc = s.get(Script, v.script_id)
        accs = [a for a in s.exec(select(Account).where(Account.channel_id == v.channel_id)).all() if a.credentials]
        for a in accs:
            s.add(Publication(channel_id=v.channel_id, video_id=v.id, account_id=a.id, platform=a.platform,
                              title=sc.title, description=sc.description, privacy="public",
                              scheduled_at=max(when, now()), status="scheduled"))
        s.commit()
    ctx.log(f"Agendado para {when_iso} em {len(accs)} conta(s)" if accs else "Nenhuma conta conectada — vídeo pronto para publicar manualmente")


# ================================================================ PILOTO AUTOMÁTICO

@handler("autopilot")
def job_autopilot(ctx: JobContext) -> dict:
    """Pega a melhor pauta aprovada (ou com nota alta) do formato do horário e produz o vídeo inteiro."""
    ch = _channel(ctx.channel_id)
    fmt = ctx.payload.get("format", "short")
    from . import focus
    if ctx.payload.get("publish_at") and focus.paused(ch):  # disparo do horário antes de o canal ser pausado
        return {"msg": "canal pausado (modo foco): nada novo produzido"}
    with session() as s:
        q = select(Idea).where(Idea.channel_id == ch.id, Idea.status.in_(["approved", "new"]),
                               Idea.fact_status == "verified").order_by(Idea.score.desc())
        cands = [i for i in s.exec(q).all()
                 if (i.status == "approved" or (i.score or 0) >= ch.min_score_to_produce)]
    same = [i for i in cands if i.format == fmt]
    promised = [i for i in same if "prometida" in (i.tags or [])]
    if promised:  # o último vídeo anunciou esta pauta como "próximo vídeo": cumpre a promessa primeiro
        same = promised
        ctx.log(f"Produzindo a pauta prometida no vídeo anterior: {promised[0].title}")
    from . import growth
    camp = growth.wants_campaign(ch)
    if camp and not promised:
        in_camp = [i for i in same if growth.campaign_tag(camp) in (i.tags or [])]
        if in_camp:
            same = in_camp
            ctx.log(f"Campanha ativa: {camp['name']}")
        else:
            enqueue("discover_ideas", title=f"Pautas da campanha: {camp['name']}", channel_id=ch.id,
                    payload={"count": 6, "format": fmt, "campaign": camp["id"]})
    pick = (same or cands)[:1]
    if not pick:
        enqueue("discover_ideas", title="Buscar pautas (piloto automático)", channel_id=ch.id,
                payload={"count": 8, "format": fmt})
        return {"msg": "sem pautas boas; buscando novas"}
    idea = pick[0]
    payload = {"auto_render": True, "format": fmt}
    if ctx.payload.get("publish_at"):
        payload["publish_at"] = ctx.payload["publish_at"]
    enqueue("write_script", title=f"Roteiro{' longo' if fmt == 'long' else ''}: {idea.title}", channel_id=ch.id,
            ref_id=idea.id, payload=payload)
    return {"idea_id": idea.id, "format": fmt}
