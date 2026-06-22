"""Stock image providers: Pexels and Pixabay.

The response parsers are pure functions over the documented JSON, so they are
unit tested with fixtures and never need the network. `search` is the thin
HTTP wrapper used at run time. Each provider's attribution terms are respected
by recording the source page and author on every candidate.
"""
from __future__ import annotations


def _candidate(provider, cid, w, h, download_url, page_url, author):
    return {
        "provider": provider, "id": str(cid), "kind": "image",
        "width": int(w or 0), "height": int(h or 0),
        "download_url": download_url, "page_url": page_url,
        "author": author or "", "duration": None,
    }


def parse_pexels_images(data: dict) -> list[dict]:
    out = []
    for p in data.get("photos", []):
        src = p.get("src", {})
        url = src.get("large2x") or src.get("original") or src.get("large")
        if not url:
            continue
        out.append(_candidate("pexels", p.get("id"), p.get("width"),
                              p.get("height"), url, p.get("url", ""),
                              p.get("photographer", "")))
    return out


def parse_pixabay_images(data: dict) -> list[dict]:
    out = []
    for h in data.get("hits", []):
        url = h.get("largeImageURL") or h.get("webformatURL")
        if not url:
            continue
        out.append(_candidate("pixabay", h.get("id"), h.get("imageWidth"),
                              h.get("imageHeight"), url, h.get("pageURL", ""),
                              h.get("user", "")))
    return out


def search(provider: str, api_key: str, query: str, per_page: int = 15,
           session=None) -> list[dict]:
    import requests
    session = session or requests
    if provider == "pexels":
        resp = session.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": per_page},
            timeout=30,
        )
        resp.raise_for_status()
        return parse_pexels_images(resp.json())
    if provider == "pixabay":
        resp = session.get(
            "https://pixabay.com/api/",
            params={"key": api_key, "q": query, "image_type": "photo",
                    "per_page": per_page, "safesearch": "true"},
            timeout=30,
        )
        resp.raise_for_status()
        return parse_pixabay_images(resp.json())
    raise ValueError(f"unknown image provider: {provider}")
