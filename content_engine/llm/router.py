"""Role based routing and JSON extraction.

`completer_for_role` resolves a role through config to a concrete provider and
returns a plain callable, or None when no provider is configured (the caller
then uses its heuristic). `extract_json` parses a model reply that may be
wrapped in prose or code fences.
"""
from __future__ import annotations

import json
import re
from typing import Callable

from .base import DEFAULT_TIMEOUT
from .providers import PROVIDERS

Completer = Callable[..., str]

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def completer_for_role(config, role: str) -> Completer | None:
    name, pcfg = config.provider_for_role(role)
    if not name:
        return None
    model = config.model_for_role(name, role)
    provider_cls = PROVIDERS[name]
    provider = provider_cls(
        base_url=pcfg.get("base_url", ""),
        api_key=pcfg.get("api_key", ""),
        model=model,
        timeout=pcfg.get("timeout", DEFAULT_TIMEOUT),
        max_tokens=pcfg.get("max_tokens", 2048),
    )

    def complete(system: str, user: str, image_path=None) -> str:
        return provider.complete(system, user, image_path)

    complete.provider_name = name  # type: ignore[attr-defined]
    return complete


def extract_json(text: str):
    """Best effort JSON parse of a model reply.

    Handles a bare object, a fenced block, or an object embedded in prose.
    Raises ValueError if nothing parses.
    """
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _FENCE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # Fall back to the first balanced object or array in the text.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON found in model reply")
