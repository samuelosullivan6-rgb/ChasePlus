"""
Step 4 of the pipeline: the chase cost leaderboard and Chase+.

Chase rate treats every swing at a ball as the same mistake, but the run
value tables say chases differ a lot in cost (about 0.06 runs on 0-1 versus
about 0.36 on 3-2). This script ranks hitters by what their chases cost.

COST OF ONE CHASE

    chase_cost = value_if_taken - value_if_swung

Both sides come from the count run value table, so the value of the
current count cancels out.
  - value_if_taken weights "ball" and "called strike" by a called-strike
    probability from a per-season logistic model (distance outside the
    zone + count), fit on this data's takes.
  - value_if_swung: a whiff or foul tip adds a strike, a foul adds a strike
    unless there are already two, and a ball in play gets the plate
    appearance's actual run value.
Takes cost 0.

COMPARING HITTERS

Raw cost is not fair on its own: deep counts (e.g. 3-1) are expensive
places to chase, and feared hitters see more easy-to-take pitches nowhere
near the zone. So every pitch is priced against the league average cost in
the same season, count and distance bucket. The headline number is runs
SAVED against that baseline, per 600 PA (positive = good).

CHASE+ (league average = 100, like wRC+)

    chase_plus = 100 + 100 * runs_saved_shrunk / league chase cost per 600 PA

The unshrunk chase_plus_raw averages exactly 100 over every hitter-season
weighted by plate appearances. 130 means he saved runs worth 30% of what an
average hitter lost to chasing that season.

Known limitation: shrinkage pulls everyone toward one season-wide mean,
and split-half tests show that is too strong at both ends of chase rate
(about 4 runs per 600 PA each way on half-season samples). Extreme values
are, if anything, understated.

DESIGN CHOICES
  - Every season stands on its own: the called-strike model, league
    baseline, shrinkage prior, ranks and floors are all per season, and
    one file is written per season. The environment moves between years,
    and 2026 is the first season under the ABS Challenge System.
  - runs_saved is relative to the hitter's own season, so every season
    averages to zero (PA-weighted). runs_saved_vs_anchor re-prices every
    season against one fixed anchor season for absolute comparisons.
  - Qualification is per season (opportunity and PA floors, prorated for
    an unfinished season). There is no chase-count floor, because it would
    only ever remove the hitters best at not chasing.
  - Out-of-zone pitches from plate appearances with no run value (almost
    all walk-off half innings, excluded by BuildRunValueTables.py) are
    dropped rather than priced at zero. Those plate appearances still
    count in each hitter's PA total (about 0.4% of PAs).
  - Every hitter-season is shrunk toward its season's mean
    (DerSimonian-Laird) in proportion to its standard error.
  - Context neutral on purpose: base-out state is ignored, so a hitter is
    not credited or charged for when his teammates reached base.

Inputs:  data/cleaned/baseline_chase_pitches.parquet
         data/cleaned/plate_appearance_run_values.parquet
         results/run_value_by_count.csv, results/run_value_by_event.csv
Outputs: results/chase_cost_leaderboard_<season>.csv (one per season)
         results/chase_cost_leaderboard_by_season.csv
         results/chase_cost_leaderboard.csv (career)
         results/chase_plus_league_scale.csv
         results/called_strike_model_check.csv
         data/cleaned/chase_costs_by_pitch.parquet

Console output (presentation only; calculations, checks and saved files
are identical in every mode, and warnings/errors always print):

    python scripts/buildchaseleaderboard.py                season summary,
        leaderboards, rank comparison, warnings, saved files
    python scripts/buildchaseleaderboard.py --diagnostics  + numerical
        diagnostic tables
    python scripts/buildchaseleaderboard.py --verbose      + explanations
        and progress messages

check_chase_invariants.py reads several settings below with the ast
module. Keep them as plain top-level NAME = <literal> assignments.
"""

import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler


# --------------------------------------------------
# DISPLAY MODE
#
# Parsed before anything is read or fitted, so --help exits right away.
# Only console output depends on it. Warnings and errors use plain print()
# (or raise) and show in every mode.
# --------------------------------------------------

def parse_display_level():
    """0 = concise (default), 1 = --diagnostics, 2 = --verbose."""

    parser = argparse.ArgumentParser(
        description=(
            "Build the per-season chase cost leaderboards and Chase+. "
            "The flags only change what is printed: every calculation, "
            "check and saved file is the same in all modes, and warnings "
            "always print."
        )
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="also print the numerical diagnostic tables (called-strike "
             "model, out-of-fold check, calibration, qualification, "
             "shrinkage, baselines, Chase+ scale, consistency checks)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="everything in --diagnostics plus detailed explanations and "
             "progress messages (wins if both flags are given)",
    )

    arguments = parser.parse_args()

    if arguments.verbose:
        return 2

    if arguments.diagnostics:
        return 1

    return 0


DISPLAY_LEVEL = parse_display_level()


def show_diagnostic(*values):
    """Print only with --diagnostics or --verbose."""

    if DISPLAY_LEVEL >= 1:
        print(*values)


def show_detail(*values):
    """Print only with --verbose (explanations and progress messages)."""

    if DISPLAY_LEVEL >= 2:
        print(*values)


def show_diagnostic_header(title):
    """Section banner for a diagnostic block."""

    show_diagnostic()
    show_diagnostic("=" * 78)
    show_diagnostic(title)
    show_diagnostic("=" * 78)


def print_header(title):
    """Section banner that prints in every mode."""

    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

# QUALIFYING, ONE SEASON AT A TIME
#
# Both floors must be cleared in the same season. The median qualified
# hitter-season sees about 950 out-of-zone pitches (the busiest about
# 1,600), so these are roughly a half-season regular: about 265-270
# hitters a year.
#
# There is deliberately no chase floor. An old 120-chase floor implied a
# 20% chase rate at 600 opportunities, so it only removed the most
# disciplined hitters (Edouard Julien 2024 and 2026, Lars Nootbaar 2026).
# Their standard errors hold up in split-half checks, and shrinkage
# handles their smaller chase samples.
MINIMUM_OPPORTUNITIES_PER_SEASON = 600

MINIMUM_PLATE_APPEARANCES_PER_SEASON = 300

# cost_per_chase divides by chases, so it is left blank below this many
# chases (at 120 chases one ball in play can move it by a whole
# between-hitter standard deviation). Not prorated by season length: the
# noise depends on the number of chases, not the calendar.
MINIMUM_CHASES_FOR_COST_PER_CHASE = 120

# Not a floor. A qualified hitter-season with fewer chases than this is
# below the range where the standard error was checked, and gets a warning.
CHASE_COUNT_WARNING_BELOW = 50

# Scale each season's floors by its games / the longest season's games, so
# an in-progress season is not emptied by the calendar. Small samples still
# get bigger standard errors and more shrinkage.
PRORATE_FLOORS_BY_SEASON_LENGTH = True

# The season every other season is re-priced against for
# runs_saved_vs_anchor. None means the earliest season in the data.
ANCHOR_SEASON = None

# Distance-outside-the-zone buckets (feet). They define the league
# baseline cells (season x count x bucket) and are used for reporting.
# The called-strike model does not use them; it takes distance as a
# continuous number.
DISTANCE_BINS = [-0.001, 0.15, 0.35, 0.70, 100]

DISTANCE_LABELS = [
    "borderline",
    "just off",
    "clearly off",
    "nowhere near",
]

# A (season, count, bucket) baseline cell with fewer pitches than this is
# listed as noisy.
THIN_CELL_WARNING_PITCHES = 200

PLATE_APPEARANCES_PER_SEASON = 600

LEADERBOARD_SIZE = 10

# Knots of the called-strike distance spline, in feet outside the zone.
# Past the last knot the curve is linear in log-odds. Knots beyond 0.7 ft
# let the thin tail bend back up past about 1.15 ft (a pitch four feet off
# more likely to be a called strike than one a foot off), so they stop
# at 0.7.
CALLED_STRIKE_DISTANCE_KNOTS = [0.0, 0.10, 0.20, 0.30, 0.45, 0.70]

# Out-of-fold check of the called-strike model: each season's takes are
# split into folds by game, and each fold is predicted by a model that
# never saw it. Adds about half a minute. False skips it.
RUN_OUT_OF_FOLD_CHECK = True

OUT_OF_FOLD_SPLITS = 5

OUT_OF_FOLD_SEED = 0

# Minimum amount by which out-of-fold log loss must exceed in-sample log
# loss, as a share of p/n (p fitted numbers, n takes). A model's in-sample
# optimism is about p/n, and clean folds here recover about 1.0-1.2 x p/n.
# Folds that saw all their own test takes would score the in-sample number
# itself, so a plain "worse than in sample" test would be decided by
# rounding; this margin catches that. Folds that saw only some of their
# test takes are not caught.
OUT_OF_FOLD_GAP_SHARE_OF_OPTIMISM = 0.25

# Calibration cells more than this many standard errors off are flagged.
CALIBRATION_Z_WARNING = 3.0


# --------------------------------------------------
# FILE LOCATIONS
#
# Paths are anchored to the project folder (the parent of scripts/), not
# to the directory the script is run from. Output names are fixed, so each
# run overwrites the last.
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
RESULTS_DIR = PROJECT_DIR / "results"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PITCH_FILE = CLEAN_DIR / "baseline_chase_pitches.parquet"
PA_VALUE_FILE = CLEAN_DIR / "plate_appearance_run_values.parquet"

COUNT_VALUE_FILE = RESULTS_DIR / "run_value_by_count.csv"
EVENT_VALUE_FILE = RESULTS_DIR / "run_value_by_event.csv"

# One file per season, plus every qualified hitter-season stacked, plus the
# career table (the same hitters added up over the seasons they qualified).
SEASON_LEADERBOARD_NAME = "chase_cost_leaderboard_{season}.csv"

OUTPUT_BY_SEASON = RESULTS_DIR / "chase_cost_leaderboard_by_season.csv"
OUTPUT_CAREER = RESULTS_DIR / "chase_cost_leaderboard.csv"
OUTPUT_PITCH_COSTS = CLEAN_DIR / "chase_costs_by_pitch.parquet"

# Diagnostic tables: the called-strike model on takes it never saw, and
# the Chase+ scale for each season.
OUTPUT_CALLED_STRIKE_CHECK = RESULTS_DIR / "called_strike_model_check.csv"
OUTPUT_CHASE_PLUS_SCALE = RESULTS_DIR / "chase_plus_league_scale.csv"


def fingerprint_of(paths):
    """
    Short hash of the given files (names and contents). Written into the
    diagnostic tables so check_chase_invariants.py can tell whether the
    results on disk came from the current script and data.
    """

    digest = hashlib.sha256()

    for path in paths:

        digest.update(Path(path).name.encode())

        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)

    return digest.hexdigest()[:16]


RUN_FINGERPRINT = fingerprint_of([
    Path(__file__).resolve(),
    PITCH_FILE,
    PA_VALUE_FILE,
    COUNT_VALUE_FILE,
    EVENT_VALUE_FILE,
])


# --------------------------------------------------
# RUN VALUE TABLES
# --------------------------------------------------

if DISPLAY_LEVEL == 0:
    print(
        "Chase leaderboard (concise output; add --diagnostics or --verbose "
        "for more)"
    )

show_detail(f"Run fingerprint (this script + the files it reads): {RUN_FINGERPRINT}")
show_detail()
show_detail("Loading run value tables...")

count_values = pd.read_csv(COUNT_VALUE_FILE)
event_values = pd.read_csv(EVENT_VALUE_FILE)

count_value_lookup = {
    (int(row["balls"]), int(row["strikes"])): float(row["run_value"])
    for _, row in count_values.iterrows()
}


def event_value(event_name):
    """Run value of a terminal outcome, from the event table."""

    match = event_values[event_values["event"] == event_name]

    if len(match) != 1:
        raise RuntimeError(
            f"Could not find a single run value for '{event_name}'."
        )

    return float(match["run_value"].iloc[0])


WALK_VALUE = event_value("walk")
STRIKEOUT_VALUE = event_value("strikeout")

show_diagnostic(f"Walk value:      {WALK_VALUE:+.4f}")
show_diagnostic(f"Strikeout value: {STRIKEOUT_VALUE:+.4f}")


def value_at_count(balls, strikes):
    """
    Run value of standing at this count. A fourth ball is a walk and a
    third strike is a strikeout, so those come from the event table.
    """

    if balls >= 4:
        return WALK_VALUE

    if strikes >= 3:
        return STRIKEOUT_VALUE

    return count_value_lookup[(balls, strikes)]


# --------------------------------------------------
# PITCHES
# --------------------------------------------------

show_detail()
show_detail("Loading pitches...")

# Only the columns this script uses.
wanted_pitch_columns = [
    "game_pk",
    "at_bat_number",
    "pitch_number",
    "batter",
    "pitcher",
    "game_year",
    "description",
    "balls",
    "strikes",
    "count_state",
    "is_analyzable",
    "is_outside_zone",
    "is_swing",
    "is_chase",
    "distance_outside_zone",
    # location and the hitter's zone: only used to label which side of
    # the zone a pitch missed on, for a calibration check
    "plate_x",
    "plate_z",
    "sz_top",
    "sz_bot",
]

df = pd.read_parquet(PITCH_FILE, columns=wanted_pitch_columns)

show_detail(f"Loaded {len(df):,} pitches.")

opportunities = df[
    (df["is_analyzable"] == 1)
    & (df["is_outside_zone"] == 1)
].copy()

show_diagnostic(f"Out-of-zone chase opportunities: {len(opportunities):,}")

opportunities["balls"] = opportunities["balls"].astype(int)
opportunities["strikes"] = opportunities["strikes"].astype(int)

opportunities["distance_bucket"] = pd.cut(
    opportunities["distance_outside_zone"],
    bins=DISTANCE_BINS,
    labels=DISTANCE_LABELS
).astype(str)


# --------------------------------------------------
# DROP PLATE APPEARANCES THAT CANNOT BE PRICED
#
# The run value file excludes half innings cut short by the end of the
# game, so a ball in play from one has no value to look up. Pricing those
# at zero would make every walk-off chase free, and would favor whoever
# appears in walk-off innings most. So every out-of-zone pitch of those
# plate appearances is removed, takes included (keeping only the takes
# would pad the sample with decisions that could never cost anything).
# The plate appearances still count in each hitter's PA total below.
# --------------------------------------------------

pa_values = pd.read_parquet(PA_VALUE_FILE)

pa_lookup = pa_values[
    ["game_pk", "at_bat_number", "run_value"]
].rename(columns={"run_value": "plate_appearance_value"})

opportunities = opportunities.merge(
    pa_lookup,
    on=["game_pk", "at_bat_number"],
    how="left"
)

unpriceable = opportunities["plate_appearance_value"].isna()

show_diagnostic()
show_diagnostic(
    f"Dropping {int(unpriceable.sum()):,} opportunities from plate "
    f"appearances with no run value "
    f"({unpriceable.mean():.2%} of the sample)."
)
show_detail(
    "These are almost entirely walk-off innings, which the run "
    "value script excludes on purpose."
)
show_detail(
    "Their plate appearances still count in each hitter's PA total."
)

opportunities = opportunities[~unpriceable].copy()


# --------------------------------------------------
# HOW LIKELY WAS A TAKE TO BE CALLED A STRIKE
#
# Assuming every take is a ball would make every borderline chase look
# like a pure giveaway. Instead, a per-season logistic model estimates the
# called-strike probability of each out-of-zone pitch if taken.
#
# Distance: a cubic spline with fixed knots (CALLED_STRIKE_DISTANCE_KNOTS),
# not buckets (which would give 0.16 ft and 0.34 ft the same rate) and not
# a straight line (which misfit the curve near the zone badly enough to
# show in the 2026 calibration table). Each season's curve is checked
# below to never rise with distance.
#
# Count: one indicator per count (0-0 is the reference). Umpires call the
# same pitch differently by count (0-2 gets a much smaller zone, 3-0 the
# most generous). Without count, two-strike chases look cheap, which hurts
# the most disciplined hitters most. Out of fold, count improves log loss
# by 2-3% every season. Straight lines in balls and strikes were rejected
# in all three seasons.
#
# This does not count the count twice:
#
#   value_if_taken = P(called strike) * V(balls, strikes + 1)
#                    + (1 - P) * V(balls + 1, strikes)
#
# P gives the probabilities and V the payoffs of one expected value; both
# have to know the count. The count x distance baseline further down is a
# separate thing: a benchmark for which pitches a hitter was shown.
#
# Deliberately not a pitch-quality model: no pitch type, velocity,
# catcher, umpire, or side of the zone. Adding any of those needs its own
# before/after test.
#
# One model per season: from 2026 calls can be challenged under the ABS
# Challenge System, and calling drifts between seasons anyway (a 2024
# model badly misses 2025's overall called-strike rate).
# --------------------------------------------------

# Which side of the zone each pitch missed on. NOT a model input; only
# used in the out-of-fold check, because it is the model's biggest known
# gap. Same geometry as distance_outside_zone in script 03.
HALF_PLATE_PLUS_BALL = 0.83

sideways_miss = (
    opportunities["plate_x"].abs() - HALF_PLATE_PLUS_BALL
).clip(lower=0)

above_miss = (opportunities["plate_z"] - opportunities["sz_top"]).clip(lower=0)
below_miss = (opportunities["sz_bot"] - opportunities["plate_z"]).clip(lower=0)

opportunities["miss_direction"] = np.select(
    [
        opportunities[["plate_x", "plate_z", "sz_top", "sz_bot"]]
        .isna()
        .any(axis=1),
        (sideways_miss > 0) & ((above_miss > 0) | (below_miss > 0)),
        sideways_miss > 0,
        above_miss > 0,
        below_miss > 0,
    ],
    ["unknown", "corner", "side", "above", "below"],
    default="on the edge",
)

takes = opportunities[opportunities["is_swing"] == 0].copy()

takes["was_called_strike"] = (
    takes["description"] == "called_strike"
).astype(int)

model_inputs = ["distance_outside_zone", "balls", "strikes"]

# Takes are a subset of opportunities, so only opportunities are counted.
missing_features = int(
    opportunities[model_inputs].isna().any(axis=1).sum()
)

if missing_features > 0:
    print()
    print(
        f"WARNING: {missing_features:,} opportunities are missing one "
        f"of {model_inputs} (likely a null sz_top/sz_bot upstream). "
        "Leaving them out of the model fit and giving them their "
        "season's called-strike rate for the count instead."
    )
    takes = takes.dropna(subset=model_inputs)

# An impossible count would not raise an error in the count indicators;
# it would silently be treated as 0-0. Stop instead.
impossible_counts = (
    ~opportunities["balls"].between(0, 3)
    | ~opportunities["strikes"].between(0, 2)
)

if impossible_counts.any():
    raise RuntimeError(
        f"{int(impossible_counts.sum()):,} opportunities have a count "
        "outside 0-3 balls / 0-2 strikes. Fix that upstream first."
    )

COUNTS_IN_ORDER = [
    (balls, strikes)
    for balls in range(4)
    for strikes in range(3)
]


def called_strike_features(frame):
    """
    Raw distance (the spline is built inside the model) plus one 0/1
    column for every count except 0-0. The columns are the same for any
    slice of pitches, so a model fit on one set can score another.
    """

    features = pd.DataFrame(
        {
            "distance_outside_zone": (
                frame["distance_outside_zone"].astype(float)
            )
        },
        index=frame.index
    )

    balls = frame["balls"].to_numpy()
    strikes = frame["strikes"].to_numpy()

    for count_balls, count_strikes in COUNTS_IN_ORDER[1:]:

        features[f"count_{count_balls}_{count_strikes}"] = (
            (balls == count_balls)
            & (strikes == count_strikes)
        ).astype(float)

    return features


def distance_only_features(frame):
    """Distance alone. Only used as the comparison model in the check."""

    return pd.DataFrame(
        {
            "distance_outside_zone": (
                frame["distance_outside_zone"].astype(float)
            )
        },
        index=frame.index
    )


def new_called_strike_model():
    """
    Logistic regression on a scaled cubic spline of distance, with any
    other columns (the count indicators) passed straight through. The
    spline lives inside the pipeline, so each season learns its own curve.
    """

    knots = np.array(CALLED_STRIKE_DISTANCE_KNOTS).reshape(-1, 1)

    distance_curve = Pipeline([
        (
            "spline",
            SplineTransformer(
                knots=knots,
                degree=3,
                extrapolation="linear",
                include_bias=False
            )
        ),
        ("scale", StandardScaler()),
    ])

    features = ColumnTransformer(
        [("distance", distance_curve, ["distance_outside_zone"])],
        remainder="passthrough",
        verbose_feature_names_out=False
    )

    return Pipeline([
        ("features", features),
        ("logit", LogisticRegression(max_iter=1000)),
    ])


def count_effects(model):
    """
    Each count's shift in the log-odds of a called strike versus 0-0 at the
    same distance, as a balls x strikes grid.
    """

    names = list(model.named_steps["features"].get_feature_names_out())

    coefficients = dict(
        zip(names, model.named_steps["logit"].coef_[0])
    )

    grid = pd.DataFrame(
        0.0,
        index=pd.Index(range(4), name="balls"),
        columns=pd.Index(range(3), name="strikes")
    )

    for count_balls, count_strikes in COUNTS_IN_ORDER[1:]:
        grid.loc[count_balls, count_strikes] = coefficients[
            f"count_{count_balls}_{count_strikes}"
        ]

    return grid


def pitches_at(distances, balls=0, strikes=0):
    """Made-up takes at these distances, all in one count."""

    return pd.DataFrame({
        "distance_outside_zone": distances,
        "balls": balls,
        "strikes": strikes,
    })


show_diagnostic_header(
    "CALLED-STRIKE MODEL (logistic: distance curve + count, per season)"
)

# A 0-0 take at each of these distances shows the shape of the curve.
DISTANCES_TO_SHOW = [0.05, 0.15, 0.25, 0.35, 0.50, 0.75, 1.00]

# Count terms only shift the whole curve, so if the 0-0 curve never rises
# with distance, no count's curve does either.
monotone_check_pitches = pitches_at(np.linspace(0, 10, 4001))

called_strike_models = {}

for year in sorted(takes["game_year"].dropna().unique()):

    year_takes = takes[takes["game_year"] == year]

    model = new_called_strike_model()
    model.fit(
        called_strike_features(year_takes),
        year_takes["was_called_strike"]
    )
    called_strike_models[year] = model

    show_diagnostic()
    show_diagnostic(
        f"{int(year)}  (takes used to fit: {len(year_takes):,}; "
        f"called strikes: {int(year_takes['was_called_strike'].sum()):,})"
    )

    show_diagnostic()
    show_diagnostic("Count effect on the log-odds of a called strike, vs 0-0:")
    show_diagnostic(count_effects(model).round(3).to_string())

    shown_rates = model.predict_proba(
        called_strike_features(pitches_at(DISTANCES_TO_SHOW))
    )[:, 1]

    show_diagnostic()
    show_diagnostic("Called-strike chance of a 0-0 take, by feet outside the zone:")
    show_diagnostic(
        "  "
        + "  ".join(
            f"{distance:.2f} ft {rate:.3f}"
            for distance, rate in zip(DISTANCES_TO_SHOW, shown_rates)
        )
    )

    curve = model.predict_proba(
        called_strike_features(monotone_check_pitches)
    )[:, 1]

    rises = np.diff(curve) > 1e-12

    if rises.any():

        first_rise = monotone_check_pitches["distance_outside_zone"].iloc[
            int(np.argmax(rises)) + 1
        ]

        print(
            f"WARNING: the fitted curve rises again past "
            f"{first_rise:.2f} ft. A pitch farther off the plate should "
            "never be likelier to be called a strike. Check the knots "
            "before trusting value_if_taken for this season."
        )

    else:

        show_diagnostic("Curve never rises with distance (checked 0 to 10 ft): OK")

    logit_step = model.named_steps["logit"]

    if int(logit_step.n_iter_[0]) >= logit_step.max_iter:
        print(
            f"WARNING: the {int(year)} fit stopped at "
            f"{int(logit_step.n_iter_[0])} iterations without converging."
        )

show_detail()
show_detail(
    "Read each grid across a row for what adding strikes does to the "
    "zone, and down a column for what adding balls does. Negative "
    "means fewer called strikes than at 0-0 for a pitch the same "
    "distance off the plate."
)

two_strike_effects = ", ".join(
    f"{int(year)} {count_effects(model).loc[0, 2]:+.2f}"
    for year, model in sorted(called_strike_models.items())
)

show_diagnostic()
show_diagnostic(f"The 0-2 effect by season: {two_strike_effects}.")
show_detail(
    "These models describe how out-of-zone takes were called each "
    "season; they cannot say why the calling changed between seasons."
)

opportunities["called_strike_rate"] = np.nan

for year, model in called_strike_models.items():

    year_mask = (
        (opportunities["game_year"] == year)
        & opportunities[model_inputs].notna().all(axis=1)
    )

    opportunities.loc[year_mask, "called_strike_rate"] = (
        model.predict_proba(
            called_strike_features(opportunities.loc[year_mask])
        )[:, 1]
    )

# A pitch the model could not score (no distance) gets its season's
# called-strike rate for takes in the same count, or the rate over all
# takes if even that is missing.
unscored = opportunities["called_strike_rate"].isna()

if unscored.any():

    count_called_strike_rate = (
        takes
        .groupby(["game_year", "balls", "strikes"])["was_called_strike"]
        .mean()
        .rename("count_called_strike_rate")
        .reset_index()
    )

    fallback_rate = (
        opportunities.loc[unscored, ["game_year", "balls", "strikes"]]
        .merge(
            count_called_strike_rate,
            on=["game_year", "balls", "strikes"],
            how="left"
        )["count_called_strike_rate"]
        .fillna(takes["was_called_strike"].mean())
        .to_numpy()
    )

    opportunities.loc[unscored, "called_strike_rate"] = fallback_rate

takes["predicted_rate"] = np.nan

for year, model in called_strike_models.items():

    year_mask = takes["game_year"] == year

    takes.loc[year_mask, "predicted_rate"] = (
        model.predict_proba(
            called_strike_features(takes.loc[year_mask])
        )[:, 1]
    )

show_diagnostic()
show_diagnostic("Out-of-zone takes called strikes, actual vs the model's average:")

for year in sorted(called_strike_models):

    year_takes = takes[takes["game_year"] == year]

    show_diagnostic(
        f"  {int(year)}: {year_takes['was_called_strike'].mean():.2%} "
        f"actual, {year_takes['predicted_rate'].mean():.2%} predicted"
    )


# --------------------------------------------------
# DOES THE MODEL HOLD UP ON TAKES IT NEVER SAW
#
# The models above are fit on every take of a season and used on those
# same pitches, which is fine for pricing but cannot show whether the
# model is right. So each season's takes are split into folds by GAME (a
# game's umpire and catcher stay together, or the check would flatter
# itself), and every fold is predicted by a model fit on the others. A
# distance-only model gets the same treatment, to measure what the count
# terms add.
#
# How to read the output:
#   - Calibration matters most: when the model says 5%, about 5% should
#     be strikes, in every count and at every distance.
#   - log_loss and brier_score: lower is better. auc only measures
#     ranking, which matters least here.
#   - calibration_slope near 1 and calibration_intercept near 0: the
#     predictions are neither too spread out nor shifted.
#   - z = (called strikes - expected) / standard error. With this many
#     takes a big z can be a tiny gap, so actual_minus_predicted_per_1000
#     is shown next to it. Both are positive when the model under-calls
#     strikes.
# --------------------------------------------------

def calibration_intercept_and_slope(outcomes, predicted):
    """
    slope: logistic fit of the outcome on logit(p).
    intercept ("calibration in the large"): the shift that makes
    logit(p) + shift match the actual strike rate, with slope held at 1.
    """

    clipped = np.clip(predicted, 1e-12, 1 - 1e-12)
    logit = np.log(clipped / (1 - clipped))

    # C=inf means no penalty, so this is a plain maximum-likelihood fit
    slope_fit = LogisticRegression(C=np.inf, max_iter=1000)
    slope_fit.fit(logit.reshape(-1, 1), outcomes)
    slope = float(slope_fit.coef_[0][0])

    # Newton's method on the one shift parameter
    shift = 0.0

    for _ in range(50):

        chance = 1 / (1 + np.exp(-(logit + shift)))
        step = (
            np.sum(outcomes - chance)
            / np.sum(chance * (1 - chance))
        )
        shift += step

        if abs(step) < 1e-10:
            break

    return shift, slope


def calibration_table(frame, group_columns, rate_column):
    """Actual vs predicted called strikes in each group, with z."""

    table = (
        frame
        .assign(
            predicted=frame[rate_column],
            variance=frame[rate_column] * (1 - frame[rate_column])
        )
        .groupby(group_columns, observed=True)
        .agg(
            takes=("was_called_strike", "size"),
            called_strikes=("was_called_strike", "sum"),
            actual_rate=("was_called_strike", "mean"),
            predicted_rate=("predicted", "mean"),
            expected_strikes=("predicted", "sum"),
            variance=("variance", "sum"),
        )
    )

    table["actual_minus_predicted_per_1000"] = (
        1000 * (table["actual_rate"] - table["predicted_rate"])
    )

    table["z"] = (
        (table["called_strikes"] - table["expected_strikes"])
        / np.sqrt(table["variance"])
    )

    return table.drop(columns=["expected_strikes", "variance"])


def print_calibration(table):
    """
    Show a calibration table, then its chi-square over all cells
    (diagnostic output).
    """

    show_diagnostic(
        table[
            [
                "takes",
                "actual_rate",
                "predicted_rate",
                "actual_minus_predicted_per_1000",
                "z",
            ]
        ]
        .round(4)
        .to_string()
    )

    # One number for the whole table, since a table-wide misfit can hide
    # behind cells that each look fine. It should be about the number of
    # cells if the model is right; p is how often chance alone would do
    # worse.
    chi_square = (table["z"] ** 2).sum()

    show_diagnostic(
        f"chi-square {chi_square:.1f} on {len(table)} cells "
        f"(p = {chi2.sf(chi_square, len(table)):.2g})"
    )


def group_label(group):
    """'just off / 2' for a multi-column group, str(group) otherwise."""

    if isinstance(group, tuple):
        return " / ".join(str(part) for part in group)

    return str(group)


def calibration_check_row(year, check_name, group, row):
    """One calibration cell as a row of the called-strike check file."""

    return {
        "game_year": int(year),
        "check": check_name,
        "group": group_label(group),
        "takes": int(row["takes"]),
        "actual_rate": row["actual_rate"],
        "predicted_rate": row["predicted_rate"],
        "actual_minus_predicted_per_1000": (
            row["actual_minus_predicted_per_1000"]
        ),
        "z": row["z"],
    }


called_strike_check_rows = []

if RUN_OUT_OF_FOLD_CHECK:

    show_diagnostic_header(
        "CALLED-STRIKE MODEL ON TAKES IT NEVER SAW (out of fold, by game)"
    )

    for year in sorted(called_strike_models):

        year_takes = takes[takes["game_year"] == year].copy()

        folds = GroupKFold(
            n_splits=OUT_OF_FOLD_SPLITS,
            shuffle=True,
            random_state=OUT_OF_FOLD_SEED
        )

        oof_full = np.full(len(year_takes), np.nan)
        oof_distance_only = np.full(len(year_takes), np.nan)

        for train_rows, test_rows in folds.split(
            year_takes,
            year_takes["was_called_strike"],
            groups=year_takes["game_pk"]
        ):

            train = year_takes.iloc[train_rows]
            test = year_takes.iloc[test_rows]

            # The point of grouping by game: no game on both sides
            if set(train["game_pk"]) & set(test["game_pk"]):
                raise RuntimeError(
                    "A game landed in a training fold and its test fold."
                )

            full_model = new_called_strike_model().fit(
                called_strike_features(train),
                train["was_called_strike"]
            )

            oof_full[test_rows] = full_model.predict_proba(
                called_strike_features(test)
            )[:, 1]

            distance_model = new_called_strike_model().fit(
                distance_only_features(train),
                train["was_called_strike"]
            )

            oof_distance_only[test_rows] = distance_model.predict_proba(
                distance_only_features(test)
            )[:, 1]

        year_takes["oof_rate"] = oof_full
        year_takes["oof_rate_distance_only"] = oof_distance_only

        outcomes = year_takes["was_called_strike"].to_numpy()

        # The same two models fit on the whole season and scored on their
        # own takes. Out of fold must come out worse than this by at least
        # the minimum gap. The used model was already fit above; the
        # distance-only comparison model is fit here.
        in_sample_distance_only = new_called_strike_model().fit(
            distance_only_features(year_takes),
            year_takes["was_called_strike"]
        )

        in_sample_of = {
            "distance + count (used)": (
                called_strike_models[year],
                year_takes["predicted_rate"].to_numpy()
            ),
            "distance only (comparison)": (
                in_sample_distance_only,
                in_sample_distance_only.predict_proba(
                    distance_only_features(year_takes)
                )[:, 1]
            ),
        }

        summary_rows = []

        for label, column in [
            ("distance + count (used)", "oof_rate"),
            ("distance only (comparison)", "oof_rate_distance_only"),
        ]:

            predicted = year_takes[column].to_numpy()

            fitted_model, in_sample_rate = in_sample_of[label]

            # every coefficient the fit chose, plus the intercept
            coefficients = int(
                fitted_model[-1].coef_.size
                + fitted_model[-1].intercept_.size
            )

            in_sample_loss = log_loss(outcomes, in_sample_rate)

            minimum_gap = (
                OUT_OF_FOLD_GAP_SHARE_OF_OPTIMISM
                * coefficients
                / len(year_takes)
            )

            intercept, slope = calibration_intercept_and_slope(
                outcomes,
                predicted
            )

            summary_rows.append({
                "model": label,
                "log_loss": log_loss(outcomes, predicted),
                "brier_score": brier_score_loss(outcomes, predicted),
                "auc": roc_auc_score(outcomes, predicted),
                "calibration_intercept": intercept,
                "calibration_slope": slope,
                "in_sample_log_loss": in_sample_loss,
                "model_coefficients": coefficients,
                "minimum_out_of_fold_gap": minimum_gap,
            })

        summary = pd.DataFrame(summary_rows)

        count_gain = (
            1
            - summary["log_loss"].iloc[0] / summary["log_loss"].iloc[1]
        )

        summary["gap_over_in_sample"] = (
            summary["log_loss"] - summary["in_sample_log_loss"]
        )

        printed = summary.drop(columns=["model_coefficients"])

        show_diagnostic()
        show_diagnostic(
            f"{int(year)}  ({len(year_takes):,} takes, "
            f"{OUT_OF_FOLD_SPLITS} folds grouped by game)"
        )
        show_diagnostic()
        show_diagnostic(printed.round(6).to_string(index=False))
        show_diagnostic()
        show_diagnostic(
            f"The count terms lower out-of-fold log loss by "
            f"{count_gain:.1%}. In sample the used model scores "
            f"{summary['in_sample_log_loss'].iloc[0]:.5f}, so out of "
            f"fold has to come in at least "
            f"{summary['minimum_out_of_fold_gap'].iloc[0]:.6f} worse "
            "than that."
        )

        for _, row in summary.iterrows():
            if row["gap_over_in_sample"] <= row["minimum_out_of_fold_gap"]:
                print(
                    f"WARNING: {row['model']} scores only "
                    f"{row['gap_over_in_sample']:+.6f} against its own "
                    f"in-sample fit, under the "
                    f"{row['minimum_out_of_fold_gap']:.6f} I expect. The "
                    "folds are probably leaking -- check that each "
                    "fold's model is fit without its test takes."
                )

        for _, row in summary.iterrows():
            called_strike_check_rows.append({
                "game_year": int(year),
                "check": "summary",
                "group": row["model"],
                "takes": len(year_takes),
                "log_loss": row["log_loss"],
                "brier_score": row["brier_score"],
                "auc": row["auc"],
                "calibration_intercept": row["calibration_intercept"],
                "calibration_slope": row["calibration_slope"],
                "in_sample_log_loss": row["in_sample_log_loss"],
                "model_coefficients": row["model_coefficients"],
                "minimum_out_of_fold_gap": row["minimum_out_of_fold_gap"],
                "fold_splits": OUT_OF_FOLD_SPLITS,
                "fold_groups": "game_pk",
                "fold_seed": OUT_OF_FOLD_SEED,
            })

        year_takes["distance_decile"] = pd.qcut(
            year_takes["distance_outside_zone"],
            10,
            duplicates="drop"
        )

        tables = [
            ("by count", ["count_state"]),
            ("by distance decile", ["distance_decile"]),
            ("by distance bucket x strikes", ["distance_bucket", "strikes"]),
        ]

        flagged = []

        for check_name, group_columns in tables:

            table = calibration_table(year_takes, group_columns, "oof_rate")

            show_diagnostic()
            show_diagnostic(f"Calibration {check_name}:")
            print_calibration(table)

            for group, row in table.iterrows():

                called_strike_check_rows.append(
                    calibration_check_row(year, check_name, group, row)
                )

                if abs(row["z"]) > CALIBRATION_Z_WARNING:
                    flagged.append(
                        f"  {check_name} {group_label(group)}: "
                        f"z = {row['z']:+.1f}, predicted "
                        f"{row['predicted_rate']:.4f} vs actual "
                        f"{row['actual_rate']:.4f} "
                        f"({row['actual_minus_predicted_per_1000']:+.1f} "
                        "called strikes per 1000 takes)"
                    )

        if flagged:
            print()
            print(
                f"WARNING: {len(flagged)} calibration cell(s) more than "
                f"{CALIBRATION_Z_WARNING:.0f} standard errors off. With "
                "this many takes, check the gap before worrying about it:"
            )
            for line in flagged:
                print(line)
        else:
            show_detail()
            show_detail(
                f"No calibration cell above is more than "
                f"{CALIBRATION_Z_WARNING:.0f} standard errors off. Read "
                "the chi-square lines too: a small p there means the "
                "table as a whole is off by more than chance even when "
                "no single cell is. (The by-count table can hardly miss "
                "for a model with one term per count; bucket x strikes "
                "is the real test of count.)"
            )

        # Which side of the zone the take missed on is NOT in the model,
        # and this is where it is furthest off (takes just above the zone
        # are called strikes far more often than predicted, corners far
        # less). Shown every run as a known limitation, not flagged.
        by_miss = calibration_table(
            year_takes,
            ["distance_bucket", "miss_direction"],
            "oof_rate"
        )

        show_diagnostic()
        show_diagnostic(
            "Calibration by distance bucket x which side of the zone "
            "the take missed on (NOT in the model -- a known gap):"
        )
        print_calibration(by_miss)

        for group, row in by_miss.iterrows():
            called_strike_check_rows.append(
                calibration_check_row(
                    year,
                    "by distance bucket x miss direction (not in model)",
                    group,
                    row
                )
            )

else:

    # A check file from an earlier run may describe a model that no longer
    # exists, so remove it.
    if OUTPUT_CALLED_STRIKE_CHECK.exists():
        OUTPUT_CALLED_STRIKE_CHECK.unlink()
        print()
        print(
            f"Out-of-fold check skipped; removed the old "
            f"{OUTPUT_CALLED_STRIKE_CHECK.name} so it cannot be mistaken "
            "for this run's."
        )

    # Without the out-of-fold check, show the in-sample version, clearly
    # labelled as in sample.
    takes["distance_decile"] = (
        takes
        .groupby("game_year")["distance_outside_zone"]
        .transform(lambda x: pd.qcut(x, 10, duplicates="drop"))
    )

    show_diagnostic()
    show_diagnostic(
        "Calibration by season and distance decile (IN SAMPLE -- set "
        "RUN_OUT_OF_FOLD_CHECK = True for the honest version):"
    )
    show_diagnostic(
        calibration_table(
            takes,
            ["game_year", "distance_decile"],
            "predicted_rate"
        )
        .round(4)
        .to_string()
    )


# --------------------------------------------------
# WHAT TAKING IT WAS WORTH
# --------------------------------------------------

ball_value = np.array([
    value_at_count(balls + 1, strikes)
    for balls, strikes in zip(
        opportunities["balls"],
        opportunities["strikes"]
    )
])

called_strike_value = np.array([
    value_at_count(balls, strikes + 1)
    for balls, strikes in zip(
        opportunities["balls"],
        opportunities["strikes"]
    )
])

opportunities["value_if_taken"] = (
    opportunities["called_strike_rate"] * called_strike_value
    + (1 - opportunities["called_strike_rate"]) * ball_value
)


# --------------------------------------------------
# WHAT SWINGING PRODUCED
# --------------------------------------------------

# foul_tip means the catcher held it, so it is a strike, not a foul
strike_descriptions = {
    "swinging_strike",
    "swinging_strike_blocked",
    "foul_tip",
}

foul_descriptions = {
    "foul",
}

in_play_descriptions = {
    "hit_into_play",
}

# A foul with two strikes leaves the count where it was
foul_value = np.array([
    value_at_count(balls, min(strikes + 1, 2))
    for balls, strikes in zip(
        opportunities["balls"],
        opportunities["strikes"]
    )
])

opportunities["value_if_swung"] = np.nan

is_whiff = opportunities["description"].isin(strike_descriptions)
is_foul = opportunities["description"].isin(foul_descriptions)
is_in_play = opportunities["description"].isin(in_play_descriptions)

opportunities.loc[is_whiff, "value_if_swung"] = (
    called_strike_value[is_whiff.to_numpy()]
)

opportunities.loc[is_foul, "value_if_swung"] = (
    foul_value[is_foul.to_numpy()]
)

# Balls in play get the real outcome. A chase that drops in for a hit is
# not treated as a mistake in hindsight; otherwise the leaderboard would
# partly measure contact luck.
opportunities.loc[is_in_play, "value_if_swung"] = (
    opportunities.loc[is_in_play, "plate_appearance_value"]
)


# --------------------------------------------------
# THE COST
# --------------------------------------------------

opportunities["chase_cost"] = (
    opportunities["value_if_taken"]
    - opportunities["value_if_swung"]
)

# Takes cost nothing. Only swings at balls do.
opportunities.loc[
    opportunities["is_chase"] == 0,
    "chase_cost"
] = 0.0

unpriced = (
    (opportunities["is_chase"] == 1)
    & opportunities["chase_cost"].isna()
)

if unpriced.sum() > 0:

    print()
    print(
        f"WARNING: {int(unpriced.sum()):,} chases still cannot be "
        f"priced. Swing descriptions I have not handled:"
    )

    print(
        opportunities.loc[unpriced, "description"]
        .value_counts()
        .to_string()
    )

    print("Dropping them rather than calling them free.")

    opportunities = opportunities[~unpriced].copy()


# --------------------------------------------------
# WHAT A CHASE COSTS, BY COUNT
# --------------------------------------------------

chases = opportunities[opportunities["is_chase"] == 1]

cost_by_count = (
    chases
    .groupby(["balls", "strikes"])
    .agg(
        chases=("chase_cost", "size"),
        mean_cost=("chase_cost", "mean")
    )
    .reset_index()
)

show_diagnostic_header("AVERAGE COST OF ONE CHASE, BY COUNT (RUNS)")

show_diagnostic()
show_diagnostic(
    cost_by_count
    .pivot(index="balls", columns="strikes", values="mean_cost")
    .round(4)
    .to_string()
)

cheapest = cost_by_count["mean_cost"].min()
dearest = cost_by_count["mean_cost"].max()

show_diagnostic()
show_diagnostic(
    f"Cheapest count to chase in costs {cheapest:.4f} runs, "
    f"dearest costs {dearest:.4f}. "
    f"A {dearest / cheapest:.1f}x spread."
)


# --------------------------------------------------
# WHAT AN AVERAGE HITTER WOULD HAVE LOST (THE BASELINE)
#
# Two things vary between hitters that are not plate discipline:
#   - Hitters who work deep counts see more expensive counts to chase in.
#   - Some hitters are shown more pitches nowhere near the zone, which are
#     easy takes. This happens to feared hitters, and even more to hitters
#     pitchers expect to chase.
# So each pitch's baseline is what the league lost on average on the same
# kind of pitch: same season, count and distance bucket. Removing the
# easy-take credit can widen the spread between hitters, not only narrow
# it.
#
# The baseline is computed within each season, never pooled. Chase rate
# (28.6% / 28.3% / 30.5%) and zone rate (49.6% / 50.7% / 47.6%) moved
# across 2024/2025/2026, and 2026 added the ABS Challenge System. A pooled
# baseline would show a league-wide shift as every hitter moving together.
# The career table's shrinkage is the only place seasons meet.
# --------------------------------------------------

league_by_cell = (
    opportunities
    .groupby(["game_year", "balls", "strikes", "distance_bucket"])
    .agg(
        expected_cost_per_pitch=("chase_cost", "mean"),
        league_chase_rate=("is_chase", "mean"),
        league_pitches=("is_chase", "size")
    )
    .reset_index()
)

# Count-only baseline, kept to show what the distance adjustment changes.
league_by_count = (
    opportunities
    .groupby(["game_year", "balls", "strikes"])
    .agg(
        expected_cost_count_only=("chase_cost", "mean")
    )
    .reset_index()
)

opportunities = opportunities.merge(
    league_by_cell[
        [
            "game_year",
            "balls",
            "strikes",
            "distance_bucket",
            "expected_cost_per_pitch"
        ]
    ],
    on=["game_year", "balls", "strikes", "distance_bucket"],
    how="left"
)

opportunities = opportunities.merge(
    league_by_count,
    on=["game_year", "balls", "strikes"],
    how="left"
)

# Edge cases:
#   - A pitch with a distance is always part of its own cell, so it always
#     has a baseline.
#   - A pitch with no distance (missing sz_top/sz_bot upstream) has no
#     bucket, so it falls back to its season's count-only baseline. That
#     is reported, because it also means that season's runs saved will not
#     add to exactly zero.
#   - A pitch WITH a distance that missed every bucket means the bucket
#     edges are wrong, and stops the script.
unknown_buckets = ~opportunities["distance_bucket"].isin(DISTANCE_LABELS)

no_distance = opportunities["distance_outside_zone"].isna()

if (unknown_buckets & ~no_distance).any():
    raise RuntimeError(
        f"{int((unknown_buckets & ~no_distance).sum()):,} opportunities "
        "have a distance outside every bucket. Check DISTANCE_BINS."
    )

if no_distance.any():

    print()
    print(
        f"WARNING: {int(no_distance.sum()):,} opportunities have no "
        "distance outside the zone. They are priced with their "
        "season's called-strike rate for the count and measured "
        "against their season's count-only baseline. Check "
        "sz_top/sz_bot upstream."
    )

    opportunities.loc[no_distance, "expected_cost_per_pitch"] = (
        opportunities.loc[no_distance, "expected_cost_count_only"]
    )

if opportunities["expected_cost_per_pitch"].isna().any():
    raise RuntimeError(
        "Some opportunities with a distance have no league baseline, "
        "which should be impossible. Check the cell merge."
    )

thin_cells = league_by_cell[
    league_by_cell["league_pitches"] < THIN_CELL_WARNING_PITCHES
]

if len(thin_cells) > 0:
    print()
    print(
        f"{len(thin_cells)} (season, count, distance) cells have fewer "
        f"than {THIN_CELL_WARNING_PITCHES} pitches, so their baselines "
        "are noisy:"
    )
    print(
        thin_cells[
            [
                "game_year",
                "balls",
                "strikes",
                "distance_bucket",
                "league_pitches",
            ]
        ]
        .to_string(index=False)
    )

# Positive means this pitch went better than the league average for the
# same kind of pitch in the same count and season.
opportunities["runs_saved"] = (
    opportunities["expected_cost_per_pitch"]
    - opportunities["chase_cost"]
)


# --------------------------------------------------
# QUALIFICATION FLOORS, BY SEASON
#
# Each floor is scaled by the season's games / the longest season's games,
# so a season in progress is not emptied by the calendar. This does not
# wave small samples through: they still get larger standard errors and
# more shrinkage.
# --------------------------------------------------

season_floors = (
    opportunities
    .groupby("game_year")
    .agg(
        league_opportunities=("is_chase", "size"),
        games=("game_pk", "nunique")
    )
    .reset_index()
)

longest_season_games = int(season_floors["games"].max())

season_floors["season_share"] = (
    season_floors["games"] / longest_season_games
)

if PRORATE_FLOORS_BY_SEASON_LENGTH:
    floor_scale = season_floors["season_share"]
else:
    floor_scale = 1.0

season_floors["minimum_opportunities"] = np.round(
    MINIMUM_OPPORTUNITIES_PER_SEASON * floor_scale
).astype(int)

season_floors["minimum_plate_appearances"] = np.round(
    MINIMUM_PLATE_APPEARANCES_PER_SEASON * floor_scale
).astype(int)

show_diagnostic_header("WHAT IT TAKES TO QUALIFY, SEASON BY SEASON")

show_diagnostic()
show_diagnostic(
    season_floors[
        [
            "game_year",
            "games",
            "season_share",
            "minimum_opportunities",
            "minimum_plate_appearances",
        ]
    ]
    .round(3)
    .to_string(index=False)
)

show_detail()
show_detail(
    f"No chase minimum. cost_per_chase is only shown for hitter-seasons "
    f"with at least {MINIMUM_CHASES_FOR_COST_PER_CHASE} chases (not "
    f"scaled by season length): below that, one ball in play can move "
    f"it by a whole between-hitter standard deviation."
)

partial_seasons = season_floors[season_floors["season_share"] < 0.98]

for _, season_row in partial_seasons.iterrows():

    show_diagnostic()
    show_diagnostic(
        f"{int(season_row['game_year'])} has "
        f"{int(season_row['games']):,} games against "
        f"{longest_season_games:,} in the fullest season "
        f"({season_row['season_share']:.0%}), so its floors are "
        f"scaled to match. Read that season as a partial one."
    )


# --------------------------------------------------
# PLATE APPEARANCES PER HITTER PER SEASON
#
# Counted from every analyzable pitch in the full pitch file, so this
# includes the walk-off plate appearances dropped from the opportunities.
# --------------------------------------------------

plate_appearance_counts = (
    df[df["is_analyzable"] == 1][
        ["batter", "game_year", "game_pk", "at_bat_number"]
    ]
    .drop_duplicates()
    .groupby(["batter", "game_year"])
    .size()
    .rename("plate_appearances")
    .reset_index()
)


# --------------------------------------------------
# ONE FIXED YARDSTICK ACROSS SEASONS (THE ANCHOR)
#
# runs_saved is relative to the hitter's own season, so every season
# averages to zero and seasons cannot be compared in absolute runs. So
# every pitch is priced a second time against the anchor season's league
# baseline. The cost side does not change, only the yardstick; the gap
# between runs_saved and runs_saved_vs_anchor is the league, not the
# hitter.
# --------------------------------------------------

if ANCHOR_SEASON is None:
    anchor_season = int(opportunities["game_year"].min())
else:
    anchor_season = int(ANCHOR_SEASON)

show_diagnostic()
show_diagnostic(f"Anchor season for cross-season comparison: {anchor_season}")

anchor_by_cell = (
    league_by_cell[
        league_by_cell["game_year"] == anchor_season
    ][
        [
            "balls",
            "strikes",
            "distance_bucket",
            "expected_cost_per_pitch"
        ]
    ]
    .rename(
        columns={
            "expected_cost_per_pitch": "expected_cost_anchor"
        }
    )
)

anchor_by_count = (
    league_by_count[
        league_by_count["game_year"] == anchor_season
    ][
        ["balls", "strikes", "expected_cost_count_only"]
    ]
    .rename(
        columns={
            "expected_cost_count_only": "anchor_count_only"
        }
    )
)

opportunities = opportunities.merge(
    anchor_by_cell,
    on=["balls", "strikes", "distance_bucket"],
    how="left"
)

opportunities = opportunities.merge(
    anchor_by_count,
    on=["balls", "strikes"],
    how="left"
)

# A cell can be missing from the anchor season specifically. Fall back to
# the anchor season's count-only baseline, then to the pitch's own
# season's baseline, so nothing silently becomes NaN.
opportunities["expected_cost_anchor"] = (
    opportunities["expected_cost_anchor"]
    .fillna(opportunities["anchor_count_only"])
    .fillna(opportunities["expected_cost_per_pitch"])
)

opportunities["runs_saved_vs_anchor"] = (
    opportunities["expected_cost_anchor"]
    - opportunities["chase_cost"]
)


# --------------------------------------------------
# AGGREGATE BY HITTER AND SEASON
#
# One row per hitter per season, never one row per hitter.
# --------------------------------------------------

# Squared chase costs are summed too, so the spread of a hitter's chase
# costs (and the standard error of cost_per_chase) can be computed from
# the totals. Takes contribute 0.
opportunities["chase_cost_squared"] = opportunities["chase_cost"] ** 2

hitter_seasons = (
    opportunities
    .groupby(["batter", "game_year"])
    .agg(
        opportunities=("is_chase", "size"),
        chases=("is_chase", "sum"),
        chase_rate=("is_chase", "mean"),
        total_cost=("chase_cost", "sum"),
        chase_cost_squared=("chase_cost_squared", "sum"),
        expected_cost=("expected_cost_per_pitch", "sum"),
        expected_cost_count_only=("expected_cost_count_only", "sum"),
        expected_cost_anchor=("expected_cost_anchor", "sum"),
        mean_runs_saved=("runs_saved", "mean"),
        standard_deviation=("runs_saved", "std"),
    )
    .reset_index()
)

hitter_seasons = hitter_seasons.merge(
    plate_appearance_counts,
    on=["batter", "game_year"],
    how="left"
)

hitter_seasons["chase_rate"] *= 100


def add_cost_per_chase(table):
    """
    Add cost_per_chase and its standard error, left blank below
    MINIMUM_CHASES_FOR_COST_PER_CHASE chases. Used for both the season and
    career tables (both carry chases, total_cost and chase_cost_squared).
    """

    chases = table["chases"].astype(float)

    table["cost_per_chase"] = table["total_cost"] / chases.where(chases > 0)

    # sample variance of the individual chase costs, from the running totals
    chase_cost_variance = (
        (
            table["chase_cost_squared"]
            - table["total_cost"] ** 2 / chases.where(chases > 0)
        )
        / (chases - 1).where(chases > 1)
    )

    table["cost_per_chase_se"] = np.sqrt(
        chase_cost_variance.clip(lower=0) / chases.where(chases > 0)
    )

    too_few = chases < MINIMUM_CHASES_FOR_COST_PER_CHASE

    table.loc[too_few, ["cost_per_chase", "cost_per_chase_se"]] = np.nan

    return table


hitter_seasons = add_cost_per_chase(hitter_seasons)

# Scale from "per opportunity" to "per 600 plate appearances". A hitter
# who sees more out-of-zone pitches per plate appearance has more chances
# to gain or lose, and this carries that through.
hitter_seasons["scale_to_600_pa"] = (
    hitter_seasons["opportunities"]
    / hitter_seasons["plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
)

hitter_seasons["runs_saved_per_600_pa"] = (
    hitter_seasons["mean_runs_saved"]
    * hitter_seasons["scale_to_600_pa"]
)

# The same number against the anchor season's league. Use this column to
# compare seasons in absolute runs.
hitter_seasons["runs_saved_vs_anchor_per_600_pa"] = (
    (hitter_seasons["expected_cost_anchor"] - hitter_seasons["total_cost"])
    / hitter_seasons["plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
)

# The count-only version, for comparison only
hitter_seasons["runs_saved_count_only_per_600_pa"] = (
    (hitter_seasons["expected_cost_count_only"] - hitter_seasons["total_cost"])
    / hitter_seasons["plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
)

# Standard error of the hitter's mean, on the same scale. It treats
# pitches as independent; pitches within a plate appearance are weakly
# correlated, so this is slightly optimistic but does not change the
# ranking.
hitter_seasons["standard_error_per_600_pa"] = (
    hitter_seasons["standard_deviation"]
    / np.sqrt(hitter_seasons["opportunities"])
    * hitter_seasons["scale_to_600_pa"]
)


# --------------------------------------------------
# THE LEAGUE'S CHASE DAMAGE, AND CHASE+
#
#   chase_plus = 100 + 100 * runs saved per 600 PA
#                          / league chase cost per 600 PA
#
# The league number is every run that season's hitters lost to chasing,
# per 600 PA, over EVERY hitter-season (qualified or not), so it does not
# move with the floors. Because the baseline is built from the same
# pitches, it is also what an average hitter is expected to lose, so it is
# on the same scale as runs saved. Weighted by PA, the league averages
# exactly 100; qualified regulars sit a little above it.
#
# Chase+ is one straight line through runs saved per season, so it ranks
# hitters exactly like runs saved, and shrinking before or after the
# conversion gives the same number. (A ratio to the hitter's own expected
# damage was tested and dropped: unstable for small samples, and it only
# averages to 100 under an odd weighting.)
# --------------------------------------------------

league_chase_damage = (
    hitter_seasons
    .groupby("game_year")
    .agg(
        league_plate_appearances=("plate_appearances", "sum"),
        league_total_cost=("total_cost", "sum"),
    )
    .reset_index()
)

league_chase_damage["league_chase_cost_per_600_pa"] = (
    league_chase_damage["league_total_cost"]
    / league_chase_damage["league_plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
)

bad_scale = (
    ~np.isfinite(league_chase_damage["league_chase_cost_per_600_pa"])
    | (league_chase_damage["league_chase_cost_per_600_pa"] <= 0)
)

if bad_scale.any():
    raise RuntimeError(
        "League chase cost per 600 PA has to be positive in every "
        "season for Chase+ to mean anything. Check the pricing."
    )

hitter_seasons = hitter_seasons.merge(
    league_chase_damage[["game_year", "league_chase_cost_per_600_pa"]],
    on="game_year",
    how="left"
)

hitter_seasons["chase_plus_raw"] = (
    100
    + 100
    * hitter_seasons["runs_saved_per_600_pa"]
    / hitter_seasons["league_chase_cost_per_600_pa"]
)

hitter_seasons["chase_plus_se"] = (
    100
    * hitter_seasons["standard_error_per_600_pa"]
    / hitter_seasons["league_chase_cost_per_600_pa"]
)


# --------------------------------------------------
# WHO QUALIFIES
# --------------------------------------------------

hitter_seasons = hitter_seasons.merge(
    season_floors[
        [
            "game_year",
            "minimum_opportunities",
            "minimum_plate_appearances",
        ]
    ],
    on="game_year",
    how="left"
)

meets_the_floors = (
    (
        hitter_seasons["opportunities"]
        >= hitter_seasons["minimum_opportunities"]
    )
    & (
        hitter_seasons["plate_appearances"]
        >= hitter_seasons["minimum_plate_appearances"]
    )
    & (hitter_seasons["standard_error_per_600_pa"] > 0)
    & hitter_seasons["standard_error_per_600_pa"].notna()
)

qualified = hitter_seasons[meets_the_floors].copy()

show_diagnostic()
show_diagnostic("Hitter-seasons in the data, and how many cleared the floors:")

qualification_summary = (
    hitter_seasons
    .assign(
        qualified=meets_the_floors.astype(int),
        blank_cost_per_chase=(
            meets_the_floors
            & (hitter_seasons["chases"] < MINIMUM_CHASES_FOR_COST_PER_CHASE)
        ).astype(int),
    )
    .groupby("game_year")
    .agg(
        hitter_seasons=("batter", "size"),
        qualified=("qualified", "sum"),
        median_opportunities=("opportunities", "median"),
        qualified_with_blank_cost_per_chase=("blank_cost_per_chase", "sum"),
    )
)

show_diagnostic()
show_diagnostic(qualification_summary.to_string())


# --------------------------------------------------
# SHRINK TOWARD THE LEAGUE, WITHIN EACH SEASON
#
# Whoever has the least data is most likely to land at an extreme (the
# winner's curse). The DerSimonian-Laird estimator measures how much
# hitters really differ (tau^2), then each hitter is pulled toward the
# season's inverse-variance-weighted mean by
#
#   shrinkage_factor = SE^2 / (SE^2 + tau^2)
#
# The prior is fit one season at a time, like the baseline: the spread
# between hitters is itself a fact about a season.
# --------------------------------------------------

def estimate_between_hitter_variance(effects, standard_errors):
    """
    Returns tau squared (the real spread between hitters, with measurement
    noise removed), the inverse-variance-weighted mean, and Cochran's Q.
    """

    effects = np.asarray(effects, dtype=float)
    standard_errors = np.asarray(standard_errors, dtype=float)

    weights = 1.0 / (standard_errors ** 2)

    weighted_mean = (
        np.sum(weights * effects)
        / np.sum(weights)
    )

    q_statistic = np.sum(
        weights * (effects - weighted_mean) ** 2
    )

    k = len(effects)

    scaling = (
        np.sum(weights)
        - np.sum(weights ** 2) / np.sum(weights)
    )

    tau_squared = (q_statistic - (k - 1)) / scaling

    return max(tau_squared, 0.0), weighted_mean, q_statistic


seasons = sorted(qualified["game_year"].unique())

shrunk_seasons = []

shrinkage_rows = []

for season in seasons:

    one_season = qualified[
        qualified["game_year"] == season
    ].copy()

    tau_squared, pooled_mean, q_statistic = (
        estimate_between_hitter_variance(
            one_season["runs_saved_per_600_pa"],
            one_season["standard_error_per_600_pa"]
        )
    )

    sampling_variance = (
        one_season["standard_error_per_600_pa"] ** 2
    )

    if tau_squared > 0:

        one_season["shrinkage_factor"] = (
            sampling_variance
            / (sampling_variance + tau_squared)
        )

    else:

        # No real spread between hitters: everyone collapses to the mean
        one_season["shrinkage_factor"] = 1.0

    one_season["runs_saved_shrunk"] = (
        one_season["runs_saved_per_600_pa"]
        - one_season["shrinkage_factor"]
        * (one_season["runs_saved_per_600_pa"] - pooled_mean)
    )

    one_season["season_pooled_mean"] = pooled_mean

    # The anchored column is the same hitter with the league yardstick
    # swapped. The only noisy part is the cost of his own decisions, which
    # has just been shrunk. The swap itself (anchor baseline minus own
    # baseline over the pitches he saw) is fixed by which pitches he saw,
    # so it is added back unshrunk. In the anchor season the two shrunk
    # columns are then identical.
    one_season["runs_saved_vs_anchor_shrunk"] = (
        one_season["runs_saved_shrunk"]
        + (
            one_season["runs_saved_vs_anchor_per_600_pa"]
            - one_season["runs_saved_per_600_pa"]
        )
    )

    # Ranks are within season too.
    one_season["chase_rate_rank"] = (
        one_season["chase_rate"].rank(ascending=True)
    )

    one_season["value_rank"] = (
        one_season["runs_saved_shrunk"].rank(ascending=False)
    )

    one_season["rank_gap"] = (
        one_season["chase_rate_rank"]
        - one_season["value_rank"]
    )

    shrunk_seasons.append(one_season)

    shrinkage_rows.append(
        {
            "game_year": season,
            "hitters": len(one_season),
            "true_spread": np.sqrt(tau_squared),
            "pooled_mean": pooled_mean,
            "median_shrinkage": one_season["shrinkage_factor"].median(),
            "opportunities_vs_shrinkage": one_season["opportunities"].corr(
                one_season["shrinkage_factor"]
            ),
        }
    )

qualified = pd.concat(shrunk_seasons, ignore_index=True)

shrinkage_summary = pd.DataFrame(shrinkage_rows)

# The headline Chase+ comes from the shrunk runs saved.
qualified["chase_plus"] = (
    100
    + 100
    * qualified["runs_saved_shrunk"]
    / qualified["league_chase_cost_per_600_pa"]
)

# chase_plus_se is the standard error of the unshrunk measurement. The
# uncertainty left after shrinkage is smaller, by sqrt(1 - shrinkage_factor).
qualified["chase_plus_posterior_sd"] = (
    qualified["chase_plus_se"]
    * np.sqrt(1 - qualified["shrinkage_factor"])
)

show_diagnostic_header("HOW MUCH DO HITTERS REALLY DIFFER, SEASON BY SEASON")

show_diagnostic()
show_diagnostic(shrinkage_summary.round(3).to_string(index=False))

show_detail()
show_detail(
    "true_spread is real hitter-to-hitter difference in runs per "
    "600 PA with measurement noise taken out. A raw number far "
    "outside it is much more likely to be a small sample than a "
    "special player."
)

show_detail()
show_detail(
    "opportunities_vs_shrinkage must be negative in every season: "
    "more data has to mean less shrinkage."
)

if (shrinkage_summary["opportunities_vs_shrinkage"] > 0).any():
    print("WARNING: wrong sign somewhere. Stop and check before reading on.")


# --------------------------------------------------
# NAMES
# --------------------------------------------------

def attach_names(table, id_column="batter"):
    """
    Add a 'player' column from pybaseball's player register. If the lookup
    fails (for example with no network), print why and return the table
    unchanged.
    """

    try:

        from pybaseball import playerid_reverse_lookup

        ids = [
            int(one_id)
            for one_id in table[id_column].dropna().unique()
        ]

        lookup = playerid_reverse_lookup(ids, key_type="mlbam")

        lookup["player"] = (
            lookup["name_first"].str.title()
            + " "
            + lookup["name_last"].str.title()
        )

        # One name per id. A duplicated id in the register would otherwise
        # duplicate that hitter's rows in the merge.
        lookup = lookup.drop_duplicates(subset="key_mlbam")

        named = table.merge(
            lookup[["key_mlbam", "player"]].rename(
                columns={"key_mlbam": id_column}
            ),
            on=id_column,
            how="left",
            validate="many_to_one"
        )

        if len(named) != len(table):
            raise RuntimeError("the name merge changed the number of rows")

        return named

    except Exception as error:

        print(f"Could not look up player names ({error}).")

        return table


show_detail()
show_detail("Looking up player names...")

qualified = attach_names(qualified)

thin_chase_samples = qualified[
    qualified["chases"] < CHASE_COUNT_WARNING_BELOW
]

if len(thin_chase_samples) > 0:

    print()
    print(
        f"WARNING: {len(thin_chase_samples)} qualified hitter-season(s) "
        f"with fewer than {CHASE_COUNT_WARNING_BELOW} chases. That is "
        "below the range where the standard error was checked, so read "
        "them with extra care:"
    )
    print(
        thin_chase_samples[
            [
                column
                for column in [
                    "player",
                    "batter",
                    "game_year",
                    "opportunities",
                    "chases",
                    "standard_error_per_600_pa",
                ]
                if column in thin_chase_samples.columns
            ]
        ]
        .to_string(index=False)
    )


# --------------------------------------------------
# THE CAREER TABLE
#
# Each hitter's QUALIFIED seasons added up. Seasons that did not qualify
# are not folded in, which is why seasons_qualified is carried alongside.
# --------------------------------------------------

# The variance of a sum of independent pieces is the sum of their
# variances, so each season contributes its own squared spread.
qualified["variance_component"] = (
    (
        qualified["standard_error_per_600_pa"]
        * qualified["plate_appearances"]
        / PLATE_APPEARANCES_PER_SEASON
    )
    ** 2
)

# A career crosses several league environments, so its Chase+ scale is
# the PA-weighted average of its seasons' scales.
qualified["league_cost_x_pa"] = (
    qualified["league_chase_cost_per_600_pa"]
    * qualified["plate_appearances"]
)

career = (
    qualified
    .groupby("batter")
    .agg(
        seasons_qualified=("game_year", "nunique"),
        first_season=("game_year", "min"),
        last_season=("game_year", "max"),
        plate_appearances=("plate_appearances", "sum"),
        opportunities=("opportunities", "sum"),
        chases=("chases", "sum"),
        total_cost=("total_cost", "sum"),
        chase_cost_squared=("chase_cost_squared", "sum"),
        expected_cost=("expected_cost", "sum"),
        expected_cost_count_only=("expected_cost_count_only", "sum"),
        expected_cost_anchor=("expected_cost_anchor", "sum"),
        variance_total=("variance_component", "sum"),
        league_cost_x_pa=("league_cost_x_pa", "sum"),
    )
    .reset_index()
)

career["chase_rate"] = (
    100 * career["chases"] / career["opportunities"]
)

career = add_cost_per_chase(career)

career["runs_saved_per_600_pa"] = (
    (career["expected_cost"] - career["total_cost"])
    / career["plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
)

career["runs_saved_vs_anchor_per_600_pa"] = (
    (career["expected_cost_anchor"] - career["total_cost"])
    / career["plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
)

career["runs_saved_count_only_per_600_pa"] = (
    (career["expected_cost_count_only"] - career["total_cost"])
    / career["plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
)

career["standard_error_per_600_pa"] = (
    np.sqrt(career["variance_total"])
    / career["plate_appearances"]
    * PLATE_APPEARANCES_PER_SEASON
)

career = career[
    (career["standard_error_per_600_pa"] > 0)
    & career["standard_error_per_600_pa"].notna()
].copy()

# Career shrinkage: one prior across all career lines (the one place where
# seasons are combined).
career_tau_squared, career_mean, career_q = (
    estimate_between_hitter_variance(
        career["runs_saved_per_600_pa"],
        career["standard_error_per_600_pa"]
    )
)

career_sampling_variance = career["standard_error_per_600_pa"] ** 2

if career_tau_squared > 0:

    career["shrinkage_factor"] = (
        career_sampling_variance
        / (career_sampling_variance + career_tau_squared)
    )

else:

    career["shrinkage_factor"] = 1.0

career["runs_saved_shrunk"] = (
    career["runs_saved_per_600_pa"]
    - career["shrinkage_factor"]
    * (career["runs_saved_per_600_pa"] - career_mean)
)

# Career Chase+ on the PA-weighted league scale. This makes a career's raw
# Chase+ the average of its seasons' raw Chase+, weighted by plate
# appearances times each season's scale.
career["league_chase_cost_per_600_pa"] = (
    career["league_cost_x_pa"]
    / career["plate_appearances"]
)

career["chase_plus_raw"] = (
    100
    + 100
    * career["runs_saved_per_600_pa"]
    / career["league_chase_cost_per_600_pa"]
)

career["chase_plus"] = (
    100
    + 100
    * career["runs_saved_shrunk"]
    / career["league_chase_cost_per_600_pa"]
)

career["chase_plus_se"] = (
    100
    * career["standard_error_per_600_pa"]
    / career["league_chase_cost_per_600_pa"]
)

career["chase_plus_posterior_sd"] = (
    career["chase_plus_se"]
    * np.sqrt(1 - career["shrinkage_factor"])
)

career["chase_rate_rank"] = career["chase_rate"].rank(ascending=True)

career["value_rank"] = career["runs_saved_shrunk"].rank(ascending=False)

career["rank_gap"] = career["chase_rate_rank"] - career["value_rank"]

career = attach_names(career)

# The per-season league_cost_x_pa column stays on `qualified` a little
# longer, for the career check further down.
career = career.drop(columns=["variance_total", "league_cost_x_pa"])


# --------------------------------------------------
# LEAGUE AVERAGE
# --------------------------------------------------

show_diagnostic_header("LEAGUE AVERAGE, SEASON BY SEASON")

league_by_season = (
    opportunities
    .groupby("game_year")
    .agg(
        opportunities=("is_chase", "size"),
        chases=("is_chase", "sum"),
        total_cost=("chase_cost", "sum"),
    )
)

league_by_season["chase_rate"] = (
    100 * league_by_season["chases"] / league_by_season["opportunities"]
)

league_by_season["cost_per_chase"] = (
    league_by_season["total_cost"] / league_by_season["chases"]
)

show_diagnostic()
show_diagnostic(
    league_by_season[
        ["opportunities", "chases", "chase_rate", "cost_per_chase"]
    ]
    .round(4)
    .to_string()
)

show_detail()
show_detail(
    "That movement between seasons is exactly why each one is "
    "priced against itself. By construction the average hitter "
    "saves zero runs against the average hitter *in his own "
    "season* (every hitter-season weighted by plate appearances), "
    "so each table below is entirely about the spread around that."
)


# --------------------------------------------------
# THE CHASE+ SCALE, SEASON BY SEASON
#
# One row per season: the league's chase damage and where it came from,
# Chase+ points per run, and where the qualified hitters landed.
# league_average_chase_plus (every hitter-season, PA-weighted) must be
# 100.000.
# --------------------------------------------------

show_diagnostic_header("THE CHASE+ SCALE, SEASON BY SEASON")

spread_by_season = shrinkage_summary.set_index("game_year")

chase_plus_scale_rows = []

for season in seasons:

    everyone = hitter_seasons[hitter_seasons["game_year"] == season]
    regulars = qualified[qualified["game_year"] == season]

    scale = float(everyone["league_chase_cost_per_600_pa"].iloc[0])

    chase_plus_scale_rows.append({
        "game_year": int(season),
        "league_plate_appearances": int(everyone["plate_appearances"].sum()),
        "opportunities_per_pa": (
            everyone["opportunities"].sum()
            / everyone["plate_appearances"].sum()
        ),
        "league_chase_rate": (
            100 * everyone["chases"].sum() / everyone["opportunities"].sum()
        ),
        "league_cost_per_chase": (
            everyone["total_cost"].sum() / everyone["chases"].sum()
        ),
        "league_chase_cost_per_600_pa": scale,
        "chase_plus_points_per_run": 100 / scale,
        "runs_saved_for_110": 0.10 * scale,
        "runs_saved_for_130": 0.30 * scale,
        "league_average_chase_plus": np.average(
            everyone["chase_plus_raw"],
            weights=everyone["plate_appearances"]
        ),
        "qualified": len(regulars),
        "qualified_mean_chase_plus": regulars["chase_plus"].mean(),
        "qualified_pa_weighted_chase_plus": np.average(
            regulars["chase_plus"],
            weights=regulars["plate_appearances"]
        ),
        "qualified_median_chase_plus": regulars["chase_plus"].median(),
        "qualified_sd_chase_plus": regulars["chase_plus"].std(),
        "qualified_sd_chase_plus_raw": regulars["chase_plus_raw"].std(),
        "talent_sd_chase_plus": (
            100 * spread_by_season.loc[season, "true_spread"] / scale
        ),
        "shrink_target_chase_plus": (
            100 + 100 * spread_by_season.loc[season, "pooled_mean"] / scale
        ),
        "median_chase_plus_se": regulars["chase_plus_se"].median(),
    })

chase_plus_scale = pd.DataFrame(chase_plus_scale_rows)

show_diagnostic()
show_diagnostic(
    chase_plus_scale
    .set_index("game_year")
    .T
    .round(3)
    .to_string()
)

show_detail()
show_detail(
    "100 is the league: every hitter-season that season, weighted by "
    "plate appearances. Qualified regulars average a little above it "
    "because the part-timers who do not qualify chase worse. 130 "
    "means he saved runs worth 30% of what an average hitter lost to "
    "chasing per plate appearance that season, which is "
    "runs_saved_for_130 runs per 600 PA -- more runs in a season "
    "whose league lost more. talent_sd_chase_plus is how far apart "
    "hitters really are on this scale once measurement noise is "
    "taken out."
)


# --------------------------------------------------
# CHECKS ON THE CHASE+ SCALE
#
# Things that must hold if every piece above agrees. A failure prints a
# WARNING.
# --------------------------------------------------

chase_plus_problems = []

for season in seasons:

    season_pitches = opportunities[opportunities["game_year"] == season]

    # The baseline is built from these same pitches, so the league's runs
    # saved must add up to zero.
    league_runs_saved = (
        season_pitches["expected_cost_per_pitch"]
        - season_pitches["chase_cost"]
    ).sum()

    if abs(league_runs_saved) > 1e-6 * season_pitches["chase_cost"].sum():
        chase_plus_problems.append(
            f"{int(season)}: league runs saved add up to "
            f"{league_runs_saved:+.6f}, not zero"
        )

    regulars = qualified[qualified["game_year"] == season]

    in_value_order = regulars.sort_values("runs_saved_shrunk")["chase_plus"]

    if not in_value_order.is_monotonic_increasing:
        chase_plus_problems.append(
            f"{int(season)}: chase_plus does not rank hitters the same "
            "way runs_saved_shrunk does"
        )

    wrong_side = (
        (regulars["chase_plus"] - 100) * regulars["runs_saved_shrunk"]
        < -1e-9
    )

    if wrong_side.any():
        chase_plus_problems.append(
            f"{int(season)}: {int(wrong_side.sum())} hitters are above "
            "100 with negative runs saved, or the other way round"
        )

off_100 = (chase_plus_scale["league_average_chase_plus"] - 100).abs() > 1e-6

for _, row in chase_plus_scale[off_100].iterrows():
    chase_plus_problems.append(
        f"{int(row['game_year'])}: league average Chase+ is "
        f"{row['league_average_chase_plus']:.6f}, not 100"
    )

# A career's raw Chase+ must be the (PA x league scale)-weighted average
# of its seasons' raw Chase+.
career_check = (
    qualified
    .assign(
        weighted_chase_plus=(
            qualified["chase_plus_raw"] * qualified["league_cost_x_pa"]
        )
    )
    .groupby("batter")
    .agg(
        weighted_chase_plus=("weighted_chase_plus", "sum"),
        weights=("league_cost_x_pa", "sum"),
    )
)

career_check["expected"] = (
    career_check["weighted_chase_plus"] / career_check["weights"]
)

career_gap = (
    career.set_index("batter")["chase_plus_raw"]
    - career_check["expected"]
).abs().max()

if career_gap > 1e-9:
    chase_plus_problems.append(
        f"career raw Chase+ is off its seasons' weighted average by "
        f"up to {career_gap:.2e}"
    )

outside_0_200 = (
    (qualified["chase_plus_raw"] < 0)
    | (qualified["chase_plus_raw"] > 200)
)

if chase_plus_problems:
    print()
    for problem in chase_plus_problems:
        print(f"WARNING: {problem}")
else:
    show_diagnostic()
    show_diagnostic(
        "Chase+ checks passed: league runs saved add to zero, league "
        "Chase+ is 100.000, Chase+ and runs saved agree on order and "
        "sign, and career Chase+ is the weighted average of its seasons."
    )

show_diagnostic(
    f"Qualified hitter-seasons with a raw Chase+ outside 0 to 200: "
    f"{int(outside_0_200.sum())}"
)

qualified = qualified.drop(columns=["variance_component", "league_cost_x_pa"])


# --------------------------------------------------
# CONSOLE TABLES
#
# Display-only formatting helpers. Saved files keep their own column names
# and full precision.
# --------------------------------------------------

def player_labels(table):
    """Player names, or the batter ID wherever the name lookup failed."""

    batter_ids = table["batter"].astype(str)

    if "player" not in table.columns:
        return batter_ids

    return table["player"].fillna(batter_ids)


def format_percent(value):
    """chase_rate is already stored in percent (28.4, not 0.284)."""

    return f"{value:.1f}%"


def format_rank(rank):
    """Ranks print as whole numbers, except ties (e.g. 12.5)."""

    return f"{rank:g}"


def whole_number(values):
    """Chase+ and its SE read like wRC+, as whole numbers."""

    return values.round().astype("Int64")


def leaderboard_view(table):
    """Player | PA | Chase% | Runs Saved/600 (shrunk) | Chase+ | Chase+ SE"""

    return pd.DataFrame({
        "Player": player_labels(table),
        "PA": table["plate_appearances"],
        "Chase%": table["chase_rate"].map(format_percent),
        "Runs Saved/600 (shrunk)": table["runs_saved_shrunk"].map(
            lambda value: f"{value:+.1f}"
        ),
        "Chase+": whole_number(table["chase_plus"]),
        "Chase+ SE": whole_number(table["chase_plus_se"]),
    })


def rank_comparison_view(table):
    """Player | PA | Chase% | Chase-rate rank | Chase+ rank | Chase+ | Chase+ SE"""

    return pd.DataFrame({
        "Player": player_labels(table),
        "PA": table["plate_appearances"],
        "Chase%": table["chase_rate"].map(format_percent),
        "Chase-rate rank": table["chase_rate_rank"].map(format_rank),
        "Chase+ rank": table["value_rank"].map(format_rank),
        "Chase+": whole_number(table["chase_plus"]),
        "Chase+ SE": whole_number(table["chase_plus_se"]),
    })


def print_table(view):
    print(view.to_string(index=False))


# --------------------------------------------------
# SEASON SUMMARY
# --------------------------------------------------

print_header("SEASON SUMMARY")

season_summary = pd.DataFrame({
    "Season": chase_plus_scale["game_year"],
    "Qualified hitters": chase_plus_scale["qualified"],
    "Mean Chase+": chase_plus_scale["qualified_mean_chase_plus"].map(
        lambda value: f"{value:.1f}"
    ),
    "SD Chase+": chase_plus_scale["qualified_sd_chase_plus"].map(
        lambda value: f"{value:.1f}"
    ),
})

print()
print_table(season_summary)
print()
print(
    "Qualified-player statistics: mean and SD of Chase+ across qualified "
    "hitters only (unweighted)."
)

for _, season_row in partial_seasons.iterrows():
    print(
        f"Note: {int(season_row['game_year'])} is a partial season "
        f"({season_row['season_share']:.0%} of the fullest season's games); "
        "its qualification floors are scaled to match."
    )


# --------------------------------------------------
# THE LEADERBOARDS, ONE PER SEASON
#
# Ranked by runs_saved_shrunk (positive = fewer runs lost to chasing than
# an average hitter shown the same pitches). Chase+ ranks them identically.
# --------------------------------------------------

show_detail()
show_detail(
    "READ cost_per_chase AND standard_error_per_600_pa ALONGSIDE "
    "THE OTHER COLUMNS, NOT ON THEIR OWN:"
)
show_detail(
    "  cost_per_chase is what actually happened on the chases a "
    "hitter took. It includes contact-outcome luck (a chase that "
    "turned into a double lowers it) and it is cheap to post a low "
    "number just by chasing in easy counts. It describes his "
    "chases, it is not a skill estimate on its own. It is blank "
    f"below {MINIMUM_CHASES_FOR_COST_PER_CHASE} chases."
)
show_detail(
    "  standard_error_per_600_pa is the sampling error of the "
    "unshrunk runs_saved_per_600_pa. Two hitters whose gap is "
    "smaller than roughly one combined standard error should be "
    "read as 'not clearly different', not as a real ranking. The "
    "uncertainty left in the shrunk number is smaller: standard "
    "error x sqrt(1 - shrinkage_factor)."
)
show_detail(
    "  chase_plus is runs_saved_shrunk against the season's league: "
    "100 is league average, 130 means he saved runs worth 30% of "
    "what the average hitter lost to chasing per plate appearance "
    "that season, 80 means he gave away an extra 20%. chase_plus_se "
    "is the standard error on that scale -- usually around 14 "
    "points, so about 20 points is one combined standard error for "
    "two typical hitters and about 40 is two."
)
show_detail(
    "  Shrinkage pulls everyone toward one season-wide mean, and "
    "split-half tests show that is too strong at both ends of chase "
    "rate: the most disciplined hitters come out a few runs too low "
    "and the heaviest chasers a few runs too high. Extreme values of "
    "runs_saved_shrunk and chase_plus are, if anything, understated."
)
show_detail(
    f"  Across seasons: use chase_plus to compare how dominant "
    f"hitters were in their own seasons, and "
    f"runs_saved_vs_anchor_shrunk (the same hitter measured in runs "
    f"against {anchor_season}'s league) to compare absolute runs. "
    f"runs_saved_shrunk is for comparing hitters within one season."
)

print()
print(
    "Chase+ SE is the standard error of the unshrunk estimate, in Chase+ "
    "points; it is not the posterior uncertainty after shrinkage."
)

for season in seasons:

    one_season = qualified[
        qualified["game_year"] == season
    ].sort_values("runs_saved_shrunk", ascending=False)

    print_header(
        f"{int(season)}: BEST {LEADERBOARD_SIZE} AND WORST {LEADERBOARD_SIZE} "
        f"({len(one_season)} qualified hitters)"
    )

    print()
    print("FEWEST RUNS GIVEN AWAY BY CHASING")
    print()
    print_table(leaderboard_view(one_season.head(LEADERBOARD_SIZE)))

    print()
    print("MOST RUNS GIVEN AWAY BY CHASING")
    print()
    print_table(leaderboard_view(one_season.tail(LEADERBOARD_SIZE).iloc[::-1]))


# --------------------------------------------------
# WHAT THE TWO ADJUSTMENTS ACTUALLY DID
#
# Spread across the same qualified hitters, in runs per 600 PA:
#
#   count_only_no_shrinkage   baseline = league, same season and count
#   count_x_distance          baseline = league, same season, count AND
#                             distance bucket (runs_saved_per_600_pa)
#   count_x_distance_shrunk   the same after shrinkage
#
# Neither of the first two ignores distance: the take side of every chase
# already uses the called-strike model. (If distance ever leaves that
# model, this note and the printed one below must change.) Only the
# baseline differs between them.
#
# The difference between them (the "distance term") depends only on which
# counts and buckets a hitter's pitches fell in, never on whether he
# swung, and it sums to zero over each season's hitters weighted by PA
# (not necessarily over the qualified table). It re-prices the pitches he
# was shown; it is not noise removal, so it can widen the spread:
#
#   var(count_x_distance) - var(count_only)
#       = var(distance term) + 2 * cov(count_only, distance term)
#
# In this data it widens it, because the hitters shown the most pitches
# nowhere near the zone include the heaviest chasers. The printout reports
# the direction rather than assuming it.
#
# Shrinkage pulls every hitter toward his season's mean and never past it,
# so it is expected (not guaranteed) to narrow the spread.
# --------------------------------------------------

show_diagnostic_header("WHAT THE ADJUSTMENTS CHANGED")

adjustment_summary = (
    qualified
    .groupby("game_year")
    .agg(
        count_only_no_shrinkage=(
            "runs_saved_count_only_per_600_pa", "std"
        ),
        count_x_distance=("runs_saved_per_600_pa", "std"),
        count_x_distance_shrunk=("runs_saved_shrunk", "std"),
    )
)

show_diagnostic()
show_diagnostic("Standard deviation across qualified hitters, runs per 600 PA:")
show_diagnostic()
show_diagnostic(adjustment_summary.round(2).to_string())

show_detail()
show_detail(
    "count_only_no_shrinkage prices every pitch against what the "
    "league lost on pitches in the same season and count. It is not "
    "free of distance: the take side of every chase comes from the "
    "called-strike model, so a chase is charged less the likelier "
    "that pitch was to be called a strike. count_x_distance changes "
    "only the baseline, to the league average in the same count AND "
    "distance bucket."
)

# Average baseline change per bucket (count x bucket baseline minus
# count-only baseline). Positive means pitches in that bucket now carry
# more expected cost, so a take there earns more credit.
bucket_shift = (
    opportunities
    .assign(
        baseline_shift=(
            opportunities["expected_cost_per_pitch"]
            - opportunities["expected_cost_count_only"]
        )
    )
    .groupby(["game_year", "distance_bucket"])["baseline_shift"]
    .mean()
    .mul(100)
    .unstack("distance_bucket")
    [DISTANCE_LABELS]
)

show_diagnostic()
show_diagnostic(
    "Average change in the baseline, runs per 100 pitches, distance "
    "baseline minus count-only (positive = more credit for pitches "
    "in that bucket):"
)
show_diagnostic()
show_diagnostic(bucket_shift.round(2).to_string())

decomposition_rows = []

for season in seasons:

    one_season = qualified[qualified["game_year"] == season]

    count_only = one_season["runs_saved_count_only_per_600_pa"]
    with_distance = one_season["runs_saved_per_600_pa"]
    shrunk = one_season["runs_saved_shrunk"]
    pooled_mean = one_season["season_pooled_mean"].iloc[0]

    distance_term = with_distance - count_only

    biggest_move_at = distance_term.abs().idxmax()

    decomposition_rows.append({
        "game_year": int(season),
        "sd_distance_term": distance_term.std(),
        "corr_count_only_vs_term": count_only.corr(distance_term),
        "narrows_if_corr_below": (
            -distance_term.std() / (2 * count_only.std())
        ),
        "var_of_term": distance_term.var(),
        "two_cov_term": 2 * np.cov(count_only, distance_term)[0, 1],
        "variance_change": with_distance.var() - count_only.var(),
        "rank_corr_before_after": count_only.corr(
            with_distance,
            method="spearman"
        ),
        "rms_from_mean_raw": np.sqrt(
            ((with_distance - pooled_mean) ** 2).mean()
        ),
        "rms_from_mean_shrunk": np.sqrt(
            ((shrunk - pooled_mean) ** 2).mean()
        ),
        "largest_mover": one_season.loc[biggest_move_at].get(
            "player",
            one_season.loc[biggest_move_at, "batter"]
        ),
        "largest_move": distance_term.loc[biggest_move_at],
    })

decomposition = pd.DataFrame(decomposition_rows)

show_diagnostic()
show_diagnostic("Where the change in spread comes from, season by season:")
show_diagnostic()
show_diagnostic(decomposition.round(3).to_string(index=False))

show_detail()
show_detail(
    "sd_distance_term is how much the distance baseline moves "
    "hitters. variance_change = var_of_term + two_cov_term, exactly, "
    "so the middle column comes out narrower than the first only "
    "when corr_count_only_vs_term is below narrows_if_corr_below. "
    "rank_corr_before_after is the Spearman (rank) correlation "
    "between the two unshrunk columns: close to 1 means the distance "
    "baseline barely reorders hitters."
)

show_detail()
show_detail(
    "The distance term depends only on which counts and buckets a "
    "hitter's pitches fell in, never on whether he swung, and, "
    "weighted by plate appearances, it adds to zero over each "
    "season's hitters (not necessarily over the qualified table "
    "above). It re-prices the pitches he was shown; "
    "it is not noise removal, so it can widen the spread as well as "
    "narrow it. It widens it when it runs with the count-only "
    "numbers -- for instance when the hitters thrown the most pitches "
    "nowhere near the zone are also the ones losing the most to "
    "chasing -- and then the count-only baseline was hiding real "
    "differences, and a wider middle column is not an error."
)

show_detail()
show_detail(
    "Shrinkage is different: it moves every hitter toward his "
    "season's pooled mean and never past it, so the last column is "
    "expected to be the narrowest -- it is here, but that is not "
    "guaranteed. That step removes the part that was small samples "
    "pretending to be talent."
)

rms_grew = (
    decomposition["rms_from_mean_shrunk"]
    > decomposition["rms_from_mean_raw"]
)

if rms_grew.any():
    print(
        "WARNING: shrinkage moved hitters AWAY from their season's "
        f"mean in {decomposition.loc[rms_grew, 'game_year'].tolist()}. "
        "That cannot happen if the shrinkage factors are between 0 and 1."
    )

sd_grew = (
    (
        adjustment_summary["count_x_distance_shrunk"]
        > adjustment_summary["count_x_distance"]
    )
    | (
        adjustment_summary["count_x_distance_shrunk"]
        > adjustment_summary["count_only_no_shrinkage"]
    )
)

if sd_grew.any():
    print(
        "WARNING: the shrunk column is not the narrowest in "
        f"{[int(season) for season in adjustment_summary.index[sd_grew]]}."
    )

biggest_movers = qualified.copy()

biggest_movers["moved"] = (
    biggest_movers["runs_saved_per_600_pa"]
    - biggest_movers["runs_saved_shrunk"]
).abs()

mover_columns = [
    column
    for column in [
        "player",
        "game_year",
        "plate_appearances",
        "runs_saved_per_600_pa",
        "runs_saved_shrunk",
    ]
    if column in biggest_movers.columns
]

show_diagnostic()
show_diagnostic("HITTER-SEASONS SHRINKAGE MOVED MOST")

show_diagnostic()
show_diagnostic(
    biggest_movers
    .sort_values("moved", ascending=False)
    [mover_columns]
    .head(8)
    .round(2)
    .to_string(index=False)
)

show_detail()
show_detail(
    "These should be the seasons with the fewest plate "
    "appearances. If a full season from a regular is near the top "
    "of this list, something is wrong."
)


# --------------------------------------------------
# DOES COST TELL ANYTHING CHASE RATE DOES NOT
#
# If runs saved simply tracked chase rate, this project would be a slower
# way to compute chase rate.
# --------------------------------------------------

show_diagnostic_header("DOES COST TELL ME ANYTHING CHASE RATE DOES NOT")

show_diagnostic()
show_diagnostic("Spearman correlation between chase rate and runs saved:")
show_diagnostic()

for season in seasons:

    one_season = qualified[qualified["game_year"] == season]

    rank_correlation = (
        one_season["chase_rate"]
        .corr(one_season["runs_saved_shrunk"], method="spearman")
    )

    show_diagnostic(f"  {int(season)}: {rank_correlation:+.3f}")

show_detail()
show_detail(
    "Strongly negative is expected: chasing more should cost more. "
    "What matters is how far from -1.0 it sits, because that gap "
    "is the information chase rate does not carry."
)


# --------------------------------------------------
# CHASE RATE RANK VS CHASE+ RANK, LATEST SEASON
#
# rank_gap = chase_rate_rank - value_rank (rank 1 is best on both). The
# five largest gaps each way; the sort is the same one the tables have
# always used, so selection and tie handling are unchanged.
# --------------------------------------------------

latest_season = seasons[-1]

latest = qualified[qualified["game_year"] == latest_season]

ranked_better_by_chase_plus = (
    latest
    .sort_values("rank_gap", ascending=False)
    .head(5)
)

ranked_better_by_chase_rate = (
    latest
    .sort_values("rank_gap", ascending=True)
    .head(5)
)

print_header(f"{int(latest_season)}: CHASE RATE RANK VS CHASE+ RANK")
print()
print(
    "Players with the largest differences between their chase-rate rank "
    "and Chase+ rank."
)

print()
print("Ranked better by Chase+")
show_detail("(they chase often, and it barely costs them)")
print()
print_table(rank_comparison_view(ranked_better_by_chase_plus))

print()
print("Ranked better by chase rate")
show_detail("(they chase rarely, and it costs them anyway)")
print()
print_table(rank_comparison_view(ranked_better_by_chase_rate))


# --------------------------------------------------
# SAVE
# --------------------------------------------------

output_columns = [
    column
    for column in [
        "batter",
        "player",
        "game_year",
        "plate_appearances",
        "opportunities",
        "chases",
        "chase_rate",
        "cost_per_chase",
        "cost_per_chase_se",
        "runs_saved_per_600_pa",
        "runs_saved_shrunk",
        "standard_error_per_600_pa",
        "chase_plus",
        "chase_plus_raw",
        "chase_plus_se",
        "chase_plus_posterior_sd",
        "league_chase_cost_per_600_pa",
        "runs_saved_vs_anchor_per_600_pa",
        "runs_saved_vs_anchor_shrunk",
        "runs_saved_count_only_per_600_pa",
        "shrinkage_factor",
        "chase_rate_rank",
        "value_rank",
        "rank_gap",
        "total_cost",
        "expected_cost",
        "expected_cost_anchor",
        "mean_runs_saved",
        "standard_deviation",
        "scale_to_600_pa",
    ]
    if column in qualified.columns
]

by_season_table = (
    qualified[output_columns]
    .sort_values(
        ["game_year", "runs_saved_shrunk"],
        ascending=[True, False]
    )
)

by_season_table.to_csv(OUTPUT_BY_SEASON, index=False)

written_files = [OUTPUT_BY_SEASON]

for season in seasons:

    season_file = RESULTS_DIR / SEASON_LEADERBOARD_NAME.format(
        season=int(season)
    )

    (
        by_season_table[by_season_table["game_year"] == season]
        .to_csv(season_file, index=False)
    )

    written_files.append(season_file)

career_columns = [
    column
    for column in [
        "batter",
        "player",
        "seasons_qualified",
        "first_season",
        "last_season",
        "plate_appearances",
        "opportunities",
        "chases",
        "chase_rate",
        "cost_per_chase",
        "cost_per_chase_se",
        "runs_saved_per_600_pa",
        "runs_saved_shrunk",
        "standard_error_per_600_pa",
        "chase_plus",
        "chase_plus_raw",
        "chase_plus_se",
        "chase_plus_posterior_sd",
        "league_chase_cost_per_600_pa",
        "runs_saved_vs_anchor_per_600_pa",
        "runs_saved_count_only_per_600_pa",
        "shrinkage_factor",
        "chase_rate_rank",
        "value_rank",
        "rank_gap",
        "total_cost",
        "expected_cost",
        "expected_cost_anchor",
    ]
    if column in career.columns
]

(
    career[career_columns]
    .sort_values("runs_saved_shrunk", ascending=False)
    .to_csv(OUTPUT_CAREER, index=False)
)

written_files.append(OUTPUT_CAREER)

opportunities[
    [
        "game_pk",
        "at_bat_number",
        "pitch_number",
        "batter",
        "pitcher",
        "game_year",
        "count_state",
        "balls",
        "strikes",
        "distance_outside_zone",
        "distance_bucket",
        "is_chase",
        "called_strike_rate",
        "value_if_taken",
        "value_if_swung",
        "chase_cost",
        "expected_cost_per_pitch",
        "expected_cost_count_only",
        "expected_cost_anchor",
        "runs_saved",
        "runs_saved_vs_anchor",
    ]
].to_parquet(OUTPUT_PITCH_COSTS, index=False)

written_files.append(OUTPUT_PITCH_COSTS)

# These two are written last and carry the run fingerprint, so a results
# folder can be checked against the current script and data
# (check_chase_invariants.py does that).
chase_plus_scale.assign(run_fingerprint=RUN_FINGERPRINT).to_csv(
    OUTPUT_CHASE_PLUS_SCALE,
    index=False
)

written_files.append(OUTPUT_CHASE_PLUS_SCALE)

if called_strike_check_rows:

    (
        pd.DataFrame(called_strike_check_rows)
        .assign(run_fingerprint=RUN_FINGERPRINT)
        .to_csv(OUTPUT_CALLED_STRIKE_CHECK, index=False)
    )

    written_files.append(OUTPUT_CALLED_STRIKE_CHECK)

print()
print(
    f"Done (run fingerprint {RUN_FINGERPRINT}). Saved, overwriting the "
    f"previous run, under {PROJECT_DIR}:"
)

for path in written_files:
    print(f"  {path.relative_to(PROJECT_DIR)}")
