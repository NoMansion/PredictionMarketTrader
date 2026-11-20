"""What selling before settlement does to a rule: every exit policy of research/exits.py, side by side.

    python research/exit_study.py --tag nine --sample liquid \
        --categories "Economics,Politics,Elections,Science and Technology,World,Health,Companies,Commodities,Financials"
    python research/exit_study.py --tag ent --sample liquid --categories Entertainment \
        --rules "NO where YES is at 5-35c|no|mk"

For each rule and each policy, both halves (in sample = markets closing before 2026-04-01):
  bets, events, mean return per bet after fees on both legs, t clustered by event
  sold early      share of bets that were sold, and why (take profit, stop, time)
  hold            median days the money was tied up
  per cap-year    sum of returns / sum of years the money was tied up: what a dollar earns per year at work
  tail            losing events against the break-even loss rate, with the 95% upper bound (analyze_rule.tail)
  replay          research/portfolio.simulate at a 1% stake, the money given back at the exit: return a year, drawdown

The grid was fixed before any exit result was seen. With ~25 policies per rule, the best one looks good by luck:
the policy is chosen IN SAMPLE (best replay return a year at 1%), and only its out-of-sample figures count.
Writes research/results/exit_<tag>.csv.
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
from analyze_rule import find_rule, tail  # noqa: E402
from backtest import Panel  # noqa: E402
from exits import Exits, bets, policies, rule_rows, stats  # noqa: E402
from families import Features  # noqa: E402
from run_sweep import titles_for  # noqa: E402

NINE = "Economics,Politics,Elections,Science and Technology,World,Health,Companies,Commodities,Financials"
DEFAULT_RULES = ("NO at mid <= 5c, <= 30d, spread <= 5c|no|mk;NO at mid <= 5c, <= 30d, spread <= 5c|no|tk;"
                 "NO where YES is at 5-35c|no|mk;NO where YES is at 5-35c|no|tk")
DAY = 86400.0


def half(p: Panel, res, keep: np.ndarray, prefix: str, stake: float) -> dict:
    out = {}
    rows = res.rows[keep]
    if rows.size == 0:
        return {f"{prefix}_bets": 0}
    r = res.r[keep]
    ts = p.col("ts").astype("float64")[rows]
    hold = np.maximum((res.release[keep] - ts) / DAY, 1 / 24)
    why = res.reason[keep]
    ev = p.event[rows]
    t = tail(pd.Series(r).groupby(ev).sum().to_numpy())
    sub = type(res)(rows, r, res.release[keep], why, res.exit_px[keep], res.cost[keep])
    acct = portfolio.simulate(bets(p, sub), stake_frac=stake)
    out.update({f"{prefix}_bets": int(rows.size), f"{prefix}_events": int(np.unique(ev).size),
                f"{prefix}_ret": float(r.mean()), f"{prefix}_sold": float((why != "settle").mean()),
                f"{prefix}_take": float((why == "take").mean()), f"{prefix}_stop": float((why == "stop").mean()),
                f"{prefix}_time": float((why == "time").mean()), f"{prefix}_hold_med": float(np.median(hold)),
                f"{prefix}_per_capyear": float(r.sum() / (hold.sum() / 365.25)),
                f"{prefix}_lose_ev": t["losing"], f"{prefix}_breakeven": t["breakeven"], f"{prefix}_upper95": t["upper95"],
                f"{prefix}_tail_ok": bool(t["proven"]), f"{prefix}_cagr": acct.cagr, f"{prefix}_maxdd": acct.max_dd,
                f"{prefix}_work": acct.exposure})
    return out


def study(p: Panel, ex: Exits, mask, side: str, entry: str, stake: float) -> pd.DataFrame:
    rows = rule_rows(p, mask, side, entry)
    o = p.oos[rows]
    out = []
    for pol in policies():
        if pol.style == "mk" and pol.take_px is None and pol.take_gain is None:
            continue
        res = ex.run(rows, side, entry, pol)
        ins, oos = stats(p, res)
        d = {"policy": pol.name, "is_t": ins.t, "oos_t": oos.t}
        d.update(half(p, res, ~o, "is", stake))
        d.update(half(p, res, o, "oos", stake))
        out.append(d)
    return pd.DataFrame(out)


def show(df: pd.DataFrame) -> str:
    cols = [("policy", "policy"), ("is_ret", "in/bet"), ("is_t", "in t"), ("is_sold", "in sold"), ("is_cagr", "in/yr"),
            ("is_maxdd", "in dd"), ("is_tail_ok", "in tail"), ("oos_bets", "out bets"), ("oos_ret", "out/bet"),
            ("oos_t", "out t"), ("oos_sold", "out sold"), ("oos_take", "take"), ("oos_stop", "stop"),
            ("oos_hold_med", "hold d"), ("oos_per_capyear", "per cap-yr"), ("oos_lose_ev", "lose ev"),
            ("oos_tail_ok", "out tail"), ("oos_cagr", "out/yr"), ("oos_maxdd", "out dd")]
    t = df[[c for c, _ in cols if c in df]].rename(columns=dict(cols))
    pct = {"in/bet", "in sold", "in/yr", "in dd", "out/bet", "out sold", "take", "stop", "per cap-yr", "out/yr", "out dd"}
    fmt = {c: (lambda x: f"{x:+.2%}") if c in pct else (lambda x: f"{x:.2f}") for c in t.columns
           if t[c].dtype.kind == "f"}
    return t.to_string(index=False, formatters=fmt)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--db", default=str(panel.DB))
    ap.add_argument("--categories", default=NINE)
    ap.add_argument("--sample", default="liquid", choices=["random", "liquid"])
    ap.add_argument("--min-cumvol", type=float, default=None)
    ap.add_argument("--rules", default=DEFAULT_RULES, help="name|side|entry;...")
    ap.add_argument("--stake", type=float, default=0.01)
    args = ap.parse_args()
    cats = [c.strip() for c in args.categories.split(",") if c.strip()] or None
    df = panel.load(args.db, cats, sample=args.sample, min_cumvol=args.min_cumvol)
    print(panel.describe(df))
    if df.empty:
        return 1
    p = Panel(df)
    f = Features(p)
    titles = titles_for(df, args.db)
    ex = Exits(p)
    pd.set_option("display.width", 260, "display.max_colwidth", 46)
    tables = []
    for spec in [s for s in args.rules.split(";") if s.strip()]:
        name, side, entry = (x.strip() for x in spec.split("|"))
        family, mask = find_rule(f, titles, name, side, entry)
        t = study(p, ex, mask, side, entry, args.stake)
        t.insert(0, "rule", f"{name} | {side} | {entry}")
        tables.append(t)
        hold = t.iloc[0]
        print(f"\n=== [{family}] {name} | buy {side.upper()} | {'resting' if entry == 'mk' else 'taker'} "
              f"({int(hold['is_bets'])} bets in sample, {int(hold.get('oos_bets', 0))} out) ===")
        print(show(t))
        cand = t.iloc[1:]
        if len(cand) and cand["is_cagr"].notna().any():
            best = cand.loc[cand["is_cagr"].idxmax()]
            print(f"chosen in sample (best replay a year at {args.stake:.0%}): {best['policy']}: in {best['is_cagr']:+.2%}/y "
                  f"vs hold {hold['is_cagr']:+.2%}/y; OUT OF SAMPLE {best.get('oos_cagr', float('nan')):+.2%}/y vs hold "
                  f"{hold.get('oos_cagr', float('nan')):+.2%}/y, worst drawdown {best.get('oos_maxdd', float('nan')):.2%} "
                  f"vs {hold.get('oos_maxdd', float('nan')):.2%}, per bet {best.get('oos_ret', float('nan')):+.2%} vs "
                  f"{hold.get('oos_ret', float('nan')):+.2%}")
    out = pd.concat(tables, ignore_index=True)
    (HERE / "results").mkdir(exist_ok=True)
    path = HERE / "results" / f"exit_{args.tag}.csv"
    out.round(5).to_csv(path, index=False)
    print(f"\n-> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
