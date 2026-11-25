"""Ideas queue 48: one bet per event. Ladders (Rotten Tomatoes, streaming ranks) give a rule several correlated bets in
one event; this keeps only one, chosen with what is known at the bar: on the first day the event has any bet, the
rung whose YES mid is nearest the target (20c); every other bet of the event is dropped, including later ones.

Pre-stated: the one-per-event version is "the risk-averse version" if it passes the tail test in both halves AND
its 1% replay has a lower out-of-sample worst drawdown than all rungs. Backtest only.

    .venv/Scripts/python.exe research/one_per_event.py --rule "NO where YES is at 5-35c" --categories Entertainment --min-cumvol 20000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import panel  # noqa: E402
import portfolio  # noqa: E402
from analyze_rule import bets_frame, find_rule  # noqa: E402
from backtest import Panel  # noqa: E402
from families import Features  # noqa: E402
from run_sweep import titles_for  # noqa: E402
from series_concentration import _half  # noqa: E402


def pick_one_per_event(rows: np.ndarray, event: np.ndarray, day: np.ndarray, yes_mid: np.ndarray,
                       target: float = 0.20) -> np.ndarray:
    """rows: the bet rows (first bar per market). Keep, per event, the row on the event's first bet day whose YES
    mid is nearest `target` (ties: the earlier row). Returns the kept rows, sorted."""
    if rows.size == 0:
        return rows
    d = pd.DataFrame({"row": rows, "ev": event[rows], "day": day[rows], "dist": np.abs(yes_mid[rows] - target)})
    first = d.groupby("ev")["day"].transform("min")
    d = d[d["day"] == first].sort_values(["ev", "dist", "row"])
    return np.sort(d.drop_duplicates("ev")["row"].to_numpy())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", required=True)
    ap.add_argument("--side", default="no", choices=["yes", "no"])
    ap.add_argument("--entry", default="mk", choices=["tk", "mk"])
    ap.add_argument("--categories", required=True)
    ap.add_argument("--min-cumvol", type=float, default=None)
    ap.add_argument("--target", type=float, default=0.20)
    ap.add_argument("--db", default=str(panel.DB))
    args = ap.parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    df = panel.load(args.db, cats, sample="liquid", min_cumvol=args.min_cumvol)
    print(panel.describe(df).splitlines()[0])
    p = Panel(df)
    f = Features(p)
    _, mask = find_rule(f, titles_for(df, args.db), args.rule, args.side, args.entry)
    key = (args.side, args.entry)
    rows = p.first_per_market(mask & p.ok[key])
    yes_mid = ((df["bid"] + df["ask"]) / 2).to_numpy("float64")
    day = (df["ts"].to_numpy() // 86400).astype("int64")
    kept = pick_one_per_event(rows, p.event, day, yes_mid, args.target)
    one = np.zeros(p.n, bool)
    one[kept] = True
    fmt = lambda x: f"{x:+.4f}"  # noqa: E731
    out = []
    for name, m in (("all rungs", mask), ("one per event", one)):
        b = bets_frame(p, m, args.side, args.entry)
        a, o = portfolio.run(p, [(m, args.side, args.entry)], stake_frac=0.01)
        for half, sel, acc in (("in", ~b["oos"].astype(bool), a), ("out", b["oos"].astype(bool), o)):
            out.append({"version": name, "half": half, **_half(b[sel]), "cagr": acc.cagr, "max_dd": acc.max_dd,
                        "at_work": acc.exposure})
    pd.set_option("display.width", 250)
    print(pd.DataFrame(out).to_string(index=False, float_format=fmt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
