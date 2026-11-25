"""Splits of a rule's bets, each half, with the event tail test (Ideas queue 68, 69, 71; reports 3.83 on).

    python research/band_splits.py --split life                 # band (Entertainment, 20,000): new against old series
    python research/band_splits.py --split per_event            # band: events with 1, 2-3, 4+ bets
    python research/band_splits.py --split per_event --rule "mid 10-25c, down 3c+ in 7d" --min-cumvol 5000

life: a bet is "new series" when the series' first market (any market of it in the history) opened within 30 days
before the bet; known at the bar, since that market had already opened.
"""
import argparse
import sqlite3
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


def per_event_group(b: pd.DataFrame) -> pd.Series:
    n = b.groupby("event")["r"].transform("size")
    return pd.cut(n, [0, 1, 3, 10 ** 9], labels=["1 bet", "2-3 bets", "4+ bets"]).astype(str)


def life_group(b: pd.DataFrame, first_open: dict, days: float = 30.0) -> pd.Series:
    fo = b["series"].map(first_open).astype("float64")
    return np.where((b["ts"] - fo) <= days * 86400, "new series (<=30d)", "older series")


def table(b: pd.DataFrame, group: pd.Series) -> pd.DataFrame:
    rows = []
    for (g, oos), part in b.groupby([np.asarray(group), b["oos"].to_numpy()]):
        ev = part.groupby("event")["r"].sum().to_numpy()
        t = tail(ev)
        rows.append({"group": g, "half": "out" if oos else "in", "bets": len(part), "events": t["events"],
                     "per bet": part["r"].mean(), "event sum mean": ev.mean(), "losing events": t["losing"],
                     "upper95": t["upper95"], "breakeven": t["breakeven"], "tail": "passes" if t["proven"] else "fails",
                     "median $7d": part["dvol7"].median()})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", required=True, choices=["life", "per_event"])
    ap.add_argument("--rule", default="NO where YES is at 5-35c")
    ap.add_argument("--categories", default="Entertainment")
    ap.add_argument("--min-cumvol", type=float, default=20000)
    ap.add_argument("--db", default=str(panel.DB))
    args = ap.parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()]
    df = panel.load(args.db, cats, sample="liquid", min_cumvol=args.min_cumvol)
    print(panel.describe(df))
    p = Panel(df)
    f = Features(p)
    _, mask = find_rule(f, titles_for(df, args.db), args.rule, "no", "mk")
    b = bets_frame(p, mask, "no", "mk")
    if args.split == "life":
        with sqlite3.connect(args.db) as con:
            fo = dict(con.execute("SELECT series, MIN(open_ts) FROM markets GROUP BY series").fetchall())
        g = life_group(b, fo)
    else:
        g = per_event_group(b)
    t = table(b, pd.Series(g, index=b.index))
    pd.set_option("display.width", 220)
    print(f"\n{args.rule} | NO resting | {args.min_cumvol:,.0f}+ | split {args.split}; last close "
          f"{pd.to_datetime(b['close_ts'].max(), unit='s').date()}")
    print(t.to_string(index=False, formatters={"per bet": "{:+.2%}".format, "event sum mean": "{:+.3f}".format,
                                               "upper95": "{:.1%}".format, "breakeven": "{:.1%}".format,
                                               "median $7d": "{:,.0f}".format}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
