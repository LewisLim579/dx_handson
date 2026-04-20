from __future__ import annotations

import random
import time
from typing import Any

import requests

DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_url(
    url: str,
    timeout: int = 25,
    headers: dict[str, str] | None = None,
) -> tuple[int, str, dict[str, str]]:
    h = {"User-Agent": DEFAULT_UA, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
    if headers:
        h.update(headers)
    # 소규모 지터로 동시 요청 완화
    time.sleep(random.uniform(0.05, 0.2))
    r = requests.get(url, headers=h, timeout=timeout)
    return r.status_code, r.text, {k: v for k, v in r.headers.items()}
