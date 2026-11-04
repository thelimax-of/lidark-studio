// Uma vila virando cidade em anéis: o poço seca, e cada etapa abre um anel novo de ruas em volta da praça. Um mundo só, que cresce.
const { THREE, scene, cam, luzes, ceu, mat, add, box, cil, esf, sh, clamp, ease, back, prng, tex, boneco, camTo, iniciar, fala, som, rotulo, D } = K3;
const V_ = { ceu: ['#4a9be6', '#dff1fb'], sol: 0xfff0dc, grama: 0x62bd55, rio: 0x3a9fd2 }, rnd = prng(31), F = fala, fim = i => F(i) + D.falas[i].dur, AUTO = [], LAST = D.falas.length - 1, N = D.falas.length;
const nk = x => String(x).toLowerCase().normalize('NFD').replace(/[^a-z0-9]/g, '');
const tk = (w, i, f = .4) => { const k = nk(w), q = D.falas[i].words?.find(p => nk(p.w).startsWith(k)); return q ? q.start : F(i) + D.falas[i].dur * f; };
const nomeT = i => { const q = [...(D.falas[i].words ?? [])].reverse().find(p => /^(essa|esse|esses|essas)$/.test(nk(p.w))); return q ? q.start : fim(i) - 1.2; };
const CI = {}; for (let i = 1; i < N - 1; i++) CI[i] = { a: F(i), e: tk('Então', i), n: nomeT(i) };
const ult = D.falas[LAST], nPal = ult.texto.split(/[!.]/)[0].trim().split(/\s+/).length, T_USO = (ult.words[nPal - 1]?.end ?? ult.t + ult.dur) + .15;
cam.near = 1; cam.far = 4000;
const flash = document.createElement('div'); flash.style.cssText = 'position:absolute;inset:0;background:#fff8d8;opacity:0'; document.getElementById('hud').prepend(flash);
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
cenario(240, 800, 3000);
const T = { bom: tk('bombeia', 1), cx: tk('caixa', 1), est: tk('estrada', 2), fei: tk('caminhões', 2), esc: tk('ergue', 3), esg: tk('enterra', 4), lag: tk('lagoas', 4), fab: tk('fábrica', 5), fam: tk('famílias', 5), pon: tk('atravessa', 6), tri: tk('trilhos', 7), tre: tk('trem', 7), pre: tk('constrói', 8) };
const rio = x => 62 + 10 * Math.sin(x / 70) + 6 * Math.sin(x / 31), R = [22, 46, 76, 110, 150], R_TR = 92, NR = 12, AR = k => (k * 30 + 15) * PI / 180, PONTES = [2, 3, 4], dF = fim(5) - T.fam + .6, dPo = fim(6) - T.pon;
const margem = (x, z) => Math.abs(z - rio(x));
const norte = (x, z) => z < rio(x);

// chão, rio, morros, plantações --------------------------------------------------------------------------------
const gr = add(new THREE.Mesh(new THREE.PlaneGeometry(9000, 9000), mat(V_.grama, { roughness: 1 }))); gr.rotation.x = -PI / 2; gr.receiveShadow = true;
const fita = (w, y, c, o = {}) => { const P_ = [], I = []; let n = 0; for (let x = -2200; x <= 2200; x += 14) { const z = rio(x); P_.push(x, y, z - w, x, y, z + w); if (n) I.push(n * 2 - 2, n * 2 - 1, n * 2, n * 2, n * 2 - 1, n * 2 + 1); n++; } const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(P_, 3)); g.setIndex(I); g.computeVertexNormals(); const m = add(new THREE.Mesh(g, mat(c, { roughness: .2, side: THREE.DoubleSide, ...o }))); m.receiveShadow = true; return m; };
fita(13, .03, 0xdcc892, { roughness: 1 }); fita(9.5, .06, V_.rio);
{ const l = []; for (let i = 0; i < 30; i++) { const a = i / 30 * 6.28 + rnd() * .2, r = 640 + rnd() * 420, x = Math.cos(a) * r, z = Math.sin(a) * r; if (Math.abs(z - rio(x)) < 150) continue; l.push({ x, z, sx: 130 + rnd() * 140, sy: 50 + rnd() * 110, sz: 130 + rnd() * 140, c: corDe([0x5fae62, 0x4f9f58, 0x6dbb6a]) }); } frota(new THREE.IcosahedronGeometry(1, 1), mat(0xffffff, { flatShading: true, roughness: 1 }), l, { sombra: false }); }
{ const l = []; for (let i = 0; i < 1700; i++) { const a = rnd() * 6.28, r = 205 + rnd() * rnd() * 520, x = Math.cos(a) * r, z = Math.sin(a) * r; if (margem(x, z) < 18 || Math.hypot(x - 208, z - 32) < 52 || Math.hypot(x + 131.5, z + 131.5) < 48 || Math.abs(Math.sin(a - AR(7)) * r) < 10 && Math.cos(a - AR(7)) > 0 || Math.abs(Math.sin(a - AR(8)) * r) < 16 && Math.cos(a - AR(8)) > 0) continue; l.push({ x, z, s: 3 + rnd() * 2.8, pinho: rnd() > .5 }); } arvores(l); }
// plantações: canteiros em volta da vila, que somem quando a cidade chega
{ const l = [], cs = [0xd9c36a, 0xb7cf6a, 0xe6d27f, 0x8fbf55, 0xc9a85a]; for (let i = 0; i < 24; i++) for (let j = 0; j < 15; j++) { const x = -160 + i * 14 + 3, z = -152 + j * 14, r = Math.hypot(x, z); if (r < 36 || r > 196 || margem(x, z) < 16) continue; { const c8 = Math.cos(AR(8)), s8 = Math.sin(AR(8)), c7 = Math.cos(AR(7)), s7 = Math.sin(AR(7)); if ((Math.abs(-x * s8 + z * c8) < 11 && x * c8 + z * s8 > 0) || (Math.abs(-x * s7 + z * c7) < 11 && x * c7 + z * s7 > 0)) continue; } const nor = norte(x, z), t2 = r < 60 ? T.esc + .2 + r * .01 : nor ? T.fam - .2 + (r - 60) / 120 * dF * .7 : T.pon + (r - 60) / 120 * dPo * .7, c = corDe(cs); l.push({ x, z, y: .03, sx: 12.4, sz: 12.4, sy: .12, c, t2 }); for (let k = -2; k <= 2; k++) l.push({ x: x + k * 2.2, z, y: .15, sx: 1.2, sz: 12, sy: .22, c: new THREE.Color(c).multiplyScalar(.82).getHex(), t2 }); } frota(UNI, mat(0xffffff), l, { sombra: false }); }

// ruas: anéis e raios, que abrem conforme a cidade cresce ---------------------------------------------------------
const tRua = (r, nor) => r < 24 ? T.est + 1 + r * .02 : r < 56 ? T.esc + .1 + (r - 24) * .03 : nor ? T.fam - .3 + (r - 56) / 100 * dF * .4 : T.pon + .6 + (r - 56) / 100 * dPo * .4;
{ const s = [], t_ = []; R.forEach((r, ir) => { const n = Math.round(2 * PI * r / 5); for (let i = 0; i < n; i++) { const a = i / n * 2 * PI, x = Math.cos(a) * r, z = Math.sin(a) * r; if (margem(x, z) < 13) continue; const ry = Math.atan2(-Math.sin(a), Math.cos(a)), L = 2 * PI * r / n + .9, t = tRua(r, norte(x, z)) + (a * 13 % 6.28) * .12; s.push({ x, z, y: .05, ry, sx: 4.2, sy: .07, sz: L, c: 0x4a4c55, t }); if (i % 2) t_.push({ x, z, y: .13, ry, sx: .2, sy: .02, sz: 1.8, c: 0xf2d24a, t }); } }); for (let k = 0; k < NR; k++) { const a = AR(k), br = PONTES.includes(k), max = k === 8 ? 1500 : k === 7 ? 215 : 150; for (let r = 18; r < max; r += 7) { const x = Math.cos(a) * r, z = Math.sin(a) * r, m_ = margem(x, z); if (m_ < 14 && !br) continue; const ry = Math.atan2(Math.cos(a), Math.sin(a)), nor = norte(x, z), t = m_ < 14 ? T.pon + .2 : r > 150 ? T.est + .3 + (1500 - r) / 1500 * .9 : tRua(r, nor); s.push({ x, z, y: .05, ry, sx: 4.6, sy: .07, sz: 7.9, c: 0x4a4c55, t: k === 8 && r > 22 ? T.est + .2 + r / 400 : t, d: .3 }); if (r < 400) t_.push({ x, z, y: .13, ry, sx: .2, sy: .02, sz: 2.2, c: 0xf2d24a, t: (k === 8 && r > 22 ? T.est + .2 + r / 400 : t) + .1 }); } } frota(UNI, mat(0xffffff), s, { sombra: false, d: .4 }); frota(UNI, mat(0xffffff), t_, { sombra: false, recebe: false }); }
for (let q = T.est + .2; q < T.est + 3; q += .3) som(q, 'pop');

// trilho de terra da vila, que a estrada cobre
{ const l = []; for (let i = 0; i < 26; i++) { const a = i / 26 * 6.28; l.push({ x: Math.cos(a) * 22, z: Math.sin(a) * 22, y: .02, ry: -a, sx: 3.4, sy: .04, sz: 7, c: 0xc9a56a, t2: T.est + 1.4 }); } frota(UNI, mat(0xffffff), l, { sombra: false }); }

// lotes: fileiras em volta dos anéis -----------------------------------------------------------------------------------
const LOT = []; [16, 28, 35, 40, 52, 59, 66, 72, 82, 88, 97, 104, 116, 124, 132, 140, 156, 164, 172].forEach(r => { const n = Math.floor(2 * PI * r / (r < 30 ? 5.6 : 3.3)); for (let i = 0; i < n; i++) { const a = (i + (r % 2) * .5) / n * 2 * PI + .03, x = Math.cos(a) * r, z = Math.sin(a) * r; if (margem(x, z) < 15.5) continue; if (Math.hypot(x - 2, z + 33) < 13 || Math.hypot(x - 22, z - 8) < 8 || Math.hypot(x + 34, z + 14) < 19) continue; let perto = false; if (r > 20) for (let k = 0; k < NR; k++) if (Math.abs(((a - AR(k) + PI * 3) % (2 * PI)) - PI) * r < 3.4) perto = true; if (!perto) LOT.push({ x, z, r, a }); } });
const tCasa = b => { const n = norte(b.x, b.z); return b.r < 30 ? -5 : b.r < 42 ? T.fei + .5 + (b.r - 30) * .03 + rnd() * .9 : b.r < 70 ? T.esc + .7 + (b.r - 42) * .05 + rnd() * .8 : n ? T.fam + (b.r - 62) / 110 * dF * .75 + rnd() * .5 : T.pon + .4 + (b.r - 62) / 110 * dPo * .7 + rnd() * .3; };
const dP = fim(8) - T.pre, tPre = r => T.pre + .1 + clamp((r - 20) / 50) * dP * .7;
{ const l = LOT.map(b => ({ x: b.x, z: b.z, ry: Math.atan2(b.x, b.z) + (Math.round(b.r) % 2 ? 0 : PI), s: b.r < 30 ? 1.3 : 1.05, t: tCasa(b), t2: b.r < 68 && b.r > 22 ? tPre(b.r) - .25 : undefined })); casas(l, { d: .3 }); window.__casas = l.length; [T.fei + .5, T.esc + .7].forEach(t0 => { for (let q = t0; q < t0 + 1.8; q += .15) som(q, 'pop'); }); [[T.fam, dF], [T.pon + 1, dPo]].forEach(([t0, d]) => { for (let q = t0; q < t0 + d * .75; q += .13) som(q, 'pop'); }); }
// árvores nos lotes
{ const l = []; for (let i = 0; i < 1300; i++) { const a = rnd() * 6.28, r = 64 + rnd() * 110, x = Math.cos(a) * r, z = Math.sin(a) * r; if (margem(x, z) < 16 || R.some(q => Math.abs(q - r) < 3.2) || Math.abs(r - R_TR) < 3.5) continue; let pert = false; for (let k = 0; k < NR; k++) if (Math.abs(((a - AR(k) + PI * 3) % (2 * PI)) - PI) * r < 3.6) pert = true; if (pert) continue; l.push({ x, z, s: .7 + rnd() * .4, t: (norte(x, z) ? T.fam + .5 + (r - 62) / 110 * dF * .75 : T.pon + 1.4 + (r - 62) / 110 * dPo * .62) + rnd() * .5 }); } arvores(l, { d: .3 }); }
// mato na outra margem: some quando a ponte leva as casas para lá
{ const l = []; for (let i = 0; i < 1400; i++) { const a = rnd() * 6.28, r = 62 + rnd() * 140, x = Math.cos(a) * r, z = Math.sin(a) * r; if (norte(x, z) || margem(x, z) < 15) continue; l.push({ x, z, s: .7 + rnd() * 1.1, pinho: rnd() > .6, t2: T.pon + .2 + clamp((r - 62) / 110) * dPo * .7 }); } arvores(l); }

// a praça da vila: chão rachando, o poço secando, a igreja, a fila -----------------------------------------------------------
{ const b = add(cil(13, 13, .16, 0xe0d8c4, 48)); b.position.y = .08; b.receiveShadow = true;
  const lama = add(new THREE.Mesh(new THREE.CircleGeometry(8, 40), mat(0xa47e55, { roughness: 1 }))); lama.rotation.x = -PI / 2; lama.position.y = .165; lama.receiveShadow = true; AUTO.push(t => { lama.visible = t < T.bom + 2.6; });
  const n = funde([[gc(1.9, 2.1, 1.2, 18), 0x9c958a], [gc(1.5, 1.5, 1.22, 18), 0x1c1712], [gb(.22, 3.2, .22, -1.9), 0x7a4a26], [gb(.22, 3.2, .22, 1.9), 0x7a4a26], [gb(4.2, .2, .2, 0, 3.2), 0x7a4a26]]); unico(n, 0, .16, 0); }
{ const g = funde([[gb(9, 5.6, 14), 0xf6f1e4], [chato(new THREE.ConeGeometry(7.2, 3.4, 4).rotateY(.785398).scale(.9, 1, 1.42).translate(0, 7.3, 0)), 0xb5482f], [gb(4, 11, 4, 0, 0, 7), 0xf6f1e4], [chato(new THREE.ConeGeometry(3, 3.6, 4).rotateY(.785398).translate(0, 12.8, 7)), 0xb5482f], [gb(.16, 1.6, .16, 0, 14.4, 7), 0xffd23f], [gb(1, .16, .16, 0, 15.1, 7), 0xffd23f], [gb(1.6, 2.6, .1, 0, 0, 9.04), 0x7a4a26], [gb(1, 1, .1, 0, 6.2, 9.04), 0x7fbcd9]]); unico(g, 2, 0, -33, 0.05); }
// a água do poço encolhe e vira lama; volta azul quando a caixa d'água chega
{ const poca = add(new THREE.Mesh(new THREE.CircleGeometry(1.46, 32), new THREE.MeshStandardMaterial({ color: 0x3a8fc8, roughness: .12, metalness: .1 }))); poca.rotation.x = -PI / 2; poca.position.y = 1.395; const CA = new THREE.Color(0x3a8fc8), CL = new THREE.Color(0x4a3220);
  AUTO.push(t => { if (t > T.bom + 2.6) { poca.scale.setScalar(1); poca.material.color.copy(CA); return; } const k = clamp((t + 1.5) / 3.3); poca.scale.setScalar(Math.max(1 - k * .9, .06)); poca.material.color.copy(CA).lerp(CL, k); }); }
// balde que sobe vazio, pedras da borda caindo, rachaduras correndo pelo chão, poeira
const balde = add(cil(.42, .32, .6, 0x8a96a5, 14)), corda = add(box(.05, 1, .05, 0xc9a56a, .01));
AUTO.push(t => { const v = t < fim(0) + .2; balde.visible = corda.visible = v; if (!v) return; const q = clamp((t + .5) / 1.9), y = .5 + ease(q) * 2.2; balde.position.set(0, y, 0); balde.rotation.z = q >= 1 ? Math.sin((t - 1.4) * 4) * .55 : 0; const L = 3.36 - (y + .3); corda.scale.y = Math.max(L, .01); corda.position.set(0, y + .3 + L / 2, 0); });
{ const P_ = []; for (let i = 0; i < 8; i++) { const m = add(new THREE.Mesh(new THREE.IcosahedronGeometry(.17 + rnd() * .08, 0), mat(0x8f887c, { flatShading: true }))); m.castShadow = true; P_.push({ m, a: i * .85 + .3, t0: -.3 + i * .26 }); }
  AUTO.push(t => P_.forEach(p => { const d = t - p.t0, r = 1.8; if (t > fim(0)) { p.m.visible = false; return; } p.m.visible = true; if (d < 0) { p.m.position.set(Math.cos(p.a) * r, 1.42, Math.sin(p.a) * r); return; } const k = Math.min(d / .6, 1); p.m.visible = k < 1; p.m.position.set(Math.cos(p.a) * r * (1 - k * .55), 1.42 + .25 * Math.sin(k * PI) - k * k * 1.6, Math.sin(p.a) * r * (1 - k * .55)); p.m.rotation.set(d * 6, d * 4, 0); })); }
{ const l = []; for (let i = 0; i < 56; i++) { const a = i * 2.39996 + rnd() * .3, r0 = 2.1 + (i % 6) * .95 + rnd() * .5, L = 1.3 + rnd() * 1.9; l.push({ x: Math.cos(a) * (r0 + L / 2), z: Math.sin(a) * (r0 + L / 2), y: .17, ry: -a + (rnd() - .5) * .6, sx: L, sy: .03, sz: .14 + rnd() * .1, c: 0x2e1d12, t: -1 + i * .045, m: 'estica', t2: T.bom + 2.6 }); } frota(UNI, mat(0xffffff, { roughness: 1 }), l, { sombra: false, d: .3 }); }
{ const n = 70, b = brilhos(Array.from({ length: n }, () => [0, -99, 0]), 0xd9b98a, 1.5, { normal: true }); AUTO.push(t => { if (t > fim(0) + .3) { b.op(0); return; } b.op(.7); for (let i = 0; i < n; i++) { const u = (t * .45 + i * .37) % 1, a = i * 2.3, r = 2 + (i % 6) * 1.1 + u * 2; b.pos[i * 3] = Math.cos(a) * r; b.pos[i * 3 + 1] = .2 + u * 2.4; b.pos[i * 3 + 2] = Math.sin(a) * r; } b.sync(); }); }
// fila de moradores com balde vazio, do outro lado do poço
const CAMISAS = [0xe8683f, 0x4285f4, 0xf4c95d, 0xd86aa0, 0x7fc97f], CABELOS = [0x3a2a1e, 0x8a5a33, 0x222222, 0xb08a4a];
const gente = (i, o = {}) => { const q = boneco({ cabeca: 'bloco', camisa: CAMISAS[i % 5], calca: [0x3a4464, 0x2b3a67, 0x5a4a3a][i % 3], sapato: 0xe9e4d8, cabelo: CABELOS[i % 4], ...o }); add(q); return q; };
const FILA = []; for (let i = 0; i < 11; i++) { const q = gente(i), a = PI * .8 + i * .19, r = 3.6 + i * 1.2; q.position.set(Math.cos(a) * r, .16, Math.sin(a) * r); q.rotation.y = Math.atan2(-q.position.x, -q.position.z); add(cil(.2, .15, .3, 0x8a96a5, 10), q).position.set(.45, .15, .25); FILA.push(q); }
AUTO.push(t => { const v = t < T.bom + .4; FILA.forEach((q, i) => { q.visible = v; if (!v) return; q.r.anda(0, 0); q.r.respira(t + i); if (i % 3 === 0) { const w = Math.sin(t * 7 + i); q.r.be.j.rotation.x = -2.5 + w * .15; q.r.bd.j.rotation.x = -2.5 - w * .15; } else if (i % 3 === 1) { q.r.be.j.rotation.x = q.r.bd.j.rotation.x = -.4; q.r.cab.rotation.x = .35; } }); });
// fala 1: gente carregando balde do rio até a vila, a pé
const ZA = 30, ZR = rio(-6) - 12.5, CARR = []; for (let i = 0; i < 6; i++) { const q = gente(i + 2); const bd = add(cil(.2, .15, .32, 0x8a96a5, 10), q.r.bd.k); bd.position.y = -.45; CARR.push(q); }
AUTO.push(t => CARR.forEach((q, i) => { const v = t > F(1) - .1 && t < T.bom + 1.5; q.visible = v; if (!v) return; const u = ((t - F(1)) * .04 + i / 6) % 1, ida = u < .5, k = ida ? u * 2 : 2 - u * 2; q.position.set(-7 + (i % 2) * 1.5, .05, ZA + (ZR - ZA) * k); q.rotation.y = ida ? 0 : PI; q.r.anda(t * .9 + i); }));

// caixa d'água: bomba no rio, cano até a caixa alta, um cano para cada casa ----------------------------------------------------------
{ const bx = 4, bz = rio(4) - 12, g = funde([[gb(7, 4, 6), 0xdfe3e8], [gb(7.6, .4, 6.6, 0, 4), 0x4aa8e8], [new THREE.CylinderGeometry(.6, .6, 4, 12).rotateX(PI / 2).translate(0, 1, 4.4), 0x8d939c]]); aparece(unico(g, bx, 0, bz), T.bom, .4); som(T.bom, 'tijolo'); const cx = 22, cz = 8, q = funde([[gc(1, 1.3, 11, 8), 0xdfe3e8], [gc(3.8, 1.1, 3, 20, 0, 11), 0x4aa8e8], [gc(3.8, 3.8, 1.1, 20, 0, 14), 0x4aa8e8], [gc(4, 4, .3, 20, 0, 15.1), 0xf4efe6]]); aparece(unico(q, cx, 0, cz), T.cx, .55, 'desce', 26); som(T.cx + .3, 'impact');
  const it = [], cam_ = [[[bx, 1, bz], [cx, 1, cz], [cx, 14, cz]]]; for (let i = 0; i < 16; i++) { const u = i / 16, v = (i + 1) / 16; it.push({ a: [bx + (cx - bx) * u, .4, bz + (cz - bz) * u], b: [bx + (cx - bx) * v, .4, bz + (cz - bz) * v], t: T.bom + .3 + i * .05 }); } const cs = LOT.filter(b => b.r < 30 && b.z > -14); cs.forEach((b, i) => { it.push({ a: [cx, .3, cz], b: [b.x, .3, b.z], t: T.cx + .7 + i * .06 }); cam_.push([[cx, 14, cz], [cx, 1, cz], [b.x, 1, b.z]]); }); cabos(it, 0x2f8ae6, .5, { sombra: true, ate: fim(1) + .5 }); pulsos(cam_, 160, 0x4fc3ff, 4.5, T.bom + .7, fim(1) + .4, .4, 2.4); }
// água jorra no poço da praça
{ const n = 60, b = brilhos(Array.from({ length: n }, () => [0, -99, 0]), 0x4fc3ff, 3.2, { normal: true }); AUTO.push(t => { if (t < T.bom + 2.6 || t > fim(2)) { b.op(0); return; } b.op(1); for (let i = 0; i < n; i++) { const u = (t * .9 + i / n) % 1, a = i * 2.4; b.pos[i * 3] = Math.cos(a) * u * 2; b.pos[i * 3 + 1] = 2 + u * 3.2 - u * u * 5; b.pos[i * 3 + 2] = Math.sin(a) * u * 2; } b.sync(); }); }

// rodovia: caminhões entram pela estrada nova ---------------------------------------------------------------------------------
const A8 = AR(8), CA8 = Math.cos(A8), SA8 = Math.sin(A8), RY8 = Math.atan2(-CA8, -SA8);
moveis(G_CAM, 26, [0xffc61a, 0xe8683f, 0x2f7fd6, 0xf4efe6], (i, t) => { if (t < T.est + .8 + i * .2) return null; if (t > F(7) - .3 && t < T.tre + 1.2) return null; const ida = i % 2, u = ((t - T.est) * .06 + i * .17) % 1, r = ida ? 24 + u * 700 : 724 - u * 700, o = ida ? 1.1 : -1.1; return [CA8 * r - SA8 * o, .08, SA8 * r + CA8 * o, ida ? RY8 + PI : RY8]; }, { de: T.est, esc: 1.15 });
// feira: as barracas aparecem na praça com o que os caminhões trazem
{ const g = funde([[gb(.1, 1.7, .1, -1.2, 0, -1), 0xdddddd], [gb(.1, 1.7, .1, 1.2, 0, -1), 0xdddddd], [gb(.1, 1.7, .1, -1.2, 0, 1), 0xdddddd], [gb(.1, 1.7, .1, 1.2, 0, 1), 0xdddddd], [gb(2.2, .7, 1.8, 0, 0, 0), 0xc9985a], [chato(new THREE.ConeGeometry(2, 1, 4).rotateY(.785398).scale(1.1, 1, 1).translate(0, 2.2, 0))]]); const l = []; for (let i = 0; i < 2; i++) { const n = i ? 26 : 18; for (let k = 0; k < n; k++) { const a = k / n * 6.28, r = i ? 11 : 7.2; l.push({ x: Math.cos(a) * r, z: Math.sin(a) * r, y: .16, ry: -a, c: [0xe0403a, 0xffc61a, 0x2fbf8f, 0x4aa8e8, 0xf4efe6, 0xff8ae2][k % 6], t: T.fei + .2 + k * .05 + i * .4 }); } } frota(g, mV, l, { d: .3 }); for (let q = T.fei + .2; q < T.fei + 2; q += .17) som(q, 'pop'); const p = []; for (let i = 0; i < 90; i++) { const a = rnd() * 6.28, r = 4.2 + rnd() * 8.6; p.push({ x: Math.cos(a) * r, z: Math.sin(a) * r, y: .16, sx: .55, sy: 1.5, sz: .4, c: corDe([0xe8683f, 0x4285f4, 0xf4c95d, 0xd86aa0, 0x7fc97f, 0xffffff]), t: T.fei + .5 + rnd() * 1.6 }); } frota(funde([[gb(1, .68, 1)], [gb(.75, .32, .75, 0, .68), 0xd9a57c]]), mV, p, { d: .3 }); }

// escola: as crianças brincam no terreno vazio; o prédio desce em volta delas -------------------------------------------------------
const XE = -34, ZE = -14, PXE = -29.2, PZE = -12.8;
{ const g = funde([[gb(30, .18, 24, 0, 0), 0xe3dccb], [gb(26, 5, 5, 0, .15, -8.5), 0xf0a35e], [gb(5, 5, 14, -10.5, .15, 1), 0xf0a35e], [gb(26.5, .5, 5.5, 0, 5.15, -8.5), 0xf4efe6], [gb(5.5, .5, 14.5, -10.5, 5.15, 1), 0xf4efe6], [gb(14, .08, 11, 4, .2, 3), 0x3fa45a], [gb(13, .1, .16, 4, .22, 3), 0xffffff], [gc(.12, .12, 9, 6, 13, .18, -3), 0xeeeeee], [gb(2.4, 1.5, .1, 14.2, 7.5, -3), 0xd83a3a], [gb(24, 1.6, .06, 0, 1.8, -5.97), 0x8fc6df], [gb(.06, 1.6, 12, -7.97, 1.8, 1), 0x8fc6df]]); aparece(unico(g, XE, 0, ZE, .4), T.esc + .1, .45, 'desce', 18); som(T.esc + .4, 'impact'); }
const KIDS = []; for (let i = 0; i < 9; i++) KIDS.push(gente(i, { altura: .62, sapato: 0xffffff }));
AUTO.push(t => KIDS.forEach((q, i) => { const v = t > F(3) - .2 && t < fim(3) + .3; q.visible = v; if (!v) return; const a = t * .8 + i * PI * 2 / 9, r = 2.6 + (i % 3) * 1.1; q.position.set(PXE + Math.cos(a) * r, .2, PZE + Math.sin(a) * r); q.rotation.y = Math.atan2(-Math.sin(a), Math.cos(a)); q.r.anda(t * 1.2 + i); }));

// esgoto: valas nos raios, cano enterrado, lagoas de tratamento antes do rio ---------------------------------------------------------
const ESX = 208, ESZ = rio(232) - 34;
{ const v = [], c = []; for (let k = 0; k < NR; k++) { const a = AR(k); for (let r = 20; r < 110; r += 7) { const x = Math.cos(a) * r, z = Math.sin(a) * r; if (margem(x, z) < 15) continue; const t = T.esg + .1 + r * .02, ry = Math.atan2(Math.cos(a), Math.sin(a)); v.push({ x, z, y: .14, ry, sx: 3.6, sy: .05, sz: 7.4, c: 0x6a4a2e, t, t2: fim(4) - .3 }); c.push({ x, z, y: .2, ry, sx: 1.1, sy: 1, sz: 3.2, c: 0xa8703e, t: t + .2, t2: fim(4) - .3, m: 'desce', dy: 7 }); } } frota(UNI, mat(0xffffff), v, { sombra: false }); frota(chato(new THREE.CylinderGeometry(.5, .5, 2, 12).rotateX(PI / 2).translate(0, .5, 0)), mat(0xffffff), c); for (let q = T.esg + .1; q < T.esg + 2.2; q += .2) som(q, 'tijolo');
  const L = [[-24, -16, 0x6a5230], [0, -16, 0x8f7f48], [24, -16, 0x8aa86a], [-24, 16, 0x7cb8a0], [0, 16, 0x69b6c9], [24, 16, 0x3fa9d6]]; L.forEach(([a, b, co], i) => { const g = funde([[gb(23, 1.2, 29), 0xd5d8dd], [gb(21, .1, 27, 0, 1.2), co]]); aparece(unico(g, ESX + a, 0, ESZ + b), T.lag + i * .18, .35); som(T.lag + i * .18, 'pop'); }); const cl = []; for (let i = 0; i < 12; i++) cl.push([[Math.cos(AR(i)) * 40, 1.6, Math.sin(AR(i)) * 40], [Math.cos(AR(i)) * 110, 1.6, Math.sin(AR(i)) * 110], [ESX - 24, 2, ESZ - 16], [ESX + 24, 2, ESZ + 16], [ESX + 30, 1, rio(ESX + 30)]]); pulsos(cl, 240, 0xb07a3a, 5.5, T.esg + .9, fim(4) + .5, .22, 2.2); }
// mancha suja no rio, que some com o tratamento
{ const n = 34, mm = mat(0x6e5530, { roughness: .4, transparent: true, opacity: 0 }); for (let i = 0; i < n; i++) { const x = -60 + i * 13, m = add(new THREE.Mesh(new THREE.CircleGeometry(6.5 + (i % 3), 18), mm)); m.rotation.x = -PI / 2; m.scale.y = .8; m.position.set(x, .09, rio(x)); } AUTO.push(t => { mm.opacity = .8 * clamp((t - F(4)) / .4) * (1 - clamp((t - T.lag - .8) / 1.2)); }); }

// zona industrial: os jovens saindo pela estrada; a fábrica chega e as famílias vêm -------------------------------------------------
const SAI = []; for (let i = 0; i < 6; i++) { const q = gente(i + 1); const m = add(box(.5, .42, .24, [0x8c5a3c, 0x2f7fd6, 0xd83a3a][i % 3], .05), q.r.bd.k); m.position.set(0, -.55, 0); SAI.push(q); }
AUTO.push(t => SAI.forEach((q, i) => { const v = t > F(5) - .1 && t < T.fab + .8; q.visible = v; if (!v) return; const r = 27 + i * 2.4 + (t - F(5)) * 1.6, o = (i % 2 ? 1 : -1) * 3; q.position.set(CA8 * r - SA8 * o, .1, SA8 * r + CA8 * o); q.rotation.y = Math.atan2(CA8, SA8); q.r.anda(t + i); }));
const FX_ = Math.cos(AR(7)) * 186, FZ_ = Math.sin(AR(7)) * 186;
{ const x = FX_, z = FZ_, g = funde([[gb(70, .2, 44), 0xbfc3c8], [gb(40, 11, 18, -8, .2, -9), 0x8c5a3c], [gb(41, .6, 19, -8, 11.2, -9), 0x5e6a78], [gb(22, 8, 14, 14, .2, 10), 0xd0d4da], [gb(22.6, .6, 14.6, 14, 8.2, 10), 0x4aa8e8], [gc(1.8, 2.5, 30, 14, -20, .2, 11), 0xc25a3a], [gc(1.8, 2.5, 30, 14, -12, .2, 11), 0xc25a3a], [gb(3.8, 1.5, 3.8, -20, 19, 11), 0xf4efe6], [gb(3.8, 1.5, 3.8, -12, 19, 11), 0xf4efe6]]); aparece(unico(g, x, 0, z, .6), T.fab + .1, .55, 'desce', 26); som(T.fab + .4, 'impact');
  const n = 130, b = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1, 1), mat(0xe2e4e8, { roughness: 1, transparent: true, opacity: .85 }), n); b.frustumCulled = false; add(b); const c6 = Math.cos(.6), s6 = Math.sin(.6), cha = [[-20, 11], [-12, 11]].map(([a, q]) => [x + a * c6 + q * s6, z - a * s6 + q * c6]); AUTO.push(t => { const v = t > T.fab + .7; b.visible = v; if (!v) return; for (let i = 0; i < n; i++) { const u = (t * .16 + i * .137) % 1, c = cha[i % 2]; O.position.set(c[0] + u * 44 + Math.sin(i + t * .4) * 3, 31 + u * 75, c[1] - u * 20 + Math.cos(i * 2) * 3); O.rotation.set(0, 0, 0); O.scale.setScalar(2.4 + u * 9); O.updateMatrix(); b.setMatrixAt(i, O.matrix); } b.instanceMatrix.needsUpdate = true; }); }

// ponte: três travessias e a outra margem acorda ------------------------------------------------------------------------------------------------
{ PONTES.forEach((k, i) => { const a = AR(k), r = (rio(Math.cos(a) * 62) + 0) / Math.sin(a), x = Math.cos(a) * r, z = Math.sin(a) * r, L = 62 / Math.sin(a) * .62, ry = Math.atan2(Math.cos(a), Math.sin(a)), par = []; par.push([gb(6.6, .5, L, 0, 1.1), 0xcfd3d9]); [-3.1, 3.1].forEach(o => { par.push([gb(.2, .7, L, o, 1.6), 0xe0403a]); for (let q = -3; q <= 3; q++) par.push([gb(.5, 1.2, .9, o, 0, q * L / 7), 0xb9bdc4]); }); const m = unico(funde(par), x, 0, z, ry); aparece(m, T.pon + .1 + i * .3, .5, 'desce', 14); som(T.pon + .3 + i * .3, 'tijolo'); }); }

// ferrovia: estrada entupida, trilhos em anel e o trem ------------------------------------------------------------------------------------------
moveis(G_CAM, 28, [0xffc61a, 0xe8683f, 0x2f7fd6, 0xf4efe6, 0xd83a3a], (i, t) => { const lado = i % 2, j = Math.floor(i / 2); const sai = Math.max(0, t - (T.tre + .7)), r = (lado ? 30 : 32) + j * 4 + Math.sin(t * 1.3 + j) * .12 + (lado ? 1 : -1) * sai * sai * 9, o = lado ? 1.1 : -1.1; if (r < 22) return null; return [CA8 * r - SA8 * o, .08, SA8 * r + CA8 * o, lado ? RY8 + PI : RY8]; }, { de: F(7) - .3, ate: T.tre + 3.5, esc: 1.15 });
{ const n = Math.round(2 * PI * R_TR / 3.1), it = [], dor = []; for (let i = 0; i < n; i++) { const a = i / n * 2 * PI, x = Math.cos(a) * R_TR, z = Math.sin(a) * R_TR, t = T.tri + .05 + (i / n) * 1.6, m_ = margem(x, z) < 15; dor.push({ x, z, y: m_ ? 1.3 : .05, ry: -a, sx: 3.6, sy: .16, sz: .8, c: 0x8a6a4a, t }); it.push({ x, z, y: (m_ ? 1.46 : .21), ry: -a, sx: 2.4, sy: .1, sz: 3.3, c: 0xb9bdc4, t }); } frota(UNI, mat(0xffffff), dor, { sombra: false, d: .2 }); frota(funde([[gb(.14, 1, 1, -.5)], [gb(.14, 1, 1, .5)]]), mV, it, { sombra: false, d: .2 }); for (let q = T.tri + .05; q < T.tri + 1.7; q += .17) som(q, 'toc');
  const G_V = funde([[gb(2.3, 2.1, 6.2, 0, .5), 0xffffff], [gb(2.34, .7, 5.2, 0, 1.4), 0xaee3f7], [gb(2.2, .3, 5.8, 0, .2), 0x24262a]]), NV = 22, fT = brilhos(Array.from({ length: NV }, () => [0, -99, 0]), 0xcfeaff, 11); moveis(G_V, NV, [0xe0403a, 0xf4efe6], (i, t) => { if (t < T.tre) return null; const a = 4.32 + (t - T.tre) * .19 - i * .073 + (i >= 11 ? 3.14 : 0), x = Math.cos(a) * R_TR, z = Math.sin(a) * R_TR; return [x, margem(x, z) < 15 ? 1.5 : .28, z, Math.atan2(-Math.sin(a), Math.cos(a))]; }, { de: T.tre, luz: fT }); ACENDE.push(k => fT.op(k)); som(T.tre + .2, 'motor');
  const st = funde([[gb(30, .5, 7), 0xcfd3d9], [gb(26, 3.4, 3, 0, .5, 2), 0xf0a35e], [gb(30, .4, 8, 0, 4, .5), 0xf4efe6]]); [AR(1) + .26, AR(10) + .26].forEach((a, i) => aparece(unico(st, Math.cos(a) * (R_TR + 6), 0, Math.sin(a) * (R_TR + 6), Math.atan2(Math.cos(a), Math.sin(a)) + PI / 2), T.tri + .8 + i * .4, .4, 'pop')); }

// carros nos anéis e nos raios ------------------------------------------------------------------------------------------------------------------------
const FX = []; R.forEach((r, ir) => { let a0 = null; const N_ = 360; for (let i = 0; i <= N_; i++) { const a = i / N_ * 2 * PI, x = Math.cos(a) * r, z = Math.sin(a) * r, ok = margem(x, z) >= 13 && i < N_; if (ok && a0 === null) a0 = a; if ((!ok) && a0 !== null) { const am = (a0 + a) / 2, nor = norte(Math.cos(am) * r, Math.sin(am) * r); FX.push({ r: r + 1, a0, a1: a, t: tRua(r, nor) + 1.4, s: 1 }, { r: r - 1, a0: a, a1: a0, t: tRua(r, nor) + 1.8, s: -1 }); a0 = null; } } });
const LANE = []; FX.forEach(l => { const n = Math.ceil(l.r * Math.abs(l.a1 - l.a0) / 16); for (let i = 0; i < n; i++) LANE.push(l); });
const fC = brilhos(Array.from({ length: 520 }, () => [0, -99, 0]), 0xffffff, 7, { cores: [0xfff2c8, 0xff5a4a] });
moveis(G_CAR, 520, [0xd83a3a, 0x3a7fd8, 0xf2c94c, 0xf4efe6, 0x2fbf8f, 0x30343c, 0xe8683f], (i, t) => { const l = LANE[i % LANE.length]; if (t < l.t + (i % 37) * .05) return null; const u = (i * .7548 + t * (.03 + (i % 5) * .006) * 60 / l.r) % 1, a = l.a0 + (l.a1 - l.a0) * u, s = Math.sin(a), c = Math.cos(a); return [c * l.r, .1, s * l.r, Math.atan2(-s * l.s, c * l.s)]; }, { de: T.est + 1, luz: fC }); ACENDE.push(k => fC.op(k * .9));

// prédios: a vila antiga vira o centro --------------------------------------------------------------------------------------------------------------------
{ const L = [], cores = [0xeaeef2, 0x8fc4e0, 0xf1cda0, 0x7fbfb8, 0xe29a7a, 0xb5c0dc, 0x6fa8d6, 0xf4efe6, 0xd9a0a8, 0xf2d27a]; [[29, 1], [38, 2], [53, 3], [62, 3]].forEach(([r, n]) => { for (let k = 0; k < NR; k++) for (let i = 0; i < n; i++) { const a = AR(k) + PI / 12 * 2 + (i - (n - 1) / 2) * (8.6 / r), x = Math.cos(a) * r, z = Math.sin(a) * r; if (margem(x, z) < 15.5 || Math.hypot(x - 2, z + 33) < 13 || Math.hypot(x - XE, z - ZE) < 21 || Math.hypot(x - 22, z - 8) < 9) continue; const h = (12 + 54 * Math.exp(-(((r - 29) / 24) ** 2))) * (.62 + rnd() * .55); L.push({ x, z, w: 7, d: 7, h, ry: -a, c: corDe(cores), t: tPre(r) + rnd() * .5 }); } }); predios(L, { d: 1 }); for (let q = T.pre + .1; q < T.pre + dP * .7; q += .34) som(q, 'tijolo'); som(T.pre + .2, 'riser'); }

// final: anoitece e a cidade inteira acende, com fogos ---------------------------------------------------------------------------------------------------------------
const T_L = T_USO + .25;
{ const q = []; R.forEach(r => { const n = Math.round(2 * PI * r / 6); for (let i = 0; i < n; i++) { const a = i / n * 6.28, x = Math.cos(a) * (r + 2.6), z = Math.sin(a) * (r + 2.6); if (margem(x, z) > 13) q.push([x, 5, z]); } }); for (let k = 0; k < NR; k++) for (let r = 20; r < 150; r += 7) { const x = Math.cos(AR(k)) * r, z = Math.sin(AR(k)) * r; if (margem(x, z) > 13) q.push([x, 5, z]); } const J = LOT.filter((_, i) => i % 2 === 0).map(b => [b.x, 2.6, b.z]), al = []; for (let i = 0; i < 700; i++) { const a = rnd() * 6.28, r = 26 + rnd() * 42; al.push([Math.cos(a) * r, 4 + rnd() * rnd() * 56, Math.sin(a) * r]); } const pos = brilhos(q, 0xffcf7a, 15), jan = brilhos(J, 0xffc76a, 10), pr = brilhos(al, 0xffdc9a, 12); ACENDE.push(k => { pos.op(k); jan.op(k * .9); pr.op(k * .8); }); veu(0, 34, 10, 640, 0xffa860, .2); }
fogos(T_L + .5, D.total + 1, 13, 280, 100, 110, 22, 50);
AUTO.push(t => { noite(ease((t - fim(8) - .1) / Math.max(.6, T_USO - fim(8) - .15))); acende(t >= T_L ? 1 - (t < T_L + .35 ? Math.max(0, Math.sin((t - T_L) * 40)) * .5 : 0) : 0);
  let fl = 0; for (let i = 1; i < N - 1; i++) { const d = t - CI[i].n; if (d > 0 && d < .6) fl = Math.max(fl, .6 * (1 - d / .6)); } flash.style.opacity = fl; });

// câmera ---------------------------------------------------------------------------------------------------------------------
const K = [], P = (t, p, l, f = 34) => K.push({ t, p, l, f }), cut = (t, p, l, f = 34) => { const a = K[K.length - 1]; if (a) P(t - .02, a.p, a.l, a.f); P(t + .02, p, l, f); };
P(0, [7.4, 7, 10.4], [-.4, .6, -.6]); P(2, [9.6, 8.6, 13.8], [-.6, .6, -1]); P(fim(0), [22, 17, 34], [-1, 1, -6]);
cut(F(1), [-30, 15, 12], [-4, 0, 44]); P(T.bom - .05, [-32, 18, 14], [-1, 0, 46]); P(T.bom + .7, [-30, 24, 16], [6, 1, 42]); P(T.cx + .5, [58, 28, 50], [20, 7, 12]); P(fim(1), [54, 32, 42], [16, 5, 6]);
cut(F(2), [80, 100, 112], [0, 0, -12]); P(T.est + .2, [78, 98, 106], [-4, 0, -18]); P(T.fei + .3, [14, 70, 54], [-22, 0, -80]); P(fim(2) - .6, [26, 32, 46], [0, 0, 0]); P(fim(2), [24, 30, 42], [0, 0, 0]);
cut(F(3), [-7, 19, 15], [-29, 1, -12]); P(T.esc + .7, [-3, 25, 21], [-31, 1, -13]); P(fim(3), [6, 40, 36], [-30, 0, -14]);
cut(F(4), [44, 30, 106], [46, 0, 62]); P(T.esg, [62, 72, 132], [28, 0, 36]); P(T.lag - .1, [70, 82, 140], [40, 0, 40]); P(T.lag + .9, [262, 78, 120], [206, 0, 30]); P(fim(4), [256, 74, 110], [206, 0, 30]);
cut(F(5), [-13, 7, -13], [-8.6, 1, -32]); P(T.fab - .1, [-15, 9, -18], [-11, 1, -40]); P(T.fab + .7, [-62, 62, -46], [-128, 6, -128]); P(T.fam + .4, [-36, 96, -6], [-92, 0, -96]); P(fim(5), [-6, 150, 56], [-70, 0, -90]);
cut(F(6), [-12, 24, 20], [-16, 0, 92]); P(T.pon + .1, [-6, 30, 26], [-14, 0, 80]); P(T.pon + 1.2, [46, 34, 28], [-20, 0, 66]); P(fim(6), [64, 70, 6], [-14, 0, 92]);
cut(F(7), [14, 14, -30], [-18, 0, -80]); P(T.tri, [16, 18, -28], [-20, 0, -82]); P(T.tre + .5, [56, 66, -14], [-20, 0, -78]); P(fim(7), [112, 110, 44], [0, 0, -20]);
cut(F(8), [30, 34, 50], [0, 4, 0]); P(T.pre + .3, [34, 38, 56], [0, 6, 0]); P(T.pre + 1.6, [-60, 84, 112], [0, 14, 0]); P(fim(8), [-112, 122, 172], [0, 20, 0]);
P(F(LAST) + .03, [-118, 126, 180], [0, 22, 0]); P(F(LAST) + .9, [20, 52, 182], [4, 20, 40]); P(T_USO + 2.2, [18, 54, 178], [4, 20, 40]); P(T_USO + 5, [-50, 150, 360], [0, 10, 30]); P(D.total + 1, [-40, 300, 500], [0, 10, 30]);
K.sort((a, b) => a.t - b.t); for (let i = 1; i < K.length; i++) if (K[i].t <= K[i - 1].t) K[i].t = K[i - 1].t + .01;

// rótulos e sons ----------------------------------------------------------------------------------------------------------------------------------------------------
etq('POÇO SECO', 2.05, fim(0), 'ruim');
etq('RIO SUJO', F(4) + .3, CI[4].e, 'ruim'); etq('ENGARRAFADO', F(7) + .3, CI[7].e, 'ruim');
const NOM = ['', "CAIXA D'ÁGUA", 'RODOVIA', 'ESCOLA', 'ESGOTO TRATADO', 'ZONA INDUSTRIAL', 'PONTE', 'FERROVIA', 'PRÉDIOS'];
for (let i = 1; i < N - 1; i++) { etq(NOM[i], CI[i].n, fim(i)); som(CI[i].n, 'whoosh'); }
etq('VIROU CIDADE!', F(LAST) + .1, T_L, 'grande');
D.falas.forEach((f, i) => { if (i) som(f.t - .05, 'whoosh'); }); som(0, 'crack'); som(.5, 'desaba'); for (let i = 0; i < 8; i++) som(.3 + i * .26, 'toc'); som(1.2, 'crack'); som(F(LAST) + .1, 'ding'); som(T_L, 'impact'); som(T_L + .05, 'zumbido'); for (let q = T_L + .6; q < D.total; q += 1.2) som(q, 'pop');

window.CAPA_T = T_L + 2.4;iniciar(t => { camTo(K, t); cam.updateMatrixWorld(); segueSol(0, 20); AUTO.forEach(f => f(t)); });
