"""NO-price drift in band markets: does NO get dearer over a market's life, and when (queue item 32, report 3.54)?

    python research/no_drift.py --categories Entertainment --min-cumvol 20000 --lo 0.05 --hi 0.35

Every quoted bar of the liquid sample whose YES mid is in [lo, hi] (the band) is an observation. Its drift over the
next h bars (daily bars) is the change of the NO mid, -(mid[t+h] - mid[t]); "to settlement" is mid - y (the NO
side's gain from mid to the outcome, before fees and spread). Grouped by things known at the bar: days to the
scheduled end and the share of the market's life gone. Each event counts once (its bars averaged) so busy events do
not dominate; t is over events. A diagnostic of where the band's price moves, not a tradeable rule by itself.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import panel  # noqa: E402

DTE_BINS = [0, 7, 30, np.inf]
DTE_LABELS = ["0-7d", "7-30d", "30+d"]
LIFE_BINS = [-np.inf, 1 / 3, 2 / 3, np.inf]
LIFE_LABELS = ["first third", "middle third", "last third"]


def drift_frame(df: pd.DataFrame, lo: float, hi: float, horizons=(1, 3, 7)) -> pd.DataFrame:
    """One row per band bar: forward NO drift over each horizon (NaN past the market's last quoted bar)."""
    g = df.groupby("ticker", sort=False)["mid"]
    out = pd.DataFrame({"event": df["event"], "oos": df["oos"], "dte": df["dte"],
                        "life_gone": df["age"] / df["life"].where(df["life"] > 0)})
    for h in horizons:
        out[f"d{h}"] = -(g.shift(-h) - df["mid"])
    out["settle"] = df["mid"] - df["y"]
    band = df["quoted"].to_numpy(bool) & (df["mid"] >= lo - 1e-9).to_numpy() & (df["mid"] <= hi + 1e-9).to_numpy()
    out = out[band].copy()
    out["dte_bin"] = pd.cut(out["dte"], DTE_BINS, labels=DTE_LABELS, right=False)
    out["life_bin"] = pd.cut(out["life_gone"], LIFE_BINS, labels=LIFE_LABELS, right=False)
    return out


def by_event(d: pd.DataFrame, col: str) -> dict:
    """Mean of the per-event means of col, its t over events, and the number of events."""
    e = d.groupby("event")[col].mean().dropna()
    n = len(e)
    if n < 2:
        return {"events": n, "mean": float(e.mean()) if n else np.nan, "t": np.nan}
    return {"events": n, "mean": float(e.mean()), "t": float(e.mean() / (e.std(ddof=1) / np.sqrt(n)))}


def table(d: pd.DataFrame, group: str, cols) -> str:
    lines = [f"  {group:14s} {'half':6s} " + " ".join(f"{c:>21s}" for c in cols)]
    for key, part in d.groupby(group, observed=True):
        for half, hp in (("in", part[~part["oos"]]), ("out", part[part["oos"]])):
            cells = []
            for c in cols:
                x = by_event(hp, c)
                cells.append(f"{x['mean'] * 100:+6.2f}c t{x['t']:+5.1f} n{x['events']:<5d}".rjust(21))
            lines.append(f"  {str(key):14s} {half:6s} " + " ".join(cells))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(panel.DB))
    ap.add_argument("--categories", default="Entertainment")
    ap.add_argument("--min-cumvol", type=float, default=20000)
    ap.add_argument("--lo", type=float, default=0.05)
    ap.add_argument("--hi", type=float, default=0.35)
    a = ap.parse_args()
    cats = [c.strip() for c in a.categories.split(",") if c.strip()] or None
    df = panel.load(a.db, cats, sample="liquid", min_cumvol=a.min_cumvol)
    print(panel.describe(df))
    d = drift_frame(df, a.lo, a.hi)
    cols = ["d1", "d3", "d7", "settle"]
    print(f"\nNO drift, YES mid {a.lo:.2f}-{a.hi:.2f}, {len(d):,} band bars in {d['event'].nunique():,} events "
          f"(cents of NO price; per-event means; t over events)")
    for name, part in (("all", d.assign(all="all")),):
        print(table(part, "all", cols))
    print("\nby days to the scheduled end")
    print(table(d, "dte_bin", cols))
    print("\nby share of the market's life gone")
    print(table(d, "life_bin", cols))
    return 0


if __name__ == "__main__":
    sys.exit(main())
