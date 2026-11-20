"""One table over every exit study written so far (research/results/exit_<tag>.csv): per sample and rule, holding
to settlement against the exit policy chosen IN SAMPLE, judged out of sample, and how the families of exits did.

    python research/exit_summary.py
"""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def family(policy: str) -> str:
    if policy.startswith("hold"):
        return "hold"
    if "+ stop" in policy:
        return "take+stop"
    if policy.startswith("take"):
        return "take"
    if policy.startswith("stop"):
        return "stop"
    return "time"


def main() -> int:
    rows = []
    for path in sorted((HERE / "results").glob("exit_*.csv")):
        tag = path.stem[5:]
        df = pd.read_csv(path)
        for rule, t in df.groupby("rule", sort=False):
            hold = t[t["policy"].str.startswith("hold")].iloc[0]
            cand = t[~t["policy"].str.startswith("hold")]
            best = cand.loc[cand["is_cagr"].idxmax()] if cand["is_cagr"].notna().any() else None
            fam = cand.assign(fam=cand["policy"].map(family)).groupby("fam")
            d = {"sample": tag, "rule": rule.replace("NO at mid <= 5c, <= 30d, spread <= 5c", "5-cent rule")
                 .replace("NO where YES is at 5-35c", "NO vs YES 5-35c"),
                 "out bets": int(hold.get("oos_bets", 0) or 0),
                 "hold in/bet": hold["is_ret"], "hold out/bet": hold.get("oos_ret"),
                 "hold out/yr": hold.get("oos_cagr"), "hold out dd": hold.get("oos_maxdd"),
                 "hold out tail": hold.get("oos_tail_ok")}
            if best is not None:
                d.update({"chosen in sample": best["policy"], "its out/bet": best.get("oos_ret"),
                          "its out/yr": best.get("oos_cagr"), "its out dd": best.get("oos_maxdd")})
            for name, g in fam:
                d[f"{name}: beat hold out/bet"] = f"{int((g['oos_ret'] > hold.get('oos_ret')).sum())}/{len(g)}"
            rows.append(d)
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 320, "display.max_columns", 40, "display.max_colwidth", 40)
    pct = [c for c in out.columns if "/bet" in c and "beat" not in c or "/yr" in c or " dd" in c]
    print(out.to_string(index=False, formatters={c: (lambda x: "" if pd.isna(x) else f"{x:+.2%}") for c in pct}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
