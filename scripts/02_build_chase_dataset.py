"""
Step 2 of the pipeline: build the cleaned pitch-level dataset.

Reads the raw Statcast month files from data/raw/, keeps regular-season
pitches for the seasons in SEASONS_TO_KEEP, and adds the flags and features
the later scripts use (analyzable pitch, swing, in/out of zone, chase,
count, game state, and batter/pitcher-relative geometry).

Every pitch is kept and flagged rather than deleted, so pitch sequences
stay intact for anything downstream.

Output: data/cleaned/baseline_chase_pitches.parquet
"""

from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# FILE LOCATIONS
# --------------------------------------------------

# Paths are anchored to the project folder (the parent of scripts/), not
# to the directory the script is run from.
PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

RAW_DIR = PROJECT_DIR / "data" / "raw"
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
CLEAN_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = CLEAN_DIR / "baseline_chase_pitches.parquet"


# --------------------------------------------------
# SEASONS AND COLUMNS
# --------------------------------------------------

# Keep in sync with SEASONS in 01_download_baseline.py. This is set by
# hand on purpose: data/raw/ can hold stray files (an old manual download,
# a test pull) that should not become in-scope just by being on disk.
SEASONS_TO_KEEP = [2021, 2022, 2023, 2024, 2025, 2026]

# The raw files have 110+ columns; only these are loaded.
wanted_columns = [
    # identifiers and ordering
    "game_pk",
    "game_date",
    "game_year",
    "game_type",
    "at_bat_number",
    "pitch_number",

    # who is involved
    "batter",
    "pitcher",
    "player_name",
    "stand",
    "p_throws",

    # what the pitch was and what happened
    "pitch_type",
    "pitch_name",
    "description",
    "events",
    "zone",
    "balls",
    "strikes",

    # pitch measurements
    "plate_x",
    "plate_z",
    "sz_top",
    "sz_bot",
    "release_speed",
    "release_pos_x",
    "release_pos_z",
    "release_extension",
    "pfx_x",
    "pfx_z",

    # game state
    "inning",
    "inning_topbot",
    "outs_when_up",
    "bat_score",
    "post_bat_score",
    "fld_score",
    "on_1b",
    "on_2b",
    "on_3b",

    # run and win expectancy changes (used by 03_build_run_value_tables.py)
    "delta_home_win_exp",
    "delta_run_exp",

    # Savant's expected wOBA from exit velocity and launch angle, only
    # filled on balls in play. Used by 04_build_chase_leaderboard.py
    # --expected-contact (xChase+).
    "estimated_woba_using_speedangle",

    # wOBA value and denominator on the last pitch of each plate
    # appearance. Used by 09_build_xchase_comparison.py for each hitter's
    # season wOBA and xwOBA.
    "woba_value",
    "woba_denom",
]


# --------------------------------------------------
# LOAD ALL RAW FILES
# --------------------------------------------------

files = sorted(RAW_DIR.glob("statcast_*.parquet"))

print(f"Found {len(files)} raw files.")

if len(files) == 0:
    raise FileNotFoundError("No Statcast parquet files found in data/raw.")

# Only request columns that exist, so an older pybaseball version with a
# missing column does not crash the load.
first_file_columns = pd.read_parquet(files[0]).columns.tolist()

available_columns = [
    col
    for col in wanted_columns
    if col in first_file_columns
]

missing_columns = [
    col
    for col in wanted_columns
    if col not in first_file_columns
]

if missing_columns:
    print()
    print("WARNING: these columns are not in the raw data:")
    print(missing_columns)

frames = []

for file in files:

    print(f"Loading {file.name}")

    frames.append(
        pd.read_parquet(file, columns=available_columns)
    )

df = pd.concat(frames, ignore_index=True)

del frames

print()
print(f"Total raw pitches loaded: {len(df):,}")


# --------------------------------------------------
# REMOVE DUPLICATE PITCHES
#
# pybaseball occasionally returns overlapping rows. A pitch is uniquely
# identified by game + at-bat + pitch number.
# --------------------------------------------------

rows_before_dedupe = len(df)

df = df.drop_duplicates(
    subset=[
        "game_pk",
        "at_bat_number",
        "pitch_number"
    ]
).copy()

print(
    f"Removed {rows_before_dedupe - len(df):,} duplicate pitches."
)


# --------------------------------------------------
# KEEP REGULAR SEASON ONLY, FOR THE SEASONS THIS PROJECT COVERS
# --------------------------------------------------

df = df[
    (df["game_year"].isin(SEASONS_TO_KEEP))
    & (df["game_type"] == "R")
].copy()

print(
    f"Regular-season pitches, {min(SEASONS_TO_KEEP)}-"
    f"{max(SEASONS_TO_KEEP)}: {len(df):,}"
)


# --------------------------------------------------
# FLAG PITCHES INSTEAD OF DELETING THEM
# --------------------------------------------------

# Not a normal swing/take decision. bunt_foul_tip must be listed, or a
# foul-tipped bunt fails the swing test and counts as a take.
excluded_descriptions = {
    "intent_ball",
    "pitchout",
    "hit_by_pitch",
    "foul_bunt",
    "missed_bunt",
    "bunt_foul_tip",
}

df["is_competitive_pitch"] = (
    ~df["description"].isin(excluded_descriptions)
).astype(int)

df["has_tracking"] = (
    df["pitch_type"].notna()
    & df["zone"].notna()
    & df["plate_x"].notna()
    & df["plate_z"].notna()
).astype(int)

# A pitch that can be used in the analysis
df["is_analyzable"] = (
    df["is_competitive_pitch"]
    * df["has_tracking"]
)

print()
print(f"Competitive pitches: {df['is_competitive_pitch'].sum():,}")
print(f"Pitches with tracking: {df['has_tracking'].sum():,}")
print(f"Analyzable pitches: {df['is_analyzable'].sum():,}")

# Pitch-type codes that are not real competitive pitches (including
# pitch-timer automatic balls/strikes). The description filter should
# already remove these; this is a safety check.
non_pitch_codes = ["IN", "PO", "AB", "AS", "UN"]

leftover = df[
    (df["is_analyzable"] == 1)
    & (df["pitch_type"].isin(non_pitch_codes))
]

if len(leftover) > 0:

    print()
    print(
        f"Found {len(leftover):,} non-pitch codes that survived "
        f"the description filter. Marking them unusable."
    )
    print(leftover["pitch_type"].value_counts())

    df.loc[
        df["pitch_type"].isin(non_pitch_codes),
        "is_analyzable"
    ] = 0


# --------------------------------------------------
# SWING, ZONE AND CHASE
# --------------------------------------------------

swing_descriptions = {
    "swinging_strike",
    "swinging_strike_blocked",
    "foul",
    "foul_tip",
    "hit_into_play",
    "swinging_pitchout",
    "foul_pitchout",
}

df["is_swing"] = df["description"].isin(swing_descriptions).astype(int)

# Baseball Savant zones: 1-9 are in the strike zone, 11-14 are outside it.
df["is_in_zone"] = df["zone"].isin([1, 2, 3, 4, 5, 6, 7, 8, 9]).astype(int)
df["is_outside_zone"] = df["zone"].isin([11, 12, 13, 14]).astype(int)

df["is_chase"] = (
    (df["is_outside_zone"] == 1)
    & (df["is_swing"] == 1)
).astype(int)


# --------------------------------------------------
# COUNT
#
# Named count_state rather than count, because df.count is a DataFrame
# method.
# --------------------------------------------------

df["count_state"] = (
    df["balls"].astype(str)
    + "-"
    + df["strikes"].astype(str)
)


# --------------------------------------------------
# GAME STATE
# --------------------------------------------------

df["score_diff"] = df["bat_score"] - df["fld_score"]

df["runner_on_1b"] = df["on_1b"].notna().astype(int)
df["runner_on_2b"] = df["on_2b"].notna().astype(int)
df["runner_on_3b"] = df["on_3b"].notna().astype(int)

df["num_runners"] = (
    df["runner_on_1b"]
    + df["runner_on_2b"]
    + df["runner_on_3b"]
)


# --------------------------------------------------
# GEOMETRY FEATURES
#
# Statcast's horizontal measurements are signed relative to the field.
# "Away" has opposite signs for left- and right-handed batters, and a
# lefty pitcher's release point and arm-side movement are mirrored too.
# These are mirrored once here so the same sign means the same thing for
# everybody.
# --------------------------------------------------

# Some parquet/pybaseball combinations leave these as object dtype, which
# breaks numpy operations such as sqrt.
geometry_numeric_columns = [
    "plate_x",
    "plate_z",
    "sz_top",
    "sz_bot",
    "release_speed",
    "release_pos_x",
    "release_pos_z",
    "release_extension",
    "pfx_x",
    "pfx_z",
]

for col in geometry_numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).astype("float64")

batter_sign = df["stand"].map({"R": 1.0, "L": -1.0})
pitcher_sign = df["p_throws"].map({"R": 1.0, "L": -1.0})

df["plate_x_batter"] = df["plate_x"] * batter_sign
df["pfx_x_arm"] = df["pfx_x"] * pitcher_sign
df["release_pos_x_arm"] = df["release_pos_x"] * pitcher_sign

# Vertical location as a fraction of this hitter's own zone height:
# 0.0 = bottom of the zone, 1.0 = top. A non-positive zone height gives NaN.
zone_height = df["sz_top"] - df["sz_bot"]

zone_height = zone_height.where(zone_height > 0)

df["plate_z_normalized"] = (
    (df["plate_z"] - df["sz_bot"])
    / zone_height
)

df["plate_z_normalized"] = (
    df["plate_z_normalized"]
    .replace([np.inf, -np.inf], np.nan)
)

# How far outside the zone the pitch was, in feet (0 inside the zone).
# Horizontally the zone edge is 0.83 ft from the middle of the plate: half
# the plate (8.5 in) plus a ball radius (1.45 in). Vertically it is the
# hitter's own sz_top / sz_bot, with no ball radius added.
half_plate_plus_ball = 0.83

horizontal_miss = (
    df["plate_x"].abs() - half_plate_plus_ball
).clip(lower=0)

above_the_top = (df["plate_z"] - df["sz_top"]).clip(lower=0)
below_the_bottom = (df["sz_bot"] - df["plate_z"]).clip(lower=0)

vertical_miss = above_the_top + below_the_bottom

df["distance_outside_zone"] = np.sqrt(
    horizontal_miss ** 2
    + vertical_miss ** 2
)


# --------------------------------------------------
# CHECK THE MIRRORING DIRECTION
#
# Hit-by-pitches are inside by definition, so mean plate_x_batter for HBP
# should be negative for both batter sides. If one is positive, the sign
# map above is flipped.
# --------------------------------------------------

hbp = df[df["description"] == "hit_by_pitch"]

print()
print("=" * 60)
print("MIRRORING CHECK (hit-by-pitches should be inside)")
print("=" * 60)

print(
    hbp
    .groupby("stand")
    .agg(
        hbp_count=("plate_x", "size"),
        mean_plate_x=("plate_x", "mean"),
        mean_plate_x_batter=("plate_x_batter", "mean")
    )
)

print()
print("Both mean_plate_x_batter values should be negative.")


# --------------------------------------------------
# VALIDATION AGAINST PUBLISHED LEAGUE NUMBERS
#
# Baseball Savant's 2025 league line is Zone% 48.8 and Chase% 28.4. Being
# more than about 1.5 points off either suggests a filter is wrong.
# --------------------------------------------------

usable = df[df["is_analyzable"] == 1]

outside = usable[usable["is_outside_zone"] == 1]

zone_rate = usable["is_in_zone"].mean()
overall_chase_rate = outside["is_chase"].mean()

print()
print("=" * 60)
print("CHASE RATE VALIDATION")
print("=" * 60)

print(f"Analyzable pitches: {len(usable):,}")
print(f"Out-of-zone pitches: {len(outside):,}")
print(f"Chases: {outside['is_chase'].sum():,}")

print()
print(f"Zone rate:   {zone_rate:.3%}   (Savant league: 48.8%)")
print(f"Chase rate:  {overall_chase_rate:.3%}   (Savant league: 28.4%)")

if abs(zone_rate - 0.488) > 0.015:
    print("WARNING: zone rate is off the published league figure.")

if abs(overall_chase_rate - 0.284) > 0.015:
    print("WARNING: chase rate is off the published league figure.")

print()
print("CHASE RATE BY YEAR")

year_summary = (
    outside
    .groupby("game_year")
    .agg(
        opportunities=("is_chase", "size"),
        chases=("is_chase", "sum"),
        chase_rate=("is_chase", "mean")
    )
)

year_summary["chase_rate"] *= 100

print(year_summary)

print()
print("CHASE RATE BY PITCH TYPE")

pitch_summary = (
    outside
    .groupby(["pitch_type", "pitch_name"])
    .agg(
        opportunities=("is_chase", "size"),
        chases=("is_chase", "sum"),
        chase_rate=("is_chase", "mean")
    )
    .sort_values("opportunities", ascending=False)
)

pitch_summary["chase_rate"] *= 100

print(pitch_summary.head(15))


# --------------------------------------------------
# CHECK delta_home_win_exp FOR 03_build_run_value_tables.py
#
# This column should only be nonzero on the pitch that ends a plate
# appearance; every other pitch should have exactly 0 (not NaN).
# --------------------------------------------------

if "delta_home_win_exp" in df.columns and "events" in df.columns:

    non_terminal = df[df["events"].isna()]

    non_terminal_nonzero = (
        non_terminal["delta_home_win_exp"].abs() > 1e-9
    ).sum()

    print()
    print("=" * 60)
    print("WIN EXPECTANCY COLUMN CHECK")
    print("=" * 60)

    print(f"Pitches that end a plate appearance: {df['events'].notna().sum():,}")
    print(f"Pitches that do not: {len(non_terminal):,}")
    print(
        f"Non-terminal pitches with a nonzero win-exp change: "
        f"{non_terminal_nonzero:,}"
    )
    print()


# --------------------------------------------------
# SAVE
# --------------------------------------------------

df.to_parquet(OUTPUT_FILE, index=False)

print()
print("Saved cleaned chase dataset to:")
print(OUTPUT_FILE)
print(f"Rows saved: {len(df):,} (all pitches, flagged not deleted)")
