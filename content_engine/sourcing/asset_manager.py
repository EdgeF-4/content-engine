"""Orchestrate sourcing: bind every planned visual to a concrete file.

Online, it queries the configured image and video providers, selects the best
fit, and downloads it. Offline (or when a provider has no key, or a fetch
fails), it synthesizes a labeled placeholder so a render always completes.
Music comes from the local library. The output is the plan with a `source`
filled in on every visual, plus a resolved `music` block.
"""
from __future__ import annotations

import copy
from pathlib import Path

from ..util import media
from . import images, videos
from .local_assets import LocalLibrary


def select_best(candidates: list[dict], target_w: int, target_h: int) -> dict | None:
    """Pick the candidate that best fits the target frame.

    Prefer the matching orientation, then the largest area that still covers
    the target, then the largest area overall.
    """
    if not candidates:
        return None
    want_portrait = target_h >= target_w
    target_area = max(1, target_w * target_h)

    def score(c: dict) -> tuple:
        w, h = c.get("width", 0), c.get("height", 0)
        area = w * h
        orient_match = (h >= w) == want_portrait
        covers = area >= target_area
        return (orient_match, covers, area)

    return max(candidates, key=score)


def _download(url: str, dest: Path, session=None) -> Path:
    import requests
    session = session or requests
    dest.parent.mkdir(parents=True, exist_ok=True)
    with session.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if chunk:
                    fh.write(chunk)
    return dest


def _placeholder(scene: dict, assets_dir: Path, width: int, height: int,
                 fps: int) -> dict:
    visual = scene["visual"]
    label = visual.get("query") or scene["beat_text"][:30]
    idx = scene["index"]
    if visual["kind"] == "clip":
        path = assets_dir / f"scene_{idx:02d}.mp4"
        media.placeholder_video(path, label, width, height,
                                seconds=scene["duration"] + 0.5, fps=fps, index=idx)
        dur = scene["duration"] + 0.5
    else:
        path = assets_dir / f"scene_{idx:02d}.jpg"
        media.placeholder_image(path, label, width, height, index=idx)
        dur = None
    return {
        "provider": "placeholder", "id": f"ph-{idx}",
        "path": str(path), "download_url": None, "page_url": None,
        "author": "generated", "width": width, "height": height,
        "duration": dur, "license": "generated locally",
        "query": visual.get("query", ""),
    }


def source_plan(plan: dict, config, work_dir: str | Path, *, offline: bool = False,
                session=None, library: LocalLibrary | None = None) -> dict:
    plan = copy.deepcopy(plan)
    work_dir = Path(work_dir)
    assets_dir = work_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    library = library or LocalLibrary()

    meta = plan["meta"]
    width, height, fps = meta["width"], meta["height"], meta["fps"]
    src_cfg = config.sourcing
    image_provider = src_cfg.get("image_provider", "pexels")
    video_provider = src_cfg.get("video_provider", "pexels")
    notes = plan.setdefault("notes", [])

    for scene in plan["scenes"]:
        visual = scene["visual"]
        kind = visual["kind"]
        provider = video_provider if kind == "clip" else image_provider
        api_key = config.sourcing_key(provider)

        if offline or not api_key:
            visual["source"] = _placeholder(scene, assets_dir, width, height, fps)
            continue

        try:
            mod = videos if kind == "clip" else images
            cands = mod.search(provider, api_key, visual["query"], session=session)
            best = select_best(cands, width, height)
            if not best:
                raise RuntimeError(f"no results for '{visual['query']}'")
            ext = ".mp4" if kind == "clip" else ".jpg"
            dest = assets_dir / f"scene_{scene['index']:02d}{ext}"
            _download(best["download_url"], dest, session=session)
            visual["source"] = {
                "provider": best["provider"], "id": best["id"],
                "path": str(dest), "download_url": best["download_url"],
                "page_url": best["page_url"], "author": best["author"],
                "width": best["width"], "height": best["height"],
                "duration": best.get("duration"),
                "license": f"{best['provider']} license, credit {best['author']}",
                "query": visual["query"],
            }
        except Exception as exc:  # any failure falls back to a placeholder
            notes.append(f"scene {scene['index']} sourcing fell back: {exc}")
            visual["source"] = _placeholder(scene, assets_dir, width, height, fps)

    music_path = library.default_music()
    whoosh = library.sfx("whoosh")
    plan.setdefault("music", {})
    plan["music"]["path"] = str(music_path) if music_path else None
    plan["audio_assets"] = {
        "transition_sfx": str(whoosh) if whoosh else None,
    }
    meta["sourced"] = True
    meta["offline_sourcing"] = bool(offline)
    return plan
