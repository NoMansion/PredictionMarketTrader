"""scripts/checkin.ps1, the headless Opus check-in, run against a FAKE claude program (never the real one).

The fake is a .cmd that runs tests' own Python script: it records its arguments, its stdin and its environment,
then prints whatever answer the test wrote for it. The script's -ClaudeExe, -DataDir and -NoNote parameters exist
for these tests only.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "checkin.ps1"
PS = shutil.which("powershell.exe") or shutil.which("powershell")

pytestmark = pytest.mark.skipif(sys.platform != "win32" or not PS, reason="Windows PowerShell only")

FAKE = r'''
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
stdin = sys.stdin.read()
env = {k: v for k, v in os.environ.items() if k.startswith(("CLAUDE", "ANTHROPIC", "TEMP", "TMP"))}
with open(os.path.join(here, "seen.json"), "w", encoding="utf-8") as f:
    json.dump({"argv": sys.argv[1:], "stdin": stdin, "env": env}, f)
cfg = json.load(open(os.path.join(here, "behaviour.json"), encoding="utf-8"))
time.sleep(cfg.get("sleep", 0))
sys.stdout.write(cfg.get("stdout", ""))
sys.stderr.write(cfg.get("stderr", ""))
sys.exit(cfg.get("exit", 0))
'''


def answer(models=("claude-opus-5-5", "claude-haiku-5-5"), result="did things\nPMT all well", **extra):
    j = {"type": "result", "is_error": False, "result": result, "duration_ms": 61000, "total_cost_usd": 0.3217}
    if models is not None:
        j["modelUsage"] = {m: {"inputTokens": 1} for m in models}
    j.update(extra)
    return json.dumps(j)


@pytest.fixture
def rig(tmp_path):
    fake_dir = tmp_path / "fake"
    fake_dir.mkdir()
    (fake_dir / "fake_claude.py").write_text(FAKE, encoding="utf-8")
    exe = fake_dir / "claude.cmd"
    exe.write_text(f'@"{sys.executable}" -I "{fake_dir / "fake_claude.py"}" %*\r\n', encoding="utf-8")
    data = tmp_path / "data"
    data.mkdir()
    prompt = tmp_path / "prompt.md"
    prompt.write_text("check things\nlast line please", encoding="utf-8")

    class Rig:
        def behave(self, **cfg):
            (fake_dir / "behaviour.json").write_text(json.dumps(cfg), encoding="utf-8")

        def run(self, *extra, claude=exe, prompt_file=prompt, env_extra=None):
            args = [PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
                    "-ClaudeExe", str(claude), "-DataDir", str(data), "-NoNote"]
            if prompt_file:
                args += ["-PromptFile", str(prompt_file)]
            env = dict(os.environ, **(env_extra or {}))
            p = subprocess.run(args + list(extra), capture_output=True, text=True, timeout=120, env=env)
            assert p.returncode == 0, p.stderr
            return p

        def log(self):
            f = data / "checkin.log"
            return f.read_text(encoding="utf-8-sig").strip().splitlines() if f.exists() else []

        def seen(self):
            f = fake_dir / "seen.json"
            return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None

    r = Rig()
    r.data, r.exe, r.fake_dir = data, exe, fake_dir
    r.behave(stdout=answer())
    return r


def test_opus_run_is_logged_ok_with_its_models_cost_and_last_line(rig):
    rig.run()
    (line,) = rig.log()
    assert "ok in 1 min, list price $0.32, models claude-opus-5-5,claude-haiku-5-5: PMT all well" in line
    assert "OTHER MODEL" not in line and "ERROR" not in line and "NO MODEL" not in line
    assert not (rig.data / "checkin.lock").exists()
    outs = list((rig.data / "checkin").glob("*.json"))
    assert len(outs) == 1 and json.loads(outs[0].read_text(encoding="utf-8"))["result"].endswith("PMT all well")


def test_cli_is_called_on_opus_headless_with_no_fallback_model_and_the_prompt_on_stdin(rig):
    rig.run()
    seen = rig.seen()
    a = seen["argv"]
    assert a[a.index("--model") + 1] == "claude-opus-5-5"
    assert "-p" in a and a[a.index("--output-format") + 1] == "json"
    assert a[a.index("--permission-mode") + 1] == "auto"
    assert not any("fallback" in x for x in a)
    assert "check things" in seen["stdin"] and "last line please" in seen["stdin"]


def test_cli_gets_a_list_price_cap_and_zero_means_none(rig):
    rig.run()
    a = rig.seen()["argv"]
    assert a[a.index("--max-budget-usd") + 1] == "8"
    rig.run("-MaxBudgetUsd", "2.5", "-MinGapMinutes", "0")
    a = rig.seen()["argv"]
    assert a[a.index("--max-budget-usd") + 1] == "2.5"
    rig.run("-MaxBudgetUsd", "0", "-MinGapMinutes", "0")
    assert "--max-budget-usd" not in rig.seen()["argv"]


def test_a_run_stopped_by_the_cap_is_flagged(rig):
    rig.behave(stdout=answer(is_error=True, subtype="error_max_budget_usd", result=""))
    rig.run()
    line = rig.log()[0]
    assert "BUDGET CAP HIT ($8)" in line and "ERROR" in line


def test_default_prompt_is_the_checkin_prompt_and_default_model_is_opus(rig):
    rig.run(prompt_file=None)
    seen = rig.seen()
    assert seen["argv"][seen["argv"].index("--model") + 1] == "claude-opus-5-5"
    first = (ROOT / "scripts" / "checkin_prompt.md").read_text(encoding="utf-8").strip().splitlines()[0]
    assert first.strip() in seen["stdin"]


def test_session_identity_is_not_inherited_and_temp_stays_under_data(rig):
    rig.run(env_extra={"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "x", "CLAUDE_AGENT_SDK_VERSION": "y",
                       "ANTHROPIC_BASE_URL": "http://example.invalid"})
    env = rig.seen()["env"]
    for k in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_AGENT_SDK_VERSION", "ANTHROPIC_BASE_URL"):
        assert k not in env
    assert Path(env["TEMP"]) == rig.data / "tmp" and env["TMP"] == env["TEMP"]
    assert (rig.data / "tmp").is_dir()


@pytest.mark.parametrize("model", ["claude-fable-5-2", "claude-sonnet-5-5"])
def test_any_model_other_than_opus_or_haiku_is_flagged(rig, model):
    rig.behave(stdout=answer(models=("claude-opus-5-5", model)))
    rig.run()
    (line,) = rig.log()
    assert f"OTHER MODEL USED ({model})" in line


def test_an_answer_that_reports_no_model_is_flagged(rig):
    rig.behave(stdout=answer(models=None))
    rig.run()
    assert "NO MODEL REPORTED" in rig.log()[0]


def test_an_error_answer_is_flagged(rig):
    rig.behave(stdout=answer(is_error=True, result="Usage limit reached"))
    rig.run()
    line = rig.log()[0]
    assert "ERROR" in line and "Usage limit reached" in line


def test_empty_answer_text_is_said_so(rig):
    rig.behave(stdout=answer(result="  \n "))
    rig.run()
    assert "(no answer text)" in rig.log()[0]


def test_output_that_is_not_json_is_a_failure_with_the_exit_code_and_stderr(rig):
    rig.behave(stdout="not json at all", stderr="Error: not logged in", exit=3)
    rig.run()
    (line,) = rig.log()
    assert "FAILED: exit 3, no JSON answer" in line and "not logged in" in line
    assert not (rig.data / "checkin.lock").exists()


def test_missing_claude_program_is_a_failure_and_releases_the_lock(rig, tmp_path):
    rig.run(claude=tmp_path / "nowhere" / "claude.exe")
    assert "FAILED: the claude program is missing" in rig.log()[0]
    assert rig.seen() is None and not (rig.data / "checkin.lock").exists()


def test_kill_switch_skips_the_run(rig):
    (rig.data / "STOP").write_text("", encoding="utf-8")
    rig.run()
    assert "skipped: data\\STOP exists" in rig.log()[0]
    assert rig.seen() is None and not (rig.data / "checkin.lock").exists()


def test_a_fresh_lock_means_another_run_is_going_and_is_left_alone(rig):
    lock = rig.data / "checkin.lock"
    lock.write_text("1234", encoding="utf-8")
    rig.run()
    assert "skipped: another check-in is running" in rig.log()[0]
    assert rig.seen() is None and lock.read_text(encoding="utf-8") == "1234"


def test_a_stale_lock_from_a_dead_run_is_taken_over(rig):
    lock = rig.data / "checkin.lock"
    lock.write_text("1234", encoding="utf-8")
    old = time.time() - 110 * 60         # older than the 100-minute timeout plus 5
    os.utime(lock, (old, old))
    rig.run()
    assert "ok in" in rig.log()[0] and rig.seen() is not None
    assert not lock.exists()


def test_a_run_past_its_timeout_is_stopped_and_logged(rig):
    rig.behave(stdout=answer(), sleep=4)
    rig.run("-TimeoutMinutes", "0")
    line = rig.log()[0]
    assert "FAILED: no answer within 0 minutes (stopped)" in line
    assert not (rig.data / "checkin.lock").exists()


def test_each_run_appends_one_line(rig):
    rig.run()
    rig.behave(stdout=answer(result="PMT second"))
    time.sleep(1)
    rig.run("-MinGapMinutes", "0")
    lines = rig.log()
    assert len(lines) == 2 and lines[1].endswith("PMT second")


def test_a_second_start_soon_after_the_last_one_is_skipped_without_asking_claude(rig):
    rig.run()
    (rig.fake_dir / "seen.json").unlink()
    rig.run()
    lines = rig.log()
    assert len(lines) == 2 and "skipped: the last check-in started 0 minutes ago (under 150)" in lines[1]
    assert rig.seen() is None and not (rig.data / "checkin.lock").exists()


def test_a_start_long_after_the_last_one_runs(rig):
    rig.run()
    old = time.time() - 151 * 60
    for f in (rig.data / "checkin").glob("*.prompt.txt"):
        os.utime(f, (old, old))
    (rig.fake_dir / "seen.json").unlink()
    rig.run()
    assert "ok in" in rig.log()[1] and rig.seen() is not None
