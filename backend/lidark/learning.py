"""Aprendizado estatístico do canal — honesto com amostra pequena.

Por que não médias simples: com 8-19 vídeos por canal, a média de 2 vídeos "vence" por acaso, e vídeos de idades
diferentes não são comparáveis (um Short de 6 h não tem as views de um de 6 dias). Aqui:

1. FEATURE STORE: um registro por vídeo publicado (formato, duração, plano de variedade, traços do título e do gancho,
   tema via TF-IDF, horário, campanha, origem da pauta). Vídeos importados sem roteiro ganham o gancho pela legenda
   automática do YouTube (yt-dlp, em cache).
2. RESULTADO NORMALIZADO PELA IDADE: curva típica de crescimento de views estimada por "chain-ladder" (só compara cada
   vídeo com ele mesmo entre duas idades, então vídeos antigos não distorcem a curva). Cada vídeo vira
   z = log(views) − curva(idade); o efeito do canal é estimado com encolhimento (Bayes empírico) e
   rel = z − efeito do canal → "x vezes o normal do canal na mesma idade".
   Também: views aos 2h/6h/24h/48h/7d (interpoladas), views engajadas/views, % médio assistido, retenção aos 3s/meio/fim,
   desempenho relativo de retenção do YouTube, inscritos por mil views, curtidas/comentários por view.
3. MODELOS:
   a) bandit bayesiano por dimensão de variedade (Thompson sampling) com prior hierárquico: efeito global da opção
      (todos os canais) → efeito no canal. Vira pesos para o sorteio do variety.py (que mantém a anti-repetição).
   b) ridge bayesiano pequeno prevendo rel, com validação leave-one-out ANINHADA (a regularização é escolhida dentro
      de cada dobra) — a acurácia relatada é a honesta, fora da amostra.
   c) detector de sinal precoce: com 1-48 h, compara o vídeo com a curva típica na mesma idade e com o quanto esse
      desvio precoce costuma se manter (estimado nos vídeos já maduros).

API pública (usada por outros módulos): prompt_context, predict, recommend_variety, refresh, breakouts, report.
"""
from __future__ import annotations

import json
import logging
import math
import re
import threading
import time
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from sqlmodel import select

from .config import CACHE_DIR
from .db import session
from .models import Channel, Idea, MetricSnapshot, Publication, Script, Video

log = logging.getLogger("lidark.learning")

TZ = ZoneInfo("America/Sao_Paulo")
STATE_PATH = CACHE_DIR / "learning_state.json"
HOOKS_PATH = CACHE_DIR / "learning_hooks.json"
VERSION = 1
MAX_AGE_S = 6 * 3600  # estado mais velho que isso é recalculado na próxima consulta

CENTERS = [1, 2, 4, 6, 9, 12, 18, 24, 36, 48, 72, 96, 120, 168, 240, 336]  # idades (h) da curva típica
FIXED_AGES = {"2h": 2, "6h": 6, "24h": 24, "48h": 48, "7d": 168}
REF_AGE = 48  # "views típicas" do canal são relatadas nesta idade
MIN_TRAIN_AGE = 6  # horas: mais novo que isso só entra no detector de sinal precoce
ANCHOR_MAX_H = 12  # 1ª leitura até 12 h após publicar: interpola a partir de 0 views na publicação

_lock = threading.RLock()
_state: dict[str, Any] | None = None
_ctx_cache: dict[tuple[int, str, str], str] = {}


# ================================================================ utilidades

def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower()


def _clean_title(t: str) -> str:
    return re.sub(r"\s*#shorts\b", "", t or "", flags=re.I).strip()


def _phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _x(v: float) -> str:
    """Fator multiplicativo legível: 1.8 → '1,8x'."""
    return f"{v:.1f}x".replace(".", ",")


def _pct(effect_log: float) -> str:
    p = (math.exp(effect_log) - 1) * 100
    return f"{p:+.0f}%"


def _conf_label(p: float) -> str:
    """p = probabilidade de o efeito ser positivo (ou de a opção ser a melhor)."""
    q = max(p, 1 - p)
    return "forte" if q >= 0.95 else "boa" if q >= 0.85 else "moderada" if q >= 0.7 else "fraca"


def _rank(a: np.ndarray) -> np.ndarray:
    order = np.argsort(a, kind="mergesort")
    r = np.empty(len(a))
    r[order] = np.arange(len(a))
    # empates: posto médio
    for v in np.unique(a):
        idx = np.where(a == v)[0]
        if len(idx) > 1:
            r[idx] = r[idx].mean()
    return r


def _spearman(a: np.ndarray, b: np.ndarray) -> float | None:
    if len(a) < 4:
        return None
    ra, rb = _rank(a), _rank(b)
    if ra.std() == 0 or rb.std() == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


# ================================================================ 1. carga + feature store

_STOP = set("a o as os um uma uns umas de da do das dos e em no na nos nas que por para pra com como se sua seu suas "
            "seus mais foi era ao aos isso essa esse este esta ele ela eles elas voce nao mas ou the of quem qual "
            "quando onde porque por que ate sobre entre sem tem ter ser sao vai vez dia shorts".split())
_CURIOSITY = re.compile(r"\b(verdade|verdadeir|mito|segredo|secret|nunca|ninguem|poucos|esquecid|escondid|proibid|"
                        r"revelad|real\b|misteri|ninguem sabe|chocante|incrivel|bizarr|estranh)", re.I)
_STORY = re.compile(r"\b(o dia em que|a vez em que|a noite em que|quando )", re.I)
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def _tokens(txt: str) -> list[str]:
    words = [w[:6] for w in re.sub(r"[^a-z0-9 ]", " ", _fold(txt)).split() if len(w) >= 3 and w not in _STOP]
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


def title_features(title: str) -> dict[str, float]:
    t = _clean_title(title)
    f = _fold(t)
    words = t.split()
    caps = [w for w in words if len(re.sub(r"[^A-ZÀ-Ý]", "", w)) >= 3 and w.upper() == w and not w.isdigit()]
    ents = [w for w in words[1:] if w[:1].isupper() and w.upper() != w]
    return {
        "t_question": float(t.endswith("?") or t.startswith(("Por que", "Como", "Quem", "Qual", "Onde", "Quando"))),
        "t_number": float(bool(re.search(r"\d", t))),
        "t_caps": float(bool(caps)),
        "t_curiosity": float(bool(_CURIOSITY.search(f))),
        "t_story": float(bool(_STORY.search(f))),
        "t_colon": float(":" in t),
        "t_entity": float(bool(ents)),
        "t_you": float(bool(re.search(r"\b(voce|seu|sua|te)\b", f))),
        "t_emoji": float(bool(_EMOJI.search(t))),
        "t_len": len(t) / 10.0,
    }


def hook_features(hook: str) -> dict[str, float]:
    h = (hook or "").strip()
    f = _fold(h)
    first = f.split()[:8]
    return {
        "h_known": float(bool(h)),
        "h_question": float("?" in h[:140]),
        "h_number": float(any(re.search(r"\d", w) for w in first)),
        "h_you": float(bool(re.search(r"\b(voce|seu|sua|te)\b", " ".join(f.split()[:12])))),
        "h_words": min(40, len(h.split())) / 5.0,
    }


def _hook_cache() -> dict[str, Any]:
    try:
        return json.loads(HOOKS_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def _caption_hook(url: str) -> str:
    """Primeiras ~15 palavras da legenda automática (pt) de um vídeo do YouTube."""
    import httpx

    from .importer import _ydl
    with _ydl({"socket_timeout": 15}) as y:
        d = y.extract_info(url, download=False) or {}
    tracks = {**(d.get("automatic_captions") or {}), **(d.get("subtitles") or {})}
    langs = [k for k in ("pt-orig", "pt", "pt-BR") if k in tracks] + [k for k in tracks if k.startswith("pt")]
    for lang in langs:
        fmts = tracks.get(lang) or []
        f = next((x for x in fmts if x.get("ext") == "json3"), None)
        if not f:
            continue
        r = httpx.get(f["url"], timeout=20, follow_redirects=True)
        events = (r.json() or {}).get("events") or []
        words: list[str] = []
        for ev in events:
            for seg in ev.get("segs") or []:
                words += (seg.get("utf8") or "").split()
            if len(words) >= 15:
                break
        if words:
            return " ".join(words[:15])
    return ""


def fetch_missing_hooks(recs: list[dict[str, Any]], max_n: int = 8) -> int:
    """Busca (e guarda em cache) o gancho de vídeos importados pela legenda automática. Tenta de novo após 3 dias."""
    cache = _hook_cache()
    done = 0
    for r in recs:
        if r["hook"] or not r.get("url") or done >= max_n:
            continue
        c = cache.get(r["external_id"]) or {}
        if c.get("hook") or (c.get("tried") and time.time() - c["tried"] < 3 * 86400):
            continue
        try:
            hook = _caption_hook(r["url"])
        except Exception as e:  # noqa: BLE001
            log.info("legenda %s: %s", r["external_id"], e)
            hook = ""
        cache[r["external_id"]] = {"hook": hook, "tried": time.time()}
        done += 1
    if done:
        HOOKS_PATH.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return done


def _load_records() -> tuple[list[dict[str, Any]], dict[int, str]]:
    """Um registro por vídeo publicado no YouTube: features + série de leituras (idade em horas, views...)."""
    now = _now()
    hooks = _hook_cache()
    with session() as s:
        chans = {c.id: c.name for c in s.exec(select(Channel)).all()}
        pubs = s.exec(select(Publication).where(Publication.status == "published",
                                                Publication.platform == "youtube")).all()
        snaps = s.exec(select(MetricSnapshot).where(MetricSnapshot.platform == "youtube")
                       .order_by(MetricSnapshot.captured_at)).all()
        by_pub: dict[int, list[MetricSnapshot]] = defaultdict(list)
        for m in snaps:
            by_pub[m.publication_id].append(m)
        recs = []
        for p in pubs:
            born = _utc(p.published_at)
            if not born or born > now:
                continue  # agendado (ainda não foi ao ar) ou sem data
            v = s.get(Video, p.video_id) if p.video_id else None
            sc = s.get(Script, v.script_id) if v else None
            idea = s.get(Idea, sc.idea_id) if sc and sc.idea_id else None
            ms = by_pub.get(p.id, [])
            series, last_an, curve, src_fmt = [], None, None, None
            for m in ms:
                age = ((_utc(m.captured_at) or now) - born).total_seconds() / 3600
                raw = m.raw or {}
                src_fmt = src_fmt or raw.get("format")
                if age < 0:
                    continue
                series.append((age, int(m.views or 0), int(m.likes or 0), int(m.comments or 0)))
                if (m.watch_time_minutes or 0) > 0 or (m.engaged_views or 0) > 0:
                    last_an = (age, m)
                if raw.get("retention_curve"):
                    curve = raw["retention_curve"]
            # leituras repetidas (mesma idade) e quedas de views (correções do YouTube): mantém a série monotônica
            clean: list[tuple] = []
            for pt in series:
                if clean and pt[0] - clean[-1][0] < 0.05:
                    clean[-1] = pt
                    continue
                if clean and pt[1] < clean[-1][1]:
                    pt = (pt[0], clean[-1][1], pt[2], pt[3])
                clean.append(pt)
            duration = float((v.duration if v else 0) or p.duration or 0)
            fmt = (sc.format if sc else None) or src_fmt or ("long" if duration > 180 else "short")
            hook = ""
            if sc:
                hook = (sc.hook or (sc.scenes[0].get("text") if sc.scenes else "") or "").strip()
            if not hook:
                hook = ((hooks.get(p.external_id) or {}).get("hook") or "").strip()
            tags = (idea.tags if idea else []) or []
            camp = next((t.split(":", 1)[1] for t in tags if isinstance(t, str) and t.startswith("campanha:")), "")
            local = born.astimezone(TZ)
            recs.append({
                "pub_id": p.id, "video_id": p.video_id, "channel_id": p.channel_id, "external_id": p.external_id,
                "title": _clean_title(sc.title if sc else p.title), "url": p.url, "thumbnail": p.thumbnail_url,
                "published_at": born.isoformat(), "age_h": (now - born).total_seconds() / 3600,
                "format": fmt, "duration": duration, "imported": p.video_id is None,
                "hook": hook, "thumbnail_text": (sc.thumbnail_text if sc else "") or "",
                "variety": (sc.variety if sc else {}) or {}, "campaign": camp,
                "origin": (idea.origin if idea else "") or "", "idea_score": idea.score if idea else None,
                "weekday": local.weekday(), "hour": local.hour,
                "series": clean, "analytics": _analytics(last_an, clean, duration), "curve": curve,
            })
    return recs, chans


def _interp(series: list[tuple], age: float, col: int = 1) -> float | None:
    """Valor acumulado (views por padrão) na idade pedida, interpolando entre leituras (0 na publicação se a 1ª
    leitura foi cedo). None fora do intervalo observado."""
    if not series:
        return None
    pts = [(0.0, 0, 0, 0)] + series if series[0][0] <= ANCHOR_MAX_H else list(series)
    if age < pts[0][0] - 1e-9 or age > pts[-1][0] + 1e-9:
        return None
    for a, b in zip(pts, pts[1:]):
        if a[0] <= age <= b[0]:
            if b[0] - a[0] < 1e-9:
                return float(b[col])
            f = (age - a[0]) / (b[0] - a[0])
            return a[col] + f * (b[col] - a[col])
    return float(pts[-1][col])


def _analytics(last: tuple | None, series: list[tuple], duration: float) -> dict[str, Any]:
    """Métricas do YouTube Analytics da última leitura que as trouxe. O Analytics atrasa ~2 dias: as views engajadas
    são divididas pelas views públicas de ~48 h antes daquela leitura (estimativa, marcada como tal)."""
    if not last:
        return {}
    age, m = last
    out: dict[str, Any] = {"age_h": round(age, 1)}
    base = _interp(series, max(age - 48, 0)) if age >= 60 else None
    if base and base >= 20 and m.engaged_views:
        out["engaged_ratio"] = round(min(1.0, m.engaged_views / base), 3)
    out["engaged_views"] = int(m.engaged_views or 0)
    avp = float(m.avg_view_percentage or 0)
    if (m.watch_time_minutes or 0) >= 3 and 0 < avp < 400:  # leituras com quase nada de dado vêm absurdas (ex.: 3565%)
        out["avg_view_pct"] = round(avp, 1)
        out["avg_view_s"] = round(float(m.avg_view_duration or 0), 1)
    views_now = series[-1][1] if series else 0
    if views_now >= 50:
        out["subs_per_1k"] = round(1000 * (m.subscribers_gained or 0) / views_now, 2)
    return out


# ================================================================ 2. resultado normalizado pela idade

def _video_curve(r: dict[str, Any]) -> dict[int, float]:
    """log(1+views) do vídeo em cada idade-centro coberta pelas leituras."""
    out = {}
    for c in CENTERS:
        v = _interp(r["series"], c)
        if v is not None:
            out[c] = math.log1p(v)
    return out


def _growth_curve(recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Curva típica g(idade) por chain-ladder: o crescimento entre duas idades vizinhas é a mediana do crescimento
    dos vídeos observados nas duas — vídeos antigos (ou melhores) não puxam a curva."""
    ys = [_video_curve(r) for r in recs]
    h = {CENTERS[0]: 0.0}
    support = {}
    for a, b in zip(CENTERS, CENTERS[1:]):
        d = [y[b] - y[a] for y in ys if a in y and b in y]
        support[b] = len(d)
        if len(d) >= 3:
            delta = max(0.0, float(np.median(d)))
        else:  # sem vídeos nas duas idades: crescimento padrão ~ t^0.3, que vai diminuindo
            delta = 0.3 * math.log(b / a) * (0.6 if a >= 72 else 1.0)
        h[b] = h[a] + delta
    hv = [h[c] for c in CENTERS]
    # nível: mediana de (log views − forma) na última idade de cada vídeo
    lv = []
    for r in recs:
        a = _last_age(r)
        y = _interp(r["series"], a) if a else None
        if y is not None and a >= 1:
            lv.append(math.log1p(y) - float(np.interp(math.log(a), np.log(CENTERS), hv)))
    level = float(np.median(lv)) if lv else 0.0
    return {"centers": CENTERS, "g": [level + x for x in hv], "support": support}


def _g(curve: dict[str, Any], age: float) -> float:
    return float(np.interp(math.log(max(age, CENTERS[0])), np.log(curve["centers"]), curve["g"]))


def _last_age(r: dict[str, Any]) -> float:
    return min(r["series"][-1][0], CENTERS[-1]) if r["series"] else 0.0


def _channel_effects(z: np.ndarray, ch: np.ndarray, w: np.ndarray) -> tuple[dict[int, float], float, float]:
    """Efeito de cada canal (Bayes empírico): média do canal encolhida para a média geral conforme a amostra."""
    if len(z) == 0:
        return {}, 0.0, 0.25
    grand = float(np.average(z, weights=w))
    groups = {c: np.where(ch == c)[0] for c in np.unique(ch)}
    means = {c: float(np.average(z[i], weights=w[i])) for c, i in groups.items()}
    resid = np.concatenate([z[i] - means[c] for c, i in groups.items()])
    dof = max(1, len(z) - len(groups))
    s2 = max(0.05, float((resid ** 2).sum() / dof))
    if len(groups) >= 2:
        se = np.array([s2 / len(groups[c]) for c in groups])
        tau2 = max(0.05, float(np.var(list(means.values()), ddof=1) - se.mean()))
    else:
        tau2 = 0.25
    out = {}
    for c, i in groups.items():
        b = (s2 / len(i)) / (s2 / len(i) + tau2)
        out[int(c)] = (1 - b) * means[c] + b * grand
    return out, grand, s2


# ================================================================ 3b. regressão (ridge bayesiano) com LOO aninhado

FEATURES: list[tuple[str, str]] = [
    ("t_question", "Título em pergunta"),
    ("t_number", "Número no título"),
    ("t_caps", "Palavra em CAIXA ALTA no título"),
    ("t_curiosity", "Palavra de curiosidade no título (verdade, mito, segredo, nunca...)"),
    ("t_story", "Título “O dia/A vez em que…”"),
    ("t_colon", "Título com dois-pontos"),
    ("t_entity", "Nome próprio no título"),
    ("t_you", "Título fala com “você”"),
    ("t_len", "Título mais comprido (+10 caracteres)"),
    ("h_question", "Gancho com pergunta"),
    ("h_number", "Número nas 8 primeiras palavras do gancho"),
    ("h_you", "Gancho fala com “você”"),
    ("h_words", "Gancho mais comprido (+5 palavras)"),
    ("dur", "Duração maior (dobro)"),
    ("long", "Vídeo longo"),
    ("slot_morning", "Publicado de manhã (6–12h)"),
    ("slot_evening", "Publicado à noite (18–24h)"),
    ("slot_late", "Publicado de madrugada (0–6h)"),
    ("weekend", "Publicado no fim de semana"),
    ("trend", "Pauta vinda do radar de tendências"),
    ("campaign", "Dentro de campanha (ex.: ENEM)"),
    ("topic", "Tema parecido com vídeos que foram bem"),
]
FEAT_KEYS = [k for k, _ in FEATURES]
FEAT_LABEL = dict(FEATURES)
ALPHAS = [0.3, 1, 3, 10, 30, 100, 300]


def _base_features(r: dict[str, Any]) -> dict[str, float]:
    f = {**title_features(r["title"]), **hook_features(r["hook"])}
    h = r.get("hour", 14)
    f.update({
        "dur": math.log2(max(10.0, r.get("duration") or (60 if r["format"] == "short" else 480))),
        "long": float(r["format"] == "long"),
        "slot_morning": float(6 <= h < 12), "slot_evening": float(18 <= h < 24), "slot_late": float(h < 6),
        "weekend": float(r.get("weekday", 0) >= 5),
        "trend": float(r.get("origin") == "trend"),
        "campaign": float(bool(r.get("campaign"))),
    })
    return f


class _Tfidf:
    def __init__(self, docs: list[str]):
        toks = [set(_tokens(d)) for d in docs]
        df: dict[str, int] = defaultdict(int)
        for t in toks:
            for w in t:
                df[w] += 1
        n = len(docs)
        self.idf = {w: math.log((n + 1) / (c + 1)) + 1 for w, c in df.items() if c >= 1}
        self.vecs = [self.vec(d) for d in docs]

    def vec(self, doc: str) -> dict[str, float]:
        cnt: dict[str, float] = defaultdict(float)
        for w in _tokens(doc):
            if w in self.idf:
                cnt[w] += 1.0
        v = {w: c * self.idf[w] for w, c in cnt.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}

    @staticmethod
    def cos(a: dict[str, float], b: dict[str, float]) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(w, 0.0) for w, x in a.items())


def _doc(r: dict[str, Any]) -> str:
    return f"{r['title']} {r['title']} {r.get('hook', '')} {r.get('thumbnail_text', '')}"


def _knn(sims: np.ndarray, rel: np.ndarray, pool: np.ndarray, k: int = 5) -> float:
    """Média (ponderada pela semelhança) do desempenho dos vídeos de tema mais parecido, encolhida para 0."""
    if len(pool) == 0:
        return 0.0
    s = sims[pool]
    top = np.argsort(-s)[:k]
    w = np.clip(s[top], 0, None) ** 2
    return float((w * rel[pool][top]).sum() / (w.sum() + 0.05))


def _fit(X: np.ndarray, y: np.ndarray, w: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ridge ponderado com intercepto livre. Devolve (beta, A^-1, alavanca h_ii)."""
    n, p = X.shape
    Xd = np.hstack([np.ones((n, 1)), X])
    P = np.eye(p + 1) * alpha
    P[0, 0] = 1e-6
    A = Xd.T @ (Xd * w[:, None]) + P
    Ai = np.linalg.inv(A)
    beta = Ai @ (Xd.T @ (w * y))
    hdiag = np.einsum("ij,jk,ik->i", Xd, Ai, Xd) * w
    return beta, Ai, hdiag


SUBSETS: dict[str, list[str]] = {  # conjuntos de traços candidatos — a escolha é feita DENTRO de cada dobra do LOO
    "completo": FEAT_KEYS,
    "tema": ["topic"],
    "tema+formato": ["topic", "dur", "long"],
    "título+tema": [k for k in FEAT_KEYS if k.startswith("t_")] + ["topic"],
    "gancho+tema": [k for k in FEAT_KEYS if k.startswith("h_")] + ["topic"],
}


def _mask(name: str) -> np.ndarray:
    keep = set(SUBSETS[name])
    return np.array([k in keep for k in FEAT_KEYS])


def _fit_masked(X: np.ndarray, y: np.ndarray, w: np.ndarray, mask: np.ndarray,
                alpha: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ridge só com as colunas do conjunto; devolve beta/A^-1 no tamanho completo (zeros fora do conjunto)."""
    beta_s, Ai_s, hd = _fit(X[:, mask], y, w, alpha)
    sel = np.concatenate([[True], mask])
    beta = np.zeros(len(sel))
    beta[sel] = beta_s
    Ai = np.zeros((len(sel), len(sel)))
    Ai[np.ix_(sel, sel)] = Ai_s
    return beta, Ai, hd


def _select(X: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[str, float]:
    """Conjunto de traços + regularização com menor erro leave-one-out (fórmula fechada) nos dados de treino."""
    best, best_err = ("tema", ALPHAS[-1]), float("inf")
    for name in SUBSETS:
        mk = _mask(name)
        Xm = X[:, mk]
        for a in ALPHAS:
            beta, _, hd = _fit(Xm, y, w, a)
            e = (y - np.hstack([np.ones((len(y), 1)), Xm]) @ beta) / np.clip(1 - hd, 0.05, None)
            err = float(np.average(e ** 2, weights=w))
            if err < best_err - 1e-9:
                best, best_err = (name, a), err
    return best


def _standardize(F: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mu, sd = F.mean(0), F.std(0)
    sd = np.where(sd < 1e-6, 1.0, sd)
    return (F - mu) / sd, mu, sd


def _design(base: list[dict[str, float]], topic: np.ndarray) -> np.ndarray:
    F = np.array([[b.get(k, 0.0) for k in FEAT_KEYS[:-1]] for b in base], dtype=float)
    return np.hstack([F, topic[:, None]])


PERMUTATIONS = 20
TIE = 0.02  # diferença de previsão (log) abaixo da qual duas pautas empatam


def _loo_eval(base: list[dict[str, float]], z: np.ndarray, ch: np.ndarray, w: np.ndarray, sims: np.ndarray,
              quick: bool = False) -> dict[str, Any]:
    """LOO aninhado: efeito do canal, tema vizinho, padronização e alfa recalculados sem o vídeo i."""
    n = len(z)
    loo, loo_feat, target = np.zeros(n), np.zeros(n), np.zeros(n)
    chosen: dict[str, int] = defaultdict(int)
    idx = np.arange(n)
    for i in range(n):
        tr = idx[idx != i]
        eff, grand, _ = _channel_effects(z[tr], ch[tr], w[tr])
        mu = np.array([eff.get(int(c), grand) for c in ch])
        rel = z - mu
        topic = np.array([_knn(sims[j], rel, tr[tr != j]) for j in range(n)])
        F = _design(base, topic)
        Xs, m, sd = _standardize(F[tr])
        name, a = _select(Xs, rel[tr], w[tr])
        chosen[name] += 1
        beta, _, _ = _fit_masked(Xs, rel[tr], w[tr], _mask(name), a)
        xi = (F[i] - m) / sd
        loo_feat[i] = float(xi @ beta[1:])  # só a parte das features (sem o intercepto da dobra)
        loo[i] = float(beta[0]) + loo_feat[i]
        target[i] = rel[i]  # alvo fora da amostra (efeito do canal sem o vídeo i)
    sse_m = float(np.average((target - loo) ** 2, weights=w))
    sse_0 = float(np.average(target ** 2, weights=w))
    r2 = 1 - sse_m / sse_0 if sse_0 > 0 else 0.0
    # métricas de ORDEM só com a parte das features (o intercepto de cada dobra anti-correlaciona com o alvo) e
    # diferenças < 2% contam como empate: com regularização forte, o resto seria só artefato do LOO
    q = np.round(loo_feat / TIE)
    rho = (_spearman(q, target) or 0.0) if q.std() > 0 else 0.0
    pairs = agree = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            if ch[i] == ch[j] and abs(target[i] - target[j]) > 0.1:
                pairs += 1
                d = loo_feat[i] - loo_feat[j]
                agree += 0.5 if abs(d) < TIE else float(d * (target[i] - target[j]) > 0)
    conc = float(agree / pairs) if pairs else None
    return {"chosen": dict(chosen), "r2": r2, "spearman": rho, "concordance": conc, "pairs": int(pairs), "sse_m": sse_m, "sse_0": sse_0,
            "pred": loo, "target": target}


def _train(recs: list[dict[str, Any]], z: np.ndarray, ch: np.ndarray, w: np.ndarray, sims: np.ndarray) -> dict[str, Any]:
    n = len(recs)
    base = [_base_features(r) for r in recs]
    if n < 8:
        return {"n": n, "ok": False}
    real = _loo_eval(base, z, ch, w, sims)
    # teste de permutação: o mesmo procedimento com os resultados embaralhados dentro de cada canal. Com amostra pequena
    # o LOO é viesado para baixo quando não há sinal; comparar com esse "acaso" diz se há aprendizado de verdade.
    rng = np.random.default_rng(11)
    null = []
    for _ in range(PERMUTATIONS):
        zp = z.copy()
        for c in np.unique(ch):
            ii = np.where(ch == c)[0]
            zp[ii] = zp[rng.permutation(ii)]
        null.append(_loo_eval(base, zp, ch, w, sims, quick=True))
    nr2 = np.array([x["r2"] for x in null])
    nrho = np.array([x["spearman"] for x in null])
    ncon = np.array([x["concordance"] if x["concordance"] is not None else 0.5 for x in null])
    # p-valor pelo R² fora da amostra (a métrica que não sofre com empates/artefatos de ordem)
    p_val = float((1 + (nr2 >= real["r2"]).sum()) / (1 + len(nr2)))
    r2, rho, conc, sse_m = real["r2"], real["spearman"], real["concordance"], real["sse_m"]
    loo, loo_base = real["pred"], real["target"]
    idx = np.arange(n)
    # ---- modelo final com todos os vídeos
    eff, grand, s2 = _channel_effects(z, ch, w)
    mu = np.array([eff.get(int(c), grand) for c in ch])
    rel = z - mu
    topic = np.array([_knn(sims[j], rel, idx[idx != j]) for j in range(n)])
    F = _design(base, topic)
    Xs, m, sd = _standardize(F)
    subset, a = _select(Xs, rel, w)
    beta, Ai, _ = _fit_masked(Xs, rel, w, _mask(subset), a)
    sigma2 = max(0.02, sse_m)  # variância do erro de previsão medida fora da amostra (honesta)
    cov = sigma2 * Ai
    coefs = []
    for j, k in enumerate(FEAT_KEYS):
        b, v = beta[j + 1] / sd[j], cov[j + 1, j + 1] / sd[j] ** 2  # efeito por unidade original do traço
        if k == "dur":
            pass  # unidade = dobrar a duração (log2)
        if not _mask(subset)[j]:
            continue
        se = math.sqrt(max(v, 1e-12))
        coefs.append({"key": k, "label": FEAT_LABEL[k], "effect": float(b), "se": se, "p_pos": _phi(b / se),
                      "share": float(F[:, j].mean()) if k not in ("t_len", "h_words", "dur", "topic") else None})
    if r2 >= 0.1 and p_val <= 0.05:
        verdict = "já ajuda a escolher entre pautas (melhor que a média do canal e que o acaso)"
    elif r2 > 0 and p_val <= 0.2:
        verdict = "sinal fraco: um pouco melhor que chutar a média do canal"
    else:
        verdict = "ainda NÃO prevê melhor que a média do canal — use só como palpite"
    return {"n": n, "ok": True, "alpha": a, "subset": subset, "subset_folds": real["chosen"], "beta": beta.tolist(), "cov": cov.tolist(), "mu": m.tolist(), "sd": sd.tolist(),
            "sigma2": sigma2, "rel_sd": float(math.sqrt(max(0.02, np.average(rel ** 2, weights=w)))),
            "loo": {"r2": round(r2, 3), "spearman": None if rho is None else round(rho, 3),
                    "concordance": None if conc is None else round(conc, 3), "pairs": real["pairs"],
                    "rmse": round(math.sqrt(sse_m), 3), "rmse_baseline": round(math.sqrt(real["sse_0"]), 3),
                    "null_r2": round(float(nr2.mean()), 3), "null_spearman": round(float(nrho.mean()), 3),
                    "null_concordance": round(float(ncon.mean()), 3), "p_value": round(p_val, 3),
                    "skill_r2": round(float(r2 - nr2.mean()), 3)},
            "loo_pred": loo.tolist(), "loo_target": loo_base.tolist(), "verdict": verdict, "coefs": coefs}


# ================================================================ 3a. bandit hierárquico por dimensão de variedade

TAU_GLOBAL = 0.35  # desvio a priori do efeito de uma opção (log-views): ±35% é plausível
TAU_CHANNEL = 0.25  # quanto o efeito num canal pode fugir do efeito global
DRAWS = 4000


def _dims() -> dict[str, dict[str, Any]]:
    from .growth import DIMENSIONS, LABELS
    from .variety import CTA_STYLES, DURATION_BANDS, GRAPHIC_DOSES, HOOKS, LOOK_OPTIONS, STRUCTURES, TITLES
    opts = {"structure": list(STRUCTURES), "hook_style": list(HOOKS), "title_style": list(TITLES),
            "cta_style": [str(i) for i in range(len(CTA_STYLES))], "graphics": [d[0] for d in GRAPHIC_DOSES],
            "duration": list(DURATION_BANDS), "grade": LOOK_OPTIONS["grade"], "caption": LOOK_OPTIONS["caption"],
            "intro": LOOK_OPTIONS["intro"], "outro": LOOK_OPTIONS["outro"], "thumb_variant": [str(i) for i in range(8)]}
    labels = {**LABELS, "structure": {k: v["name"] for k, v in STRUCTURES.items()},
              "cta_style": {str(i): s[:48] for i, s in enumerate(CTA_STYLES)},
              "thumb_variant": {str(i): f"Layout {i + 1}" for i in range(8)}}
    out = {"structure": {"label": "Estrutura narrativa", "get": lambda p: p.get("structure")},
           "cta_style": {"label": "Estilo de CTA", "get": lambda p: p.get("cta_style")}}
    for k, (lab, get) in DIMENSIONS.items():
        out[k] = {"label": lab, "get": get}
    for k, d in out.items():
        d["options"] = opts.get(k, [])
        d["names"] = labels.get(k, {})
    return out


def _bandit(recs: list[dict[str, Any]], rel: np.ndarray, w: np.ndarray, sigma2: float,
            channels: list[int]) -> dict[str, Any]:
    rng = np.random.default_rng(7)
    dims = _dims()
    out: dict[str, Any] = {}
    for key, d in dims.items():
        vals = []
        for r in recs:
            try:
                v = d["get"](r["variety"]) if r["variety"] else None
            except Exception:  # noqa: BLE001
                v = None
            vals.append(None if v in (None, "") else str(v))
        if not any(vals):
            continue
        options = list(d["options"]) or sorted({v for v in vals if v})
        for v in vals:
            if v and v not in options:
                options.append(v)
        # efeito global da opção (todos os canais), centrado na média das opções testadas
        obs = defaultdict(list)
        for v, y, wi, r in zip(vals, rel, w, recs):
            if v:
                obs[v].append((float(y), float(wi), r["channel_id"]))
        center = float(np.average([y for v in obs for y, _, _ in obs[v]], weights=[wi for v in obs for _, wi, _ in obs[v]]))
        glob = {}
        for o in options:
            ys = obs.get(o, [])
            prec = 1 / TAU_GLOBAL ** 2 + sum(wi for _, wi, _ in ys) / sigma2
            mean = (sum(wi * (y - center) for y, wi, _ in ys) / sigma2) / prec
            glob[o] = (mean, 1 / prec, len(ys))
        per_ch = {}
        for cid in channels + [0]:  # 0 = todos os canais (efeito global)
            post = {}
            for o in options:
                gm, gv, gn = glob[o]
                if cid == 0:
                    post[o] = (gm, gv, gn)
                    continue
                ys = [(y, wi) for y, wi, c in obs.get(o, []) if c == cid]
                pv = TAU_CHANNEL ** 2 + gv
                prec = 1 / pv + sum(wi for _, wi in ys) / sigma2
                mean = (gm / pv + sum(wi * (y - center) for y, wi in ys) / sigma2) / prec
                post[o] = (mean, 1 / prec, len(ys))
            means = np.array([post[o][0] for o in options])
            sds = np.sqrt([post[o][1] for o in options])
            draws = rng.normal(means, sds, size=(DRAWS, len(options)))
            pbest = np.bincount(draws.argmax(1), minlength=len(options)) / DRAWS
            K = len(options)
            rows = []
            for j, o in enumerate(options):
                m_, v_, n_ = post[o]
                sd_ = math.sqrt(v_)
                p_mix = 0.7 * pbest[j] + 0.3 / K  # sempre sobra exploração
                # raiz: suaviza — opções com 1 vídeo ganham chance por serem incertas (Thompson), mas sem dominar
                mult = min(2.0, max(0.5, math.sqrt(K * p_mix)))
                rows.append({"key": o, "label": d["names"].get(o, o), "n": n_,
                             "n_all": glob[o][2], "effect": round(m_, 4), "lo": round(m_ - 1.2816 * sd_, 4),
                             "hi": round(m_ + 1.2816 * sd_, 4), "p_pos": round(_phi(m_ / sd_), 3),
                             "p_best": round(float(pbest[j]), 3), "mult": round(mult, 3)})
            rows.sort(key=lambda x: -x["effect"])
            per_ch[cid] = {"options": rows, "tested": sum(1 for x in rows if x["n"] > 0),
                           "n": sum(x["n"] for x in rows)}
        out[key] = {"label": d["label"], "channels": per_ch}
    return out


# ================================================================ 3c. sinal precoce

def _early_model(recs: list[dict[str, Any]], curve: dict[str, Any], eff: dict[int, float], grand: float) -> dict[str, Any]:
    """Para cada idade-centro até 48 h: desvio típico do vídeo nessa idade e quanto desse desvio se mantém
    (regressão do resultado final sobre o desvio precoce, nos vídeos já maduros)."""
    out = {}
    for c in [x for x in CENTERS if x <= 48]:
        xs, ys = [], []
        for r in recs:
            final_age = _last_age(r)
            if final_age < max(3 * c, 48):
                continue
            v = _interp(r["series"], c)
            vf = _interp(r["series"], final_age)
            if v is None or vf is None:
                continue
            mu = eff.get(r["channel_id"], grand)
            xs.append(math.log1p(v) - _g(curve, c) - mu)
            ys.append(math.log1p(vf) - _g(curve, final_age) - mu)
        if len(xs) >= 5:
            x, y = np.array(xs), np.array(ys)
            sd = float(max(0.15, x.std()))
            rho = float(np.clip((x * y).sum() / max(1e-6, (x * x).sum()), 0.2, 1.0))
            resid = float(max(0.1, (y - rho * x).std()))
            out[c] = {"sd": sd, "rho": rho, "resid": resid, "n": len(xs)}
        else:
            out[c] = {"sd": 0.6, "rho": 0.6, "resid": 0.5, "n": len(xs), "prior": True}
    return out


# ================================================================ cálculo completo

def _compute(fetch_hooks: bool = False) -> dict[str, Any]:
    t0 = time.time()
    recs, chans = _load_records()
    if fetch_hooks:
        try:
            if fetch_missing_hooks(recs):
                recs, chans = _load_records()
        except Exception as e:  # noqa: BLE001
            log.info("ganchos por legenda: %s", e)
    recs = [r for r in recs if r["series"]]
    curve = _growth_curve(recs)
    # resultado normalizado de cada vídeo (na última idade observada, limitada a 14 dias)
    for r in recs:
        a = _last_age(r)
        v = _interp(r["series"], a)
        r["z"] = (math.log1p(v) - _g(curve, a)) if (v is not None and a >= 1) else None
        r["views"] = r["series"][-1][1]
        r["likes"] = r["series"][-1][2]
        r["comments"] = r["series"][-1][3]
        r["views_at"] = {k: (None if (x := _interp(r["series"], h)) is None else round(x)) for k, h in FIXED_AGES.items()}
        vw = max(1, r["views"])
        r["like_rate"] = round(r["likes"] / vw, 4) if r["views"] >= 30 else None
        r["comment_rate"] = round(r["comments"] / vw, 4) if r["views"] >= 30 else None
        q = {}
        if r.get("curve") and (r["duration"] or 0) > 0:
            try:
                from .retention import curve_quality
                q = curve_quality(r["curve"], r["duration"])
            except Exception as e:  # noqa: BLE001
                log.info("curva %s: %s", r["pub_id"], e)
        r["retention"] = q
    train = [r for r in recs if r["z"] is not None and _last_age(r) >= MIN_TRAIN_AGE]
    # winsorização: Shorts que o YouTube quase não distribuiu (2-10 views) viram outliers enormes em log e dominariam
    # os modelos; limitados a ±2 (≈7x) em torno da mediana — continuam sendo "os piores", só não decidem tudo sozinhos
    zmed = float(np.median([r["z"] for r in train])) if train else 0.0
    for r in recs:
        if r["z"] is not None:
            r["z_raw"] = r["z"]
            r["z"] = float(np.clip(r["z"], zmed - 2.0, zmed + 2.0))
    z = np.array([r["z"] for r in train])
    ch = np.array([r["channel_id"] for r in train])
    w = np.array([min(1.0, max(0.35, math.log1p(_last_age(r)) / math.log1p(72))) for r in train])
    eff, grand, s2 = _channel_effects(z, ch, w)
    for r in recs:
        mu = eff.get(r["channel_id"], grand)
        r["rel"] = None if r["z"] is None else r["z"] - mu
    tf = _Tfidf([_doc(r) for r in train]) if train else None
    sims = np.array([[_Tfidf.cos(a, b) if i != j else 0.0 for j, b in enumerate(tf.vecs)]
                     for i, a in enumerate(tf.vecs)]) if tf and train else np.zeros((0, 0))
    model = _train(train, z, ch, w, sims) if len(train) >= 8 else {"n": len(train), "ok": False}
    if model.get("ok"):
        for r, p in zip(train, model["loo_pred"]):
            r["loo_pred"] = p
    rel = np.array([r["rel"] for r in train]) if train else np.zeros(0)
    sigma2 = model.get("sigma2") or max(0.05, float(np.average(rel ** 2, weights=w)) if len(rel) else 0.3)
    bandit = _bandit(train, rel, w, sigma2, sorted(chans)) if train else {}
    early = _early_model(recs, curve, eff, grand)
    # nota da IA na pauta (Idea.score) × desempenho real: quanto a nota prevê?
    pairs = [(r["idea_score"], r["rel"]) for r in train if r["idea_score"] is not None]
    idea_rho = _spearman(np.array([a for a, _ in pairs], float), np.array([b for _, b in pairs])) if len(pairs) >= 6 else None
    # temas (termos) que aparecem em vencedores × perdedores, por canal
    topics = _topic_terms(train)
    state = {
        "version": VERSION, "computed_at": _now().isoformat(), "seconds": round(time.time() - t0, 2),
        "channels": {int(k): v for k, v in chans.items()}, "curve": curve,
        "channel_effect": {int(k): v for k, v in eff.items()}, "grand": grand, "within_var": s2,
        "records": [_slim(r) for r in recs], "model": model, "bandit": _jsonable_bandit(bandit), "early": early,
        "idea_score_spearman": None if idea_rho is None else round(idea_rho, 3), "idea_score_n": len(pairs),
        "topics": topics, "tfidf": {"idf": tf.idf if tf else {}, "pubs": [r["pub_id"] for r in train]},
    }
    return state


def _topic_terms(train: list[dict[str, Any]]) -> dict[int, dict[str, list]]:
    out: dict[int, dict[str, list]] = {}
    by_ch: dict[int, list] = defaultdict(list)
    for r in train:
        by_ch[r["channel_id"]].append(r)
    for cid, rs in by_ch.items():
        terms: dict[str, list[float]] = defaultdict(list)
        words: dict[str, str] = {}
        for r in rs:
            for raw in set(re.sub(r"[^\wÀ-ú ]", " ", r["title"]).split()):
                k = _fold(raw)[:6]
                if len(k) < 4 or k in _STOP:
                    continue
                terms[k].append(r["rel"])
                words.setdefault(k, raw.lower())
        scored = [(words[k], sum(v) / (len(v) + 2), len(v)) for k, v in terms.items() if len(v) >= 2]
        scored.sort(key=lambda x: -x[1])
        out[cid] = {"win": [list(x) for x in scored[:6] if x[1] > 0.1], "lose": [list(x) for x in scored[::-1][:6] if x[1] < -0.1]}
    return out


def _slim(r: dict[str, Any]) -> dict[str, Any]:
    keep = ("pub_id", "video_id", "channel_id", "external_id", "title", "url", "thumbnail", "published_at", "age_h", "format",
            "duration", "imported", "hook", "thumbnail_text", "campaign", "origin", "idea_score", "weekday", "hour",
            "z", "rel", "views", "likes", "comments", "views_at", "like_rate", "comment_rate", "retention", "analytics",
            "loo_pred")
    out = {k: r.get(k) for k in keep}
    out["variety"] = {k: v for k, v in (r.get("variety") or {}).items() if k != "avoid_openings"}
    out["series"] = [[round(a, 2), v] for a, v, *_ in r["series"]]
    return out


def _jsonable_bandit(b: dict[str, Any]) -> dict[str, Any]:
    return {k: {"label": v["label"], "channels": {str(c): x for c, x in v["channels"].items()}} for k, v in b.items()}


# ================================================================ estado (cache)

def _get_state() -> dict[str, Any]:
    global _state
    with _lock:
        if _state and time.time() - _state.get("_loaded", 0) < MAX_AGE_S:
            return _state
        if _state is None:
            try:
                st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
                age = (_now() - datetime.fromisoformat(st["computed_at"])).total_seconds()
                if st.get("version") == VERSION and age < MAX_AGE_S:
                    st["_loaded"] = time.time() - age
                    _state = _restore(st)
                    return _state
            except Exception:  # noqa: BLE001
                pass
        try:
            _set_state(_compute(fetch_hooks=False))
        except Exception:  # noqa: BLE001
            log.exception("aprendizado: falha ao calcular")
            if _state is None:
                _state = {"records": [], "model": {"ok": False}, "bandit": {}, "channels": {}, "_loaded": time.time()}
        return _state


def _restore(st: dict[str, Any]) -> dict[str, Any]:
    st["channels"] = {int(k): v for k, v in st.get("channels", {}).items()}
    st["channel_effect"] = {int(k): v for k, v in st.get("channel_effect", {}).items()}
    st["early"] = {int(k): v for k, v in st.get("early", {}).items()}
    st["topics"] = {int(k): v for k, v in st.get("topics", {}).items()}
    return st


def _set_state(st: dict[str, Any]) -> None:
    global _state
    st["_loaded"] = time.time()
    try:
        STATE_PATH.write_text(json.dumps({k: v for k, v in st.items() if k != "_loaded"}, ensure_ascii=False, default=str),
                              encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        log.info("aprendizado: não salvou cache: %s", e)
    with _lock:
        _state = _restore(json.loads(json.dumps({k: v for k, v in st.items()}, default=str)))
        _state["_loaded"] = time.time()
        _ctx_cache.clear()


def refresh(channel_id: int | None = None) -> dict[str, Any]:
    """Recalcula tudo (o modelo é um só, compartilhado entre canais). Seguro chamar após cada coleta de métricas."""
    with _lock:
        st = _compute(fetch_hooks=True)
        _set_state(st)
    m = st.get("model") or {}
    recs = [r for r in st["records"] if channel_id is None or r["channel_id"] == channel_id]
    return {"ok": True, "computed_at": st["computed_at"], "seconds": st["seconds"], "videos": len(recs),
            "trained": m.get("n", 0), "loo": m.get("loo"), "verdict": m.get("verdict")}


# ================================================================ API pública

def _rec_views_typical(st: dict[str, Any], cid: int, age: float = REF_AGE) -> float:
    mu = st.get("channel_effect", {}).get(cid, st.get("grand", 0.0))
    return max(0.0, math.expm1(_g(st["curve"], age) + mu)) if st.get("curve") else 0.0


def _bandit_rows(st: dict[str, Any], dim: str, cid: int | None) -> list[dict[str, Any]]:
    d = (st.get("bandit") or {}).get(dim) or {}
    return ((d.get("channels") or {}).get(str(cid or 0)) or {}).get("options") or []


def recommend_variety(channel_id: int) -> dict[str, dict[str, float]]:
    """{dimensão: {opção: peso}} na escala do variety._pick (50 = neutro; 25 = metade da chance; 100 = o dobro).
    Só dimensões com algum vídeo medido. A anti-repetição e o piso de exploração continuam no variety.py."""
    try:
        st = _get_state()
    except Exception:  # noqa: BLE001
        return {}
    out: dict[str, dict[str, float]] = {}
    for dim in (st.get("bandit") or {}):
        rows = _bandit_rows(st, dim, channel_id)
        if not rows or not any(r["n_all"] for r in rows):
            continue
        n_dim = sum(r["n"] for r in rows)
        weights = {}
        for r in rows:
            m = r["mult"]
            if dim == "duration":  # mantém o palpite inicial (Shorts curtos) até haver dados, desaparecendo aos poucos
                from .variety import DURATION_PRIOR
                pm = 1 + max(-0.5, min(1.0, (DURATION_PRIOR.get(r["key"], 50) - 50) / 50))
                m = min(2.0, max(0.5, m * pm ** (1 / (1 + n_dim / 8))))
            weights[r["key"]] = round(50 + 50 * (m - 1), 1)
        out[dim] = weights
    return out


def variety_detail(channel_id: int | None) -> list[dict[str, Any]]:
    st = _get_state()
    out = []
    for dim, d in (st.get("bandit") or {}).items():
        rows = _bandit_rows(st, dim, channel_id)
        if rows:
            out.append({"key": dim, "label": d["label"], "options": rows,
                        "tested": sum(1 for r in rows if r["n"]), "n": sum(r["n"] for r in rows)})
    return out


def _features_for(st: dict[str, Any], channel_id: int, title: str, hook: str, fmt: str,
                  extra: dict[str, Any]) -> tuple[np.ndarray | None, list[dict[str, Any]], float]:
    m = st.get("model") or {}
    recs = {r["pub_id"]: r for r in st["records"]}
    idf = (st.get("tfidf") or {}).get("idf") or {}
    pubs = (st.get("tfidf") or {}).get("pubs") or []
    tf = _Tfidf.__new__(_Tfidf)
    tf.idf = idf
    q = tf.vec(f"{title} {title} {hook} {extra.get('thumbnail_text', '')}")
    sims = []
    for pid in pubs:
        r = recs.get(pid)
        if r and r.get("rel") is not None:
            sims.append((_Tfidf.cos(q, tf.vec(_doc(r))) * (1.15 if r["channel_id"] == channel_id else 1.0), r))
    sims.sort(key=lambda x: -x[0])
    if sims:
        s = np.array([x[0] for x in sims])
        rel = np.array([x[1]["rel"] for x in sims])
        topic = _knn(s, rel, np.arange(len(s)))
    else:
        topic = 0.0
    plan = extra.get("variety") or {}
    seconds = extra.get("seconds") or plan.get("seconds") or extra.get("duration")
    when = extra.get("published_at") or extra.get("when")
    try:
        local = datetime.fromisoformat(str(when)).astimezone(TZ) if when else None
    except ValueError:
        local = None
    r = {"title": title, "hook": hook, "format": fmt, "duration": float(seconds or 0),
         "hour": local.hour if local else int(extra.get("hour", 14)), "weekday": local.weekday() if local else int(extra.get("weekday", 2)),
         "origin": extra.get("origin", ""), "campaign": extra.get("campaign", "")}
    if not m.get("ok"):
        return None, sims, topic
    b = _base_features(r)
    F = np.array([b.get(k, 0.0) for k in FEAT_KEYS[:-1]] + [topic])
    return F, sims, topic


def predict(channel_id: int, title: str, hook: str = "", fmt: str = "short", extra: dict | None = None) -> dict[str, Any]:
    """Previsão do desempenho normalizado (vs o normal do canal na mesma idade), com incerteza honesta.
    score 0-100 = percentil esperado entre os vídeos do sistema (50 = típico do canal)."""
    extra = extra or {}
    st = _get_state()
    m = st.get("model") or {}
    F, sims, topic = _features_for(st, channel_id, title, hook, fmt, extra)
    similar = [{"title": r["title"], "views": r["views"], "url": r["url"], "x": round(math.exp(r["rel"]), 2),
                "channel_id": r["channel_id"]} for s, r in sims[:3] if s > 0.05]
    reasons: list[str] = []
    if F is None:
        return {"score": 50, "low": 20, "high": 80, "reasons": ["Ainda sem vídeos medidos o bastante para prever."],
                "similar": similar, "confidence": "nenhuma"}
    mu, sd = np.array(m["mu"]), np.array(m["sd"])
    beta, cov = np.array(m["beta"]), np.array(m["cov"])
    x = np.concatenate([[1.0], (F - mu) / sd])
    pred = float(x @ beta)
    var = float(m["sigma2"] + x @ cov @ x)
    # escolhas de variedade já sorteadas (se vierem): efeito do bandit no canal, pela metade (evita contar duas vezes)
    plan = extra.get("variety") or {}
    if plan:
        dims = _dims()
        for dim, d in dims.items():
            try:
                v = d["get"](plan)
            except Exception:  # noqa: BLE001
                v = None
            row = next((o for o in _bandit_rows(st, dim, channel_id) if o["key"] == str(v)), None) if v not in (None, "") else None
            if row and row["n"] >= 2 and abs(row["effect"]) >= 0.1:
                pred += 0.5 * row["effect"]
                var += 0.25 * ((row["hi"] - row["lo"]) / 2.563) ** 2
                reasons.append(f"{d['label']} “{row['label']}”: {_pct(row['effect'])} no canal até agora ({row['n']} vídeos, "
                               f"confiança {_conf_label(row['p_pos'])})")
    contrib = [(FEAT_KEYS[j], float(x[j + 1] * beta[j + 1])) for j in range(len(FEAT_KEYS))]
    contrib.sort(key=lambda c: -abs(c[1]))
    for k, c in contrib[:4]:
        if abs(c) < 0.04:
            continue
        if k == "topic":
            coef = beta[FEAT_KEYS.index(k) + 1]
            if topic > 0.05 and coef < 0:
                reasons.append(f"Tema parecido com vídeos que já foram bem: {_pct(c)} — até agora, repetir tema de sucesso "
                               "rendeu MENOS (saturação); busque um ângulo novo")
            elif topic < -0.05 and coef < 0:
                reasons.append(f"Tema parecido com vídeos que foram mal: {_pct(c)} (pelo histórico, mudar o ângulo ajuda)")
            else:
                reasons.append(f"Tema em relação aos vídeos parecidos: {_pct(c)}")
            continue
        lab = FEAT_LABEL[k] if F[FEAT_KEYS.index(k)] or k in ("t_len", "h_words", "dur") else f"Sem: {FEAT_LABEL[k].lower()}"
        reasons.append(f"{lab}: {_pct(c)}")
    if similar:
        reasons.append("Parecido com: " + "; ".join(f"“{s['title'][:50]}” ({_x(s['x'])} o normal)" for s in similar[:2]))
    if (m.get("loo") or {}).get("r2", 0) < 0.03:
        reasons.append("Atenção: o modelo ainda não supera a média do canal fora da amostra — trate como palpite.")
    sdev = math.sqrt(var)
    rs = m.get("rel_sd") or 0.5
    to_score = lambda v: int(round(100 * _phi(v / rs)))  # noqa: E731
    typical = _rec_views_typical(st, channel_id)
    return {"score": to_score(pred), "low": to_score(pred - 1.2816 * sdev), "high": to_score(pred + 1.2816 * sdev),
            "reasons": reasons[:6], "similar": similar,
            "x_normal": round(math.exp(pred), 2), "x_low": round(math.exp(pred - 1.2816 * sdev), 2),
            "x_high": round(math.exp(pred + 1.2816 * sdev), 2),
            "views_48h": {"mid": round(typical * math.exp(pred)), "low": round(typical * math.exp(pred - 1.2816 * sdev)),
                          "high": round(typical * math.exp(pred + 1.2816 * sdev))},
            "confidence": "baixa" if (m.get("loo") or {}).get("r2", 0) < 0.03 else "moderada" if m["loo"]["r2"] < 0.15 else "boa"}


def breakouts(hours: int = 48) -> list[dict[str, Any]]:
    """Vídeos de até `hours` horas: desvio da curva típica na mesma idade, com projeção para 7 dias."""
    from . import cache  # vários canais/telas pedem ao mesmo tempo: lê as séries no máximo 1x por minuto
    return cache.get(f"learning:breakouts:{hours}", lambda: _breakouts(hours), ttl=60, stale=600)


def _breakouts(hours: int) -> list[dict[str, Any]]:
    st = _get_state()
    recs, _ = _load_records()  # leituras frescas (o estado pode ter algumas horas)
    curve, early = st.get("curve"), st.get("early") or {}
    if not curve:
        return []
    out = []
    for r in recs:
        if not r["series"] or not (1 <= r["age_h"] <= hours):
            continue
        a = r["series"][-1][0]
        if a < 1:
            continue
        v = r["series"][-1][1]
        mu = st["channel_effect"].get(r["channel_id"], st.get("grand", 0.0))
        dev = math.log1p(v) - _g(curve, a) - mu
        c = min(early, key=lambda k: abs(math.log(k) - math.log(a))) if early else None
        em = early.get(c) if c else {"sd": 0.6, "rho": 0.6, "resid": 0.5, "n": 0}
        zsc = dev / em["sd"]
        proj = dev * em["rho"]
        typical7 = math.expm1(_g(curve, 168) + mu)
        status = ("breakout" if zsc >= 1.28 else "acima" if zsc >= 0.5 else "flop" if zsc <= -1.28
                  else "abaixo" if zsc <= -0.5 else "normal")
        vel = None
        if len(r["series"]) >= 2:
            (a0, v0, *_), (a1, v1, *_) = r["series"][-2], r["series"][-1]
            if a1 - a0 > 0.2:
                vel = round((v1 - v0) / (a1 - a0), 1)
        out.append({"pub_id": r["pub_id"], "channel_id": r["channel_id"], "channel": st["channels"].get(r["channel_id"], ""),
                    "title": r["title"], "url": r["url"], "thumbnail": r["thumbnail"], "age_h": round(r["age_h"], 1),
                    "views": v, "expected_now": round(math.expm1(_g(curve, a) + mu)), "x_normal": round(math.exp(dev), 2),
                    "z": round(zsc, 2), "status": status, "views_per_h": vel,
                    "proj_7d": round(typical7 * math.exp(proj)),
                    "proj_7d_low": round(typical7 * math.exp(proj - 1.2816 * em["resid"])),
                    "proj_7d_high": round(typical7 * math.exp(proj + 1.2816 * em["resid"])),
                    "p_above": round(_phi(proj / em["resid"]), 2), "calibration_n": em.get("n", 0)})
    out.sort(key=lambda x: -abs(x["z"]))
    return out


def _lessons(st: dict[str, Any], cid: int | None, purposes: set[str] | None = None, max_n: int = 8) -> list[dict[str, Any]]:
    """Achados com probabilidade ≥ 75% de serem reais (efeito com sinal certo), do mais confiável ao menos."""
    out = []
    dim_purpose = {"title_style": {"title", "ideas"}, "hook_style": {"hook", "script"}, "structure": {"script", "ideas"},
                   "duration": {"script"}, "graphics": {"script"}, "cta_style": {"script"}, "thumb_variant": {"thumbnail"},
                   "caption": {"script"}, "intro": {"script", "hook"}, "outro": {"script"}, "grade": {"thumbnail", "script"}}
    for dim, d in (st.get("bandit") or {}).items():
        if purposes and not (dim_purpose.get(dim, set()) & purposes):
            continue
        for o in _bandit_rows(st, dim, cid):
            if o["n"] < 2:
                continue
            q = o["p_pos"]
            if max(q, 1 - q) >= 0.75 and abs(o["effect"]) >= 0.08:
                good = o["effect"] > 0
                out.append({"kind": "variety", "dim": dim, "conf": max(q, 1 - q),
                            "text": f"{d['label']}: “{o['label']}” {'rende MAIS' if good else 'rende MENOS'} "
                                    f"({_pct(o['effect'])} views vs o normal; {o['n']} vídeos; confiança {_conf_label(q)})"})
    feat_purpose = {"t": {"title", "ideas"}, "h": {"hook", "script"}, "d": {"script"}, "l": {"script", "ideas"},
                    "s": {"ideas"}, "w": {"ideas"}, "c": {"ideas"}}
    m = st.get("model") or {}
    if m.get("ok") and (m.get("loo") or {}).get("r2", 0) > -0.1:  # coeficientes só se o modelo não for pior que a média
        for c in m.get("coefs", []):
            k = c["key"]
            if k == "topic":
                continue
            if purposes and not (feat_purpose.get(k[0], set()) & purposes):
                continue
            q = c["p_pos"]
            if max(q, 1 - q) >= 0.8 and abs(c["effect"]) >= 0.08 and (c["share"] is None or 0.1 <= c["share"] <= 0.9):
                out.append({"kind": "feature", "dim": k, "conf": max(q, 1 - q),
                            "text": f"{c['label']}: {_pct(c['effect'])} views (todos os canais; confiança {_conf_label(q)})"})
    out.sort(key=lambda x: -x["conf"])
    return out[:max_n]


def _retention_lines(st: dict[str, Any], cid: int) -> list[str]:
    rs = [r for r in st["records"] if r["channel_id"] == cid and (r.get("retention") or {}).get("hook")]
    if len(rs) < 3:
        return []
    rs.sort(key=lambda r: -r["retention"]["hook"])
    lines = [f"- Segura melhor aos 3s ({r['retention']['hook']:.0f}%): gancho “{(r['hook'] or '')[:110]}”" for r in rs[:2] if r["hook"]]
    lines += [f"- Perde mais aos 3s ({r['retention']['hook']:.0f}%): gancho “{(r['hook'] or '')[:110]}”" for r in rs[-2:] if r["hook"]]
    return lines


def prompt_context(channel_id: int, purpose: str) -> str:
    """Bloco em português com orientação baseada nos dados (exemplos, o que vence, com confiança) para o prompt da IA.
    purpose: ideas | script | title | hook | thumbnail. Vazio se ainda não há dados."""
    try:
        stamp = _get_state().get("computed_at", "")  # recalcula se o estado envelheceu (e isso limpa o cache)
    except Exception:  # noqa: BLE001
        return ""
    key = (int(channel_id), purpose, stamp)
    if key in _ctx_cache:
        return _ctx_cache[key]
    try:
        txt = _prompt_context(channel_id, purpose)
    except Exception:  # noqa: BLE001
        log.exception("prompt_context")
        txt = ""
    _ctx_cache[key] = txt
    return txt


def _prompt_context(channel_id: int, purpose: str) -> str:
    st = _get_state()
    recs = [r for r in st["records"] if r["channel_id"] == channel_id and r.get("rel") is not None
            and (r.get("age_h") or 0) >= 12]  # exemplos só com pelo menos 12 h no ar
    if len(recs) < 3:
        return ""
    recs.sort(key=lambda r: -r["rel"])
    typical = _rec_views_typical(st, channel_id)
    m = st.get("model") or {}
    parts = [f"APRENDIZADO MEDIDO NOS DADOS ({len(recs)} vídeos do canal, comparados na MESMA IDADE; "
             f"um vídeo típico do canal tem ~{typical:.0f} views com 48 h). Use como evidência, não como regra cega:"]

    def ex(r: dict[str, Any]) -> str:
        dias = f"{r['age_h'] / 24:.1f}".replace(".", ",")
        bits = [f"“{r['title']}” → {_x(math.exp(r['rel']))} o normal ({r['views']} views em {dias} dias)"]
        if purpose in ("hook", "script") and r.get("hook"):
            bits.append(f"gancho: “{r['hook'][:100]}”")
        if purpose == "thumbnail" and r.get("thumbnail_text"):
            bits.append(f"texto da miniatura: “{r['thumbnail_text']}”")
        ret = r.get("retention") or {}
        if purpose in ("hook", "script") and ret.get("hook"):
            bits.append(f"retém {ret['hook']:.0f}% aos 3s, {ret.get('end', 0):.0f}% no fim")
        return "- " + " | ".join(bits)

    k = 3 if len(recs) >= 6 else 2
    parts.append("MELHORES (imite o que eles têm em comum, sem copiar):\n" + "\n".join(ex(r) for r in recs[:k]))
    parts.append("PIORES (evite o que eles têm em comum):\n" + "\n".join(ex(r) for r in recs[-k:]))
    purposes = {purpose}
    les = _lessons(st, channel_id, purposes)
    if les:
        parts.append("O QUE OS EXPERIMENTOS MOSTRAM (efeito estimado com encolhimento bayesiano; “fraca” = ainda pode ser acaso):\n"
                     + "\n".join(f"- {x['text']}" for x in les))
    if purpose == "ideas":
        tp = (st.get("topics") or {}).get(channel_id) or {}
        if tp.get("win"):
            parts.append("TERMOS/TEMAS QUE APARECEM NOS VÍDEOS QUE FORAM BEM: " + ", ".join(f"{w} ({n} vídeos)" for w, _, n in tp["win"]))
        if tp.get("lose"):
            parts.append("TERMOS/TEMAS DOS QUE FORAM MAL: " + ", ".join(f"{w} ({n} vídeos)" for w, _, n in tp["lose"]))
        rho = st.get("idea_score_spearman")
        if rho is not None and rho < 0.2:
            parts.append(f"Aviso: a nota 0-100 das pautas quase não previu o resultado real (correlação {rho:+.2f} em "
                         f"{st.get('idea_score_n')} vídeos). Seja mais crítico: priorize curiosidade concreta e específica.")
    tc = next((c for c in (m.get("coefs") or []) if c["key"] == "topic"), None) if m.get("ok") else None
    if tc and purpose in ("ideas", "title") and max(tc["p_pos"], 1 - tc["p_pos"]) >= 0.8:
        if tc["effect"] < 0:
            parts.append("PADRÃO MEDIDO (todos os canais, confiança " + _conf_label(tc["p_pos"]) + "): pautas muito parecidas "
                         "com um vídeo que já foi bem tendem a render MENOS que ele (o público/algoritmo satura). Prefira "
                         "assuntos novos ou um ângulo realmente diferente, não a mesma história de novo.")
        else:
            parts.append("PADRÃO MEDIDO (todos os canais, confiança " + _conf_label(tc["p_pos"]) + "): temas próximos dos "
                         "vídeos que foram bem tendem a render bem de novo — explore ângulos vizinhos dos vencedores.")
    if purpose in ("hook", "script"):
        rl = _retention_lines(st, channel_id)
        if rl:
            parts.append("GANCHOS × RETENÇÃO AOS 3 SEGUNDOS (curva real do YouTube):\n" + "\n".join(rl))
    if m.get("ok"):
        r2 = (m.get("loo") or {}).get("r2", 0)
        if r2 < 0.03:
            parts.append("Honestidade: com tão poucos vídeos, nenhum padrão de título/gancho previu as views fora da amostra "
                         "ainda. Varie com ousadia e mantenha a variedade — é testando que o canal descobre o que funciona.")
    return "\n\n".join(parts)


# ================================================================ relatório (painel)

def report(channel_id: int | None = None) -> dict[str, Any]:
    st = _get_state()
    m = st.get("model") or {}
    recs = [r for r in st["records"] if channel_id is None or r["channel_id"] == channel_id]
    videos = []
    for r in sorted(recs, key=lambda r: r["published_at"], reverse=True):
        videos.append({k: r.get(k) for k in ("pub_id", "channel_id", "title", "url", "thumbnail", "published_at", "age_h",
                                             "format", "duration", "views", "views_at", "like_rate", "comment_rate",
                                             "retention", "analytics", "imported", "hook")}
                      | {"x_normal": None if r.get("rel") is None else round(math.exp(r["rel"]), 2),
                         "x_pred": None if r.get("loo_pred") is None else round(math.exp(r["loo_pred"]), 2),
                         "trained": r.get("loo_pred") is not None,
                         "variety": {k: (r.get("variety") or {}).get(k) for k in ("structure", "hook_style", "title_style")}})
    chans = []
    for cid, name in sorted(st.get("channels", {}).items()):
        if channel_id is not None and cid != channel_id:
            continue
        rs = [r for r in st["records"] if r["channel_id"] == cid]
        tr = [r for r in rs if r.get("loo_pred") is not None]
        chans.append({"id": cid, "name": name, "videos": len(rs), "trained": len(tr),
                      "typical_48h": round(_rec_views_typical(st, cid)), "typical_7d": round(_rec_views_typical(st, cid, 168)),
                      "effect_x": round(math.exp(st["channel_effect"].get(cid, st.get("grand", 0)) - st.get("grand", 0)), 2),
                      "best": max((r for r in rs if r.get("rel") is not None), key=lambda r: r["rel"], default=None) and
                      {k: v for k, v in max((r for r in rs if r.get("rel") is not None), key=lambda r: r["rel"]).items()
                       if k in ("title", "url", "views")}})
    pred_vs_actual = [{"title": r["title"], "channel_id": r["channel_id"], "pred": round(r["loo_pred"], 3),
                       "actual": round(r["rel"], 3)} for r in recs if r.get("loo_pred") is not None]
    curve = st.get("curve") or {}
    return {
        "computed_at": st.get("computed_at"), "seconds": st.get("seconds"),
        "channel_id": channel_id, "channels": chans,
        "model": {k: m.get(k) for k in ("ok", "n", "alpha", "loo", "verdict")} | {
            "coefs": sorted(m.get("coefs") or [], key=lambda c: -abs(c["effect"]))},
        "idea_score": {"spearman": st.get("idea_score_spearman"), "n": st.get("idea_score_n")},
        "lessons": [x["text"] for x in _lessons(st, channel_id, None, 12)],
        "dimensions": variety_detail(channel_id),
        "weights": recommend_variety(channel_id) if channel_id else {},
        "videos": videos, "pred_vs_actual": pred_vs_actual,
        # curva típica: do canal (nível do canal) ou geral (todos os canais)
        "curve": [{"age_h": c, "views": round(math.expm1(g + (st["channel_effect"].get(channel_id, st.get("grand", 0.0))
                                                               if channel_id else 0.0)))}
                  for c, g in zip(curve.get("centers", []), curve.get("g", []))],
        "curve_support": curve.get("support"),
        "topics": (st.get("topics") or {}).get(channel_id) if channel_id else None,
        "method": [
            "Views comparadas na mesma idade: curva típica de crescimento por chain-ladder (cada vídeo comparado com ele mesmo).",
            "Efeito de cada canal com encolhimento bayesiano (canais com poucos vídeos puxam para a média geral).",
            "Variedade: bandit bayesiano (Thompson sampling) com efeito global da opção → efeito no canal.",
            "Previsão: ridge bayesiano com validação leave-one-out aninhada — a acurácia mostrada é fora da amostra.",
        ],
    }
