"""Som: efeitos sintetizados aqui mesmo (sem direitos), voz, música baixa. Tudo somado em numpy."""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

SR = 44100


def _t(d):
    return np.arange(int(SR * d)) / SR


def _env(d, a=.004, q=6.0):
    t = _t(d)
    return np.minimum(1, t / a) * np.exp(-t * q)


def _ruido(d, seed=1):
    return np.random.default_rng(seed).normal(0, 1, int(SR * d))


def _lp(x, k=8):
    return np.convolve(x, np.ones(k) / k, 'same')


def _hp(x, k=8):
    return x - _lp(x, k)


def moeda(seed=0):
    d = .32
    t = _t(d)
    f = [3950, 5230, 7100, 8450]
    x = sum(np.sin(2 * np.pi * (a + seed * 37) * t) * b for a, b in zip(f, (.5, .4, .25, .15)))
    return x * _env(d, .001, 15) * .6


def moedas():
    x = np.zeros(int(SR * .9))
    r = np.random.default_rng(3)
    for i in range(7):
        p = int(r.uniform(0, .55) * SR)
        m = moeda(i)
        x[p:p + len(m)] += m * r.uniform(.5, 1)
    return x * .7


def caixa_reg():
    d = .7
    x = np.zeros(int(SR * d))
    for s, f in ((0, 1318), (.09, 1760), (.18, 2637)):
        t = _t(.4)
        b = (np.sin(2 * np.pi * f * t) + .4 * np.sin(2 * np.pi * f * 2 * t)) * _env(.4, .002, 9)
        p = int(s * SR)
        x[p:p + len(b)] += b * .5
    return x


def carimbo():
    d = .3
    t = _t(d)
    x = np.sin(2 * np.pi * (70 + 60 * np.exp(-t * 30)) * t) * _env(d, .001, 16) + _lp(_ruido(d), 14) * _env(d, .001, 40) * 1.2
    return x * .95


def pop():
    d = .13
    t = _t(d)
    return np.sin(2 * np.pi * (420 + 900 * t / d) * t) * _env(d, .002, 22) * .6


def whoosh():
    d = .34
    t = _t(d)
    return _hp(_ruido(d, 5), 6) * np.sin(np.pi * t / d) ** 2 * .22


def chiado(d=2.0):
    x = _hp(_ruido(d, 8), 3) * .16
    return x * np.minimum(1, _t(d) / .1) * np.minimum(1, (d - _t(d)) / .2)


def lapis():
    d = .28
    return _hp(_ruido(d, 2), 3) * .26 * np.sin(np.pi * _t(d) / d)


def risco():
    d = .45
    return _hp(_ruido(d, 12), 2) * .3 * (1 + .6 * np.sin(2 * np.pi * 26 * _t(d))) * np.sin(np.pi * _t(d) / d)


def miado():
    d = .55
    t = _t(d)
    f = 620 + 340 * np.sin(np.pi * t / d) - 240 * t / d
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = (np.sin(ph) + .5 * np.sin(2 * ph) + .3 * np.sin(3 * ph)) * np.sin(np.pi * t / d) ** .6
    return x * .34


def tosse():
    d = .32
    x = np.zeros(int(SR * .8))
    for s in (0, .36):
        b = _lp(_ruido(d, 3), 6) * _env(d, .004, 11) * .9
        p = int(s * SR)
        x[p:p + len(b)] += b
    return x


def trovao():
    d = 2.2
    x = _lp(_ruido(d, 9), 240) * 14 * _env(d, .05, 1.8)
    return np.clip(x, -1, 1) * .8


def chuva(d):
    x = _hp(_ruido(d, 21), 4) * .11 + _lp(_ruido(d, 22), 30) * .3
    return x * np.minimum(1, _t(d) / .4) * np.minimum(1, (d - _t(d)) / .4)


def splash():
    d = .3
    return _lp(_ruido(d, 13), 5) * _env(d, .01, 12) * .6


def clique():
    d = .05
    return _hp(_ruido(d, 6), 3) * _env(d, .001, 80) * .5


def papel():
    d = .24
    return _hp(_ruido(d, 15), 2) * .22 * (1 + np.sin(2 * np.pi * 34 * _t(d))) * np.sin(np.pi * _t(d) / d)


def passo():
    d = .1
    t = _t(d)
    return np.sin(2 * np.pi * 95 * t) * _env(d, .002, 34) * .5


def sucesso():
    d = 1.0
    x = np.zeros(int(SR * d))
    for s, f in ((0, 523), (.12, 659), (.24, 784), (.36, 1047)):
        t = _t(.6)
        b = (np.sin(2 * np.pi * f * t) + .3 * np.sin(2 * np.pi * f * 2 * t)) * _env(.6, .004, 6)
        p = int(s * SR)
        x[p:p + len(b)] += b * .4
    return x


def perda():
    d = 1.0
    x = np.zeros(int(SR * d))
    for s, f in ((0, 392), (.2, 330), (.42, 247)):
        t = _t(.5)
        b = (np.sin(2 * np.pi * f * t) + .2 * np.sin(2 * np.pi * f * 3 * t)) * _env(.5, .006, 6)
        p = int(s * SR)
        x[p:p + len(b)] += b * .4
    return x


def desce():
    d = .5
    t = _t(d)
    ph = 2 * np.pi * np.cumsum(520 - 360 * t / d) / SR
    return np.sin(ph) * _env(d, .004, 4) * .42


def aviso():
    d = .4
    t = _t(d)
    return np.sign(np.sin(2 * np.pi * 280 * t)) * _env(d, .002, 7) * .14


def vibra():
    d = .7
    t = _t(d)
    return np.sin(2 * np.pi * 150 * t) * (np.sin(2 * np.pi * 3.2 * t) > 0) * .5


def freio():
    d = .8
    t = _t(d)
    ph = 2 * np.pi * np.cumsum(2400 + 500 * np.sin(2 * np.pi * 7 * t)) / SR
    return np.sin(ph) * np.sin(np.pi * t / d) * .16


def batida():
    d = .7
    return np.clip(_lp(_ruido(d, 31), 9) * 6 * _env(d, .002, 7), -1, 1) * .9 + carimbo_longo(d)


def carimbo_longo(d):
    t = _t(d)
    return np.sin(2 * np.pi * (60 + 80 * np.exp(-t * 18)) * t) * _env(d, .001, 8) * .9


def splat():
    d = .35
    return _lp(_ruido(d, 17), 4) * _env(d, .004, 10) * .8


def arfar():
    d = 1.1
    t = _t(d)
    return _hp(_ruido(d, 19), 5) * .16 * (np.sin(2 * np.pi * 1.8 * t) ** 2)


def sobe_escada():
    x = np.zeros(int(SR * 1.2))
    for i in range(6):
        b = passo()
        p = int(i * .2 * SR)
        x[p:p + len(b)] += b
    return x


def ding():
    d = .6
    t = _t(d)
    return (np.sin(2 * np.pi * 1320 * t) + .4 * np.sin(2 * np.pi * 2640 * t)) * _env(d, .002, 6) * .4


def teclas():
    x = np.zeros(int(SR * .7))
    for i in range(6):
        b = clique()
        p = int(i * .11 * SR)
        x[p:p + len(b)] += b
    return x


SONS = dict(vibra=vibra, freio=freio, batida=batida, splat=splat, arfar=arfar, sobe_escada=sobe_escada, ding=ding, teclas=teclas, moeda=moeda, moedas=moedas, caixa=caixa_reg, carimbo=carimbo, pop=pop, whoosh=whoosh, lapis=lapis, risco=risco, miado=miado, tosse=tosse, trovao=trovao,
            splash=splash, clique=clique, papel=papel, passo=passo, sucesso=sucesso, perda=perda, desce=desce, aviso=aviso)


def _ler(ff, p, tmp):
    o = Path(tmp) / (Path(p).stem + '_dec.raw')
    subprocess.run([ff, '-y', '-v', 'error', '-i', str(p), '-f', 'f32le', '-ac', '1', '-ar', str(SR), str(o)], check=True)
    return np.fromfile(o, dtype='<f4')


def mixar(ep, total, tmp, ff):
    from lidark import music
    n = int(total * SR) + SR
    voz = np.zeros(n)
    fx = np.zeros(n)
    amb = np.zeros(n)

    def soma(buf, x, t, vol=1.0):
        p = int(t * SR)
        e = min(n, p + len(x))
        if e > p:
            buf[p:e] += x[:e - p] * vol

    t = 0.0
    for c in ep['cenas']:
        for f in c.get('falas', []):
            soma(voz, _ler(ff, f['_mp3'], tmp), t + f['t'], 1.0)
        for s in c.get('sfx', []):
            nome, at = s[0], s[1]
            vol = s[2] if len(s) > 2 else 1.0
            if nome == 'chiado':
                soma(fx, chiado(s[3]), t + at, vol)
            else:
                soma(fx, SONS[nome](), t + at, vol)
        for a in c.get('ambiente', []):
            if a[0] == 'chuva':
                soma(amb, chuva(a[2]), t + a[1], a[3] if len(a) > 3 else 1)
        if t > 0:
            soma(fx, whoosh(), t - .12, .8)
        t += c['dur']
    try:
        bed = music.ambient_track(total + 2, seed=ep.get('seed_musica', 23), mood=ep.get('musica', 'leve esperançosa'))
    except Exception:  # noqa: BLE001 — sem trilha o episódio ainda sai
        bed = None
    import wave as _w
    with _w.open(str(Path(tmp) / 'voz.wav'), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(voz, -1, 1) * 32767).astype('<i2').tobytes())
    mus = _ler(ff, bed, tmp) if bed else np.zeros(n)
    mus = np.pad(mus, (0, max(0, n - len(mus))))[:n]
    mus = mus / (np.max(np.abs(mus)) + 1e-6)
    # a música abaixa quando há voz
    env = np.convolve(np.abs(voz), np.ones(SR // 5) / (SR // 5), 'same')
    ganho = .17 - .09 * np.clip(env * 12, 0, 1)
    voz = voz / (np.max(np.abs(voz)) + 1e-6)
    mx = voz * 1.0 + fx * .62 + amb * .5 + mus * ganho
    mx = np.tanh(mx * 1.1) * .92
    o = Path(tmp) / 'mix.wav'
    import wave
    with wave.open(str(o), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(mx, -1, 1) * 32767).astype('<i2').tobytes())
    return o
