# Where the 2026 bottom 10 lose their runs, and what a coach could do about it

Built from `scripts/12_build_coaching_profiles.py`. Every number is runs per
600 PA against the league baseline (same season, count and distance bucket),
so "-5.5 on pitches below the zone" means that is what those pitches cost
this hitter beyond what the league loses on the same pitches.

Each hitter's loss is split into two parts that add up exactly:

- **Decision**: what his swing/take choices cost if every chase had turned
  out like a league-average chase on that kind of pitch. This is the
  "swings at balls the league takes" part.
- **Execution**: what his chases cost beyond that, because he whiffs or
  makes weak contact more (or less) than the league does when it chases.

The tables behind this are in `bottom10_2026_summary.csv` (one row per
hitter), `bottom10_2026_by_dimension.csv` (count, distance, zone, pitch
group, hand, swing result), `bottom10_2026_cells.csv` (strikes x pitch
group x zone miss, worst cells first) and `bottom10_2026_history.csv`
(the same splits for 2024 and 2025).

## What the group has in common

Pooled over all ten, the runs lost come from:

| Split | Share of runs lost |
|---|---:|
| Decision / execution | 83% / 17% |
| 2 strikes / 1 strike / 0 strikes | 48% / 31% / 22% |
| Breaking balls / offspeed / fastballs | 62% / 22% / 16% |
| Straight below the zone / down-and-away / up | 48% / 16% / 20% |
| vs RHP / vs LHP | 78% / 22% |

Three things fall out of that:

1. **Eight of the ten are decision problems.** They swing at pitches the
   league takes, and when they do chase, the result is about what the
   league gets. The fix is a take, not a swing change.
2. **Two are execution problems** (Montgomery, Duran). Their chase rates
   are barely above league, but they whiff on 60-68% of chases against a
   league 43%. For them the lever is different: a chase is worth less to
   them than to the league, so their take threshold should be stricter
   than league norms, especially with two strikes.
3. **The pitch straight below the zone is the single biggest leak**, and
   it is almost pure decision (-73 of the -153 pooled runs; execution on
   those pitches is zero). Down-and-away gets more attention in scouting
   reports, but for this group it is a third the size.

A note on which cells to coach. The league itself chases 56% of two-strike
breaking balls below the zone, so a hitter at 70% there is 14 points over.
The same hitter at 50% on 0-1 breaking balls below the zone, against a
league 32%, is 18 points over, and those early takes cost nothing in
strikeouts. Several of the cheapest fixes below are early-count takes, not
two-strike ones.

## Two archetypes

| Archetype | Hitters | Signature |
|---|---|---|
| Volume chaser, league-average results | Tovar, Pérez, Clement, Giménez, Neto, Peraza, Peña, Moniak | decision -13 to -23; execution between -3 and +8 |
| Normal chase rate, can't make contact on a chase | Montgomery, Duran | decision -4 to -7; execution -10 to -13; whiff on chase 60-68% |

Pérez and Clement are worth a special note: their execution is *positive*
(+7.8 and +3.2). When they chase, they do better than the league. Their
entire loss is volume. Coaching them to stop chasing where they do damage
would be a mistake; the targets below start with the spots where they both
over-swing and get nothing for it.

## Hitter by hitter

Ordered worst to best. "Repeats?" compares with 2024 and 2025.

### 1. Mickey Moniak (xChase+ 55, -25.0 runs)

- Chases 44% of out-of-zone pitches (league 30.5%). Decision -18.5,
  execution -6.5.
- Two separate leaks: pitches below the zone (-11.7, chases 55% vs 39%)
  and fastballs above it (-7.1, chases 56% vs 36%).
- The high fastball is an early-count problem: with 0 strikes he chases
  47% of them against a league 23%. The low breaking ball is a two-strike
  problem: 71% chase vs 56%, and he whiffs on 57% of two-strike chases
  (league 39%).
- One-ball counts are where it adds up (-11.4): he swings at 53% of
  out-of-zone pitches in 1-0, 1-1 and 1-2 against a league 34%.
- Repeats? Yes. xChase+ 54, 77, 55 over 2024-26. Chase rate below the zone
  51%, 48%, 55%; above it 47%, 44%, 56%.
- **Draft adjustment:** split it in two. Early in counts, take the fastball
  above the letters; that alone is -2 to -3 runs with no strikeout cost.
  With two strikes, the low breaking ball is both a decision and a contact
  problem, so the realistic goal is the chase rate, not the whiff: get the
  71% down to league. The combined two-strike cells below the zone and
  fastball up are -8.4.

### 2. Ezequiel Tovar (xChase+ 66, -19.2 runs)

- Almost entirely decision (-18.2 vs execution -1.0). Breaking balls
  -13.6, offspeed -5.2, fastballs 0.
- The whole problem is soft stuff below the zone: he chases 69% of pitches
  straight below the zone (league 39%) and 40% of down-and-away (league
  21%). Those two zones are -14.6 of the -19.2.
- With two strikes he swings at 87% of breaking balls below the zone
  (40 of 46). On 3-2 he chases 64% vs 46%, -3.9 in only 44 pitches.
- First pitch: 30.5% chase vs 17.4%, -3.8 over 249 pitches.
- Repeats? Yes. xChase+ 57, 79, 66. Chase rate below the zone 59%, 50%,
  69%; on breaking balls 51%, 50%, 53% against a league 31-33% every year.
  Worst pitch group was "breaking" all three seasons.
- **Draft adjustment:** one rule, not several: anything that starts at the
  knees and is still dropping is a take, in every count. He has no fastball
  problem (+0.4 decision on fastballs), so a "sit hard, spit spin below the
  zone" plan does not cost him anything up top. Two cheap places to start
  are 0-0 (-3.8) and 3-2 (-3.9), where the league rarely chases and the
  3-2 chase is the most expensive one in the game.

### 3. Andrés Giménez (xChase+ 67, -17.3 runs)

- Decision -14.9, execution -2.5. Chases 44% vs 30.5%.
- Not one spot. Fastballs -6.8 (chases 42% vs 27%), breaking -7.6. Up
  -5.7, down -4.9, in -3.4, away -2.5.
- One-strike counts are the hole: -9.3, chasing 51.5% vs 32%. The worst
  single count is 0-1 (-4.8, 52% vs 31%). He is treating 0-1 like 0-2.
- With two strikes he chases 77% of fastballs above the zone (league 52%).
- Contact on chases is weak: .221 xwOBA on chased balls in play (league
  .288), the lowest of the ten.
- Repeats? **No.** xChase+ 95, 105, 67. Chase rate 38%, 35%, 44%. The
  2026 expansion is across every zone and pitch type (up 45/43/49, down
  36/38/45, breaking 41/32/47). In 2025 he was an above-average chase
  decision-maker.
- **Draft adjustment:** this is the one hitter where "get back to your
  2025 approach" is a real plan rather than a platitude, because the
  evidence says the skill exists. The specific target is 0-1 and 1-1: he
  gave back -7.7 in those two counts, and in 2025 his one-strike chase
  rate was far lower. Before any mechanical work, the question is what
  changed in 2026 (role, injury, a conscious decision to be more
  aggressive early).

### 4. Jarren Duran (xChase+ 68, -16.9 runs)

- **Execution hitter.** Chase rate 34.5% is barely above league, but
  decision is only -6.7 and execution is -10.2.
- He whiffs on 59.5% of chases (league 43%) and 63% of two-strike chases
  (league 39%). Two-strike counts are 61% of the loss (-10.3), and almost
  all of that is execution (-8.7).
- vs RHP -15.4 of the -16.9. Fastballs -4.4 (all execution: he misses the
  chased four-seamer up), breaking -8.0.
- Repeats? Yes, and getting worse. xChase+ 81, 82, 68. Execution -6.5,
  -4.8, -10.2. Whiff rate on chases 47%, 54%, 60%.
- **Draft adjustment:** his chase swing is a full swing that misses, so
  the league's two-strike norms do not apply to him. Where the league
  chases 56% of two-strike breaking balls below the zone and whiffs 39%,
  he chases 52% and whiffs far more; for a hitter like that the break-even
  swing rate is much lower than the league's. Two options, not exclusive:
  (a) a stricter two-strike take line on anything below the knees from
  RHP, accepting some called third strikes; (b) a two-strike contact
  swing. Option (a) is the one this data can price: the two-strike cells
  below the zone and fastball up are -9.7 combined.

### 5. Colson Montgomery (xChase+ 68, -16.6 runs)

- **Execution hitter, the most extreme of the ten.** Chase rate 32.7% vs
  30.5%. Decision -3.6, execution -13.0.
- He whiffs on 68% of chases (league 43%) and puts only 10% in play
  (league 24%). With two strikes he actually chases *less* than the league
  (37% vs 41%, decision +1.6) but the execution there is -11.8.
- Pitches below the zone are -12.7 (chases 46% vs 39%). Chased
  four-seamers are -4.3 of execution on their own.
- The one decision leak is early: 0-strike chase rate 27% vs 19% (-3.4).
- Repeats? Only one prior partial season (2025, not qualified), where the
  whiff rate on chases was already 59%.
- **Draft adjustment:** this is a bat-to-ball problem on pitches below the
  zone, and the stat can't say whether that is swing path, pitch
  recognition or timing. What it can say: a chase is close to a guaranteed
  strike for him, so (a) the early-count chases are more expensive for him
  than the decision number suggests because they lead to two-strike counts
  where his whiff bites, and (b) his two-strike take line should be
  stricter than league norms, as with Duran. The first lever is the cheap
  one: take the 0-strike pitch below the zone.

### 6. Zach Neto (xChase+ 71, -15.9 runs)

- Decision -13.1, execution -2.7. Fastballs are fine (+2.7). Breaking
  balls are -14.7 (chases 43% vs 33%) on a huge volume: 686 out-of-zone
  breaking balls in 697 PA. Pitchers have found it.
- Straight below the zone: -11.7, chasing 50% vs 39% over 441 pitches.
  Sliders alone -7.1.
- Two strikes are 63% of the loss. Two-strike breaking balls below the
  zone: 69.5% chase vs 56%; down-and-away 43% vs 26%.
- Whiffs on 54% of chases (league 43%), so there is a contact component on
  the slider too.
- Repeats? Trending the wrong way. xChase+ 100, 79, 71. Chase rate below
  the zone 38%, 38%, 50%; on breaking balls 35%, 33%, 43%. In 2024 he was
  league average at this.
- **Draft adjustment:** right-handed slider below the zone, period. His
  fastball decisions are a strength, so this is a "sit fastball, take
  anything that breaks below the knees" plan, and the 2024 numbers say he
  could do it. The two-strike breaking-ball cells below the zone and
  down-and-away are -9.5 together.

### 7. Salvador Pérez (xChase+ 73, -15.5 runs)

- Decision -23.3, the worst of the ten, offset by execution +7.8, the best
  of the ten. He chases 45% (602 chases) and does better than the league
  when he does: 27% in play (league 24%), fewer whiffs, .290 xwOBA on
  chased balls in play.
- The loss is pure volume: away -5.5 (chases 55% vs 28%, 90 excess
  chases), down -5.2 (65% vs 39%), down-and-away -5.1. Breaking balls -9.3.
- Every count contributes; 0-0 alone is -2.4 (29% vs 17% over 318
  pitches).
- Repeats? Completely. xChase+ 82, 73, 73. Decision -24, -22, -23;
  execution +14, +8, +8 in each of the three seasons.
- **Draft adjustment:** start with early-count breaking balls away, where
  he over-swings and gets nothing: 0-strike breaking balls away (51% chase
  vs 13.5%), 0-strike down-and-away (36% vs 17%), 1-strike away (66% vs
  30%). Those three cells are about -5 runs and none of them risks a
  strikeout. The two-strike breaking ball below the zone is the next step:
  he chases 78% of them, and his good contact (+2.75) offsets only part of
  the choice cost (-4.65), so it is still about -1.9 on net. At 36 the
  volume approach is not changing wholesale; the early-count away pitch is
  the cheapest part to fix.

### 8. Ernie Clement (xChase+ 74, -14.1 runs)

- Decision -17.4, execution +3.2. Contact hitter: whiffs on only 23% of
  chases (league 43%) and puts 43% in play (league 24%), but weakly (.235
  xwOBA, league .288). Two strikes are only 15% of his loss because he
  rarely strikes out on a chase.
- The leak is fastballs above the zone, early: fastballs -9.1 (chases 44%
  vs 27%, 85 excess chases), up -5.75 (55% vs 36%). With 0 strikes he
  chases 41% of fastballs above the zone (league 23%); with 1 strike 73%
  (league 40%). 1-1 is his worst count (-3.9, 57.5% vs 34%).
- Repeats? Yes. xChase+ 85, 93, 74. "Up" was his worst zone in all three
  seasons (chase rate 63%, 50%, 55% vs a league 30-36%); fastballs were
  the worst pitch group in 2024 and 2026. 2025, his best year, was the one
  where he chased the high fastball least.
- **Draft adjustment:** take the fastball above the letters with fewer
  than two strikes. He puts it in play, which is why it never looks like a
  mistake, but at .235 xwOBA it is a weak out that cost him a hitter's
  count. The 0- and 1-strike fastball-up cells are -4.6; add the 0-strike
  fastball in (-1.4) and the early-count fastball leak is about -6.

### 9. Oswald Peraza (xChase+ 76, -14.9 runs, 367 PA)

- Decision -13.8, execution -1.0. Smallest sample of the ten.
- Two strikes are 76% of the loss (-11.3). Below the zone -9.1,
  down-and-away -6.2. Breaking -10.6, offspeed -5.3, fastballs +1.1. Away
  is actually +4.3: his chased pitches away produced (.352 xwOBA on chased
  balls in play).
- Three-ball counts: 62% chase vs 36%, -5.2 over 45 pitches, including
  8 of 10 on 3-1. Those are the most expensive chases there are.
- Two-strike breaking balls below the zone 69% vs 56%; down-and-away 45%
  vs 26%; whiffs on 52% of two-strike chases.
- Repeats? Only a 2025 partial (472 out-of-zone pitches, not qualified).
  His two-strike chase rate then was below league (33%), so the two-strike
  pattern may be a 2026 thing; whiff rate on chases was 56% then too.
- **Draft adjustment:** cheapest first: with three balls, nothing below
  the knees is a swing. That is -5 in 45 pitches. Then the two-strike soft
  stuff down and down-and-away (-9.7 across the three cells). Leave the
  pitch away alone; it is where he does damage. Flag the sample size on
  anything beyond the three-ball rule.

### 10. Jeremy Peña (xChase+ 76, -14.6 runs)

- Decision -12.7, execution -1.9. Fastballs are a plus (+4.4, execution
  +6.2: he hurts the chased fastball). Breaking balls are -16.9 (chases 48%
  vs 33%), both decision (-9.6) and execution (-7.3). Sliders alone -8.6.
- Above the zone he chases 61% (league 36%) but his execution there is
  +5.4, so the high fastball nets out to about zero. Do not coach that
  away.
- The leaks: RHP breaking balls away and down-and-away with two strikes
  (84% chase vs 47% on breaking balls away; 34% vs 26% down-and-away with
  whiffs, -8.6 for the two cells), and the first pitch (-4.1, 32% vs 17%
  over 227 pitches). vs RHP -14.2; vs LHP -0.5.
- Repeats? Yes. xChase+ 72, 85, 76. Breaking balls were the worst pitch
  group all three years (-10.7, -8.1, -16.9) at a 44-48% chase rate
  against a league 31-33%.
- **Draft adjustment:** two rules. One, the first pitch: he chases 0-0 at
  almost double the league rate for -4.1, and a 0-0 take costs nothing.
  Two, the two-strike slider away from a right-hander: 27 of 32 swings on
  breaking balls away with two strikes is a pattern a pitcher can plan an
  at-bat around. His aggression up in the zone is fine and should stay.

## Caveats

- These are decision-level patterns. The data cannot see swing mechanics,
  pitch recognition, or a team's two-strike philosophy, and a "take"
  recommendation assumes the hitter can tell the pitch from a strike. The
  decision number already prices the called strikes that takes would
  produce (through the called-strike model), so it is a fair ceiling on
  what a take rule could recover, not a promise.
- A cell's runs are the sum of a few dozen to a few hundred pitches; cells
  under about 30 pitches are listed for completeness but should not drive
  a plan on their own (Peraza's 3-1 count, Montgomery's two-strike
  breaking ball in).
- Shrinkage is not applied to any of the splits here; they are raw sums,
  scaled to 600 PA. The headline xChase+ for each hitter is shrunk and so
  will look a little less extreme than the raw runs.
- 2026 is under the ABS challenge system and Statcast's zone boundaries
  differ from earlier years, so the year-over-year chase rates in the
  history file are compared against each season's own league rate.
