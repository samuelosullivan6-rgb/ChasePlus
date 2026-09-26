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
         data/cleaned/baseline_chase_pitches.parquet (descriptions only)
         results/hitter_value_leaderboard.csv
         results/xchase/hitter_value_leaderboard.csv (offense test only;
         skipped if either is missing)
Outputs: results/xchase/xchase_comparison_<season>.csv (one per season)
         results/xchase/xchase_comparison_by_season.csv
         results/xchase/xchase_reliability.csv
         results/xchase/xchase_leaderboard_<season>.csv (one per season)
         results/xchase/xchase_leaderboard_by_season.csv
         results/xchase/regression_candidates.csv
         results/xchase/xchase_offense_correlation.csv

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

CHASE_OFFENSE = RESULTS_DIR / "hitter_value_leaderboard.csv"
X_OFFENSE = XCHASE_DIR / "hitter_value_leaderboard.csv"

OUTPUT_BY_SEASON = XCHASE_DIR / "xchase_comparison_by_season.csv"
SEASON_FILE_NAME = "xchase_comparison_{season}.csv"
OUTPUT_RELIABILITY = XCHASE_DIR / "xchase_reliability.csv"

OUTPUT_LEADERBOARD = XCHASE_DIR / "xchase_leaderboard_by_season.csv"
LEADERBOARD_FILE_NAME = "xchase_leaderboard_{season}.csv"
OUTPUT_CANDIDATES = XCHASE_DIR / "regression_candidates.csv"
OUTPUT_OFFENSE = XCHASE_DIR / "xchase_offense_correlation.csv"

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
# WHICH ONE TRACKS TOTAL OFFENSE?
#
# Correlation of Chase+, xChase+ and chase rate with each hitter's total
# offense (runs_per_600_shrunk from 05_build_hitter_value_leaderboard.py), one
# season at a time.
#
# Not a fair race for Chase+: its balls in play are priced from the same
# plate appearance results that make up offense, so part of its
# correlation is the same runs counted twice. xChase+ prices those balls
# in play from xwOBA, so less of that overlap is left in it.
# --------------------------------------------------

if CHASE_OFFENSE.exists() and X_OFFENSE.exists():

    chase_offense = pd.read_csv(CHASE_OFFENSE)
    x_offense = pd.read_csv(X_OFFENSE)

    if not np.allclose(
        chase_offense["runs_per_600_shrunk"],
        x_offense["runs_per_600_shrunk"],
        rtol=0,
        atol=1e-9
    ):
        raise RuntimeError(
            "The two hitter_value_leaderboard.csv files disagree on "
            "offense. Rerun 05_build_hitter_value_leaderboard.py with and "
            "without --expected-contact."
        )

    offense_rows = []

    for season in seasons:

        one_season = chase_offense[
            (chase_offense["game_year"] == season)
            & chase_offense["chase_plus"].notna()
        ][["batter", "runs_per_600_shrunk", "chase_rate", "chase_plus"]]

        one_season = one_season.merge(
            x_offense[x_offense["game_year"] == season][["batter", "xchase_plus"]],
            on="batter",
            how="inner"
        )

        offense_rows.append({
            "game_year": int(season),
            "hitters": len(one_season),
            "chase_plus_vs_offense": one_season["chase_plus"].corr(
                one_season["runs_per_600_shrunk"]
            ),
            "xchase_plus_vs_offense": one_season["xchase_plus"].corr(
                one_season["runs_per_600_shrunk"]
            ),
            "chase_rate_vs_offense": one_season["chase_rate"].corr(
                one_season["runs_per_600_shrunk"]
            ),
        })

    offense_table = pd.DataFrame(offense_rows)

    offense_table.to_csv(OUTPUT_OFFENSE, index=False)

    written_files.append(OUTPUT_OFFENSE)

    print()
    print("=" * 78)
    print("WHICH ONE TRACKS TOTAL OFFENSE (correlation with runs per 600 PA, shrunk)")
    print("=" * 78)
    print()
    print(offense_table.round(3).to_string(index=False))
    print()
    print(
        "Chase+ has a head start here: its balls in play are priced from "
        "the same results that make up offense. xChase+ removes most of "
        "that overlap, so a lower number for it is expected and is not by "
        "itself a point against it."
    )

else:

    print()
    print(
        "Skipping the offense test: run 05_build_hitter_value_leaderboard.py "
        "with and without --expected-contact first."
    )

print()
print(f"Done. Saved under {PROJECT_DIR}:")

for path in written_files:
    print(f"  {path.relative_to(PROJECT_DIR)}")
