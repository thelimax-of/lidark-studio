"""Utilidades de mídia: localizar FFmpeg, detectar NVENC, duração de arquivos."""
from __future__ import annotations

import functools
import shutil
import subprocess
from pathlib import Path

from . import config

TOOLS = Path(__file__).resolve().parents[1] / "tools"


@functools.lru_cache
def ffmpeg_exe() -> str:
    for cand in (shutil.which("ffmpeg"), TOOLS / "ffmpeg" / "bin" / "ffmpeg.exe"):
        if cand and Path(cand).exists():
            return str(cand)
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


@functools.lru_cache
def nvenc_ok() -> bool:
    """Testa de verdade (o encoder pode existir mas a GPU não estar disponível)."""
    if not config.get("use_nvenc"):
        return False
    try:
        r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                            "color=black:s=256x256:d=0.2", "-c:v", "h264_nvenc", "-f", "null", "-"],
                           capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def ffmpeg_info() -> dict:
    return {"path": ffmpeg_exe(), "nvenc": nvenc_ok()}


def video_encoder_args(quality: str = "high") -> list[str]:
    if nvenc_ok():
        return ["-c:v", "h264_nvenc", "-preset", "p6", "-tune", "hq", "-rc", "vbr", "-cq", "19",
                "-b:v", "12M", "-maxrate", "20M", "-bufsize", "24M", "-profile:v", "high", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "medium" if quality == "high" else "veryfast", "-crf", "19",
            "-profile:v", "high", "-pix_fmt", "yuv420p"]


def run_ffmpeg(args: list[str], timeout: int = 1800) -> None:
    r = subprocess.run([ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args],
                       capture_output=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("FFmpeg falhou: " + r.stderr.decode(errors="ignore")[-1500:])


def audio_duration(path: str | Path) -> float:
    import av
    with av.open(str(path)) as c:
        if c.duration:
            return c.duration / 1_000_000
        s = c.streams.audio[0]
        return float(s.duration * s.time_base) if s.duration else 0.0


def decode_audio(path: str | Path, sr: int = 24000):
    """Decodifica qualquer áudio para numpy float32 mono."""
    import numpy as np
    out = Path(path).with_suffix(".tmp.f32")
    run_ffmpeg(["-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", str(out)])
    data = np.fromfile(out, dtype=np.float32)
    out.unlink(missing_ok=True)
    return data
