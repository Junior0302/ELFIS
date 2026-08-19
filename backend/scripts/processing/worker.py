"""CLI worker Document Processing.

Usage:
  python -m scripts.processing.worker --once
  python -m scripts.processing.worker --poll-seconds 2 --max-jobs 5
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Document Processing worker")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=None)
    parser.add_argument("--worker-id", default="")
    parser.add_argument("--max-jobs", type=int, default=5)
    parser.add_argument("--pipeline", default="")
    parser.add_argument("--database-url", default="")
    args = parser.parse_args(argv)

    if args.database_url:
        os.environ["DATABASE_URL"] = args.database_url

    env = (os.environ.get("ELFIS_ENVIRONMENT") or os.environ.get("APP_ENV") or "").strip()
    if not env:
        print("FATAL: ELFIS_ENVIRONMENT / APP_ENV non défini")
        return 2
    print(f"ELFIS_ENVIRONMENT={env}")

    from app.document_processing.worker import run_worker_loop

    run_worker_loop(
        once=args.once,
        poll_seconds=args.poll_seconds,
        worker_id=args.worker_id or None,
        max_jobs=args.max_jobs,
        pipeline=args.pipeline or None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
