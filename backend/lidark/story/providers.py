"""Geradores de imagem GRÁTIS para o Modo História + orçamento diário por fonte.

Interface única (o planejador só usa isto):
    generate(prompt, w, h, seed, kind) -> Path | None     (kind: sheet | hero | location | scene | prop | insert)
    capacity() -> {provider: {...}}                         (quanto ainda dá para gerar hoje, quando zera)

Fontes (medidas em 30/10/2026):
- cf_lucid    Cloudflare Workers AI @cf/leonardo/lucid-origin: melhor visual, aceita largura/altura. ≈550 neurônios
              por 720x1280 com 12 passos → ~18 imagens/dia dos 10.000 grátis (zera 00:00 UTC = 21:00 Brasília).
- cf_schnell  Cloudflare @cf/black-forest-labs/flux-1-schnell: 1024x1024 fixo, MUITO mais barato (estimativa pela
              tabela pública: ~58 neurônios com 4 passos → ~170/dia; o custo real se calibra sozinho quando a cota
              acaba — ver _calibrate). Às vezes acusa NSFW à toa ("bed", "grandmother") → reescreve e tenta de novo.
- local       worker de GPU local (outro processo/venv: SD1.5+LCM ou SDXL-Lightning no RTX 3050) — volume.
              Interface HTTP configurável (story config "local_url"): POST /generate, GET /capacity. Ver LocalProvider.
- hf_space    Hugging Face Space black-forest-labs/FLUX.1-schnell (gradio_client). Anônimo: ~3 imagens e bloqueia
              (cota ZeroGPU por IP); com token (hf_token) rende mais.
- pollinations  só com token (pollinations_token): anônimo devolve 402 / modelo ruim com marca d'água. Último recurso.

Roteamento: folhas de personagem e cenas-herói → cf_lucid primeiro (consistência); volume (cenários, cenas,
objetos, inserts) → local, cf_schnell, hf, e lucid só com sobra acima da reserva do dia.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from .. import config
from ..config import DATA_DIR

log = logging.getLogger("lidark.story.providers")

STORY_DIR = DATA_DIR / "story"
GEN_DIR = STORY_DIR / "_gen"
LEDGER = STORY_DIR / "budget.json"
CONF = STORY_DIR / "config.json"
_lock = threading.RLock()

CF_DAILY = 10_000
CF_MARGIN = 150  # não encosta no teto (a conta da Cloudflare arredonda diferente)
DEFAULT_COSTS = {"cf_lucid": 550.0, "cf_schnell": 58.0}  # neurônios por imagem (lucid: 720x1280, 12 passos)
LUCID_RESERVE_IMAGES = 4  # do lucid, guarda espaço para N folhas/heróis por dia antes de gastar com volume

VOLUME_KINDS = {"location", "scene", "prop", "insert"}
HERO_KINDS = {"sheet", "hero"}

CONF_DEFAULTS: dict[str, Any] = {
    "local_url": "",            # ex.: http://127.0.0.1:8790 (worker de GPU local)
    "local_lock_client": True,  # o servidor segura a trava de GPU durante a chamada ao worker local
    "local_images_per_hour": 0,  # capacidade declarada (0 = pergunta ao worker em /capacity)
    "hf_token": "",
    "pollinations_token": "",
    "enabled": {"cf_lucid": True, "cf_schnell": True, "local": True, "hf_space": True, "pollinations": True},
    "cf_costs": {},             # sobrescreve DEFAULT_COSTS
    "new_images_short": [12, 16],  # alvo de imagens NOVAS por Short quando há capacidade
    "new_images_long_per_min": 6,
}
SECRET = {"hf_token", "pollinations_token"}


class NSFWFlag(RuntimeError):
    """O filtro do provedor recusou o prompt (falso positivo comum) — vale reescrever."""


class Exhausted(RuntimeError):
    """A fonte não tem mais cota hoje."""


# ================================================================ config e livro-caixa

def conf() -> dict[str, Any]:
    d = json.loads(json.dumps(CONF_DEFAULTS))
    if CONF.exists():
        try:
            d.update(json.loads(CONF.read_text(encoding="utf-8")))
        except ValueError:
            pass
    st = config.load_settings()  # fallback: chaves salvas no settings.json geral
    for k in ("hf_token", "pollinations_token"):
        if not d.get(k) and st.get(k):
            d[k] = st[k]
    return d


def save_conf(patch: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        cur = {}
        if CONF.exists():
            try:
                cur = json.loads(CONF.read_text(encoding="utf-8"))
            except ValueError:
                cur = {}
        for k, v in patch.items():
            if k not in CONF_DEFAULTS:
                continue
            if k in SECRET and isinstance(v, str) and ("•" in v or v.startswith("***")):
                continue  # painel devolveu o valor mascarado
            cur[k] = v
        STORY_DIR.mkdir(parents=True, exist_ok=True)
        CONF.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
    return public_conf()


def public_conf() -> dict[str, Any]:
    c = conf()
    for k in SECRET:
        if c.get(k):
            c[k] = "•••• " + c[k][-4:]
    return c


def _utc_day(at: datetime | None = None) -> str:
    return (at or datetime.now(timezone.utc)).strftime("%Y-%m-%d")


def cf_reset_at() -> datetime:
    n = datetime.now(timezone.utc)
    return (n + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _ledger() -> dict[str, Any]:
    if LEDGER.exists():
        try:
            return json.loads(LEDGER.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {}


def _save_ledger(d: dict[str, Any]) -> None:
    STORY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(LEDGER)


def _bucket(d: dict[str, Any], name: str, day: str) -> dict[str, Any]:
    b = d.setdefault(name, {})
    if b.get("day") != day:
        hist = d.setdefault("history", [])
        if b.get("day") and (b.get("images") or b.get("neurons")):
            hist.append({"source": name, **{k: b.get(k) for k in ("day", "images", "neurons", "failures")}})
            d["history"] = hist[-120:]
        b.clear()
        b.update(day=day, images=0, neurons=0.0, failures=0, exhausted=False, by_model={})
    return b


def _cost(model: str) -> float:
    c = {**DEFAULT_COSTS, **(conf().get("cf_costs") or {})}
    scale = float(_ledger().get("cf_scale") or 1.0)
    return float(c.get(model, 500)) * scale


def _calibrate(neurons_est: float) -> None:
    """A Cloudflare disse 'acabou' com X neurônios estimados: ajusta a escala dos custos (média móvel)."""
    if neurons_est < 1500:
        return
    d = _ledger()
    k = max(0.5, min(3.0, CF_DAILY / neurons_est))
    d["cf_scale"] = round(0.5 * float(d.get("cf_scale") or 1.0) * k + 0.5 * float(d.get("cf_scale") or 1.0), 3)
    _save_ledger(d)
    log.info("Cloudflare: custo recalibrado (escala %.2f)", d["cf_scale"])


def record(source: str, *, images: int = 0, neurons: float = 0.0, model: str = "", failed: bool = False,
           exhausted: bool = False, blocked_until: float | None = None, seconds: float = 0.0) -> None:
    with _lock:
        d = _ledger()
        day = _utc_day() if source.startswith("cf_") or source == "cloudflare" else datetime.now().strftime("%Y-%m-%d")
        b = _bucket(d, "cloudflare" if source.startswith("cf_") else source, day)
        b["images"] += images
        b["neurons"] = round(b.get("neurons", 0) + neurons, 1)
        b["seconds"] = round(b.get("seconds", 0) + seconds, 1)
        if model:
            bm = b.setdefault("by_model", {})
            bm[model] = bm.get(model, 0) + images
        if failed:
            b["failures"] = b.get("failures", 0) + 1
        if exhausted:
            b["exhausted"] = True
        if blocked_until:
            b["blocked_until"] = blocked_until
        _save_ledger(d)
    if exhausted and source.startswith("cf_"):
        _calibrate(b.get("neurons", 0))


def _cf_state() -> dict[str, Any]:
    with _lock:
        d = _ledger()
        return dict(_bucket(d, "cloudflare", _utc_day()))


def cf_remaining() -> float:
    b = _cf_state()
    if b.get("exhausted"):
        return 0.0
    return max(0.0, CF_DAILY - CF_MARGIN - float(b.get("neurons") or 0))


# ================================================================ provedores

def _png(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    im.load()
    return im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")


class Provider:
    name = ""
    kinds_ok: set[str] = HERO_KINDS | VOLUME_KINDS

    def enabled(self) -> bool:
        return bool((conf().get("enabled") or {}).get(self.name, True))

    def available(self) -> bool:
        return self.enabled()

    def capacity(self) -> dict[str, Any]:
        return {"available": self.available()}

    def run(self, prompt: str, w: int, h: int, seed: int, kind: str) -> Image.Image:
        raise NotImplementedError


class CloudflareProvider(Provider):
    def __init__(self, name: str, model: str, sized: bool, steps: int) -> None:
        self.name, self.model, self.sized, self.steps = name, model, sized, steps

    def _creds(self) -> tuple[str, str]:
        st = config.load_settings()
        return st.get("cloudflare_account_id") or "", st.get("cloudflare_api_token") or ""

    def available(self) -> bool:
        acc, tok = self._creds()
        return self.enabled() and bool(acc and tok) and cf_remaining() >= _cost(self.name)

    def capacity(self) -> dict[str, Any]:
        rem = cf_remaining()
        c = _cost(self.name)
        return {"available": self.available(), "configured": all(self._creds()), "cost_neurons": round(c),
                "images_left": int(rem // c) if c else 0, "images_per_day": int((CF_DAILY - CF_MARGIN) // c),
                "neurons_left": round(rem), "resets_at": cf_reset_at().isoformat(), "model": self.model}

    def run(self, prompt: str, w: int, h: int, seed: int, kind: str) -> Image.Image:
        acc, tok = self._creds()
        if not (acc and tok):
            raise Exhausted("Cloudflare sem credenciais")
        body: dict[str, Any] = {"prompt": prompt[:2000], "steps": self.steps, "seed": int(seed) % 2_147_483_647}
        if self.sized:
            body.update(width=int(w), height=int(h))
        url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{self.model}"
        r = httpx.post(url, json=body, headers={"Authorization": f"Bearer {tok}"}, timeout=180)
        ctype = r.headers.get("content-type", "")
        if r.status_code == 200 and ctype.startswith("image/"):
            img = _png(r.content)
        else:
            txt = r.text[:600]
            low = txt.lower()
            if r.status_code == 429 or "4006" in txt or "daily free allocation" in low or ("neurons" in low and "used" in low):
                record(self.name, exhausted=True)
                raise Exhausted(f"Cloudflare: cota do dia acabou ({r.status_code})")
            if "nsfw" in low:
                record(self.name, failed=True)
                raise NSFWFlag("Cloudflare marcou o prompt como NSFW")
            if r.status_code != 200:
                record(self.name, failed=True)
                raise RuntimeError(f"Cloudflare {r.status_code}: {txt[:200]}")
            data = r.json()
            res = data.get("result") or {}
            b64 = res.get("image") if isinstance(res, dict) else None
            if not b64:
                record(self.name, failed=True)
                raise RuntimeError(f"Cloudflare sem imagem: {txt[:200]}")
            img = _png(base64.b64decode(b64))
        scale = (w * h) / (720 * 1280) if self.sized else 1.0
        record(self.name, images=1, neurons=_cost(self.name) * (scale if self.name == "cf_lucid" else 1.0), model=self.model)
        return img


class HFSpaceProvider(Provider):
    name = "hf_space"
    space = "black-forest-labs/FLUX.1-schnell"

    def available(self) -> bool:
        if not self.enabled():
            return False
        b = _ledger().get("hf_space") or {}
        return float(b.get("blocked_until") or 0) < time.time()

    def capacity(self) -> dict[str, Any]:
        b = _ledger().get("hf_space") or {}
        tok = bool(conf().get("hf_token"))
        return {"available": self.available(), "token": tok, "images_today": b.get("images", 0) if b.get("day") == datetime.now().strftime("%Y-%m-%d") else 0,
                "images_per_day": 25 if tok else 3, "blocked_until": b.get("blocked_until")}

    def run(self, prompt: str, w: int, h: int, seed: int, kind: str) -> Image.Image:
        try:
            from gradio_client import Client
        except ImportError as e:
            raise Exhausted("gradio_client não instalado") from e
        tok = conf().get("hf_token") or None
        w2, h2 = (int(w) // 16) * 16, (int(h) // 16) * 16
        try:
            c = Client(self.space, hf_token=tok, verbose=False) if tok else Client(self.space, verbose=False)
            res = c.predict(prompt=prompt[:1500], seed=int(seed) % 2_147_483_647, randomize_seed=False, width=w2, height=h2,
                            num_inference_steps=4, api_name="/infer")
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            if "quota" in msg.lower():
                m = re.search(r"(\d+):(\d\d):(\d\d)", msg)
                wait = (int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))) if m else 0
                record(self.name, failed=True, blocked_until=time.time() + max(wait, 3600 if not tok else 900))
                raise Exhausted("HF ZeroGPU sem cota") from e
            record(self.name, failed=True)
            raise
        path = res[0] if isinstance(res, (list, tuple)) else res
        img = Image.open(path)
        img.load()
        record(self.name, images=1)
        return img.convert("RGB")


class PollinationsProvider(Provider):
    name = "pollinations"

    def available(self) -> bool:
        return self.enabled() and bool(conf().get("pollinations_token"))

    def capacity(self) -> dict[str, Any]:
        return {"available": self.available(), "token": bool(conf().get("pollinations_token"))}

    def run(self, prompt: str, w: int, h: int, seed: int, kind: str) -> Image.Image:
        from urllib.parse import quote
        tok = conf().get("pollinations_token")
        if not tok:
            raise Exhausted("Pollinations sem token")
        r = httpx.get(f"https://image.pollinations.ai/prompt/{quote(prompt[:900])}",
                      params={"width": w, "height": h, "seed": seed, "model": "flux", "nologo": "true", "private": "true"},
                      headers={"Authorization": f"Bearer {tok}"}, timeout=180, follow_redirects=True)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
            record(self.name, images=1)
            return _png(r.content)
        record(self.name, failed=True)
        if r.status_code in (402, 429):
            raise Exhausted(f"Pollinations {r.status_code}")
        raise RuntimeError(f"Pollinations {r.status_code}")


class LocalProvider(Provider):
    """Worker de GPU local (outro processo). Contrato HTTP provisório — ajustar em _call quando o worker estiver pronto:
        POST {local_url}/generate  json {prompt, negative, width, height, seed, kind, steps?} → image/png (bytes)
             (ou json {"image": base64} / {"path": "C:/..."})
        GET  {local_url}/capacity  → json {"ok": true, "images_per_hour": 120, "queue": 0}
    A trava de GPU (gpu.py) é segurada aqui durante a chamada (conf local_lock_client=True); se o worker passar a
    travar sozinho o mesmo arquivo, desligue local_lock_client para não haver espera dupla."""
    name = "local"

    def _url(self) -> str:
        return (conf().get("local_url") or "").rstrip("/")

    def _probe(self) -> dict[str, Any] | None:
        u = self._url()
        if not u:
            return None
        try:
            r = httpx.get(u + "/capacity", timeout=3)
            return r.json() if r.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None

    def available(self) -> bool:
        return self.enabled() and bool(self._url()) and bool(self._probe())

    def capacity(self) -> dict[str, Any]:
        p = self._probe() or {}
        b = _ledger().get("local") or {}
        today = b.get("day") == datetime.now().strftime("%Y-%m-%d")
        iph = float(conf().get("local_images_per_hour") or p.get("images_per_hour") or 0)
        return {"available": bool(p) and self.enabled(), "configured": bool(self._url()), "images_per_hour": iph,
                "images_today": b.get("images", 0) if today else 0, "seconds_today": b.get("seconds", 0) if today else 0,
                "queue": p.get("queue"), "images_per_day": int(iph * 20) if iph else None}

    def run(self, prompt: str, w: int, h: int, seed: int, kind: str) -> Image.Image:
        u = self._url()
        if not u:
            raise Exhausted("worker local não configurado")
        body = {"prompt": prompt, "negative": NEGATIVE, "width": int(w), "height": int(h), "seed": int(seed), "kind": kind}
        t0 = time.time()

        def call() -> httpx.Response:
            return httpx.post(u + "/generate", json=body, timeout=600)

        if conf().get("local_lock_client", True):
            from .gpu import gpu_lock
            with gpu_lock("image-local", timeout=1200):
                r = call()
        else:
            r = call()
        if r.status_code != 200:
            record(self.name, failed=True)
            raise RuntimeError(f"worker local {r.status_code}: {r.text[:200]}")
        if r.headers.get("content-type", "").startswith("image/"):
            img = _png(r.content)
        else:
            data = r.json()
            if data.get("image"):
                img = _png(base64.b64decode(data["image"]))
            elif data.get("path"):
                img = Image.open(data["path"])
                img.load()
            else:
                raise RuntimeError("worker local sem imagem")
        record(self.name, images=1, seconds=time.time() - t0)
        return img


NEGATIVE = "text, letters, words, signature, watermark, logo, caption, frame border, photo, photorealistic, extra limbs, deformed"

PROVIDERS: dict[str, Provider] = {
    "cf_lucid": CloudflareProvider("cf_lucid", "@cf/leonardo/lucid-origin", sized=True, steps=12),
    "cf_schnell": CloudflareProvider("cf_schnell", "@cf/black-forest-labs/flux-1-schnell", sized=False, steps=4),
    "local": LocalProvider(),
    "hf_space": HFSpaceProvider(),
    "pollinations": PollinationsProvider(),
}


def route(kind: str) -> list[str]:
    """Ordem de tentativa por tipo de imagem."""
    if kind in HERO_KINDS:
        return ["cf_lucid", "local", "hf_space", "cf_schnell", "pollinations"]
    order = ["local", "cf_schnell", "hf_space"]
    # lucid para volume só com sobra acima da reserva de folhas/heróis do dia
    if cf_remaining() - LUCID_RESERVE_IMAGES * _cost("cf_lucid") >= _cost("cf_lucid"):
        order.append("cf_lucid")
    return order + ["pollinations"]


def capacity() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for n, p in PROVIDERS.items():
        try:
            out[n] = {"enabled": p.enabled(), **p.capacity()}
        except Exception as e:  # noqa: BLE001
            out[n] = {"available": False, "error": str(e)[:160]}
    cf = _cf_state()
    out["_cloudflare_day"] = {"neurons_used": round(float(cf.get("neurons") or 0)), "limit": CF_DAILY, "images": cf.get("images", 0),
                              "by_model": cf.get("by_model", {}), "exhausted": bool(cf.get("exhausted")),
                              "resets_at": cf_reset_at().isoformat(), "scale": _ledger().get("cf_scale", 1.0)}
    out["_today_new_images"] = images_left_today()
    return out


def images_left_today(kind: str = "scene") -> int:
    """Estimativa de quantas imagens de volume ainda saem hoje somando as fontes disponíveis."""
    n = 0
    rem = cf_remaining()
    if PROVIDERS["cf_schnell"].available():
        n += int(max(0.0, rem - LUCID_RESERVE_IMAGES * _cost("cf_lucid")) // _cost("cf_schnell"))
    loc = PROVIDERS["local"]
    if loc.enabled() and conf().get("local_url"):
        c = loc.capacity()
        if c.get("available"):
            n += int((c.get("images_per_hour") or 0) * 4)  # o que cabe nas próximas ~4 h de fila
    hf = PROVIDERS["hf_space"]
    if hf.available():
        n += 2 if not conf().get("hf_token") else 10
    return n


# ================================================================ API principal

def _rephrase(prompt: str) -> str:
    """Troca palavras que costumam disparar falso NSFW por sinônimos neutros."""
    subs = {r"\bbed(room)?\b": "simple wooden cot", r"\bgrandmother\b": "elderly neighbor lady", r"\bgrandma\b": "elderly lady",
            r"\bnaked\b": "plain", r"\bbare\b": "plain", r"\bblood(y)?\b": "red paint", r"\bkill(ed|ing)?\b": "defeat",
            r"\bshirtless\b": "in a white shirt", r"\bbath\b": "wash basin", r"\bkiss\b": "hug", r"\bbody\b": "figure",
            r"\bchild(ren)?\b": "young person", r"\bgirl\b": "young woman", r"\bboy\b": "young man"}
    out = prompt
    for k, v in subs.items():
        out = re.sub(k, v, out, flags=re.I)
    return out + ", family friendly, wholesome illustration"


def generate(prompt: str, w: int, h: int, seed: int, kind: str, *, only: list[str] | None = None,
             log_fn=None) -> Path | None:
    """Gera UMA imagem na melhor fonte disponível para o tipo. Nunca levanta exceção: None = sem cota/sem fonte.
    O arquivo sai em data/story/_gen/<hash>.png, com metadados em <hash>.json (fonte, modelo, prompt, semente)."""
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(f"{prompt}|{w}x{h}|{seed}|{kind}".encode()).hexdigest()[:20]
    out = GEN_DIR / f"{key}.png"
    if out.exists():
        return out
    order = [p for p in route(kind) if (only is None or p in only)]
    for name in order:
        p = PROVIDERS[name]
        try:
            if not p.available():
                continue
        except Exception:  # noqa: BLE001
            continue
        pr = prompt
        for attempt in range(3):
            try:
                t0 = time.time()
                img = p.run(pr, w, h, seed + attempt * 7919, kind)
                img.save(out)
                out.with_suffix(".json").write_text(json.dumps({
                    "provider": name, "model": getattr(p, "model", name), "prompt": pr, "seed": seed + attempt * 7919,
                    "kind": kind, "size": list(img.size), "asked": [w, h], "secs": round(time.time() - t0, 1),
                    "at": datetime.now(timezone.utc).isoformat()}, ensure_ascii=False), encoding="utf-8")
                if log_fn:
                    log_fn(f"imagem nova ({name}, {img.size[0]}x{img.size[1]}, {time.time() - t0:.0f}s)")
                return out
            except NSFWFlag:
                pr = _rephrase(pr)
                continue
            except Exhausted as e:
                if log_fn:
                    log_fn(f"{name}: {e}")
                break
            except Exception as e:  # noqa: BLE001
                log.warning("%s falhou: %s", name, e)
                if log_fn:
                    log_fn(f"{name} falhou: {str(e)[:120]}")
                break
    return None


def meta(path: Path) -> dict[str, Any]:
    j = Path(path).with_suffix(".json")
    try:
        return json.loads(j.read_text(encoding="utf-8")) if j.exists() else {}
    except ValueError:
        return {}
