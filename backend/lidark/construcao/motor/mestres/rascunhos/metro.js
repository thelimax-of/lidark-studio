// Metrô em corte, em tamanho real: rua e cidade em cima; paredes, escoras, tatuzão, anéis, estação, trilhos, escadas, ventiladores e sinais embaixo; no fim, o trem chega à estação.
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
// Metrô em corte, em tamanho real: rua e cidade em cima; paredes, escoras, tatuzão, anéis, estação, trilhos, escadas, ventiladores e sinais embaixo; no fim, o trem chega à estação.
cenario(150, 500, 2600); noite(0);
const T = { par: tk('paredes', 1), esc: tk('escoras', 2), tat: tk('tatuzão', 3), est: tk('esteira', 4), ane: tk('anéis', 5), pla: tk('plataforma', 6), tri: tk('trilhos', 7), rol: tk('escadas', 8), ven: tk('ventiladores', 9), sin: tk('sinais', 10) };
const CONC = 0xc4c1b8, CONC2 = 0xb2afa6, AMAR = 0xffc61a, ACO = 0x8a95a3, MAQ = V_.maq;
const XA = 45, YF = -24, ZB = -11, YE = -14.6, RT = 3.2, RH = 3.5, XM = 640, YB = -90, YR = YE - RT + .55, YP = YR + 1.1, YM = -8.4;
const rest = (t, i) => Math.max(1.2, fim(i) - t - .25), liso = (i, c = 0) => ease((c - F(i) - .04) / (dur(i) + .06));

// terra em camadas ----------------------------------------------------------------------------------------------------
const FAIXA = [[0, 1.4, '#5d4228'], [1.4, 9, '#b26a3c'], [9, 15, '#c9a26a'], [15, 28, '#8f7a64'], [28, 50, '#a38f76'], [50, 90, '#6f6a66']];
const TR = tex(1024, 1024, (g, w, h) => { const y_ = m => m / 90 * h; FAIXA.forEach(([a, b, c]) => { g.fillStyle = c; g.beginPath(); g.moveTo(0, y_(a) + (a ? Math.sin(a) * 6 : 0)); for (let x = 0; x <= w; x += 8) g.lineTo(x, y_(a) + (a ? Math.sin(x / w * 6.283 * 3 + a) * 6 + Math.sin(x / w * 6.283 * 7) * 3 : 0)); g.lineTo(w, h); g.lineTo(0, h); g.fill(); }); const r = prng(12); for (let i = 0; i < 2600; i++) { const x = r() * w, y = r() * h, s = 1 + r() * 3.2; g.fillStyle = r() > .5 ? 'rgba(0,0,0,.13)' : 'rgba(255,255,255,.1)'; g.beginPath(); g.ellipse(x, y, s * 1.5, s, r() * 3, 0, 6.3); g.fill(); } for (let i = 0; i < 90; i++) { const x = r() * w, y = h * (.3 + r() * .7), s = 5 + r() * 12; g.fillStyle = ['#8d8a84', '#a3a09a', '#76736d'][i % 3]; g.beginPath(); g.ellipse(x, y, s * 1.4, s, r() * 3, 0, 6.3); g.fill(); } });
const mT = new THREE.MeshStandardMaterial({ map: TR, roughness: 1 }), mTc = new THREE.MeshStandardMaterial({ map: TR, roughness: 1, transparent: true, opacity: 1 });
const uvM = g => { const p = g.attributes.position, u = g.attributes.uv; for (let i = 0; i < p.count; i++) u.setXY(i, p.getX(i) / 180, (p.getY(i) - YB) / -YB); return g; };
const bm = (x0, x1, y0, y1, z0, z1, m = mT) => { const g = uvM(new THREE.BoxGeometry(x1 - x0, y1 - y0, z1 - z0).translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)), q = add(new THREE.Mesh(g, m)); q.receiveShadow = true; return q; };
const ZH = -14;[-1, 1].forEach(s => { const a = s < 0 ? -XM : XA, b = s < 0 ? -XA : XM; bm(a, b, YE + RH, 0, ZH, 0); bm(a, b, YB, YE - RH, ZH, 0); }); bm(-XA, XA, YB, YF, ZH, 0); bm(-XM, XM, YB, 0, -420, ZH);
// fundo do buraco do túnel, atrás dos anéis
[-1, 1].forEach(s => { const q = add(new THREE.Mesh(new THREE.PlaneGeometry(XM - XA, RH * 2), mat(0x4a3a2c, { roughness: 1 }))); q.position.set(s * (XM + XA) / 2, YE, -3.45); });
// pedras e canos enterrados aparecendo no corte
{ const l = [], r2 = prng(5); for (let i = 0; i < 300; i++) { const x = (r2() - .5) * 600, y = -2 - r2() * 80; if (Math.abs(x) < 49 && y > -27) continue; if (Math.abs(y - YE) < 4.6) continue; l.push({ x, y, z: .02, sx: .3 + r2() * 1.1, sy: .25 + r2() * .7, sz: .01, c: corDe([0x8d8a84, 0xa3a09a, 0x76736d, 0x5e5044]) }); } frota(gc(1, 1, 1, 9).rotateX(PI / 2), mat(0xffffff, { roughness: 1 }), l, { sombra: false }); }
[[-1.7, .34, 0x3a7fd8], [-2.6, .5, 0x8d6a4a], [-3.4, .22, 0xffb627]].forEach(([y, r_, c]) => { [-1, 1].forEach(s => { const q = add(box(XM - XA, r_ * 2, .05, c, .01)); q.position.set(s * (XM + XA + 2) / 2, y, .03); }); });
// chão, ruas e cidade -----------------------------------------------------------------------------------------------------------
const cha = (w, d, x, z, c, y = .02) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, d), mat(c, { roughness: 1 }))); m.rotation.x = -PI / 2; m.position.set(x, y, z); m.receiveShadow = true; return m; };
cha(3000, 2400, 0, ZH - 1200, V_.grama); [-1, 1].forEach(s => { cha(XM - XA, 8.5 - 1.5, s * (XM + XA) / 2, -5, 0x3b3d45, .04); cha(XM - XA, 1.5, s * (XM + XA) / 2, -.75, 0xd9d7d0, .05); cha(XM - XA, 5.5, s * (XM + XA) / 2, -11.25, 0xd9d7d0, .05); for (let x = XA + 3; x < XM; x += 7) add(box(3, .03, .16, 0xf2d24a, .01)).position.set(s * x, .07, -5); });
cha(2 * XA, 3, 0, ZH + 1.45, 0xd9d7d0, .05);
{ const P_ = [], c = [], ar = []; for (let x = -420; x < 420; x += 22) for (let z = -30; z > -300; z -= 22) { const q = rnd(), near = z > -60; if (q < (near ? .85 : .45)) P_.push({ x: x + (rnd() - .5) * 3, z: z + (rnd() - .5) * 3, w: 16, d: 15, h: near ? 16 + rnd() * 46 : 10 + rnd() * 30, c: corDe([0xeaeef2, 0x8fc4e0, 0xf1cda0, 0x7fbfb8, 0xe29a7a, 0xb5c0dc, 0xf4efe6, 0xd9a0a8]), t: -5 }); else if (q < .8) c.push({ x, z, s: 3.6, ry: 0, t: -5 }); else ar.push({ x, z, s: 3.5, t: -5 }); } predios(P_); casas(c); arvores(ar); const a2 = []; for (let x = -280; x < 280; x += 14) if (Math.abs(x) > 60) a2.push({ x, z: -12.4, s: 2.1, t: -5 }); arvores(a2); }

// rua sobre a estação: some na obra e volta no fim ----------------------------------------------------------------------------------------
const T_RUA = fim(6) + .1, G_RUA = funde([[gb(5, .3, 7, 0, -.28, -5), 0x3b3d45], [gb(5, .3, 1.5, 0, -.25, -.75), 0xd9d7d0], [gb(2.4, .03, .16, 0, .03, -5), 0xf2d24a]]), NRU = 18, RUA = []; for (let i = 0; i < NRU; i++) RUA.push({ x: -XA + 2.5 + i * 5, t: .18 + Math.abs(i - 8.5) * .05, r: (i % 2 ? 1 : -1) * .5 });
moveis(G_RUA, NRU, [0xffffff], (i, t) => { const b = RUA[i]; if (t >= T_RUA + i * .02) return [b.x, 0, 0, 0, 0]; if (t >= fim(0) + .02) return null; const fura = Math.abs(i - 8.5) < 4.2, q = fura ? Math.max(0, t - b.t) : 0; return [b.x, -q * q * 10, 0, 0, b.r * Math.min(1, q * 1.4)]; });
const G_BUS = funde([[gb(12, 2.6, 2.6, 0, .55)], [gb(12.05, .9, 2.65, 0, 1.75), 0xaee3f7], [gb(12.05, .5, 2.65), 0x24262a], ...[-3.6, 3.6].flatMap(x => [[-1.32, 1.32].map(z => [gc(.55, .55, .3, 12).rotateX(PI / 2).translate(x, .55, z), 0x1e2026])]).flat()]);
const T_Q = .32; moveis(G_BUS, 1, [V_.faixa], (i, t) => { const x = 2 - Math.min(t, T_Q) * 7, q = Math.max(0, t - T_Q); return [x + q * 1.5, .02 - q * q * 8.2, -3.2, 0, -Math.min(1.05, q * 1.5)]; }, { de: 0, ate: fim(0) + .02 });
const NPO = 280, po = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 0), mat(0x9a6a44, { flatShading: true, roughness: 1 }), NPO); po.frustumCulled = false; add(po); const PO = []; for (let i = 0; i < NPO; i++) PO.push({ x: (rnd() - .5) * 28, z: -1 - rnd() * 8, t: .14 + rnd() * .9, s: .2 + rnd() * .75, vx: (rnd() - .5) * 5, r: rnd() * 6 });
AUTO.push(t => { const on = t < fim(0) + .02; po.visible = on; if (!on) return; for (let i = 0; i < NPO; i++) { const b = PO[i], q = t - b.t; if (q <= 0) { O.scale.setScalar(0); O.position.set(0, -9, 0); } else { O.position.set(b.x + b.vx * q, Math.max(-13.4, -.2 - 8 * q * q), b.z); O.rotation.set(b.r + q * 3, b.r, q); O.scale.setScalar(b.s); } O.updateMatrix(); po.setMatrixAt(i, O.matrix); } po.instanceMatrix.needsUpdate = true; });

// a terra dentro do terreno da estação: blocos que saem camada por camada ------------------------------------------------------------------------
const CX = 8, CY = 16, CELA = [], tD0 = F(2) + .3, tDD = Math.max(1.5, fim(2) - tD0 - .3); for (let a = 0; a < CX; a++) for (let b = 0; b < CY; b++) { const x0 = -XA + a * (2 * XA / CX), x1 = x0 + 2 * XA / CX, y1 = -b * (-YF / CY), y0 = y1 + YF / CY, m = bm(x0, x1, y0, y1, ZH, 0, mTc); CELA.push({ m, a, b, t: tD0 + (b + ((a * 3) % CX) / CX) / CY * tDD, abre: Math.abs(x0 + x1) / 2 < 17 && y1 < -2.9, cai: Math.abs(x0 + x1) / 2 < 17 }); }
const yPit = t => YF * clamp((t - tD0) / tDD);
AUTO.push(t => { CELA.forEach(c => { c.m.visible = t < fim(0) + .02 ? !(c.abre || (c.cai && t > .16 + c.a * .03)) : t < c.t; }); mTc.opacity = t > F(1) + .3 && t < F(3) ? .3 : 1; mTc.depthWrite = !(t > F(1) + .3 && t < F(3)); });
AUTO.push(t => { }); for (let q = tD0; q < tD0 + tDD; q += .35) som(q, 'motor');

// paredes de concreto enfiadas na terra -------------------------------------------------------------------------------------------------------------------
const dP = rest(T.par, 1), H_W = -YF + 3;
{ const l = [], n = 24; for (let i = 0; i < n; i++) { const x = -XA + (i + .5) * 2 * XA / n; l.push({ x, z: ZB - .45, y: YF - 2.9, sx: 2 * XA / n - .08, sy: H_W, sz: .9, dy: 7, t: T.par + .05 + ((i * 7) % n) / n * dP * .8, c: i % 2 ? CONC : CONC2 }); } [-1, 1].forEach(s => { [-.9, -3.8, -6.7, -9.6].forEach((z, k) => { l.push({ x: s * (XA + .45), z, y: YE + RH, sx: .9, sy: -YE - RH + .2, sz: 2.8, dy: -YE, t: T.par + .3 + k * .35 + (s > 0 ? .2 : 0), c: CONC }); l.push({ x: s * (XA + .45), z, y: YF - 2.9, sx: .9, sy: YE - RH - YF + 2.9, sz: 2.8, dy: H_W, t: T.par + .45 + k * .35 + (s > 0 ? .2 : 0), c: CONC2 }); }); }); frota(UNI, mat(0xffffff, { roughness: .7 }), l, { modo: 'desce', d: .55 }); for (let q = T.par; q < T.par + dP; q += .26) som(q, 'impact'); }
const G_CLAM = funde([[gb(7, 1, 4, 0, 0), 0x333844], [gb(4, 2.4, 3.4, 0, 1), AMAR], [barraG([0, 3, 0], [0, 20, 3.5], .6), AMAR], [gb(.14, 12, .14, 0, 9, 3.7), 0x24262a]]);
moveis(G_CLAM, 2, [0xffffff], (i, t) => [-XA + ((i * .5 + clamp((t - T.par) / dP) * .55)) * 2 * XA, 0, ZB - 5.2 + 0, PI], { de: F(1) - .02, ate: fim(1) + .05 });

// escoras de aço, nível por nível, mais vigas de apoio -------------------------------------------------------------------------------------------------------------
const NIV = [-6.5, -12.5, -18.5], tE0 = T.esc + .05, dE = rest(T.esc, 2), T_TIRA = T.pla + 1.2;
{ const l = [], w = [], n = 13; NIV.forEach((y, k) => { for (let i = 0; i < n; i++) { const x = -40 + i * 6.667; l.push({ a: [x, y, ZB], b: [x, y, -.3], t: tE0 + k / 3 * dE * .7 + i * .03 }); } w.push({ x: 0, z: ZB + .4, y: y - .4, sx: 90, sy: .8, sz: .8, c: 0x4a5564, t: tE0 + k / 3 * dE * .7 - .15, m: 'estica' }); }); cabos(l, AMAR, .55, { sombra: true, d: .22, ate: T_TIRA }); frota(gb(1, 1, 1), mat(0xffffff), w, { d: .3, ate: T_TIRA }); for (let i = 0; i < 3; i++) som(tE0 + i / 3 * dE * .7, 'tijolo'); }
{ const G = funde([[gb(5, .8, 2.6, 0, 0), 0x333844], [gb(3, 1.8, 2.4, 0, .8), AMAR], [barraG([1, 2, 0], [3.6, 3.8, 0], .4), AMAR], [barraG([3.6, 3.8, 0], [5.2, .8, 0], .3), AMAR], [gb(1, .8, 1.2, 5.2, 0), 0x56606e]]); moveis(G, 2, [0xffffff], (i, t) => { const y = Math.max(yPit(t), YF), x = -24 + i * 42 + Math.sin(t * 1.3 + i) * 3; return [x, y + .05, -6, i ? PI : 0]; }, { de: F(2), ate: fim(2) + .1 }); }
moveis(funde([[gb(9, 1.1, 2.6, 0, .4), 0x333844], [gb(2.6, 1.9, 2.5, 3.1, 1.3), MAQ], [gb(5.6, 1.5, 2.4, -1.4, 1.5), 0xc9652d]]), 3, [0xffffff], (i, t) => [-XA - 14 - i * 11 + ((t * 3) % 11), 0, -5, 0], { de: F(2), ate: T.est + 6 });

// tatuzão -----------------------------------------------------------------------------------------------------------------------------------------------------------
const X0 = 30, X1 = 138, X2 = 166, tD = T.tat - .4, tP = Math.min(fim(3) - .6, T.tat + 1.5), TBM = new THREE.Group(); add(TBM); const CAB = new THREE.Group();
{ const cy = (r, l, c, x, o = {}) => { const m = add(sh(new THREE.Mesh(new THREE.CylinderGeometry(r, r, l, 40).rotateZ(PI / 2), mat(c, { roughness: .45, metalness: .25, ...o }))), TBM); m.position.x = x; return m; }; cy(RT + .05, 10.5, MAQ, -5.6); cy(RT - .05, .4, 0xe0403a, -.7); cy(RT - .05, .4, 0x333844, -3.5); cy(RT - .05, .4, 0x333844, -8); for (let i = 0; i < 8; i++) { const a = i / 8 * 6.283; add(box(10, .16, .16, 0x333844, .02), TBM).position.set(-5.6, Math.cos(a) * (RT + .05), Math.sin(a) * (RT + .05)); } TBM.add(CAB); const dis = add(sh(new THREE.Mesh(new THREE.CylinderGeometry(RT + .1, RT + .1, .6, 44).rotateZ(PI / 2), mat(0x3c424c, { metalness: .4, roughness: .4 }))), CAB); dis.position.x = .1; for (let i = 0; i < 6; i++) { const g = new THREE.Group(); g.rotation.x = i / 6 * 6.283; CAB.add(g); add(box(.5, .34, RT * 2 - .3, 0xe0a800, .03), g).position.set(.5, 0, 0); for (let k = 0; k < 7; k++) { const c = add(cil(.2, .2, .16, 0xdfe5ec, 14), g); c.rotation.z = PI / 2; c.position.set(.72, 0, -RT + .5 + k * .95); } } add(cil(.7, 1.1, .7, 0xffc61a, 20), CAB).rotation.z = -PI / 2;
  for (let i = 0; i < 3; i++) { const x = -15 - i * 6.6, g = add(box(6, 1.5, 2.6, i % 2 ? 0x56606e : 0x46505e, .05), TBM); g.position.set(x, -1.1, 0); add(box(5.6, .4, .05, 0xffb627, .01), TBM).position.set(x, -1, 1.33); add(box(6, .2, 1.2, 0xd9a55f, .02), TBM).position.set(x, -1.75, 2.1); [-2.2, 2.2].forEach(a => { const r_ = add(cil(.4, .4, 3.2, 0x24262a, 14), TBM); r_.rotation.x = PI / 2; r_.position.set(x + a, -2.6, 0); }); }
  add(box(21, .1, .1, AMAR, .01), TBM).position.set(-21, -.75, 2.65); }
const xTB = t => t < F(4) ? X0 : t < F(5) ? X0 + (X1 - X0) * liso(4, t) : X1 + (X2 - X1) * liso(5, t), yTB = t => 9 + (YE - 9) * ease((t - tD) / (tP - tD)), T_SAI = F(6) - .02;
AUTO.push(t => { const on = t >= tD - .05 && t < T_SAI; TBM.visible = on; if (!on) return; TBM.position.set(xTB(t), yTB(t), 0); CAB.rotation.x = t >= F(4) ? (t - F(4)) * 2.2 : 0; });
frota(UNI, mat(0xffffff), [{ x: 12, z: 0, y: YF, sx: 64, sy: YE - RT - .25 - YF, sz: 5, c: 0x9a968f, t: F(3) - .1 }, { x: 12, z: 0, y: YE - RT - .25, sx: 64, sy: .12, sz: 5, c: 0x56606e, t: F(3) - .1 }], { d: .3, de: F(3) - .1, ate: T_SAI });
// guindaste que desce a máquina
{ const G = funde([[gb(9, 1.2, 6, 0, 0), 0x333844], [gb(5, 3, 5, 0, 1.2), AMAR], [barraG([0, 4, 0], [0, 40, 16], .8), AMAR]]); frota(G, mV, [{ x: X0 - 5.6, z: -17, y: 0, c: 0xffffff, t: F(3) - .5 }], { de: F(2) + 1, ate: fim(3) + .1 }); const c1 = add(new THREE.Mesh(UNI, mat(0x24262a))); AUTO.push(t => { const on = t >= tD - .05 && t < fim(3) - .1; c1.visible = on; if (on) { const y = yTB(t) + RT; c1.position.set(X0 - 5.6, y, -1); c1.scale.set(.14, 40 - y, .14); } }); }
// lascas de terra saindo da frente
{ const n = 90, G = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.2, 0), mat(0x8f7350, { flatShading: true }), n); G.frustumCulled = false; add(G); AUTO.push(t => { const on = t >= F(4) && t < fim(5) && xTB(t) > 45; G.visible = on; if (!on) return; const x = xTB(t); for (let i = 0; i < n; i++) { const c = (t * 1.4 + i * .137) % 1, a = i * 2.4; O.position.set(x + .9 + (i % 5) * .15, YE + Math.sin(a) * RT * .8 - c * c * 5, .4 + Math.abs(Math.cos(a)) * RT * .7); O.rotation.set(i, i * 2, t); O.scale.setScalar(.7 + (i % 3) * .5); O.updateMatrix(); G.setMatrixAt(i, O.matrix); } G.instanceMatrix.needsUpdate = true; }); }
// esteira levando a terra da frente até o caminhão na rua
const YBE = YE + 1.3, ZBE = -2.3, bandaD = add(box(1, .24, 1.1, 0x24262a, .02)), PX = [[0, YBE, ZBE], [XA - 40 + 8, YBE, ZBE], [22, YBE, -6], [6, .9, -6]]; bandaD.position.set(0, YBE - .2, ZBE);
const bandaR = add(new THREE.Mesh(UNI, mat(0x24262a))); const bandaS = barraG([22, YBE - .2, -6], [6, .7, -6], .9), rmp = add(new THREE.Mesh(new THREE.BufferGeometry().copy(bandaS), mat(0x46505e))); rmp.castShadow = true;
AUTO.push(t => { const on = t >= T.est - .1 && t < T_SAI; bandaD.visible = rmp.visible = on; bandaR.visible = false; if (!on) return; const x = xTB(t) - 12; bandaD.scale.x = Math.max(1, x - 26); bandaD.position.x = (x + 26) / 2; });
{ const n = 300, G = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(.32, 0), mat(0x9a7a55, { flatShading: true }), n); G.frustumCulled = false; add(G); AUTO.push(t => { const on = t >= T.est && t < T_SAI; G.visible = on; if (!on) return; const x0 = xTB(t) - 12, La = Math.max(1, x0 - 26), Lb = Math.hypot(16, YBE), L = La + Lb; for (let i = 0; i < n; i++) { const u = ((i * .618 + t * 7 / L * 1.6) % 1) * L; if (u < La) O.position.set(x0 - u, YBE + .1, ZBE + ((i * 7) % 5 - 2) * .1); else { const k = (u - La) / Lb; O.position.set(22 - 16 * k, YBE + (.9 - YBE) * k + .3, -6); } O.rotation.set(i, i, 0); O.scale.setScalar(.7 + (i % 3) * .3); O.updateMatrix(); G.setMatrixAt(i, O.matrix); } G.instanceMatrix.needsUpdate = true; }); }

// anéis: a ordem de instâncias já é a ordem de montagem -----------------------------------------------------------------------------------------------------------------
const LA = 1.5, NAD = Math.floor((XM - XA) / LA), G_AN = new THREE.CylinderGeometry(RT + .3, RT + .3, LA * .95, 28, 1, true, PI, PI).rotateZ(PI / 2), mAn = mat(0xffffff, { roughness: .8, side: THREE.DoubleSide }), an = [1, -1].map(s => { const m = new THREE.InstancedMesh(G_AN, mAn, NAD); m.frustumCulled = false; m.receiveShadow = true; add(m); for (let i = 0; i < NAD; i++) { O.position.set(s * (XA + (i + .5) * LA), YE, 0); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); m.setMatrixAt(i, O.matrix); COR.set([0xcfccc3, 0xbfbcb3, 0xd8d5cc, 0xb5b2a9][i % 4]); m.setColorAt(i, COR); } return m; });
const borda = [1, -1].flatMap(s => [RT + .15, -RT - .15].map(o => { const m = add(new THREE.Mesh(gb(1, .4, .16, .5, -.2), mat(0xe2e0d8))); m.position.set(s > 0 ? XA : -XA, YE + o, -.05); if (s < 0) m.scale.x = -1; m.userData.s = s; return m; })); const CAUDA = t => xTB(t) - 12, T_INT = T_SAI + .01;
AUTO.push(t => { const nD = t >= T_INT ? NAD : Math.max(0, Math.floor((CAUDA(t) - XA) / LA)); an[0].count = nD; an[0].visible = nD > 0; an[1].visible = t >= T_INT; const ld = nD * LA; borda.forEach(b => { b.visible = b.userData.s > 0 ? nD > 0 : t >= T_INT; b.scale.x = (b.userData.s > 0 ? 1 : -1) * Math.max(ld, 1); }); });
for (let q = F(5) + .3; q < fim(5); q += .42) som(q, 'tijolo');
// a montadora: dois braços girando logo atrás da blindagem
moveis(funde([[gb(.5, RT - .5, .5, 0, 0), 0xe0403a], [new THREE.CylinderGeometry(RT + .1, RT + .1, 1.4, 16, 1, false, -.5, 1).rotateX(0).toNonIndexed().rotateZ(0), 0xcfccc3]]), 1, [0xffffff], (i, t) => [CAUDA(t) + .75, YE, 0, PI / 2, 2.1 + Math.sin(t * 1.9) * .85], { de: F(4), ate: T_SAI });
// terra tampando o túnel adiante
const tampa = [1, -1].map(s => { const g = uvM(new THREE.PlaneGeometry(1, RH * 2).translate(.5, YE, .0)), m = add(new THREE.Mesh(g, mT)); m.position.z = .02; m.receiveShadow = true; if (s < 0) { m.position.x = -XM; m.scale.x = XM - XA; g.attributes.uv.setX(0, -XM / 180); g.attributes.uv.setX(1, -XA / 180); g.attributes.uv.setX(2, -XM / 180); g.attributes.uv.setX(3, -XA / 180); } return m; });
AUTO.push(t => { const on = t < T_INT; tampa.forEach(m => { m.visible = on; }); if (!on) return; const x = Math.max(XA, xTB(t) + .05), m = tampa[0], u = m.geometry.attributes.uv; m.position.x = x; m.scale.x = XM - x; u.setX(0, x / 180); u.setX(2, x / 180); u.setX(1, XM / 180); u.setX(3, XM / 180); u.needsUpdate = true; });

// estação: base, plataforma, mezanino, laje, colunas ---------------------------------------------------------------------------------------------------------------------
const dE6 = rest(T.pla, 6), XE0 = -6, XE1 = 14, tZ = x => T.pla + .1 + (x + XA) / (2 * XA) * dE6 * .7;
{ const b = [], c = [], lj = []; for (let x = -XA + 3.75; x < XA; x += 7.5) { b.push({ x, z: ZB / 2, y: YF, sx: 7.55, sy: YR - YF - .1, sz: -ZB, c: x % 2 ? 0x8d8a84 : 0x9a968f, t: F(6) - .2, sub: 4 }); } for (let x = -XA + 2.5; x < XA; x += 5) { lj.push({ x, z: (ZB - 1.7) / 2, y: YR, sx: 5.03, sy: 1.1, sz: -ZB - 1.7, c: 0xd9d7d0, t: tZ(x), m: 'sobe', sub: 1.1 }, { x, z: -1.75, y: YP - .02, sx: 5.03, sy: .03, sz: .36, c: 0xffd23f, t: tZ(x) + .1 }); if (!(x > 9 && x < 31)) lj.push({ x, z: ZB / 2 - .0, y: YM - .6, sx: 5.03, sy: .6, sz: -ZB, c: x % 10 > 5 ? CONC : CONC2, t: tZ(x) + .35, dy: 6, m: 'desce' }); if (!(x > XE0 && x < XE1)) lj.push({ x, z: ZB / 2, y: -1.1, sx: 5.03, sy: .8, sz: -ZB, c: CONC2, t: tZ(x) + .55, dy: 6, m: 'desce' }); else lj.push({ x, z: (-8.3) / 2, y: -1.1, sx: 5.03, sy: .8, sz: 8.3, c: CONC2, t: tZ(x) + .55, dy: 6, m: 'desce' }); } for (let x = -40; x <= 40; x += 10) { c.push({ x, z: -6, y: YP, sx: .85, sz: .85, sy: YM - .6 - YP, sub: 4, c: 0xe9e6dd, t: tZ(x) + .2 }); c.push({ x, z: -6, y: YM, sx: .85, sz: .85, sy: -1.1 - YM, sub: 3, c: 0xe9e6dd, t: tZ(x) + .45 }); } frota(UNI, mat(0xffffff), b, { modo: 'sobe', d: .3 }); frota(UNI, mat(0xffffff, { roughness: .6 }), c, { modo: 'sobe', d: .3 }); frota(UNI, mat(0xffffff, { roughness: .6 }), lj, { d: .3 }); for (let q = T.pla; q < T.pla + dE6; q += .24) som(q, 'tijolo');
  const ac = [], tA = fim(6) - .1; for (let i = 0; i < 18; i++) ac.push({ x: -XA + 2.5 + i * 5, z: ZB + .15, y: YP, sx: 4.96, sy: YM - .6 - YP, sz: .1, c: i % 3 === 1 ? V_.faixa : 0xe8efef, t: tA + i * .03 }); frota(UNI, mat(0xffffff, { roughness: .35 }), ac, { d: .2 }); const sg = tex(512, 64, (g, w, h) => { g.fillStyle = '#17324d'; g.fillRect(0, 0, w, h); g.fillStyle = '#fff'; g.font = '900 44px Arial'; g.textAlign = 'center'; g.fillText('ESTAÇÃO CENTRO', w / 2, 47); }), pl = add(new THREE.Mesh(new THREE.BoxGeometry(12, 1.5, .1), new THREE.MeshBasicMaterial({ map: sg }))); pl.position.set(-10, YM - 2.2, ZB + .3); aparece(pl, tA + .5, .25); }
// luzes do teto
const LUZS = []; for (let x = -42; x <= 42; x += 7) LUZS.push([x, YM - .68, -3], [x, YM - .68, -8.5], [x, -1.2, -3], [x, -1.2, -8.5]); const lzE = brilhos(LUZS, 0xfff2cf, 3.4); { const l = LUZS.map((p, i) => ({ x: p[0], z: p[2], y: p[1], sx: 3, sy: .1, sz: .3, c: 0xfff6dc, t: fim(6) + i * .002 })); frota(UNI, new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false }), l, { sombra: false, d: .2 }); }

// trilhos: dormentes, trilho e terceiro trilho ---------------------------------------------------------------------------------------------------------------------------------
const dT = rest(T.tri, 7), XTS = 240, tSl = x => T.tri + .05 + (x + XTS) / (2 * XTS) * dT * .78;
{ const l = [], s = []; for (let x = -XTS; x < XTS; x += .75) if (Math.abs(x) < XTS) l.push({ x, z: 0, y: YR, sx: .26, sy: .18, sz: 2.5, c: 0x8d8a84, t: tSl(x) }); s.push({ x: -XM, z: 0, y: YR - .5, sx: 2 * XM, sy: .5, sz: 3.4, c: 0x9a968f, t: F(7) - .1, m: 'estica' }); frota(gb(1, 1, 1, .5), mat(0xffffff), s, { d: .4 }); frota(UNI, mat(0xffffff), l, { d: .16 }); const r = [-.72, .72].map(z => ({ x: -XTS, z, y: YR + .18, sx: 2 * XTS, sy: .16, sz: .08, c: 0xc7ced6, t: T.tri + .05, d: dT * .82, m: 'estica' })); r.push({ x: -XTS, z: -1.42, y: YR + .28, sx: 2 * XTS, sy: .2, sz: .24, c: 0xffc61a, t: tk('terceiro', 7) + .1, d: Math.max(.8, fim(7) - tk('terceiro', 7) - .3), m: 'estica' }); frota(gb(1, 1, 1, .5), mat(0xffffff, { metalness: .6, roughness: .3 }), r); }
moveis(funde([[gb(9, 1.6, 2.5, 0, .1), MAQ], [gb(2, 1, 2.2, -3, 1.7), 0xaee3f7]]), 1, [0xffffff], (i, t) => [-XTS + clamp((t - T.tri - .05) / (dT * .82)) * XTS * 2, YR + .3, 0, 0], { de: F(7), ate: fim(7) + .05 }); for (let q = T.tri; q < T.tri + dT; q += .2) som(q, 'toc');

// escadas rolantes ----------------------------------------------------------------------------------------------------------------------------------------------------------------
const EP = [{ a: [31, YP, -9.8], b: [15, YM, -9.8] }, { a: [15, YM, -9.8], b: [-1, .15, -9.8] }, { a: [31, YP, -8.4], b: [15, YM, -8.4] }, { a: [15, YM, -8.4], b: [-1, .15, -8.4] }], dR = rest(T.rol, 8);
{ const c = [], m = []; EP.forEach((e, i) => { const t0 = T.rol + .1 + (i % 2) * dR * .4; [-.62, .62].forEach(o => c.push({ a: [e.a[0], e.a[1] + 1, e.a[2] + o], b: [e.b[0], e.b[1] + 1, e.b[2] + o], t: t0 + .2 })); m.push({ a: [e.a[0], e.a[1] - .3, e.a[2]], b: [e.b[0], e.b[1] - .3, e.b[2]], t: t0 }); }); cabos(c, 0x24262a, .12, { d: .8, sombra: true }); cabos(m, 0x7a8796, 1.45, { d: .7, sombra: true }); const n = 32, G = gb(.95, .18, 1.1); moveis(G, n * 4, [0xf4efe6, 0xd9d7d0], (i, t) => { const q = Math.floor(i / n), e = EP[q], t0 = T.rol + .3 + (q % 2) * dR * .4; if (t < t0) return null; const u = (((i % n) + (t - t0) * 2.6) / n) % 1, ex = clamp((t - t0) * 2); return [e.a[0] + (e.b[0] - e.a[0]) * u * ex, e.a[1] + (e.b[1] - e.a[1]) * u * ex + .14, e.a[2], 0]; }, { de: T.rol }); for (let q = T.rol; q < T.rol + dR; q += .3) som(q, 'zumbido'); }
// entrada na calçada de trás
{ const l = [{ x: 5, z: -10.8, y: 0, sx: 21, sy: 3.4, sz: .2, c: 0x9cc9df, t: T.rol + 1 }, { x: 5, z: -9.8, y: 3.4, sx: 22, sy: .3, sz: 5, c: V_.faixa, t: T.rol + 1.2, m: 'desce' }]; frota(UNI, mat(0xffffff, { roughness: .4 }), l, { d: .3 }); }

// ventiladores -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
const VX = [35.5, 41], T_VL = T.ven + .3, VENT = VX.map(x => { const g = new THREE.Group(); g.position.set(x, -5, -7.2); add(g); const a = add(new THREE.Mesh(new THREE.TorusGeometry(2.1, .24, 12, 40), mat(0x56606e, { metalness: .4 })), g); a.castShadow = true; const p = new THREE.Group(); g.add(p); add(cil(.5, .5, .5, 0x333844, 20), p).rotation.x = PI / 2; for (let i = 0; i < 6; i++) { const b = add(box(.7, 1.9, .05, AMAR, .02), p); b.rotation.z = i / 6 * 6.283; b.position.set(Math.sin(i / 6 * 6.283) * -1.1, Math.cos(i / 6 * 6.283) * 1.1, 0); } g.userData.p = p; aparece(g, T_VL - .5, .3); return g; });
AUTO.push(t => { VENT.forEach(g => { g.userData.p.rotation.z = t > T_VL ? -(t - T_VL) * 13 : 0; }); });
{ const c = [{ x: 38, z: -7.2, y: -5.4 + 3, sx: 11.5, sy: 1.7, sz: 4.6, c: 0xaab2bc, t: T.ven - .1 }, { x: 40, z: -7.2, y: -1.3, sx: 5, sy: 5.3, sz: 4.6, c: 0xaab2bc, t: T.ven - .05 }, { x: 40, z: -11.4, y: 3.9, sx: 6, sy: .3, sz: 5, c: 0x46505e, t: T.ven }]; frota(UNI, mat(0xffffff, { metalness: .3, roughness: .5 }), c, { d: .25 }); const P_ = [[[40, 5, -8], [40, 1, -7.2], [38, -3, -7.2], [38, -7, -5.5], [25, -9, -3], [8, -12, -3], [-24, -14, -3]], [[42, 5, -7], [42, 1, -7.2], [36, -3, -7.2], [34, -7, -5], [16, -13, -2.6], [-10, -15, -4]], [[39, 5, -7], [39, 1, -7.2], [36, -2, -7.2], [33, -6.5, -3], [20, -7, -4], [-20, -7, -4]]]; pulsos(P_, 170, 0x9fe0ff, 1.1, T_VL, fim(9) + .1, .32, 1.6); for (let q = T_VL; q < fim(9); q += 1) som(q, 'zumbido'); }

// sinais no túnel -----------------------------------------------------------------------------------------------------------------------------------------------------------------------
const XSI = []; for (let x = 52; x < 300; x += 24) XSI.push(x); for (let x = -52; x > -300; x -= 24) XSI.push(x);
{ const c = XSI.map(x => ({ x, z: -2.4, y: YR, sx: .15, sy: 3.1, sz: .15, c: 0x333844, t: T.sin + .1 + Math.abs(x) * .004 })), b = XSI.map(x => ({ x, z: -2.32, y: YR + 2.7, sx: .55, sy: 1.5, sz: .3, c: 0x1e2026, t: T.sin + .12 + Math.abs(x) * .004 })); frota(UNI, mat(0xffffff), c, { d: .2 }); frota(UNI, mat(0xffffff), b, { d: .2 }); }
const lzV = brilhos(XSI.map(x => [x, YR + 3.8, -2.12]), 0xff3a2a, 2.4), lzD = brilhos(XSI.map(x => [x, YR + 3.1, -2.12]), 0x3aff7a, 2.4), T_VE = fim(10) - 1.4;
AUTO.push(t => { const on = t >= T.sin + .3; lzV.op(on && t < T_VE ? 1 : 0); lzD.op(on && t >= T_VE ? 1 : 0); }); som(T_VE, 'ding');

// trem e gente ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
const NV_ = 4, LV_ = 22.4, Xp = -42, T_ST = T_USO + 3.6, T_PT = D.total - .2, xTr = t => { if (t < T_ST) return Xp + (T_ST - t) ** 2 * 7.5; return t < T_PT ? Xp : Xp - (t - T_PT) ** 2 * 7; };
const G_VAG = funde([[gb(21.8, 3.05, 2.9, 0, .65)], [gb(21.82, .55, 2.92, 0, 1.3), V_.faixa], ...[-1, 1].flatMap(s => { const L = []; for (let i = 0; i < 6; i++) L.push([gb(2.1, .85, .05, -9 + i * 3.6, 2.2, s * 1.46), 0x2c4258]); return L; }), ...[-6.8, 6.8].map(x => [gb(3, .65, 2.2, x, 0), 0x24262a]), [gb(21.8, .1, 2.6, 0, 3.7), 0x8a95a3]]);
moveis(G_VAG, NV_, [V_.trem], (i, t) => [xTr(t) + 10.9 + i * LV_, YR + .34, 0, 0], { de: F(LAST) - .05 });
const ABR = t => t >= T_ST + .3 && t < T_PT - 1.2; moveis(gb(1.9, 2.3, .07), NV_ * 3, [0x101820], (i, t) => { if (!ABR(t)) return null; const v = Math.floor(i / 3), k = i % 3; return [Xp + 10.9 + v * LV_ - 7.2 + k * 7.2, YR + 1, -1.49, 0]; }, { de: F(LAST) });
const lzT = brilhos(Array.from({ length: 2 }, () => [0, -99, 0]), 0xfff4c8, 5); AUTO.push(t => { lzT.op(t >= F(LAST) && t < T_ST ? 1 : 0); const x = xTr(t); lzT.pos[0] = x; lzT.pos[1] = YR + 1.5; lzT.pos[2] = .9; lzT.pos[3] = x; lzT.pos[4] = YR + 1.5; lzT.pos[5] = -.9; lzT.sync(); });
const G_PES = funde([[gb(.4, .62, .24, 0, .78)], [gb(.2, .22, .2, 0, 1.42), 0xd9a57c], [gb(.16, .8, .2, -.11, 0), 0x2b3a67], [gb(.16, .8, .2, .11, 0), 0x2b3a67]]), r3 = prng(77), GENT = []; for (let i = 0; i < 70; i++) { let x = -40 + r3() * 84; if (Math.abs(x - 4) < 3.5) x += 7; GENT.push({ x, z: -2.6 - r3() * 6.5, b: i % 3 !== 2 }); } const nCid = 30, CID = []; for (let i = 0; i < nCid; i++) CID.push({ x: -44 + r3() * 88, z: i % 2 ? -3 - r3() * 7 : -3 - r3() * 7, v: (r3() - .5) * 2.4, f: r3() * 6 });
moveis(G_PES, GENT.length, [0xd8443a, 0x3a7fd8, 0xf4efe6, 0xffb627, 0x2fbf8f, 0x8e5bd0, 0xeab0a6], (i, t) => { const g = GENT[i], k = g.b ? clamp((t - T_ST - .6 - (i % 9) * .22) / 1) : 0, xd = Math.round((g.x - Xp - 3.7) / 7.46) * 7.46 + Xp + 3.7; if (k >= 1) return null; return [g.x + (xd - g.x) * k, YP, g.z + (-1.5 - g.z) * k, k > 0 ? 3.14 : Math.sin(i) * 2]; }, { de: F(LAST) - .05 });
moveis(G_PES, nCid, [0xd8443a, 0x3a7fd8, 0xf4efe6, 0xffb627, 0x2fbf8f], (i, t) => { const c = CID[i], x = ((c.x + 44 + t * c.v) % 88 + 88) % 88 - 44; return [x, YM + .02, c.z, c.v > 0 ? 1.57 : -1.57]; }, { de: F(LAST) - .05 });
moveis(G_PES, 16, [0xf4efe6, 0xd8443a, 0x3a7fd8, 0xffb627], (i, t) => { const e = EP[i % 2], u = (i * .173 + t * .08) % 1; return [e.a[0] + (e.b[0] - e.a[0]) * u, e.a[1] + (e.b[1] - e.a[1]) * u + .2, -9.8, 1.57]; }, { de: F(LAST) - .05 });
// carros e ônibus na rua, por cima de tudo, depois de pronta
moveis(G_CAR, 24, [0xd83a3a, 0x3a7fd8, 0xf2c94c, 0xf4efe6, 0x2fbf8f, 0x30343c], (i, t) => { const s = i % 2 ? 1 : -1, u = ((i * .137 + t * .016 * (1 + (i % 3) * .2)) % 1), x = s * (-250 + u * 500); if (t < T_RUA && Math.abs(x) < XA + 3) return null; if (t < fim(0) + .1 && t > 0) { } return [x, .08, -5 + s * 1.8, s > 0 ? PI / 2 : -PI / 2]; }, { esc: 2.3, de: 0 });
moveis(G_BUS, 1, [0x3a7fd8], (i, t) => [90 - (t - T_RUA) * 9, .08, -6.8, 0], { de: T_RUA });

// operário ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
const OP = operario(.86), VIS = [
  [[21, 8, 33], [1, -5, -6]],
  [[-7, 14, 34], [-20, -4, -9], 1],
  [[-70, 9, 30], [-43, -7, -6], 1],
  [[20, -8, 36], [32, -15, -6], 1],
  [[X0 + 18, -7, 32], [X0 - 8.5, YE, 0], 1, [X1 + 18, -7, 32], [X1 - 8.5, YE, 0]],
  [[X1 - 30, -9, 15], [X1 - 14, YE + .4, -2], 1, [X2 - 30, -9, 15], [X2 - 14, YE + .4, -2]],
  [[-34, -7, 25], [6, -15, -6], 1],
  [[-34, -13, 10], [-5, YR + .4, -1.5], 1],
  [[48, -3, 23], [22, -9, -6], 1],
  [[11, -1, 21], [35, -5, -6], 1],
  [[92, -13.5, 11], [64, YE - 1, -1.5], 1],
];
const yW = YE - 1.65, ZW = 2.1;
{ const q = (i, x, z, y, g, c = 1) => [F(i), x, z, y, olha(VIS[i][0], x, z), g, c], RT_ = [[0, 19, -.8, .08, olha(VIS[0][0], 19, -.8), 'pasmo'], [fim(0), 19, -.8, .08, 0, 'pasmo'], q(1, -20, -.9, .02, 'bate'), q(2, -47.3, -.8, .08, 'para'), q(3, 34, 1.7, YE - RT - .13, 'para'), q(4, 34, 1.7, YE - RT - .13, 'para', 0), q(5, X1, 0, 0, 'bate'), q(6, 3, -1.2, YR, 'bate'), q(7, -13, -1.5, YR + .02, 'bate'), q(8, 23, -5, YM + .02, 'bate'), q(9, 31, -5, YM + .02, 'bate'), q(10, 68, -1.95, YR + .02, 'bate'), [T_USO, 68, -1.95, YR + .02, 0, 'bate']]; RT_[4][5] = 'para'; roteiro(OP, RT_, T_USO); }
AUTO.push(t => { if (t >= F(4) && t < F(6)) { const { h, r } = OP; h.position.set(xTB(t) - 15, yW + .1, ZW); h.rotation.y = .6; h.scale.setScalar(OP.S); r.anda(0, 0); r.respira(t); const w = Math.sin(t * 8); r.bd.j.rotation.x = -2.35 + w * .42; r.bd.k.rotation.x = -.25; } });
festa(OP, 4, -4.3, .7, T_USO, YP);

// câmera -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
const K = plano(VIS, [{ t: F(LAST) + .03, p: [82, 20, 118], l: [6, -7, -6] }, { t: T_USO - .03, p: [76, 18, 110], l: [6, -7, -6] }, { t: T_USO + .02, p: [60, -9, 26], l: [12, YE, -3] }, { t: T_ST, p: [54, -10, 22], l: [10, YE, -3] }, { t: T_ST + .03, p: [-26, -9, 19], l: [4, YP + .6, -3] }, { t: D.total - 1.5, p: [-20, -10, 16], l: [4, YP + .6, -3] }, { t: D.total + 1, p: [-20, -10, 16], l: [4, YP + .6, -3] }]);

// rótulos e sons ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
etq('SEM ESCORAR', F(0) + .15, fim(0), 'ruim');
[['PAREDES', T.par, fim(1)], ['ESCORAS', T.esc, fim(2)], ['TATUZÃO', T.tat, fim(3)], ['ESTEIRA', T.est, fim(4)], ['ANÉIS', T.ane, fim(5)], ['PLATAFORMA', T.pla, fim(6)], ['TRILHOS', T.tri, fim(7)], ['ESCADAS ROLANTES', T.rol, fim(8)], ['VENTILADORES', T.ven, fim(9)], ['SINAIS', T.sin, fim(10)]].forEach(l => etq(...l));
etq('METRÔ PRONTO!', F(LAST) + .1, T_USO, 'grande');
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); som(.1, 'crack'); som(.25, 'crack'); som(.45, 'desaba'); som(.9, 'impact'); som(1, 'desaba'); som(F(LAST) + .1, 'ding'); som(T_USO + .1, 'whoosh'); for (let q = F(4); q < fim(5); q += 1) som(q, 'motor'); for (let q = F(LAST) + 1; q < T_ST; q += .5) som(q, 'zumbido'); som(T_ST, 'ding'); som(T_ST + .3, 'whoosh'); som(T_PT, 'zumbido');
for (let q = F(1); q < fim(10); q += 1.3) som(q, 'toc');

window.CAPA_T = T_ST + 1.4;
AUTO.push(t => { const k = clamp((t - fim(6)) / .4); lzE.op(k * .5); });
function foco() { return [cam.position.x * .6, -20]; }
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); const f = foco(); segueSol(f[0], f[1]); AUTO.forEach(q => q(t)); });
