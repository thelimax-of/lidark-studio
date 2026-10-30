"""Banco de questões ENEM (Ciências Humanas / História): temas que voltam prova após prova, cada um virando um Short de
~50 s que termina na alternativa certa e emenda no começo (loop).

Regras de honestidade (valem para o roteiro e para a descrição):
- As provas e gabaritos oficiais são do INEP (citado na descrição). Nada de reproduzir imagens/charges/textos-base da prova.
- As perguntas daqui são AUTORAIS, no estilo da prova, sobre temas recorrentes — não são "a questão X do ENEM 20YY".
  Só citamos ano/número de questão quando estiver conferido (campo "refs" com refs_verified=True); hoje nenhum está.
- Nunca prometer "vai cair", "questão garantida", "gabarito vazado".
- Cada pauta ainda passa pela checagem de fatos da fila (verify_idea) e o roteiro pela checagem frase a frase.
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Any

from sqlmodel import select

from .db import session
from .jobs import JobContext, enqueue, handler
from .models import Channel, Idea

log = logging.getLogger("lidark.enem_bank")

INEP_URL = "https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enem/provas-e-gabaritos"
INEP_LINE = ("Provas e gabaritos oficiais do ENEM: INEP (gov.br/inep). A pergunta do vídeo é autoral, no estilo da prova, "
             "sobre um tema que aparece com frequência em Ciências Humanas — não é previsão do que vai cair.")
SHORT_SECONDS = 50
DAILY_LIMIT = 2  # pautas novas do banco por canal por dia (o resto do canal continua variado)

# weight = quanto o tema volta nas provas (3 = muito recorrente). refs = [{"year", "question", "note"}] só se conferido.
BANK: list[dict[str, Any]] = [
    {"key": "vacina-1904", "weight": 3, "enem": "Primeira República: urbanização e saúde pública",
     "title": "Revolta da Vacina: o povo era contra a vacina?",
     "pattern": "texto-base sobre a reforma urbana do Rio e a campanha sanitária; pede o motivo social da revolta",
     "question": "A Revolta da Vacina (Rio de Janeiro, 1904) é explicada, além da obrigatoriedade da vacina, por qual fator?",
     "alternatives": {"A": "A defesa da monarquia contra a República recém-proclamada",
                      "B": "A reforma urbana que demoliu cortiços e expulsou os pobres do centro",
                      "C": "A proibição do voto feminino pela Constituição de 1891",
                      "D": "A crise do café provocada pela quebra da Bolsa de 1929",
                      "E": "A chegada de imigrantes japoneses ao porto do Rio"},
     "answer": "B",
     "why": "O 'bota-abaixo' do prefeito Pereira Passos derrubou cortiços e afastou a população pobre do centro; a vacinação "
            "obrigatória contra a varíola, conduzida por Oswaldo Cruz, foi a gota d'água (10 a 16 de novembro de 1904).",
     "summary": "Em 1904, o Rio passava pela reforma urbana de Pereira Passos e pela campanha sanitária de Oswaldo Cruz. A lei "
                "da vacinação obrigatória contra a varíola (31/10/1904) detonou a revolta de 10 a 16 de novembro; o governo "
                "suspendeu a obrigatoriedade. O ENEM cobra a exclusão social na urbanização da Primeira República."},
    {"key": "canudos", "weight": 3, "enem": "Primeira República: movimentos sociais no campo",
     "title": "Por que a República destruiu Canudos?",
     "pattern": "trecho de 'Os Sertões' ou de jornal da época; pede como a República via o arraial",
     "question": "Por que o governo republicano tratou o arraial de Canudos (1896-1897) como uma ameaça?",
     "alternatives": {"A": "Porque Canudos era uma colônia estrangeira apoiada pela Inglaterra",
                      "B": "Porque o arraial cobrava impostos dos fazendeiros de São Paulo",
                      "C": "Porque era visto como foco monarquista e de fanatismo, que desafiava a ordem dos coronéis",
                      "D": "Porque os moradores queriam a independência do Nordeste com apoio da Argentina",
                      "E": "Porque Antônio Conselheiro era deputado da oposição no Congresso"},
     "answer": "C",
     "why": "A imprensa e o governo pintaram Canudos como reduto monarquista e fanático; na prática, o arraial atraía "
            "sertanejos pobres e esvaziava a mão de obra dos coronéis. Quatro expedições militares; o arraial caiu em outubro de 1897.",
     "summary": "Canudos, no sertão da Bahia, liderado por Antônio Conselheiro, derrotou três expedições militares entre 1896 e "
                "1897 e foi destruído pela quarta em outubro de 1897. Euclides da Cunha narrou o conflito em 'Os Sertões' "
                "(1902). O ENEM cobra Canudos como movimento social e o olhar da República sobre o sertão."},
    {"key": "quilombos", "weight": 3, "enem": "Escravidão e resistência no Brasil Colônia",
     "title": "Quilombo era só esconderijo de fugitivos?",
     "pattern": "texto-base sobre Palmares ou quilombos; pede o significado da resistência",
     "question": "Para a historiografia atual, os quilombos como Palmares representavam principalmente:",
     "alternatives": {"A": "Esconderijos temporários sem organização social própria",
                      "B": "Comunidades organizadas de resistência à escravidão, com economia e chefias próprias",
                      "C": "Aldeias fundadas por jesuítas para catequizar africanos",
                      "D": "Fazendas de senhores que libertavam seus escravizados",
                      "E": "Fortes militares portugueses contra invasões holandesas"},
     "answer": "B",
     "why": "Palmares, na Serra da Barriga (atual Alagoas), durou quase todo o século XVII, com agricultura, comércio e "
            "lideranças como Ganga Zumba e Zumbi; caiu em 1694, e Zumbi foi morto em 20 de novembro de 1695.",
     "summary": "O Quilombo dos Palmares resistiu a várias expedições até 1694, quando tropas de Domingos Jorge Velho destruíram "
                "o mocambo do Macaco. Zumbi foi morto em 20/11/1695 — hoje Dia da Consciência Negra. O ENEM cobra a "
                "resistência à escravidão, memória e patrimônio."},
    {"key": "clt-vargas", "weight": 3, "enem": "Era Vargas: trabalhismo e populismo",
     "title": "Vargas deu os direitos trabalhistas de presente?",
     "pattern": "propaganda do Estado Novo ou trecho da CLT; pede a relação entre direitos e controle dos sindicatos",
     "question": "A legislação trabalhista da Era Vargas, reunida na CLT (1943), combinava direitos com:",
     "alternatives": {"A": "A liberdade total de organização sindical, sem interferência do Estado",
                      "B": "O fim do salário mínimo e da carteira de trabalho",
                      "C": "O controle dos sindicatos pelo Estado e a imagem de 'pai dos pobres'",
                      "D": "A proibição de greves apenas para trabalhadores rurais",
                      "E": "A privatização da Previdência Social"},
     "answer": "C",
     "why": "Vargas atrelou os sindicatos ao Ministério do Trabalho (criado em 1930) enquanto ampliava direitos — e a "
            "propaganda vendia as leis como concessão pessoal, apagando lutas como a Greve Geral de 1917.",
     "summary": "A Consolidação das Leis do Trabalho (Decreto-Lei 5.452, de 1º de maio de 1943) reuniu leis trabalhistas dos anos "
                "1930 (Ministério do Trabalho em 1930, carteira de trabalho em 1932). Vargas atrelou os sindicatos ao Estado. "
                "Reivindicações operárias já apareciam na Greve Geral de 1917. O ENEM cobra trabalhismo e populismo."},
    {"key": "ai5-censura", "weight": 3, "enem": "Ditadura militar: autoritarismo e direitos civis",
     "title": "O que o AI-5 tirou dos brasileiros?",
     "pattern": "música censurada, capa de jornal ou trecho do ato; pede o efeito sobre os direitos",
     "question": "Uma das medidas do Ato Institucional nº 5 (13 de dezembro de 1968) foi:",
     "alternatives": {"A": "Garantir eleições diretas para presidente em 1969",
                      "B": "Suspender o habeas corpus para crimes políticos e permitir fechar o Congresso",
                      "C": "Revogar a censura prévia à imprensa e às artes",
                      "D": "Conceder anistia aos exilados políticos",
                      "E": "Criar o voto facultativo para analfabetos"},
     "answer": "B",
     "why": "O AI-5, de Costa e Silva, fechou o Congresso, permitiu cassações, suspendeu o habeas corpus em crimes "
            "políticos e ampliou a censura; vigorou até 1º de janeiro de 1979.",
     "summary": "O AI-5 foi decretado em 13/12/1968 pelo presidente Costa e Silva: fechou o Congresso, permitiu cassar mandatos, "
                "suspendeu o habeas corpus para crimes políticos e ampliou a censura. Foi revogado pela Emenda Constitucional "
                "nº 11 (1978), com efeito em 1º/1/1979. O ENEM cobra censura, repressão e direitos civis."},
    {"key": "ludismo", "weight": 2, "enem": "Revolução Industrial e mundo do trabalho",
     "title": "Os ludistas odiavam máquinas?",
     "pattern": "texto-base sobre fábricas inglesas; pede o sentido da destruição de máquinas",
     "question": "A destruição de máquinas pelos ludistas na Inglaterra (1811-1816) expressava sobretudo:",
     "alternatives": {"A": "Uma rejeição religiosa a qualquer tecnologia",
                      "B": "O protesto contra desemprego, salários baixos e as condições de trabalho nas fábricas",
                      "C": "Uma campanha do governo inglês para reduzir a produção têxtil",
                      "D": "A defesa dos interesses dos donos das fábricas",
                      "E": "A luta pelo fim da monarquia britânica"},
     "answer": "B",
     "why": "Os ludistas atacavam teares que baixavam salários e tiravam empregos; em 1812 o Parlamento tornou a destruição de "
            "máquinas crime punível com morte. Depois vieram as trade unions.",
     "summary": "Entre 1811 e 1816, trabalhadores têxteis ingleses (ludistas) destruíram teares em protesto contra salários "
                "baixos, desemprego e condições de trabalho; em 1812 a destruição de máquinas virou crime punível com morte. "
                "O ENEM cobra Revolução Industrial e relações de trabalho."},
    {"key": "atenas-cidadania", "weight": 3, "enem": "Antiguidade clássica: democracia e cidadania",
     "title": "Quem podia votar na democracia de Atenas?",
     "pattern": "comparação entre a democracia ateniense e a atual; pede quem era cidadão",
     "question": "Na democracia ateniense do século V a.C., o direito de participar da assembleia (Eclésia) era restrito a:",
     "alternatives": {"A": "Todos os moradores da cidade, inclusive estrangeiros",
                      "B": "Homens e mulheres livres maiores de 18 anos",
                      "C": "Homens adultos, livres e filhos de pais atenienses",
                      "D": "Sacerdotes e militares de alta patente",
                      "E": "Proprietários de escravizados nascidos em Esparta"},
     "answer": "C",
     "why": "Mulheres, escravizados e estrangeiros (metecos) ficavam de fora; pela lei de Péricles (451 a.C.), cidadão era o "
            "filho de pai e mãe atenienses — uma minoria da população.",
     "summary": "Em Atenas, no século V a.C., só homens adultos, livres e filhos de pai e mãe atenienses (lei de Péricles, 451 "
                "a.C.) eram cidadãos; mulheres, escravizados e metecos não votavam. A democracia era direta, na Eclésia. O "
                "ENEM cobra cidadania e a comparação com a democracia atual."},
    {"key": "feudalismo", "weight": 2, "enem": "Idade Média: sociedade feudal",
     "title": "Servo medieval era escravo?",
     "pattern": "texto sobre obrigações camponesas; pede a diferença entre servidão e escravidão",
     "question": "Na sociedade feudal europeia, o servo se diferenciava do escravizado porque:",
     "alternatives": {"A": "Podia ser vendido livremente em mercados",
                      "B": "Era preso à terra e devia obrigações ao senhor, mas não era propriedade dele",
                      "C": "Recebia salário fixo em moedas de ouro",
                      "D": "Tinha o direito de votar na escolha do rei",
                      "E": "Não pagava nenhum tributo à Igreja"},
     "answer": "B",
     "why": "O servo devia corveia (trabalho nas terras do senhor), talha (parte da produção) e outras taxas, e não podia "
            "abandonar o feudo — mas não era uma mercadoria, como o escravizado.",
     "summary": "Na Europa feudal, os servos eram presos à terra e deviam obrigações ao senhor (corveia, talha, banalidades), "
                "além do dízimo à Igreja, mas não eram propriedade do senhor. O ENEM cobra as relações sociais da Idade Média."},
    {"key": "lei-de-terras", "weight": 2, "enem": "Brasil Império: questão agrária",
     "title": "A lei de 1850 que fechou o acesso à terra",
     "pattern": "trecho da Lei 601 ou dado de concentração fundiária; pede a consequência social",
     "question": "A Lei de Terras de 1850 contribuiu para a concentração fundiária no Brasil porque:",
     "alternatives": {"A": "Distribuiu terras gratuitamente aos ex-escravizados",
                      "B": "Determinou que terras devolutas só poderiam ser obtidas por compra",
                      "C": "Proibiu a venda de terras a brasileiros",
                      "D": "Criou a reforma agrária no Segundo Reinado",
                      "E": "Transferiu as terras da Igreja para os indígenas"},
     "answer": "B",
     "why": "A Lei 601, de 18 de setembro de 1850, exigiu compra para ter terra — no mesmo ano em que a Lei Eusébio de "
            "Queirós proibiu o tráfico de africanos. Posseiros, libertos e imigrantes pobres ficaram de fora.",
     "summary": "A Lei de Terras (Lei 601, de 18/9/1850) determinou que terras devolutas só seriam obtidas por compra, no mesmo "
                "ano da Lei Eusébio de Queirós (fim do tráfico). Dificultou o acesso à terra de pobres e libertos. O ENEM "
                "cobra a questão agrária e a relação com a mão de obra."},
    {"key": "coronelismo", "weight": 3, "enem": "Primeira República: coronelismo e voto de cabresto",
     "title": "Voto de cabresto: como o coronel ganhava a eleição",
     "pattern": "charge ou texto sobre eleições da República Velha; pede o mecanismo de controle",
     "question": "O 'voto de cabresto' na Primeira República era possível principalmente porque:",
     "alternatives": {"A": "O voto era secreto e eletrônico",
                      "B": "O voto era aberto, e os coronéis controlavam trabalhadores e eleitores locais",
                      "C": "Somente mulheres podiam votar",
                      "D": "As eleições eram organizadas pela Justiça Eleitoral independente",
                      "E": "Os partidos nacionais proibiam alianças regionais"},
     "answer": "B",
     "why": "Com voto aberto, o eleitor votava sob os olhos do coronel; a política dos governadores (Campos Sales) ligava esses "
            "votos ao governo federal. O voto secreto só veio com o Código Eleitoral de 1932.",
     "summary": "Na Primeira República (1889-1930), o voto era aberto e os coronéis controlavam o eleitorado local ('voto de "
                "cabresto'), base da política dos governadores de Campos Sales. O Código Eleitoral de 1932 trouxe o voto "
                "secreto e o feminino. O ENEM cobra coronelismo e oligarquias."},
    {"key": "constituicao-88", "weight": 3, "enem": "Constituição de 1988 e cidadania",
     "title": "O que a Constituição de 1988 trouxe de novo?",
     "pattern": "artigo da Constituição; pede a ampliação de direitos",
     "question": "Qual destas mudanças foi trazida pela Constituição de 1988, a 'Constituição Cidadã'?",
     "alternatives": {"A": "O fim do voto direto para presidente",
                      "B": "A censura prévia a jornais e emissoras",
                      "C": "O voto facultativo para analfabetos e jovens de 16 e 17 anos",
                      "D": "A volta da monarquia parlamentarista",
                      "E": "A proibição de partidos de oposição"},
     "answer": "C",
     "why": "A Constituição promulgada em 5 de outubro de 1988 também tornou o racismo crime inafiançável, criou o SUS e "
            "reconheceu os direitos originários dos povos indígenas às suas terras.",
     "summary": "A Constituição de 5/10/1988, chamada de 'Cidadã' por Ulysses Guimarães, garantiu voto facultativo a analfabetos "
                "e a jovens de 16 e 17 anos, tornou o racismo crime inafiançável e imprescritível, criou o SUS e reconheceu os "
                "direitos indígenas às terras (art. 231). O ENEM cobra cidadania e direitos."},
    {"key": "partilha-africa", "weight": 2, "enem": "Imperialismo e neocolonialismo",
     "title": "Quem desenhou as fronteiras da África?",
     "pattern": "mapa da partilha ou texto sobre o neocolonialismo; pede a consequência das fronteiras",
     "question": "A Conferência de Berlim (1884-1885) é associada a quais consequências para a África?",
     "alternatives": {"A": "A independência de todos os países africanos",
                      "B": "Regras europeias de partilha que geraram fronteiras artificiais, cortando povos e reinos",
                      "C": "A união dos reinos africanos num só império",
                      "D": "O fim do comércio entre Europa e África",
                      "E": "A criação da ONU para proteger os povos africanos"},
     "answer": "B",
     "why": "Nenhum africano estava à mesa: as potências europeias definiram regras de ocupação, e as fronteiras traçadas depois "
            "cortaram povos e reinos. Em 1914, só a Etiópia e a Libéria eram independentes.",
     "summary": "A Conferência de Berlim (1884-1885) reuniu potências europeias, os EUA e o Império Otomano para definir regras da "
                "partilha da África, sem representantes africanos. Em 1914, só Etiópia e Libéria eram independentes. O ENEM "
                "cobra o imperialismo do século XIX e suas consequências."},
    {"key": "declaracao-1789", "weight": 2, "enem": "Revolução Francesa e Iluminismo",
     "title": "O documento de 1789 que ainda está na sua vida",
     "pattern": "trecho da Declaração dos Direitos do Homem e do Cidadão; pede o princípio iluminista",
     "question": "A Declaração dos Direitos do Homem e do Cidadão (1789) expressa qual ideia iluminista?",
     "alternatives": {"A": "O direito divino dos reis de governar sem limites",
                      "B": "A divisão da sociedade em ordens com privilégios de nascimento",
                      "C": "A igualdade de direitos dos cidadãos perante a lei e a soberania da nação",
                      "D": "A obrigação de todos seguirem a religião oficial",
                      "E": "O fim da propriedade privada"},
     "answer": "C",
     "why": "Aprovada em agosto de 1789, logo depois da queda da Bastilha (14 de julho), a Declaração atacou os privilégios do "
            "Antigo Regime: 'os homens nascem e permanecem livres e iguais em direitos'.",
     "summary": "A Declaração dos Direitos do Homem e do Cidadão foi aprovada em agosto de 1789, após a queda da Bastilha (14/7/1789). "
                "Afirmou igualdade de direitos perante a lei e a soberania nacional, contra os privilégios do Antigo Regime. O "
                "ENEM cobra os ideais iluministas e o fim do Antigo Regime."},
    {"key": "guerra-fria", "weight": 3, "enem": "Guerra Fria: bipolarização",
     "title": "Por que a Guerra Fria foi 'fria'?",
     "pattern": "charge sobre a corrida armamentista; pede a lógica da bipolarização",
     "question": "A Guerra Fria (1947-1991) recebeu esse nome porque:",
     "alternatives": {"A": "Aconteceu apenas nos países do Polo Norte",
                      "B": "EUA e URSS disputaram influência sem guerra direta entre si, mas com conflitos indiretos",
                      "C": "Não houve nenhum conflito armado no mundo nesse período",
                      "D": "Foi uma guerra comercial só entre Europa e Japão",
                      "E": "Terminou com a vitória militar da URSS sobre os EUA"},
     "answer": "B",
     "why": "As superpotências nunca se enfrentaram diretamente — o medo nuclear segurou —, mas houve guerras ligadas à disputa: "
            "Coreia (1950-1953), Vietnã (até 1975), Afeganistão (1979-1989); a Crise dos Mísseis (1962) quase virou guerra nuclear.",
     "summary": "Na Guerra Fria, EUA e URSS disputaram influência sem guerra direta entre si; houve conflitos indiretos como Coreia "
                "(1950-1953), Vietnã (até 1975) e Afeganistão (1979-1989). A Crise dos Mísseis (outubro de 1962) levou o mundo à "
                "beira da guerra nuclear. O ENEM cobra bipolarização e corrida armamentista."},
]
for _it in BANK:  # nenhuma referência a questão/ano específico foi conferida — o roteiro não pode citar uma
    _it.setdefault("refs", [])
    _it.setdefault("refs_verified", False)

_BY_KEY = {it["key"]: it for it in BANK}


def get(key: str) -> dict[str, Any] | None:
    return _BY_KEY.get(key)


def used_keys(channel_id: int) -> set[str]:
    with session() as s:
        ideas = s.exec(select(Idea).where(Idea.channel_id == channel_id)).all()
    return {str(t)[10:] for i in ideas for t in (i.tags or []) if str(t).startswith("enem_bank:")}


def available(channel_id: int) -> list[dict[str, Any]]:
    used = used_keys(channel_id)
    return [it for it in BANK if it["key"] not in used]


def prompt_material(ch: Channel, k: int = 5) -> list[str]:
    """Linhas de inspiração para a descoberta de pautas (temas recorrentes ainda não usados)."""
    pool = available(ch.id)
    pool.sort(key=lambda it: -it["weight"] - random.random() * 2)
    return [f"- (tema recorrente no ENEM, {it['enem']}) {it['title']} — {it['why'][:160]}" for it in pool[:k]]


def _alts(it: dict[str, Any]) -> str:
    return " | ".join(f"{k}) {v}" for k, v in it["alternatives"].items())


def script_extra(key: str, fmt: str = "short") -> str:
    """Instruções do roteiro para uma pauta do banco (Short de ~50 s que termina na alternativa certa)."""
    it = get(key)
    if not it:
        return ""
    refs = ("; ".join(f"{r.get('year')} questão {r.get('question')}" for r in it["refs"])
            if it.get("refs_verified") and it.get("refs") else "")
    return f"""PAUTA DO BANCO DE QUESTÕES ENEM (tema recorrente em Ciências Humanas — provas oficiais: INEP):
- Tema: {it['enem']}. Como costuma aparecer na prova: {it['pattern']}.
- Pergunta (AUTORAL, no estilo da prova): {it['question']}
- Alternativas: {_alts(it)}
- Correta: {it['answer']} — {it['why']}
{('- Referência conferida: ' + refs) if refs else '- NÃO cite ano nem número de questão: diga "no estilo do ENEM" ou "como o ENEM costuma cobrar" (nunca "a questão X de 20YY").'}
ROTEIRO (~{SHORT_SECONDS} s, Short):
- Cena 1: o gancho (a pegadinha ou o erro comum sobre o tema), na abertura pedida em VARIEDADE.
- Uma cena com o gráfico "list" mostrando a pergunta curta como "title" e as 5 alternativas como "items" ("A) ..."); a
  narração lê a pergunta e só 1-2 alternativas-armadilha, rápido. Desafie o espectador a responder antes da revelação.
- 2 a 3 cenas de contexto com os fatos que levam à resposta (só fatos das fontes).
- Revelação: "a resposta é a letra {it['answer']}" + o porquê em 1 frase (delivery "slow", pausa antes).
- O vídeo é em LOOP: depois da revelação e do CTA curto, a última frase emenda na pergunta do começo.
- PROIBIDO: "vai cair", "cai com certeza", "questão garantida", "gabarito vazado"; reproduzir imagem, charge ou texto-base
  da prova. Título com o ASSUNTO primeiro (o título sugerido é só ponto de partida)."""


def create_ideas(ch: Channel, n: int = DAILY_LIMIT, ctx: JobContext | None = None) -> list[int]:
    """Cria até n pautas novas do banco para o canal ENEM (limite diário, sem repetir tema) e põe na checagem."""
    from .content import is_enem_channel
    if not is_enem_channel(ch):
        return []
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    with session() as s:
        today = [i for i in s.exec(select(Idea).where(Idea.channel_id == ch.id, Idea.origin == "enem_bank")).all()
                 if i.created_at and (i.created_at if i.created_at.tzinfo else i.created_at.replace(tzinfo=timezone.utc)) >= start]
    left = max(0, min(n, DAILY_LIMIT) - len(today))
    pool = available(ch.id)
    if not left or not pool:
        return []
    pool.sort(key=lambda it: -it["weight"] - random.random() * 1.5)  # os mais recorrentes primeiro, sem ordem fixa
    created = []
    for it in pool[:left]:
        with session() as s:
            idea = Idea(channel_id=ch.id, title=it["title"], format="short", origin="enem_bank", status="new",
                        angle=f"{it['question']} (resposta: {it['answer']}) — {it['why']}", summary=it["summary"],
                        tags=[it["enem"], f"enem_bank:{it['key']}", "loop", f"segundos:{SHORT_SECONDS}"],
                        sources=[{"title": "INEP — provas e gabaritos do ENEM", "url": INEP_URL, "kind": "oficial"}])
            s.add(idea)
            s.commit()
            s.refresh(idea)
            created.append(idea.id)
        enqueue("manual_idea", title=f"Checar pauta do banco ENEM: {it['title']}", channel_id=ch.id, ref_id=idea.id)
        if ctx:
            ctx.log(f"{ch.name}: pauta do banco ENEM → {it['title']}")
    return created


@handler("enem_bank_ideas")
def job_enem_bank_ideas(ctx: JobContext) -> dict:
    with session() as s:
        chans = [s.get(Channel, ctx.channel_id)] if ctx.channel_id else s.exec(select(Channel)).all()
    out = {}
    for ch in chans:
        if ch:
            try:
                out[ch.id] = create_ideas(ch, int(ctx.payload.get("count") or DAILY_LIMIT), ctx)
            except Exception as e:  # noqa: BLE001
                ctx.log(f"{ch.name}: {e}")
    return {"created": out}
