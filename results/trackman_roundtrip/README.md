# The college path, tested on MLB data

Written by `scripts/trackman_roundtrip.py`. The college path
(`scripts/college_build.py`) turns a college team's TrackMan files into
xChase+ and decision cards. There is no college data here to test it on,
so this test makes some: 2026 Statcast games written out as TrackMan game
CSVs, with only what a TrackMan file carries (no strike zone, no runners
on base, no xwOBA, no score; PlateLocSide mirrored). Each team's first
60 games is about 17,500 pitches, a college season's worth. The
college build runs on those files exactly as it would on a college
team's, and its numbers are compared with the MLB build's for the same
pitches. KC is shown in detail; the round trip ran on all 30 teams,
296 qualified hitters in all.

These are MLB data, so this folder is committed. The college builds the
test makes live in `college/`, which is not.

## 1. The college method reproduces steps 03 and 04

`scripts/college_method.py` is the college path's copy of steps 03 and 04,
with the settings a small league needs passed in. Given step 03's and step
04's own settings, on every 2026 pitch, it gives their numbers back. The
test stops if it ever does not, so every difference further down is a
choice the college path makes, not a slip in copying.

| Check, all 2026 MLB pitches | Largest difference |
|---|---:|
| count run values | 8.3e-17 |
| event run values | 8.3e-17 |
| called_strike_rate | 0 |
| chase_cost | 2.2e-16 |
| expected_cost_per_pitch | 4.2e-17 |
| runs_saved | 4.4e-16 |
| xChase+ | 2.8e-14 |
| pitches priced (college method / step 04) | 0 |
| qualified hitters (college method / step 04) | 0 |

## 2. Settings for a league of 17,500 pitches

Each team's first 60 games of 2026 (17,199 to 18,338 pitches: the team
and its opponents) was priced as a league of its own: its own run values,
xwOBA, called-strike model and baseline, with the college floors (100 PA,
200 out-of-zone pitches). Each of the 296 qualified hitters (the
team's own; an opponent never reaches 100 PA in 60 games) is compared with
the MLB build's price of the same pitches, against the whole league. The
question for each setting: how far from the MLB build does a college-sized
league put a hitter's raw runs saved?

| League baseline cells | Runs per 600 PA from the MLB build (RMSE) | Same, step 03's count values | Correlation | xChase+ points (RMSE) |
|---|---:|---:|---:|---:|
| **12 counts x 4 buckets (MLB)** | 3.25 | 3.26 | 0.956 | 6.8 |
| 12 counts x 3 buckets | 3.39 | 3.40 | 0.952 | 7.1 |
| 12 counts x 2 buckets | 3.40 | 3.41 | 0.952 | 7.1 |
| 12 counts, no buckets | 3.49 | 3.49 | 0.949 | 7.2 |
| 4 count groups x 4 buckets | 4.21 | 4.16 | 0.923 | 9.0 |
| 4 count groups x 2 buckets | 4.28 | 4.24 | 0.921 | 9.2 |

A college season is small, so the obvious move is coarser cells. They came
out worse, not better, so the college path keeps step 04's: 12 counts x 4 distance buckets, 48 cells of
about 190 pitches each at this size. Merging the buckets lets a pitch
nowhere near the zone share a baseline with one just off it, and the
four count groups put a 3-1 chase (expensive) with a 1-0 one (cheap);
both biases cost more than a 190-pitch cell's noise. Averaging the result's
run value over the counts (the college choice) or each plate appearance's
own (step 03's) makes no difference here.

| Spread between hitters fit on | Hitters in the fit (median) | Talent SD, xChase+ points (median) | Error predicting the next 100 games | Gap to the MLB build, same pitches |
|---|---:|---:|---:|---:|
| qualified only | 10 | 18.4 | 10.32 | 2.91 |
| 20+ out-of-zone pitches | 124 | 27.2 | 10.33 | 2.81 |
| 40+ out-of-zone pitches | 36 | 21.9 | 10.14 | 2.64 |
| 80+ out-of-zone pitches | 14 | 19.5 | 10.20 | 2.81 |
| 150+ out-of-zone pitches | 12 | 18.8 | 10.23 | 2.83 |
| no shrinkage (raw slice) |  |  | 11.31 | 5.01 |
| MLB build on the same pitches, its own prior |  |  | 10.02 | 0.00 |

Shrinkage, priced with the chosen settings. Step 04 fits the spread
between hitters on its qualified hitters; a slice has about ten, so the
college path fits it on everyone in the files with 40 or more out-of-zone
pitches (a median of 36 a slice, the opponents included) and shrinks
toward their average. Each choice is scored on how well the slice predicts the same
hitter's raw runs saved over the team's next 100 games (priced by the MLB
build), and on how close it comes to the MLB build's own shrunk number for
the same pitches. 40 does best on both, and predicts the next 100 games
nearly as well as the MLB build does with the whole league behind it (the
last row): a college-sized league loses little.

## 3. The round trip

Each team's 60 games written as TrackMan CSVs (`scripts/statcast_to_trackman.py`,
one file per game, PlateLocSide mirrored so the adapter must read the
sign off the files), a heights roster read back off the 2026 zones, and
`college_build.py` run on them: the adapter, step 02, the college pricing,
steps 13 and 15, and step 17's card page. Every number in this section
comes from what that build wrote.

### What the adapter rebuilt

|  | KC | All 30 teams |
|---|---:|---:|
| PlateLocSide's sign, read off the hit-by-pitches | mirrored, found | 30 of 30 found |
| Pitches read as a decision the same way as step 02 on Statcast | 100.00% | 100.00% to 100.00% |
| Inside or outside the zone the same way as Savant | 99.90% | 99.78% to 99.92% |
| Zone top and bottom from the heights roster, largest gap | 0.003 in | up to 0.009 in |
| Plate appearance results in the same group | 100.00% | 100.00% to 100.00% |
| Runners on base exactly right, start of each plate appearance | 92.2% | 89.6% to 93.9% |
| Runner on first / second / third right | 97.3% / 93.8% / 95.0% | 96.8% / 93.8% / 95.0% (average) |
| Score before every pitch right | 100.00% | 100.00% to 100.00% |
| College xwOBA against Savant's, same batted balls (correlation) | 0.966 | 0.951 to 0.977 |

The adapter finds what TrackMan does not carry. The sign of PlateLocSide
comes from the hit-by-pitches, which are inside by definition. The
zones come from the roster's heights, and they match Savant's to a few
thousandths of an inch (the roster lists heights to a hundredth of an
inch). The runners on base are rebuilt play by play from the result, the
outs and the runs scored. They are exactly right at the start of 90% to 94%
of plate appearances (the range over the 30 teams); a wrong base is mostly
a runner who took an extra base on a hit, moved up on an out or stole a
base, none of which a TrackMan row records. Run values built on the rebuilt
bases come out as close to the MLB build's as run values built on the true
ones. The college xwOBA (the average of the 20 to 50 nearest batted balls
in the files, the number chosen by cross-validation in each build) tracks
Savant's closely without using it. The wOBA weights the build fits
from the files' own run values come out near Savant's (medians across the
teams: walk 0.76, hit by pitch 0.79, single 0.90, double 1.24, triple 1.62, home run 2.01; Savant's are 0.70, 0.70, 0.90, 1.25, 1.60 and 2.00).

### Pitch by pitch

| Per pitch | Pitches | College mean | MLB build mean | Correlation | Correlation, all 30 teams |
|---|---:|---:|---:|---:|---:|
| called-strike chance if taken | 9,063 | +0.0479 | +0.0484 | 0.965 | 0.971 |
| value if taken | 9,063 | +0.0389 | +0.0441 | 0.991 | 0.984 |
| value of the swing (chases) | 2,650 | -0.0897 | -0.0806 | 0.964 | 0.962 |
| chase cost (chases) | 2,650 | +0.1172 | +0.1159 | 0.967 | 0.962 |
| the league's expected cost (baseline) | 9,063 | +0.0343 | +0.0364 | 0.970 | 0.955 |
| runs saved | 9,063 | +0.0000 | +0.0025 | 0.968 | 0.967 |

Every out-of-zone pitch the two builds both price, side by side. The
college build's league is the team and its opponents in 60 games, so its
called-strike model, run values and baseline are fit on 2% of the MLB
build's pitches; each pitch's price still follows the MLB build's closely.

### The hitters: KC

| Hitter | PA | xChase+, college build | MLB build, same pitches | MLB build, full season | Top leak, college card | Top leak, MLB build, same pitches |
|---|---:|---:|---:|---:|---|---|
| Lane Thomas | 130 | **137** ± 13 | 137 | 126 | ahead, fastballs above | ahead, fastballs above |
| Isaac Collins | 193 | **114** ± 10 | 113 | 118 | two strikes, breaking balls below | two strikes, breaking balls below |
| Maikel García | 246 | **111** ± 10 | 112 | 116 | two strikes, fastballs above | two strikes, fastballs above |
| Vinnie Pasquantino | 246 | **104** ± 11 | 110 | 113 | two strikes, fastballs above | two strikes, fastballs above |
| Carter Jensen | 200 | **93** ± 12 | 95 | 102 | two strikes, breaking balls below | two strikes, breaking balls below |
| Bobby Witt | 264 | **84** ± 10 | 96 | 105 | two strikes, breaking balls below | two strikes, breaking balls below |
| Salvador Pérez | 238 | **80** ± 13 | 94 | 73 | two strikes, breaking balls below | two strikes, breaking balls below |
| Michael Massey | 125 | **80** ± 14 | 90 | 93 | two strikes, breaking balls below | two strikes, breaking balls below |
| Jac Caglianone | 200 | **78** ± 11 | 89 | 78 | two strikes, breaking balls below | two strikes, breaking balls below |
| Kyle Isbel | 165 | **70** ± 11 | 74 |  | two strikes, breaking balls below | two strikes, breaking balls below |

Across all 30 teams, the college build's xChase+ is 6.0 points from
the MLB build's on the same pitches (RMSE; correlation 0.95; 90% of
hitters within 10 points, the largest gap 20). Of that, 4.1 points
(RMSE) is a shift every hitter on a team shares (see where the
differences come from, below), and 4.4 is left within a team. So the
college build orders each team's hitters nearly as the MLB build does:
rank correlation 0.95 within a team, on average. Before shrinkage the two
are 3.3 runs per 600 PA apart (correlation 0.95). The two also shrink
a little differently, the MLB build toward its qualified hitters and the
college build toward the average of everyone in its files with 40 or more
out-of-zone pitches, which moves the college number -0.8 points on
average.

Two checks on what the gap means. Against each hitter's MLB card for the
full season (162 games, a bigger and different sample), the college
xChase+ correlates 0.80, and the MLB build's for the same 60 games
0.84. Predicting the same hitters' raw runs saved over the team's
next 100 games, the college build is off by 8.5 runs per 600 PA (RMSE)
and the MLB build on the same 60 games by 8.5. Most of the distance
to the full season is the 60-game sample, which a college season has too;
the college pricing adds little to it. KC, shown above, is 7.8 points from the MLB build (RMSE; the 30 teams run from 1.7 to 9.9). Pérez, Witt and Caglianone come out 11-14 points lower than on the MLB build: about 51% of their raw gap is the shift KC's hitters share (the league), and about 44% their contact on chases, which the college xwOBA values differently from Savant's.

### Leaks

| Leaks, college card against the MLB build on the same pitches | All 30 teams |
|---|---:|
| Hitters with a leak on both | 218 of 296 |
| Hitters with no leak on either | 50 |
| A leak on one only (college / MLB build) | 11 / 17 |
| Same top leak, of those with a leak on both | 92% |
| College top leak among the MLB build's three, same | 97% |
| Leaks the two lists share, of up to three, same | 1.9 |
| Leaks per card, college / MLB build | 1.6 / 1.6 |

A card's leaks are its three costliest spots where the hitter chases more
than the league would on the same pitches, by step 17's own rule, and the
college card's come from step 17 itself, run on the college build. The MLB
build's for the same pitches are rebuilt here with step 17's per-pitch
expectation and labels from the 2026 page (that rebuild reproduces the MLB
cards' leaks for 100% of 261 hitters over the full season). The two
agree on whether a hitter has a leak at all for 268 of 296. Of the
218 both find one for, the college card names the same top leak as the
MLB build on the same pitches for 92%, and its top leak is among the
MLB build's three for 97%. How much a leak moves with the sample: for hitters with a
full-season MLB card, the college top leak is among the full season's three
for 74% and the MLB build's 60-game top leak for 72%.
Sixty games is a small sample for a leak, whoever prices it; the college
pricing adds little to that.

### Where the differences come from

| Priced with | Runs per 600 PA from the MLB build (RMSE) | Shared by the team | Within the team |
|---|---:|---:|---:|
| the college build as it is | 3.33 | 2.48 | 2.22 |
| the college build with the MLB build's run values (step 03's tables) | 2.98 | 2.43 | 1.73 |
| the college build with the MLB build's expected contact (Savant's xwOBA and its line to runs) | 2.93 | 2.58 | 1.38 |
| the college build with the MLB build's called-strike chance | 3.33 | 2.47 | 2.23 |
| the college build with all three: every pitch priced as the MLB build prices it, against the 60 games' own league | 2.64 | 2.54 | 0.73 |
| ...and against the whole MLB league's baseline: the MLB build | 0.36 | 0.11 | 0.35 |

Each hitter's raw runs saved per 600 PA, priced again with ingredients
taken from the MLB build: run values, expected contact and the
called-strike chance, each on its own and then all three. Each time the
league baseline is recomputed from the 60 games' pitches at the new prices,
because a baseline is the league's average price and means nothing next to
costs priced another way. The last row adds the whole league's baseline on
top, and that is the MLB build itself; what is left (0.36 runs) is the
0.1% of pitches whose zone call differs. Each gap is split into its team's
average gap, one number shared by every hitter on the team, and what is
left within the team.

The two parts have different causes. The part a team shares is the
league. Priced exactly as the MLB build prices them, a team's hitters
still sit 2.54 runs above or below the MLB build together, until the
baseline is the whole league's (0.11). Sixty games of one team are a
different league from all 30 teams: half its plate appearances are the
team's own hitters, and a 190-pitch cell has noise of its own. A shift
every hitter on a team shares does not change which of them chases most,
or where, so the order of a team's hitters and their leaks come through it
(above). The part within a team is the pricing: 2.22 runs as built,
0.73 with all three ingredients from the MLB build. Expected contact
matters most (the college xwOBA is fit on about 3,000 batted balls; with
Savant's, the within-team gap is 1.38), then the run values (1.73);
the called-strike model makes no difference (2.23).

In college the part a team shares is the point, not a flaw. A Clemson
hitter is measured against the pitchers and hitters in Clemson's games,
not against a league he never sees.

## What the round trip cannot test

- **How a TrackMan operator records a play.** The files here were written
  from Statcast, so every play is recorded the way the adapter expects. A
  real file can differ: foul tips may or may not be marked, a bunt may or
  may not be tagged, an out on the bases may be on the pitch or between
  pitches, and some rows may be blank. The adapter reads the outs from the
  Outs column rather than trusting OutsOnPlay, treats a pitch with no call
  or type as no decision, and reports what it filled in (BUILD.md); the
  first real files should be read with that report open.
- **PlateLocSide's sign.** Found from the files' hit-by-pitches in both
  directions here (the round trip writes it mirrored; written unmirrored,
  the adapter reads +1). A real season has plenty of hit batters; with
  fewer than ten, it stops and asks.
- **College batted balls and umpires.** The xwOBA, run values and
  called-strike model are refit on the files, so they follow metal bats and
  college umpires whatever those do. What the round trip shows is that the
  fits work on 17,500 pitches; it cannot show what they look like on college
  pitches.
- **Missing exit speeds.** Statcast tracks every ball in play; TrackMan
  misses some. A ball with no exit speed gets its hit type's average value.
  How many there are is in BUILD.md.
- **The schedule.** Here the opponents are a cross-section of MLB. A
  college team's are its schedule: a weak midweek opponent and a strong
  conference one are in the same league baseline, which is the league the
  team's hitters actually faced.
- **The card's footer.** "Does fixing a leak pay?" quotes the MLB backtest
  (step 16 needs back-to-back seasons). A college card says the same until
  there are two college seasons to test it on.

## Files

| File | What it is |
|---|---|
| `parity.csv` | Part 1: the college method against steps 03 and 04 |
| `settings_study_baselines.csv`, `settings_study_hitters.csv` | Part 2: each baseline and count-value choice, summed up and hitter by hitter |
| `settings_study_shrinkage.csv`, `settings_study_shrinkage_hitters.csv` | Part 2: each shrinkage pool |
| `adapter_fidelity.csv`, `woba_weights.csv` | Part 3: what the adapter rebuilt and the wOBA weights each build fit, by team |
| `pitches.csv` | Part 3: per-pitch prices, KC and all teams |
| `hitters.csv` | Part 3: every qualified hitter, the college build next to the MLB build |
| `decomposition.csv` | Part 3: every hitter priced with each ingredient swapped |
| `leaks.csv` | Part 3: every hitter's leaks, the college card, the MLB build on the same pitches and the full season |
| `leak_rebuild_check.csv` | The check on the MLB leaks rebuilt for the comparison |

Rerun it all with `python scripts/trackman_roundtrip.py` (about 15
minutes; `--skip-study` keeps the last settings study, `--teams KC NYY`
limits the round trips). KC's college build stays in
`college/roundtrip_KC/`, cards page included.
