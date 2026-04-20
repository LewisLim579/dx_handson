from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from clipper.storage import Storage

KST = timezone(timedelta(hours=9))


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(storage: Storage, key: str, default: Any) -> Any:
    data = storage.read_json(key)
    return default if data is None else data


def save_json(storage: Storage, key: str, data: Any) -> None:
    storage.write_json(key, data)


def prune_sent_entries(entries: dict[str, Any], keep_days: int = 30) -> dict[str, Any]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    out: dict[str, Any] = {}
    for k, v in entries.items():
        ts = v.get("created_at") if isinstance(v, dict) else None
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if dt >= cutoff:
                out[k] = v
        except Exception:
            continue
    return out


def merge_checkpoint_sources(
    checkpoint: dict[str, Any],
    source_id: str,
    update: dict[str, Any],
) -> None:
    checkpoint.setdefault("sources", {})
    cur = dict(checkpoint["sources"].get(source_id) or {})
    cur.update(update)
    checkpoint["sources"][source_id] = cur
