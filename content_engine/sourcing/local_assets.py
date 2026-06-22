"""The local asset library: music, sfx, transition overlays, backgrounds.

Scans the repository `assets/` folders so the renderer can reach for a music
bed or a transition sound without a network call. Self generated assets ship
in the repo, and any file a user drops in is picked up automatically.
"""
from __future__ import annotations

from pathlib import Path

from ..config import REPO_ROOT

_AUDIO_EXT = {".wav", ".mp3", ".m4a", ".aac", ".ogg"}
_VIDEO_EXT = {".mp4", ".mov", ".webm"}


class LocalLibrary:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else REPO_ROOT / "assets"

    def _list(self, folder: str, exts: set[str]) -> list[Path]:
        d = self.root / folder
        if not d.exists():
            return []
        return sorted(p for p in d.iterdir()
                      if p.is_file() and p.suffix.lower() in exts)

    def music_tracks(self) -> list[Path]:
        return self._list("music", _AUDIO_EXT)

    def sfx(self, name: str | None = None) -> Path | None:
        tracks = self._list("sfx", _AUDIO_EXT)
        if name:
            for t in tracks:
                if t.stem == name:
                    return t
        return tracks[0] if tracks else None

    def default_music(self) -> Path | None:
        tracks = self.music_tracks()
        return tracks[0] if tracks else None

    def transition_overlays(self) -> list[Path]:
        return self._list("transitions", _VIDEO_EXT)

    def backgrounds(self) -> list[Path]:
        return self._list("backgrounds", _VIDEO_EXT)
