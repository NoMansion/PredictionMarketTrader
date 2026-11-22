"""research/hourly_bars.py against a fake client: no network, databases in tmp_path."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))

import hourly_bars as hb  # noqa: E402

C = 1_767_225_600          # 2026-01-01 00:00 UTC
H = 3600


class Err(Exception):
    def __init__(self, code):
        super().__init__(f"status {code}")
        self.status_code = code


class FakeK:
    def __init__(self, answers):
        self.answers = answers          # ticker -> list of candle dicts, or an int status to raise
        self.calls = []

    def get(self, path, **params):
        self.calls.append((path, params))
        ticker = path.split("/markets/")[1].split("/")[0]
        a = self.answers[ticker]
        if isinstance(a, int):
            raise Err(a)
        return {"candlesticks": a}


def bar(ts, bid, ask):
    return {"end_period_ts": ts, "yes_bid": {"close_dollars": str(bid), "open_dollars": str(bid)},
            "yes_ask": {"close_dollars": str(ask)}, "price": {"close_dollars": str((bid + ask) / 2)}, "volume_fp": "10"}


def test_window_is_the_last_hours_and_never_before_the_open():
    assert hb.window(C - 10 * 86400, C, 48) == (C - 48 * H, C + H)
    assert hb.window(C - 5 * H, C, 48) == (C - 5 * H, C + H)
    assert hb.window(None, C, 48) is None
    assert hb.window(C, C, 48) is None


def test_fetch_stores_hourly_bars_uses_the_right_path_and_resumes(tmp_path):
    db = hb.open_db(tmp_path / "h.db")
    k = FakeK({"A": [bar(C - H, 0.9, 0.92), bar(C, 0.95, 0.97)], "B": [], "C": 404, "D": 429})
    mk = [("A", "SA", C - 10 * 86400, C, "hist"), ("B", "SB", C - 86400, C, "recent"),
          ("C", "SC", C - 86400, C, "hist"), ("D", "SD", C - 86400, C, "hist"), ("E", "SE", None, C, "hist")]
    logs = []
    counts = hb.fetch(db, k, mk, 48, log=logs.append)
    assert counts[1] == 1 and counts[2] == 1 and counts[4] == 1 and counts[3] == 1 and counts["retry"] == 1
    path, params = k.calls[0]
    assert path == "/historical/markets/A/candlesticks"
    assert params == {"start_ts": C - 48 * H, "end_ts": C + H, "period_interval": 60}
    assert k.calls[1][0] == "/series/SB/markets/B/candlesticks"
    rows = db.execute("SELECT ts, bid, ask, vol FROM candles_1h WHERE ticker='A' ORDER BY ts").fetchall()
    assert rows == [(C - H, 0.9, 0.92, 10.0), (C, 0.95, 0.97, 10.0)]
    st = dict(db.execute("SELECT ticker, status FROM hourly_done"))
    assert st == {"A": 1, "B": 2, "C": 4, "E": 3}         # D (throttled) is left for the next run
    k2 = FakeK({"D": [bar(C, 0.5, 0.6)]})
    counts = hb.fetch(db, k2, mk, 48)
    assert counts["skipped"] == 4 and counts[1] == 1 and len(k2.calls) == 1


def test_fetch_stops_at_max_markets(tmp_path):
    db = hb.open_db(tmp_path / "h.db")
    k = FakeK({t: [bar(C, 0.5, 0.6)] for t in "ABC"})
    mk = [(t, "S", C - 86400, C, "hist") for t in "ABC"]
    counts = hb.fetch(db, k, mk, 48, max_markets=2)
    assert counts[1] == 2 and len(k.calls) == 2
