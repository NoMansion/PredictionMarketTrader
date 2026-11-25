"""research/series_concentration.py on a hand-made bets frame."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from series_concentration import drop_top, series_table  # noqa: E402


def _frame(spec):
    """spec: (series, oos, [returns]); one event per bet."""
    rows = []
    for s, oos, rets in spec:
        for k, r in enumerate(rets):
            rows.append({"series": s, "oos": oos, "r": r, "event": f"{s}{int(oos)}_{k}"})
    return pd.DataFrame(rows)


def test_one_series_carrying_the_money_is_fragile_and_a_spread_one_is_not():
    # A earns everything in both halves; B and C are flat
    b = _frame([("A", False, [0.3] * 20), ("B", False, [0.0] * 20), ("C", False, [0.01] * 20),
                ("A", True, [0.3] * 20), ("B", True, [0.0] * 20), ("C", True, [0.0] * 20)])
    t, v = drop_top(b)
    assert v["fragile"]
    assert t[(t["dropped"] == 1) & (t["half"] == "out")]["series_dropped"].iloc[0] == "A"
    assert series_table(b)["series"].iloc[0] == "A"
    # same return in every series: dropping one changes nothing
    b2 = _frame([(s, o, [0.1] * 20) for s in "ABC" for o in (False, True)])
    _, v2 = drop_top(b2)
    assert not v2["fragile"]
    assert abs(v2["oos_without_top1"] - 0.1) < 1e-12


def test_series_are_picked_on_their_in_sample_record_only():
    from series_concentration import select_by_history
    b = _frame([("A", False, [0.2] * 12), ("B", False, [-0.1] * 12), ("C", False, [0.5] * 3),
                ("A", True, [-0.3] * 5), ("B", True, [0.4] * 5), ("C", True, [0.1] * 5), ("D", True, [0.0] * 5)])
    t = select_by_history(b).set_index(["group", "half"])
    assert abs(t.loc[("picked", "out"), "per_bet"] + 0.3) < 1e-12      # A, despite its out-of-sample loss
    assert abs(t.loc[("rejected", "out"), "per_bet"] - 0.4) < 1e-12    # B
    assert t.loc[("thin", "out"), "series"] == 2                        # C (3 events) and D (new)
