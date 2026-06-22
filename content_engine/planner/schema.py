"""Dataclasses for the scene plan.

The plan is the contract between the planner and every stage after it. Once
serialized with `plan_to_dict` it travels as plain JSON, so downstream stages
read dicts and never import this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

TRANSITIONS = ["cut", "crossfade", "dip-to-black", "slide", "whip"]
MOTIONS = ["static", "ken-burns", "pan", "counter", "text-reveal"]


@dataclass
class MotionSpec:
    type: str = "static"          # one of MOTIONS
    params: dict = field(default_factory=dict)


@dataclass
class Transition:
    type: str = "cut"             # one of TRANSITIONS
    duration: float = 0.0         # seconds; 0 for a hard cut


@dataclass
class Visual:
    kind: str = "image"           # "image" or "clip"
    query: str = ""               # primary search string
    search_terms: list[str] = field(default_factory=list)
    critical: bool = False        # script critical: flagged for upscale if weak
    # filled by the sourcing stage:
    source: dict | None = None    # provider, url, path, width, height, license


@dataclass
class LowerThird:
    text: str
    subtitle: str = ""
    start: float = 0.0            # seconds from scene start
    duration: float = 3.0


@dataclass
class TitleCard:
    text: str
    subtitle: str = ""
    start: float = 0.0           # seconds from video start
    duration: float = 3.0


@dataclass
class Scene:
    index: int
    beat_text: str
    start: float                 # seconds from video start
    duration: float
    word_count: int
    visual: Visual
    transition_in: Transition
    motion: MotionSpec
    lower_third: LowerThird | None = None


@dataclass
class MusicSpec:
    track: str = "default"
    gain_db: float = -22.0       # ducked well under the voiceover


@dataclass
class ScenePlan:
    meta: dict
    title_card: TitleCard
    scenes: list[Scene]
    music: MusicSpec
    notes: list[str] = field(default_factory=list)


def plan_to_dict(plan: ScenePlan) -> dict:
    return asdict(plan)
