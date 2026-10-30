"""Modo História: vídeos de história em série, ilustrados, com HUD de missão (estilo jogo) e personagens recorrentes.

Peças:
- bible.py      — "bíblia" da série por canal (estilo de arte, paleta, época, personagens, vozes, HUD)
- bank.py       — banco de assets com tags (poses recortadas, cenários vazios, cenas, objetos), reaproveitamento
- cutout.py     — chroma key, recorte por IA local (u2netp), olhos para piscar, validação, limpeza de assinatura
- providers.py  — geradores de imagem grátis (Cloudflare, HF Space, local, Pollinations) + orçamento diário
- gpu.py        — trava de GPU entre processos (geração local × render)
- writer.py     — roteiro de episódio (JSON) pelo LLM + memória da série + checagem de fatos
- planner.py    — plano de imagens do episódio (novas × banco) dentro da cota
- jobs.py       — tarefas da fila: story_episode, story_assets, story_pregen, story_render
O render fica em lidark/render/story.py (+ story_hud.py).
"""
