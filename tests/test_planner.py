import json

from content_engine.planner import plan_script, plan_to_dict
from content_engine.planner.schema import TRANSITIONS, MOTIONS

SCRIPT = (
    "The ocean holds more secrets than we can imagine. "
    "Deep currents are constantly moving across the planet. "
    "Marine biologists study these patterns every single day. "
    "In 2024 a new species was discovered near the Mariana trench. "
    "It changes how scientists think about life under pressure."
)


def test_heuristic_plan_is_complete_and_time_exact():
    plan = plan_script(SCRIPT, vo_duration=20.0, fps=30, width=1080, height=1920)
    assert plan.scenes, "expected scenes"
    total = sum(s.duration for s in plan.scenes)
    assert abs(total - 20.0) < 0.01, f"durations must sum to VO length, got {total}"

    # monotonic, gapless timeline
    cursor = 0.0
    for s in plan.scenes:
        assert abs(s.start - cursor) < 0.01
        cursor += s.duration
        assert s.visual.query
        assert s.visual.kind in ("image", "clip")
        assert s.transition_in.type in TRANSITIONS
        assert s.motion.type in MOTIONS

    assert plan.title_card.text
    assert plan.meta["beat_count"] == len(plan.scenes)
    assert 0.0 <= plan.meta["clip_ratio"] <= 1.0
    assert plan.meta["planner"] == "heuristic"


def test_motion_beat_is_clip_concept_beat_is_image():
    plan = plan_script(
        "Cars race down the crowded highway at full speed. "
        "Philosophy asks deep questions about meaning and truth.",
        vo_duration=10.0,
    )
    kinds = {s.beat_text[:4]: s.visual.kind for s in plan.scenes}
    assert kinds["Cars"] == "clip"
    assert kinds["Phil"] == "image"


def test_number_beat_gets_counter_and_is_critical():
    plan = plan_script(SCRIPT, vo_duration=20.0)
    counters = [s for s in plan.scenes if s.motion.type == "counter"]
    assert counters, "the 2024 beat should produce a counter motion"
    assert all(s.visual.critical for s in counters)


def test_plan_is_json_serializable():
    plan = plan_script(SCRIPT, vo_duration=15.0)
    d = plan_to_dict(plan)
    s = json.dumps(d)  # must not raise
    assert json.loads(s)["meta"]["vo_duration"] == 15.0


def test_llm_enrichment_merges_and_marks_provider():
    def fake_llm(system, user, image_path=None):
        return json.dumps({
            "title_card": {"text": "Secrets Of The Deep", "subtitle": "Part 1"},
            "scenes": [
                {"index": 0, "kind": "clip", "query": "deep ocean waves",
                 "search_terms": ["ocean", "deep", "waves"],
                 "lower_third": {"text": "The Deep", "subtitle": ""}},
            ],
        })
    fake_llm.provider_name = "nim"

    plan = plan_script(SCRIPT, vo_duration=20.0, llm=fake_llm)
    assert plan.title_card.text == "Secrets Of The Deep"
    assert plan.title_card.subtitle == "Part 1"
    s0 = plan.scenes[0]
    assert s0.visual.kind == "clip"
    assert s0.visual.query == "deep ocean waves"
    assert s0.lower_third and s0.lower_third.text == "The Deep"
    assert plan.meta["planner"] == "llm-enriched"
    assert plan.meta["llm_provider"] == "nim"


def test_llm_failure_falls_back_to_heuristic():
    def broken_llm(system, user, image_path=None):
        raise RuntimeError("network down")

    plan = plan_script(SCRIPT, vo_duration=20.0, llm=broken_llm)
    assert plan.meta["planner"] == "heuristic"
    assert any("enrichment skipped" in n for n in plan.notes)
