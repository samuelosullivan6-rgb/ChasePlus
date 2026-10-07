"""
xChase+ by handedness matchup: four leaderboards per season.

A separate look at xChase+, not a change to it. Every pitch keeps the
price the xChase+ run gave it (04_build_chase_leaderboard.py
--expected-contact); this script only splits the pitches by matchup and
ranks hitters within each one:

    R/R   right-handed batter against a right-handed pitcher
    L/L   left-handed batter against a left-handed pitcher
    R/L   right-handed batter against a left-handed pitcher
    L/R   left-handed batter against a right-handed pitcher

A switch hitter shows up on R/L and L/R (the side he actually batted
from).

Each board is built like the main leaderboard, one season at a time:

  - Baseline: what the league lost on the same kind of pitch IN THE SAME
    MATCHUP (season x matchup x count x distance bucket). So 100 on a
    board is the average hitter in that matchup, not the league average.
    Same-handed matchups are harder; the league table says by how much on
    the main xChase+ scale.
  - Scale: the season's overall league chase cost per 600 PA, the same as
    the main leaderboard, so a point is the same number of runs on every
    board.
  - Qualifying: the main floors (opportunities and PA) times the league's
    share of plate appearances against that pitcher hand, prorated for an
    unfinished season like the main floors.
  - Shrinkage: DerSimonian-Laird within each season and matchup, toward
    that board's mean.

The samples are a fraction of a season (about a quarter for the boards
against left-handed pitchers), so the boards are noisier than the main
one. The year-to-year correlations this script writes say how much.
The difference between a hitter's matchup score and his overall score is
mostly noise in a single season.

Inputs:  data/cleaned/xchase_costs_by_pitch.parquet
         data/cleaned/baseline_chase_pitches.parquet (handedness, PA counts)
         results/xchase/chase_cost_leaderboard_by_season.csv
         results/xchase/chase_plus_league_scale.csv
Outputs: results/xchase/matchups/xchase_matchup_leaderboard_<season>.csv
         results/xchase/matchups/xchase_matchup_leaderboard_by_season.csv
         results/xchase/matchups/xchase_matchup_league.csv
         results/xchase/matchups/xchase_matchup_reliability.csv
"""

import ast
from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

# Batter / pitcher, in the order the boards are printed and saved.
MATCHUPS = ["R/R", "L/L", "R/L", "L/R"]

PLATE_APPEARANCES_PER_SEASON = 600

# How many hitters each printed board shows at the top and at the bottom.
LIST_SIZE = 5

# A (season, matchup, count, distance) baseline cell with fewer pitches
# than this is counted as thin.
THIN_CELL_WARNING_PITCHES = 50


# --------------------------------------------------
# FILE LOCATIONS
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

SCRIPT_DIR = Path(__file__).resolve().parent
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
RESULTS_DIR = PROJECT_DIR / "results"
XCHASE_DIR = RESULTS_DIR / "xchase"
OUTPUT_DIR = XCHASE_DIR / "matchups"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LEADERBOARD_SCRIPT = SCRIPT_DIR / "04_build_chase_leaderboard.py"

X_PITCHES = CLEAN_DIR / "xchase_costs_by_pitch.parquet"
PITCH_FILE = CLEAN_DIR / "baseline_chase_pitches.parquet"
X_BY_SEASON = XCHASE_DIR / "chase_cost_leaderboard_by_season.csv"
X_SCALE = XCHASE_DIR / "chase_plus_league_scale.csv"

# Player names (Chadwick register), downloaded once and cached.
PLAYER_REGISTER_FILE = PROJECT_DIR / "data" / "raw" / "chadwick_register.parquet"

SEASON_FILE_NAME = "xchase_matchup_leaderboard_{season}.csv"
OUTPUT_BY_SEASON = OUTPUT_DIR / "xchase_matchup_leaderboard_by_season.csv"
OUTPUT_LEAGUE = OUTPUT_DIR / "xchase_matchup_league.csv"
OUTPUT_RELIABILITY = OUTPUT_DIR / "xchase_matchup_reliability.csv"

for needed in [X_PITCHES, PITCH_FILE, X_BY_SEASON, X_SCALE]:
    if not needed.exists():
        raise FileNotFoundError(
            f"{needed.relative_to(PROJECT_DIR)} is missing. Run "
            "04_build_chase_leaderboard.py --expected-contact first."
        )


def read_settings(names):
    """
    Read top-level literal assignments (NAME = <literal>) out of the
    leaderboard script without running it, so the floors here always
    follow the main leaderboard's.
    """

    tree = ast.parse(LEADERBOARD_SCRIPT.read_text())
    found = {}

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in names:
                found[target.id] = ast.literal_eval(node.value)

    missing = set(names) - set(found)

    if missing:
        raise RuntimeError(
            f"Could not find {sorted(missing)} in {LEADERBOARD_SCRIPT.name}"
        )

    return found


SETTINGS = read_settings([
    "MINIMUM_OPPORTUNITIES_PER_SEASON",
    "MINIMUM_PLATE_APPEARANCES_PER_SEASON",
    "PRORATE_FLOORS_BY_SEASON_LENGTH",
    "XCHASE_PLUS_VERSION",
])


# --------------------------------------------------
# PITCHES, WITH THEIR MATCHUP
#
# Every out-of-zone pitch the xChase+ run priced, with the batter's side
# and the pitcher's hand from the cleaned pitch file.
# --------------------------------------------------

pitch_key = ["game_pk", "at_bat_number", "pitch_number"]

pitches = pd.read_parquet(
    X_PITCHES,
    columns=pitch_key + [
        "batter", "game_year", "balls", "strikes", "distance_bucket",
        "is_chase", "chase_cost", "runs_saved",
    ]
)

handedness = pd.read_parquet(
    PITCH_FILE,
    columns=pitch_key + ["stand", "p_throws"]
)

pitches = pitches.merge(handedness, on=pitch_key, how="left")

no_matchup = pitches["stand"].isna() | pitches["p_throws"].isna()

if no_matchup.any():
    raise RuntimeError(
        f"{int(no_matchup.sum()):,} priced pitches have no batter side or "
        "pitcher hand."
    )

pitches["matchup"] = pitches["stand"] + "/" + pitches["p_throws"]

print(
    f"{len(pitches):,} out-of-zone pitches from the xChase+ run "
    f"({SETTINGS['XCHASE_PLUS_VERSION']}), split by matchup."
)


# --------------------------------------------------
# PLATE APPEARANCES PER HITTER, SEASON AND MATCHUP
#
# Counted the same way as the main leaderboard (every analyzable pitch,
# walk-off plate appearances included, and a plate appearance with a
# pinch hitter partway through counted once for each batter). A plate
# appearance counts toward the matchup of the batter's first pitch in it,
# so a pitching change in the middle of one does not count it twice.
# --------------------------------------------------

plate_appearances = (
    pd.read_parquet(
        PITCH_FILE,
        columns=pitch_key + [
            "batter", "game_year", "stand", "p_throws", "is_analyzable",
        ]
    )
    .query("is_analyzable == 1")
    .sort_values(pitch_key)
    .drop_duplicates(subset=["batter", "game_pk", "at_bat_number"])
)

plate_appearances["matchup"] = (
    plate_appearances["stand"] + "/" + plate_appearances["p_throws"]
)

pa_counts = (
    plate_appearances
    .groupby(["batter", "game_year", "matchup"])
    .size()
    .rename("plate_appearances")
    .reset_index()
)


# --------------------------------------------------
# THE LEAGUE SCALE, AND EACH MATCHUP ON IT
#
# league_chase_cost_per_600_pa comes from the main xChase+ run, so a point
# on a matchup board is worth the same runs as on the main leaderboard.
#
# matchup_xchase_plus is how the average hitter did in each matchup
# against the MAIN baseline (runs_saved in the pitch file): below 100 in
# same-handed matchups, above it in opposite-handed ones. The boards below
# measure each hitter against his own matchup's average instead.
# --------------------------------------------------

league_scale = pd.read_csv(X_SCALE, dtype={"run_fingerprint": str})

scale_by_season = league_scale.set_index("game_year")[
    "league_chase_cost_per_600_pa"
]

league = (
    pitches
    .groupby(["game_year", "matchup"])
    .agg(
        opportunities=("is_chase", "size"),
        chases=("is_chase", "sum"),
        chase_rate=("is_chase", "mean"),
        total_cost=("chase_cost", "sum"),
        main_runs_saved=("runs_saved", "sum"),
    )
    .reset_index()
    .merge(
        pa_counts
        .groupby(["game_year", "matchup"])["plate_appearances"]
        .sum()
        .reset_index(),
        on=["game_year", "matchup"],
        how="left"
    )
)

league["chase_rate"] *= 100
league["cost_per_chase"] = league["total_cost"] / league["chases"]
league["league_chase_cost_per_600_pa"] = (
    league["game_year"].map(scale_by_season)
)
league["matchup_xchase_plus"] = (
    100
    + 100
    * league["main_runs_saved"]
    / league["plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
    / league["league_chase_cost_per_600_pa"]
)

# Share of each season's plate appearances against each pitcher hand,
# for the floors below.
pitcher_hand = league["matchup"].str[-1]

league["share_of_pa_vs_this_hand"] = (
    league.groupby([league["game_year"], pitcher_hand])["plate_appearances"]
    .transform("sum")
    / league.groupby("game_year")["plate_appearances"].transform("sum")
)

print()
print("=" * 78)
print("THE AVERAGE HITTER IN EACH MATCHUP, ON THE MAIN xCHASE+ SCALE")
print("=" * 78)
print()
print(
    league
    .pivot(index="game_year", columns="matchup", values="matchup_xchase_plus")
    [MATCHUPS]
    .round(1)
    .to_string()
)


# --------------------------------------------------
# THE MATCHUP BASELINE
#
# Each pitch against what the league lost on the same kind of pitch in the
# same matchup: same season, matchup, count and distance bucket.
# --------------------------------------------------

baseline_cell = ["game_year", "matchup", "balls", "strikes", "distance_bucket"]

pitches["matchup_expected_cost"] = (
    pitches.groupby(baseline_cell)["chase_cost"].transform("mean")
)

pitches["matchup_runs_saved"] = (
    pitches["matchup_expected_cost"] - pitches["chase_cost"]
)

cell_sizes = pitches.groupby(baseline_cell).size()

thin_cells = cell_sizes[cell_sizes < THIN_CELL_WARNING_PITCHES]

if len(thin_cells) > 0:
    print()
    print(
        f"{len(thin_cells)} of {len(cell_sizes)} (season, matchup, count, "
        f"distance) baseline cells have fewer than "
        f"{THIN_CELL_WARNING_PITCHES} pitches "
        f"({int(thin_cells.sum()):,} pitches in all), mostly 3-0 counts; "
        "their baselines are noisy."
    )

# The baseline is built from these same pitches, so every season and
# matchup has to add to zero.
leftover = pitches.groupby(["game_year", "matchup"])["matchup_runs_saved"].sum()

if (leftover.abs() > 1e-6).any():
    raise RuntimeError(
        "Matchup runs saved do not add up to zero in every season and "
        "matchup. Check the baseline cells."
    )


# --------------------------------------------------
# PER HITTER, SEASON AND MATCHUP
# --------------------------------------------------

hitters = (
    pitches
    .groupby(["batter", "game_year", "matchup"])
    .agg(
        opportunities=("is_chase", "size"),
        chases=("is_chase", "sum"),
        chase_rate=("is_chase", "mean"),
        total_cost=("chase_cost", "sum"),
        expected_cost=("matchup_expected_cost", "sum"),
        standard_deviation=("matchup_runs_saved", "std"),
    )
    .reset_index()
    .merge(pa_counts, on=["batter", "game_year", "matchup"], how="left")
)

hitters["chase_rate"] *= 100

# A hitter's opportunities in a matchup whose plate appearances all began
# against the other hand (a pitching change mid plate appearance) have no
# PA of their own; there are only a handful, and they cannot qualify.
hitters["plate_appearances"] = hitters["plate_appearances"].fillna(0).astype(int)

# Every hitter-season's matchups have to add up to his main line.
main = pd.read_csv(X_BY_SEASON)

totals = (
    hitters
    .groupby(["batter", "game_year"])[["opportunities", "chases"]]
    .sum()
    .join(
        pa_counts.groupby(["batter", "game_year"])["plate_appearances"].sum()
    )
    .reset_index()
    .merge(
        main[["batter", "game_year", "opportunities", "chases",
              "plate_appearances", "xchase_plus"]],
        on=["batter", "game_year"],
        suffixes=("", "_main")
    )
)

for column in ["opportunities", "chases", "plate_appearances"]:
    if not (totals[column] == totals[f"{column}_main"]).all():
        raise RuntimeError(
            f"{column} by matchup does not add up to the main leaderboard."
        )

print()
print(
    f"Check passed: the four matchups add up to the main leaderboard for "
    f"all {len(totals):,} qualified hitter-seasons."
)

with_pa = hitters["plate_appearances"] > 0

hitters["runs_saved_per_600_pa"] = np.where(
    with_pa,
    (hitters["expected_cost"] - hitters["total_cost"])
    / hitters["plate_appearances"].where(with_pa)
    * PLATE_APPEARANCES_PER_SEASON,
    np.nan
)

# Standard error of the hitter's mean per pitch, on the same scale (same
# treatment as the main leaderboard).
hitters["standard_error_per_600_pa"] = (
    hitters["standard_deviation"]
    / np.sqrt(hitters["opportunities"])
    * hitters["opportunities"]
    / hitters["plate_appearances"].where(with_pa)
    * PLATE_APPEARANCES_PER_SEASON
)

hitters["league_chase_cost_per_600_pa"] = (
    hitters["game_year"].map(scale_by_season)
)

hitters["xchase_plus_raw"] = (
    100
    + 100
    * hitters["runs_saved_per_600_pa"]
    / hitters["league_chase_cost_per_600_pa"]
)

hitters["xchase_plus_se"] = (
    100
    * hitters["standard_error_per_600_pa"]
    / hitters["league_chase_cost_per_600_pa"]
)

# Every hitter in a matchup, weighted by plate appearances, has to average
# 100 on that matchup's own baseline. Not exactly 100: the few pitches
# thrown after a mid plate appearance pitching change count in their own
# matchup, but their plate appearance counts in the one it started in.
# That moves the average by about a thousandth of a point.
for (season, matchup), board in hitters[with_pa].groupby(["game_year", "matchup"]):

    average = np.average(
        board["xchase_plus_raw"],
        weights=board["plate_appearances"]
    )

    if abs(average - 100) > 0.01:
        raise RuntimeError(
            f"{season} {matchup}: the average hitter is {average:.4f}, not 100."
        )


# --------------------------------------------------
# WHO QUALIFIES
#
# The main floors times the league's share of plate appearances against
# this pitcher hand, then prorated by season length exactly like the main
# leaderboard (games / the longest season's games).
# --------------------------------------------------

games = pitches.groupby("game_year")["game_pk"].nunique()

if SETTINGS["PRORATE_FLOORS_BY_SEASON_LENGTH"]:
    season_scale = games / games.max()
else:
    season_scale = games * 0 + 1.0

league["minimum_opportunities"] = np.round(
    SETTINGS["MINIMUM_OPPORTUNITIES_PER_SEASON"]
    * league["share_of_pa_vs_this_hand"]
    * league["game_year"].map(season_scale)
).astype(int)

league["minimum_plate_appearances"] = np.round(
    SETTINGS["MINIMUM_PLATE_APPEARANCES_PER_SEASON"]
    * league["share_of_pa_vs_this_hand"]
    * league["game_year"].map(season_scale)
).astype(int)

hitters = hitters.merge(
    league[["game_year", "matchup", "minimum_opportunities",
            "minimum_plate_appearances"]],
    on=["game_year", "matchup"],
    how="left"
)

qualified = hitters[
    (hitters["opportunities"] >= hitters["minimum_opportunities"])
    & (hitters["plate_appearances"] >= hitters["minimum_plate_appearances"])
    & (hitters["standard_error_per_600_pa"] > 0)
].copy()


# --------------------------------------------------
# SHRINK WITHIN EACH SEASON AND MATCHUP
#
# Same DerSimonian-Laird estimator as the main leaderboard, one board at a
# time: each hitter is pulled toward his board's mean in proportion to his
# standard error.
# --------------------------------------------------

def estimate_between_hitter_variance(effects, standard_errors):
    """
    Returns tau squared (the real spread between hitters, with measurement
    noise removed) and the inverse-variance-weighted mean.
    """

    effects = np.asarray(effects, dtype=float)
    standard_errors = np.asarray(standard_errors, dtype=float)

    weights = 1.0 / (standard_errors ** 2)

    weighted_mean = np.sum(weights * effects) / np.sum(weights)

    q_statistic = np.sum(weights * (effects - weighted_mean) ** 2)

    scaling = np.sum(weights) - np.sum(weights ** 2) / np.sum(weights)

    tau_squared = (q_statistic - (len(effects) - 1)) / scaling

    return max(tau_squared, 0.0), weighted_mean


boards = []
board_rows = []

for (season, matchup), board in qualified.groupby(["game_year", "matchup"]):

    board = board.copy()

    tau_squared, pooled_mean = estimate_between_hitter_variance(
        board["runs_saved_per_600_pa"],
        board["standard_error_per_600_pa"]
    )

    sampling_variance = board["standard_error_per_600_pa"] ** 2

    if tau_squared > 0:
        board["shrinkage_factor"] = (
            sampling_variance / (sampling_variance + tau_squared)
        )
    else:
        board["shrinkage_factor"] = 1.0

    board["runs_saved_shrunk"] = (
        board["runs_saved_per_600_pa"]
        - board["shrinkage_factor"]
        * (board["runs_saved_per_600_pa"] - pooled_mean)
    )

    # Shrinkage moves a hitter toward the board's mean and never past it.
    moved_past = (
        (board["runs_saved_shrunk"] - pooled_mean)
        * (board["runs_saved_per_600_pa"] - pooled_mean)
        < -1e-9
    )

    if moved_past.any():
        raise RuntimeError(f"{season} {matchup}: shrinkage overshot the mean.")

    board["xchase_plus"] = (
        100
        + 100
        * board["runs_saved_shrunk"]
        / board["league_chase_cost_per_600_pa"]
    )

    board["xchase_plus_posterior_sd"] = (
        board["xchase_plus_se"] * np.sqrt(1 - board["shrinkage_factor"])
    )

    board["rank"] = (
        board["runs_saved_shrunk"].rank(ascending=False, method="min")
        .astype(int)
    )

    boards.append(board)

    scale = float(board["league_chase_cost_per_600_pa"].iloc[0])
    median_se = float(board["xchase_plus_se"].median())
    true_sd = 100 * np.sqrt(tau_squared) / scale

    board_rows.append({
        "game_year": int(season),
        "matchup": matchup,
        "qualified": len(board),
        "true_sd_xchase_plus": true_sd,
        "median_xchase_plus_se": median_se,
        # Share of the spread on this board that is real for a typical
        # qualified hitter: tau^2 / (tau^2 + SE^2)
        "typical_reliability": (
            true_sd ** 2 / (true_sd ** 2 + median_se ** 2)
            if true_sd > 0 else 0.0
        ),
    })

qualified = pd.concat(boards, ignore_index=True)

league = league.merge(
    pd.DataFrame(board_rows),
    on=["game_year", "matchup"],
    how="left"
)


# --------------------------------------------------
# NAMES, BATTING SIDE, AND THE MAIN xCHASE+ FOR CONTEXT
# --------------------------------------------------

def attach_names(table, id_column="batter"):
    """
    Add a 'player' column from the Chadwick player register, which keeps
    names as written (McCann, LeMahieu, Acuña), so nothing is re-cased.
    The register is downloaded once and cached in data/raw/, so reruns get
    the same names without a network call. If it cannot be loaded, print
    why and return the table unchanged.
    """

    try:

        if PLAYER_REGISTER_FILE.exists():

            register = pd.read_parquet(PLAYER_REGISTER_FILE)

        else:

            from pybaseball import chadwick_register

            register = chadwick_register()[
                ["key_mlbam", "name_first", "name_last"]
            ]

            PLAYER_REGISTER_FILE.parent.mkdir(parents=True, exist_ok=True)
            register.to_parquet(PLAYER_REGISTER_FILE, index=False)

        # One name per id. A duplicated id in the register would otherwise
        # duplicate that hitter's rows in the merge.
        lookup = (
            register
            .dropna(subset=["key_mlbam"])
            .drop_duplicates(subset="key_mlbam")
        )

        lookup = pd.DataFrame({
            id_column: lookup["key_mlbam"].astype(int),
            "player": (
                lookup["name_first"].str.strip()
                + " "
                + lookup["name_last"].str.strip()
            ),
        })

        named = table.merge(
            lookup,
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


qualified = attach_names(qualified)

if "player" in qualified.columns:
    qualified["player"] = qualified["player"].fillna(
        qualified["batter"].astype(str)
    )
else:
    qualified["player"] = qualified["batter"].astype(str)

# S for a hitter who batted from both sides that season
sides = plate_appearances.groupby(["batter", "game_year"])["stand"].agg(
    lambda stand: "S" if stand.nunique() > 1 else stand.iloc[0]
)

qualified = qualified.join(
    sides.rename("bats"),
    on=["batter", "game_year"]
)

# The hitter's main xChase+, when he qualified on the main leaderboard
qualified = qualified.merge(
    main[["batter", "game_year", "xchase_plus"]].rename(
        columns={"xchase_plus": "overall_xchase_plus"}
    ),
    on=["batter", "game_year"],
    how="left"
)


# --------------------------------------------------
# YEAR TO YEAR, BOARD BY BOARD
#
# Hitters qualified on the same board in consecutive seasons, unshrunk,
# the same way 06_build_chase_reliability.py tests the main leaderboard.
# --------------------------------------------------

seasons = sorted(int(season) for season in qualified["game_year"].unique())

reliability_rows = []

for matchup in MATCHUPS:

    board = qualified[qualified["matchup"] == matchup]

    for first_season, second_season in zip(seasons[:-1], seasons[1:]):

        paired = (
            board[board["game_year"] == first_season]
            .merge(
                board[board["game_year"] == second_season],
                on="batter",
                suffixes=("_first", "_second")
            )
        )

        if len(paired) < 20:
            continue

        reliability_rows.append({
            "matchup": matchup,
            "first_season": first_season,
            "second_season": second_season,
            "paired_hitters": len(paired),
            "xchase_plus_r": paired["xchase_plus_raw_first"].corr(
                paired["xchase_plus_raw_second"]
            ),
        })

reliability = pd.DataFrame(reliability_rows)

reliability_summary = (
    reliability
    .groupby("matchup")
    .agg(
        season_pairs=("xchase_plus_r", "size"),
        median_paired_hitters=("paired_hitters", "median"),
        lowest_r=("xchase_plus_r", "min"),
        average_r=("xchase_plus_r", "mean"),
        highest_r=("xchase_plus_r", "max"),
    )
    .reindex(MATCHUPS)
)


# --------------------------------------------------
# SAVE
# --------------------------------------------------

output_columns = [
    "matchup",
    "rank",
    "player",
    "batter",
    "bats",
    "game_year",
    "plate_appearances",
    "opportunities",
    "chases",
    "chase_rate",
    "xchase_plus",
    "xchase_plus_posterior_sd",
    "xchase_plus_raw",
    "xchase_plus_se",
    "overall_xchase_plus",
    "runs_saved_per_600_pa",
    "runs_saved_shrunk",
    "standard_error_per_600_pa",
    "shrinkage_factor",
    "league_chase_cost_per_600_pa",
]

qualified["matchup_order"] = qualified["matchup"].map(
    {matchup: order for order, matchup in enumerate(MATCHUPS)}
)

by_season = (
    qualified
    .sort_values(["game_year", "matchup_order", "rank"])
    [output_columns]
)

by_season.to_csv(OUTPUT_BY_SEASON, index=False)

written_files = [OUTPUT_BY_SEASON]

for season in seasons:

    season_file = OUTPUT_DIR / SEASON_FILE_NAME.format(season=season)

    by_season[by_season["game_year"] == season].to_csv(season_file, index=False)

    written_files.append(season_file)

league_columns = [
    "game_year",
    "matchup",
    "plate_appearances",
    "opportunities",
    "chases",
    "chase_rate",
    "cost_per_chase",
    "matchup_xchase_plus",
    "share_of_pa_vs_this_hand",
    "minimum_opportunities",
    "minimum_plate_appearances",
    "qualified",
    "true_sd_xchase_plus",
    "median_xchase_plus_se",
    "typical_reliability",
    "league_chase_cost_per_600_pa",
]

(
    league
    .assign(
        matchup_order=league["matchup"].map(
            {matchup: order for order, matchup in enumerate(MATCHUPS)}
        ),
        stat_version=f"xChase+ {SETTINGS['XCHASE_PLUS_VERSION']}",
        run_fingerprint=league_scale["run_fingerprint"].iloc[0],
    )
    .sort_values(["game_year", "matchup_order"])
    [league_columns + ["stat_version", "run_fingerprint"]]
    .to_csv(OUTPUT_LEAGUE, index=False)
)

written_files.append(OUTPUT_LEAGUE)

reliability.to_csv(OUTPUT_RELIABILITY, index=False)

written_files.append(OUTPUT_RELIABILITY)


# --------------------------------------------------
# PRINT
# --------------------------------------------------

print()
print("=" * 78)
print("WHO QUALIFIES, AND HOW MUCH OF EACH BOARD IS REAL")
print("=" * 78)
print()
print(
    league
    .set_index(["game_year", "matchup"])
    [["minimum_plate_appearances", "minimum_opportunities", "qualified",
      "true_sd_xchase_plus", "median_xchase_plus_se", "typical_reliability"]]
    .round(2)
    .to_string()
)
print()
print(
    "true_sd is the real spread between hitters on the board, with noise "
    "taken out; median SE is the noise for a typical qualified hitter. "
    "typical_reliability is the share of a typical hitter's raw number "
    "that is real."
)

print()
print("=" * 78)
print("YEAR TO YEAR (hitters qualified on the same board both seasons, unshrunk)")
print("=" * 78)
print()
print(reliability_summary.round(2).to_string())

board_view_columns = [
    "rank", "player", "bats", "plate_appearances", "chase_rate",
    "xchase_plus", "xchase_plus_posterior_sd", "overall_xchase_plus",
]

for season in seasons:

    for matchup in MATCHUPS:

        board = by_season[
            (by_season["game_year"] == season)
            & (by_season["matchup"] == matchup)
        ]

        print()
        print("=" * 78)
        print(f"{season} {matchup} ({len(board)} qualified)")
        print("=" * 78)

        view = pd.concat([board.head(LIST_SIZE), board.tail(LIST_SIZE)])[
            board_view_columns
        ]

        print(view.round(1).to_string(index=False))


def markdown_board(board):
    """Top and bottom LIST_SIZE of one board as a README markdown table."""

    lines = [
        "| Rank | Player | Bats | PA | Chase% | xChase+ ± 1 SD | Overall xChase+ |",
        "|---:|---|:---:|---:|---:|---|---:|",
    ]

    def row(hitter):
        overall = (
            f"{hitter['overall_xchase_plus']:.0f}"
            if pd.notna(hitter["overall_xchase_plus"]) else "-"
        )
        return (
            f"| {hitter['rank']} | {hitter['player']} | {hitter['bats']} | "
            f"{int(hitter['plate_appearances'])} | "
            f"{hitter['chase_rate']:.1f}% | "
            f"**{hitter['xchase_plus']:.0f}** ± "
            f"{hitter['xchase_plus_posterior_sd']:.0f} | {overall} |"
        )

    lines += [row(hitter) for _, hitter in board.head(LIST_SIZE).iterrows()]
    lines.append("| | ... | | | | | |")
    lines += [row(hitter) for _, hitter in board.tail(LIST_SIZE).iterrows()]

    return "\n".join(lines)


latest_season = seasons[-1]

print()
print(f"Markdown tables for README.md ({latest_season}):")

for matchup in MATCHUPS:

    board = by_season[
        (by_season["game_year"] == latest_season)
        & (by_season["matchup"] == matchup)
    ]

    print()
    print(f"**{matchup}** ({len(board)} qualified hitters)")
    print()
    print(markdown_board(board))

print()
print(f"Done. Saved under {PROJECT_DIR}:")

for path in written_files:
    print(f"  {path.relative_to(PROJECT_DIR)}")
