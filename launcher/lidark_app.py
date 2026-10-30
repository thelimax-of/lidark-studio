"""Lidark Studio — janela de aplicativo nativa (pywebview + WebView2).

Abre o painel em TELA CHEIA TOTAL (cobre a barra de tarefas, sem barra de título), como um jogo.
A barra do topo do painel usa `window.pywebview.api` para minimizar, fechar e alternar a tela cheia.

Uso:  pythonw launcher/lidark_app.py [--url http://localhost:8765] [--windowed]
Se o pywebview/WebView2 falhar, cai para o Edge/Chrome em modo app (--app --start-fullscreen).
"""
from __future__ import annotations

import argparse
import ctypes
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TITLE = "Lidark Studio"
BG = "#07080c"


def wait_health(url: str, seconds: int = 60) -> bool:
    for _ in range(seconds):
        try:
            with urllib.request.urlopen(url.rstrip("/") + "/api/health", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def focus_existing() -> bool:
    """Se a janela já está aberta, traz para frente em vez de abrir outra."""
    if os.name != "nt":
        return False
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    # só conta a janela do próprio app (WinForms do pywebview): uma aba do Edge com o painel aberto
    # também se chama "Lidark Studio" e fazia o app achar que já estava aberto e sair sem abrir nada
    found: list[int] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def each(hwnd, _):
        title, cls = ctypes.create_unicode_buffer(256), ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, 256)
        user32.GetClassNameW(hwnd, cls, 256)
        if title.value == TITLE and cls.value.startswith("WindowsForms"):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(each, 0)
    if not found:
        return False
    hwnd = found[0]
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.SetForegroundWindow(hwnd)
    return True


def browser_fallback(url: str) -> None:
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    for exe in (Path(pf86) / "Microsoft/Edge/Application/msedge.exe", Path(pf) / "Microsoft/Edge/Application/msedge.exe",
                Path(pf) / "Google/Chrome/Application/chrome.exe"):
        if exe.exists():
            subprocess.Popen([str(exe), f"--app={url}", "--start-fullscreen"], close_fds=True)
            return
    import webbrowser
    webbrowser.open(url)


class Api:
    """Exposto ao JS como window.pywebview.api (atributos com _ não são expostos)."""

    def __init__(self, fullscreen: bool) -> None:
        self._win = None
        self._fs = fullscreen

    def minimize(self) -> None:
        self._win.minimize()

    def close(self) -> None:
        self._win.destroy()

    def toggle_fullscreen(self) -> bool:
        self._win.toggle_fullscreen()
        self._fs = not self._fs
        return self._fs

    def is_fullscreen(self) -> bool:
        return self._fs


def set_icon(window) -> None:
    """Ícone do Lidark na janela/barra de tarefas (WinForms via pythonnet)."""
    ico = ROOT / "backend" / "assets" / "lidark.ico"
    try:
        form = window.native
        if form is None or not ico.exists():
            return
        from System import Action  # type: ignore
        from System.Drawing import Icon  # type: ignore
        form.Invoke(Action(lambda: setattr(form, "Icon", Icon(str(ico)))))
    except Exception:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8765")
    ap.add_argument("--windowed", action="store_true", help="abre em janela (sem tela cheia), útil para testes")
    ap.add_argument("--no-wait", action="store_true")
    args = ap.parse_args()

    if focus_existing():
        return 0
    if not args.no_wait and not wait_health(args.url):
        ctypes.windll.user32.MessageBoxW(0, "O motor do Lidark não respondeu. Veja data\\logs\\server.log", TITLE, 0x30)
        return 1

    if os.name == "nt":  # agrupa na barra de tarefas como app próprio (não como "Python")
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Lidark.Studio")
        except Exception:
            pass

    try:
        import webview  # pywebview
    except Exception:
        browser_fallback(args.url)
        return 0

    fullscreen = not args.windowed
    api = Api(fullscreen)
    try:
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True  # só o fundo da barra arrasta, botões continuam clicáveis
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    except Exception:
        pass
    # tamanho ao sair da tela cheia: 90% da tela (centralizada)
    w, h = 1480, 920
    try:
        sc = webview.screens[0]
        w, h = int(sc.width * 0.9), int(sc.height * 0.9)
    except Exception:
        pass
    try:
        win = webview.create_window(
            TITLE, args.url, js_api=api,
            fullscreen=fullscreen, frameless=True, easy_drag=False,
            width=w, height=h, min_size=(1024, 640),
            background_color=BG, text_select=True, zoomable=True,
        )
        api._win = win
        win.events.shown += lambda: set_icon(win)
        storage = ROOT / "data" / "webview"
        storage.mkdir(parents=True, exist_ok=True)
        # private_mode=False: mantém localStorage/IndexedDB (cache instantâneo, canal selecionado, filtros)
        webview.start(gui="edgechromium", private_mode=False, storage_path=str(storage))
    except Exception:
        browser_fallback(args.url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
