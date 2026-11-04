// Telhado do zero, estilo personagem em mini-cidade: o pedreiro trabalha no andaime e, no fim, a chuva testa a obra.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, tex, arvore, boneco, camTo, iniciar, pal, fala, som, rotulo, D } = K3;
const E = window.ESPEC, V_ = E.variante, rnd = prng(E.semente ?? 31), F = fala, fim = i => F(i) + D.falas[i].dur, AUTO = [], LAST = D.falas.length - 1;
const nk = x => String(x).toLowerCase().normalize('NFD').replace(/[^a-z]/g, ''), tk = (w, i) => { const k = nk(w), q = D.falas[i].words?.find(p => nk(p.w).startsWith(k)); return q ? q.start : F(i) + .4; }, ult = D.falas[LAST], nPal = ult.texto.split(/[!.]/)[0].trim().split(/\s+/).length, T_USO = (ult.words[nPal - 1]?.end ?? ult.t + ult.dur) + .15;
ceu(V_.ceu[0], V_.ceu[1]); const sol = luzes(V_.sol, 0xd8ecff, 0x90b870, 2.6, 22); scene.environmentIntensity = .3;
const MAD = 0xc98d4f, MAD2 = 0xdba868, RIP = 0xe7bf85, TEL = V_.telha;
const barra = (a, b, s, c, p = scene) => { const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), m = add(box(s, A.distanceTo(B), s, c, .012), p); m.position.copy(A).add(B).multiplyScalar(.5); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), B.clone().sub(A).normalize()); return m; };
const aparece = (o, t0, d = .35, modo = 'pop') => { const s = o.scale.clone(), y = o.position.y; o.visible = false; AUTO.push(t => { const k = (t - t0) / d; o.visible = t >= t0; if (!o.visible) return; if (k >= 1) { o.scale.copy(s); o.position.y = y; return; } if (modo === 'pop') o.scale.copy(s).multiplyScalar(Math.max(back(k), .01)); else o.position.y = y + (1 - ease(k)) * 1.3; }); return o; };

// bairro -------------------------------------------------------------------------------------------
const grama = add(new THREE.Mesh(new THREE.PlaneGeometry(300, 300), mat(V_.grama, { roughness: 1 }))); grama.rotation.x = -Math.PI / 2; grama.receiveShadow = true;
const rua = add(new THREE.Mesh(new THREE.PlaneGeometry(300, 7), mat(0x3b3d45))); rua.rotation.x = -Math.PI / 2; rua.position.set(0, .02, 13); rua.receiveShadow = true;
const cal = add(new THREE.Mesh(new THREE.PlaneGeometry(300, 2.4), mat(0xd9d7d0))); cal.rotation.x = -Math.PI / 2; cal.position.set(0, .03, 8.6); cal.receiveShadow = true;
for (let x = -60; x < 60; x += 5) add(box(2.6, .02, .2, 0xf2d24a, .01)).position.set(x, .05, 13);
const vizinha = (x, z, c, tc) => { add(box(7.5, 3.2, 6, c, .05)).position.set(x, 1.6, z); const t = add(sh(new THREE.Mesh(new THREE.ConeGeometry(6, 2.4, 4), mat(tc, { flatShading: true })))); t.rotation.y = .785; t.scale.z = .8; t.position.set(x, 4.4, z); add(box(1, 2, .08, 0x7a4a26, .01)).position.set(x - 1.8, 1, z + 3.03); add(box(1.4, 1.1, .08, 0xaee3f7, .01, { roughness: .15 })).position.set(x + 1.4, 1.9, z + 3.03); add(box(9.5, .9, .14, 0xf4efe6, .02)).position.set(x, .45, z + 5); };
[[-13.5, 0xa9c9e8, 0xb5482f], [13.5, 0xf2b8c6, 0x8c5a3c], [-27, 0xd6e6c0, 0xb5482f], [27, 0xf0dba0, 0xc2502f]].forEach(([x, c, t]) => vizinha(x, -.5, c, t));
[[-6, 0xeab0a6, 0x8c5a3c], [7, 0xbfe0ef, 0xb5482f], [-20, 0xf0dba0, 0xc2502f], [20, 0xd8d0e8, 0x8c5a3c]].forEach(([x, c, t]) => vizinha(x, -15, c, t));
for (let i = 0; i < 44; i++) { const a = rnd() * 6.28, r = 24 + rnd() * 50, x = Math.cos(a) * r, z = Math.sin(a) * r - 26; if (z > 3) continue; const q = add(arvore(rnd, 1.6 + rnd() * 1.6, rnd() > .5)); q.position.set(x, 0, z); }
[[-9.5, 5.6], [9.6, 5.8], [8.9, -3.2], [-9.2, -3]].forEach(([x, z]) => { const q = add(arvore(rnd, 1.25, false)); q.position.set(x, 0, z); });
[[-14, 0xd83a3a], [16, 0x3a7fd8]].forEach(([x, c]) => { const g = new THREE.Group(); g.position.set(x, 0, 11); add(g); add(box(3.4, .55, 1.5, c, .12), g).position.y = .55; add(box(1.8, .5, 1.3, 0xaee3f7, .1, { roughness: .15 }), g).position.y = 1.05; [[-1.1, .7], [1.1, .7], [-1.1, -.7], [1.1, -.7]].forEach(([a, b]) => { const r = add(cil(.3, .3, .2, 0x1e2026, 16), g); r.rotation.x = Math.PI / 2; r.position.set(a, .3, b); }); });

// casa pronta sem telhado ---------------------------------------------------------------------------
const CREME = V_.casa;
add(box(8, 2.8, 6, CREME, .04)).position.set(0, 1.5, 0); add(box(8.5, .1, 6.5, 0xc9c5bb, .02)).position.set(0, .06, 0);
const LAJE = 3.05; add(box(8.2, .22, 6.2, 0xbfc3c8, .02)).position.set(0, LAJE - .1, 0);
add(box(1.2, 2.2, .1, 0x8a4e2b, .02)).position.set(-2.1, 1.2, 3.04); add(esf(.06, 0xe0c060)).position.set(-1.65, 1.2, 3.1);
[[.8, 1.9], [2.9, 1.9]].forEach(([x, y]) => { add(box(1.5, 1.25, .08, 0xffffff, .01)).position.set(x, y, 3.03); add(box(1.3, 1.05, .1, 0xaee3f7, .01, { roughness: .1 })).position.set(x, y, 3.05); add(box(1.7, .1, .24, 0xffffff, .01)).position.set(x, y - .68, 3.08); });
add(box(1.4, .05, 3.2, 0xd2d0c8, .02)).position.set(-2.1, .04, 4.7); for (let i = 0; i < 11; i++) { const m = add(box(.9, .75, .1, 0xf4efe6, .02)); m.position.set(-7.4 + i * .9 + (i > 4 ? 1.9 : 0), .4, 7.1); } [-3.5, 3.6].forEach((x, i) => { for (let k = 0; k < 4; k++) { const f = add(esf(.14, [0xff7aa2, 0xffd23f, 0xff8a4c][k % 3])); f.position.set(x + k * .55 - .8, .34, 3.7 + (i % 2) * .15); add(cil(.03, .03, .3, 0x3fa45a, 6)).position.set(x + k * .55 - .8, .16, 3.7 + (i % 2) * .15); } });

// andaime na frente --------------------------------------------------------------------------------
const AND = new THREE.Group(); add(AND); const ZA = 4.1, YA = 2.95;
[-4.4, -2.2, 0, 2.2, 4.4].forEach(x => { [ZA - .5, ZA + .5].forEach(z => add(cil(.04, .04, 4.6, 0x7a8796, 8), AND).position.set(x, 2.3, z)); add(cil(.03, .03, 1, 0x7a8796, 6), AND).position.set(x, YA - .1, ZA); AND.children[AND.children.length - 1].rotation.x = 1.5708; });
add(box(9.2, .08, 1.15, 0xd9a55f, .02), AND).position.set(0, YA, ZA); add(box(9.2, .05, .05, 0xffb627, .01), AND).position.set(0, YA + 1, ZA + .55);
// escada
for (let i = 0; i < 10; i++) add(box(.6, .05, .05, 0xffd23f, .01), AND).position.set(5.1, .3 + i * .3, ZA + .4); [-.28, .28].forEach(s => add(box(.05, 3.1, .05, 0xffd23f, .01), AND).position.set(5.1 + s, 1.55, ZA + .4));
// materiais ao lado
for (let a = 0; a < 3; a++) for (let c = 0; c < 4; c++) add(box(.34, .13, .62, TEL, .03), AND).position.set(-6 + a * .38, .1 + c * .15, 4.8);
for (let c = 0; c < 6; c++) add(box(3.4, .12, .14, MAD, .01), AND).position.set(6.8, .1 + (c % 3) * .15, 5.2 + Math.floor(c / 3) * .18);

// telhado -------------------------------------------------------------------------------------------
const Y0 = LAJE + .05, CUME = Y0 + 1.8, EZ = 3.9, EX = 4.7, inc = (CUME - Y0) / EZ, ang = Math.atan(inc), ys = z => CUME - Math.abs(z) * inc;
const T = { tes: tk('tesouras', 2), ter: tk('terças', 3), cai: tk('caibros', 4), rip: tk('ripas', 5), man: tk('manta', 6), tel: F(7) + .5, cum: tk('cumeeira', 8), cal: tk('calha', 9) };
for (let i = 0; i < 6; i++) { const x = -3.75 + i * 1.5, g = new THREE.Group(); g.position.x = x; add(g); const A = [0, Y0, -EZ], B = [0, Y0, EZ], C = [0, CUME, 0]; barra(A, B, .14, MAD, g); barra(A, C, .14, MAD, g); barra(B, C, .14, MAD, g); barra([0, Y0, 0], C, .11, MAD, g); [-1, 1].forEach(s => barra([0, Y0, 0], [0, ys(1.95), s * 1.95], .1, MAD, g)); aparece(g, T.tes + .25 + i * .42, .4, 'desce'); som(T.tes + .25 + i * .42, 'tijolo'); som(T.tes + .45 + i * .42, 'toc'); }
[-3.4, -2.2, -1.1, 0, 1.1, 2.2, 3.4].forEach((z, i) => { aparece(barra([-EX, ys(z) + .13, z], [EX, ys(z) + .13, z], .12, 0xb97d43), T.ter + .2 + i * .22, .3, 'desce'); som(T.ter + .2 + i * .22, 'toc'); });
for (let i = 0, x = -EX + .1; x < EX; x += .6, i++) [-1, 1].forEach(s => aparece(barra([x, ys(EZ) + .22, s * EZ], [x, CUME + .22, 0], .075, MAD2), T.cai + .15 + i * .1, .25, 'pop'));
for (let q = T.cai + .15; q < T.cai + 1.6; q += .3) som(q, 'toc');
for (let d = .2, i = 0; d < EZ; d += .36, i++) [-1, 1].forEach(s => aparece(barra([-EX, ys(d) + .28, s * d], [EX, ys(d) + .28, s * d], .04, RIP), T.rip + .1 + i * .09, .22, 'pop'));
for (let q = T.rip + .1; q < T.rip + 1; q += .22) som(q, 'pop');
[-1, 1].forEach(s => { const m = add(new THREE.Mesh(new THREE.BoxGeometry(EX * 2 - .1, .02, Math.hypot(EZ, CUME - Y0)), mat(0xdbe4ea, { metalness: .6, roughness: .32 }))); m.rotation.x = s * ang; m.position.set(0, (CUME + ys(EZ)) / 2 + .33, s * EZ / 2); m.castShadow = true; const t0 = T.man + .2 + (s > 0 ? 0 : .5); AUTO.push(t => { const k = ease((t - t0) / .9); m.visible = k > 0; m.scale.x = Math.max(k, .01); m.position.x = -EX * (1 - k); }); });
const NF = 15, NC = 30, tg = new THREE.CylinderGeometry(.215, .215, .5, 10, 1, false, 0, Math.PI), telha = new THREE.InstancedMesh(tg, mat(0xffffff, { roughness: .55, side: THREE.DoubleSide }), NF * NC * 2); telha.castShadow = true; telha.frustumCulled = false; add(telha); const OT = new THREE.Object3D(), C = new THREE.Color(), tls = [];
[1, -1].forEach(s => { for (let r = 0; r < NF; r++) { const z = EZ + .05 - (r + .5) * (EZ / NF); for (let c = 0; c < NC; c++) { tls.push({ x: -EX + .1 + (c + .5) * (EX * 2 / NC), z: s * z, s, t: T.tel + (r + ((c * 7) % 11) * .06) * .36 + (s < 0 ? .1 : 0) }); C.set(TEL).offsetHSL((rnd() - .5) * .03, 0, (rnd() - .5) * .09); telha.setColorAt(tls.length - 1, C); } } });
const fimTel = Math.max(...tls.map(b => b.t)) + .3; for (let q = T.tel; q < fimTel; q += .24) som(q, 'telha');
AUTO.push(t => { if (t > fimTel + .3 && telha.userData.ok) return; tls.forEach((b, i) => { const k = back((t - b.t) / .2); OT.position.set(b.x, ys(Math.abs(b.z)) + .36 + (1 - clamp(k)) * .7, b.z); OT.rotation.set(Math.PI / 2 + b.s * ang, 0, Math.PI / 2, 'XYZ'); OT.scale.setScalar(Math.max(k, .0001)); OT.updateMatrix(); telha.setMatrixAt(i, OT.matrix); }); telha.instanceMatrix.needsUpdate = true; if (t > fimTel + .3) telha.userData.ok = true; });
for (let i = 0; i < 13; i++) { const m = add(cil(.26, .26, .78, V_.cumeeira, 12)); m.rotation.z = Math.PI / 2; m.position.set(-EX + .4 + i * .74, CUME + .47, 0); aparece(m, T.cum + .1 + i * .13, .22, 'pop'); som(T.cum + .1 + i * .13, 'telha'); }
[-1, 1].forEach(s => { const m = add(new THREE.Shape ? new THREE.Mesh(new THREE.ExtrudeGeometry((() => { const f = new THREE.Shape(); f.moveTo(-EZ + .1, 0); f.lineTo(EZ - .1, 0); f.lineTo(0, CUME - Y0); f.closePath(); return f; })(), { depth: .14, bevelEnabled: false }), mat(CREME)) : null); m.rotation.y = Math.PI / 2; m.position.set(s * 3.98 - .07, Y0 - .02, 0); m.castShadow = true; aparece(m, T.tes + .1, .4, 'pop'); });
const yc = ys(EZ) + .16; [1, -1].forEach(s => { const c = add(box(EX * 2 + .2, .15, .2, 0xeef1f3, .03, { metalness: .3 })); c.position.set(0, yc, s * (EZ + .08)); const t0 = T.cal + .1 + (s > 0 ? 0 : .3); AUTO.push(t => { const k = ease((t - t0) / .7); c.visible = k > 0; c.scale.x = Math.max(k, .01); }); });
const des = add(cil(.075, .075, yc, 0xeef1f3, 12)); des.position.set(EX + .02, yc / 2, EZ + .08); aparece(des, T.cal + 1, .3, 'pop');

// pedreiro -------------------------------------------------------------------------------------------
const h = boneco({ cabeca: 'bloco', camisa: 0x2fbf8f, calca: 0x2b3a67, sapato: 0xe9e4d8, cabelo: 0x3a2a1e }); add(h); const r = h.r;
add(box(.47, .15, .45, 0xffc61a, .05), r.cab).position.y = .33; add(box(.32, .03, .2, 0xffc61a, .012), r.cab).position.set(0, .28, .3);
const mart = new THREE.Group(); r.bd.k.add(mart); mart.position.y = -.38; add(box(.05, .36, .05, 0x7a4a26, .012), mart).position.y = -.1; add(box(.2, .1, .1, 0x5e6a78, .02), mart).position.y = -.3; mart.rotation.x = 1.4;
// roteiro de movimento: [t, x, z, y] pontos; entre eles anda, e no destino martela
const P0 = [[0, 0, 5.4, 0]]; const Y_A = YA + .05;
const RT = [[F(0), -3.4, 5.6, 0], [F(1) + .3, 5.05, 4.85, 0], [F(1) + 1.9, 5.05, ZA + .1, Y_A], [T.tes, 3.2, ZA, Y_A], [T.ter, -3.4, ZA, Y_A], [T.cai, 2.6, ZA, Y_A], [T.rip, -2.6, ZA, Y_A], [T.man, 0, ZA, Y_A], [T.tel, 3.3, ZA, Y_A], [T.tel + 2.4, -3, ZA, Y_A], [T.cum, 2, ZA, Y_A], [T.cal, 4.2, ZA, Y_A], [T_USO - .1, 4.2, ZA, Y_A]];
const anda = (a, b, t) => { const d = Math.hypot(b[1] - a[1], b[2] - a[2], (b[3] - a[3]) * 2), dur = Math.max(.5, d / 2.2), k = clamp((t - a[0]) / dur); return { k, dur, d }; };
AUTO.push(t => {
  if (t >= T_USO) return;
  let i = 0; while (i < RT.length - 2 && t >= RT[i + 1][0]) i++;
  const a = RT[i], b = RT[i + 1], { k, dur } = anda(a, b, t), mov = k > 0 && k < 1, e = k; h.position.set(a[1] + (b[1] - a[1]) * e, a[3] + (b[3] - a[3]) * e, a[2] + (b[2] - a[2]) * e);
  if (mov && Math.abs(b[1] - a[1]) + Math.abs(b[2] - a[2]) > .05) { h.rotation.y = Math.atan2(b[1] - a[1], b[2] - a[2]); r.anda(t); r.be.j.rotation.z = 0; r.bd.j.rotation.z = 0; }
  else if (mov) { h.rotation.y = 3.14; r.anda(t * .8); }
  else { r.anda(0, 0); h.rotation.y = i >= 2 ? Math.PI + Math.sin(t * .7) * .25 : .2; r.respira(t); if (i >= 3) { const w = Math.sin(t * 9); r.bd.j.rotation.x = -2.35 + w * .42; r.bd.k.rotation.x = -.25; } }
});
for (let q = T.tes + 1; q < fim(9); q += 1.15) if (q < T.tel || q > fimTel) som(q, 'toc');

// clipe final: chove e a água corre pela calha -----------------------------------------------------------
const NCH = 700, chu = new THREE.InstancedMesh(new THREE.BoxGeometry(.018, .42, .018), new THREE.MeshBasicMaterial({ color: 0xbfe2f7, transparent: true, opacity: .7 }), NCH); chu.frustumCulled = false; add(chu); const CV = []; for (let i = 0; i < NCH; i++) CV.push([-14 + rnd() * 28, rnd(), -7 + rnd() * 21, rnd() * 3]);
const agua = new THREE.InstancedMesh(new THREE.SphereGeometry(.055, 8, 6), new THREE.MeshBasicMaterial({ color: 0x57bdf7, toneMapped: false }), 90); agua.frustumCulled = false; add(agua);
const AG = new THREE.Object3D();
AUTO.push(t => {
  const f = t >= T_USO, g = ease((t - T_USO) / .8); AND.visible = t < T_USO; chu.visible = agua.visible = f;
  sol.intensity = 2.6 - g * 1.5; scene.environmentIntensity = .3 - g * .05; renderer_sky(g);
  if (!f) return;
  CV.forEach(([x, u, z, p], i) => { const q = ((u - t * 1.25 + p) % 1 + 1) % 1, y = q * 12; AG.position.set(x, y, z); AG.rotation.set(0, 0, .05); AG.scale.set(1, 1, 1); AG.updateMatrix(); chu.setMatrixAt(i, AG.matrix); }); chu.instanceMatrix.needsUpdate = true;
  for (let i = 0; i < 90; i++) { const u = ((t * .7 + i / 90) % 1), x_ = i % 3; AG.rotation.set(0, 0, 0); AG.scale.setScalar(1); if (x_ === 0) AG.position.set(-EX + u * EX * 2, yc + .08, EZ + .08); else if (x_ === 1) AG.position.set(EX + .02, yc * (1 - u), EZ + .08); else AG.position.set(EX + .02 + u * 1.2, .08, EZ + .08 + u * 3.4); AG.updateMatrix(); agua.setMatrixAt(i, AG.matrix); } agua.instanceMatrix.needsUpdate = true;
  // pedreiro seco na porta, comemorando
  h.position.set(-2.1, 0, 3.75); h.rotation.y = .1; r.anda(0, 0); const w = Math.sin(t * 6); r.be.j.rotation.x = -2.7 + w * .15; r.bd.j.rotation.x = -2.7 - w * .15; r.be.k.rotation.x = 0; r.bd.k.rotation.x = 0; mart.visible = false;
});
const C_A = new THREE.Color(V_.ceu[0]), C_B = new THREE.Color('#6e8296'); let skyT = null;
function renderer_sky(g) { if (g <= 0) { if (skyT) { scene.background = skyT.a; } return; } if (!skyT) skyT = { a: scene.background, c: new THREE.Color() }; scene.background = skyT.c.lerpColors(C_A, C_B, g); }

// câmera ---------------------------------------------------------------------------------------------
const V = [[[-2, 2.2, 16], [-1.5, 1.9, 2], 34], [[10, 4.2, 15], [2, 2.6, 2], 34], [[11, 8.2, 15], [0, 3.7, 0], 34], [[-12, 8.4, 14.5], [0, 3.8, 0], 34], [[10, 8.6, 13], [0, 4, 0], 34], [[-9, 9.2, 13], [0, 4, .5], 34], [[0, 10.4, 14], [0, 4, .3], 34], [[12, 7.8, 13], [0, 3.9, 1], 34], [[-10, 9, 12], [0, 4.4, 0], 34], [[9.2, 3.8, 12], [3.2, 2.7, 3.2], 34]];
const K = []; V.forEach(([p, l, f], i) => { if (i) K.push({ t: F(i) + .03, ...K[K.length - 1], t: F(i) + .03 }); K.push({ t: F(i) + (i ? .85 : 0), p, l, f }); K.push({ t: fim(i), p: p.map((v, j) => j === 1 ? v : v * .965), l, f }); });
K.push({ t: F(LAST) + .03, p: K[K.length - 1].p, l: K[K.length - 1].l, f: 34 }, { t: F(LAST) + .5, p: [9, 7, 19], l: [0, 3.2, 1], f: 34 }, { t: T_USO - .02, p: [9, 7, 19], l: [0, 3.2, 1], f: 34 }, { t: T_USO, p: [9, 6.8, 24], l: [.4, 3, 1.5], f: 34 }, { t: D.total + 1, p: [5, 7.4, 24.5], l: [.4, 3, 1.5], f: 34 });
for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01;

// rótulos e sons -------------------------------------------------------------------------------------
[['SEM TELHADO', [0, 4.6, 0], F(0) + .3, fim(0), 'ruim'], ['INCLINAÇÃO', [0, 5.6, 0], tk('inclinação', 1), fim(1), 'pilula'], ['TESOURAS', [0, 6.2, 0], T.tes, fim(2), 'ouro'], ['TERÇAS', [0, 6.2, 0], T.ter, fim(3), 'ouro'], ['CAIBROS', [0, 6.3, 0], T.cai, fim(4), 'ouro'], ['RIPAS', [0, 6.3, 0], T.rip, fim(5), 'ouro'], ['MANTA', [0, 6.3, 0], T.man, fim(6), 'ouro'], ['TELHAS', [0, 6.4, 0], T.tel, fim(7), 'ouro'], ['CUMEEIRA', [0, 6.4, 0], T.cum, fim(8), 'ouro'], ['CALHA', [3.2, 3.8, 3.9], T.cal, fim(9), 'ouro']].forEach(l => { rotulo(...l); if (l[4] === 'ouro') som(l[2], 'ding'); });
rotulo('TELHADO PRONTO!', [540, 290], F(LAST) + .1, T_USO, 'grande').style.fontSize = '78px';
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); som(F(0) + .3, 'gota'); som(F(0) + 1.1, 'gota'); som(F(0) + 1.9, 'gota'); som(T_USO + .1, 'whoosh');
for (let q = T_USO; q < D.total; q += .95) som(q, 'chuva'); som(F(LAST) + .1, 'ding');
// gotas entrando pela laje, no começo
const gota = new THREE.InstancedMesh(new THREE.SphereGeometry(.06, 8, 6), new THREE.MeshBasicMaterial({ color: 0x4db4f2, toneMapped: false }), 34); gota.frustumCulled = false; add(gota); const gv = []; for (let i = 0; i < 34; i++) gv.push([-3.9 + rnd() * 7.8, -2.9 + rnd() * 5.9, rnd()]);
AUTO.push(t => { const on = t < fim(0); gota.visible = on; if (!on) return; gv.forEach(([x, z, p], i) => { AG.position.set(x, 6 - ((t * .8 + p) % 1) * 2.9, z); AG.rotation.set(0, 0, 0); AG.scale.setScalar(1); AG.updateMatrix(); gota.setMatrixAt(i, AG.matrix); }); gota.instanceMatrix.needsUpdate = true; });

window.CAPA_T = T_USO + 1.5;
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); AUTO.forEach(f => f(t)); });
