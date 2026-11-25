"""Ideas queue 72, 73, 75 and 79 (reports 3.88-3.91): the pre-stated cuts of the Entertainment band at 20,000, resting
at the best NO bid for 3 daily bars (research/resting_variants.variant, the engine of 3.73's +37.8%/y, 7.0% DD baseline).

    72  spread 2c+ at entry (a market's first band bar with spread >= 2c)
    73  late entrants: markets with 5+ bars in the sample before their first band bar, against the rest
    75  skip STALE(3) bars (research/stale_quotes.stale_flags): the market's first non-stale band bar
    79  events listing 4+ markets AT THE BAR (markets of the event with open_ts <= the bar's ts; not ev_total, which
        counts every market the event ever listed); plus the 10-25c fall rule (5,000) on the same cut, as a record

    .venv/Scripts/python.exe research/band_prestated.py 72
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))


def listed_at_bar(event: np.ndarray, ts: np.ndarray, opens: dict) -> np.ndarray:
    """Markets of each row's event whose open_ts <= the row's ts. opens: event -> array of open_ts (any order)."""
    out = np.zeros(len(event), dtype="int32")
    srt = {e: np.sort(np.asarray(v, dtype="float64")) for e, v in opens.items()}
    for e in pd.unique(event):
        idx = np.flatnonzero(event == e)
        o = srt.get(e)
        if o is not None:
            out[idx] = np.searchsorted(o, ts[idx].astype("float64"), side="right")
    return out


def bars_before_first(ticker: np.ndarray, mask: np.ndarray) -> dict:
    """Per market: how many of its bars (rows sorted by ticker, then time) come before its first masked bar."""
    cc = pd.Series(np.arange(len(ticker))).groupby(ticker, sort=False).cumcount().to_numpy()
    first = pd.Series(cc[mask]).groupby(ticker[mask], sort=False).first()
    return first.to_dict()


def main() -> int:
    import panel
    from backtest import Panel
    from families import Features
    from analyze_rule import find_rule
    from resting_variants import variant, describe
    from run_sweep import titles_for
    from stale_quotes import stale_flags, STALE
    item = sys.argv[1]
    pd.set_option("display.width", 250)
    mc = 5000 if item == "79f" else 20000
    df = panel.load(str(panel.DB), ["Entertainment"], sample="liquid", min_cumvol=mc)
    print(panel.describe(df).splitlines()[0])
    p = Panel(df); f = Features(p); d = p.df
    rule = "NO where YES is at 5-35c"
    if item == "79f":
        cell = f.base & (f.mid >= 0.10) & (f.mid < 0.25)
        band = cell & (f.mom[7] <= -0.03)
    else:
        _, band = find_rule(f, titles_for(df, str(panel.DB)), rule, "no", "mk")
    rows = {"whole": band}
    if item == "72":
        rows["spread 2c+"] = band & (f.spread >= 0.02 - 1e-6)
    elif item == "73":
        bb = bars_before_first(d["ticker"].to_numpy(), band)
        late = d["ticker"].map(lambda t: bb.get(t, -1) >= 5).to_numpy()
        fall = f.mom[7] <= -0.03
        rows.update({"late (5+ bars before)": band & late, "early (<5 bars)": band & ~late,
                     "late, 3c+ fall in 7d": band & late & fall, "late, no such fall": band & late & ~fall})
    elif item == "75":
        fl = stale_flags(d["ticker"].to_numpy(), d["mid"].to_numpy(), 3)
        rows["skip STALE(3)"] = band & (fl != STALE)
    elif item in ("79", "79f"):
        import sqlite3
        con = sqlite3.connect(str(panel.DB))
        ev = pd.read_sql_query("SELECT event, open_ts FROM markets WHERE open_ts IS NOT NULL", con)
        opens = {e: g.to_numpy() for e, g in ev.groupby("event")["open_ts"]}
        n = listed_at_bar(d["event"].to_numpy(), d["ts"].to_numpy(), opens)
        rows["4+ listed at bar"] = band & (n >= 4)
        rows["1-3 listed at bar"] = band & (n < 4)
        print(f"ev_total >= 4 on band bars {np.mean(f.ev_total[band] >= 4):.1%}; listed-at-bar >= 4 {np.mean(n[band] >= 4):.1%}")
    if item == "80":
        import portfolio
        bb = bars_before_first(d["ticker"].to_numpy(), band)
        b = variant(p, band, 0.0, 3)
        late = b["ticker"].map(lambda t: bb.get(t, -1) >= 5).to_numpy()
        for label, part, lt in (("in", b[~b["oos"]], late[~b["oos"].to_numpy()]), ("out", b[b["oos"]], late[b["oos"].to_numpy()])):
            for mult in (1.0, 2.0):
                x = part[["ts", "close", "r", "event"]].copy()
                x["m"] = np.where(lt, mult, 1.0)
                x = x.sort_values("ts").to_numpy("float64")
                x[:, 1] = np.maximum(x[:, 1], x[:, 0] + 86400)
                a = portfolio.simulate(x, stake_frac=0.01)
                print(f"{label}: late stake x{mult:g}: {len(x)} bets ({int(lt.sum())} late), replay {a.cagr:+.1%}/y, worst DD {a.max_dd:.1%}")
        return 0
    out = []
    for name, m in rows.items():
        b = variant(p, m, 0.0, 3)
        if len(b):
            r = {"cut": name, **describe(b)}
            if item == "73":
                first = p.first_per_market(m)
                r["median $/day at entry"] = float(np.nanmedian(d["vol"].to_numpy()[first] * (1 - d["mid"].to_numpy()[first])))
            out.append(r)
    fmt = {c: "{:+.2%}".format for c in ("mean", "in_mean", "out_mean", "in_cagr", "out_cagr")}
    fmt.update({"fill": "{:.0%}".format, "price": "{:.3f}".format, "in_dd": "{:.1%}".format, "out_dd": "{:.1%}".format})
    print(pd.DataFrame(out).to_string(index=False, formatters=fmt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
