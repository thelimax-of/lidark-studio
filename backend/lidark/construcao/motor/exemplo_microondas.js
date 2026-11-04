// Micro-ondas do zero, numa bancada de cozinha. Ondas em pulsos que quicam nas paredes; só atualiza o que muda.
const { THREE, renderer, scene, cam, luzes, mat, add, box, cil, esf, clamp, ease, back, prng, tex, camTo, iniciar, pal, fala, som, rotulo, D } = K3;

scene.background = new THREE.Color(0xf1e7d6); luzes(0xfff0dc, 0xffffff, 0xd9c4a4, 1.9, 9); scene.environmentIntensity = .3;
const rnd = prng(23), F = fala, fim = i => F(i) + D.falas[i].dur;
const azul = tex(256, 256, (g, w) => { g.fillStyle = '#e9e2d3'; g.fillRect(0, 0, w, w); g.fillStyle = '#d7efe9'; g.fillRect(4, 4, w / 2 - 8, w / 2 - 8); g.fillRect(w / 2 + 4, w / 2 + 4, w / 2 - 8, w / 2 - 8); g.fillStyle = '#f7f4ec'; g.fillRect(w / 2 + 4, 4, w / 2 - 8, w / 2 - 8); g.fillRect(4, w / 2 + 4, w / 2 - 8, w / 2 - 8); }, 10, 6);
const par = add(new THREE.Mesh(new THREE.PlaneGeometry(26, 15), new THREE.MeshStandardMaterial({ map: azul, roughness: .4 }))); par.position.set(0, 7.5, -2.4); par.receiveShadow = true;
const ban = add(new THREE.Mesh(new THREE.PlaneGeometry(26, 14), mat(0x9a6b47, { roughness: .45 }))); ban.rotation.x = -Math.PI / 2; ban.position.set(0, 0, 4.6); ban.receiveShadow = true;
[-6.5, 6.5].forEach(x => { add(box(4.6, 2.2, 1.4, 0x3f8f85, .05)).position.set(x, 6.4, -1.7); }); add(box(.7, 1.5, .7, 0xe8e2d4, .08)).position.set(-5.3, .75, -.9); add(box(.5, 1, .5, 0xd8683f, .08)).position.set(-4.4, .5, -1.2);
const jarra = add(cil(.45, .55, 1.3, 0xe8c64e, 24)); jarra.position.set(4.9, .65, -1.2);

const X0 = -1.7, X1 = 1.5, XM = .75, Y0 = .22, Y1 = 2.3, Z0 = -1.1, Z1 = 1.1, ESP = .1, GX = -.5, GY = .3;
const CX = (X0 + X1) / 2, LX = X1 - X0, LZ = Z1 - Z0, CY = (Y0 + Y1) / 2, LY = Y1 - Y0;
const pulo = x => { x = clamp(x); return 1 - Math.abs(Math.cos(x * Math.PI * 1.6)) * (1 - x) ** 1.4; };
const pecas = []; const chega = (o, t, dy = 1.8) => { pecas.push({ o, t, y: o.position.y, dy, s: o.scale.clone() }); return o; };

// base (sempre visível)
const METAL = () => mat(0x9aa3b0, { metalness: .15, roughness: .45 }), CAV = () => mat(0xdde1e6, { roughness: .55 });
const chao = add(box(LX, ESP, LZ, METAL(), .03)); chao.position.set(CX, Y0, 0); [[-1.5, .9], [1.3, .9], [-1.5, -.9], [1.3, -.9]].forEach(([x, z]) => add(cil(.09, .11, .17, 0x7d828c, 14)).position.set(x, .085, z));

const entra = g => chega(g, .12, 1.5);
// comida: anéis × fatias, com cor por posição
const prato = new THREE.Group(); prato.position.set(GX, GY, 0); add(prato);
add(cil(.86, .86, .05, 0xdfe8ee, 48, { roughness: .25 }), prato).position.y = .025; add(cil(.74, .68, .07, 0xfafafa, 48, { roughness: .35 }), prato).position.y = .085;
const NA = 24, NR = 6, cel = [], BASE = new THREE.Color(0xeec26a), QUENTE = new THREE.Color(0xe6401c), FRIO = new THREE.Color(0x3d8fe6);
for (let a = 0; a < NA; a++) for (let r = 0; r < NR; r++) { const g = new THREE.SphereGeometry(.62, 5, 3, a / NA * 6.2832, 6.2832 / NA + .01, r / NR * 1.5708, 1.5708 / NR + .01); const m = new THREE.Mesh(g, mat(BASE.getHex(), { roughness: .6 })); m.scale.y = .55; m.position.y = .12; m.castShadow = true; prato.add(m); cel.push({ m, a: (a + .5) / NA * 6.2832, r: (r + .5) / NR }); }
entra(prato);
for (let i = 0; i < 14; i++) { const a = rnd() * 6.28, r = .15 + rnd() * .4, m = add(esf(.05 + rnd() * .025, [0xc73a2e, 0x3f9a45, 0x8a4a2a][i % 3]), prato); m.position.set(Math.cos(a) * r, .12 + .341 * Math.sqrt(1 - (r / .62) ** 2), Math.sin(a) * r); m.scale.y = .45; }
const COR = new THREE.Color(); let cc = '';
const colore = (borda, meio, lado, unif) => { const ch = [borda, meio, lado, unif].map(v => v.toFixed(2)).join(); if (ch === cc) return; cc = ch; cel.forEach(c => { const e = c.r; COR.copy(BASE).lerp(QUENTE, clamp(unif + borda * ease(e * 1.5 - .2))).lerp(FRIO, meio * (1 - e) * (1 - e) * 1.8 > 1 ? 1 : meio * (1 - e) * (1 - e) * 1.8); const q = clamp(.5 - Math.cos(c.a) * 1.3); COR.lerp(FRIO, lado * q); c.m.material.color.copy(COR); }); };

// magnetron, transformador, capacitor, ventilador
const mag = new THREE.Group(); mag.position.set(1.12, Y0 + .1, 0); add(mag); const mMag = mat(0xd8833b, { roughness: .35, emissive: 0xff2000, emissiveIntensity: 0 }); add(cil(.27, .27, .9, mMag, 28), mag).position.y = .85; for (let i = 0; i < 7; i++) add(cil(.34, .34, .03, 0xf0d9a8, 28), mag).position.y = .52 + i * .11; add(box(.5, .22, .5, 0xcf3434, .05), mag).position.y = .2; add(box(.5, .16, .5, 0xcf3434, .05), mag).position.y = 1.4; const ant = add(cil(.05, .05, .36, 0xffc531, 12), mag); ant.rotation.z = Math.PI / 2; ant.position.set(-.33, 1.2, 0); chega(mag, pal('magnetron') - .1, 2.4);
const tra = new THREE.Group(); tra.position.set(1.12, Y0 + .05, -.72); add(tra); add(box(.56, .6, .5, 0x4c5563, .03), tra).position.y = .3; [-.16, .16].forEach(x => { const c = add(cil(.15, .15, .38, 0xc06a2b, 18), tra); c.position.set(x, .3, .26); c.rotation.x = Math.PI / 2; }); chega(tra, pal('transformador'), 2);
const cap = new THREE.Group(); cap.position.set(1.12, Y0 + .05, .78); add(cap); add(cil(.16, .16, .58, 0xdfe3e6, 20), cap).position.y = .29; add(cil(.05, .05, .1, 0xd9a93a, 8), cap).position.y = .62; chega(cap, pal('capacitor'), 2);
const tom = add(box(.5, .5, .08, 0xf4f1ea, .04)); tom.position.set(2.6, 1.6, -2.34); const liga_ = (a, b) => { const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), m = add(cil(.03, .03, A.distanceTo(B), 0x24262a, 8)); m.position.copy(A).add(B).multiplyScalar(.5); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), B.clone().sub(A).normalize()); }; liga_([2.6, 1.55, -2.3], [2.6, .04, -1.7]); liga_([2.6, .04, -1.7], [1.55, .04, -.8]); liga_([1.55, .04, -.8], [1.5, .3, -.8]);
const fan = new THREE.Group(); fan.position.set(1.12, 1.95, .62); add(fan); const anel = add(new THREE.Mesh(new THREE.TorusGeometry(.33, .04, 8, 28), mat(0x51596a)), fan); const rotor = new THREE.Group(); fan.add(rotor); for (let i = 0; i < 5; i++) { const b = add(box(.27, .1, .02, 0x8fa4bd, .008), rotor); b.position.set(Math.cos(i * 1.2566) * .17, Math.sin(i * 1.2566) * .17, 0); b.rotation.z = i * 1.2566; } fan.rotation.x = -.4; chega(fan, pal('ventilador'), 2);

// guia de ondas
const gui = add(box(.55, .42, .5, 0xc9ced6, .03)); gui.position.set(XM + .05, 1.52, 0); chega(gui, pal('canal') + .1, 1.6);
// cavidade
const pareds = [[add(box(LX, LY, ESP, CAV(), .03)), CX, CY, Z0], [add(box(ESP, LY, LZ, METAL(), .03)), X0, CY, 0], [add(box(ESP, LY, LZ, METAL(), .03)), X1, CY, 0], [add(box(LX + .06, ESP, LZ, METAL(), .03)), CX, Y1, 0], [add(box(ESP, LY, LZ, CAV(), .03)), XM, CY, 0]];
pareds.forEach(([m, x, y, z], i) => { m.position.set(x, y, z); chega(m, pal('caixa') + i * .17); });

// pulsos de micro-ondas com rastro
const N = 42, RAS = 4, pul = new THREE.InstancedMesh(new THREE.SphereGeometry(.055, 8, 6), new THREE.MeshBasicMaterial({ color: 0xffb21f, toneMapped: false }), N * RAS); pul.frustumCulled = false; add(pul); const P = new THREE.Object3D(), pv = []; for (let i = 0; i < N; i++) pv.push([rnd(), rnd(), rnd(), .3 + rnd() * .25, .22 + rnd() * .2, .18 + rnd() * .2]);
const tri = (v, a, b) => { const u = ((v % 2) + 2) % 2; return a + (b - a) * (u < 1 ? u : 2 - u); };
const fug = new THREE.InstancedMesh(new THREE.SphereGeometry(.06, 8, 6), new THREE.MeshBasicMaterial({ color: 0xff3d2e, toneMapped: false }), 30); fug.frustumCulled = false; add(fug); const fv = []; for (let i = 0; i < 30; i++) fv.push([-1.5 + rnd() * 2, .5 + rnd() * 1.6, rnd(), .35 + rnd() * .25]);
const ondaLivre = new THREE.InstancedMesh(new THREE.TorusGeometry(.32, .022, 8, 26, Math.PI), new THREE.MeshBasicMaterial({ color: 0xffb21f, toneMapped: false }), 8); ondaLivre.frustumCulled = false; add(ondaLivre);

// moléculas e vapor
const agua = []; for (let i = 0; i < 11; i++) { const g = new THREE.Group(); add(esf(.1, 0xe2453a), g);[-1, 1].forEach(s => add(esf(.058, 0xffffff), g).position.set(s * .1, .07, 0)); const a = i / 11 * 6.2832 + rnd(), r = .2 + rnd() * .38; g.userData = { b: new THREE.Vector3(GX + Math.cos(a) * r, GY + .32 + rnd() * .34, Math.sin(a) * r + .15), f: 24 + rnd() * 14, p: rnd() * 6 }; g.visible = false; add(g); agua.push(g); }
const vapM = () => new THREE.MeshStandardMaterial({ color: 0xffffff, transparent: true, opacity: .7 }), vapor = []; for (let i = 0; i < 12; i++) { const m = add(new THREE.Mesh(new THREE.SphereGeometry(.09, 10, 8), vapM())); m.userData = { x: GX + (rnd() - .5) * .9, z: (rnd() - .5) * .8, p: rnd() }; m.visible = false; vapor.push(m); }

// porta
const porta = new THREE.Group(); porta.position.set(X0, CY, Z1 + .03); add(porta); const PW = XM - X0 + .08, PH = LY + .1;
const ba = (w, h, x, y) => add(box(w, h, .1, mat(0xaab2bd, { roughness: .4 }), .03), porta).position.set(x, y, 0); ba(.2, PH, .1, 0); ba(.2, PH, PW - .1, 0); ba(PW, .2, PW / 2, PH / 2 - .1); ba(PW, .2, PW / 2, -PH / 2 + .1); add(box(.08, 1.1, .14, 0xf4f4f4, .03), porta).position.set(PW - .1, 0, .1);
const vM = new THREE.MeshStandardMaterial({ color: 0xbfe6f5, transparent: true, opacity: .2, roughness: .1 }); add(new THREE.Mesh(new THREE.PlaneGeometry(PW - .36, PH - .36), vM), porta).position.set(PW / 2, 0, 0);
const furos = tex(512, 512, (g, w) => { g.fillStyle = '#6b7482'; g.fillRect(0, 0, w, w); g.globalCompositeOperation = 'destination-out'; for (let y = 0; y < 15; y++) for (let x = 0; x < 15; x++) { g.beginPath(); g.arc((x + .5 + (y % 2) * .5) * 34, (y + .5) * 34, 11.5, 0, 7); g.fill(); } }, 2.2, 2.6);
const tela = add(new THREE.Mesh(new THREE.PlaneGeometry(PW - .36, PH - .36), new THREE.MeshStandardMaterial({ map: furos, transparent: true, alphaTest: .35, side: THREE.DoubleSide, roughness: .5 })), porta); tela.position.set(PW / 2, 0, .02);
// travas
const trM = new THREE.MeshBasicMaterial({ color: 0xff3030, toneMapped: false }); const trs = [.45, -.45].map(d => { const m = add(new THREE.Mesh(new THREE.BoxGeometry(.13, .24, .22), trM)); m.position.set(XM - .02, CY + d, Z1 - .06); return m; });
// painel
const painel = new THREE.Group(); painel.position.set((XM + X1) / 2 + .04, CY, Z1 + .03); add(painel); add(box(X1 - XM + .02, PH, .08, mat(0x9aa3b0, { roughness: .45 }), .03), painel);
const vc = document.createElement('canvas'); vc.width = 256; vc.height = 96; const vg = vc.getContext('2d'), vt = new THREE.CanvasTexture(vc); vt.colorSpace = THREE.SRGBColorSpace; let vu = '';
const visor = s => { if (s === vu) return; vu = s; vg.fillStyle = '#123f3a'; vg.fillRect(0, 0, 256, 96); vg.fillStyle = '#7dffb2'; vg.font = '800 62px Arial'; vg.textAlign = 'center'; vg.fillText(s, 128, 70); vt.needsUpdate = true; }; add(new THREE.Mesh(new THREE.PlaneGeometry(.58, .22), new THREE.MeshBasicMaterial({ map: vt, toneMapped: false })), painel).position.set(0, .68, .05);
for (let i = 0; i < 12; i++) add(box(.13, .1, .04, 0xf2f2f2, .015), painel).position.set(-.19 + (i % 3) * .19, .36 - Math.floor(i / 3) * .17, .05); add(box(.48, .14, .04, 0x3caa55, .02), painel).position.set(0, -.5, .05);
const luz = new THREE.PointLight(0xffe2a8, 0, 2.2); luz.position.set(-.5, 2, .3); add(luz);

const T = { mag: pal('magnetron'), onda: pal('ondas') - .3, guia: pal('canal'), caixa: pal('caixa'), rico: pal('ricocheteiam'), bal: pal('moléculas'), porta: F(7), tela: pal('tela'), abre: F(8), trava: pal('travas'), frio: F(9), prato: pal('prato'), pain: pal('painel'), fim: F(11) };
const VIS = [[[1.2, 2.8, 8.4], [-.2, .6, 0], 34], [[2.7, 3.3, 11.2], [.2, .9, 0], 34], [[5.2, 3.7, 7], [1.1, .85, 0], 34], [[4.6, 3.6, 6.4], [1.1, 1.25, .2], 34], [[3.7, 3.5, 8.2], [.5, 1.4, 0], 34], [[-.4, 2.8, 10.8], [-.1, 1.2, 0], 34], [[-.15, 1.8, 3.7], [-.5, .42, .1], 36], [[6.2, 3.4, 10.8], [.9, 1.1, 1.4], 34], [[-3.6, 3, 9.8], [-.2, 1.3, 1], 34], [[-.3, 2.3, 3.95], [-.5, .25, .1], 34], [[3.1, 2.7, 7.2], [1.1, 1.3, 1], 34], [[3.1, 3.1, 11.8], [0, 1.2, 0], 34]];
const K = []; VIS.forEach(([p, l, f], i) => { if (i) K.push({ t: F(i) + .05, p: VIS[i - 1][0].map((v, j) => v * .97 + (j === 2 ? 0 : .08)), l: VIS[i - 1][1], f: VIS[i - 1][2] }); K.push({ t: F(i) + (i ? .85 : 0), p, l, f }); }); K.push({ t: D.total + 1, p: [2.2, 2.9, 11.2], l: [0, 1.2, 0], f: 34 });

// rótulos
const LAB = [['MAGNETRON', [1.12, 2.3, 0], T.mag, fim(1), 'ouro'], ['TRANSFORMADOR', [1.12, 1.1, -.9], pal('transformador'), pal('capacitor'), 'pilula'], ['CAPACITOR', [1.12, 1.2, .8], pal('capacitor'), fim(2), 'pilula'], ['VENTILADOR', [1.12, 2.65, .6], pal('ventilador'), fim(3), 'ouro'], ['GUIA DE ONDAS', [.75, 2.45, 0], pal('guia'), fim(4), 'ouro'], ['CAVIDADE', [-.5, 3.1, 0], pal('cavidade'), fim(5), 'ouro'], ['ÁGUA', [-.5, 1.25, .1], T.bal, pal('calor') - .1, 'pilula'], ['CALOR', [-.5, 1.3, .1], pal('calor'), fim(6), 'ouro'], ['ONDAS ESCAPANDO', [1, 3, 2.4], T.porta + .5, T.tela, 'ruim'], ['TELA DE METAL', [-.5, 3, 1.1], T.tela, pal('blindagem'), 'pilula'], ['BLINDAGEM', [-.5, 3.1, 1.1], pal('blindagem'), fim(7), 'ouro'], ['ENERGIA CORTADA', [-.1, 3, 1], T.trava + .4, fim(8), 'ruim'], ['TRAVAS', [.75, 2.8, 1.1], T.trava, T.trava + 1.2, 'ouro'], ['PONTOS FRIOS', [-.1, 1.15, .1], pal('frios') - .2, T.prato - .15, 'ruim'], ['PRATO GIRATÓRIO', [-.5, 1.15, .1], T.prato, fim(9), 'ouro'], ['PAINEL', [1.1, 2.9, 1.1], T.pain, pal('tempo'), 'ouro'], ['LIGA E DESLIGA', [1.1, 2.9, 1.1], pal('potência'), fim(10), 'pilula']];
LAB.forEach(l => rotulo(...l));
{ rotulo('SEM FOGO', [-.5, 1.4, 0], pal('sem'), pal('invisíveis') + .3, 'ruim'); const e2 = rotulo('MILHARES DE VOLTS', [540, 330], pal('milhares'), pal('Então'), 'grande'); e2.style.cssText += ';font-size:76px;color:#ff5a4f'; }
rotulo('MICRO-ONDAS PRONTO!', [540, 300], T.fim + .3, D.total + 1, 'grande').style.fontSize = '76px';

// sons
const s_ = (t, k) => som(t, k); D.falas.forEach((f, i) => { if (i) s_(f.t - .05, 'whoosh'); }); s_(.12, 'whoosh'); s_(.35, 'tijolo'); s_(.6, 'toc');
['magnetron', 'transformador', 'capacitor', 'ventilador', 'canal', 'cavidade', 'blindagem', 'travas', 'prato', 'painel'].forEach(w => s_(pal(w), 'ding'));
[T.mag - .1, pal('transformador'), pal('capacitor'), pal('ventilador'), T.guia + .1].forEach(q => { s_(q + .2, 'tijolo'); s_(q + .42, 'toc'); }); pareds.forEach((_, i) => s_(T.caixa + i * .17 + .22, 'tijolo'));
for (let q = pal('ventilador'); q < fim(3); q += 1.1) s_(q, 'motor'); for (let q = T.rico; q < fim(5); q += 1) s_(q, 'zumbido'); for (let q = T.bal; q < fim(6); q += 1) s_(q, 'zumbido'); s_(T.bal, 'riser'); for (let q = F(7); q < T.tela; q += 1) s_(q, 'zumbido'); s_(T.tela, 'impact'); s_(T.abre + .3, 'toc'); s_(T.trava + .4, 'impact'); for (let q = T.prato; q < fim(9); q += 1) s_(q, 'zumbido');
for (let i = 0; i < 4; i++) s_(T.pain + .2 + i * .22, 'pop'); s_(pal('liga') , 'toc'); s_(pal('desliga'), 'toc'); s_(T.fim + .2, 'ding'); s_(T.fim + .55, 'ding'); s_(pal('faísca'), 'crack');

window.__foto = (p_, l_, f_) => { renderer.setSize(1920, 1080); cam.aspect = 16 / 9; cam.position.set(...p_); cam.lookAt(...l_); cam.fov = f_; cam.updateProjectionMatrix(); cam.updateMatrixWorld(); };
const liga = [[T.rico, T.abre + .35], [T.frio, fim(9)], [T.fim + .2, T.fim + 1.2]], onM = t => liga.some(([a, b]) => t > a && t < b);
iniciar(t => {
  camTo(K, t); cam.updateMatrixWorld();
  for (const p of pecas) { const k = (t - p.t) / .55, on = k > 0; p.o.visible = on; if (!on || k > 1.05) { if (on) { p.o.position.y = p.y; p.o.scale.copy(p.s); } continue; } p.o.position.y = p.y + (1 - pulo(k)) * p.dy; p.o.scale.copy(p.s).multiplyScalar(.6 + .4 * back(k)); }
  // gancho: quente fora, frio dentro; depois a comida volta ao normal, esquenta e iguala
  const gancho = 0, quente = ease((t - T.bal) / 3) * (1 - ease((t - T.frio) / .4)) * .75, lado = ease((t - T.frio - .7) / .8) * (1 - ease((t - T.prato - .4) / 2.4)), unif = ease((t - T.prato) / 2.6) * .7 + quente;
  colore(gancho, gancho, lado, t > T.frio ? clamp(.6 * (1 - ease((t - T.frio) / .8)) + unif) : unif);
  prato.rotation.y = Math.max(0, t - T.prato) * 2.1 * ease((t - T.prato) / .5) + (t > T.pain ? 0 : 0);
  // ondas soltas, antes da caixa
  const lv = t > T.onda + .3 && t < T.caixa; ondaLivre.visible = lv; if (lv) { for (let i = 0; i < 8; i++) { const u = ((t * .55 + i / 8) % 1), x = .75 - u * 1.9; P.position.set(x, 1.5 - (u > .6 ? (u - .6) * 1.4 : 0), 0); P.rotation.set(0, Math.PI / 2, Math.PI / 2); P.scale.setScalar(.8 + u * 1.3); P.updateMatrix(); ondaLivre.setMatrixAt(i, P.matrix); } ondaLivre.instanceMatrix.needsUpdate = true; }
  // pulsos quicando na cavidade
  const on = onM(t); pul.visible = on; if (on) { P.rotation.set(0, 0, 0); pv.forEach(([a, b, c, vx, vy, vz], i) => { for (let k = 0; k < RAS; k++) { const q = t - k * .035; P.position.set(tri(a * 2 + q * vx * 3, X0 + .12, XM - .12), tri(b * 2 + q * vy * 3, Y0 + .14, Y1 - .12), tri(c * 2 + q * vz * 3, Z0 + .12, Z1 - .1)); P.scale.setScalar(1 - k * .2); P.updateMatrix(); pul.setMatrixAt(i * RAS + k, P.matrix); } }); pul.instanceMatrix.needsUpdate = true; }
  // vazamento pela porta
  const vaz = t > T.porta + .4 && t < T.tela + .9; fug.visible = vaz; if (vaz) { P.rotation.set(0, 0, 0); fv.forEach(([x, y, p, v], i) => { const z0 = ((t * v * 2 + p) % 1) * 4.2 + Z1, z = t < T.tela ? z0 : Math.min(z0, Z1 + 3 * (1 - ease((t - T.tela) / .8))); P.position.set(x, y, t < T.tela ? z : Z1 + (z0 - Z1) * (1 - ease((t - T.tela) / .7))); P.scale.setScalar(t < T.tela ? 1 : 1 - ease((t - T.tela) / .8) * .99); P.updateMatrix(); fug.setMatrixAt(i, P.matrix); }); fug.instanceMatrix.needsUpdate = true; }
  // magnetron e ventilador
  mMag.emissiveIntensity = .9 * ease((t - F(3)) / .8) * (1 - ease((t - pal('sopra')) / 1.6)); rotor.rotation.z = -Math.max(0, t - pal('ventilador')) * 15;
  fan.visible = fan.visible && t < T.fim + 99;
  // moléculas, vapor
  const mOn = t > T.bal - .1 && t < fim(6) + .1; agua.forEach(g => { g.visible = mOn; if (!mOn) return; const d = g.userData, e = .03 + ease((t - T.bal) / 2.5) * .05; g.position.copy(d.b); g.position.x += Math.sin(t * d.f + d.p) * e; g.position.y += Math.cos(t * d.f * 1.3 + d.p) * e; g.rotation.set(Math.sin(t * d.f) * 1.2, t * d.f * .5, Math.cos(t * d.f * .8) * 1.2); g.scale.setScalar(back((t - T.bal) / .25)); });
  const vOn = t > pal('calor') - .4 && t < fim(6) + .4 || t > T.prato + 1.2 && t < fim(9); vapor.forEach((m, i) => { m.visible = vOn; if (!vOn) return; const d = m.userData, c = ((t * .42 + d.p) % 1); m.position.set(d.x + Math.sin(t + i) * .06, GY + .45 + c * 1.1, d.z); m.scale.setScalar(.7 + c * 1.5); m.material.opacity = .7 * (1 - c); });
  // porta: entra fechando; abre na trava; some no zoom do prato; fecha no fim
  const ab = -2.1, ang = ab * (1 - ease((t - T.porta + .1) / .45)) + ab * ease((t - T.abre - .2) / .5) * (1 - ease((t - T.frio + .1) / .4)); porta.rotation.y = -ang * -1; porta.visible = t > T.porta - .15 && !(t > T.frio + .2 && t < T.pain - .4);
  tela.visible = t > T.tela; if (tela.visible) { const k = back((t - T.tela) / .4); tela.scale.set(Math.max(k, .01), Math.max(k, .01), 1); }
  const trOn = t > T.trava - .1 && t < fim(8) + .3; trs.forEach((m, i) => { m.visible = trOn; if (trOn) m.scale.setScalar(1 + Math.max(0, Math.sin(t * 9)) * .25); });
  painel.visible = t > T.pain - .1; if (painel.visible) { const k = back((t - T.pain + .1) / .4); painel.scale.setScalar(Math.max(k, .01)); const seg = Math.max(0, 90 - Math.floor(Math.max(0, t - pal('tempo')) * 14)); visor(t < pal('tempo') ? '00:00' : `0${Math.floor(seg / 60)}:${String(seg % 60).padStart(2, '0')}`); }
  const lz = t > T.fim ? ease((t - T.fim) / .4) : t > T.pain ? (Math.sin((t - T.pain) * 7) > 0 ? .7 : 0) : 0; luz.intensity = lz * 3; vM.color.lerpColors(new THREE.Color(0xbfe6f5), new THREE.Color(0xffc75a), lz); vM.opacity = .2 + lz * .35;
});
