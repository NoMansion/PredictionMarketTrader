# Strategy research on Kalshi history
*Started Wednesday 2026-11-18. A running report: newest status first, then method, then one dated section per
round. Nothing here has been traded, on paper or otherwise.*

## Status

*Updated 1:57 am CST, 2026-11-19. Times in new text are US Central; sections 3.1 to 3.5 were written in UTC.*

- **What the data supports: in busy Kalshi markets a cheap YES is overpriced, and the money in that goes to
  whoever rests orders, not to whoever pays the ask.** Across all seven categories the bot trades, at 5,000+
  contracts traded (17,522 markets, 5,316 events), 17 rules pass and 16 of them buy NO against a cheap YES.
  Sections 3.7 to 3.19.
- **The resting-order version of the 5-cent rule passes on all seven categories pooled:** +1.85% per bet, 58
  losing events of 1,518, tail test passed in both halves, +3.6% a year before April 2026 and +14.8% a year after
  in the replay at 1% stakes. It does not depend on where exactly the order rests or for how long (3.17). Its
  fills are modelled from daily highs and lows, not observed: until the forward log has observed them (3.13),
  it is a hypothesis with good support, not a result.
- **Paying the ask does not pass on the pooled sample** (+0.43% per bet, tail test failed in both halves, replay
  about zero). It works in two narrower places: Economics (+1.3% per bet, 3.11), and stand-alone yes/no
  questions, events with a single market, where it lost 5 times in 696 (3.19). Both are small.
- **Where the effect is and is not:** strongest in single-market events and in Economics; present with resting
  orders in Politics and Science and Technology; absent in Elections and inside multi-outcome events.
- **Only the narrow version survives as an account.** Buying NO against YES at up to 35 or 50 cents looks good
  per bet (+2.6% resting), but replayed it lost 3% a year with a 29% drawdown before April 2026, and counting
  each event once it earns nothing: its gains sit in a few events with dozens of outcomes (3.14, 3.17). The
  idea of correcting the forecast bot's starting price above 10 cents is not supported either.
- **A third flaw of mine, found at 11:55 pm (3.17):** the account replay took same-day bets losers first. Every
  replay figure in sections 3.8 to 3.16 is too pessimistic; the corrected ones are in 3.17 and in this list.
- **No arbitrage across an event's outcomes** (3.15): where outcomes exclude each other, their bids add up to 1.00
  to 1.02, and the fee takes the rest.
- **It is small either way.** Each bet risks about 96 cents to make 2 to 4. On a $1,000 account this is tens of
  dollars a year. It is not in the paper bot (section 3.9).
- **Nothing passes on a random sample of all markets** (3.6, 3.12). The exchange as a whole is priced about
  right; the mispricing is where the volume is (3.10).
- **Two flaws of mine found and fixed on the way:** markets chosen by lifetime volume (3.5), and "days to close"
  measured from a close date not knowable in advance (3.7). Rounds 3.1 to 3.5 are superseded.
- **Forward test of Claude's forecasts:** five paper cycles, 20 forecasts, most of them low-confidence and not
  traded, four resting paper orders, none filled, account at $1,000 (`reports/forward_log.csv`).
- **Downloaded:** every category the bot trades. Commodities is downloading now, then Financials, Mentions,
  Entertainment, Crypto, Social, Climate and Weather: categories the bot does not trade, tested for completeness.

## 1. Method

**Data.** Settled Kalshi markets from the exchange's public archive (2021 to September 2026) plus markets settled
since, with daily bars of bid, ask and traded price. Since 20:53 UTC on 2026-11-18 the download draws markets in a fixed random order within each category and
takes any market that ever traded; backtests use only that random sample. (Before that it took the biggest
markets first, with a 200-contract minimum: see section 3.5 for why that was a mistake.) Liquidity conditions in
a rule must use volume as it stood at the time of the bar, never lifetime volume.

**Two samples, and only these two** (since 4:00 pm CST on 2026-11-18):
- *Random:* markets in a fixed random order, any market that ever traded. It represents the whole exchange,
  which is mostly tiny markets with wide quotes.
- *Busy markets:* every market that ever reached a set number of contracts traded, seen only from the day it
  reached it. A rule never sees the quiet early days of a market that later became big, so there is no hindsight
  in the choice. The level is 13,100 contracts for Economics alone and 45,000 where Politics is included; the
  download is extending it down to 5,000.

**Days to close come from the schedule.** Kalshi overwrites a market's close time when it closes early, so for
markets that can close early the backtest counts days to the expected expiration, which was known in advance.
Holding times and account replays use the real close.

**One observation per market per day.** A rule may look only at what was known at the end of a daily bar: the
quote, the days left, the market's age, recent volume and price changes, and the other markets of the same event.

**Entries.** One per market, at the first bar on which the rule's condition holds.
- *Taker:* buy at the next bar's opening ask (or one minus the bid, for NO) and pay Kalshi's fee,
  0.07 × price × (1 − price) per contract.
- *Resting:* leave a bid at the bar's closing bid for up to three bars. It counts only if the ask later came down
  to it or a trade printed below it. Series that charge resting orders pay that fee too.

**Exit.** Hold to settlement. Returns are per dollar staked, after fees.

**Judging a rule.** Fixed before any result was seen:
- *Split.* In sample is markets closing before 2026-04-01; out of sample is from that date. Kalshi's history is
  concentrated in 2026, so this puts roughly half the events on each side.
- *Sample size is events, not markets.* The markets of one event rise and fall together, so standard errors are
  clustered by event, and a rule needs 100 events on each side to be judged at all.
- *Pass:* positive on both sides, in-sample t of 2 or more, out-of-sample t of 3 or more. With about 4,000 rules
  in a round, pure chance produces about one such "pass" in four rounds; anything that passes is then re-tested
  on categories and periods it was not found on before it is believed.
- *Lead:* positive on both sides with out-of-sample t of 2 or more. Worth a follow-up round, not a conclusion.
- *Lopsided bets get a different test.* A t-statistic means little for a bet that wins 2 cents 99 times and loses
  97 cents once. For those, `research/analyze_rule.py` counts losing events, works out the loss rate at which
  the rule breaks even, and asks whether an exact 95% upper bound on the true loss rate is still below it.

**Checked against a made-up exchange.** With fair prices, no taker rule passes and the average rule loses about
the spread and the fee. With cheap contracts deliberately quoted 6 cents too high, selling them passes and buying
them loses. So the engine neither invents edges nor misses a planted one.

## 2. Families

| # | Family | What it asks |
|---|---|---|
| 1 | Price-level calibration | Is a contract at this price worth its price? By price band, days left, category |
| 2 | Favourites near expiry | Do near-certain contracts close to settlement pay more than their risk? |
| 3 | Always No | Does betting against everything pay, by event size and by whether the market is the event's favourite? |
| 4, 13 | Momentum, reversal, jumps | After a move of 3 to 20 cents in 1 to 7 days: follow it or fade it? |
| 5 | Deadline wording | Do "before" and "by" markets drift to No? |
| 6 | Threshold ladders | Are "above X" markets of one event priced in order? Lock-in pair trades |
| 7, 10 | Volume and age | Thin against busy markets; newly listed against old |
| 8 | Spread | Does a wide quote pay the side that rests in it? |
| 11 | Series persistence | Does a series that paid one side in the first half still pay it in the second? |
| 12 | Calendar | Day of week, month |
| 14 | Combinations | Price × days × category, × volume, × favourite, × momentum |
| 16 | Early close | Markets that can close early against fixed-date ones (uninformative: 82 to 99% carry the flag) |
| 18 | Question shape | "Above X", "below X", "between", or no number |
| 19 | Event size | Longshots and favourites by the number of outcomes in the event |
| 22 | Event price sums | Outcomes of one event priced to more or less than 1 in total |
| 23 | Traded so far | Price bands by contracts traded up to that day |
| 24 | Share of life | Price bands by how much of the scheduled life has passed |
| 25 | Longshot crosses | NO under 15c crossed with days left, momentum, volume, spread, favourite |
| 26 | Dear side | The favourite-longshot bias as one rule: buy the expensive side when the cheap side is under x |
| 27 | Event baskets | NO on every outcome of an event whose YES bids add up to more than 1 |
| 28 | Stand-alone questions | Events listed with one market against outcomes of larger events: price bands, days, spread, volume |
| 15 | Account replay | A rule's bets replayed through an account: lock-up, drawdown, return per year |
| 17, 18 | Claude forecasts | Forward only, through the paper bot |

## 3. Rounds

### 3.1 Round r01, Economics only, preliminary (17:45 UTC)

Data: 1,476 Economics markets in 411 events, 137,928 daily bars, closing 2022-01 to 2026-09; 484 markets out of
sample. These are the largest Economics markets only.

Result: **every one of 1,673 rules is "thin"**. No rule has 100 events on both sides; the out-of-sample half has
at most 85.

One pattern is worth writing down so it can be checked, not believed: in the out-of-sample months, contracts
priced 65 to 95 cents paid out far less often than their price (80 to 90 cents: 65% of 156 markets in 65 events).
I traced the losing bets to the raw bars. They are real: mostly weekly and monthly gas-price markets and CPI
markets in mid-2026, where prices swung from the 90s to single digits within days. It is 65 events concentrated
in two series and one volatile stretch. If favourites in economic-data markets are really overpriced, it will
show up again in the full Economics sample and in other categories.

### 3.2 Round r02, Economics, 2,537 markets (17:55 UTC)

Data: 2,537 Economics markets in 655 events, 208,946 daily bars, closing 2021-08 to 2026-09; 935 markets out of
sample. Two things were added to the engine first: a fixed-horizon snapshot (family 1b: the price a set number of
days before close, whatever path it took), and an event-weighted statistic that counts a 20-rung ladder once.

Result: 2,017 rules. **0 pass, 19 leads, 18 reliably lose**, 344 no, 1,636 still thin.

**What reliably loses** (negative on both sides of the split, both weightings):

| Rule (taker entries) | In sample | t | Out of sample | t | Events in / out |
|---|---|---|---|---|---|
| YES at 50c or more, 60 days before close | −13.6% | −4.7 | −23.8% | −4.8 | 327 / 110 |
| YES at 50c or more, 30 days before close | −9.3% | −3.3 | −20.3% | −4.4 | 335 / 115 |
| YES at 50c or more, 7 days before close | −9.7% | −3.6 | −18.1% | −3.7 | 324 / 115 |
| YES at 80 to 90c, first time there | −8.7% | −3.5 | −15.7% | −3.6 | 305 / 108 |
| YES at 80c or more, 30 days or less to go, tight spread | −4.1% | −2.1 | −10.4% | −3.4 | 297 / 109 |
| NO against a 5 to 10c longshot | −4.3% | −2.4 | −9.2% | −4.5 | 312 / 123 |
| NO against a 5 to 20c longshot quoted 6 to 15c wide | −5.9% | −3.2 | −12.8% | −4.5 | 283 / 112 |

Both ends of the price range are overconfident in this category: favourites win less often than their price, and
longshots come in more often than theirs. Fees and spread explain only 2 to 4 points of these losses. For the
paper bot this matters directly: the README's "lean to favourites" came from studies of other venues and is
wrong for Kalshi Economics on this evidence. Nothing in the bot's config depended on it (it trades 15 to 85
cents on Claude's disagreement with the price), so nothing changes yet.

**The leads all point one way: buy NO.** For example NO at 20 to 80 cents taken 30 days before close: +2.7% in
sample (t 0.5), +22.9% out of sample (t 2.3). None is significant in sample. Breaking the 7-day snapshot down:

- by strike type: the effect is in "above X" markets (588 of 723 bets); there are almost no "below X" markets
  to compare with, so a bias toward YES cannot be told apart from numbers simply coming in low;
- by series: weekly gas prices are a quarter of the bets and return +47%; payrolls return −7%;
- by year: NO lost in 2023 (−16%) and 2024 (−13%) and won in 2022, 2025 and 2026.

So this is a lead with a plausible boring explanation (gas prices and inflation prints came in below what markets
expected through 2025 and 2026). It gets tested where that explanation cannot apply: other categories, and
"below X" markets when enough exist.

**Momentum:** fading a rise (NO after +3 to +5 cents in a day) and following a fall both show up as leads out of
sample and nothing in sample. They are the same NO tilt wearing a different name, not evidence about momentum.

**Still thin:** every price × days cell, the ladders (10 rules), persistence (7), and all combinations.

### 3.3 Round r03, Economics first pass complete, 3,215 markets (18:00 UTC)

Data: 3,215 Economics markets in 845 events (the 4,000 biggest, less those never quoted), 243,542 daily bars;
1,201 markets out of sample. Same 2,018 rules.

Result: **0 pass, 9 leads (down from 19), 15 reliably lose.** Adding 190 events removed half the leads, which is
what leads that were luck look like.

| What held up | In sample | t | Out of sample | t | Events in / out |
|---|---|---|---|---|---|
| Taker NO against a 5 to 10c longshot loses | −5.1% | −3.2 | −8.4% | −4.4 | 383 / 150 |
| ... and against 5 to 20c longshots in markets with under $50 traded that week | −9.8% | −4.1 | −16.3% | −5.1 | 276 / 117 |
| Taker YES at 50c or more, 30 days before close, loses | −8.5% | −3.3 | −14.5% | −3.6 | 419 / 149 |

Selling longshots is the most solid result in the category so far: it loses on both sides of the split, on both
weightings, and loses most where the market is quietest. The other side of that trade, buying those thin
longshots, returns +22% in sample (t 1.2) and +61% out of sample (t 2.5; counted per event, t 1.7). That is a
lead with lottery-ticket variance: most bets lose everything, and it needs several times more events to judge.

The favourite loss is weaker counted per event out of sample (−8 to −9%, t about −2) than per bet: a few big
ladders carry part of it.

The buy-NO leads from 3.2 mostly faded. The one that strengthened is NO at 20 to 80 cents on markets listed 2 to
7 days ago, by resting order: nothing in sample (+2%, t 0.3), +51% out of sample (t 4.2). One half only, so it
stays a lead.

### 3.4 The Economics leads, year by year (19:55 UTC)

Before spending more rounds on the two leads left from 3.3, each was broken down by year, by series and by how
much of its profit comes from its five best events. Same data as 3.3.

| Lead | 2022 | 2023 | 2024 | 2025 | 2026 | Profit from 5 best events | Events that paid |
|---|---|---|---|---|---|---|---|
| Buy thin 5 to 20c longshots (taker) | +218% | +14% | +33% | −19% | +15% | 63% | 25% |
| Buy any 5 to 20c longshot (taker) | +65% | +6% | +31% | −29% | −12% | (net loss recently) | 24% |
| NO at 20 to 80c on markets listed 2 to 7 days ago (resting) | −18% | −10% | −5% | +3% | +30% | 49% | 49% |
| For comparison, the reliable loser: taker NO against 5 to 10c longshots | −9% | −4% | −9% | −2% | −6% | n/a | 83% |

**Both leads are dropped.** The longshot lead is 2022 and five events; it lost in 2025. The young-market lead is
2026 only and lost in every earlier year, which is the pattern of a stretch in which numbers came in low, not of
a pricing habit. The loser, by contrast, loses in every single year, with 83% of its events paying a little and
the rest costing a lot: that is what a real, small, persistent mispricing looks like, and it is on the wrong
side for anyone wanting a "safe" trade.

Where Economics stands after four looks: **no mechanical rule earns money after costs out of sample; two
"conservative" plays reliably lose it.** The engine now reports a year-by-year table for any lead before it is
followed further.

Operational note: this session's worker restarted around 19:10 UTC and killed both background jobs; the download
gained only 160 Politics markets in the hour. Both are restarted, a watchdog check-in now restarts them every
half hour, and the paper loop keeps its schedule in the ledger so a restart does not reset its clock.

### 3.5 Round r04, Politics added, and a flaw in the sample (21:00 UTC)

**Data.** Politics: 1,836 markets in 711 events. Combined with Economics: 5,080 markets, 1,565 events, 391,669
daily bars, 1,775 markets out of sample. 2,190 rules.

**What the round shows.** 1 pass, 49 leads, 50 reliably lose. Politics repeats the Economics pattern:

| Rule (taker unless noted), Economics + Politics | In sample | t | Out of sample | t | Events in / out |
|---|---|---|---|---|---|
| YES at 65 to 80c | −10.5% | −4.2 | −19.3% | −4.7 | 654 / 246 |
| YES at 80 to 90c | −7.6% | −4.1 | −15.4% | −4.6 | 569 / 215 |
| NO against a 5 to 10c longshot | −4.9% | −4.0 | −6.5% | −4.8 | 713 / 293 |
| YES at 0 to 5c, 14 to 30 days out | −65% | −6.6 | −81% | −7.6 | 414 / 166 |
| NO at 65 to 80c, resting order (the mirror of the first row) | +8.9% | 1.3 | +39.9% | 3.4 | 619 / 239 |
| NO against a 0 to 5c longshot, 14 to 30 days out, resting order (the one "pass") | +2.1% | 3.2 | +2.8% | 4.9 | 342 / 150 |

Read at face value: prices are too extreme between about 5 and 95 cents (the dear side loses), and the very
cheapest contracts, under 5 cents, are overpriced.

**Why I do not read it at face value.** Every market in these rounds was among the biggest of its category by
lifetime volume: the median market here traded 66,858 contracts. Lifetime volume is hindsight. A 10-cent
contract that goes on to win trades heavily on its way to a dollar; a 90-cent favourite that collapses does the
same. Choosing the biggest markets therefore over-samples surprises, and surprises are exactly "the dear side
lost". I checked whether the effect grows with volume inside this sample and it does not clearly (favourites:
−10%, −13%, −20%, −15% from the smaller half to the top 5%), but that proves little, because the whole sample is
the top of the distribution.

**What changed.** The download now takes markets in a fixed random order within each category, with no volume
minimum beyond "ever traded", and `research/panel.py` uses only the markets drawn that way. The 5,840 markets
already downloaded biggest-first stay in the database but are excluded by default. A test covers it. The random
Economics sample is downloading now; Politics follows.

**What stays.** The engine, the families, and the rule that any lead gets a year-by-year table. The forward test
of Claude's forecasts is unaffected.

**Also found:** this session's machine is put to sleep about two minutes after a turn ends unless a task tracked
by the session is still running. Detached jobs alone do not keep it awake. That is why the download stalled twice.
Each check-in now leaves a tracked keep-awake task running beside the download.

### 3.6 Round r07 on the random sample: the earlier pattern is gone (4:40 pm CST)

**Data.** The random draw: Economics 1,948 markets in 1,076 events (complete first pass); Politics 1,039 markets
in 684 events (first pass 40% done). About 2,730 rules each.

**Result.** No rule passes in either category.

| YES price, random Economics | YES taker in / out | NO taker in / out | Events in / out |
|---|---|---|---|
| 5 to 10c | −4.9% / +0.4% | −5.6% / −6.8% | 179 / 143 |
| 10 to 20c | −4.5% / −8.2% | −5.7% / −7.9% | 170 / 120 |
| 20 to 35c | −6.3% / +0.1% | −6.0% / −9.1% | 170 / 113 |
| 65 to 80c | −1.1% / −4.1% | −18.6% / −16.0% | 155 / 118 |
| 80 to 90c | −0.8% / −8.2% | −35.8% / +4.1% | 143 / 105 |

- *"Taker YES at 65 to 90c loses" (rounds 3.2 to 3.5):* not confirmed. −1% in sample, −4% to −8% out, neither
  significant. The −10% to −19% of round r04 came from choosing markets by lifetime volume.
- *"Taker NO against 5 to 20c longshots loses":* still negative (−6% to −8%, t about −2.5 to −3), but so is
  every other taker bet here. In the typical Kalshi market the quote is wide and thin, and anyone paying the ask
  on either side loses roughly the spread and the fee. That is a statement about costs, not about mispricing.
- Random Politics looks different from random Economics: cheap YES loses heavily there too (YES at 0 to 5c:
  −71% / −100%; NO against it: +0.6% / +2.2%), the same shape as in the busy markets below.

### 3.7 Round r07 on busy markets: cheap YES is overpriced (4:40 pm CST)

**Why a second sample.** The bot would only ever trade busy markets, and a random draw of 2,500 holds few of
them. The 5,840 markets downloaded biggest-first are exactly the busy ones; what made them unusable was that
rules also saw their early days, before anyone could know they would become big. The busy-market sample keeps a
market only from the day it had traded the set level. Checked: a market's daily bars add up to at most 1.023
times its lifetime volume, so with a 3% margin no market that qualified is missing.

**A second flaw, found on the way.** For a market that closed early, Kalshi's archive shows the early close as
its close time. "At most 30 days to close" then selects the days just before something happened. The download
now keeps each market's expected expiration and the backtest counts days to that. It mattered most in Politics,
where 36% of the yes-resolving markets had closed more than 3 days early. All numbers below are after the fix.

**Data.** Economics and Politics at the 45,000-contract level: 3,313 markets in 1,105 events, 120,938 daily
bars, 1,045 markets out of sample. 2,931 rules: 22 pass, 49 leads, 43 reliably lose. Every pass and every
lead is the same idea: buy NO.

| YES price | YES taker in / out | NO taker in / out | YES resting in / out | NO resting in / out | Events in / out |
|---|---|---|---|---|---|
| 0 to 5c | −73.9% / −75.7% | +1.2% / +1.0% | −78.1% / −80.4% | +2.9% / +2.7% | 464 / 168 |
| 5 to 10c | −66.9% / −52.4% | +2.6% / +2.2% | −57.2% / −47.3% | +5.4% / +4.4% | 409 / 132 |
| 10 to 20c | −44.9% / −33.1% | +3.7% / +1.4% | −43.9% / −18.0% | +7.4% / +4.5% | 375 / 122 |
| 20 to 35c | −24.9% / −27.4% | +2.1% / +4.2% | −16.1% / −22.9% | +5.9% / +7.6% | 345 / 110 |
| 35 to 50c | −14.9% / −13.2% | +0.2% / +0.2% | −11.7% / −8.0% | +3.9% / +1.4% | 287 / 80 |
| 50 to 65c | −9.2% / −6.6% | −2.6% / −3.3% | −5.3% / −1.7% | +3.8% / +5.4% | 271 / 80 |
| 65 to 80c | −4.5% / −4.9% | −9.8% / −10.1% | −2.2% / −0.9% | −2.8% / +2.2% | 267 / 79 |
| 80 to 90c | −0.2% / −3.0% | −24.3% / −8.8% | +2.4% / −1.3% | −13.0% / +3.2% | 262 / 84 |
| 90 to 95c | +0.8% / +0.2% | −39.4% / −36.0% | +3.0% / +3.3% | −23.6% / −9.4% | 251 / 78 |
| 95 to 100c | +0.9% / −1.4% | −71.6% / −45.8% | +2.3% / −0.2% | −63.2% / +2.6% | 285 / 80 |

**How to read it.** Whoever buys the cheap side loses, on either side of the book: YES under 35 cents and NO
under 10 cents (the last three rows) both lose heavily. This is the favourite-longshot bias, and it is what
Bürgi, Deng and Whelan report for Kalshi ("Makers and Takers", cited in the strategy report). The other side of those trades earns something only on one side:
buying NO against a cheap YES is positive in every band under 35 cents, in and out of sample, while buying YES
against a cheap NO is about zero. So there is also a general lean toward YES being overpriced.

**The rules that pass,** all "buy NO where YES is very cheap":

| Rule (busy markets, Economics + Politics) | Entry | In sample | t | Out of sample | t | Win rate out | Events in / out |
|---|---|---|---|---|---|---|---|
| YES at 5c or less, 30 days or less to go, spread 5c or less | taker | +1.3% | 3.2 | +1.7% | 4.7 | 99.7% | 392 / 150 |
| same | resting | +3.0% | 6.4 | +3.2% | 6.9 | 99.6% | 324 / 134 |
| YES at 3 to 6c, spread 1c | taker | +2.5% | 5.1 | +3.1% | 4.7 | 99.1% | 336 / 124 |
| YES at 3 to 6c, fell 1c or more in a day | resting | +4.2% | 6.8 | +4.3% | 5.3 | 98.9% | 295 / 104 |
| YES at 10c or less, 30 days or less to go (a lead: weak when each event counts once) | resting | +3.8% | 5.2 | +3.7% | 4.1 | 98.2% | 367 / 149 |
| YES at 5 to 35c, any time (a lead) | resting | +6.0% | 3.4 | +6.0% | 2.1 | 85.3% | 486 / 159 |

Economics alone at the lower 13,100-contract level shows the same (8 pass, all of this kind). The busy-market
condition matters: in random Economics, most of which is thin, the same bets lose 2% to 6%.

### 3.8 The 5-cent rule taken apart (4:40 pm CST)

*Correction: the account-replay figures in this section were computed with a flawed ordering and are too pessimistic. Corrected figures are in 3.17.*

Rule: busy market, YES at 5 cents or less, spread 5 cents or less, 30 days or less to the scheduled end; buy NO.

| | Taker | Resting order |
|---|---|---|
| Bets, events | 914 in 524 | 736 in 443 |
| Mean return per bet | +1.41% | +3.06% |
| Losing bets | 7 | 6 |
| Losing events in / out of sample | 6 of 392 / 1 of 150 | 5 of 324 / 1 of 134 |
| Break-even loss rate (events) | 3.8% | 6.2% |
| 95% upper bound on the true loss rate | 2.5% | 2.7% |
| Median holding time | 13 days | 13 days |
| Account replay at 1% stakes, before April 2026 (4.4 years) | +0.8% a year, 3% of money at work | +2.3% a year |
| Account replay at 1% stakes, April to September 2026 | +8.6% a year, 17% at work, worst drawdown 1.0% | +13.5% a year |

The tail test passes in both halves: even the pessimistic loss rate is below break-even.

**What to hold against it.**
- *All seven losses are in 2025 and 2026*, five of them in 2025, when the taker version made +0.4% per bet:
  about nothing. Before 2025 there are only 85 bets. So the evidence is two years, one of them flat.
- *Losses come together.* A surprise in one event takes out every longshot NO in it; a broad shock could take
  out several events. The replay's 1% drawdown has not seen that.
- *Resting-order fills are modelled*, from daily highs and lows. The +3% depends on that model; the +1.4%
  taker figure does not.
- *Size.* On the entry day the median market traded 3,300 contracts; one in eight traded under 100. Fine for
  $20 orders, not for much more in the smaller ones.
- *Dollars.* 220 to 265 bets in the last half year at $10 to $20 each is a few dollars a month on $1,000.
- *Two categories, five and a half months out of sample.*

### 3.9 Forward: what was started, and what was not changed (4:40 pm CST)

- **Observation log, no orders.** `scripts/shadow_longshot.py` looks at live Kalshi markets that meet the
  5-cent rule and records the quote, the contracts resting at the NO ask, what a $20 order would have paid on
  that book, and later the settlement. First run: 17 candidates in Economics and Politics, 11 qualified. Dollars
  resting at the NO ask: $50 at the 10th percentile, $113 at the 25th, $3,466 at the median, $16,463 at the
  75th. A $20 order would have filled in full on all 11. It runs after every paper cycle. This is the check the
  backtest cannot do: Kalshi's history has no order books.
- **The paper bot is unchanged.** The rule buys at 95 to 99 cents; the bot's `sizing.max_price` is 0.88 and its
  universe stops at 85 cents. Raising either because a backtest looks good is what I said I would not do. If you
  want the rule traded on paper, the clean way is a second paper account with its own limits, so the forecast
  test and the rule test do not mix. That is your call.
- **Paper cycles.** 12:52 pm: 4 forecasts, 1 resting order (NO on the December 12 shutdown market, $20 at 65c).
  3:56 pm: 4 forecasts, no order (3 low confidence, 1 edge of 0.9 points against the 3 required). Six of eight
  forecasts were marked low-confidence by the forecaster itself. The order has not filled.

### 3.10 How far the price is from the truth (4:55 pm CST)

Returns mix three things: the level of the price, the spread and the fee. This table takes the last two out. For
each market, at the first tradable bar on which the mid was in the band: the mid, and how often YES happened
(`research/calibration_curve.py`; errors clustered by event).

| YES mid | Busy markets (45,000+ contracts), in sample | | | Busy, out of sample | | | Random markets, in / out |
|---|---|---|---|---|---|---|---|
| | mid | YES happened | gap (t) | mid | YES happened | gap (t) | gap |
| 0 to 5c | 3.5% | 1.2% | −2.2 (−6.0) | 3.1% | 1.3% | −1.9 (−3.4) | −1.4 / +0.1 |
| 5 to 10c | 7.8% | 3.5% | −4.2 (−6.2) | 7.8% | 4.2% | −3.5 (−2.9) | −1.1 / +0.7 |
| 10 to 20c | 15.5% | 10.0% | −5.5 (−4.4) | 15.1% | 11.7% | −3.4 (−1.6) | −0.7 / +0.8 |
| 20 to 35c | 27.7% | 23.2% | −4.5 (−2.3) | 27.7% | 22.1% | −5.6 (−1.6) | −1.3 / −1.5 |
| 35 to 50c | 41.9% | 38.5% | −3.4 (−1.4) | 41.8% | 38.7% | −3.0 (−0.6) | −0.1 / +3.4 |
| 50 to 65c | 57.1% | 54.8% | −2.3 (−0.9) | 57.4% | 55.6% | −1.8 (−0.3) | −2.1 / +2.7 |
| 65 to 80c | 71.2% | 70.9% | −0.2 (−0.1) | 72.2% | 71.2% | −1.0 (−0.2) | −0.8 / −2.7 |
| 80 to 90c | 84.6% | 86.6% | +2.0 (+1.0) | 84.9% | 84.4% | −0.5 (−0.1) | +2.5 / −4.0 |
| 90 to 95c | 92.2% | 94.6% | +2.4 (+1.7) | 92.2% | 94.1% | +1.9 (+0.7) | +3.1 / −0.3 |
| 95 to 100c | 96.5% | 98.5% | +2.0 (+2.6) | 96.9% | 96.8% | −0.2 (−0.1) | −1.0 / +1.6 |

Gaps are in percentage points. Busy: Economics and Politics, 1,105 events. Random: the same two categories,
1,760 events.

- **In busy markets a YES priced under 50 cents happened about 2 to 5 points less often than its price said,** in
  both halves. Under 10 cents it is established (t of −6 in sample, −3 out). Between 10 and 50 cents the size
  is the same but the out-of-sample evidence is thin (t of −0.6 to −1.6 on 80 to 122 events).
- **In the exchange as a whole the price is about right.** No gap in the random sample is distinguishable from
  zero in both halves. The mispricing lives where the volume is.
- **What it means for the forecast bot (not applied).** The bot treats the market price as its starting point
  and moves 30% of the way to Claude's number. In a busy market with YES under about 35 cents, the evidence says
  the starting point itself is 3 to 5 points high. A bot that started from a corrected price would lean toward NO
  there before Claude says anything. I have not changed it: the out-of-sample support above 10 cents is
  weak, the bot's own "busy" bar ($1,000 traded) is lower than the level tested here, and the correction
  should first be re-measured at that level and on more categories. It is on the list.

### 3.11 Round r08: Economics at the lower volume level (5:48 pm CST)

**Data.** The Economics census is now complete down to 5,000 contracts: 5,289 markets in 1,397 events seen from
the day they had traded 5,150 contracts (was 3,187 markets at 13,100). 2,761 rules: 26 pass, 52 leads, 51 lose.
Every pass is again "buy NO where YES is very cheap".

| 5-cent rule, Economics, 5,150+ contracts | Taker | Resting order |
|---|---|---|
| Bets, events | 1,076 in 554 | 786 in 440 |
| Mean return per bet | +1.27% | +3.35% |
| Losing events in / out of sample | 6 of 379 / 3 of 176 | 4 of 289 / 3 of 152 |
| Break-even loss rate; 95% upper bound on the true rate | 4.0%; 2.8% | 7.2%; 3.0% |
| Account replay at 1% stakes, before April 2026 / after | +1.3% a year / +9.0% a year | +3.2% / +15.0% a year |
| Entry days with under 100 contracts traded | 24% | 18% |

- **The rule holds at the lower level**, and the tail test passes in both halves.
- **2024 was a losing year for it** at this level: 80 bets, 4 total losses, −3.0% per bet. The 45,000-contract
  sample had no 2024 loss, so the smaller markets carry more of the tail. A year like that costs about three
  years of the rule's pre-2026 income.
- **The wider mispricing fades as markets get smaller.** Paying the ask for NO against YES at 5 to 35 cents is
  about zero here (+0.6% / +0.4% at 5 to 10c, −0.5% / −0.1% at 10 to 20c), against +2% to +4% at 45,000
  contracts. The price gap of section 3.10 is 2 to 3 points here instead of 3 to 5. With the random-sample
  result (under 1,000 contracts: negative) this is a steady gradient: the more a market has traded, the more
  overpriced its cheap YES.
- **Thinner entries.** A quarter of entry days traded under 100 contracts, twice the share at the higher level.

**What a loss looks like.** The nine Economics losses are data surprises: CPI for January 2024 above 0.2%
(bought NO at 99c), core CPI the same month, payrolls for January 2024 at 300,000 or more, payrolls for
September 2024 above 250,000, CPI for January 2025 above 0.4%, payrolls for January 2026 above 125,000, the
weekly gas price, Argentina's monthly inflation, the petroleum reserve level. Three of the nine came from one
month's releases (January 2024): the losses are not independent, which is the clustering risk of section 3.8
showing up in the record. The Politics losses in the 45,000-contract sample are "will X happen before a date"
questions where X then happened: a veto, a resignation, a White House visit, a tariff ending.

**Housekeeping.** The session's container was restarted at about 5:45 pm CST. The data survived; the download
and the paper loop were restarted within two minutes.

### 3.12 Round r09: Politics in full, and a weaker result there (6:52 pm CST)

**Data.** The random Politics draw is complete (2,744 markets, 1,400 events). The Politics census has reached
15,000 contracts and is still going down: 3,342 Politics markets in 1,209 events at that level, 6,323 markets in
1,994 events with Economics.

**Random Politics: 1 pass in 2,780 rules,** about what chance gives. YES is overpriced at every price (paying the
ask for YES lost 4% to 65% in both halves), but paying the ask for NO only breaks even, because the quotes are
wide. The pass and the three leads next to it are one idea: NO where YES is at 10 to 20 cents or less with two or
three days to the scheduled end (+1.9% / +2.1%).

**Busy markets at 15,000 contracts, both categories: 60 pass, 100 leads, every one of them "buy NO".** No rule
that buys YES passes or leads anywhere.

| YES price (15,000+ contracts) | NO taker in / out | NO resting in / out | Events in / out |
|---|---|---|---|
| 0 to 5c | +0.7% / +1.1% | +2.6% / +2.7% | 730 / 323 |
| 5 to 10c | +0.2% / +2.1% | +3.1% / +4.5% | 681 / 263 |
| 10 to 20c | +0.2% / +0.5% | +3.5% / +2.5% | 652 / 259 |
| 20 to 35c | +0.4% / +1.8% | +5.1% / +5.2% | 599 / 240 |
| 35 to 50c | +2.2% / −0.5% | +6.6% / +2.5% | 515 / 209 |

**The 5-cent rule on Politics alone is weaker than on Economics.**

| 5-cent rule, Politics, 15,000+ contracts | Taker | Resting order |
|---|---|---|
| Bets, events | 1,027 in 535 | 797 in 428 |
| Mean return per bet | +0.79% | +2.28% |
| Losing events in / out of sample | 10 of 380 / 4 of 176 | 9 of 298 / 4 of 148 |
| Break-even loss rate; 95% upper bound, in sample | 3.7%; 4.4%: **not** below | 6.8%; 5.2% |
| The same, out of sample | 4.5%; 5.1%: **not** below | 7.0%; 6.1% |
| 2025 alone | 270 bets, 10 lost, −1.6% per bet | 203 bets, 9 lost, −0.4% per bet |
| Account replay at 1% stakes, before April 2026 / after | 0.0% a year, drawdown 5.9% / +7.9% a year | +1.2% / +12.8% a year |

- **Paying the ask does not pass the tail test in Politics**, in either half. The observed loss rate (2.6%) is
  below break-even (4.1%), but with 14 losing events the data cannot rule out a true rate above it. In 2025 the
  rule lost money in Politics.
- **The resting-order version passes**, and its margin is what makes the difference: it buys a cent or two
  cheaper. That margin rests on a fill model, not on observed fills.
- **So the statement in the status section needs its qualifier:** the rule is supported in Economics by both
  entries at two volume levels (3.8, 3.11); in Politics only with resting orders. Politics questions are
  "will X happen before a date", where the cheap YES is a real event that sometimes happens, in clusters
  (the first months of a new administration, 2025, are where the losses are).

**Housekeeping.** The container restarted a second time at about 6:40 pm CST. Data intact; jobs restarted within
a minute.

### 3.13 Round r10: both categories at 5,000 contracts; the taker version does not survive in Politics (8:07 pm CST)

**Data.** The Politics census is complete down to 5,000 contracts: 5,620 markets in 1,775 events. With
Economics: 10,909 markets, 3,172 events, 362,482 daily bars, 4,388 markets out of sample. 2,957 rules: 26 pass,
117 leads, 172 reliably lose. All 26 passes and 116 of the leads buy NO.

| YES price (5,150+ contracts, both categories) | YES taker in / out | NO taker in / out | NO resting in / out | Events in / out |
|---|---|---|---|---|
| 0 to 5c | −64.4% / −58.2% | +0.3% / +0.3% | +2.2% / +1.5% | 1,076 / 540 |
| 5 to 10c | −45.7% / −36.6% | 0.0% / 0.0% | +2.7% / +1.7% | 1,038 / 479 |
| 10 to 20c | −30.0% / −23.5% | 0.0% / −0.4% | +2.9% / +1.5% | 1,052 / 472 |
| 20 to 35c | −23.7% / −19.0% | +0.3% / +0.4% | +4.1% / +2.3% | 960 / 433 |
| 35 to 50c | −14.7% / −14.2% | −2.1% / −0.1% | +1.7% / +1.4% | 822 / 390 |

At this level, paying the ask for NO is worth nothing in any band: the overpricing of YES is about the size of
the spread plus the fee. A resting NO order keeps the spread and earns 1.5% to 4%.

**The 5-cent rule at 5,150+ contracts.**

| | Politics, taker | Politics, resting | Both, taker | Both, resting |
|---|---|---|---|---|
| Bets, events | 1,670 in 809 | 1,207 in 614 | 2,746 in 1,363 | 1,993 in 1,054 |
| Mean return per bet | +0.14% | +1.31% | +0.58% | +2.11% |
| Losing events | 33 | 32 | 42 | 39 |
| Tail test in / out of sample | fails / fails | passes / fails | passes / fails | passes / passes |
| 2025 alone | −1.8% per bet | −0.9% | −0.4% | +1.4% |
| Replay at 1% stakes, before April 2026 / after | −0.7% / −1.2% a year | +0.9% / +3.8% | +0.3% / −3.3% | +3.5% / +12.7% |

- **Politics, paying the ask: no edge.** 33 losing events in 809 (4.1%) against a break-even of 4.4%.
- **Economics carries the taker result** (3.11): +1.27% per bet, tail test passed, at the same volume level.
- **The resting version passes on the pooled sample and in Economics; in Politics alone it passes in sample and
  not out.**
- **Reading the whole evening together:** the edge grows with how much a market has traded (45,000+ contracts:
  3.8; 15,000+: 3.12; 5,000+: here; everything: 3.6) and is larger in Economics than in Politics. That is the
  pattern "Makers and Takers" describes: takers, who mostly buy YES and mostly buy cheap contracts, pay; the
  resting side collects.

**Also checked: the last days before the end are not special.** NO where YES is at 5 to 20 cents with one to
three days to the scheduled end earns +0.5% to +1.5% paying the ask on the busy sample, not significant. The
edge is not concentrated at the close, so hourly bars for the final days are dropped from the list.

**What this changes in the plan.** The question that decides whether any of this is usable is whether a small
resting NO order really gets filled at those prices, and how often it is filled only when it is about to lose.
The backtest cannot answer that. So the forward observation log now tracks it with real trades (8:10 pm CST):
for each qualifying market it notes the best NO bid and how many contracts were already queued there, then
reads Kalshi's public trade tape for three days. The hypothetical order counts as filled only if buyers of YES
traded through that price, or took everything queued ahead of it plus the order itself. First reading, four
hours after the first 11 observations: 2 filled, both by a trade through the price, which is the bad kind of
fill (YES was rising). Their outcomes, and the fill rate against the model's 55% to 60%, will take days to
weeks to mean anything.

### 3.14 Wider bands fail as an account; so does the price correction above 10 cents (8:55 pm CST)

*Correction: the account-replay figures in this section were computed with a flawed ordering and are too pessimistic. Corrected figures are in 3.17.*

**Why look.** At 5,000+ contracts a resting NO order earned +1.5% to +4% per bet in every band under 50 cents
(3.13), which suggests a much bigger rule than the 5-cent one: rest NO bids against any cheap YES. Sample: both
categories, 5,150+ contracts.

| Rule, resting order | Bets | Mean per bet | Replay at 1% stakes, before April 2026 | After | Worst drawdown |
|---|---|---|---|---|---|
| NO where YES is 35c or less, any time | 4,868 | +2.61% | −4.6% a year | −9.6% a year | 28.7% |
| NO where YES is 5 to 35c | 3,953 | +2.85% | −5.4% a year | +0.1% a year | 30.6% |
| NO where YES is 10c or less, 30 days or less | 2,554 | +2.42% | +5.6% a year | +11.0% a year | 6.7% |
| NO where YES is 5c or less, 30 days or less (3.13) | 1,993 | +2.11% | +3.5% a year | +12.7% a year | 3.1% |

**A positive mean per bet and a losing account.** The mean counts every market. The account cannot: it caps
each event at 3% of equity and has half its money locked for weeks (median holding 20 days, mean 55). The bets
it has to skip are the many outcomes of a few very large events, "who will be the next ..." with thirty names,
where buying NO on every longshot wins twenty-nine times by construction. Count each event once and the wide
rules earn nothing: their event-weighted t out of sample is −0.6 and −0.8. This is what the second statistic in
the pass test is for, and it is why these rules were "leads" and not passes.

**The same correction applied to section 3.10.** Price against outcome with each event counted once, 5,150+
contracts, both categories (gap in percentage points; t in brackets):

| YES mid | In sample, per market | In sample, per event | Out of sample, per market | Out of sample, per event |
|---|---|---|---|---|
| 0 to 5c | −1.6 (−4.9) | −1.7 (−4.7) | −1.3 (−3.6) | −1.4 (−2.9) |
| 5 to 10c | −2.3 (−3.3) | −3.4 (−6.0) | −1.7 (−2.1) | −1.4 (−1.4) |
| 10 to 20c | −2.7 (−2.8) | −4.4 (−5.1) | −1.8 (−1.5) | −0.7 (−0.5) |
| 20 to 35c | −3.7 (−2.8) | −6.2 (−5.2) | −2.9 (−1.6) | −1.6 (−0.9) |
| 35 to 50c | −2.7 (−1.6) | −3.9 (−2.6) | −3.1 (−1.3) | −1.7 (−0.8) |

- **Under 5 cents the overpricing is solid however it is counted:** a YES at 3.3 cents happened about 1.9% of the
  time, in both halves.
- **Above 10 cents it was there before April 2026 and is not distinguishable from zero since.** The idea in 3.10
  of starting the forecast bot from a corrected price for YES under 35 cents is withdrawn.

**Companies** finished downloading and is too small to judge: 225 markets in 79 events, 11 of them out of
sample. It will only count pooled with the rest. **Commodities** (264,635 markets, mostly daily price ranges the
bot does not trade) was moved behind Science and Technology, Elections, Health and World.

### 3.15 Family 27: baskets across an event's outcomes. No free money (10:06 pm CST)

**The idea.** If the outcomes of an event exclude each other, at most one YES wins, so NO on n of them pays at
least n − 1. If the YES bids of those n add up to more than 1 plus fees, the basket is a locked profit.

**Test** (`research/event_baskets.py`). Busy sample, both categories, events without numeric strikes. Basket
formed on the first day the closing bids of the legs present add up to the threshold; every leg bought at the
next day's opening quote with the taker fee; result is what the basket actually paid. Kalshi's own
"mutually exclusive" flag was fetched for all 405 candidate events: 154 are exclusive, 251 are not.

| Bids add up to | Exclusive events: baskets in / out | Mean return in / out | Worst | Not exclusive: mean in / out |
|---|---|---|---|---|
| 0.90 or more | 92 / 62 | −3.5% / −0.6% | −11.8% | the "lock" does not exist; most lose |
| 1.00 or more | 33 / 29 | −0.9% / −0.9% | −3.3% | |
| 1.02 or more | 3 / 9 | −0.2% / −0.5% | −1.4% | |
| 1.05 or more | 1 / 0 | +0.2% | | |

- **Exclusive events are priced tightly.** In five years of busy Economics and Politics markets the bids of an
  exclusive event's outcomes reached 1.05 once. At 1.00 to 1.02 the basket is locked, at a small loss: the
  taker fee on every leg is more than the excess.
- **Events that only look exclusive are a trap.** "Before June?" and "before December?" have no numeric strike
  and their bids add up to well over 1, but both can be yes. Treating those as a lock lost on 191 of 264 baskets
  in sample. Any rule of this kind must read Kalshi's flag, never infer it.
- Verdict: nothing here. It also explains 3.14 from another side: inside a large exclusive event the outcomes
  are priced consistently with each other, so the longshot overpricing there is a few tenths of a cent per
  outcome, real per bet and too thin to carry an account.

### 3.16 Round r11: Science and Technology, a third category (10:53 pm CST)

**Data.** Science and Technology is small enough to have been downloaded almost whole: 3,893 of its 3,906 traded
markets. Random sample 3,850 markets in 637 events; busy sample (5,150+ contracts) 1,559 markets in 417 events.
It is a 2026 category: three quarters of its markets closed after April 1.

**Random sample: 0 pass, 0 leads** in 2,756 rules. The two halves disagree in sign almost everywhere (NO at 20
to 80 cents: +2% to +17% before April, −20% to −43% after), which is what noise from a few large event families
looks like.

**Busy sample: 0 pass, 11 leads, all resting NO where YES is cheap** (+3% to +5% out of sample, +0.1% to +3.6%
in). Too few events for anything to pass alone (about 140 in, 100 out).

| 5-cent rule, 5,150+ contracts | Sci & Tech, taker | Sci & Tech, resting | Three categories, taker | Three categories, resting |
|---|---|---|---|---|
| Bets, events | 519 in 250 | 397 in 216 | 3,265 in 1,613 | 2,390 in 1,270 |
| Mean return per bet | +0.08% | +1.32% | +0.50% | +1.98% |
| Losing events | 10 | 10 | 52 | 49 |
| Tail test in / out of sample | fails / fails | fails / fails | fails / fails | passes / passes |
| Replay at 1% stakes, before April 2026 / after | −0.6% / +2.0% a year | +0.1% / +5.3% | −0.7% / −2.9% | +3.1% / +11.4% |

- **Third category, same picture as Politics:** paying the ask earns nothing; resting earns something, not enough
  events to prove it alone.
- **Pooled over three categories the resting version passes in both halves** with 1,270 events, and the taker
  version fails in both. This is now the firm shape of the result.
- **Scale, pooled, resting, 1% stakes:** 916 bets in four and a half years before April 2026, 653 in the half
  year after. Kalshi's growth in 2026 is why the recent replay earns four times the earlier one: more qualifying
  markets, so more of the account is at work (33% against 7%).

**Paper cycle at 10:03 pm.** Two new resting paper orders from Claude's forecasts: buy YES $20 at 70c on
`KXTRUMPACT-26NOV15-T2` (Claude's blended 77%), buy NO $20 at 40c on `KXCBDHUNGARY-26DEC15-C25` (blended 47% for
NO). Three resting orders in all, none filled.

### 3.17 A flaw in the account replay, corrected; and where to rest the order (11:56 pm CST)

**The flaw.** `research/portfolio.py` replays a rule's bets in time order through an account with a cap per
event. Bets entered on the same day were ordered by their eventual return, lowest first. With a cap of three bets
per event, an event with ten longshots and one winner always had its one losing NO among the three taken. That
is using the outcome, in the pessimistic direction. Same-day bets are now taken in an order unrelated to the
outcome, and a test holds it there. Means per bet, t-statistics and tail tests never used this code and are
unchanged. Every "replay" figure in 3.8 to 3.16 did.

**Corrected replays, 1% stakes, 5-cent rule** (was → is; a year, before April 2026 / after):

| Sample | Taker | Resting |
|---|---|---|
| Economics + Politics, 45,000+ (3.8) | +0.8% / +8.6% → +1.0% / +8.6% | +2.3% / +13.5% → unchanged |
| Economics, 5,150+ (3.11) | +1.3% / +9.0% → +1.3% / +9.1% | +3.2% / +15.0% → +3.3% / +15.1% |
| Politics, 15,000+ (3.12) | 0.0% / +7.9% → +0.2% / +7.9% | +1.2% / +12.8% → +1.5% / +12.8% |
| Politics, 5,150+ (3.13) | −0.7% / −1.2% → −0.6% / +0.8% | +0.9% / +3.8% → +1.1% / +3.9% |
| Economics + Politics, 5,150+ (3.13) | +0.3% / −3.3% → +0.5% / +4.4% | +3.5% / +12.7% → +3.8% / +15.4% |
| Science and Technology, 5,150+ (3.16) | −0.6% / +2.0% → unchanged | +0.1% / +5.3% → unchanged |
| Three categories, 5,150+ (3.16) | −0.7% / −2.9% → −0.4% / +3.1% | +3.1% / +11.4% → +3.4% / +17.6% |

**Corrected replays, wide rules of 3.14** (resting, Economics + Politics, 5,150+):

| Rule | Before April 2026 | After | Worst drawdown |
|---|---|---|---|
| NO where YES is 35c or less, any time | −4.6% → −3.2% a year | −9.6% → +6.5% a year | 28.6% |
| NO where YES is 5 to 35c | −5.4% → −2.8% a year | +0.1% → +7.6% a year | 27.5% |
| NO where YES is 10c or less, 30 days or less | +5.6% → +5.6% a year | +11.0% → +14.7% a year | 5.0% |

**What changes in the conclusions.**
- Nothing about which rules pass. The pooled taker replay is now slightly positive after April 2026 instead of
  slightly negative; its tail test still fails in both halves, so the verdict on paying the ask stands.
- The resting version looks better: +3.4% a year before April 2026 and +17.6% after, across three categories.
- The wide rules are no longer "lose in both periods": they lost about 3% a year with a 28% drawdown for four
  and a half years and then gained 7% a year. With an event-weighted t below zero that is still not a rule to
  trade, but 3.14 overstated the case.

**Where to rest the order, and for how long** (`research/resting_variants.py`; three categories, 5,150+
contracts; YES at 5 cents or less, 30 days or less, spread 5 cents or less). "Deeper" is cents below the best NO
bid; −1 is a cent better than the best bid, possible where the spread is 2 cents or more. A fill always needs a
trade through the price.

| Deeper (cents) | Days working | Fill rate | Bets | Mean per bet in / out | Losing events in / out | Replay in / out, a year |
|---|---|---|---|---|---|---|
| −1 | 3 | 74% | 1,825 | +2.2% / +2.4% | 22 of 783 / 8 of 333 | +3.0% / +21.2% |
| 0 | 1 | 42% | 2,277 | +2.2% / +1.5% | 25 of 782 / 21 of 462 | +3.6% / +16.4% |
| 0 (the sweeps' setting) | 3 | 54% | 2,390 | +2.2% / +1.7% | 28 of 815 / 21 of 479 | +3.4% / +19.8% |
| 0 | 7 | 61% | 2,445 | +2.3% / +1.8% | 29 of 837 / 21 of 480 | +3.4% / +21.5% |
| 1 | 3 | 37% | 1,837 | +2.7% / +2.2% | 27 of 654 / 21 of 409 | +3.6% / +17.5% |
| 2 | 3 | 28% | 1,469 | +3.0% / +2.7% | 27 of 537 / 21 of 353 | +3.2% / +22.2% |
| 3 | 3 | 22% | 1,212 | +3.6% / +3.2% | 25 of 449 / 21 of 326 | +3.6% / +26.8% |

All 15 combinations tried (five depths, three windows) pass the tail test in both halves. Resting deeper trades
fewer fills for more per fill and the account ends up in about the same place; leaving the order longer adds
fills at no cost. So there is no setting to tune here, which is what a real effect looks like and a fitted one
does not. (This table's replays differ a little from the one above for the same rule because the two programs
break same-day ties differently; neither uses the outcome.)

### 3.18 Round r12: Elections, a fourth category (12:54 am CST, November 19)

**Data.** Kalshi's archive has Elections only from November 2024. Random sample complete: 2,511 markets in 1,244
events. Busy sample at the level downloaded so far (23,000+ contracts; still descending to 5,000): 2,247 markets
in 794 events.

**Random: 0 pass, 0 leads** of 2,780. Paying the ask for YES loses at every price (−5% to −66%), as in Politics;
NO earns nothing either.

**Busy: 0 pass, 3 leads** of 2,756, none of them the longshot rule.

| 5-cent rule, 23,000+ contracts | Elections, taker | Elections, resting | Four categories, taker | Four categories, resting |
|---|---|---|---|---|
| Bets, events | 255 in 169 | 170 in 115 | 1,923 in 1,059 | 1,493 in 858 |
| Mean return per bet | +0.07% | +0.91% | +1.04% | +2.55% |
| Losing events | 4 | 4 | 20 | 19 |
| Tail test in / out of sample | fails / fails | fails / fails | passes / passes | passes / passes |
| Replay at 1% stakes, before April 2026 / after | +0.5% / −1.4% a year | +1.0% / 0.0% | +0.9% / +12.1% | +3.3% / +23.1% |

- **Elections does not show the effect.** Few bets qualify (election markets are long-dated; the rule wants 30
  days or less to the end), and where they do, a YES at 3 cents happened about as often as its price said after
  April 2026 (gap 0.0 points per market, −0.6 per event, against −1.3 and −1.4 in Economics and Politics).
- **Category by category the rule is now: Economics yes; Politics and Science and Technology with resting orders
  only, not proven alone; Elections no.** Pooled, it passes, because Economics and the busiest Politics markets
  carry it.
- **Volume matters more than category.** At 23,000+ contracts the pooled taker version passes the tail test in
  both halves (+1.04% per bet); at 5,150+ it did not (+0.50%, 3.16).

### 3.19 Round r13: all seven of the bot's categories, and where the effect lives (1:57 am CST, November 19)

**Data.** Elections is complete down to 5,000 contracts; Health (616 markets) and World (795) are downloaded
whole and are too small and too old to judge alone (3 markets between them closed after April 1). Pooled busy
sample, 5,150+ contracts: 17,522 markets in 5,316 events, 593,068 daily bars, 8,193 markets out of sample.
Pooled random sample: 12,378 markets in 5,202 events.

**Random, seven categories: 1 pass, 7 leads** of about 3,750 rules: chance. **Busy, seven categories: 17 pass,
120 leads.** 16 of the passes buy NO against a YES under 20 cents (most under 6); the other rests YES bids at 95
cents or more in one question type.

| 5-cent rule, 5,150+ contracts | Seven categories, taker | Seven categories, resting | Elections, taker | Elections, resting |
|---|---|---|---|---|
| Bets, events | 3,828 in 1,987 | 2,744 in 1,518 | 423 in 250 | 262 in 168 |
| Mean return per bet | +0.43% | +1.85% | −0.45% | +0.22% |
| Losing events | 61 | 58 | 8 | 8 |
| Tail test in / out of sample | fails / fails | passes / passes | fails | fails |
| Replay at 1% stakes, before April 2026 / after | −0.2% / −0.3% a year | +3.6% / +14.8% | +1.0% / −5.1% | +1.0% / −2.4% |

**Where the effect lives: the size of the event.** NO against a YES at 5 cents or less, by how many markets the
exchange listed in the event:

| Markets in the event | Taker, in / out of sample | Resting, in / out | Events in / out |
|---|---|---|---|
| 1 (a stand-alone yes/no question) | +1.7% (t 4.4) / +2.2% | +3.9% (t 8.2) / +4.1% | 609 / 87 |
| 2 to 4 | +0.8% / −0.6% | +2.9% / +0.3% | 311 / 259 |
| 5 to 10 | −0.4% / −0.6% | +1.2% / +0.3% | 529 / 545 |
| 11 or more | −0.4% / +0.1% | +1.4% / +1.4% | 243 / 233 |

- **Single-market events carry the taker result.** 696 bets, 5 lost (0.7%) against a break-even of 2.4%; the 95%
  upper bound on the true loss rate is 1.5%. Since April 2026: 87 bets, none lost. That is too few to pass
  out of sample alone (with 87 the bound is 3.4%).
- **Inside multi-outcome events the cheap outcomes are priced about right** for someone paying the ask, which
  agrees with 3.15: those events are tightly priced as a set.
- **Why it is not a bigger finding:** these questions are scarce and thin. 87 qualified in the last half year
  against 302 for all of 2026; 38% of entry days traded under 100 contracts; median holding 30 days. Replay at
  1% stakes: +1.0% a year before April 2026, +3.0% a year after, with 6% to 13% of the account at work.
- **One step up in price (YES at 5 to 10 cents, single-market events):** +2.7% taker and +6.0% resting per bet,
  21 losses in 606, passes in sample and is unproven out of sample (67 events, 3 lost).

**A correction to the measure.** "Markets in the event" used to count the markets present in the sample, so the
one busy market of a thirty-outcome event counted as an event of one. It now counts the markets the exchange
listed. The table above uses the corrected count; no earlier conclusion rested on the old one.

### 3.20 Family 28: stand-alone questions (2:53 am CST, November 19)

**Why.** 3.19 found the taker edge in events the exchange lists with a single market. This family tests that
directly: 132 rules on single-market events (price bands on both sides; NO against a cheap YES by days left, by
spread, by recent volume), with the same bands on multi-market events as a control. Seven categories, both
samples.

**Result: none can pass, because none has 100 events out of sample.** Kalshi lists few stand-alone questions now:
of 1,561 in the busy sample, 245 closed after April 1, 2026. Every rule in the family is "thin" by the rule
fixed before any result was seen.

What the family shows without passing (busy sample; NO where YES is 5 cents or less):

| Condition, single-market events | Entry | In sample (events) | t | Out of sample (events) | Lost out of sample |
|---|---|---|---|---|---|
| spread 5c or less | taker | +1.7% (608) | 4.6 | +2.3% (87) | 0 |
| spread 5c or less | resting | +3.8% (503) | 8.2 | +4.1% (54) | 0 |
| 30 days or less to the end | taker | +1.4% (551) | 4.4 | +2.0% (62) | 0 |
| 30 to 90 days to the end | taker | +2.1% (325) | 6.4 | +2.7% (22) | 0 |
| $200+ traded in the last 7 days | resting | +4.3% (280) | 8.0 | +4.2% (34) | 0 |
| YES at 10c or less, 30 to 90 days | resting | +7.4% (352) | 15.6 | +7.6% (22) | 0 |

- **In sample it is the strongest thing found tonight** (t of 4 to 16 on 280 to 600 events, every variant
  positive), and since April 2026 every variant under 5 cents is positive with no loss. On the random sample the
  same rules are positive in sample (+1% to +5%) and mixed after, on 5 to 44 events.
- **It still does not pass**, and I am not going to move the split date or lower the 100-event bar to make it.
  Honest reading: well supported before April 2026, consistent since, not proven, and with about 15 qualifying
  questions a month across seven categories it is tiny.
- **Forward.** The observation log now records how many markets each qualifying event has, so stand-alone
  questions can be followed separately as they come.


### 3.21 Rounds r15 and r16: Commodities and Financials (5:15 am CST, November 19)

**What was new.** Commodities finished downloading at 4:13 am (random pass and census); round r15 was run then
but not written up. Financials' random pass finished at 4:30 am; its census of busy markets is still coming
down, so only the random sample of Financials can be judged yet (r16).

**Commodities alone: too small to say anything.** Random sample 806 markets in 527 events, busy sample 1,241
markets in 319 events, and almost all of it closed after April 1, 2026 (2 to 16 events per price band before).
Every one of about 2,780 rules is "thin" on both samples: 0 pass, 0 leads, 0 lose.

The 5-cent rule there (NO where YES is 5 cents or less, 30 days or less, spread 5 cents or less; busy sample):

| Entry | Bets (events) | Mean per bet | Lost | Tail test |
|---|---|---|---|---|
| taker | 79 (28) | -0.22% | 2 | fails (26 events since April, none lost; bound 10.9% against 5.7% break-even) |
| resting | 64 (24) | +0.50% | 2 | fails (22 events since April; bound 12.7% against 8.2%) |

Both losses are weekly oil price markets (KXWTIW, which has 71% of the bets). Bets last 1.6 days; a median of
$1,363 traded in the 7 days before entry. Not a failure of the rule and not support for it: too few events.

**Eight categories pooled (busy sample, 19,619 markets, 6,142 events; 4,145 rules):** 19 pass, 143 leads, 306
lose. 18 of the 19 are resting NO orders against a cheap YES, the same picture as r13 (3.19); the other is a
resting YES at 95 cents and above on "custom" questions. On the random sample (4,315 rules): 1 pass, 5 leads,
105 lose, which is what chance gives.

The 5-cent rule pooled over eight categories, with the account replay at 1% stakes:

| Entry | Events in / out | Mean per bet | Tail test in / out | Replay in / out, per year | Worst drawdown in / out |
|---|---|---|---|---|---|
| resting | 1,026 / 584 | +1.77% | passes / passes (bounds 4.7% and 6.1% against break-even 6.8% and 7.4%) | +3.3% / +12.1% | 3.4% / 5.0% |
| taker | 1,426 / 701 | +0.36% | fails / fails (bounds 3.7% and 5.1% against 3.4% and 4.7%) | -0.7% / -1.9% | 7.4% / 5.8% |

Adding Commodities changed nothing: the resting version passes, paying the ask does not, as in 3.19. Capacity is
unchanged and small: the median qualifying market traded $209 in the 7 days before entry (a quarter under $66),
and 22% of entry days traded under 100 contracts. The resting result still rests on the fill model (52% filled);
the forward log has 5 resting bids decided so far, all 5 filled, none settled.

**Financials, random sample (r16: 1,890 markets, 1,184 events, 1,310 markets since April; 2,840 rules):** 0 pass,
0 leads, 8 reliably losing. All eight are the same bet, paying the ask for NO where YES is at 50 cents or less:
-5% to -7% per bet before April 2026 and -13% to -16% after (t -3.1 to -3.6 by event, 150 to 200 events each
side); one more, NO in the last week on questions without deadline wording, lost 30% after April. So in
Financials' small markets the cheap side won more often than its price said, the opposite of the busy markets of
the other categories. These are mostly daily and weekly index and rate ranges. The busy sample of Financials
decides whether this is a property of the category or of thin quotes: run it when the census is complete.

**Variant paper accounts (12 accounts: the main one, 9 that follow Claude under other rules, 2 controls):** no
market has settled, so there are no standings. Only `claude_only_taker` has filled orders (3 positions, -$2.65
marked at the bid, which is the spread it paid); the two controls (`control_fade`, `control_coinflip`) have 5
resting orders each and $1,000.

### 3.22 Rounds r17 and r18: Financials' busy markets, nine categories pooled, Mentions (6:30 am CST, November 19)

**What was new.** Financials' census of busy markets finished at 5:21 am and Mentions' random pass at 5:41 am
(its census is still coming down). Three rounds: `r17_liquid_financials`, `r17_liquid_nine`,
`r18_random_mentions`.

**Financials, busy sample (7,016 markets, 2,170 events, 41,375 daily bars; 2,888 rules): every rule is thin.**
These are daily and weekly index and rate ranges that live about six bars each, so a price band holds only 24
to 85 events on each side of April 2026. No pass, no lead, no reliable loser. What can be read, with that
warning: paying the ask for NO lost in every band from 10 cents up, in both halves (YES at 20-35c: -10% before
April, -17% after; 35-50c: -8% / -52%), the same direction as the random sample in 3.21. So the answer to
3.21's question is "probably the category, not only thin quotes", but on 28 to 42 events a band it is not a
result.

The 5-cent rule on Financials' busy markets fails outright, and is the first category where it loses money:

| Entry | Bets (events) | Mean per bet | Losing events in / out | Tail test | Replay at 1%, in / out, per year |
|---|---|---|---|---|---|
| taker | 281 (109) | -1.30% | 9 of 82 / 0 of 30 | fails both (bounds 18.4% and 9.5% against break-even 5.0% and 3.2%) | -0.8% / +1.8% |
| resting | 172 (82) | -1.33% | 9 of 60 / 0 of 23 | fails both (bounds 24.7% and 12.2% against 8.6% and 5.6%) | -0.9% / +2.5% |

Seven of the nine losses closed in 2024; five are weekly 10-year Treasury yield ranges (KXTNOTEW), two the
Nasdaq-100. A price range on a traded index is not a longshot in the sense the rule relies on: the underlying
can move through it in a day. Median $386 to $630 traded in the seven days before entry.

**Nine categories pooled (busy sample, 26,635 markets, 8,312 events; 4,317 rules):** 18 pass, 122 leads, 284
lose. 16 of the 18 are NO against a YES at 10 cents or less (15 resting, 1 taker in the last tenth of a
market's life); one is a resting YES at 95c and above on "custom" questions. The picture of 3.19 and 3.21 is
unchanged with Financials in.

The 5-cent rule pooled over nine categories:

| Entry | Events in / out | Mean per bet | Tail test in / out | Replay at 1%, in / out, per year | Worst drawdown in / out |
|---|---|---|---|---|---|
| resting | 1,086 / 607 | +1.59% | passes / passes (bounds 5.4% and 5.9% against break-even 6.9% and 7.4%) | +2.7% / +17.6% | 3.9% / 3.5% |
| taker | 1,508 / 731 | +0.25% | fails / fails (bounds 4.2% and 4.9% against 3.5% and 4.6%) | -0.9% / -0.7% | 8.6% / 4.8% |

Financials pulled the mean down (from +1.77% to +1.59% resting) but did not change either verdict. Capacity is
as small as before: median $216 traded in the seven days before a resting entry, a quarter under $67, 22% of
entry days under 100 contracts. If the rule is ever traded on paper, leaving out index and yield ranges is the
obvious variant to record beside it; that is a choice made after seeing the losses, so it counts as one more
variant tried, not as evidence.

**Mentions, random sample (r18: 2,066 markets, 1,476 events, all from 2025 and 2026; 2,794 rules):** 1 pass,
9 leads, 49 reliably losing, and the three groups say one thing: YES is overpriced in "will X say Y" markets.
All 49 losers are buying YES (for example YES at 50c or less 30 to 60 days out: -38% before April, -45% after,
t by event -6). By price band, paying the ask for YES between 10 and 80 cents lost 16% to 54% in both halves,
and NO was positive in every band up to 80 cents in both halves (taker +1% to +14%, resting +4% to +35%).

| Rule (buy NO) | Entry | Events in / out | In / out per bet | t out (by event) | Tail test in / out | Replay at 0.5%, in / out, per year | Worst drawdown |
|---|---|---|---|---|---|---|---|
| spread 6-15c, YES at 20-80c | resting | 234 / 284 | +18.9% / +26.3% | 3.2 (3.5) | passes / passes | +25% / +98% | 5.0% / 5.6% |
| any spread, YES at 20-80c | resting | 291 / 380 | +21.6% / +13.6% | 2.2 (2.3) | passes / passes | +37% / +73% | 5.1% / 6.6% |
| any spread, YES at 20-80c | taker | 311 / 408 | +8.8% / +4.8% | 1.0 (1.3) | passes / fails | +15% / +22% | 6.6% / 8.9% |

Why this is a lead and not a result:

- **One pass in 2,794 rules is what chance gives.** What is not chance-like is the consistency (every band,
  both halves, 175 series, the largest 11% of the bets). The wide-spread rule that passed was not predicted
  beforehand; the plain "NO at 20-80c" rule is the honest version and it is a lead resting (t 2.2) and nothing
  as a taker (t 1.0).
- **It is a coin-flip bet, not a longshot bet.** 46% to 48% of events lose the whole stake; the edge is that a
  winner pays about 1.3 to 1.4 times the stake at a resting price. Returns swing: one series
  (KXSECPRESSMENTION) carries 20% to 37% of the profit, and KXTRUMPMENTION, the second largest, loses.
- **The capacity is tiny.** The median qualifying market traded $47 to $88 in the seven days before entry, a
  quarter under $15, and 25% to 35% of entry days traded under 100 contracts. The replay's percentages are on
  an account that could not be more than a few hundred dollars.
- **The resting figure rests on the fill model** (75% to 81% filled) on daily bars of markets that live a
  median of 2.4 days: many are decided inside one live broadcast, where a resting NO bid is filled exactly when
  the word has just been said. The model counts those fills, but a daily bar cannot show the order of events
  inside the day.
- Mentions is not one of the paper bot's categories, and nothing here changes its config.

The test that decides it is the busy sample (Mentions' census, downloading now): if NO at 20-80c still earns
there as a taker, there is something with capacity; if it lives only where $50 a week trades, it is a curiosity.

**Forward logs.** Observation log of the 5-cent rule: 12 qualifying markets seen, none settled; 5 resting bids
decided, all 5 filled. Variant paper accounts (12 accounts: the main one, 9 that follow Claude under other
rules, 2 controls): no market has settled, so no standings. Main $999.14 (one filled YES position marked 2
cents under its price), `claude_only_taker` $997.35 (the spread on 3 positions), every other account,
including both controls (`control_fade`, `control_coinflip`), $1,000.00 with 3 to 6 resting orders. The third
PC cycle (8 questions) started at 5:48 am and was still running when this was written.

### 3.23 Rounds r19 and r20: Mentions' busy markets do not confirm the lead; Entertainment (7:25 am CST, November 19)

**What was new.** Mentions' census of busy markets finished at about 6:40 am and Entertainment's random pass at
7:00 am (its census is coming down now). Two rounds: `r19_liquid_mentions`, `r20_random_entertainment`.

**Mentions, busy sample (5,685 markets, 1,153 events, but only 10,502 daily bars; 2,792 rules): every rule is
thin.** These markets live about two daily bars each after reaching 5,000 contracts, so a price band holds 5
to 50 events a side. No pass, no lead, no reliable loser. The question 3.22 left for this sample was whether
"NO where YES is at 20 to 80 cents" still earns where there is money to trade against:

| Entry | Bets (events) | Mean per bet | Losing events in / out | Tail test in / out | Replay at 0.5%, in / out, per year | Worst drawdown |
|---|---|---|---|---|---|---|
| taker | 138 (50) | -0.58% | 17 of 33 / 9 of 18 | fails / fails (bounds 66.7% and 70.9% against break-even 56.4% and 38.4%) | +0.6% / -1.7% | 4.0% / 2.5% |
| resting | 132 (48) | +5.81% | 17 of 33 / 8 of 16 | fails / fails (bounds 66.7% and 72.1% against 63.7% and 41.5%) | +1.9% / -0.2% | 4.0% / 2.4% |

- **It is not confirmed.** As a taker the rule is at zero (-0.6% per bet, 2025 -14.6%, 2026 +5.4%); resting it
  is positive on average but the account replay is flat to slightly negative after April 2026 and the tail
  test fails in both halves. Out of sample a winner made 0.83 to 0.87 of the stake and a loser cost 1.2 to 1.3
  (several bets per event), the reverse of the random sample's picture.
- **It is too small a sample to call the opposite either**: 50 events, 16 to 18 of them after April. The band
  table points the same way as 3.22 below 35 cents (NO taker +7.5% / +8.6% at 20-35c on 19 / 9 events) and
  the other way at 35-50c (+10.9% / -23.4% on 10 / 7 events). One event, KXDJTJOINTSESSION, holds 23 of the
  138 bets.
- **Capacity is the one thing that is clearly there**: median $16,745 traded in the seven days before entry (a
  tenth under $7,900), 14,700 contracts on the entry day, against $47 to $88 in the random sample.
- Reading the two samples together, by the test 3.22 set beforehand: the Mentions edge lives where about $50
  a week trades and is not visible where thousands do. It stays a curiosity. Nothing more is spent on it
  unless a forward log is wanted, which would be the user's choice.

**Entertainment, random sample (r20: 2,426 markets, 1,876 events, 50,442 daily bars, 2021 to 2026; 2,864
rules):** 0 pass, 0 leads, 9 reliably losing, all nine buying YES at low prices (for example a resting YES at
5-20c with a 6-15c spread: -74% before April, -91% after, t by event -9; YES at 50c or less 30 to 60 days
before the close: -61% to -76%, t by event -10). Cheap YES is overpriced here as elsewhere, but, as in every
other random sample, the other side does not collect it: paying the ask for NO against a YES under 20 cents
lost 0.3% to 5% in both halves, and a resting NO was -0.4% to -2.9% before April and +1.2% to +4.3% after. NO
against favourites (YES above 65c) lost 14% to 80%. Nothing to follow until the census is down: the busy
sample is where the 5-cent rule is judged.

**Forward logs.** Observation log of the 5-cent rule: 13 qualifying markets seen, none settled; 5 resting bids
decided, all 5 filled (the backtest's model fills 55% to 60%; five is too few to say it is wrong). The third
PC cycle (5:48 am, 8 questions) ended ok: 4 low confidence, 4 with enough edge stopped by the daily order
budget; 32 forecasts so far, none resolved. Variant paper accounts (12 accounts: the main one, 9 that follow
Claude under other rules, 2 controls): no market has settled, so no standings. Main $999.14;
`claude_only_taker` $995.46 and `blend30_taker` $997.20 (the spread on 5 and 2 positions); the seven other
Claude accounts $999.73 each (one filled NO position marked under its price); both controls
(`control_fade`, `control_coinflip`) $1,000.00 with 5 resting orders and nothing filled.

### 3.24 Round r21: Entertainment's busy markets, the first category where the wider NO rules hold up (8:15 am CST, November 19)

**What was new.** Entertainment's census of busy markets finished at 7:50 am (the download is now listing
Crypto). One round, `r21_liquid_entertainment`: 7,385 markets, 1,947 events, 105,883 daily bars, closes
September 2021 to September 2026, 2,781 markets out of sample; each market seen from the bar at which it had
traded 5,000 contracts. 2,890 rules: **18 pass, 68 leads, 113 reliably losing**, 1,849 thin.

**The picture by price band** (return per bet, before April 2026 / from April 2026):

| YES price | YES taker | NO taker | NO resting | Events in / out |
|---|---|---|---|---|
| 0-5c | -50.0% / -49.4% | +0.3% / +0.1% | +1.9% / +1.1% | 486 / 291 |
| 5-10c | -54.4% / -62.4% | +1.1% / +2.6% | +4.3% / +5.1% | 415 / 205 |
| 10-20c | -35.4% / -41.4% | +1.6% / +3.1% | +4.9% / +5.7% | 431 / 189 |
| 20-35c | -35.9% / -35.5% | +6.0% / +5.9% | +11.4% / +10.4% | 393 / 165 |
| 35-50c | -22.7% / -25.6% | +4.9% / +8.5% | +11.4% / +15.7% | 325 / 129 |
| 50-65c | -17.9% / -9.8% | +7.3% / -2.3% | +17.9% / +4.8% | 355 / 152 |
| 80-90c | -2.3% / -1.4% | -23.3% / -19.5% | -14.7% / -13.3% | 323 / 176 |
| 95-100c | +0.5% / +0.3% | -74.4% / -53.4% | -75.5% / -39.0% | 304 / 231 |

YES is overpriced in every band up to 80 cents, in both halves (the calibration curve: a YES quoted at 5-10c
resolved yes 4.6% / 3.4% of the time, at 20-35c 19% / 20%, at 35-50c 35% / 34%; per event the gap is 2 to 7
points, t 1.7 to 3.3). All 113 losing rules buy YES below 80c or NO above 80c. All 18 passing rules buy NO
against a YES between 5 and 35 cents, 17 of them with a resting order.

**The 5-cent rule is NOT what works here.** "NO at mid <= 5c, <= 30 days, spread <= 5c":

| Entry | Bets (events) | Mean per bet | Losing events in / out | Tail test in / out | Replay at 0.5%, in / out, per year |
|---|---|---|---|---|---|
| taker | 1,396 (651) | +0.12% | 11 of 406 / 11 of 246 | fails / fails (bounds 4.4% and 7.3% against break-even 3.2% and 4.2%) | +0.5% / -1.2% |
| resting | 1,073 (561) | +1.42% | 11 of 358 / 11 of 204 | passes / fails (bounds 5.0% and 8.8% against 5.7% and 6.8%) | +1.7% / +2.8% |

22 losing events in 651, all in 2025 and 2026 (Rotten Tomatoes scores, the Time cover, album sales, Netflix
ranks). Entertainment joins Politics, Elections and Financials as a category where the taker version does not
pay; do not add it to the rule's pooled categories as support.

**The wider rules, with the replay and the tail test** (the check that sank them in 3.14):

| Rule (buy NO) | Entry | Bets (events) | Mean per bet | Tail test in / out | Replay at 0.5% stake, in / out, per year | Worst drawdown in / out | At 2% stake, out |
|---|---|---|---|---|---|---|---|
| YES at 5-10c | resting | 1,044 (566) | +4.56% | passes / passes (11.1% and 10.9% against 15.6%) | +3.2% / +9.9% | 2.4% / 1.6% | +20.6% a year, drawdown 7.4% |
| YES at 5-10c | taker | 1,225 (618) | +1.63% | fails / passes | +0.9% / +5.6% | 3.8% / 1.7% | +4.1%, drawdown 7.8% |
| YES at 5-35c | resting | 1,937 (846) | +7.28% | passes / passes (27.8% and 26.3% against 37.5% and 34.7%) | +7.6% / +25.0% | 2.5% / 2.8% | +25.4%, drawdown 8.8% |
| YES at 5-35c | taker | 2,135 (884) | +3.30% | passes / passes (27.7% and 26.6% against 30.7% and 29.8%) | +2.8% / +12.1% | 3.7% / 3.3% | +4.1%, drawdown 11.1% |
| YES at 10-25c, down 3c+ in 7 days | resting | 716 (430) | +8.95% | passes / passes (23.4% and 20.2% against 29.7% and 29.3%) | +9.2% / +14.1% | 3.0% / 1.6% | +32.3%, drawdown 5.4% |
| YES at 10-25c, down 3c+ in 7 days | taker | 822 (470) | +5.25% | passes / passes (22.3% and 18.1% against 24.8% and 24.2%) | +2.8% / +10.8% | 4.6% / 1.5% | +21.5%, drawdown 5.1% |

- **This is the first category where a wide NO rule survives the account replay in both halves, and where a
  taker version passes the tail test in both halves** (5-35c and the 7-day-fall rule). In the pooled sample of
  3.14 the same rules had positive means and a losing replay. Here the profit is spread: 491 series, the
  largest (Rotten Tomatoes scores) 9% of the bets and 2% of the profit; every year from 2024 is positive.
- **Reasons not to call it usable yet.** (1) It is one category of eleven, found after ten others showed
  nothing of the kind: by rule 4 the search across categories is itself a multiple test, and the random
  Entertainment sample (r20) showed no NO edge at all. (2) Out of sample the event-weighted t of the passing
  rules is 2.2 to 3.3, mostly under the bar of 3; the taker 5-35c rule is not among the sweep's 18 passes.
  (3) The resting figures rest on the fill model (69% to 80% filled); the forward log has 5 fills decided so
  far, all in other categories. (4) Out of sample is five and a half months of closes, 116 to 280 events.
- **Capacity is small.** Dollars traded in the seven days before entry: median $2,140 for 5-35c (a quarter
  under $950, a tenth under $435), $1,100 for 5-10c; 2,600 to 3,800 contracts on the entry day, a tenth of
  entry days under about 100 contracts. Taking a tenth of a week's flow means $100 to $200 per market. With
  about 2 new bets a day in the out-of-sample replay and a median holding time of 6 to 10 days, that is a few thousand
  dollars at work, not more.
- What would test it properly is forward observation, as for the 5-cent rule: `scripts/shadow_longshot.py`
  records only YES at 5c or less. A second observation band (Entertainment, YES 5-35c, no orders) would be
  new code and a new standing log; it is left for the user to say whether they want it.

**Forward logs.** Fourth PC cycle running since 7:48 am (8 questions); the 5:48 am cycle ended ok. 34 forecasts,
none resolved. The main account holds 2 filled positions and 3 resting orders, $998.30. Variant paper accounts
(12 accounts: the main one, 9 that follow Claude under other rules, 2 controls): no market has settled, so no
standings; `claude_only_taker` $995.46 and `blend30_taker` $997.20 (the spread on 5 and 2 positions), the seven
other Claude accounts $999.73 each, both controls (`control_fade`, `control_coinflip`) $1,000.00 with 5 resting
orders and nothing filled. Observation log of the 5-cent rule: 13 markets seen, none settled; 5 resting bids
decided, all 5 filled.

### 3.25 Round r22: Crypto, random sample: too short-lived for daily bars (9:20 am CST, November 19)

**Data.** Crypto's random pass finished at 8:31 am CST (2,520 markets downloaded out of 3,018,367 listed). The
panel keeps 227 of them (219 events, 1,295 daily bars, closes 2024-10-31 to 2026-09-19, 175 out of sample).

- **Result: all 2,768 rules thin. 0 pass, 0 leads, 0 reliably losing.** Nothing can be said either way.
- **Why so few.** 96.6% of all listed Crypto markets live less than 24 hours, and the median lifetime among
  those downloaded so far is 15 minutes (the "price in the next 15 minutes" series). Such a market has one
  daily bar or none, so the engine, which enters on one day's bar and judges on later ones, has nothing to
  work with. Only the few hundred longer-dated questions (year-end price levels and the like) remain.
- **What this means for the census.** 138,349 Crypto markets have 5,000+ lifetime contracts; the download takes
  the 8,000 biggest, and those are mostly the same 15-minute markets (among 8,680 downloaded so far, 345 have
  two or more daily bars). Round r23 on the busy sample will be run when the census finishes, with the
  pre-stated tests (5-cent rule, NO where YES is at 5-35c), but expect it to be thin as well.
- **Not tested, and not testable with this data:** rules inside the 15-minute and hourly markets. That would
  need minute bars, a separate download and a separate engine; it is also where automated market makers are
  most active. Left on the backlog (family 16), not started.

**Forward logs.** Fourth PC cycle (7:48 am) ended ok; 40 forecasts, none resolved; next cycle about 9:50 am. Main
account: 2 filled positions, 3 resting orders, $998.30. Variant paper accounts (12 accounts: the main one, 9
that follow Claude under other rules, 2 controls): no market has settled, so no standings; `claude_only_taker`
$995.46 and `blend30_taker` $995.81 (the spread on 5 and 2 positions), the three wide accounts $997.06 to
$997.36, the four other Claude accounts $999.73, both controls (`control_fade`, `control_coinflip`) $1,000.00
with 5 resting orders and nothing filled. Observation log of the 5-cent rule: 13 markets seen, none settled;
5 resting bids decided, all 5 filled.

### 3.26 Rounds r23 and r24: Crypto's busy markets (thin, as expected), Social (too small), Climate and Weather random (10:20 am CST, November 19)

**Data.** Crypto's census finished at 9:18 am CST (7,000 markets downloaded). Social was listed and downloaded
in a minute: 68 markets, none with 5,000+ contracts. Climate and Weather's random pass finished at 9:38 am
(2,520 markets); its census is in progress.

**r23, Crypto, busy sample: 133 markets, 104 events, 2,447 daily bars (closes 2024-11-30 to 2026-09-19, 101 out
of sample).**

- **All 2,792 rules thin. 0 pass, 0 leads, 0 reliably losing.** As 3.25 expected: the census is mostly
  15-minute and hourly markets with no usable daily bars.
- **The two pre-stated tests, on what little there is** (year-end and "will Bitcoin reach X" questions):
  - 5-cent rule: 8 events, none losing, taker +2% to +3% a bet, resting +4% to +5%. Eight events cannot
    bound the loss rate (95% upper bound 31% against a break-even of 7% to 9%): **tail test not passed, no
    evidence either way.**
  - NO where YES is at 5-35c: 10 events, 3 losing (taker and resting alike; break-even 46% to 51%, upper
    bound 61%): **not passed.** The replay is about +1% a year at 0.5% to 1% stake, and negative in sample at
    2% stake (drawdown 7.8%). The Entertainment lead of 3.24 is neither confirmed nor contradicted here.
  - Capacity is real where the markets exist (median $7,200 traded in the 7 days before a 5-cent entry,
    $55,000 for the 5-35c band), but there are about ten events in two years.
- **Crypto is closed for the daily-bar engine.** Do not pool it. The minute-bar question stays on the backlog.

**Social: no round.** 66 markets in 36 events in the panel, one of them out of sample, no busy sample at all.

**r24, Climate and Weather, random sample: 1,305 markets, 1,080 events, 5,063 daily bars (closes 2021-08-13 to
2026-09-18, 647 out of sample). 2,794 rules: 0 pass, 2 leads, 6 reliably losing, 180 no, 2,606 thin.** Almost all
of it is the daily "highest temperature in a city" series: held a median of 1.1 days.

| YES price | YES taker in / out | NO taker in / out | YES resting in / out | NO resting in / out | Events in / out |
|---|---|---|---|---|---|
| 0-5c | −100.0% / −55.1% | +1.8% / +0.0% | −100.0% / −50.1% | +4.1% / +0.8% | 101 / 162 |
| 5-10c | −34.7% / −25.0% | −2.5% / −1.3% | +58.5% / +33.7% | −1.2% / −0.5% | 80 / 76 |
| 10-20c | −40.2% / −42.3% | +1.1% / +3.0% | −28.3% / −40.5% | +4.4% / +6.2% | 93 / 81 |
| 20-35c | −19.4% / −1.7% | −1.4% / −7.1% | −10.8% / +0.3% | +3.1% / −6.2% | 121 / 86 |
| 35-50c | −11.4% / −24.6% | −7.0% / +8.2% | −9.9% / −19.2% | −3.3% / +14.8% | 91 / 64 |

- **Reliably losing: buying cheap YES as a taker.** YES at 0-50c, 3 to 60 days before the close: −39% to −42%
  a bet in sample, −40% to −47% out (t −3.7 to −5.3, about 360 / 390 events); the favourite of a 5-10 market
  event: −44% / −40%. The same shape as Mentions and Entertainment.
- **NO does not collect it.** NO as a taker is between −7% and +8% with no pattern across the bands.
- **The two leads are one rule** (resting NO where YES is at 20c or less, spread 5c or less, within 14 or 30
  days): +0.3% a bet in sample (t 0.1), +4.0% out (t 2.3, by event 2.5), 142 / 190 events, fill 68%. Tail test:
  in sample 13 losing events of 142 (9.2% against a break-even of 9.4%, upper bound 14.2%): fails; out of
  sample 10 of 190 (upper bound 8.8% against 9.2%): passes; all together fails. Replay at 0.5% stake: +0.0% a
  year in sample, +7.7% a year out. Two leads among 2,794 rules, flat in sample: what chance gives. Capacity:
  a median of $39 traded in the 7 days before entry. **Not a result.**
- **The 5-cent rule fails here.** Taker: 270 bets in 258 events, +0.69% a bet, 3 losing events, all in 2026
  (out of sample 3 of 159 = 1.9% against a break-even of 1.9%; upper bound 4.8%). Resting: 159 bets, +2.16% a
  bet, the same 3 losses (out of sample 3 of 93 = 3.2% against 4.0%; upper bound 8.1%). In sample there is no
  loss but too few events to bound the rate. **Tail test not passed in either half, either entry.** Replay at
  0.5% stake: +0.2% / +0.0% a year (taker), +0.6% / +0.7% (resting). Capacity in this sample: a median of $8
  to $12 traded in the 7 days before entry. Do not pool Climate and Weather into the rule's categories unless
  the busy sample says otherwise.
- The busy sample (census in progress) is the one that matters here, as for every category: r25 when it lands.

**Forward logs.** Fifth PC cycle running since 9:51 am; 40 forecasts, none resolved. Main account unchanged: 2
filled positions, 3 resting orders, $998.30. Variant paper accounts (12 accounts: the main one, 9 that follow
Claude under other rules, 2 controls): no market has settled, so no standings; figures as in 3.25 (takers
$995.46 and $995.81, wide accounts $997.06 to $997.36, both controls $1,000.00 with nothing filled).
Observation log of the 5-cent rule: 13 markets seen, none settled; 5 resting bids decided, all 5 filled.

### 3.27 Round r25: Climate and Weather's busy markets, the last category (12:25 pm CST, November 19)

**Data.** The Climate and Weather census finished at 10:28 am: 7,319 markets in 3,239 events, but only 17,722
daily bars (about 2.4 a market: most are one-day temperature and rain questions), closes August 2021 to
September 2026, 2,818 markets out of sample. With this round the mechanical backtest has seen every category.
The download has gone on to extend the random samples beyond the first 2,500 markets per category (same fixed
shuffle, so the samples stay valid; they only get larger).

**Round r25** (`r25_liquid_climate`, 2,816 rules): 0 pass, 0 leads, 0 reliably losing; 2,812 thin, 4 "no". As
with Crypto, too few bars per market for the round's bar of 100 events a half. The price-band table has the
familiar shape (cheap YES loses heavily, NO against it earns a little), on 6 to 100 events a cell.

**The 5-cent rule** (NO at mid <= 5c, <= 30 days, spread <= 5c):
- Taker: 204 bets in 164 events, +1.57% a bet, one losing event (2025). In sample 1 loss in 98 events against
  a break-even of 2.7% (upper bound 4.8%); out of sample 0 in 66 against 2.2% (upper bound 4.4%). **Tail test
  not passed in either half**: the loss rate looks low, but there are too few events to bound it.
- Resting: 154 bets in 127 events, +3.44% a bet, the same one loss. Not passed in either half (bounds 6.0%
  against 5.1%, 5.8% against 4.3%); passed only on all 127 events together (3.7% against 4.8%), which is not
  the test.
- Replay at 0.5% stake: +0.2% / +1.4% a year (taker), +0.4% / +2.2% (resting): almost no capital is ever at
  work. Capacity: a median of about $900 traded in the 7 days before entry.
- Read with the random sample (3.26, where it failed with 3 losses in 2026): **not confirmed in Climate and
  Weather.** It stays out of the rule's categories.

**The Entertainment lead as a pre-stated test** (NO where YES is at 5 to 35c; stated in STATE.md before r25):
- Taker: 236 bets in 186 events, +4.35% a bet. Tail test fails both halves (in sample 12.6% losing events
  against a break-even of 17.7%, upper bound 18.7%; out of sample 10.4% against 13.3%, upper bound 18.7%).
  Replay at 0.5% stake +0.9% / +2.1% a year, drawdown 2.0% / 1.2%.
- Resting: 211 bets in 173 events, +9.19% a bet. Tail test passes in sample (13.8% against 22.7%, upper
  bound 20.4%) and narrowly fails out of sample (6 losing of 64 = 9.4% against 16.9%, upper bound 17.7%).
  Replay at 0.5% stake +1.5% / +5.6% a year, drawdown 1.9% / 0.6%.
- Losses cluster: New York monthly snow (5 losing bets in 4 events) and 2024 as a losing year. Capacity is
  better than for the 5-cent rule: a median of about $4,300 traded in the 7 days before entry.
- **Verdict: same sign as Entertainment, not a confirmation.** 64 to 67 events out of sample cannot carry the
  test, and the resting figure rests on the fill model. The 3.24 lead stays a lead in one category.

**Calibration** (busy sample, per event): YES under 35c resolves yes less often than its price in every band
and both halves (gaps of 2 to 12 points), but only the bands under 10c reach t of 2 (the out-of-sample t of
-24 at 0-5c is an artefact of zero yes outcomes in 72 events). Above 35c nothing is stable.

**Where the backtest stands, all categories seen.** One rule passes its tests pooled over the nine categories
(the 5-cent rule as a RESTING order, 3.22; its taker version fails); it fails or is unconfirmed in
Entertainment, Mentions, Financials alone, and Climate and Weather. The wider NO rules are a lead in
Entertainment with a same-signed, unconfirmed echo here. No new rounds are left to run; what remains is exits
before settlement, a combined-portfolio replay, and the forward logs.

**Forward logs.** Sixth PC cycle running since 11:53 am (five before it all ended ok); 49 forecasts on 49
markets, none resolved. Main account $998.02, 2 positions, 3 resting orders. Variant paper accounts (12: the
main one, 9 that follow Claude under other rules, 2 controls): nothing has settled, so there are no standings;
equity $995.46 to $999.73 for the accounts that follow Claude, both controls $1,000.00 with nothing filled.
Observation log of the 5-cent rule: 13 markets seen, none settled; 6 resting bids decided, all 6 filled
(the backtest's model assumes 55% to 60%).

### 3.28 Selling before settlement; the 5-cent rule on a larger census; one account for the survivors (4:20 am CST, November 20)

**What was asked.** The user: implement the open coding items and be thorough, "especially curious to see how
selling before settlement can impact things". Built and tested (214 tests): `research/exits.py` (follows each
historical bet bar by bar after entry and sells on a take-profit, stop-loss or time rule, at prices the market
offered LATER: a taker exit at the next bar's opening bid less the fee, a resting exit only if the market traded
through it), `research/exit_study.py` (a grid of 25 exit policies, fixed before any exit result was seen),
`research/combined.py` (several rules in one account), `research/exit_summary.py`, price-only exits for the paper
accounts (`src/trader.py`, six new exit accounts in `variants.yaml`), and the replay of the wide accounts' own
records (`src/replay.py`, `scripts/replay_wide.py`). Held to settlement, the exit engine reproduces
`analyze_rule.py` to the cent (checked on the live data and in `tests/test_exits.py`).

**1. Exits, mechanical rules (5 years of Kalshi history).** Each rule × 25 policies, in sample (closing before
2026-04-01) and out of sample; the policy is chosen in sample by its account replay and judged out of sample.
Out-of-sample return per bet, holding against the best policy of each family (count = policies of that family
that beat holding out of sample):

| Sample | Rule | Bets out | Hold, per bet | Take-profit (12) | Stop-loss (6) | Time exit (3) | Take + stop (3) |
|---|---|---|---|---|---|---|---|
| nine categories, busy | 5-cent rule, resting | 1,862 | +0.72% | 0 beat hold | 0 | 0 | 0 |
| nine categories, busy | 5-cent rule, taker | 3,048 | +0.02% | 0 | 0 | 0 | 0 |
| nine categories, busy | NO vs YES 5-35c, resting | 5,420 | -2.32% | 0 | 0 | 0 | 0 |
| twelve categories, busy | 5-cent rule, resting | 2,377 | +0.79% | 0 | 0 | 0 | 0 |
| Entertainment, busy | NO vs YES 5-35c, resting | 643 | +7.16% | 0 | 0 | 0 | 0 |
| Entertainment, busy | 5-cent rule, resting | 403 | +0.78% | 0 | 5 of 6 | 0 | 2 of 3 |
| Climate and Weather, busy | NO vs YES 5-35c, resting | 71 | +8.17% | 0 | 0 | 0 | 0 |
| Mentions, busy | both rules | 44-84 | -0.4% to +3.3% | 0 | 0 to 2 | 0 | 0 |
| nine categories, random | both rules | 2,425-10,316 | -0.1% to -4.8% | 0 | 0 | 0 | 0 |
| Entertainment, random | both rules | 533-1,377 | -1.9% to +0.1% | 0 | 0 | 0 | 0 |

Out of 32 rule-and-sample cases (eight samples, four rules), **take-profits never beat holding out of sample (0 of
384 tries), time exits never did (0 of 96), and stop-losses did in four cases, all small**: the 5-cent rule in
Entertainment (resting and taker, 403 and 549 bets, where holding was already weak: +0.78% and -0.13% a bet)
and the wide NO rule in Mentions (44 and 52 bets). What the grid shows, read across all of them:
- **Stops are the costliest idea.** They sell a longshot NO after the YES has jumped, which is exactly when it
  most often comes back down: the 5-cent rule in nine categories goes from +0.72% a bet to -1.4% (stop at -10
  points) and -1.8% (stop at -5); every stop raises the number of LOSING events (55 to 105-183 out of sample),
  because a stopped-out bet is a certain small loss where holding was mostly a win. The rare total loss is what
  a stop should prevent; on daily bars it usually cannot (the jump happens within a day; the sale is at the next
  open), and the many false alarms cost more than the few saves.
- **Taking profit at 97-99 cents gives away the last cents that are the whole edge** of a bet bought at 95-96
  cents: the 5-cent rule earns about +1 cent per contract, and a taker exit pays a spread and a fee to save the
  last 1-2. Resting the sale at the ask is cheaper and hurts less (take at 0.99 resting: +0.69% against +0.72%).
- **Selling days before the scheduled end throws away the decay** the rule is paid for: 1, 3 or 7 days early
  costs 1 to 2.5 points a bet.
- **What an exit does buy is capital time**: money comes back earlier and is staked again. On the account
  replay this sometimes outweighs the lower return per bet (Entertainment's NO rule: take at 98c resting, +32%
  a year out of sample against +27% holding, at 1% a bet), but never reliably, and the per-bet return falls in
  every such case.
- Caveat for all of it: daily bars. An exit can only happen at the next day's open, which is fair to a bot that
  checks once a day (the paper bot checks every 2 hours) but pessimistic for stops in fast markets. Hourly bars
  for the last days are still not downloaded.

**2. The same question for the whole account (combined replay, 0.5% a bet).** Four legs in one account: the
5-cent rule resting on the nine categories; NO against YES at 5-35c resting in Entertainment and in Climate and
Weather; the 5-cent rule resting in Entertainment. Out of sample (0.93 years):

| Exit rule | Return a year | Worst drawdown | Sharpe | At work |
|---|---|---|---|---|
| hold to settlement | +15.3% | 5.4% | 2.73 | 25% |
| take at 98c, resting | +14.6% | 5.4% | 2.47 | 24% |
| stop at -10 points | -2.1% | 4.7% | -0.31 | 24% |
| take 99c resting + stop -10 | -2.1% | 4.8% | -0.33 | 23% |

In sample (4.7 years): +7.6%, +8.1%, +1.1%, +1.1% a year, drawdowns 8.6% to 18.6%. **Holding to settlement is
the best or tied-best exit for the combined account too.** Combining helps (the 5-cent rule alone: +5.6% a year
out of sample at 0.5%, drawdown 3.7%), but most of the combined return is the Entertainment leg, which was
FOUND on Entertainment's data (3.24): its in-sample half is not independent evidence, and only its out-of-sample
half counts. At 1% and 2% a bet the combined account does worse out of sample (+12.2%, +2.6% a year): the event
cap binds and the 5-cent leg's losses grow faster than its gains.

**3. The 5-cent rule on the larger census: it now fails at the default level, and passes on busy markets.**
Since 3.22 the download has gone further down the volume ladder: the nine-category busy sample grew from 26,635
to 39,858 markets. At the new default level (the lowest level complete in each category), the resting rule's
mean fell to +0.91% a bet and it **no longer passes the tail test out of sample** (55 losing events of 828, 95%
bound 8.25% against a break-even of 8.14%); replay at 1%: +2.4% a year in sample, -0.5% out of sample, worst
drawdown 12.3%. By the level of trading a market had reached (the 45,000-contract level is the one used since
3.7; the others are the neighbours):

| Contracts traded so far | Bets (events) | Per bet | Losing events in / out | Tail test in / out | Replay at 1%, in / out a year | Worst drawdown |
|---|---|---|---|---|---|---|
| 5,000 (Economics not yet complete there) | 1,981 (1,088) | +1.29% | 28 of 699 / 23 of 415 | passes / fails | +1.5% / +2.6% | 4.5% / 5.9% |
| 20,000 | 1,637 (945) | +2.40% | 16 of 652 / 8 of 315 | passes / passes | +3.3% / +19.9% | 3.3% / 2.3% |
| 45,000 | 1,188 (716) | +2.07% | 16 of 505 / 4 of 227 | passes / passes | +1.6% / +18.1% | 3.0% / 1.5% |
| default (lowest complete) | 4,514 (2,238) | +0.91% | 84 of 1,442 / 55 of 828 | passes / fails | +2.4% / -0.5% | 12.3% / 8.1% |

So the rule lives in markets that are already busy, and the quiet markets the download added are where its rare
total losses come from (KXAPRPOTUS and KX538APPROVE, approval-rating ranges, are the two biggest series and both
lose money). Choosing a level after seeing this is one more variant tried; the 45,000 level was fixed in 3.7,
before any of this, and it passes. Capacity stays small: median $72 traded in the week before a resting entry at
the default level.

**4. The Entertainment lead, both samples.** Busy markets (7,385 markets, 846 events with a bet): NO against YES
at 5-35c resting, +7.28% a bet, **tail test passes in both halves** (144 of 584 and 58 of 267 losing events,
bounds 27.8% and 26.3% against break-evens of 37.5% and 34.7%), replay at 0.5%: +7.6% a year in sample, +25.0%
out of sample, drawdowns 2.5% and 2.8%; capacity a median $2,140 traded in the week before entry, the best of any
rule so far. Random sample (13,584 markets): the same rule LOSES (-0.60% a bet, tail test fails both halves,
replay -1.6% and -7.6% a year). Like the 5-cent rule, it is a busy-market effect. With the random sample against
it, and found on this data, it stays a lead: the forward observation log is the place to test it.

**5. Forward.** Six exit accounts started at 4:04 am (`blend30_hold`, `claude_only_hold`, `claude_only_take10`,
`claude_only_stop15`, `claude_only_take_stop`, `claude_only_last3d`): the same Claude forecasts, each with one
change to when it sells, against a pair that differs in nothing else; 18 accounts in all. The replay of the wide
accounts works (tested on a ledger with known answers) and has nothing to say yet: 0 of their markets have
settled. Main account $1,001.67, 88 forecasts, none resolved.

**What this changes, and what it does not.** Nothing reaches the paper bot. The paper bot keeps its rule (sell
only when a fresh forecast says the bid is worth more than holding; no price stops). For the mechanical rules,
the history says: hold to settlement, rest the entry, and trade only markets that are already busy. Open for the
user: a second paper account for the 5-cent rule restricted to markets with 45,000+ contracts traded, and a
forward observation band (no orders) for NO against YES at 5-35c in busy Entertainment markets.


### 3.29 The backtest's rules as paper accounts; Claude as a filter; the Entertainment band at the busiest level (5:40 am CST, November 21)

**What was new.** The user said yes to both open questions and asked for "anything else possible for testing",
then: "Keep testing and trying things indefinitely". So:

- **Ten mechanical paper accounts** (`rules.yaml`, `src/rules.py`, `scripts/run_rules.py`), run by the paper loop
  after every cycle, each with $1,000 and its own ledger: the 5-cent rule on busy markets (45,000+ contracts) and
  the Entertainment band (NO vs YES 5-35c, 5,000+ contracts), the four-leg combined account at 0.5% a bet, taker
  twins of the first two, the Entertainment 7-day-fall rule, the Climate band, two quiet-market CONTROLS (the same
  rules where the history says they lose), and `rule_5c_busy_claude`: the 5-cent rule with Claude as a filter
  (the paper bot's own forecaster, no price shown; a veto when Claude gives NO less than the price or calls the
  rules unclear; at most 2 questions a cycle; vetoed markets' outcomes are recorded too). Entries rest at the best
  NO bid for 72 hours (the backtest's resting entry) and are held to settlement (report 3.28). The paper broker
  fills a resting order only when the market trades through it, which is harsher than the backtest's fill model.
- **Five stricter Claude accounts** in `variants.yaml` (5 and 8 points of edge, high confidence only, the side
  priced 50c+ only, NO only): 23 Claude accounts in all.
- **A second observation log**: `scripts/shadow_longshot.py --band ent` records the Entertainment band's books and
  whether a resting NO bid would really have filled (data/shadow_ent.db; 17 markets on the first pass).
- First run of the rule accounts, 5:01 am: 152 paper orders across nine accounts (7 in the 5-cent busy account,
  24 in the Entertainment band, 26 in the combined account, 23 in each control). Nothing has filled or settled.

**Ideas queue, item 1: the Entertainment band at the busiest level.** Report 3.24 found the band on markets seen
from 5,000 contracts. Is it still there where markets are busiest? NO where YES is at 5-35c, resting:

| Contracts traded so far | Bets (events) | Per bet | Losing events in / out | Tail test in / out | Replay at 1%, in / out a year | Worst drawdown in / out |
|---|---|---|---|---|---|---|
| 5,000 | 1,937 (846) | +7.28% | 144 of 584 / 58 of 267 | passes / passes | +10.9% / +31.4% | 4.0% / 6.0% |
| 20,000 | 1,526 (691) | +7.39% | 106 of 474 / 47 of 220 | passes / passes | +9.1% / +33.0% | 6.5% / 6.6% |
| 45,000 | 815 (402) | +7.14% | 68 of 282 / 19 of 121 | passes / passes (bound 22.2% against 35.9%) | +9.9% / +25.5% | 8.1% / 2.3% |

At 0.5% a bet the 45,000 level's out-of-sample replay is +14.3% a year with a worst drawdown of 1.2%. Capacity
grows with the level: a median $5,663 traded in the week before entry at 45,000 (against $2,140 at 5,000). **The
band holds at every level**, unlike the 5-cent rule, whose quiet markets carried its losses. Three levels are
three variants of one rule, all fixed before this look (5,000 is the census level, 20,000 and 45,000 the levels of
report 3.28). It is still one category of eleven, found on its own data: the forward accounts are the test.

**What this changes.** Nothing reaches the paper bot. A check-in with nothing new now takes the next item of the
ideas queue in STATE.md (13 items: taker and days-window splits, stand-alone questions, the band per category,
calibration at 45,000, risk-averse sizing, exits at the busy level, momentum, hourly bars, event sums, and the
forward comparisons) instead of stopping.

### 3.30 The Entertainment band as a taker at the busy levels (6:25 am CST, November 21)

**Ideas queue, item 2.** The band of 3.29 buying NO at the ask (taker, fee in) instead of resting at the bid.
`research/analyze_rule.py --sample liquid --categories Entertainment --rule "NO where YES is at 5-35c" --side no
--entry tk`, at two census levels:

| Contracts traded so far | Bets (events) | Per bet | Losing events in / out | Tail test in / out | Replay at 1%, in / out a year | Worst drawdown in / out |
|---|---|---|---|---|---|---|
| 20,000 | 1,675 (726) | +3.47% | 113 of 497 / 48 of 232 | passes (bound 26.1% against 29.5%) / passes (25.6% against 27.3%) | +2.9% / +13.7% | 7.6% / 7.4% |
| 45,000 | 883 (413) | +3.45% | 71 of 290 / 20 of 124 | **fails** (bound 29.0% against 28.5%) / passes (22.6% against 30.6%) | +2.0% / +16.1% | 10.0% / 4.0% |

**Result: the taker version is about half the resting version** (+3.5% a bet against +7.1-7.4%), as the spread
and fee would predict, and at the busiest level it fails the tail test in sample by half a point. At 20,000 it
passes both halves, but its in-sample replay is thin (+2.9% a year, worst drawdown 7.6%); 2025 was flat (+2.2% a
bet). Capacity at 45,000: median $5,664 traded in the week before entry. The largest series, Rotten Tomatoes
(KXRT, 8-9% of bets), loses slightly in both; dropping it would be a filter chosen after the look and is not
done. Two variants tried here (two levels, both fixed beforehand). **Verdict: not a new account.** The resting
band stays the stronger form; the paper account `rule_ent_band_taker` (5,000+) already tests the taker side
forward, and the paper broker's harsher resting fills are what decide between them.

### 3.31 Where the 5-cent rule's money comes from: price and days to close at 45,000 (6:45 am CST, November 21)

Ideas queue item 3. The busy sample at 45,000 contracts, the nine categories, family 25's pre-defined slices
(`analyze_rule.py --sample liquid --min-cumvol 45000 --rule "NO at mid <p>, <d> to scheduled end, <early>"`):
price 0-3c or 3-6c, 0-7 or 7-30 days, can close early or fixed date, resting and taker. 16 variants. These
slices have no spread filter, so they are neighbours of the 5-cent rule, not pieces of it.

| Slice (can close early) | Entry | Bets (events) | Per bet | Losing events in / out | Tail test in / out | Replay 1%, in / out a year | Worst DD in / out |
|---|---|---|---|---|---|---|---|
| 0-3c, 0-7d | resting | 501 (341) | +0.71% | 8/233 / 1/111 | fails / fails | +0.2% / +5.5% | 2.1% / 1.0% |
| 0-3c, 0-7d | taker | 774 (499) | +0.04% | 8/352 / 1/150 | fails / fails | -0.6% / +3.0% | 2.8% / 1.0% |
| 0-3c, 7-30d | resting | 656 (438) | +1.79% | 5/326 / 1/124 | passes (3.20 vs 3.83%) / passes (3.77 vs 3.94%) | +1.0% / +7.3% | 2.0% / 1.0% |
| 0-3c, 7-30d | taker | 880 (564) | +0.55% | 6/434 / 1/148 | fails / fails | +0.1% / +3.9% | 3.3% / 1.0% |
| 3-6c, 0-7d | resting | 330 (248) | +3.32% | 6/167 / 1/83 | passes (6.97 vs 7.68%) / passes (5.59 vs 6.19%) | +1.7% / +9.6% | 1.9% / 1.0% |
| 3-6c, 0-7d | taker | 438 (312) | +1.55% | 6/220 / 1/94 | fails / fails | +1.4% / +7.3% | 1.7% / 1.0% |
| 3-6c, 7-30d | resting | 526 (369) | +3.21% | 10/282 / 2/91 | passes (5.94 vs 7.34%) / passes (6.76 vs 8.41%) | +1.7% / +11.6% | 2.6% / 1.0% |
| 3-6c, 7-30d | taker | 660 (451) | +1.25% | 12/348 / 2/110 | fails / fails | -0.0% / +8.0% | 3.1% / 1.0% |

Fixed-date markets are almost absent from the busy sample (3 to 16 events per slice, no losers, every tail test
"not below break-even" for lack of events): no conclusion there.

**Result: the money is in the 3-6c band, resting, at any horizon up to 30 days (+3.2-3.3% a bet, passes both
halves); under 3c it is thin (+0.7% under a week, fails; +1.8% at 7-30 days, passes by a hair).** No taker slice
passes: a taker pays about 1.3c more, which is most of a 0-3c bet's margin. Capacity: median $2,255 traded in
the week before entry for 3-6c under a week, $1,345 for 3-6c at 7-30 days, $378-783 under 3c. The replays stay
small (+1.7% a year in sample at 1% stakes; the account is mostly idle), so this is a sharpening, not a new
strategy. 16 variants tried; nothing here is above t 3 on its own. **Verdict: no new account.** A pre-stated
follow-up goes to the queue: the 5-cent rule without its 0-3c, 0-7 day corner (NO at 3-5c, spread <= 5c,
<= 30 days), to be judged on both halves with the same tests.


### 3.32 The 5-cent rule on stand-alone questions at 45,000 (9:15 am CST, November 21)

Ideas queue item 4, the question 3.19 and 3.20 left open: family 28's "single-market event: NO where YES is 5c
or less, spread <= 5c" on the busy sample at 45,000 contracts, nine categories
(`analyze_rule.py --sample liquid --min-cumvol 45000`), resting and taker. 2 variants.

| Entry | Bets (events) | Per bet | Losing events in / out | Tail test in / out | Replay 1%, in / out a year | Worst DD in / out |
|---|---|---|---|---|---|---|
| resting | 330 (330) | +3.72% | 3/303 / 0/27 | passes (2.54 vs 4.53%) / not below break-even (10.5 vs 3.77%) | +1.7% / +1.3% | 1.0% / 0.0% |
| taker | 366 (366) | +1.86% | 3/331 / 0/35 | passes (2.33 vs 2.67%) / not below break-even (8.2 vs 2.23%) | +0.9% / +0.9% | 1.0% / 0.0% |

**Result: strong in sample, too thin out of sample to judge.** Both entries pass the tail test before April 2026
(the taker only by a hair) and have lost nothing since, but on 27 and 35 events an exact bound cannot get under
a break-even loss rate of 2-4%: 100+ events are needed. No series has more than 4% of the bets. Capacity is
small: median $492 (resting) / $680 (taker) traded in the week before entry, a fifth of entry days under 100
contracts. The replay barely uses the account (2-7% at work), so a year earns about 1-2% at 1% stakes. Same
reading as 3.20 at the busier level: well supported, consistent, not proven, and tiny. **Verdict: no new
account.** The shadow log already records event size; stand-alone questions are counted there as they come.

### 3.33 The wide band category by category at 45,000 (9:45 am CST, November 21)

Ideas queue item 5. Pooled over the nine categories at the default census level the wide band (NO where YES is at
5-35c, resting) lost (-2.32% a bet, report 3.28); Entertainment alone carries it (3.29). Does another category?
`analyze_rule.py --sample liquid --min-cumvol 45000 --categories <Cat> --rule "NO where YES is at 5-35c" --side no
--entry mk`, each category alone, then the nine pooled at 45,000 and Politics at 5,000 and 20,000 as checks.
12 variants in all, the nine single-category runs fixed beforehand.

| Sample | Bets (events) | Per bet | Losing events in / out | Tail test in / out | Replay 1%, in / out a year | Worst DD in / out |
|---|---|---|---|---|---|---|
| Economics | 500 (263) | +7.54% | 41/203 / 15/61 | passes / **fails** (35.3 vs 34.6%) | +5.7% / +9.8% | 7.0% / 4.4% |
| Politics | 759 (366) | +4.98% | 56/283 / 23/98 | passes (24.1 vs 26.1%) / passes by a hair (31.6 vs 32.0%) | +2.3% / +14.2% | 7.5% / 4.8% |
| Companies | 24 (10) | +14.9% | 2/8 / 0/2 | too few | -0.1% / +2.2% | 1.6% / 0.0% |
| Science and Technology | 151 (91) | +5.72% | 10/58 / 6/34 | fails / fails | +3.4% / +5.5% | 3.1% / 1.3% |
| Elections | 667 (302) | +0.99% | 45/181 / 34/124 | fails / fails | -3.3% / +7.6% | 9.6% / 3.7% |
| Health | 18 (16) | +14.9% | 2/16 / none | too few | +0.6% / - | 1.0% / - |
| World | 5 (5) | -11.3% | 1/5 / none | too few | -0.1% / - | 1.0% / - |
| Commodities | 79 (33) | +9.96% | 1/4 / 6/29 | too few / passes | - / +10.3% | 1.0% / 1.0% |
| Financials | 152 (59) | -3.76% | 10/35 / 7/24 | fails / fails | -0.5% / -9.8% | 5.9% / 6.9% |
| nine pooled, 45,000 | 2,355 (1,145) | +4.18% | 168/793 / 91/372 | passes (23.7 vs 28.0%) / passes (28.4 vs 31.0%) | +1.0% / +15.2% | 11.2% / 6.2% |
| Politics, 20,000 | 1,202 (584) | +3.11% | 92/427 / 51/179 | passes / **fails** (34.6 vs 31.2%) | +1.7% / -2.3% | 11.9% / 7.3% |
| Politics, 5,000 | 5,972 (1,960) | -0.23% | 508/1369 / 219/637 | fails / fails | -2.6% / -5.4% | 24.7% / 12.4% |

**Result: no second Entertainment.** Only Politics passes both halves on its own, and only at 45,000 and by 0.4
points out of sample; at 20,000 it fails out of sample and at 5,000 it loses, so its pass is one level of three and
not a stable effect. Economics is strong in sample and fails out of sample by a point. The nine pooled at 45,000
do pass both tail tests (+4.2% a bet), which is the reverse of the 5,000-level result: the band's losses sit in
quieter markets, as with the 5-cent rule. But the pooled money is almost all 2026 (by year of close: 2024 +0.1%,
2025 +1.3%, 2026 +6.8% a bet), and the in-sample replay at 1% earns +1.0% a year with an 11.2% worst drawdown:
not risk-averse on its in-sample record. Capacity at 45,000: median $4,799 traded in the week before entry (nine
pooled), $5,043 Politics. With 12 variants and nothing above the tail test by a clear margin out of sample,
**verdict: no new account.** Follow-up to the queue (item 16): is the pooled band's 2026 jump a change in the
market or a horizon effect (days to close by year)?

### 3.34 Calibration curve at 45,000 contracts, every category (12:25 pm CST, November 21)

Ideas queue item 6. `research/calibration_curve.py --sample liquid --min-cumvol 45000`, one category at a time
(Economics, Politics, Companies, Science and Technology, Elections, Health, World, Commodities, Financials,
Entertainment, Mentions, Climate and Weather, Crypto; 10 price bands each, about 130 band-halves). Question:
is YES overpriced (or underpriced) in some band in BOTH halves, per event, beyond what is already known?

- Bands with the same sign in both halves and the per-event t at least 2 in both, with 30+ events in each half:
  only three. Politics 0-5c (-1.8c in / -3.3c out; the 5-cent rule's ground, report 3.33), Entertainment 10-20c
  (-3.8c / -8.1c; inside the known Entertainment band, 3.29), and Climate and Weather 0-5c (-2.7c / -2.7c; 76 and
  45 events). Every other "both halves" hit has under 30 events a half (World, Commodities, Financials, Mentions,
  Climate 90-100c) and its t comes from no YES at all in a handful of events: not evidence.
- The longshot side (YES 0-20c too dear) shows the same sign out of sample in Politics, Science and Technology,
  Elections, Entertainment, Mentions and Economics, but out-of-sample t under 2 everywhere except the three above.
- The one new candidate, tested as a rule: the 5-cent rule ("NO at mid <= 5c, <= 30d, spread <= 5c") on Climate
  and Weather alone at 45,000. Resting: 89 events, 0 losing, +4.8% a bet, but the tail test fails in both halves
  (in 57 events, bound 5.12% vs break-even 4.75%; out 32 events, bound 8.94% vs 4.26%); replay at 1% +0.7%/y in
  sample, +2.8%/y out, no drawdown; median $1,153 traded in the week before entry. Taker: 111 events, 0 losing,
  +2.5% a bet, fails both halves. No losses, but too few events to prove the loss rate is below break-even.
  (At the random sample the 5-cent rule FAILED in Climate and Weather, r24.) 2 variants tried (mk, tk).
- Verdict: no new band. Climate and Weather's 5-cent rule at 45,000 is a lead that needs more events; not an
  account. Queue item 17 added: re-test it when the download has added Climate and Weather markets.

### 3.35 Smaller stakes for the combined account (12:35 pm CST, November 21)

Ideas queue item 7. `research/combined.py --stakes 0.0025,0.005,0.0075,0.01`, hold to settlement, default census
level, on the data downloaded as of today (larger than in 3.28). Out of sample (0.93 years), the four legs in one account:

| Stake a bet | Return a year | Worst drawdown | Sharpe | At work |
|---|---|---|---|---|
| 0.25% | +12.1% | 4.0% | 2.67 | 21% |
| 0.50% | +8.8% | 6.7% | 1.59 | 26% |
| 0.75% | +4.1% | 10.3% | 0.51 | 28% |
| 1.00% | +2.3% | 10.2% | 0.27 | 29% |

In sample (4.7 years): +5.2%, +7.2%, +8.8%, +9.9% a year, drawdowns 4.5%, 8.9%, 11.7%, 12.2%.
- **Yes, a smaller stake buys a much smaller drawdown, and out of sample it also earns MORE.** The return falls as
  the stake rises because the 5-cent leg's out-of-sample result turns negative with size (alone: +2.4%/y at 0.25%,
  -1.2% at 0.5%, -7.7% at 0.75%, -11.9% at 1%, drawdown 3.1% to 10.6%): its per-bet edge out of sample is now only
  +0.29% (was larger in 3.28), so the occasional full loss of a 5-cent NO costs more than the decay earns once the
  event cap and cash limit bind. The Entertainment leg alone scales cleanly (+12.7% / +24.5% / +34.1% / +32.6% a
  year, drawdown 1.4% to 5.9%).
- **The 0.5% figure moved since 3.28** (+15.3%/y, DD 5.4% then; +8.8%, DD 6.7% now) with no code change: the
  download added markets, and the new ones are worse for the 5-cent leg. The combined result is not stable yet.
- In sample the order is the reverse (bigger stake, more return, bigger drawdown), so the out-of-sample ranking is
  one half-sample's evidence. 4 stakes tried. The paper rule accounts already stake small; no account change.
- Suggests: the Entertainment band without the 5-cent leg carries the account; queue item 18 added (combined
  account without the 5-cent nine-category leg, and the 5-cent leg at 45,000 instead of the default level).

### 3.36 Ideas queue 8: selling the Entertainment band early, at the 45,000-contract level (3:15 pm CST, November 21)

`research/exit_study.py --categories Entertainment --sample liquid --min-cumvol 45000 --rules "NO where YES is at
5-35c|no|mk"` (the 25-policy grid of 3.28, unchanged). Data: 3,178 markets, 942 events, closes 2022-02-07 to
2026-09-18; 573 bets in sample, 242 out of sample. Output: `research/results/exit_ent_liquid_45000.csv`.

| Policy | Per bet in / out | Replay at 1%, a year, in / out | Worst drawdown in / out | Losing events out |
|---|---|---|---|---|
| hold to settlement | +5.94% / +9.96% | +9.9% / +25.5% | 8.1% / 2.3% | 19 |
| take at 0.98, resting (the 3.28 lead) | +6.00% / +9.73% | +10.1% / +24.9% | 8.4% / 2.4% | 19 |
| take at 0.97, taker (chosen in sample) | +5.56% / +10.01% | +11.3% / +27.8% | 6.8% / 2.3% | 17 |
| stop at -10 points | +3.15% / +6.44% | +4.6% / +14.1% | 9.8% / 3.1% | 31 |
| sell 3 days before the end | +2.71% / +9.96% | +4.7% / +26.5% | 8.6% / 1.5% | 23 |

- **At the busy level the 98-cent resting exit does not help**: it earns slightly less than holding in both the
  per-bet and the account figures out of sample (3.28's gain at the default level came from capital time, and at
  45,000 the band's bets are already short). The policy picked in sample (take at 0.97 as a taker) beats holding
  out of sample by 2.4 points a year with the same drawdown, the gap is far inside the noise of 242 bets, and it
  was the best of 25 policies tried. Holding stays the rule. Stops and early sales cost, as everywhere in 3.28.
- Holding passes the tail test in both halves here (as in 3.29). No new account; nothing for the paper config.

### 3.37 Ideas queue 9: the momentum lead pooled over the nine categories, busy sample (3:45 pm CST, November 21)

`research/analyze_rule.py --sample liquid --categories <the nine> --rule "mid 3-10c, down 3c+ in Nd" --side no`,
N = 1, 3, 7 days, resting and taker (6 variants), default census level, on the data downloaded as of today.

| Fall in | Entry | Events in / out | Losing in / out | Tail test in / out (bound vs break-even) | Replay at 0.5%, a year, in / out | Worst drawdown in / out |
|---|---|---|---|---|---|---|
| 1 day | resting | 1,647 / 1,300 | 10.6% / 12.7% | passes / FAILS (14.3% vs 12.6%) | +0.5% / -0.3% | 4.7% / 2.8% |
| 1 day | taker | 2,522 / 1,916 | 8.4% / 11.5% | fails / fails | -2.8% / -4.6% | 14.1% / 7.0% |
| 3 days | resting | 1,828 / 1,365 | 10.7% / 13.5% | passes / FAILS (15.1% vs 13.5%) | -0.7% / +2.5% | 9.8% / 2.7% |
| 3 days | taker | 2,649 / 1,903 | 8.4% / 11.9% | fails / fails | -3.3% / -3.3% | 16.7% / 5.1% |
| 7 days | resting | 1,518 / 1,074 | 10.1% / 14.0% | passes / FAILS (15.8% vs 14.1%) | +0.7% / +0.2% | 4.9% / 3.5% |
| 7 days | taker | 2,013 / 1,486 | 8.5% / 11.8% | fails / fails | -1.6% / -5.6% | 9.1% / 8.4% |

- **The lead is dead in the pooled busy sample.** Every resting version passes in sample and fails out of sample
  (losing rate rises 2 to 4 points after April 2026); every taker version fails both halves and loses money in
  the replay. Larger stakes make it worse (resting 3 days at 2%: -4.7%/y in sample, drawdown 34.8%).
- Capacity is thin anyway: median $71 to $142 traded in the week before entry; 30% to 60% of entry days under
  100 contracts. The largest series (KXAPRPOTUS, approval ratings) loses money in every variant.
- Verdict: not an account, nothing for the paper config. The existing fall-rule account (YES at 10-25c, down 3c+
  in 7 days, report 3.27) is a different rule and is not affected.

### 3.38 Ideas queue 10: hourly bars for the last two days (6:30 pm CST, November 21)

Code only, no result yet. `research/hourly_bars.py` fetches 60-minute bid / ask / trade bars for the final 48 hours
before the close of every market a rule bets on, into its own database (`data\kalshi_hourly.db`, table
`candles_1h`, the same columns as the daily `candles`), so it never competes with the running history download
for the main database. Paced at 1 s a request, resumable, a final 4xx is written off, a throttled answer is
retried next run. 3 tests (fake client), 476 in all pass.
- First run: the Entertainment band (NO vs YES 5-35c, resting) at 45,000 contracts: 815 markets in its bets;
  the first 400 fetched in about 7 minutes, 398 with bars (18,048 hourly bars, about 45 a market), 2 empty, no
  errors. The other 415 come with the next run of the same command.
- Not yet used: the exit study still sells stops at the next DAILY open. Queue item 20 (added) replays the
  band's stops on the hourly bars to see whether the daily caveat changes any verdict of 3.28 / 3.36.
- Forward: nothing settled. Main account $1,010.72, 0 settled; rule accounts 0 settled (equity $980 to $1,000,
  the Entertainment taker lowest at -$20 marked at the bid); shadow logs: resting NO bids filled 11 of 14
  (busy 5-cent) and 8 of 8 (Entertainment band) decided so far.

### 3.39 Ideas queue 11: event baskets on every busy category (6:35 pm CST, November 21)

Item 11 asked for code that was already written: `research/event_baskets.py` (family 27, report 3.15, tried then on
Economics and Politics only). This round runs it on the busy sample of all eleven categories with a census
(the nine, Entertainment, Climate and Weather), same thresholds (YES bids adding up to 0.90 / 1.00 / 1.02 / 1.05 /
1.10 / 1.20), taker entry at the next open with fees, one basket per event. 6 thresholds, 3 splits each.
- With only the 405 events flagged in 3.15 known, the events Kalshi flags as EXCLUSIVE still show no free money:
  at 1.00+ 49 / 46 baskets in / out of sample, -0.9% / +0.8% (t +0.7), worst -3.3%; at 1.02+ 8 / 22, -0.3% /
  +0.4%; at 1.05+ 2 / 5, +0.1% / +2.7% (t 1.8, 5 baskets, 0 losing, locked at entry only +0.2%). None passes.
- Events flagged NOT exclusive lose, as before: -10% in sample, -18% to -20% out of sample, worst -100%.
- About 3,700 of the 4,100 candidate baskets are on events with no flag yet. Their "locked at entry" figure
  (+14% to +78%) is meaningless until the flag is known (3.15: never infer it). The flags are being fetched now
  (one request every 1.5 s, about 1.5 hours, `data\event_baskets_all.log`); the next check-in reads the table again
  with the flags known and writes the result here.
- Forward: nothing settled. Main account $1,010.72, 0 settled; a cycle is running (started 6:25 pm).

### 3.40 Ideas queue 11, finished: event baskets with Kalshi's flags known (4:15 am CST, November 22)

The detached flag fetch of 3.39 finished before the pause (flags for 3,706 of the 4,111 candidate events; the other
405 had them already). Same run, same 6 thresholds x 3 splits (18 variants), taker entry with fees, one basket per event.
- EXCLUSIVE events (the only case where "locked at entry" means anything) never pass in both halves:
  1.00+ in sample 429 baskets -0.37% (t -1.4), out of sample 673 baskets +0.73% (t +2.1), worst -3.4%;
  1.02+ 119 / 323 baskets, -0.09% (t -0.5) / +1.16% (t +2.3), worst -1.5%;
  1.05+ 13 / 55 baskets, +0.16% / +1.75% (t 2.8), worst -0.2%: in sample far too few; 1.10+ and 1.20+ almost empty.
  The "locked at entry" figure is negative or about zero at 1.00+ and 1.02+: after fees there is no lock; what
  out of sample earns is ordinary price drift, not an arbitrage.
- NOT exclusive and "all" lose in sample at every threshold (-2% to -5%, worst -100%) and are flat out of sample.
- Verdict: FAILS (in sample negative). No account. The 1.05+ exclusive corner (8-leg baskets, 55 out of sample) is
  a curiosity; noted as queue item 21, to look at only if the download adds many more exclusive events.
- Forward: nothing settled. Main account $1,010.31, 0 settled, 6 resting orders; a paper cycle began at 4:07 am
  after the resume.

### 3.41 Ideas queue 14: the Entertainment band by days to close, at 20,000 contracts (6:20 am CST, November 22)

Question: the taker version (3.30) was thin in 2025; does the resting band's edge come from short-dated markets, where
capital turns over fastest? `research/band_by_dte.py 20000`: busy Entertainment (5,802 markets, 1,570 events, closes
Feb 2022 to Sep 2026; 2,141 markets out of sample), "NO where YES is at 5-35c", resting, sliced by days to the
scheduled close; each slice enters at the first bar inside its window (a market can be in more than one slice).
Three slices plus the whole, 4 variants.

| slice | bets / events | per bet | tail test in / out of sample (loss rate, bound vs break-even) | replay at 1%, in / out |
|---|---|---|---|---|
| all | 1,526 / 691 | +7.39% | 22.4%, 25.7 < 35.3 pass / 21.4%, 26.4 < 33.8 pass | +9.1%/y DD 6.5% / +33.0%/y DD 6.6% |
| 0-7 d | 831 / 442 | +6.15% | 22.4%, 26.8 < 33.2 pass / 22.2%, 28.5 > 26.9 FAIL | +14.5%/y DD 6.6% / +20.2%/y DD 7.8% |
| 7-30 d | 422 / 242 | +7.08% | 20.3%, 25.8 < 30.0 pass / 23.2%, 34.4 < 34.9 pass (by a hair, 56 events) | +4.7%/y DD 3.6% / +15.6%/y DD 2.3% |
| 30+ d | 558 / 213 | +8.15% | 22.6%, 28.6 < 35.7 pass / 12.0%, 22.3 < 48.8 pass | +5.0%/y DD 4.8% / +15.8%/y DD 2.1% |

- The short-dated slice is NOT where the edge sits: it has the lowest per-bet return and fails the tail test out of
  sample (winners there make only +0.35 against a 0.94 loss). It turns capital fastest (median hold 3.4 days) and is
  the deepest (median 13,151 contracts on the entry day against 1,462 for 30+ days).
- The 30+ day slice earns the most per bet, but its 2025 is +3.9% (185 bets) and its out-of-sample figure leans on
  2026 (+10.8%, 6 losing of 50 events); the thinnest slice (14% of entry days under 100 contracts).
- Verdict: no slice beats the whole band; the band is spread across horizons, so the paper account `rule_ent_band`
  (all horizons) stays as it is. No new account.
- Forward: rule accounts have almost nothing settled (control_ent_quiet 2 bets); main account $1,009.89, 0 settled,
  5 resting orders; a paper cycle began at 6:09 am.

### 3.42 Ideas queue 15: the 5-cent rule without its 0-3c corner (7:35 am CST, November 22)

Question (from 3.31): the 5-cent rule's money sits in 3-6c; does dropping the 0-3c corner give a better rule? New
rule name in `research/families.py` (added, nothing renamed; one test): "NO at mid 3-5c, <= 30d, spread <= 5c", family
2. `analyze_rule.py --sample liquid --categories <the nine>`, at 45,000 contracts and at the default census level,
resting and taker, with the whole 5-cent rule beside it on the same data. 8 runs, 4 of them new variants. Data: at
45,000, 8,893 markets, 3,202 events, closes Aug 2021 to Sep 2026; default level 53,711 markets, 11,098 events.

| level | rule | entry | bets (events) | per bet | tail test in / out (bound vs break-even) | replay 1%, in / out a year (worst DD) | median $ traded 7d before |
|---|---|---|---|---|---|---|---|
| 45,000 | 3-5c | resting | 662 (459) | +3.27% | 4.73 < 7.07 pass / 5.68 < 7.22 pass | +2.0% (2.5%) / +13.6% (1.8%) | $1,416 |
| 45,000 | whole 0-5c | resting | 1,188 (716) | +2.07% | 4.77 < 6.03 pass / 3.99 < 5.99 pass | +1.6% (3.0%) / +18.1% (1.5%) | $844 |
| 45,000 | 3-5c | taker | 858 (573) | +1.25% | 4.57 > 4.24 FAIL / 4.83 = 4.83 FAIL | +0.3% (3.4%) / +8.8% (1.7%) | $1,390 |
| 45,000 | whole 0-5c | taker | 1,503 (861) | +0.70% | 4.05 > 3.44 FAIL / 3.54 < 3.83 pass | +0.1% (4.0%) / +8.9% (1.9%) | $844 |
| default | 3-5c | resting | 3,349 (2,001) | +0.96% | 7.51 < 8.22 pass / 9.93 > 8.93 FAIL | +2.3% (12.7%) / -13.8% (12.1%) | $67 |
| default | whole 0-5c | resting | 5,470 (2,715) | +0.74% | 6.77 < 7.70 pass / 9.05 > 8.16 FAIL | +2.3% (12.0%) / -14.7% (12.8%) | $45 |
| default | 3-5c | taker | 6,081 (3,021) | -0.21% | FAIL / FAIL | -2.5% (15.4%) / -21.8% (13.7%) | $37 |
| default | whole 0-5c | taker | 9,419 (3,798) | -0.19% | FAIL / FAIL | -3.7% (19.3%) / -17.4% (11.0%) | $26 |

- At 45,000, resting: dropping 0-3c raises the per-bet return from +2.07% to +3.27% and widens the margin below
  break-even in both halves (in sample 2.3 points against 1.3; out of sample 1.5 against 2.0: narrower out of sample,
  with only 134 events). The markets are deeper (median $1,416 a week against $844). But the account earns LESS out of
  sample (+13.6% a year against +18.1%): fewer bets, less capital at work (10% against 20%); in sample it earns a
  little more (+2.0% against +1.6%). Drawdowns are alike (1.5-3.0%). Losing bets by year: 2024 1 of 30, 2025 4 of 206,
  2026 7 of 403; the largest series has 5% of the bets.
- Taker: fails at 45,000 in both halves (the whole rule's taker fails in sample too). At the default level both
  versions fail out of sample and lose about 14% a year: the busy-market level stays what pays, as 3.7 found.
- Verdict: a sharpening, not a better account. Per bet it is better; in money out of sample it is worse, and the
  difference sits inside the noise of 4 variants on 134-227 events. The paper account `rule_5c_busy` already buys
  every market this rule would (it is a strict subset), so no new account: queue item 22 reads rule_5c_busy's settled
  bets split by entry price (0-3c against 3-5c) once 30+ have settled, which tests the same question forward for free.
- Forward: nothing settled. Rule accounts: rule_5c_busy_taker -$3.09 (27 open), rule_ent_band_taker -$19.58 (69
  open), controls flat; the shadow fill rates so far 79% (14 decided) and 100% (9 decided) against the backtest's
  55-80% model, too few to read. Main account $1,009.89, 0 settled; the paper cycle of 7:08 am is running.

### 3.43 Ideas queue 16: the nine-category wide band at 45,000 by days to close and year (9:25 am CST, November 22)

Question (from 3.33): the nine pooled band (NO where YES is at 5-35c, resting) at 45,000 earns almost only in 2026;
is that a change in the market or a shift towards short-dated markets? `research/band_by_dte.py 45000 nine` (the
3.41 script, now with a `nine` option): 8,893 markets, 3,202 events, closes Aug 2021 to Sep 2026, 3,571 markets out
of sample. Three slices by days to the scheduled close plus the whole, first bar per market inside the window; 4
variants here, 16 with report 3.33 on this band.

| slice | bets / events | per bet | 2025 / 2026 per bet | tail test in / out (bound vs break-even) | replay at 1%, in / out a year (worst DD) | median $ traded 7d before |
|---|---|---|---|---|---|---|
| all | 2,355 / 1,145 | +4.18% | +1.3% / +6.8% | 23.71 < 28.01 pass / 28.41 < 31.02 pass | +1.0% (11.2%) / +15.2% (6.2%) | $4,799 |
| 0-7 d | 615 / 391 | +5.97% | +4.2% / +7.6% | 20.20 < 22.82 pass / 24.89 < 25.64 pass (by 0.75 pt, 135 events) | +5.5% (4.4%) / +19.1% (4.6%) | $6,688 |
| 7-30 d | 788 / 491 | +4.94% | +3.0% / +5.0% | 20.08 < 24.15 pass / 31.97 > 28.10 FAIL | +7.0% (4.2%) / +8.7% (7.8%) | $5,190 |
| 30+ d | 1,536 / 711 | +2.94% | -0.0% / +6.4% | 25.70 < 27.39 pass / 30.53 > 30.41 FAIL | -2.0% (12.3%) / +5.2% (4.9%) | $4,159 |

- Mostly a horizon effect: the long-dated slice is flat in 2025 (682 bets, -0.0% a bet) and its long holds (median
  65 days) are what make the whole band's in-sample replay weak (+1.0% a year, 11.2% drawdown). Short-dated markets
  earn in 2025 as well (0-7 d +4.2%, 7-30 d +3.0%), so 2026 is not the only source. All slices are better in 2026, so
  part of the jump is the market too.
- The 0-7 day slice is the only one that passes the tail test in both halves, with the best replays (in sample +5.5% a
  year, drawdown 4.4%; out of sample +19.1%, 4.6%; capital at work 1-3%, median hold 4.4 days) and the deepest
  markets. But out of sample it passes by 0.75 points on 135 events, picked as the best of 4 slices after 12 earlier
  variants; largest series 8% of bets (gas prices, CPI, WTI: data-release markets).
- Verdict: a lead, not yet an account. Before a paper account (queue item 13), the same slice must hold at a second
  census level (queue item 23: 0-7 d at 20,000), as Politics in 3.33 did not. No account added this round.
- Forward: nothing settled in any account (main $1,009.89, 3 open, 4 resting; rule accounts flat to -$19 on open
  taker positions, controls flat). The paper cycle of 8:14 am is running.

### 3.44 Ideas queue 17: the Climate and Weather 5-cent rule again, and pooled with Politics (10:10 am CST, November 22)

The rule "NO at mid <= 5c, <= 30d, spread <= 5c" at 45,000 contracts, liquid sample, resting (mk) and taker (tk).
4 runs (2 pools x 2 entries) plus Politics alone resting for comparison.

- Climate and Weather alone: unchanged from 3.34 (89 events resting, 111 taker, 0 losing); the download has not
  added Climate and Weather markets at this level yet. Still fails the tail test in both halves (too few events).
- Climate and Weather + Politics, resting: passes both halves (in 252 events, 4 losing, bound 3.60% vs break-even
  5.84%; out 115 events, 0 losing, bound 2.57% vs 5.53%). Replay at 1%: +1.6%/y in sample (DD 1.7%), +12.6%/y out
  (DD 0.0%). Median $688 traded in the week before entry; 14% of entry days under 100 contracts. Largest series 3%.
- Taker: fails in sample (bound 3.40% vs 3.40%), passes out; replay at 1% +0.4%/y in sample, DD 3.1%.
- Politics alone, resting, already passes both halves (in 195 events bound 4.63% vs 6.12%; out 83 events 3.54% vs
  6.01%; replay 1% +1.1%/y in, +10.8%/y out). Climate adds about half a point a year in sample and 1.8 out, no
  drawdown, and narrows the bounds: it helps, but Politics carries the pool.
- Verdict: a pass on the tests, but not a new account. The two categories were picked after the fact from per-category
  results (3.33, 3.34), so the pool's pass is partly selection; the in-sample year is weak (+1.6%/y); and both
  categories' 5-cent markets are already in paper: Politics inside rule_5c_busy (nine categories), so the forward
  test of this pool can be read off rule_5c_busy's Politics bets plus a Climate split later. Re-test Climate alone
  when the download adds its markets (item 17 stays as a standing re-test, low priority).
- Forward: nothing settled in any account (main $1,009.89; 23 variant accounts, controls control_fade -$27.83 and
  control_coinflip -$33.54; 10 rule accounts, 0 settled). Shadow logs: resting NO bids filled 12 of 16 (5-cent) and
  11 of 11 (Entertainment band) decided so far, above the backtest's fill model; too few to judge (needs 50+).

### 3.45 Ideas queue 18: the combined account without the 5-cent leg, and with that leg at 45,000 (12:40 pm CST, November 22)

`research/combined.py` has two new options (tests added, 478 pass): `--five-cumvol N` puts the 5-cent nine-category
leg on bars where the market had traded N contracts (the other legs unchanged), and `--min-cumvol N` sets the census
level for every leg; a new row "the other three legs (no 5-cent nine)" is always printed. Hold to settlement, stakes
0.25%, 0.5%, 1%; 4 runs x 3 stakes x 8 accounts = 96 rows, so read the best cell as partly luck.

**First, a change in the data that touches every default-level result.** The download's random pass has now
finished for Economics, Politics, Elections, Entertainment, Companies, Health, Science and Technology and World, so
`panel.load(sample="liquid")` finds those categories "complete down to 1 contract" and its DEFAULT level now takes
in every market, quiet ones too. At that default the Entertainment band earns +0.05% a bet out of sample (3,528 bets)
and the combined account loses (0.25%: -4.4%/y, DD 11.8%). That is the quiet-market result the control account
expects, not a new finding about the rule. From now on every run must pass `--min-cumvol` (5,000 for the accounts'
level, 45,000 for report 3.7's): default-level figures from today on are not comparable with reports 3.22-3.35. (Report
3.42's "default level fails out of sample" may already have been affected.)

At 5,000 contracts (comparable with 3.35; the Climate leg drops out: its census is complete only to 31,452):

| account, out of sample | 0.25% /y | DD | 0.5% /y | DD | 1% /y | DD | bets out |
|---|---|---|---|---|---|---|---|
| all four legs, 5-cent at 5,000 | +7.6% | 5.7% | +1.7% | 10.1% | +6.3% | 8.7% | 2,719 |
| all four legs, 5-cent at 45,000 | +10.3% | 6.0% | +3.3% | 11.0% | -0.7% | 14.3% | 1,922 |
| other three legs, no 5-cent nine | +8.9% | 5.9% | +0.7% | 12.5% | +1.3% | 15.7% | 1,573 |
| Entertainment band alone | +7.2% | 6.3% | +1.2% | 12.6% | -2.5% | 18.5% | 1,198 |

In sample at 0.25%: +5.0%/y (DD 4.0%), +5.3% (3.7%), +4.9% (3.7%). The 5-cent leg at 45,000 alone: +2.4% a bet out of
sample (349 bets) against +1.4% at 5,000; it is the steadiest leg (out-of-sample Sharpe 3.3).

- Answer to item 18: at the risk-averse stake (0.25%) the 45,000 version of the 5-cent leg is the best of the three
  out of sample (+10.3%/y against +7.6% with the 5,000 leg and +8.9% without it) and equal in sample; dropping the leg
  does not help. Above 0.25% every version earns less and draws down more out of sample.
- **The bigger result: the Entertainment band is weaker on the larger download.** At 5,000 it now has 2,252 / 1,198
  bets (3.35 had 1,294 / 643) and earns +5.3% / +3.2% a bet (3.29: +7.3% / +7.2%). Its replay at 1% out of sample is
  now -2.5%/y with an 18.5% drawdown (3.29: +31%/y, DD 6.0%). The paper accounts rule_ent_band (1%) and rule_combined
  (0.5%: now +0.8% to +3.3%/y out of sample, DD 10-13%) were built on the older figures. They are left as they are
  (their record runs on), but the tail test of the band must be re-run on the finished download before anything is
  read off them: queue item 25, worked next.
- Forward: main $1,010.18, 1 settled (+$8.57); 23 variant accounts, 0 settled (controls control_fade -$27.22,
  control_coinflip -$34.86); 10 rule accounts, 0 settled. Shadow logs: resting NO bids filled 12 of 16 (5-cent) and 11
  of 11 (Entertainment band); too few to judge.

### 3.46 Ideas queue 25: the Entertainment band and the 5-cent rule on the finished download (1:30 pm CST, November 22)

Report 3.45 found the band weaker on the larger download. Re-run of report 3.29 / 3.30 / 3.7 with the census level always
given (`analyze_rule.py --sample liquid --min-cumvol N`): "NO where YES is at 5-35c", Entertainment, resting (mk) and taker
(tk) at 5,000 / 20,000 / 45,000, and the 5-cent rule ("NO at mid <= 5c, <= 30d, spread <= 5c") on the nine at 45,000. 8 runs,
all fixed beforehand.

| Rule, level, entry | Bets (events) | Per bet | Tail test in / out | Replay 1%, in / out a year | Worst DD in / out |
|---|---|---|---|---|---|
| band, 5,000, resting | 3,450 (1,369) | +4.57% | passes (30.1 vs 37.2%) / passes (30.2 vs 32.1%) | +4.9% / **-1.0%** | 12.3% / **18.0%** |
| band, 5,000, taker | 3,855 (1,473) | +0.76% | **fails / fails** | -2.5% / -6.9% | 16.6% / 19.3% |
| band, 20,000, resting | 1,526 (691) | +7.39% | passes (25.7 vs 35.3%) / passes (26.4 vs 33.8%) | +9.1% / +33.0% | 6.5% / 6.6% |
| band, 20,000, taker | 1,675 (726) | +3.47% | passes / passes | +2.9% / +13.7% | 7.6% / 7.4% |
| band, 45,000, resting | 815 (402) | +7.14% | passes (28.7 vs 34.3%) / passes (22.2 vs 35.9%) | +9.9% / +25.5% | 8.1% / 2.3% |
| band, 45,000, taker | 883 (413) | +3.45% | fails (29.0 vs 28.5%) / passes | +2.0% / +16.1% | 10.0% / 4.0% |
| 5-cent, nine, 45,000, resting | 1,188 (716) | +2.07% | passes (4.8 vs 6.0%) / passes (4.0 vs 6.0%) | +1.6% / +18.1% | 3.0% / 1.5% |
| 5-cent, nine, 45,000, taker | 1,503 (861) | +0.70% | fails / passes | +0.1% / +8.9% | 4.0% / 1.9% |

**Result: at 20,000 and 45,000 nothing changed** (the same bets as 3.29 / 3.30: the download has not added busy markets), and
the 5-cent rule at 45,000 is exactly report 3.42's figure. **At 5,000 the band is weaker**: the download added about 1,200
markets between 5,000 and 20,000 contracts; per bet it fell from +7.3% to +4.57%. It still passes the tail test in both
halves (out of sample by 1.9 points), but the account replay at 1% loses out of sample (-1.0%/y, worst drawdown 18.0%; at 0.5%
+2.9%/y, DD 12.1%), and the taker version now fails both halves. Capacity at 5,000: median $854 traded in the week before
entry (at 20,000: $2,805; at 45,000: $5,663).

- Verdicts that stand: 3.29's band at 20,000 and 45,000; 3.30's taker at 20,000 (passes) and 45,000 (fails in sample); 3.7's
  5-cent rule at 45,000. Verdict that does NOT stand: the band at 5,000 as a 1% account (3.29: +31%/y out of sample, DD 6.0%).
- The paper accounts rule_ent_band, rule_ent_band_taker and rule_combined use the 5,000 level. They keep running unchanged
  (changing them would break their record), but their backtest basis is now weak: read them with this in mind.
- New paper account `rule_ent_band_20k` (rules.yaml, under a new name, allowed by the standing instruction): the same band,
  resting, 1% a bet, 20,000+ contracts only, the level that still passes everything. It is a subset of rule_ent_band's markets.
- Forward: main $1,010.18, 1 settled; 23 variant accounts, 0 settled (controls control_fade -$27.22, control_coinflip
  -$34.86); 10 rule accounts (11 from the next cycle), 0 settled. Shadow logs: resting fills 12 of 16 and 11 of 11.

### 3.47 Ideas queue 19: does a recent fall add anything to the Entertainment band? (3:30 pm CST, November 22)

`research/analyze_rule.py --sample liquid --min-cumvol N --categories Entertainment --side no --entry mk`, N = 20,000 and
45,000, on the finished download. Six rules at each level (12 variants): the band itself (NO where YES is at 5-35c), YES at
10-25c after a fall of 3c+ in 1 / 3 / 7 days, the opposite move (10-25c, up 3c+ in 7 days), and 3-10c after a 7-day fall.
All resting. Per bet is the mean over all bets; the tail test is per event, in sample / out of sample.

| Level | Rule | Events | Per bet | Losing events in / out | Tail test in / out | Replay 1% a year in / out | Worst DD in / out |
|---|---|---|---|---|---|---|---|
| 20,000 | band 5-35c | 691 | +7.39% | 22.4% / 21.4% | passes / passes | +9.1% / +33.0% | 6.5% / 6.6% |
| 20,000 | 10-25c, down in 1d | 402 | +7.14% | 21.4% / 13.5% | passes / passes | +7.8% / +27.8% | 7.4% / 2.9% |
| 20,000 | 10-25c, down in 3d | 403 | +7.65% | 21.1% / 13.6% | passes / passes | +5.5% / +25.2% | 7.5% / 2.8% |
| 20,000 | 10-25c, down in 7d | 359 | +9.23% | 19.8% / 11.8% | passes / passes | +12.2% / +26.0% | 6.9% / 2.7% |
| 20,000 | 10-25c, UP in 7d | 201 | +5.87% | 20.5% / 12.0% | FAILS (26.7% vs 26.4%) / passes | +2.6% / +8.7% | 4.4% / 2.8% |
| 20,000 | 3-10c, down in 7d | 404 | +4.83% | 4.9% / 5.9% | passes / passes | +4.6% / +9.0% | 3.4% / 2.4% |
| 45,000 | band 5-35c | 402 | +7.14% | 24.1% / 15.7% | passes / passes | +9.9% / +25.5% | 8.1% / 2.3% |
| 45,000 | 10-25c, down in 1d | 226 | +8.04% | 19.5% / 9.7% | passes / passes | +5.0% / +28.0% | 6.5% / 1.6% |
| 45,000 | 10-25c, down in 3d | 222 | +8.38% | 19.2% / 9.1% | passes / passes | +6.9% / +20.0% | 7.4% / 1.8% |
| 45,000 | 10-25c, down in 7d | 218 | +10.21% | 17.1% / 6.1% | passes / passes | +8.2% / +20.4% | 4.6% / 2.0% |
| 45,000 | 10-25c, UP in 7d | 105 | +3.11% | 25.6% / 7.4% | FAILS (35.0% vs 24.8%) / passes | +1.1% / +10.4% | 5.2% / 1.0% |
| 45,000 | 3-10c, down in 7d | 254 | +5.49% | 3.3% / 4.1% | passes / passes | +8.6% / +6.3% | 1.7% / 1.0% |

- **A fall helps per bet, not per account.** After a 7-day fall the 10-25c bets earn +9.2% / +10.2% a bet against the
  band's +7.4% / +7.1%, and every falling version passes both halves at both levels; the same prices after a RISE earn about
  half and fail the tail test in sample. So the direction of the last move carries some information, the opposite of what
  the pooled nine categories showed (3.37). But the falling subsets trade half as often, and the 1% replay earns less a
  year than the whole band out of sample (+20% to +28% against +25.5% / +33.0%); in sample the 7-day fall is ahead only at
  20,000 (+12.2% against +9.1%).
- Caveats: 12 variants, no t-statistic above 3 is claimed; the band and the fall rules overlap (a fall rule's bets are mostly
  band bets), and there is no "10-25c with no fall" rule to compare against directly (item 28 added). Capacity is the
  band's: median $3,000 to $6,800 traded in the week before entry, under 100 contracts on 5-9% of entry days.
- Verdict: no new account. The existing `rule_ent_fall` (10-25c, down 3c+ in 7 days, 5,000+) is the forward test of this
  and stays as it is; the band stays the main Entertainment account.
- Forward: main $1,010.18, 1 settled (+$8.57); a cycle has been running since 2:20 pm. 23 variant accounts, 0 settled
  (controls control_fade -$27.26, control_coinflip -$34.86); 11 rule accounts, 0 settled (rule_ent_band -$2.27 against its
  control control_ent_quiet -$2.53; rule_5c_busy -$0.22 against control_5c_quiet $0.00). Shadow logs: resting fills 12 of 16
  (busy 5-cent) and 11 of 11 (Entertainment band) decided.

### 3.48 Ideas queue 20: the Entertainment band's stops on hourly bars (4:45 pm CST, November 22)

The hourly fetch of 3.38 is finished: all 815 markets the band (NO vs YES 5-35c, resting) bets on at 45,000 contracts,
813 with bars, 34,278 hourly bars for the last 48 hours before each close. `research/exits.py` got an hourly option
(`Exits(p, hourly)`, `load_hourly`; `research/exit_study.py --hourly data\kalshi_hourly.db`): a stop is also tested on
every hourly bar that ends inside the daily bar being looked at, before the daily test, and is sold at the next hourly
bar's opening bid (taker fee) if that bar opens two-sided within the hour; otherwise the daily rule stands. Take-profit
and time exits stay daily. 1 new test (479 pass). Same 25 policies as 3.28 / 3.36, run on the same panel daily and hourly
(3,178 markets, 942 events; 573 bets in sample, 242 out; 1,278 stop sales moved to an hourly bar over all policies).

| stop policy | in/bet daily -> hourly | out/bet daily -> hourly | out 1% replay a year | out tail test | stopped out |
|---|---|---|---|---|---|
| -5 points | +1.80% -> -0.52% | +6.07% -> +1.11% | +14.0% -> +1.1% | passes -> FAILS | 29% -> 44% |
| -10 points | +3.15% -> +1.28% | +6.44% -> +3.88% | +14.1% -> +8.8% | passes -> passes | 24% -> 33% |
| -20 points | +4.54% -> +2.37% | +8.23% -> +7.44% | +19.8% -> +19.0% | passes -> passes | 15% -> 19% |
| our mid <= 0.90 | -0.94% -> -1.58% | +2.50% -> -1.77% | +4.9% -> -6.0% | passes -> FAILS | 50% -> 71% |
| our mid <= 0.85 | -0.18% -> -0.94% | +2.67% -> -1.36% | +4.9% -> -5.2% | passes -> FAILS | 42% -> 59% |
| our mid <= 0.75 | +1.58% -> +0.61% | +5.08% -> +0.85% | +11.6% -> +1.4% | passes -> FAILS | 29% -> 43% |
| hold to settlement (no stop) | +5.94% | +9.96% | +25.5%, worst drawdown 2.3% | passes | - |

- **Every stop gets worse on hourly bars, in both halves.** The daily bars hid intraday dips that recover: on hourly bars
  the stops fire a third to a half more often, sell near the low, and the bet then settles as a win. Four of the six stops
  now fail the tail test out of sample and three lose money there. The daily caveat of 3.28 was flattering the stops, not
  hurting them.
- **No verdict of 3.28 / 3.36 changes:** holding to settlement was already ahead of every stop and stays the policy; the
  in-sample pick is still "take at 0.97, taker" (+27.8%/y out of sample against hold +25.5%/y, inside the noise of 25
  policies), and the take-profit rows are unchanged (they stay daily). 25 policies x 2 bar types tried; no t above 3 is claimed.
- Caveat: hourly bars cover only the last 48 hours of each market; earlier stops are still daily. That can only add more
  intraday stop-outs, not fewer, so the direction of the result is safe.
- For the paper accounts: the Claude exit accounts with stops (claude_only_stop15, claude_only_take_stop) test stops on live
  quotes each cycle; nothing settled yet. Item 29 added: the same on the 5-cent rule's markets.
- Forward: main $1,010.18, 1 settled (+$8.57); 23 variant accounts, 0 settled (controls control_fade -$26.71,
  control_coinflip -$35.08); 11 rule accounts, 0 settled (rule_ent_band -$2.37 against control_ent_quiet -$2.41;
  rule_5c_busy -$0.22 against control_5c_quiet $0.00). Shadow logs: resting fills 12 of 16 (busy 5-cent) and 11 of 11
  (Entertainment band) decided, none settled.

## 3.49 Ideas queue 23: the nine-category wide band at 0-7 days fails out of sample at 20,000 and 5,000 (6:20 pm CST, Nov 22)

Report 3.43 found the nine-category wide band (NO where YES is at 5-35c, resting) passing both halves at 45,000 contracts
only in its 0-7 day slice, by 0.75 pt out of sample. The pre-stated check: the same slice at 20,000 and 5,000
(`research/band_by_dte.py 20000 nine`, `... 5000 nine`); a paper account only if it passes both halves at 20,000.

| level, slice | bets / events | per bet | tail test in / out (bound vs break-even) | 1% replay in / out, a year (worst DD) |
|---|---|---|---|---|
| 20,000, all | 3,268 / 1,596 | +3.60% | passes / passes (29.0 vs 31.7) | +3.1% (13.4%) / +11.5% (10.0%) |
| 20,000, 0-7d | 903 / 562 | +3.67% | passes / **FAILS** (30.7 vs 26.4) | +6.4% (5.5%) / +4.1% (7.8%) |
| 20,000, 7-30d | - / 695 | - | passes / passes (27.8 vs 28.3) | +8.1% (7.3%) / +29.6% (6.5%) |
| 20,000, 30+d | - / 981 | - | passes / passes | -2.0% (13.5%) / +8.7% (5.1%) |
| 5,000, 0-7d | 1,909 / 1,077 | +3.01% | passes / **FAILS** (27.7 vs 27.4) | +7.0% (14.8%) / +20.5% (16.4%) |
| 5,000, 7-30d | 2,198 / 1,196 | +4.07% | passes / passes by a hair (27.27 vs 27.35) | +11.0% (8.9%) / +36.1% (11.3%) |
| 5,000, 30+d | 3,641 / 1,709 | +2.98% | passes / passes | -1.3% (15.0%) / -2.8% (12.0%) |

- **The 0-7 day lead of 3.43 does not hold below 45,000**: it fails the tail test out of sample at both 20,000 and 5,000.
  No paper account. The 45,000 pass was the thin edge of a slice that fails at the levels with more events.
- At the lower levels it is the 7-30 day slice that passes both halves, by under 0.6 pt out of sample, while 3.43 found it
  failing at 45,000. With 3 slices x 3 levels tried and the passing slice changing with the level, this is the noise of
  slicing, not a finding; no t above 3 is claimed. The 30+ day slice loses in the replay in sample at both levels (as in 3.43).
- Capacity (20,000, 0-7d): median $3,706 traded in the 7 days before entry; 5% of entry days under 100 contracts.
- Forward: main $1,008.69, 1 settled (+$8.57); 23 variant accounts, 0 settled (controls control_fade -$26.71,
  control_coinflip -$35.08); 11 rule accounts, 0 settled (rule_ent_band -$2.37 against control_ent_quiet -$2.41;
  rule_5c_busy -$0.22 against control_5c_quiet $0.00). Shadow logs: resting fills 12 of 16 (busy 5-cent) and 12 of 12
  (Entertainment band) decided, none settled.

## 3.50 Ideas queue 26: the Entertainment band's 5,000-20,000 layer: it is the whole 5,000 account, and its quiet markets are not the losers (7:15 pm CST, Nov 22)

Question (3.46): at 5,000 contracts the band now earns less than at 20,000 (1% replay out of sample -1.0%/y, DD 18%). Is
it the markets between 5,000 and 20,000 that lose? New: `research/analyze_rule.py --max-cumvol N` keeps only bars at which
the market had traded fewer than N contracts so far (known at the bar; `below_cumvol`, +1 test, 480 pass).

- **The layer cut by volume at entry is the whole 5,000 account.** With `--min-cumvol 5000 --max-cumvol 20000` the band
  (resting) gives exactly the 3.46 figures: 3,450 bets in 1,369 events, +4.57% a bet, tail test passes both halves (30.1 vs
  37.2%, 30.2 vs 32.1%), replay 1% +4.9%/y in, -1.0%/y out, DD 18.0%. Taker: +0.76% a bet, fails both halves, loses in
  every replay. The account bets on a market's first qualifying bar, which is always before it reaches 20,000 contracts.
  The 20,000 account trades the same markets, but later and at other prices. So "the layer" cannot be cut ex ante by volume.
- **Diagnostic only (uses each market's FINAL volume, which is hindsight; not a rule):**

| resting, 5,000 account | in sample: bets / events / per bet / tail | out of sample: bets / events / per bet / tail |
|---|---|---|
| markets that never reached 20,000 | 605 / 425 / +8.13% / passes (17.5 vs 24.0%) | 292 / 205 / +5.67% / passes (18.8 vs 20.6%) |
| markets that reached 20,000 later | 1,647 / 664 / +4.25% / passes (34.3 vs 38.6%) | 906 / 319 / +2.42% / **FAILS** (34.6 vs 34.4%) |

  Taker, same split: never-busy +4.36% / +3.21% (passes both); later-busy -0.34% / -0.98% (fails both).
- Read: the quiet markets are the band's best bets, not its losers; the weak part is markets that went on to trade heavily.
  Final volume is partly caused by the outcome (a market whose YES comes alive draws trading), so this split is biased and
  says nothing tradeable. It does rule out the guess of item 26: the 5,000 account is not dragged down by a quiet layer.
- No account changes. rule_ent_band and rule_combined (5,000+) keep running; rule_ent_band_20k is the cleaner test. Item 30
  added: for markets that reach 20,000, compare the bet at the 5,000 bar with the bet at the 20,000 bar (entry timing).
- Forward: main $1,008.96, 1 settled (+$8.57); 23 variant accounts, 0 settled (controls control_fade -$26.71,
  control_coinflip -$35.08); 11 rule accounts, 0 settled (rule_ent_band -$2.37 against control_ent_quiet -$2.41;
  rule_5c_busy -$0.22 against control_5c_quiet $0.00). Shadow logs: resting fills 12 of 16 and 12 of 12, none settled.

## 3.51 Ideas queue 28: the Entertainment fall effect isolated: 10-25c bets with no fall against those after one (9:25 pm CST, Nov 22)

New rule name in `research/families.py` ("mid 10-25c, no 3c+ fall in 7d", family 14 price x momentum; also 1d and 3d and the
other price bands): every bar at the price WITHOUT a 3c+ fall in the window, including bars with no 7-day history, so it and
"down 3c+ in 7d" split the 10-25c bets exactly (1 test, 481 pass). `research/analyze_rule.py --sample liquid --min-cumvol N
--categories Entertainment --side no --entry mk`, N = 20,000 and 45,000, on the download as of tonight. 2 new variants (the
fall rows are re-runs of 3.47, unchanged).

| Level | Rule | Bets (events) | Per bet | Losing events in / out | Tail test in / out | Replay 1% a year in / out | Worst DD in / out |
|---|---|---|---|---|---|---|---|
| 20,000 | 10-25c, down 3c+ in 7d | 581 (359) | +9.23% | 19.8% / 11.8% | passes / passes | +12.2% / +26.0% | 6.9% / 2.7% |
| 20,000 | 10-25c, NO fall in 7d | 658 (397) | +3.59% | 21.3% / 19.2% | FAILS (25.8% vs 25.6%) / FAILS (25.9% vs 24.9%) | +1.4% / +9.6% | 10.0% / 5.8% |
| 45,000 | 10-25c, down 3c+ in 7d | 305 (218) | +10.21% | 17.1% / 6.1% | passes / passes | +8.2% / +20.4% | 4.6% / 2.0% |
| 45,000 | 10-25c, NO fall in 7d | 328 (197) | +5.30% | 23.0% / 12.1% | FAILS (29.7% vs 27.2%) / passes | +2.8% / +13.2% | 6.5% / 2.4% |

- **Most of the 10-25c money is the fall.** Without a fall the same prices earn a third to a half as much a bet, are flat in
  2025 (+1.2% / -1.3% a bet), fail the tail test in sample at both levels and out of sample at 20,000, and the 1% replay in
  sample earns +1.4% / +2.8% a year with a worse drawdown at 20,000 (10.0%). They do not lose outright: per bet stays positive
  in both halves, so the band is not carried by the fall alone; its other prices (5-10c, 25-35c) are not split here.
- Caveat: 3.47 picked the fall rule after seeing the band, and the 7-day window was one of three; 2 new variants here, no
  t-statistic above 3 is claimed. Capacity as the band (median $3,100 / $5,500 traded in the 7 days before entry).
- Verdict: no account change. `rule_ent_fall` (5,000+) is the forward test; the band stays. Item 31 added: the same split for the
  band's 3-10c and 25-50c prices, to see whether the fall effect holds across the band.
- Forward: main $1,007.88, 1 settled (+$8.57); a cycle has been running since 8:24 pm. 23 variant accounts, 1 settled (main);
  controls control_fade -$30.28, control_coinflip -$38.65. 11 rule accounts, 0 settled (rule_ent_band -$2.22 against
  control_ent_quiet -$2.29; rule_ent_band_20k -$1.24; rule_5c_busy -$0.22 against control_5c_quiet $0.00; rule_ent_fall -$0.45).
  Shadow logs: resting fills 12 of 17 (busy 5-cent) and 12 of 12 (Entertainment band) decided.

## 3.52 Ideas queue 30: Entertainment band entry timing: the same markets bet at their first 5,000 bar against their first 20,000 / 45,000 bar (10:15 pm CST, Nov 22)

New script `research/entry_timing.py` (+1 test, 482 pass): loads the liquid Entertainment sample at 5,000, takes the band
("NO where YES is at 5-35c", NO, resting) and, for every market the band also bets once it has traded the higher level
(cumvol known at the bar), compares its first bet at all ("early") with its first bet at the higher level ("late"). Which
markets get a late bet is known only afterwards: a diagnostic of timing, not a tradeable split. 2 comparisons.

| Late level | Group | Bets (events) | Per bet | Median hold | Tail test in / out |
|---|---|---|---|---|---|
| 20,000 | same markets, early bet | 1,526 (691) | +9.77% (in +9.66 / out +9.99) | 13.7 d | passes / passes |
| 20,000 | same markets, late bet | 1,526 (691) | +7.39% (in +7.58 / out +7.00) | 6.4 d | passes / passes |
| 20,000 | early only (no late bet) | 1,924 (1,069) | +0.44% (in +1.64 / out -1.67) | 7.0 d | FAILS / FAILS |
| 45,000 | same markets, early bet | 815 (402) | +11.54% (in +9.46 / out +16.47) | 16.4 d | passes / passes |
| 45,000 | same markets, late bet | 815 (402) | +7.14% (in +5.94 / out +9.96) | 5.4 d | passes / passes |
| 45,000 | early only (no late bet) | 2,635 (1,266) | +2.41% (in +3.86 / out -0.14) | 7.9 d | passes / FAILS |

- **Waiting is not what earns.** On the same markets the early bet earns MORE a bet than the late one (+2.4 / +4.4 points), at a
  lower NO price (0.801 against 0.814 at 20,000): the NO side tends to get dearer while the market gets busy. Waiting earns less
  a bet but frees capital sooner (median hold 6.4 against 13.7 days), so per day held the late bet is roughly comparable or
  better; the account replays of rule_ent_band (5,000+) and rule_ent_band_20k (3.46) already measure that trade-off.
- **The 5,000 account's weakness is in the other markets**: those the band bets at 5,000 but never again once they are busy
  (out of the band by then, or never busy) earn about nothing and fail the tail test out of sample at both levels. Which
  markets those are is not known at entry, so this does not give a filter; it does say the 20,000 account's edge is the same
  markets' edge, entered later, not a different set of markets.
- Verdict: no account change. Item 32 added (does the NO price drift up between the early and late bar in band markets
  generally: a drift rule with a known-at-the-bar signal).
- Forward: main $1,007.88, 1 settled (+$8.57); last cycle ok at 9:55 pm (8 forecasts, 1 order). Nothing new settled.

## 3.53 Ideas queue 31: the fall split across the rest of the Entertainment band, 3-10c and 25-50c (1:20 am CST, Nov 23)

`research/analyze_rule.py --sample liquid --min-cumvol N --categories Entertainment --side no --entry mk --rule "mid P, C"`,
N = 20,000 and 45,000, P = 3-10c and 25-50c (YES mid), C = "down 3c+ in 7d" against "no 3c+ fall in 7d" (the two split each
price exactly, 3.51). 8 runs, 4 prices x levels. Note 25-50c reaches past the band's 35c top (the existing family's band).

| Level | Rule | Bets (events) | Per bet | Losing events in / out | Tail test in / out | Replay 1% a year in / out | Worst DD in / out |
|---|---|---|---|---|---|---|---|
| 20,000 | 3-10c, down 3c+ | 727 (404) | +4.83% | 4.9% / 5.9% | passes / passes | +4.6% / +9.0% | 3.4% / 2.4% |
| 20,000 | 3-10c, no fall | 788 (405) | +3.66% | 7.4% / 4.4% | passes / passes | +2.8% / +12.3% | 2.0% / 1.0% |
| 20,000 | 25-50c, down 3c+ | 455 (280) | +20.96% | 31.3% / 31.9% | passes / passes | +16.8% / +26.1% | 5.1% / 3.9% |
| 20,000 | 25-50c, no fall | 610 (380) | +6.30% | 40.4% / 37.2% | FAILS (45.6 vs 45.6) / FAILS (45.3 vs 44.9) | +3.8% / +18.7% | 8.7% / 10.7% |
| 45,000 | 3-10c, down 3c+ | 419 (254) | +5.49% | 3.3% / 4.1% | passes / passes | +8.6% / +6.3% | 1.7% / 1.0% |
| 45,000 | 3-10c, no fall | 418 (223) | +3.04% | 7.2% / 5.6% | passes / FAILS (12.4 vs 10.6) | +4.9% / +4.5% | 1.7% / 1.3% |
| 45,000 | 25-50c, down 3c+ | 228 (152) | +16.96% | 33.1% / 35.3% | passes / FAILS (50.8 vs 47.5; 34 events) | +13.6% / +9.2% | 3.5% / 3.0% |
| 45,000 | 25-50c, no fall | 300 (190) | +7.12% | 40.0% / 36.4% | FAILS / FAILS | +4.4% / +10.9% | 7.4% / 4.0% |

- **At 3-10c the fall matters little**: both halves earn (+4.8% against +3.7% a bet at 20,000) and both pass the tail test at
  20,000; the no-fall bets are not the losers, so the cheap end of the band is not carried by the fall.
- **At 25-50c the fall is most of the money**: after a 3c+ fall NO earns +21.0% a bet at 20,000 (every year 2024-26 between
  +17.6% and +22.6%), passes both halves, replay 1% +16.8% / +26.1% a year, worst drawdown 5.1%; without a fall +6.3% and the
  tail test fails in both halves. At 45,000 the fall version passes in sample but fails out of sample on only 34 events.
- Caveats: this price window was chosen after 3.47/3.51 showed the fall effect, 25-50c is not the band's price range, and the
  family has tried many price x momentum cells (6 prices x 3 windows x 2 signs, plus the no-fall complements); no t above 3 is
  claimed. Capacity: dollars traded in the 7 days before entry, median $6,200 (20,000) / $13,150 (45,000), the largest of the
  band's prices; the losing rate is a third of events, so it is not a lopsided bet and drawdowns come from clusters of losses.
- Verdict: a LEAD, no account yet. Item 33 added: the 25-50c fall rule at 5,000 and with the 35-50c part alone (outside the
  band), and a pre-stated check of 1d/3d windows, before any paper account.
- Forward: main $1,005.72, 1 settled (+$8.57); a cycle has been running since 12:58 am. 23 variant accounts, 1 settled (main);
  controls control_fade -$26.64, control_coinflip -$34.16. 11 rule accounts, 0 settled (rule_ent_band -$3.07 against
  control_ent_quiet -$2.06; rule_ent_band_20k -$2.09; rule_5c_busy -$0.33 against control_5c_quiet $0.00; rule_ent_fall +$1.67).
  Shadow logs: resting fills 12 of 17 (busy 5-cent) and 14 of 14 (Entertainment band) decided.

## 3.54 Ideas queue 32: does the NO price in Entertainment band markets drift up over a market's life? (4:30 am CST, Nov 23)

`research/no_drift.py --categories Entertainment --min-cumvol N` (new, + 1 test), N = 5,000 / 20,000 / 45,000. Every quoted bar
with YES mid 5-35c is an observation; drift over the next 1 / 3 / 7 daily bars is the change of the NO mid, "settle" is
mid - outcome (the NO side's gain to settlement, before fees and spread). Each event counts once (its bars averaged), t over
events; grouped by days to the scheduled end and by share of the market's life gone (both known at the bar). Cents of NO price.

| Level | Half | Next 1 bar | Next 3 bars | Next 7 bars | To settlement | Events |
|---|---|---|---|---|---|---|
| 5,000 | in / out | -0.55c (t -1.9) / -1.45c (t -2.6) | -1.06c / -2.85c (t -3.0) | -0.56c / -2.85c | +2.63c (t 3.1) / -0.10c | 1,113 / 514 |
| 20,000 | in / out | -1.87c (t -3.2) / -0.05c | -1.08c / -2.98c (t -1.7) | +0.07c / +0.49c | +2.30c (t 1.8) / +2.95c (t 1.7) | 556 / 234 |
| 45,000 | in / out | -2.33c (t -2.5) / -0.52c | -1.97c / -0.65c | +1.71c / +2.43c | +0.85c / +8.62c (t 5.3) | 332 / 127 |

- **No general upward drift.** Over the next 1-7 days the band's NO price, if anything, gets CHEAPER (YES bounces back), most in
  the 0-7 day markets (next 3 bars -1.5c to -7.6c, t -1.3 to -2.2); only the 45,000 level's 7-30d and 30+d bars drift up a little
  (+0.6c to +6.0c, mixed t). By share of life gone nothing is consistent across halves and levels.
- The band's money arrives AT SETTLEMENT (the "to settlement" column), not as a price drift a holder could sell into; this agrees
  with 3.28 / 3.36 / 3.48 (holding beats every early exit). The 1.4-2.7c rise between early and late bets in 3.52 is a selection of
  markets that went on to get busy, not a general drift.
- At 5,000 the out-of-sample settlement gain is about zero (-0.10c), echoing 3.46 (the 5,000 band weakens on the full download);
  20,000 and 45,000 keep it.
- Caveats: per-bar observations overlap (one event contributes many bars, averaged once), daily bars, before fees; 3 levels x
  4 horizons x 7 groups x 2 halves read, so single cells with |t| near 2 are noise. Verdict: FAILS as a drift signal; no account
  change. Item 34 added (does waiting a bar or resting a cent lower in the band's 0-7 day markets buy NO cheaper without losing fills?).
- Forward: main $1,005.99, 1 settled (+$8.57); a cycle has been running since 3:31 am. 23 variant accounts, 1 settled (main);
  controls control_fade -$31.07, control_coinflip -$39.89. 11 rule accounts, 0 settled (rule_ent_band -$3.31 against
  control_ent_quiet -$2.17; rule_ent_band_20k -$2.43; rule_5c_busy -$1.05 against control_5c_quiet $0.00; rule_ent_fall +$1.56).
  Shadow logs: resting fills 12 of 17 (busy 5-cent) and 14 of 14 (Entertainment band) decided.

## 3.55 Ideas queue 33: the 25-50c fall lead split at 35c, at three levels and three windows (9:40 am CST, Nov 23)

Pre-stated in item 33 before the runs: the 35-50c part alone (outside the band) against 25-35c, at 5,000 / 20,000 / 45,000, and
the 1d / 3d windows at 20,000; a paper account if the 35-50c fall part passes both halves at 20,000. New rule names "mid 25-35c" and
"mid 35-50c" with "down 3c+ in kd" / "no 3c+ fall in kd" in `research/families.py` (added, + 1 test: the two split 25-50c exactly).
`research/analyze_rule.py --sample liquid --min-cumvol N --categories Entertainment --side no --entry mk`. 11 runs this round.

| Level | Rule | Bets (events) | Per bet | Losing events in / out | Tail test in / out (bound vs break-even out) | Replay 1% a year in / out | Worst DD in / out |
|---|---|---|---|---|---|---|---|
| 20,000 | 35-50c, down 3c+ 7d | 291 (214) | +22.87% | 33.3% / 36.7% | passes / passes (49.5 vs 50.2) | +11.9% / +16.3% | 5.9% / 4.3% |
| 20,000 | 35-50c, no fall 7d | 403 (273) | +10.51% | 39.0% / 39.8% | passes / passes (49.4 vs 49.6) | +5.8% / +16.0% | 7.9% / 6.0% |
| 20,000 | 25-35c, down 3c+ 7d | 301 (209) | +17.31% | 22.3% / 32.8% | passes / passes (44.0 vs 44.2) | +20.9% / +11.6% | 2.8% / 2.5% |
| 20,000 | 25-35c, no fall 7d | 369 (257) | +5.33% | 34.2% / 31.5% | passes / FAILS (41.6 vs 35.2) | +5.6% / +2.9% | 5.3% / 7.1% |
| 20,000 | 25-50c, down 3c+ 1d | 555 (342) | +15.02% | 35.1% / 36.1% | passes / passes | +25.9% / +25.7% | 8.1% / 8.0% |
| 20,000 | 25-50c, down 3c+ 3d | 524 (325) | +18.68% | 31.9% / 34.4% | passes / passes | +16.6% / +26.0% | 6.4% / 5.8% |
| 5,000 | 25-50c, down 3c+ 7d | 1,007 (562) | +16.83% | 35.9% / 36.1% | passes / passes | +23.7% / +32.5% | 8.4% / 10.3% |
| 5,000 | 35-50c, down 3c+ 7d | 649 (421) | +21.19% | 37.5% / 38.9% | passes / passes | +21.3% / +28.4% | 5.8% / 7.3% |
| 5,000 | 25-35c, down 3c+ 7d | 685 (435) | +14.20% | 28.0% / 34.9% | passes / passes | +28.7% / +16.0% | 5.1% / 8.0% |
| 45,000 | 35-50c, down 3c+ 7d | 133 (103) | +21.85% | 33.7% / 50.0% | passes / FAILS (20 events) | +11.2% / +5.7% | 2.8% / 4.3% |
| 45,000 | 25-35c, down 3c+ 7d | 159 (117) | +13.12% | 26.1% / 31.0% | passes / FAILS (29 events) | +8.2% / +5.6% | 4.5% / 2.0% |

- **The fall lead holds on both halves of the price window and at 5,000 and 20,000**, and with 1-day and 3-day windows too; the
  35-50c part earns the most a bet (+22.9% at 20,000, every year 2024-26 at +21% to +23%). At 45,000 every version fails out of
  sample, on 20-29 events: too few to tell.
- **New and not pre-stated: 35-50c NO earns WITHOUT a fall too** (+10.5% a bet, passes both halves at 20,000, by 0.2 pt out of
  sample), while 25-35c without a fall fails out of sample. So above 35c part of the money is plain calibration (Entertainment YES at
  35-50c overpriced), not the fall; the fall roughly doubles it.
- Caveats: the window was chosen after 3.47 / 3.51 / 3.53 showed the fall effect, the momentum family now has many cells (prices x
  3 windows x 2 signs plus complements), and both 20,000 out-of-sample passes are by under 1 pt; no t above 3 is claimed. Losing
  rate is a third of events, not a lopsided bet: drawdowns come from clusters. Capacity at 20,000: dollars traded in the 7 days
  before entry, median $6,750 (35-50c fall), 25th percentile $3,370; at 5,000 the median falls to $2,200 and a fifth of entry days
  trade under 100 contracts.
- Verdict: the pre-stated test passed, so a NEW paper account `rule_ent_fall_35_50` (rules.yaml: Entertainment, YES mid 35-49.5c,
  3c+ fall in 7 days, 20,000+ contracts, resting, 1%; + 1 test, 486 pass). It does not overlap rule_ent_band / rule_ent_fall (5-35c).
  Item 35 added (Entertainment 35-50c NO as a calibration rule, without the fall condition).
- Forward: main $1,004.14, 1 settled (+$8.57); a cycle has been running since 8:39 am. 23 variant accounts, 1 settled (main);
  controls control_fade -$31.63, control_coinflip -$47.64. 12 rule accounts (one not started), 0 settled (rule_ent_band -$3.24
  against control_ent_quiet -$2.06; rule_ent_band_20k -$2.58; rule_5c_busy -$0.84 against control_5c_quiet $0.00; rule_ent_fall
  +$0.81; rule_ent_band_taker -$17.13). Shadow logs: resting fills 12 of 18 (busy 5-cent) and 14 of 14 (Entertainment band) decided.

## 3.56 Ideas queue 34: entry delay in the Entertainment band's 0-7 day markets (12:15 pm CST, Nov 23)

Question (from 3.54: the band's NO gets 1.5-7.6c cheaper over the next 3 bars in 0-7 day markets): does resting the NO bid a cent
or two lower, or one or three bars later, buy NO cheaper without losing the fills that pay? `research/entry_delay.py` (new, + 1 test,
487 pass). Same placements for every variant: the band rule ("NO where YES is at 5-35c", Entertainment, liquid sample) at its first
bar per market inside 0-7 days to the scheduled end. "-k c": NO bid k cents lower, filled only if a later bar's YES bid reached
that level or a trade printed above it within 3 bars. "+d bars": committed at the placement bar, resting at the bar d bars later
at its own price. "Per order" counts unfilled orders as zero, the fair comparison. 5 variants x 2 levels, plus the whole band at
20,000 for reference: 15 runs read.

| Level | Variant | Fill in / out | Per bet in / out | Per order in / out | Tail test in / out |
|---|---|---|---|---|---|
| 20,000 (939 placements, 479 events) | base | 84% / 86% | +7.87% / +3.03% | +6.60% / +2.61% | passes / FAILS (28.8 vs 26.8) |
| | -1c | 74% / 80% | +7.49% / +3.13% | +5.53% / +2.49% | passes / FAILS |
| | -2c | 68% / 76% | +8.04% / +3.63% | +5.50% / +2.75% | passes / FAILS |
| | +1 bar | 60% / 61% | +5.17% / +1.51% | +3.12% / +0.92% | passes / FAILS |
| | +3 bars | 34% / 20% | +4.88% / -2.72% | +1.65% / -0.55% | FAILS / FAILS |
| 45,000 (490 placements, 265 events) | base | 84% / 86% | +6.90% / +6.26% | +5.79% / +5.39% | passes / passes (24.6 vs 25.9) |
| | -1c | 73% / 79% | +6.10% / +6.59% | +4.45% / +5.21% | passes / passes |
| | -2c | 67% / 77% | +6.71% / +7.56% | +4.49% / +5.82% | passes / passes |
| | +1 bar | 59% / 54% | +4.88% / +1.79% | +2.88% / +0.96% | FAILS / FAILS |
| | +3 bars | 30% / 15% | -4.79% / -20.63% | -1.45% / -3.03% | FAILS / FAILS |
| 20,000, all days (reference) | base / -2c / +3 bars per order | | | +6.12% / +5.65% / +4.02% in; +5.43% / +5.09% / +2.92% out | all pass |

- **FAILS: the first-bar bid stays.** Waiting a bar loses a third of the fills and roughly half the money per order at both levels;
  waiting three bars loses money in the short-dated markets. The NO price that "gets cheaper" in 3.54 gets cheaper in the markets
  where YES then rises, i.e. the bets that lose: a lower or later bid fills more of those and fewer of the winners (adverse
  selection), so the cheaper price does not pay.
- A bid 1-2c lower keeps per-bet returns about level (better in 2 of 4 cells) but fills 8-17 points less, so per order it earns
  less in 3 of 4 cells; the one better cell (-2c out of sample at 45,000, +5.82% vs +5.39%) is inside the noise of 15 runs on 80 events.
- Side finding, consistent with 3.41: the band's 0-7 day slice at 20,000 fails the tail test out of sample (+3.0% a bet); at 45,000 it
  passes. No account change (rule_ent_band_20k trades all days, where the band passes both halves).
- Forward: main $1,004.14, 1 settled (+$8.57); a cycle has been running since 11:13 am. 23 variant accounts, 1 settled (main); controls
  control_fade -$32.02, control_coinflip -$52.76. 12 rule accounts: rule_5c_busy -$10.64 with its first settled bet LOST (and the
  same market lost in rule_5c_busy_taker and rule_5c_busy_claude), against control_5c_quiet -$0.31; rule_ent_band -$3.41 against
  control_ent_quiet -$2.06; one settled bet is far too few to read. Shadow logs: resting fills 13 of 19 (busy 5-cent, 68%) and 14 of 14
  (Entertainment band) decided.

## 3.57 Ideas queue 35: Entertainment 35-50c NO as a plain calibration rule, without the fall condition (12:20 am CST, Nov 24)

Pre-stated in item 35: the existing calibration rule "mid 35-50c" (family 1), Entertainment, NO, resting (mk) and taker (tk), at
5,000 / 20,000 / 45,000 contracts, with "mid 50-65c" beside it. `research/analyze_rule.py --sample liquid --min-cumvol N
--categories Entertainment --side no --entry mk|tk`. 12 runs this round.

| Level | Rule | Entry | Bets (events) | Per bet | Tail test in / out (bound vs break-even out) | Replay 1% a year in / out | Worst DD in / out |
|---|---|---|---|---|---|---|---|
| 5,000 | 35-50c | mk | 1,378 (742) | +8.86% | passes / FAILS (51.9 vs 48.0) | +12.8% / -2.5% | 13.6% / 20.0% |
| 5,000 | 35-50c | tk | 1,523 (785) | +3.64% | passes / FAILS (51.8 vs 44.4) | +5.8% / -12.8% | 17.1% / 25.0% |
| 20,000 | 35-50c | mk | 563 (341) | +16.28% | passes / passes (47.4 vs 54.8) | +12.6% / +33.4% | 9.0% / 7.3% |
| 20,000 | 35-50c | tk | 600 (353) | +9.65% | passes / passes (47.6 vs 50.3) | +6.7% / +19.0% | 10.6% / 8.1% |
| 45,000 | 35-50c | mk | 267 (175) | +13.22% | passes / FAILS (63.5 vs 59.6, 42 events) | +12.3% / +10.0% | 6.2% / 3.3% |
| 45,000 | 35-50c | tk | 285 (184) | +7.01% | FAILS / FAILS | +6.9% / +4.2% | 8.1% / 4.2% |
| 5,000 | 50-65c | mk | 1,329 (781) | +11.53% | passes / FAILS (61.3 vs 55.1) | +24.7% / -8.0% | 22.1% / 34.5% |
| 5,000 | 50-65c | tk | 1,423 (822) | +3.16% | passes / FAILS | +8.9% / -14.2% | 22.3% / 36.5% |
| 20,000 | 50-65c | mk | 573 (375) | +12.26% | passes / FAILS (65.5 vs 58.4) | +12.1% / -2.9% | 13.0% / 17.0% |
| 20,000 | 50-65c | tk | 598 (386) | +3.32% | FAILS / FAILS | +3.6% / -11.5% | 18.3% / 19.6% |
| 45,000 | 50-65c | mk | 254 (177) | +9.84% | passes / FAILS | +7.0% / -9.8% | 7.4% / 14.4% |
| 45,000 | 50-65c | tk | 269 (187) | +1.48% | FAILS / FAILS | +4.1% / -15.0% | 7.3% / 19.2% |

- **50-65c NO fails out of sample at every level and both entries** (losing 56-66% of events after 2026-04-01, replay negative): no
  plain overpricing of Entertainment favourites-to-be at 50-65c. Closed.
- **35-50c NO passes both halves at 20,000 only** (resting +16.3% a bet, steady by year: 2024 +19.8%, 2025 +16.8%, 2026 +15.7%;
  taking +9.7% also passes). At 5,000 it fails out of sample with a losing replay (-2.5% a year, drawdown 20%), and at 45,000 it fails
  on 42 events. One level of three is not a robust calibration effect: the 20,000 pass looks like what 3.55 already found (the fall
  subset, now its own paper account rule_ent_fall_35_50, plus a no-fall part that passed by 0.2 pt), not a separate rule.
- Capacity at 20,000 (resting 35-50c): dollars traded in the 7 days before entry, median $8,190, 25th percentile $4,460; 7% of entry
  days under 100 contracts.
- Verdict: FAILS the robustness bar. No new paper account (it would mostly duplicate rule_ent_fall_35_50). Item 37 added: is the
  5,000 failure the quiet 5,000-20,000 layer (`--max-cumvol 20000`), as with the band (3.50)?
- Forward (nothing new settled): main $1,003.83, 1 settled (+$8.57); 23 variant accounts, controls control_fade -$32.43, control_coinflip
  -$51.95. 12 rule accounts, rule_5c_busy -$10.74 (1 settled, lost) against control_5c_quiet -$0.20; rule_ent_band -$3.77 against
  control_ent_quiet -$2.06. Shadow logs: resting fills 13 of 20 (busy 5-cent, 65%) and 14 of 14 (Entertainment band) decided.
  The PC was powered off and restarted several times between 9:00 and 9:55 pm Nov 23; the 9:22 pm cycle was cut off (left
  "running" in the ledger, no orders logged); the loop came back at 9:57 pm and a cycle has been running since 11:57 pm.

## 3.58 Ideas queue 36: is a slow resting fill a warning sign? (3:25 am CST, Nov 24)

Question (from 3.56, where lower or later bids filled more of the losers): in the Entertainment band ("NO where YES is at 5-35c",
resting NO at 1 - ask for 3 bars, first bar per market, all days to close), split the placements by the bar on which the order
filled, and price the orders that never filled as a taker would. `research/fill_speed.py` (new, + 1 test, 488 pass). 2 levels x 2
halves x 5 cells: 20 cells read, none pre-registered as a pass.

| Level, half | Placed | Fill bar 1 / bar 2-3 / never | Bar 1 per bet | Bar 2-3 per bet | Never, taker at next open | Never, taker after window | Per order: cancel after bar 1 / rest 3 bars |
|---|---|---|---|---|---|---|---|
| 20,000 in | 1,163 | 65% / 11% / 25% | +8.23% passes | +7.54% passes | +6.32% passes | +0.26% FAILS | +5.32% / +6.12% |
| 20,000 out | 560 | 79% / 5% / 16% | +5.86% passes | +16.44% (25 events) FAILS | +12.04% passes | +6.26% FAILS | +4.61% / +5.43% |
| 45,000 in | 644 | 66% / 10% / 23% | +5.73% passes | +8.81% FAILS | +5.46% passes | +0.20% FAILS | +3.81% / +4.72% |
| 45,000 out | 271 | 77% / 4% / 19% | +8.19% passes | +26.68% (10 events) FAILS | +14.29% passes | +11.82% FAILS | +6.29% / +7.47% |

- **FAILS as a warning sign: a slow fill is not a loser in the whole band.** Bar 2-3 fills earn as much or more a bet than bar-1
  fills in all four cells (their tail tests fail only for size: 10-98 events). Cancelling an order that has not filled after one
  bar earns about 0.8-1.2 points less per order at both levels and in both halves. The 3-bar resting order stays as it is.
  The adverse selection of 3.56 belongs to bids placed lower or later in the short-dated markets, not to the standard bid.
- **The never-filled markets are winners too** (+5.5% to +14.3% a bet bought at the next open, passing the tail test), but that is
  hindsight: one only knows an order never filled 3 bars later, and buying then (taker after the window) fails the tail test in
  all four cells (+0.2% in sample). No taker fallback; no account change.

## 3.59 Ideas queue 37: is the 5,000 failure of Entertainment 35-50c NO the quiet layer? (6:25 am CST, Nov 24)

Pre-stated in item 37: `research/analyze_rule.py --sample liquid --min-cumvol 5000 --max-cumvol 20000 --categories Entertainment
--side no --entry mk`, for "mid 35-50c" and its 7-day fall / no-fall cells (3.55). Three runs, resting only.

| rule (5,000-20,000 layer) | bets (events) | per bet | tail test in / out | replay 1% in / out | worst DD in / out |
|---|---|---|---|---|---|
| mid 35-50c | 1,378 (742) | +8.86% | passes / FAILS (51.9 vs 48.0) | +12.8% / -2.5% a year | 13.6% / 20.0% |
| 35-50c, down 3c+ in 7d | 649 (421) | +21.19% | passes / passes (47.1 vs 52.2) | +21.3% / +28.4% a year | 5.8% / 7.3% |
| 35-50c, no 3c+ fall in 7d | 1,116 (664) | +6.47% | passes / FAILS (55.2 vs 47.9) | +7.9% / -9.0% a year | 16.0% / 19.9% |

- **The question cannot be split this way: cut by volume at entry, the layer IS the whole 5,000 account.** Every figure is
  identical to the 5,000 rows of 3.57 and 3.55: a market's first eligible bar comes before it reaches 20,000 contracts, so the
  bet is always placed in the layer (as with the band in 3.50).
- **What the runs do show: the 5,000 failure is the no-fall bets.** With the fall, 35-50c NO passes both halves at 5,000 too
  (+21% a bet, out-of-sample replay +28%/y, drawdown 7.3%); without it, it loses out of sample (-9%/y). The plain rule's
  failure comes from its no-fall bets (the two cells overlap: a market can enter each at a different bar).
- Capacity (plain rule): entry-day dollars traded in the 7 days before, median $1,351, 25th percentile $594.
- No account change: rule_ent_fall_35_50 (20,000+) already trades the fall cell; nothing here argues for a plain 35-50c account.

## 3.60 Ideas queue 38: is a slow resting fill a warning sign in the 0-7 day Entertainment band markets? (9:20 am CST, Nov 24)

Pre-stated in item 38: report 3.58's fill-speed split (all days) re-read on the band's 0-7 day markets only, where 3.56 found
adverse selection. `research/fill_speed.py --categories Entertainment --min-cumvol N --dte-hi 7` (new `--dte-lo/--dte-hi`
options, `in_window` + 1 test; 489 pass). Rule "NO where YES is at 5-35c", resting at 1 - ask for 3 bars. Data: 5,802 markets
at 20,000 (1,570 events), 3,178 at 45,000 (942 events), closes to 2026-09-18. Two runs.

| level, half | placed | bar 1 / 2-3 / never | bar-1 fills per bet | bar 2-3 fills per bet | never, taker late | per order: cancel after bar 1 / rest 3 bars |
|---|---|---|---|---|---|---|
| 20,000 in | 620 | 77% / 7% / 16% | +8.11% (passes) | +5.26% (n 43, fails) | -3.02% (n 40) | +6.24% / +6.60% |
| 20,000 out | 319 | 84% / 2% / 14% | +2.59% (FAILS, 29.4% vs 26.6%) | +19.89% (n 7) | +1.92% (n 6) | +2.18% / +2.61% |
| 45,000 in | 347 | 78% / 6% / 16% | +6.61% (passes) | +10.70% (n 21) | +1.35% (n 19) | +5.14% / +5.79% |
| 45,000 out | 143 | 86% / 0% / 14% | +6.26% (passes) | none | n 1 | +5.39% / +5.39% |

- **FAILS as a signal, as in 3.58.** In the short-dated markets almost every fill comes on bar 1 (77-86%); the bar 2-3 fills are
  few (0-43) and do not earn less in three of four cells. Cancelling after one bar never earns more per order (0 to -0.4 pt).
  The 3-bar resting order stays.
- Never-filled markets win for NO (+8-15% a bet at the next open, 0-4% losing), but that is known only after the window: the
  order that did not fill is the one where YES fell away from it. Crossing after the window (taker late) earns -3.0% / +1.4% in
  sample and fails. Not tradeable.
- Worth noting: at 20,000 the bar-1 fills in 0-7 day markets fail out of sample (+2.6% a bet), in line with 3.41 (0-7d is the band's
  weakest slice). At 45,000 they pass.
- Variants: 2 levels x 2 halves, one pre-stated window. No account change.

## 3.61 Ideas queue 40: the 20,000 Entertainment band without its 0-7 day markets (12:15 pm CST, Nov 24)

Pre-stated in item 40: would leaving out the 0-7 day markets (one variant: enter at the first bar with 7+ days to the
scheduled close) have lifted rule_ent_band_20k's out-of-sample account replay? 3.41's split re-run with a 45,000 cut beside it.
`research/band_by_dte.py 20000` and `45000` (new 7-10000 slice). Rule "NO where YES is at 5-35c", resting. Data: 5,802 markets
at 20,000 (1,570 events), 3,178 at 45,000 (942 events), closes to 2026-09-18.

| level, slice | bets / events | per bet | tail test out of sample (loss rate, bound vs break-even) | replay at 1%, in / out of sample |
|---|---|---|---|---|
| 20,000 all | 1,526 / 691 | +7.39% | 21.4%, 26.4 < 33.8 pass | +9.1%/y DD 6.5% / +33.0%/y DD 6.6% |
| 20,000 0-7 d | 831 / 442 | +6.15% | 22.2%, 28.5 > 26.9 FAIL | +14.5%/y DD 6.6% / +20.2%/y DD 7.8% |
| 20,000 7+ d (the variant) | 888 / 391 | +8.18% | 19.0%, 26.6 < 40.6 pass | +5.7%/y DD 3.4% / +22.3%/y DD 2.7% |
| 45,000 all | 815 / 402 | +7.14% | 15.7%, 22.2 < 35.9 pass | +9.9%/y DD 8.1% / +25.5%/y DD 2.3% |
| 45,000 0-7 d | 433 / 250 | +6.97% | 16.3%, 24.6 < 26.3 pass | +6.4%/y DD 6.6% / +16.3%/y DD 3.3% |
| 45,000 7+ d | 465 / 215 | +7.59% | 14.8%, 25.2 < 44.6 pass | +8.6%/y DD 3.5% / +16.1%/y DD 1.6% |

- **FAILS as pre-stated.** Without its 0-7 day markets the 20,000 band earns more per bet (+8.18% against +7.39%) and passes
  the tail test with more room, but the account replay earns LESS a year in both halves (+5.7% against +9.1% in sample, +22.3%
  against +33.0% out of sample at 1%). The short-dated markets turn capital fastest (median hold 3.4 days against 18.4) and are
  the deepest (median 13,151 contracts on the entry day against 2,048), so they add return per year even with the thinner
  per-bet edge. What the exclusion buys is a smaller drawdown (2.7% against 6.6% out of sample).
- At 45,000 the 0-7 day slice passes the tail test out of sample (by a small margin, 24.6 < 26.3), as in 3.60.
- Verdict: rule_ent_band_20k stays as it is. No new account. The 0-7 day slice at 20,000 is the band's weak point (it fails the
  tail test out of sample); item 41 tests a mixed cut that keeps 0-7 day markets only at 45,000.
- Variants: 1 pre-stated (7+ d at 20,000), plus the 45,000 cut for comparison. 489 tests unchanged (slice added to a script).
- Forward: nothing new has settled in the rule accounts (rule_5c_busy 1 bet, lost; the rest 0); main $1,009.26, 2 settled (both
  profitable, +$15.60), 3 open, 5 resting; the 11:08 am cycle ended ok (8 forecasts).

## 3.62 Ideas queue 41: a mixed cut for the Entertainment band, 0-7 day markets only at 45,000 (3:25 pm CST, Nov 24)

Pre-stated in item 41: one variant, "NO where YES is at 5-35c", Entertainment, resting; bars with 7+ days to the scheduled
close at 20,000 contracts traded, bars closer than 7 days only once the market has traded 45,000 (both known at the bar; the
first qualifying bar per market is the bet). Passes if its out-of-sample replay at 1% beats rule_ent_band_20k's (+33.0%/y)
with no larger drawdown and it passes the tail test in both halves. `research/band_by_dte.py 20000 ent --mixed` (new helper
`analyze_rule.near_close_cumvol`, + 1 test). Data unchanged from 3.61: 5,802 markets at 20,000 (1,570 events), closes to
2026-09-18.

| cut | bets / events | per bet | tail test in / out of sample (bound vs break-even) | replay at 1%, in / out of sample |
|---|---|---|---|---|
| 20,000 all (rule_ent_band_20k) | 1,526 / 691 | +7.39% | 25.7 < 35.3 pass / 26.4 < 33.8 pass | +9.1%/y DD 6.5% / +33.0%/y DD 6.6% |
| 20,000 7+ d only (3.61) | 888 / 391 | +8.18% | 26.1 < 35.0 pass / 26.6 < 40.6 pass | +5.7%/y DD 3.4% / +22.3%/y DD 2.7% |
| mixed (the variant) | 1,172 / 521 | +7.91% | 27.1 < 36.4 pass / 24.8 < 37.7 pass | +6.1%/y DD 4.8% / +31.0%/y DD 3.3% |

- **FAILS as pre-stated, narrowly.** The mixed cut passes the tail test in both halves with more room than the 20,000 band
  out of sample (loss rate 18.8% against 21.4%) and halves the out-of-sample drawdown (3.3% against 6.6%), but its replay
  earns less a year in both halves (+31.0% against +33.0% out of sample, +6.1% against +9.1% in sample). At 0.5% it is
  +17.8%/y DD 1.6% against +19.3%/y DD 3.2%; at 2% +27.3%/y DD 9.3% against +19.0%/y DD 12.9%.
- Reading: the 0-7 day markets under 45,000 contracts carry return per year even though they fail the tail test on their
  own (3.60, 3.61); leaving them out trades about a tenth of the yearly return in sample and out for half the drawdown.
  Under the rules the 20,000 account stays as it is. No new account.
- Capacity: median 3,766 contracts on the entry day (25th percentile 916), $2,896 traded in the 7 days before; 9% of entry
  days under 100 contracts. Median hold 10.7 days.
- Variants: 1 pre-stated. 490 tests pass. Forward: nothing new has settled in the rule accounts (rule_5c_busy 1 bet, lost);
  main $1,009.26, 2 settled (+$15.60), 3 open, 5 resting; the 12:39 pm cycle ended ok. Item 42 added (forward check of the
  same split once rule_ent_band_20k has settled bets).

## 3.63 Ideas queue 29: the 5-cent rule's stops on hourly bars (6:35 pm CST, Nov 24)

The same test as 3.48, on the 5-cent rule ("NO at mid <= 5c, <= 30d, spread <= 5c", resting) in busy markets (45,000
contracts traded) of the nine categories: 8,893 markets, 3,202 events, closes to 2026-09-18; 790 bets in sample, 398 out.
`research/hourly_bars.py` fetched the last 48 hours of 60-minute bars for all 1,188 markets the rule bets on (1,173 with
bars); `research/exit_study.py --tag nine_liquid_45000_hourly --hourly data\kalshi_hourly.db` against the same run on daily
bars only (`--tag nine_liquid_45000_daily`). Same 25 policies as 3.28; 418 stop sales moved to an hourly bar.

| stop policy | in/bet daily -> hourly | out/bet daily -> hourly | out 1% replay a year | out tail test | stopped out (out) |
|---|---|---|---|---|---|
| -5 points | +1.30% -> +0.87% | +1.01% -> +0.18% | +6.8% -> +0.6% | passes -> FAILS | 9.8% -> 14.8% |
| -10 points | +1.61% -> +1.34% | +1.73% -> +1.00% | +11.3% -> +6.1% | passes -> passes | 4.3% -> 7.5% |
| -20 points | +1.56% -> +1.62% | +2.00% -> +0.98% | +13.5% -> +6.3% | passes -> FAILS | 2.3% -> 4.8% |
| our mid <= 0.90 | +1.37% -> +0.97% | +1.12% -> +0.52% | +7.7% -> +3.1% | passes -> FAILS | 8.8% -> 12.1% |
| our mid <= 0.85 | +1.57% -> +1.36% | +1.69% -> +1.05% | +11.0% -> +6.5% | passes -> passes | 4.3% -> 7.0% |
| our mid <= 0.75 | +1.57% -> +1.61% | +1.97% -> +1.09% | +13.2% -> +7.1% | passes -> FAILS | 2.3% -> 4.3% |
| hold to settlement (no stop) | +1.83% | +2.55% (t 4.72) | +18.1%, worst drawdown 1.55% | passes (4 losing events) | - |

- **Every stop gets worse on hourly bars out of sample**, as in the Entertainment band (3.48): stops fire about one and a
  half to two times as often, sell near an intraday low, and the bet then settles as a win. Four of the six stops now fail
  the tail test out of sample. Holding to settlement stays the policy for rule_5c_busy; no verdict of 3.28 changes.
- The in-sample pick moves from "take 0.99 resting + stop -10" (daily; +10.6%/y out of sample) to "take at bid >= 0.98,
  resting" (hourly; +16.6%/y out of sample, drawdown 1.35%) because its stop leg got worse; both trail hold (+18.1%/y).
  Take-profits are still tested on daily bars only (item 43). 25 policies x 2 bar types tried; no t above 3 is claimed for
  any exit.
- Caveat as in 3.48: hourly bars cover the last 48 hours only, so earlier stops are still daily; that can only add stop-outs.
- Capacity is unchanged from 3.28 (same bets). Data: `research/results/exit_nine_liquid_45000_{daily,hourly}.csv`.
- Forward: nothing new has settled in the rule accounts (rule_5c_busy 1 bet, lost); main $1,009.78, 2 settled (+$15.60),
  3 open, 5 resting; the 4:42 pm cycle ended ok.

## 3.64 The paper fill rate against the backtest's: a measurement mismatch, not a generous fill model (7:35 pm CST, Nov 24)

The question (raised with the user at 10:25 am and 6:55 pm Nov 24): the Entertainment band's observation log
(`data\shadow_ent.db`, a hypothetical $20 resting NO bid at the best bid on each qualifying market, left three days)
filled 95 of 194 decided orders, 49%, while its report said "the backtest's model fills about 69% to 80%". If the
backtest's resting fills were too generous, every resting rule's figures would be too good. New tool:
`research/fill_audit.py` (+5 tests); `research/panel.py` gets a second fill model, `panel.set_fill("trade")` (+1 test),
and `analyze_rule.py --fill trade`.

1. **The log measured what it says.** Re-deciding all 216 decided orders of both logs from each market's full public
   trade record (one request each; no window came near the 5,000-trade cap of the log's own check) gives exactly what
   was logged: Entertainment 95 of 194 (49%), the 5-cent log 14 of 22 (64%). A wider "through" rule, which also counts
   a NO buyer trading at or above the order's price (the level must have been cleared), adds no fill at all.
2. **The backtest's fill rule is not what is generous.** Its resting NO bid fills when a later daily bar's YES bid
   reaches the order's price OR a trade prints above it. Counting only the print ("trade" model): the band at 20,000
   goes from 1,526 to 1,513 bets, +7.39% to +7.31% a bet, both halves still pass the tail test (upper bounds unchanged:
   25.7% / 26.4% against break-even 35.1% / 33.6%), 1% replay out of sample +33.0%/y to +34.7%/y, drawdown 6.6% to 6.5%.
3. **The 69-80% was the wrong comparison.** The backtest bets on each market's first bar on which the rule held AND
   the order filled, so an unfilled order is placed again on the next qualifying bar (the paper rule accounts do the
   same). Its "fill rate" was the share of markets whose FIRST qualifying bar filled. The log places one order per
   market at whatever moment it first saw the market, mostly well into its time in the band. The backtest's rate for
   an order placed on ANY qualifying bar is the like-for-like figure:

| rule, level, fill model | markets | first qualifying bar | any qualifying bar | filled on some bar | the log |
|---|---|---|---|---|---|
| Entertainment band, 5,000, quote | 3,932 | 70% | **51%** (53,458 bars) | 88% | **49%** (194) |
| Entertainment band, 5,000, trade | 3,932 | 68% | 50% | 87% | |
| Entertainment band, 20,000, quote | 1,723 | 78% | 62% (20,312 bars) | 89% | |
| Entertainment band, 20,000, trade | 1,723 | 77% | 61% | 88% | |
| 5-cent rule, Economics + Politics, 45,000, quote | 921 | 61% | **50%** (7,795 bars) | 80% | **64%** (22) |
| 5-cent rule, same, trade | 921 | 59% | 48% | 79% | |

- **Verdict: the paper fill rates agree with the backtest** (49% against 51% for the band; the 5-cent log is above its
  figure on 22 orders). Nothing in the resting results of 3.7-3.63 is inflated by the fill model; the "trade" model moves
  each figure by a point or two. The logs' reports now quote the any-bar figure with the first-bar one beside it.
- What this does NOT settle: whether the fills that happen are the bad ones (adverse selection). 3.56 / 3.58 / 3.60
  found later fills earn as much a bet; the logs' filled-and-settled bets will say it forward (none settled yet).
- Queue items 51 and 62 were written on the premise that the paper fill rate is below the model; they stand as tests of
  their own, but that premise is withdrawn. No account changes. Data: `research/results/fill_audit_20261124.csv`.

## 3.65 Ideas queue 43: take-profits on hourly bars (9:15 pm CST, Nov 24)

`research/exits.py` got `Exits(..., hourly_takes=True)` (`exit_study.py --hourly-takes`): a TAKER take-profit is also
tested on each hourly bar inside the daily bar (our side's closing bid at or above the level), sold at the next hourly
open's bid with the taker fee; a stop wins over a take on the same bar; resting takes stay daily (no hourly fill model).
1 new test (517 pass). Same 25 policies, same hourly bars (last 48 hours before close) as 3.48 / 3.63. Baselines run on
the same panel with hourly stops and daily takes (the Entertainment panel has grown since 3.48: 573 in / 368 out bets,
161 out-of-sample events; one market landed between the two runs). Per bet, fees in:

| rule (resting entry, 45,000) | policy | out/bet daily take -> hourly take | out 1% replay a year (hourly) | out dd | tail both halves |
|---|---|---|---|---|---|
| Ent band | hold to settlement | +7.78% | +25.3% | 3.37% | yes |
| Ent band | take at bid >= 0.97, taker | +7.66% -> +7.08% | +26.4% | 3.89% | yes |
| Ent band | take at bid >= 0.98, taker | +7.55% -> +7.40% | +25.3% | 3.67% | yes |
| Ent band | take at +3 points, taker | +4.13% -> +1.44% | +3.7% | 7.51% | no |
| Ent band | take at +10 points, taker | +5.87% -> +4.76% | +13.5% | 7.16% | yes |
| 5-cent rule (nine) | hold to settlement | +2.55% | +18.1% | 1.55% | yes |
| 5-cent rule (nine) | take at bid >= 0.97, taker | +1.16% -> +0.50% | +3.5% | 2.00% | yes |
| 5-cent rule (nine) | take at bid >= 0.98, taker | +1.77% -> +1.26% | +9.0% | 1.59% | yes |
| 5-cent rule (nine) | take at bid >= 0.99, taker | +2.34% -> +2.31% | +16.5% | 1.55% | yes |
| 5-cent rule (nine) | take at +3 points, taker | +2.17% -> +2.05% | +14.6% | 1.44% | yes |

- **FAILS: no take-profit beats holding out of sample on hourly bars.** Moving the takes to hourly bars makes every
  taker take worse or no better, in both rules, as hourly stops did (3.48, 3.63): intraday spikes sell bets that would
  have settled at $1. The one near-miss, the band's 0.97 taker take (+26.4%/y vs +25.3%/y hold, because money comes back
  earlier), earns less a bet and has the larger drawdown (3.89% vs 3.37%): not the risk-averse choice.
- Hold to settlement stays the exit for every rule account. Variants tried: 2 rules x 8 taker take policies, one run.
- Data: `research/results/exit_{ent,nine}_liquid_45000_hourtake.csv`, baseline `exit_ent_liquid_45000_hourstop_now.csv`.

## 3.66 Ideas queue 44: is the edge decaying? Per-bet return by calendar quarter (9:20 pm CST, Nov 24)

New `research/edge_by_quarter.py` (+1 test, 518 pass): first bar per market as `analyze_rule.py`, grouped by the quarter
of the market's close; slope = OLS of each bet's return on the quarter index, standard error clustered by event.
Pre-stated: "decaying" if every out-of-sample quarter is below the in-sample mean AND the slope's t < -2. Resting entry.

| rule | data (last close) | in-sample mean / bet | 2026Q2 | 2026Q3 | 2026Q4 | slope a quarter (t) | decaying |
|---|---|---|---|---|---|---|---|
| Ent band, 20,000 | 6,685 mkts, 1,727 ev (Nov 24) | +7.58% | +8.69% (240 bets, 102 ev) | +5.57% (316, 141) | +5.69% (184, 59) | +0.29 pt (+0.59) | no |
| 5-cent rule, nine, 45,000 | 8,893 mkts (Sep 18) | +1.83% | +3.65% (233, 130) | +0.99% (165, 109) | - | -0.005 pt (-0.06) | no |
| Climate band, 5,000 | 39,080 mkts (Sep 18) | +0.71% | +1.24% (401, 262) | +2.27% (354, 223) | - | -0.03 pt (-0.08) | no |

- **No sign of decay in any of the three rules** by the pre-stated test: in each, one out-of-sample quarter is above its
  in-sample mean and no slope is near t -2. Quarterly errors are wide (2-4 points a bet for the band), so this rules out
  a steep decline, not a slow one.
- Worth watching: the band's last two quarters (+5.6%, +5.7% a bet) sit below its in-sample mean (+7.6%), within one
  standard error. 2026Q4 is the refreshed history (markets settled since Sep 21, queue item 64's data) and is still
  positive. The 5-cent rule's 2026Q3 (+1.0%) is below its mean too; its Q2 was the best quarter on record.
- The Climate band's in-sample mean is only +0.7% a bet, its 2024Q4 -7.1% (179 bets): its out-of-sample quarters are its
  best. Same caveat as 3.27 (thin edge). No account changes.

## 3.67 Ideas queue 45: stability inside the out-of-sample half (9:20 pm CST, Nov 24)

`research/edge_by_quarter.py --periods` (+1 test, 519 pass): per bet and the tail test (each event's summed return,
`analyze_rule.tail`) on bets closing Apr-Jun 2026 and Jul 2026 onward. The split is not moved. Resting entry.

| rule | period | bets | events | per bet | losing events | loss-rate bound 95% vs break-even | tail test |
|---|---|---|---|---|---|---|---|
| Ent band, 20,000 | Apr-Jun 2026 | 240 | 102 | +8.69% | 21 | 28.3% vs 37.4% | pass |
| Ent band, 20,000 | Jul-Nov 24 2026 | 500 | 195 | +5.61% | 45 | 28.6% vs 33.0% | pass |
| 5-cent rule, nine, 45,000 | Apr-Jun 2026 | 233 | 130 | +3.65% | 0 | 2.3% vs 6.2% | pass |
| 5-cent rule, nine, 45,000 | Jul-Sep 18 2026 | 165 | 109 | +0.99% | 4 | 8.2% vs 5.1% | FAIL |
| Climate band, 5,000 | Apr-Jun 2026 | 401 | 262 | +1.24% | 70 | 31.6% vs 28.3% | FAIL |
| Climate band, 5,000 | Jul-Sep 18 2026 | 354 | 223 | +2.27% | 52 | 28.5% vs 26.4% | FAIL |

- **The Entertainment band is stable**: it passes the tail test in both sub-periods on its own, with the later one
  (which includes the refreshed history to Nov 24) weaker a bet but larger.
- **The 5-cent rule is fragile by the item's own test**: its out-of-sample pass rests on Apr-Jun 2026 (no losing event
  in 130). From July it earns +0.99% a bet and 4 losing events in 109 put the bound above break-even. A lopsided rule
  with 100-odd events can fail on four losers, so this is a warning, not a verdict; item 64 (the refreshed history, to
  Nov 2026) is the real test, and the paper account rule_5c_busy (1 settled, a loss) keeps running.
- **The Climate band fails the tail test in both sub-periods and, re-checked on the current data, on each whole half**
  (in sample 188 losing of 731 events, bound 28.5% vs break-even 26.5%; out 122 of 485, 28.6% vs 27.4%). Its per-bet
  return is positive (+0.7% / +1.7%) but it does not meet rule 1 of the judging rules at 5,000 on today's data. The paper
  account rule_climate_band (+$14.74, 0 settled) is left running as a record (accounts are never changed); no setting of
  it should reach anything else. Data to Sep 18 for the nine and Climate (refresh pending).

## 3.68 Ideas queue 46: series concentration of the band and the Climate band (12:25 am CST, Nov 25)

New `research/series_concentration.py` (+1 test): per-series bets, events and return in each half, then the rule
without its top 1 and top 3 series ranked by IN-SAMPLE money (no out-of-sample hindsight in the ranking). Pre-stated:
"fragile" if dropping the top series halves the out-of-sample per-bet return. Resting entry, liquid sample.

| rule | data | series (in / out) | out per bet | without top 1 | without top 3 | tail test out, top 3 dropped | fragile |
|---|---|---|---|---|---|---|---|
| Ent band, 20,000 | 6,685 mkts, 1,727 ev, last close Nov 24 | 349 / 122 | +6.61% (740 bets, 294 ev) | +6.61% | +6.40% | pass (65 losing of 290, 26.8% vs 34.1%) | no |
| Climate band, 5,000 | last close Nov 24 | 87 / 78 | +1.83% (886 bets, 583 ev) | +1.74% | +1.70% | FAIL (as without dropping) | no |

- **The Entertainment band is not carried by a series.** Its in-sample top series are one-off events (Super Bowl
  guests, ads and performers, Time and Google lists) with no out-of-sample bets at all, so dropping them changes nothing
  out of sample. Looked at with hindsight, out of sample: the top series (KXRT, Rotten Tomatoes) holds 13% of the money,
  the top 3 25%, the top 5 35%; without the top 1 the per-bet return RISES to +7.97% (KXRT has many bets at a lower
  return), without the top 5 it is +6.43%. Broad.
- **The Climate band is concentrated.** In sample, without its top 3 series (KXHIGHAUS, KXHIGHNY, KXSNOWNYM) it earns
  -0.79% a bet. Out of sample, with hindsight, its top 5 series hold 118% of the money (the rest lose) and without them
  it earns -0.78%. It passes the pre-stated test only because the in-sample leaders are not where the out-of-sample money
  came from. Together with 3.67 (fails the tail test in both halves at 5,000) this says the Climate band has no stable
  basis on today's data; item 66 (20,000 / 45,000) and item 54 (by series group) are the remaining checks.
  rule_climate_band keeps running as a record; no setting of it goes anywhere.
- Climate's out-of-sample half has grown since 3.67 (583 events, 141 losing, against 485 and 122 then): the refreshed
  history is landing in Climate (last close now Nov 24). It still fails the tail test (27.3% bound vs 26.5% break-even).

## 3.69 Ideas queue 47: picking the band's series by their own in-sample record (12:35 am CST, Nov 25)

`research/series_concentration.py --select` (+1 test): Entertainment band, 20,000, resting entry, data to Nov 24.
Series with 10+ in-sample events and a positive in-sample per-bet return ("picked") against rejected ones (10+ events,
not positive) and thin ones (fewer than 10 in-sample events, including series new out of sample).

| group | series | in sample per bet (bets, events) | out of sample per bet (bets, events) | tail test out |
|---|---|---|---|---|
| picked (KXALBUMSALES, KXNETFLIXRANKSHOW, KXRT) | 3 | +12.66% (77, 36) | +4.97% (232, 85) | FAIL (24 losing, 37.4% vs 36.1%) |
| rejected | 0 | - | - | - |
| thin (all others) | 346 / 119 | +7.16% (947, 438) | +7.36% (508, 209) | pass |

- **FAILS: series selection adds nothing to the band.** Only three Entertainment series have 10 in-sample events; all
  three were positive and so nothing could be rejected. Out of sample the picked three earn LESS a bet than the rest and
  fail the tail test alone (mostly KXRT, 3.68). With a looser 5-event cut (a side look, not the pre-stated test) two series
  are rejected; they had 10 out-of-sample bets at -1.1%, too few to matter. The band's money comes from the long tail of
  short-lived series, which by construction have no history to select on. Family 11 (series selection) stays closed for
  the band. Variants tried here: 1 pre-stated (+1 side look).

## 3.70 Ideas queue 48: one bet per event for the band (3:10 am CST, Nov 25)

`research/one_per_event.py` (+1 test): Entertainment band (NO against YES at 5-35c), 20,000 contracts, resting entry,
data to Nov 24 (6,685 markets, 1,727 events). Per event, only the rung whose YES mid is nearest 20c on the event's first
bet day (known at the bar); every other bet of the event dropped. Replay at 1% a bet, event cap 3%.

| version | half | bets | events | per bet | losing events | upper bound vs break-even | replay /y | worst drawdown |
|---|---|---|---|---|---|---|---|---|
| all rungs | in | 1,024 | 474 | +7.58% | 106 | 25.7% vs 35.3% pass | +9.1% | 6.5% |
| all rungs | out | 740 | 294 | +6.61% | 66 | 26.8% vs 34.5% pass | +43.5% | 7.0% |
| one per event | in | 474 | 474 | +5.01% | 75 | 18.8% vs 19.8% pass | +4.4% | 7.5% |
| one per event | out | 291 | 291 | +3.13% | 46 | 19.8% vs 18.4% FAIL | +8.5% | 9.0% |

- **FAILS on both pre-stated counts.** One bet per event earns less a bet, fails the tail test out of sample, and has a
  DEEPER drawdown in both halves. The extra rungs are not what makes the drawdown: they diversify within the event
  (a losing event usually loses on one rung, while its other rungs win), so the summed event return loses less often.
  The rung nearest 20c alone is the riskier bet. No new account. Variants tried: 1 (target 20c, pre-stated).
- Side note: the all-rungs band's out-of-sample replay is now +43.5% a year (3.61 had +33.0%), with the refreshed
  history landing in Entertainment; item 64 is the proper re-test.

## 3.71 Ideas queue 49: the band against a correctly-priced null (3:15 am CST, Nov 25)

`research/calibrated_null.py` (+1 test): Entertainment band, 20,000, resting entry, data to Nov 24. The queue's wording
(shuffle outcomes within each price cent) cannot test anything: a shuffle inside a price cell keeps each cell's win count,
so the per-bet mean never moves. Replaced, before running, by draws under the null that the price is right: 5,000 draws,
one uniform per event (all rungs of an event move together, the most correlated and so the widest null), each bet
resolving YES if the uniform is below p_yes. Two nulls: p_yes = the ask (the price paid is fair) and p_yes = the mid (no
edge beyond the half spread a resting order earns).

| half | bets | events | observed per bet | null: price fair (mean, sd) | share of draws >= observed | null: mid (mean, sd) | share >= observed |
|---|---|---|---|---|---|---|---|
| in | 1,024 | 474 | +7.58% | +0.0%, 2.8% | 0.3% | +2.0%, 2.7% | 1.3% |
| out | 740 | 294 | +6.61% | +0.1%, 3.2% | 1.7% | +1.7%, 3.1% | 5.4% |

- **A milder confirmation than the tail test.** Against a fair price the band is unlikely to be luck in both halves
  (1-in-60 out of sample). Against the mid, the part of the return that is not simply the half spread is 1-in-18 out
  of sample: suggestive, not proof, and well short of the t-above-3 bar (about 1-in-750) of rule 4. Under this most
  correlated null roughly 1.7 points of the band's 6.6 come from resting inside the spread; the rest (about 5 points)
  is the over-priced-YES claim, and it is only about 1.6 sd from the null out of sample.
- The comonotone null overstates the spread for events whose rungs are not nested, so the true shares are somewhat
  smaller; no independent-draw version was run (it was not pre-stated). Nothing changes in the paper accounts.
  Variants tried: 2 nulls, both pre-stated here.

## 3.72 Ideas queue 50: a multiple-testing ledger for Entertainment (6:15 am CST, Nov 25)

No new code. Data to Nov 24 (Entertainment census: 6,685 markets at 20,000, 15,501 at 5,000). Per-event t: the mean of
each event's bet returns, events weighted equally, one-sided p from the normal curve. Resting entry.

| rule (live account) | level | half | bets | events | per bet | per-event t | one-sided p |
|---|---|---|---|---|---|---|---|
| band, NO vs YES 5-35c (rule_ent_band_20k) | 20,000 | in | 1,024 | 474 | +7.58% | +2.53 | 0.0056 |
| band | 20,000 | out | 740 | 294 | +6.61% | +2.52 | 0.0059 |
| fall rule, 10-25c down 3c+ in 7d (rule_ent_fall) | 5,000 | in | 847 | 481 | +8.59% | +3.67 | 0.0001 |
| fall rule | 5,000 | out | 579 | 260 | +5.16% | -0.04 | 0.52 |
| 35-50c fall rule (rule_ent_fall_35_50) | 20,000 | in | 217 | 165 | +23.96% | +3.38 | 0.0004 |
| 35-50c fall rule | 20,000 | out | 125 | 77 | +14.65% | +0.93 | 0.18 |

How many things were tried on Entertainment: round r21 (the busy-sample sweep that found the band) scored 2,890 rules on
both halves, r20 (random sample) 2,864 more; the follow-ups since 3.24 (queue items 1, 2, 5, 6, 14, 19, 20, 25, 26, 28,
30-38, 40, 41, 43-49: levels, entries, slices, windows, stops, take-profits, nulls) come to about 125 variants by the
reports' own counts. Holm at 5%, out-of-sample p only:

| family counted | m | first threshold | band (p 0.0059) | fall rule (0.52) | 35-50c fall (0.18) |
|---|---|---|---|---|---|
| the three live accounts only | 3 | 0.0167 | passes | fails | fails |
| plus the follow-ups since 3.24 | ~128 | 0.0004 | fails | fails | fails |
| plus the r21 sweep that found the band | ~3,000 | 0.00002 | fails | fails | fails |

- **Deflated verdict, plainly: nothing on Entertainment survives a correction that counts the search.** The band is the
  only one of the three with a real out-of-sample signal (t 2.5, the same as in sample, and it passes the tail test both
  halves), but t 2.5 is what the best of ~3,000 tries would show by luck about as often as not; rule 4's bar (t 3 out of
  sample) is not met either. It passes Holm only if the family is the three accounts now trading, which ignores how
  they were picked.
- **The two fall rules have no out-of-sample signal by event.** The 10-25c fall rule's +5.2% a bet out of sample is
  carried by events with many bets; the event-weighted mean is zero (t -0.04). The 35-50c rule's +14.7% is t 0.9 on 77
  events. Both pass the tail test out of sample because of their high break-even loss rates, not because of a proven edge.
- Nothing changes in the paper accounts (they are the forward test that settles this); the band stays the lead, the
  fall rules stay on probation. New item 71: why the fall rule's per-bet and per-event means differ.

## 3.73 Ideas queue 51: the band by spread at entry, and a bid a cent inside the spread (6:15 am CST, Nov 25)

No new code (research/resting_variants.variant and describe on the band's mask). Entertainment band, 20,000, data to
Nov 24, NO bid resting 3 daily bars. "deeper -1" = a cent better than the best NO bid (possible only where the spread is
2c or more). Each spread row takes a market's first bar with that spread, so a market can appear in more than one row.

| spread at entry | bid | bets | events | fill | per bet | in: per bet, losing | out: per bet, losing | replay 1% /y in / out | worst DD in / out |
|---|---|---|---|---|---|---|---|---|---|
| all | best bid | 1,764 | 765 | 77% | +7.17% | +7.58%, 106/474 ok | +6.61%, 66/294 ok | +9.2% / +37.8% | 6.4% / 7.0% |
| all | 1c inside | 1,535 | 694 | 89% | +7.70% | +7.06%, 98/440 ok | +8.69%, 45/257 ok | +6.8% / +38.7% | 5.8% / 5.4% |
| 1c | best bid | 1,093 | 509 | 77% | +5.56% | +7.32%, 57/298 ok | +3.42%, 46/213 ok | +7.2% / +15.5% | 5.6% / 5.9% |
| 2c | best bid | 838 | 444 | 76% | +7.52% | +6.71%, 51/274 ok | +8.75%, 25/172 ok | +5.9% / +25.1% | 4.0% / 4.9% |
| 2c | 1c inside | 909 | 462 | 93% | +7.12% | +6.46% | +8.12% | +4.8% / +27.1% | 3.1% / 4.8% |
| 3-5c | best bid | 1,030 | 527 | 76% | +8.67% | +8.19%, 72/333 ok | +9.46%, 38/195 ok | +7.4% / +35.2% | 4.1% / 4.4% |
| 3-5c | 1c inside | 1,115 | 548 | 89% | +8.14% | +7.53% | +9.18% | +6.3% / +34.0% | 5.2% / 3.9% |
| 6-10c | best bid | 470 | 321 | 67% | +11.12% | +11.49%, 37/228 ok | +10.32%, 19/93 ok | +9.1% / +14.4% | 4.6% / 2.7% |
| 6-10c | 1c inside | 535 | 350 | 81% | +10.49% | +10.83% | +9.73% | +8.7% / +15.9% | 4.4% / 2.7% |

- **The band's money rises with the spread at entry, in both halves**: 1c +5.6% a bet, 2c +7.5%, 3-5c +8.7%, 6-10c
  +11.1%. Every row passes the tail test in both halves. The tightest quotes (1c, the most bets) are the weakest out of
  sample (+3.4%). Consistent with "a resting bid in a wide quote earns part of the spread", and with wide quotes marking
  markets the crowd prices carelessly. Not a pre-stated test: item 72 pre-states a "spread 2c+" cut.
- **Bidding a cent inside the spread is not clearly worth it.** It fills more (89-93% against 76-77%) but earns less a
  bet in every spread row and in sample overall (+7.06% against +7.58%; replay +6.8% against +9.2% a year); only the
  whole-band out-of-sample row is better (+8.69%), and that row also drops the 1c-spread first bars, so it is partly
  the spread effect above. Accounts stay at the best bid. Variants tried: 5 spread rows x 2 bids, one run.

## 3.74 Ideas queue 52: weekend against weekday entry for the band (6:16 am CST, Nov 25)

No new code. Entertainment band, 20,000, resting, data to Nov 24; each bet split by the weekday of its entry bar (UTC
date). Replay at 1%, event cap 3%.

| entry day | bets in / out | per bet in / out | losing events in / out (bound vs break-even) | replay 1% /y in / out | worst DD in / out |
|---|---|---|---|---|---|
| all | 1,024 / 740 | +7.58% / +6.61% | 106/474 ok / 66/294 ok | +9.1% / +43.5% | 6.5% / 7.0% |
| Fri-Sun | 440 / 339 | +6.84% / +7.29% | 56/270 (25.2% vs 29.7%) ok / 39/208 (23.8% vs 29.3%) ok | +11.9% / +24.5% | 7.3% / 5.7% |
| Mon-Thu | 584 / 401 | +8.13% / +6.04% | 65/345 (22.6% vs 30.0%) ok / 44/200 (27.4% vs 31.1%) ok | +7.2% / +24.9% | 4.5% / 5.3% |

- **No weekday effect.** Both parts pass the tail test in both halves, and which part earns more flips between the
  halves (in sample Mon-Thu by 1.3 points, out of sample Fri-Sun by 1.3). Nothing to use. Variants tried: 1, pre-stated.

## 3.75 Ideas queue 53: volume spikes in the band (6:17 am CST, Nov 25)

No new code. Entertainment band, 20,000, resting, data to Nov 24. A bet is a "spike" when its 7-day volume (dvol7) is at
or above the 75th percentile of that market's STRICTLY earlier bars in the sample; the percentile needs 5 earlier bars
(added before running: the bar itself cannot be its own history).

| split | bets in / out | per bet in / out | losing events in / out (bound vs break-even) | replay 1% /y in / out | worst DD in / out |
|---|---|---|---|---|---|
| all | 1,024 / 740 | +7.58% / +6.61% | ok / ok | +9.1% / +43.5% | 6.5% / 7.0% |
| spike | 66 / 34 | -2.66% / +10.50% | 12/46 (38.8% vs 23.1%) FAIL / 2/22 (25.9% vs 21.8%) FAIL | -0.9% / +3.2% | 3.2% / 1.0% |
| not a spike | 91 / 67 | +13.38% / +15.88% | 12/68 ok / 6/43 ok | +6.2% / +9.8% | 3.7% / 1.7% |
| under 5 earlier bars | 867 / 639 | +7.75% / +5.43% | 93/448 ok / 61/285 ok | +8.3% / +32.7% | 6.6% / 7.5% |

- **The split cannot be read: 85% of the band's bets have no history to compare with.** The liquid sample starts a market
  at its 20,000-contract bar, and most band bets are on that bar or soon after. Among the 258 bets that have history,
  spikes are mixed (lose in sample, win out of sample on 34 bets; tail test fails both halves) and the rest earn more.
  No account; variants tried: 1, pre-stated.
- Side finding, not pre-stated: the 158 non-spike bets with 5+ earlier bars earn about twice the band a bet in both
  halves (+13.4% / +15.9%). They are markets that came INTO the band late, after time above 20,000: item 73 tests that.

## 3.76 Ideas queue 54: the Climate band by series group and days to close; the Climate 5-cent rule at 20,000 (6:18 am CST, Nov 25)

No new code. Climate and Weather, liquid sample at 5,000 (45,407 markets, data to Nov 24), NO against YES at 5-35c,
resting. Series groups by ticker (KXHIGH*, KXLOW*, KXRAIN*, snow series, KXHUR*/KXTROP*, the rest). Cells: bets, per bet,
losing events, bound vs break-even. Replay at 1% in / out.

| slice | in sample | out of sample | replay /y in / out | worst DD in / out |
|---|---|---|---|---|
| all | 1,099, +0.71%, 188/731, 28.5% vs 26.5% FAIL | 1,104, +1.81%, 169/680, 27.7% vs 27.4% FAIL | +2.0% / +29.5% | 15.6% / 12.2% |
| daily highs | 641, +0.31%, FAIL | 571, +2.51%, FAIL | +0.4% / +30.8% | 13.4% / 6.8% |
| lows | 39, +9.70%, FAIL | 80, -3.30%, FAIL | +18.2% / -4.2% | 1.8% / 6.3% |
| rain | 99, +6.44%, FAIL | 350, +2.85%, FAIL | +3.0% / +12.4% | 3.4% / 7.1% |
| snow | 133, -5.98%, FAIL | 20, +14.10%, FAIL | -2.6% / +40.2% | 15.1% / 2.0% |
| hurricanes, tropical | 74, +7.64%, FAIL | 12, +4.25%, FAIL | +2.2% / +1.5% | 3.8% / 1.0% |
| the rest | 113, -1.80%, FAIL | 71, -7.13%, FAIL | +0.3% / -8.0% | 5.1% / 7.3% |
| 0-7 days | 724, +1.09%, FAIL | 872, +2.01%, FAIL | +1.6% / +35.3% | 13.1% / 8.0% |
| 8-30 days | 262, -2.05%, FAIL | 193, +0.61%, FAIL | -2.1% / +0.2% | 15.5% / 9.4% |
| 31 days+ | 113, +4.70%, FAIL | 39, +3.08%, FAIL | +2.2% / +1.5% | 4.6% / 2.0% |

5-cent rule (NO at mid 5c or less, 30 days or less, spread 5c or less), Climate and Weather alone at 20,000: in sample 150
bets, +3.03%, 2/120 losing (5.2% vs 5.3%) passes by a hair; out of sample 199 bets, +1.55%, 4/150 (6.0% vs 4.7%) FAILS;
replay 1% +1.0% / +4.4% a year, drawdown 1.3% / 1.1%.

- **No part of the Climate band passes the tail test in either half**, by series group or by days to close. The
  out-of-sample replay's +29.5% a year is the daily-high markets at 0-7 days, whose loss rate sits right on break-even;
  with a 12-16% drawdown it is not risk-averse. The Climate band stays a failed echo (as 3.67); rule_climate_band
  and the combined account's Climate leg keep trading only as forward records.
- **The Climate 5-cent rule at 20,000 fails out of sample**, as it did at 45,000 (3.44) and on the random sample (r24).
  Climate stays out of the 5-cent rule's categories. Variants tried: 6 groups + 3 windows + 1, all as the queue stated.

### 3.77 Politics alone at 20,000: the band and the 5-cent rule (9:25 am CST, November 25)

Ideas queue item 55. 3.33 found the band passes in Politics only at 45,000 (by 0.4 points out of sample). Re-run on
today's data: `analyze_rule.py --sample liquid --categories Politics --min-cumvol <level> --side no --entry mk`, the
band ("NO where YES is at 5-35c") at 20,000 and the 5-cent rule ("NO at mid <= 5c, <= 30d, spread <= 5c") at 20,000
and 45,000. 3 variants, all stated in the queue.

| Politics | Bets (events) | Per bet | Losing events in / out | Tail test in / out | Replay 1%, in / out a year | Worst DD in / out |
|---|---|---|---|---|---|---|
| band, 20,000 | 1,371 (671) | +2.74% | 92/427 / 77/266 | passes (25.1 vs 26.4%) / **FAILS** (33.9 vs 30.8%) | +1.5% / +2.9% | 11.7% / 7.2% |
| 5-cent rule, 20,000 | 792 (438) | +2.58% | 7/269 / 3/187 | passes (4.8 vs 6.7%) / passes (4.1 vs 6.5%) | +1.6% / +13.6% | 2.6% / 1.0% |
| 5-cent rule, 45,000 | 504 (288) | +2.77% | 4/195 / 1/108 | passes (4.6 vs 6.1%) / passes (4.3 vs 5.9%) | +1.1% / +7.7% | 1.9% / 1.0% |

- **The Politics band fails out of sample at 20,000 again** (as 3.33): its pass at 45,000 is one level, not a stable
  effect. No Politics band account.
- **The 5-cent rule holds in Politics alone at both levels** (+2.6% / +2.8% a bet, both halves, shallow drawdowns;
  capacity at 20,000: median $411 traded in the week before entry, 19% of entry days under 100 contracts). Politics
  is already one of the nine inside rule_5c_busy, so a Politics-only account would be a subset of a live account,
  not a new edge; its in-sample year (+1.6%) is as thin as the pooled rule's, and by year the money is 2026 (2025 per
  bet +0.0%). **No new account.** The pooled rule's out-of-sample reliance on Apr-Jun (3.67) is the open question;
  Politics does not answer it.

### 3.78 Stale quotes in the band (9:35 am CST, November 25)

Ideas queue item 61. Is the band's edge in overpriced YES quotes nobody re-prices? `research\stale_quotes.py 20000`
(new, + 1 test): a band bar is STALE(k) when its YES mid equals the mid of each of the market's k earlier bars in the
liquid sample, MOVED when it differs from any, NEW when the market has under k earlier bars. First band bar per market
inside each group (a market can be in several groups, so the groups overlap). Entertainment, 20,000, resting. 6 cells.

| Group | Bets (events) | Per bet | Tail test in / out | Replay 1%, in / out a year | Worst DD in / out | Median $ traded week before |
|---|---|---|---|---|---|---|
| k=3 stale | 194 (101) | +3.63% | **fails** (29.1 vs 25.4%) / **fails** (31.8 vs 25.0%) | +2.3% / +1.7% | 3.9% / 2.5% | $594 |
| k=3 moved | 1,039 (471) | +8.76% | passes (24.8 vs 35.2%) / passes (22.7 vs 36.8%) | +6.6% / +37.5% | 5.2% / 2.7% | $2,667 |
| k=3 new | 1,396 (706) | +6.16% | passes / passes | +7.5% / +27.2% | 7.3% / 7.4% | $2,723 |
| k=7 stale | 27 (21) | +2.48% | too few | -0.8% / +2.3% | 1.6% / 0.0% | $134 |
| k=7 moved | 722 (318) | +7.50% | passes / passes | +5.3% / +23.3% | 4.6% / 1.9% | $1,634 |
| k=7 new | 1,563 (736) | +7.08% | passes / passes | +9.0% / +35.7% | 6.4% / 7.4% | $2,773 |

- **The idea is reversed: stale quotes are the band's WORST bets** (+3.6% a bet, fails the tail test in both halves,
  thin markets: a quarter of entry days under 100 contracts). The edge sits in band bars whose price has just moved.
  A stale mid in a thin market is probably a quote nobody trades, not an overpriced one.
- No account: the groups overlap and none was pre-stated as a variant. **Pre-stated for the queue (item 75):** the band
  at 20,000 skipping a bar that is STALE(3) (the market's next non-stale band bar is taken instead); passes only if it
  passes the tail test in both halves and its 1% replay beats the whole band out of sample (+37.8% a year, 3.72) with a
  worst drawdown no deeper (7.0%). Counted in the band's multiple-testing tally (item 50).

### 3.79 The refreshed history: Entertainment rules on markets that settled after they were chosen (9:50 am CST, November 25)

Ideas queue item 64, first part. Entertainment's late listings finished at 9:15 pm Nov 24; the sample now runs to markets
closing **Nov 24, 2026** (the old archive stopped at Sep 19). Same commands as 3.29 / 3.46 / 3.55 (`analyze_rule.py
--sample liquid --categories Entertainment --side no --entry mk --min-cumvol N`). The "Sep 20+" columns are bets on
markets that closed on or after Sep 20, 2026: none of them was in any backtest when the rules were picked (3.24-3.55).
Event tail test on that slice alone. 6 rules re-run, nothing new chosen.

| Rule, level | Then (report) | Now, all: bets, per bet, tail in / out | Replay 1% in / out a year, worst DD out | Sep 20+: bets (events), per bet, losing events, tail |
|---|---|---|---|---|
| band, 5,000 | 1,937, +7.28% (3.29); 3,450, +4.57% (3.46) | 3,972, +4.42%, passes / passes | +6.6% / +5.2%, 11.1% | 521 (156), +3.37%, 50, passes (38.7 vs 39.1%) |
| band, 20,000 | 1,526, +7.39% (3.46) | 1,764, +7.17%, passes / passes | +9.1% / +43.5%, 7.0% | 238 (76), +5.79%, 19, passes (34.5 vs 36.1%) |
| band, 45,000 | 815, +7.14% (3.46) | 943, +6.56%, passes / passes | +9.3% / +25.9%, 3.4% | 128 (43), +2.88%, 15, too few to pass (48.5 vs 41.2%) |
| fall 10-25c, 5,000 | +8.95% (3.24) | 1,426, +7.20%, passes / passes | +6.4% / +3.6%, **14.3%** | 169 (67), +2.47%, 20, does not pass (40.4 vs 33.7%) |
| fall 35-50c, 20,000 | +22.9% (3.55) | 342, +20.56%, passes / passes | +11.9% / +19.3%, 4.3% | 51 (29), +7.41%, 13, too few (61.6 vs 50.6%) |
| 5-cent, Entertainment, 5,000 | (combined leg) | 2,069, +1.64%, passes (all) | - | 211 (104), +3.18%, 1, passes (4.5 vs 7.3%) |

- **No verdict changes.** Every rule is still positive on the markets it had never seen, and every one still passes the
  tail test in both halves of the full sample. The band at 20,000 (rule_ent_band_20k's level) passes on the fresh slice
  alone: +5.8% a bet on 76 events, against +7.4% when chosen.
- **Every fresh-slice per-bet figure is below the figure at selection** (band 5,000 +3.4 vs +7.3%, 20,000 +5.8 vs +7.4%,
  fall 10-25c +2.5 vs +9.0%, fall 35-50c +7.4 vs +22.9%): the usual shrink after selection. The 10-25c fall rule is the
  weakest: its fresh slice does not pass the tail test and its out-of-sample replay now has a 14.3% worst drawdown.
  Not risk-averse on this record; it keeps trading on paper as a record only.
- Two months is one season of Entertainment (awards, box office, charts); the fresh slices are 29-156 events. Still to
  do under item 64: the 5-cent rule on the nine (Politics and Economics late bars are landing now) and the Climate band.

### 3.80 The Climate band at 5,000 / 20,000 / 45,000 on the refreshed history (10:00 am CST, November 25)

Ideas queue item 66, and item 64's Climate part (Climate's late listings finished at 4:07 am Nov 25; closes to Nov 24).
`analyze_rule.py --sample liquid --categories "Climate and Weather" --rule "NO where YES is at 5-35c" --side no --entry mk
--min-cumvol N`; "Sep 20+" as in 3.79. 3 levels, stated in the queue.

| Level | Bets (events) | Per bet | Tail test in / out | Replay 1% in / out a year | Worst DD in / out | Sep 20+: bets (events), per bet, tail |
|---|---|---|---|---|---|---|
| 5,000 | 2,203 (1,411) | +1.26% | **fails** (28.5 vs 26.5%) / **fails** (27.7 vs 27.4%) | +2.0% / +29.5% | 15.6% / 12.2% | 348 (194), +1.95%, fails |
| 20,000 | 429 (314) | +5.91% | **fails** (26.7 vs 24.4%) / passes (15.6 vs 19.4%) | +1.5% / +27.6% | 5.1% / 3.0% | 85 (60), +10.15%, passes |
| 45,000 | 193 (158) | +7.68% | **fails** (26.1 vs 21.3%) / passes (13.8 vs 18.8%) | +0.8% / +16.9% | 4.4% / 1.4% | 54 (41), +11.56%, passes |

- **At 5,000 (rule_climate_band's level) the band still fails both halves** (as 3.67), fresh markets included.
- **In busier Climate markets it is strong out of sample and on the fresh markets** (20,000: +10.2% a bet on 60 fresh
  events, 6 losing) **but fails in sample at both levels**: the in-sample years earn +0.8-1.5% a year. A rule that passes
  only out of sample does not meet the rules for judging a result. **No account changes.** Capacity at 20,000: median
  $3,267 traded in the week before entry. Queue item 76 added: re-check once a third month of fresh Climate markets is in,
  as a pre-stated test (20,000, the fresh slice alone), not a new search.

### 3.81 Rotten Tomatoes ladders in the band (10:05 am CST, November 25)

Ideas queue item 67. The band (Entertainment, 20,000, resting; closes to Nov 24) split into KXRT* series (Rotten Tomatoes
score ladders, one series per film) against the rest, each half, event tail test. One split, pre-stated.

| Group | Half | Bets (events) | Per bet | Losing events | Tail test | Median $ traded week before |
|---|---|---|---|---|---|---|
| KXRT* | in | 246 (111) | +7.97% | 27 | passes (31.9 vs 36.3%) | $4,152 |
| KXRT* | out | 207 (69) | +2.69% | 24 | **fails** (45.3 vs 39.3%) | $5,269 |
| rest | in | 778 (363) | +7.45% | 79 | passes (25.6 vs 35.1%) | $2,015 |
| rest | out | 533 (225) | +8.14% | 42 | passes (23.5 vs 34.4%) | $2,545 |

- **RT is weaker than the rest only out of sample** (+2.7% against +8.1% a bet, and it fails the tail test there); in
  sample it is slightly better (+8.0% against +7.5%). The queue's condition for a "band without RT" variant (RT below
  the rest in BOTH halves) is not met, so **no variant is tested and no account changes**. RT is about a quarter of the
  band's bets and its busiest markets; whether RT's out-of-sample slump persists is a forward question for
  rule_ent_band_20k (item 77).

### 3.82 Ladder rungs out of line: NO on a rung 3c+ above its neighbours' line (12:20 pm CST, November 25)

Ideas queue item 60. New rule in `research/families.py` (family 6, `ladder_kink`, + a test): a rung whose YES mid is 3c or
more above the average of the rungs just above and below it (both quoted, known at the bar); buy NO on it, resting.
Liquid sample, closes to Nov 24 (the nine's Health, World, Commodities and Financials late bars not yet landed).
4 variants tried (2 groups x 2 levels), stated in the queue.

| Group, level | Bets (events) | Per bet | Tail test in / out | Replay 1% in / out a year | Worst DD in / out |
|---|---|---|---|---|---|
| Entertainment, 20,000 | 328 (136) | +7.87% | fails (77.3 vs 72.3%) / fails (71.2 vs 63.6%) | +6.1% / +32.4% | 23.5% / 24.5% |
| Entertainment, 45,000 | 108 (55) | -7.20% | fails / fails | -9.8% / +3.7% | 16.4% / 10.6% |
| nine, 20,000 | 632 (284) | +6.91% | fails (68.2 vs 65.6%) / fails (75.8 vs 71.4%) | +3.4% / +20.8% | 24.2% / **51.3%** |
| nine, 45,000 | 287 (143) | +36.9% | passes (68.5 vs 73.3%) / passes, barely (74.6 vs 75.0%) | +20.1% / +75.3% | 11.8% / 16.3% |

- **FAILS as a strategy.** Three of four cells fail the tail test in both halves. The one pass (the nine at 45,000) is
  not borne out one level down (the nine at 20,000, which contains it, fails both halves with a 51% drawdown), its
  2023-24 bets lose, its out-of-sample bound clears break-even by 0.4 points, and the profit sits in a few macro ladders
  (KXGDP, KXPAYROLLS, KXAAAGASM: 61% of it). It is a 28c longshot-NO bet that loses 60% of the time: drawdowns of 12-16% at
  a 1% stake are not risk-averse. **No account.** Capacity at 45,000: median $40,900 traded in the week before entry.
- Item 78 added: the nine at 45,000 re-checked as a pre-stated test once all nine categories' late bars have landed.

### 3.83 The band by series life: new series against older ones (12:23 pm CST, November 25)

Ideas queue item 68. The band (Entertainment, NO where YES is 5-35c, 20,000+, resting; closes to Nov 24) split by whether
the bet's series had its first market open within 30 days before the bet (known at the bar). `research/band_splits.py
--split life` (new, + a test). One split, pre-stated.

| Group | Half | Bets (events) | Per bet | Losing events | Tail test | Median $ traded week before |
|---|---|---|---|---|---|---|
| new series (<=30 days) | in | 285 (159) | +6.19% | 39 | passes (30.8 vs 32.7%) | $4,130 |
| new series | out | 111 (42) | +6.77% | 10 | passes (37.0 vs 39.4%) | $3,091 |
| older series | in | 739 (337) | +8.11% | 72 | passes (25.4 vs 36.5%) | $2,045 |
| older series | out | 629 (262) | +6.58% | 59 | passes (27.2 vs 33.8%) | $3,086 |

- **No difference.** New series do not carry the edge: both groups pass the tail test in both halves at about the same
  per-bet return (out of sample +6.8% against +6.6%). The pre-stated "new series only" variant is not taken up, and
  nothing changes. 3.69's "short-lived series" finding is about series that list few markets, not series that are new.

### 3.84 The band by bets per event (12:25 pm CST, November 25)

Ideas queue item 69. The band (Entertainment, 20,000+, resting; closes to Nov 24) split by how many band bets its event
took. `research/band_splits.py --split per_event`. One split, pre-stated.

| Bets in the event | Half | Bets (events) | Per bet | Event sum, mean | Losing events | Tail test |
|---|---|---|---|---|---|---|
| 1 | in | 258 (258) | +2.16% | +0.022 | 44 | **fails** (21.4 vs 18.8%) |
| 1 | out | 134 (134) | +3.27% | +0.033 | 19 | **fails** (20.1 vs 16.9%) |
| 2-3 | in | 334 (143) | +6.98% | +0.163 | 41 | passes (35.5 vs 40.9%) |
| 2-3 | out | 221 (97) | +6.60% | +0.150 | 28 | passes (37.4 vs 40.1%) |
| 4+ | in | 432 (73) | +11.27% | +0.667 | 21 | passes (38.7 vs 70.0%) |
| 4+ | out | 385 (63) | +7.78% | +0.476 | 19 | passes (41.0 vs 53.0%) |

- **The edge grows with ladder width in both halves**: events where only one rung entered the band earn +2-3% a bet and
  fail the tail test; events with 4+ band rungs earn +8-11% a bet. Most of the band's profit is in wide ladders.
- **Not a rule as it stands**: how many rungs will enter the band is known only afterwards. What is known at the bar is
  how many rungs the event already lists and how many are already in the band. Queue item 79 pre-states that test.

### 3.85 The 10-25c fall rule by bets per event (12:27 pm CST, November 25)

Ideas queue item 71 (3.72: +5.2% a bet out of sample but event-weighted t 0.0). Entertainment, NO where YES at 10-25c has
fallen 3c+ in 7 days, 5,000+, resting (rule_ent_fall's level); closes to Nov 24. `research/band_splits.py --split per_event
--rule "mid 10-25c, down 3c+ in 7d" --min-cumvol 5000`.

| Bets in the event | Half | Bets (events) | Per bet | Event sum, mean | Losing events | Tail test |
|---|---|---|---|---|---|---|
| 1 | in | 300 (300) | +5.31% | +0.053 | 47 | passes (19.5 vs 19.9%) |
| 1 | out | 137 (137) | **-5.60%** | -0.056 | 31 | **fails** (29.3 vs 18.0%) |
| 2-3 | in | 328 (143) | +8.79% | +0.202 | 40 | passes |
| 2-3 | out | 191 (83) | +4.85% | +0.112 | 19 | **fails** (31.8 vs 29.1%) |
| 4+ | in | 219 (38) | +12.77% | +0.736 | 9 | passes |
| 4+ | out | 251 (40) | +11.28% | +0.708 | 12 | passes (44.0 vs 66.5%) |

- **Yes, it is the wide ladders.** Out of sample, the 137 single-bet events lose 5.6% a bet and the 2-3 bet events fail the
  tail test; all of the rule's out-of-sample profit sits in 40 events with 4+ bets (251 bets). That is why the per-bet
  mean is positive while the event-weighted t is 0. Together with 3.79 (fresh slice fails, 14.3% drawdown), the fall rule
  is not risk-averse; rule_ent_fall keeps trading on paper as a record only. Item 79's at-the-bar ladder-width test covers
  this rule too (added there).

### 3.86 Calibrated nulls for the live rules (12:45 pm CST, November 25)

Ideas queue item 70. `research/calibrated_null.py` (3.71) for the three live rules besides the band, and the band with
one draw per MARKET (`--independent`, new, + a test) as the narrow bound beside 3.71's whole-event one. 2,000 draws.
Cell: share of null draws with a per-bet return at least the observed one (small = the edge is not luck). Closes to
Nov 24-25.

| Rule (level) | Half | Bets (events) | Observed per bet | Null "price fair (ask)" | Null "mid" |
|---|---|---|---|---|---|
| 5-cent, nine (45,000) | in | 790 (505) | +1.83% | 0.028 | 0.12 |
| 5-cent, nine (45,000) | out | 519 (304) | +1.78% | 0.075 | 0.20 |
| fall 10-25c, Ent (5,000) | in | 847 (481) | +8.59% | <0.001 | 0.006 |
| fall 10-25c, Ent (5,000) | out | 579 (260) | +5.16% | 0.098 | 0.21 |
| fall 35-50c, Ent (20,000) | in | 217 (165) | +23.96% | <0.001 | 0.005 |
| fall 35-50c, Ent (20,000) | out | 125 (77) | +14.65% | 0.11 | 0.14 |
| band, Ent (20,000), per market | in | 1,024 (474) | +7.58% | <0.001 | <0.001 |
| band, Ent (20,000), per market | out | 740 (294) | +6.61% | <0.001 | 0.002 |

- **Out of sample, no live rule except the band clears even the "price fair" null at 5%** when a ladder's rungs share
  one draw: the 5-cent rule (0.075), the 10-25c fall rule (0.098) and the 35-50c fall rule (0.11). Against the mid null
  (what a resting order earns for free from the half spread) they are at 0.14-0.21: indistinguishable from no edge.
- The 5-cent rule does not clear the mid null even in sample (0.12): its +1.8% a bet is mostly the half spread.
- The band clears both nulls with markets drawn independently (the narrow bound); with whole events (3.71) it was 0.006
  out of sample on the mid null. Between the two bounds, the band is the one live rule this test supports.
- No account changes (the accounts are records; nothing reaches config). It agrees with 3.72's Holm count and 3.85.
