"""What-if replay of a paper account's own record: "what would a daily budget of X, an edge threshold of Y, a stake
of Z or a different exit rule have done", worked out afterwards from one account that took every trade.

The wide variant accounts (variants.yaml) have no daily budget and no category or total exposure cap, so they
record every trade their rule wants. This takes that record and replays it under tighter settings:

  edge       only the decisions whose recorded edge is at least this
  budget     at most N orders and P% of the bankroll per rolling 24 hours (an order that rested and never filled
             still used the budget, as in src/safety.py)
  stake      each recorded stake scaled by stake_pct / recorded_pct (the accounts staked 2% a market)
  exit       hold (to settlement), recorded (the account's own sells), take_gain / stop_drop / days_before_end
             evaluated on the price snapshots the ledgers kept (the bid the bot would have sold into)

Only what the record can say is said: an order that did not fill on paper is not filled in the replay either,
and a market that has not settled is valued at its last recorded bid (reported apart as "open").
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

DAY = 86400.0
TAKER = 0.07


@dataclass(frozen=True)
class Settings:
    name: str = ""
    min_edge: float = 0.0
    max_orders_per_day: int = 10**6
    max_deploy_per_day_pct: float = 10.0
    stake_pct: float = 0.02
    recorded_pct: float = 0.02
    exit: str = "hold"                   # hold | recorded | rule
    take_gain: float | None = None
    stop_drop: float | None = None
    days_before_end: float | None = None
    bankroll: float = 1000.0


@dataclass
class Trade:
    ts: float
    market_id: str
    outcome: str                         # YES or NO
    edge: float
    stake: float                         # dollars the account committed
    filled: bool
    fill_ts: float | None = None
    price: float | None = None           # price paid per contract (before fee)
    fee_per_share: float = 0.0


@dataclass
class Outcome:
    accepted: int = 0
    filled: int = 0
    settled: int = 0
    open: int = 0
    sold: int = 0
    staked: float = 0.0
    pnl_settled: float = 0.0             # realised: settled or sold
    pnl_open: float = 0.0                # unrealised, at the last bid
    worst: float = 0.0
    lines: list = field(default_factory=list)

    @property
    def pnl(self) -> float:
        return self.pnl_settled + self.pnl_open

    @property
    def ret(self) -> float:
        return self.pnl / self.staked if self.staked else float("nan")


def load(account_db: str | Path, price_dbs: list[str | Path]) -> tuple[list[Trade], dict, dict, dict, dict]:
    """(trades, price paths, settlements, end times, recorded sells) from an account ledger and the ledgers whose
    snapshots give price paths (the main ledger tracks every forecast market for a week; the account its own)."""
    db = sqlite3.connect(f"file:{Path(account_db).as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    trades = []
    for o in db.execute("""SELECT o.id, o.ts, o.market_id, o.outcome, o.usd, o.status, d.edge FROM orders o
                           LEFT JOIN decisions d ON d.id = o.decision_id WHERE o.side='BUY' ORDER BY o.ts, o.id"""):
        f = db.execute("SELECT ts, price, shares, fee FROM fills WHERE order_id=? ORDER BY ts", (o["id"],)).fetchall()
        sh = sum(x["shares"] for x in f)
        trades.append(Trade(ts=o["ts"], market_id=o["market_id"], outcome=o["outcome"], edge=float(o["edge"] or 0.0),
                            stake=float(o["usd"]), filled=bool(f) and sh > 0,
                            fill_ts=f[0]["ts"] if f else None,
                            price=(sum(x["price"] * x["shares"] for x in f) / sh) if sh > 0 else None,
                            fee_per_share=(sum(x["fee"] or 0.0 for x in f) / sh) if sh > 0 else 0.0))
    sells: dict[str, list] = {}
    for s in db.execute("SELECT market_id, outcome, ts, price, fee, shares FROM fills WHERE side='SELL' ORDER BY ts"):
        sells.setdefault((s["market_id"], s["outcome"]), []).append(dict(s))
    paths: dict[str, list] = {}
    settle: dict[str, float] = {}
    ends: dict[str, float] = {}
    for path in [account_db, *price_dbs]:
        p = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
        for mid, ts, bid, ask, mtd in p.execute("SELECT market_id, ts, bid, ask, mid FROM snapshots ORDER BY ts"):
            paths.setdefault(mid, []).append((ts, bid, ask, mtd))
        for mid, pay, end in p.execute("SELECT market_id, payout_yes, end_ts FROM markets"):
            if pay is not None:
                settle[mid] = float(pay)
            if end is not None:
                ends.setdefault(mid, float(end))
        p.close()
    for mid in paths:
        seen, uniq = set(), []
        for row in sorted(paths[mid]):
            if round(row[0]) not in seen:
                seen.add(round(row[0]))
                uniq.append(row)
        paths[mid] = uniq
    db.close()
    return trades, paths, settle, ends, sells


def mine(outcome: str, bid, ask, mid) -> tuple[float | None, float | None]:
    """(our side's bid, our side's mid) from a YES snapshot."""
    if outcome == "YES":
        return bid, mid
    return (None if ask is None else 1.0 - ask), (None if mid is None else 1.0 - mid)


def follow(t: Trade, s: Settings, path: list, settle: float | None, end: float | None, sells: list) -> tuple[str, float, float]:
    """(how it ended, value per share received, time) for one filled trade."""
    pay = None if settle is None else (settle if t.outcome == "YES" else 1.0 - settle)
    if s.exit == "recorded":
        for x in sells:
            if x["ts"] >= (t.fill_ts or t.ts):
                return "sold", x["price"] - (x["fee"] or 0.0) / max(x["shares"], 1e-9), x["ts"]
    elif s.exit == "rule":
        for ts, bid, ask, mtd in path:
            if ts <= (t.fill_ts or t.ts):
                continue
            b, m = mine(t.outcome, bid, ask, mtd)
            if b is None or b <= 0:
                continue
            take = s.take_gain is not None and b >= t.price + s.take_gain - 1e-9
            stop = s.stop_drop is not None and m is not None and m <= t.price - s.stop_drop + 1e-9
            late = s.days_before_end is not None and end is not None and end - ts <= s.days_before_end * DAY
            if take or stop or late:
                return "sold", b - TAKER * b * (1 - b), ts
    if pay is not None:
        return "settled", pay, end or 0.0
    last = [r for r in path if r[0] > (t.fill_ts or t.ts)] or path
    for ts, bid, ask, mtd in reversed(last):
        b, _ = mine(t.outcome, bid, ask, mtd)
        if b is not None:
            return "open", b, ts
    return "open", t.price or 0.0, t.ts


def replay(trades: list[Trade], paths: dict, settle: dict, ends: dict, sells: dict, s: Settings) -> Outcome:
    out = Outcome()
    taken: list[tuple[float, float]] = []                     # (ts, dollars) of accepted orders
    scale = s.stake_pct / s.recorded_pct
    for t in sorted(trades, key=lambda x: x.ts):
        if t.edge < s.min_edge - 1e-12:
            continue
        recent = [(ts, usd) for ts, usd in taken if ts > t.ts - DAY]
        stake = t.stake * scale
        if len(recent) >= s.max_orders_per_day or sum(u for _, u in recent) + stake > s.max_deploy_per_day_pct * s.bankroll + 1e-9:
            continue
        taken.append((t.ts, stake))
        out.accepted += 1
        if not t.filled or not t.price:
            continue
        out.filled += 1
        shares = stake / (t.price + t.fee_per_share)
        how, value, when = follow(t, s, paths.get(t.market_id, []), settle.get(t.market_id), ends.get(t.market_id),
                                  sells.get((t.market_id, t.outcome), []))
        pnl = shares * value - stake
        out.staked += stake
        if how == "open":
            out.open += 1
            out.pnl_open += pnl
        else:
            out.settled += how == "settled"
            out.sold += how == "sold"
            out.pnl_settled += pnl
        out.worst = min(out.worst, pnl)
        out.lines.append((t.market_id, t.outcome, round(t.price, 3), how, round(value, 3), round(pnl, 2)))
    return out


def grid() -> list[Settings]:
    """The settings worth comparing; fixed before any of these accounts' markets had settled (2026-11-20)."""
    out = []
    budgets = (("6/day, 10%", 6, 0.10), ("12/day, 20%", 12, 0.20), ("no budget", 10**6, 10.0))
    for edge in (0.01, 0.03, 0.05, 0.08):
        for bname, n, pct in budgets:
            out.append(Settings(f"edge {edge:.2f}, {bname}, hold", edge, n, pct))
    for edge in (0.03,):
        for label, kw in (("recorded sells", {"exit": "recorded"}),
                          ("take +10", {"exit": "rule", "take_gain": 0.10}),
                          ("stop -15", {"exit": "rule", "stop_drop": 0.15}),
                          ("take +10 / stop -15", {"exit": "rule", "take_gain": 0.10, "stop_drop": 0.15}),
                          ("sell 3d before end", {"exit": "rule", "days_before_end": 3})):
            out.append(Settings(f"edge {edge:.2f}, no budget, {label}", edge, 10**6, 10.0, **kw))
    for pct in (0.01, 0.03):
        out.append(Settings(f"edge 0.03, no budget, stake {pct:.0%}, hold", 0.03, 10**6, 10.0, stake_pct=pct))
    return out
