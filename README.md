# Chase Value (xChase+ and Chase+)

**Everything, hosted:** [samuelosullivan6-rgb.github.io/ChasePlus](https://samuelosullivan6-rgb.github.io/ChasePlus/)
has every hitter's decision card, the roster by team, the noted hitters'
report with printable cards, and this write-up.

Chase rate counts how often a hitter swings outside the zone and treats
every one of those swings as the same mistake. They aren't: a chase on
3-2 costs about 5.6 times as many runs as one on 0-1. This project prices
every chase decision in runs from Statcast data (2021-2026), builds a
per-season leaderboard, and tests whether the numbers hold up.

Two scores, one scale: **xChase+** (the main number, version 1.1) prices
a chase put in play by how it was hit, using Savant's xwOBA; **Chase+**
(version 2.0) prices it by what actually happened. Takes, whiffs and
fouls are priced the same in both, and Chase+ minus xChase+ is **luck**.

**Reading the charts:** solid mark = estimate, pale band or ± =
uncertainty, thin gray line = league average (100).

## Results

### Why price chases instead of counting them

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/xchase/figures/chase_cost_by_count_dark.png">
  <img alt="Average runs lost per chase in each count, from 0.061 at 0-1 to 0.338 at 3-2" src="results/xchase/figures/chase_cost_by_count.png" width="560">
</picture>

A chase with three balls costs far more than one early in the count.

### Leaders and trailers, season by season

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/xchase/figures/leaderboard_by_season_dark.png">
  <img alt="Top 5 and bottom 5 hitters by xChase+ for each season from 2021 to 2026, with uncertainty bars and each hitter's Chase+ marked as a hollow ring" src="results/xchase/figures/leaderboard_by_season.png" width="720">
</picture>

About 250-280 hitters qualify a season; 130 is about the top 7%. The
hollow ring is the hitter's Chase+, the line between them luck. Full
tables: `results/xchase/xchase_leaderboard_<season>.csv`.

<details>
<summary>Top 5 and bottom 5 as tables</summary>

**2021** (251 qualified hitters)

| Rank | Player | PA | Chase% | Runs saved / 600 PA | xChase+ ± 1 SD | Chase+ | Luck |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | Juan Soto | 635 | 12.2% | +24.4 | **167** ± 6 | 157 | -10 |
| 2 | Robbie Grossman | 668 | 15.7% | +20.1 | **155** ± 7 | 153 | -3 |
| 3 | Brandon Nimmo | 384 | 15.1% | +19.1 | **153** ± 8 | 146 | -7 |
| 4 | Brandon Belt | 378 | 19.0% | +17.3 | **148** ± 12 | 145 | -3 |
| 5 | Mookie Betts | 550 | 18.4% | +16.3 | **145** ± 8 | 142 | -3 |
| | ... | | | | | | |
| 247 | Kevin Pillar | 345 | 36.4% | -11.3 | **69** ± 10 | 87 | +18 |
| 248 | Adolis García | 622 | 35.8% | -11.9 | **67** ± 10 | 79 | +11 |
| 249 | James McCann | 412 | 32.1% | -12.2 | **66** ± 10 | 72 | +5 |
| 250 | Salvador Pérez | 660 | 45.3% | -15.5 | **57** ± 11 | 58 | +0 |
| 251 | Javier Báez | 547 | 44.7% | -16.8 | **54** ± 12 | 72 | +18 |

**2022** (267 qualified hitters)

| Rank | Player | PA | Chase% | Runs saved / 600 PA | xChase+ ± 1 SD | Chase+ | Luck |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | Juan Soto | 662 | 17.1% | +18.6 | **153** ± 9 | 140 | -13 |
| 2 | Steven Kwan | 635 | 20.3% | +15.8 | **145** ± 7 | 140 | -5 |
| 3 | Alex Bregman | 655 | 18.2% | +15.7 | **145** ± 7 | 141 | -4 |
| 4 | Max Muncy | 564 | 16.4% | +15.5 | **144** ± 8 | 139 | -6 |
| 5 | Jesse Winker | 546 | 18.6% | +15.5 | **144** ± 7 | 130 | -14 |
| | ... | | | | | | |
| 263 | Jorge Mateo | 532 | 36.8% | -10.9 | **69** ± 9 | 71 | +2 |
| 264 | Hunter Dozier | 500 | 33.0% | -11.3 | **68** ± 9 | 61 | -7 |
| 265 | Avisaíl García | 382 | 41.1% | -11.4 | **68** ± 11 | 67 | -1 |
| 266 | Jeremy Peña | 556 | 38.0% | -11.7 | **67** ± 8 | 72 | +5 |
| 267 | Javier Báez | 590 | 47.7% | -13.2 | **63** ± 11 | 68 | +6 |

**2023** (280 qualified hitters)

| Rank | Player | PA | Chase% | Runs saved / 600 PA | xChase+ ± 1 SD | Chase+ | Luck |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | Juan Soto | 706 | 16.6% | +20.4 | **154** ± 8 | 148 | -6 |
| 2 | Lars Nootbaar | 505 | 17.0% | +19.1 | **151** ± 9 | 148 | -3 |
| 3 | Ha-Seong Kim | 627 | 20.5% | +18.2 | **148** ± 7 | 155 | +7 |
| 4 | Alex Bregman | 721 | 18.7% | +17.9 | **148** ± 7 | 139 | -8 |
| 5 | Will Smith | 548 | 25.6% | +16.8 | **145** ± 9 | 144 | -1 |
| | ... | | | | | | |
| 276 | Jake Burger | 539 | 38.9% | -14.4 | **62** ± 9 | 59 | -3 |
| 277 | Mickey Moniak | 319 | 46.9% | -15.5 | **59** ± 12 | 65 | +6 |
| 278 | Christian Bethancourt | 333 | 45.3% | -16.8 | **55** ± 11 | 64 | +9 |
| 279 | Elehuris Montero | 306 | 43.7% | -16.9 | **55** ± 13 | 63 | +8 |
| 280 | Javier Báez | 542 | 44.4% | -20.2 | **46** ± 10 | 45 | -2 |

**2024** (269 qualified hitters)

| Rank | Player | PA | Chase% | Runs saved / 600 PA | xChase+ ± 1 SD | Chase+ | Luck |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | Juan Soto | 710 | 18.0% | +17.7 | **149** ± 8 | 149 | +0 |
| 2 | Mookie Betts | 516 | 21.2% | +17.1 | **148** ± 8 | 135 | -13 |
| 3 | Lars Nootbaar | 404 | 17.0% | +15.5 | **143** ± 8 | 139 | -4 |
| 4 | Ha-Seong Kim | 469 | 18.8% | +14.6 | **141** ± 8 | 131 | -10 |
| 5 | Steven Kwan | 543 | 19.2% | +14.1 | **139** ± 7 | 134 | -5 |
| | ... | | | | | | |
| 265 | Seth Brown | 401 | 30.1% | -11.6 | **68** ± 10 | 73 | +6 |
| 266 | Harrison Bader | 434 | 33.6% | -12.0 | **67** ± 9 | 70 | +3 |
| 267 | Ceddanne Rafaela | 569 | 46.7% | -15.4 | **57** ± 9 | 67 | +10 |
| 268 | Ezequiel Tovar | 695 | 43.8% | -15.5 | **57** ± 9 | 72 | +15 |
| 269 | Mickey Moniak | 418 | 39.1% | -16.3 | **55** ± 9 | 63 | +8 |

**2025** (266 qualified hitters)

| Rank | Player | PA | Chase% | Runs saved / 600 PA | xChase+ ± 1 SD | Chase+ | Luck |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | Gleyber Torres | 627 | 17.2% | +19.7 | **154** ± 7 | 148 | -5 |
| 2 | Juan Soto | 707 | 15.9% | +16.6 | **145** ± 8 | 139 | -6 |
| 3 | Geraldo Perdomo | 720 | 19.0% | +15.2 | **141** ± 7 | 141 | +0 |
| 4 | Bryson Stott | 563 | 23.4% | +15.0 | **141** ± 8 | 131 | -10 |
| 5 | Will Smith | 438 | 19.4% | +14.8 | **140** ± 9 | 136 | -4 |
| | ... | | | | | | |
| 262 | Pedro Pagés | 388 | 35.9% | -12.8 | **65** ± 10 | 74 | +8 |
| 263 | Jordan Walker | 394 | 34.1% | -13.7 | **63** ± 9 | 71 | +9 |
| 264 | Hunter Goodman | 577 | 36.9% | -14.3 | **61** ± 9 | 76 | +15 |
| 265 | Gabriel Arias | 470 | 39.0% | -14.4 | **61** ± 10 | 69 | +9 |
| 266 | Javier Báez | 435 | 46.2% | -15.7 | **57** ± 10 | 65 | +7 |

**2026** (261 qualified hitters)

| Rank | Player | PA | Chase% | Runs saved / 600 PA | xChase+ ± 1 SD | Chase+ | Luck |
|---:|---|---:|---:|---:|---|---:|---:|
| 1 | Taylor Ward | 606 | 15.0% | +23.3 | **154** ± 6 | 148 | -6 |
| 2 | Geraldo Perdomo | 681 | 20.6% | +21.2 | **149** ± 6 | 143 | -6 |
| 3 | Steven Kwan | 637 | 19.4% | +20.5 | **147** ± 6 | 147 | -1 |
| 4 | Gleyber Torres | 419 | 18.9% | +19.1 | **144** ± 8 | 137 | -7 |
| 5 | Miguel Vargas | 696 | 20.9% | +18.6 | **143** ± 7 | 140 | -3 |
| | ... | | | | | | |
| 257 | Colson Montgomery | 633 | 32.7% | -13.8 | **68** ± 7 | 67 | -1 |
| 258 | Jarren Duran | 607 | 34.5% | -14.1 | **67** ± 7 | 66 | -1 |
| 259 | Andrés Giménez | 503 | 44.1% | -14.2 | **67** ± 7 | 81 | +14 |
| 260 | Ezequiel Tovar | 508 | 43.7% | -14.9 | **66** ± 8 | 60 | -5 |
| 261 | Mickey Moniak | 435 | 44.1% | -19.9 | **54** ± 8 | 48 | -6 |

Luck is Chase+ minus xChase+. Hitters at the top of a list sorted by
xChase+ tend to have negative luck (and the bottom positive luck): that's
partly what put them at the extremes.

</details>

### What chase rate misses

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/xchase/figures/chase_plus_vs_chase_rate_dark.png">
  <img alt="xChase+ against chase rate for 2026, highlighting the ten hitters whose two rankings disagree most" src="results/xchase/figures/chase_plus_vs_chase_rate.png" width="720">
</picture>

Some hitters chase often but cheaply; some rarely chase but pay when they
do. The highlighted hitters are where the two rankings disagree most.
xChase+ correlates 0.30-0.34 with a hitter's xwOBA each season; chase
rate 0.23-0.30 (negative).

### Does it repeat?

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/xchase/figures/reliability_chase_vs_xchase_dark.png">
  <img alt="Year-to-year correlations averaged over five pairs of seasons: chase rate 0.85, xChase+ 0.73, the part of xChase+ chase rate doesn't explain 0.49, Chase+ 0.65, luck 0.03" src="results/xchase/figures/reliability_chase_vs_xchase.png" width="720">
</picture>

Yes. Over five pairs of seasons xChase+ repeats at r = 0.73, Chase+ at
0.65, luck at 0.03, so xChase+ is the main number. Chase rate repeats at
0.85 but only counts; the part of xChase+ it doesn't explain still
repeats at 0.49, and that part is what pricing adds.

### From a number to a plan: player decision cards

xChase+ says how many runs a hitter loses; a card says where and what to
do. Every qualified hitter since 2021 has one on
[the interactive page](https://samuelosullivan6-rgb.github.io/ChasePlus/results/xchase/player_cards/index.html),
with a season switcher and a Roster view
([`#roster`](https://samuelosullivan6-rgb.github.io/ChasePlus/results/xchase/player_cards/index.html#roster),
or `#roster/NYY`).

Start with the average right-handed hitter: his chase rate by spot, count
and pitcher hand. Everyone chases more with two strikes.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/xchase/player_cards/2026/reference/average_rhb_dark.png">
  <img alt="The average right-handed hitter's chase rate by location, count and pitcher hand, with a numbered guide to reading a player card" src="results/xchase/player_cards/2026/reference/average_rhb_light.png" width="900">
</picture>

A player card shows the difference from that baseline, red where he
swings more than average and blue where he takes more. Salvador Pérez,
255th of 261:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/xchase/noted_players/cards/salvador_perez_dark.png">
  <img alt="Salvador Pérez's 2026 decision card: red below and away from the zone in every count, with a plan, leaks, a count table and a season trend" src="results/xchase/noted_players/cards/salvador_perez_light.png" width="900">
</picture>

Top to bottom: the **header** names the problem (Pérez's choices cost
23.0 runs per 600 PA while his chases produce 7.2 more than average: the
choices, not the swing); the **zones** show where, around his own strike
zone from the catcher's view; the **leaks** are ranked by runs (worst:
two-strike breaking balls below the zone, chased 78% against 49%); the
**plan** is written to the player, one pitch per line, each take saying
how far off the zone those pitches were so "let it go" never means the
borderline pitch, a take before two strikes first because it costs no
strikeouts, ending "Keep swinging at strikes"; the **coach's note** says
where to point the camera, since a card says where, not why; the **count
table** says whether he struggles there; the **trend** says habit or
slump; and the **target** is the number to get under, since leak chasing
halves on its own.

**Does taking more pay?** Across 941 back-to-back season pairs, a
10-point cut in far-off chase rate came with +3.1 points of walk rate,
−1.7 of strikeout rate, +.022 xwOBA and −2.5 points of swings at strikes:
a small cost next to the gain.

### Checking the advice

**The count check (step 15)** looks at the count, not the pitch: a
hitter's xwOBA once a plate appearance reaches those counts, against the
league's in the same counts. Ahead-in-the-count performance beyond a
hitter's level barely repeats (r = 0.07); two-strike performance does
(0.53). Both are shrunk (DerSimonian-Laird), and ±10 points of xwOBA
marks *struggling* or *productive*.

**Does fixing a leak pay? (step 16)** For 756 season pairs and 1,194
half-season pairs, each hitter's card leaks are found in the first period
and watched in the next. Excess chasing in leaks halves on its own (15
points to 7), so everything is measured against that prediction. Per
10-point cut beyond predicted:

| Change | Season to season | First half to second |
|---|---:|---:|
| xChase+ | +4.9 ± 0.6 | +4.2 ± 0.5 |
| Offense, runs per 600 PA (xwOBA) | +1.4 ± 0.5 | +2.1 ± 0.4 |
| Walk rate | +0.8 pts | +0.5 pts |
| Strikeout rate | -0.1 pts | -0.3 pts |
| Swing rate at strikes | -0.5 pts | -0.3 pts |

Each run of choices recovered came back as 0.75 ± 0.31 (seasons) and
1.22 ± 0.27 (halves) runs of offense; 1 would mean the card's runs are
the runs a hitter gets back. The count check doesn't change the payoff,
so every leak stays in the plan.

**Limits.** Association, not an experiment. Season to season most of the
effect is hitters who chased *more* than predicted losing offense (−3.0
± 1.1 runs); those who cut more gained xChase+ but about broke even. So
the first promise is fewer wasted counts, not a better slash line.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/xchase/figures/leak_fix_direction_dark.png">
  <img alt="Every hitter pair's change in offense against how much more or less he chased in his leaks than predicted, season to season and half to half, with the cut-more, as-predicted and chased-more groups marked" src="results/xchase/figures/leak_fix_direction.png" width="720">
</picture>

**Frozen before 2027 (step 19).**
[`leak_predictions_2026.csv`](results/xchase/coaching/leak_predictions_2026.csv)
is a stamped pre-season prediction for every 2026 card's leaks (next =
−3.8 + 0.72 × 2026), the same line as each card's target; step 20
scores it after 2027.

**The loop, tested on four earlier pairs (step 20).** Each of 2022-2025
was frozen with a line fit only through that season and scored on the
next (`coaching/leak_predictions_<season>.csv`,
`leak_scores_<season>.csv`). The slope held in all four (b = 0.78-1.14),
the level in the two most recent; xChase+ and walks rose in every pair,
strikeouts didn't move, and offense was positive in all four, clearly in
two. Scored on the first half of 2026 alone (`--period h1`) the
predictions were again centered: a July check for the spring's cards.

### Using the cards

Start every session with the average hitter's card. Promise fewer wasted
counts, not a better line. Measure against the target, not the current
rate: 15 falling to 7 is regression, not the plan. The card says where,
not why. It is the far-off pitch, every time, because a two-strike take
of a borderline pitch is a called third strike. Start before two strikes.
The 17 noted hitters' cards and printable versions are in
[`results/xchase/noted_players/`](results/xchase/noted_players/README.md).

## How it works

1. **Price each chase.** Cost = the value of taking the pitch minus the
   value of what the swing produced, from that season's count run values.
   A per-season logistic called-strike model (distance, count, one curve
   per side of the zone) weighs ball against called strike. A ball in
   play is worth its outcome's league-average value (Chase+) or a
   straight-line fit from xwOBA to those values (xChase+); neither depends
   on runners or outs.
2. **Compare to the league** on the same season, count and distance.
3. **Shrink small samples** toward the season mean (DerSimonian-Laird).
4. **Put it on a 100 scale:**
   `xchase_plus = 100 + 100 * runs_saved_shrunk / league_chase_cost_per_600_pa`

Every season is computed on its own; 2026 is the first under MLB's ABS
Challenge System.

## Reading the leaderboard

`runs_saved_shrunk` ranks within a season (runs per 600 PA), `xchase_plus`
compares across seasons, `runs_saved_vs_anchor_shrunk` prices every
season against 2024; ± is `xchase_plus_posterior_sd` (7-10 points).
`results/xchase/` holds everything for xChase+, including `matchups/`,
`coaching/`, `player_cards/<season>/` and `noted_players/`;
`results/chase/` has the same leaderboard, reliability and chart files
for Chase+. Qualifying: 600
out-of-zone pitches and 300 PA, prorated in-season.

## Limitations

- **xwOBA only knows exit velocity and launch angle**, not spray
  direction or sprint speed; luck didn't repeat in any of the five pairs
  of seasons, so there's no sign that hurts anyone.
- **The xwOBA line is fit on chases only** (implied wOBA scale 1.15-1.21,
  at or a little below the usual 1.2-1.25).
- **Chase+ treats every out the same.**
- **Shrinkage is a little strong at the extremes** (7-8 points).
- **The called-strike model knows the side of the zone but not the
  pitch**: no pitch type, catcher, umpire or challenge.
- **2026 is measured against a shorter zone.** Statcast now records the
  ABS box set from height, 2.86 inches shorter than 2025's, while umpires
  kept calling the taller one. About 2.1 of the 2.6-point rise in chase
  rate is the box; rankings within 2026 are unaffected, but a 2026 trend
  point sits on a different box.

## Running it

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the scripts in order; steps 4-8 build Chase+, and rerun with
`--expected-contact` they build xChase+ into `results/xchase/`.

<details>
<summary>What each script does</summary>

| Step | Script | What it does |
|---|---|---|
| 1 | `scripts/01_download_baseline.py` | Downloads Statcast data by month with `pybaseball` into `data/raw/` |
| 2 | `scripts/02_build_chase_dataset.py` | Cleans and labels pitches (swing, zone, chase), keeps xwOBA |
| 3 | `scripts/03_build_run_value_tables.py` | Builds run expectancy, event and count run values |
| 4 | `scripts/04_build_chase_leaderboard.py` | Prices chases, fits the models, writes the leaderboards |
| 5 | `scripts/05_build_hitter_value_leaderboard.py` | Compares chase value with total offense |
| 6 | `scripts/06_build_chase_reliability.py` | Tests year-to-year repeatability |
| 7 | `scripts/07_check_chase_invariants.py` | Runs the consistency checks (below) |
| 8 | `scripts/08_make_figures.py` | Draws the charts and prints the README tables |
| 9 | `scripts/09_build_xchase_comparison.py` | Lines up Chase+ and xChase+, tests both against wOBA / xwOBA (needs step 4 both ways) |
| 10 | `scripts/10_make_xchase_figures.py` | Draws the two charts that compare them |
| 11 | `scripts/11_build_matchup_leaderboards.py` | xChase+ leaderboards by handedness matchup (needs step 4 with `--expected-contact`) |
| 12 | `scripts/12_build_coaching_profiles.py` | Splits the bottom 10 hitters' runs lost into decision and execution, by count, zone, pitch group and more, into `results/xchase/coaching/` (needs step 4 with `--expected-contact`) |
| 13 | `scripts/13_build_actionability_profiles.py` | Scores every qualified hitter on how much of the loss is swing decisions on far-off pitches, and sorts them into archetypes (needs step 4 with `--expected-contact`) |
| 14 | `scripts/14_test_take_advice.py` | Checks whether hitters who cut far-off chases from one season to the next walked more, struck out less and gained xwOBA, and what it cost in swings at strikes |
| 15 | `scripts/15_build_count_check.py` | The count check: each hitter's xwOBA once a plate appearance reaches each count group, against the league's in the same counts, shrunk for noise, and how much each part repeats (needs step 4 with `--expected-contact`) |
| 16 | `scripts/16_backtest_leak_fixes.py` | Finds every hitter's card leaks in one season or half and checks what happened when he cut them the next: xChase+, offense runs, walks, strikeouts and swings at strikes, and whether the count check changes the payoff (needs step 15) |
| 17 | `scripts/17_build_player_cards.py` | Draws a decision card for every qualified hitter in one season: the interactive page, with its roster view, and its pitches (`player_cards/<season>/`), the CSVs behind them with each hitter's team, the noted hitters' cards and report, and the average-hitter reference cards (needs steps 13, 15 and 16, and the raw files from step 01 for the teams; `--data-only` writes just the card data for an earlier season) |
| 18 | `scripts/18_make_terrain_figures.py` | Draws the same surfaces in 3D as still images: the average hitter's chase terrain by count, and one hitter's costliest panel (needs step 17) |
| 19 | `scripts/19_freeze_leak_predictions.py` | Writes down, before the 2027 season, a prediction for every 2026 card's leaks, for step 20 to score out of sample. Run once: a later run only checks the frozen file (needs steps 16 and 17). `--season <year> --retrospective` writes the same file for an earlier season (2022 to 2025), marked as not out of sample, to test the loop |
| 20 | `scripts/20_score_leak_predictions.py` | Scores a frozen file on the season that followed: is the actual leak chasing centered on the prediction, and did the frozen payoffs hold on the frozen cells? Run after the next season is in (needs step 19). `--period h1` scores the first half only, for a midseason check |
| 22 | `scripts/22_build_season_pages.py` | The card site for every season: runs step 17 per season, freezing an earlier season's targets first (step 19 `--retrospective`) when its frozen file is missing, so every page carries the same wording and the same season switcher (needs the inputs of step 17 for each season) |

</details>

```
python scripts/01_download_baseline.py
python scripts/02_build_chase_dataset.py
python scripts/03_build_run_value_tables.py

python scripts/04_build_chase_leaderboard.py
python scripts/05_build_hitter_value_leaderboard.py
python scripts/06_build_chase_reliability.py
python scripts/07_check_chase_invariants.py
python scripts/08_make_figures.py

python scripts/04_build_chase_leaderboard.py --expected-contact
python scripts/05_build_hitter_value_leaderboard.py --expected-contact
python scripts/06_build_chase_reliability.py --expected-contact
python scripts/07_check_chase_invariants.py --expected-contact
python scripts/08_make_figures.py --expected-contact

python scripts/09_build_xchase_comparison.py
python scripts/10_make_xchase_figures.py
python scripts/11_build_matchup_leaderboards.py
python scripts/12_build_coaching_profiles.py
python scripts/13_build_actionability_profiles.py
python scripts/14_test_take_advice.py
python scripts/15_build_count_check.py
python scripts/16_backtest_leak_fixes.py
python scripts/22_build_season_pages.py
python scripts/18_make_terrain_figures.py
```

Step 19 was run once before 2027; step 20 runs after 2027 is in. `data/`
is not committed; `results/` is, and GitHub Pages serves main as it is.

## Checks

`07_check_chase_invariants.py` rebuilds the key numbers from the pitch
level and runs 22 checks: league Chase+ is exactly 100, shrinkage never
overshoots, the called-strike rate never rises with distance, the
out-of-fold check doesn't leak, and the results on disk match the current
script and data. Step 17 tests every fact in the hand-written coach's
notes, and `scripts/plan_checks.py` tests every generated plan against
the numbers beside it; any failure stops the run and names the card.

## TrackMan files: the college path

The method ports to any league with pitch tracking once the numbers are
refit on its pitches. `scripts/college_build.py` does that for TrackMan
in about 15 seconds for a 60-game season:

```
python scripts/college_build.py --name clemson_2026 \
    --trackman college/clemson_2026/trackman --heights college/clemson_2026/heights.csv
```

It takes the season's per-pitch CSVs and a roster of heights (TrackMan
has no strike zone, so each hitter's is set from height as MLB's 2026
zone is) and refits run values, wOBA weights, xwOBA, the called-strike
model and the league baseline on the files alone. A round trip of every
MLB team's first 60 games of 2026
([results/trackman_roundtrip/](results/trackman_roundtrip/README.md))
landed 6.0 xChase+ points (RMSE) from the MLB build with the same top
leak for 92% of hitters. `college/<name>/` is gitignored, so no commit
can carry a team's data.

## Appendix: Chase+ vs xChase+

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="results/xchase/figures/chase_plus_vs_xchase_plus_dark.png">
  <img alt="Chase+ against xChase+ for 2026, r = 0.93, with the five hitters the results flattered most and the five they hurt most" src="results/xchase/figures/chase_plus_vs_xchase_plus.png" width="720">
</picture>

They mostly agree (r = 0.91-0.95). Luck has an SD of 5.8-7.3 points and
doesn't repeat; 12-20 hitters a season (4.5-7.1%) sit 2 standard errors
from zero (`regression_candidates.csv`), against about 4.6% by chance
alone, and only 2022 and 2023 (6.4% and 7.1%) run clearly above that.
Same season,
xChase+ tracks xwOBA better than Chase+ tracks wOBA; next season, once
this year's xwOBA and chase rate are known, neither adds anything.
xChase+ is a real, repeatable part of a hitter's approach, not a hidden
predictor of production.

## Appendix: xChase+ by matchup

The same priced pitches split by batter/pitcher hand, one board per
matchup per season. 100 on a board is the average hitter in that
matchup, not the league, so a board score and the overall score beside
it are on different baselines. On the overall scale, hitters chase worse
against same-handed pitchers (average 93-99) and better against
opposite-handed ones (102-107), every season. Boards against righties repeat about like overall xChase+ (R/R
0.74); boards against lefties rest on a quarter of the pitches and are
noisier (L/L 0.44).

<details>
<summary>2026 top 5 and bottom 5 on each board</summary>

**R/R** (101 qualified hitters)

| Rank | Player | Bats | PA | Chase% | xChase+ ± 1 SD | Overall xChase+ |
|---:|---|:---:|---:|---:|---|---:|
| 1 | Taylor Ward | R | 414 | 14.0% | **160** ± 8 | 154 |
| 2 | Miguel Vargas | R | 491 | 21.0% | **146** ± 9 | 143 |
| 3 | Gleyber Torres | R | 292 | 21.4% | **142** ± 9 | 144 |
| 4 | Isaac Paredes | R | 500 | 25.9% | **136** ± 8 | 126 |
| 5 | Gabriel Moreno | R | 403 | 28.1% | **136** ± 10 | 133 |
| | ... | | | | | |
| 97 | Salvador Pérez | R | 453 | 44.2% | **73** ± 10 | 72 |
| 98 | Trea Turner | R | 466 | 37.4% | **72** ± 9 | 77 |
| 99 | Ezequiel Tovar | R | 338 | 45.2% | **71** ± 10 | 66 |
| 100 | Jeremy Peña | R | 370 | 39.8% | **71** ± 9 | 76 |
| 101 | Oswald Peraza | R | 230 | 40.0% | **69** ± 11 | 75 |

**L/L** (81 qualified hitters)

| Rank | Player | Bats | PA | Chase% | xChase+ ± 1 SD | Overall xChase+ |
|---:|---|:---:|---:|---:|---|---:|
| 1 | J. P. Crawford | L | 159 | 18.7% | **143** ± 12 | 135 |
| 2 | Steven Kwan | L | 204 | 19.9% | **138** ± 10 | 147 |
| 3 | Jonathan Aranda | L | 188 | 24.9% | **137** ± 11 | 130 |
| 4 | JJ Wetherholt | L | 218 | 21.9% | **130** ± 11 | 126 |
| 5 | Wilyer Abreu | L | 218 | 27.3% | **130** ± 12 | 112 |
| | ... | | | | | |
| 77 | Daylen Lile | L | 182 | 42.2% | **77** ± 12 | 90 |
| 78 | Brandon Lowe | L | 209 | 40.5% | **76** ± 12 | 84 |
| 79 | Brandon Marsh | L | 130 | 42.3% | **73** ± 13 | 83 |
| 80 | Jac Caglianone | L | 169 | 46.8% | **65** ± 12 | 77 |
| 81 | Andrés Giménez | L | 141 | 45.9% | **55** ± 11 | 67 |

**R/L** (182 qualified hitters)

| Rank | Player | Bats | PA | Chase% | xChase+ ± 1 SD | Overall xChase+ |
|---:|---|:---:|---:|---:|---|---:|
| 1 | Gleyber Torres | R | 127 | 14.0% | **147** ± 12 | 144 |
| 2 | Taylor Ward | R | 192 | 17.2% | **144** ± 9 | 154 |
| 3 | Seiya Suzuki | R | 165 | 18.4% | **143** ± 14 | 124 |
| 4 | Miguel Vargas | R | 205 | 20.5% | **138** ± 11 | 143 |
| 5 | Junior Caminero | R | 187 | 25.6% | **138** ± 15 | 105 |
| | ... | | | | | |
| 178 | Brenton Doyle | R | 97 | 36.5% | **72** ± 15 | - |
| 179 | Hunter Goodman | R | 185 | 40.3% | **70** ± 14 | 78 |
| 180 | Ozzie Albies | S | 260 | 44.5% | **68** ± 11 | 82 |
| 181 | Brooks Lee | S | 206 | 36.9% | **66** ± 12 | 83 |
| 182 | Colby Thomas | R | 104 | 40.6% | **61** ± 14 | - |

**L/R** (161 qualified hitters)

| Rank | Player | Bats | PA | Chase% | xChase+ ± 1 SD | Overall xChase+ |
|---:|---|:---:|---:|---:|---|---:|
| 1 | Steven Kwan | L | 433 | 19.2% | **145** ± 7 | 147 |
| 2 | Geraldo Perdomo | S | 481 | 20.2% | **145** ± 7 | 149 |
| 3 | Trent Grisham | L | 349 | 19.0% | **135** ± 8 | 133 |
| 4 | Kevin McGonigle | L | 501 | 19.1% | **134** ± 7 | 130 |
| 5 | Juan Soto | L | 306 | 19.0% | **132** ± 10 | 130 |
| | ... | | | | | |
| 157 | Spencer Jones | L | 229 | 35.7% | **68** ± 12 | - |
| 158 | Colson Montgomery | L | 438 | 32.7% | **62** ± 8 | 68 |
| 159 | Luke Raley | L | 257 | 34.4% | **61** ± 9 | - |
| 160 | Jarren Duran | L | 465 | 35.2% | **60** ± 8 | 67 |
| 161 | Mickey Moniak | L | 344 | 43.6% | **57** ± 9 | 54 |

</details>

Full boards: `results/xchase/matchups/`.

## Version history

- **xChase+ 1.1, Chase+ 2.0.** Balls in play priced context neutral
  (league-average outcome value instead of RE24). xChase+ barely moved
  (r = 0.999 with 1.0); Chase+ moved more (r = 0.95). Luck is now contact
  luck only.
- **xChase+ 1.0, Chase+ 1.0.** First release.

## Use of AI

AI tools (Claude) were used for code cleanup, refactoring, review and the
chart script, checked against the invariant tests and by comparing
outputs before and after on the same data.

## License

Code is MIT (see `LICENSE`). Statcast data is the property of MLB
Advanced Media and is not covered by this license.
