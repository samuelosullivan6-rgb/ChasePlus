"""
Line up Chase+ with xChase+, one season at a time.

xChase+ comes from a second run of the leaderboard script:

    python scripts/04_build_chase_leaderboard.py                     (Chase+)
    python scripts/04_build_chase_leaderboard.py --expected-contact  (xChase+)
    python scripts/09_build_xchase_comparison.py

The two runs share every step except how a chase put in play is priced
(actual plate appearance value vs. a line in Savant's xwOBA), so

    luck = chase_plus - xchase_plus

is what the result of those balls in play added beyond how they were hit
(contact luck, plus the base-out context of those plate appearances).
Positive = the results flattered him. It repeating year to year would mean
xwOBA is missing something real about the hitter.

Before comparing anything, this script checks that the two runs really
differ only on balls in play (same fingerprint, same hitter-seasons, same
takes/whiffs/fouls, same league scale). If a check fails it stops.

Inputs:  results/chase_cost_leaderboard_by_season.csv
         results/chase_plus_league_scale.csv
         results/xchase/chase_cost_leaderboard_by_season.csv
         results/xchase/chase_plus_league_scale.csv
         data/cleaned/chase_costs_by_pitch.parquet
         data/cleaned/xchase_costs_by_pitch.parquet
         data/cleaned/baseline_chase_pitches.parquet (descriptions, and
         wOBA / xwOBA per plate appearance for the offense tests)
Outputs: results/xchase/xchase_comparison_<season>.csv (one per season)
         results/xchase/xchase_comparison_by_season.csv
         results/xchase/xchase_reliability.csv
         results/xchase/xchase_leaderboard_<season>.csv (one per season)
         results/xchase/xchase_leaderboard_by_season.csv
         results/xchase/regression_candidates.csv
         results/xchase/offense_same_season.csv
         results/xchase/offense_next_season.csv

The xChase+ run saves its columns as xchase_plus, xchase_plus_se, ...
(the Chase+ run keeps chase_plus), so they are read under those names.
"""

from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

# How many hitters each printed list shows.
LIST_SIZE = 10

PLATE_APPEARANCES_PER_SEASON = 600


# --------------------------------------------------
# FILE LOCATIONS
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
RESULTS_DIR = PROJECT_DIR / "results"
XCHASE_DIR = RESULTS_DIR / "xchase"

CHASE_BY_SEASON = RESULTS_DIR / "chase_cost_leaderboard_by_season.csv"
CHASE_SCALE = RESULTS_DIR / "chase_plus_league_scale.csv"
CHASE_PITCHES = CLEAN_DIR / "chase_costs_by_pitch.parquet"

X_BY_SEASON = XCHASE_DIR / "chase_cost_leaderboard_by_season.csv"
X_SCALE = XCHASE_DIR / "chase_plus_league_scale.csv"
X_PITCHES = CLEAN_DIR / "xchase_costs_by_pitch.parquet"

PITCH_FILE = CLEAN_DIR / "baseline_chase_pitches.parquet"

OUTPUT_BY_SEASON = XCHASE_DIR / "xchase_comparison_by_season.csv"
SEASON_FILE_NAME = "xchase_comparison_{season}.csv"
OUTPUT_RELIABILITY = XCHASE_DIR / "xchase_reliability.csv"

OUTPUT_LEADERBOARD = XCHASE_DIR / "xchase_leaderboard_by_season.csv"
LEADERBOARD_FILE_NAME = "xchase_leaderboard_{season}.csv"
OUTPUT_CANDIDATES = XCHASE_DIR / "regression_candidates.csv"
OUTPUT_SAME_SEASON = XCHASE_DIR / "offense_same_season.csv"
OUTPUT_NEXT_SEASON = XCHASE_DIR / "offense_next_season.csv"

# A hitter goes on the regression candidates list when his luck is at
# least this many standard errors from zero.
REGRESSION_Z = 2.0

for needed in [CHASE_BY_SEASON, CHASE_SCALE, CHASE_PITCHES,
               X_BY_SEASON, X_SCALE, X_PITCHES, PITCH_FILE]:
    if not needed.exists():
        raise FileNotFoundError(
            f"{needed.relative_to(PROJECT_DIR)} is missing. Run "
            "04_build_chase_leaderboard.py, then again with --expected-contact."
        )


# --------------------------------------------------
# CHECK 1: BOTH RUNS CAME FROM THE SAME SCRIPT AND DATA
# --------------------------------------------------

as_text = {"run_fingerprint": str}

chase_fingerprints = set(
    pd.read_csv(CHASE_SCALE, dtype=as_text)["run_fingerprint"]
)
x_fingerprints = set(
    pd.read_csv(X_SCALE, dtype=as_text)["run_fingerprint"]
)

if len(chase_fingerprints) != 1 or chase_fingerprints != x_fingerprints:
    raise RuntimeError(
        f"Chase+ run fingerprint {sorted(chase_fingerprints)} does not "
        f"match xChase+ {sorted(x_fingerprints)}. One of them is stale; "
        "rerun both."
    )

fingerprint = chase_fingerprints.pop()

print(f"Both runs have fingerprint {fingerprint}.")


# --------------------------------------------------
# CHECK 2: PITCH BY PITCH, ONLY BALLS IN PLAY DIFFER
# --------------------------------------------------

pitch_key = ["game_pk", "at_bat_number", "pitch_number"]

chase_pitches = pd.read_parquet(
    CHASE_PITCHES,
    columns=pitch_key + [
        "batter", "game_year", "is_chase",
        "value_if_taken", "chase_cost", "runs_saved",
    ]
)

x_pitches = pd.read_parquet(
    X_PITCHES,
    columns=pitch_key + ["value_if_taken", "chase_cost", "runs_saved"]
).rename(columns={
    "value_if_taken": "x_value_if_taken",
    "chase_cost": "x_chase_cost",
    "runs_saved": "x_runs_saved",
})

descriptions = pd.read_parquet(
    PITCH_FILE,
    columns=pitch_key + ["description"]
)

pitches = chase_pitches.merge(x_pitches, on=pitch_key, how="outer",
                              indicator=True)

if (pitches["_merge"] != "both").any():
    raise RuntimeError(
        f"{int((pitches['_merge'] != 'both').sum()):,} pitches are in only "
        "one of the two runs."
    )

pitches = pitches.drop(columns="_merge")

pitches = pitches.merge(descriptions, on=pitch_key, how="left")

del chase_pitches, x_pitches, descriptions

in_play = (pitches["description"] == "hit_into_play").to_numpy()

# The called-strike model is the same in both runs, so every take is
# priced the same.
if not np.array_equal(pitches["value_if_taken"], pitches["x_value_if_taken"]):
    raise RuntimeError("value_if_taken differs between the two runs.")

# Everything that is not a ball in play has to cost exactly the same.
not_in_play_chase_cost = pitches.loc[~in_play, "chase_cost"].to_numpy()
not_in_play_x_cost = pitches.loc[~in_play, "x_chase_cost"].to_numpy()

if not np.array_equal(not_in_play_chase_cost, not_in_play_x_cost):
    different = int((not_in_play_chase_cost != not_in_play_x_cost).sum())
    raise RuntimeError(
        f"{different:,} pitches that were not put in play have a different "
        "chase cost in the two runs."
    )

changed_in_play = int(
    (pitches.loc[in_play, "chase_cost"]
     != pitches.loc[in_play, "x_chase_cost"]).sum()
)

print(
    f"Pitch check passed: {len(pitches):,} opportunities, "
    f"{int(in_play.sum()):,} chases put in play ({changed_in_play:,} "
    "repriced), everything else identical."
)


# --------------------------------------------------
# LUCK PER PITCH, THEN PER HITTER-SEASON
#
# Per pitch, Chase+ minus xChase+ in runs is runs_saved - x_runs_saved
# (the league baselines differ a little between the runs, so this is not
# only nonzero on balls in play). Its spread gives the standard error of
# the gap directly, which is much smaller than either stat's own standard
# error because the two share almost every pitch.
# --------------------------------------------------

pitches["luck_runs"] = pitches["runs_saved"] - pitches["x_runs_saved"]
pitches["chase_in_play"] = (in_play & (pitches["is_chase"] == 1)).astype(int)

luck_by_hitter = (
    pitches
    .groupby(["batter", "game_year"])
    .agg(
        luck_opportunities=("luck_runs", "size"),
        mean_luck=("luck_runs", "mean"),
        luck_standard_deviation=("luck_runs", "std"),
        chases_in_play=("chase_in_play", "sum"),
    )
    .reset_index()
)


# --------------------------------------------------
# CHECK 3: THE SAME HITTER-SEASONS, SAME SCALE
# --------------------------------------------------

keep_columns = [
    "batter",
    "player",
    "game_year",
    "plate_appearances",
    "opportunities",
    "chases",
    "chase_rate",
    "chase_plus",
    "chase_plus_raw",
    "chase_plus_se",
    "chase_plus_posterior_sd",
    "league_chase_cost_per_600_pa",
    "scale_to_600_pa",
    "value_rank",
]

chase = pd.read_csv(CHASE_BY_SEASON)[keep_columns]

x_chase = pd.read_csv(X_BY_SEASON)[
    [
        "batter",
        "game_year",
        "opportunities",
        "chases",
        "plate_appearances",
        "xchase_plus",
        "xchase_plus_raw",
        "xchase_plus_se",
        "xchase_plus_posterior_sd",
        "league_chase_cost_per_600_pa",
        "value_rank",
    ]
].rename(columns={
    "opportunities": "x_opportunities",
    "chases": "x_chases",
    "plate_appearances": "x_plate_appearances",
    "league_chase_cost_per_600_pa": "x_league_chase_cost_per_600_pa",
    "value_rank": "xchase_plus_rank",
})

comparison = chase.merge(x_chase, on=["batter", "game_year"], how="outer",
                         indicator=True)

if (comparison["_merge"] != "both").any():
    raise RuntimeError(
        f"{int((comparison['_merge'] != 'both').sum()):,} hitter-seasons "
        "qualified in only one run. The floors do not depend on balls in "
        "play, so this should be impossible."
    )

comparison = comparison.drop(columns="_merge")

for column in ["opportunities", "chases", "plate_appearances"]:
    if not (comparison[column] == comparison[f"x_{column}"]).all():
        raise RuntimeError(f"{column} differs between the two runs.")

if not np.allclose(
    comparison["league_chase_cost_per_600_pa"],
    comparison["x_league_chase_cost_per_600_pa"],
    rtol=0,
    atol=1e-9
):
    raise RuntimeError(
        "The league chase cost per 600 PA differs between the runs, so "
        "Chase+ and xChase+ are not on the same scale."
    )

comparison = comparison.drop(columns=[
    "x_opportunities",
    "x_chases",
    "x_plate_appearances",
    "x_league_chase_cost_per_600_pa",
])

comparison = comparison.rename(columns={"value_rank": "chase_plus_rank"})

comparison = comparison.merge(luck_by_hitter, on=["batter", "game_year"],
                              how="left")

points_per_run = 100 / comparison["league_chase_cost_per_600_pa"]

# In Chase+ points. luck_raw is the unshrunk gap, luck the shrunk one.
comparison["luck"] = comparison["chase_plus"] - comparison["xchase_plus"]
comparison["luck_raw"] = (
    comparison["chase_plus_raw"] - comparison["xchase_plus_raw"]
)

comparison["luck_se"] = (
    comparison["luck_standard_deviation"]
    / np.sqrt(comparison["luck_opportunities"])
    * comparison["scale_to_600_pa"]
    * points_per_run
)

comparison["luck_z"] = comparison["luck_raw"] / comparison["luck_se"]

# Positive = Chase+ ranks him higher than xChase+ does.
comparison["rank_move"] = (
    comparison["xchase_plus_rank"] - comparison["chase_plus_rank"]
)

# The per-pitch luck has to add up to the gap between the two raw stats.
rebuilt_gap = (
    comparison["mean_luck"] * comparison["scale_to_600_pa"] * points_per_run
)

if not np.allclose(rebuilt_gap, comparison["luck_raw"], rtol=0, atol=1e-6):
    raise RuntimeError(
        "Per-pitch luck does not add up to chase_plus_raw - "
        "xchase_plus_raw."
    )

print(
    f"Hitter-season check passed: {len(comparison):,} hitter-seasons in "
    "both runs, same counts, same league scale."
)


# --------------------------------------------------
# SAVE
# --------------------------------------------------

output_columns = [
    "batter",
    "player",
    "game_year",
    "plate_appearances",
    "chases",
    "chases_in_play",
    "chase_rate",
    "chase_plus",
    "xchase_plus",
    "luck",
    "luck_raw",
    "luck_se",
    "luck_z",
    "chase_plus_rank",
    "xchase_plus_rank",
    "rank_move",
    "chase_plus_raw",
    "xchase_plus_raw",
    "chase_plus_se",
    "xchase_plus_se",
    "league_chase_cost_per_600_pa",
]

# Same fallback as the leaderboard: show the batter ID when the name
# lookup failed.
comparison["player"] = comparison["player"].fillna(
    comparison["batter"].astype(str)
)

# Kept whole for the combined leaderboard further down, which also needs
# the posterior SDs.
full_comparison = comparison.copy()

comparison = comparison[output_columns].sort_values(
    ["game_year", "luck"],
    ascending=[True, False]
)

comparison.to_csv(OUTPUT_BY_SEASON, index=False)

written_files = [OUTPUT_BY_SEASON]

seasons = sorted(comparison["game_year"].unique())

for season in seasons:

    season_file = XCHASE_DIR / SEASON_FILE_NAME.format(season=int(season))

    comparison[comparison["game_year"] == season].to_csv(
        season_file,
        index=False
    )

    written_files.append(season_file)


# --------------------------------------------------
# PRINT: WHO THE RESULTS FLATTERED, WHO THEY HURT, WHO AGREES
#
# The first two lists are sorted by luck_z, not the raw gap, so a hitter
# with few balls in play cannot top them on noise alone.
# --------------------------------------------------

show_columns = [
    "player",
    "chases_in_play",
    "chase_plus",
    "xchase_plus",
    "luck",
    "luck_z",
    "chase_plus_rank",
    "xchase_plus_rank",
]


def print_list(title, table):
    """One printed list, rounded for reading."""

    print()
    print(title)

    view = table[show_columns].copy()

    for column in ["chase_plus", "xchase_plus", "luck", "luck_z"]:
        view[column] = view[column].round(1)

    for column in ["chases_in_play", "chase_plus_rank", "xchase_plus_rank"]:
        view[column] = view[column].astype(int)

    print(view.to_string(index=False))


for season in seasons:

    season_table = comparison[comparison["game_year"] == season].copy()

    print()
    print("=" * 78)
    print(f"{int(season)}: CHASE+ vs xCHASE+ ({len(season_table)} qualified)")
    print("=" * 78)

    print()
    print(
        f"Mean Chase+ {season_table['chase_plus'].mean():.1f}, "
        f"mean xChase+ {season_table['xchase_plus'].mean():.1f}. "
        f"SD of luck {season_table['luck'].std():.1f} points. "
        f"Correlation {season_table['chase_plus'].corr(season_table['xchase_plus']):.3f}."
    )

    print_list(
        "Results flattered him most (Chase+ above xChase+):",
        season_table.sort_values("luck_z", ascending=False).head(LIST_SIZE)
    )

    print_list(
        "Results hurt him most (Chase+ below xChase+):",
        season_table.sort_values("luck_z", ascending=True).head(LIST_SIZE)
    )

    season_table["absolute_luck"] = season_table["luck"].abs()

    print_list(
        "Chase+ and xChase+ agree most:",
        season_table.sort_values("absolute_luck").head(LIST_SIZE)
    )


# --------------------------------------------------
# YEAR TO YEAR: DOES xCHASE+ REPEAT BETTER, AND DOES LUCK REPEAT AT ALL?
#
# Unshrunk values, hitters qualified in both seasons, the same way
# 06_build_chase_reliability.py does it.
# --------------------------------------------------

reliability_rows = []

print()
print("=" * 78)
print("YEAR TO YEAR (hitters qualified both seasons, unshrunk)")
print("=" * 78)

for first_season, second_season in zip(seasons[:-1], seasons[1:]):

    first = comparison[comparison["game_year"] == first_season]
    second = comparison[comparison["game_year"] == second_season]

    paired = first.merge(second, on="batter", suffixes=("_first", "_second"))

    chase_r = paired["chase_plus_raw_first"].corr(
        paired["chase_plus_raw_second"]
    )
    x_r = paired["xchase_plus_raw_first"].corr(
        paired["xchase_plus_raw_second"]
    )
    luck_r = paired["luck_raw_first"].corr(paired["luck_raw_second"])

    x_predicts_chase_r = paired["xchase_plus_raw_first"].corr(
        paired["chase_plus_raw_second"]
    )

    reliability_rows.append({
        "first_season": int(first_season),
        "second_season": int(second_season),
        "paired_hitters": len(paired),
        "chase_plus_r": chase_r,
        "xchase_plus_r": x_r,
        "luck_r": luck_r,
        "xchase_plus_to_next_chase_plus_r": x_predicts_chase_r,
    })

    print()
    print(f"{int(first_season)} -> {int(second_season)} ({len(paired)} hitters)")
    print(f"  Chase+  r = {chase_r:+.3f}")
    print(f"  xChase+ r = {x_r:+.3f}")
    print(f"  luck    r = {luck_r:+.3f}   (near 0 = luck, clearly above = xwOBA misses a skill)")
    print(f"  xChase+ -> next Chase+ r = {x_predicts_chase_r:+.3f}   (vs {chase_r:+.3f} from Chase+ itself)")

pd.DataFrame(reliability_rows).to_csv(OUTPUT_RELIABILITY, index=False)

written_files.append(OUTPUT_RELIABILITY)


# --------------------------------------------------
# THE COMBINED LEADERBOARD
#
# xChase+ is the main number (it repeats better year to year), so the
# leaderboard is ranked by it. Chase+ sits next to it as what actually
# happened, with the luck between them.
# --------------------------------------------------

leaderboard_columns = [
    "xchase_plus_rank",
    "player",
    "batter",
    "game_year",
    "plate_appearances",
    "chase_rate",
    "xchase_plus",
    "xchase_plus_posterior_sd",
    "chase_plus",
    "chase_plus_posterior_sd",
    "chase_plus_rank",
    "rank_move",
    "luck",
    "luck_se",
    "luck_z",
    "chases",
    "chases_in_play",
]

leaderboard = full_comparison[leaderboard_columns].sort_values(
    ["game_year", "xchase_plus_rank"]
)

leaderboard.to_csv(OUTPUT_LEADERBOARD, index=False)

written_files.append(OUTPUT_LEADERBOARD)

for season in seasons:

    season_file = XCHASE_DIR / LEADERBOARD_FILE_NAME.format(season=int(season))

    leaderboard[leaderboard["game_year"] == season].to_csv(
        season_file,
        index=False
    )

    written_files.append(season_file)


# --------------------------------------------------
# REGRESSION CANDIDATES
#
# Hitters whose Chase+ is at least REGRESSION_Z standard errors away from
# their xChase+. Luck doesn't repeat year to year (see above), so their
# Chase+ should move toward their xChase+.
#
# By chance alone about 5% of hitters land past +-2, so this list is who
# to watch, not proof anyone was lucky.
# --------------------------------------------------

candidates = full_comparison[
    full_comparison["luck_z"].abs() >= REGRESSION_Z
].copy()

candidates["expect_chase_plus_to"] = np.where(
    candidates["luck"] > 0,
    "fall",
    "rise"
)

candidates = candidates[
    [
        "game_year",
        "player",
        "batter",
        "expect_chase_plus_to",
        "chase_plus",
        "xchase_plus",
        "luck",
        "luck_z",
        "chases_in_play",
        "plate_appearances",
    ]
].sort_values(["game_year", "luck_z"], ascending=[True, False])

candidates.to_csv(OUTPUT_CANDIDATES, index=False)

written_files.append(OUTPUT_CANDIDATES)

print()
print("=" * 78)
print(f"REGRESSION CANDIDATES (luck at least {REGRESSION_Z:.0f} standard errors from zero)")
print("=" * 78)

for season in seasons:

    in_season = candidates[candidates["game_year"] == season]
    qualified = int((comparison["game_year"] == season).sum())

    print()
    print(
        f"{int(season)}: {len(in_season)} of {qualified} hitters "
        f"({len(in_season) / qualified:.1%}; about 4.6% would land here by "
        "chance alone)"
    )

    if len(in_season) > 0:

        view = in_season[
            ["player", "expect_chase_plus_to", "chase_plus", "xchase_plus",
             "luck", "luck_z", "chases_in_play"]
        ].copy()

        for column in ["chase_plus", "xchase_plus", "luck", "luck_z"]:
            view[column] = view[column].round(1)

        print(view.to_string(index=False))


# --------------------------------------------------
# OFFENSE: wOBA AND xwOBA PER HITTER-SEASON
#
# Built from the plate appearances in the cleaned pitch file (the last
# pitch of each PA carries woba_value and woba_denom). xwOBA swaps a ball
# in play's actual woba_value for Savant's estimate from exit velocity and
# launch angle; walks, HBP and strikeouts keep their actual value.
#
# Two versions:
#   - all plate appearances (next-season target, and this season's
#     control)
#   - without the PAs that ended on a chase put in play. Those batted balls
#     are inside Chase+ (actual result) and xChase+ (xwOBA), so leaving
#     them in would put the same numbers on both sides of a same-season
#     correlation.
# --------------------------------------------------

plate_appearances = pd.read_parquet(
    PITCH_FILE,
    columns=["batter", "game_year", "description", "is_chase",
             "woba_value", "woba_denom", "estimated_woba_using_speedangle"]
)

plate_appearances = plate_appearances[plate_appearances["woba_denom"] > 0].copy()

in_play = plate_appearances["description"] == "hit_into_play"
has_estimate = plate_appearances["estimated_woba_using_speedangle"].notna()

plate_appearances["xwoba_value"] = np.where(
    in_play & has_estimate,
    plate_appearances["estimated_woba_using_speedangle"],
    plate_appearances["woba_value"]
)

plate_appearances["chased_in_play"] = in_play & (plate_appearances["is_chase"] == 1)


def woba_by_hitter(table, suffix):
    """wOBA and xwOBA per (batter, game_year) from PA-level values."""

    totals = (
        table
        .groupby(["batter", "game_year"])[["woba_value", "xwoba_value", "woba_denom"]]
        .sum()
    )

    return pd.DataFrame({
        f"woba{suffix}": totals["woba_value"] / totals["woba_denom"],
        f"xwoba{suffix}": totals["xwoba_value"] / totals["woba_denom"],
    }).reset_index()


offense = woba_by_hitter(plate_appearances, "").merge(
    woba_by_hitter(
        plate_appearances[~plate_appearances["chased_in_play"]],
        "_without_chased_in_play"
    ),
    on=["batter", "game_year"],
    how="left"
)

hitters = full_comparison[
    ["batter", "player", "game_year", "chase_rate", "chase_plus", "xchase_plus"]
].merge(offense, on=["batter", "game_year"], how="left")

if hitters["xwoba"].isna().any():
    raise RuntimeError("Some qualified hitter-seasons have no plate appearances.")


# --------------------------------------------------
# SAME SEASON: like against like
#
# Chase+ (actual results) against wOBA, xChase+ (expected) against xwOBA,
# both without the chased balls in play.
# --------------------------------------------------

same_season_rows = []

for season in seasons:

    one = hitters[hitters["game_year"] == season]

    same_season_rows.append({
        "game_year": int(season),
        "hitters": len(one),
        "chase_plus_vs_woba": one["chase_plus"].corr(one["woba_without_chased_in_play"]),
        "xchase_plus_vs_xwoba": one["xchase_plus"].corr(one["xwoba_without_chased_in_play"]),
        "chase_rate_vs_woba": one["chase_rate"].corr(one["woba_without_chased_in_play"]),
        "chase_rate_vs_xwoba": one["chase_rate"].corr(one["xwoba_without_chased_in_play"]),
    })

same_season = pd.DataFrame(same_season_rows)
same_season.to_csv(OUTPUT_SAME_SEASON, index=False)
written_files.append(OUTPUT_SAME_SEASON)


# --------------------------------------------------
# NEXT SEASON: does it tell you anything about next year's xwOBA?
#
# For hitters qualified in both seasons, next season's xwOBA (all PAs)
# regressed on this season's xwOBA and chase rate, then again with the
# chase stat added. The gain in R^2 is what the chase stat knows about
# next year that this year's xwOBA and chase rate don't.
#
# "all pairs" stacks every pair of seasons with a separate intercept per
# pair, so a league-wide change between seasons can't count as a signal.
# --------------------------------------------------

def fit(target, predictors):
    """Least squares. Returns R^2, coefficients and their standard errors."""

    design = np.column_stack([np.ones(len(target))] + predictors)
    coefficients, _, _, _ = np.linalg.lstsq(design, target, rcond=None)

    residuals = target - design @ coefficients
    r_squared = 1 - residuals.var() / target.var()

    degrees_of_freedom = len(target) - design.shape[1]
    residual_variance = residuals @ residuals / degrees_of_freedom
    covariance = residual_variance * np.linalg.inv(design.T @ design)

    return r_squared, coefficients, np.sqrt(np.diag(covariance))


def next_season_test(paired, label):
    """One row per chase stat: plain r, R^2 without and with it, and its t."""

    target = paired["xwoba_next"].to_numpy()
    controls = [
        paired["xwoba"].to_numpy(),
        paired["chase_rate"].to_numpy(),
    ]

    # one intercept per season pair (the first pair is the baseline)
    pair_codes = pd.factorize(paired["pair"])[0]
    for code in range(1, pair_codes.max() + 1):
        controls.append((pair_codes == code).astype(float))

    base_r_squared, _, _ = fit(target, controls)

    rows = []

    for column, name in [("xchase_plus", "xChase+"), ("chase_plus", "Chase+")]:

        r_squared, coefficients, errors = fit(
            target, controls + [paired[column].to_numpy()]
        )

        rows.append({
            "seasons": label,
            "hitters": len(paired),
            "stat": name,
            "r_with_next_xwoba": paired[column].corr(paired["xwoba_next"]),
            "r_squared_without": base_r_squared,
            "r_squared_with": r_squared,
            "r_squared_gain": r_squared - base_r_squared,
            # xwOBA points (thousandths) per 10 points of the chase stat
            "next_xwoba_per_10_points": 10000 * coefficients[-1],
            "t_value": coefficients[-1] / errors[-1],
        })

    return rows


pairs = []

for first_season, second_season in zip(seasons[:-1], seasons[1:]):

    first = hitters[hitters["game_year"] == first_season]
    second = hitters[hitters["game_year"] == second_season][["batter", "xwoba"]]

    paired = first.merge(
        second.rename(columns={"xwoba": "xwoba_next"}),
        on="batter"
    )
    paired["pair"] = f"{int(first_season)}-{int(second_season)}"
    pairs.append(paired)

next_season_rows = []

for paired in pairs:
    next_season_rows += next_season_test(paired, paired["pair"].iloc[0])

if len(pairs) > 1:
    next_season_rows += next_season_test(pd.concat(pairs, ignore_index=True), "all pairs")

next_season = pd.DataFrame(next_season_rows)
next_season.to_csv(OUTPUT_NEXT_SEASON, index=False)
written_files.append(OUTPUT_NEXT_SEASON)

print()
print("=" * 78)
print("SAME SEASON: Chase+ vs wOBA, xChase+ vs xwOBA (without chased balls in play)")
print("=" * 78)
print()
print(same_season.round(3).to_string(index=False))

print()
print("=" * 78)
print("NEXT SEASON'S xwOBA, beyond this season's xwOBA and chase rate")
print("=" * 78)
print()
print(next_season.round(4).to_string(index=False))
print()
print(
    "r_squared_gain is what the chase stat adds. next_xwoba_per_10_points "
    "is in xwOBA points (.001) per 10 points of the stat. |t| above about "
    "2 is unlikely to be noise."
)


print()
print(f"Done. Saved under {PROJECT_DIR}:")

for path in written_files:
    print(f"  {path.relative_to(PROJECT_DIR)}")
