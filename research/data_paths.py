"""Where the research databases live: the Kalshi history (kalshi_hist.db, with kalshi_events.db beside it) and the
hourly bars (kalshi_hourly.db).

Normally data\\ in the project. If C: runs short of space they are moved to another drive (the user, 2026-11-24: "if
the C drive fills up please switch to using the D drive"; scripts\\move_history.ps1), and data\\history_location.txt
then names the folder that holds them. Everything that opens them asks here, so nothing else changes after a move.

If the file names a folder that is not there (the drive is missing), this raises instead of falling back to data\\:
a fallback would quietly start a new, empty history on C:.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POINTER = ROOT / "data" / "history_location.txt"


def history_dir(pointer: Path | None = None) -> Path:
    pointer = POINTER if pointer is None else pointer
    if not pointer.exists():
        return ROOT / "data"
    where = Path(pointer.read_text(encoding="utf-8-sig").strip())
    if not where.is_dir():
        raise FileNotFoundError(f"{pointer} says the research databases are in {where}, which is not there "
                                f"(is the drive connected?)")
    return where


def hist_db(pointer: Path | None = None) -> Path:
    return history_dir(pointer) / "kalshi_hist.db"


def hourly_db(pointer: Path | None = None) -> Path:
    return history_dir(pointer) / "kalshi_hourly.db"
