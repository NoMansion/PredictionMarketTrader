"""Several rules in ONE account: does putting the survivors together help, and what does an exit rule do there?

    python research/combined.py
    python research/combined.py --stakes 0.005,0.01,0.02 --exit "take at bid >= 0.98, resting"
    python research/combined.py --five-cumvol 45000      # the 5-cent nine-category leg on 45,000+ markets only

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


def thin(res: Result, rate: float, rng: np.random.Generator) -> Result:
    """Keep each bet with probability `rate` (queue item 62: the paper fill rates of the observation logs)."""
    k = rng.random(res.rows.size) < rate
    return Result(res.rows[k], res.r[k], res.release[k], res.reason[k], res.exit_px[k], res.cost[k])


def leg_level(df: pd.DataFrame, min_cumvol: float) -> np.ndarray:
    """Bars at which the market had traded at least `min_cumvol` contracts so far (known at the bar, rule 0)."""
    return df["cumvol"].to_numpy("float64") >= float(min_cumvol)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(panel.DB))
    ap.add_argument("--stakes", default="0.005,0.01,0.02")
    ap.add_argument("--exit", default="", help="an exit policy name from research/exits.policies() (default: hold)")
    ap.add_argument("--min-cumvol", type=float, default=None,
                    help="census level for every leg (default: the lowest complete level, which falls to 1 contract "
                         "once a category's random pass is finished: pass 5000 to compare with reports 3.22-3.35)")
    ap.add_argument("--five-cumvol", type=float, default=None,
                    help="the 5-cent nine-category leg only on bars where the market has traded this many contracts "
                         "(report 3.7's 45,000 level); the other legs keep the default level")
    ap.add_argument("--draws", type=int, default=0,
                    help="queue item 62: also run this many draws with fills thinned at random (1%% stake only)")
    ap.add_argument("--fill-five", type=float, default=0.65, help="fill rate kept for the 5-cent legs in the draws")
    ap.add_argument("--fill-wide", type=float, default=0.49, help="fill rate kept for the 5-35c legs in the draws")
    args = ap.parse_args()
    cats = sorted({c for leg in LEGS for c in leg[4]})
    df = panel.load(args.db, cats, sample="liquid", min_cumvol=args.min_cumvol)
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
    for i, (label, name, side, entry, leg_cats) in enumerate(LEGS):
        _, mask = find_rule(f, titles, name, side, entry)
        mask = mask & np.isin(catcol, leg_cats)
        if i == 0 and args.five_cumvol is not None:
            mask = mask & leg_level(df, args.five_cumvol)
            label = f"{label}, {args.five_cumvol:,.0f}+"
        legs.append((label, ex.run(rule_rows(p, mask, side, entry), side, entry, pol)))
    out = []
    combos = [(label, [res]) for label, res in legs]
    combos.append(("ALL FOUR LEGS in one account", [res for _, res in legs]))
    combos.append(("the first three legs", [res for _, res in legs[:3]]))
    combos.append(("5-cent nine + NO 5-35c Entertainment", [legs[0][1], legs[1][1]]))
    combos.append(("the other three legs (no 5-cent nine)", [res for _, res in legs[1:]]))
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
    if args.draws:
        rng = np.random.default_rng(62)
        rates = [args.fill_five if leg[1] == FIVE else args.fill_wide for leg in LEGS]
        rows = []
        for d in range(args.draws):
            thinned = [thin(res, rate, rng) for (_, res), rate in zip(legs, rates)]
            dc = [(label, [thinned[i]]) for i, (label, _) in enumerate(legs)]
            dc += [("ALL FOUR LEGS in one account", thinned), ("the first three legs", thinned[:3]),
                   ("5-cent nine + NO 5-35c Entertainment", [thinned[0], thinned[1]])]
            for label, parts in dc:
                a, o = account(p, first_per_market(p, merge(parts)), 0.01)
                rows.append({"draw": d, "account": label, "in/yr": a.cagr, "in dd": a.max_dd, "out/yr": o.cagr,
                             "out dd": o.max_dd})
        dr = pd.DataFrame(rows)
        q = dr.groupby("account", sort=False)[["in/yr", "in dd", "out/yr", "out dd"]].quantile([0.05, 0.5, 0.95]).unstack()
        print(f"\n{args.draws} draws, fills kept: 5-cent {args.fill_five:.0%}, 5-35c {args.fill_wide:.0%}; stake 1%; "
              "5th / 50th / 95th percentile")
        print((q * 100).round(1).to_string())
        lv = (f"_min{args.min_cumvol:.0f}" if args.min_cumvol is not None else "") + (
            f"_five{args.five_cumvol:.0f}" if args.five_cumvol is not None else "")
        q.round(5).to_csv(HERE / "results" / f"combined_fill{lv}_draws{args.draws}.csv")
    t = pd.DataFrame(out)
    pd.set_option("display.width", 260, "display.max_colwidth", 48)
    pct = ["in/bet", "out/bet", "in/yr", "in dd", "in at work", "out/yr", "out dd", "out at work"]
    print(f"\nexit policy: {pol.name}")
    print(t.to_string(index=False, formatters={**{c: (lambda x: f"{x:+.2%}") for c in pct},
                                               "in sharpe": "{:.2f}".format, "out sharpe": "{:.2f}".format,
                                               "out years": "{:.2f}".format}))
    tag = "hold" if pol is HOLD else "".join(ch if ch.isalnum() else "_" for ch in pol.name)[:40]
    if args.min_cumvol is not None:
        tag += f"_min{args.min_cumvol:.0f}"
    if args.five_cumvol is not None:
        tag += f"_five{args.five_cumvol:.0f}"
    path = HERE / "results" / f"combined_{tag}.csv"
    t.round(5).to_csv(path, index=False)
    print(f"-> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
