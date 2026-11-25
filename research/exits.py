"""Selling before settlement: what an exit rule does to a mechanical rule's bets.

backtest.py holds every bet to settlement. This follows each bet bar by bar after its entry and sells it when an
exit condition holds, at prices the market really offered later:

  condition    known at the END of a later bar j of the same market (never the entry bar itself)
  taker exit   sell at the OPEN of bar j+1: our side's bid (YES: n_bid_op; NO: 1 - n_ask_op), less the taker fee
  resting exit offer at bar j's ask for our side (YES: ask; NO: 1 - bid) for up to 3 bars; counted only if the market
               traded through it (the same trade-through test the resting entries use); otherwise keep holding and
               test the condition again on later bars

Exit conditions (any that are set; the first bar on which one holds triggers the exit):

  take_px      our side's bid reaches this price (e.g. 0.99: sell a NO bought at 96c once it is bid 99c)
  take_gain    our side's bid is this many points above the price paid (before fees)
  stop_drop    our side's mid has fallen this many points below the price paid
  stop_px      our side's mid has fallen to this price or below (e.g. 0.85 for a NO: the YES is at 15c)
  days         the scheduled end is this many days away or less (sell before the last days)

Returns are per dollar staked, after fees on both legs. A sold bet also gives its money back EARLIER, which an
account replay sees: `release` is the time the capital is free again (the exit, or the market's close).

The resting exit is offered only for take-profit conditions: a stop wants out now, at the bid.

Hourly stops (Ideas queue item 20): with `hourly` (load_hourly: 60-minute bars of research/hourly_bars.py, which
cover only the last hours before a market's close), a stop is also tested on each hourly bar that ends inside the
daily bar being looked at, BEFORE that daily bar's own test; when one holds, the bet is sold at the OPEN of the next
hourly bar (our side's bid, taker fee), if that bar opens with a two-sided quote within an hour of the daily bar's
end. Otherwise the daily rule applies as before. Take-profit and time exits stay daily.

Hourly take-profits (Ideas queue item 43): with `hourly_takes=True` as well, a TAKER take-profit (style "tk") is
tested on the same hourly bars: our side's closing bid of an hourly bar at or above the take level sells at the
next hourly open's bid (taker fee), as a stop does; on one bar a stop wins over a take. Resting takes (style "mk")
stay daily: the hourly bars have no fill model.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import panel
from backtest import Panel, Sample

DAY = 86400.0


@dataclass(frozen=True)
class Policy:
    name: str
    take_px: float | None = None
    take_gain: float | None = None
    stop_drop: float | None = None
    stop_px: float | None = None
    days: float | None = None
    style: str = "tk"                   # how a take-profit sells: "tk" at the next open's bid, "mk" resting at the ask

    @property
    def holds(self) -> bool:
        return all(v is None for v in (self.take_px, self.take_gain, self.stop_drop, self.stop_px, self.days))


HOLD = Policy("hold to settlement")


@dataclass
class Result:
    rows: np.ndarray                    # entry row of each bet
    r: np.ndarray                       # return per dollar staked, after fees
    release: np.ndarray                 # when the money is free again
    reason: np.ndarray                  # "settle", "take", "stop", "time"
    exit_px: np.ndarray                 # price received per contract before fees (NaN when held to settlement)
    cost: np.ndarray                    # price paid per contract, fees included
    extra: dict = field(default_factory=dict)


class Exits:
    """Precomputed arrays for following bets after entry. Build once per Panel."""

    def __init__(self, p: Panel, hourly: dict | None = None, hourly_takes: bool = False):
        self.p = p
        d = p.df
        self.hourly = hourly or {}
        self.tick = d["ticker"].to_numpy()
        self.hourly_stops = 0           # stops sold on an hourly bar (counted over every follow() call)
        self.hourly_takes = hourly_takes
        self.hourly_take_sales = 0      # taker take-profits sold on an hourly bar
        self.ts = d["ts"].to_numpy("float64")
        self.close = d["close_ts"].to_numpy("float64")
        self.bid = d["bid"].to_numpy("float64")
        self.ask = d["ask"].to_numpy("float64")
        self.mid = d["mid"].to_numpy("float64")
        self.quoted = d["quoted"].to_numpy(bool)
        self.n_bid = d["n_bid_op"].to_numpy("float64")
        self.n_ask = d["n_ask_op"].to_numpy("float64")
        self.n_ok = d["n_ok"].to_numpy(bool)
        self.dte = d["dte"].to_numpy("float64")
        self.mult = d["mult"].to_numpy("float64")
        self.maker_rate = np.where(d["maker_fee"].to_numpy(bool), panel.MAKER, 0.0)
        self.f1_yes, self.f1_no = d["f1_yes"].to_numpy(bool), d["f1_no"].to_numpy(bool)
        self.f3_yes, self.f3_no = d["f3_yes"].to_numpy(bool), d["f3_no"].to_numpy(bool)
        self.y = p.y.astype("float64")
        # last row of each market (rows are ordered by market, then time)
        t = p.ticker
        last = np.ones(p.n, bool)
        last[:-1] = t[1:] != t[:-1]
        self.end = np.zeros(p.n, "int64")
        ends = np.flatnonzero(last)
        starts = np.r_[0, ends[:-1] + 1]
        for s, e in zip(starts, ends):
            self.end[s:e + 1] = e

    def tfee(self, i: int, px: float) -> float:
        return panel.TAKER * self.mult[i] * px * (1 - px)

    def entry(self, i: int, side: str, entry: str) -> tuple[float, float, int]:
        """(price paid before fees, cost per contract with fees, first row on which an exit may be considered)."""
        if entry == "tk":
            px = self.n_ask[i] if side == "yes" else 1 - self.n_bid[i]
            fee_px = self.n_ask[i] if side == "yes" else self.n_bid[i]
            return px, px + self.tfee(i, fee_px), i + 1
        px = self.bid[i] if side == "yes" else 1 - self.ask[i]
        q = self.bid[i] if side == "yes" else self.ask[i]
        cost = px + self.maker_rate[i] * self.mult[i] * q * (1 - q)
        # a resting entry is filled somewhere in the next 1 to 3 bars: exits are considered only after that
        filled_first = self.f1_yes[i] if side == "yes" else self.f1_no[i]
        return px, cost, i + (1 if filled_first else 3)

    def hourly_stop(self, j: int, side: str, px: float, cost: float, pol: Policy):
        """A stop (and, with hourly_takes, a taker take-profit) on the hourly bars ending inside daily bar j (after
        bar j-1), sold at the next hourly open."""
        want_take = self.hourly_takes and pol.style == "tk" and (pol.take_px is not None or pol.take_gain is not None)
        h = self.hourly.get(self.tick[j])
        if h is None or len(h) == 0:
            return None
        lo, hi = self.ts[j - 1], self.ts[j]
        a, b = np.searchsorted(h[:, 0], lo, "right"), np.searchsorted(h[:, 0], hi, "right")
        for k in range(a, b):
            bid, ask = h[k, 1], h[k, 2]
            if not (bid > 0 and ask < 1 and ask > bid):
                continue
            mid = (bid + ask) / 2
            mine = mid if side == "yes" else 1 - mid
            stop = ((pol.stop_drop is not None and mine <= px - pol.stop_drop + 1e-9)
                    or (pol.stop_px is not None and mine <= pol.stop_px + 1e-9))
            mine_bid = bid if side == "yes" else 1 - ask
            take = want_take and ((pol.take_px is not None and mine_bid >= pol.take_px - 1e-9)
                                  or (pol.take_gain is not None and mine_bid >= px + pol.take_gain - 1e-9))
            if not (stop or take):
                continue
            for m in range(k + 1, len(h)):
                if h[m, 0] > hi + 3600:
                    break
                bo, ao = h[m, 3], h[m, 4]
                if bo > 0 and ao < 1 and ao > bo:
                    q = bo if side == "yes" else ao
                    got = q if side == "yes" else 1 - q
                    net = got - self.tfee(j, q)
                    if stop:
                        self.hourly_stops += 1
                    else:
                        self.hourly_take_sales += 1
                    return (net - cost) / cost, float(h[m, 0]), "stop" if stop else "take", got, cost
            return None                                            # no tradable next hourly open: daily rule
        return None

    def follow(self, i: int, side: str, entry: str, pol: Policy) -> tuple[float, float, str, float, float]:
        """(return, release time, reason, exit price, cost) for one bet entered on row i."""
        px, cost, start = self.entry(i, side, entry)
        pay = self.y[i] if side == "yes" else 1 - self.y[i]
        settle = ((pay - cost) / cost, max(self.close[i], self.ts[i] + DAY), "settle", float("nan"), cost)
        if pol.holds or cost <= 0:
            return settle
        e = self.end[i]
        j = start
        while j <= e:
            if self.hourly and (pol.stop_drop is not None or pol.stop_px is not None
                                or (self.hourly_takes and pol.style == "tk"
                                    and (pol.take_px is not None or pol.take_gain is not None))):
                hit = self.hourly_stop(j, side, px, cost, pol)
                if hit is not None:
                    return hit
            if not self.quoted[j]:
                j += 1
                continue
            mine_bid = self.bid[j] if side == "yes" else 1 - self.ask[j]
            mine_mid = self.mid[j] if side == "yes" else 1 - self.mid[j]
            take = ((pol.take_px is not None and mine_bid >= pol.take_px - 1e-9)
                    or (pol.take_gain is not None and mine_bid >= px + pol.take_gain - 1e-9))
            stop = ((pol.stop_drop is not None and mine_mid <= px - pol.stop_drop + 1e-9)
                    or (pol.stop_px is not None and mine_mid <= pol.stop_px + 1e-9))
            late = pol.days is not None and self.dte[j] <= pol.days
            if stop or late or (take and pol.style == "tk"):
                if self.n_ok[j]:                                  # sell at the next bar's opening bid
                    q = self.n_bid[j] if side == "yes" else self.n_ask[j]
                    got = q if side == "yes" else 1 - q
                    net = got - self.tfee(j, q)
                    why = "stop" if stop else ("take" if (take and pol.style == "tk") else "time")
                    rel = self.ts[j + 1] if j + 1 <= e else self.ts[j] + DAY
                    return (net - cost) / cost, rel, why, got, cost
            elif take:                                            # resting offer at our side's ask
                filled = self.f3_no[j] if side == "yes" else self.f3_yes[j]
                if filled:
                    got = self.ask[j] if side == "yes" else 1 - self.bid[j]
                    q = self.ask[j] if side == "yes" else self.bid[j]
                    net = got - self.maker_rate[j] * self.mult[j] * q * (1 - q)
                    rel = self.ts[min(j + 3, e)] if j + 1 <= e else self.ts[j] + DAY
                    return (net - cost) / cost, rel, "take", got, cost
            j += 1
        return settle

    def run(self, rows: np.ndarray, side: str, entry: str, pol: Policy) -> Result:
        out = [self.follow(int(i), side, entry, pol) for i in rows]
        if not out:
            z = np.zeros(0)
            return Result(rows, z, z, np.zeros(0, dtype=object), z, z)
        r, rel, why, got, cost = (np.array(x) for x in zip(*out))
        return Result(rows, r.astype("float64"), rel.astype("float64"), why.astype(object), got.astype("float64"),
                      cost.astype("float64"))


def load_hourly(path, tickers=None) -> dict:
    """ticker -> float array (n, 5) of ts, bid, ask, bid_op, ask_op, sorted by ts, from candles_1h
    (research/hourly_bars.py). Missing prices are NaN."""
    import sqlite3
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=60)
    rows = con.execute("SELECT ticker, ts, bid, ask, bid_op, ask_op FROM candles_1h ORDER BY ticker, ts").fetchall()
    con.close()
    keep = None if tickers is None else set(tickers)
    out: dict = {}
    for r in rows:
        if keep is None or r[0] in keep:
            out.setdefault(r[0], []).append([float("nan") if v is None else float(v) for v in r[1:]])
    return {t: np.array(v, dtype="float64") for t, v in out.items()}


def rule_rows(p: Panel, mask: np.ndarray, side: str, entry: str) -> np.ndarray:
    """Entry rows exactly as backtest.Panel.evaluate picks them: the first qualifying bar of each market."""
    return p.first_per_market(mask & p.ok[(side, entry)])


def stats(p: Panel, res: Result) -> tuple[Sample, Sample]:
    """(in sample, out of sample) in backtest.Sample form, split by the market's close as everywhere else."""
    full = np.full(p.n, np.nan)
    full[res.rows] = res.r
    cost = np.full(p.n, np.nan)
    cost[res.rows] = res.cost
    win = np.zeros(p.n, "float32")
    win[res.rows] = (res.r > 0).astype("float32")
    o = p.oos[res.rows]
    return p.sample(res.rows[~o], full, cost, win), p.sample(res.rows[o], full, cost, win)


def bets(p: Panel, res: Result) -> np.ndarray:
    """(entry ts, release ts, return, event) in entry order, for research/portfolio.simulate."""
    ts = p.col("ts").astype("float64")[res.rows]
    tick = p.ticker[res.rows]
    order = sorted(range(len(res.rows)), key=lambda k: (ts[k], (int(tick[k]) * 2654435761) % 4294967296))
    return np.array([(ts[k], max(res.release[k], ts[k] + 3600.0), res.r[k], p.event[res.rows[k]]) for k in order],
                    dtype="float64") if order else np.zeros((0, 4))


def policies() -> list[Policy]:
    """The grid, fixed before any exit result was seen (2026-11-20). A choice among them is made in sample."""
    out = [HOLD]
    for x in (0.97, 0.98, 0.99):
        out.append(Policy(f"take at bid >= {x:.2f}, taker", take_px=x))
        out.append(Policy(f"take at bid >= {x:.2f}, resting", take_px=x, style="mk"))
    for g in (0.03, 0.05, 0.10):
        out.append(Policy(f"take at +{g * 100:g} points, taker", take_gain=g))
        out.append(Policy(f"take at +{g * 100:g} points, resting", take_gain=g, style="mk"))
    for d in (0.05, 0.10, 0.20):
        out.append(Policy(f"stop at -{d * 100:g} points", stop_drop=d))
    for s in (0.90, 0.85, 0.75):
        out.append(Policy(f"stop at our mid <= {s:.2f}", stop_px=s))
    for dd in (1, 3, 7):
        out.append(Policy(f"sell {dd}d before the scheduled end", days=dd))
    out.append(Policy("take 0.99 resting + stop -10 points", take_px=0.99, stop_drop=0.10, style="mk"))
    out.append(Policy("take +5 points resting + stop -10 points", take_gain=0.05, stop_drop=0.10, style="mk"))
    out.append(Policy("take 0.98 taker + stop at mid <= 0.85", take_px=0.98, stop_px=0.85))
    return out
