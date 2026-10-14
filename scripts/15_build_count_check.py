"""
Step 15: is the hitter struggling in the counts where his leaks are?

A card's leak says "with two strikes, let breaking balls below the zone
go." Before a coach acts on that, the obvious question is whether the
hitter is actually struggling once the count gets there. A hitter who
chases there but hits well in those counts anyway is a weaker case for
changing anything than one who doesn't.

The check is made on the count group, not the single pitch: a leak is
one pitch inside a count, and the question is how the hitter's plate
appearances go once they reach that count, every pitch included.

WHAT IS MEASURED

For every qualified hitter-season and count group (first pitch, ahead,
even or behind, two strikes): the xwOBA of every plate appearance that
passed through one of those counts, against the league's in the same
counts. wOBA and OPS ride along for reference.

Two things make the raw split misleading, and the check corrects both:

  1. The count itself. The league's xwOBA once a plate appearance
     reaches a hitter's count is far above its xwOBA once it reaches two
     strikes, so a hitter is only compared with the league in the same
     counts.
  2. Noise. Beyond a hitter's overall level, how he does in one count
     group is a small, noisy difference. leak_rules.count_check shrinks
     the overall level and the count-specific extra separately, each by
     how much hitters really differ in it that season, and this script
     measures how much each part repeats (split halves of every season
     by odd and even games, and back-to-back seasons).

Status: "struggling" when the shrunk estimate is at least 10 points of
xwOBA below the league in those counts, "productive" when at least 10
above, "average" otherwise.

OUTPUTS, in results/xchase/coaching/
  count_check_<season>.csv      one row per qualified hitter, count group
                                and pitcher hand (all / R / L). The shrunk
                                estimate and status are for all pitchers;
                                the hand rows are raw, for the card tables
  count_check_reliability.csv   how much each part repeats

Run after step 04 with --expected-contact (for the leaderboards).
"""

from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leak_rules as lr  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
CLEAN = PROJECT_DIR / "data" / "cleaned"
XCHASE = PROJECT_DIR / "results" / "xchase"
OUT = XCHASE / "coaching"

pitches = pd.read_parquet(
    CLEAN / "baseline_chase_pitches.parquet",
    columns=["game_pk", "at_bat_number", "batter", "game_year", "p_throws", "description",
             "events", "balls", "strikes", "woba_value", "woba_denom",
             "estimated_woba_using_speedangle"],
)
boards = {int(p.stem[-4:]): pd.read_csv(p) for p in sorted(XCHASE.glob("xchase_leaderboard_20??.csv"))}

pas = lr.plate_appearances(pitches)
hands = pitches[lr.PA_KEY + ["p_throws"]].drop_duplicates(lr.PA_KEY)
pas = pas.merge(hands, on=lr.PA_KEY, how="left")

# --------------------------------------------------
# THE CHECK, EVERY SEASON
# --------------------------------------------------

OUT.mkdir(parents=True, exist_ok=True)
all_checks = []
for season, board in boards.items():
    hitters = set(board["batter"])
    season_pitches = pitches[pitches["game_year"] == season]
    season_pas = pas[pas["game_year"] == season]
    through = lr.through_counts(season_pitches, season_pas)
    check = lr.count_check(through, hitters)
    check.insert(2, "hand", "all")

    # Raw splits by pitcher hand, against the league facing the same hand
    by_hand = []
    for hand in ("R", "L"):
        sub = through[through["p_throws"] == hand]
        league = sub.groupby("count_group").agg(lg_x=("x", "mean"), lg_w=("w", "mean"))
        league["lg_ops"] = lr.ops(sub, ["count_group"])
        mine = sub[sub["batter"].isin(hitters)]
        raw = (mine.groupby(["batter", "count_group"])
               .agg(pa=("x", "size"), x=("x", "mean"), w=("w", "mean"))
               .join(league, on="count_group").reset_index())
        raw["ops"] = lr.ops(mine, ["batter", "count_group"]).to_numpy()
        raw["hand"] = hand
        by_hand.append(raw)
    check = pd.concat([check] + by_hand, ignore_index=True)
    check = check.merge(board[["batter", "player"]], on="batter")
    check["game_year"] = season
    check["count_group"] = pd.Categorical(check["count_group"], lr.COUNT_GROUPS, ordered=True)
    check["hand"] = pd.Categorical(check["hand"], ["all", "R", "L"], ordered=True)
    check = check.sort_values(["player", "hand", "count_group"])
    columns = ["game_year", "player", "batter", "hand", "count_group", "pa", "x", "lg_x",
               "x_shrunk", "gap", "status", "level", "extra", "level_weight", "extra_weight",
               "w", "lg_w", "ops", "lg_ops"]
    check = check[columns].rename(columns={
        "pa": "plate_appearances", "x": "xwoba", "lg_x": "league_xwoba",
        "x_shrunk": "xwoba_shrunk", "gap": "shrunk_vs_league", "level": "overall_level",
        "extra": "count_extra", "level_weight": "overall_weight",
        "extra_weight": "count_extra_weight", "w": "woba", "lg_w": "league_woba",
        "ops": "ops", "lg_ops": "league_ops"})
    check.to_csv(OUT / f"count_check_{season}.csv", index=False, float_format="%.4f")
    all_checks.append(check)

checks = pd.concat(all_checks, ignore_index=True)
checks = checks[checks["hand"] == "all"]

# --------------------------------------------------
# HOW MUCH EACH PART REPEATS
#
# raw: the hitter's xwOBA in those counts minus the league's.
# beyond overall: that, minus the same gap over all his plate appearances.
# Split halves are odd vs even games of one season (no shrinkage; it is
# the raw signal being tested). Year to year pairs qualified seasons.
# --------------------------------------------------

def gaps(through, hitters, by):
    league = through.groupby(by[:-1] + ["count_group"])["x"].mean().rename("lg")
    mine = through[through["batter"].isin(hitters)]
    g = mine.groupby(by + ["count_group"])["x"].mean().to_frame("x").join(
        league, on=by[:-1] + ["count_group"])
    wide = (g["x"] - g["lg"]).unstack("count_group")
    for group in lr.COUNT_GROUPS[1:]:
        wide[group + " beyond overall"] = wide[group] - wide["first"]
    return wide.rename(columns={"first": "overall"})


rows = []
halves = []
yearly = []
for season, board in boards.items():
    hitters = set(board["batter"])
    through = lr.through_counts(pitches[pitches["game_year"] == season],
                                pas[pas["game_year"] == season])
    through["half"] = through["game_pk"] % 2
    halves.append(gaps(through, hitters, ["half", "batter"]).assign(game_year=season))
    yearly.append(gaps(through, hitters, ["game_year", "batter"]))
halves = pd.concat(halves).reset_index()
a = halves[halves["half"] == 0].set_index(["game_year", "batter"])
b = halves[halves["half"] == 1].set_index(["game_year", "batter"])
split = a.join(b, lsuffix="_a", rsuffix="_b", how="inner")
yearly = pd.concat(yearly).reset_index()
nxt = yearly.copy()
nxt["game_year"] -= 1
pairs = yearly.merge(nxt, on=["game_year", "batter"], suffixes=("_a", "_b"))

measures = ["overall"] + lr.COUNT_GROUPS[1:] + [g + " beyond overall" for g in lr.COUNT_GROUPS[1:]]
for m in measures:
    r_half = split[[m + "_a", m + "_b"]].corr().iloc[0, 1]
    shrink = None
    if m == "overall":
        shrink = checks.loc[checks["count_group"] == "first", "overall_weight"].mean()
    elif m.endswith("beyond overall"):
        shrink = checks.loc[checks["count_group"] == m.split()[0], "count_extra_weight"].mean()
    rows.append({
        "measure": m,
        "split_half_r": r_half,
        "full_season_reliability": 2 * r_half / (1 + r_half),
        "year_to_year_r": pairs[[m + "_a", m + "_b"]].corr().iloc[0, 1],
        "mean_weight_kept_after_shrinkage": shrink,
        "hitter_seasons": len(split),
        "season_pairs": len(pairs),
    })
reliability = pd.DataFrame(rows)
reliability.to_csv(OUT / "count_check_reliability.csv", index=False, float_format="%.4f")

# --------------------------------------------------
# REPORT
# --------------------------------------------------

pd.set_option("display.width", 200)
print(f"Count check for {len(checks['batter'].unique())} hitters over {len(boards)} seasons.")
print("\nHow much each part repeats (xwOBA vs the league in the same counts):")
print(reliability[["measure", "split_half_r", "full_season_reliability", "year_to_year_r",
                   "mean_weight_kept_after_shrinkage"]].round(2).to_string(index=False))
latest = max(boards)
lc = checks[checks["game_year"] == latest]
print(f"\n{latest}: league xwOBA once the count gets there, and status shares:")
print(lc.groupby("count_group", observed=True)
      .agg(league_xwoba=("league_xwoba", "first"))
      .join(lc.groupby("count_group", observed=True)["status"].value_counts(normalize=True)
            .unstack().round(2)).to_string())
print(f"\nWrote count_check_<season>.csv for {len(boards)} seasons and "
      f"count_check_reliability.csv to {OUT.relative_to(PROJECT_DIR)}/")
