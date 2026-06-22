"""Command line interface.

Subcommands mirror the pipeline stages. `run` chains them all:

    python -m content_engine run --script s.txt --voiceover vo.wav --out out.mp4

Each stage can also run on its own against a shared work directory, which is
handy for inspecting or re-running a single step.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Config
from .pipeline import (
    Dims, dims_from_config, plan_stage, source_stage, qc_stage, render_stage,
    run_all,
)
from .util import media


def _config(args) -> Config:
    return Config.load(args.config)


def _work_dir(args, default_stem: str) -> Path:
    wd = Path(args.work_dir) if args.work_dir else (
        Path(__file__).resolve().parents[1] / "work" / default_stem)
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def cmd_plan(args) -> int:
    config = _config(args)
    work_dir = _work_dir(args, Path(args.script).stem)
    dims = dims_from_config(config, test=args.test)
    vo_duration = media.ffprobe_duration(args.voiceover)
    plan_stage(Path(args.script).read_text(), vo_duration, config, work_dir,
               dims=dims, use_llm=not args.no_llm, title=args.title)
    print(f"wrote {work_dir / 'scene_plan.json'}")
    return 0


def cmd_source(args) -> int:
    config = _config(args)
    work_dir = _work_dir(args, "job")
    source_stage(config, work_dir, offline=args.offline)
    print(f"wrote {work_dir / 'sourced_plan.json'}")
    return 0


def cmd_qc(args) -> int:
    config = _config(args)
    work_dir = _work_dir(args, "job")
    qc_stage(config, work_dir, use_llm=not args.no_llm)
    print(f"wrote {work_dir / 'qc_plan.json'}")
    return 0


def cmd_render(args) -> int:
    work_dir = _work_dir(args, "job")
    out = render_stage(work_dir, args.voiceover, out_path=args.out,
                       concurrency=args.concurrency)
    print(f"rendered {out}")
    return 0


def cmd_run(args) -> int:
    config = _config(args)
    out = run_all(args.script, args.voiceover, config=config,
                  work_dir=args.work_dir, out_path=args.out, test=args.test,
                  offline=args.offline, use_llm=not args.no_llm,
                  title=args.title, concurrency=args.concurrency)
    print(f"\nvideo ready: {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="content-engine",
                                description="Script plus voiceover to a video.")
    p.add_argument("--config", default=None, help="path to config.json")
    sub = p.add_subparsers(dest="command", required=True)

    def add_common(sp):
        sp.add_argument("--work-dir", default=None,
                        help="job directory for stage artifacts")

    sp = sub.add_parser("plan", help="script -> scene plan")
    add_common(sp)
    sp.add_argument("--script", required=True)
    sp.add_argument("--voiceover", required=True, help="used for timing")
    sp.add_argument("--title", default=None)
    sp.add_argument("--test", action="store_true", help="test dimensions")
    sp.add_argument("--no-llm", action="store_true")
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser("source", help="scene plan -> sourced assets")
    add_common(sp)
    sp.add_argument("--offline", action="store_true",
                    help="synthesize placeholders, no network")
    sp.set_defaults(func=cmd_source)

    sp = sub.add_parser("qc", help="sourced plan -> quality checked plan")
    add_common(sp)
    sp.add_argument("--no-llm", action="store_true")
    sp.set_defaults(func=cmd_qc)

    sp = sub.add_parser("render", help="qc plan -> rendered mp4")
    add_common(sp)
    sp.add_argument("--voiceover", required=True)
    sp.add_argument("--out", default=None)
    sp.add_argument("--concurrency", type=int, default=None)
    sp.set_defaults(func=cmd_render)

    sp = sub.add_parser("run", help="full pipeline: script + voiceover -> mp4")
    sp.add_argument("--script", required=True)
    sp.add_argument("--voiceover", required=True)
    sp.add_argument("--out", default=None)
    sp.add_argument("--work-dir", default=None)
    sp.add_argument("--title", default=None)
    sp.add_argument("--test", action="store_true",
                    help="small fast dimensions for a quick render")
    sp.add_argument("--offline", action="store_true",
                    help="placeholder assets, no network")
    sp.add_argument("--no-llm", action="store_true")
    sp.add_argument("--concurrency", type=int, default=None)
    sp.set_defaults(func=cmd_run)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
