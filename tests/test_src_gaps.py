"""Error and edge paths of src/ that the other test files do not reach: what happens when the exchange, the
forecaster or the machine misbehaves, and the corners of the record keeping. Everything is offline: the venue is
the fake exchange (or a stub), the `claude` process is a fake Popen, the Anthropic SDK is a fake module, and the
HTTP transport is a scripted object. Nothing here touches data/ or the network."""
import ctypes
import dataclasses
import io
import json
import math
import os
import sqlite3
import subprocess
import sys
import types
from types import SimpleNamespace

import pytest

from fakes import FakeExchange, FakeKalshiHTTP, iso
from test_trader import run as cycle, setup as trader_setup
from src import forecast as fc
from src import kalshi_http as kh
from src import runtime, safety, scoring, universe
from src.book import Book, simulate_sell, summarize
from src.broker import LiveBroker, PaperBroker
from src.fees import FeeModel
from src.kalshi import Kalshi
from src.kalshi_http import KalshiError, KalshiHTTP
from src.ledger import Ledger
from src.replay import Outcome, Settings, Trade, follow
from src.sizing import Exposure, SizingRules, plan_entry
from src.variants import SharedVenue, load_variants, run_variants, standings
from src.venue import Market, PolymarketUS, parse_time

NOW = 1_800_000_000.0
H = 3600.0
DAY = 86400.0
SLUG = "cpi-above-3"


def boom(*_a, **_k):
    raise RuntimeError("gateway timeout")


def quiet_cycle(tr, now):
    """A cycle that marks, exits and records but asks for no new forecast."""
    tr._books.clear()
    tr._markets.clear()
    tr.venue.clock = lambda: now
    return tr.run(now=now, do_forecast=False)


def said(res, text):
    return any(text in line for line in res.log)


# =====================================================================================================
# trader.py: a failure in one market never stops the cycle, and never moves money by accident
# =====================================================================================================

def test_book_failure_on_a_held_market_holds_it_and_values_it_at_its_last_snapshot(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.75}, execution={"style": "taker"})
    cycle(tr)
    pos = ledger.positions()[0]
    tr.venue.books = boom
    r = cycle(tr, NOW + 2 * H)
    assert r.status == "ok"
    assert said(r, f"{SLUG}: order book unavailable (RuntimeError: gateway timeout)")
    assert len(ledger.positions()) == 1                                  # no book: no exit, no panic sale
    assert ledger.q("SELECT * FROM orders WHERE side='SELL'") == []
    assert r.stats["equity"] == pytest.approx(ledger.cash() + pos["shares"] * 0.48)   # last recorded bid, not zero


def test_no_position_without_a_book_is_marked_from_the_mirrored_yes_snapshot(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.25}, execution={"style": "taker"})
    cycle(tr)
    pos = ledger.positions()[0]
    assert pos["outcome"] == "NO"
    tr._books.clear()
    bid, mid = tr._marks()[pos["token_id"]]
    assert bid == pytest.approx(1 - 0.50) and mid == pytest.approx(1 - 0.49)       # NO bid = 1 - YES ask
    ledger.db.execute("DELETE FROM snapshots")
    ledger.db.commit()
    assert tr._marks() == {}                                                       # nothing known: no mark at all
    eq = ledger.record_equity(tr._marks(), ts=NOW + 1)
    assert eq["positions_bid"] == 0.0 and eq["positions_mid"] == pytest.approx(pos["cost"])


def test_market_detail_failure_is_logged_and_the_market_is_not_forecast_blind(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.75}, execution={"style": "taker"})
    cycle(tr)
    tr.venue.market = boom                          # PolymarketUS.enrich goes through market() too
    r = cycle(tr, NOW + 49 * H)                     # due for a new forecast
    assert r.status == "ok"
    assert said(r, f"{SLUG}: market detail unavailable (RuntimeError")
    assert said(r, f"{SLUG}: detail unavailable (RuntimeError)")
    assert f.asked == [SLUG]                        # never forecast without the rules text
    assert len(ledger.positions()) == 1


def test_resolution_lookups_wait_until_due_and_a_failed_lookup_is_retried(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.52}, execution={"track_forecasts_days": 0},
                             universe={"reforecast_after_hours": 1000})
    cycle(tr)                                       # forecast, no trade, then no longer tracked
    calls = []
    tr.venue.is_closed = lambda mid: calls.append(mid) or False
    cycle(tr, NOW + 10 * H)
    assert calls == []                              # looked at 10 h ago: not due

    def failing(mid):
        calls.append(mid)
        raise RuntimeError("503")
    tr.venue.is_closed = failing
    r = cycle(tr, NOW + 80 * H)
    assert calls == [SLUG] and said(r, f"{SLUG}: resolution check failed (RuntimeError: 503)")
    assert ledger.market(SLUG)["checked_ts"] is None                    # a failed look is not a look

    tr.venue.is_closed = lambda mid: calls.append(mid) or False
    cycle(tr, NOW + 81 * H)
    assert calls == [SLUG, SLUG] and ledger.market(SLUG)["checked_ts"] == NOW + 81 * H
    cycle(tr, NOW + 82 * H)
    assert len(calls) == 2


def test_settlement_lookup_failure_leaves_the_position_alone(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.75}, execution={"style": "taker"})
    cycle(tr)
    cash = ledger.cash()
    ex.close(SLUG, settlement=1.0)
    tr.venue.settlement = boom
    r = cycle(tr, NOW + 30 * 24 * H)
    assert said(r, f"{SLUG}: closed, settlement unavailable (RuntimeError")
    assert len(ledger.positions()) == 1 and ledger.cash() == pytest.approx(cash)
    assert ledger.market(SLUG)["payout_yes"] is None


def test_take_profit_gain_is_measured_from_the_price_paid_including_the_fee(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.75}, execution={"style": "taker", "take_profit_gain": 0.08})
    cycle(tr)
    p = ledger.positions()[0]
    paid = p["cost"] / p["shares"]
    assert paid == pytest.approx(0.50 + 0.095 * 0.25, abs=1e-3)
    ex.set_book(SLUG, 0.58, 0.60)                   # +0.056 over what was paid: not enough
    cycle(tr, NOW + 8 * H)
    assert len(ledger.positions()) == 1
    ex.set_book(SLUG, 0.61, 0.63)
    r = cycle(tr, NOW + 9 * H)
    assert ledger.positions() == []
    reason = ledger.one("SELECT reason FROM decisions WHERE action='SELL'")["reason"]
    assert reason.startswith("take profit: bid 0.610") and f"over the {paid:.3f} paid" in reason
    assert said(r, "SELL")


def test_time_exit_falls_back_to_the_ledger_end_date_when_the_detail_is_missing(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.75}, execution={"style": "taker", "sell_days_before_end": 3})
    cycle(tr)
    tr.venue.market = lambda slug: None             # the venue no longer returns the market's detail
    r = quiet_cycle(tr, NOW + 17.5 * DAY)
    assert ledger.positions() == [] and said(r, "time exit: 2.5 days to the scheduled end")


def test_listing_failure_means_no_forecasts_but_the_cycle_finishes(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.75})
    tr.venue.list_markets = boom
    r = cycle(tr)
    assert r.status == "ok" and f.asked == [] and ledger.q("SELECT * FROM orders") == []
    assert said(r, "market listing failed (RuntimeError: gateway timeout): no new forecasts this cycle")
    assert ledger.one("SELECT status FROM runs")["status"] == "ok"


def test_candidate_whose_book_cannot_be_read_is_not_forecast(ledger, tmp_path):
    ex = FakeExchange(NOW).add("broken-book").add(SLUG)
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.52, "broken-book": 0.52}, ex=ex)
    real = tr.venue.books
    tr.venue.books = lambda slug: boom() if slug == "broken-book" else real(slug)
    r = cycle(tr)
    assert f.asked == [SLUG] and said(r, "broken-book: order book unavailable")
    assert r.stats["candidates_with_books"] == 1


def test_rate_limited_exchange_stops_reading_new_order_books(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.75})
    tr.venue.rate_limited = 3
    r = cycle(tr)
    assert said(r, "the exchange is rate limiting: no more order books this cycle")
    assert f.asked == [] and "markets.book:" + SLUG not in ex.calls


def test_market_found_closed_in_its_detail_is_not_forecast(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.75})
    real = tr.venue.enrich
    tr.venue.enrich = lambda m: dataclasses.replace(real(m), closed=True)
    r = cycle(tr)
    assert f.asked == [] and said(r, "not considered: 1 closed")


def test_forecaster_exception_is_logged_and_the_heartbeat_still_beats(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.75}, on_call=boom)
    beats = []
    tr.heartbeat = lambda: beats.append(1)
    r = cycle(tr)
    assert r.status == "ok" and said(r, f"{SLUG}: forecaster failed (RuntimeError: gateway timeout)")
    assert beats == [1]                             # the run lock is refreshed even when the forecaster dies
    assert ledger.q("SELECT * FROM forecasts") == [] and ledger.q("SELECT * FROM orders") == []


def test_passive_price_on_a_one_sided_book_is_none(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {})
    yes = Book.from_levels("m:YES", [(0.48, 100)], [])
    no = Book.from_levels("m:NO", [], [(0.52, 100)])
    assert tr._entry_prices(yes, no, Market("m", "q?")) == (None, None, 0.0, 0.0)


def test_a_new_forecast_replaces_the_resting_order(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.70}, universe={"reforecast_after_hours": 1})
    cycle(tr)
    cycle(tr, NOW + 2 * H)
    o = ledger.q("SELECT * FROM orders ORDER BY id")
    assert f.asked == [SLUG, SLUG]
    assert len(o) == 2 and o[0]["status"] == "cancelled" and o[0]["note"] == "replaced by a newer forecast"
    assert o[1]["status"] == "resting"
    assert ledger.cash() == pytest.approx(1000.0)


def test_book_emptied_during_the_forecast_blocks_the_order(ledger, tmp_path):
    ex = FakeExchange(NOW).add(SLUG)
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.70}, ex=ex,
                             on_call=lambda m: ex._books[SLUG]["marketData"].__setitem__("offers", []))
    cycle(tr)
    assert ledger.q("SELECT * FROM orders") == []
    d = ledger.q("SELECT * FROM decisions")
    assert len(d) == 1 and d[0]["action"] == "SKIP" and d[0]["reason"] == "no two-sided market after the forecast"
    assert len(ledger.q("SELECT * FROM forecasts")) == 1                  # still scored


def test_too_little_depth_for_the_minimum_order_is_a_skip(ledger, tmp_path):
    ex = FakeExchange(NOW).add("m", size=10)         # $14.20 near the price on the thinner side
    ex, f, tr = trader_setup(ledger, tmp_path, {"m": 0.70}, ex=ex, universe={"trade_min_depth_usd": 10})
    cycle(tr)
    assert ledger.q("SELECT * FROM orders") == []
    reason = ledger.one("SELECT reason FROM decisions")["reason"]
    assert reason == "only $3.55 of depth to trade against (minimum order $5.00)"


def test_account_stop_cancels_resting_orders(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.70})
    cycle(tr)
    assert ledger.one("SELECT status FROM orders")["status"] == "resting"
    ledger.deposit(-500.0, "withdrawal")            # equity halves between cycles
    r = cycle(tr, NOW + 4 * H)
    assert r.status == "stopped"
    o = ledger.one("SELECT * FROM orders")
    assert o["status"] == "cancelled" and o["note"] == "account safety stop"
    assert ledger.positions() == [] and f.asked == [SLUG]


def test_resting_order_counts_as_exposure_in_its_own_market_event_and_category(ledger, tmp_path):
    ex, f, tr = trader_setup(ledger, tmp_path, {SLUG: 0.70})
    cycle(tr)
    usd = ledger.one("SELECT usd FROM orders")["usd"]
    e = tr._exposure(tr._markets[SLUG], 1000.0)
    assert (e.market, e.event, e.category, e.total) == pytest.approx((usd, usd, usd, usd))
    assert e.cash == pytest.approx(1000.0 - usd)


# =====================================================================================================
# forecast.py: the claude process and the API, faked
# =====================================================================================================

def fmarket(**kw):
    base = dict(market_id=SLUG, question="Will CPI inflation be above 3.0%?", rules="Resolves per bls.gov.",
                event_title="January CPI", category="economics", end_ts=NOW + 20 * DAY, outcome="Yes")
    return Market(**{**base, **kw})


def answer(p=0.6, **kw):
    base = {"resolution_summary": "YES if BLS prints above 3.0%", "rules_clear": True, "base_rate": "about 40%",
            "key_facts": ["Dec CPI 2.9%"], "case_for_yes": "energy", "case_for_no": "shelter", "p_yes": p,
            "confidence": "medium", "caveats": [], "flags": [], "sources": ["https://www.bls.gov/cpi/"]}
    return {**base, **kw}


def claude_json(ans=None, cost=0.1, models=None, **kw):
    out = {"is_error": False, "total_cost_usd": cost, "result": "", **kw}
    if ans is not None:
        out["structured_output"] = ans
    if models:
        out["modelUsage"] = {m: {} for m in models}
    return json.dumps(out)


def fake_popen(monkeypatch, replies):
    """Replace subprocess.Popen: each process started answers with the next (returncode, stdout, stderr)."""
    replies, started = list(replies), []

    class P:
        pid = 4242

        def __init__(self, cmd, **kw):
            started.append((cmd, kw))
            self.reply, self.returncode = replies.pop(0), None

        def communicate(self, input=None, timeout=None):
            self.returncode, out, err = self.reply
            return out, err
    monkeypatch.setattr(fc.subprocess, "Popen", P)
    return started


def backend(tmp_path, **kw):
    return fc.ClaudeCodeBackend(cwd=tmp_path / "cwd", executable="claude-not-run", timeout_s=5, **kw)


def test_command_carries_the_budget_cap(tmp_path):
    cmd = backend(tmp_path, max_budget_usd=2.5).command()
    assert cmd[cmd.index("--max-budget-usd") + 1] == "2.5"
    assert "--max-budget-usd" not in backend(tmp_path).command()


def test_answer_without_structured_output_is_dropped_with_a_reason(tmp_path, monkeypatch):
    fake_popen(monkeypatch, [(0, claude_json(result="I estimate 60%"), "")] * 2)
    be = backend(tmp_path, runs=2)
    assert be.forecast(fmarket(), NOW) is None
    assert be.last_error == "claude answered without the required structured output"


BAD_ANSWERS = [answer(1.5), {k: v for k, v in answer().items() if k != "sources"}]


def test_runs_that_all_fail_validation_give_no_forecast_and_a_reason(tmp_path, monkeypatch):
    fake_popen(monkeypatch, [(0, claude_json(a), "") for a in BAD_ANSWERS])
    be = backend(tmp_path, runs=2)
    assert be.forecast(fmarket(), NOW) is None
    assert be.last_error.startswith("only ") and be.last_error.endswith(" of 2 runs gave a valid answer")


def test_runs_that_all_fail_validation_say_none_were_valid(tmp_path, monkeypatch):
    fake_popen(monkeypatch, [(0, claude_json(a), "") for a in BAD_ANSWERS])
    be = backend(tmp_path, runs=2)
    assert be.forecast(fmarket(), NOW) is None
    assert be.last_error == "only 0 of 2 runs gave a valid answer"


def test_one_malformed_run_of_three_is_dropped_and_a_fallback_model_is_recorded(tmp_path, monkeypatch):
    fake_popen(monkeypatch, [(0, claude_json(answer(0.60), cost=0.1, models=["claude-opus-x"]), ""),
                             (0, claude_json(answer(0.9, confidence="certain"), cost=0.2, models=["claude-opus-x"]), ""),
                             (0, claude_json(answer(0.62), cost=0.3, models=["claude-sonnet-fallback"]), "")])
    be = backend(tmp_path, runs=3)
    f = be.forecast(fmarket(), NOW)
    assert f.p_runs == [0.60, 0.62] and f.p_yes == pytest.approx(0.61)
    assert f.cost_usd == pytest.approx(0.6)                              # the malformed run was still paid for
    assert f.model == "claude-opus-x,claude-sonnet-fallback"            # every model that answered, not the alias


def test_model_name_falls_back_to_the_alias_then_to_default(tmp_path, monkeypatch):
    fake_popen(monkeypatch, [(0, claude_json(answer(0.6)), "")] * 4)
    assert backend(tmp_path, runs=2).forecast(fmarket(), NOW).model == "opus"
    assert backend(tmp_path, runs=2, model=None).forecast(fmarket(), NOW).model == "default"


@pytest.mark.parametrize("stdout", ["null", "[]"])
def test_non_object_json_from_claude_is_a_failed_run_not_a_crash(tmp_path, monkeypatch, stdout):
    fake_popen(monkeypatch, [(0, stdout, "")])
    be = backend(tmp_path, runs=1)
    assert be.forecast(fmarket(), NOW) is None and "JSON" in be.last_error


class HungProc:
    """A claude process that never answers, and whose second wait times out too."""
    pid = 4242

    def __init__(self, cmd, **kw):
        HungProc.started = kw
        self.killed = False
        HungProc.last = self

    def communicate(self, input=None, timeout=None):
        raise subprocess.TimeoutExpired("claude", timeout)

    def kill(self):
        self.killed = True


def test_hung_claude_on_posix_kills_the_process_group_and_falls_back_to_kill(tmp_path, monkeypatch):
    killpg = []

    def fake_killpg(pid, sig):
        killpg.append((pid, sig))
        raise ProcessLookupError("already gone")
    monkeypatch.setattr(fc, "os", SimpleNamespace(name="posix", environ=dict(os.environ), killpg=fake_killpg))
    monkeypatch.setattr(fc, "signal", SimpleNamespace(SIGKILL=9))
    monkeypatch.setattr(fc.subprocess, "Popen", HungProc)
    be = backend(tmp_path, runs=1)
    assert be.forecast(fmarket(), NOW) is None
    assert be.last_error == "claude timed out after 5 s"
    assert HungProc.started.get("start_new_session") is True
    assert killpg == [(4242, 9)] and HungProc.last.killed


def test_hung_claude_on_windows_kills_the_whole_tree(tmp_path, monkeypatch):
    ran = []
    monkeypatch.setattr(fc, "os", SimpleNamespace(name="nt", environ=dict(os.environ)))
    monkeypatch.setattr(fc.subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200, raising=False)
    monkeypatch.setattr(fc.subprocess, "Popen", HungProc)
    monkeypatch.setattr(fc.subprocess, "run", lambda args, **kw: ran.append(args))
    be = backend(tmp_path, runs=1)
    assert be.forecast(fmarket(), NOW) is None and "timed out" in be.last_error
    assert ran == [["taskkill", "/T", "/F", "/PID", "4242"]]
    assert HungProc.started.get("creationflags") == 0x200


# ---- the API backend, with a fake `anthropic` module (the SDK is not installed) ----------------------

@pytest.fixture
def fake_sdk(monkeypatch):
    mod = types.ModuleType("anthropic")

    class APIStatusError(Exception):
        pass

    class RateLimitError(APIStatusError):
        pass

    class APIConnectionError(Exception):
        pass
    mod.APIStatusError, mod.RateLimitError, mod.APIConnectionError = APIStatusError, RateLimitError, APIConnectionError
    mod.Anthropic = lambda: "client-made-by-sdk"
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    return mod


def resp(stop, *texts, extra=()):
    blocks = [SimpleNamespace(type=t, text="ignored") for t in extra] + [SimpleNamespace(type="text", text=t) for t in texts]
    return SimpleNamespace(stop_reason=stop, content=blocks)


class FakeMessages:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def create(self, **kw):
        self.calls.append(kw)
        r = self.replies.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


def api(replies, runs=3):
    msgs = FakeMessages(replies)
    return fc.ApiBackend(runs=runs, max_searches=4, client=SimpleNamespace(beta=SimpleNamespace(messages=msgs))), msgs


def test_api_backend_resumes_paused_research_and_skips_unusable_runs(fake_sdk):
    be, msgs = api([resp("pause_turn", "half", extra=["server_tool_use"]), resp("end_turn", "MEMO TEXT"),
                    resp("refusal"), resp("max_tokens", "{\"p_yes\""), resp("end_turn", "not json"),
                    resp("end_turn", json.dumps(answer(0.60))), resp("end_turn", json.dumps(answer(0.64)))], runs=5)
    f = be.forecast(fmarket(), NOW)
    assert f.p_runs == [0.60, 0.64] and f.p_yes == pytest.approx(0.62) and f.backend == "api" and f.model == "claude-opus-5-5"
    research, resumed, first_run = msgs.calls[0], msgs.calls[1], msgs.calls[2]
    assert research["tools"][0]["max_uses"] == 4 and research["fallbacks"] == "default"
    assert resumed["messages"][-1]["role"] == "assistant"               # the paused turn is handed back
    assert "<research>\nMEMO TEXT\n</research>" in first_run["messages"][0]["content"]
    assert first_run["output_config"]["format"]["type"] == "json_schema"
    assert len(msgs.calls) == 7


def test_api_backend_refused_research_is_no_forecast(fake_sdk):
    be, msgs = api([resp("refusal")])
    assert be.forecast(fmarket(), NOW) is None and len(msgs.calls) == 1


@pytest.mark.parametrize("err", ["RateLimitError", "APIStatusError", "APIConnectionError"])
def test_api_backend_errors_skip_the_market(fake_sdk, err):
    be, msgs = api([resp("end_turn", "memo"), resp("end_turn", json.dumps(answer(0.6))), getattr(fake_sdk, err)("x")])
    assert be.forecast(fmarket(), NOW) is None


def test_api_backend_gives_up_resuming_after_four_requests(fake_sdk):
    be, msgs = api([resp("pause_turn", "x")] * 6)
    r = be._create([{"role": "user", "content": "q"}])
    assert r.stop_reason == "pause_turn" and len(msgs.calls) == 4
    assert len(msgs.calls[-1]["messages"]) == 4                         # user + three handed-back turns


def test_api_client_is_made_once_from_the_sdk(fake_sdk):
    be = fc.ApiBackend()
    assert be.client == "client-made-by-sdk" and be.client is be._client


def test_make_backend_api_with_credentials_in_the_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "test-placeholder-not-a-token")
    be = fc.make_backend({"forecaster": {"backend": "api", "api_model": "claude-test", "runs": 2, "max_searches": 3}}, tmp_path)
    assert isinstance(be, fc.ApiBackend) and (be.model, be.runs, be.max_searches) == ("claude-test", 2, 3)


def test_file_backend_consumes_a_corrupt_answer_without_crashing(tmp_path):
    be = fc.FileBackend(tmp_path)
    path = tmp_path / "forecasts" / f"{SLUG}.json"
    path.write_text("{not json")
    os.utime(path, (NOW, NOW))
    assert be.forecast(fmarket(), NOW + 60) is None
    assert not path.exists() and (tmp_path / "forecasts" / f"{SLUG}.{int(NOW + 60)}.used").exists()
    path.write_text(json.dumps([answer(0.60), answer(0.70)]))             # several runs in one file
    os.utime(path, (NOW, NOW))
    assert be.forecast(fmarket(), NOW + 120).p_yes == pytest.approx(0.65)


# =====================================================================================================
# runtime.py: priority, free memory, the lock
# =====================================================================================================

class FakeKernel32:
    def __init__(self, avail_gb=None, fail=False):
        self.avail_gb, self.fail, self.calls = avail_gb, fail, []

    def GetCurrentProcess(self):
        return 777

    def SetPriorityClass(self, handle, cls):
        if self.fail:
            raise OSError("access denied")
        self.calls.append((handle, cls))
        return 1

    def GlobalMemoryStatusEx(self, ref):
        if self.avail_gb is None:
            return 0
        ref._obj.ullAvailPhys = int(self.avail_gb * 2 ** 30)
        return 1


def on_windows(monkeypatch, k32):
    monkeypatch.setattr(runtime, "sys", SimpleNamespace(platform="win32"))
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(kernel32=k32), raising=False)


def test_lower_priority_on_windows_asks_for_below_normal(monkeypatch):
    k = FakeKernel32()
    on_windows(monkeypatch, k)
    runtime.lower_priority()
    assert k.calls == [(777, 0x00004000)]
    on_windows(monkeypatch, FakeKernel32(fail=True))
    runtime.lower_priority()                                             # best effort: never an error


def test_lower_priority_elsewhere_uses_nice_and_swallows_errors(monkeypatch):
    niced = []
    monkeypatch.setattr(runtime, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(runtime.os, "nice", lambda n: niced.append(n), raising=False)
    runtime.lower_priority()
    assert niced == [10]

    def denied(n):
        raise PermissionError("no")
    monkeypatch.setattr(runtime.os, "nice", denied, raising=False)
    runtime.lower_priority()


def test_free_memory_on_windows(monkeypatch):
    on_windows(monkeypatch, FakeKernel32(avail_gb=6.5))
    assert runtime.free_memory_gb() == pytest.approx(6.5)
    on_windows(monkeypatch, FakeKernel32(avail_gb=None))                 # the call failed
    assert runtime.free_memory_gb() is None


def test_free_memory_from_proc_meminfo(monkeypatch):
    monkeypatch.setattr(runtime, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(runtime, "open", lambda *a, **k: io.StringIO("MemTotal: 16 kB\nMemAvailable:  8388608 kB\n"),
                        raising=False)
    assert runtime.free_memory_gb() == pytest.approx(8.0)
    monkeypatch.setattr(runtime, "open", lambda *a, **k: io.StringIO("MemTotal: 16 kB\n"), raising=False)
    assert runtime.free_memory_gb() is None                              # no MemAvailable line

    def missing(*a, **k):
        raise FileNotFoundError("/proc/meminfo")
    monkeypatch.setattr(runtime, "open", missing, raising=False)
    assert runtime.free_memory_gb() is None


def test_preflight_low_priority_can_be_switched_off(monkeypatch, tmp_path):
    lowered = []
    monkeypatch.setattr(runtime, "lower_priority", lambda: lowered.append(1))
    monkeypatch.setattr(runtime, "free_memory_gb", lambda: 8.0)
    runtime.preflight({"runtime": {"min_free_gb": 1.5, "low_priority": False, "quiet_windows": []}}, tmp_path)
    assert lowered == []
    runtime.preflight({"runtime": {"min_free_gb": 1.5}}, tmp_path)
    runtime.preflight(None, tmp_path)
    assert lowered == [1, 1]


def test_lock_survives_its_file_vanishing(tmp_path):
    path = tmp_path / "cycle.lock"
    lock = runtime.Lock(path)
    lock.__enter__()
    path.unlink()                                                        # someone cleaned up data/
    assert not lock.ours()
    lock.touch()
    assert not path.exists()                                             # touch never recreates a lock
    assert lock.__exit__(None, None, None) is False


def test_lock_touch_and_release_errors_are_swallowed(tmp_path, monkeypatch):
    path = tmp_path / "cycle.lock"
    lock = runtime.Lock(path)
    lock.__enter__()

    def denied(*a, **k):
        raise PermissionError("file in use")
    monkeypatch.setattr(runtime.os, "utime", denied)
    lock.touch()
    monkeypatch.setattr(type(path), "unlink", denied)
    assert lock.__exit__(None, None, None) is False
    monkeypatch.undo()
    assert path.exists()                                                 # left behind; it goes stale in time


# =====================================================================================================
# kalshi_http.py: pacing, backoff and rate limits, with a scripted transport
# =====================================================================================================

class Resp:
    def __init__(self, status, body=None, headers=None, text=""):
        self.status_code, self.body, self.headers, self.text = status, body, headers or {}, text

    def json(self):
        return self.body


class Transport:
    def __init__(self, *replies):
        self.replies, self.seen = list(replies), []

    def get(self, url, params=None):
        self.seen.append((url, params))
        r = self.replies.pop(0)
        if isinstance(r, BaseException):
            raise r
        return r


@pytest.fixture
def sleeps(monkeypatch):
    out = []
    monkeypatch.setattr(kh.time, "sleep", out.append)
    return out


def backoffs(sleeps):
    return [s for s in sleeps if s >= 1.0]          # pacing sleeps are fractions of a second


def test_connection_errors_are_retried_with_growing_pauses(sleeps):
    t = Transport(TimeoutError("read timeout"), ConnectionResetError("reset"), Resp(200, {"ok": 1}))
    h = KalshiHTTP(min_interval=0, client=t)
    assert h.get("/markets", ticker="A", cursor=None) == {"ok": 1}
    assert backoffs(sleeps) == [5.0, 15.0] and h.requests == 3
    assert t.seen[0][1] == {"ticker": "A"}                               # None parameters are not sent


def test_connection_error_on_the_last_try_is_raised(sleeps):
    h = KalshiHTTP(min_interval=0, client=Transport(TimeoutError("t1"), TimeoutError("t2")))
    with pytest.raises(TimeoutError, match="t2"):
        h.get("/markets", tries=2)
    assert backoffs(sleeps) == [5.0]


def test_retry_after_is_honoured_bad_values_ignored_and_waits_capped(sleeps):
    t = Transport(Resp(429, headers={"Retry-After": "soon"}), Resp(503, headers={"Retry-After": "2"}),
                  Resp(429, headers={"Retry-After": "500"}), Resp(200, {"done": True}))
    h = KalshiHTTP(min_interval=0, client=t, max_wait=90)
    assert h.get("/markets") == {"done": True}
    assert backoffs(sleeps) == [5.0, 2.0, 90.0]
    assert h.rate_limited == 2                                           # the 503 is not a rate limit
    assert h.min_interval == pytest.approx((0 * 1.5 + 0.05) * 1.5 + 0.05)


def test_rate_limit_on_the_last_try_raises_with_its_status(sleeps):
    h = KalshiHTTP(min_interval=2.9, client=Transport(Resp(429, text="slow   down"), Resp(429, text="slow down")))
    with pytest.raises(KalshiError) as e:
        h.get("/markets", tries=2)
    assert e.value.status_code == 429 and "Kalshi 429 on /markets: slow down" in str(e.value)
    assert h.min_interval == 3.0                                         # slowed down, but never past 3 s


def test_client_errors_are_not_retried_and_zero_tries_gives_up(sleeps):
    t = Transport(Resp(404, text="not found"))
    with pytest.raises(KalshiError) as e:
        KalshiHTTP(min_interval=0, client=t).get("/markets/X")
    assert e.value.status_code == 404 and len(t.seen) == 1 and backoffs(sleeps) == []
    with pytest.raises(KalshiError) as e:
        KalshiHTTP(min_interval=0, client=Transport()).get("/markets", tries=0)
    assert e.value.status_code == 599


def test_speed_is_earned_back_after_forty_successes(sleeps):
    h = KalshiHTTP(min_interval=0, client=Transport(*[Resp(200, {}) for _ in range(41)]))
    h.min_interval = 0.5                                                 # slowed by earlier refusals
    for _ in range(39):
        h.get("/x")
    assert h.min_interval == 0.5
    h.get("/x")
    assert h.min_interval == pytest.approx(0.45) and h._streak == 0


def test_default_client_is_httpx_with_our_user_agent():
    h = KalshiHTTP(user_agent="ua-under-test", timeout=3)
    try:
        assert h.client.headers["User-Agent"] == "ua-under-test"
    finally:
        h.client.close()


# =====================================================================================================
# kalshi.py: listing filters, caches that cannot be read or written, lookups that fail
# =====================================================================================================

class ListingHTTP:
    requests = rate_limited = 0

    def __init__(self, rows):
        self.rows = rows

    def get(self, path, tries=6, **params):
        if path == "/series":
            return {"series": [{"ticker": "KXCPIYOY", "fee_type": "quadratic", "fee_multiplier": 1, "tags": []}]
                    if params.get("category") == "Economics" else []}
        if path == "/markets":
            return {"markets": self.rows, "cursor": ""}
        raise KalshiError(404, path, "not found")


def test_listing_drops_non_binary_one_sided_duplicate_settled_and_past_markets():
    src = FakeKalshiHTTP(NOW)
    for t in "ABCDE":
        src.add(f"KXCPIYOY-26NOV-{t}")
    m = {k[-1]: dict(v) for k, v in src.markets.items()}
    m["B"]["market_type"] = "scalar"
    m["C"]["yes_ask_dollars"] = "1.0000"                                 # no ask
    m["D"].update(status="finalized", result="yes")
    m["E"]["close_time"] = iso(NOW - DAY)
    rows = [m["A"], m["B"], m["C"], dict(m["A"]), m["D"], m["E"]]
    got = Kalshi(http=ListingHTTP(rows), clock=lambda: NOW).list_markets(categories=["economics"], min_days=0, max_days=75)
    assert [x.market_id for x in got] == ["KXCPIYOY-26NOV-A"]


def test_corrupt_series_cache_is_refetched_and_rewritten(tmp_path):
    (tmp_path / "kalshi_series.json").write_text("{not json")
    http = FakeKalshiHTTP(NOW).add("KXCPIYOY-26NOV-T3.6")
    got = Kalshi(http=http, clock=lambda: NOW, cache_dir=tmp_path).list_markets(categories=["Economics"])
    assert len(got) == 1
    assert "economics" in json.loads((tmp_path / "kalshi_series.json").read_text())


def test_unwritable_cache_folder_does_not_stop_the_listing(tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("a file where the cache folder should be")
    http = FakeKalshiHTTP(NOW).add("KXCPIYOY-26NOV-T3.6")
    v = Kalshi(http=http, clock=lambda: NOW, cache_dir=blocker)
    assert [m.market_id for m in v.list_markets(categories=["Economics"])] == ["KXCPIYOY-26NOV-T3.6"]
    assert [m.market_id for m in v.list_markets(categories=["Economics"])] == ["KXCPIYOY-26NOV-T3.6"]
    assert blocker.read_text().startswith("a file")


class FailingKalshi(FakeKalshiHTTP):
    def __init__(self, now, fail_prefix, status=503):
        super().__init__(now)
        self.fail_prefix, self.status = fail_prefix, status

    def get(self, path, tries=6, **params):
        if path.startswith(self.fail_prefix):
            raise KalshiError(self.status, path, "unavailable")
        return super().get(path, tries=tries, **params)


def test_server_error_on_market_detail_is_raised_not_read_as_missing():
    v = Kalshi(http=FailingKalshi(NOW, "/markets/", 500).add("A"), clock=lambda: NOW)
    with pytest.raises(KalshiError) as e:
        v.market("A")
    assert e.value.status_code == 500
    with pytest.raises(KalshiError):
        v.is_closed("A")                                                 # "closed?" must not quietly answer no


def test_series_lookup_failure_still_returns_the_market():
    v = Kalshi(http=FailingKalshi(NOW, "/series/").add("KXNEW-26NOV-A", series="KXNEW"), clock=lambda: NOW)
    m = v.market("KXNEW-26NOV-A")
    assert m.market_id == "KXNEW-26NOV-A" and m.category is None and m.fee_rate == pytest.approx(0.07)


def test_enrich_without_the_event_and_of_a_vanished_market():
    http = FailingKalshi(NOW, "/events/").add("KXCPIYOY-26NOV-T3.6")
    v = Kalshi(http=http, clock=lambda: NOW)
    listed = v.list_markets(categories=["economics"])[0]
    listed.n_event_markets = 5
    full = v.enrich(listed)
    assert "Consumer Price Index" in full.rules and "Settlement sources" not in full.rules
    assert full.n_event_markets == 5 and full.category == "economics"
    assert v.enrich(Market("GONE", "q?")) is None


def test_finalized_market_without_a_yes_no_result_reports_its_value():
    http = FakeKalshiHTTP(NOW).add("A")
    v = Kalshi(http=http, clock=lambda: NOW)
    http.markets["A"].update(status="finalized", result="", settlement_value_dollars="0.3700")
    assert v.settlement("A") == pytest.approx(0.37)                      # the trader refuses to settle on this
    http.markets["A"].update(status="determined", settlement_value_dollars=None)
    assert v.settlement("A") is None


# =====================================================================================================
# venue.py: the Polymarket US adapter with a stub client
# =====================================================================================================

def stub_client(market=None, event=None, event_error=None, settlement=None, settlement_error=None):
    def ev(slug):
        if event_error:
            raise event_error
        return {"event": event}

    def st(slug):
        if settlement_error:
            raise settlement_error
        return settlement
    return SimpleNamespace(markets=SimpleNamespace(retrieve_by_slug=lambda s: {"market": market}, settlement=st),
                           events=SimpleNamespace(retrieve_by_slug=ev))


DETAIL = {"slug": "cpi-above-3", "title": "Above 3%", "eventSlug": "cpi-nov", "description": "Detail rules.",
          "endDate": "2027-01-01T00:00:00Z", "active": True, "closed": False}


def test_market_detail_brings_its_event_when_it_names_one():
    ev = {"slug": "cpi-nov", "title": "CPI in November", "category": "macro", "markets": [{}, {}, {}]}
    m = PolymarketUS(stub_client(DETAIL, ev), min_interval=0).market("cpi-above-3")
    assert m.event_id == "cpi-nov" and m.event_title == "CPI in November" and m.category == "macro"
    assert m.question == "CPI in November: Above 3%" and m.n_event_markets == 3


def test_market_detail_survives_a_failed_event_lookup():
    m = PolymarketUS(stub_client(DETAIL, event_error=RuntimeError("500")), min_interval=0).market("cpi-above-3")
    assert m.event_id == "cpi-nov" and m.event_title is None and m.rules == "Detail rules."


def test_missing_market_and_enrich_keep_what_only_the_listing_knows():
    assert PolymarketUS(stub_client(None), min_interval=0).market("gone") is None
    assert PolymarketUS(stub_client(None), min_interval=0).enrich(Market("gone", "q?")) is None
    v = PolymarketUS(stub_client({**DETAIL, "eventSlug": None}), min_interval=0)
    listed = Market("cpi-above-3", "CPI in November: Above 3%", rules="Detail rules.\n\nListing-only clause.",
                    event_id="cpi-nov", category="macro", tags=["inflation"], n_event_markets=4)
    full = v.enrich(listed)
    assert full.rules == "Detail rules.\n\nListing-only clause."
    assert (full.event_id, full.category, full.n_event_markets, full.question) == ("cpi-nov", "macro", 4, listed.question)
    assert "inflation" in full.tags


def test_settlement_values_and_errors():
    v = lambda **kw: PolymarketUS(stub_client(**kw), min_interval=0)
    assert v(settlement={"settlement": None}).settlement("s") is None
    assert v(settlement={"settlement": 100}).settlement("s") == 1.0       # in cents
    err = RuntimeError("server error")
    err.status_code = 500
    with pytest.raises(RuntimeError):
        v(settlement_error=err).settlement("s")                           # only "not settled yet" means None


def test_parse_time_reads_a_naive_timestamp_as_utc():
    assert parse_time("2027-01-15T00:00:00") == parse_time("2027-01-15T00:00:00Z") == 1_799_971_200.0
    assert parse_time("yesterday") is None


# =====================================================================================================
# ledger.py: a failed write leaves no trace; old files are migrated
# =====================================================================================================

def test_rejected_fills_leave_cash_positions_and_the_order_untouched(ledger, market):
    ledger.upsert_market(market)
    ledger.deposit(10.0)
    oid = ledger.add_order({"market_id": "m1", "token_id": "m1-yes", "outcome": "YES", "side": "BUY", "status": "resting"})
    with pytest.raises(ValueError, match="needs \\$50.00 but cash is \\$10.00"):
        ledger.apply_fill(oid, "m1", "m1-yes", "YES", "BUY", 0.5, 100, order_status="filled")
    with pytest.raises(ValueError, match="only 0.0 held"):
        ledger.apply_fill(None, "m1", "m1-yes", "YES", "SELL", 0.5, 1)
    with pytest.raises(ValueError, match="unknown side"):
        ledger.apply_fill(None, "m1", "m1-yes", "YES", "HOLD", 0.5, 1)
    assert ledger.q("SELECT * FROM fills") == [] and ledger.q("SELECT * FROM positions") == []
    assert ledger.cash() == 10.0 and ledger.one("SELECT status FROM orders")["status"] == "resting"


def test_settling_twice_pays_once(ledger, market):
    ledger.upsert_market(market)
    ledger.deposit(100.0)
    ledger.apply_fill(None, "m1", "m1-no", "NO", "BUY", 0.4, 10)
    assert ledger.settle("m1", 0.0, ts=500.0) == pytest.approx(10.0)
    assert ledger.settle("m1", 0.0, ts=900.0) == 0.0
    assert ledger.cash() == pytest.approx(100.0 - 4.0 + 10.0)
    assert ledger.market("m1")["resolved_ts"] == 500.0


def test_old_ledger_gains_the_new_market_columns(tmp_path, market):
    path = tmp_path / "old.db"
    db = sqlite3.connect(path)
    db.execute("""CREATE TABLE markets (market_id TEXT PRIMARY KEY, condition_id TEXT, slug TEXT, question TEXT,
                  rules TEXT, event_id TEXT, event_title TEXT, category TEXT, end_ts REAL, neg_risk INTEGER DEFAULT 0,
                  yes_token TEXT, no_token TEXT, first_seen REAL, last_seen REAL, closed INTEGER DEFAULT 0,
                  resolved_ts REAL, payout_yes REAL)""")
    db.execute("INSERT INTO markets (market_id, question) VALUES ('old', 'kept?')")
    db.commit()
    db.close()
    led = Ledger(path)
    try:
        cols = {r["name"] for r in led.q("PRAGMA table_info(markets)")}
        assert {"checked_ts", "fee_rate", "maker_fee_rate"} <= cols
        assert led.market("old")["question"] == "kept?"
        led.upsert_market({**market, "fee_rate": 0.07})
        led.set_checked("m1", 123.0)
        assert (led.market("m1")["checked_ts"], led.market("m1")["fee_rate"]) == (123.0, 0.07)
    finally:
        led.close()


def test_snapshot_and_equity_lookups_before_a_time(ledger):
    ledger.add_snapshot("m1", 0.4, 0.5, 0.45, ts=100.0)
    ledger.add_snapshot("m1", 0.5, 0.6, 0.55, ts=200.0)
    assert ledger.last_snapshot("m1")["ts"] == 200.0
    assert ledger.last_snapshot("m1", before=150.0)["mid"] == 0.45
    assert ledger.last_snapshot("m1", before=50.0) is None
    ledger.record_equity({}, ts=100.0)
    ledger.record_equity({}, ts=200.0)
    assert ledger.last_equity(before=150.0)["ts"] == 100.0 and ledger.last_equity(before=50.0) is None


# =====================================================================================================
# broker.py, book.py
# =====================================================================================================

def test_resting_order_without_the_cash_is_cancelled_not_overdrawn(ledger):
    ledger.deposit(10.0)
    b = PaperBroker(ledger, FeeModel())
    oid = b.place_resting("r", "m1", "YES", "m1-yes", 0.50, 20.0, now=NOW)
    log = b.work_resting({"m1-yes": Book.from_levels("m1-yes", [(0.48, 100)], [(0.49, 100)])}, now=NOW + 60)
    assert log == ["m1: resting YES order cancelled (cash)"]
    o = ledger.one("SELECT * FROM orders WHERE id=?", (oid,))
    assert o["status"] == "cancelled" and o["note"] == "not enough cash when the price came to it"
    assert ledger.cash() == 10.0 and ledger.positions() == []


def test_live_broker_refuses_to_exist():
    with pytest.raises(NotImplementedError):
        LiveBroker()


def test_book_edges():
    one_sided = Book.from_levels("t", [(0.4, 1)], [])
    assert one_sided.spread is None and one_sided.mid is None and one_sided.near_touch_usd() == 0.0
    fills = simulate_sell(Book.from_levels("t", [(0.50, 0.01), (0.49, 100)], []), 10, 0.40)
    assert [(x.price, x.shares) for x in fills] == [(0.49, 10)]          # a sliver too small to trade is skipped
    assert summarize([]) == (0.0, 0.0, 0.0)


# =====================================================================================================
# replay.py, scoring.py
# =====================================================================================================

def test_replay_rule_exit_ignores_prices_from_before_the_fill_and_missing_bids():
    assert math.isnan(Outcome().ret)
    t = Trade(ts=100, market_id="m", outcome="YES", edge=0.05, stake=10, filled=True, fill_ts=100, price=0.5)
    path = [(50, 0.90, 0.92, 0.91), (100, 0.90, 0.92, 0.91), (200, None, 0.55, None), (300, 0.62, 0.64, 0.63)]
    how, value, when = follow(t, Settings(exit="rule", take_gain=0.10), path, None, None, [])
    assert (how, when) == ("sold", 300) and value == pytest.approx(0.62 - 0.07 * 0.62 * 0.38)
    assert follow(t, Settings(), [(200, None, None, None)], None, None, []) == ("open", 0.5, 100)


def test_scoring_small_samples_and_verdicts():
    assert all(math.isnan(x) for x in scoring.mean_se([]))
    m, se = scoring.mean_se([1.0])
    assert m == 1.0 and math.isnan(se)
    rep = lambda t, n=40: scoring.BrierReport(n=n, t=t).verdict()
    assert rep(float("nan")) == "no variation yet"
    assert rep(2.5).startswith("model beats the market price")
    assert rep(-2.5).startswith("model is WORSE") and "stop trading" in rep(-2.5)
    assert rep(0.5).startswith("no measurable difference")
    assert rep(5.0, n=10).startswith("too few")


def test_price_drift_uses_an_early_resolution_and_skips_markets_with_no_later_price(ledger, market):
    for mid in ("m1", "m2"):
        ledger.upsert_market({**market, "market_id": mid})
        ledger.add_forecast({"market_id": mid, "p_yes": 0.70, "market_mid": 0.50, "ts": 1000.0})
    ledger.mark_resolved("m1", 1.0, ts=1000.0 + H)                         # resolved inside the 72 h horizon
    rep = scoring.price_drift(ledger)
    assert rep.n == 1 and rep.toward == 1 and rep.mean_capture == pytest.approx(2.5)


# =====================================================================================================
# variants.py, safety.py, sizing.py, universe.py
# =====================================================================================================

def test_variant_names_must_be_file_safe(tmp_path):
    p = tmp_path / "variants.yaml"
    p.write_text("variants:\n  plain_one:\n  bad-name:\n    transform: none\n")
    with pytest.raises(ValueError, match="letters, digits and underscores"):
        load_variants(p)
    p.write_text("variants:\n  plain_one:\n")
    assert load_variants(p) == {"plain_one": {"about": "", "transform": "none", "overrides": {}}}


def test_shared_venue_skips_failing_missing_and_closed_markets_and_asks_once():
    asked = []
    good = Market("good", "q?")

    class Inner:
        def market(self, mid):
            asked.append(mid)
            if mid == "broken":
                raise RuntimeError("500")
            return {"good": good, "closed": Market("closed", "q?", closed=True)}.get(mid)
    sv = SharedVenue(Inner(), ["good", "broken", "gone", "closed", "good"])
    first = sv.list_markets()
    assert [m.market_id for m in first] == ["good"]
    first[0].raw["lite"] = True                                          # one account marks up its copy ...
    second = sv.list_markets()
    assert "lite" not in second[0].raw and "lite" not in good.raw        # ... the next account does not see it
    assert sorted(asked) == ["broken", "broken", "closed", "gone", "good"]   # failures are not cached, answers are


def test_run_variants_only_runs_the_named_ones_and_standings_cope_with_missing_files(tmp_path):
    from test_variants import VARIANTS, cfg as vcfg
    main = Ledger(tmp_path / "data" / "pmt.db")
    try:
        main.deposit(1000.0)
        out = run_variants(vcfg(), VARIANTS, main, Kalshi(http=FakeKalshiHTTP(NOW), clock=lambda: NOW), tmp_path,
                           now=NOW, only=["control_fade"])
    finally:
        main.close()
    assert [s["variant"] for s in out] == ["control_fade"] and out[0]["status"] == "ok"
    assert not (tmp_path / "data" / "variants" / "claude_only.db").exists()
    rows = {r["account"]: r for r in standings(tmp_path, VARIANTS, main_db=tmp_path / "nowhere.db")}
    assert rows["main"]["started"] is None and rows["claude_only"]["started"] is None
    assert rows["control_fade"]["deposited"] == 1000.0


def test_empty_kill_switch_setting_disables_the_file_check(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "STOP").write_text("stop")
    assert safety.kill_switch_on({}, tmp_path) == "data/STOP"
    assert safety.kill_switch_on({"safety": {"kill_switch": ""}}, tmp_path) is None


def test_min_edge_ratio_blocks_cheap_longshots():
    rules = SizingRules(shrink_weight=0.5, min_edge=0.03, min_edge_ratio=0.6, min_price=0.10)
    sz = plan_entry(0.30, 0.15, 0.15, None, Exposure(equity=1000.0, cash=1000.0), rules)
    assert not sz.trade and sz.reason == "edge 0.075 is under 60% of the cost 0.150"
    assert plan_entry(0.30, 0.15, 0.15, None, Exposure(equity=1000.0, cash=1000.0),
                      dataclasses.replace(rules, min_edge_ratio=0.0)).trade


def test_book_check_minimum_traded_volume():
    yes = Book.from_levels("t", [(0.48, 500)], [(0.50, 500)])
    yes.volume_usd = 100.0
    st = universe.settings({"universe": {"min_volume": 500}})
    assert universe.book_check(yes, "MARKET_STATE_OPEN", st) == "only $100 traded so far (min $500)"
    yes.volume_usd = None                                               # unknown volume is not a reason to drop
    assert universe.book_check(yes, "MARKET_STATE_OPEN", st) == ""
