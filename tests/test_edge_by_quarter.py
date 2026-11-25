"""research/edge_by_quarter.py on a hand-made bets frame."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from edge_by_quarter import by_quarter  # noqa: E402


def _frame(rets_by_quarter, oos_from):
    rows = []
    for qi, (start, rets) in enumerate(rets_by_quarter):
        ts = pd.Timestamp(start).timestamp()
        for k, r in enumerate(rets):
            rows.append({"r": r, "event": f"E{qi}_{k}", "close_ts": ts + k * 3600, "oos": qi >= oos_from})
    return pd.DataFrame(rows)


def test_a_steadily_shrinking_edge_is_decaying_and_a_flat_one_is_not():
    rng = np.random.default_rng(0)
    starts = ["2025-01-15", "2025-04-15", "2025-07-15", "2025-10-15", "2026-01-15", "2026-04-15", "2026-07-15"]
    shrink = [(s, list(0.20 - 0.05 * i + rng.normal(0, 0.01, 40))) for i, s in enumerate(starts)]
    t, v = by_quarter(_frame(shrink, oos_from=5))
    assert list(t["quarter"]) == ["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3"]
    assert t["bets"].eq(40).all() and t["events"].eq(40).all() and list(t["oos"]) == [False] * 5 + [True] * 2
    assert v["slope_per_quarter"] < -0.04 and v["slope_t"] < -2 and v["oos_all_below_is"] and v["decaying"]
    flat = [(s, list(0.05 + rng.normal(0, 0.01, 40))) for s in starts]
    assert not by_quarter(_frame(flat, oos_from=5))[1]["decaying"]


def test_sub_periods_split_by_close_date_and_run_the_tail_test():
    from edge_by_quarter import sub_periods
    starts = ["2026-05-15", "2026-08-15"]
    b = _frame([(starts[0], [0.05] * 30), (starts[1], [0.05] * 29 + [-1.0])], oos_from=0)
    t = sub_periods(b)
    assert list(t["bets"]) == [30, 30] and list(t["events"]) == [30, 30]
    assert abs(t["per_bet"].iloc[0] - 0.05) < 1e-12 and list(t["losing_ev"]) == [0, 1]
    assert t["period"].iloc[1] == "2026-07-01 to last"
