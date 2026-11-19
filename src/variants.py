"""Variant paper accounts: the same Claude forecasts, traded under different rules, side by side.

The main account (data/pmt.db) asks Claude and trades a cautious blend of Claude's number and the market price.
A variant account never asks Claude anything. After each main cycle it is handed the forecasts the main account
has just made and runs the same trading cycle (same code: Trader, broker, safety checks, fees) with a few
settings changed: Claude's number alone instead of the blend, paying the ask instead of resting a bid, and so on.
Each variant has its own ledger under data/variants/, its own $1,000, and costs no Claude usage.

Two of the variants are controls. One bets against Claude, one bets in a fixed pseudo-random direction with the
size of Claude's disagreement. If Claude's forecasts carry information, the accounts that follow it should end
ahead of both; if they do not, that is the answer.

What keeps the comparison fair:
  - one set of prices: every variant in a run sees the same order books, read once and shared (SharedVenue), and
    decides at the same instant;
  - one set of limits: the stake caps, the daily budget and the safety stops are the main account's unless a
    variant's whole point is to change one;
  - each forecast is handed to each variant exactly once.

What it cannot do: a variant can hold a market the main account does not hold, and only markets the main account
holds are re-forecast early. A variant's position is therefore usually held to settlement without a second look.

Many accounts means many chances for one to look good by luck. Read them against the controls and against each
other, not one at a time, and say how many there are whenever one is quoted.
"""
from __future__ import annotations

import copy
import json
import time
import zlib
from pathlib import Path

import yaml

from . import safety
from .forecast import P_CEIL, P_FLOOR, Forecast
from .ledger import Ledger
from .trader import Trader

TRANSFORMS = ("none", "fade", "coinflip")


def merge(base: dict, over: dict | None) -> dict:
    """A deep copy of `base` with `over` laid on top, section by section."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else copy.deepcopy(v)
    return out


def load_variants(path: str | Path) -> dict[str, dict]:
    """variants.yaml -> {name: {"about": str, "transform": str, "overrides": dict}}. A file that is missing means
    no variants; a variant with an unknown transform is an error worth seeing."""
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = (yaml.safe_load(f) or {}).get("variants") or {}
    out = {}
    for name, spec in raw.items():
        spec = spec or {}
        transform = str(spec.get("transform", "none")).lower()
        if transform not in TRANSFORMS:
            raise ValueError(f"variant {name!r}: unknown transform {transform!r} (one of {', '.join(TRANSFORMS)})")
        if not str(name).replace("_", "").isalnum():
            raise ValueError(f"variant name {name!r}: letters, digits and underscores only (it becomes a file name)")
        out[str(name)] = {"about": str(spec.get("about", "")), "transform": transform, "overrides": spec.get("overrides") or {}}
    return out


def transformed(p: float, mid: float | None, transform: str, market_id: str) -> float:
    """The probability a control account trades on. fade: as far from the market price as Claude, on the other
    side. coinflip: as far from the market price as Claude, on a side fixed by the market's name."""
    if transform == "none" or mid is None:
        return p
    gap = p - mid
    if transform == "fade":
        gap = -gap
    elif transform == "coinflip":
        gap = abs(gap) if zlib.crc32(market_id.encode("utf-8")) % 2 == 0 else -abs(gap)
    return min(max(mid + gap, P_FLOOR), P_CEIL)


class ReplayForecaster:
    """Answers from forecasts the main account has already paid for. rows: market_id -> main-ledger forecast row."""

    name = "replay"

    def __init__(self, rows: dict, transform: str = "none"):
        self.rows, self.transform, self.last_error = rows, transform, ""

    def forecast(self, m, now: float | None = None) -> Forecast | None:
        r = self.rows.get(m.market_id)
        if r is None:
            self.last_error = "the main account has no new forecast for this market"
            return None
        mid = r["market_mid"]
        t = lambda p: round(transformed(float(p), mid, self.transform, m.market_id), 4)
        note = "" if self.transform == "none" else f" ({self.transform} of it: a control, not Claude's view)"
        return Forecast(market_id=m.market_id, p_yes=t(r["p_yes"]), p_runs=[t(x) for x in json.loads(r["p_runs"] or "[]")],
                        confidence=r["confidence"] or "low", rules_clear=bool(r["rules_clear"]),
                        flags=json.loads(r["flags"] or "[]"), rationale=f"replay of main forecast {r['id']}{note}",
                        sources=[], backend=f"replay:{self.transform}", model=r["model"] or "", cost_usd=0.0, ts=float(r["ts"]))


class SharedVenue:
    """The real venue, for one run of all the variants: every answer is fetched once and then shared, so each
    account sees the same prices, and the listing is only the markets the main account has just forecast."""

    def __init__(self, inner, market_ids):
        self.inner, self.ids = inner, list(dict.fromkeys(market_ids))
        self._cache: dict[tuple, object] = {}

    @property
    def requests(self):
        return getattr(self.inner, "requests", None)

    @property
    def rate_limited(self):
        return getattr(self.inner, "rate_limited", 0)

    def _once(self, kind: str, key: str, fetch):
        k = (kind, key)
        if k not in self._cache:
            self._cache[k] = fetch()
        return self._cache[k]

    @staticmethod
    def _own(m):
        """A market object the caller may mark up (the trader does) without the next account seeing it."""
        if m is None:
            return None
        c = copy.copy(m)
        c.raw = dict(m.raw)
        return c

    def list_markets(self, **_):
        out = []
        for mid in self.ids:
            try:
                m = self.market(mid)
            except Exception:                       # one market's trouble is not the run's
                m = None
            if m is not None and not m.closed:
                out.append(m)
        return out

    def market(self, market_id: str):
        return self._own(self._once("market", market_id, lambda: self.inner.market(market_id)))

    def enrich(self, listed):
        return self._own(self._once("enrich", listed.market_id, lambda: self.inner.enrich(listed)))

    def books(self, market_id: str):
        return self._once("books", market_id, lambda: self.inner.books(market_id))

    def is_closed(self, market_id: str) -> bool:
        return self._once("closed", market_id, lambda: self.inner.is_closed(market_id))

    def settlement(self, market_id: str):
        return self._once("settlement", market_id, lambda: self.inner.settlement(market_id))


def variant_config(main_cfg: dict, overrides: dict) -> dict:
    """The main configuration with the variant's changes. A variant never tracks prices for scoring forecasts
    (that is the main account's job, and it would multiply the requests), unless it says otherwise."""
    cfg = merge(main_cfg, {"execution": {"track_forecasts_days": 0}})
    return merge(cfg, overrides)


def run_variants(main_cfg: dict, variants: dict[str, dict], main_ledger: Ledger, venue, root: str | Path,
                 now: float | None = None, only: list[str] | None = None) -> list[dict]:
    """One cycle of every variant account on the forecasts the main account made within the forecast age limit.
    Returns one summary per variant. A variant that fails is reported and does not stop the others."""
    now = now or time.time()
    root = Path(root)
    max_age = safety.settings(main_cfg)["max_forecast_age_hours"] * 3600.0
    fresh = main_ledger.q("SELECT * FROM forecasts WHERE ts >= ? ORDER BY id", (now - max_age,))
    newest = max((int(r["id"]) for r in fresh), default=0)
    shared = SharedVenue(venue, [r["market_id"] for r in fresh])
    out = []
    for name, spec in variants.items():
        if only and name not in only:
            continue
        summary = {"variant": name, "status": "error", "log": []}
        ledger = None
        try:
            cfg = variant_config(main_cfg, spec["overrides"])
            ledger = Ledger(root / "data" / "variants" / f"{name}.db")
            if ledger.deposits() == 0:
                ledger.deposit(float((cfg.get("account") or {}).get("paper_bankroll", 1000.0)), "deposit: paper bankroll")
            seen = int(ledger.get_meta("replay_last_id", 0) or 0)
            rows = {r["market_id"]: r for r in fresh if int(r["id"]) > seen}        # the newest per market wins
            trader = Trader(cfg, ledger, shared, ReplayForecaster(rows, spec["transform"]), root=root)
            res = trader.run(now=now)
            ledger.set_meta("replay_last_id", max(seen, newest))
            summary.update(status=res.status, log=res.log, run_id=res.run_id, handed=len(rows), **res.stats)
        except Exception as e:                      # written down, and the next variant still runs
            summary["log"].append(f"{type(e).__name__}: {e}")
        finally:
            if ledger is not None:
                ledger.close()
        out.append(summary)
    return out


def standings(root: str | Path, variants: dict[str, dict], main_db: str | Path | None = None) -> list[dict]:
    """Where every account stands, the main one first. Equity values positions at the bid, as everywhere else."""
    root = Path(root)
    books = [("main", Path(main_db) if main_db else root / "data" / "pmt.db", "the paper bot itself: Claude blended with the market price")]
    books += [(n, root / "data" / "variants" / f"{n}.db", s["about"]) for n, s in variants.items()]
    out = []
    for name, path, about in books:
        if not path.exists():
            out.append({"account": name, "about": about, "started": None})
            continue
        led = Ledger(path)
        try:
            eq = led.last_equity()
            dep = led.deposits()
            orders = {r["status"]: r["n"] for r in led.q("SELECT status, COUNT(*) AS n FROM orders WHERE side='BUY' GROUP BY status")}
            first = led.one("SELECT MIN(started) AS t FROM runs")["t"]
            settled = led.one("SELECT COUNT(DISTINCT market_id) AS n FROM fills WHERE side='SETTLE'")["n"]
            out.append({"account": name, "about": about, "started": first, "deposited": dep,
                        "equity": float(eq["equity"]) if eq else dep, "cash": led.cash(),
                        "positions": len(led.positions()), "resting": orders.get("resting", 0),
                        "filled": orders.get("filled", 0), "expired": orders.get("expired", 0),
                        "cancelled": orders.get("cancelled", 0), "settled_markets": int(settled or 0),
                        "forecasts": led.one("SELECT COUNT(*) AS n FROM forecasts")["n"],
                        "buys_decided": led.one("SELECT COUNT(*) AS n FROM decisions WHERE action LIKE 'BUY_%'")["n"]})
        finally:
            led.close()
    return out
