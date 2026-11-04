// Arranha-céu. Abre com uma torre de vidro sem estrutura entortando no vento e soltando vidros na rua, vista de um parque.
// No mesmo terreno a obra de verdade cresce: corte do solo com estacas até a rocha, bloco, núcleo, lajes, diagonais, pele de vidro,
// amortecedor de massa no topo, elevadores, para-raios na tempestade e, no fim, a cidade acende à noite. Medidas em metros.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, tex, camTo, iniciar, som, rotulo, fala, D } = K3;
const rnd = prng(73), F = fala, fim = i => F(i) + D.falas[i].dur, N = D.falas.length, AUTO = [], O = new THREE.Object3D(), C = new THREE.Color(), PI = Math.PI;
O.rotation.order = 'YXZ'; cam.far = 2600; cam.updateProjectionMatrix();
const nk = x => String(x).toLowerCase().normalize('NFD').replace(/[^a-z0-9]/g, '');
const tk = (w, i, f = .4) => { const k = nk(w), q = D.falas[i].words?.find(p => nk(p.w).startsWith(k)); return q ? q.start : F(i) + D.falas[i].dur * f; };
const nomeT = i => { const q = [...(D.falas[i].words ?? [])].reverse().find(p => /^(essa|esse|essas|esses)$/.test(nk(p.w))); return q ? q.start : fim(i) - 1.2; };
const rev = (t, a, b) => clamp((t - a) / (b - a));
const CI = {}; for (let i = 1; i < N - 1; i++) CI[i] = { a: F(i), e: tk('Então', i, .4), n: nomeT(i) };
const T_F = F(N - 1) - .02, T_MOE = tk('moeda', N - 1, .45), T_VER = tk('Verdade', N - 1, .85);
const B = (g, w, h, d, c, x, y, z, r = .02, o) => { const m = add(box(w, h, d, c, r, o), g); m.position.set(x, y, z); return m; };
const pc = (n, g, x, y, z, ry = 0, o, e = 1) => { const q = PC.novo(n, o); q.position.set(x, y, z); q.rotation.y = ry; if (e !== 1) q.scale.multiplyScalar(e); g.add(q); return q; };
const grupo = (a, b = 1e9, pai = scene) => { const g = new THREE.Group(); add(g, pai); AUTO.push(t => { g.visible = t >= a && t < b; }); return g; };
const pose = (I, i, x, y, z, ry, sx = 1, sy = sx, sz = sx, rx = 0, rz = 0) => { O.position.set(x, y, z); O.rotation.set(rx, ry, rz, 'YXZ'); O.scale.set(sx, sy, sz); O.updateMatrix(); I.setMatrixAt(i, O.matrix); };
const inst = (geo, m, n, g = scene, sombra = true) => { const I = new THREE.InstancedMesh(geo, m, n); I.frustumCulled = false; I.castShadow = sombra; I.receiveShadow = sombra; g.add(I); return I; };
const plano = (w, d, c, x, y, z, g = scene, o) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, d), typeof c === 'object' ? c : mat(c, { roughness: 1, ...o })), g); m.rotation.x = -PI / 2; m.position.set(x, y, z); m.receiveShadow = true; return m; };
const brilho = (c, o = {}) => new THREE.MeshBasicMaterial({ color: c, toneMapped: false, ...o });
const UP = new THREE.Vector3(0, 1, 0), VA = new THREE.Vector3(), VB = new THREE.Vector3();
const seg = (a, b, r, x = {}) => { VA.set(...a); VB.set(...b).sub(VA); const n = VB.length(), q = new THREE.Quaternion().setFromUnitVectors(UP, VB.clone().normalize()); return { p: a, q, s: [r, n, r], ...x }; };
const QY = a => new THREE.Quaternion().setFromAxisAngle(UP, a);
const face = (f, d, u, y) => { const a = f * PI / 2; return [Math.sin(a) * d + Math.cos(a) * u, y, Math.cos(a) * d - Math.sin(a) * u]; };
const lote = (geo, material, L, base = 0xffffff, pai = scene) => {
  const m = new THREE.InstancedMesh(geo, material, L.length); m.castShadow = m.receiveShadow = true; m.frustumCulled = false; add(m, pai);
  let fimT = -1; L.forEach((b, i) => { C.set(b.c ?? base); m.setColorAt(i, C); fimT = Math.max(fimT, b.t + b.d); }); fimT += .05; let u = -9;
  AUTO.push(t => { if (t > fimT && u > fimT) return; u = t; for (let i = 0; i < L.length; i++) { const b = L[i], k = (t - b.t) / b.d, s = b.s || [1, 1, 1]; O.position.set(b.p[0], b.p[1], b.p[2]); if (b.q) O.quaternion.copy(b.q); else O.quaternion.identity(); if (k <= 0) O.scale.setScalar(0); else if (b.modo === 'pop') { const e = Math.max(back(k), .001); O.scale.set(s[0] * e, s[1] * e, s[2] * e); } else if (b.modo === 'cresce') O.scale.set(s[0], s[1] * Math.max(ease(k), .001), s[2]); else { O.position.y += (1 - ease(k)) * (b.dy ?? 3); O.scale.set(s[0], s[1], s[2]); } O.updateMatrix(); m.setMatrixAt(i, O.matrix); } m.instanceMatrix.needsUpdate = true; });
  return m;
};
const G_CIL = new THREE.CylinderGeometry(1, 1, 1, 8).translate(0, .5, 0), G_CX = new THREE.BoxGeometry(1, 1, 1), G_CX0 = new THREE.BoxGeometry(1, 1, 1).translate(0, .5, 0), G_DESCE = new THREE.CylinderGeometry(1, 1, 1, 14).translate(0, -.5, 0);
const M_L = (o = {}) => new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .7, ...o });

// céu, luz e camadas de tela ---------------------------------------------------------------------------------------
const CEU = '#3f8fe0'; ceu(CEU, '#d6eefa'); const fundo = scene.background; scene.fog = new THREE.Fog(0xcfe6f2, 320, 1300);
const sol = luzes(0xfff2de, 0xd8ecff, 0x8fb070, 2.6, 150); sol.position.set(150, 300, 190); sol.target.position.set(0, 30, 0); scene.add(sol.target); sol.shadow.camera.far = 900; sol.shadow.camera.updateProjectionMatrix(); scene.environmentIntensity = .32;
const hemi = []; scene.traverse(o => { if (o.isHemisphereLight) { hemi.push(o); o.groundColor.setHex(0xb8b09a); } });
const frenteL = add(new THREE.DirectionalLight(0xfff1e0, .55)); frenteL.position.set(-60, 120, 260);
const camada = (c, m = '') => { const e = document.createElement('div'); e.style.cssText = `position:absolute;inset:0;background:${c};opacity:0;${m}`; document.getElementById('hud').prepend(e); return e; };
const flash = camada('#fff8e0'), trevas = camada('#0b1020');

// medidas ----------------------------------------------------------------------------------------------------------
const HA = 3.5, NAND = 30, YC = NAND * HA, NCR = 3, H_T = YC + NCR * HA, W2 = 12, NU = 5, PIT = 17, FUN = 10, YB = -7, ROC = -30, P = 70, BQ = 28;
const AS = 0x34373e, CAL = 0xcfcac0, GR = 0x4fae58, CONC = 0xc9c7c0, CONC2 = 0xb9b6ae, FERRO = 0xb4582a, AMAR = 0xffc21a, ACO = 0xd8452e, VID = 0x5fa8d8;
const CAM = [0xd8352f, 0x2f7fd6, 0xffc21a, 0xf4f4f2, 0x3fa45a, 0xe8683f, 0x8a5bc4, 0x24303c], PELE = [0xdca77f, 0xb5805a, 0x8a5a3c, 0xe8c4a0];
const gente = (g, x, z, ry, o = {}) => pc('personagem', g, x, o.y ?? 0, z, ry, { capacete: false, cinto: false, camisa: CAM[Math.floor(rnd() * 8)], camisa2: 0x333844, calca: [0x2b3a67, 0x3a3f4a, 0x6b5a45][Math.floor(rnd() * 3)], cabelo: [0x3a2a1e, 0x15110e, 0x8a5a33][Math.floor(rnd() * 3)], pele: PELE[Math.floor(rnd() * 4)], ...o });

// chão da cidade, com o buraco do terreno ----------------------------------------------------------------------------
const chapa = (L, h, c, y) => { const s = new THREE.Shape(); s.moveTo(-L, -L); s.lineTo(L, -L); s.lineTo(L, L); s.lineTo(-L, L); s.closePath(); const p = new THREE.Path(); p.moveTo(-h, -h); p.lineTo(-h, h); p.lineTo(h, h); p.lineTo(h, -h); p.closePath(); s.holes.push(p); const m = add(new THREE.Mesh(new THREE.ShapeGeometry(s).rotateX(-PI / 2), mat(c, { roughness: 1 }))); m.position.y = y; m.receiveShadow = true; return m; };
const asfalto = chapa(262, PIT, AS, 0), grama = chapa(4000, 258, GR, -.06);
{ const ST = [-175, -105, -35, 35, 105, 175], cruz = p => ST.some(s => Math.abs(p - s) < 8), I = inst(new THREE.BoxGeometry(3, .02, .22), mat(0xf2d24a), 6 * 80 * 2, scene, false); let n = 0; for (const s of ST) for (let k = -40; k < 40; k++) { const p = k * 6.4 + 3; if (cruz(p)) continue; pose(I, n++, p, .03, s, 0); pose(I, n++, s, .03, p, PI / 2); } I.count = n;
  const Z = inst(new THREE.BoxGeometry(.9, .02, 4.6), mat(0xf4efe6), 80, scene, false); let m = 0; [[0, 35], [0, -35], [35, 0], [-35, 0]].forEach(([x, z]) => { for (let k = 0; k < 8; k++) { if (z) pose(Z, m++, -7 + k * 2, .035, z, 0); else pose(Z, m++, x, .035, -7 + k * 2, PI / 2); } }); Z.count = m; }
// morros ao longe
{ const MO = inst(new THREE.IcosahedronGeometry(1, 2), mat(0x5aa060, { flatShading: true, roughness: 1 }), 46, scene, false); for (let i = 0; i < 46; i++) { const a = i / 46 * PI * 2, r = 620 + rnd() * 160; pose(MO, i, Math.cos(a) * r, -10, Math.sin(a) * r, rnd() * 6, 90 + rnd() * 70, 40 + rnd() * 55, 70 + rnd() * 40); MO.setColorAt(i, C.set(0x5aa060).offsetHSL((rnd() - .5) * .04, 0, (rnd() - .5) * .1)); } MO.instanceColor.needsUpdate = true; }

// quarteirões e prédios com janelas que acendem ------------------------------------------------------------------------
const janelas = claro => tex(64, 64, (g, w, h) => { g.fillStyle = claro ? '#000' : '#fff'; g.fillRect(0, 0, w, h); for (let a = 0; a < 2; a++) for (let b = 0; b < 2; b++) { if (claro && (a * 3 + b * 5 + 1) % 3 === 0) continue; g.fillStyle = claro ? '#ffd98a' : '#6d8fa8'; g.fillRect(6 + a * 30, 8 + b * 30, 22, 18); } });
const mJ = janelas(false), mL = janelas(true), MATS = [];
const edif = (x, z, w, d, a, c) => { const t1 = mJ.clone(), t2 = mL.clone(); t1.repeat.set(Math.max(1, Math.round(w / 6)), Math.max(1, Math.round(a / 7))); t2.repeat.copy(t1.repeat); t1.needsUpdate = t2.needsUpdate = true; const ma = new THREE.MeshStandardMaterial({ color: c, map: t1, roughness: .55, emissive: 0xffffff, emissiveMap: t2, emissiveIntensity: 0 }), m = add(sh(new THREE.Mesh(new THREE.BoxGeometry(w, a, d), [ma, ma, mat(c), mat(c), ma, ma]))); m.position.set(x, a / 2 + .22, z); MATS.push(ma); add(box(w + .6, .7, d + .6, new THREE.Color(c).offsetHSL(0, 0, -.1).getHex(), .05)).position.set(x, a + .5, z); if (a > 24) { add(box(w * .35, 3, d * .35, 0xc9c7bf, .06)).position.set(x, a + 2.2, z); add(cil(1.3, 1.3, 2.4, 0x3a7fd8, 12)).position.set(x + w * .26, a + 2, z + d * .26); } };
const CE = [0xe9c9a0, 0xa9c9e8, 0xf2b8c6, 0xd8d0e8, 0xd6e6c0, 0xf0dba0, 0xbfe0ef, 0xeab0a6, 0xe4dfd2, 0x9fb9d8];
const ARV = [];
for (let a = -3; a <= 3; a++) for (let b = -3; b <= 3; b++) { const x = a * P, z = b * P, r = Math.max(Math.abs(a), Math.abs(b)); if (!a && !b) continue;
  add(box(BQ * 2, .22, BQ * 2, 0xd9d7d0, .03)).position.set(x, .11, z);
  if (!a && b === 1) continue;
  const alto = () => r === 1 ? 10 + rnd() * 20 : r === 2 ? 18 + rnd() * 34 : 28 + rnd() * 52, lay = Math.abs(a * 3 + b * 5) % 3;
  if (lay === 0) edif(x, z, 40, 40, alto(), CE[(a + b * 3 + 40) % 10]); else if (lay === 1) { edif(x - 11, z, 18, 44, alto(), CE[(a + b + 40) % 10]); edif(x + 11, z, 18, 44, alto(), CE[(a * 2 + b + 43) % 10]); } else [[-11, -11], [11, -11], [-11, 11], [11, 11]].forEach(([u, v], n) => edif(x + u, z + v, 18, 18, alto(), CE[(a + b + n + 40) % 10]));
  if (r === 1) for (let k = 0; k < 6; k++) [[-1, 0], [1, 0], [0, -1], [0, 1]].forEach(([u, v]) => ARV.push([x + (u ? u * 26 : -22 + k * 8.8), z + (v ? v * 26 : -22 + k * 8.8), 1])); }
// parque em frente ao terreno, com fonte, bancos e parquinho
{ const g = scene, x0 = 0, z0 = P; plano(BQ * 2 - 2, BQ * 2 - 2, GR, x0, .235, z0); plano(4, BQ * 2 - 2, 0xe8dcc0, x0, .24, z0); plano(BQ * 2 - 2, 4, 0xe8dcc0, x0, .24, z0); pc('rua_chafariz', g, -12, .22, 58, 0); pc('rua_parquinho', g, 13, .22, 86, PI); [[-6, 52, 0], [6, 52, 0], [-18, 72, PI / 2], [18, 60, -PI / 2]].forEach(([x, z, r]) => pc('rua_banco_praca', g, x, .22, z, r));
  for (let i = 0; i < 46; i++) { const x = -25 + rnd() * 50, z = 45 + rnd() * 50; if (Math.abs(x) < 4 || Math.abs(z - 70) < 4 || (x > -9 && x < 25 && z > 44)) continue; ARV.push([x, z, 1.1 + rnd() * .6]); } }
// árvores instanciadas, que o vento entorta
const NARV = ARV.length, TRO = inst(new THREE.CylinderGeometry(.22, .32, 1, 7).translate(0, .5, 0), mat(0x6b4a2c), NARV), COP = inst(new THREE.IcosahedronGeometry(1, 0), mat(0xffffff, { flatShading: true }), NARV * 2);
ARV.forEach((q, i) => { COP.setColorAt(i * 2, C.set([0x2e8f3e, 0x3aa84a, 0x237a35][i % 3])); COP.setColorAt(i * 2 + 1, C.set([0x3aa84a, 0x2e8f3e, 0x46b254][i % 3])); }); COP.instanceColor.needsUpdate = true;
const ventoArv = t => t < fim(0) + .1 ? .26 + Math.sin(t * 3.3) * .1 : 0;
const arvores = t => { const v = ventoArv(t); ARV.forEach(([x, z, e], i) => { const s = e * 1.7, lean = v * (1 + Math.sin(t * 6 + i) * .25); pose(TRO, i, x, .22, z, 0, s * .9, s * 2.4, s * .9, 0, -lean); pose(COP, i * 2, x + Math.sin(lean) * s * 2.6, .22 + s * 2.8, z, i, s * 1.5, s * 1.25, s * 1.5, 0, -lean); pose(COP, i * 2 + 1, x + Math.sin(lean) * s * 3.4 + .8, .22 + s * 3.5, z + .5, i * 2, s * 1.05, s * .9, s * 1.05, 0, -lean); }); TRO.instanceMatrix.needsUpdate = COP.instanceMatrix.needsUpdate = true; };
let ultV = -1; AUTO.push(t => { const v = ventoArv(t); if (v === 0 && ultV === 0) return; ultV = v; arvores(t); });
// postes de luz nas ruas em volta do terreno
const LUZP = []; for (let k = -3; k <= 3; k++) { if (!k) continue; [[k * 12, 29.2, PI], [k * 12, -29.2, 0], [29.2, k * 12, -PI / 2], [-29.2, k * 12, PI / 2]].forEach(([x, z, r]) => { pc('rua_poste_luz', scene, x, .22, z, r); LUZP.push([x - Math.sin(r) * 1.6, 7.7, z - Math.cos(r) * 1.6]); }); }

// carros nas avenidas ----------------------------------------------------------------------------------------------------
const NCA = 64, CB = inst(new THREE.BoxGeometry(4.2, .8, 1.8).translate(0, .62, 0), mat(0xffffff, { roughness: .35, metalness: .2 }), NCA), CT = inst(new THREE.BoxGeometry(2.2, .62, 1.62).translate(-.2, 1.3, 0), mat(0x2a3440, { roughness: .15, metalness: .5 }), NCA), RO = inst(new THREE.CylinderGeometry(.34, .34, 1.9, 12).rotateX(PI / 2), mat(0x1b1d22), NCA * 2, scene, false);
const FAR = inst(new THREE.BoxGeometry(.06, .16, 1.4), brilho(0xfff4c8), NCA, scene, false), LAN = inst(new THREE.BoxGeometry(.06, .16, 1.4), brilho(0xff3020), NCA, scene, false);
const CAR = []; for (let i = 0; i < NCA; i++) { const eixo = i % 2, l = i % 4 < 2 ? 1 : -1, via = [35, -35, 105, -105][(i >> 2) % 4]; CAR.push({ eixo, l, faixa: l * 2.6, via, f: rnd(), v: 8 + rnd() * 5 }); CB.setColorAt(i, C.set([0xd8352f, 0x2f7fd6, 0xf4f4f2, 0xffc21a, 0x3fa45a, 0x24303c, 0xb9bcc2, 0xe8683f][i % 8])); } CB.instanceColor.needsUpdate = true;
AUTO.push(t => { CAR.forEach((c, i) => { const L = 500, s = -250 + ((c.f * L + t * c.v * (t < fim(0) ? .25 : 1)) % L), d = s * c.l; let x, z, ry; if (c.eixo) { x = c.via + c.faixa; z = d; ry = c.l > 0 ? -PI / 2 : PI / 2; } else { x = d; z = c.via + c.faixa; ry = c.l > 0 ? 0 : PI; } if (Math.abs(x) < 30 && Math.abs(z) < 30) z += 80; pose(CB, i, x, 0, z, ry); pose(CT, i, x, 0, z, ry); const cx = Math.cos(ry), sz = -Math.sin(ry); pose(RO, i * 2, x + cx * 1.35, .34, z + sz * 1.35, ry); pose(RO, i * 2 + 1, x - cx * 1.35, .34, z - sz * 1.35, ry); pose(FAR, i, x + cx * 2.12, .75, z + sz * 2.12, ry); pose(LAN, i, x - cx * 2.12, .75, z - sz * 2.12, ry); }); CB.instanceMatrix.needsUpdate = CT.instanceMatrix.needsUpdate = RO.instanceMatrix.needsUpdate = FAR.instanceMatrix.needsUpdate = LAN.instanceMatrix.needsUpdate = true; });

// gente nas calçadas -----------------------------------------------------------------------------------------------------
const povo = n => { const c = inst(new THREE.BoxGeometry(.46, .62, .28), mat(0xffffff, { roughness: .8 }), n, scene, false), h = inst(new THREE.SphereGeometry(.15, 10, 8), mat(0xffffff, { roughness: .7 }), n, scene, false), p = inst(new THREE.BoxGeometry(.36, .8, .22), mat(0x2f3644), n, scene, false); for (let i = 0; i < n; i++) { c.setColorAt(i, C.set(CAM[Math.floor(rnd() * 8)])); h.setColorAt(i, C.set(PELE[Math.floor(rnd() * 4)])); p.setColorAt(i, C.set([0x2b3a67, 0x3a3f4a, 0x6b5a45, 0x24303c][Math.floor(rnd() * 4)])); } c.instanceColor.needsUpdate = h.instanceColor.needsUpdate = p.instanceColor.needsUpdate = true; return { put(i, x, y, z, ry, on) { const s = on ? 1 : .001; pose(p, i, x, y + .4, z, ry, s); pose(c, i, x, y + 1.11, z, ry, s); pose(h, i, x, y + 1.6, z, ry, s); }, up() { c.instanceMatrix.needsUpdate = h.instanceMatrix.needsUpdate = p.instanceMatrix.needsUpdate = true; } }; };
const NPV = 260, PV = povo(NPV), pv = Array.from({ length: NPV }, (_, i) => ({ h: i % 3 ? 43.6 + (rnd() - .5) * 1.4 : 26.6 + (rnd() - .5) * .9, u: rnd() * 4, s: (rnd() > .5 ? 1 : -1) * (.012 + rnd() * .006), ph: rnd() * 6 }));
const quad = (h, u) => { u = ((u % 4) + 4) % 4; const k = Math.floor(u), f = (u - k) * 2 - 1; return [[f * h, h, 0], [h, -f * h, PI / 2], [-f * h, -h, PI], [-h, f * h, -PI / 2]][k]; };
AUTO.push(t => { const on = t >= F(1) - .02; pv.forEach((q, i) => { const [x, z, r] = quad(q.h, q.u + q.s * t * (q.h < 30 ? 1.6 : 1)); const cr = (Math.abs(x) < 2.5 || Math.abs(z) < 2.5) && q.h > 40; PV.put(i, x, .22 + Math.abs(Math.sin(t * 7 + q.ph)) * .03, z, r + (q.s > 0 ? PI / 2 : -PI / 2), on && !cr); }); PV.up(); });

// terreno: praça (abertura e fim), tapume, terra, cava ------------------------------------------------------------------
const PRACA = grupo(0, F(1) - .02); const PRF = grupo(T_F); [PRACA, PRF].forEach(g => { B(g, 50, .22, 50, 0xe2ddd2, 0, .11, 0, .02); for (let i = 0; i < 12; i++) B(g, .08, .01, 50, 0xcac4b8, -22 + i * 4, .225, 0, .002); [[-18, 18], [18, 18], [-18, -18], [18, -18]].forEach(([x, z]) => pc('rua_floreira', g, x, .22, z, 0)); [[-8, 20, 0], [8, 20, 0]].forEach(([x, z, r]) => pc('rua_banco_praca', g, x, .22, z, r)); });
{ const g = grupo(F(1) - .02, T_F); [[0, 26.5, 50, 3], [0, -26.5, 50, 3], [26.5, 0, 3, 56], [-26.5, 0, 3, 56]].forEach(([x, z, w, d]) => B(g, w, .22, d, 0xd9d7d0, x, .11, z, .02)); [[0, 21, 50, 8], [0, -21, 50, 8], [21, 0, 8, 34], [-21, 0, 8, 34]].forEach(([x, z, w, d]) => plano(w, d, 0x9a7a56, x, .02, z, g)); }
const TAP = grupo(F(1) - .02, T_F), TAPF = grupo(F(1) - .02, T_F);
{ const L = [], Lf = []; for (let f = 0; f < 4; f++) for (let k = 0; k < 49; k++) { const u = -24.5 + k + .5, [x, , z] = face(f, 24.6, u, 0); (f === 0 ? Lf : L).push({ p: [x, 0, z], q: QY(f * PI / 2), s: [.98, 2.4, .1], t: -1, d: .01, modo: 'cresce', c: k % 4 < 2 ? 0xff8a3a : 0xf4efe6 }); } lote(G_CX0, M_L(), L, 0xffffff, TAP); lote(G_CX0, M_L(), Lf, 0xffffff, TAPF); }
// cava com estacas-prancha
const CAVA = grupo(F(1) - .02, CI[3].e + .1); plano(PIT * 2, PIT * 2, 0x7a5a3c, 0, -FUN, 0, CAVA);
const PAREDEF = grupo(F(1) - .02, CI[3].e + .1);
{ const L = [], Lf = []; [[0, 1], [1, 0], [0, -1], [-1, 0]].forEach(([a, b], i) => { for (let k = 0; k < 34; k++) { const u = -PIT + k + .5; (i === 0 ? Lf : L).push({ p: [a ? a * PIT : u, -FUN, b ? b * PIT : u], s: [a ? .12 : .96, FUN, a ? .96 : .12], t: -1, d: .01, modo: 'cresce', c: k % 2 ? 0x8a97a5 : 0x75828f }); } }); lote(G_CX0, M_L({ metalness: .4 }), L, 0xffffff, CAVA); lote(G_CX0, M_L({ metalness: .4 }), Lf, 0xffffff, PAREDEF); }
// corte do solo, visto de lado: camadas de terra e a rocha lá embaixo
{ const g = grupo(F(1) - .02, CI[3].e + .1), ZF = 13; [[-FUN, -20, 0xa8703f], [-20, ROC, 0x8f6a45], [ROC, -60, 0x6d7078]].forEach(([y0, y1, c]) => B(g, 220, y0 - y1, 1, c, 0, (y0 + y1) / 2, ZF - .5, .01)); [[0, -2.5, 0x6b4a2e], [-2.5, -FUN, 0xa8703f]].forEach(([y0, y1, c]) => [-1, 1].forEach(s => B(g, 100, y0 - y1, 1, c, s * (PIT + 50), (y0 + y1) / 2 - .03, PIT - .5, .01)));
  const R = inst(new THREE.IcosahedronGeometry(1, 0), mat(0x5a5e66, { flatShading: true }), 120, g, false); for (let i = 0; i < 120; i++) { pose(R, i, -60 + rnd() * 120, ROC - 1.5 - rnd() * 22, ZF + .1, rnd() * 6, .5 + rnd() * 1.3, .4 + rnd(), .3); R.setColorAt(i, C.set(0x5a5e66).offsetHSL(0, 0, (rnd() - .5) * .12)); } R.instanceColor.needsUpdate = true;
  const S = inst(new THREE.IcosahedronGeometry(1, 0), mat(0x7a5634, { flatShading: true }), 160, g, false); for (let i = 0; i < 160; i++) pose(S, i, -60 + rnd() * 120, -FUN - .5 - rnd() * 19, ZF + .05, rnd() * 6, .15 + rnd() * .3, .1 + rnd() * .2, .1);
  B(g, 220, .3, 1.05, 0x4f5258, 0, ROC, ZF - .5, .01); }

// abertura: torre fina, sem estrutura, entortando e soltando vidros ------------------------------------------------------
const NCH = 13, HCH = 7, LR = 12, RUIM = grupo(0, F(1) - .02), chain = [];
{ const tv = tex(64, 64, (g, w, h) => { g.fillStyle = '#7fb3d6'; g.fillRect(0, 0, w, h); g.fillStyle = '#a9d2ea'; g.fillRect(4, 4, 26, 26); g.fillRect(34, 34, 26, 26); g.fillStyle = '#6aa0c6'; g.fillRect(34, 4, 26, 26); g.fillRect(4, 34, 26, 26); g.fillStyle = '#3a4a5a'; g.fillRect(0, 0, w, 3); g.fillRect(0, 31, w, 3); g.fillRect(0, 0, 3, h); g.fillRect(31, 0, 3, h); }, 2, 2);
  const ma = new THREE.MeshStandardMaterial({ map: tv, roughness: .12, metalness: .45 }); let pai = RUIM;
  for (let i = 0; i < NCH; i++) { const g = new THREE.Group(); g.position.y = i ? HCH : .22; pai.add(g); const m = add(sh(new THREE.Mesh(new THREE.BoxGeometry(LR, HCH * .99, LR), ma)), g); m.position.y = HCH / 2; add(box(LR + .3, .35, LR + .3, 0xdad6cc, .03), g).position.y = HCH; chain.push(g); pai = g; }
  add(box(LR - 3, 3, LR - 3, 0xdad6cc, .05), pai).position.y = HCH + 1.5; add(cil(.15, .15, 8, 0x8d949c, 8), pai).position.set(2, HCH + 6, 2);
  B(RUIM, LR + 4, 4.5, LR + 4, 0xf0ece4, 0, 2.4, 0, .05); B(RUIM, 6, 3.4, .1, 0x2a3440, 0, 2, LR / 2 + 2.05, .01, { roughness: .1, metalness: .5 }); }
const kR = t => .0155 * Math.sin(t * 1.75 + 1.15) * (1 + .15 * Math.min(t, 3));
const angR = (t, i) => { let a = 0; for (let j = 0; j <= i; j++) a += kR(t) * (1 + j * .1); return a; };
const posR = (y, t) => { let x = 0, yy = .22, a = 0; for (let j = 0; j < NCH; j++) { const an = a + kR(t) * (1 + j * .1); if (y <= (j + 1) * HCH) { const f = (y - j * HCH) / HCH; return [x - Math.sin(an) * HCH * f, yy + Math.cos(an) * HCH * f, an]; } x -= Math.sin(an) * HCH; yy += Math.cos(an) * HCH; a = an; } return [x, yy, a]; };
const NVD = 320, cacos = inst(new THREE.BoxGeometry(1.45, 1.6, .05), new THREE.MeshStandardMaterial({ color: 0xa9d8f0, roughness: .08, metalness: .55 }), NVD, RUIM, false), CB2 = [];
for (let i = 0; i < NVD; i++) { const fc = Math.floor(rnd() * 3), y = 18 + rnd() * 70; CB2.push({ fc, y, u: -5.2 + rnd() * 10.4, t: -2.6 + rnd() * (fim(0) + 2.2), vx: (rnd() - .4) * 5, vz: 2 + rnd() * 5, r: rnd() * 6, sx: (rnd() - .5) * 8, sz: (rnd() - .2) * 6 }); }
const NST = 150, riscos = inst(new THREE.BoxGeometry(7, .07, .07), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: .5 }), NST, scene, false), RS = Array.from({ length: NST }, () => [rnd(), 2 + rnd() * 100, -40 + rnd() * 110, .7 + rnd() * .7]);
const vento = t => (t < fim(0) + .05) || (t > tk('vento', 4) - .3 && t < fim(4)) || (t > F(6) && t < fim(6));
AUTO.push(t => { const on = t < F(1) - .02; cacos.visible = on;
  const vv = vento(t); riscos.visible = vv; if (vv) { for (let i = 0; i < NST; i++) { const [u, y, z, v] = RS[i]; pose(riscos, i, -90 + ((u * 180 + t * 70 * v) % 180), y, z, 0, v, 1, 1); } riscos.instanceMatrix.needsUpdate = true; }
  if (!on) return; chain.forEach((g, i) => { g.rotation.z = kR(t) * (1 + i * .1); });
  for (let i = 0; i < NVD; i++) { const b = CB2[i], q = t - b.t; if (q <= 0) { pose(cacos, i, 0, -50, 0, 0, .001); continue; } const [x0, y0, an] = posR(b.y, b.t), fall = 4.9 * q * q; const ox = b.fc === 1 ? x0 + LR / 2 + .1 : x0 + b.u, oz = b.fc === 1 ? b.u : LR / 2 + .1; let y = y0 - fall, x = ox + b.vx * q, z = oz + b.vz * q;
    if (y <= .3) { const tq = Math.sqrt(Math.max(y0 - .3, 0) / 4.9); x = ox + b.vx * tq + b.sx * .3; z = oz + b.vz * tq + b.sz * .3; pose(cacos, i, x, .26, z, b.r, .45 + (i % 3) * .12, .45, 1, -PI / 2); } else pose(cacos, i, x, y, z, b.r + q * 4, .9, .9, 1, q * 5, q * 3 + an); }
  cacos.instanceMatrix.needsUpdate = true; });
// quem estava na praça corre para longe
const CORRE = [[-6, 30, -1, 3.6], [-2, 32, -1, 3.2], [3, 31.5, 1, 3.4], [7, 30.5, 1, 3.8], [-9, 33, -1, 3], [10, 32.5, 1, 3.1], [0, 41, 1, 2.6], [-4, 40.4, -1, 2.8]].map(([x, z, s, v], i) => { const q = gente(RUIM, x, z, s > 0 ? PI / 2 : -PI / 2, { escala: 1 }); AUTO.push(t => { if (!RUIM.visible) return; q.position.set(x + s * v * t, .22 + Math.abs(Math.sin(t * 9 + i)) * .07, z + Math.sin(t + i) * .3); q.r.anda(t * 1.5 + i, 1.2); if (i % 2) { q.r.be.j.rotation.x = -2.7; q.r.bd.j.rotation.x = -2.5; } q.r.cab.rotation.y = s * .9; }); return q; });

// fundação: fantasma afundando, estacas até a rocha, ferro e concreto ----------------------------------------------------
const T_EST = tk('estacas', 1), T_ROC = tk('rocha', 1), T_BLO = tk('bloco', 1);
const FANT = new THREE.MeshStandardMaterial({ color: 0xff4a3a, transparent: true, opacity: .32, depthWrite: false, roughness: .6 });
const FANTS = new THREE.MeshStandardMaterial({ color: 0xff3a2a, transparent: true, opacity: .55, depthWrite: false, roughness: .6 });
{ const g = grupo(CI[1].a, CI[1].e + .25); const m = add(new THREE.Mesh(new THREE.BoxGeometry(22, 40, 1), FANTS), g); const ar = add(new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(22, 40, 1)), new THREE.LineBasicMaterial({ color: 0xff2010 })), g);
  const RACH = inst(new THREE.BoxGeometry(.25, 1, .1), mat(0x3a2414), 18, g, false); for (let i = 0; i < 18; i++) pose(RACH, i, (i % 2 ? 1 : -1) * (11.5 + (i >> 1) * .5), -FUN - 1 - (i % 5), 13.7, 0, 1, 2 + (i % 4), 1, 0, (i % 2 ? .4 : -.4) + (i % 3) * .2);
  AUTO.push(t => { if (!g.visible) return; const k = ease(rev(t, CI[1].a + .1, CI[1].e)), y = -FUN + 20 - k * 7; [m, ar].forEach(o => { o.position.set(k * 1.2, y, 13.9); o.rotation.z = -k * .06; }); RACH.visible = k > .3; FANTS.opacity = .55 * (1 - rev(t, CI[1].e, CI[1].e + .25)); }); }
const XE = [-14, -9.33, -4.67, 0, 4.67, 9.33, 14], tE0 = Math.max(CI[1].e + .1, T_EST - .15), tE1 = Math.max(tE0 + 2, T_BLO - .2), dE = (tE1 - tE0) / 7;
{ const L = [], Lc = []; XE.forEach((x, a) => XE.forEach((z, b) => { const t0 = b === 6 ? tE0 + a * dE + dE * .45 : tE0 + ((a * 7 + b) / 49) * (tE1 - tE0); if (b === 6) L.push({ p: [x, -FUN, 14], s: [.55, -ROC + FUN + 1.2, .55], t: t0, d: dE * .5, modo: 'cresce', c: (a % 2) ? CONC : CONC2 }); Lc.push({ p: [x, -FUN + .08, z], s: [1.3, .16, 1.3], t: t0 + .2, d: .2, modo: 'pop', c: 0xd8d6cf }); })); lote(G_DESCE, M_L(), L, 0xffffff, scene); lote(new THREE.CylinderGeometry(1, 1, 1, 16), M_L(), Lc, 0xffffff, scene); XE.forEach((x, a) => som(tE0 + a * dE + dE * .45, 'impact')); }
// trado girando: desce até a rocha antes de cada estaca da frente
const TRADO = new THREE.Group(); add(TRADO); { add(cil(.18, .18, 1, 0x8d949c, 10, { metalness: .6 }), TRADO).geometry.translate(0, -.5, 0); }
const helices = []; for (let i = 0; i < 26; i++) { const m = add(new THREE.Mesh(new THREE.TorusGeometry(.42, .07, 6, 14).rotateX(PI / 2 + .25), mat(0x6d747e, { metalness: .6 })), TRADO); helices.push(m); }
const PERF = pc('obra_perfuratriz', scene, 0, -FUN, 9.4, 0);
AUTO.push(t => { const on = t > tE0 - .3 && t < tE1 + .3; TRADO.visible = PERF.visible = on || (t > F(1) - .02 && t < CI[3].a); if (!TRADO.visible) return; const k = clamp((t - tE0) / (tE1 - tE0)) * 7, i = Math.min(6, Math.floor(k)), f = k - i, x = XE[i]; PERF.position.x = x - .4; const dep = on ? (f < .45 ? ease(f / .45) : 1 - ease((f - .45) / .4)) * (-ROC + FUN + 1) : 0; TRADO.visible = on && dep > .05; TRADO.position.set(x, -FUN + 1.6, 14); TRADO.children[0].scale.y = dep + 1.6; helices.forEach((h, j) => { h.position.y = -j * .9 - .3; h.visible = j * .9 < dep + 1.2; h.rotation.y = t * 9; }); if (PERF.broca) PERF.broca.rotation.y = t * 9; });
// ferro do bloco e concreto
const tB0 = T_BLO + .05, tB1 = Math.max(tB0 + 1.8, CI[1].n - .05), tCo = tB0 + (tB1 - tB0) * .45;
{ const L = []; for (let l = 0; l < 2; l++) for (let i = 0; i < 34; i++) { const u = -16.5 + i, y = -FUN + .7 + l * 1.6, q = tB0 + (i / 34) * (tCo - tB0) * .85; L.push({ ...seg([u, y, -16.6], [u, y, 16.6], .05), t: q, d: .15, modo: 'pop' }, { ...seg([-16.6, y + .08, u], [16.6, y + .08, u], .05), t: q + .03, d: .15, modo: 'pop' }); } for (let i = -4; i <= 4; i++) for (let k = -4; k <= 4; k++) if (Math.abs(i) === 4 || Math.abs(k) === 4) L.push({ ...seg([i * 1.2, -FUN + .3, k * 1.2], [i * 1.2, YB + 2.2, k * 1.2], .07), t: tCo - .3, d: .25, modo: 'cresce' }); lote(G_CIL, M_L({ metalness: .5, roughness: .45 }), L, FERRO); }
const BLOCO = add(box(PIT * 2 - .1, YB + FUN, PIT * 2 - .1, CONC, .02)); AUTO.push(t => { const k = ease(rev(t, tCo, tB1)); BLOCO.visible = k > 0 && t < CI[3].e + .1; BLOCO.scale.y = Math.max(k, .01); BLOCO.position.y = -FUN + (YB + FUN) * k / 2; });
const OBRA1 = grupo(F(1) - .02, CI[3].e + .1);
const BOMBA = pc('obra_bomba_concreto', OBRA1, 8, 0, 34.5, PI / 2), CRV = new THREE.CatmullRomCurve3([[8, 4.2, 34.5], [6, 20, 26], [3, 21, 12], [1, 14, 4], [0, YB + 3, 2]].map(q => new THREE.Vector3(...q)));
const MANG = add(sh(new THREE.Mesh(new THREE.TubeGeometry(CRV, 60, .28, 8), mat(0xd8352f, { roughness: .5 }))), OBRA1); MANG.visible = false; AUTO.push(t => { MANG.visible = t > tB0 - .2 && t < fim(1) + .1; });
const JC = inst(new THREE.SphereGeometry(.34, 8, 6), mat(0xb4b2aa), 70, OBRA1, false); AUTO.push(t => { const on = t > tCo - .1 && t < tB1 + .2; JC.visible = on; if (!on) return; for (let i = 0; i < 70; i++) { const q = (t * .9 + i / 70) % 1; if (q < .82) { const p = CRV.getPointAt(q / .82); pose(JC, i, p.x, p.y, p.z, 0, .6); } else { const f = (q - .82) / .18, top = -FUN + (YB + FUN) * ease(rev(t, tCo, tB1)); pose(JC, i, Math.sin(i) * .4, YB + 3 - f * (YB + 3 - top), 2 + Math.cos(i) * .4, 0, 1); } } JC.instanceMatrix.needsUpdate = true; });
[['obra_caminhao_betoneira', -8, 34.5, PI / 2], ['obra_caminhao_betoneira', -24, 34.5, PI / 2], ['obra_basculante', -21, 20, PI / 2], ['obra_vergalhoes', 20, -20, 0], ['obra_sacos_cimento', 21, -14, .3], ['obra_tabuas', 20, 15, PI / 2], ['obra_gerador', 21, 8, 1]].forEach(([n, x, z, r]) => pc(n, OBRA1, x, n.includes('caminhao') ? 0 : .02, z, r));
const ESCV = pc('obra_escavadeira', CAVA, -11, -FUN, -9, .6); AUTO.push(t => { if (ESCV.braco) ESCV.braco.rotation.x = -.3 + Math.sin(t * 2.2) * .25; ESCV.visible = t < tB0; });
const OPS = [[-8, 5, 0xff7a1a], [6, -6, 0x2f7fd6], [12, 8, 0x2fbf8f]].map(([x, z, c], i) => { const q = pc('personagem', CAVA, x, -FUN, z, 0, { camisa: c, camisa2: 0x25303c }); AUTO.push(t => { const top = t < tCo ? -FUN : -FUN + (YB + FUN) * ease(rev(t, tCo, tB1)); q.position.set(x + Math.sin(t * .7 + i * 2) * 2.5, Math.max(-FUN, top) + (t > tB0 && t < tCo ? 2.4 : 0), z); q.rotation.y = Math.cos(t * .7 + i * 2) > 0 ? PI / 2 : -PI / 2; q.r.anda(t + i, .8); }); return q; });

// torre: tudo que balança junto ---------------------------------------------------------------------------------------------
const TORRE = new THREE.Group(); add(TORRE); TORRE.matrixAutoUpdate = false;
// núcleo
const tN0 = CI[2].e + .1, tN1 = Math.max(tN0 + 2, fim(2) - .25), NNU = 32, HNU = (YC - YB) / NNU, yNu = t => YB + clamp((t - tN0) / (tN1 - tN0)) * (YC - YB);
{ const L = [], Lp = []; for (let i = 0; i < NNU; i++) { const q = tN0 + i / NNU * (tN1 - tN0); L.push({ p: [0, YB + i * HNU, 0], s: [NU * 2, HNU * .99, NU * 2], t: q, d: (tN1 - tN0) / NNU * 1.5, modo: 'cresce', c: i % 2 ? CONC : CONC2 }); if (YB + i * HNU > 0) for (let f = 0; f < 4; f++) Lp.push({ p: face(f, NU + .02, f % 2 ? 1.5 : -1.5, YB + (i + .45) * HNU), q: QY(f * PI / 2), s: [1.4, 2.3, .06], t: q + .15, d: .12, modo: 'pop', c: 0x3a4250 }); } lote(G_CX0, M_L(), L, 0xffffff, TORRE); lote(G_CX, M_L(), Lp, 0xffffff, TORRE); for (let i = 0; i < NNU; i += 3) som(tN0 + i / NNU * (tN1 - tN0), 'tijolo'); }
const FORMA = new THREE.Group(); TORRE.add(FORMA); { B(FORMA, 13, .18, 13, 0xd9a55f, 0, 0, 0, .02); B(FORMA, 13, .12, 13, 0x56606e, 0, -2.4, 0, .02); for (let f = 0; f < 4; f++) { for (let k = 0; k < 6; k++) add(box(.1, 2.6, .1, 0x8d949c, .01), FORMA).position.set(...face(f, 6.4, -6 + k * 2.4, -1.1)); const r = add(box(13, .09, .09, AMAR, .01), FORMA); r.position.set(...face(f, 6.45, 0, 1.1)); r.rotation.y = f * PI / 2; } }
const FANT2 = new THREE.Group(); TORRE.add(FANT2); const fpl = []; for (let i = 0; i < 12; i++) { const m = add(new THREE.Mesh(new THREE.BoxGeometry(24, .4, 24), FANT), FANT2); m.add(new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(24, .4, 24)), new THREE.LineBasicMaterial({ color: 0xff3020 }))); fpl.push(m); }
AUTO.push(t => { const on = t > CI[2].a && t < CI[2].e + .2; FANT2.visible = on; if (on) fpl.forEach((m, i) => { const h = (i + 1) * HA * 1.6, w = Math.sin(t * 3.2 - i * .25) * (i / 12) ** 1.6 * 9; m.position.set(w, YB + 7 + h, 0); m.rotation.z = -Math.cos(t * 3.2 - i * .25) * (i / 12) * .12; }); const fo = t > tN0 - .3 && t < F(3) + .4; FORMA.visible = fo; if (fo) FORMA.position.y = yNu(t) + .1; });
// pilares e lajes
const tL0 = CI[3].e + .1, tL1 = Math.max(tL0 + 2.2, fim(3) - .3), tFl = i => tL0 + i / NAND * (tL1 - tL0), yLaj = t => clamp((t - tL0) / (tL1 - tL0)) * YC;
const COLS = []; [-11.4, -5.7, 0, 5.7, 11.4].forEach(u => { COLS.push([u, 11.4], [u, -11.4]); if (Math.abs(u) < 11) COLS.push([11.4, u], [-11.4, u]); });
{ const Lc = [], Ls = []; COLS.forEach(([x, z], k) => Lc.push({ p: [x, YB, z], s: [.8, -YB, .8], t: tL0 - .4 + k * .01, d: .3, modo: 'cresce', c: CONC2 })); for (let i = 0; i < NAND + NCR; i++) { const q = i < NAND ? tFl(i) : tL1 + (i - NAND) * .12; COLS.forEach(([x, z], k) => Lc.push({ p: [x, i * HA, z], s: [.8, HA, .8], t: q + (k % 5) * .01, d: (tL1 - tL0) / NAND * 1.2, modo: 'cresce', c: CONC2 })); if (i < NAND) Ls.push({ p: [0, (i + 1) * HA - .18, 0], s: [24.6, .36, 24.6], t: q + (tL1 - tL0) / NAND, d: .22, modo: 'desce', dy: 3, c: i % 2 ? CONC : 0xd6d3cb }); } Ls.push({ p: [0, H_T - .2, 0], s: [24.6, .4, 24.6], t: CI[6].n + .2, d: .35, modo: 'desce', dy: 4, c: 0xd6d3cb }); lote(G_CX0, M_L(), Lc, 0xffffff, TORRE); lote(G_CX, M_L(), Ls, 0xffffff, TORRE); for (let i = 0; i < NAND; i += 2) som(tFl(i) + .1, i % 4 ? 'tijolo' : 'toc'); }
const TAMPA = add(box(PIT * 2 + .2, -YB, PIT * 2 + .2, 0xcfccc4, .02)); TAMPA.position.y = YB / 2 - .04; AUTO.push(t => { TAMPA.visible = t > tL0 - .45; });
// parapeito da cobertura
{ const g = grupo(CI[6].n + .4, 1e9, TORRE); for (let f = 0; f < 4; f++) { const m = add(box(24.6, 1.1, .3, 0xe6e3dc, .03), g); m.position.set(...face(f, 12.15, 0, H_T + .55)); m.rotation.y = f * PI / 2; } }

// diagonais de aço em xis -----------------------------------------------------------------------------------------------------
const NTI = 5, HTI = YC / NTI, tD0 = CI[4].e + .1, tD1 = Math.max(tD0 + 1.6, CI[4].n), DD = W2 + .95;
{ const L = [], Ln = [], Lh = []; for (let k = 0; k < NTI; k++) for (let f = 0; f < 4; f++) { const y0 = k * HTI, y1 = y0 + HTI, q = tD0 + ((k + f / 4) / NTI) * (tD1 - tD0); L.push({ ...seg(face(f, DD, -12.2, y0), face(f, DD, 12.2, y1), .38), t: q, d: .25, modo: 'cresce' }, { ...seg(face(f, DD, 12.2, y0), face(f, DD, -12.2, y1), .38), t: q + .06, d: .25, modo: 'cresce' }); Ln.push({ p: face(f, DD + .2, 0, (y0 + y1) / 2), q: QY(f * PI / 2), s: [1.3, 1.3, .5], t: q + .2, d: .15, modo: 'pop' }); }
  for (let k = 0; k <= NTI; k++) for (let f = 0; f < 4; f++) Lh.push({ p: face(f, DD, 0, k * HTI), q: QY(f * PI / 2), s: [26.4, .7, .6], t: tD0 + Math.min(k, NTI - .2) / NTI * (tD1 - tD0), d: .2, modo: 'pop' });
  for (let f = 0; f < 4; f++) L.push({ ...seg(face(f, DD, -12.2, YC), face(f, DD, 12.2, H_T), .38), t: tD1, d: .25, modo: 'cresce' }, { ...seg(face(f, DD, 12.2, YC), face(f, DD, -12.2, H_T), .38), t: tD1 + .05, d: .25, modo: 'cresce' });
  lote(new THREE.BoxGeometry(1, 1, 1).translate(0, .5, 0), M_L({ metalness: .35, roughness: .4 }), L, ACO, TORRE); lote(G_CX, M_L({ metalness: .4 }), Ln, 0x3c4350, TORRE); lote(G_CX, M_L({ metalness: .3, roughness: .45 }), Lh, ACO, TORRE); for (let q = tD0; q < tD1; q += .25) som(q, 'tijolo'); }

// pele de vidro ------------------------------------------------------------------------------------------------------------------
const tV0 = CI[5].e + .1, tV1 = Math.max(tV0 + 2, fim(5) - .3), NCV = 8, LPV = 24 / NCV, PANES = [];
for (let i = 0; i < NAND; i++) for (let f = 0; f < 4; f++) for (let c = 0; c < NCV; c++) PANES.push({ f, c, i, u: -12 + (c + .5) * LPV, y: i * HA + HA / 2 + .1 });
const yVid = t => clamp((t - tV0) / (tV1 - tV0)) * YC;
{ const L = PANES.map((b, n) => ({ p: face(b.f, 12.42, b.u, b.y), q: QY(b.f * PI / 2), s: [LPV * .96, HA * .86, .1], t: tV0 + (b.i + (b.f * NCV + b.c) / (4 * NCV)) / NAND * (tV1 - tV0), d: .12, modo: 'pop', c: new THREE.Color(VID).offsetHSL((n * 7 % 11) * .002, 0, ((n * 13) % 7 - 3) * .014).getHex() })); lote(G_CX, M_L({ metalness: .6, roughness: .08 }), L, 0xffffff, TORRE); for (let i = 0; i < NAND; i += 2) som(tV0 + i / NAND * (tV1 - tV0), 'pop'); }
// janelas acesas da noite, numa onda que sobe
{ const L = []; PANES.forEach((b, n) => { if ((n * 2654435761 >>> 7) % 10 > 6) return; L.push({ p: face(b.f, 12.5, b.u, b.y), q: QY(b.f * PI / 2), s: [LPV * .9, HA * .8, .02], t: T_F + .3 + b.i * .035, d: .08, modo: 'pop', c: [0xffd98a, 0xffe7b0, 0xffc861, 0xfff1d0][n % 4] }); }); const m = lote(G_CX, new THREE.MeshBasicMaterial({ color: 0xffffff }), L, 0xffffff, TORRE); m.castShadow = false; }
// gôndola com o vidraceiro
const GOND = new THREE.Group(); TORRE.add(GOND); { B(GOND, 4.4, .12, 1.3, 0xd9a55f, 0, 0, 0, .02); [-.6, .6].forEach(z => B(GOND, 4.3, .07, .07, AMAR, 0, 1.05, z, .01)); [-2.15, 2.15].forEach(x => B(GOND, .07, 1.05, 1.25, AMAR, x, .52, 0, .01)); GOND.cab = [-1.9, 1.9].map(x => { const c = add(cil(.035, .035, 1, 0x24262a, 6), GOND); c.geometry = G_CIL; c.position.set(x, 1.05, -.5); return c; }); }
const VIDR = pc('personagem', GOND, -.8, .06, 0, PI, { camisa: 0x2f7fd6, camisa2: 0x2565b5 }), PLV = B(GOND, 2.9, 3, .08, VID, .9, 1.6, -.3, .01, { metalness: .6, roughness: .08 });
AUTO.push(t => { const on = t > tV0 - .2 && t < fim(5) + .1; GOND.visible = on; if (!on) return; const y = Math.min(yVid(t), YC - 3); GOND.position.set(3, y + .4, 12.42 + 1.1); GOND.cab.forEach(c => c.scale.set(.035, H_T - y, .035)); VIDR.r.respira(t); VIDR.r.bd.j.rotation.x = -1.6 + Math.sin(t * 6) * .2; VIDR.r.be.j.rotation.x = -1.5; PLV.position.x = .9 + Math.sin(t * 3) * .15; });
// chuva entrando pelos andares abertos e poças
const NCH2 = 900, CHU = inst(new THREE.BoxGeometry(.04, 2.2, .04), new THREE.MeshBasicMaterial({ color: 0xcfe2f2, transparent: true, opacity: .55 }), NCH2, scene, false), CV = Array.from({ length: NCH2 }, () => [rnd(), rnd(), rnd(), .8 + rnd() * .5]);
const chovendo = t => t > F(5) - .05 && t < CI[5].e + .6;
const POCA = inst(new THREE.CircleGeometry(1, 18), new THREE.MeshStandardMaterial({ color: 0x8fb8d0, roughness: .05, metalness: .4 }), 18, TORRE, false), PCs = Array.from({ length: 18 }, (_, i) => [-9 + rnd() * 18, 11 + (i % 6) * 2 * HA + HA, 4 + rnd() * 6, 1 + rnd() * 1.6]);
AUTO.push(t => { const c = chovendo(t); CHU.visible = c; if (c) { for (let i = 0; i < NCH2; i++) { const q = CV[i], y = 1 - (q[1] + t * 1.6 * q[3]) % 1; pose(CHU, i, -24 + q[0] * 44 + (1 - y) * 6, 22 + y * 50, -2 + q[2] * 40, 0, 1, 1, 1, 0, -.22); } CHU.instanceMatrix.needsUpdate = true; }
  const pk = ease(rev(t, F(5) + .2, F(5) + 1.4)) * (1 - ease(rev(t, tV0, tV1))); POCA.visible = pk > .01; if (POCA.visible) { PCs.forEach(([x, y, z, r], i) => pose(POCA, i, x, y + .02, z, 0, r * pk, r * pk * .7, 1, -PI / 2)); POCA.instanceMatrix.needsUpdate = true; } });

// amortecedor de massa na coroa ------------------------------------------------------------------------------------------------------
const T_BOL = tk('bola', 6), YBL = YC + 4.6, RBL = 3.2, tBd = clamp(CI[6].n - T_BOL - .5, .9, 1.5), BOLA = new THREE.Group(); TORRE.add(BOLA);
const bola = add(sh(new THREE.Mesh(new THREE.SphereGeometry(RBL, 40, 28), mat(0xf2bb3a, { metalness: .85, roughness: .22 }))), BOLA);
const CAB_B = [[-1.6, -1.6], [1.6, -1.6], [-1.6, 1.6], [1.6, 1.6]].map(([x, z]) => { const m = add(cil(.06, .06, 1, 0x24262a, 6), TORRE); m.geometry = G_CIL; return { m, x, z }; });
const AMT = []; for (let i = 0; i < 8; i++) { const m = add(cil(.14, .14, 1, 0x56606e, 8), TORRE); m.geometry = G_CIL; AMT.push({ m, a: i / 8 * PI * 2 }); }
let bx = 0; const sway = t => { if (t > CI[4].a + .1 && t < tD1 + .4) return .05 * Math.sin((t - CI[4].a) * 2.6) * ease(rev(t, CI[4].a + .1, CI[4].a + .6)) * (1 - ease(rev(t, tD0 + .3, tD1 + .4))); if (t > CI[6].a + .05 && t < fim(6) + .1) { const a = ease(rev(t, CI[6].a + .05, CI[6].a + .5)), red = 1 - .75 * ease(rev(t, T_BOL + tBd, T_BOL + tBd + .8)); return .016 * Math.sin((t - CI[6].a) * 2.6) * a * red; } return 0; };
AUTO.push(t => { const s = sway(t); TORRE.matrix.set(1, s, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1); TORRE.matrixWorldNeedsUpdate = true;
  const on = t > T_BOL - .3; BOLA.visible = on; const des = 1 - ease(rev(t, T_BOL - .2, T_BOL + tBd)), solto = t > T_BOL + tBd; bx = solto ? -s * YC * 2.2 : 0; BOLA.position.set(bx, YBL + des * 34, 0); CAB_B.forEach(c => { c.m.visible = on && solto; if (!c.m.visible) return; const s_ = seg([c.x + bx, YBL + RBL * .7, c.z], [c.x, H_T - .4, c.z], 1); c.m.position.set(...s_.p); c.m.quaternion.copy(s_.q); c.m.scale.set(.07, s_.s[1], .07); }); AMT.forEach(a => { a.m.visible = on && solto; if (!a.m.visible) return; const s_ = seg([Math.cos(a.a) * 7.5, YC + .2, Math.sin(a.a) * 7.5], [Math.cos(a.a) * RBL * .75 + bx, YBL - RBL * .45, Math.sin(a.a) * RBL * .75], 1); a.m.position.set(...s_.p); a.m.quaternion.copy(s_.q); a.m.scale.set(.14, s_.s[1], .14); }); });

// grua: sobe junto com o prédio --------------------------------------------------------------------------------------------------------
const GX = -21, GZ = -21, GH = 150, GRUA = pc('obra_grua_torre', scene, GX, 0, GZ, 0, { altura: GH, lanca: 52, cor: AMAR }), caboG = add(cil(.06, .06, 1, 0x1c2026, 6)), gancho = B(scene, 1, .8, .6, AMAR, 0, 0, 0, .06), cacamba = add(cil(1.1, .7, 1.8, 0x56606e, 14, { metalness: .4 }));
const topo = t => t < tN0 ? YB : Math.max(yNu(t), t > tL0 ? YC : 0);
const yG = t => Math.min(0, topo(t) + 24 - GH);
const alvoG = t => { if (t < F(3)) return [2, yNu(t) + 5, 2, 1]; if (t < fim(3)) return [-3 + Math.sin(t * 2) * 4, Math.min(yLaj(t) + 6, YC), 6, 0]; if (t > T_BOL - .3 && t < T_BOL + tBd + .1) return [BOLA.position.x, BOLA.position.y + RBL + .5, 0, 2]; return [-26 + Math.sin(t * .4) * 8, H_T + 14, -30, 0]; };
AUTO.push(t => { const on = t > F(2) - .02 && t < T_F; GRUA.visible = caboG.visible = gancho.visible = on; cacamba.visible = false; if (!on) return; GRUA.position.y = yG(t); const a = alvoG(t), dx = a[0] - GX, dz = a[2] - GZ, d = clamp(Math.hypot(dx, dz), 5, 50), fi = Math.atan2(dx, dz); if (GRUA.giro) GRUA.giro.rotation.y = fi; const tx = GX + Math.sin(fi) * d, tz = GZ + Math.cos(fi) * d, ty = GH + GRUA.position.y + .6; caboG.position.set(tx, (ty + a[1]) / 2, tz); caboG.scale.y = Math.max(ty - a[1], .1); gancho.position.set(tx, a[1] + .4, tz); cacamba.visible = a[3] === 1; cacamba.position.set(tx, a[1] - 1.1, tz); });

// elevadores na face leste ------------------------------------------------------------------------------------------------------------
const T_CAB = tk('cabines', 7), tEl0 = CI[7].e + .05, XEL = W2 + 2.8, ZEL = [-4.5, 4.5];
{ const L = [], Lm = []; ZEL.forEach(zc => [-1.35, 1.35].forEach(dz => L.push({ p: [W2 + 1.6, 0, zc + dz], s: [.2, YC, .2], t: tEl0, d: .7, modo: 'cresce', c: 0x56606e }))); ZEL.forEach(zc => Lm.push({ p: [XEL - .4, YC + 1.2, zc], s: [3.4, 2.4, 3.2], t: tEl0 + .5, d: .25, modo: 'pop', c: 0xdedad2 })); lote(G_CX0, M_L({ metalness: .5 }), L, 0xffffff, TORRE); lote(G_CX, M_L(), Lm, 0xffffff, TORRE); }
const cabine = (zc, fase) => { const g = new THREE.Group(); TORRE.add(g); B(g, 2.6, .18, 2.6, AMAR, 0, 0, 0, .03); B(g, 2.6, .18, 2.6, AMAR, 0, 2.8, 0, .03); [[-1.25, -1.25], [1.25, -1.25], [-1.25, 1.25], [1.25, 1.25]].forEach(([a, b]) => B(g, .1, 2.8, .1, AMAR, a, 1.4, b, .01)); const v = add(new THREE.Mesh(new THREE.BoxGeometry(2.5, 2.7, 2.5), new THREE.MeshStandardMaterial({ color: 0xaee3f7, transparent: true, opacity: .25, roughness: .05 })), g); v.position.y = 1.4; add(new THREE.Mesh(new THREE.BoxGeometry(2.4, .05, 2.4), brilho(0xfff1c8)), g).position.y = 2.7;
  const p1 = gente(g, -.4, .1, 0, { escala: 1 }); p1.position.set(-.4, .09, .3); p1.rotation.y = PI / 2; const cb = add(cil(.04, .04, 1, 0x1c2026, 6), TORRE); cb.geometry = G_CIL;
  AUTO.push(t => { const on = t > T_CAB - .1; g.visible = cb.visible = on; if (!on) return; const k = ease(rev(t, T_CAB + .2, fim(7) + .3)), y = t < T_F ? (fase ? 16 + k * 50 : 66 - k * 48) : (Math.sin(t * .35 + fase * 3) * .5 + .5) * (YC - 6); g.position.set(XEL, y, zc); g.scale.setScalar(Math.max(back(rev(t, T_CAB - .1, T_CAB + .2)), .01)); cb.position.set(XEL, y + 2.9, zc); cb.scale.set(.05, YC + .2 - y - 2.9, .05); p1.r.respira(t); }); return g; };
const CABA = cabine(ZEL[0], 1), CABB = cabine(ZEL[1], 0);
// quem teria que subir a pé
const SUB = pc('pessoa_moradora', scene, 18.5, 0, 14.5, -2.4); AUTO.push(t => { SUB.visible = t > F(7) - .02 && t < CI[7].e + .1; if (SUB.r) { SUB.r.respira?.(t); if (SUB.r.cab) SUB.r.cab.rotation.x = -.5; } });

// para-raios, cabo de descida e a tempestade -------------------------------------------------------------------------------------------
const T_HAS = tk('haste', 8), T_LIG = tk('ligada', 8), T_RAIO = CI[8].n, T_R1 = Math.min(tk('procura', 8) + .3, CI[8].e - .4);
const HASTE = new THREE.Group(); TORRE.add(HASTE); { add(cil(.12, .16, 9, 0xb9c0c8, 10, { metalness: .8, roughness: .25 }), HASTE).position.y = 4.5; add(cil(.9, 1.1, .5, 0x8d949c, 14, { metalness: .6 }), HASTE).position.y = .25; add(esf(.22, 0xd8dde3, { metalness: .9, roughness: .2 }), HASTE).position.y = 9.1; }
const LUZA = add(esf(.3, brilho(0xff2a2a)), TORRE); LUZA.position.y = H_T + 9.5;
AUTO.push(t => { const k = ease(rev(t, T_HAS, T_HAS + .7)); HASTE.visible = k > 0; HASTE.position.y = H_T; HASTE.scale.set(1, Math.max(k, .01), 1); LUZA.visible = t > T_F && Math.sin(t * 5) > -.1; });
const DC = W2 + 1.5, COBRE = mat(0xe08a3a, { metalness: .6, roughness: .3, emissive: 0x8a3a08, emissiveIntensity: .9 }), DESC = add(new THREE.Mesh(G_DESCE, COBRE), TORRE); DESC.position.set(DC, H_T + .3, DC); const DTOP = add(new THREE.Mesh(G_CIL, COBRE), TORRE); { const s_ = seg([0, H_T + .35, 0], [DC, H_T + .35, DC], 1); DTOP.position.set(...s_.p); DTOP.quaternion.copy(s_.q); DTOP.scale.set(.14, s_.s[1], .14); }
const ATER = new THREE.Group(); add(ATER); ATER.position.set(DC, 0, DC); add(cil(.6, .6, .1, 0x56606e, 16), ATER).position.y = .05; add(cil(.08, .08, 3, 0xc9904a, 8, { metalness: .7 }), ATER).position.y = -1.4;
AUTO.push(t => { const k = ease(rev(t, T_LIG, T_LIG + 1)); DESC.visible = k > 0; DESC.scale.set(.22, Math.max(k * (H_T + .3), .01), .22); DTOP.visible = t > T_LIG - .1; ATER.visible = t > T_LIG + .9; });
const raio = (x, z, yB, sd) => { const g = new THREE.Group(); add(g); const r2 = prng(sd); let px = x, py = yB; const pts = [[px, py]]; while (py < yB + 220) { px += (r2() - .5) * 18; py += 10 + r2() * 12; pts.push([px, py]); } const mB = brilho(0xeef4ff), mG = new THREE.MeshBasicMaterial({ color: 0x9fb8ff, transparent: true, opacity: .35, toneMapped: false, depthWrite: false }); for (let i = 1; i < pts.length; i++) { const s_ = seg([pts[i - 1][0], pts[i - 1][1], z], [pts[i][0], pts[i][1], z], 1); [[mB, .35], [mG, 1.4]].forEach(([m, r]) => { const c = add(new THREE.Mesh(G_CIL, m), g); c.position.set(...s_.p); c.quaternion.copy(s_.q); c.scale.set(r, s_.s[1], r); }); if (i % 3 === 1) { const b = add(new THREE.Mesh(G_CIL, mB), g); const s2 = seg([pts[i][0], pts[i][1], z], [pts[i][0] + (r2() - .5) * 20, pts[i][1] + 12, z + (r2() - .5) * 6], 1); b.position.set(...s2.p); b.quaternion.copy(s2.q); b.scale.set(.18, s2.s[1], .18); } } g.visible = false; return g; };
const R1 = raio(W2, -W2 + .5, H_T, 11), R2 = raio(0, 0, H_T + 9.2, 5);
const FAIS = inst(new THREE.SphereGeometry(.35, 8, 6), brilho(0xbfe0ff), 40, scene, false);
const CORR = inst(new THREE.SphereGeometry(.5, 10, 8), brilho(0x9fd8ff), 24, scene, false);
const rel = t => [T_R1, T_RAIO + .05].reduce((a, q) => { const d = t - q; return d > 0 && d < .45 ? Math.max(a, (1 - d / .45) * (Math.sin(d * 60) * .25 + .75)) : a; }, 0);
AUTO.push(t => { const d1 = t - T_R1, d2 = t - T_RAIO - .05; R1.visible = d1 > 0 && d1 < .32 && Math.sin(d1 * 70) > -.5; R2.visible = d2 > 0 && d2 < .4 && Math.sin(d2 * 70) > -.5;
  const fo = d1 > 0 && d1 < 1; FAIS.visible = fo; if (fo) { for (let i = 0; i < 40; i++) { const a = i * 2.4, v = 4 + (i % 5) * 2; pose(FAIS, i, W2 + Math.cos(a) * v * d1, H_T + 1 + v * d1 * 1.2 - 9 * d1 * d1, -W2 + Math.sin(a) * v * d1, 0, Math.max(1 - d1, .01)); } FAIS.instanceMatrix.needsUpdate = true; }
  const co = d2 > 0 && d2 < 2.4; CORR.visible = co; if (co) { for (let i = 0; i < 24; i++) { const q = clamp(d2 * 1.1 - i * .035); let x, y, z; if (q < .12) { const f = q / .12; x = (DC) * f; z = (DC) * f; y = H_T + 9 - f * 8.6; } else { const f = (q - .12) / .88; x = DC; z = DC; y = (H_T + .3) * (1 - f); } pose(CORR, i, x, y, z, 0, q > 0 && q < 1 ? 1 : .001); } CORR.instanceMatrix.needsUpdate = true; } });
const tempestade = t => ease(rev(t, F(8) - .1, F(8) + .7)) * (1 - ease(rev(t, T_F - .1, T_F + .6)));

// moeda na beira da cobertura --------------------------------------------------------------------------------------------------------
const MOEDA = add(cil(.0135, .0135, .0022, 0xe8b830, 24, { metalness: .95, roughness: .18 })); MOEDA.visible = false; const MBR = add(new THREE.Mesh(new THREE.SphereGeometry(.03, 10, 8), brilho(0xfff2b0, { transparent: true, opacity: .8 })));
AUTO.push(t => { const on = t > T_MOE - .3 && t < T_VER; MOEDA.visible = MBR.visible = on; if (!on) return; const q = Math.max(0, t - T_MOE - .15), y = H_T + 1.112 - 4.9 * q * q, z = W2 + .15 + q * 2.8; MOEDA.position.set(1.4, Math.max(y, .25), z); MOEDA.rotation.set(q * 14, 0, q * 9); MBR.position.copy(MOEDA.position); MBR.position.x += .008; MBR.position.y += .006; MBR.scale.setScalar(.15 + Math.abs(Math.sin(t * 9)) * .2); });

// noite, tempestade, clarões ------------------------------------------------------------------------------------------------------
const GLOW = (() => { const tx = tex(64, 64, (c, w, h) => { const g = c.createRadialGradient(32, 32, 0, 32, 32, 32); g.addColorStop(0, 'rgba(255,240,200,1)'); g.addColorStop(.3, 'rgba(255,214,140,.5)'); g.addColorStop(1, 'rgba(255,200,120,0)'); c.fillStyle = g; c.fillRect(0, 0, w, h); }); const pts = [...LUZP]; for (let f = 0; f < 4; f++) for (let k = 0; k < 7; k++) pts.push(face(f, 12.8, -12 + k * 4, H_T + 1.3)); const ps = new Float32Array(pts.length * 3); pts.forEach((p, i) => ps.set(p, i * 3)); const q = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(ps, 3)), new THREE.PointsMaterial({ map: tx, size: 9, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, opacity: .85, sizeAttenuation: true, fog: false })); q.frustumCulled = false; add(q); AUTO.push(tt => { q.visible = tt >= T_F + .3; }); return q; })();
const COROA = (() => { const g = new THREE.Group(); TORRE.add(g); for (let f = 0; f < 4; f++) { const m = add(new THREE.Mesh(new THREE.BoxGeometry(24.8, .25, .1), brilho(0xbfe6ff)), g); m.position.set(...face(f, 12.62, 0, H_T + 1.15)); m.rotation.y = f * PI / 2; const n = add(new THREE.Mesh(new THREE.BoxGeometry(24.8, .25, .1), brilho(0xbfe6ff)), g); n.position.set(...face(f, 13.5, 0, YC + .2)); n.rotation.y = f * PI / 2; } AUTO.push(t => { g.visible = t > T_F + 1.3; }); return g; })();
const BG = new THREE.Color(), DIA = new THREE.Color(CEU), NO = new THREE.Color('#0a1030'), TEMP = new THREE.Color('#4a5466'), CHV = new THREE.Color('#8494a6'), RAIOC = new THREE.Color('#c8d4ff');
AUTO.push(t => { const n = ease(rev(t, T_F - .1, T_F + .9)), st = tempestade(t), ch = chovendo(t) ? ease(rev(t, F(5) - .05, F(5) + .3)) * (1 - ease(rev(t, CI[5].e + .2, CI[5].e + .6))) : 0, rl = rel(t);
  if (n > 0 || st > 0 || ch > 0 || rl > 0) { BG.copy(DIA).lerp(CHV, ch * .8).lerp(TEMP, st).lerp(NO, n).lerp(RAIOC, rl * .5); scene.background = BG; } else scene.background = fundo;
  const esc = Math.max(st * .85, ch * .5); sol.intensity = 2.6 * (1 - n) * (1 - esc * .7) + rl * 2.5 + .02; frenteL.intensity = .55 * (1 - n) + n * .1; hemi.forEach(h => { h.intensity = 1.25 - n * .85 - esc * .45 + rl * 1.2; }); scene.environmentIntensity = .32 - n * .2 - esc * .1;
  scene.fog.color.copy(C.set(0xcfe6f2).lerp(TEMP, esc).lerp(new THREE.Color(0x0e1630), n)); scene.fog.near = 320 - esc * 120; scene.fog.far = 1300 - esc * 500;
  grama.material.color.set(GR).lerp(C.set(0x10261c), n); MATS.forEach(m => { m.emissiveIntensity = n * 1.5; });
  trevas.style.opacity = st * .18;
  let fl = 0; for (let i = 1; i < N - 1; i++) { const d = t - CI[i].n; if (d > 0 && d < .45) fl = Math.max(fl, .3 * (1 - d / .45)); } fl = Math.max(fl, rl * .55); flash.style.opacity = fl; });
// chuva da tempestade, no fim do para-raios
const NCH3 = 1400, CH3 = inst(new THREE.BoxGeometry(.06, 3.4, .06), new THREE.MeshBasicMaterial({ color: 0xbfd8f7, transparent: true, opacity: .45 }), NCH3, scene, false), C3 = Array.from({ length: NCH3 }, () => [-80 + rnd() * 200, rnd(), -60 + rnd() * 200, rnd()]);
AUTO.push(t => { const on = tempestade(t) > .3; CH3.visible = on; if (!on) return; for (let i = 0; i < NCH3; i++) { const [x, u, z, p] = C3[i], q = ((u - t * 1.2 + p) % 1 + 1) % 1, y = q * 150; pose(CH3, i, x + (150 - y) * .15, y, z, 0, 1, 1, 1, 0, -.15); } CH3.instanceMatrix.needsUpdate = true; });

// operário que acompanha a obra --------------------------------------------------------------------------------------------------------
const OP = pc('personagem', TORRE, 0, 0, 0, 0, { camisa: 0xff7a1a, camisa2: 0xd9631a }), MART = new THREE.Group(); OP.r.bd.k.add(MART); MART.position.y = -.38; B(MART, .05, .36, .05, 0x7a4a26, 0, -.1, 0, .012); B(MART, .2, .1, .1, 0x5e6a78, 0, -.3, 0, .02); MART.rotation.x = 1.4;
const postoOP = t => { if (t < tN0) return null; if (t < F(3)) return { p: [3.6, yNu(t) + .2, 4.2], ry: .5, m: 1 }; if (t < F(4)) { const y = Math.floor(yLaj(t) / HA) * HA; return { p: [6.5, Math.max(y, 0) + .2, 8.5], ry: .6, m: 1 }; } if (t < F(6)) return null; if (t < fim(6)) return { p: [-6.5, YC + .38, 6.5], ry: -.6, m: 0 }; if (t > F(8) && t < T_F) return { p: [3.2, H_T + .2, 2.6], ry: .5, m: 1 }; return null; };
AUTO.push(t => { const q = postoOP(t); OP.visible = !!q; if (!q) return; OP.position.set(...q.p); OP.rotation.y = q.ry; OP.r.anda(0, 0); OP.r.respira(t); MART.visible = !!q.m; if (q.m) { OP.r.bd.j.rotation.x = -2.3 + Math.sin(t * 9) * .4; OP.r.bd.k.rotation.x = -.25; } else { OP.r.bd.j.rotation.x = -.4; } });

// câmera ------------------------------------------------------------------------------------------------------------------------------------
const K = [], Pk = (t, p, l, f = 38) => K.push({ t, p, l, f }), cut = (t, p, l, f = 38) => { const a = K[K.length - 1]; if (a) Pk(t - .02, a.p, a.l, a.f); Pk(t + .02, p, l, f); };
Pk(0, [13, 1.7, 76], [0, 41, 0], 62); Pk(fim(0) + .1, [10, 1.7, 70], [0, 43, 0], 60);
const T_SEC1 = Math.max(T_BLO, tE1) + .02;
cut(F(1), [0, 30, 60], [0, 0, 0]); Pk(T_SEC1 - .05, [0, 30, 60], [0, 0, 0]); // trecho trocado pelo corte do solo (ver SECAO)
cut(T_SEC1, [35, 34, 56], [0, -7, 0]); Pk(CI[1].n, [33, 36, 52], [0, -7, 0]); Pk(fim(1), [32, 38, 50], [0, -6, 0]);
cut(F(2), [35, 30, 80], [0, 8, 0]); Pk(tN0, [35, 28, 78], [0, 6, 0]); Pk(tN1, [35, YC + 8, 96], [0, YC - 4, 0]); Pk(fim(2), [35, YC + 10, 98], [0, YC - 4, 0]);
cut(F(3), [-105, 52, 160], [0, 54, 0]); Pk(tL0, [-102, 50, 155], [0, 54, 0]); Pk(fim(3), [-92, 58, 140], [0, 58, 0]);
cut(F(4), [105, 46, 150], [0, 54, 0]); Pk(tD0, [105, 46, 146], [0, 55, 0]); Pk(fim(4), [105, 62, 128], [0, 58, 0]);
cut(F(5), [9, 47, 42], [0, 46, 8], 40); Pk(CI[5].e, [7, 48, 40], [0, 46, 8], 40); cut(tV0, [-28, 12, 52], [2, 14, 12]); Pk(tV1, [-36, YC - 2, 66], [2, YC - 10, 12]); Pk(fim(5), [-38, YC + 2, 68], [2, YC - 8, 12]);
cut(F(6), [52, YC + 14, 64], [0, YC + 2, 0]); Pk(T_BOL - .3, [46, YC + 14, 56], [0, YC + 3, 0]); cut(T_BOL - .25, [30, YC + 14, 40], [0, YC + 10, 0], 44); Pk(T_BOL + tBd, [27, YC + 10, 35], [0, YC + 5, 0], 42); Pk(fim(6), [25, YC + 9, 33], [0, YC + 4.6, 0], 42);
cut(F(7), [23.6, 1.0, 23.6], [8, 14, 2], 60); Pk(CI[7].e, [23.4, 1.0, 23.2], [8, 17, 2], 60); cut(tEl0, [40, 30, 3], [W2, 28, 0], 56); Pk(T_CAB + .3, [40, 30, 2], [W2, 28, 0], 56); Pk(fim(7), [40, 50, 1], [W2, 48, 0], 56);
cut(F(8), [74, H_T + 22, 92], [0, H_T - 14, 0]); Pk(CI[8].e, [70, H_T + 20, 88], [0, H_T - 12, 0]); cut(CI[8].e + .02, [28, H_T + 11, 36], [0, H_T + 3, 0], 40); Pk(T_LIG - .05, [26, H_T + 10, 34], [0, H_T + 3, 0], 40); cut(T_LIG, [58, 54, 76], [W2, 50, W2]); Pk(T_RAIO - .1, [58, 52, 76], [W2, 52, W2]); cut(T_RAIO - .05, [140, 70, 170], [0, 66, 0]); Pk(fim(8), [135, 70, 162], [0, 66, 0]);
cut(T_F, [-105, 70, 182], [0, 60, 0]); Pk(T_MOE - .35, [-105, 72, 172], [0, 60, 0]); cut(T_MOE - .3, [-.2, H_T + 2.1, 9.6], [2.2, H_T - 28, 26], 26); Pk(T_VER - .1, [-.3, H_T + 2.2, 9.2], [2.2, H_T - 34, 24], 26); cut(T_VER, [172, 118, 228], [0, 56, 0]); Pk(D.total + 1, [184, 128, 240], [0, 56, 0]);
K.sort((a, b) => a.t - b.t); for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01;
// corte do solo: câmera abaixo do chão (o camTo não deixa descer, então é feita aqui)
const SECAO = t => t > F(1) && t < T_SEC1; const cA = new THREE.Vector3(), cL = new THREE.Vector3();
const camSecao = t => { const k = ease(rev(t, F(1), T_SEC1)); cA.set(-3 + k * 6, -12.5, 81 - k * 4); cL.set(k * 2, -22, 13); cam.position.copy(cA); cam.fov = 38; cam.updateProjectionMatrix(); cam.lookAt(cL); };
AUTO.push(t => { const s = SECAO(t); TAPF.visible = !s && t >= F(1) - .02 && t < T_F; PAREDEF.visible = !s && t < CI[3].e + .1 && t >= F(1) - .02; });

// rótulos e sons ------------------------------------------------------------------------------------------------------------------------------
const NOM = ['', 'FUNDAÇÃO', 'NÚCLEO', 'LAJES', 'DIAGONAIS', 'PELE DE VIDRO', 'AMORTECEDOR', 'ELEVADORES', 'PARA-RAIOS'];
for (let i = 1; i < N - 1; i++) { const a = CI[i].n, e = rotulo(NOM[i], [540, 400], a, fim(i), 'grande'); e.style.fontSize = NOM[i].length > 11 ? '70px' : '88px'; e.style.transform += ' rotate(-3deg)'; som(a, 'ding'); }
const ruim = (x, a, b) => { rotulo(x, [540, 400], a, b, 'grande').style.cssText += ';font-size:66px;color:#ff5a4f'; };
ruim('SEM ESTRUTURA', Math.max(2.1, tk('Sem', 0, .7) - .1), fim(0)); ruim('CHÃO MOLE', tk('mole', 1), CI[1].e); ruim('SEM ESPINHA', tk('espinha', 2), CI[2].e); ruim('SEM PISO', tk('piso', 3), CI[3].e); ruim('VENTO', tk('vento', 4), CI[4].e); ruim('CHUVA', tk('chuva', 5), CI[5].e); ruim('BALANÇA', tk('balança', 6), CI[6].e); ruim('A PÉ?', tk('escada', 7), CI[7].e); ruim('RAIO', tk('raio', 8), CI[8].e);
rotulo('ROCHA', [-5, ROC - 6, 14], T_ROC, T_SEC1, 'ouro');
rotulo('ARRANHA-CÉU PRONTO!', [540, 400], T_F + .1, T_MOE - .35, 'grande').style.fontSize = '64px'; rotulo('VERDADE OU MENTIRA?', [540, 400], T_VER, D.total + 1, 'grande').style.fontSize = '62px';
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); });
som(.05, 'crack'); som(.6, 'crack'); som(1.3, 'desaba'); som(1.4, 'crack'); for (let q = .2; q < fim(0); q += .55) som(q, 'gota'); som(.1, 'whoosh'); som(2.2, 'whoosh');
som(CI[1].a + .3, 'concreto'); for (let q = tB0; q < tCo; q += .3) som(q, 'toc'); som(tCo, 'concreto'); som(tCo + 1, 'concreto');
som(CI[4].a + .2, 'whoosh'); som(CI[6].a + .2, 'whoosh'); som(T_BOL + tBd, 'impact');
for (let q = F(5); q < CI[5].e + .5; q += .9) som(q, 'chuva'); som(tEl0, 'motor'); som(T_CAB + .3, 'motor'); som(T_HAS, 'toc'); som(T_R1, 'impact'); som(T_R1 + .05, 'crack'); som(T_RAIO + .05, 'impact'); som(T_RAIO + .1, 'zumbido'); for (let q = F(8); q < fim(8); q += .9) som(q, 'chuva');
som(T_F - .4, 'riser'); som(T_F + .3, 'impact'); som(T_MOE + .2, 'gota'); som(T_VER, 'ding');
window.CAPA_T = T_F + 2.1;
// a câmera acompanha a moeda caindo
const MCAM = t => t > T_MOE - .3 && t < T_VER;
const camMoeda = () => { const p = MOEDA.position; cam.position.set(p.x - .45, p.y + .5, p.z - .2); cam.fov = 34; cam.updateProjectionMatrix(); cam.lookAt(p.x + .05, p.y - .08, p.z + .05); };
iniciar(t => { camTo(K, t); if (SECAO(t)) camSecao(t); cam.updateMatrixWorld(); AUTO.forEach(f => f(t)); if (MCAM(t)) { camMoeda(); cam.updateMatrixWorld(); } });
