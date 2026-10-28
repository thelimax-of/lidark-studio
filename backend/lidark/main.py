"""Ponto de entrada: python -m lidark.main  →  http://127.0.0.1:8765"""
from __future__ import annotations

import logging
import mimetypes

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import brandwizard, channels, cloud, community, enem, importer, inspector, longform, pipeline, publish, radar  # noqa: F401  (registra handlers da fila)
from .api import router
from .config import FRONTEND_DIST, MEDIA_DIR
from .render.core import FONTS as FONTS_DIR
from .db import init_db
from .jobs import start_workers
from .seed import seed

mimetypes.add_type("application/manifest+json", ".webmanifest")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Lidark Channel", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")
app.mount("/fonts", StaticFiles(directory=FONTS_DIR), name="fonts")


@app.on_event("startup")
def _startup() -> None:
    init_db()
    seed()
    start_workers()
    try:
        from . import scheduler
        scheduler.start()
    except ImportError:
        pass


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
