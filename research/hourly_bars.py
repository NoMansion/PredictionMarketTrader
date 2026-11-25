"""Hourly bars for the last hours of the markets a rule bets on (Ideas queue item 10).

The exit study (research/exits.py, report 3.28) works on DAILY bars, so a stop that triggers on a day is sold at
the next day's open. For the last two days of a market that is its one real caveat: much of the move happens in
hours. This fetches 60-minute bid / ask / trade bars for the final `--hours` before each market's close, for the
markets a rule's bets were placed in, into a SEPARATE database (data/kalshi_hourly.db, table candles_1h, the
same columns as candles in data/kalshi_hist.db) so it never competes with the running history download for
the main database's write lock.

Public endpoints only, paced, resumable (a market is fetched once; a passing failure is retried on the next run).

    python research/hourly_bars.py --sample liquid --min-cumvol 45000 --categories Entertainment \
        --rules "NO where YES is at 5-35c|no|mk" --max-markets 400
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from kalshi_download import candle_rows  # noqa: E402
from data_paths import hourly_db  # noqa: E402

HOURLY_DB = hourly_db()                 # data\kalshi_hourly.db, or wherever scripts\move_history.ps1 put it
SCHEMA = """
CREATE TABLE IF NOT EXISTS candles_1h (ticker TEXT, ts INTEGER, bid REAL, ask REAL, bid_hi REAL, bid_lo REAL, ask_hi REAL,
    ask_lo REAL, px REAL, px_hi REAL, px_lo REAL, vol REAL, oi REAL, bid_op REAL, ask_op REAL, px_mean REAL,
    PRIMARY KEY (ticker, ts)) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS hourly_done (ticker TEXT PRIMARY KEY, status INTEGER, start_ts INTEGER, end_ts INTEGER,
    bars INTEGER, fetched_at INTEGER);
"""
# status: 1 bars stored, 2 the exchange had no bars, 3 no usable open / close time, 4 a final 4xx answer


def open_db(path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=60)
    db.executescript(SCHEMA)
    return db


def window(open_ts, close_ts, hours: float) -> tuple[int, int] | None:
    """The last `hours` before the close (never before the open), plus one hour past it for the closing bar."""
    if not open_ts or not close_ts or close_ts <= open_ts:
        return None
    return int(max(open_ts, close_ts - hours * 3600)), int(close_ts + 3600)


def fetch(db: sqlite3.Connection, k, markets, hours: float = 48.0, max_markets: int = 10 ** 9, log=print) -> dict:
    """markets: iterable of (ticker, series, open_ts, close_ts, src). k: anything with .get(path, **params) -> dict
    (src.kalshi_http.KalshiHTTP). Already-done tickers are skipped. Returns counts by status."""
    done = {r[0] for r in db.execute("SELECT ticker FROM hourly_done")}
    counts = {"skipped": 0, 1: 0, 2: 0, 3: 0, 4: 0, "retry": 0}
    n = 0
    for ticker, series, o, cl, src in markets:
        if ticker in done:
            counts["skipped"] += 1
            continue
        if n >= max_markets:
            break
        n += 1
        w = window(o, cl, hours)
        bars = 0
        if w is None:
            status = 3
        else:
            path = (f"/historical/markets/{ticker}/candlesticks" if src == "hist"
                    else f"/series/{series or ''}/markets/{ticker}/candlesticks")
            try:
                cs = k.get(path, start_ts=w[0], end_ts=w[1], period_interval=60).get("candlesticks") or []
                rows = candle_rows(ticker, cs)
                db.executemany("INSERT OR IGNORE INTO candles_1h VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
                bars = len(rows)
                status = 1 if rows else 2
            except Exception as e:  # noqa: BLE001
                code = getattr(e, "status_code", None)
                if code is not None and 400 <= code < 500 and code != 429:
                    status = 4
                else:                                   # throttled or network trouble: try again next run
                    counts["retry"] += 1
                    log(f"hourly: {ticker}: {type(e).__name__} {code or ''}")
                    continue
        db.execute("INSERT OR REPLACE INTO hourly_done VALUES (?,?,?,?,?,?)",
                   (ticker, status, w[0] if w else None, w[1] if w else None, bars, int(time.time())))
        counts[status] += 1
        if n % 50 == 0:
            db.commit()
            log(f"hourly: {n} markets fetched")
    db.commit()
    return counts


def rule_markets(hist_db, cats, sample, min_cumvol, specs) -> list[tuple]:
    """(ticker, series, open_ts, close_ts, src) of every market the rules bet on, in entry order."""
    import panel
    from analyze_rule import find_rule
    from backtest import Panel
    from exits import rule_rows
    from families import Features
    from run_sweep import titles_for

    df = panel.load(hist_db, cats, sample=sample, min_cumvol=min_cumvol)
    print(panel.describe(df))
    if df.empty:
        return []
    p = Panel(df)
    f = Features(p)
    titles = titles_for(df, hist_db)
    tickers: list[str] = []
    for spec in [s for s in specs.split(";") if s.strip()]:
        name, side, entry = (x.strip() for x in spec.split("|"))
        _, mask = find_rule(f, titles, name, side, entry)
        rows = rule_rows(p, mask, side, entry)
        tickers += [t for t in df["ticker"].to_numpy()[rows] if t not in tickers]
    con = sqlite3.connect(f"file:{hist_db}?mode=ro", uri=True, timeout=60)
    info = {}
    for i in range(0, len(tickers), 500):
        part = tickers[i:i + 500]
        q = f"SELECT ticker, series, open_ts, close_ts, src FROM markets WHERE ticker IN ({','.join('?' * len(part))})"
        info.update({r[0]: r for r in con.execute(q, part)})
    con.close()
    return [info[t] for t in tickers if t in info]


def main() -> int:
    import panel
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(panel.DB), help="the history database (read only)")
    ap.add_argument("--out", default=str(HOURLY_DB))
    ap.add_argument("--categories", default="Entertainment")
    ap.add_argument("--sample", default="liquid", choices=["random", "liquid"])
    ap.add_argument("--min-cumvol", type=float, default=None)
    ap.add_argument("--rules", default="NO where YES is at 5-35c|no|mk", help="name|side|entry;...")
    ap.add_argument("--hours", type=float, default=48.0)
    ap.add_argument("--max-markets", type=int, default=400)
    ap.add_argument("--interval", type=float, default=1.0,
                    help="seconds between requests; slower than the history download, which runs beside it")
    args = ap.parse_args()
    from src.kalshi_http import KalshiHTTP
    cats = [c.strip() for c in args.categories.split(",") if c.strip()] or None
    markets = rule_markets(args.db, cats, args.sample, args.min_cumvol, args.rules)
    print(f"{len(markets)} markets in the rules' bets")
    db = open_db(args.out)
    counts = fetch(db, KalshiHTTP(min_interval=args.interval), markets, args.hours, args.max_markets)
    have = db.execute("SELECT COUNT(*), SUM(status=1), SUM(bars) FROM hourly_done").fetchone()
    db.close()
    print(f"this run: {counts}; database: {have[0]} markets done, {have[1] or 0} with bars, {have[2] or 0} hourly bars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
