# Does xChase+ depend on the pitches a hitter was shown?

Qualified hitter-seasons, 2021-2026 (1594 in all), from `scripts/22_check_pitch_mix_confound.py`. xChase+ prices chases against the league on the same season, count and distance bucket, but not the same pitch type. This asks how much of a hitter's xChase+ follows from the kind of off-zone pitches he happened to see.

## The finding

Pooled over the six seasons (each centred on its own season), the share of breaking and offspeed pitches a hitter saw off the zone correlates -0.36 with his xChase+ (by season: -0.25, -0.40, -0.42, -0.41, -0.36, -0.28) and -0.26 with the part of xChase+ chase rate does not explain. Read as a straight line, a hitter at the 90th percentile of non-fastball share sits 16.0 points below one at the 10th, in xChase+ points.

The league's chase rate on the cells he saw (pitch group x distance bucket x count x pitcher hand, each cell rated without his own pitches) correlates +0.20 with xChase+ and +0.03 with the residual; the 90th percentile hitter in that rate sits 8.9 points above the 10th. Most of that is count and distance, which the baseline already removes: the part of the cell rate beyond step 04's count x distance cell correlates -0.27 with xChase+ (by season: -0.19, -0.29, -0.34, -0.34, -0.26, -0.19), -0.25 with the residual, and puts the 90th percentile hitter 12.1 points below the 10th. One caveat on that proxy: it is a chase rate, while step 04's baseline is a chase cost (the rate times the cost of a chase, with the called-strike model pricing the take), so a pitch group with the same chase rate as its count x distance cell but costlier chases (more whiffs, weaker contact) is a confound the proxy cannot see.

Mean distance outside the zone correlates -0.42 with xChase+ (the 90th percentile hitter 18.8 points below the 10th) and mean release speed +0.36 (16.4 points above). All the proxies fit at once reach a multiple correlation of 0.49 with xChase+ (adjusted R² = 0.24) and a 10th to 90th percentile spread of 22.5 points in the fitted value, 7.3 points of the residual. For scale, xChase+ has a standard deviation of about 18 points across qualified hitters in a season, and each card's ± is 7-10 points.

These are ceilings on the confound, not the confound itself, because two other things put the same relation in a cross-section. Targeting: pitchers choose what to throw, so a hitter who chases breaking balls is shown more of them off the plate, and part of any relation is his own habit being targeted. Hitter type: strikeout-prone hitters both see more breaking balls and chase more, so the share marks the kind of hitter he is as much as the pitches he was shown. A pitch-quality baseline would remove all three.

## Pooled, by proxy

| Proxy | Units | Mean | 10th-90th pct | r with xChase+ | r with chase rate | r with residual | Spread, xChase+ points | Spread, residual points |
|---|---|---|---|---|---|---|---|---|
| non_fastball_share | % of off-zone pitches | 49.9 | 44.2 to 55.8 | -0.36 | +0.25 | -0.26 | -16.0 | -7.1 |
| breaking_share | % of off-zone pitches | 33.4 | 26.9 to 39.7 | -0.32 | +0.26 | -0.18 | -14.8 | -4.9 |
| offspeed_share | % of off-zone pitches | 16.5 | 11.0 to 23.1 | -0.02 | -0.03 | -0.07 | -0.7 | -2.0 |
| cell_chase_rate | % chase rate | 28.8 | 27.3 to 30.5 | +0.20 | -0.22 | +0.03 | +8.9 | +0.9 |
| cell_chase_rate_beyond_baseline | % chase rate | -0.0 | -0.5 to 0.5 | -0.27 | +0.15 | -0.25 | -12.1 | -6.6 |
| mean_distance | ft | 0.60 | 0.57 to 0.64 | -0.42 | +0.41 | -0.16 | -18.8 | -4.3 |
| mean_release_speed | mph | 88.6 | 88.0 to 89.4 | +0.36 | -0.27 | +0.24 | +16.4 | +6.6 |
| all proxies at once | | | | 0.49 (multiple, adjusted) | | 0.27 (multiple, adjusted) | 22.5 | 7.3 |

The spread is xChase+ fit as a straight line on the proxy, read at the 90th percentile hitter minus the 10th; for all proxies at once (every proxy but non_fastball_share, the sum of the two shares) it is the 10th to 90th percentile of the fitted values. Pooled rows centre every value on its season first.

## By season

| Season | Hitters | r(non-fastball share, xChase+) | r(cell rate, xChase+) | r(beyond baseline, xChase+) | r(beyond baseline, residual) | Spread: non-fastball | Spread: cell rate | Spread: beyond baseline | Spread: all |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | 251 | -0.25 | +0.02 | -0.19 | -0.25 | -11.0 | +0.7 | -8.5 | 19.3 |
| 2022 | 267 | -0.40 | +0.24 | -0.29 | -0.17 | -16.9 | +10.7 | -12.0 | 24.8 |
| 2023 | 280 | -0.42 | +0.22 | -0.34 | -0.26 | -20.8 | +10.8 | -17.3 | 27.1 |
| 2024 | 269 | -0.41 | +0.21 | -0.34 | -0.26 | -17.8 | +9.8 | -14.6 | 23.5 |
| 2025 | 266 | -0.36 | +0.22 | -0.26 | -0.32 | -16.1 | +9.9 | -11.5 | 23.8 |
| 2026 | 261 | -0.28 | +0.24 | -0.19 | -0.23 | -12.2 | +9.7 | -7.8 | 18.8 |

2021 is the weakest season on every proxy, and the cells' league chase rate does not relate to xChase+ at all there (r = +0.02 against +0.21 to +0.24 after); the check does not say why.

## Within hitters: odd against even games

A cross-section cannot say whether the mix is a confound (sliders off the plate are hard to take, so a hitter shown more of them loses points he did not earn) or targeting (pitchers throw sliders off the plate to hitters who chase them, so the mix follows the habit). This splits every qualified hitter-season into odd and even games by game_pk (the split step 15 uses; odd and even games interleave, so a slump or a mid-season change sits in both halves), recomputes each proxy on each half (the leave-one-hitter-out cell rates stay those of the full season), and takes two outcomes per half: his chase rate, and the runs saved over that half's priced pitches per 600 plate appearances in xChase+ points (100 × runs saved per 600 PA / the league's chase cost per 600 PA; plate appearances per half are counted from the pitch file the way step 04 counts a season's, and the two halves add back to the leaderboard's PA, runs saved per 600 PA and unshrunk xChase+ exactly). The odd-minus-even difference in the outcome is then fit on the odd-minus-even difference in the proxy across hitter-seasons. Scouting is the same in both halves, so most of the half-to-half variation in the mix is which pitchers and pitches he happened to draw: a within-hitter slope near the cross-sectional slope says confound, a slope near zero says targeting or hitter type, with two caveats that pull opposite ways (below). The half-season points are unshrunk, so the cross-sectional slope to compare is the one on the unshrunk full-season points (xchase_plus_raw); on xChase+ itself the cross-sectional slopes are about 0.8 times as large, the shrinkage. Every standard error here is HC1, robust to the unequal noise across hitters (a hitter near the plate-appearance floor carries about twice the odd-minus-even outcome variance of a regular).

**The within-hitter slopes sit much nearer zero than the cross-section's, but not at zero for the pitch mix.** Pooled over the six seasons, the within-hitter slope of points on non-fastball share is -0.43 ± 0.14 points per percentage point against -1.79 across hitters (-1.44 on xChase+): 24% of the cross-sectional slope, 3.0 standard errors from zero and 9 from the cross-section. Over the cross-section's 10th to 90th percentile range of the share (44.2 to 55.8%), that is -4.8 ± 1.6 points within hitters against -20.0 across them (-16.0 on xChase+). Weighting each hitter by his pitches (1 / (1/n_odd + 1/n_even), so a regular counts for more than a hitter at the floor) moves the slope to -0.48 ± 0.14 (-5.3 ± 1.5 over the range). Chase rate reads the same: +0.081 ± 0.022 chase-rate points per percentage point within hitters against +0.325 across them (25%). The part of the cell chase rate beyond the baseline cell gives the same picture: 32% of its cross-sectional slope on points (-4.8 ± 1.4 against -15.1 points over its 10th to 90th range; -5.1 ± 1.4 weighted), 34% on chase rate. Its within-hitter chase-rate slope, +0.75 ± 0.21, is close to the 1.0 an additive cell effect would give (his chase rate moving one for one with the league's rate on the cells he saw), while the cross-sectional 2.23 is more than twice that: the cells are as hard as the league says, and the hitters who see the hard ones chase more than the cells explain.

Mean release speed and mean distance show nothing within hitters on points: -1.0 ± 1.2 points over the speed range against +20.6 across hitters, and +0.4 ± 1.1 over the distance range against -23.7. On chase rate, distance reverses sign: within a hitter, a half with pitches further off the plate has the lower chase rate (-1.4 ± 0.2 chase-rate points over the range), while across hitters the ones pitched further off the plate chase more (+5.9). That is targeting in its plainest form, pitchers going further off the plate against hitters who will chase, and the baseline already prices the distance, so it leaves no mark on points.

Read together: about 24% to 32% of the cross-sectional relation between the pitch mix and xChase+ survives within hitters, so most of what the cross-section shows is targeting or hitter type, and the confound a pitch-quality baseline would remove is about 5 points between the 10th and 90th percentile hitters in the mix, possibly 8: the pooled spread runs from about 2 to 8 points at two standard errors (-4.8 ± 1.6 on the share, -4.8 ± 1.4 by the cell rate), and 2026 alone reads -8.6 ± 4.1 and -7.9 ± 3.3. That reaches the edge of a card's ± of 7-10 points rather than sitting inside it.

The within-hitter slope is an estimate of the confound, not a bound on it, because two biases of unknown size pull it opposite ways. Same-half targeting pushes it toward the cross-section: a pitcher who sees a hitter chase a slider in the second inning throws him more in the sixth, and both land in the same half, so part of a half's extra sliders is the half's own chasing. Lagged targeting pulls it toward zero: a hitter who chases sliders in an odd game is thrown more of them in the next, even, game, which ties the halves' mixes to each other's outcomes and attenuates the odd-minus-even relation. The check cannot size either, so the slope sits somewhere between them.

Every season's within-hitter slope on the share is negative (-0.24, -0.62, -0.39, -0.41, -0.24, -0.68, standard errors 0.32 to 0.41); 2026 is the largest and sits 0.8 standard errors from the pooled value, so no season stands apart. 2026's within / cross ratios (0.57 on the share, 0.82 by the cell rate) are the highest mainly because the denominator moved, not the numerator: its cross-sectional slope on the share, -1.19 ± 0.25 points per percentage point, is the smallest of the six seasons against -2.08 to -2.17 in 2022-2024, most likely the ABS box flattening the cross-section (the shorter zone made more takes chases on every pitch type), while its within-hitter slope is the ordinary 0.8 standard errors from the pooled value.

Noise in the differences. The odd-minus-even difference in non-fastball share has a standard deviation of 3.7 percentage points across hitter-seasons, against 4.5 for the share itself across hitters, and 3.3 of it is what an independent draw of his own season's pitches would give (the rest, about 1.8, is which pitchers he drew). The within-hitter range is the narrower, so the within-hitter slope is the less precise, and its standard error is what the spreads above carry. But the pitches a half happened to hold are the pitches he had to take or chase, so that variation is the treatment itself, not measurement error in it, and the slope is not attenuated by it; the same holds for the other proxies (SDs in the last table). The outcome side is noisier for some hitters than others (its variance scales with 1/n_odd + 1/n_even), so the standard errors are HC1, heteroskedasticity-robust; on the pooled share they come to 0.145 against a classical 0.138 (1.44 against 1.37 by the cell rate), and the classical ones stay in the CSV.

### Pooled, by proxy

| Proxy | 10th-90th pct | Cross spread, xChase+ | Cross spread, unshrunk ± SE | Within spread ± SE | Weighted within spread ± SE | Within / cross | Cross chase-rate spread | Within chase-rate spread ± SE | Within / cross |
|---|---|---|---|---|---|---|---|---|---|
| non_fastball_share | 44.2 to 55.8 | -16.0 | -20.0 ± 1.3 | -4.8 ± 1.6 | -5.3 ± 1.5 | 0.24 | +3.6 | +0.9 ± 0.2 | 0.25 |
| breaking_share | 26.9 to 39.7 | -14.8 | -18.6 ± 1.4 | -2.3 ± 1.9 | -2.2 ± 1.8 | 0.13 | +4.0 | +0.1 ± 0.3 | 0.02 |
| offspeed_share | 11.0 to 23.1 | -0.7 | -0.8 ± 1.4 | -4.5 ± 2.1 | -5.4 ± 2.0 | – | -0.5 | +1.3 ± 0.3 | – |
| cell_chase_rate | 27.3 to 30.5 | +8.9 | +11.2 ± 1.4 | -0.2 ± 0.9 | -0.3 ± 0.9 | -0.02 | -3.3 | +2.1 ± 0.1 | -0.64 |
| cell_chase_rate_beyond_baseline | -0.5 to 0.5 | -12.1 | -15.1 ± 1.3 | -4.8 ± 1.4 | -5.1 ± 1.4 | 0.32 | +2.2 | +0.7 ± 0.2 | 0.34 |
| mean_distance | 0.57 to 0.64 | -18.8 | -23.7 ± 1.3 | +0.4 ± 1.1 | +0.3 ± 1.1 | -0.02 | +5.9 | -1.4 ± 0.2 | -0.23 |
| mean_release_speed | 88.0 to 89.4 | +16.4 | +20.6 ± 1.3 | -1.0 ± 1.2 | -0.9 ± 1.1 | -0.05 | -4.0 | -0.0 ± 0.2 | 0.01 |

Spreads are the slope times the cross-section's 10th to 90th percentile range of the proxy, in xChase+ points (chase-rate points in the last three columns); the ratio is the within-hitter slope over the cross-sectional slope on the unshrunk points (on chase rate), left blank where the cross-sectional spread is under 5 points (2 chase-rate points) and the ratio would mean nothing. Standard errors are HC1; the weighted column fits with weight 1 / (1/n_odd + 1/n_even) per hitter. Note that the within-hitter spread reads a straight line well past the data: the share's cross-sectional range is 11.2 percentage points while its odd-minus-even difference has a standard deviation of 3.7, so the spread extrapolates the within-hitter slope about 3 SDs out from where the differences sit, and linearity is doing that work. Pooled rows centre every difference on its season.

### By season

| Season | Hitters | Pitches per half | Share: cross slope ± SE | Share: within slope ± SE | Share: within / cross | Beyond baseline: cross slope ± SE | Beyond baseline: within slope ± SE | Beyond baseline: within / cross | Share, chase rate: within / cross | Beyond baseline, chase rate: within / cross |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 251 | 505 | -1.45 ± 0.37 | -0.24 ± 0.35 | 0.17 | -11.2 ± 3.8 | -1.0 ± 3.7 | 0.09 | 0.30 | 0.16 |
| 2022 | 267 | 498 | -2.12 ± 0.29 | -0.62 ± 0.41 | 0.30 | -17.5 ± 3.7 | -6.6 ± 3.7 | 0.38 | 0.18 | 0.36 |
| 2023 | 280 | 498 | -2.17 ± 0.27 | -0.39 ± 0.32 | 0.18 | -20.5 ± 3.2 | -4.7 ± 3.2 | 0.23 | 0.24 | 0.31 |
| 2024 | 269 | 496 | -2.08 ± 0.26 | -0.41 ± 0.34 | 0.20 | -18.2 ± 2.9 | -6.2 ± 3.4 | 0.34 | 0.33 | 0.27 |
| 2025 | 266 | 494 | -1.72 ± 0.24 | -0.24 ± 0.38 | 0.14 | -12.8 ± 2.7 | -2.6 ± 3.6 | 0.20 | 0.04 | 0.10 |
| 2026 | 261 | 527 | -1.19 ± 0.25 | -0.68 ± 0.33 | 0.57 | -9.9 ± 3.1 | -8.1 ± 3.3 | 0.82 | 0.43 | 0.78 |

Slopes are xChase+ points per percentage point of the proxy (the cross slope on the unshrunk points), standard errors HC1; the ratios are the within slope over that season's cross slope (on chase rate).

### How much the proxies move between halves

| Proxy | Units | SD across hitters | SD of odd minus even | Of which the pitch draw alone |
|---|---|---|---|---|
| non_fastball_share | % of off-zone pitches | 4.47 | 3.73 | 3.25 |
| breaking_share | % of off-zone pitches | 4.83 | 3.73 | 3.06 |
| offspeed_share | % of off-zone pitches | 4.62 | 3.01 | 2.40 |
| cell_chase_rate | % chase rate | 0.90 | 1.33 | 1.26 |
| cell_chase_rate_beyond_baseline | % chase rate | 0.40 | 0.37 | 0.34 |
| mean_distance | ft | 0.028 | 0.033 | 0.032 |
| mean_release_speed | mph | 0.49 | 0.56 | 0.40 |

The last column is the SD an independent draw of each hitter's own season's pitches would put on his odd-minus-even difference (his per-pitch variance times 1/n_odd + 1/n_even, root-mean-squared over hitters); what the middle column has beyond it is which pitchers the halves happened to hold.

Full numbers, every proxy and season, in `pitch_mix_confound.csv` (the cross-section) and `pitch_mix_confound_within.csv` (the within-hitter test).
