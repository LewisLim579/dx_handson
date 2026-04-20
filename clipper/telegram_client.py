from __future__ import annotations

from typing import Any

import requests

from clipper.secrets import get_secret


def send_telegram_message(text: str, parse_mode: str = "HTML") -> tuple[bool, str | None]:
    token = get_secret("TELEGRAM_BOT_TOKEN")
    chat = get_secret("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return False, "missing_telegram_credentials"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat,
        "text": text[:3900],
        "parse_mode": parse_mode,
        "disable_web_page_preview": False,
    }
    r = requests.post(url, json=payload, timeout=20)
    if r.status_code != 200:
        return False, r.text[:500]
    return True, None


def format_news_gov_line(
    category: str,
    site_name: str,
    menu_name: str,
    title: str,
    link: str,
    published_at: str | None,
) -> str:
    ts = published_at or "-"
    return (
        f"[{category.upper()}] {site_name}\n"
        f"메뉴: {menu_name}\n"
        f"<b>{_esc(title)}</b>\n"
        f"게시: { _esc(ts) }\n"
        f"{link}"
    )


def format_x_line(text: str, link: str, reason: str, matched: list[str], tags: list[str]) -> str:
    mk = ", ".join(matched[:20]) if matched else "-"
    tg = ", ".join(tags[:10]) if tags else "-"
    return (
        f"[X] 대통령\n"
        f"{_esc(text[:800])}\n"
        f"{link}\n"
        f"판정근거: {_esc(reason)}\n"
        f"matched_keywords: {_esc(mk)}\n"
        f"business_tags: {_esc(tg)}"
    )


def format_youtube_line(summary: str, link: str, bullets: list[str], caution: str, matched: list[str]) -> str:
    b = "\n".join(f"• {_esc(x)}" for x in bullets[:8]) if bullets else "(불릿 없음)"
    mk = ", ".join(matched[:20]) if matched else "-"
    return (
        f"[YouTube] KTV 국무회의\n"
        f"<b>{_esc(summary)}</b>\n"
        f"{b}\n"
        f"{link}\n"
        f"matched_keywords: {_esc(mk)}\n"
        f"caution: {_esc(caution or '-')}"
    )


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
