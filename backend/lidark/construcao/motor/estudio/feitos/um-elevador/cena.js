// Um elevador. O prédio aparece cortado ao meio, como uma maquete: tudo acontece dentro dele, do fundo do poço à casa de máquinas.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, tex, arvore, camTo, iniciar, som, rotulo, fala, D } = K3;
const rnd = prng(47), F = fala, fim = i => F(i) + D.falas[i].dur, N = D.falas.length, AUTO = [], O = new THREE.Object3D(), C = new THREE.Color(), PI = Math.PI;
const nk = x => String(x).toLowerCase().normalize('NFD').replace(/[^a-z0-9]/g, '');
const tk = (w, i, f = .4) => { const k = nk(w), q = D.falas[i].words?.find(p => nk(p.w).startsWith(k)); return q ? q.start : F(i) + D.falas[i].dur * f; };
const nomeT = i => { const q = [...(D.falas[i].words ?? [])].reverse().find(p => /^(essa|esse|essas|esses)$/.test(nk(p.w))); return q ? q.start : fim(i) - 1.2; };
const u = D.falas[N - 1], nP = u.texto.split(/[!.]/)[0].trim().split(/\s+/).length, T_USO = (u.words[nP - 1]?.end ?? fim(N - 1)) + .15;
const rev = (t, a, b) => clamp((t - a) / (b - a));
const CI = {}; for (let i = 1; i < N - 1; i++) CI[i] = { a: F(i), e: tk('Então', i, .4), n: nomeT(i) };

// medidas do prédio, em metros
const PD = 3, ANDARES = 10, TOPO = 31, FOSSO = -2.7, POCO = { x0: -3.6, x1: .3, z: -3.2 }, X_CAB = -1, X_CP = -2.8, Z_EL = -1.6, XE = -10.2, XD = 9.6, FUNDO = -10;
const yA = i => i * PD;

// céu, sol e névoa --------------------------------------------------------------------------------------------
const CEU = '#3f8fe0'; ceu(CEU, '#d6eefa'); const fundo = scene.background; scene.fog = new THREE.Fog(0xcfe6f2, 75, 330); const sol = luzes(0xfff2de, 0xd8ecff, 0x8fb070, 1.9, 52); sol.position.set(30, 62, 46); scene.environmentIntensity = .3; const hemi = []; scene.traverse(o => { if (o.isHemisphereLight) { hemi.push(o); o.intensity = .95; } });
const flash = document.createElement('div'); flash.style.cssText = 'position:absolute;inset:0;background:#fff8d8;opacity:0'; document.getElementById('hud').prepend(flash);
const B = (g, w, h, d, c, x, y, z, r = .02, o) => { const m = add(box(w, h, d, c, r, o), g); m.position.set(x, y, z); return m; };
const MET = { roughness: .34, metalness: .55 }, VID = { roughness: .12, metalness: .4 };
const pc = (n, g, x, y, z, ry = 0, o, e = 1) => { const q = PC.novo(n, o); q.position.set(x, y, z); q.rotation.y = ry; if (e !== 1) q.scale.multiplyScalar(e); g.add(q); return q; };
const mostra = (o, a, b = 1e9) => AUTO.push(t => { o.visible = t >= a && t < b; });
const poe = (o, t0, d = .3) => { const s = o.scale.clone(); o.visible = false; AUTO.push(t => { o.visible = t >= t0; if (o.visible) o.scale.copy(s).multiplyScalar(Math.max(back((t - t0) / d), .01)); }); return o; };

// bairro: relevo, ruas e gente --------------------------------------------------------------------------------
const MUNDO = new THREE.Group(); add(MUNDO);
const GR = 0x46b254, AS = 0x2a2d34, CR = 0xd9d6cc;
const chao = add(new THREE.Mesh(new THREE.PlaneGeometry(900, 496), mat(GR, { roughness: 1 })), MUNDO); chao.rotation.x = -PI / 2; chao.position.set(0, -.04, -252); chao.receiveShadow = true;
// a fatia junto do corte deixa o fosso aberto
[[-452, POCO.x0 - .3], [POCO.x1 + .3, 452]].forEach(([a, b]) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(b - a, 4), chao.material), MUNDO); m.rotation.x = -PI / 2; m.position.set((a + b) / 2, -.04, -2); m.receiveShadow = true; });
const plano = (x, z, w, d, c, y = .01) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, d), mat(c)), MUNDO); m.rotation.x = -PI / 2; m.position.set(x, y, z); m.receiveShadow = true; return m; };
// avenida que sai do corte para o fundo, travessa e calçadas
plano(19, -150, 11, 300, AS); plano(-27, -150, 8, 300, AS); plano(0, -40, 400, 8, AS, .012); plano(0, -92, 400, 8, AS, .012);
plano(12, -150, 3, 300, CR, .05); plano(26, -150, 3, 300, CR, .05); plano(-22, -150, 2.4, 300, CR, .05); plano(-32, -150, 2.4, 300, CR, .05);
plano(0, -22, 44, 36, 0x5fae58, .02); plano(0, -7, 60, 6, 0xb9b3a5, .03);[[-30, POCO.x0 - .3], [POCO.x1 + .3, 30]].forEach(([a, b]) => plano((a + b) / 2, -2, b - a, 4, 0xb9b3a5, .03));
for (let i = 0; i < 40; i++) B(MUNDO, .18, .02, 2.4, 0xf2d24a, 19, .03, -3 - i * 7, .005);
for (let i = 0; i < 18; i++) B(MUNDO, 2.2, .02, .18, 0xf2d24a, -60 + i * 8, .03, -40, .005);
// fatia do terreno: é o mesmo chão, cortado junto com o prédio
const TERRA = 0x8d6240, TERRA2 = 0x734a2e;
const terras = [[-210, POCO.x0 - .3], [POCO.x1 + .3, 210]];
terras.forEach(([a, b]) => { B(MUNDO, b - a, 70, 80, TERRA, (a + b) / 2, -35, -40, .01); });
B(MUNDO, 6, 70 + FOSSO - 1.4, 80, TERRA, -1.65, -35 + (FOSSO - .6) / 2 - .4, -40, .01);
// camadas do solo, com o fosso livre no meio
[[-210, POCO.x0 - .3], [POCO.x1 + .3, 210]].forEach(([a, b]) => { B(MUNDO, b - a, .5, .1, 0x4a7a3a, (a + b) / 2, -.24, .04, .01); B(MUNDO, b - a, 1.2, .1, 0x5e3b28, (a + b) / 2, -1.1, .03, .01); }); B(MUNDO, 420, 2.2, .06, TERRA2, 0, -6, .03, .01);
{ const pedra = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 0), mat(0x9b8e80, { flatShading: true }), 260); pedra.frustumCulled = false; add(pedra, MUNDO); let n = 0; while (n < 260) { const x = -80 + rnd() * 160, y = -1.8 - rnd() * 34; if (x > -6 && x < 3 && y > -4.2) continue; O.position.set(x, y, .1); O.rotation.set(rnd() * 3, rnd() * 3, 0); O.scale.setScalar(.14 + rnd() * .42); O.updateMatrix(); pedra.setMatrixAt(n, O.matrix); pedra.setColorAt(n, C.set(0x9b8e80).offsetHSL(0, 0, (rnd() - .5) * .16)); n++; } }
[[-8, -2.4, .34, 0x4c6a8c], [-7.1, -2.4, .22, 0xc9794a], [7, -3.2, .42, 0x8a9198], [8.2, -3.1, .2, 0x3f8f5a]].forEach(([x, y, r, c]) => { const a = add(cil(r, r, .16, c, 26), MUNDO); a.rotation.x = PI / 2; a.position.set(x, y, .12); const b = add(cil(r * .68, r * .68, .17, 0x1a1c20, 26), MUNDO); b.rotation.x = PI / 2; b.position.set(x, y, .13); });
// morros e serra na névoa
[[-170, -300, 120, 62], [-40, -340, 150, 54], [120, -320, 170, 74], [260, -280, 130, 48], [-300, -260, 120, 56]].forEach(([x, z, r, h], i) => { const m = add(new THREE.Mesh(new THREE.ConeGeometry(r, h, 7), mat([0x4f9a70, 0x5ca680, 0x487f6b][i % 3], { flatShading: true })), MUNDO); m.position.set(x, h / 2 - 1, z); m.scale.z = .6; });
// nuvens
const NUV = []; for (let i = 0; i < 9; i++) { const g = new THREE.Group(); g.position.set(-150 + i * 42 + rnd() * 20, 60 + rnd() * 34, -200 - rnd() * 60); add(g, MUNDO); for (let k = 0; k < 5; k++) { const s = add(new THREE.Mesh(new THREE.SphereGeometry(7 + rnd() * 7, 12, 8), new THREE.MeshBasicMaterial({ color: 0xffffff, fog: false })), g); s.position.set((k - 2) * 8, rnd() * 3, 0); s.scale.y = .55; } NUV.push(g); }
// árvores do bairro: ficam em volta do prédio, nunca no corte
for (let i = 0; i < 70; i++) { const x = -130 + rnd() * 260, z = -14 - rnd() * 170; if (Math.abs(x - 19) < 9 || Math.abs(x + 27) < 7 || Math.abs(z + 40) < 7 || Math.abs(z + 92) < 7 || (Math.abs(x) < 13 && z > -20)) continue; const a = add(arvore(rnd, 2.2 + rnd() * 2.4, rnd() > .55), MUNDO); a.position.set(x, 0, z); }
// prédios vizinhos com janelas que acendem de noite
const PJ = []; const predio = (x, z, w, h, d, c) => { B(MUNDO, w, h, d, c, x, h / 2, z, .05); B(MUNDO, w + .5, .5, d + .5, 0xdedbd2, x, h + .2, z, .03); const nx = Math.floor((w - 1.4) / 2.1), ny = Math.floor((h - 2) / 3.2); for (let a = 0; a < ny; a++) for (let b = 0; b < nx; b++) PJ.push({ x: x - (nx - 1) * 1.05 + b * 2.1, y: 2.6 + a * 3.2, z: z + d / 2 + .05, on: rnd() }); };
const VIZ = [[-24.6, -7, 14, 48, 12, 0xd9b48f], [24, -9, 11, 34, 12, 0xa9c4d6], [34, -4, 8, 24, 7, 0xe3d8c0], [-37, -8, 8, 28, 10, 0xc7d2bd], [-16, -36, 15, 62, 12, 0xbfd0dd], [8, -34, 14, 44, 12, 0xe2c9b0], [42, -34, 16, 74, 13, 0x9fb4c6], [-50, -30, 16, 54, 12, 0xd6c2c9], [-74, -46, 18, 40, 13, 0xcfcab4], [66, -50, 18, 58, 13, 0xb6c4c0], [-6, -70, 18, 82, 13, 0x9dafc2], [26, -74, 18, 60, 13, 0xcab8a4], [-44, -74, 18, 72, 13, 0xb9c2cc], [80, -80, 20, 44, 13, 0xd4c8b6], [-96, -80, 20, 56, 13, 0xc2ccbc], [110, -60, 20, 36, 13, 0xccbfae], [-130, -60, 22, 44, 13, 0xbcc8d0]];
VIZ.forEach(p => predio(...p));
const VJ = new THREE.BoxGeometry(1.3, 1.5, .06), janD = new THREE.InstancedMesh(VJ, new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }), PJ.length); janD.frustumCulled = false; add(janD, MUNDO);
PJ.forEach((j, i) => { O.position.set(j.x, j.y, j.z); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); janD.setMatrixAt(i, O.matrix); janD.setColorAt(i, C.set(0x3a5468)); });
// rua viva
const CARROS = []; [['veiculo_sedan', 0xd8352f], ['veiculo_hatch', 0xffc21a], ['veiculo_suv', 0x2f7fd6], ['veiculo_taxi'], ['veiculo_onibus_urbano'], ['veiculo_picape', 0xf4f4f2], ['veiculo_hatch', 0x3fb06a], ['veiculo_sedan', 0x4c5563]].forEach(([n, c], i) => { const q = PC.novo(n, c ? { cor: c } : {}); add(q, MUNDO); const lado = i % 2; CARROS.push({ q, lado, p: i * 37, v: 9 + (i % 3) * 2.5 }); });
AUTO.push(t => CARROS.forEach(c => { const z = ((t * c.v + c.p) % 260); if (c.lado) { c.q.position.set(21.5, .02, -z - 2); c.q.rotation.y = PI; } else { c.q.position.set(16.5, .02, -258 + z); c.q.rotation.y = 0; } }));
for (let i = 0; i < 9; i++) { pc('rua_poste_luz', MUNDO, 12.6, 0, -8 - i * 24, -PI / 2); pc('rua_poste_luz', MUNDO, -22.4, 0, -6 - i * 24, PI / 2); }
pc('rua_ponto_onibus', MUNDO, 12.6, .06, -26, -PI / 2); pc('rua_banca_jornal', MUNDO, -14, .03, -14, .5); pc('rua_banco_praca', MUNDO, 12, .03, -2.4, 0); pc('rua_floreira', MUNDO, -13, .03, -2.2); pc('rua_floreira', MUNDO, 11, .03, -6); pc('rua_lixeira_poste', MUNDO, -11, .03, -6); pc('rua_hidrante', MUNDO, 10.6, .03, -1.6); pc('rua_bicicletario', MUNDO, -14, .03, -6, .3);
[['ipe', -12.4, -9], ['arvore_redonda', 13.6, -11], ['palmeira', -18, -3], ['arvore_alta', -19, -12], ['ipe', 14.4, -19], ['arvore_redonda', -11, -16]].forEach(([n, x, z]) => pc(n, MUNDO, x, 0, z, x));
const AND = []; [[-16, 0xe8683f, .9], [-13, 0x2f7fd6, 1.25], [12.2, 0xffc21a, 1.05], [13, 0x7a5fc0, .8]].forEach(([x, c, v], i) => { const q = PC.novo('personagem', { capacete: false, cinto: false, camisa: c, camisa2: c, escala: .8 }); add(q, MUNDO); AND.push({ q, x, v, p: i * 2.1 }); });
AUTO.push(t => AND.forEach(a => { const f = Math.sin(t * .26 * a.v + a.p); a.q.position.set(a.x, .04, -7 + f * 5.2); a.q.rotation.y = Math.cos(t * .26 * a.v + a.p) > 0 ? PI : 0; a.q.r.anda(t * a.v); }));

// prédio em corte ---------------------------------------------------------------------------------------------
const PR = new THREE.Group(); add(PR);
const INT = []; const interno = c => { const m = mat(c); INT.push({ m, c }); return m; };
const COR_AP = [0xeec06e, 0x6fb7dc, 0xe88a6e, 0x8fcf8a, 0xc79be0, 0xf2cf5e, 0x6fb7dc, 0xeec06e, 0xe88a6e, 0x8fcf8a], COR_HALL = interno(0x63b5ae), COR_ESC = interno(0xe9b35c), COR_MEIO = interno(0xc8b49a);
const MAT_AP = COR_AP.map(interno), LAJE = 0x5c6068, FACH = 0xc9794a;
const CASCA = (y, h) => { B(PR, .4, h, -FUNDO, FACH, XE, y + h / 2, FUNDO / 2, .01); B(PR, .4, h, -FUNDO, FACH, XD, y + h / 2, FUNDO / 2, .01); };
const LUZTETO = [];
const VISTA = new THREE.MeshBasicMaterial({ color: 0xbfe7f6 }); AUTO.push(t => { const n = ease(rev(t, F(N - 1) + .1, T_USO + .4)); VISTA.color.setHex(0xbfe7f6).lerp(C.setHex(0x101a38), n); });
const LOSAS = [];
for (let i = 0; i < ANDARES; i++) {
  const y = yA(i), h = i === ANDARES - 1 ? TOPO - y : PD;
  // laje com faixa cortada: fora do poço fica fixa, o trecho do poço cai depois
  B(PR, POCO.x0 - XE, .26, -FUNDO, LAJE, (XE + POCO.x0) / 2, y - .13, FUNDO / 2, .01); B(PR, XD - POCO.x1, .26, -FUNDO, LAJE, (XD + POCO.x1) / 2, y - .13, FUNDO / 2, .01); B(PR, POCO.x1 - POCO.x0, .26, -POCO.z + FUNDO * -1 + POCO.z * 2, LAJE, (POCO.x0 + POCO.x1) / 2, y - .13, (FUNDO + POCO.z) / 2, .01);
  const pedaco = B(PR, POCO.x1 - POCO.x0, .26, -POCO.z, LAJE, (POCO.x0 + POCO.x1) / 2, y - .13, POCO.z / 2, .01); LOSAS.push(pedaco);
  CASCA(y, h);
  // forro claro: sem ele a laje vira uma faixa preta quando a câmera olha de baixo
  if (i) { const fx = 0xf1ece0; B(PR, POCO.x0 - XE, .03, -FUNDO, fx, (XE + POCO.x0) / 2, y - .275, FUNDO / 2, .004); B(PR, XD - POCO.x1, .03, -FUNDO, fx, (XD + POCO.x1) / 2, y - .275, FUNDO / 2, .004); }
  // pisos
  B(PR, POCO.x0 - XE, .02, -FUNDO, i % 2 ? 0xc9a678 : 0xb78f62, (XE + POCO.x0) / 2, y + .012, FUNDO / 2, .002); B(PR, XD - POCO.x1, .02, -FUNDO, 0xa8a297, (XD + POCO.x1) / 2, y + .012, FUNDO / 2, .002);
  // paredes do fundo
  const pf = add(new THREE.Mesh(new THREE.BoxGeometry(POCO.x0 - XE, h, .2), MAT_AP[i]), PR); pf.position.set((XE + POCO.x0) / 2, y + h / 2, FUNDO); pf.receiveShadow = true;
  const pm = add(new THREE.Mesh(new THREE.BoxGeometry(POCO.x1 - POCO.x0, h, .2), COR_MEIO), PR); pm.position.set((POCO.x0 + POCO.x1) / 2, y + h / 2, FUNDO); pm.receiveShadow = true;
  const ph = add(new THREE.Mesh(new THREE.BoxGeometry(4.7, h, .2), COR_HALL), PR); ph.position.set(2.65, y + h / 2, -3.4); ph.receiveShadow = true;
  const pe = add(new THREE.Mesh(new THREE.BoxGeometry(4.6, h, .2), COR_ESC), PR); pe.position.set(7.3, y + h / 2, -3.4); pe.receiveShadow = true;
  // parede lateral do apartamento e janela
  const jan = add(new THREE.Mesh(new THREE.PlaneGeometry(2.4, 1.5), VISTA), PR); jan.position.set(-7.7, y + 1.65, FUNDO + .12); B(PR, 2.6, .1, .2, 0xf4f4f2, -7.7, y + .86, FUNDO + .14);
  // luz do teto
  [[-7, 3.2], [2.6, 1.5], [7.2, 1]].forEach(([x, w]) => { const l = B(PR, w, .05, .3, 0xf6f2e6, x, y + h - .05, -2.2, .01); l.castShadow = false; l.material = l.material.clone(); LUZTETO.push(l.material); });
  // móveis, cada andar arrumado de um jeito
  const tipo = i % 3;
  if (i > 0) { if (tipo === 0) { pc('sofa', PR, -7, y, -7.6, 0, { cor: [0x2f7fd6, 0xe8683f, 0x3fa45a][(i / 3 | 0) % 3] }, 1.05); pc('mesa_centro', PR, -7, y, -5.4); pc('planta_vaso', PR, -4.5, y, -8.6); } else if (tipo === 1) { pc('cama_casal', PR, -7, y, -7.8, 0, {}); pc('estante', PR, -4.6, y, -9.5); pc('poltrona', PR, -9, y, -4.4, 1); } else { pc('rack_tv', PR, -7, y, -9.4); pc('televisor', PR, -7, y + .58, -9.5, 0, { l: 1.5 }); pc('poltrona', PR, -8, y, -6, 2.6); pc('poltrona', PR, -5.6, y, -6, 3.5); pc('planta_vaso', PR, -9.3, y, -9.2); } }
  // quadro no hall com o número do andar
  const pl = add(new THREE.Mesh(new THREE.PlaneGeometry(.7, .7), new THREE.MeshBasicMaterial({ map: tex(128, 128, (c, w, h2) => { c.fillStyle = '#1e3a5f'; c.fillRect(0, 0, w, h2); c.fillStyle = '#fff'; c.font = '900 96px Segoe UI'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(i ? String(i) : 'T', w / 2, h2 / 2 + 6); }) })), PR); pl.position.set(3.4, y + 1.9, -3.28);
  if (i % 2) pc('planta_vaso', PR, 4.2, y, -2.8, 0, undefined, .7);
}
// laje da cobertura com o vão do poço livre: é por ele que os cabos passam
B(PR, POCO.x0 - XE + .2, .34, -FUNDO + .2, LAJE, (XE - .2 + POCO.x0) / 2, TOPO - .13, FUNDO / 2, .01); B(PR, XD + .2 - POCO.x1, .34, -FUNDO + .2, LAJE, (XD + .2 + POCO.x1) / 2, TOPO - .13, FUNDO / 2, .01); B(PR, POCO.x1 - POCO.x0, .34, -FUNDO + .2 + POCO.z, LAJE, (POCO.x0 + POCO.x1) / 2, TOPO - .13, (FUNDO - .2 + POCO.z) / 2, .01);
const LOSA_T = B(PR, POCO.x1 - POCO.x0, .36, -POCO.z, LAJE, (POCO.x0 + POCO.x1) / 2, TOPO - .13, POCO.z / 2 - .02, .005);
B(PR, XD - XE + .4, .8, .3, 0xd9cfb9, (XE + XD) / 2, TOPO + .5, FUNDO, .01); [XE, XD].forEach(x => B(PR, .3, .8, -FUNDO, 0xd9cfb9, x, TOPO + .5, FUNDO / 2, .01));
// fachada do fundo e térreo
B(PR, XD - XE + .4, TOPO, .2, FACH, (XE + XD) / 2, TOPO / 2, FUNDO - .2, .01);
// cobertura: caixa d'água, ar e placas
[-8, -6.2].forEach(x => { const a = add(cil(.95, .95, 1.5, 0x8fb6d0, 22), PR); a.position.set(x, TOPO + .9, -6.5); add(cil(1, 1, .1, 0x7aa0ba, 22), PR).position.set(x, TOPO + 1.7, -6.5); });
for (let i = 0; i < 4; i++) { const p = B(PR, 1.5, .06, 1, 0x1f3a66, 5 + i * 1.3 - 1, TOPO + .7, -7, .01, VID); p.rotation.x = .4; B(PR, 1.3, .04, .04, 0x8a8f96, 5 + i * 1.3 - 1, TOPO + .4, -6.8); }
// casa de máquinas: fica pronta quando o poço chega no topo
const CM = new THREE.Group(); add(CM); const YM = TOPO;
B(CM, 8.4, .22, 5, 0xc9c5bb, -.6, YM + 3.9, -2.3, .02); B(CM, .3, 3.9, 5, 0xddd5c2, -4.8, YM + 1.95, -2.3); B(CM, .3, 3.9, 5, 0xddd5c2, 3.6, YM + 1.95, -2.3); const pcm = add(new THREE.Mesh(new THREE.BoxGeometry(8.4, 3.9, .3), interno(0xe7dfcf)), CM); pcm.position.set(-.6, YM + 1.95, -4.7); pcm.receiveShadow = true; [[8.2, 1.3, -.6, -.55], [8.2, 2.75, -.6, -3.33], [1.6, .7, -3.9, -1.6], [4.2, .7, 1.4, -1.6]].forEach(([w, d, x, z]) => B(CM, w, .2, d, 0x7d8288, x, YM - .06, z, .01));
// duas escadas de marinheiro não: a casa de máquinas tem porta para a cobertura
B(CM, .9, 2.2, .06, 0x54606e, -3, YM + 1.1, -4.53, .01);
const yCM = (() => { const T = CI[1]; return { a: tk('topo', 1) - .2, b: tk('topo', 1) + .5 }; })(); AUTO.push(t => { const k = ease(rev(t, yCM.a, yCM.b)); CM.visible = k > 0; CM.scale.y = Math.max(k, .01); CM.position.y = YM * (1 - k); });

// escadas: lance para a direita, patamar, lance de volta
const NEG = (ANDARES - 1) * 2 * 11; const deg = new THREE.InstancedMesh(new THREE.BoxGeometry(.32, .16, 1.15), mat(0x7d7a74), NEG); deg.frustumCulled = false; deg.castShadow = deg.receiveShadow = true; add(deg, PR); { let n = 0; for (let i = 0; i < ANDARES - 1; i++) { const y = yA(i); for (let k = 0; k < 11; k++) { O.position.set(5.4 + k * .32, y + .08 + k * .136, -.75); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); deg.setMatrixAt(n++, O.matrix); O.position.set(8.8 - k * .32, y + 1.58 + k * .136, -2.05); O.updateMatrix(); deg.setMatrixAt(n++, O.matrix); } B(PR, 1, .16, 2.7, 0x7d7a74, 9, y + 1.5, -1.4, .01); B(PR, .06, 1, .06, 0x54606e, 5.1, y + .5, -.2, .01); const cor = add(new THREE.Mesh(new THREE.BoxGeometry(3.7, .05, .05), mat(0x54606e)), PR); cor.position.set(7.05, y + 1.5, -.18); cor.rotation.z = Math.atan2(1.5, 3.5); } }
const posEsc = (u, v = new THREE.Vector3()) => { const f = Math.floor(u), q = u - f, y = yA(f); let x, z, yy, dir; if (q < .5) { const k = q * 2; x = 5.3 + k * 3.5; yy = y + .18 + k * 1.5; z = -.75; dir = 1; } else { const k = (q - .5) * 2; x = 8.8 - k * 3.5; yy = y + 1.68 + k * 1.5; z = -2.05; dir = -1; } v.set(x, yy, z); v.dir = dir; return v; };
const SUB = []; [[0xe8683f, .05, .16, true], [0x2f7fd6, 1.55, .13, false], [0x8a5fc0, 3.1, .15, true], [0xd8a020, 4.7, .11, false], [0x3fa45a, 6.2, .14, true]].forEach(([c, u0, v, sac]) => { const q = PC.novo('personagem', { capacete: false, cinto: false, camisa: c, camisa2: c, escala: .76 }); add(q, PR); if (sac) { B(q.r.be.k, .3, .4, .16, 0xf4f4f2, 0, -.5, 0, .04); B(q.r.bd.k, .3, .36, .16, 0xffc21a, 0, -.5, 0, .04); } SUB.push({ q, u0, v }); });
const SUOR = new THREE.InstancedMesh(new THREE.SphereGeometry(.05, 8, 6), new THREE.MeshBasicMaterial({ color: 0x7fd2ff, toneMapped: false }), 30); SUOR.frustumCulled = false; add(SUOR, PR);
const V1 = new THREE.Vector3();
AUTO.push(t => { SUB.forEach(s => { const on = t < F(3); s.q.visible = on; if (!on) return; const u = (s.u0 + t * s.v) % 8.6; posEsc(u, V1); s.q.position.copy(V1); s.q.rotation.y = V1.dir > 0 ? PI / 2 : -PI / 2; s.q.r.anda(t * .85, .75); s.q.rotation.x = 0; }); const on = t < fim(0) + .4; SUOR.visible = on; if (on) { for (let i = 0; i < 30; i++) { const s = SUB[i % SUB.length], q = (t * 1.1 + i * .37) % 1; O.position.copy(s.q.position); O.position.x += Math.sin(i * 7) * .22; O.position.y += 1.7 - q * .9; O.position.z += .26; O.rotation.set(0, 0, 0); O.scale.setScalar(1 - q * .6); O.updateMatrix(); SUOR.setMatrixAt(i, O.matrix); } SUOR.instanceMatrix.needsUpdate = true; } });
// quem não consegue subir, ao pé da escada
const CAD = pc('pessoa_cadeirante', PR, 3.6, .03, -1.2, PI / 2); const BEB = pc('pessoa_idosa', PR, 2.4, .03, -2.5, 1); const BEN = pc('pessoa_idoso', PR, 1.5, .03, -1.5, 1);
AUTO.push(t => { BEB.visible = BEN.visible = t < CI[1].e; });

// obra: mesma rua, mesmos operários ---------------------------------------------------------------------------
const OB = new THREE.Group(); add(OB); mostra(OB, F(1) - .02, CI[7].a); const c1 = CI[1];
pc('obra_caminhao_betoneira', OB, 15.6, .02, -7.2, PI); pc('obra_sacos_cimento', OB, 3.4, .02, -2.3); pc('obra_carrinho_mao', OB, 1.7, .02, -2.2, .4); pc('obra_vergalhoes', OB, 11.4, .04, -4); pc('obra_cone', OB, 10.6, .04, -.8); pc('obra_cone', OB, 11.6, .04, -.8); pc('rua_cacamba', OB, -13.6, .03, -2.8);
const GRUA = pc('obra_grua_torre', OB, -16, 0, -22); const PD1 = PC.novo('personagem', { camisa: 0x2f7fd6, camisa2: 0x2565b5, escala: .8 }); add(PD1, OB); const brit = pc('obra_britadeira', OB, 2.3, .02, -1.2, 0);
AUTO.push(t => { CAD.visible = t < c1.e || t >= T_USO - 40 && t >= F(N - 1) - 1; PD1.position.set(1.8, .03, -.9); PD1.rotation.y = -PI / 2; PD1.r.anda(0, 0); PD1.r.respira(t); const bat = t > c1.e && t < tk('topo', 1); brit.position.y = .02 + (bat ? Math.abs(Math.sin(t * 40)) * .05 : 0); PD1.r.bd.j.rotation.x = PD1.r.be.j.rotation.x = -.8; PD1.position.y = .03 + (bat ? Math.abs(Math.sin(t * 40)) * .03 : 0); });

// poço: risco, abertura, concreto -----------------------------------------------------------------------------
const T1 = { ab: tk('abre', 1), tu: tk('túnel', 1), co: tk('concreto', 1), to: tk('topo', 1) };
const risco = add(new THREE.Mesh(new THREE.BoxGeometry(POCO.x1 - POCO.x0, TOPO + 2.7, .05), new THREE.MeshBasicMaterial({ color: 0xff4b3a, transparent: true, opacity: .34, depthWrite: false, toneMapped: false })), PR); risco.position.set((POCO.x0 + POCO.x1) / 2, (TOPO - 2.7) / 2, .1);
AUTO.push(t => { risco.visible = t > F(1) + .2 && t < T1.ab + .3; risco.material.opacity = .22 + Math.sin(t * 9) * .12; });
// bloco de terra que sai do fosso
const tampaT = add(box(POCO.x1 - POCO.x0 + .6, 2.7 + .7, 3.8, TERRA, .01), PR); tampaT.position.set((POCO.x0 + POCO.x1) / 2, FOSSO / 2 - .35, -1.8); const PAREDES = new THREE.Group(); add(PAREDES);
const CONC = mat(0x8d949b), CONC2 = mat(0x767d85);
const parede = (i, y, h) => { const g = new THREE.Group(); g.position.y = y; PAREDES.add(g); const pa = (w, hh, d, x, yy, z, m = CONC) => { const q = sh(new THREE.Mesh(new THREE.BoxGeometry(w, hh, d), m)); q.position.set(x, yy, z); g.add(q); return q; }; pa(.3, h, 3.4, POCO.x0 - .05, h / 2, POCO.z / 2); pa(4.2, h, .3, -1.65, h / 2, POCO.z - .1, CONC2); if (i >= 0) { pa(.3, h - 2.3, 3.4, POCO.x1 + .05, 2.3 + (h - 2.3) / 2, POCO.z / 2); pa(.3, 2.3, .8, POCO.x1 + .05, 1.15, -.4); pa(.3, 2.3, 1, POCO.x1 + .05, 1.15, -2.8); } else pa(.3, h, 3.4, POCO.x1 + .05, h / 2, POCO.z / 2); const T0 = T1.co - .15 + (i + 1) * .13; AUTO.push(t => { const k = ease(rev(t, T0, T0 + .24)); g.visible = k > 0; g.scale.y = Math.max(k, .01); }); return g; };
parede(-1, FOSSO - .35, -FOSSO + .35); for (let i = 0; i < ANDARES; i++) parede(i, yA(i), i === ANDARES - 1 ? TOPO - yA(i) : PD); B(PAREDES, 4.2, .35, 3.6, 0x9fa4a9, -1.65, FOSSO - .18, -1.6, .01);
// linhas das fôrmas no concreto, na parede de trás
{ const l = new THREE.InstancedMesh(new THREE.BoxGeometry(3.8, .02, .01), mat(0x8a9094), ANDARES * 5); l.frustumCulled = false; for (let i = 0; i < ANDARES * 5; i++) { O.position.set(-1.65, i * .6 + .2, POCO.z + .07); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); l.setMatrixAt(i, O.matrix); } add(l, PAREDES); }
// a laje racha e cai, andar por andar, e a poeira sobe
const POEIRA = []; const NP = 150, poeira = new THREE.InstancedMesh(new THREE.SphereGeometry(.28, 8, 6), new THREE.MeshBasicMaterial({ color: 0xcfc6b6, transparent: true, opacity: .32, depthWrite: false }), NP); poeira.frustumCulled = false; add(poeira, PR);
const nuvemP = (t0, x, y, z, n = 18, l = 1.5) => { for (let i = 0; i < n && POEIRA.length < NP; i++) POEIRA.push({ t0: t0 + rnd() * .15, x: x + (rnd() - .5) * 3, y: y + rnd() * .4, z: z + rnd() * 1.4, vx: (rnd() - .5) * 2.4, vy: .6 + rnd() * 1.3, l: .8 + rnd() * l }); };
LOSAS.forEach((m, i) => { const t0 = T1.ab + .05 + i * .1, y0 = m.position.y; AUTO.push(t => { const k = rev(t, t0, t0 + .55); m.visible = k < 1; m.position.y = y0 - k * k * 3.4; m.rotation.z = k * .6 * (i % 2 ? 1 : -1); }); nuvemP(t0, -1.65, yA(i), -1.6, 12); });
AUTO.push(t => { const k = ease(rev(t, T1.ab, T1.ab + .5)); tampaT.visible = k < 1; tampaT.scale.y = Math.max(1 - k, .01); tampaT.position.y = FOSSO / 2 - .35 - k * .9; const t2 = T1.to + .1; LOSA_T.visible = t < T1.ab + 1.1; });
AUTO.push(t => { for (let i = 0; i < NP; i++) { const p = POEIRA[i]; let s = .0001; if (p && t > p.t0 && t < p.t0 + p.l) { const q = (t - p.t0) / p.l; O.position.set(p.x + p.vx * q, p.y + p.vy * q, p.z); s = (.6 + q * 1.6) * (1 - q * q); } O.rotation.set(0, 0, 0); O.scale.setScalar(s); O.updateMatrix(); poeira.setMatrixAt(i, O.matrix); } poeira.instanceMatrix.needsUpdate = true; });

// trilhos -----------------------------------------------------------------------------------------------------
const T2 = { ...CI[2], tr: tk('trilhos', 2), de: tk('desliza', 2) };
const RAIL = mat(0x7f8892, MET), RAILC = mat(0xd9dee3, { roughness: .22, metalness: .75 }); const trilhos = [[-2.14, 0], [.14, 0], [-3.32, 1], [-2.28, 1]], RG = [];
const Z_TR = -2.9; trilhos.forEach(([x, cp], j) => { const g = new THREE.Group(); g.position.set(x, FOSSO, cp ? Z_EL : Z_TR); add(g); const L = TOPO + 1.2 - FOSSO, alma = sh(new THREE.Mesh(new THREE.BoxGeometry(.09, L, .16), RAILC)), pe = sh(new THREE.Mesh(new THREE.BoxGeometry(.07, L, .3), RAIL)); alma.position.y = pe.position.y = L / 2; alma.position.x = 0; pe.position.x = x < X_CAB - .5 && !cp ? -.05 : (cp ? (j === 2 ? -.05 : .05) : .05); g.add(alma, pe); const t0 = cp ? tk('bloco', 4) - .2 : T2.tr + j * .1, t1 = t0 + (cp ? .45 : 1.1); AUTO.push(t => { const k = ease(rev(t, t0, t1)); g.visible = k > 0; g.scale.y = Math.max(k, .01); }); RG.push(g); for (let i = 0; i < 11; i++) { const y = -FOSSO + .8 + i * 3, b = B(g, .18, .12, .34, 0x4c5563, pe.position.x * 2.4, y, 0, .01); b.scale.y = 1; } });
for (let k = 0; k < 7; k++) som(T2.tr + .1 + k * .17, 'toc');

// cabine ------------------------------------------------------------------------------------------------------
const CAB = new THREE.Group(); add(CAB); const CX = new THREE.Group(); CAB.add(CX);
const INOX = mat(0xcfd6db, { roughness: .28, metalness: .7 }), PAINEL = mat(0xf1ece0), COR_CAB = 0x2f6fb8;
const FAB = (w, h, d, c, x, y, z, r, o) => B(CX, w, h, d, c, x, y, z, r, o);
FAB(2.06, .1, 2.4, 0x3a4048, 0, .0, 0, .01); FAB(1.96, .03, 2.3, 0xb89a68, 0, .065, 0, .004); FAB(2.06, .1, 2.4, 0x4c5563, 0, 2.66, 0, .01);
const fundoCab = FAB(1.96, 2.56, .05, INOX, 0, 1.33, -1.18, .01); const esp = FAB(1.2, 1.7, .03, 0xa8d4e8, -.1, 1.5, -1.14, .01, { roughness: .05, metalness: .9 }); FAB(.05, 2.56, 2.36, INOX, -1.01, 1.33, 0, .01); FAB(1.8, .05, .05, 0xd9b84a, 0, .95, -1.08, .02, MET);
const lt = FAB(1.2, .04, 1.4, 0xfff2cc, 0, 2.59, 0, .01); lt.material = new THREE.MeshBasicMaterial({ color: 0xfff2cc, toneMapped: false }); lt.castShadow = false;
const luzCab = new THREE.PointLight(0xffe8c0, 0, 9, 1.7); luzCab.position.set(0, 2.3, .4); CAB.add(luzCab);
const mold = FAB(.26, .9, .03, 0x22262c, .72, 1.45, -1.14, .01); for (let i = 0; i < 12; i++) { const m = FAB(.05, .05, .02, i === 7 ? 0xffd23f : 0xe6e6e6, .66 + (i % 2) * .12, 1.15 + (i >> 1) * .12, -1.11, .01); }
// porta da cabine (no lado direito, de frente para o hall)
const PC_E = FAB(.05, 2.5, 1, 0xbfc7cd, 1.01, 1.33, -.5, .01, MET), PC_D = FAB(.05, 2.5, 1, 0xbfc7cd, 1.01, 1.33, .5, .01, MET);
// armação de aço: montantes, travessa e sapatas das guias
const AC = 0x3b5f8a; const ARM = new THREE.Group(); CAB.add(ARM); B(ARM, .12, 3.4, .16, AC, -1.1, 1.45, Z_TR - Z_EL, .01); B(ARM, .12, 3.4, .16, AC, 1.1, 1.45, Z_TR - Z_EL, .01); B(ARM, 2.4, .2, .2, AC, 0, 3.1, 0, .02); B(ARM, 2.4, .2, .24, AC, 0, -.2, 0, .02);
const SAP = [];[-1, 1].forEach(s => [-.15, 3.05].forEach(y => { const q = B(ARM, .12, .42, .3, 0xffc21a, s * 1.13, y, Z_TR - Z_EL, .02); SAP.push(q); B(ARM, .16, .12, 1.3, AC, s * 1.1, y, (Z_TR - Z_EL) / 2, .01); }));
const argola = add(new THREE.Mesh(new THREE.TorusGeometry(.13, .035, 8, 20), mat(0x4c5563, MET)), ARM); argola.position.set(0, 3.32, 0);
// garras do freio embaixo da cabine, abrem e fecham nos trilhos
const GARRA = []; [-1, 1].forEach(s => { const g = new THREE.Group(); g.position.set(s * 1.14, -.4, Z_TR - Z_EL); CAB.add(g); B(g, .34, .3, .4, 0xd8352f, -s * .08, 0, 0, .02); const a = B(g, .12, .22, .12, 0xffd23f, s * .02, -.02, .15, .01), b = B(g, .12, .22, .12, 0xffd23f, s * .02, -.02, -.15, .01); GARRA.push({ g, a, b, s }); });
const PASS = PC.novo('personagem', { capacete: false, cinto: false, camisa: 0xe8683f, camisa2: 0xc9532e, escala: .8 }); CAB.add(PASS); PASS.position.set(-.1, .09, .1); PASS.rotation.y = .3;
CAB.position.set(X_CAB, 0, Z_EL);

// contrapeso --------------------------------------------------------------------------------------------------
const T4 = { ...CI[4], bl: tk('bloco', 4), de: tk('desce', 4), so: tk('sobe', 4) };
const CP = new THREE.Group(); CP.position.set(X_CP, 0, Z_EL); add(CP); [-.42, .42].forEach(x => B(CP, .08, 2.6, .2, 0x4c5563, x, 1.3, 0, .01)); B(CP, .92, .12, .24, 0x4c5563, 0, 2.56, 0, .01); B(CP, .92, .12, .24, 0x4c5563, 0, .06, 0, .01);[-1, 1].forEach(s => [.1, 2.5].forEach(y => B(CP, .08, .3, .26, 0xffc21a, s * .48, y, 0, .02)));
const BLOCOS = []; for (let i = 0; i < 12; i++) { const m = B(CP, .76, .17, .2, i % 2 ? 0xe2802a : 0xf0962e, 0, .21 + i * .19, 0, .012); BLOCOS.push(m); const t0 = T4.bl - .05 + i * .07, y0 = m.position.y; AUTO.push(t => { const k = ease(rev(t, t0, t0 + .16)); m.visible = k > 0; m.position.y = y0 + (1 - k) * 3; }); som(t0 + .13, 'tijolo'); }
const cpOn = () => tk('pendura', 4) - .1;

// máquina de tração na casa de máquinas ------------------------------------------------------------------------
const T3 = { ...CI[3], ca: tk('cabos', 3), ro: tk('roda', 3), mo: tk('motor', 3), so: tk('sozinha', 3) };
const R_TR = .5, R_DF = .3, X_TR = X_CP + R_TR, X_DF = X_CAB - R_DF, Y_FIO = YM + 2.1, Y_TR = Y_FIO - R_TR, Y_DF = Y_FIO - R_DF;
const MQ = new THREE.Group(); add(MQ);
const roda = (x, y, r, c) => { const g = new THREE.Group(); g.position.set(x, y, Z_EL); MQ.add(g); const d = add(cil(r, r, .34, c, 40), g); d.rotation.x = PI / 2; for (let i = 0; i < 5; i++) { const s = add(new THREE.Mesh(new THREE.TorusGeometry(r * .985, .022, 6, 44), mat(0x1c1f24)), g); s.position.z = -.16 + i * .08; } const m = add(cil(r * .62, r * .62, .38, 0x2c3138, 26), g); m.rotation.x = PI / 2; add(cil(r * .16, r * .16, .42, 0xd9dee3, 16), g).rotation.x = PI / 2; for (let i = 0; i < 4; i++) { const b = B(g, r * 1.05, r * .12, .4, 0xffd23f, 0, 0, 0, .01); b.rotation.z = i * PI / 4; } return g; };
const R1 = roda(X_TR, Y_TR, R_TR, 0x8a919a), R2 = roda(X_DF, Y_DF, R_DF, 0x8a919a);
const base = new THREE.Group(); MQ.add(base); [-.42, .42].forEach(q => B(base, 3.5, .2, .2, 0x3a4048, -1.75, YM + .2, Z_EL + q, .02)); [[X_TR - .5, 1.2], [X_DF + .2, 1.2]].forEach(([x, h]) => { B(base, .16, Y_TR - YM - .2, .16, 0x3a4048, x, (Y_TR + YM + .3) / 2, Z_EL + .36, .01); B(base, .16, Y_TR - YM - .2, .16, 0x3a4048, x, (Y_TR + YM + .3) / 2, Z_EL - .36, .01); }); B(base, 2.1, .1, .18, 0x3a4048, -1.75, Y_TR + .02, Z_EL - .36, .01);
const MOT = new THREE.Group(); MOT.position.set(X_TR, Y_TR, Z_EL - 1); MQ.add(MOT); const mcor = 0x2a7f8f; const mc = add(cil(.62, .62, 1.3, mcor, 30), MOT); mc.rotation.x = PI / 2; for (let i = 0; i < 7; i++) { const a = add(new THREE.Mesh(new THREE.TorusGeometry(.63, .025, 8, 40), mat(0x236c7a)), MOT); a.position.z = -.54 + i * .18; } add(cil(.3, .3, 1.5, 0xd9dee3, 20), MOT).rotation.x = PI / 2; const eixo = add(cil(.12, .12, .9, 0xd9dee3, 16), MOT); eixo.rotation.x = PI / 2; eixo.position.z = .9; B(MOT, .5, .3, .5, 0x1f2329, 0, .7, -.1, .03); B(MOT, .22, .12, .22, 0xffc21a, 0, .9, -.1, .02); B(MOT, 1.5, .4, 1.5, 0x3a4048, 0, -.86, 0, .03); B(MOT, 1.2, .8, 1.2, 0x2c3138, 0, -1.25, 0, .02);
const rubro = add(new THREE.Mesh(new THREE.SphereGeometry(1.2, 18, 12), new THREE.MeshBasicMaterial({ color: 0xff3a1a, transparent: true, opacity: 0, depthWrite: false, toneMapped: false })), MQ); rubro.position.set(X_TR, Y_TR, Z_EL - .6); const fum = new THREE.InstancedMesh(new THREE.SphereGeometry(.22, 8, 6), new THREE.MeshBasicMaterial({ color: 0x55585e, transparent: true, opacity: .6, depthWrite: false }), 16); fum.frustumCulled = false; add(fum, MQ);
const ROPE = 4, ropeG = new THREE.CylinderGeometry(.024, .024, 1, 6), ropeM = mat(0x25282e, { roughness: .5 }), CABOS = [], CABOSP = [], ZC = i => Z_EL - .09 + i * .06;
for (let i = 0; i < ROPE; i++) { const dx = (i - 1.5) * .07; const a = sh(new THREE.Mesh(ropeG, ropeM)); a.position.set(X_CAB + dx, 0, ZC(i)); add(a); CABOS.push(a); const b = sh(new THREE.Mesh(ropeG, ropeM)); b.position.set(X_CP + dx, 0, ZC(i)); add(b); CABOSP.push(b); }
const TOPOC = []; for (let i = 0; i < ROPE; i++) { const pts = []; for (let k = 0; k <= 12; k++) { const a = PI - k / 12 * PI / 2; pts.push(new THREE.Vector3(X_TR + Math.cos(a) * (R_TR + .02), Y_TR + Math.sin(a) * (R_TR + .02), ZC(i))); } for (let k = 0; k <= 12; k++) { const a = PI / 2 - k / 12 * PI / 2; pts.push(new THREE.Vector3(X_DF + Math.cos(a) * (R_DF + .02), Y_DF + Math.sin(a) * (R_DF + .02), ZC(i))); } const m = sh(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 60, .024, 6), ropeM)); add(m); TOPOC.push(m); }
// corda provisória com o operário puxando lá em cima
const CORDA = sh(new THREE.Mesh(new THREE.CylinderGeometry(.03, .03, 1, 6), mat(0xd9a55f))); add(CORDA); CORDA.position.set(X_CAB, 0, Z_EL);
const OP = PC.novo('personagem', { camisa: 0xff8a22, camisa2: 0xe07016, escala: .8 }); add(OP); OP.position.set(1.7, YM + .04, -1.6); OP.rotation.y = -PI / 2;

// molas no fundo ----------------------------------------------------------------------------------------------
const T6 = { ...CI[6], te: tk('térreo', 6), mo: tk('molas', 6) };
const MOLA_H = 1.5, MOLAS = []; [-.55, .55].forEach((x, j) => { const g = new THREE.Group(); g.position.set(X_CAB + x, FOSSO, Z_EL); add(g); const pts = []; for (let i = 0; i <= 70; i++) { const a = i / 70 * PI * 2 * 5.5; pts.push(new THREE.Vector3(Math.cos(a) * .24, i / 70, Math.sin(a) * .24)); } add(sh(new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 220, .05, 7), mat(0xf0c020, { roughness: .4, metalness: .3 }))), g).scale.y = MOLA_H; const pb = add(cil(.34, .38, .08, 0x4c5563, 20)); g.parent.add(pb); pb.position.set(X_CAB + x, FOSSO + .04, Z_EL); const pt = add(cil(.32, .32, .07, 0x4c5563, 20), g); pt.position.y = MOLA_H; MOLAS.push({ g, pt, x, pb }); });

// portas de cada andar --------------------------------------------------------------------------------------
const T7 = { ...CI[7], po: tk('portas', 7), ab: tk('abrem', 7) };
const PORTAS = [], FP = 5; const BOT = [];
for (let i = 0; i < ANDARES; i++) { const y = yA(i), g = new THREE.Group(); g.position.set(POCO.x1 + .22, y, 0); add(g); const a = B(g, .06, 2.28, .75, 0xc8ced3, 0, 1.15, Z_EL - .375 + .0, .01, MET), b = B(g, .06, 2.28, .75, 0xbfc6cc, 0, 1.15, Z_EL + .375, .01, MET); B(g, .1, .12, 1.7, 0x4c5563, .02, 2.35, Z_EL, .01); const t0 = T7.po + .1 + i * .07; PORTAS.push({ g, a, b, t0, i }); AUTO.push(t => { g.visible = t >= t0; g.scale.y = t >= t0 ? Math.max(back((t - t0) / .2), .01) : .01; }); som(t0, 'toc');
  const bt = new THREE.Group(); bt.position.set(POCO.x1 + .24, y + 1.3, -.2); add(bt); B(bt, .03, .42, .24, 0xd9dee3, 0, 0, 0, .01, MET); const luz_ = add(new THREE.Mesh(new THREE.SphereGeometry(.08, 12, 10), new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false })), bt); luz_.position.set(.03, 0, 0); BOT.push({ bt, luz_, i }); }

// comando: armário e tela na casa de máquinas
const T8 = { ...CI[8], bo: tk('botões', 8), co: tk('computador', 8), pa: tk('paradas', 8) };
const QD = new THREE.Group(); QD.position.set(2, YM, -4.2); add(QD); B(QD, 1.8, 2.6, .6, 0x4c5563, 0, 1.3, 0, .03); B(QD, 1.66, 2.44, .03, 0x59616c, 0, 1.3, .31, .01); const TELA = add(new THREE.Mesh(new THREE.PlaneGeometry(1.34, 1.05), new THREE.MeshBasicMaterial({ color: 0x0b1626, toneMapped: false })), QD); TELA.position.set(0, 1.85, .33); const NBAR = 10, barras = []; for (let i = 0; i < NBAR; i++) { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(1.1, .075), new THREE.MeshBasicMaterial({ color: 0x24405c, toneMapped: false })), QD); m.position.set(0, 1.42 + i * .095, .34); barras.push(m); } const LQ = []; for (let i = 0; i < 24; i++) { const m = add(new THREE.Mesh(new THREE.CircleGeometry(.03, 10), new THREE.MeshBasicMaterial({ color: 0x3dff7c, toneMapped: false })), QD); m.position.set(-.55 + (i % 8) * .157, .55 + (i >> 3) * .2, .335); LQ.push(m); } mostra(QD, T8.co - .1);

// roteiro da cabine: altura y(t) ------------------------------------------------------------------------------
const f5a = CI[5].a, tBaixa = T4.de; const T5 = { ...CI[5], ga: tk('garras', 5), tv: tk('travam', 5), ra: tk('rápido', 5), ar: tk('arrebentarem', 5) };
const YK = []; const Y = (t, y) => YK.push([t, y]);
const FIM7 = T7.ab + .2, ST = [T8.co + .2, 0];
Y(0, 9);
// sobe e desce nos trilhos
Y(T2.de - .1, 9); Y(CI[2].n + .2, 21);
// cabos e motor: parada lá em cima, depois sobe pelo motor
Y(T3.n - .05, 21); Y(fim(3), 25.5);
// a câmera está na casa de máquinas: aqui a cabine recomeça embaixo, mal saindo do lugar
Y(fim(3) + .05, 3); Y(T4.bl, 4); Y(T4.de, 4); Y(fim(4) + .05, 24);
// cabos arrebentam
const tQ = T5.ar + .12;
Y(tQ, 24); Y(T5.e - .05, 4); Y(T5.e - .02, 19); Y(T5.tv + .05, 19); Y(T5.tv + .62, 15.5); Y(fim(5) + .05, 15.5);
// passa do térreo
Y(F(6) + .02, 8); Y(T6.te + .5, FOSSO + .55); Y(T6.e - .05, FOSSO + .55); Y(T6.mo + .1, 3.4); Y(T6.mo + .5, 3.4); Y(T6.n + .35, FOSSO + 1.7); Y(T6.n + .75, FOSSO + 2.05); Y(T6.n + 1, FOSSO + 1.95); Y(fim(6) + .05, 0);
// portas
Y(T7.a, 0); Y(T7.ab - .9, 0); Y(T7.ab + .6, yA(FP)); Y(fim(7) + .05, yA(FP));
// sem saber aonde ir: sobe e desce à toa
const q8 = F(8), e8 = T8.e; Y(q8 + .1, yA(5)); Y(q8 + (e8 - q8) * .4, yA(8)); Y(q8 + (e8 - q8) * .75, yA(3)); Y(T8.bo, yA(3)); Y(T8.pa + .05, yA(3));
const PAR = [[2, 3], [5, 4], [8, 7]]; let tq = T8.pa + .1; const durS = Math.max(.75, (fim(8) - tq + .1) / 3); const PARADAS = [];
PAR.forEach(([a]) => { const d = (durS - .34); Y(tq + d, yA(a)); PARADAS.push({ a, t0: tq + d, t1: tq + d + .3 }); Y(tq + d + .3, yA(a)); tq += durS; });
const tVolta = fim(8) + .02; Y(tVolta, 0);
// cadeirante entra e vai para o último andar
const tU0 = F(N - 1) + .9, tU1 = T_USO + 1.2; Y(tU0, 0); Y(tU1, yA(9)); Y(fim(N - 1) - .5, yA(9)); Y(D.total - .4, yA(4));
YK.sort((a, b) => a[0] - b[0]);
const yCab = t => { let i = 0; while (i < YK.length - 2 && t > YK[i + 1][0]) i++; const a = YK[i], b = YK[i + 1]; if (t <= a[0]) return a[1]; const k = rev(t, a[0], b[0]); const q = (t > T5.ar && t < T5.e) || (t > T5.tv && t < T5.tv + .62) || (t > F(6) && t < T6.te + .5) ? k * k : ease(k); return a[1] + (b[1] - a[1]) * q; };

// quando cada coisa mostra
const T_CAB = F(2) - .02;
const faseCabos = t => t >= T3.ca && !(t >= tQ && t < T5.e);
const CPY = 27.3; const cpVis = t => t >= tk('pendura', 4) - .05;
const BAT = []; const faisca = new THREE.InstancedMesh(new THREE.SphereGeometry(.05, 6, 5), new THREE.MeshBasicMaterial({ color: 0xffd84a, toneMapped: false }), 70); faisca.frustumCulled = false; add(faisca);
const FAI = []; const fagulha = (t0, x, y, z, n = 14, s = 1) => { for (let i = 0; i < n; i++) FAI.push({ t0: t0 + rnd() * .08, x, y: y + (rnd() - .5) * .4, z: z + (rnd() - .5) * .3, vx: (rnd() - .5) * 4.2 * s, vy: (rnd() - .2) * 3.2, l: .3 + rnd() * .3 }); };
// batidas da caixa solta
const nBat = 5; const tB = i => F(2) + .25 + i * Math.max(.34, (T2.e - F(2) - .3) / nBat); for (let i = 0; i < nBat; i++) { const s = i % 2 ? 1 : -1; fagulha(tB(i), s > 0 ? .1 : POCO.x0 + .2, 11, Z_EL, 14); }
// fagulhas do freio e pancada do fosso
const YFR = 17; for (let i = 0; i < 6; i++) { fagulha(T5.tv + .3 + i * .05, X_CAB - 1.14, 15.5 + (5 - i) * .6 - .3, Z_TR, 8); fagulha(T5.tv + .3 + i * .05, X_CAB + 1.14, 15.5 + (5 - i) * .6 - .3, Z_TR, 8); }
fagulha(tQ, X_CAB, 31.2, Z_EL, 30, 1.6); nuvemP(T6.te + .5, -1.3, FOSSO + .2, -1.4, 16, 1.4); fagulha(T6.te + .5, X_CAB, FOSSO + .4, Z_EL, 26, 1.6);
const fumV = []; for (let i = 0; i < 16; i++) fumV.push({ p: rnd(), x: rnd() - .5 });
AUTO.push(t => { for (let i = 0; i < 70; i++) { O.scale.setScalar(.0001); O.position.set(0, -100, 0); O.rotation.set(0, 0, 0); O.updateMatrix(); faisca.setMatrixAt(i, O.matrix); } let n = 0; for (const f of FAI) { if (n >= 70) break; if (t > f.t0 && t < f.t0 + f.l) { const q = t - f.t0; O.position.set(f.x + f.vx * q, f.y + f.vy * q - 5 * q * q, f.z); O.scale.setScalar(1.3 - q); O.updateMatrix(); faisca.setMatrixAt(n++, O.matrix); } } faisca.instanceMatrix.needsUpdate = true; });

// atualização principal do elevador ---------------------------------------------------------------------------
let ultima = 0;
const portaAb = (i, t) => { // quanto a porta do andar i está aberta
  const ev = []; if (i === 0) ev.push([T7.po - 2, T7.a + .4, 0]); if (i === FP) ev.push([T7.ab + .65, fim(7) - .1]); PARADAS.forEach(p => { if (p.a === i) ev.push([p.t0 + .02, p.t1 - .02]); }); if (i === 0) ev.push([fim(8) + .1, tU0]); if (i === 9) ev.push([tU1 + .05, fim(N - 1) - .55]);
  let v = 0; ev.forEach(([a, b]) => { v = Math.max(v, Math.min(ease(rev(t, a, a + .22)), 1 - ease(rev(t, b - .22, b)))); }); return v; };
AUTO.push(t => {
  const on = t >= T_CAB; CAB.visible = on; let y = yCab(t), sw = 0;
  if (t < T2.e) { const q = rev(t, F(2), T2.e), a = Math.sin((t - F(2)) * PI / Math.max(.34, (T2.e - F(2) - .3) / nBat)) * .68; sw = a * (1 - ease(rev(t, T2.e - .1, T2.e + .25))); }
  else if (t < T2.tr + .4) sw = 0;
  const xBase = t < T2.e + .2 ? X_CAB - .62 * (1 - ease(rev(t, T2.e, T2.e + .3))) : X_CAB;
  if (on) { CAB.position.set(xBase + sw, y, Z_EL); CAB.rotation.z = -sw * .05; } else y = 0;
  // treme quando a garra trava ou quando bate no fundo
  const tr = Math.max(t > T5.tv + .62 && t < T5.tv + 1 ? 1 - rev(t, T5.tv + .62, T5.tv + 1) : 0, t > T6.te + .5 && t < T6.te + .9 ? 1 - rev(t, T6.te + .5, T6.te + .9) : 0);
  CAB.position.y += Math.sin(t * 90) * .05 * tr;
  // mostra as sapatas só quando há trilho
  SAP.forEach(s => { s.visible = t > T2.tr + .6; }); ARM.visible = on;
  // garras
  const g0 = T5.ga; GARRA.forEach(g => { const s = t >= g0 ? Math.max(back((t - g0) / .24), .01) * 1.5 : .001; g.g.visible = t >= g0; g.g.scale.setScalar(s); const fecha = ease(rev(t, T5.tv + .28, T5.tv + .4)) * (1 - ease(rev(t, fim(5) - .1, fim(5)))); g.a.position.z = .19 - fecha * .09; g.b.position.z = -.19 + fecha * .09; });
  // passageiro assustado
  const cheio = t > fim(4) - 1 && t < CI[7].a || t > T7.ab + .6 && t < fim(7); PASS.visible = cheio; PASS.r.anda(0, 0); PASS.r.respira(t); const susto = (t > T5.ar && t < T5.e) || (t > T5.tv && t < T5.n) || (t > T6.te - .1 && t < T6.e); PASS.r.be.j.rotation.x = PASS.r.bd.j.rotation.x = susto ? -2.8 + Math.sin(t * 22) * .15 : 0; const qd = (t > T5.ar && t < T5.e); PASS.position.y = .09 + (qd ? .35 : 0);
  // cabos: pendurados da roda até a cabine
  const cVis = faseCabos(t), desce = ease(rev(t, T3.ca, T3.ca + .6)); const yTop = Y_FIO - R_DF, yH = y + 3.32; const yLast = yTop - (yTop - yH) * desce;
  CABOS.forEach(m => { m.visible = cVis && on; m.position.y = (yTop + yLast) / 2; m.scale.y = Math.max(yTop - yLast, .01); });
  TOPOC.forEach(m => { m.visible = t >= T3.ro - .05 && !(t >= tQ && t < T5.e); });
  // contrapeso e cabos do outro lado
  const cpOk = cpVis(t); CP.visible = cpOk; const ycp = cpOk ? Math.max(.4, t < T4.de ? 24.6 : 24.6 - (y - 4) * 1.12) : 0; CP.position.y = ycp; const tp = Y_FIO - R_TR, cpTop = ycp + 2.62; CABOSP.forEach(m => { m.visible = cVis && cpOk; m.position.y = (tp + cpTop) / 2; m.scale.y = Math.max(tp - cpTop, .01); });
  // rodas giram com a cabine
  MQ.visible = t >= T3.ro - .05; const r = t >= T3.ro ? Math.max(back((t - T3.ro) / .28), .01) : .01; R1.scale.setScalar(r); R2.scale.setScalar(r); base.visible = t >= T3.ro; MOT.visible = t >= T3.mo; const kM = t >= T3.mo ? Math.max(back((t - T3.mo) / .3), .01) : .01; MOT.scale.setScalar(kM); const giro = y / R_TR; R1.rotation.z = giro; R2.rotation.z = giro * R_TR / R_DF;
  // motor sofrendo no começo do contrapeso
  const quente = ease(rev(t, CI[4].a, CI[4].a + .7)) * (1 - ease(rev(t, T4.de, T4.de + .5))); rubro.material.opacity = quente * (.3 + Math.sin(t * 15) * .12); MOT.position.x = X_TR + Math.sin(t * 70) * .012 * quente; fum.visible = quente > .05; if (fum.visible) { fumV.forEach((f, i) => { const q = (t * .6 + f.p) % 1; O.position.set(X_TR + f.x * .9, Y_TR + .7 + q * 2, Z_EL - 1); O.rotation.set(0, 0, 0); O.scale.setScalar((.4 + q * 1.6) * quente); O.updateMatrix(); fum.setMatrixAt(i, O.matrix); }); fum.instanceMatrix.needsUpdate = true; }
  // corda provisória e operário puxando
  const cOn = on && t < T3.ca + .2; CORDA.visible = cOn; if (cOn) { const x = CAB.position.x, yh = y + 3.3; CORDA.position.set(x * .5 + X_CAB * .5, (TOPO + 1.2 + yh) / 2, Z_EL); CORDA.scale.y = TOPO + 1.2 - yh; CORDA.rotation.z = Math.atan2(X_CAB - x, TOPO + 1.2 - yh) * -1; }
  OP.visible = t > F(2) - .1 && t < CI[7].a; OP.r.anda(0, 0); OP.r.respira(t); const puxa = t > F(3) && t < T3.ca; if (puxa) { const w = Math.sin(t * 7); OP.r.bd.j.rotation.x = OP.r.be.j.rotation.x = -1.5 + w * .35; OP.rotation.z = .1 + w * .08; OP.position.x = -.5 + w * .12; OP.rotation.y = -PI / 2; CAB.position.y += Math.abs(w) * .06; } else { OP.rotation.z = 0; OP.position.x = t > T3.ro ? .4 : 1.7; OP.r.bd.j.rotation.x = OP.r.be.j.rotation.x = 0; }
  // molas
  MOLAS.forEach(m => { const on_ = t >= T6.mo - .05; m.g.visible = m.pb.visible = on_; if (!on_) return; const k = Math.max(back((t - T6.mo) / .3), .01), base_ = CAB.position.y - .3 - FOSSO; const h = Math.min(MOLA_H * k, Math.max(.5, base_)); m.g.scale.y = h / MOLA_H; m.g.scale.x = m.g.scale.z = 1; });
  // portas abertas
  PORTAS.forEach(p => { const v = portaAb(p.i, t); p.a.position.z = Z_EL - .375 - v * .72; p.b.position.z = Z_EL + .375 + v * .72; });
  const vc = PORTAS.reduce((m, p) => Math.max(m, Math.abs(CAB.position.y - yA(p.i)) < .1 ? portaAb(p.i, t) : 0), 0); PC_E.position.z = -.5 - vc * .9; PC_D.position.z = .5 + vc * .9;
  // botões: acesos enquanto há chamada
  BOT.forEach(b => { const ped = PARADAS.find(p => p.a === b.i); const on2 = ped && t > T8.bo + PAR.findIndex(q => q[0] === b.i) * .28 && t < ped.t0; b.luz_.material.color.setHex(on2 ? 0xffd23f : 0x6a7078); b.bt.visible = t >= T8.bo - .15; });
  barras.forEach((m, i) => { const at = Math.abs(CAB.position.y - yA(i)) < 1.5, ped = PARADAS.find(p => p.a === i); const ch = ped && t > T8.pa && t < ped.t0; m.material.color.setHex(at ? 0x3dff7c : ch ? 0xffd23f : 0x24405c); }); LQ.forEach((m, i) => { m.visible = Math.sin(t * (5 + i * .7) + i * 3) > -.2; });
  // luz da cabine
  const n = ease(rev(t, F(N - 1) + .1, T_USO + .4)); luzCab.intensity = on ? 10 + n * 34 : 0;
  ultima = t;
});
// sons do elevador
for (let k = 0; k < nBat; k++) som(tB(k), 'impact'); som(CI[1].a + .1, 'riser'); for (let k = 0; k < 10; k++) som(T1.ab + k * .1, 'crack'); som(T1.ab, 'impact'); for (let q = T1.co; q < T1.to + .6; q += .4) som(q, 'concreto');
for (let q = T3.n; q < fim(5) - 1; q += 1.2) som(q, 'motor'); som(T3.mo, 'pop'); som(T3.ro, 'toc'); som(tQ, 'crack'); som(tQ + .05, 'impact'); som(T5.ga, 'pop'); som(T5.tv + .62, 'impact'); som(T5.tv + .3, 'crack'); som(T6.te + .5, 'impact'); som(T6.te + .5, 'desaba'); som(T6.mo + .1, 'pop'); som(T6.n + .4, 'toc'); som(T7.ab + .7, 'ding'); PARADAS.forEach(p => som(p.t0, 'ding')); som(T8.bo, 'pop'); som(T8.co, 'zumbido'); som(T8.bo + .3, 'pop');

// bola que rola para o poço aberto, com a criança parando na beira
const T_B = tk('cair', 7), BOLA = add(esf(.14, 0xff4a4a)), CR_ = PC.novo('personagem', { capacete: false, cinto: false, camisa: 0xffc21a, camisa2: 0xffc21a, escala: .55 }); add(CR_); const FPY = yA(FP);
AUTO.push(t => { const a = t > CI[7].a - .05 && t < T7.po + .5; BOLA.visible = CR_.visible = a; if (!a) return; const k = rev(t, CI[7].a + .05, T_B + .45), x = 3 - k * 3.5; BOLA.rotation.z = k * 16; if (x > POCO.x1 - .1) BOLA.position.set(x, FPY + .15, Z_EL); else { const q = t - (CI[7].a + .05 + (T_B + .4 - CI[7].a) * (3.15 / 3.5)); BOLA.position.set(Math.max(POCO.x1 - .6 - q * .4, -.2), FPY + .15 - 6 * q * q, Z_EL); } const kk = ease(rev(t, CI[7].a + .3, T_B + .5)); CR_.position.set(3.6 - kk * 2.4, FPY + .03, Z_EL + .1); CR_.rotation.y = -PI / 2; if (kk < 1) CR_.r.anda(t); else { CR_.r.anda(0, 0); const w = Math.sin(t * 16); CR_.r.be.j.rotation.x = CR_.r.bd.j.rotation.x = -2.6 + w * .3; } });
const MOR = PC.novo('personagem', { capacete: false, cinto: false, camisa: 0x8a5fc0, camisa2: 0x7a4fb0, escala: .78 }); add(MOR); B(MOR.r.be.k, .3, .4, .16, 0xf4f4f2, 0, -.5, 0, .04);
AUTO.push(t => { const a = t > T7.ab - .3 && t < fim(7) + .1; MOR.visible = a; if (!a) return; const k = ease(rev(t, T7.ab + .85, T7.ab + 1.7)); const entra = k > 0; MOR.position.set(2.1 - k * 2.6, FPY + .03, Z_EL); MOR.rotation.y = -PI / 2; if (entra && k < 1) MOR.r.anda(t); else { MOR.r.anda(0, 0); MOR.r.respira(t); } });
// mão que aperta o botão no hall
const DEDO = PC.novo('personagem', { capacete: false, cinto: false, camisa: 0x3fa45a, camisa2: 0x2f8f4a, escala: .78 }); add(DEDO); AUTO.push(t => { const a = t > CI[8].a && t < T8.co + .2; DEDO.visible = a; if (!a) return; DEDO.position.set(POCO.x1 + 1.1, yA(5) + .03, .1); DEDO.rotation.y = -PI / 2; DEDO.r.anda(0, 0); DEDO.r.respira(t); DEDO.r.bd.j.rotation.x = t > T8.bo - .2 ? -1.7 : 0; DEDO.r.be.j.rotation.x = 0; });
const ESP = []; PAR.forEach(([a], i) => { const q = PC.novo('personagem', { capacete: false, cinto: false, camisa: [0xe8683f, 0x2f7fd6, 0xffc21a][i], camisa2: [0xc9532e, 0x2565b5, 0xd8a020][i], escala: .78 }); add(q); q.position.set(1.6, yA(a) + .03, Z_EL - .3); q.rotation.y = -PI / 2; ESP.push({ q, a }); });
AUTO.push(t => ESP.forEach((e, i) => { const p = PARADAS[i], a = t > CI[8].a - .1 && t < p.t1; e.q.visible = a; if (!a) return; e.q.position.x = 1.6 - ease(rev(t, p.t0, p.t1)) * 1.6; if (t > p.t0) e.q.r.anda(t); else { e.q.r.anda(0, 0); e.q.r.respira(t); e.q.rotation.y = -PI / 2; } }));
// cadeirante entra na cabine
AUTO.push(t => { if (t < CI[1].e) return; const a = t >= tVolta && t < D.total + 2; if (a) { CAD.visible = true; const k = ease(rev(t, tVolta + .1, tU0 - .1)), inSide = t >= tU0 - .1 && t < tU1 + .1, sai = ease(rev(t, tU1 + .25, tU1 + 1)); CAD.rotation.y = -PI / 2; if (t < tU0 - .1) CAD.position.set(3.2 - k * 3.6, .03, Z_EL); else if (inSide) CAD.position.set(-.4, CAB.position.y + .1, Z_EL); else { CAD.rotation.y = PI / 2; CAD.position.set(-.4 + sai * 2.6, yA(9) + .03, Z_EL); } } else CAD.visible = t < c1.e; });

// luz, noite, cidade acendendo --------------------------------------------------------------------------------
const BG = new THREE.Color(), DIA = new THREE.Color(CEU), NO = new THREE.Color('#0a1028'), ENT = new THREE.Color('#e8783f'), DG = new THREE.Color(GR), NG = new THREE.Color(0x10261c);
const JAC = new THREE.Color(0xffd98a), JDI = new THREE.Color(0x3a5468); let acesas = -1;
AUTO.push(t => { const a = F(N - 1) + .1, n = ease(rev(t, a, T_USO + .5)), pr = ease(rev(t, T_USO, T_USO + 3));
  if (n > 0) { BG.copy(DIA).lerp(ENT, Math.min(n * 2, 1) * (1 - Math.max(0, n * 2 - 1))).lerp(NO, Math.max(0, n * 2 - 1)); scene.background = BG; } else scene.background = fundo;
  sol.intensity = 1.9 - n * 1.75; hemi.forEach(h => { h.intensity = .95 - n * .65; }); scene.environmentIntensity = .3 - n * .1; scene.fog.color.setHex(n > .5 ? 0x121a36 : 0xcfe6f2); chao.material.color.copy(DG).lerp(NG, n);
  INT.forEach(i => { i.m.emissive.setHex(i.c); i.m.emissiveIntensity = n * .62; }); LUZTETO.forEach(m => { m.emissive.setHex(0xfff0c8); m.emissiveIntensity = n * 2.2; });
  // as janelas do bairro acendem em onda a partir do prédio
  const pq = Math.floor(pr * 40); if (pq !== acesas) { acesas = pq; PJ.forEach((j, i) => { const ok = pr * 1.2 > j.on + Math.abs(j.x) / 400; janD.setColorAt(i, ok && j.on < .86 ? C.setHSL(.11 + j.on * .03, .85, .62) : JDI); }); janD.instanceColor.needsUpdate = true; }
  NUV.forEach((g, i) => { g.position.x += 0; g.children.forEach(c => { c.material.color.setHex(0xffffff).lerp(C.setHex(0x1c2848), n); }); }); const fl_ = (() => { let fl = 0; for (let i = 1; i < N - 1; i++) { const d = t - CI[i].n; if (d > 0 && d < .5) fl = Math.max(fl, .34 * (1 - d / .5)); } return fl; })(); flash.style.opacity = fl_; });

// câmera ------------------------------------------------------------------------------------------------------
const K = [], P = (t, p, l, f = 38) => K.push({ t, p, l, f }), cut = (t, p, l, f) => { const a = K[K.length - 1]; if (a) P(t - .02, a.p, a.l, a.f); P(t + .02, p, l, f); };
const c0 = tk('tem', 0, .55);
P(0, [10.5, 19.6, 11], [7.2, 17.4, -1.2]); P(tk('todo', 0) - .1, [10.5, 18.6, 12], [7.2, 16.4, -1.2]); P(tk('escada', 0) + .1, [16, 16, 56], [0, 15.4, -2]);
cut(c0, [7.6, 2.2, 8.5], [4.4, 1.05, -1.2]); P(fim(0), [7.2, 2, 7.6], [4.6, 1.1, -1.2]);
cut(F(1), [-7, 15, 54], [-1.6, 15, -2]); P(T1.ab - .1, [-3, 15.5, 56], [-1.6, 15, -2]);
cut(T1.ab, [-1.6, 1.4, 15], [-1.6, -.8, -2]); P(T1.co, [-1.6, 2.2, 15.5], [-1.6, 0, -2]); P(T1.to, [-3.4, 18, 19], [-1.6, 20, -2]); P(CI[1].n - .05, [-4, 26, 19], [-1.6, 27, -2]); P(CI[1].n + .25, [8, 17, 56], [-.6, 15.6, -2]); P(fim(1), [6, 17, 53], [-.6, 15.6, -2]);
cut(F(2), [2.4, 11.6, 13.5], [-1.5, 11.2, -2]); P(T2.e, [2, 11.2, 12], [-1.4, 10.8, -2]); P(T2.tr + 1, [3.5, 16, 20], [-1.4, 17, -2]); P(T2.de, [3.2, 13, 15], [-1, 13, -2]); P(CI[2].n, [3.6, 21, 15], [-1, 20, -2]); P(fim(2), [4.2, 14, 22], [-1, 15, -2]);
cut(F(3), [6, 32, 16], [-.8, 29, -2]); P(T3.ca - .05, [5.4, 31.6, 15], [-.8, 29, -2]);
cut(T3.ca + .02, [3, 24, 13], [-1, 26, -2]); P(T3.ro - .12, [3, 27, 14], [-1, 28, -2]); cut(T3.ro, [3, 34.6, 8], [-2, 33, -2]); P(T3.mo, [3.8, 34.4, 7.4], [-2.1, 33, -2.4]); P(T3.n, [4.4, 34.2, 7.6], [-1.9, 33, -2.4]); P(fim(3), [5, 34.4, 8], [-1.8, 33, -2.4]);
cut(F(4), [4, 34.2, 6.2], [-2.3, 33, -2.2]); P(T4.e, [4.2, 34.4, 5.8], [-2.3, 33, -2.2]); cut(T4.e + .02, [5.4, 27, 13], [-2.2, 27.5, -2]); P(T4.bl + .55, [5, 28, 12], [-2.4, 27.5, -2]); cut(T4.de - .04, [12, 16.6, 58], [-1.2, 16.6, -2]); P(fim(4), [11, 17, 54], [-1.2, 17, -2]);
cut(F(5), [3.6, 34.4, 9], [-1.2, 32, -2]); P(tQ - .02, [3.4, 34, 8.2], [-1.2, 31.8, -2]); cut(tQ + .24, [4, 26, 15], [-1, 22, -2]); P(T5.e, [4.2, 8, 16], [-1, 7, -2]);
cut(T5.e + .02, [3, 18.3, 5.6], [-1, 18.6, -1.6]); P(T5.tv, [2.8, 18, 5], [-1, 18.6, -1.6]); P(T5.tv + .6, [3.4, 15.2, 6.4], [-1, 15.8, -1.6]); P(fim(5), [4, 15.2, 7.6], [-1, 16, -1.6]);
cut(F(6), [5.4, 1.2, 12.5], [-1, -.4, -2]); P(T6.e, [5, 1.5, 11.6], [-1, -.6, -2]); P(T6.mo, [3.4, .8, 8.6], [-1, -1.2, -2]); P(T6.n, [3.2, .4, 8.2], [-1, -1.4, -2]); P(fim(6), [3.8, 1, 9.4], [-1, -.8, -2]);
cut(F(7), [4.8, yA(5) + 1.8, 1.4], [.1, yA(5) + .9, -1.6], 46); P(T7.po - .1, [4.4, yA(5) + 1.9, 1], [.1, yA(5) + .7, -1.6], 46); cut(T7.po + .1, [17, 15.6, 21], [.3, 15.6, -1.6], 44); P(T7.ab - .1, [15, 16, 19], [.3, 16, -1.6], 44); cut(T7.ab + .02, [4.3, yA(5) + 1.5, -.5], [.3, yA(5) + 1.2, -1.6], 50); P(fim(7), [4.1, yA(5) + 1.5, -.7], [.3, yA(5) + 1.2, -1.6], 50);
cut(F(8), [10, 16, 52], [-.4, 16.4, -2]); P(T8.e, [9, 16, 50], [-.4, 16.4, -2]); cut(T8.bo - .05, [3, yA(5) + 1.7, 3], [.3, yA(5) + 1.3, -.4]); P(T8.co - .05, [2.8, yA(5) + 1.5, 2.8], [.3, yA(5) + 1.3, -.4]); cut(T8.co, [3.2, YM + 2.2, 3], [2, YM + 1.7, -3.8]); P(T8.pa - .05, [3, YM + 2, 2.2], [2, YM + 1.7, -3.8]); cut(T8.pa, [7, 15.6, 50], [-.2, 15.6, -2]); P(fim(8), [5, 15.8, 47], [-.2, 15.6, -2]);
cut(F(N - 1), [6.4, 2.4, 8.5], [.6, 1.4, -1.6]); P(tU0 + .1, [5.6, 2.8, 9], [-.6, 1.6, -1.6]); P(T_USO - .1, [8, 16, 38], [-.6, 16, -2]); P(T_USO + 1.6, [14, 24, 66], [0, 17, -2]); P(T_USO + 5, [30, 40, 120], [0, 24, -6]); P(D.total + 1, [36, 58, 168], [0, 30, -20]);
K.sort((a, b) => a.t - b.t); for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01;

// rótulos e sons ----------------------------------------------------------------------------------------------
const NOM = ['', 'POÇO', 'GUIAS', 'MÁQUINA DE TRAÇÃO', 'CONTRAPESO', 'FREIO DE SEGURANÇA', 'AMORTECEDOR', 'PORTAS DE PAVIMENTO', 'COMANDO'];
for (let i = 1; i < N - 1; i++) { const a = CI[i].n, e = rotulo(NOM[i], [540, 400], a, fim(i), 'grande'); e.style.fontSize = NOM[i].length > 16 ? '62px' : NOM[i].length > 12 ? '72px' : '88px'; e.style.transform += ' rotate(-3deg)'; som(a, 'ding'); som(a, 'whoosh'); }
const avisos = [['SEM ELEVADOR', .15, c0 - .1], ['NÃO CONSEGUE SUBIR', c0 + .1, fim(0)], ['BATE NAS PAREDES', F(2) + .15, T2.e], ['MOTOR SOBRECARREGADO', F(4) + .3, T4.bl - .1], ['CABOS ROMPIDOS', tQ + .12, T5.e], ['PASSOU DO TÉRREO', T6.te + .2, T6.e], ['POÇO ABERTO', tk('cair', 7) - .1, T7.e]]; avisos.forEach(([x, a, b]) => { rotulo(x, [540, 400], a, b, 'grande').style.cssText += ';font-size:64px;color:#ff5a4f'; });
rotulo('ELEVADOR PRONTO!', [540, 400], F(N - 1) + .1, D.total + 1, 'grande').style.fontSize = '82px';
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); for (let q = T_USO; q < D.total; q += 1.4) som(q, 'zumbido');
window.CAPA_T = T_USO + 2.4;
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); AUTO.forEach(f => f(t)); });
