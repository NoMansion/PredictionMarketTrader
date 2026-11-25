"""Ideas queue 49: a second opinion on the tail test. The queue's wording (shuffle outcomes between events within each
price cent) is degenerate: a shuffle inside a price cell keeps every cell's win count, so the per-bet mean cannot move.
This draws outcomes under the null that the price is right instead, with events kept whole:

  each draw gives every event ONE uniform U; a bet in it resolves YES if U < p_yes (rungs of one ladder move together,
  the most correlated choice, so the null's spread is if anything too wide).

Two nulls for a resting NO bet: p_yes = the ask (the price paid is fair: no edge at all) and p_yes = the mid (no edge
beyond the half spread a resting order earns). Reported: the share of draws with a per-bet return at least the
observed one, in each half. Backtest only.

    .venv/Scripts/python.exe research/calibrated_null.py --rule "NO where YES is at 5-35c" --categories Entertainment --min-cumvol 20000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import panel  # noqa: E402
from analyze_rule import find_rule  # noqa: E402
from backtest import Panel  # noqa: E402
from families import Features  # noqa: E402
from run_sweep import titles_for  # noqa: E402


def null_share(cost: np.ndarray, p_yes: np.ndarray, event: np.ndarray, observed: float, draws: int = 5000,
               seed: int = 0) -> dict:
    """NO bets at all-in cost `cost` (a win pays 1). Per-bet mean return under outcomes drawn with P(YES) = p_yes,
    one uniform per event per draw. Returns the share of draws at least `observed`, and the null's mean and sd."""
    rng = np.random.default_rng(seed)
    ev = pd.factorize(event)[0]
    n_ev = int(ev.max()) + 1 if ev.size else 0
    win, lose = (1 - cost) / cost, -1.0
    means = np.empty(draws)
    for k in range(draws):
        u = rng.random(n_ev)[ev]
        means[k] = np.where(u < p_yes, lose, win).mean()
    return {"share_ge": float((means >= observed - 1e-12).mean()), "null_mean": float(means.mean()),
            "null_sd": float(means.std()), "observed": observed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", required=True)
    ap.add_argument("--categories", required=True)
    ap.add_argument("--min-cumvol", type=float, default=None)
    ap.add_argument("--draws", type=int, default=5000)
    ap.add_argument("--db", default=str(panel.DB))
    args = ap.parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    df = panel.load(args.db, cats, sample="liquid", min_cumvol=args.min_cumvol)
    print(panel.describe(df).splitlines()[0])
    p = Panel(df)
    f = Features(p)
    _, mask = find_rule(f, titles_for(df, args.db), args.rule, "no", "mk")
    rows = p.first_per_market(mask & p.ok[("no", "mk")])
    d = df.iloc[rows]
    ask, bid = d["ask"].to_numpy("float64"), d["bid"].to_numpy("float64")
    mrate = np.where(d["maker_fee"].to_numpy(bool), panel.MAKER, 0.0)
    cost = (1 - ask) + mrate * d["mult"].to_numpy("float64") * ask * (1 - ask)
    r = p.r[("no", "mk")][rows].astype("float64")
    oos = d["oos"].to_numpy(bool)
    out = []
    for half, m in (("in", ~oos), ("out", oos)):
        for null, py in (("price fair (ask)", ask), ("mid", (bid + ask) / 2)):
            x = null_share(cost[m], py[m], d["event"].to_numpy()[m], float(r[m].mean()), args.draws)
            out.append({"half": half, "bets": int(m.sum()), "events": d["event"][m].nunique(), "null": null, **x})
    pd.set_option("display.width", 200)
    print(pd.DataFrame(out).to_string(index=False, float_format=lambda v: f"{v:+.4f}"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
