"""research/band_prestated.py: markets listed by the bar (no hindsight) and bars before a market's first masked bar."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from band_prestated import listed_at_bar, bars_before_first  # noqa: E402


def test_listed_at_bar_counts_only_markets_open_by_then():
    event = np.array(["e", "e", "e", "f", "g"])
    ts = np.array([100, 200, 300, 150, 10])
    opens = {"e": [300, 100, 150, 250], "f": [10, 20]}
    assert listed_at_bar(event, ts, opens).tolist() == [1, 2, 4, 2, 0]


def test_bars_before_first_masked_bar():
    ticker = np.array(["a"] * 4 + ["b"] * 3)
    mask = np.array([0, 0, 1, 1, 1, 0, 1], dtype=bool)
    assert bars_before_first(ticker, mask) == {"a": 2, "b": 0}


def test_simulate_stake_multiplier_column():
    import portfolio
    day = 86400.0
    base = np.array([[0, day, 0.10, 1], [2 * day, 3 * day, 0.10, 2]], dtype="float64")
    one = portfolio.simulate(base, stake_frac=0.01, event_cap=0.5)
    same = portfolio.simulate(np.c_[base, [1.0, 1.0]], stake_frac=0.01, event_cap=0.5)
    two = portfolio.simulate(np.c_[base, [2.0, 1.0]], stake_frac=0.01, event_cap=0.5)
    assert same.total == one.total
    assert abs(two.total - (1.002 * 1.001 * 1.0) + 1) < 1e-3 and two.total > one.total
