// Tratamento de água. Um mundo só, cortado como maquete: rio, estação, morro e cidade. A água muda de cor de tanque em tanque.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, tex, arvore, camTo, iniciar, som, rotulo, fala, D } = K3;
const rnd = prng(61), F = fala, fim = i => F(i) + D.falas[i].dur, N = D.falas.length, AUTO = [], O = new THREE.Object3D(), C = new THREE.Color(), C2 = new THREE.Color(), PI = Math.PI;
const nk = x => String(x).toLowerCase().normalize('NFD').replace(/[^a-z0-9]/g, '');
const tk = (w, i, f = .4) => { const k = nk(w), q = D.falas[i].words?.find(p => nk(p.w).startsWith(k)); return q ? q.start : F(i) + D.falas[i].dur * f; };
const nomeT = i => { const q = [...(D.falas[i].words ?? [])].reverse().find(p => /^(essa|esse)$/.test(nk(p.w))); return q ? q.start : fim(i) - 1.2; };
const T_USO = tk('transparente', N - 1, .55) - .3;
const rev = (t, a, b) => clamp((t - a) / (b - a)), sm = (a, b, x) => ease((x - a) / (b - a));
const CI = {}; for (let i = 1; i < N - 1; i++) CI[i] = { a: F(i), e: tk('Então', i, .4), n: nomeT(i) };

// céu, sol e névoa ---------------------------------------------------------------------------------------------
const CEU = '#3f8fe0'; ceu(CEU, '#d6eefa'); const fundo = scene.background; scene.fog = new THREE.Fog(0xcfe6f2, 70, 420);
const sol = luzes(0xfff2de, 0xd8ecff, 0x8fb070, 2.3, 70); add(sol.target); scene.environmentIntensity = .3; const hemi = []; scene.traverse(o => { if (o.isHemisphereLight) { hemi.push(o); o.intensity = 1.05; } });
const flash = document.createElement('div'); flash.style.cssText = 'position:absolute;inset:0;background:#f4fbff;opacity:0'; document.getElementById('hud').prepend(flash);
const B = (g, w, h, d, c, x, y, z, r = .02, o) => { const m = add(box(w, h, d, c, r, o), g); m.position.set(x, y, z); return m; };
const MET = { roughness: .34, metalness: .55 }, VID = { roughness: .12, metalness: .4 };
const pc = (n, g, x, y, z, ry = 0, o, e = 1) => { const q = PC.novo(n, o); q.position.set(x, y, z); q.rotation.y = ry; if (e !== 1) q.scale.multiplyScalar(e); g.add(q); return q; };
const curva = p => new THREE.CatmullRomCurve3(p.map(q => new THREE.Vector3(...q)));
const tubo = (g, cur, r, c, n = 80, o = {}) => add(sh(new THREE.Mesh(new THREE.TubeGeometry(cur, n, r, 10), typeof c === 'object' ? c : mat(c, o))), g);
const mostra = (o, a, b = 1e9) => AUTO.push(t => { o.visible = t >= a && t < b; });
const poe = (o, t0, d = .3, t1 = 1e9) => { const s = o.scale.clone(); o.visible = false; AUTO.push(t => { o.visible = t >= t0 && t < t1; if (o.visible) o.scale.copy(s).multiplyScalar(Math.max(back((t - t0) / d), .01)); }); return o; };
const sobe = (o, t0, d = .7) => { o.visible = false; AUTO.push(t => { o.visible = t >= t0; o.scale.y = Math.max(ease((t - t0) / d), .01); }); return o; };
const cresce = (m, t0, d) => { const n = m.geometry.index.count; AUTO.push(t => { const k = ease(rev(t, t0, t0 + d)); m.visible = k > 0; m.geometry.setDrawRange(0, Math.floor(k * n / 6) * 6); }); return m; };
const parts = (g, n, geo, c, fn, basic = false) => { const I = new THREE.InstancedMesh(geo, basic ? new THREE.MeshBasicMaterial({ color: c, toneMapped: false }) : mat(c, { flatShading: true }), n); I.frustumCulled = false; add(I, g); AUTO.push(t => { if (!g.visible) return; let on = false; for (let i = 0; i < n; i++) { O.rotation.set(0, 0, 0); O.scale.setScalar(1); const s = fn(i, t, O); if (s !== false) on = true; else O.scale.setScalar(.0001); O.updateMatrix(); I.setMatrixAt(i, O.matrix); } I.visible = on; I.instanceMatrix.needsUpdate = true; }); return I; };
const GEO_P = new THREE.IcosahedronGeometry(1, 0), GEO_E = new THREE.SphereGeometry(1, 10, 8);
const pulsos = (g, cur, n, c, ativo, vel = .3, r = .17) => parts(g, n, GEO_E, c, (i, t, o) => { if (!ativo(t)) return false; const p = cur.getPointAt((t * vel + i / n) % 1); o.position.copy(p); o.scale.setScalar(r); }, true);
const CORES = { bruta: 0x8d6332, turva: 0xa98a55, leve: 0x9cc0b0, clara: 0x4fb4e8, limpa: 0x2f9df0 };
const lerpH = (a, b, k) => C2.set(a).lerp(C.set(b), clamp(k)).getHex();

// o mundo: rio à esquerda, estação no plano, morro e cidade à direita -------------------------------------------
const MUNDO = new THREE.Group(); add(MUNDO);
const ZF = 8, RX = -58, WL = -.7, TOPO_M = 16.5;
const h = (x, z) => {
  const rx = RX + (z < -25 ? Math.sin((z + 25) * .018) * 10 : 0), d = Math.abs(x - rx);
  const pl = (1 - sm(30, 38, x)) * sm(-47, -43, x) * sm(-46, -36, z), ci = sm(80, 86, x) * sm(-190, -150, z), flat = Math.max(pl, ci);
  const bump = (Math.sin(x * .13 + z * .09) * .5 + Math.sin(x * .31 - z * .17) * .22 + .7) * (1 - flat);
  const fundoM = sm(-50, -140, z) * (12 + 7 * Math.sin(x * .021) + 4 * Math.sin(x * .057 + 1)) * (1 - ci);
  const morro = Math.min(21 * Math.exp(-(((x - 54) / 18) ** 2)), TOPO_M) * sm(29, 38, x) * (1 - sm(72, 86, x));
  const y = bump + fundoM + morro + sm(-76, -112, x) * 9;
  return y + (-3.2 - y) * (1 - sm(9, 14, d));
};
{ const W = 560, P_ = 320, geo = new THREE.PlaneGeometry(W, P_, 280, 160); geo.rotateX(-PI / 2); geo.translate(40, 0, ZF - P_ / 2); const pos = geo.attributes.position, cor = new Float32Array(pos.count * 3);
  for (let i = 0; i < pos.count; i++) { const x = pos.getX(i), z = pos.getZ(i), y = h(x, z); pos.setY(i, y); const d = Math.abs(x - RX), n = Math.sin(x * .37 + z * .23) * .5 + Math.sin(x * .11 - z * .31) * .5;
    C.set(0x4cae50).offsetHSL(n * .018, 0, n * .03); if (d < 17 && z > -26) C.lerp(C2.set(0xcdb67e), 1 - sm(13, 17, d)); if (y < -1) C.set(0x6d5536); if (y > 15) C.lerp(C2.set(0x6fae5c), .5); cor[i * 3] = C.r; cor[i * 3 + 1] = C.g; cor[i * 3 + 2] = C.b; }
  geo.setAttribute('color', new THREE.BufferAttribute(cor, 3)); geo.computeVertexNormals(); const m = add(new THREE.Mesh(geo, mat(0xffffff, { vertexColors: true, roughness: 1 })), MUNDO); m.receiveShadow = true; MUNDO.userData.chao = m; }
// fatia do terreno
const faixa = (top, bot, c, dz = 0) => { const s = new THREE.Shape(); const xs = []; for (let x = -240; x <= 320; x += 2) xs.push(x); xs.forEach((x, i) => i ? s.lineTo(x, top(x)) : s.moveTo(x, top(x))); [...xs].reverse().forEach(x => s.lineTo(x, bot(x))); s.closePath(); const m = add(new THREE.Mesh(new THREE.ShapeGeometry(s), mat(c, { roughness: 1 })), MUNDO); m.position.z = ZF + dz; return m; };
const hf = x => h(x, ZF);
faixa(x => hf(x) - 1.5, () => -70, 0x8d6240); faixa(x => hf(x) - .45, x => hf(x) - 1.5, 0x5e3b28, .01); faixa(x => hf(x), x => hf(x) - .45, 0x4a8a3c, .02); faixa(() => -9, () => -14, 0x734a2e, .015);
{ const n = 420, I = new THREE.InstancedMesh(GEO_P, mat(0x9b8e80, { flatShading: true }), n); I.frustumCulled = false; add(I, MUNDO); let k = 0; while (k < n) { const x = -190 + rnd() * 460, y = -2.4 - rnd() * 30; if (y > hf(x) - 1.6 || Math.abs(y + 1.4) < .9) continue; O.position.set(x, y, ZF + .1); O.rotation.set(rnd() * 3, rnd() * 3, 0); O.scale.setScalar(.12 + rnd() * .4); O.updateMatrix(); I.setMatrixAt(k, O.matrix); I.setColorAt(k, C.set(0x9b8e80).offsetHSL(0, 0, (rnd() - .5) * .16)); k++; } }
// rio: superfície correndo, com a fatia de água marrom
const texRio = tex(256, 256, (c, w, h_) => { c.fillStyle = '#8a6030'; c.fillRect(0, 0, w, h_); c.lineCap = 'round'; for (let i = 0; i < 60; i++) { const x = rnd() * w, y = rnd() * h_, l = 14 + rnd() * 26; c.strokeStyle = i % 3 ? 'rgba(186,146,88,.22)' : 'rgba(72,48,22,.16)'; c.lineWidth = 1.5 + rnd() * 2; c.beginPath(); c.moveTo(x - l, y); c.quadraticCurveTo(x, y + 7 * (i % 2 ? 1 : -1), x + l, y); c.stroke(); } }, 9, 44);
const RIO = add(new THREE.Mesh(new THREE.PlaneGeometry(62, 330), new THREE.MeshStandardMaterial({ map: texRio, roughness: .3, metalness: .05 })), MUNDO); RIO.rotation.x = -PI / 2; RIO.position.set(RX, WL, ZF - 165); RIO.receiveShadow = true; AUTO.push(t => { texRio.offset.y = -t * .32; });
{ const s = new THREE.Shape(); const xs = []; for (let x = -80; x <= -40; x += 1) if (hf(x) < WL) xs.push(x); xs.forEach((x, i) => i ? s.lineTo(x, WL) : s.moveTo(x, WL)); [...xs].reverse().forEach(x => s.lineTo(x, hf(x))); s.closePath(); const m = add(new THREE.Mesh(new THREE.ShapeGeometry(s), new THREE.MeshBasicMaterial({ color: 0x7a5429, transparent: true, opacity: .9 })), MUNDO); m.position.z = ZF + .03; }
// morros na névoa, nuvens e árvores
[[-170, -300, 130, 70], [-30, -330, 150, 58], [130, -320, 170, 78], [280, -290, 130, 52], [-300, -260, 120, 60]].forEach(([x, z, r, a], i) => { const m = add(new THREE.Mesh(new THREE.ConeGeometry(r, a, 7), mat([0x4f9a70, 0x5ca680, 0x487f6b][i % 3], { flatShading: true })), MUNDO); m.position.set(x, a / 2 - 1, z); m.scale.z = .6; });
const NUV = []; for (let i = 0; i < 12; i++) { const g = new THREE.Group(); g.position.set(-190 + i * 44 + rnd() * 20, 62 + rnd() * 30, -210 - rnd() * 60); add(g, MUNDO); for (let k = 0; k < 5; k++) { const s = add(new THREE.Mesh(new THREE.SphereGeometry(7 + rnd() * 7, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffffff, fog: false })), g); s.position.set((k - 2) * 8, rnd() * 3, 0); s.scale.y = .55; } NUV.push(g); }
const zonaLivre = (x, z) => (x > -46 && x < 36 && z > -44) || (x > 78 && z > -170) || Math.abs(x - RX - (z < -25 ? Math.sin((z + 25) * .018) * 10 : 0)) < 15 || (Math.abs(x - 54) < 12 && z > -14);
{ let n = 0; while (n < 75) { const x = -190 + rnd() * 340, z = ZF - 2 - rnd() * 170; if (zonaLivre(x, z)) continue; const a = add(arvore(rnd, 2 + rnd() * 2.4, rnd() > .55), MUNDO); a.position.set(x, h(x, z) - .05, z); n++; }
  const nF = 900, f = new THREE.InstancedMesh(new THREE.ConeGeometry(2.1, 6.4, 6), mat(0x2f8f44, { flatShading: true }), nF); f.frustumCulled = false; f.castShadow = true; add(f, MUNDO); let k = 0; while (k < nF) { const x = -220 + rnd() * 520, z = -30 - rnd() * 270; if (zonaLivre(x, z)) continue; O.position.set(x, h(x, z) + 2.8, z); O.rotation.set(0, rnd() * 3, 0); O.scale.setScalar(.8 + rnd() * .9); O.updateMatrix(); f.setMatrixAt(k, O.matrix); f.setColorAt(k, C.set(0x2f8f44).offsetHSL(rnd() * .04, 0, (rnd() - .5) * .09)); k++; } }
// pedras e capim na margem
{ const n = 90, I = new THREE.InstancedMesh(GEO_P, mat(0x8f8778, { flatShading: true }), n); I.frustumCulled = false; I.castShadow = true; add(I, MUNDO); for (let i = 0; i < n; i++) { const s = i % 2 ? 1 : -1, x = RX + s * (11 + rnd() * 6), z = ZF - rnd() * 130; O.position.set(x, h(x, z) + .1, z); O.rotation.set(rnd() * 3, rnd() * 3, 0); O.scale.set(.3 + rnd() * .7, .2 + rnd() * .4, .3 + rnd() * .7); O.updateMatrix(); I.setMatrixAt(i, O.matrix); } }

// pátio da estação: calçamento, escritório, galpão, cerca, postes, gente ---------------------------------------
const CONC = 0xcfccc2, CONC2 = 0xb4b6b4, CORTE = 0xf0ece0;
const plano = (x, z, w, d, c, y = .03) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, d), mat(c, { roughness: 1 })), MUNDO); m.rotation.x = -PI / 2; m.position.set(x, y, z); m.receiveShadow = true; return m; };
const ANTES = new THREE.Group(); add(ANTES); const ESTACAO = new THREE.Group(); add(ESTACAO);
plano(-5, -18, 70, 50, 0xbdbbb0, .03); plano(-5, -36, 70, 8, 0x4b5057, .05); for (let i = 0; i < 12; i++) B(ESTACAO, 2.4, .02, .18, 0xf2d24a, -38 + i * 6, .07, -36, .005);
{ const g = ESTACAO; B(g, 15, 6, 8, 0xf1eee6, 6, 3, -21, .04); B(g, 15.6, .4, 8.6, 0x2f7fd6, 6, 6.2, -21, .03); for (let i = 0; i < 5; i++) { B(g, 1.9, 1.3, .06, 0x8fc6df, .8 + i * 2.6, 4.2, -16.97, .01, VID); B(g, 1.9, 1.3, .06, 0x8fc6df, .8 + i * 2.6, 1.8, -16.97, .01, VID); } B(g, 1.5, 2.4, .06, 0x2c5f78, 11.8, 1.2, -16.96, .01);
  B(g, 12, 5, 8, 0xd9d3c4, -18, 2.5, -21, .04); B(g, 12.6, .4, 8.6, 0x8a5a3c, -18, 5.2, -21, .03); B(g, 5, 3.6, .06, 0x6f7a84, -18, 1.8, -16.96, .01);
  pc('veiculo_van', g, -6, .03, -20, .4, { cor: 0xf4f4f2 }); pc('veiculo_picape', g, 23, .03, -22, -.5, { cor: 0x2f7fd6 });
  [-40, -22, -6, 12, 28].forEach(x => pc('rua_poste_luz', g, x, 0, -13, 0)); for (let i = 0; i < 14; i++) { const q = B(g, .06, 1.8, .06, 0x8a8f94, -40 + i * 6, .9, -41, .01, MET); B(g, 6, .05, .05, 0x8a8f94, -37 + i * 6, 1.7, -41, .005, MET); B(g, 6, .05, .05, 0x8a8f94, -37 + i * 6, .7, -41, .005, MET); } }
// tanque em corte: sem parede da frente
const H_T = 5.2, ZB = -7, BB = [];
const tanque = (x0, x1, t0) => { const g = new THREE.Group(); ESTACAO.add(g); const w = x1 - x0, xm = (x0 + x1) / 2; B(g, w + .6, .3, -ZB + .3, CONC2, xm, .15, ZB / 2, .01); B(g, w + .6, H_T, .3, 0xc4c7c6, xm, H_T / 2, ZB - .15, .01); [x0 - .15, x1 + .15].forEach(x => { B(g, .3, H_T, -ZB, CONC, x, H_T / 2, ZB / 2, .01); B(g, .32, H_T, .02, CORTE, x, H_T / 2, .01, .005); }); B(g, w + .6, .32, .02, CORTE, xm, .15, .16, .005);
  B(g, w + .8, .12, 1.1, 0x9aa1a8, xm, H_T + .06, ZB + .1, .01, MET); for (let i = 0; i <= Math.floor(w / 2); i++) B(g, .06, 1, .06, 0xffc21a, x0 + i * 2, H_T + .6, ZB + .55, .01); B(g, w + .6, .07, .07, 0xffc21a, xm, H_T + 1.08, ZB + .55, .01); B(g, w + .6, .3, .04, 0x2f7fd6, xm, H_T - .3, ZB + .01, .005); sobe(g, t0); return g; };
const agua = (g, x0, x1, y0, y1, zt = ZB, nx = 24) => { const w = x1 - x0, a = y1 - y0, gr = new THREE.Group(); gr.position.set(x0, y0, 0); g.add(gr); const m = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: .82, toneMapped: false, side: THREE.DoubleSide, depthWrite: false }), m2 = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: .92, toneMapped: false, side: THREE.DoubleSide });
  const fg = new THREE.PlaneGeometry(w, a, nx, 1); fg.translate(w / 2, a / 2, .05); const tg = new THREE.PlaneGeometry(w, -zt, nx, 1); tg.rotateX(-PI / 2); tg.translate(w / 2, 0, zt / 2); const cf = new Float32Array((nx + 1) * 6), ct = new Float32Array((nx + 1) * 6); fg.setAttribute('color', new THREE.BufferAttribute(cf, 3)); tg.setAttribute('color', new THREE.BufferAttribute(ct, 3));
  const fr = add(new THREE.Mesh(fg, m), gr), to = add(new THREE.Mesh(tg, m2), gr), li = add(new THREE.Mesh(new THREE.PlaneGeometry(w, .05), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: .55, toneMapped: false })), gr); li.position.set(w / 2, 0, .07);
  const A = { gr, nivel(k) { k = Math.max(k, .001); fr.scale.y = k; to.position.y = li.position.y = a * k; gr.visible = k > .002; }, cor(fn) { for (let r = 0; r < 2; r++) for (let i = 0; i <= nx; i++) { C.set(fn(i / nx)); const j = (r * (nx + 1) + i) * 3; [cf, ct].forEach(q => { q[j] = C.r; q[j + 1] = C.g; q[j + 2] = C.b; }); } fg.attributes.color.needsUpdate = tg.attributes.color.needsUpdate = true; } }; AG.push(m, m2); return A; };
const AG = [];

{ const g = ESTACAO, mz = 5.7; tubo(g, curva([[-33, .34, mz], [0, .34, mz], [28, .34, mz]]), .15, 0x4aa8ff, 30); for (let x = -32; x < 28; x += 5) B(g, .36, .22, .36, 0x8a8f94, x, .11, mz, .02); [-26, -11, 7, 18].forEach(x => pc('inf_valvula', g, x, 0, -.2 + 1.4, 0, undefined, .7));
  for (let i = 0; i < 2; i++) B(g, 66, .02, .16, 0xf2d24a, -2.5, .06, 1.3 + i * 4.6, .005); for (let x = -36; x < 30; x += 4.4) { B(g, 3.4, .28, .9, 0xa8a196, x, .15, 6.9, .02); const a = add(new THREE.Mesh(GEO_P, mat(0x3fa45a, { flatShading: true })), g); a.position.set(x, .46, 6.9); a.scale.set(1.5, .26, .42); a.castShadow = true; const b = add(new THREE.Mesh(GEO_P, mat(0xf29ab8, { flatShading: true })), g); b.position.set(x + .9, .68, 6.8); b.scale.setScalar(.1); }
  [[-20, 2.2], [-4, 5.2], [14, 2.1]].forEach(([x, z]) => { const c = add(cil(.05, .17, .5, 0xf28a2a, 12), g); c.position.set(x, .3, z); }); }
{ tubo(MUNDO, curva([[-36, -3.1, ZF + .1], [-3, -3.1, ZF + .1], [30, -3.1, ZF + .1]]), .22, 0x8a8f94, 6); for (let x = -30; x < 30; x += 9) { const m = add(cil(.26, .26, .08, 0x59626c, 16), MUNDO); m.rotation.z = PI / 2; m.position.set(x, -3.1, ZF + .1); } }

// abertura: cano direto no rio ------------------------------------------------------------------------------------
const CRU = curva([[-52.5, -.9, 2.2], [-50, -.45, 2.4], [-46, .3, 3], [-30, .3, 5], [10, .3, 5.5], [50, h(50, 5) + .3, 5.5], [90, .3, 5.5]]);
const CRUm = tubo(ANTES, CRU, .22, 0x1c2026, 200); pulsos(ANTES, CRU, 90, 0xb58a50, t => t < F(1), .05, .24); mostra(ANTES, -1, F(1) + .02);
{ const m = add(cil(.3, .3, .3, 0x1c2026, 18), ANTES); m.rotation.z = PI / 2 - .3; m.position.set(-52.6, -.92, 2.2); }

// lixo no rio ----------------------------------------------------------------------------------------------------
const mkGalho = () => { const g = new THREE.Group(); tubo(g, curva([[-1.1, 0, 0], [-.2, .05, .1], [.4, .02, -.1], [1.2, .08, .05]]), .07, 0x6b4a2c, 12); tubo(g, curva([[.2, .03, 0], [.6, .1, .5], [.8, .12, .8]]), .04, 0x6b4a2c, 8); [[1.2, .1, .1], [.8, .14, .85], [-.5, .1, .2]].forEach(([x, y, z]) => { const f = add(new THREE.Mesh(GEO_P, mat(0x3f8f3a, { flatShading: true })), g); f.position.set(x, y, z); f.scale.set(.32, .12, .24); }); return g; };
const mkFolha = () => { const g = new THREE.Group(), f = add(new THREE.Mesh(GEO_P, mat(0x6fb03a, { flatShading: true })), g); f.scale.set(.32, .05, .18); return g; };
const mkGarrafa = () => { const g = new THREE.Group(), a = add(cil(.11, .11, .5, 0xcdeaf2, 12, { transparent: true, opacity: .8, roughness: .2 }), g); a.rotation.z = PI / 2; const b = add(cil(.045, .05, .1, 0x2f7fd6, 10), g); b.rotation.z = PI / 2; b.position.x = .3; return g; };
const mkPneu = () => { const g = new THREE.Group(), a = add(new THREE.Mesh(new THREE.TorusGeometry(.42, .17, 10, 22), mat(0x1b1d22)), g); a.rotation.x = PI / 2; a.castShadow = true; return g; };
const tG = tk('grade', 1), tBo = tk('bomba', 1), LIXO = []; for (let i = 0; i < 16; i++) { const f = [mkGalho, mkGarrafa, mkFolha, mkPneu, mkFolha, mkGalho, mkGarrafa, mkFolha][i % 8](); f.rotation.y = rnd() * 6; f.scale.setScalar(1.7); add(f, MUNDO); LIXO.push({ f, x: RX + 2 + rnd() * 6, f0: i * 4.7, zs: -5.3 + (i % 8) * 1, ys: WL + .08 + (i > 7 ? .16 : 0), ry: rnd() * 6 }); }
AUTO.push(t => { LIXO.forEach((q, i) => { const fz = -66 + (t * 2.6 + q.f0) % 76, ry = q.ry + Math.sin(t * .5 + i) * .4, on = i < 12, k = on ? ease(rev(t, tG + .5 + i * .22, tG + 1.9 + i * .22)) : 0, x = q.x + (-48.9 - q.x - (i % 3) * .2) * k, z = fz + (q.zs - fz) * k; q.f.position.set(x, q.ys + Math.sin(t * 2.2 + i) * .03, z); q.f.rotation.y = ry * (1 - k) + (i % 2 ? PI / 2 : 0) * k; }); });

// captação --------------------------------------------------------------------------------------------------------
const c1 = CI[1], CAP = new THREE.Group(); add(CAP); mostra(CAP, tG - .15);
{ const g = CAP; B(g, 4.6, 5.2, 9, CONC, -46, -.6, -2, .02); B(g, 4.8, .2, 9.2, CONC2, -46, 2.05, -2, .02); B(g, .06, 2.6, 7.6, 0x20262c, -48.33, -1.1, -2, .005);
  B(g, 4.6, .08, .08, 0xffc21a, -46, 2.95, 2.5, .01); B(g, .08, .08, 9.2, 0xffc21a, -43.7, 2.95, -2, .01); for (let i = 0; i < 6; i++) B(g, .07, .9, .07, 0xffc21a, -43.7, 2.5, 2.5 - i * 1.8, .01);
  const barras = []; for (let i = 0; i < 12; i++) { const b = add(cil(.085, .085, 4.8, mat(0x98a3ae, MET), 10), g); barras.push(b); const t0 = tG + i * .05; AUTO.push(t => { b.position.set(-48.75, -.3 + (1 - ease(rev(t, t0, t0 + .32))) * 7, -5.6 + i * .66); }); som(t0 + .28, 'toc'); } B(g, .14, .2, 7.8, 0x3f4750, -48.75, 2, -2, .02, MET); B(g, .14, .2, 7.8, 0x3f4750, -48.75, 0, -2, .02, MET);
  const tec = pc('personagem', g, -45.6, 2.15, .4, -PI / 2 - .3, { camisa: 0x2f7fd6, camisa2: 0x2565b5 }); AUTO.push(t => { tec.r.anda(0, 0); tec.r.respira(t); tec.r.bd.j.rotation.x = -.5; }); }
const AD = curva([[-44.2, .9, -2], [-41, .9, -2], [-37.6, .9, -2], [-35.5, 1.1, -2], [-34.95, 3, -2], [-34.95, 5.5, -2], [-34.3, 6.05, -2], [-33.2, 5.7, -2]]);
const CASA_B = new THREE.Group(); add(CASA_B); poe(CASA_B, tBo - .1, .01);
{ const g = CASA_B; B(g, 8.4, .3, 7, CONC2, -39.4, .15, -2, .01); [[-43.4, 1], [-35.4, 1], [-43.4, -5], [-35.4, -5]].forEach(([x, z]) => B(g, .24, 3.6, .24, 0xe9e4d8, x, 1.9, z, .01)); B(g, 8.8, .24, 7.2, 0x2f7fd6, -39.4, 3.8, -2, .02); const bo = pc('bomba_dagua', g, -40, .3, -2, 0, undefined, 1.5); AUTO.push(t => { bo.position.y = .3 + (t > tBo + .4 ? Math.sin(t * 70) * .006 : 0); }); }
const VIDRO_T = { transparent: true, opacity: .34, roughness: .15, metalness: .1, color: 0xcfe6ee }; const AD_m = tubo(MUNDO, AD, .3, new THREE.MeshStandardMaterial(VIDRO_T), 140); cresce(AD_m, tBo + .15, 1.1); pulsos(MUNDO, AD, 24, 0xa8743a, t => t > tBo + .9, .22, .19);

// coagulação ------------------------------------------------------------------------------------------------------
const c2 = CI[2], X1 = -34, X2 = -27, tGr = tk('gruda', 2), TQ1 = tanque(X1, X2, F(2) - .1), A1 = agua(ESTACAO, X1, X2, .3, H_T - .55); const tPr = tk('produto', 2);
const QUEDA1 = parts(TQ1, 26, GEO_E, 0xa8743a, (i, t, o) => { if (t < F(2) + .2) return false; const q = (t * 1.3 + i / 26) % 1; o.position.set(-33.2 + Math.sin(i) * .1, 5.6 - q * 5.1, -2 + Math.cos(i * 2) * .14 + 1.6); o.scale.setScalar(.09); });
{ const g = new THREE.Group(); TQ1.add(g); poe(g, tPr - .35, .3); const pl = g; B(pl, 3, .16, 1.8, 0x9aa1a8, -28.8, H_T + .2, ZB + .8, .01, MET); const t_ = add(cil(.8, .8, 1.9, 0xf4f4f2, 26), pl); t_.position.set(-28.8, H_T + 1.25, ZB + .8); add(cil(.82, .82, .22, 0x2f7fd6, 26), pl).position.set(-28.8, H_T + 1.6, ZB + .8); add(cil(.82, .82, .1, 0x2f7fd6, 26), pl).position.set(-28.8, H_T + .55, ZB + .8);
  tubo(pl, curva([[-28.8, H_T + .4, ZB + 1.6], [-29.4, H_T + .5, -3], [-30.5, H_T + .4, -.9], [-30.5, H_T + .1, -.7]]), .05, 0xeef0f2, 30);
  parts(pl, 22, GEO_E, 0xffffff, (i, t, o) => { if (t < tPr || t > tGr + 1.4) return false; const q = (t * 1.8 + i / 22) % 1; o.position.set(-30.5 + Math.sin(i * 3) * .09, H_T + .05 - q * 1.05, -.45); o.scale.setScalar(.075); }, true);
  // misturador
  const eixo = new THREE.Group(); eixo.position.set(-32.3, 0, -1.3); pl.add(eixo); add(cil(.06, .06, 4.4, mat(0x6a7682, MET), 8), eixo).position.y = 3.3;[0, 1].forEach(i => { const p = B(eixo, 1.5, .34, .08, 0x6a7682, 0, 1.5, 0, .02, MET); p.rotation.y = i * PI / 2; }); AUTO.push(t => { eixo.rotation.y = t * 7; }); B(pl, .9, .6, .7, 0x2f7fd6, -32.3, H_T + .35, -1.3, .05); B(pl, 2, .1, .3, 0x6a7682, -32.3, H_T + .02, -1.3, .01, MET); }
const NG = 170, G1 = []; for (let i = 0; i < NG; i++) { const cl = i % 16; G1.push({ x: X1 + .4 + rnd() * 6.2, y: .55 + rnd() * 3.9, cx: X1 + .9 + (cl % 4) * 1.75 + rnd() * .15, cy: .95 + Math.floor(cl / 4) * 1.05, ox: (rnd() - .5) * .36, oy: (rnd() - .5) * .36, p: rnd() * 9 }); }
parts(TQ1, NG, GEO_P, 0x4e3216, (i, t, o) => { if (t < F(2) + .4 || t > fim(3) + .2) return false; const q = G1[i], k = ease(rev(t, tGr + .1 + (i % 16) * .03, tGr + 1.1 + (i % 16) * .03)), fx = q.x + Math.sin(t * 1.6 + q.p) * .28, fy = q.y + Math.cos(t * 1.3 + q.p) * .2, cx = q.cx + q.ox + Math.sin(t * .8 + q.p) * .1, cy = q.cy + q.oy + Math.sin(t * .9 + (i % 16)) * .14; o.position.set(fx + (cx - fx) * k, fy + (cy - fy) * k, -.25 - (i % 3) * .15); o.scale.setScalar(.07); o.rotation.set(q.p, q.p * 2, 0); });

// floculação ------------------------------------------------------------------------------------------------------
const c3 = CI[3], X3 = -25, X4 = -12, TQ2 = tanque(X3, X4, c3.e - .1), A2 = agua(ESTACAO, X3, X4, .3, H_T - .55); const RODAS = [];
for (let i = 1; i < 3; i++) { const m = B(TQ2, .24, 3.7, 6.8, 0xbcbfbe, X3 + i * 13 / 3, 2.35, ZB / 2, .01); B(TQ2, .25, 3.7, .02, CORTE, X3 + i * 13 / 3, 2.35, .01, .005); }
for (let i = 0; i < 3; i++) { const g = new THREE.Group(); g.position.set(X3 + (i + .5) * 13 / 3, 2.5, -1.2); TQ2.add(g); const ei = add(cil(.09, .09, 5.6, mat(0x59626c, MET), 10), g); ei.rotation.x = PI / 2; ei.position.z = -2.4; for (let a = 0; a < 4; a++) { const br = new THREE.Group(); br.rotation.z = a * PI / 2; g.add(br); B(br, .12, 1.75, .12, 0x6a7682, 0, .9, 0, .01, MET);[.6, 1.2, 1.7].forEach(y => B(br, .52, .1, 1.4, 0xe8e4da, 0, y, -.2, .02)); } RODAS.push(g); B(TQ2, 1, .6, .8, 0x2f7fd6, g.position.x, H_T + .42, ZB + .4, .05); }
AUTO.push(t => { RODAS.forEach((g, i) => { g.rotation.z = -(t - c3.e) * (.95 - i * .22); }); });
const NF = 120, FL = []; for (let i = 0; i < NF; i++) FL.push({ cam: i % 3, a: rnd() * 6.28, r: .6 + rnd() * 1.2, y: rnd(), p: rnd() * 9, z: -.25 - rnd() * .3 });
const flocoGeo = new THREE.IcosahedronGeometry(1, 1); parts(TQ2, NF, flocoGeo, 0x5c3b1b, (i, t, o) => { const q = FL[i]; if (t < c3.e + .5) return false; const cx = X3 + (q.cam + .5) * 13 / 3, ang = q.a - (t - c3.e) * (.9 - q.cam * .2), g = ease(rev(t, c3.e + .6 + q.cam * .5, c3.e + 3 + q.cam * .5)), s = (.09 + (q.cam * .09 + .05) * g + (i % 5) * .012) * (.5 + .5 * ease(rev(t, c3.e + .4, c3.e + 1))); o.position.set(cx + Math.cos(ang) * q.r, 2.45 + Math.sin(ang) * q.r * 1.1, q.z); o.scale.setScalar(s); o.rotation.set(q.p, q.p * 2, 0); });

// decantação ------------------------------------------------------------------------------------------------------
const c4 = CI[4], X5 = -10, X6 = 6, TQ3 = tanque(X5, X6, c4.e - .1), A3 = agua(ESTACAO, X5, X6, .3, H_T - .55, ZB, 32);
const LODO = add(new THREE.Mesh(new THREE.BoxGeometry(15.8, 1, .1), mat(0x4a2f15, { roughness: 1 })), TQ3); LODO.position.set(-2, .32, .03); const LODO2 = add(new THREE.Mesh(new THREE.BoxGeometry(15.8, 1, 6.8), mat(0x54361a, { roughness: 1 })), TQ3); LODO2.position.set(-2, .32, -3.4);
const ras = new THREE.Group(); TQ3.add(ras); B(ras, .14, .5, 6.6, 0x6a7682, 0, .55, -3.4, .01, MET); B(ras, .14, 4.9, .14, 0x6a7682, 0, 3, -6.6, .01, MET); const tEf = tk('afundam', 4); AUTO.push(t => { ras.position.x = -6.5 + Math.abs(((t * .12) % 2) - 1) * 13; const k = ease(rev(t, tEf - .6, tEf + 2.6)); [LODO, LODO2].forEach(m => { m.scale.y = Math.max(k * .95, .02); m.position.y = .32 + m.scale.y / 2; }); });
const NDF = 120, DF = []; for (let i = 0; i < NDF; i++) DF.push({ x: rnd(), y: rnd(), p: rnd() * 9, s: .14 + rnd() * .1, z: -.25 - rnd() * .4, d: rnd() * .6 });
parts(TQ3, NDF, flocoGeo, 0x5c3b1b, (i, t, o) => { const q = DF[i]; if (t < c4.e + .3) return false; const k = ease(rev(t, c4.e + .6 + q.d, tEf + 1 + q.d * 2)), x = X5 + .5 + q.x * (X6 - X5 - 1) * (.15 + .85 * Math.min(1, (t - c4.e) / 1.6)), yL = 1 + (q.x * .1), y0 = 1.6 + q.y * 2.9; o.position.set(x + Math.sin(t + q.p) * .1, y0 + (yL - y0) * k + Math.sin(t * 1.2 + q.p) * .06 * (1 - k), q.z); o.scale.setScalar(q.s * (1 - .25 * k)); o.rotation.set(q.p, q.p, 0); });
const c5 = CI[5], NM = 90, MI = []; for (let i = 0; i < NM; i++) MI.push({ x: rnd(), y: rnd(), p: rnd() * 9 });
parts(TQ3, NM, GEO_P, 0x6a4a22, (i, t, o) => { const q = MI[i]; if (t < c5.a - .2 || t > fim(5) + .4) return false; o.position.set(X5 + 5 + q.x * 10.6 + Math.sin(t * 1.2 + q.p) * .2, 2.1 + q.y * 2.4 + Math.cos(t * 1.5 + q.p) * .14, -.22); o.scale.setScalar(.05); o.rotation.set(q.p, q.p, 0); });

// filtração ------------------------------------------------------------------------------------------------------
const X7 = 8, X8 = 17, TQ4 = tanque(X7, X8, c5.e - .15), A4 = agua(ESTACAO, X7, X8, .3, H_T - .55);
const camada = (y0, y1, base, c1_, c2_, s0, s1, t0) => { const t_ = tex(512, 256, (c, w, h_) => { c.fillStyle = base; c.fillRect(0, 0, w, h_); for (let i = 0; i < 2400; i++) { c.fillStyle = i % 2 ? c1_ : c2_; const r = s0 + rnd() * s1; c.beginPath(); c.arc(rnd() * w, rnd() * h_, r, 0, 7); c.fill(); } }, 1, 1); const m = add(new THREE.Mesh(new THREE.PlaneGeometry(9, y1 - y0), new THREE.MeshStandardMaterial({ map: t_, roughness: 1 })), TQ4); m.position.set(12.5, (y0 + y1) / 2, .08); const tp = add(new THREE.Mesh(new THREE.BoxGeometry(9, y1 - y0, 6.8), mat(new THREE.Color(base).getHex(), { roughness: 1 })), TQ4); tp.position.set(12.5, (y0 + y1) / 2, -3.4); AUTO.push(t => { const k = Math.max(ease(rev(t, t0, t0 + .85)), .001), a = y1 - y0; [m, tp].forEach(q => { q.scale.y = k; q.position.y = y0 + a * k / 2; q.visible = t >= t0; }); }); };
const tAr = tk('areia', 5), tCa = tk('carvão', 5), Y_P = [.3, 1.2], Y_A = [1.2, 2.7], Y_C = [2.7, 3.8];
camada(Y_P[0], Y_P[1], '#8d8a84', '#b9b6ae', '#55524e', 7, 9, c5.e - .1); camada(Y_A[0], Y_A[1], '#ecd49a', '#d3b672', '#f9e9c4', 2, 3, tAr - .05); camada(Y_C[0], Y_C[1], '#2a2b30', '#4b4d55', '#15161a', 3, 5, tCa - .05);
const queda = (x, a, b, c, n = 44) => parts(TQ4, n, GEO_E, c, (i, t, o) => { if (t < a || t > b) return false; const q = (t * 2.2 + i / n) % 1; o.position.set(x + Math.sin(i * 7) * 1.4, 7.8 - q * 5 , -.4 - (i % 3) * .3); o.scale.setScalar(.07); }); queda(11, tAr - .3, tAr + .8, 0xecd49a); queda(14, tCa - .3, tCa + .8, 0x2a2b30);
{ const bica = new THREE.Group(); TQ4.add(bica); B(bica, 2.4, .9, 1.4, 0xf2b01e, 11.4, 8.4, -.5, .08); B(bica, 2.4, .9, 1.4, 0x3b3f46, 14.2, 8.4, -.5, .08); B(bica, 6, .12, .12, 0x59626c, 12.8, 9, -.5, .01, MET); mostra(bica, tAr - .4, tCa + 1); }
const NS = 60; parts(TQ4, NS, GEO_P, 0x6a4a22, (i, t, o) => { if (t < tCa + .6) return false; const q = (t * .34 + i / NS) % 1, x = X7 + .3 + (i * 37 % 84) / 10; o.position.set(x, Y_C[1] + .06 + (1 - clamp(q * 1.8)) * 0.85, -.22); o.scale.setScalar(.055); o.rotation.set(i, i, 0); });
parts(TQ4, 110, GEO_E, 0x8fdcff, (i, t, o) => { if (t < tCa + .9) return false; const q = (t * .5 + i / 110) % 1, x = X7 + .3 + (i * 53 % 84) / 10; o.position.set(x + Math.sin(q * 9 + i) * .08, Y_C[1] - q * 3.35, .16); o.scale.setScalar(.05); }, true);

// desinfecção --------------------------------------------------------------------------------------------------
const c6 = CI[6], X9 = 19, X10 = 27, TQ5 = tanque(X9, X10, c6.a - .1), A5 = agua(ESTACAO, X9, X10, .3, H_T - .55); const tGo = tk('pinga', 6), tMo = tk('morrem', 6), tCl = tk('cloro', 6);
for (let i = 1; i < 3; i++) { B(TQ5, .16, 3.9, 5.6, 0xbcbfbe, X9 + i * 8 / 3, i % 2 ? 2.25 : 2.65, ZB / 2 + (i % 2 ? .1 : -.1), .01); }
const CIL = new THREE.Group(); TQ5.add(CIL); poe(CIL, c6.e - .1, .3);
{ const g = CIL; B(g, 4.4, .16, 2, 0x9aa1a8, 24.4, H_T + .2, ZB + 1, .01, MET);[23, 24.5, 26].forEach(x => { const c = add(cil(.42, .42, 2.1, 0xf2c21e, 22), g); c.position.set(x, H_T + 1.34, ZB + .9); const ca = add(esf(.42, 0xf2c21e), g); ca.position.set(x, H_T + 2.38, ZB + .9); ca.scale.y = .5; B(g, .2, .22, .2, 0x59626c, x, H_T + 2.66, ZB + .9, .02, MET); add(cil(.44, .44, .24, 0x2f8f58, 22), g).position.set(x, H_T + 1.8, ZB + .9); }); tubo(g, curva([[23, H_T + 2.72, ZB + .9], [24, H_T + .9, -3.6], [23.2, H_T + .55, -1], [23, H_T + .2, -.75]]), .05, 0xf2c21e, 30); B(g, 2.4, 1, .1, 0xf4f4f2, 24.4, H_T + 1.1, ZB + 2.1, .01); }
parts(TQ5, 10, GEO_E, 0xf6ffd0, (i, t, o) => { if (t < tGo + .1) return false; const q = (t * 1.1 + i / 10) % 1; o.position.set(23, H_T + .15 - q * .95, -.55); o.scale.set(.1, .17, .1); som; }, true);
const LUPA = new THREE.Group(); LUPA.position.set(23, 2.55, .75); ESTACAO.add(LUPA); poe(LUPA, c6.a + .3, .3, fim(6));
{ const d = add(new THREE.Mesh(new THREE.CircleGeometry(2.1, 44), new THREE.MeshBasicMaterial({ color: 0xa8e0ff, toneMapped: false })), LUPA); AUTO.push(t => { d.material.color.setHex(t > tMo + .5 ? 0xd8f4ff : 0xa8e0ff); }); const r_ = add(new THREE.Mesh(new THREE.TorusGeometry(2.14, .15, 10, 44), mat(0x20262c, MET)), LUPA); r_.position.z = .03; const c_ = B(LUPA, .34, 1.9, .2, 0x8a4f22, 2.1, -2.2, .03, .07); c_.rotation.z = .78; }
const GER = []; { const conePos = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [.7, .7, 0], [-.7, .7, 0], [.7, -.7, 0], [-.7, -.7, 0]]; const mg = (c, n = 1) => { const g = new THREE.Group(); const b = add(esf(.26, c, { roughness: .5 }), g); b.scale.set(1.25, .85, .85); conePos.forEach(p => { const s = add(new THREE.Mesh(new THREE.CylinderGeometry(.015, .03, .22, 6), mat(0x20262c)), g); s.position.set(p[0] * .3, p[1] * .26, p[2] * .24); s.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(...p).normalize()); }); return g; }; for (let i = 0; i < 13; i++) { const a = i * 2.4, r = .42 + (i / 13) * 1.25, g = mg([0x56c04a, 0xe0577a, 0xc8a92a][i % 3]); g.position.set(Math.cos(a) * r, Math.sin(a) * r, .12); LUPA.add(g); GER.push({ g, x: g.position.x, y: g.position.y, t0: tMo - .3 + i * .06, p: i * 1.7 }); som(tMo - .3 + i * .06, i % 3 ? 'pop' : 'gota'); } }
AUTO.push(t => { GER.forEach(q => { q.g.visible = t < q.t0 + .22; const s = t < q.t0 ? 1 : Math.max(1 - (t - q.t0) / .2, .01); q.g.scale.setScalar(s); q.g.position.set(q.x + Math.sin(t * 2.2 + q.p) * .1, q.y + Math.cos(t * 1.9 + q.p) * .1, .12); q.g.rotation.z = t * .9 + q.p; }); });

// ligações entre tanques
const LIG = (x0, x1, c, t0) => { const cv = curva([[x0, 4.25, -2], [(x0 + x1) / 2, 4.3, -2], [x1, 4.25, -2]]); const m = tubo(ESTACAO, cv, .3, new THREE.MeshStandardMaterial(VIDRO_T), 16); AUTO.push(t => { m.visible = t > t0; }); pulsos(ESTACAO, cv, 4, c, t => t > t0, .7, .19); };
LIG(X2 - .1, X3 + .1, 0x9a7a44, c3.e + .2); LIG(X4 - .1, X5 + .1, 0x9fbaa8, c4.e + .2); LIG(X6 - .1, X7 + .1, 0x88cfe4, c5.e + .2); LIG(X8 - .1, X9 + .1, 0x3fb0f4, c6.a + .3);
const SAI = curva([[27.2, 1.1, -2.5], [29, .7, -2.5], [31, .3, 1], [32, .1, 6], [32.4, -.5, 8.14], [33, -1.4, 8.14]]);

// gente e obra em volta da estação
{ const pes = [[-26, -8.6, 0xf28a2a], [-11, -8.6, 0x2f7fd6], [7, -8.6, 0x2fbf8f], [18, -8.6, 0xe0577a]]; pes.forEach(([x, z, c], i) => { const q = pc('personagem', ESTACAO, x, 0, z, 0, { camisa: c }); AUTO.push(t => { q.position.x = x + Math.sin(t * .4 + i * 2) * 2.2; q.rotation.y = Math.cos(t * .4 + i * 2) > 0 ? PI / 2 : -PI / 2; q.r.anda(t + i, 1); }); });
  const op = pc('personagem', ESTACAO, -26, H_T + .12, ZB + .15, 0, { camisa: 0x2f7fd6 }); AUTO.push(t => { op.visible = t > c3.e; op.r.anda(0, 0); op.r.respira(t); }); const lab = pc('personagem', ESTACAO, 18, 0, 3.4, -.4, { capacete: 0xffffff, camisa: 0xf4f4f2, camisa2: 0xdedbd2 }); AUTO.push(t => { lab.visible = t > c5.a; lab.r.anda(0, 0); lab.r.respira(t); lab.r.bd.j.rotation.x = -1.3; lab.r.bd.k.rotation.x = -.4; }); }

// cidade: casas em corte, uma atrás da outra ----------------------------------------------------------------------
const CIDADE = new THREE.Group(); add(CIDADE);
const TQ_CASAS = [100, 116, 132, 148, 164, 180], CASAS = [], JAN = [];
const casa = (x, c, tc, ic) => { const g = new THREE.Group(); g.position.set(x, 0, ZF); CIDADE.add(g); const w = 11, d = 6.6, H = 3.1; B(g, w, .16, d, 0xd6b48a, 0, .08, -d / 2, .01); for (let i = 0; i < 6; i++) B(g, w, .01, .03, 0xb89468, 0, .165, -i * 1.1 - .3, .001); B(g, w, H, .2, c, 0, H / 2, -d, .01); [-1, 1].forEach(s => { B(g, .2, H, d, c, s * w / 2, H / 2, -d / 2, .01); B(g, .21, H, .02, CORTE, s * w / 2, H / 2, .01, .005); }); B(g, w + .4, .16, d + .4, 0xf4f4f2, 0, H + .08, -d / 2, .01);
  B(g, w, .4, .06, 0xf4f4f2, 0, .95, -d + .13, .01); B(g, 11, .9, .05, ic, 0, 1.75 + .05, -d + .12, .01);
  const fo = new THREE.Shape(); fo.moveTo(-w / 2 - .5, 0); fo.lineTo(w / 2 + .5, 0); fo.lineTo(0, 1.9); fo.closePath(); const to = add(sh(new THREE.Mesh(new THREE.ExtrudeGeometry(fo, { depth: d + .6, bevelEnabled: false }), mat(tc, { flatShading: true }))), g); to.position.set(0, H + .16, -d - .3);
  // janela de trás
  const ja = add(new THREE.Mesh(new THREE.PlaneGeometry(2, 1.2), new THREE.MeshBasicMaterial({ color: 0xbfe7f6, toneMapped: false })), g); ja.position.set(-.3, 1.95, -d + .13); B(g, 2.2, .1, .1, 0xf4f4f2, -.3, 1.32, -d + .15, .01); B(g, 2.2, .1, .1, 0xf4f4f2, -.3, 2.58, -d + .15, .01);[-1.35, -.3, .75].forEach(q => B(g, .08, 1.3, .1, 0xf4f4f2, q, 1.95, -d + .15, .01)); JAN.push(ja.material);
  // pia
  const zp = -d + .52; B(g, 3.4, .86, .66, 0xf4f4f2, -.3, .59, zp, .02); B(g, 3.5, .06, .72, 0x3a3f47, -.3, 1.05, zp, .01); B(g, .9, .03, .42, 0x8a929a, -.3, 1.075, zp + .05, .005, MET); for (let i = 0; i < 2; i++) { B(g, 1.55, .72, .02, 0xdedbd2, -1.15 + i * 1.7, .6, zp + .34, .01); B(g, .22, .03, .03, 0x59626c, -1.1 + i * 1.7, .86, zp + .36, .005); }
  tubo(g, curva([[-.3, 1.06, zp - .24], [-.3, 1.42, zp - .22], [-.3, 1.5, zp - .06], [-.3, 1.36, zp + .08]]), .022, mat(0xe6eaee, { roughness: .35, metalness: .15 }), 16); B(g, .14, .04, .05, 0xc9ced4, -.3, 1.2, zp - .2, .01, MET);
  B(g, .9, 1.9, .75, 0xeef0f2, 2.9, 1.11, -d + .5, .06); B(g, .88, .02, .02, 0x9aa1a8, 2.9, 1.5, -d + .89, .005); B(g, .05, .5, .05, 0x8a929a, 2.55, 1.75, -d + .9, .01, MET); B(g, 1.4, .05, .8, 0xa8703f, -3.6, .85, -2.4, .02); [[-4.2, -2.1], [-3, -2.1], [-4.2, -2.75], [-3, -2.75]].forEach(([a, b]) => B(g, .06, .7, .06, 0x7a4a26, a, .5, b, .01));
  const jato = add(cil(.024, .024, 1, new THREE.MeshBasicMaterial({ color: 0x9a6a30, transparent: true, opacity: .92 }), 10), g), go = -.3; jato.position.set(go, 1.2, zp + .08); const pe = pc('personagem', g, -1.3, .16, zp + .95, 2.35, { capacete: false, cinto: false, camisa: [0xe8683f, 0x2f7fd6, 0x8a5ad6, 0x2fbf8f, 0xf2b01e, 0xe0577a][CASAS.length % 6], camisa2: 0x555555 });
  const q = { g, x, jato, pe, zp }; CASAS.push(q); return q; };
const CC = [0xf2d9a6, 0xbfe0ef, 0xf2b8a6, 0xcfe6c4, 0xe8d0f0, 0xf6e7b0], TC = [0xc2502f, 0x8c5a3c, 0xb5482f, 0x5e6a78], IC = [0x7fc4c0, 0xe8b45a, 0xd98a7a, 0x8fb8e0, 0xa6d08a, 0xe6a8c8];
TQ_CASAS.forEach((x, i) => casa(x, CC[i], TC[i % 4], IC[i]));
// ruas: a da frente corre atrás das casas em corte; a segunda fileira olha para ela
const AS = 0x2a2d34, CR = 0xd9d6cc; const planoC = (x, z, w, d, c, y) => plano(x, z, w, d, c, y);
planoC(200, -8, 240, 9, AS, .03); planoC(200, -2.9, 240, 1.6, CR, .06); planoC(200, -13.2, 240, 1.6, CR, .06); for (let i = 0; i < 40; i++) B(CIDADE, 2.2, .02, .16, 0xf2d24a, 90 + i * 6, .05, -8, .005);
for (let m = 0; m < 7; m++) planoC(92 + m * 32, -80, 7, 150, AS, .025); for (let k = 1; k < 4; k++) planoC(200, -8 - k * 44, 240, 7, AS, .025);
[0, 1, 2, 3, 4, 5, 6].forEach(m => { const x = 92 + m * 32; B(CIDADE, 6.8, .1, .02, AS, x, -.04, ZF + .04, .005); });
const CFX = ['casa_simples', 'casa_colonial', 'casa_moderna', 'casa_popular', 'casa_chale', 'casa_vila', 'casa_sitio'];
for (let i = 0; i < 13; i++) { const x = 100 + i * 12.6; if ((x - 92) % 32 < 7 || (x - 92) % 32 > 28) continue; const c = pc(CFX[i % 7], CIDADE, x, 0, -21, 0); }
{ const n = 340, I = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), mat(0xffffff, { roughness: .8 }), n * 2); I.castShadow = I.receiveShadow = true; I.frustumCulled = false; add(I, CIDADE); let k = 0; const L = []; for (let a = 0; a < 21; a++) for (let b = 0; b < 12; b++) { const x = 98 + a * 10.2, z = -38 - b * 10.8; if ((x - 92) % 32 < 7.5 || ((-z - 8) % 44) < 7.5 || k >= n * 2 - 2) continue; const al = 3 + rnd() * (x < 130 ? 1.4 : 5), wx = 7 + rnd(), wz = 7; O.position.set(x, al / 2, z); O.rotation.set(0, 0, 0); O.scale.set(wx, al, wz); O.updateMatrix(); I.setMatrixAt(k, O.matrix); I.setColorAt(k, C.set(CC[k % 6])); k++; O.position.set(x, al + .3, z); O.scale.set(wx + .5, .6, wz + .5); O.updateMatrix(); I.setMatrixAt(k, O.matrix); I.setColorAt(k, C.set(TC[k % 4])); k++; L.push([x, z, al]); } I.count = k; CIDADE.userData.lotes = L; }
for (let i = 0; i < 26; i++) { const x = 95 + i * 7.6, z = i % 2 ? -14.8 : -1.8; if (z > 0) continue; const a = add(arvore(rnd, 1.8 + rnd(), false), CIDADE); a.position.set(x, 0, z); } for (let i = 0; i < 6; i++) if (i !== 1) pc(['veiculo_sedan', 'veiculo_hatch', 'veiculo_suv', 'veiculo_taxi'][i % 4], CIDADE, 112 + i * 22, .04, i % 2 ? -5.4 : -10.6, PI / 2, undefined);
for (let i = 0; i < 7; i++) pc('rua_poste_luz', CIDADE, 98 + i * 20, 0, -14, 0);
// gente doente na abertura e ambulância
const tCid = tk('cidade', 0) - .05, DOE = new THREE.Group(); add(DOE); mostra(DOE, tCid - .1, F(1));
{ const am = pc('veiculo_ambulancia', DOE, 152, .04, -9.6, PI / 2 + .25); const gi = add(new THREE.Mesh(new THREE.SphereGeometry(.16, 12, 8), new THREE.MeshBasicMaterial({ color: 0xff3030, toneMapped: false })), DOE); gi.position.set(151.4, 2.72, -9.6); AUTO.push(t => { gi.material.color.setHex(Math.floor(t * 7) % 2 ? 0xff3030 : 0x3060ff); });
  const P_ = [[131, -5.4, .5, 0xe8683f], [134, -7.2, -.3, 0x2f7fd6], [136.4, -5, .3, 0x8a5ad6], [138, -9.4, -.2, 0x2fbf8f], [133, -10.6, .2, 0xf2b01e], [129.6, -8.4, .4, 0xe0577a], [140.4, -6.6, -.4, 0x45b0a0]]; P_.forEach(([x, z, ry, c], i) => { const q = pc('personagem', DOE, x, 0, z, ry, { capacete: false, cinto: false, camisa: c, camisa2: 0x555555 }); AUTO.push(t => { q.r.anda(0, 0); q.r.bd.j.rotation.x = -1.1; q.r.be.j.rotation.x = -1.1; q.r.bd.j.rotation.z = .4; q.r.be.j.rotation.z = -.4; q.r.cab.rotation.x = .5 + Math.sin(t * 3 + i) * .08; q.rotation.x = .38 + Math.sin(t * 2.4 + i) * .05; }); }); }

// rede: cano embaixo das ruas -------------------------------------------------------------------------------------
const c7 = CI[7], c8 = CI[8], tCn = tk('canos', 7), REDE = curva([[33, -1.4, ZF + .14], [80, -1.4, ZF + .14], [130, -1.4, ZF + .14], [186, -1.4, ZF + .14]]);
const AZ = 0x2f7fd6, SAI_m = tubo(MUNDO, SAI, .28, AZ, 40), RE_m = tubo(MUNDO, REDE, .33, AZ, 240); AUTO.push(t => { SAI_m.visible = t > F(7); }); const dRE = 2.1; cresce(RE_m, tCn - .2, dRE); pulsos(MUNDO, REDE, 44, 0x8fe6ff, t => t > tCn + dRE - .6, .05, .2);
// vala aberta e fechada em frente à cidade, com a escavadeira
const VALA = add(new THREE.Mesh(new THREE.BoxGeometry(1, 2, .1), mat(0x2c1a0d)), MUNDO); VALA.position.set(0, -1, ZF + .09); const ESC = pc('obra_escavadeira', MUNDO, 84, 0, ZF - 3, PI / 2); const BR = ESC.braco ?? new THREE.Group(); ESC.visible = false;
{ const op = pc('personagem', MUNDO, 79, h(79, ZF - 1), ZF - 1.2, .5, { camisa: 0xf28a2a }); mostra(op, F(7) - .1, nomeF(7)); AUTO.push(t => { op.r.anda(0, 0); op.r.respira(t); }); } function nomeF(i) { return fim(i) + .1; }
AUTO.push(t => { const k = ease(rev(t, tCn - .9, tCn + 1.4)), on = t > F(7) && t < fim(7) + .2; ESC.visible = on; ESC.position.x = 74 + k * 26; BR.rotation.x = Math.sin(t * 5) * .3; const fe = ease(rev(t, tCn + 1.1, tCn + 2.4)), x0 = 72 + fe * 40, x1 = 72 + k * 40; VALA.visible = on && x1 - x0 > .1; VALA.scale.x = Math.max(x1 - x0, .01); VALA.position.x = (x0 + x1) / 2; });
const RAM = CASAS.map((q, i) => { const xs = q.x + .9, zb = ZF - 6.1, cv = curva([[xs, -1.4, ZF + .14], [xs, -.3, ZF + .14], [xs, .12, ZF - .4], [xs, .19, ZF - 5.4], [xs, .4, zb + .1], [xs, 1, zb + .05]]), m = tubo(MUNDO, cv, .055, 0x4aa8ff, 50), t0 = tCn + .1 + (q.x - 100) / 86 * dRE; cresce(m, t0, .55); pulsos(MUNDO, cv, 7, 0x8fe6ff, t => t > t0 + .5, .4, .06); q.t0 = t0 + .5; return m; });

// reservatório no alto do morro ---------------------------------------------------------------------------------
const RES = new THREE.Group(); RES.position.set(54, TOPO_M, ZF); add(RES); const tRes = c8.e, R_ = 8.6, HR = 7;
{ const m_ = new THREE.MeshStandardMaterial({ color: 0xe8e4da, roughness: .8, side: THREE.DoubleSide }); const sh_ = add(sh(new THREE.Mesh(new THREE.CylinderGeometry(R_, R_, HR, 56, 1, true, PI / 2, PI), m_)), RES); sh_.position.y = HR / 2; const ch = add(new THREE.Mesh(new THREE.CircleGeometry(R_, 56, PI, PI), mat(CONC2)), RES); ch.rotation.x = -PI / 2; ch.position.y = .06; ch.receiveShadow = true;
  const tet = add(sh(new THREE.Mesh(new THREE.ConeGeometry(R_ + .5, 1.6, 56, 1, true, PI / 2, PI), new THREE.MeshStandardMaterial({ color: 0x2f7fd6, side: THREE.DoubleSide }))), RES); tet.position.y = HR + .8; B(RES, 2 * R_ + .9, .16, .1, CORTE, 0, .05, .03, .01);[-1, 1].forEach(s => B(RES, .24, HR, .06, CORTE, s * R_, HR / 2, .02, .01)); for (let i = 0; i < 4; i++) { const a = (i / 3 - .5) * 2.4, r = add(new THREE.Mesh(new THREE.TorusGeometry(R_ + .04, .05, 8, 56, PI), mat(0x59626c, MET)), RES); r.rotation.x = PI / 2; r.position.y = 1.2 + i * 1.6; r.rotation.z = PI; } const es = B(RES, .6, HR + .4, .1, 0xffc21a, -5, HR / 2, -7.2, .01); pc('personagem', RES, 3, .1, -3, -.3, { camisa: 0x2f7fd6 }); }
sobe(RES, tRes - .05, .9);
const AR_g = new THREE.Group(); RES.add(AR_g); const ARf = add(new THREE.Mesh(new THREE.PlaneGeometry(2 * R_ - .3, 1), new THREE.MeshBasicMaterial({ color: 0x2f9df0, transparent: true, opacity: .84, toneMapped: false })), AR_g); ARf.position.z = .07; const ARt = add(new THREE.Mesh(new THREE.CircleGeometry(R_ - .15, 48, PI, PI), new THREE.MeshBasicMaterial({ color: 0x57baf6, toneMapped: false, transparent: true, opacity: .92 })), AR_g); ARt.rotation.x = -PI / 2; const ARl = add(new THREE.Mesh(new THREE.PlaneGeometry(2 * R_ - .3, .07), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: .6, toneMapped: false })), AR_g); ARl.position.z = .09;
const tTan = tk('tanque', 8), tDes = tk('desce', 8); AUTO.push(t => { const a = .3 + ease(rev(t, tRes + .7, tDes - .1)) * (HR - 1.4) - .4 * ease(rev(t, tDes + .4, fim(8) + 1)); AR_g.visible = t > tRes + .6; ARf.scale.y = a; ARf.position.y = a / 2 + .1; ARt.position.y = ARl.position.y = a + .1; });
const SUB = curva([[54, -1.4, ZF + .14], [54, 7, ZF + .14], [54, TOPO_M + .2, ZF + .14]]), SUB_m = tubo(MUNDO, SUB, .3, AZ, 60); cresce(SUB_m, tRes + .1, .8); const DESC = curva([[54, TOPO_M + .2, ZF + .14], [54, 7, ZF + .14], [54, -1.4, ZF + .14]]); pulsos(MUNDO, SUB, 12, 0x8fe6ff, t => t > tRes + .7 && t < tDes, .7, .2); pulsos(MUNDO, DESC, 14, 0xd8f8ff, t => t > tDes - .1, .9, .22);

// torneiras: marrom, depois limpa; de manhã a água falha -----------------------------------------------------------
const tAbre = tk('torneira', 8), tFalta = tk('falta', 8), tBar = tk('barrenta', 0) - .3, tIni = tk('água', 0) - .1;
AUTO.push(t => { CASAS.forEach((q, i) => { const j = q.jato, ab = i === 0 ? (t < F(1)) : false, ab2 = t > F(8) + .2 + Math.max(i - 1, 0) * ((tFalta - F(8) - .15) / 5) && t < F(9) - .1, ligado = (t >= q.t0 && t < tAbre - .3 && i < 1), rece = t > tDes + .4; const on = ab || ligado || ab2 || (i === 0 && t > F(9) - .05 && t < T_USO + .1); j.visible = on; if (!on) { poseP(q, t, false); return; } let r = 1; if (ab2 && !ab) r = rece ? ease(rev(t, tDes + .4, tDes + 1)) : 1 - .85 * ease(rev(t, tFalta - .1, tFalta + .5)); const pinga = r < .25, gr_ = Math.max(r, .4) * (t > F(1) && t < F(9) - .1 ? 1.5 : 1.1); j.scale.set(gr_, pinga ? (.14 + Math.sin(t * 14 + i) * .05) : .47, gr_); j.position.y = pinga ? 1.34 - (t * 3 % 1) * .24 : 1.3 - .235; j.material.color.setHex(t < F(1) ? 0x8d6332 : 0x3fb8ff); poseP(q, t, true); }); });
function poseP(q, t, on) { const r = q.pe.r; r.anda(0, 0); r.respira(t); if (on && t < F(1)) { const n = t - (tIni + .3), re = ease(n / .4); q.pe.position.z = q.zp + .95 + re * .35; r.be.j.rotation.x = -1.6 * re; r.bd.j.rotation.x = -1.6 * re; r.cab.rotation.x = -.15 * re; } else { q.pe.position.z = q.zp + .95; r.bd.j.rotation.x = on ? -1.1 : 0; r.bd.k.rotation.x = on ? -.2 : 0; } }
const T_FIM = D.total + 2;
// copo debaixo da torneira
const COPO = new THREE.Group(); COPO.position.set(100 - .3, 1.105, ZF - 6.6 + .6); add(COPO); { add(cil(.058, .048, .17, 0xdff3fa, 20, { transparent: true, opacity: .3, roughness: .08, depthWrite: false }), COPO).position.y = .085; const lk = add(new THREE.PointLight(0xfff0d0, 0, 9), COPO); lk.position.set(.7, 1.2, 1.4); AUTO.push(t => { lk.intensity = 14 * noiteK(t); }); }
const LIQ = add(cil(.054, .044, .14, new THREE.MeshBasicMaterial({ color: 0x8d6332, toneMapped: false, transparent: true, opacity: .9 }), 20), COPO); AUTO.push(t => { const k = t < F(1) ? rev(t, 1.6, 3.5) : ease(rev(t, F(9) + .05, F(9) + 1.2)) ; LIQ.scale.y = Math.max(k, .02); LIQ.position.y = .022 + .07 * k; LIQ.visible = k > .02; LIQ.material.color.setHex(t < F(1) ? 0x8d6332 : 0xbfe9ff); LIQ.material.opacity = t < F(1) ? .95 : .78; });

// noite: janelas e veias de água acesas ----------------------------------------------------------------------------
const T_NOITE = F(9) + 1.2, noiteK = t => ease(rev(t, T_NOITE, T_NOITE + 1.6));
const LO = CIDADE.userData.lotes, LJ = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshBasicMaterial({ color: 0xffd97a, toneMapped: false }), LO.length * 6); LJ.frustumCulled = false; add(LJ, CIDADE); { let k = 0; LO.forEach(([x, z, al]) => { for (let i = 0; i < 3; i++) { O.position.set(x - 2.2 + i * 2.2, al * .55, z + 3.53); O.rotation.set(0, 0, 0); O.scale.set(1.6, Math.max(al * .4, 1.3), .05); O.updateMatrix(); LJ.setMatrixAt(k++, O.matrix); O.position.set(x + 4.04, al * .55, z - 2.2 + i * 2.2); O.scale.set(.05, Math.max(al * .4, 1.3), 1.6); O.updateMatrix(); LJ.setMatrixAt(k++, O.matrix); } }); LJ.count = k; }
const NVE = 150, VE = []; { for (let k = 0; k < 4; k++) for (let i = 0; i < 40; i++) VE.push({ x: 88 + i * 6, z: -8 - k * 44, l: 6.2, rot: 0 }); for (let m = 0; m < 7; m++) for (let i = 0; i < 26; i++) VE.push({ x: 92 + m * 32, z: -8 - i * 6, l: 6.2, rot: PI / 2 }); }
const VEI = new THREE.InstancedMesh(new THREE.BoxGeometry(1, .3, 1.5), new THREE.MeshBasicMaterial({ color: 0x4fe6ff, toneMapped: false }), VE.length); VEI.frustumCulled = false; add(VEI, CIDADE);
{ const q = add(new THREE.PointLight(0x7fd4ff, 0, 60), RES); q.position.set(0, 4, 2); AUTO.push(t => { q.intensity = 900 * noiteK(t); VEI.visible = LJ.visible = t > T_NOITE + .1; if (!VEI.visible) return; const fr = (t - T_NOITE - .1) / 1.7; let vis = 0; VE.forEach((v, i) => { const d = Math.hypot(v.x - 88, v.z + 8) / 190, k = clamp((fr - d) / .12); O.position.set(v.x, .14, v.z); O.rotation.set(0, v.rot, 0); O.scale.set(v.l * k + .001, 1, 1); O.updateMatrix(); VEI.setMatrixAt(i, O.matrix); }); VEI.instanceMatrix.needsUpdate = true; LJ.count = Math.floor(LO.length * 6 * clamp(fr * 1.1)); }); }
const POL = add(new THREE.PointLight(0xffe2a8, 0, 34), ESTACAO); POL.position.set(-4, 12, 8); AUTO.push(t => { POL.intensity = 1600 * noiteK(t); });

// cor da água por etapa -------------------------------------------------------------------------------------------
const tL = t => clamp(t); const { bruta, turva, leve, clara, limpa } = CORES;
AUTO.push(t => {
  // tanque de mistura
  A1.gr.visible = t > F(2) + .2; A1.nivel(ease(rev(t, F(2) + .2, F(2) + 1.3))); const kG = ease(rev(t, tGr, tGr + 1.4)); A1.cor(x => lerpH(bruta, 0xa27c44, kG));
  const f3 = c3.e + .1; A2.nivel(ease(rev(t, f3, f3 + 1))); A2.gr.visible = t > f3; A2.cor(x => lerpH(0xa27c44, 0xb09a68, ease(x))); if (t > tEf) A2.cor(x => lerpH(0xa27c44, 0xb09a68, ease(x)));
  const f4 = c4.e + .1, k4 = ease(rev(t, tEf - .2, tEf + 2.6)); A3.nivel(ease(rev(t, f4, f4 + 1))); A3.gr.visible = t > f4; A3.cor(x => lerpH(0xb09a68, lerpH(0xb09a68, 0x9fd6e4, ease(x * 1.5 - .1)), k4));
  const f5 = c5.e + .05; A4.nivel(ease(rev(t, f5, f5 + .8))); A4.gr.visible = t > f5; A4.cor(x => 0xa6cfd4);
  A5.nivel(ease(rev(t, c6.a + .1, c6.a + .9))); A5.gr.visible = t > c6.a + .1; const kC = ease(rev(t, tMo - .2, tMo + .8)); A5.cor(x => lerpH(0x8ccfdf, limpa, kC));
});

// céu, noite, sol acompanha a câmera, clarão ------------------------------------------------------------------------
const BG = new THREE.Color(), DIA = new THREE.Color(CEU), NO = new THREE.Color('#0a1028'), CH_M = MUNDO.userData.chao.material;
AUTO.push(t => { const n = noiteK(t); if (n > 0) { BG.copy(DIA).lerp(NO, n); scene.background = BG; } else scene.background = fundo; sol.intensity = 2.3 - n * 2.16; hemi.forEach(q => { q.intensity = 1.05 - n * .8; }); scene.environmentIntensity = .3 - n * .16; scene.fog.color.setHex(n > .5 ? 0x121a36 : 0xcfe6f2); CH_M.color.setRGB(1 - n * .72, 1 - n * .68, 1 - n * .5); AG.forEach(m => m.color.setScalar(1 - n * .35));
  const fx = cam.position.x * .5 + (cam.position.x + cam.getWorldDirection(new THREE.Vector3()).x * 22) * .5; sol.position.set(fx + 42, 74, 40); sol.target.position.set(fx, 0, -8); sol.target.updateMatrixWorld();
  NUV.forEach((g, i) => { g.position.x += 0; }); JAN.forEach(m => m.color.setHex(n > .5 ? 0x1b2a54 : 0xbfe7f6));
  let fl = 0; for (let i = 1; i < N - 1; i++) { const d = t - CI[i].n; if (d > 0 && d < .5) fl = Math.max(fl, .42 * (1 - d / .5)); } flash.style.opacity = fl; });

// câmera ------------------------------------------------------------------------------------------------------------
const K = [], P = (t, p, l, f = 38) => K.push({ t, p, l, f }), cut = (t, p, l, f) => { const a = K[K.length - 1]; if (a) P(t - .02, a.p, a.l, a.f); P(t + .02, p, l, f); };
const KX = 99.7, KZ = ZF - 6;
P(0, [-49, 2.6, 14], [-52, -.3, 1.8]); P(tIni - .1, [-47, 3, 15.5], [-50.5, -.2, 1]);
cut(tIni, [KX + .8, 1.6, ZF - 3.1], [KX, 1.22, KZ + .4], 40); P(tCid - .1, [KX + .55, 1.5, ZF - 4], [KX, 1.2, KZ + .4], 40);
cut(tCid, [135, 6.6, .4], [135, .5, -9.5], 54); P(fim(0), [135, 6, .2], [135, .5, -9], 54);
cut(F(1), [-62, 3, 11], [-52, -.6, -8]); P(tG - .1, [-60, 3.2, 6], [-48.6, -.2, -5]); P(tBo - .2, [-58.5, 3.4, 2], [-47.6, .4, -2.4]);
cut(tBo, [-34, 5, 19], [-40, 2.2, -2]); P(c1.n, [-31, 6, 17], [-38, 3, -2]); P(fim(1), [-30, 6.2, 16], [-37, 3.2, -2]);
cut(F(2), [-36.5, 4.4, 19], [-30.5, 3, -3]); P(tPr, [-33.5, 4.6, 16.5], [-30.5, 3.2, -3]); P(tGr + .3, [-31.4, 3.2, 14], [-30.6, 2.5, -2]); P(fim(2), [-30.5, 3, 13], [-30.6, 2.5, -2]);
cut(F(3), [-30.6, 2.6, 9], [-30.6, 2.4, -1]); P(c3.e - .1, [-28.4, 2.8, 10], [-29.6, 2.5, -1]);
cut(c3.e, [-29, 4.6, 24], [-18.5, 2.3, -3]); P(c3.n, [-24, 4.4, 23], [-18.5, 2.1, -3]); P(fim(3), [-22.5, 4.4, 22], [-18, 2.1, -3]);
cut(F(4), [-16.2, 3, 12], [-15.8, 2.5, -1]); P(c4.e - .1, [-14, 3, 13], [-14.6, 2.5, -1]);
cut(c4.e, [-17, 5, 20], [-4, 2.2, -3]); P(tEf, [-11, 4.6, 22], [-2, 2.1, -3]); P(c4.n, [-2, 3.2, 18], [1.6, 2.2, -2]); P(fim(4), [-1, 3.2, 17.4], [1.6, 2.2, -2]);
cut(F(5), [2.4, 3.2, 12.5], [3, 2.6, -1]); P(c5.e - .1, [3.6, 3.2, 11.5], [3.6, 2.6, -1]);
cut(c5.e, [12.5, 6.2, 27], [12.5, 4.4, -3]); P(tCa + .4, [12.5, 5, 24], [12.5, 3.4, -2]); P(c5.n, [12.5, 4, 20], [12.5, 2.5, -2]); P(fim(5), [12.5, 3.8, 19], [12.5, 2.5, -2]);
cut(F(6), [21, 5.2, 24], [23, 3.4, -2]); P(c6.e - .1, [22.5, 4.6, 21], [23, 3.2, -2]); P(tMo, [23.4, 6, 22], [23, 4.2, -2]); P(fim(6), [23.2, 5.6, 19], [23, 3.6, -2]);
cut(F(7), [84, 5, 40], [108, 2, 0]); P(tCn - .9, [76, 3.6, 28], [88, 1, 6]); P(tCn + .3, [90, 3, 25], [98, .6, 6]); P(tCn + 1.6, [108, 3, 26], [114, .8, 6]); P(fim(7), [120, 3, 27], [122, 1, 4]);
{ const pl = i => { const x = TQ_CASAS[i]; return [[x + .2, 1.9, ZF + 3.4], [x - .8, 1.25, KZ + .3]]; }, d = (tFalta - F(8) - .15) / 5; for (let i = 0; i < 5; i++) { const [p, l] = pl(i + 1), a = F(8) + i * d; if (i === 0) cut(a, p, l); else cut(a, p, l); } const [p, l] = pl(5); P(c8.e - .1, [p[0], 1.65, p[2] - .7], l); }
cut(c8.e, [54, 25, 60], [54, 20, 8]); P(tDes - .2, [54, 24, 56], [54, 19.6, 8]); P(tDes + .2, [50, 20, 66], [56, 11, 6]); P(c8.n, [50, 20, 74], [58, 10, 6]); P(fim(8), [50, 20, 75], [58, 10, 6]);
cut(F(9), [KX + .9, 1.52, ZF - 4.1], [KX, 1.2, KZ + .1], 36); P(T_NOITE - .1, [KX + .7, 1.45, ZF - 4.6], [KX, 1.2, KZ + .1], 36);
cut(T_NOITE, [236, 34, -34], [150, 2, -38], 44); P(T_USO - .1, [210, 54, -38], [86, 2, -34], 44);
cut(T_USO, [KX + .55, 1.32, ZF - 5.05], [KX, 1.2, ZF - 6], 34); P(D.total + 1, [KX + .34, 1.28, ZF - 5.3], [KX, 1.17, ZF - 6], 34);
K.sort((a, b) => a.t - b.t); for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01;

// rótulos e sons ---------------------------------------------------------------------------------------------------
const NOM = ['', 'CAPTAÇÃO', 'COAGULAÇÃO', 'FLOCULAÇÃO', 'DECANTAÇÃO', 'FILTRAÇÃO', 'DESINFECÇÃO', 'REDE', 'RESERVATÓRIO'];
for (let i = 1; i < N - 1; i++) { const a = CI[i].n, e = rotulo(NOM[i], [540, 400], a, fim(i), 'grande'); e.style.fontSize = NOM[i].length > 10 ? '76px' : '88px'; e.style.transform += ' rotate(-3deg)'; som(a, 'ding'); som(a, 'whoosh'); }
const ruim = (x, a, b) => { rotulo(x, [540, 400], a, b, 'grande').style.cssText += ';font-size:64px;color:#ff5a4f'; };
ruim('ÁGUA SUJA', .2, tCid - .1); ruim('CIDADE DOENTE', tCid + .2, fim(0)); ruim('LIXO NO RIO', F(1) + .2, tG - .1); ruim('ÁGUA BARRENTA', F(2) + .3, c2.e); ruim('GRÃOS LEVES', F(3) + .2, c3.e); ruim('FLOCOS SOLTOS', F(4) + .2, c4.e); ruim('SUJEIRA MIÚDA', F(5) + .2, c5.e); ruim('GERMES', F(6) + .3, c6.e); ruim('FALTOU ÁGUA', tFalta, c8.e);
[['AREIA', tAr + .1, tCa], ['CARVÃO', tCa + .1, c5.n]].forEach(([x, a, b]) => { rotulo(x, [540, 400], a, b, 'grande').style.cssText += ';font-size:64px;color:#fff'; });
rotulo('ÁGUA LIMPA NA CIDADE!', [540, 400], T_NOITE + .2, T_USO - .1, 'grande').style.fontSize = '64px'; const vm = rotulo('VERDADE OU MENTIRA?', [540, 400], tk('Verdade', 9, .85), D.total + 1, 'grande'); vm.style.fontSize = '68px';
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); for (let q = 0; q < fim(0); q += 1.1) som(q, 'chuva'); for (let q = tBo + .3; q < fim(1); q += 1.2) som(q, 'motor'); for (let q = c3.e; q < c3.n; q += 1.2) som(q, 'motor'); som(c4.e, 'concreto'); som(tAr, 'concreto'); som(tCa, 'concreto'); som(c5.e, 'concreto'); som(tCn - .9, 'motor'); som(tCn + .3, 'motor'); som(tCn + 1.5, 'motor'); som(tPr + .1, 'gota'); som(tPr + .5, 'gota'); som(tCl + .5, 'gota'); som(tCl + .9, 'gota'); som(F(9), 'gota'); som(F(9) + .3, 'gota'); som(T_NOITE, 'riser'); som(T_NOITE + 1.5, 'impact'); for (let i = 0; i < 6; i++) som(tAbre + i * .12, 'toc'); som(tRes + .1, 'concreto');
window.CAPA_T = T_USO - .4;
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); AUTO.forEach(f => f(t)); });
