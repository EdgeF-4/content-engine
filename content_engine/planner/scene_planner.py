"""The scene planner: deterministic heuristic core, optional LLM enrichment.

`plan_script` always returns a complete, valid plan with no LLM. When an LLM
completer is passed it refines search queries and on screen copy and may flip
a visual between clip and image, but it can never leave the plan incomplete.
"""
from __future__ import annotations

import json
import re

from ..util import text as T
from .schema import (
    LowerThird, MotionSpec, MusicSpec, Scene, ScenePlan, TitleCard, Transition,
    Visual,
)

_NUMBER = re.compile(r"\b\d[\d,\.]*\b")
_PROPER = re.compile(r"(?<!^)(?<![.!?]\s)\b([A-Z][a-z]{2,})\b")

# A tasteful rotation of soft transitions for scene to scene changes.
_ROTATION = [
    Transition("crossfade", 0.5),
    Transition("slide", 0.45),
    Transition("cut", 0.0),
    Transition("whip", 0.35),
]


def _allocate_durations(weights: list[int], total: float,
                        min_dur: float = 1.2) -> list[float]:
    """Split `total` seconds across beats by word weight, clamped and exact."""
    W = sum(weights) or 1
    raw = [total * w / W for w in weights]
    clamped = [max(min_dur, r) for r in raw]
    s = sum(clamped) or 1.0
    scaled = [c * total / s for c in clamped]
    # Absorb floating point drift into the last scene so the sum is exact.
    scaled[-1] += total - sum(scaled)
    return [round(x, 3) for x in scaled]


def _proper_noun(beat: str) -> str | None:
    m = _PROPER.search(beat)
    return m.group(1) if m else None


def _build_scene(index: int, beat: str, start: float, duration: float,
                 prev_keywords: set[str], prev_had_lt: bool,
                 prev_transition: str) -> Scene:
    kws = T.keywords(beat, limit=4)
    is_clip = T.is_motion(beat)
    query = " ".join(kws[:3]) if kws else "abstract motion background"

    # Transition: a topic shift (no shared keywords) gets a firmer dip to black,
    # but never two dips in a row, so the rotation keeps the cut feeling varied.
    topic_shift = bool(prev_keywords) and not (set(kws) & prev_keywords)
    if index == 0:
        trans = Transition("crossfade", 0.6)        # acts as a fade in
    elif topic_shift and prev_transition != "dip-to-black":
        trans = Transition("dip-to-black", 0.4)
    else:
        trans = _ROTATION[index % len(_ROTATION)]

    # Motion: a number gets an animated counter, stills get a slow zoom.
    num = _NUMBER.search(beat)
    if num:
        motion = MotionSpec("counter", {"value": num.group(0)})
    elif is_clip:
        motion = MotionSpec("static", {})
    else:
        direction = "in" if index % 2 == 0 else "out"
        motion = MotionSpec("ken-burns", {"zoom": 1.12, "direction": direction})

    # Lower third on a named entity, never two scenes in a row.
    lower_third = None
    noun = _proper_noun(beat)
    if noun and not prev_had_lt and index != 0:
        lower_third = LowerThird(text=noun, subtitle="", start=0.4,
                                 duration=min(3.0, max(1.5, duration - 0.6)))

    visual = Visual(
        kind="clip" if is_clip else "image",
        query=query,
        search_terms=kws or ["background"],
        critical=bool(noun) or bool(num),
    )
    return Scene(
        index=index, beat_text=beat, start=round(start, 3),
        duration=duration, word_count=T.word_count(beat), visual=visual,
        transition_in=trans, motion=motion, lower_third=lower_third,
    )


def _heuristic_plan(script: str, vo_duration: float, fps: int, width: int,
                    height: int, title: str | None) -> ScenePlan:
    beats = T.split_beats(script)
    if not beats:
        raise ValueError("script produced no beats")
    weights = [max(1, T.word_count(b)) for b in beats]
    durations = _allocate_durations(weights, vo_duration)

    scenes: list[Scene] = []
    start = 0.0
    prev_keywords: set[str] = set()
    prev_had_lt = False
    prev_transition = ""
    for i, (beat, dur) in enumerate(zip(beats, durations)):
        scene = _build_scene(i, beat, start, dur, prev_keywords, prev_had_lt,
                             prev_transition)
        scenes.append(scene)
        prev_keywords = set(scene.visual.search_terms)
        prev_had_lt = scene.lower_third is not None
        prev_transition = scene.transition_in.type
        start += dur

    head_kws = T.keywords(beats[0], limit=3)
    title_text = title or (T.title_case(beats[0]) if not head_kws
                           else " ".join(head_kws).title())
    title_card = TitleCard(
        text=title_text, subtitle="", start=0.0,
        duration=min(3.0, scenes[0].duration),
    )

    clip_count = sum(1 for s in scenes if s.visual.kind == "clip")
    meta = {
        "vo_duration": round(vo_duration, 3),
        "fps": fps, "width": width, "height": height,
        "word_count": T.word_count(script),
        "beat_count": len(beats),
        "clip_count": clip_count,
        "image_count": len(scenes) - clip_count,
        "clip_ratio": round(clip_count / len(scenes), 3),
        "planner": "heuristic",
        "llm_provider": None,
    }
    return ScenePlan(meta=meta, title_card=title_card, scenes=scenes,
                     music=MusicSpec(), notes=[])


# -- LLM enrichment ------------------------------------------------------

_ENRICH_SYSTEM = (
    "You are a senior short-form video editor planning b-roll and on-screen "
    "text for a voiceover. For each beat you choose whether the visual should "
    "be a clip (motion, action, process) or a still image (concept, person, "
    "place), a concise stock-footage search query, and optional lower-third "
    "copy. Reply with JSON only, no prose."
)


def _enrich_prompt(plan: ScenePlan) -> str:
    beats = [
        {
            "index": s.index,
            "beat": s.beat_text,
            "draft_kind": s.visual.kind,
            "draft_query": s.visual.query,
        }
        for s in plan.scenes
    ]
    schema = {
        "title_card": {"text": "str", "subtitle": "str"},
        "scenes": [{
            "index": "int",
            "kind": "image|clip",
            "query": "short search string",
            "search_terms": ["term"],
            "lower_third": {"text": "str", "subtitle": "str"},
        }],
    }
    return (
        "Beats:\n" + json.dumps(beats, ensure_ascii=False) +
        "\n\nReturn JSON shaped like:\n" + json.dumps(schema) +
        "\nUse null for lower_third when no on-screen label fits. Keep queries "
        "to 2-4 words. Keep title_card text under 8 words."
    )


def _apply_enrichment(plan: ScenePlan, data: dict) -> None:
    tc = data.get("title_card") or {}
    if isinstance(tc, dict) and tc.get("text"):
        plan.title_card.text = str(tc["text"])[:80]
        if tc.get("subtitle"):
            plan.title_card.subtitle = str(tc["subtitle"])[:80]

    by_index = {s.index: s for s in plan.scenes}
    for item in data.get("scenes", []):
        if not isinstance(item, dict):
            continue
        scene = by_index.get(item.get("index"))
        if scene is None:
            continue
        if item.get("kind") in ("image", "clip"):
            scene.visual.kind = item["kind"]
        if item.get("query"):
            scene.visual.query = str(item["query"])[:80]
        terms = item.get("search_terms")
        if isinstance(terms, list) and terms:
            scene.visual.search_terms = [str(t)[:40] for t in terms[:6]]
        lt = item.get("lower_third")
        if isinstance(lt, dict) and lt.get("text"):
            scene.lower_third = LowerThird(
                text=str(lt["text"])[:60], subtitle=str(lt.get("subtitle", ""))[:60],
                start=0.4, duration=min(3.0, max(1.5, scene.duration - 0.6)),
            )

    # Recompute ratio after any clip/image flips.
    clip_count = sum(1 for s in plan.scenes if s.visual.kind == "clip")
    plan.meta["clip_count"] = clip_count
    plan.meta["image_count"] = len(plan.scenes) - clip_count
    plan.meta["clip_ratio"] = round(clip_count / len(plan.scenes), 3)


def plan_script(script: str, vo_duration: float, *, fps: int = 30,
                width: int = 1080, height: int = 1920, title: str | None = None,
                llm=None) -> ScenePlan:
    """Produce a complete scene plan. `llm` is an optional completer callable."""
    plan = _heuristic_plan(script, vo_duration, fps, width, height, title)
    if llm is None:
        return plan
    try:
        from ..llm import extract_json
        reply = llm(_ENRICH_SYSTEM, _enrich_prompt(plan))
        data = extract_json(reply)
        _apply_enrichment(plan, data)
        plan.meta["planner"] = "llm-enriched"
        plan.meta["llm_provider"] = getattr(llm, "provider_name", "llm")
    except Exception as exc:  # never let enrichment break the plan
        plan.notes.append(f"llm enrichment skipped: {exc}")
    return plan
