"""로컬 CLI: python -m cli run --job news|gov|x|youtube"""

from __future__ import annotations

import argparse
import json
import os

from clipper.runner import run_job
from clipper.storage import storage_from_env


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="단일 job 실행")
    r.add_argument("--job", required=True, choices=["news", "gov", "x", "youtube"])
    args = p.parse_args()
    if args.cmd == "run":
        os.environ.setdefault("LOCAL_DATA_ROOT", "local_data")
        st = storage_from_env()
        out = run_job(st, args.job)  # type: ignore[arg-type]
        print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
