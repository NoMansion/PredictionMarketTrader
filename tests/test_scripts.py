"""The command-line scripts, run in-process against a throwaway project folder.

Nothing here reads or writes the real data/ folder, the network or Claude: every script's ROOT is pointed at
tmp_path (autouse fixture below), the exchange is the offline fake from tests/fakes.py, the forecaster answers
from a table, and the paper loop's subprocess and sleep are replaced."""
import csv
import json
import re
import runpy
import sqlite3
import sys
import time
import types
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import _bootstrap  # noqa: E402
import demo_offline  # noqa: E402
import export_forecasts  # noqa: E402
import paper_loop as pl  # noqa: E402
import replay_wide  # noqa: E402
import run_cycle  # noqa: E402
import run_variants  # noqa: E402
import status  # noqa: E402
from fakes import FakeKalshiHTTP, TableForecaster  # noqa: E402

from src import runtime, safety  # noqa: E402
from src.kalshi import Kalshi  # noqa: E402
from src.ledger import Ledger  # noqa: E402
from src.replay import grid, load, replay  # noqa: E402
from src.trader import Trader  # noqa: E402

T = "KXCPIYOY-26NOV-T3.6"
H = 3600.0
SCRIPT_MODULES = (demo_offline, export_forecasts, pl, replay_wide, run_cycle, run_variants, status)


class Recorder:
    """Stands in for a venue class: remembers how it was built, never opens a connection."""

    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs


@pytest.fixture(autouse=True)
def project(tmp_path, monkeypatch):
    """Every script thinks tmp_path is the project folder; no script can reach the exchange or Claude by default."""
    for mod in SCRIPT_MODULES:
        monkeypatch.setattr(mod, "ROOT", tmp_path)
    monkeypatch.setattr(run_cycle, "Kalshi", Recorder)
    monkeypatch.setattr(run_cycle, "PolymarketUS", Recorder)
    monkeypatch.setattr(run_cycle, "make_backend", lambda cfg, root: TableForecaster({}))
    monkeypatch.setattr(runtime, "lower_priority", lambda: None)       # never lower the test process
    return tmp_path


def base_cfg(**over):
    c = {"account": {"mode": "paper", "venue": "kalshi", "paper_bankroll": 1000.0},
         "universe": {"categories_allow": ["economics"], "categories_deny": ["sports"]},
         "forecaster": {"model": "opus"}, "sizing": {"shrink_weight": 1.0, "max_disagreement": 1.0},
         "execution": {"style": "passive"}, "fees": {"taker_rate": 0.07, "round_up_cents": True},
         "safety": {}, "runtime": {"low_priority": False}}
    for k, v in over.items():
        c[k] = {**c.get(k, {}), **v}
    return c


def write_cfg(tmp_path, cfg=None, name="config.yaml"):
    p = tmp_path / name
    p.write_text(yaml.safe_dump(cfg or base_cfg()), encoding="utf-8")
    return p


def argv(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["script.py", *[str(a) for a in args]])


def fake_exchange(monkeypatch, table, *tickers, module=run_cycle):
    """A live-shaped Kalshi on the offline HTTP fake, and a table forecaster, wired into run_cycle."""
    http = FakeKalshiHTTP(time.time())
    for t in tickers or (T,):
        http.add(t, bid=0.48, ask=0.50)
    fc = TableForecaster(table)
    monkeypatch.setattr(module, "make_venue", lambda cfg: Kalshi(http=http))
    if module is run_cycle:
        monkeypatch.setattr(run_cycle, "make_backend", lambda cfg, root: fc)
    return http, fc


# ==== scripts/_bootstrap.py =========================================================================================

def test_bootstrap_puts_the_project_on_the_path_and_loads_dotenv(monkeypatch):
    root = str(Path(_bootstrap.__file__).resolve().parent.parent)
    monkeypatch.setattr(sys, "path", [p for p in sys.path if p != root])
    loaded = []
    monkeypatch.setitem(sys.modules, "dotenv", types.SimpleNamespace(load_dotenv=lambda p: loaded.append(Path(p))))
    ns = runpy.run_path(_bootstrap.__file__)
    assert sys.path[0] == root and ns["ROOT"] == Path(root)
    assert loaded == [Path(root) / ".env"]


def test_bootstrap_survives_odd_consoles_and_no_dotenv(monkeypatch):
    class Stubborn:
        def __init__(self, exc):
            self.exc, self.calls = exc, 0

        def reconfigure(self, **kw):
            self.calls += 1
            raise self.exc

        def write(self, s):
            return len(s)

        def flush(self):
            pass

    out, err = Stubborn(ValueError("detached")), Stubborn(OSError("no console"))
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    monkeypatch.setitem(sys.modules, "dotenv", None)                  # `import dotenv` raises ImportError
    ns = runpy.run_path(_bootstrap.__file__)
    assert out.calls == 1 and err.calls == 1 and "ROOT" in ns


# ==== scripts/run_cycle.py ==========================================================================================

def test_make_venue_builds_the_configured_exchange(tmp_path):
    k = run_cycle.make_venue({"runtime": {"venue_min_interval_s": 2.5, "listing_cache_hours": 5}})
    assert isinstance(k, Recorder)
    assert k.kwargs == {"min_interval": 2.5, "cache_dir": tmp_path / "data", "listing_cache_hours": 5.0}
    k = run_cycle.make_venue({})                                       # kalshi is the default, 1 s, 20 h
    assert k.kwargs == {"min_interval": 1.0, "cache_dir": tmp_path / "data", "listing_cache_hours": 20.0}
    p = run_cycle.make_venue({"account": {"venue": "Polymarket_US"}})
    assert p.kwargs == {"min_interval": 1.0}
    with pytest.raises(ValueError, match="unknown account.venue 'nyse'"):
        run_cycle.make_venue({"account": {"venue": "NYSE"}})


def test_a_cycle_records_its_run_forecast_decision_and_order(tmp_path, monkeypatch, capsys):
    http, fc = fake_exchange(monkeypatch, {T: 0.60})
    argv(monkeypatch, "--config", write_cfg(tmp_path))
    assert run_cycle.main() == 0
    out = capsys.readouterr().out
    assert "paper account opened with $1,000.00" in out
    led = Ledger(tmp_path / "data" / "pmt.db")
    try:
        runs = led.q("SELECT * FROM runs")
        assert len(runs) == 1 and runs[0]["status"] == "ok" and runs[0]["finished"] is not None
        assert json.loads(runs[0]["summary"])["log"]                      # the cycle log is kept with the run
        assert re.search(rf"cycle {re.escape(runs[0]['run_id'])}: ok in \d+ s \| equity \$1,000\.00", out)
        assert "| 1 forecasts, 1 orders" in out and "1 resting orders" in out
        assert fc.asked == [T]
        f = led.one("SELECT * FROM forecasts")
        assert f["p_yes"] == pytest.approx(0.60) and f["market_mid"] == pytest.approx(0.49) and f["run_id"] == runs[0]["run_id"]
        d = led.q("SELECT * FROM decisions")
        assert len(d) == 1 and d[0]["action"] == "BUY_YES" and d[0]["forecast_id"] == f["id"]
        o = led.q("SELECT * FROM orders")
        assert len(o) == 1 and o[0]["status"] == "resting" and o[0]["outcome"] == "YES"
        assert led.deposits() == 1000.0
    finally:
        led.close()
    assert not (tmp_path / "data" / "cycle.lock").exists()             # the lock is released

    # a second cycle: the account is not opened again, the market is not re-forecast before it is due
    assert run_cycle.main() == 0
    out = capsys.readouterr().out
    assert "paper account opened" not in out and fc.asked == [T]
    led = Ledger(tmp_path / "data" / "pmt.db")
    assert led.deposits() == 1000.0 and len(led.q("SELECT * FROM runs")) == 2
    led.close()


def test_no_forecast_marks_and_records_without_asking(tmp_path, monkeypatch, capsys):
    http, fc = fake_exchange(monkeypatch, {T: 0.60})
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--no-forecast")
    assert run_cycle.main() == 0
    assert fc.asked == []
    led = Ledger(tmp_path / "data" / "pmt.db")
    assert led.q("SELECT * FROM forecasts") == [] and led.q("SELECT * FROM orders") == []
    assert led.one("SELECT status FROM runs")["status"] == "ok"
    led.close()


def test_db_argument_keeps_a_trial_run_off_the_main_ledger(tmp_path, monkeypatch):
    fake_exchange(monkeypatch, {T: 0.60})
    trial = tmp_path / "trial.db"
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--db", trial)
    assert run_cycle.main() == 0
    assert trial.exists() and not (tmp_path / "data" / "pmt.db").exists()


def test_backend_and_trader_get_the_project_root(tmp_path, monkeypatch):
    fake_exchange(monkeypatch, {})
    seen = {}
    monkeypatch.setattr(run_cycle, "make_backend", lambda cfg, root: seen.setdefault("root", root) and TableForecaster({}))
    argv(monkeypatch, "--config", write_cfg(tmp_path))
    assert run_cycle.main() == 0
    assert seen["root"] == tmp_path


def test_kill_switch_is_a_safety_stop_exit_code(tmp_path, monkeypatch, capsys):
    http, fc = fake_exchange(monkeypatch, {T: 0.60})
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "STOP").write_text("stop", encoding="utf-8")
    argv(monkeypatch, "--config", write_cfg(tmp_path))
    assert run_cycle.main() == safety.EXIT_CODE == 4
    assert ": stopped in" in capsys.readouterr().out
    led = Ledger(tmp_path / "data" / "pmt.db")
    assert led.one("SELECT status FROM runs")["status"] == "stopped" and led.q("SELECT * FROM orders") == []
    led.close()
    assert fc.asked == []


def test_another_cycle_holding_the_lock_skips(tmp_path, monkeypatch, capsys):
    http, fc = fake_exchange(monkeypatch, {T: 0.60})
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "cycle.lock").write_text("pid 1 started earlier", encoding="utf-8")
    argv(monkeypatch, "--config", write_cfg(tmp_path))
    assert run_cycle.main() == 3
    assert "skipped: another cycle holds" in capsys.readouterr().out
    assert not (tmp_path / "data" / "pmt.db").exists() and fc.asked == []
    assert (tmp_path / "data" / "cycle.lock").read_text(encoding="utf-8") == "pid 1 started earlier"   # not ours to remove


def test_quiet_window_and_low_memory_skip_before_anything(tmp_path, monkeypatch, capsys):
    http, fc = fake_exchange(monkeypatch, {T: 0.60})
    argv(monkeypatch, "--config", write_cfg(tmp_path, base_cfg(runtime={"quiet_windows": ["00:00-24:00"]})))
    assert run_cycle.main() == 3
    assert "skipped: quiet window 00:00-24:00" in capsys.readouterr().out
    monkeypatch.setattr(runtime, "free_memory_gb", lambda: 0.5)
    argv(monkeypatch, "--config", write_cfg(tmp_path, base_cfg(runtime={"min_free_gb": 2})))
    assert run_cycle.main() == 3
    assert "only 0.5 GB of memory free (needs 2 GB)" in capsys.readouterr().out
    assert not (tmp_path / "data").exists() and fc.asked == [] and http.requests == 0


def test_scan_lists_candidates_and_changes_nothing(tmp_path, monkeypatch, capsys):
    http, fc = fake_exchange(monkeypatch, {T: 0.60}, T, "KXCPIYOY-26NOV-T3.7", "KXCPIYOY-26NOV-T9.9")
    http.set_book("KXCPIYOY-26NOV-T9.9", 0.03, 0.05)                    # a longshot: dropped by the price range
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--scan")
    assert run_cycle.main() == 0
    out = capsys.readouterr().out
    assert "3 open markets listed in economics; 2 pass the listing filters" in out
    assert re.search(r"dropped\s+1\s+\S", out)
    cands = out.split("Candidates in forecast order")[1]
    assert cands.count("Will KXCPIYOY-26NOV-T3.") == 2 and "T9.9" not in cands
    assert "0.480/0.500" in cands
    assert fc.asked == [] and not (tmp_path / "data").exists()         # no ledger, no lock, no forecast


def test_scan_failure_is_reported_not_raised(tmp_path, monkeypatch, capsys):
    class Down:
        requests = 0

        def list_markets(self, **kw):
            raise ConnectionError("gateway unreachable")

    monkeypatch.setattr(run_cycle, "make_venue", lambda cfg: Down())
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--scan")
    assert run_cycle.main() == 1
    assert "scan failed" in capsys.readouterr().out


# ==== scripts/run_variants.py =======================================================================================

VARIANTS_YAML = """variants:
  claude_only:
    about: Claude's number alone
    transform: none
    overrides: {sizing: {shrink_weight: 1.0, max_disagreement: 1.0}}
  control_fade:
    about: bets against Claude (a control)
    transform: fade
    overrides: {sizing: {shrink_weight: 1.0, max_disagreement: 1.0}}
"""


def variants_file(tmp_path, text=VARIANTS_YAML):
    p = tmp_path / "variants.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def main_account_cycle(tmp_path, http, table):
    """The main account's cycle (blend 0.3: no trade of its own), as run_cycle would leave it."""
    led = Ledger(tmp_path / "data" / "pmt.db")
    led.deposit(1000.0, "deposit: paper bankroll")
    Trader(base_cfg(sizing={"shrink_weight": 0.3}), led, Kalshi(http=http), TableForecaster(table), root=tmp_path).run()
    assert led.q("SELECT * FROM orders") == [] and len(led.q("SELECT * FROM forecasts")) == 1
    led.close()


def report_rows(out):
    return {line.split()[0]: line.split() for line in out.splitlines()
            if line and not line.startswith((" ", "account", "Equity"))}


def test_report_before_anything_ran_lists_every_account_and_the_controls_note(tmp_path, monkeypatch, capsys):
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--variants", variants_file(tmp_path), "--report")
    assert run_variants.main() == 0
    out = capsys.readouterr().out
    for name in ("main", "claude_only", "control_fade"):
        assert re.search(rf"^{name}\s+not started yet$", out, re.MULTILINE)
    assert "Two accounts are controls (they do not follow Claude)." in out
    assert "  claude_only: Claude's number alone" in out and "  control_fade: bets against Claude (a control)" in out
    assert "  main: the paper bot itself" in out
    assert not (tmp_path / "data").exists()                            # a report creates nothing


def test_variants_trade_the_main_forecasts_then_report(tmp_path, monkeypatch, capsys):
    http, _ = fake_exchange(monkeypatch, {}, module=run_variants)
    main_account_cycle(tmp_path, http, {T: 0.60})
    cfg, vf = write_cfg(tmp_path, base_cfg(sizing={"shrink_weight": 0.3})), variants_file(tmp_path)
    argv(monkeypatch, "--config", cfg, "--variants", vf)
    assert run_variants.main() == 0
    out = capsys.readouterr().out
    assert "[claude_only] ok: 1 new forecasts handed over, 1 orders, equity $1,000.00, 0 positions, 1 resting" in out
    assert "[control_fade] ok: 1 new forecasts handed over, 1 orders" in out
    assert re.search(r"^    .*resting BUY YES", out, re.MULTILINE) and re.search(r"^    .*resting BUY NO", out, re.MULTILINE)
    assert "variants: 2 accounts in" in out
    for name, side in (("claude_only", "YES"), ("control_fade", "NO")):
        led = Ledger(tmp_path / "data" / "variants" / f"{name}.db")
        assert [o["outcome"] for o in led.q("SELECT * FROM orders")] == [side]
        led.close()
    assert not (tmp_path / "data" / "cycle.lock").exists()

    argv(monkeypatch, "--config", cfg, "--variants", vf, "--report")
    assert run_variants.main() == 0
    rows = report_rows(capsys.readouterr().out)
    assert set(rows) == {"main", "claude_only", "control_fade"}
    #            account  equity   P&L     open resting filled expired settled forecasts
    assert rows["main"][1:9] == ["1000.00", "+0.00", "0", "0", "0", "0", "0", "1"]
    assert rows["claude_only"][1:9] == ["1000.00", "+0.00", "0", "1", "0", "0", "0", "1"]
    assert rows["control_fade"][4] == "1"


def test_only_runs_the_named_variants(tmp_path, monkeypatch, capsys):
    http, _ = fake_exchange(monkeypatch, {}, module=run_variants)
    main_account_cycle(tmp_path, http, {T: 0.60})
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--variants", variants_file(tmp_path), "--only", " control_fade , ")
    assert run_variants.main() == 0
    out = capsys.readouterr().out
    assert "[control_fade]" in out and "[claude_only]" not in out and "variants: 1 accounts" in out
    assert not (tmp_path / "data" / "variants" / "claude_only.db").exists()


def test_every_variant_failing_exits_1(tmp_path, monkeypatch, capsys):
    http, _ = fake_exchange(monkeypatch, {}, module=run_variants)
    main_account_cycle(tmp_path, http, {T: 0.60})
    broken = "variants:\n  broken:\n    overrides: {sizing: {no_such_setting: 1}}\n"
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--variants", variants_file(tmp_path, broken))
    assert run_variants.main() == 1
    out = capsys.readouterr().out
    assert "[broken] error" in out and re.search(r"^    .*Error.*no_such_setting", out, re.MULTILINE)


def test_no_variants_file_means_nothing_to_do(tmp_path, monkeypatch, capsys):
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--variants", tmp_path / "missing.yaml")
    assert run_variants.main() == 0
    assert "no variants defined" in capsys.readouterr().out
    assert not (tmp_path / "data").exists()


def test_variants_skip_in_a_quiet_window_or_while_a_cycle_runs(tmp_path, monkeypatch, capsys):
    http, _ = fake_exchange(monkeypatch, {}, module=run_variants)
    vf = variants_file(tmp_path)
    argv(monkeypatch, "--config", write_cfg(tmp_path, base_cfg(runtime={"quiet_windows": ["00:00-24:00"]})), "--variants", vf)
    assert run_variants.main() == 3
    assert "variants skipped: quiet window" in capsys.readouterr().out
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "cycle.lock").write_text("a cycle", encoding="utf-8")
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--variants", vf)
    assert run_variants.main() == 3
    assert "variants skipped: another cycle holds" in capsys.readouterr().out
    assert not (tmp_path / "data" / "variants").exists() and http.requests == 0


# ==== scripts/status.py =============================================================================================

NOW = time.time()


def status_ledger(path):
    """One open position (A), one resting order (B), one resolved forecast market (C), one cycle."""
    led = Ledger(path)
    led.deposit(1000.0, "deposit: paper bankroll")
    t0 = NOW - 100 * H
    led.upsert_market({"market_id": "A", "question": "Will A happen?", "category": "Economics", "end_ts": NOW + 9 * 86400})
    led.upsert_market({"market_id": "B", "question": "Will B happen?", "category": "Economics"})
    led.upsert_market({"market_id": "C", "question": "Will C happen?", "category": "Economics", "event_id": "ec"})
    fa = led.add_forecast({"market_id": "A", "p_yes": 0.70, "market_mid": 0.50, "ts": t0, "run_id": "r1", "model": "m"})
    led.add_forecast({"market_id": "C", "p_yes": 0.80, "market_mid": 0.60, "ts": t0, "run_id": "r1", "model": "m"})
    did = led.add_decision({"ts": t0, "run_id": "r1", "market_id": "A", "forecast_id": fa, "action": "BUY_YES",
                            "reason": "edge 0.10 after costs"})
    oid = led.add_order({"ts": t0, "run_id": "r1", "market_id": "A", "token_id": "A:YES", "outcome": "YES", "side": "BUY",
                         "limit_price": 0.50, "usd": 20.0, "shares": 40.0, "status": "resting", "decision_id": did})
    led.apply_fill(oid, "A", "A:YES", "YES", "BUY", 0.50, 40.0, ts=t0 + H, order_status="filled")
    led.add_order({"ts": NOW - H, "run_id": "r1", "market_id": "B", "token_id": "B:NO", "outcome": "NO", "side": "BUY",
                   "limit_price": 0.45, "usd": 10.0, "shares": 22.2, "status": "resting"})
    led.add_snapshot("A", 0.55, 0.57, 0.56, ts=t0 + 73 * H)            # 72 h on: the market moved toward the model
    led.add_snapshot("A", 0.59, 0.61, 0.60, ts=NOW)
    led.settle("C", 1.0, ts=NOW - 10 * H)
    led.record_equity({"A:YES": (0.59, 0.60)}, ts=NOW)
    led.start_run("r1")
    led.finish_run("r1", "ok", {"log": []})
    return led


def test_status_report_shows_account_positions_orders_scores_and_gates(tmp_path):
    led = status_ledger(tmp_path / "pmt.db")
    try:
        text = status.report(led, {"account": {"mode": "paper"}, "sizing": {"shrink_weight": 0.3}})
    finally:
        led.close()
    lines = text.splitlines()
    assert lines[0].startswith("# PolymarketTrader status, ") and "Mode: paper" in lines
    # equity = 980 cash + 40 shares at the 0.59 bid
    assert "- Equity $1,003.60 on $1,000.00 deposited: +3.60 (+0.4%), drawdown from peak 0.0%" in lines
    assert "- Cash $980.00; fees paid $0.00" in lines
    assert "- Markets traded 1, settled 0 (0 profitable, net +0.00)" in lines
    assert "## Open positions (1)" in lines
    assert "- YES 40 @ 0.500, now 0.600, model P(yes) 0.70: Will A happen?" in lines
    assert "## Resting orders (1)" in lines
    assert any(re.fullmatch(r"- buy NO \$10\.00 @ 0\.450 since \d{4}-\d\d-\d\d \d\d:\d\d: B", x) for x in lines)
    assert "- 2 forecasts on 2 markets; 1 of those markets have resolved" in lines
    assert any(x.startswith("- Verdict: too few resolved markets") for x in lines)
    # C: model 0.80 -> Brier 0.04, market 0.60 -> 0.16, blend 0.66 -> 0.1156
    assert any(x.startswith("- Brier score (lower is better): model 0.0400, market 0.1600, blend traded 0.1156; "
                            "model advantage +0.1200") for x in lines)
    assert "  - forecasts 80-100%: 1 markets, mean forecast 0.80, resolved yes 1.00" in lines
    # A: gap +0.20, 73 h later the mid was 0.56 (30% of the gap); C resolved after 90 h with no snapshot: not counted
    drift = [x for x in lines if x.startswith("- Price movement 72 h after")]
    assert len(drift) == 1 and "1 moved toward the model, 0 away" in drift[0] and "on 1 forecasts" in drift[0]
    gates = [x for x in lines if x.startswith("## Go-live gates")]
    assert gates == ["## Go-live gates (0 of 6 passed; all are required)"]
    assert sum(1 for x in lines if x.startswith("- [ ] ")) == 6
    assert any(re.search(r"BUY_YES\s+A: edge 0\.10 after costs$", x) for x in lines)
    assert lines[-1].endswith(" ok (r1)") and "## Last 5 cycles" in lines


def test_status_report_on_an_empty_ledger(tmp_path):
    led = Ledger(tmp_path / "pmt.db")
    led.deposit(1000.0)
    try:
        text = status.report(led, {})
    finally:
        led.close()
    assert "Mode: paper" in text and "## Open positions (0)" in text and "## Resting orders (0)" in text
    assert "- 0 forecasts on 0 markets; 0 of those markets have resolved" in text
    assert "Brier score" not in text
    assert "- No price-movement observations yet (needs forecasts at least 72 hours old)" in text
    assert status.fmt_ts(None) == "-" and status.fmt_ts(0) == "-"


def test_status_position_without_a_price_or_a_market_row(tmp_path):
    led = Ledger(tmp_path / "pmt.db")
    led.deposit(100.0)
    led.apply_fill(None, "GHOST", "GHOST:NO", "NO", "BUY", 0.40, 10.0)
    try:
        text = status.report(led, {})
    finally:
        led.close()
    assert "- NO 10 @ 0.400, now -, model P(yes) -: GHOST" in text


def test_status_main_reads_data_pmt_db_and_writes_status_md(tmp_path, monkeypatch, capsys):
    argv(monkeypatch, "--config", write_cfg(tmp_path))
    assert status.main() == 0
    assert "no data/pmt.db yet" in capsys.readouterr().out
    assert not (tmp_path / "data").exists()                            # looking does not create the ledger
    status_ledger(tmp_path / "data" / "pmt.db").close()
    assert status.main() == 0
    assert "## Open positions (1)" in capsys.readouterr().out
    assert not (tmp_path / "data" / "status.md").exists()
    argv(monkeypatch, "--config", write_cfg(tmp_path), "--write")
    assert status.main() == 0
    printed = capsys.readouterr().out
    saved = (tmp_path / "data" / "status.md").read_text(encoding="utf-8")
    assert "## Go-live gates" in saved and saved.strip() == printed.strip()


# ==== scripts/export_forecasts.py ===================================================================================

COLUMNS = ["forecast_utc", "market", "question", "category", "event", "closes_utc", "model", "p_yes", "runs", "confidence",
           "rules_clear", "flags", "market_mid", "gap", "decision", "reason", "resolved_yes"]


def export(tmp_path, monkeypatch, db):
    out = tmp_path / "out.csv"
    argv(monkeypatch, "--db", db, "--out", out)
    assert export_forecasts.main() == 0
    with open(out, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def test_export_writes_one_row_per_forecast_with_its_latest_decision_and_outcome(tmp_path, monkeypatch, capsys):
    t0 = 1_800_000_000.0
    led = Ledger(tmp_path / "pmt.db")
    led.upsert_market({"market_id": "A", "question": "Q" * 200, "category": "Economics", "event_id": "EA", "end_ts": t0 + 86400})
    led.upsert_market({"market_id": "B", "question": "Will B?", "category": "Politics", "event_id": "EB"})
    fa = led.add_forecast({"market_id": "A", "ts": t0, "model": "claude-opus-5-5", "p_yes": 0.62, "p_runs": [0.6, 0.62, 0.65],
                           "confidence": "medium", "rules_clear": True, "flags": ["x", "y"], "market_mid": 0.49})
    led.add_forecast({"market_id": "B", "ts": t0 + 60, "model": "m", "p_yes": 0.30, "confidence": "low",
                      "rules_clear": False, "market_mid": None})
    led.add_decision({"ts": t0, "market_id": "A", "forecast_id": fa, "action": "SKIP", "reason": "first look"})
    led.add_decision({"ts": t0 + 1, "market_id": "A", "forecast_id": fa, "action": "BUY_YES", "reason": "r" * 300})
    led.settle("B", 0.0, ts=t0 + 7200)
    led.close()

    rows = export(tmp_path, monkeypatch, tmp_path / "pmt.db")
    assert "2 forecasts -> " in capsys.readouterr().out
    assert rows[0] == COLUMNS and len(rows) == 3
    a, b = (dict(zip(COLUMNS, r)) for r in rows[1:])
    assert a["forecast_utc"] == "2027-01-15T08:00:00Z" and a["closes_utc"] == "2027-01-16T08:00:00Z"
    assert a["market"] == "A" and a["question"] == "Q" * 160 and a["category"] == "Economics" and a["event"] == "EA"
    assert a["model"] == "claude-opus-5-5" and a["p_yes"] == "0.62" and a["runs"] == "0.6 0.62 0.65"
    assert a["confidence"] == "medium" and a["rules_clear"] == "1" and a["flags"] == "2"
    assert a["market_mid"] == "0.49" and a["gap"] == "0.13"
    assert a["decision"] == "BUY_YES" and a["reason"] == "r" * 140      # the newest decision on that forecast
    assert a["resolved_yes"] == ""                                     # not resolved yet
    assert b["market"] == "B" and b["closes_utc"] == "" and b["runs"] == "" and b["flags"] == "0"
    assert b["market_mid"] == "" and b["gap"] == "" and b["decision"] == "" and b["reason"] == ""
    assert b["rules_clear"] == "0" and b["resolved_yes"] == "0.0"     # resolved NO is 0, not blank


def test_export_of_an_empty_ledger_is_just_the_header(tmp_path, monkeypatch, capsys):
    Ledger(tmp_path / "pmt.db").close()
    assert export(tmp_path, monkeypatch, tmp_path / "pmt.db") == [COLUMNS]
    assert "0 forecasts -> " in capsys.readouterr().out


def test_export_defaults_point_into_the_project(tmp_path, monkeypatch):
    seen = {}

    class Stop(Exception):
        pass

    def fake_ledger(path):
        seen["db"] = path
        raise Stop
    monkeypatch.setattr(export_forecasts, "Ledger", fake_ledger)
    # argparse defaults are built inside main() from ROOT, which the fixture points at tmp_path
    argv(monkeypatch)
    with pytest.raises(Stop):
        export_forecasts.main()
    assert Path(seen["db"]) == tmp_path / "data" / "pmt.db"


# ==== scripts/demo_offline.py =======================================================================================

def test_demo_runs_four_cycles_and_a_status_report_in_its_own_database(tmp_path, capsys):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "demo.db").write_bytes(b"left over from last time")   # replaced, not reused
    assert demo_offline.main() == 0
    out = capsys.readouterr().out
    for label in ("day 0: scan, forecast, place resting orders", "day 0 + 8h: prices came to the orders",
                  "day 3: prices moved toward the forecasts", "day 30: markets settle"):
        assert f"=== {label} ===" in out
    assert "# PolymarketTrader status" in out and "## Go-live gates" in out
    led = Ledger(tmp_path / "data" / "demo.db")
    try:
        assert led.deposits() == 1000.0
        assert led.market("cpi-above-3")["payout_yes"] == 1.0 and led.market("gdp-above-2")["payout_yes"] == 0.0
        assert len(led.q("SELECT * FROM runs")) == 4
        assert "nba-finals" not in {f["market_id"] for f in led.q("SELECT market_id FROM forecasts")}   # sports never asked
        assert led.q("SELECT * FROM fills WHERE side='SETTLE'")                       # positions were paid out
    finally:
        led.close()


# ==== scripts/replay_wide.py ========================================================================================

T0 = 1_800_000_000.0


def wide_account(path):
    """The four-trade account of tests/test_replay.py: A wins, B loses, C never filled, D still open."""
    led = Ledger(path)
    led.deposit(1000.0)
    for mid in "ABCD":
        led.upsert_market({"market_id": mid, "question": mid, "end_ts": T0 + 10 * 86400, "category": "Economics"})
    for k, (mid, outcome, edge, fill) in enumerate((("A", "YES", 0.10, 0.50), ("B", "NO", 0.02, 0.40),
                                                    ("C", "YES", 0.05, None), ("D", "YES", 0.06, 0.30))):
        ts = T0 + k * H
        did = led.add_decision({"ts": ts, "market_id": mid, "action": f"BUY_{outcome}", "edge": edge, "stake": 20.0})
        oid = led.add_order({"ts": ts, "market_id": mid, "token_id": f"{mid}:{outcome}", "outcome": outcome, "side": "BUY",
                             "limit_price": fill or 0.5, "usd": 20.0, "shares": 20.0 / (fill or 0.5), "status": "resting",
                             "decision_id": did})
        if fill is not None:
            led.apply_fill(oid, mid, f"{mid}:{outcome}", outcome, "BUY", fill, 20.0 / fill, ts=ts + H, order_status="filled")
    led.add_snapshot("D", 0.45, 0.47, 0.46, ts=T0 + 25 * H)
    led.settle("A", 1.0, ts=T0 + 10 * 86400)
    led.settle("B", 1.0, ts=T0 + 10 * 86400)
    led.close()
    return path


def test_replay_wide_prints_the_grid_for_each_account(tmp_path, monkeypatch, capsys):
    path = wide_account(tmp_path / "data" / "variants" / "claude_only_wide.db")
    Ledger(tmp_path / "data" / "pmt.db").close()
    argv(monkeypatch, "--account", "claude_only_wide", "--account", "not_yet", "--lines")
    assert replay_wide.main() == 0
    out = capsys.readouterr().out
    assert "== claude_only_wide: 4 orders recorded, 3 filled, 2 in markets that have settled ==" in out
    assert "not_yet: no ledger yet" in out
    names = {s.name for s in grid()}
    rows = {line[:48].strip(): line[48:].split() for line in out.splitlines() if line[:48].strip() in names}
    assert set(rows) == names                                           # one row per setting of the grid
    first = grid()[0]
    o = replay(*load(path, [tmp_path / "data" / "pmt.db"]), first)
    assert rows[first.name][:6] == [str(o.accepted), str(o.filled), str(o.settled), str(o.sold), str(o.open), f"{o.staked:.2f}"]
    assert rows[first.name][6:8] == [f"{o.pnl_settled:+.2f}", f"{o.pnl:+.2f}"]
    trade_lines = [line for line in out.splitlines() if line.startswith("     ")]
    assert len(trade_lines) == len(o.lines) > 0                         # --lines: the first setting's trades only


def test_replay_wide_defaults_to_the_three_wide_accounts(tmp_path, monkeypatch, capsys):
    argv(monkeypatch)
    assert replay_wide.main() == 0
    out = capsys.readouterr().out
    assert [line for line in out.splitlines() if line] == [f"{n}: no ledger yet" for n in replay_wide.WIDE]


def test_replay_wide_without_a_main_ledger(tmp_path, monkeypatch, capsys):
    wide_account(tmp_path / "data" / "variants" / "blend30_wide.db")
    argv(monkeypatch, "--account", "blend30_wide")
    assert replay_wide.main() == 0
    assert "== blend30_wide: 4 orders recorded" in capsys.readouterr().out


# ==== scripts/paper_loop.py: main() =================================================================================

class StopLoop(Exception):
    pass


HIT = ["A: no usable forecast (claude reported an error: Claude usage limit reached, resets 9am)"]
OK = ["Safety: PASS", "A: forecast 0.60 vs market 0.50 (medium, runs [0.6, 0.6, 0.6])"]


def add_run(db, run_id, log, models=(), started=None):
    led = Ledger(db)
    led.start_run(run_id)
    for m in models:
        led.add_forecast({"market_id": "A", "p_yes": 0.6, "run_id": run_id, "model": m})
    led.finish_run(run_id, "ok", {"log": log})
    if started is not None:
        led.db.execute("UPDATE runs SET started=? WHERE run_id=?", (started, run_id))
        led.db.commit()
    led.close()


@pytest.fixture
def loop(tmp_path, monkeypatch):
    """paper_loop.main() with fake subprocesses and a sleep that ends the loop after `sleeps` iterations."""
    st = types.SimpleNamespace(calls=[], on_cycle=None, sleeps=1, on_sleep=None, slept=[])

    def run(cmd, cwd=None):
        st.calls.append((cmd, cwd))
        if cmd[-1].endswith("run_cycle.py") or (len(cmd) > 2 and cmd[2].endswith("run_cycle.py")):
            if st.on_cycle:
                st.on_cycle()

    def sleep(s):
        st.slept.append(s)
        if st.on_sleep:
            st.on_sleep(len(st.slept))
        if len(st.slept) >= st.sleeps:
            raise StopLoop

    monkeypatch.setattr(pl, "subprocess", types.SimpleNamespace(run=run))
    monkeypatch.setattr(pl, "time", types.SimpleNamespace(time=time.time, strftime=time.strftime, gmtime=time.gmtime,
                                                          sleep=sleep))
    st.db = tmp_path / "data" / "pmt.db"
    st.state = tmp_path / "data" / "paper_loop_state.json"
    st.cfg = write_cfg(tmp_path, {"runtime": {"cycle_every_hours": 2, "cycle_max_hours": 12}, "forecaster": {"model": "opus"}})

    def go(*extra):
        argv(monkeypatch, "--config", st.cfg, "--poll", 7, *extra)
        with pytest.raises(StopLoop):
            pl.main()
    st.go = go
    return st


def scripts_called(st):
    return [Path(next(a for a in cmd if a.endswith(".py"))).name for cmd, _ in st.calls]


def test_loop_runs_the_six_steps_and_widens_after_a_limit(tmp_path, loop, capsys):
    loop.on_cycle = lambda: add_run(loop.db, "r1", HIT)
    loop.go()
    assert scripts_called(loop) == ["run_cycle.py", "run_variants.py", "run_rules.py", "export_forecasts.py",
                                    "shadow_longshot.py", "shadow_longshot.py"]
    cmds = [cmd for cmd, _ in loop.calls]
    assert all(c[-2:] == ["--config", str(loop.cfg)] for c in cmds[:3])
    assert all("--config" not in c for c in cmds[3:])
    assert cmds[5][-2:] == ["--band", "ent"] and "--band" not in cmds[4]
    assert cmds[0][:2] == [sys.executable, "-u"]
    assert all(cwd == str(tmp_path) for _, cwd in loop.calls)
    assert all(str(tmp_path / "scripts") in " ".join(c) for c in cmds)
    out = capsys.readouterr().out
    assert "paper loop started: a cycle every 2 h (configured 2 h, widest 12 h)" in out
    assert "next cycle in 4 h instead of 2 h: the forecaster hit a limit" in out
    saved = json.loads(loop.state.read_text(encoding="utf-8"))
    assert saved["every_hours"] == 4 and "limit" in saved["why"] and saved["set"].endswith("UTC")
    assert loop.slept == [7.0]


def test_loop_waits_while_the_last_cycle_is_recent(tmp_path, loop, capsys):
    add_run(loop.db, "r0", OK, ["claude-opus-5-5"])                    # started a moment ago
    loop.state.write_text(json.dumps({"every_hours": 8}), encoding="utf-8")
    loop.go()
    assert loop.calls == []
    assert "a cycle every 8 h (configured 2 h, widest 12 h)" in capsys.readouterr().out
    assert json.loads(loop.state.read_text(encoding="utf-8")) == {"every_hours": 8}    # untouched


def test_loop_narrows_again_when_forecasts_come_through(tmp_path, loop, capsys):
    add_run(loop.db, "r0", HIT, started=time.time() - 9 * H)
    loop.state.write_text(json.dumps({"every_hours": 8}), encoding="utf-8")
    loop.on_cycle = lambda: add_run(loop.db, "r1", OK, ["claude-opus-5-5"])
    loop.go()
    assert "next cycle in 4 h instead of 8 h: forecasts are coming through again" in capsys.readouterr().out
    assert json.loads(loop.state.read_text(encoding="utf-8"))["every_hours"] == 4


def test_a_skipped_cycle_decides_nothing(tmp_path, loop, capsys):
    add_run(loop.db, "r0", OK, ["claude-opus-5-5"], started=time.time() - 3 * H)
    loop.on_cycle = None                                               # the cycle exits 3: no new run row
    loop.go()
    assert scripts_called(loop)[0] == "run_cycle.py" and len(loop.calls) == 6
    assert not loop.state.exists() and "next cycle in" not in capsys.readouterr().out


def test_every_argument_and_an_unreadable_config_mid_loop(tmp_path, loop, capsys):
    add_run(loop.db, "r0", OK, ["claude-opus-5-5"])
    loop.sleeps = 2
    loop.on_sleep = lambda n: loop.cfg.write_text("runtime: [half saved", encoding="utf-8") if n == 1 else None
    loop.go("--every", 3)
    out = capsys.readouterr().out
    assert "a cycle every 3 h (configured 3 h, widest 12 h)" in out
    assert "config not readable (" in out and "keeping 3 h" in out
    assert loop.calls == []


def test_last_run_helpers_on_broken_or_missing_ledgers(tmp_path):
    assert pl.last_run_started(tmp_path / "nowhere" / "pmt.db") == 0.0
    assert pl.last_run(tmp_path / "nowhere" / "pmt.db") == {}
    db = tmp_path / "pmt.db"
    led = Ledger(db)
    led.start_run("r1")
    led.db.execute("UPDATE runs SET summary='not json' WHERE run_id='r1'")
    led.db.commit()
    led.close()
    assert pl.last_run(db) == {}                                       # a garbled summary is no evidence
    assert pl.last_run_started(db) > 0


def test_settings_defaults_and_next_gap_edges(tmp_path):
    cfg = tmp_path / "bare.yaml"
    cfg.write_text("account: {mode: paper}\n", encoding="utf-8")
    assert pl.settings(str(cfg), None) == (6.0, 12.0, None)
    cfg.write_text("", encoding="utf-8")
    assert pl.settings(str(cfg), 0) == (6.0, 12.0, None)               # --every 0 means "not given"
    assert pl.load_gap(tmp_path / "missing.json", 2, 12) == 2
    st = tmp_path / "s.json"
    st.write_text(json.dumps({"every_hours": 0.5}), encoding="utf-8")
    assert pl.load_gap(st, 2, 12) == 2                                  # never under the base
    st.write_text(json.dumps({"other": 1}), encoding="utf-8")
    assert pl.load_gap(st, 2, 12) == 2
    st.write_text(json.dumps({"every_hours": None}), encoding="utf-8")
    assert pl.load_gap(st, 2, 12) == 2
    # a gap already above the ceiling is clamped before doubling; a limit wins over a fallback model
    gap, why = pl.next_gap(40, 2, 12, {"log": HIT, "models": ["claude-sonnet-5-5"]}, "opus")
    assert gap == 12 and "limit" in why
    long = ["B: forecaster failed (" + "x" * 300 + ")"]
    gap, why = pl.next_gap(2, 2, 12, {"log": long, "models": []}, "opus")
    assert gap == 4 and len(why) < 160                                  # the reason is cut short
    assert pl.next_gap(2, 2, 12, {"log": None, "models": None}, "opus") == (2, "")
    assert pl.next_gap(4, 2, 12, {"log": OK, "models": ["CLAUDE-OPUS-5-5"]}, "Opus")[0] == 2   # case does not matter
