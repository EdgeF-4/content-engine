"""The single interface every provider implements.

A provider turns a system prompt plus a user prompt (and an optional image,
for vision QC) into a text completion. Nothing above this layer knows which
vendor answered.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

DEFAULT_TIMEOUT = 90


class LLMProvider(ABC):
    name = "base"

    def __init__(self, base_url: str, api_key: str, model: str,
                 timeout: int = DEFAULT_TIMEOUT, **kwargs):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.opts = kwargs

    @abstractmethod
    def complete(self, system: str, user: str,
                 image_path: str | Path | None = None) -> str:
        """Return the model's text reply. image_path is for vision requests."""
        raise NotImplementedError
