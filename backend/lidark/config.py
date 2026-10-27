"""Configuração global: caminhos e chaves salvas em data/settings.json (editáveis pelo painel)."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("LIDARK_DATA", ROOT / "data"))
DB_PATH = DATA_DIR / "lidark.db"
SETTINGS_PATH = DATA_DIR / "settings.json"
MEDIA_DIR = DATA_DIR / "media"
CACHE_DIR = DATA_DIR / "cache"
MUSIC_DIR = DATA_DIR / "music"
SECRETS_DIR = DATA_DIR / "secrets"
FRONTEND_DIST = ROOT / "frontend" / "dist"
# Wikimedia exige User-Agent identificável (https://w.wiki/4wJS)
USER_AGENT = "LidarkChannel/2.0 (https://github.com/lidark-channel/lidark; local educational tool) httpx/0.28"

for _d in (DATA_DIR, MEDIA_DIR, CACHE_DIR, MUSIC_DIR, SECRETS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DEFAULTS: dict[str, Any] = {
    # LLMs — ordem de fallback
    "llm_order": ["gemini", "glm", "ollama"],
    "gemini_api_keys": [],  # várias chaves = mais cota gratuita (rotação automática)
    "gemini_model": "gemini-3.5-flash",
    "gemini_fallback_models": ["gemini-flash-latest", "gemini-3.5-flash-lite"],
    "gemini_vision_model": "gemini-3.5-flash-lite",  # mais cota diária para avaliar imagens
    "glm_api_key": "",
    "glm_base_url": "https://api.z.ai/api/paas/v4",
    "glm_model": "glm-4.5-flash",
    "trend_radar_enabled": True,  # radar diário das 7h (cria pautas sozinho)
    "auto_ideas_on_setup": True,  # canal recém-conectado ganha 8 pautas automaticamente
    "footage_enabled": False,  # filmagens reais nas cenas (experimental, desligado)
    "ntfy_enabled": False,  # avisos no celular (app ntfy)
    "ntfy_server": "https://ntfy.sh",
    "ntfy_topic": "",
    "ntfy_muted": [],  # eventos silenciados: ready, review, failed, published, comments, daily
    "glm_vision_models": ["glm-4.6v-flash", "glm-4.6v-flashx"],  # reserva de visão: grátis, depois o barato
    "ollama_url": "http://127.0.0.1:11434",
    "ollama_model": "qwen3:8b",
    # TTS
    "gemini_tts_model": "gemini-3.8-flash-tts",
    # Imagens
    "pexels_api_key": "",
    "smithsonian_api_key": "",  # grátis em api.data.gov (sem ela usa DEMO_KEY, com limite)
    "image_ai_provider": "none",  # none | pollinations | gemini (pago) — Pollinations grátis gerou imagens ruins
    "pollinations_model": "flux",
    "image_min_quality": 70,
    "no_attribution_only": True,  # só imagens/músicas que dispensam crédito (domínio público, CC0, NASA, Pexels)
    # Render
    "use_nvenc": True,
    "whisper_model": "small",
    "whisper_device": "cuda",
}

_lock = threading.Lock()


def load_settings() -> dict[str, Any]:
    data = dict(DEFAULTS)
    if SETTINGS_PATH.exists():
        try:
            data.update(json.loads(SETTINGS_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            pass
    # Variáveis de ambiente têm prioridade (ex.: GEMINI_API_KEYS=a,b)
    if os.environ.get("GEMINI_API_KEYS"):
        data["gemini_api_keys"] = [k.strip() for k in os.environ["GEMINI_API_KEYS"].split(",") if k.strip()]
    if os.environ.get("GLM_API_KEY"):
        data["glm_api_key"] = os.environ["GLM_API_KEY"]
    return data


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        current = load_settings()
        for k, v in patch.items():
            if k not in DEFAULTS:
                continue
            if isinstance(v, str) and _is_masked(v):
                continue  # o painel devolveu o valor mascarado: mantém o original
            if isinstance(v, list) and k in SECRET_KEYS:
                originals = {_mask(o): o for o in current.get(k, [])}
                v = [originals.get(x, x) for x in v if not _is_masked(x) or x in originals]
            current[k] = v
        SETTINGS_PATH.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
        return current


def get(key: str) -> Any:
    return load_settings().get(key, DEFAULTS.get(key))


SECRET_KEYS = {"gemini_api_keys", "glm_api_key", "pexels_api_key", "smithsonian_api_key"}


def public_settings() -> dict[str, Any]:
    """Configurações para o painel, com segredos mascarados."""
    out = {}
    for k, v in load_settings().items():
        if k in SECRET_KEYS:
            if isinstance(v, list):
                out[k] = [_mask(x) for x in v]
            else:
                out[k] = _mask(v) if v else ""
        else:
            out[k] = v
    return out


def _mask(v: str) -> str:
    return v[:4] + "…" + v[-4:] if len(v) > 10 else "••••"


def _is_masked(v: str) -> bool:
    return "…" in v or v == "••••"
