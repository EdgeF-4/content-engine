"""Lightweight text analysis for the deterministic planner core.

No NLP dependencies. Sentence splitting, beat grouping, keyword extraction,
and a motion heuristic, all from the standard library so the planner runs
anywhere with zero setup.
"""
from __future__ import annotations

import re

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "of", "to", "in",
    "on", "for", "with", "as", "at", "by", "from", "is", "are", "was", "were",
    "be", "been", "being", "it", "its", "this", "that", "these", "those", "i",
    "you", "we", "they", "he", "she", "him", "her", "them", "our", "your",
    "their", "my", "me", "us", "do", "does", "did", "have", "has", "had", "not",
    "no", "yes", "can", "will", "would", "should", "could", "may", "might",
    "about", "into", "over", "after", "before", "than", "very", "just", "also",
    "what", "when", "where", "which", "who", "how", "why", "there", "here",
    "out", "up", "down", "all", "any", "some", "more", "most", "one", "two",
    "get", "got", "make", "made", "like", "because", "while", "still", "even",
}

# Language that suggests live action, motion, or process: leans toward a clip.
_MOTION_WORDS = {
    "run", "running", "ran", "move", "moving", "moved", "drive", "driving",
    "fly", "flying", "flew", "build", "building", "built", "grow", "growing",
    "flow", "flowing", "rush", "rushing", "race", "racing", "spin", "spinning",
    "dance", "dancing", "walk", "walking", "jump", "jumping", "fall", "falling",
    "crash", "crashing", "explode", "explosion", "wave", "waves", "storm",
    "traffic", "machine", "engine", "process", "transform", "transforming",
    "action", "fast", "speed", "rapid", "motion", "stream", "streaming",
    "pour", "pouring", "burn", "burning", "shake", "shaking", "swim",
}

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]+")


def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        for sent in _SENT_SPLIT.split(line):
            sent = sent.strip()
            if sent:
                parts.append(sent)
    return parts


def word_count(text: str) -> int:
    return len(_WORD.findall(text))


def split_beats(text: str, min_words: int = 6) -> list[str]:
    """Group sentences into beats, merging very short fragments forward.

    A beat is the unit a single visual covers. Short sentences (an aside, a
    one word hook) merge into the next so a beat carries enough to search on.
    """
    sentences = split_sentences(text)
    beats: list[str] = []
    buffer = ""
    for sent in sentences:
        candidate = (buffer + " " + sent).strip() if buffer else sent
        if word_count(candidate) < min_words:
            buffer = candidate
            continue
        beats.append(candidate)
        buffer = ""
    if buffer:
        if beats:
            beats[-1] = (beats[-1] + " " + buffer).strip()
        else:
            beats.append(buffer)
    return beats


def keywords(text: str, limit: int = 4) -> list[str]:
    """Frequency ranked content words, original order broken by first use."""
    words = [w.lower() for w in _WORD.findall(text)]
    freq: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for i, w in enumerate(words):
        if w in _STOPWORDS or len(w) < 3:
            continue
        freq[w] = freq.get(w, 0) + 1
        first_seen.setdefault(w, i)
    ranked = sorted(freq, key=lambda w: (-freq[w], first_seen[w]))
    return ranked[:limit]


def is_motion(text: str) -> bool:
    """True when the beat reads as motion or action (favor a clip)."""
    words = {w.lower() for w in _WORD.findall(text)}
    return bool(words & _MOTION_WORDS)


def title_case(text: str, max_words: int = 7) -> str:
    words = _WORD.findall(text)
    return " ".join(words[:max_words]).title()
