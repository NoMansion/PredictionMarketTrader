"""Adverse selection of the resting fill (queue item 36, report 3.58).

    python research/fill_speed.py --categories Entertainment --min-cumvol 20000

Report 3.56 found that bids which fill late are the losers. Here, for the band rule's first bar per market (known at
the bar; resting NO at 1 - ask for 3 bars, the backtest's standard r_no_mk), split the placements by the bar on which
the resting order filled: bar 1, bar 2-3, never. Filled orders earn r_no_mk. Unfilled orders are priced as a taker
would pay: at the next bar's open (r_no_tk of the placement bar, "taker now") and at the open after the 3-bar window
(r_no_tk of placement + 3, "taker late", the price a trader who cancels and then crosses would get).
Is a slow fill (no fill on bar 1) a warning sign worth cancelling on?
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import panel  # noqa: E402
from analyze_rule import find_rule, tail  # noqa: E402
from backtest import Panel  # noqa: E402
from families import Features  # noqa: E402
from run_sweep import titles_for  # noqa: E402


def fill_bar(df: pd.DataFrame, rows: np.ndarray) -> np.ndarray:
    """First later bar (1, 2 or 3) on which a resting NO bid at 1 - ask of the row fills; 0 = never in 3 bars.
    Same test as panel's f3_no: the YES bid rose to the ask or a trade printed above it. df ordered by market, time."""
    rows = np.asarray(rows, dtype=int)
    tk = df["ticker"].to_numpy()
    ask = df["ask"].to_numpy("float64")[rows]
    bid_hi = df["bid_hi"].to_numpy("float64")
    px_hi = df["px_hi"].to_numpy("float64")
    out = np.zeros(len(rows), dtype=int)
    for k in (3, 2, 1):                       # descending, so the earliest bar wins
        t = rows + k
        ok = t < len(df)
        tc = np.where(ok, t, 0)
        ok &= tk[tc] == tk[rows]
        hit = ok & ((np.nan_to_num(bid_hi[tc], nan=-1) >= ask - 1e-6) | (np.nan_to_num(px_hi[tc], nan=-1) > ask + 1e-6))
        out = np.where(hit, k, out)
    return out


def taker_at(df: pd.DataFrame, rows: np.ndarray, lag: int) -> np.ndarray:
    """r_no_tk of the row `lag` bars later in the same market (NaN when the market has no such row)."""
    rows = np.asarray(rows, dtype=int)
    tk = df["ticker"].to_numpy()
    t = rows + lag
    ok = t < len(df)
    tc = np.where(ok, t, 0)
    ok &= tk[tc] == tk[rows]
    return np.where(ok, df["r_no_tk"].to_numpy("float64")[tc], np.nan)


def line(label: str, r: np.ndarray, event: np.ndarray) -> str:
    f = ~np.isnan(r)
    if f.sum() == 0:
        return f"    {label:22s} n 0"
    sums = pd.Series(r[f]).groupby(event[f]).sum().to_numpy()
    x = tail(sums)
    return (f"    {label:22s} n {f.sum():4d}, per bet {r[f].mean():+7.2%}, lose {np.mean(r[f] < 0):4.0%}; "
            f"{x['events']} events, bound {x['upper95']:.1%} vs {x['breakeven']:.1%} "
            f"{'passes' if x['proven'] else 'FAILS'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(panel.DB))
    ap.add_argument("--categories", default="Entertainment")
    ap.add_argument("--min-cumvol", type=float, default=20000)
    ap.add_argument("--rule", default="NO where YES is at 5-35c")
    a = ap.parse_args()
    cats = [c.strip() for c in a.categories.split(",") if c.strip()] or None
    df = panel.load(a.db, cats, sample="liquid", min_cumvol=a.min_cumvol)
    print(panel.describe(df).splitlines()[0])
    p = Panel(df)
    f = Features(p)
    _, mask = find_rule(f, titles_for(df, a.db), a.rule, "no", "mk")
    rows = p.first_per_market(mask & df["quoted"].to_numpy(bool))
    event, oos = df["event"].to_numpy()[rows], df["oos"].to_numpy(bool)[rows]
    fb = fill_bar(df, rows)
    mk = df["r_no_mk"].to_numpy("float64")[rows]
    now, late = taker_at(df, rows, 0), taker_at(df, rows, 3)
    print(f"{a.rule}, NO, resting, min_cumvol {a.min_cumvol:,.0f}: {len(rows):,} placements in {len(set(event)):,} events")
    for name, m in (("in sample", ~oos), ("out of sample", oos)):
        print(f"  {name}: placed {m.sum()}, fill bar 1 {np.mean(fb[m] == 1):.0%}, bar 2-3 {np.mean(fb[m] >= 2):.0%}, "
              f"never {np.mean(fb[m] == 0):.0%}")
        print(line("filled bar 1", np.where(m & (fb == 1), mk, np.nan), event))
        print(line("filled bar 2-3", np.where(m & (fb >= 2), mk, np.nan), event))
        print(line("never: taker now", np.where(m & (fb == 0), now, np.nan), event))
        print(line("never: taker late", np.where(m & (fb == 0), late, np.nan), event))
        print(line("bar 2-3: taker now", np.where(m & (fb >= 2), now, np.nan), event))
        # policy: keep only bar-1 fills (cancel after one bar) vs the standard 3 bars, per order
        keep1 = np.where(m & (fb == 1), mk, 0.0)[m]
        keep3 = np.where(m & (fb >= 1), mk, 0.0)[m]
        print(f"    per order: cancel after bar 1 {np.nan_to_num(keep1).mean():+.2%}, rest 3 bars "
              f"{np.nan_to_num(keep3).mean():+.2%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
