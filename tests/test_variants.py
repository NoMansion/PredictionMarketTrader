import pytest

from fakes import FakeKalshiHTTP, TableForecaster
from src.kalshi import Kalshi
from src.ledger import Ledger
from src.trader import Trader
from src.variants import (ReplayForecaster, SharedVenue, load_variants, merge, run_variants, standings, transformed,
                          variant_config)

NOW = 1_800_000_000.0
H = 3600.0
T = "KXCPIYOY-26NOV-T3.6"


def cfg():
    return {"account": {"mode": "paper", "venue": "kalshi", "paper_bankroll": 1000.0},
            "universe": {"categories_allow": ["economics"], "categories_deny": ["sports"]},
            "forecaster": {}, "sizing": {"shrink_weight": 0.3}, "execution": {"style": "passive"},
            "fees": {"taker_rate": 0.07, "round_up_cents": True}, "safety": {}}


VARIANTS = {
    "claude_only": {"about": "claude alone", "transform": "none", "overrides": {"sizing": {"shrink_weight": 1.0, "max_disagreement": 1.0}}},
    "control_fade": {"about": "against claude", "transform": "fade", "overrides": {"sizing": {"shrink_weight": 1.0, "max_disagreement": 1.0}}},
}


def main_cycle(tmp_path, http, table, now=NOW):
    """One cycle of the main account on the fake exchange. Returns its ledger (the caller closes it)."""
    led = Ledger(tmp_path / "data" / "pmt.db")
    if led.deposits() == 0:
        led.deposit(1000.0)
    venue = Kalshi(http=http, clock=lambda: now)
    http.now = now
    Trader(cfg(), led, venue, TableForecaster(table), root=tmp_path).run(now=now)
    return led


def variant_ledger(tmp_path, name):
    return Ledger(tmp_path / "data" / "variants" / f"{name}.db")


def test_merge_and_variant_config_leave_the_main_config_alone():
    base = cfg()
    out = variant_config(base, {"sizing": {"shrink_weight": 1.0}, "execution": {"style": "taker"}})
    assert out["sizing"]["shrink_weight"] == 1.0 and out["execution"] == {"style": "taker", "track_forecasts_days": 0}
    assert base["sizing"] == {"shrink_weight": 0.3} and base["execution"] == {"style": "passive"}
    assert merge({"a": {"b": 1, "c": 2}}, {"a": {"c": 3}, "d": 4}) == {"a": {"b": 1, "c": 3}, "d": 4}


def test_control_transforms():
    assert transformed(0.60, 0.49, "none", "M") == 0.60
    assert transformed(0.60, 0.49, "fade", "M") == pytest.approx(0.38)
    flips = {transformed(0.60, 0.49, "coinflip", f"M{i}") for i in range(40)}
    assert {round(x, 2) for x in flips} == {0.38, 0.60}                 # Claude's distance, either side
    assert transformed(0.60, 0.49, "coinflip", "M7") == transformed(0.60, 0.49, "coinflip", "M7")    # fixed per market
    assert transformed(0.99, 0.10, "fade", "M") == 0.02                 # kept inside the forecaster's own bounds
    assert transformed(0.60, None, "fade", "M") == 0.60                 # no price recorded: nothing to mirror


def test_the_same_forecast_is_traded_differently_by_each_account(tmp_path):
    http = FakeKalshiHTTP(NOW).add(T, bid=0.48, ask=0.50)
    main = main_cycle(tmp_path, http, {T: 0.60})
    # the blend moves 30% of the way from 0.49 to 0.60: not enough edge for the main account
    assert main.q("SELECT * FROM orders") == [] and len(main.q("SELECT * FROM forecasts")) == 1
    before = http.requests
    out = run_variants(cfg(), VARIANTS, main, Kalshi(http=http, clock=lambda: NOW + 60), tmp_path, now=NOW + 60)
    assert [s["status"] for s in out] == ["ok", "ok"] and all(s["handed"] == 1 for s in out), out
    asked = http.requests - before

    co, fade = variant_ledger(tmp_path, "claude_only"), variant_ledger(tmp_path, "control_fade")
    o1, o2 = co.q("SELECT * FROM orders"), fade.q("SELECT * FROM orders")
    assert len(o1) == 1 and o1[0]["outcome"] == "YES" and o1[0]["status"] == "resting"      # Claude says 0.60: buy YES
    assert len(o2) == 1 and o2[0]["outcome"] == "NO"                                         # the control takes the other side
    f1, f2 = co.one("SELECT * FROM forecasts"), fade.one("SELECT * FROM forecasts")
    assert f1["p_yes"] == pytest.approx(0.60) and f2["p_yes"] == pytest.approx(0.38)
    assert f1["backend"] == "replay:none" and f1["cost_usd"] == 0 and f1["ts"] == pytest.approx(NOW)   # the original forecast, free
    assert co.deposits() == 1000.0 and fade.deposits() == 1000.0
    # both accounts decided on the same prices
    d1, d2 = co.one("SELECT p_market FROM decisions"), fade.one("SELECT p_market FROM decisions")
    assert d1["p_market"] == d2["p_market"] == pytest.approx(0.49)
    for led in (co, fade):
        led.close()

    # prices were read once and shared: a second account costs no further requests
    http2 = FakeKalshiHTTP(NOW).add(T, bid=0.48, ask=0.50)
    main2 = main_cycle(tmp_path / "solo", http2, {T: 0.60})
    before2 = http2.requests
    run_variants(cfg(), {"claude_only": VARIANTS["claude_only"]}, main2, Kalshi(http=http2, clock=lambda: NOW + 60),
                 tmp_path / "solo", now=NOW + 60)
    assert asked == http2.requests - before2
    main.close(); main2.close()


def test_a_forecast_is_handed_over_once(tmp_path):
    http = FakeKalshiHTTP(NOW).add(T, bid=0.48, ask=0.50)
    main = main_cycle(tmp_path, http, {T: 0.60})
    one = {"claude_only": VARIANTS["claude_only"]}
    run_variants(cfg(), one, main, Kalshi(http=http, clock=lambda: NOW + 60), tmp_path, now=NOW + 60)
    again = run_variants(cfg(), one, main, Kalshi(http=http, clock=lambda: NOW + 2 * H), tmp_path, now=NOW + 2 * H)
    assert again[0]["status"] == "ok" and again[0]["handed"] == 0
    led = variant_ledger(tmp_path, "claude_only")
    assert len(led.q("SELECT * FROM forecasts")) == 1
    orders = led.q("SELECT * FROM orders")
    assert len(orders) == 1 and orders[0]["status"] == "resting"       # not cancelled and placed again
    led.close(); main.close()


def test_resting_order_fills_and_settles_in_the_variant_ledger(tmp_path):
    http = FakeKalshiHTTP(NOW).add(T, bid=0.48, ask=0.50)
    main = main_cycle(tmp_path, http, {T: 0.60})
    one = {"claude_only": VARIANTS["claude_only"]}
    run_variants(cfg(), one, main, Kalshi(http=http, clock=lambda: NOW + 60), tmp_path, now=NOW + 60)
    http.set_book(T, 0.47, 0.49)                                         # the ask comes down to the resting bid
    t2 = NOW + 4 * H
    run_variants(cfg(), one, main, Kalshi(http=http, clock=lambda: t2), tmp_path, now=t2)
    led = variant_ledger(tmp_path, "claude_only")
    assert len(led.positions()) == 1 and led.positions()[0]["outcome"] == "YES"
    led.close()
    http.settle(T, "yes")
    t3 = NOW + 30 * 24 * H
    run_variants(cfg(), one, main, Kalshi(http=http, clock=lambda: t3), tmp_path, now=t3)
    led = variant_ledger(tmp_path, "claude_only")
    assert led.positions() == [] and led.cash() > 1000.0
    led.close()
    rows = standings(tmp_path, one)
    assert [r["account"] for r in rows] == ["main", "claude_only"]
    assert rows[1]["equity"] > 1000.0 and rows[1]["settled_markets"] == 1 and rows[1]["filled"] == 1
    assert rows[0]["equity"] == 1000.0
    main.close()


def test_low_confidence_is_traded_only_where_the_variant_says_so(tmp_path):
    http = FakeKalshiHTTP(NOW).add(T, bid=0.48, ask=0.50)
    main = main_cycle(tmp_path, http, {T: {"p_yes": 0.60, "confidence": "low"}})
    both = {"claude_only": VARIANTS["claude_only"],
            "unfiltered": {"about": "", "transform": "none",
                           "overrides": {"sizing": {"shrink_weight": 1.0, "max_disagreement": 1.0},
                                         "execution": {"trade_low_confidence": True}}}}
    run_variants(cfg(), both, main, Kalshi(http=http, clock=lambda: NOW + 60), tmp_path, now=NOW + 60)
    a, b = variant_ledger(tmp_path, "claude_only"), variant_ledger(tmp_path, "unfiltered")
    assert a.q("SELECT * FROM orders") == [] and "confidence is low" in a.one("SELECT reason FROM decisions")["reason"]
    assert len(b.q("SELECT * FROM orders")) == 1
    a.close(); b.close(); main.close()


def test_one_broken_variant_does_not_stop_the_others(tmp_path):
    http = FakeKalshiHTTP(NOW).add(T, bid=0.48, ask=0.50)
    main = main_cycle(tmp_path, http, {T: 0.60})
    mixed = {"broken": {"about": "", "transform": "none", "overrides": {"sizing": {"no_such_setting": 1}}},
             "claude_only": VARIANTS["claude_only"]}
    out = run_variants(cfg(), mixed, main, Kalshi(http=http, clock=lambda: NOW + 60), tmp_path, now=NOW + 60)
    assert out[0]["status"] == "error" and "no_such_setting" in out[0]["log"][0]
    assert out[1]["status"] == "ok" and out[1]["orders"] == 1
    main.close()


def test_old_forecasts_are_not_replayed(tmp_path):
    http = FakeKalshiHTTP(NOW).add(T, bid=0.48, ask=0.50)
    main = main_cycle(tmp_path, http, {T: 0.60})
    late = NOW + 7 * H                                                   # past the 6-hour forecast age limit
    out = run_variants(cfg(), {"claude_only": VARIANTS["claude_only"]}, main, Kalshi(http=http, clock=lambda: late),
                       tmp_path, now=late)
    assert out[0]["handed"] == 0 and out[0].get("orders", 0) == 0
    main.close()


def test_shared_venue_hands_out_private_copies_and_fetches_once(tmp_path):
    http = FakeKalshiHTTP(NOW).add(T)
    shared = SharedVenue(Kalshi(http=http, clock=lambda: NOW), [T, T, "MISSING"])
    a, b = shared.list_markets(), shared.list_markets()
    assert [m.market_id for m in a] == [T] and a[0] is not b[0]
    a[0].raw["lite"] = True
    assert "lite" not in b[0].raw
    n = http.requests
    shared.books(T); shared.books(T); shared.market(T); shared.is_closed(T); shared.is_closed(T)
    assert http.requests == n + 2                                         # one book, one status; the market was cached


def test_replay_forecaster_reports_why_it_has_nothing():
    fc = ReplayForecaster({})

    class M:
        market_id = "X"
    assert fc.forecast(M()) is None and "no new forecast" in fc.last_error


def test_variants_file_is_valid_and_every_variant_builds_a_trader(tmp_path):
    from pathlib import Path

    from src.config import load_config
    root = Path(__file__).resolve().parent.parent
    variants = load_variants(root / "variants.yaml")
    assert {"claude_only", "control_fade", "control_coinflip"} <= set(variants)
    main_cfg = load_config(root / "config.yaml")
    for name, spec in variants.items():
        led = Ledger(tmp_path / f"{name}.db")
        Trader(variant_config(main_cfg, spec["overrides"]), led, None, None, root=tmp_path)    # unknown settings raise here
        led.close()
    assert load_variants(tmp_path / "missing.yaml") == {}
    bad = tmp_path / "bad.yaml"
    bad.write_text("variants:\n  x: {transform: sideways}\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_variants(bad)
