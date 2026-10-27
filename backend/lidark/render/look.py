"""'Look' do vídeo: tratamento de cor e granulado aplicados no quadro final.

Cada vídeo recebe um look sorteado pelo diretor de variedade (lidark/variety.py), para que
os vídeos do canal não tenham todos a mesma 'impressão digital' visual. Os tratamentos são suaves:
a identidade do canal (cores do tema, mascote, fontes) continua reconhecível.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

GRADES = ("neutro", "quente", "frio", "contraste", "sepia", "filme")


def _curve(x: np.ndarray, lift: float = 0.0, gain: float = 1.0, gamma: float = 1.0, s: float = 0.0) -> np.ndarray:
    y = np.clip(x, 0, 1) ** gamma
    if s:  # curva em S (contraste) centrada no meio-tom
        y = y + s * (y - 0.5) * (1 - np.abs(2 * y - 1))
    return np.clip(lift + y * (gain - lift), 0, 1)


def grade_lut(name: str) -> list[int] | None:
    """Tabela de 768 entradas (R, G, B) para Image.point — custa ~1 ms por quadro."""
    if name in ("", "neutro", None):
        return None
    x = np.linspace(0, 1, 256)
    r = g = b = x
    if name == "quente":
        r, g, b = _curve(x, gain=1.0, gamma=0.96), _curve(x, gamma=0.99), _curve(x, gain=0.93, gamma=1.04)
    elif name == "frio":
        r, g, b = _curve(x, gain=0.95, gamma=1.03), _curve(x, gamma=0.99), _curve(x, lift=0.02, gamma=0.95)
    elif name == "contraste":
        r = g = b = _curve(x, s=0.35, gamma=1.02)
    elif name == "sepia":  # mistura de canais feita em apply(); aqui só aquece
        r, g, b = _curve(x, lift=0.03, gamma=0.97), _curve(x, lift=0.02), _curve(x, lift=0.0, gain=0.9, gamma=1.06)
    elif name == "filme":  # pretos levantados + leve S, cara de película
        r, g, b = _curve(x, lift=0.05, gain=0.98, s=0.2), _curve(x, lift=0.045, gain=0.97, s=0.2), _curve(x, lift=0.06, gain=0.95, s=0.15)
    lut = np.concatenate([r, g, b]) * 255
    return [int(v) for v in np.clip(lut, 0, 255)]


class Look:
    def __init__(self, cfg: dict | None, W: int, H: int, seed: int = 0):
        cfg = cfg or {}
        self.grade = cfg.get("grade", "neutro")
        self.lut = grade_lut(self.grade)
        self.desat = 0.35 if self.grade == "sepia" else (0.12 if self.grade == "filme" else 0.0)
        self.grain = float(cfg.get("grain", 0.0))
        self._noise: list[Image.Image] = []
        if self.grain > 0:
            rng = np.random.default_rng(seed)
            # granulado em baixa resolução ampliado (mais orgânico e barato)
            for _ in range(6):
                n = rng.normal(0, 255 * self.grain, (H // 2, W // 2)).astype(np.int16)
                img = Image.fromarray(np.clip(n + 128, 0, 255).astype(np.uint8), "L").resize((W, H), Image.BILINEAR)
                self._noise.append(Image.merge("RGB", (img, img, img)))

    @property
    def active(self) -> bool:
        return bool(self.lut or self.desat or self._noise)

    def apply(self, frame: Image.Image, i: int) -> Image.Image:
        if frame.mode != "RGB":
            frame = frame.convert("RGB")
        if self.desat:
            frame = Image.blend(frame, frame.convert("L").convert("RGB"), self.desat)
        if self.lut:
            frame = frame.point(self.lut)
        if self._noise:
            from PIL import ImageChops
            frame = ImageChops.overlay(frame, self._noise[i % len(self._noise)])
        return frame
