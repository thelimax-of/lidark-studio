// Estádio em tamanho real: estacas, pilares, arquibancada, rampas, treliças, cobertura, drenos, gramado, cadeiras e refletores; no fim, torcida lotada num jogo à noite.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, tex, boneco, camTo, iniciar, som, rotulo, D } = K3;
const E = window.ESPEC, V_ = E.variante, rnd = prng(E.semente ?? 31), F = K3.fala, dur = i => D.falas[i].dur, fim = i => F(i) + dur(i), AUTO = [], LAST = D.falas.length - 1;
const norm = s => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]/g, '');
const tk = (w, i) => { const k = norm(w), q = D.falas[i].words.find(p => norm(p.w) === k); return q ? q.start : F(i) + dur(i) * .12; };
const ult = D.falas[LAST], nPal = ult.texto.split(/[!.]/)[0].trim().split(/\s+/).length, T_USO = (ult.words[nPal - 1]?.end ?? ult.t + ult.dur) + .15;
cam.near = .5; cam.far = 4000;
const O = new THREE.Object3D(), COR = new THREE.Color(), V3 = THREE.Vector3, PI = Math.PI;

// peças: geometrias com base em y, fundidas com cor por vértice -----------------------------------------
const gb = (w, h, d, x = 0, y = 0, z = 0) => new THREE.BoxGeometry(w, h, d).translate(x, y + h / 2, z);
const gc = (a, b, h, n = 12, x = 0, y = 0, z = 0) => new THREE.CylinderGeometry(a, b, h, n).translate(x, y + h / 2, z);
const chato = g => { const q = g.index ? g.toNonIndexed() : g; q.computeVertexNormals(); return q; };
const barraG = (a, b, s) => { const A = new V3(...a), B = new V3(...b), g = new THREE.BoxGeometry(s, A.distanceTo(B), s); g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new V3(0, 1, 0), B.clone().sub(A).normalize())); const M = A.clone().add(B).multiplyScalar(.5); return g.translate(M.x, M.y, M.z); };
function funde(l) {
  const P = [], N = [], C = [];
  l.forEach(([g, c]) => { const q = g.index ? g.toNonIndexed() : g, p = q.attributes.position, n = q.attributes.normal; COR.set(c ?? 0xffffff); for (let i = 0; i < p.count; i++) { P.push(p.getX(i), p.getY(i), p.getZ(i)); N.push(n.getX(i), n.getY(i), n.getZ(i)); C.push(COR.r, COR.g, COR.b); } });
  const r = new THREE.BufferGeometry(); r.setAttribute('position', new THREE.Float32BufferAttribute(P, 3)); r.setAttribute('normal', new THREE.Float32BufferAttribute(N, 3)); r.setAttribute('color', new THREE.Float32BufferAttribute(C, 3)); return r;
}
const mV = mat(0xffffff, { vertexColors: true });
const UNI = gb(1, 1, 1);

// frota: instâncias que entram no tempo. t entrada, d duração, t2 saída. modos: pop, sobe, desce, estica
function frota(geo, material, itens, o = {}) {
  const n = itens.length, im = new THREE.InstancedMesh(geo, material, Math.max(n, 1)); im.frustumCulled = false; im.castShadow = o.sombra !== false; im.receiveShadow = o.recebe !== false; add(im); im.count = n;
  const A = im.instanceMatrix.array, dur = o.d ?? .35, modo = o.modo || 'pop'; let tA = 1e9, tZ = -1e9;
  itens.forEach((b, i) => { b.sx ??= 1; b.sy ??= 1; b.sz ??= 1; b.y ??= 0; b.ry ??= 0; b.t ??= -5; COR.set(b.c ?? 0xffffff); im.setColorAt(i, COR); tA = Math.min(tA, b.t); tZ = Math.max(tZ, b.t + (b.d ?? dur), b.t2 != null ? b.t2 + .4 : -1e9); });
  if (n) im.instanceColor.needsUpdate = true;
  const poe = (i, b, t) => {
    let k = (t - b.t) / (b.d ?? dur), s = 1, y = b.y, ex = 1, m = b.m || modo;
    if (k <= 0) s = 0; else if (b.t2 != null && t > b.t2) s = 1 - clamp((t - b.t2) / .4);
    else if (k < 1) { if (m === 'pop') s = Math.max(back(k), .001); else if (m === 'sobe') y -= (b.sub ?? b.sy) * (1 - ease(k)); else if (m === 'desce') y += (1 - ease(k)) * (b.dy ?? 4); else if (m === 'estica') ex = Math.max(ease(k), .001); }
    const c = Math.cos(b.ry), z = Math.sin(b.ry), sx = b.sx * s * ex, sy = b.sy * s, sz = b.sz * s, j = i * 16;
    A[j] = sx * c; A[j + 1] = 0; A[j + 2] = -sx * z; A[j + 3] = 0; A[j + 4] = 0; A[j + 5] = sy; A[j + 6] = 0; A[j + 7] = 0; A[j + 8] = sz * z; A[j + 9] = 0; A[j + 10] = sz * c; A[j + 11] = 0; A[j + 12] = b.x; A[j + 13] = y; A[j + 14] = b.z; A[j + 15] = 1;
  };
  itens.forEach((b, i) => poe(i, b, -1e9)); let last = -1e9;
  AUTO.push(t => { if (o.de != null || o.ate != null) im.visible = t >= (o.de ?? -1e9) && t < (o.ate ?? 1e9); if (!((t < tA && last < tA) || (t > tZ && last > tZ))) { itens.forEach((b, i) => poe(i, b, t)); im.instanceMatrix.needsUpdate = true; } last = t; });
  return im;
}
// barras finas em qualquer direção: cabos, fios, tubos
function cabos(itens, cor, raio, o = {}) {
  const im = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1).translate(0, .5, 0), o.mat || mat(cor, { roughness: .5 }), itens.length); im.frustumCulled = false; im.castShadow = o.sombra === true; add(im); const dur = o.d ?? .25, Y = new V3(0, 1, 0); let tZ = -1e9, tA = 1e9, last = -1e9;
  itens.forEach(b => { b.A = new V3(...b.a); const B = new V3(...b.b); b.L = b.A.distanceTo(B); b.q = new THREE.Quaternion().setFromUnitVectors(Y, B.sub(b.A).normalize()); b.t ??= -5; tZ = Math.max(tZ, b.t + dur); tA = Math.min(tA, b.t); }); O.scale.setScalar(0); O.position.set(0, 0, 0); O.quaternion.identity(); O.updateMatrix(); itens.forEach((b, i) => im.setMatrixAt(i, O.matrix));
  AUTO.push(t => { if (o.de != null || o.ate != null) im.visible = t >= (o.de ?? -1e9) && t < (o.ate ?? 1e9); if ((t < tA && last < tA) || (t > tZ && last > tZ)) { last = t; return; } itens.forEach((b, i) => { const k = ease((t - b.t) / dur); O.position.copy(b.A); O.quaternion.copy(b.q); O.scale.set(raio, Math.max(b.L * k, .0001), raio); O.updateMatrix(); im.setMatrixAt(i, O.matrix); }); im.instanceMatrix.needsUpdate = true; last = t; });
  return im;
}
const curva = (a, b, f, n) => { const r = []; for (let i = 0; i <= n; i++) { const u = i / n; r.push([a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u - f * 4 * u * (1 - u), a[2] + (b[2] - a[2]) * u]); } return r; };
// objeto único que entra
const aparece = (o, t0, d = .4, modo = 'pop', dy = 4) => { const s = o.scale.clone(), y = o.position.y; o.visible = false; AUTO.push(t => { const k = (t - t0) / d; o.visible = t >= t0; if (!o.visible) return; if (k >= 1) { o.scale.copy(s); o.position.y = y; return; } if (modo === 'pop') o.scale.copy(s).multiplyScalar(Math.max(back(k), .01)); else o.position.y = y + (1 - ease(k)) * dy; }); return o; };
const unico = (geo, x, y, z, ry = 0) => { const m = sh(new THREE.Mesh(geo, mV)); add(m); m.position.set(x, y, z); m.rotation.y = ry; return m; };

// janelas: mapa de dia e mapa aceso
const R_J = prng(77), ACESA = []; for (let i = 0; i < 64; i++) ACESA.push(R_J() < .66 ? ['#ffd98a', '#ffc65c', '#fff0c4', '#ffb347'][Math.floor(R_J() * 4)] : null);
const janela = (g, w, f) => { const c = w / 8; for (let a = 0; a < 8; a++) for (let b = 0; b < 8; b++) f(g, a * c + c * .2, b * c + c * .2, c * .6, c * .62, ACESA[a + b * 8]); };
const mapaP = tex(256, 256, (g, w) => { g.fillStyle = '#fff'; g.fillRect(0, 0, w, w); janela(g, w, (q, x, y, a, b) => { q.fillStyle = '#3d5f82'; q.fillRect(x, y, a, b); q.fillStyle = '#7fb4d8'; q.fillRect(x, y, a * .4, b); }); });
const luzP = tex(256, 256, (g, w) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, w); janela(g, w, (q, x, y, a, b, c) => { if (c) { q.fillStyle = c; q.fillRect(x, y, a, b); } }); });
const mPred = new THREE.MeshStandardMaterial({ map: mapaP, emissiveMap: luzP, emissive: 0xffffff, emissiveIntensity: 0, roughness: .55 });
const geoPred = (nx, ny) => { const g = new THREE.BoxGeometry(1, 1, 1).translate(0, .5, 0), u = g.attributes.uv; for (let i = 0; i < u.count; i++) { if (i >= 8 && i < 16) u.setXY(i, .004, .004); else u.setXY(i, u.getX(i) * nx / 8, u.getY(i) * ny / 8); } return g; };
const UC = { value: -1e5 }, CORTE = m => { m.onBeforeCompile = sh_ => { sh_.uniforms.uCorte = UC; sh_.vertexShader = 'varying float vZW;\n' + sh_.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n vZW = (modelMatrix * instanceMatrix * vec4(position, 1.)).z;'); sh_.fragmentShader = 'uniform float uCorte; varying float vZW;\n' + sh_.fragmentShader; if (m.isMeshStandardMaterial) sh_.fragmentShader = sh_.fragmentShader.replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\n totalEmissiveRadiance *= step(uCorte, vZW);'); else sh_.fragmentShader = sh_.fragmentShader.replace('#include <color_fragment>', '#include <color_fragment>\n diffuseColor.a *= step(uCorte, vZW);'); }; }; CORTE(mPred);
const GP = [geoPred(4, 5), geoPred(5, 12), geoPred(5, 26)];
const ACENDE = []; // funções k -> liga as luzes
function predios(lista, o = {}) { // {x,z,w,d,h,c,t,ry,y0}
  const cl = [[], [], []], topo = [];
  lista.forEach(b => { const q = { x: b.x, y: b.y0 ?? 0, z: b.z, sx: b.w, sz: b.d, sy: b.h, sub: b.h, ry: b.ry ?? 0, t: b.t, c: b.c, t2: b.t2 }; cl[b.h < 11 ? 0 : b.h < 26 ? 1 : 2].push(q); topo.push({ x: b.x, y: (b.y0 ?? 0) + b.h, z: b.z, sx: b.w * .92, sy: .5, sz: b.d * .92, sub: b.h + 2, ry: b.ry ?? 0, t: b.t, c: 0xc9ccd2, t2: b.t2 }); topo.push({ x: b.x + b.w * .2, y: (b.y0 ?? 0) + b.h + .5, z: b.z - b.d * .15, sx: b.w * .3, sy: 1.1, sz: b.d * .3, sub: b.h + 4, ry: b.ry ?? 0, t: b.t, c: 0x8d95a2, t2: b.t2 }); });
  cl.forEach((c, i) => { if (c.length) frota(GP[i], mPred, c, { modo: 'sobe', d: o.d ?? .9, ...o }); }); frota(UNI, mat(0xffffff), topo, { modo: 'sobe', d: o.d ?? .9, ...o });
}
// casas
const JANC = (() => { const a = gb(.42, .42, .05, -.55, .7, 1.03), b = gb(.42, .42, .05, .55, .7, 1.03), c = gb(.42, .42, .05, -.55, .7, -1.03), d = gb(.42, .42, .05, .55, .7, -1.03); return funde([[a], [b], [c], [d]]); })();
const G_PAR = funde([[gb(2.5, 1.5, 2)], [gb(.5, .95, .05, 0, 0, 1.02), 0x7a4a26], [gb(.46, .46, .05, -.72, .62, 1.02), 0x7fbcd9], [gb(.46, .46, .05, .72, .62, 1.02), 0x7fbcd9], [gb(.46, .46, .05, -.55, .68, -1.02), 0x7fbcd9], [gb(.46, .46, .05, .55, .68, -1.02), 0x7fbcd9]]);
const G_TEL = (() => { const g = new THREE.ConeGeometry(2.05, 1.05, 4).rotateY(.785398); g.scale(1.06, 1, .86); g.translate(0, 2.02, 0); return chato(g); })();
const mJan = new THREE.MeshBasicMaterial({ color: 0xffd27a, toneMapped: false, transparent: true, opacity: 0 });
CORTE(mJan);
const C_PAR = [0xf2e6c9, 0xa9c9e8, 0xf2b8c6, 0xd6e6c0, 0xf0dba0, 0xeab0a6, 0xbfe0ef, 0xd8d0e8, 0xf6f1e4], C_TEL = [0xc2502f, 0xb5482f, 0x8c5a3c, 0xd16a3a, 0x9a4a3a];
const corDe = l => l[Math.floor(rnd() * l.length)];
function casas(l, o = {}) { // {x,z,ry,s,t,t2}
  const P_ = [], T_ = [], J_ = []; l.forEach(b => { const s = b.s ?? 1, q = { x: b.x, y: b.y ?? 0, z: b.z, ry: b.ry ?? 0, sx: s, sy: s * (b.alto ?? 1), sz: s, t: b.t, t2: b.t2 }; P_.push({ ...q, c: b.c ?? corDe(C_PAR) }); T_.push({ ...q, c: b.tc ?? corDe(C_TEL) }); J_.push({ ...q, c: rnd() > .3 ? 0xffffff : 0x7a6a50 }); });
  const a = frota(G_PAR, mV, P_, o), b = frota(G_TEL, mat(0xffffff, { roughness: .7 }), T_, o), c = frota(JANC, mJan, J_, { ...o, sombra: false, recebe: false }); return [a, b, c];
}
// árvores
const G_ARV = funde([[gc(.13, .2, 1, 6), 0x7a5a3a], [new THREE.IcosahedronGeometry(.95, 0).translate(0, 1.5, 0)], [new THREE.IcosahedronGeometry(.7, 0).translate(.45, 1.15, .2)], [new THREE.IcosahedronGeometry(.62, 0).translate(-.4, 1.2, -.25)]]);
const G_PIN = funde([[gc(.14, .2, .9, 6), 0x7a5a3a], [chato(new THREE.ConeGeometry(1.05, 1.5, 7).translate(0, 1.4, 0))], [chato(new THREE.ConeGeometry(.82, 1.3, 7).translate(0, 2.05, 0))], [chato(new THREE.ConeGeometry(.56, 1.1, 7).translate(0, 2.7, 0))]]);
const C_ARV = [0x2e8f3e, 0x3aa84a, 0x237a35, 0x4fb04f, 0x2f9f55];
function arvores(l, o = {}) { const a = [], b = []; l.forEach(q => { const s = q.s ?? 1; (q.pinho ? b : a).push({ x: q.x, z: q.z, y: q.y ?? 0, sx: s, sy: s, sz: s, ry: rnd() * 6.28, t: q.t, t2: q.t2, c: corDe(C_ARV) }); }); if (a.length) frota(G_ARV, mV, a, o); if (b.length) frota(G_PIN, mV, b, o); }
// veículos e o que se move sempre: fn(i,t) -> [x,y,z,ry] ou null
const G_CAR = funde([[gb(.84, .34, 1.8, 0, .14)], [gb(.74, .32, .95, 0, .48, -.05), 0xaee3f7], [gb(.86, .16, 1.82, 0, 0), 0x24262a]]);
const G_ONI = funde([[gb(1.05, .95, 3.4, 0, .16)], [gb(1.08, .34, 3.2, 0, .62), 0xaee3f7], [gb(1.06, .16, 3.42), 0x24262a]]);
const G_CAM = funde([[gb(1.05, 1.15, 2.2, 0, .2, -.7), 0xf4efe6], [gb(1.05, .85, .95, 0, .2, 1.05)], [gb(.95, .34, .08, 0, .66, 1.52), 0xaee3f7], [gb(1.08, .2, 3.3), 0x24262a]]);
function moveis(geo, n, cores, fn, o = {}) {
  const im = new THREE.InstancedMesh(geo, o.mat || mV, n); im.frustumCulled = false; im.castShadow = o.sombra !== false; add(im); for (let i = 0; i < n; i++) { COR.set(cores[i % cores.length]); im.setColorAt(i, COR); } im.instanceColor.needsUpdate = true; const de = o.de ?? -1e9, ate = o.ate ?? 1e9, luz = o.luz;
  AUTO.push(t => { const v = t >= de && t < ate; im.visible = v; if (luz) luz.p.visible = v && luz.p.material.opacity > .004; if (!v) return; for (let i = 0; i < n; i++) { const p = fn(i, t), s = p ? (o.esc ?? 1) : 0; if (!p) { O.position.set(0, -50, 0); O.scale.setScalar(0); } else { O.position.set(p[0], p[1], p[2]); O.scale.setScalar(s); } O.rotation.set(0, p ? p[3] : 0, p ? (p[4] || 0) : 0); O.updateMatrix(); im.setMatrixAt(i, O.matrix); if (luz) { luz.pos[i * 3] = O.position.x; luz.pos[i * 3 + 1] = O.position.y + .5; luz.pos[i * 3 + 2] = O.position.z; } } im.instanceMatrix.needsUpdate = true; if (luz) luz.sync(); });
  return im;
}
// brilhos: pontos que somam luz; dão o aspecto de cidade de noite sem pós-processo
const TX_G = tex(64, 64, (g, w) => { g.clearRect(0, 0, w, w); const r = g.createRadialGradient(w / 2, w / 2, 0, w / 2, w / 2, w / 2); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(.25, 'rgba(255,255,255,.75)'); r.addColorStop(.55, 'rgba(255,255,255,.18)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, w, w); });
function brilhos(pts, cor, tam, o = {}) {
  const pos = new Float32Array(pts.length * 3), g = new THREE.BufferGeometry(); pts.forEach((p, i) => { pos[i * 3] = p[0]; pos[i * 3 + 1] = p[1]; pos[i * 3 + 2] = p[2]; }); g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  if (o.cores) { const c = new Float32Array(pts.length * 3); pts.forEach((p, i) => { COR.set(o.cores[i % o.cores.length]); c[i * 3] = COR.r; c[i * 3 + 1] = COR.g; c[i * 3 + 2] = COR.b; }); g.setAttribute('color', new THREE.BufferAttribute(c, 3)); }
  const m = new THREE.PointsMaterial({ size: tam, map: TX_G, color: cor, transparent: true, opacity: o.op ?? 0, blending: o.normal ? THREE.NormalBlending : THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true, vertexColors: !!o.cores, toneMapped: false }), p = new THREE.Points(g, m); p.frustumCulled = false; p.visible = (o.op ?? 0) > 0; add(p);
  return { p, pos, op: k => { m.opacity = k; p.visible = k > .004; }, conta: n => g.setDrawRange(0, n), sync: () => { g.attributes.position.needsUpdate = true; } };
}
// pulsos correndo por caminhos: água, esgoto, energia. Avançam até a frente, que abre em rev segundos
function pulsos(cams, n, cor, tam, t0, t1, vel = .25, rev = 2.5, o = {}) {
  const b = brilhos(Array.from({ length: n }, () => [0, -99, 0]), cor, tam, { normal: !o.soma }), L = cams.map(c => c.length - 1), f = o.forte ?? 1;
  AUTO.push(t => { const on = t >= t0 && t < t1; if (!on) { b.op(0); return; } b.op(f * clamp((t - t0) / .4) * clamp((t1 - t) / .5)); const fr = clamp((t - t0) / rev) * 1.02; for (let i = 0; i < n; i++) { const c = i % cams.length, u = (i * .3819 + t * vel * (o.inverte ? -1 : 1) + 100) % 1; if (u > fr) { b.pos[i * 3 + 1] = -99; continue; } const q = u * L[c], a = Math.floor(q), e = q - a, A = cams[c][a], B = cams[c][Math.min(a + 1, L[c])]; b.pos[i * 3] = A[0] + (B[0] - A[0]) * e; b.pos[i * 3 + 1] = A[1] + (B[1] - A[1]) * e; b.pos[i * 3 + 2] = A[2] + (B[2] - A[2]) * e; } b.sync(); });
  return b;
}
function chuva(n, t0, t1, alvo, l = 40, h = 40, cmp = 1.2) {
  const m = new THREE.InstancedMesh(new THREE.BoxGeometry(.05 * cmp, 1.2 * cmp, .05 * cmp), new THREE.MeshBasicMaterial({ color: 0xcfe6f7, transparent: true, opacity: .55 }), n); m.frustumCulled = false; add(m); const L = []; for (let i = 0; i < n; i++) L.push([rnd() - .5, rnd(), rnd() - .5, rnd() * 3]);
  AUTO.push(t => { const on = t >= t0 && t < t1; m.visible = on; if (!on) return; const c = alvo(t); L.forEach(([x, u, z, p], i) => { const q = ((u - t * 1.6 + p) % 1 + 1) % 1; O.position.set(c[0] + x * l, q * h, c[2] + z * l); O.rotation.set(0, 0, .06); O.scale.setScalar(1); O.updateMatrix(); m.setMatrixAt(i, O.matrix); }); m.instanceMatrix.needsUpdate = true; });
}
function fogos(t0, t1, n, area, base, alt, tamF = 30, raio = 48) {
  const POR = 44, N = n * POR, b = brilhos(Array.from({ length: N }, () => [0, -99, 0]), 0xffffff, tamF, { cores: [0xff5a5a, 0xffd23f, 0x6fd3ff, 0x8dff9a, 0xff8ae2, 0xffffff] }), S_ = []; const r = prng(4242); for (let i = 0; i < n; i++) S_.push({ t: t0 + (t1 - t0) * (i / n), x: (r() - .5) * area, z: (r() - .5) * area, y: base + r() * alt });
  const dirs = []; for (let i = 0; i < POR; i++) { const z = 1 - 2 * (i + .5) / POR, a = i * 2.39996, q = Math.sqrt(1 - z * z); dirs.push([q * Math.cos(a), z, q * Math.sin(a)]); }
  AUTO.push(t => { if (t < t0) { b.op(0); return; } b.op(1); S_.forEach((s, i) => { const q = t - s.t; dirs.forEach((d, j) => { const k = (i * POR + j) * 3, v = q >= 0 && q < 1.7, e = 1 - Math.exp(-q * 2.6); b.pos[k] = s.x + d[0] * raio * e; b.pos[k + 1] = v ? s.y + d[1] * raio * e - q * q * 5 : -99; b.pos[k + 2] = s.z + d[2] * raio * e; }); }); b.sync(); });
}

// operário de capacete e martelo
function operario(S = 1, camisa = 0x2fbf8f) {
  const h = boneco({ cabeca: 'bloco', camisa, calca: 0x2b3a67, sapato: 0xe9e4d8, cabelo: 0x3a2a1e }); h.scale.setScalar(S); add(h); const r = h.r;
  const cap = new THREE.Group(); r.cab.add(cap); add(box(.47, .15, .45, 0xffc61a, .05), cap).position.y = .33; add(box(.32, .03, .2, 0xffc61a, .012), cap).position.set(0, .28, .3);
  const mart = new THREE.Group(); r.bd.k.add(mart); mart.position.y = -.38; add(box(.05, .36, .05, 0x7a4a26, .012), mart).position.y = -.1; add(box(.2, .1, .1, 0x5e6a78, .02), mart).position.y = -.3; mart.rotation.x = 1.4;
  return { h, r, mart, S };
}
// roteiro: [t, x, z, y, olhar, gesto]; gesto: 'bate' (padrão), 'para', 'pasmo'
function roteiro(op, RT, tFim) {
  const { h, r } = op, v = 3.2 * op.S;
  AUTO.push(t => { if (t >= tFim) return; let i = 0; while (i < RT.length - 2 && t >= RT[i + 1][0]) i++; const a = RT[i], b = RT[i + 1], y0 = a[3] ?? 0, y1 = b[3] ?? 0, d = Math.hypot(b[1] - a[1], b[2] - a[2], y1 - y0), dur = Math.max(.4, d / v), k = b[6] ? 0 : clamp((t - a[0]) / dur), mov = k > 0 && k < 1 && d > .05; h.position.set(a[1] + (b[1] - a[1]) * k, y0 + (y1 - y0) * k, a[2] + (b[2] - a[2]) * k); h.scale.setScalar(op.S); r.be.j.rotation.set(0, 0, 0); r.bd.j.rotation.set(0, 0, 0); r.be.k.rotation.x = 0; r.bd.k.rotation.x = 0;
    if (mov) { h.rotation.y = Math.atan2(b[1] - a[1], b[2] - a[2]); r.anda(t); return; }
    r.anda(0, 0); r.respira(t); const g = (k >= 1 ? b[5] : a[5]) ?? 'bate'; h.rotation.y = (k >= 1 ? b[4] : a[4]) ?? .4; if (g === 'bate') { const w = Math.sin(t * 8); r.bd.j.rotation.x = -2.35 + w * .42; r.bd.k.rotation.x = -.25; } else if (g === 'puxa') { const w = Math.sin(t * 5); r.be.j.rotation.x = -1.5 + w * .55; r.bd.j.rotation.x = -1.5 - w * .55; r.be.k.rotation.x = -.5; r.bd.k.rotation.x = -.5; } else if (g === 'pasmo') { const w = Math.sin(t * 7); r.be.j.rotation.x = -2.6 + w * .12; r.bd.j.rotation.x = -2.6 - w * .12; r.be.k.rotation.x = -1.2; r.bd.k.rotation.x = -1.2; } });
}
const festa = (op, x, z, ry, t0, y = 0) => AUTO.push(t => { if (t < t0) return; const { h, r, mart } = op; h.position.set(x, y, z); h.rotation.y = ry; r.anda(0, 0); mart.visible = false; const w = Math.sin(t * 6); r.be.j.rotation.set(-2.7 + w * .15, 0, 0); r.bd.j.rotation.set(-2.7 - w * .15, 0, 0); r.be.k.rotation.x = r.bd.k.rotation.x = 0; });

// céu, sol, noite ----------------------------------------------------------------------------------------
let sol, hemi, AREA = 100; const cvCeu = document.createElement('canvas'); cvCeu.width = 8; cvCeu.height = 256; const ctxCeu = cvCeu.getContext('2d'), txCeu = new THREE.CanvasTexture(cvCeu); txCeu.colorSpace = THREE.SRGBColorSpace;
const pintaCeu = (a, b) => { const l = ctxCeu.createLinearGradient(0, 0, 0, 256); l.addColorStop(0, '#' + a.getHexString()); l.addColorStop(.75, '#' + b.getHexString()); ctxCeu.fillStyle = l; ctxCeu.fillRect(0, 0, 8, 256); txCeu.needsUpdate = true; };
const CC = { a: new THREE.Color(V_.ceu[0]), b: new THREE.Color(V_.ceu[1]), na: new THREE.Color('#070c22'), nb: new THREE.Color('#27305e'), ca: new THREE.Color(), cb: new THREE.Color(), s0: new THREE.Color(V_.sol), s1: new THREE.Color(0x9fb6ee) }; let kN = -1;
function cenario(area, n0, n1) { AREA = area; sol = luzes(V_.sol, 0xd8ecff, 0x90b870, 2.7, area); add(sol.target); hemi = scene.children.find(q => q.isHemisphereLight); scene.environmentIntensity = .3; scene.background = txCeu; scene.fog = new THREE.Fog(new THREE.Color(V_.ceu[1]), n0, n1); sol.shadow.camera.far = area * 5; sol.shadow.camera.updateProjectionMatrix(); return sol; }
function noite(k) { if (Math.abs(k - kN) < .002) return; kN = k; CC.ca.lerpColors(CC.a, CC.na, k); CC.cb.lerpColors(CC.b, CC.nb, k); pintaCeu(CC.ca, CC.cb); scene.fog.color.copy(CC.cb); sol.intensity = 2.7 - k * 2.15; sol.color.lerpColors(CC.s0, CC.s1, k); hemi.intensity = 1.25 - k * .78; hemi.color.lerpColors(new THREE.Color(0xd8ecff), new THREE.Color(0x6a7fd0), k); scene.environmentIntensity = .3 - k * .2; }
const segueSol = (x, z) => { sol.target.position.set(x, 0, z); sol.position.set(x + AREA * .6, AREA, z + AREA * .55); };
function acende(k) { mPred.emissiveIntensity = k * 1.9; mJan.opacity = k; ACENDE.forEach(f => f(k)); }

// etiqueta dourada fixa na tela: o mundo é grande demais para prender rótulo num ponto
const etq = (txt, t0, t1, e = 'ouro') => { const el = rotulo(txt, [540, 330], t0, t1, 'grande'); el.style.fontSize = e === 'grande' ? '82px' : '66px'; el.style.webkitTextStroke = '11px #111'; if (e === 'ruim') { el.style.color = '#ff4b4b'; el.style.webkitTextStroke = '10px #fff'; } if (e === 'ouro') som(t0, 'ding'); };
// câmera: [pos, alvo, corte?]; um plano por fala, com aproximação lenta
function plano(V, F_) { const K = []; V.forEach(([p, l, c, pF, lF], i) => { const pf = pF || p.map((v, j) => l[j] + (v - l[j]) * .9); if (i) K.push({ ...K[K.length - 1], t: F(i) + .02 }); K.push({ t: F(i) + (i && !c ? .9 : .04), p, l, f: 34 }); K.push({ t: fim(i) + .1, p: pf, l: lF || l, f: 34 }); }); F_.forEach(q => K.push({ f: 34, ...q })); K.sort((a, b) => a.t - b.t); for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01; return K; }
const agua = (w, d, x, z, c, y = .05) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, d), mat(c, { roughness: .18, metalness: .1 }))); m.rotation.x = -PI / 2; m.position.set(x, y, z); m.receiveShadow = true; return m; };
// véu de luz: uma mancha quente sobre a cidade à noite, faz o papel do brilho sem pós-processo
function veu(x, y, z, esc, cor, forca = .4) { const m = new THREE.SpriteMaterial({ map: TX_G, color: cor, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, toneMapped: false }), s = new THREE.Sprite(m); s.position.set(x, y, z); s.scale.setScalar(esc); add(s); ACENDE.push(k => { m.opacity = k * forca; s.visible = k > .01; }); s.visible = false; }
// coloca o operário no quadro: a para a direita, b para perto da câmera, em frações do quadro
const noQuadro = (p, l, a, b) => { const f = new V3(l[0] - p[0], 0, l[2] - p[2]).normalize(), r = new V3(-f.z, 0, f.x), d = Math.hypot(p[0] - l[0], p[1] - l[1], p[2] - l[2]), W = d * .171; return [l[0] + r.x * a * W - f.x * b * W * 2, l[2] + r.z * a * W - f.z * b * W * 2]; };
const olha = (p, x, z, o = .5) => Math.atan2(p[0] - x, p[2] - z) + o;
// Estádio em tamanho real: estacas, pilares, arquibancada, rampas, treliças, cobertura, drenos, gramado, cadeiras e refletores; no fim, torcida lotada num jogo à noite.
cenario(230, 900, 3000);
const T = { est: tk('estacas', 1), pil: tk('pilares', 2), arq: tk('arquibancada', 3), ram: tk('rampas', 4), tre: tk('treliças', 5), cob: tk('cobertura', 6), dre: tk('drenos', 7), gra: tk('gramado', 8), cad: tk('cadeiras', 9), ref: tk('refletores', 10) };
const rest = (t, i) => Math.max(1.2, fim(i) - t - .25);
const CONC = 0xc4c1b8, CONC2 = 0xb2afa6, ACO = 0x8a95a3, AMAR = 0xffc61a, TERRA = 0xa98a62;

// o anel do estádio: curva interna a passos iguais, mais a normal para fora ------------------------------------
const NB = 80, FN = 960, TAB = [];
{ const sp = (c, e) => Math.sign(c) * Math.abs(c) ** e, Q = []; let L = 0, a0 = null; for (let i = 0; i <= 6000; i++) { const a = i / 6000 * PI * 2, x = 62 * sp(Math.cos(a), .58), z = 44 * sp(Math.sin(a), .58); if (a0) L += Math.hypot(x - a0[0], z - a0[1]); a0 = [x, z]; Q.push([x, z, L]); } let j = 0; for (let i = 0; i < FN; i++) { const s = i / FN * L; while (Q[j + 1][2] < s) j++; TAB.push({ x: Q[j][0], z: Q[j][1] }); } for (let i = 0; i < FN; i++) { const a = TAB[(i + FN - 6) % FN], b = TAB[(i + 6) % FN], dx = b.x - a.x, dz = b.z - a.z, n = Math.hypot(dx, dz); TAB[i].nx = dz / n; TAB[i].nz = -dx / n; } }
const pt = (u, o) => { const q = (((u / NB * FN) % FN) + FN) % FN, i = Math.floor(q), e = q - i, a = TAB[i], b = TAB[(i + 1) % FN]; return [a.x + (b.x - a.x) * e + (a.nx + (b.nx - a.nx) * e) * o, a.z + (b.z - a.z) * e + (a.nz + (b.nz - a.nz) * e) * o]; };
const peca = (i, o, x = {}) => { const a = pt(i, o), b = pt(i + 1, o), dx = b[0] - a[0], dz = b[1] - a[1]; return { x: (a[0] + b[0]) / 2, z: (a[1] + b[1]) / 2, ry: Math.atan2(-dz, dx), sx: Math.hypot(dx, dz) + .05, ...x }; };
let HB = 0; { let m = -9; for (let i = 0; i < NB; i++) { const q = TAB[Math.floor(i / NB * FN)], s = q.nx * -.74 + q.nz * -.67; if (s > m) { m = s; HB = i; } } }
const HN = TAB[Math.floor(HB / NB * FN)], HT_ = [-HN.nz, HN.nx], H = (o, d = 0, y = 0) => { const p = pt(HB, 0); return [p[0] + HN.nx * o + HT_[0] * d, y, p[1] + HN.nz * o + HT_[1] * d]; };
const dB = i => Math.min(Math.abs(i - HB), NB - Math.abs(i - HB)) / (NB / 2), ord = i => .3 * dB(i) + .7 * ((i * .618034) % 1);
const NR = 42, oR = r => 3 + r * .8, yR = r => 2.5 + r * .45, yO = o => 2.5 + (o - 3) * .5625, YT = 37;

// chão, ruas e cidade em volta -----------------------------------------------------------------------------------
const gr = add(new THREE.Mesh(new THREE.PlaneGeometry(12000, 12000), mat(V_.grama, { roughness: 1 }))); gr.rotation.x = -PI / 2; gr.receiveShadow = true;
const disco = (rx, rz, c, y) => { const m = add(new THREE.Mesh(new THREE.CircleGeometry(1, 72), mat(c, { roughness: 1 }))); m.rotation.x = -PI / 2; m.scale.set(rx, rz, 1); m.position.y = y; m.receiveShadow = true; return m; };
disco(200, 160, TERRA, .03); const praca = disco(198, 158, 0xcfcdc6, .05); AUTO.push(t => { praca.visible = t >= F(4) + .3; });
{ const m = [], tr = [], VIA = [-430, -310, -190, 190, 310, 430]; VIA.forEach(z => { m.push({ x: 0, z, y: .06, sx: 1500, sy: .06, sz: 11, c: 0x44464e }); for (let x = -740; x < 740; x += 12) tr.push({ x, z, y: .13, sx: 5, sy: .02, sz: .2, c: 0xf2d24a }); });[-560, -430, -240, 240, 430, 560].forEach(x => { m.push({ x, z: 0, y: .07, sx: 11, sy: .06, sz: 1500, c: 0x44464e }); for (let z = -740; z < 740; z += 12) tr.push({ x, z, y: .14, sx: .2, sy: .02, sz: 5, c: 0xf2d24a }); }); frota(UNI, mat(0xffffff), m, { sombra: false }); frota(UNI, mat(0xffffff), tr, { sombra: false, recebe: false });
  const c = [], P_ = [], ar = []; for (let x = -720; x < 720; x += 24) for (let z = -720; z < 720; z += 24) { if (Math.abs(x / 250) ** 3 + Math.abs(z / 195) ** 3 < 1) continue; if (VIA.some(v => Math.abs(z - v) < 16)) continue; if ([-560, -430, -240, 240, 430, 560].some(v => Math.abs(x - v) < 16)) continue; const q = rnd(); if (q < .1) P_.push({ x, z, w: 16, d: 16, h: 14 + rnd() * 34, c: corDe([0xeaeef2, 0x8fc4e0, 0xf1cda0, 0x7fbfb8, 0xe29a7a, 0xb5c0dc, 0xf4efe6]), t: -5 }); else if (q < .78) c.push({ x: x + (rnd() - .5) * 3, z: z + (rnd() - .5) * 3, ry: Math.floor(rnd() * 4) * PI / 2, s: 3.6, t: -5 }); else ar.push({ x, z, s: 3 + rnd() * 2.5, pinho: rnd() > .6, t: -5 }); } casas(c); predios(P_); arvores(ar);
  const fx = []; VIA.forEach(z => fx.push({ z: z - 2.7, a: -700, b: 700 }, { z: z + 2.7, a: 700, b: -700 })); const fC = brilhos(Array.from({ length: 160 }, () => [0, -99, 0]), 0xffffff, 8, { cores: [0xfff2c8, 0xff5a4a] }); moveis(G_CAR, 160, [0xd83a3a, 0x3a7fd8, 0xf2c94c, 0xf4efe6, 0x2fbf8f, 0x30343c], (i, t) => { const l = fx[i % fx.length], u = (i * .618 + t * (.012 + (i % 5) * .002)) % 1; return [l.a + (l.b - l.a) * u, .1, l.z, l.b > l.a ? PI / 2 : -PI / 2]; }, { esc: 2.4, luz: fC }); ACENDE.push(k => fC.op(k * .9));
  const mo = [], cs = [0x5fae62, 0x4f9f58, 0x6dbb6a]; for (let i = 0; i < 18; i++) { const a = i / 18 * 6.28; mo.push({ x: Math.cos(a) * 1500, z: Math.sin(a) * 1500, sx: 420, sy: 160 + rnd() * 100, sz: 300, c: corDe(cs) }); } const mM = mat(0xffffff, { flatShading: true, roughness: 1 }); frota(new THREE.IcosahedronGeometry(1, 1), mM, mo, { sombra: false }); AUTO.push(t => { mM.color.setScalar(1 - .86 * ease((t - F(10) - .1) / 3)); }); }

// abertura: a arquibancada apoiada em terra fofa afunda, racha e despenca -----------------------------------------------
const G_W = (() => { const L = []; for (let r = 0; r < 30; r++) L.push([gb(15, .46, 1, 0, r * .45, -r * .8), r % 2 ? CONC : CONC2]);[3, 9, 15, 20].forEach((o, i) => { [-5.5, 5.5].forEach(x => L.push([gb(.5, Math.max(.6, o * .5625), .5, x, -1 * 0, -o), 0x9a978e])); }); L.push([barraG([-7, .4, 0], [-7, 13, -22], .4), 0x9a978e], [barraG([7, .4, 0], [7, 13, -22], .4), 0x9a978e]); return funde(L); })();
const VEL = []; { for (let j = 0; j < 6; j++) { const u = HB - 8.5 + j * 3.4, a = pt(u, 6), b = pt(u + 3.4, 6), g = new THREE.Group(); g.rotation.order = 'YXZ'; g.position.set((a[0] + b[0]) / 2, .6, (a[1] + b[1]) / 2); g.rotation.y = Math.atan2(-(b[1] - a[1]), b[0] - a[0]); add(g); const m = sh(new THREE.Mesh(G_W, mV)); g.add(m); m.position.z = 0; VEL.push({ g, t: .05 + Math.abs(j - 3) * .13, r: (j % 2 ? 1 : .8), y: g.position.y, ry: g.rotation.y, zz: j }); } }
const NPO = 340, po = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 0), mat(0xc0ad90, { flatShading: true, roughness: 1 }), NPO); po.frustumCulled = false; add(po); const PO = []; for (let i = 0; i < NPO; i++) { const j = i % 6, u = VEL[j].g.position; PO.push({ j, x: u.x + (rnd() - .5) * 15, z: u.z + (rnd() - .5) * 15, y: rnd() * 12, vx: (rnd() - .5) * 11, vz: (rnd() - .5) * 11, vy: 4 + rnd() * 9, s: .2 + rnd() * .75, r: rnd() * 6 }); }
{ const L = []; for (let i = 0; i < 18; i++) L.push({ x: H(10 + rnd() * 18)[0] + (rnd() - .5) * 42, z: H(10 + rnd() * 18)[2] + (rnd() - .5) * 42, y: .06, sx: 3 + rnd() * 6, sy: .05, sz: 3 + rnd() * 6, ry: rnd() * 3, c: 0x5a4632, t: .05 + rnd() * .5, t2: fim(0) }); frota(UNI, mat(0xffffff), L, { sombra: false, de: 0, ate: fim(0) + .02, d: .4 }); }
AUTO.push(t => { const on = t < fim(0) + .02; po.visible = on; VEL.forEach(v => { v.g.visible = on; if (!on) return; const q = Math.max(0, t - v.t), c = q * q; v.g.rotation.x = Math.min(.95, c * 1.25) * v.r + Math.sin(q * 26) * .012 * clamp(q * 5) * clamp(1.5 - q); v.g.position.y = v.y - Math.min(8.5, c * 5.5); }); if (!on) return; for (let i = 0; i < NPO; i++) { const b = PO[i], q = t - VEL[b.j].t - .25; if (q <= 0) { O.scale.setScalar(0); O.position.set(0, -9, 0); } else { O.position.set(b.x + b.vx * q, Math.max(.2, b.y * .6 + b.vy * q - 6 * q * q), b.z + b.vz * q); O.rotation.set(b.r + q * 3, b.r, q); O.scale.setScalar(b.s * (1 + q * .7)); } O.updateMatrix(); po.setMatrixAt(i, O.matrix); } po.instanceMatrix.needsUpdate = true; });

// estacas e blocos ----------------------------------------------------------------------------------------------------
const OF = [6, 18, 30, 44], dE = rest(T.est, 1);
{ const Pil = [], Bl = [], tE = i => T.est + .1 + ord(i) * dE * .85; for (let i = 0; i < NB; i++) OF.forEach(o => { const [x, z] = pt(i, o), tt = tE(i) + o * .006; [[-1.1, -1.1], [1.1, -1.1], [-1.1, 1.1], [1.1, 1.1], [0, 0]].forEach(([a, b], k) => Pil.push({ x: x + a, z: z + b, y: -.3, sx: .36, sz: .36, sy: 1.15, t: tt + k * .04, dy: 9, c: k % 2 ? CONC : CONC2 })); Bl.push({ x, z, y: 0, sx: 4, sz: 4, sy: 1.1, t: tt + .4, c: 0xa8a59c, m: 'sobe' }); }); frota(gc(1, 1, 1, 10), mat(0xffffff, { roughness: .6 }), Pil, { modo: 'desce', d: .32 }); frota(UNI, mat(0xffffff), Bl, { modo: 'pop', d: .25 }); for (let q = T.est; q < T.est + dE; q += .26) som(q, 'impact'); }
const G_BATE = funde([[gb(5.4, 1, 3.4, 0, 0), 0x333844], [gb(4, 2.2, 3, 0, 1), AMAR], [gb(.9, 21, .9, 0, 3, 2), 0x46505e], [barraG([0, 3.1, -1], [0, 15, 1.9], .32), 0x46505e], [gb(1.4, .5, 1.4, 0, 24, 2), AMAR]]), G_MART = funde([[gb(1.5, 3, 1.2, 0, 0, 0), 0xe0403a], [gb(.3, 20, .3, 0, 3, 0), 0x24262a]]);
const rig = i => { const s = i === 0 ? 0 : i === 1 ? -1 : 1, u = HB + (i === 0 ? 2.6 : s * (5 + clamp((-0 + 0) + 0) + 0)); return u; };
const RIG = t => [0, 1, 2].map(i => { const k = clamp((t - T.est) / dE), s = [1, -1, 1][i], o = [18, 30, 6][i], u = HB + s * ([-1.5, 9, 22][i] + k * [3, 16, 16][i]); const q = H(19, 16 + k * 3); return { p: i === 0 ? [q[0], q[2]] : pt(u, o) }; });
moveis(G_BATE, 3, [0xffffff], (i, t) => { const q = RIG(t)[i].p; return [q[0], 0, q[1], i * 1.2 + .5]; }, { de: F(1) - .1, ate: fim(1) + .1 });
moveis(G_MART, 3, [0xffffff], (i, t) => { const q = RIG(t)[i].p, a = i * 1.2 + .5; return [q[0] + Math.sin(a) * 2, 3.6 + Math.abs(Math.sin(t * 5.2 + i)) * 2.2, q[1] + Math.cos(a) * 2, a]; }, { de: F(1) - .1, ate: fim(1) + .1 });
{ const Pi = []; for (let i = 0; i < 60; i++) { const j = i % 12, c = Math.floor(i / 12); Pi.push({ x: H(-20 + c * 1.1)[0] + j * 1.1 * HT_[0], z: H(-20 + c * 1.1)[2] + j * 1.1 * HT_[1], y: .55, sx: 1, sy: 1, sz: 9, ry: Math.atan2(HN.nx, HN.nz), c: CONC }); } frota(gb(1, 1, 1), mat(0xffffff), Pi, { de: F(1) - .05, ate: F(2) }); const m = []; for (let i = 0; i < 26; i++) { const q = H(-30 + rnd() * 90, -70 + rnd() * 140); m.push({ x: q[0], z: q[2], y: -1, sx: 3 + rnd() * 5, sy: 2 + rnd() * 2.8, sz: 3 + rnd() * 5, c: corDe([0x8f7350, 0xa2845e, 0x7e6444]) }); } frota(new THREE.IcosahedronGeometry(1, 1), mat(0xffffff, { flatShading: true, roughness: 1 }), m, { ate: F(4) }); }

// pilares, vigas e rampas de concreto que levam a arquibancada ---------------------------------------------------------------------------
const dP = rest(T.pil, 2), tP = i => T.pil + .05 + ord(i) * dP * .85;
{ const c = [], b = [], ra = [], l = []; for (let i = 0; i < NB; i++) { [.5, 6, 18, 30].forEach(o => { const [x, z] = pt(i, o), h = Math.max(.6, yO(o) - 2.2); c.push({ x, z, y: 1, sx: 1.1, sz: 1.1, sy: h, sub: h, t: tP(i) + o * .005, c: i % 2 ? CONC : CONC2 }); }); const [x, z] = pt(i, 44); c.push({ x, z, y: 1, sx: 1.5, sz: 1.5, sy: YT - 1, sub: YT - 1, t: tP(i) + .1, c: CONC }); const a = pt(i, 0), e = pt(i, 40); ra.push({ a: [a[0], .95, a[1]], b: [e[0], yO(40) - 1.7, e[1]], t: tP(i) + .28 }); l.push(peca(i, 41, { y: yO(40) - .6, sy: .5, sz: 7, c: CONC2, t: tP(i) + .35 }), peca(i, 44, { y: 13, sy: .8, sz: .9, c: CONC, t: tP(i) + .3 }), peca(i, 44, { y: 24, sy: .8, sz: .9, c: CONC, t: tP(i) + .35 }), peca(i, 44, { y: YT - .8, sy: 1, sz: 1, c: 0x8d939c, t: tP(i) + .4 })); } frota(UNI, mat(0xffffff, { roughness: .6 }), c, { modo: 'sobe', d: .4 }); cabos(ra, CONC2, .95, { sombra: true, d: .22 }); frota(UNI, mat(0xffffff), l, { d: .25 }); for (let q = T.pil; q < T.pil + dP; q += .3) som(q, 'tijolo'); }
// gruas: fuste fixo, lança que gira; a primeira mira o trecho onde o operário está
const G_FUS = funde([[gb(3, 1, 3, 0, 0), 0x46505e], ...(() => { const L = [], h = 64, s = 2.1; [[1, 1], [1, -1], [-1, -1], [-1, 1]].forEach(([a, c]) => L.push([gb(.32, h, .32, a * s / 2, 1, c * s / 2), AMAR])); for (let i = 0; i < 24; i++) { const y0 = 1 + i * 2.6; [[-1, -1, 1, -1], [1, -1, 1, 1], [1, 1, -1, 1], [-1, 1, -1, -1]].forEach(([a, c, d, e], j) => L.push([barraG([a * s / 2, y0 + (j % 2 ? 2.6 : 0), c * s / 2], [d * s / 2, y0 + (j % 2 ? 0 : 2.6), e * s / 2], .16), AMAR])); } return L; })(), [gb(3, 3, 3, 0, 65), 0xf4efe6]]);
const G_LAN = funde([[gb(70, 1.5, 1.5, 28, 0), AMAR], [gb(16, .9, 1.4, -14, .1), AMAR], [gb(6, 3, 2, -18, -2.4), 0x8d939c], ...(() => { const L = [[gb(.5, 7, .5, 0, 0), AMAR], [barraG([0, 7, 0], [40, 1.4, 0], .12), 0x24262a], [barraG([0, 7, 0], [-20, 1, 0], .12), 0x24262a]]; for (let i = 0; i < 24; i++) L.push([barraG([-6 + i * 2.7, .1, -.6], [-5 + i * 2.7, 1.4, .6], .13), 0xe0a800]); return L; })()]);
const CR = [[pt(HB + 5, -11), 2.2], [pt(HB + 22, -11), 1], [pt(HB + 42, -11), 0], [pt(HB + 62, -11), -1.2]];
const FimGrua = F(7) - .05, tG = T.pil + .3;
frota(G_FUS, mV, CR.map(([p], i) => ({ x: p[0], z: p[1], y: 0, t: tG + i * .25, sub: 66, sy: 1 })), { modo: 'sobe', d: .5, ate: FimGrua });
const alvo = H(16); const yawH = Math.atan2(-(alvo[2] - CR[0][0][1]), alvo[0] - CR[0][0][0]);
moveis(G_LAN, CR.length, [0xffffff], (i, t) => { if (t < tG + 1 + i * .25) return null; return [CR[i][0][0], 69, CR[i][0][1], i === 0 ? yawH + (t < T.arq ? (T.arq - t) * .2 : 0) : CR[i][1] + t * .09]; }, { de: tG + .5, ate: FimGrua });

// arquibancada: degraus pré-moldados, trecho por trecho ------------------------------------------------------------------------------------------
const dA = rest(T.arq, 3), tA = (i, r) => Math.abs(i - HB) <= 1 ? T.arq + .1 + r / NR * dA * .92 : T.arq + .1 + ord(i) * dA * .72 + r / NR * dA * .25;
{ const l = []; for (let i = 0; i < NB; i++) for (let r = 0; r < NR; r++) { const o = oR(r); l.push(peca(i, o, { y: yR(r) - .46, sy: .5, sz: .84, c: r % 2 ? CONC : CONC2, t: tA(i, r), dy: 7 })); } frota(UNI, mat(0xffffff, { roughness: .7 }), l, { modo: 'desce', d: .3 }); for (let q = T.arq; q < T.arq + dA; q += .22) som(q, 'tijolo'); }
{ const G_C = gb(1, 1, 1), L = moveis(funde([[gb(14, .5, 2.4, 0, 0), CONC]]), 1, [0xffffff], (i, t) => { const c = ((t - T.arq) * .85) % 1, r = clamp((t - T.arq) / dA) * NR * .9, p = pt(HB - 1 + (Math.floor((t - T.arq) * .85) % 3), oR(r)), ya = yR(r) + (1 - ease(c)) * 26; return [p[0], ya, p[1], Math.atan2(-HT_[1], HT_[0])]; }, { de: T.arq, ate: fim(3) }); moveis(gb(.08, 1, .08), 4, [0x24262a], (i, t) => { const c = ((t - T.arq) * .85) % 1, r = clamp((t - T.arq) / dA) * NR * .9, p = pt(HB - 1 + (Math.floor((t - T.arq) * .85) % 3), oR(r)), ya = yR(r) + (1 - ease(c)) * 26 + .5; return [p[0] + [-3, 3, -3, 3][i] * HT_[0], ya, p[1] + [-3, 3, -3, 3][i] * HT_[1], 0]; }, { de: T.arq, ate: fim(3) }); }
{ const fi = new THREE.InstancedMesh(UNI, mat(0x24262a), 1); fi.frustumCulled = false; add(fi); AUTO.push(t => { const on = t >= T.arq && t < fim(3); fi.visible = on; if (!on) return; const c = ((t - T.arq) * .85) % 1, r = clamp((t - T.arq) / dA) * NR * .9, p = pt(HB - 1 + (Math.floor((t - T.arq) * .85) % 3), oR(r)), ya = yR(r) + (1 - ease(c)) * 26 + 3.5; O.position.set(p[0], ya, p[1]); O.rotation.set(0, 0, 0); O.scale.set(.12, 68 - ya, .12); O.updateMatrix(); fi.setMatrixAt(0, O.matrix); fi.instanceMatrix.needsUpdate = true; }); }

// rampas em caracol e fachada --------------------------------------------------------------------------------------------------------------------------
const dR = rest(T.ram, 4), U_R = [HB + 40, HB + 20, HB + 60, HB + 2].map(u => u % NB), RR = 15;
const G_RAM = funde([[gb(6.6, .4, 3.4), 0xd2d0c8], [gb(.16, 1.1, 3.4, 3.2, .4), 0xf4efe6], [gb(.16, 1.1, 3.4, -3.2, .4), 0xf4efe6]]);
const cR = U_R.map(u => { const [x, z] = pt(u, 44 + RR + 3.5); return [x, z]; });
{ const l = [], c = [], n = 130; cR.forEach(([cx, cz], k) => { const yaw0 = Math.atan2(cz, cx) + 2.6; for (let i = 0; i < n; i++) { const a = yaw0 + i * .19, y = 1 + i * 20.6 / n; l.push({ x: cx + Math.cos(a) * RR, z: cz + Math.sin(a) * RR, y, ry: -a, t: T.ram + .1 + (i / n) * dR * .75 + k * .12 }); if (i % 13 === 0) c.push({ x: cx + Math.cos(a) * (RR + 3), z: cz + Math.sin(a) * (RR + 3), y: 0, sx: .8, sz: .8, sy: y, sub: y, t: T.ram + .05 + (i / n) * dR * .75 + k * .12, c: CONC }, { x: cx + Math.cos(a) * (RR - 3), z: cz + Math.sin(a) * (RR - 3), y: 0, sx: .8, sz: .8, sy: y, sub: y, t: T.ram + .05 + (i / n) * dR * .75 + k * .12, c: CONC }); } }); frota(G_RAM, mV, l, { d: .2 }); frota(UNI, mat(0xffffff), c, { modo: 'sobe', d: .3 }); for (let q = T.ram; q < T.ram + dR; q += .18) som(q, 'pop'); }
{ const f = []; for (let i = 0; i < NB; i++) { const tq = F(4) + .3 + ord(i) * (fim(4) - F(4) - .6); [[2, 10.8, V_.cad1], [14, 9.6, 0xdfe5ea], [25, 11, V_.cad1]].forEach(([y, h, c], k) => f.push(peca(i, 44.2, { y, sy: h, sz: .3, c: k === 1 ? (i % 2 ? 0xb6d8e8 : 0x9cc9df) : (i % 2 ? c : new THREE.Color(c).offsetHSL(0, 0, -.04).getHex()), t: tq + k * .1 }))); } frota(UNI, mat(0xffffff, { roughness: .4 }), f, { d: .25 }); }

// treliças de aço, em balanço para dentro do campo ---------------------------------------------------------------------------------------------------------
const YTr = z => YT - z * .069, LTR = 44;
const G_TRE = (() => { const L = [], yb = z => YT - 5.6 + z * .06, c = ACO, q = 0; for (const s of [-.5, .5]) { L.push([barraG([s, 0, 0], [s, -3, LTR], .34), 0xe9edf1], [barraG([s * .3, -5.6, 0], [s * .3, -3.3, LTR], .42), 0xe9edf1]); for (let i = 0; i < 12; i++) { const z0 = i * LTR / 12, z1 = (i + 1) * LTR / 12; L.push([barraG([s, YTr(z0) - YT, z0], [s * .3, yb(z1) - YT, z1], .16), c], [barraG([s * .3, yb(z1) - YT, z1], [s, YTr(z1) - YT, z1], .16), c]); } } return funde(L); })();
const dT = rest(T.tre, 5), tTr = i => T.tre + .1 + ord(i) * dT * .85;
chuva(900, F(5) - .02, T.tre + .4, () => H(14, 0), 120, 90, 2.2);
{ const l = [], ri = []; for (let i = 0; i < NB; i += 1) { const a = pt(i, 44), b = pt(i + 1, 44), q = pt(i, 0), ang = Math.atan2(q[0] - a[0], q[1] - a[1]); l.push({ x: a[0], z: a[1], y: YT, ry: ang, t: tTr(i), dy: 16 });[44, 30, 16, 2].forEach((o, k) => ri.push(peca(i, o, { y: YT - (44 - o) * .069 - .3, sy: .3, sz: .3, c: ACO, t: tTr(i) + .2 + k * .03 }))); } frota(G_TRE, mV, l, { modo: 'desce', d: .45 }); frota(UNI, mat(0xffffff), ri, { d: .2 }); for (let q = T.tre; q < T.tre + dT; q += .24) som(q, 'toc'); }

// cobertura: placas caindo por cima das treliças -----------------------------------------------------------------------------------------------------------------
const dC = rest(T.cob, 6), teto = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: .35, metalness: .15 });
{ const g = new THREE.BoxGeometry(1, .14, 1), p = g.attributes.position; for (let i = 0; i < p.count; i++) p.setY(i, p.getY(i) - p.getZ(i) * 1.5); g.computeVertexNormals(); const l = [], cor = new THREE.Color(V_.teto); for (let i = 0; i < NB; i++) for (let k = 0; k < 4; k++) { const zc = 5.5 + k * 11, o = 44 - zc; l.push(peca(i, o, { sx: 0, y: YTr(zc) + .2, sz: 11.1, c: k === 3 ? V_.cad1 : cor.clone().offsetHSL(0, 0, Math.floor(i / 2) % 2 ? 0 : -.09).getHex(), t: T.cob + .1 + ((1 - dB(i)) * .12 + ord(i) * .72) * dC + (3 - k) * .1 })); const a = pt(i, o + 5.5), b = pt(i + 1, o + 5.5); l[l.length - 1].sx = Math.hypot(a[0] - b[0], a[1] - b[1]) + .2; } frota(g, teto, l, { modo: 'desce', dy: 8, d: .3 }); for (let q = T.cob; q < T.cob + dC; q += .16) som(q, 'telha'); }

// campo: base, drenos, brita, gramado, linhas, gols e placas -------------------------------------------------------------------------------------------------------
const YG = .3, dD = rest(T.dre, 7);
{ const l = []; for (let x = -50; x <= 50; x += 5) [-1, 1].forEach(s => l.push({ a: [Math.round(x), .34, 0], b: [x + s * 0 + 11, .34, s * 33], t: T.dre + .1 + (x + 50) / 100 * dD * .55 + (s > 0 ? .1 : 0) })); const c = [{ a: [-53, .34, 0], b: [53, .34, 0], t: T.dre }]; const ma = add(box(112, .26, 74, 0x8a6e4e, .02)); ma.position.set(0, .13, 0); ma.receiveShadow = true; AUTO.push(t => { ma.visible = t >= F(7) - .02; }); const v = []; for (let x = -55; x <= 55; x += 2.5) [-1, 1].forEach(s => v.push({ x: x, z: s * 18, y: .26, sx: 1.5, sy: .1, sz: 37, c: 0x6d5438, t: T.dre + (x + 55) / 110 * dD * .4 })); frota(UNI, mat(0xffffff), v, { d: .2, recebe: true, ate: T.gra }); cabos(l, 0xf0f0ea, .3, { sombra: true, d: .3, ate: T.gra + 2 }); cabos(c, 0xe07830, .62, { sombra: true, d: .4, ate: T.gra + 2 }); const b = []; for (let i = 0; i < 56; i++) for (let j = 0; j < 36; j++) { const x = -55 + i * 2 + 1, z = -35 + j * 2 + 1; b.push({ x, z, y: .27, sx: 2.05, sy: .14, sz: 2.05, c: corDe([0xb5b2aa, 0xa4a198, 0xc4c1b9]), t: T.dre + dD * .62 + i / 56 * dD * .35 + (j % 5) * .03 }); } frota(UNI, mat(0xffffff, { roughness: 1 }), b, { d: .2, sombra: false, ate: T.gra + 1.5 }); for (let q = T.dre; q < T.dre + dD; q += .24) som(q, 'toc'); }
const dG = rest(T.gra, 8), NF = 14, LF = 112, WF = 74 / NF;
{ const l = []; for (let i = 0; i < NF; i++) { const z = 37 - (i + .5) * WF; l.push({ x: -LF / 2, z, y: .29, sx: LF, sy: .1, sz: WF + .03, t: T.gra + .1 + i * dG * .86 / NF, d: dG * .86 / NF, m: 'estica', c: new THREE.Color(0x3a8f3e).offsetHSL(0, 0, i % 2 ? .04 : -.015).getHex() }); } frota(gb(1, 1, 1, .5), mat(0xffffff, { roughness: .95 }), l, { sombra: false }); const tp = dG * .86 / NF; moveis(funde([[gc(.55, .55, WF - .3, 14).rotateX(PI / 2).translate(0, .85, -(WF - .3) / 2), 0x3a8f3e], [gb(2.6, 1.3, 2, 2.4, .6), 0xd8443a], [gb(1.4, 1, 1.4, 2.4, 1.9), 0xaee3f7]]), 1, [0xffffff], (i, t) => { const u = (t - T.gra - .1) / tp, n = clamp(Math.floor(u), 0, NF - 1), e = clamp(u - n); return [-LF / 2 + LF * e, .3, 37 - (n + .5) * WF + WF - .15, 0]; }, { de: T.gra, ate: T.gra + .1 + dG * .8 }); moveis(new THREE.BoxGeometry(.1, .1, .1), 1, [0xffffff], () => null); }
const REDE = [], LN = []; { const t0 = T.gra + dG * .86, B = (x, z, w, d, k) => LN.push({ x, z, y: .4, sx: w, sy: .03, sz: d, c: 0xffffff, t: t0 + k * .03 });[-34, 34].forEach(z => B(0, z, 105, .14, 0));[-52.5, 52.5, 0].forEach(x => B(x, 0, .14, 68, 1));[-1, 1].forEach(s => { B(s * 36, 0, .14, 40.3, 2); B(s * 44.25, 20.15, 16.5, .14, 3); B(s * 44.25, -20.15, 16.5, .14, 3); B(s * 47, 0, .14, 18.3, 4); B(s * 49.75, 9.15, 5.5, .14, 4); B(s * 49.75, -9.15, 5.5, .14, 4); }); for (let i = 0; i < 40; i++) { const a = i / 40 * 6.283; B(Math.cos(a) * 9.15, Math.sin(a) * 9.15, .3, .3, 2); } frota(UNI, mat(0xffffff), LN, { sombra: false, d: .2 }); const g = [];[-1, 1].forEach(s => { const x = s * 52.7; g.push({ x, z: -3.66, y: .3, sx: .14, sy: 2.44, sz: .14, c: 0xffffff, t: t0 + .2 }, { x, z: 3.66, y: .3, sx: .14, sy: 2.44, sz: .14, c: 0xffffff, t: t0 + .2 }, { x, z: 0, y: 2.74, sx: .14, sy: .14, sz: 7.46, c: 0xffffff, t: t0 + .25 }); });
  [-1, 1].forEach(s => { const r = add(new THREE.Mesh(new THREE.BoxGeometry(2, 2.44, 7.4), new THREE.MeshBasicMaterial({ map: tex(64, 64, (q, w) => { q.clearRect(0, 0, w, w); q.strokeStyle = '#fff'; q.lineWidth = 7; for (let i = 0; i <= 4; i++) { q.beginPath(); q.moveTo(i * 16, 0); q.lineTo(i * 16, w); q.moveTo(0, i * 16); q.lineTo(w, i * 16); q.stroke(); } }, 4, 3), transparent: true, opacity: .75, side: THREE.DoubleSide, depthWrite: false }))); r.position.set(s * 53.7, 1.52, 0); aparece(r, t0 + .3, .2); if (s < 0) REDE.push(r); }); const lo = [], cor = [V_.cad1, 0x24262a, V_.cad2]; for (let i = 0; i < NB; i++) lo.push(peca(i, -.2, { y: .3, sy: 2.2, sz: .25, c: 0x40464f, t: F(9) - .3 + dB(i) * .4 })); frota(UNI, mat(0xffffff), lo, { d: .2 }); const pl = []; for (let i = 0; i < NB; i++) pl.push(peca(i, -6, { y: .4, sy: 1, sz: .16, c: cor[i % 3], t: t0 + .3 + i * .005 })); frota(UNI, mat(0xffffff, { roughness: .4 }), pl, { d: .2, ate: 1e9 }); frota(UNI, mat(0xffffff, { roughness: .5 }), g, { d: .2, ate: 1e9 }); }

// cadeiras: a ordem de montagem é a própria ordem das instâncias ------------------------------------------------------------------------------------------------------------
const SE = []; for (let i = 0; i < NB; i++) for (let r = 0; r < NR; r++) { const o = oR(r), a = pt(i, o), b = pt(i + 1, o), w = Math.hypot(a[0] - b[0], a[1] - b[1]), n = Math.floor(w / .56), ry = Math.atan2(-(b[1] - a[1]), b[0] - a[0]) + PI; for (let s = 0; s < n; s++) { const u = (s + .5) / n; SE.push({ x: a[0] + (b[0] - a[0]) * u, z: a[1] + (b[1] - a[1]) * u, y: yR(r) + .04, ry, b: i, k: dB(i) + r * .0016 + s * .00001, m: Math.floor((i + 4) / 4) % 2 === 0 ? (Math.floor(r / 5) % 2 ? V_.cad1 : V_.cad2) : V_.cad1 }); } }
SE.sort((a, b) => a.k - b.k);
const G_SEAT = funde([[gb(.46, .08, .44, 0, .36)], [gb(.46, .5, .07, 0, .38, -.2)], [gb(.08, .36, .3, 0, 0)]]), cadeira = new THREE.InstancedMesh(G_SEAT, mat(0xffffff, { roughness: .5 }), SE.length); cadeira.frustumCulled = false; cadeira.receiveShadow = true; add(cadeira);
SE.forEach((s, i) => { O.position.set(s.x, s.y, s.z); O.rotation.set(0, s.ry, 0); O.scale.setScalar(1); O.updateMatrix(); cadeira.setMatrixAt(i, O.matrix); COR.set(s.m); cadeira.setColorAt(i, COR); });
const dS = rest(T.cad, 9); AUTO.push(t => { cadeira.count = Math.floor(SE.length * clamp((t - T.cad - .05) / dS)); cadeira.visible = cadeira.count > 0; }); for (let q = T.cad; q < T.cad + dS; q += .13) som(q, 'pop');

// refletores e telão ---------------------------------------------------------------------------------------------------------------------------------------------------------------
const dL = rest(T.ref, 10), T_LZ = Math.min(tk('claro', 10), fim(10) - .7), lumi = new THREE.MeshStandardMaterial({ color: 0xf2f2ee, emissive: 0xfff4d6, emissiveIntensity: 0, roughness: .3 });
{ const l = [], g = []; for (let i = 0; i < NB; i++) { const q = T.ref + .05 + dB(i) * dL * .55; const n = 3; for (let k = 0; k < n; k++) { const u = (k + .5) / n, p = pt(i + u, 1.2); l.push({ x: p[0], z: p[1], y: YT - 3.5, sx: 1.2, sy: .5, sz: .7, ry: Math.atan2(-pt(i + u + .1, 0)[1] + pt(i + u, 0)[1], pt(i + u + .1, 0)[0] - pt(i + u, 0)[0]), t: q + k * .05 }); } g.push(peca(i, 1.6, { y: YT - 3.1, sy: .25, sz: 1.5, c: 0x56606e, t: q - .05 })); } frota(UNI, mat(0xffffff), g, { d: .2 }); frota(UNI, lumi, l, { d: .2 }); }
const G_TEL_ = (() => { const c = tex(256, 128, (x, w, h) => { x.fillStyle = '#101820'; x.fillRect(0, 0, w, h); x.fillStyle = '#ffd23f'; x.font = '900 72px Arial'; x.textAlign = 'center'; x.fillText('0 x 0', w / 2, 92); }); return c; })();
const placar = new THREE.MeshBasicMaterial({ map: G_TEL_, toneMapped: false }), telaM = [1, -1].map(s => { const m = add(new THREE.Mesh(new THREE.BoxGeometry(.8, 11, 24), [placar, placar, placar, placar, placar, placar])); m.position.set(s * 100, 28.5, 0); aparece(m, T.ref + 1, .4); return m; });
const cvP = tex(256, 128, (x, w, h) => { x.fillStyle = '#101820'; x.fillRect(0, 0, w, h); x.fillStyle = '#ffd23f'; x.font = '900 72px Arial'; x.textAlign = 'center'; x.fillText('1 x 0', w / 2, 92); });

// pessoas: torcida lotada, sentada nas cadeiras ------------------------------------------------------------------------------------------------------------------------------------
const CCor = [V_.cad1, V_.cad1, V_.cad1, V_.cad2, 0xf4efe6, V_.cad1, 0x2b3a67, V_.time2], PE = []; { const r2 = prng(909); SE.forEach(s => { if (r2() < .9) PE.push({ ...s, f: r2() * 6.28, c: CCor[Math.floor(r2() * CCor.length)], p: corDe([0xd9a57c, 0xb97e55, 0x8a5a3a, 0xeac6a0]) }); }); }
const G_TOR2 = funde([[gb(.4, .56, .24, 0, .52, .04)], [gb(.2, .22, .2, 0, 1.08, .04), 0xd9a57c], [gb(.4, .1, .34, 0, .4, .2), 0x2b3a67]]), publico = new THREE.InstancedMesh(G_TOR2, mV, PE.length); publico.frustumCulled = false; add(publico); PE.forEach((s, i) => { O.position.set(s.x, s.y, s.z); O.rotation.set(0, s.ry, 0); O.scale.setScalar(1); O.updateMatrix(); publico.setMatrixAt(i, O.matrix); COR.set(s.c); publico.setColorAt(i, COR); });
const AP = publico.instanceMatrix.array, Y0 = PE.map(s => s.y), Ang = PE.map(s => s.b / NB * 6.2832);
const T_G = T_USO + 2.5; // o gol
AUTO.push(t => { const q = t - T_G; REDE.forEach(r => { r.scale.x = q > 0 && q < 1.4 ? 1 + Math.sin(q * 15) * .42 * Math.exp(-q * 2.2) : 1; }); });
AUTO.push(t => { const on = t >= F(LAST) - .05; publico.visible = on; if (!on) return; const fest = clamp((t - T_G) / .25) * clamp((T_G + 3.4 - t) / .6); for (let i = 0; i < PE.length; i++) { const s = PE[i], w = Math.sin(Ang[i] * 2 - t * 2.2), ola = w > .9 ? (w - .9) * 5 : 0, sal = fest * Math.abs(Math.sin(t * 7 + s.f)) * .55; AP[i * 16 + 13] = Y0[i] + ola * .5 + sal + Math.sin(t * 3 + s.f) * .02; } publico.instanceMatrix.needsUpdate = true; });
// jogadores e bola
const G_JOG = funde([[gb(.46, .62, .28, 0, .9)], [gb(.22, .24, .22, 0, 1.54), 0xd9a57c], [gb(.17, .9, .2, -.13, 0), 0xf4efe6], [gb(.17, .9, .2, .13, 0), 0xf4efe6]]);
const J = []; for (let i = 0; i < 22; i++) J.push({ x: (i < 11 ? -1 : 1) * (6 + (i % 11) * 4.1), z: -30 + ((i * 7) % 11) * 6, c: i < 11 ? V_.cad1 : V_.time2, f: i * 1.3 });
const bolaP = t => { const a = T_G - 2.1, k = clamp((t - a) / 1.5), e = clamp((t - T_G + .6) / .6); if (t >= T_G) return [-53.6, .65, 1.4]; if (e > 0) return [-34 + (-53.6 + 34) * e, .5 + Math.sin(e * PI) * 2.1, 3 + (1.4 - 3) * e]; const c = (t * .7) % 1; return t < a ? [Math.sin(t) * 16, .4, Math.cos(t * .8) * 18] : [Math.sin(a) * 16 + (-34 - Math.sin(a) * 16) * k, .4, Math.cos(a * .8) * 18 + (3 - Math.cos(a * .8) * 18) * k]; };
moveis(G_JOG, 22, J.map(j => j.c), (i, t) => { const j = J[i], b = bolaP(t), q = (i === 3 || i === 7 || i === 14) ? 1 : .16, x = j.x * (1 - q) + (b[0] + (i - 7) * .4) * q * .92 + Math.sin(t * .9 + j.f) * 1.4, z = j.z * (1 - q) + b[2] * q + Math.cos(t * .7 + j.f) * 1.4; return [Math.max(-50, x * .7 + (i < 11 ? -26 : -30)), .36 + Math.abs(Math.sin(t * 7 + j.f)) * .1, z, b[0] - x > 0 ? 1.4 : -1.4]; }, { de: F(LAST) - .05 });
moveis(new THREE.SphereGeometry(.34, 12, 8), 1, [0xffffff], (i, t) => { const b = bolaP(t); return [b[0], b[1] + .3, b[2], 0]; }, { de: F(LAST) - .05, mat: new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }) });
// fumaça e bandeiras da torcida, atrás do gol
const NBD = 26, BD = []; for (let i = 0; i < NBD; i++) { const u = HB + 12 + i * .55; BD.push({ p: pt(u, 5 + (i % 5) * 3.2), o: 5 + (i % 5) * 3.2, f: i }); }
moveis(funde([[gb(.05, 2.6, .05, 0, 0), 0x56606e], [gb(1.5, .9, .03, .78, 1.7)]]), NBD, [V_.cad1, V_.cad2], (i, t) => { const b = BD[i]; return [b.p[0], yO(b.o) + .8, b.p[1], Math.sin(t * 2.2 + b.f) * .9, Math.sin(t * 2.6 + b.f) * .35]; }, { de: T_USO - .05 });

// luzes finais -------------------------------------------------------------------------------------------------------------------------------------------------------------------------
const fZ = []; for (let i = 0; i < NB * 3; i++) { const p = pt(i / 3, 1.2); fZ.push([p[0], YT - 3.7, p[1]]); } const flo = brilhos(fZ, 0xfff2cf, 8), T_N = F(10) + .1; const bol = veuT();
function veuT() { const m = new THREE.SpriteMaterial({ map: TX_G, color: 0xffeecc, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, toneMapped: false }), s = new THREE.Sprite(m); s.position.set(0, 40, 0); s.scale.setScalar(420); add(s); return m; }
const C_LZ = new THREE.Color(0xfff6e4);
AUTO.push(t => { const k = ease((t - T_N) / Math.max(1.2, T_LZ - T_N)), on = t >= T_LZ, lz = on ? ease((t - T_LZ) / .25) : 0; noite(k * .94); acende(k); flo.op(lz * .6); lumi.emissiveIntensity = lz * 3.5; bol.opacity = lz * .06 * (t > T_USO ? 0 : 1); if (lz > 0) { sol.intensity = .55 + lz * 2; sol.color.lerp(C_LZ, lz); hemi.intensity = .47 + lz * .75; scene.environmentIntensity = .1 + lz * .2; } placar.map = t >= T_G ? cvP : G_TEL_; });

// operário: escala real, ao lado da peça em cada fala --------------------------------------------------------------------------------------------------------------------------------------
const OP = operario(.86), pQ = (u, o, y, c) => { const p = pt(u, o); return [p[0], p[1], y, c]; };
const p1 = H(9, 6), p2 = (() => { const q = pt(HB + 2, 18); return [q[0] + HT_[0] * 1.5, q[1] + HT_[1] * 1.5]; })(), p3 = pt(HB, -3), p4 = (() => { const [cx, cz] = cR[0], n = Math.hypot(cx, cz); return [cx + cx / n * (RR + 9), cz + cz / n * (RR + 9)]; })(), p5 = pt(HB - .5, 41), p6 = pt(HB - .5, 30), p7 = [-46, 16], p8 = [-22, 8], p9 = pt(HB, oR(10)), p10 = pt(HB, 3);
const VIS = [
  [H(-62, 26, 22), H(14, 2, 5.5)],
  [H(-20, -22, 16), H(9, 10, .5), 1],
  [H(-26, 26, 15), H(12, -2, 6), 1],
  [H(-40, -20, 10), H(8, 3, 8), 1],
  [[p4[0] + 30, 15, p4[1] + 26], [p4[0] - 7, 7, p4[1] - 6], 1],
  [H(4, -26, 30), H(42, 0, 23), 1],
  [H(-8, 20, 50), H(30, -4, 35), 1],
  [[p7[0] + 26, 17, p7[1] + 38], [p7[0] - 3, .4, p7[1] - 4], 1],
  [[p8[0] + 22, 15, p8[1] + 40], [p8[0] - 4, .5, p8[1] - 8], 1],
  [H(-16, -15, 24), H(10, 3, yR(11)), 1],
  [H(-30, 24, 39), H(3, -4, 32), 1],
];
{ const RT = [[0, H(-28, -6)[0], H(-28, -6)[2], 0, olha(VIS[0][0], H(-28, -6)[0], H(-28, -6)[2]), 'pasmo'], [fim(0), H(-28, -6)[0], H(-28, -6)[2], 0, 0, 'pasmo'],
  [F(1), p1[0], p1[2], 0, olha(VIS[1][0], p1[0], p1[2]), 'bate', 1], [F(2), p2[0], p2[1], 1.1, olha(VIS[2][0], p2[0], p2[1]), 'bate', 1], [F(3), p3[0], p3[1], .03, olha(VIS[3][0], p3[0], p3[1]), 'para', 1],
  [F(4), p4[0], p4[1], .06, olha(VIS[4][0], p4[0], p4[1]), 'bate', 1], [F(5), p5[0], p5[1], yO(40) - 1.08, olha(VIS[5][0], p5[0], p5[1]), 'bate', 1], [F(6), p6[0], p6[1], YTr(14) + .35, olha(VIS[6][0], p6[0], p6[1]), 'bate', 1],
  [F(7), p7[0], p7[1], .3, olha(VIS[7][0], p7[0], p7[1]), 'bate', 1], [F(8), p8[0], p8[1], .4, olha(VIS[8][0], p8[0], p8[1]), 'para', 1], [F(9), p9[0], p9[1], yR(10) + .05, olha(VIS[9][0], p9[0], p9[1]), 'bate', 1], [F(10), p10[0], p10[1], YTr(41) + .3, olha(VIS[10][0], p10[0], p10[1]), 'bate', 1], [T_USO, p10[0], p10[1], YTr(41) + .3, 0, 'bate']];
  roteiro(OP, RT, T_USO); }
const pF_ = [-57, -9.5]; festa(OP, pF_[0], pF_[1], -1.2, T_USO, .4);

// câmera ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
const K = plano(VIS, [{ t: F(LAST) + .03, p: [-420, 340, -480], l: [0, 14, 0] }, { t: T_USO - .03, p: [-340, 280, -390], l: [0, 14, 0] }, { t: T_USO + .02, p: [-94, 25, -9], l: [-37, 1, 1] }, { t: T_G + 1, p: [-90, 24, -8], l: [-37, 1, 1] }, { t: T_G + 1.03, p: [52, 42, 44], l: [-72, 13, -34] }, { t: D.total + 1, p: [36, 38, 32], l: [-72, 13, -34] }]);

// rótulos e sons ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
etq('TERRA FOFA', F(0) + .15, fim(0), 'ruim');
[['ESTACAS', T.est, fim(1)], ['PILARES', T.pil, fim(2)], ['ARQUIBANCADA', T.arq, fim(3)], ['RAMPAS', T.ram, fim(4)], ['TRELIÇAS', T.tre, fim(5)], ['COBERTURA', T.cob, fim(6)], ['DRENOS', T.dre, fim(7)], ['GRAMADO', T.gra, fim(8)], ['CADEIRAS', T.cad, fim(9)], ['REFLETORES', T.ref, fim(10)]].forEach(l => etq(...l));
etq('ESTÁDIO PRONTO!', F(LAST) + .1, T_USO, 'grande'); etq('GOL!', T_G + .05, T_G + 1.6, 'grande');
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); som(.08, 'crack'); som(.3, 'crack'); som(.55, 'desaba'); som(.8, 'impact'); som(1.05, 'desaba'); som(F(LAST) + .1, 'ding'); som(T_LZ, 'impact'); som(T_LZ + .05, 'zumbido'); som(T_USO + .1, 'whoosh'); som(T_G - .55, 'toc'); som(T_G, 'impact'); som(T_G + .1, 'riser');
for (let q = F(LAST) + .4; q < D.total; q += 1.4) som(q, 'chuva');
for (let q = F(1); q < fim(10); q += 1.3) som(q, 'toc');

window.CAPA_T = T_G + 2.2;
function foco() { const v = new V3(); cam.getWorldDirection(v); const y = cam.position.y, q = v.y < -.05 ? Math.min(y / -v.y, 220) : 120; return [cam.position.x + v.x * q, cam.position.z + v.z * q]; }
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); const f = foco(); segueSol(f[0], f[1]); AUTO.forEach(q => q(t)); });
