"""Selling before settlement (research/exits.py): held bets must reproduce the backtest exactly, an exit must use
only prices that came after the signal, and on fair prices no exit rule may create money."""
import sqlite3
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "tests"))

import panel  # noqa: E402
import portfolio  # noqa: E402
from backtest import Panel  # noqa: E402
from exits import HOLD, Exits, Policy, bets, policies, rule_rows, stats  # noqa: E402
from families import Features  # noqa: E402
from kalshi_download import SCHEMA, shuffle_key  # noqa: E402
from test_research import make_db  # noqa: E402

DAY = 86400


@pytest.fixture(scope="module")
def fair(tmp_path_factory):
    path = tmp_path_factory.mktemp("exits") / "fair.db"
    make_db(path, n_events=1500, seed=11)          # closes on both sides of the split
    return Panel(panel.load(path))


def one_market(tmp_path, quotes, result="no", name="M"):
    """A single market whose bars are given as (bid, ask) or (bid, ask, bid_hi, ask_lo); opens equal the
    previous close unless the tuple has 6 items (bid, ask, bid_hi, ask_lo, bid_op, ask_op)."""
    path = tmp_path / f"{name}.db"
    db = sqlite3.connect(str(path))
    db.executescript(SCHEMA)
    db.execute("INSERT INTO series VALUES ('S', 'Economics', 'Test', 'quadratic', 1, 'daily', '', 1)")
    n = len(quotes)
    close = panel.SPLIT_TS + 40 * DAY
    tk = f"S-{name}"
    bars = []
    prev = None
    for b, q in enumerate(quotes):
        bid, ask = q[0], q[1]
        bid_hi = q[2] if len(q) > 2 else bid
        ask_lo = q[3] if len(q) > 3 else ask
        bid_op, ask_op = (q[4], q[5]) if len(q) > 5 else (prev or (bid, ask))
        mid = (bid + ask) / 2
        ts = close - (n - b) * DAY
        bars.append((tk, ts, bid, ask, bid_hi, bid, ask, ask_lo, mid, mid, mid, 100.0, 500.0, bid_op, ask_op, mid))
        prev = (bid, ask)
    db.execute("INSERT INTO markets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,0)",
               (tk, "S", f"S-{name}", "Economics", "Will it happen?", "x", close - (n + 1) * DAY, close, result,
                1.0 if result == "yes" else 0.0, 5000.0, 500.0, 0.5, None, None, None, "hist", shuffle_key(tk), close + 3600))
    db.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", bars)
    db.commit()
    db.close()
    return Panel(panel.load(path))


def test_holding_reproduces_the_backtest_for_every_side_and_entry(fair):
    ex = Exits(fair)
    f = Features(fair)
    for side in ("yes", "no"):
        for entry in ("tk", "mk"):
            rows = rule_rows(fair, f.base & f.price(0.1, 0.9), side, entry)
            res = ex.run(rows, side, entry, HOLD)
            assert rows.size > 300
            np.testing.assert_allclose(res.r, fair.r[(side, entry)][rows].astype("float64"), rtol=2e-4, atol=2e-5)
            assert (res.reason == "settle").all()
            ins, oos = stats(fair, res)
            ref_in, ref_out = fair.evaluate(f.base & f.price(0.1, 0.9), side, entry)
            assert (ins.n, oos.n) == (ref_in.n, ref_out.n)
            assert ins.ret == pytest.approx(ref_in.ret, abs=1e-5) and oos.ret == pytest.approx(ref_out.ret, abs=1e-5)


def test_take_profit_sells_at_the_next_open_after_the_signal(tmp_path):
    # NO bought by taker at bar 0 (filled at bar 1's open: YES bid 0.05 -> NO costs 0.95 + fee).
    # Bar 2 closes with YES ask 0.01 (NO bid 0.99): the signal. The sale is at bar 3's OPEN, YES ask 0.02 -> 0.98.
    p = one_market(tmp_path, [(0.04, 0.06), (0.04, 0.06), (0.00 + 0.005, 0.01), (0.01, 0.03, 0.01, 0.03, 0.005, 0.02),
                              (0.01, 0.02), (0.01, 0.02)])
    ex = Exits(p)
    i = 0
    pol = Policy("t", take_px=0.99)
    r, rel, why, got, cost = ex.follow(i, "no", "tk", pol)
    paid = 1 - p.df["n_bid_op"].iloc[0]
    assert cost == pytest.approx(paid + 0.07 * (1 - paid) * paid, rel=1e-5)
    assert why == "take" and got == pytest.approx(0.98)
    net = 0.98 - 0.07 * 0.02 * 0.98
    assert r == pytest.approx((net - cost) / cost, rel=1e-5)
    assert rel == pytest.approx(p.df["ts"].iloc[3]) and rel < p.df["close_ts"].iloc[0]
    held = ex.follow(i, "no", "tk", HOLD)
    assert held[2] == "settle" and held[0] > r                   # the NO paid 1: selling at 0.98 gave some up


def test_the_entry_bar_itself_never_triggers_an_exit(tmp_path):
    # the entry bar already shows a NO bid of 0.99; a rule must not "sell" on the bar it bought on
    p = one_market(tmp_path, [(0.005, 0.01), (0.04, 0.06), (0.04, 0.06), (0.04, 0.06)], result="no", name="E")
    ex = Exits(p)
    r, rel, why, got, cost = ex.follow(0, "no", "tk", Policy("t", take_px=0.99))
    assert why == "settle"


def test_stop_loss_cuts_a_loser_and_time_exit_sells_before_the_end(tmp_path):
    # NO at 0.95; the YES climbs to 0.30 at bar 2 (NO mid 0.70); the market then resolves YES (NO pays 0)
    q = [(0.04, 0.06), (0.04, 0.06), (0.29, 0.31), (0.30, 0.32), (0.60, 0.62), (0.90, 0.92)]
    p = one_market(tmp_path, q, result="yes", name="L")
    ex = Exits(p)
    held = ex.follow(0, "no", "tk", HOLD)
    assert held[0] == pytest.approx(-1.0)
    r, rel, why, got, cost = ex.follow(0, "no", "tk", Policy("s", stop_drop=0.10))
    assert why == "stop" and got == pytest.approx(1 - 0.31) and -0.35 < r < -0.25
    r2, _, why2, _, _ = ex.follow(0, "no", "tk", Policy("d", days=2))
    assert why2 == "time" and r2 > -1.0
    # the stop on an absolute level: NO mid <= 0.85 holds at bar 2 as well
    assert ex.follow(0, "no", "tk", Policy("s2", stop_px=0.85))[2] == "stop"


def test_resting_exit_needs_the_market_to_trade_through(tmp_path):
    # NO held; take at NO bid >= 0.98 resting at NO ask = 1 - YES bid. Bar 2: YES bid 0.01, ask 0.02 -> offer NO at 0.99.
    # It fills only if a later bar's YES ask comes down to 0.01 (ask_lo); first market: never; second: at bar 3.
    never = one_market(tmp_path, [(0.04, 0.06), (0.04, 0.06), (0.01, 0.02), (0.01, 0.02), (0.01, 0.02), (0.01, 0.02)],
                       name="N")
    fills = one_market(tmp_path, [(0.04, 0.06), (0.04, 0.06), (0.01, 0.02), (0.01, 0.02, 0.01, 0.01), (0.01, 0.02),
                                  (0.01, 0.02)], name="F")
    pol = Policy("m", take_px=0.98, style="mk")
    a = Exits(never).follow(0, "no", "tk", pol)
    b = Exits(fills).follow(0, "no", "tk", pol)
    assert b[2] == "take" and b[3] == pytest.approx(0.99)
    assert a[2] != "take" or a[3] != pytest.approx(0.99)        # never traded through at 0.99
    assert b[1] < Exits(fills).follow(0, "no", "tk", HOLD)[1]   # the money came back before the close


def test_on_fair_prices_no_exit_rule_makes_money(fair):
    """Selling a fairly priced contract at its bid cannot beat holding it: every policy only adds costs."""
    ex = Exits(fair)
    f = Features(fair)
    rows = rule_rows(fair, f.base & f.price(0.1, 0.9), "yes", "tk")
    held = ex.run(rows, "yes", "tk", HOLD).r
    for pol in policies():
        if pol.style == "mk" and pol.take_px is None and pol.take_gain is None:
            continue
        r = ex.run(rows, "yes", "tk", pol).r
        diff = r - held
        assert r.mean() < 0.02, pol.name                          # no free money
        # bet by bet against holding the same contract: not better beyond noise (2.5 standard errors)
        assert diff.mean() <= 2.5 * diff.std(ddof=1) / np.sqrt(diff.size), pol.name


def test_released_money_feeds_the_account_replay(fair):
    ex = Exits(fair)
    f = Features(fair)
    rows = rule_rows(fair, f.base & f.price(0.1, 0.9), "no", "tk")
    held = ex.run(rows, "no", "tk", HOLD)
    sold = ex.run(rows, "no", "tk", Policy("d", days=6))
    b_hold, b_sold = bets(fair, held), bets(fair, sold)
    assert len(b_hold) == len(b_sold) == rows.size
    assert (np.diff(b_hold[:, 0]) >= 0).all()                     # in entry order
    assert (b_sold[:, 1] <= b_hold[:, 1] + 1).mean() > 0.99      # never later than the close
    assert (b_sold[:, 1] < b_hold[:, 1] - DAY).mean() > 0.3       # often days earlier
    a = portfolio.simulate(b_hold, stake_frac=0.01)
    b = portfolio.simulate(b_sold, stake_frac=0.01)
    # money given back earlier is staked again: the same rule fits more bets into the account
    assert a.bets > 0 and b.bets > a.bets


def test_the_policy_grid_is_fixed_and_named_once():
    names = [p.name for p in policies()]
    assert len(names) == len(set(names)) and names[0] == HOLD.name and len(names) >= 20


def test_hourly_stop_sells_at_the_next_hourly_open_inside_the_day(tmp_path):
    # NO bought by taker at bar 0 (YES bid ~0.10 -> NO ~0.90). Daily bars never show the stop (YES mid stays 0.11),
    # but an hourly bar inside daily bar 3 has YES at 0.40/0.42 (NO mid 0.59): a 10-point stop holds there and the
    # bet is sold at the NEXT hourly bar's open, YES ask 0.45 -> NO 0.55 less the taker fee.
    p = one_market(tmp_path, [(0.10, 0.12)] * 6, name="H")
    tk = p.df["ticker"].iloc[0]
    ts = p.df["ts"].to_numpy("float64")
    pol = Policy("s", stop_drop=0.10)
    base = Exits(p).follow(0, "no", "tk", pol)
    assert base[2] == "settle"                                      # daily bars alone: no stop
    nan = float("nan")
    h = np.array([[ts[3] - 7200, 0.10, 0.12, 0.10, 0.12],
                  [ts[3] - 3600, 0.40, 0.42, 0.11, 0.13],           # the signal, known at this bar's end
                  [ts[3], 0.44, 0.46, 0.43, 0.45],                  # sold at this bar's open: NO bid 1 - 0.45
                  [ts[3] + 3600, nan, nan, nan, nan]])
    ex = Exits(p, {tk: h})
    r, rel, why, got, cost = ex.follow(0, "no", "tk", pol)
    assert why == "stop" and got == pytest.approx(0.55) and rel == pytest.approx(ts[3])
    assert r == pytest.approx((0.55 - 0.07 * 0.45 * 0.55 - cost) / cost, rel=1e-5)
    assert ex.hourly_stops == 1
    assert ex.follow(0, "no", "tk", HOLD)[2] == "settle"           # holding ignores hourly bars
    # hourly bars before the bet's first exit bar are never used (the entry bar's own day)
    early = np.array([[ts[0] - 1800, 0.40, 0.42, 0.40, 0.42], [ts[0], 0.44, 0.46, 0.43, 0.45]])
    assert Exits(p, {tk: early}).follow(0, "no", "tk", pol)[2] == "settle"
    # no tradable next open within the hour: the daily rule stands
    dead = h.copy()
    dead[2, 3:] = nan
    assert Exits(p, {tk: dead[:3]}).follow(0, "no", "tk", pol)[2] == "settle"
