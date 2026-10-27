"""Primitivas de desenho e pipeline de quadros → FFmpeg."""
from __future__ import annotations

import functools
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..media import ffmpeg_exe, video_encoder_args

FONTS = Path(__file__).resolve().parents[2] / "assets" / "fonts"


# ================================================================ dados da linha do tempo

@dataclass
class Word:
    text: str
    start: float
    end: float
    hi: bool = False  # destaque dourado


@dataclass
class SceneT:
    index: int
    start: float
    end: float
    text: str
    image: Image.Image | None
    label: str = ""
    step: int = 0  # 0 = sem passo (gancho/final)
    words: list[Word] = field(default_factory=list)
    fx: str = ""  # efeito pedido pelo roteiro (mito | verdade)
    graphic: dict | None = None  # cena animada com dados: {"kind": "timeline", "data": {...}}
    clip: Any = None  # filmagem real da cena (Clip) — quando existe, toca no lugar da foto


class Clip:
    """Filmagem já recortada no tamanho do vídeo: lê quadros em sequência (sem carregar tudo na memória)."""

    def __init__(self, path: str, fps: int = 30):
        self.path, self.fps = path, fps
        self._gen = None
        self._i = -1
        self._cur: Image.Image | None = None
        self.size = (0, 0)

    def _open(self) -> None:
        import imageio_ffmpeg
        self._gen = imageio_ffmpeg.read_frames(self.path, pix_fmt="rgb24")
        meta = next(self._gen)
        self.size = tuple(meta["size"])
        self._i = -1

    def frame(self, t: float) -> Image.Image | None:
        idx = max(0, int(t * self.fps))
        if self._gen is None or idx < self._i:
            self._open()
        while self._i < idx:
            try:
                buf = next(self._gen)
            except StopIteration:
                break  # clipe acabou: segura o último quadro
            self._i += 1
            if self._i >= idx - 0:
                self._cur = Image.frombytes("RGB", self.size, buf)
        return self._cur


@dataclass
class Timeline:
    width: int
    height: int
    fps: int
    duration: float
    narration_end: float
    title: str
    scenes: list[SceneT]
    steps: int
    words: list[Word]
    envelope: np.ndarray  # volume da narração por quadro (0..1) → boca do mascote
    theme: dict[str, Any]
    fmt: str = "short"

    def scene_at(self, t: float) -> SceneT:
        for s in self.scenes:
            if s.start <= t < s.end:
                return s
        return self.scenes[-1]


# ================================================================ cores, fontes, easing

def hex2rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgba(h: str, a: int = 255) -> tuple[int, int, int, int]:
    return (*hex2rgb(h), a)


@functools.lru_cache(maxsize=64)
def font(name: str, size: int, weight: int | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:  # noqa: BLE001
            pass
    return f


def clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return a if x < a else b if x > b else x


def ease_out_cubic(x: float) -> float:
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_out_back(x: float, s: float = 1.6) -> float:
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def ease_in_out(x: float) -> float:
    x = clamp(x)
    return 3 * x * x - 2 * x * x * x


# ================================================================ desenho

def radial_gradient(w: int, h: int, center: tuple[float, float], inner: str, outer: str, radius: float) -> Image.Image:
    y, x = np.ogrid[:h, :w]
    d = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2) / radius
    d = np.clip(d, 0, 1) ** 1.4
    a, b = np.array(hex2rgb(inner), np.float32), np.array(hex2rgb(outer), np.float32)
    img = a[None, None, :] * (1 - d[..., None]) + b[None, None, :] * d[..., None]
    # granulação sutil para evitar banding
    img += np.random.default_rng(1).normal(0, 1.6, img.shape)
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def linear_gradient(w: int, h: int, top: str, bottom: str) -> Image.Image:
    a, b = np.array(hex2rgb(top), np.float32), np.array(hex2rgb(bottom), np.float32)
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    img = np.broadcast_to(a * (1 - t) + b * t, (h, w, 3))
    return Image.fromarray(img.astype(np.uint8), "RGB")


def rounded_mask(w: int, h: int, r: int, ss: int = 3) -> Image.Image:
    m = Image.new("L", (w * ss, h * ss), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * ss - 1, h * ss - 1), r * ss, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def shadow(w: int, h: int, r: int, blur: int, alpha: int = 140, spread: int = 0) -> Image.Image:
    pad = blur * 3
    img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    ImageDraw.Draw(img).rounded_rectangle((pad - spread, pad - spread, pad + w + spread, pad + h + spread), r, fill=(0, 0, 0, alpha))
    return img.filter(ImageFilter.GaussianBlur(blur))


def supersampled(w: int, h: int, draw_fn: Callable[[ImageDraw.ImageDraw, float], None], ss: int = 3) -> Image.Image:
    """Desenha em resolução maior e reduz (anti-aliasing)."""
    img = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(img), ss)
    return img.resize((w, h), Image.LANCZOS)


def paste(dst: Image.Image, src: Image.Image, xy: tuple[float, float], opacity: float = 1.0) -> None:
    x, y = int(round(xy[0])), int(round(xy[1]))
    if opacity <= 0.01:
        return
    if opacity < 0.999:
        src = src.copy()
        a = src.getchannel("A").point(lambda v: int(v * opacity))
        src.putalpha(a)
    dst.paste(src, (x, y), src)


def scaled(img: Image.Image, s: float, resample=Image.BILINEAR) -> Image.Image:
    if abs(s - 1) < 1e-3:
        return img
    w, h = max(1, int(img.width * s)), max(1, int(img.height * s))
    return img.resize((w, h), resample)


def fit_cover(img: Image.Image, w: int, h: int, zoom: float = 1.0, focus: tuple[float, float] = (0.5, 0.42)) -> Image.Image:
    """Recorta a imagem para preencher w×h (com zoom para Ken Burns), sem distorcer."""
    s = max(w / img.width, h / img.height) * zoom
    cw, ch = w / s, h / s
    cx = clamp(focus[0] * img.width, cw / 2, img.width - cw / 2)
    cy = clamp(focus[1] * img.height, ch / 2, img.height - ch / 2)
    box = (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)
    return img.resize((w, h), Image.BICUBIC, box=box)


def text_width(f: ImageFont.FreeTypeFont, s: str) -> float:
    return f.getlength(s)


def wrap(f: ImageFont.FreeTypeFont, text: str, max_w: float) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def ellipsize(f: ImageFont.FreeTypeFont, text: str, max_w: float) -> str:
    if f.getlength(text) <= max_w:
        return text
    while text and f.getlength(text + "...") > max_w:
        text = text[:-1]
    return text.rstrip() + "..."


# ================================================================ codificação

class FrameWriter:
    """Envia quadros RGB para o FFmpeg (NVENC quando disponível) e já mistura o áudio final."""

    def __init__(self, out: Path, w: int, h: int, fps: int, audio: Path | None):
        args = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
        if audio:
            args += ["-i", str(audio)]
        args += video_encoder_args()
        if audio:
            args += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-map", "0:v", "-map", "1:a", "-shortest"]
        args += ["-movflags", "+faststart", "-r", str(fps), str(out)]
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, frame: Image.Image) -> None:
        assert self.proc.stdin
        self.proc.stdin.write(frame.tobytes())

    def close(self) -> None:
        assert self.proc.stdin
        self.proc.stdin.close()
        err = self.proc.stderr.read().decode(errors="ignore") if self.proc.stderr else ""
        if self.proc.wait() != 0:
            raise RuntimeError("FFmpeg falhou ao codificar: " + err[-1500:])


def render(tl: Timeline, template: Any, out: Path, audio: Path | None,
           progress: Callable[[float], None] | None = None) -> None:
    n = int(math.ceil(tl.duration * tl.fps))
    w = FrameWriter(out, tl.width, tl.height, tl.fps, audio)
    try:
        for i in range(n):
            t = i / tl.fps
            frame = template.frame(t, i)
            look = getattr(template, "look", None)
            if look is not None and look.active:
                frame = look.apply(frame, i)
            w.write(frame.convert("RGB") if frame.mode != "RGB" else frame)
            if progress and i % 15 == 0:
                progress(i / n)
    finally:
        w.close()
