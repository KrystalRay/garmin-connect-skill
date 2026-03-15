#!/usr/bin/env python3
"""
Fetch recent weight history from Garmin Connect.

Outputs the last N days of weigh-ins (default: 7).
Uses stored credentials in ~/.garth/session.json.
"""

import argparse
import base64
import json
from datetime import date, timedelta
from pathlib import Path

from garminconnect import Garmin


def load_credentials():
    session_file = Path.home() / ".garth" / "session.json"
    if not session_file.exists():
        raise FileNotFoundError(f"No credentials found at {session_file}")

    creds = json.loads(session_file.read_text())
    if "password_encrypted" in creds:
        creds["password"] = base64.b64decode(creds["password_encrypted"]).decode()
    return creds


def kg_from_grams(value):
    if value is None:
        return None
    try:
        grams = float(value)
    except (TypeError, ValueError):
        return None
    if grams <= 0:
        return None
    return round(grams / 1000, 2)


def main():
    parser = argparse.ArgumentParser(description="Fetch recent weight history.")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (default: 7)",
    )
    args = parser.parse_args()

    creds = load_credentials()
    garmin = Garmin(creds["email"], creds["password"], is_cn=creds.get("is_cn", False))
    garmin.login()

    end_date = date.today()
    start_date = end_date - timedelta(days=max(args.days - 1, 0))

    data = garmin.get_weigh_ins(start_date.isoformat(), end_date.isoformat())

    summaries = []
    if isinstance(data, dict):
        summaries = data.get("dailyWeightSummaries", [])

    rows = []
    for summary in summaries:
        summary_date = summary.get("summaryDate")
        latest = summary.get("latestWeight")
        if not latest:
            metrics = summary.get("allWeightMetrics") or []
            latest = metrics[-1] if metrics else None
        if not latest:
            continue
        weight_kg = kg_from_grams(latest.get("weight"))
        if weight_kg is None:
            continue
        rows.append(
            {
                "date": summary_date,
                "weight_kg": weight_kg,
                "source": latest.get("sourceType"),
            }
        )

    # Sort by date asc for readability
    rows.sort(key=lambda r: r["date"] or "")

    if not rows:
        print("No weight data found in the given range.")
        return

    print("Date        Weight(kg)  Source")
    print("----------  ----------  ------")
    for row in rows:
        print(f"{row['date']}  {row['weight_kg']:>10}  {row.get('source','')}")


if __name__ == "__main__":
    main()
