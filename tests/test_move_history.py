"""scripts/move_history.ps1 and research/data_paths.py: moving the research databases off C: (the user, 2026-11-24:
"if the C drive fills up please switch to using the D drive"). Runs on temporary folders only, never on data\\."""
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))

import data_paths  # noqa: E402

SCRIPT = ROOT / "scripts" / "move_history.ps1"
PS = shutil.which("powershell.exe") or shutil.which("powershell")
windows = pytest.mark.skipif(sys.platform != "win32" or not PS, reason="Windows PowerShell only")


def make_db(path: Path, rows: int):
    db = sqlite3.connect(str(path))
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE t (x INTEGER)")
    db.executemany("INSERT INTO t VALUES (?)", [(i,) for i in range(rows)])
    db.commit()
    db.close()


def run(data: Path, to: Path, check=True):
    p = subprocess.run([PS, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT), "-DataDir", str(data),
                        "-To", str(to), "-NoStop", "-NoRestart"], capture_output=True, text=True, timeout=120)
    if check:
        assert p.returncode == 0, p.stdout + p.stderr
    return p


@windows
def test_the_databases_move_and_the_pointer_follows(tmp_path):
    data, to = tmp_path / "data", tmp_path / "D" / "PredictionMarketTrader" / "data"
    data.mkdir()
    make_db(data / "kalshi_hist.db", 1000)
    make_db(data / "kalshi_hourly.db", 10)
    (data / "pmt.db").write_bytes(b"the paper ledger stays")
    run(data, to)
    pointer = data / "history_location.txt"
    assert pointer.read_text(encoding="utf-8") == str(to)
    assert not list(data.glob("kalshi_*"))                       # the C: copies are gone
    assert (data / "pmt.db").exists() and not (to / "pmt.db").exists()
    db = sqlite3.connect(str(to / "kalshi_hist.db"))
    assert db.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1000
    db.close()
    assert data_paths.hist_db(pointer) == to / "kalshi_hist.db" and data_paths.hourly_db(pointer) == to / "kalshi_hourly.db"
    assert "moved" in (data / "move_history.log").read_text(encoding="utf-8-sig")


@windows
def test_a_second_run_only_clears_leftovers(tmp_path):
    data, to = tmp_path / "data", tmp_path / "D"
    data.mkdir()
    make_db(data / "kalshi_hist.db", 100)
    run(data, to)
    (data / "kalshi_hist.db").write_bytes(b"x")                  # a stale C: copy a busy run could not delete
    p = run(data, to)
    assert "already moved" in p.stdout and not (data / "kalshi_hist.db").exists()
    assert sqlite3.connect(str(to / "kalshi_hist.db")).execute("SELECT COUNT(*) FROM t").fetchone()[0] == 100


@windows
def test_nothing_to_move_is_an_error(tmp_path):
    (tmp_path / "data").mkdir()
    p = run(tmp_path / "data", tmp_path / "D", check=False)
    assert p.returncode != 0 and not (tmp_path / "data" / "history_location.txt").exists()


def test_without_a_pointer_the_databases_are_in_data(tmp_path):
    assert data_paths.history_dir(tmp_path / "none.txt") == ROOT / "data"


def test_a_pointer_to_a_missing_folder_is_an_error_not_a_new_empty_history(tmp_path):
    p = tmp_path / "history_location.txt"
    p.write_text(str(tmp_path / "gone"), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        data_paths.hist_db(p)
    (tmp_path / "gone").mkdir()
    p.write_text("﻿" + str(tmp_path / "gone") + "\r\n", encoding="utf-8")   # a byte-order mark and a newline
    assert data_paths.hist_db(p) == tmp_path / "gone" / "kalshi_hist.db"
