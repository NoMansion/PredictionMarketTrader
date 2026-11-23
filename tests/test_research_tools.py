"""The research command-line tools (research/*.py mains) on small made-up exchanges: the tail test and its exact
bound, one bet per market when legs are combined, exit studies and their summary, event baskets, the sweep and
its tables, the calibration curve and the resting-bid variants; plus the corners of the engine, the account
replay and the shadow log the other test files leave out.

Nothing here reads data/kalshi_hist.db, writes to research/results/ or data/, or touches the network: every
tool gets --db pointing at a file in tmp_path, and the module's HERE (or ROOT) is pointed at tmp_path where a
tool writes its results."""
import json
import math
import sqlite3
import sys
import time
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "research"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_rule  # noqa: E402
import calibration_curve  # noqa: E402
import combined  # noqa: E402
import entry_timing  # noqa: E402
import no_drift  # noqa: E402
import event_baskets  # noqa: E402
import exit_study  # noqa: E402
import exit_summary  # noqa: E402
import panel  # noqa: E402
import portfolio  # noqa: E402
import resting_variants  # noqa: E402
import round_tables  # noqa: E402
import run_sweep  # noqa: E402
import shadow_longshot as sl  # noqa: E402
from backtest import Panel, verdict  # noqa: E402
from exits import HOLD, Exits, Result, policies, rule_rows  # noqa: E402
from fakes import FakeKalshiHTTP  # noqa: E402
from families import Features, all_rules, persistence  # noqa: E402
from kalshi_download import SCHEMA, shuffle_key  # noqa: E402
from src.kalshi import Kalshi  # noqa: E402
from src.kalshi_http import KalshiError  # noqa: E402

DAY = 86400
SPLIT_2026_04_01 = 1775001600           # 2026-04-01 00:00 UTC, written out by hand
FIVE, WIDE = combined.FIVE, combined.WIDE
CATS = (("Economics", "ECO"), ("Entertainment", "ENT"), ("Climate and Weather", "CLI"))


# ---- made-up exchanges -------------------------------------------------------------------------------------

def tools_db(path, n_events=180, seed=5, bias=None, cats=CATS):
    """Events of 3 markets with 12 daily bars, closes spread over about a year either side of the split, the
    categories taking turns. Almost half the markets start at 0.5-4c so the longshot rules have bets. The true
    probability is a martingale; quotes under 30c sit `bias` (per category, default 2c) above it."""
    bias = bias or {}
    rng = np.random.default_rng(seed)
    db = sqlite3.connect(str(path))
    db.executescript(SCHEMA)
    for cat, s in cats:
        db.execute("INSERT INTO series VALUES (?, ?, 'Test', 'quadratic', 1, 'daily', '', 1)", (s, cat))
    t0 = panel.SPLIT_TS - 190 * DAY
    step = int(375 * DAY / n_events)
    for e in range(n_events):
        cat, s = cats[e % len(cats)]
        up = bias.get(cat, 0.02)
        close = t0 + e * step + 14 * DAY
        for j in range(3):
            tk = f"{s}-{e}-{j}"
            p = float(rng.uniform(0.005, 0.04) if rng.random() < 0.45 else rng.uniform(0.05, 0.9))
            bars = []
            for b in range(12):
                p = float(p + rng.uniform(-1, 1) * 0.25 * min(p, 1 - p))
                mid = p + (up if p < 0.30 else 0.0)
                bid, ask = round(mid - 0.01, 2), round(mid + 0.01, 2)
                bid_hi = round(bid + 0.01 * int(rng.integers(0, 3)), 2)        # up to the ask: NO bids can fill
                ask_lo = round(ask - 0.01 * int(rng.integers(0, 3)), 2)        # down to the bid: YES bids can fill
                bars.append((tk, close - (12 - b) * DAY, bid, ask, bid_hi, bid, ask, ask_lo, mid, mid, mid, 100.0, 500.0,
                             bid, ask, mid))
            y = "yes" if rng.random() < p else "no"
            db.execute("INSERT INTO markets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,0)",
                       (tk, s, f"{s}-{e}", cat, f"Will {tk} happen?", "x", close - 13 * DAY, close, y,
                        1.0 if y == "yes" else 0.0, 5000.0, 500.0, 0.5, None, None, None, "hist", shuffle_key(tk),
                        close + 3600))
            db.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", bars)
    db.commit()
    db.close()


def custom_db(path, markets):
    """Markets written out by hand. Each: ticker, event, close, result, bars = [(ts, bid, ask[, bid_hi[, ask_lo]])],
    optional category, strike_type, floor_strike. A bar's open equals its close."""
    db = sqlite3.connect(str(path))
    db.executescript(SCHEMA)
    db.execute("INSERT INTO series VALUES ('H', 'Economics', 'Test', 'quadratic', 1, 'daily', '', 1)")
    for m in markets:
        tk = m["ticker"]
        rows = []
        for q in m["bars"]:
            ts, bid, ask = q[:3]
            bid_hi = q[3] if len(q) > 3 else bid
            ask_lo = q[4] if len(q) > 4 else ask
            mid = (bid + ask) / 2
            rows.append((tk, ts, bid, ask, bid_hi, bid, ask, ask_lo, mid, mid, mid, 100.0, 500.0, bid, ask, mid))
        db.execute("INSERT INTO markets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?,0)",
                   (tk, "H", m["event"], m.get("category", "Economics"), f"Will {tk} happen?", "x", m["bars"][0][0] - DAY,
                    m["close"], m["result"], 1.0 if m["result"] == "yes" else 0.0, 5000.0, 500.0, 0.5,
                    m.get("strike_type"), m.get("floor_strike"), None, "hist", shuffle_key(tk), m["close"] + 3600))
        db.executemany("INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    db.commit()
    db.close()


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    path = tmp_path_factory.mktemp("tools") / "world.db"
    tools_db(path)
    df = panel.load(path)
    p = Panel(df)
    return {"db": path, "df": df, "p": p, "f": Features(p), "titles": run_sweep.titles_for(df, path)}


B_CLOSE = SPLIT_2026_04_01 + 40 * DAY
R_CLOSE = SPLIT_2026_04_01 + 30 * DAY
X_CLOSE = SPLIT_2026_04_01 - 2 * 3600       # closes two hours before the split: in sample


def three_days(close, bid, ask):
    return [(close - 3 * DAY, bid, ask), (close - 2 * DAY, bid, ask), (close - DAY, bid, ask)]


@pytest.fixture(scope="module")
def hand(tmp_path_factory):
    path = tmp_path_factory.mktemp("hand") / "hand.db"
    markets = []
    # B: three exclusive outcomes whose YES bids add up to 1.05; outcome 0 happens
    for j, (bid, res) in enumerate(((0.40, "yes"), (0.35, "no"), (0.30, "no"))):
        markets.append({"ticker": f"B-{j}", "event": "B", "close": B_CLOSE, "result": res,
                        "bars": three_days(B_CLOSE, bid, bid + 0.02)})
    # L: a ladder of "above X?" rungs, bids adding up to 1.2: not a basket, whatever the sum
    for j, bid in enumerate((0.50, 0.40, 0.30)):
        markets.append({"ticker": f"L-{j}", "event": "L", "close": B_CLOSE, "result": "no", "strike_type": "greater",
                        "floor_strike": float(j + 1), "bars": three_days(B_CLOSE, bid, bid + 0.02)})
    # T: two outcomes bid 0.30 each (0.60 in all)
    for j in range(2):
        markets.append({"ticker": f"T-{j}", "event": "T", "close": B_CLOSE, "result": "no",
                        "bars": three_days(B_CLOSE, 0.30, 0.32)})
    # R: one longshot for the resting-bid variants. YES 2/4c throughout; the YES bid touches 4c on bar 1 and 5c on bar 2
    markets.append({"ticker": "R", "event": "R", "close": R_CLOSE, "result": "no",
                    "bars": [(R_CLOSE - (5 - b) * DAY, 0.02, 0.04, hi) for b, hi in enumerate((0.02, 0.04, 0.05, 0.02, 0.02))]})
    # X: closes just before the split. Bar 0 is one-sided; bar 1, twelve hours before the close, is the first entry
    markets.append({"ticker": "X", "event": "X", "close": X_CLOSE, "result": "no",
                    "bars": [(X_CLOSE - 2 * DAY, 0.0, 0.06), (X_CLOSE - 12 * 3600, 0.04, 0.06), (X_CLOSE - 3600, 0.04, 0.06)]})
    # U: quoted, then a bar with no bid, then quoted again
    markets.append({"ticker": "U", "event": "U", "close": B_CLOSE, "result": "yes",
                    "bars": [(B_CLOSE - (4 - b) * DAY, bid, 0.52) for b, bid in enumerate((0.50, 0.0, 0.50, 0.50))]})
    custom_db(path, markets)
    df = panel.load(path)
    p = Panel(df)
    return {"db": path, "df": df, "p": p, "f": Features(p)}


# ---- guards: the split never moves, the real results folder is never written ----------------------------------

@pytest.fixture(autouse=True)
def split_stays_put():
    before = panel.SPLIT_TS
    yield
    assert panel.SPLIT_TS == before == SPLIT_2026_04_01, "a tool moved the in/out-of-sample boundary"


@pytest.fixture(scope="module", autouse=True)
def real_results_untouched():
    folder = ROOT / "research" / "results"
    snap = lambda: {p.name: p.stat().st_mtime_ns for p in folder.glob("*")} if folder.exists() else {}   # noqa: E731
    before = snap()
    yield
    assert snap() == before, "research/results was written to"


def same(a, b) -> bool:
    """Two backtest Samples are equal, NaN fields included."""
    x, y = a.cells("s"), b.cells("s")
    return x.keys() == y.keys() and all(x[k] == y[k] or (math.isnan(x[k]) and math.isnan(y[k])) for k in x)


def empty_account(a) -> bool:
    return a.bets == 0 and a.skipped == 0 and a.total == 0.0 and a.years == 0.0 and math.isnan(a.sharpe)


def run_main(monkeypatch, mod, *args) -> int:
    monkeypatch.setattr(sys, "argv", [mod.__file__, *[str(a) for a in args]])
    return mod.main()


@pytest.fixture
def results_here(monkeypatch, tmp_path):
    """Point every tool's HERE at tmp_path, so HERE / 'results' is tmp_path / 'results'."""
    for mod in (combined, exit_study, exit_summary, run_sweep, round_tables):
        monkeypatch.setattr(mod, "HERE", tmp_path)
    (tmp_path / "results").mkdir()
    return tmp_path / "results"


@pytest.fixture
def frames(monkeypatch):
    """Every DataFrame a tool prints, as it was when printed."""
    seen = []
    orig = pd.DataFrame.to_string

    def spy(self, *a, **k):
        seen.append(self.copy())
        return orig(self, *a, **k)

    monkeypatch.setattr(pd.DataFrame, "to_string", spy)
    return seen


# ---- analyze_rule: the exact bound, the tail test, the rule lookup, the report ---------------------------------

def test_the_split_is_2026_04_01_and_decides_both_halves(world):
    assert panel.SPLIT_TS == SPLIT_2026_04_01 == int(pd.Timestamp("2026-04-01", tz="UTC").timestamp())
    df = world["df"]
    assert (df["oos"] == (df["close_ts"] >= SPLIT_2026_04_01)).all() and df["oos"].any() and (~df["oos"]).any()
    p, f = world["p"], world["f"]
    _, mask = analyze_rule.find_rule(f, world["titles"], FIVE, "no", "tk")
    b = analyze_rule.bets_frame(p, mask, "no", "tk")
    assert (b["oos"] == (b["close_ts"] >= SPLIT_2026_04_01)).all() and b["oos"].any() and (~b["oos"]).any()


def test_binomial_cdf_matches_the_direct_sum():
    for k, n, q in ((0, 10, 0.1), (3, 20, 0.25), (7, 7, 0.6), (5, 100, 0.03), (40, 50, 0.9)):
        direct = sum(math.comb(n, i) * q ** i * (1 - q) ** (n - i) for i in range(k + 1))
        assert analyze_rule.binom_cdf(k, n, q) == pytest.approx(direct, rel=1e-9)
    assert analyze_rule.binom_cdf(0, 10, 0.0) == 1.0
    assert analyze_rule.binom_cdf(10, 10, 1.0) == 1.0 and analyze_rule.binom_cdf(9, 10, 1.0) == 0.0


def test_clopper_pearson_upper_bound_against_known_values():
    u = analyze_rule.loss_rate_upper
    # no loss in n: the bound solves (1 - p)^n = 0.05
    assert u(0, 100) == pytest.approx(1 - 0.05 ** (1 / 100), abs=1e-9) == pytest.approx(0.029513, abs=1e-6)
    assert u(0, 10) == pytest.approx(0.258866, abs=1e-6)
    assert u(0, 50, conf=0.99) == pytest.approx(1 - 0.01 ** (1 / 50), abs=1e-9)
    # textbook one-sided 95% values (the upper ends of the two-sided 90% Clopper-Pearson intervals)
    assert u(1, 10) == pytest.approx(0.3942, abs=1e-4)
    assert u(5, 100) == pytest.approx(0.1023, abs=1e-4)
    # at the bound, seeing k or fewer is exactly 5% likely
    for k, n in ((1, 10), (2, 200), (5, 100)):
        hi = u(k, n)
        assert sum(math.comb(n, i) * hi ** i * (1 - hi) ** (n - i) for i in range(k + 1)) == pytest.approx(0.05, abs=1e-9)
    assert u(0, 0) == 1.0 and u(10, 10) == 1.0
    assert u(0, 200) < u(1, 200) < u(2, 200) < u(5, 200)
    assert u(5, 100) > 5 / 100


def test_the_tail_test_passes_a_clean_record_and_fails_a_short_one():
    # 1,000 events that each made 2c and none lost: break-even 0.02 / 1.02 = 1.96%, bound 0.30%
    ok = analyze_rule.tail(np.full(1000, 0.02))
    assert ok["events"] == 1000 and ok["losing"] == 0 and math.isnan(ok["loss_per_loser"])
    assert ok["gain_per_winner"] == pytest.approx(0.02) and ok["breakeven"] == pytest.approx(0.02 / 1.02)
    assert ok["upper95"] == pytest.approx(1 - 0.05 ** (1 / 1000), abs=1e-9) and ok["proven"]
    # 200 events, 2 lost 97c: the loss rate seen (1%) is below break-even (2.02%), but its bound (3.1%) is not
    r = np.r_[np.full(198, 0.02), [-0.97, -0.97]]
    bad = analyze_rule.tail(r)
    assert bad["losing"] == 2 and bad["loss_per_loser"] == pytest.approx(0.97)
    assert bad["breakeven"] == pytest.approx(0.02 / 0.99) and bad["upper95"] == pytest.approx(0.031143, abs=1e-5)
    assert 2 / 200 < bad["breakeven"] < bad["upper95"] and not bad["proven"]
    # the same record ten times longer is proven
    assert analyze_rule.tail(np.tile(r, 10))["proven"]
    # nothing but losers: break-even 0, never proven
    lost = analyze_rule.tail(np.full(50, -1.0))
    assert lost["breakeven"] == 0.0 and not lost["proven"]


def test_below_cumvol_keeps_only_bars_under_the_level_known_at_the_bar(world):
    p, f = world["p"], world["f"]
    _, mask = analyze_rule.find_rule(f, world["titles"], WIDE, "no", "mk")
    assert analyze_rule.below_cumvol(p, mask, None) is mask
    cv = p.df["cumvol"].to_numpy()
    level = float(np.median(cv[mask])) if mask.any() else 1.0
    cut = analyze_rule.below_cumvol(p, mask, level)
    assert np.array_equal(cut, mask & (cv < level))
    assert not (cut & ~mask).any() and (cv[cut] < level).all()
    assert not analyze_rule.below_cumvol(p, mask, 0.0).any()


def test_find_rule_finds_the_named_condition_and_refuses_unknown_ones(world):
    f, titles = world["f"], world["titles"]
    fam, mask = analyze_rule.find_rule(f, titles, FIVE, "no", "mk")
    assert fam == "2 bonds"
    assert np.array_equal(mask, f.base & (f.dte <= 30) & (f.spread <= 0.05) & (f.mid <= 1 - 0.95) & (f.mid > 0))
    fam, mask = analyze_rule.find_rule(f, titles, WIDE, "no", "tk")
    assert fam == "26 dear side" and np.array_equal(mask, f.base & f.price(0.05, 0.35))
    with pytest.raises(SystemExit, match="no rule named 'no such rule'"):
        analyze_rule.find_rule(f, titles, "no such rule", "no", "tk")
    with pytest.raises(SystemExit, match="side yes"):
        analyze_rule.find_rule(f, titles, FIVE, "yes", "tk")          # the name exists, but only for NO


def test_the_5_cent_rule_without_its_0_3c_corner_is_the_5_cent_rule_above_3c(world):
    f, titles = world["f"], world["titles"]
    for entry in ("mk", "tk"):
        _, five = analyze_rule.find_rule(f, titles, FIVE, "no", entry)
        fam, mask = analyze_rule.find_rule(f, titles, "NO at mid 3-5c, <= 30d, spread <= 5c", "no", entry)
        assert fam == "2 bonds" and np.array_equal(mask, five & (f.mid > 0.03))
        assert not (mask & (f.mid <= 0.03)).any()

def test_no_fall_rule_is_the_exact_complement_of_the_fall_rule_within_the_price(world):
    f, titles = world["f"], world["titles"]
    for k in (1, 3, 7):
        _, down = analyze_rule.find_rule(f, titles, f"mid 10-25c, down 3c+ in {k}d", "no", "mk")
        fam, nofall = analyze_rule.find_rule(f, titles, f"mid 10-25c, no 3c+ fall in {k}d", "no", "mk")
        whole = f.base & f.price(0.10, 0.25)
        assert fam == "14 price x momentum"
        assert not (down & nofall).any() and np.array_equal(down | nofall, whole)


def test_bets_frame_is_one_bet_per_market(world):
    p, f = world["p"], world["f"]
    _, mask = analyze_rule.find_rule(f, world["titles"], FIVE, "no", "tk")
    b = analyze_rule.bets_frame(p, mask, "no", "tk")
    assert len(b) > 60 and b["ticker"].is_unique
    rows = p.first_per_market(mask & p.ok[("no", "tk")])
    np.testing.assert_allclose(b["r"].to_numpy(), p.r[("no", "tk")][rows], rtol=1e-6)
    assert set(b.columns) == {"ticker", "event", "series", "category", "ts", "close_ts", "year", "oos", "r", "cost", "hold",
                              "day_contracts", "dvol7"}
    assert (b["hold"] >= 0.5).all() and (b["cost"] > 0.9).all() and (b["day_contracts"] == 100).all()


def test_report_shows_the_tail_and_the_account_replay(world):
    p, f = world["p"], world["f"]
    _, mask = analyze_rule.find_rule(f, world["titles"], FIVE, "no", "tk")
    b = analyze_rule.bets_frame(p, mask, "no", "tk")
    text = analyze_rule.report(b, p, mask, "no", "tk")
    assert text.startswith(f"{len(b):,} bets in {b['event'].nunique():,} events")
    for part in ("by year of close", "the tail", "concentration by series", "capacity:", "holding time", "account replay"):
        assert part in text
    x = analyze_rule.tail(b[b["oos"]].groupby("event")["r"].sum().to_numpy())
    tail_line = next(s for s in text.splitlines() if s.strip().startswith("out of sample"))
    assert f"{x['events']:5d} events, {x['losing']:3d} losing" in tail_line
    assert ("-> below break-even" if x["proven"] else "NOT below break-even") in tail_line
    a, o = portfolio.run(p, [(mask, "no", "tk")], stake_frac=0.01)
    stake_line = next(s for s in text.splitlines() if "stake 1.0%" in s)
    assert f"{a.bets:4d} bets" in stake_line.split("|")[0] and f"{o.bets:4d} bets" in stake_line.split("|")[1]


def test_analyze_rule_main_end_to_end(world, monkeypatch, capsys):
    assert run_main(monkeypatch, analyze_rule, "--db", world["db"], "--rule", FIVE, "--side", "no", "--entry", "tk") == 0
    out = capsys.readouterr().out
    assert f"[2 bonds] {FIVE} | buy NO | taker" in out and "account replay" in out and "stake 2.0%" in out
    assert run_main(monkeypatch, analyze_rule, "--db", world["db"], "--rule", FIVE, "--side", "no", "--entry", "mk",
                    "--sample", "liquid", "--categories", "Economics") == 0
    assert "resting order" in capsys.readouterr().out
    assert run_main(monkeypatch, analyze_rule, "--db", world["db"], "--rule", FIVE, "--side", "no", "--entry", "tk",
                    "--categories", "Nothing") == 1
    assert "no observations yet" in capsys.readouterr().out


def test_report_on_a_rule_without_bets(world):
    p, f = world["p"], world["f"]
    none = np.zeros(p.n, bool)
    text = analyze_rule.report(analyze_rule.bets_frame(p, none, "no", "tk"), p, none, "no", "tk")
    assert text.startswith("0 bets")


# ---- combined: one bet per market across legs ----------------------------------------------------------------

def res(rows, r):
    rows = np.asarray(rows, "int64")
    r = np.asarray(r, "float64")
    return Result(rows, r, r * 0 + 1.0, np.array(["settle"] * rows.size, dtype=object), r * np.nan, r * 0 + 0.9)


def test_merge_and_first_per_market_keep_the_earliest_entry(world):
    p = world["p"]
    t = p.ticker
    first = np.flatnonzero(np.r_[True, t[1:] != t[:-1]])           # first row of every market
    m1, m2 = first[0], first[1]
    late_leg = res([m1 + 5, m2 + 2], [1.0, 2.0])                    # sees market 1 on its 6th bar, market 2 on its 3rd
    early_leg = res([m1 + 1], [3.0])                                # sees market 1 on its 2nd bar
    merged = combined.merge([late_leg, early_leg])
    assert merged.rows.tolist() == [m1 + 5, m2 + 2, m1 + 1] and merged.r.tolist() == [1.0, 2.0, 3.0]
    one = combined.first_per_market(p, merged)
    assert one.rows.tolist() == [m1 + 1, m2 + 2] and one.r.tolist() == [3.0, 2.0]   # the earlier leg wins market 1
    # two legs on the same bar: the leg listed first wins
    tie = combined.first_per_market(p, combined.merge([res([m1 + 1], [7.0]), res([m1 + 1], [8.0])]))
    assert tie.rows.tolist() == [m1 + 1] and tie.r.tolist() == [7.0]
    empty = combined.first_per_market(p, combined.merge([]))
    assert empty.rows.size == 0 and empty.r.size == 0


def test_account_splits_the_bets_at_the_close(world):
    p, f = world["p"], world["f"]
    _, mask = analyze_rule.find_rule(f, world["titles"], FIVE, "no", "mk")
    r = Exits(p).run(rule_rows(p, mask, "no", "mk"), "no", "mk", HOLD)
    a, o = combined.account(p, r, 0.01)
    oos = p.oos[r.rows]
    assert a.bets + a.skipped == (~oos).sum() > 0 and o.bets + o.skipped == oos.sum() > 0


def test_combined_five_cumvol_limits_only_the_five_cent_leg(world, results_here, monkeypatch):
    df = panel.load(world["db"], ["Economics"], sample="liquid")
    lvl = combined.leg_level(df, 1e12)
    assert lvl.dtype == bool and not lvl.any() and combined.leg_level(df, 0).all()
    assert run_main(monkeypatch, combined, "--db", world["db"], "--stakes", "0.01") == 0
    base = pd.read_csv(results_here / "combined_hold.csv").set_index("account")
    assert run_main(monkeypatch, combined, "--db", world["db"], "--stakes", "0.01", "--five-cumvol", "1e12") == 0
    t = pd.read_csv(results_here / "combined_hold_five1000000000000.csv").set_index("account")
    five = [a for a in t.index if a.startswith("5-cent rule, nine")]
    assert len(five) == 1 and t.loc[five[0], ["bets in", "bets out"]].sum() == 0
    other = "the other three legs (no 5-cent nine)"
    assert run_main(monkeypatch, combined, "--db", world["db"], "--stakes", "0.01", "--min-cumvol", "1") == 0
    assert (results_here / "combined_hold_min1.csv").exists()
    assert t.loc[other, "bets in"] == base.loc[other, "bets in"] > 0
    assert t.loc["ALL FOUR LEGS in one account", "bets in"] == base.loc[other, "bets in"]


def test_combined_main_writes_one_row_per_account_and_stake(world, results_here, monkeypatch, capsys):
    assert run_main(monkeypatch, combined, "--db", world["db"], "--stakes", "0.01,0.02") == 0
    t = pd.read_csv(results_here / "combined_hold.csv")
    assert list(t.columns) == ["stake", "account", "bets in", "bets out", "in/bet", "out/bet", "in/yr", "in dd", "in sharpe",
                               "in at work", "out/yr", "out dd", "out sharpe", "out at work", "out years"]
    assert len(t) == 2 * 8 and sorted(t["stake"].unique()) == [0.01, 0.02]
    assert "exit policy: hold to settlement" in capsys.readouterr().out
    # every market once, however many legs saw it
    df = panel.load(world["db"], sorted({c for leg in combined.LEGS for c in leg[4]}), sample="liquid")
    p = Panel(df)
    f = Features(p)
    titles = run_sweep.titles_for(df, world["db"])
    tickers, per_leg = set(), []
    for _, name, side, entry, cats in combined.LEGS:
        _, mask = analyze_rule.find_rule(f, titles, name, side, entry)
        rows = rule_rows(p, mask & np.isin(df["category"].to_numpy(object), cats), side, entry)
        per_leg.append(rows.size)
        tickers |= set(df["ticker"].to_numpy()[rows])
    one = t[t["stake"] == 0.01].set_index("account")
    bets = one["bets in"] + one["bets out"]
    assert bets.iloc[:4].tolist() == per_leg and min(per_leg) > 0
    assert bets["ALL FOUR LEGS in one account"] == len(tickers) < sum(per_leg)     # the legs overlap; each market once
    assert bets["the first three legs"] <= bets["ALL FOUR LEGS in one account"]
    # an exit policy gets its own file
    assert run_main(monkeypatch, combined, "--db", world["db"], "--stakes", "0.01", "--exit", "take at bid >= 0.98, resting") == 0
    t2 = pd.read_csv(results_here / "combined_take_at_bid____0_98__resting.csv")
    assert len(t2) == 8 and (t2["bets in"] + t2["bets out"]).tolist() == bets.tolist()   # an exit changes returns, not entries


# ---- exit_study and exit_summary -----------------------------------------------------------------------------

def test_exit_study_half_and_study(world):
    p, f = world["p"], world["f"]
    _, mask = analyze_rule.find_rule(f, world["titles"], FIVE, "no", "tk")
    ex = Exits(p)
    r = ex.run(rule_rows(p, mask, "no", "tk"), "no", "tk", HOLD)
    assert exit_study.half(p, r, np.zeros(r.rows.size, bool), "is", 0.01) == {"is_bets": 0}
    h = exit_study.half(p, r, ~p.oos[r.rows], "is", 0.01)
    assert h["is_bets"] == (~p.oos[r.rows]).sum() and h["is_sold"] == 0.0 and h["is_take"] == 0.0
    t = exit_study.study(p, ex, mask, "no", "tk", 0.01)
    assert t["policy"].tolist() == [x.name for x in policies()]
    hold = t.iloc[0]
    ins, oos = p.evaluate(mask, "no", "tk")
    assert hold["is_bets"] == ins.n and hold["oos_bets"] == oos.n
    assert hold["is_ret"] == pytest.approx(ins.ret, abs=1e-6) and hold["oos_ret"] == pytest.approx(oos.ret, abs=1e-6)
    assert (t["is_bets"] == ins.n).all()                           # every policy follows the same entries
    assert (t.iloc[1:]["oos_sold"] > 0).any()
    assert "out tail" in exit_study.show(t)


def test_exit_study_main_then_exit_summary_on_its_output(world, results_here, monkeypatch, capsys, frames):
    rules = f"{FIVE}|no|tk;{WIDE}|no|mk"
    assert run_main(monkeypatch, exit_study, "--tag", "t", "--db", world["db"], "--categories", "Economics,Entertainment",
                    "--rules", rules) == 0
    assert "chosen in sample" in capsys.readouterr().out
    t = pd.read_csv(results_here / "exit_t.csv")
    n = len(policies())
    assert len(t) == 2 * n and t["rule"].tolist() == [f"{FIVE} | no | tk"] * n + [f"{WIDE} | no | mk"] * n
    assert t["policy"].iloc[0] == HOLD.name and t["policy"].iloc[n] == HOLD.name
    for col in ("is_bets", "is_ret", "is_tail_ok", "is_cagr", "oos_bets", "oos_ret", "oos_upper95", "oos_maxdd"):
        assert col in t
    frames.clear()
    assert run_main(monkeypatch, exit_summary) == 0
    s = frames[-1]
    assert s["sample"].tolist() == ["t", "t"] and s["rule"].tolist() == ["5-cent rule | no | tk", "NO vs YES 5-35c | no | mk"]
    assert s["out bets"].tolist() == [int(t["oos_bets"].iloc[0]), int(t["oos_bets"].iloc[n])]
    assert s["take: beat hold out/bet"].str.endswith("/12").all() and s["time: beat hold out/bet"].str.endswith("/3").all()
    assert run_main(monkeypatch, exit_study, "--tag", "none", "--db", world["db"], "--categories", "Nothing") == 1
    assert not (results_here / "exit_none.csv").exists()


def test_exit_study_main_on_a_rule_that_never_fires(world, results_here, monkeypatch):
    # every market here lives 12 days: a rule for contracts 90+ days from the end never fires
    assert run_main(monkeypatch, exit_study, "--tag", "empty", "--db", world["db"], "--categories", "Economics",
                    "--rules", "mid 0-5c, 90+d to close|no|tk") == 0
    assert (results_here / "exit_empty.csv").exists()
    assert exit_summary.main() == 0                   # and the summary reads a results file with no replay columns


def test_combined_refuses_an_unknown_exit_policy(world, results_here, monkeypatch):
    with pytest.raises(SystemExit, match="unknown exit policy"):
        run_main(monkeypatch, combined, "--db", world["db"], "--exit", "take at whenever")
    assert not (results_here / "combined_hold.csv").exists()


def test_exit_family_mapping_covers_the_whole_grid():
    fam = [exit_summary.family(p.name) for p in policies()]
    assert {k: fam.count(k) for k in set(fam)} == {"hold": 1, "take": 12, "stop": 6, "time": 3, "take+stop": 3}
    assert exit_summary.family("take 0.99 resting + stop -10 points") == "take+stop"
    assert exit_summary.family("take at +5 points, taker") == "take"
    assert exit_summary.family("stop at our mid <= 0.85") == "stop"
    assert exit_summary.family("sell 3d before the scheduled end") == "time"


def test_exit_summary_counts_the_exits_that_beat_holding(results_here, monkeypatch, frames):
    R = "NO at mid <= 5c, <= 30d, spread <= 5c | no | mk"
    rows = [  # policy, in-sample replay a year, out-of-sample return per bet
        ("hold to settlement", 0.10, 0.010),
        ("take at bid >= 0.98, taker", 0.30, 0.020),
        ("take at +3 points, taker", 0.20, 0.005),
        ("stop at -5 points", 0.05, 0.000),
        ("stop at our mid <= 0.85", 0.04, 0.015),
        ("sell 1d before the scheduled end", 0.01, 0.030),
        ("take 0.99 resting + stop -10 points", 0.02, 0.010),       # equal to holding: does not beat it
    ]
    t = pd.DataFrame([{"rule": R, "policy": pol, "is_ret": 0.01, "is_cagr": c, "oos_bets": 40, "oos_ret": o, "oos_cagr": o * 5,
                       "oos_maxdd": 0.1, "oos_tail_ok": True} for pol, c, o in rows])
    blind = t.assign(rule="other | yes | tk", is_cagr=np.nan)       # no in-sample replay at all: nothing is chosen
    pd.concat([t, blind]).to_csv(results_here / "exit_a.csv", index=False)
    t.assign(oos_ret=-t["oos_ret"]).to_csv(results_here / "exit_b.csv", index=False)
    (results_here / "other.csv").write_text("not an exit study")
    assert run_main(monkeypatch, exit_summary) == 0
    s = frames[-1].set_index(["sample", "rule"])
    a = s.loc[("a", "5-cent rule | no | mk")]
    assert a["chosen in sample"] == "take at bid >= 0.98, taker" and a["its out/bet"] == pytest.approx(0.02)
    assert a["hold out/bet"] == pytest.approx(0.01) and a["out bets"] == 40
    assert (a["take: beat hold out/bet"], a["stop: beat hold out/bet"], a["time: beat hold out/bet"],
            a["take+stop: beat hold out/bet"]) == ("1/2", "1/2", "1/1", "0/1")
    assert pd.isna(s.loc[("a", "other | yes | tk")]["chosen in sample"])
    b = s.loc[("b", "5-cent rule | no | mk")]                          # signs flipped: holding (-1%) now beats more of them
    assert (b["take: beat hold out/bet"], b["stop: beat hold out/bet"], b["time: beat hold out/bet"]) == ("1/2", "1/2", "0/1")
    assert len(s) == 3


# ---- event baskets ----------------------------------------------------------------------------------------------

def test_a_basket_costs_the_next_open_plus_fees_and_pays_what_settled(hand):
    b = event_baskets.baskets(hand["df"], 0.90).set_index("event")
    assert list(b.index) == ["B"]                                     # L is a ladder, T adds up to 0.60, R and X are alone
    x = b.loc["B"]
    bids = np.array([0.40, 0.35, 0.30])
    cost = (1 - bids).sum() + 0.07 * (bids * (1 - bids)).sum()
    assert x["legs"] == 3 and x["sig_sum"] == pytest.approx(1.05, abs=1e-6) and x["cost"] == pytest.approx(cost, rel=1e-5)
    assert x["pay"] == 2.0 and x["ret"] == pytest.approx((2 - cost) / cost, rel=1e-4)
    assert x["locked"] == pytest.approx((3 - 1 - cost) / cost, rel=1e-4) and x["oos"]
    assert x["ts"] == B_CLOSE - 3 * DAY and x["hold"] == pytest.approx(3.0)      # the first qualifying day only
    assert set(event_baskets.baskets(hand["df"], 0.50)["event"]) == {"B", "T"}
    assert event_baskets.baskets(hand["df"], 1.10).empty
    assert event_baskets.baskets(hand["df"], 0.50, min_legs=4).empty
    assert event_baskets.baskets(hand["df"].iloc[0:0], 0.5).empty
    assert event_baskets.line(pd.DataFrame()) == "none"
    assert event_baskets.line(event_baskets.baskets(hand["df"], 0.5)).strip().startswith("2 baskets, ")


class FakeEventsHTTP:
    """Stands in for src.kalshi_http.KalshiHTTP inside event_baskets.fetch_flags."""
    answers = {"E1": {"mutually_exclusive": True, "title": "one"}, "E2": {"mutually_exclusive": False, "title": "two"},
               "E3": 404, "E4": {"title": "no flag"}, "E5": 429, "E6": {"mutually_exclusive": True}}
    asked: list = []

    def __init__(self, min_interval=0.0):
        pass

    def get(self, path, tries=3):
        e = path.rsplit("/", 1)[-1]
        FakeEventsHTTP.asked.append(e)
        a = self.answers[e]
        if isinstance(a, int):
            raise KalshiError(a, path, "refused")
        return {"event": a}


def test_flags_are_fetched_once_kept_beside_the_history_and_a_429_stops(tmp_path, monkeypatch):
    import src.kalshi_http
    monkeypatch.setattr(src.kalshi_http, "KalshiHTTP", FakeEventsHTTP)
    FakeEventsHTTP.asked = []
    db = tmp_path / "hist.db"
    assert event_baskets.flags_db(db) == str(tmp_path / "kalshi_events.db")
    assert event_baskets.flags(db) == {}
    assert event_baskets.fetch_flags(db, ["E1", "E2", "E3", "E4", "E5", "E6"]) == 3     # E3 refused, stopped at E5
    assert FakeEventsHTTP.asked == ["E1", "E2", "E3", "E4", "E5"]
    assert event_baskets.flags(db) == {"E1": True, "E2": False}                         # E4 came back without a flag
    FakeEventsHTTP.asked = []
    event_baskets.fetch_flags(db, ["E1", "E2", "E6"])
    assert FakeEventsHTTP.asked == ["E6"]                                             # known flags are not asked again


def test_event_baskets_main_splits_by_the_exclusive_flag(hand, monkeypatch, capsys, tmp_path):
    import shutil
    import src.kalshi_http
    db = tmp_path / "hand.db"
    shutil.copy(hand["db"], db)
    assert run_main(monkeypatch, event_baskets, "--db", db) == 0
    out = capsys.readouterr().out
    assert "bids add up to 1.10+: none" in out and "bids add up to 1.20+: none" in out
    line = next(s for s in out.splitlines() if s.startswith("bids add up to 1.02+, all"))
    assert "in sample none" in line
    below = out.splitlines()[out.splitlines().index(line) + 1]
    assert "out of sample    1 baskets, 3 legs" in below
    # with the flags fetched (from a fake exchange), B is counted as exclusive
    monkeypatch.setattr(src.kalshi_http, "KalshiHTTP", FakeEventsHTTP)
    monkeypatch.setattr(FakeEventsHTTP, "answers", {"B": {"mutually_exclusive": True}})
    assert run_main(monkeypatch, event_baskets, "--db", db, "--fetch-flags") == 0
    out = capsys.readouterr().out.splitlines()
    assert "flags fetched for 1 of 1 candidate events" in out                          # T's bids add up to 0.60 only
    ex = out.index(next(s for s in out if s.startswith("bids add up to 1.02+, exclusive")))
    assert "1 baskets" in out[ex + 1]
    nx = out.index(next(s for s in out if s.startswith("bids add up to 1.02+, not exclusive")))
    assert out[nx + 1].strip().endswith("out of sample none")
    assert run_main(monkeypatch, event_baskets, "--db", db, "--categories", "Nothing") == 1


# ---- run_sweep and round_tables --------------------------------------------------------------------------------

def test_titles_follow_the_rows(world):
    t = world["titles"]
    assert len(t) == len(world["df"]) and (t == ("Will " + world["df"]["ticker"] + " happen?").to_numpy()).all()


def test_run_sweep_main_writes_every_rule_and_round_tables_reads_it(world, results_here, monkeypatch, capsys):
    assert run_main(monkeypatch, run_sweep, "--round", "t", "--db", world["db"], "--min-events", "20") == 0
    assert "verdicts:" in capsys.readouterr().out
    out = pd.read_csv(results_here / "t.csv")
    n_rules = sum(1 for _ in all_rules(world["f"], world["titles"]))
    pers = list(persistence(world["f"]))
    assert len(out) == n_rules + len(pers) and n_rules > 1000
    for col in ("family", "rule", "side", "entry", "is_n", "is_events", "is_ret", "is_t", "oos_n", "oos_ret", "oos_t",
                "oos_evt", "verdict", "fill"):
        assert col in out
    assert set(out["verdict"]) <= {"pass", "lead", "loses", "no", "thin"} and (out["verdict"] != "thin").any()
    assert (out.loc[out["entry"] == "tk", "fill"] == 1.0).all()
    mk = out.loc[(out["entry"] == "mk") & (out["family"] == "1 calibration"), "fill"].dropna()
    assert len(mk) > 10 and mk.between(0, 1).all() and mk.mean() > 0.3
    ins, oos = world["p"].evaluate(world["f"].base & world["f"].price(0.0, 0.05), "no", "tk")
    r = out[(out["rule"] == "mid 0-5c") & (out["side"] == "no") & (out["entry"] == "tk")].iloc[0]
    assert r["is_n"] == ins.n and r["oos_n"] == oos.n and r["oos_ret"] == pytest.approx(oos.ret, abs=1e-5)
    # round_tables on that file
    assert run_main(monkeypatch, round_tables, "t", "--min-events", "20") == 0
    text = capsys.readouterr().out
    assert text.startswith(f"{len(out)} rules: ") and "| YES price |" in text and "**pass:" in text and "**loses:" in text
    assert run_main(monkeypatch, round_tables, "t", "--family", "2 bonds", "--min-events", "5") == 0
    fam = capsys.readouterr().out.strip().splitlines()
    assert fam[0].startswith("| Rule | Side |") and len(fam) > 3


def test_run_sweep_split_option_moves_the_boundary_for_that_run_only(tmp_path, results_here, monkeypatch):
    db = tmp_path / "small.db"
    tools_db(db, n_events=24, seed=2)
    monkeypatch.setattr(panel, "SPLIT_TS", panel.SPLIT_TS)          # restored when the test ends
    assert run_main(monkeypatch, run_sweep, "--round", "a", "--db", db) == 0
    assert panel.SPLIT_TS == SPLIT_2026_04_01
    assert run_main(monkeypatch, run_sweep, "--round", "b", "--db", db, "--split", "2025-12-01") == 0
    assert panel.SPLIT_TS == int(pd.Timestamp("2025-12-01", tz="UTC").timestamp())
    a, b = (pd.read_csv(results_here / f"{x}.csv").set_index(["family", "rule", "side", "entry"]) for x in "ab")
    k = ("3 always no", "events of 2-4 markets", "no", "tk")
    assert a.loc[k, "is_n"] + a.loc[k, "oos_n"] == b.loc[k, "is_n"] + b.loc[k, "oos_n"]
    assert b.loc[k, "is_n"] < a.loc[k, "is_n"]
    assert run_main(monkeypatch, run_sweep, "--round", "c", "--db", db, "--categories", "Nothing") == 1


def test_round_table_formatting():
    assert round_tables.pct(0.0123) == "+1.2%" and round_tables.pct(-0.05) == "−5.0%" and round_tables.pct(np.nan) == ""
    assert round_tables.tt(-3.14) == "−3.1" and round_tables.tt(2.0) == "2.0" and round_tables.tt(np.nan) == ""
    d = pd.DataFrame([
        {"family": "1 calibration", "rule": "mid 0-5c", "side": "no", "entry": "tk", "is_ret": 0.02, "is_t": 2.5,
         "oos_ret": 0.03, "oos_t": 3.5, "oos_evt": 2.2, "oos_win": 0.97, "is_events": 120, "oos_events": 130, "fill": 1.0},
        {"family": "1 calibration", "rule": "mid 0-5c", "side": "yes", "entry": "mk", "is_ret": -0.4, "is_t": -4.0,
         "oos_ret": -0.5, "oos_t": -5.0, "oos_evt": -3.0, "oos_win": 0.02, "is_events": 110, "oos_events": 100, "fill": 0.55},
        {"family": "1 calibration", "rule": "mid 0-5c", "side": "yes", "entry": "tk", "is_ret": -0.3, "is_t": -3.0,
         "oos_ret": -0.2, "oos_t": -2.0, "oos_evt": np.nan, "oos_win": 0.03, "is_events": 121, "oos_events": 131, "fill": 1.0},
    ])
    t = round_tables.table(d).splitlines()
    assert len(t) == 2 + 3 and t[0].count("|") == 13 and t[1] == "|" + "---|" * 12
    assert t[2] == ("| 1 calibration | mid 0-5c | NO | taker | +2.0% | 2.5 | +3.0% | 3.5 | 2.2 | 97.0% | 120 / 130 |  |")
    assert t[3].endswith("| 110 / 100 | 55% |") and "| resting |" in t[3]
    assert round_tables.table(d, with_family=False).splitlines()[0].startswith("| Rule |")
    c = round_tables.calibration(d).splitlines()
    assert c[2] == "| 0-5c | −30.0% / −20.0% | +2.0% / +3.0% | −40.0% / −50.0% |  | 121 / 131 |"
    assert round_tables.calibration(d.assign(family="2 bonds")) == ""


# ---- calibration curve -----------------------------------------------------------------------------------------

def test_calibration_curve_is_one_market_per_band_and_finds_a_planted_gap(world, tmp_path, monkeypatch, capsys):
    p, f = world["p"], world["f"]
    c = calibration_curve.curve(p, f)
    assert list(c.columns) == ["band", "half", "markets", "events", "mean_mid", "yes_rate", "gap", "t", "ev_gap", "ev_t"]
    assert set(c["half"]) == {"in", "out"} and (c["events"] <= c["markets"]).all()
    np.testing.assert_allclose(c["gap"], c["yes_rate"] - c["mean_mid"], atol=1e-6)
    # the out-of-sample 0-5c row, by hand: first tradable bar of each market in the band
    idx = p.first_per_market(f.base & f.price(0.0, 0.05))
    idx = idx[p.oos[idx]]
    d = pd.DataFrame({"event": p.event[idx], "gap": p.y[idx] - p.df["mid"].to_numpy("float64")[idx]})
    row = c[(c["band"] == "0-5c") & (c["half"] == "out")].iloc[0]
    assert row["markets"] == len(idx) == p.ticker[idx].size and row["events"] == d["event"].nunique()
    assert row["gap"] == pytest.approx(d["gap"].mean(), abs=1e-9)
    assert row["ev_gap"] == pytest.approx(d.groupby("event")["gap"].mean().mean(), abs=1e-9)
    one = calibration_curve.curve(p, f, bands=[(0.0, 0.05)])
    pd.testing.assert_frame_equal(one, c[c["band"] == "0-5c"].reset_index(drop=True))
    # quotes under 30c planted 4c above the truth: the 10-20c band shows it in both halves
    db = tmp_path / "dear.db"
    tools_db(db, n_events=150, seed=4, bias={cat: 0.04 for cat, _ in CATS})
    q = Panel(panel.load(db))
    band = calibration_curve.curve(q, Features(q), bands=[(0.10, 0.20)])
    assert len(band) == 2 and (band["gap"] < -0.015).all() and (band["t"] < -1).all(), band
    assert run_main(monkeypatch, calibration_curve, "--db", world["db"]) == 0
    assert "0-5c" in capsys.readouterr().out
    assert run_main(monkeypatch, calibration_curve, "--db", world["db"], "--categories", "Nothing") == 1


# ---- resting variants ----------------------------------------------------------------------------------------

def test_a_resting_variant_fills_only_when_the_market_trades_through(hand):
    p = hand["p"]
    mask = (hand["df"]["ticker"] == "R").to_numpy()
    r0 = np.flatnonzero(mask)[0]
    join = resting_variants.variant(p, mask, 0.0, 1)                # NO bid 96c: YES bid reaches 4c on the next bar
    assert len(join) == 1 and join["ts"].iloc[0] == p.df["ts"].iloc[r0] and join.attrs["fill_rate"] == 1.0
    assert join["cost"].iloc[0] == pytest.approx(0.96, abs=1e-6) and join["r"].iloc[0] == pytest.approx(0.04 / 0.96, rel=1e-5)
    deeper = resting_variants.variant(p, mask, 0.01, 1)             # 95c: the first order is not reached, the second is
    assert deeper["ts"].iloc[0] == p.df["ts"].iloc[r0 + 1] and deeper.attrs["fill_rate"] == 0.0
    longer = resting_variants.variant(p, mask, 0.01, 3)             # left three bars, the first order is reached
    assert longer["ts"].iloc[0] == p.df["ts"].iloc[r0] and longer.attrs["fill_rate"] == 1.0
    inside = resting_variants.variant(p, mask, -0.01, 1)            # 97c, inside the 2c spread
    assert inside["cost"].iloc[0] == pytest.approx(0.97, abs=1e-6)
    crossed = resting_variants.variant(p, mask, -0.02, 1)           # 98c would meet the YES bid: never placed
    assert crossed.empty and np.isnan(crossed.attrs["fill_rate"])
    d = resting_variants.describe(join)
    assert d["bets"] == 1 and d["out_lost"] == "0/1" and d["out_tail"] == "no" and "in_mean" not in d
    assert d["out_mean"] == pytest.approx(0.04 / 0.96, rel=1e-5)


def test_resting_variants_main_more_time_more_fills(world, monkeypatch, frames):
    assert run_main(monkeypatch, resting_variants, "--db", world["db"], "--categories", "Economics,Entertainment") == 0
    t = frames[-1]
    grid = [[d, w] for d in (-1, 0, 1, 2, 3) for w in (1, 3, 7)]
    got = t[["deeper_c", "window"]].values.tolist()
    # variants that never filled are left out (here the YES bid never rises 2c+ above the ask within one bar)
    assert got == [g for g in grid if g in got] and grid[:9] == got[:9] and [2, 1] not in got and len(got) >= 12
    for col in ("bets", "events", "fill", "price", "mean", "in_mean", "in_lost", "in_tail", "in_cagr", "out_mean", "out_cagr"):
        assert col in t
    for _, g in t.groupby("deeper_c"):
        assert g["fill"].is_monotonic_increasing and g["bets"].is_monotonic_increasing
    for _, g in t[t["deeper_c"] >= 0].groupby("window"):
        assert g["bets"].is_monotonic_decreasing                      # a cheaper bid is reached less often
    assert run_main(monkeypatch, resting_variants, "--db", world["db"], "--categories", "Nothing") == 1


# ---- the engine's corners: backtest, families, portfolio --------------------------------------------------------

def test_evaluate_custom_matches_evaluate(world, hand):
    p, f = world["p"], world["f"]
    m = f.base & f.price(0.1, 0.5)
    a = p.evaluate(m, "no", "tk")
    b = p.evaluate_custom(m, p.r[("no", "tk")], p.px[("no", "tk")], 1 - p.y)
    assert same(a[0], b[0]) and same(a[1], b[1]) and a[0].n > 50
    every = p.evaluate_custom(m, p.r[("no", "tk")], p.px[("no", "tk")], 1 - p.y, once=False)
    assert every[0].n > a[0].n
    h = hand["p"]                                                    # the ladder pair trade
    pair = h.r[("pair", "pair")]
    assert np.isfinite(pair).sum() > 0
    x = h.evaluate(np.ones(h.n, bool), "pair", "pair")
    y = h.evaluate_custom(np.ones(h.n, bool), pair, h.px[("pair", "pair")], (pair > 0).astype("float32"))
    assert same(x[1], y[1]) and x[1].n == 2 and x[0].n == 0          # two rungs have a rung above them


def test_fill_rate_and_the_lead_verdict(world):
    p, f = world["p"], world["f"]
    fr = p.fill_rate(f.base & f.price(0.1, 0.5), "no")
    assert 0.3 < fr < 1.0
    assert math.isnan(p.fill_rate(np.zeros(p.n, bool), "no"))
    r = {"is_events": 150, "oos_events": 150, "is_ret": 0.01, "oos_ret": 0.02, "is_t": 1.0, "oos_t": 2.5}
    assert verdict(r) == "lead"
    strong = {**r, "is_t": 2.5, "oos_t": 3.5, "is_evret": 0.01, "oos_evt": 2.5}
    assert verdict(strong) == "pass"
    assert verdict({**strong, "oos_evt": 1.0}) == "lead"             # per bet yes, per event no: not a pass
    assert verdict({**strong, "is_evret": -0.01}) == "lead"
    assert verdict({**r, "oos_t": 1.5}) == "no" and verdict({**r, "is_events": 50}) == "thin"


@pytest.fixture(scope="module")
def one_biased_series(tmp_path_factory):
    db = tmp_path_factory.mktemp("pers") / "pers.db"
    tools_db(db, n_events=150, seed=9, bias={"Economics": 0.06, "Entertainment": 0.0, "Climate and Weather": 0.0})
    return db


def test_persistence_picks_the_series_that_paid_and_tests_it_out_of_sample(one_biased_series):
    p = Panel(panel.load(one_biased_series))
    f = Features(p)
    out = list(persistence(f))
    series = p.df["series"].to_numpy(object)
    names = {(fam, name, side, entry): (mask, k) for fam, name, mask, side, entry, k in out}
    assert all(fam == "11 persistence" for fam, *_ in names)
    mask, k = names[("11 persistence", "series that paid in sample: NO at mid 3-20c", "no", "tk")]
    assert k == 1 and set(series[mask]) == {"ECO"}                   # only the biased series is carried forward
    ins, oos = p.evaluate(mask, "no", "tk")
    assert oos.n > 20 and oos.ret > 0                                # and it keeps paying out of sample
    assert not any(side == "yes" and "3-20c" in name for (_, name, side, _) in names)
    assert list(persistence(f, min_events=10_000)) == []             # no series has that many events


def test_run_sweep_judges_persistence_rules_out_of_sample_only(one_biased_series, results_here, monkeypatch):
    assert run_main(monkeypatch, run_sweep, "--round", "p", "--db", one_biased_series, "--min-events", "20") == 0
    out = pd.read_csv(results_here / "p.csv")
    pers = out[out["family"] == "11 persistence"]
    assert len(pers) >= 1 and pers["rule"].str.endswith("(1 series)").any() and pers["fill"].isna().all()
    for _, r in pers.iterrows():
        want = ("thin" if r["oos_events"] < 20 else "pass" if r["oos_ret"] > 0 and r["oos_t"] >= 3 else
                "lead" if r["oos_ret"] > 0 and r["oos_t"] >= 2 else "no")
        assert r["verdict"] == want, r["rule"]
    assert (pers["verdict"] != "thin").any()


def test_account_corners():
    a = portfolio.Account(bets=3, total=0.1)
    assert a.cells("x") == {"x_bets": 3, "x_total": 0.1, "x_cagr": 0.0, "x_maxdd": 0.0, "x_sharpe": a.sharpe,
                            "x_exposure": 0.0, "x_years": 0.0}
    assert empty_account(portfolio.simulate(np.zeros((0, 4))))
    # everything on one bet that loses it all: the account is empty and stops
    bets = np.array([[0.0, DAY, -1.0, 0], [2 * DAY, 3 * DAY, 0.5, 1], [4 * DAY, 5 * DAY, 0.5, 2]])
    gone = portfolio.simulate(bets, stake_frac=1.0, event_cap=1.0, max_exposure=1.0)
    assert gone.bets == 1 and gone.total == pytest.approx(-1.0) and gone.max_dd == pytest.approx(1.0) and gone.cagr == -1.0


def test_account_replay_with_no_entries(world):
    p = world["p"]
    a, o = portfolio.run(p, [(np.zeros(p.n, bool), "no", "tk")])
    assert empty_account(a) and empty_account(o)


def test_account_replay_splits_where_the_backtest_does(hand):
    p, f = hand["p"], hand["f"]
    x = f.base & (hand["df"]["ticker"] == "X").to_numpy()
    ins, oos = p.evaluate(x, "no", "tk")
    assert (ins.n, oos.n) == (1, 0)                                  # the backtest: in sample (closes before the split)
    a, o = portfolio.run(p, [(x, "no", "tk")])
    assert (a.bets, o.bets) == (1, 0)


def test_exits_skip_unquoted_bars_and_run_on_nothing(hand):
    from exits import Policy
    p = hand["p"]
    ex = Exits(p)
    empty = ex.run(np.zeros(0, "int64"), "no", "tk", HOLD)
    assert empty.r.size == 0 and empty.reason.size == 0
    u = int(np.flatnonzero((hand["df"]["ticker"] == "U").to_numpy())[0])
    assert not p.df["quoted"].iloc[u + 1]                            # bar 1 of U has no bid
    r, rel, why, got, cost = ex.follow(u, "yes", "tk", Policy("late", days=100))
    assert why == "time" and rel == p.df["ts"].iloc[u + 3]            # not decided on bar 1: sold at bar 3's open


# ---- shadow_longshot: the branches test_shadow.py leaves out ------------------------------------------------------

NOW = 1_800_000_000.0


class FlakyHTTP(FakeKalshiHTTP):
    """A fake exchange that refuses chosen paths: {path prefix: status}."""

    def __init__(self, now, fail=None):
        super().__init__(now)
        self.fail = dict(fail or {})

    def get(self, path, tries=6, **params):
        for prefix, status in self.fail.items():
            if path.startswith(prefix) and (prefix != "/markets/trades" or params.get("ticker") in self.fail_tickers):
                self.requests += 1
                raise KalshiError(status, path, "refused")
        return super().get(path, tries=tries, **params)

    fail_tickers: set = set()


def shadow_setup(tmp_path, http=None):
    http = http or FakeKalshiHTTP(NOW)
    venue = Kalshi(http=http, clock=lambda: NOW)
    venue._load_series(["Economics"])
    db = sl.open_db(sqlite3.connect(str(tmp_path / "shadow.db")))
    return http, venue, db


def test_candidates_skip_bad_rows_and_other_categories():
    good = {"ticker": "G", "event_ticker": "KXCPIYOY-1", "yes_bid_dollars": "0.02", "yes_ask_dollars": "0.03",
            "volume_fp": "90000", "close_time": "2027-01-25T00:00:00Z"}
    now = pd.Timestamp("2027-01-15", tz="UTC").timestamp()
    listing = {"markets": [good, {"ticker": "NOQUOTE"}, {**good, "ticker": "TEXT", "yes_bid_dollars": "n/a"},
                           {**good, "ticker": "NONE", "yes_ask_dollars": None},
                           {**good, "ticker": "SPORT", "event_ticker": "KXNBA-1"}, {**good, "ticker": "DEAR", "yes_bid_dollars": "0.20"}]}
    cat = {"KXCPIYOY-1": "economics", "KXNBA-1": "sports"}.get
    assert [m["ticker"] for m in sl.candidates(listing, {"economics"}, cat, 45000, set(), now)] == ["G"]
    assert sl.candidates({}, {"economics"}, cat, 45000, set(), now) == []


def test_look_says_why_a_candidate_was_not_recorded(tmp_path):
    http = FlakyHTTP(NOW, fail={"/events/": 500})
    http.add("OK", days=10, bid=0.02, ask=0.03, volume=90000)
    http.add("SHUT", days=10, bid=0.02, ask=0.03, volume=90000)
    http.markets["SHUT"]["status"] = "closed"
    http.add("LATE", days=40, bid=0.02, ask=0.03, volume=90000)
    http.add("QUIET", days=10, bid=0.02, ask=0.03, volume=500)
    http.add("ONESIDE", days=10, bid=0.02, ask=0.03, volume=90000)
    http.books["ONESIDE"] = {"orderbook_fp": {"yes_dollars": [["0.0200", "400.00"]], "no_dollars": []}}
    _, venue, db = shadow_setup(tmp_path, http)
    look = lambda t: sl.look(venue, db, {"ticker": t}, NOW, 20.0, 45000.0)    # noqa: E731
    assert look("GONE") == "gone"
    assert look("SHUT") == "closed"
    assert look("LATE") == "40 days to the end"
    assert look("QUIET") == "volume below the tested level"
    assert look("ONESIDE") == "one-sided book"
    assert look("OK") == "recorded"                                  # the event lookup failed: size left unknown
    assert db.execute("SELECT ticker, ev_markets FROM obs").fetchall() == [("OK", None)]


def test_resting_fill_ignores_unreadable_trades():
    t = lambda **k: {"taker_side": "yes", "yes_price_dollars": "0.0300", "count_fp": "10", "created_time": "2026-01-01T00:00:00Z", **k}  # noqa: E731
    assert sl.resting_fill([t(count_fp=None), t(yes_price_dollars="x"), {"taker_side": "yes"}], 0.03, 5.0) is None
    assert sl.resting_fill([t(count_fp="3"), t(count_fp="3", created_time="2026-01-02T00:00:00Z")], 0.03, 5.0) == \
        pd.Timestamp("2026-01-02", tz="UTC").timestamp()
    assert sl.resting_fill([t(count_fp="999")], 0.03, None) is None      # no queue recorded: only a trade through counts


def test_track_resting_skips_a_refused_market_and_stops_on_429(tmp_path):
    http = FlakyHTTP(NOW, fail={"/markets/trades": 500})
    _, venue, db = shadow_setup(tmp_path, http)
    for t in ("A", "B"):
        db.execute("INSERT INTO obs (ticker, seen_ts, end_ts, yes_ask, rest_px, rest_ahead, stake) VALUES (?,?,?,?,?,?,?)",
                   (t, NOW, NOW + 10 * DAY, 0.03, 0.97, 100.0, 20.0))
    http.fail_tickers = {"A"}
    assert sl.track_resting(venue, db, NOW + 100 * 3600) == 1         # A refused (500) and skipped; B decided unfilled
    assert db.execute("SELECT ticker, rest_done FROM obs ORDER BY ticker").fetchall() == [("A", None), ("B", 1)]
    http.fail = {"/markets/trades": 429}
    before = http.requests
    assert sl.track_resting(venue, db, NOW + 100 * 3600) == 0 and http.requests == before + 1


def test_observe_stops_on_errors_and_keeps_to_its_limits(tmp_path):
    http = FlakyHTTP(NOW)
    for t in ("L1", "L2", "L3", "L4"):
        http.add(t, days=10, bid=0.02, ask=0.03, size=400, volume=90000)    # all one event
    listing = {"markets": [dict(m) for m in http.markets.values()]}
    _, venue, db = shadow_setup(tmp_path, http)
    res = sl.observe(venue, db, listing, {"economics"}, NOW)            # two per event by default
    assert res["looked"] == 2 and res["recorded"] == 2
    assert sl.observe(venue, db, listing, {"economics"}, NOW, per_event=10, max_new=1)["looked"] == 1
    # an order book refused with a 500 is noted as such
    http.fail = {f"/markets/{t}/orderbook": 500 for t in http.markets}
    assert sl.observe(venue, db, listing, {"economics"}, NOW, per_event=10) == \
        {"recorded": 0, "looked": 1, "settled": 0, "resting_decided": 0}
    assert db.execute("SELECT COUNT(*) FROM checked WHERE why='error 500'").fetchone() == (1,)
    # the settlement pass: a refused detail stops it before the next market
    first, second = [r[0] for r in db.execute("SELECT ticker FROM obs ORDER BY ticker LIMIT 2")]
    db.execute("UPDATE obs SET end_ts=? WHERE ticker=?", (NOW - 2, first))
    db.execute("UPDATE obs SET end_ts=? WHERE ticker=?", (NOW - 1, second))
    http.settle(first, "no")
    http.settle(second, "yes")
    http.fail = {f"/markets/{first}": 500}
    assert sl.observe(venue, db, {"markets": []}, set(), NOW)["settled"] == 0
    http.fail = {}
    assert sl.observe(venue, db, {"markets": []}, set(), NOW)["settled"] == 2
    # a 429 on the order book stops the round: nothing is looked at, nothing marked as checked
    sub = tmp_path / "b"
    sub.mkdir()
    http2 = FlakyHTTP(NOW, fail={"/markets/M/orderbook": 429, "/markets/N/orderbook": 429})
    http2.add("M", days=10, bid=0.02, ask=0.03, volume=90000)
    http2.add("N", days=10, bid=0.02, ask=0.03, volume=90000)
    _, venue2, db2 = shadow_setup(sub, http2)
    r2 = sl.observe(venue2, db2, {"markets": [dict(m) for m in http2.markets.values()]}, {"economics"}, NOW, per_event=10)
    assert r2["looked"] == 0 and db2.execute("SELECT COUNT(*) FROM checked").fetchone() == (0,)


def test_report_corners(tmp_path):
    _, _, db = shadow_setup(tmp_path)
    assert sl.report(db) == "no observations yet"
    db.execute("INSERT INTO obs (ticker, category, no_ask, ask_contracts, ask_usd_1c, fill_px, fill_shares, fee, stake, result, "
               "rest_px, maker_rate, rest_filled, rest_done) VALUES ('A', 'economics', 0.98, 100, 200, 0.98, 20, 0.03, 20, 'no', "
               "0.97, 0.0175, 1, 1)")
    text = sl.report(db)
    assert "1 decided, 1 filled (100%" in text and "of the filled, 1 settled, 0 lost" in text
    cost = 0.97 + 0.0175 * 0.97 * 0.03
    assert f"{1 / cost - 1:+.2%} per dollar" in text


def test_shadow_main_reports_and_observes_on_a_fake_exchange(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sl, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    assert run_main(monkeypatch, sl, "--report") == 0
    assert "no observations yet" in capsys.readouterr().out
    assert run_main(monkeypatch, sl) == 3                              # no listing written yet
    assert "no market listing yet" in capsys.readouterr().out
    http = FakeKalshiHTTP(time.time())
    http.add("LONG", days=10, bid=0.02, ask=0.03, size=400, volume=90000)
    (tmp_path / "data" / "kalshi_listing.json").write_text(json.dumps({"markets": list(http.markets.values())}), encoding="utf-8")
    monkeypatch.setattr(sl, "Kalshi", lambda min_interval, cache_dir: Kalshi(http=http, cache_dir=cache_dir))
    assert run_main(monkeypatch, sl, "--pace", "0") == 0
    out = capsys.readouterr().out
    assert "shadow longshot: looked at 1, recorded 1" in out and "1 qualifying markets seen" in out
    assert (tmp_path / "data" / "shadow.db").exists() and (tmp_path / "data" / "kalshi_series.json").exists()


def test_entry_timing_pairs_the_same_markets_early_and_late(world):
    p, f = world["p"], world["f"]
    _, mask = analyze_rule.find_rule(f, world["titles"], WIDE, "no", "mk")
    cv = p.df["cumvol"].to_numpy()
    level = float(np.median(cv[mask])) if mask.any() else 1.0
    e, lt, rest = entry_timing.timing_pair(p, mask, "no", "mk", level)
    assert list(e["ticker"]) == list(lt["ticker"])
    assert (e["ts"].to_numpy() <= lt["ts"].to_numpy()).all()
    late_rows = p.df.set_index(["ticker", "ts"]).loc[list(zip(lt["ticker"], lt["ts"])), "cumvol"].to_numpy()
    assert (late_rows >= level).all()
    allb = analyze_rule.bets_frame(p, mask, "no", "mk")
    assert len(e) + len(rest) == len(allb) and not set(rest["ticker"]) & set(lt["ticker"])


def test_no_drift_signs_and_horizons():
    df = pd.DataFrame({
        "ticker": ["A"] * 4 + ["B"] * 2, "event": ["EA"] * 4 + ["EB"] * 2, "oos": [False] * 4 + [True] * 2,
        "dte": [10.0, 9, 8, 7, 3, 2], "age": [0.0, 1, 2, 3, 0, 1], "life": [10.0] * 4 + [4.0] * 2,
        "mid": [0.30, 0.25, 0.20, 0.50, 0.10, 0.12], "quoted": [True] * 6, "y": [0.0] * 4 + [1.0] * 2})
    d = no_drift.drift_frame(df, 0.05, 0.35, horizons=(1, 3))
    assert len(d) == 5                                       # the 0.50 bar is outside the band
    assert d["d1"].iloc[0] == pytest.approx(0.05)            # YES 0.30 -> 0.25: NO dearer by 5c
    assert d["d3"].iloc[0] == pytest.approx(-0.20)           # 0.30 -> 0.50 three bars later
    assert np.isnan(d["d1"].iloc[4])                         # B's last bar: nothing after it
    assert d["settle"].iloc[3] == pytest.approx(0.10 - 1.0)  # YES won: NO loses its price
    assert list(d["dte_bin"].astype(str)[:2]) == ["7-30d", "7-30d"]
    x = no_drift.by_event(d, "settle")
    assert x["events"] == 2
