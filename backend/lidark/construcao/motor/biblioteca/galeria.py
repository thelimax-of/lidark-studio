"""Testa e fotografa a biblioteca. Uso, a partir de backend:
python <esta pasta>/galeria.py [categoria ou item,item] [pagina]
Gera galeria_<filtro>_<pagina>.jpg (15 itens por folha) e imprime os problemas de cada item.
Um render por vez: a trava faz os outros esperarem, para não esgotar a memória.
"""
import base64, json, os, sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, '.')
from lidark.construcao import MOTOR
from lidark.construcao.render import ARGS, CSS

H = Path(__file__).resolve().parent
filtro, pagina = (sys.argv[1] if len(sys.argv) > 1 else ''), int(sys.argv[2]) if len(sys.argv) > 2 else 0
TRAVA = H / '.trava'
while True:
    try:
        os.close(os.open(TRAVA, os.O_CREAT | os.O_EXCL)); break
    except FileExistsError:
        if time.time() - TRAVA.stat().st_mtime > 300:
            TRAVA.unlink(missing_ok=True)
        time.sleep(2)
try:
    arqs = [H / 'base.js'] + sorted(p for p in (H / 'itens').glob('*.js')) if (H / 'itens').exists() else [H / 'base.js']
    JS = r"""
(() => { const { THREE, scene, cam, luzes, ceu, add, rotulo, D } = K3; ceu('#dfe9f0', '#f6f4ee'); luzes(0xfff4e6, 0xdfeeff, 0xc9c0b0, 2.6, 30); scene.environmentIntensity = .4;
 const chao = add(new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({ color: 0xe9e6df, roughness: 1 }))); chao.rotation.x = -Math.PI / 2; chao.receiveShadow = true;
 const F = window.FILTRO, P = window.PAGINA, nomes = Object.keys(PC.R).filter(n => !F || F.split(',').includes(n) || F.split(',').includes(PC.R[n].cat)), lista = nomes.slice(P * 15, P * 15 + 15), COL = 3, W = 3.3, rel = [];
 nomes.forEach(n => { try { const g = PC.novo(n), b = new THREE.Box3().setFromObject(g), s = b.getSize(new THREE.Vector3()); let tri = 0, cham = 0; g.traverse(q => { if (q.isMesh) { cham++; tri += (q.geometry.index ? q.geometry.index.count : q.geometry.attributes.position.count) / 3 * (q.isInstancedMesh ? q.count : 1); } }); const pr = []; if (!isFinite(s.x + s.y + s.z)) pr.push('medida inválida'); else { if (PC.R[n].parede !== true && Math.abs(b.min.y) > .06) pr.push('não toca o chão: y=' + b.min.y.toFixed(2)); if (s.x < .005 || s.y < .005 || s.z < .005) pr.push('achatado'); } if (cham < (PC.R[n].minPartes ?? 6)) pr.push('poucas peças: ' + cham); if (!PC.R[n].cat || !PC.R[n].desc) pr.push('falta categoria ou descrição'); rel.push({ n, cat: PC.R[n].cat, m: [s.x, s.y, s.z].map(v => +v.toFixed(2)), partes: cham, tri: Math.round(tri), pr }); } catch (e) { rel.push({ n, pr: ['ERRO: ' + e.message] }); } });
 window.REL = rel; window.TOT = nomes.length;
 lista.forEach((n, i) => { try { const g = PC.novo(n), b = new THREE.Box3().setFromObject(g), s = b.getSize(new THREE.Vector3()), m = Math.max(s.x, s.y, s.z) || 1, k = Math.min(2.5 / m, 1.6), q = new THREE.Group(); q.add(g); q.scale.setScalar(k); q.position.set((i % COL - 1) * W - (b.min.x + b.max.x) / 2 * k, 0, Math.floor(i / COL) * W - 6.6 - (b.min.z + b.max.z) / 2 * k); add(q); g.rotation.y = -.5; const r = rotulo(n, [(i % COL - 1) * W, -.01, Math.floor(i / COL) * W - 6.6 + 1.5], 0, 9, 'pilula'); r.style.fontSize = '20px'; r.style.padding = '3px 10px'; } catch (e) { } });
 cam.position.set(0, 25, 11); cam.lookAt(0, 0, -.6); cam.fov = 36; cam.updateProjectionMatrix(); K3.iniciar(() => { });
})();"""
    kit = (MOTOR / 'kit.bundle.js').read_text(encoding='utf-8')
    corpo = '\n'.join(f'<script>{a.read_text(encoding="utf-8")}</script>' for a in arqs)
    hp = H / 'tmp_galeria.html'
    d = {'falas': [{'t': 0, 'dur': 9, 'texto': 'x', 'words': []}], 'total': 9, 'cauda': 0, 'destaque': []}
    hp.write_text(f"<!doctype html><meta charset=utf8><style>{CSS}</style><div id=c></div><div id=hud></div><div id=leg></div><script>window.ZOOM=1;window.DADOS={json.dumps(d)};window.FILTRO={json.dumps(filtro)};window.PAGINA={pagina}</script><script>{kit}</script>{corpo}<script>{JS}</script>", encoding='utf-8')
    with sync_playwright() as p:
        b = p.chromium.launch(channel='msedge', args=ARGS)
        pg = b.new_page(viewport={'width': 1080, 'height': 1920}); er = []
        pg.on('pageerror', lambda e: er.append(str(e)))
        pg.goto(hp.as_uri())
        try:
            pg.wait_for_function('window.pronto===true', timeout=60000)
        except Exception:
            print('ERRO_CENA', er[:5]); sys.exit(2)
        pg.evaluate('frame(1)')
        cdp = pg.context.new_cdp_session(pg)
        out = H / f"galeria_{(filtro or 'tudo').replace(',', '_')[:30]}_{pagina}.jpg"
        out.write_bytes(base64.b64decode(cdp.send('Page.captureScreenshot', {'format': 'jpeg', 'quality': 88})['data']))
        rel = pg.evaluate('window.REL'); tot = pg.evaluate('window.TOT'); b.close()
    ruins = [r for r in rel if r.get('pr')]
    print('ITENS', tot, 'COM_PROBLEMA', len(ruins), 'FOLHA', out)
    for r in ruins[:40]:
        print(' ', r['n'], r['pr'])
    print('ERROS', er[:4])
finally:
    TRAVA.unlink(missing_ok=True)
