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


# ---------------------------------------------------------------- sinais de público, engajadas, cortes, diagnóstico

def _cached(key: str, fn, ttl: float = 600):
    from . import cache
    return cache.get(f"learning:{key}", fn, ttl=ttl, stale=6 * 3600)


@router.get("/audience")
def learning_audience(channel_id: Optional[int] = None) -> dict[str, Any]:
    """Origem do público (feed, busca, sugeridos...), inscritos e aparelho por formato; engajadas/views e retenção aos
    3s por opção de variedade (tipo de abertura, loop, gancho...)."""
    return learning.audience_signals(learning._get_state(), channel_id)


@router.get("/engaged")
def learning_engaged(channel_id: Optional[int] = None) -> dict[str, Any]:
    return learning.engaged_panel(channel_id)


@router.get("/cuts")
def learning_cuts(channel_id: int) -> dict[str, Any]:
    """Mapa de quedas por segundo × cortes de cena (Shorts com curva de retenção) + regra derivada."""
    from . import retention

    def run() -> dict[str, Any]:
        rows = retention.channel_retention(channel_id)
        return {**retention.cut_drops(rows, channel_id), "rule": retention.cut_rule(channel_id, rows)}
    return _cached(f"cuts:{channel_id}", run)


@router.get("/diagnose")
def learning_diagnose(channel_id: Optional[int] = None, min_age_h: float = 48, max_age_h: float = 720,
                      limit: int = 30) -> list[dict[str, Any]]:
    """“Por que flopou”: causa provável (gancho, meio, tema, miniatura) e ação sugerida, vídeo a vídeo."""
    from . import diagnose
    return _cached(f"diag:{channel_id}:{min_age_h}:{max_age_h}:{limit}",
                   lambda: diagnose.diagnose(channel_id, min_age_h, max_age_h, limit), ttl=300)


@router.get("/age-compare")
def learning_age_compare(channel_id: int, n: int = 8) -> dict[str, Any]:
    """Vídeos recentes × curva mediana do canal na mesma idade (gráfico)."""
    return learning.age_compare(channel_id, max(1, min(n, 20)))


@router.post("/signals/refresh")
def learning_signals_refresh() -> dict[str, Any]:
    """Busca agora os sinais de público que estão vencidos (o refresh do aprendizado já faz isso a cada coleta)."""
    from . import retention
    return retention.collect_signals()


# ---------------------------------------------------------------- radar de outliers e almanaque

class OutlierIdeaIn(BaseModel):
    channel_id: int
    video_id: str


@router.get("/outliers")
def learning_outliers(channel_id: int, refresh: bool = False) -> dict[str, Any]:
    """Outliers do nicho (PT e EN, views ÷ média do canal ≥ 5x) e temas em inglês ainda sem cobertura em português.
    Atualiza sozinho 1x por dia (2 buscas = 200 unidades da cota por canal)."""
    from . import radar
    return radar.outliers(channel_id, refresh)


@router.post("/outliers/idea")
def learning_outlier_idea(body: OutlierIdeaIn) -> dict[str, Any]:
    from fastapi import HTTPException

    from . import radar
    try:
        return radar.outlier_idea(body.channel_id, body.video_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


class AlmanacIdeaIn(BaseModel):
    channel_id: int
    event_id: str


@router.get("/almanac")
def learning_almanac(channel_id: int, days: int = 60, min_ahead: int = 7) -> dict[str, Any]:
    """Efemérides dos próximos dias por nicho (só fontes verificáveis ou cálculo; confiança marcada)."""
    from . import almanac
    return almanac.calendar(channel_id, max(14, min(days, 120)), max(0, min(min_ahead, 30)))


@router.post("/almanac/idea")
def learning_almanac_idea(body: AlmanacIdeaIn) -> dict[str, Any]:
    from fastapi import HTTPException

    from . import almanac
    try:
        return almanac.create_idea(body.channel_id, body.event_id)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
