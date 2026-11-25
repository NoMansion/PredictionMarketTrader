"""Why do the observation logs' resting NO bids fill less often than the backtest says? (the user, 2026-11-24:
"Test as many things as you can"; data/shadow_ent.db showed 95 of 194 filled, 49%, against the backtest's 69-80%)

Re-decides every decided observation from the market's FULL public trade record over its three-day window, under
two rules, and compares both with what the log recorded:

  queue    the log's own rule (scripts/shadow_longshot.resting_fill): a YES buyer trades ABOVE the order's YES price
           L (1 - the NO bid), or YES buyers trade AT L at least everything queued ahead at the observation plus the
           order. It assumes nobody queued ahead ever cancels, so it is a lower bound.
  through  the level was cleared, by anyone: a YES buyer above L, or a trade at L or above in which the taker bought
           NO (the resting side was a YES bid at L or higher, which can only rest once every offer at L, the order
           included, is gone); or the queue rule. This is the backtest's condition (a later bar's YES bid reaching L,
           or a print above it) read from trades instead of daily bars: a bid that reached L without a trade is not
           seen here, so it is still a lower bound for the backtest's rule.

    python research/fill_audit.py                 both logs (data/shadow.db, data/shadow_ent.db)
    python research/fill_audit.py --log ent --csv research/results/fill_audit.csv

Public endpoints only, about one request per observation. No orders, no Claude.
"""
import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.kalshi_http import KalshiError, KalshiHTTP  # noqa: E402

REST_HOURS = 72.0
LOGS = {"5c": ROOT / "data" / "shadow.db", "ent": ROOT / "data" / "shadow_ent.db"}
EPS = 1e-9


def ts(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp()
    except (TypeError, ValueError):
        return None


def decide(trades: list[dict], level: float, need: float | None) -> dict:
    """First fill time under each rule (None = not filled). `level` = the order's YES price (the YES ask at the
    observation); `need` = contracts queued ahead plus the order (None: not recorded, then only a trade through)."""
    out = {"queue": None, "through": None}
    at = 0.0
    for t in sorted(trades, key=lambda t: t.get("created_time") or ""):
        try:
            px, n, side = float(t["yes_price_dollars"]), float(t["count_fp"]), t.get("taker_side")
        except (KeyError, TypeError, ValueError):
            continue
        when = ts(t.get("created_time"))
        if side == "yes":
            if px > level + EPS:
                hit = True
            elif abs(px - level) <= EPS:
                at += n
                hit = need is not None and at >= need - EPS
            else:
                hit = False
            if hit:
                out["queue"] = out["queue"] or when
                out["through"] = out["through"] or when
        elif side == "no" and px >= level - EPS:        # a YES bid rested at L or above: the level was cleared
            out["through"] = out["through"] or when
        if out["queue"] and out["through"]:
            break
    return out


def audit(log: str, db_path: Path, k: KalshiHTTP, max_pages: int = 200) -> list[dict]:
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = db.execute("SELECT ticker, seen_ts, end_ts, yes_ask, rest_px, rest_ahead, stake, rest_filled, result FROM obs "
                      "WHERE rest_done = 1 ORDER BY seen_ts").fetchall()
    db.close()
    out = []
    for ticker, seen, end, yes_ask, rest_px, ahead, stake, logged, result in rows:
        until = min(seen + REST_HOURS * 3600, end or 9e18)
        try:
            trades = list(k.pages("/markets/trades", "trades", max_pages=max_pages, tries=3, ticker=ticker,
                                  min_ts=int(seen), max_ts=int(until)))
        except KalshiError as e:
            print(f"{ticker}: {e}", file=sys.stderr)
            continue
        need = None if ahead is None or not rest_px else ahead + stake / rest_px
        d = decide(trades, yes_ask, need)
        out.append({"log": log, "ticker": ticker, "seen_ts": seen, "level": yes_ask, "ahead": ahead, "trades": len(trades),
                    "over_5000": len(trades) > 5000, "logged": logged, "queue": int(d["queue"] is not None),
                    "through": int(d["through"] is not None), "result": result or ""})
    return out


def summary(rows: list[dict]) -> str:
    lines = []
    for log in sorted({r["log"] for r in rows}):
        rs = [r for r in rows if r["log"] == log]
        n = len(rs)
        f = lambda key: sum(int(r[key]) for r in rs)
        lines.append(f"[{log}] {n} decided orders: logged filled {f('logged')} ({f('logged') / n:.0%}); full trade record: "
                     f"queue rule {f('queue')} ({f('queue') / n:.0%}), through rule {f('through')} ({f('through') / n:.0%}); "
                     f"windows over 5,000 trades {f('over_5000')}")
        diff = [r for r in rs if r["logged"] != r["queue"]]
        if diff:
            lines.append(f"    logged against the queue rule on the full record: {len(diff)} differ "
                         f"({sum(1 for r in diff if r['queue'])} fills the log missed)")
        settled = [r for r in rs if r["result"] in ("yes", "no")]
        for name, sel in (("filled by the queue rule", lambda r: r["queue"]),
                          ("filled only by the through rule", lambda r: r["through"] and not r["queue"]),
                          ("not filled by either", lambda r: not r["through"])):
            s = [r for r in settled if sel(r)]
            if s:
                lines.append(f"    settled, {name}: {len(s)}, YES won (the NO bet lost) {sum(1 for r in s if r['result'] == 'yes')}")
    return "\n".join(lines)


def backtest_rates(df, mask, side: str = "no") -> dict:
    """The backtest's own fill rates for a resting order of the rule, two ways: the FIRST bar of each market on which
    the rule held (Panel.fill_rate, the "69% to 80%" quoted beside the logs), and ANY bar on which it held (what an
    observation at a random moment of a market's time in the band sees, as the logs do). With the share of markets
    that fill on some bar: the backtest's bets are each market's first FILLED bar, so an unfilled order is placed
    again on the next qualifying bar, as the paper rule accounts do."""
    import numpy as np
    from backtest import Panel
    p = Panel(df)
    q = df["quoted"].to_numpy(bool)
    ok = p.ok[(side, "mk")]
    placed = p.first_per_market(mask & q)
    any_bar = np.flatnonzero(mask & q)
    filled_ever = p.first_per_market(mask & q & ok)
    return {"markets": int(placed.size), "first_bar": float(ok[placed].mean()) if placed.size else float("nan"),
            "any_bar": float(ok[any_bar].mean()) if any_bar.size else float("nan"), "bars": int(any_bar.size),
            "ever": float(filled_ever.size / placed.size) if placed.size else float("nan")}


def backtest_table(rule: str, categories: list[str], levels: list[float]) -> str:
    sys.path.insert(0, str(ROOT / "research"))
    import panel
    from analyze_rule import find_rule, titles_for
    from families import Features
    from backtest import Panel
    lines = [f"backtest fill rates of a resting NO bid, \"{rule}\", {', '.join(categories)} (3 daily bars):"]
    for fill in ("quote", "trade"):
        panel.set_fill(fill)
        for lv in levels:
            df = panel.load(panel.DB, categories, sample="liquid", min_cumvol=lv)
            if df.empty:
                lines.append(f"  {fill:5s} {lv:>8,.0f}: no sample")
                continue
            _, mask = find_rule(Features(Panel(df)), titles_for(df, panel.DB), rule, "no", "mk")
            r = backtest_rates(df, mask)
            lines.append(f"  fill={fill:5s} at {lv:>7,.0f}: {r['markets']:,} markets; first bar {r['first_bar']:.0%}, "
                         f"any bar {r['any_bar']:.0%} ({r['bars']:,} bars), filled on some bar {r['ever']:.0%}")
    panel.set_fill("quote")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", choices=["5c", "ent", "both"], default="both")
    ap.add_argument("--csv", default=None)
    ap.add_argument("--interval", type=float, default=0.5)
    ap.add_argument("--backtest", action="store_true", help="instead: the backtest's fill rates (no network)")
    args = ap.parse_args()
    if args.backtest:
        print(backtest_table("NO where YES is at 5-35c", ["Entertainment"], [5000, 20000]))
        print(backtest_table("NO at mid <= 5c, <= 30d, spread <= 5c",
                             ["Economics", "Politics"], [45000]))
        return 0
    k = KalshiHTTP(min_interval=args.interval)
    rows = []
    for log in (["5c", "ent"] if args.log == "both" else [args.log]):
        rows += audit(log, LOGS[log], k)
    print(summary(rows))
    if args.csv and rows:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
