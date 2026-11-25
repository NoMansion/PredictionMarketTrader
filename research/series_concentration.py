"""Ideas queue 46: series concentration of a rule. Bets, events and per-bet return of its top series in each half,
then the rule without its best series and without its top 3, ranked by IN-SAMPLE money (summed return of the
in-sample bets), so the ranking carries no out-of-sample hindsight.

Pre-stated verdict: "fragile" if dropping the top series halves the out-of-sample per-bet return. Backtest only.

    .venv/Scripts/python.exe research/series_concentration.py --rule "NO where YES is at 5-35c" --categories Entertainment --min-cumvol 20000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import panel  # noqa: E402
from analyze_rule import bets_frame, find_rule, tail  # noqa: E402
from backtest import Panel  # noqa: E402
from families import Features  # noqa: E402
from run_sweep import titles_for  # noqa: E402


def series_table(b: pd.DataFrame, top: int = 15) -> pd.DataFrame:
    """Per series and half: bets, events, per-bet return, summed return. Sorted by in-sample money."""
    b = b.assign(half=np.where(b["oos"].astype(bool), "out", "in"))
    g = b.groupby(["series", "half"]).agg(bets=("r", "size"), events=("event", "nunique"),
                                          per_bet=("r", "mean"), money=("r", "sum")).unstack("half")
    g.columns = [f"{a}_{h}" for a, h in g.columns]
    for c in ("bets_in", "bets_out", "events_in", "events_out", "money_in", "money_out"):
        if c not in g:
            g[c] = 0.0
        g[c] = g[c].fillna(0.0)
    g["share_in"] = g["money_in"] / max(float(b.loc[b["half"] == "in", "r"].sum()), 1e-12)
    g["share_out"] = g["money_out"] / max(float(b.loc[b["half"] == "out", "r"].sum()), 1e-12)
    return g.sort_values("money_in", ascending=False).head(top).reset_index()


def _half(g: pd.DataFrame) -> dict:
    d = {"bets": len(g), "events": g["event"].nunique(), "per_bet": float(g["r"].mean()) if len(g) else float("nan")}
    if len(g):
        tt = tail(g.groupby("event")["r"].sum().to_numpy("float64"))
        d.update({"losing_ev": tt["losing"], "upper95": tt["upper95"], "breakeven": tt["breakeven"],
                  "tail_ok": tt["proven"]})
    return d


def drop_top(b: pd.DataFrame, ks=(0, 1, 3)) -> tuple[pd.DataFrame, dict]:
    """The rule without its top k series by in-sample money, each half. Verdict: fragile if dropping the top
    series halves the out-of-sample per-bet return (or turns it non-positive)."""
    oos = b["oos"].astype(bool)
    rank = b[~oos].groupby("series")["r"].sum().sort_values(ascending=False).index.tolist()
    rows = []
    for k in ks:
        drop = set(rank[:k])
        g = b[~b["series"].isin(drop)]
        for half, m in (("in", ~g["oos"].astype(bool)), ("out", g["oos"].astype(bool))):
            rows.append({"dropped": k, "series_dropped": ",".join(rank[:k]), "half": half, **_half(g[m])})
    t = pd.DataFrame(rows)
    out = t[t["half"] == "out"].set_index("dropped")["per_bet"]
    base, one = float(out.get(0, np.nan)), float(out.get(1, np.nan))
    fragile = bool(np.isfinite(base) and base > 0 and (not np.isfinite(one) or one <= base / 2))
    return t, {"oos_base": base, "oos_without_top1": one, "fragile": fragile}


def select_by_history(b: pd.DataFrame, min_events: int = 10) -> pd.DataFrame:
    """Queue item 47: series picked by their own in-sample record (10+ in-sample events and a positive in-sample
    per-bet return) against the rest, out of sample. Groups: picked, rejected (10+ events, not positive), thin
    (under min_events in sample, including series new out of sample)."""
    oos = b["oos"].astype(bool)
    ins = b[~oos].groupby("series").agg(ev=("event", "nunique"), r=("r", "mean"))
    seasoned = ins[ins["ev"] >= min_events]
    picked = set(seasoned.index[seasoned["r"] > 0])
    rejected = set(seasoned.index[seasoned["r"] <= 0])
    grp = np.where(b["series"].isin(picked), "picked", np.where(b["series"].isin(rejected), "rejected", "thin"))
    rows = []
    for name in ("picked", "rejected", "thin"):
        for half, m in (("in", ~oos), ("out", oos)):
            g = b[(grp == name) & m.to_numpy()]
            rows.append({"group": name, "half": half, "series": g["series"].nunique(), **_half(g)})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rule", required=True)
    ap.add_argument("--side", default="no", choices=["yes", "no"])
    ap.add_argument("--entry", default="mk", choices=["tk", "mk"])
    ap.add_argument("--categories", required=True)
    ap.add_argument("--min-cumvol", type=float, default=None)
    ap.add_argument("--db", default=str(panel.DB))
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--select", action="store_true", help="queue item 47: series picked by their in-sample record")
    args = ap.parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    df = panel.load(args.db, cats, sample="liquid", min_cumvol=args.min_cumvol)
    print(panel.describe(df).splitlines()[0])
    p = Panel(df)
    f = Features(p)
    _, mask = find_rule(f, titles_for(df, args.db), args.rule, args.side, args.entry)
    b = bets_frame(p, mask, args.side, args.entry)
    print(f"series with bets: {b['series'].nunique()} (in {b.loc[~b['oos'].astype(bool), 'series'].nunique()}, "
          f"out {b.loc[b['oos'].astype(bool), 'series'].nunique()}); last close {pd.to_datetime(b['close_ts'].max(), unit='s').date()}")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    fmt = lambda x: f"{x:+.4f}"  # noqa: E731
    print(series_table(b, args.top).to_string(index=False, float_format=fmt))
    t, v = drop_top(b)
    print(t.drop(columns=["series_dropped"]).to_string(index=False, float_format=fmt))
    print("dropped:", t.loc[t["half"] == "out", ["dropped", "series_dropped"]].to_string(index=False))
    print(f"out-of-sample per bet {v['oos_base']:+.2%}, without top series {v['oos_without_top1']:+.2%}; FRAGILE: {v['fragile']}")
    if args.select:
        print(select_by_history(b).to_string(index=False, float_format=fmt))
    return 0


if __name__ == "__main__":
    sys.exit(main())
