"""Render de um projeto: python -m lidark.construcao.render <pasta> previa|mudo

previa: narração + 12 quadros em previa.jpg. mudo: tmp/mudo.mp4 e tmp/audio.json (usado por audio.py).
Imprime "P <n> <total>" para a tarefa acompanhar o progresso, e sai com código 2 se a cena não carregar.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from lidark import tts
from lidark.media import ffmpeg_exe

from . import MOTOR

ARGS = ["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist", "--force_high_performance_gpu"]
CSS = ('html,body{margin:0;background:#000;width:1080px;height:1920px;overflow:hidden}#c,#hud{position:absolute;inset:0}'
       '#leg{position:absolute;left:540px;top:1240px;white-space:nowrap;font:900 84px "Segoe UI",Arial;-webkit-text-stroke:14px #111;paint-order:stroke fill}'
       '.r{position:absolute;white-space:nowrap;font:900 40px "Segoe UI",Arial}.pilula{background:#fff;color:#111;padding:8px 26px;border-radius:40px;box-shadow:0 5px 0 #0003}'
       '.ouro{color:#ffd23f;font-size:64px;-webkit-text-stroke:11px #111;paint-order:stroke fill}.ruim{color:#ff4b4b;font-size:60px;-webkit-text-stroke:10px #fff;paint-order:stroke fill}'
       '.grande{color:#ffd23f;font-size:120px;-webkit-text-stroke:15px #111;paint-order:stroke fill}')


def _dur(ff: str, p: Path) -> float:
    r = subprocess.run([ff, "-hide_banner", "-i", str(p)], capture_output=True, text=True, errors="ignore").stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def narracao(pasta: Path, proj: dict, ff: str) -> tuple[list[dict], float]:
    tmp = pasta / "tmp"
    tmp.mkdir(exist_ok=True)
    fs, t = [], .25
    for x in proj["falas"]:
        o = tmp / (hashlib.md5((x + proj["voz"] + proj["rate"]).encode()).hexdigest()[:12] + ".mp3")
        j = o.with_suffix(".json")
        if not o.exists() or not j.exists():
            r = tts.synthesize(x, o, provider="edge", voice=proj["voz"], rate=proj["rate"])
            j.write_text(json.dumps(r.get("words") or []), encoding="utf-8")
        d = _dur(ff, o)
        w = [{"w": a["w"], "start": a["start"] + t, "end": a["end"] + t} for a in json.loads(j.read_text(encoding="utf-8"))]
        fs.append({"t": t, "dur": d, "texto": x, "words": w, "mp3": str(o)})
        t += d + .14
    return fs, round(t + .9 + float(proj.get("cauda") or 0), 2)


def pagina(pasta: Path, proj: dict, fs: list[dict], total: float) -> Path:
    d = {"falas": [{k: v for k, v in f.items() if k != "mp3"} for f in fs], "total": total, "cauda": float(proj.get("cauda") or 0), "destaque": proj.get("destaque", [])}
    kit = (MOTOR / "kit.bundle.js").read_text(encoding="utf-8")
    cena = (pasta / "cena.js").read_text(encoding="utf-8")
    bib = ""
    if proj.get("biblioteca"):
        pecas = [MOTOR / "biblioteca" / "base.js", *sorted((MOTOR / "biblioteca" / "itens").glob("*.js"))]
        bib = "".join("<script>" + f.read_text(encoding="utf-8") + "</script>" for f in pecas)
    hp = pasta / "tmp" / "pagina.html"
    hp.write_text(f"<!doctype html><meta charset=utf8><style>{CSS}</style><div id=c></div><div id=hud></div><div id=leg></div>"
                  f"<script>window.ZOOM={float(proj.get('zoom') or 1)};window.DADOS={json.dumps(d, ensure_ascii=False)}</script><script>{kit}</script>{bib}<script>{cena}</script>", encoding="utf-8")
    return hp


def main() -> None:
    from PIL import Image
    from playwright.sync_api import sync_playwright
    pasta, modo = Path(sys.argv[1]), sys.argv[2]
    if len(sys.argv) > 3:
        os.environ["QUADROS"] = sys.argv[3]
    proj = json.loads((pasta / "projeto.json").read_text(encoding="utf-8"))
    ff = ffmpeg_exe()
    fs, total = narracao(pasta, proj, ff)
    print("TOTAL", total, flush=True)
    hp = pagina(pasta, proj, fs, total)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", args=ARGS)
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        er: list[str] = []
        pg.on("pageerror", lambda e: er.append(str(e)))
        pg.on("console", lambda m: er.append(m.text) if m.type == "error" else None)
        pg.goto(hp.as_uri())
        try:
            pg.wait_for_function("window.pronto===true", timeout=60000)
        except Exception:  # noqa: BLE001
            print("ERRO_CENA", json.dumps(er[:4], ensure_ascii=False), flush=True)
            sys.exit(2)
        cdp = pg.context.new_cdp_session(pg)
        shot = lambda q: base64.b64decode(cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": q, "optimizeForSpeed": True})["data"])  # noqa: E731
        if modo == "previa":
            mids = [f["t"] + f["dur"] * .75 for f in fs]
            ts = [mids[round(i * (len(mids) - 1) / 10)] for i in range(11)] + [pg.evaluate("window.CAPA_T ?? 0") or total * .96]
            if os.environ.get("QUADROS"):
                ts = [float(x) for x in os.environ["QUADROS"].split(",")]
            W, H = 300, 533
            s = Image.new("RGB", (W * 6, H * 2))
            for i, t in enumerate(ts):
                pg.evaluate("t=>frame(t)", t)
                s.paste(Image.open(io.BytesIO(shot(85))).resize((W, H)), (i % 6 * W, i // 6 * H))
            s.save(pasta / "previa.jpg", quality=85)
            print("OCULTAS", json.dumps(pg.evaluate("window.OCULTAS||[]"), ensure_ascii=False), flush=True)
            if er:
                print("ERRO_CENA", json.dumps(er[:4], ensure_ascii=False), flush=True)
                sys.exit(2)
        else:
            mudo = pasta / "tmp" / "mudo.mp4"
            enc = subprocess.Popen([ff, "-y", "-v", "error", "-f", "image2pipe", "-c:v", "mjpeg", "-framerate", "30", "-i", "-", "-vf", "scale=in_range=full:out_range=tv,format=yuv420p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:v", "libx264", "-preset", "medium", "-crf", "20", str(mudo)], stdin=subprocess.PIPE)
            n_q = int(total * 30)
            for n in range(n_q):
                pg.evaluate("t=>frame(t)", n / 30)
                enc.stdin.write(shot(95))
                if n % 15 == 0:
                    print("P", n, n_q, flush=True)
            enc.stdin.close()
            enc.wait()
            sons = pg.evaluate("window.SONS||[]")
            (pasta / "tmp" / "audio.json").write_text(json.dumps({"sons": sons, "falas": [{"t": f["t"], "mp3": f["mp3"]} for f in fs], "total": total}), encoding="utf-8")
            # capa vertical: objeto completo quando a cena informa CAPA_T, sem legenda
            pg.add_style_tag(content="#leg,#hud{display:none!important}")
            pg.evaluate("t=>frame(window.CAPA_T ?? t)", total * .42)
            (pasta / "tmp" / "capa_base.jpg").write_bytes(shot(92))
        b.close()


if __name__ == "__main__":
    main()
