"""research/one_per_event.py: the rung picked per event uses only the event's first bet day."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from one_per_event import pick_one_per_event  # noqa: E402


def test_nearest_20c_on_the_first_day_only():
    # rows 0-2: event 0 day 1 (mids 0.05, 0.22, 0.30); row 3: event 0 day 2 at exactly 0.20 (later: not eligible)
    # rows 4-5: event 1 day 5 (0.10, 0.34): 0.10 is nearer; row 6: not a bet
    event = np.array([0, 0, 0, 0, 1, 1, 1])
    day = np.array([1, 1, 1, 2, 5, 5, 5])
    mid = np.array([0.05, 0.22, 0.30, 0.20, 0.10, 0.34, 0.20])
    rows = np.array([0, 1, 2, 3, 4, 5])
    assert pick_one_per_event(rows, event, day, mid).tolist() == [1, 4]
    assert pick_one_per_event(np.array([], int), event, day, mid).size == 0
