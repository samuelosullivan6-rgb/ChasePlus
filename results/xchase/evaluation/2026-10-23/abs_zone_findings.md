# What the ABS challenge data say about the 2026 Statcast zone

Date: 2026-10-23. These findings came out of a review of the separate ABS challenge study (https://github.com/samuelosullivan6-rgb/ABS-Usage), recomputed from this repository's own parquet files. The side-of-zone called-strike model and the README's 2026 limitation (commit c3b3a35) act on them.

## Findings

**1. The 2026 limitation can now be stated as fact.** Statcast's 2026 sz_top and sz_bot are the ABS box: the within-batter SD of sz_top is 0.000 in 2026 against 0.07 to 0.10 feet in 2021 to 2025, and the recorded zone is 2.86 inches shorter than in 2025 (top 3.435 to 3.215 feet, bottom 1.605 to 1.622). Umpires kept calling a taller zone. The called-strike rate on takes 0 to 2 inches above the recorded top is 75.7% in 2026 against 41 to 58% in the five seasons before, and the top edge's 50% point sits 1.8 inches above the recorded box against 0.6 to 1.2 before.

**2. The consequences in the main project.**

- Chase rate 28.3% to 30.5%: about 2.1 points of that is the box (C1).
- League chase cost 37.1 to 43.9 runs per 600 PA decomposes as opportunities per PA +6%, chase rate +8%, cost per chase +3%. The cost-per-chase rise is concentrated in borderline chases (0.064 to 0.079 runs), the pitches the model most under-predicts as called strikes.
- The league's far-off chase rate (more than 0.35 feet off the recorded box) went 19.3% to 21.8%, and the far-off share of out-of-zone pitches 61.7% to 64.1%. Every card's season trend and every frozen 2027 cell is measured against a different box in 2026 than in 2021 to 2025, and no card says so.
- The called-strike model's direction error more than doubled. Actual minus predicted called strikes per 1,000 takes: borderline above +198 (2025: +4), borderline below +144 (−20), just-off above +117 (+64), just-off side −58 (−20).
- Per hitter, the direction-blind model overcharges chases by 0.83 ± 0.40 runs per 600 PA in 2026 against 0.28 ± 0.17 in 2025 (hitters with 300+ PA). The league mean cancels against the baseline; the spread does not. That is about one xChase+ point for a typical hitter and about three at the extremes: Cedric Mullins, Patrick Bailey and Moisés Ballesteros are overcharged by 1.9 to 2.2 runs, Spencer Steer undercharged by 0.4. The README's "roughly 0.2 to 0.4 runs per 600 PA" was right for 2025 and is about 2.4 times too low for 2026.
- The 2025-to-2026 reliability pair (0.70) is in range, so the ranking survived; but "comparable across seasons" leans on a 2026 league scale that is inflated partly by bookkeeping.

**3. The fixes.** Add the side of the zone a pitch missed on (above, below, side) to the called-strike model, at least from 2026, and rerun. Rewrite the limitation with the numbers above. Put the box change on the 2026 cards' trend and in the frozen 2027 file's notes: the cells are defined by the ABS box, which is fine if 2027 keeps it, and the file should say that.

