from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal, Optional

Decision = Literal["sent", "skipped", "failed"]
Category = Literal["news", "gov", "x", "youtube"]
JobType = Literal["news", "gov", "x", "youtube"]


@dataclass
class ParsedItem:
    external_id: str
    title: str
    link: str
    published_at: Optional[str] = None
    summary_hint: Optional[str] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class FilterResult:
    matched: bool
    matched_keywords: list[str]
    normalized_text: str


@dataclass
class XAIResult:
    relevance: Literal["relevant", "irrelevant", "uncertain"]
    relevance_score: float
    reason: str
    matched_keywords: list[str]
    business_tags: list[str]


@dataclass
class YouTubeAIResult:
    summary_short: str
    summary_bullets: list[str]
    matched_keywords: list[str]
    caution: str
    transcript_available: bool


def item_dedupe_key(item: ParsedItem) -> dict[str, Any]:
    return {
        "external_id": item.external_id,
        "link": item.link,
        "title": item.title,
    }
