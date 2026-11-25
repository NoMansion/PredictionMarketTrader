"""Build a local history of settled Kalshi markets for strategy research (data/kalshi_hist.db).

Public endpoints only, paced, resumable: stop it at any point and run it again. Three phases, each skipped once done:

  series   every series (a recurring question such as "CPI year-over-year") in the chosen categories
  markets  every settled market of those series in the archive (/historical/markets, back to 2022)
  candles  daily bid / ask / trade bars for each market from open to close, in a RANDOM order within each
           category (a fixed shuffle: the checksum of the ticker). Random on purpose: taking the biggest markets
           first, as the first version did, selects on lifetime volume, which is only known afterwards and is
           larger for markets where something surprising happened. Backtests use only the random sample.
  recent   markets settled since the archive cutoff (/markets?status=settled) and their bars; last and slowest,
           because that endpoint throttles hard

The data stays on this machine (data/ is not committed): Kalshi's terms do not allow redistributing it.

    python research/kalshi_download.py                       all phases, default categories
    python research/kalshi_download.py --phase candles --min-volume 200 --max-markets 50000
"""
import argparse
import sqlite3
import sys
import time
import zlib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.kalshi_http import KalshiError, KalshiHTTP  # noqa: E402

# In the order they are downloaded: the categories the paper bot trades first, the giant ones last. (Commodities
# moved back on 2026-11-18: 264,000 markets, mostly daily price ranges the bot does not trade.)
CATEGORIES = ["Economics", "Politics", "Companies", "Science and Technology", "Elections", "Health", "World",
              "Commodities", "Financials", "Mentions", "Entertainment", "Crypto", "Social", "Climate and Weather", "Sports"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS series (ticker TEXT PRIMARY KEY, category TEXT, title TEXT, fee_type TEXT, fee_multiplier REAL,
    frequency TEXT, tags TEXT, markets_done INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS markets (ticker TEXT PRIMARY KEY, series TEXT, event TEXT, category TEXT, title TEXT, sub TEXT,
    open_ts INTEGER, close_ts INTEGER, result TEXT, settle REAL, volume REAL, open_interest REAL, last_price REAL,
    strike_type TEXT, floor_strike REAL, cap_strike REAL, src TEXT, candles_done INTEGER DEFAULT 0, rnd INTEGER,
    exp_ts INTEGER, early INTEGER);
CREATE TABLE IF NOT EXISTS refreshed (category TEXT, what TEXT, ts INTEGER, PRIMARY KEY (category, what));
CREATE INDEX IF NOT EXISTS markets_series ON markets (series);
CREATE INDEX IF NOT EXISTS markets_todo ON markets (candles_done, category, volume);
CREATE TABLE IF NOT EXISTS candles (ticker TEXT, ts INTEGER, bid REAL, ask REAL, bid_hi REAL, bid_lo REAL, ask_hi REAL,
    ask_lo REAL, px REAL, px_hi REAL, px_lo REAL, vol REAL, oi REAL, bid_op REAL, ask_op REAL, px_mean REAL,
    PRIMARY KEY (ticker, ts)) WITHOUT ROWID;
"""


def ts(s):
    try:
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp())
    except (ValueError, TypeError):
        return None


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def first(d, *keys):
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return None


def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def phase_series(db, k, categories):
    for cat in categories:
        if db.execute("SELECT 1 FROM series WHERE category=? LIMIT 1", (cat,)).fetchone():
            continue
        rows = k.get("/series", category=cat).get("series") or []
        db.executemany("INSERT OR IGNORE INTO series (ticker, category, title, fee_type, fee_multiplier, frequency, tags) VALUES (?,?,?,?,?,?,?)",
                       [(s["ticker"], cat, s.get("title"), s.get("fee_type"), num(s.get("fee_multiplier")), s.get("frequency"),
                         ",".join(s.get("tags") or [])) for s in rows])
        db.commit()
        log(f"series: {cat}: {len(rows)}")


def shuffle_key(ticker: str) -> int:
    """A fixed pseudo-random number per market: its position in the download order and in the sample."""
    return zlib.crc32(ticker.encode("utf-8"))


def frontier(db, category: str, min_volume: float) -> int:
    """Markets of the category with a shuffle key below this number have all been attempted: they ARE the random
    sample. (2**32 when the whole category is done.) Late listings (phase_refresh) waiting for bars do not count:
    they join the sample as their bars come in, in the same random order."""
    late = {r[1] for r in db.execute("PRAGMA table_info(markets)")} >= {"late"}   # migrate() adds it
    row = db.execute("SELECT MIN(rnd) FROM markets WHERE category=? AND candles_done=0 AND volume>=?"
                     + (" AND COALESCE(late, 0)=0" if late else ""), (category, min_volume)).fetchone()
    return int(row[0]) if row and row[0] is not None else 2 ** 32


def market_row(m, series, category, src):
    return (m["ticker"], series, m.get("event_ticker"), category, m.get("title"), first(m, "yes_sub_title", "subtitle"),
            ts(m.get("open_time")), ts(m.get("close_time")), m.get("result"),
            num(first(m, "settlement_value_dollars", "settlement_value")), num(first(m, "volume_fp", "volume")),
            num(first(m, "open_interest_fp", "open_interest")), num(first(m, "last_price_dollars", "last_price")),
            m.get("strike_type"), num(m.get("floor_strike")), num(m.get("cap_strike")), src, shuffle_key(m["ticker"]),
            *schedule(m))


def schedule(m):
    """(scheduled end, may close early). close_time is rewritten when a market closes early, so for a market that
    can close early the only end date that was known in advance is its expiration. A backtest that measures "days
    to close" from the actual close of such a market knows the event is about to happen."""
    return (ts(first(m, "expected_expiration_time", "expiration_time", "latest_expiration_time")),
            1 if m.get("can_close_early") else 0)


def phase_markets(db, k, categories, max_per_series, which):
    """which = "hist" (the archive) or "recent" (settled since the archive cutoff). markets_done is a bit mask:
    1 = archive listed, 2 = recent listed. The live endpoint behind "recent" throttles hard, so it is paced slower
    and a series that cannot be read now is simply left for the next run."""
    bit = 1 if which == "hist" else 2
    path, extra = ("/historical/markets", {}) if which == "hist" else ("/markets", {"status": "settled"})
    todo = db.execute(f"SELECT ticker, category, COALESCE(late, 0) FROM series WHERE (markets_done & ?) = 0 AND category IN "
                      f"({','.join('?' * len(categories))}) ORDER BY category, ticker", [bit] + categories).fetchall()
    log(f"markets[{which}]: {len(todo)} series to list")
    failures = 0
    for i, (series, cat, late) in enumerate(todo):
        batch, ok = [], True
        try:
            for m in k.pages(path, "markets", tries=3, series_ticker=series, **extra):
                if m.get("result") not in ("yes", "no"):              # scalar or voided markets are left out
                    continue
                batch.append(market_row(m, series, cat, which))
                if len(batch) >= max_per_series:
                    break
        except KalshiError as e:
            ok = e.status_code == 404
            if not ok:
                failures += 1
                log(f"markets[{which}]: {series}: {e}")
                if failures >= 5:
                    log(f"markets[{which}]: the endpoint keeps refusing: stopping this phase, the rest waits for the next run")
                    db.commit()
                    return
                time.sleep(60)
        insert_markets(db, batch, late=1 if late else None)     # a series found by a refresh: its markets are late too
        if ok:
            failures = 0
            db.execute("UPDATE series SET markets_done = markets_done | ? WHERE ticker=?", (bit, series))
        db.commit()
        if i % 200 == 0:
            total = db.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
            log(f"markets[{which}]: {i}/{len(todo)} series, {total} markets so far ({cat} {series}: {len(batch)}); "
                f"{k.requests} requests, {k.rate_limited} rate limits, interval {k.min_interval:.2f}s")


def insert_markets(db, rows, late=None) -> int:
    """INSERT OR IGNORE market_row() tuples; returns how many were new."""
    before = db.total_changes
    db.executemany("INSERT OR IGNORE INTO markets (ticker, series, event, category, title, sub, open_ts, close_ts, result, "
                   "settle, volume, open_interest, last_price, strike_type, floor_strike, cap_strike, src, rnd, exp_ts, early, "
                   "late) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [(*r, late) for r in rows])
    return db.total_changes - before


# The refresh goes category by category in this order (the rules the paper accounts trade first, the big ones last).
REFRESH_ORDER = ["Entertainment", "Climate and Weather", "Politics", "Economics", "Elections", "Science and Technology",
                 "Companies", "Health", "World", "Mentions", "Social", "Commodities", "Financials", "Sports"]
REFRESH_SKIP = {"Crypto"}       # closed for the daily-bar engine (report 3.25); its random pass alone takes weeks
REFRESH_BIG = {"Commodities", "Financials"}     # mostly daily price ranges: hours of bars, so not before a first pass


def relist_series(db, k, cat, every_days, now) -> int:
    """New series of a category since it was last listed (a new show, artist, city): added with late=1."""
    row = db.execute("SELECT ts FROM refreshed WHERE category=? AND what='series'", (cat,)).fetchone()
    if row and row[0] >= now - every_days * 86400:
        return 0
    try:
        rows = k.get("/series", category=cat).get("series") or []
    except KalshiError as e:
        log(f"refresh[series]: {cat}: {e}")
        return 0
    before = db.total_changes
    db.executemany("INSERT OR IGNORE INTO series (ticker, category, title, fee_type, fee_multiplier, frequency, tags, late) "
                   "VALUES (?,?,?,?,?,?,?,1)",
                   [(s["ticker"], cat, s.get("title"), s.get("fee_type"), num(s.get("fee_multiplier")), s.get("frequency"),
                     ",".join(s.get("tags") or [])) for s in rows])
    new = db.total_changes - before
    db.execute("INSERT OR REPLACE INTO refreshed (category, what, ts) VALUES (?, 'series', ?)", (cat, now))
    db.commit()
    log(f"refresh[series]: {cat}: {new} new series")
    return new


def relist_markets(db, k, cat, which, every_days, now, max_per_series) -> int:
    """List again every series of the category whose last `which` listing ("recent": the live endpoint's settled
    markets, which reach back to the archive cutoff, about two months; "hist": the archive) is older than every_days.
    New markets are added with late=1. Returns how many were new."""
    col = "recent_ts" if which == "recent" else "hist_ts"
    path, extra = ("/historical/markets", {}) if which == "hist" else ("/markets", {"status": "settled"})
    todo = [r[0] for r in db.execute(f"SELECT ticker FROM series WHERE category=? AND (markets_done & 1) = 1 AND "
                                     f"({col} IS NULL OR {col} < ?) ORDER BY ticker", (cat, now - every_days * 86400))]
    if not todo:
        return 0
    log(f"refresh[{which}]: {cat}: {len(todo)} series to list again")
    saved = k.min_interval
    if which == "recent":                           # the live endpoint is the touchy one
        k.min_interval = max(k.min_interval, 0.6)
    try:
        return _relist(db, k, cat, which, col, path, extra, todo, now, max_per_series)
    finally:
        if which == "recent":                       # back to the bars' pace
            k.min_interval = saved


def _relist(db, k, cat, which, col, path, extra, todo, now, max_per_series) -> int:
    new = failures = 0
    for i, series in enumerate(todo):
        batch, ok = [], True
        try:
            for m in k.pages(path, "markets", tries=3, series_ticker=series, **extra):
                if m.get("result") not in ("yes", "no"):
                    continue
                batch.append(market_row(m, series, cat, which))
                if len(batch) >= max_per_series:
                    break
        except KalshiError as e:
            ok = e.status_code == 404
            if not ok:
                failures += 1
                log(f"refresh[{which}]: {series}: {e}")
                if failures >= 5:
                    log(f"refresh[{which}]: the endpoint keeps refusing: the rest waits for the next round")
                    db.commit()
                    return new
                time.sleep(60)
        new += insert_markets(db, batch, late=1)
        if ok:
            failures = 0
            db.execute(f"UPDATE series SET {col}=? WHERE ticker=?", (now, series))
        db.commit()
        if i % 200 == 0:
            log(f"refresh[{which}]: {cat}: {i}/{len(todo)} series, {new} new markets so far; {k.requests} requests, "
                f"{k.rate_limited} rate limits")
    log(f"refresh[{which}]: {cat}: {new} new markets")
    return new


def phase_refresh(db, k, categories, refresh_days, max_per_series, max_days, min_volume, hist_days=56, now=None) -> int:
    """Keep the history current. Each series is listed once by phase_markets, so without this a market that settles
    later is never seen (found 2026-11-24: bars ended at the archive cutoff of the first listing, Sep 19, 2026).
    Category by category (REFRESH_ORDER): new series; the live endpoint's settled markets every refresh_days; the
    archive every hist_days (it lags about two months, so this only fills the days between the first listing and its
    cutoff); then bars for every late listing, in the fixed random order. Late listings waiting for bars are left out
    of the census floor and the random frontier (frontier(), panel.py), so a refresh never shrinks a sample: they join
    it as their bars arrive. A category still on its first listing is left to the first pass."""
    now = int(now or time.time())
    order = [c for c in REFRESH_ORDER if c in categories] + [c for c in categories if c not in REFRESH_ORDER]
    did = 0
    for cat in order:
        if cat in REFRESH_SKIP or not db.execute("SELECT 1 FROM series WHERE category=? LIMIT 1", (cat,)).fetchone():
            continue
        if db.execute("SELECT 1 FROM series WHERE category=? AND (markets_done & 1) = 0 AND COALESCE(late, 0)=0 LIMIT 1",
                      (cat,)).fetchone():
            continue
        did += relist_series(db, k, cat, refresh_days, now)
        phase_markets(db, k, [cat], max_per_series, "hist")            # the new series' archive markets (late)
        did += relist_markets(db, k, cat, "recent", refresh_days, now, max_per_series)
        did += relist_markets(db, k, cat, "hist", hist_days, now, max_per_series)
        did += phase_candles(db, k, [cat], min_volume, 10 ** 9, max_days, late_only=True) or 0
    return did


def phase_backfill(db, k, categories, census_volume):
    """Markets listed before the schedule columns existed: read their series again and fill the two columns in.
    Only series that matter to a backtest (a market with bars, or one big enough for the census)."""
    todo = db.execute(f"SELECT DISTINCT series FROM markets WHERE early IS NULL AND src='hist' AND "
                      f"(candles_done=1 OR volume>=?) AND category IN ({','.join('?' * len(categories))}) ORDER BY series",
                      [census_volume] + categories).fetchall()
    if not todo:
        return
    log(f"backfill: scheduled end dates for {len(todo)} series")
    failures = 0
    for i, (series,) in enumerate(todo):
        try:
            rows = [(*schedule(m), m["ticker"]) for m in k.pages("/historical/markets", "markets", tries=3, series_ticker=series)]
            db.executemany("UPDATE markets SET exp_ts=?, early=? WHERE ticker=?", rows)
            # whatever the archive no longer lists must not be asked for again (only after a full answer: a
            # failed read says nothing about what is listed, and the series is tried again on the next run)
            db.execute("UPDATE markets SET early=-1 WHERE series=? AND early IS NULL AND src='hist'", (series,))
            failures = 0
        except KalshiError as e:
            failures += 1
            log(f"backfill: {series}: {e}")
            if failures >= 5:
                break
            time.sleep(60)
        db.commit()
        if i % 200 == 0:
            log(f"backfill: {i}/{len(todo)} series; {k.requests} requests, {k.rate_limited} rate limits")
    log("backfill: done")


def candle_rows(ticker, cs):
    out = []
    for c in cs:
        def g(group, field):
            d = c.get(group) or {}
            return num(first(d, field + "_dollars", field))
        out.append((ticker, c.get("end_period_ts"), g("yes_bid", "close"), g("yes_ask", "close"), g("yes_bid", "high"),
                    g("yes_bid", "low"), g("yes_ask", "high"), g("yes_ask", "low"), g("price", "close"), g("price", "high"),
                    g("price", "low"), num(first(c, "volume_fp", "volume")), num(first(c, "open_interest_fp", "open_interest")),
                    g("yes_bid", "open"), g("yes_ask", "open"), g("price", "mean")))
    return [r for r in out if r[1]]


def phase_candles(db, k, categories, min_volume, max_markets, max_days, biggest_first=False, late_only=False):
    """biggest_first=False: the fixed random order (the random sample). True: every market with at least
    min_volume lifetime contracts, biggest first (the census of busy markets; research/panel.py, sample="liquid").
    late_only: only the late listings of phase_refresh (in the random order). Returns the markets attempted."""
    order = "volume DESC" if biggest_first else "rnd"
    only = " AND COALESCE(late, 0)=1" if late_only else ""
    done = 0
    cats = [c for c in categories if db.execute("SELECT 1 FROM markets WHERE category=? AND candles_done=0 AND volume>=?"
                                                f"{only} LIMIT 1", (c, min_volume)).fetchone()]
    kind = "late listings" if late_only else ("census, volume >= %g" % min_volume if biggest_first else "random order")
    log(f"candles ({kind}): categories with work: {cats}")
    retry_later: set[str] = set()                   # failed for a passing reason in this pass: not picked again in it
    while cats and done < max_markets:
        for cat in list(cats):                      # round-robin across categories
            rows = db.execute("SELECT ticker, series, open_ts, close_ts, src FROM markets WHERE category=? AND candles_done=0 "
                              f"AND volume>=?{only} ORDER BY {order} LIMIT ?", (cat, min_volume, 40 + len(retry_later))).fetchall()
            rows = [r for r in rows if r[0] not in retry_later][:40]
            if not rows:
                cats.remove(cat)
                continue
            for ticker, series, o, cl, src in rows:
                status = 1
                if not o or not cl or cl <= o:
                    status = 3
                else:
                    start = max(o, cl - max_days * 86400)
                    # a few old tickers contain "%" or spaces: KalshiHTTP.get encodes the path once (encoding it
                    # here as well sent "%2525" and got a 404, which wrote the market off)
                    path = (f"/historical/markets/{ticker}/candlesticks" if src == "hist"
                            else f"/series/{series or ''}/markets/{ticker}/candlesticks")
                    try:
                        cs = k.get(path, start_ts=start, end_ts=cl + 86400, period_interval=1440).get("candlesticks") or []
                        db.executemany("INSERT OR IGNORE INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", candle_rows(ticker, cs))
                        if not cs:
                            status = 2              # no bars: never quoted
                    except KalshiError as e:
                        # 404 and the other 4xx answers are final: the exchange will never answer for this
                        # ticker. Leaving it "to do" would get it picked again at once (one bad ticker stalled
                        # the whole download for a night) and would hold the random sample at this market for
                        # ever (panel.py stops at the first gap). 5xx and 429 after the retries wait for the next run.
                        status = 4 if 400 <= e.status_code < 500 and e.status_code != 429 else 0
                        if e.status_code != 404:
                            log(f"candles: {ticker}: {e}")
                    except Exception as e:          # network trouble: leave it for the next run
                        status = 0
                        log(f"candles: {ticker}: {type(e).__name__}")
                        time.sleep(10)
                if status:
                    db.execute("UPDATE markets SET candles_done=? WHERE ticker=?", (status, ticker))
                else:
                    retry_later.add(ticker)
                done += 1
            db.commit()
            if done % 2000 < 40:
                n = db.execute("SELECT COUNT(*) FROM markets WHERE candles_done=1").fetchone()[0]
                log(f"candles: {n} markets with bars; {k.requests} requests, {k.rate_limited} rate limits, interval {k.min_interval:.2f}s")
    log(f"candles: finished this pass ({done} markets)")
    return done


def migrate(db):
    """Columns added after the first databases were made (kept out of SCHEMA, which other tools and tests use with
    positional inserts): the shuffle, the schedule, and the refresh's late flag and listing times."""
    have = {r[1] for r in db.execute("PRAGMA table_info(markets)")}
    if "rnd" not in have:                           # databases from before the shuffle
        db.execute("ALTER TABLE markets ADD COLUMN rnd INTEGER")
    for col in ("exp_ts", "early", "late"):         # ... the scheduled end date, the refresh
        if col not in have:
            db.execute(f"ALTER TABLE markets ADD COLUMN {col} INTEGER")
    have_s = {r[1] for r in db.execute("PRAGMA table_info(series)")}
    for col in ("late", "hist_ts", "recent_ts"):
        if col not in have_s:
            db.execute(f"ALTER TABLE series ADD COLUMN {col} INTEGER")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "data" / "kalshi_hist.db"))
    ap.add_argument("--phase", default="all", choices=["all", "series", "markets", "recent", "candles"])
    ap.add_argument("--categories", default=",".join(c for c in CATEGORIES if c != "Sports"))
    ap.add_argument("--with-sports", action="store_true",
                    help="add Sports (last) to the categories: its own sample, analysed apart from the rest (the user, "
                         "2026-11-24: \"Test as many things as you can\"; backlog family 16)")
    ap.add_argument("--min-volume", type=float, default=1.0,
                    help="lifetime contracts traded; keep it at 1 (any trade at all): a higher bar selects on hindsight")
    ap.add_argument("--max-markets", type=int, default=10 ** 9)
    ap.add_argument("--first-pass", type=int, default=4000, help="markets per category to get bars for in the first pass")
    ap.add_argument("--census-volume", type=float, default=5000.0,
                    help="after the random pass, also fetch EVERY market with at least this many lifetime contracts, biggest "
                         "first (0 = off). Valid without hindsight only for rules that look at a market after it has traded "
                         "that much: panel.load(sample='liquid') enforces it")
    ap.add_argument("--census-max", type=int, default=8000, help="census markets per category")
    ap.add_argument("--max-per-series", type=int, default=200000)
    ap.add_argument("--max-days", type=int, default=400)
    ap.add_argument("--interval", type=float, default=0.2, help="seconds between requests")
    ap.add_argument("--refresh-days", type=float, default=0.0,
                    help="list every series again this often (phase_refresh): new series, markets settled since (0 = off)")
    ap.add_argument("--forever", action="store_true",
                    help="never finish: the random pass in chunks, with the refresh between them; an idle round waits an hour")
    ap.add_argument("--chunk", type=int, default=20000, help="--forever: markets per random-pass chunk (about 2.5 h)")
    ap.add_argument("--rounds", type=int, default=0, help="--forever: stop after this many rounds (0 = never; for tests)")
    args = ap.parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    if args.with_sports and "Sports" not in cats:
        cats.append("Sports")
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(args.db, timeout=60)
    db.executescript(SCHEMA)
    migrate(db)
    todo = db.execute("SELECT ticker FROM markets WHERE rnd IS NULL").fetchall()
    if todo:
        db.executemany("UPDATE markets SET rnd=? WHERE ticker=?", [(shuffle_key(t[0]), t[0]) for t in todo])
        db.commit()
    db.execute("CREATE INDEX IF NOT EXISTS markets_rnd ON markets (category, candles_done, rnd)")
    db.execute("PRAGMA journal_mode=WAL")
    k = KalshiHTTP(min_interval=args.interval)
    if args.phase in ("all", "series"):
        phase_series(db, k, cats)
    def refresh(categories=cats):
        return phase_refresh(db, k, categories, args.refresh_days, args.max_per_series, args.max_days, args.min_volume)
    if args.phase == "all":
        phase_backfill(db, k, cats, args.census_volume)        # everything listed before the schedule columns existed
        if args.refresh_days > 0:                   # the categories already analysed get their new markets first; the
            refresh([c for c in cats if c not in REFRESH_BIG])  # two giant ones wait for the first --forever round
        # First pass, one category at a time: list its markets, then fetch bars for its biggest ones. Analysis can
        # start on the first categories while the later ones are still downloading.
        for cat in cats:
            phase_markets(db, k, [cat], args.max_per_series, "hist")
            phase_backfill(db, k, [cat], args.census_volume)
            have = db.execute("SELECT COUNT(*) FROM markets WHERE category=? AND volume>=? AND rnd<?",
                              (cat, args.min_volume, frontier(db, cat, args.min_volume))).fetchone()[0]
            if have < args.first_pass:              # a restart does not repeat a category's first pass
                phase_candles(db, k, [cat], args.min_volume, args.first_pass - have, args.max_days)
            if args.census_volume > 0:
                got = db.execute("SELECT COUNT(*) FROM markets WHERE category=? AND volume>=? AND candles_done<>0",
                                 (cat, args.census_volume)).fetchone()[0]
                if got < args.census_max:
                    phase_candles(db, k, [cat], args.census_volume, args.census_max - got, args.max_days, biggest_first=True)
    if args.phase in ("all", "markets"):                # also picks up any series a throttled pass left behind
        phase_markets(db, k, cats, args.max_per_series, "hist")
    if args.phase == "all" and args.forever:
        rounds = 0
        while True:
            did = phase_candles(db, k, cats, args.min_volume, args.chunk, args.max_days) or 0
            if args.refresh_days > 0:
                did += refresh()
            phase_markets(db, k, cats, args.max_per_series, "hist")
            rounds += 1
            if args.rounds and rounds >= args.rounds:
                break
            if not did:
                log("nothing to do: looking again in an hour")
                time.sleep(3600)
        db.close()
        return
    if args.phase in ("all", "candles"):
        phase_candles(db, k, cats, args.min_volume, args.max_markets, args.max_days)
    if args.phase in ("all", "recent"):                 # last: the live endpoint is the touchy one
        k.min_interval = max(k.min_interval, 0.6)
        phase_markets(db, k, cats, args.max_per_series, "recent")
        phase_candles(db, k, cats, args.min_volume, args.max_markets, args.max_days)
    db.close()


if __name__ == "__main__":
    main()
