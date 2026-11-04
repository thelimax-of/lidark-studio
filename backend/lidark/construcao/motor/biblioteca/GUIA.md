# Biblioteca de peças 3D

Cada item é um objeto 3D reutilizável, feito só com código (Three.js). O sistema vai montar vídeos sozinho juntando esses itens, então o item precisa ficar bonito de qualquer ângulo.

## Como escrever

Leia `base.js` inteiro antes. Ele traz os ajudantes `PC.H` e os exemplos do nível exigido: `sofa`, `estante`, `planta_vaso`, `personagem`.

Grave um arquivo `itens/<sua_categoria>.js`, assim:

```js
(() => { const { THREE, mat, add, box, cil, esf, sh } = K3, { PI, G, B, C, CZ, CX, E, T, tubo, forma, roda, luz, vidro, metal, VD } = PC.H;
  PC.item('nome_unico', { cat: 'categoria', tags: ['...'], desc: 'O que é, em uma frase' }, (o = {}) => { const g = new THREE.Group(); /* ... */ return g; });
})();
```

## Regras

1. **Metros reais.** Base em y=0, centrado em x=0, z=0, frente para +z. Objeto de parede usa `parede: true` e `minPartes` se for simples.
2. **Reconhecível à primeira vista**, com silhueta certa e proporções reais. Formas limpas e arredondadas, cores vivas e harmônicas, no estilo low-poly suave do `sofa`.
3. **Detalhe onde importa**: rodas com aro, janelas com moldura, puxadores, parafusos, faróis, sombras de cor com tons mais escuros. Nada de caixa pura com nome de objeto. Mínimo de 6 peças.
4. **Personalizável:** aceite `o.cor` quando fizer sentido. Partes que animam ficam expostas no grupo, como `g.rodas`, `g.porta`, `g.helice`, `g.tela`, `g.leds`.
5. **Sem marcas, logotipos, nem personagens ou produtos conhecidos.** Tudo genérico e original.
6. **Leve:** até uns 1.500 triângulos por item comum; instancie o que repetir. Sem texturas externas, sem `Math.random` (use `K3.prng`), sem depender do tempo.
7. Nomes em português, minúsculos, com sublinhado, únicos na biblioteca. Prefixe se puder colidir. Não edite `base.js`, `galeria.py`, nem arquivos de outras categorias.

## Teste obrigatório

A partir da pasta `backend` do projeto:

```
.venv/Scripts/python.exe "<caminho>/biblioteca/galeria.py" <sua_categoria> <pagina>
```

Mostra 15 itens por folha e lista os problemas de TODOS os itens da categoria. Abra cada folha com a ferramenta Read e olhe de verdade: feio, irreconhecível ou desproporcional deve ser refeito. O teste automático só prova que carrega, não que está bonito. A trava interna faz um teste por vez; pode esperar.

Grave código com a ferramenta Write, porque heredoc no Git Bash altera barras invertidas.

Ao final, responda em português: quantos itens ficaram aprovados, quantas folhas você olhou e quais ficaram mais fracos, sem maquiar.
