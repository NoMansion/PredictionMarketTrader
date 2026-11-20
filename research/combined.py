"""Several rules in ONE account: does putting the survivors together help, and what does an exit rule do there?

    python research/combined.py
    python research/combined.py --stakes 0.005,0.01,0.02 --exit "take at bid >= 0.98, resting"

The legs (rule, side, entry, categories) are fixed below, from reports 3.22 to 3.27: the 5-cent rule resting on the
nine categories where it was tested pooled, and the wide NO rule resting where it was a lead (Entertainment, with
Climate and Weather as the same-signed echo). Each leg alone, then all of them in one account: a market is
entered once (by whichever leg saw it first), stakes are a fraction of the account's equity, capped per event and
by the cash on hand, and the money comes back at the exit or the close (research/portfolio.simulate).
In-sample and out-of-sample periods are simulated separately, each from a fresh bankroll.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import panel  # noqa: E402
import portfolio  # noqa: E402
from analyze_rule import find_rule  # noqa: E402
from backtest import Panel  # noqa: E402
from exits import HOLD, Exits, Result, bets, policies, rule_rows  # noqa: E402
from families import Features  # noqa: E402
from run_sweep import titles_for  # noqa: E402

NINE = ["Economics", "Politics", "Elections", "Science and Technology", "World", "Health", "Companies", "Commodities",
        "Financials"]
FIVE = "NO at mid <= 5c, <= 30d, spread <= 5c"
WIDE = "NO where YES is at 5-35c"
LEGS = [
    ("5-cent rule, nine categories, resting", FIVE, "no", "mk", NINE),
    ("NO vs YES 5-35c, Entertainment, resting", WIDE, "no", "mk", ["Entertainment"]),
    ("NO vs YES 5-35c, Climate and Weather, resting", WIDE, "no", "mk", ["Climate and Weather"]),
    ("5-cent rule, Entertainment, resting", FIVE, "no", "mk", ["Entertainment"]),
]


def merge(results: list[Result]) -> Result:
    """One bet per market across legs: the earliest entry wins."""
    if not results:
        z = np.zeros(0)
        return Result(np.zeros(0, "int64"), z, z, np.zeros(0, dtype=object), z, z)
    rows = np.concatenate([r.rows for r in results])
    keys = {k: np.concatenate([getattr(r, k) for r in results]) for k in ("r", "release", "reason", "exit_px", "cost")}
    return Result(rows, **keys)


def first_per_market(p: Panel, res: Result) -> Result:
    order = np.argsort(res.rows, kind="stable")                 # rows are ordered by market, then time
    rows = res.rows[order]
    t = p.ticker[rows]
    keep = np.ones(rows.size, bool)
    keep[1:] = t[1:] != t[:-1]
    idx = order[keep]
    return Result(res.rows[idx], res.r[idx], res.release[idx], res.reason[idx], res.exit_px[idx], res.cost[idx])


def account(p: Panel, res: Result, stake: float) -> tuple[portfolio.Account, portfolio.Account]:
    o = p.oos[res.rows]
    a = [Result(res.rows[k], res.r[k], res.release[k], res.reason[k], res.exit_px[k], res.cost[k]) for k in (~o, o)]
    return portfolio.simulate(bets(p, a[0]), stake_frac=stake), portfolio.simulate(bets(p, a[1]), stake_frac=stake)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(panel.DB))
    ap.add_argument("--stakes", default="0.005,0.01,0.02")
    ap.add_argument("--exit", default="", help="an exit policy name from research/exits.policies() (default: hold)")
    args = ap.parse_args()
    cats = sorted({c for leg in LEGS for c in leg[4]})
    df = panel.load(args.db, cats, sample="liquid")
    print(panel.describe(df))
    p = Panel(df)
    f = Features(p)
    titles = titles_for(df, args.db)
    ex = Exits(p)
    pol = next((x for x in policies() if x.name == args.exit), None) if args.exit else HOLD
    if pol is None:                    # an unknown name must not quietly become "hold" and overwrite its results
        raise SystemExit(f"unknown exit policy {args.exit!r}; known: " + "; ".join(x.name for x in policies()))
    catcol = df["category"].to_numpy(object)
    legs = []
    for label, name, side, entry, leg_cats in LEGS:
        _, mask = find_rule(f, titles, name, side, entry)
        mask = mask & np.isin(catcol, leg_cats)
        legs.append((label, ex.run(rule_rows(p, mask, side, entry), side, entry, pol)))
    out = []
    combos = [(label, [res]) for label, res in legs]
    combos.append(("ALL FOUR LEGS in one account", [res for _, res in legs]))
    combos.append(("the first three legs", [res for _, res in legs[:3]]))
    combos.append(("5-cent nine + NO 5-35c Entertainment", [legs[0][1], legs[1][1]]))
    for stake in [float(s) for s in args.stakes.split(",")]:
        for label, parts in combos:
            res = first_per_market(p, merge(parts))
            a, o = account(p, res, stake)
            oo = p.oos[res.rows]
            out.append({"stake": stake, "account": label, "bets in": int((~oo).sum()), "bets out": int(oo.sum()),
                        "in/bet": float(res.r[~oo].mean()) if (~oo).any() else np.nan,
                        "out/bet": float(res.r[oo].mean()) if oo.any() else np.nan,
                        "in/yr": a.cagr, "in dd": a.max_dd, "in sharpe": a.sharpe, "in at work": a.exposure,
                        "out/yr": o.cagr, "out dd": o.max_dd, "out sharpe": o.sharpe, "out at work": o.exposure,
                        "out years": o.years})
    t = pd.DataFrame(out)
    pd.set_option("display.width", 260, "display.max_colwidth", 48)
    pct = ["in/bet", "out/bet", "in/yr", "in dd", "in at work", "out/yr", "out dd", "out at work"]
    print(f"\nexit policy: {pol.name}")
    print(t.to_string(index=False, formatters={**{c: (lambda x: f"{x:+.2%}") for c in pct},
                                               "in sharpe": "{:.2f}".format, "out sharpe": "{:.2f}".format,
                                               "out years": "{:.2f}".format}))
    tag = "hold" if pol is HOLD else "".join(ch if ch.isalnum() else "_" for ch in pol.name)[:40]
    path = HERE / "results" / f"combined_{tag}.csv"
    t.round(5).to_csv(path, index=False)
    print(f"-> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
