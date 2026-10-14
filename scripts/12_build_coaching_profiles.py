"""
Step 12: where the worst xChase+ hitters lose their runs.

Takes the bottom N hitters by xChase+ in one season and splits each one's
runs lost (vs. the league baseline, per 600 PA) along the dimensions a
hitting coach can act on: count, distance off the plate, side of the
zone the pitch missed on, pitch group, pitcher hand and swing result.

Every out-of-zone pitch's runs_saved (from 04_build_chase_leaderboard.py
--expected-contact) is split into two parts that add up exactly:

    decision  = expected_cost - is_chase * league_cost_per_chase_in_cell
    execution = is_chase * (league_cost_per_chase_in_cell - chase_cost)

where the cell is (season, count, distance bucket), the same cell the
league baseline uses. "decision" is what the hitter's swing/take choices
cost if each of his chases had turned out like a league-average chase in
that cell. "execution" is what his chases cost beyond that: whiffing or
making weak contact more (negative) or less (positive) than the league
does on the same kind of pitch.

Writes, in results/xchase/coaching/:
  bottom<N>_<season>_summary.csv        one row per hitter
  bottom<N>_<season>_by_dimension.csv   runs by strikes / balls / distance /
                                        zone miss / pitch group / hand /
                                        swing result, per hitter
  bottom<N>_<season>_cells.csv          strikes x pitch group x zone miss,
                                        per hitter, worst cells first
  bottom<N>_<season>_history.csv        the same hitters' headline splits
                                        in each season they have data
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "xchase"
OUT = RESULTS / "coaching"

parser = argparse.ArgumentParser()
parser.add_argument("--season", type=int, default=2026)
parser.add_argument("--bottom", type=int, default=10)
parser.add_argument("--history-seasons", type=int, nargs="*",
                    default=[2024, 2025, 2026])
args = parser.parse_args()

SEASON, N = args.season, args.bottom
HIST = sorted(set(args.history_seasons) | {SEASON})
PA_PER_SEASON = 600

FASTBALLS = {"FF", "SI", "FC", "FA"}
BREAKING = {"SL", "ST", "CU", "KC", "SV", "CS"}
HALF_PLATE_PLUS_BALL = 0.83  # same geometry as script 04's miss_direction
WHIFFS = {"swinging_strike", "swinging_strike_blocked", "foul_tip"}

# --------------------------------------------------
# LOAD AND JOIN
# --------------------------------------------------

leaderboards = {
    y: pd.read_csv(RESULTS / f"xchase_leaderboard_{y}.csv")
    for y in HIST if (RESULTS / f"xchase_leaderboard_{y}.csv").exists()
}
bottom = (
    leaderboards[SEASON].sort_values("xchase_plus_rank").tail(N)
)
ids = bottom["batter"].tolist()
names = dict(zip(bottom["batter"], bottom["player"]))

costs = pd.read_parquet(ROOT / "data/cleaned/xchase_costs_by_pitch.parquet")
costs = costs[costs["game_year"].isin(HIST)]
pitches = pd.read_parquet(
    ROOT / "data/cleaned/baseline_chase_pitches.parquet",
    columns=[
        "game_pk", "at_bat_number", "pitch_number", "batter", "game_year",
        "p_throws", "pitch_type", "description", "plate_x_batter",
        "plate_z", "sz_top", "sz_bot", "estimated_woba_using_speedangle",
    ],
)
pitches = pitches[pitches["game_year"].isin(HIST)]
df = costs.merge(
    pitches,
    on=["game_pk", "at_bat_number", "pitch_number", "batter", "game_year"],
    how="left",
)
assert df["pitch_type"].notna().mean() > 0.99

# --------------------------------------------------
# DECISION / EXECUTION SPLIT
# --------------------------------------------------

chased = df[df["is_chase"] == 1]
cost_in_cell = (
    chased.groupby(["game_year", "balls", "strikes", "distance_bucket"])
    ["chase_cost"].mean().rename("league_cost_per_chase")
)
df = df.join(cost_in_cell, on=["game_year", "balls", "strikes", "distance_bucket"])
df["league_cost_per_chase"] = df["league_cost_per_chase"].fillna(0.0)
df["decision"] = (
    df["expected_cost_per_pitch"] - df["is_chase"] * df["league_cost_per_chase"]
)
df["execution"] = df["is_chase"] * (df["league_cost_per_chase"] - df["chase_cost"])
assert np.allclose(df["decision"] + df["execution"], df["runs_saved"])

# --------------------------------------------------
# LABELS
# --------------------------------------------------

df["pitch_group"] = np.select(
    [df["pitch_type"].isin(FASTBALLS), df["pitch_type"].isin(BREAKING)],
    ["fastball", "breaking"], "offspeed",
)
above = (df["plate_z"] - df["sz_top"]).clip(lower=0)
below = (df["sz_bot"] - df["plate_z"]).clip(lower=0)
inside = (-df["plate_x_batter"] - HALF_PLATE_PLUS_BALL).clip(lower=0)
away = (df["plate_x_batter"] - HALF_PLATE_PLUS_BALL).clip(lower=0)
vert = np.where(above > 0, "up", np.where(below > 0, "down", ""))
horz = np.where(inside > 0, "in", np.where(away > 0, "away", ""))
df["zone_miss"] = [(v + "-" + h).strip("-") or "edge" for v, h in zip(vert, horz)]
df["swing_result"] = np.select(
    [df["is_chase"] == 0, df["description"].isin(WHIFFS),
     df["description"] == "foul", df["description"] == "hit_into_play"],
    ["take", "whiff", "foul", "in play"], "other",
)
df["strikes_lbl"] = df["strikes"].map({0: "0 strikes", 1: "1 strike", 2: "2 strikes"})
df["balls_lbl"] = df["balls"].map({0: "0 balls", 1: "1 ball", 2: "2 balls", 3: "3 balls"})
df["hand"] = np.where(df["p_throws"] == "R", "vs RHP", "vs LHP")
df["whiff"] = df["description"].isin(WHIFFS).astype(int)

DIMENSIONS = ["strikes_lbl", "balls_lbl", "distance_bucket", "zone_miss",
              "pitch_group", "hand", "count_state", "pitch_type"]

# --------------------------------------------------
# PER-HITTER TABLES, TARGET SEASON
# --------------------------------------------------

season = df[df["game_year"] == SEASON]
league_chase = season["is_chase"].mean()

summary, by_dim, cells = [], [], []
for batter in ids:
    row = bottom[bottom["batter"] == batter].iloc[0]
    d = season[season["batter"] == batter]
    k = PA_PER_SEASON / row["plate_appearances"]
    ch = d[d["is_chase"] == 1]
    lg_ch = season[season["is_chase"] == 1]
    two = d[d["strikes"] == 2]
    in_play = ch[ch["swing_result"] == "in play"]
    summary.append({
        "player": row["player"], "batter": batter, "rank": int(row["xchase_plus_rank"]),
        "xchase_plus": round(row["xchase_plus"], 1), "pa": int(row["plate_appearances"]),
        "ooz_pitches": len(d), "chases": int(d["is_chase"].sum()),
        "chase_rate": round(d["is_chase"].mean() * 100, 1),
        "league_chase_rate": round(league_chase * 100, 1),
        "runs_per_600": round(d["runs_saved"].sum() * k, 1),
        "decision_per_600": round(d["decision"].sum() * k, 1),
        "execution_per_600": round(d["execution"].sum() * k, 1),
        "whiff_given_chase": round(ch["whiff"].mean() * 100, 1),
        "league_whiff_given_chase": round(lg_ch["whiff"].mean() * 100, 1),
        "in_play_given_chase": round((ch["swing_result"] == "in play").mean() * 100, 1),
        "league_in_play_given_chase": round((lg_ch["swing_result"] == "in play").mean() * 100, 1),
        "xwoba_chased_in_play": round(in_play["estimated_woba_using_speedangle"].mean(), 3),
        "league_xwoba_chased_in_play": round(
            lg_ch.loc[lg_ch["swing_result"] == "in play",
                      "estimated_woba_using_speedangle"].mean(), 3),
        "two_strike_share_of_loss": round(two["runs_saved"].sum() / d["runs_saved"].sum(), 2),
        "two_strike_chase_rate": round(two["is_chase"].mean() * 100, 1),
        "league_two_strike_chase_rate": round(
            season.loc[season["strikes"] == 2, "is_chase"].mean() * 100, 1),
        "two_strike_whiff_given_chase": round(two.loc[two["is_chase"] == 1, "whiff"].mean() * 100, 1),
        "league_two_strike_whiff_given_chase": round(
            season.loc[(season["strikes"] == 2) & (season["is_chase"] == 1), "whiff"].mean() * 100, 1),
    })
    for dim in DIMENSIONS:
        g = d.groupby(dim).agg(
            pitches=("is_chase", "size"), chases=("is_chase", "sum"),
            chase_rate=("is_chase", "mean"), runs=("runs_saved", "sum"),
            decision=("decision", "sum"), execution=("execution", "sum"),
        )
        g["league_chase_rate"] = season.groupby(dim)["is_chase"].mean()
        g["excess_chases"] = ((g["chase_rate"] - g["league_chase_rate"]) * g["pitches"]).round(0)
        for c in ["runs", "decision", "execution"]:
            g[c] = (g[c] * k).round(2)
        g["chase_rate"] = (g["chase_rate"] * 100).round(1)
        g["league_chase_rate"] = (g["league_chase_rate"] * 100).round(1)
        g = g.reset_index().rename(columns={dim: "level"})
        g.insert(0, "dimension", dim)
        g.insert(0, "player", row["player"])
        by_dim.append(g)
    # swing result is only defined on chases; show share vs league too
    sr = pd.DataFrame({
        "pitches": ch["swing_result"].value_counts(),
        "share": ch["swing_result"].value_counts(normalize=True).round(3),
        "league_share": lg_ch["swing_result"].value_counts(normalize=True).round(3),
        "execution": (ch.groupby("swing_result")["execution"].sum() * k).round(2),
    }).reset_index().rename(columns={"index": "level", "swing_result": "level"})
    sr.insert(0, "dimension", "swing_result")
    sr.insert(0, "player", row["player"])
    by_dim.append(sr)

    g = d.groupby(["strikes_lbl", "pitch_group", "zone_miss"]).agg(
        pitches=("is_chase", "size"), chases=("is_chase", "sum"),
        chase_rate=("is_chase", "mean"), runs=("runs_saved", "sum"),
        decision=("decision", "sum"), execution=("execution", "sum"),
    )
    g["league_chase_rate"] = season.groupby(["strikes_lbl", "pitch_group", "zone_miss"])["is_chase"].mean()
    for c in ["runs", "decision", "execution"]:
        g[c] = (g[c] * k).round(2)
    g["chase_rate"] = (g["chase_rate"] * 100).round(1)
    g["league_chase_rate"] = (g["league_chase_rate"] * 100).round(1)
    g = g.reset_index().sort_values("runs")
    g.insert(0, "player", row["player"])
    cells.append(g)

# --------------------------------------------------
# HISTORY: same hitters, every season with data
# --------------------------------------------------

history = []
for batter in ids:
    for y in HIST:
        d = df[(df["batter"] == batter) & (df["game_year"] == y)]
        if len(d) < 150:
            continue
        L = df[df["game_year"] == y]
        lb = leaderboards.get(y)
        r = lb[lb["batter"] == batter] if lb is not None else pd.DataFrame()
        qualified = len(r) > 0
        k = PA_PER_SEASON / r["plate_appearances"].iloc[0] if qualified else np.nan
        ch = d[d["is_chase"] == 1]
        zone = d.groupby("zone_miss")["runs_saved"].sum()
        pg = d.groupby("pitch_group")["runs_saved"].sum()
        history.append({
            "player": names[batter], "season": y, "qualified": qualified,
            "xchase_plus": round(r["xchase_plus"].iloc[0], 1) if qualified else np.nan,
            "ooz_pitches": len(d),
            "chase_rate": round(d["is_chase"].mean() * 100, 1),
            "league_chase_rate": round(L["is_chase"].mean() * 100, 1),
            "runs_per_600": round(d["runs_saved"].sum() * k, 1) if qualified else np.nan,
            "decision_per_600": round(d["decision"].sum() * k, 1) if qualified else np.nan,
            "execution_per_600": round(d["execution"].sum() * k, 1) if qualified else np.nan,
            "whiff_given_chase": round(ch["whiff"].mean() * 100, 1),
            "league_whiff_given_chase": round(L.loc[L["is_chase"] == 1, "whiff"].mean() * 100, 1),
            "worst_zone": zone.idxmin(), "worst_pitch_group": pg.idxmin(),
            "chase_rate_down": round(d.loc[d["zone_miss"] == "down", "is_chase"].mean() * 100, 1),
            "league_chase_rate_down": round(L.loc[L["zone_miss"] == "down", "is_chase"].mean() * 100, 1),
            "chase_rate_up": round(d.loc[d["zone_miss"] == "up", "is_chase"].mean() * 100, 1),
            "league_chase_rate_up": round(L.loc[L["zone_miss"] == "up", "is_chase"].mean() * 100, 1),
            "chase_rate_breaking": round(d.loc[d["pitch_group"] == "breaking", "is_chase"].mean() * 100, 1),
            "league_chase_rate_breaking": round(L.loc[L["pitch_group"] == "breaking", "is_chase"].mean() * 100, 1),
        })

# --------------------------------------------------
# WRITE
# --------------------------------------------------

OUT.mkdir(parents=True, exist_ok=True)
stem = f"bottom{N}_{SEASON}"
pd.DataFrame(summary).to_csv(OUT / f"{stem}_summary.csv", index=False)
pd.concat(by_dim, ignore_index=True).to_csv(OUT / f"{stem}_by_dimension.csv", index=False)
pd.concat(cells, ignore_index=True).to_csv(OUT / f"{stem}_cells.csv", index=False)
pd.DataFrame(history).to_csv(OUT / f"{stem}_history.csv", index=False)

pooled = season[season["batter"].isin(ids)]
total = pooled["runs_saved"].sum()
print(f"Bottom {N} by xChase+, {SEASON}. Runs lost vs league, pooled, share by:")
for dim in ["strikes_lbl", "zone_miss", "pitch_group", "distance_bucket"]:
    g = pooled.groupby(dim)[["runs_saved", "decision", "execution"]].sum()
    g["share"] = (g["runs_saved"] / total * 100).round(0)
    print(f"\n  {dim}")
    print(g.round(1).to_string())
print(f"\n  decision {pooled['decision'].sum() / total:.0%} / execution {pooled['execution'].sum() / total:.0%}")
print("\nSummary:")
print(pd.DataFrame(summary)[["player", "rank", "xchase_plus", "chase_rate", "runs_per_600",
                             "decision_per_600", "execution_per_600", "whiff_given_chase",
                             "two_strike_share_of_loss"]].to_string(index=False))
print(f"\nWrote 4 files to {OUT}")
