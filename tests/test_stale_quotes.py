"""research/stale_quotes.py: a bar is stale only if its mid equals each of its market's k earlier mids."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from stale_quotes import stale_flags, STALE, MOVED, NEW  # noqa: E402


def test_stale_moved_new_per_market():
    ticker = np.array(["a"] * 5 + ["b"] * 3)
    mid = np.array([0.20, 0.20, 0.20, 0.20, 0.21, 0.10, np.nan, 0.10])
    out = stale_flags(ticker, mid, 2)
    # a: rows 0-1 too new; row 2 equals both earlier; row 3 too; row 4 moved. b: rows 5-6 new; row 7 has a NaN earlier
    assert out.tolist() == [NEW, NEW, STALE, STALE, MOVED, NEW, NEW, MOVED]
    assert stale_flags(ticker, mid, 3).tolist()[3] == STALE
