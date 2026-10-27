"""Backup na nuvem: um .zip diário no seu Google Drive com tudo que não está no GitHub.

Vai no zip: banco (contas, canais, pautas, roteiros, métricas), configurações e chaves, client_secret do Google,
identidade visual dos canais (logo, capa, avatar). Fica de fora: vídeos renderizados e cache (dá para refazer).
Permissão usada: drive.file — o sistema só enxerga os arquivos que ele mesmo criou no seu Drive.
"""
from __future__ import annotations

import json
import logging
import secrets
import sqlite3
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DATA_DIR, DB_PATH, MEDIA_DIR

log = logging.getLogger("lidark.cloud")

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT = "http://localhost:8765/api/oauth/drive/callback"
SECRETS = DATA_DIR / "secrets"
TOKEN = SECRETS / "drive_token.json"
STATE = DATA_DIR / "cloud_backup.json"
LOCAL = DATA_DIR / "backups" / "cloud"
FOLDER_NAME = "Lidark Studio — backups"
KEEP = 14
_pending: dict[str, str | None] = {}


def _flow(state: str | None = None):
    from google_auth_oauthlib.flow import Flow
    cs = SECRETS / "client_secret.json"
    if not cs.exists():
        raise RuntimeError("Coloque o client_secret.json do Google Cloud em data/secrets/")
    flow = Flow.from_client_secrets_file(str(cs), scopes=SCOPES, state=state)
    flow.redirect_uri = REDIRECT
    return flow


def connect() -> dict[str, str]:
    state = secrets.token_urlsafe(16)
    flow = _flow(state)
    url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    _pending[state] = getattr(flow, "code_verifier", None)
    return {"auth_url": url}


def callback(state: str, code: str) -> None:
    import os
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    if state not in _pending:
        raise RuntimeError("Sessão de login expirada — tente de novo")
    flow = _flow(state)
    if _pending.get(state):
        flow.code_verifier = _pending[state]
    _pending.pop(state, None)
    flow.fetch_token(code=code)
    TOKEN.write_text(flow.credentials.to_json(), encoding="utf-8")


def _drive():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    if not TOKEN.exists():
        raise RuntimeError("Google Drive não conectado")
    c = Credentials.from_authorized_user_info(json.loads(TOKEN.read_text(encoding="utf-8")))
    if not c.valid and c.refresh_token:
        c.refresh(Request())
        TOKEN.write_text(c.to_json(), encoding="utf-8")
    return build("drive", "v3", credentials=c, cache_discovery=False)


def _state() -> dict[str, Any]:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save_state(**kw: Any) -> None:
    STATE.write_text(json.dumps({**_state(), **kw}, ensure_ascii=False, indent=2), encoding="utf-8")


def make_archive() -> Path:
    """Monta o .zip local (snapshot consistente do banco + configurações + identidade dos canais)."""
    LOCAL.mkdir(parents=True, exist_ok=True)
    dest = LOCAL / f"lidark-{datetime.now():%Y-%m-%d_%H%M}.zip"
    snap = LOCAL / "_snapshot.db"
    src, dst = sqlite3.connect(DB_PATH), sqlite3.connect(snap)
    with dst:
        src.backup(dst)
    src.close()
    dst.close()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(snap, "data/lidark.db")
        for name in ("settings.json", "scheduler_state.json"):
            if (DATA_DIR / name).exists():
                z.write(DATA_DIR / name, f"data/{name}")
        for p in SECRETS.glob("*.json"):
            if not p.name.startswith("accounts-backup"):
                z.write(p, f"data/secrets/{p.name}")
        # identidade dos canais: arquivos soltos na pasta do canal (logo, capa, avatar, prévias) — sem os vídeos
        if MEDIA_DIR.exists():
            for ch_dir in (d for d in MEDIA_DIR.iterdir() if d.is_dir()):
                for p in ch_dir.iterdir():
                    if p.is_file() and p.stat().st_size < 15_000_000:
                        z.write(p, f"data/media/{ch_dir.name}/{p.name}")
                for sub in ("brand", "identidade", "kit"):
                    for p in (ch_dir / sub).rglob("*") if (ch_dir / sub).exists() else []:
                        if p.is_file():
                            z.write(p, f"data/media/{ch_dir.name}/{sub}/{p.relative_to(ch_dir / sub)}")
    snap.unlink(missing_ok=True)
    for old in sorted(LOCAL.glob("lidark-*.zip"))[:-3]:  # localmente guarda só os 3 últimos
        old.unlink(missing_ok=True)
    return dest


def _folder_id(drive) -> str:
    fid = _state().get("folder_id")
    if fid:
        try:
            f = drive.files().get(fileId=fid, fields="id,trashed").execute()
            if not f.get("trashed"):
                return fid
        except Exception:  # noqa: BLE001
            pass
    f = drive.files().create(body={"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
                             fields="id").execute()
    _save_state(folder_id=f["id"])
    return f["id"]


def backup_now() -> dict[str, Any]:
    from googleapiclient.http import MediaFileUpload
    path = make_archive()
    try:
        drive = _drive()
        folder = _folder_id(drive)
        media = MediaFileUpload(str(path), mimetype="application/zip", resumable=True)
        f = drive.files().create(body={"name": path.name, "parents": [folder]}, media_body=media,
                                 fields="id,name,size,webViewLink").execute()
        files = drive.files().list(q=f"'{folder}' in parents and trashed = false", orderBy="createdTime desc",
                                   fields="files(id,name,size,createdTime)", pageSize=100).execute().get("files", [])
        for old in files[KEEP:]:
            drive.files().delete(fileId=old["id"]).execute()
        info = {"last_ok": datetime.now().isoformat(timespec="seconds"), "last_file": f["name"],
                "last_size": int(f.get("size") or 0), "last_error": "", "count": min(len(files), KEEP)}
        _save_state(**info)
        log.info("backup na nuvem: %s", f["name"])
        return info
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "accessNotConfigured" in msg or "has not been used in project" in msg or "SERVICE_DISABLED" in msg:
            msg = ("A API do Google Drive está desligada no seu projeto. Ative em "
                   "https://console.cloud.google.com/apis/library/drive.googleapis.com e tente de novo.")
        _save_state(last_error=msg[:500], last_try=datetime.now().isoformat(timespec="seconds"))
        raise RuntimeError(msg) from e


def status() -> dict[str, Any]:
    st = _state()
    return {"connected": TOKEN.exists(), "last_ok": st.get("last_ok"), "last_file": st.get("last_file"),
            "last_size": st.get("last_size"), "last_error": st.get("last_error", ""), "count": st.get("count", 0),
            "folder_url": f"https://drive.google.com/drive/folders/{st['folder_id']}" if st.get("folder_id") else None}


def _register() -> None:
    from .jobs import JobContext, handler

    @handler("cloud_backup")
    def job_cloud_backup(ctx: JobContext) -> dict:
        ctx.update(0.2, "Montando o pacote de backup")
        info = backup_now()
        ctx.log(f"Enviado ao Google Drive: {info['last_file']} ({info['last_size'] // 1024} KB) · {info['count']} cópias guardadas")
        return info


_register()
