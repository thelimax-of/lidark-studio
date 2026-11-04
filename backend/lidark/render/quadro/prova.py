"""Folhas de prova da variedade: personagens, lugares e objetos, sem LLM nem vídeo.

    python -m lidark.render.quadro.prova personagens|lugares|objetos SAIDA.png --tmp PASTA
"""
from __future__ import annotations

import base64
import io
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import boneco, gerador, lugares, objetos, personagens


def _shots(ep, tmp, n):
    from playwright.sync_api import sync_playwright
    html, _ = gerador.pagina(ep, tmp)
    hp = Path(tmp) / "prova.html"
    hp.write_text(html, encoding="utf-8")
    fs = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 1080, "height": 1920})
        er = []
        pg.on("pageerror", lambda e: er.append(str(e)))
        pg.goto(hp.as_uri())
        cdp = pg.context.new_cdp_session(pg)
        for i in range(n):
            pg.evaluate("t=>frame(t)", i + .5)
            fs.append(Image.open(io.BytesIO(base64.b64decode(cdp.send("Page.captureScreenshot", {"format": "jpeg", "quality": 90})["data"]))).convert("RGB"))
        b.close()
    if er:
        print("ERROS", er[:3])
    return fs


def _folha(fs, rot, saida, cols=4, w=480):
    h = int(w * 16 / 9)
    lin = (len(fs) + cols - 1) // cols
    o = Image.new("RGB", (cols * w, lin * (h + 44)), "#1b1d24")
    d = ImageDraw.Draw(o)
    fn = ImageFont.truetype("arialbd.ttf", 26)
    for i, f in enumerate(fs):
        x, y = (i % cols) * w, (i // cols) * (h + 44)
        o.paste(f.resize((w, h)), (x, y + 44))
        d.text((x + 10, y + 8), rot[i][:34], fill="#ffd23f", font=fn)
    o.save(saida, quality=90)
    print("folha", o.size, saida)


def _ep(planos, **k):
    return dict(meta=100, cenas=[dict(id="p", dur=len(planos), cenario="neutro", dias=0, planos=planos)], **k)


def personagens_folha(saida, tmp):
    r = random.Random(77)
    us: set[str] = set()
    fixos = [dict(idade="crianca", sexo="m"), dict(idade="idoso", sexo="f", corpo="curvado", cabelo="coque", cor_cabelo=5), dict(idade="adulto", corpo="gordo", cabelo="calvo", barba="cheia", nariz="batata", orelha="abano", dentes="dentuco"),
             dict(idade="jovem", sexo="f", corpo="alto", cabelo="black", roupa="vestido"), dict(idade="meia_idade", corpo="barrigudo", cabelo="careca", roupa="camisa", nariz="adunco", sobrancelha="monocelha"), dict(idade="adolescente", sexo="f", cabelo="trancas", dentes="aparelho"),
             dict(idade="idoso", sexo="m", corpo="magro", cabelo="grisalho_lado", barba="bigode", oculos=True, roupa="terno", cor_roupa="#2b2f3a"), dict(idade="adulto", sexo="f", corpo="gordo", cabelo="rabo", roupa="avental"), dict(idade="jovem", sexo="m", corpo="forte", cabelo="topete", roupa="regata", nariz="longo"),
             dict(idade="adulto", sexo="f", corpo="baixo", cabelo="chanel", roupa="jaleco", cor_roupa="#fbfbf6", oculos=True), dict(idade="adulto", sexo="m", corpo="magro", cabelo="franja", nariz="pontudo", orelha="grande", dentes="banguela"), dict(idade="meia_idade", sexo="f", cabelo="longo", roupa="uniforme"),
             dict(idade="adulto", sexo="m", roupa="macacao", barba="cavanhaque"), dict(idade="crianca", sexo="f", cabelo="trancas"), dict(idade="meia_idade", sexo="m", corpo="alto", roupa="listrada", cranio="quadrado"), dict(idade="idoso", sexo="f", corpo="gordo", cabelo="curto", cor_cabelo=4, roupa="casaco")]
    pers = {f"p{i}": boneco.sortear(r, us, **fx) for i, fx in enumerate(fixos)}
    pl = [dict(ate=i + 1, cenario="neutro", sem_hud=True, cam=[[0, 360, 640, 1]], atores=[dict(nome=f"p{i}", x=360, y=1190, escala=1.5, poses=[[0, ["de_pe", dict(ex="neutro" if i % 3 else "sorriso", o=[5, 1])]]])]) for i in range(16)]
    _folha(_shots(_ep(pl, personagens=pers), tmp, 16), [boneco.descrever(pers[f"p{i}"]) for i in range(16)], saida)


def lugares_folha(saida, tmp):
    nomes = ["casa_pobre", "casa_rica", "barraco", "salao", "atelie", "academia", "hospital", "onibus", "praia", "sitio", "boteco", "cinema", "delegacia", "oficina", "casamento", "ponto_onibus"]
    if len(sys.argv) > 5:
        nomes = sys.argv[5].split(",")
    hs = ["dia", "noite", "tarde"]
    pl = [dict(ate=i + 1, cenario="composto", sem_hud=True, opc=dict(tipo=n, semente=100 + i * 13, hora=hs[i % 3], clima="chuva" if n == "ponto_onibus" else "bom"), cam=[[0, 360, 640, 1]]) for i, n in enumerate(nomes)]
    _folha(_shots(_ep(pl), tmp, len(nomes)), nomes, saida)


def objetos_folha(saida, tmp, extra):
    nomes = ["maquina de costura", "vestido", "tesoura", "flores", "perfume", "carta", "mala", "bolo"] + list(extra)
    pl = []
    for i, n in enumerate(nomes):
        sv, _ = objetos.svg_de(n)
        pl.append(dict(ate=i + 1, cenario="detalhe", sem_hud=True, cam=[[0, 360, 640, 1]], objetos=[dict(id=f"o{i}", svg=sv, camada="frente", chaves=[[0, 360, 860, 0, 3, 1]])]))
    _folha(_shots(_ep(pl), tmp, len(nomes)), nomes, saida)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    personagens._registrar_tipos()
    alvo, s, tmp = sys.argv[1], sys.argv[2], sys.argv[4]
    Path(tmp).mkdir(parents=True, exist_ok=True)
    if alvo == "personagens":
        personagens_folha(s, tmp)
    elif alvo == "lugares":
        lugares_folha(s, tmp)
