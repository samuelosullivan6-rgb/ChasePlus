"""
README figures and tables for the chase leaderboard.

Reads the finished results (nothing is recalculated, so the figures always
match the saved leaderboards) and writes four charts, each in a light and a
dark version, to results/figures/:

  chase_cost_by_count        average cost of one chase in each count
  leaderboard_by_season      top 5 and bottom 5 Chase+ per season
  chase_plus_vs_chase_rate   where Chase+ and chase rate disagree most
  reliability                does chase value carry over between seasons?

It also prints the per-season top 5 / bottom 5 as markdown tables, ready to
paste into README.md.

How uncertainty is drawn, in every chart:
  - the estimate itself is a solid mark (a dot, a line, a number);
  - its uncertainty is a pale, translucent band or bar behind it, and
    printed values show it as a smaller, lighter "±" figure;
  - reference values (league average = 100, zero) are thin gray lines.

Inputs:  results/chase_cost_leaderboard_by_season.csv
         results/chase_value_reliability.csv (to cross-check correlations)
         data/cleaned/chase_costs_by_pitch.parquet (count chart only; that
         chart is skipped if the file is missing)
Outputs: results/figures/*.png

With --expected-contact it draws the same charts and tables for xChase+:
inputs come from results/xchase/ and xchase_costs_by_pitch.parquet, the
charts go to results/xchase/figures/, and the labels say xChase+.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import t as t_distribution

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, to_rgb


# --------------------------------------------------
# FILE LOCATIONS
# --------------------------------------------------

# Paths are anchored to the project folder (the parent of scripts/), not
# to the directory the script is run from.
PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

parser = argparse.ArgumentParser(
    description="README charts and tables for Chase+ (or xChase+)."
)
parser.add_argument(
    "--expected-contact",
    action="store_true",
    help="draw the xChase+ versions from results/xchase/ into "
         "results/xchase/figures/",
)
arguments = parser.parse_args()

EXPECTED_CONTACT = arguments.expected_contact

if EXPECTED_CONTACT:
    RESULTS_DIR = PROJECT_DIR / "results" / "xchase"
    PITCH_COST_FILE = PROJECT_DIR / "data" / "cleaned" / "xchase_costs_by_pitch.parquet"
    STAT_NAME = "xChase+"
else:
    RESULTS_DIR = PROJECT_DIR / "results"
    PITCH_COST_FILE = PROJECT_DIR / "data" / "cleaned" / "chase_costs_by_pitch.parquet"
    STAT_NAME = "Chase+"

FIGURE_DIR = RESULTS_DIR / "figures"

BY_SEASON_FILE = RESULTS_DIR / "chase_cost_leaderboard_by_season.csv"
RELIABILITY_FILE = RESULTS_DIR / "chase_value_reliability.csv"

TOP_AND_BOTTOM = 5


# --------------------------------------------------
# COLORS AND STYLE
#
# Light and dark versions use the same roles. The README picks the dark
# version automatically for readers using GitHub's dark theme.
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
        "better": "#2a78d6",   # blue: above average / ranked better by Chase+
        "worse": "#e34948",    # red: below average
        "other": "#eb6834",    # orange: ranked better by chase rate
        "ramp": ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5",
                 "#256abf", "#184f95", "#0d366b"],
        "confidence_band_alpha": 0.18,
        "band_alpha": 0.28,
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#ffffff",
        "ink_secondary": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "context_dots": "#52514e",
        "better": "#3987e5",
        "worse": "#e66767",
        "other": "#d95926",
        "ramp": ["#104281", "#184f95", "#1c5cab", "#256abf",
                 "#3987e5", "#6da7ec", "#9ec5f4"],
        "confidence_band_alpha": 0.32,
        "band_alpha": 0.45,
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


def clean_axes(axis, keep_left=False):
    """Remove the box; keep only a bottom (and optionally left) hairline."""

    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.spines["left"].set_visible(keep_left)
    axis.tick_params(length=0)


def add_titles(figure, title, subtitle, theme):
    """Takeaway title plus one line of plain-language subtitle."""

    figure.text(0.01, 0.985, title, ha="left", va="top",
                fontsize=14, fontweight="bold", color=theme["ink"])
    figure.text(0.01, 0.945, subtitle, ha="left", va="top",
                fontsize=9.5, color=theme["ink_secondary"])


def save(figure, name, mode):
    suffix = "" if mode == "light" else "_dark"
    path = FIGURE_DIR / f"{name}{suffix}.png"
    figure.savefig(path, dpi=200)
    plt.close(figure)
    return path


def player_labels(table):
    """Player names, or the batter ID where no name was found."""

    batter_ids = table["batter"].astype(str)

    if "player" not in table.columns:
        return batter_ids

    return table["player"].fillna(batter_ids)


def readable_ink(hex_color):
    """White or ink text, whichever reads better on a filled cell."""

    red, green, blue = to_rgb(hex_color)
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue

    if luminance > 0.5:
        return "#0b0b0b"

    return "#ffffff"


# --------------------------------------------------
# LOAD
# --------------------------------------------------

if not BY_SEASON_FILE.exists():
    raise RuntimeError(
        f"{BY_SEASON_FILE} is not there. Run 04_build_chase_leaderboard.py first"
        + (" with --expected-contact." if EXPECTED_CONTACT else ".")
    )

by_season = pd.read_csv(BY_SEASON_FILE)

# The xChase+ run saves its columns as xchase_plus, ...; the charts below
# use the chase_plus names for either run.
if EXPECTED_CONTACT:
    by_season = by_season.rename(
        columns=lambda name: name.replace("xchase_plus", "chase_plus")
    )

by_season["label"] = player_labels(by_season)

# For xChase+ the leaders chart also marks each hitter's Chase+ (what
# actually happened), so the gap between the two is visible.
actual_chase_plus = {}

if EXPECTED_CONTACT:

    chase_plus_file = PROJECT_DIR / "results" / "chase_cost_leaderboard_by_season.csv"

    if chase_plus_file.exists():
        actual = pd.read_csv(chase_plus_file)
        for _, row in actual.iterrows():
            actual_chase_plus[(row["batter"], row["game_year"])] = row["chase_plus"]
    else:
        print(
            "No Chase+ leaderboard in results/, so the leaders chart will "
            "not mark Chase+. Run 04_build_chase_leaderboard.py to add it."
        )

seasons = sorted(int(season) for season in by_season["game_year"].unique())
latest_season = seasons[-1]

FIGURE_DIR.mkdir(parents=True, exist_ok=True)

written = []


# --------------------------------------------------
# CHART 1: WHAT ONE CHASE COSTS, BY COUNT
#
# Average chase_cost over every chase in each count, all seasons combined
# (the same pooling as the leaderboard script's cost-by-count table).
# Standard error = standard deviation / sqrt(number of chases).
# --------------------------------------------------

if PITCH_COST_FILE.exists():

    pitch_costs = pd.read_parquet(
        PITCH_COST_FILE,
        columns=["balls", "strikes", "is_chase", "chase_cost"]
    )

    chases = pitch_costs[pitch_costs["is_chase"] == 1]

    cost_by_count = (
        chases
        .groupby(["balls", "strikes"])["chase_cost"]
        .agg(["mean", "std", "size"])
        .reset_index()
    )

    cost_by_count["standard_error"] = (
        cost_by_count["std"] / np.sqrt(cost_by_count["size"])
    )

    cheapest = cost_by_count.loc[cost_by_count["mean"].idxmin()]
    dearest = cost_by_count.loc[cost_by_count["mean"].idxmax()]
    spread = dearest["mean"] / cheapest["mean"]

    for mode, theme in THEMES.items():

        apply_style(theme)

        figure, axis = plt.subplots(figsize=(6.4, 5.6))
        figure.subplots_adjust(left=0.13, right=0.97, top=0.80, bottom=0.03)

        grid = (
            cost_by_count
            .pivot(index="balls", columns="strikes", values="mean")
            .sort_index()
        )
        errors = (
            cost_by_count
            .pivot(index="balls", columns="strikes", values="standard_error")
            .sort_index()
        )

        colormap = LinearSegmentedColormap.from_list("ramp", theme["ramp"])
        low, high = grid.values.min(), grid.values.max()

        for row, balls in enumerate(grid.index):
            for column, strikes in enumerate(grid.columns):

                value = grid.loc[balls, strikes]
                fill = colormap((value - low) / (high - low))
                fill_hex = matplotlib.colors.to_hex(fill)

                # cells separated by a surface-colored gap
                axis.add_patch(plt.Rectangle(
                    (column + 0.03, row + 0.03), 0.94, 0.94,
                    facecolor=fill_hex, edgecolor="none"
                ))

                text_color = readable_ink(fill_hex)

                # the estimate: large and bold
                axis.text(column + 0.5, row + 0.44, f"{value:.3f}",
                          ha="center", va="center", fontsize=13,
                          fontweight="bold", color=text_color)

                # its uncertainty: small, lighter, marked with ±
                axis.text(column + 0.5, row + 0.68,
                          f"± {errors.loc[balls, strikes]:.3f}",
                          ha="center", va="center", fontsize=8,
                          color=text_color, alpha=0.75)

        axis.set_xlim(0, 3)
        axis.set_ylim(4, 0)
        axis.set_xticks([0.5, 1.5, 2.5], ["0 strikes", "1 strike", "2 strikes"])
        axis.set_yticks([0.5, 1.5, 2.5, 3.5],
                        ["0 balls", "1 ball", "2 balls", "3 balls"])
        axis.xaxis.tick_top()
        clean_axes(axis)
        axis.spines["bottom"].set_visible(False)

        add_titles(
            figure,
            f"A chase on {int(dearest['balls'])}-{int(dearest['strikes'])} "
            f"costs {spread:.1f}× one on "
            f"{int(cheapest['balls'])}-{int(cheapest['strikes'])}",
            "Average runs lost per chase, by count (2024-2026 combined)"
            + (", balls in play priced from xwOBA" if EXPECTED_CONTACT else "")
            + ".\nSmall figures: ±1 standard error of that average.",
            theme,
        )

        written.append(save(figure, "chase_cost_by_count", mode))

else:

    print(
        f"Skipping the count chart: {PITCH_COST_FILE.name} is not in "
        "data/cleaned/ (run 04_build_chase_leaderboard.py to create it)."
    )


# --------------------------------------------------
# CHART 2: TOP 5 AND BOTTOM 5 CHASE+, EACH SEASON
#
# Dot = Chase+ (the shrunk estimate). Pale bar = ±1 posterior SD, the
# uncertainty left after shrinkage (chase_plus_posterior_sd). Gray line =
# league average, 100.
# --------------------------------------------------

def top_and_bottom(season):
    """
    Best 5 and worst 5 in leaderboard order (runs_saved_shrunk, best
    first), so the very worst hitter is the last row.
    """

    one_season = by_season[by_season["game_year"] == season].sort_values(
        "runs_saved_shrunk", ascending=False
    )

    return (
        one_season.head(TOP_AND_BOTTOM),
        one_season.tail(TOP_AND_BOTTOM),
        len(one_season),
    )


for mode, theme in THEMES.items():

    apply_style(theme)

    figure, axes = plt.subplots(
        len(seasons), 1,
        figsize=(7.6, 3.05 * len(seasons) + 1.0),
        sharex=True
    )
    figure.subplots_adjust(left=0.22, right=0.96, top=0.875, bottom=0.05,
                           hspace=0.36)

    axes = np.atleast_1d(axes)

    x_low = 40
    x_high = 185

    for axis, season in zip(axes, seasons):

        best, worst, qualified = top_and_bottom(season)

        rows = pd.concat([best, worst])
        colors = [theme["better"]] * len(best) + [theme["worse"]] * len(worst)

        # a small gap between the top 5 and the bottom 5
        positions = list(range(len(best))) + [
            len(best) + 0.6 + index for index in range(len(worst))
        ]

        axis.axvline(100, color=theme["ink_secondary"], linewidth=1, zorder=1)
        axis.grid(axis="x", zorder=0)

        for position, (_, row), color in zip(positions, rows.iterrows(), colors):

            estimate = row["chase_plus"]
            spread = row["chase_plus_posterior_sd"]

            # uncertainty: pale, thick, behind the dot
            axis.plot([estimate - spread, estimate + spread],
                      [position, position], color=color, alpha=theme["band_alpha"],
                      linewidth=7, solid_capstyle="round", zorder=2)

            # estimate: solid dot with a surface ring
            axis.scatter(estimate, position, s=58, color=color,
                         edgecolor=theme["surface"], linewidth=1.6, zorder=3)

            # xChase+ only: the hitter's Chase+ as a hollow ring on the
            # same row, joined to the dot by a thin line
            label_start = estimate + spread + 3.5
            key = (row["batter"], row["game_year"])

            if key in actual_chase_plus:
                actual_value = actual_chase_plus[key]
                # drawn under the xChase+ dot, so the dot stays visible
                # when the two are close
                axis.plot([estimate, actual_value], [position, position],
                          color=theme["ink_secondary"], linewidth=0.8, zorder=2.4)
                axis.scatter(actual_value, position, s=46,
                             facecolor=theme["surface"],
                             edgecolor=theme["ink_secondary"], linewidth=1.3,
                             zorder=2.5)
                label_start = max(label_start, actual_value + 3.5)

            # value label past the end of the band
            axis.text(label_start, position, f"{estimate:.0f}",
                      ha="left", va="center", fontsize=9,
                      fontweight="bold", color=theme["ink"])
            label_width = 2.1 * len(f"{estimate:.0f}")
            axis.text(label_start + label_width + 1.2, position,
                      f"±{spread:.0f}", ha="left", va="center",
                      fontsize=7.5, color=theme["muted"])

        axis.set_yticks(positions, rows["label"])
        axis.set_ylim(max(positions) + 0.7, -0.7)
        axis.set_xlim(x_low, x_high)
        clean_axes(axis)

        partial = " (season in progress)" if season == latest_season else ""
        axis.set_title(
            f"{season}{partial}  ·  {qualified} qualified hitters",
            loc="left", fontsize=10.5, fontweight="bold", pad=6
        )

    axes[-1].set_xlabel(f"{STAT_NAME}  (100 = league average; higher = fewer runs lost to chasing)")

    add_titles(
        figure,
        f"{STAT_NAME} leaders and trailers, season by season",
        "Top 5 (blue) and bottom 5 (red) qualified hitters.",
        theme,
    )

    # legend: estimate, uncertainty, reference
    handles = [
        plt.Line2D([], [], marker="o", linestyle="none", markersize=7,
                   color=theme["ink_secondary"],
                   markeredgecolor=theme["surface"], label=f"{STAT_NAME} estimate"),
        plt.Line2D([], [], color=theme["ink_secondary"], alpha=min(theme["band_alpha"] + 0.1, 1),
                   linewidth=7, solid_capstyle="round",
                   label="±1 SD uncertainty (after shrinkage)"),
        plt.Line2D([], [], color=theme["ink_secondary"], linewidth=1,
                   label="League average (100)"),
    ]

    if actual_chase_plus:
        handles.append(
            plt.Line2D([], [], marker="o", linestyle="none", markersize=6.5,
                       markerfacecolor=theme["surface"],
                       markeredgecolor=theme["ink_secondary"],
                       markeredgewidth=1.3, label="Chase+ (actual results)")
        )

    figure.legend(handles=handles, loc="upper left",
                  ncol=4 if actual_chase_plus else 3,
                  bbox_to_anchor=(0.005, 0.925), fontsize=8.5,
                  handlelength=1.6, columnspacing=1.4)

    written.append(save(figure, "leaderboard_by_season", mode))


# --------------------------------------------------
# CHART 3: CHASE+ VS CHASE RATE, LATEST SEASON
#
# Highlighted: the five largest rank disagreements each way, chosen exactly
# like the leaderboard script's comparison tables (sort by rank_gap).
# Gray line: least-squares fit, the Chase+ typical for each chase rate.
# --------------------------------------------------

latest = by_season[by_season["game_year"] == latest_season]

ranked_better_by_chase_plus = (
    latest.sort_values("rank_gap", ascending=False).head(TOP_AND_BOTTOM)
)
ranked_better_by_chase_rate = (
    latest.sort_values("rank_gap", ascending=True).head(TOP_AND_BOTTOM)
)


def stacked_label_heights(estimates, gap):
    """
    Heights for a column of names: same top-to-bottom order as the dots,
    evenly spaced `gap` apart, centered on the dots' average height. Keeping
    the order means the leader lines never cross each other.
    """

    order = np.argsort(estimates)
    count = len(estimates)
    center = np.mean(estimates)
    heights = np.empty(count)

    for slot, index in enumerate(order):
        heights[index] = center + (slot - (count - 1) / 2) * gap

    return heights


for mode, theme in THEMES.items():

    apply_style(theme)

    figure, axis = plt.subplots(figsize=(7.6, 6.2))
    figure.subplots_adjust(left=0.10, right=0.97, top=0.78, bottom=0.10)

    axis.grid(zorder=0)
    axis.axhline(100, color=theme["ink_secondary"], linewidth=1, zorder=1)

    # everyone else, as quiet context
    axis.scatter(latest["chase_rate"], latest["chase_plus"], s=16,
                 color=theme["context_dots"], edgecolor="none", zorder=2)

    # typical Chase+ for a given chase rate
    slope, intercept = np.polyfit(latest["chase_rate"], latest["chase_plus"], 1)
    x_line = np.linspace(latest["chase_rate"].min(), latest["chase_rate"].max(), 50)
    axis.plot(x_line, slope * x_line + intercept, color=theme["muted"],
              linewidth=1.5, zorder=2)

    # Names sit in a column beside each group (right of the blue group, left
    # of the orange one), joined to their dots by thin leader lines.
    groups = [
        (ranked_better_by_chase_plus, theme["better"], "right"),
        (ranked_better_by_chase_rate, theme["other"], "left"),
    ]

    for group, color, side in groups:

        estimates = group["chase_plus"].to_numpy()
        spreads = group["chase_plus_posterior_sd"].to_numpy()
        rates = group["chase_rate"].to_numpy()

        # uncertainty: pale vertical bars
        for rate, estimate, spread in zip(rates, estimates, spreads):
            axis.plot([rate, rate], [estimate - spread, estimate + spread],
                      color=color, alpha=theme["band_alpha"], linewidth=6,
                      solid_capstyle="round", zorder=3)

        # estimate: solid dots
        axis.scatter(rates, estimates, s=58, color=color,
                     edgecolor=theme["surface"], linewidth=1.6, zorder=5)

        if side == "right":
            column_x = rates.max() + 2.2
            alignment = "left"
        else:
            column_x = rates.min() - 2.2
            alignment = "right"

        label_heights = stacked_label_heights(estimates, gap=4.2)

        for rate, estimate, height, name in zip(rates, estimates, label_heights,
                                                group["label"]):
            axis.plot([rate, column_x], [estimate, height],
                      color=theme["muted"], linewidth=0.6, zorder=4)
            nudge = 0.25 if side == "right" else -0.25
            axis.text(column_x + nudge, height, name, ha=alignment,
                      va="center", fontsize=8.5, color=theme["ink"])

    axis.set_xlabel("Chase rate (% of out-of-zone pitches swung at)")
    axis.set_ylabel(STAT_NAME)
    clean_axes(axis, keep_left=False)

    add_titles(
        figure,
        f"Where chase rate and {STAT_NAME} disagree most ({latest_season})",
        "Each dot is a qualified hitter. Highlighted: the five biggest gaps between\n"
        f"chase-rate rank and {STAT_NAME} rank, in each direction.",
        theme,
    )

    handles = [
        plt.Line2D([], [], marker="o", linestyle="none", markersize=7,
                   color=theme["better"], markeredgecolor=theme["surface"],
                   label=f"Ranked better by {STAT_NAME}"),
        plt.Line2D([], [], marker="o", linestyle="none", markersize=7,
                   color=theme["other"], markeredgecolor=theme["surface"],
                   label="Ranked better by chase rate"),
        plt.Line2D([], [], color=theme["ink_secondary"], alpha=min(theme["band_alpha"] + 0.1, 1),
                   linewidth=6, solid_capstyle="round",
                   label="±1 SD uncertainty (after shrinkage)"),
        plt.Line2D([], [], color=theme["muted"], linewidth=1.5,
                   label=f"Typical {STAT_NAME} for that chase rate"),
        plt.Line2D([], [], color=theme["ink_secondary"], linewidth=1,
                   label="League average (100)"),
    ]
    figure.legend(handles=handles, loc="upper left", ncol=3,
                  bbox_to_anchor=(0.005, 0.895), fontsize=8.2,
                  handlelength=1.6, columnspacing=1.2)

    written.append(save(figure, "chase_plus_vs_chase_rate", mode))


# --------------------------------------------------
# CHART 4: DOES CHASE VALUE REPEAT?
#
# The same pairing as 06_build_chase_reliability.py: unshrunk runs saved per
# 600 PA for hitters qualified in both seasons. Solid line = least-squares
# fit; pale band = its 95% confidence band. r is shown with a 95% interval
# (Fisher z).
# --------------------------------------------------

def paired_seasons(first_season, second_season):
    columns = ["batter", "runs_saved_per_600_pa", "chase_rate"]
    first = by_season[by_season["game_year"] == first_season][columns]
    second = by_season[by_season["game_year"] == second_season][columns]
    return first.merge(second, on="batter", suffixes=("_first", "_second"))


def correlation_interval(r, n):
    """95% interval for a Pearson correlation, via Fisher's z."""

    z = np.arctanh(r)
    half_width = 1.96 / np.sqrt(n - 3)
    return np.tanh(z - half_width), np.tanh(z + half_width)


def fit_with_band(x, y, x_grid):
    """Least-squares line and its 95% confidence band at x_grid."""

    n = len(x)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    residual_sd = np.sqrt(np.sum((y - fitted) ** 2) / (n - 2))
    x_mean = x.mean()
    spread_x = np.sum((x - x_mean) ** 2)

    line = intercept + slope * x_grid
    half_width = (
        t_distribution.ppf(0.975, n - 2)
        * residual_sd
        * np.sqrt(1 / n + (x_grid - x_mean) ** 2 / spread_x)
    )

    return line, line - half_width, line + half_width


season_pairs = list(zip(seasons[:-1], seasons[1:]))

recorded = (
    pd.read_csv(RELIABILITY_FILE).set_index(["first_season", "second_season"])
    if RELIABILITY_FILE.exists()
    else None
)

for mode, theme in THEMES.items():

    apply_style(theme)

    figure, axes = plt.subplots(
        1, len(season_pairs),
        figsize=(4.0 * len(season_pairs) + 0.4, 4.9),
        sharex=True, sharey=True, squeeze=False
    )
    figure.subplots_adjust(left=0.09, right=0.98, top=0.77, bottom=0.13,
                           wspace=0.12)

    for axis, (first_season, second_season) in zip(axes[0], season_pairs):

        paired = paired_seasons(first_season, second_season)

        x = paired["runs_saved_per_600_pa_first"].to_numpy()
        y = paired["runs_saved_per_600_pa_second"].to_numpy()

        value_r = np.corrcoef(x, y)[0, 1]
        rate_r = np.corrcoef(paired["chase_rate_first"],
                             paired["chase_rate_second"])[0, 1]

        # the figure must agree with what 06_build_chase_reliability.py saved
        if recorded is not None and (first_season, second_season) in recorded.index:
            saved_r = recorded.loc[(first_season, second_season), "value_correlation"]
            if abs(saved_r - value_r) > 1e-9:
                print(
                    f"WARNING: {first_season}-{second_season} correlation "
                    f"{value_r:.4f} differs from chase_value_reliability.csv "
                    f"({saved_r:.4f}). Rerun 06_build_chase_reliability.py."
                )

        low_r, high_r = correlation_interval(value_r, len(paired))

        axis.axhline(0, color=theme["axis"], linewidth=0.8, zorder=1)
        axis.axvline(0, color=theme["axis"], linewidth=0.8, zorder=1)

        axis.scatter(x, y, s=14, color=theme["better"], alpha=0.45,
                     edgecolor="none", zorder=2)

        x_grid = np.linspace(x.min(), x.max(), 100)
        line, band_low, band_high = fit_with_band(x, y, x_grid)

        # uncertainty: pale band behind the line
        axis.fill_between(x_grid, band_low, band_high, color=theme["better"],
                          alpha=theme["confidence_band_alpha"], linewidth=0,
                          zorder=3)

        # estimate: solid line
        axis.plot(x_grid, line, color=theme["better"], linewidth=2, zorder=4)

        axis.text(0.03, 0.97, f"r = {value_r:.2f}", transform=axis.transAxes,
                  ha="left", va="top", fontsize=12, fontweight="bold",
                  color=theme["ink"])
        axis.text(0.03, 0.885, f"95% interval {low_r:.2f} to {high_r:.2f}",
                  transform=axis.transAxes, ha="left", va="top", fontsize=8,
                  color=theme["muted"])
        axis.text(0.03, 0.82, f"chase rate r = {rate_r:.2f}",
                  transform=axis.transAxes, ha="left", va="top", fontsize=8,
                  color=theme["ink_secondary"])

        axis.set_title(f"{first_season} to {second_season}  ·  {len(paired)} hitters",
                       loc="left", fontsize=10.5, fontweight="bold", pad=6)
        axis.set_xlabel(f"{first_season} runs saved per 600 PA")
        axis.grid(zorder=0)
        clean_axes(axis)

    axes[0][0].set_ylabel("Next season, runs saved per 600 PA")

    add_titles(
        figure,
        "Chase value carries over from one season to the next"
        + (" (xChase+)" if EXPECTED_CONTACT else ""),
        "Hitters qualified in both seasons (runs saved before shrinkage). "
        "Plain chase rate repeats more strongly.",
        theme,
    )

    handles = [
        plt.Line2D([], [], marker="o", linestyle="none", markersize=5,
                   color=theme["better"], alpha=0.6, markeredgecolor="none",
                   label="Hitter"),
        plt.Line2D([], [], color=theme["better"], linewidth=2,
                   label="Fitted line (estimate)"),
        plt.Line2D([], [], color=theme["better"],
                   alpha=theme["confidence_band_alpha"] + 0.07, linewidth=8,
                   label="95% confidence band for the fit"),
    ]
    figure.legend(handles=handles, loc="upper left", ncol=3,
                  bbox_to_anchor=(0.005, 0.915), fontsize=8.5,
                  handlelength=1.8, columnspacing=1.6)

    written.append(save(figure, "reliability", mode))


# --------------------------------------------------
# MARKDOWN TABLES FOR THE README
# --------------------------------------------------

def markdown_rows(table, start_rank, step):
    lines = []
    rank = start_rank
    for _, row in table.iterrows():
        line = (
            f"| {rank} | {row['label']} | {int(row['plate_appearances'])} "
            f"| {row['chase_rate']:.1f}% | {row['runs_saved_shrunk']:+.1f} "
            f"| **{row['chase_plus']:.0f}** ± {row['chase_plus_posterior_sd']:.0f} |"
        )

        # xChase+: add the hitter's Chase+ and the luck between them
        key = (row["batter"], row["game_year"])
        if key in actual_chase_plus:
            actual_value = actual_chase_plus[key]
            line += f" {actual_value:.0f} | {actual_value - row['chase_plus']:+.0f} |"

        lines.append(line)
        rank += step
    return lines


print()
print("Markdown tables for README.md:")

for season in seasons:

    one_season = by_season[by_season["game_year"] == season].sort_values(
        "runs_saved_shrunk", ascending=False
    )
    count = len(one_season)

    print()
    print(f"**{season}** ({count} qualified hitters)")
    print()
    if actual_chase_plus:
        print(f"| Rank | Player | PA | Chase% | Runs saved / 600 PA | {STAT_NAME} ± 1 SD | Chase+ | Luck |")
        print("|---:|---|---:|---:|---:|---|---:|---:|")
    else:
        print(f"| Rank | Player | PA | Chase% | Runs saved / 600 PA | {STAT_NAME} ± 1 SD |")
        print("|---:|---|---:|---:|---:|---|")
    for line in markdown_rows(one_season.head(TOP_AND_BOTTOM), 1, 1):
        print(line)
    print("| | ... | | | | | | |" if actual_chase_plus else "| | ... | | | | |")
    for line in markdown_rows(one_season.tail(TOP_AND_BOTTOM),
                              count - TOP_AND_BOTTOM + 1, 1):
        print(line)

print()
print(f"Saved {len(written)} figures to {FIGURE_DIR.relative_to(PROJECT_DIR)}/:")

for path in written:
    print(f"  {path.name}")
