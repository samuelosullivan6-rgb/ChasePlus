"""
Does a hitter's chase value repeat from one season to the next?

A leaderboard can be an accurate record of what happened without
measuring a lasting property of a player. This script correlates each
qualified hitter's chase value in consecutive seasons:

  high correlation -> chase value behaves like a skill
  near zero        -> it is mostly noise and circumstance

Design choices:
  - The values come from chase_cost_leaderboard_by_season.csv, where the
    called-strike model, league baseline and qualification floors are all
    per season. A baseline pooled across years would let a league-wide
    shift move every hitter together and inflate the correlation.
  - The unshrunk runs_saved_per_600_pa is correlated. Shrinkage pulls
    everyone toward the season mean, which would make seasons look more
    alike than the measurements are.
  - Chase rate, one of the most stable hitter stats, gets the same test
    as a yardstick.

Input:   results/chase_cost_leaderboard_by_season.csv
Outputs: results/chase_value_reliability.csv
         results/chase_value_reliability.png

With --expected-contact it does the same for xChase+: it reads and writes
results/xchase/ instead of results/.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


# --------------------------------------------------
# FILE LOCATIONS
# --------------------------------------------------

# Paths are anchored to the project folder (the parent of scripts/), not
# to the directory the script is run from.
PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

parser = argparse.ArgumentParser(
    description="Year-to-year repeatability of chase value (Chase+ or xChase+)."
)
parser.add_argument(
    "--expected-contact",
    action="store_true",
    help="use the xChase+ run: read and write results/xchase/",
)
arguments = parser.parse_args()

EXPECTED_CONTACT = arguments.expected_contact

if EXPECTED_CONTACT:
    RESULTS_DIR = PROJECT_DIR / "results" / "xchase"
    STAT_NAME = "xChase+"
else:
    RESULTS_DIR = PROJECT_DIR / "results"
    STAT_NAME = "Chase+"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

BY_SEASON_FILE = RESULTS_DIR / "chase_cost_leaderboard_by_season.csv"

OUTPUT_PAIRS = RESULTS_DIR / "chase_value_reliability.csv"
OUTPUT_FIGURE = RESULTS_DIR / "chase_value_reliability.png"


# --------------------------------------------------
# LOAD
#
# One row per qualified hitter-season, already filtered and priced
# upstream, so this script and 04_build_chase_leaderboard.py always agree on
# who qualifies.
# --------------------------------------------------

print(f"Loading the per-season {STAT_NAME} leaderboard...")

if not BY_SEASON_FILE.exists():
    raise RuntimeError(
        f"{BY_SEASON_FILE} is not there. Run "
        "04_build_chase_leaderboard.py first (with --expected-contact for "
        "xChase+)."
    )

by_season = pd.read_csv(BY_SEASON_FILE)

seasons = sorted(int(season) for season in by_season["game_year"].unique())

print(f"Qualified hitter-seasons: {len(by_season):,}")
print(f"Seasons present: {seasons}")

if len(seasons) < 2:
    raise RuntimeError(
        "Need at least two seasons to test whether anything "
        "repeats. Download another year and rerun the pipeline."
    )

print()
print("Qualified hitters by season:")
print(
    by_season
    .groupby("game_year")
    .agg(
        hitters=("batter", "size"),
        median_opportunities=("opportunities", "median"),
        spread_of_runs_saved=("runs_saved_per_600_pa", "std")
    )
    .round(2)
    .to_string()
)


# --------------------------------------------------
# CORRELATE CONSECUTIVE SEASONS
# --------------------------------------------------

def spearman_brown(reliability, multiplier):
    """
    Project a reliability to 'multiplier' times as much data per estimate.
    Non-positive values are returned unchanged.
    """

    if reliability <= 0:
        return reliability

    return (
        multiplier * reliability
        / (1 + (multiplier - 1) * reliability)
    )


def one_season_values(season, suffix):
    """batter, runs saved, chase rate and opportunities for one season."""

    return by_season[
        by_season["game_year"] == season
    ][
        [
            "batter",
            "runs_saved_per_600_pa",
            "chase_rate",
            "opportunities"
        ]
    ].rename(
        columns={
            "runs_saved_per_600_pa": f"value_{suffix}",
            "chase_rate": f"rate_{suffix}",
            "opportunities": f"opportunities_{suffix}",
        }
    )


pair_rows = []

season_pairs = list(zip(seasons[:-1], seasons[1:]))

for first_season, second_season in season_pairs:

    first = one_season_values(first_season, "first")
    second = one_season_values(second_season, "second")

    paired = first.merge(second, on="batter", how="inner")

    if len(paired) < 30:
        print()
        print(
            f"Only {len(paired)} hitters qualified in both "
            f"{first_season} and {second_season}. Skipping."
        )
        continue

    value_correlation = paired["value_first"].corr(
        paired["value_second"]
    )

    value_spearman = paired["value_first"].corr(
        paired["value_second"],
        method="spearman"
    )

    rate_correlation = paired["rate_first"].corr(
        paired["rate_second"]
    )

    pair_rows.append(
        {
            "first_season": first_season,
            "second_season": second_season,
            "hitters": len(paired),
            "value_correlation": value_correlation,
            "value_spearman": value_spearman,
            "value_projected_two_seasons": spearman_brown(
                value_correlation, 2
            ),
            "chase_rate_correlation": rate_correlation,
            "paired": paired,
        }
    )

    print()
    print("=" * 78)
    print(f"{first_season} AGAINST {second_season}")
    print("=" * 78)

    print()
    print(f"Hitters qualified in both seasons: {len(paired)}")

    print()
    print(f"Chase VALUE, year to year:  r = {value_correlation:+.3f}")
    print(f"  (Spearman rank version:   r = {value_spearman:+.3f})")
    print(f"Chase RATE,  year to year:  r = {rate_correlation:+.3f}")

    print()
    print(
        f"Projected to a two-season sample: "
        f"{spearman_brown(value_correlation, 2):+.3f}"
    )
    print(
        "One season against one season is the harshest version of "
        "this test. The projection says what two seasons of the "
        "same hitter would be expected to give."
    )


# --------------------------------------------------
# VERDICT
# --------------------------------------------------

if len(pair_rows) == 0:
    raise RuntimeError(
        "No season pair had enough hitters in common. Lower the "
        "per-season floors in 04_build_chase_leaderboard.py, or check "
        "the data."
    )

average_value_correlation = np.mean(
    [row["value_correlation"] for row in pair_rows]
)

average_rate_correlation = np.mean(
    [row["chase_rate_correlation"] for row in pair_rows]
)

print()
print("=" * 78)
print("VERDICT")
print("=" * 78)

print()
print(
    f"Average year-to-year correlation across "
    f"{len(pair_rows)} season pair(s):"
)
print(f"  chase value: {average_value_correlation:+.3f}")
print(f"  chase rate:  {average_rate_correlation:+.3f}")

print()

if average_value_correlation >= 0.5:
    print(
        "Chase value is a real, persistent hitter skill. The "
        "leaderboard describes players, not just seasons, and it "
        "is worth posting as a player evaluation tool."
    )
elif average_value_correlation >= 0.3:
    print(
        "Chase value is moderately persistent. Real, but noisy "
        "enough that a single season should not be used to judge "
        "a hitter. Report the correlation next to the leaderboard "
        "so nobody over-reads one year."
    )
elif average_value_correlation >= 0.15:
    print(
        "Weakly persistent. There is something here, but most of "
        "what a single season shows is noise and the pitches a "
        "hitter happened to see. The leaderboard is a good "
        "description of what happened, not a measurement of who "
        "anyone is. Say exactly that."
    )
else:
    print(
        "Chase value does not repeat. That is a genuine finding "
        "and it needs to be the headline, not a footnote: the "
        "cost of a hitter's chases is mostly circumstance. It "
        "would also mean chase RATE is the better tool for "
        "projecting forward even though value describes the past "
        "more accurately."
    )

print()
print(
    "Compare the two numbers directly. Chase rate is one of the "
    "stickiest things a hitter does, so it should win. How much "
    "it wins by is the real cost of the extra machinery, and that "
    "belongs in the writeup either way."
)


# --------------------------------------------------
# SCATTER PLOTS, ONE PER SEASON PAIR
# --------------------------------------------------

print()
print("Drawing the scatter plots...")

panels = len(pair_rows)

figure, axes = plt.subplots(
    1,
    panels,
    figsize=(6.5 * panels, 6),
    squeeze=False
)

for index, row in enumerate(pair_rows):

    axis = axes[0][index]

    paired = row["paired"]

    axis.axhline(0, color="#cccccc", linewidth=1, zorder=1)
    axis.axvline(0, color="#cccccc", linewidth=1, zorder=1)

    # Dot size grows with playing time (the smaller of the two seasons'
    # opportunities), so regulars stand out from part-timers.
    sizes = (
        paired[["opportunities_first", "opportunities_second"]]
        .min(axis=1)
        / 40
    )

    axis.scatter(
        paired["value_first"],
        paired["value_second"],
        s=sizes,
        alpha=0.55,
        color="#4a3b8f",
        edgecolor="none",
        zorder=3
    )

    # Least squares fit
    slope, intercept = np.polyfit(
        paired["value_first"],
        paired["value_second"],
        1
    )

    x_line = np.linspace(
        paired["value_first"].min(),
        paired["value_first"].max(),
        100
    )

    axis.plot(
        x_line,
        slope * x_line + intercept,
        color="#e8590c",
        linewidth=2.5,
        zorder=4,
        label=f"fit (r = {row['value_correlation']:+.3f})"
    )

    axis.set_xlabel(
        f"{row['first_season']} runs saved per 600 PA",
        fontsize=11
    )

    axis.set_ylabel(
        f"{row['second_season']} runs saved per 600 PA",
        fontsize=11
    )

    axis.set_title(
        f"{row['first_season']} to {row['second_season']}  "
        f"({row['hitters']} hitters)",
        fontsize=12
    )

    axis.legend(loc="upper left", frameon=False)

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)

figure.suptitle(
    f"Does a hitter's chase value ({STAT_NAME}) repeat from one season to the next?"
    if EXPECTED_CONTACT
    else "Does a hitter's chase value repeat from one season to the next?",
    fontsize=14,
    y=1.02
)

figure.tight_layout()

figure.savefig(
    OUTPUT_FIGURE,
    dpi=150,
    bbox_inches="tight"
)

print(f"Saved figure: {OUTPUT_FIGURE}")


# --------------------------------------------------
# SAVE
# --------------------------------------------------

summary = pd.DataFrame(
    [
        {
            key: value
            for key, value in row.items()
            if key != "paired"
        }
        for row in pair_rows
    ]
)

summary.to_csv(OUTPUT_PAIRS, index=False)

print()
print("Saved (overwriting the previous run):")
print(OUTPUT_PAIRS)
print(OUTPUT_FIGURE)
