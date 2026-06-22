import json

from content_engine.qc import review_plan


def _scene(index, kind, critical, src, beat="A beat about something."):
    return {
        "index": index, "beat_text": beat, "start": 0.0, "duration": 3.0,
        "word_count": 4,
        "visual": {"kind": kind, "query": "q", "search_terms": ["q"],
                   "critical": critical, "source": src},
        "transition_in": {"type": "cut", "duration": 0.0},
        "motion": {"type": "static", "params": {}},
        "lower_third": None,
    }


def _plan(scenes, w=1080, h=1920):
    return {
        "meta": {"width": w, "height": h, "fps": 30, "vo_duration": 9.0},
        "title_card": {"text": "T", "subtitle": "", "start": 0, "duration": 3},
        "scenes": scenes,
        "music": {"track": "default", "gain_db": -22.0},
    }


def test_accept_high_res_match():
    plan = _plan([_scene(0, "image", False,
                         {"provider": "pexels", "width": 1080, "height": 1920})])
    out = review_plan(plan)
    assert out["scenes"][0]["qc"]["verdict"] == "accept"
    assert out["qc_summary"]["passed"] is True


def test_flag_upscale_for_critical_low_res():
    plan = _plan([_scene(0, "image", True,
                         {"provider": "pexels", "width": 540, "height": 960})])
    out = review_plan(plan)
    assert out["scenes"][0]["qc"]["verdict"] == "flag-upscale"
    assert out["scenes"][0]["qc"]["action"] == "upscale"


def test_reject_noncritical_tiny():
    plan = _plan([_scene(0, "image", False,
                         {"provider": "pexels", "width": 320, "height": 240})])
    out = review_plan(plan)
    assert out["scenes"][0]["qc"]["verdict"] == "reject"
    assert out["qc_summary"]["passed"] is False


def test_placeholder_always_accepted():
    plan = _plan([_scene(0, "image", True,
                         {"provider": "placeholder", "width": 1080, "height": 1920})])
    out = review_plan(plan)
    assert out["scenes"][0]["qc"]["verdict"] == "accept"


def test_vision_offtopic_rejects_noncritical():
    def fake_vision(system, user, image_path=None):
        return json.dumps({"relevance": 1, "quality": 4, "note": "unrelated"})

    plan = _plan([_scene(0, "image", False,
                         {"provider": "pexels", "width": 1080, "height": 1920,
                          "path": "/tmp/x.jpg"})])
    out = review_plan(plan, llm=fake_vision)
    qc = out["scenes"][0]["qc"]
    assert qc["verdict"] == "reject"
    assert qc["scores"]["relevance"] == 1


def test_vision_offtopic_flags_critical():
    def fake_vision(system, user, image_path=None):
        return json.dumps({"relevance": 2, "quality": 3, "note": "weak"})

    plan = _plan([_scene(0, "image", True,
                         {"provider": "pexels", "width": 1080, "height": 1920,
                          "path": "/tmp/x.jpg"})])
    out = review_plan(plan, llm=fake_vision)
    assert out["scenes"][0]["qc"]["verdict"] == "flag-upscale"


def test_summary_counts():
    plan = _plan([
        _scene(0, "image", False, {"provider": "pexels", "width": 1080, "height": 1920}),
        _scene(1, "image", True, {"provider": "pexels", "width": 540, "height": 960}),
        _scene(2, "image", False, {"provider": "pexels", "width": 200, "height": 200}),
    ])
    out = review_plan(plan)
    s = out["qc_summary"]
    assert s["accepted"] == 1 and s["flagged_upscale"] == 1 and s["rejected"] == 1
    assert s["total"] == 3
