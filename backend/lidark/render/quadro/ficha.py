"""Folha de personagem: prova de anatomia antes de renderizar um episódio.

    python -m lidark.render.quadro.ficha SAIDA.png --tmp PASTA [--referencia VIDEO --t 60.5]
"""
from __future__ import annotations

import argparse
import base64
import io
import subprocess

from PIL import Image, ImageDraw, ImageFont

from . import gerador

POSES = [('EM PÉ', 'de_pe'), ('SENTADO', 'sentado'), ('SEGURANDO', 'segura'), ('APONTANDO', 'aponta'), ('BRAÇO LEVANTADO', 'braco_alto')]
Z = 1.42


def plano(pose, ate):
    return dict(ate=ate, cenario='neutro', sem_hud=True, cam=[[0, 360, 640, 1]], atores=[
        dict(nome='ze', x=205, y=1190, escala=Z, poses=[[0, pose]]),
        dict(nome='bia', x=500, y=1190, escala=Z, poses=[[0, pose]])])


def caio(ate):
    return dict(ate=ate, cenario='neutro', sem_hud=True, cam=[[0, 360, 640, 1]], atores=[
        dict(nome='caio', x=220, y=1190, escala=1.6, poses=[[0, 'de_pe']]),
        dict(nome='caio', x=510, y=1190, escala=1.6, poses=[[0, 'sentado']])])


def renderizar(saida, tmp, ref=None, t=60.5):
    from lidark.media import ffmpeg_exe
    from pathlib import Path
    from playwright.sync_api import sync_playwright
    tmp = Path(tmp)
    tmp.mkdir(parents=True, exist_ok=True)
    pl = [plano(p, i + 1) for i, (_, p) in enumerate(POSES)] + [caio(len(POSES) + 1)]
    ep = dict(meta=250, cenas=[dict(id='f', dur=len(pl), cenario='neutro', dias=0, planos=pl)])
    html, _ = gerador.pagina(ep, tmp)
    hp = tmp / 'ficha.html'
    hp.write_text(html, encoding='utf-8')
    fs = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel='msedge')
        pg = b.new_page(viewport={'width': 1080, 'height': 1920})
        er = []
        pg.on('pageerror', lambda e: er.append(str(e)))
        pg.goto(hp.as_uri())
        cdp = pg.context.new_cdp_session(pg)
        for i in range(len(pl)):
            pg.evaluate('t=>frame(t)', i + .45)
            fs.append(Image.open(io.BytesIO(base64.b64decode(cdp.send('Page.captureScreenshot', {'format': 'png'})['data']))).convert('RGB'))
        b.close()
    if er:
        print('ERROS', er[:3])
    if ref:
        o = tmp / 'ref.png'
        subprocess.run([ffmpeg_exe(), '-y', '-v', 'error', '-ss', str(t), '-i', str(ref), '-frames:v', '1', str(o)], check=True)
        fs.append(Image.open(o).convert('RGB'))
    W, H = 760, 1351
    rot = [n for n, _ in POSES] + ['CAIO: CÓDIGO NOVO'] + (['CAIO: EPISÓDIO ANTERIOR'] if ref else [])
    cols = 4
    lin = (len(fs) + cols - 1) // cols
    fol = Image.new('RGB', (cols * W, lin * (H + 70)), '#1b1d24')
    dr = ImageDraw.Draw(fol)
    fn = ImageFont.truetype('arialbd.ttf', 44)
    for i, f in enumerate(fs):
        x, y = (i % cols) * W, (i // cols) * (H + 70)
        fol.paste(f.resize((W, H)), (x, y + 70))
        dr.text((x + 24, y + 12), rot[i], fill='#ffd23f', font=fn)
    fol.save(saida)
    print('ficha', fol.size, saida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('saida')
    ap.add_argument('--tmp', required=True)
    ap.add_argument('--referencia')
    ap.add_argument('--t', type=float, default=60.5)
    a = ap.parse_args()
    renderizar(a.saida, a.tmp, a.referencia, a.t)


if __name__ == '__main__':
    main()
