#!/usr/bin/env python3
"""
Sync recent N days Garmin data into xlsx.
Default: yesterday + today (2 days).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync recent days to xlsx.")
    parser.add_argument(
        "--days",
        type=int,
        default=2,
        help="How many recent days to sync. Default: 2 (yesterday + today).",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="End date in YYYY-MM-DD. Default: today.",
    )
    parser.add_argument(
        "--xlsx",
        default=str(Path.home() / ".openclaw" / "workspace" / "训练饮食记录表.xlsx"),
        help="Target xlsx path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview commands without writing.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.days < 1:
        raise ValueError("--days must be >= 1")

    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    else:
        end_date = datetime.now().date()
    start_date = end_date - timedelta(days=args.days - 1)

    script_dir = Path(__file__).resolve().parent
    backfill = script_dir / "garmin_backfill_to_xlsx.py"

    cmd = [
        sys.executable,
        str(backfill),
        "--start-date",
        start_date.isoformat(),
        "--end-date",
        end_date.isoformat(),
        "--xlsx",
        str(Path(args.xlsx).expanduser().resolve()),
    ]
    if args.dry_run:
        cmd.append("--dry-run")

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
