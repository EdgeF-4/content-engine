from pathlib import Path

from content_engine.config import Config
from content_engine.planner import plan_script, plan_to_dict
from content_engine.sourcing import source_plan
from content_engine.qc import review_plan
from content_engine.render import build_render_props
from content_engine.util import media

SCRIPT = (
    "Cars race down the open highway at full speed. "
    "The quiet mind reflects on meaning and truth. "
    "In 2024 the team measured a record near the Mariana ridge."
)


def _qc_plan(tmp_path, w=128, h=128, fps=12):
    cfg = Config({"sourcing": {"image_provider": "pexels", "video_provider": "pexels"}})
    plan = plan_to_dict(plan_script(SCRIPT, vo_duration=6.0, fps=fps, width=w, height=h))
    sourced = source_plan(plan, cfg, tmp_path, offline=True)
    return sourced


def test_props_are_contiguous_and_total_matches(tmp_path):
    sourced = _qc_plan(tmp_path)
    reviewed = review_plan(sourced)
    remotion_dir = tmp_path / "remotion"
    vo = media.silent_audio(tmp_path / "vo.wav", 6.0)
    props = build_render_props(reviewed, tmp_path, vo, remotion_dir=remotion_dir)

    total = props["durationInFrames"]
    assert total == round(6.0 * 12)
    cursor = 0
    for s in props["scenes"]:
        assert s["startFrame"] == cursor
        cursor += s["durationFrames"]
    assert cursor == total


def test_assets_are_staged_under_public(tmp_path):
    sourced = _qc_plan(tmp_path)
    reviewed = review_plan(sourced)
    remotion_dir = tmp_path / "remotion"
    vo = media.silent_audio(tmp_path / "vo.wav", 6.0)
    props = build_render_props(reviewed, tmp_path, vo, remotion_dir=remotion_dir)

    public = remotion_dir / "public"
    assert (public / props["voiceover"]).exists()
    assert (public / props["music"]).exists()
    for s in props["scenes"]:
        assert (public / s["asset"]["path"]).exists()
    # props file written for the renderer
    assert (tmp_path / "render_props.json").exists()


def test_flagged_image_is_actually_upscaled(tmp_path):
    W, H = 256, 256
    sourced = _qc_plan(tmp_path, w=W, h=H)
    # Force scene 1 (the concept/image beat) to look like a small real asset
    # that is script critical, so QC flags it for upscale.
    target = next(s for s in sourced["scenes"] if s["visual"]["kind"] == "image")
    src_file = target["visual"]["source"]["path"]
    target["visual"]["critical"] = True
    target["visual"]["source"].update(
        {"provider": "pexels", "width": 80, "height": 80})

    reviewed = review_plan(sourced)
    tgt_qc = next(s for s in reviewed["scenes"] if s["index"] == target["index"])
    assert tgt_qc["qc"]["verdict"] == "flag-upscale"

    remotion_dir = tmp_path / "remotion"
    vo = media.silent_audio(tmp_path / "vo.wav", 6.0)
    props = build_render_props(reviewed, tmp_path, vo, remotion_dir=remotion_dir)

    staged = remotion_dir / "public" / next(
        s["asset"]["path"] for s in props["scenes"] if s["index"] == target["index"])
    assert media.ffprobe_dimensions(staged) == (W, H)
    _ = src_file  # the original small asset was the upscale input
