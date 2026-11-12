# Methodology review, 2026-11-12

Scope: the method, math and code behind xChase+ / Chase+ and the coaching
layer, reviewed at commit 263d692 (local main level with origin/main) plus
the uncommitted step 22 pitch-mix check and README edit. The website, card
pictures and prose were out of scope. Every number here was recomputed from
the committed CSVs or the pitch parquet unless marked "from the code".

## Verdict in one paragraph

The pricing core is sound, carefully checked and reproducible: the cost
identity is right, every season stands alone, the called-strike model is
monotone and calibrated out of fold, the DerSimonian-Laird shrinkage and
posterior SD are correct, the 22 invariants pass on the current data, and
every README figure I tested reproduces. The two weak points are not bugs
but framing. First, xChase+ is mostly chase rate: chase rate explains
57-71% of its variance each season, and the increment that pricing adds
repeats at 0.49 and is partly the pitch mix a hitter was shown (5-8 points
between the 10th and 90th percentile after the within-hitter correction).
Second, the coaching validation table leads with outcomes that are
mechanically tied to the fix (xChase+, walk rate, far-off chase rate); the
one real outcome, offense runs, is positive but small and, as the README
says, comes mostly from hitters who chased more getting worse. There is a
credible use case, but it is the card-and-port layer for programs without
an analytics staff, not a new MLB leaderboard stat.

## What was verified

- Local main is level with origin/main (0 ahead, 0 behind). Uncommitted:
  README limitation paragraph, `scripts/22_check_pitch_mix_confound.py`,
  its three outputs.
- `07_check_chase_invariants.py --expected-contact`: 22 of 22 pass.
- Year-to-year r of xChase+ by pair (hitters qualified both years,
  n = 181-192): 0.70, 0.76, 0.75, 0.72, 0.70 (README says 0.73 average).
  Chase rate 0.84-0.86. Unshrunk and shrunk r are identical to two decimals
  because shrinkage is nearly uniform (median factor 0.17-0.21).
- r(chase rate, xChase+) by season: -0.81, -0.80, -0.84, -0.76, -0.79,
  -0.78 (R² 0.57-0.71).
- Opportunities per PA correlate only 0.12-0.28 with xChase+; runs saved
  per opportunity correlates 0.996-0.997. The score is per-pitch skill, not
  volume.
- Between-hitter SD of xChase+ 16.5-19.9; median posterior SD 8.0-9.1.
  Implied single-season reliability about 0.74, consistent with the 0.73.
- 2025 chase cost by distance bucket: borderline 22.6% of chases, 12.4% of
  cost, 11% of between-hitter variance in runs saved; just off + clearly
  off 69% of cost. Mean P(called strike) on borderline chases 0.27; on the
  other three buckets 0.07, 0.005, 0.000.
- Called-strike model out of fold (grouped by game): log loss 0.098-0.138,
  within 0.0002 of in-sample, AUC 0.94-0.95, calibration slope 0.994-0.997.
- Backtest: xChase+ moves 2.66 ± 0.39 points per run of leak choices
  recovered; the season scale is 2.66-2.84 points per run. The payoff is
  the identity.
- Frozen-line scoring: actual minus predicted leak excess +2.1 ± 0.7
  (2022->2023), +2.3 ± 0.7 (2023->2024), +0.0 ± 0.7, -0.6 ± 0.7 points.
- Backtest pairs: median 48 period-2 pitches in the leak cells (5th
  percentile 13); mean binomial variance of the period-2 rate is 57% of
  var(fix) over all pairs.

## Findings, ranked

### A. Method

1. **The counterfactual for a chase is estimated from a selected sample.**
   The called-strike model is fit on takes and applied to swings
   (`04:1100-1130, 1771-1795`). Pitches hitters swing at look more like
   strikes than pitches they take at the same distance, so P(called
   strike) is understated on chased pitches and value_if_taken overstated.
   This matters only where P is material: the borderline bucket, 12% of
   cost and 11% of between-hitter variance. Bounded, but unstated. The
   corollary is that the 47-coefficient side-of-zone model moves the
   median hitter 0.3 points (commit c3b3a35); the pricing is dominated by
   count leverage on pitches that are balls with near certainty.

2. **xChase+ is mostly chase rate.** R² 0.57-0.71 within season. The README
   is honest about the residual (repeats 0.49) and the modest xwOBA
   correlation gain (0.30-0.34 vs 0.23-0.30). The pitch-mix check now shows
   part of that residual is what a hitter was shown. State plainly that the
   increment over chase rate is real but modest.

3. **Pitch-mix confound (step 22, uncommitted).** Cross-section r = -0.36
   with non-fastball share; within-hitter slope 24-32% of the
   cross-sectional one; conclusion "about 5 points, inside a card's ±".
   The within-hitter design is biased in both directions, not one: same-half
   targeting inflates it (the md says so), but lagged targeting (a chase in
   an odd game draws more breaking balls in the next, even game) attenuates
   it toward zero, so it is an estimate, not a ceiling. Pooled -4.8 ± 1.5
   gives roughly -2 to -8; 2026 alone -7.9 ± 3.5. "About 5, possibly 8" is
   what the numbers support. The 2026 ratios (0.57, 0.82) are high because
   the cross-sectional slope shrank under the ABS box, not because the
   within slope grew; say that instead of "0.8 SE from pooled". SEs are
   classical OLS on heteroskedastic differences (`22:513-528`); use
   HC-robust or pitch-weighted. "Beyond baseline" is a rate while step 04's
   baseline is a cost (rate x cost per chase), so a whiffier pitch group
   with the same chase rate is a confound the proxy cannot see.

4. **Coaching payoff table mixes identities with outcomes.** xChase+, walk
   rate and far-off chase rate are built from the same swings as the fix;
   only offense runs (xwOBA over all PA) is independent. The real finding
   is +1.4 ± 0.5 runs per 600 PA per 10-point cut beyond expected (season
   pairs), +2.1 ± 0.4 (halves), with the season effect driven by the
   chased-more group (-3.0 ± 1.1) while the cut-more group about broke
   even. The README says the last part; it should also drop xChase+ and
   BB% from the "payoff" framing or label them as accounting.

5. **About half the fix variable is coin-flip noise.** Median 48 period-2
   pitches in the leak cells; binomial variance of the period-2 rate is
   ~57% of var(fix). Slopes on offense are attenuated (conservative), but
   the "cut more than expected" group is roughly half luck, and pairs with
   13 pitches get the same weight as pairs with 200 (`16:90, 257`). Use
   weighted LS or a higher floor.

6. **The frozen-line tests are data-out-of-sample, design-in-sample.**
   Leak rules (12 pitches, 0.75 runs, top 3), cell definitions and the
   side-of-zone model were set with all six seasons in hand; the four
   retrospective freezes test the regression-to-mean line, not the method.
   Two of four missed the level by ~3 SE. The README's "the level in the
   two most recent" is accurate but soft. There is no pre-registered
   pass/fail criterion for 2027; write one now (e.g. |actual - predicted| <
   1.5 points, slope in 0.8-1.2, offense payoff > 0 at 1 SE).

7. **Step 14 is weaker than step 16 and presented alike.** Change-on-change
   OLS with only the period-1 chase rate as control (`14:129-133`): no
   control for the outcome's own period-1 level, so shared regression to
   the mean inflates +.022 xwOBA. Classical SEs with ~330 hitters repeated
   across 941 pairs. Also sums x_value over PA ends including
   woba_denom = 0 rows where step 16 filters them (`14:81-90` vs
   `leak_rules.py:160`).

8. **Survivorship, unstated.** Every pair analysis uses hitters qualified in
   both periods (181-192 of 250-280). Direction is probably conservative
   for reliability and ambiguous for the backtest.

9. **Luck "clearly above chance" is overstated.** 6.4% and 7.1% vs 4.55%
   with n = 267/280 is 1.4-1.9 SE; luck_z SD 0.98-1.09 says an 8% SE
   understatement explains it.

10. **Shrinkage target is the qualified pool (103-105), not 100.** Documented
    in the diagnostics; fine, but say it in the README's "How it works".

### B. Bugs (small, real)

- `09:702-710`: candidates are selected on raw luck z but labelled from
  shrunk luck; the two differ in sign on 149 of 1,594 hitter-seasons.
  Brandon Belt 2021 is listed "rise" with luck -2.8 and z +2.13.
- `05:675-702`: correlates runs_saved_shrunk with offense that contains
  the same chased balls in play (step 09 excludes them at 812-849); and
  races shrunk chase value against unshrunk chase rate.
- `13:216-233`: decision_share is NaN when runs_saved >= 0, so every
  above-average hitter is archetype "mixed"; `13:223` adds unshrunk
  recoverable runs to shrunk xChase+; "league" reference rates are over
  qualified hitters only.
- `11:70`: THIN_CELL_WARNING_PITCHES = 50 hard-coded while step 04 has
  200 and step 11 reads other settings by ast.
- `04` by-count calibration rows are in-sample and tautological: a logistic
  model with count dummies matches each count's rate by construction.

### C. Code and engineering

- Monolithic module-level scripts: step 04 is 3,952 lines with 35
  functions and the main flow at top level; step 17 is 3,076 lines. Nothing
  is importable, so there are no unit tests; the invariant scripts are
  integration checks that mostly recompute the same arithmetic (the
  substantive ones: monotone curves, strike worse than ball every count,
  shrinkage ordering, grouped out-of-fold with calibration bounds).
- Cross-script settings read by `ast` (07, 11, 22 reading 04 and 13) keep
  constants in sync but are brittle; a shared settings module would do it.
- Geometry constant 0.83 ft defined in 02, 04, 12 and 13 separately.
- `college_method.py` is a copy of steps 03 and 04 verified identical by
  the round trip; a maintenance fork that will drift the next time 04
  changes.
- 302 MB of results committed; fine for GitHub Pages, heavy for clones.
- Done well: run fingerprints on every output, hard failures on every data
  gap, per-season isolation, the luck SE built from the league rather than
  the hitter's own balls, clustered SEs and both period-1 levels controlled
  in the backtest, frozen files that refuse to overwrite, and `claim()`
  guards that stop the markdown from printing wording its numbers no longer
  support.

## Is there a credible use case?

Prior art: Baseball Savant publishes Swing/Take run values by attack zone,
and swing-decision models (selective-aggression metrics and team-internal
pitch-level models) exist. "Price chases by count in runs" is not new. What
this project adds: a baseline for which pitches a hitter was shown, xwOBA
pricing of contact to separate luck, shrinkage with an honest posterior SD,
a leak-and-plan layer with a pre-registered prediction, and a TrackMan port
that reproduces the MLB build to 6 xChase+ points RMSE.

- **MLB front offices**: no. They have pitch-level swing-decision models
  with pitch type, movement and location probability as inputs; this is a
  coarser version without those inputs.
- **Public leaderboard stat**: marginal. Chase rate already carries most of
  it, the cross-season scale moves with the ABS box, and the pitch-mix
  dependence means a score partly reflects pitches seen.
- **College, independent and lower-minors programs with TrackMan and no
  analytics staff**: yes, this is the credible case. The product is the
  card (where, in which count, how far off) plus a validated target, built
  in 15 seconds from their own files, with MLB-scale evidence that the
  advice is at least not harmful and that leak chasing regresses on its own
  so the target is set against that. The honest promise, as the README
  says, is fewer wasted counts rather than a better slash line.
- **Portfolio or publication**: strong, provided the framing changes above
  are made; the self-critical checks (confound, frozen predictions,
  invariants) are the most persuasive part.

## Recommended order of fixes

1. Reframe the validation table around offense runs; mark xChase+, BB% and
   far-off chase rate as accounting.
2. Pre-register the 2027 pass criterion in step 19/20 and the README.
3. Add pitch group (or pitch group x pitcher hand) to the baseline cells, or
   fit a pitch-quality chase model, and report xChase+ both ways.
4. Weighted LS or a 25-pitch floor in step 16; robust SEs in steps 14 and
   22; control the outcome's period-1 level in step 14.
5. Fix the 09 label, 05 double counting, 13 archetype NaN and unshrunk mix.
6. State survivorship and the selected-sample counterfactual in Limitations.
7. Refactor step 04's flow into functions with a pytest on a synthetic
   season; merge the geometry constant and the college copy.

## Addendum: what was done the same day

Every item above was acted on; main xChase+ / Chase+ numbers did not move
(largest change in any hitter-season 0.0), and 22 of 22 invariants pass
for both runs.

- **Shared module.** `scripts/chase_model.py` now holds the zone geometry
  (0.83 ft edge, ball radius), the pitch groups, the side-of-zone
  called-strike model and DerSimonian-Laird; steps 02, 04, 12, 13, the
  card surfaces, the TrackMan adapter and `college_method.py` import it,
  and `tests/test_chase_model.py` (15 unittest cases on a synthetic
  season) covers it. Step 07 reads shared settings from it and includes
  it in the run fingerprint. This also fixed a drift the review missed:
  the college path still carried the pre-October-23 model (one free
  spline, no side of the zone), so the round trip's "reproduces step 04
  exactly" had been false since that commit.
- **Pitch-group baseline (step 04).** A second baseline on season x
  count x distance x pitch group is computed beside the main one
  (`xchase_plus_pitch_group`, `pitch_group_baseline_comparison.csv`). It
  moves hitters by an SD of 1.5-1.8 points, largest 8, r = 0.995 with the
  main number: the confound is real, modest, and now measured directly.
- **Bugs.** Step 09 labels candidates from raw luck (Belt 2021 now
  "fall"). Step 05 excludes PAs ending on chased balls in play from the
  offense side (Chase+'s correlation falls from .33 to .27) and races
  unshrunk against unshrunk. Step 13 gives above-average hitters their own
  archetype (815 hitter-seasons out of "mixed"), shrinks recoverable runs
  before adding them to shrunk xChase+ (Báez 2021 fixed-if 125 to 103),
  and computes league reference rates over all hitters; the card
  template's Problem filter carries the new label. Step 11 reads the
  thin-cell constant from step 04. Step 06 pairs consecutive seasons only.
- **Statistics.** Step 14 controls the outcome's first-season level,
  clusters SEs by hitter, uses step 16's in-wOBA denominator (it had
  overstated xwOBA by 2.5 points on average), and reports with and
  without the 2025-26 pair (+3.1 BB, −1.5 K, +.021 xwOBA, −2.7 zone
  swings; +3.5, −1.4, +.022, −3.0 without). Step 16 adds pitch-weighted
  payoff rows, a noise-share row (50% season, 60% half) and a
  measure_type column separating accounting (xChase+, BB%, far-off rate)
  from outcomes. Step 22 uses HC1 robust SEs and says "about 5, possibly
  8", with the lagged-targeting and rate-vs-cost caveats.
- **Pre-registration.** Step 20 carries a fixed 2027 pass criterion
  (level within 1.5 points or 2 SE; slope's 1 SE band reaches 0.8-1.2;
  offense payoff positive at 1 SE) and prints a verdict. Held to it, one
  of the four retrospective seasons passes (2025 on 2026); the two
  earliest miss the level, two miss the payoff at 1 SE; the 2026 first
  half passes all three. Step 20 no longer refuses a frozen file whose
  line differs from the current refit (step 19 holds frozen predictions
  fixed through pricing changes by design); it reports the gap.
- **README.** Validation table reframed around offense with the
  accounting rows marked; survivorship, the takes-to-swings
  counterfactual, the chase-rate share, the shrink target, the luck
  wording, the step 14 and step 20 results and the criterion stated.
