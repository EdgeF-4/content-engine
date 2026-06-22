"""Quality check: score each sourced visual, then accept, reject, or flag.

The heuristic enforces the measurable rules from `guidelines.md` (resolution,
orientation) on metadata alone, so it runs offline and deterministically. When
a vision completer is supplied it adds a relevance judgement read from the
image. Script critical visuals are never silently dropped; weak ones are
flagged for upscale or manual review instead.
"""
from __future__ import annotations

import json
from pathlib import Path

GUIDELINES_PATH = Path(__file__).resolve().parent / "guidelines.md"

# Thresholds mirror guidelines.md.
ACCEPT_AREA = 0.90
FLAG_AREA = 0.45
RELEVANCE_REJECT = 2  # vision score 1-5; at or below this is off topic

ACCEPT, FLAG, REJECT = "accept", "flag-upscale", "reject"
ACTION = {ACCEPT: "keep", FLAG: "upscale", REJECT: "resource"}


def _area_ratio(src: dict, target_w: int, target_h: int) -> float:
    target = max(1, target_w * target_h)
    return (src.get("width", 0) * src.get("height", 0)) / target


def _orientation_match(src: dict, target_w: int, target_h: int) -> bool:
    sw, sh = src.get("width", 0), src.get("height", 0)
    if not sw or not sh:
        return True
    return (sh >= sw) == (target_h >= target_w)


def _heuristic_verdict(src: dict, critical: bool, target_w: int,
                       target_h: int) -> tuple[str, list[str], dict]:
    reasons: list[str] = []
    ratio = _area_ratio(src, target_w, target_h)
    orient = _orientation_match(src, target_w, target_h)
    scores = {"area_ratio": round(ratio, 3), "orientation_match": orient}

    if src.get("provider") == "placeholder":
        return ACCEPT, ["synthetic placeholder, built to fit the frame"], scores

    if not orient:
        reasons.append("orientation mismatch, renderer will crop to fill")

    if ratio >= ACCEPT_AREA:
        verdict = ACCEPT
    elif ratio >= FLAG_AREA:
        if critical:
            verdict = FLAG
            reasons.append("script critical and below full resolution")
        else:
            verdict = ACCEPT
            reasons.append("slightly soft, acceptable for a non critical beat")
    else:
        if critical:
            verdict = FLAG
            reasons.append("script critical but well below resolution, upscale")
        else:
            verdict = REJECT
            reasons.append("resolution too low, re-source")
    return verdict, reasons, scores


_VISION_SYSTEM = (
    "You are a video quality reviewer. Judge how well a single image fits the "
    "narration beat it will play under, following the supplied guidelines. "
    "Reply with JSON only: {\"relevance\": 1-5, \"quality\": 1-5, \"note\": \"...\"}."
)


def _vision_score(llm, guidelines: str, beat: str, image_path: str) -> dict | None:
    from ..llm import extract_json
    prompt = (
        f"Guidelines:\n{guidelines}\n\nNarration beat:\n{beat}\n\n"
        "Rate this image for relevance to the beat and overall quality."
    )
    try:
        reply = llm(_VISION_SYSTEM, prompt, image_path=image_path)
        data = extract_json(reply)
        return {
            "relevance": int(data.get("relevance", 3)),
            "quality": int(data.get("quality", 3)),
            "note": str(data.get("note", ""))[:160],
        }
    except Exception:
        return None


def review_plan(plan: dict, *, llm=None, guidelines_path: Path | None = None) -> dict:
    import copy

    plan = copy.deepcopy(plan)
    guidelines = (guidelines_path or GUIDELINES_PATH).read_text()
    meta = plan["meta"]
    tw, th = meta["width"], meta["height"]

    counts = {ACCEPT: 0, FLAG: 0, REJECT: 0}
    for scene in plan["scenes"]:
        visual = scene["visual"]
        src = visual.get("source") or {}
        critical = bool(visual.get("critical"))
        verdict, reasons, scores = _heuristic_verdict(src, critical, tw, th)

        # Optional vision pass, only on real images (not placeholders/clips).
        if (llm is not None and visual["kind"] == "image"
                and src.get("provider") not in (None, "placeholder")
                and src.get("path")):
            vs = _vision_score(llm, guidelines, scene["beat_text"], src["path"])
            if vs:
                scores.update(vs)
                if vs["relevance"] <= RELEVANCE_REJECT:
                    if critical:
                        verdict = FLAG
                        reasons.append("vision: off topic but script critical")
                    else:
                        verdict = REJECT
                        reasons.append("vision: off topic, re-source")

        counts[verdict] += 1
        scene["qc"] = {
            "verdict": verdict,
            "action": ACTION[verdict],
            "critical": critical,
            "reasons": reasons,
            "scores": scores,
        }

    plan["qc_summary"] = {
        "accepted": counts[ACCEPT],
        "flagged_upscale": counts[FLAG],
        "rejected": counts[REJECT],
        "total": len(plan["scenes"]),
        "passed": counts[REJECT] == 0,
        "guidelines": str((guidelines_path or GUIDELINES_PATH)),
    }
    meta["qc"] = True
    return plan
