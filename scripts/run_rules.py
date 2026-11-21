"""Run the mechanical paper accounts of rules.yaml (src/rules.py): price rules from the Kalshi history, traded on
paper. No Claude calls. The paper loop runs it after every cycle.

    python scripts/run_rules.py                     every account in rules.yaml
    python scripts/run_rules.py --only rule_5c_busy
    python scripts/run_rules.py --report            where every account stands, nothing run

Exit codes: 0 done, 3 skipped (quiet window, a cycle is running, low memory), 1 every account failed.
"""
import argparse
import sys
import time

from _bootstrap import ROOT

from src import runtime
from src.config import load_config
from src.kalshi import Kalshi
from src.ledger import Ledger
from src.rules import kalshi_candles, load_rules, run_rules
from src.variants import standings


def settled_stats(path) -> dict:
    """Bets that have settled: how many, how many lost, dollars in and out (fees included)."""
    if not path.exists():
        return {"n": 0}
    led = Ledger(path)
    try:
        rows = led.q("""SELECT market_id,
                               SUM(CASE WHEN side='BUY' THEN price * shares + fee ELSE 0 END) AS cost,
                               SUM(CASE WHEN side='SETTLE' THEN price * shares ELSE 0 END) AS paid
                        FROM fills GROUP BY market_id
                        HAVING SUM(CASE WHEN side='SETTLE' THEN 1 ELSE 0 END) > 0""")
    finally:
        led.close()
    cost = sum(float(r["cost"] or 0) for r in rows)
    paid = sum(float(r["paid"] or 0) for r in rows)
    return {"n": len(rows), "lost": sum(1 for r in rows if float(r["paid"] or 0) < float(r["cost"] or 0) - 1e-9),
            "cost": cost, "paid": paid}


def report(accounts) -> int:
    rows = standings(ROOT, {n: {"about": a.about} for n, a in accounts.items()}, folder="rules", with_main=False)
    print(f"{'account':22s} {'equity':>9s} {'P&L':>8s} {'open':>4s} {'resting':>7s} {'filled':>6s} {'expired':>7s} "
          f"{'settled':>7s} {'lost':>4s} {'per $':>7s}  since")
    for r in rows:
        if r.get("started") is None:
            print(f"{r['account']:22s} not started yet")
            continue
        s = settled_stats(ROOT / "data" / "rules" / f"{r['account']}.db")
        per = f"{s['paid'] / s['cost'] - 1:+.1%}" if s["n"] and s["cost"] > 0 else "-"
        since = time.strftime("%m-%d %I:%M %p", time.localtime(r["started"]))
        print(f"{r['account']:22s} {r['equity']:9.2f} {r['equity'] - r['deposited']:+8.2f} {r['positions']:4d} {r['resting']:7d} "
              f"{r['filled']:6d} {r['expired']:7d} {s['n']:7d} {s.get('lost', 0):4d} {per:>7s}  {since}")
    print("\nMechanical rules, no Claude. Equity values open positions at the bid; 'per $' is the return on the dollars"
          "\nstaked in settled bets, fees included. Accounts marked CONTROL should lose if the busy-market effect is real.")
    for r in rows:
        print(f"  {r['account']}: {r['about']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--rules", default=str(ROOT / "rules.yaml"))
    ap.add_argument("--only", default="", help="comma-separated account names")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--pace", type=float, default=0.6, help="seconds between requests")
    ap.add_argument("--listing-hours", type=float, default=6.0, help="how long one listing of open markets is reused")
    args = ap.parse_args()
    cfg = load_config(args.config)
    accounts = load_rules(args.rules)
    if args.report:
        return report(accounts)
    if not accounts:
        print("no rule accounts defined")
        return 0
    try:
        runtime.preflight(cfg, ROOT)
    except runtime.Busy as e:
        print(f"rule accounts skipped: {e}")
        return 3
    rt = cfg.get("runtime") or {}
    # its own listing file (data/rules/kalshi_listing.json): the paper bot's covers other categories and days
    venue = Kalshi(min_interval=args.pace, cache_dir=ROOT / "data" / "rules", listing_cache_hours=args.listing_hours)
    t0 = time.time()
    try:
        with runtime.Lock(ROOT / "data" / "cycle.lock", float(rt.get("lock_stale_hours", 1))):
            only = [s.strip() for s in args.only.split(",") if s.strip()] or None
            out = run_rules(cfg, accounts, venue, ROOT, now=t0, only=only, candles=kalshi_candles(venue))
    except runtime.Busy as e:
        print(f"rule accounts skipped: {e}")
        return 3
    for s in out:
        print(f"[{s['account']}] {s['status']}: {s.get('qualifying', 0)} qualifying, {s.get('orders', 0)} orders, "
              f"equity ${s.get('equity', 0):,.2f}, {s.get('positions', 0)} positions, {s.get('resting', 0)} resting")
        for line in s["log"]:
            if any(k in line for k in ("BUY", "listed", "settled", "filled", "expired", "Error", "failed", "unavailable")):
                print(f"    {line}")
    print(f"rule accounts: {len(out)} in {time.time() - t0:,.0f} s, {venue.requests} requests")
    return 1 if out and all(s["status"] == "error" for s in out) else 0


if __name__ == "__main__":
    sys.exit(main())
