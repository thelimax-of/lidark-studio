"""Calendário de efemérides: datas que vêm por aí (7+ dias à frente) por nicho, cada uma vira pauta com um clique.

Regra de ouro: NENHUMA data inventada. Cada evento vem de uma fonte confiável ou de um cálculo, com a confiança marcada:
- Aniversários redondos ("há 100 anos"): "Neste dia" da Wikipédia em português (API do Wikimedia) — o ano e o fato vêm
  da Wikipédia, com o link do artigo; a pauta ainda passa pela checagem de fatos antes de virar roteiro.
- Astronomia CALCULADA (algoritmos de Jean Meeus, "Astronomical Algorithms"): luas cheia/nova, equinócios/solstícios e
  eclipses (tipo pelo gama/u do cap. 54; a visibilidade no Brasil não é calculada — confira no site da NASA).
- Chuvas de meteoros: picos anuais do calendário da IMO (International Meteor Organization), ±1 dia.
- Lançamentos espaciais: Launch Library 2 (The Space Devs) — datas programadas, que mudam com frequência.
- Futebol: fatos de futebol do "Neste dia" da Wikipédia (finais, títulos, fundações de clubes).
- ENEM: só a data do edital do Inep que já está no sistema (growth.ENEM_DAY).
"""
from __future__ import annotations

import json
import logging
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from .config import CACHE_DIR

log = logging.getLogger("lidark.almanac")
TZ = ZoneInfo("America/Sao_Paulo")
UA = {"User-Agent": "LidarkStudio/1.0 (local desktop app; https://localhost) httpx"}  # a Wikimedia exige UA descritivo
WIKI_DIR = CACHE_DIR / "almanac"

# ================================================================ astronomia calculada (Meeus)

def _jd_to_dt(jd: float) -> datetime:
    """Dia juliano (TT ≈ UTC para o que importa aqui: a data) → datetime UTC."""
    return datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=jd - 2451545.0)


def _dt_to_k(d: date) -> float:
    return (d.year + (d.timetuple().tm_yday - 1) / 365.25 - 2000) * 12.3685


def _syzygy(k: float) -> dict[str, Any]:
    """Lua nova (k inteiro) ou cheia (k + 0,5) e o eclipse, se houver — Meeus, cap. 54 (data ± poucos minutos)."""
    rad = math.radians
    T = k / 1236.85
    jde = 2451550.09766 + 29.530588861 * k + 0.00015437 * T ** 2 - 0.000000150 * T ** 3 + 0.00000000073 * T ** 4
    M = rad((2.5534 + 29.10535670 * k - 0.0000014 * T ** 2 - 0.00000011 * T ** 3) % 360)
    Mp = rad((201.5643 + 385.81693528 * k + 0.0107582 * T ** 2 + 0.00001238 * T ** 3 - 0.000000058 * T ** 4) % 360)
    F = rad((160.7108 + 390.67050284 * k - 0.0016118 * T ** 2 - 0.00000227 * T ** 3 + 0.000000011 * T ** 4) % 360)
    Om = rad((124.7746 - 1.56375588 * k + 0.0020672 * T ** 2 + 0.00000215 * T ** 3) % 360)
    E = 1 - 0.002516 * T - 0.0000074 * T ** 2
    F1 = F - rad(0.02665) * math.sin(Om)
    A1 = rad((299.77 + 0.107408 * k - 0.009173 * T ** 2) % 360)
    full = abs(k - math.floor(k) - 0.5) < 0.01
    s = math.sin
    jd = jde + ((-0.4065 if full else -0.4075) * s(Mp) + (0.1727 if full else 0.1721) * E * s(M)
                + 0.0161 * s(2 * Mp) - 0.0097 * s(2 * F1) + 0.0073 * E * s(Mp - M) - 0.0050 * E * s(Mp + M)
                - 0.0023 * s(Mp - 2 * F1) + 0.0021 * E * s(2 * M) + 0.0012 * s(Mp + 2 * F1) + 0.0006 * E * s(2 * Mp + M)
                - 0.0004 * s(3 * Mp) - 0.0003 * E * s(M + 2 * F1) + 0.0003 * s(A1) - 0.0002 * E * s(M - 2 * F1)
                - 0.0002 * E * s(2 * Mp - M) - 0.0002 * s(Om))
    out: dict[str, Any] = {"kind": "full" if full else "new", "when": _jd_to_dt(jd), "eclipse": None}
    if abs(math.sin(F)) > 0.36:
        return out
    c = math.cos
    P = (0.2070 * E * s(M) + 0.0024 * E * s(2 * M) - 0.0392 * s(Mp) + 0.0116 * s(2 * Mp) - 0.0073 * E * s(Mp + M)
         + 0.0067 * E * s(Mp - M) + 0.0118 * s(2 * F1))
    Q = (5.2207 - 0.0048 * E * c(M) + 0.0020 * E * c(2 * M) - 0.3299 * c(Mp) - 0.0060 * E * c(Mp + M)
         + 0.0041 * E * c(Mp - M))
    W = abs(c(F1))
    gamma = (P * c(F1) + Q * s(F1)) * (1 - 0.0048 * W)
    u = 0.0059 + 0.0046 * E * c(M) - 0.0182 * c(Mp) + 0.0004 * c(2 * Mp) - 0.0005 * c(M + Mp)
    g = abs(gamma)
    if not full:
        if g > 1.5433 + u:
            return out
        if g < 0.9972:
            typ = "total" if u < 0 else "anular" if u > 0.0047 else "híbrido"
        else:
            typ = "parcial"
        out["eclipse"] = {"type": typ, "gamma": round(gamma, 4)}
    else:
        pen = (1.5573 + u - g) / 0.5450
        umb = (1.0128 - u - g) / 0.5450
        if pen <= 0:
            return out
        typ = "total" if umb >= 1 else "parcial" if umb > 0 else "penumbral"
        out["eclipse"] = {"type": typ, "gamma": round(gamma, 4), "magnitude": round(umb if umb > 0 else pen, 3)}
    return out


def moon_events(start: date, end: date) -> list[dict[str, Any]]:
    out = []
    k0 = math.floor(_dt_to_k(start)) - 1
    for i in range(0, int((end - start).days / 29.5) + 4):
        for frac in (0.0, 0.5):
            ev = _syzygy(k0 + i + frac)
            d = ev["when"].astimezone(TZ).date()
            if start <= d <= end:
                ev["date"] = d
                out.append(ev)
    return sorted(out, key=lambda e: e["when"])


def seasons(year: int) -> list[tuple[str, datetime]]:
    """Equinócios e solstícios (Meeus, cap. 27, termos médios + correção periódica)."""
    Y = (year - 2000) / 1000
    base = {
        "mar": 2451623.80984 + 365242.37404 * Y + 0.05169 * Y ** 2 - 0.00411 * Y ** 3 - 0.00057 * Y ** 4,
        "jun": 2451716.56767 + 365241.62603 * Y + 0.00325 * Y ** 2 + 0.00888 * Y ** 3 - 0.00030 * Y ** 4,
        "set": 2451810.21715 + 365242.01767 * Y - 0.11575 * Y ** 2 + 0.00337 * Y ** 3 + 0.00078 * Y ** 4,
        "dez": 2451900.05952 + 365242.74049 * Y - 0.06223 * Y ** 2 - 0.00823 * Y ** 3 + 0.00032 * Y ** 4,
    }
    A = [485, 203, 199, 182, 156, 136, 77, 74, 70, 58, 52, 50, 45, 44, 29, 18, 17, 16, 14, 12, 12, 12, 9, 8]
    B = [324.96, 337.23, 342.08, 27.85, 73.14, 171.52, 222.54, 296.72, 243.58, 119.81, 297.17, 21.02, 247.54, 325.15,
         60.93, 155.12, 288.79, 198.04, 199.76, 95.39, 287.11, 320.81, 227.73, 15.45]
    C = [1934.136, 32964.467, 20.186, 445267.112, 45036.886, 22518.443, 65928.934, 3034.906, 9037.513, 33718.147,
         150.678, 2281.226, 29929.562, 31555.956, 4443.417, 67555.328, 4562.452, 62894.029, 31436.921, 14577.848,
         31931.756, 34777.259, 1222.114, 16859.074]
    out = []
    for key, jde0 in base.items():
        T = (jde0 - 2451545.0) / 36525
        Wd = math.radians(35999.373 * T - 2.47)
        dl = 1 + 0.0334 * math.cos(Wd) + 0.0007 * math.cos(2 * Wd)
        S = sum(a * math.cos(math.radians(b + c * T)) for a, b, c in zip(A, B, C))
        out.append((key, _jd_to_dt(jde0 + 0.00001 * S / dl)))
    return out


SEASON_NAMES = {  # nomes no hemisfério sul (Brasil)
    "mar": ("Equinócio de março", "começo do outono no Hemisfério Sul"),
    "jun": ("Solstício de junho", "começo do inverno no Hemisfério Sul — a noite mais longa do ano no Brasil"),
    "set": ("Equinócio de setembro", "começo da primavera no Hemisfério Sul"),
    "dez": ("Solstício de dezembro", "começo do verão no Hemisfério Sul — o dia mais longo do ano no Brasil"),
}

# picos anuais (calendário da IMO); variam ±1 dia de um ano para outro
METEOR_SHOWERS = [
    ((1, 3), "Quadrântidas", "boa no Hemisfério Norte; baixa no Brasil"),
    ((4, 22), "Líridas", "visível no Brasil de madrugada, taxa modesta"),
    ((5, 6), "Eta Aquáridas", "uma das melhores para o Hemisfério Sul; restos do cometa Halley"),
    ((7, 30), "Delta Aquáridas do Sul", "favorável ao Hemisfério Sul"),
    ((8, 12), "Perseidas", "a mais famosa; baixa no Brasil (radiante ao norte)"),
    ((10, 21), "Orionídeas", "restos do cometa Halley; visível no Brasil"),
    ((11, 17), "Leônidas", "famosa pelas tempestades históricas de 1833, 1966 e 2001"),
    ((12, 14), "Geminídeas", "a mais intensa do ano; visível no Brasil depois da meia-noite"),
]


def astronomy(start: date, end: date) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ev in moon_events(start, end):
        d = ev["date"]
        hora = ev["when"].astimezone(TZ).strftime("%H:%M")
        if ev["eclipse"]:
            e = ev["eclipse"]
            body = "do Sol" if ev["kind"] == "new" else "da Lua"
            out.append({"date": d.isoformat(), "kind": "astronomia", "title": f"Eclipse {body} {e['type']}",
                        "detail": f"Calculado (Meeus): sizígia às {hora} (Brasília), gama {e['gamma']:+.3f}. "
                                  "A faixa de visibilidade não é calculada aqui — confira se dá para ver do Brasil.",
                        "confidence": "calculado", "source": "Cálculo astronômico (Meeus, cap. 54)",
                        "url": "https://eclipse.gsfc.nasa.gov/eclipse.html", "weight": 3})
        else:
            nome = "Lua cheia" if ev["kind"] == "full" else "Lua nova"
            extra = " — céu escuro, melhor noite para observar estrelas e a Via Láctea" if ev["kind"] == "new" else ""
            out.append({"date": d.isoformat(), "kind": "astronomia", "title": nome,
                        "detail": f"Às {hora} (Brasília){extra}.", "confidence": "calculado",
                        "source": "Cálculo astronômico (Meeus)", "url": "", "weight": 1})
    for y in range(start.year, end.year + 1):
        for key, dt in seasons(y):
            d = dt.astimezone(TZ).date()
            if start <= d <= end:
                nome, det = SEASON_NAMES[key]
                out.append({"date": d.isoformat(), "kind": "astronomia", "title": nome,
                            "detail": f"Às {dt.astimezone(TZ).strftime('%H:%M')} (Brasília): {det}.",
                            "confidence": "calculado", "source": "Cálculo astronômico (Meeus, cap. 27)", "url": "",
                            "weight": 2})
        for (m, dd), nome, det in METEOR_SHOWERS:
            d = date(y, m, dd)
            if start <= d <= end:
                out.append({"date": d.isoformat(), "kind": "astronomia", "title": f"Pico da chuva de meteoros {nome}",
                            "detail": f"{det}. O pico varia ±1 dia de um ano para outro.",
                            "confidence": "média", "source": "Calendário anual da IMO",
                            "url": "https://www.imo.net/resources/calendar/", "weight": 2})
    return out


def launches(start: date, end: date) -> list[dict[str, Any]]:
    """Lançamentos programados (Launch Library 2, The Space Devs; grátis, cache de 12 h)."""
    from . import cache

    def fetch() -> list[dict[str, Any]]:
        r = httpx.get("https://ll.thespacedevs.com/2.2.0/launch/upcoming/", headers=UA, timeout=25,
                      params={"limit": 60, "mode": "list", "hide_recent_previous": "true"})
        r.raise_for_status()
        return r.json().get("results") or []
    try:
        rows = cache.get("almanac:launches", fetch, ttl=12 * 3600, stale=3 * 86400, error_ttl=1800)
    except Exception as e:  # noqa: BLE001
        log.info("lançamentos: %s", e)
        return []
    out = []
    for x in rows or []:
        try:
            when = datetime.fromisoformat(str(x.get("net")).replace("Z", "+00:00")).astimezone(TZ)
        except ValueError:
            continue
        if not (start <= when.date() <= end):
            continue
        st = (x.get("status") or {}).get("abbrev") or ""
        name = str(x.get("name") or "")
        big = bool(re.search(r"artemis|starship|crew|tripul|james webb|europa|mars|lua|moon|new glenn|ariane 6|"
                             r"h3|long march 10|gaganyaan|chang", name, re.I))
        if not big and st != "Go":
            continue
        out.append({"date": when.date().isoformat(), "kind": "lançamento", "title": f"Lançamento: {name}",
                    "detail": f"Previsto para {when.strftime('%d/%m %H:%M')} (Brasília) · status {st or '?'} · "
                              f"{x.get('pad') or x.get('location') or ''}".strip(" ·"),
                    "confidence": "programado" if st == "Go" else "a confirmar", "source": "Launch Library 2 (The Space Devs)",
                    "url": f"https://thespacedevs.com/", "weight": 3 if big else 1})
    return out


# ================================================================ "Neste dia" (Wikipédia)

ROUND = (500, 400, 300, 250, 200, 150, 100, 75, 50, 40, 30, 25, 20, 10)
BRAZIL_RX = re.compile(r"\b(brasil|brasileir|rio de janeiro|s[aã]o paulo|minas gerais|bahia|pernambuco|rio grande do sul|"
                       r"imp[eé]rio do brasil|dom pedro|get[uú]lio|vargas|portugal|lisboa|sele[cç][aã]o brasileira|"
                       r"maracan|pel[eé]|amaz[oô]nia|bras[ií]lia|recife|salvador|porto alegre|curitiba)", re.I)
MAX_EVENTS = 45  # por canal: os mais fortes (peso) — o resto é ruído

NICHE_RX = {
    "historia": None,  # qualquer fato histórico (o filtro é o ano redondo)
    "espaco": re.compile(r"\b(espac|astron|sat[eé]lit|foguete|nasa|lua\b|lunar|marte|planeta|cometa|estrela|gal[aá]xia|"
                         r"telesc|apollo|sputnik|gagarin|[oó]rbita|asteroide|eclipse|cosmonauta|astronauta|sonda|hubble|"
                         r"voyager|roscosmos|esa\b)", re.I),
    "futebol": re.compile(r"\b(futebol|futebolista|copa do mundo|copa am[eé]rica|libertadores|sele[cç][aã]o (brasileira|de futebol)|"
                          r"fifa|pel[eé]\b|maracan[aã]|campeonato (brasileiro|mundial|paulista|carioca|ga[uú]cho|mineiro)|"
                          r"flamengo|corinthians|palmeiras|vasco da gama|gr[eê]mio|sport club internacional|chapecoense|"
                          r"cruzeiro esporte|atl[eé]tico mineiro|fluminense|botafogo|santos futebol|s[aã]o paulo futebol|"
                          r"mundial de clubes|ta[cç]a (libertadores|jules rimet)|est[aá]dio)", re.I),
    "ciencia": re.compile(r"\b(cient|f[ií]sic|qu[ií]mic|biolog|medicin|vacina|descobr|inven|teoria|nobel|dna|gen[eé]t|"
                          r"[aá]tomo|nuclear|eletric|computador|internet|penicilina|darwin|einstein|newton|curie|"
                          r"tesla|edison|pasteur|matem[aá]tic|laborat)", re.I),
}


def niches_for(ch) -> list[str]:
    txt = f"{ch.name} {ch.niche} {ch.description}".lower()
    out = []
    football = bool(re.search(r"futebol|placar|esporte|copa", txt))
    if re.search(r"enem|passado", txt) or (re.search(r"hist[oó]ri", txt) and not football):
        out.append("historia")
    if re.search(r"cosmo|espa[cç]|astro|universo|planet", txt):
        out.append("espaco")
    if re.search(r"futebol|placar|esporte|copa", txt):
        out.append("futebol")
    if re.search(r"ci[eê]ncia|laborat|experiment|qu[ií]mic|f[ií]sic", txt):
        out.append("ciencia")
    return out or ["historia"]


def _wiki_day(d: date) -> dict[str, Any]:
    """Fatos do dia (mês/dia) na Wikipédia em português, em cache local por 30 dias."""
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    p = WIKI_DIR / f"wiki_{d.month:02d}{d.day:02d}.json"
    try:
        if time.time() - p.stat().st_mtime < 30 * 86400:
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    r = httpx.get(f"https://api.wikimedia.org/feed/v1/wikipedia/pt/onthisday/all/{d.month:02d}/{d.day:02d}",
                  headers=UA, timeout=25)
    r.raise_for_status()
    raw = r.json()
    slim: dict[str, list] = {}
    for key in ("selected", "events", "births", "deaths"):
        rows = []
        for e in raw.get(key) or []:
            pages = e.get("pages") or []
            pg = pages[0] if pages else {}
            rows.append({"year": e.get("year"), "text": e.get("text", ""),
                         "page": (pg.get("titles") or {}).get("normalized") or pg.get("title", ""),
                         "url": ((pg.get("content_urls") or {}).get("desktop") or {}).get("page", "")})
        slim[key] = rows
    p.write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")
    return slim


def anniversaries(start: date, end: date, niches: list[str]) -> list[dict[str, Any]]:
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda d: (d, _safe_wiki(d)), days))
    out = []
    for d, data in res:
        seen = set()
        for key in ("selected", "events", "births", "deaths"):
            for e in data.get(key) or []:
                y = e.get("year")
                if not isinstance(y, int) or y <= 0 or y >= d.year:
                    continue
                age = d.year - y
                if age not in ROUND:
                    continue
                txt = e.get("text") or ""
                br = bool(BRAZIL_RX.search(txt + " " + (e.get("page") or "")))
                person = key in ("births", "deaths")
                for niche in niches:
                    rx = NICHE_RX.get(niche)
                    if rx is not None and not rx.search(txt + " " + (e.get("page") or "")):
                        continue
                    # nascimentos/mortes (a lista é enorme): só aniversários bem redondos (50, 100...) e, fora de
                    # ciência/espaço, só brasileiros — o resto é ruído para o público do canal
                    if person and (age % 50 or (niche in ("historia", "futebol") and not br)):
                        continue
                    if niche == "historia" and not person and age < 25:
                        continue
                    k = (txt[:60], niche)
                    if k in seen:
                        continue
                    seen.add(k)
                    what = {"births": "Nascimento", "deaths": "Morte"}.get(key, "")
                    title = f"Há {age} anos" + (f" ({what.lower()})" if what else "") + f": {txt[:140]}"
                    weight = (3 if age % 100 == 0 or age in (50, 150, 250) else 2 if age % 25 == 0 else 1) + \
                             (1 if key == "selected" else 0) + (1 if br else 0) - (1 if person else 0)
                    out.append({"date": d.isoformat(), "kind": "futebol" if niche == "futebol" else "aniversário",
                                "niche": niche, "title": title, "detail": f"{y} → {d.year} ({age} anos). {e.get('page') or ''}",
                                "year": y, "age": age, "confidence": "fonte (Wikipédia)",
                                "source": "Wikipédia — Neste dia", "url": e.get("url", ""), "weight": weight})
    return out


def _safe_wiki(d: date) -> dict[str, Any]:
    try:
        return _wiki_day(d)
    except Exception as e:  # noqa: BLE001
        log.info("wikipedia %s: %s", d, e)
        return {}


# ================================================================ calendário por canal

def calendar(channel_id: int, days: int = 60, min_ahead: int = 7) -> dict[str, Any]:
    from . import cache
    return cache.get(f"almanac:cal:{channel_id}:{days}:{min_ahead}:{date.today().isoformat()}",
                     lambda: _calendar(channel_id, days, min_ahead), ttl=6 * 3600, stale=86400)


def _calendar(channel_id: int, days: int, min_ahead: int) -> dict[str, Any]:
    from .db import session
    from .models import Channel, Idea
    from sqlmodel import select
    with session() as s:
        ch = s.get(Channel, channel_id)
        if not ch:
            return {"events": [], "niches": []}
        made = {t.split(":", 1)[1] for i in s.exec(select(Idea).where(Idea.channel_id == channel_id,
                                                                    Idea.origin == "almanac")).all()
                for t in (i.tags or []) if isinstance(t, str) and t.startswith("almanaque:")}
    niches = niches_for(ch)
    today = datetime.now(TZ).date()
    start, end = today + timedelta(days=min_ahead), today + timedelta(days=days)
    ev: list[dict[str, Any]] = []
    ev += anniversaries(start, end, niches)
    if "espaco" in niches or "ciencia" in niches:
        ev += [e for e in astronomy(start, end) if "espaco" in niches or e["weight"] >= 2]
    if "espaco" in niches:
        ev += launches(start, end)
    if "historia" in niches and re.search(r"enem", f"{ch.name} {ch.niche} {ch.description}", re.I):
        from .growth import ENEM_DAY
        for off, what in ((0, "1º dia do ENEM (Linguagens, Ciências Humanas e Redação)"),):
            d = ENEM_DAY + timedelta(days=off)
            if today <= d <= end:  # ENEM entra mesmo a menos de 7 dias: é a data mais importante do canal
                ev.append({"date": d.isoformat(), "kind": "enem", "title": what,
                           "detail": "Data do edital do Inep (configurada no sistema). Pautas de revisão antes; correção depois.",
                           "confidence": "oficial (Inep)", "source": "Edital do ENEM (Inep)", "url": "https://www.gov.br/inep",
                           "weight": 4})
    ann = sorted([e for e in ev if e["kind"] in ("aniversário", "futebol")], key=lambda e: -e["weight"])
    ev = [e for e in ev if e["kind"] not in ("aniversário", "futebol")] + ann[:MAX_EVENTS]
    for e in ev:
        e["id"] = re.sub(r"\W+", "-", f"{e['date']}-{e['title'][:50]}".lower()).strip("-")
        e["days_ahead"] = (date.fromisoformat(e["date"]) - today).days
        e["idea_created"] = e["id"] in made
    ev.sort(key=lambda e: (e["date"], -e["weight"]))
    return {"channel_id": channel_id, "niches": niches, "start": start.isoformat(), "end": end.isoformat(),
            "events": ev, "sources": [
                "Wikipédia — Neste dia (API Wikimedia)", "Cálculo astronômico (Meeus): luas, estações e eclipses",
                "IMO: chuvas de meteoros", "Launch Library 2: lançamentos", "Inep: ENEM"]}


def create_idea(channel_id: int, event_id: str) -> dict[str, Any]:
    """Pauta a partir de uma efeméride (origem "almanac"). O roteiro adapta o tema com pesquisa própria e a checagem
    de fatos roda antes de virar vídeo."""
    from .db import session
    from .jobs import enqueue
    from .models import Idea
    e = None
    for days in (60, 30, 90, 120):  # mesmas janelas da tela (em cache) — não refaz a busca inteira
        cal = calendar(channel_id, days, 7)
        e = next((x for x in cal["events"] if x["id"] == event_id), None)
        if e:
            break
    if not e:
        raise ValueError("Efeméride não encontrada (o calendário pode ter mudado)")
    d = date.fromisoformat(e["date"])
    when = d.strftime("%d/%m/%Y")
    base = re.sub(r"^Há \d+ anos( \([^)]*\))?: ", "", e["title"])
    title = (f"Há {e['age']} anos: {base}" if e.get("age") else e["title"])[:200]
    angle = (f"Efeméride de {when} ({e['source']}). Publicar alguns dias antes ou no dia. Contar o fato com pesquisa "
             f"própria e um ângulo de curiosidade — confirme a data e os nomes nas fontes antes de roteirizar.")
    with session() as s:
        idea = Idea(channel_id=channel_id, title=title, angle=angle, summary=f"{e['title']}. {e['detail']}"[:2000],
                    format="short", origin="almanac",
                    tags=[f"almanaque:{e['id']}", f"data:{e['date']}", f"confiança:{e['confidence']}"],
                    sources=[{"title": e["source"], "url": e.get("url", ""), "snippet": e["detail"][:300]}] if e.get("url") else [])
        s.add(idea)
        s.commit()
        s.refresh(idea)
        iid = idea.id
    try:
        enqueue("score_idea", title="Avaliar pauta do almanaque", channel_id=channel_id, ref_id=iid)
        enqueue("verify_idea", title="Checar fatos da pauta", channel_id=channel_id, ref_id=iid)
    except Exception as ex:  # noqa: BLE001
        log.info("almanaque: fila %s", ex)
    from . import cache
    cache.drop(f"almanac:cal:{channel_id}:")
    return {"ok": True, "idea_id": iid, "title": title}
