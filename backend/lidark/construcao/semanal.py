"""Vídeo longo semanal do Parte por Parte: junta os Shorts mais vistos com narração nova.

Só este canal usa isto; os outros têm o motor de vídeo longo. Cada parte é renderizada de novo a partir da própria
cena, para a voz e a legenda baterem com a imagem. Roda sábado à noite e agenda a publicação para domingo.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlmodel import select

from ..config import MEDIA_DIR
from ..db import session
from ..jobs import JobContext, handler
from ..media import ffmpeg_exe
from ..models import Account, Channel, MetricSnapshot, Publication, Script, Video
from ..notify import safe as avisar
from . import BASE
from . import projeto as P
from .render import _dur

CANAL = "ze-na-fuga"
QTD = 5
PAUSA = timedelta(days=56)  # um Short só volta a entrar em um longo depois disso
ESTADO = BASE / "semanal.json"
FUNDO = ("split[a][b];[a]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=40:2,eq=brightness=-.12[f];"
         "[b]scale=-2:1080[v];[f][v]overlay=(W-w)/2:0")
P_ROTEIRO = """Monte a narração nova do vídeo longo semanal do canal Parte por Parte. Pasta: {pasta}
Em partes/ há {n} Shorts, na ordem do vídeo. Cada pasta tem projeto.json (falas atuais) e cena.js (a animação).

Reescreva a narração de cada parte, com outras palavras, para quem já viu o Short ter motivo para assistir de novo:
- Mesmo número de falas. A cena é sincronizada fala por fala.
- Na mesma fala, mantenha cada palavra de "destaque" e cada palavra que cena.js procura na narração, como em tk('palavra').
- Mantenha a frase "Esse é o..." ou "Essa é a..." com o mesmo nome técnico.
- A última fala de cada parte começa com a mesma primeira frase de agora ("Parabéns, você construiu...") e depois puxa a próxima parte, dizendo o que vem nela.
- A última fala da última parte termina com um gancho: uma crença do dia a dia ligada ao tema e "Verdade ou mentira? Comenta aí."
- Mesmo tamanho das falas atuais, frases curtas de conversa, sem algarismos, só informação correta.

Grave em {pasta}/roteiro.json:
{{"titulo": "até 70 caracteres, sem #Shorts", "descricao": "duas frases", "tags": ["..."], "capa": "até 4 palavras",
 "partes": [{{"capitulo": "nome curto da parte", "falas": ["..."]}}]}}
Escreva só esse arquivo. Não publique nada. Termine com uma frase dizendo o que ficou pronto."""
FERRAMENTAS = "Read,Write,Glob,Grep"


def _nome(s: str) -> str:
    s = re.sub(r"#\w+|, parte por parte", "", str(s), flags=re.I)
    return re.sub(r"\W+", " ", s).strip().lower()


def _estado() -> dict[str, str]:
    return json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}


def candidatos(cid: int) -> list[dict[str, Any]]:
    """Shorts no ar com cena guardada, do mais visto ao menos visto. Vídeo apagado do YouTube fica com zero views."""
    proj = [p for p in P.listar() if p.get("tem_cena") and p.get("falas") and not p.get("teste")]
    por_id = {p["id"]: p for p in proj}
    por_nome = {_nome(p.get("titulo", "")): p for p in proj}
    usados, agora, out = _estado(), datetime.now(timezone.utc), {}
    with session() as s:
        for pub in s.exec(select(Publication).where(Publication.channel_id == cid, Publication.status == "published", Publication.privacy == "public")).all():
            m = s.exec(select(MetricSnapshot).where(MetricSnapshot.publication_id == pub.id).order_by(MetricSnapshot.captured_at.desc())).first()
            v = s.get(Video, pub.video_id) if pub.video_id else None
            if v and v.format != "short":
                continue
            p = por_id.get((v.assets or {}).get("projeto")) if v else por_nome.get(_nome(pub.title))
            if not p or not m or m.views <= 0 or p["id"] in out:
                continue
            quando = usados.get(p["id"])
            if quando and agora - datetime.fromisoformat(quando) < PAUSA:
                continue
            out[p["id"]] = {"id": p["id"], "views": m.views, "titulo": pub.title}
    return sorted(out.values(), key=lambda x: -x["views"])


def _preparar(p: dict[str, Any], ids: list[str]) -> None:
    for i, pid in enumerate(ids, 1):
        o, q = P.pasta(pid), P.pasta(p["id"]) / "partes" / str(i)
        q.mkdir(parents=True, exist_ok=True)
        shutil.copy2(o / "cena.js", q / "cena.js")
        b = P.ler(pid)
        (q / "projeto.json").write_text(json.dumps({**b, **P.VOZ_CLAUDE, "cauda": 2, "origem": pid}, ensure_ascii=False, indent=1), encoding="utf-8")


def _roteiro(p: dict[str, Any], ctx: JobContext, n: int) -> dict[str, Any]:
    d = P.pasta(p["id"])
    if not (d / "roteiro.json").exists():
        P._claude(p, ctx, P_ROTEIRO.format(pasta=d.as_posix(), n=n), FERRAMENTAS)
    r = json.loads((d / "roteiro.json").read_text(encoding="utf-8"))
    if len(r.get("partes", [])) != n:
        raise RuntimeError("O roteiro não veio com todas as partes")
    for i, x in enumerate(r["partes"], 1):
        f = d / "partes" / str(i) / "projeto.json"
        b = json.loads(f.read_text(encoding="utf-8"))
        if len(x.get("falas", [])) != len(b["falas"]):
            raise RuntimeError(f"A parte {i} mudou o número de falas")
        b["falas"] = x["falas"]
        f.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    return r


def _renderizar(q: Path, ctx: JobContext, a: float, b: float) -> None:
    r, sai = P._rodar("lidark.construcao.motor.estudio.render_hq", [str(q)], ctx, a, b)
    if r:
        raise RuntimeError(sai[-500:])
    r, sai = P._rodar("lidark.construcao.audio", [str(q / "tmp"), str(q / "final.mp4")], ctx)
    if r:
        raise RuntimeError(sai[-500:])


def _juntar(partes: list[Path], saida: Path) -> None:
    ff = ffmpeg_exe()
    ent = [x for q in partes for x in ("-i", str(q / "final.mp4"))]
    fil = ";".join(f"[{i}:v]{FUNDO},setsar=1[v{i}]" for i in range(len(partes)))
    fil += ";" + "".join(f"[v{i}][{i}:a]" for i in range(len(partes))) + f"concat=n={len(partes)}:v=1:a=1[v][a]"
    subprocess.run([ff, "-y", "-v", "error", *ent, "-filter_complex", fil, "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(saida)], check=True)


def _capa(d: Path, texto: str) -> Path:
    vert, out = d / "capa_vertical.jpg", d / "capa.jpg"
    P.capa(d / "partes" / "1" / "tmp" / "capa_base.jpg", texto, vert)
    subprocess.run([ffmpeg_exe(), "-y", "-v", "error", "-i", str(vert), "-filter_complex", f"[0:v]{FUNDO},scale=1280:720", "-frames:v", "1", "-q:v", "3", str(out)], check=True)
    return out


def _proximo_domingo() -> datetime:
    agora = datetime.now().astimezone()
    alvo = (agora + timedelta(days=(6 - agora.weekday()) % 7)).replace(hour=11, minute=0, second=0, microsecond=0)
    return max(alvo, agora + timedelta(hours=1)).astimezone(timezone.utc)


def _registrar(ch: Channel, d: Path, r: dict[str, Any], texto: str, dur: float, ids: list[str], publicar: bool) -> int:
    dm = MEDIA_DIR / ch.slug / f"semanal_{d.name}"
    dm.mkdir(parents=True, exist_ok=True)
    shutil.copy2(d / "final.mp4", dm / "video.mp4")
    shutil.copy2(d / "capa.jpg", dm / "capa.jpg")
    falas = [f for x in r["partes"] for f in x["falas"]]
    with session() as s:
        sc = Script(channel_id=ch.id, format="long", title=r["titulo"], hook=falas[0], scenes=[{"text": f} for f in falas], description=texto, tags=r.get("tags", []), hashtags=list(ch.default_hashtags or []), status="produced", variety={"from_long": True})
        s.add(sc)
        s.commit()
        s.refresh(sc)
        v = Video(channel_id=ch.id, script_id=sc.id, format="long", status="ready", path=str((dm / "video.mp4").relative_to(MEDIA_DIR)), thumbnail_path=str((dm / "capa.jpg").relative_to(MEDIA_DIR)), duration=dur, assets={"template": "construcao_semanal", "duration": dur, "partes": ids})
        s.add(v)
        s.commit()
        s.refresh(v)
        conta = s.exec(select(Account).where(Account.channel_id == ch.id, Account.platform == "youtube")).first()
        if publicar:
            if not conta:
                raise RuntimeError("O canal não tem conta do YouTube conectada")
            s.add(Publication(channel_id=ch.id, video_id=v.id, account_id=conta.id, platform="youtube", status="scheduled", scheduled_at=_proximo_domingo(), title=r["titulo"], description=texto, privacy="public", duration=dur))
            s.commit()
        return v.id


@handler("construcao_semanal")
def job_semanal(ctx: JobContext) -> dict:
    publicar = bool(ctx.payload.get("publicar"))
    with session() as s:
        ch = s.exec(select(Channel).where(Channel.slug == CANAL)).first()
    ids = ctx.payload.get("ids") or [c["id"] for c in candidatos(ch.id)[:QTD]]
    if not ctx.payload.get("ids") and len(ids) < QTD:
        avisar("Vídeo longo da semana não saiu", f"Só há {len(ids)} Shorts do Parte por Parte disponíveis e são necessários {QTD}.", event="failed")
        return {"pulado": True, "disponiveis": len(ids)}
    pid = ctx.payload.get("pasta") or f"semanal-{datetime.now():%Y-%m-%d}"
    d = P.pasta(pid)
    if (d / "projeto.json").exists():
        p = P.ler(pid)
    else:
        p = P.salvar({"id": pid, "channel_id": ch.id, "tema": "vídeo longo semanal", "titulo": "Vídeo longo semanal", "status": "criando", "falas": [], "teste": True})
    _preparar(p, ids)
    ctx.update(progress=.03, stage="O Claude está escrevendo a narração nova")
    r = _roteiro(p, ctx, len(ids))
    partes = [d / "partes" / str(i) for i in range(1, len(ids) + 1)]
    for i, q in enumerate(partes):
        ctx.update(progress=.1 + .75 * i / len(partes), stage=f"Renderizando a parte {i + 1} de {len(partes)}")
        _renderizar(q, ctx, .1 + .75 * i / len(partes), .1 + .75 * (i + 1) / len(partes))
    ctx.update(progress=.87, stage="Juntando as partes")
    _juntar(partes, d / "final.mp4")
    durs, t, cap = [_dur(ffmpeg_exe(), q / "final.mp4") for q in partes], 0., []
    for x, du in zip(r["partes"], durs):
        cap.append(f"{int(t // 60):02d}:{int(t % 60):02d} {x.get('capitulo', '').strip()}")
        t += du
    texto = f"{r.get('descricao', '').strip()}\n\n" + "\n".join(cap)
    _capa(d, r.get("capa") or "Como tudo é construído")
    vid = _registrar(ch, d, r, texto, t, ids, publicar)
    if publicar:
        est = _estado()
        est.update({x: datetime.now(timezone.utc).isoformat() for x in ids})
        ESTADO.write_text(json.dumps(est, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"video_id": vid, "duracao": t, "partes": ids}
