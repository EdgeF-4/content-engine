"""Thin wrappers over ffmpeg, ffprobe, and espeak-ng.

Kept small and dependency free so every other module can probe media and
synthesize placeholder assets without pulling in heavy libraries.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

# A small, readable palette for placeholder visuals.
_PALETTE = [
    "0x1f2937", "0x374151", "0x4b5563", "0x1e3a8a",
    "0x065f46", "0x7c2d12", "0x581c87", "0x9d174d",
]


class MediaError(RuntimeError):
    pass


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise MediaError(f"command failed: {' '.join(cmd)}\n{proc.stderr.strip()}")
    return proc


def ffprobe_duration(path: str | Path) -> float:
    """Return media duration in seconds."""
    proc = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path),
    ])
    data = json.loads(proc.stdout)
    return float(data["format"]["duration"])


def ffprobe_dimensions(path: str | Path) -> tuple[int, int]:
    """Return (width, height) of the first video/image stream."""
    proc = _run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", str(path),
    ])
    stream = json.loads(proc.stdout)["streams"][0]
    return int(stream["width"]), int(stream["height"])


def generate_voiceover(text: str, out_path: str | Path, wpm: int = 165) -> Path:
    """Synthesize a spoken-word WAV from text using espeak-ng.

    Used to produce a short example voiceover and for the end to end test.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(["espeak-ng", "-s", str(wpm), "-w", str(out), text])
    return out


def _color(index: int) -> str:
    return _PALETTE[index % len(_PALETTE)]


def _escape_drawtext(text: str) -> str:
    # ffmpeg drawtext is picky about colons, quotes, and percent signs.
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "")
        .replace("%", "\\%")
    )


def placeholder_image(out_path: str | Path, label: str, width: int, height: int,
                      index: int = 0) -> Path:
    """Render a solid color still with a centered label."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = _escape_drawtext(label[:40])
    draw = (
        f"drawtext=text='{text}':fontcolor=white:fontsize={max(18, height // 16)}"
        f":x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxcolor=black@0.35:boxborderw=12"
    )
    _run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={_color(index)}:s={width}x{height}",
        "-vf", draw, "-frames:v", "1", str(out),
    ])
    return out


def placeholder_video(out_path: str | Path, label: str, width: int, height: int,
                      seconds: float, fps: int = 24, index: int = 0) -> Path:
    """Render a short solid color clip with a label and gentle motion."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    text = _escape_drawtext(label[:40])
    # A drifting label gives the clip visible motion so it reads as video.
    draw = (
        f"drawtext=text='{text}':fontcolor=white:fontsize={max(18, height // 16)}"
        f":x=(w-text_w)/2+40*sin(t):y=(h-text_h)/2:box=1:boxcolor=black@0.35:boxborderw=12"
    )
    _run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c={_color(index)}:s={width}x{height}:d={seconds:.3f}:r={fps}",
        "-vf", draw, "-t", f"{seconds:.3f}", "-pix_fmt", "yuv420p", str(out),
    ])
    return out


def upscale_image(src: str | Path, out_path: str | Path, width: int,
                  height: int) -> Path:
    """Upscale a still to cover the target frame using Lanczos.

    Used when QC flags a script critical image as too small. It is a real
    resample, not a stretch: the image is scaled to cover and center cropped.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={width}:{height}"
    )
    _run(["ffmpeg", "-y", "-i", str(src), "-vf", vf, "-frames:v", "1", str(out)])
    return out


def silent_audio(out_path: str | Path, seconds: float) -> Path:
    """Generate a silent WAV of a given length (used in tests)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=channel_layout=mono:sample_rate=22050",
        "-t", f"{seconds:.3f}", str(out),
    ])
    return out
