// Paraquedas, parte por parte. Abre no céu: o pano saiu embolado, só sacode, a pessoa gira e despenca.
// Um mundo só: a área de salto (lona de dobragem, hangar, alvo, pista de grama) no meio de sítios, rio, mata e uma cidadezinha.
// No chão: células costuradas, o vento enchendo o velame, cordas e arnês, dobragem no container. No céu: slider, extrator, batoques e reserva.
// Fecha com pouso no alvo ao pôr do sol, formação em queda livre e a área de salto acendendo à noite. Medidas em metros.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, tex, iniciar, som, rotulo, fala, D } = K3;
const H = PC.H, rnd = prng(57), F = fala, fim = i => F(i) + D.falas[i].dur, N = D.falas.length, AUTO = [], O = new THREE.Object3D(), C = new THREE.Color(), PI = Math.PI;
O.rotation.order = 'YXZ'; cam.far = 4200; cam.updateProjectionMatrix();
const nk = x => String(x).toLowerCase().normalize('NFD').replace(/[^a-z0-9]/g, '');
const tk = (w, i, f = .4) => { const k = nk(w), q = D.falas[i].words?.find(p => nk(p.w).startsWith(k)); return q ? q.start : F(i) + D.falas[i].dur * f; };
const nomeT = i => { const q = [...(D.falas[i].words ?? [])].reverse().find(p => /^(essa|esse|essas|esses)$/.test(nk(p.w))); return q ? q.start : fim(i) - 1.2; };
const rev = (t, a, b) => clamp((t - a) / (b - a));
const CI = {}; for (let i = 1; i < N - 1; i++) CI[i] = { a: F(i), e: tk('Então', i, .4), n: nomeT(i) };
const B = (g, w, h, d, c, x, y, z, r = .02, o) => { const m = add(box(w, h, d, c, r, o), g); m.position.set(x, y, z); return m; };
const pc = (n, g, x, y, z, ry = 0, o, e = 1) => { const q = PC.novo(n, o); q.position.set(x, y, z); q.rotation.y = ry; if (e !== 1) q.scale.multiplyScalar(e); g.add(q); return q; };
const pose = (I, i, x, y, z, ry, sx = 1, sy = sx, sz = sx, rx = 0, rz = 0) => { O.position.set(x, y, z); O.rotation.set(rx, ry, rz, 'YXZ'); O.scale.set(sx, sy, sz); O.updateMatrix(); I.setMatrixAt(i, O.matrix); };
const inst = (geo, m, n, g = scene, sombra = true) => { const I = new THREE.InstancedMesh(geo, m, n); I.frustumCulled = false; I.castShadow = sombra; I.receiveShadow = true; g.add(I); return I; };
const plano = (w, d, c, x, y, z, g = scene, o) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, d), typeof c === 'object' ? c : mat(c, { roughness: 1, ...o })), g); m.rotation.x = -PI / 2; m.position.set(x, y, z); m.receiveShadow = true; return m; };
const brilho = (c, o = {}) => new THREE.MeshBasicMaterial({ color: c, toneMapped: false, ...o });
const escuro = (c, f = .78) => new THREE.Color(c).multiplyScalar(f).getHex();
const curva = p => new THREE.CatmullRomCurve3(p.map(q => new THREE.Vector3(...q)), false, 'catmullrom', .3);
const UP = new THREE.Vector3(0, 1, 0), V1 = new THREE.Vector3(), V2 = new THREE.Vector3(), V3 = new THREE.Vector3(), V4 = new THREE.Vector3(), Q1 = new THREE.Quaternion();
const G_CIL = new THREE.CylinderGeometry(1, 1, 1, 6).translate(0, .5, 0);
const liga = (m, a, b, r) => { V3.subVectors(b, a); const n = Math.max(V3.length(), 1e-4); m.position.copy(a); m.quaternion.setFromUnitVectors(UP, V3.multiplyScalar(1 / n)); m.scale.set(r, n, r); };
const ligaI = (I, i, a, b, r) => { V3.subVectors(b, a); const n = Math.max(V3.length(), 1e-4); O.position.copy(a); O.quaternion.setFromUnitVectors(UP, V3.multiplyScalar(1 / n)); O.scale.set(r, n, r); O.updateMatrix(); I.setMatrixAt(i, O.matrix); };

// tempos ----------------------------------------------------------------------------------------------------------------
const T0E = tk('embolado', 0), T0D = tk('despenca', 0), T0P = (() => { const q = (D.falas[0].words ?? []).filter(p => nk(p.w) === 'pano'); return q[1] ? q[1].start : fim(0) - 1.6; })();
const T1B = tk('balança', 1), T1C = Math.max(tk('costura', 1), CI[1].e + .05), T1K = Math.max(tk('camadas', 1), T1C + .7), T1R = Math.max(tk('paredes', 1), T1K + .6), T1N = CI[1].n;
const T2M = tk('murchas', 2), T2V = Math.max(tk('vento', 2), T2M + .4), T2E = Math.max(tk('enche', 2), T2V + .3), T2A = Math.max(tk('asa', 2), T2E + .5), T2N = CI[2].n;
const T3C = tk('carregar', 3), T3K = Math.max(tk('cordas', 3), CI[3].e + .1), T3F = Math.max(tk('fitas', 3), T3K + .8), T3P = Math.max(tk('pernas', 3), T3F + .3), T3T = Math.max(tk('peito', 3), T3P + .3), T3N = CI[3].n;
const T4S = Math.max(F(4) + .8, tk('tranco', 4) - .2), T4E = CI[4].e, T4A = tk('argolas', 4), T4D = Math.max(tk('desce', 4), T4E + .4), T4B = Math.max(T4D + 2.2, CI[4].n + .3), T4N = CI[4].n;
const T5V = tk('avião', 5), T5E = CI[5].e, T5D = Math.max(tk('dobra', 5), T5E + .1), T5M = Math.max(tk('mochila', 5), T5D + .8), T5P = Math.max(tk('pino', 5), T5M + .7), T5N = CI[5].n;
const T6X = F(6) + .45, T6E = Math.max(CI[6].e, T6X + .9), T6P = Math.max(tk('paraquedinha', 6), T6E + .3), T6I = Math.max(tk('arranca', 6), T6P + .7), T6R = Math.max(tk('resto', 6), T6I + .35), T6N = CI[6].n;
const T7C = tk('controle', 7), T7P = Math.max(tk('puxa', 7), CI[7].e + .1), T7F = Math.max(tk('freiam', 7), T7P + 1.2), T7N = CI[7].n;
const T8S = Math.max(tk('solta', 8), CI[8].e + .1), T8A = Math.max(tk('abre', 8), T8S + .6), T8N = CI[8].n;
const T9 = F(N - 1) - .02, T9L = T9 + 2.3, T9C = Math.max(tk('queda', N - 1), T9L + .5), T9V = tk('Verdade', N - 1, .85);

// céu e luz -------------------------------------------------------------------------------------------------------------
const CEU = '#3f8fe0'; ceu(CEU, '#d6eefa'); const fundo = scene.background; scene.fog = new THREE.Fog(0xcfe6f2, 200, 2600);
const sol = luzes(0xfff2de, 0xd8ecff, 0x8fb070, 2.6, 18); add(sol.target); scene.environmentIntensity = .32;
const hemi = []; scene.traverse(o => { if (o.isHemisphereLight) hemi.push(o); });
const camada = c => { const e = document.createElement('div'); e.style.cssText = `position:absolute;inset:0;background:${c};opacity:0`; document.getElementById('hud').prepend(e); return e; };
const flash = camada('#fff8e0'), alerta = camada('radial-gradient(circle at 50% 50%, rgba(255,40,20,0) 35%, rgba(255,30,10,.85) 100%)');

// chão: sítios, rio, lago, estradas, mata, cidade, morros ------------------------------------------------------------
const GR = 0x5fb55a, TG = new THREE.Vector3(26, 0, 18);
plano(9000, 9000, 0x5c9c48, 0, 0, 0);
const RIO = curva([[-2600, 0, -520], [-1400, 0, -300], [-700, 0, -130], [-300, 0, -250], [120, 0, -215], [520, 0, -330], [1100, 0, -180], [1800, 0, -420], [2600, 0, -300]]).getSpacedPoints(420);
const perto = (x, z, L, d) => { for (let i = 0; i < L.length; i += 2) { const p = L[i]; if ((p.x - x) ** 2 + (p.z - z) ** 2 < d * d) return true; } return false; };
const fita = (pts, w, y, c, o = {}) => { const P = [], I = []; for (let i = 0; i < pts.length; i++) { const a = pts[Math.max(i - 1, 0)], b = pts[Math.min(i + 1, pts.length - 1)]; V1.subVectors(b, a).normalize(); const nx = -V1.z, nz = V1.x, p = pts[i]; P.push(p.x + nx * w / 2, y, p.z + nz * w / 2, p.x - nx * w / 2, y, p.z - nz * w / 2); if (i < pts.length - 1) I.push(2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 1, 2 * i + 3, 2 * i + 2); } const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); g.setIndex(I); g.computeVertexNormals(); const m = add(new THREE.Mesh(g, mat(c, { side: 2, ...o }))); m.receiveShadow = true; return m; };
fita(RIO, 54, .05, 0xcfb47c); fita(RIO, 32, .08, 0x3b8fd2, { roughness: .15, metalness: .15 });
{ const l = add(new THREE.Mesh(new THREE.CircleGeometry(80, 40), mat(0x3b8fd2, { roughness: .15, metalness: .15 }))); l.rotation.x = -PI / 2; l.position.set(-420, .08, 300); const m = add(new THREE.Mesh(new THREE.CircleGeometry(92, 40), mat(0xcfb47c))); m.rotation.x = -PI / 2; m.position.set(-420, .06, 300); }
const CIDADE = new THREE.Vector3(820, 0, 640);
const fora = (x, z, m = 0) => Math.abs(x) < 200 + m && Math.abs(z) < 170 + m;
// lotes de plantação
{ const CL = [0x6dbb4f, 0x8cc84b, 0x4f9a3f, 0xd9c25a, 0xb98d4f, 0x7fae3a, 0xa7c95a, 0xe0cf7a, 0x5fa844, 0xc4a85a], n = 1700, I = inst(new THREE.PlaneGeometry(1, 1).rotateX(-PI / 2), mat(0xffffff, { roughness: 1 }), n, scene, false); let k = 0;
  for (let gx = -20; gx <= 20; gx++) for (let gz = -20; gz <= 20; gz++) { const x = gx * 112 + (rnd() - .5) * 18, z = gz * 112 + (rnd() - .5) * 18; if (k >= n || fora(x, z) || perto(x, z, RIO, 70) || Math.hypot(x - CIDADE.x, z - CIDADE.z) < 200 || Math.hypot(x + 420, z - 300) < 120) continue; pose(I, k, x, .03, z, (rnd() - .5) * .06, 92 + rnd() * 16, 1, 92 + rnd() * 16); I.setColorAt(k, C.set(CL[Math.floor(rnd() * CL.length)])); k++; } I.count = k; }
// estradas
const TERRA_E = 0xc8a56e, ASF = 0x4a4d55;
plano(5200, 9, ASF, 0, .06, 420); plano(9, 2600, ASF, 820, .06, 1300); plano(7, 290, TERRA_E, 40, .06, 280); plano(5200, 6, TERRA_E, 0, .055, 860); plano(6, 5200, TERRA_E, -640, .055, 0);
{ const I = inst(new THREE.BoxGeometry(5, .02, .25), brilho(0xf2e6b0), 300, scene, false); for (let i = 0; i < 300; i++) pose(I, i, -2600 + i * 17.5, .07, 420, 0); }
// mata: árvores em grupos e na beira da área de salto
const ARV = [];
for (let c = 0; c < 46; c++) { let cx, cz; do { cx = (rnd() - .5) * 3400; cz = (rnd() - .5) * 3400; } while (fora(cx, cz, 60) || perto(cx, cz, RIO, 60) || Math.hypot(cx - CIDADE.x, cz - CIDADE.z) < 260); const r = 30 + rnd() * 60; for (let i = 0; i < 46; i++) { const a = rnd() * PI * 2, d = Math.sqrt(rnd()) * r; ARV.push([cx + Math.cos(a) * d, cz + Math.sin(a) * d, .8 + rnd() * .7]); } }
for (let i = 0; i < 260; i++) { const a = rnd() * PI * 2, d = Math.sqrt(rnd()) * 70; ARV.push([-270 + Math.cos(a) * d * .8, 40 + Math.sin(a) * d, .9 + rnd() * .6]); } // mata a oeste, onde o paraquedas desgovernado iria cair
for (let i = 0; i < 180; i++) { const lado = i % 4, q = rnd(); const x = lado < 2 ? -180 + q * 360 : (lado === 2 ? -182 : 182) + (rnd() - .5) * 6, z = lado < 2 ? (lado ? -152 : 152) + (rnd() - .5) * 6 : -150 + q * 300; if (Math.abs(x - 40) < 8 && z > 140) continue; ARV.push([x, z, .7 + rnd() * .5]); }
RIO.forEach((p, i) => { if (i % 3 === 0 && Math.abs(p.x) < 2400) ARV.push([p.x + (rnd() - .5) * 70, p.z + (i % 2 ? 34 : -34) + (rnd() - .5) * 10, .7 + rnd() * .5]); });
{ const n = ARV.length, TR = inst(new THREE.CylinderGeometry(.3, .45, 1, 6).translate(0, .5, 0), mat(0x6b4a2c), n), CO = inst(new THREE.IcosahedronGeometry(1, 0), mat(0xffffff, { flatShading: true }), n * 2);
  ARV.forEach(([x, z, e], i) => { const s = e * 5; pose(TR, i, x, 0, z, 0, s * .22, s * 1.1, s * .22); pose(CO, i * 2, x, s * 1.45, z, i, s * .75, s * .62, s * .75); pose(CO, i * 2 + 1, x + s * .3, s * 1.85, z + s * .2, i * 2, s * .5, s * .45, s * .5); CO.setColorAt(i * 2, C.set([0x2e8f3e, 0x3aa84a, 0x237a35, 0x4a9a38][i % 4])); CO.setColorAt(i * 2 + 1, C.set([0x3aa84a, 0x2e8f3e, 0x46b254][i % 3])); }); }
// cidadezinha com janelas que acendem à noite
const JAN = [];
{ const n = 300, CA = inst(new THREE.BoxGeometry(1, 1, 1).translate(0, .5, 0), mat(0xffffff, { roughness: .85 }), n), TE = inst(new THREE.ConeGeometry(.75, 1, 4).rotateY(PI / 4).translate(0, .5, 0), mat(0xffffff, { flatShading: true }), n); const CC = [0xf2d9a6, 0xbfe0ef, 0xf2b8a6, 0xf4f4f2, 0xe8d0f0, 0xf6e7b0, 0xcfe6c4], TC = [0xc2502f, 0x8c5a3c, 0xb5482f, 0x5e6a78]; let k = 0;
  for (let i = -9; i <= 9; i++) for (let j = -8; j <= 8; j++) { if (k >= n || (i % 4 === 0) || (j % 4 === 0) || rnd() < .12) continue; const x = CIDADE.x + i * 16 + (rnd() - .5) * 3, z = CIDADE.z + j * 15 + (rnd() - .5) * 3, w = 7 + rnd() * 3, d = 8 + rnd() * 3, h = 3 + rnd() * (Math.abs(i) < 3 && Math.abs(j) < 3 ? 9 : 2.5); pose(CA, k, x, 0, z, 0, w, h, d); CA.setColorAt(k, C.set(CC[k % 7])); pose(TE, k, x, h, z, 0, w * .95, 2.2, d * .95); TE.setColorAt(k, C.set(TC[k % 4])); JAN.push([x, h * .55, z + d / 2 + .05]); k++; } CA.count = TE.count = k; }
pc('igreja_matriz', scene, CIDADE.x + 8, 0, CIDADE.z + 2, 0); pc('caixa_dagua_torre', scene, CIDADE.x - 150, 0, CIDADE.z - 60, 0);
// morros no horizonte
{ const MO = inst(new THREE.IcosahedronGeometry(1, 1), mat(0x6aa860, { flatShading: true, roughness: 1 }), 46, scene, false); for (let i = 0; i < 46; i++) { const a = i / 46 * PI * 2 + rnd() * .1, r = 2300 + rnd() * 700; pose(MO, i, Math.cos(a) * r, -30, Math.sin(a) * r, rnd() * 6, 380 + rnd() * 300, 160 + rnd() * 220, 380 + rnd() * 260); MO.setColorAt(i, C.set(0x6aa860).offsetHSL((rnd() - .5) * .05, 0, (rnd() - .5) * .1)); } }
// sítios com celeiro, vacas e cavalos
pc('celeiro', scene, 330, 0, -40, -.4); pc('casa_sitio', scene, 300, 0, 30, -1.2); pc('celeiro', scene, -360, 0, -60, .9); pc('casa_sitio', scene, 260, 0, -330, .3);
[[150, -95, .4], [138, -110, 1.9], [160, -118, 3], [128, -86, 2.4], [146, 96, -1], [132, 108, .6]].forEach(([x, z, r]) => pc('vaca', scene, x, 0, z, r));
pc('cavalo', scene, 120, 0, 120, .8); pc('cavalo', scene, 108, 0, 112, 2.2);

// área de salto -----------------------------------------------------------------------------------------------------------
plano(364, 304, GR, 0, .02, 0);
plano(620, 22, 0x86c96f, 0, .04, -62); { const I = inst(new THREE.BoxGeometry(6, .02, .5), mat(0xf4f4f2), 30, scene, false); for (let i = 0; i < 30; i++) pose(I, i, -290 + i * 20, .05, -62, 0); }
// cerca em volta
{ const L = []; for (let x = -180; x <= 180; x += 3.2) { L.push([x, -150]); if (Math.abs(x - 40) > 6) L.push([x, 150]); } for (let z = -147; z < 150; z += 3.2) { L.push([-180, z]); L.push([180, z]); } const P = inst(new THREE.BoxGeometry(.14, 1.3, .14).translate(0, .65, 0), mat(0x9a6a3e), L.length); L.forEach(([x, z], i) => pose(P, i, x, 0, z, 0)); [[-180, -150, 180, -150], [-180, 150, 34, 150], [46, 150, 180, 150], [-180, -150, -180, 150], [180, -150, 180, 150]].forEach(([a, b, c, d]) => [.6, 1.1].forEach(y => { const m = B(scene, Math.hypot(c - a, d - b), .08, .05, 0xb07d4c, (a + c) / 2, y, (b + d) / 2, .01); m.rotation.y = -Math.atan2(d - b, c - a); })); }
// lona de dobragem
plano(12.6, 7.6, 0x3b4656, 0, .04, 0); plano(12, 7, 0x62778f, 0, .045, 0);
// hangar em arco aberto para a lona
const HG = new THREE.Group(); add(HG); HG.position.set(-4, 0, -27);
{ const g = HG, R = 11, L = 24; const f = new THREE.Shape(); f.absarc(0, 0, R, 0, PI, false); f.absarc(0, 0, R - .3, PI, 0, true); const ar = add(sh(new THREE.Mesh(new THREE.ExtrudeGeometry(f, { depth: L, bevelEnabled: false, curveSegments: 28 }), mat(0xc9d0d8, { roughness: .45, metalness: .45, side: 2 }))), g); ar.position.z = -L / 2;
  for (let i = 0; i <= 8; i++) { const m = add(new THREE.Mesh(new THREE.TorusGeometry(R + .05, .12, 6, 28, PI), mat(0x8a96a3, { roughness: .4, metalness: .5 })), g); m.position.z = -L / 2 + i * L / 8; }
  const fu = add(new THREE.Mesh(new THREE.CircleGeometry(R - .2, 28, 0, PI), mat(0xb8c0c9, { side: 2 })), g); fu.position.z = -L / 2 + .1; plano(2 * R - .6, L, 0x9a9da3, 0, .05, 0, g);
  { const m = add(new THREE.Mesh(new THREE.TorusGeometry(R + .05, .32, 8, 32, PI), mat(0xff6a1a, { roughness: .5 })), g); m.position.z = L / 2; }
  [-1, 1].forEach(s => { const p = B(g, 4.2, 6.6, .25, 0x8fa3b8, s * (R + 2.3), 3.3, L / 2 + .45, .03); for (let i = 0; i < 6; i++) B(p, .08, 6.4, .1, 0x6f8399, -1.8 + i * .72, 0, .15, .01); B(g, 6.4, .25, .3, 0x5e6a78, s * (R + 1.2), .12, L / 2 + .45, .01); B(g, 6.4, .2, .3, 0x5e6a78, s * (R + 1.2), 6.7, L / 2 + .45, .01); });
  const fd = add(new THREE.Mesh(new THREE.CircleGeometry(R - .35, 28, 0, PI), mat(0x3a4250, { side: 2, roughness: 1 })), g); fd.position.z = -L / 2 + .3;
  for (let i = 0; i < 4; i++) { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(4.6, 3.6), mat(0x4a5a6e, { roughness: .9 })), g); m.rotation.x = -PI / 2; m.position.set(-6 + i * 4, .07, -4); }
  [[-7, -8], [6, -6], [7.5, 2]].forEach(([x, z], i) => { const p = PC.novo('personagem', { capacete: false, cinto: false, camisa: [0xd8352f, 0x3fa45a, 0xffc21a][i], camisa2: 0x333844 }); p.position.set(x, .05, z); p.rotation.y = i * 1.4; g.add(p); });
  pc('veiculo_aviao_pequeno', g, 2.5, .05, -6, 2.6, { cor: 0xf2f2ee, cor2: 0x2f7fd6 }); }
const LUZ_HG = new THREE.PointLight(0xffe2b0, 0, 40); LUZ_HG.position.set(-4, 8, -22); add(LUZ_HG);
const AVP = pc('veiculo_aviao_pequeno', scene, 20, 0, -30, -.9, { cor: 0xf2f2ee, cor2: 0xd8452f });
pc('casa_simples', scene, -27, 0, -9, .35, { cor: 0xf2c879 }); B(scene, 9, .2, 4, 0xa8703f, -25.5, .1, -2.6, .02);
[[-34, 12, 'veiculo_sedan', 0xd8352f], [-38, 15, 'veiculo_hatch', 0x2f7fd6], [-30, 17, 'veiculo_suv', 0xf4f4f2], [-42, 9, 'veiculo_sedan', 0x3fa45a]].forEach(([x, z, n, c]) => pc(n, scene, x, 0, z, PI / 2 + .1, { cor: c }));
// biruta
const BIR = new THREE.Group(); add(BIR); BIR.position.set(-13, 0, 8); { const m = add(cil(.06, .08, 6, 0xd8dde3, 10), BIR); m.position.y = 3; const c = new THREE.Group(); c.position.set(0, 5.8, 0); BIR.add(c); for (let i = 0; i < 4; i++) { const s = add(new THREE.Mesh(new THREE.CylinderGeometry(.42 - i * .07, .35 - i * .07, .55, 14, 1, true), mat(i % 2 ? 0xf4f4f2 : 0xff6a1a, { side: 2 })), c); s.rotation.x = -PI / 2; s.position.z = -.3 - i * .55; } BIR.saco = c; }
// alvo de pouso
{ const d = (r, c, y) => { const m = add(new THREE.Mesh(new THREE.CircleGeometry(r, 48), mat(c, { roughness: 1 }))); m.rotation.x = -PI / 2; m.position.set(TG.x, y, TG.z); m.receiveShadow = true; return m; }; d(6, 0xd8c9a3, .05); d(3, 0xf4f4f2, .055); d(2.7, 0xd8c9a3, .06); d(.9, 0xff6a1a, .065); }
// bandeiras de vela perto do alvo
const BAND = [[TG.x + 7, TG.z + 9, 0xff6a1a], [TG.x + 9.5, TG.z + 6, 0x2f7fd6], [TG.x + 11, TG.z + 2.5, 0xffc21a]].map(([x, z, c]) => { const g = new THREE.Group(); g.position.set(x, 0, z); add(g); add(cil(.03, .03, 4, 0x2a2d33, 8), g).position.y = 2; const p = add(new THREE.Mesh(new THREE.PlaneGeometry(.8, 2.6, 4, 1).translate(.4, 0, 0), mat(c, { side: 2 })), g); p.position.y = 2.6; g.p = p; return g; });
// público e dobradores
const gente = (g, x, y, z, ry, o = {}) => pc('personagem', g, x, y, z, ry, { capacete: false, cinto: false, camisa: [0xd8352f, 0x2f7fd6, 0xffc21a, 0x3fa45a, 0xe8683f, 0x8a5bc4][Math.floor(rnd() * 6)], camisa2: 0x333844, calca: [0x2b3a67, 0x3a3f4a, 0x6b5a45][Math.floor(rnd() * 3)], cabelo: [0x3a2a1e, 0x15110e, 0x8a5a33][Math.floor(rnd() * 3)], pele: [0xdca77f, 0xb5805a, 0x8a5a3c, 0xe8c4a0][Math.floor(rnd() * 4)], ...o });
const PUB = [gente(scene, -19, 0, -4, .9), gente(scene, -18, 0, -2.6, 1.6), gente(scene, -21.5, 0, -1.8, 1.2), gente(scene, 14, 0, -14, -2.2), gente(scene, 9, 0, 8.5, 2.8)];
AUTO.push(t => PUB.forEach((p, i) => { p.r.respira(t + i); p.r.anda(0, 0); p.rotation.y += Math.sin(t * .7 + i) * .002; }));
const AMI = [gente(scene, TG.x - 6, 0, TG.z + 1, .9), gente(scene, TG.x + 6, 0, TG.z - 1, -.8), gente(scene, TG.x + 4.5, 0, TG.z + 6, .4)];
// luzes da noite: pista, varal de lâmpadas, postes e janelas
const NOITE_M = [];
{ const n = 2 * 42, I = inst(new THREE.SphereGeometry(.22, 8, 6), brilho(0xffd27a), n, scene, false); for (let i = 0; i < 42; i++) { pose(I, i * 2, -300 + i * 14.6, .25, -62 - 11.6, 0); pose(I, i * 2 + 1, -300 + i * 14.6, .25, -62 + 11.6, 0); } NOITE_M.push(I); }
{ const pts = []; const a = new THREE.Vector3(-13, 4.5, -15), b = new THREE.Vector3(-23, 4, -6); for (let i = 0; i <= 26; i++) { const q = i / 26; pts.push(new THREE.Vector3().lerpVectors(a, b, q).add(V1.set(0, -Math.sin(q * PI) * 1.2, 0))); } const I = inst(new THREE.SphereGeometry(.09, 8, 6), brilho(0xffe08a), pts.length, scene, false); pts.forEach((p, i) => pose(I, i, p.x, p.y, p.z, 0)); NOITE_M.push(I); B(scene, .1, 4.5, .1, 0x4a4d55, -23, 2.25, -6, .01); }
{ const I = inst(new THREE.SphereGeometry(.14, 8, 6), brilho(0xffe8b0), 16, scene, false); for (let i = 0; i < 16; i++) { const a = i / 16 * PI * 2; pose(I, i, TG.x + Math.cos(a) * 6.1, .12, TG.z + Math.sin(a) * 6.1, 0); } NOITE_M.push(I); }
{ const I = inst(new THREE.BoxGeometry(1.6, 1.1, .1), brilho(0xffc96a), JAN.length, scene, false); JAN.forEach(([x, y, z], i) => pose(I, i, x, y, z, 0)); NOITE_M.push(I); }
const POSTE = [[-15, -12], [2, -15], [48, 2], [-14, 14]].map(([x, z]) => { const g = new THREE.Group(); g.position.set(x, 0, z); add(g); add(cil(.08, .1, 7, 0x6b7280, 10), g).position.y = 3.5; B(g, .7, .2, .4, 0x3a3f4a, 0, 7, 0, .03); const l = add(new THREE.Mesh(new THREE.BoxGeometry(.6, .05, .32), brilho(0x555555)), g); l.position.y = 6.88; g.l = l; return g; });
const PL = [new THREE.PointLight(0xffe2b0, 0, 60), new THREE.PointLight(0xffe2b0, 0, 60)]; PL[0].position.set(TG.x, 9, TG.z); PL[1].position.set(0, 8, 4); PL.forEach(p => add(p));
const EST = (() => { const n = 700, P = new Float32Array(n * 3); for (let i = 0; i < n; i++) { const a = rnd() * PI * 2, e = .08 + rnd() * 1.4; P[i * 3] = Math.cos(a) * Math.cos(e) * 3600; P[i * 3 + 1] = Math.sin(e) * 3600; P[i * 3 + 2] = Math.sin(a) * Math.cos(e) * 3600; } const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(P, 3)); const p = add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0xffffff, size: 2.2, sizeAttenuation: false, fog: false, transparent: true, opacity: 0 }))); return p; })();

// nuvens longe dos pontos de salto ---------------------------------------------------------------------------------
const SALTOS = [[-60, 300, 80], [150, 370, -120], [-150, 470, 40], [60, 380, -40], [-110, 90, 60], [120, 350, -80], [-240, 600, 140], [0, 10, 0], [26, 30, 50]];
{ let k = 0, tent = 0; while (k < 34 && tent++ < 900) { const x = (rnd() - .5) * 2400, y = 160 + rnd() * 460, z = (rnd() - .5) * 2400; if (SALTOS.some(([a, b, c]) => Math.hypot(x - a, (y - b) * 1.6, z - c) < 170)) continue; const n = PC.novo('nuvem_lowpoly'); const s = 14 + rnd() * 18; n.scale.set(s, s * .7, s); n.position.set(x, y, z); n.rotation.y = rnd() * 6; n.traverse(o => { if (o.isMesh) o.castShadow = false; }); add(n); k++; } }

// velame: duas peles de náilon com paredes (células), abertas na frente -----------------------------------------------
const NC = 9, NU = NC * 8, NV = 16, SPAN = 7.4, CORDA = 2.8, V0 = .12;
const yt = v => .2969 * Math.sqrt(v) - .126 * v - .3516 * v * v + .2843 * v * v * v - .1036 * v * v * v * v;
const superficie = (u, v, topo, s, t, out) => {
  const sx = SPAN / 2 * (.16 + .84 * s.esp), a = u * .62 * s.arc, d0 = u * sx; let X = d0, Y = 0; if (Math.abs(a) > 1e-4) { const R = d0 / a; X = R * Math.sin(a); Y = -R * (1 - Math.cos(a)); }
  const nx = Math.sin(a), ny = Math.cos(a), c = (u + 1) / 2 * NC, f = c - Math.floor(c), bo = Math.sin(PI * f), k = s.k, w = 1 - k;
  let d = topo ? .012 + CORDA * 1.55 * yt(v) * k + .1 * k * bo * (1 - .5 * v) + (v < .16 ? .16 * k * (1 - v / .16) ** 2 : 0) : -.012 - CORDA * .32 * yt(v) * k - .035 * k * bo;
  d += w * s.am * (.07 * Math.sin(u * 23 + v * 7 + t * 2.3) + .04 * Math.sin(u * 41 - v * 13)) + s.flap * .3 * Math.sin(u * 7 - t * 11 + v * 4);
  let Z = CORDA / 2 - v * CORDA; const br = u > 0 ? s.bP : s.bN; if (v > .55 && br > 0) { const q = (v - .55) / .45, e = br * Math.pow(Math.abs(u), .6) * q * q; d -= e * .95; Z += e * .3; }
  out[0] = X + nx * d; out[1] = Y + ny * d; out[2] = Z;
};
const velame = cores => {
  const g = new THREE.Group(); g.visible = false; const st = g.st = { k: 1, esp: 1, arc: 1, bP: 0, bN: 0, flap: 0, am: 1 }; let tA = 0;
  const grade = () => { const gg = new THREE.BufferGeometry(), P = new Float32Array((NU + 1) * (NV + 1) * 3), I = []; for (let i = 0; i < NU; i++) for (let j = 0; j < NV; j++) { const a = i * (NV + 1) + j, b = a + NV + 1; I.push(a, b, a + 1, b, b + 1, a + 1); } gg.setIndex(I); gg.setAttribute('position', new THREE.BufferAttribute(P, 3)); gg.setAttribute('color', new THREE.BufferAttribute(new Float32Array(P.length), 3)); return gg; };
  const mt = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .55, side: THREE.DoubleSide }), gT = grade(), gB = grade();
  const nr = NC + 1, PR = new Float32Array(nr * (NV + 1) * 2 * 3), IR = []; for (let r = 0; r < nr; r++) for (let j = 0; j < NV; j++) { const a = (r * (NV + 1) + j) * 2; IR.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); }
  const gR = new THREE.BufferGeometry(); gR.setIndex(IR); gR.setAttribute('position', new THREE.BufferAttribute(PR, 3)); gR.setAttribute('color', new THREE.BufferAttribute(new Float32Array(PR.length), 3));
  [gT, gB, gR].forEach(q => add(sh(new THREE.Mesh(q, mt)), g));
  const cc = cores.map(c => new THREE.Color(c)), cT = gT.attributes.color.array, cB = gB.attributes.color.array, cR = gR.attributes.color.array;
  for (let i = 0; i <= NU; i++) { const c0 = cc[Math.min(Math.floor(i / (NU / NC)), NC - 1)]; for (let j = 0; j <= NV; j++) { const q = (i * (NV + 1) + j) * 3; cT[q] = c0.r; cT[q + 1] = c0.g; cT[q + 2] = c0.b; cB[q] = c0.r * .7; cB[q + 1] = c0.g * .7; cB[q + 2] = c0.b * .7; } }
  for (let q = 0; q < cR.length; q += 3) { cR[q] = .86; cR[q + 1] = .86; cR[q + 2] = .9; }
  const P3 = [0, 0, 0];
  g.atualiza = t => { tA = t; const pT = gT.attributes.position.array, pB = gB.attributes.position.array;
    for (let i = 0; i <= NU; i++) { const u = -1 + 2 * i / NU; for (let j = 0; j <= NV; j++) { const q = (i * (NV + 1) + j) * 3; superficie(u, j / NV, 1, st, t, P3); pT[q] = P3[0]; pT[q + 1] = P3[1]; pT[q + 2] = P3[2]; superficie(u, V0 + (1 - V0) * j / NV, 0, st, t, P3); pB[q] = P3[0]; pB[q + 1] = P3[1]; pB[q + 2] = P3[2]; } }
    for (let r = 0; r < nr; r++) { const u = -1 + 2 * r / NC; for (let j = 0; j <= NV; j++) { const v = V0 + (1 - V0) * j / NV, q = ((r * (NV + 1) + j) * 2) * 3; superficie(u, v, 1, st, t, P3); PR[q] = P3[0]; PR[q + 1] = P3[1] - .02; PR[q + 2] = P3[2]; superficie(u, v, 0, st, t, P3); PR[q + 3] = P3[0]; PR[q + 4] = P3[1] + .01; PR[q + 5] = P3[2]; } }
    [gT, gB, gR].forEach(q => { q.attributes.position.needsUpdate = true; q.computeVertexNormals(); q.computeBoundingSphere(); }); };
  g.revela = (kb, kt, kr) => { gB.setDrawRange(0, Math.floor(clamp(kb) * NU) * NV * 6); gT.setDrawRange(0, Math.floor(clamp(kt) * NU) * NV * 6); gR.setDrawRange(0, Math.floor(clamp(kr) * nr) * NV * 6); };
  g.ponto = (u, v, out) => { superficie(u, v, 0, st, tA, P3); out.set(P3[0], P3[1], P3[2]); return g.localToWorld(out); };
  g.zera = () => { Object.assign(st, { k: 1, esp: 1, arc: 1, bP: 0, bN: 0, flap: 0, am: 1 }); g.position.set(0, 6.6, 0); g.rotation.set(0, 0, 0); g.scale.setScalar(1); g.revela(1, 1, 1); };
  return g;
};
const COR_P = [0x1f5fd0, 0xf4f4f2, 0xff6a1a, 0xff6a1a, 0xffc21a, 0xff6a1a, 0xff6a1a, 0xf4f4f2, 0x1f5fd0], COR_R = [0xf4f4f2, 0x8fc8f0, 0xf4f4f2, 0x8fc8f0, 0xf4f4f2, 0x8fc8f0, 0xf4f4f2, 0x8fc8f0, 0xf4f4f2];

// o saltador: macacão, capacete, arnês, container com abas, pino, extrator e punhos -----------------------------------
const zera = r => { [r.be, r.bd, r.pe, r.pd].forEach(m => { m.j.rotation.set(0, 0, 0); m.k.rotation.set(0, 0, 0); }); r.cab.rotation.set(0, 0, 0); r.cab.parent.position.y = .95; };
const saltador = (cor, capa) => {
  const p = PC.novo('personagem', { capacete: false, cinto: false, camisa: cor, camisa2: escuro(cor), calca: cor, sapato: 0x2a2d33, escala: .86 }), r = p.r, tr = r.cab.parent, cab = r.cab;
  const cp = add(sh(new THREE.Mesh(new THREE.SphereGeometry(.27, 18, 10, 0, PI * 2, 0, PI * .52), mat(capa, { roughness: .35 }))), cab); cp.position.set(0, .1, -.02); cp.scale.set(1, 1, 1.06);
  H.B(cab, .42, .08, .05, 0x1d2630, 0, .19, .2, .03, { roughness: .12, metalness: .5 }); H.B(cab, .1, .06, .06, 0xff6a1a, 0, .3, .2, .02);
  H.B(tr, .52, .05, .32, escuro(cor, .55), 0, .12, 0, .02); [-1, 1].forEach(s => H.B(tr, .03, .5, .32, 0xf4f4f2, s * .255, .3, 0, .01));
  const KC = H.G(tr, 0, .3, -.27); H.B(KC, .46, .62, .2, 0x22304e, 0, 0, 0, .06); H.B(KC, .47, .035, .205, 0xff6a1a, 0, .3, 0, .015); H.B(KC, .47, .035, .205, 0xff6a1a, 0, -.3, 0, .015);
  const resv = H.G(KC, 0, .3, -.1); H.B(resv, .42, .2, .035, 0x2c3d63, 0, -.1, 0, .02); H.B(resv, .3, .025, .04, 0xff6a1a, 0, -.19, 0, .01);
  const recheio = H.B(KC, .36, .4, .08, 0xff6a1a, 0, -.1, -.08, .03);
  const ab = [];
  { const a = H.G(KC, 0, .08, -.105); H.B(a, .4, .19, .025, 0x2a3a60, 0, -.095, 0, .01); a.abre = 1.8; a.eixo = 'x'; ab.push(a); }
  { const a = H.G(KC, 0, -.29, -.105); H.B(a, .4, .19, .025, 0x2a3a60, 0, .095, 0, .01); a.abre = -1.8; a.eixo = 'x'; ab.push(a); }
  { const a = H.G(KC, -.21, -.1, -.11); H.B(a, .2, .36, .025, 0x324671, .1, 0, 0, .01); a.abre = 1.9; a.eixo = 'y'; ab.push(a); }
  { const a = H.G(KC, .21, -.1, -.115); H.B(a, .2, .36, .025, 0x324671, -.1, 0, 0, .01); a.abre = -1.9; a.eixo = 'y'; ab.push(a); }
  const pino = H.G(KC, 0, -.1, -.135); { const m = H.C(pino, .011, .011, .11, 0xe8ecf0, 0, 0, 0, 8, H.metal); m.rotation.z = PI / 2; H.T(pino, .025, .006, 0xe8ecf0, -.07, 0, 0); }
  const boc = H.E(KC, .04, 0xffc21a, .16, -.34, -.06);
  const arn = [];[-1, 1].forEach(s => arn.push(H.B(tr, .07, .62, .03, 0x1b2233, s * .14, .3, .17, .01))); arn.push(H.B(tr, .34, .05, .03, 0x1b2233, 0, .42, .18, .01));
  [r.pe, r.pd].forEach(l => { const m = H.T(l.j, .13, .028, 0x1b2233, 0, -.12, 0); m.rotation.x = PI / 2; arn.push(m); });
  const corta = H.B(tr, .1, .07, .05, 0xd8352f, -.15, .26, .2, .02), puxa = H.T(tr, .045, .012, 0xd8dde3, .15, .26, .2);
  const ris = []; [-1, 1].forEach(s => [.05, -.06].forEach(z => ris.push(H.B(tr, .045, .7, .02, 0x1b2233, s * .17, .97, z, .01))));
  const bat = [-1, 1].map(s => H.B(tr, .07, .12, .05, 0xffc21a, s * .17, 1.25, -.08, .01));
  return { p, r, tr, KC, resv, ab, pino, boc, recheio, arn, corta, puxa, ris, bat };
};
const pQueda = (r, t) => { zera(r); const w = Math.sin(t * 9) * .05; r.be.j.rotation.z = -2.05 + w; r.bd.j.rotation.z = 2.05 - w; r.be.k.rotation.z = -1; r.bd.k.rotation.z = 1; r.pe.j.rotation.z = -.28; r.pd.j.rotation.z = .28; r.pe.j.rotation.x = r.pd.j.rotation.x = .25; r.pe.k.rotation.x = r.pd.k.rotation.x = 1.25 + w; r.cab.rotation.x = -.75; };
const pPend = (r, t, pN = 0, pP = 0) => { zera(r); r.be.j.rotation.x = -2.95 + pN * 1.7; r.bd.j.rotation.x = -2.95 + pP * 1.7; r.be.j.rotation.z = -.12; r.bd.j.rotation.z = .12; r.be.k.rotation.x = -.15 - pN * .7; r.bd.k.rotation.x = -.15 - pP * .7; const b = Math.sin(t * 1.7) * .06; r.pe.j.rotation.x = -.45 + b; r.pd.j.rotation.x = -.4 - b; r.pe.k.rotation.x = r.pd.k.rotation.x = .35; };
const pDebate = (r, t) => { zera(r); r.be.j.rotation.x = -2.5 + Math.sin(t * 11) * .5; r.bd.j.rotation.x = -2.4 + Math.cos(t * 10) * .55; r.be.j.rotation.z = -.5 - Math.sin(t * 7) * .3; r.bd.j.rotation.z = .5 + Math.cos(t * 8) * .3; r.be.k.rotation.x = -.6; r.bd.k.rotation.x = -.6; r.pe.j.rotation.x = Math.sin(t * 8) * .7; r.pd.j.rotation.x = -Math.sin(t * 8) * .7; r.pe.k.rotation.x = .6 + Math.sin(t * 9) * .4; r.pd.k.rotation.x = .6 - Math.sin(t * 9) * .4; r.cab.rotation.x = -.4 + Math.sin(t * 6) * .2; };
const pSentado = (r, t) => { zera(r); r.pe.j.rotation.x = r.pd.j.rotation.x = -1.45; r.pe.k.rotation.x = r.pd.k.rotation.x = 1.3 + Math.sin(t * 3) * .05; r.be.j.rotation.x = -.6; r.bd.j.rotation.x = -.4; r.be.j.rotation.z = -.4; r.bd.j.rotation.z = .5; r.be.k.rotation.x = -.5; r.bd.k.rotation.x = -.5; };
const pFesta = (r, t, f = 0) => { zera(r); r.be.j.rotation.x = -2.8 + Math.sin(t * 9 + f) * .25; r.bd.j.rotation.x = -2.8 + Math.cos(t * 9 + f) * .25; r.be.j.rotation.z = -.35; r.bd.j.rotation.z = .35; r.respira(t); };

const SIS = new THREE.Group(); add(SIS); const JP = H.G(SIS); const JJ = saltador(0x2f54d6, 0xf4f4f2); JP.add(JJ.p); JJ.p.position.y = -1.12;
const VEL = velame(COR_P), VR = velame(COR_R); SIS.add(VEL); SIS.add(VR);
// cordas: quatro fileiras por parede e linhas de freio até os batoques
const LP = []; for (let r = 0; r <= NC; r++) { const u = -1 + 2 * r / NC; [.16, .4, .62, .86].forEach((v, j) => LP.push({ u, v, s: u < 0 ? -1 : 1, tras: j > 1 })); }
[-1, -.8, -.6, -.4, .4, .6, .8, 1].forEach(u => LP.push({ u, v: 1, s: u < 0 ? -1 : 1, freio: true }));
const LIN = inst(G_CIL, mat(0x5b616b, { roughness: .6 }), LP.length, scene, false);
const ponta = (s, tras, pull, out) => JJ.tr.localToWorld(out.set(s * .17, 1.32 - pull * .5, tras ? -.06 : .05));
// slider: pano com quatro argolas
const SLD = new THREE.Group(); add(SLD); { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(1, .85).rotateX(-PI / 2), mat(0xffd21a, { side: 2, roughness: .5 })), SLD); m.castShadow = true;[[-.5, -.42], [.5, -.42], [-.5, .42], [.5, .42]].forEach(([x, z]) => { const a = add(new THREE.Mesh(new THREE.TorusGeometry(.06, .018, 8, 18), mat(0xd8dde3, H.metal)), SLD); a.rotation.x = PI / 2; a.position.set(x, 0, z); }); B(SLD, 1, .02, .05, 0xff6a1a, 0, .005, 0, .01); }
// pano embolado: fita torcida que sacode, com cordas enroladas
const NST = 44, ST = new THREE.Group(); add(ST);
const gST = new THREE.BufferGeometry(); { const P = new Float32Array((NST + 1) * 2 * 3), Cc = new Float32Array(P.length), I = []; for (let i = 0; i < NST; i++) { const a = i * 2; I.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } for (let i = 0; i <= NST; i++) { const c = new THREE.Color(COR_P[Math.floor(i / 5) % NC]); [0, 1].forEach(s => { Cc[(i * 2 + s) * 3] = c.r; Cc[(i * 2 + s) * 3 + 1] = c.g; Cc[(i * 2 + s) * 3 + 2] = c.b; }); } gST.setIndex(I); gST.setAttribute('position', new THREE.BufferAttribute(P, 3)); gST.setAttribute('color', new THREE.BufferAttribute(Cc, 3)); }
add(sh(new THREE.Mesh(gST, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: .55, side: 2 }))), ST);
const STL = inst(G_CIL, mat(0x2c3038), 10, ST, false);
const stP = (q, t, L, out) => { const y = q * L; return out.set(Math.sin(q * 5 - t * 17) * .5 * q, y, Math.cos(q * 4 - t * 13) * .4 * q); };
const atualizaST = (t, L) => { const P = gST.attributes.position.array; for (let i = 0; i <= NST; i++) { const q = i / NST; stP(q, t, L, V1); const w = (.12 + 1.05 * Math.pow(Math.sin(PI * Math.min(q * 1.25, 1)), .6)) * clamp(q / .08), tw = q * 7 + t * 10; const dx = Math.cos(tw) * w / 2, dz = Math.sin(tw) * w / 2; P.set([V1.x + dx, V1.y, V1.z + dz, V1.x - dx, V1.y, V1.z - dz], i * 6); } gST.attributes.position.needsUpdate = true; gST.computeVertexNormals(); gST.computeBoundingSphere();
  for (let i = 0; i < 10; i++) { const s = i % 2 ? 1 : -1; V2.set(s * .14, -.05, (i % 4 < 2 ? .05 : -.05)); stP(.2 + (i % 5) * .07, t, L, V4); V4.x += Math.sin(i * 2.3 + t * 6) * .15; ligaI(STL, i, V2, V4, .012); } STL.instanceMatrix.needsUpdate = true; };
// extrator (paraquedinha), fita de ligação, saco do velame e pino solto
const PCH = new THREE.Group(); SIS.add(PCH); { add(sh(new THREE.Mesh(new THREE.SphereGeometry(.48, 18, 8, 0, PI * 2, 0, PI / 2), mat(0xff6a1a, { side: 2, roughness: .5 }))), PCH); const m = add(new THREE.Mesh(new THREE.CylinderGeometry(.48, .22, .45, 18, 1, true), mat(0x30343c, { side: 2, transparent: true, opacity: .55 })), PCH); m.position.y = -.22; H.E(PCH, .06, 0x1f5fd0, 0, .49, 0); }
const BRI = add(new THREE.Mesh(G_CIL, mat(0xf4f4f2))); const BAG = new THREE.Group(); SIS.add(BAG); B(BAG, .36, .3, .22, 0xff6a1a, 0, 0, 0, .05); B(BAG, .37, .05, .23, 0x1f5fd0, 0, .1, 0, .01);
const PINV = new THREE.Group(); add(PINV); { const m = add(cil(.011, .011, .11, 0xe8ecf0, 8, H.metal), PINV); m.rotation.z = PI / 2; }
// vento: riscos passando pelo saltador em queda e riscos que entram no velame no chão
const NVT = 70, VT = inst(new THREE.BoxGeometry(.016, 1.8, .016), brilho(0xffffff, { transparent: true, opacity: .28 }), NVT, scene, false); const VTP = Array.from({ length: NVT }, () => [(rnd() - .5) * 16, rnd() * 24, (rnd() - .5) * 16]);
const NVG = 46, VG = inst(new THREE.BoxGeometry(.03, .03, 2.6), brilho(0xffffff, { transparent: true, opacity: .55 }), NVG, scene, false); const VGP = Array.from({ length: NVG }, () => [(rnd() - .5) * 7.4, .15 + rnd() * .5, rnd() * 12]);
// avião de salto em voo, com a porta aberta do lado direito
const AV = new THREE.Group(); add(AV); const AVM = PC.novo('veiculo_aviao_pequeno', { cor: 0xf2f2ee, cor2: 0x2f7fd6 }); AV.add(AVM); AVM.rotation.y = PI / 2; B(AVM, .05, .95, .95, 0x15181d, -.66, 1.3, .35, .02);
// teste do pano reto: lençol plano com saco de areia que balança
const TESTE = new THREE.Group(); add(TESTE); const gLen = new THREE.PlaneGeometry(3.2, 3.2, 12, 12).rotateX(-PI / 2), LEN0 = gLen.attributes.position.array.slice();
add(sh(new THREE.Mesh(gLen, mat(0xff6a1a, { side: 2, roughness: .55 }))), TESTE); const SACO = B(TESTE, .5, .6, .4, 0x9a7a52, 0, -3.1, 0, .12); B(TESTE, .52, .06, .42, 0x6b5236, 0, -2.82, 0, .02);
[[-1.6, -1.6], [1.6, -1.6], [-1.6, 1.6], [1.6, 1.6]].forEach(([x, z]) => { const m = add(new THREE.Mesh(G_CIL, mat(0x2c3038)), TESTE); liga(m, V1.set(x, 0, z), V2.set(0, -2.8, 0), .012); });
// mesa de costura com a costureira
const COST = new THREE.Group(); add(COST); COST.position.set(-7.8, 0, 1.4); COST.rotation.y = PI / 2;
B(COST, 1.7, .06, .8, 0xc99a68, 0, .76, 0, .01);[[-.78, -.34], [.78, -.34], [-.78, .34], [.78, .34]].forEach(([x, z]) => B(COST, .05, .74, .05, 0x5e3b22, x, .37, z, .01));
const MAQ = new THREE.Group(); MAQ.position.set(.1, .79, -.05); COST.add(MAQ); B(MAQ, .5, .1, .22, 0xf4f4f2, 0, .05, 0, .03); B(MAQ, .1, .32, .14, 0xf4f4f2, .2, .26, 0, .03); B(MAQ, .46, .1, .14, 0xf4f4f2, .02, .4, 0, .04); B(MAQ, .1, .14, .12, 0xd8352f, -.2, .32, 0, .02); const AGU = add(cil(.006, .006, .14, 0xc9ced4, 6), MAQ); AGU.position.set(-.2, .2, 0); const RODA = add(cil(.07, .07, .03, 0x3a3f4a, 16), MAQ); RODA.rotation.z = PI / 2; RODA.position.set(.27, .36, 0);
B(COST, 1.4, .012, .5, 0xff6a1a, -.2, .8, .05, .002); B(COST, .7, .014, .5, 0x1f5fd0, .5, .801, .1, .002);
const COSTU = gente(COST, 0, 0, .78, PI, { camisa: 0x8a5bc4 }); B(COST, .4, .45, .4, 0x3a3f4a, 0, .22, .9, .04);
AUTO.push(t => { COSTU.r.respira(t); COSTU.r.anda(0, 0); COSTU.r.pe.j.rotation.x = COSTU.r.pd.j.rotation.x = -1.5; COSTU.r.pe.k.rotation.x = COSTU.r.pd.k.rotation.x = 1.5; COSTU.position.y = -.3 + .3; COSTU.r.be.j.rotation.x = -1.1 + Math.sin(t * 6) * .08; COSTU.r.bd.j.rotation.x = -1.2 + Math.cos(t * 6) * .08; COSTU.r.be.k.rotation.x = COSTU.r.bd.k.rotation.x = -.5; COSTU.r.cab.rotation.x = .35; AGU.position.y = .2 + Math.abs(Math.sin(t * 30)) * .04; RODA.rotation.x = t * 12; });
// formação em queda livre no fim (quatro saltadores de mãos dadas)
const FORM = new THREE.Group(); add(FORM); const FJ = [0xd8352f, 0x3fa45a, 0xffc21a, 0x8a5bc4].map((c, i) => { const pv = H.G(FORM); pv.rotation.y = i * PI / 2; const jp = H.G(pv, 0, 0, -1.05); jp.rotation.x = PI / 2; const s = saltador(c, [0xf4f4f2, 0x24272e, 0xff6a1a, 0xf4f4f2][i]); jp.add(s.p); s.p.position.y = -1.12; s.ab.forEach(a => { a.rotation[a.eixo] = 0; }); s.recheio.visible = false; s.ris.forEach(m => m.visible = false); s.bat.forEach(m => m.visible = false); return s; });

// estado de cada quadro ----------------------------------------------------------------------------------------------
const AN = { sis: new THREE.Vector3(), av: new THREE.Vector3(), form: new THREE.Vector3() };
let LA = null, LG = 1, TN = 0, TP = 0, SS = -1, STON = false, STB = new THREE.Vector3(), STD = new THREE.Vector3(0, 1, 0), STL_ = 6.4, PCON = false, BAGON = false, VV = 0, VGON = false, ABAS = 0, PINO = 1, RESV = 0, RISON = false, REC = false, KCON = true, ARN = [1, 1, 1, 1, 1], PINVON = false;
const resetar = () => { JJ.p.visible = true; SIS.visible = true; VEL.visible = VR.visible = false; VEL.zera(); VR.zera(); LA = null; LG = 1; TN = TP = 0; SS = -1; STON = false; STL_ = 6.4; PCON = BAGON = false; VV = 0; VGON = false; AV.visible = false; TESTE.visible = false; FORM.visible = false;
  SIS.rotation.set(0, 0, 0, 'YXZ'); JP.rotation.set(0, 0, 0); JP.position.set(0, 0, 0); ABAS = 0; PINO = 1; RESV = 0; RISON = false; REC = 0; KCON = true; ARN = [1, 1, 1, 1, 1]; PINVON = false; JJ.p.rotation.set(0, 0, 0); };
const naPorta = (t, out) => out.copy(AV.position).add(V4.set(.32, 1.0, 1.0));
const vooAviao = t => t < F(6) ? V1.set(-260 + 34 * (t - F(5)), 470, 40) : V1.set(-160 + 34 * (t - F(6)), 470, -40);
// queda depois de sair do avião: velocidade cresce até abrir, depois cai devagar
const queda6 = (t, out) => { out.copy(vooAviao(T6X)).add(V4.set(.32, 1.0, 1.0)); let vy = 0, x = out.x, y = out.y; const dt = .02; for (let q = T6X; q < t; q += dt) { const a = q - T6X; const vx = 34 * Math.exp(-a / 1.4); const alvo = q < T6R + .3 ? Math.min(9.8 * a, 48) : 48 - 42 * ease(rev(q, T6R + .3, T6R + 1.8)); vy = alvo; x += vx * dt; y -= vy * dt; } return out.set(x, y, out.z); };
const PSI0 = -PI / 2, P7 = new THREE.Vector3(-105, 96, 62);
const PSI1 = (() => { const x = P7.x + Math.sin(PSI0) * 9 * (T7P - F(7)), z = P7.z + Math.cos(PSI0) * 9 * (T7P - F(7)); let p = Math.atan2(TG.x - x, TG.z - z); while (p > PSI0) p -= PI * 2; return p; })();
const psi7 = q => PSI0 + (PSI1 - PSI0) * ease(rev(q, T7P, T7P + 2)) + (q < T7P ? .22 * Math.sin((q - F(7)) * 1.4) : 0);
const flare7 = q => ease(rev(q, T7F, T7F + .4)) * (1 - ease(rev(q, T7F + 1.3, T7F + 1.8)));
const voo7 = (t, out) => { let x = P7.x, z = P7.z; const dt = .02; for (let q = F(7); q < t; q += dt) { const p = psi7(q), sp = 9 * (1 - .5 * flare7(q)); x += Math.sin(p) * sp * dt; z += Math.cos(p) * sp * dt; } return out.set(x, P7.y - 4.4 * (t - F(7)), z); };
const quadro = t => {
  resetar();
  if (t < F(1)) { // abertura: pano embolado, giro e queda
    SIS.position.set(-60, 430 - 36 * t, 80); SIS.rotation.y = t * 3.4; SIS.rotation.z = Math.sin(t * 5) * .12; JP.rotation.x = .3 + Math.sin(t * 3) * .1; pDebate(JJ.r, t); ABAS = 1; PINO = 0; RISON = true; STON = true; VV = 36;
  } else if (t < F(2)) { // pano reto balança; costura das células
    if (t < CI[1].e) { TESTE.visible = true; JJ.p.visible = false; const q = t - F(1), k = rev(t, F(1), CI[1].e + .4); TESTE.position.set(-4, 13.5 - 6 * k, -8); TESTE.rotation.set(Math.sin(q * 1.9) * .18, 0, Math.sin(q * 2.8) * .6); const P = gLen.attributes.position.array; for (let i = 0; i < P.length; i += 3) P[i + 1] = LEN0[i + 1] + Math.sin(LEN0[i] * 1.6 + q * 9) * .22 + Math.cos(LEN0[i + 2] * 1.3 + q * 7) * .15; gLen.attributes.position.needsUpdate = true; gLen.computeVertexNormals(); }
    else { SIS.position.set(0, 1.12, 0); JJ.p.visible = false; VEL.visible = true; VEL.position.set(0, -1.12 + .14, 0); Object.assign(VEL.st, { arc: 0, k: .05 + .65 * ease(rev(t, T1R, T1R + 1.3)), am: .12 }); VEL.revela(ease(rev(t, T1C, T1C + .8)), ease(rev(t, T1K, T1K + .8)), rev(t, T1R, T1R + 1.2)); }
  } else if (t < F(3)) { // murchas e o vento enchendo: vira asa
    SIS.position.set(0, 1.12, 0); JJ.p.visible = false; VEL.visible = true; const km = ease(rev(t, F(2) + .1, T2M + .5)), ke = ease(rev(t, T2E - .1, T2E + 1.1)), kl = ease(rev(t, T2A, T2A + 1.5));
    const kb = .7 - .6 * km; Object.assign(VEL.st, { k: kb + (1 - kb) * ke, arc: kl, am: .4 + .6 * km, flap: .08 * km * (1 - ke) }); VEL.position.set(0, -.98 + kl * 6.6 + Math.sin(t * 1.3) * .1 * kl, 0); VEL.rotation.x = -.12 * kl; VGON = t > T2V;
  } else if (t < F(4)) { // cordas e arnês
    SIS.position.set(0, 1.12, 0); VEL.visible = true; VEL.position.set(Math.sin(t * .9) * .15, 5.62 + Math.sin(t * 1.3) * .1, 0); VEL.rotation.set(-.12, 0, Math.sin(t * .9) * .03); KCON = false;
    const kw = ease(rev(t, F(3), F(3) + 1.8)); JP.position.x = 6 * (1 - kw); if (kw < 1) { zera(JJ.r); JJ.r.anda(t, 1); JJ.p.rotation.y = -PI / 2 * (1 - kw); } else pPend(JJ.r, t, .55, .55);
    LA = VEL; LG = ease(rev(t, T3K, T3K + 1.3)); RISON = LG > 0; ARN = [ease(rev(t, T3F, T3F + .35)), ease(rev(t, T3F + .1, T3F + .45)), ease(rev(t, T3T, T3T + .35)), ease(rev(t, T3P, T3P + .35)), ease(rev(t, T3P + .1, T3P + .45))]; TN = TP = .55;
  } else if (t < F(5)) { // tranco e slider
    SIS.position.set(150, 380 - 16 * (t - F(4)), -120); VEL.visible = true; LA = VEL; RISON = true; ABAS = 1; PINO = 0; PCON = true;
    if (t < T4E) { const ks = ease(rev(t, T4S, T4S + .14)), d = t - T4S; Object.assign(VEL.st, { esp: .12 + .88 * ks, k: .25 + .75 * ks, flap: .25 * (1 - ks) }); const pr = d < 0 ? .9 : .9 * Math.max(0, 1 - d / .22) - Math.sin(clamp(d / .9) * PI * 3) * .35 * (1 - clamp(d / .9)); JP.rotation.x = pr; JP.position.y = d > 0 ? -Math.sin(clamp(d / .35) * PI) * .6 : 0; SIS.rotation.x = d > 0 ? Math.sin(clamp(d / 1.1) * PI * 2.5) * .3 * (1 - clamp(d / 1.1)) : 0; if (d < 0) pQueda(JJ.r, t); else if (d < .7) pDebate(JJ.r, t * 1.6); else pPend(JJ.r, t); VV = d < 0 ? 40 : 6; }
    else { const ks = ease(rev(t, T4D, T4B)); Object.assign(VEL.st, { esp: .12 + .88 * ks, k: .25 + .75 * ks, flap: .2 * (1 - ks) }); SS = ks; JP.rotation.x = .85 * (1 - ks); if (ks < .45) pQueda(JJ.r, t); else pPend(JJ.r, t); VV = 34 * (1 - ks) + 6; }
    PCH.position.set(0, VEL.position.y + 1.5 + Math.sin(t * 3) * .1, -.3);
  } else if (t < F(6)) { // não pode abrir no avião; dobra no container e trava com o pino
    if (t < T5E) { AV.visible = true; AV.position.copy(vooAviao(t)); AV.rotation.z = Math.sin(t * .8) * .03; naPorta(t, SIS.position); pSentado(JJ.r, t); ABAS = 1; PINO = 0; STON = true; STL_ = 5.4 * ease(rev(t, F(5) + .2, F(5) + .9)) + .1; STB.copy(AV.position).add(V4.set(.25, 1.55, .85)); STD.set(-1, .08, .3).normalize(); }
    else { SIS.position.set(0, 1.12, 0); VEL.visible = true; const kc = ease(rev(t, T5D, T5D + .9)), km = ease(rev(t, T5M, T5M + .9)); Object.assign(VEL.st, { k: 1 - .9 * kc, arc: 1 - kc, esp: 1 - .8 * km, flap: .1 * kc * (1 - km) }); VEL.position.set(0, (5.62 - kc * 4.9) * (1 - km) + km * -.05, -1.6 * kc * (1 - km) - .33 * km); VEL.rotation.x = -.12 * (1 - kc); VEL.scale.setScalar(1 - .96 * km); VEL.visible = km < .99;
      LA = VEL; LG = 1 - km; RISON = LG > .02; KCON = t > T5M - .25; ABAS = 1 - ease(rev(t, T5P - .55, T5P - .1)); REC = km; PINO = ease(rev(t, T5P - .05, T5P + .3)); pPend(JJ.r, t, .9 + .1 * km, .9 + .1 * km); JJ.r.be.j.rotation.x = JJ.r.bd.j.rotation.x = -2.95 * (1 - kc) - .2 * kc; JJ.r.respira(t); }
  } else if (t < F(7)) { // saída do avião, extrator, pino, saco e abertura
    AV.visible = true; AV.position.copy(vooAviao(t)); AV.rotation.z = Math.sin(t * .8) * .03; PINO = 1; REC = t < T6I + .15 ? 1 : 0;
    if (t < T6X) { naPorta(t, SIS.position); pSentado(JJ.r, t); }
    else { queda6(t, SIS.position); const kq = ease(rev(t, T6X, T6X + 1)), ko = ease(rev(t, T6R + .3, T6R + 1.6)); JP.rotation.x = PI / 2 * kq * (1 - ko); if (t < T6R + .9) { if (t < T6X + .5) pSentado(JJ.r, t); else pQueda(JJ.r, t); } else pPend(JJ.r, t); VV = t < T6R + .4 ? Math.min(48, 9.8 * (t - T6X)) : 6;
      if (t > T6E && t < T6P + .25) { const k = ease(rev(t, T6E, T6E + .35)); JJ.r.bd.j.rotation.set(.9 * k, 0, 2.05 * (1 - k) + .5 * k); JJ.r.bd.k.rotation.set(0, 0, 0); }
      if (t > T6P) { PCON = true; const k = ease(rev(t, T6P, T6P + .7)); PCH.position.set(.5 + .3 * k, .4 + 3.6 * k, -.2); PCH.rotation.z = (1 - k) * 1.2; }
      if (t > T6I) { PINO = 0; ABAS = ease(rev(t, T6I + .05, T6I + .25)); PINVON = t < T6I + 1.2; const kb = ease(rev(t, T6I + .1, T6I + .6)); BAGON = t < T6R + .45; BAG.position.set(0, .3 + 3 * kb, -.2); PCH.position.set(.2, BAG.position.y + 2.2, -.2); }
      if (t > T6R) { const kl = ease(rev(t, T6R, T6R + .5)), ks = ease(rev(t, T6R + .4, T6R + 1.8)); BAG.position.y = 3.3 + kl * 3; VEL.visible = true; VEL.position.y = 3.3 + kl * 3.3; Object.assign(VEL.st, { esp: .1 + .9 * ks, k: .2 + .8 * ks, flap: .25 * (1 - ks) }); LA = VEL; RISON = true; SS = ks; PCH.position.set(0, VEL.position.y + 1.6, -.3); } } }
  else if (t < F(8)) { // sem controle; batoques
    voo7(t, SIS.position); const p = psi7(t), dp = (psi7(t + .05) - psi7(t - .05)) / .1, fl = flare7(t); SIS.rotation.y = p; SIS.rotation.z = (t < T7P ? Math.sin(t * 2.2) * .14 : 0) - dp * .22; SIS.rotation.x = -fl * .25; VEL.visible = true; LA = VEL; RISON = true;
    const bn = Math.max(ease(rev(t, T7P - .1, T7P + .3)) * (1 - ease(rev(t, T7P + 1.7, T7P + 2.1))) * .95, fl * .85); VEL.st.bN = bn; VEL.st.bP = fl * .85; TN = bn; TP = fl * .85; pPend(JJ.r, t, TN, TP);
  } else if (t < F(9)) { // principal enrosca; corte e reserva
    const dA = t - T8A; SIS.position.set(120, 380 - 30 * (t - F(8)) + (dA > 0 ? 24 * (dA - ease(rev(t, T8A, T8A + 2)) * .9) : 0), -80); RISON = true; ABAS = 1; PINO = 0;
    if (t < T8A + .3) { SIS.rotation.y = (t - F(8)) * 3.4 * (t < T8S ? 1 : Math.max(0, 1 - (t - T8S) * 1.2)); JP.rotation.x = .3; pDebate(JJ.r, t); VV = 32; if (t > T8S - .5 && t < T8S + .4) { const k = ease(rev(t, T8S - .5, T8S - .1)); JJ.r.be.j.rotation.set(-.9 * k - (1 - k) * 2.3, 0, .3 * k); JJ.r.be.k.rotation.set(-1.6 * k, 0, 0); } }
    STON = t < T8S + 1.6; if (t > T8S) { RISON = false; const d = t - T8S; STB.copy(V2.set(-.3 * d, 21 * d, .6 * d)); } RESV = ease(rev(t, T8A, T8A + .2));
    if (t > T8A) { const kl = ease(rev(t, T8A, T8A + .35)), ks = ease(rev(t, T8A + .3, T8A + 1.3)); VR.visible = true; VR.position.y = 1 + 5.6 * kl; Object.assign(VR.st, { esp: .1 + .9 * ks, k: .2 + .8 * ks, flap: .25 * (1 - ks) }); LA = VR; RISON = true; SS = ks; PCON = true; PCH.position.set(0, VR.position.y + 1.6, -.3); JP.rotation.x = .3 * (1 - ks); if (ks > .3) pPend(JJ.r, t); VV = 32 * (1 - ks) + 4; SIS.rotation.y = (T8S - F(8)) * 3.4 * .2; }
  } else { // pouso no alvo, formação e noite
    const kl = rev(t, T9 - .3, T9L), y = 1.12 + 32 * Math.pow(1 - kl, 1.25), z = TG.z + 66 * (1 - kl); SIS.position.set(TG.x, y, z); SIS.rotation.y = PI; VEL.visible = true; LA = VEL; RISON = true;
    const fl = ease(rev(t, T9L - 1.3, T9L - .35)), kc = ease(rev(t, T9L + .1, T9L + 1.4)); VEL.st.bN = VEL.st.bP = fl * (1 - kc); Object.assign(VEL.st, { k: 1 - .85 * kc, arc: 1 - kc, flap: .06 * kc }); VEL.position.set(0, 6.6 - 7.45 * kc, 3.6 * kc); VEL.rotation.x = .6 * kc;
    if (t < T9L) pPend(JJ.r, t, fl, fl); else pFesta(JJ.r, t); SIS.rotation.x = -fl * .2 * (1 - kc);
    FORM.visible = t > T9C - .05 && t < T9V; AN.form.set(-240, 620 - 42 * (t - T9C), 140); FORM.position.copy(AN.form); FORM.rotation.y = (t - T9C) * .35; FJ.forEach((s, i) => { pQueda(s.r, t + i); s.r.be.j.rotation.z = -1.5; s.r.bd.j.rotation.z = 1.5; s.r.be.k.rotation.z = -.3; s.r.bd.k.rotation.z = .3; s.r.fala(t + i, true); });
    VV = t > T9C && t < T9V ? 42 : 0;
  }
  aplica(t);
};
// aplica peças que dependem do estado
const RA = new THREE.Vector3(), RB = new THREE.Vector3();
const aplica = t => {
  AN.sis.copy(SIS.position); AN.av.copy(AV.position); if (AV.visible) AVM.helice.rotation.z = t * 70;
  JJ.KC.visible = KCON; JJ.ab.forEach(a => { a.rotation[a.eixo] = a.abre * ABAS; }); JJ.recheio.visible = KCON && REC > .02 && ABAS > .02; JJ.recheio.scale.setScalar(Math.max(REC, .02)); JJ.pino.visible = PINO > 0 && KCON; JJ.pino.position.x = .14 * (1 - PINO); JJ.resv.rotation.x = 2 * RESV;
  JJ.arn.forEach((m, i) => { m.visible = ARN[i] > .01; m.scale.setScalar(Math.max(ARN[i], .01)); }); JJ.ris.forEach(m => m.visible = RISON); JJ.bat.forEach((m, i) => { m.visible = RISON; m.position.y = 1.25 - (i ? TP : TN) * .5; });
  SIS.updateMatrixWorld(true);
  [VEL, VR].forEach(v => { if (v.visible) v.atualiza(t); });
  // cordas
  if (LA && LA.visible && LG > .01) { LIN.visible = true; LP.forEach((l, i) => { LA.ponto(l.u, l.v, RA); if (l.freio) ponta(l.s, true, l.s < 0 ? TN : TP, RB).add(V4.set(0, -.12, 0)); else ponta(l.s, l.tras, 0, RB); if (LG < 1) RB.lerpVectors(RA, RB, LG); ligaI(LIN, i, RA, RB, .0075); }); LIN.instanceMatrix.needsUpdate = true; } else LIN.visible = false;
  // slider desce pelas cordas
  SLD.visible = SS >= 0 && !!LA; if (SLD.visible) { LA.ponto(0, .5, RA); ponta(1, false, 0, RB); ponta(-1, true, 0, V4); RB.add(V4).multiplyScalar(.5).add(V1.set(0, .25, 0)); SLD.position.lerpVectors(RA, RB, SS).add(V1.set(0, -.2 * (1 - SS), 0)); SIS.getWorldQuaternion(SLD.quaternion); }
  // pano embolado
  ST.visible = STON; if (STON) { if (!(t > F(5) && t < T5E)) { ponta(1, false, 0, RA); ponta(-1, true, 0, RB); const base = RA.add(RB).multiplyScalar(.5); if (t > T8S && t < F(9)) base.add(STB); ST.position.copy(base); ST.quaternion.copy(SIS.quaternion); if (t > T8S && t < F(9)) ST.rotateZ((t - T8S) * 1.5); } else { ST.position.copy(STB); ST.quaternion.setFromUnitVectors(UP, STD); } atualizaST(t, STL_); }
  // extrator, fita, saco, pino solto
  PCH.visible = PCON; BAG.visible = BAGON; BRI.visible = PCON; if (PCON) { PCH.getWorldPosition(RA); if (BAGON) BAG.getWorldPosition(RB); else if (LA && LA.visible) { LA.ponto(0, .45, RB); RB.add(V4.set(0, .5, 0)); } else { JJ.KC.getWorldPosition(RB); } liga(BRI, RB, RA, .014); PCH.rotation.x = Math.sin(t * 7) * .1; }
  PINV.visible = PINVON; if (PINVON) { const d = t - T6I; JJ.KC.getWorldPosition(PINV.position); PINV.position.add(V4.set(.4 * d, .25 + 3.5 * d, .1 * d)); PINV.rotation.set(d * 9, d * 5, 0); }
  // vento
  VT.visible = VV > 0; if (VV > 0) { cam.getWorldPosition(V1); for (let i = 0; i < NVT; i++) { const p = VTP[i]; pose(VT, i, SIS.position.x + p[0], SIS.position.y - 10 + ((p[1] + t * VV) % 24), SIS.position.z + p[2], 0); } VT.instanceMatrix.needsUpdate = true; }
  VG.visible = VGON; if (VGON) { for (let i = 0; i < NVG; i++) { const p = VGP[i], z = 12 - ((p[2] + t * 9) % 13); pose(VG, i, p[0], p[1] + (z < 1.6 ? .1 : 0), z, 0); } VG.instanceMatrix.needsUpdate = true; }
  // biruta e bandeiras
  BIR.saco.rotation.y = Math.sin(t * 2.3) * .12; BIR.saco.rotation.x = -.15 + Math.sin(t * 3.1) * .05; BAND.forEach((b, i) => { b.p.rotation.y = -1.4 + Math.sin(t * 2 + i) * .25; });
  AMI.forEach((p, i) => { p.visible = t > T9L - .5; if (t > T9L) { pFesta(p.r, t, i * 2); p.position.y = Math.abs(Math.sin(t * 7 + i * 2)) * .25; } else { p.r.respira(t); p.r.anda(0, 0); p.position.y = 0; } p.lookAt(SIS.position.x, 0, SIS.position.z); });
};

// céu: dia, pôr do sol e noite ---------------------------------------------------------------------------------------
const BG = new THREE.Color(), DIA = new THREE.Color(CEU), TARDE = new THREE.Color('#f0915a'), NO = new THREE.Color('#0a1130');
const ceuQuadro = t => { const ta = ease(rev(t, T9 - .3, T9 + .8)), n = ease(rev(t, T9V - .2, T9V + 1)); if (ta > 0) { if (n > 0) BG.copy(TARDE).lerp(NO, n); else BG.copy(DIA).lerp(TARDE, ta); scene.background = BG; } else scene.background = fundo;
  sol.intensity = 2.6 - ta * .9 - n * 1.55; sol.color.setHex(n > .5 ? 0x8fa8ff : ta > .3 ? 0xffb27a : 0xfff2de); hemi.forEach(h => { h.intensity = 1.25 - ta * .25 - n * .8; h.color.setHex(n > .5 ? 0x5a6fb0 : ta > .3 ? 0xffd2b0 : 0xd8ecff); }); scene.environmentIntensity = .32 - n * .2;
  const alto = cam.position.y > 60; scene.fog.color.setHex(n > .5 ? 0x121a36 : ta > .3 ? 0xf2b48a : 0xcfe6f2); scene.fog.near = alto ? 380 : 160; scene.fog.far = alto ? 3000 : 1900;
  const noite = n > .4; NOITE_M.forEach(m => m.visible = noite); LUZ_HG.intensity = noite ? 60 : 0; PL.forEach(p => p.intensity = noite ? 90 : 0); POSTE.forEach(p => p.l.material.color.setHex(noite ? 0xfff0c0 : 0x555555)); EST.material.opacity = n;
  // sombra acompanha o que a câmera olha
  sol.target.position.copy(FOCO); sol.position.copy(FOCO).add(ta > .3 ? V1.set(-26, 14, -30) : V1.set(14, 26, 12)); sol.target.updateMatrixWorld();
  let fl = 0; for (let i = 1; i < N - 1; i++) { const d = t - CI[i].n; if (d > 0 && d < .6) fl = Math.max(fl, .7 * (1 - d / .6)); } const d4 = t - T4E; if (d4 > 0 && d4 < .35) fl = Math.max(fl, .9 * (1 - d4 / .35)); const d9 = t - T9; if (d9 > 0 && d9 < .6) fl = Math.max(fl, .8 * (1 - d9 / .6)); flash.style.opacity = fl;
  const ds = t - T4S; alerta.style.opacity = ds > 0 && ds < .9 && t < T4E ? .9 * (1 - ds / .9) : 0; };

// câmera (chaves podem seguir o saltador, o avião ou a formação) ---------------------------------------------------------
const K = [], P = (t, p, l, f = 38, a = null) => K.push({ t, p, l, f, a }), cut = (t, p, l, f = 38, a = null) => { const q = K[K.length - 1]; if (q) P(t - .001, q.p, q.l, q.f, q.a); P(t + .001, p, l, f, a); };
const FOCO = new THREE.Vector3(), CP = new THREE.Vector3();
const camara = t => { let i = 0; while (i < K.length - 2 && t > K[i + 1].t) i++; const a = K[i], b = K[i + 1], k = ease((t - a.t) / (b.t - a.t)); CP.set(...a.p).lerp(V1.set(...b.p), k); FOCO.set(...a.l).lerp(V1.set(...b.l), k); const an = b.a && a.a === b.a ? AN[b.a] : null; if (an) { CP.add(an); FOCO.add(an); }
  let tr = 0; const ds = t - T4S; if (ds > 0 && ds < .6 && t < T4E) tr = .25 * (1 - ds / .6); CP.x += Math.sin(t * 61) * tr; CP.y += Math.cos(t * 53) * tr; cam.position.copy(CP); cam.position.x += Math.sin(t * .7) * .012; cam.lookAt(FOCO); cam.fov = (a.f || 38) + ((b.f || 38) - (a.f || 38)) * k; cam.updateProjectionMatrix(); };
const S = 'sis';
P(0, [8, 7.5, 11], [0, 2.2, 0], 44, S); P(T0E - .1, [7.2, 7, 10], [0, 2.4, 0], 44, S); cut(T0E, [3.4, 4.2, 4.2], [0, 4.4, 0], 40, S); P(T0D - .05, [3, 4.4, 3.8], [0, 4.6, 0], 40, S); cut(T0D, [12, 4, 15], [0, -4, 0], 44, S); P(T0P - .05, [11, 3.6, 14], [0, -5, 0], 44, S); cut(T0P, [4.2, .6, 5.2], [0, 3.6, 0], 40, S); P(fim(0), [4.8, 1, 6], [0, 3.6, 0], 40, S);
cut(F(1), [5, 4.2, 5.5], [-4, 9.2, -8], 40); P(CI[1].e - .05, [4.4, 3.8, 5], [-4, 7.6, -8], 40); cut(CI[1].e, [1.8, 3.2, 7.2], [-6.6, .8, 1.2]); P(T1K + .7, [3.4, 3.2, 7.2], [-2.4, .5, .4]); P(T1R - .1, [4.4, 3, 7.2], [-1, .4, .3]); P(T1N - .05, [3.2, 1.3, 6.6], [0, .42, .5]); P(fim(1), [2.8, 1.15, 6.2], [0, .42, .6]);
cut(F(2), [2.6, 1.6, 5.8], [0, .4, .5]); P(T2V, [3.2, 1.8, 7.4], [0, .4, .4]); P(T2A, [4.4, 1.8, 10], [0, 1.2, 0]); P(T2N, [6.5, 3, 15.5], [0, 4.2, 0]); P(fim(2), [7, 3.4, 16], [0, 4.4, 0]);
cut(F(3), [8, 2.8, 15], [0, 3.8, 0]); P(T3K + 1.2, [7.4, 3, 14], [0, 3.9, 0]); cut(T3F, [1.7, 1.55, 2.9], [0, 1.0, 0]); P(T3T + .45, [1.3, 1.6, 2.7], [0, 1.1, 0]); cut(T3N, [6.2, 2.8, 13.5], [0, 3.8, 0]); P(fim(3), [6.8, 3, 14], [0, 3.8, 0]);
cut(F(4), [8.5, 1.4, 11.5], [0, 2.8, 0], 40, S); P(T4S + .7, [9, 2, 12], [0, 3.4, 0], 40, S); cut(T4E, [7, 1, 9.5], [0, 3.4, 0], 40, S); P(T4B, [8.5, .8, 11.5], [0, 3.5, 0], 40, S); P(fim(4), [9, 1.2, 12], [0, 3.5, 0], 40, S);
cut(F(5), [7.5, 4.6, 21], [-2, .4, 0], 40, 'av'); P(T5E - .05, [5.6, 4, 18], [-2.4, .8, 0], 40, 'av'); cut(T5E, [-6.5, 5, -14], [0, 3.2, 0]); P(T5M - .1, [-4.4, 3.4, -9], [0, 1.8, 0]); cut(T5M, [-1.4, 1.75, -2.7], [0, 1.15, -.25]); P(T5P - .05, [-1.1, 1.6, -2.2], [0, 1.12, -.25]); cut(T5P, [-.62, 1.35, -1.35], [0, 1.08, -.3], 36); P(T5N, [-.66, 1.38, -1.4], [0, 1.08, -.3], 36); cut(T5N + .05, [-2.6, 2.3, -4.4], [0, 1.2, 0]); P(fim(5), [-2.8, 2.4, -4.8], [0, 1.2, 0]);
cut(F(6), [6.5, 3.6, 15], [-1, .6, 0], 40, 'av'); P(T6X + .3, [6, 3.2, 14], [0, .4, 0], 40, 'av'); cut(T6X + .35, [3.6, 3.4, 8.5], [0, 0, 0], 40, S); P(T6E, [3.2, 3, 5.4], [0, .2, 0], 40, S); cut(T6P - .05, [2.6, 2.2, 3.4], [0, .6, 0], 38, S); P(T6I + .2, [3.8, 2.6, 5.4], [0, 2.2, 0], 38, S); cut(T6R, [8, 1.2, 10], [0, 3.4, 0], 40, S); P(T6N, [7.6, 1.4, 10.4], [0, 3.8, 0], 40, S); P(fim(6), [8, 1.8, 11], [0, 3.8, 0], 40, S);
const atras = (p, b, u, s) => [-Math.sin(p) * b - Math.cos(p) * s, u, -Math.cos(p) * b + Math.sin(p) * s], frente = (p, f, u) => [Math.sin(p) * f, u, Math.cos(p) * f];
cut(F(7), atras(PSI0, 12, 4.2, 3), frente(PSI0, 8, 2.8), 42, S); P(T7P, atras(PSI0, 12.5, 4.4, 3), frente(PSI0, 8, 2.6), 42, S); [.35, .7, 1.05, 1.4, 1.75].forEach(d => { const p = psi7(T7P + d); P(T7P + d, atras(p, 12.3, 4.3, 3 - d * 2.6), frente(p, 8.5, 2.5), 42, S); }); P(T7P + 2.1, atras(PSI1, 12, 4.2, -2), frente(PSI1, 9, 2.4), 42, S); P(T7N, atras(PSI1, 11.5, 4.4, -3), frente(PSI1, 9, 2.6), 42, S); P(fim(7), atras(PSI1, 12, 4.8, -3.4), frente(PSI1, 9, 2.6), 42, S);
cut(F(8), [6.4, 1.2, 8.4], [0, 2.8, 0], 40, S); P(T8S, [5.6, 1.4, 7.6], [0, 2.6, 0], 40, S); P(T8A, [6.6, .8, 9.6], [0, 3.2, 0], 40, S); P(T8N, [7.6, .8, 10.6], [0, 3.8, 0], 40, S); P(fim(8), [8, 1.2, 11], [0, 3.8, 0], 40, S);
cut(T9, [TG.x - 10, 3, TG.z - 14], [TG.x, 22, TG.z + 46], 44); P(T9 + 1.2, [TG.x - 9, 2.6, TG.z - 12], [TG.x, 10, TG.z + 22], 42); P(T9L, [TG.x - 8, 2.2, TG.z - 10], [TG.x, 2.6, TG.z + 2], 40); P(T9C - .05, [TG.x - 7, 2.4, TG.z - 9], [TG.x, 1.6, TG.z], 40);
cut(T9C, [4.5, 11, 5], [0, -2, 0], 42, 'form'); P(T9V - .05, [3.8, 10, 4.4], [0, -2, 0], 42, 'form'); cut(T9V, [56, 10, 50], [4, 3.5, -12]); P(D.total + 1, [62, 12, 58], [4, 3.5, -14]);
K.sort((a, b) => a.t - b.t); for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .002;

// rótulos e sons -------------------------------------------------------------------------------------------------------
const NOM = ['', 'CÉLULAS', 'VELAME', 'ARNÊS', 'SLIDER', 'CONTAINER', 'EXTRATOR', 'BATOQUES', 'RESERVA'];
for (let i = 1; i < N - 1; i++) { const a = CI[i].n, e = rotulo(NOM[i], [540, 400], a, fim(i), 'grande'); e.style.fontSize = NOM[i].length > 8 ? '74px' : '88px'; e.style.transform += ' rotate(-3deg)'; som(a, 'ding'); }
const ruim = (x, a, b) => { rotulo(x, [540, 400], a, b, 'grande').style.cssText += ';font-size:66px;color:#ff5a4f'; };
ruim('NÃO ABRIU!', 2.05, fim(0)); ruim('SÓ BALANÇA', T1B, CI[1].e); ruim('MURCHAS', T2M, CI[2].e); ruim('COMO SEGURAR?', T3C, CI[3].e); ruim('TRANCO!', T4S + .05, CI[4].e); ruim('NO AVIÃO, NÃO!', T5V, CI[5].e); ruim('QUEM PUXA?', F(6) + .6, CI[6].e); ruim('SEM CONTROLE', T7C, CI[7].e); ruim('ENROSCOU!', F(8) + .4, CI[8].e);
rotulo('PARAQUEDAS PRONTO!', [540, 400], T9 + .1, T9C - .1, 'grande').style.fontSize = '64px'; rotulo('VERDADE OU MENTIRA?', [540, 400], T9V, D.total + 1, 'grande').style.fontSize = '62px';
const RPINO = [0, 0, 0], RARG = [0, 0, 0]; rotulo('PINO', RPINO, T5P + .1, T5N - .1, 'pilula'); rotulo('ARGOLAS', RARG, T4A, T4N - .1, 'pilula');
AUTO.push(t => { if (t > T5P && t < T5N) { JJ.pino.getWorldPosition(V1); RPINO[0] = V1.x - .12; RPINO[1] = V1.y + .12; RPINO[2] = V1.z; } if (t > T4A && t < T4N) { SLD.getWorldPosition(V1); RARG[0] = V1.x + .9; RARG[1] = V1.y + .3; RARG[2] = V1.z; } });
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); });
for (let q = 0; q < fim(0); q += .5) som(q, 'whoosh'); som(.05, 'riser');
som(T1B, 'whoosh'); for (let q = T1C; q < T1R; q += .25) som(q, 'toc'); for (let i = 0; i < 10; i++) som(T1R + i * .12, 'pop');
som(T2V, 'whoosh'); som(T2E, 'riser'); som(T2A, 'whoosh');
for (let i = 0; i < 6; i++) som(T3K + i * .2, 'toc'); som(T3F, 'pop'); som(T3P, 'pop'); som(T3T, 'pop');
som(T4S, 'impact'); som(T4S + .02, 'crack'); som(T4D, 'whoosh'); som(T4B - .2, 'pop');
for (let q = F(5); q < T5E; q += .8) som(q, 'motor'); som(F(5) + .3, 'whoosh'); som(T5D, 'whoosh'); som(T5M + .3, 'pop'); som(T5P - .3, 'toc'); som(T5P + .2, 'pop');
for (let q = F(6); q < T6X + .2; q += .8) som(q, 'motor'); som(T6X, 'whoosh'); som(T6P, 'whoosh'); som(T6I, 'pop'); som(T6R, 'whoosh'); som(T6R + .5, 'impact');
som(T7P, 'whoosh'); som(T7F, 'riser');
for (let q = F(8); q < T8S; q += .5) som(q, 'whoosh'); som(T8S, 'crack'); som(T8A, 'pop'); som(T8A + .4, 'impact');
som(T9L - .2, 'impact'); som(T9 - .3, 'riser'); som(T9V, 'ding'); som(T9V + .2, 'riser');
window.CAPA_T = T7N - .25;
iniciar(t => { quadro(t); AUTO.forEach(f => f(t)); camara(t); ceuQuadro(t); });
