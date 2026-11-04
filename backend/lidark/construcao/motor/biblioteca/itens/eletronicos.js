// Eletrodomésticos e eletrônicos genéricos, em metros reais. Nomes com prefixo ele_ para não colidir com outras categorias.
// Portas: pivô na dobradiça; g.porta.userData.abre traz o ângulo de abertura (aplicar em rotation.y ou rotation.x, conforme userData.eixo).
(() => { const { THREE, mat, add, sh } = K3, { PI, G, B, C, CZ, CX, luz, vidro, metal, VD } = PC.H;
  const DK = (c, k = .8) => new THREE.Color(c).multiplyScalar(k).getHex();
  const PR = 0x24272e, PR2 = 0x15181d, CZA = 0x5a6068, INOX = 0xc6ccd2, BR = 0xf1f2ef;
  const VIDRO = { transparent: true, opacity: .32, roughness: .08, metalness: .1, side: 2 };

  // peças leves: B do kit gasta 588 triângulos e E gasta 1.000; estas gastam 108 e cerca de 200
  const _mc = new Map(), _gc = new Map();
  const cm = (c, o) => { if (typeof c === 'object') return c; if (o) return mat(c, o); if (!_mc.has(c)) _mc.set(c, mat(c)); return _mc.get(c); };
  const ms = (g, geo, c, x, y, z, o) => { const m = add(sh(new THREE.Mesh(geo, cm(c, o))), g); m.position.set(x, y, z); return m; };
  const geoRB = (w, h, d, r) => { r = Math.min(r, w / 2.1, h / 2.1, d / 2.1); const k = [w, h, d, r].map(v => v.toFixed(4)).join(); if (_gc.has(k)) return _gc.get(k); const b = new THREE.BoxGeometry(w, h, d, 3, 3, 3), p = b.attributes.position, n = b.attributes.normal, ax = [w / 2, h / 2, d / 2], v = new THREE.Vector3(); for (let i = 0; i < p.count; i++) { const q = [p.getX(i), p.getY(i), p.getZ(i)].map((a, e) => { const fora = Math.abs(a) > ax[e] * .9; return { s: Math.sign(a), fora }; }); v.set(q[0].fora ? q[0].s : 0, q[1].fora ? q[1].s : 0, q[2].fora ? q[2].s : 0).normalize(); p.setXYZ(i, q[0].s * (ax[0] - r) + v.x * r, q[1].s * (ax[1] - r) + v.y * r, q[2].s * (ax[2] - r) + v.z * r); n.setXYZ(i, v.x, v.y, v.z); } _gc.set(k, b); return b; };
  const RB = (g, w, h, d, c, x = 0, y = 0, z = 0, r = .01, o) => ms(g, geoRB(w, h, d, r), c, x, y, z, o);
  const PL = (g, w, h, d, c, x = 0, y = 0, z = 0, o) => ms(g, new THREE.BoxGeometry(w, h, d), c, x, y, z, o);
  const ES = (g, r, c, x = 0, y = 0, z = 0, sx = 1, sy = 1, sz = 1, o, a = 12, b = 8) => { const m = ms(g, new THREE.SphereGeometry(r, a, b), c, x, y, z, o); m.scale.set(sx, sy, sz); return m; };
  const TL = (g, r, tb, c, x = 0, y = 0, z = 0, arco = PI * 2, o, a = 5, b = 18) => ms(g, new THREE.TorusGeometry(r, tb, a, b, arco), c, x, y, z, o);
  const TB = (g, pts, r, c, o, a = 6) => ms(g, new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(q => new THREE.Vector3(...q))), Math.max(6, pts.length * 3), r, a), c, 0, 0, 0, o);
  const LA = (g, pts, c, x = 0, y = 0, z = 0, n = 18, o) => ms(g, new THREE.LatheGeometry(pts.map(([a, b]) => new THREE.Vector2(a, b)), n), c, x, y, z, { side: 2, ...(o || {}) });
  const TE = (g, w, h, c, x = 0, y = 0, z = 0, ry = 0) => { const m = add(new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: c, toneMapped: false })), g); m.position.set(x, y, z); m.rotation.y = ry; return m; };
  const BTN = (g, r, h, c, x, y, z, n = 12, o) => { const m = CZ(g, r, h, c, x, y, z, n, o); return m; };
  const _d = new THREE.Object3D();
  const IM = (g, geo, c, n, fn, o) => { const m = new THREE.InstancedMesh(geo, cm(c, o), n); for (let i = 0; i < n; i++) { _d.position.set(0, 0, 0); _d.rotation.set(0, 0, 0); _d.scale.set(1, 1, 1); const cor = fn(i, _d); _d.updateMatrix(); m.setMatrixAt(i, _d.matrix); if (cor != null) m.setColorAt(i, new THREE.Color(cor)); } m.instanceMatrix.needsUpdate = true; m.castShadow = m.receiveShadow = true; m.frustumCulled = false; return add(m, g); };
  const CUBO = new THREE.BoxGeometry(1, 1, 1);
  // caixa aberta na frente: casca colorida e forro interno
  const oca = (g, w, h, d, e, c, ci, x = 0, y = 0, z = 0) => { RB(g, w, e, d, c, x, y + h / 2 - e / 2, z, e / 2.2); RB(g, w, e, d, c, x, y - h / 2 + e / 2, z, e / 2.2); [-1, 1].forEach(s => { RB(g, e, h, d, c, x + s * (w / 2 - e / 2), y, z, e / 2.2); PL(g, .002, h - 2 * e, d - e, ci, x + s * (w / 2 - e - .001), y, z - e / 2); PL(g, w - 2 * e, .002, d - e, ci, x, y + s * (h / 2 - e - .001), z - e / 2); }); RB(g, w, h, e, c, x, y, z - d / 2 + e / 2, e / 2.2); PL(g, w - 2 * e, h - 2 * e, .002, ci, x, y, z - d / 2 + e + .001); };
  const pes = (g, lista, r, h, c = PR, n = 10) => lista.forEach(([x, z]) => C(g, r, r * .85, h, c, x, h / 2, z, n));
  const qd = (a, b) => [[-a, -b], [a, -b], [-a, b], [a, b]];
  const chapaFuro = (g, w, h, r, esp, c, x, y, z, cy = 0) => { const f = new THREE.Shape(); f.moveTo(-w / 2, -h / 2); f.lineTo(w / 2, -h / 2); f.lineTo(w / 2, h / 2); f.lineTo(-w / 2, h / 2); f.closePath(); const fu = new THREE.Path(); fu.absarc(0, cy, r, 0, PI * 2, true); f.holes.push(fu); const geo = new THREE.ExtrudeGeometry(f, { depth: esp, bevelEnabled: false, curveSegments: 16 }); geo.translate(0, 0, -esp / 2); return ms(g, geo, c, x, y, z); };
  // perfil [z, y] estendido ao longo de x
  const perfilX = (g, pts, len, c, x, y, z, b = .012) => { const f = new THREE.Shape(); pts.forEach(([a, q], i) => i ? f.lineTo(-a, q) : f.moveTo(-a, q)); f.closePath(); const geo = new THREE.ExtrudeGeometry(f, { depth: len - 2 * b, bevelEnabled: true, bevelThickness: b, bevelSize: b, bevelOffset: -b, bevelSegments: 2 }); geo.translate(0, 0, -(len - 2 * b) / 2); geo.rotateY(PI / 2); return ms(g, geo, c, x, y, z); };
  // contorno [x, z] estendido para cima a partir de y
  const planta = (g, pts, alt, c, y, b = .004) => { const f = new THREE.Shape(); pts.forEach(([a, q], i) => i ? f.lineTo(a, -q) : f.moveTo(a, -q)); f.closePath(); const geo = new THREE.ExtrudeGeometry(f, { depth: alt - 2 * b, bevelEnabled: true, bevelThickness: b, bevelSize: b, bevelOffset: -b, bevelSegments: 2 }); geo.translate(0, 0, b); geo.rotateX(-PI / 2); return ms(g, geo, c, 0, y, 0); };
  const pivo = (g, x, y, z, abre, eixo) => { const p = G(g, x, y, z); p.userData.abre = abre; p.userData.eixo = eixo; return p; };
  const I = (n, meta, fn) => PC.item('ele_' + n, { cat: 'eletronicos', ...meta }, (o = {}) => { const g = new THREE.Group(); fn(g, o); return g; });

  // ---------- linha branca ----------
  I('geladeira', { tags: ['geladeira', 'refrigerador', 'cozinha', 'eletrodomestico'], desc: 'Geladeira duplex, com portas que abrem e prateleiras por dentro' }, (g, o) => {
    const c = o.cor ?? 0x9ad8cf, c2 = DK(c, .82), W = .72;
    oca(g, W, 1.68, .6, .03, c, 0xf7fbff, 0, .9, -.035); pes(g, qd(.3, .22), .03, .06, PR);
    RB(g, W - .06, .03, .56, c2, 0, 1.24, -.045, .01); PL(g, W - .04, .05, .012, PR, 0, .09, .26);
    [.48, .72, .98].forEach(y => PL(g, W - .08, .008, .46, 0xbfe3ee, 0, y, -.07, { transparent: true, opacity: .55, roughness: .15 }));
    RB(g, W - .1, .13, .42, 0xd9f0f5, 0, .2, -.07, .012, { transparent: true, opacity: .75 }); RB(g, W - .12, .03, .02, 0x8fc7d6, 0, .24, .145, .008);
    C(g, .04, .04, .19, 0xffffff, -.2, .58, -.1, 10); B(g, .08, .03, .08, 0xe8683f, -.2, .69, -.1, .01); C(g, .03, .036, .2, 0x3fa45a, .05, .58, -.14, 10); ES(g, .05, 0xe0413a, .22, .53, -.04, 1, 1, 1, undefined, 10, 8); ES(g, .05, 0xffb52e, .14, .77, -.02, 1, 1, 1, undefined, 10, 8); RB(g, .2, .08, .16, 0xffd27a, -.16, .77, -.08, .02); RB(g, .22, .12, .18, 0x8fd0ee, 0, 1.08, -.1, .02); RB(g, .16, .07, .14, 0xf4f4f2, .18, 1.32, -.08, .015); RB(g, .2, .1, .16, 0xd8352f, -.14, 1.33, -.08, .015);
    TE(g, .3, .012, 0xfff6d8, 0, 1.2, .12, 0).rotation.x = PI;
    const coluna = IM(g, CUBO, PR, 14, (i, d) => { d.position.set(0, .35 + i * .085, -.343); d.scale.set(.58, .012, .012); }); RB(g, .6, 1.3, .006, 0x34383f, 0, .9, -.336, .002); C(g, .1, .1, .16, PR2, .2, .14, -.27, 12);
    const porta = (y, h, cor) => { const p = pivo(g, -W / 2, y, .265, -1.9, 'y'); RB(p, W, h, .075, cor, W / 2, 0, .04, .03); RB(p, W - .05, h - .05, .016, 0xcfd6db, W / 2, 0, -.002, .005); const n = h > .8 ? 3 : 1; for (let i = 0; i < n; i++) { const yy = (i - (n - 1) / 2) * (h / 3.2); RB(p, W - .14, .05, .05, 0xeef4f7, W / 2, yy, -.03, .008); [.2, .34, .5].forEach((x, k) => { if (n > 1) C(p, .03, .03, .12, [0x3fa45a, 0xffd23f, 0xe8683f][k], x, yy + .07, -.03, 8); }); } RB(p, .03, h * (h > .8 ? .34 : .6), .022, INOX, W - .05, h > .8 ? h * .26 : -h * .1, .09, .01, metal); return p; };
    const baixa = porta(.645, 1.19, c), alta = porta(1.5, .5, c); RB(alta, .15, .07, .004, PR, W / 2, .08, .079, .002); TE(alta, .13, .05, 0x2fd0c0, W / 2, .08, .0815);
    g.porta = baixa; g.porta2 = alta; g.portas = [baixa, alta]; });

  I('fogao', { tags: ['fogao', 'cozinha', 'forno', 'gas', 'eletrodomestico'], desc: 'Fogão de quatro bocas com forno, grades, botões e porta com visor' }, (g, o) => {
    const c = o.cor ?? 0xe8eaec, W = .76;
    oca(g, W, .72, .56, .02, c, 0x2f3238, 0, .42, -.02); pes(g, qd(.32, .22), .03, .06, PR2);
    RB(g, W, .13, .03, PR, 0, .72, .265, .008); RB(g, W - .01, .11, .03, c, 0, .12, .265, .008); RB(g, .5, .014, .02, INOX, 0, .135, .29, .006, metal); PL(g, W - .1, .005, .44, 0x8a9198, 0, .36, -.03, metal);
    const pe = pivo(g, 0, .185, .27, 1.45, 'x'); RB(pe, W - .012, .47, .035, c, 0, .235, 0, .012); RB(pe, W - .19, .28, .01, 0x12151a, 0, .235, .018, .006, vidro); PL(pe, W - .25, .02, .002, 0x3b4048, 0, .34, .024, vidro); CX(pe, .012, .6, INOX, 0, .425, .05, 10, metal); [-.27, .27].forEach(x => CZ(pe, .009, .04, INOX, x, .425, .03, 8, metal)); g.porta = pe;
    RB(g, W, .04, .62, INOX, 0, .8, 0, .012, metal); RB(g, W, .1, .03, c, 0, .87, -.295, .012); PL(g, W - .1, .003, .004, PR, 0, .85, -.277);
    g.chamas = []; qd(.19, .15).forEach(([x, z]) => { const b = G(g, x, .82, z + .01); C(b, .075, .08, .008, 0x8f969d, 0, .005, 0, 18, metal); C(b, .052, .056, .022, PR, 0, .018, 0, 16); C(b, .042, .05, .012, 0x34383f, 0, .035, 0, 14); PL(b, .22, .012, .012, PR2, 0, .045, 0); PL(b, .012, .012, .22, PR2, 0, .045, 0); TL(b, .1, .007, PR2, 0, .045, 0, PI * 2, undefined, 4, 16).rotation.x = PI / 2; const f = C(b, .03, .05, .03, 0x4aa8ff, 0, .05, 0, 12, { emissive: 0x2a7bff, emissiveIntensity: 1.6, transparent: true, opacity: .85 }); f.visible = false; g.chamas.push(f); });
    g.botoes = [-.28, -.14, 0, .14, .28].map(x => { const k = G(g, x, .725, .285); CZ(k, .024, .03, INOX, 0, 0, .012, 14, metal); PL(k, .006, .03, .004, PR, 0, .006, .028); return k; }); });

  I('forno', { tags: ['forno', 'cozinha', 'eletrico', 'assar', 'eletrodomestico'], desc: 'Forno elétrico de bancada, com porta de vidro, grade e botões giratórios' }, (g, o) => {
    const c = o.cor ?? 0xd94f3d;
    oca(g, .52, .32, .4, .014, c, 0x41454c, 0, .19, -.01); pes(g, qd(.21, .14), .018, .032, PR2);
    RB(g, .12, .3, .02, PR, .2, .19, .19, .008); PL(g, .34, .006, .3, 0x9aa1a8, -.05, .15, -.02, metal); IM(g, new THREE.BoxGeometry(.004, .004, .3), 0xb4bac0, 7, (i, d) => { d.position.set(-.2 + i * .05, .155, -.02); });
    g.resistencia = [.08, .3].map(y => CX(g, .006, .34, 0xff7a2a, -.05, y, -.02, 8, { emissive: 0xff5a10, emissiveIntensity: .8 }));
    g.botoes = [.29, .2, .11].map(y => { const k = G(g, .2, y, .2); CZ(k, .026, .022, INOX, 0, 0, .012, 14, metal); PL(k, .005, .03, .004, PR, 0, .01, .024); return k; });
    IM(g, CUBO, DK(c, .7), 8, (i, d) => { d.position.set(-.14 + i * .04, .351, -.04); d.scale.set(.012, .004, .2); });
    const p = pivo(g, -.06, .05, .195, 1.5, 'x'); RB(p, .39, .29, .02, c, 0, .145, .01, .008); RB(p, .31, .19, .008, 0x10141a, 0, .135, .022, .004, { transparent: true, opacity: .72, roughness: .1 }); CX(p, .01, .3, INOX, 0, .255, .05, 10, metal); [-.12, .12].forEach(x => CZ(p, .008, .035, INOX, x, .255, .032, 8, metal)); g.porta = p; });

  I('micro_ondas', { tags: ['micro-ondas', 'cozinha', 'eletrodomestico'], desc: 'Micro-ondas com painel digital, visor telado e prato giratório' }, (g, o) => {
    const c = o.cor ?? 0xe4e7ea;
    oca(g, .5, .28, .36, .012, c, 0xdfe3e6, 0, .16, -.01); pes(g, qd(.2, .12), .016, .022, PR2); PL(g, .34, .28, .002, 0xe7ebee, -.06, .16, .17);
    RB(g, .13, .27, .022, PR, .182, .16, .178, .008); RB(g, .1, .05, .004, PR2, .182, .265, .19, .002); g.tela = TE(g, .088, .036, 0x37e0b0, .182, .265, .1925);
    IM(g, CUBO, 0xffffff, 12, (i, d) => { d.position.set(.152 + (i % 3) * .03, .21 - Math.floor(i / 3) * .03, .19); d.scale.set(.022, .018, .006); return 0xb9c0c7; }); RB(g, .082, .024, .008, 0x3fc77f, .182, .07, .19, .004);
    IM(g, CUBO, DK(c, .7), 9, (i, d) => { d.position.set(.251, .13 + i * .016, -.08); d.scale.set(.003, .007, .14); });
    const pr = g.prato = G(g, -.07, .045, -.02); C(pr, .135, .13, .01, 0xd9eaf2, 0, 0, 0, 22, { transparent: true, opacity: .8, roughness: .1 }); C(pr, .07, .07, .012, 0xc3d6e0, 0, -.006, 0, 14);
    const p = pivo(g, -.25, .16, .172, -1.8, 'y'); RB(p, .362, .27, .024, 0x2f3339, .181, 0, .012, .008); RB(p, .27, .185, .006, 0x0f1216, .15, 0, .026, .003, { roughness: .2 }); IM(p, CUBO, 0x2f3339, 8, (i, d) => { d.position.set(.15, -.075 + i * .0215, .03); d.scale.set(.26, .002, .001); }); RB(p, .016, .2, .03, INOX, .335, 0, .036, .007, metal); g.porta = p; });

  I('lava_loucas', { tags: ['lava-loucas', 'cozinha', 'louca', 'eletrodomestico'], desc: 'Lava-louças de 60 cm, com porta basculante, cestos e braço giratório' }, (g, o) => {
    const c = o.cor ?? 0xaeb6bd, INT = 0xd5dade;
    oca(g, .6, .8, .54, .016, c, INT, 0, .46, -.02); PL(g, .59, .058, .02, PR, 0, .03, .22); pes(g, qd(.25, .2), .022, .06, PR2);
    const cesto = (y) => { const k = G(g, 0, y, -.02); [-.2, .2].forEach(z => CX(k, .005, .5, 0x7c8590, 0, 0, z, 6)); [-.25, .25].forEach(x => { const m = C(k, .005, .005, .4, 0x7c8590, x, 0, 0, 6); m.rotation.x = PI / 2; }); IM(k, new THREE.CylinderGeometry(.003, .003, .4, 4), 0x9aa3ad, 9, (i, d) => { d.position.set(-.2 + i * .05, -.005, 0); d.rotation.x = PI / 2; }); IM(k, new THREE.CylinderGeometry(.003, .003, .5, 4), 0x9aa3ad, 5, (i, d) => { d.position.set(0, -.005, -.16 + i * .08); d.rotation.z = PI / 2; }); return k; };
    const k1 = cesto(.2), k2 = cesto(.54); [-.16, -.09, -.02, .05, .12].forEach((z, i) => { const p = CX(k1, .1, .012, i % 2 ? 0xffc23a : BR, .08, .1, z, 16); p.rotation.y = 0; p.rotation.z = PI / 2 + .12; }); [-.2, -.14].forEach(x => { C(k1, .05, .04, .16, 0x8fd0ee, x, .08, .0, 12, { transparent: true, opacity: .75 }); }); [[-.14, -.08], [.02, -.08], [.16, -.08], [-.08, .08], [.08, .08]].forEach(([x, z], i) => { C(k2, .04, .032, .07, i % 2 ? 0xe8683f : 0x2f7fd6, x, .04, z, 12); });
    const h = g.helice = G(g, 0, .13, -.02); C(h, .03, .03, .03, 0x7c8590, 0, 0, 0, 12); RB(h, .44, .014, .04, 0x8f98a2, 0, .02, 0, .006);
    const p = pivo(g, 0, .065, .25, 1.5, 'x'); RB(p, .6, .78, .035, c, 0, .39, .017, .012); RB(p, .598, .085, .04, PR, 0, .735, .018, .008); g.tela = TE(p, .14, .036, 0x37e0b0, .14, .735, .0395); [-.24, -.19, -.14, -.09].forEach(x => BTN(p, .012, .006, INOX, x, .735, .04, 12, metal)); RB(p, .3, .03, .03, INOX, 0, .64, .045, .012, metal); PL(p, .5, .002, .002, DK(c, .8), 0, .08, .035); RB(p, .54, .7, .012, INT, 0, .38, -.006, .004); g.porta = p; });

  // lavadora e secadora dividem a estrutura: tambor, gaxeta e porta redonda
  const tamborFrontal = (g, o, sec) => {
    const c = o.cor ?? (sec ? 0xb9c3cc : 0xf0f2f2), Y = .39, D = .58, Z = D / 2;
    oca(g, .6, .83, D, .014, c, 0x4b5057, 0, .44, 0); chapaFuro(g, .6, .83, .205, .016, c, 0, .44, Z, Y - .44); pes(g, qd(.25, .22), .025, .03, PR2);
    const t = g.tambor = G(g, 0, Y, -.04); const cil = ms(t, new THREE.CylinderGeometry(.2, .2, .42, 22, 1, true), 0xb4bcc4, 0, 0, 0, { side: 1, roughness: .45, metalness: .5 }); cil.rotation.x = PI / 2; CZ(t, .2, .006, 0x9aa3ad, 0, 0, -.21, 22, metal); CZ(t, .05, .012, 0x7c8590, 0, 0, -.205, 12, metal); for (let i = 0; i < 3; i++) { const a = i / 3 * PI * 2 + .4, m = RB(t, .05, .045, .34, sec ? 0x8f98a2 : BR, Math.cos(a) * .17, Math.sin(a) * .17, 0, .018); m.rotation.z = a - PI / 2; }
    IM(t, new THREE.CylinderGeometry(.008, .008, .004, 6), 0x6e7680, 24, (i, d) => { const a = i / 6 * PI * 2 + (i >> 2) * .3, r = .07 + (i % 4) * .035; d.position.set(Math.cos(a) * r, Math.sin(a) * r, -.2); d.rotation.x = PI / 2; });
    ms(g, new THREE.TorusGeometry(.2, .018, 5, 24), sec ? PR : 0x8d949b, 0, Y, Z + .008);
    const p = pivo(g, -.215, Y, Z + .02, -1.8, 'y'); g.porta = p; const anel = sec ? PR : INOX; ms(p, new THREE.TorusGeometry(.165, .036, 6, 24), anel, .215, 0, .018, sec ? undefined : metal); if (sec) ES(p, .155, 0x2a3038, .215, 0, .008, 1, 1, .2, { roughness: .2, metalness: .3 }, 18, 8); else ES(p, .155, 0x7fb4d6, .215, 0, .004, 1, 1, .3, { transparent: true, opacity: .42, roughness: .1 }, 18, 8); RB(p, .03, .1, .03, PR, .395, 0, .028, .01); RB(p, .03, .07, .03, PR, -.005, .09, .012, .008); RB(p, .03, .07, .03, PR, -.005, -.09, .012, .008);
    const yc = .76; RB(g, .6, .1, .012, sec ? PR : 0xdfe3e6, 0, yc, Z + .006, .005); RB(g, .2, .072, .014, sec ? 0x34383f : BR, -.18, yc, Z + .014, .006); PL(g, .1, .012, .004, sec ? INOX : 0xaab1b8, -.18, yc, Z + .022); RB(g, .15, .056, .006, PR2, .03, yc, Z + .014, .003); g.tela = TE(g, .13, .04, sec ? 0xffb52e : 0x37e0b0, .03, yc, Z + .0175);
    const k = g.botao = G(g, .21, yc, Z + .012); CZ(k, .042, .024, INOX, 0, 0, .012, 18, metal); CZ(k, .03, .03, sec ? 0x34383f : BR, 0, 0, .015, 14); PL(k, .007, .03, .004, 0xd8352f, 0, .015, .032);
    if (sec) { IM(g, CUBO, DK(c, .62), 7, (i, d) => { d.position.set(0, .06 + i * .013, Z + .009); d.scale.set(.42, .006, .004); }); CZ(g, .05, .08, 0xb4bcc4, 0, .2, -Z - .03, 14, metal); CZ(g, .056, .02, 0x8f98a2, 0, .2, -Z - .06, 14, metal); }
    else { RB(g, .13, .1, .008, DK(c, .9), .2, .085, Z + .009, .004); CZ(g, .012, .008, DK(c, .7), .2, .085, Z + .015, 10); PL(g, .6, .012, .004, 0xbcc2c8, 0, .17, Z + .009); }
    RB(g, .36, .34, .004, DK(c, .86), 0, .5, -Z - .002, .002); IM(g, new THREE.CylinderGeometry(.005, .005, .004, 6), INOX, 4, (i, d) => { d.position.set(i % 2 ? .165 : -.165, i < 2 ? .655 : .345, -Z - .005); d.rotation.x = PI / 2; }, metal); if (!sec) [-.12, -.2].forEach((x, i) => { CZ(g, .016, .03, i ? 0xd8352f : 0x2f7fd6, x, .77, -Z - .014, 10); CZ(g, .021, .012, INOX, x, .77, -Z - .03, 6, metal); });
  };
  I('maquina_lavar', { tags: ['maquina de lavar', 'lavadora', 'lavanderia', 'roupa', 'eletrodomestico'], desc: 'Lavadora de abertura frontal com tambor que gira e gaveta de sabão' }, (g, o) => tamborFrontal(g, o, false));
  I('secadora', { tags: ['secadora', 'lavanderia', 'roupa', 'eletrodomestico'], desc: 'Secadora de roupas de porta escura, com grade baixa e duto traseiro' }, (g, o) => tamborFrontal(g, o, true));

  // ---------- portáteis de cozinha ----------
  I('liquidificador', { tags: ['liquidificador', 'cozinha', 'vitamina', 'eletroportatil'], desc: 'Liquidificador com copo transparente, tampa, alça e lâminas giratórias' }, (g, o) => {
    const c = o.cor ?? 0x2f7fd6, c2 = DK(c, .72);
    LA(g, [[0, 0], [.09, 0], [.095, .012], [.088, .03], [.08, .1], [.066, .135], [0, .135]], c, 0, 0, 0, 20); C(g, .096, .096, .008, PR2, 0, .004, 0, 20); C(g, .068, .072, .03, PR, 0, .148, 0, 16);
    const k = g.botao = G(g, 0, .07, .083); k.rotation.x = -.14; CZ(k, .026, .02, BR, 0, 0, .006, 14); PL(k, .006, .024, .004, c2, 0, .01, .018); [-.052, .052].forEach(x => BTN(g, .009, .008, BR, x, .082, .083, 10));
    g.liquido = LA(g, [[0, .17], [.052, .17], [.08, .3], [.08, .305], [0, .305]], o.liquido ?? 0xff7a8a, 0, 0, 0, 16);
    LA(g, [[0, .165], [.05, .165], [.066, .19], [.096, .42], [.102, .43]], 0xeaf6fb, 0, 0, 0, 20, VIDRO);
    IM(g, CUBO, BR, 5, (i, d) => { d.position.set(0, .22 + i * .04, .074 + i * .0108); d.scale.set(.03, .003, .002); d.rotation.x = -.13; });
    const h = g.helice = G(g, 0, .185, 0); g.lamina = h; C(h, .012, .014, .02, INOX, 0, 0, 0, 10, metal); [0, PI / 2].forEach((a, i) => { const m = PL(h, .08, .002, .014, INOX, 0, .01 + i * .007, 0, metal); m.rotation.y = a; m.rotation.z = i ? .3 : -.3; });
    TB(g, [[.082, .36, 0], [.15, .355, 0], [.158, .29, 0], [.13, .23, 0], [.075, .215, 0]], .013, PR); C(g, .108, .104, .026, PR, 0, .44, 0, 20); C(g, .04, .036, .03, 0xdce8ee, 0, .465, 0, 14, { transparent: true, opacity: .8 }); });

  I('batedeira', { tags: ['batedeira', 'cozinha', 'bolo', 'eletroportatil'], desc: 'Batedeira planetária com tigela de inox e batedor de arame' }, (g, o) => {
    const c = o.cor ?? 0xe0413a, c2 = DK(c, .75);
    RB(g, .22, .04, .36, c, 0, .022, 0, .018); RB(g, .2, .012, .34, c2, 0, .006, 0, .006); RB(g, .13, .23, .13, c, 0, .15, -.11, .05); ES(g, .095, c, 0, .3, -.03, 1, .95, 1.95, undefined, 18, 12); CZ(g, .075, .028, INOX, 0, .3, .1, 18, metal); ES(g, .058, c, 0, .3, .135, 1, 1, .5, undefined, 14, 8); C(g, .05, .036, .04, INOX, 0, .225, .05, 14, metal);
    const k = CX(g, .008, .05, INOX, .1, .3, -.09, 8, metal); ES(g, .018, PR, .13, .3, -.09); CX(g, .03, .012, INOX, .096, .28, -.12, 12, metal); g.alavanca = k;
    const t = G(g, 0, 0, .06); LA(t, [[0, .046], [.06, .046], [.1, .09], [.118, .15], [.122, .19], [.128, .195]], INOX, 0, 0, 0, 20, metal); [-1, 1].forEach(s => TL(t, .022, .005, INOX, s * .128, .165, 0, PI * 2, metal).rotation.y = PI / 2); g.tigela = t;
    const b = g.helice = G(g, 0, .21, .055); g.batedor = b; C(b, .006, .006, .05, INOX, 0, -.01, 0, 8, metal); [0, PI / 3, PI * 2 / 3].forEach(a => { const q = G(b, 0, -.085, 0); q.rotation.y = a; const m = ms(q, new THREE.TorusGeometry(.04, .0022, 4, 16), 0xdde2e6, 0, 0, 0, metal); m.scale.set(1, 1.4, 1); }); });

  I('cafeteira', { tags: ['cafeteira', 'cafe', 'cozinha', 'eletroportatil'], desc: 'Cafeteira de filtro com jarra de vidro, chapa quente e reservatório' }, (g, o) => {
    const c = o.cor ?? 0x2b2e34, a = o.cor2 ?? 0xd9483b;
    RB(g, .2, .035, .25, c, 0, .018, 0, .012); C(g, .085, .085, .008, 0x4c5158, 0, .039, .04, 18, metal); RB(g, .17, .27, .08, c, 0, .17, -.085, .02); RB(g, .2, .09, .25, c, 0, .315, 0, .03); RB(g, .15, .012, .19, DK(c, .7), 0, .362, 0, .005); RB(g, .022, .17, .05, 0xa8dcf0, .085, .175, -.085, .006, { transparent: true, opacity: .78 }); IM(g, CUBO, 0xffffff, 4, (i, d) => { d.position.set(.097, .12 + i * .035, -.085); d.scale.set(.002, .003, .02); return 0x2f7fd6; });
    C(g, .082, .066, .05, 0x3a3e45, 0, .25, .04, 16); RB(g, .05, .02, .05, a, .0, .362, -.03, .008);
    const j = g.jarra = G(g, 0, 0, .04); g.cafe = LA(j, [[0, .05], [.068, .052], [.076, .08], [.058, .125], [0, .125]], 0x4a2412, 0, 0, 0, 16);
    LA(j, [[0, .046], [.07, .048], [.083, .08], [.062, .15], [.053, .18], [.066, .205]], 0xe6f3f8, 0, 0, 0, 18, VIDRO); C(j, .068, .066, .012, PR, 0, .206, 0, 16); TL(j, .056, .006, PR, 0, .148, 0, PI * 2).rotation.x = PI / 2; TB(j, [[.066, .18, 0], [.118, .172, 0], [.122, .1, 0], [.078, .078, 0]], .009, PR);
    RB(g, .08, .022, .008, 0x3a3e45, .05, .018, .125, .006); const l = luz(g, .007, 0xff3a3a, .05, .018, .1305); RB(g, .025, .018, .006, a, -.05, .018, .126, .004); g.leds = [l]; });

  I('torradeira', { tags: ['torradeira', 'pao', 'cozinha', 'eletroportatil'], desc: 'Torradeira de duas fendas com fatias de pão, alavanca e botão' }, (g, o) => {
    const c = o.cor ?? 0xe8683f;
    RB(g, .29, .025, .17, PR, 0, .014, 0, .01); RB(g, .275, .155, .155, c, 0, .1, 0, .045); RB(g, .2, .05, .002, DK(c, .85), 0, .13, .078, .001); RB(g, .24, .012, .16, INOX, 0, .035, 0, .005, metal);
    [-.036, .036].forEach(z => { RB(g, .22, .006, .036, INOX, 0, .177, z, .002, metal); PL(g, .2, .002, .022, PR2, 0, .1805, z); });
    const p = g.torradas = G(g, 0, 0, 0); [-.036, .036].forEach(z => { RB(p, .14, .1, .018, 0xd9a15c, 0, .16, z, .008); RB(p, .125, .085, .019, 0xf0cf95, 0, .157, z, .006); ES(p, .036, 0xd9a15c, -.038, .21, z, 1, .6, .25, undefined, 10, 6); ES(p, .036, 0xd9a15c, .038, .21, z, 1, .6, .25, undefined, 10, 6); });
    PL(g, .006, .1, .022, PR2, .139, .11, 0); const a = g.alavanca = G(g, .15, .15, 0); RB(a, .036, .014, .028, PR, .008, 0, 0, .005);
    BTN(g, .018, .014, INOX, -.09, .07, .08, 14, metal); BTN(g, .01, .006, PR, .08, .06, .08, 10); TB(g, [[0, .03, -.082], [.01, .03, -.13], [.06, .012, -.15], [.1, .01, -.15]], .004, PR, undefined, 5); });

  I('sanduicheira', { tags: ['sanduicheira', 'misto quente', 'cozinha', 'eletroportatil'], desc: 'Sanduicheira de chapas antiaderentes com tampa articulada' }, (g, o) => {
    const c = o.cor ?? 0xf2c230, c2 = DK(c, .78);
    pes(g, qd(.09, .09), .012, .014, PR2); RB(g, .25, .045, .25, c, 0, .036, 0, .02); RB(g, .21, .01, .21, PR, 0, .062, 0, .004); RB(g, .24, .012, .24, c2, 0, .018, 0, .005);
    const placa = (p, y, z) => { PL(p, .29, .003, .004, 0x3a3e45, 0, y, z).rotation.y = PI / 4; PL(p, .29, .003, .004, 0x3a3e45, 0, y, z).rotation.y = -PI / 4; PL(p, .004, .003, .2, 0x3a3e45, 0, y, z); };
    placa(g, .068, 0);
    const t = pivo(g, 0, .07, -.12, -1.25, 'x'); RB(t, .25, .036, .25, c, 0, .018, .12, .018); RB(t, .19, .02, .19, c, 0, .042, .12, .018); RB(t, .21, .008, .21, PR, 0, -.002, .12, .004); placa(t, -.006, .12); RB(t, .07, .022, .06, PR, 0, .02, .27, .009); RB(g, .05, .018, .02, PR, 0, .05, .135, .006); g.tampa = t; g.porta = t;
    RB(g, .06, .02, .05, c2, 0, .03, -.13, .008); const l1 = luz(g, .006, 0xff3a3a, -.05, .036, .1252), l2 = luz(g, .006, 0x33ff7a, -.03, .036, .1252); g.leds = [l1, l2]; });

  I('air_fryer', { tags: ['air fryer', 'fritadeira', 'cozinha', 'eletroportatil'], desc: 'Fritadeira elétrica sem óleo, com gaveta e cesto de grade e painel digital' }, (g, o) => {
    const c = o.cor ?? 0x30343a, a = o.cor2 ?? 0xff8a1f;
    LA(g, [[0, .015], [.14, .015], [.158, .04], [.163, .1], [.16, .26], [.14, .31], [.09, .33], [0, .333]], c, 0, 0, 0, 24); pes(g, qd(.09, .09), .014, .018, PR2); C(g, .165, .165, .006, a, 0, .205, 0, 24);
    LA(g, [[0, .331], [.075, .331], [.075, .334], [0, .334]], 0x1c1f24, 0, 0, 0, 16); IM(g, CUBO, PR2, 12, (i, d) => { const q = i / 12 * PI * 2; d.position.set(Math.cos(q) * .115, .318, Math.sin(q) * .115); d.rotation.y = -q; d.scale.set(.03, .004, .007); d.rotation.z = -.5; });
    RB(g, .16, .07, .03, PR2, 0, .262, .153, .012); g.tela = TE(g, .1, .04, 0x37e0b0, -.012, .262, .1688); BTN(g, .014, .008, a, .062, .262, .169, 12);
    const d = pivo(g, 0, 0, 0, .22, 'z'); g.gaveta = d; g.porta = d; RB(d, .22, .15, .05, c, 0, .115, .15, .018); RB(d, .2, .135, .004, DK(c, .72), 0, .115, .176, .002); RB(d, .05, .04, .06, a, 0, .135, .2, .012); RB(d, .05, .1, .022, PR, 0, .11, .232, .01);
    const cst = G(d, 0, .1, .04); C(cst, .105, .09, .1, 0x3a3e45, 0, 0, 0, 18, { side: 2 }); IM(cst, CUBO, 0x8f969d, 7, (i, q) => { q.position.set(-.075 + i * .025, .051, 0); q.scale.set(.004, .004, .15); }); IM(cst, CUBO, 0xf2c14e, 16, (i, q) => { const a = i * 2.4, r = .02 + (i % 4) * .022; q.position.set(Math.cos(a) * r, .056 + (i % 3) * .004, Math.sin(a) * r); q.rotation.y = a * 1.7; q.scale.set(.012, .012, .085); }); });

  // solado em forma de ponta
  const SOLA = [[-.055, -.12], [.055, -.12], [.06, -.08], [.058, -.02], [.05, .04], [.034, .1], [.014, .14], [0, .15], [-.014, .14], [-.034, .1], [-.05, .04], [-.058, -.02], [-.06, -.08]];
  I('ferro_passar', { tags: ['ferro de passar', 'roupa', 'lavanderia', 'eletroportatil'], desc: 'Ferro de passar a vapor com solado de inox, cabo e dial de temperatura' }, (g, o) => {
    const c = o.cor ?? 0x7a4fd1, c2 = DK(c, .75);
    planta(g, SOLA, .012, INOX, 0, .003).material = mat(INOX, metal); planta(g, SOLA.map(([a, b]) => [a * .95, b * .96]), .026, c2, .012, .006);
    ES(g, .1, c, 0, .036, -.005, .54, .42, 1.34, undefined, 16, 10); ES(g, .05, 0xc9b6ff, 0, .06, .075, .55, .5, 1.2, { transparent: true, opacity: .65, roughness: .15 }, 12, 8);
    TB(g, [[0, .05, -.105], [0, .115, -.08], [0, .14, -.02], [0, .135, .05], [0, .09, .095]], .016, c, undefined, 8); RB(g, .012, .012, .05, a2(c), 0, .158, .02, .005);
    const k = g.botao = G(g, 0, .075, -.06); C(k, .024, .026, .014, BR, 0, 0, 0, 14); PL(k, .004, .004, .03, 0xd8352f, 0, .009, .006);
    TB(g, [[0, .03, -.125], [.01, .025, -.17], [.05, .01, -.2], [.11, .007, -.2]], .004, PR, undefined, 5); const l = luz(g, .006, 0xff3a3a, 0, .05, -.1095, PI); g.leds = [l]; });
  function a2(c) { return new THREE.Color(c).lerp(new THREE.Color(0xffffff), .55).getHex(); }

  // ---------- limpeza, clima, pessoal ----------
  I('aspirador', { tags: ['aspirador de po', 'limpeza', 'casa', 'eletrodomestico'], desc: 'Aspirador de pó de arrastar, com mangueira, tubo e bocal de piso' }, (g, o) => {
    const c = o.cor ?? 0xd8352f, r = G(g, 0, 0, -.1);
    ES(r, .17, c, 0, .17, -.2, .92, .84, 1.28, undefined, 18, 12); RB(r, .25, .04, .34, PR, 0, .05, -.2, .018); ES(r, .1, 0xa9d8ea, 0, .22, -.17, 1, .72, 1.3, { transparent: true, opacity: .62, roughness: .15 }, 14, 10); C(r, .03, .034, .03, PR, 0, .305, -.3, 12); C(r, .018, .018, .012, BR, .06, .3, -.3, 10);
    g.rodas = [-1, 1].map(s => { const w = G(r, s * .165, .085, -.28); CX(w, .085, .035, PR2, 0, 0, 0, 20); CX(w, .05, .04, INOX, 0, 0, 0, 14, metal); CX(w, .018, .045, PR, 0, 0, 0, 8); return w; }); C(r, .02, .02, .03, PR2, 0, .015, -.06, 10);
    CZ(r, .05, .05, PR, 0, .19, -.005, 14);
    TB(r, [[0, .19, .0], [0, .23, .1], [.03, .33, .2], [.05, .52, .27], [.04, .64, .3]], .024, CZA, undefined, 8); IM(r, new THREE.TorusGeometry(.0245, .003, 4, 12), 0x3a3e45, 3, (i, d) => { const p = [[0, .228, .095], [.03, .33, .2], [.05, .52, .27]][i]; d.position.set(...p); d.rotation.x = PI / 2 - (.5 + i * .4); });
    TB(r, [[.04, .64, .3], [.04, .35, .42], [.04, .06, .54]], .016, INOX, metal); const pu = RB(r, .05, .13, .05, c, .04, .64, .3, .018); pu.rotation.x = .38; const ca = RB(r, .034, .034, .13, PR, .04, .7, .22, .012); ca.rotation.x = -.25;
    RB(r, .3, .045, .08, PR, .04, .03, .56, .018); RB(r, .28, .012, .06, CZA, .04, .006, .56, .004); RB(r, .06, .04, .05, c, .04, .06, .53, .014); });

  I('robo_aspirador', { tags: ['robo aspirador', 'limpeza', 'casa', 'automacao'], desc: 'Robô aspirador redondo, com sensor no topo e escovas laterais' }, (g, o) => {
    const c = o.cor ?? 0x2b2e34, a = o.cor2 ?? 0x2fd0c0;
    LA(g, [[0, .018], [.165, .018], [.175, .034], [.175, .07], [.164, .086], [.14, .09], [0, .092]], c, 0, 0, 0, 28); C(g, .14, .14, .003, DK(c, .7), 0, .092, 0, 24); C(g, .046, .05, .026, PR2, 0, .106, -.05, 16); C(g, .03, .03, .012, 0x3a3e45, 0, .124, -.05, 12);
    const anel = TL(g, .026, .0035, a, 0, .094, .06, PI * 2, { emissive: a, emissiveIntensity: .9 }); anel.rotation.x = PI / 2; C(g, .018, .02, .006, BR, 0, .095, .06, 14); g.leds = [anel];
    const bp = TL(g, .177, .017, 0x585e66, 0, .05, 0, PI * .9, undefined, 6, 22); bp.rotation.set(PI / 2, 0, PI * .05); bp.scale.z = 1.2; [-.05, .05].forEach(x => luz(g, .007, 0xff5a5a, x, .05, .194));
    g.rodas = [-1, 1].map(s => { const w = G(g, s * .13, .03, 0); CX(w, .03, .022, PR2, 0, 0, 0, 14); return w; }); C(g, .012, .012, .012, PR2, 0, .012, .12, 8);
    g.escovas = [-1, 1].map(s => { const b = G(g, s * .125, .01, .125); C(b, .012, .012, .012, CZA, 0, .003, 0, 8); IM(b, CUBO, a, 3, (i, d) => { const q = i / 3 * PI * 2; d.position.set(Math.cos(q) * .04, 0, Math.sin(q) * .04); d.rotation.y = -q; d.scale.set(.08, .002, .004); }); return b; }); g.helice = g.escovas[0]; });

  const ventoinhaGrande = (cab, R, c, cg) => {
    const zf = .05, zt = -.04; [zf, zt].forEach(z => { TL(cab, R, .005, cg, 0, 0, z, PI * 2, metal, 4, 26); TL(cab, R * .62, .0025, cg, 0, 0, z, PI * 2, metal, 3, 18); TL(cab, R * .32, .0025, cg, 0, 0, z, PI * 2, metal, 3, 12); IM(cab, new THREE.CylinderGeometry(.0018, .0018, R * .93, 3, 1, true), cg, 16, (i, d) => { const a = i / 16 * PI * 2; d.position.set(Math.cos(a) * R * .535, Math.sin(a) * R * .535, z); d.rotation.z = a - PI / 2; }, metal); });
    IM(cab, new THREE.CylinderGeometry(.0025, .0025, zf - zt, 3, 1, true), cg, 10, (i, d) => { const a = i / 10 * PI * 2; d.position.set(Math.cos(a) * R, Math.sin(a) * R, (zf + zt) / 2); d.rotation.x = PI / 2; }, metal);
    CZ(cab, R * .2, .014, c, 0, 0, zf + .004, 18);
    const h = G(cab, 0, 0, .005); CZ(h, R * .17, .03, BR, 0, 0, 0, 14); for (let i = 0; i < 4; i++) { const q = G(h); q.rotation.z = i / 4 * PI * 2; const p = ES(q, R * .42, c, 0, R * .5, 0, .68, 1, .07, { transparent: true, opacity: .9 }, 8, 6); p.rotation.y = .4; } return h; };
  I('ventilador_mesa', { tags: ['ventilador', 'calor', 'vento', 'casa'], desc: 'Ventilador de mesa com grade, hélice de quatro pás e botões na base' }, (g, o) => {
    const c = o.cor ?? 0x2f7fd6, Y = .33, R = .17, a = 0xe6e9ec;
    LA(g, [[0, 0], [.125, 0], [.13, .012], [.11, .035], [.03, .05], [0, .05]], a, 0, 0, -.02, 24); C(g, .018, .022, Y - .05, a, 0, (Y + .05) / 2, -.02, 12);
    [-.06, -.02, .02, .06].forEach((x, i) => { const m = C(g, .012, .012, .012, i ? CZA : 0xd8352f, x, .036, .075, 10); m.rotation.x = .5; });
    const cab = g.cabeca = G(g, 0, Y, 0); ES(cab, .075, a, 0, 0, -.085, 1, 1, 1.15, undefined, 14, 10); CZ(cab, .06, .03, DK(a, .85), 0, 0, -.045, 14); C(cab, .012, .012, .05, CZA, 0, .085, -.095, 8);
    g.helice = ventoinhaGrande(cab, R, c, 0xd3d8dd); });
  I('ventilador_pedestal', { tags: ['ventilador', 'calor', 'vento', 'casa', 'coluna'], desc: 'Ventilador de coluna, com haste regulável e base em cruz' }, (g, o) => {
    const c = o.cor ?? 0x2f7fd6, Y = 1.22, R = .22, a = 0xe6e9ec;
    [0, PI / 2].forEach(q => { const m = RB(g, .52, .03, .07, a, 0, .03, 0, .012); m.rotation.y = q; }); C(g, .06, .07, .03, DK(a, .85), 0, .06, 0, 16);
    C(g, .024, .024, .72, a, 0, .42, 0, 14); C(g, .03, .03, .05, CZA, 0, .79, 0, 12); C(g, .015, .015, .42, INOX, 0, 1, 0, 12, metal);
    RB(g, .09, .13, .09, a, 0, 1.06, 0, .022); [.1, .06, .02].forEach((y, i) => BTN(g, .011, .008, i ? CZA : 0xd8352f, 0, 1.0 + y, .046, 10));
    const cab = g.cabeca = G(g, 0, Y, 0); ES(cab, .085, a, 0, 0, -.09, 1, 1, 1.2, undefined, 14, 10); CZ(cab, .07, .03, DK(a, .85), 0, 0, -.045, 14); C(cab, .016, .016, .05, CZA, 0, .095, -.1, 8);
    g.helice = ventoinhaGrande(cab, R, c, 0xd3d8dd); });

  I('ar_condicionado', { parede: true, tags: ['ar-condicionado', 'split', 'clima', 'parede'], desc: 'Ar-condicionado split de parede com aleta móvel e visor, instalado a 2,2 m' }, (g, o) => {
    const c = o.cor ?? 0xf0f2f3, Y = 2.2, W = .92;
    RB(g, W - .02, .27, .03, DK(c, .85), 0, Y, -.09, .01); perfilX(g, [[-.105, -.14], [.05, -.14], [.05, -.09], [.095, -.07], [.108, -.02], [.108, .04], [.098, .09], [.07, .125], [.02, .145], [-.105, .145]], W, c, 0, Y, 0);
    PL(g, W - .06, .02, .09, PR, 0, Y - .137, .0);
    IM(g, CUBO, DK(c, .6), 16, (i, d) => { d.position.set(-.38 + i * .0507, Y + .138, .03); d.scale.set(.03, .006, .12); d.rotation.x = .18; });
    PL(g, W - .04, .005, .004, DK(c, .8), 0, Y + .0, .1095);
    const al = pivo(g, 0, Y - .13, .075, .7, 'x'); RB(al, W - .08, .012, .08, 0xe2e6e9, 0, -.002, -.02, .005); g.aleta = al; g.porta = al;
    RB(g, .17, .036, .004, PR2, .29, Y - .05, .109, .002); g.tela = TE(g, .06, .02, 0x4ad8ff, .25, Y - .05, .1115); g.leds = [luz(g, .004, 0x33ff7a, .33, Y - .05, .1115), luz(g, .004, 0x4ad8ff, .35, Y - .05, .1115)];
    CX(g, .014, .05, 0xd6d9dc, W / 2 + .018, Y - .11, -.08, 10); });

  I('aquecedor', { tags: ['aquecedor', 'frio', 'calor', 'radiador', 'casa'], desc: 'Aquecedor a óleo com aletas, rodinhas e botão de temperatura' }, (g, o) => {
    const c = o.cor ?? 0xe4e7ea, a = o.cor2 ?? 0xe8683f, n = 9, p = .057;
    const geo = geoRB(.036, .5, .2, .016); g.aletas = IM(g, geo, c, n, (i, d) => { d.position.set(-.22 + i * p, .36, 0); }); IM(g, CUBO, DK(c, .8), 2, (i, d) => { d.position.set(0, i ? .59 : .13, 0); d.scale.set(.5, .03, .05); });
    IM(g, new THREE.CylinderGeometry(.009, .009, .46, 6), DK(c, .72), 7, (i, d) => { d.position.set(-.22 + i * .076, .36, .1); d.scale.set(0, 0, 0); });
    RB(g, .13, .2, .2, a, .31, .3, 0, .03); const k = g.botao = G(g, .376, .34, 0); CX(k, .03, .02, BR, 0, 0, 0, 14); PL(k, .006, .03, .006, a, .012, .012, 0); g.leds = [luz(g, .007, 0xff5a2a, .3762, .26, .03, PI / 2), luz(g, .007, 0x33ff7a, .3762, .26, -.03, PI / 2)];
    TB(g, [[-.22, .64, 0], [-.22, .68, 0], [.2, .68, 0], [.2, .64, 0]], .009, PR).scale.set(1, 1, 1);
    [-1, 1].forEach(s => { RB(g, .08, .022, .36, DK(c, .7), s * .17, .085, 0, .01); [-1, 1].forEach(q => { C(g, .012, .012, .07, CZA, s * .17, .06, q * .15, 8); CX(g, .032, .024, PR, s * .17, .032, q * .15, 14); }); }); });

  I('secador_cabelo', { tags: ['secador de cabelo', 'banheiro', 'salao', 'eletroportatil'], desc: 'Secador de cabelo com bico concentrador, grade traseira e cabo' }, (g, o) => {
    const c = o.cor ?? 0xe8527f, Y = .19, b = G(g, 0, Y, .01);
    const cor = LA(b, [[0, -.1], [.04, -.1], [.052, -.085], [.056, -.04], [.052, .04], [.04, .085], [.032, .1], [.036, .105], [.036, .15], [0, .15]], c, 0, 0, 0, 20); cor.rotation.x = PI / 2;
    const n = RB(b, .095, .024, .03, DK(c, .7), 0, 0, .16, .008); CZ(b, .058, .012, DK(c, .7), 0, 0, -.095, 18); TL(b, .05, .004, INOX, 0, 0, -.104, PI * 2, metal, 4, 20); IM(b, CUBO, INOX, 6, (i, d) => { d.position.set(0, 0, -.103); d.rotation.z = i / 6 * PI; d.scale.set(.1, .004, .004); }, metal);
    const h = g.helice = G(b, 0, 0, -.09); CZ(h, .014, .012, CZA, 0, 0, 0, 10);
    const m = G(g, 0, 0, -.035); m.rotation.x = .08; C(m, .024, .03, .17, c, 0, .09, 0, 14); ES(m, .03, DK(c, .7), 0, .008, 0, 1, .28, 1, undefined, 12, 6); RB(m, .018, .05, .01, BR, 0, .12, .027, .004); RB(m, .014, .02, .01, 0xffd23f, 0, .07, .03, .004);
    TB(g, [[0, .012, -.035], [.015, .012, -.1], [.07, .01, -.15], [.13, .008, -.15]], .004, PR, undefined, 5); });

  // ---------- celular e tablet ----------
  const APPS = [0x2fd0c0, 0xffc23a, 0xe8683f, 0x7a6be0, 0x3fa45a, 0xe8527f, 0xf4f4f2, 0x4ad8ff];
  const aparelho = (g, o, W, A, E2, bz, cols, lin, t, rIcone) => {
    const c = o.cor ?? 0x2b2e34, Y = A / 2, z = E2 / 2; RB(g, W, A, E2, c, 0, Y, 0, E2 * .45); RB(g, W - .0006, A - .0006, E2 + .0004, 0x0d0f13, 0, Y, 0, E2 * .4);
    g.tela = TE(g, W - bz * 2, A - bz * 2, o.corTela ?? 0x3f6fe0, 0, Y, z + .0004); TE(g, W - bz * 2, (A - bz * 2) * .42, 0x7a5be0, 0, Y + (A - bz * 2) * .29, z + .00045);
    const ic = rIcone, passoX = (W - bz * 2) / cols, passoY = (A - bz * 2) * .62 / lin; const ic_ = G(g); g.icones = ic_; IM(ic_, new THREE.PlaneGeometry(ic * 2, ic * 2), 0xffffff, cols * lin, (i, d) => { const cx = i % cols, ly = Math.floor(i / cols); d.position.set((cx - (cols - 1) / 2) * passoX, A - bz - (ly + .9) * passoY, z + .0007); return APPS[(i * 3 + ly) % 8]; }, { emissive: 0x000000 });
    IM(ic_, new THREE.PlaneGeometry(ic * 2, ic * 2), 0xffffff, cols, (i, d) => { d.position.set((i - (cols - 1) / 2) * passoX, bz + ic * 2.6, z + .0007); return APPS[(i * 5 + 1) % 8]; });
    TE(g, (W - bz * 2) * .9, ic * 3.6, 0xdbe6ff, 0, bz + ic * 2.6, z + .00055);
    CZ(g, Math.max(.0022, t), .0006, 0x2a2d33, 0, A - bz * 1.45, z + .0009, 10);
    const a = G(g, 0, 0, -z); RB(a, W - .001, A - .001, .0006, o.cor2 ?? 0x3f8fd6, 0, Y, -.0001, .0003); const s = W * .34; RB(a, s, s * (W < .1 ? 1.3 : 1), .0016, DK(o.cor2 ?? 0x3f8fd6, .7), -W / 2 + s * .72, A - s * .85, -.0008, .004);
    [0, 1].forEach(i => { CZ(a, s * .26, .0026, 0x12151a, -W / 2 + s * .72, A - s * .85 + (i ? -s * .32 : s * .32), -.0012, 12, vidro); }); CZ(a, s * .1, .002, 0xffffff, -W / 2 + s * 1.05, A - s * .85, -.0012, 8, { emissive: 0xffffff, emissiveIntensity: .4 });
    RB(g, .0008, A * .1, E2 * .5, 0x8f969d, W / 2 + .0002, A * .74, 0, .0003); RB(g, .0008, A * .06, E2 * .5, 0x8f969d, -W / 2 - .0002, A * .78, 0, .0003); };
  I('celular', { minPartes: 6, tags: ['celular', 'smartphone', 'telefone', 'tecnologia'], desc: 'Celular de tela cheia com ícones, em pé, e câmera dupla atrás' }, (g, o) => aparelho(g, o, .075, .156, .0085, .0028, 4, 5, .0024, .0055));
  I('tablet', { minPartes: 6, tags: ['tablet', 'tela', 'tecnologia'], desc: 'Tablet de tela grande com ícones, em pé, e câmera traseira' }, (g, o) => aparelho(g, o, .185, .26, .0075, .009, 5, 5, .0024, .0105));

  // ---------- informática ----------
  // fileiras de teclas instanciadas: lin linhas de col teclas, no plano y
  const teclas = (g, W, D, lin, col, y, c, tamZ = 1, o = {}) => { const px = W / col, pz = D / lin, esp = lin - 1; const lista = []; for (let l = 0; l < lin; l++) { if (l < esp) for (let k = 0; k < col; k++) lista.push([k, l, 1]); else { [[0, 1.4], [1.4, 1.2], [2.6, 1.2]].forEach(([a, b]) => lista.push([a + b / 2 - .5, l, b])); lista.push([3.8 + (col - 7.6) / 2 - .5, l, col - 7.6]); [[col - 3.8, 1.2], [col - 2.6, 1.2], [col - 1.4, 1.4]].forEach(([a, b]) => lista.push([a + b / 2 - .5, l, b])); } } return IM(g, CUBO, 0xffffff, lista.length, (i, d) => { const [k, l, lg] = lista[i]; d.position.set(-W / 2 + (k + .5) * px, y, -D / 2 + (l + .5) * pz); d.scale.set(px * lg * .86, o.alt ?? .0035, pz * .84 * tamZ); return (o.acento != null && ((l === 0 && k === 0) || (l === esp - 1 && k === col - 1))) ? o.acento : c; }); };
  I('notebook', { tags: ['notebook', 'laptop', 'computador', 'tecnologia'], desc: 'Notebook aberto com teclado, touchpad e tampa articulada' }, (g, o) => {
    const c = o.cor ?? 0xb8bec5;
    RB(g, .34, .018, .235, c, 0, .011, 0, .007, metal); pes(g, qd(.14, .09), .006, .003, PR2); RB(g, .3, .001, .125, PR, 0, .0205, -.035, .0004); teclas(g, .29, .115, 5, 14, .0222, 0x34383f); RB(g, .11, .001, .07, DK(c, .88), 0, .0205, .07, .0004); PL(g, .07, .004, .001, DK(c, .7), 0, .012, .118); [-.08, -.05].forEach(z => PL(g, .0012, .006, .016, PR2, .1704, .011, z));
    [-.05, -.02].forEach(z => PL(g, .0012, .006, .012, PR2, -.1704, .011, z)); RB(g, .24, .009, .008, PR, 0, .021, -.114, .003);
    const t = pivo(g, 0, .02, -.114, -.26, 'x'); t.rotation.x = -.26; t.userData.fechar = PI / 2; RB(t, .34, .228, .006, c, 0, .114, 0, .003, metal); PL(t, .332, .22, .0008, PR2, 0, .114, .0032); g.tela = TE(t, .318, .196, o.corTela ?? 0x3f6fe0, 0, .118, .0037); g.tampa = t; g.porta = t;
    TE(t, .23, .135, 0xeef3fb, -.03, .122, .0039); TE(t, .23, .016, 0x2fd0c0, -.03, .181, .0041); TE(t, .05, .135, 0x25365f, .118, .122, .0039); TE(t, .16, .006, 0x9fb4d8, -.05, .15, .0041); TE(t, .19, .006, 0xc3cfe6, -.035, .135, .0041); CZ(t, .0016, .0006, 0x3a3e45, 0, .2192, .004, 8); });

  // cooler de gabinete: gira em x, com anel de luz
  const cooler = (g, x, y, z, r, cor, eixo = 'x') => { const h = G(g, x, y, z); if (eixo === 'x') h.rotation.y = PI / 2; const a = TL(h, r, .006, cor, 0, 0, 0, PI * 2, { emissive: cor, emissiveIntensity: 1.3 }, 4, 18); const rot = G(h); CZ(rot, r * .3, .012, PR2, 0, 0, 0, 10); IM(rot, CUBO, 0x1c1f24, 7, (i, d) => { const q = i / 7 * PI * 2; d.position.set(Math.cos(q) * r * .6, Math.sin(q) * r * .6, 0); d.rotation.z = q; d.rotation.y = .4; d.scale.set(r * .78, r * .3, .002); }); return { rot, a }; };
  I('computador', { tags: ['computador', 'pc', 'gabinete', 'gamer', 'tecnologia'], desc: 'Gabinete de computador com lateral de vidro, placas e coolers iluminados' }, (g, o) => {
    const c = o.cor ?? 0x1f2329, a = o.cor2 ?? 0x2fd0c0, W = .21, H = .44, D = .42, Y = .235, a2_ = 0xe8527f;
    pes(g, qd(.08, .16), .016, .015, PR2); RB(g, .012, H, D, c, -W / 2 + .006, Y, 0, .004); RB(g, W, .012, D, c, 0, Y + H / 2 - .006, 0, .004); RB(g, W, .012, D, c, 0, Y - H / 2 + .006, 0, .004); RB(g, W, H, .01, c, 0, Y, -D / 2 + .005, .004);
    RB(g, W, H, .022, DK(c, 1.25), 0, Y, D / 2 - .011, .006); RB(g, .05, H - .08, .004, a, 0, Y, D / 2 + .001, .002, { emissive: a, emissiveIntensity: .9 }); IM(g, CUBO, PR2, 18, (i, d) => { d.position.set(i < 9 ? -.066 : .066, Y - .17 + (i % 9) * .043, D / 2 + .0006); d.scale.set(.05, .018, .002); }); BTN(g, .009, .006, INOX, 0, Y + H / 2 - .022, D / 2 + .002, 10, metal); [-.06, .06].forEach(x => PL(g, .022, .007, .002, PR2, x, Y + H / 2 - .022, D / 2 + .001));
    IM(g, CUBO, PR2, 8, (i, d) => { d.position.set(0, Y + H / 2 + .0004, -.13 + i * .037); d.scale.set(.15, .002, .014); });
    RB(g, .005, H - .03, D - .03, 0x2c6a58, -W / 2 + .016, Y, 0, .002); TE(g, .15, .3, 0xbfeee3, 0, Y + H / 2 - .0125, 0).rotation.x = PI / 2; RB(g, W - .02, .075, D - .025, 0x2a2e35, 0, Y - H / 2 + .05, 0, .004);
    RB(g, .1, .03, .24, 0x2b2e34, -.04, Y - .045, .02, .006); PL(g, .004, .024, .2, a2_, -.09, Y - .045, .02, { emissive: a2_, emissiveIntensity: .9 }); [-.04, .08].forEach(z => { CX(g, .034, .004, PR2, .012, Y - .045, z, 14); });
    RB(g, .05, .08, .08, 0x8f969d, -.05, Y + .1, .03, .006, metal); [-.05, -.03, -.01, .01].forEach(z => RB(g, .018, .09, .006, z < -.02 ? a2_ : a, -.07, Y + .1, z + .13, .002)); IM(g, CUBO, 0x8f969d, 4, (i, d) => { d.position.set(-.066, Y + .17, -.03 - i * .02); d.scale.set(.012, .05, .004); });
    const f1 = cooler(g, -.012, Y + .1, .03, .036, a), f2 = cooler(g, 0, Y + .06, D / 2 - .03, .06, a, 'z'), f3 = cooler(g, 0, Y - .06, D / 2 - .03, .06, a, 'z'), f4 = cooler(g, 0, Y + .1, -D / 2 + .018, .05, a2_, 'z'); g.helice = [f1.rot, f2.rot, f3.rot, f4.rot]; g.leds = [f1.a, f2.a, f3.a, f4.a];
    RB(g, .012, H - .014, D - .014, 0x90b8d0, W / 2 - .006, Y, 0, .004, { transparent: true, opacity: .1, roughness: .05, metalness: .2 }); RB(g, .002, H - .02, .012, 0x8f969d, W / 2 + .0005, Y, D / 2 - .03); });

  I('monitor', { tags: ['monitor', 'tela', 'computador', 'tecnologia'], desc: 'Monitor de computador widescreen com pé ajustável' }, (g, o) => {
    const c = o.cor ?? 0x24272e, W = .62, H = .36, Y = .31;
    RB(g, W, H, .024, c, 0, Y, 0, .01); RB(g, W + .002, .02, .026, DK(c, 1.3), 0, Y - H / 2 + .008, 0, .006); RB(g, .34, .21, .04, DK(c, .9), 0, Y, -.03, .018); IM(g, CUBO, PR2, 7, (i, d) => { d.position.set(0, Y + .03 + i * .008, -.0505); d.scale.set(.22, .003, .002); });
    g.tela = TE(g, W - .024, H - .044, o.corTela ?? 0x3f6fe0, 0, Y + .007, .0125); TE(g, .4, .24, 0xeef3fb, -.07, Y + .007, .0127); TE(g, .4, .022, 0x2fd0c0, -.07, Y + .116, .0129); TE(g, .15, .24, 0x25365f, .205, Y + .007, .0127); [.05, 0, -.05].forEach((d, i) => TE(g, .3 - i * .05, .012, 0xc3cfe6, -.1, Y + d, .0129));
    const l = luz(g, .0035, 0x33ff7a, .28, Y - H / 2 + .009, .0125); g.leds = [l]; [.23, .2, .17].forEach(x => CZ(g, .004, .002, 0x3a3e45, x, Y - H / 2 + .009, .0122, 8));
    RB(g, .055, .24, .03, DK(c, 1.2), 0, .16, -.052, .012); RB(g, .015, .1, .004, PR2, 0, .15, -.035, .002); RB(g, .24, .012, .19, DK(c, 1.2), 0, .006, -.03, .005); RB(g, .09, .018, .08, DK(c, 1.2), 0, .019, -.05, .008); });

  I('teclado', { tags: ['teclado', 'computador', 'digitar', 'tecnologia'], desc: 'Teclado de computador com teclas soltas e bloco numérico' }, (g, o) => {
    const c = o.cor ?? 0x2b2e34, t = G(g, 0, .0, 0); t.rotation.x = .055; t.position.y = .018;
    RB(t, .44, .018, .15, c, 0, 0, 0, .007); RB(t, .32, .0015, .11, PR2, -.05, .0095, .012, .0005); RB(t, .08, .0015, .11, PR2, .165, .0095, .012, .0005);
    const g1 = G(t, -.05, 0, .012); teclas(g1, .31, .105, 5, 14, .0125, o.corTecla ?? 0xe9ebee, 1, { acento: o.cor2 ?? 0xe8683f, alt: .006 });
    const g2 = G(t, .165, 0, .012); IM(g2, CUBO, 0xffffff, 17, (i, d) => { const l = Math.floor(i / 4), k = i % 4; d.position.set(-.03 + k * .02, .0125, -.042 + l * .021); d.scale.set(.0172, .006, .0178); return k === 3 ? 0xc9ced4 : 0xe9ebee; });
    IM(t, CUBO, 0x33ff7a, 3, (i, d) => { d.position.set(.15 + i * .012, .0095, -.058); d.scale.set(.006, .001, .003); }, { emissive: 0x22cc55, emissiveIntensity: .8 }); g.teclado = t;
    [-.17, .17].forEach(x => RB(g, .05, .01, .02, PR2, x, .007, -.062, .004)); TB(g, [[.0, .022, -.078], [.01, .02, -.12], [.05, .01, -.145], [.12, .006, -.15]], .0026, PR, undefined, 5); });

  I('mouse', { minPartes: 6, tags: ['mouse', 'computador', 'clique', 'tecnologia'], desc: 'Mouse com dois botões, roda de rolagem e fio' }, (g, o) => {
    const c = o.cor ?? 0x2b2e34, a = o.cor2 ?? 0xeceeee, S = [.0325, .038, .058];
    const cas = (phi, dphi, teta, dteta, cor, k = 1) => { const m = ms(g, new THREE.SphereGeometry(1, 12, 8, phi, dphi, teta, dteta), cor, 0, .003, 0, { side: 2 }); m.scale.set(S[0] * k, S[1] * k, S[2] * k); return m; };
    cas(PI, PI, 0, PI / 2, c); cas(0, PI, 1.02 + .06, PI / 2 - 1.08, c); cas(.03, PI / 2 - .05, 0, PI / 2, a, 1.012); cas(PI / 2 + .03, PI / 2 - .05, 0, PI / 2, a, 1.012);
    C(g, 1, 1, .004, PR2, 0, .002, 0, 16).scale.set(S[0] * .97, 1, S[2] * .97); const r = g.roda = G(g, 0, .036, .017); CX(r, .0078, .007, PR2, 0, 0, 0, 12); CX(r, .0084, .004, 0xd8352f, 0, 0, 0, 12); RB(g, .002, .009, .022, CZA, -.0318, .021, .004, .001); TB(g, [[0, .012, .057], [0, .01, .07], [.008, .007, .09], [.03, .005, .105]], .0018, PR, undefined, 5); });

  I('impressora', { tags: ['impressora', 'papel', 'escritorio', 'tecnologia'], desc: 'Impressora multifuncional com scanner, bandejas de papel e painel' }, (g, o) => {
    const c = o.cor ?? 0xe8eaec, a = o.cor2 ?? 0x2f3339;
    pes(g, qd(.18, .14), .012, .012, PR2); RB(g, .44, .14, .35, c, 0, .08, 0, .02); RB(g, .3, .036, .01, PR, 0, .062, .175, .004); RB(g, .13, .03, .015, DK(c, .85), -.14, .115, .175, .006); RB(g, .3, .024, .006, 0x8fd0ee, .03, .118, .172, .002, { transparent: true, opacity: .1 });
    RB(g, .34, .008, .16, DK(c, .88), 0, .045, .25, .004); g.papel = PL(g, .21, .003, .19, 0xffffff, 0, .052, .225); [[-.05, .25, .1, 0x2f7fd6], [.04, .25, .05, 0xe8683f], [.0, .28, .13, 0xc9ced4], [0, .19, .13, 0xc9ced4]].forEach(([x, z, w, cor]) => PL(g, w, .0008, .012, cor, x, .0538, z));
    const q = G(g, 0, 0, 0); q.rotation.x = -.15; const b = G(g, 0, .16, -.17); b.rotation.x = -.25; RB(b, .3, .007, .13, DK(c, .86), 0, .05, .0, .003); RB(b, .21, .004, .12, 0xffffff, 0, .056, .005, .001); PL(b, .26, .016, .006, a, 0, .055, .07);
    PL(g, .4, .002, .32, 0x2a3038, 0, .15, 0); const t = pivo(g, 0, .152, -.172, -1.25, 'x'); RB(t, .42, .03, .34, a, 0, .016, .172, .012); RB(t, .4, .003, .32, BR, 0, -.0005, .172, .001); RB(t, .06, .01, .018, DK(a, .7), 0, .022, .335, .004); g.tampa = t; g.porta = t;
    const pa = G(g, .13, .118, .178); pa.rotation.x = -.35; RB(pa, .15, .01, .06, PR, 0, .004, -.012, .004); g.tela = TE(pa, .07, .036, 0x4ad8ff, -.03, .0095, -.012); g.tela.rotation.set(-PI / 2, 0, 0); [.03, .055].forEach((x, i) => { const m = C(pa, .007, .007, .005, i ? 0x3fc77f : 0xd8352f, x, .011, -.012, 10); }); });

  I('caixa_som', { tags: ['caixa de som', 'musica', 'audio', 'tecnologia'], desc: 'Caixa de som com alto-falante, tweeter e porta de ar na frente' }, (g, o) => {
    const c = o.cor ?? 0xc27a3e, Y = .225, Z = .13;
    pes(g, qd(.09, .09), .014, .02, PR2); RB(g, .25, .41, .26, c, 0, Y, 0, .014); RB(g, .232, .392, .012, PR, 0, Y, Z + .001, .006);
    const fal = (y, r) => { const f = G(g, 0, y, Z + .006); CZ(f, r * 1.1, .006, 0x4c5158, 0, 0, .002, 22, metal); TL(f, r * .92, r * .06, 0x1b1d22, 0, 0, .005, PI * 2, undefined, 6, 24); return f; };
    const w = fal(Y - .065, .1); const cone = g.cone = G(w, 0, 0, 0); const co = LA(cone, [[.088, .0], [.04, -.024], [.03, -.026]], 0x34383f, 0, 0, .012, 22); co.rotation.x = -PI / 2; const dc = ES(cone, .033, 0x8a4f22, 0, 0, -.006, 1, 1, .55, undefined, 12, 8);
    const tw = fal(Y + .125, .036); ES(tw, .024, INOX, 0, 0, .004, 1, 1, .55, metal, 12, 8);
    const p = G(g, 0, Y - .175, Z + .006); CZ(p, .019, .006, 0x4c5158, 0, 0, .002, 14); CZ(p, .014, .008, PR2, 0, 0, .002, 12);
    IM(w, new THREE.CylinderGeometry(.0028, .0028, .004, 6), INOX, 6, (i, d) => { const a = i / 6 * PI * 2; d.position.set(Math.cos(a) * .104, Math.sin(a) * .104, .006); d.rotation.x = PI / 2; }, metal);
    const l = luz(g, .004, 0x33ff7a, .09, Y + .17, Z + .0074); g.leds = [l]; RB(g, .1, .08, .004, PR, 0, Y - .1, -.131, .002); [-.02, .02].forEach(x => CZ(g, .006, .012, x < 0 ? 0xd8352f : PR2, x, Y - .1, -.137, 8)); g.cones = [cone]; });

  I('fones', { tags: ['fone de ouvido', 'headphone', 'musica', 'audio'], desc: 'Fones de ouvido de arco com almofadas macias' }, (g, o) => {
    const c = o.cor ?? 0x2f7fd6, Y = .058, X = .08, p = 0x2a2d33;
    [-1, 1].forEach(s => { const k = G(g, s * X, Y, 0); k.rotation.z = s * .1; const sn = -s; CX(k, .056, .026, c, s * .014, 0, 0, 22); CX(k, .05, .004, DK(c, .7), s * .029, 0, 0, 18); CX(k, .056, .022, p, sn * .012, 0, 0, 22); CX(k, .03, .002, 0x45494f, sn * .0235, 0, 0, 14);
      TL(k, .059, .004, INOX, 0, 0, 0, PI * 1.02, metal, 4, 14).rotation.set(0, PI / 2, -.01); C(k, .0036, .0036, .05, INOX, s * .001, .082, 0, 6, metal); });
    TL(g, .09, .006, INOX, 0, .135, 0, PI, metal, 5, 22); const ac = TL(g, .092, .0145, p, 0, .135, 0, PI * .68, undefined, 6, 14); ac.rotation.z = PI * .16; ac.scale.z = 1.5; });

  I('camera', { tags: ['camera', 'foto', 'fotografia', 'tecnologia'], desc: 'Câmera fotográfica profissional genérica, com lente e visor traseiro' }, (g, o) => {
    const c = o.cor ?? 0x24272e, a = o.cor2 ?? 0xd8352f, r = G(g, 0, 0, -.04);
    RB(r, .15, .095, .07, c, 0, .0475, 0, .012); RB(r, .07, .03, .05, c, 0, .1, 0, .012); RB(r, .036, .01, .036, DK(c, .7), 0, .118, 0, .003); RB(r, .04, .096, .082, PR2, .058, .0485, .006, .016);
    C(r, .012, .013, .008, a, .052, .1, .012, 12); C(r, .016, .018, .012, INOX, -.052, .1, 0, 16, metal); C(r, .012, .013, .01, PR2, .03, .1, -.014, 12); [-1, 1].forEach(s => TL(r, .007, .0018, INOX, s * .079, .082, 0, PI * 2, metal, 4, 10).rotation.y = PI / 2);
    const l = g.lente = G(r, -.012, .048, .034); CZ(l, .04, .018, INOX, 0, 0, .008, 22, metal); CZ(l, .038, .03, PR2, 0, 0, .028, 22); IM(l, CUBO, 0x2f3339, 14, (i, d) => { const q = i / 14 * PI * 2; d.position.set(Math.cos(q) * .0385, Math.sin(q) * .0385, .028); d.rotation.z = q; d.scale.set(.003, .004, .026); }); CZ(l, .04, .006, a, 0, 0, .046, 22); CZ(l, .036, .026, PR, 0, 0, .062, 22); TL(l, .036, .002, CZA, 0, 0, .075, PI * 2, undefined, 4, 22); CZ(l, .03, .003, 0x0d1420, 0, 0, .074, 22, vidro); ES(l, .022, 0x2a4f8f, 0, 0, .074, 1, 1, .2, { roughness: .05, metalness: .7 }, 14, 6); ES(l, .007, 0xcfe6ff, .009, .009, .08, 1, 1, .2, undefined, 8, 4);
    g.tela = TE(r, .07, .05, 0x3f6fe0, -.022, .048, -.0356, PI); RB(r, .08, .06, .002, PR2, -.022, .048, -.0345, .001); IM(r, CUBO, CZA, 6, (i, d) => { d.position.set(.042 + (i % 2) * .018, .065 - (i >> 1) * .016, -.0356); d.scale.set(.012, .01, .002); }); RB(r, .03, .012, .006, PR2, 0, .1, -.026, .002); g.leds = [luz(r, .0035, 0xff3a3a, .04, .074, .0352)]; });

  I('videogame', { tags: ['videogame', 'console', 'jogo', 'controle', 'tecnologia'], desc: 'Console de videogame genérico com controle sem fio' }, (g, o) => {
    const c = o.cor ?? 0x6a4fd8, a = o.cor2 ?? 0x2fd0c0, K = G(g, 0, 0, -.07);
    pes(K, qd(.13, .08), .01, .01, PR2); RB(K, .32, .05, .21, PR, 0, .035, 0, .012); RB(K, .33, .02, .22, c, 0, .068, 0, .009); RB(K, .1, .008, .2, DK(c, .7), .08, .08, 0, .003).rotation.y = -.12; IM(K, CUBO, PR2, 8, (i, d) => { d.position.set(-.13 + i * .016, .0795, 0); d.scale.set(.006, .002, .17); });
    const led = RB(K, .2, .005, .002, a, -.04, .035, .1055, .001, { emissive: a, emissiveIntensity: 1.2 }); g.leds = [led]; RB(K, .1, .006, .002, PR2, .08, .046, .1055, .001); BTN(K, .006, .004, a, -.13, .046, .106, 10); [.1, .12].forEach(x => PL(K, .012, .005, .002, 0x3a3e45, x, .022, .1055));
    const J = g.controle = G(g, .02, 0, .145); J.rotation.y = -.25; const cc = 0x3a3e45;
    RB(J, .1, .022, .058, c, 0, .025, -.002, .01); [-1, 1].forEach(s => { const m = ES(J, .032, DK(c, .85), s * .056, .024, .016, 1, .62, 1.5, undefined, 12, 8); m.rotation.y = s * .35; RB(J, .03, .008, .014, PR, s * .044, .033, -.03, .003); });
    [[-.046, -.004], [.022, .016]].forEach(([x, z]) => { C(J, .0085, .0085, .01, PR, x, .039, z, 10); C(J, .0115, .009, .003, cc, x, .045, z, 12); });
    PL(J, .024, .004, .008, PR2, -.022, .037, .016); PL(J, .008, .004, .024, PR2, -.022, .037, .016); [[.046, -.014, 0xe8683f], [.058, -.002, 0xffc23a], [.046, .01, 0x3fa45a], [.034, -.002, 0x4ad8ff]].forEach(([x, z, cor]) => C(J, .0052, .0052, .004, cor, x, .037, z, 10)); });

  I('roteador', { tags: ['roteador', 'wifi', 'internet', 'rede', 'tecnologia'], desc: 'Roteador Wi-Fi de mesa com quatro antenas e luzes de status' }, (g, o) => {
    const c = o.cor ?? 0x24272e, a = o.cor2 ?? 0xd8352f;
    pes(g, qd(.095, .055), .009, .008, PR2); RB(g, .24, .034, .16, c, 0, .025, 0, .014); RB(g, .2, .004, .12, DK(c, 1.45), 0, .043, 0, .002); IM(g, CUBO, PR2, 11, (i, d) => { d.position.set(-.07 + i * .014, .0452, .006); d.scale.set(.006, .001, .08); }); PL(g, .2, .006, .002, a, 0, .018, .08);
    g.leds = [.06, .03, 0, -.03, -.06].map((x, i) => luz(g, .0038, i === 4 ? 0xffb52e : 0x33ff7a, x, .03, .0802));
    g.antenas = [[-.11, -.075, -.18], [-.04, -.082, -.05], [.04, -.082, .05], [.11, -.075, .18]].map(([x, z, q]) => { const p = G(g, x, .04, z); p.rotation.z = -q; C(p, .009, .009, .012, CZA, 0, .004, 0, 8); C(p, .0065, .0105, .16, c, 0, .09, 0, 10); return p; });
    [-.06, -.038, -.016, .006].forEach(x => PL(g, .017, .011, .003, 0x4f7fd6, x, .025, -.0802)); PL(g, .017, .011, .003, 0xffc23a, .04, .025, -.0802); CZ(g, .004, .003, PR2, .07, .025, -.081, 8); });

  I('modem', { tags: ['modem', 'internet', 'rede', 'tecnologia'], desc: 'Modem vertical de provedor, com fileira de luzes e conectores atrás' }, (g, o) => {
    const c = o.cor ?? 0xeef0f1, a = o.cor2 ?? 0x2f7fd6;
    RB(g, .12, .014, .09, DK(c, .8), 0, .008, 0, .006); RB(g, .17, .19, .044, c, 0, .11, 0, .014); RB(g, .15, .17, .002, DK(c, .93), 0, .11, .0218, .001); PL(g, .15, .02, .002, a, 0, .19, .0224);
    IM(g, CUBO, DK(c, .6), 12, (i, d) => { d.position.set(-.066 + i * .012, .2049, 0); d.scale.set(.005, .001, .024); });
    g.leds = [.15, .125, .1, .075, .05].map((y, i) => { const l = luz(g, .0036, i === 4 ? 0xff3a3a : 0x33ff7a, -.055, y, .0235); PL(g, .05, .004, .0005, 0xa8afb6, -.018, y, .0226); return l; });
    CZ(g, .007, .016, 0xd9b84a, .05, .13, -.03, 10, metal); CZ(g, .0108, .004, 0xb79a3c, .05, .13, -.024, 6, metal); PL(g, .016, .012, .003, 0x4f7fd6, .02, .13, -.0225); PL(g, .016, .012, .003, 0x4f7fd6, -.005, .13, -.0225); CZ(g, .006, .004, PR2, -.04, .13, -.0235, 10); });

  I('nobreak', { tags: ['nobreak', 'energia', 'bateria', 'tecnologia'], desc: 'Nobreak de mesa com visor, botão, luzes e tomadas na frente' }, (g, o) => {
    const c = o.cor ?? 0x24272e, a = o.cor2 ?? 0x3fc77f, Y = .135, Z = .17;
    pes(g, qd(.06, .13), .012, .014, PR2); RB(g, .16, .24, .34, c, 0, Y, 0, .014); RB(g, .152, .23, .018, 0x34383f, 0, Y, Z - .001, .008);
    RB(g, .1, .05, .003, PR2, 0, Y + .08, Z + .009, .001); g.tela = TE(g, .088, .04, 0x37e0b0, 0, Y + .08, Z + .011);
    CZ(g, .016, .006, INOX, 0, Y + .025, Z + .009, 16, metal); g.botao = CZ(g, .011, .008, a, 0, Y + .025, Z + .012, 14, { emissive: a, emissiveIntensity: .7 });
    g.leds = [-.045, -.022, .022, .045].map((x, i) => luz(g, .0045, [0x33ff7a, 0xffb52e, 0xff3a3a, 0x33ff7a][i], x, Y + .025, Z + .0085));
    [-1, 1].forEach(s => { const t = G(g, s * .036, Y - .055, Z + .009); RB(t, .058, .058, .004, BR, 0, 0, 0, .006); const h = CZ(t, .021, .003, 0xcfd4d9, 0, 0, .002, 6); h.rotation.y = 0; [[-.008, .002], [.008, .002], [0, -.008]].forEach(([x, y]) => CZ(t, .0027, .002, PR2, x, y, .0036, 6)); });
    IM(g, CUBO, PR2, 18, (i, d) => { d.position.set(.0805, Y + .08 - (i % 9) * .02, -.11 + (i > 8 ? .08 : 0)); d.scale.set(.002, .01, .06); }); IM(g, CUBO, PR2, 18, (i, d) => { d.position.set(-.0805, Y + .08 - (i % 9) * .02, -.11 + (i > 8 ? .08 : 0)); d.scale.set(.002, .01, .06); });
    [-.04, .04].forEach(x => { RB(g, .06, .05, .004, 0x34383f, x, Y + .04, -.171, .002); }); CZ(g, .03, .012, CZA, 0, Y - .05, -.174, 14); });

  I('controle_remoto', { tags: ['controle remoto', 'tv', 'sala', 'tecnologia'], desc: 'Controle remoto de televisão com teclado numérico e setas' }, (g, o) => {
    const c = o.cor ?? 0x24272e, a = 0xd8352f;
    RB(g, .052, .016, .175, c, 0, .01, 0, .007); RB(g, .046, .002, .165, DK(c, 1.4), 0, .0185, 0, .0009); RB(g, .05, .004, .17, DK(c, .7), 0, .003, 0, .002); RB(g, .03, .007, .006, 0x4f1818, 0, .011, .0862, .002);
    const cilB = new THREE.CylinderGeometry(.0048, .0048, .003, 10); C(g, .0062, .0062, .003, a, -.012, .0198, -.067, 12); C(g, .0048, .0048, .003, 0xd9dde2, .012, .0198, -.067, 10);
    IM(g, cilB, 0xffffff, 12, (i, d) => { d.position.set(-.014 + (i % 3) * .014, .0198, -.05 + Math.floor(i / 3) * .0125); return i === 10 ? 0xffffff : 0xcfd4d9; });
    C(g, .017, .017, .002, 0x45494f, 0, .0195, .024, 18); C(g, .0064, .0064, .003, a, 0, .0204, .024, 12); [[0, -.012], [0, .012], [-.012, 0], [.012, 0]].forEach(([x, z]) => PL(g, Math.abs(z) ? .007 : .003, .0008, Math.abs(z) ? .003 : .007, BR, x, .0208, .024 + z));
    [-.015, .015].forEach(x => { RB(g, .009, .002, .026, 0x45494f, x, .0192, .058, .001); }); [0x3fa45a, 0xffc23a, 0x4ad8ff, a].forEach((cor, i) => PL(g, .007, .002, .004, cor, -.0135 + i * .009, .0194, .0775)); });

  I('lampada', { minPartes: 6, tags: ['lampada', 'luz', 'ideia', 'energia'], desc: 'Lâmpada de bulbo com rosca e filamento visível; g.bulbo e g.filamento acendem' }, (g, o) => {
    const c = o.cor ?? 0xffd76a, on = o.ligada !== false;
    LA(g, [[0, 0], [.004, 0], [.006, .002], [.0115, .004], [.0132, .007], [.0132, .03], [.0145, .032], [0, .032]], 0xc9ced4, 0, 0, 0, 16, metal); C(g, .0052, .0052, .0035, PR2, 0, .0018, 0, 10); IM(g, new THREE.TorusGeometry(.0133, .0011, 4, 16), 0xaab1b8, 4, (i, d) => { d.position.set(0, .009 + i * .0055, 0); d.rotation.x = PI / 2 + .06; }, metal);
    LA(g, [[.0148, .031], [.0158, .036], [.0138, .04]], 0xf1f2ef, 0, 0, 0, 16);
    const m = { transparent: true, opacity: .62, roughness: .08, emissive: c, emissiveIntensity: on ? .55 : 0, side: 2 }; const b = LA(g, [[.0138, .038], [.0155, .05], [.022, .065], [.03, .082], [.0335, .1], [.032, .116], [.024, .129], [.012, .1355], [0, .137]], c, 0, 0, 0, 22, m); g.bulbo = b; b.renderOrder = 2;
    C(g, .0045, .0115, .03, 0xe7f1f5, 0, .055, 0, 8, { transparent: true, opacity: .7 }); [-1, 1].forEach(s => TB(g, [[s * .002, .068, 0], [s * .007, .085, 0], [s * .012, .1, 0]], .0005, 0xc9ced4, undefined, 4));
    g.filamento = TB(g, [[-.012, .1, 0], [-.008, .106, 0], [-.004, .098, 0], [0, .106, 0], [.004, .098, 0], [.008, .106, 0], [.012, .1, 0]], .0009, 0xffa23a, { emissive: 0xff8a1f, emissiveIntensity: on ? 2.2 : 0 }, 4); });

  I('tomada', { parede: true, minPartes: 6, tags: ['tomada', 'energia', 'parede', 'eletrica'], desc: 'Tomada de três pinos em espelho branco, instalada a 30 cm do chão' }, (g, o) => {
    const c = o.cor ?? 0xf1f2ef, Y = .3, Z = .006;
    RB(g, .08, .12, .012, c, 0, Y, 0, .004); RB(g, .054, .074, .002, DK(c, .92), 0, Y, Z + .0004, .001); const h = C(g, .0235, .0235, .004, 0xc6cacd, 0, Y, Z + .001, 6); h.rotation.x = PI / 2; h.rotation.y = PI / 6;
    [[-.0095, -.0025], [.0095, -.0025], [0, .0065]].forEach(([x, y]) => CZ(g, .0024, .0012, PR2, x, Y - y * 1, Z + .0031, 10));
    [1, -1].forEach(s => { CZ(g, .0028, .0016, INOX, 0, Y + s * .049, Z + .0002, 10, metal); PL(g, .0042, .0008, .0006, PR, 0, Y + s * .049, Z + .0011); });
    PL(g, .054, .0008, .0008, DK(c, .8), 0, Y + .037, Z + .0014); });

  I('disjuntor', { parede: true, tags: ['disjuntor', 'quadro de luz', 'energia', 'eletrica', 'parede'], desc: 'Quadro de disjuntores de parede com tampa fumê e alavancas, a 1,5 m' }, (g, o) => {
    const c = o.cor ?? 0xe0e3e6, Y = 1.5, W = .36, H = .44, D = .1, Z = D / 2;
    oca(g, W, H, D, .012, c, 0xb9bec4, 0, Y, 0); RB(g, W - .04, H - .05, .006, 0xd4d8db, 0, Y, -.03, .002);
    const n = 8, pw = .036, gR = G(g, 0, Y, -.005); g.alavancas = [];
    [.1, -.08].forEach((ry, l) => { PL(gR, W - .05, .012, .012, 0x8f969d, 0, ry, -.016); IM(gR, CUBO, 0xfafbfb, n, (i, d) => { d.position.set((i - (n - 1) / 2) * pw, ry, .004); d.scale.set(.033, .1, .05); }); PL(gR, W - .06, .032, .048, 0xe3e6e9, 0, ry, .002); for (let i = 0; i < n; i++) { const x = (i - (n - 1) / 2) * pw, t = G(gR, x, ry, .03); t.rotation.x = -.45; PL(t, .014, .03, .022, i === 0 && l === 0 ? 0xd8352f : PR, 0, .004, .004); g.alavancas.push(t); } PL(gR, .29, .012, .002, 0xf7e9a8, 0, ry + .056, .03); });
    TB(g, [[-.14, Y + .17, -.01], [-.15, Y + .14, .0]], .003, 0xd8352f, undefined, 4);
    const p = pivo(g, -W / 2, Y, Z + .004, -1.9, 'y'); g.porta = p; [-1, 1].forEach(s => { RB(p, W, .04, .012, c, W / 2, s * (H / 2 - .02), 0, .005); RB(p, .04, H, .012, c, W / 2 + s * (W / 2 - .02), 0, 0, .005); }); PL(p, W - .07, H - .07, .004, 0x2c3a44, W / 2, 0, 0, { transparent: true, opacity: .2, roughness: .1 }); RB(p, .018, .05, .016, CZA, W - .018, 0, .004, .006);
    const tri = PC.H.forma(p, [[-.017, 0], [.017, 0], [0, .03]], .002, 0xffc61a, W / 2, H / 2 - .036, .007); PL(p, .002, .012, .001, PR, W / 2, H / 2 - .021, .0082); PL(p, .05, .01, .001, 0xeef0f1, W / 2, -H / 2 + .02, .0065);
    [-1, 1].forEach(s => RB(g, .012, .04, .012, 0x8f969d, -W / 2 - .002, Y + s * .15, Z, .004)); });
})();
