// Estilo "camadas" v2: câmera de frente para o corte, ciclo problema → máquina → nome, camada por camada.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, arvore, camTo, iniciar, fala, som, rotulo, D } = K3;
const rnd = prng(47), F = fala, fim = i => F(i) + D.falas[i].dur, N = D.falas.length, AUTO = [], O = new THREE.Object3D(), C = new THREE.Color(), PI = Math.PI;
const nk = x => String(x).toLowerCase().normalize('NFD').replace(/[^a-z]/g, ''), tk = (w, i, f = .3) => { const k = nk(w), q = D.falas[i].words?.find(p => nk(p.w).startsWith(k)); return q ? q.start : F(i) + D.falas[i].dur * f; };
const u = D.falas[N - 1], nP = u.texto.split(/[!.]/)[0].trim().split(/\s+/).length, T_USO = (u.words[nP - 1]?.end ?? fim(N - 1)) + .15;
const CEU = new THREE.Color('#2f86e0'), CHU = new THREE.Color('#62778c'), NOI = new THREE.Color('#050b1c'), BG = new THREE.Color('#2f86e0');
ceu('#2f86e0', '#cdeafa'); const fundo = scene.background; const sol = luzes(0xfff0d8, 0xd8ecff, 0x7fa860, 2.7, 48); scene.environmentIntensity = .3; const hemi = []; scene.traverse(o => { if (o.isHemisphereLight) hemi.push(o); });
const flash = document.createElement('div'); flash.style.cssText = 'position:absolute;inset:0;background:#fff8d8;opacity:0'; document.getElementById('hud').prepend(flash);

// tempos do ciclo: t0 problema, tE "Então", tN "Esse é o nome" -----------------------------------------------
const EN = i => tk('Então', i, .4), NO = i => Math.max(tk('Essa', i, 2), tk('Esse', i, 2)) < fim(i) ? Math.min(tk('Essa', i, 2), tk('Esse', i, 2)) : fim(i) - 1.2;
const nomeT = i => { const w = D.falas[i].words ?? [], q = [...w].reverse().find(p => /^(essa|esse|esses)$/.test(nk(p.w))); return q ? q.start : fim(i) - 1.2; };
const CI = {}; for (let i = 1; i < N - 1; i++) CI[i] = { a: F(i), e: EN(i), n: nomeT(i) };

// caminho ----------------------------------------------------------------------------------------------------
const CUR = new THREE.CatmullRomCurve3([[0, 0, 8], [0, 0, -24], [-3, 0, -52], [-14, 0, -82], [-38, 0, -108], [-76, 0, -124], [-130, 0, -128]].map(q => new THREE.Vector3(...q)), false, 'centripetal');
const LEN = CUR.getLength(), NE = 320, EST = []; for (let i = 0; i <= NE; i++) { const k = i / NE, p = CUR.getPointAt(k), t = CUR.getTangentAt(k); EST.push({ s: k * LEN, p, t, n: new THREE.Vector3(-t.z, 0, t.x).normalize() }); }
const naS = s => { const i = clamp(s / LEN) * NE, a = EST[Math.floor(i)], b = EST[Math.min(NE, Math.floor(i) + 1)], f = i - Math.floor(i); return { p: a.p.clone().lerp(b.p, f), t: a.t, n: a.n }; };
const W = 9; // largura da plataforma, maior que o quadro na câmera de frente
// camadas: uma entra por vez, de longe até o corte
const CAM = [{ k: 'ate', y0: 0, y1: .8, c: 0xcf8a52, i: 2 }, { k: 'sub', y0: .8, y1: 1.15, c: 0xb9a68a, i: 3 }, { k: 'las', y0: 1.15, y1: 1.7, c: 0x8f949b, i: 4 }];
const FAR = 48, DUR = { ate: 3.6, sub: 3.2, las: 3.4 }, Y_D = 1.72, Y_T = 2.02;
CAM.forEach(c => { c.t0 = CI[c.i].e + .15; c.t1 = c.t0 + DUR[c.k]; });
const borda = (c, t) => FAR * (1 - ease(clamp((t - c.t0) / (c.t1 - c.t0)))) ;
// altura do chão em qualquer ponto e instante: todo veículo usa isto, e nada flutua
const topo = (s, t) => { let y = 0; for (const c of CAM) { if (t < c.t0) break; if (t >= c.t1 || s >= borda(c, t) - .4 || s > FAR) y = c.y1; else break; } if (s > FAR && t >= CAM[2].t1) y = 1.7; return y + (t >= T_MUD && t < T_MUF && s < 26 ? -.03 : 0); };
const T_MUD = -1, T_MUF = -1;
const poe = (g, s, t, of = 0, dy = 0, frente = 1) => { const q = naS(s); g.position.copy(q.p).addScaledVector(q.n, of); g.position.y = topo(s, t) + dy; g.rotation.y = Math.atan2(q.t.x, q.t.z) + (frente > 0 ? PI : 0); };

// fita de uma camada -----------------------------------------------------------------------------------------
function fita(w, y0, y1, c, rough = .95, of = 0) {
  const pos = new Float32Array((NE + 1) * 12), idx = [], g = new THREE.BufferGeometry(); for (let i = 0; i <= NE; i++) { const e = EST[i]; [[-w / 2, y0], [-w / 2, y1], [w / 2, y1], [w / 2, y0]].forEach(([x, y], j) => { const X = x + of, o = i * 12 + j * 3; pos[o] = e.p.x + e.n.x * X; pos[o + 1] = y; pos[o + 2] = e.p.z + e.n.z * X; }); }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); for (let i = NE - 1; i >= 0; i--) for (let l = 0; l < 3; l++) { const a = i * 4 + l, b = a + 1, c_ = a + 4, d = a + 5; idx.push(a, c_, b, b, c_, d); } g.setIndex(idx); g.computeVertexNormals();
  const m = add(new THREE.Mesh(g, mat(c, { roughness: rough, side: THREE.DoubleSide }))); m.receiveShadow = true; m.frustumCulled = false; m.ver = (sMin) => { const i = Math.floor(clamp(sMin / LEN) * NE); g.setDrawRange(0, (NE - i) * 18); }; m.ver(LEN); return m;
}

// mundo ------------------------------------------------------------------------------------------------------
const perto = (x, z) => { let m = 1e9; for (let i = 0; i <= NE; i += 6) { const e = EST[i]; m = Math.min(m, Math.hypot(e.p.x - x, e.p.z - z)); } return m; };
const alt = (x, z) => { const d = perto(x, z), k = clamp((d - 8) / 20); return (Math.sin(x * .07 + 1) * Math.cos(z * .08) * 2.8 + Math.sin(x * .17) * Math.sin(z * .13 + 2) * 1.5 + 2) * k * k; };
{ const n = 150, g = new THREE.PlaneGeometry(460, 300, n, n); g.rotateX(-PI / 2); g.translate(-30, 0, -142); const p = g.attributes.position, cor = new Float32Array(p.count * 3); for (let i = 0; i < p.count; i++) { const x = p.getX(i), z = p.getZ(i), h = z > 7 ? 0 : alt(x, z); p.setY(i, h); C.set(0x35a644).offsetHSL((Math.sin(i * 12.9) * .5) * .025, .05, (Math.cos(i * 7.3) * .5) * .05 + h * .012); cor.set([C.r, C.g, C.b], i * 3); } g.setAttribute('color', new THREE.BufferAttribute(cor, 3)); g.computeVertexNormals(); const m = add(new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 1, flatShading: true }))); m.receiveShadow = true; }
const solo = add(box(460, 26, 1, 0xe0a060, .01)); solo.position.set(-30, -13, 7.5);
const SOL = [0x9a6a42, 0xb8875a, 0x7c5436, 0xcda070, 0x6e6a66, 0x8f8a84];
{ const I = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.1, 0), mat(0xffffff, { flatShading: true }), 620); for (let i = 0; i < 620; i++) { O.position.set(-9 + rnd() * 18, -1.05 - rnd() ** 1.5 * 13, 8.03); const s = i % 9 === 0 ? 1.6 + rnd() * 1.2 : .25 + rnd() * .6; O.scale.set(s * (1 + rnd() * .5), s * .75, s * .4); O.rotation.set(0, 0, rnd() * 3); O.updateMatrix(); I.setMatrixAt(i, O.matrix); I.setColorAt(i, C.set(SOL[i % 6])); } add(I); }
const hum = add(box(460, .85, .9, 0x4a2c1c, .01)); hum.position.set(-30, -.43, 7.6);
const faixa = add(new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat(0x8a5a3c))); faixa.visible = false;
const crua = fita(W, .01, .03, 0x7d4f35); crua.ver(0);
const raizes = new THREE.Group(); add(raizes); for (let i = 0; i < 26; i++) { const x = -5.6 + i * .45 + rnd() * .15, m = add(cil(.03, .015, .55, 0xf1dcbc, 6), raizes); m.position.set(x, -.44, 8.1); m.rotation.z = (i % 2 ? 1 : -1) * (.15 + rnd() * .5); if (i % 3 === 0) { const f = add(esf(.1, 0xd9791f), raizes); f.scale.set(1.9, .45, .25); f.position.set(x + .28, -.27, 8.1); } }
// mato sobre a faixa, que cai sob a lâmina
const MAT = 700, mato = new THREE.InstancedMesh(new THREE.ConeGeometry(.13, .5, 5), mat(0xffffff, { flatShading: true }), MAT), mtv = []; mato.frustumCulled = false; mato.castShadow = true; add(mato); for (let i = 0; i < MAT; i++) { const s = rnd() * 56, q = naS(s), o = (rnd() - .5) * 8.6; mtv.push({ s, x: q.p.x + q.n.x * o, z: q.p.z + q.n.z * o, k: .7 + rnd() * 1 }); mato.setColorAt(i, C.set(0x3fa844).offsetHSL(rnd() * .05, 0, (rnd() - .5) * .1)); }
for (let i = 0; i < 90; i++) { const x = -150 + rnd() * 240, z = 4 - rnd() ** .7 * 220; if (perto(x, z) < 11 || (Math.abs(x) < 7 && z > -40)) continue; const a = add(arvore(rnd, 1.1 + rnd() * 1.7, rnd() > .4)); a.position.set(x, alt(x, z) - .1, z); }
const NUV = []; { const nu = (x, y, z, s) => { const g = new THREE.Group(); g.position.set(x, y, z); g.scale.setScalar(s); add(g); NUV.push(g); [[0, 0, 1.5], [1.7, -.25, 1.05], [-1.6, -.3, 1.1], [.7, .85, 1.05], [-.7, .7, .9]].forEach(([a, b, r]) => { const m = add(new THREE.Mesh(new THREE.IcosahedronGeometry(r, 1), new THREE.MeshStandardMaterial({ color: 0xffffff, flatShading: true, roughness: 1, emissive: 0xffffff, emissiveIntensity: .28 })), g); m.position.set(a, b, 0); m.scale.y = .72; }); }; [[-13, 27, -60, 2], [8, 31, -72, 2.5], [-4, 21, -46, 1.1], [14, 22, -48, 1.3], [-24, 33, -90, 3], [30, 26, -80, 2.2], [-46, 24, -120, 3]].forEach(a => nu(...a)); }

// camadas ----------------------------------------------------------------------------------------------------
CAM.forEach(c => { c.f = fita(W, c.y0, c.y1, c.c); const f = add(sh(new THREE.Mesh(new THREE.BoxGeometry(W, c.y1 - c.y0, .06), mat(c.c, { roughness: .95 })))); f.position.set(0, (c.y0 + c.y1) / 2, 8.03); c.cap = f; f.visible = false; });
// aterro: linhas de compactação, que surgem a cada passada
const LIN = []; for (let i = 0; i < 4; i++) { const m = add(box(W, .035, .03, 0xa96a3a, .005)); m.position.set(0, .16 * (i + 1), 8.08); m.visible = false; LIN.push(m); }
// sublastro: cascalho miúdo no corte
const NCF = 260, ccf = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.05, 0), mat(0xffffff, { flatShading: true }), NCF); add(ccf); ccf.visible = false; for (let i = 0; i < NCF; i++) { O.position.set(-W / 2 + rnd() * W, .84 + rnd() * .28, 8.08); O.rotation.set(rnd() * 3, rnd() * 3, 0); O.scale.setScalar(.6 + rnd()); O.updateMatrix(); ccf.setMatrixAt(i, O.matrix); ccf.setColorAt(i, C.set([0x8d8578, 0xa89f90, 0x75706a][i % 3])); }
// lastro: pedras no corte e na superfície
const NFR = 520, pf = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.1, 0), mat(0xffffff, { flatShading: true, roughness: .9 }), NFR), pfv = []; add(pf); pf.frustumCulled = false; for (let i = 0; i < NFR; i++) { const x = -W / 2 + rnd() * W, y = 1.17 + rnd() * .53, r = rnd() * 3; pfv.push({ x, y, r, k: .7 + rnd() * .9, d: rnd() }); pf.setColorAt(i, C.set([0x8d9198, 0xa3a7ad, 0x72767e, 0xb9bcc0, 0xd2d4d6][i % 5])); }
const NP = 3600, ped = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.075, 0), mat(0xffffff, { flatShading: true, roughness: .9 }), NP), ptv = []; ped.frustumCulled = false; ped.castShadow = true; add(ped); for (let i = 0; i < NP; i++) { const s = rnd() * 52, q = naS(s), o = (rnd() - .5) * W; ptv.push({ s, x: q.p.x + q.n.x * o, y: 1.71, z: q.p.z + q.n.z * o, r: rnd() * 6, k: .75 + rnd() * .9 }); ped.setColorAt(i, C.set([0x8d9198, 0xa3a7ad, 0x72767e, 0xb9bcc0][i % 4])); }
// dormentes, trilhos, grampos
const ND = Math.floor((LEN - 3) / .72), dor = new THREE.InstancedMesh(new THREE.BoxGeometry(2.6, .2, .3), mat(0xc4c6c8, { roughness: .8 }), ND), T5 = CI[5]; dor.frustumCulled = false; dor.castShadow = dor.receiveShadow = true; add(dor);
const BIT = .72, trilho = [-1, 1].map(s => { const b = fita(.2, Y_D + .18, Y_D + .3, 0x70777f, .6, s * BIT), t = fita(.13, Y_D + .3, Y_D + .38, 0xdfe3e7, .28, s * BIT); return [b, t]; });
const NG = ND * 4, gra = new THREE.InstancedMesh(new THREE.BoxGeometry(.13, .1, .14), mat(0xff8a22, { roughness: .45 }), NG); gra.frustumCulled = false; add(gra);

// veículos ------------------------------------------------------------------------------------------------------
const roda = (g, x, y, z, r, l = .38, aro = 0xc9ced4) => { const w = new THREE.Group(); w.position.set(x, y, z); g.add(w); const m = add(cil(r, r, l, 0x1b1d22, 24), w); m.rotation.z = PI / 2; const a = add(cil(r * .55, r * .55, l + .03, aro, 18), w); a.rotation.z = PI / 2; const c_ = add(cil(r * .18, r * .18, l + .06, 0x4c5563, 10), w); c_.rotation.z = PI / 2; (g.rodas ??= []).push(w); return w; };
const B = (g, w, h, d, c, x, y, z, r = .05, o) => { const m = add(box(w, h, d, c, r, o), g); m.position.set(x, y, z); return m; };
const VID = { roughness: .15, metalness: .4 }, VD = 0x2a3540;
const grupo = () => { const g = new THREE.Group(); add(g); g.visible = false; return g; };
function trator() { const g = grupo(), Y = 0xf5b31a, E = 0x2a2d33; B(g, 2, .62, 2.7, Y, 0, .98, -.1, .1); B(g, 1.5, .28, 1.4, Y, 0, 1.4, .55, .08); B(g, 1.26, 1, 1.12, E, 0, 1.88, -.62, .06); B(g, 1.34, .08, 1.26, Y, 0, 2.42, -.62, .04);[[.0, 1.92, -.04], [.0, 1.92, -1.19]].forEach(([x, y, z]) => B(g, 1.04, .62, .04, VD, x, y, z, .01, VID)); B(g, .1, .7, .1, 0x3a3f47, .55, 1.8, .62, .03);[-1.24, 1.24].forEach(x => { B(g, .52, .68, 3.1, E, x, .36, 0, .3);[-1.1, -.4, .4, 1.1].forEach(z => { const r = add(cil(.2, .2, .56, 0x7c838c, 12), g); r.rotation.z = PI / 2; r.position.set(x, .36, z); }); });[-1, 1].forEach(s => { const a = B(g, .14, .14, 1.2, Y, s * 1.02, .62, 1.6, .03); a.rotation.x = .35; }); const lam = new THREE.Group(); lam.position.set(0, .56, 2.15); g.add(lam); B(lam, 3.5, .96, .14, Y, 0, 0, 0, .05); B(lam, 3.5, .14, .22, 0x3a3f47, 0, -.48, .06, .03); B(lam, 3.5, .1, .2, Y, 0, .5, .08, .03); return g; }
function rolo() { const g = grupo(), Y = 0xf5b31a; const c_ = add(cil(.82, .82, 2.3, 0x9aa3ad, 32, { metalness: .5, roughness: .32 }), g); c_.rotation.z = PI / 2; c_.position.set(0, .82, 1.5); g.c = c_;[-1.26, 1.26].forEach(x => { B(g, .16, 1.15, 1.2, Y, x, 1.1, 1.5, .05); }); B(g, 2.7, .25, .4, Y, 0, 1.72, 1.4, .05); B(g, 2.1, .9, 2.8, Y, 0, 1.25, -1.1, .12); B(g, 1.5, .12, 1.2, 0x2a2d33, 0, 1.76, -1.1, .03); B(g, .7, .55, .6, 0x2a2d33, 0, 2.1, -.9, .05);[[-.82, .82], [.82, .82], [-.82, -.82], [.82, -.82]].forEach(([x, z]) => { const m = cil(.05, .05, 1.6, Y, 8); add(m, g); m.position.set(x, 2.7, -1.1 + z); }); B(g, 2, .08, 1.9, Y, 0, 3.52, -1.1, .04);[-1.02, 1.02].forEach(x => roda(g, x, .62, -1.45, .62, .5, Y)); return g; }
function caminhao(cCab = 0xe8682a, cCac = 0x6b7078) { const g = grupo(); B(g, 2.2, .24, 6.3, 0x2d3036, 0, .86, -.3, .03); const k = new THREE.Group(); k.position.set(0, 1, 2.1); g.add(k); B(k, 2.3, 1.75, 1.75, cCab, 0, .9, 0, .16); B(k, 2.04, .78, .04, VD, 0, 1.2, .89, .02, VID);[-1, 1].forEach(s => B(k, .04, .7, .95, VD, s * 1.16, 1.2, .1, .02, VID)); B(k, 2.34, .22, .24, 0x2d3036, 0, .16, .95, .04); B(k, 2.3, .1, 1.7, 0xc4511f, 0, 1.8, 0, .04);[-.82, .82].forEach(x => { const f = add(new THREE.Mesh(new THREE.CircleGeometry(.14, 16), new THREE.MeshBasicMaterial({ color: 0xfff3c0, toneMapped: false })), k); f.position.set(x, .46, .885); }); const cac = new THREE.Group(); cac.position.set(0, 1, -1.05); g.add(cac); g.cac = cac; const q = new THREE.Group(); q.position.z = 1.9; q.position.y = 0; cac.add(q); const piv = new THREE.Group(); piv.position.set(0, 0, -2.2); cac.add(piv); g.piv = piv; const M = cCac; B(piv, 2.3, .12, 3.9, M, 0, .08, 1.95, .03);[-1, 1].forEach(s => { B(piv, .1, 1, 3.9, M, s * 1.12, .55, 1.95, .03); for (let i = 0; i < 5; i++) B(piv, .04, .92, .1, 0x565b63, s * 1.18, .55, .3 + i * .82, .01); }); B(piv, 2.3, 1.12, .1, M, 0, .55, 3.88, .03); B(piv, 2.3, 1, .1, M, 0, .55, .02, .03); const car = new THREE.Group(); piv.add(car); car.position.set(0, .34, 1.95); g.car = car; const mCar = mat(0x9a7a5a, { flatShading: true }); g.mCar = mCar; for (let i = 0; i < 46; i++) { const a_ = add(new THREE.Mesh(new THREE.IcosahedronGeometry(.2 + (i % 4) * .05, 0), mCar), car); const q = i * 2.4, r_ = (i % 9) / 9; a_.position.set(Math.cos(q) * .95 * r_, .12 + (1 - r_) * .38, Math.sin(q) * 1.65 * r_); a_.rotation.set(i, i * 2, 0); }[[-1.02, 2.05], [1.02, 2.05], [-1.02, -1.55], [1.02, -1.55], [-1.02, -2.5], [1.02, -2.5]].forEach(([x, z]) => roda(g, x, .52, z, .52)); return g; }
function sedan(c = 0xc92a2a) { const g = grupo(); B(g, 1.84, .5, 4.3, c, 0, .68, 0, .16); B(g, 1.6, .55, 2.1, c, 0, 1.18, -.2, .18); B(g, 1.5, .44, .04, VD, 0, 1.2, .86, .02, VID); B(g, 1.5, .44, .04, VD, 0, 1.2, -1.26, .02, VID);[-1, 1].forEach(s => B(g, .04, .4, 1.9, VD, s * .81, 1.2, -.2, .02, VID));[-.68, .68].forEach(x => { const r = add(new THREE.Mesh(new THREE.CircleGeometry(.13, 12), new THREE.MeshBasicMaterial({ color: 0xff2a2a, toneMapped: false })), g); r.position.set(x, .78, -2.16); r.rotation.y = PI; });[[-.92, 1.35], [.92, 1.35], [-.92, -1.35], [.92, -1.35]].forEach(([x, z]) => roda(g, x, .38, z, .38, .26)); return g; }
function escavadeira() { const g = grupo(), Y = 0xf5b31a; B(g, 2.4, .55, 3, 0x2a2d33, 0, .36, 0, .24); const H = new THREE.Group(); H.position.y = .68; g.add(H); g.H = H; B(H, 2.2, .95, 2.8, Y, 0, .55, -.25, .1); B(H, .9, 1, 1.05, 0x2a2d33, -.55, 1.45, .32, .05); B(H, .8, .6, .04, VD, -.55, 1.5, .86, .01, VID); const a = B(H, .42, .42, 3.4, Y, .4, 2.1, 1.5, .06); a.rotation.x = -.5; const P = new THREE.Group(); P.position.set(.4, 2.9, 3); H.add(P); g.P = P; const b = B(P, .3, 2, .3, Y, 0, -.95, 0, .05); const s = B(P, 2.6, .2, .3, 0xc4c6c8, 0, -2.05, 0, .03); g.s = s; return g; }
function loco() { const g = grupo(), R = 0xd8352f; B(g, 2.5, .3, 15, 0x2d3036, 0, 1.02, 0, .04); B(g, 2.45, 1.9, 8.4, R, 0, 2.1, -2.8, .14); B(g, 2.5, .18, 8.5, 0xffc21a, 0, 1.72, -2.8, .02); const k = B(g, 2.5, 2.5, 2.9, R, 0, 2.42, 2.9, .2); B(g, 2.5, .18, 2.95, 0xffc21a, 0, 1.72, 2.9, .02); B(g, 2.2, .85, .05, VD, 0, 3, 4.36, .03, VID);[-1, 1].forEach(s => B(g, .05, .7, 1.5, VD, s * 1.26, 3, 3.2, .03, VID)); const n = B(g, 2.3, 1.15, 2.4, 0xf4efe6, 0, 1.75, 5.5, .22); const fr = add(new THREE.Mesh(new THREE.CircleGeometry(.24, 18), new THREE.MeshBasicMaterial({ color: 0xfff6c8, toneMapped: false })), g); fr.position.set(0, 2.02, 6.71); B(g, 2.5, .34, .5, 0x2d3036, 0, 1.08, 7.1, .06); for (let i = 0; i < 6; i++) B(g, 2.47, .05, .5, 0x9c2622, 0, 2.4, -6 + i * 1.4, .01);[-4.8, -3.5, 3.5, 4.8].forEach(z => [-BIT, BIT].forEach(x => roda(g, x, .46, z, .46, .16, 0x70777f))); return g; }
function vagao(c) { const g = grupo(); B(g, 2.4, .26, 11, 0x2d3036, 0, 1.02, 0, .03); B(g, 2.5, 2.1, 10.2, c, 0, 2.2, 0, .05); for (let i = 0; i < 17; i++)[-1, 1].forEach(s => B(g, .03, 1.95, .16, 0x000000, s * 1.26, 2.2, -4.8 + i * .6, .005, { transparent: true, opacity: .16 })); B(g, 2.5, .08, 10.2, 0xe9e4d8, 0, 3.28, 0, .02);[-3.8, -2.6, 2.6, 3.8].forEach(z => [-BIT, BIT].forEach(x => roda(g, x, .46, z, .46, .16, 0x70777f))); return g; }
const m1 = trator(), m2 = rolo(), m3 = caminhao(0xe8682a), m4 = caminhao(0x2f7fd6, 0x7a8087), mC = sedan(), mE = escavadeira(), mF = caminhao(0xe8682a), lc = loco(), va = [0x2f7fd6, 0x3fa45a, 0xf0a82c, 0x8e9299, 0xd8352f, 0x2f7fd6, 0xf0a82c].map(vagao), TR = [lc, ...va]; const g0 = 13.4;
const giro = (g, d) => (g.rodas ?? []).forEach(w => { w.rotation.x = d * 1.9; });
// seta vermelha de problema
const seta = new THREE.Group(); add(seta); { const m = new THREE.MeshBasicMaterial({ color: 0xff5a3c, toneMapped: false }); add(new THREE.Mesh(new THREE.CylinderGeometry(.09, .09, .95, 12), m), seta).position.y = .7; const c_ = add(new THREE.Mesh(new THREE.ConeGeometry(.28, .5, 16), m), seta); c_.rotation.x = PI; } seta.visible = false;
const posSeta = (t, a, b, x, y, z) => { if (t > a && t < b) { seta.visible = true; seta.position.set(x, y + .35 + Math.sin(t * 8) * .14, z); return true; } return false; };
// poeira e torrões
const NPO = 60, po = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.3, 1), new THREE.MeshStandardMaterial({ color: 0xc8a57c, transparent: true, opacity: .34, flatShading: true }), NPO); po.frustumCulled = false; add(po);
const NTO = 44, tor = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.1, 0), mat(0x5e3b28, { flatShading: true }), NTO); tor.frustumCulled = false; add(tor);
// chuva, água
const NC = 900, chu = new THREE.InstancedMesh(new THREE.BoxGeometry(.014, .5, .014), new THREE.MeshBasicMaterial({ color: 0xdff0fb, transparent: true, opacity: .75 }), NC), cv = []; chu.frustumCulled = false; add(chu); for (let i = 0; i < NC; i++) cv.push([-9 + rnd() * 18, rnd(), -14 + rnd() * 34, rnd()]);
const lama = fita(W, .815, .822, 0x5a3424, .18); lama.material.transparent = true;
const agua = new THREE.InstancedMesh(new THREE.SphereGeometry(.07, 8, 6), new THREE.MeshBasicMaterial({ color: 0x57bdf7, toneMapped: false }), 60); agua.frustumCulled = false; add(agua);
// sinais
const sinais = [18, 46, 84].map(s => { const q = naS(s), g = new THREE.Group(); add(g); g.position.copy(q.p).addScaledVector(q.n, -3.2); g.position.y = 1.7; add(cil(.07, .09, 4.6, 0x3a3f47, 10), g).position.y = 2.3; add(box(.52, 1.2, .36, 0x22252b, .06), g).position.y = 4.8; g.rotation.y = Math.atan2(q.t.x, q.t.z) + PI; g.lz = [0xff3030, 0x35ff6a].map((c, k) => { const m = add(new THREE.Mesh(new THREE.CircleGeometry(.16, 18), new THREE.MeshBasicMaterial({ color: c, toneMapped: false })), g); m.position.set(0, 5.03 - k * .46, .19); return m; }); g.visible = false; return g; });
const luzT = new THREE.SpotLight(0xfff0c8, 0, 90, .34, .6, 1); add(luzT); add(luzT.target);

// animação ------------------------------------------------------------------------------------------------------
const rev = (t, a, b) => clamp((t - a) / (b - a));
const trem = (s0, t, k8) => { TR.forEach((g, i) => { const s = s0 + (i === 0 ? 0 : g0 + (i - 1) * 11.6); g.visible = s > .5 && s < LEN - 6; if (g.visible) { const q = naS(s); g.position.copy(q.p); g.position.y = Y_T - .05 + (k8 ?? 0) * bank(s) * .3; g.rotation.y = Math.atan2(q.t.x, q.t.z) + PI; g.rotation.z = -(k8 ?? 0) * bank(s) * .22; giro(g, s); } }); };
const bank = s => clamp((s - 62) / 16) * clamp((132 - s) / 14);
let bk = -1;
const dorm = t => { const kD = rev(t, CI[5].e + .1, CI[5].n), n = Math.floor(kD * Math.min(ND, 36) * 1.04) + (t > CI[5].n + .2 ? ND : 0); for (let i = 0; i < ND; i++) { const s = .4 + i * .72, q = naS(s), on = i < n; O.position.set(q.p.x, on ? Y_D + .08 : -30, q.p.z); O.rotation.set(0, Math.atan2(q.t.x, q.t.z), 0); O.scale.setScalar(1); O.updateMatrix(); dor.setMatrixAt(i, O.matrix); } dor.instanceMatrix.needsUpdate = true; return n; };
AUTO.push(t => {
  // fundos da fala 0-1: mato e raízes
  const c1 = CI[1], kL = ease(rev(t, c1.e + .1, c1.e + 3.3)), sL = 54 * (1 - kL);
  mtv.forEach((v, i) => { const on = v.s < sL; O.position.set(v.x, .2, v.z); O.rotation.set(0, i, 0); O.scale.setScalar(on ? v.k : .0001); O.updateMatrix(); mato.setMatrixAt(i, O.matrix); }); mato.instanceMatrix.needsUpdate = true;
  raizes.visible = kL < .97; const apod = rev(t, c1.a + .3, c1.e); raizes.children.forEach((m, i) => { m.material.color?.set(i % 2 ? 0xe9d2ae : 0xe9d2ae); }); hum.material.color.setHex(kL >= .97 ? 0xc98a54 : apod > 0 ? 0x3a2216 : 0x4a2c1c); crua.material.color.setHex(0x7d4f35);
  m1.visible = t > c1.e - .2 && t < c1.n + .6; if (m1.visible) { poe(m1, Math.max(sL, 1) + 2, t); m1.position.y = 0; }
  // terra por camadas
  CAM.forEach(c => { const e = borda(c, t); c.f.ver(t >= c.t0 ? Math.max(0, e) : LEN); const kc = ease(rev(t, c.t1 - .9, c.t1)); c.cap.visible = kc > 0; c.cap.scale.y = Math.max(kc, .01); c.cap.position.y = c.y0 + (c.y1 - c.y0) * kc / 2; });
  // aterro: rolo vai e volta, deixando uma linha por passada
  const ca = CAM[0]; m2.visible = t >= ca.t0 - .2 && t < CI[2].n + .9; if (m2.visible) { const e = Math.max(borda(ca, t), 0), s = e - 1.6; poe(m2, Math.max(s, .9) + (t > ca.t1 ? (t - ca.t1) * 9 : 0), t); m2.c.rotation.x = t * 5; giro(m2, t * 3); } LIN.forEach((m, i) => { m.visible = t > ca.t1 - .5 + i * .22 && t < T_USO + 30; });
  // caminhão do sublastro
  const cs = CAM[1]; m3.visible = t >= cs.t0 - .2 && t < cs.t1 + .7; if (m3.visible) { const e = Math.max(borda(cs, t), 0), s = e + 4.8, tp = t > cs.t1 ? (t - cs.t1) * 12 : 0; poe(m3, s + tp, t, 0, 0, -1); giro(m3, t * 6); m3.piv.rotation.x = -.5; } ccf.visible = t > cs.t1 - .25;
  // lastro: basculante despeja
  const cl = CAM[2]; m4.visible = t >= cl.t0 - .2 && t < cl.t1 + .8; if (m4.visible) { const e = Math.max(borda(cl, t), 0), s = e + 4.8; poe(m4, s + (t > cl.t1 ? (t - cl.t1) * 12 : 0), t, 0, 0, -1); giro(m4, t * 6); m4.piv.rotation.x = -.55; m4.mCar.color.setHex(0x8f949b); }
  const kfr = rev(t, cl.t1 - 1.1, cl.t1); pf.visible = t > cl.t1 - 1.1; if (pf.visible) { for (let i = 0; i < NFR; i++) { const v = pfv[i], q = clamp((kfr - v.d * .7) / .3); O.position.set(v.x, v.y + (1 - ease(q)) * 1.8, 8.12); O.rotation.set(v.r, v.r * 2, 0); O.scale.setScalar(Math.max(q, .001) * v.k); O.updateMatrix(); pf.setMatrixAt(i, O.matrix); } pf.instanceMatrix.needsUpdate = true; }
  const eL = t < cl.t0 ? LEN : borda(cl, t); for (let i = 0; i < NP; i++) { const v = ptv[i], on = t > cl.t0 && v.s > eL; O.position.set(v.x, on ? v.y : -40, v.z); O.rotation.set(v.r, v.r * 2, 0); O.scale.setScalar(v.k); O.updateMatrix(); ped.setMatrixAt(i, O.matrix); } ped.instanceMatrix.needsUpdate = true;
  // dormentes: a escavadeira pousa um a um
  const n = dorm(t), c5 = CI[5]; mE.visible = t > c5.e - .3 && t < c5.n + .4; if (mE.visible) { const s = .4 + Math.min(n, 36) * .72; poe(mE, s + 5.2, t, 0, 0); mE.P.rotation.x = Math.sin(t * 7) * .1; mE.s.visible = (t * 2.6 % 1) < .7; }
  // trilhos entram de longe; solda; grampos
  const a6 = F(6) + .1, kT = ease(rev(t, a6, a6 + 1.7)); trilho.flat().forEach(m => m.ver(t > a6 ? LEN * (1 - kT) : LEN));
  const c7 = CI[7], kF = rev(t, c7.e + .1, c7.n), nF = Math.floor(kF * Math.min(ND, 40)) + (t > c7.n + .1 ? ND : 0); for (let i = 0; i < ND; i++) { const s = .4 + i * .72, q = naS(s); [-1, 1].forEach((sd, j) => [-1, 1].forEach((ex, k) => { const x = sd * BIT + ex * .17, on = i < nF; O.position.set(q.p.x + q.n.x * x, on ? Y_D + .25 : -30, q.p.z + q.n.z * x); O.rotation.set(0, Math.atan2(q.t.x, q.t.z), 0); O.scale.setScalar(on ? 1 : .01); O.updateMatrix(); gra.setMatrixAt(i * 4 + j * 2 + k, O.matrix); })); } gra.instanceMatrix.needsUpdate = true;
  // curva
  const c8 = CI[8], k8 = t < c8.e ? 0 : ease(rev(t, c8.e + .2, c8.e + 1.8)); if (k8 !== bk) { bk = k8; const up = (m, y0, y1) => { const p = m.geometry.attributes.position; for (let i = 0; i <= NE; i++) { const h = bank(EST[i].s) * .62 * k8; [y0, y1, y1, y0].forEach((y, j) => p.setY(i * 4 + j, y + h)); } p.needsUpdate = true; }; up(trilho[1][0], Y_D + .18, Y_D + .3); up(trilho[1][1], Y_D + .3, Y_D + .38); }
  // trem por trecho
  let s = -999, kc = 0; if (t > c7 .a && t < c7.e + .1) s = 26 - (t - c7.a) * 9; else if (t > c8.a && t < c8.n + 1.4) { s = 128 - (t - c8.a) * 8.2; kc = k8; } else if (t > tk('Então', 9, .3) + 1 && t < T_USO) s = 74 - (t - tk('Então', 9, .3) - 1) * 7; else if (t >= T_USO) s = 158 - (t - T_USO) * 9; if (s > -200) trem(s, t, kc); else TR.forEach(g => { g.visible = false; });
  const noite = t > F(9) && t < T_USO; luzT.intensity = noite && lc.visible ? 420 : 0; if (lc.visible) { luzT.position.copy(lc.position).setY(Y_T + 2.4); const q = naS(Math.max(0, s - 24)); luzT.target.position.set(q.p.x, Y_D, q.p.z); }
  sinais.forEach(g => { g.visible = t > CI[9].e + .2; g.scale.setScalar(ease((t - CI[9].e - .2) / .4)); const verde = t > T_USO + 1.2; g.lz[0].visible = !verde; g.lz[1].visible = verde; });
  NUV.forEach(g => { g.visible = !noite; });
});
// problemas e efeitos
AUTO.push(t => {
  seta.visible = false; const c = CI;
  // 0: trilho sobre a terra, trem passa
  const velho = t < c[1].a + .5;
  // 1: raízes apodrecem e o chão afunda
  posSeta(t, c[1].a + 1.6, c[1].e - .1, .3, .35, 3);
  // 2: caminhão pesado afunda na terra fofa
  const on2 = t > c[2].a && t < c[2].e; mF.visible = on2; if (on2) { const k = rev(t, c[2].a, c[2].e - .5); mF.position.set(.4, -ease(rev(t, c[2].a + 1.4, c[2].e - .2)) * .5 + .03, -14 + k * 14.5); mF.rotation.y = 0; mF.rotation.z = -ease(rev(t, c[2].a + 1.4, c[2].e)) * .05; giro(mF, t * 7); posSeta(t, c[2].a + 1.2, c[2].e, .4, 3.4, -1); }
  // 3: chove, a terra vira lama e o carro atola
  const a3 = c[3].a, e3 = c[3].e, on3 = t > a3 - .1 && t < e3 + .15, kCh = on3 ? ease(rev(t, a3, a3 + .5)) * (1 - ease(rev(t, e3 - .25, e3 + .15))) : 0; chu.visible = on3; lama.visible = kCh > 0; if (on3) { lama.ver(0); lama.material.opacity = .92 * rev(t, a3 + .6, a3 + 2.2); mC.visible = true; const q = rev(t, a3, e3 - .6); mC.position.set(.6, .8 - ease(rev(t, a3 + 1.4, e3 - .3)) * .36, -3 + q * 5.5); mC.rotation.set(-ease(rev(t, a3 + 1.4, e3)) * .05, PI, .03); giro(mC, t * (t > e3 - 1 ? 1 : 8)); cv.forEach(([x, u_, z, p], i) => { O.position.set(x, ((u_ - t * 1.5 + p) % 1 + 1) % 1 * 14, z); O.rotation.set(0, 0, .03); O.scale.setScalar(1); O.updateMatrix(); chu.setMatrixAt(i, O.matrix); }); chu.instanceMatrix.needsUpdate = true; } else { mC.visible = false; }
  // 3b: abaulamento: água escorre para os lados
  const onA = t > c[3].n - 1 && t < fim(3); agua.visible = onA; if (onA) { for (let i = 0; i < 60; i++) { const q = (t * .9 + i * .37) % 1, sd = i % 2 ? 1 : -1; O.position.set(sd * (.4 + q * 5), 1.18 - q * .12, 4 - (i % 12) * 1.4); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); agua.setMatrixAt(i, O.matrix); } agua.instanceMatrix.needsUpdate = true; }
  // 4: tremor; 7: trilho levanta
  posSeta(t, c[4].a + .2, c[4].e - .1, .3, 1.55, -5); posSeta(t, c[7].a + 1, c[7].e, .72, 2.5, 3.5);
  // poeira da máquina da vez
  const fonte = m1.visible ? m1 : m2.visible ? m2 : m3.visible ? m3 : m4.visible ? m4 : null, ativo = !!fonte; po.visible = ativo; tor.visible = m1.visible; if (ativo) { for (let i = 0; i < NPO; i++) { const q = (t * .7 + i * .137) % 1, a_ = i * 2.4; O.position.set(fonte.position.x + Math.cos(a_) * (.7 + q * 1.6), fonte.position.y + .25 + q * 1.5, fonte.position.z + Math.sin(a_) * .8 + 1.4 + q * .4); O.rotation.set(0, 0, 0); O.scale.setScalar((.5 + q * 1.5) * (1 - q)); O.updateMatrix(); po.setMatrixAt(i, O.matrix); } po.instanceMatrix.needsUpdate = true; for (let i = 0; i < NTO; i++) { const q = (t * 1.3 + i * .29) % 1, x = (i * 1.7 % 3.2) - 1.6; O.position.set(m1.position.x + x, .1 + Math.sin(q * PI) * .9, m1.position.z + 2.4 + q * 1.3); O.rotation.set(t * 4 + i, t * 3, 0); O.scale.setScalar(.8 + (i % 3) * .5); O.updateMatrix(); tor.setMatrixAt(i, O.matrix); } tor.instanceMatrix.needsUpdate = true; }
  // céu e luz
  const gN = t > F(9) && t < T_USO ? ease((t - F(9)) / .35) : t >= T_USO && t < T_USO + .7 ? 1 - ease((t - T_USO) / .7) : 0, gC = kCh; if (gN > 0 || gC > 0) { BG.copy(CEU).lerp(CHU, gC).lerp(NOI, gN); scene.background = BG; } else scene.background = fundo; sol.intensity = 2.7 - gC * 1.6 - gN * 2.62; hemi.forEach(h => { h.intensity = 1.25 - gC * .5 - gN * 1.12; }); scene.environmentIntensity = .3 - gN * .26;
  // clarão no nome da etapa
  let fl = 0; for (let i = 1; i < N - 1; i++) { const d = t - CI[i].n; if (d > 0 && d < .62) fl = Math.max(fl, .78 * (1 - d / .62)); } flash.style.opacity = fl;
});

// câmera --------------------------------------------------------------------------------------------------------
const FR = [[0, 3.3, 19], [0, .4, 0]], K = []; const P = (t, p, l, f = 38) => K.push({ t, p, l, f });
const Z = (i, p, l) => { const a = K[K.length - 1]; if (a) P(F(i) - .02, a.p, a.l); P(F(i) + .32, p, l); };
P(0, [8, 8, 34], [-1, .5, -16]); P(F(1) - .3, [5, 6, 30], [-1, .5, -18]);
{ const c = CI[1]; P(F(1) + .28, [0, .9, 12.2], [0, -.3, 0]); P(c.a + 1.5, [0, .9, 12.2], [0, -.3, 0]); P(c.a + 1.8, [0, 3, 18], [0, .1, 0]); P(c.e - .05, [0, 3, 18], [0, .1, 0]); P(c.e + .2, [1, 3.4, 17], [0, .7, 0]); P(c.n + 1, [0, 3.4, 16], [0, .7, 0]); }
for (const i of [2, 3, 4]) { const c = CI[i], tp = CAM[i - 2].y1; P(c.a + .04, [3.5, 2.6 + tp, 13], [0, tp, -6]); P(c.e - .06, [2.5, 2.4 + tp, 11], [0, tp + .2, -6]); P(c.e + .2, FR[0], [0, .6, 0]); P(c.n - .1, [0, 3.2, 18], [0, .7, 0]); P(c.n + .22, [0, 2.2 + tp * .6, 14], [0, tp * .55, 7]); P(fim(i), [0, 2.2 + tp * .6, 13.4], [0, tp * .55, 7]); }
{ const c = CI[5]; P(c.a + .04, [2.6, 5.4, 15], [0, 1.6, -4]); P(c.n + .2, [1.8, 5, 14], [0, 1.6, -4]); P(fim(5), [1.6, 5, 13.5], [0, 1.6, -4]); }
{ const c = CI[6]; P(c.a + .04, [-2.4, 3.8, 14], [0, 1.8, -6]); P(c.n, [-1.5, 3.2, 12.4], [0, 1.8, -8]); P(fim(6), [-1, 3.2, 11.6], [0, 1.9, -8]); }
{ const c = CI[7]; P(c.a + .04, [2.2, 3.2, 13], [0, 2, -4]); P(c.e, [2, 3.2, 12], [0, 2, -4]); P(c.e + .25, [1.4, 3.4, 11.5], [.4, 1.9, 2]); P(fim(7), [1, 3.3, 10], [.4, 1.9, 2]); }
{ const c = CI[8], a = K[K.length - 1]; P(c.a - .02, a.p, a.l); P(c.a + .02, [13, 13, -55], [-22, 2.4, -96]); P(fim(8), [10, 12, -58], [-22, 2.4, -96]); }
{ const c = CI[9], a = K[K.length - 1]; P(c.a - .02, a.p, a.l); P(c.a + .02, [4.6, 4.6, 14], [-.4, 2.4, -14]); P(fim(9), [4, 4.4, 12], [-.4, 2.4, -14]); }
{ const a = K[K.length - 1]; P(F(N - 1) - .02, a.p, a.l); P(F(N - 1) + .02, [-8, 19, -60], [-36, 2, -116]); P(D.total + 1, [-40, 16, -66], [-44, 2, -120]); }
K.sort((a, b) => a.t - b.t); for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01;
// tremor da fala 4 fica por conta do deslocamento no quadro
// rótulos e sons ------------------------------------------------------------------------------------------------
const NOM = ['', 'LIMPEZA', 'ATERRO', 'SUBLASTRO', 'LASTRO', 'DORMENTES', 'TRILHO CONTÍNUO', 'FIXAÇÃO', 'SUPERELEVAÇÃO', 'SINALIZAÇÃO'];
for (let i = 1; i < N - 1; i++) { const a = CI[i].n, e = rotulo(NOM[i], [540, 410], a, fim(i), 'grande'); e.style.fontSize = '72px'; e.style.transform += ' rotate(-3deg)'; som(a, 'ding'); som(a, 'whoosh'); }
rotulo('FERROVIA PRONTA!', [540, 410], F(N - 1) + .1, T_USO + 1, 'grande').style.fontSize = '76px';
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); });
for (let i = 1; i <= 4; i++) { const c = CI[i]; for (let k = 0; k < 3.4; k += 1) som(c.e + k, 'motor'); } som(CI[1].a + 1.7, 'desaba'); som(CI[2].a + 1.6, 'impact');
for (let q = F(3); q < CI[3].e; q += .9) som(q, 'chuva'); for (let k = 0; k < 8; k++) som(CAM[2].t1 - 1 + k * .14, 'tijolo'); for (let k = 0; k < 16; k++) som(CI[5].e + k * .3, 'toc'); for (let k = 0; k < 11; k++) som(CI[7].e + k * .27, 'pop');
for (let q = T_USO; q < D.total; q += 1.1) som(q, 'motor');
window.CAPA_T = T_USO + 3;
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); AUTO.forEach(f => f(t)); });
