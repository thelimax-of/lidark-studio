"""Primitivas de desenho e pipeline de quadros → FFmpeg."""
from __future__ import annotations

import functools
import logging
import math
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..media import ffmpeg_exe, video_encoder_args

FONTS = Path(__file__).resolve().parents[2] / "assets" / "fonts"
log = logging.getLogger("lidark.render")


# ================================================================ dados da linha do tempo

@dataclass
class Word:
    text: str
    start: float
    end: float
    hi: bool = False  # destaque dourado

    def __post_init__(self):
        self.start, self.end = float(self.start), float(self.end)


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

    def __post_init__(self):
        self.start, self.end = float(self.start), float(self.end)


class Clip:
    """Filmagem já recortada no tamanho do vídeo: lê quadros em sequência (sem carregar tudo na memória)."""

    def __init__(self, path: str, fps: int = 30):
        self.path, self.fps = path, fps
        self._gen = None
        self._i = -1
        self._cur: Image.Image | None = None
        self.size = (0, 0)

    def __getstate__(self) -> dict:
        # vai para os processos do render paralelo: o leitor de quadros é reaberto lá
        return {"path": self.path, "fps": self.fps}

    def __setstate__(self, st: dict) -> None:
        self.__init__(st["path"], st["fps"])

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
    hook: str = ""  # frase curta de gancho (texto da miniatura): legível já no 1º quadro dos Shorts

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
    if not weight:
        # fonte variável cujo padrão é fino (Montserrat abre em 100, Nunito em 200): sem peso, a legenda saía um fio
        try:
            ax = f.get_variation_axes()
            if ax and ax[0].get("default", 400) < 400:
                weight = min(700, ax[0].get("maximum", 700))
        except Exception:  # noqa: BLE001
            pass
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:  # noqa: BLE001
            pass
    return f


def clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    x = float(x)
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
    return img.filter(ImageFilter.GaussianBlur(float(blur)))


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
    """Envia quadros RGB para o FFmpeg (NVENC quando disponível); no fim junta o áudio final.

    O vídeo é codificado sozinho e o áudio entra numa 2ª passada rápida (-c:v copy, mesmo vídeo bit a bit): com o
    áudio na mesma passada (-shortest) o FFmpeg acumulava ~1 GB de RAM ao longo de um Short de 70 s."""

    def __init__(self, out: Path, w: int, h: int, fps: int, audio: Path | None):
        self.out, self.audio, self.fps = out, audio, fps
        self.video = out.with_name(out.stem + "_video" + out.suffix) if audio else out
        args = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
        args += video_encoder_args()
        args += ["-movflags", "+faststart", "-r", str(fps), str(self.video)]
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    def write(self, frame: Image.Image) -> None:
        self.write_bytes(frame.tobytes())

    def write_bytes(self, data: bytes | bytearray | memoryview) -> None:
        assert self.proc.stdin
        self.proc.stdin.write(data)

    def close(self) -> None:
        assert self.proc.stdin
        self.proc.stdin.close()
        err = self.proc.stderr.read().decode(errors="ignore") if self.proc.stderr else ""
        if self.proc.wait() != 0:
            raise RuntimeError("FFmpeg falhou ao codificar: " + err[-1500:])
        if self.audio:
            from ..media import run_ffmpeg
            try:
                run_ffmpeg(["-i", str(self.video), "-i", str(self.audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart",
                            str(self.out)])
            finally:
                self.video.unlink(missing_ok=True)


def render_frame(tl: Timeline, template: Any, i: int) -> Image.Image:
    """Quadro i pronto para o encoder: RGB, já com o look (cor/granulado) do vídeo."""
    frame = template.frame(i / tl.fps, i)
    look = getattr(template, "look", None)
    if look is not None and look.active:
        frame = look.apply(frame, i)
    return frame.convert("RGB") if frame.mode != "RGB" else frame


def render(tl: Timeline, template: Any, out: Path, audio: Path | None,
           progress: Callable[[float], None] | None = None) -> None:
    """Desenha todos os quadros e codifica. Com núcleos e memória livres, os quadros são desenhados em processos
    paralelos (mesmos pixels e mesmo encoder: o arquivo final é igual ao do render em série)."""
    n = int(math.ceil(tl.duration * tl.fps))
    try:
        workers = render_workers(n)
        if workers > 1:
            try:
                _render_parallel(tl, template, out, audio, progress, n, workers)
                return
            except Exception as e:  # noqa: BLE001 — Cancelled (BaseException) passa direto
                log.warning("render paralelo falhou (%s) — refazendo em um processo só", e)
        w = FrameWriter(out, tl.width, tl.height, tl.fps, audio)
        try:
            for i in range(n):
                w.write(render_frame(tl, template, i))
                if progress and i % 15 == 0:
                    progress(i / n)
        finally:
            w.close()
    finally:
        _clear_caches(template)


# ================================================================ render paralelo

CHUNK = 8  # quadros seguidos por processo (o processo k desenha os trechos k, k+N, k+2N...)
AHEAD = 12  # quadros prontos que cada processo pode deixar na fila enquanto espera a vez
WORKER_MB = 450  # memória medida de cada processo (~300 MB: fotos das cenas + caches) + folga


def free_ram_mb() -> float | None:
    """Memória física disponível agora (MB)."""
    try:
        if os.name == "nt":
            import ctypes

            class _MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            m = _MS()
            m.dwLength = ctypes.sizeof(_MS)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):
                return None
            return m.ullAvailPhys / 2 ** 20
        return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 2 ** 20
    except Exception:  # noqa: BLE001
        return None


def render_workers(n: int) -> int:
    """Quantos processos usar: config "render_workers" (0 = automático), limitado pelos núcleos e pela RAM livre."""
    from .. import config
    try:
        want = int(config.get("render_workers") or 0)
    except (TypeError, ValueError):
        want = 0
    if want == 1 or n < 90:
        return 1
    limit = want if want > 1 else max(1, min(6, (os.cpu_count() or 2) // 2))
    free = free_ram_mb()
    if free is not None:  # nunca troca RAM por memória virtual: com a RAM cheia o render fica MAIS lento
        limit = min(limit, int((free - 900) // WORKER_MB))
    return max(1, limit)


def _render_parallel(tl: Timeline, template: Any, out: Path, audio: Path | None,
                     progress: Callable[[float], None] | None, n: int, workers: int) -> None:
    """Processos auxiliares (lidark.render.worker) desenham trechos intercalados; este processo só lê os quadros
    na ordem e manda para um único FFmpeg."""
    import pickle
    import shutil
    import sys

    tmp = out.with_name(out.stem + "_render")
    tmp.mkdir(parents=True, exist_ok=True)
    job = tmp / "timeline.pkl"
    cls = type(template)
    with open(job, "wb") as f:
        pickle.dump({"tl": tl, "module": cls.__module__, "cls": cls.__qualname__, "setup": hasattr(template, "plans"),
                     "n": n, "chunk": CHUNK, "workers": workers, "ahead": AHEAD}, f, protocol=pickle.HIGHEST_PROTOCOL)
    backend = Path(__file__).resolve().parents[2]
    exe = Path(sys.executable)
    if exe.name.lower() == "pythonw.exe" and exe.with_name("python.exe").exists():
        exe = exe.with_name("python.exe")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(x for x in (str(backend), os.environ.get("PYTHONPATH", "")) if x),
           # 1 thread no BLAS do numpy: senão cada processo reserva ~350 MB só ao importar o numpy (buffers por núcleo)
           "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    # sem janela e com prioridade baixa: o computador continua usável enquanto renderiza
    flags = (subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS) if os.name == "nt" else 0
    procs: list[subprocess.Popen] = []
    logs: list[Any] = []
    w: FrameWriter | None = None

    def tail(k: int) -> str:
        try:
            logs[k].flush()
            logs[k].seek(0)
            return logs[k].read().decode(errors="ignore")[-1200:]
        except Exception:  # noqa: BLE001
            return ""

    try:
        for k in range(workers):
            logs.append(open(tmp / f"worker{k}.log", "w+b"))
            procs.append(subprocess.Popen([str(exe), "-m", "lidark.render.worker", str(job), str(k)], cwd=str(backend),
                                          env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=logs[k],
                                          creationflags=flags))
        w = FrameWriter(out, tl.width, tl.height, tl.fps, audio)
        size = tl.width * tl.height * 3
        buf = memoryview(bytearray(size))
        for i in range(n):
            k = (i // CHUNK) % workers
            src = procs[k].stdout
            got = 0
            while got < size:
                r = src.readinto(buf[got:])  # type: ignore[union-attr]
                if not r:
                    try:
                        procs[k].wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        pass
                    raise RuntimeError(f"processo {k} do render parou no quadro {i}: {tail(k)}")
                got += r
            w.write_bytes(buf)
            if progress and i % 15 == 0:
                progress(i / n)
        for k, p in enumerate(procs):
            if p.wait(timeout=60) != 0:
                raise RuntimeError(f"processo {k} do render terminou com erro: {tail(k)}")
    finally:
        for p in procs:
            if p.poll() is None:
                p.kill()
            if p.stdout:
                p.stdout.close()  # se sobrar algum processo, ele sai sozinho ao tentar escrever
        try:
            if w is not None:
                w.close()
        finally:
            for lg in logs:
                lg.close()
            shutil.rmtree(tmp, ignore_errors=True)


def _clear_caches(template: Any) -> None:
    """Os caches de método (lru_cache) ficam na classe e seguram o template — e as fotos do vídeo — na memória do
    servidor depois do render; limpa ao terminar."""
    for klass in type(template).__mro__:
        for v in vars(klass).values():
            if hasattr(v, "cache_clear"):
                try:
                    v.cache_clear()
                except Exception:  # noqa: BLE001
                    pass
