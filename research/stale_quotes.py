"""Ideas queue 61 (report 3.78): stale quotes in the Entertainment band. A band bar is STALE(k) when its YES mid equals
the mid of each of the market's k earlier bars in the loaded sample (nobody re-priced it), MOVED when it differs from
any of them, NEW when the market has fewer than k earlier bars. Each group takes the first bar per market inside it,
so a market can be in several groups. Pre-stated split, k = 3 and 7, resting, Entertainment.

    .venv/Scripts/python.exe research/stale_quotes.py 20000
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import numpy as np
import pandas as pd

STALE, MOVED, NEW = 1, 0, -1


def stale_flags(ticker: np.ndarray, mid: np.ndarray, k: int, tol: float = 1e-6) -> np.ndarray:
    """Per bar (rows sorted by ticker, then time): STALE, MOVED or NEW against the market's k earlier bars.
    A missing mid (NaN) on the bar or an earlier one counts as a move."""
    s = pd.Series(np.asarray(mid, dtype="float64"))
    g = s.groupby(np.asarray(ticker), sort=False)
    same = np.ones(len(s), dtype=bool)
    have = np.ones(len(s), dtype=bool)
    for j in range(1, k + 1):
        prev = g.shift(j).to_numpy()
        have &= ~np.isnan(prev) | (g.cumcount().to_numpy() >= j)
        same &= np.abs(s.to_numpy() - prev) <= tol  # NaN compares False: a move
    out = np.where(same, STALE, MOVED)
    out[g.cumcount().to_numpy() < k] = NEW
    return out


def main() -> int:
    import panel
    from backtest import Panel
    from families import Features
    from analyze_rule import find_rule, bets_frame, report
    from run_sweep import titles_for
    pd.set_option("display.width", 200)
    mc = float(sys.argv[1]) if len(sys.argv) > 1 else 20000
    df = panel.load(str(panel.DB), ["Entertainment"], sample="liquid", min_cumvol=mc)
    print(panel.describe(df).splitlines()[0])
    p = Panel(df); f = Features(p)
    _, mask = find_rule(f, titles_for(df, str(panel.DB)), "NO where YES is at 5-35c", "no", "mk")
    for k in (3, 7):
        fl = stale_flags(p.df["ticker"].to_numpy(), p.df["mid"].to_numpy(), k)
        for name, g in (("STALE", STALE), ("MOVED", MOVED), ("NEW", NEW)):
            m = mask & (fl == g)
            print(f"\n===== k={k} {name} (first band bar per market in the group), min_cumvol {mc:g}")
            print(report(bets_frame(p, m, "no", "mk"), p, m, "no", "mk"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
