// Base comum das cenas 3D. frame(t) é determinístico. Sem GTAO: ele causa blocos pretos.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
export { THREE, RoundedBoxGeometry };
export const W = 1080, H = 1920;
export const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
renderer.setSize(W, H); renderer.setPixelRatio(1);
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
document.getElementById('c').appendChild(renderer.domElement);
export const scene = new THREE.Scene();
export const cam = new THREE.PerspectiveCamera(38, W / H, 0.1, 800);
const pm = new THREE.PMREMGenerator(renderer);
scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture; scene.environmentIntensity = 0.35;

// tempo da narração --------------------------------------------------------
export const D = window.DADOS;   // {falas:[{t,dur,texto,words:[{w,start,end}]}], total, destaque:[...]}
const norm = s => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '');
const PAL = D.falas.flatMap(f => f.words);
/** instante (s) em que a n-ésima ocorrência da palavra é dita */
export function pal(w, n = 0) { const k = norm(w), a = PAL.filter(p => norm(p.w) === k); if (!a[n]) throw new Error('palavra fora do roteiro: ' + w); return a[n].start; }
/** início da fala i, mais fração da duração */
export const fala = (i, f = 0) => D.falas[i].t + D.falas[i].dur * f;
export const falando = (t, i) => t >= D.falas[i].t && t <= D.falas[i].t + D.falas[i].dur;
/** efeitos sonoros: k = whoosh | impact | ding | riser */
export const SONS = window.SONS = []; export const som = (t, k = 'whoosh') => SONS.push({ t, k });

// rótulos em HTML presos a um ponto 3D ---------------------------------------
const hud = document.getElementById('hud'), V = new THREE.Vector3(), rot = [];
/** estilo: 'pilula' (branca) | 'ouro' (amarelo grande) | 'ruim' (vermelho) | 'grande' (fixo; pos=[px,py]) */
export function rotulo(texto, pos, t0, t1, estilo = 'pilula') { const e = document.createElement('div'); e.className = 'r ' + estilo; e.textContent = texto; hud.appendChild(e); rot.push({ e, pos, t0, t1, estilo }); return e; }
function hudFrame(t) {
  for (const r of rot) {
    const on = t >= r.t0 && t <= r.t1; r.e.style.display = on ? 'block' : 'none'; if (!on) continue;
    const k = back((t - r.t0) / .22);
    if (r.estilo === 'grande') { r.e.style.left = (r.pos[0] ?? 540) + 'px'; r.e.style.top = (r.pos[1] ?? 500) + 'px'; }
    else { V.set(...r.pos).project(cam); r.e.style.left = (V.x * .5 + .5) * W + 'px'; r.e.style.top = (-V.y * .5 + .5) * H + 'px'; }
    r.e.style.transform = `translate(-50%,-50%) scale(${Math.max(k, .01)})`;
  }
}
const leg = document.getElementById('leg'), DEST = new Set(D.destaque.map(norm));
function legenda(t) {
  let w = null; for (const p of PAL) { if (t >= p.start - .03) w = p; else break; }
  const ativo = w && t <= w.end + .35; leg.style.display = ativo ? 'block' : 'none';
  if (ativo) { leg.textContent = w.w.replace(/[.,!?;:]+$/, ''); leg.style.color = DEST.has(norm(w.w)) ? '#ffd23f' : '#fff'; const k = .86 + .14 * ease((t - w.start) / .08); leg.style.transform = `translate(-50%,-50%) scale(${k})`; }
}
/** registra a cena: att(t) é chamado a cada quadro */
export function iniciar(att) {
  window.frame = t => { att(t); hudFrame(t); legenda(t); renderer.render(scene, cam); };
  window.__render = () => renderer.render(scene, cam); window.info = () => ({ calls: renderer.info.render.calls, tris: renderer.info.render.triangles });
  window.pronto = true;
}

// utilidades -------------------------------------------------------------
export const mat = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.75, ...o });
export const add = (m, p = scene) => (p.add(m), m);
export const sh = m => (m.traverse(o => { if (o.isMesh) { o.castShadow = o.receiveShadow = true; } }), m);
export function box(w, h, d, c, r = 0.04, o) { return sh(new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2.1, h / 2.1, d / 2.1)), typeof c === 'object' ? c : mat(c, o))); }
export const cil = (a, b, h, c, n = 24, o) => sh(new THREE.Mesh(new THREE.CylinderGeometry(a, b, h, n), typeof c === 'object' ? c : mat(c, o)));
export const esf = (r, c, o) => sh(new THREE.Mesh(new THREE.SphereGeometry(r, 32, 24), typeof c === 'object' ? c : mat(c, o)));
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const ease = x => { x = clamp(x); return x * x * (3 - 2 * x); };
export const back = x => { x = clamp(x); const c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2; };
export const prng = s => () => (s = (s * 16807) % 2147483647) / 2147483647;
export function luzes(sol = 0xfff1dc, ceu = 0xbfe0ff, chao = 0x8d9a7a, I = 2.6, area = 30) {
  add(new THREE.HemisphereLight(ceu, chao, 1.25));
  const d = add(new THREE.DirectionalLight(sol, I)); d.position.set(area * .6, area, area * .55);
  d.castShadow = true; d.shadow.mapSize.set(4096, 4096); d.shadow.bias = -0.0002; d.shadow.normalBias = 0.03; d.shadow.radius = 5;
  Object.assign(d.shadow.camera, { left: -area, right: area, top: area, bottom: -area, near: 1, far: area * 4 });
  return d;
}
export function ceu(a = '#3e8ddd', b = '#d9eefb') {
  const c = document.createElement('canvas'); c.width = 8; c.height = 512; const g = c.getContext('2d');
  const l = g.createLinearGradient(0, 0, 0, 512); l.addColorStop(0, a); l.addColorStop(.75, b); g.fillStyle = l; g.fillRect(0, 0, 8, 512);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; scene.background = t;
}
export function tex(w, h, fn, rx = 1, ry = 1) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; fn(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 16;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rx, ry); return t;
}
export function placa(w, h, fn, r = 512) { const t = tex(r, Math.round(r * h / w), fn); return sh(new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: t, roughness: .85 }))); }
export function arvore(rnd, s = 1, pinho = false) {
  const g = new THREE.Group(); const t = add(cil(.08 * s, .13 * s, .9 * s, 0x6b4a2c, 7), g); t.position.y = .45 * s;
  const v = [0x2e8f3e, 0x3aa84a, 0x237a35][Math.floor(rnd() * 3)];
  if (pinho) for (let i = 0; i < 3; i++) { const c = add(sh(new THREE.Mesh(new THREE.ConeGeometry((.7 - i * .17) * s, .9 * s, 7), mat(v, { flatShading: true }))), g); c.position.y = (.95 + i * .5) * s; }
  else for (let i = 0; i < 3; i++) { const c = add(sh(new THREE.Mesh(new THREE.IcosahedronGeometry((.5 + rnd() * .2) * s, 0), mat(v, { flatShading: true }))), g); c.position.set((rnd() - .5) * .5 * s, (1.05 + rnd() * .4) * s, (rnd() - .5) * .5 * s); }
  return g;
}

// boneco articulado ------------------------------------------------------
export function boneco(o) {
  const c = { pele: 0xd9a57c, camisa: 0x3fae85, calca: 0x262c40, sapato: 0xeeeeee, cabelo: 0x3a2a1e, cabeca: 'bloco', altura: 1, bone: false, oculos: false, chapeu: false, ...o };
  const raiz = new THREE.Group(), r = {}, tronco = new THREE.Group(); raiz.add(tronco); tronco.position.y = .95;
  const cart = c.cabeca === 'cartoon';
  if (cart) { const t = add(esf(.3, c.camisa), tronco); t.scale.set(1, 1.25, .78); t.position.y = .28; }
  else add(box(.5, .62, .28, c.camisa, .06), tronco).position.y = .3;
  const cab = new THREE.Group(); cab.position.y = cart ? .72 : .8; tronco.add(cab); r.cab = cab;
  if (cart) {
    add(esf(.36, c.pele), cab).scale.set(1, .95, .95);
    const cab2 = add(esf(.365, c.cabelo), cab); cab2.scale.set(1.02, .75, 1); cab2.position.set(0, .12, -.05);
    [-1, 1].forEach(s => {
      const e = add(esf(.058, 0xffffff), cab); e.position.set(s * .13, .03, .33); e.scale.z = .5;
      const p = add(esf(.034, 0x111111), cab); p.position.set(s * .13, .03, .362); p.scale.z = .5;
      const b = add(esf(.05, 0xee8877), cab); b.position.set(s * .21, -.1, .29); b.scale.set(1.2, .7, .3); b.material.transparent = true; b.material.opacity = .55;
      const br = add(box(.11, .02, .02, 0x332211, .01), cab); br.position.set(s * .13, .14, .345); br.rotation.z = -s * .1;
      if (c.oculos) { const a = add(new THREE.Mesh(new THREE.TorusGeometry(.085, .012, 8, 28), mat(0x111111)), cab); a.position.set(s * .13, .03, .35); }
    });
    add(esf(.035, 0xd98a6a), cab).position.set(0, -.04, .36);
  } else {
    add(box(.42, .42, .4, c.pele, .05), cab).position.y = .06;
    add(box(.45, .16, .43, c.cabelo, .04), cab).position.set(0, .22, -.02);
    [-1, 1].forEach(s => {
      add(esf(.05, 0xffffff), cab).position.set(s * .1, .08, .2);
      add(esf(.027, 0x111111), cab).position.set(s * .1, .08, .243);
      add(box(.09, .018, .02, 0x332211, .008), cab).position.set(s * .1, .15, .205);
    });
  }
  const boca = add(box(.09, .018, .02, 0x7a3030, .008), cab); boca.position.set(0, cart ? -.14 : -.05, cart ? .33 : .205); r.boca = boca;
  if (c.bone) { add(box(.47, .13, .45, 0x232a4a, .05), cab).position.y = .33; add(box(.3, .03, .22, 0x232a4a, .012), cab).position.set(0, .28, .3); }
  if (c.chapeu) { const h = add(cil(.3, .27, .22, 0xffffff), cab); h.position.y = .32; }
  const membro = (x, y, cor, cor2, comp, g) => {
    const j = new THREE.Group(); j.position.set(x, y, 0); tronco.add(j);
    add(cil(g, g * .85, comp / 2, cor, 14), j).position.y = -comp / 4;
    const k = new THREE.Group(); k.position.y = -comp / 2; j.add(k);
    add(cil(g * .85, g * .75, comp / 2, cor2, 14), k).position.y = -comp / 4;
    return { j, k };
  };
  r.be = membro(-.32, .52, c.camisa, c.pele, .68, .075); r.bd = membro(.32, .52, c.camisa, c.pele, .68, .075);
  r.pe = membro(-.14, 0, c.calca, c.calca, .9, .1); r.pd = membro(.14, 0, c.calca, c.calca, .9, .1);
  [r.pe, r.pd].forEach(l => add(box(.17, .1, .3, c.sapato, .04), l.k).position.set(0, -.46, .06));
  r.anda = (t, f = 1) => { const a = Math.sin(t * 8) * .55 * f, b = Math.abs(Math.sin(t * 8)) * .03 * f;
    r.pe.j.rotation.x = a; r.pd.j.rotation.x = -a; r.pe.k.rotation.x = Math.max(0, -Math.sin(t * 8 + .6)) * .8 * f; r.pd.k.rotation.x = Math.max(0, Math.sin(t * 8 + .6)) * .8 * f;
    r.be.j.rotation.x = -a * .8; r.bd.j.rotation.x = a * .8; tronco.position.y = .95 + b; };
  r.fala = (t, on) => { boca.scale.y = on ? 1 + Math.abs(Math.sin(t * 17)) * 4 : 1; };
  r.respira = t => { tronco.scale.y = 1 + Math.sin(t * 2) * .006; cab.rotation.y = Math.sin(t * .9) * .05; };
  raiz.r = r; raiz.scale.setScalar(c.altura); return raiz;
}
export const camTo = (kf, t) => {
  let i = 0; while (i < kf.length - 2 && t > kf[i + 1].t) i++;
  const a = kf[i], b = kf[i + 1], k = ease((t - a.t) / (b.t - a.t));
  cam.position.lerpVectors(new THREE.Vector3(...a.p), new THREE.Vector3(...b.p), k);
  const L_ = new THREE.Vector3(...a.l).lerp(new THREE.Vector3(...b.l), k); cam.position.sub(L_).multiplyScalar(window.ZOOM || 1).add(L_); if (cam.position.y < .35) cam.position.y = .35; cam.lookAt(L_);
  cam.position.x += Math.sin(t * .7) * .012; cam.fov = (a.f || 38) + ((b.f || 38) - (a.f || 38)) * k; cam.updateProjectionMatrix();
};

