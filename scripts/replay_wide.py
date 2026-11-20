"""Replay the wide paper accounts' own records under other settings (src/replay.py).

    python scripts/replay_wide.py                         the three wide accounts, the standard grid
    python scripts/replay_wide.py --account claude_only_wide --lines

Each row: orders accepted, filled, settled / sold / still open, dollars staked, profit realised (settled or sold),
profit with the open positions at their last bid, and profit per dollar staked. Until a few dozen of these
markets have settled the "open" column carries almost everything, and the table says nothing yet about which
setting is better: it says only that the tool works.
"""
import argparse
import sys

from _bootstrap import ROOT

from src.replay import grid, load, replay

WIDE = ("claude_only_wide", "claude_only_wide_edge1", "blend30_wide")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--account", action="append", help="variant name (default: the three wide accounts)")
    ap.add_argument("--lines", action="store_true", help="also print each trade of the first setting")
    args = ap.parse_args()
    main_db = ROOT / "data" / "pmt.db"
    for name in args.account or WIDE:
        path = ROOT / "data" / "variants" / f"{name}.db"
        if not path.exists():
            print(f"{name}: no ledger yet")
            continue
        trades, paths, settle, ends, sells = load(path, [main_db])
        print(f"\n== {name}: {len(trades)} orders recorded, {sum(t.filled for t in trades)} filled, "
              f"{sum(1 for t in trades if t.market_id in settle)} in markets that have settled ==")
        print(f"{'setting':48s} {'accept':>6s} {'filled':>6s} {'settl':>5s} {'sold':>4s} {'open':>4s} {'staked':>8s} "
              f"{'realised':>9s} {'with open':>9s} {'per $':>7s}")
        for k, s in enumerate(grid()):
            o = replay(trades, paths, settle, ends, sells, s)
            print(f"{s.name:48s} {o.accepted:6d} {o.filled:6d} {o.settled:5d} {o.sold:4d} {o.open:4d} {o.staked:8.2f} "
                  f"{o.pnl_settled:+9.2f} {o.pnl:+9.2f} {o.ret:+7.2%}")
            if args.lines and k == 0:
                for line in o.lines:
                    print("    ", line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
