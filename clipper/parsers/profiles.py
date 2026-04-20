from __future__ import annotations

import hashlib
import re
from typing import Callable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from clipper.dedupe import safe_external_id
from clipper.models import ParsedItem

try:
    _PARSER = "lxml"
    BeautifulSoup("<html></html>", _PARSER)
except Exception:
    _PARSER = "html.parser"


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, _PARSER)


ProfileFn = Callable[[str, str, str], list[ParsedItem]]


def _abs(base: str, href: str) -> str:
    if not href or href.startswith("#") or href.startswith("javascript:"):
        return ""
    return urljoin(base, href)


def _guess_external_id(link: str) -> str:
    p = urlparse(link)
    tail = (p.path or "").strip("/").split("/")[-1]
    if tail:
        return safe_external_id(tail, "url")
    return f"h:{hashlib.sha256(link.encode('utf-8')).hexdigest()[:16]}"


def _clean_title(t: str) -> str:
    t = re.sub(r"\s+", " ", (t or "").strip())
    return t[:500]


def parse_html_article_list(html: str, page_url: str, source_id: str) -> list[ParsedItem]:
    soup = _soup(html)
    items: list[ParsedItem] = []
    seen: set[str] = set()

    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        link = _abs(page_url, href)
        if not link or link in seen:
            continue
        if not any(
            x in link.lower()
            for x in ("articleview", "articleview.html", "newsview", "articledetail", "view.do", "article")
        ):
            if not re.search(r"/(news|article)/\d", link, re.I):
                continue
        title = _clean_title(a.get_text(" ", strip=True))
        if len(title) < 6:
            continue
        seen.add(link)
        eid = _guess_external_id(link)
        items.append(ParsedItem(external_id=eid, title=title, link=link, published_at=None, raw={"profile": "html_article_list"}))

    if not items:
        return parse_generic_list_fallback(html, page_url, source_id)
    return items[:80]


def parse_html_search_result(html: str, page_url: str, source_id: str) -> list[ParsedItem]:
    soup = _soup(html)
    items: list[ParsedItem] = []
    seen: set[str] = set()
    base_host = urlparse(page_url).hostname or ""
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        link = _abs(page_url, href)
        if not link or link in seen:
            continue
        host = urlparse(link).hostname or ""
        if host and base_host and host != base_host:
            continue
        title = _clean_title(a.get_text(" ", strip=True))
        if len(title) < 8:
            continue
        if not re.search(r"(news|article|view|stock|content)", link, re.I):
            continue
        seen.add(link)
        items.append(
            ParsedItem(
                external_id=_guess_external_id(link),
                title=title,
                link=link,
                published_at=None,
                raw={"profile": "html_search_result"},
            )
        )
    if not items:
        return parse_generic_list_fallback(html, page_url, source_id)
    return items[:80]


def parse_html_notice_board(html: str, page_url: str, source_id: str) -> list[ParsedItem]:
    soup = _soup(html)
    items: list[ParsedItem] = []
    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        link = _abs(page_url, href)
        if not link or link in seen:
            continue
        title = _clean_title(a.get_text(" ", strip=True))
        if len(title) < 4:
            continue
        if not any(
            k in link.lower()
            for k in ("detail", "view", "read", "article", "seq", "bid", "board", "cms", "bbs", "content", "menuid", "nid", "idx")
        ):
            continue
        seen.add(link)
        items.append(
            ParsedItem(
                external_id=_guess_external_id(link),
                title=title,
                link=link,
                published_at=None,
                raw={"profile": "html_notice_board"},
            )
        )
    if not items:
        return parse_generic_list_fallback(html, page_url, source_id)
    return items[:120]


def parse_html_policy_board(html: str, page_url: str, source_id: str) -> list[ParsedItem]:
    return parse_html_notice_board(html, page_url, source_id)


def parse_html_report_board(html: str, page_url: str, source_id: str) -> list[ParsedItem]:
    return parse_html_notice_board(html, page_url, source_id)


def parse_generic_list_fallback(html: str, page_url: str, source_id: str) -> list[ParsedItem]:
    soup = _soup(html)
    items: list[ParsedItem] = []
    seen: set[str] = set()
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        link = _abs(page_url, href)
        if not link or link in seen:
            continue
        title = _clean_title(a.get_text(" ", strip=True))
        if len(title) < 10:
            continue
        seen.add(link)
        items.append(
            ParsedItem(
                external_id=_guess_external_id(link),
                title=title,
                link=link,
                published_at=None,
                raw={"profile": "generic_list_fallback"},
            )
        )
    return items[:80]


PROFILE_MAP: dict[str, ProfileFn] = {
    "html_article_list": parse_html_article_list,
    "html_search_result": parse_html_search_result,
    "html_notice_board": parse_html_notice_board,
    "html_policy_board": parse_html_policy_board,
    "html_report_board": parse_html_report_board,
    "generic_list_fallback": parse_generic_list_fallback,
}


def parse_for_profile(profile: str, html: str, page_url: str, source_id: str) -> list[ParsedItem]:
    fn = PROFILE_MAP.get(profile) or parse_generic_list_fallback
    return fn(html, page_url, source_id)
