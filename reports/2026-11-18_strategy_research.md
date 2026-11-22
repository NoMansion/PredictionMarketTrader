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
