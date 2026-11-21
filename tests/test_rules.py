"""The mechanical paper accounts (src/rules.py, rules.yaml, scripts/run_rules.py) on the fake Kalshi exchange."""
import sys
import time
from pathlib import Path

import pytest

from fakes import FakeKalshiHTTP
from src.book import Book
from src.kalshi import Kalshi
from src.ledger import Ledger
from src.rules import (Leg, RuleAccount, RuleTrader, account_config, fall_from_candles, kalshi_candles, load_rules,
                       run_rules, scan_window)
from src.venue import Market

ROOT = Path(__file__).resolve().parents[1]
NOW = 1_800_000_000.0
DAY = 86400.0
H = 3600.0


def cfg():
    return {"account": {"mode": "paper", "venue": "kalshi", "paper_bankroll": 1000.0},
            "universe": {"categories_allow": ["economics"]}, "forecaster": {}, "sizing": {},
            "execution": {"style": "passive"}, "fees": {"taker_rate": 0.07, "round_up_cents": True}, "safety": {}}


class Http(FakeKalshiHTTP):
    """The fake exchange plus an Entertainment series and the candlestick endpoint."""

    def __init__(self, now):
        super().__init__(now)
        self.series["KXRT"] = {"ticker": "KXRT", "category": "Entertainment", "fee_type": "quadratic", "fee_multiplier": 1, "tags": []}
        self.candles: dict[str, list] = {}

    def get(self, path, tries=6, **params):
        self.paths = getattr(self, "paths", []) + [path]
        if path.endswith("/candlesticks"):
            self.requests += 1
            return {"candlesticks": self.candles.get(path.split("/")[4], [])}
        return super().get(path, tries=tries, **params)


def bar(ts, bid, ask):
    return {"end_period_ts": ts, "yes_bid": {"close_dollars": f"{bid:.4f}"}, "yes_ask": {"close_dollars": f"{ask:.4f}"}}


def five_cent(**kw):
    return RuleAccount(name=kw.pop("name", "five"), about="5-cent", entry=kw.pop("entry", "resting"),
                       legs=[Leg(label="5c", categories=("economics",), max_yes_mid=0.05, max_spread=0.05, max_days=30,
                                 min_volume=45000, **kw.pop("leg", {}))], **kw)


def venue_for(http, now=NOW):
    http.now = now
    return Kalshi(http=http, clock=lambda: now)


def ledger(tmp_path, name):
    return Ledger(tmp_path / "data" / "rules" / f"{name}.db")


# ---- the configuration file --------------------------------------------------------------------------------------
def test_the_real_rules_file_loads():
    acc = load_rules(ROOT / "rules.yaml")
    assert {"rule_5c_busy", "rule_ent_band", "rule_combined", "control_5c_quiet", "control_ent_quiet"} <= set(acc)
    five = acc["rule_5c_busy"]
    assert five.entry == "resting" and five.stake_pct == 0.01 and not five.control
    leg = five.legs[0]
    assert leg.side == "NO" and leg.max_yes_mid == 0.05 and leg.min_volume == 45000 and leg.max_days == 30
    assert "economics" in leg.categories and "financials" in leg.categories and len(leg.categories) == 9
    assert len(acc["rule_combined"].legs) == 4 and acc["rule_combined"].stake_pct == 0.005
    assert acc["rule_ent_band"].legs[0].categories == ("entertainment",)
    assert acc["control_5c_quiet"].control and acc["control_5c_quiet"].legs[0].max_volume == 45000
    assert acc["rule_5c_busy_taker"].entry == "taker"
    assert acc["rule_ent_fall"].legs[0].min_fall_7d == 0.03


def write(tmp_path, text):
    p = tmp_path / "rules.yaml"
    p.write_text(text, encoding="utf-8")
    return p


@pytest.mark.parametrize("text, msg", [
    ("accounts:\n  a:\n    stake: 0.01\n    legs: [{categories: [Economics]}]\n", "unknown setting"),
    ("accounts:\n  a:\n    legs: [{categories: [Economics], max_mid: 0.05}]\n", "leg 1: unknown setting"),
    ("accounts:\n  a:\n    legs: [{categories: [Economics], side: maybe}]\n", "side must be"),
    ("accounts:\n  a:\n    entry: market\n    legs: [{categories: [Economics]}]\n", "entry must be"),
    ("accounts:\n  a:\n    about: nothing\n", "has no legs"),
    ("accounts:\n  bad-name:\n    legs: [{categories: [Economics]}]\n", "letters, digits"),
])
def test_rules_file_mistakes_are_errors(tmp_path, text, msg):
    with pytest.raises(ValueError, match=msg):
        load_rules(write(tmp_path, text))


def test_rules_file_defaults(tmp_path):
    assert load_rules(tmp_path / "missing.yaml") == {}
    acc = load_rules(write(tmp_path, "accounts:\n  a:\n    legs: [{categories: Entertainment, side: yes}]\n"))["a"]
    assert acc.legs[0].categories == ("entertainment",) and acc.legs[0].side == "YES" and acc.legs[0].label == "leg 1"
    assert acc.entry == "resting" and acc.event_cap_pct == 0.03 and acc.max_exposure_pct == 0.5


def test_account_config_and_scan_window():
    c = account_config(cfg(), five_cent(config={"safety": {"max_drawdown": 0.3}}))
    assert c["execution"]["resting_ttl_hours"] == 72 and c["execution"]["exit_on_forecast"] is False
    assert c["safety"] == {"max_drawdown": 0.3}
    assert account_config(cfg(), five_cent(entry="taker"))["execution"]["style"] == "taker"
    acc = load_rules(ROOT / "rules.yaml")
    cats, lo, hi = scan_window(acc)
    assert "Entertainment" in cats and "Climate and Weather" in cats and "Science and Technology" in cats
    assert lo == 0.25 and hi == 400


# ---- one leg ------------------------------------------------------------------------------------------------------
def mk(cat="economics", bid=0.03, ask=0.04, days=10, contracts=50000, closed=False):
    m = Market(market_id="M", question="q?", category=cat, end_ts=NOW + days * DAY, best_bid=bid, best_ask=ask, closed=closed)
    m.contracts = contracts
    return m


def book(bid, ask):
    return Book.from_levels("M:YES", [(bid, 100)] if bid else [], [(ask, 100)] if ask else [], ts=NOW)


def test_leg_listing_cut_has_slack_on_the_price_only():
    leg = five_cent().legs[0]
    assert leg.listed_fits(mk(), NOW)
    assert leg.listed_fits(mk(bid=0.06, ask=0.08), NOW)                 # 7c listed: within the 3c of slack
    assert not leg.listed_fits(mk(bid=0.08, ask=0.10), NOW)
    assert not leg.listed_fits(mk(cat="politics"), NOW)
    assert not leg.listed_fits(mk(contracts=44999), NOW) and not leg.listed_fits(mk(contracts=None), NOW)
    assert not leg.listed_fits(mk(days=31), NOW) and not leg.listed_fits(mk(days=0.2), NOW)
    assert not leg.listed_fits(mk(bid=None), NOW)
    quiet = Leg(label="q", categories=("economics",), max_volume=45000)
    assert quiet.listed_fits(mk(contracts=100), NOW) and not quiet.listed_fits(mk(contracts=45000), NOW)
    assert not quiet.listed_fits(mk(contracts=None), NOW)
    assert Leg(label="any", categories=("economics",)).listed_fits(mk(contracts=None), NOW)


def test_leg_check_on_a_fresh_book():
    leg = five_cent().legs[0]
    assert leg.check(book(0.03, 0.04), mk(), NOW) == ""
    assert leg.check(book(0.05, 0.05 + 0.01), mk(), NOW).startswith("YES mid 0.055")
    assert leg.check(book(0.01, 0.07), mk(), NOW).startswith("spread 0.060")
    assert leg.check(book(None, 0.04), mk(), NOW) == "one-sided book"
    assert leg.check(book(0.03, 0.04), mk(closed=True), NOW) == "closed"
    assert leg.check(book(0.03, 0.04), mk(days=40), NOW) == "days to the close outside the rule"
    assert "contracts traded" in leg.check(book(0.03, 0.04), mk(contracts=1000), NOW)
    band = Leg(label="b", categories=("entertainment",), min_yes_mid=0.05, max_yes_mid=0.345)
    assert band.check(book(0.03, 0.05), mk(), NOW).startswith("YES mid 0.040 outside")
    assert band.check(book(0.20, 0.22), mk(), NOW) == ""
    wide = Leg(label="w", categories=("x",), max_spread=0.5)
    assert wide.check(book(0.20, 0.32), mk(), NOW).startswith("spread 0.120 above 0.10")      # never wider than 10c
    fall = Leg(label="f", categories=("x",), min_fall_7d=0.03)
    assert fall.check(book(0.2, 0.22), mk(), NOW) == "no price from 7 days ago"
    assert fall.check(book(0.2, 0.22), mk(), NOW, fall_7d=0.02).startswith("YES fell +0.020")
    assert fall.check(book(0.2, 0.22), mk(), NOW, fall_7d=0.05) == ""


def test_fall_from_candles():
    bars = [bar(NOW - 9 * DAY, 0.30, 0.32), bar(NOW - 7 * DAY, 0.25, 0.27), bar(NOW - 1 * DAY, 0.20, 0.22)]
    assert fall_from_candles(bars, 0.21, NOW) == pytest.approx(0.05)
    assert fall_from_candles(bars[2:], 0.21, NOW) is None                # nothing from a week ago
    assert fall_from_candles([bar(NOW - 10 * DAY, 0.3, 0.32)], 0.21, NOW) is None     # too far back
    unquoted = [bar(NOW - 7 * DAY, 0.0, 0.27), {"end_period_ts": NOW - 7 * DAY}, bar(NOW - 8 * DAY, 0.28, 0.30)]
    assert fall_from_candles(unquoted, 0.21, NOW) == pytest.approx(0.08)
    assert fall_from_candles([], 0.2, NOW) is None and fall_from_candles(None, 0.2, NOW) is None


# ---- whole accounts on the fake exchange -------------------------------------------------------------------------
def test_resting_account_enters_once_fills_when_traded_through_and_settles(tmp_path):
    http = Http(NOW).add("KXCPIYOY-26NOV-T5", bid=0.03, ask=0.04, volume=50000, days=10)
    http.add("KXCPIYOY-26NOV-T6", bid=0.20, ask=0.22, volume=50000, days=10)       # not cheap enough
    http.add("KXCPIYOY-26NOV-T7", bid=0.02, ask=0.03, volume=1000, days=10)        # too quiet
    acc = {"five": five_cent(), "quiet": RuleAccount(name="quiet", about="q", control=True, legs=[
        Leg(label="q", categories=("economics",), max_yes_mid=0.05, max_spread=0.05, max_days=30, max_volume=45000)])}
    out = run_rules(cfg(), acc, venue_for(http), tmp_path, now=NOW)
    assert [s["status"] for s in out] == ["ok", "ok"]
    led = ledger(tmp_path, "five")
    o = led.q("SELECT * FROM orders")
    assert len(o) == 1 and o[0]["market_id"] == "KXCPIYOY-26NOV-T5" and o[0]["status"] == "resting"
    assert o[0]["outcome"] == "NO" and o[0]["limit_price"] == pytest.approx(0.96) and o[0]["usd"] == pytest.approx(10.0, abs=0.01)
    d = led.one("SELECT * FROM decisions WHERE action='BUY_NO'")
    assert "5c: YES 0.03/0.04, resting NO at 0.960" in d["reason"] and led.market("KXCPIYOY-26NOV-T5")["category"] == "economics"
    led.close()
    q = ledger(tmp_path, "quiet")
    assert [r["market_id"] for r in q.q("SELECT market_id FROM orders")] == ["KXCPIYOY-26NOV-T7"]
    q.close()

    # two hours later nothing new: one bet per market, and the price has not traded through the order
    run_rules(cfg(), {"five": acc["five"]}, venue_for(http, NOW + 2 * H), tmp_path, now=NOW + 2 * H)
    led = ledger(tmp_path, "five")
    assert led.one("SELECT COUNT(*) AS n FROM orders")["n"] == 1 and led.q("SELECT status FROM orders")[0]["status"] == "resting"
    led.close()

    # YES buyers lift the bid to 4c: the NO ask comes down to our 96c and the order fills
    http.set_book("KXCPIYOY-26NOV-T5", 0.04, 0.05)
    run_rules(cfg(), {"five": acc["five"]}, venue_for(http, NOW + 4 * H), tmp_path, now=NOW + 4 * H)
    led = ledger(tmp_path, "five")
    assert led.q("SELECT status FROM orders")[0]["status"] == "filled"
    pos = led.positions()
    assert len(pos) == 1 and pos[0]["outcome"] == "NO" and float(pos[0]["shares"]) == pytest.approx(10 / 0.96, abs=0.01)
    led.close()

    # it settles NO: the position pays $1 a contract; a settled market is not entered again
    http.settle("KXCPIYOY-26NOV-T5", "no")
    out = run_rules(cfg(), {"five": acc["five"]}, venue_for(http, NOW + 6 * H), tmp_path, now=NOW + 6 * H)
    led = ledger(tmp_path, "five")
    assert led.positions() == [] and led.cash() == pytest.approx(1000 - 10 + 10 / 0.96, abs=0.02)
    assert led.one("SELECT COUNT(*) AS n FROM orders")["n"] == 1
    led.close()
    assert any("settled" in line for line in out[0]["log"])


def test_taker_account_pays_the_ask_at_once(tmp_path):
    http = Http(NOW).add("KXCPIYOY-26NOV-T5", bid=0.03, ask=0.04, volume=50000, days=10, size=5000)
    run_rules(cfg(), {"tk": five_cent(name="tk", entry="taker")}, venue_for(http), tmp_path, now=NOW)
    led = ledger(tmp_path, "tk")
    f = led.q("SELECT * FROM fills WHERE side='BUY'")
    assert len(f) == 1 and f[0]["outcome"] == "NO" and f[0]["price"] == pytest.approx(0.97) and f[0]["fee"] > 0
    assert led.q("SELECT status FROM orders")[0]["status"] == "filled"
    led.close()


def test_event_cap_and_book_limit(tmp_path):
    http = Http(NOW)
    for i in range(5):
        http.add(f"KXCPIYOY-26NOV-T{i}", bid=0.03, ask=0.04, volume=50000, days=10)     # all one event
    run_rules(cfg(), {"five": five_cent()}, venue_for(http), tmp_path, now=NOW)
    led = ledger(tmp_path, "five")
    assert led.one("SELECT COUNT(*) AS n FROM orders")["n"] == 3                         # 3% event cap at 1% a bet
    skips = led.q("SELECT reason FROM decisions WHERE action='SKIP'")
    assert len(skips) == 2 and all("bound by event cap" in s["reason"] for s in skips)
    led.close()
    run_rules(cfg(), {"few": five_cent(name="few", max_books=2)}, venue_for(http), tmp_path, now=NOW)
    led = ledger(tmp_path, "few")
    assert led.one("SELECT COUNT(*) AS n FROM decisions")["n"] == 2
    led.close()


def test_the_seven_day_fall_rule_reads_the_price_history(tmp_path):
    http = Http(NOW)
    http.add("KXRT-26NOV-A", series="KXRT", bid=0.18, ask=0.20, volume=9000, days=20)
    http.add("KXRT-26NOV-B", series="KXRT", bid=0.18, ask=0.20, volume=9000, days=20)
    http.candles["KXRT-26NOV-A"] = [bar(NOW - 7 * DAY, 0.24, 0.26), bar(NOW - DAY, 0.19, 0.21)]   # fell 6c
    http.candles["KXRT-26NOV-B"] = [bar(NOW - 7 * DAY, 0.19, 0.21)]                               # flat
    acct = RuleAccount(name="fall", about="f", legs=[Leg(label="fall", categories=("entertainment",), min_yes_mid=0.10,
                                                         max_yes_mid=0.245, min_volume=5000, min_fall_7d=0.03)])
    v = venue_for(http)
    out = run_rules(cfg(), {"fall": acct}, v, tmp_path, now=NOW, candles=kalshi_candles(v))
    led = ledger(tmp_path, "fall")
    assert [r["market_id"] for r in led.q("SELECT market_id FROM orders")] == ["KXRT-26NOV-A"]
    assert led.q("SELECT limit_price FROM orders")[0]["limit_price"] == pytest.approx(0.80)
    led.close()
    assert "not now: {'YES': 1}" in " ".join(out[0]["log"])


def test_a_failing_account_does_not_stop_the_others(tmp_path, monkeypatch):
    http = Http(NOW).add("KXCPIYOY-26NOV-T5", bid=0.03, ask=0.04, volume=50000, days=10)
    bad = five_cent(name="bad", entry="resting")
    bad.stake_pct = "lots"                                  # breaks the stake arithmetic
    out = run_rules(cfg(), {"bad": bad, "good": five_cent(name="good")}, venue_for(http), tmp_path, now=NOW)
    assert out[0]["status"] == "error" and "TypeError" in out[0]["log"][-1]
    assert out[1]["status"] == "ok" and out[1]["orders"] == 1
    assert run_rules(cfg(), {"good": five_cent(name="good")}, venue_for(http), tmp_path, now=NOW, only=["nobody"]) == []


def test_kill_switch_stops_new_bets(tmp_path):
    http = Http(NOW).add("KXCPIYOY-26NOV-T5", bid=0.03, ask=0.04, volume=50000, days=10)
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "data" / "STOP").write_text("stop", encoding="utf-8")
    out = run_rules(cfg(), {"five": five_cent()}, venue_for(http), tmp_path, now=NOW)
    assert out[0]["status"] == "stopped" and out[0].get("orders", 0) == 0


def test_no_price_to_rest_at_is_recorded(tmp_path):
    http = Http(NOW).add("KXCPIYOY-26NOV-T5", bid=0.03, ask=0.04, volume=50000, days=10)
    v = venue_for(http)
    listing = v.list_markets(categories=["Economics"], min_days=0.25, max_days=30)
    led = ledger(tmp_path, "five")
    led.deposit(1000.0)
    t = RuleTrader(account_config(cfg(), five_cent()), led, v, five_cent(), listing, root=tmp_path)
    m = listing[0]
    yes = Book.from_levels(f"{m.market_id}:YES", [(0.03, 10)], [(0.04, 10)], ts=NOW)
    no = Book.from_levels(f"{m.market_id}:NO", [], [(0.97, 10)], ts=NOW)
    from src.trader import CycleResult
    t.entries([(m, five_cent().legs[0], yes, no)], 1000.0, None, CycleResult("r"), NOW)
    assert "no NO price to resting" in led.one("SELECT reason FROM decisions")["reason"]
    led.close()


# ---- the script ----------------------------------------------------------------------------------------------------
def test_run_rules_script_report(tmp_path, monkeypatch, capsys):
    sys.path.insert(0, str(ROOT / "scripts"))
    import run_rules as script
    monkeypatch.setattr(script, "ROOT", tmp_path)
    acc = {"five": five_cent()}
    assert script.report(acc) == 0 and "five" in capsys.readouterr().out
    http = Http(NOW).add("KXCPIYOY-26NOV-T5", bid=0.04, ask=0.05, volume=50000, days=10, size=5000)
    run_rules(cfg(), {"five": five_cent(entry="taker")}, venue_for(http), tmp_path, now=NOW)
    http.settle("KXCPIYOY-26NOV-T5", "yes")                 # the rare total loss
    run_rules(cfg(), {"five": five_cent(entry="taker")}, venue_for(http, NOW + H), tmp_path, now=NOW + H)
    s = script.settled_stats(tmp_path / "data" / "rules" / "five.db")
    assert s["n"] == 1 and s["lost"] == 1 and s["paid"] == 0 and s["cost"] == pytest.approx(10.0, abs=0.01)
    assert script.settled_stats(tmp_path / "nothing.db") == {"n": 0}
    script.report(acc)
    out = capsys.readouterr().out
    assert "-100.0%" in out and "CONTROL" in out


RULES_YAML = """accounts:
  five:
    about: the 5-cent rule
    legs: [{label: 5c, categories: [Economics], max_yes_mid: 0.05, max_spread: 0.05, max_days: 30, min_volume: 45000}]
"""


@pytest.fixture
def script(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    import yaml

    import run_rules as mod
    from src import runtime
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(runtime, "lower_priority", lambda: None)
    c = cfg()
    c["runtime"] = {"low_priority": False}
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(c), encoding="utf-8")
    (tmp_path / "rules.yaml").write_text(RULES_YAML, encoding="utf-8")
    http = Http(time.time()).add("KXCPIYOY-26NOV-T5", bid=0.03, ask=0.04, volume=50000, days=10)
    built = []

    def make(**kw):
        built.append(kw)
        return Kalshi(http=http)
    monkeypatch.setattr(mod, "Kalshi", make)
    mod.http, mod.built = http, built
    return mod


def args(monkeypatch, tmp_path, *extra):
    monkeypatch.setattr(sys, "argv", ["run_rules.py", "--config", str(tmp_path / "config.yaml"),
                                      "--rules", str(tmp_path / "rules.yaml"), *extra])


def test_script_runs_the_accounts_then_reports(script, tmp_path, monkeypatch, capsys):
    args(monkeypatch, tmp_path)
    assert script.main() == 0
    out = capsys.readouterr().out
    assert "[five] ok: 1 qualifying, 1 orders" in out and "resting BUY NO" in out and "rule accounts: 1 in" in out
    assert script.built[0]["cache_dir"] == tmp_path / "data" / "rules" and script.built[0]["listing_cache_hours"] == 6.0
    assert not (tmp_path / "data" / "cycle.lock").exists()
    args(monkeypatch, tmp_path, "--report")
    assert script.main() == 0
    assert "five" in capsys.readouterr().out


def test_script_skips_while_a_cycle_runs_and_when_nothing_is_defined(script, tmp_path, monkeypatch, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "cycle.lock").write_text("a cycle", encoding="utf-8")
    args(monkeypatch, tmp_path)
    assert script.main() == 3 and "rule accounts skipped: another cycle holds" in capsys.readouterr().out
    (tmp_path / "rules.yaml").write_text("accounts: {}\n", encoding="utf-8")
    assert script.main() == 0 and "no rule accounts defined" in capsys.readouterr().out


def test_script_quiet_window_and_every_account_failing(script, tmp_path, monkeypatch, capsys):
    import yaml
    c = cfg()
    c["runtime"] = {"low_priority": False, "quiet_windows": ["00:00-24:00"]}
    (tmp_path / "quiet.yaml").write_text(yaml.safe_dump(c), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["run_rules.py", "--config", str(tmp_path / "quiet.yaml"), "--rules", str(tmp_path / "rules.yaml")])
    assert script.main() == 3 and "rule accounts skipped: quiet window" in capsys.readouterr().out
    monkeypatch.setattr(script, "run_rules", lambda *a, **k: [{"account": "five", "status": "error", "log": ["Boom: failed"]}])
    args(monkeypatch, tmp_path)
    assert script.main() == 1 and "    Boom: failed" in capsys.readouterr().out


def test_each_cycle_reads_a_fresh_sample_of_books(tmp_path):
    http = Http(NOW)
    for i in range(30):
        http.add(f"KXCPIYOY-26NOV-T{i}", bid=0.20, ask=0.22, volume=50000, days=10)    # listed near the band, not in it
        http.markets[f"KXCPIYOY-26NOV-T{i}"].update(yes_bid_dollars="0.0300", yes_ask_dollars="0.0400")
    read = []
    for k in range(3):
        http.paths = []
        run_rules(cfg(), {"few": five_cent(name="few", max_books=5)}, venue_for(http, NOW + k * H), tmp_path, now=NOW + k * H)
        read.append({p.split("/")[2] for p in http.paths if p.endswith("/orderbook")})
    led = ledger(tmp_path, "few")
    assert led.one("SELECT COUNT(*) AS n FROM orders")["n"] == 0 and int(led.get_meta("scan_round")) == 3
    led.close()
    assert all(len(r) == 5 for r in read) and len(read[0] | read[1] | read[2]) > 5     # not the same five each time


# ---- Claude as a filter -------------------------------------------------------------------------------------------
def test_claude_filter_keeps_vetoes_and_waits(tmp_path):
    from fakes import TableForecaster
    http = Http(NOW)
    for t in ("A", "B", "C", "D"):
        http.add(f"KXCPIYOY-26NOV-{t}", bid=0.03, ask=0.04, volume=50000, days=10)
    acct = five_cent(name="cl", claude_filter=True, max_asks=3)
    fc = TableForecaster({"KXCPIYOY-26NOV-A": 0.01, "KXCPIYOY-26NOV-B": 0.10,
                          "KXCPIYOY-26NOV-C": {"p_yes": 0.01, "rules_clear": False}})
    out = run_rules(cfg(), {"cl": acct}, venue_for(http), tmp_path, now=NOW, asker=lambda: fc)
    led = ledger(tmp_path, "cl")
    asked = set(fc.asked)
    assert len(asked) == 3 and out[0]["claude_asked"] == 3 and out[0]["claude_waiting"] == 1
    orders = [r["market_id"] for r in led.q("SELECT market_id FROM orders")]
    vetoes = {r["market_id"]: r["reason"] for r in led.q("SELECT market_id, reason FROM decisions WHERE action='VETO'")}
    if "KXCPIYOY-26NOV-A" in asked:
        assert orders == ["KXCPIYOY-26NOV-A"]
        d = led.one("SELECT * FROM decisions WHERE action='BUY_NO'")
        assert d["forecast_id"] is not None and d["p_model"] == pytest.approx(0.01)
    if "KXCPIYOY-26NOV-B" in asked:
        assert "Claude gives NO 0.900, under the 0.960" in vetoes["KXCPIYOY-26NOV-B"]
    if "KXCPIYOY-26NOV-C" in asked:
        assert "not clear" in vetoes["KXCPIYOY-26NOV-C"]
    assert len(led.q("SELECT * FROM forecasts")) == len(asked & {"KXCPIYOY-26NOV-A", "KXCPIYOY-26NOV-B", "KXCPIYOY-26NOV-C"})
    led.close()
    # next cycle: the market that waited (or got no answer) is asked; vetoed and ordered ones are not asked again
    fc.asked.clear()
    run_rules(cfg(), {"cl": acct}, venue_for(http, NOW + 2 * H), tmp_path, now=NOW + 2 * H, asker=fc)
    every = {f"KXCPIYOY-26NOV-{t}" for t in "ABCD"}
    no_answer = {"KXCPIYOY-26NOV-D"} & asked                            # D is not in the table: asked again
    assert set(fc.asked) == (every - asked) | no_answer


def test_claude_filter_needs_a_forecaster_and_survives_its_failures(tmp_path):
    from fakes import TableForecaster
    http = Http(NOW).add("KXCPIYOY-26NOV-T5", bid=0.03, ask=0.04, volume=50000, days=10)
    acct = five_cent(name="cl", claude_filter=True)
    out = run_rules(cfg(), {"cl": acct}, venue_for(http), tmp_path, now=NOW)
    assert out[0]["status"] == "error" and "no forecaster" in out[0]["log"][-1]

    class Broken(TableForecaster):
        def forecast(self, m, now=None):
            raise RuntimeError("claude is down")
    out = run_rules(cfg(), {"cl": acct}, venue_for(http), tmp_path, now=NOW, asker=Broken({}))
    assert out[0]["status"] == "ok" and any("forecaster failed" in line for line in out[0]["log"])
    out = run_rules(cfg(), {"cl": acct}, venue_for(http), tmp_path, now=NOW + H, asker=TableForecaster({}))
    assert any("no usable forecast" in line and "asked again next cycle" in line for line in out[0]["log"])
    led = ledger(tmp_path, "cl")
    assert led.q("SELECT * FROM orders") == [] and led.q("SELECT * FROM decisions WHERE action='VETO'") == []
    led.close()


def test_the_real_file_has_the_claude_filtered_account():
    a = load_rules(ROOT / "rules.yaml")["rule_5c_busy_claude"]
    assert a.claude_filter and a.max_asks == 2 and a.legs[0].min_volume == 45000
