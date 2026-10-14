"""
Step 13 of the pipeline: which hitters' chase losses look coachable.

xChase+ says how many runs a hitter lost to chasing. This script asks a
different question: how much of that loss comes from decisions a hitter
could plausibly change, and where exactly it comes from.

SPLITTING EACH PITCH'S RUNS SAVED

Every out-of-zone pitch already carries runs_saved against the league
baseline for its season, count and distance bucket (script 04). That is
split here into two parts that add back to runs_saved:

    decision  = expected_cost - is_chase * league_cost_per_chase_in_cell
    execution = is_chase * (league_cost_per_chase_in_cell - chase_cost)

"decision" is what the pitch would have been worth if the hitter's chases
had turned out like the league's chases in that cell: positive for a
take, negative for a chase. It measures how often he swings. "execution"
is zero on a take and, on a chase, how much better or worse the swing
turned out than a league-average chase there: whiffing more, or hitting
the ball harder. Swing frequency is an approach problem; execution is a
contact problem. Both are reported per 600 PA.

HOW OBVIOUS THE SWING WAS

Each decision is classed by how clearly the take was right:

    A  fewer than two strikes, pitch clearly off or nowhere near
    B  two strikes, pitch clearly off or nowhere near
    C  three balls, pitch borderline or just off
    D  everything else (borderline / just off with 0-2 strikes)

A and B are the "far-off" classes: the pitch was at least 0.35 ft outside
the zone, where the called-strike model gives a take little risk. Those
are the runs a hitter gets back by simply not swinging; class D is close
calls nobody takes reliably. `far_off_recoverable` is the decision loss
in A and B with the sign flipped: the runs a hitter would have saved by
chasing far-off pitches at the league rate.

ARCHETYPES (qualified hitters only)

    decision-only   decision <= -8 and execution >= -1: his chases turn
                    out as well as the league's, he just takes too many
    decision-led    decision <= -8 and at least 60% of the loss
    execution-led   less than half the loss is decision
    mixed           everything else

The decision-only group is where a "take that pitch" adjustment is most
likely to pay: there is nothing wrong with the swing, only the choice.

OUTPUTS, in results/xchase/coaching/

    actionability_<season>.csv    one row per qualified hitter
    far_off_cells_<season>.csv    per hitter, decision runs by strikes x
                                  pitch group x side of the zone missed,
                                  far-off pitches only, with the league
                                  chase rate in the same cell; hitters
                                  losing at least 5 runs per 600 PA
    far_off_history.csv           far-off chase rate and decision runs
                                  per hitter-season, for persistence

Run after `04_build_chase_leaderboard.py --expected-contact`,
`09_build_xchase_comparison.py` and `12_build_coaching_profiles.py` (the
bottom-10 profiles; this script scores every qualified hitter).
"""

from pathlib import Path

import numpy as np
import pandas as pd

PLATE_APPEARANCES_PER_SEASON = 600
DECISION_FLOOR = -8.0          # runs per 600 PA
EXECUTION_NEUTRAL = -1.0       # runs per 600 PA
CELL_TABLE_FLOOR = -5.0        # runs per 600 PA; cell tables only for hitters losing this much
HALF_PLATE_PLUS_BALL = 0.83    # same geometry as scripts 03 and 04
FAR_BUCKETS = {"clearly off", "nowhere near"}

FASTBALLS = {"FF", "SI", "FC", "FA"}
BREAKING = {"SL", "ST", "CU", "KC", "SV", "CS"}
OFFSPEED = {"CH", "FS", "FO", "EP", "KN"}

PROJECT_DIR = Path(__file__).resolve().parent
if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
XCHASE_DIR = PROJECT_DIR / "results" / "xchase"
OUTPUT_DIR = XCHASE_DIR / "coaching"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

X_PITCHES = CLEAN_DIR / "xchase_costs_by_pitch.parquet"
PITCH_FILE = CLEAN_DIR / "baseline_chase_pitches.parquet"
LEADERBOARD = "xchase_leaderboard_{season}.csv"
SCALE_FILE = XCHASE_DIR / "chase_plus_league_scale.csv"

for needed in (X_PITCHES, PITCH_FILE, SCALE_FILE):
    if not needed.exists():
        raise SystemExit(f"{needed.relative_to(PROJECT_DIR)} is missing.")

# --------------------------------------------------
# LOAD AND JOIN
# --------------------------------------------------

costs = pd.read_parquet(X_PITCHES)
pitches = pd.read_parquet(
    PITCH_FILE,
    columns=[
        "game_pk", "at_bat_number", "pitch_number", "batter", "game_year",
        "p_throws", "pitch_type", "description", "plate_x_batter",
        "plate_z", "sz_top", "sz_bot", "estimated_woba_using_speedangle",
    ],
)
keys = ["game_pk", "at_bat_number", "pitch_number", "batter", "game_year"]
df = costs.merge(pitches, on=keys, how="left", validate="one_to_one")
if df["pitch_type"].isna().mean() > 0.01:
    raise SystemExit("More than 1% of priced pitches did not join to the pitch file.")

seasons = sorted(df["game_year"].unique())

leaderboards = []
for season in seasons:
    path = XCHASE_DIR / LEADERBOARD.format(season=season)
    if path.exists():
        lb = pd.read_csv(path)
        lb["game_year"] = season
        leaderboards.append(lb)
leaderboard = pd.concat(leaderboards, ignore_index=True)
qualified = leaderboard[["batter", "game_year", "player", "plate_appearances",
                         "xchase_plus", "xchase_plus_rank"]]

scale = pd.read_csv(SCALE_FILE).set_index("game_year")["league_chase_cost_per_600_pa"]

# --------------------------------------------------
# DECISION / EXECUTION SPLIT
# --------------------------------------------------

cell_keys = ["game_year", "balls", "strikes", "distance_bucket"]
league_cost_per_chase = (
    df[df["is_chase"] == 1]
    .groupby(cell_keys)["chase_cost"].mean()
    .rename("league_cost_per_chase")
)
df = df.join(league_cost_per_chase, on=cell_keys)
df["league_cost_per_chase"] = df["league_cost_per_chase"].fillna(0.0)

df["decision"] = df["expected_cost_per_pitch"] - df["is_chase"] * df["league_cost_per_chase"]
df["execution"] = df["is_chase"] * (df["league_cost_per_chase"] - df["chase_cost"])
if not np.allclose(df["decision"] + df["execution"], df["runs_saved"]):
    raise SystemExit("decision + execution does not reproduce runs_saved.")

# --------------------------------------------------
# LABELS
# --------------------------------------------------

df["pitch_group"] = np.select(
    [df["pitch_type"].isin(FASTBALLS), df["pitch_type"].isin(BREAKING), df["pitch_type"].isin(OFFSPEED)],
    ["fastball", "breaking", "offspeed"], "other",
)

# Side of the zone the pitch missed, from the batter's point of view.
# plate_x_batter is negative on the inside half (script 02).
miss_in = (-df["plate_x_batter"] - HALF_PLATE_PLUS_BALL).clip(lower=0)
miss_away = (df["plate_x_batter"] - HALF_PLATE_PLUS_BALL).clip(lower=0)
miss_up = (df["plate_z"] - df["sz_top"]).clip(lower=0)
miss_down = (df["sz_bot"] - df["plate_z"]).clip(lower=0)
vertical = np.where(miss_up > 0, "up", np.where(miss_down > 0, "down", ""))
horizontal = np.where(miss_in > 0, "in", np.where(miss_away > 0, "away", ""))
df["zone_miss"] = [(v + "-" + h).strip("-") or "edge" for v, h in zip(vertical, horizontal)]

df["far_off"] = df["distance_bucket"].isin(FAR_BUCKETS)
df["whiff"] = df["description"].isin({"swinging_strike", "swinging_strike_blocked", "foul_tip"}).astype(int)
df["in_play"] = (df["description"] == "hit_into_play").astype(int)
df["decision_class"] = np.select(
    [
        (df["strikes"] < 2) & df["far_off"],
        (df["strikes"] == 2) & df["far_off"],
        (df["balls"] == 3) & ~df["far_off"],
    ],
    ["A", "B", "C"], "D",
)

# Qualified hitter-seasons only, scaled to 600 PA
df = df.merge(qualified[["batter", "game_year", "plate_appearances"]], on=["batter", "game_year"], how="inner")
df["scale"] = PLATE_APPEARANCES_PER_SEASON / df["plate_appearances"]
for col in ("runs_saved", "decision", "execution"):
    df[col + "_600"] = df[col] * df["scale"]

# --------------------------------------------------
# PER HITTER-SEASON TABLE
# --------------------------------------------------

def per_hitter(group):
    chases = group[group["is_chase"] == 1]
    in_play = chases[chases["in_play"] == 1]
    far = group[group["far_off"]]
    by_class = group.groupby("decision_class")["decision_600"].sum()
    return pd.Series({
        "runs_saved_per_600": group["runs_saved_600"].sum(),
        "decision_per_600": group["decision_600"].sum(),
        "execution_per_600": group["execution_600"].sum(),
        "chase_rate": group["is_chase"].mean(),
        "whiff_rate_on_chases": chases["whiff"].mean(),
        "xwoba_on_chases_in_play": in_play["estimated_woba_using_speedangle"].mean(),
        "far_off_chase_rate_lt2k": far.loc[far["strikes"] < 2, "is_chase"].mean(),
        "far_off_chase_rate_2k": far.loc[far["strikes"] == 2, "is_chase"].mean(),
        "decision_A_early_far": by_class.get("A", 0.0),
        "decision_B_2k_far": by_class.get("B", 0.0),
        "decision_C_3ball_near": by_class.get("C", 0.0),
        "decision_D_near": by_class.get("D", 0.0),
    })

table = df.groupby(["batter", "game_year"]).apply(per_hitter).reset_index()
table = table.merge(qualified, on=["batter", "game_year"])

table["decision_share"] = np.where(
    table["runs_saved_per_600"] < 0,
    table["decision_per_600"] / table["runs_saved_per_600"], np.nan,
)
table["far_off_recoverable"] = -(
    table["decision_A_early_far"].clip(upper=0) + table["decision_B_2k_far"].clip(upper=0)
)
table["xchase_plus_if_far_off_fixed"] = (
    table["xchase_plus"] + 100 * table["far_off_recoverable"] / table["game_year"].map(scale)
)
table["archetype"] = np.select(
    [
        (table["decision_per_600"] <= DECISION_FLOOR) & (table["execution_per_600"] >= EXECUTION_NEUTRAL),
        (table["decision_per_600"] <= DECISION_FLOOR) & (table["decision_share"] >= 0.6),
        table["decision_share"] < 0.5,
    ],
    ["decision-only", "decision-led", "execution-led"], "mixed",
)

league_rows = []
for season, g in df.groupby("game_year"):
    chases = g[g["is_chase"] == 1]
    far = g[g["far_off"]]
    league_rows.append({
        "game_year": season,
        "chase_rate": g["is_chase"].mean(),
        "whiff_rate_on_chases": chases["whiff"].mean(),
        "xwoba_on_chases_in_play": chases.loc[chases["in_play"] == 1, "estimated_woba_using_speedangle"].mean(),
        "far_off_chase_rate_lt2k": far.loc[far["strikes"] < 2, "is_chase"].mean(),
        "far_off_chase_rate_2k": far.loc[far["strikes"] == 2, "is_chase"].mean(),
    })
league = pd.DataFrame(league_rows)

columns = [
    "game_year", "xchase_plus_rank", "player", "batter", "plate_appearances", "xchase_plus",
    "runs_saved_per_600", "decision_per_600", "execution_per_600", "decision_share", "archetype",
    "decision_A_early_far", "decision_B_2k_far", "decision_C_3ball_near", "decision_D_near",
    "far_off_recoverable", "xchase_plus_if_far_off_fixed",
    "chase_rate", "far_off_chase_rate_lt2k", "far_off_chase_rate_2k",
    "whiff_rate_on_chases", "xwoba_on_chases_in_play",
]
table = table[columns].sort_values(["game_year", "runs_saved_per_600"])

# --------------------------------------------------
# FAR-OFF CELLS
# --------------------------------------------------

cell = ["game_year", "strikes", "pitch_group", "zone_miss"]
far = df[df["far_off"]]
league_cells = far.groupby(cell)["is_chase"].mean().rename("league_chase_rate")
cells = (
    far.groupby(["batter"] + cell)
    .agg(
        pitches=("is_chase", "size"),
        chases=("is_chase", "sum"),
        chase_rate=("is_chase", "mean"),
        decision_per_600=("decision_600", "sum"),
        execution_per_600=("execution_600", "sum"),
        whiffs=("whiff", "sum"),
    )
    .join(league_cells, on=cell)
    .reset_index()
)
cells["excess_chases"] = (cells["chase_rate"] - cells["league_chase_rate"]) * cells["pitches"]
losing = table.loc[table["runs_saved_per_600"] <= CELL_TABLE_FLOOR, ["batter", "game_year", "player"]]
cells = cells.merge(losing, on=["batter", "game_year"])
cells = cells[["game_year", "player", "batter", "strikes", "pitch_group", "zone_miss", "pitches", "chases",
               "chase_rate", "league_chase_rate", "excess_chases", "whiffs", "decision_per_600", "execution_per_600"]]
cells = cells.sort_values(["game_year", "player", "decision_per_600"])

history = table[["batter", "player", "game_year", "xchase_plus", "far_off_chase_rate_lt2k", "far_off_chase_rate_2k",
                 "decision_A_early_far", "decision_B_2k_far", "far_off_recoverable", "archetype"]]

# --------------------------------------------------
# WRITE
# --------------------------------------------------

for season in seasons:
    table[table["game_year"] == season].to_csv(OUTPUT_DIR / f"actionability_{season}.csv", index=False)
    cells[cells["game_year"] == season].to_csv(OUTPUT_DIR / f"far_off_cells_{season}.csv", index=False)
history.sort_values(["player", "game_year"]).to_csv(OUTPUT_DIR / "far_off_history.csv", index=False)
league.to_csv(OUTPUT_DIR / "league_reference.csv", index=False)

latest = seasons[-1]
t = table[table["game_year"] == latest]
print(f"{latest}: {len(t)} qualified hitters")
print(t["archetype"].value_counts().to_string())
print()
print(f"Decision-only hitters losing 8+ runs per 600 PA, {latest}:")
show = t[(t["archetype"] == "decision-only") & (t["runs_saved_per_600"] <= -8)]
print(show[["xchase_plus_rank", "player", "xchase_plus", "runs_saved_per_600", "decision_per_600",
            "execution_per_600", "far_off_recoverable", "xchase_plus_if_far_off_fixed"]]
      .round(1).to_string(index=False))
print()
print(f"Wrote {len(seasons)} seasons of actionability and far-off cell tables to {OUTPUT_DIR.relative_to(PROJECT_DIR)}/")
