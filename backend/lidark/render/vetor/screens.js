/* screens.js — telas do motor vetorial (celular, TV, monitores, cartões). Dono: agente TELAS.
 *
 * Uso: V.screens.nome(t, d, o) -> string SVG. t = segundos desde que a tela abriu; d = dados; o.device:
 *   "fullscreen"  aparelho grande com cenário próprio (opaco, cobre os 720x1280).
 *   "hand"        mão do Zé segurando o aparelho, com o mundo escurecido atrás (fundo transparente).
 *   "tv_on_set"   só o conteúdo da tela, sem moldura, com canto em (0,0). O tamanho vem de
 *                 V.screenInfo[nome] = {kind, w, h}; o motor escala e encaixa na TV do cenário.
 * Extras: o.talk (0..1) anima boca/ondas com a voz. V.screenTimeline(nome, d) -> [{t, kind:"key|tap|pop|alert|shutter"}]
 * lista os instantes de tecla, toque e alerta para o motor marcar o som no ritmo certo.
 * Tudo é função pura do tempo: nada de Math.random()/Date. Dados que faltam caem no exemplo de V.docs.screens.
 * Texto longo sempre quebra linha (ou encolhe/corta com reticências) medindo a fonte de verdade.
 */
(function () {
  'use strict';
  const V = (window.V = window.V || {});
  V.screens = V.screens || {};
  V.docs = V.docs || {};
  V.docs.screens = V.docs.screens || {};
  V.screenInfo = V.screenInfo || {};

  // ---------- utilidades básicas ----------
  const INK = '#14182a';
  const UI = "'Segoe UI', Arial, sans-serif";
  const TT = "Impact, 'Arial Black', sans-serif";
  const SKIN = '#efe3c8', SLEEVE = '#6b6a3a', CAP = '#24412c';
  const cl = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const ease = x => { x = cl(x); return x * x * (3 - 2 * x); };
  const rnd = s => (V.rnd ? V.rnd(s) : (() => { const v = Math.sin(s * 127.1 + 311.7) * 43758.5453; return v - Math.floor(v); })());
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const n = x => Math.round(x * 100) / 100;
  const str = (x, f = '') => (x == null ? f : String(x));
  const arr = x => (Array.isArray(x) ? x : []);
  const num = (x, f) => (typeof x === 'number' && isFinite(x) ? x : (x != null && isFinite(+x) ? +x : f));
  const spr = x => (x <= 0 ? 0 : 1 - Math.exp(-8 * x) * Math.cos(12 * x)); // mola com passada
  const fade = (t, t0, d = 0.22) => ease((t - t0) / d);
  const blink = (t, hz = 2) => Math.sin(t * hz * 6.2832) > 0;
  const pulse = (t, hz = 1) => 0.5 + 0.5 * Math.sin(t * hz * 6.2832);
  const pad2 = v => String(Math.floor(v)).padStart(2, '0');
  const clock = s => { s = Math.max(0, s); return pad2(s / 60) + ':' + pad2(s % 60); };
  const money = v => 'R$ ' + (v < 0 ? '-' : '') + Math.abs(v).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const lerp = (a, b, k) => a + (b - a) * k;

  // contexto da chamada atual: ids únicos estáveis e gravação da linha do tempo de som
  let cur = { name: 'x', n: 0, rec: null, o: {} };
  const uid = () => 'sc_' + cur.name + '_' + (cur.n++);
  const evt = (t, kind) => { if (cur.rec) cur.rec.push({ t: n(t), kind }); };
  const talk = (t, hz = 7) => { const v = cur.o && cur.o.talk; return v != null ? cl(+v || 0) : cl(0.5 + 0.5 * Math.sin(t * hz) * Math.sin(t * hz * 0.37 + 1)); };

  // ---------- primitivas SVG ----------
  const S = (w = 5, c = INK) => `stroke="${c}" stroke-width="${w}"`;
  const R = (x, y, w, h, r, f, e = '') => `<rect x="${n(x)}" y="${n(y)}" width="${n(Math.max(0, w))}" height="${n(Math.max(0, h))}" rx="${n(r)}" fill="${f}" ${e}/>`;
  const C = (x, y, r, f, e = '') => `<circle cx="${n(x)}" cy="${n(y)}" r="${n(Math.max(0, r))}" fill="${f}" ${e}/>`;
  const E = (x, y, a, b, f, e = '') => `<ellipse cx="${n(x)}" cy="${n(y)}" rx="${n(a)}" ry="${n(Math.max(0, b))}" fill="${f}" ${e}/>`;
  const P = (d, f = 'none', e = '') => `<path d="${d}" fill="${f}" ${e}/>`;
  const L = (x1, y1, x2, y2, c = INK, w = 4, e = '') => `<line x1="${n(x1)}" y1="${n(y1)}" x2="${n(x2)}" y2="${n(y2)}" stroke="${c}" stroke-width="${w}" stroke-linecap="round" ${e}/>`;
  const G = (x, y, s, b, e = '') => `<g transform="translate(${n(x)} ${n(y)})${s !== 1 ? ` scale(${n(s * 1000) / 1000})` : ''}" ${e}>${b}</g>`;
  const Rot = (a, x, y, b) => `<g transform="rotate(${n(a)} ${n(x)} ${n(y)})">${b}</g>`;
  const Op = (a, b) => (a <= 0 ? '' : `<g opacity="${n(cl(a))}">${b}</g>`);
  // anima entrada em mola em torno de (x,y)
  const Pop = (t, t0, x, y, b) => { if (t < t0) return ''; const k = spr(t - t0); return `<g opacity="${n(cl((t - t0) / 0.1))}" transform="translate(${n(x)} ${n(y)}) scale(${n(k)}) translate(${n(-x)} ${n(-y)})">${b}</g>`; };
  const Slide = (t, t0, dx, dy, b) => { if (t < t0) return ''; const k = 1 - spr(t - t0); return `<g opacity="${n(cl((t - t0) / 0.1))}" transform="translate(${n(dx * k)} ${n(dy * k)})">${b}</g>`; };
  const Clip = (shape, b) => { const id = uid(); return `<clipPath id="${id}">${shape}</clipPath><g clip-path="url(#${id})">${b}</g>`; };
  const Grad = (c1, c2, dir = 'v') => { const id = uid(); return { id, def: `<linearGradient id="${id}" x1="0" y1="0" x2="${dir === 'd' ? 1 : 0}" y2="1"><stop offset="0" stop-color="${c1}"/><stop offset="1" stop-color="${c2}"/></linearGradient>`, url: `url(#${id})` }; };
  const GR = (x, y, w, h, r, c1, c2, e = '', dir = 'v') => { const g = Grad(c1, c2, dir); return `<defs>${g.def}</defs>` + R(x, y, w, h, r, g.url, e); };

  // ---------- texto medido ----------
  let mctx = null; const mcache = new Map();
  function measure(s, size, bold, title) {
    const key = (title ? 'T' : bold ? 'B' : 'N') + s;
    let v = mcache.get(key);
    if (v == null) {
      try {
        if (!mctx) mctx = document.createElement('canvas').getContext('2d');
        mctx.font = `${title ? '400' : bold ? '700' : '400'} 100px ${title ? TT : UI}`;
        v = mctx.measureText(s).width;
      } catch (e) { v = s.length * (title ? 48 : bold ? 58 : 54); }
      if (mcache.size > 6000) mcache.clear();
      mcache.set(key, v);
    }
    return (v * size) / 100;
  }
  const isB = o => (o.w || 400) >= 600;
  function T(x, y, s, o = {}) {
    const title = o.f === 'title';
    const st = `font-family:${title ? TT : UI};font-weight:${title ? 400 : o.w || 400};font-size:${n(o.size || 20)}px;fill:${o.fill || INK};text-anchor:${o.a || 'start'};` +
      `letter-spacing:${o.ls || 0}px;stroke:${o.st || 'none'};stroke-width:${o.sw || 0}px;paint-order:stroke;stroke-linejoin:round`;
    return `<text x="${n(x)}" y="${n(y)}" style="${st}"${o.op != null ? ` opacity="${n(o.op)}"` : ''}${o.e ? ' ' + o.e : ''}>${esc(s)}</text>`;
  }
  function wrap(text, size, maxW, o = {}) {
    const out = [], m = s => measure(s, size, isB(o), o.f === 'title') + (o.ls || 0) * s.length;
    for (const para of str(text).split('\n')) {
      let line = '';
      for (let w of para.split(/\s+/).filter(Boolean)) {
        while (m(w) > maxW && w.length > 1) { // palavra enorme: parte na marra
          if (line) { out.push(line); line = ''; }
          let k = w.length - 1; while (k > 1 && m(w.slice(0, k)) > maxW) k--;
          out.push(w.slice(0, k)); w = w.slice(k);
        }
        const tr = line ? line + ' ' + w : w;
        if (m(tr) <= maxW) line = tr; else { out.push(line); line = w; }
      }
      out.push(line);
    }
    return out;
  }
  function clampLines(lines, max, size, maxW, o) {
    if (!max || lines.length <= max) return lines;
    const c = lines.slice(0, max); let l = c[max - 1] + '…';
    while (l.length > 2 && measure(l, size, isB(o), o.f === 'title') > maxW) l = l.slice(0, -2) + '…';
    c[max - 1] = l; return c;
  }
  // parágrafo: y = linha de base da primeira linha
  function para(x, y, text, o = {}) {
    const size = o.size || 20, lh = o.lh || size * 1.28, maxW = o.maxW || 300;
    const lines = clampLines(wrap(text, size, maxW, o), o.max, size, maxW, o);
    return lines.map((l, i) => T(x, y + i * lh, l, o)).join('');
  }
  const paraH = (text, o) => { const s = o.size || 20; return clampLines(wrap(text, s, o.maxW || 300, o), o.max, s, o.maxW || 300, o).length * (o.lh || s * 1.28); };
  // parágrafo que encolhe até caber na caixa (maxW x maxH), para títulos enormes
  function fitPara(x, y, text, o) {
    let size = o.size; const min = o.min || 14;
    while (size > min) {
      const lh = (o.lhk || 1.12) * size;
      if (wrap(text, size, o.maxW, o).length * lh <= o.maxH) break;
      size -= 2;
    }
    return { svg: para(x, y + (size - o.size) * 0.8, text, { ...o, size, lh: (o.lhk || 1.12) * size, max: Math.max(1, Math.floor(o.maxH / ((o.lhk || 1.12) * size))) }), size };
  }
  // uma linha só: encolhe e, se preciso, corta
  function fit1(x, y, s, o = {}) {
    s = str(s); let size = o.size || 20; const min = o.min || Math.max(11, size * 0.6), maxW = o.maxW || 300;
    const m = z => measure(s, z, isB(o), o.f === 'title') + (o.ls || 0) * s.length;
    while (size > min && m(size) > maxW) size -= 1;
    if (m(size) > maxW) { const ms = x => measure(x, size, isB(o), o.f === 'title') + (o.ls || 0) * x.length; while (s.length > 2 && ms(s + '…') > maxW) s = s.slice(0, -1); s += '…'; }
    return T(x, y, s, { ...o, size });
  }

  // ---------- digitação ----------
  const ttCache = new Map();
  function typeTimes(s, cps, seed) {
    const k = s + '|' + cps + '|' + seed; let v = ttCache.get(k);
    if (!v) {
      v = []; let a = 0; const ch = [...s];
      ch.forEach((c, i) => { let dt = (0.6 + 0.9 * rnd(seed + i * 7.31)) / cps; if (c === ' ') dt *= 1.3; if (',.!?:'.includes(c)) dt *= 2.4; a += dt; v.push(a); });
      if (ttCache.size > 800) ttCache.clear();
      ttCache.set(k, v);
    }
    return v;
  }
  function typed(t, s, t0, cps = 13, seed = 1, kind = 'key') {
    s = str(s); const ts = typeTimes(s, cps, seed); let c = 0;
    while (c < ts.length && t0 + ts[c] <= t) c++;
    if (cur.rec && kind !== 'none') ts.forEach(x => evt(t0 + x, kind));
    const ch = [...s];
    return { s: ch.slice(0, c).join(''), n: c, done: c >= ts.length, end: t0 + (ts.length ? ts[ts.length - 1] : 0), last: c > 0 ? ch[c - 1] : '', sinceKey: c > 0 ? t - (t0 + ts[c - 1]) : 9 };
  }
  const caret = (x, y, h, t, c = INK) => (blink(t, 1.6) ? R(x, y, 3, h, 1, c) : '');

  // ---------- ícones (24x24, linha) ----------
  const GL = {
    chat: 'M3 5h18v12H9l-5 4v-4H3z', phone: 'M6 3l4 1 1 5-2 2c1 2 2 3 4 4l2-2 5 1 1 4-3 3C10 20 4 14 3 6z', camera: 'M3 7h5l2-3h4l2 3h5v13H3zM12 10a3.5 3.5 0 1 0 .01 0',
    map: 'M3 5l6-2 6 2 6-2v16l-6 2-6-2-6 2zM9 3v16M15 5v16', bank: 'M3 9l9-6 9 6zM5 10v8M10 10v8M14 10v8M19 10v8M3 20h18', news: 'M3 4h15v16H5a2 2 0 0 1-2-2zM18 9h3v9a2 2 0 0 1-3 2M6 8h9M6 12h9M6 16h6',
    mail: 'M3 5h18v14H3zM3 6l9 7 9-7', music: 'M9 18V5l11-2v13M9 18a3 3 0 1 1-.01 0M20 16a3 3 0 1 1-.01 0', clock: 'M12 3a9 9 0 1 0 .01 0M12 7v5l4 3', gear: 'M12 8a4 4 0 1 0 .01 0M12 2v4M12 18v4M2 12h4M18 12h4M5 5l3 3M16 16l3 3M5 19l3-3M16 8l3-3',
    search: 'M10 3a7 7 0 1 0 .01 0M15 15l6 6', cart: 'M2 4h3l3 11h11l2-8H6M9 20a1 1 0 1 0 .01 0M18 20a1 1 0 1 0 .01 0', heart: 'M12 20C4 14 2 10 3 7c1-3 6-4 9 0 3-4 8-3 9 0 1 3-1 7-9 13z', cloud: 'M7 18a4 4 0 0 1 0-8 6 6 0 0 1 11 1 4 4 0 0 1 0 7z',
    moto: 'M5 18a3 3 0 1 0 .01 0M19 18a3 3 0 1 0 .01 0M6 16l5-5h5l3 6M14 7h3l1 4', game: 'M7 8h10a4 4 0 0 1 4 4l1 5a2 2 0 0 1-4 1l-2-3H8l-2 3a2 2 0 0 1-4-1l1-5a4 4 0 0 1 4-4zM8 11v3M6.5 12.5h3M16 12h.01M18 14h.01', photo: 'M3 4h18v16H3zM3 16l5-5 4 4 3-3 6 6M15 8a1.5 1.5 0 1 0 .01 0',
    note: 'M5 3h14v18H5zM8 8h8M8 12h8M8 16h5', video: 'M3 6h13v12H3zM16 10l5-3v10l-5-3z', mic: 'M9 4a3 3 0 0 1 6 0v7a3 3 0 0 1-6 0zM5 11a7 7 0 0 0 14 0M12 18v3', back: 'M15 4l-8 8 8 8', share: 'M4 12v8h16v-8M12 15V3M7 8l5-5 5 5', bolt: 'M13 2L4 14h7l-1 8 10-13h-7z',
    speaker: 'M3 9h4l6-5v16l-6-5H3zM16 8a5 5 0 0 1 0 8M19 5a9 9 0 0 1 0 14', keypad: 'M6 5h.01M12 5h.01M18 5h.01M6 11h.01M12 11h.01M18 11h.01M6 17h.01M12 17h.01M18 17h.01', plus: 'M12 4v16M4 12h16', check: 'M4 13l5 5L20 6', x: 'M5 5l14 14M19 5L5 19', up: 'M12 20V5M5 12l7-7 7 7', star: 'M12 3l3 6 6 1-4 5 1 6-6-3-6 3 1-6-4-5 6-1z', comment: 'M3 4h18v13H10l-5 4v-4H3z', pin: 'M12 22s-7-8-7-13a7 7 0 0 1 14 0c0 5-7 13-7 13zM12 6a3 3 0 1 0 .01 0',
    play: 'M7 4l13 8-13 8z', pause: 'M7 4v16M17 4v16', lock: 'M6 10h12v11H6zM8 10V7a4 4 0 0 1 8 0v3', flash: 'M13 2L4 14h7l-1 8 10-13h-7z', hang: 'M2 14c6-6 14-6 20 0l-3 4-4-2v-3a10 10 0 0 0-6 0v3l-4 2z', wifi: 'M2 9a15 15 0 0 1 20 0M6 13a9 9 0 0 1 12 0M10 17a3 3 0 0 1 4 0',
  };
  const gl = (k, x, y, s, c = '#fff', w = 2.2, fill = 'none') => `<g transform="translate(${n(x - s / 2)} ${n(y - s / 2)}) scale(${n(s / 24)})"><path d="${GL[k] || GL.star}" fill="${fill}" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"/></g>`;

  // ---------- gente vetorial ----------
  // busto com ombros; (x,y) = centro da cabeça; r da cabeça = 60*s
  function bust(x, y, s, t, o = {}) {
    const skin = o.skin || '#e8b98f', shirt = o.shirt || '#2f6fd0', hair = o.hair || '#3a2a1e', st = 'stroke="' + INK + '" stroke-width="6" stroke-linejoin="round"';
    const lv = o.talk != null ? o.talk : 0, bl = (t * 0.31 + (o.seed || 0)) % 1 < 0.02;
    let b = '';
    if (o.style === 'long') b += P('M-68 -10C-80 -90 80 -90 68 -10L78 90H-78z', hair, st);
    b += P('M-120 190C-120 110 -70 84 -28 78H28C70 84 120 110 120 190z', shirt, st);
    if (o.tie) b += P('M-12 84L0 96 12 84 8 150 0 164-8 150z', o.tie, st) + P('M-30 78L0 104 30 78 44 120-2 100-44 120z', '#fff', st);
    b += R(-24, 44, 48, 44, 16, skin, st);
    b += C(0, 0, 60, skin, st);
    if (o.style === 'cap') b += P('M-60 -10A60 60 0 0 1 60 -10Q0 -34 -60 -10z', o.capc || CAP, st) + P('M28 -22q36 -2 54 12-32 4-58 0z', '#1a3122', st);
    else if (o.style === 'bun') b += C(0, -74, 22, hair, st) + P('M-60 -6C-60 -76 60 -76 60 -6 30 -30 -30 -30 -60 -6z', hair, st);
    else if (o.style === 'bald') b += P('M-60 0q-8 -14 0 -22M60 0q8 -14 0 -22', hair, 'stroke="' + INK + '" stroke-width="6"');
    else if (o.style === 'long') b += P('M-60 0C-60 -70 60 -70 60 0 34 -34 -20 -36 -60 0z', hair, st);
    else b += P('M-60 -2C-66 -74 66 -74 60 -2 44 -30 20 -34 0 -32-24 -34-44 -26-60 -2z', hair, st);
    b += bl ? P('M-34 2h20M14 2h20', 'none', 'stroke="' + INK + '" stroke-width="6" stroke-linecap="round"') : C(-24, 4, 7, INK) + C(24, 4, 7, INK);
    if (o.brows !== false) b += P(o.worried ? 'M-38 -16l24 -8M14 -24l24 8' : 'M-36 -18h22M14 -18h22', 'none', 'stroke="' + INK + '" stroke-width="5" stroke-linecap="round"');
    if (o.glasses) b += R(-40, -10, 32, 26, 8, '#ffffff33', st) + R(8, -10, 32, 26, 8, '#ffffff33', st) + L(-8, 2, 8, 2);
    if (o.beard) b += P('M-48 18c10 44 86 44 96 0-22 10-74 10-96 0z', hair, st);
    b += lv > 0.08 ? E(0, 32, 14 + 4 * lv, 3 + 12 * lv, '#7a2a2a', st) : P('M-14 30q14 8 28 0', 'none', 'stroke="' + INK + '" stroke-width="5" stroke-linecap="round"');
    b += C(-42, 22, 10, '#e88', 'opacity=".45"') + C(42, 22, 10, '#e88', 'opacity=".45"');
    return G(x, y, s, b);
  }
  const zeBust = (x, y, s, t, o = {}) => bust(x, y, s, t, { skin: SKIN, shirt: SLEEVE, style: 'cap', brows: true, ...o });

  // ---------- miniaturas de "foto" ----------
  function photo(kind, x, y, w, h, t = 0, label = '') {
    const cx = x + w / 2, cy = y + h / 2, m = Math.min(w, h);
    let b = '';
    switch (kind) {
      case 'earth':
        b = R(x, y, w, h, 0, '#0c1436') + [...Array(26)].map((_, i) => C(x + rnd(i + 3) * w, y + rnd(i + 40) * h, 1 + rnd(i) * 1.4, '#fff')).join('') +
          C(cx + m * 0.2, cy + m * 0.5, m * 0.6, '#2a8fd8', S(4, '#6fd3ff')) + P(`M${n(cx - m * .1)} ${n(cy + m * .25)}q${n(m * .2)} ${n(-m * .15)} ${n(m * .4)} 0t${n(m * .1)} ${n(m * .3)}-${n(m * .4)} 0z`, '#46b36b', S(3, '#1f6e43')); break;
      case 'selfie':
        b = GR(x, y, w, h, 0, '#9fd8ff', '#e6f4ff') + R(x, y + h * .7, w, h * .3, 0, '#c8cfd8') + zeBust(cx, cy - m * .02, m / 280, t + 3, { talk: .1, worried: true }); break;
      case 'food':
        b = R(x, y, w, h, 0, '#ffd9a8') + E(cx, cy + m * .08, m * .4, m * .24, '#fff', S(5)) + E(cx, cy + m * .03, m * .3, m * .15, '#e67e22', S(4)) +
          C(cx - m * .1, cy, m * .05, '#d9483b', S(3)) + C(cx + m * .1, cy + m * .04, m * .05, '#46b36b', S(3)) + C(cx + m * .02, cy - m * .05, m * .05, '#ffd23f', S(3)); break;
      case 'mountain':
        b = GR(x, y, w, h, 0, '#7fd4ff', '#fdf1c9') + C(x + w * .75, y + h * .25, m * .1, '#ffd23f', S(4)) + P(`M${n(x)} ${n(y + h)}L${n(x + w * .32)} ${n(y + h * .35)}L${n(x + w * .55)} ${n(y + h * .75)}L${n(x + w * .72)} ${n(y + h * .5)}L${n(x + w)} ${n(y + h)}z`, '#46b36b', S(4)); break;
      case 'station':
        b = R(x, y, w, h, 0, '#3a82b4') + R(x, y + h * .65, w, h * .35, 0, '#55697f') + C(cx, cy - m * .12, m * .25, '#c9d6e2', S(5)) + C(cx, cy - m * .12, m * .18, '#0c1436', S(4)) + C(cx + m * .05, cy - m * .05, m * .1, '#2a8fd8') +
          R(x, y + h * .55, w, h * .09, 0, '#c8cfd8', S(4)) + R(x + w * .1, y + h * .7, w * .16, h * .22, 4, '#f0b429', S(4)) + R(x + w * .72, y + h * .74, w * .18, h * .18, 4, '#d9483b', S(4)); break;
      case 'cat':
        b = R(x, y, w, h, 0, '#ffe08a') + C(cx, cy + m * .08, m * .28, '#f39c3d', S(5)) + P(`M${n(cx - m * .26)} ${n(cy - m * .04)}l${n(m * .04)} ${n(-m * .22)} ${n(m * .16)} ${n(m * .1)}zM${n(cx + m * .26)} ${n(cy - m * .04)}l${n(-m * .04)} ${n(-m * .22)} ${n(-m * .16)} ${n(m * .1)}z`, '#f39c3d', S(5)) +
          C(cx - m * .1, cy + m * .05, m * .03, INK) + C(cx + m * .1, cy + m * .05, m * .03, INK) + P(`M${n(cx - m * .06)} ${n(cy + m * .17)}q${n(m * .06)} ${n(m * .06)} ${n(m * .12)} 0`, 'none', S(4)); break;
      case 'blur':
        b = GR(x, y, w, h, 0, '#b9c6d8', '#7f8ea6') + C(cx - m * .1, cy, m * .28, '#efe3c8', 'opacity=".55"') + R(x + w * .55, y + h * .3, w * .3, h * .5, 12, '#3d5a86', 'opacity=".4"'); break;
      case 'street':
        b = GR(x, y, w, h, 0, '#a9e2ff', '#fff6d6') + [0, 1, 2, 3].map(i => R(x + i * w * .25 + 4, y + h * (.2 + .1 * (i % 2)), w * .22, h * .6, 3, ['#f28fa0', '#ffd23f', '#7fd4a3', '#9db8ff'][i], S(3))).join('') + R(x, y + h * .78, w, h * .22, 0, '#8d99a8'); break;
      default: {
        b = GR(x, y, w, h, 0, '#ffd23f', '#ff7a59') + gl('photo', cx, cy - (label ? 12 : 0), m * .4, INK, 2.4);
        if (label) b += fit1(cx, cy + m * .3, label, { size: 18, w: 700, a: 'middle', maxW: w - 16 });
      }
    }
    return Clip(`<rect x="${n(x)}" y="${n(y)}" width="${n(w)}" height="${n(h)}"/>`, b);
  }

  // ---------- mãos ----------
  // mão segurando um objeto com caixa (0,0,w,h): back vai atrás do aparelho, front por cima dele
  function holdHand(w, h, sk = SKIN, sl = SLEEVE) {
    const s = S(6), cx = w / 2;
    const back = R(cx - 110, h + 90, 220, 900, 40, sl, s) + P(`M-30 ${n(h - 210)}C-44 ${n(h + 40)} ${n(cx - 150)} ${n(h + 190)} ${n(cx)} ${n(h + 190)}C${n(cx + 150)} ${n(h + 190)} ${n(w + 62)} ${n(h + 40)} ${n(w + 34)} ${n(h - 380)}z`, sk, s);
    let front = '';
    [0, 1, 2, 3].forEach(i => { front += Rot(-6 + i * 3, w + 8, h - 330 + i * 78, R(w - 14, h - 360 + i * 78, 70, 66, 30, sk, s) + P(`M${n(w + 34)} ${n(h - 346 + i * 78)}v38`, 'none', S(3, '#b9a98a'))); });
    front += Rot(30, -20, h - 60, R(-98, h - 240, 84, 230, 42, sk, s) + R(-86, h - 232, 56, 42, 16, '#fbf4e4', S(4)));
    return { back, front };
  }
  // dedo do Zé com a ponta em (0,0), vindo de baixo
  function finger(press = 0, sk = SKIN) {
    const s = S(6);
    return `<g transform="rotate(-12) scale(${n(1 - press * 0.06)})">` + P('M-44 40C-46 -32 46 -32 44 40L52 620H-52z', sk, s) +
      P('M-27 -6C-26 -22 26 -22 27 -6L25 30C10 38 -10 38 -25 30z', '#fbf4e4', S(4)) +
      P('M-30 120q30 12 60 0M-30 140q30 12 60 0M-32 260q32 12 64 0M-32 282q32 12 64 0', 'none', S(3, '#b9a98a')) + '</g>';
  }
  // dedo percorrendo toques [{t,x,y}]; devolve o desenho já na posição
  function tapper(t, taps) {
    taps = arr(taps).filter(a => a && a.t != null);
    if (!taps.length) return '';
    taps.forEach(a => evt(a.t, 'tap'));
    const first = taps[0], last = taps[taps.length - 1];
    if (t < first.t - 0.7 || t > last.t + 0.8) return '';
    let x = first.x + 40, y = 1050, press = 0, b = '';
    if (t < first.t - 0.12) { const k = ease((t - first.t + 0.7) / 0.58); x = lerp(first.x + 60, first.x, k); y = lerp(1050, first.y, k); }
    else if (t >= last.t + 0.12) { const k = ease((t - last.t - 0.12) / 0.6); x = lerp(last.x, last.x + 60, k); y = lerp(last.y, 1050, k); }
    else {
      let i = 0; while (i < taps.length - 1 && t > taps[i + 1].t - 0.12) i++;
      const a = taps[i], z = taps[Math.min(i + 1, taps.length - 1)];
      const k = z === a ? 0 : ease((t - a.t - 0.12) / Math.max(0.1, z.t - a.t - 0.24));
      x = lerp(a.x, z.x, k); y = lerp(a.y, z.y, k) - Math.sin(k * 3.14) * 22;
    }
    taps.forEach(a => {
      press = Math.max(press, 1 - Math.abs(t - a.t) / 0.12);
      if (t >= a.t && t < a.t + 0.4) { const r = (t - a.t) / 0.4; b += C(a.x, a.y, 16 + r * 46, 'none', `stroke="#fff" stroke-width="5" opacity="${n(1 - r)}"`); }
    });
    return b + G(x, y + 10, 1, finger(cl(press)));
  }
  function remoteHand(t) {
    const led = blink(t, 3) ? '#ff5a4d' : '#7a2a2a';
    return G(560, 1120 + Math.sin(t * 1.4) * 6, 1, Rot(-16, 0, 0,
      R(-70, 110, 150, 420, 40, SLEEVE, S(6)) + R(-38, -130, 92, 250, 18, '#2a3040', S(6)) + C(8, -116, 6, led, S(3)) + R(-18, -94, 52, 20, 6, '#d9483b', S(3)) +
      [0, 1, 2].map(r => [0, 1, 2].map(c => C(-8 + c * 22, -52 + r * 22, 7, '#c8cfd8', S(2))).join('')).join('') +
      R(-84, -10, 176, 150, 60, SKIN, S(6)) + [0, 1, 2].map(i => R(-92, 2 + i * 42, 120, 40, 20, SKIN, S(5))).join('')));
  }

  // ---------- teclado e barra de status ----------
  const KB_H = 262;
  function keyboard(w, y, hl, dark, t) {
    const rows = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM'], kw = (w - 12) / 10 - 5, kh = 46;
    const bg = dark ? '#1f2433' : '#d4d8e0', key = dark ? '#3a4152' : '#fff', tc = dark ? '#fff' : INK;
    let b = R(0, y, w, KB_H + 10, 0, bg), up = (hl || '').toUpperCase(), pop = '';
    rows.forEach((row, r) => {
      const x0 = (w - row.length * (kw + 5)) / 2 + 2.5;
      [...row].forEach((c, i) => {
        const x = x0 + i * (kw + 5), yy = y + 10 + r * (kh + 9), on = c === up;
        b += R(x, yy, kw, kh, 7, key) + T(x + kw / 2, yy + 31, c, { size: 21, a: 'middle', fill: tc });
        if (on) pop = R(x - 8, yy - 56, kw + 16, kh + 54, 12, key, S(3, '#0003')) + T(x + kw / 2, yy - 16, c, { size: 32, a: 'middle', w: 600, fill: tc });
      });
    });
    const yr = y + 10 + 3 * (kh + 9), sp = hl === ' ';
    b += R(8, yr - 55, 42, kh, 7, dark ? '#2a3040' : '#b4bac6') + gl('up', 29, yr - 32, 20, tc) + R(w - 50, yr - 55, 42, kh, 7, dark ? '#2a3040' : '#b4bac6') + gl('x', w - 29, yr - 32, 16, tc);
    b += R(8, yr, 84, kh, 7, dark ? '#2a3040' : '#b4bac6') + T(50, yr + 29, '123', { size: 18, a: 'middle', fill: tc });
    b += R(98, yr, w - 196, kh, 7, sp ? '#9db8ff' : key) + T(w / 2, yr + 29, 'espaço', { size: 17, a: 'middle', fill: dark ? '#aab' : '#667' });
    b += R(w - 92, yr, 84, kh, 7, '#2f7bf6') + T(w - 50, yr + 29, 'ir', { size: 18, a: 'middle', fill: '#fff', w: 600 });
    return b + pop;
  }
  function statusBar(w, d, dark, t, o = {}) {
    const c = dark ? '#fff' : INK, bat = cl(num(o.battery != null ? o.battery : d.battery, 62), 0, 100), low = bat <= 20;
    const sig = num(d.signal, 3);
    let b = fit1(34, 34, str(o.time || d.time, '21:42'), { size: 20, w: 700, fill: c, maxW: 104, min: 12 });
    b += R(w / 2 - 58, 12, 116, 32, 16, '#0b0d14') + C(w / 2 + 40, 28, 6, '#1f2a44');
    [0, 1, 2, 3].forEach(i => { b += R(w - 112 + i * 8, 32 - 5 - i * 4, 6, 7 + i * 4, 1.5, i < sig ? c : c + '44'); });
    b += gl('wifi', w - 62 - 8, 26, 18, c, 2.6);
    b += R(w - 56, 18, 36, 18, 5, 'none', S(2.4, c)) + R(w - 18, 23, 3, 8, 1, c) + R(w - 53, 21, 30 * bat / 100, 12, 2.5, low ? '#ff3b30' : c);
    return b;
  }
  const homeBar = (w, h, dark) => R(w / 2 - 68, h - 16, 136, 6, 3, dark ? '#fff' : INK);

  // ---------- cenas de fundo ----------
  function backdrop(t, c1, c2, opt = {}) {
    let b = GR(0, 0, 720, 1280, 0, c1, c2);
    let rays = '';
    for (let i = 0; i < 12; i++) { const a = i * 30 + t * 4; rays += `<path d="M0 0L1500 -130L1500 130z" fill="#fff" opacity=".045" transform="rotate(${n(a)})"/>`; }
    b += G(360, 620, 1, rays);
    for (let i = 0; i < 26; i++) {
      const sp = 14 + rnd(i + 7) * 30, y = (rnd(i + 80) * 1400 - t * sp) % 1400, yy = y < 0 ? y + 1400 : y;
      b += C(rnd(i + 50) * 720, yy - 60, 3 + rnd(i) * 9, opt.dot || '#ffffff', `opacity="${n(.1 + rnd(i + 3) * .22)}"`);
    }
    return b;
  }

  // sala com TV ou mesa com monitor, para o modo fullscreen
  function tvRoom(t, body, sw, sh) {
    const x = (720 - sw) / 2, y = 190;
    let b = GR(0, 0, 720, 1280, 0, '#ffd98a', '#f7b267');
    for (let i = 0; i < 8; i++) b += R(i * 100 - 10, 0, 44, 950, 0, '#ffffff', 'opacity=".12"');
    b += R(0, 950, 720, 330, 0, '#b5764a') + L(0, 950, 720, 950, INK, 7);
    for (let i = 0; i < 7; i++) b += L(-200 + i * 180, 950, -400 + i * 220, 1280, '#8d5934', 5);
    b += E(360, 1190, 300, 62, '#d9483b', S(6)) + E(360, 1190, 230, 40, '#f06a5a', S(4));
    // quadros, prateleira e planta
    b += R(44, 40, 118, 92, 6, '#fff4d6', S(6)) + P('M60 118l30-38 22 22 16-14 20 30z', '#46b36b', S(4)) + C(132, 66, 10, '#ffd23f', S(3));
    b += R(560, 30, 112, 124, 6, '#9db8ff', S(6)) + T(616, 104, 'LAR', { f: 'title', size: 34, a: 'middle', fill: '#fff', st: INK, sw: 5 });
    b += R(232, 120, 256, 16, 4, '#8d5934', S(5)) + R(262, 76, 30, 44, 3, '#d9483b', S(4)) + R(296, 66, 30, 54, 3, '#2f7bf6', S(4)) + R(330, 84, 26, 36, 3, '#46b36b', S(4)) + E(430, 106, 26, 14, '#fff', S(4));
    // rack
    const ry = y + sh + 70;
    b += R(40, ry, 640, 240, 18, '#8d5934', S(7)) + R(66, ry + 28, 280, 184, 10, '#6f4426', S(5)) + R(374, ry + 28, 280, 184, 10, '#6f4426', S(5)) + C(322, ry + 120, 8, '#ffd23f', S(3)) + C(398, ry + 120, 8, '#ffd23f', S(3));
    b += R(100, ry + 60, 150, 40, 8, '#2a3040', S(4)) + C(232, ry + 80, 5, blink(t, 1) ? '#39d98a' : '#14532d') + R(420, ry + 120, 190, 16, 4, '#ffd23f', S(4)) + R(430, ry + 104, 170, 16, 4, '#2f7bf6', S(4));
    b += R(20, ry - 66, 70, 66, 10, '#d9483b', S(6)) + Rot(Math.sin(t * 1.3) * 3, 55, ry - 66, P(`M55 ${ry - 66}c-30-40-44-70-40-110 20 20 30 50 40 80 0-40 10-80 26-110 10 40 0 80-14 110 14-24 30-40 52-50-6 34-30 60-64 80z`, '#46b36b', S(5)));
    // TV
    b += R(x - 24, y - 24, sw + 48, sh + 48, 26, '#2a3040', S(8)) + R(x - 10, y - 10, sw + 20, sh + 20, 12, '#14182a') + R(250, y + sh + 24, 220, 46, 8, '#2a3040', S(7));
    b += C(x + sw + 6, y + sh + 12, 4, '#39d98a');
    b += G(x, y, 1, body);
    return b;
  }
  function deskRoom(t, body, sw, sh) {
    const x = (720 - sw) / 2, y = 170;
    let b = GR(0, 0, 720, 1280, 0, '#8fd0e8', '#5aa9c9');
    for (let i = 0; i < 6; i++) b += R(i * 130 - 20, 0, 12, 900, 0, '#ffffff', 'opacity=".16"');
    b += R(-20, 58, 760, 40, 0, '#c8cfd8', S(6)) + R(-20, 68, 760, 8, 0, '#eef2f6') + R(90, 40, 30, 76, 6, '#8d99a8', S(5)) + R(600, 40, 30, 76, 6, '#8d99a8', S(5));
    b += R(250, 8, 220, 36, 8, '#ffd23f', S(5)) + T(360, 34, 'NÃO ENCOSTE', { f: 'title', size: 22, a: 'middle' });
    b += C(44, 150, 10, blink(t, 1.2) ? '#ff5a4d' : '#7a2a2a', S(4));
    const dy = y + sh + 120;
    b += R(310, y + sh + 26, 100, 100, 6, '#7b8ba0', S(7)) + R(220, y + sh + 110, 280, 26, 10, '#7b8ba0', S(7));
    b += R(-20, dy + 10, 760, 400, 0, '#c58a55', S(7)) + R(-20, dy + 10, 760, 22, 0, '#dcae78');
    b += R(170, dy + 56, 380, 100, 12, '#e6e9ef', S(6));
    for (let r = 0; r < 3; r++) for (let c = 0; c < 13; c++) b += R(184 + c * 27, dy + 66 + r * 27, 22, 22, 4, '#fff', S(2.5));
    b += R(46, dy + 40, 88, 104, 12, '#fff', S(6)) + P(`M134 ${dy + 66}q34 0 34 28-2 28-34 28`, 'none', S(6)) + T(90, dy + 100, 'CHEFE', { f: 'title', size: 20, a: 'middle', fill: '#d9483b' });
    b += P(`M78 ${dy + 26}q10-16 0-30`, 'none', `stroke="#fff" stroke-width="5" stroke-linecap="round" opacity="${n(.4 + .4 * pulse(t, .7))}"`);
    b += R(578, dy + 60, 92, 70, 40, '#d9dde4', S(6));
    b += R(x + 8, dy + 180, 170, 70, 6, '#ffd23f', S(5)) + T(x + 22, dy + 222, 'senha: 1234', { size: 22, w: 600 });
    b += R(x - 22, y - 22, sw + 44, sh + 44, 20, '#3a4152', S(8)) + R(x - 8, y - 8, sw + 16, sh + 16, 10, INK);
    b += C(360, y + sh + 12, 4, '#39d98a');
    b += R(x + sw + 2, y + 30, 20, 60, 4, '#ffd23f', S(3));
    b += G(x, y, 1, body);
    return b;
  }

  // ---------- palcos por tipo de aparelho ----------
  const SIZES = { phone: [390, 800], tv: [640, 500], monitor: [640, 500], tablet: [560, 760], radio: [420, 300], atm: [460, 360], card: [720, 1280], paper: [720, 1280], watch: [300, 340] };
  const dimBg = (a = 0.45) => R(0, 0, 720, 1280, 0, '#0b0d14', `opacity="${a}"`);
  const glass = (w, h, r) => P(`M0 ${n(h * .28)}L${n(w * .5)} 0H${n(w * .78)}L0 ${n(h * .46)}z`, '#fff', 'opacity=".06"');
  const scan = (w, h, t) => { let b = ''; for (let y = 0; y < h; y += 8) b += R(0, y, w, 2, 0, '#000', 'opacity=".05"'); const yy = (t * 90) % (h + 80) - 40; return b + R(0, yy, w, 40, 0, '#fff', 'opacity=".03"'); };

  function phoneStage(t, o, d, body, over) {
    const [w, h] = SIZES.phone, dev = o.device || 'fullscreen';
    const inner = Clip(`<rect width="${w}" height="${h}" rx="44"/>`, body);
    if (dev === 'tv_on_set') return inner;
    const fw = w + 28, fh = h + 28;
    const frame = R(0, 0, fw, fh, 62, '#1c2030', S(7)) + R(-6, 150, 7, 58, 3, '#2a3040', S(4)) + R(-6, 224, 7, 58, 3, '#2a3040', S(4)) + R(fw - 1, 190, 7, 90, 3, '#2a3040', S(4)) + R(5, 5, fw - 10, fh - 10, 57, 'none', S(2.5, '#566')) +
      G(14, 14, 1, inner + glass(w, h) + (over || ''));
    const k = spr(t);
    if (dev === 'hand') {
      const s = 1.06, hh = holdHand(fw, fh, d.skin || SKIN, d.sleeve || SLEEVE), bob = Math.sin(t * 1.6) * 5;
      return dimBg(0.5 * fade(t, 0, .25)) + `<g transform="translate(${n((720 - fw * s) / 2 + 6)} ${n(142 + bob + (1 - k) * 760)}) rotate(${n(-2.5 + (1 - k) * 8 + Math.sin(t * .9) * .5)} ${fw / 2} ${fh}) scale(${s})">` + hh.back + frame + hh.front + '</g>';
    }
    const s = 1.42, bob = Math.sin(t * 1.4) * 3;
    const bg = d.bg === 'none' ? '' : backdrop(t, d.bg || '#7a33e0', d.bg2 || '#2b1168');
    return bg + `<g transform="translate(${n((720 - fw * s) / 2)} ${n(34 + bob + (1 - k) * 640)}) rotate(${n((1 - k) * 6)} ${fw / 2} ${fh / 2}) scale(${s})">` + frame + '</g>';
  }
  // TV/monitor: dev define moldura
  function screenStage(kind, t, o, d, body) {
    const [w, h] = SIZES[kind], dev = o.device || 'fullscreen';
    // ligar: linha clara que abre na vertical
    const on = ease(t / 0.28), f = kind === 'tv' ? 0.97 + 0.03 * Math.sin(t * 37) : 1;
    const c = Clip(`<rect width="${w}" height="${h}" rx="8"/>`, `<g transform="translate(0 ${n(h / 2 * (1 - on))}) scale(1 ${n(Math.max(.01, on))})" opacity="${f}">${body}</g>` + scan(w, h, t) + glass(w, h)
      + Op(1 - fade(t, .05, .25), R(0, 0, w, h, 0, '#fff')));
    const scr = R(0, 0, w, h, 8, '#0b0d14') + c;
    if (dev === 'tv_on_set') return scr;
    const room = kind === 'tv' ? tvRoom(t, scr, w, h) : deskRoom(t, scr, w, h);
    if (dev === 'hand') return room + dimBg(0.08) + (kind === 'tv' ? remoteHand(t) : G(620, 1190 + Math.sin(t * 2) * 4, 1, R(-60, 40, 120, 240, 40, SLEEVE, S(6)) + R(-60, -50, 120, 120, 50, SKIN, S(6)) + R(-52, -86, 100, 70, 34, '#d9dde4', S(6))));
    return room;
  }

  // ---------- registro ----------
  function fallback(name) {
    return R(160, 520, 400, 240, 24, '#2a3040', S(6)) + T(360, 650, 'SEM SINAL', { f: 'title', size: 52, a: 'middle', fill: '#fff' });
  }
  function reg(name, kind, fn, desc, data) {
    const [w, h] = SIZES[kind];
    V.screenInfo[name] = { kind, w, h };
    V.docs.screens[name] = { desc, data };
    V.screens[name] = (t, d, o) => {
      const rec = cur.rec;
      cur = { name, n: 0, rec, o: o || {} };
      const dd = Object.assign({}, data, d || {}), oo = o || {};
      t = Math.max(0, +t || 0);
      try {
        const r = fn(t, dd, oo);
        if (kind === 'phone') return typeof r === 'string' ? phoneStage(t, oo, dd, r, '') : phoneStage(t, oo, dd, r.b, r.over);
        if (kind === 'tv' || kind === 'monitor') return screenStage(kind, t, oo, dd, r);
        return r;
      } catch (e) {
        (V.errors = V.errors || []).push(name + ': ' + e.message);
        return fallback(name);
      }
    };
  }
  // linha do tempo de sons: roda a tela lá no fim e colhe os eventos
  V.screenTimeline = (name, d, o) => {
    if (!V.screens[name]) return [];
    cur.rec = [];
    try { V.screens[name](9999, d, o); return cur.rec.slice().sort((a, b) => a.t - b.t); } finally { cur.rec = null; }
  };

  const PW = 390, PH = 800;
  const initials = s => str(s, '?').trim().charAt(0).toUpperCase();
  const avatar = (x, y, r, name, c = '#e0507a') => C(x, y, r, c, S(3)) + T(x, y + r * .36, initials(name), { size: r, w: 700, a: 'middle', fill: '#fff' });
  const appTile = (x, y, s, c, g) => R(x, y, s, s, s * .24, c, S(3)) + gl(g, x + s / 2, y + s / 2, s * .58, '#fff', 2.4);
  // cabeçalho padrão de app
  const appBar = (title, c, dark) => R(0, 0, PW, 112, 0, c) + fit1(PW / 2, 92, title, { size: 26, w: 700, a: 'middle', fill: dark ? '#fff' : INK, maxW: 300 });

  // ---------- CELULAR ----------
  reg('phone_lock', 'phone', (t, d) => {
    let b = GR(0, 0, PW, PH, 0, '#3b2fa8', '#ef6ea3');
    for (let i = 0; i < 24; i++) b += C(rnd(i + 2) * PW, rnd(i + 30) * 360, 1 + rnd(i) * 2, '#fff', `opacity="${n(.4 + .5 * pulse(t, .3 + rnd(i) * .6))}"`);
    b += C(320, 640, 150, '#ffb86b', S(5)) + P('M170 640q150 -60 300 0', 'none', S(5, '#e8813c')) + P('M-10 800L120 620 230 740 300 680 400 800z', '#2b1168', S(5));
    b += statusBar(PW, d, true, t);
    b += gl('lock', PW / 2, 84, 26, '#fff', 2.4);
    b += fit1(PW / 2, 138, str(d.date, 'terça, 12 de órbita'), { size: 22, a: 'middle', fill: '#fff', w: 600, maxW: 340 });
    b += fit1(PW / 2, 232, str(d.time, '21:42'), { size: 104, w: 300, a: 'middle', fill: '#fff', maxW: 350 });
    const ns = arr(d.notifs).slice(0, 7), cw = PW - 32;
    const info = ns.map((m, i) => ({ m, t0: num(m.t, .6 + i * .95), h: 58 + paraH(str(m.text), { size: 17, lh: 22, maxW: cw - 76, max: 3 }) }));
    let cards = '';
    info.forEach((c, i) => {
      evt(c.t0, 'alert');
      if (t < c.t0) return;
      let y = 262;
      for (let j = i + 1; j < info.length; j++) y += (info[j].h + 10) * ease((t - info[j].t0) / .3);
      const op = 1 - cl((y + c.h - 690) / 70);
      if (op <= 0) return;
      const m = c.m;
      cards = Op(op, Slide(t, c.t0, 0, -70, R(16, y, cw, c.h, 22, '#ffffffee', S(5)) + appTile(28, y + 12, 44, m.color || '#2f9e62', m.icon || 'chat') +
        fit1(84, y + 26, str(m.app, 'APP').toUpperCase(), { size: 14, w: 700, fill: '#556', maxW: 200 }) + T(PW - 30, y + 26, str(m.ago, 'agora'), { size: 14, a: 'end', fill: '#667' }) +
        fit1(84, y + 48, str(m.title), { size: 19, w: 700, maxW: cw - 80 }) + para(84, y + 70, str(m.text), { size: 17, lh: 22, maxW: cw - 76, max: 3 }))) + cards;
    });
    b += cards;
    b += C(58, 734, 28, '#ffffff33', S(4, '#fff')) + gl('flash', 58, 734, 24, '#fff') + C(PW - 58, 734, 28, '#ffffff33', S(4, '#fff')) + gl('camera', PW - 58, 734, 24, '#fff');
    b += T(PW / 2, 744, 'deslize para abrir', { size: 16, a: 'middle', fill: '#fff', op: .5 + .5 * pulse(t, .8) });
    return b + homeBar(PW, PH, true) + Op(1 - fade(t, 0, .35), R(0, 0, PW, PH, 0, '#000'));
  }, 'Celular bloqueado com notificações empilhando, a mais nova em cima.',
  { time: '21:42', date: 'terça, 12 de órbita', battery: 41, notifs: [{ app: 'Papo', title: 'Laura', text: 'cadê você??', color: '#2f9e62', icon: 'chat' }, { app: 'BancoTroco', title: 'Saldo baixo', text: 'Você tem R$ 0,37. Parabéns pela coragem.', color: '#7a33e0', icon: 'bank' }, { app: 'Estação', title: 'ALERTA DE OXIGÊNIO', text: 'Vazamento no módulo 3. Respire menos, por favor.', color: '#d9483b', icon: 'bolt' }, { app: 'VaiLogo', title: 'Seu pedido', text: 'O entregador desistiu da órbita.', color: '#ef8a17', icon: 'moto' }] });

  // layout e tempos de uma conversa
  function chatLayout(d) {
    const ms = arr(d.messages).map(m => ({ ...m, me: m.from === 'me' })); let c = num(d.start, .5), y = 150;
    const bw = 262;
    ms.forEach((m, i) => {
      m.text = str(m.text); m.isAudio = m.audio != null; m.hasPhoto = !!m.photo;
      m.tl = m.text ? wrap(m.text, 20, bw - 32) : [];
      m.bh = (m.hasPhoto ? 178 : 0) + (m.isAudio ? 62 : 0) + (m.tl.length ? m.tl.length * 26 + 22 : 0) + (m.hasPhoto && m.tl.length ? 4 : 0);
      m.bw = m.hasPhoto ? bw : m.isAudio ? 248 : Math.min(bw, Math.max(...m.tl.map(l => measure(l, 20))) + 34);
      if (m.t != null) c = num(m.t, c);
      if (m.me) {
        m.typing = !m.hasPhoto && !m.isAudio && d.keyboard !== false;
        m.t0 = c; m.end = m.typing ? c + 0.1 + typeTimes(m.text, 15, 3 + i).slice(-1)[0] : c + .5;
        m.show = m.end + .32; c = m.show + .75;
      } else { m.t0 = c; m.show = c + cl(.6 + m.text.length * .018, .7, 1.7); c = m.show + .55 + cl(m.text.length * .022, .2, 1.1); }
      m.y = y; y += m.bh + 12;
    });
    return { ms, endY: y };
  }
  reg('phone_chat', 'phone', (t, d) => {
    const dark = !!d.dark, { ms } = chatLayout(d), bg = dark ? '#10151f' : '#fff', tc = dark ? '#fff' : INK;
    const inH = 66;
    // teclado sobe só enquanto o Zé digita
    let kb = 0, comp = '', hl = '', compAct = false; const taps = [];
    ms.forEach((m, i) => {
      if (!m.me) return;
      kb = Math.max(kb, m.typing ? ease((t - m.t0 + .3) / .28) * (1 - ease((t - m.show - .55) / .28)) : 0);
      if (m.typing) {
        const ty = typed(t, m.text, m.t0 + .1, 15, 3 + i);
        if (t >= m.t0 && t < m.show) { comp = ty.s; compAct = true; if (ty.sinceKey < .11) hl = ty.last; }
      }
      if (d.finger !== false) taps.push({ t: m.end + .16, x: PW - 44, y: PH - (m.typing ? KB_H + 10 : 0) - 44 });
    });
    const kbH = (KB_H + 10) * kb, viewB = PH - kbH - inH - 16;
    let sc = 0; // rolagem suave: cada mensagem nova empurra a conversa
    ms.forEach(m => { const need = m.y + m.bh + 34 - viewB; sc = Math.max(sc, need * ease((t - m.show) / .3)); });
    if (kb > 0) { const lastShown = ms.filter(m => m.show <= t).pop(); if (lastShown) sc = Math.max(sc, lastShown.y + lastShown.bh + 34 - viewB); }
    let list = T(PW / 2, 138 - sc, str(d.day, 'Hoje ' + str(d.time, '21:42')), { size: 14, a: 'middle', fill: '#8892a4' });
    ms.forEach((m, i) => {
      const y = m.y - sc, x = m.me ? PW - 16 - m.bw : 16;
      evt(m.show, m.me ? 'pop' : 'alert');
      if (!m.me && t >= m.t0 && t < m.show) { // digitando…
        const yy = Math.min(y, viewB - 54);
        list += Pop(t, m.t0, 16, yy + 24, R(16, yy, 84, 44, 22, dark ? '#2a3040' : '#e9ecf2') + [0, 1, 2].map(k => C(40 + k * 18, yy + 22 - Math.max(0, Math.sin(t * 9 - k * .9)) * 6, 6, '#8892a4')).join(''));
      }
      if (t < m.show) return;
      const col = m.me ? '#2f7bf6' : (dark ? '#2a3040' : '#e9ecf2'), tcol = m.me ? '#fff' : tc;
      let bub = R(x, y, m.bw, m.bh, 20, col);
      let yy = y;
      if (m.hasPhoto) { bub += Clip(`<rect x="${x + 5}" y="${y + 5}" width="${m.bw - 10}" height="168" rx="16"/>`, photo(str(m.photo.kind || m.photo), x + 5, y + 5, m.bw - 10, 168, t, str(m.photo.label))); yy += 178; }
      if (m.isAudio) {
        bub += C(x + 34, yy + 31, 20, m.me ? '#fff' : '#2f7bf6') + gl('play', x + 35, yy + 31, 20, m.me ? '#2f7bf6' : '#fff', 2, m.me ? '#2f7bf6' : '#fff');
        for (let k = 0; k < 18; k++) bub += R(x + 64 + k * 8, yy + 31 - (4 + 13 * rnd(k + 9)), 4, 2 * (4 + 13 * rnd(k + 9)), 2, tcol, 'opacity=".75"');
        bub += T(x + m.bw - 12, yy + 54, clock(num(m.audio, 7)), { size: 12, a: 'end', fill: tcol }); yy += 62;
      }
      m.tl.forEach((l, k) => { bub += T(x + 16, yy + 30 + k * 26, l, { size: 20, fill: tcol }); });
      list += Pop(t, m.show, m.me ? x + m.bw : x, y + m.bh, bub);
      // recibo
      if (m.me) {
        const nxt = ms.slice(i + 1).find(q => q.me);
        if (!nxt || t < nxt.show) {
          const rd = num(m.read_at, m.show + 1.2), rx = PW - 18;
          if (m.read === false) { if (t > m.show + .4) list += T(rx, y + m.bh + 17, 'Entregue', { size: 13, a: 'end', fill: '#8892a4' }); }
          else if (t > rd) list += Pop(t, rd, rx - 30, y + m.bh + 12, T(rx, y + m.bh + 17, 'Lida ' + str(d.time, '21:44'), { size: 13, a: 'end', fill: '#2f7bf6', w: 600 }));
          else if (t > m.show + .4) list += T(rx, y + m.bh + 17, 'Entregue', { size: 13, a: 'end', fill: '#8892a4' });
        }
      }
    });
    let b = R(0, 0, PW, PH, 0, bg);
    for (let i = 0; i < 7; i++) b += C(30 + rnd(i) * 330, 150 + rnd(i + 20) * 500, 6 + rnd(i) * 12, dark ? '#ffffff06' : '#2f7bf60c');
    b += Clip(`<rect y="112" width="${PW}" height="${n(viewB - 112 + 10)}"/>`, list);
    const anyTy = ms.find(m => !m.me && t >= m.t0 && t < m.show);
    b += R(0, 0, PW, 112, 0, dark ? '#1a2030' : '#f6f7fa') + L(0, 112, PW, 112, dark ? '#333b4c' : '#d6dae2', 2) + statusBar(PW, d, dark, t);
    b += gl('back', 22, 80, 24, '#2f7bf6', 3) + avatar(70, 80, 24, d.contact, d.color || '#e0507a') + fit1(104, 74, str(d.contact, 'Laura'), { size: 20, w: 700, fill: tc, maxW: 200 });
    b += T(104, 96, anyTy ? 'digitando…' : str(d.status, 'online'), { size: 14, fill: '#2f9e62' });
    b += gl('video', PW - 76, 78, 26, '#2f7bf6') + gl('phone', PW - 34, 78, 24, '#2f7bf6');
    const iy = PH - kbH - inH;
    b += R(0, iy, PW, inH, 0, dark ? '#1a2030' : '#f6f7fa') + gl('plus', 28, iy + 32, 24, '#2f7bf6', 3);
    const lines = comp ? wrap(comp, 18, 250) : [], last = lines.length ? lines[lines.length - 1] : '';
    b += R(50, iy + 11, 278, 44, 22, dark ? '#10151f' : '#fff', S(2, '#c8cfd8'));
    if (last) b += T(66, iy + 39, last, { size: 18, fill: tc }); else if (!compAct) b += T(66, iy + 39, 'Mensagem', { size: 18, fill: '#99a2b2' });
    if (compAct) b += caret(68 + measure(last, 18), iy + 21, 24, t, '#2f7bf6');
    b += C(PW - 34, iy + 33, 21, comp ? '#2f7bf6' : '#9db8ff') + gl('up', PW - 34, iy + 33, 22, '#fff', 3);
    if (kb > 0) b += keyboard(PW, PH - kbH, hl, dark, t);
    return { b: b + (kb < .5 ? homeBar(PW, PH, dark) : ''), over: tapper(t, taps) };
  }, 'Conversa: mensagens surgem, "digitando…", teclado sobe quando o Zé (from "me") digita, recibo Entregue/Lida; mensagem pode ter photo (earth, selfie, food, mountain, station, cat, blur, street) ou audio (segundos).',
  { contact: 'Laura', status: 'online', time: '21:42', color: '#e0507a', dark: false, messages: [{ from: 'them', text: 'o que você faz pra se divertir?' }, { from: 'me', text: 'conserto vazamento de oxigênio' }, { from: 'them', text: 'manda foto da vista', }, { from: 'me', photo: 'earth', text: 'tá caindo um pouquinho' }, { from: 'them', text: 'isso é... a Terra?' }] });

  reg('phone_voice', 'phone', (t, d) => {
    const dark = d.dark !== false, dur = num(d.dur, 9), tp = num(d.play_at, .9), pl = cl((t - tp) / dur), play = t >= tp && pl < 1;
    const bg = dark ? '#10151f' : '#f6f7fa', tc = dark ? '#fff' : INK, acc = '#ffd23f';
    let b = R(0, 0, PW, PH, 0, bg) + R(0, 0, PW, 112, 0, dark ? '#1a2030' : '#fff') + statusBar(PW, d, dark, t) + gl('back', 22, 80, 24, acc, 3) + avatar(70, 80, 24, d.contact, d.color || '#2f9e62') + fit1(104, 74, str(d.contact), { size: 20, w: 700, fill: tc, maxW: 220 }) + T(104, 96, play ? 'gravando…' : 'online', { size: 14, fill: '#39d98a' });
    b += R(PW / 2 - 60, 132, 120, 28, 14, dark ? '#2a3040' : '#dde1e8') + fit1(PW / 2, 152, str(d.day, 'HOJE'), { size: 13, a: 'middle', fill: tc, w: 700, maxW: 104, min: 10 });
    // recado antigo, para dar contexto
    const y0 = 180, y1 = 290;
    const old = (yy, on, pp, seed, w) => {
      let s = R(16, yy, 340, 92, 20, dark ? '#1f2636' : '#fff', on ? S(4, acc) : S(2, '#3a4152')) + avatar(50, yy + 46, 22, d.contact, d.color || '#2f9e62');
      s += C(102, yy + 46, 22, on ? acc : '#3a4152') + gl(on && play ? 'pause' : 'play', 103, yy + 46, 20, on ? INK : '#fff', 3, on ? INK : '#fff');
      const nb = 26;
      for (let k = 0; k < nb; k++) {
        const x = 136 + k * 7.6, a = 5 + 22 * Math.abs(Math.sin(k * 1.7 + seed)) * (.4 + .6 * rnd(k + seed)), ph = k / nb, liv = on && play && Math.abs(ph - pp) < .1 ? 1 + .5 * Math.sin(t * 20 + k) : 1;
        s += R(x, yy + 46 - a * liv, 4, 2 * a * liv, 2, ph <= pp && on ? acc : '#7a8499');
      }
      if (on) s += C(136 + pp * nb * 7.6, yy + 46, 8, acc, S(3));
      s += T(136, yy + 84, on ? `${clock(dur * pl)} / ${clock(dur)}` : clock(w), { size: 13, fill: '#aab3c4' }) + fit1(346, yy + 84, str(d.time, '07:00'), { size: 13, a: 'end', fill: '#aab3c4', maxW: 60, min: 10 });
      return s;
    };
    b += Op(.75, old(y0, false, 0, 3, 4));
    b += Pop(t, .25, 180, y1 + 46, old(y1, true, pl, 8, dur));
    if (t > tp) b += Pop(t, tp, 40, 410, R(344 - 76, y1 - 14, 66, 28, 14, acc, S(3)) + T(344 - 43, y1 + 6, '1,5x', { size: 15, w: 700, a: 'middle' }));
    if (d.text) {
      const shown = typed(t, str(d.text), tp + .2, Math.max(8, str(d.text).length / Math.max(1, dur)), 4, 'none');
      const lines = clampLines(wrap(shown.s, 20, 320), 5, 20, 320, {}), fullN = Math.min(5, wrap(str(d.text), 20, 320).length), h = 48 + fullN * 28;
      b += Op(fade(t, tp, .3), R(16, 408, 358, h, 18, dark ? '#1a2030' : '#fff', S(4, acc)) + T(32, 436, 'TRANSCRIÇÃO', { size: 13, w: 700, fill: acc }) + lines.map((l, i) => T(32, 466 + i * 28, l, { size: 20, fill: tc })).join(''));
    }
    // quem fala, grande, com ondas no ritmo da voz
    const lv = play ? talk(t, 9) : 0, ay = 628;
    for (let i = 0; i < 3; i++) b += C(PW / 2, ay, 56 + i * 16 + lv * 18, 'none', `stroke="${acc}" stroke-width="3" opacity="${n((.5 - i * .14) * (play ? 1 : .35))}"`);
    b += avatar(PW / 2, ay, 50, d.contact, d.color || '#2f9e62');
    b += R(16, PH - 74, 300, 46, 23, dark ? '#1f2636' : '#fff', S(2, '#3a4152')) + T(36, PH - 45, 'Mensagem', { size: 17, fill: '#7a8499' }) + C(PW - 42, PH - 51, 23, acc, S(3)) + gl('mic', PW - 42, PH - 51, 24, INK, 2.4);
    return { b: b + homeBar(PW, PH, dark), over: d.finger === false ? '' : tapper(t, [{ t: tp, x: 116, y: y1 + 60 }]) };
  }, 'Mensagem de voz: bolha com play, onda que preenche e cronômetro; text opcional vira transcrição digitada.',
  { contact: 'Pai', dur: 8, play_at: .9, time: '07:00', day: 'HOJE', color: '#2f9e62', text: 'Zé, me escuta. Aguenta setenta e duas horas e não mexe em nenhum botão vermelho.' });

  reg('phone_call', 'phone', (t, d) => {
    const acc = d.state === 'active' ? 0 : d.accept_at != null ? num(d.accept_at, 2.6) : (d.state === 'incoming' ? 1e9 : 2.6), on = t >= acc, k = fade(t, acc, .3);
    let b = GR(0, 0, PW, PH, 0, on ? '#1e7a56' : '#31406f', on ? '#0f4436' : '#141b3a') + statusBar(PW, d, true, t);
    b += fit1(PW / 2, 92, on ? str(d.app, 'Chamada Papo') : 'chamada recebida…', { size: 18, a: 'middle', fill: '#cfd6e4', maxW: 300 });
    const cy = 268;
    if (!on) for (let i = 0; i < 3; i++) { const r = ((t * .9 + i / 3) % 1); b += C(PW / 2, cy, 92 + r * 110, 'none', `stroke="#fff" stroke-width="4" opacity="${n((1 - r) * .55)}"`); }
    b += C(PW / 2, cy, 92 + (on ? talk(t) * 6 : Math.sin(t * 6) * 3), d.color || '#e0507a', S(6));
    b += Clip(`<circle cx="${PW / 2}" cy="${cy}" r="89"/>`, bust(PW / 2, cy - 8, .95, t, { talk: on ? talk(t) : 0, style: d.look || 'long', shirt: '#fff', hair: d.hair || '#5b3a22', skin: d.skin_tone || '#c98a5e' }));
    b += fit1(PW / 2, 420, str(d.contact), { size: 40, w: 700, a: 'middle', fill: '#fff', maxW: 340 });
    b += on ? T(PW / 2, 458, clock(t - acc), { size: 24, a: 'middle', fill: '#aef0cf' }) : fit1(PW / 2, 458, str(d.subtitle, 'celular'), { size: 20, a: 'middle', fill: '#cfd6e4', maxW: 340 });
    if (on) {
      const items = [['mic', 'mudo'], ['keypad', 'teclado'], ['speaker', 'viva-voz'], ['plus', 'adicionar'], ['video', 'vídeo'], ['chat', 'recado']];
      items.forEach((g, i) => {
        const x = 90 + (i % 3) * 105, y = 530 + Math.floor(i / 3) * 104, a = i === 2;
        b += Pop(t, acc + .05 + i * .05, x, y, C(x, y, 36, a ? '#fff' : '#ffffff2e', S(3, '#ffffff66')) + gl(g[0], x, y, 28, a ? INK : '#fff') + T(x, y + 56, g[1], { size: 14, a: 'middle', fill: '#fff' }));
      });
      b += C(PW / 2, 722, 36, '#ff3b30', S(4)) + gl('hang', PW / 2, 722, 32, '#fff', 2.2, '#fff');
    } else {
      const bump = 1 + .08 * pulse(t, 1.6);
      b += G(100, 650, bump, C(0, 0, 40, '#ff3b30', S(5)) + gl('hang', 0, 0, 36, '#fff', 2.2, '#fff')) + T(100, 720, 'recusar', { size: 16, a: 'middle', fill: '#fff' });
      b += G(PW - 100, 650, bump, C(0, 0, 40, blink(t, 2) ? '#34d17f' : '#22a765', S(5)) + gl('phone', 0, 0, 36, '#fff', 2.2, '#fff')) + T(PW - 100, 720, 'atender', { size: 16, a: 'middle', fill: '#fff' });
      for (let i = 0; i < 3; i++) if ((t % .8) < .4) b += P(`M${PW - 150 - i * 8} ${630 - i * 8}q-16 18 0 40`, 'none', `stroke="#fff" stroke-width="3" opacity=".6"`);
    }
    return { b: b + homeBar(PW, PH, true), over: acc < 1e8 && d.finger !== false && d.state !== 'active' ? tapper(t, [{ t: acc, x: PW - 100, y: 650 }]) : '' };
  }, 'Chamada: state "incoming" (fica tocando), "active" (em curso) ou omita e use accept_at para atender no meio, com cronômetro e botões.',
  { contact: 'MÃE', subtitle: 'celular · 7ª tentativa', accept_at: 2.6, color: '#e0507a' });

  reg('phone_video_call', 'phone', (t, d) => {
    const lag = (t + 1.3) % 6.5 < .7 && d.lag !== false, tt = lag ? Math.floor(t * 3) / 3 : t;
    let b = GR(0, 0, PW, PH, 0, '#ffe2a8', '#ffb26b');
    b += R(0, 480, PW, 320, 0, '#b5764a') + R(30, 110, 130, 110, 6, '#fff', S(5)) + P('M40 210l40-50 30 30 20-20 22 40z', '#46b36b', S(3)) + R(240, 120, 110, 170, 6, '#9db8ff', S(5));
    b += bust(PW / 2 + Math.sin(tt * .8) * 8, 380, 1.9, tt, { talk: lag ? .5 : talk(tt), style: d.look || 'bun', shirt: d.shirt || '#d9483b', hair: d.hair || '#8a8a8a', skin: '#e8b98f', glasses: true });
    if (lag) { for (let i = 0; i < 14; i++) b += R(rnd(i + Math.floor(t * 6)) * PW, 220 + rnd(i * 3 + Math.floor(t * 6)) * 340, 30 + rnd(i) * 70, 14, 0, ['#d9483b', '#e8b98f', '#ffb26b', '#fff'][i % 4], 'opacity=".85"'); b += R(70, 110, 250, 40, 20, '#000a') + T(PW / 2, 138, 'conexão instável…', { size: 18, a: 'middle', fill: '#fff' }); }
    b += R(0, 0, PW, 60, 0, '#0005') + statusBar(PW, d, true, t);
    b += fit1(24, 90, str(d.contact), { size: 24, w: 700, fill: '#fff', st: '#0008', sw: 4, maxW: 220 }) + T(24, 114, clock(t + num(d.elapsed, 0)), { size: 16, fill: '#fff', st: '#0008', sw: 3 });
    // minha câmera
    const px = 240, py = 500;
    b += Pop(t, .3, px + 60, py + 90, R(px, py, 130, 180, 18, '#3a82b4', S(5)) + Clip(`<rect x="${px + 3}" y="${py + 3}" width="124" height="174" rx="15"/>`, C(px + 100, py + 40, 24, '#0c1436', S(3)) + zeBust(px + 65, py + 96, .62, t, { worried: true, talk: .1 })) + C(px + 16, py + 16, 5, '#ff3b30'));
    [['mic', '#fff3', 90], ['video', '#fff3', 165], ['hang', '#ff3b30', 240], ['speaker', '#fff3', 315]].forEach((g, i) => { b += C(g[2] - 7, 730, 30, g[1], S(4, '#fff8')) + gl(g[0], g[2] - 7, 730, 26, '#fff'); });
    return { b: b + homeBar(PW, PH, true) };
  }, 'Vídeo-chamada: pessoa grande falando, câmera do Zé no canto, travadas de conexão ocasionais.',
  { contact: 'Vó Dita', look: 'bun', elapsed: 14 });

  const ICONS = [['Papo', '#2f9e62', 'chat'], ['Fone', '#22a765', 'phone'], ['Foto', '#e0507a', 'camera'], ['TôPerdido', '#2f7bf6', 'map'], ['BancoTroco', '#7a33e0', 'bank'], ['Diário', '#d9483b', 'news'], ['Carta', '#3a82b4', 'mail'], ['Som', '#ef6ea3', 'music'], ['Hora', '#3a4152', 'clock'], ['Ajustes', '#7b8ba0', 'gear'], ['Buscão', '#ffb020', 'search'], ['Compras', '#ef8a17', 'cart'], ['Fofoca', '#e8318a', 'heart'], ['Clima', '#5ec2f0', 'cloud'], ['VaiLogo', '#ef8a17', 'moto'], ['Joguinho', '#46b36b', 'game'], ['Galeria', '#ff7a59', 'photo'], ['Notas', '#d9a400', 'note'], ['Rapidinhas', '#14182a', 'video'], ['Lanterna', '#556', 'flash']];
  reg('phone_home', 'phone', (t, d) => {
    let b = GR(0, 0, PW, PH, 0, '#4ec3f0', '#7a33e0') + C(320, 120, 130, '#ffffff22') + C(60, 660, 170, '#ffffff14');
    b += statusBar(PW, d, true, t);
    b += R(18, 62, PW - 36, 120, 26, '#ffffff33', S(4, '#fff6')) + T(36, 112, str(d.time, '21:42'), { size: 44, w: 300, fill: '#fff' }) + T(36, 148, 'céu limpo, sem ar', { size: 17, fill: '#fff' }) + gl('cloud', PW - 74, 118, 56, '#fff', 2) + T(PW - 74, 166, '-150°', { size: 18, a: 'middle', fill: '#fff', w: 700 });
    const names = ICONS.slice(0, 16), s = 66, gap = (PW - 4 * s) / 5, pick = str(d.pick, 'Papo'), at = num(d.pick_at, 2.2);
    let ix = names.findIndex(x => x[0].toLowerCase() === pick.toLowerCase()); if (ix < 0) ix = 0;
    const open = ease((t - at - .2) / .38);
    let px = 0, py = 0;
    names.forEach((ic, i) => {
      const x = gap + (i % 4) * (s + gap), y = 200 + Math.floor(i / 4) * 106, sel = i === ix;
      if (sel) { px = x + s / 2; py = y + s / 2; }
      const jig = d.wiggle ? Math.sin(t * 16 + i) * 1.5 : 0, press = sel && Math.abs(t - at) < .14 ? .85 : 1;
      let ico = appTile(-s / 2, -s / 2, s, ic[1], ic[2]);
      const badge = [3, 1, 0, 0, 9, 0, 27, 0, 0, 0, 0, 0, 99, 0, 1][i];
      if (badge) ico += C(s / 2 - 4, -s / 2 + 4, 13, '#ff3b30', S(3, '#fff')) + T(s / 2 - 4, -s / 2 + 9, String(badge), { size: 13, w: 700, a: 'middle', fill: '#fff' });
      b += G(x + s / 2, y + s / 2, press * (sel ? 1 + .05 * pulse(t, 1.5) * (t < at ? 1 : 0) : 1), Rot(jig, 0, 0, ico)) + fit1(x + s / 2, y + s + 20, ic[0], { size: 14, a: 'middle', fill: '#fff', st: '#0006', sw: 3, maxW: s + 16 });
    });
    b += R(14, PH - 112, PW - 28, 92, 30, '#ffffff44', S(3, '#fff6'));
    [0, 1, 2, 3].forEach(i => { const ic = ICONS[[1, 2, 6, 7][i]]; b += appTile(30 + i * 87, PH - 98, 62, ic[1], ic[2]); });
    b += homeBar(PW, PH, true);
    if (open > 0) { const ic = names[ix]; b += R(lerp(px - 33, 0, open), lerp(py - 33, 0, open), lerp(66, PW, open), lerp(66, PH, open), lerp(16, 0, open), ic[1]) + Op(1 - open * .4, gl(ic[2], lerp(px, PW / 2, open), lerp(py, PH / 2 - 30, open), lerp(38, 110, open), '#fff', 2.2)) + Op(open, T(PW / 2, PH / 2 + 70, ic[0], { size: 34, w: 700, a: 'middle', fill: '#fff' })); }
    return { b, over: d.finger === false ? '' : tapper(t, [{ t: at, x: px, y: py }]) };
  }, 'Tela inicial com ícones; o dedo escolhe o app "pick" (nome entre Papo, Fone, Foto, TôPerdido, BancoTroco, Diário, Fofoca, VaiLogo, Buscão...) em pick_at e ele abre.',
  { time: '21:42', pick: 'BancoTroco', pick_at: 2.2 });

  reg('phone_news', 'phone', (t, d) => {
    const items = arr(d.related), sc = Math.max(0, (t - num(d.scroll_at, 3)) * 34), lim = 430;
    const off = -Math.min(sc, lim);
    const title = str(d.headline);
    let b = R(0, 0, PW, PH, 0, '#fff'), c = '';
    let y = 150 + off;
    c += photo(d.photo || 'earth', 0, y, PW, 214, t);
    c += R(0, y + 180, 138, 34, 0, '#d9483b') + T(14, y + 205, str(d.tag, 'URGENTE'), { f: 'title', size: 22, fill: '#fff', ls: 1 });
    y += 248;
    const hd = fitPara(16, y, title, { f: 'title', size: 42, maxW: PW - 32, maxH: 160, lhk: 1.08, min: 24 });
    c += Op(fade(t, .35, .3), hd.svg);
    const hh = wrap(title, hd.size, PW - 32, { f: 'title' }).length * hd.size * 1.08;
    y += hh + 2;
    c += Op(fade(t, .6, .3), fit1(16, y, str(d.byline), { size: 14, fill: '#667', maxW: PW - 32 }));
    y += 26;
    const bodyO = { size: 20, lh: 27, maxW: PW - 32, max: 9 };
    c += Op(fade(t, .9, .3), para(16, y, str(d.body), bodyO));
    y += paraH(str(d.body), bodyO) + 6;
    c += Op(fade(t, 1.2, .3), R(16, y, PW - 32, 76, 12, '#fff3bf', S(3)) + T(28, y + 18, 'PUBLICIDADE', { size: 11, w: 700, fill: '#776' }) + fit1(28, y + 46, str(d.ad, 'Oxigênio em lata: agora sabor nuvem'), { size: 19, w: 700, maxW: PW - 56 }) + T(28, y + 66, 'só R$ 89,90 o suspiro', { size: 14 }));
    y += 94;
    items.forEach((m, i) => {
      c += R(16, y, 84, 72, 10, ['#9db8ff', '#ffd23f', '#7fd4a3'][i % 3], S(3)) + gl('news', 58, y + 36, 34, INK) + para(110, y + 24, str(m), { size: 18, w: 600, lh: 23, maxW: PW - 128, max: 3 });
      y += 86;
    });
    b += Clip(`<rect y="112" width="${PW}" height="${PH - 112}"/>`, c);
    b += R(0, 0, PW, 112, 0, '#d9483b') + statusBar(PW, d, true, t) + fit1(PW / 2, 96, str(d.paper, 'DIÁRIO DA ÓRBITA'), { f: 'title', size: 30, a: 'middle', fill: '#fff', ls: 1, maxW: 280 }) + gl('back', 24, 88, 24, '#fff', 3) + gl('share', PW - 28, 88, 24, '#fff');
    return { b: b + homeBar(PW, PH, false) };
  }, 'App de notícias: foto, tarja, manchete, corpo, anúncio absurdo e relacionadas; rola sozinho a partir de scroll_at.',
  { paper: 'DIÁRIO DA ÓRBITA', tag: 'URGENTE', headline: 'ZELADOR ESPACIAL SOME COM ÚLTIMO ROLO DE FITA DA ESTAÇÃO', byline: 'Por Redação · há 4 minutos', body: 'Testemunhas afirmam que o suspeito fugia pelo módulo 3 com um sanduíche na mão. A central pede calma, mas avisa que o ar acaba na quinta.', photo: 'station', related: ['Astronauta jura que não foi ele', 'Quanto custa um suspiro em órbita?', 'Gato da estação é promovido a chefe'], scroll_at: 3.2 });

  reg('phone_feed', 'phone', (t, d) => {
    let b = R(0, 0, PW, PH, 0, '#fff') + R(0, 0, PW, 112, 0, '#fff') + statusBar(PW, d, false, t) + fit1(18, 96, str(d.app, 'Fofoca'), { f: 'title', size: 32, fill: '#e8318a', maxW: 270 }) + gl('heart', PW - 76, 86, 26, INK) + gl('mail', PW - 32, 86, 26, INK) + L(0, 112, PW, 112, '#e2e5ea', 2);
    const y0 = 122;
    b += Slide(t, .1, 0, 40, avatar(40, y0 + 28, 22, d.user, '#2f7bf6') + fit1(72, y0 + 24, str(d.user), { size: 17, w: 700, maxW: 250 }) + T(72, y0 + 46, str(d.place, 'Órbita baixa'), { size: 14, fill: '#667' }) + T(PW - 24, y0 + 30, '···', { size: 24, w: 700, a: 'end' }));
    const py = y0 + 62, ph = 282;
    b += Pop(t, .2, PW / 2, py + ph / 2, photo(d.photo || 'selfie', 0, py, PW, ph, t));
    // curtidas subindo
    const l0 = num(d.likes_from, 12), l1 = num(d.likes_to, 48211), rate = cl((t - .8) / 4), liked = t > 1.5, likes = Math.floor(l0 + (l1 - l0) * (rate * rate));
    for (let i = 0; i < 7; i++) { const tk = 1 + i * .55, r = (t - tk) / 1.2; if (r > 0 && r < 1) b += gl('heart', 300 + Math.sin(r * 8 + i) * 24 + i * 6, py + ph - r * 240, 30, '#e8318a', 2, '#ff7ab0'); }
    const hy = py + ph + 36, hs = liked ? 1 + .35 * Math.exp(-5 * (t - 1.5)) * Math.cos((t - 1.5) * 18) : 1;
    b += G(32, hy, hs, gl('heart', 0, 0, 34, liked ? '#e8318a' : INK, 2.2, liked ? '#e8318a' : 'none')) + gl('comment', 82, hy, 30, INK) + gl('share', 130, hy, 30, INK) + gl('star', PW - 32, hy, 30, INK);
    b += T(16, hy + 38, likes.toLocaleString('pt-BR') + ' curtidas', { size: 19, w: 700 });
    b += para(16, hy + 64, str(d.user).split(' ')[0] + '  ' + str(d.caption), { size: 17, lh: 22, maxW: PW - 32, max: 2 });
    // comentários rolando
    const cs = arr(d.comments), top = hy + 110, h = PH - top - 56, step = 1.05;
    let list = '', yy = 0;
    const hts = cs.map(m => 12 + paraH(str(m.text), { size: 16, lh: 20, maxW: PW - 78, max: 3 }) + 22);
    let sc = 0;
    cs.forEach((m, i) => {
      const t0 = 1.4 + i * step; evt(t0, 'pop');
      if (yy + hts[i] > h) sc = Math.max(sc, (yy + hts[i] - h) * ease((t - t0) / .3));
      yy += hts[i];
    });
    yy = 0;
    cs.forEach((m, i) => {
      const t0 = 1.4 + i * step, c = (m.color || ['#ef8a17', '#2f9e62', '#7a33e0', '#d9483b'][i % 4]);
      list += Slide(t, t0, 0, 30, avatar(32, top + yy - sc + 20, 15, m.user, c) + T(58, top + yy - sc + 15, str(m.user), { size: 14, w: 700 }) + para(58, top + yy - sc + 35, str(m.text), { size: 16, lh: 20, maxW: PW - 78, max: 3 }));
      yy += hts[i];
    });
    b += Clip(`<rect y="${top - 4}" width="${PW}" height="${h + 6}"/>`, list);
    b += R(0, PH - 56, PW, 56, 0, '#fff') + R(16, PH - 50, PW - 32, 30, 15, '#f0f2f6') + T(32, PH - 29, 'Adicione um comentário…', { size: 15, fill: '#8892a4' });
    return { b: b + homeBar(PW, PH, false), over: d.finger === false ? '' : tapper(t, [{ t: 1.5, x: 32, y: hy + 6 }]) };
  }, 'Rede social fictícia: post, curtidas subindo sozinhas (likes_from → likes_to), corações voando e comentários rolando.',
  { app: 'Fofoca', user: 'zeladorze', place: 'Módulo 3', photo: 'selfie', caption: 'dia 12 sem oxigênio, mas com estilo', likes_from: 12, likes_to: 48211, comments: [{ user: 'laura', text: 'isso aí atrás é fogo?' }, { user: 'mae_do_ze', text: 'COME ALGUMA COISA' }, { user: 'chefe', text: 'você está demitido' }, { user: 'gato_oficial', text: 'miau' }, { user: 'nasa_de_ze', text: 'não tocamos em nada, juramos' }] });

  reg('phone_shorts', 'phone', (t, d) => {
    const dur = num(d.dur, 7), lt = t % dur;
    let b = GR(0, 0, PW, PH, 0, d.c1 || '#ff7ab0', d.c2 || '#7a33e0');
    for (let i = 0; i < 9; i++) { const a = i * 40 + t * 22; b += G(PW / 2, 400, 1, `<path d="M0 0L700 -60L700 60z" fill="#fff" opacity=".08" transform="rotate(${n(a)})"/>`); }
    const kind = str(d.scene, 'dance');
    if (kind === 'cat') b += photo('cat', 40, 190, 310, 310, t);
    else {
      const sw = Math.sin(t * 7), hop = Math.abs(Math.sin(t * 7)) * 26;
      b += E(PW / 2, 620, 120, 16, '#0004');
      b += G(PW / 2 + sw * 18, 360 - hop, 1.05, Rot(sw * 8, 0, 110, zeBust(0, 0, 1, t, { talk: Math.abs(sw), shirt: d.shirt || '#ffd23f' })) +
        Rot(-40 + sw * 40, -100, 130, R(-120, 130, 44, 150, 22, SKIN, S(6))) + Rot(40 - sw * 40, 100, 130, R(76, 130, 44, 150, 22, SKIN, S(6))) +
        R(-70, 186, 62, 130, 18, '#3d5a86', S(6)) + R(8, 186, 62, 130, 18, '#3d5a86', S(6)));
      for (let i = 0; i < 6; i++) b += gl('music', 60 + i * 56, 170 + Math.sin(t * 3 + i) * 34, 30, '#fff', 2.4);
    }
    b += R(0, 0, PW, 90, 0, '#0003') + statusBar(PW, d, true, t) + T(PW / 2, 88, 'Seguindo   |   Para você', { size: 17, w: 600, a: 'middle', fill: '#fff', st: '#0006', sw: 3 });
    const cap = str(d.caption_big, ''), words = cap.split(/\s+/).filter(Boolean);
    if (words.length) { const w = words[Math.floor(lt / .55) % words.length]; b += fit1(PW / 2 - 16, 500, w.toUpperCase(), { f: 'title', size: 62, a: 'middle', fill: '#ffd23f', st: INK, sw: 12, maxW: 300 }); }
    // coluna de ações
    const l = Math.floor(num(d.likes, 900000) * (1 + t * .004));
    const fmt = v => v >= 1e6 ? (v / 1e6).toFixed(1).replace('.', ',') + ' mi' : v >= 1e3 ? Math.floor(v / 1e3) + ' mil' : String(v);
    [['heart', fmt(l), true], ['comment', fmt(num(d.comments, 31000)), false], ['share', 'Enviar', false], ['star', 'Salvar', false]].forEach((a, i) => {
      const y = 430 + i * 82, s = a[2] ? 1 + .1 * pulse(t, 1.7) : 1;
      b += G(PW - 38, y, s, gl(a[0], 0, 0, 40, '#fff', 2.4, a[2] ? '#ff3b6b' : '#0003')) + T(PW - 38, y + 40, a[1], { size: 14, w: 600, a: 'middle', fill: '#fff', st: '#0007', sw: 3 });
    });
    b += avatar(40, 640, 22, d.user, '#2f7bf6') + fit1(72, 648, '@' + str(d.user), { size: 18, w: 700, fill: '#fff', st: '#0006', sw: 3, maxW: 170 }) + R(248, 626, 74, 32, 8, '#ff3b6b') + T(285, 648, 'Seguir', { size: 15, w: 700, a: 'middle', fill: '#fff' });
    b += para(20, 684, str(d.caption), { size: 17, lh: 22, maxW: PW - 96, max: 2, fill: '#fff', st: '#0007', sw: 3 });
    const mt = str(d.music, 'som original') + '   ♪   ';
    b += Clip(`<rect x="44" y="736" width="240" height="26"/>`, T(44 - (t * 40) % (measure(mt, 15)), 754, mt + mt + mt, { size: 15, fill: '#fff' })) + gl('music', 28, 748, 20, '#fff');
    b += R(0, PH - 28, PW, 4, 0, '#fff5') + R(0, PH - 28, PW * lt / dur, 4, 0, '#ff3b6b') + C(PW * lt / dur, PH - 26, 6, '#fff');
    return { b: b + homeBar(PW, PH, true) };
  }, 'Vídeo vertical no celular (app Rapidinhas): scene "dance" ou "cat", legenda piscando caption_big, ações laterais, barra de progresso e música correndo.',
  { user: 'zedancinha', caption: 'dançando enquanto o oxigênio acaba #fuga #orbita', caption_big: 'ESSE SOU EU FUGINDO', music: 'Batidão da Câmara de Vácuo', likes: 912000, comments: 31000, scene: 'dance', dur: 7 });

  // desenha mapa estilizado; route = pontos normalizados; devolve {svg, pos}
  function cityMap(w, h, t, seed, route, prog, col) {
    let b = R(0, 0, w, h, 0, '#e8f0dc');
    b += P(`M-10 ${n(h * .7)}C${n(w * .3)} ${n(h * .55)} ${n(w * .5)} ${n(h * .9)} ${n(w + 10)} ${n(h * .75)}V${n(h + 10)}H-10z`, '#a9e2ff', S(3, '#6bb5dc'));
    b += R(w * .08, h * .08, w * .22, h * .16, 10, '#b7e3a6', S(3, '#7fbf6d'));
    for (let i = 0; i < 8; i++) { const y = (i + .5) * h / 8; b += L(0, y + Math.sin(i + seed) * 10, w, y - Math.cos(i * 2) * 14, '#fff', 12 + (i % 3) * 4) + L(0, y + Math.sin(i + seed) * 10, w, y - Math.cos(i * 2) * 14, '#d5dbe2', 1); }
    for (let i = 0; i < 6; i++) { const x = (i + .5) * w / 6; b += L(x + 12, 0, x - 12, h, '#fff', 12); }
    for (let i = 0; i < 14; i++) b += R(rnd(seed + i) * w, rnd(seed + i * 3) * h, 26, 18, 4, ['#f4c9a8', '#d7c6f0', '#f6e49a'][i % 3], 'opacity=".8"');
    const pts = route.map(p => [p[0] * w, p[1] * h]);
    let lens = [], tot = 0;
    for (let i = 1; i < pts.length; i++) { const l = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); lens.push(l); tot += l; }
    let dd = prog * tot, pos = pts[0], ang = 0;
    for (let i = 0; i < lens.length; i++) { ang = Math.atan2(pts[i + 1][1] - pts[i][1], pts[i + 1][0] - pts[i][0]); if (dd <= lens[i]) { const k = dd / (lens[i] || 1); pos = [lerp(pts[i][0], pts[i + 1][0], k), lerp(pts[i][1], pts[i + 1][1], k)]; break; } dd -= lens[i]; pos = pts[i + 1]; }
    const path = 'M' + pts.map(p => n(p[0]) + ' ' + n(p[1])).join('L');
    b += P(path, 'none', `stroke="${INK}" stroke-width="16" stroke-linejoin="round" stroke-linecap="round"`) + P(path, 'none', `stroke="${col}" stroke-width="10" stroke-linejoin="round" stroke-linecap="round"`);
    const lp = pts[pts.length - 1];
    b += G(lp[0], lp[1] - 18, 1, gl('pin', 0, 0, 46, INK, 2, '#d9483b'));
    return { svg: b, pos, ang };
  }
  reg('phone_map', 'phone', (t, d) => {
    const route = arr(d.route).length > 1 ? d.route : [[.14, .76], [.2, .62], [.52, .57], [.56, .4], [.84, .36], [.8, .25]];
    const pr = cl(t / num(d.dur, 9)), H = PH - 112 - 150;
    const m = cityMap(PW, PH, t, 3, route, pr, '#2f7bf6');
    let b = m.svg + C(m.pos[0], m.pos[1], 16 + 12 * pulse(t, 1.4), '#2f7bf644') + C(m.pos[0], m.pos[1], 12, '#2f7bf6', S(5, '#fff'));
    b += R(0, 0, PW, 56, 0, '#0002') + statusBar(PW, d, false, t);
    const ins = arr(d.steps), i = Math.min(ins.length - 1, Math.floor(pr * ins.length));
    b += R(12, 62, PW - 24, 92, 20, '#2f7bf6', S(5)) + gl(i % 2 ? 'back' : 'up', 50, 108, 42, '#fff', 3) + para(92, 98, str(ins[i]), { size: 21, w: 700, fill: '#fff', lh: 26, maxW: PW - 124, max: 2 });
    b += R(0, PH - 138, PW, 138, 24, '#fff', S(5)) + R(PW / 2 - 28, PH - 128, 56, 5, 3, '#c8cfd8');
    b += T(22, PH - 92, Math.max(1, Math.ceil(num(d.eta, 12) * (1 - pr))) + ' min', { size: 34, w: 700, fill: '#2f9e62' }) + fit1(22, PH - 62, str(d.to), { size: 17, maxW: 210 }) + T(22, PH - 38, str(d.app, 'TôPerdido') + ' · ' + str(d.note, 'rota com menos meteoros'), { size: 13, fill: '#667' });
    b += R(PW - 124, PH - 104, 104, 54, 27, '#ff3b30', S(4)) + T(PW - 72, PH - 69, 'Sair', { size: 21, w: 700, a: 'middle', fill: '#fff' });
    return { b: b + homeBar(PW, PH, false) };
  }, 'Mapa com rota e ponto andando; steps são as instruções trocando ao longo do caminho; route opcional = [[x,y]..] de 0 a 1.',
  { app: 'TôPerdido', to: 'Cápsula de fuga', eta: 12, dur: 9, note: 'rota com menos meteoros', steps: ['Siga pelo corredor B', 'Vire onde está pegando fogo', 'Mantenha a calma por 30 metros', 'Chegou. Boa sorte.'] });

  reg('phone_bank', 'phone', (t, d) => {
    const dec = num(d.decline_at, 2.8), sal = num(d.balance, 6);
    let b = GR(0, 0, PW, 300, 0, '#7a33e0', '#4a1aa8') + R(0, 280, PW, PH, 0, '#f4f2fa') + statusBar(PW, d, true, t);
    b += fit1(22, 92, str(d.bank, 'BancoTroco'), { f: 'title', size: 30, fill: '#fff', maxW: 240 }) + gl('gear', PW - 34, 84, 26, '#fff') + T(22, 146, 'Olá, ' + str(d.name, 'Zé'), { size: 18, fill: '#e6dcff' });
    const k = ease(t / .9);
    b += T(22, 180, 'Saldo disponível', { size: 16, fill: '#e6dcff' }) + T(22, 232, money(lerp(sal * 7.3, sal, k)), { size: 48, w: 700, fill: '#fff' });
    b += T(22, 262, 'limite: ' + money(0) + ' · cartão no bico', { size: 14, fill: '#e6dcff' });
    [['share', 'Pix-ar'], ['cart', 'Pagar'], ['bank', 'Extrato'], ['heart', 'Rezar']].forEach((a, i) => { const x = 58 + i * 92; b += Pop(t, .2 + i * .06, x, 320, C(x, 320, 30, '#fff', S(4)) + gl(a[0], x, 320, 26, '#7a33e0') + T(x, 370, a[1], { size: 14, a: 'middle' })); });
    b += T(22, 416, 'Últimas compras', { size: 18, w: 700 });
    arr(d.history).slice(0, 4).forEach((m, i) => {
      const y = 430 + i * 72;
      b += Slide(t, .5 + i * .12, 50, 0, R(16, y, PW - 32, 64, 14, '#fff', S(3)) + C(46, y + 32, 20, '#ede6ff') + gl('cart', 46, y + 32, 22, '#7a33e0') + fit1(76, y + 28, str(m.what), { size: 17, w: 600, maxW: 170 }) + T(76, y + 50, str(m.when, 'hoje'), { size: 13, fill: '#667' }) + T(PW - 30, y + 38, money(-Math.abs(num(m.value, 1))), { size: 16, w: 700, a: 'end', fill: '#d9483b' }));
    });
    // compra recusada
    evt(dec, 'alert');
    if (t >= dec) {
      const sh = Math.exp(-5 * (t - dec)) * Math.sin((t - dec) * 50) * 12;
      b += Op(fade(t, dec, .15) * .55, R(0, 0, PW, PH, 0, '#000'));
      b += G(sh, 0, 1, Pop(t, dec, PW / 2, 400, R(24, 240, PW - 48, 330, 26, '#fff', S(7)) + C(PW / 2, 312, 46, blink(t, 1.6) ? '#ff3b30' : '#d9281e', S(6)) + gl('x', PW / 2, 312, 46, '#fff', 3.6) +
        T(PW / 2, 398, str(d.title, 'COMPRA RECUSADA'), { f: 'title', size: 38, a: 'middle', fill: '#d9281e' }) +
        fit1(PW / 2, 432, str(d.item, 'Oxigênio premium'), { size: 20, w: 600, a: 'middle', maxW: 290 }) + T(PW / 2, 468, money(num(d.price, 89.9)), { size: 30, w: 700, a: 'middle' }) +
        para(50, 498, str(d.reason, 'Saldo insuficiente.'), { size: 16, fill: '#667', lh: 20, maxW: 290, max: 2 }) + R(70, 524, PW - 140, 34, 17, blink(t, 1) ? '#7a33e0' : '#5f22c0') + T(PW / 2, 547, 'Chorar', { size: 17, w: 700, a: 'middle', fill: '#fff' })));
    }
    return { b: b + homeBar(PW, PH, false) };
  }, 'App de banco: saldo descendo até balance, últimas compras e, em decline_at, cartão de compra recusada tremendo.',
  { bank: 'BancoTroco', name: 'Zé', balance: 6, decline_at: 2.8, item: 'Oxigênio premium (1 suspiro)', price: 89.9, reason: 'Saldo insuficiente. Tente respirar menos.', history: [{ what: 'Sanduíche orbital', when: 'hoje', value: 42 }, { what: 'Fita isolante', when: 'ontem', value: 19.9 }, { what: 'Multa de vácuo', when: 'seg', value: 310 }] });

  reg('phone_camera', 'phone', (t, d) => {
    const shot = num(d.shot_at, 2.4), kind = d.photo || 'selfie', zoom = 1 + (t < shot ? t * .02 : 0);
    let b = R(0, 0, PW, PH, 0, '#000');
    const sh = t >= shot ? 0 : Math.sin(t * 5) * 3;
    b += Clip(`<rect y="104" width="${PW}" height="520"/>`, G(PW / 2 + sh, 364, zoom, photo(kind, -PW / 2, -260, PW, 520, t)));
    b += [1, 2].map(i => L(i * PW / 3, 104, i * PW / 3, 624, '#fff', 1.5, 'opacity=".4"') + L(0, 104 + i * 520 / 3, PW, 104 + i * 520 / 3, '#fff', 1.5, 'opacity=".4"')).join('');
    if (t < shot) { const k = cl(1.3 - t * 1.2, 1, 1.3), fx = PW / 2 - 90 * k, fy = 260 - 90 * k, fs = 180 * k, c = t > 1.1 ? '#39d98a' : '#ffd23f'; b += R(fx, fy, fs, fs, 12, 'none', S(4, c)); }
    b += T(PW / 2, 150, '● ' + str(d.mode, 'modo: desespero'), { size: 15, w: 600, a: 'middle', fill: '#ffd23f', st: '#0008', sw: 3 });
    b += R(0, 0, PW, 104, 0, '#000') + statusBar(PW, d, true, t) + gl('flash', 34, 80, 26, '#ffd23f', 2.2, '#ffd23f') + T(PW / 2, 88, 'HDR   4:3   ⏱', { size: 15, a: 'middle', fill: '#fff' });
    b += R(PW / 2 - 38, 580, 76, 30, 15, '#0007') + T(PW / 2, 601, '1x', { size: 16, w: 700, a: 'middle', fill: '#ffd23f' });
    ['VÍDEO', 'FOTO', 'RETRATO'].forEach((m, i) => { b += T(PW / 2 + (i - 1) * 96, 656, m, { size: 15, w: 700, a: 'middle', fill: i === 1 ? '#ffd23f' : '#fff' }); });
    const pr = cl(1 - Math.abs(t - shot) / .1);
    b += C(PW / 2, 722, 42, 'none', S(5, '#fff')) + C(PW / 2, 722, 34 - pr * 6, pr ? '#ccc' : '#fff') + R(PW - 88, 700, 44, 44, 22, '#2a3040') + gl('camera', PW - 66, 722, 24, '#fff');
    evt(shot, 'shutter');
    // miniatura voa para o canto
    b += R(38, 698, 52, 52, 8, '#2a3040', S(3, '#fff'));
    if (t >= shot) { const k = ease((t - shot - .12) / .4); const w = lerp(PW, 52, k), h = lerp(520, 52, k), x = lerp(0, 38, k), y = lerp(104, 698, k); b += Clip(`<rect x="${n(x)}" y="${n(y)}" width="${n(w)}" height="${n(h)}" rx="${n(k * 8)}"/>`, G(x + w / 2, y + h / 2, lerp(1, .12, k), photo(kind, -PW / 2, -260, PW, 520, shot))) + R(x, y, w, h, k * 8, 'none', S(3, '#fff')); }
    b += Op(cl(1 - (t - shot) / .3) * (t >= shot ? 1 : 0), R(0, 0, PW, PH, 0, '#fff'));
    return { b: b + homeBar(PW, PH, true), over: d.finger === false ? '' : tapper(t, [{ t: shot, x: PW / 2, y: 722 }]) };
  }, 'Câmera: foco, botão apertado em shot_at, flash branco e miniatura voando para a galeria; photo = selfie, station, earth, cat, food...',
  { photo: 'selfie', shot_at: 2.4, mode: 'modo: desespero' });

  reg('phone_search', 'phone', (t, d) => {
    const q = str(d.query), ty = typed(t, q, .6, 13, 5), sent = ty.end + .55, res = t >= sent, kbk = 1 - ease((t - sent) / .3);
    evt(sent, 'tap');
    let b = R(0, 0, PW, PH, 0, '#fff') + statusBar(PW, d, false, t);
    const top = lerp(84, 210, kbk);
    if (kbk > .02) b += Op(kbk, [...'Buscão'].map((c, i) => T(PW / 2 - 92 + i * 33, 170 + Math.sin(t * 3 + i) * 3, c, { f: 'title', size: 48, a: 'middle', fill: ['#2f7bf6', '#d9483b', '#ffb020', '#2f7bf6', '#2f9e62', '#d9483b'][i], st: INK, sw: 5 })).join(''));
    else b += T(22, 62, 'Buscão', { f: 'title', size: 22, fill: '#2f7bf6' });
    const lines = wrap(ty.s, 20, 290), last = lines[lines.length - 1] || '';
    let shown = last; const lw = measure(shown, 20);
    b += R(16, top, PW - 32, 56, 28, '#fff', S(4, res ? '#c8cfd8' : '#2f7bf6')) + gl('search', 44, top + 28, 22, '#667');
    b += (lines.length > 1 ? T(68, top + 36, '…' + last, { size: 20 }) : T(68, top + 36, last, { size: 20 })) + (res ? '' : caret(70 + lw + (lines.length > 1 ? 14 : 0), top + 14, 28, t, '#2f7bf6'));
    if (!res) {
      arr(d.suggest).slice(0, 3).forEach((s, i) => { if (ty.n < 3 + i * 4) return; const y = top + 70 + i * 40; b += Slide(t, 0, 0, 0, gl('search', 42, y + 16, 18, '#99a2b2') + fit1(66, y + 23, str(s), { size: 17, fill: '#334', maxW: 290 })); });
      const hl = ty.sinceKey < .11 && !ty.done ? ty.last : '';
      b += G(0, 0, 1, keyboard(PW, PH - (KB_H + 10) * Math.max(.001, kbk), hl, false, t));
    } else {
      let y = top + 84;
      if (d.fix) { b += Op(fade(t, sent + .1), para(18, y, 'Você quis dizer: ' + str(d.fix), { size: 16, fill: '#d9483b', w: 600, lh: 20, maxW: PW - 36, max: 2 })); y += 20 * Math.min(2, wrap('Você quis dizer: ' + d.fix, 16, PW - 36, { w: 600 }).length) + 6; }
      b += Op(fade(t, sent + .15), T(18, y, str(d.count, 'Cerca de 3 resultados (0,00 segundo de esperança)'), { size: 13, fill: '#667' }));
      y += 18;
      arr(d.results).slice(0, 6).forEach((r, i) => {
        const h = 62 + paraH(str(r.text), { size: 16, lh: 21, maxW: PW - 36, max: 3 });
        if (y + h > PH - 30) return;
        const yy = y;
        b += Slide(t, sent + .25 + i * .22, 0, 30, fit1(18, yy + 16, str(r.site), { size: 13, fill: '#2f9e62', maxW: PW - 36 }) + fit1(18, yy + 40, str(r.title), { size: 21, w: 600, fill: '#2f55c8', maxW: PW - 36 }) + para(18, yy + 62, str(r.text), { size: 16, lh: 21, fill: '#445', maxW: PW - 36, max: 3 }));
        y += h + 2;
      });
    }
    return { b: b + (res ? homeBar(PW, PH, false) : '') };
  }, 'Busca digitada letra a letra com sugestões; depois resultados engraçados surgem um a um; fix = "Você quis dizer".',
  { query: 'como consertar oxigênio com fita', suggest: ['como consertar oxigênio', 'como consertar a vida', 'como fugir da órbita a pé'], fix: 'como escrever um testamento', results: [{ site: 'wikicomo.orb › gambiarras', title: 'Fita resolve tudo? Depende', text: 'Especialistas dizem que não. Mas especialistas não estão aí.' }, { site: 'forum-do-zelador.orb', title: 'Prendi a respiração por 3 dias', text: 'Última mensagem do usuário há 3 dias.' }, { site: 'vaiporcima.orb', title: '7 sinais de que o ar acabou', text: 'O número 4 você não vai conseguir ler.' }] });

  reg('phone_battery', 'phone', (t, d) => {
    const from = num(d.from, 3), off = num(d.off_at, 5.2), warn = num(d.warn_at, .5), pct = Math.ceil(Math.max(0, from * (1 - t / off)));
    if (t > off + .35) {
      let b = R(0, 0, PW, PH, 0, '#04060c') + P('M0 240L240 0H320L0 320z', '#fff', 'opacity=".04"');
      if (t < off + 2.4 ? blink(t, 1.2) : blink(t, .5)) b += G(PW / 2, PH / 2, 1, R(-56, -26, 104, 52, 10, 'none', S(5, '#fff')) + R(48, -9, 8, 18, 3, '#fff') + R(-49, -19, 8, 38, 3, '#ff3b30')) + gl('bolt', PW / 2, PH / 2 + 74, 32, '#ff3b30', 2.4);
      return b;
    }
    let b = GR(0, 0, PW, PH, 0, '#4ec3f0', '#7a33e0');
    b += statusBar(PW, d, true, t, { battery: pct, time: d.time });
    ICONS.slice(0, 12).forEach((ic, i) => { b += appTile(28 + (i % 4) * 88, 110 + Math.floor(i / 4) * 100, 62, ic[1], ic[2]); });
    b += Op(.35 + .1 * (pct / 3), R(0, 0, PW, PH, 0, '#000'));
    evt(warn, 'alert');
    b += Pop(t, warn, PW / 2, 400, R(40, 270, PW - 80, 296, 28, '#fffffff2', S(6)) + G(PW / 2, 332, 1, R(-48, -24, 90, 48, 10, '#fff', S(5)) + R(42, -9, 8, 18, 3, INK) + R(-42, -18, 16 * Math.max(.15, pct / from), 36, 4, blink(t, 3) ? '#ff3b30' : '#ffb0a8')) +
      fit1(PW / 2, 392, str(d.title, 'Bateria fraca'), { size: 26, w: 700, a: 'middle', maxW: PW - 110 }) + T(PW / 2, 454, pct + '%', { f: 'title', size: 54, a: 'middle', fill: '#d9281e' }) +
      para(66, 486, str(d.text), { size: 16, lh: 20, fill: '#445', maxW: PW - 132, max: 2 }) + L(40, 526, PW - 40, 526, '#c8cfd8', 2) + T(PW / 2, 554, 'Ok, chorar', { size: 18, w: 600, a: 'middle', fill: '#2f7bf6' }));
    // apagando: tela encolhe para uma linha
    if (t > off) { const k = ease((t - off) / .35); b = `<g transform="translate(0 ${n(PH / 2 * k)}) scale(1 ${n(Math.max(.004, 1 - k))})">${b}</g>`; return R(0, 0, PW, PH, 0, '#04060c') + b; }
    return b;
  }, 'Bateria caindo de from% a 0, aviso e tela apagando em off_at; depois fica preta com ícone de bateria vazia piscando.',
  { from: 3, off_at: 5.2, warn_at: .5, title: 'Bateria fraca', text: 'Conecte-se a um carregador. Ou a uma estrela.', time: '21:42' });

  reg('phone_delivery', 'phone', (t, d) => {
    const pr = cl(t / num(d.dur, 10)), route = [[.12, .78], [.3, .72], [.34, .5], [.66, .46], [.7, .3], [.86, .26]], H = 500;
    const m = cityMap(PW, H, t, 9, route, pr, '#ef8a17');
    let b = R(0, 0, PW, PH, 0, '#fff') + m.svg;
    b += G(m.pos[0], m.pos[1], 1, C(0, 0, 26 + 8 * pulse(t, 1.5), '#ef8a1744') + C(0, 0, 24, '#ef8a17', S(5)) + gl('moto', 0, 0, 32, '#fff', 2.2));
    b += R(0, 0, PW, 56, 0, '#fff8') + statusBar(PW, d, false, t) + R(14, 64, 190, 44, 22, '#fff', S(4)) + fit1(32, 93, str(d.app, 'VaiLogo'), { f: 'title', size: 22, fill: '#ef8a17', maxW: 118 }) + gl('moto', 170, 86, 24, INK);
    b += R(0, 440, PW, 360, 26, '#fff', S(5));
    const steps = arr(d.steps), cu = Math.min(steps.length - 1, Math.floor(pr * steps.length));
    b += fit1(22, 482, 'Chega em ' + Math.max(1, Math.ceil(num(d.eta, 25) * (1 - pr))) + ' min', { size: 30, w: 700, maxW: 280 }) + fit1(PW - 22, 482, '#' + str(d.order, '4471'), { size: 15, a: 'end', fill: '#667', maxW: 70, min: 10 });
    b += fit1(22, 508, str(d.item), { size: 16, fill: '#445', maxW: PW - 44 });
    steps.slice(0, 4).forEach((s, i) => {
      const y = 528 + i * 36, on = i <= cu;
      b += (i < Math.min(steps.length, 4) - 1 ? L(32, y + 14, 32, y + 40, on && i < cu ? '#2f9e62' : '#c8cfd8', 4) : '') + C(32, y + 12, 11, on ? '#2f9e62' : '#fff', S(3, on ? INK : '#c8cfd8')) + (on ? gl('check', 32, y + 12, 14, '#fff', 3.6) : '');
      b += fit1(54, y + 19, str(s), { size: 17, w: i === cu ? 700 : 400, fill: on ? INK : '#99a2b2', maxW: PW - 76 });
      if (i === cu) b += Op(pulse(t, 1.4), C(32, y + 12, 16, 'none', S(3, '#2f9e62')));
    });
    b += L(16, 676, PW - 16, 676, '#e2e5ea', 2);
    b += avatar(48, 716, 26, d.courier, '#ef8a17') + fit1(84, 710, str(d.courier), { size: 18, w: 700, maxW: 180 }) + T(84, 734, '★ ' + str(d.rating, '2,1') + ' · moto voadora', { size: 14, fill: '#667' });
    b += C(PW - 96, 716, 24, '#e9ecf2', S(3)) + gl('chat', PW - 96, 716, 22, INK) + C(PW - 42, 716, 24, blink(t, 1) ? '#34d17f' : '#22a765', S(3)) + gl('phone', PW - 42, 716, 22, '#fff');
    return { b: b + homeBar(PW, PH, false) };
  }, 'App de entrega: motinho andando no mapa, etapas marcando, entregador e previsão diminuindo.',
  { app: 'VaiLogo', item: '1x Sanduíche · 2x Tanque de oxigênio', order: '4471', eta: 25, dur: 10, courier: 'Valdir', rating: '2,1', steps: ['Pedido aceito', 'Saiu da atmosfera', 'Perdido em órbita', 'Chegando na escotilha'] });

  // ---------- TV ----------
  const TW = 640, TH = 500;
  function ticker(t, text, y, h, bg = '#10203f', fg = '#fff', speed = 110) {
    const s = str(text) + '   •   ', u = Math.max(40, measure(s, 20, true));
    return R(0, y, TW, h, 0, bg) + Clip(`<rect y="${y}" width="${TW}" height="${h}"/>`, T(10 - (t * speed) % u, y + h / 2 + 7, s.repeat(Math.ceil(TW / u) + 2), { size: 20, w: 700, fill: fg }));
  }
  const liveTag = (x, y, t, s = 'AO VIVO') => R(x, y, 92, 30, 6, '#d9281e', S(3)) + (blink(t, 1) ? C(x + 15, y + 15, 6, '#fff') : '') + T(x + 26, y + 22, s, { size: 16, w: 700, fill: '#fff' });
  const chan = (x, y, s) => R(x, y, 112, 34, 6, '#ffffffe0', S(3)) + fit1(x + 56, y + 25, s, { f: 'title', size: 20, a: 'middle', fill: '#d9281e', maxW: 100 });
  // manchete em duas linhas no terço inferior
  function lowerThird(t, t0, tag, head, y) {
    const k = fade(t, t0, .3);
    return `<g transform="translate(${n((1 - k) * -640)} 0)">` + (tag ? R(0, y, 170, 40, 0, blink(t, 1.2) ? '#d9281e' : '#ef3b2e') + fit1(14, y + 30, tag, { f: 'title', size: 28, fill: '#fff', ls: 1, maxW: 145 }) : '') +
      R(0, y + 40, 620, 88, 0, '#fff') + R(0, y + 40, 10, 88, 0, '#d9281e') + fitPara(24, y + 76, head, { f: 'title', size: 36, maxW: 584, maxH: 80, lhk: 1.08, min: 18 }).svg + '</g>';
  }
  reg('tv_news', 'tv', (t, d) => {
    let b = GR(0, 0, TW, TH, 0, '#2d6fd0', '#123a86');
    for (let i = 0; i < 9; i++) b += R(i * 74, 200 - (i * 37 % 70), 54, 200, 3, '#ffffff14');
    b += P('M0 0h640v40H0z', '#ffffff10');
    // painel com gráfico
    const pts = arr(d.chart), px = 340, py = 66, pw = 276, ph = 196, ch = pts.length > 1 ? pts : [20, 30, 25, 55, 48, 80, 96];
    b += Pop(t, .4, px + pw / 2, py + ph / 2, R(px, py, pw, ph, 10, '#0c1f4a', S(4, '#7fb4ff')) + fit1(px + 14, py + 26, str(d.chart_title, 'NÍVEL DE PÂNICO'), { size: 16, w: 700, fill: '#ffd23f', maxW: pw - 28 }) +
      [1, 2, 3].map(i => L(px + 12, py + 40 + i * 36, px + pw - 12, py + 40 + i * 36, '#ffffff22', 1.5)).join(''));
    const max = Math.max(...ch), dr = cl((t - .7) / 1.8), m = (ch.length - 1) * dr, pp = [];
    for (let i = 0; i <= Math.floor(m); i++) pp.push([px + 18 + i * (pw - 36) / (ch.length - 1), py + ph - 14 - (ch[i] / max) * (ph - 66)]);
    if (m % 1 && Math.ceil(m) < ch.length) { const i = Math.floor(m), f = m - i; pp.push([px + 18 + m * (pw - 36) / (ch.length - 1), py + ph - 14 - (lerp(ch[i], ch[i + 1], f) / max) * (ph - 66)]); }
    if (pp.length > 1) { b += P('M' + pp.map(q => n(q[0]) + ' ' + n(q[1])).join('L'), 'none', 'stroke="#ff5a4d" stroke-width="6" stroke-linejoin="round" stroke-linecap="round"'); const l = pp[pp.length - 1]; b += C(l[0], l[1], 7 + 3 * pulse(t, 2), '#ffd23f', S(3)); }
    // âncora e bancada
    b += bust(170, 164, .98, t, { talk: talk(t), shirt: d.anchor_c || '#2a3040', tie: '#d9281e', style: d.anchor_style || 'short', hair: '#2a1a12', skin: d.anchor_skin || '#c98a5e' });
    b += R(40, 296, 270, 30, 6, '#d9e6ff', S(4)) + fit1(175, 318, str(d.anchor, 'Jorge Bonito'), { size: 15, w: 700, a: 'middle', maxW: 250 });
    b += chan(14, 14, str(d.channel, 'TV ÓRBITA')) + liveTag(TW - 106, 16, t) + fit1(TW - 116, 38, str(d.hour, '02:07'), { size: 18, w: 700, a: 'end', fill: '#fff', maxW: 70, min: 11 });
    b += lowerThird(t, .55, str(d.tag, 'URGENTE'), str(d.headline), 322);
    b += ticker(t, d.ticker, 456, 44);
    return b;
  }, 'Telejornal: âncora falando, gráfico sendo traçado, tarja URGENTE, manchete e letreiro correndo. Use o.talk para a boca.',
  { channel: 'TV ÓRBITA', anchor: 'Jorge Bonito', tag: 'URGENTE', headline: 'ZELADOR FOGE COM A ÚLTIMA FITA DA ESTAÇÃO', ticker: 'Autoridades pedem calma • Oxigênio acaba na quinta • Gato é promovido a comandante', chart_title: 'NÍVEL DE PÂNICO', chart: [20, 30, 25, 55, 48, 80, 96], hour: '02:07' });

  const wxIcon = (k, x, y, s, t) => k === 'sun' ? C(x, y, 22 * s, '#ffd23f', S(4)) + [...Array(8)].map((_, i) => Rot(i * 45 + t * 20, x, y, L(x, y - 28 * s, x, y - 38 * s, '#ff9f1c', 5))).join('')
    : k === 'storm' ? gl('cloud', x, y, 56 * s, INK, 2, '#7b8ba0') + gl('bolt', x + 4, y + 22 * s, 28 * s, INK, 2, '#ffd23f')
      : k === 'meteor' ? C(x + Math.sin(t * 2) * 4, y, 14 * s, '#d9483b', S(4)) + P(`M${n(x - 12)} ${n(y - 10)}l-28 -22M${n(x)} ${n(y - 16)}l-24 -28`, 'none', S(5, '#ff9f1c'))
        : gl('cloud', x, y, 56 * s, INK, 2, '#fff');
  reg('tv_weather', 'tv', (t, d) => {
    let b = GR(0, 0, TW, TH, 0, '#5ec2f0', '#2f7bf6');
    // mapa
    b += P('M250 90c60 -40 170 -40 240 0s120 90 90 170-110 110-200 96-150-60-160-130 0-110 30-136z', '#7fd4a3', S(5)) + P('M330 170q60 -30 120 0t30 80-120 30-30-110z', '#46b36b', S(4));
    for (let i = 0; i < 3; i++) { const x = (t * 26 + i * 240) % 760 - 60; b += gl('cloud', x, 120 + i * 56, 90, '#fff', 1.4, '#ffffffaa'); }
    const cs = arr(d.cities).slice(0, 4), pos = [[320, 160], [470, 130], [390, 270], [520, 260]];
    cs.forEach((c, i) => { const p = pos[i]; b += Pop(t, .4 + i * .25, p[0], p[1], wxIcon(c.icon, p[0], p[1], 1, t) + R(p[0] - 44, p[1] + 34, 88, 44, 8, '#fff', S(3)) + fit1(p[0], p[1] + 50, str(c.name), { size: 12, a: 'middle', w: 600, maxW: 80 }) + fit1(p[0], p[1] + 72, str(c.temp), { f: 'title', size: 20, a: 'middle', fill: '#d9281e', maxW: 80, min: 10 })); });
    // apresentadora apontando
    const arm = Math.sin(t * 2) * 6;
    b += bust(120, 180, 1, t, { talk: talk(t), style: 'long', shirt: '#e8318a', hair: '#7a3a12', skin: '#e8b98f' });
    b += Rot(-68 + arm, 195, 280, R(180, 276, 34, 130, 16, '#e8318a', S(5)) + C(197, 410, 18, '#e8b98f', S(5)));
    b += chan(14, 14, str(d.channel, 'TV ÓRBITA')) + liveTag(TW - 106, 16, t);
    b += R(0, 376, TW, 124, 0, '#123a86');
    b += fit1(16, 402, str(d.title, 'PREVISÃO'), { f: 'title', size: 24, fill: '#ffd23f', maxW: 600 });
    arr(d.week).slice(0, 5).forEach((w, i) => { const x = 16 + i * 124; b += Pop(t, 1.2 + i * .12, x + 54, 440, R(x, 412, 112, 80, 8, '#ffffff22', S(2.5, '#fff6')) + fit1(x + 56, 432, str(w.day), { size: 15, w: 700, a: 'middle', fill: '#fff', maxW: 100, min: 10 }) + wxIcon(w.icon, x + 34, 464, .55, t) + fit1(x + 78, 472, str(w.temp), { f: 'title', size: 20, a: 'middle', fill: '#fff', maxW: 58, min: 10 })); });
    return b;
  }, 'Previsão do tempo: apresentadora, mapa com cidades (icon sun|cloud|storm|meteor) e faixa da semana.',
  { channel: 'TV ÓRBITA', title: 'PREVISÃO', cities: [{ name: 'Módulo 1', temp: '21°', icon: 'sun' }, { name: 'Módulo 3', temp: '-40°', icon: 'storm' }, { name: 'Escotilha', temp: '-150°', icon: 'cloud' }, { name: 'Cantina', temp: '120°', icon: 'meteor' }], week: [{ day: 'SEG', temp: '-150', icon: 'cloud' }, { day: 'TER', temp: '120', icon: 'sun' }, { day: 'QUA', temp: '-90', icon: 'meteor' }, { day: 'QUI', temp: '?', icon: 'storm' }, { day: 'SEX', temp: 'RIP', icon: 'storm' }] });

  reg('tv_ad', 'tv', (t, d) => {
    const fl = Math.floor(t * 2.4) % 2;
    let b = R(0, 0, TW, TH, 0, fl ? '#ffd23f' : '#ff9f1c');
    for (let i = 0; i < 14; i++) b += G(TW / 2, 220, 1, `<path d="M0 0L600 -44L600 44z" fill="${fl ? '#ff9f1c' : '#ffd23f'}" transform="rotate(${n(i * 25.7 + t * 30)})"/>`);
    const bob = Math.sin(t * 4) * 8, s = str(d.product);
    b += Pop(t, .15, 210, 240, G(210, 236 + bob, 1, Rot(Math.sin(t * 2.3) * 7, 0, 0, R(-68, -96, 136, 200, 24, d.product_c || '#2f7bf6', S(6)) + R(-36, -128, 72, 34, 8, '#d9483b', S(6)) + R(-58, -40, 116, 90, 10, '#fff', S(5)) + fitPara(-48, -8, s, { f: 'title', size: 26, maxW: 96, maxH: 56, lhk: 1.05, min: 13 }).svg)));
    const hd = str(d.slogan);
    b += R(0, 18, TW, 74, 0, '#d9281e') + fitPara(TW / 2, 58, hd, { f: 'title', size: 42, a: 'middle', maxW: 600, maxH: 66, fill: '#fff', lhk: 1.06, min: 18 }).svg;
    const sb = 1 + .08 * pulse(t, 2.4);
    b += Pop(t, .9, 480, 260, G(480, 260, sb, Rot(-8, 0, 0, P([...Array(24)].map((_, i) => { const a = i * Math.PI / 12, r = i % 2 ? 94 : 120; return (i ? 'L' : 'M') + n(Math.cos(a) * r) + ' ' + n(Math.sin(a) * r); }).join('') + 'z', '#d9281e', S(6)) + T(0, -30, 'SÓ', { f: 'title', size: 26, a: 'middle', fill: '#fff' }) + fit1(0, 14, str(d.price, 'R$ 9,90'), { f: 'title', size: 44, a: 'middle', fill: '#ffd23f', st: INK, sw: 6, maxW: 170 }) + fit1(0, 44, str(d.price_note, 'a prestação'), { size: 15, w: 700, a: 'middle', fill: '#fff', maxW: 130, min: 10 }))));
    if (t > 1.5) b += Slide(t, 1.5, 0, 60, R(34, 366, 572, 56, 12, blink(t, 2) ? '#14182a' : '#2a3040', S(4)) + fit1(TW / 2, 405, 'LIGUE JÁ  ' + str(d.phone, '0800-ORBITA'), { f: 'title', size: 34, a: 'middle', fill: '#ffd23f', maxW: 540 }));
    b += para(14, 444, str(d.fine), { size: 11, fill: INK, w: 600, lh: 13, maxW: 612, max: 4 });
    return b;
  }, 'Comercial absurdo: raios piscando, produto rodando, selo de preço, "LIGUE JÁ" e letras miúdas.',
  { product: 'Ar em Lata', slogan: 'RESPIRE COMO UM RICO!', price: 'R$ 9,90', price_note: 'por suspiro', phone: '0800-ORBITA', fine: 'Produto não contém ar. Não respire. Efeitos colaterais incluem falta de ar, saudade da Terra e cobrança no cartão. Consulte um astronauta.' });

  reg('tv_static', 'tv', (t, d) => {
    const seed = Math.floor(t * 24), id = uid(), cut = num(d.card_at, 1.6), cardOn = t >= cut && d.card !== false;
    let b = `<defs><filter id="${id}" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="${seed}"/><feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  3.2 0 0 0 -1.25"/></filter></defs>`;
    b += R(0, 0, TW, TH, 0, '#3a3f4a') + R(0, 0, TW, TH, 0, '#000', `filter="url(#${id})" opacity="0"`);
    b += `<rect width="${TW}" height="${TH}" filter="url(#${id})" fill="#fff"/>`;
    for (let i = 0; i < 5; i++) { const y = (rnd(seed + i) * TH), h = 4 + rnd(seed * 2 + i) * 22; b += R(0, y, TW, h, 0, i % 2 ? '#fff' : '#000', 'opacity=".22"'); }
    if (cardOn) {
      const cols = ['#fff', '#ffd23f', '#35d0e6', '#39d98a', '#ef6ea3', '#ef3b2e', '#2f55c8'], roll = t < cut + .5 ? (1 - ease((t - cut) / .5)) * TH : 0;
      let c = ''; cols.forEach((k, i) => { c += R(i * TW / 7, 0, TW / 7 + 1, 330, 0, k); });
      [['#2f55c8', 0], ['#14182a', 1], ['#ef6ea3', 2], ['#14182a', 3], ['#35d0e6', 4], ['#14182a', 5], ['#fff', 6]].forEach(a => { c += R(a[1] * TW / 7, 330, TW / 7 + 1, 34, 0, a[0]); });
      c += R(0, 364, TW, 136, 0, '#14182a') + fit1(TW / 2, 430, str(d.title, 'FORA DO AR'), { f: 'title', size: 62, a: 'middle', fill: '#fff', maxW: 580 }) + fit1(TW / 2, 470, str(d.subtitle), { size: 19, w: 600, a: 'middle', fill: '#ffd23f', maxW: 580 });
      c += R(170, 110, 300, 110, 12, '#14182aee', S(4, '#fff')) + T(TW / 2, 158, str(d.channel, 'TV ÓRBITA'), { f: 'title', size: 34, a: 'middle', fill: '#fff' }) + T(TW / 2, 196, 'teste de sinal', { size: 18, a: 'middle', fill: '#cfd6e4' });
      b += G(0, -roll, 1, c) + (roll ? G(0, TH - roll, 1, c) : '') + Op(.14 + .05 * pulse(t, 7), `<rect width="${TW}" height="${TH}" filter="url(#${id})" fill="#fff"/>`);
    }
    return b;
  }, 'Chiado de TV; em card_at rola para barras coloridas com FORA DO AR. card:false fica só no chiado.',
  { channel: 'TV ÓRBITA', title: 'FORA DO AR', subtitle: 'o técnico foi sugado. voltamos já.', card_at: 1.6 });

  reg('tv_live_reporter', 'tv', (t, d) => {
    const wind = Math.sin(t * 5) * 6;
    let b = GR(0, 0, TW, TH, 0, '#a9e2ff', '#fff6d6');
    [[10, 90, 110, 220, '#f28fa0'], [130, 50, 120, 260, '#ffd23f'], [420, 70, 110, 240, '#7fd4a3'], [540, 110, 110, 200, '#9db8ff']].forEach(p => { b += R(p[0], p[1], p[2], p[3], 4, p[4], S(5)); for (let r = 0; r < 4; r++) for (let c = 0; c < 3; c++) b += R(p[0] + 12 + c * 32, p[1] + 16 + r * 44, 22, 28, 2, (r + c) % 3 ? '#fff' : '#ffd23f', S(3)); });
    b += R(0, 310, TW, 190, 0, '#c8cfd8') + L(0, 310, TW, 310, INK, 5);
    b += R(258, 110, 8, 200, 0, '#3a4152', S(3)) + E(262, 104, 24, 18, '#ffd23f', S(4));
    // figurante que dá tchauzinho e corre
    const fx = (t * 60) % 900 - 130, wv = Math.sin(t * 12) * 18;
    b += G(fx, 240, .55, zeBust(0, 0, 1, t, { talk: .6, shirt: '#46b36b', capc: '#d9483b' }) + Rot(wv - 30, 100, 120, R(90, 40, 34, 110, 16, SKIN, S(6))));
    if (d.rain !== false) for (let i = 0; i < 24; i++) { const x = (rnd(i) * 700 + t * -80) % 700, xx = x < 0 ? x + 700 : x, y = (rnd(i + 9) * 560 + t * 500) % 560; b += L(xx, y - 40, xx - 8, y - 16, '#2f7bf6', 3, 'opacity=".55"'); }
    b += G(430 + wind * .4, 210, 1.2, bust(0, 0, 1, t, { talk: talk(t), style: 'short', shirt: '#d9483b', hair: '#101010', skin: '#a56a43', worried: true }));
    b += Rot(wind * .6, 320, 400, R(308, 300, 22, 110, 6, '#2a3040', S(4)) + C(319, 288, 26, '#14182a', S(4)) + R(290, 306, 58, 30, 4, '#ffd23f', S(3)) + T(319, 327, 'T7', { f: 'title', size: 20, a: 'middle' }));
    b += chan(14, 14, str(d.channel, 'TV ÓRBITA')) + liveTag(TW - 106, 16, t) + fit1(TW - 16, 68, str(d.place, 'MÓDULO 3'), { f: 'title', size: 20, a: 'end', fill: '#fff', st: INK, sw: 5, maxW: 240 });
    b += lowerThird(t, .5, str(d.tag, 'AO VIVO'), str(d.headline), 322);
    b += R(0, 408 + 48, TW, 44, 0, '#10203f') + fit1(14, 484, str(d.reporter, 'Repórter') + ' · direto do local', { size: 18, w: 600, fill: '#fff', maxW: 610 });
    return b;
  }, 'Repórter na rua ao vivo: chuva, vento no microfone, figurante correndo atrás, tarja com manchete.',
  { channel: 'TV ÓRBITA', reporter: 'Marta Ventania', place: 'MÓDULO 3', tag: 'AO VIVO', headline: 'MORADORES RELATAM CHEIRO DE SANDUÍCHE NO VÁCUO', rain: true });

  // ---------- MONITORES ----------
  reg('monitor_terminal', 'monitor', (t, d) => {
    let bc = '#0d1b2a', b = R(0, 0, TW, TH, 0, bc) + R(0, 0, TW, 34, 0, '#1e3a5f') + [0, 1, 2].map(i => C(18 + i * 22, 17, 7, ['#ff5a4d', '#ffd23f', '#39d98a'][i], S(2))).join('') + fit1(TW / 2, 24, str(d.title, 'estacao@modulo3: ~'), { size: 15, a: 'middle', fill: '#cfd6e4', maxW: 420 });
    const rows = []; let c = .4; const lh = 25, sz = 19, mw = TW - 40;
    arr(d.lines).forEach((l, i) => {
      if (l.cmd != null) {
        const ty = typed(t, str(l.cmd), c, 22, 11 + i); const full = wrap('$ ' + l.cmd, sz, mw);
        if (t >= c) { const cur2 = wrap('$ ' + ty.s, sz, mw); cur2.forEach((x, k) => rows.push({ s: x, c: '#39d98a', bold: true, caret: !ty.done && k === cur2.length - 1 })); }
        c = ty.end + .25;
      } else if (l.bar != null) {
        const dur = num(l.dur, 1.4), p = cl((t - c) / dur) * cl(num(l.to, 100) / 100);
        if (t >= c) rows.push({ bar: true, label: str(l.bar), p, fail: l.fail && p >= cl(num(l.to, 100) / 100) });
        c += dur + .2;
      } else {
        const s = str(l.err != null ? l.err : l.ok != null ? l.ok : l.out), col = l.err != null ? '#ff6b5e' : l.ok != null ? '#ffd23f' : '#cfe6ff';
        const pre = l.err != null ? 'ERRO: ' : '';
        if (t >= c) wrap(pre + s, sz, mw).forEach(x => rows.push({ s: x, c: col, bold: l.err != null, err: l.err != null }));
        evt(c, l.err != null ? 'alert' : 'pop'); c += num(l.wait, l.err != null ? .55 : .3);
      }
    });
    const maxR = Math.floor((TH - 54) / lh), vis = rows.slice(-maxR);
    vis.forEach((r, i) => {
      const y = 62 + i * lh;
      if (r.bar) {
        b += fit1(20, y, r.label, { size: sz, fill: '#cfe6ff', maxW: 200 }) + R(232, y - 16, 300, 18, 3, '#1e3a5f', S(2, '#7fb4ff')) + R(235, y - 13, 294 * r.p, 12, 2, r.fail ? '#ff5a4d' : '#39d98a') + T(TW - 20, y, Math.floor(r.p * 100) + '%' + (r.fail ? ' !' : ''), { size: sz, w: 700, a: 'end', fill: r.fail ? '#ff6b5e' : '#39d98a' });
      } else {
        if (r.err && blink(t, 2)) b += R(14, y - 18, TW - 28, 24, 3, '#7a1f18');
        b += T(20, y, r.s, { size: sz, fill: r.c, w: r.bold ? 600 : 400 });
        if (r.caret) b += R(23 + measure(r.s, sz, r.bold), y - 17, 11, 21, 1, '#39d98a');
      }
    });
    if (rows.length && c < t) { const y = 62 + vis.length * lh; if (vis.length < maxR) b += T(20, y, '$', { size: sz, w: 600, fill: '#39d98a' }) + caret(38, y - 17, 21, t, '#39d98a'); }
    return b;
  }, 'Terminal: lines = sequência de {cmd} (digitado), {out}, {ok}, {err} (pisca em vermelho), {bar,to,dur,fail} (barra de progresso).',
  { title: 'estacao@modulo3: ~', lines: [{ cmd: 'sudo abrir --escotilha 3' }, { out: 'verificando permissões...' }, { bar: 'copiando ar', to: 100, dur: 1.2 }, { bar: 'pressurizando', to: 62, dur: 1.2, fail: true }, { err: 'válvula presa por sanduíche' }, { cmd: 'rm -rf sanduiche' }, { err: 'acesso negado: o sanduíche é do chefe' }, { ok: 'tentando plano B: fita isolante' }] });

  function cctvCam(i, cam, t, w, h) {
    const kind = str(cam.kind, ['corridor', 'airlock', 'canteen', 'hangar'][i % 4]);
    let b = GR(0, 0, w, h, 0, '#5a8fb0', '#2d5570');
    if (kind === 'corridor') b += P(`M0 0L${w * .35} ${h * .3}V${h * .7}L0 ${h}zM${w} 0L${w * .65} ${h * .3}V${h * .7}L${w} ${h}z`, '#3a6c8c', S(3)) + R(w * .35, h * .3, w * .3, h * .4, 0, '#1e3a4f', S(3)) + C(w * .5, h * .5, 12, '#ffd23f', S(3));
    else if (kind === 'airlock') b += C(w * .5, h * .46, h * .32, '#c9d6e2', S(4)) + C(w * .5, h * .46, h * .22, '#0c1436', S(3)) + C(w * .56, h * .54, h * .12, '#2a8fd8') + R(0, h * .82, w, h * .18, 0, '#55697f', S(3));
    else if (kind === 'canteen') b += R(0, h * .7, w, h * .3, 0, '#55697f') + R(w * .2, h * .5, w * .6, 16, 3, '#c58a55', S(3)) + R(w * .24, h * .55, 10, h * .2, 0, '#8d5934') + R(w * .72, h * .55, 10, h * .2, 0, '#8d5934') + R(w * .1, h * .1, 90, 50, 4, '#fff', S(3)) + T(w * .1 + 45, h * .1 + 32, 'PF R$9', { size: 17, w: 700, a: 'middle' }) + E(w * .5, h * .49, 22, 8, '#fff', S(3));
    else b += R(0, h * .75, w, h * .25, 0, '#55697f') + R(w * .1, h * .3, 120, 70, 10, '#d9483b', S(3)) + P(`M${w * .1 + 120} ${h * .3}l40 35-40 35z`, '#ffd23f', S(3)) + R(w * .65, h * .45, 60, h * .3, 4, '#f0b429', S(3));
    if (cam.motion !== false && (cam.motion || i === 1)) { // vulto passando
      const per = 5.5, x = ((t / per + i * .3) % 1) * (w + 80) - 40, st = Math.sin(t * 8) * 4;
      b += G(x, h * .62 + st * .3, .28, zeBust(0, -30, 1, 3, { talk: 0, shirt: cam.color || '#efe', capc: '#d9483b' }) + R(-26, 160, 22, 120, 8, '#14182a') + R(6, 160, 22, 120, 8, '#14182a'));
    }
    b += R(0, 0, w, h, 0, '#0e2b1e', 'opacity=".12"');
    return b;
  }
  reg('monitor_cctv', 'monitor', (t, d) => {
    let b = R(0, 0, TW, TH, 0, '#0b0d14');
    const cams = arr(d.cams).slice(0, 4), cw = 316, ch = 246, base = String(str(d.clock, '03:12:40')).split(':').map(x => parseInt(x, 10) || 0), sec = (base[0] || 0) * 3600 + (base[1] || 0) * 60 + (base[2] || 0) + Math.floor(t);
    const hhmm = pad2(sec / 3600 % 24) + ':' + pad2(sec / 60 % 60) + ':' + pad2(sec % 60), al = num(d.alert_cam, -1), alOn = t > num(d.alert_at, 1.6);
    cams.forEach((c, i) => {
      const x = 2 + (i % 2) * (cw + 4), y = 2 + (i > 1 ? 1 : 0) * (ch + 4), lost = !!c.lost;
      let s;
      if (lost) { const sd = Math.floor(t * 18); s = R(0, 0, cw, ch, 0, '#2a3040'); for (let k = 0; k < 90; k++) s += R(rnd(sd + k) * cw, rnd(sd + k * 3) * ch, 14, 4, 0, k % 2 ? '#c8cfd8' : '#14182a'); s += R(cw / 2 - 90, ch / 2 - 22, 180, 44, 6, '#14182a') + T(cw / 2, ch / 2 + 9, 'SEM SINAL', { f: 'title', size: 26, a: 'middle', fill: '#fff' }); }
      else s = cctvCam(i, c, t, cw, ch);
      const hot = i === al && alOn;
      s += R(8, 8, Math.min(190, measure('CAM 01 ' + str(c.name), 15, true) + 16), 24, 4, '#0009') + fit1(16, 25, 'CAM 0' + (i + 1) + ' ' + str(c.name), { size: 15, w: 700, fill: '#fff', maxW: 174 });
      s += (blink(t, 1) ? C(cw - 66, 20, 7, '#ff3b30') : '') + T(cw - 54, 26, 'REC', { size: 15, w: 700, fill: '#ff3b30' }) + R(cw - 128, ch - 30, 120, 22, 3, '#0009') + T(cw - 68, ch - 13, hhmm, { size: 15, w: 600, a: 'middle', fill: '#fff' });
      if (hot) s += R(4, 4, cw - 8, ch - 8, 4, 'none', S(blink(t, 2) ? 7 : 4, '#ff3b30')) + R(cw / 2 - 86, ch - 62, 172, 26, 4, '#ff3b30') + fit1(cw / 2, ch - 43, str(d.alert, 'MOVIMENTO!'), { size: 16, w: 700, a: 'middle', fill: '#fff', maxW: 160, min: 10 });
      b += G(x, y, 1, Clip(`<rect width="${cw}" height="${ch}"/>`, s));
    });
    return b;
  }, 'Painel de 4 câmeras com REC, hora correndo e vulto passando; cam: {name, kind corridor|airlock|canteen|hangar, motion, lost}; alert_cam (0-3) acende aviso em alert_at.',
  { clock: '03:12:40', alert_cam: 1, alert_at: 1.6, alert: 'MOVIMENTO!', cams: [{ name: 'CORREDOR B' }, { name: 'ESCOTILHA', motion: true }, { name: 'CANTINA' }, { name: 'HANGAR', lost: true }] });

  reg('monitor_radar', 'monitor', (t, d) => {
    const cx = 236, cy = 250, r = 214, sw = (t * 110) % 360;
    let b = R(0, 0, TW, TH, 0, '#072a1c') + C(cx, cy, r, '#0b3d28', S(5, '#39d98a'));
    [.25, .5, .75].forEach(k => { b += C(cx, cy, r * k, 'none', S(2, '#39d98a66')); });
    b += L(cx - r, cy, cx + r, cy, '#39d98a66', 2) + L(cx, cy - r, cx, cy + r, '#39d98a66', 2);
    for (let i = 0; i < 16; i++) { const a = (sw - i * 4) * Math.PI / 180, a2 = (sw - (i + 1) * 4) * Math.PI / 180; b += P(`M${cx} ${cy}L${n(cx + Math.cos(a) * r)} ${n(cy + Math.sin(a) * r)}L${n(cx + Math.cos(a2) * r)} ${n(cy + Math.sin(a2) * r)}z`, '#39d98a', `opacity="${n((16 - i) / 40)}"`); }
    arr(d.blips).slice(0, 6).forEach((p, i) => {
      const v = num(p.v, 0), ang = num(p.a, i * 70) * Math.PI / 180, dist = cl(num(p.d, .7) - v * t, .04, 1), x = cx + Math.cos(ang) * dist * r, y = cy + Math.sin(ang) * dist * r, aDeg = (ang * 180 / Math.PI + 360) % 360, age = ((sw - aDeg + 360) % 360) / 360, o = 1 - age * .85, hot = p.hot;
      b += C(x, y, 8 + (hot ? 3 * pulse(t, 2) : 0), hot ? '#ff5a4d' : '#c8ffe4', `opacity="${n(o)}"`) + Op(o, T(x + 13, y + 5, str(p.label), { size: 14, w: 700, fill: hot ? '#ff9a90' : '#c8ffe4' }));
    });
    b += C(cx, cy, 7, '#fff') ;
    const hot = arr(d.blips).find(p => p.hot) || {}, dist = Math.max(0, cl(num(hot.d, .7) - num(hot.v, 0) * t, 0, 1)) * num(d.range, 1000);
    b += R(466, 24, 158, 452, 8, '#0b3d28', S(3, '#39d98a')) + fit1(545, 54, str(d.title, 'RADAR'), { f: 'title', size: 26, a: 'middle', fill: '#39d98a', maxW: 140 });
    b += T(480, 98, 'ALVO', { size: 14, w: 700, fill: '#7fe0b0' }) + fit1(480, 126, str(hot.label, '---'), { size: 22, w: 700, fill: '#fff', maxW: 132 });
    b += T(480, 172, 'DISTÂNCIA', { size: 14, w: 700, fill: '#7fe0b0' }) + T(480, 214, Math.floor(dist) + ' m', { f: 'title', size: 38, fill: blink(t, 2) ? '#ffd23f' : '#fff' });
    b += T(480, 260, 'VELOCIDADE', { size: 14, w: 700, fill: '#7fe0b0' }) + fit1(480, 292, str(d.speed, '28.000 km/h'), { size: 20, w: 700, fill: '#fff', maxW: 134 });
    [0, 1, 2, 3, 4, 5].forEach(i => { b += R(480 + i * 22, 402 - 60 * (.3 + .7 * Math.abs(Math.sin(t * 2 + i))), 16, 60 * (.3 + .7 * Math.abs(Math.sin(t * 2 + i))), 2, '#39d98a'); });
    b += R(476, 420, 138, 42, 6, blink(t, 1.4) ? '#d9281e' : '#7a1f18', S(3, '#fff')) + fit1(545, 448, str(d.status, 'COLISÃO'), { f: 'title', size: 22, a: 'middle', fill: '#fff', maxW: 126 });
    return b;
  }, 'Radar com varredura; blips {label, a (ângulo°), d (0-1 do centro), v (aproximação por s), hot} e painel de distância.',
  { title: 'RADAR', range: 1000, speed: '28.000 km/h', status: 'COLISÃO', blips: [{ label: 'METEORO', a: 320, d: .85, v: .05, hot: true }, { label: 'LIXO', a: 130, d: .6 }, { label: 'GARRAFA', a: 210, d: .42 }] });

  reg('monitor_vitals', 'monitor', (t, d) => {
    const bpm = lerp(num(d.bpm, 72), num(d.bpm_to, 148), ease(t / num(d.dur, 6))), spo2 = lerp(num(d.o2, 98), num(d.o2_to, 84), ease(t / num(d.dur, 6))), low = spo2 < num(d.alarm_below, 90);
    let b = R(0, 0, TW, TH, 0, low && blink(t, 1.5) ? '#2a0b10' : '#0b1220');
    const beat = 60 / bpm;
    const ecg = ph => { const x = ph % 1; return x < .08 ? Math.sin(x / .08 * 3.14) * .1 : x < .14 ? 0 : x < .17 ? -.15 : x < .21 ? 1 : x < .25 ? -.3 : x > .35 && x < .5 ? Math.sin((x - .35) / .15 * 3.14) * .2 : 0; };
    const wave = (y, amp, f, col, label) => {
      let p = ''; const head = (t * 130) % 400;
      for (let x = 0; x <= 400; x += 3) { const dt = ((x - head + 400) % 400); if (dt < 20) { if (p && !p.endsWith('|')) p += '|'; continue; } const tt = t - dt / 130; p += (p === '' || p.endsWith('|') ? 'M' : 'L') + (14 + x) + ' ' + n(y - f(tt) * amp) + ' '; }
      return P(p.replace(/\|/g, ''), 'none', `stroke="${col}" stroke-width="3.5" stroke-linejoin="round"`) + C(14 + head, y - f(t) * amp, 5, '#fff') + T(14, y - amp - 6, label, { size: 14, w: 700, fill: col });
    };
    b += fit1(14, 28, str(d.patient, 'PACIENTE: ZÉ'), { size: 18, w: 700, fill: '#fff', maxW: 300 }) + fit1(428, 28, str(d.room, 'ENFERMARIA'), { size: 16, a: 'end', fill: '#9fb0c8', maxW: 110, min: 10 });
    b += wave(150, 70, tt => ecg(tt / beat), '#39d98a', 'ECG');
    b += wave(280, 34, tt => Math.sin(tt * 6.28 / beat) * .5 + .4 * Math.sin(tt * 12.56 / beat + 1) * .5, '#5ec2f0', 'PLETH');
    b += wave(400, 30, tt => Math.sin(tt * 1.5) * .7, '#ffd23f', 'RESP');
    const box = (y, h, lab, val, un, col, al) => R(448, y, 180, h, 8, al && blink(t, 2) ? '#d9281e' : '#ffffff0c', S(3, col)) + T(460, y + 22, lab, { size: 14, w: 700, fill: col }) + fit1(616, y + h - 16, val, { f: 'title', size: 62, a: 'end', fill: al && blink(t, 2) ? '#fff' : col, maxW: 124, min: 20 }) + T(460, y + h - 14, un, { size: 13, fill: '#9fb0c8' });
    b += box(14, 132, 'BATIMENTOS', String(Math.round(bpm)), 'bpm', '#39d98a', bpm > 130) + gl('heart', 604, 34, 22 + 7 * Math.exp(-8 * ((t % beat))), '#ff5a4d', 2, '#ff5a4d');
    b += box(156, 132, 'OXIGÊNIO', Math.round(spo2) + '%', 'SpO₂', '#5ec2f0', low) + box(298, 104, 'TEMP', str(d.temp, '38,4'), '°C', '#ffd23f', false);
    b += R(448, 412, 180, 74, 8, low ? (blink(t, 2) ? '#d9281e' : '#7a1f18') : '#14532d', S(3, '#fff')) + fit1(538, 460, low ? str(d.alarm, 'ALARME') : 'ESTÁVEL', { f: 'title', size: 32, a: 'middle', fill: '#fff', maxW: 160 });
    return b;
  }, 'Monitor médico: ECG, pleth e respiração varrendo; batimentos vão de bpm a bpm_to e oxigênio de o2 a o2_to em dur; alarme abaixo de alarm_below.',
  { patient: 'PACIENTE: ZÉ', room: 'ENFERMARIA', bpm: 72, bpm_to: 148, o2: 98, o2_to: 84, dur: 6, temp: '38,4', alarm: 'ALARME', alarm_below: 90 });

  reg('monitor_map_station', 'monitor', (t, d) => {
    let b = R(0, 0, TW, TH, 0, '#144a8a');
    for (let i = 0; i < 16; i++) b += L(i * 44, 0, i * 44, TH, '#ffffff14', 1.5);
    for (let i = 0; i < 12; i++) b += L(0, i * 44, TW, i * 44, '#ffffff14', 1.5);
    b += fit1(16, 34, str(d.title, 'PLANTA DA ESTAÇÃO'), { f: 'title', size: 28, fill: '#fff', ls: 1, maxW: 400 }) + fit1(TW - 16, 32, str(d.deck, 'DECK 2'), { size: 18, w: 700, a: 'end', fill: '#9fd0ff', maxW: 180, min: 11 });
    const rs = arr(d.rooms), al = str(d.alert, ''), col = '#cfe6ff';
    b += P('M92 150H548M320 150V380M92 380H548M92 150V380M548 150V380', 'none', `stroke="${col}" stroke-width="20" opacity=".3"`);
    rs.forEach((r, i) => {
      const hot = str(r.name) === al;
      b += Pop(t, .1 + i * .08, r.x + r.w / 2, r.y + r.h / 2, R(r.x, r.y, r.w, r.h, 8, hot ? (blink(t, 1.6) ? '#d9281e' : '#a81c13') : '#2f7bc8', S(4, '#fff')) + para(r.x + r.w / 2, r.y + r.h / 2 + 5, str(r.name).toUpperCase(), { size: 14, w: 700, a: 'middle', fill: '#fff', lh: 16, maxW: r.w - 12, max: 2 }));
    });
    b += Op(.8, C(320, 265, 60, 'none', S(3, '#fff')) + T(320, 270, 'NÚCLEO', { size: 13, w: 700, a: 'middle', fill: '#fff' }));
    // ponto andando pelo corredor
    const rt = arr(d.path).length > 1 ? d.path : [[92, 380], [320, 380], [320, 150], [548, 150]];
    let tot = 0, ls = []; for (let i = 1; i < rt.length; i++) { const l = Math.hypot(rt[i][0] - rt[i - 1][0], rt[i][1] - rt[i - 1][1]); ls.push(l); tot += l; }
    let dd = cl(t / num(d.dur, 8)) * tot, p = rt[0];
    for (let i = 0; i < ls.length; i++) { if (dd <= ls[i]) { const k = dd / (ls[i] || 1); p = [lerp(rt[i][0], rt[i + 1][0], k), lerp(rt[i][1], rt[i + 1][1], k)]; break; } dd -= ls[i]; p = rt[i + 1]; }
    b += P('M' + rt.map(q => q[0] + ' ' + q[1]).join('L'), 'none', 'stroke="#ffd23f" stroke-width="4" stroke-dasharray="10 10" opacity=".85"');
    if (blink(t, 2)) b += C(p[0], p[1], 22, 'none', S(3, '#ffd23f'));
    b += C(p[0], p[1], 11, '#ffd23f', S(4)) + R(p[0] - 44, p[1] - 44, 88, 26, 6, '#ffd23f', S(3)) + fit1(p[0], p[1] - 25, str(d.who, 'VOCÊ'), { size: 15, w: 700, a: 'middle', maxW: 78 });
    b += R(0, 442, TW, 58, 0, '#0c2f5c') + C(30, 471, 9, '#ffd23f', S(3)) + fit1(46, 477, str(d.who, 'VOCÊ'), { size: 15, w: 600, fill: '#fff', maxW: 78, min: 10 }) + R(130, 462, 18, 18, 3, '#d9281e', S(2, '#fff')) + T(156, 477, 'perigo', { size: 15, w: 600, fill: '#fff' }) + fit1(TW - 16, 478, str(d.note), { size: 16, w: 700, a: 'end', fill: '#ffd23f', maxW: 370 });
    return b;
  }, 'Planta azul da estação: salas com nomes, a sala em alert pisca em vermelho e o ponto who anda pelo corredor (path opcional).',
  { title: 'PLANTA DA ESTAÇÃO', deck: 'DECK 2', who: 'ZÉ', alert: 'Módulo 3', dur: 8, note: 'saída mais próxima: nenhuma', rooms: [{ name: 'Cantina', x: 30, y: 70, w: 130, h: 80 }, { name: 'Módulo 3', x: 480, y: 70, w: 130, h: 80 }, { name: 'Oxigênio', x: 255, y: 70, w: 130, h: 80 }, { name: 'Hangar', x: 30, y: 350, w: 130, h: 80 }, { name: 'Enfermaria', x: 255, y: 350, w: 130, h: 80 }, { name: 'Cápsula', x: 480, y: 350, w: 130, h: 80 }] });

  reg('monitor_countdown', 'monitor', (t, d) => {
    const from = num(d.from, 30), left = Math.max(0, from - t), done = left <= 0, hot = left <= num(d.red_at, 10);
    let b = R(0, 0, TW, TH, 0, hot ? (blink(t, 2) ? '#7a1f18' : '#4a100b') : '#10203f');
    const stripes = y => { let s = R(0, y, TW, 40, 0, '#ffd23f', S(3)); for (let i = -1; i < 16; i++) s += P(`M${i * 50 + (t * 40) % 50} ${y}h24l-24 40h-24z`, INK); return s; };
    b += stripes(0) + stripes(TH - 40);
    b += fit1(TW / 2, 96, str(d.title, 'AUTODESTRUIÇÃO EM'), { f: 'title', size: 42, a: 'middle', fill: '#fff', ls: 1, maxW: 590 });
    if (done) {
      evt(from, 'alert');
      b += Pop(t, from, TW / 2, 260, fit1(TW / 2, 300, str(d.end, 'ZERO'), { f: 'title', size: 140, a: 'middle', fill: '#ffd23f', st: INK, sw: 10, maxW: 590 }));
    } else {
      const fr = Math.floor((left % 1) * 100), beatS = 1 + .05 * Math.exp(-6 * (1 - (left % 1)));
      b += R(40, 130, TW - 80, 210, 16, '#0b0d14', S(6, hot ? '#ff5a4d' : '#39d98a'));
      b += G(TW / 2, 300, beatS, T(0, 0, clock(left) + ':' + pad2(fr), { f: 'title', size: 138, a: 'middle', fill: hot ? '#ff5a4d' : '#39d98a' }));
    }
    b += R(40, 356, TW - 80, 26, 6, '#0b0d14', S(3, '#fff')) + R(44, 360, (TW - 88) * left / from, 18, 3, hot ? '#ff5a4d' : '#39d98a');
    b += fit1(TW / 2, 424, str(d.note), { size: 22, w: 600, a: 'middle', fill: '#fff', maxW: 590 });
    return b;
  }, 'Contagem regressiva gigante com faixas de perigo; fica vermelha em red_at e mostra end ao zerar.',
  { title: 'AUTODESTRUIÇÃO EM', from: 30, red_at: 10, note: 'Por favor, retire seus pertences', end: 'ZERO' });

  // ---------- OUTROS ----------
  function cardBg(t, o, c1, c2, body) {
    const dev = o.device || 'fullscreen';
    return (dev === 'hand' ? dimBg(.6 * fade(t, 0, .2)) : backdrop(t, c1, c2)) + body;
  }
  // aparelho de mão: coloca (w,h) centrado, com mão se pedido
  function handheld(t, o, d, w, h, body, bg, opt = {}) {
    const dev = o.device || 'fullscreen', k = spr(t), y0 = opt.y != null ? opt.y : (1280 - h) / 2;
    if (dev === 'hand') {
      const s = opt.hs || .94, hh = holdHand(w, h, d.skin || SKIN, d.sleeve || SLEEVE), bob = Math.sin(t * 1.6) * 5;
      return dimBg(.5 * fade(t, 0, .25)) + `<g transform="translate(${n((720 - w * s) / 2)} ${n(opt.hy != null ? opt.hy + bob + (1 - k) * 760 : 150 + bob + (1 - k) * 760)}) rotate(${n(-2 + (1 - k) * 8)} ${w / 2} ${h}) scale(${s})">` + hh.back + body + hh.front + '</g>';
    }
    const s = opt.fs || 1;
    return backdrop(t, bg[0], bg[1]) + `<g transform="translate(${n((720 - w * s) / 2)} ${n(y0 + (h - h * s) / 2 + Math.sin(t * 1.4) * 3 + (1 - k) * 640)}) rotate(${n((1 - k) * 6)} ${w / 2} ${h / 2}) scale(${s})">` + body + '</g>';
  }

  reg('radio_comms', 'radio', (t, d) => {
    const lv = talk(t, 9), [cw, ch] = SIZES.radio, msg = typed(t, str(d.text), .5, num(d.cps, 15), 6);
    let c = R(0, 0, cw, ch, 8, '#c8f0b0');
    c += fit1(14, 28, 'CANAL ' + str(d.channel, '7'), { size: 18, w: 700, maxW: 190 }) + fit1(cw - 14, 28, str(d.freq, '148,7 MHz'), { size: 18, w: 700, a: 'end', maxW: 190 }) + L(10, 40, cw - 10, 40, INK, 3);
    c += T(14, 66, 'FALANDO:', { size: 14, w: 700, fill: '#2d5a2d' }) + fit1(14, 100, str(d.who), { f: 'title', size: 36, maxW: cw - 124 });
    for (let i = 0; i < 12; i++) { const h = 6 + (lv * 40) * (.3 + .7 * Math.abs(Math.sin(t * 13 + i * 1.3))); c += R(cw - 104 + i * 8, 84 - h, 5, h, 1, INK); }
    const lines = wrap(msg.s, 26, cw - 28, { w: 600 }).slice(-5);
    lines.forEach((l, i) => { c += T(14, 146 + i * 33, l, { size: 26, w: 600 }); });
    if (!msg.done) c += caret(16 + measure(lines[lines.length - 1] || '', 26, true), 124 + (lines.length - 1) * 33, 27, t);
    const lcd = Clip(`<rect width="${cw}" height="${ch}" rx="8"/>`, c);
    if (o_dev(cur.o) === 'tv_on_set') return lcd;
    const bw = 480, bh = 860;
    let b = R(330, -190, 34, 210, 12, '#2a3040', S(6)) + C(347, -196, 16, '#d9483b', S(5));
    b += R(0, 0, bw, bh, 44, '#ffb020', S(7)) + R(14, 14, bw - 28, bh - 28, 34, '#e5940a', S(4));
    b += R(-14, 300, 18, 130, 6, '#2a3040', S(5)) + C(90, -14, 32, '#3a4152', S(6)) + R(20, 40, 440, 320, 16, '#2a3040', S(5)) + G(30, 50, 1, lcd);
    b += C(70, 400, 12, lv > .15 ? (blink(t, 6) ? '#ff5a4d' : '#b92a20') : '#552', S(4)) + T(92, 406, 'TX', { size: 18, w: 700 }) + T(bw - 40, 408, str(d.brand, 'FALATRON'), { f: 'title', size: 22, a: 'end' });
    for (let r = 0; r < 8; r++) for (let q = 0; q < 12; q++) b += C(70 + q * 31, 450 + r * 30, 8, '#7a4f06');
    b += R(150, 700, 180, 56, 12, '#2a3040', S(5)) + T(240, 738, 'FALAR', { f: 'title', size: 26, a: 'middle', fill: '#fff' });
    // ondas saindo da antena
    for (let i = 0; i < 4; i++) { const r = ((t * 1.2 + i * .25) % 1); b += C(347, -196, 24 + r * 130, 'none', `stroke="#fff" stroke-width="5" opacity="${n((1 - r) * (.3 + lv * .7))}"`); }
    return handheld(t, cur.o, d, bw, bh, b, ['#2fb8a8', '#0f5a78'], { fs: .98, y: 290, hs: .74, hy: 260 });
  }, 'Rádio comunicador: nome de quem fala, onda de nível, fala digitada no visor e ondas saindo da antena.',
  { who: 'CONTROLE', channel: '7', freq: '148,7 MHz', text: 'Zé, aqui é o controle. Largue o sanduíche e vá para a escotilha agora.', brand: 'FALATRON' });
  function o_dev(o) { return (o && o.device) || 'fullscreen'; }

  reg('tablet_checklist', 'tablet', (t, d) => {
    const [cw, ch] = SIZES.tablet, items = arr(d.items).slice(0, 8), step = num(d.step, .9), t0 = num(d.start, .8);
    let c = R(0, 0, cw, ch, 10, '#fff') + R(0, 0, cw, 124, 0, '#ffd23f') + L(0, 124, cw, 124, INK, 5);
    c += fit1(26, 44, str(d.kicker, 'MISSÃO 2'), { size: 18, w: 700, ls: 2, maxW: cw - 52 }) + fit1(26, 100, str(d.title), { f: 'title', size: 48, maxW: cw - 150 }) + T(cw - 24, 102, clock(Math.max(0, num(d.timer, 90) - t)), { f: 'title', size: 36, a: 'end', fill: '#d9281e' });
    const doneN = items.filter((_, i) => t >= t0 + i * step && items[i].done !== false).length, FS = 30, rowH = items.length > 5 ? 74 : 92;
    let y = 146;
    items.forEach((m, i) => {
      const tk = t0 + i * step, on = m.done !== false && t >= tk, cu = !on && (i === 0 || t >= t0 + (i - 1) * step);
      const lines = clampLines(wrap(str(m.text != null ? m.text : m), FS, cw - (m.tag ? 220 : 130), { w: 600 }), 2, FS, cw - (m.tag ? 220 : 130), { w: 600 }), h = Math.max(rowH, lines.length * 36 + 20);
      evt(tk, 'tap');
      c += R(20, y, cw - 40, h - 8, 12, on ? '#e4f8ec' : cu ? '#fff6d6' : '#f4f6fa', S(4, on ? '#2f9e62' : INK));
      c += R(34, y + (h - 8) / 2 - 18, 36, 36, 8, on ? '#2f9e62' : '#fff', S(4));
      if (on) c += Pop(t, tk, 52, y + (h - 8) / 2, gl('check', 52, y + (h - 8) / 2, 30, '#fff', 4));
      lines.forEach((l, k) => { const ly = y + (h - 8) / 2 + 11 - (lines.length - 1) * 18 + k * 36; c += T(84, ly, l, { size: FS, w: 600, fill: on ? '#667' : INK }); if (on) { const w = measure(l, FS, true) * ease((t - tk) / .25); c += L(84, ly - 8, 84 + w, ly - 8, '#2f9e62', 3); } });
      if (m.tag) c += R(cw - 124, y + (h - 8) / 2 - 13, 90, 26, 13, '#d9483b') + fit1(cw - 79, y + (h - 8) / 2 + 6, str(m.tag), { size: 13, w: 700, a: 'middle', fill: '#fff', maxW: 82 });
      y += h;
    });
    const pr = items.length ? doneN / items.length : 0;
    c += R(20, ch - 74, cw - 40, 22, 11, '#e2e5ea', S(3)) + R(23, ch - 71, (cw - 46) * ease(pr), 16, 8, '#2f9e62') + T(cw - 22, ch - 86, doneN + '/' + items.length, { size: 18, w: 700, a: 'end' }) + T(22, ch - 86, 'progresso', { size: 16, fill: '#667' });
    const all = t0 + (items.length - 1) * step + .5;
    if (d.stamp !== false && items.length && items.every(m => m.done !== false) && t >= all) { evt(all, 'alert'); c += Pop(t, all, cw / 2, ch - 180, Rot(-5, cw / 2, ch - 150, R(46, ch - 196, cw - 92, 92, 14, '#39d98a', S(7)) + fit1(cw / 2, ch - 130, str(d.stamp_text, 'MISSÃO CONCLUÍDA'), { f: 'title', size: 50, a: 'middle', maxW: cw - 120 }))); }
    const scr = Clip(`<rect width="${cw}" height="${ch}" rx="10"/>`, c);
    if (o_dev(cur.o) === 'tv_on_set') return scr;
    const bw = cw + 56, bh = ch + 56, b = R(0, 0, bw, bh, 36, '#2a3040', S(7)) + C(bw / 2, 14, 5, '#566') + G(28, 28, 1, scr + glass(cw, ch));
    return handheld(t, cur.o, d, bw, bh, b, ['#ffb020', '#d9483b'], { fs: 1.06, y: 190, hs: .92, hy: 170 });
  }, 'Tablet com objetivos marcando um a um (risca o texto), barra de progresso e carimbo no fim; item pode ter done:false para ficar pendente.',
  { kicker: 'MISSÃO 2', title: 'PREPARE O ABRIGO', timer: 90, start: .8, step: .9, items: [{ text: 'Coletar água' }, { text: 'Fechar a escotilha' }, { text: 'Carregar tudo' }, { text: 'Esconder o sanduíche do chefe', tag: 'SECRETO' }] });

  reg('smartwatch', 'watch', (t, d) => {
    const [cw, ch] = SIZES.watch, al = num(d.alert_at, .4), on = t >= al, c1 = d.color || '#d9281e';
    evt(al, 'alert');
    let c = R(0, 0, cw, ch, 0, on && blink(t, 1.5) ? c1 : '#0b0d14');
    c += T(cw / 2, 40, str(d.time, '21:42'), { size: 26, w: 700, a: 'middle', fill: '#fff' });
    if (on) {
      c += Pop(t, al, cw / 2, 110, gl(d.icon || 'bolt', cw / 2, 106, 76, '#fff', 2.2, '#ffffff33'));
      c += fitPara(cw / 2, 204, str(d.title), { f: 'title', size: 40, a: 'middle', fill: '#fff', maxW: cw - 36, maxH: 88, lhk: 1.08, min: 20 }).svg;
      c += para(cw / 2, 274, str(d.text), { size: 18, a: 'middle', fill: '#fff', lh: 22, maxW: cw - 36, max: 2 });
    } else c += gl('heart', cw / 2, 170, 80, '#ff5a4d');
    const scr = Clip(`<rect width="${cw}" height="${ch}" rx="64"/>`, c);
    if (o_dev(cur.o) === 'tv_on_set') return scr;
    const dev = o_dev(cur.o), k = spr(t), vib = on ? Math.sin(t * 70) * 4 * (.5 + .5 * Math.sign(Math.sin(t * 6))) : 0;
    let b = dev === 'hand' ? dimBg(.55 * fade(t, 0, .2)) : backdrop(t, '#2f7bf6', '#123a86');
    let w = '';
    w += `<g transform="rotate(-6 360 640)">`;
    w += R(-200, 500, 1120, 330, 120, d.skin || SKIN, S(7)) + R(-260, 470, 300, 390, 40, d.sleeve || SLEEVE, S(7)) + P('M40 470v390', 'none', S(5)) + P('M660 520q40 120 0 240', 'none', S(4, '#b9a98a'));
    w += R(258, 180, 204, 930, 30, '#2a3040', S(7)) + [0, 1, 2, 3, 4].map(i => L(290, 220 + i * 40, 430, 220 + i * 40, '#3a4152', 5) + L(290, 900 + i * 40, 430, 900 + i * 40, '#3a4152', 5)).join('');
    w += `</g>`;
    b += `<g transform="translate(${n((1 - k) * 700)} ${n((1 - k) * 240)})">` + w;
    b += G(360 + vib, 640, 1, Rot(-6, 0, 0, R(-200, -222, 400, 444, 96, '#7b8ba0', S(7)) + R(-184, -206, 368, 412, 84, '#14182a') + R(198, -60, 22, 60, 8, '#c8cfd8', S(5)) + G(-150, -170, 1, scr + glass(cw, ch))));
    if (on) for (let i = 0; i < 3; i++) { const q = (t * 2.4 + i * .33) % 1, a = (1 - q) * .8; b += P(`M${n(130 - q * 40)} 470q${n(-70 - q * 26)} 170 0 340`, 'none', `stroke="#fff" stroke-width="6" stroke-linecap="round" opacity="${n(a)}"`) + P(`M${n(590 + q * 40)} 470q${n(70 + q * 26)} 170 0 340`, 'none', `stroke="#fff" stroke-width="6" stroke-linecap="round" opacity="${n(a)}"`); }
    return b + '</g>';
  }, 'Close no pulso: relógio vibra com alerta piscando (title grande, text pequeno).',
  { time: '21:42', title: 'OXIGÊNIO 12%', text: 'Respire devagar. Isso é uma ordem.', alert_at: .4, icon: 'bolt' });

  reg('atm', 'atm', (t, d) => {
    const [cw, ch] = SIZES.atm, pinAt = 1.1, pin = str(d.pin, '1234'), ty = typed(t, pin, pinAt, 4, 2), done = ty.end + .4, wait = done + 1, fin = t >= wait;
    let c = R(0, 0, cw, ch, 6, fin ? (d.ok ? '#17803d' : '#a81c13') : '#1b4fa8');
    c += R(0, 0, cw, 52, 0, '#0002') + fit1(16, 36, str(d.bank, 'BANCOTROCO 24H'), { f: 'title', size: 26, fill: '#ffd23f', maxW: cw - 32 });
    if (t < pinAt) {
      c += T(cw / 2, 150, 'Insira seu cartão', { f: 'title', size: 42, a: 'middle', fill: '#fff' }) + G(cw / 2, 220 + Math.sin(t * 5) * 8, 1, R(-44, -28, 88, 56, 8, '#ffd23f', S(4)) + gl('up', 0, 0, 30, INK, 3));
    } else if (t < done) {
      c += T(cw / 2, 130, 'Digite sua senha', { f: 'title', size: 38, a: 'middle', fill: '#fff' });
      [0, 1, 2, 3].forEach(i => { const x = cw / 2 - 96 + i * 64; c += R(x, 170, 56, 66, 8, '#fff', S(4)) + (i < ty.n ? C(x + 28, 203, 12, INK) : ''); });
      c += T(cw / 2, 290, 'não deixe ninguém ver', { size: 18, a: 'middle', fill: '#cfe0ff' });
    } else if (!fin) {
      c += T(cw / 2, 150, 'Aguarde…', { f: 'title', size: 44, a: 'middle', fill: '#fff' });
      for (let i = 0; i < 8; i++) { const a = i * 45 + t * 240; c += Rot(a, cw / 2, 220, C(cw / 2, 190, 8, '#fff', `opacity="${n((i + 1) / 8)}"`)); }
    } else {
      evt(wait, 'alert');
      c += Pop(t, wait, cw / 2, 150, fitPara(cw / 2, 136, str(d.result), { f: 'title', size: 54, a: 'middle', fill: '#fff', maxW: cw - 40, maxH: 130, lhk: 1.08, min: 24 }).svg) + para(cw / 2, 240, str(d.detail), { size: 21, a: 'middle', fill: '#fff', lh: 26, maxW: cw - 50, max: 3 }) + (blink(t, 1.2) ? T(cw / 2, 336, str(d.action, '» RETIRE SEU CARTÃO «'), { size: 18, w: 700, a: 'middle', fill: '#ffd23f' }) : '');
    }
    const scr = Clip(`<rect width="${cw}" height="${ch}" rx="6"/>`, c);
    if (o_dev(cur.o) === 'tv_on_set') return scr;
    const bw = 620, bh = 1090, hl = ty.sinceKey < .2 && !ty.done ? ty.last : '';
    let b = R(0, 0, bw, bh, 26, '#c8cfd8', S(7)) + R(0, 0, bw, 84, 26, '#d9483b', S(7)) + T(bw / 2, 60, 'CAIXA 24H', { f: 'title', size: 46, a: 'middle', fill: '#fff' });
    b += R(62, 104, cw + 36, ch + 36, 14, '#2a3040', S(6)) + G(80, 122, 1, scr + glass(cw, ch));
    [0, 1, 2, 3].forEach(i => { b += R(20, 146 + i * 76, 36, 44, 6, '#7b8ba0', S(4)) + R(bw - 56, 146 + i * 76, 36, 44, 6, '#7b8ba0', S(4)); });
    const keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#'];
    b += R(60, 530, 300, 366, 14, '#3a4152', S(6));
    keys.forEach((k, i) => { const x = 76 + (i % 3) * 92, y = 546 + Math.floor(i / 3) * 86, on = k === hl; b += R(x, y + (on ? 4 : 0), 80, 74, 10, on ? '#ffd23f' : '#e6e9ef', S(4)) + T(x + 40, y + 50 + (on ? 4 : 0), k, { f: 'title', size: 36, a: 'middle' }); });
    b += R(392, 546, 170, 16, 6, '#14182a', S(4)) + T(477, 596, 'CARTÃO', { size: 16, w: 700, a: 'middle' });
    const cardOut = t < pinAt ? ease(1 - (t - .4) / .6) : (fin ? ease((t - wait - .3) / .5) : 0);
    b += R(424, 562 - 100 * (1 - cardOut) * 0 , 106, 70 * cardOut, 6, '#ffd23f', S(4));
    b += R(392, 660, 170, 90, 10, '#2a3040', S(4)) + C(477, 705, 26, '#39d98a22', S(3, '#39d98a')) + T(477, 712, 'R$', { f: 'title', size: 24, a: 'middle', fill: '#39d98a' });
    b += R(392, 776, 170, 120, 10, '#14182a', S(4)) + R(404, 836, 146, 10, 3, '#3a4152') + T(477, 816, 'NOTAS', { size: 16, w: 700, a: 'middle', fill: '#c8cfd8' });
    b += R(60, 930, 500, 130, 12, '#e6e9ef', S(5)) + para(bw / 2, 974, 'Câmeras em operação. Sorria, sua conta está vazia.', { size: 22, w: 600, a: 'middle', lh: 28, maxW: 460, max: 2 });
    return handheld(t, cur.o, d, bw, bh, b, ['#7fd4ff', '#2f7bf6'], { fs: 1.08, y: 96, hs: .96, hy: 110 });
  }, 'Caixa eletrônico: pede cartão, senha digitada no teclado, aguarde, e o result (grande) com detail; ok:true deixa verde.',
  { bank: 'BANCOTROCO 24H', pin: '1234', result: 'SALDO INSUFICIENTE', detail: 'Seu saldo é R$ 0,37. Tarifa do saque: R$ 8,90.', ok: false });

  reg('newspaper', 'paper', (t, d) => {
    const spin = num(d.spin, 1.1), k = ease(t / spin), s = .05 + .95 * (1 - Math.pow(1 - cl(t / spin), 3)), rot = (1 - cl(t / spin)) ** 2 * 900, settle = t > spin ? Math.exp(-6 * (t - spin)) * Math.sin((t - spin) * 22) * 4 : 0, sway = Math.sin(t * 1.1) * .8;
    const w = 620, h = 880;
    evt(spin, 'alert');
    let p = R(0, 0, w, h, 4, '#f7f1e1', S(7)) + R(8, 8, w, h, 4, '#0000');
    p += fit1(w / 2, 40, str(d.edition, 'EDIÇÃO EXTRA · ANO 12 · R$ 2,00'), { size: 15, w: 700, a: 'middle', fill: '#554', maxW: w - 40, min: 10 });
    p += fit1(w / 2, 104, str(d.paper, 'O GRITO ORBITAL'), { f: 'title', size: 70, a: 'middle', maxW: w - 40, ls: 2 }) + L(20, 122, w - 20, 122, INK, 6) + L(20, 132, w - 20, 132, INK, 2);
    const hd = fitPara(w / 2, 240, str(d.headline), { f: 'title', size: 124, a: 'middle', fill: '#d9281e', maxW: w - 40, maxH: 262, lhk: 1.04, min: 28 });
    p += hd.svg;
    const y1 = 412;
    p += R(20, y1, 340, 250, 2, '#fff', S(4)) + photo(d.photo || 'selfie', 24, y1 + 4, 332, 242, 2) + para(24, y1 + 276, str(d.caption, 'O suspeito, em foto de arquivo.'), { size: 15, w: 600, lh: 18, maxW: 332, max: 2, fill: '#554' });
    const body = str(d.body), cols = wrap(body, 17, 210), half = 13;
    cols.slice(0, half).forEach((l, i) => { p += T(382, y1 + 16 + i * 21, l, { size: 17 }); });
    p += L(372, y1, 372, y1 + 300, '#998', 2);
    for (let c = 0; c < 3; c++) for (let i = 0; i < 7; i++) p += R(24 + c * 196, 730 + i * 17, c === 2 && i === 6 ? 90 : 180, 7, 2, '#c8bfa8');
    const pg = `<g transform="translate(360 ${610}) rotate(${n(rot + settle + sway)}) scale(${n(s)}) translate(${-w / 2} ${-h / 2})">${p}</g>`;
    const dev = o_dev(cur.o);
    return (dev === 'hand' ? dimBg(.6 * fade(t, 0, .2)) : backdrop(t, '#d9483b', '#7a1f18', {})) + pg;
  }, 'Capa de jornal girando até parar na frente da câmera, com manchete enorme, foto e texto.',
  { paper: 'O GRITO ORBITAL', headline: 'CADÊ A FITA, ZÉ?', edition: 'EDIÇÃO EXTRA · ANO 12 · R$ 2,00', photo: 'selfie', caption: 'O suspeito, em foto de arquivo.', body: 'A polícia orbital procura o zelador que sumiu com o último rolo de fita. Vizinhos dizem que ele sempre foi quieto, mas que deixava o micro-ondas sujo.', spin: 1.1 });

  reg('id_card', 'card', (t, d) => {
    const k = spr(t * .9), w = 620, h = 400, st = num(d.stamp_at, 1.8), sw = (t * .5) % 1;
    let c = R(0, 0, w, h, 26, '#fdfbf3', S(7)) + R(0, 0, w, 76, 26, d.color || '#2f7bf6', S(7)) + R(3, 50, w - 6, 24, 0, d.color || '#2f7bf6');
    c += fit1(26, 52, str(d.org, 'ESTAÇÃO ORBITAL'), { f: 'title', size: 36, fill: '#fff', ls: 1, maxW: 430 }) + C(w - 48, 38, 24, '#ffd23f', S(4)) + gl('star', w - 48, 38, 28, INK, 2);
    c += R(28, 100, 180, 224, 10, '#cfe6ff', S(5)) + Clip('<rect x="31" y="103" width="174" height="218" rx="8"/>', zeBust(118, 208, 1.02, t, { worried: true }));
    const row = (y, l, v) => T(232, y, l, { size: 15, w: 700, fill: '#667' }) + fit1(232, y + 30, str(v), { size: 27, w: 700, maxW: w - 258 });
    c += row(110, 'NOME', d.name) + row(176, 'CARGO', d.role) + row(242, 'SETOR', d.sector);
    for (let i = 0; i < 44; i++) c += R(232 + i * 8.2, 300 + 8, 2 + rnd(i) * 4, 44, 0, INK);
    c += fit1(28, 356, 'Nº ' + str(d.number, '0471-Z'), { size: 19, w: 700, maxW: 195, min: 11 }) + fit1(28, 380, 'validade: ' + str(d.valid, 'ontem'), { size: 15, fill: '#d9281e', w: 600, maxW: 195, min: 11 });
    c += Clip(`<rect width="${w}" height="${h}" rx="26"/>`, `<path d="M${n(sw * 1100 - 300)} 0h80l-180 ${h}h-80z" fill="#fff" opacity=".42"/>`);
    if (d.stamp && t >= st) { evt(st, 'alert'); c += Pop(t, st, 400, 200, Rot(-14, 400, 200, R(190, 140, 420, 120, 10, '#ffffff66', S(9, d.stamp_color || '#d9281e')) + fit1(400, 224, str(d.stamp), { f: 'title', size: 74, a: 'middle', fill: d.stamp_color || '#d9281e', maxW: 390 }))); }
    const b = R(330, -200, 60, 760, 0, '#d9483b', S(6)) + R(322, 524, 76, 64, 10, '#c8cfd8', S(6)) + `<g transform="translate(50 ${n(580 + (1 - k) * 800)}) rotate(${n((1 - k) * -22 + Math.sin(t * 1.3) * 1.2)} ${w / 2} 0)">${c}</g>`;
    return cardBg(t, cur.o, '#9db8ff', '#2f55c8', b);
  }, 'Crachá balançando no cordão com foto, dados, código de barras, brilho e carimbo opcional em stamp_at.',
  { org: 'ESTAÇÃO ORBITAL', name: 'José "Zé" Silva', role: 'Zelador Espacial', sector: 'Módulo 3', number: '0471-Z', valid: 'ontem', stamp: 'PROCURADO', stamp_at: 1.8, stamp_color: '#d9281e' });

  // ícones de objetos: usa V.props se houver, senão desenho próprio
  const ITEMS = {
    tape: () => C(0, 0, 36, '#b9bdc4', S(6)) + C(0, 0, 15, '#23527d', S(5)),
    oxygen_tank: () => R(-20, -38, 40, 80, 16, '#39d98a', S(6)) + R(-10, -48, 20, 14, 4, '#c8cfd8', S(5)) + T(0, 10, 'O₂', { f: 'title', size: 22, a: 'middle' }),
    wrench: () => Rot(40, 0, 0, R(-9, -30, 18, 74, 8, '#c8cfd8', S(6)) + P('M-22 -46a22 22 0 0 0 44 0l-10-8v14h-24v-14z', '#c8cfd8', S(6))),
    key: () => C(-16, 0, 18, '#ffd23f', S(6)) + R(0, -6, 44, 12, 3, '#ffd23f', S(5)) + R(28, 4, 8, 14, 2, '#ffd23f', S(4)),
    sandwich: () => P('M-38 -8q38-34 76 0z', '#e8b56b', S(6)) + R(-36, -8, 72, 10, 4, '#46b36b', S(4)) + R(-36, 2, 72, 10, 3, '#d9483b', S(4)) + R(-38, 12, 76, 14, 7, '#e8b56b', S(5)),
    battery: () => R(-34, -18, 62, 36, 6, '#fff', S(6)) + R(28, -8, 8, 16, 2, INK) + R(-28, -12, 22, 24, 3, '#ff5a4d'),
    medkit: () => R(-34, -26, 68, 54, 8, '#fff', S(6)) + R(-14, -40, 28, 14, 5, 'none', S(5)) + R(-6, -16, 12, 34, 2, '#d9483b') + R(-17, -5, 34, 12, 2, '#d9483b'),
    flashlight: () => Rot(-30, 0, 0, R(-34, -10, 44, 20, 5, '#3a4152', S(5)) + P('M10 -10l22 -10v40l-22 -10z', '#ffd23f', S(5))),
    rope: () => C(0, 0, 34, 'none', S(12, '#c58a55')) + C(0, 0, 20, 'none', S(10, '#a56a35')),
    sock: () => P('M-18 -40h34v44l18 16a14 14 0 0 1-12 20h-30l-10-26z', '#9db8ff', S(6)),
    coin: () => C(0, 0, 30, '#ffd23f', S(6)) + T(0, 12, '$', { f: 'title', size: 34, a: 'middle' }),
    note: () => R(-30, -36, 60, 72, 4, '#fff4d6', S(6)) + L(-18, -16, 18, -16) + L(-18, 2, 18, 2) + L(-18, 20, 6, 20),
  };
  function itemIcon(name, s, t) {
    const pr = V.props && V.props[name];
    if (typeof pr === 'function') { try { return `<g transform="scale(${n(s)})">${pr(t, { state: {}, label: '' })}</g>`; } catch (e) { /* cai no desenho próprio */ } }
    return `<g transform="scale(${n(s * 1.1)})">${(ITEMS[name] || ITEMS.note)()}</g>`;
  }
  reg('inventory_full', 'card', (t, d) => {
    const items = arr(d.items).slice(0, 16), cols = 4, slot = 148, gap = 8, x0 = 28, y0 = 300, total = 16;
    const dev = o_dev(cur.o);
    let b = dev === 'hand' ? dimBg(.6 * fade(t, 0, .2)) : backdrop(t, '#ffb020', '#c94f1a');
    let c = R(20, 120, 680, 1040, 30, '#fff4d6', S(8)) + R(20, 120, 680, 110, 30, '#7a4f2a', S(8)) + R(23, 180, 674, 48, 0, '#7a4f2a');
    c += fit1(46, 192, str(d.title, 'MOCHILA'), { f: 'title', size: 60, fill: '#fff', ls: 2, maxW: 400 }) + T(676, 176, 'CAPACIDADE', { size: 16, w: 700, a: 'end', fill: '#f5d9b0' });
    const usedK = items.filter((m, i) => t >= .4 + i * .18).length, w = num(d.weight, usedK * 2.5), mw = num(d.max_weight, 40), over = w > mw;
    c += T(676, 208, usedK + '/' + total + ' · ' + w + ' kg', { size: 24, w: 700, a: 'end', fill: over ? '#ffb0a8' : '#fff' });
    c += R(42, 244, 636, 26, 13, '#e6d5ae', S(4)) + R(46, 248, 628 * cl(ease(t / 2) * w / mw), 18, 9, over ? '#d9281e' : '#2f9e62');
    for (let i = 0; i < total; i++) {
      const x = x0 + 12 + (i % cols) * (slot + gap), y = y0 + Math.floor(i / cols) * (slot + gap), m = items[i], t0 = .4 + i * .18, nw = m && m.new;
      c += R(x, y, slot, slot, 18, '#e6d5ae', S(5));
      if (m && t >= t0) {
        evt(t0, 'pop');
        c += Pop(t, t0, x + slot / 2, y + slot / 2, (nw ? R(x + 4, y + 4, slot - 8, slot - 8, 14, '#fff3b0', S(blink(t, 1.6) ? 6 : 4, '#ef8a17')) : '') + G(x + slot / 2, y + slot / 2 - 18 + (nw ? Math.sin(t * 4) * 3 : 0), 1, itemIcon(str(m.icon, 'note'), 1, t)) + fit1(x + slot / 2, y + slot - 14, str(m.label), { size: 18, w: 700, a: 'middle', maxW: slot - 16 }) + (m.qty ? C(x + slot - 26, y + 26, 18, '#2f7bf6', S(4)) + T(x + slot - 26, y + 33, String(m.qty), { size: 19, w: 700, a: 'middle', fill: '#fff' }) : '') + (nw ? R(x + 6, y + 6, 66, 26, 8, '#ef8a17', S(3)) + T(x + 39, y + 25, 'NOVO', { size: 15, w: 700, a: 'middle', fill: '#fff' }) : ''));
      }
    }
    const sel = items.findIndex(m => m.new), si = sel >= 0 ? sel : 0, m = items[si];
    if (m && t > 1.6) c += Slide(t, 1.6, 0, 40, para(46, 1115 - 0, str(m.label).toUpperCase() + ': ' + str(m.desc, 'Serve para alguma coisa, provavelmente.'), { size: 22, w: 600, lh: 28, maxW: 628, max: 1 }));
    return b + G(0, (1 - spr(t)) * 900, 1, c);
  }, 'Grade de mochila: itens {icon, label, qty, new, desc} aparecem um a um, peso enchendo; icon = nome de prop ou tape, oxygen_tank, wrench, key, sandwich, battery, medkit, flashlight, rope, sock, coin, note.',
  { title: 'MOCHILA', weight: 18, max_weight: 40, items: [{ icon: 'tape', label: 'Fita', qty: 1 }, { icon: 'sandwich', label: 'Sanduíche', qty: 2 }, { icon: 'wrench', label: 'Chave' }, { icon: 'oxygen_tank', label: 'Oxigênio', new: true, desc: 'Sobram dois suspiros e meio.' }, { icon: 'sock', label: 'Meia' }, { icon: 'battery', label: 'Pilha' }, { icon: 'key', label: 'Chave 3' }, { icon: 'medkit', label: 'Remédio' }] });

  reg('mission_card', 'card', (t, d) => {
    const w = 620, y0 = 400, acc = '#ffd23f', objs = arr(d.objectives).slice(0, 4), h = 372 + objs.length * 52;
    let c = R(0, 0, w, h, 26, '#14182a', S(7, acc)) + R(10, 10, w - 20, h - 20, 18, 'none', S(2, acc));
    c += fit1(w / 2, 72, str(d.kicker, 'MISSÃO PRINCIPAL'), { size: 22, w: 700, a: 'middle', fill: '#cfd6e4', ls: 3, maxW: w - 60 });
    c += fitPara(w / 2, 158, str(d.title), { f: 'title', size: 82, a: 'middle', fill: acc, maxW: w - 60, maxH: 170, lhk: 1.04, min: 34 }).svg;
    c += L(50, 262, w - 50, 262, acc, 3);
    if (d.deadline) c += R(w / 2 - 138, 282, 276, 44, 22, '#2a3040', S(3, acc)) + gl('clock', w / 2 - 110, 304, 24, acc) + fit1(w / 2 + 12, 312, str(d.deadline), { size: 22, w: 700, a: 'middle', fill: '#fff', maxW: 210 });
    objs.forEach((o2, i) => { const y = 350 + i * 52, tk = .9 + i * .3; c += Slide(t, tk, 60, 0, R(52, y, 32, 32, 7, 'none', S(3, '#fff')) + fit1(100, y + 24, str(o2.text != null ? o2.text : o2), { size: 25, w: 600, fill: '#fff', maxW: w - 150 })); evt(tk, 'pop'); });
    const b = Pop(t, 0, 360, y0 - 96, R(218, y0 - 118, 284, 58, 29, '#14182a', S(5, acc)) + gl('bolt', 254, y0 - 89, 30, acc, 2.4) + fit1(378, y0 - 76, str(d.badge, 'NOVA MISSÃO'), { size: 25, w: 700, a: 'middle', fill: acc, ls: 2, maxW: 196, min: 13 })) +
      C(360, y0 - 8 + 0, 0, 'none') + `<g transform="translate(50 ${y0}) translate(${w / 2} ${h / 2}) scale(${n(spr(t - .1))}) rotate(${n((1 - spr(t - .1)) * -6)}) translate(${-w / 2} ${-h / 2})">${t >= .1 ? c : ''}</g>`;
    return cardBg(t, cur.o, '#3a4152', '#14182a', b);
  }, 'Cartão NOVA MISSÃO em preto e amarelo com título enorme, prazo e objetivos surgindo.',
  { badge: 'NOVA MISSÃO', kicker: 'MISSÃO PRINCIPAL', title: 'SOBREVIVA 72H', deadline: 'até o ar acabar', objectives: ['Achar a fita', 'Tapar o vazamento', 'Não apertar o botão vermelho'] });

  reg('level_up', 'card', (t, d) => {
    const from = num(d.from, 3), to = num(d.to, 4), sw = t > .9, dev = o_dev(cur.o);
    let b = dev === 'hand' ? dimBg(.55 * fade(t, 0, .2)) : GR(0, 0, 720, 1280, 0, '#7a33e0', '#2b1168');
    for (let i = 0; i < 16; i++) b += G(360, 480, 1, `<path d="M0 0L900 -64L900 64z" fill="#ffd23f" opacity="${n(.2 * fade(t, .1))}" transform="rotate(${n(i * 22.5 + t * 26)})"/>`);
    for (let i = 0; i < 48; i++) { const a = rnd(i) * 6.28, v = 200 + rnd(i + 9) * 460, tt = Math.max(0, t - .9), x = 360 + Math.cos(a) * v * Math.min(tt, 1.2), y = 480 + Math.sin(a) * v * Math.min(tt, 1.2) + tt * tt * 140; if (tt > 0) b += Rot(t * 200 + i * 40, x, y, R(x - 8, y - 5, 16, 10, 2, ['#ffd23f', '#39d98a', '#ef6ea3', '#5ec2f0', '#fff'][i % 5], S(2.5))); }
    b += Pop(t, 0, 360, 240, fit1(360, 280, str(d.title, 'LEVEL UP!'), { f: 'title', size: 124, a: 'middle', fill: '#ffd23f', st: INK, sw: 16, maxW: 660 }));
    const bs = sw ? 1 + .4 * Math.exp(-7 * (t - .9)) : 1;
    b += G(360, 490, bs, Pop(t, .3, 0, 0, C(0, 0, 150, '#ffd23f', S(9)) + C(0, 0, 122, '#ff9f1c', S(6)) + T(0, -64, 'NÍVEL', { f: 'title', size: 32, a: 'middle', fill: '#fff', st: INK, sw: 6 }) + T(0, 62, String(sw ? to : from), { f: 'title', size: 124, a: 'middle', fill: '#fff', st: INK, sw: 12 })));
    evt(.9, 'alert');
    arr(d.stats).slice(0, 4).forEach((s, i) => {
      const y = 700 + i * 88, tk = 1.1 + i * .25, v = lerp(num(s.from, 0), num(s.to, 10), ease((t - tk - .1) / .6));
      b += Slide(t, tk, -120, 0, R(60, y, 600, 72, 18, '#ffffffee', S(6)) + fit1(84, y + 47, str(s.label), { size: 28, w: 700, maxW: 260 }) + R(360, y + 22, 180, 28, 10, '#e2e5ea', S(4)) + R(363, y + 25, 174 * cl(v / Math.max(1, num(s.max, 100))), 22, 8, '#39d98a') + T(640, y + 50, '+' + Math.round(num(s.to, 10) - num(s.from, 0)), { f: 'title', size: 36, a: 'end', fill: '#2f9e62' }));
    });
    if (d.reward) b += Pop(t, 2.1, 360, 1090, R(90, 1056, 540, 76, 38, '#39d98a', S(7)) + fit1(360, 1108, str(d.reward), { f: 'title', size: 36, a: 'middle', maxW: 490 }));
    return b;
  }, 'Subida de nível com raios, confete, número virando de from para to, barras de atributos e recompensa.',
  { title: 'LEVEL UP!', from: 3, to: 4, stats: [{ label: 'Coragem', from: 12, to: 18, max: 40 }, { label: 'Gambiarra', from: 30, to: 41, max: 50 }, { label: 'Fôlego', from: 8, to: 9, max: 40 }], reward: 'DESBLOQUEOU: FITA DUPLA' });

  reg('game_over', 'card', (t, d) => {
    const dev = o_dev(cur.o), sec = num(d.countdown, 9), left = Math.max(0, Math.ceil(sec - Math.max(0, t - 1.6)));
    let b = dev === 'hand' ? dimBg(.7 * fade(t, 0, .2)) : GR(0, 0, 720, 1280, 0, '#7a1f18', '#14182a');
    for (let i = 0; i < 22; i++) { const y = (rnd(i) * 1400 + t * (70 + rnd(i + 4) * 90)) % 1400 - 60; b += P(`M${n(rnd(i + 9) * 720)} ${n(y)}q10 16 0 24-10-8 0-24z`, '#ff5a4d', 'opacity=".35"'); }
    [...str(d.line1, 'GAME')].forEach((c, i, a) => { const tk = .05 + i * .1, x = 360 + (i - (a.length - 1) / 2) * Math.min(124, 640 / a.length), y = 400; const k = spr(t - tk); if (t > tk) { evt(tk, 'alert'); b += T(x, y - (1 - k) * 700, c, { f: 'title', size: 196, a: 'middle', fill: '#ff3b30', st: '#fff', sw: 12 }); } });
    [...str(d.line2, 'OVER')].forEach((c, i, a) => { const tk = .5 + i * .1, x = 360 + (i - (a.length - 1) / 2) * Math.min(124, 640 / a.length), y = 590; const k = spr(t - tk); if (t > tk) b += Rot(i === 3 ? Math.sin(t * 3) * 6 + 8 : 0, x, y, T(x, y - (1 - k) * 700, c, { f: 'title', size: 196, a: 'middle', fill: '#ff3b30', st: '#fff', sw: 12 })); });
    // caveira
    b += Pop(t, 1, 360, 760, G(360, 760 + Math.sin(t * 2) * 6, 1, C(0, 0, 92, '#fff', S(8)) + R(-48, 62, 96, 64, 14, '#fff', S(8)) + E(-36, -6, 26, 30, INK) + E(36, -6, 26, 30, INK) + (blink(t, .7) ? C(-36, -6, 6, '#ff3b30') + C(36, -6, 6, '#ff3b30') : '') + P('M0 26l-12 24h24z', INK) + [-24, 0, 24].map(x => L(x, 82, x, 122, INK, 5)).join('')));
    b += Op(fade(t, 1.3), fitPara(360, 960, str(d.reason), { size: 32, w: 700, a: 'middle', fill: '#fff', maxW: 660, maxH: 78, lhk: 1.15, min: 18 }).svg);
    b += Op(fade(t, 1.6), T(360, 1056, 'CONTINUAR?', { f: 'title', size: 62, a: 'middle', fill: '#ffd23f', st: INK, sw: 8 }) + T(360, 1168, String(left), { f: 'title', size: 104, a: 'middle', fill: blink(t, 1) ? '#fff' : '#ffd23f', st: INK, sw: 10 }));
    return b + Op(fade(t, 1.6), fit1(360, 1226, str(d.cost, 'insira 1 ficha'), { size: 22, w: 600, a: 'middle', fill: '#cfd6e4', maxW: 660 }));
  }, 'Fim de jogo: letras caindo uma a uma, caveira, motivo e contagem CONTINUAR?.',
  { reason: 'Morreu de teimosia', countdown: 9, cost: 'insira 1 ficha' });

  reg('poll_live', 'card', (t, d) => {
    const dev = o_dev(cur.o), opts = arr(d.options).slice(0, 4), tot = opts.reduce((a, o2) => a + Math.max(0, num(o2.pct, 0)), 0) || 100, dur = num(d.dur, 3.2);
    let b = dev === 'hand' ? dimBg(.6 * fade(t, 0, .2)) : backdrop(t, '#2f7bf6', '#123a86');
    b += Pop(t, 0, 360, 150, R(40, 110, 170, 54, 12, '#d9281e', S(6)) + (blink(t, 1) ? C(70, 137, 9, '#fff') : '') + T(90, 150, 'AO VIVO', { f: 'title', size: 30, fill: '#fff' }) + R(226, 110, 454, 54, 12, '#fff', S(6)) + T(662, 148, Math.floor(num(d.votes, 12834) * (ease(t / dur) * .8 + .2)).toLocaleString('pt-BR') + ' votos', { size: 28, w: 700, a: 'end' }));
    b += Pop(t, .15, 360, 280, R(40, 190, 640, 200, 22, '#ffd23f', S(7)) + fitPara(360, 260, str(d.question), { f: 'title', size: 62, a: 'middle', maxW: 590, maxH: 160, lhk: 1.08, min: 28 }).svg);
    const k = ease((t - .5) / dur), wave = cl((t - .5) / dur), cols = ['#ef3b2e', '#39d98a', '#ffb020', '#ef6ea3'], max = Math.max(...opts.map(o2 => num(o2.pct, 0)));
    opts.forEach((o2, i) => {
      const rh = Math.min(240, 790 / Math.max(1, opts.length)), y = 430 + i * rh, ch = rh - 22, p = (num(o2.pct, 0) / tot * 100), jig = (1 - wave) * Math.sin(t * 6 + i * 2) * 14, v = cl(p * k + jig * (t > .5 ? 1 : 0), 0, 100), win = wave >= 1 && num(o2.pct, 0) === max, c = o2.color || cols[i % 4];
      b += Slide(t, .3 + i * .1, 120 * (i % 2 ? 1 : -1), 0, R(40, y, 640, ch, 22, '#fff', win ? S(blink(t, 2) ? 9 : 6, '#ffd23f') : S(6)) + fit1(64, y + ch * .4, str(o2.label), { f: 'title', size: Math.min(58, ch * .32), maxW: 450 }) + T(656, y + ch * .42, Math.round(v) + '%', { f: 'title', size: Math.min(72, ch * .38), a: 'end', fill: c, st: INK, sw: 5 }) + R(62, y + ch * .56, 596, ch * .34, 16, '#e2e5ea', S(4)) + R(66, y + ch * .56 + 4, 588 * v / 100, ch * .34 - 8, 12, c));
    });
    return b;
  }, 'Votação ao vivo: pergunta, opções {label, pct} com barras disputando até o resultado e contador de votos.',
  { question: 'O ZÉ DEVE ABRIR A ESCOTILHA?', votes: 12834, dur: 3.2, options: [{ label: 'SIM, COM FÉ', pct: 61 }, { label: 'NÃO, PELO AMOR', pct: 27 }, { label: 'CHAMA O GATO', pct: 12 }] });
})();
