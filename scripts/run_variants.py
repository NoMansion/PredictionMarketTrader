"""Run the variant paper accounts on the forecasts the main account has just made (see src/variants.py and
variants.yaml). No Claude calls: the forecasts are read from the main ledger. Run it right after a cycle; the
paper loop does.

    python scripts/run_variants.py                  every account in variants.yaml
    python scripts/run_variants.py --only claude_only,control_fade
    python scripts/run_variants.py --report         where every account stands, nothing run

Exit codes: 0 done, 3 skipped (quiet window, a cycle is running, low memory), 1 every variant failed.
"""
import argparse
import sys
import time

from _bootstrap import ROOT

from run_cycle import make_venue
from src import runtime
from src.config import load_config
from src.ledger import Ledger
from src.variants import load_variants, run_variants, standings


def report(variants) -> int:
    rows = standings(ROOT, variants)
    print(f"{'account':24s} {'equity':>9s} {'P&L':>8s} {'open':>4s} {'resting':>7s} {'filled':>6s} {'expired':>7s} "
          f"{'settled':>7s} {'forecasts':>9s}  since")
    for r in rows:
        if r.get("started") is None:
            print(f"{r['account']:24s} not started yet")
            continue
        since = time.strftime("%m-%d %I:%M %p", time.localtime(r["started"]))
        print(f"{r['account']:24s} {r['equity']:9.2f} {r['equity'] - r['deposited']:+8.2f} {r['positions']:4d} {r['resting']:7d} "
              f"{r['filled']:6d} {r['expired']:7d} {r['settled_markets']:7d} {r['forecasts']:9d}  {since}")
    print("\nEquity values open positions at the bid. Two accounts are controls (they do not follow Claude).")
    for r in rows:
        print(f"  {r['account']}: {r['about']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--variants", default=str(ROOT / "variants.yaml"))
    ap.add_argument("--only", default="", help="comma-separated variant names")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    cfg = load_config(args.config)
    variants = load_variants(args.variants)
    if args.report:
        return report(variants)
    if not variants:
        print("no variants defined")
        return 0
    try:
        runtime.preflight(cfg, ROOT)
    except runtime.Busy as e:
        print(f"variants skipped: {e}")
        return 3
    rt = cfg.get("runtime") or {}
    try:
        # the cycle's own lock: a cycle and the variants never run at the same time (one ledger read, one exchange)
        with runtime.Lock(ROOT / "data" / "cycle.lock", float(rt.get("lock_stale_hours", 1))):
            main_ledger = Ledger(ROOT / "data" / "pmt.db")
            try:
                t0 = time.time()
                only = [s.strip() for s in args.only.split(",") if s.strip()] or None
                out = run_variants(cfg, variants, main_ledger, make_venue(cfg), ROOT, now=t0, only=only)
            finally:
                main_ledger.close()
    except runtime.Busy as e:
        print(f"variants skipped: {e}")
        return 3
    for s in out:
        print(f"[{s['variant']}] {s['status']}: {s.get('handed', 0)} new forecasts handed over, {s.get('orders', 0)} orders, "
              f"equity ${s.get('equity', 0):,.2f}, {s.get('positions', 0)} positions, {s.get('resting', 0)} resting")
        for line in s["log"]:
            if any(k in line for k in ("BUY", "SELL", "no trade", "settled", "filled", "expired", "Error", "failed")):
                print(f"    {line}")
    print(f"variants: {len(out)} accounts in {time.time() - t0:,.0f} s")
    return 1 if out and all(s["status"] == "error" for s in out) else 0


if __name__ == "__main__":
    sys.exit(main())
