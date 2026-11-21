"""Keep the paper bot cycling: run a cycle whenever the last one started more than N hours ago, then the variant
accounts, the forecast export and the observation log. Safe to kill and restart at any time: the schedule lives
in the ledger, not in this process.

    python scripts/paper_loop.py                    N from config.yaml (runtime.cycle_every_hours)
    python scripts/paper_loop.py --every 3          N fixed at 3, whatever the config says

How often is a free dial (it does not touch the forecaster, so it does not break the track record), with one
limit that is not ours: the Claude subscription. So N widens by itself. After a cycle in which the forecaster
could not answer (a usage limit, a model other than the configured one answering, every question failing), the
gap to the next cycle doubles, up to runtime.cycle_max_hours; after a cycle whose forecasts came through it
halves again, down to the configured N. The current gap is kept in data/paper_loop_state.json and printed in
the log, so it is never a mystery why a cycle did not run.
"""
import argparse
import json
import re
import sqlite3
import subprocess
import sys
import time

from _bootstrap import ROOT

from src.config import load_config

LIMIT_WORDS = re.compile(r"limit|usage|quota|overloaded|capacity|credit|429|too many requests", re.IGNORECASE)
FAILED = ("no usable forecast", "forecaster failed")


def last_run_started(db_path) -> float:
    try:
        db = sqlite3.connect(str(db_path), timeout=30)
        row = db.execute("SELECT MAX(started) FROM runs").fetchone()
        db.close()
        return float(row[0] or 0.0)
    except sqlite3.Error:
        return 0.0


def last_run(db_path) -> dict:
    """What the most recent cycle did: its log lines and the model behind each forecast it made."""
    try:
        db = sqlite3.connect(str(db_path), timeout=30)
        row = db.execute("SELECT run_id, summary FROM runs ORDER BY started DESC LIMIT 1").fetchone()
        if not row:
            db.close()
            return {}
        models = [r[0] or "" for r in db.execute("SELECT model FROM forecasts WHERE run_id=?", (row[0],))]
        db.close()
        summary = json.loads(row[1] or "{}")
        return {"run_id": row[0], "log": summary.get("log") or [], "models": models}
    except (sqlite3.Error, ValueError):
        return {}


def next_gap(current: float, base: float, ceiling: float, run: dict, model: str | None = None) -> tuple[float, str]:
    """Hours to wait before the next cycle, and why. `run` is last_run(); `model` is the configured forecaster
    model ("opus"): a forecast answered by anything else means the subscription fell back to another model."""
    current = min(max(current, base), ceiling)
    log = run.get("log") or []
    failed = [line for line in log if any(k in line for k in FAILED)]
    made = len(run.get("models") or [])
    limited = [line for line in failed if LIMIT_WORDS.search(line)]
    other = [m for m in (run.get("models") or []) if model and model.lower() not in m.lower()]
    why = ""
    if limited:
        why = f"the forecaster hit a limit ({limited[0][:120]})"
    elif other:
        why = f"a forecast was answered by {other[0]!r}, not {model!r}: the subscription may be falling back"
    elif failed and not made:
        why = f"every question failed ({failed[0][:120]})"
    if why:
        return min(current * 2.0, ceiling), why
    if made and current > base:
        return max(current / 2.0, base), "forecasts are coming through again"
    return current, ""


def settings(config_path, every_arg) -> tuple[float, float, str | None]:
    """(base gap, widest gap, configured model). The config is read again before every decision, so changing
    runtime.cycle_every_hours takes effect without restarting the loop."""
    cfg = load_config(config_path)
    rt = cfg.get("runtime") or {}
    base = float(every_arg) if every_arg else float(rt.get("cycle_every_hours", 6.0))
    ceiling = max(float(rt.get("cycle_max_hours", 12.0)), base)
    model = (cfg.get("forecaster") or {}).get("model")
    return base, ceiling, model


def load_gap(path, base: float, ceiling: float) -> float:
    try:
        return min(max(float(json.loads(path.read_text(encoding="utf-8"))["every_hours"]), base), ceiling)
    except (OSError, ValueError, KeyError, TypeError):
        return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--every", type=float, default=None, help="hours between cycles (default: runtime.cycle_every_hours)")
    ap.add_argument("--poll", type=float, default=300.0, help="seconds between checks")
    args = ap.parse_args()
    db = ROOT / "data" / "pmt.db"
    state = ROOT / "data" / "paper_loop_state.json"
    extra = ["--config", args.config] if args.config else []
    py = [sys.executable, "-u"]
    base, ceiling, model = settings(args.config, args.every)
    gap = load_gap(state, base, ceiling)
    stamp = lambda: time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    print(f"===== {stamp()} paper loop started: a cycle every {gap:g} h (configured {base:g} h, widest {ceiling:g} h)", flush=True)
    while True:
        try:
            base, ceiling, model = settings(args.config, args.every)
        except Exception as e:                      # a half-saved config file: keep the last settings
            print(f"config not readable ({type(e).__name__}): keeping {base:g} h", flush=True)
        gap = min(max(gap, base), ceiling)
        if time.time() - last_run_started(db) >= gap * 3600:
            before = last_run(db).get("run_id")
            print(f"===== {stamp()}", flush=True)
            subprocess.run(py + [str(ROOT / "scripts" / "run_cycle.py")] + extra, cwd=str(ROOT))
            # the variant accounts trade the forecasts this cycle has just made (no Claude calls): src/variants.py
            subprocess.run(py + [str(ROOT / "scripts" / "run_variants.py")] + extra, cwd=str(ROOT))
            # the mechanical rule accounts (price rules from the history, no Claude): src/rules.py, rules.yaml
            subprocess.run(py + [str(ROOT / "scripts" / "run_rules.py")] + extra, cwd=str(ROOT))
            subprocess.run([sys.executable, str(ROOT / "scripts" / "export_forecasts.py")], cwd=str(ROOT))
            # the mechanical rule under observation (no orders, its own file): see scripts/shadow_longshot.py
            subprocess.run([sys.executable, str(ROOT / "scripts" / "shadow_longshot.py")], cwd=str(ROOT))
            subprocess.run([sys.executable, str(ROOT / "scripts" / "shadow_longshot.py"), "--band", "ent"], cwd=str(ROOT))
            run = last_run(db)
            if run.get("run_id") != before:         # a cycle that was skipped (quiet window, lock) decides nothing
                new, why = next_gap(gap, base, ceiling, run, model)
                if new != gap:
                    print(f"next cycle in {new:g} h instead of {gap:g} h: {why}", flush=True)
                gap = new
                try:
                    state.write_text(json.dumps({"every_hours": gap, "why": why, "set": stamp()}), encoding="utf-8")
                except OSError:
                    pass
        time.sleep(args.poll)


if __name__ == "__main__":
    sys.exit(main())
