# Garmin Connect Skill (Current)

This skill syncs Garmin Connect data into:

- `$HOME/.openclaw/workspace/训练饮食记录表.xlsx`

It is optimized for OpenClaw daily use, with a simple default:

- sync **yesterday + today** each run (to avoid missing data on first sync of the day)

## What This Skill Can Do

### Garmin API native data (auto-sync)

- Steps, resting HR, daily calories
- Sleep duration and stages (when available)
- Workout summary (type, duration, calories, HR, distance)
- Weight-related fields (if Garmin account/device has data)

### Skill-derived data (not raw Garmin fields)

- Daily muscle group inference: `胸 / 背 / 肩膀 / 臀腿`
- Inference uses:
  1) Garmin exercise-set categories (`exerciseSets.category`) first
  2) Workout name keywords second
  3) Fixed cycle fallback last
- Inference reason can be written into `备注`
- If `饮食总结/热量和营养成分分析` already contains text, script can parse and backfill
  `总热量(大卡), 蛋白质摄入(g), 碳水摄入(g), 脂肪摄入(g)`
- Recommended fixed summary format:
  1) `总热量：约 x–y kcal（中位约 z kcal）`
  2) `蛋白质：约 x–y g（中位约 z g）`
  3) `碳水：约 x–y g（中位约 z g）`
  4) `脂肪：约 x–y g（中位约 z g）`

### Still manual

- Set-by-set details in your table (sets/reps/weights per exercise)
- Diet, hydration, subjective status, digestion notes

## Script Set (Simplified)

Only these scripts are part of the active workflow:

- `scripts/garmin-auth.py` - one-time login/auth
- `scripts/garmin-sync.py` - fetch Garmin data into cache
- `scripts/garmin_to_xlsx.py` - write one target date into xlsx
- `scripts/garmin_backfill_to_xlsx.py` - backfill date range
- `scripts/sync_recent_days_to_xlsx.py` - default daily sync (recent N days, default 2)
- `scripts/sync_xlsx_today.sh` - tiny wrapper for `garmin_to_xlsx.py`

## Quick Start

### 1) Install deps

```bash
cd $HOME/.openclaw/workspace/skills/garmin-connect-skill
python3 -m pip install -r requirements.txt
```

### 2) Authenticate once

China account:

```bash
python3 scripts/garmin-auth.py your-email@qq.com your-password --cn
```

Global account:

```bash
python3 scripts/garmin-auth.py your-email@gmail.com your-password
```

Session is stored at:

- `~/.garth/session.json`

### 3) Daily sync (recommended)

```bash
python3 scripts/sync_recent_days_to_xlsx.py
```

Default behavior:

- sync yesterday and today
- write into `训练饮食记录表.xlsx`

## Common Commands

### Sync

```bash
# Recent 3 days
python3 scripts/sync_recent_days_to_xlsx.py --days 3

# One specific date
python3 scripts/garmin_to_xlsx.py --date 2026-03-18

# Dry-run
python3 scripts/garmin_to_xlsx.py --date 2026-03-18 --dry-run
```

### Workout summary + reason into remark

```bash
python3 scripts/garmin_to_xlsx.py --date 2026-03-18 --write-summary-to-remark
```

### Query muscle group only (no write)

```bash
python3 scripts/garmin_to_xlsx.py --query-muscle-group --date 2026-03-18
```

Example output fields:

- `muscle_group`
- `inference_method`
- `inference_reason`
- `category_counts`

### Backfill

```bash
python3 scripts/garmin_backfill_to_xlsx.py --start-date 2026-02-14 --end-date 2026-03-18
```

## Important Notes

- This skill currently does **not** include system-level scheduled tasks by default.
- If needed, schedule manually via `launchd` (macOS) or similar.
- To avoid date mismatch issues, always pass `--date` when syncing a specific day.
- Column aliases are supported:
  - nutrition analysis: `热量和营养成分分析` or `饮食总结`
  - total calories: `总热量(大卡)` or `总热量摄入(大卡)`

## Troubleshooting

### Auth failure

```bash
cat ~/.garth/session.json
python3 scripts/garmin-auth.py your-email your-password [--cn]
```

### Sync wrote wrong-day values

- Use date-specific sync:

```bash
python3 scripts/garmin_to_xlsx.py --date 2026-03-18
```

- Or use recommended daily command:

```bash
python3 scripts/sync_recent_days_to_xlsx.py
```

### No training group inferred

- Query first:

```bash
python3 scripts/garmin_to_xlsx.py --query-muscle-group --date 2026-03-18
```

- If `inference_method` is fallback, check workout naming or Garmin set-category availability.

### Diet columns falsely reported as empty

- Run:

```bash
python3 scripts/garmin_to_xlsx.py --date 2026-03-18 --dry-run
```

- Check output:
  - `diet_status: filled_meals=x/4`
  - `summary_present=True/False`
- Only when `filled_meals=0/4` should the agent conclude diet fields are empty.

## Version

- Updated: 2026-03-18
- Status: streamlined workflow (xlsx-first)
