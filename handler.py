"""
AWS Lambda entry: EventBridge 스케줄 + Function URL(HTTP) 겸용.
"""

from __future__ import annotations

import json
import os
from typing import Any

from clipper.http_dashboard import handle_http_event
from clipper.runner import run_job
from clipper.storage import storage_from_env


def _is_http_event(event: dict[str, Any]) -> bool:
    if not isinstance(event, dict):
        return False
    if event.get("requestContext", {}).get("http"):
        return True
    # REST API v1 proxy
    if event.get("httpMethod") or event.get("requestContext", {}).get("elb"):
        return True
    return False


def _parse_job_type(event: dict[str, Any]) -> str | None:
    if not isinstance(event, dict):
        return None
    jt = event.get("jobType")
    if isinstance(jt, str) and jt:
        return jt
    detail = event.get("detail")
    if isinstance(detail, dict):
        jt2 = detail.get("jobType")
        if isinstance(jt2, str) and jt2:
            return jt2
    # EventBridge Scheduler direct input
    if event.get("source") == "aws.scheduler":
        jt3 = event.get("jobType")
        if isinstance(jt3, str) and jt3:
            return jt3
    return None


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    storage = storage_from_env()

    if _is_http_event(event):
        return handle_http_event(storage, event)

    job = _parse_job_type(event)
    if not job:
        return {"statusCode": 400, "body": json.dumps({"error": "jobType required"}, ensure_ascii=False)}

    if job not in ("news", "gov", "x", "youtube"):
        return {"statusCode": 400, "body": json.dumps({"error": "invalid jobType"}, ensure_ascii=False)}

    out = run_job(storage, job)  # type: ignore[arg-type]
    code = 200 if out.get("ok") else 500
    return {"statusCode": code, "body": json.dumps(out, ensure_ascii=False)}
