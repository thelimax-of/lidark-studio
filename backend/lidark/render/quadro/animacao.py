"""Entrega o runtime de animação (animacao.js) para a página do episódio."""
from __future__ import annotations

from pathlib import Path


def js() -> str:
    return (Path(__file__).parent / 'animacao.js').read_text(encoding='utf-8')
