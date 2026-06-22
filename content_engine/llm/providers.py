"""Concrete providers: NVIDIA NIM, Anthropic, Google Gemini.

Each is a thin HTTP client over the vendor's documented API. NIM speaks the
OpenAI compatible chat format and is the free option used in development.
Anthropic and Gemini are the paid options used for real runs.
"""
from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from .base import LLMProvider


def _read_image_b64(image_path: str | Path) -> tuple[str, str]:
    p = Path(image_path)
    mime = mimetypes.guess_type(str(p))[0] or "image/jpeg"
    return mime, base64.b64encode(p.read_bytes()).decode("ascii")


class NIMProvider(LLMProvider):
    """OpenAI compatible chat completions (NVIDIA NIM hosted models)."""

    name = "nim"

    def complete(self, system: str, user: str, image_path=None) -> str:
        import requests

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": messages,
                "temperature": self.opts.get("temperature", 0.4),
                "max_tokens": self.opts.get("max_tokens", 2048),
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def complete(self, system: str, user: str, image_path=None) -> str:
        import requests

        content: list[dict] = []
        if image_path:
            mime, data = _read_image_b64(image_path)
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": data},
            })
        content.append({"type": "text", "text": user})
        resp = requests.post(
            f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": self.opts.get("max_tokens", 4096),
                "system": system,
                "messages": [{"role": "user", "content": content}],
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        blocks = resp.json()["content"]
        return "".join(b.get("text", "") for b in blocks if b.get("type") == "text")


class GeminiProvider(LLMProvider):
    name = "gemini"

    def complete(self, system: str, user: str, image_path=None) -> str:
        import requests

        parts: list[dict] = [{"text": user}]
        if image_path:
            mime, data = _read_image_b64(image_path)
            parts.append({"inlineData": {"mimeType": mime, "data": data}})
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        resp = requests.post(
            url,
            params={"key": self.api_key},
            headers={"content-type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": {
                    "temperature": self.opts.get("temperature", 0.4),
                    "maxOutputTokens": self.opts.get("max_tokens", 2048),
                },
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        cand = resp.json()["candidates"][0]
        return "".join(p.get("text", "") for p in cand["content"]["parts"])


PROVIDERS = {
    "nim": NIMProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
}
