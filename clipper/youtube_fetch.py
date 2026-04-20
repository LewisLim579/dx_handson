from __future__ import annotations

from typing import Any

import requests

from clipper.secrets import get_secret


def _yt_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    key = get_secret("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY missing")
    p = dict(params)
    p["key"] = key
    url = f"https://www.googleapis.com/youtube/v3/{path}"
    r = requests.get(url, params=p, timeout=25)
    if r.status_code != 200:
        raise RuntimeError(f"youtube_{r.status_code}: {r.text[:400]}")
    return r.json()


def resolve_channel_id_for_handle(handle: str) -> str:
    handle = handle.lstrip("@")
    data = _yt_get("channels", {"part": "id,snippet", "forHandle": handle})
    items = data.get("items") or []
    if not items:
        data = _yt_get("channels", {"part": "id,snippet", "forUsername": handle})
        items = data.get("items") or []
    if not items:
        raise RuntimeError("youtube_channel_not_found")
    cid = items[0].get("id")
    if isinstance(cid, dict):
        return str(cid.get("channelId") or cid)
    return str(cid)


def search_cabinet_videos(channel_id: str, max_results: int = 10) -> list[dict[str, Any]]:
    data = _yt_get(
        "search",
        {
            "part": "snippet",
            "channelId": channel_id,
            "q": "국무회의",
            "type": "video",
            "order": "date",
            "maxResults": max_results,
        },
    )
    return data.get("items") or []


def get_video_detail(video_id: str) -> dict[str, Any]:
    data = _yt_get("videos", {"part": "snippet,contentDetails", "id": video_id})
    items = data.get("items") or []
    return items[0] if items else {}
