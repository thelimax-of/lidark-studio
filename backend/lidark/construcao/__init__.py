"""Motor 3D do canal Parte por Parte: roteiro, cena em Three.js, voz, música, render e registro do vídeo.

Cada projeto fica em data/construcao/<id>/ com projeto.json e cena.js. A cena é um script comum que usa o
global K3, publicado por motor/kit.bundle.js. O render roda em processo separado (render.py e audio.py).
"""
from pathlib import Path

from ..config import DATA_DIR

BASE = DATA_DIR / "construcao"
MOTOR = Path(__file__).resolve().parent / "motor"
