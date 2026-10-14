"""
Step 21 (test): which hitters made the adjustment their frozen card
recommended, and hit better in those counts the next season?

Step 20 scores a frozen file on the hitter as a whole. This step reads
its per-hitter output and asks the case-study question instead, on the
same frozen cells:

  ADJUSTED   chased in the frozen leak cells at least ADJUST_PTS below
             what the season-to-season line predicted with no change
             (actual minus predicted excess <= -ADJUST_PTS), so the drop
             is beyond the regression everyone gets for free.
  IMPROVED   in the count groups of those leaks, both
               - xwOBA against the league in those counts went up, and
               - it went up by more than his overall xwOBA did (the gap
                 in those counts minus his gap in every plate appearance,
                 so a hitter who simply hit better everywhere doesn't count),
             and the run value of his choices in the leak cells went up.

A leak in the first-pitch count can't separate the counts from the
whole season (every plate appearance passes through 0-0), so it adds
nothing to the situation-specific measure.

The groups are compared side by side: hitters who adjusted, who held
to the line, and who chased more than predicted. The question is
whether the adjusters' gain in those counts beats the other groups',
not just whether it is above zero.

OUTPUTS, in results/xchase/coaching/
  adjusters_<next>.csv   one row per scored hitter, with the flags

Options: --season (default 2025; the frozen season, scored on the next).

Run after step 20 for that season.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUT = PROJECT_DIR / "results" / "xchase" / "coaching"

ADJUST_PTS = 0.05               # beyond the line's prediction, in chase-rate points

parser = argparse.ArgumentParser(description="Find hitters who fixed a frozen leak and gained in those counts.")
parser.add_argument("--season", type=int, default=2025, help="the frozen season")
args = parser.parse_args()
SEASON = args.season
NEXT = SEASON + 1

scores_file = OUT / f"leak_scores_{NEXT}.csv"
if not scores_file.exists():
    raise SystemExit(f"No {scores_file.name}; run step 20 --season {SEASON} first.")
scores = pd.read_csv(scores_file).set_index("batter")
frozen = pd.read_csv(OUT / f"leak_predictions_{SEASON}.csv")
leaks = frozen[frozen["row"] != "hitter"]

# --------------------------------------------------
# XWOBA IN THE LEAK COUNTS, BOTH SEASONS
# --------------------------------------------------


def count_gaps(season):
    c = pd.read_csv(OUT / f"count_check_{season}.csv")
    c = c[c["hand"] == "all"].copy()
    c["gap"] = c["xwoba"] - c["league_xwoba"]
    overall = c[c["count_group"] == "first"].set_index("batter")["gap"]
    c["extra"] = c["gap"] - c["batter"].map(overall)
    return c.set_index(["batter", "count_group"])[["plate_appearances", "gap", "extra"]], overall


gaps, overall = {}, {}
for season in (SEASON, NEXT):
    gaps[season], overall[season] = count_gaps(season)

groups = leaks[["batter", "count_group"]].drop_duplicates()
rows = []
for batter, g in groups.groupby("batter"):
    if batter not in scores.index:
        continue
    r = {"batter": batter, "leak_counts": "/".join(sorted(g["count_group"]))}
    for i, season in ((1, SEASON), (2, NEXT)):
        at = [(batter, cg) for cg in g["count_group"] if (batter, cg) in gaps[season].index]
        if not at:
            r[f"count_gap_{i}"] = r[f"count_extra_{i}"] = np.nan
            continue
        t = gaps[season].loc[at]
        w = t["plate_appearances"]
        r[f"count_gap_{i}"] = np.average(t["gap"], weights=w)
        r[f"count_extra_{i}"] = np.average(t["extra"], weights=w)
        r[f"count_pa_{i}"] = w.sum()
        r[f"overall_gap_{i}"] = overall[season].get(batter, np.nan)
    rows.append(r)
sit = pd.DataFrame(rows).set_index("batter")

# --------------------------------------------------
# FLAGS
# --------------------------------------------------

d = scores[["player", "leaks", "count_status", "leak_chase_rate_1", "leak_chase_rate_2",
            f"predicted_excess_{NEXT}", f"actual_excess_{NEXT}", "leak_choices_per_600_1",
            "leak_choices_per_600_2", f"pitches_{SEASON}", f"pitches_{NEXT}",
            "change_offense_runs"]].join(sit)
d["beyond_line"] = d[f"actual_excess_{NEXT}"] - d[f"predicted_excess_{NEXT}"]
d["change_count_gap"] = d["count_gap_2"] - d["count_gap_1"]
d["change_count_extra"] = d["count_extra_2"] - d["count_extra_1"]
d["change_overall_gap"] = d["overall_gap_2"] - d["overall_gap_1"]
d["change_leak_choices"] = d["leak_choices_per_600_2"] - d["leak_choices_per_600_1"]
d["group"] = np.select([d["beyond_line"] <= -ADJUST_PTS, d["beyond_line"] >= ADJUST_PTS],
                       ["adjusted", "chased more"], "held to the line")
d["adjusted"] = d["group"] == "adjusted"
d["improved"] = ((d["change_count_gap"] > 0) & (d["change_count_extra"] > 0)
                 & (d["change_leak_choices"] > 0))
d["adjusted_and_improved"] = d["adjusted"] & d["improved"]

out = OUT / f"adjusters_{NEXT}.csv"
d.round(4).sort_values(["adjusted_and_improved", "change_count_extra"],
                       ascending=[False, False]).to_csv(out)

# --------------------------------------------------
# REPORT
# --------------------------------------------------


def mean_se(x):
    x = x.dropna()
    return f"{x.mean() * 1000:+5.1f} ± {x.std(ddof=1) / np.sqrt(len(x)) * 1000:4.1f}"


print(f"\n{SEASON} cards scored on {NEXT}: {len(d)} hitters. 'Adjusted' = chased "
      f"{ADJUST_PTS * 100:.0f}+ pts below the line's prediction in the frozen cells.\n")
print(f"{'':18s}{'n':>4s}  {'leak chase':>11s}  {'xwOBA in leak counts':>21s}  "
      f"{'...beyond overall':>18s}  {'overall xwOBA':>14s}")
print(f"{'':18s}{'':>4s}  {'(pts)':>11s}  {'(pts, +/- se)':>21s}  {'':>18s}  {'':>14s}")
for name in ["adjusted", "held to the line", "chased more"]:
    g = d[d["group"] == name]
    lc = (g["leak_chase_rate_2"] - g["leak_chase_rate_1"]).mean() * 100
    print(f"{name:18s}{len(g):4d}  {lc:+11.1f}  {mean_se(g['change_count_gap']):>21s}  "
          f"{mean_se(g['change_count_extra']):>18s}  {mean_se(g['change_overall_gap']):>14s}")

a = d[d["adjusted"]]
print(f"\n{int(d['adjusted_and_improved'].sum())} of {len(a)} adjusters also gained in those "
      f"counts, beyond their overall change, with better choices in the cells:\n")
show = d[d["adjusted_and_improved"]].sort_values("change_count_extra", ascending=False)
print(f"{'hitter':22s}{'counts':>14s}{'leak chase':>14s}{'vs line':>9s}"
      f"{'xwOBA there':>16s}{'beyond overall':>16s}{'PA there':>10s}")
for _, r in show.iterrows():
    print(f"{r['player']:22s}{r['leak_counts']:>14s}"
          f"{r['leak_chase_rate_1'] * 100:6.0f}% → {r['leak_chase_rate_2'] * 100:3.0f}%"
          f"{r['beyond_line'] * 100:+8.0f}"
          f"{r['count_gap_1'] * 1000:+7.0f} → {r['count_gap_2'] * 1000:+4.0f}"
          f"{r['change_count_extra'] * 1000:+16.0f}"
          f"{r['count_pa_1']:5.0f}/{r['count_pa_2']:<4.0f}")
print(f"\nxwOBA in points (thousandths) against the league in the same counts. Wrote {out.name}.")
