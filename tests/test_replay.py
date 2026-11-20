"""The what-if replay of a wide account's record (src/replay.py) on a small ledger whose answers are known."""
import pytest

from src.ledger import Ledger
from src.replay import Settings, grid, load, replay

T0 = 1_800_000_000.0
H = 3600.0


def order(led, ts, mid, outcome, edge, usd=20.0, fill=None, fill_ts=None):
    did = led.add_decision({"ts": ts, "run_id": "r", "market_id": mid, "forecast_id": None, "action": f"BUY_{outcome}",
                            "reason": "", "p_model": None, "p_market": None, "q": None, "cost": fill, "edge": edge,
                            "stake": usd, "detail": "{}"})
    oid = led.add_order({"ts": ts, "run_id": "r", "mode": "paper", "market_id": mid, "token_id": f"{mid}:{outcome}",
                         "outcome": outcome, "side": "BUY", "limit_price": fill or 0.5, "usd": usd,
                         "shares": usd / (fill or 0.5), "status": "resting", "venue_order_id": None, "decision_id": did,
                         "note": "passive"})
    if fill is not None:
        led.apply_fill(oid, mid, f"{mid}:{outcome}", outcome, "BUY", fill, usd / fill, ts=fill_ts or ts + H,
                       order_status="filled")
    return oid


@pytest.fixture
def account(tmp_path):
    led = Ledger(tmp_path / "wide.db")
    led.deposit(1000.0)
    for mid, end in (("A", T0 + 10 * 24 * H), ("B", T0 + 10 * 24 * H), ("C", T0 + 10 * 24 * H), ("D", T0 + 5 * 24 * H)):
        led.upsert_market({"market_id": mid, "question": mid, "end_ts": end, "category": "Economics"})
    order(led, T0, "A", "YES", 0.10, fill=0.50)          # wins: YES settles 1
    order(led, T0 + 1 * H, "B", "NO", 0.02, fill=0.40)   # loses: YES settles 1, the NO pays 0
    order(led, T0 + 2 * H, "C", "YES", 0.05)             # rested, never filled
    order(led, T0 + 3 * H, "D", "YES", 0.06, fill=0.30)  # still open, last bid 0.45
    # price paths: D rises; B's YES rises (its NO falls)
    for k, (bid, ask) in enumerate(((0.32, 0.34), (0.41, 0.43), (0.45, 0.47))):
        led.add_snapshot("D", bid, ask, (bid + ask) / 2, ts=T0 + (5 + 10 * k) * H)
    for k, (bid, ask) in enumerate(((0.62, 0.64), (0.80, 0.82))):
        led.add_snapshot("B", bid, ask, (bid + ask) / 2, ts=T0 + (5 + 10 * k) * H)
    led.settle("A", 1.0, ts=T0 + 10 * 24 * H)
    led.settle("B", 1.0, ts=T0 + 10 * 24 * H)
    led.db.commit()
    return tmp_path / "wide.db"


def test_hold_with_an_edge_threshold(account):
    data = load(account, [])
    o = replay(*data, Settings(min_edge=0.03))
    assert (o.accepted, o.filled, o.settled, o.open) == (3, 2, 1, 1)   # B below the threshold, C never filled
    assert o.pnl_settled == pytest.approx(20.0)                           # A: 40 shares at 0.50 paid 1
    assert o.pnl_open == pytest.approx(20.0 / 0.30 * 0.45 - 20.0)          # D at its last bid
    all_ = replay(*data, Settings(min_edge=0.0))
    assert all_.pnl_settled == pytest.approx(20.0 - 20.0) and all_.worst == pytest.approx(-20.0)


def test_daily_budget_counts_orders_that_never_filled(account):
    data = load(account, [])
    o = replay(*data, Settings(max_orders_per_day=3))
    assert o.accepted == 3 and o.filled == 2                               # A, B, C (unfilled) use the budget; D is out
    o = replay(*data, Settings(max_deploy_per_day_pct=0.05))               # $50 a day: two $20 orders
    assert o.accepted == 2


def test_stake_scales_every_result(account):
    data = load(account, [])
    a = replay(*data, Settings(min_edge=0.03))
    b = replay(*data, Settings(min_edge=0.03, stake_pct=0.01))
    assert b.pnl == pytest.approx(a.pnl / 2) and b.staked == pytest.approx(a.staked / 2)


def test_exit_rules_on_the_recorded_prices(account):
    data = load(account, [])
    take = replay(*data, Settings(min_edge=0.03, exit="rule", take_gain=0.10))
    assert take.sold == 1 and take.open == 0                               # D bid 0.41 >= 0.30 + 0.10: sold there
    assert take.pnl_settled == pytest.approx(20.0 + 20.0 / 0.30 * (0.41 - 0.07 * 0.41 * 0.59) - 20.0)
    stop = replay(*data, Settings(min_edge=0.0, exit="rule", stop_drop=0.15))
    # B's NO was bought at 0.40; its mid falls to 1 - 0.63 = 0.37 (not yet), then 0.19: sold at the NO bid 0.18
    line = [x for x in stop.lines if x[0] == "B"][0]
    assert line[3] == "sold" and line[4] == pytest.approx(0.18 - 0.07 * 0.18 * 0.82, abs=1e-3)
    late = replay(*data, Settings(min_edge=0.03, exit="rule", days_before_end=4.5))
    assert [x for x in late.lines if x[0] == "D"][0][3] == "sold"         # D ends 5 days in: its 25 h snapshot is in


def test_recorded_sells(tmp_path, account):
    led = Ledger(account)
    led.apply_fill(None, "D", "D:YES", "YES", "SELL", 0.44, 20.0 / 0.30, fee=0.5, ts=T0 + 20 * H)
    led.db.commit()
    o = replay(*load(account, []), Settings(min_edge=0.03, exit="recorded"))
    d = [x for x in o.lines if x[0] == "D"][0]
    assert d[3] == "sold" and d[4] == pytest.approx(0.44 - 0.5 / (20.0 / 0.30), abs=1e-3)


def test_the_grid_is_named_once():
    names = [s.name for s in grid()]
    assert len(names) == len(set(names)) > 10
