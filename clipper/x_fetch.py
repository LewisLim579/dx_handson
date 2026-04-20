from __future__ import annotations

from typing import Any

import requests

from clipper.secrets import get_secret


def fetch_recent_tweets(username: str, since_id: str | None = None, max_results: int = 10) -> tuple[list[dict[str, Any]], str | None]:
    """Twitter API v2 user timeline (Bearer token)."""
    bearer = get_secret("TWITTER_BEARER_TOKEN")
    if not bearer:
        raise RuntimeError("TWITTER_BEARER_TOKEN missing")
    headers = {"Authorization": f"Bearer {bearer}"}
    u = f"https://api.twitter.com/2/users/by/username/{username}"
    r = requests.get(u, headers=headers, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"twitter_user_{r.status_code}: {r.text[:300]}")
    uid = r.json()["data"]["id"]
    params: dict[str, Any] = {
        "max_results": max_results,
        "tweet.fields": "created_at,referenced_tweets",
        "exclude": "retweets,replies",
    }
    if since_id:
        params["since_id"] = since_id
    tl = f"https://api.twitter.com/2/users/{uid}/tweets"
    r2 = requests.get(tl, headers=headers, params=params, timeout=20)
    if r2.status_code != 200:
        raise RuntimeError(f"twitter_timeline_{r2.status_code}: {r2.text[:300]}")
    data = r2.json()
    tweets = data.get("data")
    if tweets is None:
        tweets = []
    newest_id = (data.get("meta") or {}).get("newest_id")
    return tweets, newest_id
