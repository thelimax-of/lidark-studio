"""Campanha ENEM 2026: banco de pautas de História que mais caem na prova, pacote pronto para lançar e SEO honesto.

Os temas vêm de levantamentos das provas (SAS "Raio-X do Enem" 2009-2023: Idade Contemporânea 15,4%, Brasil Colônia
12,8%, Brasil Império 11,5%, História Política 10,6%, Patrimônio e memória 9,2%, Primeira República 6,2%; Aprova Total
2026: Brasil Colônia, Estado Novo/Populismo, Idade Média, Tempo Presente e Idade Moderna no topo). Cada pauta traz o
resumo factual (datas e nomes conferidos) — a checagem de fatos da fila ainda roda em cima dele antes de virar roteiro.

As pautas entram como pautas APROVADAS da campanha; quem decide quando cada uma vira vídeo continua sendo o piloto
automático (horários, espaço mínimo e limite diário de posting_times) e o sorteio de variedade de cada roteiro.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlmodel import select

from .db import session
from .jobs import JobContext, enqueue, handler
from .models import Channel, Idea

log = logging.getLogger("lidark.enem")

CAMPAIGN_ID = "enem-revisao-2026"

# estrutura forçada só quando o tema pede (mito, personagem, cena de clímax); nas demais o sorteio de variedade decide.
# weight = quanto o tema costuma cair (3 = topo dos levantamentos) — define a ordem de produção sugerida.
SHORTS: list[dict[str, Any]] = [
    {"key": "abolicao", "weight": 3, "structure": "mito_verdade", "enem": "Escravidão e abolição (Brasil Império)",
     "title": "Lei Áurea: a abolição foi mesmo um presente da princesa Isabel?",
     "angle": "Todo mundo aprende que a princesa Isabel 'libertou os escravos'. A assinatura foi o último passo de décadas de luta.",
     "summary": "A Lei Áurea foi assinada em 13 de maio de 1888 pela princesa Isabel, regente do Império. Antes vieram a Lei "
                "Eusébio de Queirós (1850, fim do tráfico), a Lei do Ventre Livre (1871) e a dos Sexagenários (1885); Ceará e "
                "Amazonas aboliram a escravidão em 1884; fugas em massa e quilombos abolicionistas (como o Jabaquara, em Santos) "
                "e abolicionistas como Luiz Gama, André Rebouças e José do Patrocínio pressionaram o fim. O Brasil foi o último "
                "país das Américas a abolir. O ENEM cobra a abolição como processo e a falta de integração dos libertos."},
    {"key": "palmares", "weight": 3, "enem": "Resistência escrava e Brasil Colônia",
     "title": "Palmares: o quilombo que resistiu por quase 100 anos",
     "angle": "Um território livre no meio da colônia açucareira que derrotou expedições por décadas.",
     "summary": "O Quilombo dos Palmares, na Serra da Barriga (atual Alagoas), formou-se no fim do século XVI/início do XVII e "
                "resistiu a várias expedições até 1694, quando tropas comandadas pelo bandeirante Domingos Jorge Velho "
                "destruíram o mocambo do Macaco. Zumbi foi morto em 20 de novembro de 1695; a data virou o Dia da Consciência "
                "Negra, feriado nacional desde 2024. O ENEM cobra resistência à escravidão, memória e patrimônio."},
    {"key": "mao-de-obra", "weight": 3, "structure": "pergunta", "enem": "Brasil Colônia: trabalho e economia açucareira",
     "title": "Por que a colônia trocou o trabalho indígena pelo africano?",
     "angle": "A resposta da escola ('indígena não servia para trabalhar') é um mito; a real é epidemia, lei e lucro.",
     "summary": "A escravização indígena foi ampla no Brasil Colônia — bandeirantes caçaram indígenas até o século XVIII. "
                "Epidemias dizimaram aldeias, jesuítas e leis da Coroa (como a lei de 1570 de D. Sebastião) restringiram a "
                "escravização indígena, e o tráfico atlântico de africanos era um negócio lucrativo para comerciantes e para a "
                "Coroa, que cobrava impostos. O ENEM cobra a relação entre economia açucareira, tráfico e trabalho compulsório."},
    {"key": "independencia", "weight": 3, "structure": "mito_verdade", "enem": "Independência e Primeiro Reinado (Brasil Império)",
     "title": "A Independência do Brasil não foi pacífica: teve guerra",
     "angle": "Depois do 7 de setembro, houve batalhas na Bahia, no Piauí, no Maranhão e no Pará.",
     "summary": "Depois de 7 de setembro de 1822, tropas fiéis a Portugal resistiram na Bahia, no Maranhão, no Piauí (Batalha "
                "do Jenipapo, 13 de março de 1823), no Pará e na Cisplatina. Na Bahia, a guerra só terminou em 2 de julho de "
                "1823, data comemorada até hoje. Portugal só reconheceu a independência em 1825, com o Brasil pagando 2 milhões "
                "de libras. O ENEM cobra a independência como processo, com conflitos e permanências (monarquia, escravidão)."},
    {"key": "lei-terras", "weight": 2, "enem": "Questão agrária no Brasil Império",
     "title": "1850: o ano em que a terra no Brasil virou mercadoria",
     "angle": "A mesma década que fechou o tráfico de escravizados fechou o acesso à terra para os pobres.",
     "summary": "A Lei de Terras (Lei 601, de 18 de setembro de 1850) determinou que as terras devolutas só poderiam ser "
                "obtidas por compra. No mesmo ano, a Lei Eusébio de Queirós proibiu o tráfico de africanos. A lei dificultou "
                "o acesso à terra para posseiros, libertos e imigrantes pobres e está na raiz da concentração fundiária. "
                "O ENEM cobra a questão agrária e sua relação com a mão de obra."},
    {"key": "tiradentes", "weight": 2, "structure": "detalhe", "enem": "Inconfidência Mineira, Iluminismo e memória",
     "title": "Ninguém sabe como era o rosto de Tiradentes",
     "angle": "A imagem de barba e cabelo comprido, parecida com Jesus, foi criada um século depois — pela República.",
     "summary": "Não existe retrato de Tiradentes (Joaquim José da Silva Xavier, alferes) feito em vida. Ele foi enforcado no "
                "Rio de Janeiro em 21 de abril de 1792, após a Inconfidência Mineira (1789), movimento inspirado no Iluminismo "
                "e na independência dos EUA e motivado pela cobrança da derrama. A imagem heroica, semelhante a Cristo, foi "
                "construída depois da Proclamação da República (1889), como no quadro 'Tiradentes Esquartejado', de Pedro "
                "Américo (1893). O ENEM cobra a construção de heróis e a memória histórica."},
    {"key": "capoeira", "weight": 2, "structure": "detalhe", "enem": "Patrimônio, cultura afro-brasileira e Primeira República",
     "title": "Capoeira já foi crime no Brasil — estava no Código Penal",
     "angle": "Dois anos depois da abolição, a lei passou a punir a capoeira com prisão.",
     "summary": "O Código Penal de 1890 (art. 402) punia a 'capoeiragem' com prisão, parte da repressão à cultura "
                "afro-brasileira no pós-abolição. Nos anos 1930, Mestre Bimba abriu em Salvador uma academia que ajudou a "
                "legitimar a prática. Em 2008 a capoeira foi registrada como patrimônio cultural imaterial pelo Iphan, e em "
                "2014 a roda de capoeira virou patrimônio imaterial da humanidade pela Unesco. O ENEM cobra patrimônio e "
                "identidade cultural."},
    {"key": "canudos", "weight": 2, "structure": "in_media_res", "enem": "Primeira República: movimentos sociais",
     "title": "Canudos: o arraial que derrotou três expedições do Exército",
     "angle": "Sertanejos de Antônio Conselheiro venceram três ataques antes de o arraial ser destruído.",
     "summary": "Canudos, no sertão da Bahia, era liderado por Antônio Conselheiro. Entre 1896 e 1897, três expedições "
                "militares foram derrotadas — na terceira morreu o coronel Moreira César. A quarta expedição destruiu o arraial "
                "em outubro de 1897. Euclides da Cunha narrou o conflito em 'Os Sertões' (1902). O ENEM cobra Canudos como "
                "movimento social e a visão da República sobre o sertão."},
    {"key": "vacina", "weight": 2, "enem": "Primeira República: urbanização e saúde pública",
     "title": "Revolta da Vacina: o Rio não se revoltou só contra a vacina",
     "angle": "A vacina obrigatória foi a gota d'água de uma reforma urbana que expulsou os pobres do centro.",
     "summary": "Em 1904, o Rio de Janeiro passava pela reforma urbana do prefeito Pereira Passos (o 'bota-abaixo' de "
                "cortiços) e pela campanha sanitária de Oswaldo Cruz. A lei da vacinação obrigatória contra a varíola, de "
                "31 de outubro de 1904, detonou a revolta de 10 a 16 de novembro; o governo suspendeu a obrigatoriedade. "
                "O ENEM cobra urbanização, exclusão social e saúde pública na Primeira República."},
    {"key": "cafe-com-leite", "weight": 2, "structure": "mito_verdade", "enem": "Primeira República: coronelismo e oligarquias",
     "title": "Café com leite: SP e MG não se revezaram sempre no poder",
     "angle": "O revezamento perfeito é simplificação; o que segurava o sistema era a política dos governadores.",
     "summary": "A 'política do café com leite' (1894-1930) não foi um revezamento perfeito entre São Paulo e Minas Gerais: "
                "Hermes da Fonseca (RS, 1910) e Epitácio Pessoa (PB, 1919) também foram presidentes. O sistema se apoiava na "
                "política dos governadores de Campos Sales, no coronelismo e no voto aberto ('voto de cabresto'). Em 1929, "
                "Washington Luís indicou o paulista Júlio Prestes, a aliança rompeu e veio a Revolução de 1930. O ENEM cobra "
                "coronelismo e as oligarquias."},
    {"key": "clt", "weight": 3, "structure": "mito_verdade", "enem": "Era Vargas: trabalhismo e populismo",
     "title": "A CLT não caiu do céu: a luta antes de Vargas",
     "angle": "Vargas reuniu as leis e controlou os sindicatos — mas as reivindicações vinham de greves anteriores.",
     "summary": "A Consolidação das Leis do Trabalho (Decreto-Lei 5.452, de 1º de maio de 1943) reuniu leis trabalhistas "
                "criadas desde o início dos anos 1930 (Ministério do Trabalho em 1930, carteira de trabalho em 1932). As "
                "reivindicações já apareciam em lutas operárias como a Greve Geral de 1917 em São Paulo. Ao mesmo tempo, Vargas "
                "atrelou os sindicatos ao Estado. O ENEM cobra trabalhismo, populismo e a imagem de 'pai dos pobres'."},
    {"key": "voz-do-brasil", "weight": 3, "structure": "detalhe", "enem": "Estado Novo: propaganda e censura",
     "title": "A Voz do Brasil nasceu na Era Vargas — e não por acaso",
     "angle": "O programa que ainda toca no rádio às 19h nasceu como ferramenta de propaganda do governo.",
     "summary": "O programa oficial de rádio do governo federal surgiu em 1935, com Getúlio Vargas, e virou 'Hora do Brasil'; "
                "no Estado Novo (1937-1945) passou a ser transmitido obrigatoriamente. Em 1939 Vargas criou o DIP "
                "(Departamento de Imprensa e Propaganda), que fazia censura e propaganda do regime. Hoje o programa se chama "
                "'A Voz do Brasil'. O ENEM cobra o uso dos meios de comunicação pelo Estado Novo."},
    {"key": "voto-feminino", "weight": 2, "structure": "personagem", "enem": "Cidadania e voto feminino (Era Vargas)",
     "title": "Celina Viana: a primeira eleitora do Brasil votou antes da lei",
     "angle": "Uma professora de Mossoró votou em 1928, quatro anos antes do voto feminino no país.",
     "summary": "Celina Guimarães Viana, professora de Mossoró (RN), alistou-se como eleitora em 1927 graças a uma lei "
                "estadual do Rio Grande do Norte e é lembrada como a primeira eleitora do Brasil. O voto feminino em todo o "
                "país veio com o Código Eleitoral de 1932, no governo Vargas, após a luta de sufragistas como Bertha Lutz, e "
                "foi confirmado na Constituição de 1934. O ENEM cobra cidadania e ampliação de direitos."},
    {"key": "ai5", "weight": 3, "structure": "in_media_res", "enem": "Ditadura militar: autoritarismo e direitos",
     "title": "AI-5: a noite em que a ditadura fechou o Congresso",
     "angle": "13 de dezembro de 1968: o ato que suspendeu o habeas corpus e endureceu o regime.",
     "summary": "O Ato Institucional nº 5 foi decretado em 13 de dezembro de 1968 pelo presidente Costa e Silva. Fechou o "
                "Congresso Nacional, permitiu cassar mandatos, suspendeu o habeas corpus para crimes políticos e ampliou a "
                "censura. Vigorou até 1º de janeiro de 1979, revogado pela Emenda Constitucional nº 11 de 1978. O ENEM cobra "
                "o AI-5 em questões sobre censura, repressão e direitos civis."},
    {"key": "milagre", "weight": 2, "structure": "comparacao", "enem": "Ditadura militar: milagre econômico e desigualdade",
     "title": "Milagre econômico: o Brasil crescia 10% ao ano — e quem pagou?",
     "angle": "O PIB disparou, mas a desigualdade e a dívida externa também.",
     "summary": "Entre 1968 e 1973, o PIB brasileiro cresceu em média cerca de 10% ao ano. No mesmo período a concentração "
                "de renda aumentou, o salário mínimo perdeu poder de compra e a dívida externa cresceu. Com a crise do "
                "petróleo de 1973, o modelo se esgotou. A ideia de 'fazer o bolo crescer para depois dividir' é associada à "
                "política econômica de Delfim Netto. O ENEM cobra o milagre e suas contradições sociais."},
    {"key": "diretas", "weight": 2, "enem": "Redemocratização (tempo presente)",
     "title": "Diretas Já: milhões nas ruas — e a emenda perdeu",
     "angle": "O maior movimento de rua da época não conseguiu aprovar a eleição direta em 1984.",
     "summary": "Em 1984, comícios das Diretas Já reuniram multidões, como na Candelária (Rio, 10 de abril) e no Vale do "
                "Anhangabaú (São Paulo, 16 de abril). A Emenda Dante de Oliveira foi votada em 25 de abril de 1984: 298 votos "
                "a favor, 65 contra, 3 abstenções e 113 ausentes — faltaram 22 votos para os dois terços. Tancredo Neves foi "
                "eleito de forma indireta pelo Colégio Eleitoral em 15 de janeiro de 1985. O ENEM cobra a redemocratização."},
    {"key": "constituicao", "weight": 3, "structure": "pergunta", "enem": "Constituição de 1988 e cidadania",
     "title": "Por que a Constituição de 1988 é chamada de 'Cidadã'?",
     "angle": "O apelido veio de Ulysses Guimarães — e de direitos que nenhuma Constituição anterior tinha.",
     "summary": "A Constituição foi promulgada em 5 de outubro de 1988; Ulysses Guimarães, presidente da Assembleia "
                "Constituinte, a chamou de 'Constituição Cidadã'. Ela garantiu voto facultativo a analfabetos e a jovens de "
                "16 e 17 anos, tornou o racismo crime inafiançável e imprescritível, criou o SUS e reconheceu os direitos "
                "originários dos povos indígenas às suas terras (art. 231). O ENEM cobra cidadania e direitos."},
    {"key": "brioches", "weight": 3, "structure": "mito_verdade", "enem": "Revolução Francesa e Antigo Regime",
     "title": "'Que comam brioches': Maria Antonieta nunca disse isso",
     "angle": "A frase aparece num livro de Rousseau escrito quando ela ainda era criança na Áustria.",
     "summary": "A frase 'que comam brioches' aparece nas 'Confissões' de Rousseau, atribuída a 'uma grande princesa', em "
                "trecho escrito quando Maria Antonieta (nascida em 1755) ainda vivia na Áustria — ela só chegou à França em "
                "1770. A frase virou propaganda contra a monarquia. A Revolução começou com a queda da Bastilha (14 de julho "
                "de 1789), veio a Declaração dos Direitos do Homem e do Cidadão (agosto de 1789), e a rainha foi guilhotinada "
                "em 16 de outubro de 1793. O ENEM cobra o fim do Antigo Regime e os ideais iluministas."},
    {"key": "terra-plana", "weight": 3, "structure": "mito_verdade", "enem": "Idade Média: Igreja, saber e o mito da 'Idade das Trevas'",
     "title": "Na Idade Média, todo mundo achava a Terra plana? É mito",
     "angle": "Os estudiosos medievais sabiam que a Terra era redonda; o mito é do século XIX.",
     "summary": "Estudiosos medievais sabiam que a Terra era esférica: Beda (século VIII) a descreveu como um globo, e o "
                "tratado 'De sphaera', de Sacrobosco (século XIII), foi usado por séculos nas universidades. A ideia de que "
                "os medievais acreditavam numa Terra plana se popularizou no século XIX, como na biografia de Colombo escrita "
                "por Washington Irving (1828). O ENEM cobra a Idade Média além do estereótipo de 'Idade das Trevas'."},
    {"key": "ludistas", "weight": 2, "enem": "Revolução Industrial e mundo do trabalho",
     "title": "Ludistas: quebrar máquinas não era ódio à tecnologia",
     "angle": "Os operários ingleses atacavam teares por salário e emprego — e a pena virou morte.",
     "summary": "Entre 1811 e 1816, na Inglaterra, trabalhadores têxteis conhecidos como ludistas destruíram teares em "
                "protesto contra salários baixos, desemprego e as condições de trabalho da Revolução Industrial. Em 1812, o "
                "Parlamento tornou a destruição de máquinas crime punível com morte. Jornadas longas e trabalho infantil "
                "marcaram as fábricas, e os trabalhadores se organizaram em associações (trade unions). O ENEM cobra a "
                "Revolução Industrial e as relações de trabalho."},
    {"key": "atenas", "weight": 2, "structure": "comparacao", "enem": "Antiguidade clássica: democracia e cidadania",
     "title": "A democracia de Atenas deixava a maioria de fora",
     "angle": "Mulheres, escravizados e estrangeiros não votavam: só uma parcela pequena era cidadã.",
     "summary": "Na Atenas do século V a.C., só homens adultos, livres e filhos de pai e mãe atenienses (lei de Péricles, "
                "451 a.C.) eram cidadãos. Mulheres, escravizados e estrangeiros (metecos) ficavam de fora — os cidadãos eram "
                "uma minoria da população. A democracia era direta, com votações na Eclésia, e existia o ostracismo. O ENEM "
                "cobra o conceito de cidadania e a comparação com a democracia atual."},
    {"key": "guerra-fria", "weight": 3, "structure": "in_media_res", "enem": "Guerra Fria: bipolarização",
     "title": "Guerra Fria: os 13 dias em que o mundo quase acabou",
     "angle": "Outubro de 1962, mísseis em Cuba — e a 'guerra fria' que teve muitas guerras quentes.",
     "summary": "Em outubro de 1962, a descoberta de mísseis soviéticos em Cuba levou EUA e URSS à beira de uma guerra "
                "nuclear (Crise dos Mísseis, cerca de 13 dias). As duas potências não se enfrentaram diretamente, mas houve "
                "guerras ligadas à disputa: Coreia (1950-1953), Vietnã (até 1975) e Afeganistão (1979-1989). O Muro de Berlim "
                "existiu de 1961 a 1989. O ENEM cobra bipolarização, corrida armamentista e o impacto na América Latina."},
    {"key": "feb", "weight": 2, "enem": "Segunda Guerra Mundial e o fim do Estado Novo",
     "title": "O Brasil lutou na Segunda Guerra: a FEB na Itália",
     "angle": "Uma ditadura mandou soldados lutarem contra o fascismo — e isso ajudou a derrubar a própria ditadura.",
     "summary": "O Brasil declarou guerra à Alemanha e à Itália em agosto de 1942, depois de ataques de submarinos a navios "
                "brasileiros. A Força Expedicionária Brasileira enviou cerca de 25 mil militares à Itália (1944-1945) e venceu "
                "em Monte Castelo em 21 de fevereiro de 1945; o lema era 'a cobra vai fumar'. Lutar contra o fascismo sendo "
                "uma ditadura expôs a contradição do Estado Novo, que acabou em 1945. O ENEM cobra a Era Vargas e a guerra."},
    {"key": "berlim-africa", "weight": 2, "structure": "detalhe", "enem": "Imperialismo e neocolonialismo",
     "title": "As fronteiras da África foram traçadas por europeus",
     "angle": "Na Conferência de Berlim não havia nenhum africano à mesa.",
     "summary": "A Conferência de Berlim (1884-1885) reuniu potências europeias, os EUA e o Império Otomano para definir regras "
                "da partilha da África, sem nenhum representante africano. Nos tratados seguintes, os europeus traçaram "
                "fronteiras que cortaram povos e reinos. Em 1914, só a Etiópia e a Libéria eram independentes. O ENEM cobra "
                "o imperialismo do século XIX e suas consequências."},
]

# vídeos longos de revisão (8-12 min, capítulos automáticos pelo render)
LONGS: list[dict[str, Any]] = [
    {"key": "longo-temas", "minutes": 11, "structure": "contagem", "publish": "2026-10-31 10:00",
     "enem": "Revisão geral de História (Ciências Humanas)",
     "title": "Os temas de História que mais caem no ENEM: revisão 2026",
     "angle": "Contagem regressiva dos temas campeões nas provas, cada um com o essencial, as datas-chave e como a questão costuma vir.",
     "summary": "Revisão em contagem regressiva dos temas de História que mais aparecem no ENEM, segundo levantamentos das "
                "provas (SAS, provas de 2009 a 2023: Idade Contemporânea 15,4%, Brasil Colônia 12,8%, Brasil Império 11,5%, "
                "História Política 10,6%, Patrimônio e memória 9,2%): Brasil Colônia (açúcar, escravidão, resistência), Brasil "
                "Império (independência, Lei de Terras, abolição em 1888), Primeira República (coronelismo, Canudos), Era "
                "Vargas (CLT 1943, Estado Novo 1937-1945), Ditadura Militar (golpe de 1964, AI-5 1968, Diretas Já 1984) e "
                "Constituição de 1988, Revoluções Francesa e Industrial, Guerra Fria, Idade Média e Antiguidade (cidadania). "
                "Para cada tema: o essencial, 2-3 datas e o tipo de questão (texto-base, charge, documento)."},
    {"key": "longo-republica", "minutes": 10, "structure": "cronologia", "publish": "2026-11-05 19:00",
     "enem": "Brasil República (1889-1988)",
     "title": "Brasil República para o ENEM: de 1889 a 1988 em 10 minutos",
     "angle": "A República inteira numa linha do tempo rápida, com o que cada período tem de mais cobrado.",
     "summary": "Linha do tempo do Brasil República para o ENEM: Proclamação (15 de novembro de 1889); Primeira República "
                "(política dos governadores, coronelismo, Canudos 1896-1897, Revolta da Vacina 1904); Revolução de 1930; Era "
                "Vargas (voto feminino 1932, Estado Novo 1937-1945, CLT 1943, FEB na Itália); período democrático de 1946 a "
                "1964; golpe de 1964, AI-5 (1968), milagre econômico (1968-1973), Lei da Anistia (1979), Diretas Já (1984); "
                "Constituição Cidadã (5 de outubro de 1988)."},
]

SEO_RULES = """SEO ENEM 2026 — o público está procurando revisão de História para a prova de 08/11 (1º dia: Ciências Humanas):
- GANCHO de revisão: parta de um erro comum, de uma pegadinha ou de um fato que surpreende sobre o tema — nunca "hoje vamos
  revisar". A revisão vem disfarçada de história boa (quem assiste até o fim aprende sem perceber).
- O vídeo precisa ENTREGAR revisão: em algum ponto (com palavras diferentes a cada vídeo, nem sempre no mesmo lugar) diga o que
  o ENEM costuma cobrar do tema — o conceito, a causa/consequência, ou como a questão aparece (texto-base, charge, documento).
- TÍTULO: o assunto vem primeiro. Use "ENEM" só se couber de forma natural e honesta — não em todo vídeo, e variando a forma
  ("cai no ENEM", "revisão ENEM", "ENEM 2026"). PROIBIDO prometer o que ninguém sabe: nada de "vai cair com certeza",
  "questão garantida", "gabarito" ou "vazou".
- DESCRIÇÃO: na 1ª ou 2ª frase, cite "ENEM 2026" e "revisão de História" de forma natural (frase própria deste vídeo);
  depois liste as datas-chave do vídeo.
- TAGS: inclua "enem 2026", "revisão enem", "história enem" e variações do assunto principal.
- HASHTAGS: #ENEM2026 e 1 ou 2 específicas do assunto."""

SEO_LONG = """- VÍDEO LONGO DE REVISÃO: anuncie cada tema pelo nome ao começar (os capítulos são gerados da narração) e feche cada bloco
  com uma frase de "como cai na prova". O TÍTULO deve conter "ENEM" e o termo de busca mais forte ("revisão", "História")."""


def is_enem(camp: dict[str, Any] | None) -> bool:
    return bool(camp) and "enem" in str(camp.get("id", "")).lower()


SEO_CORRECTION = """SEO CORREÇÃO ENEM 2026 — a prova de Ciências Humanas já aconteceu (08/11); o público procura as questões que caíram,
o gabarito comentado e o contexto histórico por trás de cada questão:
- O vídeo explica o TEMA HISTÓRICO de uma questão que caiu: o que a questão cobrava, o contexto, e por que a alternativa
  certa está certa. Só cite a questão/gabarito se estiver nas fontes; nunca invente enunciado, número de questão ou alternativa.
- GANCHO: parta da dúvida de quem fez a prova (ex.: a pegadinha, o conceito que confundiu), com palavras próprias deste vídeo.
- TÍTULO: o assunto primeiro + "ENEM 2026" quando couber de forma natural ("caiu no ENEM 2026", "questão do ENEM 2026").
  PROIBIDO "gabarito oficial" se não for do Inep, "vazou", "anulada" sem fonte.
- DESCRIÇÃO: na 1ª ou 2ª frase, "ENEM 2026" e "correção"/"questão de História" de forma natural; depois as datas-chave.
- TAGS: "enem 2026", "correção enem 2026", "questões enem história" e variações do assunto. HASHTAGS: #ENEM2026 e 1-2 do assunto."""


def seo_rules(fmt: str, today: date | None = None) -> str:
    """Regras de SEO da campanha: revisão até o dia da prova; depois, correção (as questões que caíram)."""
    from .growth import ENEM_DAY
    if (today or date.today()) > ENEM_DAY:
        return SEO_CORRECTION
    return SEO_RULES + ("\n" + SEO_LONG if fmt == "long" else "")


def ensure_campaign(ch: Channel) -> dict[str, Any]:
    """Garante a campanha de revisão ativa (o dono pode ter apagado/pausado no painel)."""
    from .growth import default_campaigns, ensure_campaigns
    camps = [c for c in ensure_campaigns(ch) if c.get("id") != "_none"]
    cur = next((c for c in camps if c.get("id") == CAMPAIGN_ID), None)
    if cur and cur.get("active", True):
        return cur
    dflt = {c["id"]: c for c in default_campaigns(ch) or []}
    base = dflt.get(CAMPAIGN_ID) or {"id": CAMPAIGN_ID, "name": "Revisão ENEM de História", "start": "2026-10-27",
                                     "end": "2026-11-08", "share": 0.7, "active": True,
                                     "focus": "os temas de História que mais caem no ENEM"}
    cur = {**base, **(cur or {}), "active": True}
    with session() as s:
        db = s.get(Channel, ch.id)
        db.campaigns = [c for c in camps if c.get("id") != CAMPAIGN_ID] + [cur]
        s.add(db)
        s.commit()
    return cur


def _existing(channel_id: int) -> dict[str, Idea]:
    with session() as s:
        ideas = s.exec(select(Idea).where(Idea.channel_id == channel_id)).all()
    out = {}
    for i in ideas:
        for t in i.tags or []:
            if str(t).startswith("enem:"):
                out[t[5:]] = i
    return out


def _slots_until(ch: Channel, end: date) -> list[datetime]:
    """Horários de Short do piloto até a véspera/dia da prova que passam nas travas de espaçamento e limite diário."""
    from . import posting_times
    from .scheduler import parse_slot
    try:
        slots = posting_times.auto_slots(ch) if posting_times.settings(ch)["mode"] == "auto" else (ch.posting_slots or [])
    except Exception:  # noqa: BLE001
        slots = ch.posting_slots or []
    try:  # modo foco do canal (Pausado = nenhum, Reduzido = metade)
        from . import focus
        if focus.paused(ch):
            return []
        slots = focus.filter_slots(ch, slots, posting_times.settings(ch)["mode"] == "auto")
    except Exception:  # noqa: BLE001
        pass
    now_ = datetime.now().astimezone()
    out: list[datetime] = []
    d = now_.date()
    while d <= end:
        for slot in slots:
            p = parse_slot(slot)
            if not p or p[3] != "short" or (p[0] is not None and p[0] != d.weekday()):
                continue
            t = datetime(d.year, d.month, d.day, p[1], p[2]).astimezone()
            if t > now_ + timedelta(minutes=75) and not posting_times.conflict(ch, t, "short", extra=out):
                out.append(t)
        d += timedelta(days=1)
    return out


def pack(ch: Channel) -> dict[str, Any]:
    """Prévia do pacote: pautas (já lançadas ou não), quantos horários cabem até a prova e o que falta ligar."""
    from .growth import ENEM_DAY
    have = _existing(ch.id)
    camp = next((c for c in ch.campaigns or [] if c.get("id") == CAMPAIGN_ID), None)
    share = float((camp or {}).get("share", 0.7))
    slots = _slots_until(ch, ENEM_DAY - timedelta(days=1))  # no dia da prova o público já está na sala

    def row(it: dict[str, Any], fmt: str) -> dict[str, Any]:
        i = have.get(it["key"])
        return {"key": it["key"], "format": fmt, "title": it["title"], "angle": it["angle"], "enem": it["enem"],
                "weight": it.get("weight", 3), "structure": it.get("structure"), "minutes": it.get("minutes"),
                "publish": it.get("publish"),
                "idea": {"id": i.id, "status": i.status, "fact_status": i.fact_status, "score": i.score} if i else None}
    shorts = sorted((row(x, "short") for x in SHORTS), key=lambda r: -r["weight"])
    return {"campaign": camp, "enem_day": ENEM_DAY.isoformat(), "days_left": (ENEM_DAY - date.today()).days,
            "short_slots": len(slots), "campaign_slots": round(len(slots) * share),
            "suggested": min(len(SHORTS), max(6, round(len(slots) * share) + 2)),
            "auto_pilot": bool(ch.auto_pilot), "long_enabled": "long" in (ch.formats or []),
            "shorts": shorts, "longs": [row(x, "long") for x in LONGS]}


def launch(ch: Channel, keys: list[str], schedule_longs: bool = False) -> dict[str, Any]:
    """Cria as pautas escolhidas (aprovadas, na campanha) e põe na fila a checagem de fatos + nota.
    Vídeos longos com schedule_longs: depois da checagem já vira roteiro → vídeo → publicação agendada."""
    from .growth import campaign_tag
    camp = ensure_campaign(ch)
    have = _existing(ch.id)
    items = {x["key"]: (x, "short") for x in SHORTS} | {x["key"]: (x, "long") for x in LONGS}
    created, skipped, jobs = [], [], []
    for k in keys:
        if k not in items:
            continue
        it, fmt = items[k]
        old = have.get(k)
        if old and old.status not in ("discarded", "rejected"):
            skipped.append(it["title"])
            idea_id = old.id
        else:
            tags = [it["enem"], campaign_tag(camp), f"enem:{k}", "enem2026"]
            if it.get("structure"):
                tags.append(f"estrutura:{it['structure']}")
            if it.get("minutes"):
                tags.append(f"minutos:{it['minutes']}")
            with session() as s:
                idea = Idea(channel_id=ch.id, title=it["title"], angle=it["angle"], summary=it["summary"],
                            format=fmt, origin="manual", status="approved", tags=tags)
                s.add(idea)
                s.commit()
                s.refresh(idea)
                idea_id = idea.id
            created.append(it["title"])
        payload: dict[str, Any] = {}
        if fmt == "long" and schedule_longs and it.get("publish"):
            payload["publish_at"] = datetime.strptime(it["publish"], "%Y-%m-%d %H:%M").astimezone().isoformat()
        if idea_id == getattr(old, "id", None) and (old.status in ("scripted", "produced")
                                                    or (old.fact_status == "verified" and not payload)):
            continue  # já checada (ou já virou roteiro): nada a refazer
        j = enqueue("enem_prepare", title=f"ENEM: checar pauta{' longa' if fmt == 'long' else ''}: {it['title']}",
                    channel_id=ch.id, ref_id=idea_id, payload=payload)
        jobs.append(j.id)
    return {"created": created, "skipped": skipped, "jobs": jobs, "campaign": camp}


@handler("enem_prepare")
def job_prepare(ctx: JobContext) -> dict:
    """Checagem de fatos → descarte se falsa → nota. Vídeo longo agendado: segue para roteiro e render."""
    from . import content
    from .pipeline import _apply_check, _channel, _enforce_facts, _score
    with session() as s:
        idea = s.get(Idea, ctx.ref_id)
    if not idea:
        raise RuntimeError("pauta não existe mais")
    ch = _channel(idea.channel_id)
    if idea.fact_status != "verified":
        ctx.update(0.1, "Checando fatos nas fontes")
        r = content.verify_idea(ch, idea)
        with session() as s:
            db = s.get(Idea, idea.id)
            _apply_check(db, r)
            s.add(db)
            s.commit()
        ctx.log(f"Checagem: {r['fact_status']} com {len(r['sources'])} fontes")
        if _enforce_facts(idea.id, ctx):
            return {"discarded": True}
    ctx.update(0.6, "Dando nota à pauta")
    _score(ch, idea.id, ctx)
    with session() as s:
        idea = s.get(Idea, idea.id)
    if ctx.payload.get("publish_at") and idea.format == "long" and idea.fact_status == "verified":
        from . import posting_times
        when = posting_times.next_free(ch, datetime.fromisoformat(ctx.payload["publish_at"]), "long")
        enqueue("write_script", title=f"Roteiro longo: {idea.title}", channel_id=ch.id, ref_id=idea.id,
                payload={"auto_render": True, "format": "long", "publish_at": when.isoformat()})
        ctx.log(f"Longo vai para roteiro → vídeo → publicação em {when.astimezone(posting_times.TZ):%d/%m %H:%M}")
    return {"fact_status": idea.fact_status, "score": idea.score}
