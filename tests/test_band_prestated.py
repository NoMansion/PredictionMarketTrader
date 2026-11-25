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
