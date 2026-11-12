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
fit with the hitter's first-season far-off chase rate AND his first-season
level of the outcome as further predictors, the same design as step 16.
Without the outcome's own level, a bad xwOBA year that happened to be a
high-chase year reverts on both counts at once and the slope takes the
credit. Standard errors are clustered by hitter (step 16's helper in
leak_rules.py), since the same hitter appears in up to five pairs.

The 2025 -> 2026 pair straddles the 2026 ABS strike-zone box: Statcast
records a shorter zone in 2026, so which pitches count as "far off" moves
with it. Every slope is therefore fit twice, on all pairs and on the pairs
that end in 2025 or earlier, and both are printed and saved.

Writes results/xchase/coaching/take_advice_backtest.csv (one row per
hitter pair of seasons) and take_advice_summary.csv (the slopes and group
means quoted in the README).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leak_rules as lr  # noqa: E402

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
                           ends["woba_value"]).astype(float)
# Only plate appearances in the wOBA denominator carry an xwOBA, the same
# definition as leak_rules.plate_appearances() in step 16. Statcast gives
# the rows outside it a non-zero woba_value anyway (sacrifice bunts 0.2 or
# 0.9 with woba_denom 0; intentional walks 0.4 with woba_denom missing), so
# summing x_value over every PA end and dividing by the denominator count
# overstated xwOBA, by more for bunters and intentionally walked hitters.
ends["in_woba"] = (ends["woba_denom"] == 1).fillna(False).astype(bool)
ends["x_in"] = ends["x_value"].where(ends["in_woba"])
outcomes = ends.groupby(keys).agg(
    pa=("events", "size"),
    k=("events", lambda s: s.isin(STRIKEOUTS).sum()),
    bb=("events", lambda s: s.isin(WALKS).sum()),
    x_sum=("x_in", "sum"),
    denom=("in_woba", "sum"),
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
# holding the first-season far-off chase rate and the first-season level
# of the outcome fixed. Fit on all pairs and again without 2025 -> 2026.
# --------------------------------------------------

ABS_SEASON = 2026   # first season on the ABS box; the pair into it is set aside

def slope(outcome, P, with_level=True):
    """Per 10-point CUT in far-off chase rate (negative change), so a
    positive number means the outcome went up when chasing went down.
    Returns the estimate, its classical and hitter-clustered standard
    errors, and the pair and hitter counts. with_level=False drops the
    outcome's first-season level, the specification this step used before
    it matched step 16; kept so the two can be compared."""
    controls = ["change_far_off_chase_rate", "far_off_chase_rate_1"]
    if with_level:
        controls.append(f"{outcome}_1")
    Q = P.dropna(subset=[f"change_{outcome}"] + controls)
    y = Q[f"change_{outcome}"].to_numpy(float)
    beta, se_cl = lr.ols(y, [Q[c] for c in controls], Q["batter"].to_numpy())
    # classical standard error alongside, for the comparison with the old file
    X = np.column_stack([np.ones(len(Q))] + [Q[c].to_numpy(float) for c in controls])
    residual = y - X @ beta
    sigma2 = residual @ residual / (len(y) - X.shape[1])
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
    return -0.10 * beta[1], 0.10 * se[1], 0.10 * se_cl[1], len(Q), Q["batter"].nunique()

before_abs = pairs[pairs["season_2"] < ABS_SEASON]
rows = []
for m in METRICS[1:]:
    for kind, with_level in [("slope_per_10pt_cut", True),
                             ("slope_per_10pt_cut (far-off level only)", False)]:
        b, se, se_cl, n, h = slope(m, pairs, with_level)
        b_x, _, se_cl_x, n_x, h_x = slope(m, before_abs, with_level)
        rows.append({"measure": m, "kind": kind,
                     "value": b, "se": se, "n_pairs": n,
                     "se_clustered": se_cl, "n_hitters": h,
                     "value_excl_2026": b_x, "se_clustered_excl_2026": se_cl_x,
                     "n_pairs_excl_2026": n_x, "n_hitters_excl_2026": h_x})
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
s = summary[summary["kind"] == "slope_per_10pt_cut"].set_index("measure")
print(f"\nPer 10-point cut in far-off chase rate (first-season far-off rate and\n"
      f"outcome level held fixed; ± is the standard error clustered by hitter):\n"
      f"  {'':16s} {'all pairs':>20s}   {'without 2025->2026':>20s}")
print(f"  {'':16s} {'(' + str(int(s['n_pairs'].iloc[0])) + ' pairs)':>20s}   "
      f"{'(' + str(int(s['n_pairs_excl_2026'].iloc[0])) + ' pairs)':>20s}")
for m, label, scale, unit in [
    ("xchase_plus", "xChase+", 1, " pts"),
    ("zone_swing_rate", "zone swing rate", 100, " pct pts"),
    ("k_rate", "K%", 100, " pct pts"),
    ("bb_rate", "BB%", 100, " pct pts"),
    ("xwoba", "xwOBA", 1000, " pts (x1000)"),
]:
    r = s.loc[m]
    print(f"  {label:16s} {r['value'] * scale:+9.2f} ± {r['se_clustered'] * scale:5.2f}   "
          f"{r['value_excl_2026'] * scale:+9.2f} ± {r['se_clustered_excl_2026'] * scale:5.2f}{unit}")
old = summary[summary["kind"] == "slope_per_10pt_cut (far-off level only)"].set_index("measure")
print("\nSame without the outcome's first-season level (the step's old design),\n"
      "all pairs, classical ± then clustered ±:")
for m, label, scale in [("xchase_plus", "xChase+", 1), ("zone_swing_rate", "zone swing rate", 100),
                        ("k_rate", "K%", 100), ("bb_rate", "BB%", 100), ("xwoba", "xwOBA", 1000)]:
    r = old.loc[m]
    print(f"  {label:16s} {r['value'] * scale:+9.2f} ± {r['se'] * scale:5.2f} / ± {r['se_clustered'] * scale:5.2f}")
print("\nMean change by group:")
g = summary[summary["kind"].str.startswith("mean_change")].copy()
g["group"] = g["kind"].str.replace("mean_change: ", "")
table = g.pivot(index="group", columns="measure", values="value")[METRICS]
for m, scale in [("far_off_chase_rate", 100), ("zone_swing_rate", 100),
                 ("k_rate", 100), ("bb_rate", 100), ("xwoba", 1000)]:
    table[m] = table[m] * scale
print(table.round(2).to_string())
print(f"\nWrote take_advice_backtest.csv and take_advice_summary.csv to {OUT.relative_to(PROJECT_DIR)}/")
