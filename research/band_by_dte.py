"""Ideas queue 14 (report 3.41): the Entertainment band (NO where YES is at 5-35c, resting) split by days to the
scheduled close. Each slice takes the first bar per market inside its window, so a market can be in several slices.

    .venv/Scripts/python.exe research/band_by_dte.py 20000
    .venv/Scripts/python.exe research/band_by_dte.py 45000 nine   # queue item 16 (report 3.43): the nine pooled
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import pandas as pd
import panel
from backtest import Panel
from families import Features
from analyze_rule import find_rule, bets_frame, report
from run_sweep import titles_for
pd.set_option("display.width", 200)
mc = float(sys.argv[1])
NINE = ["Economics", "Politics", "Companies", "Science and Technology", "Elections", "Health", "World",
        "Commodities", "Financials"]
cats = NINE if len(sys.argv) > 2 and sys.argv[2] == "nine" else ["Entertainment"]
df = panel.load(str(panel.DB), cats, sample="liquid", min_cumvol=mc)
print(panel.describe(df).splitlines()[0])
p = Panel(df); f = Features(p)
for entry in ("mk",):
    fam, mask = find_rule(f, titles_for(df, str(panel.DB)), "NO where YES is at 5-35c", "no", entry)
    for lo, hi in ((0, 10000), (0, 7), (7, 30), (30, 10000)):
        m = mask & f.days(lo, hi)
        print(f"\n===== {entry} dte {lo}-{hi} (first bar per market inside the window), min_cumvol {mc:g}")
        print(report(bets_frame(p, m, "no", entry), p, m, "no", entry))
