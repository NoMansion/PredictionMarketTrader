"""How many ideas-queue items a check-in may work, from a rough pace of the week's Claude usage. No network, no Claude.

A check-in cannot see the plan's usage meter, but this project logs what each Claude run would cost at list price:
the main account's forecasts (data/pmt.db), the rule accounts that ask Claude (data/rules/*.db) and every check-in
(data/checkin/*.json). The meter has tracked that spend closely: 4% of the week for $34 (2026-11-22) and 16% for
$140 (2026-11-24, which also holds the user's own sessions), so about $8.50 a percent.

The user aims for 75% of the weekly limit (2026-11-22) and wants as much tested as possible (2026-11-24: "Test as many
things as you can. There is no time constraint"). So: project the week from the last 24 hours, keep a reserve for the
user's own sessions (which this cannot see), and spread what is left over the check-ins still to come.

    python scripts/usage_pace.py            a few lines; the last is "ITEMS n" (0 = health only)
    python scripts/usage_pace.py --json
"""
import argparse
import glob
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent

CENTRAL = ZoneInfo("America/Chicago")
RESET_WEEKDAY, RESET_HOUR = 6, 16        # the weekly limit resets Sundays at 4:00 pm Central
DOLLARS_PER_PCT = 8.5                    # list-price dollars per 1% of the week (measured, see above)
TARGET_PCT = 75.0                        # the user, 2026-11-22
RESERVE_PCT = 7.0                        # kept for the user's own sessions on either PC
ITEM_USD = 0.5                           # one more queue item inside a check-in. Measured 2026-11-24/25 over seven runs:
                                         # 1 item $0.63-1.39, 2 items $1.02-1.12, 3 items $1.71, so about $0.40 an
                                         # extra item (was 1.5 until 4:10 am Nov 25, which held runs to 2 items)
MAX_ITEMS = 8                            # a check-in has 100 minutes and an $8 cap (scripts/checkin.ps1), and starts no
                                         # new item after 60 minutes
CHECKIN_EVERY_H = 3.0


def last_reset(now: datetime) -> datetime:
    """The most recent Sunday 4:00 pm Central at or before `now` (an aware datetime), in UTC."""
    local = now.astimezone(CENTRAL)
    day = local.date() - timedelta(days=(local.weekday() - RESET_WEEKDAY) % 7)
    reset = datetime(day.year, day.month, day.day, RESET_HOUR, tzinfo=CENTRAL)
    if reset > local:
        reset -= timedelta(days=7)
        reset = datetime(reset.year, reset.month, reset.day, RESET_HOUR, tzinfo=CENTRAL)   # across a DST change
    return reset.astimezone(timezone.utc)


def ledger_spend(path: Path, since: float) -> float:
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30)
        try:
            row = db.execute("SELECT SUM(cost_usd) FROM forecasts WHERE ts >= ?", (since,)).fetchone()
        finally:
            db.close()
        return float(row[0] or 0.0)
    except sqlite3.Error:                    # no forecasts table (a rule account that never asks Claude)
        return 0.0


def checkin_spend(folder: Path, since: float) -> float:
    total = 0.0
    for f in glob.glob(str(folder / "*.json")):
        try:
            if os.path.getmtime(f) < since:
                continue
            with open(f, encoding="utf-8-sig") as fh:
                total += float(json.load(fh).get("total_cost_usd") or 0.0)
        except (OSError, ValueError, AttributeError):
            continue
    return total


def spend(root: Path, since: float) -> dict:
    data = root / "data"
    out = {"forecasts": ledger_spend(data / "pmt.db", since),
           "rule_accounts": sum(ledger_spend(Path(p), since) for p in glob.glob(str(data / "rules" / "*.db"))),
           "checkins": checkin_spend(data / "checkin", since)}
    out["total"] = sum(out.values())
    return out


def pace(root: Path, now: datetime, per_pct: float = DOLLARS_PER_PCT, target: float = TARGET_PCT,
         reserve: float = RESERVE_PCT) -> dict:
    reset = last_reset(now)
    nxt = last_reset(now + timedelta(days=7))
    week = spend(root, reset.timestamp())
    day = spend(root, (now - timedelta(hours=24)).timestamp())
    hours_left = max((nxt - now).total_seconds() / 3600.0, 0.0)
    used = week["total"] / per_pct
    projected = used + day["total"] / 24.0 * hours_left / per_pct
    room = target - reserve - projected                         # percent of the week left to give out
    checkins_left = max(hours_left / CHECKIN_EVERY_H, 1.0)
    extra_usd = room * per_pct / checkins_left
    if room >= 0:
        items = min(MAX_ITEMS, 1 + int(math.floor(extra_usd / ITEM_USD)))
    else:                                                        # over: one item while under the target, then none
        items = 1 if projected <= target else 0
    return {"now": now.astimezone(CENTRAL).isoformat(timespec="minutes"),
            "reset": reset.astimezone(CENTRAL).isoformat(timespec="minutes"),
            "next_reset": nxt.astimezone(CENTRAL).isoformat(timespec="minutes"),
            "hours_left": round(hours_left, 1), "week_usd": {k: round(v, 2) for k, v in week.items()},
            "last_24h_usd": round(day["total"], 2), "used_pct": round(used, 1), "projected_pct": round(projected, 1),
            "target_pct": target, "reserve_pct": reserve, "extra_usd_per_checkin": round(extra_usd, 2), "items": items}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--per-pct", type=float, default=DOLLARS_PER_PCT, help="list-price dollars per 1%% of the week")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args()
    p = pace(Path(args.root), datetime.now(timezone.utc), per_pct=args.per_pct)
    if args.json:
        print(json.dumps(p, indent=1))
        return 0
    w = p["week_usd"]
    print(f"week since {p['reset']}: ${w['total']:.2f} at list price (forecasts ${w['forecasts']:.2f}, rule accounts "
          f"${w['rule_accounts']:.2f}, check-ins ${w['checkins']:.2f}), about {p['used_pct']:.0f}% of the week")
    print(f"last 24 h ${p['last_24h_usd']:.2f}; at that rate the week ends near {p['projected_pct']:.0f}% "
          f"(target {p['target_pct']:.0f}%, {p['reserve_pct']:.0f}% kept for the user's own sessions); "
          f"{p['hours_left']:.0f} h to the reset")
    print(f"ITEMS {p['items']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
