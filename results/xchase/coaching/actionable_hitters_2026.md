# Which 2026 chase losses look coachable

Built from `scripts/13_build_actionability_profiles.py`. The bottom-10
write-up (`bottom10_2026_coaching_notes.md`) asks where the worst hitters
lose their runs. This one asks a different question across all 261
qualified hitters: whose loss comes from decisions that could plausibly
be changed, and how much would come back if they were?

All numbers are runs per 600 PA against the league baseline for the same
season, count and distance bucket, so they are the same units as the
`runs_saved_shrunk` column of the leaderboard (before shrinkage).

## How "coachable" is measured

Every out-of-zone pitch's runs saved is split into two parts that add
back exactly:

- **Decision**: what the swing/take choice was worth if the hitter's
  chases had turned out like a league-average chase on that kind of
  pitch. This is swing frequency.
- **Execution**: on a chase, how much better or worse it turned out than
  the league's chases there. Whiffing more, or hitting it harder.

Then each decision is classed by how obvious the take was:

| Class | Pitch | Why it matters |
|---|---|---|
| A | fewer than 2 strikes, at least 0.35 ft off the plate | no called-strike risk, no protect-the-plate instinct; the clearest "just take it" |
| B | 2 strikes, at least 0.35 ft off the plate | a recognition failure; the called-strike model gives the take little risk |
| C | 3 balls, borderline or just off | the take almost always wins the count |
| D | borderline or just off, 0-2 strikes | close calls; nobody takes these reliably |

**Far-off recoverable** is the decision loss in A and B with the sign
flipped: the runs a hitter would have saved by chasing far-off pitches at
the league rate, nothing else changing. Class D is deliberately left out,
because "stop swinging at borderline pitches" is not an adjustment anyone
can make on demand.

A hitter is **decision-only** when he loses 8+ decision runs and his
execution is at least league average (within 1 run). His chases turn out
fine. He just takes too many of them.

League reference, 2026: chase rate 30%, far-off chase rate 16% with fewer
than two strikes and 30% with two, whiff rate on chases 42%, xwOBA on
chased balls in play .294.

## The subset

Of the 41 qualified hitters losing 8+ runs per 600 PA, 18 are
decision-only, 7 decision-led, 10 execution-led and 6 mixed. The
decision-only group is the subset where an approach change is most likely
to pay, because there is nothing wrong with the swing. Within it, these
nine combine the biggest far-off loss with evidence the pattern is real:

| Player | xChase+ | Decision | Execution | Far-off recoverable | xChase+ if fixed | Far-off chase rate by season (2K) | Note |
|---|---:|---:|---:|---:|---:|---|---|
| Salvador Pérez | 73 | -23.3 | +7.8 | 16.9 | 112 | .48 / .37 / .34 / .38 | four straight seasons of 15-22 far-off runs lost |
| Michael Harris II | 78 | -21.8 | +9.0 | 16.8 | 116 | .42 / .42 / .48 / .50 | best execution in the group; far-off loss has grown every year |
| Ernie Clement | 74 | -17.4 | +3.2 | 13.8 | 105 | .50 / .44 / .55 | lowest whiff rate on chases in the group (23%) |
| Angel Martínez | 87 | -17.8 | +9.3 | 12.6 | 116 | .48 / .47 | two seasons, same pattern |
| Ceddanne Rafaela | 86 | -16.6 | +8.5 | 12.2 | 113 | .42 / .36 / .46 | three seasons at 10-16 far-off runs lost |
| José Caballero | 79 | -13.5 | +1.4 | 11.7 | 105 | .36 / .29 / .47 | was +1.2 on far-off pitches in 2025 (xChase+ 109); the 2026 loss is all two-strike |
| Ozzie Albies | 82 | -13.3 | +3.6 | 8.5 | 101 | .37 / .29 / .35 / .39 | worst year of four; all of it below the zone |
| Luis García | 86 | -14.9 | +5.9 | 8.4 | 105 | .31 / .34 / .35 / .36 | loss is two cells: fastballs up, and 3-ball counts |
| Hunter Goodman | 78 | -14.8 | +1.2 | 10.0 | 101 | .35 / .35 | two seasons, 9-10 far-off runs each |

Rookies in the same archetype with no history yet, so the pattern can't
be called persistent: Samuel Basallo (12.2 recoverable), Jac Caglianone
(11.4), Cole Carrigg (8.7), Konnor Griffin (6.8). Worth tracking, not yet
worth a verdict.

"xChase+ if fixed" is an upper bound. It assumes the hitter takes far-off
pitches at exactly the league rate with no cost anywhere else, and the
decision/execution split uses league-average chase outcomes per cell, so
a hitter who chases pitches he can handle will look slightly better on
execution than he is.

## What is not in the subset, and why

- **Execution-led hitters** (Jarren Duran, Colson Montgomery, Kyle
  Stowers, Christian Walker, Owen Caissie, Coby Mayo). Their chase rates
  are near league but they whiff on 53-68% of chases against 42%. Taking
  more pitches would help a little (2-5 recoverable runs each), but the
  loss is bat-to-ball, which is a different and slower conversation.
- **Decision-led hitters at the very bottom** (Mickey Moniak, Ezequiel
  Tovar, Zach Neto, Andrés Giménez, Jeremy Peña). Their far-off loss is
  as large as the subset's (10-13.5 runs), but their execution is also
  negative and the loss is spread across every count, pitch group and
  side of the zone. There is no single pattern to drill; it is a general
  discipline problem. They are the bottom-10 write-up's subject.
- **Mixed hitters** losing 8-11 runs (Trea Turner, Brandon Lowe, Ty
  France, Royce Lewis). Nothing concentrated enough to name.

## Per-player draft notes

Cells are strikes x pitch group x side of the zone missed, far-off pitches
only. "Excess" is how many more chases the hitter took than the league
would have on the same pitches.

**Salvador Pérez.** 78% of his far-off loss is breaking and offspeed below
the zone, and it starts early: 37-39% chase on 0- and 1-strike breaking
balls down-and-away against 14-20% league (22 excess chases, -2.6 runs),
then 69% on 2-strike breaking balls down against 47% (12 excess, -3.9).
He also chases 22% of 0-0 far-off pitches against 11% and 57% of 3-ball
out-of-zone pitches against 36% (-2.9 runs). His chases produce +7.8
execution runs, so the swing is fine. Draft: take the first pitch unless
it's a fastball, and treat any spin below the knees before two strikes as
an automatic take. He has done this before; his far-off chase rate with
fewer than two strikes has sat at 31-34% for four years, so this is the
baseline, not a slump.

**Michael Harris II.** The loss is the most concentrated in the group:
-8.9 of -16.8 far-off runs come with two strikes against right-handers,
and -5.0 from one cell, 2-strike breaking balls straight down (76% chase
vs 47%, 15 excess). Sliders and curves at 80-86 mph. His chases are the
best in the group (+9.0 execution; .32 xwOBA on chased balls in play), so
a chase that stays in the zone-ish is not the problem. Draft: a 2-strike
breaking ball that starts at the knees from a right-hander is a take.
Nothing else needs to change; his early-count far-off chase (29%) is high
too but costs a third as much.

**Ernie Clement.** Two cells: fastballs above the zone (2-strike 78% chase
vs 39%; 0-strike 37% vs 14%; 31 excess chases, -4.3 runs) and changeups
below with one strike (67% vs 33%, -1.3). He chases 23% of 0-0 far-off
pitches against 11% and 62% of 2-strike far-off pitches from lefties
against 30%. He whiffs on only 23% of chases, so most of these become
weak contact rather than strikeouts, which is why execution is positive
and the loss is still real. Draft: the high fastball is the whole
conversation. A 95 mph fastball at the letters or above is a ball he
turns into a pop-up or a foul; lay off it with fewer than two strikes and
spit on it with two.

**Angel Martínez.** -6.7 of -12.6 far-off runs come with two strikes
against right-handers, nearly all below the zone: breaking (70% vs 47%),
offspeed (64% vs 39%) and breaking down-and-in (77% vs 24%). Execution
+9.3 (he fouls these off and puts them in play at .34 xwOBA), so the
contact is there. Draft: same as Harris, from the other side. Two
strikes, right-hander, anything soft that starts at the knees, take it.

**Ceddanne Rafaela.** Fastballs up: 2-strike 55% chase vs 39% (11
excess, -3.5), 1-strike 50% vs 24% (10 excess, -1.0). Mostly 95 mph
four-seamers. Secondary: 2-strike breaking balls away (71% vs 32%). He
has improved: far-off early-count chase went 35% to 28% to 27% over three
seasons and 2024's far-off loss was -15.8. Draft: the high heater with
two strikes is where to spend the attention; 2026 was his best early-count
year so leave that alone.

**José Caballero.** The cleanest case in the group. With fewer than two
strikes he is a league-average taker (far-off chase 16%, decision +0.3).
With two strikes he chases 47% of far-off pitches against 30%, and 37 of
48 fastballs above the zone (77% vs 39%, 19 excess chases, -4.9 runs, the
single worst cell for any hitter in the group). In 2025 his far-off
decision runs were +1.2 and his xChase+ 109. Draft: this is one pitch
with two strikes. A fastball above the belt that he has to reach up for
is a ball. It was not a take in 2025 either: he chased 65% of the
far-off ones that year (55% in 2024), so his good 2025 came from
elsewhere, and this pitch has gotten worse every season.

**Ozzie Albies.** Everything is below the zone and most of it is soft:
2-strike splitters/changeups down (70% vs 39%), 2-strike breaking balls
down (73% vs 47%), and the same pitches earlier (0- and 1-strike offspeed
and breaking down, 61-65% vs 26-39%). The loss is heavier from lefties
(-5.8 of -8.5 far-off runs on a third of the pitches). Draft: a changeup
or splitter that disappears below the knees from a left-hander is the
pitch, every count.

**Luis García.** Two unrelated leaks. High fastballs: 2-strike 90% chase
vs 39% (18 of 20) and 0-strike 60% vs 14% (18 of 30), -4.3 runs together.
Then 3-ball counts: 58% chase on out-of-zone pitches against 36%, -4.4
runs (class C, not counted in far-off recoverable, so his real
recoverable total is nearer 12). His execution is +5.9, so he can hit the
high fastball; the 3-ball swings are the free runs. Draft: with three
balls, a swing has to be at a strike. Full stop.

**Hunter Goodman.** Spread more evenly than the others: fastballs up
(0-strike 37% vs 14%, 1-strike 50% vs 24%, 21 excess, -2.4) and breaking
balls down with one strike (65% vs 39%, -1.9). He chases 23% of 0-0
far-off pitches against 11%. Execution is only +1.2 and his whiff rate on
chases (50%) is above league, so he is the weakest fit here. Draft: the
0-0 and 1-strike high fastball is the free part; the two-strike breaking
ball may be a contact issue as much as a decision one.

## Reading the files

- `actionability_<season>.csv`: one row per qualified hitter, with the
  decision/execution split, the A-D class totals, far-off recoverable, the
  implied xChase+ and the archetype.
- `far_off_cells_<season>.csv`: for every hitter losing 5+ runs, each
  strikes x pitch group x zone-miss cell on far-off pitches, with the
  league chase rate in the same cell and excess chases.
- `far_off_history.csv`: far-off chase rates and decision runs by season,
  for checking whether a hitter's pattern persists.
- `league_reference.csv`: the league rates quoted above, by season.
