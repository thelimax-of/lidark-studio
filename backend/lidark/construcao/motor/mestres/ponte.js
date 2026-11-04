// Ponte pênsil sobre o rio: estacas, blocos, torres, ancoragens, cabos, tirantes, tabuleiro, asfalto e mureta; no fim, os carros atravessam ao anoitecer.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, arvore, boneco, camTo, iniciar, som, rotulo, D } = K3;
const E = window.ESPEC, V_ = E.variante, rnd = prng(E.semente ?? 31), F = K3.fala, dur = i => D.falas[i].dur, fim = i => F(i) + dur(i), AUTO = [], LAST = D.falas.length - 1;
const norm = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '');
const tk = (w, i) => { const k = norm(w), q = D.falas[i].words.find(p => norm(p.w) === k); return q ? q.start : F(i) + dur(i) * .12; };
const ult = D.falas[LAST], nPal = ult.texto.split(/[!.]/)[0].trim().split(/\s+/).length, T_USO = (ult.words[nPal - 1]?.end ?? ult.t + ult.dur) + .15;
ceu(V_.ceu[0], V_.ceu[1]); const sol = luzes(V_.sol, 0xd8ecff, 0x90b870, 2.7, 72); scene.environmentIntensity = .3;
const hemi = scene.children.find(o => o.isHemisphereLight); scene.fog = new THREE.Fog(new THREE.Color(V_.ceu[1]), 150, 520);
const O = new THREE.Object3D(), C = new THREE.Color(), UP = new THREE.Vector3(0, 1, 0), VA = new THREE.Vector3(), VB = new THREE.Vector3();
const CONC = 0xc9c7bf, CONC2 = 0xb4b2aa, ACO = 0x7a8796, TORRE = V_.torre, TORRE2 = new THREE.Color(V_.torre).offsetHSL(0, 0, -.022).getHex(), AMAR = 0xffc61a;
const aparece = (o, t0, d = .35, modo = 'pop', dy = 1.3) => { const s = o.scale.clone(), y = o.position.y; o.visible = false; AUTO.push(t => { const k = (t - t0) / d; o.visible = t >= t0; if (!o.visible) return; if (k >= 1) { o.scale.copy(s); o.position.y = y; return; } if (modo === 'pop') o.scale.copy(s).multiplyScalar(Math.max(back(k), .01)); else if (modo === 'cresce') { o.scale.copy(s); o.scale.y = s.y * Math.max(ease(k), .01); } else o.position.y = y + (1 - ease(k)) * dy; }); return o; };
// lote de peças repetidas: cada item {p, q?, s?, t, d, modo, dy, c}
const lote = (geo, material, L, base = 0xffffff) => {
  const m = new THREE.InstancedMesh(geo, material, L.length); m.castShadow = m.receiveShadow = true; m.frustumCulled = false; add(m);
  let fimT = -1; L.forEach((b, i) => { C.set(b.c ?? base); m.setColorAt(i, C); fimT = Math.max(fimT, b.t + b.d); }); fimT += .05; let u = -9;
  AUTO.push(t => { if (t > fimT && u > fimT) return; u = t; for (let i = 0; i < L.length; i++) { const b = L[i], k = (t - b.t) / b.d, s = b.s || [1, 1, 1]; O.position.set(b.p[0], b.p[1], b.p[2]); if (b.q) O.quaternion.copy(b.q); else O.quaternion.identity(); if (k <= 0) O.scale.setScalar(0); else if (b.modo === 'pop') { const e = Math.max(back(k), .001); O.scale.set(s[0] * e, s[1] * e, s[2] * e); } else if (b.modo === 'cresce') O.scale.set(s[0], s[1] * Math.max(ease(k), .001), s[2]); else { O.position.y += (1 - ease(k)) * (b.dy ?? 1.3); O.scale.set(s[0], s[1], s[2]); } O.updateMatrix(); m.setMatrixAt(i, O.matrix); } m.instanceMatrix.needsUpdate = true; });
  return m;
};
const seg = (a, b, r, x = {}) => { VA.set(...a); VB.set(...b).sub(VA); const n = VB.length(), q = new THREE.Quaternion().setFromUnitVectors(UP, VB.normalize()); return { p: a, q, s: [r, n, r], ...x }; };
const G_CIL = new THREE.CylinderGeometry(1, 1, 1, 8).translate(0, .5, 0), G_CAIXA = new THREE.BoxGeometry(1, 1, 1), G_CAIXA0 = new THREE.BoxGeometry(1, 1, 1).translate(0, .5, 0);
const M_L = (o = {}) => new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .7, ...o });

// geometria da ponte --------------------------------------------------------------------------------------
const XT = 24, RW = 36, YD = 9.2, ZD = 4.85, HT = 33, HC = HT + .9, XA = 50, YS = YD + 1.7, YA_ = YD + 5.2;
const zL = y => 6.5 - (6.5 - ZD) * (y / HT), yC = x => { const a = Math.abs(x); return a <= XT ? YS + (HC - YS) * (a / XT) ** 2 : HC + (YA_ - HC) * (a - XT) / (XA - XT); };

// rio, margens, cidade e sítio --------------------------------------------------------------------------------
const rio = add(new THREE.Mesh(new THREE.PlaneGeometry(1400, 1400), mat(V_.rio, { roughness: .28, metalness: .15 }))); rio.rotation.x = -Math.PI / 2; rio.receiveShadow = true;
[-1, 1].forEach(s => { const b = add(new THREE.Mesh(new THREE.BoxGeometry(700, YD, 1400), mat(0x8c7a62))); b.position.set(s * (RW + 350), YD / 2, 0); b.receiveShadow = true; const g = add(new THREE.Mesh(new THREE.PlaneGeometry(700, 1400), mat(V_.grama, { roughness: 1 }))); g.rotation.x = -Math.PI / 2; g.position.set(s * (RW + 350), YD + .02, 0); g.receiveShadow = true; const r_ = add(new THREE.Mesh(new THREE.PlaneGeometry(700, 8.6), mat(0x3b3d45))); r_.rotation.x = -Math.PI / 2; r_.position.set(s * (RW + 350), YD + .05, 0); r_.receiveShadow = true; });
{ const L = []; for (let i = 0; i < 520; i++) { const s = i % 2 ? 1 : -1, z = -200 + rnd() * 330, q = rnd(); L.push({ p: [s * (RW + .6 - q * 3.6), .3 + rnd() * YD * (1 - q) * .9, z], s: [1.2 + rnd() * 2.2, .9 + rnd() * 1.4, 1.2 + rnd() * 2.2], t: -1, d: .1, modo: 'x', dy: 0, c: [0x9a8a74, 0x8c7a62, 0xa89a84, 0x7c6e5a][i % 4] }); } lote(new THREE.IcosahedronGeometry(.7, 0), M_L({ flatShading: true }), L); }
for (let i = 0; i < 90; i++) { const x = -44 + rnd() * 88, z = -300 + rnd() * 270; const l = 0; }
for (let x = -130; x < 130; x += 5) if (Math.abs(x) > RW + 2) add(box(2.6, .02, .2, 0xf2d24a, .01)).position.set(x, YD + .08, 0);
const casa = (x, z, c, tc, a = 3.2) => { const y = YD; add(box(7.5, a, 6, c, .05)).position.set(x, y + a / 2, z); const t = add(sh(new THREE.Mesh(new THREE.ConeGeometry(6, 2.4, 4), mat(tc, { flatShading: true })))); t.rotation.y = .785; t.scale.z = .8; t.position.set(x, y + a + 1.2, z); const sn = z > 0 ? -1 : 1; add(box(1, 2, .08, 0x7a4a26, .01)).position.set(x - 1.8, y + 1, z + sn * 3.03); add(box(1.4, 1.1, .08, 0xaee3f7, .01, { roughness: .15 })).position.set(x + 1.4, y + 1.9, z + sn * 3.03); };
const predio = (x, z, c, a) => { add(box(9, a, 8, c, .05)).position.set(x, YD + a / 2, z); const n = Math.floor(a / 2.2); for (let i = 0; i < n; i++) for (let k = 0; k < 3; k++) { add(box(1.5, 1.1, .08, 0xaee3f7, .01, { roughness: .15 })).position.set(x - 2.8 + k * 2.8, YD + 1.5 + i * 2.2, z + (z > 0 ? -4.05 : 4.05)); add(box(.08, 1.1, 1.5, 0xaee3f7, .01, { roughness: .15 })).position.set(x + (x > 0 ? -4.55 : 4.55), YD + 1.5 + i * 2.2, z - 2.2 + k * 2.2); } };
// cidade na margem esquerda
[[-44, -12, 0xe9c9a0, 11], [-55, -13, 0xa9c9e8, 16], [-66, -12, 0xf2b8c6, 9], [-78, -13, 0xd8d0e8, 19], [-46, 13, 0xd6e6c0, 13], [-57, 14, 0xf0dba0, 8], [-70, 13, 0xbfe0ef, 15], [-84, 13, 0xeab0a6, 12], [-50, -28, 0xd8d0e8, 22], [-64, -30, 0xf0dba0, 14], [-80, -29, 0xa9c9e8, 25], [-96, -24, 0xf2b8c6, 18]].forEach(([x, z, c, a]) => predio(x, z, c, a));
// sítio e igrejinha na margem direita
[[68, 12, 0xf2b8c6, 0x8c5a3c], [80, -12, 0xa9c9e8, 0xb5482f], [66, -14, 0xf0dba0, 0xc2502f], [92, 13, 0xd6e6c0, 0xb5482f], [105, -13, 0xeab0a6, 0x8c5a3c], [72, -34, 0xbfe0ef, 0xb5482f], [92, -36, 0xd8d0e8, 0xc2502f]].forEach(([x, z, c, t]) => casa(x, z, c, t));
{ const x = 86, z = 34; add(box(8, 6, 12, 0xf4efe6, .05)).position.set(x, YD + 3, z); add(box(3.2, 11, 3.2, 0xf4efe6, .05)).position.set(x, YD + 5.5, z - 7); const t = add(sh(new THREE.Mesh(new THREE.ConeGeometry(2.6, 3.4, 4), mat(0x3f6fb5, { flatShading: true })))); t.rotation.y = .785; t.position.set(x, YD + 12.7, z - 7); add(box(.2, 1.4, .2, 0xffd23f, .02)).position.set(x, YD + 15, z - 7); add(box(.9, .2, .2, 0xffd23f, .02)).position.set(x, YD + 15.1, z - 7); }
for (let i = 0; i < 90; i++) { const s = i % 3 ? 1 : -1, x = s * (RW + 3 + rnd() * 90), z = -130 + rnd() * 240; if (Math.abs(z) < 7.5) continue; if (s > 0 && x < 58 && Math.abs(z) < 12) continue; if (s < 0 && Math.abs(z) < 42 && x > -100 && x < -40) continue; const q = add(arvore(rnd, 2 + rnd() * 2, rnd() > .45)); q.position.set(x, YD, z); }
[[-240, -320, 90, 0x6d9c6b], [-60, -420, 130, 0x7fae86], [170, -360, 100, 0x6d9c6b], [340, -300, 70, 0x87b48c]].forEach(([x, z, a, c]) => { const m = add(new THREE.Mesh(new THREE.ConeGeometry(a * 1.5, a, 6), mat(c, { flatShading: true }))); m.position.set(x, a / 2, z); });
// barquinhos no rio e correnteza
const barco = (c, s = 1) => { const g = new THREE.Group(); add(box(4 * s, .7, 1.5 * s, c, .1), g).position.y = .35; add(box(1.4 * s, .9, 1.1 * s, 0xf4efe6, .05), g).position.set(-.5 * s, 1.1, 0); add(g); return g; };
const pescadores = [[-14, 40, 0xd8443a, .6], [16, 58, 0x2f7fd6, -.4], [-6, -46, 0xffd23f, 1.1], [9, -70, 0xf4efe6, .2]].map(([x, z, c, r_]) => { const g = barco(c); g.position.set(x, 0, z); g.rotation.y = r_; return g; });
const NCO = 240, cor = new THREE.InstancedMesh(new THREE.PlaneGeometry(.24, 5), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: .22, depthWrite: false }), NCO); cor.frustumCulled = false; add(cor); const CO = []; for (let i = 0; i < NCO; i++) CO.push([-RW + rnd() * RW * 2, rnd(), .6 + rnd() * .8]);
AUTO.push(t => { for (let i = 0; i < NCO; i++) { const [x, u, v] = CO[i]; O.position.set(x, .04, -180 + ((u * 340 + t * 7 * v) % 340)); O.rotation.set(-Math.PI / 2, 0, 0); O.scale.set(1, v * 1.2, 1); O.updateMatrix(); cor.setMatrixAt(i, O.matrix); } cor.instanceMatrix.needsUpdate = true; });

// tempos ---------------------------------------------------------------------------------------------------------
const T = { est: tk('estacas', 1), blo: tk('bloco', 2), tor: tk('torres', 3), anc: tk('ancoragem', 4), cab: tk('cabos', 5), tir: tk('tirantes', 6), tab: tk('tabuleiro', 7), asf: tk('asfalto', 8), mur: tk('mureta', 9) };

// abertura: ponte fraca, apoiada na lama, desaba ----------------------------------------------------------------
const T_D = tk('desaba', 0), VELHA = new THREE.Group(); add(VELHA); const NV = 8, LV = (RW * 2) / NV, velhas = [];
for (let i = 0; i < NV; i++) { const g = new THREE.Group(); g.position.set(-RW + LV * (i + .5), YD - .4, 0); VELHA.add(g); add(box(LV - .05, .8, 8, 0xa98a62, .03), g); add(box(LV - .05, .05, 7, 0x4a4a50, .01), g).position.y = .42; [-1, 1].forEach(s => { for (let k = 0; k < 4; k++) add(box(.16, .9, .16, 0x7a5c3a, .02), g).position.set(-LV / 2 + 1 + k * 2.1, .85, s * 3.8); add(box(LV - .1, .12, .14, 0x7a5c3a, .02), g).position.set(0, 1.25, s * 3.8); }); const n = Math.abs(i - 3.5); velhas.push({ g, t: .2 + n / 2.5 * Math.max(.6, T_D - .5), x: g.position.x, r: (i < 3.5 ? 1 : -1) * (.25 + (i % 3) * .14) }); }
const pilV = []; for (let i = 1; i < NV; i++) { const g = new THREE.Group(); g.position.set(-RW + LV * i, 0, 0); VELHA.add(g); [-2.6, 2.6].forEach(z => add(cil(.42, .5, YD - .6, 0x9a8f80, 12), g).position.set(0, (YD - .6) / 2, z)); add(box(1.6, .6, 7, 0x9a8f80, .03), g).position.y = YD - 1; const n = Math.abs(i - 4); pilV.push({ g, t: .02 + n / 3 * Math.max(.6, T_D - .5), r: (i % 2 ? 1 : -1) * .5 }); }
const carro = (c, s = 1) => { const g = new THREE.Group(); add(box(3.4 * s, .55 * s, 1.5 * s, c, .12), g).position.y = .55 * s; add(box(1.8 * s, .5 * s, 1.3 * s, 0xaee3f7, .1, { roughness: .15 }), g).position.y = 1.05 * s; [[-1.1, .7], [1.1, .7], [-1.1, -.7], [1.1, -.7]].forEach(([a, b]) => { const r = add(cil(.3 * s, .3 * s, .2 * s, 0x1e2026, 16), g); r.rotation.x = Math.PI / 2; r.position.set(a * s, .3 * s, b * s); }); return g; };
{ const k = add(carro(0xffb627), velhas[4].g); k.position.set(.4, .42, 1.8); const k2 = add(carro(0x2f7fd6), velhas[2].g); k2.position.set(-.8, .42, -1.8); }
const NSP = 420, spray = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.34, 1), new THREE.MeshBasicMaterial({ color: 0xeaf7ff }), NSP); spray.frustumCulled = false; add(spray); const SP = []; for (let i = 0; i < NSP; i++) { const e = velhas[i % NV], a = rnd() * 6.28, v = 3 + rnd() * 11; SP.push({ e, x: e.x + (rnd() - .5) * LV, z: (rnd() - .5) * 9, vx: Math.cos(a) * v * .5, vz: Math.sin(a) * v * .5, vy: 6 + rnd() * 12, s: .5 + rnd() * 1.2 }); }
const NPO = 90, po = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.3, 0), mat(0xb49c7c, { flatShading: true }), NPO); po.frustumCulled = false; add(po); const PO = []; for (let i = 0; i < NPO; i++) PO.push({ i: i % NV, ox: (rnd() - .5) * LV, oz: (rnd() - .5) * 7, vx: (rnd() - .5) * 6, vz: (rnd() - .5) * 6, vy: rnd() * 3, r: rnd() * 6 });
const qd = q => Math.max(0, q), QUEDA = 1.25;
AUTO.push(t => {
  const on = t < fim(0) + .02; VELHA.visible = spray.visible = po.visible = on; if (!on) return;
  pilV.forEach(p => { const q = qd(t - p.t); p.g.rotation.z = p.r * Math.min(1, q * q * 1.4); p.g.position.y = -Math.min(q * q * 4, 12); });
  velhas.forEach(v => { const q = qd(t - v.t); v.g.position.y = YD - .4 - 6.5 * q * q; v.g.rotation.z = v.r * Math.min(1.5, q * 1.3); v.g.visible = v.g.position.y > -6; });
  for (let i = 0; i < NSP; i++) { const b = SP[i], q = t - b.e.t - QUEDA; if (q <= 0 || q > 1.9) { O.scale.setScalar(0); } else { O.position.set(b.x + b.vx * q, Math.max(0, b.vy * q - 8 * q * q), b.z + b.vz * q); O.rotation.set(0, 0, 0); O.scale.setScalar(b.s * (1 - q / 2.1)); } O.updateMatrix(); spray.setMatrixAt(i, O.matrix); } spray.instanceMatrix.needsUpdate = true;
  for (let i = 0; i < NPO; i++) { const b = PO[i], v = velhas[b.i], q = t - v.t; if (q <= .1) { O.scale.setScalar(0); } else { O.position.set(v.x + b.ox + b.vx * q, Math.max(.1, YD - .4 + b.vy * q - 8 * q * q), b.oz + b.vz * q); O.rotation.set(b.r + q * 4, b.r, q * 3); O.scale.setScalar(1 + (b.r % 1)); } O.updateMatrix(); po.setMatrixAt(i, O.matrix); } po.instanceMatrix.needsUpdate = true;
});

// estacas: pórtico sobre duas balsas, com quatro martelos -----------------------------------------------------------
const XP = [-3.75, -2.25, -.75, .75, 2.25, 3.75], ZP = [-7.5, -5, -2.5, 0, 2.5, 5, 7.5], LPI = []; const tP0 = T.est + .05, tPD = (fim(1) - .2 - tP0) / ZP.length;
[-XT, XT].forEach((X, a) => ZP.forEach((z, r_) => XP.forEach((x, c) => { LPI.push({ p: [X + x, -1, z], s: [.4, 3.1, .4], t: tP0 + r_ * tPD, d: tPD * .85, modo: 'desce', dy: 5.4, c: c % 2 ? CONC : CONC2 }); })));
lote(new THREE.CylinderGeometry(1, 1, 1, 16).translate(0, .5, 0), M_L({ roughness: .6 }), LPI);
for (let q = tP0; q < fim(1) - .2; q += tPD / 3) som(q, 'impact');
const portico = X => { const g = new THREE.Group(); add(g); g.position.x = X; [-8.2, 8.2].forEach(x => { add(box(4.4, 1, 11, 0x46505e, .08), g).position.set(x, .5, 0); add(box(4.5, .1, 11.1, 0xd8443a, .02), g).position.set(x, .95, 0); [-3.2, 3.2].forEach(z => { const v = add(box(.5, 11.5, .5, AMAR, .03), g); v.position.set(x, 6.5, z); }); add(box(.4, .4, 7, AMAR, .03), g).position.set(x, 12, 0); for (let i = 0; i < 9; i++) add(box(.12, .12, 7.2, 0x333844, .01), g).position.set(x, 2 + i * 1.2, 0); }); add(box(17, .9, 1.2, AMAR, .04), g).position.y = 12.2; const hs = XP.map(x => { const m = new THREE.Group(); m.position.x = x; g.add(m); add(box(.95, 1.5, .95, 0x333844, .05), m); const v_ = add(box(.2, 1, .2, ACO, .02), m); v_.geometry = G_CAIXA0; v_.position.y = .7; m.userData.h = v_; return m; }); return { g, hs }; };
const PO_ = [portico(-XT), portico(XT)];
AUTO.push(t => { const on = t >= F(1) - .1 && t < F(2) + .4; PO_.forEach(P_ => { P_.g.visible = on; if (!on) return; const u = (t - tP0) / tPD, r_ = clamp(Math.floor(u), 0, ZP.length - 1), f = clamp(u - r_); const z = ZP[r_] + (f > .88 ? (f - .88) / .12 * 2.5 : 0); P_.g.position.z = t > fim(1) - .2 ? 9 + (t - fim(1) + .2) * 4 : Math.min(z, 7.5); const top = -1 + 3.1 + (1 - ease(f / .85)) * 5.4, b = (Math.sin(t * 19) * .5 + .5) * .9; P_.hs.forEach(m => { m.position.y = top + .75 + b * (t < fim(1) - .3 ? 1 : 0); m.userData.h.scale.set(.2, 11.8 - m.position.y - .7, .2); }); }); });

// blocos: gaiola de ferro e concreto ---------------------------------------------------------------------------------
const YB0 = 1.6, YB1 = 3.6, tA0 = F(2) + .15, tAF = Math.max(T.blo - .15, F(2) + dur(2) * .55), LAR = [];
[-XT, XT].forEach(X => { [1.95, 2.5, 3.05].forEach((y, l) => { for (let i = 0; i < 13; i++) { const x = X - 4.2 + i * .7, q = tA0 + (l + i / 13) / 3.2 * (tAF - tA0); LAR.push({ ...seg([x, y, -8.2], [x, y, 8.2], .05), t: q, d: .18, modo: 'pop' }); } for (let i = 0; i < 24; i++) { const z = -8 + i * .696, q = tA0 + (l + i / 24) / 3.2 * (tAF - tA0); LAR.push({ ...seg([X - 4.3, y + .08, z], [X + 4.3, y + .08, z], .05), t: q, d: .18, modo: 'pop' }); } }); [-1, 1].forEach(s => { for (let a = 0; a < 5; a++) for (let b = 0; b < 4; b++) { const x = X - .6 + a * .3, z = s * zL(3) - .45 + b * .3; LAR.push({ ...seg([x, 1.8, z], [x, 5.4, z], .05), t: tAF - .5 + a * .06, d: .25, modo: 'cresce' }); } }); });
lote(G_CIL, M_L({ metalness: .5, roughness: .45 }), LAR, 0xc9652d);
[-XT, XT].forEach(X => { const b = add(box(9.2, YB1 - YB0, 17.6, CONC, .04)); b.position.set(X, (YB0 + YB1) / 2, 0); const q = b.position.y; b.scale.y = 1; AUTO.push(t => { const k = ease((t - tAF) / Math.max(.8, (fim(2) - tAF) * .75)); b.visible = k > 0; b.scale.y = Math.max(k, .01); b.position.y = YB0 + (YB1 - YB0) * k / 2; }); const fo = add(box(9.8, 2.2, 18.2, 0xd9a55f, .02, { transparent: true, opacity: 0 })); fo.visible = false; });
{ const L = []; [-XT, XT].forEach(X => { for (let i = 0; i < 12; i++) [-1, 1].forEach(s => L.push({ p: [X - 4.4 + i * .8, YB0 + 1, s * 8.95], s: [.74, 2.1, .1], t: tA0 + i * .03, d: .2, modo: 'pop', c: i % 2 ? 0xd9a55f : 0xc98d4f })); for (let i = 0; i < 22; i++) [-1, 1].forEach(s => L.push({ p: [X + s * 4.75, YB0 + 1, -8.5 + i * .81], s: [.1, 2.1, .74], t: tA0 + i * .02, d: .2, modo: 'pop', c: i % 2 ? 0xd9a55f : 0xc98d4f })); }); const m = lote(G_CAIXA, M_L(), L); AUTO.push(t => { m.visible = t < F(3) - .02; }); }
{ const m = add(box(9.4, .1, 1.4, 0xd9a55f, .02)); m.position.set(XT, 3.72, 6.2); AUTO.push(t => { m.visible = t > F(2) - .02 && t < F(3) - .02; }); }
const betoneira = (() => { const g = new THREE.Group(); add(g); g.rotation.y = -Math.PI / 2; add(box(9, 1, 5, 0x46505e, .08), g).position.y = .5; add(box(5, 1.4, 2.4, 0xd8443a, .08), g).position.set(0, 1.7, 0); const d_ = add(cil(1.1, 1.1, 3, 0xf0e8d8, 20), g); d_.rotation.z = Math.PI / 2; d_.position.set(0, 3.2, 0); const tb = add(cil(.2, .2, 6, 0x56606e, 10), g); tb.rotation.x = .9; tb.position.set(0, 4.6, -2.6); AUTO.push(t => { g.visible = t > F(2) - .1 && t < F(3) - .02; g.position.set(XT - 9.8 - (1 - ease((t - F(2) + .1) / .8)) * 22, 0, 1); d_.rotation.x = t * 3; }); return g; })();
const NCC = 60, jato = new THREE.InstancedMesh(new THREE.SphereGeometry(.16, 8, 6), mat(0xb4b2aa), NCC); jato.frustumCulled = false; add(jato); AUTO.push(t => { const on = t > tAF && t < fim(2); jato.visible = on; if (!on) return; for (let i = 0; i < NCC; i++) { const u = (t * 1.6 + i / NCC) % 1; O.position.set(XT - 7.7 + u * 3, 3.1 - u * u * 1.4, 1 + Math.cos(i * 1.3) * .15); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); jato.setMatrixAt(i, O.matrix); } jato.instanceMatrix.needsUpdate = true; });

// torres, anel por anel, com plataforma que sobe junto -----------------------------------------------------------------
const NR = 40, HR = (HT - YB1) / NR, tT0 = T.tor + .1, tTD = Math.max(1, fim(3) - tT0 - .35), LR = [], QL = s => new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), s * Math.atan((6.5 - ZD) / HT));
[-XT, XT].forEach((X, a) => [-1, 1].forEach(s => { for (let i = 0; i < NR; i++) { const y = YB1 + i * HR, q = tT0 + i / NR * tTD; LR.push({ p: [X, y, s * zL(y)], q: QL(s), s: [2 - i * .012, HR * .97, 1.5 - i * .009], t: q, d: tTD / NR * 1.6, modo: 'desce', dy: .5, c: i % 2 ? TORRE : TORRE2 }); } }));
lote(G_CAIXA0, M_L({ roughness: .5, metalness: .12 }), LR);
const yT = t => YB1 + clamp((t - tT0) / tTD) * (HT - YB1), tY = y => tT0 + (y - YB1) / (HT - YB1) * tTD;
{ const L = [];[-XT, XT].forEach(X => { [YD - 2.6, 17.5, 25, HT - 1].forEach((y, i) => { const zz = zL(y) * 2 - 1, n = 8; L.push({ p: [X, y, 0], s: [1.5, 1.5, zz], t: tY(y) + .25, d: .35, modo: 'pop', c: TORRE }); for (let k = 0; k < n; k++) L.push({ p: [X + .78, y, -zz / 2 + (k + .5) * zz / n], s: [.06, 1.1, zz / n * .7], t: tY(y) + .4, d: .2, modo: 'pop', c: TORRE2 }); }); [-1, 1].forEach(s => L.push({ p: [X, HT + .35, s * ZD], s: [2.6, .9, 1.5], t: tT0 + tTD, d: .3, modo: 'pop', c: 0x46505e })); }); lote(G_CAIXA, M_L({ roughness: .5 }), L); }
const plataforma = X => { const g = new THREE.Group(); add(g); add(box(3.8, .12, 4.4, 0xd9a55f, .02), g); [[-1.8, -2.1], [1.8, -2.1], [-1.8, 2.1], [1.8, 2.1]].forEach(([a, b]) => { add(box(.08, 1.15, .08, AMAR, .01), g).position.set(a, .6, b); add(box(.08, 2.6, .08, ACO, .01), g).position.set(a, -1.2, b); }); [-2.1, 2.1].forEach(z => add(box(3.7, .07, .07, AMAR, .01), g).position.set(0, 1.15, z)); add(box(.07, .07, 4.3, AMAR, .01), g).position.set(1.85, 1.15, 0); add(box(3.8, .1, 4.4, 0x56606e, .02), g).position.y = -2.4; g.position.x = X; AUTO.push(t => { const on = t > T.tor - .3 && t < fim(3) + .02; g.visible = on; if (on) { const y = yT(t) + .1; g.position.y = y; g.position.z = zL(y) + .2; } }); return g; };
plataforma(XT); plataforma(-XT);
for (let i = 0; i < NR; i += 3) som(tT0 + i / NR * tTD, 'tijolo');

// ancoragens --------------------------------------------------------------------------------------------------------------
const tAn = Math.min(T.anc, F(4) + dur(4) * .2), tAnD = Math.max(1.2, fim(4) - tAn - .5);
{ const L = [], LV2 = []; [-1, 1].forEach(sx => [-1, 1].forEach(sz => { for (let i = 0; i < 12; i++) { const w = 13 - i * .7; L.push({ p: [sx * (XA + 1.4 + i * .3), YD + i * .55, sz * 8], s: [w, .53, 6.2], t: tAn + i / 12 * tAnD * .75, d: .3, modo: 'desce', dy: 1.6, c: i % 2 ? CONC : CONC2 }); } for (let i = 0; i < 16; i++) { const a = -.5 + i / 15, q = tAn + tAnD * .72 + i * .03; LV2.push({ ...seg([sx * (XA - .2), YA_ - .2, sz * ZD], [sx * (XA + 6.4), YD + 3.4, sz * (ZD + a * 4.4 + 2)], .1), t: q, d: .2, modo: 'cresce' }); } })); lote(G_CAIXA0, M_L(), L); lote(G_CIL, M_L({ metalness: .6, roughness: .35 }), LV2, 0x3c4350); }
[-1, 1].forEach(sx => [-1, 1].forEach(sz => { const t_ = add(new THREE.Mesh(new THREE.IcosahedronGeometry(4.2, 1), mat(0x8a6a48, { flatShading: true }))); t_.castShadow = true; t_.position.set(sx * (XA + 13), YD + .2, sz * 13.5); t_.scale.y = .5; aparece(t_, F(4) + .05, .35, 'pop'); }));
for (let i = 0; i < 12; i += 2) som(tAn + i / 12 * tAnD * .75, 'tijolo');

// cabo principal: fios que passam um a um ---------------------------------------------------------------------------------
const tC0 = T.cab + .1, tCD = Math.max(1.5, fim(5) - tC0 - .3), NF = 7, NX = 100, OF = [[0, 0]]; for (let i = 0; i < 6; i++) OF.push([Math.cos(i * 1.047) * .24, Math.sin(i * 1.047) * .24]);
{ const L = []; [-1, 1].forEach(sz => OF.forEach(([a, b], f) => { for (let i = 0; i < NX; i++) { const x0 = -XA + i, x1 = x0 + 1.02; const u = i / NX; L.push({ ...seg([x0, yC(x0) + b, sz * ZD + a], [x1, yC(x1) + b, sz * ZD + a], .135), t: tC0 + (f + u) / NF * tCD, d: .06, modo: 'x', dy: 0, c: f % 2 ? 0xc6ccd4 : 0xdfe3e8 }); } })); lote(G_CIL, M_L({ metalness: .55, roughness: .35 }), L); }
const rodas = [-1, 1].map(s => { const g = new THREE.Group(); add(g); const r_ = add(new THREE.Mesh(new THREE.TorusGeometry(.75, .16, 8, 20), mat(AMAR)), g); r_.rotation.y = Math.PI / 2; g.userData.r = r_; AUTO.push(t => { const u = (t - tC0) / tCD * NF, on = t > tC0 && t < tC0 + tCD; g.visible = on; if (!on) return; const x = -XA + (u % 1) * NX; g.position.set(x, yC(x) + .9, s * ZD); r_.rotation.x = t * 12; }); return g; });
{ const L = []; for (let i = 0; i < 2; i++) { } }
for (let q = tC0; q < tC0 + tCD; q += tCD / NF / 2) som(q, 'zumbido');
// abraçadeiras
{ const L = []; [-1, 1].forEach(sz => { for (let x = -XA + 1; x < XA; x += 2) { if (Math.abs(Math.abs(x) - XT) < .6) continue; L.push({ p: [x, yC(x), sz * ZD], s: [.34, .55, .55], t: T.tir, d: .2, modo: 'pop' }); } }); lote(G_CAIXA, M_L({ metalness: .4 }), L, 0x3c4350); }

// tirantes -----------------------------------------------------------------------------------------------------------------------
const tH0 = T.tir + .1, tHD = Math.max(1.5, fim(6) - tH0 - .35), XH = []; for (let x = 1; x <= 35; x += 2) XH.push(x, -x); const LH = [], DZ = [-.14, .14];
const ordem = x => (Math.abs(x) - 1) / 34;
[-1, 1].forEach(sz => XH.forEach(x => DZ.forEach(d => LH.push({ ...seg([x, yC(x), sz * ZD + d], [x, YD - .1, sz * ZD + d], .055), t: tH0 + ordem(x) * tHD, d: .3, modo: 'cresce' }))));
lote(G_CIL, M_L({ metalness: .5, roughness: .4 }), LH, 0xe9edf1); for (let i = 0; i < 18; i++) som(tH0 + i / 17 * tHD, i % 2 ? 'toc' : 'pop');
// cestinha pendurada no cabo
const cesta = new THREE.Group(); add(cesta); add(box(1.9, .08, 1.5, 0xd9a55f, .02), cesta); [[-.9, -.7], [.9, -.7], [-.9, .7], [.9, .7]].forEach(([a, b]) => add(box(.05, 1, .05, AMAR, .01), cesta).position.set(a, .5, b)); [-.7, .7].forEach(z => add(box(1.85, .05, .05, AMAR, .01), cesta).position.set(0, 1, z)); [-.9, .9].forEach(x => add(box(.05, .05, 1.45, AMAR, .01), cesta).position.set(x, 1, 0)); [-.85, .85].forEach(x => { const c_ = add(cil(.03, .03, 3.9, ACO, 6), cesta); c_.position.set(x, 2, .7); }); const xCe = t => 1 + clamp((t - tH0) / tHD) * 34;
AUTO.push(t => { const on = t > F(6) - .05 && t < fim(6) + .02; cesta.visible = on; if (on) { const x = xCe(t); cesta.position.set(x, yC(x) - 3.95, ZD + .7); cesta.rotation.z = -Math.atan2(yC(x + .2) - yC(x - .2), .4) * .4 + Math.sin(t * 2) * .02; } });

// tabuleiro: cada pedaço sobe do barco ------------------------------------------------------------------------------------------------
const tD0 = T.tab + .1, tDD = Math.max(1.8, fim(7) - tD0 - .5), XS = []; for (let x = 1; x <= 35; x += 2) XS.push(x, -x); const tS = x => tD0 + (Math.abs(x) - 1) / 34 * tDD, dyS = x => Math.abs(x) > 18 && Math.abs(x) < 30 ? -1.4 : -(YD - 1.6);
{ const Lz = [], Lc = [], Ld = [], Lv = []; XS.forEach(x => { const t = tS(x), d = .62, dy = dyS(x), bs = { t, d, modo: 'desce', dy }; Lz.push({ p: [x, YD - .2, 0], s: [1.99, .34, ZD * 2], c: CONC, ...bs }); [-1, 1].forEach(s => { Lc.push({ p: [x, YD - .42, s * ZD], s: [2, .24, .26], ...bs, c: V_.viga }, { p: [x, YD - 2, s * ZD], s: [2, .24, .26], ...bs, c: V_.viga }); [[-1, 1], [1, -1]].forEach(([a, b]) => { VA.set(a, 1.58 * b, 0).normalize(); Ld.push({ p: [x, YD - 1.21, s * ZD], q: new THREE.Quaternion().setFromUnitVectors(UP, VA), s: [.15, 2.55, .15], ...bs, c: V_.viga }); }); }); Lv.push({ p: [x, YD - 2, 0], s: [.22, .22, ZD * 2], ...bs, c: V_.viga }); }); lote(G_CAIXA, M_L(), Lz); lote(G_CAIXA, M_L({ roughness: .55, metalness: .1 }), Lc); lote(G_CAIXA, M_L({ roughness: .55, metalness: .1 }), Ld); lote(G_CAIXA, M_L({ roughness: .55 }), Lv); }
XS.forEach(x => som(tS(x) + .5, x > 0 ? 'tijolo' : 'toc'));
const balsas = [-1, 1].map(s => { const g = barco(0xd8443a, 1.8); g.rotation.y = Math.PI / 2; for (let i = 0; i < 3; i++) add(box(4.8, .24, 2, V_.viga, .03), g).position.set(0, 1 + i * .26, 0).constructor; AUTO.push(t => { const on = t > F(7) - .05 && t < fim(7); g.visible = on; if (on) { const x = 1 + clamp((t - tD0) / tDD) * 34; g.position.set(s * (x > 17.5 ? Math.min(x, 17.5) : x), 0, 0); } }); return g; });
const icaL = []; for (let i = 0; i < 8; i++) { const m = add(cil(.05, .05, 1, 0x24262a, 6)); m.geometry = G_CIL; icaL.push(m); }
AUTO.push(t => { let n = 0; XS.forEach(x => { const k = (t - tS(x)) / .62; if (k <= 0 || k >= 1 || n > 6) return; const y = YD - .2 + (1 - ease(k)) * dyS(x), L = YD - y; [-1, 1].forEach(s => { const m = icaL[n++]; m.visible = true; m.position.set(x, YD, s * ZD); m.rotation.x = Math.PI; m.scale.set(.05, L, .05); }); }); while (n < icaL.length) icaL[n++].visible = false; });

// asfalto, faixas e máquina --------------------------------------------------------------------------------------------------------------
const tAs0 = Math.min(T.asf, F(8) + dur(8) * .2), tAsD = Math.max(1.8, fim(8) - tAs0 - .5), LP = RW * 2, xAs = t => -RW + clamp((t - tAs0) / tAsD) * LP;
const asf = add(box(LP, .12, ZD * 2 - .5, 0x34363e, .02)); asf.position.set(0, YD + .02, 0); AUTO.push(t => { const k = clamp((t - tAs0) / tAsD); asf.visible = k > 0; asf.scale.x = Math.max(k, .001); asf.position.x = -RW + LP * k / 2; });
{ const L = []; for (let x = -RW + 1; x < RW; x += 2.2) L.push({ p: [x, YD + .1, 0], s: [1.2, .02, .16], t: tAs0 + (x + RW) / LP * tAsD + .25, d: .2, modo: 'pop', c: 0xf2d24a }); [-1, 1].forEach(s => { for (let x = -RW + .5; x < RW; x += 1) L.push({ p: [x, YD + .1, s * (ZD - .75)], s: [1.02, .02, .12], t: tAs0 + (x + RW) / LP * tAsD + .25, d: .15, modo: 'pop', c: 0xf4efe6 }); }); lote(G_CAIXA, M_L(), L); }
const maq = new THREE.Group(); add(maq); add(box(3.4, 1.3, 7.6, AMAR, .1), maq).position.y = 1; add(box(1.2, 1.1, 1.8, 0x24262a, .06), maq).position.set(-.7, 2.2, 1.6); add(cil(.13, .13, 1.3, 0x24262a, 8), maq).position.set(.9, 2.2, -2);[-2.4, 2.4].forEach(z => { const r_ = add(cil(.5, .5, .9, 0x1e2026, 14), maq); r_.rotation.x = Math.PI / 2; r_.position.set(.8, .5, z); }); add(box(.5, .4, 8.4, 0x56606e, .03), maq).position.set(-1.9, .2, 0);
AUTO.push(t => { const on = t > F(8) - .05 && t < fim(8) + .02; maq.visible = on; if (on) maq.position.set(xAs(t) + 1.9, YD + .02, 0); });
for (let q = tAs0; q < tAs0 + tAsD; q += .9) som(q, 'motor');

// mureta, postes e luz ------------------------------------------------------------------------------------------------------------------------
const tM0 = Math.min(T.mur, F(9) + dur(9) * .22), tMD = Math.max(1.5, fim(9) - tM0 - .3), ZM = ZD - .22, tMx = x => tM0 + (x + RW) / LP * tMD;
{ const L = [], Lb = []; [-1, 1].forEach(s => { for (let x = -RW + .2; x < RW; x += .6) { L.push({ p: [x, YD, s * ZM], s: [.13, 1.05, .13], t: tMx(x), d: .16, modo: 'cresce', c: 0xe9edf1 }); } for (let x = -RW + 1; x < RW; x += 2) { Lb.push({ p: [x, YD + 1.05, s * ZM], s: [2.02, .14, .2], t: tMx(x) + .05, d: .16, modo: 'pop', c: V_.viga }, { p: [x, YD + .1, s * ZM], s: [2.02, .28, .34], t: tMx(x), d: .16, modo: 'pop', c: CONC }); } }); lote(G_CAIXA0, M_L(), L); lote(G_CAIXA, M_L(), Lb); }
const LAMP = []; [-1, 1].forEach(s => { for (let x = -RW + 3; x < RW; x += 6) LAMP.push([x, s]); });
{ const L = []; LAMP.forEach(([x, s]) => { L.push({ p: [x, YD, s * (ZM + .05)], s: [.09, 4.2, .09], t: tMx(x) + .1, d: .25, modo: 'cresce', c: 0x56606e }, { p: [x, YD + 4.2, s * (ZM - .55)], s: [.09, .09, 1.2], t: tMx(x) + .3, d: .15, modo: 'pop', c: 0x56606e }); }); const l2 = L.filter(b => b.s[1] > 1), l3 = L.filter(b => b.s[1] < 1); lote(G_CAIXA0, M_L(), l2); lote(G_CAIXA, M_L(), l3); }
const lampMat = new THREE.MeshStandardMaterial({ color: 0xfff1c8, emissive: 0xffc861, emissiveIntensity: 0, roughness: .4 }), L_L = LAMP.map(([x, s]) => ({ p: [x, YD + 4.08, s * (ZM - 1.05)], s: [.22, .13, .22], t: tMx(x) + .35, d: .15, modo: 'pop' })); lote(new THREE.SphereGeometry(1, 12, 10), lampMat, L_L);
const pool = new THREE.InstancedMesh(new THREE.CircleGeometry(2.6, 24), new THREE.MeshBasicMaterial({ color: 0xffb860, transparent: true, opacity: 0, depthWrite: false, toneMapped: false, blending: THREE.AdditiveBlending, fog: false }), LAMP.length); pool.frustumCulled = false; add(pool); LAMP.forEach(([x, s], i) => { O.position.set(x, YD + .16, s * (ZM - 1.1)); O.rotation.set(-Math.PI / 2, 0, 0); O.scale.setScalar(1); O.updateMatrix(); pool.setMatrixAt(i, O.matrix); });
for (let q = tM0; q < tM0 + tMD; q += .32) som(q, 'toc');

// pedreiro: um posto por fala, sempre sobre a obra ------------------------------------------------------------------------------------------------
const h = boneco({ cabeca: 'bloco', camisa: 0x2fbf8f, calca: 0x2b3a67, sapato: 0xe9e4d8, cabelo: 0x3a2a1e, altura: 1.45 }); add(h); const r = h.r;
const cap = new THREE.Group(); r.cab.add(cap); add(box(.47, .15, .45, AMAR, .05), cap).position.y = .33; add(box(.32, .03, .2, AMAR, .012), cap).position.set(0, .28, .3);
const mart = new THREE.Group(); r.bd.k.add(mart); mart.position.y = -.38; add(box(.05, .36, .05, 0x7a4a26, .012), mart).position.y = -.1; add(box(.2, .1, .1, 0x5e6a78, .02), mart).position.y = -.3; mart.rotation.x = 1.4;
const posto = t => {
  if (t < F(2)) { const P_ = PO_[1].g.position; return { p: [XT + 7.6, 1, P_.z + 2.8], ry: -.5 + Math.sin(t) * .3, m: 1 }; }
  if (t < F(3)) return { p: [XT + 2.6 - Math.min(1, (t - F(2)) / 2.4) * 2.6, 3.8, 6.2], ry: .3, m: 1 };
  if (t < F(4)) { const y = yT(t) + .16; return { p: [XT + .4, y, zL(y) + 1.8], ry: Math.PI - .2 + Math.sin(t) * .3, m: 1 }; }
  if (t < F(5)) { return { p: [XA - .5, YD + .06, 12.5], ry: Math.PI - .2 + Math.sin(t) * .2, m: 1 }; }
  if (t < F(6)) return { p: [XT - 1.3, HT + .12, 0], ry: .9 + Math.sin(t * .7) * .3, m: 1 };
  if (t < F(7)) { const x = xCe(t); return { p: [x, yC(x) - 3.9, ZD + .7], ry: -1.2, m: 1 }; }
  if (t < F(8)) { const x = Math.min(1 + clamp((t - tD0) / tDD) * 34, 20) - 1.6; return { p: [x, YD + .05, 2.6], ry: 1.57, m: 1 }; }
  if (t < F(9)) { const x = xAs(t) - 1.5; return { p: [x, YD + .15, 3.1], ry: 1.57, m: 0, anda: 1 }; }
  return { p: [8 + clamp((t - T.mur) / dur(9) * 1.2) * 14, YD + .15, 3.3], ry: 1.57, m: 0, anda: t < fim(9) - .2 };
};
const pub = [[17, 3.4, 0xe8683f], [20, 3.6, 0x4285f4], [13.5, -3.6, 0xf4c95d], [15.5, -3.3, 0xd8443a]].map(([x, z, c]) => { const q = boneco({ cabeca: 'bloco', camisa: c, calca: 0x2b3a67, sapato: 0xe9e4d8, cabelo: 0x3a2a1e, altura: 1.35 }); add(q); q.position.set(x, YD + .15, z); q.rotation.y = -1.5; q.visible = false; return q; });
AUTO.push(t => {
  const f = t >= T_USO; h.visible = t >= F(1); if (!f) { const q = posto(t); h.position.set(...q.p); h.rotation.y = q.ry; if (q.anda) { r.anda(t); } else { r.anda(0, 0); r.respira(t); if (q.m) { const w = Math.sin(t * 9); r.bd.j.rotation.x = -2.35 + w * .42; r.bd.k.rotation.x = -.25; } } mart.visible = !q.anda; }
  else { h.position.set(18.5, YD + .15, 3.2); h.rotation.y = -1.5; r.anda(0, 0); mart.visible = false; const o = Math.sin(t * 6); r.be.j.rotation.x = -2.7 + o * .15; r.bd.j.rotation.x = -2.7 - o * .15; r.be.k.rotation.x = r.bd.k.rotation.x = 0; pub.forEach((p, i) => { p.visible = true; p.r.anda(0, 0); const o2 = Math.sin(t * 5 + i); p.r.be.j.rotation.x = -2.5 + o2 * .2; p.r.bd.j.rotation.x = -2.5 - o2 * .2; p.position.y = YD + .15 + Math.abs(Math.sin(t * 5 + i)) * .14; }); }
});
for (let q = F(1); q < fim(9); q += 1.15) som(q, 'toc');

// clipe final: anoitece, os postes acendem e os carros atravessam ----------------------------------------------------------------------------------------
const NC = 20, cores = [0xd83a3a, 0x3a7fd8, 0xf4efe6, 0xffb627, 0x2fbf8f, 0x8e5bd0, 0xe9edf1, 0xff7aa2], carros = []; for (let i = 0; i < NC; i++) { const g = carro(cores[i % cores.length], 1); add(g); const s = i % 2 ? 1 : -1; if (s < 0) g.rotation.y = Math.PI; g.visible = false; const fa = add(box(.08, .16, 1.1, 0xfff4c8, .02), g); fa.position.set(1.72, .6, 0); fa.material = new THREE.MeshBasicMaterial({ color: 0xfff4c8, toneMapped: false }); carros.push({ g, s, f: i / NC * 2 % 1, v: 15 + (i % 3) * 2.6 }); }
const ALC = 90, T_DUSK = T_USO + .2, barcao = barco(0xf4efe6, 2.2); barcao.visible = false;
const C_A = new THREE.Color(V_.ceu[0]), C_B = new THREE.Color('#3b3f7a'), C_F = new THREE.Color(V_.ceu[1]), C_F2 = new THREE.Color('#5a4f86'); let skyT = null;
const NFO = 260, fogo = new THREE.InstancedMesh(new THREE.SphereGeometry(.22, 6, 5), new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }), NFO); fogo.frustumCulled = false; add(fogo); for (let i = 0; i < NFO; i++) fogo.setColorAt(i, C.set([0xffd23f, 0xff5a5a, 0x7fd0ff, 0xffffff][(i >> 3) % 4]));
AUTO.push(t => {
  const f = t >= T_USO, g = ease((t - T_DUSK) / 1.5);
  sol.intensity = 2.7 - g * 1.9; sol.color.set(V_.sol).lerp(C.set(0xff9a5a), g); hemi.intensity = 1.25 - g * .65; scene.environmentIntensity = .3 - g * .12; lampMat.emissiveIntensity = g * 5; pool.material.opacity = g * .13; pool.visible = g > 0; if (g > 0) pool.instanceMatrix.needsUpdate = true;
  if (g > 0) { if (!skyT) skyT = { a: scene.background, c: new THREE.Color() }; scene.background = skyT.c.lerpColors(C_A, C_B, g); scene.fog.color.lerpColors(C_F, C_F2, g); } else if (skyT) { scene.background = skyT.a; scene.fog.color.copy(C_F); }
  carros.forEach(c => { c.g.visible = f; if (!f) return; const L_ = ALC * 2, x = -ALC + (((t - T_USO) * c.v + c.f * L_) % L_); c.g.position.set(c.s * -x, YD + .15, c.s * -1.75); });
  barcao.visible = f; if (f) { barcao.position.set(-5, 0, -60 + (t - T_USO) * 9); barcao.rotation.y = Math.PI / 2; }
  const on = t > T_USO + 1.2; fogo.visible = on; if (on) { for (let i = 0; i < NFO; i++) { const e = i >> 3 & 3, c = (t - T_USO - 1.2 - e * .55) % 2.2, a = i * 2.4, b = i * 1.7; if (c < 0 || c > 1.5) { O.scale.setScalar(0); } else { const cx = [62, 78, 70, 88][e], cy = [27, 31, 23, 29][e], rr = (1 - (1 - c / 1.5) ** 3) * 9; O.position.set(cx + Math.cos(a) * Math.sin(b) * rr, cy + Math.cos(b) * rr - c * c * 3, Math.sin(a) * Math.sin(b) * rr + [-5, 6, 3, -8][e]); O.scale.setScalar(2.4 * (1 - c / 1.5) + .2); } O.rotation.set(0, 0, 0); O.updateMatrix(); fogo.setMatrixAt(i, O.matrix); } fogo.instanceMatrix.needsUpdate = true; }
});

// câmera: [posição, alvo, corte seco?] -----------------------------------------------------------------------------------------------------------------------
const V = [
  [[33, 27, 52], [1, 8.5, 0]],
  [[36, 15, 38], [XT + .5, 6.5, 1], 1],
  [[35, 15, 33], [XT - 1, 3.4, 1], 1],
  [[-16, 23, 29], [XT, 18, 0]],
  [[XA + 20, 25, 34], [XA - 2, 12, 2], 1],
  [[86, 46, 62], [10, 22, 0], 1],
  [[30, 30, 46], [13, 19, 4], 1],
  [[46, 30, 50], [6, 7, 0]],
  [[-12, 22, 26], [-2, 8.5, 0], 1],
  [[-3, 20, 23], [15, 10, 1], 1],
];
const pontoA = (p, l, k) => p.map((v, j) => v + (l[j] - v) * k);
const K = []; V.forEach(([p, l, c], i) => { if (i) K.push({ ...K[K.length - 1], t: F(i) + .02 }); K.push({ t: F(i) + (i ? (c ? .05 : .7) : 0), p, l, f: 34 }); K.push({ t: fim(i), p: pontoA(p, l, .07), l, f: 34 }); });
K.push({ ...K[K.length - 1], t: F(LAST) - .02 }, { t: F(LAST) + .03, p: [70, 40, 66], l: [4, 20, 0], f: 34 }, { t: T_USO, p: pontoA([70, 40, 66], [4, 20, 0], .05), l: [4, 20, 0], f: 34 }, { t: T_USO + .03, p: [-15, 19, 2.6], l: [16, 15.4, -.4], f: 34 }, { t: D.total + 1, p: [-9, 18.5, 2.2], l: [16, 15.4, -.4], f: 34 });
for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01;

// rótulos e sons -----------------------------------------------------------------------------------------------------------------------------------------------
[['SEM FUNDAÇÃO', [-2, 21, 0], F(0) + .15, fim(0), 'ruim'], ['ESTACAS', [XT, 15, 0], T.est, fim(1), 'ouro'], ['BLOCO', [XT, 9.5, 0], T.blo, fim(2), 'ouro'], ['TORRES', [XT - 3, 29, 0], T.tor, fim(3), 'ouro'], ['ANCORAGEM', [XA + 1, 20.5, 2], T.anc, fim(4), 'ouro'], ['CABOS', [6, 44, 0], T.cab, fim(5), 'ouro'], ['TIRANTES', [8, 27, 0], T.tir, fim(6), 'ouro'], ['TABULEIRO', [-1, 20, 0], T.tab, fim(7), 'ouro'], ['ASFALTO', [-8, 15.5, 0], T.asf, fim(8), 'ouro'], ['MURETA', [15, 18, 0], T.mur, fim(9), 'ouro']].forEach(l => { rotulo(...l); if (l[4] === 'ouro') som(l[2], 'ding'); });
rotulo('PONTE PRONTA!', [540, 290], F(LAST) + .1, T_USO, 'grande').style.fontSize = '96px';
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); som(.15, 'crack'); som(.7, 'crack'); velhas.forEach((v, i) => { if (i % 2 === 0) som(v.t + 1.2, 'desaba'); }); som(T_D, 'impact'); som(T_D + .2, 'desaba'); som(F(LAST) + .1, 'ding'); som(T_USO + .1, 'whoosh');
for (let q = T_USO + .3; q < D.total; q += 1.1) som(q, 'motor'); for (let q = T_USO + 1.3; q < D.total; q += 1.1) som(q, 'impact');

window.CAPA_T = T_USO + 3.2;
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); AUTO.forEach(f => f(t)); });
