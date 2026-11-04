"""Biblioteca de poses-chave. Braços: [x, y, ângulo da mão ou None, curva do cotovelo] relativos ao ombro,
em frações do alcance do braço (+x = para onde o ator olha). Pernas: [x, y] relativos ao quadril, em frações da perna."""
from __future__ import annotations

BASE = dict(lean=0, q=[0, 0], hr=0, h=[0, 0], o=[0, 0], lid=None, ex='neutro', fecha=0, lagrima=0,
            N=[.05, .95, None, 1], F=[.02, .95, None, 1], mN='relaxada', mF='relaxada', sN='', sF='',
            pN=[-.02, .985], pF=[.04, .985], aN=0, aF=0, osc=None, anda=0, balanco=1, sobre='', frenteF=0, sombra=1, sent=0, ciclo=0, bb=[30, -100])

POSES = {
    'em_pe': {},
    'em_pe_atento': dict(ex='atento', hr=-2, o=[3, -1], N=[.1, .84, None, 1], F=[.04, .85, None, 1]),
    'olha_baixo': dict(ex='preocupado', hr=9, h=[2, 4], lean=2, o=[2, 6]),
    'anda': dict(anda=1.5, N=[.1, .86, None, 1], F=[.0, .86, None, 1]),
    'corre': dict(anda=2.4, lean=7, N=[.3, .6, None, 1], F=[.3, .62, None, 1], balanco=0, ex='preocupado'),
    # ------ mesa
    'mesa': dict(q=[0, 104], pN=[.1, .56], pF=[.2, .56], lean=2, sobre='NF', sombra=0, hr=7, h=[0, 2], o=[4, 7], ex='cansado',
                 N=[.14, .64, 30, 1], F=[.16, .64, 150, -1]),
    'mesa_conta': dict(q=[0, 104], pN=[.1, .56], pF=[.2, .56], lean=3, sobre='NF', sombra=0, hr=9, h=[0, 4], o=[3, 8], ex='cansado',
                       N=[.2, .62, 30, 1], F=[.16, .66, 150, -1], mN='pinca', mF='aberta'),
    'mesa_suspira': dict(q=[0, 104], pN=[.1, .56], pF=[.2, .56], lean=-1, sobre='NF', sombra=0, hr=-6, h=[0, -5], o=[1, -3], ex='triste', lid=.56,
                         N=[.16, .62, 30, 1], F=[.16, .64, 150, -1]),
    'mesa_abre': dict(q=[0, 104], pN=[.1, .56], pF=[.2, .56], lean=2, sobre='NF', sombra=0, hr=7, o=[3, 7], ex='atento', N=[.24, .5, 50, 1], F=[.1, .5, 130, -1], mN='pinca', mF='pinca'),
    'mesa_surpresa': dict(q=[0, 104], pN=[.1, .56], pF=[.2, .56], lean=-2, sobre='NF', sombra=0, hr=-4, h=[0, -4], o=[0, 0], ex='surpreso', N=[.2, .24, -120, 1], F=[.16, .64, 150, -1], mN='aberta', mF='aberta'),
    # ------ Caio
    'espia': dict(lean=7, ex='preocupado', hr=-2, h=[6, 0], o=[8, 3], F=[.05, .6, -14, 1], mF='punho', sF='cofrinho', frenteF=1),
    'espia_fundo': dict(lean=8, ex='triste', hr=2, h=[6, 2], o=[9, 6], F=[.05, .6, -14, 1], mF='punho', sF='cofrinho', frenteF=1),
    'segura_cofre': dict(ex='preocupado', hr=9, h=[4, 3], lean=7, o=[3, 7], F=[.05, .42, -14, 1], mF='punho', sF='cofrinho', frenteF=1),
    'sacode_cofre': dict(ex='atento', hr=7, h=[4, 3], lean=7, o=[3, 7], F=[.06, .3, 6, 1], mF='punho', sF='cofrinho', frenteF=1, osc=dict(F=[.012, .05, 3.6, 0])),
    'mesa_estudo': dict(sent=1, q=[0, 96], pN=[.5, .54], pF=[.58, .54], lean=12, sombra=0, hr=11, h=[4, 2], o=[3, 7], ex='decidido', N=[.5, .14, -6, 1], F=[.56, .2, 20, 1], mN='punho', sN='lapis', mF='aberta', sobre='NF', osc=dict(N=[.012, .006, 2.6, 0])),
    'mesa_pensa': dict(sent=1, q=[0, 96], pN=[.5, .54], pF=[.58, .54], lean=6, sombra=0, hr=-5, h=[2, -3], o=[3, -7], ex='neutro', N=[.34, -.12, -60, 1], F=[.56, .2, 20, 1], mN='punho', sN='lapis', mF='aberta', sobre='NF'),
    'mexe': dict(ex='decidido', hr=6, o=[3, 7], lean=4, N=[.7, -.1, 0, 1], F=[.34, .52, None, 1], mN='punho', sN='colher', mF='aberta', osc=dict(N=[.05, .012, 1.3, 0])),
    'mexe_rapido': dict(ex='preocupado', hr=6, o=[3, 7], lean=4, N=[.7, -.1, 0, 1], F=[.34, .52, None, 1], mN='punho', sN='colher', mF='aberta', osc=dict(N=[.06, .016, 2.6, 0])),
    'tosse': dict(ex='tosse', lean=-7, hr=-9, h=[0, 3], N=[.3, -.2, -120, 1], F=[.34, .52, None, 1], mN='punho', mF='aberta', osc=dict(N=[.01, .012, 5, 0])),
    'abana': dict(ex='tosse', lean=-5, hr=-8, N=[.56, -.2, -40, 1], F=[.34, .52, None, 1], mN='aberta', mF='aberta', osc=dict(N=[.12, .05, 3.6, 0])),
    'coca_cabeca': dict(ex='preocupado', hr=-6, o=[-4, -6], N=[.28, -.28, -130, 1], F=[.5, .42, 20, 1], mN='aberta', osc=dict(N=[.015, .012, 3.4, 0])),
    'vende': dict(ex='sorriso', hr=-2, o=[4, 0], N=[.26, .36, -20, 1], F=[.42, .3, -90, -1], mN='punho', sN='', mF='punho', sF='placa'),
    'vende_chama': dict(ex='alegre', hr=-5, h=[0, -2], o=[5, -1], N=[.26, .36, -20, 1], F=[.46, .06, -90, -1], mN='punho', mF='punho', sF='placa'),
    'vende_triste': dict(ex='preocupado', hr=5, o=[5, 2], N=[.26, .36, -20, 1], F=[.42, .34, -90, -1], mN='punho', mF='punho', sF='placa'),
    'entrega': dict(ex='sorriso', hr=-5, o=[5, -3], lean=3, N=[.66, .08, -10, 1], F=[.42, .34, -90, -1], mN='pinca', sN='brig', mF='punho', sF='placa'),
    'entrega2': dict(ex='alegre', hr=-5, o=[6, -4], lean=3, N=[.66, .08, -10, 1], F=[.42, .34, -90, -1], mN='palma', sN='', mF='punho', sF='placa'),
    'caixa_duas': dict(ex='sorriso', hr=3, o=[3, 4], N=[.4, .4, -5, 1], F=[.5, .42, -20, 1], mN='punho', mF='punho'),
    'caixa_vazia': dict(ex='surpreso', hr=8, h=[1, 3], o=[2, 8], N=[.4, .4, -5, 1], F=[.5, .42, -20, 1], mN='punho', mF='punho'),
    'comemora': dict(ex='alegre', hr=-6, h=[0, -2], o=[4, -3], lean=-2, N=[.4, .4, -5, 1], F=[.74, -.52, -70, -1], mN='punho', mF='punho', frenteF=0),
    'sentado_calcada': dict(q=[0, 170], pN=[.6, .3], pF=[.72, .3], lean=6, hr=12, h=[3, 5], o=[2, 8], ex='triste', N=[.5, .74, 12, 1], F=[.46, .76, 12, 1], frenteF=1, sombra=1, sent=1),
    'sentado_cabeca': dict(q=[0, 170], pN=[.6, .3], pF=[.72, .3], lean=9, hr=17, h=[4, 9], o=[2, 8], ex='triste', lid=.7, N=[.54, .72, 12, 1], F=[.5, .74, 12, 1], frenteF=1, sent=1),
    'sentado_cama': dict(q=[0, 124], pN=[.5, .5], pF=[.6, .5], lean=4, hr=-3, o=[6, -6], ex='preocupado', N=[.5, .76, 10, 1], F=[.44, .78, 10, 1], frenteF=1, sent=1),
    'sentado_cama_olha': dict(q=[0, 124], pN=[.5, .5], pF=[.6, .5], lean=2, hr=-8, h=[0, -3], o=[7, -8], ex='triste', N=[.5, .76, 10, 1], F=[.44, .78, 10, 1], frenteF=1, sent=1),
    'segura_bola': dict(ex='triste', hr=9, h=[2, 3], o=[3, 8], lean=3, N=[.44, .4, -12, 1], F=[.62, .36, 200, -1], mN='palma', mF='palma', sN='bola', frenteF=1),
    'estende_bola': dict(ex='aperto', hr=-2, o=[6, 1], lean=4, N=[.66, .2, -8, 1], F=[.74, .24, 200, -1], mN='palma', mF='palma', sN='bola', frenteF=1),
    'solta_bola': dict(ex='aperto', hr=4, o=[6, 2], N=[.2, .8, None, 1], F=[.1, .82, None, 1], lean=1),
    'recebe_nota': dict(ex='triste', hr=6, h=[1, 2], o=[3, 7], lean=2, N=[.5, .38, 0, 1], F=[.02, .85, None, 1], mN='pinca', sN='nota'),
    'prof_compra': dict(ex='sorriso', hr=-6, h=[0, -1], o=[6, 6], lean=3, N=[.6, .3, -10, 1], F=[.16, .52, -60, 1], mN='palma', frenteF=1),
    'prof_morde': dict(ex='sorriso', hr=-4, o=[4, 2], lean=-1, N=[.34, -.06, -130, 1], F=[.16, .52, -60, 1], mN='pinca', sN='brig', frenteF=1, lid=.5),
    'prof_ok': dict(ex='sorriso', hr=-4, o=[5, 0], N=[.2, .4, -30, 1], F=[.2, .58, -60, 1], frenteF=1),
    'ped_sentado': dict(q=[0, 150], pN=[.5, .42], pF=[.62, .42], lean=6, hr=4, ex='cansado', sombra=0, sent=1, N=[.54, .76, 8, 1], F=[.36, .82, 8, 1], frenteF=1),
    'ped_estende': dict(ex='alegre', hr=-5, o=[6, 3], lean=7, N=[.66, .22, -10, 1], F=[.2, .7, None, 1], mN='pinca', frenteF=0),
    'ped_paga': dict(ex='sorriso', hr=-4, o=[6, 2], lean=5, N=[.64, .26, -10, 1], F=[.3, .6, None, 1], mN='pinca', sN='moedaM'),
    'ped_come': dict(ex='sorriso', hr=-6, h=[0, -2], o=[2, 0], lid=.4, N=[.3, -.1, -130, 1], F=[.16, .7, None, 1], mN='pinca', sN='brig'),
    'viz_recebe': dict(ex='sorriso', hr=6, h=[1, 2], o=[6, 4], lean=3, N=[.62, .32, -5, 1], F=[.66, .36, 200, -1], mN='palma', mF='palma', frenteF=1),
    'viz_paga': dict(ex='sorriso', hr=5, o=[6, 4], lean=3, N=[.62, .3, -10, 1], F=[.1, .8, None, 1], mN='pinca', sN='nota'),
    'viz_bola': dict(ex='sorriso', hr=2, o=[6, 2], N=[.5, .4, -12, 1], F=[.6, .38, 200, -1], mN='palma', mF='palma', sN='bola', frenteF=1),
    'mae_ao_lado': dict(ex='preocupado', hr=4, o=[5, 2], N=[.1, .84, None, 1], F=[.04, .85, None, 1]),
    'mae_braco': dict(ex='emocionado', hr=8, h=[6, 6], lean=9, o=[3, 6], lagrima=1, N=[.46, .68, None, 1], F=[.3, .6, None, 1], sobre='N'),
    'mae_abraca': dict(ex='emocionado', hr=12, h=[8, 10], lean=13, fecha=1, lagrima=1, N=[.44, .78, None, 1], F=[.3, .6, None, 1], sobre='N'),
    'caio_abraca': dict(ex='emocionado', hr=8, h=[6, 4], lean=8, fecha=1, N=[.78, .38, 10, 1], F=[.5, .5, None, 1]),
    'caio_olha_mae': dict(ex='preocupado', hr=-8, h=[0, -2], o=[6, -6], N=[.1, .84, None, 1], F=[.06, .85, None, 1]),
}


SENT = dict(sent=1, q=[0, 165], pN=[.5, .5], pF=[.58, .5], sombra=0, frenteF=1)
POSES.update({
    # ------ Zé e Bia. Mesa: cotovelo junto ao corpo, antebraço para a frente, mãos apoiadas.
    'de_pe': dict(hr=-1, o=[3, 0]),
    'sentado': dict(SENT, lean=4, hr=2, o=[4, 2], N=[.42, .78, 12, 1], F=[.42, .8, 12, 1], mN='apoiada', mF='apoiada'),
    'sentado_mesa': dict(SENT, lean=7, hr=8, o=[3, 7], ex='preocupado', sobre='NF', N=[.44, .5, 8, 1], F=[.42, .54, 8, 1], mN='punho', mF='apoiada', sN='caneta'),
    'sentado_mesa_soma': dict(SENT, lean=7, hr=9, o=[3, 7], ex='preocupado', sobre='NF', N=[.48, .5, 8, 1], F=[.42, .54, 8, 1], mN='punho', mF='apoiada', sN='caneta', osc=dict(N=[.02, .006, 2.4, 0])),
    'sentado_mesa_cabeca': dict(SENT, lean=9, hr=12, h=[3, 5], ex='triste', lid=.5, o=[2, 8], sobre='F', N=[.3, -.08, -110, 1], F=[.6, .54, 8, 1], mN='apoiada', mF='apoiada'),
    'segura': dict(hr=7, o=[3, 7], lean=2, ex='atento', N=[.42, .44, -10, 1], mN='punho', sN='celular'),
    'segura_cel': dict(hr=9, h=[2, 3], o=[2, 8], lean=3, ex='atento', N=[.3, .36, -60, 1], mN='punho', sN='celular'),
    'digita': dict(hr=10, h=[2, 3], o=[2, 8], lean=3, ex='alegre', N=[.3, .36, -60, 1], F=[.36, .4, -40, 1], mN='punho', sN='celular', mF='dedo', frenteF=1, osc=dict(F=[.012, .012, 5, 0])),
    'aponta': dict(hr=-3, o=[6, 0], ex='decidido', F=[.94, -.1, -8, 1], mF='dedo'),
    'braco_alto': dict(hr=-3, o=[5, -3], ex='alegre', lean=-3, F=[.34, -.9, -78, -1], mF='aberta'),
    'acena': dict(hr=-4, o=[5, -3], ex='alegre', lean=-2, F=[.56, -.7, -70, -1], mF='aberta', osc=dict(F=[.06, .02, 2.2, 0])),
    'maos_quadril_nao': dict(),
    'pedala': dict(lean=14, q=[-30, 0], hr=-8, h=[4, 2], o=[6, 0], ex='neutro', N=[.54, .6, 8, 1], F=[.56, .62, 8, 1], mN='punho', mF='punho', frenteF=1, sombra=0, sent=1, ciclo=1.6),
    'pedala_medo': dict(lean=4, q=[-30, 0], hr=-3, h=[4, 0], o=[8, 0], ex='surpreso', N=[.56, .56, 8, 1], F=[.58, .58, 8, 1], mN='punho', mF='punho', frenteF=1, sombra=0, sent=1, ciclo=3.2),
    'sobe': dict(lean=12, hr=8, h=[3, 4], o=[4, 4], ex='tosse', N=[.5, .4, -6, 1], mN='punho', sN='pizza', anda=1.0, balanco=0),
    'entrega_pizza': dict(lean=-3, hr=2, ex='tosse', lid=.6, N=[.5, .46, -6, 1], mN='punho', sN='pizza'),
    'ofegante': dict(lean=16, hr=14, h=[3, 8], ex='tosse', lid=.7, N=[.3, .86, None, 1], F=[.34, .86, None, 1], mN='aberta', mF='aberta'),
    'cliente_olha': dict(hr=8, h=[2, 3], o=[-3, 7], ex='neutro', N=[.46, .5, -10, 1], mN='apoiada'),
    'cliente_cade': dict(hr=-2, o=[4, -1], ex='bravo_c', N=[.4, .42, -30, 1], F=[.5, .1, -90, 1], mN='apoiada', mF='aberta', frenteF=1),
    'veste_olha': dict(hr=7, o=[4, 6], ex='preocupado', N=[.6, .06, -6, 1], mN='punho', sN='camisa'),
    'veste_pinta': dict(hr=9, o=[4, 7], ex='decidido', N=[.66, .1, -10, 1], F=[.5, -.04, -30, 1], mN='punho', mF='punho', sF='caneta', frenteF=1, osc=dict(F=[.012, .012, 4, 0])),
    'bolso_ri': dict(hr=-4, o=[4, 0], ex='alegre', N=[.46, .5, -30, 1], mN='punho', sN='notas'),
    'caido': dict(q=[0, 270], lean=38, hr=30, h=[4, 6], ex='tosse', lid=.8, pN=[.7, .1], pF=[.86, .02], N=[.5, .3, 40, 1], F=[.7, .1, 30, 1], mN='aberta', mF='aberta', sent=1, sombra=0, frenteF=1),
    'levanta_mao': dict(hr=2, ex='preocupado', o=[5, 0], N=[.38, -.14, -100, 1], mN='aberta'),
    'bia_balcao': dict(hr=-2, o=[5, 0], ex='sorriso', sobre='NF', N=[.3, .86, 4, 1], F=[.34, .88, 4, 1], mN='apoiada', mF='apoiada'),
    'bia_ri': dict(hr=-6, h=[0, -3], o=[6, -4], ex='alegre', fecha=0, sobre='F', N=[.32, .04, -115, 1], F=[.34, .88, 4, 1], mN='relaxada', mF='apoiada'),
    'ze_balcao': dict(hr=-2, o=[6, 0], ex='sorriso', sobre='N', N=[.5, .72, 4, 1], mN='apoiada'),
    'ze_compra': dict(hr=-3, o=[6, 0], ex='sorriso', sobre='N', N=[.5, .66, 2, 1], mN='punho', sN='pao'),
    'ze_encolhe': dict(hr=6, h=[0, 4], o=[5, -5], ex='calmo', sobre='N', N=[.5, .72, 4, 1], mN='apoiada', lean=3),
    'cama_cel': dict(SENT, lean=6, hr=9, h=[2, 3], o=[2, 8], ex='atento', N=[.34, .42, -60, 1], F=[.42, .8, 12, 1], mN='punho', sN='celular', mF='apoiada'),
    'cama_pensa': dict(SENT, lean=3, hr=-6, h=[0, -2], o=[-6, -7], ex='preocupado', N=[.34, .42, -60, 1], F=[.42, .8, 12, 1], mN='punho', sN='celular', mF='apoiada'),
    'chefe_bravo': dict(hr=-4, o=[6, 0], ex='bravo_c', lean=4, N=[.06, .95, None, 1], F=[.02, .95, None, 1], mN='punho', mF='punho'),
    'bici_final': dict(hr=2, o=[5, 2], ex='preocupado', N=[.5, .46, -8, 1], mN='punho'),
})


def resolve(p):
    """Aceita "nome", ["nome", {ajustes}] ou {"base": "nome", ...}."""
    if isinstance(p, str):
        b, ov = p, {}
    elif isinstance(p, dict):
        b, ov = p.get('base', 'em_pe'), {k: v for k, v in p.items() if k != 'base'}
    else:
        b, ov = p[0], p[1]
    out = dict(BASE)
    out.update(POSES[b])
    out.update(ov)
    return out
