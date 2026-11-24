"""Ideas queue 14 (report 3.41): the Entertainment band (NO where YES is at 5-35c, resting) split by days to the
scheduled close. Each slice takes the first bar per market inside its window, so a market can be in several slices.

    .venv/Scripts/python.exe research/band_by_dte.py 20000
    .venv/Scripts/python.exe research/band_by_dte.py 45000 nine   # queue item 16 (report 3.43): the nine pooled
    The 7-10000 slice (queue item 40, report 3.61) is the band with its 0-7 day markets left out.
    .venv/Scripts/python.exe research/band_by_dte.py 20000 ent --mixed   # queue item 41 (report 3.62): adds the mixed cut,
    7+ day bars at 20,000 and 0-7 day bars only at 45,000
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import pandas as pd
import panel
from backtest import Panel
from families import Features
from analyze_rule import find_rule, bets_frame, report, near_close_cumvol
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
    for lo, hi in ((0, 10000), (0, 7), (7, 30), (30, 10000), (7, 10000)):  # 7-10000: queue item 40, the band without 0-7d
        m = mask & f.days(lo, hi)
        print(f"\n===== {entry} dte {lo}-{hi} (first bar per market inside the window), min_cumvol {mc:g}")
        print(report(bets_frame(p, m, "no", entry), p, m, "no", entry))
    if mc < 45000 and "--mixed" in sys.argv:  # queue item 41 (report 3.62): 7+ d at this level, 0-7 d only at 45,000
        m = near_close_cumvol(p, mask, f.dte, 7, 45000)
        print(f"\n===== {entry} mixed: 7+ d at {mc:g}, 0-7 d only at 45000 (first bar per market)")
        print(report(bets_frame(p, m, "no", entry), p, m, "no", entry))
