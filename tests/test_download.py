"""The Kalshi history downloader (research/kalshi_download.py) against a fake exchange, and the parts of
research/panel.py the backtest tests do not reach, on a hand-built database where every value is known.

No test touches the network or data/kalshi_hist.db: the real KalshiHTTP client is used with a fake HTTP client
injected, time.sleep is replaced by a recorder, and every database lives in tmp_path."""
import os
import re
import runpy
import sqlite3
import sys
import time
import zlib
from pathlib import Path
from urllib.parse import unquote

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))

import kalshi_download as kd  # noqa: E402
import panel  # noqa: E402
from src.kalshi_http import KalshiError, KalshiHTTP  # noqa: E402

DAY = 86400
O = 1_735_689_600                     # 2025-01-01 00:00 UTC
BASE = "https://fake.test/v2"
HIST = "/historical/markets"


# ---------------------------------------------------------------------------------------------------------------
# a fake exchange
# ---------------------------------------------------------------------------------------------------------------

class Resp:
    def __init__(self, status=200, body=None, headers=None):
        self.status_code = status
        self._body = {} if body is None else body
        self.headers = headers or {}
        self.text = "" if status == 200 else f"<html>status {status}</html>"

    def json(self):
        return self._body


class FakeAPI:
    """Answers the paths the downloader uses, decoding the URL once the way a real server does.

    Scripted answers (an int status, a Resp, or an exception to raise) are keyed by path or by (path, series_ticker):
    `queue` answers are used up one per request, `always` answers every request."""

    def __init__(self):
        self.page = 2
        self.series = {}        # category -> [series dicts]
        self.hist = {}          # series -> [market dicts] in /historical/markets
        self.recent = {}        # series -> [market dicts] in /markets?status=settled
        self.candles = {}       # ticker -> [candle dicts]; a ticker missing here answers 404
        self.queued = {}
        self.always = {}
        self.calls = []         # (decoded path, params)
        self.urls = []          # raw URLs as sent

    def queue(self, key, *answers):
        self.queued.setdefault(key, []).extend(answers)
        return self

    def paths(self, prefix=""):
        return [p for p, _ in self.calls if p.startswith(prefix)]

    def get(self, url, params=None):
        assert url.startswith(BASE), url
        self.urls.append(url)
        path = unquote(url[len(BASE):])
        params = dict(params or {})
        self.calls.append((path, params))
        ans = None
        for key in ((path, params.get("series_ticker")), path):
            if self.queued.get(key):
                ans = self.queued[key].pop(0)
                break
            if key in self.always:
                ans = self.always[key]
                break
        if ans is not None:
            if isinstance(ans, BaseException):
                raise ans
            return ans if isinstance(ans, Resp) else Resp(ans)
        return self.route(path, params)

    def route(self, path, params):
        if path == "/series":
            return Resp(body={"series": self.series.get(params["category"], [])})
        if path in (HIST, "/markets"):
            if path == "/markets":
                assert params.get("status") == "settled"
            items = (self.hist if path == HIST else self.recent).get(params["series_ticker"], [])
            start = int(params.get("cursor") or 0)
            nxt = start + self.page
            return Resp(body={"markets": items[start:nxt], "cursor": str(nxt) if nxt < len(items) else ""})
        m = (re.fullmatch(r"/historical/markets/(.+)/candlesticks", path)
             or re.fullmatch(r"/series/[^/]+/markets/(.+)/candlesticks", path))
        if m and m.group(1) in self.candles:
            return Resp(body={"candlesticks": self.candles[m.group(1)]})
        return Resp(404)


def mkt(ticker, result="yes", volume=10.0, **kw):
    d = {"ticker": ticker, "event_ticker": ticker.rsplit("-", 1)[0], "title": f"Will {ticker}?", "yes_sub_title": "above 3",
         "open_time": "2025-01-01T00:00:00Z", "close_time": "2025-01-11T00:00:00Z", "result": result,
         "settlement_value_dollars": "1.0000" if result == "yes" else "0.0000", "volume_fp": f"{volume:.2f}",
         "open_interest_fp": "5.00", "last_price_dollars": "0.5500", "strike_type": "greater", "floor_strike": 3.5,
         "expected_expiration_time": "2025-01-12T00:00:00Z", "can_close_early": True}
    d.update(kw)
    return d


def cbar(ts, bid=0.40, ask=0.44, px=0.42, vol="3.00"):
    def r(x):
        return f"{x:.4f}"
    return {"end_period_ts": ts,
            "yes_bid": {"open_dollars": r(bid - .01), "close_dollars": r(bid), "high_dollars": r(bid + .02), "low_dollars": r(bid - .02)},
            "yes_ask": {"open_dollars": r(ask + .01), "close_dollars": r(ask), "high_dollars": r(ask + .02), "low_dollars": r(ask - .02)},
            "price": {"close_dollars": r(px), "high_dollars": r(px + .01), "low_dollars": r(px - .01), "mean_dollars": r(px)},
            "volume_fp": vol, "open_interest_fp": "7.00"}


def cpath(ticker):
    return f"/historical/markets/{ticker}/candlesticks"


def put(db, ticker, category="Economics", volume=10.0, open_ts=O, close_ts=O + 10 * DAY, src="hist", series="S",
        done=0, early=0, rnd=None):
    db.execute("INSERT INTO markets (ticker, series, event, category, open_ts, close_ts, result, volume, src, candles_done, "
               "rnd, early) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
               (ticker, series, ticker, category, open_ts, close_ts, "yes", volume, src, done,
                kd.shuffle_key(ticker) if rnd is None else rnd, early))
    db.commit()


def done_of(db, ticker):
    return db.execute("SELECT candles_done FROM markets WHERE ticker=?", (ticker,)).fetchone()[0]


def logged(capsys):
    """The log lines printed so far, each checked for its timestamp and returned without it."""
    out = capsys.readouterr().out.splitlines()
    for line in out:
        assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ", line), line
    return [line[20:] for line in out]


@pytest.fixture(autouse=True)
def sleeps(monkeypatch):
    rec = []
    monkeypatch.setattr(time, "sleep", rec.append)      # the same module object kalshi_http and kalshi_download use
    return rec


@pytest.fixture
def api():
    return FakeAPI()


@pytest.fixture
def k(api):
    return KalshiHTTP(min_interval=0, base=BASE, client=api)


@pytest.fixture
def db(tmp_path):
    con = sqlite3.connect(str(tmp_path / "hist.db"))
    con.executescript(kd.SCHEMA)
    yield con
    con.close()


# ---------------------------------------------------------------------------------------------------------------
# small helpers and the schema
# ---------------------------------------------------------------------------------------------------------------

def test_parsing_helpers():
    assert kd.ts("2025-01-01T00:00:00Z") == O
    assert kd.ts("2025-01-01T01:00:00+01:00") == O
    assert kd.ts(None) is None and kd.ts("not a date") is None and kd.ts("") is None
    assert kd.num("0.55") == 0.55 and kd.num(3) == 3.0
    assert kd.num(None) is None and kd.num("n/a") is None and kd.num("") is None
    assert kd.first({"a": None, "b": "", "c": 0, "d": 1}, "a", "b", "c", "d") == 0      # 0 is a value, "" is not
    assert kd.first({"a": None}, "a", "b") is None


def test_shuffle_key_is_a_fixed_checksum():
    assert kd.shuffle_key("KXCPI-25JAN-T3") == zlib.crc32(b"KXCPI-25JAN-T3")
    keys = [kd.shuffle_key(f"T-{i}") for i in range(200)]
    assert all(0 <= x < 2 ** 32 for x in keys) and len(set(keys)) == 200
    assert keys != sorted(keys)                     # not the listing order


def test_log_lines_carry_a_timestamp(capsys):
    kd.log("hello")
    assert logged(capsys) == ["hello"]


def test_schedule_prefers_the_expected_expiration():
    assert kd.schedule({"expected_expiration_time": "2025-01-01T00:00:00Z", "expiration_time": "2030-01-01T00:00:00Z",
                        "can_close_early": True}) == (O, 1)
    assert kd.schedule({"expiration_time": "2025-01-01T00:00:00Z"}) == (O, 0)
    assert kd.schedule({"expected_expiration_time": "", "latest_expiration_time": "2025-01-01T00:00:00Z"}) == (O, 0)
    assert kd.schedule({}) == (None, 0)


def test_market_row_maps_fields_and_falls_back():
    r = kd.market_row(mkt("S-A"), "S", "Economics", "hist")
    assert len(r) == 20
    assert r[:9] == ("S-A", "S", "S", "Economics", "Will S-A?", "above 3", O, O + 10 * DAY, "yes")
    assert r[9:17] == (1.0, 10.0, 5.0, 0.55, "greater", 3.5, None, "hist")
    assert r[17] == kd.shuffle_key("S-A") and r[18:] == (O + 11 * DAY, 1)
    # older field names, and a partial record: everything missing becomes NULL instead of an error
    old = {"ticker": "S-B", "subtitle": "old sub", "volume": 7, "open_interest": 2, "result": "no"}
    r = kd.market_row(old, "S", "Economics", "recent")
    assert r[5] == "old sub" and r[6] is None and r[7] is None and r[10] == 7.0 and r[11] == 2.0
    assert r[9] is None and r[12] is None and r[16] == "recent" and r[18:] == (None, 0)


def test_candle_rows_match_the_table_columns(db):
    legacy = {"end_period_ts": O + DAY, "yes_bid": {"close": "0.3"}, "volume": 5, "open_interest": 9}
    broken = {"end_period_ts": O + 2 * DAY, "yes_bid": None, "yes_ask": {"close_dollars": "n/a"}}
    no_ts = cbar(None)
    rows = kd.candle_rows("T", [cbar(O), legacy, broken, no_ts])
    assert len(rows) == 3                            # a bar without an end time is dropped
    db.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    db.row_factory = sqlite3.Row
    got = [dict(r) for r in db.execute("SELECT * FROM candles ORDER BY ts")]
    assert got[0] == pytest.approx({"ticker": "T", "ts": O, "bid": .40, "ask": .44, "bid_hi": .42, "bid_lo": .38, "ask_hi": .46,
                                    "ask_lo": .42, "px": .42, "px_hi": .43, "px_lo": .41, "vol": 3.0, "oi": 7.0,
                                    "bid_op": .39, "ask_op": .45, "px_mean": .42})
    assert got[1]["bid"] == pytest.approx(0.3) and got[1]["ask"] is None and got[1]["vol"] == 5 and got[1]["oi"] == 9
    assert all(got[2][c] is None for c in ("bid", "ask", "px", "vol", "oi"))


def test_schema_is_idempotent_and_keys_bars_by_ticker_and_time(db):
    db.executescript(kd.SCHEMA)                      # a second run on an existing database changes nothing
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {"series", "markets", "candles"}
    idx = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")}
    assert {"markets_series", "markets_todo"} <= idx
    cols = [r[1] for r in db.execute("PRAGMA table_info(markets)")]
    assert cols[-5:] == ["src", "candles_done", "rnd", "exp_ts", "early"]
    row = ("T", O) + (0.5,) * 14
    db.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
    db.execute("INSERT OR IGNORE INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
    assert db.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 1
    db.execute("INSERT INTO series (ticker) VALUES ('X')")
    assert db.execute("SELECT markets_done FROM series").fetchone()[0] == 0


def test_frontier_is_the_first_unattempted_key(db):
    assert kd.frontier(db, "Economics", 1.0) == 2 ** 32
    put(db, "A", rnd=10, done=1)
    put(db, "B", rnd=20)
    put(db, "C", rnd=5, volume=0.5)                  # too small to be in the sample: does not hold it back
    put(db, "D", rnd=1, category="Politics")
    assert kd.frontier(db, "Economics", 1.0) == 20
    assert kd.frontier(db, "Economics", 0.1) == 5
    db.execute("UPDATE markets SET candles_done=2 WHERE ticker IN ('B','C')")
    assert kd.frontier(db, "Economics", 0.1) == 2 ** 32


# ---------------------------------------------------------------------------------------------------------------
# series
# ---------------------------------------------------------------------------------------------------------------

def test_series_are_listed_once_per_category(db, api, k, capsys):
    api.series = {"Economics": [{"ticker": "S1", "title": "CPI", "fee_type": "quadratic", "fee_multiplier": "0.5",
                                 "frequency": "monthly", "tags": ["inflation", "us"]},
                                {"ticker": "S2", "tags": None}],
                  "Politics": None}
    kd.phase_series(db, k, ["Economics", "Politics"])
    rows = db.execute("SELECT ticker, category, title, fee_type, fee_multiplier, frequency, tags, markets_done FROM series "
                      "ORDER BY ticker").fetchall()
    assert rows == [("S1", "Economics", "CPI", "quadratic", 0.5, "monthly", "inflation,us", 0),
                    ("S2", "Economics", None, None, None, None, "", 0)]
    assert logged(capsys) == ["series: Economics: 2", "series: Politics: 0"]
    assert [p["category"] for _, p in api.calls] == ["Economics", "Politics"]
    api.calls.clear()
    kd.phase_series(db, k, ["Economics", "Politics"])          # resume: a category with series is not asked again
    assert [p["category"] for _, p in api.calls] == ["Politics"]


# ---------------------------------------------------------------------------------------------------------------
# market listings
# ---------------------------------------------------------------------------------------------------------------

def add_series(db, *tickers, category="Economics", done=0):
    db.executemany("INSERT INTO series (ticker, category, markets_done) VALUES (?,?,?)", [(t, category, done) for t in tickers])
    db.commit()


def test_listing_follows_the_cursor_and_keeps_only_yes_no(db, api, k, capsys):
    add_series(db, "S1")
    api.hist["S1"] = [mkt("S1-A"), mkt("S1-B", result="no"), mkt("S1-C", result="scalar"), mkt("S1-D", result=""),
                      mkt("S1-E", result="yes")]
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    assert [p.get("cursor") for _, p in api.calls] == [None, "2", "4"]
    assert all(p["series_ticker"] == "S1" and p["limit"] == 1000 for _, p in api.calls)
    rows = db.execute("SELECT ticker, src, rnd, candles_done, early FROM markets ORDER BY ticker").fetchall()
    assert rows == [(t, "hist", kd.shuffle_key(t), 0, 1) for t in ("S1-A", "S1-B", "S1-E")]
    assert db.execute("SELECT markets_done FROM series").fetchone()[0] == 1
    assert logged(capsys) == ["markets[hist]: 1 series to list",
                              "markets[hist]: 0/1 series, 3 markets so far (Economics S1: 3); 3 requests, 0 rate limits, interval 0.00s"]


def test_listing_resumes_without_duplicates(db, api, k):
    add_series(db, "S1", "S2")
    add_series(db, "P1", category="Politics")
    api.hist = {"S1": [mkt("S1-A"), mkt("S1-B")], "S2": [mkt("S2-A")], "P1": [mkt("P1-A")]}
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    assert sorted(p["series_ticker"] for _, p in api.calls) == ["S1", "S2"]       # only the categories asked for
    api.calls.clear()
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    assert api.calls == []                                                      # finished series are not listed again
    db.execute("UPDATE series SET markets_done=0")                                # and if they are, nothing doubles
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    assert db.execute("SELECT COUNT(*), COUNT(DISTINCT ticker) FROM markets").fetchone() == (3, 3)


def test_listing_stops_at_max_per_series(db, api, k):
    add_series(db, "S1")
    api.hist["S1"] = [mkt(f"S1-{i}") for i in range(7)]
    kd.phase_markets(db, k, ["Economics"], 3, "hist")
    assert db.execute("SELECT COUNT(*) FROM markets").fetchone()[0] == 3
    assert len(api.calls) == 2                       # it stops reading pages once the cap is reached


def test_a_series_the_archive_does_not_know_counts_as_listed(db, api, k, capsys, sleeps):
    add_series(db, "S1")
    api.always[(HIST, "S1")] = 404
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    assert db.execute("SELECT markets_done FROM series").fetchone()[0] == 1
    assert not any("Kalshi 404" in line for line in logged(capsys)) and 60 not in sleeps


def test_a_series_that_fails_midway_keeps_its_first_pages_and_is_listed_again(db, api, k, capsys, sleeps):
    add_series(db, "S1")
    api.hist["S1"] = [mkt("S1-A"), mkt("S1-B"), mkt("S1-C")]
    # the first page arrives, the second is refused three times (tries=3)
    api.queue((HIST, "S1"), Resp(body={"markets": [mkt("S1-A"), mkt("S1-B")], "cursor": "2"}), 503, 503, 503)
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    assert db.execute("SELECT COUNT(*) FROM markets").fetchone()[0] == 2
    assert db.execute("SELECT markets_done FROM series").fetchone()[0] == 0
    assert any(line.startswith("markets[hist]: S1: Kalshi 503 on /historical/markets") for line in logged(capsys))
    assert 60 in sleeps and [5.0, 15.0] == [s for s in sleeps if s in (5.0, 15.0)]   # KalshiHTTP's backoff, then a pause
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    assert db.execute("SELECT COUNT(*), COUNT(DISTINCT ticker) FROM markets").fetchone() == (3, 3)
    assert db.execute("SELECT markets_done FROM series").fetchone()[0] == 1


def test_the_listing_phase_gives_up_after_five_refusals_in_a_row(db, api, k, capsys, sleeps):
    add_series(db, *[f"S{i}" for i in range(1, 7)])
    api.always[HIST] = 503
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    asked = sorted({p["series_ticker"] for _, p in api.calls})
    assert asked == ["S1", "S2", "S3", "S4", "S5"] and len(api.calls) == 5 * 3      # tries=3 per series
    assert sleeps.count(60) == 4
    lines = logged(capsys)
    assert lines[-1] == "markets[hist]: the endpoint keeps refusing: stopping this phase, the rest waits for the next run"
    assert db.execute("SELECT COUNT(*) FROM series WHERE markets_done=0").fetchone()[0] == 6


def test_one_good_answer_resets_the_refusal_count(db, api, k, capsys):
    add_series(db, *[f"S{i:02d}" for i in range(1, 11)])
    for i in (1, 2, 3, 4, 6, 7, 8, 9):
        api.always[(HIST, f"S{i:02d}")] = 503
    api.hist = {"S05": [mkt("S05-A")], "S10": [mkt("S10-A")]}
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    assert not any("keeps refusing" in line for line in logged(capsys))
    assert {r[0] for r in db.execute("SELECT ticker FROM series WHERE markets_done=1")} == {"S05", "S10"}


def test_recent_listing_uses_the_live_endpoint_and_its_own_bit(db, api, k, capsys):
    add_series(db, "S1", done=1)                     # archive already listed
    api.recent["S1"] = [mkt("S1-R")]
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "recent")
    assert api.calls[0][0] == "/markets" and api.calls[0][1]["status"] == "settled"
    assert db.execute("SELECT src FROM markets").fetchone()[0] == "recent"
    assert db.execute("SELECT markets_done FROM series").fetchone()[0] == 3
    assert logged(capsys)[0] == "markets[recent]: 1 series to list"


def test_a_rate_limit_is_waited_out_and_slows_the_pace(db, api, capsys, sleeps):
    k = KalshiHTTP(min_interval=0.2, base=BASE, client=api)
    add_series(db, "S1")
    api.hist["S1"] = [mkt("S1-A")]
    api.queue((HIST, "S1"), Resp(429, headers={"Retry-After": "7"}), 429)
    kd.phase_markets(db, k, ["Economics"], 10 ** 6, "hist")
    assert 7.0 in sleeps and 15.0 in sleeps          # the server's Retry-After, then KalshiHTTP's own backoff
    assert k.rate_limited == 2 and k.min_interval == pytest.approx((0.2 * 1.5 + .05) * 1.5 + .05)
    assert db.execute("SELECT markets_done FROM series").fetchone()[0] == 1
    assert logged(capsys)[-1].endswith(f"3 requests, 2 rate limits, interval {k.min_interval:.2f}s")


# ---------------------------------------------------------------------------------------------------------------
# schedule backfill
# ---------------------------------------------------------------------------------------------------------------

def test_backfill_fills_the_schedule_of_markets_that_matter(db, api, k, capsys):
    put(db, "M1", series="B1", done=1, early=None)
    put(db, "M2", series="B1", done=1, early=None)              # no longer in the archive
    put(db, "M3", series="B2", done=0, early=None, volume=10)   # neither fetched nor big: left alone
    put(db, "M4", series="B3", done=0, early=None, volume=500)  # big enough for the census
    put(db, "M5", series="B4", done=1, early=None, src="recent")
    api.hist = {"B1": [mkt("M1", expected_expiration_time="2025-02-01T00:00:00Z", can_close_early=True)],
                "B3": [mkt("M4", expected_expiration_time="", expiration_time="2025-03-01T00:00:00Z", can_close_early=False)]}
    kd.phase_backfill(db, k, ["Economics"], 100.0)
    assert sorted({p["series_ticker"] for _, p in api.calls}) == ["B1", "B3"]
    got = dict(((t, (e, x)) for t, e, x in db.execute("SELECT ticker, early, exp_ts FROM markets")))
    assert got["M1"] == (1, kd.ts("2025-02-01T00:00:00Z")) and got["M4"] == (0, kd.ts("2025-03-01T00:00:00Z"))
    assert got["M2"] == (-1, None) and got["M3"] == (None, None) and got["M5"] == (None, None)
    assert logged(capsys) == ["backfill: scheduled end dates for 2 series", "backfill: 0/2 series; 1 requests, 0 rate limits",
                              "backfill: done"]
    api.calls.clear()
    kd.phase_backfill(db, k, ["Economics"], 100.0)             # nothing left: no request, no log
    assert api.calls == [] and logged(capsys) == []


def test_backfill_gives_up_after_five_failures(db, api, k, capsys, sleeps):
    for i in range(6):
        put(db, f"M{i}", series=f"B{i}", done=1, early=None)
    api.always[HIST] = 503
    kd.phase_backfill(db, k, ["Economics"], 100.0)
    assert sorted({p["series_ticker"] for _, p in api.calls}) == ["B0", "B1", "B2", "B3", "B4"]
    assert sleeps.count(60) == 4
    lines = logged(capsys)
    assert lines[-1] == "backfill: done" and sum("Kalshi 503" in line for line in lines) == 5


def test_backfill_does_not_write_off_a_series_it_could_not_read(db, api, k):
    put(db, "M1", series="B1", done=1, early=None)
    api.always[(HIST, "B1")] = 503
    kd.phase_backfill(db, k, ["Economics"], 100.0)
    assert db.execute("SELECT early FROM markets WHERE ticker='M1'").fetchone()[0] is None


# ---------------------------------------------------------------------------------------------------------------
# daily bars
# ---------------------------------------------------------------------------------------------------------------

def test_bars_are_fetched_in_the_fixed_random_order(db, api, k, capsys):
    tickers = [f"E-{i}" for i in range(8)]
    for t in tickers:
        put(db, t)
        api.candles[t] = [cbar(O + DAY), cbar(O + 2 * DAY)]
    kd.phase_candles(db, k, ["Economics"], 1.0, 10 ** 9, 400)
    asked = [re.fullmatch(r"/historical/markets/(.+)/candlesticks", p).group(1) for p in api.paths()]
    assert asked == sorted(tickers, key=kd.shuffle_key)
    assert db.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 16
    assert {done_of(db, t) for t in tickers} == {1}
    lines = logged(capsys)
    assert lines[0] == "candles (random order): categories with work: ['Economics']"
    assert lines[1] == "candles: 8 markets with bars; 8 requests, 0 rate limits, interval 0.00s"
    assert lines[-1] == "candles: finished this pass (8 markets)"


def test_census_pass_goes_biggest_first_above_its_volume(db, api, k, capsys):
    for i, v in enumerate([50, 900, 10, 400, 5000]):
        put(db, f"E-{i}", volume=v)
        api.candles[f"E-{i}"] = [cbar(O + DAY)]
    kd.phase_candles(db, k, ["Economics"], 100.0, 10 ** 9, 400, biggest_first=True)
    assert api.paths() == [cpath("E-4"), cpath("E-1"), cpath("E-3")]
    assert done_of(db, "E-0") == 0 and done_of(db, "E-2") == 0
    assert logged(capsys)[0] == "candles (census, volume >= 100): categories with work: ['Economics']"


def test_the_bar_request_window(db, api, k):
    put(db, "A", open_ts=O, close_ts=O + 10 * DAY)
    put(db, "B", open_ts=O, close_ts=O + 10 * DAY, src="recent", series="SER")
    api.candles = {"A": [], "B": []}
    kd.phase_candles(db, k, ["Economics"], 1.0, 10 ** 9, 3)
    by = {p: q for p, q in api.calls}
    assert by[cpath("A")] == {"start_ts": O + 7 * DAY, "end_ts": O + 11 * DAY, "period_interval": 1440}
    assert by["/series/SER/markets/B/candlesticks"]["start_ts"] == O + 7 * DAY
    api.calls.clear()
    db.execute("UPDATE markets SET candles_done=0")
    kd.phase_candles(db, k, ["Economics"], 1.0, 10 ** 9, 400)
    assert api.calls[0][1]["start_ts"] == O                     # never before the market opened


def test_final_states_no_bars_bad_dates_and_refusals(db, api, k, capsys):
    put(db, "EMPTY")
    put(db, "NOOPEN", open_ts=None)
    put(db, "BACKWARDS", open_ts=O + 5 * DAY, close_ts=O + 5 * DAY)
    put(db, "GONE")                                  # 404
    put(db, "BAD")                                   # 400
    put(db, "NULLBODY")
    put(db, "NOKEY")
    api.candles = {"EMPTY": []}
    api.always[cpath("BAD")] = 400
    api.always[cpath("NULLBODY")] = Resp(body={"candlesticks": None})
    api.always[cpath("NOKEY")] = Resp(body={"something": "else"})
    kd.phase_candles(db, k, ["Economics"], 1.0, 10 ** 9, 400)
    assert {t: done_of(db, t) for t in ("EMPTY", "NOOPEN", "BACKWARDS", "GONE", "BAD", "NULLBODY", "NOKEY")} == \
        {"EMPTY": 2, "NOOPEN": 3, "BACKWARDS": 3, "GONE": 4, "BAD": 4, "NULLBODY": 2, "NOKEY": 2}
    assert cpath("NOOPEN") not in api.paths() and cpath("BACKWARDS") not in api.paths()
    lines = logged(capsys)
    assert any(line.startswith("candles: BAD: Kalshi 400 on /historical/markets/BAD/candlesticks") for line in lines)
    assert not any("GONE" in line for line in lines)                # a 404 is routine: not logged
    assert db.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 0


def test_rate_limits_and_network_trouble_leave_the_market_to_do(db, api, k, capsys, sleeps):
    put(db, "LIMITED")
    api.always[cpath("LIMITED")] = 429
    kd.phase_candles(db, k, ["Economics"], 1.0, 1, 400)
    assert done_of(db, "LIMITED") == 0 and k.rate_limited == 6 and k.min_interval > 0
    assert any(line.startswith("candles: LIMITED: Kalshi 429") for line in logged(capsys))

    db.execute("UPDATE markets SET candles_done=1")
    put(db, "OFFLINE")
    api.always[cpath("OFFLINE")] = ConnectionError("reset by peer")
    sleeps.clear()
    kd.phase_candles(db, k, ["Economics"], 1.0, 1, 400)
    assert done_of(db, "OFFLINE") == 0
    assert "candles: OFFLINE: ConnectionError" in logged(capsys) and sleeps[-1] == 10

    db.execute("UPDATE markets SET candles_done=1")
    put(db, "LISTBODY")                              # a malformed answer: a JSON list instead of an object
    api.always[cpath("LISTBODY")] = Resp(body=[1, 2])
    kd.phase_candles(db, k, ["Economics"], 1.0, 1, 400)
    assert done_of(db, "LISTBODY") == 0 and "candles: LISTBODY: AttributeError" in logged(capsys)


def test_a_rate_limited_bar_request_is_retried_and_the_pace_is_earned_back(db, api, capsys, sleeps):
    k = KalshiHTTP(min_interval=0.2, base=BASE, client=api)
    tickers = [f"E-{i:02d}" for i in range(41)]
    for t in tickers:
        put(db, t)
        api.candles[t] = [cbar(O + DAY)]
    first = sorted(tickers, key=kd.shuffle_key)[0]
    api.queue(cpath(first), Resp(429, headers={"Retry-After": "2"}))
    kd.phase_candles(db, k, ["Economics"], 1.0, 10 ** 9, 400)
    assert {done_of(db, t) for t in tickers} == {1} and 2.0 in sleeps
    # 0.2 -> 0.35 after the refusal, then 40 answers in a row earn back 10%
    assert k.rate_limited == 1 and k.min_interval == pytest.approx(0.35 * 0.9)


def test_round_robin_across_categories_and_a_soft_market_cap(db, api, k, capsys):
    for cat in ("Economics", "Politics"):
        for i in range(50):
            t = f"{cat[0]}-{i}"
            put(db, t, category=cat)
            api.candles[t] = []
    put(db, "TINY", category="Science", volume=0.5)            # below min_volume: no work in that category
    kd.phase_candles(db, k, ["Economics", "Politics", "Science"], 1.0, 50, 400)
    cats = [p.split("/")[3][0] for p in api.paths()]
    assert cats == ["E"] * 40 + ["P"] * 40           # 40 at a time per category; the cap is checked between rounds
    lines = logged(capsys)
    assert lines[0] == "candles (random order): categories with work: ['Economics', 'Politics']"
    assert lines[-1] == "candles: finished this pass (80 markets)"
    kd.phase_candles(db, k, ["Economics", "Politics"], 1.0, 10 ** 9, 400)
    assert len(api.calls) == 100 and done_of(db, "TINY") == 0


def test_bars_resume_without_refetching_or_duplicating(db, api, k):
    for i in range(5):
        put(db, f"E-{i}")
        api.candles[f"E-{i}"] = [cbar(O + DAY), cbar(O + 2 * DAY)]
    kd.phase_candles(db, k, ["Economics"], 1.0, 10 ** 9, 400)
    api.calls.clear()
    kd.phase_candles(db, k, ["Economics"], 1.0, 10 ** 9, 400)
    assert api.calls == []
    db.execute("UPDATE markets SET candles_done=0")                # asked again: the bars do not double
    kd.phase_candles(db, k, ["Economics"], 1.0, 10 ** 9, 400)
    assert db.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 10


def test_an_interrupted_pass_resumes_from_its_last_commit(tmp_path, api):
    """Ctrl-C (or the machine going down) in the middle of a batch: what was committed stays, the rest is fetched
    on the next run, and no bar is stored twice."""
    path = tmp_path / "int.db"
    db = sqlite3.connect(str(path))
    db.executescript(kd.SCHEMA)
    tickers = [f"E-{i:03d}" for i in range(100)]
    for t in tickers:
        put(db, t)
        api.candles[t] = [cbar(O + DAY), cbar(O + 2 * DAY)]

    class Interrupting:
        n = 0

        def get(self, url, params=None):
            self.n += 1
            if self.n == 50:
                raise KeyboardInterrupt
            return api.get(url, params)

    with pytest.raises(KeyboardInterrupt):
        kd.phase_candles(db, KalshiHTTP(min_interval=0, base=BASE, client=Interrupting()), ["Economics"], 1.0, 10 ** 9, 400)
    db.close()                                       # without a commit: the half-done batch is gone
    db = sqlite3.connect(str(path))
    assert db.execute("SELECT COUNT(*) FROM markets WHERE candles_done=1").fetchone()[0] == 40
    assert db.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 80
    api.calls.clear()
    kd.phase_candles(db, KalshiHTTP(min_interval=0, base=BASE, client=api), ["Economics"], 1.0, 10 ** 9, 400)
    assert len(api.calls) == 60
    assert db.execute("SELECT COUNT(*), COUNT(DISTINCT ticker || ':' || ts) FROM candles").fetchone() == (200, 200)
    assert db.execute("SELECT COUNT(*) FROM markets WHERE candles_done<>1").fetchone()[0] == 0
    db.close()


def test_a_failing_market_waits_for_the_next_run(db, api, k):
    for t in ("OK-1", "OK-2", "DOWN"):
        put(db, t)
        api.candles[t] = [cbar(O + DAY)]
    api.always[cpath("DOWN")] = 503
    kd.phase_candles(db, k, ["Economics"], 1.0, 30, 400)
    assert api.paths().count(cpath("DOWN")) == 6       # one k.get, its 6 tries
    assert done_of(db, "OK-1") == 1 and done_of(db, "OK-2") == 1


def test_odd_tickers_are_encoded_once(db, api, k):
    put(db, "GPT%-23DEC31")
    api.candles["GPT%-23DEC31"] = [cbar(O + DAY)]
    kd.phase_candles(db, k, ["Economics"], 1.0, 10 ** 9, 400)
    assert api.urls == [BASE + "/historical/markets/GPT%25-23DEC31/candlesticks"]
    assert done_of(db, "GPT%-23DEC31") == 1


# ---------------------------------------------------------------------------------------------------------------
# main(): the whole run
# ---------------------------------------------------------------------------------------------------------------

@pytest.fixture
def run(monkeypatch, api):
    """Runs main() with these arguments against the fake exchange; returns the KalshiHTTP it used."""
    made = []

    def factory(min_interval):
        made.append(KalshiHTTP(min_interval=min_interval, base=BASE, client=api))
        return made[-1]

    monkeypatch.setattr(kd, "KalshiHTTP", factory)

    def go(*argv):
        monkeypatch.setattr(sys, "argv", ["kalshi_download.py", *map(str, argv)])
        kd.main()
        return made[-1]
    return go


def test_a_full_run_and_a_restart(tmp_path, api, run, capsys):
    path = tmp_path / "full.db"
    api.series = {"Economics": [{"ticker": "S1", "fee_multiplier": "1"}], "Politics": [{"ticker": "P1"}]}
    api.hist = {"S1": [mkt("S1-A"), mkt("S1-B", result="no"), mkt("S1-C", result="scalar"), mkt("S1-D")]}
    api.always[(HIST, "P1")] = 404
    api.recent = {"P1": [mkt("P1-A")]}
    api.candles = {"S1-A": [cbar(O + DAY), cbar(O + 2 * DAY)], "S1-B": [], "P1-A": [cbar(O + DAY)]}
    k = run("--db", path, "--categories", "Economics, Politics,")
    assert k.min_interval >= 0.6                     # the live endpoint is paced slower
    db = sqlite3.connect(str(path))
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert dict(db.execute("SELECT ticker, markets_done FROM series")) == {"S1": 3, "P1": 3}
    assert dict(db.execute("SELECT ticker, candles_done FROM markets")) == {"S1-A": 1, "S1-B": 2, "S1-D": 4, "P1-A": 1}
    assert db.execute("SELECT src FROM markets WHERE ticker='P1-A'").fetchone()[0] == "recent"
    assert "/series/P1/markets/P1-A/candlesticks" in api.paths()
    assert db.execute("SELECT COUNT(*) FROM candles").fetchone()[0] == 3
    before = db.execute("SELECT (SELECT COUNT(*) FROM markets), (SELECT COUNT(*) FROM candles)").fetchone()
    db.close()
    lines = logged(capsys)
    assert "series: Economics: 1" in lines and "markets[recent]: 2 series to list" in lines
    api.calls.clear()
    run("--db", path, "--categories", "Economics,Politics")             # a restart has nothing left to ask
    assert api.calls == []
    db = sqlite3.connect(str(path))
    assert db.execute("SELECT (SELECT COUNT(*) FROM markets), (SELECT COUNT(*) FROM candles)").fetchone() == before
    db.close()
    os.remove(path)                                  # main closed its connection (Windows refuses to delete an open file)


def spy_on_candles(monkeypatch):
    calls, real = [], kd.phase_candles

    def spy(db, k, categories, min_volume, max_markets, max_days, biggest_first=False):
        calls.append((list(categories), min_volume, max_markets, biggest_first))
        return real(db, k, categories, min_volume, max_markets, max_days, biggest_first)
    monkeypatch.setattr(kd, "phase_candles", spy)
    return calls


def test_first_pass_then_census_and_a_restart_skips_the_first_pass(tmp_path, api, run, monkeypatch):
    path = tmp_path / "fp.db"
    api.page = 1000
    api.series = {"Economics": [{"ticker": "E"}]}
    api.hist = {"E": [mkt(f"E-{v:03d}", volume=v) for v in range(1, 101)]}
    api.candles = {f"E-{v:03d}": [cbar(O + DAY)] for v in range(1, 101)}
    calls = spy_on_candles(monkeypatch)
    args = ("--db", path, "--categories", "Economics", "--first-pass", 50, "--census-volume", 90, "--census-max", 20,
            "--max-markets", 0)
    run(*args)
    assert calls[0] == (["Economics"], 1.0, 50, False)                  # the random first pass
    cen = calls[1]
    assert cen[0] == ["Economics"] and cen[1] == 90.0 and cen[3] is True and 9 <= cen[2] <= 20
    assert calls[2:] == [(["Economics"], 1.0, 0, False)] * 2            # the later passes, capped at 0 here
    db = sqlite3.connect(str(path))
    rnds = sorted(r[0] for r in db.execute("SELECT rnd FROM markets"))
    lowest = {r[0] for r in db.execute("SELECT ticker FROM markets ORDER BY rnd LIMIT 80")}
    assert {r[0] for r in db.execute("SELECT ticker FROM markets WHERE candles_done=1 AND rnd<=?", (rnds[79],))} == lowest
    assert db.execute("SELECT COUNT(*) FROM markets WHERE volume>=90 AND candles_done=0").fetchone()[0] == 0
    assert kd.frontier(db, "Economics", 1.0) > rnds[79]
    db.close()
    calls.clear()
    api.calls.clear()
    run(*args)
    assert calls[0] == (["Economics"], 90.0, 9, True)                   # no first pass again, only the census check
    assert not api.paths("/historical/markets/")


def test_census_can_be_turned_off(tmp_path, api, run, monkeypatch):
    api.series = {"Economics": [{"ticker": "E"}]}
    api.hist = {"E": [mkt("E-1", volume=10 ** 6)]}
    api.candles = {"E-1": []}
    calls = spy_on_candles(monkeypatch)
    run("--db", tmp_path / "c.db", "--categories", "Economics", "--census-volume", 0)
    assert not any(c[3] for c in calls)


def test_census_stops_once_it_has_enough(tmp_path, api, run, monkeypatch):
    api.series = {"Economics": [{"ticker": "E"}]}
    api.hist = {"E": [mkt("E-1", volume=10 ** 6)]}
    api.candles = {"E-1": []}
    calls = spy_on_candles(monkeypatch)
    run("--db", tmp_path / "c.db", "--categories", "Economics", "--census-volume", 100, "--census-max", 1)
    assert not any(c[3] for c in calls)              # the first pass already attempted the one big market


def test_single_phases_touch_only_their_endpoints(tmp_path, api, run):
    path = tmp_path / "p.db"
    api.series = {"Economics": [{"ticker": "E"}]}
    api.hist = {"E": [mkt("E-1")]}
    api.candles = {"E-1": [cbar(O + DAY)]}
    run("--db", path, "--categories", "Economics", "--phase", "series")
    assert api.paths() == ["/series"]
    api.calls.clear()
    run("--db", path, "--categories", "Economics", "--phase", "markets")
    assert api.paths() == [HIST]
    api.calls.clear()
    k = run("--db", path, "--categories", "Economics", "--phase", "candles", "--interval", 0.05)
    assert api.paths() == [cpath("E-1")] and k.min_interval == 0.05
    api.calls.clear()
    k = run("--db", path, "--categories", "Economics", "--phase", "recent")
    assert api.paths() == ["/markets"] and k.min_interval == 0.6


def test_an_old_database_is_migrated(tmp_path, api, run):
    path = tmp_path / "old.db"
    db = sqlite3.connect(str(path))
    db.execute("CREATE TABLE series (ticker TEXT PRIMARY KEY, category TEXT, title TEXT, fee_type TEXT, fee_multiplier REAL, "
               "frequency TEXT, tags TEXT, markets_done INTEGER DEFAULT 0)")
    db.execute("CREATE TABLE markets (ticker TEXT PRIMARY KEY, series TEXT, event TEXT, category TEXT, title TEXT, sub TEXT, "
               "open_ts INTEGER, close_ts INTEGER, result TEXT, settle REAL, volume REAL, open_interest REAL, "
               "last_price REAL, strike_type TEXT, floor_strike REAL, cap_strike REAL, src TEXT, candles_done INTEGER DEFAULT 0)")
    db.execute("INSERT INTO series (ticker, category) VALUES ('E', 'Economics')")
    db.executemany("INSERT INTO markets (ticker, category, volume) VALUES (?, 'Economics', 5)", [("OLD-1",), ("OLD-2",)])
    db.commit()
    db.close()
    run("--db", path, "--categories", "Economics", "--phase", "series")
    assert api.calls == []
    db = sqlite3.connect(str(path))
    cols = {r[1] for r in db.execute("PRAGMA table_info(markets)")}
    assert {"rnd", "exp_ts", "early"} <= cols
    assert dict(db.execute("SELECT ticker, rnd FROM markets")) == {"OLD-1": kd.shuffle_key("OLD-1"), "OLD-2": kd.shuffle_key("OLD-2")}
    assert db.execute("SELECT 1 FROM sqlite_master WHERE type='index' AND name='markets_rnd'").fetchone()
    db.close()


def test_running_the_file_as_a_script(tmp_path, api, monkeypatch):
    """`python research/kalshi_download.py --phase series`: the default categories leave Sports out."""
    import src.kalshi_http as kh
    monkeypatch.setattr(kh, "KalshiHTTP", lambda min_interval: KalshiHTTP(min_interval=0, base=BASE, client=api))
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sys, "argv", ["kalshi_download.py", "--db", str(tmp_path / "sub" / "s.db"), "--phase", "series"])
    runpy.run_path(str(ROOT / "research" / "kalshi_download.py"), run_name="__main__")
    asked = [p["category"] for _, p in api.calls]
    assert asked == [c for c in kd.CATEGORIES if c != "Sports"] and (tmp_path / "sub" / "s.db").exists()


def test_with_sports_adds_sports_last(tmp_path, api, monkeypatch):
    """`--with-sports`: the default categories, then Sports (listed last, so the others keep their place)."""
    import src.kalshi_http as kh
    monkeypatch.setattr(kh, "KalshiHTTP", lambda min_interval: KalshiHTTP(min_interval=0, base=BASE, client=api))
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(sys, "argv", ["kalshi_download.py", "--db", str(tmp_path / "s.db"), "--phase", "series", "--with-sports"])
    runpy.run_path(str(ROOT / "research" / "kalshi_download.py"), run_name="__main__")
    asked = [p["category"] for _, p in api.calls]
    assert asked == [c for c in kd.CATEGORIES if c != "Sports"] + ["Sports"]


# ---------------------------------------------------------------------------------------------------------------
# panel.py on a hand-built database
# ---------------------------------------------------------------------------------------------------------------

CANDLE_COLS = ("ticker", "ts", "bid", "ask", "bid_hi", "bid_lo", "ask_hi", "ask_lo", "px", "px_hi", "px_lo", "vol", "oi",
               "bid_op", "ask_op", "px_mean")


def simple_bar(tk, t, bid, ask):
    mid = (bid + ask) / 2
    return (tk, t, bid, ask, bid + .01, bid - .01, ask + .01, ask - .01, mid, mid + .01, mid - .01, 10.0, 5.0, bid - .01,
            ask + .01, mid)


# EV-T10: four bars, chosen so that each trade-through rule is decided by one number
#            bid   ask   bid_hi bid_lo ask_hi ask_lo px   px_hi px_lo  vol  oi  bid_op ask_op px_mean
T10 = [(.40, .44, .41, .39, .45, .43, .42, .43, .41, 10, 5, .39, .45, .42),
       (.42, .46, .43, .41, .47, .45, .44, .45, .41, 10, 5, .41, .45, .44),
       (.38, .42, .42, .37, .46, .40, .40, .41, .39, 10, 5, .41, .45, .40),
       (.50, .54, .52, .37, .56, .43, .52, .53, .38, 10, 5, .47, .51, .52)]
PX_CLOSE = panel.SPLIT_TS + 10 * DAY


def hand_db(path):
    db = sqlite3.connect(str(path))
    db.executescript(kd.SCHEMA)
    db.execute("INSERT INTO series (ticker, category, fee_type, fee_multiplier) VALUES ('EV','Economics','quadratic_with_maker_fees',0.5)")
    db.execute("INSERT INTO series (ticker, category, fee_type, fee_multiplier) VALUES ('PX','Politics','quadratic',NULL)")

    def market(tk, series, event, cat, close, result, volume, done, rnd, early, floor=None):
        db.execute("INSERT INTO markets (ticker, series, event, category, open_ts, close_ts, result, volume, strike_type, "
                   "floor_strike, src, candles_done, rnd, exp_ts, early) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (tk, series, event, cat, close - 5 * DAY, close, result, volume, "greater" if floor else None, floor,
                    "hist", done, rnd, close, early))
    close = O + 5 * DAY
    market("EV-T10", "EV", "EV", "Economics", close, "yes", 100, 1, 100, 0, floor=10)
    market("EV-T20", "EV", "EV", "Economics", close, "no", 100, 1, 200, 0, floor=20)
    market("EV-T30", "EV", "EV", "Economics", close, "no", 5, 2, 300, 0, floor=30)    # listed, attempted, never quoted
    market("ZZ-1", "EV", "ZZ", "Economics", close, "no", 0.5, 0, 150, 0)                # not fetched yet, but tiny
    market("PX-1", "PX", "PX", "Politics", PX_CLOSE, "no", 100, 1, 10, None)            # schedule not downloaded
    market("PX-2", "PX", "PX", "Politics", PX_CLOSE, "yes", 100, 1, 20, None)
    rows = [("EV-T10", O + (i + 1) * DAY, *b) for i, b in enumerate(T10)]
    rows += [simple_bar("EV-T20", O + (i + 1) * DAY, b, a) for i, (b, a) in enumerate([(.20, .24), (.22, .26), (.18, .22), (.30, .34)])]
    rows += [simple_bar("PX-1", t, b, a) for t, b, a in [(PX_CLOSE - 2 * DAY, .60, .64), (PX_CLOSE - DAY, .70, .74),
                                                        (PX_CLOSE, .65, .69), (PX_CLOSE + 2 * DAY, .50, .60)]]
    rows += [simple_bar("PX-2", PX_CLOSE - DAY, .50, .54)]
    db.executemany(f"INSERT INTO candles ({','.join(CANDLE_COLS)}) VALUES ({','.join('?' * 16)})", rows)
    db.commit()
    return db


@pytest.fixture
def hand(tmp_path):
    path = tmp_path / "hand.db"
    hand_db(path).close()
    return path


def bars_of(df, tk):
    return df[df["ticker"] == tk].sort_values("ts").reset_index(drop=True)


def test_trade_through_flags_on_a_hand_built_market(hand):
    a = bars_of(panel.load(hand), "EV-T10")
    assert len(a) == 4
    # bar 0 (bid .40, ask .44): next bar's ask low .45 and trade low .41 stay above the bid -> no fill in 1 bar;
    # within 3 bars the ask comes down to exactly .40 (counts, to the tolerance). For NO the bid high .43 stays under
    # the ask but a trade printed at .45, above it -> filled.
    # bar 1 (bid .42, ask .46): the ask drops to .40 next bar -> YES fills; nothing reaches .46 next bar, but bar 3's
    # bid high .52 does.
    # bar 2 (bid .38, ask .42): bar 3's ask low .43 is above the bid and its trade low is AT the bid, .38: a print at
    # the price does not prove a resting bid filled -> no YES fill. Bar 3's bid high .52 >= .42 -> NO fills.
    # bar 3: nothing after it.
    assert list(a["f1_yes"]) == [False, True, False, False]
    assert list(a["f3_yes"]) == [True, True, False, False]
    assert list(a["f1_no"]) == [True, False, True, False]
    assert list(a["f3_no"]) == [True, True, True, False]


def test_takers_buy_at_the_next_bars_open(hand):
    a = bars_of(panel.load(hand), "EV-T10")
    assert list(a["n_ask_op"].iloc[:3]) == pytest.approx([.45, .45, .51])
    assert list(a["n_bid_op"].iloc[:3]) == pytest.approx([.41, .41, .47])
    assert list(a["n_ok"]) == [True, True, True, False]
    mult = 0.5
    c = .45 + .07 * mult * .45 * .55
    assert a.loc[0, "r_yes_tk"] == pytest.approx((1 - c) / c, rel=1e-5)          # resolved YES
    assert a.loc[0, "r_no_tk"] == pytest.approx(-1.0)
    c = .51 + .07 * mult * .51 * .49
    assert a.loc[2, "r_yes_tk"] == pytest.approx((1 - c) / c, rel=1e-5)
    assert np.isnan(a.loc[3, "r_yes_tk"]) and np.isnan(a.loc[3, "r_no_tk"])
    # makers rest at this bar's bid, pay the maker fee (this series has one), and count only when filled
    c = .40 + .0175 * mult * .40 * .60
    assert a.loc[0, "r_yes_mk"] == pytest.approx((1 - c) / c, rel=1e-5)
    assert np.isnan(a.loc[2, "r_yes_mk"]) and a.loc[0, "r_no_mk"] == pytest.approx(-1.0)
    # a series without maker fees: the NO maker at 1 - ask pays nothing on top
    p = bars_of(panel.load(hand), "PX-1")
    assert not p["maker_fee"].any() and p["mult"].eq(1.0).all()
    assert p.loc[0, "f3_no"] and p.loc[0, "r_no_mk"] == pytest.approx(.64 / .36, rel=1e-5)


def test_signals_event_structure_and_ladder(hand):
    df = panel.load(hand)
    a, b = bars_of(df, "EV-T10"), bars_of(df, "EV-T20")
    assert a.loc[0, "mid"] == pytest.approx(.42) and a.loc[0, "spread"] == pytest.approx(.04)
    assert a.loc[1, "mom1"] == pytest.approx(.02, abs=1e-6) and np.isnan(a.loc[0, "mom1"])
    assert list(a["cumvol"]) == [10, 20, 30, 40] and a.loc[0, "dte"] == pytest.approx(4.0) and a.loc[0, "age"] == pytest.approx(1.0)
    assert a.loc[0, "ev_n"] == 2 and a.loc[0, "ev_sum"] == pytest.approx(.64) and a.loc[0, "ev_max"] == pytest.approx(.42)
    assert a["ev_fav"].all() and not b["ev_fav"].any()
    assert a["ev_total"].eq(3).all()                 # the never-quoted third market still counts as listed
    # the next rung up (floor 20) at the same bar, and the pair trade: YES at 10, NO at 20
    assert a.loc[0, "up_bid"] == pytest.approx(.20) and a.loc[0, "up_ask"] == pytest.approx(.24)
    assert np.isnan(a.loc[0, "dn_mid"]) and b.loc[0, "dn_mid"] == pytest.approx(.42) and b["up_mid"].isna().all()
    nb = .21                                         # EV-T20's next opening bid
    cost = .45 + (1 - nb) + .07 * .5 * (.45 * .55 + nb * (1 - nb))
    assert a.loc[0, "pair_cost"] == pytest.approx(cost, rel=1e-5)
    assert a.loc[0, "r_pair_tk"] == pytest.approx((2 - cost) / cost, rel=1e-5)
    assert np.isnan(a.loc[3, "r_pair_tk"])


def test_load_trims_and_filters(hand):
    df = panel.load(hand)
    assert set(df["ticker"]) == {"EV-T10", "EV-T20", "PX-1"}    # PX-2 has one bar, under min_bars
    p = bars_of(df, "PX-1")
    assert len(p) == 3 and p["ts"].max() == PX_CLOSE           # the bar two days after the close is dropped
    assert p["oos"].all() and not bars_of(df, "EV-T10")["oos"].any()
    assert not p["sched_known"].any() and bars_of(df, "EV-T10")["sched_known"].all()
    assert set(panel.load(hand, min_bars=1)["ticker"]) == {"EV-T10", "EV-T20", "PX-1", "PX-2"}
    assert set(panel.load(hand, categories=["Politics"])["ticker"]) == {"PX-1"}
    assert panel.load(hand, categories=["Nothing"]).empty


def test_random_sample_stops_at_the_first_unattempted_key(hand):
    assert set(panel.load(hand)["ticker"]) == {"EV-T10", "EV-T20", "PX-1"}     # ZZ-1 is under min_volume
    # counted as part of the sample, ZZ-1 (key 150) has not been fetched: EV-T20 (key 200) is past the frontier
    assert set(panel.load(hand, min_volume=0.1)["ticker"]) == {"EV-T10", "PX-1"}
    assert set(panel.load(hand, sample="all", min_volume=0.1)["ticker"]) == {"EV-T10", "EV-T20", "PX-1"}


def test_liquid_sample_starts_each_market_when_it_qualified(hand):
    liq = panel.load(hand, sample="liquid")          # default level: complete down to max(1.03 * 0.5, 1) = 1 contract
    assert set(liq["ticker"]) == {"EV-T10", "EV-T20", "PX-1"} and len(liq) == 11
    liq = panel.load(hand, sample="liquid", min_cumvol=15)
    a = bars_of(liq, "EV-T10")
    assert list(a["cumvol"]) == [20, 30, 40] and a.loc[0, "f1_yes"]           # execution still looks at the next bar
    assert list(bars_of(liq, "PX-1")["cumvol"]) == [20, 30]
    assert a.loc[0, "ev_n"] == 2 and a.loc[0, "up_bid"] == pytest.approx(.22)  # structure among qualifying bars


def test_liquid_sample_leaves_out_incomplete_categories(hand):
    db = sqlite3.connect(str(hand))
    db.execute("UPDATE markets SET volume=500 WHERE ticker='ZZ-1'")              # a 500-contract market not fetched yet
    db.commit()
    liq = panel.load(hand, sample="liquid", min_cumvol=15)
    assert set(liq["category"]) == {"Politics"}
    assert panel.load(hand, sample="liquid", categories=["Economics"], min_cumvol=15).empty     # nothing qualifies
    db.execute("UPDATE markets SET volume=1000 WHERE ticker LIKE 'EV-%'")       # lifetime says big, bars add up to 40
    db.commit()
    db.close()
    assert panel.load(hand, sample="liquid", categories=["Economics"], min_cumvol=1000).empty


def test_census_floor(hand):
    db = sqlite3.connect(str(hand))
    assert panel.census_floor(db, "Economics") == 0.5 and panel.census_floor(db, "Politics") == 0.0
    db.close()


def test_a_database_from_before_the_shuffle_and_the_schedule(tmp_path):
    path = tmp_path / "old.db"
    db = sqlite3.connect(str(path))
    old = kd.SCHEMA.replace(", rnd INTEGER,\n    exp_ts INTEGER, early INTEGER)", ")")
    assert "rnd INTEGER" not in old
    db.executescript(old)
    db.execute("INSERT INTO markets (ticker, series, event, category, open_ts, close_ts, result, volume, candles_done) "
               "VALUES ('A','S','E','Economics',?,?,'yes',10,1)", (O, O + 5 * DAY))
    db.execute("INSERT INTO markets (ticker, series, event, category, open_ts, close_ts, result, volume, candles_done) "
               "VALUES ('B','S','E','Economics',?,?,'no',10,0)", (O, O + 5 * DAY))
    db.executemany(f"INSERT INTO candles ({','.join(CANDLE_COLS)}) VALUES ({','.join('?' * 16)})",
                   [simple_bar("A", O + DAY, .4, .44), simple_bar("A", O + 2 * DAY, .5, .54)])
    db.commit()
    db.close()
    df = panel.load(path)
    assert len(df) == 2 and not df["sched_known"].any() and df["mult"].eq(1.0).all()


def test_set_split_moves_the_out_of_sample_date(hand, monkeypatch):
    monkeypatch.setattr(panel, "SPLIT_TS", panel.SPLIT_TS)        # restored after the test
    panel.set_split("2025-01-03")
    assert panel.SPLIT_TS == O + 2 * DAY
    assert panel.load(hand)["oos"].all()


def test_describe(hand):
    assert panel.describe(pd.DataFrame()) == "no observations yet"
    text = panel.describe(panel.load(hand)).splitlines()
    assert text[0] == ("3 markets, 2 events, 11 daily bars; closes 2025-01-06 to 2026-04-11; "
                       "1 markets out of sample (closing from 2026-04-01)")
    eco = next(line for line in text if line.strip().startswith("Economics"))
    pol = next(line for line in text if line.strip().startswith("Politics"))
    assert "2 markets" in eco and "resolved yes 50.0%" in eco and "out of sample      0" in eco
    assert "can close early   0%" in eco and "SCHEDULE MISSING" not in eco
    assert "resolved yes  0.0%" in pol and "SCHEDULE MISSING FOR 100%" in pol
    assert not any("liquid census" in line for line in text)
    # the census line, given floors (load() should set them, see the xfail below)
    liq = panel.load(hand, sample="liquid", min_cumvol=15)
    liq.attrs["floors"] = {"Economics": 1500.0, "Politics": 15.0}
    assert panel.describe(liq).splitlines()[1] == ("  liquid census: bars from the day a market had traded at least "
                                                   "1,500 contracts (Economics), 15 contracts (Politics)")


def test_the_liquid_census_floors_reach_describe(hand):
    liq = panel.load(hand, sample="liquid", min_cumvol=15)
    assert liq.attrs.get("floors") == {"Economics": 15.0, "Politics": 15.0}
    assert "liquid census: bars from the day a market had traded at least 15 contracts (" in panel.describe(liq)


def test_running_panel_as_a_script(hand, monkeypatch, capsys):
    """`python research/panel.py` reads the default database; the connection is pointed at the hand-built one."""
    real, seen = sqlite3.connect, []

    def connect(path, *a, **kw):
        seen.append(path)
        return real(str(hand), *a, **kw)
    monkeypatch.setattr(sqlite3, "connect", connect)
    runpy.run_path(str(ROOT / "research" / "panel.py"), run_name="__main__")
    assert seen and all(Path(p) == panel.DB for p in seen)
    assert capsys.readouterr().out.startswith("3 markets, 2 events, 11 daily bars")
