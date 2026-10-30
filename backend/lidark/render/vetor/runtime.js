// Motor vetorial: cada quadro é uma função pura de t (mesmo t = mesmo desenho).
// Define o global V (contrato em CONTRATO.md) e compõe cenário, adereços, elenco, fx, tela, HUD, legendas,
// carimbos, reações, transições e a tela de escolha final a partir do spec.
(function () {
  'use strict';
  const INK = '#14182a', TITLE = "Impact,'Arial Black',sans-serif", UI = "'Segoe UI',Arial,sans-serif";
  const W0 = 720, H0 = 1280;

  const V = window.V = {
    sets: {}, props: {}, screens: {}, chars: {},
    docs: { sets: {}, props: {}, screens: {}, chars: {} },
    anchors: {},          // V.anchors.<set> = {tv:{x,y,w}}: onde a TV do cenário fica (opcional)
    missing: [], errors: window.__erros || [], spec: null,
  };

  // ---------------------------------------------------------------- utilidades públicas
  V.rnd = s => { const x = Math.sin(s * 127.1 + 311.7) * 43758.5453; return x - Math.floor(x); };
  V.ease = x => x * x * (3 - 2 * x);
  V.cl = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  V.esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const { rnd, ease, cl, esc } = V;
  const f1 = x => +x.toFixed(1), f2 = x => +x.toFixed(3);
  const back = x => { const c = 1.9, u = x - 1; return 1 + (c + 1) * u * u * u + c * u * u; }; // passa do ponto e volta (pop)

  // largura real do texto (cacheada; a mesma fonte dá sempre a mesma medida)
  const _cv = document.createElement('canvas').getContext('2d'), _tw = {};
  V.tw = function (text, size, font) {
    const k = (font || TITLE) + '|' + text;
    if (_tw[k] == null) { _cv.font = '100px ' + (font || TITLE); _tw[k] = _cv.measureText(text).width / 100; }
    return _tw[k] * size;
  };

  function miss(kind, name) {
    const k = kind + ':' + name;
    if (!V.missing.includes(k)) V.missing.push(k);
  }
  function fail(kind, name, e) {
    const k = kind + ':' + name + ': ' + (e && e.message || e);
    if (!V.errors.includes(k)) V.errors.push(k);
  }
  // chama uma biblioteca sem nunca derrubar o quadro
  function lib(kind, name, ph, ...args) {
    const fn = V[kind][name];
    if (typeof fn !== 'function') { miss(kind, name); return ph; }
    try { return fn(...args) || ''; } catch (e) { fail(kind, name, e); return ph; }
  }

  const phSet = (t, n) => `<rect width="${W0}" height="${H0}" fill="#bcd7ea"/><rect y="880" width="${W0}" height="400" fill="#8c9db0"/>` +
    `<path d="M0 880H${W0}" stroke="${INK}" stroke-width="6"/><text x="360" y="420" font-size="30" fill="#5d7388" text-anchor="middle">${esc(n)}</text>`;
  const phProp = n => `<rect x="-46" y="-46" width="92" height="92" rx="14" fill="#ffd23f" stroke="${INK}" stroke-width="6"/>` +
    `<text y="16" font-size="46" fill="${INK}" text-anchor="middle">?</text>`;
  const phChar = n => `<ellipse cy="10" rx="110" ry="16" fill="#000" opacity=".25"/><rect x="-80" y="-300" width="160" height="300" rx="50" fill="#aeb8c6" stroke="${INK}" stroke-width="7"/>` +
    `<circle cy="-420" r="120" fill="#efe3c8" stroke="${INK}" stroke-width="7"/>`;
  const phScreen = n => `<rect width="${W0}" height="${H0}" fill="#223"/><text x="360" y="640" font-size="44" fill="#fff" text-anchor="middle">${esc(n)}</text>`;

  // ---------------------------------------------------------------- spec
  V.load = function (spec) {
    V.spec = spec;
    spec.shots = (spec.shots || []).slice().sort((a, b) => a.t0 - b.t0);
    spec.fps = spec.fps || 30;
    V.W = spec.W || W0; V.H = spec.H || H0;
    const host = document.getElementById('stage');
    host.innerHTML = '';
    V._capY = {};
    return true;
  };

  function shotAt(t) {
    const S = V.spec.shots;
    let i = S.length - 1;
    while (i > 0 && t < S[i].t0) i--;
    return i;
  }

  // envelope da voz (quadro a quadro) vira a boca de quem fala; sem envelope, simula sílabas
  V.talkAt = function (who, t) {
    const sp = V.spec, L = sp.lines || [];
    for (const l of L) {
      if (l.speaker === who && t >= l.start && t < l.start + (l.dur || (l.end - l.start))) {
        const env = sp._env;
        if (env && env.length) return cl(env[Math.min(env.length - 1, Math.round(t * sp.fps))] || 0);
        return .25 + .6 * Math.abs(Math.sin(t * 13)) * (.6 + .4 * Math.sin(t * 7.3));
      }
    }
    return 0;
  };

  // ---------------------------------------------------------------- câmera
  const TRANS = { cut: .13, whip: .3, flash: .26, iris: .5, glitch: .24, slide: .34 };

  function camAt(sh, t) {
    const c = sh.cam || {}, a = Object.assign({ x: 360, y: 640, z: 1 }, c.from || c.to || {}), b = Object.assign({}, a, c.to || {});
    const p = ease(cl((t - sh.t0) / Math.max(.01, sh.t1 - sh.t0)));
    let z = a.z + (b.z - a.z) * p, x = a.x + (b.x - a.x) * p, y = a.y + (b.y - a.y) * p;
    // deriva mínima: a imagem nunca fica congelada
    z *= 1 + .004 * Math.sin(t * .9);
    const tr = sh.transition || 'cut';
    if (tr === 'cut' && sh.t0 > 0) z *= 1 + .06 * (1 - ease(cl((t - sh.t0) / TRANS.cut)));
    const sk = +c.shake || 0;
    const mg = sk ? 1 + sk * 1.6 / 360 : 1;
    z = Math.max(1, z) * mg;
    const hw = 360 / z, hh = 640 / z;
    // cenários vão além do quadro (x -300..1020, y -300..1700): o limite só impede ver o fim do desenho
    x = cl(x, hw - 280, W0 - hw + 280); y = cl(y, hh - 280, H0 - hh + 400);
    let sx = 0, sy = 0;
    // sacudida curta: some em 0,4 s (tremer o plano inteiro cansa)
    const dk = sk * Math.max(0, 1 - (t - sh.t0) / .4);
    if (dk) { sx = dk * (Math.sin(t * 61) + .5 * Math.sin(t * 37 + 1)); sy = dk * (Math.cos(t * 53) + .5 * Math.sin(t * 29 + 2)); }
    return { x, y, z, sx, sy };
  }
  const camT = c => `translate(${f1(360 - c.x * c.z + c.sx)} ${f1(640 - c.y * c.z + c.sy)}) scale(${f2(c.z)})`;

  // onde o personagem está no quadro t (trata a entrada pela lateral)
  function castPos(c, sh, t) {
    const out = { x: c.x == null ? 360 : c.x, y: c.y == null ? 1090 : c.y, pose: c.pose || 'stand', flip: !!c.flip };
    if (c.move) {  // quem anda atravessa o cenário: posição ligada ao tempo do plano
      const p = cl((t - sh.t0) / Math.max(.01, sh.t1 - sh.t0));
      out.x = c.move[0] + (c.move[1] - c.move[0]) * p;
      out.flip = c.move[1] < c.move[0];
      return out;
    }
    if (c.enter === 'left' || c.enter === 'right') {
      const p = cl((t - sh.t0) / (c.pose === 'run' ? .5 : .75));
      if (p < 1) {
        const from = c.enter === 'left' ? -260 : 980;
        out.x = from + (out.x - from) * (1 - (1 - p) * (1 - p));
        out.flip = c.enter === 'right';
        if (out.pose !== 'run') out.pose = 'walk';
      }
    }
    return out;
  }

  // ---------------------------------------------------------------- fx
  const FX = {
    sparks(t, o) {
      const ox = o.x == null ? 560 : o.x, oy = o.y == null ? 430 : o.y; let s = '';
      for (let b = 0; b < 2; b++) {
        const per = 1.3 + b * .4, cy = (t + b * .55) / per, id = Math.floor(cy), f = cy - id;
        if (f > .55) continue;
        const p = f / .55;
        for (let i = 0; i < 16; i++) {
          const r = id * 13 + i * 3 + b, a = rnd(r) * Math.PI * 2, v = 80 + rnd(r + 1) * 240;
          const x = ox + Math.cos(a) * v * p, y = oy + Math.sin(a) * v * p * .7 + 420 * p * p;
          const dx = Math.cos(a) * 14, dy = (Math.sin(a) * 10 + 22 * p);
          s += `<path d="M${f1(x)} ${f1(y)}l${f1(dx)} ${f1(dy)}" stroke="${i % 3 ? '#ffd23f' : '#ff8a2a'}" stroke-width="${f1(7 * (1 - p) + 2)}" stroke-linecap="round"/>`;
        }
        s += `<circle cx="${ox}" cy="${oy}" r="${f1(46 * (1 - p))}" fill="#fff6b0" opacity="${f2(.9 * (1 - p))}"/>`;
      }
      return s;
    },
    smoke(t, o) {
      const ox = o.x == null ? 360 : o.x, oy = o.y == null ? 900 : o.y; let s = '';
      for (let i = 0; i < 22; i++) {
        const f = (t * .16 + rnd(i)) % 1, x = ox + (rnd(i + 40) - .5) * 520 + Math.sin(t + i) * 26 + f * 50, y = oy - f * 760, r = 40 + f * 120;
        s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(r)}" fill="${i % 2 ? '#8c93a3' : '#b3b9c6'}" opacity="${f2(.25 * Math.sin(f * Math.PI))}"/>`;
      }
      return s;
    },
    steam(t, o) {
      const ox = o.x == null ? 610 : o.x, oy = o.y == null ? 520 : o.y, dir = o.dir || -1; let s = '';
      for (let i = 0; i < 34; i++) {
        const f = (t * 1.7 + i * .071) % 1, sp = (rnd(i) - .5) * .7, d = f * 300;
        const x = ox + dir * d * (.8 + sp * .4), y = oy - d * (.5 + sp) - f * f * 60;
        s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(4 + f * 26)}" fill="#e9f7ff" opacity="${f2((1 - f) * .85)}"/>`;
      }
      return s;
    },
    floaters(t, o) {
      let s = '';
      for (let i = 0; i < 26; i++) {
        const sp = 8 + rnd(i) * 18, x = ((rnd(i + 3) * 820 + t * sp * (i % 2 ? 1 : -1)) % 820 + 820) % 820 - 50;
        const y = rnd(i + 9) * 1050 + 110 + Math.sin(t * .6 + i) * 34, r = (t * (20 + rnd(i) * 40) + i * 40) % 360, k = i % 5;
        const c = ['#ffd23f', '#dfe7f1', '#7fd4ff', '#ff8a5c', '#b9f0c8'][k];
        const sh = k === 0 ? `<path d="M-14 0h28M-5-9v18" stroke="${INK}" stroke-width="3"/><circle r="7" fill="${c}" stroke="${INK}" stroke-width="3"/>`
          : k === 1 ? `<rect x="-11" y="-6" width="22" height="12" rx="3" fill="${c}" stroke="${INK}" stroke-width="3"/>`
            : k === 2 ? `<path d="M0-11q11 13 0 20-11-7 0-20z" fill="${c}" stroke="${INK}" stroke-width="3"/>`
              : k === 3 ? `<circle r="6" fill="${c}" stroke="${INK}" stroke-width="3"/>`
                : `<path d="M-9-9l18 6-14 12z" fill="${c}" stroke="${INK}" stroke-width="3" stroke-linejoin="round"/>`;
        s += `<g transform="translate(${f1(x)} ${f1(y)}) rotate(${f1(r)})">${sh}</g>`;
      }
      return s;
    },
    rain(t, o) {
      let s = '<g stroke="#bfe6ff" stroke-width="4" stroke-linecap="round" opacity=".75">';
      for (let i = 0; i < 70; i++) {
        const f = (t * (1.5 + rnd(i) * .7) + rnd(i + 5)) % 1, x = rnd(i + 11) * 900 - 40 - f * 150, y = f * 1400 - 80;
        s += `<path d="M${f1(x)} ${f1(y)}l-14 44"/>`;
      }
      s += '</g><g fill="none" stroke="#dff2ff" stroke-width="3">';
      for (let i = 0; i < 14; i++) {
        const f = (t * 2 + rnd(i + 70)) % 1, x = rnd(i + 80) * 720, y = 1020 + rnd(i + 90) * 230;
        s += `<ellipse cx="${f1(x)}" cy="${f1(y)}" rx="${f1(4 + f * 26)}" ry="${f1(2 + f * 8)}" opacity="${f2(1 - f)}"/>`;
      }
      return s + '</g>';
    },
    dust(t, o) {
      let s = '';
      for (let i = 0; i < 40; i++) {
        const f = (t * (.05 + rnd(i) * .08) + rnd(i + 2)) % 1, x = rnd(i + 21) * 760 + Math.sin(t * .8 + i) * 22, y = f * 1200 + 40;
        s += `<circle cx="${f1(x)}" cy="${f1(y)}" r="${f1(2 + rnd(i + 31) * 6)}" fill="#f6e6c0" opacity="${f2(.65 * Math.sin(f * Math.PI))}"/>`;
      }
      return s;
    },
  };

  // alarme é o único fx em tela (não acompanha a câmera)
  function alarmOverlay(t, tod) {
    const k = .5 + .5 * Math.sin(t * 6.3), a = t * 1.9, x = 360 + Math.cos(a) * 980, y = 110 + Math.sin(a) * 980;
    // sem lavar o quadro de vermelho: o peso fica nas bordas e no feixe giratório
    // cenário em tod "alert" já pulsa vermelho sozinho: aqui fica só a borda
    if (tod === 'alert') return `<rect width="${W0}" height="${H0}" fill="url(#vgRed)" opacity="${f2(.4 + k * .4)}"/>`;
    return `<rect width="${W0}" height="${H0}" fill="#ff2a2a" opacity="${f2(.02 + k * .06)}"/>` +
      `<path d="M360 110L${f1(x - 240)} ${f1(y + 240)}L${f1(x + 240)} ${f1(y - 240)}z" fill="#ff5a3a" opacity="${f2(.06 + k * .06)}"/>` +
      `<rect width="${W0}" height="${H0}" fill="url(#vgRed)" opacity="${f2(.5 + k * .4)}"/>`;
  }

  // ---------------------------------------------------------------- reações em cima da cabeça
  function reaction(kind, p, s) {
    const i = `stroke="${INK}" stroke-width="7" stroke-linejoin="round" stroke-linecap="round"`;
    if (kind === 'sweat') return [0, 1, 2].map(k => {
      const f = (s * 1.5 + k * .33) % 1;
      return `<path transform="translate(${44 - k * 40} ${f1(f * 90 - 20 + k * 8)})" d="M0-26q22 30 0 44-22-14 0-44z" fill="#7fd4ff" ${i} opacity="${f2(1 - f * .7)}"/>`;
    }).join('');
    if (kind === 'question') return `<text font-size="150" y="50" text-anchor="middle" fill="#ffd23f" stroke="${INK}" stroke-width="13">?</text>`;
    if (kind === 'exclaim') return `<text font-size="170" y="60" text-anchor="middle" fill="#ff5a4d" stroke="${INK}" stroke-width="13">!</text>`;
    if (kind === 'heart') return `<path d="M0 46C-70-4-46-62-14-52 0-46 0-34 0-30 0-34 0-46 14-52 46-62 70-4 0 46z" fill="#ff5a7a" ${i}/>`;
    if (kind === 'anger') return `<g fill="none" stroke="#ff3b30" stroke-width="15" stroke-linecap="round"><path d="M-50-16Q-16-16-14-50M50-16Q16-16 14-50M-50 16Q-16 16-14 50M50 16Q16 16 14 50"/></g>`;
    if (kind === 'bulb') {
      const r = 60 + 6 * Math.sin(s * 14);
      return `<g stroke="#ffd23f" stroke-width="9" stroke-linecap="round">${[0, 1, 2, 3, 4].map(k => `<path transform="rotate(${-80 + k * 40})" d="M0 ${f1(-r - 12)}v-22"/>`).join('')}</g>` +
        `<circle cy="-6" r="46" fill="#ffe680" ${i}/><path d="M-20 38h40v22q-20 12-40 0z" fill="#c8cfd8" ${i}/><path d="M-13 6l13-14 13 14" fill="none" stroke="#c98a00" stroke-width="5"/>`;
    }
    if (kind === 'zzz') return [0, 1, 2].map(k => {
      const f = (s * .6 + k * .33) % 1;
      return `<text x="${f1(f * 60 + k * 6)}" y="${f1(30 - f * 110)}" font-size="${f1(44 + f * 44)}" fill="#fff" stroke="${INK}" stroke-width="9" opacity="${f2(Math.sin(f * Math.PI))}">Z</text>`;
    }).join('');
    return '';
  }

  // ---------------------------------------------------------------- uma tomada (mundo + tela)
  function screenStart(i) {
    // telas iguais em tomadas seguidas continuam de onde estavam
    const S = V.spec.shots, sc = S[i].screen;
    if (sc.t0 != null) return sc.t0;
    let k = i;
    while (k > 0 && S[k - 1].screen && S[k - 1].screen.type === sc.type && (S[k - 1].screen.device || '') === (sc.device || '') &&
      JSON.stringify(S[k - 1].screen.data) === JSON.stringify(sc.data)) k--;
    return S[k].t0;
  }

  // a tela anima a boca/ondas com a voz de quem não está em cena (locutor, ligação)
  function screenTalk(sh, t) {
    const sp = V.spec, inCast = c => (sh.cast || []).some(x => x.char === c);
    for (const l of sp.lines || []) {
      if (t >= l.start && t < l.start + (l.dur || (l.end - l.start)) && !inCast(l.speaker)) return V.talkAt(l.speaker, t);
    }
    return 0;
  }

  function screenContent(i, t, sc) {
    const dev = sc.device || 'fullscreen';
    return lib('screens', sc.type, phScreen(sc.type), Math.max(0, t - screenStart(i)), sc.data || {}, { device: dev, talk: screenTalk(V.spec.shots[i], t) });
  }

  // tv_on_set: a tela vem sem moldura com canto em (0,0) e tamanho em V.screenInfo; encaixa na TV do cenário
  function tvOnSet(i, t, sh, sc) {
    const a = V.anchors[sh.set] && V.anchors[sh.set].tv || {}, x = sc.x != null ? sc.x : a.x != null ? a.x : 360,
      y = sc.y != null ? sc.y : a.y != null ? a.y : 400, info = (V.screenInfo && V.screenInfo[sc.type]) || { w: W0, h: H0 };
    const w = sc.w || a.w || 440, h = sc.h || a.h || Math.round(w * info.h / info.w), k = Math.min(w / info.w, h / info.h), cid = `tvc${i}`;
    const fw = info.w * k, fh = info.h * k, bezel = a.bezel === false ? '' :
      `<rect x="${f1(-fw / 2 - 16)}" y="${f1(-fh / 2 - 16)}" width="${f1(fw + 32)}" height="${f1(fh + 32)}" rx="18" fill="#23293a" stroke="${INK}" stroke-width="7"/>` +
      `<circle cx="${f1(fw / 2 + 2)}" cy="${f1(fh / 2 + 8)}" r="4" fill="#39d98a"/>`;
    return `<g transform="translate(${x} ${y})">${bezel}<clipPath id="${cid}"><rect x="${f1(-fw / 2)}" y="${f1(-fh / 2)}" width="${f1(fw)}" height="${f1(fh)}" rx="6"/></clipPath>` +
      `<g clip-path="url(#${cid})"><g transform="translate(${f1(-fw / 2)} ${f1(-fh / 2)}) scale(${f2(k)})">${screenContent(i, t, sc)}</g></g></g>`;
  }

  function shotLayer(i, t) {
    const sh = V.spec.shots[i], sc = sh.screen, cam = camAt(sh, t), dev = sc && (sc.device || 'fullscreen');
    if (dev === 'fullscreen') return `<g transform="${camT(cam)}">${screenContent(i, t, sc)}</g>`;
    let w = lib('sets', sh.set, phSet(t, sh.set), t, { tod: sh.tod || 'day', state: sh.set_state || {} });
    const props = sh.props || [];
    const pr = p => `<g transform="translate(${p.x || 0} ${p.y || 0}) scale(${(p.scale || 1) * (p.flip ? -1 : 1)} ${p.scale || 1})${p.rot ? ` rotate(${p.rot})` : ''}">` +
      lib('props', p.id, phProp(p.id), t, { state: p.state || {}, label: p.label }) + '</g>';
    for (const p of props) if (!p.front) w += pr(p);
    if (dev === 'tv_on_set') w += tvOnSet(i, t, sh, sc);
    const cast = (sh.cast || []).slice().sort((a, b) => (a.y || 0) - (b.y || 0));
    for (const c of cast) {
      const q = castPos(c, sh, t), s = c.scale || 1;
      const o = { pose: q.pose, expr: c.expr || 'neutral', talk: V.talkAt(c.char, t), hold: c.hold, state: c.state || {}, flip: q.flip };
      w += `<g transform="translate(${f1(q.x)} ${f1(q.y)}) scale(${s})">${lib('chars', c.char, phChar(c.char), t, o)}</g>`;
    }
    for (const p of props) if (p.front) w += pr(p);
    let over = '';
    for (const e of sh.fx || []) {
      const k = typeof e === 'string' ? e : e.kind, o = typeof e === 'string' ? {} : e;
      if (k === 'alarm') over += alarmOverlay(t, sh.tod);
      else if (FX[k]) { try { w += FX[k](t, o); } catch (x) { fail('fx', k, x); } } else miss('fx', k);
    }
    // reações moram no mundo: acompanham o zoom
    for (const r of V.spec.reactions || []) {
      if (t < r.t0 || t >= r.t1) continue;
      const c = (sh.cast || []).find(x => x.char === r.char);
      if (!c) continue;
      const q = castPos(c, sh, t), s = c.scale || 1, h = headOf(c, q, t);
      const pop = back(cl((t - r.t0) / .16)), fade = cl((r.t1 - t) / .12);
      const dx = (q.flip ? -1 : 1) * h.r * .95 * s, xx = cl(h.x + dx, 90, 630), yy = Math.max(170, h.y - h.r * .92 * s);
      w += `<g transform="translate(${f1(xx)} ${f1(yy)}) scale(${f2(pop * Math.max(.6, Math.min(1.1, s)))})" opacity="${f2(fade)}">${reaction(r.kind, 0, t - r.t0)}</g>`;
    }
    let s = `<g transform="${camT(cam)}">${w}</g>` + over;
    if (dev === 'hand') s += screenContent(i, t, sc); // a própria tela desenha a mão e escurece o mundo
    return s;
  }

  function headOf(c, q, t) {
    const s = c.scale || 1;
    let h = { x: 0, y: -470, r: 132 };
    try { if (V.charHead) h = V.charHead(c.char, { pose: q.pose }, t) || h; } catch (e) { fail('chars', c.char, e); }
    return { x: q.x + (q.flip ? -1 : 1) * h.x * s, y: q.y + h.y * s, r: h.r };
  }

  // ---------------------------------------------------------------- legenda: fora do rosto em close
  function capY(i) {
    if (V._capY[i] != null) return V._capY[i];
    const sh = V.spec.shots[i], sc = sh.screen, dev = sc && (sc.device || 'fullscreen');
    let y = 960;
    if (dev === 'fullscreen' || dev === 'hand') y = 1080;
    else {
      const faces = [];
      for (const k of [0, 1]) {
        const t = k ? sh.t1 - .01 : sh.t0 + .3, cam = camAt(sh, t);
        for (const c of sh.cast || []) {
          const q = castPos(c, sh, t), h = headOf(c, q, t), s = c.scale || 1;
          faces.push({ y: 640 + (h.y - cam.y) * cam.z, r: h.r * s * cam.z, x: 360 + (h.x - cam.x) * cam.z });
        }
      }
      const vis = faces.filter(f => f.x > -f.r * .6 && f.x < W0 + f.r * .6);
      const gap = Y => Math.min(...vis.map(f => Math.abs(f.y - Y) - f.r * .78), 1e4);
      let best = 960, bv = -1e9;
      for (const Y of [960, 1060, 860, 760, 300, 420]) {
        const g = gap(Y);
        if (g >= 62) { best = Y; bv = 1e9; break; }
        if (g > bv) { bv = g; best = Y; }
      }
      y = best;
    }
    return (V._capY[i] = y);
  }

  function captions(t, i, endOn) {
    const list = V.spec.captions || [];
    let s = '';
    for (const c of list) {
      if (t < c.t0 || t >= c.t1) continue;
      const y = endOn ? 1160 : capY(i), txt = String(c.text || '').toUpperCase(), col = c.color || '#fff';
      let lines = [txt], size = endOn ? 60 : 88;
      if (V.tw(txt, size) > 640 && txt.includes(' ')) {
        const w = txt.split(' ');
        let cut = 1, b = 1e9;
        for (let k = 1; k < w.length; k++) {
          const d = Math.abs(V.tw(w.slice(0, k).join(' '), size) - V.tw(w.slice(k).join(' '), size));
          if (d < b) { b = d; cut = k; }
        }
        lines = [w.slice(0, cut).join(' '), w.slice(cut).join(' ')];
      }
      const mx = Math.max(...lines.map(l => V.tw(l, size)));
      if (mx > 640) size *= 640 / mx;
      const q = 1 + .24 * (1 - ease(cl((t - c.t0) / .1))), lh = size * 1.06, y0 = y - (lines.length - 1) * lh / 2 + size * .36;
      s += `<g transform="translate(360 ${y}) scale(${f2(q)}) translate(-360 ${-y})" font-size="${f1(size)}" text-anchor="middle" fill="${esc(col)}" stroke="#0b0d14" stroke-width="${f1(size * .19)}">` +
        lines.map((l, k) => `<text x="360" y="${f1(y0 + k * lh)}">${esc(l)}</text>`).join('') + '</g>';
    }
    return s;
  }

  // ---------------------------------------------------------------- carimbos
  const STAMP = { yellow: ['#ffd23f', INK], red: ['#ff5a4d', '#fff'], green: ['#39d98a', INK] };
  function stamps(t) {
    let s = '';
    (V.spec.stamps || []).forEach((c, n) => {
      if (t < c.t0 || t >= c.t1) return;
      const st = STAMP[c.style] || STAMP.yellow, txt = String(c.text || '').toUpperCase();
      let fs = 50, w = V.tw(txt, fs) + 56;
      if (w > 660) { fs *= 660 / w; w = 660; }
      const x = cl(c.x == null ? 360 : c.x, w / 2 + 16, W0 - w / 2 - 16), y = c.y == null ? 300 : c.y, a = (rnd(n + 3) - .5) * 11;
      const p = cl((t - c.t0) / .13), q = 1 + .7 * (1 - ease(p)), o = Math.min(cl(p * 3), cl((c.t1 - t) / .1));
      const j = p < 1 ? Math.sin(t * 90) * 4 * (1 - p) : 0;
      s += `<g transform="translate(${f1(x + j)} ${y}) rotate(${f1(a)}) scale(${f2(q)})" opacity="${f2(o)}">` +
        `<rect x="${f1(-w / 2 + 6)}" y="-38" width="${f1(w)}" height="96" rx="14" fill="#000" opacity=".3"/>` +
        `<rect x="${f1(-w / 2)}" y="-46" width="${f1(w)}" height="92" rx="14" fill="${st[0]}" stroke="${INK}" stroke-width="7"/>` +
        `<rect x="${f1(-w / 2 + 9)}" y="-37" width="${f1(w - 18)}" height="74" rx="8" fill="none" stroke="${st[1]}" stroke-width="3" opacity=".55"/>` +
        `<text y="${f1(fs * .36)}" font-size="${f1(fs)}" text-anchor="middle" fill="${st[1]}" stroke="none">${esc(txt)}</text></g>`;
    });
    return s;
  }

  // ---------------------------------------------------------------- HUD
  function meterVal(m, t) {
    const k = m.keys || [[0, 100]];
    if (t <= k[0][0]) return k[0][1];
    for (let i = 1; i < k.length; i++) {
      if (t < k[i][0]) { const a = k[i - 1], b = k[i]; return a[1] + (b[1] - a[1]) * (t - a[0]) / (b[0] - a[0]); }
    }
    return k[k.length - 1][1];
  }

  function hud(t) {
    const h = V.spec.hud;
    if (!h || h.show === false) return '';
    let s = '', x = 20;
    const ctr = h.counters || [], ms = h.meters || [], box = 'fill="#10131d" opacity=".93"';
    const lab = (a, X, Y, sz, fill, anc) => `<text x="${X}" y="${Y}" font-size="${sz}" fill="${fill}"${anc ? ` text-anchor="${anc}"` : ''} letter-spacing="2" stroke="none">${esc(a)}</text>`;
    for (const c of ctr) {
      const label = String(c.label || ''), w = Math.max(150, V.tw(label, 19) + 40 + label.length * 2);
      s += `<rect x="${x}" y="24" width="${f1(w)}" height="84" rx="14" ${box}/>` + lab(label, x + w / 2, 54, 19, '#cfd6e4', 'middle') +
        `<text x="${f1(x + w / 2)}" y="97" font-size="38" fill="#ffd23f" text-anchor="middle" stroke="none">${esc(c.value)}</text>`;
      x += w + 12;
    }
    if (ms.length) {
      const n = Math.min(ms.length, 3), rowH = 84 / n, W = 700 - x;
      s += `<rect x="${f1(x)}" y="24" width="${f1(W)}" height="${84}" rx="14" ${box}/>`;
      ms.slice(0, 3).forEach((m, k) => {
        const v = cl(meterVal(m, t), 0, 100), low = m.lowAt != null && v < m.lowAt, col = low ? (m.low || '#ff5a4d') : (m.color || '#39d98a');
        const pulse = low ? .55 + .45 * Math.sin(t * 9) : 1, y = 24 + k * rowH;
        if (n === 1) {
          const bw = W - 134;
          s += lab(m.label, x + 22, 56, 20, '#cfd6e4') + `<rect x="${f1(x + 22)}" y="68" width="${f1(bw)}" height="22" rx="11" fill="#2a3040"/>` +
            `<rect x="${f1(x + 22)}" y="68" width="${f1(Math.max(22, bw * v / 100))}" height="22" rx="11" fill="${col}" opacity="${f2(pulse)}"/>` +
            `<rect x="${f1(x + 30)}" y="72" width="${f1(Math.max(6, bw * v / 100 - 18))}" height="5" rx="2.5" fill="#fff" opacity=".35"/>` +
            `<text x="${f1(x + W - 18)}" y="92" font-size="38" fill="${col}" text-anchor="end" stroke="none">${Math.round(v)}%</text>`;
        } else {
          const by = y + rowH / 2 - 7, lw = 112, bw = W - lw - 88;
          s += lab(m.label, x + 16, f1(by + 13), 15, '#cfd6e4') + `<rect x="${f1(x + lw + 10)}" y="${f1(by)}" width="${f1(bw)}" height="14" rx="7" fill="#2a3040"/>` +
            `<rect x="${f1(x + lw + 10)}" y="${f1(by)}" width="${f1(Math.max(14, bw * v / 100))}" height="14" rx="7" fill="${col}" opacity="${f2(pulse)}"/>` +
            `<text x="${f1(x + W - 14)}" y="${f1(by + 17)}" font-size="24" fill="${col}" text-anchor="end" stroke="none">${Math.round(v)}%</text>`;
        }
      });
    }
    return s + inventory(t, h);
  }

  function itemArt(t, it) { return lib('props', it.item, phProp(it.item), t, { state: {}, label: it.label }); }

  // mochila no canto: o item surge grande, segura um instante e voa para dentro dela
  function inventory(t, h) {
    const inv = (h.inventory || []).slice().sort((a, b) => a.t - b.t);
    if (!inv.length || t < inv[0].t) return '';
    const BX = 56, BY = 170, LIFE = 1.3, FLY = .84;
    let land = 0, s = '', anim = '', bounce = 0, shown = 0;
    inv.forEach(it => {
      const d = t - it.t;
      if (d < 0) return;
      if (d >= LIFE) {
        const sx = 118 + shown * 78, q = back(cl((d - LIFE) / .2));
        s += `<g transform="translate(${sx} ${BY}) scale(${f2(q)})"><rect x="-35" y="-35" width="70" height="70" rx="14" fill="#10131d" opacity=".9"/>` +
          `<rect x="-35" y="-35" width="70" height="70" rx="14" fill="none" stroke="#ffd23f" stroke-width="4"/><g transform="scale(.52)">${itemArt(t, it)}</g></g>`;
        shown++;
      } else {
        const a = cl(d / .2), b = cl((d - FLY) / (LIFE - FLY)), e = b * b;
        const x = 360 + (BX - 360) * e, y = 340 + (BY - 340) * e - Math.sin(b * Math.PI) * 70;
        const q = (b > 0 ? 1.1 * (1 - e) + .3 : 1.1 * back(a)) * (it.big || 1) * (1 + (b ? 0 : .04 * Math.sin(t * 8)));
        const rays = b ? '' : `<g opacity="${f2(.9 * a)}">${[...Array(12)].map((_, k) => `<path transform="rotate(${f1(k * 30 + t * 40)})" d="M-16-96L0-170L16-96z" fill="#ffd23f" stroke="${INK}" stroke-width="5" stroke-linejoin="round"/>`).join('')}</g>` +
          `<circle r="88" fill="#fff6d0" stroke="${INK}" stroke-width="7"/>`;
        anim += `<g transform="translate(${f1(x)} ${f1(y)}) rotate(${f1(b * 200)}) scale(${f2(q)})">${rays}${itemArt(t, it)}</g>`;
        if (!b) {
          const txt = ('+1 ITEM: ' + (it.label || it.item)).toUpperCase(), w = Math.min(640, V.tw(txt, 46) + 56), fs = 46 * Math.min(1, 584 / V.tw(txt, 46)), r = back(cl((d - .1) / .18));
          anim += `<g transform="translate(360 548) rotate(-3) scale(${f2(r)})"><rect x="${f1(-w / 2)}" y="-44" width="${f1(w)}" height="88" rx="14" fill="#ffd23f" stroke="${INK}" stroke-width="7"/>` +
            `<text y="${f1(fs * .36)}" font-size="${f1(fs)}" text-anchor="middle" fill="${INK}" stroke="none">${esc(txt)}</text></g>`;
        }
        if (d > LIFE - .34) bounce = Math.max(bounce, 1 - (d - (LIFE - .34)) / .34);
      }
      if (d >= LIFE && d < LIFE + .3) land = Math.max(land, 1 - (d - LIFE) / .3);
    });
    const sq = 1 + .22 * Math.sin((bounce + land) * Math.PI) * (bounce + land > 0 ? 1 : 0);
    s = `<g transform="translate(${BX} ${BY}) scale(${f2(sq)} ${f2(2 - sq)})">` +
      `<path d="M-20-32q0-14 20-14t20 14" fill="none" stroke="${INK}" stroke-width="7"/><rect x="-34" y="-34" width="68" height="72" rx="20" fill="#2a2d38" stroke="#ffd23f" stroke-width="5"/>` +
      `<rect x="-22" y="4" width="44" height="26" rx="8" fill="#3b4050" stroke="#ffd23f" stroke-width="3"/><path d="M-30-10H30" stroke="#ffd23f" stroke-width="3"/></g>` + s;
    return s + anim;
  }

  // ---------------------------------------------------------------- escolha final: comente uma palavra, A x B
  function choiceStart() {
    const e = V.spec.end, c = e && e.choice;
    if (!c) return null;
    const d = +V.spec.duration || 0;
    return c.t0 != null ? c.t0 : e.t0 != null ? e.t0 : Math.max(0, d - 4);
  }

  function card(t, s, y, c, col, dark, side, delay) {
    const p = cl((s - delay) / .3), e = 1 - (1 - p) * (1 - p) * (1 - p), x = (1 - e) * side * 800, word = String(c.word || '').toUpperCase();
    const fs = Math.min(128, 128 * 560 / Math.max(1, V.tw(word, 128)));
    const b = 1 + .022 * Math.sin((s - delay) * 5 + side);
    const hint = esc(c.hint || '');
    return `<g transform="translate(${f1(360 + x)} ${y}) rotate(${side * -1.6}) scale(${f2(b)})">` +
      `<rect x="-322" y="-146" width="656" height="304" rx="32" fill="#000" opacity=".3"/>` +
      `<rect x="-330" y="-152" width="660" height="304" rx="32" fill="${col}" stroke="${INK}" stroke-width="8"/>` +
      `<rect x="-314" y="-136" width="628" height="60" rx="18" fill="#fff" opacity=".22"/>` +
      `<text y="${hint ? 16 : 46}" font-size="${f1(fs)}" text-anchor="middle" fill="#fff" stroke="${INK}" stroke-width="${f1(fs * .13)}">${esc(word)}</text>` +
      (hint ? `<text y="96" font-size="37" text-anchor="middle" fill="${dark}" stroke="none" style="font-family:${UI};font-weight:700">${hint}</text>` : '') + '</g>';
  }

  function choice(t) {
    const t0 = choiceStart();
    if (t0 == null || t < t0) return '';
    const c = V.spec.end.choice, s = t - t0, f = ease(cl(s / .25));
    let o = `<rect width="${W0}" height="${H0}" fill="#1a2744" opacity="${f2(.93 * f)}"/>`;
    // raios girando atrás de tudo
    o += `<g transform="translate(360 640) rotate(${f1(s * 14)})" opacity="${f2(.2 * f)}">` +
      [...Array(10)].map((_, k) => `<path transform="rotate(${k * 36})" d="M-50 0L-200-1100H200L50 0z" fill="#fff"/>`).join('') + '</g>';
    const title = String(c.title || 'COMENTE UMA PALAVRA').toUpperCase(), tp = back(cl((s - .08) / .24));
    const fs = Math.min(70, 70 * 620 / V.tw(title, 70)), tw = V.tw(title, fs) + 50;
    o += `<g transform="translate(360 196) rotate(-2) scale(${f2(tp)})"><rect x="${f1(-tw / 2)}" y="-56" width="${f1(tw)}" height="112" rx="18" fill="#ffd23f" stroke="${INK}" stroke-width="8"/>` +
      `<text y="${f1(fs * .36)}" font-size="${f1(fs)}" text-anchor="middle" fill="${INK}" stroke="none">${esc(title)}</text></g>`;
    o += card(t, s, 430, c.a || {}, '#2f8fe8', '#eaf5ff', -1, .2) + card(t, s, 820, c.b || {}, '#ee5340', '#fff0ec', 1, .34);
    // selo X entre as cartas
    const vp = back(cl((s - .55) / .22)) * 1.05, vb = 1 + .06 * Math.sin(s * 8);
    o += `<g transform="translate(360 625) rotate(${f1(-8 + 3 * Math.sin(s * 3))}) scale(${f2(vp * vb)})">` +
      `<path d="M0-76L20-34 66-58 50-12 94 0 50 12 66 58 20 34 0 76-20 34-66 58-50 12-94 0-50-12-66-58-20-34z" fill="#ffd23f" stroke="${INK}" stroke-width="7" stroke-linejoin="round"/>` +
      `<text y="28" font-size="76" text-anchor="middle" fill="${INK}" stroke="#fff" stroke-width="5">X</text></g>`;
    // barra de comentário digitando as duas palavras, uma de cada vez
    const bp = ease(cl((s - .7) / .25));
    if (bp > 0) {
      const a = String((c.a || {}).word || '').toUpperCase(), b = String((c.b || {}).word || '').toUpperCase(), per = 2.2, n = Math.floor(Math.max(0, s - .9) / per);
      const w = n % 2 ? b : a, ph = (Math.max(0, s - .9) % per) / per, nch = Math.min(w.length, Math.floor(ph * 2.6 * w.length));
      const typed = esc(w.slice(0, ph > .85 ? Math.max(0, Math.ceil(w.length * (1 - ph) / .15)) : nch)), caret = Math.floor(s * 3) % 2 ? '|' : ' ';
      o += `<g transform="translate(360 ${f1(1050 + (1 - bp) * 80)})" opacity="${f2(bp)}"><rect x="-320" y="-46" width="640" height="92" rx="46" fill="#fff" stroke="${INK}" stroke-width="7"/>` +
        `<circle cx="-270" r="30" fill="#efe3c8" stroke="${INK}" stroke-width="5"/><circle cx="-280" cy="-4" r="4" fill="${INK}"/><circle cx="-260" cy="-4" r="4" fill="${INK}"/>` +
        `<text x="-224" y="15" font-size="42" fill="${INK}" stroke="none" xml:space="preserve">${typed}${caret}</text>` +
        `<g transform="translate(274 0)"><circle r="30" fill="#2f8fe8" stroke="${INK}" stroke-width="5"/><path d="M-10-14L16 0-10 14l4-14z" fill="#fff"/></g></g>`;
    }
    return o;
  }

  // ---------------------------------------------------------------- transições
  function compose(t) {
    const S = V.spec.shots, i = shotAt(t), sh = S[i], tr = sh.transition || 'cut', d = TRANS[tr] || .13, p = (t - sh.t0) / d;
    const blur = (s, id) => `<filter id="${id}" x="-20%" y="0" width="140%" height="100%"><feGaussianBlur stdDeviation="${f1(s)} 0"/></filter>`;
    const prev = i > 0 ? i - 1 : -1;
    if (prev >= 0 && p < 1) {
      if (tr === 'whip') {
        const e = ease(p), sb = Math.sin(p * Math.PI) * 46;
        return `<defs>${blur(sb, 'wb')}</defs><g filter="url(#wb)"><g transform="translate(${f1(-e * W0)} 0)">${shotLayer(prev, t)}</g><g transform="translate(${f1((1 - e) * W0)} 0)">${shotLayer(i, t)}</g></g>`;
      }
      if (tr === 'slide') {
        const e = 1 - (1 - p) * (1 - p) * (1 - p);
        return `<g transform="translate(${f1(-e * W0 * .3)} 0)">${shotLayer(prev, t)}</g><rect width="${W0}" height="${H0}" fill="#000" opacity="${f2(.35 * e)}"/>` +
          `<g transform="translate(${f1((1 - e) * W0)} 0)"><rect x="-10" y="0" width="10" height="${H0}" fill="${INK}"/>${shotLayer(i, t)}</g>`;
      }
      if (tr === 'glitch') {
        const st = Math.floor(t * 30);
        let s = `<g id="glL">${shotLayer(p < .45 ? prev : i, t)}</g>`;
        for (let k = 0; k < 7; k++) {
          const y = rnd(st + k * 7) * H0, h = 24 + rnd(st + k * 3) * 120, off = (rnd(st + k) - .5) * 150, cid = 'gs' + k;
          s += `<clipPath id="${cid}"><rect y="${f1(y)}" width="${W0}" height="${f1(h)}"/></clipPath><g clip-path="url(#${cid})"><use href="#glL" x="${f1(off)}"/></g>`;
          s += `<rect x="0" y="${f1(y)}" width="${W0}" height="${f1(h)}" fill="${k % 2 ? '#ff2a6a' : '#2ae0ff'}" opacity=".24"/>`;
        }
        return s;
      }
    }
    let s = shotLayer(i, t);
    // íris fecha na tomada de saída e abre na de entrada
    const next = S[i + 1];
    const ir = (a) => {
      const R = 760 * a;
      return `<path fill-rule="evenodd" fill="#0b0d14" d="M-20-20H740V1300H-20zM${f1(360 - R)} 600a${f1(R)} ${f1(R)} 0 1 0 ${f1(2 * R)} 0a${f1(R)} ${f1(R)} 0 1 0 ${f1(-2 * R)} 0z"/>` +
        (R > 1 ? `<circle cx="360" cy="600" r="${f1(R)}" fill="none" stroke="#ffd23f" stroke-width="8"/>` : '');
    };
    if (tr === 'iris' && prev >= 0 && t - sh.t0 < d / 2) s += ir(ease((t - sh.t0) / (d / 2)));
    if (next && (next.transition === 'iris') && next.t0 - t < TRANS.iris / 2) s += ir(ease((next.t0 - t) / (TRANS.iris / 2)));
    if (tr === 'flash' && prev >= 0 && p < 1) s += `<rect width="${W0}" height="${H0}" fill="#fff" opacity="${f2(1 - ease(p))}"/>`;
    if (next && next.transition === 'flash' && next.t0 - t < .06) s += `<rect width="${W0}" height="${H0}" fill="#fff" opacity="${f2(1 - (next.t0 - t) / .06)}"/>`;
    return s;
  }

  // ---------------------------------------------------------------- quadro completo
  V.render = function (t) {
    if (!V.spec) return;
    const i = shotAt(t), t0 = choiceStart(), endOn = t0 != null && t >= t0;
    // aparelho em tela cheia tem a própria moldura: o HUD sai, salvo pedido explícito (shot.hud:true)
    const sh = V.spec.shots[i] || {}, full = sh.screen && (sh.screen.device || 'fullscreen') === 'fullscreen';
    const hideHud = sh.hud === false || (full && sh.hud !== true);
    const body = compose(t) + (hideHud ? '' : hud(t)) + stamps(t) + choice(t) + captions(t, i, endOn);
    document.getElementById('stage').innerHTML =
      `<svg xmlns="http://www.w3.org/2000/svg" width="${V.W}" height="${V.H}" viewBox="0 0 ${W0} ${H0}">` +
      `<defs><radialGradient id="vgRed"><stop offset=".55" stop-color="#ff2a2a" stop-opacity="0"/><stop offset="1" stop-color="#d0101a" stop-opacity=".85"/></radialGradient></defs>` +
      body + '</svg>';
  };
  window.render = t => V.render(t);
})();
