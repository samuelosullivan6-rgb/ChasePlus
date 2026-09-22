"""
Total offensive value per hitter-season, side by side with chase value.

The chase leaderboard answers a narrow question (how much a hitter gave
away by swinging at balls). This script values the whole hitter and then
compares the two, one season at a time:

  1. Total offensive run value per 600 PA, shrunk within season.
  2. Cost per chase: how expensive a hitter's average chase was (only for
     hitter-seasons with enough chases; the chase leaderboard leaves
     cost_per_chase blank below 120 chases).
  3. Does chase value predict offense? If it does not, the chase metric
     measures something real but unimportant, and the writeup should say
     so.

Two ways to value a plate appearance are reported:
  - RE24 (run_value): the actual change in run expectancy. Context
    dependent -- a grand slam is worth more than a solo home run.
  - Context neutral (neutral_value): the league-average run value of the
    outcome, matching the chase leaderboard, which is context neutral on
    purpose.
The gap between them reflects the chances a hitter's teammates gave him.

Inputs:  data/cleaned/plate_appearance_run_values.parquet
         results/run_value_by_event.csv
         results/chase_cost_leaderboard_by_season.csv (optional)
Output:  results/hitter_value_leaderboard.csv
"""

from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

# Per-season floor, prorated for an unfinished season exactly like the
# chase leaderboard, because the two tables are joined further down.
MINIMUM_PLATE_APPEARANCES_PER_SEASON = 300

PRORATE_FLOORS_BY_SEASON_LENGTH = True

PLATE_APPEARANCES_PER_SEASON = 600

LEADERBOARD_SIZE = 10


# --------------------------------------------------
# FILE LOCATIONS
#
# Paths are anchored to the project folder (the parent of scripts/), not
# to the directory the script is run from. Output names are fixed and
# overwritten on every run.
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
RESULTS_DIR = PROJECT_DIR / "results"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PA_VALUE_FILE = CLEAN_DIR / "plate_appearance_run_values.parquet"
EVENT_VALUE_FILE = RESULTS_DIR / "run_value_by_event.csv"
CHASE_LEADERBOARD_FILE = (
    RESULTS_DIR / "chase_cost_leaderboard_by_season.csv"
)

OUTPUT_FILE = RESULTS_DIR / "hitter_value_leaderboard.csv"


# --------------------------------------------------
# SHRINKAGE
#
# Same DerSimonian-Laird estimator as the chase leaderboard. Without it,
# the extremes of any leaderboard belong to whoever had the fewest plate
# appearances.
# --------------------------------------------------

def estimate_between_hitter_variance(effects, standard_errors):
    """
    Returns tau squared (the real spread between hitters with measurement
    noise removed) and the inverse-variance-weighted mean.
    """

    effects = np.asarray(effects, dtype=float)
    standard_errors = np.asarray(standard_errors, dtype=float)

    weights = 1.0 / (standard_errors ** 2)

    weighted_mean = (
        np.sum(weights * effects)
        / np.sum(weights)
    )

    q_statistic = np.sum(
        weights * (effects - weighted_mean) ** 2
    )

    k = len(effects)

    scaling = (
        np.sum(weights)
        - np.sum(weights ** 2) / np.sum(weights)
    )

    tau_squared = (q_statistic - (k - 1)) / scaling

    return max(tau_squared, 0.0), weighted_mean


def shrink(effects, standard_errors):
    """
    Shrunk estimates, the shrinkage factor for each one, the between-hitter
    standard deviation (tau) and the pooled mean.
    """

    tau_squared, pooled_mean = estimate_between_hitter_variance(
        effects,
        standard_errors
    )

    sampling_variance = np.asarray(standard_errors, dtype=float) ** 2

    if tau_squared > 0:
        factor = sampling_variance / (sampling_variance + tau_squared)
    else:
        factor = np.ones_like(sampling_variance)

    shrunk = (
        np.asarray(effects, dtype=float)
        - factor * (np.asarray(effects, dtype=float) - pooled_mean)
    )

    return shrunk, factor, np.sqrt(tau_squared), pooled_mean


def attach_names(table, id_column="batter"):
    """
    Add a 'player' column from pybaseball's player register. If the lookup
    fails (for example with no network), print why and return the table
    unchanged.
    """

    try:

        from pybaseball import playerid_reverse_lookup

        ids = [
            int(one_id)
            for one_id in table[id_column].dropna().unique()
        ]

        lookup = playerid_reverse_lookup(ids, key_type="mlbam")

        lookup["player"] = (
            lookup["name_first"].str.title()
            + " "
            + lookup["name_last"].str.title()
        )

        # One name per id. A duplicated id in the register would otherwise
        # duplicate that hitter's rows in the merge.
        lookup = lookup.drop_duplicates(subset="key_mlbam")

        named = table.merge(
            lookup[["key_mlbam", "player"]].rename(
                columns={"key_mlbam": id_column}
            ),
            on=id_column,
            how="left",
            validate="many_to_one"
        )

        if len(named) != len(table):
            raise RuntimeError("the name merge changed the number of rows")

        return named

    except Exception as error:

        print(f"Could not look up player names ({error}).")

        return table


# --------------------------------------------------
# LOAD
# --------------------------------------------------

print("Loading plate appearance run values...")

pa = pd.read_parquet(PA_VALUE_FILE)

print(f"Plate appearances: {len(pa):,}")

print()
print(
    "Note: this file excludes half innings that ended because the "
    "game ended, so a hitter's count here misses those plate "
    "appearances: 0.4% of a qualified hitter's season on average, "
    "1.7% at the most. The chase leaderboard counts plate "
    "appearances a different way -- every one with an analyzable "
    "pitch -- so the two plate_appearances columns in the saved file "
    "do not have to agree, and they differ by -6 to +31."
)

event_values = pd.read_csv(EVENT_VALUE_FILE)


# --------------------------------------------------
# CONTEXT-NEUTRAL VALUE
#
# Each plate appearance also gets the league-average run value of its
# outcome, so a home run is worth the same whatever the base-out state.
# --------------------------------------------------

pa = pa.merge(
    event_values[["event", "run_value"]].rename(
        columns={"run_value": "neutral_value"}
    ),
    on="event",
    how="left"
)

missing_neutral = pa["neutral_value"].isna().sum()

if missing_neutral > 0:
    print()
    print(
        f"{missing_neutral:,} plate appearances have an outcome "
        f"with no league value, so they only count toward RE24."
    )


# --------------------------------------------------
# QUALIFICATION FLOORS, BY SEASON
#
# Same proration as the chase leaderboard (games in the season divided by
# games in the longest season), so both tables admit the same kind of
# hitter-season.
# --------------------------------------------------

season_floors = (
    pa
    .groupby("game_year")
    .agg(games=("game_pk", "nunique"))
    .reset_index()
)

longest_season_games = int(season_floors["games"].max())

season_floors["season_share"] = (
    season_floors["games"] / longest_season_games
)

if PRORATE_FLOORS_BY_SEASON_LENGTH:
    floor_scale = season_floors["season_share"]
else:
    floor_scale = 1.0

season_floors["minimum_plate_appearances"] = np.round(
    MINIMUM_PLATE_APPEARANCES_PER_SEASON * floor_scale
).astype(int)

print()
print("Plate appearances needed to qualify, by season:")
print()
print(
    season_floors
    .round(3)
    .to_string(index=False)
)


# --------------------------------------------------
# AGGREGATE BY HITTER AND SEASON
# --------------------------------------------------

hitters = (
    pa
    .groupby(["batter", "game_year"])
    .agg(
        plate_appearances=("run_value", "size"),
        total_run_value=("run_value", "sum"),
        mean_run_value=("run_value", "mean"),
        run_value_spread=("run_value", "std"),
        total_neutral_value=("neutral_value", "sum"),
    )
    .reset_index()
)

hitters["runs_per_600_pa"] = (
    hitters["mean_run_value"]
    * PLATE_APPEARANCES_PER_SEASON
)

hitters["neutral_runs_per_600_pa"] = (
    hitters["total_neutral_value"]
    / hitters["plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
)

# Positive means the hitter's chances came in better-than-average
# situations (teammates on base).
hitters["context_bonus_per_600_pa"] = (
    hitters["runs_per_600_pa"]
    - hitters["neutral_runs_per_600_pa"]
)

hitters["standard_error_per_600_pa"] = (
    hitters["run_value_spread"]
    / np.sqrt(hitters["plate_appearances"])
    * PLATE_APPEARANCES_PER_SEASON
)

hitters = hitters.merge(
    season_floors[["game_year", "minimum_plate_appearances"]],
    on="game_year",
    how="left"
)

qualified = hitters[
    (
        hitters["plate_appearances"]
        >= hitters["minimum_plate_appearances"]
    )
    & (hitters["standard_error_per_600_pa"] > 0)
    & hitters["standard_error_per_600_pa"].notna()
].copy()


# --------------------------------------------------
# SHRINK WITHIN EACH SEASON
#
# The prior is fit season by season, like the chase leaderboard's, so no
# hitter is pulled toward a mean built from seasons he did not play in.
# --------------------------------------------------

seasons = sorted(int(season) for season in qualified["game_year"].unique())

shrunk_seasons = []

offense_rows = []

for season in seasons:

    one_season = qualified[
        qualified["game_year"] == season
    ].copy()

    (
        one_season["runs_per_600_shrunk"],
        one_season["shrinkage_factor"],
        offense_spread,
        offense_mean
    ) = shrink(
        one_season["runs_per_600_pa"],
        one_season["standard_error_per_600_pa"]
    )

    shrunk_seasons.append(one_season)

    offense_rows.append(
        {
            "game_year": season,
            "hitters": len(one_season),
            "true_spread": offense_spread,
            "pooled_mean": offense_mean,
            "median_shrinkage": np.median(
                one_season["shrinkage_factor"]
            ),
            "pa_vs_shrinkage": one_season["plate_appearances"].corr(
                one_season["shrinkage_factor"]
            ),
        }
    )

qualified = pd.concat(shrunk_seasons, ignore_index=True)

print()
print("=" * 78)
print("HOW MUCH DO HITTERS DIFFER IN TOTAL OFFENSE, BY SEASON")
print("=" * 78)

print()
print(pd.DataFrame(offense_rows).round(3).to_string(index=False))

print()
print(
    "pa_vs_shrinkage must be negative in every season: more plate "
    "appearances has to mean less shrinkage."
)

qualified = attach_names(qualified)


# --------------------------------------------------
# THE CHASE LEADERBOARD, SEASON BY SEASON
# --------------------------------------------------

if CHASE_LEADERBOARD_FILE.exists():

    chase = pd.read_csv(CHASE_LEADERBOARD_FILE)

else:

    chase = None

    print()
    print(
        f"No per-season chase leaderboard found at "
        f"{CHASE_LEADERBOARD_FILE}. Run buildchaseleaderboard.py "
        f"to get the chase sections."
    )


# --------------------------------------------------
# THE THREE LEADERBOARDS, ONE SEASON AT A TIME
# --------------------------------------------------

offense_columns = [
    column
    for column in [
        "player",
        "plate_appearances",
        "runs_per_600_pa",
        "neutral_runs_per_600_pa",
        "context_bonus_per_600_pa",
        "runs_per_600_shrunk",
    ]
    if column in qualified.columns
]

context_columns = [
    column
    for column in [
        "player",
        "plate_appearances",
        "runs_per_600_pa",
        "neutral_runs_per_600_pa",
        "context_bonus_per_600_pa",
    ]
    if column in qualified.columns
]

correlation_rows = []

for season in seasons:

    one_season = qualified[qualified["game_year"] == season]

    print()
    print("=" * 78)
    print(f"{season}: TOTAL OFFENSIVE RUN VALUE")
    print(f"({len(one_season)} qualified hitters)")
    print("=" * 78)

    by_offense = one_season.sort_values(
        "runs_per_600_shrunk",
        ascending=False
    )

    print()
    print("Runs created above an average hitter, per 600 plate appearances.")

    print()
    print(f"BEST {LEADERBOARD_SIZE}")
    print()
    print(
        by_offense[offense_columns]
        .head(LEADERBOARD_SIZE)
        .round(2)
        .to_string(index=False)
    )

    print()
    print(f"WORST {LEADERBOARD_SIZE}")
    print()
    print(
        by_offense[offense_columns]
        .tail(LEADERBOARD_SIZE)
        .iloc[::-1]
        .round(2)
        .to_string(index=False)
    )

    # --------------------------------------------------
    # CONTEXT: WHO GOT THE CHANCES
    #
    # The gap between context-dependent and context-neutral value is a
    # fact about a hitter's teammates, not about him.
    # --------------------------------------------------

    by_context = one_season.sort_values(
        "context_bonus_per_600_pa",
        ascending=False
    )

    print()
    print(f"{season}: MOST HELPED BY WHEN THEIR CHANCES CAME")
    print()
    print(
        by_context[context_columns]
        .head(5)
        .round(2)
        .to_string(index=False)
    )

    print()
    print(f"{season}: LEAST HELPED")
    print()
    print(
        by_context[context_columns]
        .tail(5)
        .iloc[::-1]
        .round(2)
        .to_string(index=False)
    )

    if chase is None:
        continue

    # --------------------------------------------------
    # COST PER CHASE
    #
    # Total chase damage mixes how often a hitter chases with how costly
    # each chase is. This isolates the second.
    # --------------------------------------------------

    chase_season = chase[chase["game_year"] == season]

    chase_columns = [
        column
        for column in [
            "player",
            "plate_appearances",
            "chase_rate",
            "chases",
            "cost_per_chase",
            "cost_per_chase_se",
            "runs_saved_shrunk",
            "chase_plus",
            "standard_error_per_600_pa",
        ]
        if column in chase_season.columns
    ]

    # Blank cost_per_chase means too few chases to rank. Left in, the
    # blanks would sort to the end, which is where the "most expensive"
    # list below reads from.
    by_cost = (
        chase_season
        .dropna(subset=["cost_per_chase"])
        .sort_values("cost_per_chase", ascending=True)
    )

    unranked = int(chase_season["cost_per_chase"].isna().sum())

    print()
    print(f"{season}: CHEAPEST {LEADERBOARD_SIZE} CHASERS")
    print("(when these hitters chase, it barely costs anything)")

    if unranked > 0:
        print(
            f"({unranked} qualified hitter(s) chased too few times to "
            "have a cost per chase and are not ranked here)"
        )
    print()
    print(
        by_cost[chase_columns]
        .head(LEADERBOARD_SIZE)
        .round(3)
        .to_string(index=False)
    )

    print()
    print(f"{season}: MOST EXPENSIVE {LEADERBOARD_SIZE} CHASERS")
    print()
    print(
        by_cost[chase_columns]
        .tail(LEADERBOARD_SIZE)
        .iloc[::-1]
        .round(3)
        .to_string(index=False)
    )

    # --------------------------------------------------
    # DOES CHASE VALUE PREDICT OFFENSE (collected here, printed below)
    # --------------------------------------------------

    paired = one_season.merge(
        chase_season[["batter", "chase_rate", "runs_saved_shrunk"]],
        on="batter",
        how="inner"
    )

    if len(paired) <= 10:
        continue

    chase_correlation = (
        paired["runs_saved_shrunk"]
        .corr(paired["runs_per_600_shrunk"])
    )

    rate_correlation = (
        paired["chase_rate"]
        .corr(paired["runs_per_600_shrunk"])
    )

    correlation_rows.append(
        {
            "game_year": season,
            "hitters": len(paired),
            "runs_saved_vs_offense": chase_correlation,
            "chase_rate_vs_offense": rate_correlation,
            "offense_explained": chase_correlation ** 2,
        }
    )


# --------------------------------------------------
# DOES CHASE VALUE PREDICT OFFENSE
# --------------------------------------------------

if len(correlation_rows) > 0:

    correlations = pd.DataFrame(correlation_rows)

    print()
    print("=" * 78)
    print("DOES CHASE VALUE PREDICT OFFENSE")
    print("=" * 78)

    print()
    print(correlations.round(3).to_string(index=False))

    print()
    print(
        "The comparison is the point. If runs saved tracks offense "
        "more closely than chase rate does, then my metric carries "
        "information about hitting that chase rate throws away, and "
        "that is the strongest argument the project has. Reading it "
        "one season at a time also shows whether the answer holds "
        "up or whether one year is carrying it."
    )

    wins = (
        correlations["runs_saved_vs_offense"].abs()
        > correlations["chase_rate_vs_offense"].abs()
    ).sum()

    print()
    print(
        f"Runs saved beats plain chase rate in {wins} of "
        f"{len(correlations)} seasons."
    )

    print()
    print(
        "Expect offense_explained to be small. Chasing is one "
        "decision among many, and power and contact quality do most "
        "of the work. A small number here is not a failure, it is "
        "the correct size of the thing being measured."
    )

    print()
    print(
        "CAVEAT: this is not a fully independent check. "
        "runs_saved_shrunk and neutral_runs_per_600_pa are both "
        "built on the same run-expectancy and event-value tables "
        "from BuildRunValueTables.py, so part of the correlation "
        "above is shared plumbing, not two independently-measured "
        "quantities happening to agree. It is still informative "
        "-- chase rate is built on nothing shared with offense at "
        "all, and it still correlates more weakly -- but it is "
        "construct validation, not a fully independent one."
    )


# --------------------------------------------------
# SAVE
# --------------------------------------------------

if chase is not None:

    output_table = qualified.merge(
        chase[
            [
                "batter",
                "game_year",
                "chase_rate",
                "chases",
                "cost_per_chase",
                "cost_per_chase_se",
                "runs_saved_shrunk",
                "chase_plus",
                "runs_saved_vs_anchor_shrunk",
            ]
        ],
        on=["batter", "game_year"],
        how="left"
    )

else:

    output_table = qualified

(
    output_table
    .sort_values(
        ["game_year", "runs_per_600_shrunk"],
        ascending=[True, False]
    )
    .to_csv(OUTPUT_FILE, index=False)
)

print()
print("Saved (overwriting the previous run):")
print(OUTPUT_FILE)
