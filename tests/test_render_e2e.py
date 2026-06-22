"""End to end render smoke test.

Skipped by default so the suite stays fast and offline. Enable it with
CE_RENDER_TEST=1 to render a short video through the real Remotion project and
assert a valid MP4 with audio comes out.

    CE_RENDER_TEST=1 python -m pytest tests/test_render_e2e.py -q
"""
import os
import shutil

import pytest

from content_engine.config import Config
from content_engine.pipeline import run_all
from content_engine.render import REMOTION_DIR
from content_engine.util import media

pytestmark = pytest.mark.skipif(
    os.environ.get("CE_RENDER_TEST") != "1",
    reason="set CE_RENDER_TEST=1 to run the heavy Remotion render",
)


def test_full_pipeline_renders_mp4(tmp_path):
    if not (REMOTION_DIR / "node_modules").exists():
        pytest.skip("remotion dependencies not installed")

    script = tmp_path / "script.txt"
    script.write_text(
        "Cars race across the bright city at night. "
        "A calm voice explains one simple idea."
    )
    vo = media.generate_voiceover(script.read_text(), tmp_path / "vo.wav")
    out = tmp_path / "out.mp4"

    cfg = Config({"render": {"test_width": 256, "test_height": 144, "test_fps": 12},
                  "sourcing": {"image_provider": "pexels", "video_provider": "pexels"}})
    result = run_all(script, vo, config=cfg, work_dir=tmp_path / "job",
                     out_path=out, test=True, offline=True, use_llm=False,
                     log=lambda *_: None)

    assert result.exists() and result.stat().st_size > 10_000
    assert abs(media.ffprobe_duration(out) - media.ffprobe_duration(vo)) < 0.5
    w, h = media.ffprobe_dimensions(out)
    assert (w, h) == (256, 144)
    # clean staged assets for this job from the shared public folder
    shutil.rmtree(REMOTION_DIR / "public" / "render-assets" / "job",
                  ignore_errors=True)
