# Research loop: state

The user asked (2026-11-18, before going to bed) for strategy research to keep running: every strategy family
that can be tested, and combinations of families, with settings varied. This file is what each check-in
reads first. Keep it short and current. Findings go in the report; this is the control sheet.

## PAUSED BY THE USER since 1:20 pm CST, 2026-11-19 ("Pause", then "Everything")

Nothing runs until the user says resume. Do NOT start the download or the paper loop, do not run a cycle or a
research round, and do not re-enable anything below on your own.

- Stopped with `research\start_jobs.ps1 -Stop`: the paper loop (last cycle 11:53 am to 12:52 pm, ended ok) and
  the history download (110,497 markets with bars at 1:09 pm). Both resume where they left off.
- Switched off: the app's scheduled check-in (`prediction-market-research-checkin`, enabled = false) and the
  Windows log-on task "PredictionMarketTrader Jobs" (disabled, so a restart of the PC does not unpause).
- To resume, on the user's word only: `Enable-ScheduledTask -TaskName "PredictionMarketTrader Jobs"`, enable
  the check-in again, then `research\start_jobs.ps1 -PaperLoop`. Then delete this section and add a progress line.
- While paused: resting paper orders pass their 24-hour limit and are expired at the first cycle after the
  resume; open positions are simply re-valued then. Forecasts older than 6 hours are not traded.

**Report:** `reports/2026-11-18_strategy_research.md` (create on first results; add a dated section per check-in).

## Standing instruction (2026-11-19, about 3:50 am CST, on the PC)

The user: "are you prepared to download data, run tests, and determine the best strategy you can to make as
much money in a risk averse way indefinitely while i leave my pc on". Taken as: the research loop the cloud
session ran continues on the PC without waiting for the user. What that does and does not cover:

- Covered: the history download, backtest rounds on new data, the forward tests (paper loop, observation
  log), writing every result into the report, pushing code, results and reports.
- NOT covered, each needs the user's own yes: any change to the paper bot's config or a second paper account
  for a mechanical rule; anything with real money (never done from here: `docs/GO_LIVE.md`); a Task Scheduler
  entry or other standing change on the PC.
- "Risk averse" is read as: the rules for judging below stay as they are, a rule is judged by its account
  replay and its worst periods as well as its mean, and capacity in dollars is always reported.
- What keeps it going (set up 2026-11-19, 3:55 am CST, with the user's yes):
  - The check-in is a scheduled task of the Claude desktop app, "PredictionMarketTrader check-in (every 3
    hours)" (id `prediction-market-research-checkin`). EVERY 3 HOURS since 11:05 am CST 2026-11-19, at about
    11 past 12, 3, 6 and 9, am and pm; hourly before that. The user chose it ("Yes, every 3 hours"): the
    hourly runs spent about 0.6 points of the weekly Fable allowance each and would have used it up about
    a day before the Sunday reset. Only the user changes this schedule. Each run is a new session
    that knows only its prompt and this file: keep this file current. It runs while the app is open; a run
    missed while the app was closed happens at the next launch. The user manages it under "Scheduled" in
    the app. Since 11:10 am CST 2026-11-19 (the user: "can you send an update message every check in") each
    finished run notifies the user's main session, which passes a short update on to the user; that works
    only while that session exists. So END EVERY RUN with the three or four plain lines the prompt asks for:
    they are what the user is sent.
  - The Windows task "PredictionMarketTrader Jobs" runs `scripts\start_jobs_hidden.vbs` when the user logs
    on: two minutes later it starts the history download and the paper loop if they are not running.
    Remove it with: `Unregister-ScheduledTask -TaskName "PredictionMarketTrader Jobs"`.
  - Neither helps while the PC is off, the user is logged out, or Claude usage is exhausted.

## Decisions already made

- **Times for the user: US Central, 12-hour with am/pm** (asked 2026-11-18, 4:34 pm CST). Applies to every
  message and to new report text; logs stay in UTC. `TZ=America/Chicago date "+%-I:%M %p %Z"`.

- **Venue: Kalshi.** Measured live on 2026-11-18 with the same filters: 570 markets in 273 events pass on Kalshi
  against 96 on Polymarket US; 86 against 6 or 7 are deep enough to trade. Kalshi's taker fee is lower (0.07
  against 0.095) and it is open in every state. The user lives in Illinois and said to use whichever is better.
- **Paper only.** No account, no keys, no orders. Live trading stays a stub (`docs/GO_LIVE.md`).
- **Language-model forecasts cannot be backtested** (the model has read about the past). They are tested forward
  only, by the paper bot. Everything backtested here is mechanical: rules on prices, time, category and structure.

## Rules for judging a result (do not relax these)

0. **Two samples are valid, nothing else.** `--sample random` (default): every market that ever traded, in the
   download's fixed shuffle; mostly tiny markets with wide quotes. `--sample liquid`: the census of busy markets,
   where a market is seen only from the bar at which it had traded the census level (`cumvol`), so the
   biggest-first download carries no hindsight. Never pass `sample="all"` to judge a rule, never filter on
   `tot_vol`: use `cumvol` or `dvol7`, which are known at the bar. Rounds r01 to r04 (report 3.1 to 3.5) used
   neither and are superseded.
0b. **Days to close come from the schedule.** Kalshi rewrites `close_time` when a market closes early, so
   `dte` uses the expected expiration for markets that can close early (`markets.early`, `markets.exp_ts`;
   `panel.describe` prints "SCHEDULE MISSING" if the back-fill has not reached a category). Holding times in
   `analyze_rule.py` and `portfolio.py` use the real close.
0c. **Lopsided bets get the tail test, not a t-statistic.** For anything bought above about 85c run
   `research/analyze_rule.py`: losing events against the break-even loss rate with an exact upper bound.
1. **Costs in.** Taker entries pay the ask plus Kalshi's fee, 0.07 × p × (1 − p) per contract (some series carry
   a different multiplier: `series.fee_multiplier`). Maker entries are counted only when a later bar shows the
   price trading through the order, and are reported separately from taker results.
2. **Out of sample.** Choose settings on markets that closed before 2026-04-01; report the result on markets
   closing from that date. The date was fixed on 2026-11-18 from the calendar alone, before any result was seen:
   Kalshi's history is concentrated in 2026 (for Economics, 43% of events closed before April 2026; for Weather,
   58%). A strategy that only works in-sample is not a result. Do not move the date.
3. **Errors clustered by event.** Markets of one event move together. t-statistics use one observation per event
   (or event-day), never one per market.
4. **Multiple testing.** With N variants tried in a family, the best is expected to look good by luck. Require
   out-of-sample t above 3 for a first claim, and say how many variants were tried.
5. **Capacity.** Report the dollars actually available at the quoted price where the data allows; a rule that
   earns 5% on $3 of depth is not a strategy.
6. **Nothing reaches the paper bot's config** without the evidence written into the report first, and nothing
   ever loosens `safety` or `sizing` limits.

## Background jobs

**MOVED TO THE USER'S PC on 2026-11-18, about 7:00 pm CST.** The project now lives at
`E:\Coding\PredictionMarketTrader` in its own repository (github.com/NoMansion/PredictionMarketTrader); the
branch on the stock trader's repository is no longer used. The cloud container's `data/` did not come along
(it is not committed), so on the PC:

- The Kalshi history is being downloaded again into `data\kalshi_hist.db`. The order is the same fixed shuffle,
  so a finished category gives the same random sample as before. Until a category's pass is complete locally,
  the rounds in `research/results/` cannot be re-run on it.
- The paper ledger `data\pmt.db` starts empty: the first local cycle opens a NEW paper account.
  `reports/forward_log.csv` keeps the cloud account's rows (append, never overwrite).
- Start what is not running: **`research\start_jobs.ps1`** (history download; add `-PaperLoop` for the paper
  loop, `-Stop` to stop both). Python is `.venv\Scripts\python.exe`, not `python3`.
- **PAPER TRADING RUNS ON THE PC since 3:46 am CST, 2026-11-19** (the user: "Start, PC settings", then "can
  you use both settings or combine them to the best option"). The settings, fixed from this cycle on:
  the forecaster as in `config.yaml` (model opus, 3 runs, high effort, quiet window 5:15 to 6:20 pm): these
  decide the quality of each forecast, and changing them breaks the track record. The cadence is a free dial
  (it only decides how many questions are forecast per day): every 6 hours, between the cloud's 3 h and the
  PC's original 8 h; `research\start_jobs.ps1 -PaperLoop` uses it by default. 6 h is about 48 Claude runs a
  day; go to 8 h if the user's Claude usage is short, down to 4 h if it is plentiful. The first 20 forecasts
  (cloud: 2 runs, medium effort) are a separate block of the record: compare the two blocks, do not pool them
  without saying so. The first PC cycle was started by hand at 3:46 am; the loop is started once it finishes
  (two writers cannot share `data\run_cycle.log`). The paragraph below is the state just before this.
- **A CYCLE EVERY 2 HOURS, WIDENING BY ITSELF** (the user, 4:35 am CST 2026-11-19: "1 or 2 hours, but if Claude
  is going to use up its limit then can you switch it to a larger time window"; they also said the stock
  trader will eventually not need Claude). `runtime.cycle_every_hours: 2`, `cycle_max_hours: 12` in
  `config.yaml`; the loop reads them before every decision. 2 and not 1: a cycle with 8 questions takes about
  40 minutes. Two guards on the limit:
  1. In the loop (`scripts/paper_loop.py`): after a cycle in which the forecaster hit a limit, was answered
     by a model other than the configured one, or failed on every question, the gap doubles (to 12 h at
     most); it halves again when forecasts come through. Current gap: `data\paper_loop_state.json` and the
     loop's lines in `data\run_cycle.log`.
  2. At each check-in, BEFORE the limit is reached: read the plan's usage (the app tool
     `mcp__ccd_session_mgmt__get_usage` if the session has it). Raise `cycle_every_hours` one step (2, 4, 6,
     8, 12) when the 5-hour window is at 80% or more, or when a weekly window's percent used is more than
     10 points ahead of the share of the week that has passed; lower it one step when every window is
     comfortably behind. Change only that one key, commit it, and write the numbers into the progress log.
  Usage at 4:35 am CST Nov 19 (week resets Sunday Nov 22, 4:00 pm CST): 5-hour 54%, weekly all models 40%,
  weekly Fable 65%. The paper loop's forecasts run on Opus (the all-models figure). The Fable figure is the
  tight one and is spent by the interactive sessions and the check-ins, not by the paper loop: keep
  check-ins short when nothing has changed.
- **8 QUESTIONS PER CYCLE from the second PC cycle** (the user, 4:14 am CST 2026-11-19: "Feel free to use more
  than 4 questions"). `universe.max_candidates_per_cycle: 8` in `config.yaml`, with the measurements behind it.
  Not a break in the record (the forecaster is unchanged), but it reaches further down the ranking, so more
  forecasts will be on markets too thin to trade (scored, not traded). If usage runs short, lower this
  before touching runs or effort.
- **VARIANT ACCOUNTS since 2026-11-19, about 4:00 am CST** (the user: can it be done "based on a claude
  analysis of the liklihood of an event occuring", then "yes add that account along with any variations of
  tests that you can"). Eight extra paper accounts in `variants.yaml` reuse the main account's forecasts (no
  Claude usage) under other rules: Claude alone (three versions), a 50% blend, taker versions, and two controls
  (against Claude; a direction Claude did not choose). Code `src/variants.py`, ledgers `data\variants\`, run
  by the paper loop after every cycle (`scripts\run_variants.py`). Standings: `scripts\run_variants.py
  --report`; quote them in the report at check-ins, always with the two controls beside them and the number
  of accounts. Do not change or remove a variant (it breaks its record): add a new name. A variant's settings
  never go into `config.yaml` without the evidence in the report and the user's yes. Their record starts with
  the first PC cycle; the cloud's 20 forecasts were not replayed (the order books of that moment are gone).
- **Before the start** (3:40 am CST, 2026-11-19). The cloud
  loop was stopped for good at 3:37 am and the cloud session at 3:38 am; the final ledger is in `data\`.
  The user's "do not start paper cycles yet" (3:20 am) still stands until they say go, and they have to
  choose the settings first: `config.yaml` (3 runs, high effort, a cycle every 8 h, quiet window around
  the stock trader's evening job) or the cloud's (`data\cloud_config.yaml`: 2 runs, medium effort, every
  3 h, no quiet window). A change is a break in the track record; with 20 forecasts and none resolved,
  now is the cheapest moment for one. Start with `research\start_jobs.ps1 -PaperLoop` (add
  `-Config data\cloud_config.yaml -Every 3` for the cloud's settings). A local loop started at 3:03 am
  at the user's earlier request was stopped at 3:22 am after one forecast; that ledger is in
  `data\_pc_before_bundle\` and is not part of the record.
- **The data bundle is in place** (3:34 am CST, 2026-11-19): `data\` now holds the cloud's snapshot of 3:06 am:
  the paper ledger (5 cycles, 20 forecasts, 4 resting orders, $1,000; last cycle 1:07 am), the observation
  log, the event flags and the history database the report's rounds saw. All four databases passed SQLite's
  check; `status.py` shows the four resting orders; the download resumed on the cloud's database
  (Commodities census). What the PC had before is in `data\_pc_before_bundle\` (its own history database,
  285 MB, behind the cloud's except in Commodities, and the one-forecast ledger of the stopped cycle): nothing
  reads it, and it can be deleted once the user agrees.
  THE LEDGER HERE IS A SNAPSHOT: the cloud loop is still running and its ledger moves on. Before the first
  paper cycle on the PC, ask the cloud session for a fresh `pmt.db` and `shadow.db` (or accept the gap and
  say so in the report), and have its loop stopped: one ledger only.
- The `claude` command is installed in `.tools\claude` (2.1.328; `forecaster.executable` points at it) and
  signed in to the user's subscription since 3:00 am. The local config is `config.yaml` itself (quiet window
  around the stock trader's evening job, 3 runs, high effort, a cycle every 8 h); the cloud cycles used
  `data/cloud_config.yaml` (2 runs, medium effort): which one the PC continues with is the user's choice, and
  a change is a break in the track record.
- New cloud commits reach this repository with `scripts\sync_from_github.ps1` (a git merge). Merged so far:
  up to the cloud's 3:08 am commit ("migration to the PC").
- **A restart of the PC stops both jobs and nothing starts them again** (it was restarted at 10:40 pm and
  1:38 am on the first night). Run `research\start_jobs.ps1 -PaperLoop` after a restart, at every check-in.
  A Task Scheduler entry "at log on" would do it unattended: not created, it needs the user's yes.
- The keep-awake task and the container notes below applied to the cloud machine only.

What follows was written for the cloud container (Linux). Start whatever is not running, at any time:
**`bash research/start_jobs.sh`** (from `PolymarketTrader/`). It
starts the Kalshi history download (resumable; log `data/kalshi_download.log`) and the paper loop
(`scripts/paper_loop.py`, one cycle every 3 h by the ledger's clock; log `data/run_cycle.log`). After each cycle
the loop also runs `scripts/shadow_longshot.py`: the forward observation log of the longshot rule (no orders; its
own file `data/shadow.db`; `python3 scripts/shadow_longshot.py --report` for the summary to quote in the report).

Download order per category: list its settled markets (with scheduled end dates), back-fill schedules for older
listings, 2,500 random markets' bars, then the census (every market with 5,000+ lifetime contracts, biggest
first, at most 8,000). `research/panel.py` works out by itself how far down the census is complete.

**THE MACHINE SLEEPS WHEN THE SESSION IS IDLE** (found 20:21: `uptime` showed 3 minutes; the download's last write
was 2 minutes after the previous turn ended). Detached jobs do not keep it awake. A task tracked by the session
does. So EVERY check-in, after `start_jobs.sh`, must leave this running as a Bash call with
`run_in_background: true` and `timeout: 7200000`:

```
cd /home/user/StockTrader/PolymarketTrader && n=0; while pgrep -f "research/kalshi_download.py" > /dev/null && [ $n -lt 115 ]; do sleep 60; n=$((n+1)); done; date -u +%T; uptime; tail -1 data/kalshi_download.log | cut -c1-160
```

It ends after about two hours (or when the download stops) and its completion notice is the cue to restart both.
The "PolymarketTrader job watchdog" check-in (minute 21) should do the same: run the script, then leave the
keep-awake task running.

The paper loop is the forward test of Claude's forecasts (family 17). Its ledger is `data/pmt.db` (not committed);
`python3 scripts/export_forecasts.py` writes the durable copy, `reports/forward_log.csv`, which IS committed: run it
and commit at every check-in. `data/cloud_config.yaml` is config.yaml with: no quiet window, 2 runs, medium effort,
4 markets, 40 books, 2 s pacing. If `data/` is gone (new container): recreate that file, run the script, and
expect the listing to take about 1.5 hours per category before bars arrive (about 2,500 markets an hour when
Kalshi throttles, 9,000 when it does not). The first cycle after a loss of `data/` starts a NEW paper account:
say so in the report, and keep `reports/forward_log.csv` (append, do not overwrite the old rows).

The download writes `data/kalshi_hist.db` (tables `series`, `markets`, `candles`). It is not committed: Kalshi's
terms do not allow redistributing its data. Commit code, aggregated results and reports only.

## Progress

- 2026-11-18 16:59 UTC: download started; restarted 17:08 in priority order (Economics, Politics, Companies,
  Commodities, Science and Technology, Elections, Health, World, Financials, Mentions, Entertainment, Crypto,
  Social, Climate and Weather). Each category: list its settled markets, then daily bars for its 6,000 biggest.
- 17:10: Kalshi adapter (`src/kalshi.py`) built, tested offline against real payloads, made the default venue.
  NOT yet run live end to end: do `python scripts/run_cycle.py --scan` first (pause the download while it runs,
  the two share Kalshi's rate limit: `pkill -STOP -f kalshi_download`, then `pkill -CONT -f kalshi_download`).
- 17:12: backtest engine committed (`research/panel.py`, `backtest.py`, `families.py`, `run_sweep.py`). Checked
  on a made-up exchange: with fair prices no taker rule passes; a planted bias is found on the right side.

- 17:26: first live Kalshi scan ran past 8 minutes under rate limiting. The adapter now keeps the listing on disk
  (`data/kalshi_listing.json`, refreshed at most every 20 h) and resumes a cut-off scan. A slow background scan
  is filling it: check `python3 -c "import json;s=json.load(open('data/kalshi_listing.json'));print(bool(s.get('finished')),len(s['markets']))"`.
  When it says True, run `python3 scripts/run_cycle.py --config data/cloud_config.yaml` (cloud config: no quiet
  window, 2 runs, medium effort, 4 markets, 2 s pacing; recreate it from config.yaml if data/ was lost).
- 17:45: round `r01_economics_prelim` on the first 1,476 Economics markets: all rules thin (411 events). Report
  section 3.1. The download reaches about 9,000 markets an hour when Kalshi is not throttling.
- Sample split fixed at 2026-04-01 (see rule 2 above). Account replay simulator added (`research/portfolio.py`).

- 17:55 (check-in 1): round `r02_economics_2760`, report 3.2. 0 pass, 19 leads (all "buy NO", not significant in
  sample, concentrated in "above X" markets of 2025-26), 18 reliably losing (taker YES on favourites; taker NO
  against longshots). Engine gained fixed-horizon snapshots (family 1b) and an event-weighted statistic; `pass`
  now needs both weightings. Both background jobs alive (download at Economics bars 3,000 of 4,000; bot listing
  partial).
- New backlog items from r02: (a) test "buy NO at 20-80c" and "favourites lose" in every other category as it
  lands; (b) split by strike_type greater / less / between wherever "less" exists; (c) year-by-year table for
  any lead; (d) does the favourite loss shrink with a resting entry and near the close?

- 18:00: round `r03_economics_4000` (Economics first pass complete: 3,215 markets, 845 events), report 3.3.
  0 pass, 9 leads, 15 lose. Solid: taker NO against 5-20c longshots loses; taker YES on favourites loses. Leads to
  re-test on other categories: buying thin 5-20c longshots; NO on markets listed 2-7 days ago. Download has
  moved on to Politics (2,526 series to list, then bars).

- 18:52 (check-in 2): slow listing scan stopped (it was starving the download); the bot's listing was built from
  the full snapshot captured at 11:33 (4,489 markets, valid 20 h; after that the adapter rescans by itself, slowly).
  FIRST LIVE KALSHI CYCLE DONE: 4 forecasts (3 low confidence, not traded), 1 paper order: resting NO $20 @ 0.65
  on KXGOVTSHUTDOWN-26DEC12 (Claude 0.205, market 0.345). Paper loop started, every 3 h. Commodities removed from
  the bot's categories. Download restarted with `--first-pass 2500` (Politics in progress).

- 19:55 (check-in 3): both jobs were dead (worker restart about 19:10); restarted with `research/start_jobs.sh`;
  watchdog trigger added. No new round (Politics has only 560 markets with bars). Year-by-year breakdown of the
  two Economics leads: both dropped (report 3.4). Rule for the future: any lead gets a year-by-year and
  concentration table before another round is spent on it.

- 20:55 (check-in 4): keep-awake confirmed (machine up 32 min, Politics 680 -> 1,840 markets). Round r04 (Politics;
  Economics + Politics): 1 pass, 49 leads, 50 lose, the same "dear side loses" pattern in both categories.
  THEN FOUND THE SAMPLING FLAW (report 3.5). Download switched to a fixed random order (`rnd` = crc32 of the
  ticker), minimum volume 1, first pass 2,500 random markets per category, Economics first. Panel uses the
  random sample only. Next round must be on the random sample and must say whether the r02-r04 pattern survives.

- 4:40 pm CST (check-in 5, 22:40 UTC): r05/r06 superseded the same hour by **r07** (after the schedule fix, with
  families 16 to 26). Random Economics and Politics: 0 pass; the r02-r04 "dear side loses" pattern is gone
  (report 3.6). Busy markets, Economics + Politics at 45,000 contracts: 22 pass, 49 leads, all "buy NO where
  YES is cheap" (report 3.7). The 5-cent rule taken apart (3.8): tail test passes both halves; small in dollars;
  all losses in 2025-26. Forward observation log started (3.9). Paper bot config NOT changed: the rule needs
  prices above `sizing.max_price`; left as the user's decision (second paper account).
  Download: Economics census down to 5,000 contracts in progress, then Politics random pass and census, then
  Companies onward.

- 4:53 pm CST (check-in 6): nothing new had landed since 4:40 pm. Calibration curve added (report 3.10). Volume
  gradient seen in family 23 (NO against YES at 0-5c, taker, in / out of sample): under 1,000 contracts so far
  +0.2% / -3.2%; 1,000-10,000: -0.4% / -0.6%; 10,000-100,000: +0.5% / +0.8% (random sample, thin). So the edge
  starts somewhere above 10,000 contracts: test it properly when the Economics census reaches 5,000
  (`--sample liquid` with no `--min-cumvol`), and write the answer into the report.

- 5:48 pm CST (check-in 7): CONTAINER RESTARTED about 5:45 pm; `data/` survived; jobs and keep-awake restarted.
  Economics census complete to 5,000 contracts. Round r08 (report 3.11): 5-cent rule holds at that level (tail
  test passes both halves; 2024 a losing year); the wider NO edge (5-35c) fades to zero at this level. Politics
  random pass resumed, then its census, then Companies.

- 5:53 pm CST (check-in 8): jobs alive, nothing new landed. Listed the rule's losing bets (report 3.11): macro
  data surprises, three of nine from January 2024 releases; Politics losses are "X happened before the date".
  Idea for the backlog: cap the rule's exposure per release month / per underlying statistic, and test whether
  skipping "data release above X" thresholds within N standard moves helps (needs the release history; later).

- 6:52 pm CST (check-in 9): second container restart about 6:40 pm, data intact. Round r09 (report 3.12):
  random Politics complete, 1 pass of 2,780 (chance). Busy at 15,000 contracts, both categories: 60 pass, all
  buy-NO. BUT the 5-cent rule as a TAKER fails the tail test on Politics alone (2025: -1.6% per bet); resting
  passes. Politics census still descending from 14,452 to 5,000: re-run `--sample liquid --categories Politics`
  when `research/panel.py`-level check shows it complete, then Companies.

- 8:07 pm CST (check-in 10): Politics census complete to 5,000. Round r10 (report 3.13): at 5,150+ contracts in
  both categories, 26 pass / 117 leads, all buy-NO, BUT paying the ask for NO is worth about zero in every band;
  the 5-cent TAKER rule fails in Politics (+0.14% per bet) and is carried by Economics; the RESTING version
  passes pooled (fill is modelled). Closing-window check: nothing special in the last 1-3 days; hourly bars
  dropped. Status section of the report rewritten. Download now on Companies.
  BUILT 8:10 pm: resting-fill tracking in `scripts/shadow_longshot.py` from Kalshi's public trades (queue-aware;
  3-day window). `--report` prints the fill rate and, once settled, the return of the filled ones: quote it in
  the report at each check-in once more than about 20 are decided.

- 8:55 pm CST (check-in 11): Companies too small (79 events). Commodities moved behind the bot's categories;
  download now on Science and Technology. Report 3.14: the WIDE resting rules (NO against YES up to 35-50c) have
  positive means per bet but LOSE in the account replay (gains sit in huge multi-outcome events; event-weighted
  t negative). Calibration gap per event: solid under 5c, gone above 10c out of sample: the "corrected starting
  price" idea for the bot is withdrawn. Lesson for judging: always run `analyze_rule.py` (replay) and read
  `oos_evt` before calling anything usable.

- 9:55 pm CST (check-in 12): downloader bug fixed (a ticker with "%" was retried for ever and held the Science
  and Technology random sample at 811 markets); Science and Technology still downloading (about 2,165 of 3,906
  with bars). New family 27, `research/event_baskets.py`: NO on every outcome of an event whose YES bids add up
  to more than 1. On the "no numeric strike" proxy it LOSES (most such events are not exclusive: "by June" and
  "by December"). Fetching Kalshi's own `mutually_exclusive` flag for the candidate events (file `data/kalshi_events.db`) to
  test the exclusive ones alone: result goes in the report as 3.15.

- 10:06 pm CST: family 27 done (report 3.15). With Kalshi's flag (154 of 405 candidate events are exclusive):
  bids of an exclusive event's outcomes add up to 1.00-1.02, basket locked at about -0.9% after fees; reached
  1.05 once in five years. No arbitrage. Flags are in `data/kalshi_events.db` (not committed).

- 10:53 pm CST (check-in 13): Science and Technology complete. Round r11 (report 3.16): random 0 pass; busy
  0 pass / 11 leads (all resting NO). 5-cent rule: taker fails there too (+0.08%); pooled over three categories
  the RESTING version passes both halves (+1.98% per bet, 1,270 events), the TAKER fails both. Fixed a crash on
  a missing title. Download is listing Elections (2,601 series), then Health, World.

- 11:56 pm CST (check-in 14): Elections still listing. FOUND AND FIXED A FLAW IN `portfolio.entries`:
  same-day bets were ordered by return, losers first (pessimistic look-ahead). All replay figures of report 3.8
  to 3.16 were too low; corrected table in 3.17; means, t and tail tests were never affected. New tool
  `research/resting_variants.py`: 5 depths x 3 windows for the resting NO bid, all 15 pass the tail test in both
  halves (report 3.17): no setting to tune.

- 12:54 am CST Nov 19 (check-in 15): Elections random pass complete, census at 22,000 contracts and descending.
  Round r12 (report 3.18): Elections shows NO longshot effect of its own (0 pass; 5-cent rule +0.07% taker, +0.91%
  resting, few bets). Four categories pooled at 23,000+: both versions pass the tail test in both halves.
  Next: Elections to 5,000, then Health and World (small), then pooled five/six-category rounds at 5,150.

- 1:57 am CST Nov 19 (check-in 16): ALL SEVEN BOT CATEGORIES DOWNLOADED. Round r13 (report 3.19), pooled busy
  sample 17,522 markets / 5,316 events: 17 pass (16 buy NO against cheap YES). 5-cent rule pooled: RESTING passes
  both halves (+1.85% per bet; replay +3.6% / +14.8% a year); TAKER fails (+0.43%). The effect lives in
  SINGLE-MARKET events (taker 5 losses in 696) and Economics; absent in Elections and inside multi-outcome
  events. `ev_total` now counts the markets the exchange listed (was: markets in the sample).
  Download has moved to Commodities (random 2,500 then census, capped at 8,000), then Financials etc.
  NEXT IDEAS: (a) 5-cent rule restricted to single-market events with <= 30d and by category; (b) the same
  breakdown for YES 5-20c; (c) forward log: add single-market flag to `scripts/shadow_longshot.py`.

- 2:53 am CST Nov 19 (check-in 17): family 28 (stand-alone questions), report 3.20: strong in sample (t 4-16,
  280-600 events), positive with no loss since April 2026, but every rule is THIN out of sample (10-87 events):
  not a pass, and the split / 100-event bar stay where they are. `scripts/shadow_longshot.py` now records the
  event's size (`ev_markets`). Commodities census in progress (about 2,900 of 8,000).

- 3:10 am CST Nov 19: THE USER ASKED TO MIGRATE THE WORK TO THEIR PC ("under the predictionmarkettrader
  project"). This session cannot reach the PC (no shared folder). Prepared instead: `docs/MIGRATE_TO_PC.md`
  (three steps), `scripts/sync_from_github.ps1`, path-independent `scripts/run_cycle_hidden.vbs`,
  `requirements-research.txt`, README updated; a data bundle (paper ledger, observation log, history database;
  snapshot 3:06 am) handed over as a file in the conversation. The cloud jobs KEEP RUNNING until the user says
  the PC copy is running; then stop the cloud paper loop (one ledger only) and ask whether the hourly check-ins
  should stop too. Do not stop them unasked.

- 2:45 am CST Nov 19 (ON THE PC, first local check-in): the local download had stalled at 10:34 pm on one archive
  ticker, `GPT%-23DEC31` (Kalshi answers 400 for it however the `%` is sent), retrying it every 16 s; then
  the PC was restarted. Fixed: paths are URL-escaped (`src/kalshi_http.py`) and any 4xx except 429 is final
  for a market (`candles_done = 4`). Restarted at 2:36 am. Local history so far: Economics 8,881 markets with
  bars, Politics 7,023, Commodities 10,120, Companies 179, Science and Technology in progress. NOT yet
  checked: whether each category's local random pass and census are complete (`research/panel.py`) before
  any round is re-run here.

- 3:37 am CST Nov 19: THE PC COPY IS RUNNING (E:\Coding\PredictionMarketTrader; the user sent its status: 176
  tests pass there, cloud data unpacked, its own download and hourly checks started). THE CLOUD PAPER LOOP IS
  STOPPED FOR GOOD: `data/PAPER_LOOP_MOVED_TO_PC` makes `start_jobs.sh` skip it. Do not restart it. The ledger
  and observation log were last written at 1:20 am CST (cycle 5), so the 3:06 am snapshot on the PC is
  complete; final copies were handed over anyway. `reports/forward_log.csv` here is final at 20 forecasts.
  OPEN, asked of the user: should the cloud download and the hourly research check-ins stop as well, now that
  the PC runs its own? Until answered they continue (history download + rounds), without the paper loop.

- 3:38 am CST Nov 19: **THE CLOUD SESSION IS STOPPED, at the user's instruction ("stop the cloud session").**
  Both scheduled tasks are disabled (research loop, job watchdog), the history download and the paper loop are
  killed, nothing is left running here. The project now lives on the user's PC at
  E:\Coding\PredictionMarketTrader, which has the data, runs its own download and checks, and holds the only
  paper ledger. Do not restart anything in the cloud unless the user asks. From here on, the PC copy's
  `research/STATE.md` is the control sheet; this file is a record up to the handover.

- 3:40 am CST Nov 19 (ON THE PC): the cloud session's FINAL ledger and observation log are in `data\`
  (same five cycles and 20 forecasts as the 3:06 am snapshot, which is kept in
  `data\_ledger_snapshot_0306\`). The cloud session is stopped: THIS FILE IS NOW THE CONTROL SHEET and the
  PC holds the only paper ledger. No paper cycle has run here yet: waiting for the user's word and their
  choice of forecaster settings (see "Background jobs"). The four resting paper orders are not being
  marked while no loop runs.

- 4:20 am CST Nov 19 (ON THE PC): FIRST PAPER CYCLE ON THE PC done (3:46 to 4:15 am, 29 minutes; 3 runs, high
  effort): 4 forecasts, usage $0.60 to $0.89 each at list price; one resting order (YES on Hawaii visitor
  arrivals above 9.6 million, $20 at 75c; Claude 0.85, market 0.76); two more had enough edge but the daily
  budget (10% of equity deployed in 24 h, resting orders included) was used; one was low confidence. The
  account has 5 resting orders, $1,000. VARIANT ACCOUNTS RAN FOR THE FIRST TIME (8 accounts, 42 s, no
  Claude calls): each was handed 8 forecasts, the 4 new ones and the 4 of the cloud's 1:07 am cycle (2 runs,
  medium effort; still inside the 6-hour forecast age limit, so they were traded at current prices: say so
  when quoting the variants). Claude-only accounts placed 5 resting orders, the 50% blend 3, the main rule as
  a taker none, Claude-only as a taker bought 3 at once (-$2.65 marked at the bid). The log-on task was
  test-fired and started the paper loop: next cycle about 9:46 am, 8 questions, variants after it.
  NOTE FOR CHECK-INS: this session and the hourly check-in session can work in the repository at the same
  time. Stage your own files by name (never `git add -A`): at 4:15 am the r15 result files of a check-in in
  progress were swept into commit 7f28a89, whose message is about something else.

- 4:30 am CST Nov 19 (ON THE PC): THREE WIDE ACCOUNTS ADDED (the user: budget "and other variables" are worth
  testing; "Do it now"). `claude_only_wide`, `claude_only_wide_edge1`, `blend30_wide` in `variants.yaml`: the
  daily budget and the category and total exposure caps are lifted, the stake per market and the safety
  stops are kept. They record every trade their rule wants; they are NOT candidates for the paper bot. Started
  on the same 8 forecasts as the others, 12 minutes later (prices of 4:29 am). Eleven variants plus the main
  account = twelve. STILL TO BUILD, once a few dozen markets have settled: a replay tool that takes a wide
  account's record and applies a daily budget, an edge threshold and a stake size after the fact (return per
  dollar staked, worst stretch), so that no further account per setting is needed.

- 4:38 am CST Nov 19 (ON THE PC): paper loop restarted on the adaptive cadence (2 h; next cycle about
  5:46 am). 194 tests.

- 5:15 am CST Nov 19 (check-in): both jobs alive; last cycle (3:46 am) ok, next about 5:46 am. Report 3.21:
  r15 (Commodities, run at 4:13 am but not written until now) and r16 (Financials, random sample). Commodities
  alone is too small (all rules thin); eight categories pooled: 5-cent rule RESTING passes both halves (+1.77%
  per bet, replay +3.3% / +12.1% a year), TAKER fails, as in 3.19. Financials random: 0 pass, 8 lose (taker NO
  against YES at 50c or less, -13% to -16% out of sample). Financials census still downloading (46,000 markets
  with bars at 5:10 am). Usage: 5-hour 0%, weekly all models 40%, weekly Fable 66%, with 51% of the week past.
  `cycle_every_hours` LEFT AT 2: the all-models window (which the paper loop spends) is 11 points behind; the
  Fable window is 15 points ahead, but the loop does not spend it and the user set 2 h at 4:35 am with the
  same figures in view. Check-ins spend Fable: stop early when nothing has landed.

- 6:30 am CST Nov 19 (check-in): both jobs alive; third PC cycle (8 questions) running since 5:48 am. Report
  3.22: r17 (Financials busy sample; nine categories pooled) and r18 (Mentions random). Financials busy: every
  rule thin; the 5-cent rule LOSES there (-1.3% per bet both entries, 9 losing events, weekly Treasury yield
  and Nasdaq ranges). Nine pooled: 18 pass; 5-cent RESTING still passes both halves (+1.59% per bet, replay
  +2.7% / +17.6% a year), TAKER fails. Mentions random: YES overpriced in every band (49 losing rules, all buy
  YES); NO at 20-80c resting is a lead (t 2.2; tail test passes both halves), taker is not (t 1.0); capacity
  about $50 to $90 a week per market: A LEAD, the busy sample decides. Usage: 5-hour 5%, weekly all models
  40%, weekly Fable 67%, with 51% of the week past. `cycle_every_hours` left at 2 for the reason given at
  5:15 am (the loop spends the all-models window, which is 11 points behind; Fable is 16 ahead and is spent
  by check-ins, so: stop early when nothing has landed).

- 7:25 am CST Nov 19 (check-in): both jobs alive; third PC cycle (5:48 am) ended ok, 32 forecasts, none
  resolved; next cycle about 7:50 am. Report 3.23: r19 (Mentions busy sample) and r20 (Entertainment random).
  Mentions busy: every rule thin (two daily bars per market); NO at 20-80c is NOT confirmed there (taker
  -0.6% per bet, resting +5.8% but replay flat out of sample, tail test fails both halves, 50 events), with
  real capacity ($16,700 a week median): the 3.22 lead is closed as a curiosity of $50-a-week markets.
  Entertainment random: 0 pass, 0 leads, 9 lose (all cheap YES); NO does not collect it. Usage: 5-hour 14%,
  weekly all models 41%, weekly Fable 67%, with 52% of the week past: `cycle_every_hours` left at 2, same
  reason as 5:15 am. E: 50 GB free, C: 30 GB.

- 8:15 am CST Nov 19 (check-in): both jobs alive; fourth PC cycle running since 7:48 am; 34 forecasts, none
  resolved. Entertainment census finished 7:50 am; download is listing Crypto. Report 3.24: r21 (Entertainment
  busy sample, 7,385 markets, 1,947 events): 18 pass, 68 leads, 113 lose. The 5-cent rule does NOT work there
  (taker +0.12% per bet, tail test fails both halves; resting passes in sample only). But the WIDER NO rules
  do, for the first time with the replay and the tail test on their side in both halves: NO against YES at
  5-35c resting +7.3% per bet (replay at 0.5% stake +7.6% / +25.0% a year, drawdown under 3%), taker +3.3%
  (+2.8% / +12.1%); also YES 5-10c resting and "10-25c after a 3c fall in 7 days". Caveats written in 3.24:
  one category of eleven, event t 2.2 to 3.3 out of sample, fill model untested there, capacity about $100
  to $200 per market (median $2,140 traded a week). A LEAD, not usable. Usage: 5-hour 19%, weekly all models
  42%, weekly Fable 68%, with 53% of the week past: `cycle_every_hours` left at 2, same reason as 5:15 am.
  E: 49.5 GB free, C: 29.8 GB.

- 9:20 am CST Nov 19 (check-in): both jobs alive; fourth PC cycle (7:48 am) ended ok, 40 forecasts, none
  resolved; next cycle about 9:50 am. Crypto random pass finished 8:31 am; census in progress. Report 3.25:
  r22 (Crypto random): 227 markets, all 2,768 rules THIN, nothing to say. Cause: 97% of Crypto markets live
  under 24 hours (median 15 minutes), so they have no usable daily bars; the census (8,000 biggest of
  138,349) is mostly the same markets, so r23 will probably be thin too. Usage: 5-hour 29%, weekly all
  models 42%, weekly Fable 68%, with 53% of the week past: `cycle_every_hours` left at 2, same reason as
  5:15 am. E: 49.4 GB free, C: 29.8 GB.

- 10:20 am CST Nov 19 (check-in): both jobs alive; fifth PC cycle running since 9:51 am; 40 forecasts, none
  resolved. Crypto census finished 9:18 am, Social done in a minute (68 markets, no busy ones), Climate and
  Weather random pass finished 9:38 am, its census in progress. Report 3.26: r23 (Crypto busy: 133 markets,
  104 events, all thin; 5-cent rule 8 events and NO at 5-35c 10 events, neither can pass the tail test:
  Crypto is closed for the daily-bar engine), Social no round (36 events), r24 (Climate and Weather random:
  0 pass, 2 leads that are one rule and flat in sample, 6 lose, all cheap YES as a taker; the 5-cent rule
  FAILS the tail test there in both halves, 3 losses in 2026, capacity $8 to $12 a week). Usage: 5-hour 2%,
  weekly all models 43%, weekly Fable 69%, with 54% of the week past: `cycle_every_hours` left at 2, same
  reason as 5:15 am. E: 49.4 GB free, C: 29.6 GB.

- 11:05 am CST Nov 19 (the user's session): CHECK-INS NOW EVERY 3 HOURS, not hourly (the user: "Yes, every 3
  hours"). Reason: weekly Fable went from 65% to 69% between 4:35 and 11:03 am, about 0.6 points per check-in,
  which reaches 100% on Saturday afternoon, a day before the reset (Sunday 4:00 pm CST); every 3 hours ends
  the week near 84%. The task's prompt now says: the paper loop's gap is paced from the 5-hour and weekly
  all-models windows only (it runs on Opus), and above 90% weekly Fable with more than a day to go a check-in
  does health only. State at 11:03 am: both jobs alive; four PC cycles (3:46, 5:48, 7:48, 9:51 am) all ok,
  48 forecasts (26 low confidence), none resolved; main account $998.30, 2 positions, 3 resting, at its 6
  orders a day; variants $995 to $1,000. MEASURED: a cycle with 8 questions takes 60 to 65 minutes, not the
  40 written at 4:35 am. Usage: 5-hour 15%, weekly all models 44%, weekly Fable 69%, 54% of the week past.

- 12:25 pm CST Nov 19 (check-in, first on the 3-hour schedule): both jobs alive; sixth PC cycle running since
  11:53 am (five before it ok); 49 forecasts, none resolved; main account $998.02. Climate and Weather census
  finished 10:28 am: THE BACKTEST HAS NOW SEEN EVERY CATEGORY. Report 3.27: r25 (Climate and Weather busy:
  7,319 markets but 2.4 daily bars each, 0 pass, all thin). 5-cent rule there: one loss in 164 events, but
  the tail test is not passed in either half, either entry (too few events): not confirmed, stays out of the
  rule's categories. Entertainment lead as a pre-stated test (NO where YES is 5-35c): same sign (+4.4% taker,
  +9.2% resting per bet, replay positive both halves), tail test passes only in sample for resting, fails
  out of sample (64 events): NOT a confirmation. The download now extends the random samples past 2,500 per
  category (same shuffle, still valid). Usage: 5-hour 20%, weekly all models 44%, weekly Fable 70%, with 55%
  of the week past: `cycle_every_hours` left at 2 (all-models 11 points behind; 2 is the floor). E: 49.3 GB
  free, C: 29.6 GB.

## How to run a round

```
cd PolymarketTrader
python3 research/panel.py                               # what has been downloaded so far
python3 research/run_sweep.py --round r01               # every rule of every family -> research/results/r01.csv
```

A round takes a few minutes. Name rounds r01, r02, ... and say in the report which data each one saw (the
panel's first line: markets, events, dates), because the download keeps growing.

## Backlog of strategy families (mechanical, backtestable)

Status: `todo`, `running`, `done` (with the report section), or `dropped` (with the reason).

1. todo: Price-level calibration (favourite-longshot): return to buying YES and to buying NO by price bucket,
   by category, by days to close.
2. todo: Favourites near expiry ("bonds"): 85-99 cents with 1 to 14 days left.
3. todo: Always-No, by category and by event size (many-outcome events).
4. todo: Momentum and reversal: 1, 3, 7-day price change, follow or fade.
5. todo: Deadline decay: "by date" markets drifting to No; buy No early.
6. todo: Ladder consistency: thresholds of one event must be ordered (P(above 3.6) >= P(above 3.7)); trade
   violations. Mutually exclusive sets summing above or below 1.
7. todo: Volume and attention: thin against busy markets; first days after listing; volume spikes.
8. todo: Spread and maker economics: what a resting bid earns by price level and category, with the
   trade-through fill rule.
9. todo: Closing-window effects: last 24 to 72 hours.
10. todo: Opening-price effects: first quoted prices against later ones.
11. todo: Series-specific persistence: does a series that was biased last year stay biased this year?
12. todo: Calendar effects: day of week, month, release-day proximity for economic series.
13. todo: Extremes: prices that jump more than X in a day, continuation or reversal.
14. todo: Combinations: the survivors of 1-13 crossed pairwise (for example favourites x near expiry x maker
    entry x category), then the best triples.
15. todo: Portfolio rules on the survivors: Kelly fraction, per-event caps, capital lock-up, drawdown.
16. todo: Sports and crypto as separate samples (download them after the non-sports set is analysed).

Forward-only (cannot be backtested):

17. todo: Claude forecasts on Kalshi through the paper bot (needs the Kalshi venue adapter, `src/kalshi.py`).
18. todo: Claude as a filter on a mechanical rule (trade the rule only where Claude does not object).

## Next actions

1. Each check-in: `python3 research/panel.py` (what landed), then for every category with a finished pass run
   both samples: `python3 research/run_sweep.py --round rNN_random_<cat> --categories <Cat>` and
   `... --round rNN_liquid_<cat> --categories <Cat> --sample liquid` (default level = as far down as the census is
   complete; use `--min-cumvol 45000` when comparing with report 3.7). `python3 research/round_tables.py <round>`
   prints the tables for the report.
2. **Re-test the 5-cent rule on every new category and at the lower census level** (Economics is being extended
   to 5,000 contracts): `python3 research/analyze_rule.py --sample liquid --categories <Cat> --rule "NO at mid <= 5c,
   <= 30d, spread <= 5c" --side no --entry tk` (and `mk`). A category where it fails is a result too: write it.
2b. **Calibration curve** (report 3.10, 3.14): `python3 research/calibration_curve.py --sample liquid --categories
   <Cat>`; read the per-event columns. Re-measure on each new category. The bot-prior correction is withdrawn.
3. Leads to follow on the busy sample: NO where YES is 5 to 35c, resting (+6% / +6%, t 2.1 out of sample, thin);
   NO at 3 to 10c after a fall of 3c+ (momentum cross). They need more events: wait for more categories.
4. Forward: `tail -20 data/run_cycle.log`; `python3 scripts/shadow_longshot.py --report`; commit
   `reports/forward_log.csv`; one line each in the report.
5. Still to code: sums over mutually exclusive events with Kalshi's own flag (needs `/events`); hourly bars for
   the last two days; exits before settlement (sell the NO at 99c instead of waiting); a combined-portfolio
   replay of several passing rules; sports and crypto samples last.
6. Open for the user: trade the 5-cent rule in a second paper account? Which Claude model for the forecaster?
7. **AS OF 12:25 pm CST Nov 19: NOTHING IS WAITING ON THE DOWNLOAD.** r25 is done (report 3.27) and every
   category has had both samples. The download is only enlarging the random samples (same shuffle): that is
   NOT a reason for a new round at each check-in. Re-run the random rounds once, when the download log shows
   the random-order pass finished for all categories, and only report what changes. Until then a check-in is:
   part A, the forward logs (variants, observation log) once markets have settled, and otherwise one line
   and stop. Left to code, none urgent, one per check-in at most: exits before settlement; a
   combined-portfolio replay; the after-the-fact replay tool for the wide variant accounts (once a few dozen
   markets have settled). Open for the user: second paper account for the 5-cent resting rule; a forward
   observation band for the wide NO rule (YES 5-35c, no orders) in Entertainment and Climate and Weather.
   The text below is the record of what was waited for.
   **Was waiting on the download (as of 10:20 am CST Nov 19):** Climate and Weather census (started 9:38 am; it
   is the LAST category in the download order). It is finished when the download log shows "finished this
   pass" after the 9:38 am "census ... ['Climate and Weather']" line. Then:
   `run_sweep.py --round r25_liquid_climate --categories "Climate and Weather" --sample liquid`, the 5-cent
   rule there (`analyze_rule.py --sample liquid --categories "Climate and Weather" --rule "NO at mid <= 5c,
   <= 30d, spread <= 5c" --side no --entry tk`, and `mk`), the calibration curve, AND the Entertainment lead
   of 3.24 as a pre-stated test: `--rule "NO where YES is at 5-35c"` (tk and mk). Crypto is done (r22, r23:
   all thin, closed for the daily-bar engine, do not pool). Social is too small for a round (36 events).
   Climate and Weather random is done (r24): 5-cent rule fails there. Entertainment is done (r20, r21): its
   wide NO rules are a LEAD (3.24);
   its 5-cent rule fails, so do not pool Entertainment into the 5-cent rule's categories. Mentions is done
   (r18, r19): not confirmed in busy markets; do not pool it either. Rounds done so far: up to r24. Until
   the Climate and Weather census finishes there is nothing new: say so in one line and stop. AFTER r25 the
   mechanical backtest has seen every category: what remains is item 5 above (exits before settlement, a
   combined-portfolio replay) and the forward logs; do not invent rounds. Open for the user: a
   forward observation band for Entertainment (YES 5-35c, no orders) in `scripts/shadow_longshot.py`?
   The nine-category
   list for pooled rounds: Economics, Politics, Companies, Science and Technology, Elections, Health, World,
   Commodities, Financials.
