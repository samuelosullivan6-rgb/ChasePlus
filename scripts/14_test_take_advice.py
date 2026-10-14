"""
Step 14: does "take the far-off pitch" actually pay?

The coaching notes from steps 12 and 13 mostly say one thing: stop
swinging at pitches well off the plate. Before putting that advice on a
card, this script checks what happened to real hitters who did it.

For every hitter qualified in two consecutive seasons it measures the
change from one season to the next in:

    far-off chase rate   swings at pitches 0.35+ ft outside the zone
                         (the "clearly off" and "nowhere near" buckets)
    zone swing rate      swings at pitches in the zone
    xChase+, K%, BB%, xwOBA

and asks two questions:

  1. When far-off chase rate falls, do the outcomes improve?
  2. Is there a hidden cost: do hitters who cut chases also start
     taking more strikes (zone swing rate falls)?

Changes in one season's stat are partly regression to the mean: a hitter
coming off a bad year tends to improve whatever he does. So every slope is
fit with the hitter's first-season level as a second predictor, which
compares hitters who started at the same far-off chase rate.

Writes results/xchase/coaching/take_advice_backtest.csv (one row per
hitter pair of seasons) and take_advice_summary.csv (the slopes and group
means quoted in the README).
"""

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
CLEAN = PROJECT_DIR / "data" / "cleaned"
XCHASE = PROJECT_DIR / "results" / "xchase"
OUT = XCHASE / "coaching"

FAR_OFF_FT = 0.35        # same edge as script 04's "clearly off" bucket
GROUP_CUTOFF = 0.03      # a 3-point change in far-off chase rate
STRIKEOUTS = {"strikeout", "strikeout_double_play"}
WALKS = {"walk"}

pitches = pd.read_parquet(
    CLEAN / "baseline_chase_pitches.parquet",
    columns=["batter", "game_year", "is_analyzable", "is_in_zone",
             "is_outside_zone", "is_swing", "distance_outside_zone",
             "events", "woba_value", "woba_denom",
             "estimated_woba_using_speedangle", "description"],
)

# --------------------------------------------------
# PER HITTER-SEASON RATES
# --------------------------------------------------

tracked = pitches[pitches["is_analyzable"] == 1]
zone = tracked[tracked["is_in_zone"] == 1]
far = tracked[(tracked["is_outside_zone"] == 1)
              & (tracked["distance_outside_zone"] > FAR_OFF_FT)]

keys = ["batter", "game_year"]
rates = pd.DataFrame({
    "far_off_chase_rate": far.groupby(keys)["is_swing"].mean(),
    "far_off_pitches": far.groupby(keys).size(),
    "zone_swing_rate": zone.groupby(keys)["is_swing"].mean(),
    "zone_pitches": zone.groupby(keys).size(),
})

# Plate appearance outcomes (every pitch row, tracked or not)
ends = pitches[pitches["events"].notna() & (pitches["events"] != "truncated_pa")].copy()
in_play = ends["description"] == "hit_into_play"
has_x = ends["estimated_woba_using_speedangle"].notna()
# xwOBA as Savant builds it: the expected value for a ball in play,
# the actual wOBA value for everything else.
ends["x_value"] = np.where(in_play & has_x,
                           ends["estimated_woba_using_speedangle"],
                           ends["woba_value"])
outcomes = ends.groupby(keys).agg(
    pa=("events", "size"),
    k=("events", lambda s: s.isin(STRIKEOUTS).sum()),
    bb=("events", lambda s: s.isin(WALKS).sum()),
    x_sum=("x_value", "sum"),
    denom=("woba_denom", "sum"),
)
outcomes["k_rate"] = outcomes["k"] / outcomes["pa"]
outcomes["bb_rate"] = outcomes["bb"] / outcomes["pa"]
outcomes["xwoba"] = outcomes["x_sum"] / outcomes["denom"]
rates = rates.join(outcomes[["k_rate", "bb_rate", "xwoba"]])

# Qualified hitter-seasons only, with xChase+
boards = []
for path in sorted(XCHASE.glob("xchase_leaderboard_20??.csv")):
    board = pd.read_csv(path)[["batter", "game_year", "player", "xchase_plus"]]
    boards.append(board)
qualified = pd.concat(boards, ignore_index=True)
seasons = qualified.merge(rates.reset_index(), on=keys, how="left")

# --------------------------------------------------
# CONSECUTIVE-SEASON PAIRS
# --------------------------------------------------

later = seasons.copy()
later["game_year"] -= 1
pairs = seasons.merge(later, on=["batter", "game_year"], suffixes=("_1", "_2"))
pairs = pairs.rename(columns={"game_year": "season_1", "player_1": "player"})
pairs["season_2"] = pairs["season_1"] + 1

METRICS = ["far_off_chase_rate", "zone_swing_rate", "xchase_plus",
           "k_rate", "bb_rate", "xwoba"]
for m in METRICS:
    pairs[f"change_{m}"] = pairs[f"{m}_2"] - pairs[f"{m}_1"]

pairs["group"] = np.select(
    [pairs["change_far_off_chase_rate"] <= -GROUP_CUTOFF,
     pairs["change_far_off_chase_rate"] >= GROUP_CUTOFF],
    ["cut far-off chases", "chased more"], "about the same",
)

# --------------------------------------------------
# SLOPES: change in outcome per 10-point cut in far-off chase rate,
# holding the first-season far-off chase rate fixed.
# --------------------------------------------------

def slope(outcome):
    y = pairs[f"change_{outcome}"].to_numpy()
    X = np.column_stack([
        np.ones(len(pairs)),
        pairs["change_far_off_chase_rate"].to_numpy(),
        pairs["far_off_chase_rate_1"].to_numpy(),
    ])
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    residual = y - X @ beta
    sigma2 = residual @ residual / (len(y) - X.shape[1])
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
    # report per 10-point CUT (negative change), so a positive number
    # means the outcome went up when chasing went down
    return -0.10 * beta[1], 0.10 * se[1], len(y)

rows = []
for m in METRICS[1:]:
    b, se, n = slope(m)
    rows.append({"measure": m, "kind": "slope_per_10pt_cut",
                 "value": b, "se": se, "n_pairs": n})
for g, sub in pairs.groupby("group"):
    for m in METRICS:
        col = sub[f"change_{m}"].dropna()
        rows.append({"measure": m, "kind": f"mean_change: {g}",
                     "value": col.mean(), "se": col.std() / np.sqrt(len(col)),
                     "n_pairs": len(col)})
summary = pd.DataFrame(rows)

OUT.mkdir(parents=True, exist_ok=True)
keep = (["player", "batter", "season_1", "season_2", "group"]
        + [f"{m}_{i}" for m in METRICS for i in (1, 2)]
        + [f"change_{m}" for m in METRICS])
pairs[keep].sort_values(["season_1", "player"]).to_csv(
    OUT / "take_advice_backtest.csv", index=False)
summary.to_csv(OUT / "take_advice_summary.csv", index=False)

pd.set_option("display.width", 200)
print(f"{len(pairs)} consecutive qualified season pairs, "
      f"{pairs['season_1'].min()}-{pairs['season_2'].max()}")
print(pairs["group"].value_counts().to_string())
print("\nPer 10-point cut in far-off chase rate (first-season level held fixed):")
s = summary[summary["kind"] == "slope_per_10pt_cut"].set_index("measure")
for m, label, scale, unit in [
    ("xchase_plus", "xChase+", 1, " pts"),
    ("zone_swing_rate", "zone swing rate", 100, " pct pts"),
    ("k_rate", "K%", 100, " pct pts"),
    ("bb_rate", "BB%", 100, " pct pts"),
    ("xwoba", "xwOBA", 1000, " pts (x1000)"),
]:
    print(f"  {label:16s} {s.loc[m, 'value'] * scale:+6.2f} ± {s.loc[m, 'se'] * scale:4.2f}{unit}")
print("\nMean change by group:")
g = summary[summary["kind"].str.startswith("mean_change")].copy()
g["group"] = g["kind"].str.replace("mean_change: ", "")
table = g.pivot(index="group", columns="measure", values="value")[METRICS]
for m, scale in [("far_off_chase_rate", 100), ("zone_swing_rate", 100),
                 ("k_rate", 100), ("bb_rate", 100), ("xwoba", 1000)]:
    table[m] = table[m] * scale
print(table.round(2).to_string())
print(f"\nWrote take_advice_backtest.csv and take_advice_summary.csv to {OUT.relative_to(PROJECT_DIR)}/")
