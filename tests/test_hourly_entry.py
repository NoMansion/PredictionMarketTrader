"""research/hourly_entry.py on made-up hourly bars."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))

import hourly_entry as he  # noqa: E402

H = 3600


def bars(ticker, rows):
    return [dict(ticker=ticker, ts=i * H, bid=b, ask=a, bid_hi=bh, px_hi=ph, bid_op=bo)
            for i, (b, a, bh, ph, bo) in enumerate(rows)]


def test_first_bar_next_open_and_resting_fill():
    h = pd.DataFrame(bars("A", [(0.20, 0.30, 0.20, None, 0.20),     # mid 25c: not a 5c signal
                                (0.02, 0.06, 0.02, None, 0.15),     # mid 4c, spread 4c: first 5c signal
                                (0.03, 0.05, 0.06, None, 0.03),     # next open bid 3c; bid_hi 6c >= ask 6c: filled
                                (0.02, 0.04, 0.02, None, 0.02)])
                     + bars("B", [(0.01, 0.04, 0.01, None, 0.01), (0.01, 0.04, 0.01, 0.03, 0.02)]))
    mk = pd.DataFrame(dict(ticker=["A", "B"], event=["E1", "E2"], close_ts=[10 * H, 10 * H], y=[0.0, 1.0],
                           mult=[1.0, 1.0], maker_fee=[False, False]))
    tk = he.bets(h, mk, 0.0, 0.05, 0.05, "tk")
    a = tk.set_index("ticker").loc["A"]
    cost = 0.97 + 0.07 * 0.03 * 0.97
    assert a["cost"] == pytest.approx(cost)
    assert a["ret"] == pytest.approx((1 - cost) / cost)
    b = tk.set_index("ticker").loc["B"]
    assert b["ret"] == pytest.approx(-1.0)               # YES won: the NO bet is lost
    mkb = he.bets(h, mk, 0.0, 0.05, 0.05, "mk")
    assert list(mkb["ticker"]) == ["A"]                  # B never traded through its 4c ask: no fill
    assert mkb["cost"].iloc[0] == pytest.approx(0.94)    # no maker fee on this series
    s = he.summary(tk)
    assert s["bets"] == 2 and s["events"] == 2 and s["tail_losing"] == 1


def test_signal_at_or_after_close_is_ignored():
    h = pd.DataFrame(bars("A", [(0.20, 0.30, 0.2, None, 0.2), (0.02, 0.04, 0.02, None, 0.02), (0.02, 0.04, 0.02, None, 0.02)]))
    mk = pd.DataFrame(dict(ticker=["A"], event=["E"], close_ts=[1 * H], y=[0.0], mult=[1.0], maker_fee=[False]))
    assert he.bets(h, mk, 0.0, 0.05, 0.05, "tk").empty
