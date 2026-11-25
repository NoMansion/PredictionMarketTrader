"""scripts/usage_pace.py: the check-in's estimate of the week's Claude usage and how many queue items it may work."""
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import usage_pace as up  # noqa: E402

UTC = timezone.utc


def test_last_reset_is_the_sunday_4pm_central_before_now():
    # Tuesday 2026-11-24 7:00 pm CST (01:00 UTC on the 25th): the reset was Sunday the 22nd, 4:00 pm CST = 22:00 UTC
    assert up.last_reset(datetime(2026, 11, 25, 1, 0, tzinfo=UTC)) == datetime(2026, 11, 22, 22, 0, tzinfo=UTC)
    # Sunday 3:59 pm CST: still the week before; 4:00 pm: the new week
    assert up.last_reset(datetime(2026, 11, 29, 21, 59, tzinfo=UTC)) == datetime(2026, 11, 22, 22, 0, tzinfo=UTC)
    assert up.last_reset(datetime(2026, 11, 29, 22, 0, tzinfo=UTC)) == datetime(2026, 11, 29, 22, 0, tzinfo=UTC)
    # summer time: 4:00 pm CDT is 21:00 UTC
    assert up.last_reset(datetime(2026, 7, 1, 12, 0, tzinfo=UTC)) == datetime(2026, 6, 28, 21, 0, tzinfo=UTC)


def make_root(tmp_path, forecasts=(), rule_forecasts=(), checkins=()):
    """forecasts / rule_forecasts: (ts, cost); checkins: (mtime, cost)."""
    data = tmp_path / "data"
    (data / "rules").mkdir(parents=True)
    (data / "checkin").mkdir()
    for path, rows in ((data / "pmt.db", forecasts), (data / "rules" / "rule_x_claude.db", rule_forecasts)):
        db = sqlite3.connect(str(path))
        db.execute("CREATE TABLE forecasts (ts REAL, cost_usd REAL)")
        db.executemany("INSERT INTO forecasts VALUES (?, ?)", rows)
        db.commit()
        db.close()
    sqlite3.connect(str(data / "rules" / "rule_plain.db")).close()   # a rule account that never asks Claude
    for i, (mtime, cost) in enumerate(checkins):
        f = data / "checkin" / f"run{i}.json"
        f.write_text(json.dumps({"total_cost_usd": cost, "result": "PMT ok"}), encoding="utf-8")
        os.utime(f, (mtime, mtime))
    (data / "checkin" / "broken.json").write_text("not json", encoding="utf-8")
    return tmp_path


NOW = datetime(2026, 11, 25, 1, 0, tzinfo=UTC)          # Tuesday 7:00 pm CST
T = NOW.timestamp()
LAST_WEEK = datetime(2026, 11, 22, 21, 0, tzinfo=UTC).timestamp()   # an hour before the reset


def test_spend_counts_every_source_since_the_reset_only(tmp_path):
    root = make_root(tmp_path, forecasts=[(T - 3600, 10.0), (LAST_WEEK, 99.0)], rule_forecasts=[(T - 7200, 2.0)],
                     checkins=[(T - 600, 1.25), (LAST_WEEK, 50.0)])
    s = up.spend(root, up.last_reset(NOW).timestamp())
    assert s == {"forecasts": 10.0, "rule_accounts": 2.0, "checkins": 1.25, "total": 13.25}


def test_room_under_the_target_gives_extra_items(tmp_path):
    # $85 this week = 10%; $20 in the last 24 h over 117 h left = about 11.5% more: ends near 21.5%, far under 75 - 7
    root = make_root(tmp_path, forecasts=[(T - 30 * 3600, 65.0), (T - 3600, 20.0)])
    p = up.pace(root, NOW)
    assert p["used_pct"] == 10.0 and 21 < p["projected_pct"] < 22
    assert p["items"] == up.MAX_ITEMS


def test_close_to_the_target_gives_one_item_and_over_it_none(tmp_path):
    # 60% used, $60 a day: ends near 94%, over the 75% target: health only
    root = make_root(tmp_path, forecasts=[(T - 40 * 3600, 450.0), (T - 3600, 60.0)])
    p = up.pace(root, NOW)
    assert p["projected_pct"] > up.TARGET_PCT and p["items"] == 0
    # ends between the reserve line (68%) and the target (75%): the one standing item, no extras
    root2 = make_root(tmp_path / "b", forecasts=[(T - 40 * 3600, 592.0), (T - 3600, 3.0)])
    p2 = up.pace(root2, NOW)
    assert up.TARGET_PCT - up.RESERVE_PCT < p2["projected_pct"] <= up.TARGET_PCT and p2["items"] == 1


def test_main_prints_items_last(tmp_path, capsys, monkeypatch):
    root = make_root(tmp_path, forecasts=[(T - 3600, 5.0)])
    monkeypatch.setattr(sys, "argv", ["usage_pace.py", "--root", str(root)])
    assert up.main() == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    assert last.startswith("ITEMS ") and 0 <= int(last.split()[1]) <= up.MAX_ITEMS
