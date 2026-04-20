"""로컬 개발 시 프로젝트 루트 `.env` 로드 (Lambda에서는 파일 없음 → 무시)."""

from __future__ import annotations

from pathlib import Path


def load_dotenv_from_project_root() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env", override=False)
