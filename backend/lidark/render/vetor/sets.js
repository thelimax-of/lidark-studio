/* sets.js — cenários do motor vetorial (agente MUNDO).
   Cada cenário: V.sets.nome(t, {tod:"day|night|alert", state:{...}}) -> string SVG em coordenadas do mundo (720x1280).
   Desenhado de x=-300 a 1020 e y=-300 a 1700 para aguentar zoom 3x e pan sem vazio.
   Chão/centro livres para o elenco (pés em y~1090). Determinístico: só V.rnd(seed).
   A parte fixa de cada cenário é montada uma vez e guardada em cache; só o que mexe é refeito por quadro. */
(function () {
  const V = window.V;
  V.sets = V.sets || {};
  V.docs = V.docs || {};
  V.docs.sets = V.docs.sets || {};
  const rnd = V.rnd;
  const O = '#14182a';
  const FH = "Impact, 'Arial Black', sans-serif";
  const FS = "'Segoe UI', Arial, sans-serif";
  const n2 = v => Math.round(v * 100) / 100;

  /* ---------- primitivas ---------- */
  const st = (sw) => sw ? `stroke="${O}" stroke-width="${sw}" stroke-linejoin="round"` : 'stroke="none"';
  const at = (sw, ex) => ex.includes('stroke="') ? `stroke-width="${sw}" stroke-linejoin="round" ${ex}` : `${st(sw)} ${ex}`;
  const R = (x, y, w, h, f, rx = 8, sw = 5, ex = '') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${f}" ${at(sw, ex)}/>`;
  const C = (x, y, r, f, sw = 5, ex = '') => `<circle cx="${x}" cy="${y}" r="${r}" fill="${f}" ${at(sw, ex)}/>`;
  const E = (x, y, rx, ry, f, sw = 5, ex = '') => `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${f}" ${at(sw, ex)}/>`;
  const P = (d, f, sw = 5, ex = '') => `<path d="${d}" fill="${f}" ${at(sw, ex)}/>`;
  const L = (d, c = O, w = 5, ex = '') => `<path d="${d}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" ${ex}/>`;
  const G = (tr, ...c) => `<g transform="${tr}">${c.join('')}</g>`;
  const T = (x, y, s, size, f = O, o = {}) => `<text x="${x}" y="${y}" font-size="${size}" fill="${f}" stroke="none" text-anchor="${o.a || 'middle'}" font-family="${o.font || FH}"${o.w ? ` font-weight="${o.w}"` : ''}${o.ls ? ` letter-spacing="${o.ls}"` : ''}${o.r ? ` transform="rotate(${o.r} ${x} ${y})"` : ''}>${s}</text>`;
  const TS = (x, y, s, size, f = O, o = {}) => T(x, y, s, size, f, Object.assign({ font: FS, w: 700 }, o));
  const rep = (n, fn) => { let s = ''; for (let i = 0; i < n; i++) s += fn(i); return s; };

  /* gradientes verticais compartilhados: mesmo par de cores = mesmo id */
  const grads = {};
  const gv = (a, b) => { const id = 'vg_' + (a + b).replace(/#/g, ''); grads[id] = `<linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient>`; return `url(#${id})`; };
  const radial = (a, b) => { const id = 'vr_' + (a + b).replace(/#/g, ''); grads[id] = `<radialGradient id="${id}"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></radialGradient>`; return `url(#${id})`; };
  const fade = (c) => { const id = 'vf_' + c.replace(/#/g, ''); grads[id] = `<radialGradient id="${id}"><stop offset="0" stop-color="${c}" stop-opacity=".85"/><stop offset="1" stop-color="${c}" stop-opacity="0"/></radialGradient>`; return `url(#${id})`; };
  const defsFixos = `<pattern id="vp_hz" width="44" height="44" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="44" height="44" fill="#ffd23f"/><rect width="22" height="44" fill="${O}"/></pattern>`;

  /* ---------- peças de cenografia ---------- */
  const hazard = (x, y, w, h, rx = 4) => R(x, y, w, h, 'url(#vp_hz)', rx, 5);
  const tapeBit = (x, y, r = 0, c = '#e8dcae') => G(`translate(${x} ${y}) rotate(${r})`, `<rect x="-22" y="-8" width="44" height="16" fill="${c}" opacity=".9" stroke="${O}" stroke-width="2"/>`);
  const ductPatch = (x, y, r = 0, w = 70) => G(`translate(${x} ${y}) rotate(${r})`, R(-w / 2, -13, w, 26, '#b9bdc4', 2, 4), L(`M${-w / 2 + 6} -4h${w * .4}M${-w * .1} 6h${w * .4}`, '#8c9199', 3), R(-13, -w / 2 + 6, 26, w - 12, '#c6cad0', 2, 4));
  const note = (x, y, w, h, title, lines, f = '#fff4d6', r = 0) => G(`rotate(${r} ${x + w / 2} ${y + h / 2})`, R(x, y, w, h, f, 3, 4),
    title ? TS(x + w / 2, y + 22, title, 15, '#c8352b') : '',
    lines.map((s, i) => TS(x + 9, y + 42 + i * 18, s, 13, O, { a: 'start', w: 600 })).join(''), tapeBit(x + w / 2, y, r * -1));
  const sticky = (x, y, s1, s2, f = '#ffe66b', r = 0) => G(`rotate(${r} ${x + 40} ${y + 40})`, R(x, y, 82, 76, f, 2, 4), TS(x + 41, y + 34, s1, 13), s2 ? TS(x + 41, y + 52, s2, 13) : '');
  const photo = (x, y, kind, r = 0, s = 1) => {
    const w = 84, h = 96;
    const sc = {
      cao: R(8, 8, 68, 62, '#8fd6ff', 0, 0) + P('M26 58q-4-30 16-30t16 30z', '#c98d4e', 3) + C(32, 26, 7, '#a86f35', 3) + C(52, 26, 7, '#a86f35', 3) + C(37, 38, 2.5, O, 0) + C(47, 38, 2.5, O, 0) + E(42, 44, 4, 3, O, 0),
      familia: R(8, 8, 68, 62, '#ffd9a0', 0, 0) + C(28, 34, 9, '#e8b98a', 3) + C(54, 32, 10, '#c98d5e', 3) + C(41, 44, 7, '#efe3c8', 3) + P('M18 70q10-26 20 0zM44 70q10-28 20 0z', '#3a82b4', 3),
      praia: R(8, 8, 68, 34, '#6fd3ff', 0, 0) + R(8, 42, 68, 12, '#2a8fd8', 0, 0) + R(8, 54, 68, 16, '#f7dc8a', 0, 0) + C(60, 22, 8, '#ffd23f', 3),
      foguete: R(8, 8, 68, 62, '#20306f', 0, 0) + P('M42 14q14 16 8 40h-16q-6-24 8-40z', '#f4f4f2', 3) + C(42, 34, 5, '#6fd3ff', 3) + P('M36 54l6 14 6-14z', '#ff9a3c', 3),
      ze: R(8, 8, 68, 62, '#a6e3a1', 0, 0) + C(42, 38, 18, '#efe3c8', 3) + P('M24 34a18 18 0 0 1 36 0q-18-8-36 0z', '#24412c', 3) + C(36, 40, 2.5, O, 0) + C(48, 40, 2.5, O, 0) + L('M36 48q6 5 12 0', O, 2.5),
    }[kind] || '';
    return G(`translate(${x} ${y}) rotate(${r}) scale(${s})`, R(0, 0, w, h, '#fff', 3, 4), sc, tapeBit(42, -2, -r * .5));
  };
  const poster = (x, y, w, h, bg, t1, t2, r = 0, ic = '') => G(`rotate(${r} ${x + w / 2} ${y + h / 2})`, R(x, y, w, h, bg, 4, 5), ic, T(x + w / 2, y + h - (t2 ? 36 : 14), t1, Math.min(26, w * .17), '#fff'), t2 ? T(x + w / 2, y + h - 12, t2, Math.min(18, w * .12), '#ffd23f') : '', C(x + 8, y + 8, 3, '#d9483b', 2), C(x + w - 8, y + 8, 3, '#d9483b', 2));
  const sign = (x, y, w, h, bg, s, fg = '#fff', size = 26, r = 0) => G(`rotate(${r} ${x + w / 2} ${y + h / 2})`, R(x, y, w, h, bg, 8, 5), T(x + w / 2, y + h / 2 + size * .36, s, size, fg));
  const warn = (x, y, s = 1) => G(`translate(${x} ${y}) scale(${s})`, R(-42, -42, 84, 84, '#ffd23f', 10, 5), P('M0 -28L30 24H-30z', O, 0), T(0, 20, '!', 32, '#ffd23f'));
  const vent = (x, y, w, h) => R(x, y, w, h, '#aab6c4', 6, 5) + rep(Math.floor((h - 12) / 12), i => L(`M${x + 10} ${y + 14 + i * 12}h${w - 20}`, O, 4));
  const rivets = (x, y, w, h, c = '#7b8ba0') => [[x + 12, y + 12], [x + w - 12, y + 12], [x + 12, y + h - 12], [x + w - 12, y + h - 12]].map(p => C(p[0], p[1], 5, c, 3)).join('');
  const cable = (x1, y1, x2, y2, sag, c, w = 10) => { const d = `M${x1} ${y1}Q${(x1 + x2) / 2} ${(y1 + y2) / 2 + sag} ${x2} ${y2}`; return L(d, O, w + 6) + L(d, c, w); };
  const pipeH = (y, h, c, x1 = -320, x2 = 1040) => R(x1, y, x2 - x1, h, c, 0, 5) + `<rect x="${x1}" y="${y + h * .2}" width="${x2 - x1}" height="${h * .2}" fill="#fff" opacity=".45"/>`;
  const pipeV = (x, w, c, y1 = -320, y2 = 880) => R(x, y1, w, y2 - y1, c, 0, 5) + `<rect x="${x + w * .2}" y="${y1}" width="${w * .2}" height="${y2 - y1}" fill="#fff" opacity=".45"/>`;
  const clampH = (x, y, h, c = '#8d99a8') => R(x, y - 10, 30, h + 20, c, 5, 4);
  const screen = (x, y, w, h, bg = '#0f2a46', c = '') => R(x - 8, y - 8, w + 16, h + 16, '#55697f', 8, 5) + R(x, y, w, h, bg, 4, 4) + c;
  const crate = (x, y, w, h, f, s, fg = O) => R(x, y, w, h, f, 5, 5) + L(`M${x} ${y + h * .22}h${w}`, O, 3) + T(x + w / 2, y + h * .72, s, Math.min(h * .34, 26, w * .22), fg);
  const handrail = (y, c = '#ffd23f', x1 = -320, x2 = 1040, step = 240) => R(x1, y, x2 - x1, 16, c, 8, 4) + rep(Math.ceil((x2 - x1) / step), i => R(x1 + 60 + i * step, y - 4, 16, 34, '#8d99a8', 4, 4));
  const shelfRow = (x, y, w, c = '#b0bcc9') => R(x, y, w, 14, c, 3, 4);
  const frame = (x, y, w, h, c, f = '#8d6a45') => R(x, y, w, h, f, 4, 5) + `<rect x="${x + 8}" y="${y + 8}" width="${w - 16}" height="${h - 16}" fill="#fff" stroke="${O}" stroke-width="3"/>` + c;
  const logoAstra = (x, y, s = 1) => G(`translate(${x} ${y}) scale(${s})`, C(0, 0, 34, '#14325f', 5), P('M0 -22l20 36h-40z', '#ffd23f', 3), L('M-34 8q34 -22 68 -8', '#ff5a4d', 5), T(0, 22, 'A9', 14, '#fff'));

  /* comidas e tralhas que flutuam na estação */
  const mini = {
    biscoito: C(0, 0, 18, '#d8a463', 4) + C(-6, -5, 3, '#6b3f1e', 0) + C(6, 3, 3, '#6b3f1e', 0) + C(-3, 8, 2.5, '#6b3f1e', 0),
    meia: P('M-10 -24h20v24l16 8q8 10-4 12h-20q-12-4-12-14z', '#fff', 4) + L('M-10 -14h20', '#d9483b', 5),
    caneta: R(-30, -4, 60, 8, '#2a8fd8', 3, 3) + P('M30 -4l12 4-12 4z', '#efe3c8', 3),
    ervilha: C(0, 0, 9, '#67c15e', 3),
    macarrao: L('M-24 0q8-14 16 0t16 0 16 0', '#f7dc8a', 7) ,
    gota: C(0, 0, 11, '#8fdcff', 3) + C(-3, -4, 3, '#fff', 0),
    maca: C(0, 0, 18, '#e8483b', 4) + L('M0 -18q2-10 8-12', O, 3),
    sache: R(-20, -24, 40, 48, '#ffb545', 5, 4) + TS(0, 5, 'SUCO', 11) ,
    bola: C(0, 0, 16, '#fff', 4) + L('M-14 -6q14 8 28 0M-14 6q14-8 28 0', '#d9483b', 2.5),
    parafuso: R(-5, -14, 10, 24, '#aab6c4', 2, 3) + R(-11, -20, 22, 8, '#8d99a8', 2, 3),
  };
  const floats = (t, list) => list.map((it, i) => {
    const a = rnd(i * 7 + 3) * 6.28, x = it[1] + Math.sin(t * .45 + a) * 26, y = it[2] + Math.cos(t * .37 + a) * 18, ro = (t * (10 + rnd(i) * 22) + a * 40) % 360;
    return G(`translate(${n2(x)} ${n2(y)}) rotate(${n2(ro)}) scale(${it[3] || 1})`, mini[it[0]]);
  }).join('');

  /* animadinhos */
  const led = (x, y, c, t, ph = 0, r = 7, rate = 2.2) => C(x, y, r, Math.sin(t * rate + ph * 9) > 0 ? c : '#3a4358', 3);
  const leds = (x, y, n, t, seed = 1, dx = 22) => rep(n, i => led(x + i * dx, y, ['#39d98a', '#ffd23f', '#ff5a4d', '#6fd3ff'][Math.floor(rnd(seed + i) * 4)], t, rnd(seed * 3 + i), 6, 1.5 + rnd(seed + i * 2) * 4));
  const gauge = (x, y, r, val, lab) => {
    const a = -130 + V.cl(val, 0, 1) * 260;
    return C(x, y, r, '#f4f4f2', 5) + rep(9, i => { const q = (-130 + i * 32.5 - 90) * Math.PI / 180; return L(`M${n2(x + Math.cos(q) * r * .72)} ${n2(y + Math.sin(q) * r * .72)}L${n2(x + Math.cos(q) * r * .9)} ${n2(y + Math.sin(q) * r * .9)}`, i > 5 ? '#39a96b' : i < 2 ? '#d9483b' : O, 3); })
      + G(`translate(${x} ${y}) rotate(${n2(a)})`, L(`M0 ${r * .14}V${-r * .72}`, '#d9483b', 4)) + C(x, y, r * .1, O, 0) + (lab ? TS(x, y + r * .55, lab, r * .24) : '');
  };
  const fan = (x, y, r, t, sp = 400, c = '#c8cfd8') => C(x, y, r, '#2d3a52', 5) + G(`translate(${x} ${y}) rotate(${n2(t * sp % 360)})`, rep(4, i => P(`M0 0Q${r * .35} ${-r * .75} ${r * .05} ${-r * .9}Q${-r * .45} ${-r * .6} 0 0z`, c, 3, `transform="rotate(${i * 90})"`))) + C(x, y, r * .15, '#ffd23f', 3);
  const dangle = (x, y, len, t, ph, inner) => G(`translate(${x} ${y}) rotate(${n2(Math.sin(t * 1.3 + ph) * 7)})`, L(`M0 0V${len}`, O, 3), G(`translate(0 ${len})`, inner));
  const steamPuff = (x, y, t, seed = 1, n = 7, up = 90) => rep(n, i => { const f = (t * .7 + i / n + rnd(seed + i) * .2) % 1; return `<circle cx="${n2(x + Math.sin(i * 2.3 + t) * 12 * f)}" cy="${n2(y - f * up)}" r="${n2(6 + f * 16)}" fill="#fff" opacity="${n2((1 - f) * .55)}"/>`; });
  const drip = (x, y, h, t, seed = 1, c = '#8fdcff') => { const f = (t * .8 + rnd(seed)) % 1; return E(x, n2(y + f * f * h), 5, 8, c, 2.5); };
  const flyes = (t, x, y, n = 3, sp = 40) => rep(n, i => { const a = t * (3 + i) + i * 2; return G(`translate(${n2(x + Math.sin(a) * sp + Math.sin(a * 2.1) * 10)} ${n2(y + Math.cos(a * 1.3) * sp * .7)})`, E(0, 0, 3.5, 3, O, 0), E(-3, -3, 3, 2, '#fff', 1, 'opacity=".8"'), E(3, -3, 3, 2, '#fff', 1, 'opacity=".8"')); });
  const stink = (x, y, t, ph = 0, c = '#8fbf4e') => { const w = Math.sin(t * 2 + ph) * 7; return L(`M${x} ${y}q${n2(12 + w)} -18 0 -36t${n2(-w)} -36 0 -36`, c, 5, 'opacity=".75"'); };
  const prop = (nome, t, x, y, s = 1, state = {}, ex = '') => `<g transform="translate(${x} ${y}) scale(${s}) ${ex}">${(V.props[nome] || (() => ''))(t, { state })}</g>`;

  /* Terra: k>1 desenha continentes menores e mais numerosos, para planetas enormes não virarem uma mancha */
  const tileTerra = {};
  function ladrilho(noite) {
    if (tileTerra[noite]) return tileTerra[noite];
    const land = noite ? '#28436f' : '#46b36b', land2 = noite ? '#22396a' : '#8fce62', deserto = noite ? '#2a4a7a' : '#e9c46a';
    const cid = noite ? rep(16, i => C(n2(-150 + rnd(i) * 320), n2(-90 + rnd(i + 30) * 190), 2.2, '#ffd97a', 0)) : '';
    return tileTerra[noite] =
      P('M-130 -80q40-44 96-30t72 42-40 34 6 44-40 44-40-34-44-10-34-60z', land, 4) + P('M-96 -46q24-14 50-2t-6 34-40 4z', land2, 0) + P('M-50 40q16-18 20 6t-20 18z', deserto, 0) +
      P('M70 -60q50-26 96-4t20 56-52 22-40 44-34-44 10-74z', land, 4) + P('M100 -30q24-10 40 6t-22 20-18-26z', deserto, 0) +
      P('M-140 70q24-14 40 6t-20 34-20-40z', land, 4) + P('M90 96q18-10 30 4t-16 22-14-26z', land, 4) + C(-10, -110, 6, land, 3) + C(20, 120, 5, land, 3) + cid +
      (noite ? '' : L('M-120 -30q44-18 96 0M20 34q44-14 80 0M-150 100q30-10 60 0M60 -96q34-10 70 0', '#fff', 11, 'opacity=".8"'));
  }
  function earth(id, cx, cy, r, t, tod, k = 1) {
    const noite = tod === 'night', q = r / 150 / k, K = Math.ceil(k), off = (t * 2) % 340;
    let m = '';
    for (let j = -K; j <= K; j++) for (let i = -K - 1; i <= K; i++) m += G(`translate(${n2(i * 340 + off + (j % 2) * 150)} ${j * 250})`, ladrilho(noite));
    return `<clipPath id="clip_${id}"><circle cx="${cx}" cy="${cy}" r="${r}"/></clipPath>` +
      C(cx, cy, r, radial(noite ? '#3a68b0' : '#6fd3ff', noite ? '#142a63' : '#1a64b0'), 0) +
      `<g clip-path="url(#clip_${id})">${G(`translate(${cx} ${cy}) scale(${n2(q)})`, m)}</g>` +
      `<circle cx="${cx}" cy="${cy}" r="${r + 5}" fill="none" stroke="#9fe4ff" stroke-width="6" opacity=".6"/>`;
  }
  const starfield = (seed, n, x, y, w, h) => rep(n, i => C(n2(x + rnd(seed + i) * w), n2(y + rnd(seed + i + 500) * h), n2(1.4 + rnd(seed + i + 900) * 2.4), '#fff', 0));
  const twinkle = (t, seed, n, x, y, w, h) => rep(n, i => { const f = Math.sin(t * (1 + rnd(i + seed) * 2) + i); const s = 5 + f * 3; return G(`translate(${n2(x + rnd(seed + i * 3) * w)} ${n2(y + rnd(seed + i * 5) * h)})`, `<path d="M0 ${-s}L${s * .25} ${-s * .25}L${s} 0L${s * .25} ${s * .25}L0 ${s}L${-s * .25} ${s * .25}L${-s} 0L${-s * .25} ${-s * .25}z" fill="#fff" opacity="${n2(.5 + f * .4)}"/>`); });

  /* escotilha com vista para fora */
  function porthole(id, x, y, r, t, tod, ex = 60) {
    return C(x, y, r + 32, '#c9d6e2', 7) + C(x, y, r + 4, '#0a1022', 6) +
      `<clipPath id="clip_${id}p"><circle cx="${x}" cy="${y}" r="${r}"/></clipPath>` +
      `<g clip-path="url(#clip_${id}p)">${starfield(40, 16, x - r, y - r, r * 2, r * 2)}${earth(id, x + ex, y + r * .6, r, t, tod)}</g>` +
      rep(8, i => { const a = i * Math.PI / 4; return C(n2(x + Math.cos(a) * (r + 18)), n2(y + Math.sin(a) * (r + 18)), 7, '#7b8ba0', 3); }) +
      L(`M${x - r * .6} ${y - r * .3}q${r * .3} ${-r * .4} ${r * .7} ${-r * .4}`, '#fff', 7, 'opacity=".5"');
  }

  /* parede e piso modulares da estação */
  const wallSt = (a, b, seam, y2 = 890) => R(-340, -340, 1400, y2 + 340, gv(a, b), 0, 0) +
    rep(8, i => L(`M${-300 + i * 200} -320V${y2}`, seam, 4)) + L(`M-340 280H1060M-340 -40H1060`, seam, 4) +
    rep(8, i => rep(3, j => C(-300 + i * 200 + 16, 100 + j * 320, 4, seam, 0) + C(-300 + i * 200 - 16, 100 + j * 320, 4, seam, 0)));
  const floorSt = (a, b, line, y0 = 880) => R(-340, y0, 1400, 900, gv(a, b), 0, 0) +
    rep(13, i => L(`M${360 + (i - 6) * 130} ${y0}L${360 + (i - 6) * 300} 1760`, line, 4)) +
    [0, 50, 120, 220, 370, 590].map(d => L(`M-340 ${y0 + d}H1060`, line, 4)).join('') +
    rep(11, i => C(n2(rnd(i + 70) * 1300 - 300), n2(y0 + 16 + rnd(i + 80) * 700), 4 + rnd(i) * 4, O, 0, 'opacity=".15"')) +
    L(`M-340 ${y0}H1060`, O, 6) + `<rect x="-340" y="${y0 + 3}" width="1400" height="10" fill="#fff" opacity=".22"/>`;
  const ceiling = (c = '#8d99a8', h = 150) => R(-340, -340, 1400, 340 + h - 40, c, 0, 5) +
    rep(7, i => R(-290 + i * 210, h - 58, 150, 22, '#f8fbff', 8, 4)) +
    pipeH(h - 32, 18, '#ff8a3c') + pipeH(h - 14, 14, '#ffd23f') +
    rep(9, i => clampH(-280 + i * 170, h - 32, 32));

  /* ---------- iluminação comum: day/night/alert ---------- */
  function luz(t, tod, cfg) {
    let s = '';
    if (tod === 'night') {
      s += `<rect x="-400" y="-400" width="1520" height="2200" fill="${cfg.noite || '#1b2478'}" opacity="${cfg.noiteOp || .2}"/>`;
    } else if (tod === 'alert') {
      const pulse = .5 + .5 * Math.sin(t * 6.3);
      s += `<rect x="-400" y="-400" width="1520" height="2200" fill="#ff2a2a" opacity="${n2(.05 + pulse * .17)}"/>`;
      (cfg.sirenes || [[120, 170], [600, 170]]).forEach((b, i) => {
        const a = (t * 200 + i * 130) % 360;
        const on = Math.sin(t * 6.3) > -.3;
        s += G(`translate(${b[0]} ${b[1]})`,
          G(`rotate(${n2(a)})`, `<path d="M0 0L520 -130L520 130z" fill="#ff4a3a" opacity=".22"/><path d="M0 0L-520 -130L-520 130z" fill="#ff4a3a" opacity=".22"/>`),
          R(-30, -34, 60, 14, '#55697f', 4, 4), P('M-24 -20h48v14a24 24 0 0 1-48 0z', on ? '#ff5a4d' : '#a82b22', 5), L('M-12 -12v8', '#fff', 5, 'opacity=".7"'));
      });
    }
    return s;
  }

  /* registrador: fn(tod, state) prepara o que é fixo e devolve (t)=>svg */
  const cache = {};
  function def(nome, desc, data, cfg, fn) {
    V.sets[nome] = (t, o) => {
      o = o || {};
      const tod = (o.tod === 'night' || o.tod === 'alert') ? o.tod : 'day', state = o.state || {};
      const key = nome + '|' + tod + '|' + JSON.stringify(state);
      const f = cache[key] || (cache[key] = fn(tod, state));
      const corpo = f(t);
      return `<defs>${defsFixos}${Object.values(grads).join('')}</defs>${corpo}${luz(t, tod, cfg)}`;
    };
    V.docs.sets[nome] = { desc, data };
  }

  /* ================= ESTAÇÃO ASTRA-9 ================= */

  def('station_corridor', 'Corredor principal da estação Astra-9: escotilha com a Terra, cano de oxigênio, avisos e tralha flutuando.',
    { state: { leak: false, door_open: false } }, {}, (tod, s) => {
      const a = wallSt('#4aa3dc', '#2f77ae', '#215a88') + ceiling() +
        R(-60, 170, 200, 660, '#58afe2', 16, 5) + R(580, 170, 200, 660, '#58afe2', 16, 5) + rivets(-60, 170, 200, 660) + rivets(580, 170, 200, 660) +
        /* porta do módulo B, fora do quadro principal */
        R(-290, 200, 200, 680, '#8d99a8', 14, 6) + hazard(-300, 176, 220, 26) +
        R(820, 200, 200, 680, '#8d99a8', 14, 6) + hazard(810, 176, 220, 26) + T(920, 300, 'MÓDULO C', 34, O) + T(-190, 300, 'MÓDULO B', 34, O) +
        (s.door_open ? R(-276, 214, 172, 666, '#0d1830', 4, 4) : R(-276, 214, 172, 666, '#b7c3cf', 4, 4) + L('M-190 214V880', O, 5)) +
        R(838, 214, 164, 666, '#b7c3cf', 4, 4) + L('M920 214V880', O, 5);
      const b =
        /* quadro de segurança */
        R(14, 180, 156, 120, '#fff', 8, 5) + T(92, 212, 'DIAS SEM', 24, O) + T(92, 238, 'ACIDENTE', 24, O) + R(66, 244, 52, 46, O, 6, 0) + T(92, 283, '0', 40, '#ff5a4d') +
        note(14, 316, 156, 150, 'TAREFAS DO ZÉ', ['1. Não apertar nada', '2. Sério, nada', '3. Regar a alface', '4. Devolver a fita', '5. NÃO APERTAR'], '#fff4d6', -3) +
        photo(94, 480, 'cao', -6) + sticky(4, 490, 'CADÊ MEU', 'BISCOITO?', '#ffb0c8', 5) +
        warn(650, 226) + R(556, 290, 156, 160, '#c8cfd8', 8, 5) + T(634, 320, 'DISJUNTORES', 19) + rep(2, j => rep(4, i => R(568 + i * 34, 334 + j * 52, 24, 40, '#fff', 3, 3) + R(574 + i * 34, 340 + j * 52, 12, 14, i % 3 ? '#39d98a' : '#ff5a4d', 2, 2))) +
        sticky(552, 474, 'ESTE AQUI', 'DÁ CHOQUE', '#ffe66b', -4) + photo(638, 470, 'familia', 5) +
        vent(180, 730, 110, 80) + vent(430, 730, 110, 80) + logoAstra(310, 790, 1.1) + T(410, 804, 'A-9', 30, '#fff');
      const c =
        pipeH(600, 62, '#c8cfd8') + T(370, 642, 'O₂ — OXIGÊNIO', 30, O, { ls: 3 }) + G('rotate(-3 640 690)', R(575, 668, 140, 30, '#ffd23f', 4, 4), TS(645, 689, 'NÃO É CORRIMÃO', 14)) +
        clampH(170, 600, 62) + clampH(540, 600, 62) + clampH(-120, 600, 62) + clampH(800, 600, 62) + ductPatch(90, 630, -8) + TS(92, 682, 'TEMPORÁRIO (2019)', 15, '#fff', { r: -3 }) +
        (s.leak ? C(622, 602, 8, O, 0) : ductPatch(622, 624, 12, 50)) +
        handrail(720, '#ffd23f') +
        /* lixeira e caixa do chão */
        R(14, 760, 100, 120, '#f0b429', 8, 5) + L('M14 800h100M14 840h100', O, 4) + T(64, 830, 'H₂O', 22, O) +
        R(600, 800, 120, 80, '#d9483b', 8, 5) + L('M640 800v-22h40v22', O, 5) + T(660, 854, 'FERRAMENTAS', 13, '#fff') +
        floorSt('#7f9ab5', '#4e6480', '#3d5068') + hazard(-320, 1500, 1360, 34, 0) +
        P('M90 1160h120v-22l50 44-50 44v-22h-120z', '#ffd23f', 4, 'opacity=".9"') + TS(150, 1190, 'SAÍDA', 18) +
        cable(-320, 1000, 110, 960, 70, '#d9483b', 9) + ductPatch(30, 985, 8, 60) + cable(1040, 1040, 620, 950, 70, '#2a8fd8', 9) +
        sticky(580, 1180, 'PISO', 'MOLHADO?', '#ffe66b', 8);
      return t => {
        const lamp = Math.sin(t * 13) * Math.sin(t * 3.1) > .86 ? `<rect x="80" y="92" width="150" height="22" rx="8" fill="${O}" opacity=".55"/>` : '';
        let jet = '';
        if (s.leak) jet = rep(30, i => { const f = (t * 1.8 + i * .07) % 1, q = (-18 - i * 5.3 % 34) * Math.PI / 180, d = f * 230; return `<circle cx="${n2(622 + Math.cos(q) * d)}" cy="${n2(602 - Math.abs(Math.sin(q + i)) * d * .75)}" r="${n2(3 + f * 11)}" fill="#dff4ff" opacity="${n2((1 - f) * .85)}"/>`; });
        return a + lamp + b + porthole('cor', 360, 330, 146, t, tod) + c + leds(570, 438, 6, t, 3, 26) + jet +
          dangle(330, 130, 60, t, 0, R(-22, 0, 44, 28, '#ffb0c8', 4, 3) + TS(0, 20, 'A-9', 13)) +
          G(`translate(235 742)`, rep(3, i => L(`M${i * 12} 0q${n2(Math.sin(t * 9 + i) * 8)} 16 0 34`, '#fff', 4))) +
          floats(t, [['biscoito', 130, 520], ['caneta', 560, 170, .9], ['ervilha', 200, 520], ['ervilha', 225, 545, .8], ['meia', 570, 520, .9], ['gota', 160, 440], ['macarrao', 530, 700, .9], ['parafuso', -150, 520], ['bola', 880, 620]]);
      };
    });

  def('station_cockpit', 'Cabine de comando: janelão com a Terra, painéis cheios de botões, radar e bugigangas da tripulação.',
    { state: { error: false } }, { sirenes: [[70, 150], [650, 150]] }, (tod, s) => {
      const a = wallSt('#3cb4b8', '#22858f', '#176a73') +
        /* teto de interruptores */
        R(-340, -340, 1400, 460, '#6d8299', 0, 5) + rep(26, i => R(-300 + i * 52, 62, 36, 40, '#dfe6ee', 4, 3) + L(`M${-282 + i * 52} 92V${i % 3 ? 72 : 84}`, O, 6)) +
        T(360, 40, 'NÃO MEXER AQUI TAMBÉM', 24, '#ffd23f', { ls: 2 });
      const b =
        /* moldura do janelão */
        P('M-300 150H1020V620H-300z', 'none', 0) + L('M-40 120V640M240 120V640M480 120V640M760 120V640', '#c9d6e2', 24) + L('M-40 120V640M240 120V640M480 120V640M760 120V640', O, 3, 'opacity=".5"') +
        R(-320, 118, 1360, 30, '#c9d6e2', 0, 5) + R(-320, 620, 1360, 34, '#c9d6e2', 0, 5) +
        sticky(30, 170, 'FREIO?', 'NÃO TEM', '#ffe66b', -5) + sticky(600, 165, 'LIGAR P/', 'A MÃE', '#ffb0c8', 6) + sticky(280, 170, 'NÃO É', 'GPS', '#b6f0a0', -3) +
        note(504, 280, 110, 110, 'ROTA', ['Direita', 'p/ sempre'], '#fff4d6', 3) + photo(120, 300, 'foguete', -4, .9);
      const c =
        /* console */
        P('M-340 700L-220 640H940L1060 700V900H-340z', '#5d7088', 6) +
        L('M-340 700H1060', '#fff', 5, 'opacity=".35"') +
        R(-340, 760, 1400, 150, '#7f93a9', 0, 5) + hazard(-320, 744, 1360, 18, 0) +
        floorSt('#567089', '#384c65', '#2c3d54') +
        /* poltronas laterais, viradas para o console */
        P('M-30 880V770q0-34 34-34h60q30 0 30 34V880z', '#d9483b', 6) + R(-50, 860, 170, 40, '#b03329', 12, 5) + R(26, 900, 20, 170, '#8d99a8', 4, 5) + R(-30, 1060, 130, 16, '#55697f', 6, 4) +
        P('M640 880V770q0-34 34-34h60q30 0 30 34V880z', '#d9483b', 6) + R(620, 860, 170, 40, '#b03329', 12, 5) + R(696, 900, 20, 170, '#8d99a8', 4, 5) + R(640, 1060, 130, 16, '#55697f', 6, 4) +
        R(10, 1120, 170, 90, '#f0b429', 8, 5) + T(95, 1178, 'SNACKS', 26) + cable(-320, 1100, 240, 1140, 40, '#7a5cff', 8) + cable(1040, 1180, 500, 1160, 50, '#39d98a', 8);
      return t => {
        const sw = ((t * 120) % 360);
        const err = s.error && Math.sin(t * 8) > 0;
        const radar = screen(30, 660, 170, 86, '#07332a', G(`translate(115 703)`, C(0, 0, 38, 'none', 2, 'stroke="#39d98a"'), C(0, 0, 18, 'none', 2, 'stroke="#39d98a"'), G(`rotate(${n2(sw)})`, L('M0 0H38', '#7dffb4', 3)), C(22, -14, 4, '#ff5a4d', 0)));
        const graf = screen(235, 660, 250, 86, err ? '#6a1420' : '#0f2a46', err ? T(360, 716, 'ERRO', 44, '#fff') : rep(16, i => R(246 + i * 14, n2(738 - 10 - (Math.sin(t * 2 + i) * .5 + .5) * 50), 10, n2(10 + (Math.sin(t * 2 + i) * .5 + .5) * 50), i % 5 ? '#6fd3ff' : '#ffd23f', 1, 0)) );
        const nav = screen(520, 660, 170, 86, '#0f2a46', TS(605, 688, 'ÓRBITA', 15, '#6fd3ff') + E(605, 714, 56, 18, 'none', 2, 'stroke="#6fd3ff"') + C(n2(605 + Math.cos(t) * 56), n2(714 + Math.sin(t) * 18), 5, '#ffd23f', 0));
        return a + R(-320, 120, 1360, 520, gv('#060b22', '#101a4a'), 0, 0) + starfield(11, 70, -320, 120, 1360, 520) + twinkle(t, 2, 8, -300, 130, 1300, 260) +
          earth('cock', 340, 640, 400, t, tod, 2) + b + c + radar + graf + nav +
          leds(-200, 690, 8, t, 2, 24) + leds(740, 690, 8, t, 6, 24) + leds(-260, 800, 14, t, 9, 26) + leds(420, 800, 12, t, 4, 26) +
          G('translate(215 810)', R(-40, -24, 80, 48, '#55697f', 8, 4), G(`rotate(${n2(Math.sin(t) * 6)})`, R(-6, -70, 12, 60, '#c8cfd8', 4, 4), C(0, -76, 16, '#d9483b', 4))) +
          G('translate(330 810)', R(-46, -28, 92, 56, '#ffd23f', 6, 4), C(0, 0, 18, '#d9483b', 4), TS(0, -32, 'NÃO', 14, '#fff')) +
          dangle(240, 140, 86, t, 1, R(-20, 0, 34, 34, '#fff', 8, 4) + C(-10, 10, 3.5, O, 0) + C(4, 22, 3.5, O, 0) + R(4, 12, 28, 28, '#ff5a4d', 8, 4) + C(18, 26, 3.5, '#fff', 0)) +
          prop('rubber_duck', t, 626, 642, .6) + prop('coffee_mug', t, 90, 640, .55) +
          floats(t, [['sache', 330, 260], ['biscoito', 430, 200, .8], ['caneta', 190, 520], ['ervilha', 560, 470], ['gota', 90, 450]]);
      };
    });

  def('station_lab', 'Laboratório: bancada com frascos borbulhando, quadro de fórmulas, microscópio, centrífuga e amostras suspeitas.',
    { state: { spill: false } }, {}, (tod, s) => {
      const flask = (x, y, c) => P(`M${x - 8} ${y}v34l-22 44q-4 12 10 12h44q14 0 10-12l-22-44v-34z`, '#eefaff', 4) + P(`M${x - 22} ${y + 62}h44l10 20q2 8-8 8h-48q-10 0-8-8z`, c, 3) + R(x - 12, y - 8, 24, 10, '#c98d4e', 3, 3);
      const tube = (x, y, c) => R(x, y, 16, 56, '#eefaff', 8, 3) + R(x + 2, y + 22, 12, 32, c, 6, 0);
      const a = wallSt('#d9f7ee', '#a8e6d6', '#7cc9b5') + ceiling('#b0bcc9') +
        /* quadro branco */
        R(170, 165, 380, 210, '#fdfdfb', 8, 6) + R(170, 370, 380, 12, '#b0bcc9', 3, 4) +
        T(185, 205, 'E = MC²', 26, '#2a8fd8', { a: 'start' }) + T(360, 200, 'ZÉ + BOTÃO = ?', 24, '#d9483b', { a: 'start' }) + L('M185 232q40-20 80 0t80 0 80 0', '#39a96b', 4) +
        T(190, 280, 'O₂ ↓ + PÂNICO ↑', 24, '#14182a', { a: 'start' }) + TS(190, 310, 'cálculo: 3 dias... (ou menos)', 17, '#d9483b', { a: 'start' }) + C(476, 300, 40, '#fff', 4) + C(462, 292, 4, O, 0) + C(490, 292, 4, O, 0) + L('M462 316q14-10 28 0', O, 4) + TS(476, 360, 'ERRADO', 15, '#d9483b') + L('M180 350h120', '#f0b429', 4) +
        R(390, 372, 44, 10, '#d9483b', 3, 2) + R(440, 372, 44, 10, '#2a8fd8', 3, 2) +
        /* tabela periódica */
        R(-36, 170, 194, 170, '#fff', 4, 5) + T(61, 196, 'TABELA PERIÓDICA', 17) + rep(5, j => rep(9, i => (j === 0 && i > 0 && i < 8) ? '' : `<rect x="${-26 + i * 19.6}" y="${206 + j * 24}" width="16" height="20" fill="${['#ff9aa8', '#ffd97a', '#9fe0ff', '#b6f0a0', '#d6b8ff'][(i + j) % 5]}" stroke="${O}" stroke-width="1.5"/>`)) +
        warn(136, 410, .75) + T(80, 472, 'RISCO BIOLÓGICO', 16, '#d9483b') +
        sticky(4, 360, 'QUEM COMEU', 'AMOSTRA 7?', '#ffb0c8', -6) +
        /* geladeira de amostras */
        R(590, 160, 180, 340, '#f4f8fb', 12, 6) + L('M590 290h180', O, 5) + R(610, 195, 12, 70, '#8d99a8', 5, 3) + R(610, 310, 12, 70, '#8d99a8', 5, 3) +
        T(690, 230, 'AMOSTRAS', 22) + T(690, 256, 'NÃO É LANCHE', 15, '#d9483b') + sticky(640, 330, 'EU SEI QUE', 'FOI VOCÊ', '#ffe66b', 4) + photo(640, 410, 'ze', -4, .75) +
        /* prateleiras altas */
        shelfRow(-300, 400, 240) + shelfRow(780, 420, 240) + rep(4, i => flask(-268 + i * 58, 308, ['#7dffb4', '#ff9aa8', '#ffd97a', '#b48cff'][i])) + rep(4, i => flask(812 + i * 58, 328, ['#6fd3ff', '#ff9a3c', '#7dffb4', '#ff9aa8'][i]));
      const b =
        /* bancada */
        R(-320, 640, 1360, 28, '#f4f8fb', 6, 5) + R(-320, 668, 1360, 214, '#6fc7b4', 0, 5) + rep(7, i => R(-300 + i * 200, 684, 180, 180, '#86d6c4', 8, 4) + C(-210 + i * 200, 720, 8, '#f4f8fb', 3)) +
        T(190, 770, 'QUÍMICOS', 22, '#14564a') + T(190, 800, 'NÃO CHEIRAR', 17, '#d9483b') + sign(30, 700, 130, 44, '#ffd23f', 'FRÁGIL', O, 22, -3) + T(570, 770, 'LUVAS', 24, '#14564a') + R(530, 790, 80, 40, '#fff', 4, 3) + TS(570, 816, 'acabaram', 14, '#d9483b') +
        floorSt('#e6f4f2', '#b9d6d6', '#97bcc0') + rep(9, i => R(-280 + i * 160, 1000 + (i % 3) * 170, 150, 50, '#cdeae6', 0, 0, 'opacity=".5"')) +
        R(20, 1110, 210, 36, '#f0b429', 8, 5) + T(125, 1137, 'PISO ESCORREGA', 22) + R(70, 960, 100, 16, '#c8cfd8', 6, 5) + R(114, 976, 12, 110, '#8d99a8', 3, 4) + E(120, 1090, 54, 10, '#55697f', 4) +
        R(600, 900, 110, 130, '#ffd23f', 8, 5) + T(655, 975, 'LIXO', 22) + T(655, 1000, 'TÓXICO', 16, '#d9483b') + C(655, 930, 16, O, 0) + E(690, 1060, 60, 10, '#7dffb4', 0, 'opacity=".6"');
      return t => {
        const bub = (x, y, n) => rep(n, i => { const f = (t * .9 + i / n) % 1; return C(n2(x + Math.sin(i * 3 + t * 3) * 8), n2(y - f * 46), n2(2 + f * 4), '#fff', 1.5, `opacity="${n2(1 - f)}"`); });
        const cent = G('translate(590 600)', R(-60, -36, 120, 76, '#c8cfd8', 10, 5), G(`rotate(${n2(t * 720 % 360)})`, C(0, -6, 26, '#55697f', 4), L('M-22 -6H22M0 -28V16', '#fff', 5)), TS(0, -42, 'CENTRÍFUGA', 13));
        const dna = screen(44, 490, 130, 130, '#10204a', rep(10, i => { const y = 500 + i * 11, q = t * 3 + i * .7; return L(`M${n2(109 + Math.sin(q) * 40)} ${y}L${n2(109 - Math.sin(q) * 40)} ${y}`, i % 2 ? '#7dffb4' : '#ff9aa8', 4); }));
        return a + b + flask(100, 548, '#7dffb4') + flask(190, 548, '#ff9aa8') + flask(460, 548, '#b48cff') + bub(100, 620, 5) + bub(190, 620, 5) + bub(460, 620, 4) +
          R(232, 596, 90, 40, '#c98d4e', 4, 4) + rep(5, i => tube(238 + i * 16, 566, ['#ff5a4d', '#ffd23f', '#39d98a', '#2a8fd8', '#b48cff'][i])) +
          G('translate(390 640)', R(-40, -14, 80, 14, '#3d5a86', 4, 4), L('M-20 -14q-16-50 24-84', O, 20), L('M-20 -14q-16-50 24-84', '#5d7088', 12), R(-6, -120, 26, 54, '#c8cfd8', 6, 4, 'transform="rotate(20)"'), C(-20, -30, 8, '#ffd23f', 3)) +
          dna + cent + leds(530, 590, 3, t, 4, 16) +
          prop('plant', t, -100, 620, .7) + prop('coffee_mug', t, 700, 615, .5) +
          (s.spill ? P('M60 636q60 10 120 0q10 60-10 150q-14 10-20-60q-14 30-30 50q-10-20-10-70q-30 10-50-70z', '#7dffb4', 4) : '') +
          floats(t, [['gota', 240, 480], ['ervilha', 480, 470], ['caneta', 170, 440, .9], ['macarrao', 560, 120, .8], ['gota', 650, 540, .8]]);
      };
    });

  def('station_generator', 'Sala do gerador de oxigênio: tanques, tubos com bolhas, manômetro grande, válvulas, botão vermelho e muita fita.',
    { state: { o2: 48, broken: false } }, { sirenes: [[60, 180], [660, 180]] }, (tod, s) => {
      const nivel = V.cl((s.o2 === undefined ? 70 : s.o2) / 100, 0, 1);
      const tank = (x, y, w, h, c, lab) => R(x, y, w, h, c, w / 2.6, 6) + `<rect x="${x + w * .16}" y="${y + 30}" width="${w * .14}" height="${h - 60}" rx="8" fill="#fff" opacity=".4"/>` + L(`M${x} ${y + 70}h${w}M${x} ${y + h - 70}h${w}`, O, 5) + T(x + w / 2, y + h / 2 + 12, lab, Math.min(38, w * .3), '#fff');
      const a = wallSt('#ffb35c', '#e98a35', '#c96b1e') + ceiling('#9a8f85') +
        pipeV(-180, 44, '#c8cfd8') + pipeV(120, 36, '#39d98a', -320, 330) + pipeV(570, 36, '#2a8fd8', -320, 330) + pipeV(880, 44, '#c8cfd8') +
        pipeH(200, 44, '#c8cfd8') + [-260, 40, 650, 900].map(x => clampH(x, 200, 44)).join('') + T(360, 234, 'LINHA PRINCIPAL DE O₂', 30, O, { ls: 2 }) +
        /* tanques ao fundo */
        tank(-300, 280, 200, 600, '#2a8fd8', 'O₂ A') + tank(-40, 300, 180, 580, '#39a96b', 'O₂ B') + tank(574, 300, 146, 580, '#39a96b', 'O₂ C') + tank(810, 280, 200, 600, '#d9483b', 'N₂') +
        ductPatch(30, 500, -14) + ductPatch(-200, 640, 7, 80) + ductPatch(680, 460, 10) + sticky(610, 560, 'NÃO', 'CHUTAR', '#ffe66b', -6) + sticky(-60, 640, 'FOI O', 'ZÉ', '#ffb0c8', 7) +
        warn(640, 330, .7) + T(50, 360, 'QUENTE!', 24, '#ffd23f');
      const b =
        /* painel central atrás do elenco */
        R(150, 280, 420, 440, '#c8cfd8', 14, 6) + rivets(150, 280, 420, 440) + T(360, 318, 'GERADOR DE OXIGÊNIO MK-2', 26, O) +
        note(165, 582, 120, 124, 'REVISÃO', ['Última:', 'NUNCA', '', 'Ass: Zé'], '#fff', -3) + sign(290, 620, 106, 50, '#d9483b', 'ATENÇÃO', '#fff', 22) +
        hazard(150, 720, 420, 22, 0) +
        floorSt('#b78f6e', '#83604a', '#6b4d3a') + R(610, 900, 90, 110, '#3a82b4', 10, 5) + L('M610 915q45 18 90 0', O, 4) + T(655, 980, 'BALDE', 16, '#fff') +
        cable(-320, 930, 200, 960, 40, '#ffd23f', 12) + cable(1040, 1010, 560, 940, 60, '#d9483b', 12) + ductPatch(90, 948, 3, 60) + P('M60 1190q80-34 150 0t-40 40-110-40z', '#39302a', 0, 'opacity=".35"') + R(20, 1040, 170, 100, '#d9a15f', 6, 5) + L('M20 1064h170', O, 3) + T(105, 1110, 'PEÇAS???', 26) + R(600, 1100, 110, 60, '#c8cfd8', 6, 5) + T(655, 1140, 'ÓLEO', 22, '#d9483b');
      return t => {
        const lvl = 214 - 200 * nivel;
        const tuboX = 196, tuboY = 348;
        const tubo = R(tuboX, tuboY, 78, 200, '#dff4ff', 12, 5) + R(tuboX + 5, n2(tuboY + 200 - nivel * 190), 68, n2(nivel * 190 - 3), s.broken ? '#ff9a8a' : '#7fe8ff', 8, 0) +
          rep(9, i => { const f = (t * .5 + i / 9) % 1; return C(n2(tuboX + 18 + rnd(i) * 42 + Math.sin(t + i) * 4), n2(tuboY + 192 - f * nivel * 180), 3 + rnd(i + 4) * 5, '#fff', 2, 'opacity=".8"'); }) + TS(tuboX + 39, tuboY + 218, 'NÍVEL', 15);
        const trem = Math.sin(t * 40) * (s.broken ? .04 : .006);
        const needle = gauge(360, 420, 76, nivel + trem, 'O₂');
        const lamp = (s.broken ? Math.sin(t * 7) > 0 : true) ? (s.broken ? '#ff5a4d' : '#39d98a') : '#5a2a2a';
        const sparks = s.broken ? rep(10, i => { const f = (t * 2.3 + i * .13) % 1, q = rnd(i) * 3.1 + 3.1; return C(n2(500 + Math.cos(q) * f * 90), n2(620 + Math.sin(q) * f * 50 + f * f * 120), 3.5, '#ffd23f', 0, `opacity="${n2(1 - f)}"`); }) : '';
        return a + b + tubo + needle + fan(490, 420, 58, t, s.broken ? 60 : 500) + C(490, 530, 22, lamp, 5) +
          G('translate(462 640)', R(-58, -46, 116, 92, '#ffd23f', 8, 5), C(0, 0, 32, '#d9483b', 5), P('M-40 -38h80', 'none', 5), TS(0, 42, 'EMERGÊNCIA', 12)) +
                    leds(316, 690, 5, t, 8, 22) +
          G(`translate(120 690) rotate(${n2(t * 6 % 360 * .1)})`, C(0, 0, 34, '#d9483b', 5), L('M-24 0H24M0 -24V24', O, 6), C(0, 0, 8, '#ffd23f', 3)) +
          steamPuff(-60, 200, t, 1, 7, 110) + steamPuff(780, 200, t, 5, 7, 110) + steamPuff(650, 300, t, 9, 5, 70) +
          drip(655, 244, 650, t, 3) + drip(655, 244, 650, t + .5, 4) + sparks + floats(t, [['parafuso', 580, 760], ['gota', 110, 780], ['biscoito', 80, 150, .7]]);
      };
    });

  def('station_dorm', 'Dormitório: sacos de dormir presos à parede, fotos, pisca-pisca, varal de meias flutuando, bagunça pessoal.',
    { state: {} }, { sirenes: [[360, 150]], noite: '#1a1d6b', noiteOp: .24 }, (tod, s) => {
      const bunk = (x, y, c, nome) => R(x, y, 230, 150, '#efe7ff', 12, 5) + P(`M${x + 20} ${y + 104}q10-74 90-74h90q20 0 20 20v54z`, c, 5) + E(x + 54, y + 72, 34, 24, '#fff', 4) + L(`M${x + 110} ${y + 30}v74M${x + 160} ${y + 30}v74`, O, 4) + R(x - 8, y + 104, 246, 16, '#8d99a8', 6, 4) + R(x + 80, y + 124, 70, 22, '#fff', 3, 3) + TS(x + 115, y + 141, nome, 13);
      const a = wallSt('#c3a6f2', '#9b7fd6', '#7a5cb8') + ceiling('#a79fc0') +
        bunk(-150, 170, '#2a8fd8', 'COMANDANTE') + bunk(-150, 360, '#d9483b', 'DRA.') + bunk(640, 170, '#39a96b', 'ZÉ') + bunk(640, 360, '#ffb545', 'VAGO') +
        G('translate(136 0) rotate(-2 35 280) scale(.85 1)', R(-50, 170, 170, 230, '#ffcf6b', 5, 5), C(35, 250, 40, '#ff9a3c', 4), P('M6 222l-10-26 26 12M64 222l10-26-26 12', '#ff9a3c', 4), C(20, 246, 5, O, 0), C(50, 246, 5, O, 0), L('M24 266q11 8 22 0', O, 4), T(35, 330, 'AGUENTA', 28, '#d9483b'), T(35, 362, 'FIRME', 28, '#d9483b')) +
        poster(486, 166, 130, 150, '#2a6fd8', 'CAMPEÃO', '1998', 4, C(551, 216, 30, '#fff', 4) + P('M551 196l11 9-5 14h-12l-5-14z', O, 0)) +
        photo(262, 176, 'familia', -5) + photo(352, 190, 'praia', 4) + sticky(300, 300, 'VOLTO', 'LOGO', '#ffe66b', -4) + photo(394, 300, 'cao', 3, .8) +
        /* calendário riscado */
        G('translate(86 118)', R(170, 310, 130, 130, '#fff', 4, 5), R(170, 310, 130, 30, '#d9483b', 4, 4), T(235, 332, 'ÓRBITA', 18, '#fff'), rep(4, j => rep(5, i => (j * 5 + i < 12) ? L(`M${184 + i * 22} ${352 + j * 20}l12 12m0-12l-12 12`, '#d9483b', 3) : R(184 + i * 22, 352 + j * 20, 12, 12, '#dfe6ee', 2, 2))));
      const b =
        note(96, 424, 140, 130, 'REGRAS', ['Sem meia na', 'ventilação', 'Sem ronco', '(Zé!!!)'], '#fff4d6', 3) +
        /* armários e mesinha */
        rep(4, i => R(-60 + i * 212, 590, 200, 290, ['#7fb3e8', '#f09aa8', '#8fd8a8', '#ffd97a'][i], 8, 5) + R(-60 + i * 212 + 170, 720, 14, 50, '#fff', 5, 3) + vent(-40 + i * 212, 610, 90, 44) + TS(-60 + i * 212 + 60, 720, ['CMDT', 'DRA.', 'ZÉ', 'VAGO'][i], 22)) +
        sticky(340, 760, 'NÃO ABRIR', 'CAI TUDO', '#ffe66b', 5) + ductPatch(440, 800, -40, 60) + ductPatch(460, 670, 30, 50) +
        floorSt('#c9b8e6', '#927fbd', '#7866a6') + E(360, 1160, 340, 90, '#ff9ac0', 5) + E(360, 1160, 280, 66, '#ffc0d8', 3) +
        R(600, 920, 130, 96, '#3a82b4', 10, 5) + L('M600 950h130', O, 4) + T(665, 998, 'ROUPA SUJA', 16, '#fff');
      return t => {
        const lights = rep(13, i => { const x = -300 + i * 110, y = 150 + Math.abs(Math.sin(i * 1.57)) * 22; return C(x, y + 12, 9, ['#ffd23f', '#ff5a4d', '#7dffb4', '#6fd3ff'][i % 4], 3, `opacity="${Math.sin(t * 3 + i) > -.4 ? 1 : .35}"`); });
        return a + porthole('dor', 500, 420, 62, t, tod) + b + L('M-320 150Q-100 186 120 150T560 150T1040 150', O, 4) + lights +
          R(10, 1020, 180, 20, '#c98d4e', 4, 5) + R(26, 1040, 14, 70, '#8d6a45', 3, 4) + R(160, 1040, 14, 70, '#8d6a45', 3, 4) + prop('laptop', t, 80, 980, .8, { on: true }) + prop('coffee_mug', t, 165, 1000, .4) + prop('backpack', t, 640, 870, .8) +
          /* varal com meias */
          L('M120 500Q360 540 600 500', O, 4) + rep(5, i => G(`translate(${170 + i * 95} ${513 + Math.sin(i * .63 + .6) * 20}) rotate(${n2(Math.sin(t * 1.4 + i) * 12)})`, L('M0 -8V6', '#d9483b', 5), G('translate(0 28) scale(.7)', i % 2 ? mini.meia : R(-20, -24, 40, 48, ['#fff', '#7fb3e8', '#ffb0c8'][i % 3], 5, 4)))) +
          floats(t, [['meia', 150, 600], ['ervilha', 520, 200], ['biscoito', 570, 560], ['bola', 80, 460], ['macarrao', 330, 470, .8], ['caneta', 560, 400]]) +
          G(`translate(460 ${n2(240 + Math.sin(t * .6) * 16)}) rotate(${n2(t * 9 % 360)})`, E(0, 0, 44, 26, '#fff', 5), L('M-26 -6q26 12 52 0', '#dfe6ee', 4));
      };
    });

  def('station_airlock', 'Eclusa de saída: porta redonda enorme, trajes pendurados, capacetes, tanques e avisos gritantes.',
    { state: { open: 0 } }, { sirenes: [[110, 170], [610, 170]] }, (tod, s) => {
      const abre = V.cl(s.open || 0, 0, 1);
      const suit = (x, y, c = '#f4f4f2') => G(`translate(${x} ${y})`, R(-3, -40, 6, 40, O, 2, 0), R(-40, -10, 80, 16, '#8d99a8', 6, 4), P('M-46 10q0-20 26-20h40q26 0 26 20l6 110h-22l-6-60v190h-30v-120h-20v120h-30V60l-6 60h-22z', c, 5), C(0, -34 + 26, 0, '#fff', 0), R(-24, 30, 48, 40, '#2a8fd8', 5, 4), leds0(-14, 48), L('M-20 90h40', '#d9483b', 8));
      function leds0(x, y) { return C(x, y, 4, '#39d98a', 2) + C(x + 14, y, 4, '#ffd23f', 2) + C(x + 28, y, 4, '#ff5a4d', 2); }
      const a = wallSt('#ffe07a', '#e8b93f', '#b98f22') + ceiling('#9aa3ad') +
        hazard(-320, 160, 1360, 34, 0) + hazard(-320, 820, 1360, 34, 0) +
        suit(-120, 400) + suit(50, 400, '#ffb545') + suit(800, 400) + suit(940, 400, '#9fe0ff') +
        rep(3, i => R(600 + i * 42, 566, 38, 140, ['#2a8fd8', '#39a96b', '#2a8fd8'][i], 16, 5) + R(610 + i * 42, 550, 18, 18, '#c8cfd8', 4, 3)) + shelfRow(590, 706, 200) +
        T(660, 746, 'O₂ RESERVA', 20);
      const b =
        warn(-250, 300, .9) + note(-190, 230, 150, 150, 'ANTES DE SAIR', ['[x] Capacete', '[ ] Oxigênio', '[ ] Coragem', '[ ] Testamento'], '#fff', -3) +
        sign(590, 205, 140, 76, '#d9483b', 'PERIGO', '#fff', 34) + TS(660, 304, 'VÁCUO LÁ FORA', 15) + TS(660, 326, '(SEM BRINCADEIRA)', 12, '#d9483b') +
        sign(-10, 205, 136, 60, '#39a96b', 'FECHE', '#fff', 30) + TS(62, 282, 'A PORTA INTERNA', 13) +
        /* botões da eclusa */
        R(590, 360, 150, 170, '#c8cfd8', 10, 5) + T(665, 392, 'CICLO', 24) + R(610, 404, 110, 40, '#0f2a46', 4, 4) +
        floorSt('#a9b3bf', '#74818f', '#5b6877') + hazard(-320, 1090 + 70, 1360, 34, 0) + T(360, 1230, 'NÃO FICAR PARADO AQUI (SÉRIO)', 30, '#fff') +
        R(10, 960, 180, 96, '#8d99a8', 8, 5) + rep(2, i => P(`M${24 + i * 80} 960q2-60 30-60h20q10 0 10 20v40z`, '#f4f4f2', 4)) + T(100, 1020, 'BOTAS', 28) + R(590, 980, 120, 80, '#d9483b', 6, 5) + T(650, 1030, 'CORDAS', 20, '#fff') + cable(-320, 1230, 200, 1300, 30, '#ffd23f', 8);
      return t => {
        /* porta redonda: abre correndo para cima */
        const x = 360, y = 460, r = 240;
        const portaY = -abre * 500;
        const buraco = '<g transform="translate(360 470) scale(.85) translate(-360 -460)">' + C(x, y, r + 34, '#c9d6e2', 8) + C(x, y, r + 4, '#060b22', 6) + `<clipPath id="clip_airh"><circle cx="${x}" cy="${y}" r="${r}"/></clipPath><g clip-path="url(#clip_airh)">${starfield(9, 40, x - r, y - r, 2 * r, 2 * r)}${earth('air', x + 60, y + 240, 240, t, tod)}` +
          G(`translate(0 ${n2(portaY)})`, C(x, y, r + 3, '#9fb1c4', 6), C(x, y, r - 50, '#b7c6d6', 5), rep(12, i => { const q = i * Math.PI / 6; return C(n2(x + Math.cos(q) * (r - 24)), n2(y + Math.sin(q) * (r - 24)), 9, '#7b8ba0', 3); }),
            C(x, y - 104, 58, '#0a1022', 6), `<circle cx="${x}" cy="${y - 104}" r="48" fill="#123a6e"/>`, L(`M${x - 26} ${y - 124}q20-16 42-10`, '#fff', 6, 'opacity=".5"'), hazard(x - 150, y + 110, 300, 22),
            G(`translate(${x} ${y + 30}) rotate(${n2(Math.sin(t * .8) * 6)})`, C(0, 0, 70, 'none', 14), L('M-70 0H70M0 -70V70', O, 12), C(0, 0, 20, '#d9483b', 5)),
            T(x, y + 172, 'SAÍDA', 28, '#fff'), ductPatch(x + 150, y - 90, 25), sticky(x - 200, y - 40, 'BOA', 'SORTE', '#ffe66b', -8)) + `</g>` +
          rep(8, i => { const q = i * Math.PI / 4 + .4; return C(n2(x + Math.cos(q) * (r + 18)), n2(y + Math.sin(q) * (r + 18)), 8, '#7b8ba0', 3); }) + '</g>';
        const bar = Math.sin(t * 1.4) * .5 + .5;
        return a + buraco + b + R(618, 412, n2(94 * (abre > 0 ? 1 : bar * .6 + .1)), 24, abre > 0 ? '#ff5a4d' : '#39d98a', 2, 0) +
          leds(612, 468, 5, t, 7, 26) + C(630, 506, 13, abre > 0 ? '#ff5a4d' : '#6b2520', 4) + C(700, 506, 13, abre > 0 ? '#1a5a3a' : '#39d98a', 4) +
          prop('helmet', t, 62, 330, .55) + prop('oxygen_mask', t, 150, 770, .5) +
          dangle(130, 140, 110, t, 2, R(-5, 0, 10, 60, '#ffd23f', 4, 3)) + dangle(600, 140, 120, t, 4, R(-5, 0, 10, 50, '#d9483b', 4, 3)) +
          cable(-300, 800, 130, 790, 70, '#ffd23f', 8) +
          floats(t, [['gota', 120, 640], ['parafuso', 620, 800], ['biscoito', 110, 780, .7]]);
      };
    });

  def('station_storage', 'Depósito: estantes abarrotadas, caixas com rótulos engraçados, rede de carga, rações e coisas boiando.',
    { state: {} }, { sirenes: [[360, 150]] }, (tod, s) => {
      const estante = (x, w) => R(x, 160, 14, 720, '#6d7f93', 3, 4) + R(x + w - 14, 160, 14, 720, '#6d7f93', 3, 4) + [330, 520, 710, 866].map(y => shelfRow(x, y, w)).join('');
      /* empilha caixas do canto para o centro */
      const pile = (x, y, seed, w, fim) => { let cx = fim ? x + w : x, s2 = ''; const cs = ['#d9a15f', '#ffb545', '#7fb3e8', '#f09aa8', '#8fd8a8', '#e8e0c8', '#c98d4e']; const labs = ['RAÇÃO', 'BOLT', '???', 'FEIJÃO', 'NÃO ABRIR', 'MEIAS', 'FITA', 'CAFÉ', 'BISCOITO', 'H₂O', 'DO ZÉ', 'FRÁGIL']; for (let i = 0; i < 9; i++) { const wd = 74 + rnd(seed + i) * 40, h = 76 + rnd(seed + i * 2) * 74; if (fim ? cx - wd < x : cx + wd > x + w) break; const bx = fim ? cx - wd : cx; s2 += crate(bx, y - h, wd, h, cs[Math.floor(rnd(seed + i * 3) * cs.length)], labs[Math.floor(rnd(seed + i * 5) * labs.length)]); cx += fim ? -(wd + 5) : wd + 5; } return s2; };
      const a = wallSt('#e9cf9c', '#cfae74', '#a78650') + ceiling('#a39a8c') +
        /* fundo central: porta de carga com rede */
        R(150, 170, 420, 710, '#a9b3bf', 10, 6) + rep(9, i => L(`M150 ${240 + i * 72}H570`, '#7b8ba0', 6)) + T(360, 228, 'CARGA — MÓDULO D', 30, O) +
        rep(7, i => L(`M${170 + i * 63} ${252 + Math.sin(i / 6 * 3.14) * 30}V${650 + Math.sin(i / 6 * 3.14) * 30}`, '#7a5cb8', 4)) + rep(6, i => L(`M170 ${310 + i * 62}Q360 ${370 + i * 62} 548 ${310 + i * 62}`, '#7a5cb8', 4)) +
        note(165, 700, 150, 124, 'INVENTÁRIO', ['Parafusos: sim', 'Comida: pouca', 'Esperança: ?', 'Fita: ACABOU'], '#fff', -3) +
        sign(390, 780, 170, 56, '#ffd23f', 'NÃO EMPILHAR', O, 22) + sticky(330, 690, 'SÓ DEUS', 'SABE', '#ffb0c8', 5) +
        estante(-300, 460) + estante(560, 460) + [330, 520, 710, 866].map((y, i) => pile(-284, y, 3 + i * 10, 430, true) + pile(574, y, 43 + i * 10, 430, false)).join('');
      const b = floorSt('#c9b48f', '#987e5c', '#7c6546') +
        crate(10, 950, 150, 110, '#d9a15f', 'COMIDA?') + crate(30, 870, 100, 80, '#e8e0c8', 'SOPA') + crate(570, 930, 150, 120, '#c98d4e', 'FITA (VAZIA)') + crate(600, 850, 100, 80, '#ffb545', 'NÃO ABRIR') +
        P('M780 880v180h140V880z', '#8d99a8', 5) + L('M780 930h140M780 1000h140', O, 5) + T(850, 980, 'ÓLEO', 22) + R(250, 1240, 230, 30, '#a0784a', 4, 5) + R(250, 1270, 230, 22, '#8d6a45', 4, 4);
      return t => a + b + floats(t, [['sache', 240, 300], ['biscoito', 480, 620], ['maca', 300, 420], ['ervilha', 450, 520], ['macarrao', 460, 330], ['parafuso', 300, 150], ['bola', 200, 560], ['meia', 510, 440]]) +
        G(`translate(460 ${n2(590 + Math.sin(t * .5) * 14)}) rotate(${n2(Math.sin(t * .4) * 9)})`, crate(-48, -36, 96, 72, '#f09aa8', 'SOCORRO')) +
        prop('rubber_duck', t, 650, 810, .5) + (Math.sin(t * .7) > .4 ? C(70, 840, 6, '#ffd23f', 3) + C(90, 840, 6, '#ffd23f', 3) : '') + leds(500, 190, 3, t, 5, 20) +
        prop('ration_pack', t, 200, 1100, .7) + prop('water_pouch', t, 530, 1120, .7, { level: .4 });
    });

  def('station_greenhouse', 'Estufa: bancadas hidropônicas, luz rosa de cultivo, tomates, alface sagrada e girassol com nome.',
    { state: { dead: false } }, { sirenes: [[360, 150]], noite: '#2a1a70', noiteOp: .26 }, (tod, s) => {
      const dead = !!s.dead;
      const verde = dead ? '#b39a56' : '#58c26a', verdeE = dead ? '#8d7740' : '#2f9c55';
      const alface = (x, y) => C(x, y, 26, verde, 4) + C(x - 16, y + 6, 18, verdeE, 4) + C(x + 16, y + 6, 18, verdeE, 4) + C(x, y + 12, 16, verde, 4);
      const tomate = (x, y) => (dead ? '' : C(x, y, 12, '#e8483b', 3) + L(`M${x - 4} ${y - 10}l8 0`, '#2f9c55', 3));
      const bench = (y, seed) => R(-320, y, 1360, 34, '#f4f8fb', 8, 5) + R(-320, y + 34, 1360, 16, '#6fd3ff', 0, 4) + rep(15, i => alface(-300 + i * 94, y - 16 + (i % 2) * 6) + R(-310 + i * 94, y + 40, 22, 26, '#fff', 3, 2));
      const vine = (x, y1, y2) => L(`M${x} ${y1}q24 ${(y2 - y1) / 4} 0 ${(y2 - y1) / 2}t0 ${(y2 - y1) / 2}`, verdeE, 8) + rep(5, i => E(x + (i % 2 ? 22 : -22), y1 + 16 + i * (y2 - y1) / 5, 20, 11, verde, 3) + tomate(x + (i % 2 ? -14 : 14), y1 + 30 + i * (y2 - y1) / 5));
      const a = wallSt('#c6f2b8', '#8fdc96', '#60b56e') + ceiling('#9fb5a4') +
        rep(6, i => R(-280 + i * 240, 148, 190, 22, '#ff8ad8', 8, 4)) +
        vine(-260, 170, 620) + vine(-120, 170, 620) + vine(-10, 170, 620) + vine(730, 170, 620) + vine(860, 170, 620) + vine(980, 170, 620);
      const b =
        bench(600, 1) + R(-320, 650, 1360, 232, '#7fd4a0', 0, 5) + rep(7, i => R(-300 + i * 200, 670, 180, 190, '#96e2b2', 8, 4)) +
        pipeH(868 - 90, 18, '#2a8fd8') +
        sign(120, 460, 180, 80, '#fff', 'NÃO COMA', '#d9483b', 24) + TS(210, 530, 'A ALFACE DA DRA.', 15, '#d9483b') +
        note(560, 420, 130, 130, 'REGAR', ['Dia sim', 'Dia não', 'Dia SIM', 'Ass: Zé'], '#fff', 4) + photo(480, 416, 'praia', -4, .7) +
        floorSt('#b9d9a6', '#7fae7a', '#62936a') + R(20, 1060, 180, 70, '#c98d4e', 8, 5) + E(110, 1058, 84, 14, '#6b4726', 4) + T(110, 1110, 'TERRA', 24, '#fff') + G('translate(240 1010)', P('M-22 40l6-60h32l6 60z', '#2a8fd8', 4), C(0, -46, 26, '#ffd23f', 4), P('M-30 -56L0 -96 30 -56z', '#d9483b', 4), C(-8, -46, 3, O, 0), C(8, -46, 3, O, 0), P('M-16 -34q16 26 32 0z', '#fff', 3)) + R(590, 1080, 120, 60, '#39a96b', 8, 5) + L('M710 1090q50 0 20-50', O, 8) + T(650, 1118, 'REGADOR', 16, '#fff') + rep(4, i => R(600 + i * 34, 930, 24, 90, '#a86f35', 3, 4) + P(`M${598 + i * 34} 930h28l-3 -16h-22z`, '#c98d4e', 3)) + T(660, 1050, 'VASOS', 22) ;
      return t => {
        const girassol = G(`translate(80 ${dead ? 530 : 440}) rotate(${n2((dead ? 60 : 0) + Math.sin(t * 1.1) * 3)})`, L(`M0 30V${dead ? 90 : 170}`, verdeE, 10), rep(14, i => E(0, -40, 13, 26, dead ? '#b39a56' : '#ffd23f', 3, `transform="rotate(${i * 360 / 14})"`)), C(0, 0, 30, '#6b3f1e', 4), C(-10, -4, 3.5, O, 0), C(10, -4, 3.5, O, 0), L(dead ? 'M-8 12q8-8 16 0' : 'M-8 8q8 8 16 0', O, 3));
        return a + porthole('est', 360, 280, 96, t, tod) + b + girassol + R(30, 640 - 28, 110, 30, '#fff', 3, 3) + TS(85, 632, 'DONA CIDA', 15) +
          rep(6, i => drip(-280 + i * 240, 170, 420, t, i + 2)) +
          `<rect x="-340" y="170" width="1400" height="710" fill="#ff5ac8" opacity="${n2(.07 + Math.sin(t * 1.3) * .015)}"/>` +
          rep(6, i => { const f = (t * .15 + i / 6) % 1; return C(n2(-200 + i * 190 + Math.sin(t + i) * 20), n2(720 - f * 480), 4 + i % 3, '#fff', 0, `opacity="${n2((1 - f) * .5)}"`); }) +
          prop('plant', t, 550, 586, .8, { dead }) + G(`translate(${n2(470 + Math.sin(t * .9) * 90)} ${n2(450 + Math.sin(t * 1.7) * 40)})`, E(0, 0, 11, 8, '#ffd23f', 3), L('M-3 -7v14M4 -7v14', O, 3), E(-4, -9, 7, 4, '#fff', 2, 'opacity=".8"'), E(5, -9, 7, 4, '#fff', 2, 'opacity=".8"')) +
          floats(t, [['gota', 200, 400], ['gota', 520, 240], ['ervilha', 560, 180], ['gota', 110, 260, .7], ['maca', 640, 360, .8]]);
      };
    });

  /* ================= ÓRBITA ================= */

  def('exterior_orbit', 'Fora da estação: Terra enorme, painéis solares, casco da Astra-9 para o elenco caminhar, satélite e destroços.',
    { state: { sparks: false } }, { sirenes: [[100, 960], [640, 960]], noite: '#10144f', noiteOp: .12 }, (tod, s) => {
      const painel = (x, y, w, h) => R(x, y, w, h, '#2a55c8', 4, 5) + rep(Math.floor(w / 60), i => L(`M${x + (i + 1) * 60} ${y}v${h}`, '#9fc0ff', 3)) + rep(3, j => L(`M${x} ${y + (j + 1) * h / 4}h${w}`, '#9fc0ff', 3));
      const fundo = R(-340, -340, 1400, 2100, gv('#0b1040', '#1a2a7a'), 0, 0) + starfield(5, 170, -340, -340, 1400, 1400) +
        `<ellipse cx="60" cy="120" rx="300" ry="170" fill="${fade('#7a3cff')}" opacity=".45"/><ellipse cx="760" cy="60" rx="280" ry="170" fill="${fade('#ff5ac8')}" opacity=".3"/>`;
      const estrutura =
        /* treliça e asas solares */
        R(-340, 228, 1400, 22, '#c8cfd8', 0, 5) + rep(14, i => L(`M${-320 + i * 100} 228l50 22l50 -22`, O, 4)) +
        painel(-320, 120, 300, 100) + painel(-320, 258, 300, 100) + painel(760, 120, 280, 100) + painel(760, 258, 280, 100) +
        /* módulo da estação atrás do casco */
        R(560, 640, 560, 330, '#e8edf3', 40, 6) + rep(5, i => L(`M${600 + i * 90} 640v330`, '#a9b3bf', 4)) + T(640, 730, 'ASTRA-9', 42, '#14325f') + T(900, 760, 'ASTRA-9', 74, '#14325f') + hazard(560, 820, 500, 20, 0) + C(640, 900, 26, '#6fd3ff', 5) + C(730, 900, 26, '#6fd3ff', 5) + C(820, 900, 26, '#ffd97a', 5) +
        R(-340, 700, 300, 270, '#e8edf3', 30, 6) + L('M-200 700v270', '#a9b3bf', 4) + logoAstra(-120, 840, 1.3) +
        /* antena */
        L('M170 980V830', O, 12) + L('M170 980V830', '#c8cfd8', 6) ;
      const casco = R(-340, 960, 1400, 800, gv('#dfe6ee', '#a4b0bf'), 0, 0) + L('M-340 960H1060', O, 7) + `<rect x="-340" y="966" width="1400" height="10" fill="#fff" opacity=".7"/>` +
        rep(9, i => L(`M${-300 + i * 170} 960L${-420 + i * 230} 1760`, '#8492a3', 4)) + [1030, 1130, 1290].map(y => L(`M-340 ${y}H1060`, '#8492a3', 4)).join('') +
        rep(14, i => C(-300 + i * 100, 1000 + (i % 2) * 20, 5, '#8492a3', 2)) +
        /* corrimão de EVA, placas e remendos */
        R(-340, 1010, 1400, 12, '#ffd23f', 6, 4) + rep(7, i => R(-300 + i * 220, 975, 12, 40, '#8d99a8', 4, 4)) +
        R(20, 1100, 190, 90, '#ffd23f', 6, 5) + T(115, 1140, 'ÁREA DE EVA', 22) + T(115, 1172, 'NÃO CAIR', 26, '#d9483b') + ductPatch(620, 1130, 15, 90) + ductPatch(330, 1230, -10, 70) + TS(620, 1190, 'VAI SEGURAR', 16, O) + hazard(-320, 1400, 1360, 34, 0);
      return t => {
        const sat = G(`translate(${n2(760 - (t * 14) % 1100)} ${n2(90 + Math.sin(t * .3) * 20)}) rotate(-12)`, R(-20, -14, 40, 28, '#ffd23f', 3, 4), R(-70, -8, 46, 16, '#2a55c8', 2, 3), R(24, -8, 46, 16, '#2a55c8', 2, 3), L('M0 -14v-16', O, 3), C(0, -32, 4, '#ff5a4d', 0));
        const dish = G(`translate(170 830) rotate(${n2(-20 + Math.sin(t * .4) * 12)})`, P('M-70 -20Q0 60 70 -20z', '#f4f4f2', 5), L('M0 22V-50', O, 4), C(0, -54, 6, '#ff5a4d', 3));
        const fx = s.sparks ? rep(10, i => { const f = (t * 2 + i * .1) % 1, q = rnd(i) * 3.1 + 3.1; return C(n2(620 + Math.cos(q) * f * 110), n2(1130 + Math.sin(q) * f * 90), 3.5, '#ffd23f', 0, `opacity="${n2(1 - f)}"`); }) : '';
        return fundo + twinkle(t, 3, 12, -300, -200, 1300, 500) + earth('orb', 330, 800, 640, t * .6, tod, 3) + sat + estrutura + dish + casco + leds(610, 700, 5, t, 2, 40) +
          led(-90, 950, '#ff5a4d', t, .1, 8, 3) + led(420, 950, '#39d98a', t, .4, 8, 2) + fx +
          G(`translate(${n2(590 - t * 3 % 200)} ${n2(450 + Math.sin(t * .5) * 30)}) rotate(${n2(t * 24)}) scale(.7)`, (V.props.wrench || (() => ''))(t, {})) +
          floats(t, [['parafuso', 100, 500], ['parafuso', 480, 300], ['gota', 200, 340, .7], ['sache', 560, 500, .7]]);
      };
    });

  def('mission_control', 'Controle da missão na Terra: telão com mapa e órbita, fileiras de técnicos, café e rosquinhas.',
    { state: { big: 'ASTRA-9 — SEM CONTATO?' } }, { sirenes: [[-60, 110], [780, 110]], noite: '#121a66', noiteOp: .2 }, (tod, s) => {
      const tecnico = (x, y, c) => R(x - 44, y - 16, 88, 90, c, 26, 5) + C(x, y - 42, 34, ['#efe3c8', '#c98d5e', '#8a5a36', '#f0c9a0'][Math.floor(rnd(x) * 4)], 5) + P(`M${x - 34} ${y - 44}a34 34 0 0 1 68 0q-34 -18 -68 0z`, ['#3a2a1e', '#14182a', '#a86f35', '#888'][Math.floor(rnd(x + 1) * 4)], 4) + L(`M${x - 34} ${y - 44}a34 34 0 0 1 68 0`, '#55697f', 5) + C(x - 35, y - 40, 7, '#d9483b', 3);
      const mesa = (y, n, dx, x0) => R(-340, y, 1400, 30, '#dfe6ee', 4, 5) + R(-340, y + 30, 1400, 80, '#7f93a9', 0, 5) + rep(n, i => R(x0 + i * dx - 56, y - 76, 112, 72, '#0f2a46', 6, 4) + R(x0 + i * dx - 14, y - 6, 28, 8, '#55697f', 2, 3));
      const parede = R(-340, -340, 1400, 1240, gv('#4f7fc8', '#3560a8'), 0, 0) + rep(8, i => L(`M${-300 + i * 200} -320V880`, '#2c4f90', 4));
      const telaFixa = R(-180, 120, 900, 390, '#14243e', 12, 7) + R(-168, 132, 876, 366, '#0f3a66', 4, 4) +
        rep(13, i => L(`M${-168 + i * 73} 132V498`, '#2a6a9a', 2)) + rep(7, i => L(`M-168 ${132 + i * 61}H708`, '#2a6a9a', 2)) +
        P('M-120 190q60-30 120-10t30 60-70 50-40 70-50-60-40-60zM80 180q70-30 150-10t60 40-90 30-30 60-40-30-50-90zM360 170q100-40 230-20t80 60-120 40-50 70-60-40-90-30-50-40zM500 400q50-20 90 0t-20 40-70-40z', '#46b36b', 3) +
        rep(3, i => R(-300 + (i ? 1000 : 0) + (i === 2 ? 170 : 0), i === 1 ? 130 : 130, 100, 150, '#0f2a46', 6, 5)) ;
      const banner = R(150, 40, 420, 58, '#ffd23f', 6, 5) + T(360, 82, V.esc(s.big || 'ASTRA-9 — DIA DE MISSÃO'), Math.min(34, 620 / ((s.big || 'x').length || 1)), O);
      const resto = R(-300, 300, 110, 200, '#fff', 4, 5) + T(-245, 330, 'CAFÉ', 22) + rep(4, i => L(`M-288 ${350 + i * 24}h76`, O, 3)) +
        R(740, 310, 170, 180, '#fff', 4, 5) + T(825, 340, 'TURNO', 22) + TS(750, 368, 'Seg: Carlos', 15, O, { a: 'start' }) + TS(750, 392, 'Ter: Carlos', 15, O, { a: 'start' }) + TS(750, 416, 'Qua: Carlos', 15, O, { a: 'start' }) + TS(750, 440, 'Qui: socorro', 15, '#d9483b', { a: 'start' });
      const fileiraFundo = mesa(650, 6, 170, -60);
      const pisos = R(-340, 880, 1400, 900, gv('#6c8cc4', '#4a68a6'), 0, 0) + cable(-320, 1190, 300, 1250, 40, '#ffd23f', 7) + cable(1040, 1120, 480, 1230, 50, '#ff9aa8', 7) + rep(9, i => L(`M${-340 + i * 170} 880L${-700 + i * 260} 1760`, '#3f5c96', 3)) + L('M-340 880H1060', O, 6) +
        rep(14, i => C(rnd(i) * 1300 - 300, 900 + rnd(i + 9) * 700, 3, '#fff', 0, 'opacity=".2"'));
      const f2 = rep(6, i => tecnico(-110 + i * 170, 760, ['#2a6fd8', '#d9483b', '#39a96b', '#ffb545', '#b48cff', '#3a82b4'][i]));
      const f3 = mesa(830, 2, 780, -40) +
        R(40, 800, 90, 30, '#e8c07a', 4, 4) + T(85, 822, 'ROSQUINHAS', 12) +
        R(600, 780, 60, 50, '#fff', 8, 4) + L('M660 794q20 6 0 24', O, 4);
      return t => {
        const blip = t * 18 % 876;
        const orb = L(rep(40, i => { const x = -168 + i * 22.5; return `${i ? 'L' : 'M'}${x} ${n2(320 + Math.sin(x / 110 + t * .1) * 120)}`; }), '#ffd23f', 3, 'stroke-dasharray="10 8"');
        const bx = -168 + blip, by = 320 + Math.sin(bx / 110 + t * .1) * 120;
        const mon = rep(6, i => { const x = -60 + i * 170 - 56; return rep(4, j => R(x + 8, 586 + j * 13, n2(30 + (Math.sin(t * 2 + i + j) * .5 + .5) * 60), 7, ['#7dffb4', '#6fd3ff', '#ffd23f', '#ff9aa8'][(i + j) % 4], 2, 0)); });
        const sMon = rep(3, i => { const x = i === 0 ? -292 : i === 1 ? 712 : 882; return rep(5, j => R(x, 150 + j * 22, n2(30 + (Math.sin(t * 1.6 + i * 2 + j) * .5 + .5) * 50), 12, i === 0 ? '#7dffb4' : '#ffd23f', 2, 0)); });
        const relogio = R(600, 56, 130, 44, '#10131d', 6, 4) + TS(665, 86, `T+${String(Math.floor(t) % 60).padStart(2, '0')}:${String(Math.floor(t * 30) % 100).padStart(2, '0')}`, 24, '#ff5a4d');
        return parede + telaFixa + orb + C(n2(bx), n2(by), 10, '#ff5a4d', 3) + C(n2(bx), n2(by), n2(10 + (t * 30 % 26)), 'none', 3, `opacity="${n2(1 - (t * 30 % 26) / 26)}"`) +
          sMon + banner + relogio + resto + pisos + fileiraFundo + mon +
          f2 + f3 +
          leds(-220, 700, 8, t, 3, 26) + leds(520, 700, 8, t, 8, 26) +
          G(`translate(${n2(620 + Math.sin(t * 1.3) * 8)} 774)`, rep(3, i => L(`M${i * 12} 0q6-10 0-20`, '#fff', 3, 'opacity=".7"'))) +
          prop('coffee_mug', t, 240, 815, .5) + prop('coffee_mug', t, 500, 815, .5) + R(20, 1000, 90, 110, '#39a96b', 8, 5) + T(65, 1060, 'LIXO', 20, '#fff') + C(52, 992, 14, '#fff', 3) + C(74, 996, 12, '#ffb0c8', 3) + R(590, 960, 120, 16, '#c8cfd8', 4, 5) + R(600, 976, 14, 96, '#8d99a8', 3, 4) + R(686, 976, 14, 96, '#8d99a8', 3, 4) + R(590, 1040, 120, 12, '#c8cfd8', 4, 4) + prop('donut', t, 620, 936, .4) + prop('coffee_mug', t, 680, 936, .4) + C(606, 1078, 8, '#2d3a52', 3) + C(694, 1078, 8, '#2d3a52', 3) + TS(650, 1100, 'CAFÉ Nº 14', 15, '#fff');
      };
    });

  def('tv_studio', 'Estúdio de telejornal: painel de LED, bancada, câmeras, spots no teto, letreiro correndo e luz NO AR.',
    { state: { headline: 'URGENTE', ticker: 'ESTAÇÃO ASTRA-9 PERDE OXIGÊNIO • ZÉ DIZ QUE A FITA RESOLVE • CIENTISTAS DISCORDAM' } }, { sirenes: [[-40, 70], [760, 70]], noite: '#10144f', noiteOp: .12 }, (tod, s) => {
      const head = V.esc(s.headline || 'URGENTE');
      const tick = V.esc(s.ticker || 'ESTAÇÃO ASTRA-9 PERDE OXIGÊNIO • ZÉ DIZ QUE A FITA RESOLVE • CIENTISTAS DISCORDAM');
      const fundo = R(-340, -340, 1400, 1240, gv('#2a5bd8', '#16349a'), 0, 0) +
        /* painéis curvos com arranha-céus */
        rep(9, i => P(`M${-340 + i * 175} 880V${540 - (i % 3) * 90 - rnd(i) * 80}h${80 + rnd(i + 2) * 70}V880z`, '#2f6fea', 3, 'opacity=".75"')) +
        rep(9, i => rep(5, j => rep(3, k => R(-326 + i * 175 + k * 26, 620 + j * 46, 14, 22, '#ffd97a', 1, 0, 'opacity=".75"')))) +
        R(60, 150, 600, 320, '#0d1e5c', 16, 7) + R(72, 162, 576, 296, gv('#e8352b', '#a81f25'), 8, 4) + T(360, 300, head, Math.min(120, 960 / Math.max(head.length, 1)), '#fff') + TS(360, 350, 'AO VIVO DA TERRA', 26, '#ffd23f') + logoAstra(610, 200, .9) +
        R(-280, 160, 280, 290, '#ffd23f', 10, 6) + T(-140, 230, 'CANAL', 44) + T(-140, 300, 'ÓRBITA', 56, '#d9483b') + T(-140, 350, 'NEWS', 40) + R(720, 160, 280, 290, '#0d1e5c', 10, 6) + TS(860, 225, 'CLIMA EM ÓRBITA', 22, '#fff') + T(860, 320, '-270°C', 66, '#6fd3ff') + TS(860, 380, 'chance de vácuo: 100%', 19, '#fff');
      const teto = R(-340, -340, 1400, 400, '#2d3a52', 0, 5) + R(-340, 56, 1400, 16, '#8d99a8', 0, 4) + rep(9, i => L(`M${-300 + i * 170} 72l20 -16l20 16`, O, 3));
      const bancada = P('M-200 900Q360 700 920 900V960H-200z', '#ffffff', 6) + P('M-160 898Q360 740 880 898', 'none', 6) + R(-200, 880, 1120, 80, '#d9483b', 8, 6) + T(360, 934, 'CANAL ÓRBITA', 40, '#fff', { ls: 4 }) +
        R(-340, 960, 1400, 800, gv('#3a4770', '#232c4e'), 0, 0) + L('M-340 960H1060', O, 6) + rep(9, i => L(`M${-340 + i * 170} 960L${-660 + i * 250} 1760`, '#55628c', 3)) +
        L('M300 1110h120M360 1080v60', '#ffd23f', 7) +
        sticky(160, 1200, 'SORRIA', 'SEMPRE', '#ffe66b', -6) + cable(-320, 1120, 150, 1240, 40, '#ffb545', 8) + cable(1040, 1180, 620, 1240, 50, '#39d98a', 8);
      const cam = (x, y, fl) => G(`translate(${x} ${y}) scale(${fl} 1)`, L('M0 0L-44 150M0 0L44 150M0 0V160', O, 9), R(-70, -80, 130, 80, '#55697f', 10, 5), R(60, -66, 44, 52, '#2d3a52', 6, 5), C(104, -40, 16, '#6fd3ff', 4), R(-50, -112, 70, 34, '#fff', 4, 4), TS(-15, -88, 'SORRIA', 12));
      return t => {
        const spots = rep(7, i => { const x = -200 + i * 190; const on = Math.sin(t * .8 + i) * 16; return `<path d="M${x} 78L${x - 120 + on} 900H${x + 120 + on}z" fill="#fff" opacity=".055"/>` + G(`translate(${x} 72) rotate(${n2(on * .5)})`, R(-20, 0, 40, 40, '#2d3a52', 6, 4), E(0, 42, 18, 7, i % 2 ? '#fff4b0' : '#fff', 3)); });
        const w = 18 * tick.length;
        const x = 720 - (t * 120) % (w + 720);
        const ticker = R(-340, 490, 1400, 56, '#ffd23f', 0, 6) + `<clipPath id="clip_tick"><rect x="-340" y="490" width="1400" height="56"/></clipPath><g clip-path="url(#clip_tick)">${T(n2(x), 532, tick, 36, O, { a: 'start' })}${T(n2(x - w - 60), 532, tick, 36, O, { a: 'start' })}</g>` + R(-340, 490, 480, 56, '#d9483b', 0, 6) + T(72, 532, 'URGENTE', 36, '#fff');
        const noAr = G('translate(650 96)', R(-62, -24, 124, 48, Math.sin(t * 2.5) > -.5 ? '#ff2a2a' : '#7a1a1a', 8, 5), T(0, 13, 'NO AR', 32, '#fff'));
        return fundo + ticker + teto + spots + bancada + cam(76, 1010, 1) + cam(644, 1010, -1) + noAr +
          G(`translate(${n2(120 + Math.sin(t * .7) * 18)} 56)`, L('M0 0V170', O, 5), E(0, 180, 20, 12, '#55697f', 4)) +
          prop('coffee_mug', t, 620, 872, .5) + leds(-140, 940, 5, t, 2, 24) + leds(720, 940, 5, t, 5, 24);
      };
    });

  /* ================= TERRA: CÉU E PRÉDIOS ================= */
  const ceu = (tod) => tod === 'night' ? gv('#141a5c', '#4a3a9c') : tod === 'alert' ? gv('#ff7a4c', '#ffd08a') : gv('#62c6ff', '#d8f3ff');
  const janelaCeu = (x, y, w, h, tod, t) => R(x, y, w, h, ceu(tod), 4, 6) + (tod === 'night' ? C(x + w * .7, y + h * .35, Math.min(w, h) * .16, '#fff4c0', 3) + starfield(8, 10, x + 6, y + 6, w - 12, h * .7) : C(x + w * .7, y + h * .35, Math.min(w, h) * .17, '#ffd23f', 4)) +
    (tod !== 'night' ? G(`translate(${n2(x + (t * 6) % w)} ${y + h * .3})`, E(0, 0, 26, 11, '#fff', 3)) : '');
  const nuvem = (x, y, s = 1) => G(`translate(${n2(x)} ${y}) scale(${s})`, P('M-60 16q-6-26 22-26 8-26 40-16 30-14 42 14 26 0 22 28z', '#fff', 5));
  const nuvens = (t, tod) => tod === 'night' ? '' : rep(5, i => nuvem(-300 + ((i * 310 + t * (6 + i)) % 1500), 90 + (i * 83) % 240, .8 + (i % 3) * .3));
  const predio = (x, y, w, c, seed, tod) => {
    let s = R(x, y, w, 900 - y, c, 4, 5); const cols = Math.floor((w - 16) / 34), rows = Math.floor((880 - y - 20) / 46);
    for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) { const lit = rnd(seed + i * 11 + j * 3) > .45; s += R(x + 14 + i * 34, y + 18 + j * 46, 22, 30, tod === 'night' ? (lit ? '#ffd97a' : '#2a2f6a') : (lit ? '#c9f0ff' : '#8fd6ff'), 2, 3); }
    return s;
  };
  const arvore = (x, y, s = 1, c = '#46b36b') => G(`translate(${x} ${y}) scale(${s})`, R(-12, -70, 24, 90, '#8d5a35', 4, 5), C(-34, -90, 40, c, 5), C(32, -96, 44, c, 5), C(0, -136, 48, c, 5), C(-14, -100, 30, c, 0));

  def('ze_home', 'Quarto bagunçado do Zé: cama, PC gamer, pôsteres, caixas de pizza, roupa e lixo pelo chão, moscas.',
    { state: { clean: false } }, { sirenes: [[360, 40]], noite: '#1a1d6b', noiteOp: .2 }, (tod, s) => {
      const limpo = !!s.clean;
      const parede = R(-340, -340, 1400, 1240, gv('#3a55b8', '#2a3f96'), 0, 0) + rep(28, i => L(`M${-330 + i * 52} -340V880`, '#3248a6', 12)) +
        poster(20, 120, 140, 190, '#2a6fd8', 'LVL 99', '', -6, P('M90 140l40 90h-80z', '#ffd23f', 4)) + poster(574, 100, 120, 130, '#d9483b', 'GAME', 'OVER', 4) +
        poster(-180, 120, 130, 170, '#39a96b', 'BRASIL', '94', 3, C(-115, 190, 34, '#ffd23f', 4)) +
        R(190, 100, 130, 300, '#a81f45', 6, 5) + L('M230 100v300M280 100v300', '#7a1533', 8) + T(255, 240, 'Z', 66, '#ffd23f') +
        /* calendário */
        R(24, 340, 130, 130, '#fff', 4, 5) + R(24, 340, 130, 30, '#d9483b', 4, 4) + T(89, 363, 'OUTUBRO', 20, '#fff') + T(89, 440, '30', 58, O) + L('M49 390l80 60M129 390l-80 60', '#d9483b', 5) +
        sticky(180, 410, 'PAGAR A', 'LUZ!!!', '#ffe66b', 5) +
        /* estante */
        shelfRow(560, 490, 220, '#c98d4e') + rep(6, i => R(570 + i * 22, 410, 20, 80, ['#d9483b', '#2a8fd8', '#ffd23f', '#39a96b', '#b48cff', '#ff9a3c'][i], 2, 3)) + P('M725 490v-26h-14v-26h36v26h-14v26zM700 430h60l-4 -30h-52z', '#ffd23f', 4);
      const cama = R(-340, 700, 500, 180, '#3a82b4', 12, 5) + P('M-340 660h400q40 0 40 40v40h-440z', '#8fbbe8', 5) + E(30, 690, 76, 30, '#fff', 5) + L('M-40 740q40 30 80 10', O, 4) + R(150, 690, 16, 190, '#8d6a45', 4, 5) +
        (limpo ? '' : P('M20 700q60-18 110 0t10 50-110 10z', '#7a5cb8', 4));
      const pc = /* mesa e cadeira gamer */
        R(500, 640, 340, 18, '#8d6a45', 4, 5) + R(520, 658, 16, 222, '#6b4726', 3, 4) + R(810, 658, 16, 222, '#6b4726', 3, 4) +
        R(555, 526, 170, 110, '#14182a', 8, 5) + R(632, 628, 16, 14, '#55697f', 2, 3) + R(740, 520, 66, 120, '#2d3a52', 6, 5) + 
        G('translate(90 40)', P('M660 840l-20-40h80l-20 40z', '#55697f', 5), P('M628 800V600q0-44 40-44h50q44 0 44 44V800z', '#d9483b', 6), L('M695 556V800', O, 12));
      const chao = R(-340, 880, 1400, 900, gv('#6a4a3a', '#3f2c2a'), 0, 0) + rep(10, i => L(`M-340 ${900 + i * i * 9}H1060`, '#2f2020', 4)) + rep(14, i => L(`M${-340 + i * 110} 880L${-640 + i * 180} 1760`, '#2f2020', 3)) + L('M-340 880H1060', O, 6) + E(360, 1140, 330, 80, '#b03a56', 5) + E(360, 1140, 270, 56, 'none', 4, 'stroke-dasharray="14 10"');
      const bagunca = limpo ? '' :
        rep(5, i => R(14 - (i % 2) * 8, 1100 - i * 22, 170, 24, '#e8c07a', 3, 4)) + T(98, 1120 - 2, 'PIZZA', 18, '#d9483b') +
        R(90, 1190, 150, 70, '#c98d4e', 4, 5, 'transform="rotate(10 165 1225)"') + P('M-40 1230l60-32 40 50-60 30z', '#ffd23f', 4) +
        P('M520 1050l60-26 80 12 26 50-30 16-20-30v60h-90v-50l-30 16z', '#d9483b', 4) + R(690, 930, 90, 130, '#55697f', 8, 5) + L('M690 960h90', O, 4) + C(715, 920, 18, '#fff', 4) + C(745, 915, 16, '#efe3c8', 4) +
        R(620, 1180, 40, 26, '#d9483b', 4, 4) + R(-30, 1110, 26, 44, '#2a8fd8', 5, 4, 'transform="rotate(70 -17 1132)"') + P('M90 1090l14-10 22 14-10 12z', '#fff', 3) + R(300, 1290, 80, 20, '#fff', 3, 3);
      return t => {
        const tela = R(562, 533, 156, 96, tod === 'night' ? '#20e080' : '#2a8fd8', 4, 3) + TS(640, 560, 'GAME', 15, '#fff') + rep(5, i => R(576 + i * 26, n2(620 - (Math.sin(t * 3 + i) * .5 + .5) * 40), 14, n2(4 + (Math.sin(t * 3 + i) * .5 + .5) * 40), '#fff', 2, 0)) ;
        const gabinete = rep(3, i => C(773, 545 + i * 26, 8, ['#ff5a4d', '#39d98a', '#6fd3ff'][Math.floor((t * 2 + i) % 3)], 3));
        return parede + janelaCeu(340 + 8, 90, 200, 230, tod, t) + L('M448 90v230M348 200h200', O, 5) + R(330, 320, 236, 18, '#fff', 4, 4) +
          P('M340 80q70 120 18 250l-40-4q30-130-10-246z', '#d9483b', 5) + P('M556 80q-40 120 6 250l44-4q-30-130 8-246z', '#d9483b', 5) +
          R(-340, 862, 1400, 22, '#efe7d6', 0, 4) + cama + pc + tela + gabinete + chao + bagunca +
          (limpo ? rep(5, i => G(`translate(${120 + i * 120} ${1000 + (i % 2) * 40}) scale(${n2(.8 + Math.sin(t * 4 + i) * .2)})`, `<path d="M0 -14L3 -3L14 0L3 3L0 14L-3 3L-14 0L-3 -3z" fill="#fff"/>`)) : stink(70, 980, t) + stink(130, 970, t, 1) + stink(735, 900, t, 2) + stink(610, 1010, t, 3) + flyes(t, 100, 960, 2) + flyes(t + 3, 720, 880, 3) + flyes(t + 5, 300, 400, 2, 60));
      };
    });

  def('kitchen', 'Cozinha da casa: geladeira cheia de recados, pia com louça, fogão, armários, moscas e janela.',
    { state: { clean: false } }, { sirenes: [[360, 60]], noite: '#1a1d6b', noiteOp: .24 }, (tod, s) => {
      const limpo = !!s.clean;
      const parede = R(-340, -340, 1400, 1240, gv('#fbe9b8', '#f2d690'), 0, 0) +
        rep(14, i => rep(5, j => R(-340 + i * 100 + (j % 2) * 50, 560 + j * 44, 100, 44, j % 2 ? '#d6f0ee' : '#c3e8e4', 0, 2))) + R(-340, 556, 1400, 8, '#fff', 0, 3);
      const armarios = rep(4, i => R(-300 + i * 200, 110, 190, 230, '#d9a15f', 6, 5) + R(-285 + i * 200, 124, 160, 202, '#e6b474', 4, 3) + C(-130 + i * 200, 300, 8, '#ffd23f', 3)) +
        rep(2, i => R(620 + i * 200, 110, 190, 150, '#d9a15f', 6, 5) + C(790 + i * 200, 230, 8, '#ffd23f', 3));
      const bancada = R(-340, 700, 960, 26, '#efe7d6', 4, 5) + R(-340, 726, 960, 156, '#d9a15f', 0, 5) + rep(5, i => R(-320 + i * 190, 740, 170, 130, '#e6b474', 6, 4) + C(-170 + i * 190, 800, 7, '#ffd23f', 3));
      const pia = G('translate(290 0)', R(-120, 690, 260, 18, '#c8cfd8', 6, 4), L('M40 690V620q0-30 34-30', O, 14), L('M40 690V620q0-30 34-30', '#c8cfd8', 6),
        limpo ? '' : rep(6, i => E(-50 + (i % 2) * 8, 684 - i * 13, 66, 9, ['#fff', '#b6e0f0', '#fff4b0'][i % 3], 3)) + P('M60 680l20-60 40 8-16 56z', '#ffb545', 4));
      const geladeira = R(560, 400, 240, 482, '#f4f8fb', 16, 6) + L('M560 560h240', O, 5) + R(578, 450, 12, 80, '#8d99a8', 5, 3) + R(578, 590, 12, 120, '#8d99a8', 5, 3) +
        sticky(620, 430, 'COMPRAR', 'TUDO', '#ffe66b', -4) + sticky(690, 600, 'DÍVIDA', 'R$ 340', '#ffb0c8', 5) + photo(614, 610, 'cao', -5, .8) + note(690, 410, 90, 110, 'LISTA', ['ovo', 'pão', 'fé'], '#fff', 3) +
        C(630, 750, 16, '#ff5a4d', 3) + C(700, 780, 16, '#39d98a', 3);
      const fogao = G('translate(320 0)', R(-300, 660, 150, 46, '#c8cfd8', 6, 5), E(-262, 660, 26, 7, O, 0), E(-186, 660, 26, 7, O, 0), R(-290, 600, 70, 56, '#d9483b', 10, 5), L('M-290 620h-30', O, 8));
      const chao = R(-340, 880, 1400, 900, gv('#d8a868', '#a8743e'), 0, 0) + rep(14, i => L(`M${-340 + i * 110} 880L${-640 + i * 180} 1760`, '#8d5a35', 4)) + rep(6, i => L(`M-340 ${900 + i * i * 22}H1060`, '#8d5a35', 4)) + L('M-340 880H1060', O, 6) +
        (limpo ? '' : P('M-20 1140q60-30 140-10t30 40-130 20-40-50z', '#7ac24e', 4) + rep(5, i => R(610 + (i % 2) * 8, 1020 - i * 22, 170, 24, '#e8c07a', 3, 4))) +
        R(20, 910, 100, 150, '#46804e', 8, 5) + L('M20 930h100', O, 5) + R(10, 900, 120, 16, '#2f6b3a', 5, 5);
      return t => {
        const hora = Math.floor(t) % 60;
        return parede + 
          armarios + janelaCeu(150, 370, 300, 180, tod, t) + L('M300 370v180M150 460h300', '#fff', 8) + L('M300 370v180M150 460h300', O, 2) + R(136, 546, 328, 14, '#fff', 3, 4) + P('M150 370q80 30 150 0v30q-80 24-150 0z', '#ff8a9c', 4) +
          prop('plant', t, 200, 700 - 164, .4) +
          bancada + pia + geladeira + fogao + chao +
          
          G('translate(70 460)', R(-72, -48, 144, 96, '#55697f', 6, 5), R(-62, -38, 100, 76, '#203a58', 3, 3), R(46, -30, 20, 16, '#39d98a', 2, 2), TS(56, 2, '0:' + String(hora).padStart(2, '0'), 11, '#fff')) +
          C(520, 340, 44, '#fff', 5) + G(`translate(520 340) rotate(${n2(t * 12)})`, L('M0 0V-32', O, 4)) + G('translate(520 340) rotate(120)', L('M0 0V-22', O, 5)) +
          drip(364, 600, 84, t, 1) + (limpo ? '' : stink(260, 590, t) + stink(390, 610, t, 2) + flyes(t, 280, 600, 3) + flyes(t + 2, 680, 1000, 2)) +
          steamPuff(65, 600, t, 4, 5, 60);
      };
    });

  def('street_city', 'Rua da cidade: prédios coloridos, árvores, ponto de ônibus, farmácia, hidrante, carros e pombos.',
    { state: {} }, { sirenes: [], noite: '#10144f', noiteOp: .1 }, (tod, s) => {
      const fundo = R(-340, -340, 1400, 1300, ceu(tod), 0, 0);
      const longe = rep(9, i => P(`M${-340 + i * 170} 880V${330 + rnd(i + 2) * 180}h${150}V880z`, tod === 'night' ? '#39409a' : '#b9d8f0', 0));
      const prd = predio(-340, 240, 200, '#e8c07a', 1, tod) + predio(-130, 360, 210, '#ff9aa8', 2, tod) + predio(90, 300, 180, '#b48cff', 3, tod) + predio(280, 420, 170, '#ffb545', 4, tod) + predio(460, 260, 220, '#6fd3a0', 5, tod) + predio(690, 340, 190, '#7fb3e8', 6, tod) + predio(890, 240, 180, '#ff9a6c', 7, tod);
      const lojas = G('translate(120 0)', R(-130, 720, 210, 180, '#fff4d6', 4, 5), R(-140, 700, 230, 44, '#2a8fd8', 4, 5), T(-25, 732, 'FARMÁCIA', 30, '#fff'), R(-110, 760, 80, 140, '#6b4726', 4, 5), R(-20, 760, 90, 80, '#bfeaff', 3, 4), P('M-3 776h16v14h14v16h-14v14h-16v-14h-14v-16h14z', '#39a96b', 3)) +
        R(460, 720, 220, 180, '#fff', 4, 5) + R(450, 700, 240, 44, '#d9483b', 4, 5) + T(570, 732, 'PADARIA', 32, '#fff') + R(480, 760, 110, 80, '#bfeaff', 3, 4) + rep(3, i => E(505 + i * 30, 812, 13, 9, '#d8a463', 3)) + R(604, 760, 62, 140, '#6b4726', 4, 5) +
        P('M450 744h240l20 40h-280z', '#ffe0e0', 5) + rep(6, i => P(`M${450 + i * 40} 744h20l-6 40h-34z`, '#d9483b', 0));
      const calcada = R(-340, 890, 1400, 300, gv('#e4e8ee', '#c6ced8'), 0, 0) + rep(11, i => L(`M${-340 + i * 150} 890L${-500 + i * 190} 1190`, '#a9b3bf', 3)) + [940, 1020, 1120].map(y => L(`M-340 ${y}H1060`, '#a9b3bf', 3)).join('') + L('M-340 890H1060', O, 5);
      const rua = R(-340, 1190, 1400, 30, '#a9b3bf', 0, 5) + R(-340, 1220, 1400, 560, '#4a5266', 0, 5) + rep(8, i => R(-300 + i * 200, 1390, 110, 16, '#ffd23f', 3, 0));
      const hidrante = G('translate(610 1050)', R(-24, -66, 48, 90, '#d9483b', 8, 5), P('M-24 -66q24-34 48 0z', '#d9483b', 5), R(-40, -44, 80, 20, '#b03329', 6, 4), R(-30, 22, 60, 12, '#8d99a8', 3, 4));
      const ponto = G('translate(-180 890)', R(-120, -150, 16, 240, '#55697f', 3, 4), R(120, -150, 16, 240, '#55697f', 3, 4), R(-140, -170, 300, 26, '#3a82b4', 6, 5), R(-90, 30, 200, 18, '#c98d4e', 4, 4), R(-80, -126, 160, 130, '#fff4d6', 4, 4), T(0, -96, 'BUSÃO', 22), TS(0, -70, 'atrasado desde', 15), TS(0, -50, '2019', 18, '#d9483b'));
      const poste = G('translate(690 900)', R(-8, -420, 16, 620, '#55697f', 5, 4), P('M0 -420q60-30 80 10', 'none', 8), E(80, -404, 24, 12, tod === 'day' ? '#fff' : '#ffe680', 4));
      return t => {
        const carro = (x, y, c, dir) => G(`translate(${n2(x)} ${y}) scale(${dir} 1)`, P('M-120 0v-40q0-14 20-14l40-40h90l50 40h30q20 0 20 20v34z', c, 6), R(-48, -84, 50, 32, '#bfeaff', 4, 4), R(10, -84, 42, 32, '#bfeaff', 4, 4), C(-74, 2, 24, '#2d3a52', 6), C(70, 2, 24, '#2d3a52', 6), C(-74, 2, 8, '#c8cfd8', 3), C(70, 2, 8, '#c8cfd8', 3), C(128, -22, 6, '#ffd97a', 3));
        const cx = -500 + (t * 220) % 2000, c2 = 1300 - (t * 170 + 900) % 2000;
        const pombo = i => G(`translate(${-40 + i * 60 + Math.sin(t * .8 + i) * 30} ${1160 - (i % 2) * 14}) scale(${i % 2 ? -1 : 1} 1)`, E(0, 0, 18, 12, '#a9b3bf', 4), C(16, -12, 8, '#a9b3bf', 4), P('M23 -13l8 3-8 3z', '#ffb545', 2), L('M-4 12v10M4 12v10', '#ff9a3c', 3));
        const sirene = tod === 'alert' ? G('translate(330 1300)', carro(0, 0, '#fff', 1), R(-34, -112, 68, 16, Math.sin(t * 10) > 0 ? '#ff2a2a' : '#2a6fff', 4, 4), `<circle cx="0" cy="-104" r="${n2(120 + Math.sin(t * 10) * 30)}" fill="${Math.sin(t * 10) > 0 ? '#ff2a2a' : '#2a6fff'}" opacity=".18"/>`) : '';
        return fundo + nuvens(t, tod) + (tod === 'night' ? C(560, 120, 44, '#fff4c0', 5) + starfield(6, 40, -300, -200, 1300, 500) : C(600, 150, 56, tod === 'alert' ? '#ff5a2a' : '#ffd23f', 5) + rep(10, i => L(`M${n2(600 + Math.cos(i * .63 + t * .2) * 72)} ${n2(150 + Math.sin(i * .63 + t * .2) * 72)}L${n2(600 + Math.cos(i * .63 + t * .2) * 92)} ${n2(150 + Math.sin(i * .63 + t * .2) * 92)}`, '#ffd23f', 6))) +
          longe + prd + lojas + calcada + arvore(300, 900, 1.15) + arvore(410, 890, .85, '#58c26a') + arvore(860, 900, 1.2) + ponto + hidrante + poste + G('translate(70 1040)', R(-34, -70, 68, 100, '#39a96b', 8, 5), L('M-34 -46h68', O, 4), P('M-40 -70h80l-6-12h-68z', '#2f8c4f', 5), C(-10, -92, 11, '#fff', 3), C(12, -88, 9, '#efe3c8', 3), TS(0, -8, 'LIXO', 15, '#fff')) + rua +
          (tod !== 'day' ? `<ellipse cx="770" cy="960" rx="130" ry="50" fill="${fade('#ffe680')}"/>` : '') + carro(c2, 1320, '#ffb545', -1) + carro(cx, 1520, '#2a8fd8', 1) + rep(4, pombo) + sirene;
      };
    });

  def('supermarket', 'Supermercado: faixa do mercado, corredores lotados com preços, pirâmide de latas, carrinho e piso xadrez.',
    { state: { sign: 'MERCADO LEVA TUDO', aisle: 'CORREDOR 5' } }, { sirenes: [[360, 70]], noite: '#1a1d6b', noiteOp: .16 }, (tod, s) => {
      const nome = V.esc(s.sign || 'MERCADO LEVA TUDO'), corr = V.esc(s.aisle || 'CORREDOR 5');
      const prod = (x, y, k, seed) => {
        const c = ['#d9483b', '#2a8fd8', '#39a96b', '#ffd23f', '#b48cff', '#ff9a3c', '#ff5ac8', '#6fd3ff'][Math.floor(rnd(seed) * 8)];
        if (k === 0) return R(x + 6, y - 52, 22, 52, c, 8, 3) + R(x + 11, y - 66, 12, 16, c, 3, 3) + R(x + 8, y - 34, 18, 14, '#fff', 2, 0);
        if (k === 1) return R(x, y - 54, 36, 54, c, 3, 3) + C(x + 18, y - 28, 11, '#fff', 0);
        return R(x + 2, y - 42, 32, 42, c, 6, 3) + L(`M${x + 2} ${y - 32}h32M${x + 2} ${y - 10}h32`, O, 2);
      };
      const shelf = (x, w, yy) => yy.map((y, r) => shelfRow(x, y, w, '#e8e0c8') + rep(Math.floor(w / 38), i => prod(x + 2 + i * 38, y, Math.floor(rnd(i * 3 + r * 7 + x) * 3), i * 13 + r * 29 + x)) + rep(Math.floor(w / 190), i => R(x + 16 + i * 190, y + 2, 70, 26, '#ffd23f', 3, 3) + TS(x + 51 + i * 190, y + 21, 'R$ ' + (1 + Math.floor(rnd(i + y) * 9)) + ',' + (rnd(i + y + 1) > .5 ? '99' : '49'), 15, '#d9483b'))).join('');
      const parede = R(-340, -340, 1400, 1240, gv('#fdf4dc', '#f1e4c0'), 0, 0);
      const faixa = R(-340, 80, 1400, 92, '#2f9c55', 0, 6) + T(360, 148, nome, Math.min(62, 1100 / Math.max(nome.length, 1)), '#fff', { ls: 2 }) + rep(2, i => C(30 + i * 660, 124, 14, '#ffd23f', 4));
      const est = shelf(-320, 1370, [330, 500, 670, 840]) + R(-340, 876 - 34, 1400, 44, '#d9a15f', 0, 5);
      const pil = (x, y, n) => { let s2 = ''; for (let r = 0; r < n; r++) for (let i = 0; i <= n - 1 - r; i++) s2 += R(x + i * 46 + r * 23, y - (r + 1) * 56, 42, 54, '#ff9a3c', 6, 4) + R(x + i * 46 + r * 23 + 5, y - (r + 1) * 56 + 18, 32, 20, '#fff', 2, 0); return s2; };
      const piso = R(-340, 880, 1400, 900, '#f2f2ee', 0, 0) + rep(9, j => rep(16, i => (i + j) % 2 ? P(`M${n2(360 + (i - 8) * (120 + j * 24))} ${880 + j * j * 10}h${n2(120 + j * 24)}l${n2((i - 7.5) * 24)} ${10 * (2 * j + 1)}h${n2(-(120 + (j + 1) * 24))}z`, '#d8dbe4', 0) : '')) + L('M-340 880H1060', O, 6);
      const carrinho = G('translate(100 1080)', P('M-110 -110h170l-20 92h-130z', '#dfe6ee', 5), rep(5, i => L(`M${-90 + i * 32} -110l6 92`, O, 3)), rep(3, i => L(`M-104 ${-80 + i * 26}h${150 - i * 6}`, O, 3)), L('M60 -110l28-28h30', O, 7), C(-70, 14, 12, '#2d3a52', 4), C(30, 14, 12, '#2d3a52', 4), L('M-90 -18l20 30M40 -18l-10 30', O, 5), R(-70, -148, 46, 40, '#39a96b', 6, 4), R(-20, -140, 54, 32, '#ffd23f', 4, 4));
      const placa = t => G(`translate(360 228) rotate(${n2(Math.sin(t * .9) * 2)})`, L('M-80 -60V-24M80 -60V-24', O, 5), R(-120, -26, 240, 62, '#ffd23f', 6, 6), T(0, 20, corr, 34, O));
      const promo = (x, y, a, b, r) => G(`translate(${x} ${y}) rotate(${r})`, rep(12, i => P('M0 0L14 -74L-14 -74z', '#ff2a2a', 0, `transform="rotate(${i * 30})"`)), C(0, 0, 62, '#ff2a2a', 0), T(0, -6, a, 26, '#fff'), T(0, 24, b, 26, '#ffd23f'));
      return t => {
        const luz1 = rep(5, i => { const f = Math.sin(t * 19 + i * 5) > .95; return R(-220 + i * 240, 20, 180, 24, f ? '#b8c0c8' : '#fff', 8, 4); });
        return parede + R(-340, -340, 1400, 400, '#dfe6ee', 0, 5) + luz1 + faixa + est + piso + pil(560, 960, 4) + R(555, 966, 190, 34, '#fff', 4, 4) + T(650, 992, 'LEVE 3, PAGUE 3', 22, '#d9483b') + carrinho + placa(t) +
          G(`translate(${n2(90 + Math.sin(t) * 3)} 330)`, promo(0, 0, 'SÓ', 'HOJE', -8)) + G(`translate(640 ${n2(330 + Math.sin(t * 1.3) * 3)})`, promo(0, 0, '50%', 'OFF?', 8)) +
          G('translate(300 1240)', P('M-50 40L-30 -50H30L50 40z', '#ffd23f', 5), T(0, -10, 'PISO', 22), T(0, 16, 'MOLHADO', 16, '#d9483b')) + E(520, 1200, 90, 18, '#8fdcff', 4, 'opacity=".8"');
      };
    });

  def('hospital', 'Quarto de hospital: leito, monitor cardíaco, soro pingando, cortina, cadeira de rodas e cartazes.',
    { state: { flatline: false } }, { sirenes: [[360, 70]], noite: '#1a2a78', noiteOp: .22 }, (tod, s) => {
      const parede = R(-340, -340, 1400, 1240, gv('#e2f5ee', '#bfe6da'), 0, 0) + R(-340, 620, 1400, 262, '#9fd8c8', 0, 5) + R(-340, 610, 1400, 16, '#fff', 0, 4);
      const teto = R(-340, -340, 1400, 400, '#f4f8fb', 0, 5) + rep(4, i => R(-200 + i * 280, 56, 200, 20, '#fff', 8, 4));
      /* cortina aberta, amontoada à esquerda */
      const cortina = L('M-340 112H1060', '#8d99a8', 8) + rep(5, i => P(`M${-320 + i * 76} 116q34 300 0 760h76q-34 -460 0 -760z`, i % 2 ? '#7fd4c8' : '#93e0d4', 4));
      const cartazes = sign(90, 130, 200, 66, '#fff', 'SILÊNCIO', '#2a8fd8', 34) + poster(310, 130, 150, 200, '#2a8fd8', 'LAVE', 'AS MÃOS', 3, rep(4, i => R(346 + i * 22, 160, 15, 60, '#efe3c8', 8, 3)) + P('M344 206h86v32q0 18-18 18h-50q-18 0-18-18z', '#efe3c8', 3)) +
        note(120, 220, 160, 130, 'PACIENTE', ['Nome: Zé', 'Pressão: alta', 'Conta: mais', 'alta ainda'], '#fff', -3) + photo(480, 170, 'familia', 5, .8) + sticky(30, 360, 'NÃO', 'FUGIR', '#ffe66b', -6);
      const cruz = P('M630 100h34v34h34v34h-34v34h-34v-34h-34v-34h34z', '#d9483b', 5);
      const leito = G('translate(180 880)', R(-200, -70, 420, 32, '#c8cfd8', 6, 5), R(-200, -130, 420, 62, '#fff', 12, 5), E(-140, -142, 62, 26, '#fff', 5), R(-40, -142, 260, 80, '#7fb3e8', 10, 5), L('M40 -142v80M120 -142v80', '#5e94d0', 5), R(-214, -210, 22, 220, '#8d99a8', 8, 5), R(216, -180, 22, 190, '#8d99a8', 8, 5), C(-170, 20, 18, '#2d3a52', 4), C(190, 20, 18, '#2d3a52', 4), R(226, -130, 34, 60, '#fff', 3, 3));
      const chao = R(-340, 880, 1400, 900, gv('#dbe6ea', '#aebfca'), 0, 0) + rep(13, i => L(`M${-340 + i * 120} 880L${-700 + i * 210} 1760`, '#8ea5b4', 3)) + [930, 1010, 1130, 1320].map(y => L(`M-340 ${y}H1060`, '#8ea5b4', 3)).join('') + L('M-340 880H1060', O, 6);
      const cadeira = G('translate(610 1020)', C(0, 0, 66, 'none', 8), C(0, 0, 12, '#8d99a8', 4), L('M-60 -100h110v80M-40 -180V-100M-56 -190h30M50 -20l50 50h30', O, 9), L('M-60 -100h110v80', '#d9483b', 4), C(-46, 56, 12, '#2d3a52', 4));
      const armario = R(760, 420, 260, 460, '#f4f8fb', 8, 6) + L('M890 420v460', O, 4) + T(890, 500, 'REMÉDIOS', 34) + R(20, 980, 110, 90, '#f4f8fb', 6, 5) + L('M20 1020h110', O, 4) + C(75, 1000, 6, '#8d99a8', 3) + C(75, 1045, 6, '#8d99a8', 3);
      return t => {
        const pts = rep(26, i => { const x = i * 8; const q = (x + t * 110) % 110; const y = s.flatline ? 0 : q < 12 ? 0 : q < 18 ? -38 : q < 24 ? 30 : q < 30 ? -10 : 0; return `${i ? 'L' : 'M'}${x} ${n2(y)}`; });
        const mon = G('translate(500 340)', R(-20, -20, 240, 170, '#55697f', 10, 5), R(-8, -8, 216, 146, '#07261f', 4, 4), G('translate(0 66)', L(pts, s.flatline ? '#ff5a4d' : '#7dffb4', 4)), T(196, 26, s.flatline ? '--' : String(78 + Math.round(Math.sin(t * .5) * 6)), 34, s.flatline ? '#ff5a4d' : '#7dffb4', { a: 'end' }), TS(4, 18, 'BPM', 15, '#7dffb4', { a: 'start' }), TS(4, 128, 'SpO₂ 98%', 15, '#6fd3ff', { a: 'start' }), L('M100 150v230', O, 10), L('M60 380h80', O, 10));
        const soro = G('translate(450 720)', L('M0 160V-260', O, 8), L('M0 160V-260', '#c8cfd8', 3), L('M-30 -260h60', O, 6), P('M-30 -250h60v90q0 20-30 26-30-6-30-26z', '#dff4ff', 4), R(-24, -210, 48, 60, '#8fdcff', 8, 0), L('M0 -134v30', O, 3), R(-7, -104, 14, 26, '#fff', 3, 3), L('M0 -78Q-40 60 -120 20', O, 3), drip(0, -102, 16, t, 2), C(-20, 170, 12, '#2d3a52', 3), C(20, 170, 12, '#2d3a52', 3));
        return parede + teto + cartazes + cruz + mon + cortina + armario + chao + leito + soro + cadeira + prop('medkit', t, 75, 950, .5) + prop('pill_bottle', t, 120, 1160, .5) + prop('coffee_mug', t, 40, 962, .3);
      };
    });

  def('forest_camp', 'Acampamento na floresta: barraca, fogueira, troncos, mochila, lanterna, riacho e placa de onça.',
    { state: {} }, { sirenes: [], noite: '#10145a', noiteOp: .16 }, (tod, s) => {
      const fundo = R(-340, -340, 1400, 1400, ceu(tod), 0, 0);
      const noite = tod === 'night';
      const morros = P('M-340 620q200-200 420-40t320-60 300 80 400-100V900H-340z', noite ? '#2a4a7a' : '#8fd6a0', 5);
      const pinhe = (x, y, s2, c) => G(`translate(${x} ${y}) scale(${s2})`, R(-10, -30, 20, 40, '#6b4726', 3, 4), P('M0 -240l60 90h-30l50 76h-32l50 80H-98l50-80H-80l50-76h-30z', c, 5));
      const fundoArv = rep(11, i => pinhe(-320 + i * 136, 780 + (i % 2) * 30, 1 + (i % 3) * .2, noite ? '#27608a' : '#58b06e'));
      const meioArv = pinhe(-260, 900, 1.8, noite ? '#20507a' : '#3f9c5e') + pinhe(-60, 880, 1.4, noite ? '#1a4a6a' : '#46a866') + pinhe(780, 900, 1.8, noite ? '#20507a' : '#3f9c5e') + pinhe(620, 870, 1.3, noite ? '#1a4a6a' : '#46a866') + pinhe(960, 890, 1.6, noite ? '#20507a' : '#3f9c5e');
      const chao = R(-340, 880, 1400, 900, gv(noite ? '#5a9a6c' : '#8fd06a', noite ? '#3a6a50' : '#62a84e'), 0, 0) + L('M-340 880q300-30 700 0t700 0', O, 5) + rep(26, i => L(`M${n2(rnd(i) * 1340 - 320)} ${n2(900 + rnd(i + 40) * 700)}l-8 -18m8 18l6 -20m-6 20l14 -14`, '#3f8a44', 4)) +
        G('translate(-130 110)', P('M660 1040q120-40 300 0t120 200 -220 200-60-200-140-200z', '#6fd3ff', 5), L('M720 1100q50-20 100 0M760 1180q50-20 100 0', '#fff', 4, 'opacity=".7"'));
      const barraca = G('translate(120 880)', P('M-210 40L-30 -240L170 40z', '#ff9a3c', 6), P('M-30 -240L170 40L300 -30L100 -270z', '#e87a24', 6), P('M-70 40L-30 -130L30 40z', '#5c3a1e', 5), L('M-30 -240V-130', O, 4), L('M-210 40l-40 26M170 40l40 26M300 -30l40 26', O, 4));
      const placaOnca = G('translate(610 960)', R(-10, -100, 20, 120, '#8d5a35', 4, 5), R(-110, -190, 220, 96, '#e8c07a', 6, 5, 'transform="rotate(-3)"'), T(0, -146, 'CUIDADO', 34, '#d9483b'), T(0, -112, 'ONÇA (MANSA?)', 24));
      const toras = R(500, 1100, 170, 50, '#8d5a35', 25, 5) + C(668, 1125, 25, '#d8a463', 5) + L('M520 1116h110M540 1136h80', '#5c3a1e', 4) + R(-120, 1190, 170, 46, '#8d5a35', 22, 5) + C(50, 1213, 22, '#d8a463', 5);
      return t => {
        const fogo = G('translate(420 1020)', R(-60, 14, 120, 18, '#6b4726', 8, 4, 'transform="rotate(10)"'), R(-60, 14, 120, 18, '#8d5a35', 8, 4, 'transform="rotate(-10)"'),
          rep(3, i => { const h = 80 - i * 22 + Math.sin(t * 9 + i) * 10; return P(`M${-34 + i * 8} 14Q${-38 + i * 8} ${-h * .5} ${n2(Math.sin(t * 6 + i) * 8)} ${-h}Q${38 - i * 8} ${-h * .5} ${34 - i * 8} 14z`, ['#ff5a2a', '#ffb545', '#ffe680'][i], i ? 3 : 5); }));
        const faiscas = rep(8, i => { const f = (t * .6 + i / 8) % 1; return C(n2(420 + Math.sin(i * 2 + t) * 22 * f), n2(960 - f * 200), 3, '#ffb545', 0, `opacity="${n2(1 - f)}"`); });
        const glow = (noite || tod === 'alert') ? `<ellipse cx="420" cy="1020" rx="300" ry="170" fill="${fade('#ffb545')}" opacity=".5"/>` : '';
        const vaga = noite ? rep(16, i => C(n2(-200 + i * 80 + Math.sin(t * .7 + i) * 40), n2(760 + Math.cos(t * .9 + i * 2) * 120), 4, '#e8ff80', 0, `opacity="${n2(.5 + Math.sin(t * 3 + i) * .5)}"`)) : rep(3, i => G(`translate(${n2(100 + i * 200 + Math.sin(t * .4 + i) * 100)} ${n2(330 + Math.sin(t * 2.4 + i) * 12)})`, L(`M-14 0q7 ${n2(-8 - Math.sin(t * 9 + i) * 6)} 14 0q7 ${n2(-8 - Math.sin(t * 9 + i) * 6)} 14 0`, O, 4)));
        return fundo + (noite ? C(560, 190, 56, '#fff4c0', 5) + starfield(7, 70, -300, -200, 1300, 700) + twinkle(t, 5, 8, -200, -100, 1100, 500) : C(120, 210, 62, tod === 'alert' ? '#ff5a2a' : '#ffd23f', 5)) +
          nuvens(t, tod) + morros + fundoArv + meioArv + chao + barraca + placaOnca + toras + glow + fogo + faiscas +
          prop('backpack', t, 80, 1120, .9) + prop('thermos', t, 200, 1190, .7) + prop('rope', t, 480, 1200, .7) + vaga + G(`translate(${n2(640 + Math.sin(t) * 6)} 1250)`, L('M-40 0q40-10 80 0', '#fff', 4, 'opacity=".6"'));
      };
    });

  def('rooftop_night', 'Terraço de prédio à noite: horizonte iluminado, lua, caixa d\'água, antenas, varal e luminoso.',
    { state: {} }, { sirenes: [], noite: '#10144f', noiteOp: .05 }, (tod, s) => {
      const c0 = tod === 'alert' ? gv('#4a1a5c', '#d9483b') : tod === 'day' ? gv('#3a5ab8', '#ff9a8a') : gv('#141a5c', '#5a3aa8');
      const fundo = R(-340, -340, 1400, 1300, c0, 0, 0) + starfield(4, 90, -340, -340, 1400, 900);
      const n = 'night';
      const skyline = predio(-340, 500, 180, '#343a8a', 1, n) + predio(-150, 420, 150, '#3f3a9c', 2, n) + predio(10, 540, 170, '#2f4a9a', 3, n) + predio(190, 400, 160, '#4a3aa8', 4, n) + predio(360, 520, 180, '#343a8a', 5, n) + predio(550, 360, 170, '#3f3a9c', 6, n) + predio(730, 480, 180, '#2f4a9a', 7, n) + predio(920, 430, 150, '#4a3aa8', 8, n);
      const mureta = R(-340, 800, 1400, 110, '#b9a8c8', 0, 6) + R(-340, 792, 1400, 20, '#dfd6e8', 0, 5) + rep(12, i => L(`M${-300 + i * 120} 812V900`, '#8d7ea8', 3));
      const piso = R(-340, 900, 1400, 900, gv('#9a8ac0', '#6a5a96'), 0, 0) + L('M-340 900H1060', O, 6) + rep(10, i => L(`M${-340 + i * 160} 900L${-700 + i * 270} 1760`, '#5a4a86', 3)) + rep(8, i => E(n2(rnd(i) * 1200 - 260), n2(960 + rnd(i + 3) * 500), 40, 10, '#5a4a86', 0, 'opacity=".4"'));
      const caixa = G('translate(70 800)', L('M-70 100L-40 -50M70 100L40 -50M-60 40H60', O, 10), P('M-90 -220h180v170q-90 30-180 0z', '#d8a463', 6), L('M-90 -170h180M-90 -110h180', O, 4), P('M-100 -220q100-70 200 0z', '#8d5a35', 6));
      const antena = L('M640 800V380M590 450h100M600 500h80M610 550h60', O, 7) + L('M640 800V380', '#c8cfd8', 2);
      const arCond = G('translate(620 960)', R(-90, -70, 180, 130, '#c8cfd8', 8, 5), vent(-76, -56, 90, 100));
      const cadeira = G('translate(90 1090)', L('M-46 10V70M46 10V70M-30 10V70M30 10V70', O, 8), R(-54, -6, 108, 18, '#fff', 8, 5), R(-48, -96, 96, 56, '#fff', 12, 5), L('M-36 -44V-6M36 -44V-6', O, 8), L('M-26 -78h52M-26 -62h52', '#a9b3bf', 4), R(64, 34, 30, 36, '#39a96b', 4, 4));
      return t => {
        const lum = Math.sin(t * 5) * Math.sin(t * 2.3) > -.75;
        const neon = G('translate(250 380)', R(-140, -50, 280, 90, '#14182a', 6, 5), L('M-110 40V170M110 40V170', O, 8), T(0, 20, 'HOTEL', 60, lum ? '#ff5ac8' : '#5a2a5a'));
        const varal = L('M-340 700Q240 780 700 690', O, 4) + rep(4, i => G(`translate(${170 + i * 110} ${735 + (i % 2) * 8}) rotate(${n2(Math.sin(t * 1.3 + i) * 7)})`, P('M-34 0h68v84h-68z', ['#fff', '#ff9ac0', '#7fb3e8', '#ffd97a'][i], 4)));
        const feixe = tod === 'alert' ? G(`translate(${n2(480 + Math.sin(t * .6) * 180)} 40) rotate(${n2(Math.sin(t * .9) * 22)})`, `<path d="M0 0L-170 1100H170z" fill="#fff" opacity=".2"/>`, R(-50, -30, 100, 40, O, 16, 0), L('M-90 -36H90', O, 6)) : '';
        return fundo + twinkle(t, 7, 10, -200, -60, 1100, 340) + C(120, 170, 70, '#fff4c0', 6) + C(100, 150, 12, '#e8d9a0', 3) + C(146, 196, 9, '#e8d9a0', 3) +
          G(`translate(${n2(-200 + (t * 26) % 1300)} 90)`, R(-30, -8, 60, 16, '#c8cfd8', 8, 4), C(-30, 0, 5, Math.sin(t * 5) > 0 ? '#ff5a4d' : '#39d98a', 2)) +
          skyline + neon + mureta + varal + piso + caixa + antena + arCond + fan(575 + 44, 958, 42, t, 300) + cadeira + feixe + flyes(t, 640, 1010, 1, 30) + L('M-340 640Q60 700 360 610T1060 640', O, 3) + rep(12, i => C(-260 + i * 110, 660 + Math.sin(i * 1.1) * 26, 7, ['#ffd97a', '#ff9ac0', '#7dffb4'][i % 3], 2.5, Math.sin(t * 2 + i) > -.5 ? '' : 'opacity=".4"')) + R(300, 1240, 150, 60, '#d9a15f', 4, 5) + rep(3, i => R(590 + i * 26, 1090, 20, 34, '#39a96b', 4, 3)) + prop('plant', t, 280, 880, .6, { dead: true }) +
          prop('trash_bag', t, 800, 960, .9);
      };
    });

})();
