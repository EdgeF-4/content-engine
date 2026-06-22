"""Stock video providers: Pexels and Pixabay.

Same shape as images.py: pure parsers plus a thin `search`. For Pexels we pick
the highest quality progressive MP4 file under a sane ceiling so a test render
never pulls a 4K clip.
"""
from __future__ import annotations

_MAX_W = 1920  # do not download anything wider than this


def _candidate(provider, cid, w, h, download_url, page_url, author, duration):
    return {
        "provider": provider, "id": str(cid), "kind": "clip",
        "width": int(w or 0), "height": int(h or 0),
        "download_url": download_url, "page_url": page_url,
        "author": author or "", "duration": float(duration or 0),
    }


def _best_pexels_file(files: list[dict]) -> dict | None:
    usable = [
        f for f in files
        if f.get("link") and (f.get("file_type") == "video/mp4"
                              or str(f.get("link", "")).endswith(".mp4"))
        and int(f.get("width") or 0) <= _MAX_W
    ]
    if not usable:
        usable = [f for f in files if f.get("link")]
    if not usable:
        return None
    return max(usable, key=lambda f: int(f.get("width") or 0))


def parse_pexels_videos(data: dict) -> list[dict]:
    out = []
    for v in data.get("videos", []):
        best = _best_pexels_file(v.get("video_files", []))
        if not best:
            continue
        out.append(_candidate(
            "pexels", v.get("id"), best.get("width") or v.get("width"),
            best.get("height") or v.get("height"), best["link"],
            v.get("url", ""), (v.get("user") or {}).get("name", ""),
            v.get("duration"),
        ))
    return out


def parse_pixabay_videos(data: dict) -> list[dict]:
    out = []
    for h in data.get("hits", []):
        streams = h.get("videos", {})
        pick = streams.get("medium") or streams.get("small") or streams.get("large")
        if not pick or not pick.get("url"):
            continue
        out.append(_candidate(
            "pixabay", h.get("id"), pick.get("width"), pick.get("height"),
            pick["url"], h.get("pageURL", ""), h.get("user", ""),
            h.get("duration"),
        ))
    return out


def search(provider: str, api_key: str, query: str, per_page: int = 15,
           session=None) -> list[dict]:
    import requests
    session = session or requests
    if provider == "pexels":
        resp = session.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": per_page},
            timeout=30,
        )
        resp.raise_for_status()
        return parse_pexels_videos(resp.json())
    if provider == "pixabay":
        resp = session.get(
            "https://pixabay.com/api/videos/",
            params={"key": api_key, "q": query, "per_page": per_page,
                    "safesearch": "true"},
            timeout=30,
        )
        resp.raise_for_status()
        return parse_pixabay_videos(resp.json())
    raise ValueError(f"unknown video provider: {provider}")
