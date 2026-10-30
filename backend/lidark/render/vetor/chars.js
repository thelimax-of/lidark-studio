// Elenco vetorial: bonecos articulados por cinemática inversa (mão e pé são alvos; cotovelo e joelho se resolvem).
// Pés em (0,0), ~620 px de altura. Cada membro tem dois segmentos cônicos com contorno único, junta dobrada e detalhes.
(function () {
  'use strict';
  const INK = '#14182a', SKIN = '#efe3c8', SHADE = '#dccba6', OUT = 7;
  const cl = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const n = x => +x.toFixed(1), lerp = (a, b, k) => a + (b - a) * k, D2R = Math.PI / 180;
  const rnd = s => V.rnd(s);

  // ---------------------------------------------------------------- geometria
  // cápsula cônica entre dois pontos
  function cap(a, b, r1, r2) {
    const dx = b[0] - a[0], dy = b[1] - a[1], d = Math.hypot(dx, dy) || .01, g = Math.atan2(dy, dx), k = Math.acos(cl((r1 - r2) / d, -1, 1));
    const P = (c, r, an) => `${n(c[0] + r * Math.cos(an))} ${n(c[1] + r * Math.sin(an))}`;
    return `M${P(a, r1, g + k)}L${P(b, r2, g + k)}A${r2} ${r2} 0 ${k > Math.PI / 2 ? 1 : 0} 0 ${P(b, r2, g - k)}L${P(a, r1, g - k)}A${r1} ${r1} 0 ${k < Math.PI / 2 ? 1 : 0} 0 ${P(a, r1, g + k)}z`;
  }
  // dois ossos: devolve joelho/cotovelo e o alvo alcançável
  function ik(a, c, l1, l2, bend) {
    let dx = c[0] - a[0], dy = c[1] - a[1], d = Math.hypot(dx, dy) || .01;
    const mx = (l1 + l2) * .995;
    if (d > mx) { dx *= mx / d; dy *= mx / d; d = mx; }
    const g = Math.atan2(dy, dx), k = Math.acos(cl((l1 * l1 + d * d - l2 * l2) / (2 * l1 * d), -1, 1)) * bend;
    return { j: [a[0] + l1 * Math.cos(g + k), a[1] + l1 * Math.sin(g + k)], e: [a[0] + dx, a[1] + dy] };
  }
  // membro de dois segmentos com silhueta única: contorno primeiro, preenchimento depois (sem emenda na junta)
  function limb(a, j, e, r0, r1, r2, fill) {
    const d = cap(a, j, r0, r1) + cap(j, e, r1, r2);
    return `<path d="${d}" fill="${INK}" stroke="${INK}" stroke-width="${OUT * 2}" stroke-linejoin="round"/><path d="${d}" fill="${fill}"/>`;
  }
  // vinco da dobra na junta: só aparece quando a junta dobra
  function crease(a, j, e, r) {
    const a1 = Math.atan2(a[1] - j[1], a[0] - j[0]), a2 = Math.atan2(e[1] - j[1], e[0] - j[0]);
    let m = (a1 + a2) / 2;
    if (Math.abs(a1 - a2) > Math.PI) m += Math.PI;
    const dot = Math.cos(a1 - a2);
    if (dot < -.92) return '';
    const x = j[0] + Math.cos(m) * r * .86, y = j[1] + Math.sin(m) * r * .86, X = j[0] + Math.cos(m) * r * .15, Y = j[1] + Math.sin(m) * r * .15;
    return `<path d="M${n(x)} ${n(y)}L${n(X)} ${n(Y)}" stroke="${INK}" stroke-width="5" stroke-linecap="round" fill="none"/>`;
  }
  // punho/barra perpendicular ao segmento
  function band(p, q, r, w, fill, sw) {
    const g = Math.atan2(q[1] - p[1], q[0] - p[0]) / D2R;
    return `<rect transform="translate(${n(p[0])} ${n(p[1])}) rotate(${n(g)})" x="${-w / 2}" y="${-r}" width="${w}" height="${r * 2}" rx="5" fill="${fill}" stroke="${INK}" stroke-width="${sw || 5}"/>`;
  }
  const along = (p, q, k) => [p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k];

  function hand(p, ang, kind, skin, side) {
    // desenhada apontando para +x; side espelha o polegar
    const body = kind === 'fist'
      ? `<circle r="25" fill="${skin}"/><path d="M6-16v12M16-10v10M8 16v-10" stroke="${INK}" stroke-width="4" stroke-linecap="round"/><path d="M-4-22q16 10 4 22" fill="${skin}" stroke="${INK}" stroke-width="5"/>`
      : kind === 'point'
        ? `<path d="${cap([10, -6], [66, -8], 12, 10)}" fill="${skin}"/><circle r="25" fill="${skin}"/><path d="M12-2h14M12 10h12" stroke="${INK}" stroke-width="4" stroke-linecap="round"/><path d="${cap([-2, 20], [14, 34], 11, 9)}" fill="${skin}"/>`
        : kind === 'grip'
          ? `<path d="M-22 10q-8-30 18-34 30 0 32 22 0 24-28 28z" fill="${skin}"/><path d="M10-20q10 10 6 16M18 -8q8 8 3 14" stroke="${INK}" stroke-width="4" fill="none" stroke-linecap="round"/>`
          : `<path d="${cap([0, 0], [36, -13], 21, 8)}" fill="${skin}"/><path d="${cap([0, 0], [44, 0], 21, 9)}" fill="${skin}"/><path d="${cap([0, 0], [36, 14], 21, 8)}" fill="${skin}"/><path d="${cap([-4, 18], [12, 38], 11, 8)}" fill="${skin}"/>` +
          `<circle r="24" fill="${skin}"/>`;
    return `<g transform="translate(${n(p[0])} ${n(p[1])}) rotate(${n(ang)}) scale(1 ${side})" stroke="${INK}" stroke-width="6" stroke-linejoin="round">${body}</g>`;
  }

  function sneaker(p, rot, dir, c) {
    // c = {up, toe, sole, lace, stripe}
    return `<g transform="translate(${n(p[0])} ${n(p[1])}) rotate(${n(rot)}) scale(${dir} 1)" stroke="${INK}" stroke-width="${OUT}" stroke-linejoin="round">` +
      `<path d="M-30 26Q-34-14-18-20H18Q28 0 60-2Q84 0 84 26z" fill="${c.up}"/>` +
      `<path d="M38 26V-1Q64-4 76 8Q84 16 84 26z" fill="${c.toe}" stroke-width="5"/>` +
      `<rect x="-36" y="20" width="126" height="16" rx="8" fill="${c.sole}"/>` +
      (c.stripe ? `<path d="M-8-4L18 14" stroke="${c.stripe}" stroke-width="9" stroke-linecap="round"/>` : '') +
      (c.lace ? `<path d="M14-14l10 8M26-8l9 8M36-3l8 8" stroke="${c.lace}" stroke-width="4" stroke-linecap="round"/>` : '') + '</g>';
  }

  // ---------------------------------------------------------------- poses (alvos em coordenadas do boneco)
  const HIP = -180;
  function poseOf(name, t, s) {
    const br = Math.sin(t * 2.4 + s), sw = Math.sin(t * .8 + s * 2) * 3;
    const P = { turn: .12, hip: [sw, HIP + br * 1.5], lean: 0, rot: 0, head: [0, 0, Math.sin(t * 1.3 + s) * 2], hkL: 'open', hkR: 'open', lift: 0,
      eL: 1, eR: -1, kL: 1, kR: -1, armsFront: false, fL: [-50, -26, 0], fR: [50, -26, 0], hL: [-126, -134 + br * 2], hR: [126, -134 - br * 2] };
    const A = (o) => Object.assign(P, o);
    switch (name) {
      case 'walk': {
        const f = t * 7.5 + s, st = 66, L = f, R = f + Math.PI;
        const ft = a => [st * Math.cos(a), -26 - Math.max(0, -Math.sin(a)) * 42, -Math.sin(a) * (Math.sin(a) < 0 ? 16 : 0) * -1];
        A({ turn: .86, hip: [4, HIP + 4 + 5 * Math.cos(2 * f)], lean: 4, fL: ft(L), fR: ft(R), eL: 1, eR: 1, kL: -1, kR: -1,
          hL: [-70 * Math.cos(L) + 8, -165 + 10 * Math.sin(L)], hR: [-70 * Math.cos(R) + 8, -165 + 10 * Math.sin(R)], hkL: 'fist', hkR: 'fist', head: [4, 3 * Math.cos(2 * f), 2 * Math.sin(f)] });
        break;
      }
      case 'run': {
        const f = t * 12.5 + s, st = 104, L = f, R = f + Math.PI;
        const ft = a => [st * Math.cos(a) - 8, -26 - Math.max(0, -Math.sin(a)) * 84 - Math.max(0, Math.sin(a)) * 6, Math.sin(a) < 0 ? -30 * Math.sin(a) * Math.cos(a) * 2 : 0];
        const hy = HIP + 2 + 13 * Math.cos(2 * f), lean = 15, sx = 4 + 150 * Math.sin(lean * D2R), sy = hy - 150;
        const h = a => [sx + 82 * Math.cos(a + Math.PI) + 12, sy + 118 + 34 * Math.sin(a + Math.PI)];
        A({ turn: .9, hip: [4, hy], lean, fL: ft(L), fR: ft(R), eL: 1, eR: 1, kL: -1, kR: -1, hL: h(L), hR: h(R), hkL: 'fist', hkR: 'fist', head: [10, 6 * Math.cos(2 * f), 3 * Math.sin(f)] });
        break;
      }
      case 'point': {
        A({ turn: .42, lean: 3, fL: [-58, -26, 0], fR: [58, -26, 0], hR: [262, -392 + Math.sin(t * 5 + s) * 7], hkR: 'point', hL: [-132, -205], eL: 1, eR: 1, head: [8, 0, 4], armsFront: true });
        break;
      }
      case 'hold': {
        A({ turn: .24, lean: 1, hR: [186, -398 + br * 5], hkR: 'grip', eR: 1, hL: [-124, -160 + br * 2], armsFront: true });
        break;
      }
      case 'hands_head': {
        const j = Math.sin(t * 7 + s) * 3;
        A({ turn: 0, hip: [0, HIP + 7 + j * .4], fL: [-66, -26, 0], fR: [66, -26, 0], hL: [-126, -496 + j], hR: [126, -496 - j], eL: -1, eR: 1, hkL: 'open', hkR: 'open', armsFront: true, head: [0, 12, Math.sin(t * 5 + s) * 3] });
        break;
      }
      case 'sit': {
        A({ turn: .55, hip: [-26, -128 + br * 1.2], lean: -2, fL: [122, -26, 0], fR: [90, -26, 0], kL: -1, kR: -1, hL: [92, -170], hR: [66, -172], eL: 1, eR: 1, head: [4, 0, Math.sin(t * .9 + s) * 2] });
        break;
      }
      case 'crawl': {
        const f = t * 5 + s;
        const hd = a => [66 + 62 * Math.cos(a), -28 - Math.max(0, -Math.sin(a)) * 26];
        const ft = a => [-222 - 46 * Math.cos(a), -26 - Math.max(0, -Math.sin(a)) * 14, 0];
        A({ turn: .95, hip: [-118, -158 + 3 * Math.sin(2 * f)], lean: 76, headAbs: [166, -232 + 3 * Math.cos(2 * f)], head: [0, 0, 3 * Math.sin(f)], hL: hd(f), hR: hd(f + Math.PI), fL: ft(f + Math.PI), fR: ft(f), eL: 1, eR: 1, kL: -1, kR: -1, hkL: 'fist', hkR: 'fist', shadowW: 240 });
        break;
      }
      case 'type': {
        const tap = k => rnd(Math.floor(t * 13 + k * .5) + k * 91) * 13;
        A({ turn: .58, lean: 8, hL: [160, -266 - tap(1)], hR: [128, -258 - tap(2)], eL: 1, eR: 1, hkL: 'fist', hkR: 'fist', head: [12, 8, 4 + Math.sin(t * 1.1) * 1.5], fL: [-40, -26, 0], fR: [46, -26, 0], armsFront: true });
        break;
      }
      case 'fall': {
        const w = Math.sin(t * 9 + s), z = Math.cos(t * 7 + s);
        A({ turn: .1, hip: [0, -262], rot: -24 + 14 * Math.sin(t * 4 + s), hL: [-176 + w * 22, -478 + z * 26], hR: [178 + z * 22, -470 + w * 26], eL: -1, eR: 1, fL: [-100 + z * 18, -112 + w * 18, -24], fR: [104 - w * 18, -88 + z * 22, 24], kL: 1, kR: -1, armsFront: true, shadowK: .4 });
        break;
      }
      case 'float': {
        const y = Math.sin(t * 1.25 + s), x = Math.sin(t * .8 + s);
        A({ turn: .22, hip: [x * 10, -258 + y * 15], rot: 7 * x, hL: [-182, -300 + y * 28], hR: [186, -322 - y * 26], fL: [-48 + x * 14, -108 + y * 14, -16], fR: [58 - x * 12, -94 - y * 13, 18], eL: 1, eR: -1, kL: 1, kR: -1, shadowK: .35, head: [0, 0, Math.sin(t * .9 + s) * 5] });
        break;
      }
      default: break;
    }
    return P;
  }

  // ---------------------------------------------------------------- rosto
  function blinkAt(t, s) {
    const per = 2.7 + rnd(s) * 1.4, ph = (t + s * 1.7) % per;
    return ph < .1 || (rnd(s + Math.floor((t + s * 1.7) / per)) > .72 && ph > .24 && ph < .33);
  }

  function face(o) {
    const { R, turn, expr, talk, t, seed: s, state } = o, th = turn * .62;
    const ex = a => R * Math.sin(a + th) * .97, xL = ex(-.42), xR = ex(.42), ey = 20, mx = R * .72 * Math.sin(th), my = 80;
    const fL = lerp(1, .78, turn), blink = blinkAt(t, s);
    let g = '';
    const eye = (x, sc) => {
      if (expr === 'happy' && !talk) return `<path d="M${n(x - 20)} ${ey + 8}q20-30 40 0" fill="none" stroke="${INK}" stroke-width="9" stroke-linecap="round"/>`;
      if (blink) return `<path d="M${n(x - 16)} ${ey}h32" stroke="${INK}" stroke-width="7" stroke-linecap="round"/>`;
      if (expr === 'shock') return `<circle cx="${n(x)}" cy="${ey - 4}" r="31" fill="#fff" stroke="${INK}" stroke-width="7"/><circle cx="${n(x)}" cy="${ey - 4}" r="9" fill="${INK}"/>`;
      if (expr === 'sleepy') return `<circle cx="${n(x)}" cy="${ey + 3}" r="13" fill="${INK}"/><path d="M${n(x - 24)} ${ey - 3}H${n(x + 24)}" stroke="${SHADE}" stroke-width="20"/><path d="M${n(x - 20)} ${ey + 3}h40" stroke="${INK}" stroke-width="7" stroke-linecap="round"/>`;
      const r = expr === 'scared' ? 21 : expr === 'angry' ? 13 : expr === 'sad' ? 15 : 14;
      return `<ellipse cx="${n(x)}" cy="${ey}" rx="${n(r * sc)}" ry="${r}" fill="${INK}"/>` + (r > 14 ? `<circle cx="${n(x + r * .3)}" cy="${n(ey - r * .35)}" r="${n(r * .28)}" fill="#fff"/>` : '');
    };
    g += eye(xL, fL) + eye(xR, 1);
    // sobrancelhas
    const brow = (x, dir) => {
      const y = ey - (expr === 'shock' ? 46 : expr === 'scared' ? 38 : 30), w = 22;
      const tilt = expr === 'angry' ? 13 : expr === 'scared' || expr === 'sad' ? -11 : expr === 'sleepy' ? 3 : 0;
      return `<path d="M${n(x - w)} ${n(y + (dir > 0 ? tilt : -tilt) * -1 * -1)}L${n(x + w)} ${n(y - (dir > 0 ? tilt : -tilt) * -1 * -1)}" stroke="${INK}" stroke-width="8" stroke-linecap="round"/>`;
    };
    g += brow(xL, -1) + brow(xR, 1);
    // bochechas
    const inR = (x, y, r) => { const m = Math.sqrt(Math.max(0, R * R - y * y)) - r - 6; return cl(x, -m, m); };
    const cx = inR(ex(-.95), 66, 24), cX = inR(ex(.95), 66, 24);
    g += `<circle cx="${n(cx)}" cy="66" r="24" fill="#ee8877" opacity="${expr === 'happy' ? .7 : .45}"/><circle cx="${n(cX)}" cy="66" r="24" fill="#ee8877" opacity="${expr === 'happy' ? .7 : .45}"/>`;
    // boca: fala pelo envelope; parada segue a expressão
    const dark = '#401b2a', tongue = '#e0586a';
    let m;
    if (talk > .06) {
      const h = 6 + talk * 30, w = (expr === 'happy' ? 34 : expr === 'scared' || expr === 'shock' ? 24 : 28) + talk * 4;
      m = `<ellipse rx="${n(w)}" ry="${n(h)}" fill="${dark}" stroke="${INK}" stroke-width="6"/>` +
        (h > 13 ? `<ellipse cy="${n(h * .55)}" rx="${n(w * .58)}" ry="${n(h * .34)}" fill="${tongue}"/>` : '') +
        (h > 18 ? `<path d="M${n(-w * .6)} ${n(-h * .66)}H${n(w * .6)}" stroke="#fff" stroke-width="6" stroke-linecap="round"/>` : '');
    } else if (expr === 'scared') {
      const q = Math.sin(t * 22) * 2;
      m = `<path d="M-26 ${n(10 + q)}q9-16 18-5t16 0 18 5q-5 13-26 13t-26-13z" fill="${dark}" stroke="${INK}" stroke-width="6" stroke-linejoin="round"/>`;
    } else if (expr === 'shock') {
      m = `<ellipse cy="12" rx="27" ry="37" fill="${dark}" stroke="${INK}" stroke-width="6"/><ellipse cy="31" rx="16" ry="11" fill="${tongue}"/>`;
    } else if (expr === 'happy') {
      m = `<path d="M-38-6Q0 4 38-6Q34 36 0 38Q-34 36-38-6z" fill="${dark}" stroke="${INK}" stroke-width="6" stroke-linejoin="round"/><path d="M-30-1Q0 7 30-1L27 8Q0 15-27 8z" fill="#fff"/><ellipse cy="27" rx="17" ry="8" fill="${tongue}"/>`;
    } else if (expr === 'angry') {
      m = `<rect x="-32" y="-8" width="64" height="26" rx="9" fill="#fff" stroke="${INK}" stroke-width="6"/><path d="M-32 5H32M-12-8v26M12-8v26" stroke="${INK}" stroke-width="4"/>`;
    } else if (expr === 'sad') {
      m = `<path d="M-26 12Q0-14 26 12" fill="none" stroke="${INK}" stroke-width="8" stroke-linecap="round"/>`;
    } else if (expr === 'sleepy') {
      m = `<ellipse cy="4" rx="10" ry="${n(8 + Math.sin(t * 2) * 2)}" fill="${dark}" stroke="${INK}" stroke-width="5"/>`;
    } else {
      m = `<path d="M-24 0Q0 15 24 0" fill="none" stroke="${INK}" stroke-width="7" stroke-linecap="round"/>`;
    }
    g += `<g transform="translate(${n(mx)} ${my})">${m}</g>`;
    if (expr === 'sad') { const f = (t * .5 + s) % 1; g += `<path transform="translate(${n(xR + 6)} ${n(ey + 24 + f * 60)})" d="M0-12q13 16 0 24-13-8 0-24z" fill="#7fd4ff" stroke="${INK}" stroke-width="4" opacity="${n(1 - f * .8)}"/>`; }
    // sujeira e curativo
    const dirt = +(state.dirt || 0);
    if (dirt > 0) {
      g += `<g fill="#6b5a44" opacity="${n(.2 + dirt * .5)}"><ellipse cx="${n(inR(ex(.8), 100, 30))}" cy="100" rx="30" ry="13"/><ellipse cx="${n(inR(ex(-1), 24, 17))}" cy="24" rx="17" ry="24"/><circle cx="${n(inR(ex(.1), 116, 9))}" cy="116" r="8"/>${dirt > .5 ? `<ellipse cx="${n(inR(ex(-.4), 108, 20))}" cy="108" rx="20" ry="8"/><circle cx="${n(inR(ex(.95), 6, 11))}" cy="6" r="10"/>` : ''}</g>`;
    }
    if (state.bandage) {
      const bx = inR(ex(-1.15), 58, 30);
      g += `<g transform="translate(${n(bx)} 58) rotate(-28)"><rect x="-30" y="-10" width="60" height="20" rx="9" fill="#f5d9b8" stroke="${INK}" stroke-width="5"/><rect x="-9" y="-10" width="18" height="20" fill="#fff1dc" stroke="${INK}" stroke-width="3"/></g>` +
        `<g transform="translate(${n(bx)} 58) rotate(58)"><rect x="-24" y="-8" width="48" height="16" rx="8" fill="#f5d9b8" stroke="${INK}" stroke-width="5"/></g>`;
    }
    return g;
  }

  function sphere(R) {
    return `<circle r="${R}" fill="${SKIN}" stroke="${INK}" stroke-width="8"/>` +
      `<path d="M${-R * .88} ${R * .36}A${R * .96} ${R * .96} 0 0 0 ${R * .88} ${R * .36}A${R * 1.16} ${R * 1.16} 0 0 1 ${-R * .88} ${R * .36}z" fill="${SHADE}" opacity=".7"/>`;
  }

  // ---------------------------------------------------------------- personagens humanos: um rig, várias roupas
  const HEAD_UP = 128, TORSO = 164, ARM = [100, 96], LEG = [81, 81];

  function rig(look, t, o) {
    o = o || {};
    const s = look.seed, P = poseOf(o.pose || 'stand', t, s), st = o.state || {}, talk = o.talk || 0, expr = o.expr || 'neutral', tn = P.turn;
    const rS = Math.cos(tn * 1.15), breath = Math.sin(t * 2.4 + s);
    const shW = 92 * lerp(1, .34, tn), hipW = 40 * lerp(1, .3, tn), tr = expr === 'scared' ? Math.sin(t * 46) * 2.4 : 0;
    const hip = [P.hip[0] + tr, P.hip[1]], le = P.lean * D2R;
    const up = (x, y) => [hip[0] + x * Math.cos(le) - y * Math.sin(le), hip[1] + x * Math.sin(le) + y * Math.cos(le)]; // local do tronco -> boneco
    const shL = up(-shW, -TORSO + 22), shR = up(shW, -TORSO + 22), neck = up(0, -TORSO);
    const hc = P.headAbs ? [P.headAbs[0] + tr, P.headAbs[1]] : [neck[0] + P.head[0], neck[1] - HEAD_UP + P.head[1] + breath * .8 + talk * -3];
    const hipL = up(-hipW, 2), hipR = up(hipW, 2);
    const aL = ik(shL, P.hL, ARM[0], ARM[1], P.eL), aR = ik(shR, P.hR, ARM[0], ARM[1], P.eR);
    const lL = ik(hipL, [P.fL[0], P.fL[1]], LEG[0], LEG[1], P.kL), lR = ik(hipR, [P.fR[0], P.fR[1]], LEG[0], LEG[1], P.kR);
    const side = tn > .45, dirL = side ? 1 : -1, dirR = 1;

    const leg = (h, q, f, dir, isFar) => {
      const c = look.leg, shin = along(q.j, q.e, .9);
      let g = limb(h, q.j, q.e, c.r[0], c.r[1], c.r[2], c.fill) + (c.detail ? c.detail(h, q) : '') + crease(h, q.j, q.e, c.r[1]);
      g += c.cuff ? band(shin, q.e, c.r[2] + 2, 15, c.cuff) : '';
      return g + sneaker([q.e[0], q.e[1] - 2], f[2] || 0, dir, look.shoe);
    };
    const arm = (sh, q, kind, sign) => {
      const c = look.arm, wr = along(q.j, q.e, .92), an = Math.atan2(q.e[1] - q.j[1], q.e[0] - q.j[0]) / D2R;
      const tip = along(q.j, q.e, 1.16);
      let g = limb(sh, q.j, q.e, c.r[0], c.r[1], c.r[2], c.fill) + crease(sh, q.j, q.e, c.r[1]);
      if (c.detail) g += c.detail(sh, q);
      if (st.bandage && sign > 0) g += band(along(q.j, q.e, .55), q.e, c.r[2] + 2, 26, '#fff4e2', 4);
      g += band(wr, q.e, c.r[2] + 2, 14, c.cuff || c.fill);
      let it = '';
      if (o.hold && sign > 0) it = heldItem(t, o, tip, an);
      return g + hand(tip, an, kind, SKIN, sign) + it;
    };

    const tRot = P.lean;
    const torso = `<g transform="translate(${n(hip[0])} ${n(hip[1])}) rotate(${n(tRot)}) scale(1 ${n(1 + breath * .008)})">${look.torso(tn, t, st, expr)}</g>`;
    const hd = `<g transform="translate(${n(hc[0])} ${n(hc[1])}) rotate(${n(P.head[2])})">${look.head(tn, t, st, expr, talk, s)}</g>`;

    // ordem de profundidade: costas, braço/perna do lado de lá, tronco, cabeça, lado de cá
    let g = look.back ? `<g transform="translate(${n(hip[0])} ${n(hip[1])}) rotate(${n(tRot)})">${look.back(tn, t, st)}</g>` : '';
    if (look.hairBack) g += `<g transform="translate(${n(hc[0])} ${n(hc[1])}) rotate(${n(P.head[2])})">${look.hairBack(tn, t)}</g>`;
    if (side) g += arm(shR, aR, P.hkR, 1) + leg(hipR, lR, P.fR, dirR) + leg(hipL, lL, P.fL, dirL);
    else g += leg(hipL, lL, P.fL, dirL) + leg(hipR, lR, P.fR, dirR);
    if (look.over) g += `<g transform="translate(${n(hip[0])} ${n(hip[1])}) rotate(${n(tRot)})">${look.over(tn, lL, lR, hip)}</g>`;
    const aLs = arm(shL, aL, P.hkL, -1), aRs = arm(shR, aR, P.hkR, 1);
    if (side) g += torso + hd + aLs;
    else if (P.armsFront) g += torso + hd + aLs + aRs; // mão na cabeça ou item erguido: braço por cima de tudo
    else g += torso + aLs + aRs + hd;
    return wrap(look, P, hip, g, o);
  }

  function wrap(look, P, hip, g, o) {
    const k = P.shadowK || 1, w = (P.shadowW || 136) * k;
    const body = P.rot ? `<g transform="rotate(${n(P.rot)} ${n(hip[0])} ${n(hip[1])})">${g}</g>` : g;
    const flip = o.flip ? -1 : 1, sc = look.scale || 1;
    return `<g transform="scale(${n(flip * sc * 1000) / 1000} ${sc})"><ellipse cx="0" cy="34" rx="${n(w)}" ry="${n(21 * Math.max(.5, k))}" fill="#000" opacity="${n(.28 * Math.max(.4, k))}"/>${body}</g>`;
  }

  function heldItem(t, o, p, an) {
    const fn = V.props && V.props[o.hold], flip = o.flip ? -1 : 1;
    const art = typeof fn === 'function' ? (() => { try { return fn(t, { state: {} }) || ''; } catch (e) { return ''; } })() : (V.missing.includes('props:' + o.hold) || V.missing.push('props:' + o.hold),
      `<rect x="-40" y="-40" width="80" height="80" rx="12" fill="#ffd23f" stroke="${INK}" stroke-width="6"/>`);
    return `<g transform="translate(${n(p[0] + 8)} ${n(p[1] - 42)}) scale(${flip} 1)">${art}</g>`;
  }

  // ---------------------------------------------------------------- Zé
  const smudge = (st) => {
    const d = +(st.dirt || 0);
    return d > 0 ? `<g fill="#4e4330" opacity="${n(.22 + d * .45)}"><ellipse cx="-58" cy="-70" rx="20" ry="13"/><ellipse cx="40" cy="-32" rx="24" ry="11"/><circle cx="62" cy="-118" r="9"/></g>` +
      (d > .55 ? `<path d="M-30-120l14 18M28-96l-12 20" stroke="${INK}" stroke-width="5" stroke-linecap="round"/>` : '') : '';
  };
  const ZE = {
    seed: 3.1,
    leg: { fill: '#3d5f92', r: [33, 26, 20], cuff: '#7f9fc9',
      detail: (h, q) => `<path d="M${n(h[0] + 14)} ${n(h[1] + 16)}L${n(q.j[0] + 10)} ${n(q.j[1] - 8)}" stroke="#5f81b5" stroke-width="4" stroke-linecap="round" fill="none"/>` },
    arm: { fill: '#6f7040', r: [31, 25, 20], cuff: '#585a30',
      detail: (s, q) => { const a = along(s, q.j, .45); return `<path d="M${n(a[0] - 12)} ${n(a[1])}l20 8" stroke="#55562f" stroke-width="4" stroke-linecap="round"/>`; } },
    shoe: { up: '#f6f5f0', toe: '#dfe3ea', sole: '#fff', lace: '#7c8596', stripe: '#c9412f' },
    back(tn) {
      const x = -24 - tn * 74, w = 78 + tn * 52;
      return `<rect x="${n(x - w / 2 + 20 * (1 - tn))}" y="-152" width="${n(w)}" height="150" rx="26" fill="#23252e" stroke="${INK}" stroke-width="${OUT}"/>` +
        (tn > .4 ? `<rect x="${n(x - w / 2 + 12)}" y="-82" width="${n(w * .55)}" height="58" rx="12" fill="#32353f" stroke="${INK}" stroke-width="5"/><path d="M${n(x - w / 2 + 16)}-112h${n(w * .7)}" stroke="#4a4e5b" stroke-width="5"/>` : '');
    },
    torso(tn, t, st) {
      const c = lerp(1, .68, tn), sw = 104 * c, hw = 92 * c, o = tn * 34, a = 36 * lerp(1, .55, tn);
      let g = `<g stroke="${INK}" stroke-width="${OUT}" stroke-linejoin="round">`;
      g += `<path d="M${n(-sw)}-138Q${n(-sw)}-172 ${n(-sw + 34)}-172H${n(sw - 34)}Q${n(sw)}-172 ${n(sw)}-138L${n(hw + 6)} 36Q0 46 ${n(-hw - 6)} 36z" fill="#6f7040"/>`;
      g += `<path d="M${n(o - a)}-172H${n(o + a)}L${n(o + a + 8)} 40H${n(o - a - 8)}z" fill="#f4f2ec"/>`; // camiseta
      g += `<path d="M${n(o - a)}-172L${n(o - a - 26)}-120L${n(o - a - 8)}-104L${n(o - a + 10)}-158z" fill="#7e8049"/><path d="M${n(o + a)}-172L${n(o + a + 26)}-120L${n(o + a + 8)}-104L${n(o + a - 10)}-158z" fill="#7e8049"/>`; // gola
      g += '</g>';
      g += `<path d="M${n(o - a - 2)}-100V30M${n(o + a + 2)}-100V30" stroke="#55562f" stroke-width="4" stroke-dasharray="8 7"/>`;
      g += `<rect x="${n(-hw + 8)}" y="-30" width="50" height="40" rx="6" fill="#62633a" stroke="${INK}" stroke-width="5"/><path d="M${n(-hw + 8)}-16h50" stroke="${INK}" stroke-width="4"/>`;
      if (tn < .7) g += `<rect x="${n(hw - 58)}" y="-30" width="50" height="40" rx="6" fill="#62633a" stroke="${INK}" stroke-width="5"/><path d="M${n(hw - 58)}-16h50" stroke="${INK}" stroke-width="4"/>`;
      g += `<rect transform="rotate(7 ${n(hw - 44)} -114)" x="${n(hw - 62)}" y="-128" width="36" height="28" rx="3" fill="#cfc78f" stroke="${INK}" stroke-width="4"/>`;
      // alças da mochila
      g += `<g stroke="${INK}" stroke-width="5"><path d="M${n(-sw * .62)}-170L${n(-sw * .5)}-46h18L${n(-sw * .62 + 26)}-170z" fill="#23252e"/>` + (tn < .6 ? `<path d="M${n(sw * .62)}-170L${n(sw * .5)}-46h-18L${n(sw * .62 - 26)}-170z" fill="#23252e"/>` : '') + '</g>';
      return g + smudge(st);
    },
    head(tn, t, st, expr, talk, s) {
      const R = 132;
      let g = sphere(R) + face({ R, turn: tn, expr, talk, t, seed: s, state: st });
      // boné: copa com gomos, botão e aba
      const b = lerp(0, 22, tn);
      g += `<g stroke="${INK}" stroke-width="8" stroke-linejoin="round"><path d="M${-R}-20A${R} ${R} 0 0 1 ${R}-20Q0-76 ${-R}-20z" fill="#27462f"/>` +
        `<path d="M${n(58 + b * .2)}-54Q${n(142 + b)}-58 ${n(176 + b)}-22Q${n(112 + b)}-14 ${n(46 + b)}-24z" fill="#1c3524"/></g>` +
        `<path d="M${n(tn * 30)}-131Q${n(-30 + tn * 30)}-90 ${n(-20 + tn * 26)}-48M${n(tn * 30)}-131Q${n(46 + tn * 30)}-96 ${n(48 + tn * 20)}-50" stroke="#16291c" stroke-width="5" fill="none"/>` +
        `<ellipse cx="${n(tn * 30)}" cy="-133" rx="13" ry="7" fill="#3a6a48" stroke="${INK}" stroke-width="5"/>` +
        `<path d="M${-R + 22}-62Q${-R + 40}-104 -44-118" stroke="#3a6a48" stroke-width="7" fill="none" stroke-linecap="round"/>`;
      return g;
    },
  };

  // ---------------------------------------------------------------- Nina
  const curl = (x, y, r, c) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${c}"/>`;
  const NINA = {
    seed: 7.7, scale: .95,
    leg: { fill: '#2b2d36', r: [29, 22, 16] },
    arm: { fill: '#ffc928', r: [29, 23, 19], cuff: '#f0a818',
      detail: (s, q) => { const a = along(s, q.j, .7); return band(a, q.j, 25, 13, '#fff3b8', 4); } },
    shoe: { up: '#e0352f', toe: '#ffffff', sole: '#ffffff', lace: '#ffffff', stripe: '#ffffff' },
    back(tn) {
      // capuz caído nas costas
      return `<path d="M-58-176Q0-122 58-176Q${n(66 - tn * 40)}-124 0-104Q${n(-66 - tn * 30)}-124-58-176z" fill="#f0b91f" stroke="${INK}" stroke-width="${OUT}" stroke-linejoin="round"/>`;
    },
    torso(tn, t, st) {
      const c = lerp(1, .7, tn), sw = 88 * c, hw = 112 * c, o = tn * 30, sway = Math.sin(t * 2.2) * 3;
      let g = `<g stroke="${INK}" stroke-width="${OUT}" stroke-linejoin="round">`;
      g += `<path d="M${n(-sw)}-138Q${n(-sw)}-172 ${n(-sw + 30)}-172H${n(sw - 30)}Q${n(sw)}-172 ${n(sw)}-138L${n(hw + sway)} 82Q0 96 ${n(-hw + sway)} 82z" fill="#ffc928"/>`;
      g += `<path d="M${n(o - 30)}-172L${n(o - 44)}-136L${n(o)}-112L${n(o + 44)}-136L${n(o + 30)}-172z" fill="#ffd95e"/></g>`;
      g += `<path d="M${n(o)}-112V90" stroke="${INK}" stroke-width="5"/>`;
      g += [-80, -40, 0, 40].map(y => `<circle cx="${n(o + 15)}" cy="${y}" r="9" fill="#fff" stroke="${INK}" stroke-width="4"/>`).join('');
      g += `<path d="M${n(-hw * .78)} 18l46-10v40l-46 6z" fill="#f0b91f" stroke="${INK}" stroke-width="5" stroke-linejoin="round"/>`;
      if (tn < .7) g += `<path d="M${n(hw * .78)} 18l-46-10v40l46 6z" fill="#f0b91f" stroke="${INK}" stroke-width="5" stroke-linejoin="round"/>`;
      g += `<path d="M${n(-hw + 8)} 66Q0 80 ${n(hw - 8)} 66" stroke="#fff3b8" stroke-width="9" fill="none"/>`;
      return g + smudge(st);
    },
    hairBack(tn, t) {
      const c = '#2c1f24', b = Math.sin(t * 3) * 2;
      return `<g stroke="${INK}" stroke-width="${OUT * 2}">${[[-96, -96, 54], [-30, -146, 66], [44, -142, 66], [100, -92, 54], [0, -196, 62], [-66, -174, 44], [68, -176, 46]].map(q => curl(q[0], q[1] + b, q[2], c)).join('')}</g>` +
        [[-96, -96, 54], [-30, -146, 66], [44, -142, 66], [100, -92, 54], [0, -196, 62], [-66, -174, 44], [68, -176, 46]].map(q => curl(q[0], q[1] + b, q[2], c)).join('');
    },
    head(tn, t, st, expr, talk, s) {
      const R = 126;
      let g = sphere(R) + face({ R, turn: tn, expr, talk, t, seed: s, state: st });
      // franja cacheada por cima da testa e fita
      const f = [[-92, -82, 34], [-52, -104, 34], [-8, -112, 36], [38, -106, 34], [82, -86, 32]];
      g += `<g stroke="${INK}" stroke-width="12">${f.map(q => curl(q[0], q[1], q[2], '#2c1f24')).join('')}</g>` + f.map(q => curl(q[0], q[1], q[2], '#2c1f24')).join('');
      g += `<g fill="none" stroke="#54404a" stroke-width="5" stroke-linecap="round"><path d="M-74-104q14-14 26-2M-18-132q16-10 26 2M30-122q14-8 24 4"/></g>`;
      g += `<path d="M-118-52Q0-120 118-52" fill="none" stroke="#e0352f" stroke-width="13" stroke-linecap="round"/>`;
      return g;
    },
  };

  // ---------------------------------------------------------------- Dona Cida
  const CIDA = {
    seed: 12.3, scale: .9,
    leg: { fill: '#e6d3bd', r: [24, 20, 15] },
    arm: { fill: '#7a4aa8', r: [31, 25, 20], cuff: '#5f3786' },
    shoe: { up: '#7b4f33', toe: '#7b4f33', sole: '#4a2f20', lace: null, stripe: null },
    // saia por cima das pernas, acompanhando os joelhos
    over(tn, lL, lR, hip) {
      const dk = (p) => [p[0] - hip[0], p[1] - hip[1]];
      const a = dk(along(lL.j, lL.e, .1)), b = dk(along(lR.j, lR.e, .1)), w = lerp(112, 80, tn);
      const x0 = Math.min(a[0], b[0], -w) - 14, x1 = Math.max(a[0], b[0], w) + 14, y = Math.max(a[1], b[1], 70) + 6;
      return `<path d="M${n(-w * .8)}-8Q${n(x0)} ${n(y * .5)} ${n(x0)} ${n(y)}Q0 ${n(y + 20)} ${n(x1)} ${n(y)}Q${n(x1)} ${n(y * .5)} ${n(w * .8)}-8z" fill="#8b6f58" stroke="${INK}" stroke-width="${OUT}" stroke-linejoin="round"/>` +
        `<path d="M${n(x0 * .4)} 30L${n(x0 * .55)} ${n(y + 6)}M${n(x1 * .4)} 30L${n(x1 * .55)} ${n(y + 6)}" stroke="#6e5644" stroke-width="5" stroke-linecap="round"/>`;
    },
    torso(tn, t, st) {
      const c = lerp(1, .72, tn), sw = 98 * c, hw = 112 * c, o = tn * 30, a = 44 * lerp(1, .6, tn);
      const flor = (x, y, k) => `<g transform="translate(${n(x)} ${y}) scale(${k})"><circle cy="-9" r="7" fill="#ff7a9c"/><circle cx="9" cy="-2" r="7" fill="#ff7a9c"/><circle cx="-9" cy="-2" r="7" fill="#ff7a9c"/><circle cx="6" cy="8" r="7" fill="#ff7a9c"/><circle cx="-6" cy="8" r="7" fill="#ff7a9c"/><circle r="5" fill="#ffd23f"/></g>`;
      let g = `<g stroke="${INK}" stroke-width="${OUT}" stroke-linejoin="round">`;
      g += `<path d="M${n(-sw)}-136Q${n(-sw)}-172 ${n(-sw + 32)}-172H${n(sw - 32)}Q${n(sw)}-172 ${n(sw)}-136L${n(hw)} 44Q0 56 ${n(-hw)} 44z" fill="#7a4aa8"/>`;
      g += `<path d="M${n(o - a)}-172H${n(o + a)}L${n(o + a + 10)} 48H${n(o - a - 10)}z" fill="#fdf6e8"/></g>`;
      g += flor(o - 22, -130, 1) + flor(o + 20, -94, .9) + flor(o - 18, -52, 1) + flor(o + 22, -12, 1) + flor(o - 16, 26, .9);
      g += `<path d="M${n(o - 14)}-172Q${n(o)}-130 ${n(o + 14)}-172" fill="none" stroke="#fff" stroke-width="8"/>` + [-10, -5, 0, 5, 10].map(k => `<circle cx="${n(o + k * 1.4)}" cy="${n(-168 + 24 * (1 - k * k / 120) * .9)}" r="4.5" fill="#fff" stroke="${INK}" stroke-width="2"/>`).join('');
      g += `<rect x="${n(-hw + 6)}" y="-14" width="52" height="42" rx="8" fill="#6a3d95" stroke="${INK}" stroke-width="5"/>`;
      if (tn < .7) g += `<rect x="${n(hw - 58)}" y="-14" width="52" height="42" rx="8" fill="#6a3d95" stroke="${INK}" stroke-width="5"/>`;
      return g + smudge(st);
    },
    hairBack() {
      const c = '#b9bcc4', L = [[-114, -44, 40], [-96, -92, 42], [-56, -128, 44], [0, -142, 46], [56, -128, 44], [96, -92, 42], [114, -44, 40]];
      return `<g stroke="${INK}" stroke-width="${OUT * 2}">${L.map(q => curl(q[0], q[1], q[2], c)).join('')}</g>` + L.map(q => curl(q[0], q[1], q[2], c)).join('');
    },
    head(tn, t, st, expr, talk, s) {
      const R = 126, th = tn * .62, ex = a => R * Math.sin(a + th) * .97, xL = ex(-.42), xR = ex(.42);
      let g = sphere(R) + face({ R, turn: tn, expr, talk, t, seed: s, state: st });
      const L = [[-88, -74, 30], [-48, -100, 32], [0, -110, 32], [48, -100, 32], [88, -74, 30]];
      g += `<g stroke="${INK}" stroke-width="12">${L.map(q => curl(q[0], q[1], q[2], '#c9ccd3')).join('')}</g>` + L.map(q => curl(q[0], q[1], q[2], '#c9ccd3')).join('');
      g += `<path d="M-64-92q14-10 24 2M-10-112q14-8 24 2M38-104q12-6 22 4" stroke="#9a9ea8" stroke-width="5" fill="none" stroke-linecap="round"/>`;
      // óculos redondos
      g += `<g fill="#fff" fill-opacity=".16" stroke="#8a3f58" stroke-width="7"><circle cx="${n(xL)}" cy="20" r="39"/><circle cx="${n(xR)}" cy="20" r="39"/></g>` +
        `<path d="M${n(xL + 39)} 16Q${n((xL + xR) / 2)} 4 ${n(xR - 39)} 16" stroke="#8a3f58" stroke-width="7" fill="none"/><path d="M${n(xL - 22)} 2l12-10M${n(xR - 22)} 2l12-10" stroke="#fff" stroke-width="6" stroke-linecap="round"/>`;
      return g;
    },
  };

  // ---------------------------------------------------------------- Astro Bob: robô de manutenção flutuante
  const BOB_HEAD = -46;
  function bob(t, o) {
    o = o || {};
    const pose = o.pose || 'stand', st = o.state || {}, expr = o.expr || 'neutral', talk = o.talk || 0, s = 21.4;
    const by = Math.sin(t * 2.1) * 13, moving = pose === 'walk' || pose === 'run';
    let tilt = Math.sin(t * 1.3) * 3, tn = .12, y = -330 + by;
    if (pose === 'walk') { tilt = 10; tn = .7; } else if (pose === 'run') { tilt = 21 + Math.sin(t * 9) * 3; tn = .85; } else if (pose === 'fall') { tilt = (t * 260) % 360; y = -300; } else if (pose === 'crawl' || pose === 'sit') { y = -240 + by * .5; } else if (pose === 'type') { tn = .55; tilt = 7; } else if (pose === 'point') tn = .4;
    const c = [0, 0], shy = 96;
    let hL = [-112, 186 + Math.sin(t * 2.7) * 12], hR = [112, 186 + Math.sin(t * 3.1) * 12], kL = 'c', kR = 'c', eL = 1, eR = -1;
    if (pose === 'point') { hR = [190, 40 + Math.sin(t * 5) * 6]; eR = 1; hL = [-108, 170]; }
    if (pose === 'hold') { hR = [150, -30 + Math.sin(t * 3) * 6]; eR = 1; }
    if (pose === 'hands_head') { hL = [-118, -16]; hR = [118, -16]; }
    if (pose === 'type') { const k = q => V.rnd(Math.floor(t * 13) + q) * 12; hL = [146, 118 - k(3)]; hR = [106, 124 - k(9)]; eL = 1; eR = 1; }
    if (pose === 'float' || moving) { hL = [-140, 150 + Math.sin(t * 3) * 22]; hR = [120, 170 - Math.sin(t * 3) * 22]; }
    const shL = [-84, shy], shR = [84, shy];
    const qL = ik(shL, hL, 66, 62, eL), qR = ik(shR, hR, 66, 62, eR);
    const mech = (sh, q, sign) => {
      const a = Math.atan2(q.e[1] - q.j[1], q.e[0] - q.j[0]) / D2R, tip = q.e;
      return limb(sh, q.j, q.e, 14, 12, 11, '#aeb9c8') + `<circle cx="${n(sh[0])}" cy="${n(sh[1])}" r="17" fill="#7c8a9c" stroke="${INK}" stroke-width="6"/><circle cx="${n(q.j[0])}" cy="${n(q.j[1])}" r="14" fill="#ffb02e" stroke="${INK}" stroke-width="6"/>` +
        `<g transform="translate(${n(tip[0])} ${n(tip[1])}) rotate(${n(a)})" stroke="${INK}" stroke-width="6" fill="#dfe6ee" stroke-linejoin="round"><circle r="13"/><path d="M6-10L36-20L42-6L22-2z"/><path d="M6 10L36 20L42 6L22 2z"/></g>`;
    };
    let g = '';
    // jato sob o corpo
    const fl = 44 + Math.sin(t * 37) * 13 + Math.sin(t * 23) * 8;
    g += `<g transform="translate(0 196)"><path d="M-26 0Q0 ${n(fl * 2.1)} 26 0z" fill="#7fd4ff" stroke="${INK}" stroke-width="6" stroke-linejoin="round"/><path d="M-13 0Q0 ${n(fl * 1.2)} 13 0z" fill="#fff"/></g>`;
    g += `<path d="M-40 150h80l-12 46h-56z" fill="#7c8a9c" stroke="${INK}" stroke-width="${OUT}" stroke-linejoin="round"/>`;
    g += mech(shR, qR, 1);
    if (o.hold) g += heldItem(t, o, qR.e, 0);
    // corpo com arnês, painel e cinto de ferramentas
    g += `<rect x="-104" y="44" width="208" height="124" rx="46" fill="#e8edf3" stroke="${INK}" stroke-width="${OUT}"/>`;
    g += `<path d="M-84 68Q0 100 84 68" stroke="#ffb02e" stroke-width="13" fill="none"/><path d="M-84 68Q0 100 84 68" stroke="${INK}" stroke-width="3" fill="none" stroke-dasharray="10 12"/>`;
    g += `<rect x="-38" y="86" width="76" height="46" rx="10" fill="#10222e" stroke="${INK}" stroke-width="6"/>`;
    const bars = [0, 1, 2, 3, 4].map(k => { const h = 8 + 22 * Math.abs(Math.sin(t * 5 + k)) * (talk > .05 ? 1 : .45); return `<rect x="${-28 + k * 12}" y="${n(109 - h / 2)}" width="8" height="${n(h)}" rx="3" fill="#39d98a"/>`; }).join('');
    g += bars;
    g += `<rect x="-100" y="136" width="200" height="24" rx="10" fill="#7a5a3a" stroke="${INK}" stroke-width="5"/><rect x="-74" y="130" width="22" height="42" rx="5" fill="#ffd23f" stroke="${INK}" stroke-width="4"/><path d="M60 128v42" stroke="#c8cfd8" stroke-width="10" stroke-linecap="round"/><path d="M60 128v42" stroke="${INK}" stroke-width="2"/>`;
    // antena e cabeça
    g += `<g transform="translate(0 ${BOB_HEAD})">`;
    const R = 112, ay = -R - 56, sv = Math.sin(t * 2.6) * 7, pisca = Math.sin(t * 4) > 0;
    g += `<path d="M0 ${-R + 4}Q${n(sv * .5)} ${-R - 30} ${n(sv)} ${ay}" stroke="${INK}" stroke-width="8" fill="none"/><circle cx="${n(sv)}" cy="${ay}" r="15" fill="${pisca ? '#ff5a4d' : '#b23a30'}" stroke="${INK}" stroke-width="6"/>`;
    g += `<rect x="${-R - 16}" y="-22" width="28" height="60" rx="10" fill="#7c8a9c" stroke="${INK}" stroke-width="6"/><rect x="${R - 12}" y="-22" width="28" height="60" rx="10" fill="#7c8a9c" stroke="${INK}" stroke-width="6"/>`;
    g += sphere(R) + `<g transform="scale(.85)">${face({ R: 132, turn: tn, expr, talk, t, seed: s, state: st })}</g>`;
    g += `<path d="M-90-70Q-60-100-24-102" stroke="#fff" stroke-width="9" stroke-linecap="round" fill="none"/></g>`;
    g += mech(shL, qL, -1);
    const f = o.flip ? -1 : 1, sk = pose === 'fall' ? .4 : .8;
    return `<g transform="scale(${f} 1)"><ellipse cx="0" cy="26" rx="${n(96 * sk + Math.sin(t * 2.1) * 8)}" ry="15" fill="#000" opacity=".2"/><g transform="translate(0 ${n(y)}) rotate(${n(tilt)}) translate(0 ${n(c[1])})">${g}</g></g>`;
  }

  // ---------------------------------------------------------------- API
  V.chars.ze = (t, o) => rig(ZE, t, o);
  V.chars.nina = (t, o) => rig(NINA, t, o);
  V.chars.cida = (t, o) => rig(CIDA, t, o);
  V.chars.astro_bob = bob;

  const LOOKS = { ze: ZE, nina: NINA, cida: CIDA };
  // centro da cabeça no referencial do boneco: legendas e reações usam isto
  V.charHead = function (name, o, t) {
    if (name === 'astro_bob') return { x: 0, y: -330 + BOB_HEAD + Math.sin(t * 2.1) * 13, r: 112 };
    const L = LOOKS[name];
    if (!L) return { x: 0, y: -440, r: 120 };
    const P = poseOf(o.pose || 'stand', t, L.seed), sc = L.scale || 1, le = P.lean * D2R, hx = P.hip[0] + TORSO * Math.sin(le), hy = P.hip[1] - TORSO * Math.cos(le);
    const h = P.headAbs ? P.headAbs : [hx + P.head[0], hy - HEAD_UP + P.head[1]];
    return { x: h[0] * sc, y: h[1] * sc, r: 132 * sc };
  };

  const POSES = 'stand|walk|run|point|hold|hands_head|sit|crawl|type|fall|float', EXPR = 'neutral|scared|happy|angry|sad|shock|sleepy';
  const data = { pose: POSES, expr: EXPR, hold: 'tape', state: { dirt: .3, bandage: true } };
  V.docs.chars.ze = { desc: 'Zé: cabeça-esfera creme, olhos de ponto, boné verde, jaqueta oliva, jeans, tênis brancos, mochila preta. Protagonista medroso mas esperto.', data };
  V.docs.chars.nina = { desc: 'Nina: cabeça-esfera, puff cacheado escuro com fita vermelha, capa de chuva amarela, legging preta, tênis vermelhos. Melhor amiga.', data };
  V.docs.chars.cida = { desc: 'Dona Cida: vizinha idosa, cabelo grisalho cacheado, óculos redondos, blusa florida, casaco roxo e saia marrom.', data };
  V.docs.chars.astro_bob = { desc: 'Bob: robozinho de manutenção flutuante, cabeça-esfera creme, arnês, painel no peito, jato embaixo e garras; sempre paira.', data };
})();
