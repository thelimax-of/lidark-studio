# Motor vetorial (estilo @escolhas.app, mais rico)

Vídeo 100% desenhado em SVG, grátis e local, sem geração de imagem. Cada quadro é uma função pura do tempo
(mesmo `t` = mesmo desenho). Referência de código: a prova `scene.html` indicada no briefing.

## Aparência (vale para todos)
- Vetor plano, contorno escuro `#14182a` de 5 a 8 px em tudo, cantos arredondados, cores claras e vivas (nada escuro/turvo).
- Muito detalhe por cena: objetos, cartazes, luzes, sujeira, pequenas piadas visuais. Cenário vazio é defeito.
- Texto só com fontes do sistema: `Impact, 'Arial Black', sans-serif` em títulos; `'Segoe UI', Arial, sans-serif` em telas.
- Tudo se move um pouco: nada fica 100% parado por mais de 1 s (luz, partículas, ponteiros, respiração).
- Determinístico: sem `Math.random()`/`Date`; use `V.rnd(seed)`.

## Arquivos e donos
| Arquivo | Dono |
|---|---|
| `render/vetor/page.html`, `runtime.js`, `chars.js`, `engine.py`, `__init__.py` | Agente MOTOR |
| `render/vetor/sets.js`, `props.js` | Agente MUNDO |
| `render/vetor/screens.js` | Agente TELAS |
| `story/vetor_director.py`, `story/vetor_writer.py`, gancho em `story/engine.py` e `story/writer.py` | Agente ROTEIRO |

## API JS (global `V`, definida em `runtime.js`, carregada antes das bibliotecas)
```js
V.sets.nome    = (t, o) => svgString   // fundo 720x1280, coords do "mundo"; o = {tod:"day|night|alert", state:{...}}
V.props.nome   = (t, o) => svgString   // desenhado em volta de (0,0), ~100 px; o = {state, label}
V.screens.nome = (t, d, o) => svgString // tela cheia 720x1280 no referencial da câmera; t = segundos desde que abriu; d = dados
V.chars.nome   = (t, o) => svgString   // o = {pose, expr, talk (0..1), hold, state, flip}; pés em (0,0), ~620 px de altura
V.rnd(seed) -> 0..1 · V.ease(x) · V.cl(x,a,b) · V.esc(texto) (escapa XML)
```
Toda biblioteca declara no fim `V.docs.<tipo>.<nome> = {desc, data}`: uma frase e o exemplo de dados. O ROTEIRO lê isso para ensinar a IA.
Bibliotecas não dependem umas das outras, exceto `V.props.x(...)` e `V.chars.x(...)` que podem ser chamados de dentro de sets/screens com fallback seguro (`(V.props.x||(()=>''))(t,o)`).
Nome desconhecido nunca quebra o quadro: desenha um substituto discreto e registra em `V.missing`.

## Spec (JSON gerado pelo ROTEIRO, lido pelo MOTOR)
```jsonc
{ "W":720,"H":1280,"fps":30,"duration":73.0,"seed":1,
  "shots":[{ "t0":0,"t1":2.4,"set":"station_corridor","tod":"alert","set_state":{},
    "cast":[{"char":"ze","x":360,"y":1090,"scale":1,"pose":"stand|walk|run|point|hold|hands_head|sit|crawl|type|fall|float",
             "expr":"neutral|scared|happy|angry|sad|shock|sleepy","hold":"tape","flip":false,"state":{"dirt":0.3,"bandage":true},
             "enter":"left|right|none"}],
    "props":[{"id":"oxygen_tank","x":100,"y":800,"scale":1,"state":{}}],
    "fx":["sparks","smoke","alarm","steam","floaters","rain","dust"],
    "cam":{"from":{"x":360,"y":640,"z":1},"to":{"x":360,"y":640,"z":1.06},"shake":0},
    "screen":null,   // ou {"type":"phone_chat","data":{...},"device":"hand|fullscreen|tv_on_set"}
    "transition":"cut|whip|flash|iris|glitch|slide" }],
  "captions":[{"t0":0.1,"t1":0.7,"text":"O OXIGÊNIO","color":"#fff"}],
  "stamps":[{"t0":3.4,"t1":4.9,"text":"MICROFURO","x":480,"y":300,"style":"yellow|red|green"}],
  "reactions":[{"t0":2,"t1":3.2,"kind":"sweat|question|exclaim|heart|anger|bulb|zzz","char":"ze"}],
  "hud":{"meters":[{"id":"o2","label":"OXIGÊNIO","color":"#39d98a","low":"#ff5a4d","lowAt":40,"keys":[[0,48],[73,31]]}],
         "counters":[{"id":"dia","label":"DIA EM ÓRBITA","value":12}],
         "inventory":[{"t":5.0,"item":"tape","label":"FITA"}], "show":true},
  "lines":[{"audio":"...wav","start":0.1,"end":1.8,"dur":1.7,"speaker":"ze","text":"..."}],
  "sfx":[{"t":3.4,"kind":"impact","gain":0.5}], "ambience":[], "music":{}, "climax_at":60,
  "end":{"choice":{"title":"COMENTE UMA PALAVRA","a":{"word":"FITA","hint":"..."},"b":{"word":"SOLDA","hint":"..."}}} }
```
`lines`, `sfx`, `ambience`, `music`, `climax_at`, `duration`, `seed`, `fps` são os mesmos campos que `render/story.py::build_audio` já lê.

## engine.py (MOTOR)
`render(spec, out, workdir, *, progress=None, check=None, music_bed=None) -> dict` com o mesmo retorno de `render/story.py::render`
e `still(spec, t) -> PIL.Image`. Usa `story.build_audio` + `production.loudnorm_2pass`, Playwright com
`p.chromium.launch(channel="msedge")` (Edge do Windows; não instalar navegador), e envia os quadros ao FFmpeg (`imageio_ffmpeg`).
O envelope da voz vira `talk` da boca do personagem que fala.

## Ativação
Só quando `bible["render_style"] == "vetor"`. Padrão desligado; nenhum outro canal muda.
