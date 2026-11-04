// Uma cidade do zero, vista de cima: o terreno vazio vira cidade e o operário gigante trabalha nas ruas.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, tex, boneco, camTo, iniciar, pal, fala, som, rotulo, D } = K3;
const E = window.ESPEC, V_ = E.variante, rnd = prng(E.semente ?? 31), F = fala, fim = i => F(i) + D.falas[i].dur, AUTO = [], LAST = D.falas.length - 1;
const tk = (w, i) => { for (let n = 0; n < 40; n++) { try { const q = pal(w, n); if (q >= F(i) - .1 && q <= fim(i)) return q; } catch { break; } } return F(i) + .4; };
const ult = D.falas[LAST], nPal = ult.texto.split(/[!.]/)[0].trim().split(/\s+/).length, T_USO = (ult.words[nPal - 1]?.end ?? ult.t + ult.dur) + .15;
cam.near = 1; cam.far = 4000;
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
const G_TOR = (() => { const L = [], H = 24, b = 3.4, ax = y => b * (1 - y / H * .86), s = .22; const q = [[1, 1], [1, -1], [-1, -1], [-1, 1]]; q.forEach(([a, c]) => L.push([barraG([a * b, 0, c * b], [a * .5, H, c * .5], .3)])); for (let i = 0; i < 7; i++) { const y0 = i * H * .13, y1 = (i + 1) * H * .13, a0 = ax(y0), a1 = ax(y1); [[1, 1, 1, -1], [1, -1, -1, -1], [-1, -1, -1, 1], [-1, 1, 1, 1]].forEach(([a, c, d, e], j) => { L.push([barraG([a * a0, y0, c * a0], [d * a1, y1, e * a1], s * .7)]); L.push([barraG([d * a0, y0, e * a0], [a * a1, y1, c * a1], s * .7)]); L.push([barraG([a * a1, y1, c * a1], [d * a1, y1, e * a1], s)]); }); } [[H * .98, 5.6], [H * .8, 7], [H * .62, 5.6]].forEach(([y, w]) => { L.push([barraG([-w, y, 0], [w, y, 0], .36)]); L.push([barraG([-w, y, 0], [0, y + 1.8, 0], .2)]); L.push([barraG([w, y, 0], [0, y + 1.8, 0], .2)]); [-w, w].forEach(x => L.push([gc(.16, .22, 1.1, 6, x, y - 1.1, 0), 0x6ec1e4])); }); L.push([gb(8.4, .4, 8.4), 0xb9bcc2]); return funde(L); })();
const TOR_Y = [[24 * .98 - 1.1, 5.6], [24 * .8 - 1.1, 7], [24 * .62 - 1.1, 5.6]];

// véu de luz: uma mancha quente sobre a cidade à noite, faz o papel do brilho sem pós-processo
function veu(x, y, z, esc, cor, forca = .4) { const m = new THREE.SpriteMaterial({ map: TX_G, color: cor, transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, depthTest: false, toneMapped: false }), s = new THREE.Sprite(m); s.position.set(x, y, z); s.scale.setScalar(esc); add(s); ACENDE.push(k => { m.opacity = k * forca; s.visible = k > .01; }); s.visible = false; }
// coloca o operário no quadro: a para a direita, b para perto da câmera, em frações do quadro
const noQuadro = (p, l, a, b) => { const f = new V3(l[0] - p[0], 0, l[2] - p[2]).normalize(), r = new V3(-f.z, 0, f.x), d = Math.hypot(p[0] - l[0], p[1] - l[1], p[2] - l[2]), W = d * .171; return [l[0] + r.x * a * W - f.x * b * W * 2, l[2] + r.z * a * W - f.z * b * W * 2]; };
const olha = (p, x, z, o = .5) => Math.atan2(p[0] - x, p[2] - z) + o;

// CENA
cenario(190, 700, 2400);
const P = 20, NQ = 10, B = 100, LQ = 15;
const T = { est: tk('estacas', 1), rua: tk('ruas', 2), gal: tk('galeria', 3), agu: tk('estação', 4), pos: tk('postes', 5), cas: tk('casas', 6), esc: tk('escola', 7), oni: tk('ônibus', 8), pre: tk('prédios', 9), par: tk('parques', 10) };
const dist = (x, z) => Math.hypot(x, z);

// terreno: mata em volta, rio a leste, clareira de terra no meio --------------------------------------------
const gr = add(new THREE.Mesh(new THREE.PlaneGeometry(9000, 9000), mat(V_.grama, { roughness: 1 }))); gr.rotation.x = -PI / 2; gr.receiveShadow = true;
{ const m = add(new THREE.Mesh(new THREE.BoxGeometry(238, .04, 238), mat(V_.terra, { roughness: 1 }))); m.position.set(12, .02, 0); m.receiveShadow = true; }
const riacho = agua(34, 6000, 158, 0, V_.rio); { const a = add(new THREE.Mesh(new THREE.PlaneGeometry(46, 6000), mat(0xe2cf9d, { roughness: 1 }))); a.rotation.x = -PI / 2; a.position.set(158, .03, 0); a.receiveShadow = true; }
{ const l = []; for (let i = 0; i < 1500; i++) { const a = rnd() * 6.28, r = 135 + rnd() * rnd() * 460, x = Math.cos(a) * r, z = Math.sin(a) * r; if (x > 128 && x < 190) continue; if (Math.abs(z) < 7) continue; if (Math.abs(x) < 122 && Math.abs(z) < 122) continue; l.push({ x, z, s: 3 + rnd() * 2.6, pinho: rnd() > .55 }); } arvores(l); }
{ const l = []; for (let i = 0; i < 26; i++) { const a = i / 26 * 6.28 + rnd(), r = 520 + rnd() * 420; l.push({ x: Math.cos(a) * r, z: Math.sin(a) * r, sx: 120 + rnd() * 120, sy: 50 + rnd() * 90, sz: 120 + rnd() * 120, c: corDe([0x5fae62, 0x4f9f58, 0x6dbb6a]) }); } frota(new THREE.IcosahedronGeometry(1, 1), mat(0xffffff, { flatShading: true, roughness: 1 }), l, { sombra: false }); }

// abertura: a cidade errada, sem ruas e sem saída para a água ----------------------------------------------
{ const l = []; for (let a = 0; a < 7; a++) for (let b = 0; b < 8; b++) l.push({ x: -36 + a * 12 + rnd() * 3, z: -30 + b * 10 + rnd() * 2.5, ry: (rnd() - .5) * .5, s: 1.9, t: -5 }); casas(l, { ate: fim(0) }); frota(G_ARV, mV, Array.from({ length: 30 }, () => ({ x: -42 + rnd() * 84, z: -34 + rnd() * 84, sx: 1.8, sy: 1.8, sz: 1.8, c: corDe(C_ARV) })), { ate: fim(0) }); }
const TX_AG = tex(256, 256, (g, w) => { g.fillStyle = '#fff'; g.fillRect(0, 0, w, w); g.strokeStyle = 'rgba(120,100,70,.5)'; g.lineWidth = 3; const r = prng(9); for (let i = 0; i < 40; i++) { const x = r() * w, y = r() * w; g.beginPath(); g.arc(x, y, 8 + r() * 26, .3, 2.2); g.stroke(); } }, 20, 20);
const enchente = add(new THREE.Mesh(new THREE.PlaneGeometry(900, 900), new THREE.MeshStandardMaterial({ color: 0x8f7a56, map: TX_AG, roughness: .3, transparent: true, opacity: .93 }))); enchente.rotation.x = -PI / 2;
const NIV = t => .7 + clamp(t / 3.4) * 1.5;
moveis(G_CAR, 16, [0xd83a3a, 0x3a7fd8, 0xf2c94c, 0xf4efe6, 0x2fbf8f], (i, t) => { const a = i * 2.4, x = -34 + (i * 11.7 % 68) + Math.sin(t * .5 + a) * 3 + t * (.8 + (i % 3) * .3), z = 2 + (i * 7.3 % 42) + Math.cos(t * .4 + a) * 2 + t * .9; return [x, NIV(t) - .2 + Math.sin(t * 2 + a) * .08, z, a + t * .35 * (i % 2 ? 1 : -1), Math.sin(t * 1.5 + a) * .14]; }, { ate: fim(0), esc: 1.9 });
chuva(1100, -1, fim(0), () => [0, 0, 22], 80, 42, 1.4);
AUTO.push(t => { enchente.visible = t < fim(0); if (enchente.visible) { enchente.position.set(0, NIV(t), 0); TX_AG.offset.set(t * .03, t * .05); } });

// estacas e linhas ---------------------------------------------------------------------------------------
{ const l = [], f = []; for (let i = -5; i <= 5; i++) for (let j = -5; j <= 5; j++) { const d = dist(i, j); [[0, 0], [.5, 0], [0, .5], [.5, .5]].forEach(([a, b]) => { if (Math.abs(i + a) > 5 || Math.abs(j + b) > 5) return; l.push({ x: (i + a) * P, z: (j + b) * P, t: T.est + .1 + d * .34 + rnd() * .3, t2: T.rua + 2.2 + d * .2 }); }); } frota(funde([[gc(.22, .22, 3.4, 6), 0xd9a55f], [gc(.3, .3, .6, 6, 0, 3.4), 0xff5a3c]]), mV, l, { modo: 'desce', d: .3 });
  for (let i = -5; i <= 5; i++) { const q = T.est + 1.1 + Math.abs(i) * .2; f.push({ x: i * P, z: 0, y: 1.6, sx: .28, sy: .12, sz: 200, c: 0xff7a3c, t: q, t2: T.rua + 3, m: 'pop', d: .4 }, { x: 0, z: i * P, y: 1.6, sx: 200, sy: .12, sz: .28, c: 0xffffff, t: q + .1, t2: T.rua + 3, m: 'pop', d: .4 }); } frota(UNI, mat(0xffffff), f, { sombra: false });
  for (let q = T.est + .1; q < T.est + 2.6; q += .24) som(q, 'toc'); }

// ruas -----------------------------------------------------------------------------------------------------
const SEG = []; for (let k = -5; k <= 5; k++) for (let j = 0; j < NQ; j++) { const u = (j - 4.5) * P; SEG.push({ x: k * P, z: u, v: true }, { x: u, z: k * P, v: false }); }
SEG.forEach(s => { s.d = dist(s.x, s.z); s.t = T.rua + .1 + s.d / 145 * 4.2; });
{ const m = [], tr = []; SEG.forEach(s => { m.push({ x: s.x, z: s.z, y: .05, sx: s.v ? 5 : P + 5, sz: s.v ? P + 5 : 5, sy: .08, c: 0x4a4c55, t: s.t, m: 'estica' }); for (let i = 0; i < 4; i++) { const o = -7.5 + i * 5; tr.push({ x: s.x + (s.v ? 0 : o), z: s.z + (s.v ? o : 0), y: .14, sx: s.v ? .26 : 2.2, sz: s.v ? 2.2 : .26, sy: .02, c: 0xf2d24a, t: s.t + .2 }); } }); frota(UNI, mat(0xffffff), m, { sombra: false, d: .5 }); frota(UNI, mat(0xffffff), tr, { sombra: false, recebe: false });
  for (let q = T.rua + .1; q < T.rua + 4; q += .3) som(q, 'pop'); const m2 = []; [-1, 1].forEach(s => m2.push({ x: s * 400 + (s > 0 ? 0 : -100), z: 0, y: .05, sx: 620, sz: 6, sy: .08, c: 0x4a4c55, t: T.rua + 3 })); frota(UNI, mat(0xffffff), m2, { sombra: false, d: .6, modo: 'pop' }); }
// caminhões de obra nas ruas
moveis(G_CAM, 22, [0xffc61a, 0xe8683f, 0x2f7fd6], (i, t) => { if (t < T.rua + 2.5 + i * .1) return null; const k = -5 + (i * 3) % 11, v = i % 2, u = ((i * .37 + t * .05) % 1) * 200 - 100, o = i % 4 < 2 ? 1 : -1; return v ? [k * P + o * 1.2, .08, u * o, o > 0 ? 0 : PI] : [u * o, .08, k * P + o * 1.2, o > 0 ? PI / 2 : -PI / 2]; }, { de: T.rua, ate: T.oni + .2, esc: 1.1 });

// galeria e valas: a rua abre, o cano gigante desce, a rua fecha -----------------------------------------------
const T_FV = T.pos - .5; // fecha as valas
{ const v = [], c = [], ca = [], ce = []; SEG.forEach(s => { const t = T.gal + .15 + s.d / 145 * 3, q = T_FV + s.d / 145 * .7; v.push({ x: s.x, z: s.z, y: .1, sx: s.v ? 3.6 : P, sz: s.v ? P : 3.6, sy: .06, c: 0x6a4a2e, t, t2: q, m: 'estica' }); for (let i = 0; i < 4; i++) { const o = -7.5 + i * 5; c.push({ x: s.x + (s.v ? 0 : o), z: s.z + (s.v ? o : 0), y: .16, ry: s.v ? 0 : PI / 2, c: i % 2 ? 0xb9bdc4 : 0xc9cdd4, t: t + .15 + i * .07, t2: q, m: 'desce', dy: 8 }); }
    const t2 = T.agu + .3 + s.d / 145 * 2.2; ca.push({ x: s.x + (s.v ? 1.15 : 0), z: s.z + (s.v ? 0 : 1.15), y: .16, sx: s.v ? .5 : P, sy: .5, sz: s.v ? P : .5, c: 0x2f8ae6, t: t2, t2: q, m: 'estica' }); ce.push({ x: s.x - (s.v ? 1.15 : 0), z: s.z - (s.v ? 0 : 1.15), y: .16, sx: s.v ? .5 : P, sy: .5, sz: s.v ? P : .5, c: 0x8a5a2e, t: t2 + .15, t2: q, m: 'estica' }); });
  frota(UNI, mat(0xffffff), v, { sombra: false, d: .4 }); const M = chato(new THREE.CylinderGeometry(1, 1, 4.6, 14).rotateX(PI / 2).translate(0, .95, 0)); frota(funde([[M], [new THREE.CylinderGeometry(1.14, 1.14, .5, 14).rotateX(PI / 2).translate(0, .95, 2.1), 0x8d939c]]), mV, c, { d: .3 }); frota(UNI, mat(0xffffff), ca.concat(ce), { d: .4 });
  for (let q = T.gal + .2; q < T.gal + 3; q += .22) som(q, 'tijolo'); }
// bocas de lobo: ficam depois que a rua fecha
{ const l = []; SEG.forEach((s, i) => { if (i % 2) return; l.push({ x: s.x + (s.v ? 2.2 : 0), z: s.z + (s.v ? 0 : 2.2), y: .1, sx: s.v ? .5 : 1.6, sy: .1, sz: s.v ? 1.6 : .5, c: 0x26282c, t: T_FV + 1 + i * .002 }); }); frota(UNI, mat(0xffffff), l, { sombra: false }); }
// saída da galeria no rio
{ const g = funde([[new THREE.CylinderGeometry(2.6, 2.6, 40, 20).rotateZ(PI / 2).translate(0, 2.4, 0), 0xb9bdc4]]); const m = unico(g, 121, .1, 0); aparece(m, T.gal + 2.2, .5, 'desce', 6); const ca = [[[100, 1, 0], [144, 1, 0]]]; }
const canos = SEG.map(s => s.v ? [[s.x, .9, s.z - 10], [s.x, .9, s.z + 10]] : [[s.x - 10, .9, s.z], [s.x + 10, .9, s.z]]);
const eixoG = []; for (let k = -5; k <= 5; k++) { eixoG.push([[k * P, 2.2, -100], [k * P, 2.2, 0], [100, 2.2, 0], [141, 2.2, 0]]); eixoG.push([[k * P, 2.2, 100], [k * P, 2.2, 0], [100, 2.2, 0], [141, 2.2, 0]]); }
pulsos(eixoG, 620, 0x63c8ff, 9, T.gal + 1.2, T.agu, .1, 2.6, { forte: 1 });

// água e esgoto: captação, estação, caixa alta; esgoto até a estação de tratamento ----------------------------
const tanque = (x, z, r, c, t, ag) => { const g = funde([[gc(r, r, 2.4, 28), 0xd5d8dd], [gc(r * .88, r * .88, .06, 28, 0, 2.42), ag]]); const m = unico(g, x, .05, z); aparece(m, t, .4, 'pop'); som(t, 'pop'); };
{ const X = [108, 121, 134], t0 = T.agu + .1; X.forEach((x, i) => { [-58, -44, -30].forEach((z, j) => tanque(x, z, 5.6, 0, t0 + i * .22 + j * .12, j === 0 ? 0x8f7a56 : j === 1 ? 0x7cc4d8 : 0x2f9fe6)); }); X.forEach((x, i) => [30, 44, 58].forEach((z, j) => tanque(x, z, 5.6, 0, t0 + 1.4 + i * .2 + j * .12, j === 0 ? 0x6a5230 : j === 1 ? 0x9a8a55 : 0x69b6c9)));
  const cx = unico(funde([[gb(46, .5, 46), 0xc8c9c6]]), 121, 0, -44), cy = unico(funde([[gb(46, .5, 46), 0xc8c9c6]]), 121, 0, 44); aparece(cx, t0 - .1, .3); aparece(cy, t0 + 1.2, .3);
  const q = funde([[gc(1.6, 2, 15, 8), 0xdfe3e8], [gc(5.5, 1.8, 4, 24, 0, 15), 0x4aa8e8], [gc(5.5, 5.5, 1.4, 24, 0, 19), 0x4aa8e8], [gc(5.7, 5.7, .4, 24, 0, 20.4), 0xf4efe6]]); aparece(unico(q, 30, 0, -30), t0 + .7, .55, 'desce', 40); }
const ruas_ag = []; for (let k = -5; k <= 5; k++) ruas_ag.push([[121, 3, -44], [100, 1, -44], [100, 1, k * P], [-100, 1, k * P]], [[30, 18, -30], [30, 1, -30], [30, 1, k * P], [k * P, 1, k * P], [k * P, 1, -100]], [[30, 1, -30], [k * P, 1, -30], [k * P, 1, 100]]);
pulsos(ruas_ag, 520, 0x5fd0ff, 7.5, T.agu + .8, T_FV + .8, .22, 2.4);
const ruas_es = []; for (let k = -5; k <= 5; k++) ruas_es.push([[-100, 1, k * P + 1.2], [100, 1, k * P + 1.2], [100, 1, 44], [121, 3, 44]]);
pulsos(ruas_es, 300, 0xc98a3a, 6.5, T.agu + 2.4, T_FV + .8, .2, 2);

// energia: linha chega pela estrada, subestação, postes e fios ---------------------------------------------------
{ const f = []; for (let i = 0; i < 16; i++) { const x = -112 - i * 42; f.push({ x, z: -12, ry: PI / 2, t: T.pos + .1 + (15 - i) * .05 }); } frota(G_TOR, mV, f, { modo: 'sobe', d: .5, sobre: 1 }); f.forEach(q => { q.sub = 26; });
  const cb = []; for (let i = 0; i < 15; i++) { const x = -112 - i * 42, y = 24 * .8 - 1.1; [-7, 7].forEach(o => curva([x, y, -12 + o], [x - 42, y, -12 + o], 2.2, 5).forEach((p, j, A) => { if (j < 5) cb.push({ a: p, b: A[j + 1], t: T.pos + .8 + (15 - i) * .05 }); })); } cabos(cb, 0x2a2c33, .16);
  const yard = funde([[gb(16, .3, 18), 0xbfc3c8], [gb(4, 3, 3, -3, .3, -4), 0x8d939c], [gb(4, 3, 3, 3, .3, -4), 0x8d939c], [gb(4, 3, 3, -3, .3, 3), 0x8d939c], [gb(4, 3, 3, 3, .3, 3), 0x8d939c], [gc(.2, .2, 6, 6, -6, .3, 7), 0x8d939c], [gc(.2, .2, 6, 6, 6, .3, 7), 0x8d939c], [gb(12.4, .3, .3, 0, 6.3, 7), 0x8d939c]]); aparece(unico(yard, -111, 0, -12), T.pos + .1, .4);
  const p = [], fw = []; const GP2 = funde([[gc(.14, .2, 6.2, 6), 0x9aa1aa], [gb(1.8, .12, .12, 0, 5.9), 0x7a4a26]]); SEG.forEach((s, i) => { const t = T.pos + .3 + s.d / 145 * 3.2, ox = s.v ? 2.85 : 0, oz = s.v ? 0 : 2.85; [-5, 5].forEach(o => p.push({ x: s.x + ox + (s.v ? 0 : o), z: s.z + oz + (s.v ? o : 0), ry: s.v ? PI / 2 : 0, t })); [-.8, .8].forEach(o => fw.push({ x: s.x + ox + (s.v ? o : 0), z: s.z + oz + (s.v ? 0 : o), y: 5.98, sx: s.v ? .07 : P, sy: .07, sz: s.v ? P : .07, c: 0x2a2c33, t: t + .25, m: 'estica' })); }); frota(GP2, mV, p, { modo: 'desce', d: .3 }); frota(UNI, mat(0xffffff), fw, { sombra: false, d: .4 }); for (let q = T.pos + .3; q < T.pos + 3.6; q += .24) som(q, 'toc'); }
const ruas_el = []; for (let k = -5; k <= 5; k++) ruas_el.push([[-111, 6, -12], [-100, 6, k * P], [100, 6, k * P]], [[-111, 6, -12], [k * P, 6, -100], [k * P, 6, 100]]);
pulsos(ruas_el, 560, 0xffd84a, 7, T.pos + 1.6, T.cas + 1, .24, 2);

// quarteirões: calçada, jardim, casas ----------------------------------------------------------------------------
const QD = []; for (let a = 0; a < NQ; a++) for (let b = 0; b < NQ; b++) { const x = (a - 4.5) * P, z = (b - 4.5) * P; QD.push({ x, z, d: dist(x, z), tipo: 'casa' }); }
const acha = (x, z) => QD.find(q => q.x === x && q.z === z);
[[30, -30, 'caixa'], [-50, -50, 'escola'], [50, 50, 'escola'], [-70, 30, 'escola'], [70, -50, 'escola'], [-10, 70, 'escola'], [10, -70, 'escola'], [-30, 50, 'posto'], [30, 70, 'posto'], [-70, -30, 'posto'], [70, 10, 'posto'], [-50, 10, 'mercado'], [50, -10, 'mercado'], [-10, -50, 'mercado'], [10, 50, 'mercado'], [-90, -90, 'parque'], [90, 70, 'parque'], [-30, -30, 'parque'], [30, 30, 'parque'], [-90, 50, 'parque'], [70, -90, 'parque']].forEach(([x, z, k]) => acha(x, z).tipo = k);
const CORE = q => Math.abs(q.x) <= 50 && Math.abs(q.z) <= 50 && q.tipo === 'casa', dT = fim(6) - T.cas, dP = fim(9) - T.pre;
const tPre = q => T.pre + .1 + q.d / 72 * dP * .72;
{ const c = [], j = [], L = [], tA = T.cas + .15; QD.forEach(q => { const t0 = tA + q.d / 135 * dT * .55; c.push({ x: q.x, z: q.z, y: .04, sx: LQ, sz: LQ, sy: .16, c: 0xd9d7d0, t: t0 - .15 }); j.push({ x: q.x, z: q.z, y: .06, sx: LQ - 1.3, sz: LQ - 1.3, sy: .17, c: q.tipo === 'parque' ? 0x7ac96a : 0x8fd27c, t: t0 - .1 }); if (q.tipo !== 'casa') return; const st = (LQ - 1.8) / 5, A = -LQ / 2 + .9; for (let i = 0; i < 5; i++) { const o = A + st * (i + .5), t = t0 + rnd() * .5 + i * .03, t2 = CORE(q) ? tPre(q) - .25 : undefined; L.push({ x: q.x + o, z: q.z - LQ / 2 + 2.5, ry: PI, t, t2, y: .2 }, { x: q.x + o, z: q.z + LQ / 2 - 2.5, ry: 0, t: t + .08, t2, y: .2 }); if (i > 0 && i < 4) L.push({ x: q.x - LQ / 2 + 2.5, z: q.z + o, ry: -PI / 2, t: t + .12, t2, y: .2 }, { x: q.x + LQ / 2 - 2.5, z: q.z + o, ry: PI / 2, t: t + .16, t2, y: .2 }); } }); frota(UNI, mat(0xffffff), c, { sombra: false }); frota(UNI, mat(0xffffff), j, { sombra: false }); casas(L, { d: .32 }); window.__casas = L.length; for (let q = tA; q < tA + dT * .8; q += .18) som(q, 'pop'); }

// serviços: escola, posto e mercado, com o raio que se anda a pé ---------------------------------------------------
const G_ESC = funde([[gb(12.6, .1, 12.6, 0, .2), 0xe3dccb], [gb(11, 3.4, 3, 0, .25, -4.2), 0xf0a35e], [gb(3, 3.4, 8, -4, .25, .8), 0xf0a35e], [gb(11.3, .3, 3.3, 0, 3.65, -4.2), 0xf4efe6], [gb(3.3, .3, 8.3, -4, 3.65, .8), 0xf4efe6], [gb(6, .06, 7, 2.2, .3, 1.6), 0x3fa45a], [gb(5.6, .08, .1, 2.2, .3, 1.6), 0xffffff], [gc(.08, .08, 6, 6, 5.4, .25, -5.6), 0xe3e3e3], [gb(1.6, 1, .08, 6.2, 5.2, -5.6), 0xd83a3a]]);
const G_POS = funde([[gb(12.6, .1, 12.6, 0, .2), 0xe3dccb], [gb(9, 4, 8, 0, .25, -1), 0xf8f8f6], [gb(4.6, .1, 1.4, 0, 4.26, -1), 0xe0403a], [gb(1.4, .1, 4.6, 0, 4.26, -1), 0xe0403a], [gb(3, 2.2, 1.6, 0, .25, 3.6), 0xe0403a], [gb(9.3, .22, 8.3, 0, 4.25, -1), 0xdadfe4]]);
const G_MER = funde([[gb(13, .1, 13, 0, .2), 0x70757e], [gb(11, 3.2, 6.4, 0, .25, -3), 0x4aa8e8], [gb(11.3, .3, 6.7, 0, 3.45, -3), 0xf4efe6], [gb(9, 1.1, .3, 0, 2.2, .3), 0xffd23f]]);
const svc = k => QD.filter(q => q.tipo === k).map((q, i) => ({ x: q.x, z: q.z, ry: i * 1.5708, sx: 1, sy: 1, sz: 1 }));
const anel = []; [['escola', G_ESC, 0], ['posto', G_POS, 1.5], ['mercado', G_MER, 2.8]].forEach(([k, g, o]) => { const l = svc(k); l.forEach((q, i) => { q.t = T.esc + .15 + o * .85 + i * .16; som(q.t, 'tijolo'); }); frota(g, mV, l, { modo: 'desce', d: .4, dy: 12 }); });
const mAnel = new THREE.MeshBasicMaterial({ color: 0xffd23f, transparent: true, opacity: 0, side: THREE.DoubleSide, depthWrite: false }); svc('escola').forEach((q, i) => { const m = add(new THREE.Mesh(new THREE.RingGeometry(.93, 1, 64), mAnel)); m.rotation.x = -PI / 2; m.position.set(q.x, 7, q.z); const t0 = T.esc + .2 + i * .15; AUTO.push(t => { const k = ease((t - t0) / 1.3); m.visible = t > t0 && t < fim(7); m.scale.setScalar(1 + k * 30); }); }); AUTO.push(t => { mAnel.opacity = .85 * clamp((t - T.esc) / .3) * clamp((fim(7) - t) / .5); });
const crian = []; svc('escola').forEach(q => { for (let i = 0; i < 6; i++) { const a = i * 1.05 + q.x; crian.push([[q.x + Math.cos(a) * 34, 1, q.z + Math.sin(a) * 34], [q.x, 1, q.z]]); } }); pulsos(crian, 240, 0xffc14a, 5, T.esc + .9, fim(7), .4, .6);

// transporte: carros, ônibus e metrô elevado --------------------------------------------------------------------------
const FX = []; for (let k = -5; k <= 5; k++) { FX.push({ x: k * P + 1.2, a: -100, b: 100, v: 1 }, { x: k * P - 1.2, a: 100, b: -100, v: 1 }, { z: k * P + 1.2, a: 100, b: -100, v: 0 }, { z: k * P - 1.2, a: -100, b: 100, v: 0 }); }
const correCar = (i, t, f = 1, t0 = T.oni) => { const l = FX[i % FX.length], u = (i * .6180339 + (t - t0) * (.05 + (i % 5) * .009) * f) % 1, q = l.a + (l.b - l.a) * u, ry = l.v ? (l.b > l.a ? 0 : PI) : (l.b > l.a ? PI / 2 : -PI / 2); return l.v ? [l.x, .09, q, ry] : [q, .09, l.z, ry]; };
const fC = brilhos(Array.from({ length: 460 }, () => [0, -99, 0]), 0xffffff, 7, { cores: [0xfff2c8, 0xff5a4a] }), fO = brilhos(Array.from({ length: 34 }, () => [0, -99, 0]), 0xffe7a8, 5);
moveis(G_CAR, 460, [0xd83a3a, 0x3a7fd8, 0xf2c94c, 0xf4efe6, 0x2fbf8f, 0x30343c, 0xe8683f], (i, t) => { if (t < T.oni + i * .006) return null; return correCar(i, t); }, { de: T.oni, luz: fC, esc: 1 });
moveis(G_ONI, 34, [0xe0403a, 0xffc61a], (i, t) => { if (t < T.oni + i * .03) return null; return correCar(i * 7 + 3, t, .8); }, { de: T.oni, luz: fO, esc: 1 });
{ const pil = []; for (let i = -9; i <= 9; i++) { pil.push({ x: 2.5, z: i * 10 + 1, sx: 1, sy: 9.6, sz: 1, sub: 9.6, c: 0xcfd3d9, t: T.oni + .3 + Math.abs(i) * .1, m: 'sobe' }); if (i) pil.push({ x: i * 10 + 1, z: 2.5, sx: 1, sy: 9.6, sz: 1, sub: 9.6, c: 0xcfd3d9, t: T.oni + .5 + Math.abs(i) * .1, m: 'sobe' }); } const vi = [{ x: 2.5, z: 0, y: 9.6, sx: 1.7, sy: .5, sz: 206, c: 0xe8ebef, t: T.oni + .9, m: 'estica', d: .7 }, { x: 0, z: 2.5, y: 9.6, sx: 206, sy: .5, sz: 1.7, c: 0xe8ebef, t: T.oni + 1.1, m: 'estica', d: .7 }]; frota(UNI, mat(0xffffff), pil, { d: .4 }); vi[0].m = 'pop'; vi[1].m = 'pop'; frota(UNI, mat(0xffffff), vi, { d: .6 });
  const G_V = funde([[gb(1.5, 1.5, 3.8)], [gb(1.54, .5, 3.4, 0, .75), 0xaee3f7]]), fM = brilhos(Array.from({ length: 24 }, () => [0, -99, 0]), 0xbfe6ff, 7); moveis(G_V, 24, [0x2fbf8f, 0xf4efe6], (i, t) => { const lin = i % 2, u = ((t - T.oni) * .07 + Math.floor(i / 2) * .021 + (i % 8 < 4 ? 0 : .5)) % 1, q = -102 + 204 * u; if (t < T.oni + 1.7) return null; return lin ? [q, 10.1, 2.5, PI / 2] : [2.5, 10.1, q, 0]; }, { de: T.oni, luz: fM }); ACENDE.push(k => fM.op(k)); }
ACENDE.push(k => { fC.op(k * .9); fO.op(k); });
for (let q = T.oni + .2; q < D.total; q += 2.2) som(q, 'motor');

// prédios: o centro sobe, e os mais altos ficam no meio ----------------------------------------------------------------
{ const L = [], cores = [0xeaeef2, 0x8fc4e0, 0xf1cda0, 0x7fbfb8, 0xe29a7a, 0xb5c0dc, 0x6fa8d6, 0xf4efe6, 0xd9a0a8, 0xf2d27a]; QD.filter(CORE).forEach(q => { const t0 = tPre(q), w = 6.3; [[-3.5, -3.5], [3.5, -3.5], [-3.5, 3.5], [3.5, 3.5]].forEach(([a, b], i) => { const r = dist(q.x + a, q.z + b), h = (9 + 62 * Math.exp(-((r / 38) ** 2))) * (.62 + rnd() * .55); L.push({ x: q.x + a, z: q.z + b, y0: .2, w, d: w, h, c: corDe(cores), t: t0 + i * .1 + rnd() * .2 }); }); }); predios(L, { d: 1 }); for (let q = T.pre + .1; q < T.pre + dP * .72; q += .38) som(q, 'tijolo'); som(T.pre + .2, 'riser');
  const g = funde([[gb(.9, 34, .9), 0xffc61a], [gb(18, .7, .8, 4, 34), 0xffc61a], [gb(2, 2.2, 2, 0, 34.7), 0xf4efe6], [gb(3, 1.4, 1.2, -4, 33), 0x5e6a78]]); frota(g, mV, [[-30, 12], [30, -12]].map(([x, z], i) => ({ x, z, y: .2, sy: 1.5, ry: i, sub: 60, t: T.pre + .2 + i * .2, t2: fim(9) + .2 })), { modo: 'sobe', d: .9 }); }

// parques: árvores nas ruas e nos pátios, e um lago ------------------------------------------------------------------------
{ const l = [], dA = fim(10) - T.par; QD.forEach(q => { const t0 = T.par + .1 + q.d / 135 * dA * .7; if (q.tipo === 'parque') { for (let i = 0; i < 24; i++) l.push({ x: q.x + (rnd() - .5) * 12, z: q.z + (rnd() - .5) * 12, s: 1.2 + rnd() * .9, pinho: rnd() > .7, t: t0 + rnd() * .7, y: .2 }); return; } if (q.tipo === 'casa' && !CORE(q)) for (let i = 0; i < 7; i++) l.push({ x: q.x + (rnd() - .5) * 6, z: q.z + (rnd() - .5) * 6, s: .85 + rnd() * .4, t: t0 + rnd() * .7, y: .2 }); for (let i = 0; i < 4; i++) { const o = -6 + i * 4; [[o, -LQ / 2 + .4], [o, LQ / 2 - .4], [-LQ / 2 + .4, o], [LQ / 2 - .4, o]].forEach(([a, b]) => l.push({ x: q.x + a, z: q.z + b, s: .7, t: t0 + rnd() * .5, y: .2 })); } }); arvores(l, { d: .4 }); for (let q = T.par + .1; q < T.par + dA * .7; q += .2) som(q, 'pop');
  QD.filter(q => q.tipo === 'parque').forEach((q, i) => { const m = add(new THREE.Mesh(new THREE.CircleGeometry(4.2, 28), mat(V_.rio, { roughness: .2 }))); m.rotation.x = -PI / 2; m.position.set(q.x + 1, .3, q.z - 1); aparece(m, T.par + .4 + i * .2, .4); }); }

// operário em escala de obra: um plano mais perto dele, trabalhando no chão ou sobre a peça ------------------------------
const OP = operario(1.5);
const VIS = [[[-30, 26, 86], [2, 2, 20]], [[34, 46, 150], [0, 0, 58], 1], [[-60, 66, 150], [-16, 0, 46]], [[52, 58, 100], [28, 0, 4]], [[150, 96, 96], [76, 0, -2]], [[-146, 54, 56], [-74, 0, -6]], [[62, 110, 170], [0, 0, 26]], [[-70, 120, 150], [-14, 0, -6]], [[46, 42, 118], [8, 4, 22]], [[-140, 120, 180], [0, 22, 0]], [[170, 180, 250], [0, 8, 6]]];
const Q_ = (i, a, b) => noQuadro(VIS[i][0], VIS[i][1], a, b);
const pp = [null, Q_(1, .3, .5), Q_(2, .2, .3), Q_(3, -.3, .3), [100, 26], [-100, 10], [20, 70], [-20, 52], [20, 72], [0, 72], [60, 110 * .9]];
const Q0 = Q_(0, .2, .35), RT = [[0, Q0[0], Q0[1], 1.7, .3, 'pasmo'], [fim(0) + .05, Q0[0], Q0[1], 1.7, .3, 'pasmo']]; pp.forEach((q, i) => { if (q) RT.push([F(i) + .05, q[0], q[1], i === 3 || i === 4 ? .3 : .25, olha(VIS[i][0], q[0], q[1]), i === 8 ? 'para' : i === 9 ? 'pasmo' : 'bate', 1]); }); RT.push([T_USO, 10, 100, 0, .3, 'pasmo', 1]);
roteiro(OP, RT, T_USO);
{ const m = unico(funde([[gb(1.8, .14, 1.8), 0xd9a55f], [gc(.09, .09, 12, 6, .7, -12, .7), 0x8d939c], [gc(.09, .09, 12, 6, -.7, -12, .7), 0x8d939c], [gc(.09, .09, 12, 6, .7, -12, -.7), 0x8d939c], [gc(.09, .09, 12, 6, -.7, -12, -.7), 0x8d939c]]), 10, 12, 100); aparece(m, F(LAST) - .1, .3, 'desce', 3); }
festa(OP, 10, 100, .1, T_USO - .02, 12.2);

// final: anoitece, um instante de escuro e tudo acende de uma vez ---------------------------------------------------------
const T_L = T_USO + .25;
{ const q = [], r = [], J = []; SEG.forEach((s, i) => { [-5, 5].forEach(o => q.push([s.x + (s.v ? 2.85 : o), 6.6, s.z + (s.v ? o : 2.85)])); }); QD.forEach(b => { for (let i = 0; i < 10; i++) J.push([b.x + (rnd() - .5) * 13, 2.6, b.z + (rnd() - .5) * 13]); });
  const pos = brilhos(q, 0xffcf7a, 15), jan = brilhos(J, 0xffc76a, 9), al = []; QD.filter(CORE).forEach(b => { for (let i = 0; i < 26; i++) al.push([b.x + (rnd() - .5) * 15, 3 + rnd() * rnd() * 40, b.z + (rnd() - .5) * 15]); }); const pr = brilhos(al, 0xffdc9a, 11); ACENDE.push(k => { pos.op(k); jan.op(k * .9); pr.op(k * .8); }); veu(0, 30, 0, 560, 0xffa860, .3); }
fogos(T_L + 1, D.total + 1, 13, 200, 70, 90);
AUTO.push(t => { noite(ease((t - fim(10) - .1) / Math.max(.6, T_USO - fim(10) - .15))); const k = t < T_L ? 0 : 1; acende(t >= T_L ? 1 - (t < T_L + .35 ? Math.max(0, Math.sin((t - T_L) * 40)) * .5 : 0) : 0); });

const K = plano(VIS, [{ t: F(LAST) + .03, ...{ p: VIS[10][0], l: VIS[10][1] } }, { t: F(LAST) + .9, p: [14, 26, 140], l: [8, 15, 30] }, { t: T_USO + 2.2, p: [13, 28, 138], l: [8, 15, 30] }, { t: T_USO + 5, p: [-40, 130, 300], l: [0, 10, 10] }, { t: D.total + 1, p: [-50, 230, 400], l: [0, 10, 10] }]);

// rótulos e sons ---------------------------------------------------------------------------------------------------------
etq('SEM DRENAGEM', F(0) + .15, fim(0), 'ruim');
[['ESTACAS', T.est, fim(1)], ['RUAS', T.rua, fim(2)], ['GALERIA DE CHUVA', T.gal, fim(3)], ['ÁGUA E ESGOTO', T.agu, fim(4)], ['ENERGIA', T.pos, fim(5)], ['CASAS', T.cas, fim(6)], ['ESCOLA PERTO', T.esc, fim(7)], ['TRANSPORTE', T.oni, fim(8)], ['PRÉDIOS', T.pre, fim(9)], ['PARQUES', T.par, fim(10)]].forEach(l => etq(...l));
etq('CIDADE PRONTA!', F(LAST) + .1, T_L, 'grande');
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); som(.1, 'chuva'); som(1, 'chuva'); som(2, 'chuva'); som(.5, 'crack'); som(.9, 'gota'); som(F(LAST) + .1, 'ding'); som(T_L, 'impact'); som(T_L + .05, 'zumbido'); for (let q = T_L + 1; q < D.total; q += 1.4) som(q, 'pop');

window.CAPA_T = T_L + 2;
iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); segueSol(0, 0); AUTO.forEach(f => f(t)); });
