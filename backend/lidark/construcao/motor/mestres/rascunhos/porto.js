// Porto de contêineres em tamanho real: draga, aterro, quebra-mar, estacas, cais, defensas, guindastes, pátio, ferrovia e boias; no fim, o navio encosta e descarrega.
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
// Porto de contêineres em tamanho real: draga, aterro, quebra-mar, estacas, cais, defensas, guindastes, pátio, ferrovia e boias; no fim, o navio encosta e descarrega.
cenario(240, 900, 3400); noite(0);
const T = { dra: tk('draga', 1), ate: tk('aterro', 2), que: tk('quebra-mar', 3), est: tk('estacas', 4), cai: tk('cais', 5), def: tk('defensas', 6), gui: tk('guindastes', 7), pat: tk('pátio', 8), fer: tk('ferrovia', 9), boi: tk('boias', 10) };
const rest = (t, i) => Math.max(1.2, fim(i) - t - .25), CONC = 0xc4c1b8, CONC2 = 0xb2afa6, AMAR = 0xffc61a, ACO = 0x8a95a3, AREIA = 0xdcc892;
// o cais corre em x, com o mar em z > 0 ------------------------------------------------------------------------------------
const XC = 280, ZQ = 0, LQ = 40, ZP = -LQ, YQ = 5, YA = 4.2;
const ondas = (() => { const n = 900, m = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: .28, depthWrite: false }), n); m.frustumCulled = false; add(m); const L = []; for (let i = 0; i < n; i++) L.push([(rnd() - .5) * 1600, 20 + rnd() * 800, rnd() * 6, 3 + rnd() * 9]); AUTO.push(t => { L.forEach(([x, z, f, w], i) => { O.position.set(x + Math.sin(t * .4 + f) * 3, .1, z + Math.cos(t * .5 + f) * 2); O.rotation.set(-PI / 2, 0, 0); O.scale.set(w, .32 + Math.sin(t + f) * .12, 1); O.updateMatrix(); m.setMatrixAt(i, O.matrix); }); m.instanceMatrix.needsUpdate = true; }); return m; })();
const mar = add(new THREE.Mesh(new THREE.PlaneGeometry(9000, 9000), mat(V_.mar, { roughness: .24, metalness: .2 }))); mar.rotation.x = -PI / 2; mar.position.z = 4200; mar.receiveShadow = true;
const terra0 = -210; // terra firme original fica atrás do aterro
const cont = add(new THREE.Mesh(new THREE.BoxGeometry(9000, 6, 4000), mat(0x8c7a62))); cont.position.set(0, YA - 3.05, terra0 - 2000); cont.receiveShadow = true; { const g = add(new THREE.Mesh(new THREE.PlaneGeometry(9000, 4000), mat(V_.grama, { roughness: 1 }))); g.rotation.x = -PI / 2; g.position.set(0, YA, terra0 - 2000); g.receiveShadow = true; }
{ const m = []; [-300, -250].forEach(z => { m.push({ x: 0, z, y: YA, sx: 2400, sy: .06, sz: 11, c: 0x44464e }); }); frota(UNI, mat(0xffffff), m, { sombra: false }); const c = [], P_ = [], ar = []; for (let x = -800; x < 800; x += 24) for (let z = -270; z > -760; z -= 24) { if (Math.abs(z + 300) < 16) continue; const q = rnd(); if (q < .12) P_.push({ x, z, y0: YA, w: 16, d: 15, h: 14 + rnd() * 30, c: corDe([0xeaeef2, 0x8fc4e0, 0xf1cda0, 0x7fbfb8, 0xe29a7a, 0xf4efe6]), t: -5 }); else if (q < .72) c.push({ x: x + (rnd() - .5) * 3, z: z + (rnd() - .5) * 3, y: YA, ry: Math.floor(rnd() * 4) * PI / 2, s: 3.6, t: -5 }); else ar.push({ x, z, y: YA, s: 3 + rnd() * 3, pinho: rnd() > .55, t: -5 }); } predios(P_); casas(c); arvores(ar); const mo = []; for (let i = 0; i < 16; i++) mo.push({ x: -1500 + i * 200, z: -1300 - (i % 3) * 120, sx: 300, sy: 160 + rnd() * 120, sz: 240, c: corDe([0x5fae62, 0x4f9f58, 0x6dbb6a]) }); frota(new THREE.IcosahedronGeometry(1, 1), mat(0xffffff, { flatShading: true, roughness: 1 }), mo, { sombra: false }); }

// navios e contêineres --------------------------------------------------------------------------------------------------------
const C_CX = [0xd8443a, 0x2f7fd6, 0xf2a93a, 0x2fbf8f, 0xe9e4d8, 0x8e5bd0, 0xc9652d, 0x4a6fa5, 0x3aa37a, 0xe07a9a];
const G_CX = funde([[gb(12, 2.5, 2.4)], ...[-1, 1].flatMap(s => { const L = []; for (let i = 0; i < 12; i++) L.push([gb(.5, 2.2, .05, -5.5 + i, .15, s * 1.21), 0x000000]); return []; })]);
const mCX = mat(0xffffff, { roughness: .55 }), G_CX2 = (() => { const c = tex(128, 64, (g, w, h) => { g.fillStyle = '#fff'; g.fillRect(0, 0, w, h); g.fillStyle = 'rgba(0,0,0,.2)'; for (let i = 0; i < 16; i++) g.fillRect(i * 8 + 1, 3, 4, h - 6); g.fillStyle = 'rgba(0,0,0,.28)'; g.fillRect(0, 0, w, 3); g.fillRect(0, h - 3, w, 3); }); mCX.map = c; return gb(12, 2.55, 2.42); })();
const casco = (L, B, H, c, c2 = 0x7a2a22) => { const q = new THREE.Shape(); q.moveTo(-L / 2, -B / 2); q.lineTo(L * .3, -B / 2); q.quadraticCurveTo(L * .46, -B / 2, L / 2, 0); q.quadraticCurveTo(L * .46, B / 2, L * .3, B / 2); q.lineTo(-L / 2, B / 2); q.closePath(); const g = new THREE.ExtrudeGeometry(q, { depth: H, bevelEnabled: false }).rotateX(-PI / 2); return funde([[g, c]]); };
function navio(L, B, H, nb, nc, nz, cor, r_) { // grupo com casco, castelo e pilha de contêineres; devolve {g, cx: lista}
  const g = new THREE.Group(); add(g); const m = sh(new THREE.Mesh(casco(L, B, H, cor), mV)); g.add(m); const fx = add(sh(new THREE.Mesh(casco(L * .995, B * .995, 2.4, 0x7a2a22), mV)), g); fx.position.y = -2.3; const bx = -L * .36; add(box(10, 22, B * .78, 0xf4efe6, .04), g).position.set(bx, H + 11, 0); add(box(5, 2.4, B + 2, 0xf4efe6, .04), g).position.set(bx + 2, H + 21, 0); add(box(9.4, 2, B * .74, 0x2c4258, .02), g).position.set(bx + .6, H + 19, 0); add(box(4, 8, 4, 0x24262a, .03), g).position.set(bx - 7, H + 6, 0); const cx = []; const x0 = bx + 10, r2 = prng(r_); for (let b = 0; b < nb; b++) for (let c = 0; c < nc; c++) { const h_ = nz - ((b * 3 + c) % 3 === 0 ? 1 : 0); for (let z = 0; z < h_; z++) cx.push({ x: x0 + 7 + b * 13, y: H + z * 2.6, z: (c - (nc - 1) / 2) * 2.55, c: C_CX[Math.floor(r2() * C_CX.length)], b, cc: c, zz: z }); } const im = new THREE.InstancedMesh(G_CX2, mCX, cx.length); im.frustumCulled = false; im.castShadow = true; g.add(im); cx.forEach((q, i) => { O.position.set(q.x, q.y, q.z); O.rotation.set(0, 0, 0); O.scale.setScalar(1); O.updateMatrix(); im.setMatrixAt(i, O.matrix); COR.set(q.c); im.setColorAt(i, COR); }); return { g, cx, im }; }

// abertura: navio em água rasa bate, tomba e derruba as caixas ---------------------------------------------------------------------------------
const NA = navio(260, 40, 14, 15, 13, 5, V_.casco, 101); NA.g.rotation.order = 'YXZ'; const ZN0 = 250, T_B = .22;
const mE = new THREE.Group(); add(mE); // banco de areia aparecendo
{ const m = add(new THREE.Mesh(new THREE.CircleGeometry(1, 40), mat(0xd9c48e, { roughness: 1 })), mE); m.rotation.x = -PI / 2; m.scale.set(150, 30, 1); m.position.set(20, .12, ZN0); }
const CAI = NA.cx.map((q, i) => ({ ...q, i, cai: q.zz >= 2 && q.cc > 5, r: rnd(), v: 4 + rnd() * 12 })).filter(q => q.cai).slice(0, 260), COPIA = new THREE.InstancedMesh(G_CX2, mCX, CAI.length); COPIA.frustumCulled = false; COPIA.castShadow = true; add(COPIA); CAI.forEach((q, i) => { COR.set(q.c); COPIA.setColorAt(i, COR); });
{ const zr = new THREE.Matrix4().makeScale(0, 0, 0); CAI.forEach(q => NA.im.setMatrixAt(q.i, zr)); NA.im.instanceMatrix.needsUpdate = true; }
const VV = new V3(), NSP = 240, spr = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), mat(0xf2fbff, { roughness: 1, flatShading: true }), NSP); spr.frustumCulled = false; add(spr); const SP = []; for (let i = 0; i < NSP; i++) SP.push({ i: i % CAI.length, a: rnd() * 6.28, s: .6 + rnd() * 2.2, f: rnd() });
const tilt = t => Math.min(.3, Math.max(0, t - T_B) ** 1.3 * .42) * (1 + Math.sin(Math.max(0, t - T_B - 1.4) * 2.2) * .04);
AUTO.push(t => { const on = t < fim(0) + .02; NA.g.visible = COPIA.visible = spr.visible = mE.visible = on; if (!on) return; const q0 = Math.max(0, t - T_B), av = Math.min(t, T_B) * 14 + (1 - Math.exp(-q0 * 4)) * 5.5, ti = tilt(t); NA.g.position.set(14 + av, .6 + ti * 3, ZN0); NA.g.rotation.y = .03; NA.g.rotation.x = ti; NA.g.rotation.z = -Math.min(.035, q0 * .08); NA.g.updateMatrixWorld();
  CAI.forEach((q, i) => { const c = q0 - .08 - (1 - q.zz / 5) * .22 - q.r * .22; VV.set(q.x, q.y + 1.25, q.z).applyMatrix4(NA.g.matrixWorld); let r0 = ti; if (c > 0) { VV.z += (5 + q.v * .9) * c + q.zz * .1; VV.y = Math.max(-.3, VV.y + 3 * c - 8.5 * c * c); VV.x += (q.r - .5) * 8 * c; r0 = ti + c * (1 + q.r * 1.6); } O.position.set(VV.x, VV.y - 1.25, VV.z); O.rotation.set(r0, .03, (q.r - .5) * Math.max(0, c) * 1.3); O.scale.setScalar(1); O.updateMatrix(); COPIA.setMatrixAt(i, O.matrix); }); COPIA.instanceMatrix.needsUpdate = true;
  for (let i = 0; i < NSP; i++) { const b = SP[i], q = CAI[b.i], c = q0 - .55 - b.f * 1.3; if (c <= 0 || c > 1.1) { O.scale.setScalar(0); O.position.set(0, -9, 0); } else { O.matrixAutoUpdate = true; const p = NA.cx[q.i]; O.position.set(p.x + 20 + Math.cos(b.a) * c * 12, Math.max(.2, 15 * c - 12 * c * c), ZN0 + 26 + q.zz * 4 + Math.sin(b.a) * c * 12); O.rotation.set(b.a, b.a, 0); O.scale.setScalar(b.s * (1 - c / 1.3)); } O.updateMatrix(); spr.setMatrixAt(i, O.matrix); } spr.instanceMatrix.needsUpdate = true; });

// draga: casco, bomba e o tubo que chupa o fundo --------------------------------------------------------------------------------------------------
const ZD_ = 230, Dg = new THREE.Group(); add(Dg); { const m = sh(new THREE.Mesh(casco(92, 20, 7, 0xd8443a), mV)); Dg.add(m); add(box(14, 13, 16, 0xf4efe6, .04), Dg).position.set(-28, 13, 0); add(box(15, 2, 17, 0x2c4258, .02), Dg).position.set(-27, 15, 0); add(box(60, 3, 14, 0xc9a56e, .03), Dg).position.set(10, 7.2, 0);[-1, 1].forEach(s => add(box(62, 1.2, .8, 0x46505e, .03), Dg).position.set(10, 8.8, s * 7.4)); add(box(4, 9, 3, AMAR, .03), Dg).position.set(14, 12, -6); const tb = add(cil(1.1, 1.1, 26, 0xffc61a, 16), Dg); tb.rotation.x = 1; tb.position.set(18, 4, 19); add(cil(.8, .8, 40, 0xffc61a, 14), Dg).rotation.z = PI / 2; Dg.children[Dg.children.length - 1].position.set(10, 11, 7); }
const dD = rest(T.dra, 1), liso = (i, c) => ease((c - F(i) - .04) / (dur(i) + .06)), xDr = t => t < F(2) ? -120 + 99 * liso(1, t) : -21 + 110 * liso(2, t);
AUTO.push(t => { const on = t >= F(1) - .02 && t < F(3); Dg.visible = on; if (on) { Dg.position.set(xDr(t), .5 + Math.sin(t) * .1, ZD_); } });
// areia subindo: mancha e riscos no mar atrás da draga (o canal fundo, mais escuro)
{ const n = 44, m = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ color: 0x173f63, transparent: true, opacity: .45, depthWrite: false }), n); m.frustumCulled = false; add(m); AUTO.push(t => { const on = t >= F(1) - .02; m.visible = on; if (!on) return; const fr = xDr(t); for (let i = 0; i < n; i++) { const x = -400 + i * 20; O.position.set(x, .12, ZD_ + 4); O.rotation.set(-PI / 2, 0, 0); O.scale.setScalar(x < fr - 34 ? 1 : 0); O.scale.x = 20.3; O.scale.y = x < fr - 34 ? 86 : 0; O.scale.z = 1; O.updateMatrix(); m.setMatrixAt(i, O.matrix); } m.instanceMatrix.needsUpdate = true; }); }
{ const n = 60, m = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), mat(0xc9a56e, { flatShading: true, roughness: 1 }), n); m.frustumCulled = false; add(m); AUTO.push(t => { const on = t >= T.dra && t < F(2) + .1; m.visible = on; if (!on) return; const x = xDr(t) + 18; for (let i = 0; i < n; i++) { const c = (t * .9 + i * .137) % 1; O.position.set(x + Math.cos(i * 2.4) * c * 7, .4, ZD_ + 34 + Math.sin(i * 2.4) * c * 7); O.scale.set(1 + c * 3, .3, 1 + c * 3); O.rotation.set(0, 0, 0); O.updateMatrix(); m.setMatrixAt(i, O.matrix); } m.instanceMatrix.needsUpdate = true; }); }

// aterro: o jato de areia da draga forma a terra nova ---------------------------------------------------------------------------------------------------
const dA = rest(T.ate, 2), XAT0 = -XC - 10, XAT1 = XC + 10, tAt = T.ate + .05, NCX = 34, NCZ = 18, WC = (XAT1 - XAT0) / NCX, ZC_ = (terra0 - ZQ + 8) / -NCZ;
{ const l = []; for (let a = 0; a < NCX; a++) for (let b = 0; b < NCZ; b++) { const x = XAT0 + (a + .5) * WC, z = terra0 + (b + .5) * ((ZQ + 8 - terra0) / NCZ), d = (b / NCZ); l.push({ x, z, y: -1, sx: WC + 2, sy: YA + 1, sz: (ZQ + 8 - terra0) / NCZ + 1, sub: YA + 2, c: corDe([0xdcc892, 0xd2bd86, 0xe3d09c]), t: tAt + (d * .55 + ((a * 7) % NCX) / NCX * .4) * dA }); } frota(UNI, mat(0xffffff, { roughness: 1 }), l, { modo: 'sobe', d: .45 }); for (let q = tAt; q < tAt + dA; q += .4) som(q, 'chuva'); }
const JATO = 1000, ja = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 0), mat(0xa8824e, { flatShading: true, roughness: 1 }), JATO); ja.frustumCulled = false; add(ja);
AUTO.push(t => { const on = t >= F(2) && t < fim(2) + .1; ja.visible = on; if (!on) return; const x0 = xDr(t) - 2, a = [x0, 24, ZD_ - 8], b = [16 + Math.sin(t * .8) * 8, YA + 1, terra0 + 18 + clamp((t - T.ate) / dA) * 20]; for (let i = 0; i < JATO; i++) { const u0 = (t * .9 + i * .00299) % 1, u = Math.sqrt(u0), h_ = 52 * 4 * u * (1 - u); O.position.set(a[0] + (b[0] - a[0]) * u + Math.sin(i * 2.4) * u * 9, a[1] + (b[1] - a[1]) * u + h_ + Math.cos(i) * u * 4, a[2] + (b[2] - a[2]) * u + Math.cos(i * 1.7) * u * 9); O.scale.setScalar(.3 + u * .8 + (i % 3) * .15); O.rotation.set(i, i, 0); O.updateMatrix(); ja.setMatrixAt(i, O.matrix); } ja.instanceMatrix.needsUpdate = true; });
// tratores espalhando areia
moveis(funde([[gb(4.6, 1.6, 3, 0, .5), AMAR], [gb(2, 1.3, 2.4, -.6, 2.1), 0xaee3f7], [gb(.4, 1.4, 3.8, 2.8, .2), 0x56606e], [gb(5, .7, 3.4, 0, 0), 0x24262a]]), 4, [0xffffff], (i, t) => { const x = -70 + i * 46 + Math.sin(t * .8 + i) * 16; return [x, YA, -70 - i * 9, Math.cos(t * .8 + i) > 0 ? 0 : PI]; }, { de: T.ate + dA * .7, ate: fim(3) });

// quebra-mar: pedra por pedra, do lado do mar aberto -------------------------------------------------------------------------------------------------------------
const inv3 = u => { let a = 0, b = 1; for (let n = 0; n < 14; n++) { const m = (a + b) / 2; if (ease(m) < u) a = m; else b = m; } return F(3) + .04 + (dur(3) + .06) * a; }, tQ = F(3) + .5, dQ = fim(3) - tQ - .3, XQ0 = -190, ZQ_ = 560, QB = [];
{ const l = [], r2 = prng(33); const L = 480; for (let i = 0; i < L; i += 3.4) { const u = i / L, ang = 1.08, x = XC + 60 - i * Math.cos(ang) * .9, z = 80 + i * Math.sin(ang) * 1.05; [[-7, 3.4], [-3.5, 6], [0, 7.2], [3.5, 6], [7, 3.4]].forEach(([o, h_], k) => { for (let c = 0; c < 2; c++) { const s = 2.4 + r2() * 2.6; l.push({ x: x + o * Math.sin(ang) + (r2() - .5) * 2, z: z + o * Math.cos(ang) + (r2() - .5) * 2, y: h_ - s * .8 - c * .6, sx: s, sy: s * (.7 + r2() * .4), sz: s, ry: r2() * 6, c: corDe([0x8d8a84, 0xa3a09a, 0x76736d, 0x9a968f]), t: inv3(u) + k * .03 + c * .05, dy: 14 }); } }); QB.push([x, z]); } frota(new THREE.IcosahedronGeometry(.75, 0), mat(0xffffff, { flatShading: true, roughness: .95 }), l, { modo: 'desce', d: .35 }); for (let q = tQ; q < tQ + dQ; q += .2) som(q, 'tijolo'); }
const qbT = t => QB[Math.floor(liso(3, t) * (QB.length - 1))];
moveis(funde([[gb(40, 2.2, 14, 0, 0), 0x46505e], [gb(40.4, .3, 14.2, 0, 1), 0xd8443a], [gb(8, 7, 7, -14, 2.2), 0xf4efe6], ...Array.from({ length: 22 }, (_, i) => [new THREE.IcosahedronGeometry(1.3, 0).translate(-8 + (i % 8) * 4, 3 + (i % 3), -4 + (i % 4) * 2.6), 0x8d8a84])]), 1, [0xffffff], (i, t) => { const q = qbT(t); return [q[0] + 28, .5, q[1] - 7, -1.05]; }, { de: F(3) - .02, ate: fim(3) + .05 });

// estacas -------------------------------------------------------------------------------------------------------------------------------------------------------------------
const dE = rest(T.est, 4), EX = 5, NXE = Math.floor(2 * XC / EX), ZE = [4, 9.2, 14.4, 19.6, 24.8, 30], tE = (a, b) => T.est + .1 + (((a * .618034) % 1) * .8 + b / 6 * .15) * dE;
{ const l = []; for (let a = 0; a < NXE; a++) ZE.forEach((z, b) => l.push({ x: -XC + (a + .5) * EX, z, y: -2, sx: .62, sz: .62, sy: YQ - .7 + 2, t: tE(a, b), dy: 11, c: b % 2 ? 0x56606e : 0x46505e })); frota(gc(1, 1, 1, 14), mat(0xffffff, { metalness: .4, roughness: .45 }), l, { modo: 'desce', d: .4 }); for (let q = T.est; q < T.est + dE; q += .24) som(q, 'impact'); }
const G_BAL = funde([[gb(30, 2, 18, 0, 0), 0x46505e], [gb(30.2, .3, 18.2, 0, 1.2), 0xd8443a], [gb(5, 3, 5, -9, 2), 0xf4efe6], [gb(1.1, 26, 1.1, 8, 2), AMAR], [gb(5, 1, 3, 8, 28), AMAR], [barraG([-2, 2, 0], [8, 18, 0], .4), AMAR], ...Array.from({ length: 5 }, (_, i) => [gc(.62, .62, 18, 14).rotateZ(PI / 2).translate(-3, 2.7 + (i % 2) * 1.1, 8.2 - i * .7), 0x46505e])]);
const xB = t => -20 + liso(4, t) * 50; moveis(G_BAL, 1, [0xffffff], (i, t) => [xB(t), .5, 44, 0], { de: F(4) - .02, ate: fim(4) + .05 });
moveis(funde([[gb(2.2, 3, 2.2, 0, 0), 0xe0403a], [gb(.25, 20, .25, 0, 3), 0x24262a]]), 1, [0xffffff], (i, t) => [xB(t) + 8, 9 + Math.abs(Math.sin(t * 5)) * 2, 39, 0], { de: F(4) - .02, ate: fim(4) + .05 });

// cais: vigas e laje sobre as estacas --------------------------------------------------------------------------------------------------------------------------------------------
const dC = Math.max(1.6, fim(5) - F(5) - .5), L_C = 15, NLC = Math.floor(2 * XC / L_C), tLC = a => { const x = -XC + (a + .5) * L_C, n = Math.abs(x + 9); return n < 9 ? F(5) - .4 : F(5) + .1 + ((a * .618034) % 1) * .2 * dC + Math.min(n / XC, 1) * dC * .68; };
{ const l = [], v = []; for (let a = 0; a < NLC; a++) { const x = -XC + (a + .5) * L_C; for (let k = 0; k < 2; k++) for (let b = 0; b < 3; b++) l.push({ x: x - 3.75 + k * 7.5, z: 6.5 + b * 12, y: YQ - .3, sx: 7.55, sy: .34, sz: 12.05, c: (a + b + k) % 2 ? CONC : CONC2, t: tLC(a) + .15 + b * .08 + k * .05, dy: 5 }); ZE.forEach(z => v.push({ x, z, y: YQ - 1.1, sx: L_C + .02, sy: .85, sz: 1.1, c: 0xa8a59c, t: tLC(a), dy: 7 })); for (let q = 0; q < 4; q++) v.push({ x: x - L_C / 2 + (q + .5) * L_C / 4, z: 17, y: YQ - 1.05, sx: .8, sy: .8, sz: 27, c: 0xa8a59c, t: tLC(a) + .05, dy: 7 }); } frota(UNI, mat(0xffffff), v, { modo: 'desce', d: .32 }); frota(UNI, mat(0xffffff, { roughness: .8 }), l, { modo: 'desce', d: .28 }); for (let q = F(5) + .1; q < F(5) + dC; q += .2) som(q, 'tijolo'); }

// defensas e cabeços ----------------------------------------------------------------------------------------------------------------------------------------------------------------
const dF = rest(T.def, 6), ZF = 33.2;
{ const f = [], c = [], bo = []; for (let x = -XC + 12; x < XC; x += 24) { const tt = T.def + .1 + Math.abs(x) / XC * dF * .85; f.push({ x, z: ZF, y: 1.2, sx: 3.6, sy: 3.3, sz: .8, c: 0x24262a, t: tt, dy: 5, m: 'desce' }, { x, z: ZF + .55, y: 1.6, sx: 2.5, sy: 2.6, sz: .4, c: 0xffc61a, t: tt + .1, m: 'pop' }, { x: x + 12, z: ZF - 1, y: 1.6, sx: .9, sy: 3.1, sz: .3, c: 0x56606e, t: tt + .1, dy: 3, m: 'desce' }); c.push({ x: x + 12, z: 30.5, y: YQ + .04, sx: .9, sy: .75, sz: .9, c: 0x333844, t: tt + .2 }); } frota(UNI, mat(0xffffff, { roughness: .7 }), f, { d: .3 }); frota(gc(.5, .62, 1, 12), mat(0xffffff, { metalness: .3 }), c, { d: .25 }); for (let q = T.def; q < T.def + dF; q += .3) som(q, 'pop'); }

// trilhos e guindastes de cais --------------------------------------------------------------------------------------------------------------------------------------------------------
const GUIX = [-132, -66, 0, 66, 132], GUIC = V_.gui, ZGA = 27, ZGB = 3, HG = 42, dG = rest(T.gui, 7);
const G_GUI = (() => { const L = [], c = GUIC, b_ = (a, b, s) => L.push([barraG(a, b, s), c]);[-13, 13].forEach(x => { [ZGA, ZGB].forEach(z => { L.push([gb(1.8, HG, 1.8, x, 0, z), c], [gb(4, 1.2, 4, x, 0, z), 0x333844]); }); b_([x, 20, ZGA], [x, 20, ZGB], 1.1); b_([x, HG, ZGA], [x, HG, ZGB], 1.1); b_([x, 3, ZGA], [x, 20, ZGB], .7); b_([x, 3, ZGB], [x, 20, ZGA], .7); b_([x, 21, ZGA], [x, HG, ZGB], .7); b_([x, 21, ZGB], [x, HG, ZGA], .7); }); [ZGA, ZGB].forEach(z => { b_([-13, HG, z], [13, HG, z], 1.2); b_([-13, 20, z], [13, 20, z], 1); }); L.push([gb(4, 2, 104, 0, HG + 1, 46), c], [gb(14, 8, 16, 0, HG + 2, -2), 0xf4efe6], [gb(2, 18, 2, -3, HG + 2, 14), c], [gb(2, 18, 2, 3, HG + 2, 14), c]);[52, 80].forEach(z => { b_([-2, HG + 3, z], [-3, HG + 20, 14], .3); b_([2, HG + 3, z], [3, HG + 20, 14], .3); }); b_([-3, HG + 20, 14], [-3, HG + 10, -10], .3); b_([3, HG + 20, 14], [3, HG + 10, -10], .3); return funde(L); })();
{ const r = [ZGA, ZGB].flatMap(z => [{ x: -XC, z, y: YQ, sx: 2 * XC, sy: .26, sz: .5, c: 0xc7ced6, t: T.gui - .2 + (z > 10 ? 0 : .3), d: 1.1, m: 'estica' }]); frota(gb(1, 1, 1, .5), mat(0xffffff, { metalness: .5 }), r); const tGi = i => T.gui + .3 + Math.abs(i - 2) * dG * .14; moveis(G_GUI, 5, [0xffffff], (i, t) => { const e = 1 - ease((t - tGi(i)) / (dG * .72)), s = i < 2 ? -1 : 1; return [GUIX[i] + (i === 2 ? -1 : s) * e * 96, YQ + .26, 0, 0]; }, { de: T.gui - .05 }); for (let i = 0; i < 5; i++) som(tGi(i) + dG * .7, 'impact'); }
moveis(funde([[gb(10, 2.4, 3, 0, 0), 0x46505e], [gb(30, 1, 8, 12, 0), 0xf4efe6]]), 1, [0xffffff], () => null, { de: 1e9 });

// pátio: asfalto, faixas e pilhas de contêineres ----------------------------------------------------------------------------------------------------------------------------------------------------
const dPa = rest(T.pat, 8), ZPA0 = -190, ZPA1 = -2, BLO = [];
{ const l = [], nx = 28, nz = 10; for (let a = 0; a < nx; a++) for (let b = 0; b < nz; b++) { const x = -XC + (a + .5) * (2 * XC / nx), z = ZPA0 + (b + .5) * ((ZPA1 - ZPA0) / nz); l.push({ x, z, y: YA, sx: 2 * XC / nx + .1, sy: .9, sz: (ZPA1 - ZPA0) / nz + .1, c: (a + b) % 2 ? 0x55575f : 0x4b4d55, t: T.pat + .05 + (1 - b / nz) * dPa * .3, sub: 1.2 }); } frota(UNI, mat(0xffffff), l, { d: .25, sombra: false, modo: 'sobe' }); const cx = [], cor2 = prng(61), tr = [];[-24, -54, -84, -114, -144].forEach((z, i) => { for (let a = -18; a < 18; a++) for (let c = 0; c < 6; c++) { const x = (a + .5) * 14.5, h_ = 1 + Math.floor(cor2() * 4); for (let k = 0; k < h_; k++) cx.push({ x, z: z + c * 2.75 - 7, y: YA + .9 + k * 2.6, ry: 0, c: C_CX[Math.floor(cor2() * C_CX.length)], t: T.pat + dPa * .2 + (.12 + cor2() * .62 + k * .05) * dPa, dy: 13, x_: x, zb: z }); } for (let x = -XC + 4; x < XC; x += 8) tr.push({ x, z: z + 9.5, y: YA + .92, sx: 4, sy: .03, sz: .2, c: 0xf2d24a, t: T.pat + .4 }); }); frota(UNI, mat(0xffffff), tr, { sombra: false, recebe: false, d: .2 }); frota(G_CX2, mCX, cx, { modo: 'desce', d: .32 }); for (let q = T.pat; q < T.pat + dPa; q += .2) som(q, 'telha'); }
const G_RTG = funde([...[-1, 1].flatMap(s => [-7, 7].flatMap(x => [[gb(1, 19, 1, x, 0, s * 11), 0xf0f0ea], [gb(1.8, 1.2, 1.8, x, 0, s * 11), 0x24262a]])), ...[-1, 1].map(s => [gb(15, .9, .9, 0, 18, s * 11), 0xf0f0ea]), [gb(1, 1, 23, -7, 19, 0), V_.gui], [gb(1, 1, 23, 7, 19, 0), V_.gui], [gb(5, 1.5, 3, 0, 20, 0), 0x46505e]]);
frota(G_RTG, mV, [-120, -40, 50, 120].flatMap((x, i) => [-24, -84].map((z, k) => ({ x: x + k * 26, z: z - 0, y: YA + .9, c: 0xffffff, t: T.pat + i * .2 + k * .25, dy: 20 }))), { modo: 'desce', d: .4 });

// ferrovia: entra pelo fundo do pátio, um trem de vagões-plataforma ------------------------------------------------------------------------------------------------------------------------------------------------
const dT = rest(T.fer, 9), ZTR = -176, tFe = T.fer + .1;
{ const d = [], r = [], b = []; for (let x = -900; x < 900; x += 1.2) { const u = (x + 900) / 1800; if (Math.abs(x) < 520) d.push({ x, z: ZTR, y: YA + .95, sx: .3, sy: .16, sz: 2.8, c: 0x7a6a58, t: tFe + u * dT * .55 }); } [-.72, .72].forEach(z => r.push({ x: -900, z: ZTR + z, y: YA + 1.1, sx: 1800, sy: .16, sz: .1, c: 0xc7ced6, t: tFe + .1, d: dT * .62, m: 'estica' })); frota(UNI, mat(0xffffff), d, { d: .15, sombra: false }); frota(gb(1, 1, 1, .5), mat(0xffffff, { metalness: .5 }), r); for (let q = tFe; q < tFe + dT * .6; q += .2) som(q, 'toc'); }
const G_VAG = funde([[gb(15, .5, 2.7, 0, 1.2), 0x46505e], [gb(2.4, 1.1, 2.4, -5, 0), 0x24262a], [gb(2.4, 1.1, 2.4, 5, 0), 0x24262a]]), G_LOC = funde([[gb(20, 3.5, 3, 0, 1.2), 0xd8443a], [gb(20.1, .6, 3.05, 0, 2.2), 0xffd23f], [gb(5, 1, 2.9, -7, 4.7), 0xd8443a], [gb(3, 1.1, 2.6, 7.2, 4.7), 0xaee3f7], [gb(3.4, 1.2, 2.4, -6, 0), 0x24262a], [gb(3.4, 1.2, 2.4, 6, 0), 0x24262a]]);
const NVG = 22, xTrm = t => { const k = clamp((t - (tFe + dT * .45)) / (dT * .5)); return 420 - ease(k) * 290 - Math.max(0, t - T_USO - 1) * 7; };
moveis(G_LOC, 1, [0xffffff], (i, t) => [xTrm(t) - 12, YA + 1.25, ZTR, 0], { de: tFe + dT * .4 }); moveis(G_VAG, NVG, [0xffffff], (i, t) => [xTrm(t) + 8 + i * 16, YA + 1.25, ZTR, 0], { de: tFe + dT * .4 });
{ const r2 = prng(19), L = Array.from({ length: NVG }, () => [C_CX[Math.floor(r2() * 10)]]); const im = moveis(G_CX2, NVG, C_CX, (i, t) => [xTrm(t) + 8 + i * 16 , YA + 3, ZTR, 0], { de: tFe + dT * .4, mat: mCX }); }

// boias: vermelhas e verdes marcando o canal -------------------------------------------------------------------------------------------------------------------------------------------------------------------------
const dB_ = rest(T.boi, 10), ZBOI = [108, 176], XBO = []; for (let i = 0; i < 30; i++) XBO.push(-760 + i * 44);
const G_BOI = funde([[gc(2.1, 2.5, 1.4, 16, 0, -.3)], [gc(.8, 1.7, 3.2, 12, 0, 1)], [gb(.5, 1.4, .5, 0, 4.1), 0xffffff]]);
const lzB = [0, 1].map(k => brilhos(XBO.map(x => [x, 5.7, ZBOI[k]]), k ? 0x3aff7a : 0xff3a2a, 7));
moveis(G_BOI, XBO.length * 2, [0xd8341e, 0x2fa84a], (i, t) => { const k = i % 2, q = XBO[Math.floor(i / 2)], t0 = T.boi + .05 + Math.abs(q + 80) / 800 * dB_ * .7; if (t < t0) return null; const e = back((t - t0) / .35); return [q, .2 + (e - 1) * 3 + Math.sin(t * 1.2 + i) * .22, ZBOI[k], 0, Math.sin(t * .9 + i) * .05]; }, { de: T.boi });
AUTO.push(t => { const b = Math.sin(t * 3) > 0 ? 1 : .35; lzB.forEach(l => l.op(t >= fim(10) - 1 ? b : 0)); });
{ const c = (i) => i; for (let q = T.boi; q < T.boi + dB_; q += .3) som(q, 'pop'); }

// navio final encostado, guindaste descarrega, caminhões levam ----------------------------------------------------------------------------------------------------------------------------------------------------------------
const NF_ = navio(280, 42, 15, 17, 15, 5, V_.casco, 202), ZNV = ZF + 22.6, XNV = 0, T_AT = T_USO + 1.6;
{ const cc = NF_.cx; } NF_.g.rotation.y = 0;
AUTO.push(t => { const on = t >= F(LAST) - .05; NF_.g.visible = on; if (!on) return; const e = 1 - ease((t - F(LAST)) / (T_AT - F(LAST))); NF_.g.position.set(XNV + e * 120, .6, ZNV + e * 90); NF_.g.rotation.y = e * .12; });
const REB = [[XNV + 145, ZNV + 25], [XNV - 90, ZNV + 25]]; moveis(funde([[gb(30, 2.6, 10, 0, 0), 0x333844], [gb(30.2, .4, 10.2, 0, 1.6), 0xd8443a], [gb(6, 5, 6, -8, 2.6), 0xf4efe6]]), 2, [0xffffff], (i, t) => { const e = 1 - ease((t - F(LAST)) / (T_AT - F(LAST))), a = i ? PI / 2 : PI / 2; return [REB[i][0] + e * 120 + (i ? 0 : 0), .4, REB[i][1] + e * 90, a]; }, { de: F(LAST) - .05 });
const GC = [-66, 0, 66], PRD = 5.2, C_GA = GC.map((x, k) => { const z_ = 2 + k * 3; return { x, k }; });
const fx = (u, k) => { const qx = GC[k], yS = YQ + 35, zN = ZNV - 8 + k * 3, zQ = 14, yN = 15 + 11, yC_ = YQ + 3.2; if (u < .22) return [qx, yN + (yS - yN) * ease(u / .22), zN]; if (u < .58) return [qx, yS, zN + (zQ - zN) * ease((u - .22) / .36)]; if (u < .8) return [qx, yS + (yC_ - yS) * ease((u - .58) / .22), zQ]; return [qx, yC_, zQ]; };
const pegaU = (t, k) => ((t - T_AT - k * 1.1) / PRD);
moveis(G_CX2, 3, [0xd8443a, 0x2f7fd6, 0xf2a93a], (i, t) => { if (t < T_AT) return null; const u = pegaU(t, i); if (u < 0) return null; const f = u % 1; if (f >= .8) return null; const p = fx(f, i); return [p[0], p[1], p[2], 0]; }, { de: T_AT, mat: mCX });
moveis(funde([[gb(14, 1.2, 4, 0, 0), 0x24262a]]), 3, [0xffffff], (i, t) => { const u = t < T_AT ? 0 : Math.max(0, pegaU(t, i)), p = t < T_AT ? [GC[i], YQ + 35, ZNV] : fx(u % 1, i); return [p[0], p[1] + 2.6, p[2], 0]; }, { de: F(LAST) });
moveis(gb(.24, 1, .24), 12, [0x24262a], (i, t) => null, { de: 1e9 });
{ const fi = GC.map(() => { const m = add(new THREE.Mesh(UNI, mat(0x24262a))); return m; }); AUTO.push(t => { fi.forEach((m, i) => { const on = t >= F(LAST); m.visible = on; if (!on) return; const u = t < T_AT ? 0 : Math.max(0, pegaU(t, i)), p = t < T_AT ? [GC[i], YQ + 35, ZNV] : fx(u % 1, i); const y = p[1] + 3.8; m.position.set(p[0], y, p[2]); m.scale.set(.5, Math.max(.1, YQ + HG - y), 2); }); }); }
for (let q = T_AT; q < D.total; q += PRD / 3) som(q, 'toc');
// caminhões carregados saindo do cais
const G_TRK = funde([[gb(2.5, 2.7, 3, 0, .6, 8.2), 0xd8443a], [gb(2.4, .9, 3.1, 0, 2, 8.2), 0xaee3f7], [gb(2.5, .45, 14, 0, .7, -.5), 0x46505e], [gb(2.5, .7, 14, 0, 0, -.5), 0x24262a]]);
moveis(G_TRK, 12, [0xffffff], (i, t) => { const k = i % 3, n = Math.floor(i / 3), c = ((t - T_AT - k * 1.1) / PRD - n * .25); const u = ((t * .12 + i * .083) % 1), s = i % 2 ? 1 : -1; if (u < .5) { return [GC[k] + (u - .25) * 30, YQ, 13 + (i % 2) * 5, PI / 2 * s]; } const z = 13 - (u - .5) * 340; return [GC[k] + 10, z < 0 ? YA + .9 : YQ, z, PI]; }, { de: F(LAST) - .05 });
moveis(G_CX2, 12, C_CX, (i, t) => { const u = ((t * .12 + i * .083) % 1), s = i % 2 ? 1 : -1, k = i % 3; if (u < .5) return [GC[k] + (u - .25) * 30 , YQ + 1.25, 13 + (i % 2) * 5, PI / 2 * s + PI / 2 - PI / 2]; const z = 13 - (u - .5) * 340; return [GC[k] + 10, (z < 0 ? YA + .9 : YQ) + 1.25, z, PI / 2]; }, { de: F(LAST) - .05, mat: mCX });
// gaivotas e barquinhos dão vida
moveis(funde([[gb(10, 1.4, 3, 0, 0), 0xf4efe6], [gb(3, 1.6, 2.2, -1.5, 1.4), 0x4a6fa5]]), 6, [0xffffff], (i, t) => [-500 + i * 190 + Math.sin(t * .1 + i) * 40, .2, 380 + i * 34, i % 2 ? 0 : PI]);

// operário -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
const OP = operario(.86), Dx = 6, VIS = [
  [[128, 36, 392], [66, 8, 268]],
  [[-90, 38, 302], [-116, 6, 236], 1, [9, 38, 302], [-17, 6, 236]],
  [[74, 27, -152], [26, 4, -198], 1],
  [[QB[0][0] + 74, 22, QB[0][1] + 24], [QB[0][0] + 22, 3, QB[0][1] - 6], 1, [QB[QB.length - 1][0] + 74, 22, QB[QB.length - 1][1] + 24], [QB[QB.length - 1][0] + 22, 3, QB[QB.length - 1][1] - 6]],
  [[-26, 27, 100], [-16, 3, 35], 1, [24, 27, 100], [34, 3, 35]],
  [[-54, 21, 60], [-13, 3, 12], 1],
  [[-18, 8, 54], [5, 2.6, 30], 1],
  [[-70, 20, 84], [-5, 16, 12], 1],
  [[40, 30, 34], [10, 5, -24], 1],
  [[46, 17, -228], [18, 4, -172], 1],
  [[-156, 9, 125], [-100, 2, 108], 1],
];
const WD = [[Dx + 22, 0], [32, -62], 0];
{ const q = (i, x, z, y, g) => [F(i), x, z, y, olha(VIS[i][0], x, z), g, 1], RT_ = [[0, 200, 180, 0, 0, 'pasmo'], [fim(0), 200, 180, 0, 0, 'pasmo'], q(1, 0, 0, 8.6, 'bate'), q(2, 30, -213, YA + .02, 'para'), q(3, 0, 0, 0, 'bate'), q(4, 6, 44, 3.15, 'bate'), q(5, -9, 21, YQ + .04, 'bate'), q(6, 3, 31.5, YQ + .04, 'bate'), q(7, -21, 28.5, YQ + .04, 'para'), q(8, 6, -13.5, YA + .95, 'para'), q(9, 20, -179.5, YA + .95, 'bate'), q(10, -130.3, 113.4, 2.15, 'bate'), [T_USO, -130.3, 113.4, 2.15, 0, 'bate']]; roteiro(OP, RT_, T_USO); }
const opAt = (i, x, y, z, ry, bat = true) => AUTO.push(t => { if (t < F(i) || t >= fim(i) + .14) return; const { h, r } = OP; h.position.set(x(t), y, z(t)); h.rotation.y = ry; if (bat) { r.anda(0, 0); r.respira(t); const w = Math.sin(t * 8); r.bd.j.rotation.x = -2.35 + w * .42; r.bd.k.rotation.x = -.25; } });
// fala 0: no píer de pedra ao lado do encalhe; falas 1 e 3: embarcado na draga e na barcaça; fala 10: na lancha ao lado da boia
opAt(0, () => 86, 2.15, () => 334, .4, false);
opAt(1, t => xDr(t) + 4, 9.6, () => 239, -.7);
opAt(3, t => qbT(t)[0] + 30.8, 2.75, t => qbT(t)[1] + 2.95, .7); opAt(4, t => xB(t) + 3, 3.2, () => 40, .1);
festa(OP, -22, 8.5, 1, T_USO, YQ + .04);
// plataforma de pedra na fala 0

moveis(funde([[gb(9, 1.6, 3.4, 0, 0), 0xf4efe6], [gb(3.4, 1.8, 2.6, 2, 1.6), 0x4a6fa5]]), 1, [0xffffff], (i, t) => (t < fim(0) + .1 ? [89, .5, 334, 0] : t >= F(10) - .02 ? [-127, .5, 113.4, 0] : null), { de: 0, ate: fim(10) + .1 });

// câmera -----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
const K = plano(VIS, [{ t: F(LAST) + .03, p: [330, 240, 560], l: [0, 6, 0] }, { t: T_USO - .03, p: [300, 215, 510], l: [0, 6, 0] }, { t: T_USO + .02, p: [190, 86, 210], l: [0, 18, 34] }, { t: T_AT + 3, p: [172, 78, 190], l: [0, 18, 34] }, { t: T_AT + 3.03, p: [-52, 12, -15], l: [-5, 17, 28] }, { t: D.total + 1, p: [-46, 12, -12], l: [-5, 17, 28] }]);

// rótulos e sons --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
etq('ÁGUA RASA', F(0) + .15, fim(0), 'ruim');
[['DRAGA', T.dra, fim(1)], ['ATERRO', T.ate, fim(2)], ['QUEBRA-MAR', T.que, fim(3)], ['ESTACAS', T.est, fim(4)], ['CAIS', T.cai, fim(5)], ['DEFENSAS', T.def, fim(6)], ['GUINDASTES', T.gui, fim(7)], ['PÁTIO', T.pat, fim(8)], ['FERROVIA', T.fer, fim(9)], ['BOIAS', T.boi, fim(10)]].forEach(l => etq(...l));
etq('PORTO PRONTO!', F(LAST) + .1, T_USO, 'grande');
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); som(.1, 'impact'); som(.24, 'crack'); som(.4, 'desaba'); som(.8, 'desaba'); som(1.1, 'impact'); som(1.5, 'chuva'); som(F(LAST) + .1, 'ding'); som(T_USO + .1, 'whoosh'); for (let q = F(1); q < fim(2); q += 1) som(q, 'motor');
for (let q = F(1); q < fim(10); q += 1.3) som(q, 'toc');

window.CAPA_T = T_AT + 2.4;
function foco() { const v = new V3(); cam.getWorldDirection(v); const y = cam.position.y, q = v.y < -.05 ? Math.min(y / -v.y, 260) : 160; return [cam.position.x + v.x * q, cam.position.z + v.z * q]; }
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); const f = foco(); segueSol(f[0], f[1]); AUTO.forEach(q => q(t)); });
