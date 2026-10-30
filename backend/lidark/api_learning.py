"""API do aprendizado: o que o sistema aprendeu, previsão de pautas, sinais precoces e recálculo."""
from __future__ import annotations

import threading
from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from . import learning

router = APIRouter(prefix="/api/learning")

_refreshing = threading.Lock()


@router.get("/report")
def learning_report(channel_id: Optional[int] = None) -> dict[str, Any]:
    """Relatório por canal (ou de todos, sem channel_id): lições com confiança, efeitos por dimensão, acurácia do
    modelo fora da amostra, previsto × real e a curva típica de views por idade."""
    return learning.report(channel_id)


class PredictIn(BaseModel):
    channel_id: int
    title: str
    hook: str = ""
    format: str = "short"
    extra: dict[str, Any] = {}


@router.post("/predict")
def learning_predict(body: PredictIn) -> dict[str, Any]:
    return learning.predict(body.channel_id, body.title, body.hook, body.format, body.extra)


@router.get("/breakouts")
def learning_breakouts(hours: int = 48, channel_id: Optional[int] = None) -> list[dict[str, Any]]:
    rows = learning.breakouts(hours)
    return [r for r in rows if channel_id is None or r["channel_id"] == channel_id]


@router.get("/variety")
def learning_variety(channel_id: int) -> dict[str, Any]:
    """Pesos que o sorteio de variedade está usando agora (50 = neutro) e o detalhe por opção."""
    return {"weights": learning.recommend_variety(channel_id), "dimensions": learning.variety_detail(channel_id)}


@router.get("/context")
def learning_context(channel_id: int, purpose: str = "ideas") -> dict[str, str]:
    """Texto que entra no prompt da IA (para conferir o que ela está recebendo)."""
    return {"purpose": purpose, "text": learning.prompt_context(channel_id, purpose)}


@router.post("/refresh")
def learning_refresh(channel_id: Optional[int] = None, wait: bool = False) -> dict[str, Any]:
    """Recalcula tudo. Por padrão roda em segundo plano (leva poucos segundos; busca legendas de importados)."""
    if wait:
        with _refreshing:
            return learning.refresh(channel_id)
    if _refreshing.locked():
        return {"ok": True, "running": True}

    def run() -> None:
        with _refreshing:
            try:
                learning.refresh(channel_id)
            except Exception:  # noqa: BLE001
                learning.log.exception("aprendizado: refresh")

    threading.Thread(target=run, daemon=True, name="learning-refresh").start()
    return {"ok": True, "running": True}
