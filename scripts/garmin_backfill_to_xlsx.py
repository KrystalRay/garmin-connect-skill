#!/usr/bin/env python3
"""
Backfill Garmin data into xlsx by date range.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from pathlib import Path


def parse_date(text: str) -> date:
    return datetime.strptime(text, "%Y-%m-%d").date()


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def default_xlsx_path() -> Path:
    script = Path(__file__).resolve()
    workspace_guess = script.parents[3] / "训练饮食记录表.xlsx"
    if workspace_guess.exists():
        return workspace_guess
    return Path.home() / ".openclaw" / "workspace" / "训练饮食记录表.xlsx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Garmin data into xlsx.")
    parser.add_argument("--start-date", required=True, help="Start date YYYY-MM-DD.")
    parser.add_argument("--end-date", default=datetime.now().strftime("%Y-%m-%d"), help="End date YYYY-MM-DD.")
    parser.add_argument("--xlsx", default=str(default_xlsx_path()), help="Target xlsx path.")
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.3,
        help="Sleep seconds between days to reduce API pressure.",
    )
    parser.add_argument(
        "--no-clear-missing",
        action="store_true",
        help="Do not clear missing fields. Default behavior clears missing fields.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print steps only.")
    parser.add_argument("--keep-cache", action="store_true", help="Keep per-day temp cache files.")
    return parser.parse_args()


def run_cmd(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def main() -> int:
    args = parse_args()
    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)
    if start_date > end_date:
        raise ValueError("start-date must be <= end-date")

    script_dir = Path(__file__).resolve().parent
    sync_script = script_dir / "garmin-sync.py"
    to_xlsx_script = script_dir / "garmin_to_xlsx.py"
    xlsx_path = Path(args.xlsx).expanduser().resolve()

    total = 0
    ok = 0
    failed = []

    with tempfile.TemporaryDirectory(prefix="garmin_backfill_") as temp_dir:
        temp_dir_path = Path(temp_dir)
        for day in daterange(start_date, end_date):
            total += 1
            day_str = day.strftime("%Y-%m-%d")
            cache_path = temp_dir_path / f"{day_str}.json"

            sync_cmd = [
                sys.executable,
                str(sync_script),
                "--date",
                day_str,
                "--output",
                str(cache_path),
            ]
            write_cmd = [
                sys.executable,
                str(to_xlsx_script),
                "--no-sync",
                "--date",
                day_str,
                "--cache",
                str(cache_path),
                "--xlsx",
                str(xlsx_path),
            ]
            if not args.no_clear_missing:
                write_cmd.append("--clear-missing")

            if args.dry_run:
                print(f"[DRY-RUN] {day_str}")
                print("  sync :", " ".join(sync_cmd))
                print("  write:", " ".join(write_cmd))
                continue

            print(f"🔄 回填 {day_str}")
            sync_res = run_cmd(sync_cmd)
            if sync_res.returncode != 0:
                failed.append((day_str, f"sync failed: {(sync_res.stderr or sync_res.stdout).strip()}"))
                print(f"  ❌ sync 失败: {failed[-1][1]}")
                continue

            write_res = run_cmd(write_cmd)
            if write_res.returncode != 0:
                failed.append((day_str, f"write failed: {(write_res.stderr or write_res.stdout).strip()}"))
                print(f"  ❌ 写入失败: {failed[-1][1]}")
                continue

            ok += 1
            print("  ✅ 完成")

            if args.pause_seconds > 0:
                time.sleep(args.pause_seconds)

            if args.keep_cache:
                keep_dir = Path.home() / ".clawdbot" / "garmin" / "backfill_cache"
                keep_dir.mkdir(parents=True, exist_ok=True)
                target = keep_dir / cache_path.name
                target.write_text(cache_path.read_text(encoding="utf-8"), encoding="utf-8")

    print("")
    if args.dry_run:
        print(f"📊 预览结束: 共 {total} 天 (未写入文件)")
        return 0

    print(f"📊 回填结束: 成功 {ok}/{total}")
    if failed:
        print("❌ 失败日期:")
        for day_str, reason in failed:
            print(f"  - {day_str}: {reason}")
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n⛔ 已取消")
        raise SystemExit(130)
    except Exception as exc:
        print(f"❌ 回填失败: {exc}")
        raise SystemExit(1)
