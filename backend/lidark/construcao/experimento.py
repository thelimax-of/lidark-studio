"""Relatório do Experimento de abertura: compara os vídeos novos do Parte por Parte com os anteriores. Só lê.

Uso: python -m lidark.construcao.experimento
"""
from __future__ import annotations

import datetime as dt
import statistics
import sys

from sqlmodel import select

from ..db import session
from ..models import Account
from ..publish import _yt_client, _yt_creds

CANAL = 5
INICIO = "2026-11-03T02:00:00Z"  # o repost do estádio, último com "Se você", saiu às 01:00 UTC
ANTES = 7  # vídeos "Como construir" anteriores usados como base
TAMANHO = 5
META_VIEWS, META_ENGAJADAS = 2000, 65


def videos(yt) -> list[dict]:
    ch = yt.channels().list(part="contentDetails", mine=True).execute()["items"][0]
    up, ids, tok = ch["contentDetails"]["relatedPlaylists"]["uploads"], [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=up, maxResults=50, pageToken=tok).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        tok = r.get("nextPageToken")
        if not tok:
            break
    vs = []
    for i in range(0, len(ids), 50):
        vs += yt.videos().list(part="snippet,statistics,status", id=",".join(ids[i:i + 50])).execute()["items"]
    return sorted((v for v in vs if v["status"]["privacyStatus"] == "public"), key=lambda v: v["snippet"]["publishedAt"])


def analise(ya, v: dict) -> dict | None:
    """Engajadas e retenção; o YouTube libera com 1 a 2 dias de atraso."""
    ini = (dt.date.fromisoformat(v["snippet"]["publishedAt"][:10]) - dt.timedelta(days=1)).isoformat()
    r = ya.reports().query(ids="channel==MINE", startDate=ini, endDate=dt.date.today().isoformat(),
                           metrics="views,engagedViews,averageViewPercentage,shares,subscribersGained",
                           filters=f"video=={v['id']}").execute().get("rows") or []
    return {"views": r[0][0], "eng": 100 * r[0][1] / r[0][0], "ret": r[0][2], "shr": r[0][3], "sub": r[0][4]} if r and r[0][0] else None


def linha(ya, v: dict) -> tuple[int, float | None]:
    n, a = int(v["statistics"].get("viewCount", 0)), analise(ya, v)
    extra = f"engajadas {a['eng']:.0f}%  retenção {a['ret']:.0f}%  compart. {a['shr']:.0f}  inscritos +{a['sub']:.0f}" if a else "detalhes ainda não liberados"
    print(f"  {v['snippet']['publishedAt'][:10]}  {n:6}  {v['snippet']['title'][:46]:46}  {extra}")
    return n, a["eng"] if a else None


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    with session() as s:
        acc = s.exec(select(Account).where(Account.channel_id == CANAL, Account.platform == "youtube")).first()
    cr = _yt_creds(acc)
    yt, ya = _yt_client(cr), _yt_client(cr, "youtubeAnalytics", "v2")
    vs = videos(yt)
    base = [v for v in vs if v["snippet"]["publishedAt"] < INICIO][-ANTES - 1:-1]
    novos = [v for v in vs if v["snippet"]["publishedAt"] >= INICIO][:TAMANHO]
    print("BASE (abertura com Se você)")
    b = [linha(ya, v) for v in base]
    print(f"\nTESTE ({len(novos)} de {TAMANHO})")
    t = [linha(ya, v) for v in novos]
    mediana = lambda xs: statistics.median(xs) if xs else None
    bv, be, tv, te = mediana([x[0] for x in b]), mediana([x[1] for x in b if x[1] is not None]), mediana([x[0] for x in t]), mediana([x[1] for x in t if x[1] is not None])
    print(f"\nMediana de views: base {bv}  teste {tv}\nMediana de engajadas: base {be}%  teste {te}%")
    furou = sum(x[0] >= META_VIEWS for x in t)
    print(f"Metas: {furou} vídeo(s) acima de {META_VIEWS} views; engajadas {'atingiu' if te and te >= META_ENGAJADAS else 'ainda abaixo de'} {META_ENGAJADAS}%.")
    if len(novos) < TAMANHO:
        print("Teste incompleto: conclua com os 5 vídeos e espere 2 dias depois do último.")


if __name__ == "__main__":
    main()
