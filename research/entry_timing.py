"""Entry timing: the same markets bet early (first bar in the sample) against late (first bar at a higher volume level).

    python research/entry_timing.py --categories Entertainment --early 5000 --late 20000 \
        --rule "NO where YES is at 5-35c" --side no --entry mk

Loads the liquid sample at the EARLY level. A market's "late" bet is the rule's first bar at which the market had
traded `--late` contracts or more (cumvol, known at the bar); its "early" bet is the rule's first bar at all.
Compared on the markets that have BOTH bets (report 3.50, queue item 30): is waiting for a market to get busy what
makes the higher-level account hold? Which markets get a late bet is known only afterwards, so this is a
diagnostic of timing, not a tradeable split; the early-only markets are printed for completeness.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import panel  # noqa: E402
from analyze_rule import bets_frame, find_rule, tail  # noqa: E402
from backtest import Panel  # noqa: E402
from families import Features  # noqa: E402
from run_sweep import titles_for  # noqa: E402


def timing_pair(p: Panel, mask: np.ndarray, side: str, entry: str, late: float):
    """(early, late, early_only): bet frames. early and late hold the same tickers, in the same order."""
    early = bets_frame(p, mask, side, entry)
    lt = bets_frame(p, mask & (p.df["cumvol"].to_numpy() >= late), side, entry)
    both = set(lt["ticker"])
    e = early[early["ticker"].isin(both)].set_index("ticker").loc[lt["ticker"]].reset_index()
    return e, lt.reset_index(drop=True), early[~early["ticker"].isin(both)].reset_index(drop=True)


def summary(label: str, b: pd.DataFrame) -> str:
    out = [f"{label}: {len(b):,} bets in {b['event'].nunique():,} events, mean {b['r'].mean():+.2%} a bet, "
           f"price {b['cost'].mean():.3f}, median hold {b['hold'].median():.1f} d"]
    for name, part in (("in sample", b[~b["oos"]]), ("out of sample", b[b["oos"]])):
        if part.empty:
            continue
        x = tail(part.groupby("event")["r"].sum().to_numpy())
        out.append(f"    {name:14s} {len(part):4d} bets, mean {part['r'].mean():+.2%}; {x['events']} events, "
                   f"{x['losing']} losing; bound {x['upper95']:.1%} vs break-even {x['breakeven']:.1%} -> "
                   f"{'passes' if x['proven'] else 'FAILS'}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", default="NO where YES is at 5-35c")
    ap.add_argument("--side", default="no", choices=["yes", "no"])
    ap.add_argument("--entry", default="mk", choices=["tk", "mk"])
    ap.add_argument("--db", default=str(panel.DB))
    ap.add_argument("--categories", default="Entertainment")
    ap.add_argument("--early", type=float, default=5000)
    ap.add_argument("--late", type=float, default=20000)
    a = ap.parse_args()
    cats = [c.strip() for c in a.categories.split(",") if c.strip()] or None
    df = panel.load(a.db, cats, sample="liquid", min_cumvol=a.early)
    print(panel.describe(df))
    p = Panel(df)
    _, mask = find_rule(Features(p), titles_for(df, a.db), a.rule, a.side, a.entry)
    e, lt, rest = timing_pair(p, mask, a.side, a.entry, a.late)
    print(f"\n{a.rule} | {a.side.upper()} | {a.entry} | early {a.early:,.0f}, late {a.late:,.0f}")
    print(summary(f"same markets, early bet (first bar at {a.early:,.0f}+)", e))
    print(summary(f"same markets, late bet (first bar at {a.late:,.0f}+)", lt))
    if len(e):
        same = (e["ts"].to_numpy() == lt["ts"].to_numpy()).mean()
        print(f"  {same:.0%} of these markets are bet on the same bar at both levels; late minus early "
              f"{lt['r'].mean() - e['r'].mean():+.2%} a bet, price {lt['cost'].mean() - e['cost'].mean():+.3f}")
    print(summary("markets with an early bet only (never bet at the late level)", rest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
