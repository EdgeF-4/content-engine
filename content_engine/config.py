"""Configuration loading and role to provider resolution.

Keys live in config.json (chmod 600) at the repository root, never in source
or environment. Missing keys are not an error: a role with no usable provider
falls back to the next, then to each stage's built in heuristic.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config.json"


class Config:
    def __init__(self, data: dict, path: Path | None = None):
        self.data = data
        self.path = path

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Config":
        p = Path(path) if path else DEFAULT_CONFIG_PATH
        if p.exists():
            data = json.loads(p.read_text())
        else:
            data = {}
        return cls(data, p)

    # -- providers -------------------------------------------------------

    def provider_config(self, name: str) -> dict:
        return self.data.get("providers", {}).get(name, {})

    def _has_key(self, name: str) -> bool:
        return bool(self.provider_config(name).get("api_key", "").strip())

    def provider_for_role(self, role: str) -> tuple[str | None, dict]:
        """Resolve a role to (provider_name, provider_config).

        Returns the primary if its key is present, else the fallback if its
        key is present, else (None, {}) meaning use the heuristic.
        """
        spec = self.data.get("roles", {}).get(role, {})
        for slot in ("primary", "fallback"):
            name = spec.get(slot)
            if name and self._has_key(name):
                return name, self.provider_config(name)
        return None, {}

    def model_for_role(self, provider_name: str, role: str) -> str | None:
        """Pick the model id for a provider given a role.

        NIM keys models by role; Anthropic and Gemini use a single model field.
        """
        cfg = self.provider_config(provider_name)
        models = cfg.get("models")
        if isinstance(models, dict):
            short = "planner" if role == "scene_planning" else "qc"
            return models.get(short) or models.get(role)
        return cfg.get("model")

    # -- sourcing / render ----------------------------------------------

    @property
    def sourcing(self) -> dict:
        return self.data.get("sourcing", {})

    def sourcing_key(self, provider: str) -> str:
        return self.sourcing.get(provider, {}).get("api_key", "").strip()

    @property
    def render(self) -> dict:
        return self.data.get("render", {})
