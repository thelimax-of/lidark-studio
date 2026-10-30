/* props.js — objetos do motor vetorial (agente MUNDO).
   V.props.nome(t, {state, label}) -> string SVG em volta de (0,0), ~100 px. Determinístico.
   Estados comuns: on, level (0..1), broken, open, pressed, up, dead, float (flutua em gravidade zero),
   label (texto; também vale o.label). */
(function () {
  const V = window.V;
  V.props = V.props || {};
  V.docs = V.docs || {};
  V.docs.props = V.docs.props || {};
  const O = '#14182a';
  const FH = "Impact, 'Arial Black', sans-serif";
  const FS = "'Segoe UI', Arial, sans-serif";
  const n2 = v => Math.round(v * 100) / 100;
  const st = sw => sw ? `stroke="${O}" stroke-width="${sw}" stroke-linejoin="round"` : 'stroke="none"';
  const R = (x, y, w, h, f, rx = 6, sw = 5, ex = '') => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${f}" ${st(sw)} ${ex}/>`;
  const C = (x, y, r, f, sw = 5, ex = '') => `<circle cx="${x}" cy="${y}" r="${r}" fill="${f}" ${st(sw)} ${ex}/>`;
  const E = (x, y, rx, ry, f, sw = 5, ex = '') => `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="${f}" ${st(sw)} ${ex}/>`;
  const P = (d, f, sw = 5, ex = '') => `<path d="${d}" fill="${f}" ${st(sw)} ${ex}/>`;
  const L = (d, c = O, w = 5, ex = '') => `<path d="${d}" fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round" ${ex}/>`;
  const G = (tr, ...c) => `<g transform="${tr}">${c.join('')}</g>`;
  const T = (x, y, s, size, f = O, o = {}) => `<text x="${x}" y="${y}" font-size="${size}" fill="${f}" stroke="none" text-anchor="${o.a || 'middle'}" font-family="${o.font || FH}"${o.w ? ` font-weight="${o.w}"` : ''}>${s}</text>`;
  const TS = (x, y, s, size, f = O, o = {}) => T(x, y, s, size, f, Object.assign({ font: FS, w: 700 }, o));
  const rep = (n, fn) => { let s = ''; for (let i = 0; i < n; i++) s += fn(i); return s; };
  const lvl = (s, d = 1) => V.cl(s.level === undefined ? (s.full === false ? 0 : d) : +s.level, 0, 1);
  const lit = (s, d = true) => s.on === undefined ? d : !!s.on;
  const brilho = (x, y, c = '#fff', o = .6) => L(`M${x} ${y}v-14`, c, 4, `opacity="${o}"`);
  const trinca = (x, y) => L(`M${x} ${y}l14 12-8 12 16 10M${x} ${y}l-16 6-4 16M${x} ${y}l6-18 14-6`, '#fff', 2.5);

  function def(nome, desc, data, fn) {
    V.props[nome] = (t, o) => {
      o = o || {}; t = t || 0;
      const s = o.state || {}, lab = V.esc(o.label !== undefined ? o.label : (s.label !== undefined ? s.label : ''));
      const c = fn(t, s, lab);
      if (!s.float) return c;
      /* em gravidade zero: boia e gira devagar */
      return G(`translate(${n2(Math.sin(t * .6) * 8)} ${n2(Math.cos(t * .5) * 8)}) rotate(${n2(Math.sin(t * .4) * 14)})`, c);
    };
    V.docs.props[nome] = { desc, data };
  }

  /* ---------- ferramentas ---------- */
  def('tape', 'Rolo de fita prateada, o herói da série.', { state: { level: 1 } }, (t, s) => {
    const r = 24 + lvl(s) * 28;
    return C(0, 0, r, '#b9bdc4', 6) + C(0, 0, r - 10, 'none', 2) + L(`M${-r * .55} ${-r * .5}q${r * .4} ${-r * .3} ${r * .8} 0`, '#eef2f6', 4) + C(0, 0, 21, '#c9a26a', 5) + C(0, 0, 13, '#3a4358', 4) +
      P(`M4 ${r - 9}h72l-7 9 7 9h-72z`, "#b9bdc4", 5);
  });
  def('wrench', 'Chave inglesa de metal.', { state: {} }, () => G('rotate(-40)', R(-13, -30, 26, 90, '#c8cfd8', 8, 5), L('M-4 -20V48', '#eef2f6', 4), P('M-30 -62q-6 28 14 40h32q20-12 14-40l-16 -8v26h-28v-26z', '#c8cfd8', 5), C(0, 62, 12, '#8d99a8', 5), C(0, 62, 4, O, 0)));
  def('screwdriver', 'Chave de fenda de cabo amarelo.', { state: {} }, () => G('rotate(40)', R(-8, -6, 16, 66, '#c8cfd8', 2, 5), P('M-8 60h16l-3 22h-10z', '#c8cfd8', 5), R(-20, -70, 40, 66, '#ffd23f', 14, 5), L('M-8 -60V-14M8 -60V-14', '#b98f22', 5), R(-14, -10, 28, 10, O, 2, 0)));
  def('flashlight', 'Lanterna; state.on liga o facho.', { state: { on: true } }, (t, s) => {
    const on = lit(s, false);
    return (on ? `<path d="M50 -24L240 -90V90L50 24z" fill="#fff6b0" opacity="${n2(.5 + Math.sin(t * 7) * .04)}"/>` : '') +
      R(-70, -18, 96, 36, '#3a82b4', 8, 5) + P('M26 -18l22 -14h14v64h-14l-22 -14z', '#c8cfd8', 5) + E(62, 0, 8, 30, on ? '#fff6b0' : '#dfe6ee', 4) + R(-40, -24, 26, 10, on ? '#ffd23f' : '#d9483b', 3, 4) + rep(4, i => L(`M${-62 + i * 7} -14v28`, O, 2.5));
  });
  def('toolbox', 'Caixa de ferramentas vermelha; state.open abre.', { state: { open: false } }, (t, s) => s.open ?
    P('M-66 -18l10-34h112l10 34z', '#b03329', 5) + G('translate(-30 -40) rotate(-8)', R(-6, -42, 12, 58, '#c8cfd8', 3, 4)) + G('translate(14 -36) rotate(14)', R(-5, -48, 10, 50, '#ffd23f', 3, 4), R(-10, -56, 20, 14, '#8d99a8', 2, 4)) + R(-72, -18, 144, 70, '#d9483b', 8, 5) + R(-12, -8, 24, 16, '#c8cfd8', 3, 4) :
    L('M-28 -36v-16q0-8 8-8h40q8 0 8 8v16', O, 8) + R(-72, -36, 144, 88, '#d9483b', 8, 5) + L('M-72 -6h144', O, 4) + R(-12, -16, 24, 20, '#c8cfd8', 3, 4));
  def('valve', 'Válvula de roda vermelha num cano; gira com state.open.', { state: { open: false } }, (t, s) => R(-70, 26, 140, 34, '#c8cfd8', 4, 5) + R(-14, 0, 28, 30, '#8d99a8', 3, 5) +
    G(`rotate(${s.open ? 60 : 0}) translate(0 -8)`, C(0, 0, 42, 'none', 0), C(0, 0, 42, '#d9483b', 0, 'opacity="0"'), `<circle r="38" fill="none" stroke="${O}" stroke-width="16"/><circle r="38" fill="none" stroke="#d9483b" stroke-width="8"/>`, L('M-36 0H36M0 -36V36', O, 10), L('M-36 0H36M0 -36V36', '#d9483b', 4), C(0, 0, 11, '#ffd23f', 4)));
  def('pipe_leak', 'Cano com furo soprando ar; state.fixed mostra o remendo.', { state: { fixed: false } }, (t, s) => {
    const jato = s.fixed ? '' : rep(14, i => { const f = (t * 1.8 + i * .07) % 1, a = (-60 - i * 11 % 60) * Math.PI / 180, d = f * 90; return `<circle cx="${n2(Math.cos(a) * d)}" cy="${n2(-16 + Math.sin(a) * d)}" r="${n2(2 + f * 7)}" fill="#dff4ff" opacity="${n2((1 - f) * .9)}"/>`; });
    return R(-80, -18, 160, 44, '#c8cfd8', 0, 5) + `<rect x="-80" y="-10" width="160" height="9" fill="#fff" opacity=".5"/>` + R(-74, -28, 18, 64, '#8d99a8', 4, 4) + R(56, -28, 18, 64, '#8d99a8', 4, 4) +
      (s.fixed ? R(-30, -24, 60, 56, '#b9bdc4', 2, 4) + R(-10, -32, 20, 70, '#c6cad0', 2, 4) : C(0, -14, 6, O, 0)) + jato;
  });
  def('cable_coil', 'Rolo de cabo elétrico com plugue.', { state: {} }, () => rep(3, i => E(0, 26 - i * 20, 62, 24, 'none', 12)) + rep(3, i => E(0, 26 - i * 20, 62, 24, 'none', 0, 'opacity="0"') + `<ellipse cy="${26 - i * 20}" rx="62" ry="24" fill="none" stroke="#ff9a3c" stroke-width="6"/>`) + L('M58 20q30 10 22 34', O, 11) + L('M58 20q30 10 22 34', '#ff9a3c', 5) + R(68, 52, 24, 24, '#3a4358', 4, 4) + L('M74 78v10M86 78v10', O, 4));
  def('rope', 'Corda enrolada.', { state: {} }, () => rep(4, i => `<ellipse cy="${30 - i * 18}" rx="${64 - i * 6}" ry="22" fill="none" stroke="${O}" stroke-width="16"/><ellipse cy="${30 - i * 18}" rx="${64 - i * 6}" ry="22" fill="none" stroke="#e0b878" stroke-width="9" stroke-dasharray="12 5"/>`) + L('M40 -30q40-20 30-46', O, 14) + L('M40 -30q40-20 30-46', '#e0b878', 8));
  def('fuse', 'Fusível de vidro; state.broken mostra queimado.', { state: { broken: false } }, (t, s) => R(-58, -18, 26, 36, '#c8cfd8', 4, 5) + R(32, -18, 26, 36, '#c8cfd8', 4, 5) + R(-32, -15, 64, 30, s.broken ? '#c8c0b0' : '#dff4ff', 4, 4) + (s.broken ? L('M-32 0q10-8 18 0M32 0q-10 8-16 0', O, 3) + C(0, 0, 8, O, 0, 'opacity=".5"') : L('M-32 0q10-14 20 0t24 0 20 0', '#d9483b', 3)));
  def('circuit_board', 'Placa de circuito verde; state.broken queima.', { state: { broken: false } }, (t, s) => R(-66, -48, 132, 96, s.broken ? '#6f8a5a' : '#2fa35f', 6, 5) + L('M-52 -30h40v30h30M-52 24h20v-16M20 -36v22h30M52 30h-24v-16', '#ffd23f', 3) + R(-22, -22, 44, 40, '#2d3a52', 3, 4) + TS(0, 3, 'A9', 16, '#fff') + rep(5, i => L(`M${-18 + i * 9} -22v-6M${-18 + i * 9} 18v6`, '#c8cfd8', 3)) + R(30, 6, 22, 22, '#d9483b', 3, 3) + C(-46, -2, 8, '#6fd3ff', 3) + (s.broken ? C(10, -10, 26, O, 0, 'opacity=".55"') + L('M8 -30q12-12 2-26', '#a9b3bf', 5, 'opacity=".7"') : C(42, -32, 5, Math.sin(t * 4) > 0 ? '#ff5a4d' : '#6b2520', 2)));
  def('battery', 'Bateria com nível; state.level de 0 a 1.', { state: { level: .3 } }, (t, s) => {
    const n = lvl(s), c = n < .25 ? '#ff5a4d' : n < .55 ? '#ffd23f' : '#39d98a';
    return R(-26, -46, 52, 98, '#3a4358', 8, 5) + R(-12, -58, 24, 12, '#c8cfd8', 3, 4) + rep(4, i => (n * 4 > i ? R(-17, 32 - i * 21, 34, 16, c, 2, 2, n < .25 && Math.sin(t * 6) > 0 ? 'opacity=".4"' : '') : '')) + (n < .1 ? T(0, 16, '!', 34, '#ff5a4d') : '');
  });

  /* ---------- sobrevivência ---------- */
  def('oxygen_tank', 'Cilindro de oxigênio com manômetro; state.level de 0 a 1.', { state: { level: .5 } }, (t, s) => {
    const n = lvl(s), a = -100 + n * 200;
    return R(-34, -62, 68, 136, '#2a8fd8', 28, 5) + `<rect x="-24" y="-44" width="9" height="102" rx="4" fill="#fff" opacity=".45"/>` + L('M-34 -30h68', O, 4) + T(0, 26, 'O₂', 34, '#fff') + R(-12, -82, 24, 20, '#c8cfd8', 3, 5) + R(-24, -96, 48, 15, '#d9483b', 5, 5) +
      G('translate(36 -44)', C(0, 0, 20, '#f4f4f2', 4), G(`rotate(${a})`, L('M0 0V-14', n < .25 ? '#d9483b' : O, 3)));
  });
  def('oxygen_mask', 'Máscara de oxigênio com mangueira.', { state: {} }, () => L('M-58 -22q-6 40 10 62', O, 5) + L('M58 -22q6 40-10 62', O, 5) + P('M-46 -30q46-46 92 0l-4 30q-14 34-42 40-28-6-42-40z', '#bfeaff', 5) + `<path d="M-30 -22q30-26 56-8" stroke="#fff" stroke-width="5" fill="none" opacity=".7"/>` + C(0, 8, 13, '#8d99a8', 4) + L('M0 44q6 26 40 26t40 20', O, 13) + L('M0 44q6 26 40 26t40 20', '#39a96b', 6));
  def('fire_extinguisher', 'Extintor vermelho.', { state: {} }, () => R(-30, -42, 60, 118, '#d9483b', 16, 5) + `<rect x="-20" y="-28" width="9" height="92" rx="4" fill="#fff" opacity=".4"/>` + R(-20, -4, 40, 46, '#fff', 3, 3) + T(0, 26, 'FOGO', 13, '#d9483b') + R(-10, -58, 20, 16, '#3a4358', 3, 4) + L('M-8 -64h42M-8 -74l36 6', O, 8) + L('M8 -60q-44 0-50 40v24', O, 7) + R(-50, 2, 14, 22, '#3a4358', 3, 3));
  def('medkit', 'Kit de primeiros socorros; state.open abre.', { state: { open: false } }, (t, s) => {
    const cruz = (x, y, q) => P(`M${x - q} ${y - 3 * q}h${2 * q}v${2 * q}h${2 * q}v${2 * q}h${-2 * q}v${2 * q}h${-2 * q}v${-2 * q}h${-2 * q}v${-2 * q}h${2 * q}z`, '#d9483b', 3);
    return s.open ? P('M-64 -10l12-36h104l12 36z', '#f4f4f2', 5) + R(-68, -10, 136, 66, '#fff', 8, 5) + R(-50, 2, 40, 18, '#ffd97a', 4, 3) + R(4, 2, 18, 42, '#bfeaff', 3, 3) + R(30, 2, 24, 42, '#ffb0c8', 3, 3) + cruz(0, -28, 5) :
      L('M-24 -42v-12h48v12', O, 8) + R(-68, -42, 136, 96, '#fff', 12, 5) + cruz(0, 6, 11) + R(-68, 34, 136, 8, '#d9483b', 0, 0);
  });
  def('ration_pack', 'Pacote de ração de astronauta.', { state: {} }, () => P('M-46 -56h92l-6 8 6 8v90l-6-6-8 6-8-6-8 6-8-6-8 6-8-6-8 6-8-6-8 6-8-6-8 6z', '#b9c6d4', 5) + L('M-46 -40h92', O, 3) + R(-36, -28, 72, 34, '#ff9a3c', 3, 3) + T(0, -4, 'RAÇÃO', 19) + TS(0, 26, 'sabor: "frango"', 10) + TS(0, 40, 'val: 2041', 10, '#d9483b'));
  def('water_pouch', 'Bolsa de água com canudo; state.level de 0 a 1.', { state: { level: 1 } }, (t, s) => {
    const n = lvl(s), y = 50 - 90 * n;
    return P('M-38 -40q0-8 8-8h60q8 0 8 8l4 84q0 12-12 12h-60q-12 0-12-12z', '#dff4ff', 5) + `<path d="M-37 ${n2(y)}q18 ${n2(Math.sin(t * 2) * 5)} 37 0t37 0l3 ${n2(50 - y)}q0 6-8 6h-64q-8 0-8-6z" fill="#6fc8ff"/>` + R(-10, -74, 20, 28, '#d9483b', 3, 4) + TS(0, 12, 'H₂O', 19, '#fff') + L('M-38 -40q0-8 8-8h60q8 0 8 8l4 84q0 12-12 12h-60q-12 0-12-12z', O, 5);
  });
  def('helmet', 'Capacete de astronauta com visor dourado.', { state: { broken: false } }, (t, s) => C(0, -6, 62, '#f4f4f2', 6) + R(-40, 46, 80, 22, '#8d99a8', 8, 5) + P('M-46 -22q46-30 92 0v30q-46 30-92 0z', s.broken ? '#6a7a8a' : '#ffc23f', 5) + `<path d="M-30 -20q16-10 34-8" stroke="#fff" stroke-width="6" fill="none" opacity=".75" stroke-linecap="round"/>` + (s.broken ? trinca(4, -2) : '') + R(52, -26, 14, 34, '#d9483b', 4, 4) + C(-52, -46, 5, Math.sin(t * 3) > 0 ? '#39d98a' : '#3a4358', 2));
  def('spacesuit', 'Traje espacial completo pendurado (sem ninguém dentro).', { state: {} }, (t) => G('translate(0 -6) scale(.9)',
    R(-46, -44, 92, 86, '#c8cfd8', 12, 5), R(-16, 34, 22, 66, '#f4f4f2', 8, 5), R(10, 34, 22, 66, '#f4f4f2', 8, 5), R(-24, 92, 32, 18, '#3a4358', 6, 4), R(8, 92, 32, 18, '#3a4358', 6, 4),
    R(-66, -38, 24, 74, '#f4f4f2', 10, 5), R(44, -38, 24, 74, '#f4f4f2', 10, 5), C(-54, 42, 12, '#ff9a3c', 4), C(56, 42, 12, '#ff9a3c', 4),
    R(-40, -42, 82, 84, '#f4f4f2', 12, 5), R(-22, -14, 44, 30, '#2a8fd8', 4, 4), C(-10, 0, 4, '#39d98a', 2), C(4, 0, 4, Math.sin(t * 3) > 0 ? '#ff5a4d' : '#6b2520', 2), L('M-38 30h78', '#d9483b', 7),
    C(0, -76, 38, '#f4f4f2', 5), C(0, -74, 26, '#ffc23f', 4), L('M-12 -86q10-8 20-4', '#fff', 4)));
  def('backpack', 'Mochila verde cheia.', { state: {} }, () => L('M-24 -56q0-18 24-18t24 18', O, 9) + R(-52, -56, 104, 122, '#5aa864', 22, 5) + R(-36, 2, 72, 50, '#468a50', 8, 4) + L('M-36 18h72', O, 3) + R(-7, 12, 14, 16, '#ffd23f', 3, 3) + R(-40, -44, 80, 30, '#6fbe78', 8, 4) + R(-68, -20, 16, 56, '#468a50', 6, 4) + R(52, -20, 16, 56, '#468a50', 6, 4));
  def('map', 'Mapa dobrado com X e trilha; o.label muda o título.', { state: {} }, (t, s, lab) => P('M-74 -46l50 12 50-12 48 12v90l-48-12-50 12-50-12z', '#f7e7b8', 5) + L('M-24 -34v92M26 -46v90', '#c9a26a', 3) + P('M-60 -20q14-12 26 2t-6 26-20-28z', '#a6e3a1', 3) + L('M-40 34q30-24 50-6t36-24', '#d9483b', 4, 'stroke-dasharray="8 6"') + L('M34 -22l16 16m0-16l-16 16', '#d9483b', 6) + (lab ? TS(0, -18, lab, 14) : ''));
  def('photo', 'Foto Polaroid; state.kind: familia ou pet; o.label escreve na borda.', { state: { kind: 'familia' } }, (t, s, lab) => G('rotate(-4)', R(-48, -58, 96, 116, '#fff', 3, 5), R(-38, -48, 76, 74, s.kind === 'pet' ? '#a6e3a1' : '#ffd9a0', 0, 3),
    s.kind === 'pet' ? C(0, -8, 22, '#c98d4e', 4) + C(-16, -28, 8, '#a86f35', 3) + C(16, -28, 8, '#a86f35', 3) + C(-7, -10, 3, O, 0) + C(7, -10, 3, O, 0) + E(0, -2, 4, 3, O, 0) :
      C(-14, -14, 11, '#e8b98a', 3) + C(16, -18, 12, '#c98d5e', 3) + C(2, -2, 8, '#efe3c8', 3) + P('M-30 26q14-30 28 0zM4 26q14-30 28 0z', '#3a82b4', 3), lab ? TS(0, 46, lab, 13) : ''));
  def('notebook', 'Caderno espiral; o.label escreve na capa.', { state: {} }, (t, s, lab) => R(-50, -64, 100, 128, '#d9483b', 5, 5) + R(-30, -44, 66, 34, '#fff', 3, 3) + TS(3, -21, lab || 'DIÁRIO', 14) + rep(7, i => L(`M-58 ${-52 + i * 17}h18`, '#c8cfd8', 5) + L(`M-58 ${-52 + i * 17}h18`, O, 1.5)) + L('M-20 30h50M-20 44h34', '#fff', 3, 'opacity=".5"'));
  def('tablet', 'Tablet com gráfico; state.on, state.broken, o.label.', { state: { on: true } }, (t, s, lab) => R(-58, -76, 116, 152, '#2d3a52', 12, 5) + R(-48, -64, 96, 124, lit(s) ? '#dff4ff' : '#0f1a2e', 3, 3) + (lit(s) ? TS(0, -44, lab || 'STATUS', 14) + rep(6, i => R(-38 + i * 13, n2(40 - (Math.sin(t * 2 + i) * .5 + .5) * 54), 9, n2(4 + (Math.sin(t * 2 + i) * .5 + .5) * 54), i % 2 ? '#2a8fd8' : '#39d98a', 1, 0)) : '') + C(0, 68, 4, '#8d99a8', 0) + (s.broken ? trinca(0, 0) : ''));
  def('laptop', 'Notebook aberto; state.on, state.broken, o.label.', { state: { on: true } }, (t, s, lab) => P('M-70 44h140l18 22q2 6-6 6h-164q-8 0-6-6z', '#a9b3bf', 5) + L('M-56 54h112M-60 62h120', O, 2) + R(-66, -50, 132, 96, '#3a4358', 8, 5) + R(-56, -42, 112, 78, lit(s) ? '#2a8fd8' : '#0f1a2e', 3, 3) +
    (lit(s) ? (lab ? TS(0, -14, lab, 14, '#fff') : '') + rep(3, i => L(`M-44 ${n2(0 + i * 11)}h${n2(30 + Math.abs(Math.sin(t * 1.5 + i)) * 56)}`, '#fff', 4, 'opacity=".8"')) : '') + (s.broken ? trinca(4, -6) : ''));
  def('phone', 'Celular; state.on, state.broken, state.ring vibra.', { state: { on: true } }, (t, s, lab) => {
    const v = s.ring ? Math.sin(t * 50) * 2.5 : 0;
    return G(`translate(${n2(v)} 0)`, R(-34, -70, 68, 140, '#14182a', 12, 5), R(-28, -60, 56, 118, lit(s) ? '#dff4ff' : '#0f1a2e', 4, 2), lit(s) ? R(-20, -46, 34, 15, '#fff', 6, 2) + R(-14, -24, 34, 15, '#7fd0ff', 6, 2) + (lab ? TS(0, 22, lab, 12) : '') : '', R(-10, -66, 20, 5, '#3a4358', 2, 0), s.broken ? trinca(0, 0) : '') +
      (s.ring ? L('M44 -30q10 8 0 18M-44 -30q-10 8 0 18', '#ff5a4d', 4) : '');
  });
  def('radio_handheld', 'Rádio comunicador; state.on pisca e chia.', { state: { on: true } }, (t, s) => L('M18 -42V-92', O, 7) + C(18, -94, 5, '#d9483b', 3) + R(-34, -46, 68, 112, '#3a4358', 10, 5) + rep(5, i => L(`M-22 ${-32 + i * 8}h44`, '#8d99a8', 3)) + R(-24, 8, 48, 22, lit(s) ? '#7dffb4' : '#203a2e', 3, 3) + R(-20, 38, 16, 16, '#d9483b', 3, 3) + R(4, 38, 16, 16, '#ffd23f', 3, 3) + C(-22, -54, 6, '#c8cfd8', 3) + C(26, -38, 3.5, lit(s) && Math.sin(t * 6) > 0 ? '#ff5a4d' : '#6b2520', 0) + (lit(s) ? rep(3, i => L(`M${-14 + i * 12} 19v${n2(-2 - Math.abs(Math.sin(t * 9 + i)) * 6)}`, O, 3)) : ''));
  def('keycard', 'Cartão de acesso; o.label escreve o nível.', { state: {} }, (t, s, lab) => R(-64, -42, 128, 84, '#ffd23f', 8, 5) + R(-64, -42, 128, 22, '#d9483b', 8, 3) + C(-38, 8, 17, '#efe3c8', 3) + P('M-54 8a16 16 0 0 1 32 0q-16-8-32 0z', '#24412c', 2) + TS(16, 2, lab || 'ACESSO', 15) + L('M-8 14h46M-8 26h34', O, 3) + R(-58, -38, 20, 14, '#c8cfd8', 2, 2));
  def('door_keypad', 'Teclado de porta; state.status: ok, denied ou idle.', { state: { status: 'idle' } }, (t, s) => R(-48, -68, 96, 136, '#8d99a8', 8, 5) + R(-36, -56, 72, 26, s.status === 'ok' ? '#39d98a' : s.status === 'denied' ? '#ff5a4d' : '#0f2a46', 3, 3) + TS(0, -37, s.status === 'ok' ? 'ABERTO' : s.status === 'denied' ? 'NEGADO' : '****', 14, '#fff') + rep(4, j => rep(3, i => R(-34 + i * 24, -22 + j * 21, 20, 17, j === 3 && i === 2 ? '#39d98a' : j === 3 && i === 0 ? '#d9483b' : '#dfe6ee', 3, 2.5))));
  def('screen_panel', 'Painel de parede com tela e LEDs; state.error, o.label.', { state: { error: false } }, (t, s, lab) => {
    const e = s.error && Math.sin(t * 7) > -.3;
    return R(-74, -58, 148, 116, '#8d99a8', 8, 5) + R(-62, -46, 124, 70, e ? '#a81f25' : '#0f2a46', 3, 3) + (e ? T(0, 0, lab || 'ERRO', 30, '#fff') : (lab ? TS(0, -22, lab, 14, '#7dffb4') : '') + L(rep(20, i => `${i ? 'L' : 'M'}${-58 + i * 6} ${n2(0 + Math.sin(t * 3 + i * .7) * 16)}`), '#7dffb4', 3)) + rep(5, i => C(-48 + i * 24, 42, 6, ['#39d98a', '#ffd23f', '#ff5a4d', '#6fd3ff', '#39d98a'][i], 2.5, Math.sin(t * (2 + i) + i) > 0 ? '' : 'opacity=".3"'));
  });
  def('alarm_light', 'Sirene giratória; state.on.', { state: { on: true } }, (t, s) => {
    const on = lit(s), a = t * 360 % 360;
    return (on ? G(`rotate(${n2(a)})`, `<path d="M0 -12L170 -60V40z" fill="#ff4a3a" opacity=".3"/><path d="M0 -12L-170 -60V40z" fill="#ff4a3a" opacity=".3"/>`) : '') + R(-40, 28, 80, 22, '#55697f', 5, 5) + P('M-32 28v-34a32 32 0 0 1 64 0v34z', on ? (Math.sin(t * 9) > 0 ? '#ff5a4d' : '#d9281c') : '#8a3a33', 5) + L('M-14 -8q6-14 18-12', '#fff', 5, 'opacity=".7"');
  });
  def('warning_sign', 'Placa amarela de aviso; o.label troca o texto.', { state: {} }, (t, s, lab) => R(-60, -60, 120, 120, '#ffd23f', 10, 5) + P('M0 -46L40 18H-40z', O, 0) + T(0, 12, '!', 44, '#ffd23f') + T(0, 46, lab || 'PERIGO', Math.min(22, 170 / Math.max((lab || 'PERIGO').length, 1))) + C(-48, -48, 3.5, '#8d99a8', 2) + C(48, -48, 3.5, '#8d99a8', 2));
  def('red_button', 'Botão vermelho com tampa; state.pressed afunda.', { state: { pressed: false } }, (t, s) => R(-58, 10, 116, 46, '#ffd23f', 8, 5) + rep(5, i => L(`M${-46 + i * 22} 54l14 -42`, O, 5)) + R(-42, -4, 84, 24, '#55697f', 6, 5) + (s.pressed ? E(0, -6, 36, 14, '#a82b22', 5) : P('M-36 -4v-16q0-24 36-24t36 24v16z', '#ff4a3a', 5) + L('M-20 -26q8-10 22-10', '#fff', 5, 'opacity=".7"')));
  def('lever', 'Alavanca; state.up para cima.', { state: { up: true } }, (t, s) => R(-52, 26, 104, 34, '#8d99a8', 6, 5) + R(-26, 8, 52, 22, '#55697f', 4, 4) + G(`translate(0 14) rotate(${s.up ? -32 : 32})`, R(-7, -78, 14, 80, '#c8cfd8', 3, 4), C(0, -84, 18, '#d9483b', 5)) + TS(-34, 50, 'ON', 11, '#fff') + TS(32, 50, 'OFF', 11, '#fff'));
  def('duct_tape_patch', 'Remendo em X de fita, com letra de bilhete.', { state: {} }, (t, s, lab) => G('rotate(-8)', R(-64, -16, 128, 32, '#b9bdc4', 2, 4, 'transform="rotate(40)"'), R(-64, -16, 128, 32, '#c6cad0', 2, 4, 'transform="rotate(-40)"'), L('M-30 -30l60 50M-20 30l50-44', '#8c9199', 2.5), lab ? TS(0, 54, lab, 14) : ''));

  /* ---------- comida e casa ---------- */
  def('pizza', 'Pizza; state.kind "slice" (fatia) ou "box" (caixa); padrão pizza inteira.', { state: { kind: 'whole' } }, (t, s) => {
    if (s.kind === 'slice') return P('M0 66L-48 -36q48-22 96 0z', '#ffd98a', 5) + P('M-48 -36q48-22 96 0l-6 14q-42-18-84 0z', '#d8a463', 4) + C(-12, -8, 10, '#d9483b', 3) + C(14, 14, 9, '#d9483b', 3) + C(-2, 34, 7, '#d9483b', 3);
    if (s.kind === 'box') return R(-70, -18, 140, 36, '#e8c07a', 4, 5) + L('M-70 -6h140', O, 3) + T(0, 12, 'PIZZA', 19, '#d9483b') + P('M-70 -18l8-14h124l8 14z', '#f0d090', 5);
    return C(0, 0, 68, '#d8a463', 5) + C(0, 0, 56, '#ffd98a', 4) + L('M-56 0H56M0 -56V56M-40 -40L40 40M40 -40L-40 40', '#d8a463', 3) + [[-24, -30], [26, -24], [-30, 22], [22, 30], [0, -2]].map(p => C(p[0], p[1], 10, '#d9483b', 3)).join('') + C(38, 2, 5, '#3f8a44', 0) + C(-4, 36, 5, '#3f8a44', 0);
  });
  def('coffee_mug', 'Caneca fumegando; o.label escreve na caneca.', { state: {} }, (t, s, lab) => L('M42 -22q34-2 34 22t-34 24', O, 16) + L('M42 -22q34-2 34 22t-34 24', '#fff', 7) + R(-46, -40, 90, 94, '#fff', 12, 5) + E(-1, -36, 44, 9, '#6b3f1e', 4) + TS(-1, 16, lab || 'A-9', 20, '#d9483b') +
    rep(3, i => L(`M${-20 + i * 20} -56q${n2(10 * Math.sin(t * 2 + i))} -14 0 -30`, '#fff', 5, 'opacity=".65"')));
  def('thermos', 'Garrafa térmica.', { state: {} }, () => R(-30, -48, 60, 118, '#d9483b', 12, 5) + `<rect x="-20" y="-34" width="9" height="92" rx="4" fill="#fff" opacity=".35"/>` + R(-24, -72, 48, 26, '#c8cfd8', 6, 5) + R(-30, 8, 60, 12, '#ffd23f', 0, 3) + L('M30 -30q24 10 0 50', O, 7));
  def('sandwich', 'Sanduíche em camadas.', { state: {} }, () => L('M6 -74V20', '#e8c07a', 6) + C(6, -78, 8, '#39a96b', 3) + R(-74, 26, 148, 22, '#fff0cf', 7, 5) + R(-74, 40, 148, 8, '#c98d4e', 4, 0) + R(-68, 12, 136, 14, '#ffb0a0', 6, 4) + P('M-76 12q10 10 20 0t20 0 20 0 20 0 20 0 20 0 20 0 18 0v-10H-76z', '#67c15e', 4) + R(-72, -14, 144, 16, '#ffd23f', 3, 4) + P('M-72 -14l10 22 10-22z', '#ffd23f', 3) + R(-74, -44, 148, 30, '#fff0cf', 9, 5) + R(-74, -44, 148, 8, '#c98d4e', 4, 0));
  def('burger', 'Hambúrguer com gergelim.', { state: {} }, () => P('M-68 -6q0-58 68-58t68 58z', '#e8a44e', 5) + rep(5, i => E(-36 + i * 18, -38 + (i % 2) * 12, 5, 3, '#fff4d6', 2)) + P('M-74 -6q12 14 24 2t24 2 26-2 24 2 24-2 26 0v12H-74z', '#67c15e', 4) + R(-72, 8, 144, 22, '#6b3f1e', 11, 4) + P('M-62 8h124l-16 16-16-16', '#ffd23f', 3) + R(-68, 30, 136, 26, '#e8a44e', 12, 5));
  def('soda', 'Lata de refrigerante; state.broken amassa.', { state: {} }, (t, s) => s.broken ? P('M-24 -44h48l-8 34 12 26-8 40h-40l-12-34 14-30z', '#d9483b', 5) + L('M-10 -10l20 16', '#fff', 5) : R(-32, -52, 64, 112, '#d9483b', 10, 5) + P('M-32 -18q32 30 64 0v30q-32 30-64 0z', '#fff', 3) + T(0, 16, 'POP', 22, '#d9483b') + E(0, -52, 26, 7, '#c8cfd8', 4) + brilho(-20, 54));
  def('donut', 'Rosquinha com granulado.', { state: {} }, () => C(0, 0, 56, '#d8a463', 5) + P('M-50 -6q6-46 50-46t50 46q-8 18-24 6t-26 8-26-6-24-8z', '#ff8ac0', 4) + C(0, 0, 18, '#ffffff', 5) + rep(10, i => L(`M${n2(Math.cos(i * .95) * 36)} ${n2(Math.sin(i * .95 + 3.14) * 34 - 6)}l6 4`, ['#ffd23f', '#6fd3ff', '#fff'][i % 3], 4)));
  def('plant', 'Vaso de planta; state.dead murcha.', { state: { dead: false } }, (t, s) => {
    const c = s.dead ? '#a89a56' : '#46b36b', sw = Math.sin(t * 1.4) * 3;
    return G(`rotate(${n2(s.dead ? 0 : sw)} 0 10)`, s.dead ? L('M0 12q6-40 30-30', '#8d7740', 7) + E(38, -10, 20, 9, c, 4) + L('M0 12q-8-30-30-16', '#8d7740', 7) + E(-38, 4, 18, 8, c, 4) :
      L('M0 14V-40', '#2f8c4f', 7) + E(-26, -30, 28, 13, c, 5, 'transform="rotate(-30 -26 -30)"') + E(26, -42, 28, 13, c, 5, 'transform="rotate(30 26 -42)"') + E(-10, -66, 13, 26, c, 5) + E(16, -8, 24, 11, c, 5, 'transform="rotate(-20 16 -8)"')) +
      P('M-40 10h80l-12 56h-56z', '#c98d4e', 5) + R(-46, 4, 92, 16, '#a86f35', 4, 5);
  });
  def('trash_bag', 'Saco de lixo preto amarrado.', { state: {} }, () => P('M-14 -48q-64 24-64 74t78 42 78-42-64-74z', '#3a4358', 5) + L('M-14 -48l-14-22M14 -48l14-22M0 -48v-24', O, 6) + R(-16, -54, 32, 12, '#ffd23f', 4, 4) + L('M-46 8q14-22 26-30', '#8d99a8', 5) + L('M30 40q14-8 20-22', '#8d99a8', 4));
  def('bucket', 'Balde; state.level de água.', { state: { level: .4 } }, (t, s) => L('M-48 -36q48-60 96 0', O, 5) + P('M-52 -36h104l-14 96h-76z', '#3a82b4', 5) + E(0, -36, 52, 11, n2(lvl(s, 0)) > 0 ? '#8fdcff' : '#23527d', 4));
  def('broom', 'Vassoura.', { state: {} }, () => G('rotate(12)', R(-5, -96, 10, 130, '#c98d4e', 4, 4), P('M-14 30h28l18 60h-64z', '#ffd23f', 5), L('M-14 58h28M-6 34l-8 54M6 34l8 54', O, 3), R(-16, 24, 32, 12, '#d9483b', 3, 4)));
  def('pill_bottle', 'Frasco de remédio.', { state: {} }, () => R(-30, -30, 60, 88, '#ff9a3c', 6, 5) + R(-34, -56, 68, 26, '#fff', 5, 5) + rep(5, i => L(`M${-24 + i * 12} -52v18`, O, 2)) + R(-24, -8, 48, 44, '#fff', 2, 3) + TS(0, 12, 'RX', 17, '#d9483b') + L('M-16 24h32', O, 3));

  /* ---------- bichos e piadas ---------- */
  def('cat', 'Gato sentado, rabo balança e pisca.', { state: {} }, (t) => {
    const pisca = (t % 3.3) < .12, cauda = Math.sin(t * 2) * 14;
    return L(`M26 50q44 ${n2(-4 + cauda * .3)} 40 -32 ${n2(cauda)} -18 ${n2(cauda)} -26`, O, 18) + L(`M26 50q44 ${n2(-4 + cauda * .3)} 40 -32 ${n2(cauda)} -18 ${n2(cauda)} -26`, '#ff9a3c', 9) + P('M-40 58q-6-66 36-66t44 66z', '#ff9a3c', 5) + L('M-8 24v30M10 24v30', O, 3) + R(-30, 48, 24, 14, '#ffc98a', 7, 4) + R(10, 48, 24, 14, '#ffc98a', 7, 4) +
      P('M-46 -60l6 32a42 36 0 1 0 80 0l6-32-28 12q-18-8-36 0z', '#ff9a3c', 5) + L('M-10 -50v12M10 -50v12M0 -52v14', '#d9701c', 4) +
      (pisca ? L('M-26 -24h14M12 -24h14', O, 4) : E(-19, -24, 7, 10, '#b6f06a', 3) + E(19, -24, 7, 10, '#b6f06a', 3) + E(-19, -24, 2.5, 8, O, 0) + E(19, -24, 2.5, 8, O, 0)) +
      P('M-6 -8h12l-6 7z', '#ff8aa0', 2) + L('M0 -2q-8 10-14 2M0 -2q8 10 14 2', O, 3) + L('M-34 -12h-26M-34 -4l-24 6M34 -12h26M34 -4l24 6', O, 2.5);
  });
  def('rubber_duck', 'Patinho de borracha que balança.', { state: {} }, (t) => G(`rotate(${n2(Math.sin(t * 1.8) * 5)})`, P('M-58 10q-14-32 12-40q26 20 40 6q2-44 40-44t40 44q0 20-16 28q10 10 2 30q-12 30-62 30t-56-54z', '#ffd23f', 5), P('M46 -34q24-4 36 6q-6 10-30 10z', '#ff9a3c', 4), C(30, -38, 6, O, 0), C(32, -40, 2, '#fff', 0), P('M-34 10q24-16 44 0-6 26-30 22t-14-22z', '#ffc21f', 4)));

  /* ---------- ainda mais tralha útil para a trama ---------- */
  def('gear', 'Engrenagem que gira; state.broken para.', { state: {} }, (t, s) => G(`rotate(${s.broken ? 12 : n2(t * 40 % 360)})`, rep(8, i => R(-11, -66, 22, 26, '#c8cfd8', 3, 4, `transform="rotate(${i * 45})"`)), C(0, 0, 48, '#c8cfd8', 5), C(0, 0, 18, '#55697f', 5)));
  def('wire_cutter', 'Alicate de corte de cabo vermelho.', { state: {} }, () => L('M-6 8Q-30 50-20 84', O, 16) + L('M-6 8Q-30 50-20 84', '#d9483b', 8) + L('M6 8Q30 50 20 84', O, 16) + L('M6 8Q30 50 20 84', '#2a8fd8', 8) + P('M-8 8L-18 -70q18 10 16 40zM8 8L18 -70q-18 10-16 40z', '#c8cfd8', 5) + C(0, 4, 8, '#8d99a8', 4));
})();
