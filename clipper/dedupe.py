from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import urlparse, urlunparse

from clipper.models import ParsedItem
from clipper.state import utc_now_iso


def normalize_url(url: str) -> str:
    try:
        p = urlparse(url.strip())
        path = p.path or ""
        q = ""
        if p.query:
            q = "?" + p.query
        frag = ""
        if p.fragment:
            frag = "#" + p.fragment
        netloc = (p.hostname or "").lower()
        if p.port and not (p.scheme == "http" and p.port == 80) and not (p.scheme == "https" and p.port == 443):
            netloc = f"{netloc}:{p.port}"
        scheme = (p.scheme or "https").lower()
        return urlunparse((scheme, netloc, path.rstrip("/") or "/", "", q, ""))
    except Exception:
        return url.strip()


def title_date_hash(title: str, published_at: str | None) -> str:
    base = f"{title}|{published_at or ''}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def dedupe_keys(item: ParsedItem) -> list[str]:
    keys: list[str] = []
    if item.external_id:
        keys.append(f"id:{item.external_id}")
    keys.append(f"url:{normalize_url(item.link)}")
    keys.append(f"hash:{title_date_hash(item.title, item.published_at)}")
    return keys


def already_sent(sent_entries: dict[str, Any], item: ParsedItem) -> bool:
    for k in dedupe_keys(item):
        if k in sent_entries:
            return True
    return False


def register_sent(sent_entries: dict[str, Any], item: ParsedItem, meta: dict[str, Any]) -> None:
    created = utc_now_iso()
    rec = {**meta, **item_dedupe_record(item)}
    for k in dedupe_keys(item):
        sent_entries[k] = {"created_at": created, "record": rec}


def item_dedupe_record(item: ParsedItem) -> dict[str, Any]:
    return {
        "external_id": item.external_id,
        "title": item.title,
        "link": item.link,
        "published_at": item.published_at,
    }


_RE_NON_ID = re.compile(r"[^a-zA-Z0-9_-]+")


def safe_external_id(raw: str, prefix: str = "gen") -> str:
    s = _RE_NON_ID.sub("-", raw.strip())[:120]
    return f"{prefix}:{s}" if s else prefix
