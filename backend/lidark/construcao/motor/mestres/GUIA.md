# Como criar uma cena-mestra

Uma cena-mestra é um vídeo feito à mão que o sistema reutiliza sozinho. A inteligência do app só escreve uma narração nova por cima dela. A referência de qualidade é o vídeo do telhado: `telhado.js`. Leia-o antes de começar.

## Arquivos

Para um tema `chave` (só letras minúsculas e sublinhado), crie:

- `mestres/chave.js`: a cena, em Three.js, autossuficiente. Copie o início do `telhado.js` (ajudantes, bairro, andaime, pedreiro, câmera).
- `mestres/chave.json`:

```json
{"chaves": "palavras que chamam esta cena", "tema": "um ventilador", "categoria": "Eletrodomésticos",
 "palavras": [165, 200], "cauda": 4.5, "zoom": 1.16, "rate": "+6%",
 "etapas": [{}, {"o": "o que acontece nesta fala", "palavra": "palavra obrigatória"}, {}],
 "exemplo": ["fala 0", "fala 1", "..."], "variantes": [{"ceu": ["#4a9be6", "#dff1fb"], "sol": 16773596, "grama": 6470997}]}
```

`chaves` deve ter palavras exclusivas do tema, sem nenhuma que chame outra cena. A primeira e a última etapa são `{}`. `exemplo` traz uma fala por etapa. Use 4 variantes de cor. Cada campo extra da variante vira cor na cena, por `E.variante`.

## Regras de roteiro

- De 165 a 200 palavras, 9 a 12 falas, cerca de 1:30.
- Frases curtas de conversa, que uma criança de dez anos entende.
- Todo termo técnico vem com comparação do dia a dia: "são as costelas do telhado".
- Cada fala diz o problema que a etapa resolve. Ligações: Então, Mas, Só que, Agora.
- Fala 0 começa com "Se você" e mostra o erro. Última começa com "Parabéns, você construiu" e termina com pergunta. Sem algarismos ou medidas.

## Regras de cena, o que separa do resto

1. **A obra enche a tela.** Cada etapa mostra um quadro quase todo tomado pela obra, sem chão vazio. O vídeo é vertical: a largura visível é pequena, então prefira objetos altos ou câmera mais alta.
2. **Muitas peças repetidas.** Centenas: telhas, caibros, voltas de cobre, raios. Use `InstancedMesh` quando passar de 100. Uma etapa nunca é uma peça só.
3. **Cada etapa muda a imagem inteira.** Se a tela antes e depois parecem iguais, a etapa está fraca.
4. **O personagem está na obra**, de capacete amarelo e martelo, em andaime ou sobre a peça, nunca andando no vazio nem na frente da câmera.
5. **Abertura com o erro acontecendo** já no primeiro segundo: algo cai, vaza, quebra, apaga.
6. **Final mostrando funcionar** com impacto no bairro: chuva, vento, luz acendendo, água correndo. Começa logo depois de "Parabéns, você construiu".
7. **Nada flutua.** Tudo que entra se apoia no que já existe, em qualquer momento do vídeo.
8. **Câmera** de cima e de lado, como o telhado, nunca de frente reta. Um plano por fala, com aproximação lenta. Se atravessar a obra ao trocar de lado, use corte seco.
9. **Cenário rico**: bairro, sítio, praia ou cidade, sempre com céu, casas, árvores e detalhes. Eletrodomésticos e objetos do dia a dia têm SEMPRE o tamanho real e ficam dentro de casa, nunca gigantes: o dono do canal recusou objeto gigante.
10. **Sons** em cada peça (`som(t, 'toc' | 'tijolo' | 'telha' | 'pop' | 'ding' | 'impact' | 'crack' | 'desaba' | 'motor' | 'zumbido' | 'chuva' | 'whoosh' | 'riser' | 'gota')`).

## Regras técnicas

- A cena usa só `K3`, `window.ESPEC` e `iniciar`. Tudo depende do tempo `t`, de forma determinística: nada de `Math.random` nem de relógio; use `prng`.
- Tempos: `F(i)` início da fala, `fim(i)` fim, `tk('palavra', i)` momento da palavra com queda segura para outra narração. Nunca use `pal()` direto: a narração muda.
- Defina `T_USO` como em `telhado.js` e `window.CAPA_T` num momento bonito do final.
- Rótulos dourados por etapa com `rotulo('NOME', [x, y, z], t0, t1, 'ouro')`; `'ruim'` em vermelho na abertura; `'grande'` para "X PRONTO!".

## Teste obrigatório

Rode, a partir de `backend`:

```
python -m lidark.construcao.prever chave
```

Ele narra o exemplo, renderiza 12 quadros e imprime o caminho de `previa.jpg`. Olhe a imagem. Para ver tempos exatos: `QUADROS=1.5,2.5,40 python -m lidark.construcao.prever chave`. Corrija e rode de novo até cumprir as 10 regras. Não aceite cena que você não olhou. Cena só com erro de sintaxe não conta: `node --check` não prova nada visual.
