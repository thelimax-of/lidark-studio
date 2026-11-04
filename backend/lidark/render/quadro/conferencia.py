"""Conferência do MP4 final: folhas de 4 quadros por segundo e medidas em todos os quadros.

    python -m lidark.render.quadro.conferencia VIDEO.mp4 EP.json PASTA
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np


def cortes(ep):
    t, out = 0.0, []
    for c in ep['cenas']:
        for p in c['planos']:
            out.append(round(t + p.get('ate', c['dur']), 3))
        t += c['dur']
    return out, [(c['id'], sum(x['dur'] for x in ep['cenas'][:i]), c['dur']) for i, c in enumerate(ep['cenas'])]


def medir(video, ep, ff):
    W, H = 180, 320
    p = subprocess.Popen([ff, '-v', 'error', '-i', str(video), '-vf', f'scale={W}:{H}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE)
    ant = None
    dif, med, dv = [], [], []
    while True:
        b = p.stdout.read(W * H)
        if len(b) < W * H:
            break
        a = np.frombuffer(b, np.uint8).astype(np.int16)[W * 45:]  # ignora o HUD
        med.append(a.mean())
        dv.append(a.std())
        dif.append(0.0 if ant is None else float(np.abs(a - ant).mean()))
        ant = a
    p.wait()
    dif = np.array(dif)
    ct, _ = cortes(ep)
    fr = lambda t: int(round(t * 30))
    corte_q = {fr(t) + d for t in ct for d in (-1, 0, 1)}
    rel = dict(quadros=len(dif))
    rel['vazios'] = [round(i / 30, 2) for i in range(len(dif)) if med[i] < 10 or dv[i] < 5]
    rel['saltos_fora_de_corte'] = [(round(i / 30, 2), round(float(dif[i]), 1)) for i in range(len(dif)) if dif[i] > 12 and i not in corte_q]
    lim = .14
    par, ini = [], None
    for i, d in enumerate(dif):
        if d < lim:
            ini = i if ini is None else ini
        else:
            if ini is not None and i - ini > 45:
                par.append((round(ini / 30, 2), round(i / 30, 2)))
            ini = None
    if ini is not None and len(dif) - ini > 45:
        par.append((round(ini / 30, 2), round(len(dif) / 30, 2)))
    rel['parado_mais_1_5s'] = par
    rel['dif_mediana'] = round(float(np.median(dif)), 3)
    return rel


def medir_voz(wav, total):
    """Cobertura da voz medida no áudio da narração, sem música nem efeitos."""
    import wave
    with wave.open(str(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(float) / 32768
    q = int(sr * .02)
    n = min(len(x) // q, int(total * 50))
    e = np.sqrt(np.mean(x[:n * q].reshape(n, q) ** 2, axis=1))
    ativo = e > max(.006, e.max() * .02)
    ult = int(np.nonzero(ativo)[0][-1])
    pausas, ini = [], None
    for i in range(ult + 1):
        if not ativo[i]:
            ini = i if ini is None else ini
        elif ini is not None:
            pausas.append((round(ini * .02, 2), round((i - ini) * .02, 2)))
            ini = None
    fala = sum(d for _, d in pausas if d < .35) + float(ativo.sum()) * .02
    return dict(cobertura_pct=round(fala / total * 100, 1), so_som_pct=round(float(ativo.sum()) * .02 / total * 100, 1), pausa_max_s=max((d for _, d in pausas), default=0),
                pausas_acima_1_2s=[p for p in pausas if p[1] > 1.2], ultima_fala_s=round(ult * .02, 2), duracao_s=round(total, 2))


def folhas(video, ep, pasta, ff):
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    _, cen = cortes(ep)
    for nome, t0, d in cen:
        n = int(np.ceil(d * 4))
        col = 8
        lin = int(np.ceil(n / col))
        subprocess.run([ff, '-y', '-v', 'error', '-ss', f'{t0:.2f}', '-t', f'{d:.2f}', '-i', str(video), '-vf', f'fps=4,scale=250:-1,tile={col}x{lin}', '-frames:v', '1', '-q:v', '3', str(pasta / f'folha_{nome}.jpg')], check=True)


def main():
    from lidark.media import ffmpeg_exe
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    video, epf, pasta = sys.argv[1:4]
    ep = json.loads(Path(epf).read_text(encoding='utf-8-sig'))
    ff = ffmpeg_exe()
    print(json.dumps(medir(video, ep, ff), ensure_ascii=False))
    if len(sys.argv) > 4:
        print(json.dumps(medir_voz(sys.argv[4], sum(c['dur'] for c in ep['cenas'])), ensure_ascii=False))
    folhas(video, ep, pasta, ff)


if __name__ == '__main__':
    main()
