// Piscina de quintal. Abre com uma piscina de cimento vazando: a água desce rápido, a parede racha e o quintal vira lama.
// No mesmo buraco a obra certa cresce: escavação e compactação, armação de aço, ralos e canos até a casa de máquinas,
// concreto projetado, impermeabilização em camadas, pastilhas e borda de pedra, água turva limpa no filtro de areia e luzes à noite.
// Medidas em metros. Câmera olha ao longo da piscina (do +x para o -x), assim a peça enche o quadro em pé.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, tex, camTo, iniciar, som, rotulo, fala, D } = K3;
const rnd = prng(41), F = fala, fim = i => F(i) + D.falas[i].dur, N = D.falas.length, AUTO = [], O = new THREE.Object3D(), C = new THREE.Color(), PI = Math.PI;
O.rotation.order = 'YXZ'; cam.far = 900; cam.updateProjectionMatrix();
const nk = x => String(x).toLowerCase().normalize('NFD').replace(/[^a-z0-9]/g, '');
const tk = (w, i, f = .4) => { const k = nk(w), q = D.falas[i].words?.find(p => nk(p.w).startsWith(k)); return q ? q.start : F(i) + D.falas[i].dur * f; };
const nomeT = i => { const q = [...(D.falas[i].words ?? [])].reverse().find(p => /^(essa|esse|essas|esses)$/.test(nk(p.w))); return q ? q.start : fim(i) - 1.2; };
const rev = (t, a, b) => clamp((t - a) / (b - a));
const CI = {}; for (let i = 1; i < N - 1; i++) CI[i] = { a: F(i), e: tk('Então', i, .4), n: nomeT(i) };
const B = (g, w, h, d, c, x, y, z, r = .02, o) => { const m = add(box(w, h, d, c, r, o), g); m.position.set(x, y, z); return m; };
const pc = (n, g, x, y, z, ry = 0, o, e = 1) => { const q = PC.novo(n, o); q.position.set(x, y, z); q.rotation.y = ry; if (e !== 1) q.scale.multiplyScalar(e); g.add(q); return q; };
const pose = (I, i, x, y, z, ry, sx = 1, sy = sx, sz = sx, rx = 0, rz = 0) => { O.position.set(x, y, z); O.rotation.set(rx, ry, rz, 'YXZ'); O.scale.set(sx, sy, sz); O.updateMatrix(); I.setMatrixAt(i, O.matrix); };
const inst = (geo, m, n, g = scene, sombra = true) => { const I = new THREE.InstancedMesh(geo, m, n); I.frustumCulled = false; I.castShadow = sombra; I.receiveShadow = sombra; g.add(I); return I; };
const plano = (w, d, c, x, y, z, g = scene, o) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, d), typeof c === 'object' ? c : mat(c, { roughness: 1, ...o })), g); m.rotation.x = -PI / 2; m.position.set(x, y, z); m.receiveShadow = true; return m; };
const brilho = (c, o = {}) => new THREE.MeshBasicMaterial({ color: c, toneMapped: false, ...o });
const UP = new THREE.Vector3(0, 1, 0), VA = new THREE.Vector3(), VB = new THREE.Vector3();
const seg = (a, b, r, x = {}) => { VA.set(...a); VB.set(...b).sub(VA); const n = VB.length(), q = new THREE.Quaternion().setFromUnitVectors(UP, VB.clone().normalize()); return { p: a, q, s: [r, n, r], ...x }; };
const lote = (geo, material, L, base = 0xffffff, pai = scene) => {
  const m = new THREE.InstancedMesh(geo, material, L.length); m.castShadow = m.receiveShadow = true; m.frustumCulled = false; add(m, pai);
  let fimT = -1; L.forEach((b, i) => { C.set(b.c ?? base); m.setColorAt(i, C); fimT = Math.max(fimT, b.t + b.d); }); fimT += .05; let u = -9;
  AUTO.push(t => { if (t > fimT && u > fimT) return; u = t; for (let i = 0; i < L.length; i++) { const b = L[i], k = (t - b.t) / b.d, s = b.s || [1, 1, 1]; O.position.set(b.p[0], b.p[1], b.p[2]); if (b.q) O.quaternion.copy(b.q); else O.quaternion.identity(); if (k <= 0) O.scale.setScalar(0); else if (b.modo === 'pop') { const e = Math.max(back(k), .001); O.scale.set(s[0] * e, s[1] * e, s[2] * e); } else if (b.modo === 'cresce') O.scale.set(s[0], s[1] * Math.max(ease(k), .001), s[2]); else { O.position.y += (1 - ease(k)) * (b.dy ?? 3); O.scale.set(s[0], s[1], s[2]); } O.updateMatrix(); m.setMatrixAt(i, O.matrix); } m.instanceMatrix.needsUpdate = true; });
  return m;
};
const G_CIL = new THREE.CylinderGeometry(1, 1, 1, 8).translate(0, .5, 0), G_CX = new THREE.BoxGeometry(1, 1, 1);
const tubo = (g, cur, r, c, n = 80, o = {}) => add(sh(new THREE.Mesh(new THREE.TubeGeometry(cur, n, r, 8), typeof c === 'object' ? c : mat(c, o))), g);
const curva = p => new THREE.CatmullRomCurve3(p.map(q => new THREE.Vector3(...q)), false, 'catmullrom', .1);
const linha = p => { const c = new THREE.CurvePath(); for (let i = 0; i < p.length - 1; i++) c.add(new THREE.LineCurve3(new THREE.Vector3(...p[i]), new THREE.Vector3(...p[i + 1]))); return c; };
const cresceTubo = (m, a, b, ate = 1e9) => { const tot = m.geometry.parameters.tubularSegments, rs = m.geometry.parameters.radialSegments; AUTO.push(t => { const k = ease(rev(t, a, b)); m.visible = k > 0 && t < ate; m.geometry.setDrawRange(0, Math.floor(k * tot) * rs * 6); }); };
const pulsos = (cur, n, c, ativo, vel = .35, r = .05) => { const I = new THREE.InstancedMesh(new THREE.SphereGeometry(r, 10, 8), brilho(c), n); I.frustumCulled = false; add(I); AUTO.push(t => { const on = ativo(t); I.visible = !!on; if (!on) return; for (let i = 0; i < n; i++) { const q = (t * vel + i / n) % 1; O.position.copy(cur.getPointAt(q)); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); I.setMatrixAt(i, O.matrix); } I.instanceMatrix.needsUpdate = true; }); return I; };
const janela = (a, b, f) => AUTO.push(t => f(t, t >= a && t < b));

// medidas da piscina e do buraco --------------------------------------------------------------------------------------------
const PX = 4.5, PZ = 2.2, PD = 1.5, EX = 4.85, EZ = 2.55, ED = 1.75;
const GR = 0x4fae58, AS = 0x34373e, TERRA = 0x8a5a3c, TERRA_S = 0xa0714a, FERRO = 0xa4532c, CONC = 0xbdb9b0, PVC = 0xf2f1ea;
const CAM = [0xd8352f, 0x2f7fd6, 0xffc21a, 0xf4f4f2, 0x3fa45a, 0xe8683f, 0x8a5bc4], PELE = [0xdca77f, 0xb5805a, 0x8a5a3c, 0xe8c4a0];
const gente = (g, x, y, z, ry, o = {}) => pc('personagem', g, x, y, z, ry, { capacete: false, cinto: false, camisa: CAM[Math.floor(rnd() * 7)], camisa2: 0x333844, calca: [0x2b3a67, 0x3a3f4a, 0x6b5a45][Math.floor(rnd() * 3)], cabelo: [0x3a2a1e, 0x15110e, 0x8a5a33][Math.floor(rnd() * 3)], pele: PELE[Math.floor(rnd() * 4)], ...o });
const obreiro = (cor, x, y, z, ry) => pc('personagem', scene, x, y, z, ry, { camisa: cor, camisa2: new THREE.Color(cor).multiplyScalar(.82).getHex() });

// tempos de cada fala ----------------------------------------------------------------------------------------------------
const T0R = tk('rachadura', 0), T0L = tk('lama', 0), T0B = tk('Buraco', 0);
const T1D0 = CI[1].e + .1, T1C0 = tk('compactador', 1), T1D1 = Math.max(T1D0 + 1.5, T1C0 - .05), T1C = Math.max(T1C0, T1D1 + .05);
const T2V = tk('vergalhões', 2), T2B = Math.max(T2V + 2.2, CI[2].n - .1);
const T3R = tk('ralos', 3), T3C = Math.max(tk('canos', 3), T3R + .5), T3F = Math.max(T3C + 1.6, CI[3].n - .05);
const T4A = tk('mangueira', 4), T4S = Math.max(tk('dispara', 4), T4A + .3), T4B = Math.max(T4S + 2.4, CI[4].n);
const T5A = Math.max(tk('pinta', 5), CI[5].e + .1), T5B = Math.max(T5A + 2.4, CI[5].n), T5M = (T5A + T5B) / 2;
const T6P = tk('pastilhas', 6), T6C = Math.max(tk('borda', 6), T6P + 2), T6F = Math.max(T6C + 1.1, CI[6].n + .3);
const T7B = tk('bomba', 7), T7T = tk('tanque', 7), T7S = tk('sujeira', 7), T7N = CI[7].n, FILL1 = Math.max(CI[7].a + 1.9, T7B + .3);
const T8L = tk('luzes', 8), T8N = CI[8].n;
const T9 = F(N - 1) - .02, T9C = tk('comer', N - 1), T9V = tk('Verdade', N - 1, .85);

// céu, luz e camadas de tela -------------------------------------------------------------------------------------------------
const CEU = '#3f8fe0'; ceu(CEU, '#d6eefa'); const fundo = scene.background; scene.fog = new THREE.Fog(0xcfe6f2, 70, 300);
const sol = luzes(0xfff2de, 0xd8ecff, 0x8fb070, 2.6, 26); sol.position.set(16, 28, 12); scene.environmentIntensity = .32;
const hemi = []; scene.traverse(o => { if (o.isHemisphereLight) { hemi.push(o); o.groundColor.setHex(0xb8b09a); } });
const camada = c => { const e = document.createElement('div'); e.style.cssText = `position:absolute;inset:0;background:${c};opacity:0`; document.getElementById('hud').prepend(e); return e; };
const flash = camada('#fff8e0');

// chão do quintal com o buraco da piscina ---------------------------------------------------------------------------------------
const solo = tex(64, 256, (g, w, h) => { const cs = ['#8a5a3c', '#7a4e33', '#94633f', '#6e4630', '#86573a']; let y = 0, i = 0; while (y < h) { const a = 14 + (i * 37) % 30; g.fillStyle = cs[i % 5]; g.fillRect(0, y, w, a); y += a; i++; } for (let k = 0; k < 90; k++) { g.fillStyle = k % 3 ? '#5c3b27' : '#b08a64'; g.beginPath(); g.arc(rnd() * w, rnd() * h, 1 + rnd() * 2.5, 0, 7); g.fill(); } }, 4, 1);
{ const s = new THREE.Shape(); s.moveTo(-300, -300); s.lineTo(300, -300); s.lineTo(300, 300); s.lineTo(-300, 300); s.closePath(); const h = new THREE.Path(); h.moveTo(-EX, -EZ); h.lineTo(-EX, EZ); h.lineTo(EX, EZ); h.lineTo(EX, -EZ); h.closePath(); s.holes.push(h); const m = add(new THREE.Mesh(new THREE.ShapeGeometry(s).rotateX(-PI / 2), mat(GR, { roughness: 1 }))); m.receiveShadow = true; }
const MSOLO = new THREE.MeshStandardMaterial({ map: solo, roughness: 1, side: THREE.DoubleSide });
const paredeT = (w, h, x, y, z, ry) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, h), MSOLO)); m.position.set(x, y, z); m.rotation.y = ry; m.receiveShadow = true; return m; };
paredeT(2 * EX, ED, 0, -ED / 2, -EZ, 0); paredeT(2 * EX, ED, 0, -ED / 2, EZ, PI); paredeT(2 * EZ, ED, -EX, -ED / 2, 0, PI / 2); paredeT(2 * EZ, ED, EX, -ED / 2, 0, -PI / 2);
const fundoT = plano(2 * EX, 2 * EZ, mat(0x9a6a46, { roughness: 1 }), 0, -ED, 0);
// tufos de grama, pedrinhas e caminho de pedras
{ const n = 900, I = inst(new THREE.ConeGeometry(.07, .22, 4).translate(0, .11, 0), mat(0x3f9a48, { flatShading: true }), n, scene, false); let k = 0; for (let i = 0; i < n * 3 && k < n; i++) { const x = -12.5 + rnd() * 29, z = -8.8 + rnd() * 18; if (Math.abs(x) < EX + 1.5 && Math.abs(z) < EZ + 1.5) continue; if (x < -8.6 && Math.abs(z + .4) < 1.6) continue; pose(I, k, x, 0, z, rnd() * 6, .8 + rnd() * .9); I.setColorAt(k, C.set(0x3f9a48).offsetHSL((rnd() - .5) * .05, 0, (rnd() - .5) * .12)); k++; } I.count = k; }
for (let i = 0; i < 7; i++) { const m = add(new THREE.Mesh(new THREE.CylinderGeometry(.34, .36, .05, 9), mat(0xd9d2c0, { roughness: .9 }))); m.position.set(6.5 + i * 1.3 * .2, .025, -4 - i * .78); m.receiveShadow = true; }

// muro, casa, casa de máquinas e vizinhança ------------------------------------------------------------------------------------
const MURO = 0xf0e9dc;
const muro = (x0, z0, x1, z1) => { const L = Math.hypot(x1 - x0, z1 - z0), r = -Math.atan2(z1 - z0, x1 - x0); B(scene, L, 1.9, .22, MURO, (x0 + x1) / 2, .95, (z0 + z1) / 2, .02).rotation.y = r; B(scene, L + .1, .08, .32, 0xc9bfae, (x0 + x1) / 2, 1.93, (z0 + z1) / 2, .01).rotation.y = r; B(scene, L, .25, .24, 0xb9ae9c, (x0 + x1) / 2, .12, (z0 + z1) / 2, .01).rotation.y = r; };
muro(-12.8, -19, -12.8, 9.5); muro(-12.8, 9.5, 17, 9.5); muro(17, 9.5, 17, -19); muro(-12.8, -19, 17, -19);
const CASA = pc('casa_moderna', scene, 2, 0, -14.2, 0);
plano(14, 2.6, 0xd8d0bf, 2, .012, -8.6); { const I = inst(new THREE.BoxGeometry(.02, .006, 2.6), mat(0xbdb5a3), 24, scene, false); for (let i = 0; i < 24; i++) pose(I, i, -5 + i * .6, .016, -8.6, 0); }
// casa de máquinas no fundo do quintal, porta aberta para a piscina
const CMx = -10.3, CMz = -.4, CMg = new THREE.Group(); add(CMg); CMg.position.set(CMx, 0, CMz);
{ const g = CMg, W = 2.6, H = 2.3, P2 = 2.4, cor = 0xe8e2d4; B(g, W, .14, P2, 0xbab3a4, 0, .07, 0, .02); B(g, .16, H, P2, cor, -W / 2 + .08, H / 2, 0, .02); B(g, W, H, .16, cor, 0, H / 2, -P2 / 2 + .08, .02); B(g, W, H, .16, cor, 0, H / 2, P2 / 2 - .08, .02);
  B(g, .16, H, .55, cor, W / 2 - .08, H / 2, -P2 / 2 + .27, .02); B(g, .16, H, .55, cor, W / 2 - .08, H / 2, P2 / 2 - .27, .02); B(g, .16, .4, 1.3, cor, W / 2 - .08, H - .2, 0, .02);
  B(g, W + .4, .16, P2 + .4, 0x8c5a3c, 0, H + .08, 0, .03); B(g, W + .5, .06, P2 + .5, 0x6e4427, 0, H + .17, 0, .02);
  const porta = new THREE.Group(); porta.position.set(W / 2, 0, .65); g.add(porta); B(porta, .05, 1.85, 1.25, 0x3f7fb5, .02, .95, -.62, .02); B(porta, .07, .05, .14, 0xd9b84a, .05, 1, -1.1, .01); porta.position.x = W / 2 + .06; porta.rotation.y = PI;
  const lz = new THREE.PointLight(0xfff0d8, 9, 5.5); lz.position.set(0, 2, .2); g.add(lz); B(g, .3, .06, .3, 0xffffff, 0, H - .05, 0, .02); }
// vizinhos atrás do muro, rua e casas em frente
pc('casa_simples', scene, -21, 0, -4, PI / 2, { cor: 0xf2c879 }); pc('casa_colonial', scene, -23, 0, 10, PI / 2); pc('casa_chale', scene, -21, 0, -17, PI / 2); pc('casa_praia', scene, 2, 0, -30, 0);
plano(220, 7, AS, 0, .02, 14); plano(220, 1.8, 0xd9d7d0, 0, .03, 10.4); plano(220, 1.8, 0xd9d7d0, 0, .03, 18.4); { const I = inst(new THREE.BoxGeometry(2.6, .01, .16), mat(0xf2d24a), 40, scene, false); for (let i = 0; i < 40; i++) pose(I, i, -80 + i * 4.2, .035, 14, 0); }
pc('casa_simples', scene, -4, 0, 24.5, PI, { cor: 0xbfe0ef }); pc('casa_vila', scene, 8, 0, 24.5, PI); pc('casa_popular', scene, 18, 0, 24.5, PI); pc('casa_simples', scene, -15, 0, 24.5, PI, { cor: 0xf2b8a6 });
pc('veiculo_sedan', scene, 3, 0, 12.3, PI / 2, { cor: 0xd8352f }); pc('veiculo_hatch', scene, -8, 0, 15.8, -PI / 2, { cor: 0x2f7fd6 });
// plantas do quintal
[['palmeira', -11.4, 7.6], ['coqueiro', -11.6, -8.2], ['palmeira', 15.6, -17.5], ['arvore_redonda', -8, -16.8],['arvore_redonda', -6, 8.2]].forEach(([n, x, z]) => pc(n, scene, x, 0, z, rnd() * 6));
[['arbusto_flores', -12, 3.2], ['arbusto', -12, -3.4], ['arbusto_flores', -12, -6], ['canteiro_flores', 2, 8.7], ['arbusto_flores', 7, 8.7], ['arbusto', -2.5, 8.7], ['arbusto', 10.5, -8.4], ['arbusto_flores', -4.8, -8.6]].forEach(([n, x, z]) => pc(n, scene, x, 0, z, rnd() * 6));
// árvores e morros ao longe
{ const ARV = []; for (let i = 0; i < 140; i++) { const a = rnd() * PI * 2, r = 30 + rnd() * 70, x = Math.cos(a) * r, z = Math.sin(a) * r * .9; if (z > 8 && z < 22) continue; ARV.push([x, z, 1 + rnd() * .9]); } const n = ARV.length, TR = inst(new THREE.CylinderGeometry(.22, .32, 1, 7).translate(0, .5, 0), mat(0x6b4a2c), n), CO = inst(new THREE.IcosahedronGeometry(1, 0), mat(0xffffff, { flatShading: true }), n * 2);
  ARV.forEach(([x, z, e], i) => { const s = e * 1.7; pose(TR, i, x, 0, z, 0, s * .9, s * 2.4, s * .9); pose(CO, i * 2, x, s * 2.8, z, i, s * 1.5, s * 1.25, s * 1.5); pose(CO, i * 2 + 1, x + .8, s * 3.5, z + .5, i * 2, s * 1.05, s * .9, s * 1.05); CO.setColorAt(i * 2, C.set([0x2e8f3e, 0x3aa84a, 0x237a35][i % 3])); CO.setColorAt(i * 2 + 1, C.set([0x3aa84a, 0x2e8f3e, 0x46b254][i % 3])); }); }
{ const MO = inst(new THREE.IcosahedronGeometry(1, 2), mat(0x5aa060, { flatShading: true, roughness: 1 }), 40, scene, false); for (let i = 0; i < 40; i++) { const a = i / 40 * PI * 2, r = 220 + rnd() * 80; pose(MO, i, Math.cos(a) * r, -8, Math.sin(a) * r, rnd() * 6, 60 + rnd() * 50, 26 + rnd() * 40, 50 + rnd() * 30); MO.setColorAt(i, C.set(0x5aa060).offsetHSL((rnd() - .5) * .04, 0, (rnd() - .5) * .1)); } }
// cachorro passeando no gramado
{ const cao = pc('cachorro', scene, 0, 0, 6.6, 0); AUTO.push(t => { const q = (t * .09) % 2, k = q < 1 ? q : 2 - q; cao.position.set(-3 + k * 9, Math.abs(Math.sin(t * 9)) * .03, 6.6 + Math.sin(t * .5) * .4); cao.rotation.y = q < 1 ? PI / 2 : -PI / 2; }); }

// casca: superfícies da piscina que nascem varrendo o comprimento (concreto, camadas e piscina de cimento) --------------------------
const casca = (c, ins, aro = true, o = {}) => { const m = mat(c, { roughness: .95, side: THREE.DoubleSide, ...o }), g = new THREE.Group(); add(g); const L = [];
  const pl = (w, h, x, y, z, rx, ry, x0, wx) => { const me = add(new THREE.Mesh(new THREE.PlaneGeometry(1, h).translate(.5, 0, 0), m), g); me.position.set(x, y, z); me.rotation.set(rx, ry, 0, 'YXZ'); me.receiveShadow = true; L.push({ me, w, x0, wx }); };
  pl(2 * PX, 2 * PZ, -PX, -PD + ins, 0, -PI / 2, 0, -PX, 2 * PX);
  pl(2 * PX, PD, -PX, -PD / 2, -PZ + ins, 0, 0, -PX, 2 * PX); pl(2 * PX, PD, -PX, -PD / 2, PZ - ins, 0, 0, -PX, 2 * PX);
  pl(2 * PZ, PD, -PX + ins, -PD / 2, PZ, 0, PI / 2, -PX, .5); pl(2 * PZ, PD, PX - ins, -PD / 2, PZ, 0, PI / 2, PX - .5, .5);
  if (aro) { pl(2 * EX, EZ - PZ, -EX, .004 + ins, -(PZ + EZ) / 2, -PI / 2, 0, -EX, 2 * EX); pl(2 * EX, EZ - PZ, -EX, .004 + ins, (PZ + EZ) / 2, -PI / 2, 0, -EX, 2 * EX); pl(EX - PX, 2 * PZ, -EX, .004 + ins, 0, -PI / 2, 0, -EX, EX - PX); pl(EX - PX, 2 * PZ, PX, .004 + ins, 0, -PI / 2, 0, PX, EX - PX); }
  g.frente = x => { L.forEach(q => { const k = clamp((x - q.x0) / q.wx); q.me.visible = k > 0; q.me.scale.x = Math.max(k * q.w, .001); }); }; g.m = m; return g; };
const FR = k => -EX + k * 2 * EX + .05;

// ABERTURA: piscina de cimento vazando ---------------------------------------------------------------------------------------
const RUIM = casca(0xa8a297, 0); RUIM.frente(99); AUTO.push(t => { RUIM.visible = t < F(1) - .02; });
const RUIMg = new THREE.Group(); add(RUIMg); AUTO.push(t => { RUIMg.visible = t < F(1) - .02; });
const H0 = 1.36, NIV0 = t => H0 - .45 - .55 * (1 - (1 - clamp(t / 2.2)) ** 2) - .14 * rev(t, 2.2, fim(0));
{ const g = RUIMg, mW = new THREE.MeshStandardMaterial({ color: 0x5c5848, roughness: .5 }), mk = [];
  [[0, -PZ + .008, 0, 2 * PX], [0, PZ - .008, 0, 2 * PX]].forEach(([x, z, r, w]) => B(g, w, .05, .01, 0x4a3f2a, x, -PD + H0 - .02, z, .005)); [-1, 1].forEach(s => B(g, .01, .05, 2 * PZ, 0x4a3f2a, s * (PX - .008), -PD + H0 - .02, 0, .005)); // faixa molhada acima da água
  [[2 * PX, -PX + PX, -PZ + .005, 0], [2 * PX, 0, PZ - .005, 0]].forEach(([w, x, z]) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, 1).translate(0, -.5, 0), mW), g); m.position.set(x, -PD + H0, z); mk.push(m); });
  [-1, 1].forEach(s => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(2 * PZ, 1).translate(0, -.5, 0), mW), g); m.rotation.y = PI / 2; m.position.set(s * (PX - .005), -PD + H0, 0); mk.push(m); });
  mk.forEach(m => { m.material.side = THREE.DoubleSide; }); AUTO.push(t => { const h = NIV0(t); mk.forEach(m => { m.scale.y = Math.max(H0 - h, .001); }); });
  // rachadura que corre pela parede do fundo e pelo piso até o redemoinho
  const RP = [[-2.1, -.05, -PZ + .012], [-1.7, -.35, -PZ + .012], [-2.0, -.62, -PZ + .012], [-1.55, -.95, -PZ + .012], [-1.8, -1.25, -PZ + .012], [-1.45, -PD + .012, -PZ + .02], [-1.65, -PD + .012, -1.6], [-1.25, -PD + .012, -1.05], [-1.5, -PD + .012, -.55]];
  const mR = new THREE.MeshBasicMaterial({ color: 0x1b1712 }); const rs = [];
  for (let i = 0; i < RP.length - 1; i++) { const a = new THREE.Vector3(...RP[i]), b = new THREE.Vector3(...RP[i + 1]), m = add(new THREE.Mesh(new THREE.BoxGeometry(.05, 1, .012).translate(0, .5, 0), mR), g); m.position.copy(a); m.quaternion.setFromUnitVectors(UP, b.clone().sub(a).normalize()); rs.push({ m, n: a.distanceTo(b), i }); }
  AUTO.push(t => { const k = .62 + .38 * ease(t / 1.1); rs.forEach(q => { const f = clamp(k * rs.length - q.i); q.m.visible = f > 0; q.m.scale.set(1.5 + 1.2 * ease(t / 2), Math.max(f * q.n, .001), 1); }); });
  // redemoinho e bolhas descendo pela trinca
  const VX = -1.5, VZ = -.6, aneis = [.22, .42, .62, .85].map((r, i) => { const m = add(new THREE.Mesh(new THREE.TorusGeometry(r, .022, 6, 40, PI * 1.5), brilho(0xe8fbff, { transparent: true, opacity: .75 })), g); m.rotation.x = -PI / 2; return m; });
  const BO = inst(new THREE.SphereGeometry(.035, 8, 6), brilho(0xffffff, { transparent: true, opacity: .8 }), 30, g, false);
  AUTO.push(t => { if (t > F(1)) return; const y = -PD + NIV0(t); aneis.forEach((m, i) => { m.position.set(VX, y + .01 - i * .004, VZ); m.rotation.z = t * (6 - i) + i; m.scale.setScalar(1 - .1 * Math.sin(t * 5 + i)); }); for (let i = 0; i < 30; i++) { const q = (t * .9 + i / 30) % 1, a = q * 14 + i, r = .5 * (1 - q); pose(BO, i, VX + Math.cos(a) * r, y - q * (y + PD), VZ + Math.sin(a) * r, 0, 1); } BO.instanceMatrix.needsUpdate = true; });
  // pedaço da borda que despenca na água
  const peca = B(g, .9, .24, .55, 0x9c968a, PX - .45, -.12, PZ + .17, .03); AUTO.push(t => { const k = clamp((t - .05) / 1.05); peca.position.set(PX - .45 - k * .5, -.12 - (k * k) * (1.1), PZ + .17 - k * .55); peca.rotation.set(k * 1.6, 0, k * .7); }); B(g, .9, .1, .4, 0x7c7468, PX - .45, -.02, PZ + .35, .02);
  // lama que se espalha no gramado atrás da piscina
  const lama = add(new THREE.Mesh(new THREE.CircleGeometry(1, 40), mat(0x5a3d26, { roughness: .25, metalness: .1 })), g); lama.rotation.x = -PI / 2; lama.position.set(-1.2, .014, -EZ - 1.9); lama.receiveShadow = true;
  const poca = add(new THREE.Mesh(new THREE.CircleGeometry(1, 40), mat(0x7a6040, { roughness: .08, metalness: .25 })), g); poca.rotation.x = -PI / 2; poca.position.set(-1.5, .02, -EZ - 2.1);
  const BL = inst(new THREE.SphereGeometry(.1, 8, 6), mat(0x8a6a48, { roughness: .1 }), 18, g, false), JT = inst(new THREE.SphereGeometry(.05, 6, 5), brilho(0xbfeaff), 48, g, false);
  AUTO.push(t => { if (t > F(1)) return; const r = .9 + 1.3 * ease(t / Math.max(T0L + .8, 2.5)); lama.scale.set(r * 1.4, r * .8, 1); poca.scale.set(r * .9, r * .55, 1); for (let i = 0; i < 18; i++) { const q = (t * 1.3 + i * .37) % 1, a = i * 2.4; pose(BL, i, -1.2 + Math.cos(a) * r * .8 * (i % 3) / 2, .02, -EZ - 1.9 + Math.sin(a) * r * .4 * (i % 3) / 2, 0, Math.sin(q * PI) * 1.3 + .01); } BL.instanceMatrix.needsUpdate = true;
    for (let i = 0; i < 48; i++) { const j = i % 4, q = (t * 1.6 + i / 12) % 1, jx = [-1.9, -1.2, -.6, -1.5][j], jz = -EZ - [.7, 1.4, 1.1, 2.3][j], a = i * 1.7; pose(JT, i, jx + Math.cos(a) * q * .25, q * (1 - q) * 2.6, jz + Math.sin(a) * q * .25, 0, 1 - q * .5); } JT.instanceMatrix.needsUpdate = true; });
  // dono desesperado do lado da piscina
  const dono = gente(g, 2.6, 0, -EZ - 1.3, -.5, { camisa: 0xe8683f }); AUTO.push(t => { dono.r.anda(0, 0); dono.r.respira(t); dono.r.be.j.rotation.x = dono.r.bd.j.rotation.x = -2.7 + Math.sin(t * 6) * .12; dono.r.be.j.rotation.z = -.5; dono.r.bd.j.rotation.z = .5; dono.r.be.k.rotation.x = dono.r.bd.k.rotation.x = -1.5; dono.rotation.y = -.5 + Math.sin(t * 2.2) * .2; }); }

// ÁGUA (a mesma da abertura, do enchimento e da noite) ----------------------------------------------------------------------------
const caus = tex(256, 256, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); g.lineWidth = 1.8; for (let i = 0; i < 90; i++) { const x = rnd() * w, y = rnd() * h, rx = 9 + rnd() * 16, ry = 7 + rnd() * 12, a = rnd() * 3; g.strokeStyle = `rgba(255,255,255,${.35 + rnd() * .4})`; for (const dx of [-w, 0, w]) for (const dy of [-h, 0, h]) { g.beginPath(); g.ellipse(x + dx, y + dy, rx, ry, a, 0, 7); g.stroke(); } } }, 3, 1.5);
const caus2 = caus.clone(); caus2.needsUpdate = true; caus2.repeat.set(4, 2);
const MV = new THREE.MeshStandardMaterial({ color: 0x2fb4e4, transparent: true, opacity: .42, roughness: .1, side: THREE.BackSide, depthWrite: false });
const MT = new THREE.MeshStandardMaterial({ color: 0x47c2ec, transparent: true, opacity: .4, roughness: .05, metalness: .15, emissive: 0xffffff, emissiveMap: caus, emissiveIntensity: .22, depthWrite: false });
const VOL = add(new THREE.Mesh(new THREE.BoxGeometry(2 * PX - .05, 1, 2 * PZ - .05).translate(0, .5, 0), MV)); VOL.renderOrder = 2;
const TOPO = add(new THREE.Mesh(new THREE.PlaneGeometry(2 * PX - .05, 2 * PZ - .05).rotateX(-PI / 2), MT)); TOPO.renderOrder = 3;
const CAUF = add(new THREE.Mesh(new THREE.PlaneGeometry(2 * PX - .1, 2 * PZ - .1).rotateX(-PI / 2), new THREE.MeshBasicMaterial({ map: caus2, color: 0x9fe8ff, transparent: true, opacity: .25, blending: THREE.AdditiveBlending, depthWrite: false }))); CAUF.position.y = -PD + .035; CAUF.renderOrder = 1;
const NIV = t => { if (t < F(1) - .02) return NIV0(t); if (t < CI[7].a + .1) return 0; return Math.max(H0 * ease(rev(t, CI[7].a + .1, FILL1)), 0); };
const TURVO = t => t < F(1) ? 0 : t < T7B + .3 ? 1 : t < T7N - .1 ? 1 - .45 * rev(t, T7B + .3, T7N - .1) : .55 * (1 - ease(rev(t, T7N - .1, T7N + .8)));
const NOITE = t => ease(rev(t, CI[8].a + .1, CI[8].a + 1.4)), LUZ = t => ease(rev(t, T8L + .05, T8L + .45));
const cLim = new THREE.Color(0x2fb4e4), cTur = new THREE.Color(0x7d7a40), cTop = new THREE.Color(0x47c2ec), cTopT = new THREE.Color(0x8a8448), cGlow = new THREE.Color(0x29d6ff);
AUTO.push(t => { const h = NIV(t), u = TURVO(t), l = LUZ(t); const on = h > .02; VOL.visible = TOPO.visible = on; CAUF.visible = on && u < .6; if (!on) return; VOL.scale.y = h; VOL.position.y = -PD + .02; TOPO.position.y = -PD + .02 + h + Math.sin(t * 2) * .006;
  const ab = t < F(1) ? 1 : 0; MV.color.copy(cLim).lerp(cTur, u); MV.opacity = .42 + .5 * u + ab * .2; MT.color.copy(cTop).lerp(cTopT, u); if (ab) MT.color.setHex(0x1f8fd0); MT.opacity = .38 + .5 * u + ab * .2; MT.emissive.setHex(0xffffff).lerp(cGlow, l); MT.emissiveIntensity = .13 * (1 - u) + l * .7; caus.offset.set(t * .03, Math.sin(t * .4) * .05); caus2.offset.set(-t * .025, t * .018); CAUF.material.opacity = (.22 + l * .4) * (1 - u); CAUF.material.color.setHex(l > .1 ? 0x7ff4ff : 0x9fe8ff); });

// ESCAVAÇÃO -----------------------------------------------------------------------------------------------------------------------
const NXC = 10, NZC = 5, cw = 2 * EX / NXC, cd = 2 * EZ / NZC, COL = inst(new THREE.BoxGeometry(cw + .004, 1, cd + .004).translate(0, -.5, 0), mat(0xffffff, { roughness: 1 }), NXC * NZC, scene, true);
const afunda = t => .28 * ease(rev(t, CI[1].a + .5, CI[1].a + 1.3)), cava = (t, ix, iz) => { const span = T1D1 - T1D0, dd = span * .34, t0 = T1D0 + (ix / (NXC - 1)) * (span - dd) + iz * .04; return ED * ease(rev(t, t0, t0 + dd)); };
const kDig = t => rev(t, T1D0, T1D1);
AUTO.push(t => { const on = t >= F(1) - .02 && t < T1D1 + .15; COL.visible = on; fundoT.visible = t >= F(1) - .02; if (!on) return; const s = afunda(t); let n = 0; for (let ix = 0; ix < NXC; ix++) for (let iz = 0; iz < NZC; iz++) { const d = Math.max(s, cava(t, ix, iz)), x = -EX + cw * (ix + .5), z = -EZ + cd * (iz + .5); if (d > ED - .01) pose(COL, n, x, -ED, z, 0, 0); else pose(COL, n, x, -d, z, 0, 1, ED - d, 1); COL.setColorAt(n, C.set(d < .005 ? GR : d < .31 ? 0x8f6a3a : TERRA_S)); n++; } COL.instanceMatrix.needsUpdate = true; COL.instanceColor.needsUpdate = true; });
// fundo compactado escurece
AUTO.push(t => { fundoT.material.color.setHex(0x9a6a46).lerp(C.setHex(0x6f4a30), ease(rev(t, T1C, fim(1)))); });
// fantasma de água pesando no gramado + setas para baixo
const fantasma = (c, op) => { const m = add(new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1).translate(0, .5, 0), new THREE.MeshStandardMaterial({ color: c, transparent: true, opacity: op, roughness: .15, depthWrite: false }))); m.visible = false; m.renderOrder = 4; return m; };
const MSETA = brilho(0xff3b30); const seta = (p, dir, len = 1.1) => { const g = new THREE.Group(); add(new THREE.Mesh(new THREE.CylinderGeometry(.07, .07, len * .62, 10).translate(0, len * .31, 0), MSETA), g); add(new THREE.Mesh(new THREE.ConeGeometry(.2, len * .38, 14).translate(0, len * .81, 0), MSETA), g); g.position.set(...p); g.quaternion.setFromUnitVectors(UP, new THREE.Vector3(...dir).normalize()); g.p0 = new THREE.Vector3(...p); g.d = new THREE.Vector3(...dir).normalize(); add(g); g.visible = false; return g; };
const setas = (L, a, b) => { L.forEach((s, i) => AUTO.push(t => { s.visible = t > a && t < b; if (s.visible) s.position.copy(s.p0).addScaledVector(s.d, Math.abs(Math.sin(t * 6 + i)) * .25); })); };
{ const fa = fantasma(0x3aa0e8, .5); fa.scale.set(2 * EX - .1, 1.45, 2 * EZ - .1); const a = CI[1].a + .15, b = CI[1].e + .1; AUTO.push(t => { fa.visible = t > a && t < b + .5; if (!fa.visible) return; const k = ease(rev(t, a, a + .4)), f = 1 - ease(rev(t, b, b + .5)); fa.position.y = 2.6 * (1 - k) - afunda(t); fa.material.opacity = .55 * f; });
  setas([seta([-2.6, 3.4, 0], [0, -1, 0]), seta([0, 3.4, 0], [0, -1, 0]), seta([2.6, 3.4, 0], [0, -1, 0])], a + .4, b); }
// escavadeira atrás do buraco, que anda acompanhando a frente da escavação
const EXC = pc('obra_escavadeira', scene, 0, 0, -EZ - 3.3, 0);
AUTO.push(t => { const on = t > T1D0 - .9 && t < F(2) + .4; EXC.visible = on; if (!on) return; const k = kDig(t), ent = ease(rev(t, T1D0 - .9, T1D0)); EXC.position.x = -EX + 1.1 + k * (2 * EX - 2.2) - (1 - ent) * 6; const w = Math.sin(t * 4.6); EXC.giro.rotation.y = t > T1D0 && t < T1D1 ? Math.max(0, Math.sin(t * 2.3)) * -.7 : 0; EXC.braco.rotation.x = -.26 + w * .22; EXC.antebraco.rotation.x = .42 + Math.cos(t * 4.6) * .3; EXC.cacamba.rotation.x = .3 + w * .5; });
// monte de terra, carrinho e pá
const MONTE = add(sh(new THREE.Mesh(new THREE.IcosahedronGeometry(1, 1), mat(TERRA_S, { flatShading: true, roughness: 1 })))); MONTE.position.set(-7.6, 0, -6.4);
AUTO.push(t => { const k = ease(rev(t, T1D0 + .3, T1D1 + .2)); MONTE.visible = k > 0 && t < T6P; MONTE.scale.set(2.4 * k + .01, 1.5 * k + .01, 1.9 * k + .01); });
const CARR = pc('obra_carrinho_mao', scene, -5.9, 0, -4.4, 1.2), PA = pc('obra_pa', scene, -6.4, 0, -5.4, .3); AUTO.push(t => { CARR.visible = PA.visible = t > F(1) && t < T6P; });
// compactador de placa (sapo) no fundo, com o operário atrás
const SAPO = new THREE.Group(); add(SAPO); { B(SAPO, .45, .07, .55, 0x3a3f47, 0, .035, 0, .01); B(SAPO, .34, .34, .3, 0xffc21a, 0, .26, -.05, .05); B(SAPO, .2, .14, .22, 0x2a2d33, 0, .5, -.05, .03); const c1 = add(cil(.018, .018, .9, 0x2a2d33, 8), SAPO); c1.position.set(-.16, .7, -.42); c1.rotation.x = .8; const c2 = add(cil(.018, .018, .9, 0x2a2d33, 8), SAPO); c2.position.set(.16, .7, -.42); c2.rotation.x = .8; B(SAPO, .42, .04, .04, 0x2a2d33, 0, 1.0, -.72, .01); }
const OPC = obreiro(0xff7a1a, 0, 0, 0, 0); const POE = inst(new THREE.SphereGeometry(.1, 8, 6), mat(0xb08a64, { transparent: true, opacity: .6 }), 12, scene, false);
AUTO.push(t => { const on = t > T1C - .1 && t < fim(1) + .05; SAPO.visible = OPC.visible = POE.visible = on; if (!on) return; const k = rev(t, T1C - .1, fim(1)), x = -3.6 + k * 5.2, z = Math.sin(k * 9) * 1.2, j = Math.abs(Math.sin(t * 22)) * .05; SAPO.position.set(x, -ED + j, z); SAPO.rotation.y = PI / 2 + Math.cos(k * 9) * .5; OPC.position.set(x + Math.cos(SAPO.rotation.y - PI / 2) * .95, -ED, z - Math.sin(SAPO.rotation.y - PI / 2) * .95); OPC.rotation.y = SAPO.rotation.y; OPC.r.anda(t, .4); OPC.r.be.j.rotation.x = OPC.r.bd.j.rotation.x = -1.1 + j * 2; for (let i = 0; i < 12; i++) { const q = (t * 1.8 + i / 12) % 1; pose(POE, i, x + Math.cos(i * 2.1) * q * .6, -ED + .05 + q * .3, z + Math.sin(i * 2.1) * q * .6, 0, (1 - q) * 1.2 + .01); } POE.instanceMatrix.needsUpdate = true; });

// ARMAÇÃO ---------------------------------------------------------------------------------------------------------------------------
setas([seta([0, -.8, -EZ + .05], [0, 0, 1]), seta([-2.6, -.8, -EZ + .05], [0, 0, 1]), seta([2.6, -.8, -EZ + .05], [0, 0, 1]), seta([0, -.8, EZ - .05], [0, 0, -1]), seta([-2.6, -.8, EZ - .05], [0, 0, -1]), seta([2.6, -.8, EZ - .05], [0, 0, -1]), seta([-EX + .05, -.8, 0], [1, 0, 0]), seta([EX - .05, -.8, 0], [-1, 0, 0])], CI[2].a + .25, CI[2].e + .15);
const RB = [], R_ = .019, yF = -ED + .1, xi = EX - .13, zi = EZ - .13;
{ const L1 = [], L2 = [], L3 = [];
  for (let z = -zi; z <= zi + .01; z += .26) L1.push(seg([-xi, yF, z], [xi, yF, z], R_));
  for (let x = -xi; x <= xi + .01; x += .26) L1.push(seg([x, yF + .03, -zi], [x, yF + .03, zi], R_));
  for (let x = -xi; x <= xi + .01; x += .26) { L2.push(seg([x, yF, -zi], [x, -.06, -zi], R_, { modo: 'cresce' })); L2.push(seg([x, yF, zi], [x, -.06, zi], R_, { modo: 'cresce' })); }
  for (let z = -zi + .26; z <= zi - .2; z += .26) { L2.push(seg([-xi, yF, z], [-xi, -.06, z], R_, { modo: 'cresce' })); L2.push(seg([xi, yF, z], [xi, -.06, z], R_, { modo: 'cresce' })); }
  for (let y = yF + .3; y < -.1; y += .32) { L3.push(seg([-xi, y, -zi + .03], [xi, y, -zi + .03], R_)); L3.push(seg([-xi, y, zi - .03], [xi, y, zi - .03], R_)); L3.push(seg([-xi + .03, y, -zi], [-xi + .03, y, zi], R_)); L3.push(seg([xi - .03, y, -zi], [xi - .03, y, zi], R_)); }
  const span = T2B - T2V, t1 = T2V, t2 = T2V + span * .42, t3 = T2V + span * .74;
  L1.forEach((b, i) => { b.t = t1 + i / L1.length * (t2 - t1 - .2); b.d = .28; b.dy = .9; RB.push(b); });
  L2.sort((a, b) => a.p[0] - b.p[0]).forEach((b, i) => { b.t = t2 + i / L2.length * (t3 - t2 - .2); b.d = .3; RB.push(b); });
  L3.forEach((b, i) => { b.t = t3 + i / L3.length * (T2B - t3 - .2); b.d = .25; b.dy = 1.2; RB.push(b); }); }
const REB = lote(G_CIL, mat(FERRO, { roughness: .6, metalness: .3 }), RB, FERRO); AUTO.push(t => { REB.visible = t > T2V - .1 && t < T5A; });
// armadores amarrando o aço
const ARM = [obreiro(0x2f7fd6, -2.4, -ED, -1.1, .6), obreiro(0x3fa45a, 1.2, -ED, 1.0, 2.6)];
ARM.forEach((p, i) => AUTO.push(t => { const on = t > T2V - .3 && t < CI[3].n; p.visible = on; if (!on) return; p.r.anda(0, 0); p.r.respira(t); p.r.bd.j.rotation.x = -1.3 + Math.sin(t * 9 + i) * .25; p.r.be.j.rotation.x = -1.1 + Math.cos(t * 9 + i) * .2; p.r.bd.k.rotation.x = -.6; p.position.y = -ED - .3 + .3; p.r.pe.j.rotation.x = p.r.pd.j.rotation.x = -.35; p.r.pe.k.rotation.x = p.r.pd.k.rotation.x = .6; }));

// TUBULAÇÃO -------------------------------------------------------------------------------------------------------------------------
{ const fa = fantasma(0x5f8a33, .78); fa.scale.set(2 * EX - .08, 1, 2 * EZ - .08); const a = CI[3].a + .15, b = CI[3].e + .1; const AL = inst(new THREE.CircleGeometry(.12, 7), mat(0x2f5a1c), 50, scene, false); AL.renderOrder = 5;
  for (let i = 0; i < 50; i++) pose(AL, i, -EX + .3 + rnd() * (2 * EX - .6), 0, -EZ + .3 + rnd() * (2 * EZ - .6), 0, .6 + rnd() * 1.4, 1, .6 + rnd() * 1.4, -PI / 2);
  AUTO.push(t => { fa.visible = AL.visible = t > a && t < b + .6; if (!fa.visible) return; const h = 1.3 * ease(rev(t, a, a + .5)) * (1 - ease(rev(t, b, b + .6))) + .001; fa.scale.y = h; fa.position.y = -ED + .02; AL.position.y = -ED + .03 + h; fa.material.opacity = .78; }); }
// valeta de terra até a casa de máquinas
const VALA = new THREE.Group(); add(VALA); { plano(CMx + 1.3 - (-EX), .9, 0x6e4630, (-EX + CMx + 1.3) / 2, .013, -.3, VALA); const I = inst(new THREE.IcosahedronGeometry(.2, 0), mat(TERRA_S, { flatShading: true }), 24, VALA); for (let i = 0; i < 24; i++) pose(I, i, -EX - .3 - i * .17, .03, i % 2 ? .3 : -.9, i, 1.1 + (i % 3) * .3, .6, 1); }
AUTO.push(t => { VALA.visible = t > T3C - .3 && t < T6P; });
const MPVC = mat(PVC, { roughness: .4 }), MPVC2 = mat(0xdde3e8, { roughness: .4 });
const ralo = x => { const g = new THREE.Group(); add(g); g.position.set(x, -PD + .004, 0); add(cil(.2, .2, .025, 0xf4f4f2, 24), g); for (let i = -3; i <= 3; i++) B(g, .3 - Math.abs(i) * .03, .03, .025, 0x8a9096, 0, .014, i * .045, .005); const pot = add(cil(.16, .16, ED - PD, 0xe8e8e2, 18), g); pot.position.y = -(ED - PD) / 2; return g; };
const RALOS = [ralo(-1.6), ralo(1.6)]; RALOS.forEach((r, i) => { const t0 = T3R + i * .2; AUTO.push(t => { r.visible = t > t0; r.scale.setScalar(t > t0 ? Math.max(back((t - t0) / .3), .01) : .01); }); });
const yP = yF - .02, CMin = [CMx + 1.1, .25, CMz + .2];
const CANO1 = linha([[1.6, yP, 0], [1.6, yP, .12], [-xi + .1, yP, .12], [-xi + .1, -.25, .12], [-EX - .2, .05, .12], [CMx + 1.1, .05, .12], CMin]);
const CANO2 = linha([[-1.6, yP, 0], [-1.6, yP, -.1], [-xi + .1, yP, -.1], [-xi + .1, -.25, -.1], [-EX - .2, .05, -.1], [CMx + 1.1, .05, -.1], [CMx + 1.1, .25, CMz + .2]]);
const RET = linha([[CMx + 1.1, .25, CMz - .4], [CMx + 1.1, .05, -.7], [-EX - .2, .05, -.7], [-xi + .2, -.5, -zi + .05], [xi - .2, -.5, -zi + .05]]);
const mC1 = tubo(scene, CANO1, .05, MPVC, 160), mC2 = tubo(scene, CANO2, .05, MPVC, 160), mR = tubo(scene, RET, .045, MPVC2, 160);
cresceTubo(mC1, T3C, T3F, T6P); cresceTubo(mC2, T3C + .15, T3F, T6P); cresceTubo(mR, T3C + .3, T3F + .1, T6P);
// bocais de retorno e skimmer na parede
const BOC = [-2.6, 0, 2.6].map((x, i) => { const g = new THREE.Group(); add(g); g.position.set(x, -.5, -PZ + .03); const c = add(cil(.07, .09, .1, 0xf4f4f2, 16), g); c.rotation.x = PI / 2; const f = add(cil(.035, .035, .11, 0x4c5563, 12), g); f.rotation.x = PI / 2; const t0 = T3F - .6 + i * .15; AUTO.push(t => { g.visible = t > t0; g.scale.setScalar(t > t0 ? Math.max(back((t - t0) / .3), .01) : .01); }); return g; });
const SKIM = new THREE.Group(); add(SKIM); SKIM.position.set(-3.4, -.2, -PZ + .01); B(SKIM, .45, .3, .06, 0xf4f4f2, 0, 0, .02, .02); B(SKIM, .36, .16, .07, 0x24303c, 0, .02, .02, .01); { const t0 = T3F - .2; AUTO.push(t => { SKIM.visible = t > t0; }); }

// CONCRETO PROJETADO ----------------------------------------------------------------------------------------------------------------
{ const NG = 40, GO = inst(new THREE.SphereGeometry(.05, 8, 6), brilho(0x7fd8ff), NG, scene, false); const a = CI[4].a + .2, b = CI[4].e + .2; AUTO.push(t => { GO.visible = t > a && t < b; if (!GO.visible) return; for (let i = 0; i < NG; i++) { const q = (t * .9 + i / NG) % 1, x = -EX + .4 + ((i * 37) % 40) / 40 * (2 * EX - .8), z = -EZ + .4 + ((i * 13) % 20) / 20 * (2 * EZ - .8); pose(GO, i, x, 1.2 - q * 3.4, z, 0, 1, 1.5, 1); } GO.instanceMatrix.needsUpdate = true; }); }
const CONCR = casca(CONC, 0); const kC = t => ease(rev(t, T4S, T4B)); AUTO.push(t => { CONCR.visible = t > T4S; if (CONCR.visible) CONCR.frente(FR(kC(t))); });
// bomba de concreto, mangueira e operário que projeta
const BCO = pc('obra_bomba_concreto', scene, 8.6, 0, -6.6, -PI / 2); AUTO.push(t => { BCO.visible = t > F(4) - .1 && t < F(5) + .5; });
const OPJ = obreiro(0xff7a1a, 0, 0, -EZ - .5, 0), NHS = 26, HOS = inst(new THREE.CylinderGeometry(.055, .055, 1, 8).translate(0, .5, 0), mat(0x1b1d22), NHS, scene, false);
const NSP = 70, SPR = inst(new THREE.SphereGeometry(.045, 6, 5), mat(0x9d9a92, { roughness: 1 }), NSP, scene, false); const pA = new THREE.Vector3(), pB = new THREE.Vector3(), Q0 = new THREE.Quaternion();
AUTO.push(t => { const on = t > T4A - .2 && t < fim(4); OPJ.visible = HOS.visible = on; SPR.visible = on && t > T4S && t < T4B; if (!on) return; const fx = clamp(FR(kC(t)), -EX + .6, EX - .4); OPJ.position.set(fx + .3, 0, -EZ - .55); OPJ.rotation.y = .15; OPJ.r.anda(0, 0); OPJ.r.respira(t); OPJ.r.bd.j.rotation.x = OPJ.r.be.j.rotation.x = -1.25; OPJ.r.bd.k.rotation.x = OPJ.r.be.k.rotation.x = -.4;
  const bico = [fx + .3, 1.05, -EZ - .05], cur = curva([[7.4, 1.2, -6.4], [5.5, .1, -5.6], [fx + 2.4, .08, -EZ - 1.6], [fx + .55, .6, -EZ - .9], bico]); for (let i = 0; i < NHS; i++) { cur.getPointAt(i / NHS, pA); cur.getPointAt((i + 1) / NHS, pB); O.position.copy(pA); O.quaternion.setFromUnitVectors(UP, pB.clone().sub(pA).normalize()); O.scale.set(1, pA.distanceTo(pB) + .02, 1); O.updateMatrix(); HOS.setMatrixAt(i, O.matrix); } HOS.instanceMatrix.needsUpdate = true; O.quaternion.copy(Q0);
  if (SPR.visible) for (let i = 0; i < NSP; i++) { const q = (t * 2.6 + i / NSP) % 1, u = (i * 0.618) % 1, alvo = i % 3 === 0 ? [fx - .5 + u * .6, -PD, -PZ + u * 2 * PZ] : i % 3 === 1 ? [fx - .6 + u * .7, -PD + u * PD, PZ] : [fx - .6 + u * .7, -PD + u * PD, -PZ]; pose(SPR, i, bico[0] + (alvo[0] - bico[0]) * q, bico[1] + (alvo[1] - bico[1]) * q + Math.sin(q * PI) * .25, bico[2] + (alvo[2] - bico[2]) * q, 0, 1); } SPR.instanceMatrix.needsUpdate = true; });

// IMPERMEABILIZAÇÃO -----------------------------------------------------------------------------------------------------------------
{ const fa = fantasma(0x3aa6e0, .5); fa.scale.set(2 * PX - .06, 1, 2 * PZ - .06); const a = CI[5].a + .1, b = CI[5].e + .1; AUTO.push(t => { fa.visible = t > a && t < b + .2; if (!fa.visible) return; const h = 1.25 * ease(rev(t, a, a + .35)) - 1.15 * ease(rev(t, a + .5, b + .2)) + .001; fa.scale.y = Math.max(h, .001); fa.position.y = -PD + .02; });
  const PO = inst(new THREE.CircleGeometry(.05, 8), brilho(0x3a3530), 160, scene, false); for (let i = 0; i < 160; i++) { const w = i % 4, u = rnd(), v = rnd(); if (w === 0) pose(PO, i, -PX + .2 + u * (2 * PX - .4), -PD + .006, -PZ + .2 + v * (2 * PZ - .4), 0, .6 + rnd(), 1, .6 + rnd(), -PI / 2); else if (w === 1) pose(PO, i, -PX + .2 + u * (2 * PX - .4), -PD + .1 + v * (PD - .2), -PZ + .006, 0, .6 + rnd()); else if (w === 2) pose(PO, i, -PX + .2 + u * (2 * PX - .4), -PD + .1 + v * (PD - .2), PZ - .006, PI, .6 + rnd()); else pose(PO, i, -PX + .006, -PD + .1 + v * (PD - .2), -PZ + .2 + u * (2 * PZ - .4), PI / 2, .6 + rnd()); }
  AUTO.push(t => { PO.visible = t > a + .2 && t < T5A + .3; }); }
const IMP1 = casca(0x737b86, .006, false, { roughness: .7 }), IMP2 = casca(0x3c4350, .011, false, { roughness: .45 });
AUTO.push(t => { IMP1.visible = t > T5A; IMP2.visible = t > T5M; if (IMP1.visible) IMP1.frente(FR(ease(rev(t, T5A, T5M + .1)))); if (IMP2.visible) IMP2.frente(FR(ease(rev(t, T5M, T5B)))); });
// rolo de pintura na mão do operário
const ROLO = new THREE.Group(); OPJ.r.bd.k.add(ROLO); ROLO.position.y = -.36; { const c = add(cil(.018, .018, 1.9, 0xd9b84a, 8), ROLO); c.position.y = -.95; const r = add(cil(.07, .07, .32, 0x3c4350, 14), ROLO); r.rotation.z = PI / 2; r.position.y = -1.9; }
AUTO.push(t => { const on = t > T5A - .4 && t < fim(5); ROLO.visible = on; if (!on) return; OPJ.visible = true; HOS.visible = false; SPR.visible = false; const k = t < T5M ? rev(t, T5A, T5M + .1) : rev(t, T5M, T5B), fx = clamp(-EX + k * 2 * EX, -EX + .6, EX - .4); OPJ.position.set(fx + .3, 0, -EZ - .55); OPJ.rotation.y = 0; OPJ.r.anda(0, 0); OPJ.r.bd.j.rotation.x = -1.9 + Math.sin(t * 6) * .35; OPJ.r.bd.k.rotation.x = 0; OPJ.r.be.j.rotation.x = -.3; });

// REVESTIMENTO ----------------------------------------------------------------------------------------------------------------------
// pé descalço no concreto áspero
{ const P = gente(scene, 1.4, -PD, .3, 1.9, { camisa: 0xffc21a, calca: 0x2f7fd6, sapato: 0xdca77f }), a = CI[6].a + .05, b = CI[6].e + .25, dor = add(new THREE.Mesh(new THREE.RingGeometry(.12, .2, 20), brilho(0xff3b30, { transparent: true, side: 2 }))); dor.rotation.x = -PI / 2;
  AUTO.push(t => { const on = t > a && t < b; P.visible = dor.visible = on; if (!on) return; const pul = Math.abs(Math.sin(t * 7)); P.position.y = -PD + pul * .18; P.r.respira(t); P.r.anda(0, 0); P.r.pd.j.rotation.x = -.9; P.r.pd.k.rotation.x = 1.6; P.r.bd.j.rotation.x = -.7; P.r.bd.k.rotation.x = -1; P.r.be.j.rotation.z = -1.2; P.rotation.y = 1.9 + Math.sin(t * 3) * .3; dor.position.set(1.4 + .1, -PD + .02, .3); dor.scale.setScalar(1 + ((t * 2) % 1) * 1.5); dor.material.opacity = 1 - (t * 2) % 1; }); }
const TL = [], TS = .24, TG = .006, CORP = [0x45b8e2, 0x5cc8ea, 0x2fa6d6, 0x7fd6f0, 0x3bb0dc, 0x9ae0f4], cP = () => CORP[Math.floor(rnd() * CORP.length)];
{ const span = T6C - T6P - .35, when = x => T6P + (x + PX) / (2 * PX) * span + rnd() * .06, ti = .02;
  for (let x = -PX + TS / 2 + TG; x < PX; x += TS + TG) for (let z = -PZ + TS / 2 + TG; z < PZ; z += TS + TG) TL.push({ p: [x, -PD + ti, z], s: [TS, .012, TS], c: cP(), modo: 'pop', t: when(x), d: .2 });
  for (let x = -PX + TS / 2 + TG; x < PX; x += TS + TG) for (let y = -PD + TS / 2 + TG; y < 0; y += TS + TG) { const top = y > -.3, c = top ? (Math.round(x / (TS + TG)) % 2 ? 0x1d5f9e : 0xf4f4f2) : cP(); TL.push({ p: [x, y, -PZ + ti], s: [TS, TS, .012], c, modo: 'pop', t: when(x), d: .2 }); TL.push({ p: [x, y, PZ - ti], s: [TS, TS, .012], c: top ? c : cP(), modo: 'pop', t: when(x), d: .2 }); }
  for (let z = -PZ + TS / 2 + TG; z < PZ; z += TS + TG) for (let y = -PD + TS / 2 + TG; y < 0; y += TS + TG) { const top = y > -.3, c = top ? (Math.round(z / (TS + TG)) % 2 ? 0x1d5f9e : 0xf4f4f2) : cP(); TL.push({ p: [-PX + ti, y, z], s: [.012, TS, TS], c, modo: 'pop', t: when(-PX), d: .2 }); TL.push({ p: [PX - ti, y, z], s: [.012, TS, TS], c, modo: 'pop', t: when(PX - .1), d: .2 }); } }
const TILES = lote(G_CX, mat(0xffffff, { roughness: .25, metalness: .05 }), TL);
// borda de pedra e piso de pedras em volta
const BO_ = [], PIS = [];
{ const W = .6; let i = 0; for (let x = -EX - .05 + W / 2; x < EX + .1; x += W) { BO_.push({ p: [x, .035, -(PZ + EZ) / 2 - .02], s: [W - .01, .07, EZ - PZ + .12], modo: 'pop', t: 0, d: .22, c: 0xeee6d2, k: i++ }); BO_.push({ p: [x, .035, (PZ + EZ) / 2 + .02], s: [W - .01, .07, EZ - PZ + .12], modo: 'pop', t: 0, d: .22, c: 0xe6dcc6, k: i++ }); }
  for (let z = -PZ + W / 2; z < PZ; z += W) { BO_.push({ p: [-(PX + EX) / 2 - .02, .035, z], s: [EX - PX + .12, .07, W - .01], modo: 'pop', t: 0, d: .22, c: 0xeee6d2, k: i++ }); BO_.push({ p: [(PX + EX) / 2 + .02, .035, z], s: [EX - PX + .12, .07, W - .01], modo: 'pop', t: 0, d: .22, c: 0xe6dcc6, k: i++ }); }
  BO_.forEach(b => { b.t = T6C + (b.k / i) * .9; });
  const P2 = .58; let j = 0; for (let x = -EX - 1.2; x < EX + 1.2; x += P2) for (let z = -EZ - 1.2; z < EZ + 1.2; z += P2) { const cx = x + P2 / 2, cz = z + P2 / 2; if (Math.abs(cx) < EX + .05 && Math.abs(cz) < EZ + .05) continue; PIS.push({ p: [cx, .012, cz], s: [P2 - .025, .024, P2 - .025], modo: 'pop', d: .2, c: new THREE.Color(0xd9d2c0).offsetHSL(0, 0, (rnd() - .5) * .06).getHex(), t: T6C + .5 + (Math.hypot(cx, cz) - 4) * .09 }); j++; } }
lote(G_CX, mat(0xffffff, { roughness: .85 }), BO_); lote(G_CX, mat(0xffffff, { roughness: .95 }), PIS);
// operário assentando as pastilhas
const ASS = obreiro(0x8a5bc4, 0, -PD, 0, 0); AUTO.push(t => { const on = t > T6P - .3 && t < T6C + .2; ASS.visible = on; if (!on) return; const k = rev(t, T6P, T6C), x = -PX + .7 + k * (2 * PX - 1.4); ASS.position.set(x, -PD - .25, -PZ + .7); ASS.rotation.y = PI; ASS.r.anda(0, 0); ASS.r.pe.j.rotation.x = ASS.r.pd.j.rotation.x = -1.4; ASS.r.pe.k.rotation.x = ASS.r.pd.k.rotation.x = 2.2; ASS.r.bd.j.rotation.x = -1.4 + Math.sin(t * 10) * .3; ASS.r.be.j.rotation.x = -.8; });

// FILTRO: água turva entra, bomba e tanque de areia ----------------------------------------------------------------------------------
const MANG = tubo(scene, curva([[3.6, .7, -9.3], [3.6, .3, -8.9], [3.4, .04, -7.6], [3.2, .04, -4.8], [3.1, .12, -EZ + .05], [3.0, .12, -PZ - .02], [3.0, -.2, -PZ + .25]]), .035, 0x2f9a4a, 60);
const JATO = tubo(scene, curva([[3.0, -.2, -PZ + .25], [3.0, -.45, -PZ + .55], [3.0, -1.3, -PZ + .75]]), .045, mat(0x8a8448, { transparent: true, opacity: .8 }), 20); B(scene, .08, .12, .06, 0xc9ced4, 3.6, .72, -9.3, .01);
AUTO.push(t => { MANG.visible = t > CI[7].a - .2 && t < T7N; JATO.visible = t > CI[7].a + .05 && t < FILL1; if (JATO.visible) JATO.scale.y = 1; });
// dentro da casa de máquinas: bomba, tanque de areia transparente e canos
const BOMBA = new THREE.Group(); CMg.add(BOMBA); BOMBA.position.set(-.35, .14, .55);
{ const g = BOMBA; B(g, .9, .06, .45, 0x3a3f47, 0, .03, 0, .01); const mo = add(cil(.17, .17, .5, 0x2f6fb5, 20), g); mo.rotation.z = PI / 2; mo.position.set(-.12, .25, 0); for (let i = 0; i < 7; i++) { const a = add(cil(.18, .18, .02, 0x255a94, 20), g); a.rotation.z = PI / 2; a.position.set(-.32 + i * .06, .25, 0); } const vo = add(cil(.16, .16, .14, 0x2f6fb5, 20), g); vo.rotation.z = PI / 2; vo.position.set(.22, .25, 0);
  const pre = add(cil(.13, .13, .32, 0x2f6fb5, 18), g); pre.position.set(.4, .26, 0); const tp = add(cil(.12, .12, .05, 0xbfe6f5, 18, { transparent: true, opacity: .6 }), g); tp.position.set(.4, .44, 0); }
const TANQ = new THREE.Group(); CMg.add(TANQ); TANQ.position.set(-.4, .14, -.45);
const AREIA = new THREE.Group(); TANQ.add(AREIA); const SUJ = inst(new THREE.SphereGeometry(.025, 6, 5), mat(0x5a4a2a), 120, AREIA, false);
{ const g = TANQ, pts = [[0, 0], [.34, .02], [.4, .12], [.4, .82], [.34, 1.0], [.16, 1.08], [0, 1.1]].map(([a, b]) => new THREE.Vector2(a, b)); const ca = add(new THREE.Mesh(new THREE.LatheGeometry(pts, 28), new THREE.MeshStandardMaterial({ color: 0x8fd0ff, transparent: true, opacity: .28, roughness: .1, side: 2, depthWrite: false })), g); ca.position.y = .08; ca.renderOrder = 6;
  const ped = add(cil(.37, .37, .14, 0x8a8a84, 24), g); ped.position.y = .17; const ar = add(cil(.37, .37, .42, 0xe2c88a, 24, { roughness: 1 }), g); ar.position.y = .45;
  add(cil(.3, .36, .1, 0x2a2d33, 20), g).position.y = .05; const v = add(cil(.12, .12, .14, 0x24303c, 16), g); v.position.y = 1.24; B(g, .3, .04, .06, 0x24303c, .1, 1.33, 0, .01); const m = add(cil(.06, .06, .03, 0xf4f4f2, 16), g); m.rotation.x = PI / 2; m.position.set(-.1, 1.25, .1); }
const SUJP = Array.from({ length: 120 }, () => { const a = rnd() * PI * 2, r = rnd() * .34; return [Math.cos(a) * r, .67 + rnd() * .02, Math.sin(a) * r]; });
AUTO.push(t => { const k = ease(rev(t, T7T, T7N - .1)); for (let i = 0; i < 120; i++) pose(SUJ, i, ...SUJP[i], 0, i / 120 < k ? 1 + (i % 3) * .3 : 0); SUJ.instanceMatrix.needsUpdate = true; const vib = t > T7B && t < fim(8) + 30 ? Math.sin(t * 70) * .006 : 0; BOMBA.position.y = .14 + vib; });
// canos dentro da casa de máquinas, ligados aos da valeta
const CMW = p => [p[0] + CMx, p[1], p[2] + CMz];
const CI1 = linha([CMin, CMW([.5, .4, .6]), CMW([.1, .4, .55])].map((p, i) => i ? p : p)), CI2 = linha([CMW([-.8, .4, .55]), CMW([-.8, 1.5, .55]), CMW([-.4, 1.5, .1]), CMW([-.4, 1.35, -.45])]), CI3 = linha([CMW([0, .5, -.45]), CMW([.5, .5, -.45]), CMW([1.1, .25, -.45]), [CMx + 1.1, .25, CMz - .4]]);
[CI1, CI2, CI3].forEach(c => tubo(scene, c, .045, MPVC, 40));
const corAgua = t => TURVO(t) > .5 ? 0x9a8a4a : 0x7ff0ff;
const pIn1 = pulsos(CI1, 4, 0x9a8a4a, t => t > T7B && t < T7N + 1.2, .8, .05), pIn2 = pulsos(CI2, 6, 0x9a8a4a, t => t > T7B && t < T7N + 1.2, .6, .05), pIn3 = pulsos(CI3, 4, 0x7ff0ff, t => t > T7T && t < T7N + 1.2, .8, .05);
AUTO.push(t => { pIn1.material.color.setHex(corAgua(t)); pIn2.material.color.setHex(corAgua(t)); });
// bolhas nos bocais de retorno quando a bomba liga
{ const BB = inst(new THREE.SphereGeometry(.03, 6, 5), brilho(0xffffff, { transparent: true, opacity: .7 }), 36, scene, false); AUTO.push(t => { BB.visible = t > T7B && NIV(t) > .9; if (!BB.visible) return; for (let i = 0; i < 36; i++) { const q = (t * 1.4 + i / 12) % 1, bx = [-2.6, 0, 2.6][i % 3]; pose(BB, i, bx + Math.sin(i * 3.1) * .05 * q, -.5 + q * .4, -PZ + .1 + q * .9, 0, 1 - q * .5); } BB.instanceMatrix.needsUpdate = true; }); }

// ILUMINAÇÃO e noite --------------------------------------------------------------------------------------------------------------
const LAMP = []; [-2.9, 0, 2.9].forEach(x => [-1, 1].forEach(s => { const g = new THREE.Group(); add(g); g.position.set(x, -.75, s * (PZ - .025)); const r = add(cil(.16, .16, .03, 0xc9ced4, 20), g); r.rotation.x = PI / 2; const l = add(new THREE.Mesh(new THREE.CircleGeometry(.12, 20), brilho(0x2a3038)), g); l.position.z = -s * .02; l.rotation.y = s > 0 ? PI : 0; LAMP.push({ g, l, s }); }));
LAMP.forEach((q, i) => { const t0 = T8L + .05 + i * .07; AUTO.push(t => { q.g.visible = t > T6P; q.l.material.color.setHex(t > t0 ? 0xe8ffff : 0x2a3038); }); });
const PL = [-3, 0, 3].map(x => { const p = new THREE.PointLight(0x5fe6ff, 0, 5, 2); p.position.set(x, -.9, 0); add(p); return p; });
const CASAL = new THREE.PointLight(0xffc77a, 0, 16, 1.6); CASAL.position.set(2, 2.4, -8.4); add(CASAL); const CML = new THREE.PointLight(0xffd59a, 0, 6); CML.position.set(CMx + 2, 2, CMz); add(CML);
// balizadores do jardim e varal de lâmpadas
const BAL = []; [[-6.5, 4], [-2, 4], [2.5, 4], [7, 4], [-6.5, -5], [7, -5]].forEach(([x, z]) => { B(scene, .14, .55, .14, 0x2a2d33, x, .27, z, .02); const l = B(scene, .12, .1, .12, 0x555555, x, .5, z, .02); l.material = brilho(0x555555); BAL.push(l); });
const POSTE = [[-4.8, -6.6], [7.4, -6.6]]; POSTE.forEach(([x, z]) => { B(scene, .1, 3, .1, 0x5a3d26, x, 1.5, z, .02); });
const NBU = 34, BUL = inst(new THREE.SphereGeometry(.07, 10, 8), brilho(0x6b6455), NBU, scene, false); for (let i = 0; i < NBU; i++) { const u = i / (NBU - 1), x = -4.8 + u * 12.2; pose(BUL, i, x, 2.9 - Math.sin(u * PI) * .55, -6.6, 0, 1); }
const FIO = tubo(scene, curva(Array.from({ length: 12 }, (_, i) => { const u = i / 11; return [-4.8 + u * 12.2, 3 - Math.sin(u * PI) * .55, -6.6]; })), .012, 0x24272e, 40);
// espreguiçadeiras e guarda-sol que entram com a piscina pronta
const LAZ = new THREE.Group(); add(LAZ); [[-2.2, -5.3], [0, -5.3], [2.2, -5.3]].forEach(([x, z], i) => { const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = PI; LAZ.add(g); B(g, .7, .08, 1.9, 0xf4f4f2, 0, .32, 0, .03); B(g, .64, .1, 1.3, [0x2f7fd6, 0xffc21a, 0xe8683f][i], 0, .41, .25, .04); const e = B(g, .64, .1, .7, [0x2f7fd6, 0xffc21a, 0xe8683f][i], 0, .62, -.7, .04); e.rotation.x = .7; [[-.3, .8], [.3, .8], [-.3, -.8], [.3, -.8]].forEach(([a, b]) => B(g, .05, .3, .05, 0xc9ced4, a, .15, b, .01)); });
{ const g = new THREE.Group(); g.position.set(-4.4, 0, -5.4); LAZ.add(g); B(g, .5, .08, .5, 0x8a8a84, 0, .04, 0, .02); add(cil(.03, .03, 2.4, 0xf4f4f2, 8), g).position.y = 1.2; const c = add(sh(new THREE.Mesh(new THREE.ConeGeometry(1.4, .55, 8, 1, true), mat(0xe8463a, { side: 2, flatShading: true }))), g); c.position.y = 2.3; const c2 = add(sh(new THREE.Mesh(new THREE.ConeGeometry(1.42, .56, 8, 1, true), mat(0xf4f4f2, { side: 2, flatShading: true }))), g); c2.position.y = 2.3; c2.rotation.y = PI / 8; c2.scale.set(.999, 1, .999); }
AUTO.push(t => { LAZ.visible = t > T6F; });
// banhistas: dois mergulham no fim, uma boia e quem está comendo na borda
const BOIA = add(sh(new THREE.Mesh(new THREE.TorusGeometry(.38, .14, 12, 28), mat(0xff6fa8, { roughness: .4 })))); BOIA.rotation.x = -PI / 2;
const NAD = [gente(scene, 0, 0, 0, 0, { camisa: 0x2f7fd6, escala: .62 }), gente(scene, 0, 0, 0, 0, { camisa: 0xffc21a, escala: .66 })];
const COME = gente(scene, 1.6, .07, PZ + .55, PI, { camisa: 0xe8683f }); const PRATO = new THREE.Group(); COME.r.bd.k.add(PRATO); PRATO.position.set(0, -.38, .12); add(cil(.16, .13, .025, 0xf4f4f2, 20), PRATO); B(PRATO, .16, .07, .1, 0xd9a05a, 0, .04, 0, .03); B(PRATO, .15, .02, .09, 0x3fa45a, 0, .08, 0, .01);
const SPL = []; const splash = (x, z, t0) => { const r = add(new THREE.Mesh(new THREE.RingGeometry(.3, .4, 32), brilho(0xffffff, { transparent: true, side: 2 }))); r.rotation.x = -PI / 2; const I = inst(new THREE.SphereGeometry(.05, 6, 5), brilho(0xdff8ff), 20, scene, false); AUTO.push(t => { const d = t - t0, on = d > 0 && d < 1.2; r.visible = I.visible = on; if (!on) return; r.position.set(x, -PD + H0 + .04, z); r.scale.setScalar(1 + d * 3); r.material.opacity = 1 - d / 1.2; for (let i = 0; i < 20; i++) { const a = i / 20 * PI * 2, v = 1.2 + (i % 4) * .4; pose(I, i, x + Math.cos(a) * v * d * .6, -PD + H0 + v * 2.4 * d - 4.9 * d * d, z + Math.sin(a) * v * d * .6, 0, 1); } I.instanceMatrix.needsUpdate = true; }); };
const PUL = [{ p0: [-2.2, .07, -EZ - .35], p1: [-1.6, 0, -.6], t0: T9 + .55 }, { p0: [2.4, .07, -EZ - .35], p1: [2.0, 0, -.3], t0: T9 + 1.15 }];
PUL.forEach((q, i) => { const P = NAD[i], yA = -PD + H0 - .55; splash(q.p1[0], q.p1[2], q.t0 + .5); som(q.t0 + .5, 'gota'); som(q.t0 + .52, 'impact');
  AUTO.push(t => { const on = t > T9 - .05; P.visible = on; if (!on) return; P.r.respira(t); P.r.anda(0, 0); const k = rev(t, q.t0, q.t0 + .5); if (k <= 0) { P.position.set(...q.p0); P.rotation.y = 0; P.r.be.j.rotation.x = P.r.bd.j.rotation.x = -.3 + Math.sin(t * 4) * .1; } else if (k < 1) { P.position.set(q.p0[0] + (q.p1[0] - q.p0[0]) * k, q.p0[1] + (yA - q.p0[1]) * k + Math.sin(k * PI) * 1.1, q.p0[2] + (q.p1[2] - q.p0[2]) * k); P.rotation.y = 0; P.r.be.j.rotation.x = P.r.bd.j.rotation.x = -3; P.r.pe.k.rotation.x = P.r.pd.k.rotation.x = 1.2; } else { const s = t - q.t0 - .5; P.position.set(q.p1[0] + Math.sin(s * .8 + i) * .4, yA + Math.sin(t * 2.4 + i) * .04, q.p1[2] + Math.cos(s * .7) * .2); P.rotation.y = i ? -2 : 1.2; P.r.be.j.rotation.x = -2.6 + Math.sin(t * 5) * .5; P.r.bd.j.rotation.x = -2.6 + Math.cos(t * 5) * .5; P.r.be.j.rotation.z = -.4; P.r.bd.j.rotation.z = .4; } }); });
AUTO.push(t => { BOIA.visible = t > T9 - .05; BOIA.position.set(.8 + Math.sin(t * .4) * .5, -PD + H0 + .04 + Math.sin(t * 2) * .02, .9 + Math.cos(t * .3) * .3); BOIA.rotation.z = t * .2;
  COME.visible = t > T9 - .05; if (COME.visible) { COME.r.anda(0, 0); COME.r.respira(t); COME.r.bd.j.rotation.x = -1.1; COME.r.bd.k.rotation.x = -.9; COME.r.be.j.rotation.x = -1.5 + (t > T9C ? Math.abs(Math.sin(t * 4)) * .4 : 0); COME.r.be.k.rotation.x = -1.5; COME.r.cab.rotation.x = t > T9C && t < T9V ? .25 : 0; } });

// céu, sol e noite ----------------------------------------------------------------------------------------------------------------
const frenteN = add(new THREE.DirectionalLight(0x6f86d8, 0)); frenteN.position.set(30, 20, 18);
const BG = new THREE.Color(), DIA = new THREE.Color(CEU), TARDE = new THREE.Color('#e7925a'), NO = new THREE.Color('#0b1230');
AUTO.push(t => { const n = NOITE(t), l = LUZ(t); if (n > 0) { if (n < .5) BG.copy(DIA).lerp(TARDE, n * 2); else BG.copy(TARDE).lerp(NO, (n - .5) * 2); scene.background = BG; } else scene.background = fundo;
  sol.intensity = 2.6 - n * 2.5; sol.color.setHex(n > .1 && n < .7 ? 0xffb27a : n >= .7 ? 0x8fa8ff : 0xfff2de); hemi.forEach(h => { h.intensity = 1.25 - n * 1.02; h.color.setHex(n > .6 ? 0x5a6fb0 : 0xd8ecff); }); scene.environmentIntensity = .32 - n * .25; frenteN.intensity = n * .35; scene.fog.color.setHex(n > .5 ? 0x121a36 : 0xcfe6f2);
  PL.forEach(p => { p.intensity = l * 7; }); CASAL.intensity = n * 4; CML.intensity = n * 1.5; const lb = t > T9 - .1 ? 1 : n > .8 ? .2 : 0; BUL.material.color.setHex(lb > .5 ? 0xffd27a : 0x6b6455); BAL.forEach(b => b.material.color.setHex(n > .7 ? 0xfff0c0 : 0x555555));
  let fl = 0; for (let i = 1; i < N - 1; i++) { const d = t - CI[i].n; if (d > 0 && d < .6) fl = Math.max(fl, .7 * (1 - d / .6)); } const d9 = t - T9; if (d9 > 0 && d9 < .6) fl = Math.max(fl, .8 * (1 - d9 / .6)); flash.style.opacity = fl; });

// câmera ------------------------------------------------------------------------------------------------------------------------
const K = [], Pk = (t, p, l, f = 38) => K.push({ t, p, l, f }), cut = (t, p, l, f = 38) => { const a = K[K.length - 1]; if (a) Pk(t - .02, a.p, a.l, a.f); Pk(t + .02, p, l, f); };
Pk(0, [7.6, 5.6, 4.6], [-1, -.9, -1.5], 40); Pk(T0R - .1, [6.8, 5, 4.0], [-1.1, -1, -1.4], 40);
cut(T0R, [1.8, 1.5, 1.6], [-1.6, -.9, -PZ], 38); Pk(T0L - .1, [1.4, 1.4, 1.2], [-1.6, -1, -PZ], 38);
cut(T0L, [4.4, 3.4, .6], [-1.2, -.1, -4.3], 40); Pk(T0B - .05, [4, 3.6, .3], [-1.2, -.1, -4.4], 40); cut(T0B, [10, 5.6, 5.6], [-.5, -.8, -.4], 40); Pk(fim(0), [11, 6.2, 6], [-.5, -.8, -.4], 40);
cut(F(1), [12.5, 6.4, 5.4], [-.6, -.2, -.8]); Pk(CI[1].e, [11.8, 6.4, 5], [-.6, -.4, -.8]); Pk(T1D0 + .4, [11, 7, 4.6], [-.4, -.8, -1.2]); Pk(T1C - .1, [10.5, 6.8, 4.4], [-.2, -1, -1.2]); cut(T1C, [8.6, 5, 3.6], [-1, -1.5, -.4], 40); Pk(fim(1), [8, 5.2, 3.4], [-1.2, -1.6, -.4], 40);
cut(F(2), [8.6, 4.4, 3.4], [-.6, -1.2, -.8]); Pk(T2V, [8.8, 4.8, 3.6], [-.6, -1.3, -.6]); Pk(CI[2].n, [8.5, 7.8, 3.6], [-.8, -1.5, -.3]); Pk(fim(2), [8, 8.4, 3.4], [-.8, -1.5, -.3]);
cut(F(3), [10, 5.6, 4.4], [-.5, -1, -.6]); Pk(T3R + .4, [8, 5, 3.6], [-.5, -1.4, -.3]); cut(T3C, [4, 4.4, 4.4], [-7, -.5, -.6], 40); Pk(T3F, [3, 4.6, 4.6], [-7.8, -.3, -.6], 40); cut(CI[3].n, [8.6, 4.4, 4.2], [-1, -1, -.8]); Pk(fim(3), [8.2, 4.6, 4.2], [-1, -1, -.8]);
const fx4 = k => FR(k); cut(F(4), [10.5, 5.6, 4.6], [-.5, -1, -.8]); Pk(T4S, [fx4(0) + 7, 4.4, 4.6], [fx4(0) + 1, -.9, -1]); Pk((T4S + T4B) / 2, [fx4(.5) + 7, 4.4, 4.6], [fx4(.5) + .6, -.9, -1]); Pk(T4B, [fx4(1) + 6.4, 4.8, 4.6], [fx4(1) - .6, -1, -1]); Pk(fim(4), [10, 6.6, 4.8], [-.4, -1.1, -.6]);
cut(F(5), [8.4, 4.4, 3.8], [-.8, -1.1, -.6]); Pk(T5A, [8, 4.6, 3.6], [-.8, -1.1, -.6]); Pk(T5B, [9.8, 6, 4.4], [-.6, -1.1, -.6]); Pk(fim(5), [10, 6.2, 4.6], [-.6, -1.1, -.6]);
cut(F(6), [7, 2.9, 3.4], [1.2, -.8, .2], 40); Pk(CI[6].e, [6.6, 2.9, 3.2], [1.2, -.9, .1], 40); cut(T6P, [10, 5.4, 4.4], [-.6, -1, -.6]); Pk(T6C - .1, [9.4, 5.6, 4.2], [-.6, -1, -.6]); cut(T6C, [11, 7.6, 7], [-.4, -.4, -.4]); Pk(fim(6), [12, 8.4, 7.6], [-.4, -.4, -.6]);
cut(F(7), [9.2, 4, 4.8], [.2, -1, -.6]); Pk(T7B - .05, [8.6, 3.8, 4.4], [.2, -1.1, -.6]); cut(T7B, [-5.6, 1.7, -.15], [-10.6, .8, -.35], 40); Pk(T7N - .05, [-6.3, 1.6, -.3], [-10.6, .75, -.4], 40); cut(T7N, [9.6, 4.6, 4.8], [-.4, -1.1, -.4]); Pk(fim(7), [10.4, 5.2, 5.2], [-.4, -1.1, -.4]);
cut(F(8), [12.6, 6, 6.4], [-.6, -.6, -.6]); Pk(T8L - .05, [11.4, 5.2, 5.8], [-.6, -.8, -.6]); Pk(T8N, [8.4, 3.6, 4.4], [-.6, -1, -.6]); Pk(fim(8), [8, 3.6, 4.2], [-.6, -1, -.6]);
cut(T9, [14.5, 8.4, 9.5], [-1, -.6, -1.2]); Pk(T9C - .3, [12.5, 6.4, 8], [-.5, -.6, -.6]); cut(T9C - .25, [5.2, 2, -.6], [1.6, .9, PZ + .55], 36); Pk(T9V - .1, [4.9, 1.9, -.4], [1.6, .9, PZ + .55], 36); cut(T9V, [17, 13, 14], [-1.2, -.6, -2]); Pk(D.total + 1, [19, 15, 16], [-1.2, -.6, -2]);
K.sort((a, b) => a.t - b.t); for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01;

// rótulos e sons -------------------------------------------------------------------------------------------------------------------
const NOM = ['', 'ESCAVAÇÃO', 'ARMAÇÃO', 'TUBULAÇÃO', 'CONCRETO PROJETADO', 'IMPERMEABILIZAÇÃO', 'REVESTIMENTO', 'FILTRO', 'ILUMINAÇÃO'];
for (let i = 1; i < N - 1; i++) { const a = CI[i].n, e = rotulo(NOM[i], [540, 400], a, fim(i), 'grande'); e.style.fontSize = NOM[i].length > 14 ? '58px' : NOM[i].length > 10 ? '70px' : '88px'; e.style.transform += ' rotate(-3deg)'; som(a, 'ding'); }
const ruim = (x, a, b) => { rotulo(x, [540, 400], a, b, 'grande').style.cssText += ';font-size:66px;color:#ff5a4f'; };
ruim('VAZANDO!', 2.05, fim(0)); ruim('TERRA SOLTA', tk('terra', 1), CI[1].e); ruim('EMPURRÃO', tk('empurrão', 2), CI[2].e); ruim('ÁGUA VERDE', tk('verde', 3), CI[3].e); ruim('VAZADA', tk('vazada', 4), CI[4].e); ruim('POROS', tk('poros', 5), CI[5].e); ruim('ÁSPERO', tk('áspero', 6), CI[6].e); ruim('TURVA', tk('turva', 7), CI[7].e); ruim('ESCURO', tk('noite', 8), CI[8].e);
rotulo('PISCINA PRONTA!', [540, 400], T9 + .1, T9C - .3, 'grande').style.fontSize = '72px'; rotulo('VERDADE OU MENTIRA?', [540, 400], T9V, D.total + 1, 'grande').style.fontSize = '62px';
rotulo('CASA DE MÁQUINAS', [CMx + 1.4, 2.9, CMz], T3C + .3, CI[3].n, 'pilula'); rotulo('AREIA', [CMx - .4, .7, CMz - .45], T7T, T7N, 'ouro');
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); });
som(.05, 'crack'); som(.5, 'crack'); som(1.05, 'impact'); som(1.1, 'gota'); for (let q = .2; q < fim(0); q += .45) som(q, 'gota'); som(T0R, 'crack');
som(CI[1].a + .5, 'impact'); for (let q = T1D0; q < T1D1; q += .9) som(q, 'motor'); for (let q = T1C; q < fim(1); q += .35) som(q, 'toc');
som(CI[2].a + .3, 'crack'); for (let q = T2V; q < T2B; q += .22) som(q, 'toc');
som(CI[3].a + .2, 'gota'); som(T3R, 'pop'); som(T3R + .2, 'pop'); for (let q = T3C; q < T3F; q += .5) som(q, 'toc'); BOC.forEach((b, i) => som(T3F - .6 + i * .15, 'pop'));
for (let q = CI[4].a + .2; q < CI[4].e; q += .3) som(q, 'gota'); for (let q = T4S; q < T4B; q += .6) som(q, 'concreto'); som(T4A, 'motor');
som(CI[5].a + .2, 'gota'); som(CI[5].a + .8, 'gota'); for (let q = T5A; q < T5B; q += .7) som(q, 'chuva');
som(CI[6].a + .3, 'impact'); for (let q = T6P; q < T6C; q += .18) som(q, 'pop'); for (let q = T6C; q < T6C + 1; q += .2) som(q, 'tijolo');
for (let q = CI[7].a + .1; q < FILL1; q += .5) som(q, 'chuva'); som(T7B, 'motor'); for (let q = T7B + .4; q < T7N; q += .9) som(q, 'zumbido');
som(T8L + .05, 'pop'); for (let i = 0; i < 6; i++) som(T8L + .1 + i * .07, 'pop'); som(T8L + .3, 'riser');
som(T9 - .4, 'riser'); som(T9 + .2, 'impact'); som(T9V, 'ding');
window.CAPA_T = T9 + 2.0;
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); AUTO.forEach(f => f(t)); });
