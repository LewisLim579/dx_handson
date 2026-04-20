from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from clipper.state import utc_now_iso


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def build_empty_dashboard() -> dict[str, Any]:
    now = utc_now_iso()
    return {
        "generated_at": now,
        "summary": {
            "last_snapshot_at": now,
            "sent_24h": 0,
            "failed_24h": 0,
            "job_last": {
                "x": {"success_at": None, "fail_at": None},
                "youtube": {"success_at": None, "fail_at": None},
                "news": {"success_at": None, "fail_at": None},
                "gov": {"success_at": None, "fail_at": None},
            },
        },
        "jobs": {
            "x": _empty_job_card(),
            "youtube": _empty_job_card(),
            "news": _empty_job_card(),
            "gov": _empty_job_card(),
        },
        "recent_sends": [],
        "recent_items": [],
        "recent_failures": [],
    }


def _empty_job_card() -> dict[str, Any]:
    return {
        "last_run_at": None,
        "status": "never",
        "fetched_count": 0,
        "filtered_count": 0,
        "sent_count": 0,
        "error_count": 0,
        "duration_ms": 0,
    }


def recompute_summary_24h(dash: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    sent = 0
    failed = 0
    for row in dash.get("recent_sends", []):
        t = _parse_iso(row.get("at"))
        if t and t >= since:
            sent += 1
    for row in dash.get("recent_failures", []):
        t = _parse_iso(row.get("at"))
        if t and t >= since:
            failed += 1
    dash.setdefault("summary", {})
    dash["summary"]["sent_24h"] = sent
    dash["summary"]["failed_24h"] = failed
    dash["summary"]["last_snapshot_at"] = utc_now_iso()


def append_send(
    dash: dict[str, Any],
    row: dict[str, Any],
    cap: int = 200,
) -> None:
    rs = dash.setdefault("recent_sends", [])
    rs.insert(0, row)
    dash["recent_sends"] = rs[:cap]


def append_item_row(
    dash: dict[str, Any],
    row: dict[str, Any],
    cap: int = 300,
) -> None:
    ri = dash.setdefault("recent_items", [])
    ri.insert(0, row)
    dash["recent_items"] = ri[:cap]


def append_failure(
    dash: dict[str, Any],
    row: dict[str, Any],
    cap: int = 200,
) -> None:
    rf = dash.setdefault("recent_failures", [])
    rf.insert(0, row)
    dash["recent_failures"] = rf[:cap]


def update_job_card(
    dash: dict[str, Any],
    job_type: str,
    card: dict[str, Any],
    success: bool,
) -> None:
    jobs = dash.setdefault("jobs", {})
    jobs[job_type] = card
    jl = dash.setdefault("summary", {}).setdefault("job_last", {})
    if job_type not in jl:
        jl[job_type] = {"success_at": None, "fail_at": None}
    ts = utc_now_iso()
    if success:
        jl[job_type]["success_at"] = ts
    else:
        jl[job_type]["fail_at"] = ts
