from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError


class Storage(ABC):
    @abstractmethod
    def read_text(self, key: str) -> str | None:
        ...

    @abstractmethod
    def write_text(self, key: str, body: str, content_type: str = "application/json") -> None:
        ...

    def read_json(self, key: str) -> Any | None:
        raw = self.read_text(key)
        if raw is None:
            return None
        return json.loads(raw)

    def write_json(self, key: str, data: Any) -> None:
        self.write_text(key, json.dumps(data, ensure_ascii=False, indent=2), "application/json")


class LocalFileStorage(Storage):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key.replace("/", os.sep)

    def read_text(self, key: str) -> str | None:
        p = self._path(key)
        if not p.is_file():
            return None
        return p.read_text(encoding="utf-8")

    def write_text(self, key: str, body: str, content_type: str = "application/json") -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


class S3Storage(Storage):
    def __init__(self, bucket: str, prefix: str = "") -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = boto3.client("s3")

    def _full_key(self, key: str) -> str:
        k = key.lstrip("/")
        return f"{self.prefix}/{k}" if self.prefix else k

    def read_text(self, key: str) -> str | None:
        fk = self._full_key(key)
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=fk)
            return resp["Body"].read().decode("utf-8")
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "NoSuchKey", "NotFound"):
                return None
            raise

    def write_text(self, key: str, body: str, content_type: str = "application/json") -> None:
        fk = self._full_key(key)
        self.client.put_object(
            Bucket=self.bucket,
            Key=fk,
            Body=body.encode("utf-8"),
            ContentType=content_type,
        )


def storage_from_env() -> Storage:
    bucket = os.environ.get("S3_BUCKET")
    if bucket:
        prefix = os.environ.get("S3_PREFIX", "")
        return S3Storage(bucket, prefix)
    root = os.environ.get("LOCAL_DATA_ROOT", "local_data")
    return LocalFileStorage(root)


def bootstrap_config_if_missing(storage: Storage, config_dir: Path) -> None:
    """첫 실행 시 S3에 설정 파일이 없으면 로컬 config/에서 복사."""
    if not config_dir.is_dir():
        return
    for sub in ["config", "config/prompts"]:
        for p in (config_dir / sub.replace("/", os.sep)).glob("**/*"):
            if p.is_file():
                rel = p.relative_to(config_dir)
                key = str(rel).replace(os.sep, "/")
                if storage.read_text(key) is None:
                    storage.write_text(key, p.read_text(encoding="utf-8"))
