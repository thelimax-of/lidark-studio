"""Ponto de entrada: python -m lidark.main  →  http://127.0.0.1:8765"""
from __future__ import annotations

import logging
import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import brandwizard, channels, cloud, community, enem, importer, inspector, longform, pipeline, publish, radar  # noqa: F401  (registra handlers da fila)
from .api import router
from .cache import FastJSON
from .config import FRONTEND_DIST, MEDIA_DIR
from .render.core import FONTS as FONTS_DIR
from .db import init_db
from .jobs import start_workers
from .seed import seed

mimetypes.add_type("application/manifest+json", ".webmanifest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


class CacheHeaders:
    """Cache do navegador: /assets do Vite (nome com hash) é imutável; index.html e sw.js sempre revalidam."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        path = scope.get("path", "") if scope["type"] == "http" else ""
        if not path or path.startswith(("/api/", "/media/")):
            return await self.app(scope, receive, send)
        if path.startswith("/assets/"):
            value = b"public, max-age=31536000, immutable"
        elif path.startswith("/fonts/"):
            value = b"public, max-age=604800"
        elif path == "/" or path.endswith((".html", "sw.js", ".webmanifest")) or "." not in path.rsplit("/", 1)[-1]:
            value = b"no-cache"  # index.html (inclusive rotas do SPA) e service worker
        else:
            value = b"public, max-age=86400"  # ícones da raiz

        async def send2(msg) -> None:
            if msg["type"] == "http.response.start" and msg.get("status", 200) < 400:
                headers = list(msg.get("headers") or [])
                if not any(k.lower() == b"cache-control" for k, _ in headers):
                    headers.append((b"cache-control", value))
                    msg = {**msg, "headers": headers}
            await send(msg)

        await self.app(scope, receive, send2)


app = FastAPI(title="Lidark Channel", version="2.0.0", default_response_class=FastJSON)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.add_middleware(CacheHeaders)
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)  # SSE, vídeo e imagens ficam de fora
app.include_router(router)
app.include_router(__import__("lidark.api_growth", fromlist=["router"]).router)  # sino, viral, tendências, miniaturas, piloto
app.include_router(__import__("lidark.api_learning", fromlist=["router"]).router)  # aprendizado (o que o sistema aprendeu)
app.include_router(__import__("lidark.api_publish2", fromlist=["router"]).router)  # cota YouTube, idiomas, legendas, checklist, aprovação
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
app.mount("/fonts", StaticFiles(directory=FONTS_DIR), name="fonts")


@app.on_event("startup")
def _startup() -> None:
    init_db()
    seed()
    start_workers()
    from . import analytics
    analytics.register_hooks()  # coleta de métricas/publicação terminou → caches da visão geral atualizam
    _prewarm()
    try:
        from . import scheduler
        scheduler.start()
    except ImportError:
        pass


def _prewarm() -> None:
    """Enche o cache da visão geral (YouTube Analytics) logo depois de subir: o 1º acesso já sai rápido."""
    import threading
    import time

    def run():
        time.sleep(15)
        try:
            from .analytics import overview
            overview(28)
        except Exception as e:  # noqa: BLE001
            logging.getLogger("lidark.main").warning("pré-aquecimento da visão geral: %s", e)

    threading.Thread(target=run, daemon=True, name="prewarm").start()


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = FRONTEND_DIST / path
        return FileResponse(f if path and f.is_file() else FRONTEND_DIST / "index.html")


def run() -> None:
    import uvicorn
    uvicorn.run("lidark.main:app", host="127.0.0.1", port=8765, reload=False)


if __name__ == "__main__":
    run()
