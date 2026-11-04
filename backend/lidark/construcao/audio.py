"""Som final: voz + efeitos sintetizados + música própria (gerada aqui, sem direitos de terceiros).
python -m lidark.construcao.audio <pasta tmp> <saida.mp4>"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
tmp = Path(sys.argv[1]); saida = sys.argv[2]
from lidark import sfx
from lidark.media import ffmpeg_exe
FF = ffmpeg_exe(); SR = 44100; A = json.load(open(tmp / 'audio.json', encoding='utf8')); T = A['total']; N = int(T * SR) + SR
rng = np.random.default_rng(7)


def ler(p):
    r = subprocess.run([FF, '-v', 'error', '-i', str(p), '-f', 's16le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True)
    return np.frombuffer(r.stdout, np.int16).astype(np.float32) / 32768


def por(buf, x, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf):
        return
    n = min(len(x), len(buf) - i); buf[i:i + n] += x[:n] * g


def env(d, a=.002, r=.08):
    t = np.arange(int(d * SR)) / SR
    return np.minimum(t / a, 1) * np.exp(-t / r)


def tom(f, d, r=.1):
    t = np.arange(int(d * SR)) / SR
    return np.sin(2 * np.pi * f * t) * env(d, r=r)


def ruido(d, r=.1):
    return rng.standard_normal(int(d * SR)).astype(np.float32) * env(d, r=r)


def pb(x, a):
    y = np.empty_like(x); s = 0.
    for i, v in enumerate(x):
        s += a * (v - s); y[i] = s
    return y


def so(*x):
    n = max(len(a) for a in x); o = np.zeros(n, np.float32)
    for a in x:
        o[:len(a)] += a
    return o


FX = {
 'toc': so(tom(420, .09, .03) * .7, pb(ruido(.05, .012), .5) * .5),
 'tijolo': so(tom(1650, .08, .02) * .35, tom(640, .1, .03) * .6, pb(ruido(.05, .01), .6) * .3),
 'telha': so(tom(2350, .1, .025) * .3, tom(1200, .12, .03) * .4),
 'pop': np.sin(2 * np.pi * np.cumsum(np.linspace(380, 900, int(.09 * SR))) / SR) * env(.09, r=.05),
 'concreto': pb(ruido(1.1, .5), .05) * 3,
 'furadeira': so(np.sign(np.sin(2 * np.pi * 95 * np.arange(int(.85 * SR)) / SR)).astype(np.float32) * .25, pb(ruido(.85, 2), .3)),
 'motor': (lambda n: ((np.sin(2 * np.pi * 62 * np.arange(n) / SR) + .35 * np.sin(2 * np.pi * 124 * np.arange(n) / SR)) * np.sin(np.pi * np.arange(n) / n) ** .5).astype(np.float32))(int(1.3 * SR)),
 'zumbido': (np.sin(2*np.pi*120*np.arange(int(1.05*SR))/SR)*.5+np.sin(2*np.pi*240*np.arange(int(1.05*SR))/SR)*.25).astype(np.float32),
 'chuva': pb(ruido(1.1, 3), .55) * .8,
 'gota': tom(1100, .12, .03) * .6,
 'crack': sum(np.pad(ruido(.05, .012) * rng.uniform(.5, 1), (int(rng.uniform(0, .6) * SR), SR)) [:int(.7 * SR)] for _ in range(26)),
 'desaba': pb(ruido(2.2, .8), .03) * 5 + sum(np.pad(pb(ruido(.12, .05), .2), (int(rng.uniform(0, 1.4) * SR), 3 * SR))[:int(2.2 * SR)] for _ in range(22)) * .7,
}
GANHO = {'chuva': .28, 'gota': .3, 'zumbido': .12, 'toc': .3, 'tijolo': .34, 'telha': .28, 'pop': .22, 'concreto': .22, 'furadeira': .3, 'motor': .1, 'crack': .5, 'desaba': .75, 'whoosh': .3, 'ding': .28, 'impact': .6, 'riser': .3}
vz = np.zeros(N, np.float32); fx = np.zeros(N, np.float32); amb = np.zeros(N, np.float32); mus = np.zeros(N, np.float32)
CONTINUOS = {'chuva', 'motor', 'zumbido', 'concreto', 'furadeira'}  # sons em repetição: abaixam quando a voz entra
for f in A['falas']:
    por(vz, ler(f['mp3']), f['t'])
for s in A['sons']:
    k = s['k']; x = FX[k] if k in FX else ler(sfx.sound(k, 0))
    por(amb if k in CONTINUOS else fx, x, s['t'], GANHO.get(k, .3))

# música: 104 bpm, progressão alegre em dó, dedilhado, baixo e bateria suave
bpm = 104; b = 60 / bpm; ACORDES = [[60, 64, 67, 72], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]
hz = lambda m: 440 * 2 ** ((m - 69) / 12)


def pluck(f, d=.6):
    t = np.arange(int(d * SR)) / SR
    return (np.sin(2 * np.pi * f * t) + .45 * np.sin(4 * np.pi * f * t) + .2 * np.sin(6 * np.pi * f * t)) * np.exp(-t / .22) * np.minimum(t / .003, 1)


kick = (np.sin(2 * np.pi * np.cumsum(np.linspace(120, 45, int(.16 * SR))) / SR) * np.exp(-np.arange(int(.16 * SR)) / SR / .07)).astype(np.float32)
hat = (np.diff(rng.standard_normal(int(.04 * SR) + 1)) * env(.04, r=.012)).astype(np.float32)
snare = so(pb(ruido(.14, .05), .5), tom(190, .1, .04) * .5)
PAD = [0, 2, 1, 3, 2, 1, 3, 2]; MEL = [12, 0, 7, 9, 12, 7, 4, 7, 9, 12, 14, 12, 7, 4, 2, 0]
t = 0.; c = 0
while t < T + 1:
    ac = ACORDES[c % 4]; sec = c // 8 % 3
    for i in range(8):
        tt = t + i * b / 2
        por(mus, pluck(hz(ac[PAD[i]])), tt, .3)
        if i % 2 == 0:
            por(mus, pluck(hz(ac[0] - 24), .8), tt, .55 if i % 4 == 0 else .35)
        por(mus, hat, tt, .09 if i % 2 else .14)
    por(mus, kick, t, .5); por(mus, kick, t + 2 * b, .45); por(mus, snare, t + b, .16); por(mus, snare, t + 3 * b, .16)
    if sec != 0:
        for i in range(4):
            por(mus, pluck(hz(ac[0] + 12 + MEL[(c * 4 + i) % 16] % 12)), t + i * b, .16)
    t += 4 * b; c += 1
mus /= np.abs(mus).max() + 1e-6
# abaixa a música sob a voz
def media(x, n):
    c = np.cumsum(np.insert(x.astype(np.float64), 0, 0)); o = np.zeros_like(x); m = (c[n:] - c[:-n]) / n; o[n // 2:n // 2 + len(m)] = m; return o


e = media(media(np.abs(vz), int(.05 * SR)) > .01, int(.25 * SR))
g = .11 - .07 * np.clip(e, 0, 1)
g[:int(.4 * SR)] *= np.linspace(0, 1, int(.4 * SR)); fim = int(T * SR); g[fim - SR:fim] *= np.linspace(1, 0, SR); g[fim:] = 0
vz /= np.abs(vz).max() + 1e-6
amb *= (1 - .8 * np.clip(e, 0, 1)) * .55
fx *= (1 - .6 * np.clip(e, 0, 1)) * .5
m = vz * .95 + fx + amb + mus * g
m = np.tanh(m * 1.05) * .94
wav = tmp / 'final.raw'; (m[:fim] * 32767).astype(np.int16).tofile(wav)
subprocess.run([FF, '-y', '-v', 'error', '-i', str(tmp / 'mudo.mp4'), '-f', 's16le', '-ar', str(SR), '-ac', '1', '-i', str(wav), '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-af', 'loudnorm=I=-18:TP=-2:LRA=6', '-ar', str(SR), '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-movflags', '+faststart', '-shortest', saida], check=True)
print('ok', saida, round(T, 1), 'pico', round(float(np.abs(m).max()), 2), 'efeitos', len(A['sons']))
