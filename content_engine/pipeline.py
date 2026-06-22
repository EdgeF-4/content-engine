"""Stage orchestration: plan, source, qc, render, and the full run.

Each stage reads and writes a JSON artifact in the job's work directory, so a
run can be inspected or resumed at any boundary. The CLI is a thin front end
over these functions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .llm import completer_for_role
from .planner import plan_script, plan_to_dict
from .sourcing import source_plan
from .qc import review_plan
from .render import build_render_props, render_video
from .util import media

PLAN_FILE = "scene_plan.json"
SOURCED_FILE = "sourced_plan.json"
QC_FILE = "qc_plan.json"
OUTPUT_FILE = "output.mp4"


@dataclass
class Dims:
    width: int
    height: int
    fps: int


def dims_from_config(config: Config, test: bool = False) -> Dims:
    r = config.render
    if test:
        return Dims(r.get("test_width", 640), r.get("test_height", 360),
                    r.get("test_fps", 24))
    return Dims(r.get("width", 1080), r.get("height", 1920), r.get("fps", 30))


def _write(work_dir: Path, name: str, data: dict) -> Path:
    p = work_dir / name
    p.write_text(json.dumps(data, indent=2))
    return p


def _read(work_dir: Path, name: str) -> dict:
    return json.loads((work_dir / name).read_text())


def plan_stage(script: str, vo_duration: float, config: Config, work_dir: Path,
               *, dims: Dims, use_llm: bool = True, title: str | None = None,
               log=print) -> dict:
    llm = completer_for_role(config, "scene_planning") if use_llm else None
    if llm:
        log(f"  planning with {getattr(llm, 'provider_name', 'llm')}")
    else:
        log("  planning with built-in heuristic")
    plan = plan_to_dict(plan_script(
        script, vo_duration, fps=dims.fps, width=dims.width, height=dims.height,
        title=title, llm=llm))
    _write(work_dir, PLAN_FILE, plan)
    m = plan["meta"]
    log(f"  {m['beat_count']} scenes, clip ratio {m['clip_ratio']}")
    return plan


def source_stage(config: Config, work_dir: Path, *, offline: bool = False,
                 plan: dict | None = None, log=print) -> dict:
    plan = plan or _read(work_dir, PLAN_FILE)
    log(f"  sourcing {len(plan['scenes'])} visuals"
        + (" (offline placeholders)" if offline else ""))
    sourced = source_plan(plan, config, work_dir, offline=offline)
    _write(work_dir, SOURCED_FILE, sourced)
    return sourced


def qc_stage(config: Config, work_dir: Path, *, use_llm: bool = True,
             plan: dict | None = None, log=print) -> dict:
    plan = plan or _read(work_dir, SOURCED_FILE)
    llm = completer_for_role(config, "qc") if use_llm else None
    reviewed = review_plan(plan, llm=llm)
    s = reviewed["qc_summary"]
    log(f"  qc: {s['accepted']} accepted, {s['flagged_upscale']} flagged, "
        f"{s['rejected']} rejected")
    _write(work_dir, QC_FILE, reviewed)
    return reviewed


def render_stage(work_dir: Path, voiceover_path: str | Path, *,
                 out_path: str | Path | None = None, plan: dict | None = None,
                 concurrency: int | None = None, accent: str = "#09f097",
                 log=print) -> Path:
    plan = plan or _read(work_dir, QC_FILE)
    out_path = Path(out_path) if out_path else work_dir / OUTPUT_FILE
    log("  building render props and staging assets")
    build_render_props(plan, work_dir, voiceover_path, accent=accent)
    log("  rendering with Remotion (this is the heavy step)")
    return render_video(work_dir / "render_props.json", out_path,
                        concurrency=concurrency, log_cb=lambda l: None)


def run_all(script_path: str | Path, voiceover_path: str | Path, *,
            config: Config | None = None, work_dir: str | Path | None = None,
            out_path: str | Path | None = None, test: bool = False,
            offline: bool = False, use_llm: bool = True,
            title: str | None = None, concurrency: int | None = None,
            log=print) -> Path:
    config = config or Config.load()
    script = Path(script_path).read_text()
    work_dir = Path(work_dir) if work_dir else (
        Path(__file__).resolve().parents[1] / "work" / Path(script_path).stem)
    work_dir.mkdir(parents=True, exist_ok=True)
    dims = dims_from_config(config, test=test)

    log("[1/4] scene plan")
    vo_duration = media.ffprobe_duration(voiceover_path)
    plan = plan_stage(script, vo_duration, config, work_dir, dims=dims,
                      use_llm=use_llm, title=title, log=log)

    log("[2/4] sourcing")
    sourced = source_stage(config, work_dir, offline=offline, plan=plan, log=log)

    log("[3/4] quality check")
    reviewed = qc_stage(config, work_dir, use_llm=use_llm, plan=sourced, log=log)

    log("[4/4] render")
    out = render_stage(work_dir, voiceover_path, out_path=out_path,
                       plan=reviewed, concurrency=concurrency, log=log)
    log(f"done: {out}")
    return out
