from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import boto3

from clipper.env_load import load_dotenv_from_project_root

load_dotenv_from_project_root()


@lru_cache(maxsize=2)
def _load_secret(secret_arn: str | None) -> dict[str, Any]:
    if not secret_arn:
        return {}
    client = boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=secret_arn)
    raw = resp.get("SecretString") or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def get_secret(key: str, default: str | None = None) -> str | None:
    """환경변수 우선, 없으면 Secrets Manager JSON."""
    v = os.environ.get(key)
    if v:
        return v
    arn = os.environ.get("APP_SECRET_ARN")
    data = _load_secret(arn)
    if key in data:
        val = data[key]
        return str(val) if val is not None else default
    return default
