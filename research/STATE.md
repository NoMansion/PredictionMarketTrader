# Research loop: state

The user asked (2026-11-18, before going to bed) for strategy research to keep running: every strategy family
that can be tested, and combinations of families, with settings varied. This file is what each check-in
reads first. Keep it short and current. Findings go in the report; this is the control sheet.

## NO FABLE USAGE (the user, 3:13 am CST 2026-11-20: "make sure to use opus 5.5. dont use any fable tokens")

- The paper bot's forecaster already runs on Opus (`forecaster.model: opus`; every forecast in the ledger is
  claude-opus-5-5, with Claude Code's own small helper calls on Haiku). Leave it.
- THE CHECK-IN RUNS ON OPUS from the Windows task "PredictionMarketTrader Check-in" (set up 3:55 am CST Nov 20,
  the user: "Implement ... the fable to opus"): every 3 hours at 12:11, 3:11, 6:11 and 9:11, am and pm, it runs
  `scripts\checkin.ps1`, which gives `scripts\checkin_prompt.md` to the Claude program headless with
  `--model claude-opus-5-5` and no fallback model (if Opus is unavailable the run fails rather than answering on
  another model). Every run's answer, the models really used and the cost: `data\checkin\<time>.json`; one line
  per run in `data\checkin.log` (a line saying OTHER MODEL USED is a fault: tell the user); its last line is
  shown as a Windows notification (not a phone push). The plumbing test at 3:51 am used claude-opus-5-5 only.
- The app's own scheduled check-in (`prediction-market-research-checkin`) stays SWITCHED OFF: its runs started
  on the app's default model, Fable 5.2, and the task record has no model setting. Do not switch it on.
- Any Claude session in this project: run on Opus 5.5, never Fable.
- Until noon Nov 20 the user's main session also has one-shot reminders (it runs on Opus): they check that the
  Windows check-in ran, and at about 12:23 pm write the user a morning summary. They live only in that session.
**Report:** `reports/2026-11-18_strategy_research.md` (create on first results; add a dated section per check-in).

## KEEP TRYING THINGS (the user, 5:25 am CST 2026-11-21: "Keep testing and trying things indefinitely")

Before that: "Yes make both of those and anything else possible for testing. We ar under no time constraint and
want to to find the best possible source of risk averse money making". So a check-in with nothing new to report
does NOT stop early any more: it takes the first open item of the "Ideas queue" (below "Next actions"), runs it,
writes the result (pass or fail) in the report and the queue, and adds any new idea the result suggests. One item
per check-in, backtests and cheap code only. New PAPER accounts (rules.yaml, variants.yaml) are covered by this
instruction when the backtest supports them: add a new name, never change an old one, write the reason here.
Still NOT covered: the main account's config, the forecaster's settings, real money, standing PC changes, and
more Claude usage than the paper loop's own plus the capped filter account (rule_5c_busy_claude, 2 questions a
cycle). If the paper loop's gap has widened (data\paper_loop_state.json above 2 h: Claude's limit was hit), do
health only.

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
  - The check-in: the Windows task "PredictionMarketTrader Check-in", every 3 hours, headless on Opus 5.5 (see
    "No Fable usage" at the top; README "Running it unattended"). Each run is a new session that knows only its
    prompt and this file: keep this file current. It runs while the user is logged on; a run missed while the PC
    was off runs when it is next on (StartWhenAvailable). Until 3:14 am Nov 20 the check-in was the Claude app's
    scheduled task (hourly, then every 3 hours from 11:05 am Nov 19, the user: "Yes, every 3 hours"), which
    spent the weekly Fable allowance; it is off. UPDATE MESSAGE EVERY RUN (the user, 11:10 am Nov 19: "can you
    send an update message every check in"): the run's last line, shown as a Windows notification.  - The Windows task "PredictionMarketTrader Jobs" runs `scripts\start_jobs_hidden.vbs` when the user logs
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

- 1:20 pm to 2:41 pm CST Nov 19: EVERYTHING PAUSED at the user's word ("Pause", "Everything"), then resumed
  ("Resume"). Both jobs stopped, the check-in and the log-on task switched off; at 2:41 pm all switched back on
  and both jobs restarted; a paper cycle began at once (the last had started at 11:53 am). Check-ins now send
  their own one-line notification (part E of the prompt), because the completion notice to the main session
  never arrived.

- 3:12 pm CST Nov 19 (check-in): both jobs alive (restarted 2:41 pm); seventh PC cycle running since 2:41 pm,
  six before it ok; 59 forecasts, none resolved; main account $998.29, 2 positions, 2 resting. Nothing new
  for a round: the download is only enlarging the random samples (115,737 markets with bars, no rate
  limits). Observation log: 13 markets seen, none settled; resting NO bids 6 of 6 filled. Usage: 5-hour 2%,
  weekly all models 48%, weekly Fable 76% (70% at 12:25 pm), with 57% of the week past:
  `cycle_every_hours` left at 2 (all-models 9 points behind; 2 is the floor). E: 49.2 GB free, C: 29.4 GB.

- 6:12 pm CST Nov 19 (check-in): both jobs alive (since 2:41 pm); cycles at 2:41 and 4:44 pm ok (eight in
  all on the PC), next about 6:45 pm; 72 forecasts, none resolved; main account $998.56, 2 positions, 3
  resting (new: YES on December CPI above -0.1 at 67c). The variants were skipped after the 4:44 pm cycle
  (it ended inside the 5:15 to 6:20 pm quiet window); they run after the next one. Nothing new for a round:
  the download is still enlarging the random samples (141,745 markets with bars, no rate limits).
  Observation log: 14 markets seen, none settled; resting NO bids 7 of 7 filled. Usage: 5-hour 24%, weekly
  all models 51%, weekly Fable 79% (76% at 3:12 pm), with 59% of the week past: `cycle_every_hours` left at
  2 (all-models 8 points behind; 2 is the floor). Fable is on course to pass 90% during Friday: from then a
  check-in does health only. E: 49.1 GB free, C: 28.5 GB.

- 7:55 pm CST Nov 19 to 3:13 am CST Nov 20: everything paused at the user's word, then resumed ("resume. close
  any unnecessay processes"). The PC had restarted at 3:10 am; no project process survived it (the cmd and
  cscript processes running at 3:10 belong to Windows services, not to this project), so nothing needed closing.
  Log-on task re-enabled, both jobs restarted at 3:13 am, a paper cycle began at once. The check-in stays OFF:
  see "No Fable usage" at the top.

- 4:25 am CST Nov 20 (the user's session, on Opus): THE CODING ITEMS ARE DONE (the user: "Implement the coding
  changes and the fable to opus ... especially curious to see how selling before settlement can impact
  things"). Report 3.28. Exits before settlement (`research/exits.py`, `exit_study.py`, `exit_summary.py`): 25
  policies x 32 rule-and-sample cases; take-profits and time exits never beat holding out of sample, stops did
  in 4 small cases and cost the most elsewhere; HOLD TO SETTLEMENT. Combined account (`research/combined.py`):
  +15.3% a year out of sample at 0.5% a bet, drawdown 5.4%, holding; most of it the Entertainment leg (found
  on that data). THE 5-CENT RULE NOW FAILS THE TAIL TEST OUT OF SAMPLE AT THE DEFAULT CENSUS LEVEL (the sample
  grew from 26,635 to 39,858 markets) and PASSES at 20,000 and 45,000 contracts traded (replay +18% to +20% a
  year out of sample at 1%): a busy-market effect. Entertainment's NO-against-5-35c rule passes the tail test in
  both halves on busy markets and loses on the random sample. Paper accounts: price-only exits in
  `src/trader.py` (off for the paper bot), six exit accounts from 4:04 am (18 accounts). `scripts/replay_wide.py`
  works, nothing settled yet. The check-in now runs on Opus from a Windows task (top of this file). 214 tests.
- 6:40 am CST Nov 20: NO DAILY BUDGET ANY MORE, in any account (the user: "Make sure you are resting also having
  no limits on the amount of trades per day"). config.yaml safety: max_orders_per_day 1000 (was 6),
  max_deploy_per_day_pct 1.0 (was 0.10). Orders already rest by default (execution.style passive); the two
  taker accounts (blend30_taker, claude_only_taker) stay taker on purpose, as the comparison for resting.
  Kept: stake per market (2%, $50 an order), per-event, category (20%) and total (40%) exposure caps, price limits,
  stops. The main account's record before and after this time is under different rules: compare them apart.
  Takes effect at the next cycle (the loop reads config.yaml each time; no restart).
- 5:23 pm CST Nov 20: EVERYTHING PAUSED at the user's word ("Pause"). Download and paper loop stopped (no cycle
  was running), both Windows tasks (Check-in, Jobs) disabled, no session reminders left. To resume: enable both
  tasks and run `research\start_jobs.ps1 -PaperLoop`.
- 6:30 pm CST Nov 20 (still paused): TESTS FOR EVERYTHING (the user: "You can delete anything and please make
  tests for anything you can"). Deleted `data\_pc_before_bundle`, `data\_ledger_snapshot_0306` and data\tmp's
  contents. Five new test files (scripts, src gaps, downloader, research tools, the check-in script with a fake
  claude): 214 -> 440 tests, coverage 68% -> 99%. Bugs they found, all fixed:
  downloader: a transient error wrote a series' schedule off (early=-1); one failing market was re-requested
  without end in the same pass; tickers with "%" were encoded twice and written off (GPT%-23DEC31 reset to
  be fetched again). panel: the liquid-census floors were lost (pandas 3 merges drop attrs). portfolio.run put
  a bet in or out of sample by its release time, not its market's close (as Panel.evaluate does): replay
  numbers near the 2026-04-01 split can move slightly on a re-run. analyze_rule and exit_study crashed on a
  rule with no bets; exit_summary on such a file; combined.py turned an unknown --exit name into "hold" and
  overwrote combined_hold.csv (now an error). forecast.py: claude JSON that is not an object crashed the
  market's remaining runs; the "only N of M runs valid" count was wrong. checkin.ps1: the exit code of a
  failed claude run was never logged; an answer reporting no model is now flagged "NO MODEL REPORTED";
  -ClaudeExe, -DataDir and -NoNote added for the tests only. replay_wide crashed without a main ledger.
- 3:25 am CST Nov 21: RESUMED at the user's word ("resume"). Both Windows tasks enabled again (next Opus
  check-in 6:11 am), download and paper loop restarted with the fixed downloader; a paper cycle began at once.
- 5:15 am CST Nov 21: NINE MECHANICAL RULE ACCOUNTS, FIVE STRICTER CLAUDE ACCOUNTS, A SECOND OBSERVATION BAND
  (the user, to both open questions: "Yes make both of those and anything else possible for testing. We ar under
  no time constraint and want to to find the best possible source of risk averse money making"). New code:
  `src/rules.py`, `rules.yaml`, `scripts/run_rules.py` (accounts under data\rules\, own listing
  data\rules\kalshi_listing.json, 6 h, all twelve tested categories, 0.25-400 days; no Claude; hold to settlement;
  resting joins the best NO bid for 72 h; 1% a bet, 3% per event, 50% exposure, as research/portfolio.simulate).
  Accounts: rule_5c_busy and rule_ent_band (the two asked for), rule_combined (the four legs of combined.py at
  0.5%), rule_5c_busy_taker, rule_ent_band_taker, rule_ent_fall (Entertainment 10-25c down 3c+ in 7 days, from
  Kalshi's daily candles), rule_climate_band, and two CONTROLS on quiet markets (control_5c_quiet under 45,000
  contracts, control_ent_quiet under 5,000), where the history says the rules lose. First run 5:01 am: 152 paper
  orders across the nine (24 Entertainment band, 7 5-cent busy, 26 combined, 23 per control), 714 requests,
  8 minutes. Variants: claude_only_edge5, _edge8, _high_conf (new execution.min_confidence), _dear_side (side
  priced 50c+), _no_side (new execution.only_side): 23 Claude accounts. `scripts/shadow_longshot.py --band ent`
  logs the Entertainment band's books and resting fills (data\shadow_ent.db; first pass 17 recorded). The paper
  loop runs both after every cycle (restarted 5:13 am). 470 tests, all pass. With 9 + 23 accounts one will look
  good by luck: read the controls first.
- 5:45 am CST Nov 21: "Keep testing and trying things indefinitely": standing section "KEEP TRYING THINGS" at
  the top and an "Ideas queue" at the end (13 items); the check-in now works one queue item when nothing new has
  landed instead of stopping. Tenth rule account `rule_5c_busy_claude` (Claude as a veto on the 5-cent busy rule,
  at most 2 questions a cycle; usage at 5:17 am: weekly all models 63% with 79% of the week gone, Fable 84%,
  unchanged). Queue item 1 done (report 3.29): the Entertainment band passes the tail test in both halves at
  5,000, 20,000 and 45,000 contracts.
- 6:25 am CST Nov 21: queue item 2 (report 3.30): the Entertainment band as a taker earns about half the resting
  version (+3.5% a bet) and fails the tail test in sample at 45,000. No new account. Jobs ok; cycle running.
- 6:45 am CST Nov 21: queue item 3 (report 3.31): the 5-cent rule's edge sits at 3-6c resting; under 3c it is thin;
  takers fail. No new account; item 15 added. Jobs ok; main $1,010.72, 0 settled.
- 9:15 am CST Nov 21: queue item 4 (report 3.32): the 5-cent rule on stand-alone questions at 45,000 passes in
  sample, too thin out of sample (27-35 events). No new account. Jobs ok; main $1,010.72, 0 settled.
- 9:45 am CST Nov 21: queue item 5 (report 3.33): the wide band per category at 45,000: only Politics passes alone, by a
  hair and not at 20,000; the nine pooled pass at 45,000 but earn almost only in 2026. No new account; item 16 added.
- 12:25 pm CST Nov 21: queue item 6 (report 3.34): calibration at 45,000 per category finds no new band; Climate and Weather's
  5-cent rule: 0 losses in 89 events, fails the tail test (too few). Item 17 added. Jobs ok; main $1,010.72, 0 settled.
- 12:35 pm CST Nov 21: queue item 7 (report 3.35): smaller stakes help the combined account out of sample (0.25%: +12.1%/y,
  DD 4.0%); the 5-cent leg loses above 0.25% and the combined figure at 0.5% fell from 15.3% to 8.8% on the larger download.
  Item 18 added. Jobs ok; main $1,010.72, 0 settled.
- 3:15 pm CST Nov 21: queue item 8 (report 3.36): Entertainment band exits at 45,000: take at 98c resting does not beat holding
  out of sample; holding stays. Jobs ok; main $1,010.72, 0 settled.
- 3:45 pm CST Nov 21: queue item 9 (report 3.37): the momentum lead (NO at 3-10c after a 3c+ fall) fails out of sample in all
  6 variants on the nine pooled busy markets. No account. Jobs ok; main $1,010.72, 0 settled.
- 6:30 pm CST Nov 21: queue item 10 (report 3.38): research/hourly_bars.py fetches hourly bars for the last 48 h of a rule's
  markets (own database); 400 of 815 Entertainment-band markets fetched. Item 20 added. Jobs ok; main $1,010.72, 0 settled.
- 6:35 pm CST Nov 21: queue item 11 (report 3.39): event baskets on all eleven busy categories; flagged-exclusive still no
  edge; Kalshi flags for ~3,700 more events being fetched (detached, ~1.5 h). Jobs ok; main $1,010.72, 0 settled.
- 8:20 pm CST Nov 21: EVERYTHING PAUSED at the user's word ("Pause"). Download and paper loop stopped (no cycle was
  running; the detached event-flag fetch had already ended), both Windows tasks (Check-in, Jobs) disabled. Next is
  queue item 12. To resume: enable both tasks and run `research\start_jobs.ps1 -PaperLoop`.
- 4:07 am CST Nov 22: RESUMED at the user's word ("close all unnecessary tasks and resume"). Nine old idle check-in
  sessions (Nov 19-20) archived in the Claude app; both Windows tasks enabled again (next Opus check-in 6:11 am);
  download and paper loop restarted, a paper cycle began at once. The app's own scheduled check-in stays OFF (Fable).
- 4:15 am CST Nov 22: queue item 11 finished (report 3.40): event baskets with the flags known fail (exclusive in sample
  negative at every threshold). Item 21 added. Jobs ok (cycle running since 4:07 am); main $1,010.31, 0 settled.
- 6:20 am CST Nov 22: queue item 14 (report 3.41): the Entertainment band by days to close: the edge is spread across
  horizons, short-dated markets the weakest (fail out of sample). No new account. Jobs ok; main $1,009.89, 0 settled.
- 7:35 am CST Nov 22: queue item 15 (report 3.42): the 5-cent rule at 3-5c only: better per bet, less money out of sample;
  no new account (subset of rule_5c_busy); new rule name in families.py + 1 test (477 pass). Item 22 added. Jobs ok;
  main $1,009.89, 0 settled.
- 9:25 am CST Nov 22: queue item 16 (report 3.43): the nine-category band's weak 2025 is the long-dated slice; 0-7d passes
  both halves at 45,000 (by a hair out of sample). Lead only; item 23 (same at 20,000) added. Jobs ok; main $1,009.89, 0 settled.

- 10:10 am CST Nov 22: queue item 17 (report 3.44): Climate 5-cent alone unchanged (89 events); with Politics passes both
  halves but Politics carries it and the pair was picked after the fact; no account; item 24 added. Jobs ok; main $1,009.89, 0 settled.

- 12:40 pm CST Nov 22: queue item 18 (report 3.45): combined account at 0.25% is best with the 5-cent leg at 45,000 (+10.3%/y out
  of sample). Found: the random pass has finished for 8 categories, so the liquid DEFAULT level is now 1 contract (all markets):
  ALWAYS pass --min-cumvol from now on. The Entertainment band is weaker on the larger download (item 25, next). Jobs ok; main
  $1,010.18, 1 settled (+$8.57).
- 4:45 pm CST Nov 22: queue item 20 (report 3.48): hourly stops on the Entertainment band: every stop worse than on daily bars; hold
  stays, no verdict changes; exits.py --hourly + 1 test (479 pass); item 29 added. Jobs ok; main $1,010.18, 1 settled.
- 6:20 pm CST Nov 22: queue item 23 (report 3.49): the nine-category band at 0-7d fails out of sample at 20,000 and 5,000; no
  account. Jobs ok; main $1,008.69, 1 settled.
- 7:15 pm CST Nov 22: queue item 26 (report 3.50): the band's 5,000-20,000 layer is the whole 5,000 account (all bets before 20,000);
  hindsight split: quiet markets are its best, not its losers; no account change; analyze_rule --max-cumvol + 1 test (480 pass); item 30
  added. Jobs ok (cycle running since 6:22 pm); main $1,008.96, 1 settled.

## How to run a round

SINCE NOV 22 the liquid sample's default level is 1 contract for every category whose random pass has finished
(report 3.45): always pass `--min-cumvol` (5,000 or 45,000), or the "busy" sample is every market.

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

17. DONE: Claude forecasts on Kalshi through the paper bot (since 2026-11-18).
18. RUNNING since 2026-11-21: Claude as a filter on a mechanical rule: the paper account `rule_5c_busy_claude`
    (rules.yaml; pair `rule_5c_busy`). Read it once 20+ of its markets (kept and vetoed) have settled.
- 1:30 pm CST Nov 22: queue item 25 (report 3.46): Entertainment band unchanged at 20,000/45,000, weaker at 5,000 (tail test passes, 1% replay out of sample -1.0%/y, DD 18%; taker fails). New paper account rule_ent_band_20k. Items 26-27 added. Jobs ok; main $1,010.18, 1 settled.

- 3:30 pm CST Nov 22: queue item 19 (report 3.47): in Entertainment a recent fall lifts the band's per-bet edge (+9-10% vs +7%), a rise
  fails in sample; fewer bets, so no account better than the band; rule_ent_fall stays. Item 28 added. Jobs ok; main $1,010.18, 1 settled.

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
   the last two days (the exit study's one real caveat: daily bars make stops sell at the next open); sports
   and crypto samples last. DONE 2026-11-20 (report 3.28): exits before settlement, the combined-portfolio
   replay, the wide-account replay tool.
5b. **Each check-in, cheap:** once markets of the paper accounts settle, `scripts\run_variants.py --report`
   (18 accounts: compare each exit account with its pair, `claude_only` or `main`) and
   `scripts\replay_wide.py`. When the download extends a sample, re-run `research\exit_study.py` only if a rule's
   held-to-settlement figures change verdict; report the 5-cent rule at the 45,000 level (fixed in 3.7) beside
   the default level, never only the better one.
6. DONE 2026-11-21 (the user said yes to both): the 5-cent busy account and the Entertainment band are paper
   accounts in `rules.yaml` (with seven more), and the band has its own observation log (`--band ent`). Each
   check-in: `scripts\run_rules.py --report`; once a few dozen bets of an account have settled, compare it with its
   quiet-market control and with the backtest's per-bet figure (5-cent busy +2.07%, Entertainment band +7.28%,
   fall rule +8.95%, combined +15.3% a year out of sample), and write it in the report. Paper fills are harsher
   than the backtest's (the market must trade through the bid): read the shadow logs' fill rates beside them.
7. **AS OF 12:25 pm CST Nov 19: NOTHING IS WAITING ON THE DOWNLOAD.** r25 is done (report 3.27) and every
   category has had both samples. The download is only enlarging the random samples (same shuffle): that is
   NOT a reason for a new round at each check-in. Re-run the random rounds once, when the download log shows
   the random-order pass finished for all categories, and only report what changes. Until then a check-in is:
   part A, the forward logs (variants, observation log) once markets have settled, and otherwise one line
   and stop. Left to code, none urgent, one per check-in at most: exits before settlement; a
   combined-portfolio replay; the after-the-fact replay tool for the wide variant accounts (once a few dozen
   markets have settled). [Those three were coded 2026-11-20, report 3.28.] Open for the user: see item 6
   (as of Nov 20 the questions are the 45,000-contract version of the 5-cent account and an Entertainment-only band).
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

## Ideas queue (work the first open item each check-in; see "KEEP TRYING THINGS" at the top)

Rule names must match `research/families.py` exactly (`analyze_rule.find_rule` says when one does not). Write
every result, pass or fail, into the report and mark the item here with the date and one line. Add new items at
the end when a result suggests one. Judge by the rules above: tail test both halves, account replay, worst
drawdown, capacity in dollars, and say how many variants were tried.

1. DONE 5:40 am CST Nov 21 (report 3.29): Entertainment band (NO vs YES 5-35c, resting) at 5,000 / 20,000 /
   45,000 contracts: passes the tail test in both halves at all three; +7.3% / +7.4% / +7.1% a bet; replay at 1%
   out of sample +31% / +33% / +26% a year, worst drawdown 6.0% / 6.6% / 2.3%. Holds at the busiest level too.
2. DONE 6:25 am CST Nov 21 (report 3.30): Entertainment band as a TAKER: +3.5% a bet at 20,000 and 45,000 (half
   the resting edge); passes both halves at 20,000, FAILS in sample at 45,000 (bound 29.0% vs 28.5%). No new account.
3. DONE 6:45 am CST Nov 21 (report 3.31): money is in 3-6c resting (+3.2-3.3% a bet, passes both halves at 0-7d
   and 7-30d); 0-3c is thin (fails under 7d, +1.8% passes by a hair at 7-30d); no taker slice passes. Was: The 5-cent rule at 45,000 split by days to the close (the "25 longshot NO" family: "NO at mid 0-3c, 0-7d to
   scheduled end, fixed date" and its neighbours, both entries): where does the rule's money come from?
4. DONE 9:15 am CST Nov 21 (report 3.32): resting +3.7% a bet, taker +1.9%; both pass the tail test in sample, out of
   sample 27/35 events with no loss is too few to pass; median $492-680 a week traded. No new account. Was: The 5-cent rule on stand-alone questions only at 45,000 ("single-market event: NO where YES is 5c or less,
   spread <= 5c", mk and tk): report 3.19 asked this.
5. DONE 9:45 am CST Nov 21 (report 3.33): no second Entertainment. Only Politics passes both halves alone at 45,000,
   by 0.4 pt out of sample, and fails at 20,000 / loses at 5,000; Economics fails out of sample. The nine pooled at
   45,000 pass both (+4.2% a bet) but the money is 2026 (2025 +1.3%), in-sample replay +1.0%/y, DD 11.2%. No account.
   Was: the wide band (NO vs YES 5-35c, resting) in each of the nine categories ALONE at 45,000.
6. DONE 12:25 pm CST Nov 21 (report 3.34): only Politics 0-5c, Entertainment 10-20c (both known) and Climate and Weather 0-5c
   are off in both halves with 30+ events; Climate's 5-cent rule at 45,000: 0 losses in 89 events but fails the tail test
   both halves (too few). No account; item 17 added. Was: Calibration curve at 45,000 for every category (`research/calibration_curve.py --sample liquid --min-cumvol
   45000 --categories <Cat>`): any other band where YES is overpriced in both halves, per event?
7. DONE 12:35 pm CST Nov 21 (report 3.35): out of sample 0.25% a bet earns MORE and draws down less (+12.1%/y, DD 4.0%) than
   0.5% (+8.8%, 6.7%) or 1% (+2.3%, 10.2%): the 5-cent leg turns negative with size; in sample the order reverses. Was:
   Risk-averse sizing for the combined account: `research/combined.py --stakes 0.0025,0.005,0.0075` and the
   worst drawdown of each; does a smaller stake buy a much smaller drawdown?
8. DONE 3:15 pm CST Nov 21 (report 3.36): at 45,000 the 98c resting exit earns slightly LESS than holding out of sample
   (+24.9%/y vs +25.5%, per bet +9.73% vs +9.96%); the in-sample pick (take 0.97 taker) +27.8%/y, inside the noise of 25
   policies and 242 bets. Holding stays. Was: The Entertainment band with "take at 0.98, resting" at 45,000 (`research/exit_study.py`): report 3.28 found
   capital time helps the account replay there; check it at the busy level.
9. DONE 3:45 pm CST Nov 21 (report 3.37): FAILS. NO at 3-10c after a 3c+ fall in 1/3/7 days, nine pooled, busy: resting
   passes in sample, fails out of sample in all three; taker fails both and loses in the replay. Thin ($71-142 a week). Was:
   The momentum lead (NO at 3-10c after a fall of 3c+, resting) on the busy sample pooled.
10. DONE 6:30 pm CST Nov 21 (report 3.38): research/hourly_bars.py (+3 tests) fetches 60-min bars for the last 48 h of a
    rule's markets into data\kalshi_hourly.db; Entertainment band at 45,000: 400 of 815 markets fetched (398 with bars).
    Was: Code: hourly bars for the last two days of markets the exit study holds (its one real caveat).
11. DONE 4:15 am CST Nov 22 (reports 3.39, 3.40): event baskets on all eleven busy categories with Kalshi's flags known
    (3,706 fetched): exclusive baskets never pass both halves (1.00+: -0.37% / +0.73%; 1.02+: -0.09% / +1.16%); after
    fees nothing is locked at entry. FAILS, no account; item 21 added.
12. STANDING (not an open item; 4:15 am CST Nov 22): check it in every check-in's forward-log step, and write it up only
    once its thresholds are met; until then go on to the next open item. Forward, when there is data: each rule account against its control and its backtest per-bet figure (30+
    settled bets); `rule_5c_busy_claude`: loss rate of kept against vetoed markets (20+ settled); the shadow logs'
    resting fill rates against the backtest's 55-80% model (50+ decided).
13. STANDING (not an open item): when a queue item passes all the tests, add a paper account for it under a new name in rules.yaml (allowed
    by the user's word above), and say so in the report.
14. DONE 6:20 am CST Nov 22 (report 3.41): no slice beats the whole band; 0-7d is the weakest (+6.2% a bet) and FAILS the
    tail test out of sample; 7-30d passes by a hair, 30+d earns most (+8.2%) but leans on 2026. Account unchanged. Was:
    The Entertainment band (resting) by days to close (0-7, 7-30, 30+ days) at 20,000: taker results (3.30) are
    thin in 2025; is the edge in the short-dated markets, where capital turns over fastest?
15. DONE 7:35 am CST Nov 22 (report 3.42): at 45,000 resting, 3-5c earns +3.27% a bet (whole rule +2.07%) and passes both
    halves, but the out-of-sample replay earns less (+13.6%/y vs +18.1%); taker fails; default level fails out of sample.
    A subset of rule_5c_busy: no new account; item 22 added. Was: The 5-cent rule without its 0-3c corner (report 3.31): NO at mid 3-5c, spread <= 5c, <= 30d, resting and taker, at
    45,000 and the default level. Needs a new rule name in research/families.py (add, do not rename) and a test.
16. DONE 9:25 am CST Nov 22 (report 3.43): mostly horizon: 30+d is flat in 2025 and drags the replay; 0-7d passes both halves
    (+5.97% a bet, out of sample by 0.75 pt on 135 events; replay 1% +5.5%/y DD 4.4% in, +19.1%/y DD 4.6% out); 7-30d and
    30+d fail out of sample. A lead, no account yet; item 23 added. Was: The nine-category wide band at 45,000 (report 3.33) earns almost only in 2026: split by year AND days to close
    (0-7, 7-30, 30+) to see whether 2026 is a change in the market or a shift to short-dated markets.
17. DONE 10:10 am CST Nov 22 (report 3.44): Climate alone unchanged (89 events, download has not added any); pooled
    with Politics resting passes both halves (replay 1% +1.6%/y in, +12.6%/y out, DD 1.7%) but Politics alone already
    passes and the pair was picked after the fact; no account (Politics is inside rule_5c_busy). Item 24 added. Was:
    Climate and Weather 5-cent rule at 45,000 (report 3.34: 0 losing in 89 events, too few): re-run analyze_rule mk/tk
    once the download has added Climate and Weather markets; also pool it with Politics only (both pass/near-pass alone).
18. DONE 12:40 pm CST Nov 22 (report 3.45): at 5,000 and 0.25% out of sample, the 5-cent leg at 45,000 is best (+10.3%/y,
    DD 6.0%) vs +7.6% (leg at 5,000) and +8.9% (no leg); above 0.25% all worse. combined.py got --five-cumvol and
    --min-cumvol (+test). Found: the Entertainment band is weaker on the larger download; item 25 goes FIRST. Was:
    Combined account (research/combined.py) without the 5-cent nine-category leg, and with that leg at 45,000 instead of
    the default level (report 3.35: the leg's out-of-sample edge fell to +0.29% a bet and it loses money above 0.25%).
    Needs a leg option in combined.py (add, with a test).
19. DONE 3:30 pm CST Nov 22 (report 3.47): in Entertainment a 7-day fall lifts 10-25c NO to +9.2% / +10.2% a bet (band +7.4% /
    +7.1%), all falling versions pass both halves at 20,000 and 45,000, a RISE fails in sample; but the 1% replay earns less a
    year than the band (fewer bets). No new account (rule_ent_fall already tests it). Item 28 added. Was: The momentum lead (report 3.37) failed pooled; one last look in Entertainment alone (busy, 20,000 and 45,000),
    where the wide NO band works: does a recent fall add anything over the band itself (compare with 3.29)?
20. DONE 4:45 pm CST Nov 22 (report 3.48): all 815 band markets fetched; exits.py --hourly: every stop gets WORSE on hourly
    bars (stopped out a third to a half more often; 4 of 6 fail the tail test out of sample); hold stays; no verdict of 3.28 /
    3.36 changes. Item 29 added. Was: Finish the hourly fetch (`research/hourly_bars.py --sample liquid --min-cumvol 45000 --categories Entertainment`,
    same command, resumes), then replay the band's stop exits (exits.py stop_drop / stop_px) on the hourly bars in the
    last 48 h instead of the next daily open: does any verdict of 3.28 / 3.36 change? Needs an hourly option in exits.py.
21. The exclusive 1.05+ basket corner (report 3.40: 13 in sample, 55 out of sample, +1.75%, worst -0.2%): re-run
    `research/event_baskets.py` only once the download has added many more exclusive events; low priority.
22. Forward, once rule_5c_busy has 30+ settled bets: split its settled bets by entry price (YES 0-3c against 3-5c) and
    compare with report 3.42 (3-5c +3.27% a bet, the 0-3c rest about +0.6%): the forward test of item 15, no new account.
23. DONE 6:20 pm CST Nov 22 (report 3.49): FAILS out of sample at 20,000 (bound 30.7% vs break-even 26.4%) and at 5,000 (27.7 vs
    27.4); no account. At those levels 7-30d passes by a hair instead (noise of 9 slices). Was: The nine-category wide band, 0-7 days to close (report 3.43, passed at 45,000 by 0.75 pt out of sample): re-run at 20,000
    and 5,000 (`research/band_by_dte.py 20000 nine`). If it passes both halves at 20,000 too, add a paper account under a
    new name in rules.yaml (check that rules.yaml supports a days-to-close window first; if not, code it with a test).
24. Forward, once rule_5c_busy has 30+ settled bets: its Politics bets alone against report 3.44 (Politics 5-cent resting
    at 45,000: +6.3% a winner, 2% of events losing in sample); and re-test Climate and Weather alone when the download
    has added its markets at 45,000 (still 89 events on Nov 22).
25. DONE 1:30 pm CST Nov 22 (report 3.46): at 20,000 / 45,000 the band and the 5-cent rule are unchanged (all of 3.29 / 3.30 /
    3.7 stand there); at 5,000 the band still passes the tail test both halves (+4.57% a bet) but its 1% replay loses out of
    sample (-1.0%/y, DD 18%) and the taker fails both. New account rule_ent_band_20k (20,000+). Items 26, 27 added. Was:
    the Entertainment band at 5,000 now earns +5.3% / +3.2% a
    bet (3.29: +7.3% / +7.2%) and its 1% replay out of sample is -2.5%/y, DD 18.5%. Re-run the tail test and replay of
    "NO where YES is at 5-35c", Entertainment, mk and tk, at 5,000 / 20,000 / 45,000 (`research/analyze_rule.py --sample
    liquid --min-cumvol N --categories Entertainment`), and the 5-cent rule at 45,000 on the nine; write which verdicts of
    3.29 / 3.30 / 3.7 still stand. If the band fails, say so to the user (rule_ent_band and rule_combined rest on it).
26. DONE 7:15 pm CST Nov 22 (report 3.50): cut by volume at entry, the layer IS the whole 5,000 account (every bet comes before
    20,000); hindsight split by final volume: never-busy markets are the BEST (+8.1% / +5.7%), later-busy fail out of sample.
    Not tradeable (final volume is partly the outcome); analyze_rule --max-cumvol + 1 test; item 30 added. Was: The Entertainment band in the 5,000-20,000 contract layer alone (report 3.46: the markets the download added there pulled
    the 5,000 figure down): does that layer lose by itself, in both halves? Needs a max-cumvol option in analyze_rule.py (add,
    with a test), or a filter in a small script. If it loses in both halves, write it plainly for the user: rule_ent_band
    and rule_combined (5,000+) trade it.
27. Forward, once both have 30+ settled bets: rule_ent_band_20k against rule_ent_band (its superset) and control_ent_quiet.
28. Isolate the fall effect in Entertainment (report 3.47): the band's 10-25c bets WITHOUT a 3c+ fall in 7 days against those
    with one, at 20,000 and 45,000, resting. Needs a new rule name in research/families.py (add, do not rename) and a test. If
    the no-fall bets lose or are flat in both halves, the band's money is the fall, worth writing for the user.
29. The 5-cent rule's stops on hourly bars (report 3.48 found hourly bars make every Entertainment-band stop worse): fetch
    hourly bars for its markets at 45,000 on the nine (`research/hourly_bars.py --sample liquid --min-cumvol 45000 --categories
    <nine> --rules "NO at mid <= 5c, <= 30d, spread <= 5c|no|mk" --max-markets 1000`, resumes), then `research/exit_study.py
    --tag nine_liquid_45000_hourly --hourly data\kalshi_hourly.db` against the same run without --hourly. Low priority: hold
    already beat its stops on daily bars (3.28).
30. Entry timing in the Entertainment band (report 3.50): for markets that reach 20,000 contracts, the band's bet at the first
    5,000 bar against its bet at the first 20,000 bar (same markets, resting; both known ex ante): is waiting for the market to
    get busy what makes the 20,000 account hold while the 5,000 account weakens? A small script on panel.load at 5,000 with
    the 20,000 mask from cumvol; tail test and per-bet both halves.
