"""The paper loop's cadence: it widens when the forecaster cannot answer and comes back when it can."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import paper_loop as pl  # noqa: E402

OK = ["Safety: PASS", "A: forecast 0.60 vs market 0.50 (medium, runs [0.6, 0.6, 0.6])", "A: no trade (edge too small)"]


def run(log, models):
    return {"run_id": "r", "log": log, "models": models}


def test_a_good_cycle_keeps_the_configured_gap():
    assert pl.next_gap(2, 2, 12, run(OK, ["claude-haiku-5-5,claude-opus-5-5"]), "opus") == (2, "")


def test_a_usage_limit_doubles_the_gap_up_to_the_ceiling():
    hit = ["A: no usable forecast (claude reported an error: Claude usage limit reached, resets 9am)"]
    gap, why = pl.next_gap(2, 2, 12, run(hit, []), "opus")
    assert gap == 4 and "limit" in why
    assert pl.next_gap(8, 2, 12, run(hit, []), "opus")[0] == 12
    # one question got through before the limit: still a limit
    assert pl.next_gap(2, 2, 12, run(OK + hit, ["claude-opus-5-5"]), "opus")[0] == 4


def test_every_question_failing_widens_even_without_the_word_limit():
    dead = ["A: no usable forecast (claude exited 1 without JSON: Not logged in)", "B: forecaster failed (OSError)"]
    gap, why = pl.next_gap(2, 2, 12, run(dead, []), "opus")
    assert gap == 4 and "every question failed" in why
    # one timeout among good forecasts is not a reason to slow down
    some = OK + ["B: no usable forecast (claude timed out after 900 s)"]
    assert pl.next_gap(2, 2, 12, run(some, ["claude-opus-5-5"]), "opus") == (2, "")


def test_another_model_answering_counts_as_a_limit():
    gap, why = pl.next_gap(2, 2, 12, run(OK, ["claude-sonnet-5-5"]), "opus")
    assert gap == 4 and "sonnet" in why
    assert pl.next_gap(2, 2, 12, run(OK, ["claude-sonnet-5-5"]), None) == (2, "")      # no model configured: nothing to compare


def test_the_gap_comes_back_down_only_when_forecasts_come_through():
    assert pl.next_gap(8, 2, 12, run(OK, ["claude-opus-5-5"]), "opus") == (4, "forecasts are coming through again")
    assert pl.next_gap(8, 2, 12, run(["Safety: PASS", "0 sent to the forecaster"], []), "opus") == (8, "")   # nothing asked: no evidence
    assert pl.next_gap(3, 2, 12, run(OK, ["claude-opus-5-5"]), "opus")[0] == 2
    assert pl.next_gap(1, 2, 12, run(OK, ["claude-opus-5-5"]), "opus")[0] == 2            # never under the configured gap
    assert pl.next_gap(8, 2, 12, {}, "opus") == (8, "")                                   # no run on record


def test_settings_and_saved_gap(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text("runtime: {cycle_every_hours: 2, cycle_max_hours: 12}\nforecaster: {model: opus}\n", encoding="utf-8")
    assert pl.settings(str(cfg), None) == (2.0, 12.0, "opus")
    assert pl.settings(str(cfg), 3) == (3.0, 12.0, "opus")             # --every wins over the file
    assert pl.settings(str(cfg), 24)[1] == 24.0                        # the ceiling is never under the base
    state = tmp_path / "s.json"
    assert pl.load_gap(state, 2, 12) == 2                              # no file yet
    state.write_text(json.dumps({"every_hours": 8}), encoding="utf-8")
    assert pl.load_gap(state, 2, 12) == 8
    state.write_text(json.dumps({"every_hours": 99}), encoding="utf-8")
    assert pl.load_gap(state, 2, 12) == 12
    state.write_text("not json", encoding="utf-8")
    assert pl.load_gap(state, 2, 12) == 2


def test_last_run_reads_the_ledger(tmp_path):
    from src.ledger import Ledger
    led = Ledger(tmp_path / "pmt.db")
    assert pl.last_run(tmp_path / "pmt.db") == {}
    led.start_run("r1")
    led.add_forecast({"market_id": "A", "p_yes": 0.6, "run_id": "r1", "model": "claude-opus-5-5"})
    led.finish_run("r1", "ok", {"log": OK})
    led.close()
    got = pl.last_run(tmp_path / "pmt.db")
    assert got == {"run_id": "r1", "log": OK, "models": ["claude-opus-5-5"]}
    assert pl.last_run_started(tmp_path / "pmt.db") > 0
