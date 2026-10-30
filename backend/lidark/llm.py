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
                headers={"x-goog-api-key": key}, json=body, timeout=_timeout(120),
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
            # modelos com "raciocínio" mandam partes thought=true: não fazem parte da resposta
            text = "".join(p.get("text", "") for p in cands[0].get("content", {}).get("parts", []) if not p.get("thought"))
            if not text.strip():
                raise LLMError(f"Gemini {model} sem texto (finishReason={cands[0].get('finishReason')})")
            if cands[0].get("finishReason") == "MAX_TOKENS":
                log.warning("Gemini %s: resposta cortada pelo limite de tokens (o JSON será consertado)", model)
            return LLMResult(text, "gemini", model)
        except httpx.TimeoutException as e:
            _cool(ck, 30)  # chave/modelo lento agora: a próxima chave (ou o próximo provedor) tenta
            last_err = LLMError(f"Gemini {model} demorou demais ({type(e).__name__})")
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
    body: dict[str, Any] = {"model": model, "messages": msgs, "temperature": temperature,
                            "max_tokens": 16000}  # roteiros longos em JSON: sem isso a resposta vem cortada
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
                           headers={"Authorization": f"Bearer {s['glm_api_key']}"}, json=body, timeout=_timeout(240))
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
        r = httpx.post(f"{s['ollama_url']}/api/chat", json=body, timeout=_timeout(600))
    except httpx.ConnectError as e:
        raise LLMError("Ollama não está rodando") from e
    r.raise_for_status()
    text = r.json()["message"]["content"]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    return LLMResult(text, "ollama", model)


PROVIDERS = {"gemini": _gemini, "glm": _glm, "ollama": _ollama}


# ---------------------------------------------------------------- API pública

# Cache em memória para prompts idênticos (ex.: tarefa refeita depois de falhar adiante, dois cliques seguidos):
# economiza a cota grátis. Só guarda respostas que viraram JSON válido, e por pouco tempo.
_CACHE_TTL = 15 * 60
_CACHE_MAX = 96
_cache: dict[str, tuple[float, LLMResult]] = {}
_tl = threading.local()  # tempo limite da chamada atual (lido pelos provedores)


def _timeout(default: float) -> float:
    t = getattr(_tl, "timeout", None)
    return float(t) if t else default


def _cache_key(prompt: str, system: str | None, json_mode: bool, temperature: float,
               images: list[bytes] | None, prefer: str | None) -> str:
    import hashlib
    h = hashlib.sha1()
    for part in (prompt, system or "", str(json_mode), f"{temperature:.2f}", prefer or ""):
        h.update(part.encode("utf-8", "ignore"))
        h.update(b"\x00")
    for img in images or []:
        h.update(hashlib.sha1(img).digest())
    return h.hexdigest()


def _cache_get(key: str) -> LLMResult | None:
    with _lock:
        hit = _cache.get(key)
        if hit and time.time() - hit[0] < _CACHE_TTL:
            return hit[1]
        _cache.pop(key, None)
    return None


def _cache_put(key: str, res: LLMResult) -> None:
    with _lock:
        if len(_cache) >= _CACHE_MAX:
            for k, _ in sorted(_cache.items(), key=lambda kv: kv[1][0])[:_CACHE_MAX // 4]:
                _cache.pop(k, None)
        _cache[key] = (time.time(), res)


def _cache_drop(key: str) -> None:
    with _lock:
        _cache.pop(key, None)


def complete(prompt: str, *, system: str | None = None, json_mode: bool = False,
             temperature: float = 0.7, images: list[bytes] | None = None,
             prefer: str | None = None, exclude: set[str] | list[str] | None = None,
             timeout: float | None = None, cache: bool = False) -> LLMResult:
    """Primeiro provedor disponível da fila (Gemini → GLM → Ollama), pulando os que falham.

    exclude: provedores a pular nesta chamada (ex.: o que acabou de devolver JSON quebrado).
    timeout: tempo limite (s) de cada requisição HTTP desta chamada (padrão de cada provedor se None).
    cache: reaproveita a resposta de um prompt idêntico dos últimos minutos."""
    key = _cache_key(prompt, system, json_mode, temperature, images, prefer) if cache else ""
    if key:
        hit = _cache_get(key)
        if hit:
            log.info("LLM: resposta reaproveitada do cache (%s)", hit.provider)
            return hit
    order = list(config.get("llm_order"))
    if prefer and prefer in order:
        order.remove(prefer)
        order.insert(0, prefer)
    skip = set(exclude or ())
    if skip and all(n in skip for n in order if n in PROVIDERS):
        skip = set()  # todos excluídos: melhor tentar de novo do que não tentar
    errors = []
    old_t = getattr(_tl, "timeout", None)
    _tl.timeout = timeout
    try:
        for name in order:
            fn = PROVIDERS.get(name)
            if not fn or name in skip:
                continue
            try:
                res = fn(prompt, system, json_mode, temperature, images, None)
                if not (res.text or "").strip():
                    raise LLMError("resposta vazia")
                _count(name, True)
                if key:
                    _cache_put(key, res)
                return res
            except Exception as e:  # noqa: BLE001 — qualquer falha passa para o próximo
                _count(name, False)
                log.warning("LLM %s falhou: %s", name, e)
                errors.append(f"{name}: {e}")
    finally:
        _tl.timeout = old_t
    raise LLMError("Nenhum LLM disponível → " + " | ".join(errors))


def complete_json(prompt: str, *, system: str | None = None, temperature: float = 0.6,
                  images: list[bytes] | None = None, retries: int = 2,
                  required: list[str] | tuple[str, ...] | None = None, cache: bool = True,
                  timeout: float | None = None) -> Any:
    """JSON estruturado: modo JSON do provedor + conserto local (cercas ```, texto em volta, vírgula sobrando,
    resposta cortada). Se ainda vier quebrado ou sem as chaves obrigatórias (required), tenta de novo em OUTRO
    provedor da fila, com temperatura menor. Respostas válidas ficam no cache curto (prompt idêntico = 0 cota)."""
    last: Exception | None = None
    bad: set[str] = set()
    p, temp = prompt, temperature
    for attempt in range(retries + 1):
        res = complete(p, system=system, json_mode=True, temperature=temp, images=images,
                       exclude=bad, timeout=timeout, cache=cache and attempt == 0)
        try:
            data = parse_json(res.text)
            missing = [k for k in (required or ()) if not (isinstance(data, dict) and data.get(k) not in (None, "", [], {}))]
            if missing:
                raise ValueError(f"faltam as chaves {missing}")
            return data
        except ValueError as e:
            last = e
            log.warning("JSON inválido de %s (tentativa %d): %s", res.provider, attempt + 1, e)
            if cache and attempt == 0:
                _cache_drop(_cache_key(prompt, system, True, temperature, images, None))
            bad.add(res.provider)  # a próxima tentativa vai para o próximo provedor da fila
            temp = max(0.1, round(temp - 0.15, 2))
            p = prompt + ("\n\nIMPORTANTE: responda APENAS com um objeto JSON válido e COMPLETO — sem comentários, sem "
                          "texto antes ou depois, sem cercas ```" + (f", com as chaves {list(required)}" if required else "") + ".")
    raise LLMError(f"JSON inválido do LLM: {last}")


def parse_json(text: str) -> Any:
    """Lê o JSON da resposta da IA consertando os defeitos comuns: texto em volta, cercas ```, <think>,
    vírgula sobrando antes de fechar e resposta cortada no meio (limite de tokens)."""
    text = (text or "").strip().lstrip("﻿")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    if fence and fence.group(1).strip()[:1] in ("{", "["):
        text = fence.group(1).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    for cand in (text, _balanced(text)):
        if cand:
            try:
                return json.loads(cand, strict=False)
            except json.JSONDecodeError:
                pass
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not starts:
        raise ValueError("nenhum JSON encontrado")
    start = min(starts)
    body = _balanced(text) or text[start:]
    try:
        return json.loads(re.sub(r",\s*([}\]])", r"\1", body), strict=False)
    except json.JSONDecodeError:
        pass
    rep = _repair_truncated(text[start:])
    if rep is not None:
        return rep
    raise ValueError("JSON inválido mesmo após conserto")


def _balanced(text: str) -> str:
    """Primeiro objeto/lista JSON completo do texto (respeitando strings), ou ''."""
    starts = [i for i in (text.find("{"), text.find("[")) if i >= 0]
    if not starts:
        return ""
    start = min(starts)
    stack: list[str] = []
    in_str = esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "{[":
            stack.append("}" if c == "{" else "]")
        elif c in "}]":
            if not stack or stack.pop() != c:
                return ""
            if not stack:
                return text[start:i + 1]
    return ""


def _repair_truncated(s: str) -> Any:
    """JSON cortado no meio: volta até o último item completo e fecha as chaves/colchetes abertos."""
    stack: list[str] = []
    in_str = esc = False
    cuts: list[tuple[int, list[str]]] = []  # pontos seguros para cortar + pilha aberta naquele ponto
    for i, c in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in "{[":
            stack.append("}" if c == "{" else "]")
        elif c in "}]":
            if stack:
                stack.pop()
            cuts.append((i + 1, list(stack)))
        elif c == ",":
            cuts.append((i, list(stack)))
    tries = []
    if in_str:
        tries.append(s + '"' + "".join(reversed(stack)))
    tries.append(s + "".join(reversed(stack)))
    tries += [s[:pos] + "".join(reversed(st)) for pos, st in reversed(cuts[-60:])]
    for t in tries:
        try:
            return json.loads(re.sub(r",\s*([}\]])", r"\1", t), strict=False)
        except json.JSONDecodeError:
            continue
    return None


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
