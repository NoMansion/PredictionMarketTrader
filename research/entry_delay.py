"""Entry delay in the Entertainment band's short-dated markets (queue item 34, report 3.56).

    python research/entry_delay.py --categories Entertainment --min-cumvol 20000 --dte-hi 7

Report 3.54 found the band's NO gets cheaper over the next 1-3 bars in 0-7 day markets. Does resting the NO bid a cent
or two lower, or one or three bars later, buy NO cheaper without losing the fills that pay? Every variant starts from
the same placement: the band rule's first bar per market inside the days-to-close window (known at the bar).

  base      rest NO at 1 - ask of that bar for 3 bars (the backtest's standard resting entry, r_no_mk)
  -k c      rest NO k cents lower (YES level ask + k/100); fills if a later bar's YES bid reached that level or a trade
            printed above it within 3 bars
  +d bars   commit at the placement bar, rest at the bar d bars later at its 1 - ask (that bar's r_no_mk); no bet if
            the market has no quoted bar there

"per order" counts unfilled orders as 0: the fair comparison, since a cheaper bid that fills less can earn less.
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


def variant_returns(df: pd.DataFrame, rows: np.ndarray, delay: int = 0, offset: float = 0.0) -> np.ndarray:
    """Return per dollar for each placement row (NaN = no fill / no bet). df ordered by market, then time."""
    rows = np.asarray(rows, dtype=int)
    if delay:
        tk = df["ticker"].to_numpy()
        tgt = rows + delay
        ok = tgt < len(df)
        tgt_c = np.where(ok, tgt, 0)
        ok &= tk[tgt_c] == tk[rows]
        ok &= df["quoted"].to_numpy(bool)[tgt_c]
        r = df["r_no_mk"].to_numpy("float64")[tgt_c]
        return np.where(ok, r, np.nan)
    if offset == 0:
        return df["r_no_mk"].to_numpy("float64")[rows]
    g = df.groupby("ticker", sort=False)
    hi = pd.concat([g["bid_hi"].shift(-i) for i in (1, 2, 3)], axis=1).max(axis=1).to_numpy("float64")[rows]
    phi = pd.concat([g["px_hi"].shift(-i) for i in (1, 2, 3)], axis=1).max(axis=1).to_numpy("float64")[rows]
    lvl = df["ask"].to_numpy("float64")[rows] + offset          # YES level the NO bid sits at
    quoted = df["quoted"].to_numpy(bool)[rows]
    filled = quoted & (lvl < 1 - 1e-9) & ((hi >= lvl - 1e-6) | (phi > lvl + 1e-6))
    mrate = np.where(df["maker_fee"].to_numpy(bool)[rows], panel.MAKER, 0.0)
    mult = df["mult"].to_numpy("float64")[rows]
    c = (1 - lvl) + mrate * mult * lvl * (1 - lvl)
    y = df["y"].to_numpy("float64")[rows]
    with np.errstate(divide="ignore", invalid="ignore"):
        r = ((1 - y) - c) / c
    return np.where(filled, r, np.nan)


def summarize(label: str, r: np.ndarray, event: np.ndarray, oos: np.ndarray) -> str:
    out = []
    for name, m in (("in", ~oos), ("out", oos)):
        rr, ev = r[m], event[m]
        f = ~np.isnan(rr)
        if not f.any():
            out.append(f"  {label:9s} {name:3s} placed {m.sum():4d}, filled 0")
            continue
        sums = pd.Series(rr[f]).groupby(ev[f]).sum().to_numpy()
        x = tail(sums)
        out.append(f"  {label:9s} {name:3s} placed {m.sum():4d}, filled {f.sum():4d} ({f.mean():.0%}), "
                   f"per bet {np.nanmean(rr):+.2%}, per order {np.nan_to_num(rr).mean():+.2%}; {x['events']} events, "
                   f"{x['losing']} losing, bound {x['upper95']:.1%} vs {x['breakeven']:.1%} "
                   f"{'passes' if x['proven'] else 'FAILS'}")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(panel.DB))
    ap.add_argument("--categories", default="Entertainment")
    ap.add_argument("--min-cumvol", type=float, default=20000)
    ap.add_argument("--rule", default="NO where YES is at 5-35c")
    ap.add_argument("--dte-lo", type=float, default=0)
    ap.add_argument("--dte-hi", type=float, default=7)
    a = ap.parse_args()
    cats = [c.strip() for c in a.categories.split(",") if c.strip()] or None
    df = panel.load(a.db, cats, sample="liquid", min_cumvol=a.min_cumvol)
    print(panel.describe(df).splitlines()[0])
    p = Panel(df)
    f = Features(p)
    _, mask = find_rule(f, titles_for(df, a.db), a.rule, "no", "mk")
    m = mask & f.days(a.dte_lo, a.dte_hi) & df["quoted"].to_numpy(bool)
    rows = p.first_per_market(m)
    event, oos = df["event"].to_numpy()[rows], df["oos"].to_numpy(bool)[rows]
    print(f"{a.rule}, NO, resting, dte {a.dte_lo:g}-{a.dte_hi:g}, min_cumvol {a.min_cumvol:,.0f}: "
          f"{len(rows):,} placements in {len(set(event)):,} events")
    for label, d, o in (("base", 0, 0.0), ("-1c", 0, 0.01), ("-2c", 0, 0.02), ("+1 bar", 1, 0.0), ("+3 bars", 3, 0.0)):
        print(summarize(label, variant_returns(df, rows, d, o), event, oos))
    return 0


if __name__ == "__main__":
    sys.exit(main())
