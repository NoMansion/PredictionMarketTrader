"""research/fill_audit.py: re-deciding the observation logs' resting NO bids from the full trade record."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))

import fill_audit as fa  # noqa: E402


def tr(minute, side, yes_px, n):
    return {"created_time": f"2026-11-24T10:{minute:02d}:00Z", "taker_side": side, "yes_price_dollars": f"{yes_px:.4f}",
            "count_fp": f"{n:.2f}"}


def test_queue_rule_needs_the_queue_ahead_and_the_order_traded_at_the_price():
    trades = [tr(1, "yes", .11, 30), tr(2, "yes", .11, 30), tr(3, "yes", .10, 500)]
    d = fa.decide(trades, level=.11, need=50)
    assert d["queue"] == fa.ts("2026-11-24T10:02:00Z") and d["through"] == d["queue"]
    assert fa.decide(trades, level=.11, need=100)["queue"] is None           # only 60 traded at the price


def test_a_yes_buyer_above_the_price_fills_both_rules():
    d = fa.decide([tr(5, "yes", .13, 1)], level=.11, need=10 ** 6)
    assert d["queue"] and d["through"]


def test_a_no_buyer_at_or_above_the_price_fills_only_the_through_rule():
    for px in (.11, .12):                       # a YES bid rested at the order's price or above it
        d = fa.decide([tr(5, "no", px, 1)], level=.11, need=10 ** 6)
        assert d["queue"] is None and d["through"] == fa.ts("2026-11-24T10:05:00Z")
    assert fa.decide([tr(5, "no", .10, 1)], level=.11, need=None) == {"queue": None, "through": None}


def test_unrecorded_queue_counts_only_trades_through_and_bad_rows_are_skipped():
    trades = [{"created_time": "x"}, tr(1, "yes", .11, 10 ** 6)]
    assert fa.decide(trades, level=.11, need=None) == {"queue": None, "through": None}


def test_backtest_rates_first_bar_any_bar_and_ever():
    # two markets: A qualifies on bars 0-2 and fills only on bar 1; B qualifies on bar 0 and fills there
    df = pd.DataFrame({"ticker": ["A", "A", "A", "B"], "quoted": [True] * 4})

    class FakePanel:
        def __init__(self, d):
            self.ticker = d["ticker"].to_numpy()
            self.ok = {("no", "mk"): np.array([False, True, False, True])}

        def first_per_market(self, mask):
            idx = np.flatnonzero(mask)
            keep = np.ones(idx.size, bool)
            keep[1:] = self.ticker[idx][1:] != self.ticker[idx][:-1]
            return idx[keep]

    import backtest
    real = backtest.Panel
    backtest.Panel = FakePanel
    try:
        r = fa.backtest_rates(df, np.array([True, True, True, True]))
    finally:
        backtest.Panel = real
    assert r == {"markets": 2, "first_bar": 0.5, "any_bar": 0.5, "bars": 4, "ever": 1.0}
