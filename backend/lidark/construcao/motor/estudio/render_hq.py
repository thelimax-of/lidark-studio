"""Render de alta qualidade, fora do app: cada quadro é a média de SUB imagens em instantes próximos.
Grava em trechos: se for interrompido, rodar de novo continua de onde parou.
Uso, a partir de backend: python -m lidark.construcao.motor.estudio.render_hq <pasta> [sub]
"""
import base64, io, json, subprocess, sys, time
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

sys.path.insert(0, '.')
from lidark.construcao.render import ARGS, narracao, pagina
from lidark.media import ffmpeg_exe

pasta, SUB = Path(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 2
OBT, TRECHO = .5, 300  # fração do quadro com o obturador aberto; quadros por trecho
proj = json.loads((pasta / 'projeto.json').read_text(encoding='utf-8'))
ff = ffmpeg_exe()
fs, total = narracao(pasta, proj, ff)
hp = pagina(pasta, proj, fs, total)
dir_ = pasta / 'tmp' / 'trechos'; dir_.mkdir(parents=True, exist_ok=True)
marca = dir_ / 'versao.txt'; versao = str((pasta / 'cena.js').stat().st_mtime) + json.dumps([proj['falas'], proj['voz'], proj['rate'], proj.get('zoom')], ensure_ascii=False)
if not marca.exists() or marca.read_text(encoding='utf-8') != versao:  # cena mudou: trechos antigos não valem
    for f in dir_.glob('*.mp4'):
        f.unlink()
    marca.write_text(versao, encoding='utf-8')
n = int(total * 30)
with sync_playwright() as p:
    b = p.chromium.launch(channel='msedge', args=ARGS)
    pg = b.new_page(viewport={'width': 1080, 'height': 1920})
    er = []
    pg.on('pageerror', lambda e: er.append(str(e)))
    pg.goto(hp.as_uri())
    pg.wait_for_function('window.pronto===true', timeout=120000)
    cdp = pg.context.new_cdp_session(pg)
    shot = lambda: base64.b64decode(cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 97, 'optimizeForSpeed': True})['data'])
    t0 = time.time()
    for ini in range(0, n, TRECHO):
        out = dir_ / f'{ini:06d}.mp4'
        if out.exists():
            print('pronto', ini, flush=True); continue
        tmp = out.with_suffix('.parcial.mp4')
        enc = subprocess.Popen([ff, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '1080x1920', '-r', '30', '-i', '-', '-vf', 'format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', str(tmp)], stdin=subprocess.PIPE)
        for i in range(ini, min(ini + TRECHO, n)):
            acc = None
            for k in range(SUB):
                pg.evaluate('t=>frame(t)', (i + k / SUB * OBT) / 30)
                a = np.asarray(Image.open(io.BytesIO(shot())).convert('RGB'), np.float32)
                acc = a if acc is None else acc + a
            enc.stdin.write((acc / SUB + .5).astype(np.uint8).tobytes())
        enc.stdin.close(); enc.wait(); tmp.replace(out)
        print('P', min(ini + TRECHO, n), n, flush=True)
    (pasta / 'tmp' / 'audio.json').write_text(json.dumps({'sons': pg.evaluate('window.SONS||[]'), 'falas': [{'t': f['t'], 'mp3': f['mp3']} for f in fs], 'total': total}), encoding='utf-8')
    pg.add_style_tag(content='#leg,#hud{display:none!important}')
    pg.evaluate('t=>frame(window.CAPA_T ?? t)', total * .42)
    (pasta / 'tmp' / 'capa_base.jpg').write_bytes(shot())
    b.close()
lista = dir_ / 'lista.txt'
lista.write_text(''.join(f"file '{f.as_posix()}'\n" for f in sorted(dir_.glob('[0-9]*.mp4')) if 'parcial' not in f.name), encoding='utf-8')
subprocess.run([ff, '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lista), '-c', 'copy', str(pasta / 'tmp' / 'mudo.mp4')], check=True)
print('ok', total, er[:3])
