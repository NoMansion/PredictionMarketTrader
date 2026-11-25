"""Ideas queue 44: edge decay. Per-bet return of a rule by calendar quarter of the market's close (bets, events,
event-clustered standard error per quarter) and the slope of per-bet return across quarters (OLS of each bet's return
on the quarter index, standard error clustered by event).

Pre-stated verdict: "decaying" if EVERY out-of-sample quarter's per-bet return is below the in-sample mean AND the
slope's t < -2. Backtest only.

    .venv/Scripts/python.exe research/edge_by_quarter.py --rule "NO where YES is at 5-35c" --categories Entertainment --min-cumvol 20000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import panel  # noqa: E402
from analyze_rule import bets_frame, find_rule  # noqa: E402
from backtest import Panel  # noqa: E402
from families import Features  # noqa: E402
from run_sweep import titles_for  # noqa: E402


def _cluster_se_mean(r: np.ndarray, ev: np.ndarray) -> float:
    n = len(r)
    if n < 2:
        return float("nan")
    e = pd.Series(r - r.mean()).groupby(ev).sum().to_numpy()
    return float(np.sqrt((e ** 2).sum()) / n) if len(e) > 1 else float("nan")


def by_quarter(b: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """b: bets frame (r, event, close_ts, oos). Returns the per-quarter table and the slope / verdict."""
    b = b.copy()
    q = pd.to_datetime(b["close_ts"].to_numpy(), unit="s").to_period("Q")
    b["q"] = q.astype(str)
    b["qi"] = (q.year - q.year.min()) * 4 + q.quarter
    rows = []
    for name, g in b.groupby("q", sort=True):
        rows.append({"quarter": name, "oos": bool(g["oos"].mean() > 0.5), "bets": len(g), "events": g["event"].nunique(),
                     "per_bet": float(g["r"].mean()), "se": _cluster_se_mean(g["r"].to_numpy(), g["event"].to_numpy())})
    t = pd.DataFrame(rows)
    x = b["qi"].to_numpy("float64")
    y = b["r"].to_numpy("float64")
    xc = x - x.mean()
    sxx = float((xc ** 2).sum())
    if sxx <= 0:
        slope, se = 0.0, float("nan")
    else:
        slope = float((xc * (y - y.mean())).sum() / sxx)
        resid = y - y.mean() - slope * xc
        s = pd.Series(xc * resid).groupby(b["event"].to_numpy()).sum().to_numpy()
        se = float(np.sqrt((s ** 2).sum()) / sxx)
    is_mean = float(b.loc[~b["oos"].astype(bool), "r"].mean()) if (~b["oos"].astype(bool)).any() else float("nan")
    oos_q = t[t["oos"]]
    all_below = bool(len(oos_q) > 0 and (oos_q["per_bet"] < is_mean).all())
    tstat = slope / se if se and np.isfinite(se) and se > 0 else float("nan")
    verdict = {"slope_per_quarter": slope, "slope_t": tstat, "is_mean": is_mean, "oos_all_below_is": all_below,
               "decaying": bool(all_below and np.isfinite(tstat) and tstat < -2)}
    return t, verdict


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", required=True)
    ap.add_argument("--side", default="no", choices=["yes", "no"])
    ap.add_argument("--entry", default="mk", choices=["tk", "mk"])
    ap.add_argument("--categories", required=True)
    ap.add_argument("--min-cumvol", type=float, default=None)
    ap.add_argument("--db", default=str(panel.DB))
    args = ap.parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    df = panel.load(args.db, cats, sample="liquid", min_cumvol=args.min_cumvol)
    print(panel.describe(df).splitlines()[0])
    p = Panel(df)
    f = Features(p)
    _, mask = find_rule(f, titles_for(df, args.db), args.rule, args.side, args.entry)
    t, v = by_quarter(bets_frame(p, mask, args.side, args.entry))
    pd.set_option("display.width", 200)
    print(t.to_string(index=False, float_format=lambda x: f"{x:+.4f}"))
    print(f"in-sample mean {v['is_mean']:+.2%}; slope {v['slope_per_quarter']:+.3%} a quarter, t {v['slope_t']:+.2f}; "
          f"every out-of-sample quarter below in-sample mean: {v['oos_all_below_is']}; DECAYING: {v['decaying']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
