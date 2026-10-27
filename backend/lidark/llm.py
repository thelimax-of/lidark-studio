"""Roteador de LLMs com fallback: Gemini (várias chaves) → GLM → Ollama local.

Quando um provedor estoura a cota (429) ou falha, a chave entra em "geladeira"
por alguns minutos e o próximo da fila é usado automaticamente.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

from . import config

log = logging.getLogger("lidark.llm")

_cooldowns: dict[str, float] = {}
_lock = threading.Lock()
usage_stats: dict[str, dict[str, int]] = {}


class LLMError(RuntimeError):
    pass


class QuotaError(LLMError):
    pass


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str


def _cool(key: str, seconds: float) -> None:
    with _lock:
        _cooldowns[key] = time.time() + seconds


def _is_cool(key: str) -> bool:
    return _cooldowns.get(key, 0) > time.time()


def _count(provider: str, ok: bool) -> None:
    with _lock:
        s = usage_stats.setdefault(provider, {"ok": 0, "fail": 0})
        s["ok" if ok else "fail"] += 1


# ---------------------------------------------------------------- provedores

def _gemini(prompt: str, system: str | None, json_mode: bool, temperature: float,
            images: list[bytes] | None, model: str | None) -> LLMResult:
    """Tenta o modelo principal e, se estiver sobrecarregado/indisponível, os modelos reserva."""
    s = config.load_settings()
    models = [model or s["gemini_model"]] + [m for m in s.get("gemini_fallback_models", []) if m != model]
    last: Exception | None = None
    for m in models:
        try:
            return _gemini_once(prompt, system, json_mode, temperature, images, m)
        except QuotaError as e:
            last = e
        except LLMError as e:
            last = e
            if "chave" in str(e):
                raise
    raise last or LLMError("Gemini indisponível")


def _gemini_once(prompt: str, system: str | None, json_mode: bool, temperature: float,
                 images: list[bytes] | None, model: str | None) -> LLMResult:
    s = config.load_settings()
    keys = s["gemini_api_keys"]
    if not keys:
        raise LLMError("Nenhuma chave Gemini configurada")
    model = model or s["gemini_model"]
    parts: list[dict[str, Any]] = [{"text": prompt}]
    for img in images or []:
        parts.append({"inline_data": {"mime_type": _sniff_mime(img), "data": base64.b64encode(img).decode()}})
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    last_err: Exception | None = None
    for key in keys:
        ck = f"gemini:{key[-6:]}:{model}"
        if _is_cool(ck):
            continue
        try:
            r = httpx.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": key}, json=body, timeout=120,
            )
            if r.status_code == 429:
                # o Google diz quanto esperar (cota por minuto: segundos; cota diária: horas) — respeita isso
                wait, daily = _retry_info(r)
                _cool(ck, wait)
                last_err = QuotaError(f"Gemini 429 ({'cota diária' if daily else 'limite por minuto'}, volta em {int(wait // 60)} min)")
                continue
            if r.status_code >= 500 or r.status_code == 404:
                _cool(ck, 120 if r.status_code == 503 else 30)
                last_err = LLMError(f"Gemini {model} {r.status_code}")
                continue
            r.raise_for_status()
            data = r.json()
            cands = data.get("candidates") or []
            if not cands:
                raise LLMError(f"Gemini sem resposta: {data.get('promptFeedback')}")
            text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []))
            return LLMResult(text, "gemini", model)
        except httpx.HTTPError as e:
            last_err = e
    raise last_err or QuotaError("Todas as chaves Gemini em espera")


def _retry_info(r: httpx.Response) -> tuple[float, bool]:
    """(segundos para esperar, é cota diária?) a partir da resposta 429 do Gemini."""
    try:
        details = r.json().get("error", {}).get("details", [])
    except ValueError:
        return 60.0, False
    daily = any("PerDay" in (v.get("quotaId") or "") for d in details for v in d.get("violations", []))
    delay = next((d.get("retryDelay") for d in details if d.get("retryDelay")), "")
    try:
        secs = float(str(delay).rstrip("s"))
    except ValueError:
        secs = 0.0
    if not secs:
        secs = 3600.0 if daily else 60.0
    return min(max(secs + 5, 20.0), 6 * 3600.0), daily


_glm_slots = threading.Semaphore(2)  # o plano grátis do GLM aceita poucas chamadas simultâneas


def _glm(prompt: str, system: str | None, json_mode: bool, temperature: float,
         images: list[bytes] | None, model: str | None) -> LLMResult:
    s = config.load_settings()
    if not s["glm_api_key"]:
        raise LLMError("GLM sem chave")
    if images:
        raise LLMError("GLM configurado sem visão")
    model = model or s["glm_model"]
    ck = f"glm:{model}"
    if _is_cool(ck):
        raise QuotaError("GLM em espera")
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body: dict[str, Any] = {"model": model, "messages": msgs, "temperature": temperature}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    if model.startswith("glm-4.5") or model.startswith("glm-4.6"):
        body["thinking"] = {"type": "disabled"}  # sem "raciocínio" visível: 3x mais rápido e 4x menos tokens
    # 429 do GLM costuma ser pico momentâneo: tenta de novo com espera crescente antes de desistir
    for attempt, wait in enumerate((0, 4, 10, 20)):
        if wait:
            time.sleep(wait)
        with _glm_slots:
            r = httpx.post(f"{s['glm_base_url'].rstrip('/')}/chat/completions",
                           headers={"Authorization": f"Bearer {s['glm_api_key']}"}, json=body, timeout=240)
        if r.status_code != 429:
            break
    if r.status_code == 429:
        code = ""
        try:
            code = str(r.json().get("error", {}).get("code", ""))
        except ValueError:
            pass
        # 1113 = sem saldo/cota do plano (demora a voltar); demais = limite de frequência
        _cool(ck, 60 * 30 if code in ("1113", "1308") else 45)
        raise QuotaError(f"GLM 429 (código {code or '?'})")
    r.raise_for_status()
    return LLMResult(r.json()["choices"][0]["message"]["content"], "glm", model)


def _ollama(prompt: str, system: str | None, json_mode: bool, temperature: float,
            images: list[bytes] | None, model: str | None) -> LLMResult:
    s = config.load_settings()
    model = model or s["ollama_model"]
    msg: dict[str, Any] = {"role": "user", "content": prompt}
    if images:
        msg["images"] = [base64.b64encode(i).decode() for i in images]
    msgs = ([{"role": "system", "content": system}] if system else []) + [msg]
    body: dict[str, Any] = {"model": model, "messages": msgs, "stream": False,
                            "options": {"temperature": temperature, "num_ctx": 8192}}
    if json_mode:
        body["format"] = "json"
    try:
        r = httpx.post(f"{s['ollama_url']}/api/chat", json=body, timeout=600)
    except httpx.ConnectError as e:
        raise LLMError("Ollama não está rodando") from e
    r.raise_for_status()
    text = r.json()["message"]["content"]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    return LLMResult(text, "ollama", model)


PROVIDERS = {"gemini": _gemini, "glm": _glm, "ollama": _ollama}


# ---------------------------------------------------------------- API pública

def complete(prompt: str, *, system: str | None = None, json_mode: bool = False,
             temperature: float = 0.7, images: list[bytes] | None = None,
             prefer: str | None = None) -> LLMResult:
    order = list(config.get("llm_order"))
    if prefer and prefer in order:
        order.remove(prefer)
        order.insert(0, prefer)
    errors = []
    for name in order:
        fn = PROVIDERS.get(name)
        if not fn:
            continue
        try:
            res = fn(prompt, system, json_mode, temperature, images, None)
            _count(name, True)
            return res
        except Exception as e:  # noqa: BLE001 — qualquer falha passa para o próximo
            _count(name, False)
            log.warning("LLM %s falhou: %s", name, e)
            errors.append(f"{name}: {e}")
    raise LLMError("Nenhum LLM disponível → " + " | ".join(errors))


def complete_json(prompt: str, *, system: str | None = None, temperature: float = 0.6,
                  images: list[bytes] | None = None, retries: int = 2) -> Any:
    last: Exception | None = None
    for attempt in range(retries + 1):
        res = complete(prompt, system=system, json_mode=True, temperature=temperature, images=images)
        try:
            return parse_json(res.text)
        except ValueError as e:
            last = e
            prompt = prompt + "\n\nIMPORTANTE: responda APENAS com JSON válido, sem comentários."
    raise LLMError(f"JSON inválido do LLM: {last}")


def parse_json(text: str) -> Any:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError as e:
            raise ValueError(str(e)) from e
    raise ValueError("nenhum JSON encontrado")


def has_vision() -> bool:
    s = config.load_settings()
    return bool(s["gemini_api_keys"] or s.get("glm_api_key"))


# preço por milhão de tokens (entrada, saída) dos modelos pagos do GLM — só para acompanhar o gasto do crédito
GLM_PRICES = {"glm-4.6v-flashx": (0.04, 0.40), "glm-4.6v": (0.30, 0.90)}
glm_spend = {"usd": 0.0, "calls": 0}


def vision_json(prompt: str, images: list[bytes]) -> Any:
    """Visão: Gemini primeiro; sem cota → GLM-4.6V-Flash (grátis) → GLM-4.6V-FlashX (crédito, centavos)."""
    s = config.load_settings()
    errors = []
    if s["gemini_api_keys"]:
        try:
            res = _gemini(prompt, None, True, 0.2, images, s["gemini_vision_model"])
            _count("gemini", True)
            return parse_json(res.text)
        except Exception as e:  # noqa: BLE001
            _count("gemini", False)
            errors.append(f"gemini: {e}")
    for model in s.get("glm_vision_models") or []:
        try:
            res = _glm_vision(prompt, images, model)
            _count("glm", True)
            return parse_json(res.text)
        except Exception as e:  # noqa: BLE001
            _count("glm", False)
            errors.append(f"{model}: {e}")
    raise LLMError("Nenhuma IA de visão disponível → " + " | ".join(errors))


def _glm_vision(prompt: str, images: list[bytes], model: str) -> LLMResult:
    s = config.load_settings()
    if not s.get("glm_api_key"):
        raise LLMError("GLM sem chave")
    ck = f"glm:{model}"
    if _is_cool(ck):
        raise QuotaError(f"{model} em espera")
    content: list[dict[str, Any]] = [{"type": "image_url", "image_url": {
        "url": f"data:{_sniff_mime(b)};base64,{base64.b64encode(b).decode()}"}} for b in images]
    content.append({"type": "text", "text": prompt + "\nResponda SOMENTE com o JSON pedido."})
    body = {"model": model, "messages": [{"role": "user", "content": content}], "temperature": 0.2,
            "thinking": {"type": "disabled"}}
    with _glm_slots:
        r = httpx.post(f"{s['glm_base_url'].rstrip('/')}/chat/completions",
                       headers={"Authorization": f"Bearer {s['glm_api_key']}"}, json=body, timeout=180)
    if r.status_code == 429:
        _cool(ck, 60)  # "sobrecarregado" (grátis) costuma passar logo
        raise QuotaError(f"{model} 429")
    r.raise_for_status()
    j = r.json()
    price = GLM_PRICES.get(model)
    if price:
        u = j.get("usage") or {}
        with _lock:
            glm_spend["usd"] += (u.get("prompt_tokens", 0) * price[0] + u.get("completion_tokens", 0) * price[1]) / 1e6
            glm_spend["calls"] += 1
    return LLMResult(j["choices"][0]["message"]["content"], "glm", model)


def _sniff_mime(b: bytes) -> str:
    if b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"
