"""Mechanical paper accounts: rules found in five years of Kalshi history, traded forward on paper.

The research (reports/2026-11-18_strategy_research.md, sections 3.7 to 3.28) found a few price rules that paid in
both halves of the history, all of the same shape: in a market that has already traded a lot, buy NO against a
cheap YES with a resting order, and hold it to settlement. A backtest cannot say whether a resting order would
really have been filled, or whether the effect is still there. These accounts answer that going forward: each is
one rule (or several, for the combined account), with its own ledger under data/rules/, its own $1,000 of paper
money, the same broker, fees and safety stops as the paper bot, and no Claude usage at all.

Two of the accounts are controls: the same rule on QUIET markets, where the history says it does not pay. If the
busy-market accounts end ahead of their quiet twins, the busy-market effect is real; if not, that is the answer.

How an account trades, every cycle (rules.yaml says which numbers):
  1. mark      the Trader's own step: settle what resolved, fill or expire resting orders, value what is held
  2. scan      the listing of open markets (read once for all accounts, kept a few hours), cut loosely by the
               rule (category, contracts traded so far, listed price, days to the close); then a fresh order book
               and a fresh market detail for each survivor, and the rule checked again on those
  3. enter     one bet per market, ever: a fixed share of equity, capped per event, by total exposure and by
               cash. "resting" joins the best NO bid (1 - the YES ask, as in the backtest) for 72 hours; "taker"
               pays the NO ask. The paper broker fills a resting order only once the market trades through it
               (src/broker.py), which is harsher than the backtest's fill model, so these results should be worse
               than real ones, not better.
  4. hold      no exits: the exit study (report 3.28) found holding to settlement the best exit for these rules.

Nothing here can place a real order: the broker is the paper broker, and the venue makes GET requests only.
"""
from __future__ import annotations

import copy
import time
import zlib
from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

from .ledger import Ledger
from .trader import DAY, CycleResult, Trader
from .variants import SharedVenue, merge
from .venue import Market, brief

ENTRIES = ("resting", "taker")
KALSHI_NAMES = {c.lower(): c for c in ("Economics", "Financials", "Politics", "Elections", "Companies", "Commodities",
                                        "Science and Technology", "Climate and Weather", "Crypto", "Entertainment",
                                        "Mentions", "Health", "Social", "World")}


@dataclass
class Leg:
    """One rule: which markets, which side. Prices are the YES mid; the side bought is NO unless said otherwise."""
    label: str
    categories: tuple[str, ...]
    side: str = "NO"
    min_yes_mid: float = 0.0            # inclusive
    max_yes_mid: float = 1.0            # inclusive
    max_spread: float = 0.10            # YES ask - YES bid (the backtest's "tradable quote" is 10 cents or less)
    min_days: float = 0.25              # days to the scheduled close
    max_days: float = 400.0
    min_volume: float = 0.0             # contracts traded so far, at least
    max_volume: float | None = None     # ... and fewer than this (the quiet-market controls)
    min_fall_7d: float | None = None    # YES mid at least this much lower than 7 days ago

    def listed_fits(self, m: Market, now: float) -> bool:
        """A loose first cut on the listing (its quotes can be hours old): 3 cents of slack on the price."""
        if (m.category or "").lower() not in self.categories:
            return False
        if not self._volume_ok(getattr(m, "contracts", None)):
            return False
        if m.best_bid is None or m.best_ask is None:
            return False
        mid = (m.best_bid + m.best_ask) / 2.0
        if not self.min_yes_mid - 0.03 <= mid <= self.max_yes_mid + 0.03:
            return False
        days = m.days_to_end(now)
        return days is not None and self.min_days < days <= self.max_days

    def _volume_ok(self, contracts) -> bool:
        if contracts is None:
            return self.min_volume <= 0 and self.max_volume is None
        if contracts < self.min_volume:
            return False
        return self.max_volume is None or contracts < self.max_volume

    def check(self, yes, m: Market, now: float, fall_7d: float | None = None) -> str:
        """'' when the rule holds on a fresh book and fresh detail, otherwise why not."""
        if m.closed:
            return "closed"
        if yes.best_bid is None or yes.best_ask is None or yes.mid is None:
            return "one-sided book"
        if not self.min_yes_mid - 1e-9 <= yes.mid <= self.max_yes_mid + 1e-9:
            return f"YES mid {yes.mid:.3f} outside {self.min_yes_mid:.3f}-{self.max_yes_mid:.3f}"
        if yes.spread > min(self.max_spread, 0.10) + 1e-9:
            return f"spread {yes.spread:.3f} above {min(self.max_spread, 0.10):.2f}"
        days = m.days_to_end(now)
        if days is None or not self.min_days < days <= self.max_days:
            return "days to the close outside the rule" if days is not None else "no close time"
        if not self._volume_ok(getattr(m, "contracts", None)):
            return f"{getattr(m, 'contracts', None)} contracts traded: outside the rule's level"
        if self.min_fall_7d is not None:
            if fall_7d is None:
                return "no price from 7 days ago"
            if fall_7d < self.min_fall_7d - 1e-9:
                return f"YES fell {fall_7d:+.3f} in 7 days (rule: {self.min_fall_7d:.2f} or more)"
        return ""


@dataclass
class RuleAccount:
    name: str
    legs: list[Leg]
    about: str = ""
    entry: str = "resting"
    stake_pct: float = 0.01             # of equity, per bet
    event_cap_pct: float = 0.03         # all bets on one event (research/portfolio.simulate: 3%)
    max_exposure_pct: float = 0.50      # everything at work (portfolio.simulate: 50%)
    min_stake: float = 1.0
    max_books: int = 40                 # fresh order books read per cycle for this account
    control: bool = False
    config: dict = field(default_factory=dict)      # laid over config.yaml (safety stops, fees)
    # Claude as a filter on the rule (forward-only idea 18 of STATE.md): each qualifying market is put to the paper
    # bot's own forecaster (the market price is not shown to it), and the bet is vetoed when Claude's probability
    # of our side is below the price paid, or Claude says the rules are unclear. At most max_asks questions a
    # cycle: the rest wait for the next cycle. A vetoed market is not asked again; its outcome is still recorded.
    claude_filter: bool = False
    max_asks: int = 2


LEG_KEYS = {f.name for f in fields(Leg)}
ACCOUNT_KEYS = {f.name for f in fields(RuleAccount)} - {"name"}


def load_rules(path: str | Path) -> dict[str, RuleAccount]:
    """rules.yaml -> {name: RuleAccount}. Unknown keys are errors: a misspelt limit must not silently vanish."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = (yaml.safe_load(f) or {}).get("accounts") or {}
    out = {}
    for name, spec in raw.items():
        spec = dict(spec or {})
        if not str(name).replace("_", "").isalnum():
            raise ValueError(f"rule account name {name!r}: letters, digits and underscores only (it becomes a file name)")
        unknown = sorted(set(spec) - ACCOUNT_KEYS)
        if unknown:
            raise ValueError(f"rule account {name!r}: unknown setting(s) {', '.join(unknown)}")
        legs = []
        for i, lg in enumerate(spec.pop("legs", None) or []):
            lg = dict(lg)
            bad = sorted(set(lg) - LEG_KEYS)
            if bad:
                raise ValueError(f"rule account {name!r}, leg {i + 1}: unknown setting(s) {', '.join(bad)}")
            cats = lg.pop("categories", None) or []
            if isinstance(cats, str):
                cats = [cats]
            lg["categories"] = tuple(sorted(str(c).lower() for c in cats))
            side = lg.get("side", "NO")
            if isinstance(side, bool):                  # YAML reads a bare yes / no as true / false
                side = "YES" if side else "NO"
            lg["side"] = str(side).upper()
            if lg["side"] not in ("YES", "NO"):
                raise ValueError(f"rule account {name!r}, leg {i + 1}: side must be YES or NO")
            lg.setdefault("label", f"leg {i + 1}")
            legs.append(Leg(**lg))
        if not legs:
            raise ValueError(f"rule account {name!r} has no legs")
        acct = RuleAccount(name=str(name), legs=legs, **{k: v for k, v in spec.items()})
        acct.entry = str(acct.entry).lower()
        if acct.entry not in ENTRIES:
            raise ValueError(f"rule account {name!r}: entry must be one of {', '.join(ENTRIES)}")
        out[acct.name] = acct
    return out


def account_config(main_cfg: dict, acct: RuleAccount) -> dict:
    """The main configuration, with what a mechanical account needs: resting orders live 72 hours (the backtest
    leaves them three daily bars), no forecast-based exits (there are no forecasts) and nothing tracked for scoring."""
    cfg = merge(main_cfg, {"execution": {"resting_ttl_hours": 72.0, "exit_on_forecast": False, "track_forecasts_days": 0,
                                         "style": "taker" if acct.entry == "taker" else "passive"}})
    return merge(cfg, acct.config)


def fall_from_candles(candles: list[dict], mid_now: float, now: float) -> float | None:
    """How far the YES mid has fallen since the daily bar of 7 days ago (positive = fell). None without that bar.
    The backtest's mom7 is the mid now minus the mid 7 daily bars back, on bid/ask closes."""
    target = now - 7 * DAY
    best = None
    for c in candles or []:
        ts = c.get("end_period_ts")
        try:
            bid = float((c.get("yes_bid") or {}).get("close_dollars"))
            ask = float((c.get("yes_ask") or {}).get("close_dollars"))
        except (TypeError, ValueError):
            continue
        if ts is None or not (bid > 0 and ask < 1 and ask > bid):
            continue
        if ts <= target + 12 * 3600 and (best is None or ts > best[0]):
            best = (ts, (bid + ask) / 2.0)
    if best is None or best[0] < target - 2 * DAY:     # no quoted bar near 7 days back
        return None
    return best[1] - mid_now


class RuleTrader(Trader):
    """The Trader with its forecast and entry steps replaced by a rule. Marking, settlement, resting-order fills,
    equity, the account safety stops and the run record are the Trader's own."""

    def __init__(self, cfg: dict, ledger: Ledger, venue, acct: RuleAccount, listing: list[Market], root=".",
                 candles=None, asker=None):
        super().__init__(cfg, ledger, venue, forecaster=asker, root=root)
        self.acct, self.listing = acct, listing
        self.candles = candles or (lambda m, now: [])
        if acct.claude_filter and asker is None:
            raise ValueError(f"rule account {acct.name!r} filters with Claude but no forecaster was given")
        self._fids: dict[str, tuple[int, float]] = {}

    def _tried(self) -> set[str]:
        return {r["market_id"] for r in self.ledger.q("SELECT DISTINCT market_id FROM orders WHERE side='BUY' "
                                                      "UNION SELECT DISTINCT market_id FROM decisions WHERE action='VETO'")}

    def _claude_filter(self, cands: list, res: CycleResult, now: float) -> list:
        """Keep the candidates Claude does not object to; ask about at most max_asks of them."""
        keep, asks, waiting = [], 0, 0
        for m, leg, yes, no in cands:
            if asks >= self.acct.max_asks:
                waiting += 1
                continue
            try:
                full = self.venue.enrich(m) or m                 # the rules text, for the question packet
            except Exception as e:
                res.say(f"{m.market_id}: detail unavailable for Claude ({brief(e)})")
                continue
            self.ledger.upsert_market(full.ledger_row(), ts=now)
            asks += 1
            try:
                f = self.forecaster.forecast(full, now)
            except Exception as e:
                res.say(f"{m.market_id}: forecaster failed ({brief(e)})")
                continue
            finally:
                self.heartbeat()
            if f is None:
                res.say(f"{m.market_id}: no usable forecast ({getattr(self.forecaster, 'last_error', '') or 'no answer'}): "
                        "asked again next cycle")
                continue
            fid = self.ledger.add_forecast(f.ledger_row(res.run_id, yes.mid))
            book = no if leg.side == "NO" else yes
            price = book.best_bid if self.acct.entry == "resting" else book.best_ask
            ours = 1.0 - f.p_yes if leg.side == "NO" else f.p_yes
            why = ""
            if not f.rules_clear:
                why = "Claude says the resolution rules are not clear"
            elif price is not None and ours < price - 1e-9:
                why = f"Claude gives {leg.side} {ours:.3f}, under the {price:.3f} it would cost"
            if why:
                self.ledger.add_decision({"ts": now, "run_id": res.run_id, "market_id": m.market_id, "forecast_id": fid,
                                          "action": "VETO", "reason": f"{leg.label}: {why}", "p_model": f.p_yes,
                                          "p_market": yes.mid})
                res.say(f"{m.market_id}: VETO ({why})")
                continue
            self._fids[m.market_id] = (fid, f.p_yes)
            res.say(f"{m.market_id}: Claude agrees ({leg.side} {ours:.3f} against {price:.3f}, {f.confidence})")
            keep.append((m, leg, yes, no))
        res.stats.update(claude_asked=asks, claude_waiting=waiting)
        if waiting:
            res.say(f"{waiting} qualifying markets wait for Claude until the next cycle (at most {self.acct.max_asks} a cycle)")
        return keep

    def forecast(self, res: CycleResult, now: float) -> list:
        """Here: the scan. Returns (market, leg, yes book, no book) for every market where the rule holds now."""
        tried = self._tried()
        picked: dict[str, tuple[Market, Leg]] = {}
        for m in self.listing:
            if m.market_id in tried or m.market_id in picked:
                continue
            for leg in self.acct.legs:
                if leg.listed_fits(m, now):
                    picked[m.market_id] = (m, leg)
                    break
        # A fresh pseudo-random order each cycle (not biggest first): with more candidates than books to read, a
        # fixed order would re-read the same markets that failed the rule every time and never reach the rest.
        rnd = int(self.ledger.get_meta("scan_round", 0) or 0)
        self.ledger.set_meta("scan_round", rnd + 1)
        order = sorted(picked.values(), key=lambda t: zlib.crc32(f"{t[0].market_id}#{rnd}".encode()))
        out, looked, why_not = [], 0, {}
        for listed, leg in order:
            if looked >= self.acct.max_books:
                break
            if getattr(self.venue, "rate_limited", 0) >= 3:
                res.say("the exchange is rate limiting: scan stopped")
                break
            looked += 1
            b = self._load_books(listed.market_id, res, snapshot=False)
            if b is None:
                continue
            yes, no, _ = b
            # the cheap checks on the book first; the detail (one more request) only for what passes them
            pre = Leg(**{**leg.__dict__, "min_days": -1e9, "max_days": 1e9, "min_volume": 0.0, "max_volume": None,
                         "min_fall_7d": None}).check(yes, listed, now)
            if pre:
                why_not[pre.split(" ")[0]] = why_not.get(pre.split(" ")[0], 0) + 1
                continue
            try:
                m = self.venue.market(listed.market_id)
            except Exception as e:
                res.say(f"{listed.market_id}: market detail unavailable ({brief(e)})")
                continue
            if m is None:
                continue
            fall = None
            if leg.min_fall_7d is not None:
                try:
                    fall = fall_from_candles(self.candles(m, now), yes.mid, now)
                except Exception as e:
                    res.say(f"{m.market_id}: price history unavailable ({brief(e)})")
            why = leg.check(yes, m, now, fall)
            if why:
                why_not[why.split(" ")[0]] = why_not.get(why.split(" ")[0], 0) + 1
                continue
            self._markets[m.market_id] = m
            out.append((m, leg, yes, no))
        res.stats.update(listed=len(self.listing), passed_listing=len(picked), books_read=looked, qualifying=len(out))
        res.say(f"{len(self.listing)} markets listed, {len(picked)} fit the rule loosely, {looked} books read, "
                f"{len(out)} qualify now" + (f"; not now: {why_not}" if why_not else ""))
        return self._claude_filter(out, res, now) if self.acct.claude_filter else out

    def entries(self, cands: list, equity: float, acct, res: CycleResult, now: float) -> None:
        a = self.acct
        for m, leg, yes, no in cands:
            book = no if leg.side == "NO" else yes
            price = book.best_bid if a.entry == "resting" else book.best_ask
            fid, p_model = self._fids.get(m.market_id, (None, None))
            base = {"ts": now, "run_id": res.run_id, "market_id": m.market_id, "forecast_id": fid, "p_model": p_model,
                    "p_market": yes.mid}
            self.ledger.upsert_market(m.ledger_row(), ts=now)
            if price is None or not 0 < price < 1:
                self.ledger.add_decision({**base, "action": "SKIP", "reason": f"{leg.label}: no {leg.side} price to {a.entry}"})
                continue
            e = self._exposure(m, equity)
            limits = {"stake": a.stake_pct * equity, "event cap": a.event_cap_pct * equity - e.event,
                      "exposure cap": a.max_exposure_pct * equity - e.total, "cash": e.cash,
                      "order ceiling": self.rules.max_order_usd}
            binding, stake = min(limits.items(), key=lambda kv: kv[1])
            stake = round(stake, 2)
            detail = {"leg": leg.label, "entry": a.entry, "binding": binding, "yes_bid": yes.best_bid, "yes_ask": yes.best_ask,
                      "contracts": getattr(m, "contracts", None), "days": m.days_to_end(now)}
            if stake < a.min_stake:
                self.ledger.add_decision({**base, "action": "SKIP", "reason": f"{leg.label}: stake ${max(stake, 0):.2f} "
                                          f"under ${a.min_stake:.2f} (bound by {binding})", "detail": detail})
                continue
            reason = (f"{leg.label}: YES {yes.best_bid:.2f}/{yes.best_ask:.2f}, {a.entry} {leg.side} at {price:.3f}, "
                      f"${stake:.2f} (bound by {binding})")
            did = self.ledger.add_decision({**base, "action": f"BUY_{leg.side}", "reason": reason, "cost": price,
                                            "stake": stake, "detail": detail})
            if a.entry == "taker":
                spent = self.broker.buy_taker(res.run_id, m.market_id, leg.side, book, stake, price, category=m.category,
                                              decision_id=did, now=now, fee_rate=m.fee_rate)
                res.say(f"{m.market_id}: BUY {leg.side} ${spent:,.2f} taken ({reason})")
            else:
                self.broker.place_resting(res.run_id, m.market_id, leg.side, book.token_id, round(price, 4), stake,
                                          decision_id=did, now=now)
                res.say(f"{m.market_id}: resting BUY {leg.side} ${stake:,.2f} @ {price:.3f} ({reason})")
            res.stats["orders"] = res.stats.get("orders", 0) + 1


def scan_window(accounts: dict[str, RuleAccount]) -> tuple[list[str], float, float]:
    """The categories (Kalshi's spelling) and the close-time window one listing must cover for every account."""
    cats = sorted({c for a in accounts.values() for lg in a.legs for c in lg.categories})
    lo = min(lg.min_days for a in accounts.values() for lg in a.legs)
    hi = max(lg.max_days for a in accounts.values() for lg in a.legs)
    return [KALSHI_NAMES.get(c, c.title()) for c in cats], lo, hi


def run_rules(main_cfg: dict, accounts: dict[str, RuleAccount], venue, root: str | Path, now: float | None = None,
              only: list[str] | None = None, listing: list[Market] | None = None, candles=None,
              asker=None) -> list[dict]:
    """One cycle of every rule account on one listing and one set of order books. A failing account is reported
    and does not stop the others. `asker`: a forecaster, or a function returning one, for the accounts that
    filter with Claude (built only when one of them runs)."""
    now = now or time.time()
    root = Path(root)
    accounts = {n: a for n, a in accounts.items() if not only or n in only}
    if not accounts:
        return []
    if listing is None:
        cats, lo, hi = scan_window(accounts)
        listing = venue.list_markets(categories=cats, min_days=lo, max_days=hi)
    shared = SharedVenue(venue, [])
    seen: dict[tuple, list] = {}

    def cached_candles(m, t):
        k = (m.market_id,)
        if k not in seen:
            seen[k] = candles(m, t) if candles else []
        return seen[k]

    out = []
    for name, acct in accounts.items():
        summary = {"account": name, "status": "error", "log": []}
        ledger = None
        try:
            cfg = account_config(main_cfg, acct)
            ledger = Ledger(root / "data" / "rules" / f"{name}.db")
            if ledger.deposits() == 0:
                ledger.deposit(float((cfg.get("account") or {}).get("paper_bankroll", 1000.0)), "deposit: paper bankroll")
            fc = None
            if acct.claude_filter:
                fc = asker() if callable(asker) and not hasattr(asker, "forecast") else asker
            trader = RuleTrader(cfg, ledger, shared, acct, [copy.copy(m) for m in listing], root=root,
                                candles=cached_candles, asker=fc)
            res = trader.run(now=now)
            summary.update(status=res.status, log=res.log, run_id=res.run_id, **res.stats)
        except Exception as e:                      # written down, and the next account still runs
            summary["log"].append(f"{type(e).__name__}: {e}")
        finally:
            if ledger is not None:
                ledger.close()
        out.append(summary)
    return out


def kalshi_candles(venue):
    """Daily bars of the last 10 days for one market, from Kalshi's public candlestick endpoint."""
    from .kalshi import series_of

    def get(m: Market, now: float) -> list[dict]:
        path = f"/series/{series_of(m.event_id)}/markets/{m.market_id}/candlesticks"
        return (venue.http.get(path, tries=3, start_ts=int(now - 10 * DAY), end_ts=int(now), period_interval=1440)
                or {}).get("candlesticks") or []
    return get
