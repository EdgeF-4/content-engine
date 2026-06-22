from pathlib import Path

from content_engine.config import Config
from content_engine.planner import plan_script, plan_to_dict
from content_engine.sourcing import source_plan
from content_engine.sourcing import images, videos
from content_engine.sourcing.asset_manager import select_best
from content_engine.sourcing.local_assets import LocalLibrary

PEXELS_IMG = {
    "photos": [
        {"id": 1, "width": 4000, "height": 6000, "url": "https://p/1",
         "photographer": "Ada", "src": {"large2x": "https://img/1.jpg"}},
        {"id": 2, "width": 1920, "height": 1080, "url": "https://p/2",
         "photographer": "Bo", "src": {"original": "https://img/2.jpg"}},
    ]
}
PIXABAY_IMG = {
    "hits": [
        {"id": 9, "imageWidth": 3000, "imageHeight": 2000,
         "largeImageURL": "https://px/9.jpg", "pageURL": "https://px/p9",
         "user": "Cy"},
    ]
}
PEXELS_VID = {
    "videos": [
        {"id": 5, "width": 1920, "height": 1080, "url": "https://v/5",
         "duration": 12, "user": {"name": "Di"},
         "video_files": [
             {"quality": "hd", "width": 1280, "height": 720,
              "file_type": "video/mp4", "link": "https://v/5-hd.mp4"},
             {"quality": "uhd", "width": 3840, "height": 2160,
              "file_type": "video/mp4", "link": "https://v/5-4k.mp4"},
         ]},
    ]
}


def test_parse_pexels_images():
    cands = images.parse_pexels_images(PEXELS_IMG)
    assert len(cands) == 2
    assert cands[0]["download_url"] == "https://img/1.jpg"
    assert cands[0]["author"] == "Ada"
    assert cands[0]["kind"] == "image"


def test_parse_pixabay_images():
    cands = images.parse_pixabay_images(PIXABAY_IMG)
    assert cands[0]["page_url"] == "https://px/p9"
    assert cands[0]["width"] == 3000


def test_parse_pexels_videos_caps_resolution():
    cands = videos.parse_pexels_videos(PEXELS_VID)
    assert len(cands) == 1
    # 4K file is over the cap, so the HD file is chosen
    assert cands[0]["download_url"] == "https://v/5-hd.mp4"
    assert cands[0]["duration"] == 12.0


def test_select_best_prefers_portrait_coverage():
    cands = [
        {"width": 1920, "height": 1080, "id": "land"},
        {"width": 1080, "height": 1920, "id": "port-hd"},
        {"width": 540, "height": 960, "id": "port-sd"},
    ]
    best = select_best(cands, target_w=1080, target_h=1920)
    assert best["id"] == "port-hd"


def test_select_best_handles_empty():
    assert select_best([], 1080, 1920) is None


def test_local_library_finds_shipped_music_and_sfx():
    lib = LocalLibrary()
    assert lib.default_music() is not None
    assert lib.default_music().name == "ambient_bed.wav"
    assert lib.sfx("whoosh") is not None


def test_source_plan_offline_creates_placeholders(tmp_path):
    cfg = Config({"sourcing": {"image_provider": "pexels", "video_provider": "pexels"}})
    plan = plan_to_dict(plan_script(
        "Cars race down the highway fast. The mind ponders quiet truth.",
        vo_duration=4.0, fps=24, width=256, height=256,
    ))
    sourced = source_plan(plan, cfg, tmp_path, offline=True)
    for scene in sourced["scenes"]:
        src = scene["visual"]["source"]
        assert src["provider"] == "placeholder"
        assert Path(src["path"]).exists()
    assert sourced["music"]["path"].endswith("ambient_bed.wav")
    assert sourced["meta"]["offline_sourcing"] is True


def test_source_plan_no_key_falls_back_even_when_online(tmp_path):
    cfg = Config({"sourcing": {"image_provider": "pexels", "pexels": {"api_key": ""}}})
    plan = plan_to_dict(plan_script("A quiet concept about meaning.",
                                    vo_duration=3.0, fps=24, width=256, height=256))
    sourced = source_plan(plan, cfg, tmp_path, offline=False)
    assert all(s["visual"]["source"]["provider"] == "placeholder"
               for s in sourced["scenes"])
