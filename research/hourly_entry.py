"""Entries on HOURLY bars in a market's last hours (Ideas queue item 59: Sports games live a few days, so daily bars
are coarse there, report 3.93).

Reads data/kalshi_hourly.db (research/hourly_bars.py; for Sports fetched with --rules all, every market of the random
sample in the download's shuffle, so the selection has no hindsight). One bet per market: the FIRST hourly bar whose
close quotes qualify. Same costs as panel.py on daily bars, one bar later:
  taker  NO at the NEXT bar's opening YES bid (1 - bid_op), plus the taker fee
  resting NO bid at 1 - the signal bar's YES ask; filled only if within the next 3 bars the YES bid rose to that ask
         or a trade printed above it (panel.py's f3 rule); maker fee only where the series charges one
Held to settlement. Per-bet return; t by event; the tail test of analyze_rule.py; split at 2026-04-01 by close.

    python research/hourly_entry.py --categories Sports
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import panel  # noqa: E402
from analyze_rule import tail  # noqa: E402
from data_paths import hourly_db  # noqa: E402

RULES = {  # name: (lowest YES mid, highest YES mid, widest spread)
    "5c": (0.0, 0.05, 0.05),          # the 5-cent rule (spread <= 5c; days to close <= 30 holds in the window)
    "10-25c": (0.10, 0.25, 1.0),      # the r26 Sports lead (3.93): NO on YES at 10-25c
}


def bets(h: pd.DataFrame, mk: pd.DataFrame, lo: float, hi: float, max_spread: float, entry: str) -> pd.DataFrame:
    """h: hourly bars (ticker, ts, bid, ask, bid_hi, px_hi, bid_op), mk: per ticker (ticker, event, close_ts, y, mult,
    maker_fee). Returns one row per market bet: ticker, event, close_ts, cost, ret."""
    h = h.sort_values(["ticker", "ts"]).reset_index(drop=True)
    h = h.merge(mk, on="ticker", how="inner")
    h = h[h["ts"] < h["close_ts"]]                         # the signal must be seen before the close
    quoted = h["bid"].notna() & h["ask"].notna() & (h["ask"] > h["bid"]) & (h["bid"] > 0) & (h["ask"] < 1)
    mid = (h["bid"] + h["ask"]) / 2
    g = h.groupby("ticker", sort=False)
    nxt_bid_op = g["bid_op"].shift(-1)
    nxt_ts = g["ts"].shift(-1)
    fill = pd.Series(False, index=h.index)
    for k in (1, 2, 3):
        bh, ph = g["bid_hi"].shift(-k), g["px_hi"].shift(-k)
        fill |= (bh >= h["ask"] - 1e-6) | (ph > h["ask"] + 1e-6)
    sig = quoted & (mid >= lo - 1e-9) & (mid <= hi + 1e-9) & ((h["ask"] - h["bid"]) <= max_spread + 1e-9)
    if entry == "tk":
        sig &= nxt_bid_op.notna() & (nxt_bid_op > 0) & (nxt_bid_op < 1) & (nxt_ts < h["close_ts"])
    first = h[sig].groupby("ticker", sort=False).head(1).index
    b = h.loc[first, ["ticker", "event", "close_ts", "y", "mult", "maker_fee", "ask"]].copy()
    if entry == "tk":
        p = nxt_bid_op.loc[first].to_numpy()
        cost = (1 - p) + panel.TAKER * b["mult"].to_numpy() * p * (1 - p)
    else:
        b = b[fill.loc[first].to_numpy()]
        p = b["ask"].to_numpy()
        rate = np.where(b["maker_fee"].to_numpy(bool), panel.MAKER, 0.0)
        cost = (1 - p) + rate * b["mult"].to_numpy() * p * (1 - p)
    b["cost"] = cost
    b["ret"] = ((1 - b["y"].to_numpy()) - cost) / cost
    return b[["ticker", "event", "close_ts", "cost", "ret"]].reset_index(drop=True)


def summary(b: pd.DataFrame) -> dict:
    ev = b.groupby("event")["ret"].sum().to_numpy()
    n = len(ev)
    m = float(b["ret"].mean()) if len(b) else float("nan")
    em = ev.mean() if n else float("nan")
    t = float(em / (ev.std(ddof=1) / np.sqrt(n))) if n > 2 and ev.std(ddof=1) > 0 else float("nan")
    out = {"bets": len(b), "events": n, "per_bet": m, "t_event": t, "cost": float(b["cost"].mean()) if len(b) else np.nan}
    out.update({f"tail_{k}": v for k, v in tail(ev).items()} if n else {})
    return out


def load(hist_db, hdb, categories) -> tuple[pd.DataFrame, pd.DataFrame]:
    con = sqlite3.connect(f"file:{hist_db}?mode=ro", uri=True, timeout=60)
    q = ("SELECT m.ticker, m.event, m.close_ts, m.result, s.fee_type, s.fee_multiplier FROM markets m "
         "LEFT JOIN series s ON s.ticker = m.series WHERE m.result IN ('yes','no')")
    args: list = []
    if categories:
        q += f" AND m.category IN ({','.join('?' * len(categories))})"
        args += categories
    mk = pd.read_sql_query(q, con, params=args)
    con.close()
    mk["y"] = (mk["result"] == "yes").astype(float)
    mk["mult"] = mk["fee_multiplier"].fillna(1.0).astype(float)
    mk["maker_fee"] = mk["fee_type"].fillna("").str.contains("maker")
    hc = sqlite3.connect(f"file:{hdb}?mode=ro", uri=True, timeout=60)
    h = pd.read_sql_query("SELECT c.ticker, c.ts, c.bid, c.ask, c.bid_hi, c.px_hi, c.bid_op FROM candles_1h c "
                          "JOIN hourly_done d ON d.ticker = c.ticker WHERE d.status = 1", hc)
    hc.close()
    return h, mk[["ticker", "event", "close_ts", "y", "mult", "maker_fee"]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(panel.DB))
    ap.add_argument("--hourly", default=str(hourly_db()))
    ap.add_argument("--categories", default="Sports")
    args = ap.parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()] or None
    h, mk = load(args.db, args.hourly, cats)
    mk = mk[mk["ticker"].isin(set(h["ticker"]))]
    h = h[h["ticker"].isin(set(mk["ticker"]))]
    print(f"{len(mk)} settled markets with hourly bars, {mk['event'].nunique()} events, {len(h)} hourly bars; "
          f"closes {pd.to_datetime(mk['close_ts'].min(), unit='s'):%Y-%m-%d} to {pd.to_datetime(mk['close_ts'].max(), unit='s'):%Y-%m-%d}")
    print("| rule | entry | half | bets | events | per bet | t (event) | mean cost | losing ev | break-even | upper 95% | tail |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, (lo, hi, sp) in RULES.items():
        for entry in ("tk", "mk"):
            b = bets(h, mk, lo, hi, sp, entry)
            for half, part in (("in", b[b["close_ts"] < panel.SPLIT_TS]), ("out", b[b["close_ts"] >= panel.SPLIT_TS])):
                s = summary(part)
                if not s["bets"]:
                    print(f"| {name} | {entry} | {half} | 0 | | | | | | | | |")
                    continue
                print(f"| {name} | {entry} | {half} | {s['bets']} | {s['events']} | {s['per_bet']:+.2%} | {s['t_event']:.1f} | "
                      f"{s['cost']:.3f} | {s['tail_losing']} | {s['tail_breakeven']:.1%} | {s['tail_upper95']:.1%} | "
                      f"{'pass' if s['tail_proven'] else 'fail'} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
