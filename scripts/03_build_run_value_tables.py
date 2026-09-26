"""
Step 3 of the pipeline: build the run value tables.

The chase leaderboard needs the value of the branch a hitter did not take
(what taking a pitch he swung at would have been worth), so that value has
to come from a model. This script builds it in three tables, each one
built on the one before:

  1. Base-out run expectancy: average runs scored from each of the 24
     base-out states to the end of the half inning.
  2. Event run values (linear weights, RE24 method): what each
     plate-appearance outcome is worth, using table 1.
  3. Count run values: the average run value of every plate appearance
     that passed through each of the twelve counts, using table 2. This is
     the table the leaderboard uses.

Each table is printed next to published reference values so a broken step
shows up immediately, before anything is built on it.

Inputs:  data/cleaned/baseline_chase_pitches.parquet
Outputs: results/run_expectancy_base_out.csv
         results/run_value_by_event.csv
         results/run_value_by_count.csv
         data/cleaned/plate_appearance_run_values.parquet
"""

from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

# A half inning cut short because the game ended is not a fair sample of
# what a base-out state is worth. Dropping every game's last half inning
# would be too blunt (a home team leading after the top of the 9th never
# bats, so that top half is an ordinary three-out inning). Instead, each
# game's final half inning is classified:
#
#   Top half, 9th or later   -> complete (ended on three outs)
#   Bottom half, home loses  -> complete (ended on three outs)
#   Bottom half, home wins   -> INCOMPLETE (walk-off)
#   Top half, before the 9th -> INCOMPLETE (rain or other stoppage)
#
# A final half inning can never end tied (the game would continue), so
# "did not finish ahead" is safely written as <=.
EXCLUDE_INCOMPLETE_HALF_INNINGS = True

# Earliest inning in which a top half can end a game as a real three-out
# inning. Anything earlier is a called game.
EARLIEST_REGULATION_FINAL_INNING = 9

# Base-out and count cells with fewer plate appearances than this are
# listed, because their averages are noisy.
MINIMUM_CELL_SIZE = 500

# Base states in order of value rather than alphabetically, so the printed
# table can be checked for rising with runners at a glance.
BASE_STATE_ORDER = [
    "___",
    "1__",
    "_2_",
    "__3",
    "12_",
    "1_3",
    "_23",
    "123",
]


# --------------------------------------------------
# FILE LOCATIONS
# --------------------------------------------------

# Paths are anchored to the project folder (the parent of scripts/), not
# to the directory the script is run from.
PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
RESULTS_DIR = PROJECT_DIR / "results"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_FILE = CLEAN_DIR / "baseline_chase_pitches.parquet"

OUTPUT_BASE_OUT = RESULTS_DIR / "run_expectancy_base_out.csv"
OUTPUT_EVENT_VALUES = RESULTS_DIR / "run_value_by_event.csv"
OUTPUT_COUNT_VALUES = RESULTS_DIR / "run_value_by_count.csv"
OUTPUT_PA_VALUES = CLEAN_DIR / "plate_appearance_run_values.parquet"


# --------------------------------------------------
# LOAD
# --------------------------------------------------

print("Loading cleaned chase dataset...")

# Only the columns this script uses (no pitch geometry).
wanted_pitch_columns = [
    "game_pk",
    "at_bat_number",
    "pitch_number",
    "batter",
    "pitcher",
    "game_year",
    "description",
    "events",
    "balls",
    "strikes",
    "count_state",
    "is_analyzable",
    "inning",
    "inning_topbot",
    "outs_when_up",
    "bat_score",
    "post_bat_score",
    "fld_score",
    "runner_on_1b",
    "runner_on_2b",
    "runner_on_3b",
    "delta_run_exp",
]

df = pd.read_parquet(INPUT_FILE, columns=wanted_pitch_columns)

print(f"Loaded {len(df):,} pitches.")

required_columns = [
    "post_bat_score",
    "bat_score",
    "inning",
    "inning_topbot",
    "outs_when_up",
    "events",
    "game_pk",
    "at_bat_number",
    "pitch_number",
]

missing = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing:

    raise RuntimeError(
        "Missing columns needed for run expectancy: "
        f"{missing}. Add them to wanted_columns in script 03 and "
        "rerun it. They are already in the raw parquet files."
    )


# --------------------------------------------------
# IS delta_run_exp POPULATED ON EVERY PITCH
#
# Diagnostic only. If Statcast's delta_run_exp is populated per pitch (not
# only on plate-appearance-ending pitches), it can be used further down as
# an independent check on the count table.
# --------------------------------------------------

print()
print("=" * 78)
print("IS delta_run_exp POPULATED ON EVERY PITCH")
print("=" * 78)

if "delta_run_exp" in df.columns:

    non_terminal = df[df["events"].isna()]

    non_terminal_nonzero = (
        non_terminal["delta_run_exp"].abs() > 1e-9
    ).sum()

    share = (
        non_terminal_nonzero
        / max(len(non_terminal), 1)
    )

    print()
    print(f"Non-plate-appearance-ending pitches: {len(non_terminal):,}")
    print(f"  of those, with a nonzero value:    {non_terminal_nonzero:,}")
    print(f"  share:                             {share:.2%}")

    print()

    if share > 0.5:
        print(
            "Populated per pitch. I can use it later as an "
            "independent check on my own count table, which is a "
            "much stronger validation than the published numbers."
        )
    else:
        print(
            "Per plate appearance only, same as delta_home_win_exp. "
            "That is exactly why this script builds the tables from "
            "scratch instead of leaning on the column."
        )

else:
    print()
    print("Column not present. Building everything from scratch.")


# --------------------------------------------------
# HALF INNINGS
# --------------------------------------------------

df = df.sort_values(
    by=[
        "game_pk",
        "at_bat_number",
        "pitch_number"
    ]
).reset_index(drop=True)

df["half_inning_id"] = (
    df["game_pk"].astype(str)
    + "_"
    + df["inning"].astype(str)
    + "_"
    + df["inning_topbot"].astype(str)
)

if EXCLUDE_INCOMPLETE_HALF_INNINGS:

    final_half_inning_per_game = set(
        df
        .groupby("game_pk")["half_inning_id"]
        .last()
    )

    final_halves = df[
        df["half_inning_id"].isin(final_half_inning_per_game)
    ]

    # The fielding team cannot score while fielding, so the max of
    # fld_score over the half inning is their final total.
    ending_summary = (
        final_halves
        .groupby("half_inning_id")
        .agg(
            inning=("inning", "first"),
            half=("inning_topbot", "first"),
            batting_final_score=("post_bat_score", "max"),
            fielding_final_score=("fld_score", "max"),
        )
    )

    complete_top_half = (
        (ending_summary["half"] == "Top")
        & (ending_summary["inning"] >= EARLIEST_REGULATION_FINAL_INNING)
    )

    complete_bottom_half = (
        (ending_summary["half"] == "Bot")
        & (
            ending_summary["batting_final_score"]
            <= ending_summary["fielding_final_score"]
        )
    )

    incomplete = set(
        ending_summary.index[
            ~(complete_top_half | complete_bottom_half)
        ]
    )

    before = df["half_inning_id"].nunique()

    df = df[~df["half_inning_id"].isin(incomplete)].copy()

    after = df["half_inning_id"].nunique()

    recovered = len(final_half_inning_per_game) - len(incomplete)

    print()
    print("=" * 78)
    print("WHICH HALF INNINGS ARE COMPLETE")
    print("=" * 78)

    print()
    print(f"Games:                          {len(final_half_inning_per_game):,}")
    print(f"  final half innings kept:      {recovered:,}")
    print(f"  final half innings dropped:   {len(incomplete):,}")

    print()
    print("Breakdown of the ones I kept:")
    print(
        f"  complete top halves:          "
        f"{int(complete_top_half.sum()):,}"
    )
    print(
        f"  complete bottom halves:       "
        f"{int(complete_bottom_half.sum()):,}"
    )

    print()
    print(f"Half innings dropped in total:  {before - after:,}")
    print(f"Half innings remaining:         {after:,}")

    print()
    print(
        "The dropped ones should be close to the number of walk-off "
        "wins in the data, which is ~10 percent of all "
        "games. If the dropped count is near one per game, the rule "
        "is not firing and something is wrong."
    )

    dropped_share = len(incomplete) / len(final_half_inning_per_game)

    if dropped_share > 0.6:
        print()
        print(
            "WARNING: dropping more than 60% of final half innings. "
            "Check that inning_topbot really contains 'Top' and "
            "'Bot' and not something else."
        )


# --------------------------------------------------
# ONE ROW PER PLATE APPEARANCE
#
# The base-out state comes from the first pitch (the state at the start of
# the plate appearance); the outcome comes from the last pitch.
# --------------------------------------------------

plate_appearances = (
    df
    .sort_values(["game_pk", "at_bat_number", "pitch_number"])
    .groupby(["game_pk", "at_bat_number"], as_index=False)
    .agg(
        half_inning_id=("half_inning_id", "first"),
        inning=("inning", "first"),
        batter=("batter", "first"),
        pitcher=("pitcher", "first"),
        game_year=("game_year", "first"),
        outs_when_up=("outs_when_up", "first"),
        runner_on_1b=("runner_on_1b", "first"),
        runner_on_2b=("runner_on_2b", "first"),
        runner_on_3b=("runner_on_3b", "first"),
        score_at_start=("bat_score", "first"),
        score_after=("post_bat_score", "last"),
        event=("events", "last"),
    )
)

print()
print(f"Plate appearances: {len(plate_appearances):,}")

# Every completed plate appearance ends in some event, so a missing one
# points to a data problem upstream.
missing_event = plate_appearances["event"].isna().sum()

if missing_event > 0:
    print(
        f"WARNING: {missing_event:,} plate appearances have no "
        f"event recorded. Check for truncated games upstream."
    )


# --------------------------------------------------
# BASE STATE AS A READABLE CODE
# --------------------------------------------------

def base_state_label(on_first, on_second, on_third):
    """'___' is bases empty, '1_3' is corners, '123' is loaded."""

    return (
        np.where(on_first == 1, "1", "_")
        + np.where(on_second == 1, "2", "_")
        + np.where(on_third == 1, "3", "_")
    )


plate_appearances["base_state"] = base_state_label(
    plate_appearances["runner_on_1b"],
    plate_appearances["runner_on_2b"],
    plate_appearances["runner_on_3b"]
)


# --------------------------------------------------
# RUNS SCORED FROM HERE TO THE END OF THE HALF INNING
#
# The batting team's final score for the half inning is the highest
# post_bat_score in it. post_bat_score (not bat_score) is used so a run
# scored on the inning's last play is still counted.
# --------------------------------------------------

half_inning_final_score = (
    plate_appearances
    .groupby("half_inning_id")["score_after"]
    .transform("max")
)

plate_appearances["runs_rest_of_inning"] = (
    half_inning_final_score
    - plate_appearances["score_at_start"]
)

negative_runs = (
    plate_appearances["runs_rest_of_inning"] < 0
).sum()

if negative_runs > 0:
    raise RuntimeError(
        f"{negative_runs:,} plate appearances have negative runs "
        "remaining. Scores are not lining up. Do not trust anything "
        "below until this is zero."
    )


# --------------------------------------------------
# TABLE 1: BASE-OUT RUN EXPECTANCY
# --------------------------------------------------

base_out = (
    plate_appearances
    .groupby(["base_state", "outs_when_up"])
    .agg(
        occurrences=("runs_rest_of_inning", "size"),
        run_expectancy=("runs_rest_of_inning", "mean")
    )
    .reset_index()
)

thin_cells = base_out[base_out["occurrences"] < MINIMUM_CELL_SIZE]

print()
print("=" * 78)
print("TABLE 1: BASE-OUT RUN EXPECTANCY")
print("=" * 78)

base_out_display = (
    base_out
    .pivot(
        index="base_state",
        columns="outs_when_up",
        values="run_expectancy"
    )
    .reindex(BASE_STATE_ORDER)
)

print()
print(base_out_display.round(3).to_string())

# Every row must fall as outs are added, and every column must rise as
# runners are added.
falls_with_outs = (
    base_out_display
    .diff(axis=1)
    .iloc[:, 1:] < 0
).all().all()

rises_with_runners = (
    base_out_display
    .diff(axis=0)
    .iloc[1:, :] > 0
).all().all()

print()
print(f"Falls as outs are added:    {falls_with_outs}")
print(f"Rises as runners are added: {rises_with_runners}")

if not (falls_with_outs and rises_with_runners):
    print()
    print(
        "WARNING: one of those is False. The half-inning logic is "
        "wrong and nothing below this point is usable."
    )

print()
print("VALIDATION")
print(
    "  These are well known numbers. Approximate targets for a "
    "modern run environment:"
)
print("    bases empty, 0 out   around 0.48 to 0.52")
print("    bases empty, 2 out   around 0.09 to 0.11")
print("    bases loaded, 0 out  around 2.2 to 2.4")
print(
    "  Every row must fall as outs go up, and every column must "
    "rise as runners are added. If either of those breaks, the "
    "half-inning logic is wrong and nothing downstream is usable."
)

if len(thin_cells) > 0:
    print()
    print("Cells below the sample floor:")
    print(thin_cells.to_string(index=False))

base_out.to_csv(OUTPUT_BASE_OUT, index=False)


# --------------------------------------------------
# TABLE 2: WHAT EACH OUTCOME IS WORTH
#
# RE24 run value of a plate appearance:
#
#   value = RE(state after) - RE(state before) + runs that scored
#
# The state after is the state at the start of the next plate appearance
# in the same half inning. If there is none, the inning is over and its
# run expectancy is zero.
# --------------------------------------------------

run_expectancy_lookup = (
    base_out
    .set_index(["base_state", "outs_when_up"])["run_expectancy"]
)

plate_appearances["run_expectancy_before"] = (
    pd.MultiIndex.from_arrays(
        [
            plate_appearances["base_state"],
            plate_appearances["outs_when_up"]
        ]
    )
    .map(run_expectancy_lookup)
)

plate_appearances = plate_appearances.sort_values(
    ["half_inning_id", "at_bat_number"]
).reset_index(drop=True)

next_state = (
    plate_appearances
    .groupby("half_inning_id")["run_expectancy_before"]
    .shift(-1)
)

# No next plate appearance: the inning is over and worth zero more runs.
plate_appearances["run_expectancy_after"] = next_state.fillna(0.0)

plate_appearances["runs_on_play"] = (
    plate_appearances["score_after"]
    - plate_appearances["score_at_start"]
)

plate_appearances["run_value"] = (
    plate_appearances["run_expectancy_after"]
    - plate_appearances["run_expectancy_before"]
    + plate_appearances["runs_on_play"]
)

event_values = (
    plate_appearances
    .groupby("event")
    .agg(
        occurrences=("run_value", "size"),
        run_value=("run_value", "mean")
    )
    .reset_index()
    .sort_values("occurrences", ascending=False)
)

print()
print("=" * 78)
print("TABLE 2: RUN VALUE BY OUTCOME")
print("=" * 78)

print()
print(
    event_values
    .head(20)
    .round(4)
    .to_string(index=False)
)

print()
print("VALIDATION")
print("  Approximate published linear weights:")
print("    home run    around  1.35 to 1.42")
print("    triple      around  1.00 to 1.07")
print("    double      around  0.74 to 0.80")
print("    single      around  0.44 to 0.48")
print("    walk        around  0.29 to 0.32")
print("    strikeout   around -0.26 to -0.28")
print(
    "  If home runs come out near 1.4 and walks near 0.3, the "
    "RE24 arithmetic is right and I can trust table 3."
)

# Check three outcomes against those bands, with 0.02 runs of slack for
# ordinary run-environment drift.
validation_bands = {
    "home_run": (1.35, 1.42),
    "walk": (0.29, 0.32),
    "strikeout": (-0.28, -0.26),
}

for event_name, (low, high) in validation_bands.items():

    match = event_values[event_values["event"] == event_name]

    if len(match) != 1:
        continue

    value = float(match["run_value"].iloc[0])

    if not (low - 0.02 <= value <= high + 0.02):
        print(
            f"  WARNING: {event_name} run value ({value:+.4f}) is "
            f"well outside the {low:+.2f} to {high:+.2f} target "
            "band. Check the RE24 arithmetic before trusting "
            "table 3."
        )

# The average plate appearance should be worth about zero runs, which is
# what makes these values "above average" rather than raw.
mean_value = plate_appearances["run_value"].mean()

print()
print(f"Mean run value across all plate appearances: {mean_value:+.5f}")
print(
    "  This should sit very close to zero. A number far from zero "
    "means the state-after logic is misaligned somewhere."
)

event_values.to_csv(OUTPUT_EVENT_VALUES, index=False)


# --------------------------------------------------
# TABLE 3: RUN VALUE BY COUNT
#
# For each count, the average run value of every plate appearance that
# passed through it.
#
# Each plate appearance counts once per count it passed through. Without
# the drop_duplicates, a plate appearance that fouls off four pitches at
# 1-2 would count five times toward 1-2, and because long plate
# appearances end differently from short ones, that would bias the table.
# --------------------------------------------------

pitch_counts = df[
    ["game_pk", "at_bat_number", "count_state"]
].drop_duplicates()

pitch_counts = pitch_counts.merge(
    plate_appearances[
        ["game_pk", "at_bat_number", "run_value"]
    ],
    on=["game_pk", "at_bat_number"],
    how="inner"
)

count_values = (
    pitch_counts
    .groupby("count_state")
    .agg(
        occurrences=("run_value", "size"),
        run_value=("run_value", "mean")
    )
    .reset_index()
)

count_values["balls"] = (
    count_values["count_state"].str[0].astype(int)
)

count_values["strikes"] = (
    count_values["count_state"].str[-1].astype(int)
)

count_values = count_values.sort_values(["balls", "strikes"])

print()
print("=" * 78)
print("TABLE 3: RUN VALUE BY COUNT")
print("=" * 78)

print()
print(
    count_values
    .pivot(
        index="balls",
        columns="strikes",
        values="run_value"
    )
    .round(4)
    .to_string()
)

print()
print("VALIDATION")
print("  Approximate published count values:")
print("    3-0   around  +0.20 to +0.25")
print("    0-0   around   0.00 by construction")
print("    0-2   around  -0.09 to -0.11")
print(
    "  Every row must rise left to right as balls accumulate, and "
    "every column must fall as strikes accumulate. 0-0 has to be "
    "essentially zero, because every plate appearance passes "
    "through it and the average plate appearance is worth nothing."
)

zero_zero = count_values[
    count_values["count_state"] == "0-0"
]["run_value"]

if len(zero_zero) == 1:

    print()
    print(f"  0-0 came out at {float(zero_zero.iloc[0]):+.5f}")

    if abs(float(zero_zero.iloc[0])) > 0.01:
        print(
            "  WARNING: that is too far from zero. Something is "
            "wrong with the plate-appearance join."
        )

count_values.to_csv(OUTPUT_COUNT_VALUES, index=False)


# --------------------------------------------------
# WHAT ONE PITCH IS WORTH, BY COUNT
#
# The value of a ball and the cost of a strike at each count. The "ball
# gains" column is what a hitter gives up when he chases. Printed for
# inspection only; nothing here is saved.
# --------------------------------------------------

count_lookup = (
    count_values
    .set_index(["balls", "strikes"])["run_value"]
    .to_dict()
)


def terminal_event_value(event_name):
    """Run value of a walk or strikeout from table 2, or NaN if missing."""

    event_row = event_values[event_values["event"] == event_name]

    if len(event_row) == 1:
        return float(event_row["run_value"].iloc[0])

    return np.nan


print()
print("=" * 78)
print("WHAT ONE PITCH IS WORTH, BY COUNT")
print("=" * 78)

print()
print("count   ball gains   strike costs")

for balls in range(4):

    for strikes in range(3):

        current = count_lookup.get((balls, strikes))

        if current is None:
            continue

        after_ball = count_lookup.get((balls + 1, strikes))
        after_strike = count_lookup.get((balls, strikes + 1))

        # A fourth ball is a walk and a third strike is a strikeout, so
        # those come from the event table instead of the count table.
        if after_ball is None:
            after_ball = terminal_event_value("walk")

        if after_strike is None:
            after_strike = terminal_event_value("strikeout")

        print(
            f"{balls}-{strikes}     "
            f"{after_ball - current:+.4f}      "
            f"{after_strike - current:+.4f}"
        )

print()
print(
    "The 'ball gains' column is what a hitter throws away every "
    "time he chases. Look at how much bigger it is at 3-1 than at "
    "0-2. That gap is the entire argument for ranking hitters by "
    "the cost of their chases instead of by how often they chase."
)


# --------------------------------------------------
# CROSS-CHECK AGAINST STATCAST'S delta_run_exp
#
# Statcast computes a per-pitch run value independently, with the
# base-out state included. This count table ignores base-out state, so
# the two will not agree exactly, but averaging Statcast's values within
# a count should land close to the value implied here.
# --------------------------------------------------

if "delta_run_exp" in df.columns:

    ball_descriptions = {
        "ball",
        "blocked_ball",
    }

    strike_descriptions = {
        "called_strike",
        "swinging_strike",
        "swinging_strike_blocked",
        "foul_tip",
    }

    check = df[
        (df["is_analyzable"] == 1)
        & df["events"].isna()
        & df["delta_run_exp"].notna()
    ].copy()

    check["pitch_result"] = np.where(
        check["description"].isin(ball_descriptions),
        "ball",
        np.where(
            check["description"].isin(strike_descriptions),
            "strike",
            "other"
        )
    )

    check = check[check["pitch_result"] != "other"]

    statcast_values = (
        check
        .groupby(["balls", "strikes", "pitch_result"])
        .agg(
            pitches=("delta_run_exp", "size"),
            statcast_value=("delta_run_exp", "mean")
        )
        .reset_index()
    )

    # The value this count table implies for the same transition
    implied_rows = []

    for _, row in statcast_values.iterrows():

        balls = int(row["balls"])
        strikes = int(row["strikes"])

        current = count_lookup.get((balls, strikes))

        if current is None:
            continue

        if row["pitch_result"] == "ball":
            after = count_lookup.get((balls + 1, strikes))
        else:
            after = count_lookup.get((balls, strikes + 1))

        # Walks and strikeouts leave the count table
        if after is None:
            continue

        implied_rows.append(
            {
                "balls": balls,
                "strikes": strikes,
                "pitch_result": row["pitch_result"],
                "pitches": int(row["pitches"]),
                "my_value": after - current,
                "statcast_value": float(row["statcast_value"]),
            }
        )

    comparison = pd.DataFrame(implied_rows)

    if len(comparison) > 0:

        comparison["difference"] = (
            comparison["my_value"]
            - comparison["statcast_value"]
        )

        comparison = comparison.sort_values(
            ["pitch_result", "balls", "strikes"]
        )

        print()
        print("=" * 78)
        print("CROSS-CHECK: MY COUNT TABLE VS STATCAST delta_run_exp")
        print("=" * 78)

        print()
        print(comparison.round(4).to_string(index=False))

        worst = comparison["difference"].abs().max()
        typical = comparison["difference"].abs().median()

        print()
        print(f"Median absolute difference: {typical:.4f} runs")
        print(f"Worst absolute difference:  {worst:.4f} runs")

        print()

        if worst < 0.03:
            print(
                "Close enough. Two independent calculations of the "
                "same quantity agree, so the count table is sound."
            )
        else:
            print(
                "One or more cells disagree by more than three "
                "hundredths of a run. Check whether the sign "
                "convention on delta_run_exp matches mine: a ball "
                "should help the batting team, so both columns "
                "should be positive for balls and negative for "
                "strikes. If the signs are flipped, that is a "
                "convention difference and not a real disagreement."
            )

        # A ball should help the hitter in both columns. If not, the two
        # sources use opposite sign conventions.
        balls_only = comparison[comparison["pitch_result"] == "ball"]

        print()
        print(
            f"Mean value of a ball  - mine: "
            f"{balls_only['my_value'].mean():+.4f}, "
            f"Statcast: {balls_only['statcast_value'].mean():+.4f}"
        )

    # --------------------------------------------------
    # PITCHES WITH A delta_run_exp OF EXACTLY ZERO
    #
    # About a tenth of non-terminal pitches have delta_run_exp exactly
    # zero. The expectation is that these are mostly two-strike fouls
    # (the count does not change), which would make them correct zeros
    # rather than missing data. This prints the breakdown to confirm.
    # --------------------------------------------------

    zero_valued = df[
        (df["is_analyzable"] == 1)
        & df["events"].isna()
        & (df["delta_run_exp"].abs() <= 1e-9)
    ]

    if len(zero_valued) > 0:

        print()
        print("=" * 78)
        print("PITCHES WITH A DELTA OF EXACTLY ZERO")
        print("=" * 78)

        print()
        print(f"Total: {len(zero_valued):,}")

        two_strike_fouls = (
            (zero_valued["description"] == "foul")
            & (zero_valued["strikes"] == 2)
        ).sum()

        print(
            f"  of those, fouls with two strikes: "
            f"{two_strike_fouls:,} "
            f"({two_strike_fouls / len(zero_valued):.1%})"
        )

        print()
        print("Most common descriptions among them:")
        print(
            zero_valued["description"]
            .value_counts()
            .head(5)
            .to_string()
        )

        print()
        print(
            "If these are almost all two-strike fouls, nothing is "
            "missing. The count did not move, so the value really "
            "is zero."
        )


# --------------------------------------------------
# SAVE
# --------------------------------------------------

plate_appearances.to_parquet(OUTPUT_PA_VALUES, index=False)

print()
print("Saved:")
print(OUTPUT_BASE_OUT)
print(OUTPUT_EVENT_VALUES)
print(OUTPUT_COUNT_VALUES)
print(OUTPUT_PA_VALUES)
