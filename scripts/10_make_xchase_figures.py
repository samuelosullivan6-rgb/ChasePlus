"""
README figure comparing Chase+ with xChase+.

Kept apart from 08_make_figures.py on purpose: the main charts only need the
Chase+ run, while this one needs the xChase+ run too. Like 08_make_figures.py
it only reads finished results, nothing is recalculated.

Two charts, each in a light and a dark version:

  chase_plus_vs_xchase_plus   each qualified hitter's Chase+ against his
                              xChase+ for the latest season, with the
                              hitters the results flattered or hurt most
  reliability_chase_vs_xchase how strongly chase rate, xChase+, Chase+ and
                              luck repeat from one season to the next

The highlighted hitters are the same ones 09_build_xchase_comparison.py prints
first in its lists (sorted by luck_z, so a hitter with only a few balls in
play can't top them on noise alone).

Inputs:  results/xchase/xchase_comparison_by_season.csv
         results/xchase/xchase_reliability.csv
         results/chase_value_reliability.csv (chase rate row)
Outputs: results/xchase/figures/chase_plus_vs_xchase_plus.png
         results/xchase/figures/chase_plus_vs_xchase_plus_dark.png
         results/xchase/figures/reliability_chase_vs_xchase.png
         results/xchase/figures/reliability_chase_vs_xchase_dark.png
"""

from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt


# --------------------------------------------------
# FILE LOCATIONS
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

RESULTS_DIR = PROJECT_DIR / "results"
# With the other xChase+ charts, not the Chase+ ones in results/figures/.
FIGURE_DIR = RESULTS_DIR / "xchase" / "figures"

COMPARISON_FILE = RESULTS_DIR / "xchase" / "xchase_comparison_by_season.csv"
X_RELIABILITY_FILE = RESULTS_DIR / "xchase" / "xchase_reliability.csv"
CHASE_RELIABILITY_FILE = RESULTS_DIR / "chase_value_reliability.csv"

# How many hitters are highlighted on each side of the line.
HIGHLIGHT_COUNT = 5


# --------------------------------------------------
# COLORS AND STYLE
#
# Same colors and look as 08_make_figures.py (copied, not imported, because
# importing 08_make_figures.py would redraw all of its charts).
# --------------------------------------------------

THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "ink": "#0b0b0b",
        "ink_secondary": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        "context_dots": "#c3c2b7",
        "hurt": "#2a78d6",       # blue: xChase+ above Chase+
        "flattered": "#eb6834",  # orange: Chase+ above xChase+
        "pair_colors": ["#9ec5f4", "#184f95"],  # season pairs, older to newer
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#ffffff",
        "ink_secondary": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "context_dots": "#52514e",
        "hurt": "#3987e5",
        "flattered": "#d95926",
        "pair_colors": ["#6da7ec", "#cde2fb"],
    },
}

FONT_FAMILY = ["Helvetica Neue", "Helvetica", "Arial", "Liberation Sans", "DejaVu Sans"]


def apply_style(theme):
    """Matplotlib defaults for one theme: hairline axes, recessive grid."""

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": FONT_FAMILY,
        "font.size": 10,
        "figure.facecolor": theme["surface"],
        "axes.facecolor": theme["surface"],
        "savefig.facecolor": theme["surface"],
        "axes.edgecolor": theme["axis"],
        "axes.linewidth": 0.8,
        "axes.labelcolor": theme["ink_secondary"],
        "axes.titlecolor": theme["ink"],
        "text.color": theme["ink"],
        "xtick.color": theme["muted"],
        "ytick.color": theme["muted"],
        "xtick.labelcolor": theme["ink_secondary"],
        "ytick.labelcolor": theme["ink_secondary"],
        "grid.color": theme["grid"],
        "grid.linewidth": 0.8,
        "legend.frameon": False,
        "legend.labelcolor": theme["ink_secondary"],
    })


def clean_axes(axis):
    """Remove the box and the tick marks."""

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_visible(False)
    axis.tick_params(length=0)


def add_titles(figure, title, subtitle, theme, subtitle_y=0.955):
    """
    Takeaway title plus a plain-language subtitle. subtitle_y is lower for
    a shorter figure, so the subtitle doesn't run into the title.
    """

    figure.text(0.01, 0.985, title, ha="left", va="top",
                fontsize=14, fontweight="bold", color=theme["ink"])
    figure.text(0.01, subtitle_y, subtitle, ha="left", va="top",
                fontsize=9.5, color=theme["ink_secondary"])


def save(figure, name, mode):
    suffix = "" if mode == "light" else "_dark"
    path = FIGURE_DIR / f"{name}{suffix}.png"
    figure.savefig(path, dpi=200)
    plt.close(figure)
    return path


def stacked_label_heights(estimates, order_keys, gap):
    """
    Heights for a column of names, evenly spaced `gap` apart and centered
    on the dots' average height. The names are stacked in the order of
    order_keys (lowest at the bottom), which keeps the leader lines from
    crossing. (Same idea as in 08_make_figures.py.)
    """

    order = np.argsort(order_keys)
    count = len(estimates)
    center = np.mean(estimates)
    heights = np.empty(count)

    for slot, index in enumerate(order):
        heights[index] = center + (slot - (count - 1) / 2) * gap

    return heights


# --------------------------------------------------
# LOAD
# --------------------------------------------------

if not COMPARISON_FILE.exists():
    raise RuntimeError(
        f"{COMPARISON_FILE.relative_to(PROJECT_DIR)} is not there. Run "
        "04_build_chase_leaderboard.py --expected-contact and "
        "09_build_xchase_comparison.py first."
    )

comparison = pd.read_csv(COMPARISON_FILE)

seasons = sorted(int(season) for season in comparison["game_year"].unique())
latest_season = seasons[-1]

latest = comparison[comparison["game_year"] == latest_season]

# One line per season for the subtitle: how closely the two stats agree.
season_summaries = []

for season in seasons:

    one_season = comparison[comparison["game_year"] == season]

    season_r = one_season["chase_plus"].corr(one_season["xchase_plus"])
    luck_spread = one_season["luck"].std()

    season_summaries.append(f"{season}: r = {season_r:.2f}, luck SD {luck_spread:.1f}")

flattered_most = latest.sort_values("luck_z", ascending=False).head(HIGHLIGHT_COUNT)
hurt_most = latest.sort_values("luck_z", ascending=True).head(HIGHLIGHT_COUNT)

FIGURE_DIR.mkdir(parents=True, exist_ok=True)

written = []


# --------------------------------------------------
# THE CHART
#
# x = Chase+ (what happened), y = xChase+ (how the chased balls in play
# were hit). On the diagonal the two agree. Below it the results flattered
# the hitter (Chase+ higher), above it they hurt him.
# --------------------------------------------------

for mode, theme in THEMES.items():

    apply_style(theme)

    figure, axis = plt.subplots(figsize=(7.6, 8.4))
    figure.subplots_adjust(left=0.11, right=0.97, top=0.83, bottom=0.07)

    axis.grid(zorder=0)

    low = min(latest["chase_plus"].min(), latest["xchase_plus"].min()) - 6
    high = max(latest["chase_plus"].max(), latest["xchase_plus"].max()) + 6

    # where the two stats agree exactly
    axis.plot([low, high], [low, high], color=theme["ink_secondary"],
              linewidth=1, zorder=1)

    # everyone else, as quiet context
    axis.scatter(latest["chase_plus"], latest["xchase_plus"], s=16,
                 color=theme["context_dots"], edgecolor="none", zorder=2)

    # Flattered hitters sit below the diagonal, so their names go in a
    # column to the right. Hurt hitters sit above it, names to the left.
    groups = [
        (flattered_most, theme["flattered"], "right"),
        (hurt_most, theme["hurt"], "left"),
    ]

    for group, color, side in groups:

        x_values = group["chase_plus"].to_numpy()
        y_values = group["xchase_plus"].to_numpy()

        # thin line from the diagonal to the dot = the luck gap
        for x_value, y_value in zip(x_values, y_values):
            axis.plot([x_value, x_value], [x_value, y_value], color=color,
                      alpha=0.45, linewidth=1.2, zorder=3)

        axis.scatter(x_values, y_values, s=58, color=color,
                     edgecolor=theme["surface"], linewidth=1.6, zorder=5)

        if side == "right":
            column_x = x_values.max() + 7
            alignment = "left"
            nudge = 0.8
        else:
            column_x = x_values.min() - 7
            alignment = "right"
            nudge = -0.8

        # Order the names mostly by height, but lean toward the side the
        # names are on. Two dots at about the same height would otherwise
        # have the inner dot's leader line run straight through the outer
        # dot, and it would look like the wrong name.
        if side == "right":
            order_keys = y_values + 0.5 * x_values
        else:
            order_keys = y_values - 0.5 * x_values

        label_heights = stacked_label_heights(y_values, order_keys, gap=5.5)

        for x_value, y_value, height, (_, row) in zip(
            x_values, y_values, label_heights, group.iterrows()
        ):
            axis.plot([x_value, column_x], [y_value, height],
                      color=theme["muted"], linewidth=0.6, zorder=4)

            axis.text(column_x + nudge, height,
                      f"{row['player']}  {row['luck']:+.0f}",
                      ha=alignment, va="center", fontsize=8.5,
                      color=theme["ink"])

    axis.set_xlim(low, high)
    axis.set_ylim(low, high)
    axis.set_aspect("equal")

    axis.set_xlabel("Chase+  (actual results)")
    axis.set_ylabel("xChase+  (balls in play priced from xwOBA)")
    clean_axes(axis)

    add_titles(
        figure,
        f"Chase+ and xChase+ mostly agree ({latest_season})",
        "Each dot is a qualified hitter. On the line the two stats are equal.\n"
        "The number after a name is Chase+ minus xChase+ (luck, in Chase+ points).\n"
        "How closely they agree, by season:  " + "  ·  ".join(season_summaries),
        theme,
    )

    handles = [
        plt.Line2D([], [], marker="o", linestyle="none", markersize=7,
                   color=theme["flattered"], markeredgecolor=theme["surface"],
                   label="Results flattered him most"),
        plt.Line2D([], [], marker="o", linestyle="none", markersize=7,
                   color=theme["hurt"], markeredgecolor=theme["surface"],
                   label="Results hurt him most"),
        plt.Line2D([], [], color=theme["ink_secondary"], linewidth=1,
                   label="Chase+ = xChase+"),
    ]
    figure.legend(handles=handles, loc="upper left", ncol=3,
                  bbox_to_anchor=(0.005, 0.895), fontsize=8.5,
                  handlelength=1.6, columnspacing=1.4)

    written.append(save(figure, "chase_plus_vs_xchase_plus", mode))



# --------------------------------------------------
# CHART 2: WHAT REPEATS FROM ONE SEASON TO THE NEXT
#
# Year-to-year correlation for hitters qualified in both seasons (unshrunk
# values, as in 06_build_chase_reliability.py and 09_build_xchase_comparison.py).
# One row per measure, one dot per pair of seasons. Pale bar = 95%
# interval for the correlation (Fisher z).
# --------------------------------------------------

def correlation_interval(r, n):
    """95% interval for a Pearson correlation, via Fisher's z."""

    z = np.arctanh(r)
    half_width = 1.96 / np.sqrt(n - 3)
    return np.tanh(z - half_width), np.tanh(z + half_width)


if X_RELIABILITY_FILE.exists() and CHASE_RELIABILITY_FILE.exists():

    x_reliability = pd.read_csv(X_RELIABILITY_FILE)
    chase_reliability = pd.read_csv(CHASE_RELIABILITY_FILE)

    reliability = x_reliability.merge(
        chase_reliability[["first_season", "second_season", "hitters",
                           "value_correlation", "chase_rate_correlation"]],
        on=["first_season", "second_season"],
        how="inner"
    )

    # The two scripts pair the same hitters, so they have to agree on the
    # Chase+ correlation (Chase+ is runs saved on a per-season scale).
    if not np.allclose(reliability["chase_plus_r"],
                       reliability["value_correlation"], rtol=0, atol=1e-9):
        raise RuntimeError(
            "xchase_reliability.csv and chase_value_reliability.csv disagree "
            "on the Chase+ correlation. Rerun both scripts."
        )

    # top to bottom
    measures = [
        ("chase_rate_correlation", "Chase rate"),
        ("xchase_plus_r", "xChase+"),
        ("chase_plus_r", "Chase+"),
        ("luck_r", "Luck (Chase+ minus xChase+)"),
    ]

    pair_labels = [
        f"{int(row.first_season)} to {int(row.second_season)}"
        for row in reliability.itertuples()
    ]

    for mode, theme in THEMES.items():

        apply_style(theme)

        figure, axis = plt.subplots(figsize=(7.6, 5.2))
        figure.subplots_adjust(left=0.28, right=0.97, top=0.74, bottom=0.12)

        axis.grid(axis="x", zorder=0)
        axis.axvline(0, color=theme["ink_secondary"], linewidth=1, zorder=1)

        pair_count = len(reliability)
        offsets = np.linspace(-0.14, 0.14, pair_count) if pair_count > 1 else [0.0]

        for row_number, (column, label) in enumerate(measures):

            for pair_number, (_, pair) in enumerate(reliability.iterrows()):

                r = pair[column]
                low, high = correlation_interval(r, pair["paired_hitters"])
                y_position = row_number + offsets[pair_number]
                color = theme["pair_colors"][pair_number % len(theme["pair_colors"])]

                # uncertainty: pale bar behind the dot
                axis.plot([low, high], [y_position, y_position], color=color,
                          alpha=0.45, linewidth=6, solid_capstyle="round",
                          zorder=2)

                # estimate: solid dot
                axis.scatter(r, y_position, s=52, color=color,
                             edgecolor=theme["surface"], linewidth=1.4,
                             zorder=3)

                axis.text(high + 0.025, y_position, f"{r:.2f}", ha="left",
                          va="center", fontsize=8.5, color=theme["ink"])

        axis.set_yticks(range(len(measures)), [label for _, label in measures])
        axis.set_ylim(len(measures) - 0.5, -0.5)
        axis.set_xlim(-0.4, 1.05)
        axis.set_xlabel("Correlation with the same hitters' next season")
        clean_axes(axis)

        add_titles(
            figure,
            "xChase+ repeats more than Chase+, and luck doesn't repeat",
            "Hitters qualified in both seasons, values before shrinkage.\n"
            "Pale bars: 95% interval for each correlation.",
            theme,
            subtitle_y=0.925,
        )

        handles = [
            plt.Line2D([], [], marker="o", linestyle="none", markersize=7,
                       color=theme["pair_colors"][index % len(theme["pair_colors"])],
                       markeredgecolor=theme["surface"],
                       label=f"{label} ({int(reliability['paired_hitters'].iloc[index])} hitters)")
            for index, label in enumerate(pair_labels)
        ]
        figure.legend(handles=handles, loc="upper left", ncol=len(handles),
                      bbox_to_anchor=(0.005, 0.845), fontsize=8.5,
                      handlelength=1.4, columnspacing=1.4)

        written.append(save(figure, "reliability_chase_vs_xchase", mode))

else:

    print(
        "Skipping the reliability chart: it needs xchase_reliability.csv "
        "and chase_value_reliability.csv (run 09_build_xchase_comparison.py and "
        "06_build_chase_reliability.py)."
    )


print(f"Saved {len(written)} figures to {FIGURE_DIR.relative_to(PROJECT_DIR)}/:")

for path in written:
    print(f"  {path.name}")
