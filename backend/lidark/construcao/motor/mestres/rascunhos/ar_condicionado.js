// Ar-condicionado de tamanho real: a condensadora nasce no quintal, os tubos sobem a parede, a evaporadora fica no quarto e, no fim, o frio congela o quarto inteiro.
const { THREE, scene, cam, luzes, ceu, mat, add: add0, box, cil, esf, sh, clamp, ease, back, prng, arvore, boneco, camTo, iniciar, pal, fala, som, rotulo, D } = K3;
const E = window.ESPEC, V_ = E.variante, rnd = prng(E.semente ?? 31), F = fala, fim = i => F(i) + D.falas[i].dur, AUTO = [], LAST = D.falas.length - 1;
const tk = (w, i, n = 0) => { try { const q = pal(w, n); return q >= F(i) - .1 && q <= fim(i) ? q : F(i) + .4; } catch { return F(i) + .4; } };
const ult = D.falas[LAST], nPal = ult.texto.split(/[!.]/)[0].trim().split(/\s+/).length, T_USO = (ult.words[nPal - 1]?.end ?? ult.t + ult.dur) + .15;
let PAI = scene; const add = (m, p = PAI) => add0(m, p);
ceu(V_.ceu[0], V_.ceu[1]); const sol = luzes(V_.sol, 0xffe6c8, 0xb8a060, 2.9, 6); scene.environmentIntensity = .3;
const COBRE = 0xe0813c, ALU = 0xdfe6ec, FERRO = 0x3c4350, ACO = 0xaab4c0, TAMPA = V_.tampa;
const O = new THREE.Object3D(), C = new THREE.Color(), Y_ = new THREE.Vector3(0, 1, 0);
const aparece = (o, t0, d = .35, modo = 'pop', dy = 1.3) => { const s = o.scale.clone(), y = o.position.y; o.visible = false; AUTO.push(t => { const k = (t - t0) / d; o.visible = t >= t0; if (!o.visible) return; if (k >= 1) { o.scale.copy(s); o.position.y = y; return; } if (modo === 'pop') o.scale.copy(s).multiplyScalar(Math.max(back(k), .01)); else o.position.y = y + (1 - ease(k)) * dy; }); return o; };
const inst = (g, m, n, sombra = true, p = PAI) => { const i = new THREE.InstancedMesh(g, m, n); i.frustumCulled = false; i.castShadow = sombra; i.receiveShadow = sombra; p.add(i); return i; };
const anima = (im, lista, fn, tFim) => AUTO.push(t => { if (t > tFim && im.userData.ok) return; lista.forEach((b, i) => { fn(b, t); O.updateMatrix(); im.setMatrixAt(i, O.matrix); }); im.instanceMatrix.needsUpdate = true; im.userData.ok = t > tFim; });
const zera = () => { O.position.set(0, -50, 0); O.rotation.set(0, 0, 0); O.scale.setScalar(.0001); };

// casa de verdade: quarto de um lado da parede, quintal do outro. Tudo em tamanho real --------------------------------
PAI = scene; sol.shadow.normalBias = .006; sol.shadow.radius = 3;
const S = .13, HEAD = new THREE.Group(), COND = new THREE.Group(); HEAD.position.set(0, .4, 0); HEAD.scale.setScalar(S); COND.position.set(0, .02, -.2); COND.rotation.y = Math.PI; COND.scale.setScalar(S); scene.add(HEAD, COND);
const plano = (w, h, c, x, y, z) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat(c, { roughness: 1 }))); m.rotation.x = -Math.PI / 2; m.position.set(x, y, z); m.receiveShadow = true; return m; };
const grama = plano(1400, 1400, V_.grama, 0, -.02, 0);
const XE = -1.42, ZF = 4.6, AP = 3.1; // parede esquerda, fundo do quarto e altura
add(box(9, AP, .2, V_.predio, .01)).position.set(.8, AP / 2, -.1); add(box(9, .12, .22, 0xf4efe6, .01)).position.set(.8, .06, .01);
// parede esquerda com janela
add(box(.16, .85, ZF, V_.predio, .01)).position.set(XE, .425, ZF / 2); add(box(.16, AP - 2.25, ZF, V_.predio, .01)).position.set(XE, (AP + 2.25) / 2, ZF / 2); add(box(.16, 1.4, .75, V_.predio, .01)).position.set(XE, 1.55, .375); add(box(.16, 1.4, ZF - 2.45, V_.predio, .01)).position.set(XE, 1.55, 2.45 + (ZF - 2.45) / 2);
[[1.55, .78, .07, 1.7], [2.26, .07, .07, 1.7], [.84, .07, .07, 1.7]].slice(1).forEach(([y, , , l]) => add(box(.08, .07, l, 0xffffff, .01)).position.set(XE + .02, y, 1.6)); [.78, 1.6, 2.42].forEach(z => add(box(.08, 1.42, .06, 0xffffff, .01)).position.set(XE + .02, 1.55, z));
for (let i = 0; i < 18; i++) add(box(9, .018, .02, 0xc9bda8, .005)).position.set(.8, .3 + i * .16, -.21);
// assoalho
{ const n = 34, m = inst(new THREE.BoxGeometry(.17, .03, ZF + .2), mat(0xffffff, { roughness: .55 }), n); for (let i = 0; i < n; i++) { O.position.set(XE + .1 + i * .176, -.005, ZF / 2); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); m.setMatrixAt(i, O.matrix); m.setColorAt(i, C.set(0xb98352).offsetHSL(0, 0, (rnd() - .5) * .07)); } }
{ const t_ = add(box(1.5, .025, 1.6, V_.tapete, .01)); t_.position.set(1.65, .03, 2.1); }
// cama, criado-mudo, abajur, quadro, roupeiro
add(box(1.7, .3, 2.1, 0x8a5a33, .03)).position.set(0, .3, 1.1); add(box(1.8, 1, .1, 0x7a4a26, .03)).position.set(0, .55, .08); add(box(1.62, .2, 2, 0xf4efe6, .08)).position.set(0, .54, 1.12); [[-.42], [.42]].forEach(([x]) => { const p_ = add(box(.66, .15, .42, 0xffffff, .07)); p_.position.set(x, .71, .38); p_.rotation.x = .12; });
const coberta = add(box(1.68, .13, 1.32, V_.coberta, .05)); coberta.position.set(0, .68, 1.42);
[-.22, .24].forEach((x, i) => add(box(.04, .02, 1.3, 0xffffff, .01)).position.set(x * 2, .75, 1.42));
add(box(.5, .55, .46, 0x8a5a33, .03)).position.set(1.2, .275, .28); add(box(.42, .17, .02, 0x7a4a26, .01)).position.set(1.2, .4, .52); add(esf(.02, 0xe0c060)).position.set(1.2, .4, .54);
add(cil(.08, .1, .03, 0x5e6a78, 18)).position.set(1.32, .565, .2); add(cil(.015, .015, .32, 0x5e6a78, 8)).position.set(1.32, .72, .2); add(cil(.08, .15, .17, 0xfff2c8, 20)).position.set(1.32, .92, .2);
const copo = add(cil(.045, .038, .13, new THREE.MeshStandardMaterial({ color: 0xbfe6ff, transparent: true, opacity: .55, roughness: .1 }), 16)); copo.position.set(1.08, .62, .34);
{ const f_ = add(box(.8, .6, .04, 0xffffff, .01)); f_.position.set(1.5, 1.7, .02); add(box(.7, .5, .02, 0xf2b84a, .01)).position.set(1.5, 1.7, .05); add(esf(.1, 0xff7a3c)).position.set(1.62, 1.8, .06); add(box(.68, .14, .02, 0x4a9a5a, .01)).position.set(1.5, 1.52, .065); }
add(box(.9, 2.2, .55, 0xd9b98a, .02)).position.set(2.6, 1.1, .3); [2.38, 2.82].forEach(x => { add(box(.42, 2.1, .02, 0xcda873, .01)).position.set(x, 1.1, .58); add(esf(.02, 0xe0c060)).position.set(x + (x < 2.6 ? .17 : -.17), 1.1, .6); });
for (let i = 0; i < 7; i++) add(box(.09, .33, .22, [0xd8443a, 0x2f7fd6, 0xffd23f, 0x2fbf8f][i % 4], .01)).position.set(-.9 + i * .11, 2.65, .13); add(box(.9, .04, .24, 0xe0dcd2, .01)).position.set(-.57, 2.46, .13);
// cortina que o frio vai levantar
const CORT = []; for (let i = 0; i < 26; i++) { const g = new THREE.Group(); g.position.set(XE + .13, 2.34, .68 + (i < 13 ? i * .035 : 1.9 + (i - 13) * .035)); add(g); add(box(.05, 1.52, .04, i % 2 ? V_.cortina : 0xffffff, .01), g).position.y = -.76; CORT.push(g); } add(cil(.012, .012, 2.1, 0x5e6a78, 8)).rotation.x = 1.5708; scene.children[scene.children.length - 1].position.set(XE + .13, 2.36, 1.6);
// vista da janela e quintal: bairro com sol forte
const vizinha = (x, z, c, tc, ry = 0) => { const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry; add(g); add(box(7.5, 3.2, 6, c, .05), g).position.y = 1.6; const t = add(sh(new THREE.Mesh(new THREE.ConeGeometry(6, 2.4, 4), mat(tc, { flatShading: true }))), g); t.rotation.y = .785; t.scale.z = .8; t.position.y = 4.4; add(box(1, 2, .08, 0x7a4a26, .01), g).position.set(-1.8, 1, 3.03); add(box(1.4, 1.1, .08, 0xaee3f7, .01, { roughness: .15 }), g).position.set(1.4, 1.9, 3.03); };
[[-16, 2, 0xa9c9e8, 0xb5482f, 1.57], [-16, 13, 0xf2b8c6, 0x8c5a3c, 1.57], [-16, -9, 0xd6e6c0, 0xc2502f, 1.57], [-7, -13, 0xf0dba0, 0xb5482f, 0], [7, -14, 0xbfe0ef, 0x8c5a3c, 0], [-20, -16, 0xeab0a6, 0xc2502f, 0], [20, -14, 0xd8d0e8, 0xb5482f, 0]].forEach(([x, z, c, t, r_]) => vizinha(x, z, c, t, r_));
for (let i = 0; i < 44; i++) { const a = rnd() * 6.28, r_ = 8 + rnd() * 50, x = Math.cos(a) * r_ - 8, z = Math.sin(a) * r_ - 4; if (x > -2.5 && z > -2.5) continue; const q = add(arvore(rnd, 1.6 + rnd() * 1.6, rnd() > .5)); q.position.set(x, 0, z); }
for (let i = 0; i < 18; i++) add(box(.12, 1.25, .05, 0xf4efe6, .01)).position.set(-3.2 + i * .42, .62, -4.4); add(box(7.6, .07, .04, 0xe0dcd2, .01)).position.set(.4, .95, -4.36);
[[-2.2, -1.6], [2.4, -2.2]].forEach(([x, z]) => { const q = add(arvore(rnd, 1.1, false)); q.position.set(x, 0, z); });
for (let i = 0; i < 9; i++) { const f = add(esf(.05, [0xc98a5a, 0xb78b4a, 0xd0a060][i % 3])); f.position.set(-1.9 + i * .18, .06, -.6); f.scale.y = .6; add(cil(.008, .008, .1, 0x8a8a4a, 5)).position.set(-1.9 + i * .18, .05, -.6); } // flores murchas
{ add(cil(.2, .16, .3, 0x4a7fb5, 18)).position.set(-1.2, .15, -1.1); }
// ferramentas e escadinha
const AND = new THREE.Group(); add(AND); { const X = 1.02, Z = .72; [[-.2, -.14], [.2, -.14], [-.2, .3], [.2, .3]].forEach(([a, b], i) => { const m = add(box(.04, .62, .05, 0xffd23f, .01), AND); m.position.set(X + a, .27, Z + b); m.rotation.x = b > 0 ? -.2 : .08; }); [.16, .34].forEach(y => add(box(.42, .03, .13, 0xffd23f, .01), AND).position.set(X, y, Z + .18 - y * .18)); add(box(.5, .04, .36, 0xe8b820, .01), AND).position.set(X, .55, Z); }
const FERR = new THREE.Group(); add(FERR); { add(box(.42, .17, .22, 0xd8332a, .03), FERR).position.set(-.82, .1, -.62); add(box(.2, .03, .04, 0x24262c, .01), FERR).position.set(-.82, .21, -.62); for (let c = 0; c < 6; c++) { const m = add(cil(.012, .012, .9, COBRE, 8), FERR); m.rotation.z = 1.5708; m.position.set(-.2 + (c % 3) * .0, .02 + (c % 2) * .022, -1.35 + c * .026); } }

// termômetro de parede ------------------------------------------------------------------------------------------------
PAI = HEAD; const TX = -8.7, TZ = .42, TERM = new THREE.Group(); TERM.position.set(TX, -2, TZ); TERM.scale.setScalar(.7); add(TERM);
add(box(1.2, 8.6, .22, 0xf4efe6, .05), TERM).position.set(0, 4.5, -.32);
for (let i = 0; i < 14; i++) add(box(i % 2 ? .22 : .34, .04, .02, 0x333842, .008), TERM).position.set(.42, 1.9 + i * .47, -.2);
const vid = add(new THREE.Mesh(new THREE.CylinderGeometry(.27, .27, 7.2, 24), new THREE.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: .28, roughness: .1, depthWrite: false })), TERM); vid.position.y = 4.8; add(esf(.27, new THREE.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: .3, roughness: .1, depthWrite: false })), TERM).position.y = 8.4;
const bulbo = add(esf(.66, new THREE.MeshStandardMaterial({ color: 0xe02a20, emissive: 0x400804, roughness: .3 })), TERM); bulbo.position.y = .96;
const coluna = add(new THREE.Mesh(new THREE.CylinderGeometry(.19, .19, 1, 18), bulbo.material), TERM);
const nivel = t => { const f = ease((t - T_USO - .6) / 3.6); return (.93 + Math.sin(t * 2.3) * .025) * (1 - f) + .07 * f; };
AUTO.push(t => { const n = nivel(t), h_ = n * 7; coluna.scale.y = h_; coluna.position.y = 1.4 + h_ / 2; const f = clamp((.65 - n) / .5); bulbo.material.color.setRGB(.88 - f * .72, .16 + f * .4, .12 + f * .84); bulbo.material.emissive.setRGB(.2 * (1 - f), .03 + f * .1, .01 + f * .3); });

// abertura: aparelho velho sem gás, tossindo fumaça, despenca na cama ----------------------------------------------------------
const T_Q = tk('continua', 0), YV = 11.6, VEL = new THREE.Group(); VEL.position.set(-.5, YV, 1); add(VEL); add(box(5, 2.8, 2, 0xb9b09a, .05), VEL); for (let i = 0; i < 10; i++) add(box(4.3, .1, .06, 0x3b3d45, .01), VEL).position.set(0, -1 + i * .22, 1.02); add(box(.7, .9, .1, 0x8b8370, .02), VEL).position.set(1.95, .7, 1.03);
const YCAMA = 1.9;
[-1.8, 1.8].forEach(x => { const b = add(box(.2, .2, 2.2, 0x56606e, .02)); b.position.set(-.5 + x, YV - 1.5, 1); AUTO.push(t => { b.visible = t < fim(0); }); });
const fum = inst(new THREE.SphereGeometry(.3, 10, 8), new THREE.MeshStandardMaterial({ color: 0x2c2c30, transparent: true, opacity: .62, roughness: 1, depthWrite: false }), 40, false);
const qcq = []; for (let i = 0; i < 18; i++) { const m = add(box(.3 + rnd() * .7, .2 + rnd() * .4, .3 + rnd() * .7, [0xb9b09a, 0x8b8370, 0x3b3d45][i % 3], .02)); m.visible = false; qcq.push({ m, vx: -4 + rnd() * 8, vy: 3 + rnd() * 4, vz: 1 + rnd() * 6 }); }
AUTO.push(t => { const f = t - T_Q, on = t < F(1), QD = .9; VEL.visible = on && f < QD; if (on) { VEL.position.x = -.5 + (f < 0 ? Math.sin(t * 38) * .06 : 0); VEL.position.y = YV - (f > 0 ? f * f * ((YV - YCAMA) / (QD * QD)) : 0); VEL.position.z = 1 + Math.max(0, f) * 4; VEL.rotation.z = f > 0 ? f * .8 : Math.sin(t * 27) * .015; } fum.visible = t < F(1); if (fum.visible) { for (let i = 0; i < 40; i++) { const u = (t * .55 + i * .025) % 1; O.position.set(-.5 + Math.sin(i * 1.7 + t) * (.4 + u * 1.4), YV + 1.4 + u * 5.5, 2 + Math.cos(i) * .4 + u * 1.2); O.rotation.set(0, 0, 0); O.scale.setScalar((.8 + u * 3.4) * clamp((t + .2) * 3)); O.updateMatrix(); fum.setMatrixAt(i, O.matrix); } fum.instanceMatrix.needsUpdate = true; } qcq.forEach(c => { const q = f - QD, v = q > 0 && on; c.m.visible = v; if (v) { c.m.position.set(-.5 + c.vx * q, Math.max(YCAMA, YCAMA + 1 + c.vy * q - 9 * q * q), 4.6 + c.vz * q); c.m.rotation.set(q * 6, q * 4, 0); } }); });
PAI = COND;

// tempos ------------------------------------------------------------------------------------------------------
const T = { com: tk('compressor', 1), ser: tk('serpentina', 2), ale: tk('aletas', 3), exa: tk('exaustor', 4), tub: tk('tubos', 5), eva: tk('evaporadora', 6), fil: tk('filtro', 7), tur: tk('turbina', 8), tam: tk('tampa', 9), val: tk('válvula', 9) };
const CZ = 3.2, CX = 2.8, CL = 2.3; // condensadora: meia-largura e meia-profundidade

// base e compressor -----------------------------------------------------------------------------------------
{ const d = add(box(6.8, .3, 5.6, 0xbfc3c8, .03)); d.position.set(0, .15, CZ); aparece(d, T.com - .15, .4, 'desce', 2); som(T.com + .1, 'impact'); }
for (let i = 0; i < 20; i++) { const a = i / 20 * 6.2832, m = add(cil(.09, .09, .1, ACO, 8)); m.position.set(Math.cos(a) * 1.5, .34, CZ + Math.sin(a) * 1.5); aparece(m, T.com + .25 + i * .03, .14, 'pop'); }
{ const m = add(cil(1.4, 1.5, .24, 0x56606e, 40)); m.position.set(0, .42, CZ); aparece(m, T.com + .4, .3, 'desce', 1.2); }
const NE = 38, esp = inst(new THREE.TorusGeometry(.78, .038, 8, 40), mat(0xffffff, { roughness: .3, metalness: .35 }), NE), evs = []; for (let i = 0; i < NE; i++) { evs.push({ y: .6 + i * .056, t: T.com + .6 + i * .028 }); C.set(COBRE).offsetHSL(0, 0, (rnd() - .5) * .1); esp.setColorAt(i, C); }
anima(esp, evs, (b, t) => { const k = back((t - b.t) / .14); O.position.set(0, b.y, CZ); O.rotation.set(Math.PI / 2, 0, 0); O.scale.setScalar(Math.max(k, .0001)); }, T.com + 2);
const CP = new THREE.Group(); CP.position.set(0, 0, CZ); add(CP); { const c_ = add(cil(1.02, 1.02, 2.2, 0x23402f, 40), CP); c_.position.y = 1.72; const d_ = add(esf(1.02, 0x23402f), CP); d_.position.y = 2.82; d_.scale.y = .5; [1.2, 2.3].forEach(y => add(cil(1.06, 1.06, .1, 0x2f5a42, 40), CP).position.y = y); add(box(.5, .6, .2, 0x1e2026, .03), CP).position.set(0, 2.1, 1.05); for (let i = 0; i < 6; i++) add(cil(.03, .03, .1, 0xffd23f, 8), CP).position.set(-.15 + (i % 3) * .15, 2.05 + (i > 2 ? .2 : 0), 1.17); }
aparece(CP, T.com + 1.9, .4, 'desce', 3); som(T.com + 2.1, 'impact'); AUTO.push(t => { if (t > T.com + 2.4) CP.scale.y = 1 + Math.sin(t * 22) * .012; });
for (let i = 0; i < 3; i++) som(T.com + .6 + i * .3, 'pop');

// serpentina: cano que vai e volta, em duas camadas -----------------------------------------------------------------
const NR = 24, ser = inst(new THREE.CylinderGeometry(.052, .052, 1, 8), mat(0xffffff, { roughness: .28, metalness: .4 }), NR * 6), corr = [];
const qt = new THREE.Quaternion(), QX = new THREE.Quaternion().setFromUnitVectors(Y_, new THREE.Vector3(1, 0, 0)), QZ = new THREE.Quaternion().setFromUnitVectors(Y_, new THREE.Vector3(0, 0, 1));
const tS = i => T.ser + .1 + i * (3.1 / (NR * 6));
{ let n = 0; for (let r = 0; r < NR; r++) for (let l = 0; l < 2; l++) { const y = .62 + r * .17 + l * .04, d = l * .12, X = CX - d, Z = CL - d; [[-X, CZ, Z * 2, QZ], [0, CZ + Z, X * 2, QX], [X, CZ, Z * 2, QZ]].forEach(([x, z, L, q]) => { corr.push({ x, y, z, L, q, t: tS(n) }); C.set(COBRE).offsetHSL(0, 0, (rnd() - .5) * .06); ser.setColorAt(n, C); n++; }); } }
anima(ser, corr, (b, t) => { const k = ease((t - b.t) / .12); if (k <= 0) { zera(); return; } O.position.set(b.x, b.y, b.z); O.quaternion.copy(b.q); O.scale.set(1, Math.max(k, .0001) * b.L, 1); }, T.ser + 4);
const arc = inst(new THREE.TorusGeometry(.085, .05, 6, 10, Math.PI), mat(COBRE, { roughness: .28, metalness: .4 }), (NR - 1) * 2), arcs = [], mb = new THREE.Matrix4().makeBasis(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, 0, -1), new THREE.Vector3(-1, 0, 0)), qb = new THREE.Quaternion().setFromRotationMatrix(mb);
for (let r = 0; r < NR - 1; r++) [-1, 1].forEach(s => arcs.push({ x: s * CX, y: .62 + r * .17 + .085, z: CZ - CL, t: tS(r * 6 + 5) }));
anima(arc, arcs, (b, t) => { const k = t >= b.t ? 1 : .0001; O.position.set(b.x, b.y, b.z); O.quaternion.copy(qb); O.scale.setScalar(k); }, T.ser + 4);
for (let q = T.ser + .1; q < T.ser + 3.2; q += .16) som(q, 'pop');
// gás quente correndo no cano, como bolinhas em brasa
const brasa = inst(new THREE.SphereGeometry(.095, 8, 6), new THREE.MeshBasicMaterial({ color: 0xff6a20, toneMapped: false }), 90, false);
AUTO.push(t => { const on = t > T.ser + 1.2 && t < T.ale + .3; brasa.visible = on; if (!on) return; for (let i = 0; i < 90; i++) { const u = (t * .22 + i / 90) % 1, r = Math.floor(u * NR), f = u * NR - r, y = .62 + Math.min(r, (corr.length / 6 | 0) - 1) * .17 + .02, s = r % 2 ? 1 : -1, p = f * (CL * 2 + CX * 2 + CL * 2); let x, z; if (p < CL * 2) { x = -s * CX; z = CZ - CL + p; } else if (p < CL * 2 + CX * 2) { x = -s * CX + s * (p - CL * 2); z = CZ + CL; } else { x = s * CX; z = CZ + CL - (p - CL * 2 - CX * 2); } const k = clamp((t - tS(r * 6)) * 5); O.position.set(x, y, z); O.rotation.set(0, 0, 0); O.scale.setScalar(Math.max(k, .001)); O.updateMatrix(); brasa.setMatrixAt(i, O.matrix); } brasa.instanceMatrix.needsUpdate = true; });

// aletas: lâminas finas descendo sobre o cano ---------------------------------------------------------------------
const nF = 124, nL = 92, ale = inst(new THREE.BoxGeometry(.03, 4.25, .3), mat(0xffffff, { roughness: .3, metalness: .45 }), nF + nL * 2), als = [], HA = 2.76;
for (let i = 0; i < nF; i++) { als.push({ x: -CX - .1 + (i + .5) * ((CX + .1) * 2 / nF), z: CZ + CL - .04, ry: 0, t: T.ale + .1 + i * .017 }); C.set(i % 2 ? ALU : 0xc4ced7); ale.setColorAt(als.length - 1, C); }
[-1, 1].forEach(s => { for (let i = 0; i < nL; i++) { als.push({ x: s * (CX - .04), z: CZ - CL + (i + .5) * (CL * 2 / nL), ry: Math.PI / 2, t: T.ale + 1.3 + i * .022 + (s > 0 ? .25 : 0) }); C.set(i % 2 ? ALU : 0xc4ced7); ale.setColorAt(als.length - 1, C); } });
anima(ale, als, (b, t) => { const k = clamp((t - b.t) / .26); if (k <= 0) { zera(); return; } const e = ease(k); O.position.set(b.x, HA + (1 - e) * 2.4, b.z); O.rotation.set(0, b.ry, 0); O.scale.setScalar(1); }, T.ale + 4.2);
for (let q = T.ale + .1; q < T.ale + 3.6; q += .19) som(q, 'toc');

// parte de cima da condensadora: moldura, bocal e exaustor --------------------------------------------------------------
{ const f = new THREE.Shape(); f.moveTo(-CX - .25, -CL - .25); f.lineTo(CX + .25, -CL - .25); f.lineTo(CX + .25, CL + .25); f.lineTo(-CX - .25, CL + .25); f.closePath(); const b = new THREE.Path(); b.absarc(0, 0, 2.02, 0, 6.2832, true); f.holes.push(b); const m = add(sh(new THREE.Mesh(new THREE.ExtrudeGeometry(f, { depth: .26, bevelEnabled: false, curveSegments: 48 }), mat(TAMPA, { roughness: .45 })))); m.rotation.x = -Math.PI / 2; m.position.set(0, 4.92, CZ); aparece(m, T.exa + .05, .35, 'desce', 1.3); som(T.exa + .3, 'impact');
  const tr = add(box(CX * 2 + .5, 4.6, .14, TAMPA, .02)); tr.position.set(0, 2.62, CZ - CL - .16); aparece(tr, T.exa - .1, .25, 'pop');
  const an = add(cil(2.06, 2.06, .55, 0x2d333d, 56, { side: THREE.DoubleSide })); an.position.set(0, 5.32, CZ); an.geometry = new THREE.CylinderGeometry(2.08, 2.04, .55, 56, 1, true); aparece(an, T.exa + .2, .3, 'pop');
  const ci = add(cil(.08, .08, 1.6, 0x56606e, 10)); ci.position.set(0, 4.4, CZ); aparece(ci, T.exa + .1, .2, 'pop'); }
for (let i = 0; i < 4; i++) { const m = add(box(4.1, .1, .12, 0x3c4350, .02)); m.position.set(0, 4.98, CZ); m.rotation.y = i * .785; aparece(m, T.exa + .2 + i * .05, .2, 'pop'); }
const HE = new THREE.Group(); HE.position.set(0, 5.28, CZ); add(HE); { const fm = new THREE.Shape(); fm.moveTo(.2, -.26); fm.bezierCurveTo(.8, -.5, 1.65, -.56, 1.9, -.2); fm.bezierCurveTo(1.92, .1, 1.1, .3, .2, .16); fm.closePath(); const G = new THREE.ExtrudeGeometry(fm, { depth: .04, bevelEnabled: false, curveSegments: 16 }); for (let i = 0; i < 5; i++) { const w = new THREE.Group(); w.rotation.y = i / 5 * 6.2832; HE.add(w); const b = add(sh(new THREE.Mesh(G, mat(0xffb627, { roughness: .4, side: THREE.DoubleSide }))), w); b.rotation.x = -Math.PI / 2 + .3; aparece(w, T.exa + .45 + i * .2, .3, 'pop'); som(T.exa + .5 + i * .2, 'tijolo'); } const cu = add(cil(.3, .36, .3, 0x2d333d, 28), HE); aparece(cu, T.exa + .4, .2, 'pop'); }
{ const fim_ = T.exa + 1.7; for (let i = 1; i <= 8; i++) { const m = add(new THREE.Mesh(new THREE.TorusGeometry(i / 8 * 2.1, i === 8 ? .05 : .02, 6, 64), mat(0x2d333d, { metalness: .4 }))); m.castShadow = true; m.rotation.x = Math.PI / 2; m.position.set(0, 5.62, CZ); aparece(m, fim_ + i * .07, .18, 'pop'); } for (let i = 0; i < 32; i++) { const m = add(box(2, .018, .018, 0x2d333d, .005)); m.rotation.y = i / 32 * 6.2832; m.position.set(Math.cos(-i / 32 * 6.2832) * 1.1, 5.63, CZ + Math.sin(-i / 32 * 6.2832) * 1.1); aparece(m, fim_ + .6 + i * .012, .1, 'pop'); } }
// ar quente saindo pelo alto
const quente = inst(new THREE.BoxGeometry(.06, .9, .06), new THREE.MeshBasicMaterial({ color: 0xffa05a, transparent: true, opacity: .55, depthWrite: false }), 70, false);
AUTO.push(t => { HE.rotation.y = t > T.exa + 1.6 ? -((t - T.exa - 1.6) ** 1.5) * 5 : 0; const on = t > T.exa + 2 && t < fim(4) + 1; quente.visible = on || t > T.val; if (!quente.visible) return; for (let i = 0; i < 70; i++) { const u = (t * .9 + i * .618) % 1, a = i * 2.4, rr = .4 + (i * .37 % 1) * 1.6; O.position.set(Math.cos(a) * rr * (1 + u * .5), 5.8 + u * 5.5, CZ + Math.sin(a) * rr * (1 + u * .5)); O.rotation.set(0, 0, Math.sin(i + t * 3) * .12); O.scale.setScalar(1 - u * .6); O.updateMatrix(); quente.setMatrixAt(i, O.matrix); } quente.instanceMatrix.needsUpdate = true; });

// tubos sobem a parede ---------------------------------------------------------------------------------------------------
const TX1 = 2.3, TX2 = 2.9, YT0 = 3.4, YT1 = 13.4, NT = 54, TZ_ = .42, HT = (YT1 - YT0) / NT;
const tub = inst(new THREE.CylinderGeometry(.17, .17, HT + .01, 14), mat(0xffffff, { roughness: .3, metalness: .35 }), NT * 2), tbs = [];
[[TX1, 0], [TX2, .3]].forEach(([x, atr]) => { for (let i = 0; i < NT; i++) { tbs.push({ x, y: YT0 + (i + .5) * HT, t: T.tub + .15 + atr + i * .05 }); C.set(COBRE).offsetHSL(0, 0, i % 2 ? .03 : -.02); tub.setColorAt(tbs.length - 1, C); } });
anima(tub, tbs, (b, t) => { const k = clamp((t - b.t) / .12); if (k <= 0) { zera(); return; } O.position.set(b.x, b.y, TZ_); O.rotation.set(0, 0, 0); O.scale.set(1, k, 1); }, T.tub + 3.4);
[TX1, TX2].forEach((x, i) => { const m = add(cil(.17, .17, CZ - CL - TZ_ + .3, COBRE, 14)); m.rotation.x = Math.PI / 2; m.position.set(x, YT0, (CZ - CL + TZ_) / 2); aparece(m, T.tub + i * .2, .2, 'pop'); });
for (let i = 0; i < 12; i++) { const y = YT0 + 2 + i * .52, m = add(box(1.1, .11, .2, 0x7a8796, .02)); m.position.set((TX1 + TX2) / 2, y, TZ_ + .1); [-.48, .48].forEach(d => { const b_ = add(cil(.05, .05, .1, 0xdfe5ec, 8), m); b_.rotation.x = 1.5708; b_.position.set(d, 0, .1); }); const q = T.tub + 1 + i * .15; aparece(m, q, .16, 'pop'); som(q, 'toc'); }
for (let q = T.tub + .15; q < T.tub + 2.6; q += .3) som(q, 'pop');
// válvula, pequena no cano mas com volante grande, para enxergar
const VY = 8.4, VAL = new THREE.Group(); VAL.position.set(TX2, VY, TZ_ + .22); add(VAL); { add(cil(.3, .3, .5, 0xd9b23f, 20, { metalness: .5, roughness: .3 }), VAL); const h_ = add(cil(.06, .06, .5, 0x8a8f98, 8), VAL); h_.rotation.x = Math.PI / 2; h_.position.z = .35; }
const VOL = new THREE.Group(); VOL.position.set(0, 0, .6); VAL.add(VOL); { const r_ = add(new THREE.Mesh(new THREE.TorusGeometry(.42, .06, 8, 28), mat(0xd8332a, { roughness: .4 })), VOL); r_.castShadow = true; for (let i = 0; i < 3; i++) add(box(.82, .06, .05, 0xd8332a, .01), VOL).rotation.z = i * 1.047; } aparece(VAL, T.tub + 2.4, .3, 'pop');
AUTO.push(t => { VOL.rotation.z = -ease((t - T.val) / 1.1) * 6.3; });

PAI = HEAD; // evaporadora, lá em cima ------------------------------------------------------------------------------------------------
const YC = 12.4, HW = 4.5, HD = 2.4;
{ const m = add(box(HW * 2, 3, .25, 0xdfe2e6, .02)); m.position.set(0, YC, .14); aparece(m, T.eva - .2, .3, 'pop'); [-1, 1].forEach((s, i) => { const c_ = add(box(.14, 3, HD, 0xe9ecef, .02)); c_.position.set(s * HW, YC, HD / 2); aparece(c_, T.eva - .05 + i * .1, .3, 'pop'); }); for (let i = 0; i < 12; i++) { const b = add(cil(.05, .05, .1, ACO, 8)); b.rotation.x = 1.5708; b.position.set(-4 + (i % 6) * 1.6, YC + (i > 5 ? 1.2 : -1.2), .3); aparece(b, T.eva + i * .02, .1, 'pop'); } const pi = add(box(HW * 2 - .2, .18, HD - .1, 0xe9ecef, .02)); pi.position.set(0, 10.99, HD / 2); aparece(pi, T.eva, .25, 'pop'); }
const TG = new THREE.Group(); TG.position.set(0, 12.85, 1.2); TG.rotation.x = -.6; add(TG);
const NE2 = 14, LE = HW * 2 - .55, ev = inst(new THREE.CylinderGeometry(.06, .06, LE, 10), mat(COBRE, { roughness: .28, metalness: .4 }), NE2 * 2, true, TG), evl = [];
const dYE = 2.15 / NE2; for (let r = 0; r < NE2; r++) [-.13, .13].forEach((z, l) => evl.push({ y: -1.05 + r * dYE, z, t: T.eva + .3 + (r * 2 + l) * .045 }));
anima(ev, evl, (b, t) => { const k = ease((t - b.t) / .14); if (k <= 0) { zera(); return; } O.position.set(0, b.y, b.z); O.quaternion.copy(QX); O.scale.set(1, Math.max(k, .0001), 1); }, T.eva + 2);
const NA2 = 180, al2 = inst(new THREE.BoxGeometry(.022, 2.3, .46), mat(0xffffff, { roughness: .3, metalness: .45 }), NA2, true, TG), a2 = [];
for (let i = 0; i < NA2; i++) { a2.push({ x: -LE / 2 + (i + .5) * (LE / NA2), t: T.eva + 1.5 + i * .009 }); C.set(i % 2 ? ALU : 0xc8d2db); al2.setColorAt(i, C); }
anima(al2, a2, (b, t) => { const k = clamp((t - b.t) / .18); if (k <= 0) { zera(); return; } O.position.set(b.x, 0, (1 - ease(k)) * 1.7); O.rotation.set(0, 0, 0); O.scale.setScalar(1); }, T.eva + 3.6);
for (let q = T.eva + .3; q < T.eva + 3; q += .24) som(q, 'pop');

// filtro: duas telas azuis que deslizam nos trilhos ---------------------------------------------------------------------------
const FILT = [-1, 1].map((s, i) => { const g = new THREE.Group(); TG.add(g); g.position.set(s * 2.15, 0, .3); const m = add(new THREE.Mesh(new THREE.PlaneGeometry(4.1, 2.3), new THREE.MeshStandardMaterial({ color: 0x6fb7ea, transparent: true, opacity: .5, side: THREE.DoubleSide, depthWrite: false })), g); [[0, 1.17, 4.2, .09], [0, -1.17, 4.2, .09]].forEach(([x, y, w, h]) => add(box(w, h, .09, 0x2f7fd6, .02), g).position.set(x, y, 0)); [-2.08, 2.08].forEach(x => add(box(.09, 2.42, .09, 0x2f7fd6, .02), g).position.x = x); const nv = 86, nh = 46, fi = inst(new THREE.BoxGeometry(.012, 2.3, .012), new THREE.MeshBasicMaterial({ color: 0x1f5fae }), nv + nh, false, g); for (let k = 0; k < nv; k++) { O.position.set(-2.03 + k * (4.06 / (nv - 1)), 0, .02); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); fi.setMatrixAt(k, O.matrix); } for (let k = 0; k < nh; k++) { O.position.set(0, -1.12 + k * (2.24 / (nh - 1)), .02); O.rotation.set(0, 0, Math.PI / 2); O.scale.set(1, 1.8, 1); O.updateMatrix(); fi.setMatrixAt(nv + k, O.matrix); } const t0 = T.fil + .1 + i * .55; AUTO.push(t => { const k = ease((t - t0) / .7); g.visible = t >= t0; g.position.x = s * (2.15 + (1 - k) * 4.4); }); som(t0 + .5, 'tijolo'); return g; });
// poeira grudando no filtro
const NP = 170, po = inst(new THREE.SphereGeometry(.034, 6, 5), mat(0x6e675c, { roughness: 1 }), NP, false, TG), pp = []; for (let i = 0; i < NP; i++) pp.push({ x: -4 + rnd() * 8, y: -1 + rnd() * 2, t: T.fil + 1.5 + rnd() * 1.9, s: .7 + rnd() * .9 });
anima(po, pp, (b, t) => { const k = (t - b.t) / .5; if (k <= 0) { zera(); return; } const e = 1 - Math.min(1, k); O.position.set(b.x + e * 1.2, b.y + e * 1.5, .36 + e * e * 3); O.rotation.set(0, 0, 0); O.scale.setScalar(b.s); }, T.fil + 4);

// turbina: rodas de lâminas, bem na frente -----------------------------------------------------------------------------------------
const TUR = new THREE.Group(); TUR.position.set(0, 11.72, 1.15); add(TUR); const NS = 11, NB = 54, LT = HW * 2 - .4, RT_ = .58, seg = LT / NS;
for (let i = 0; i <= NS; i++) { const m = add(cil(RT_ + .05, RT_ + .05, .05, 0xe0e4e8, 40), TUR); m.rotation.z = Math.PI / 2; m.position.x = -LT / 2 + i * seg; aparece(m, T.tur + .1 + i * .09, .16, 'pop'); }
const la = inst(new THREE.BoxGeometry(seg - .05, .02, .15), mat(0x3a7fd8, { roughness: .4 }), NS * NB, true, TUR), las = [];
for (let s = 0; s < NS; s++) for (let i = 0; i < NB; i++) { const a = i / NB * 6.2832 + s * .17; las.push({ x: -LT / 2 + (s + .5) * seg, a, t: T.tur + .25 + s * .1 + i * .007 }); C.set(i % 2 ? 0x3a7fd8 : 0x56a0ee); la.setColorAt(las.length - 1, C); }
anima(la, las, (b, t) => { const k = back((t - b.t) / .14); O.position.set(b.x, Math.cos(b.a) * RT_, Math.sin(b.a) * RT_); O.rotation.set(-b.a + .55, 0, 0); O.scale.setScalar(Math.max(k, .0001)); }, T.tur + 2.2);
{ const e_ = add(cil(.12, .12, LT + .3, 0xdfe5ec, 16), TUR); e_.rotation.z = Math.PI / 2; aparece(e_, T.tur + .05, .3, 'pop'); }
for (let q = T.tur + .1; q < T.tur + 1.3; q += .15) som(q, 'pop');

// tampa branca com display ---------------------------------------------------------------------------------------------------------------
const TP = new THREE.Group(); add(TP); { const f = new THREE.Shape(); f.moveTo(.02, 13.95); f.lineTo(1.2, 13.95); f.bezierCurveTo(1.9, 13.9, 2.42, 13.5, 2.46, 12.8); f.lineTo(2.46, 11.72); f.lineTo(1.82, 11.72); f.lineTo(1.82, 12.8); f.lineTo(.02, 13.4); f.closePath(); const m = add(sh(new THREE.Mesh(new THREE.ExtrudeGeometry(f, { depth: HW * 2 + .22, bevelEnabled: true, bevelSize: .03, bevelThickness: .03, bevelSegments: 2, curveSegments: 14 }), mat(TAMPA, { roughness: .32 }))), TP); m.rotation.y = -Math.PI / 2; m.position.x = HW + .11;
  for (let i = 0; i < 60; i++) add(box(.04, .03, .95, 0xb6bec6, .01), TP).position.set(-4.3 + i * .146, 13.99, .72);
  add(box(8.9, .1, .03, 0x3a9fe8, .01), TP).position.set(0, 12.05, 2.5); add(box(1.8, .8, .05, 0x101318, .02), TP).position.set(2.8, 12.74, 2.49); }
const cv = document.createElement('canvas'); cv.width = 256; cv.height = 128; const cx_ = cv.getContext('2d'), tela = new THREE.CanvasTexture(cv); tela.colorSpace = THREE.SRGBColorSpace; const dsp = add(new THREE.Mesh(new THREE.PlaneGeometry(1.6, .7), new THREE.MeshBasicMaterial({ map: tela, toneMapped: false })), TP); dsp.position.set(2.8, 12.74, 2.525);
let graus = null; const mostra = g => { if (g === graus) return; graus = g; cx_.fillStyle = '#05080c'; cx_.fillRect(0, 0, 256, 128); cx_.fillStyle = g > 22 ? '#ff7a4a' : '#6fe0ff'; cx_.font = 'bold 110px Segoe UI, Arial'; cx_.textAlign = 'center'; cx_.textBaseline = 'middle'; cx_.fillText(g + '°', 128, 70); tela.needsUpdate = true; };
{ const y0 = TP.position.y; AUTO.push(t => { const k = ease((t - T.tam) / .55); TP.visible = t >= T.tam; TP.position.set(0, y0 + (1 - k) * 2.2, (1 - k) * 2.4); if (TP.visible) mostra(Math.round(16 + 24 * clamp((nivel(t) - .07) / .86))); }); som(T.tam + .5, 'impact'); }
const PAL_ = new THREE.Group(); PAL_.position.set(0, 11.5, 2.42); add(PAL_); add(box(8.6, .07, .75, TAMPA, .02), PAL_).position.z = -.38; AUTO.push(t => { PAL_.visible = t > T.tam + .5; PAL_.rotation.x = .1 + ease((t - T_USO) / .5) * .8; });

PAI = COND; // gás correndo nos tubos: quente descendo, gelado subindo --------------------------------------------------------------------------------------
const gx = inst(new THREE.SphereGeometry(.14, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }), 60, false), gxs = []; for (let i = 0; i < 60; i++) { gxs.push(i); gx.setColorAt(i, C.set(i % 2 ? 0x57d4ff : 0xff5a30)); }
const geada = inst(new THREE.SphereGeometry(.05, 6, 5), mat(0xe6f7ff, { roughness: .5 }), 110, false), gd = []; for (let i = 0; i < 110; i++) gd.push({ y: VY + .4 + rnd() * (YT1 - VY - .4), a: rnd() * 6.28, s: .6 + rnd() * 1.4, q: T.val + .6 + rnd() * 1.6 });
anima(geada, gd, (b, t) => { if (t < b.q) { zera(); return; } O.position.set(TX2 + Math.cos(b.a) * .17, b.y, TZ_ + Math.sin(b.a) * .17); O.rotation.set(0, 0, 0); O.scale.setScalar(b.s * ease((t - b.q) * 3)); }, T.val + 3);
AUTO.push(t => { const on = t > T.val + .5; gx.visible = on; if (!on) return; for (let i = 0; i < 60; i++) { const q = i % 2, u = (t * .42 * (q ? 1 : -1) + i * .0333 + 9) % 1; O.position.set(q ? TX2 : TX1, YT0 + u * (YT1 - YT0), TZ_ + .1); O.rotation.set(0, 0, 0); O.scale.setScalar(q && (YT0 + u * (YT1 - YT0)) < VY ? .001 : 1); O.updateMatrix(); gx.setMatrixAt(i, O.matrix); } gx.instanceMatrix.needsUpdate = true; });

// pedreiro em tamanho normal: ajoelhado no quintal, na escadinha no quarto -----------------------------------------------------------------------------
PAI = scene;
const h = boneco({ cabeca: 'bloco', camisa: 0x2fbf8f, calca: 0x2b3a67, sapato: 0xe9e4d8, cabelo: 0x3a2a1e }); add(h); h.scale.setScalar(.84); const r = h.r;
const cap = new THREE.Group(); r.cab.add(cap); add(box(.47, .15, .45, 0xffc61a, .05), cap).position.y = .33; add(box(.32, .03, .2, 0xffc61a, .012), cap).position.set(0, .28, .3);
const mart = new THREE.Group(); r.bd.k.add(mart); mart.position.y = -.38; add(box(.05, .36, .05, 0x7a4a26, .012), mart).position.y = -.1; add(box(.2, .1, .1, 0x5e6a78, .02), mart).position.y = -.3; mart.rotation.x = 1.4;
const cac = add(box(.56, .13, .34, 0xd8332a, .05), r.cab); cac.position.y = -.2; cac.visible = false;
const ajoelha = () => { r.anda(0, 0); r.pe.k.rotation.x = r.pd.k.rotation.x = 1.5; h.position.y = -.37; };
const bate = t => { const w = Math.sin(t * 9); r.bd.j.rotation.x = -2.1 + w * .42; r.bd.k.rotation.x = -.3; r.be.j.rotation.x = 0; };
const T_FORA = F(1), T_DENTRO = F(6), T_VF = T.val - .25; // quintal de F(1) a F(6) e de novo na válvula
AUTO.push(t => { if (t >= T_USO) return; mart.visible = true;
  if (t < F(1)) { h.position.set(1.62, 0, .95); h.rotation.y = -.9; r.anda(0, 0); r.respira(t); r.bd.j.rotation.x = -2.3 + Math.sin(t * 9) * .3; r.bd.k.rotation.x = -1.3; r.be.j.rotation.x = 0; mart.visible = false; return; }
  if (t < F(5)) { h.position.set(.74, 0, -.85); ajoelha(); h.rotation.y = -1.25 + Math.sin(t * .7) * .12; r.respira(t); bate(t); return; }
  if (t < T_DENTRO || t >= T_VF) { h.position.set(-.86, 0, -.56); r.anda(0, 0); r.respira(t); h.rotation.y = 1; const w = Math.sin(t * 9); r.bd.j.rotation.x = -2.75 + w * .3; r.bd.k.rotation.x = -.2; r.be.j.rotation.x = t >= T_VF ? -2.6 : 0; return; }
  h.position.set(.86, .57, .66); r.anda(0, 0); r.respira(t); h.rotation.y = -2.5 + Math.sin(t * .7) * .15; const w = Math.sin(t * 9); r.bd.j.rotation.x = -2.5 + w * .36; r.bd.k.rotation.x = -.3; });
for (let q = T.com + 1; q < T.val; q += 1.15) som(q, 'toc');

// quem dorme: sua no calor, acorda tremendo no frio ---------------------------------------------------------------------------------------------------
const dor = boneco({ cabeca: 'bloco', camisa: 0xf4c95d, calca: 0x4285f4, sapato: 0xd9a57c, cabelo: 0x1e1a18 }); add(dor); dor.scale.setScalar(.84); dor.r.anda(0, 0); const cac2 = add(box(.56, .13, .34, 0x2f7fd6, .05), dor.r.cab); cac2.position.y = -.2; cac2.visible = false;
const NSU = 18, suor = inst(new THREE.SphereGeometry(.018, 6, 5), new THREE.MeshBasicMaterial({ color: 0x8fd8ff, toneMapped: false }), NSU, false);

// clipe final: frio em onda, neve e geada dentro do quarto ------------------------------------------------------------------------------------------------
const T_F = T_USO + .35;
const G = new THREE.CircleGeometry(1, 96), pos = G.attributes.position; for (let i = 1; i < pos.count; i++) { const a = Math.atan2(pos.getY(i), pos.getX(i)), q = 1 + Math.sin(a * 7) * .06 + Math.sin(a * 19) * .03; pos.setXY(i, pos.getX(i) * q, pos.getY(i) * q); }
const neve = add(new THREE.Mesh(G, mat(0xf2f8fc, { roughness: .8 }))); neve.rotation.x = -Math.PI / 2; neve.position.set(.4, .022, .3); neve.receiveShadow = true;
const NCB = 90, cob = inst(new THREE.IcosahedronGeometry(.1, 1), mat(0xf4faff, { roughness: .9 }), NCB, false), ccs = []; for (let i = 0; i < NCB; i++) ccs.push({ x: -.8 + rnd() * 1.6, z: .1 + rnd() * 2, y: .78, s: .5 + rnd() * .9, t: T_F + 1.4 + rnd() * 2.4, sx: 1 + rnd() });
anima(cob, ccs, (b, t) => { const k = ease((t - b.t) / .6); if (k <= 0) { zera(); return; } O.position.set(b.x, b.y, b.z); O.rotation.set(0, 0, 0); O.scale.set(b.s * b.sx * k, b.s * .35 * k, b.s * b.sx * k); }, D.total + 5); // neve em cima da cama
const NFL = 520, flo = inst(new THREE.SphereGeometry(.012, 6, 5), new THREE.MeshBasicMaterial({ color: 0xffffff }), NFL, false), fls = []; for (let i = 0; i < NFL; i++) fls.push([XE + .2 + rnd() * 4.4, rnd(), .1 + rnd() * 4.2, rnd() * 6.28, .7 + rnd() * .9]);
PAI = HEAD; const NV_ = 200, ven = inst(new THREE.BoxGeometry(.09, .09, 2), new THREE.MeshBasicMaterial({ color: 0xbfe9ff, transparent: true, opacity: .7, depthWrite: false }), NV_, false);
const NB_ = 30, nev = inst(new THREE.SphereGeometry(1, 12, 10), new THREE.MeshBasicMaterial({ color: 0xe8f7ff, transparent: true, opacity: .07, depthWrite: false }), NB_, false);
const NI = 70, gel = inst(new THREE.ConeGeometry(.09, 1, 6), mat(0xcdeeff, { roughness: .15, metalness: .1 }), NI, false), gls = []; for (let i = 0; i < NI; i++) gls.push({ x: -HW + .2 + (i + .5) * (HW * 2 - .4) / NI, z: 2.3, l: .4 + rnd() * .8, y: 10.92 });
PAI = scene;
const ping = [[1.5, 2.3], [1.9, 2.8]].map(([x, z]) => { const g = new THREE.Group(); g.position.set(x, 0, z); g.scale.setScalar(.75); add(g); const c_ = add(esf(.34, 0x20242c), g); c_.scale.y = 1.4; c_.position.y = .5; const b_ = add(esf(.25, 0xffffff), g); b_.scale.y = 1.4; b_.position.set(0, .46, .15); add(esf(.2, 0x20242c), g).position.y = 1; const bi = add(cil(0, .06, .16, 0xffa53c, 8), g); bi.position.set(0, .98, .22); bi.rotation.x = 1.57; [-.09, .09].forEach(s => add(esf(.03, 0xffffff), g).position.set(s, 1.05, .17)); [-.12, .12].forEach(s => add(box(.14, .05, .22, 0xffa53c, .02), g).position.set(s, .03, .08)); g.rotation.y = -2.2; g.visible = false; return g; });
const bon = (() => { const g = new THREE.Group(); g.position.set(1.72, 0, 1.2); g.scale.setScalar(.62); add(g); add(esf(.5, 0xfbfdff), g).position.y = .45; add(esf(.36, 0xfbfdff), g).position.y = 1.12; add(esf(.25, 0xfbfdff), g).position.y = 1.62; const n_ = add(cil(0, .06, .3, 0xff8a3c, 8), g); n_.rotation.x = 1.57; n_.position.set(0, 1.62, .35); [-.09, .09].forEach(s => add(esf(.035, 0x111111), g).position.set(s, 1.7, .22)); aparece(g, T_F + 2.6, .4, 'pop'); return g; })();
const gelo = add(new THREE.Mesh(new THREE.PlaneGeometry(1.72, 1.42), new THREE.MeshBasicMaterial({ map: K3.tex(256, 256, (g, w, h_) => { g.clearRect(0, 0, w, h_); for (let i = 0; i < 900; i++) { const x = rnd() * w, y = rnd() * h_, b = Math.min(x, y, w - x, h_ - y) / 110; if (rnd() > b) { g.fillStyle = 'rgba(245,252,255,.75)'; g.beginPath(); g.arc(x, y, 3 + rnd() * 9, 0, 6.3); g.fill(); } } }), transparent: true, opacity: 0, depthWrite: false }))); gelo.rotation.y = Math.PI / 2; gelo.position.set(XE + .1, 1.55, 1.6);
const ceuCv = scene.background.image, ceuG = ceuCv.getContext('2d'), CA = new THREE.Color(V_.ceu[0]), CB = new THREE.Color(V_.ceu[1]), CF = new THREE.Color('#8fcbf0'), CG = new THREE.Color('#f4fbff'), c1 = new THREE.Color(), c2 = new THREE.Color(); let gU = -1;
const pintaCeu = g => { if (Math.abs(g - gU) < .004) return; gU = g; const l = ceuG.createLinearGradient(0, 0, 0, 512); l.addColorStop(0, '#' + c1.lerpColors(CA, CF, g).getHexString()); l.addColorStop(.75, '#' + c2.lerpColors(CB, CG, g).getHexString()); ceuG.fillStyle = l; ceuG.fillRect(0, 0, 8, 512); scene.background.needsUpdate = true; };
const solC = new THREE.Color(V_.sol), friaC = new THREE.Color(0xcfe6ff), cobC = coberta.material.color.clone(), cobF = new THREE.Color(0xeaf4fb);
AUTO.push(t => {
  const f = t >= T_USO, q = Math.max(0, t - T_F), g = ease(q / 3.2), fora = (t >= F(1) && t < F(6)) || (t >= T_VF && t < F(LAST)); AND.visible = !f; FERR.visible = !f; pintaCeu(g);
  sol.position.set(fora ? 2.4 : 3.2, 6, fora ? -3.4 : 4); sol.intensity = 2.9 - g * 1.1; sol.color.lerpColors(solC, friaC, g); neve.scale.setScalar(.01 + ease(q / 4) * 6.4); neve.visible = q > 0; coberta.material.color.lerpColors(cobC, cobF, ease((q - 1) / 2.4)); gelo.material.opacity = ease((q - .6) / 2.6); copo.material.color.lerpColors(new THREE.Color(0xbfe6ff), new THREE.Color(0xffffff), g); copo.material.opacity = .55 + g * .4;
  CORT.forEach((c, i) => { c.rotation.x = 0; c.rotation.z = -(q > 0 ? (.45 + Math.sin(t * 9 + i * .7) * .12) * clamp(q) : Math.sin(t * .8 + i) * .01); });
  cac.visible = f; if (f) { mart.visible = false; const tr = Math.sin(t * 40) * .012 * g; h.position.set(1.3 + tr, 0, 1.45); h.rotation.y = -.3; r.anda(0, 0); const o = Math.sin(t * 6); r.be.j.rotation.x = -2.7 + o * .15; r.bd.j.rotation.x = -2.7 - o * .15; r.be.k.rotation.x = r.bd.k.rotation.x = 0; }
  // dormindo deitado; no frio senta tremendo
  const sen = ease((q - 1.6) / .7); dor.rotation.x = -Math.PI / 2 * (1 - sen); dor.position.set(-.02 - sen * .42 + Math.sin(t * 46) * .012 * sen, .62 - sen * .78, 1.72 - sen * .82); dor.r.be.j.rotation.x = -.2 - sen * 2.3; dor.r.bd.j.rotation.x = -.2 - sen * 2.3; dor.r.be.j.rotation.z = -sen * .9; dor.r.bd.j.rotation.z = sen * .9; cac2.visible = sen > .1; dor.r.pe.j.rotation.x = dor.r.pd.j.rotation.x = -sen * 1.5;
  suor.visible = t < T_USO + .3 && !fora; if (suor.visible) { for (let i = 0; i < NSU; i++) { const u = (t * .8 + i * .0556) % 1, a = i * 2.4; O.position.set(-.02 + Math.cos(a) * .15, .86 + Math.sin(u * 3.14) * .1 - u * .1, .34 + Math.sin(a) * .1 + u * .08); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); suor.setMatrixAt(i, O.matrix); } suor.instanceMatrix.needsUpdate = true; }
  flo.visible = ven.visible = nev.visible = gel.visible = q > 0; ping.forEach((p, i) => { const u = q - 2.4 - i * .4; p.visible = u > 0; if (u > 0) { p.position.x = (i ? 1.9 : 1.5) - u * .22; p.rotation.z = Math.sin(u * 7) * .13; } }); if (q <= 0) return;
  const s = clamp(q / 1.4); fls.forEach((b, i) => { const u = ((b[1] - t * .13 * b[4]) % 1 + 1) % 1; O.position.set(b[0] + Math.sin(t + b[3]) * .08, u * 2.8, b[2]); O.rotation.set(0, 0, 0); O.scale.setScalar((i / NFL < s ? 1 : .0001) * b[4]); O.updateMatrix(); flo.setMatrixAt(i, O.matrix); }); flo.instanceMatrix.needsUpdate = true;
  for (let i = 0; i < NV_; i++) { const u = (q * .75 + i * .618) % 1, x0 = -4.2 + (i * .137 % 1) * 8.4, of = (i * .37 % 1) * 1.4; O.position.set(x0 * (1 + u * .5), 10.6 - u * u * 7 - of * u, 3 + u * 19); O.rotation.set(.45 + u * .3, 0, 0); O.scale.set(1, 1, .6 + u * 1.2); O.updateMatrix(); ven.setMatrixAt(i, O.matrix); } ven.instanceMatrix.needsUpdate = true;
  for (let i = 0; i < NB_; i++) { const u = (q * .42 + i * .217) % 1, x0 = -4 + (i * .271 % 1) * 8; O.position.set(x0 * (1 + u * .5), 10.8 - u * u * 6.6, 3 + u * 16); O.rotation.set(0, 0, 0); O.scale.setScalar((.5 + u * 3) * Math.min(1, q * 2)); O.updateMatrix(); nev.setMatrixAt(i, O.matrix); } nev.instanceMatrix.needsUpdate = true;
  gls.forEach((b, i) => { const k = ease((q - .8 - (i % 9) * .1) / 1.4); O.position.set(b.x, b.y - b.l * k / 2, b.z); O.rotation.set(Math.PI, 0, 0); O.scale.set(1, Math.max(k, .001) * b.l, 1); O.updateMatrix(); gel.setMatrixAt(i, O.matrix); }); gel.instanceMatrix.needsUpdate = true;
});
// calor ondulando no ar antes do frio
const NC = 120, onda = inst(new THREE.BoxGeometry(.012, .2, .012), new THREE.MeshBasicMaterial({ color: 0xffc27a, transparent: true, opacity: .42, depthWrite: false }), NC, false), ocs = []; for (let i = 0; i < NC; i++) ocs.push([-1.3 + rnd() * 3.6, rnd(), -2.6 + rnd() * 6, rnd() * 6.28]);
AUTO.push(t => { const on = t < T_USO + 1.2; onda.visible = on; if (!on) return; const a = 1 - ease((t - T_USO) / 1.2); ocs.forEach((b, i) => { const u = (b[1] + t * .28) % 1; O.position.set(b[0] + Math.sin(t * 3 + b[3] + u * 5) * .05, .2 + u * 2.3, b[2]); O.rotation.set(0, 0, Math.sin(t * 4 + b[3]) * .15); O.scale.setScalar(a * Math.sin(u * 3.14)); O.updateMatrix(); onda.setMatrixAt(i, O.matrix); }); onda.instanceMatrix.needsUpdate = true; });

// câmera --------------------------------------------------------------------------------------------------------------------------------------------------
const V = [[[.5, 2.2, 4.5], [.15, 1.4, .6]], [[-1.5, 1.75, -3.3], [.28, .55, -.7]], [[-1.9, 1.5, -3], [.3, .55, -.7]], [[-.9, 1.95, -3.2], [.3, .55, -.7]], [[-1.7, 2.3, -2.5], [.3, .72, -.66]], [[1.7, 1.8, -3], [-.34, 1, -.4]], [[-.6, 3.1, 2.7], [.55, 1.75, .3]], [[-.75, 2.95, 2.6], [.52, 1.75, .3]], [[-.5, 2.75, 2.75], [.52, 1.72, .3]], [[-.55, 2.85, 2.8], [.5, 1.75, .3]]];
const K = []; V.forEach(([p, l], i) => { if (i) K.push({ ...K[K.length - 1], t: F(i) + .03 }); K.push({ t: F(i) + (i ? .85 : 0), p, l, f: 34 }); if (i === 9) { K.push({ t: T_VF - .02, p: [-.5, 2.85, 2.7], l, f: 34 }, { t: T_VF, p: [1.6, 1.7, -2.9], l: [-.42, 1.05, -.3], f: 34 }, { t: fim(9), p: [1.5, 1.66, -2.7], l: [-.42, 1.05, -.3], f: 34 }); } else K.push({ t: fim(i), p: p.map((v, j) => j === 1 ? v : l[j] + (v - l[j]) * .9), l, f: 34 }); });
K.push({ ...K[K.length - 1], t: F(LAST) - .02 }, { t: F(LAST) + .03, p: [-.7, 2.5, 3.6], l: [.4, 1.5, .3], f: 34 }, { t: T_USO - .02, p: [-.65, 2.5, 3.4], l: [.4, 1.5, .3], f: 34 }, { t: T_USO, p: [1.5, 3.1, 6.7], l: [.2, 1.36, .9], f: 34 }, { t: D.total + 1, p: [.5, 3.3, 6.6], l: [.2, 1.36, .9], f: 34 });
for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01;

// rótulos e sons ---------------------------------------------------------------------------------------------------------------------------------------------
const YC_ = .82; [['SEM GÁS', [-.2, 2.3, .5], F(0) + .2, fim(0), 'ruim'], ['COMPRESSOR', [.4, .95, -.62], T.com, fim(1), 'ouro'], ['SERPENTINA', [.35, 1.05, -.62], T.ser, fim(2), 'ouro'], ['ALETAS', [.3, 1.05, -.62], T.ale, fim(3), 'ouro'], ['EXAUSTOR', [.3, 1.1, -.62], T.exa, fim(4), 'ouro'], ['TUBOS', [-.35, 1.85, -.22], T.tub, fim(5), 'ouro'], ['EVAPORADORA', [.5, 2.5, .15], T.eva, fim(6), 'ouro'], ['FILTRO', [.4, 2.5, .15], T.fil, fim(7), 'ouro'], ['TURBINA', [.4, 2.4, .15], T.tur, fim(8), 'ouro'], ['VÁLVULA', [-.1, 1.5, -.3], T.val, fim(9), 'ouro']].forEach(l => { rotulo(...l); if (l[4] === 'ouro') som(l[2], 'ding'); });
rotulo('AR-CONDICIONADO PRONTO!', [540, 290], F(LAST) + .1, T_USO, 'grande').style.fontSize = '60px';
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); som(.3, 'zumbido'); som(1, 'zumbido'); som(T_Q + .1, 'crack'); som(T_Q + .9, 'desaba'); som(T_Q + .92, 'impact');
for (let q = T.com + 2.4; q < T.ser; q += .9) som(q, 'motor'); for (let q = T.exa + 1.7; q < fim(4); q += 1) som(q, 'zumbido'); for (let q = T.val; q < F(LAST); q += .5) som(q, 'gota');
som(T_USO + .1, 'whoosh'); som(F(LAST) + .1, 'ding'); som(T_F, 'riser'); for (let q = T_F + .4; q < D.total; q += 1.1) som(q, 'zumbido'); for (let q = T_F + .9; q < D.total; q += .95) som(q, 'chuva');

window.CAPA_T = T_USO + 4.4;
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); AUTO.forEach(f => f(t)); });
