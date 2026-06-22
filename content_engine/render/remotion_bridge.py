"""Bridge between the Python pipeline and the Remotion renderer.

`build_render_props` flattens a QC approved plan into one props document the
composition consumes, staging every asset into the Remotion `public/` folder
and converting seconds to frames. Scene frame boundaries are contiguous and
gapless and the total equals round(voiceover_seconds * fps), so the rendered
video lines up with the voiceover exactly. `render_video` invokes the CLI.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from ..config import REPO_ROOT
from ..util import media

REMOTION_DIR = REPO_ROOT / "remotion"
DEFAULT_ACCENT = "#09f097"


def _safe_job_id(name: str) -> str:
    jid = re.sub(r"[^A-Za-z0-9_-]", "-", name).strip("-")
    return jid or "job"


def _db_to_linear(db: float) -> float:
    return round(10 ** (db / 20.0), 4)


def _frame_boundaries(scenes: list[dict], fps: int, total_frames: int) -> list[tuple[int, int]]:
    """Contiguous (startFrame, durationFrames) pairs covering [0, total_frames)."""
    starts = [round(s["start"] * fps) for s in scenes]
    starts[0] = 0
    bounds = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else total_frames
        bounds.append((start, max(1, end - start)))
    return bounds


def build_render_props(plan: dict, work_dir: str | Path, voiceover_path: str | Path,
                       *, remotion_dir: str | Path | None = None,
                       accent: str = DEFAULT_ACCENT) -> dict:
    plan = json.loads(json.dumps(plan))  # deep copy
    work_dir = Path(work_dir)
    remotion_dir = Path(remotion_dir) if remotion_dir else REMOTION_DIR

    meta = plan["meta"]
    fps, W, H = meta["fps"], meta["width"], meta["height"]
    vo_duration = meta["vo_duration"]
    total_frames = max(1, round(vo_duration * fps))

    job_id = _safe_job_id(work_dir.name)
    stage = remotion_dir / "public" / "render-assets" / job_id
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=True)

    def rel(name: str) -> str:
        return f"render-assets/{job_id}/{name}"

    bounds = _frame_boundaries(plan["scenes"], fps, total_frames)
    scene_props = []
    for scene, (start_f, dur_f) in zip(plan["scenes"], bounds):
        visual = scene["visual"]
        src = visual.get("source") or {}
        kind = visual["kind"]
        src_path = src.get("path")
        verdict = scene.get("qc", {}).get("verdict", "accept")

        ext = (Path(src_path).suffix if src_path else "") or (
            ".mp4" if kind == "clip" else ".jpg")
        dest_name = f"scene_{scene['index']:02d}{ext}"
        dest = stage / dest_name
        if verdict == "flag-upscale" and kind == "image" and src_path:
            media.upscale_image(src_path, dest, W, H)
        elif src_path:
            shutil.copy(src_path, dest)
        else:  # nothing sourced: synthesize a labeled still so there is no gap
            media.placeholder_image(dest, visual.get("query", "scene"), W, H,
                                    index=scene["index"])

        trans = scene["transition_in"]
        lt = scene.get("lower_third")
        lower_third = None
        if lt:
            lt_start = max(0, round(lt["start"] * fps))
            lt_dur = max(1, round(lt["duration"] * fps))
            lt_dur = min(lt_dur, max(1, dur_f - lt_start))
            lower_third = {
                "text": lt["text"], "subtitle": lt.get("subtitle", ""),
                "startFrame": lt_start, "durationFrames": lt_dur,
            }

        scene_props.append({
            "index": scene["index"],
            "startFrame": start_f,
            "durationFrames": dur_f,
            "asset": {"kind": kind, "path": rel(dest_name)},
            "transition": {
                "type": trans["type"],
                "durationFrames": max(0, round(trans.get("duration", 0) * fps)),
            },
            "motion": {"type": scene["motion"]["type"],
                       "params": scene["motion"].get("params", {})},
            "lowerThird": lower_third,
            "query": visual.get("query", ""),
        })

    # Title card.
    tc = plan["title_card"]
    tc_start = max(0, round(tc["start"] * fps))
    tc_dur = min(total_frames, max(1, round(tc["duration"] * fps)))
    title_card = {"text": tc["text"], "subtitle": tc.get("subtitle", ""),
                  "startFrame": tc_start, "durationFrames": tc_dur}

    # Audio: voiceover, music bed, transition sfx.
    vo_ext = Path(voiceover_path).suffix or ".wav"
    shutil.copy(voiceover_path, stage / f"vo{vo_ext}")
    voiceover_rel = rel(f"vo{vo_ext}")

    music_rel = None
    music_path = (plan.get("music") or {}).get("path")
    if music_path and Path(music_path).exists():
        m_ext = Path(music_path).suffix or ".wav"
        shutil.copy(music_path, stage / f"music{m_ext}")
        music_rel = rel(f"music{m_ext}")
    music_gain = (plan.get("music") or {}).get("gain_db", -22.0)

    sfx_rel = None
    sfx_path = (plan.get("audio_assets") or {}).get("transition_sfx")
    if sfx_path and Path(sfx_path).exists():
        s_ext = Path(sfx_path).suffix or ".wav"
        shutil.copy(sfx_path, stage / f"whoosh{s_ext}")
        sfx_rel = rel(f"whoosh{s_ext}")

    props = {
        "width": W, "height": H, "fps": fps,
        "durationInFrames": total_frames,
        "voiceover": voiceover_rel,
        "music": music_rel,
        "transitionSfx": sfx_rel,
        "musicVolume": _db_to_linear(music_gain),
        "accentColor": accent,
        "titleCard": title_card,
        "scenes": scene_props,
    }

    props_path = work_dir / "render_props.json"
    props_path.write_text(json.dumps(props, indent=2))
    return props


def render_video(props_path: str | Path, out_path: str | Path, *,
                 remotion_dir: str | Path | None = None,
                 concurrency: int | None = None, log_cb=None) -> Path:
    remotion_dir = Path(remotion_dir) if remotion_dir else REMOTION_DIR
    out_path = Path(out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    props_path = Path(props_path).resolve()

    cmd = ["npx", "remotion", "render", "Video", str(out_path),
           f"--props={props_path}"]
    if concurrency:
        cmd.append(f"--concurrency={concurrency}")

    proc = subprocess.Popen(cmd, cwd=str(remotion_dir), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines: list[str] = []
    for line in proc.stdout:  # type: ignore[union-attr]
        lines.append(line)
        if log_cb:
            log_cb(line.rstrip())
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(
            "remotion render failed:\n" + "".join(lines[-25:]))
    if not out_path.exists():
        raise RuntimeError(f"render reported success but {out_path} is missing")
    return out_path
