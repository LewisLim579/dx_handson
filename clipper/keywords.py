from __future__ import annotations

import re
from typing import Any

from clipper.models import FilterResult


def apply_alias_map(text: str, alias_map: dict[str, str]) -> str:
    out = text
    for src, dst in alias_map.items():
        out = out.replace(src, dst)
    return out


def normalize_for_match(text: str, extra_normalize: dict[str, str] | None = None) -> str:
    t = text.lower()
    t = re.sub(r"\s+", " ", t).strip()
    if extra_normalize:
        t = apply_alias_map(t, extra_normalize)
    return t


def collect_keywords_for_source(
    kw_config: dict[str, Any],
    source_id: str,
    use_source_specific: bool,
) -> tuple[list[str], dict[str, str]]:
    """global + (optional) source_specific 병합. normalize 맵 별도 반환."""
    glob = list(kw_config.get("global_keywords") or [])
    spec_map: dict[str, list[str]] = kw_config.get("source_specific_keywords") or {}
    extra = spec_map.get(source_id) if use_source_specific else None
    merged = list(glob)
    if extra:
        merged.extend(extra)
    # de-dupe preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for k in merged:
        if k not in seen:
            seen.add(k)
            uniq.append(k)
    norm = dict(kw_config.get("normalize") or {})
    return uniq, norm


def merge_normalize_maps(base: dict[str, str], extra: dict[str, str] | None) -> dict[str, str]:
    out = dict(base)
    if extra:
        out.update(extra)
    return out


def keyword_filter(
    text: str,
    keywords: list[str],
    normalize_map: dict[str, str],
    exclude_keywords: list[str] | None = None,
    strict_keywords: list[str] | None = None,
) -> FilterResult:
    exclude_keywords = exclude_keywords or []
    strict_keywords = strict_keywords or []
    nt = normalize_for_match(text, normalize_map)
    matched: list[str] = []
    for ex in exclude_keywords:
        if ex and normalize_for_match(ex, normalize_map) in nt:
            return FilterResult(False, [], nt)
    for sk in strict_keywords:
        if sk and normalize_for_match(sk, normalize_map) not in nt:
            return FilterResult(False, [], nt)
    for kw in keywords:
        if not kw:
            continue
        kn = normalize_for_match(kw, normalize_map)
        if kn in nt or kn.replace(" ", "") in nt.replace(" ", ""):
            matched.append(kw)
    # substring for partial phrases
    if not matched:
        for kw in keywords:
            if not kw:
                continue
            kn = normalize_for_match(kw, normalize_map)
            if len(kn) >= 2 and kn in nt:
                matched.append(kw)
    ok = len(matched) > 0
    return FilterResult(ok, matched, nt)
