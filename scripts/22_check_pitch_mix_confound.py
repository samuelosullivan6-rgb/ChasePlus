"""
Pitch-mix check: does xChase+ depend on the kind of off-zone pitches a
hitter happened to see?

A diagnostic, not a pipeline step: nothing downstream reads its outputs,
and no model, baseline, leaderboard or card number is touched.

xChase+ prices every chase against the league on the same season, count
and distance bucket, so a hitter is not charged for working deep counts
or credited for being shown pitches nowhere near the zone. The baseline
does not know the pitch. A hitter shown sliders off the plate faces
harder takes than one shown fastballs there, and a pitch-quality
baseline (swing probability from pitch type, velocity and movement, in
the spirit of PitcherList's PLV) would remove that. Before one is built,
this measures how much there is to remove.

WHAT IS MEASURED

For every hitter-season on the qualified xChase+ leaderboard, from his
off-zone pitches (the opportunities step 04 prices: analyzable pitches
outside the zone), a few proxies for the pitches he faced:

  non_fastball_share    share of breaking and offspeed pitches (step
                        13's groups), with breaking_share and
                        offspeed_share alongside, in percent
  cell_chase_rate       the league's chase rate on the cells he saw,
                        pitch group x distance bucket x count x pitcher
                        hand, each cell's rate computed with his own
                        pitches left out, averaged over his pitches: the
                        chase rate an average hitter would have had on
                        his pitches, in percent
  cell_chase_rate_beyond_baseline
                        the same minus the league rate of each pitch's
                        count x distance-bucket cell (step 04's baseline
                        cell, also leaving him out): the part of the
                        pitch mix the baseline does not already remove.
                        A chase rate, where step 04's baseline is a
                        chase cost (rate x cost per chase, the called-
                        strike model on the take side), so a pitch group
                        with the same chase rate but costlier chases is
                        a confound this proxy cannot see
  mean_distance         mean distance outside the zone, feet
  mean_release_speed    mean release speed, mph

Then, one season at a time and pooled: the correlation of each proxy
with xChase+, with chase rate, and with the part of xChase+ chase rate
does not explain (what is left after a straight-line fit of xChase+ on
chase rate within the season, the residual step 06 uses), and the spread
the proxy implies: xChase+ fit as a straight line on the proxy and read
at the 90th and 10th percentile hitter, in xChase+ points, with the same
spread for the residual. One more row fits every proxy at once and
reports the 10th to 90th percentile spread of the fitted values (its
r and r² are adjusted for the number of proxies).

The pooled rows centre every proxy and xChase+ on its season first, so a
league-wide drift (velocity rising, the 2026 zone) does not read as a
hitter effect. Correlations are across qualified hitters, unweighted,
like step 06.

A correlation here is a ceiling on the confound, not the confound
itself: pitchers choose what to throw, so a hitter who chases breaking
balls is shown more of them off the plate (targeting), and strikeout-
prone hitters both see more breaking balls and chase more (hitter
type). Part of any relation is the hitter himself, which a pitch-quality
baseline would remove along with the rest.

WITHIN HITTERS: ODD AGAINST EVEN GAMES

A cross-section cannot tell the two stories apart, so the second half
of the script looks inside each hitter-season. His off-zone pitches are
split into odd and even games by game_pk (step 15's split; step 16
splits by date into a first and a second half, which would let a slump
or a mid-season adjustment into the comparison, and odd/even games
interleave so neither can). Each half gets the same proxies, with the
leave-one-hitter-out cell rates still computed on the full season, and
two outcomes: his chase rate in that half, and the runs saved over that
half's priced pitches (step 04's runs_saved per pitch) per 600 plate
appearances, in xChase+ points (100 x runs saved per 600 PA / the
league's chase cost per 600 PA). Plate appearances per half are counted
from the pitch file the way step 04 counts a season's, so the two halves
add up to the leaderboard's PA exactly. The half-season points are
unshrunk, so the cross-sectional slope on the unshrunk full-season
points (xchase_plus_raw) is the fair comparison; the slope on xChase+
itself is shown too and is smaller by about the shrinkage.

Then, per season and pooled, the odd-minus-even difference in points
(and in chase rate) is regressed on the odd-minus-even difference in
each proxy across hitter-seasons: slope, standard error, r, and the
spread it implies over the same 10th to 90th percentile proxy range the
cross-section uses. The outcome's noise scales with 1/n_odd + 1/n_even,
so a hitter near the plate-appearance floor is about twice as noisy as
a regular; every standard error reported (within and cross-sectional)
is HC1, heteroskedasticity-robust, built by hand in numpy, with the
classical ones kept in the CSV, and a second within-hitter slope weights
each hitter by 1 / (1/n_odd + 1/n_even). Scouting is the same in both
halves, so most half-to-half variation in the mix is which pitchers and
pitches he happened to draw. A within-hitter slope near the cross-
sectional slope says the mix is a confound (sliders off the plate are
hard to take); a slope near zero says the cross-section is targeting
(pitchers throw sliders off the plate to hitters who chase them) or
hitter type. The within slope is an estimate, not a bound: same-half
targeting (a chase in the second inning draws more sliders in the sixth)
pushes it toward the cross-section, lagged targeting (a chase in an odd
game draws more sliders in the next, even, game) ties the halves
together and pulls it toward zero, and neither bias can be sized here.
The spread also extrapolates that slope about three SDs past the odd-
minus-even differences, so it leans on linearity. The within-hitter SD
of each proxy difference is reported against the cross-sectional SD,
with the SD an independent draw of his own season's pitches would give,
so the narrower within-hitter range is read for what it is.

Inputs:  data/cleaned/baseline_chase_pitches.parquet
         data/cleaned/xchase_costs_by_pitch.parquet (runs_saved per
             priced pitch, joined on the keys step 13 uses)
         results/xchase/xchase_leaderboard_<season>.csv
         results/xchase/chase_cost_leaderboard_<season>.csv (a check
             that the pitches here are the ones step 04 priced, and the
             unshrunk xchase_plus_raw and runs_saved_per_600_pa)
         results/xchase/chase_plus_league_scale.csv
             (league_chase_cost_per_600_pa, the points-per-run scale)
         scripts/04_build_chase_leaderboard.py (DISTANCE_BINS and
             DISTANCE_LABELS, read with ast as step 07 does)
         scripts/13_build_actionability_profiles.py (FASTBALLS, BREAKING
             and OFFSPEED, the same way)
Outputs: results/xchase/pitch_mix_confound.csv
             one row per season (and pooled) per proxy; the pooled rows
             describe the season-centred proxy (centred = yes), so their
             mean is 0 and their percentiles are offsets from the season
         results/xchase/pitch_mix_confound_within.csv
             the within-hitter test, one row per season (and pooled) per
             proxy: the cross-sectional slopes next to the within-hitter
             slopes, standard errors, implied spreads and the SDs
         results/xchase/pitch_mix_confound.md
             the finding in plain words, both halves
"""

import ast
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent
SCRIPT_DIR = PROJECT_DIR / "scripts"
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
XCHASE_DIR = PROJECT_DIR / "results" / "xchase"

PITCH_FILE = CLEAN_DIR / "baseline_chase_pitches.parquet"
COST_FILE = CLEAN_DIR / "xchase_costs_by_pitch.parquet"
LEADERBOARD = "xchase_leaderboard_{season}.csv"
COST_LEADERBOARD = "chase_cost_leaderboard_{season}.csv"
SCALE_FILE = XCHASE_DIR / "chase_plus_league_scale.csv"
LEADERBOARD_SCRIPT = SCRIPT_DIR / "04_build_chase_leaderboard.py"
PROFILE_SCRIPT = SCRIPT_DIR / "13_build_actionability_profiles.py"
OUTPUT_CSV = XCHASE_DIR / "pitch_mix_confound.csv"
OUTPUT_WITHIN_CSV = XCHASE_DIR / "pitch_mix_confound_within.csv"
OUTPUT_MD = XCHASE_DIR / "pitch_mix_confound.md"

# The keys step 13 joins the priced pitches on.
KEYS = ["game_pk", "at_bat_number", "pitch_number", "batter", "game_year"]

PLATE_APPEARANCES_PER_SEASON = 600

# Share of off-zone pitches allowed to have no price (the walk-off plate
# appearances step 04 drops, about 0.4%), step 13's tolerance.
MAX_UNPRICED_SHARE = 0.01

# Step 04 drops the out-of-zone pitches of plate appearances with no run
# value (walk-off half innings, about 0.4% of PAs); this script keeps
# them, so a hitter's count here runs a little above step 04's (0.4% on
# average, 2.4% at most, a hitter with 635 opportunities who batted in
# several walk-off half innings).
MAX_OPPORTUNITY_GAP = 0.03

# Share of priced pitches allowed to be missing a field before the
# script stops instead of quietly averaging around the gap.
MAX_MISSING_SHARE = 0.001

PERCENTILES = (10, 90)

PROXIES = [
    "non_fastball_share",
    "breaking_share",
    "offspeed_share",
    "cell_chase_rate",
    "cell_chase_rate_beyond_baseline",
    "mean_distance",
    "mean_release_speed",
]

# The joint fit leaves out non_fastball_share, which is the sum of the
# two shares after it.
JOINT_PROXIES = [proxy for proxy in PROXIES if proxy != "non_fastball_share"]

PROXY_UNITS = {
    "non_fastball_share": "% of off-zone pitches",
    "breaking_share": "% of off-zone pitches",
    "offspeed_share": "% of off-zone pitches",
    "cell_chase_rate": "% chase rate",
    "cell_chase_rate_beyond_baseline": "% chase rate",
    "mean_distance": "ft",
    "mean_release_speed": "mph",
}

# Every proxy is the mean of one per-pitch quantity over a hitter's
# pitches; these are the per-pitch columns, used for the SD an independent
# draw of his own pitches would put on the odd-minus-even difference.
PER_PITCH = {
    "non_fastball_share": "pitch_non_fastball",
    "breaking_share": "pitch_breaking",
    "offspeed_share": "pitch_offspeed",
    "cell_chase_rate": "pitch_cell_rate",
    "cell_chase_rate_beyond_baseline": "pitch_cell_beyond",
    "mean_distance": "distance_outside_zone",
    "mean_release_speed": "release_speed",
}

for needed in (PITCH_FILE, COST_FILE, SCALE_FILE, LEADERBOARD_SCRIPT, PROFILE_SCRIPT):
    if not needed.exists():
        raise SystemExit(f"{needed.relative_to(PROJECT_DIR)} is missing.")


# --------------------------------------------------
# SETTINGS SHARED WITH STEPS 04 AND 13
# --------------------------------------------------

def read_literal_settings(script, names):
    """
    Top-level NAME = <literal> assignments of another script, read with
    ast (the way step 07 reads step 04), so the buckets and pitch groups
    here cannot drift from the ones the leaderboard and profiles use.
    """

    tree = ast.parse(script.read_text())
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in names:
                found[target.id] = ast.literal_eval(node.value)
    missing = sorted(set(names) - set(found))
    if missing:
        raise SystemExit(
            f"{script.name} has no top-level literal for {missing}."
        )
    return found


bucket_settings = read_literal_settings(
    LEADERBOARD_SCRIPT, ["DISTANCE_BINS", "DISTANCE_LABELS"]
)
DISTANCE_BINS = bucket_settings["DISTANCE_BINS"]
DISTANCE_LABELS = bucket_settings["DISTANCE_LABELS"]

group_settings = read_literal_settings(
    LEADERBOARD_SCRIPT.parent / "chase_model.py", ["FASTBALLS", "BREAKING", "OFFSPEED"]
)
FASTBALLS = set(group_settings["FASTBALLS"])
BREAKING = set(group_settings["BREAKING"])
OFFSPEED = set(group_settings["OFFSPEED"])

if FASTBALLS & BREAKING or FASTBALLS & OFFSPEED or BREAKING & OFFSPEED:
    raise SystemExit("A pitch type sits in two of step 13's groups.")

# The two cell definitions. FULL_CELL is what this script asks about;
# BASELINE_CELL is what step 04 already prices against (within a season).
BASELINE_CELL = ["balls", "strikes", "distance_bucket"]
FULL_CELL = BASELINE_CELL + ["pitch_group", "p_throws"]


# --------------------------------------------------
# LOAD
# --------------------------------------------------

pitches = pd.read_parquet(
    PITCH_FILE,
    columns=KEYS + [
        "balls", "strikes", "is_analyzable",
        "is_outside_zone", "is_chase", "distance_outside_zone",
        "pitch_type", "p_throws", "release_speed",
    ],
)

# Plate appearances per hitter, season and half (odd or even game_pk),
# counted the way step 04 counts a season's: every analyzable pitch, one
# per game and at-bat number, walk-off plate appearances included. The
# two halves therefore add up to the leaderboard's plate_appearances,
# which the season loop checks.
plate_appearances_by_half = (
    pitches.loc[pitches["is_analyzable"] == 1,
                ["batter", "game_year", "game_pk", "at_bat_number"]]
    .drop_duplicates()
)
plate_appearances_by_half["half"] = plate_appearances_by_half["game_pk"] % 2
plate_appearances_by_half = (
    plate_appearances_by_half.groupby(["batter", "game_year", "half"])
    .size()
    .rename("plate_appearances")
)

# The same filter as step 04.
opportunities = pitches[
    (pitches["is_analyzable"] == 1) & (pitches["is_outside_zone"] == 1)
].copy()
del pitches

# Step 04's price on each of these pitches, joined the way step 13 joins
# it. Every priced pitch must be one of the off-zone pitches here; the
# few here without a price are the walk-off plate appearances step 04
# drops, and they count for the proxies but not for the runs saved.
costs = pd.read_parquet(COST_FILE, columns=KEYS + ["is_chase", "runs_saved"])
if costs[KEYS].duplicated().any():
    raise SystemExit("The priced pitches hold a pitch twice.")
# A left join keeps the pitch file's row order, so the cross-sectional
# numbers above are summed in the same order as before this join existed.
opportunities = opportunities.merge(
    costs.rename(columns={"is_chase": "is_chase_priced"}),
    on=KEYS, how="left", validate="one_to_one", indicator=True,
)
if (opportunities["_merge"] == "both").sum() != len(costs):
    raise SystemExit("A priced pitch is not among the off-zone pitches here.")
del costs
unpriced_share = (opportunities["_merge"] == "left_only").mean()
if unpriced_share > MAX_UNPRICED_SHARE:
    raise SystemExit(
        f"{unpriced_share:.2%} of off-zone pitches have no price from step 04."
    )
priced = opportunities["_merge"] == "both"
if (
    opportunities.loc[priced, "is_chase_priced"] != opportunities.loc[priced, "is_chase"]
).any():
    raise SystemExit("A pitch's chase flag differs between the pitch file and its price.")
if opportunities.loc[priced, "runs_saved"].isna().any():
    raise SystemExit("A priced pitch has no runs_saved.")
opportunities = opportunities.drop(columns=["_merge", "is_chase_priced"])
opportunities["is_chase"] = opportunities["is_chase"].astype(int)
opportunities["half"] = opportunities["game_pk"] % 2

if opportunities["distance_outside_zone"].isna().any():
    raise SystemExit("Some off-zone pitches have no distance outside the zone.")
if opportunities["pitch_type"].isna().mean() > MAX_MISSING_SHARE:
    raise SystemExit("More than 0.1% of off-zone pitches have no pitch type.")
if opportunities["release_speed"].isna().mean() > MAX_MISSING_SHARE:
    raise SystemExit("More than 0.1% of off-zone pitches have no release speed.")
if not opportunities["p_throws"].isin(["R", "L"]).all():
    raise SystemExit("A pitcher hand is neither R nor L.")
if not (opportunities["balls"].between(0, 3) & opportunities["strikes"].between(0, 2)).all():
    raise SystemExit("An off-zone pitch has a count outside 0-3 balls / 0-2 strikes.")

opportunities["balls"] = opportunities["balls"].astype(int)
opportunities["strikes"] = opportunities["strikes"].astype(int)
opportunities["distance_bucket"] = pd.cut(
    opportunities["distance_outside_zone"],
    bins=DISTANCE_BINS,
    labels=DISTANCE_LABELS,
).astype(str)
if not opportunities["distance_bucket"].isin(DISTANCE_LABELS).all():
    raise SystemExit("A distance missed every bucket. Check DISTANCE_BINS in step 04.")

opportunities["pitch_group"] = np.select(
    [
        opportunities["pitch_type"].isin(FASTBALLS),
        opportunities["pitch_type"].isin(BREAKING),
        opportunities["pitch_type"].isin(OFFSPEED),
    ],
    ["fastball", "breaking", "offspeed"],
    "other",
)
other_share = (opportunities["pitch_group"] == "other").mean()
if other_share > MAX_MISSING_SHARE:
    raise SystemExit(
        f"{other_share:.2%} of off-zone pitches fall outside step 13's "
        "pitch groups. Check FASTBALLS / BREAKING / OFFSPEED."
    )

# Per-pitch versions of the share proxies, in percent, so a hitter's
# share is their mean and their variance gives the sampling SD below.
opportunities["pitch_breaking"] = 100.0 * (opportunities["pitch_group"] == "breaking")
opportunities["pitch_offspeed"] = 100.0 * (opportunities["pitch_group"] == "offspeed")
opportunities["pitch_non_fastball"] = (
    opportunities["pitch_breaking"] + opportunities["pitch_offspeed"]
)

seasons = sorted(int(season) for season in opportunities["game_year"].unique())
for season in seasons:
    for name in (LEADERBOARD, COST_LEADERBOARD):
        if not (XCHASE_DIR / name.format(season=season)).exists():
            raise SystemExit(
                f"results/xchase/{name.format(season=season)} is missing. "
                "Run step 04 with --expected-contact and step 09 first."
            )


# --------------------------------------------------
# PROXIES, ONE SEASON AT A TIME
# --------------------------------------------------

def leave_one_out_rate(table, cell):
    """
    For every (batter, cell) pair in `table`: the cell's league chase rate
    with that batter's own pitches left out, and how many of his pitches
    sit in the cell. A cell only he saw has no rate (NaN) and is dropped
    from his average.
    """

    league = (
        table.groupby(cell)["is_chase"]
        .agg(league_chases="sum", league_pitches="size")
    )
    own = (
        table.groupby(["batter"] + cell)["is_chase"]
        .agg(own_chases="sum", own_pitches="size")
        .reset_index()
        .join(league, on=cell)
    )
    others = own["league_pitches"] - own["own_pitches"]
    own["rate"] = np.where(
        others > 0,
        (own["league_chases"] - own["own_chases"]) / others.where(others > 0, 1),
        np.nan,
    )
    return own[["batter"] + cell + ["own_pitches", "rate"]]


def hitter_mean_of_cell_rates(rates, column="rate"):
    """Each hitter's average of `column` over his pitches, in percent."""

    rated = rates.dropna(subset=[column])
    weighted = (rated[column] * rated["own_pitches"]).groupby(rated["batter"]).sum()
    pitches_rated = rated.groupby("batter")["own_pitches"].sum()
    return 100 * weighted / pitches_rated


def season_cell_rates(one_season):
    """
    For every (batter, full cell) pair in a season: the cell's leave-him-
    out chase rate (rate), and the same minus the leave-him-out rate of
    its baseline cell, count x distance bucket (beyond), attached to the
    full cell so the difference is averaged over the same pitches.
    """

    full = leave_one_out_rate(one_season, FULL_CELL)
    base = leave_one_out_rate(one_season, BASELINE_CELL)
    rates = full.merge(
        base.rename(columns={"rate": "base_rate"}).drop(columns="own_pitches"),
        on=["batter"] + BASELINE_CELL,
        how="left",
        validate="many_to_one",
    )
    rates["beyond"] = rates["rate"] - rates["base_rate"]
    return rates[["batter"] + FULL_CELL + ["own_pitches", "rate", "beyond"]]


def hitter_proxies(table, cell_rates):
    """
    One row per hitter in `table` (a season's off-zone pitches, or the
    odd or even games of them): the proxies, with the cell rates taken
    from `cell_rates` (the full season's leave-one-out rates) and
    averaged over the pitches in `table`.
    """

    by_hitter = table.groupby("batter").agg(
        opportunities_here=("is_chase", "size"),
        chase_rate_here=("is_chase", "mean"),
        breaking_share=("pitch_group", lambda g: (g == "breaking").mean()),
        offspeed_share=("pitch_group", lambda g: (g == "offspeed").mean()),
        mean_distance=("distance_outside_zone", "mean"),
        mean_release_speed=("release_speed", "mean"),
    )
    by_hitter["chase_rate_here"] *= 100
    by_hitter["breaking_share"] *= 100
    by_hitter["offspeed_share"] *= 100
    by_hitter["non_fastball_share"] = (
        by_hitter["breaking_share"] + by_hitter["offspeed_share"]
    )

    seen = (
        table.groupby(["batter"] + FULL_CELL)
        .size()
        .rename("own_pitches")
        .reset_index()
        .merge(
            cell_rates.drop(columns="own_pitches"),
            on=["batter"] + FULL_CELL,
            how="left",
            validate="one_to_one",
        )
    )
    by_hitter["cell_chase_rate"] = hitter_mean_of_cell_rates(seen, "rate")
    by_hitter["cell_chase_rate_beyond_baseline"] = hitter_mean_of_cell_rates(
        seen, "beyond"
    )
    by_hitter["unrated_cell_share"] = seen["rate"].isna().groupby(seen["batter"]).mean()

    return by_hitter.reset_index()


def attach_pitch_cell_rates(one_season, cell_rates):
    """
    Each pitch's leave-him-out cell rate and its part beyond the
    baseline cell, in percent, so the two cell proxies are per-pitch
    means like the others.
    """

    with_rates = one_season.merge(
        cell_rates.drop(columns="own_pitches").rename(
            columns={"rate": "pitch_cell_rate", "beyond": "pitch_cell_beyond"}
        ),
        on=["batter"] + FULL_CELL,
        how="left",
        validate="many_to_one",
    )
    with_rates["pitch_cell_rate"] *= 100
    with_rates["pitch_cell_beyond"] *= 100
    return with_rates


def fit_line(x, y):
    """Slope and intercept of y on x."""

    slope, intercept = np.polyfit(x, y, 1)
    return slope, intercept


def correlation(x, y):
    return float(np.corrcoef(x, y)[0, 1])


def fit_robust(x, y, weights=None):
    """
    y on x by least squares with an intercept (weighted least squares
    when `weights` is given): the slope, its HC1 heteroskedasticity-
    robust standard error, its classical standard error, and r.

    The classical error assumes every hitter's outcome is equally noisy.
    It is not: the odd-minus-even difference in points or chase rate has
    a variance that scales with 1/n_odd + 1/n_even, so a hitter near the
    plate-appearance floor carries about twice the outcome variance of a
    regular, and the cross-section's points are noisier for the same
    hitters. HC1 (White's sandwich with the n / (n - k) small-sample
    factor) lets each hitter's own squared residual stand in for his
    variance, so the error is right whatever the pattern of noise.
    statsmodels is not a dependency, so it is assembled here:
    (X'WX)^-1 X' diag(w² e²) X (X'WX)^-1 times n / (n - k), with W the
    identity when unweighted.

    The intercept is kept but not reported: which games are odd is
    arbitrary, so the mean odd-minus-even gap in y has nothing to be but
    noise around 0; it costs one degree of freedom and guards against any
    asymmetry in the split. r is the plain (unweighted) correlation.
    """

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    n = len(x)
    w = np.ones(n) if weights is None else np.asarray(weights, dtype=float)
    design = np.column_stack([np.ones(n), x])
    bread = np.linalg.inv(design.T @ (design * w[:, None]))
    coefficients = bread @ (design.T @ (w * y))
    residual = y - design @ coefficients
    classical = np.sqrt((w * residual ** 2).sum() / (n - 2) * bread[1, 1])
    meat = design.T @ (design * (w ** 2 * residual ** 2)[:, None])
    robust = np.sqrt((bread @ meat @ bread)[1, 1] * n / (n - 2))
    return coefficients[1], robust, classical, correlation(x, y)


def within_summary(cross, diffs, label):
    """
    One row per proxy: the cross-sectional slopes from `cross` (one row
    per hitter; raw within a season, season-centred when pooled) next to
    the within-hitter slopes from `diffs` (one row per hitter, his
    odd-minus-even differences, centred the same way). Every spread uses
    the cross-section's 10th to 90th percentile proxy range, so the two
    slopes are read over the same hitters.
    """

    rows = []
    low, high = PERCENTILES
    if len(cross) != len(diffs):
        raise SystemExit(f"{label}: the cross-section and the halves differ in hitters.")

    for proxy in PROXIES:
        x = cross[proxy].to_numpy()
        p_low, p_high = np.percentile(x, [low, high])
        span = p_high - p_low
        d = diffs["diff_" + proxy].to_numpy()

        # Every standard error below is HC1; the classical ones ride along
        # in the CSV for comparison. The weighted within-hitter fit puts
        # weight 1 / (1/n_odd + 1/n_even) on each hitter, the inverse of
        # how his odd-minus-even outcome variance scales with his pitches,
        # so regulars count for more than hitters near the floor.
        weight = diffs["weight"].to_numpy()
        slope_plus, se_plus, _, _ = fit_robust(x, cross["xchase_plus"].to_numpy())
        slope_raw, se_raw, _, _ = fit_robust(x, cross["xchase_plus_raw"].to_numpy())
        slope_rate, se_cross_rate, _, _ = fit_robust(x, cross["chase_rate"].to_numpy())
        within_points, se_points, se_points_classical, r_points = fit_robust(
            d, diffs["diff_points"].to_numpy()
        )
        weighted_points, se_weighted_points, _, _ = fit_robust(
            d, diffs["diff_points"].to_numpy(), weight
        )
        within_rate, se_rate, se_rate_classical, r_rate = fit_robust(
            d, diffs["diff_chase_rate"].to_numpy()
        )
        weighted_rate, se_weighted_rate, _, _ = fit_robust(
            d, diffs["diff_chase_rate"].to_numpy(), weight
        )

        rows.append({
            "season": label,
            "proxy": proxy,
            "units": PROXY_UNITS[proxy],
            "centred": "yes" if label == "pooled" else "no",
            "hitters": len(diffs),
            "pitches_per_half": diffs["pitches_per_half"].mean(),
            "proxy_sd_cross": x.std(ddof=1),
            "proxy_p10_cross": p_low,
            "proxy_p90_cross": p_high,
            "proxy_diff_sd": d.std(ddof=1),
            "proxy_diff_sampling_sd": np.sqrt(
                (diffs["sampling_sd_" + proxy] ** 2).mean()
            ),
            "slope_cross_xchase_plus": slope_plus,
            "se_cross_xchase_plus": se_plus,
            "spread_cross_xchase_plus": slope_plus * span,
            "slope_cross_raw_points": slope_raw,
            "se_cross_raw_points": se_raw,
            "spread_cross_raw_points": slope_raw * span,
            "spread_cross_raw_points_se": se_raw * span,
            "slope_within_points": within_points,
            "se_within_points": se_points,
            "se_within_points_classical": se_points_classical,
            "r_within_points": r_points,
            "spread_within_points": within_points * span,
            "spread_within_points_se": se_points * span,
            "within_over_cross_points": within_points / slope_raw,
            "slope_within_points_weighted": weighted_points,
            "se_within_points_weighted": se_weighted_points,
            "spread_within_points_weighted": weighted_points * span,
            "spread_within_points_weighted_se": se_weighted_points * span,
            "slope_cross_chase_rate": slope_rate,
            "se_cross_chase_rate": se_cross_rate,
            "spread_cross_chase_rate": slope_rate * span,
            "slope_within_chase_rate": within_rate,
            "se_within_chase_rate": se_rate,
            "se_within_chase_rate_classical": se_rate_classical,
            "r_within_chase_rate": r_rate,
            "spread_within_chase_rate": within_rate * span,
            "spread_within_chase_rate_se": se_rate * span,
            "within_over_cross_chase_rate": within_rate / slope_rate,
            "slope_within_chase_rate_weighted": weighted_rate,
            "se_within_chase_rate_weighted": se_weighted_rate,
            "spread_within_chase_rate_weighted": weighted_rate * span,
            "spread_within_chase_rate_weighted_se": se_weighted_rate * span,
        })

    return rows


def summarise(table, label):
    """
    One row per proxy (plus all proxies at once) for the hitters in
    `table`, whose xchase_plus, chase_rate and xchase_residual are already
    on the scale to be compared (raw within a season, season-centred when
    pooled).
    """

    rows = []
    low, high = PERCENTILES

    for proxy in PROXIES:
        x = table[proxy].to_numpy()
        p_low, p_high = np.percentile(x, [low, high])
        slope, slope_se, _, r_plus = fit_robust(x, table["xchase_plus"].to_numpy())
        residual_slope, _ = fit_line(x, table["xchase_residual"].to_numpy())
        rows.append({
            "season": label,
            "proxy": proxy,
            "units": PROXY_UNITS[proxy],
            "centred": "yes" if label == "pooled" else "no",
            "hitters": len(table),
            "proxy_mean": x.mean(),
            "proxy_sd": x.std(ddof=1),
            "proxy_p10": p_low,
            "proxy_p90": p_high,
            "r_xchase_plus": r_plus,
            "r_chase_rate": correlation(x, table["chase_rate"]),
            "r_residual": correlation(x, table["xchase_residual"]),
            "r_squared_xchase_plus": r_plus ** 2,
            "slope_points_per_unit": slope,
            "slope_points_per_unit_se": slope_se,
            "implied_spread_points": slope * (p_high - p_low),
            "implied_spread_points_se": slope_se * (p_high - p_low),
            "residual_implied_spread_points": residual_slope * (p_high - p_low),
        })

    # Every proxy at once: least squares with an intercept. The spread is
    # the 10th to 90th percentile of the fitted values, and r_squared is
    # adjusted for the number of proxies.
    design = np.column_stack(
        [np.ones(len(table))] + [table[proxy].to_numpy() for proxy in JOINT_PROXIES]
    )
    if np.linalg.matrix_rank(design) < design.shape[1]:
        raise SystemExit(f"{label}: the joint design matrix is rank deficient.")
    row = {
        "season": label,
        "proxy": "all_proxies",
        "units": "",
        "centred": "yes" if label == "pooled" else "no",
        "hitters": len(table),
    }
    for target, spread_name, r_name in (
        ("xchase_plus", "implied_spread_points", "r_xchase_plus"),
        ("xchase_residual", "residual_implied_spread_points", "r_residual"),
    ):
        y = table[target].to_numpy()
        coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
        fitted = design @ coefficients
        r_squared = 1 - ((y - fitted) ** 2).sum() / ((y - y.mean()) ** 2).sum()
        degrees_lost = len(JOINT_PROXIES)
        adjusted = 1 - (1 - r_squared) * (len(y) - 1) / (len(y) - degrees_lost - 1)
        fitted_low, fitted_high = np.percentile(fitted, [low, high])
        row[spread_name] = fitted_high - fitted_low
        row[r_name] = np.sqrt(max(adjusted, 0.0))
        if target == "xchase_plus":
            row["r_squared_xchase_plus"] = adjusted
    rows.append(row)

    return rows


season_tables = []
summary_rows = []
difference_tables = []
within_rows = []

league_scale = pd.read_csv(SCALE_FILE).set_index("game_year")["league_chase_cost_per_600_pa"]
if league_scale.index.duplicated().any():
    raise SystemExit("chase_plus_league_scale.csv lists a season twice.")

print("Pitch-mix check, qualified hitters, one season at a time")
print(
    f"{'season':>6} {'hitters':>7} {'r(mix, xChase+)':>16} "
    f"{'r(cell rate, xChase+)':>22} {'r(beyond, resid)':>17} "
    f"{'spread cell':>11} {'spread beyond':>13} {'spread all':>10}"
)

for season in seasons:

    leaderboard = pd.read_csv(XCHASE_DIR / LEADERBOARD.format(season=season))
    cost_board = pd.read_csv(XCHASE_DIR / COST_LEADERBOARD.format(season=season))
    for board, name in ((leaderboard, LEADERBOARD), (cost_board, COST_LEADERBOARD)):
        if board["batter"].duplicated().any():
            raise SystemExit(f"{name.format(season=season)} lists a hitter twice.")
        if (board["game_year"] != season).any():
            raise SystemExit(f"{name.format(season=season)} holds another season.")

    one_season = opportunities[opportunities["game_year"] == season]
    cell_rates = season_cell_rates(one_season)
    proxies = hitter_proxies(one_season, cell_rates)

    hitters = (
        leaderboard[["batter", "player", "game_year", "plate_appearances",
                     "chase_rate", "xchase_plus"]]
        .merge(proxies, on="batter", how="left", validate="one_to_one")
        .merge(cost_board[["batter", "opportunities", "xchase_plus_raw",
                           "runs_saved_per_600_pa", "league_chase_cost_per_600_pa"]],
               on="batter", how="left", validate="one_to_one")
    )

    # Every qualified hitter must have pitches here, and about as many as
    # step 04 priced: the same opportunities, less the walk-off PAs.
    if hitters["opportunities_here"].isna().any():
        missing = hitters.loc[hitters["opportunities_here"].isna(), "player"].tolist()
        raise SystemExit(f"{season}: no off-zone pitches for {missing}.")
    if hitters["opportunities"].isna().any():
        raise SystemExit(f"{season}: a leaderboard hitter is not on the cost leaderboard.")
    gap = (hitters["opportunities_here"] - hitters["opportunities"]) / hitters["opportunities"]
    if (gap < 0).any() or (gap > MAX_OPPORTUNITY_GAP).any():
        raise SystemExit(
            f"{season}: opportunity counts differ from step 04 by "
            f"{gap.min():+.2%} to {gap.max():+.2%}; the pitches here are "
            "not the ones it priced."
        )
    # Chase rate recomputed here must match the leaderboard's to the same
    # tolerance (the dropped PAs can move it a little).
    rate_gap = (hitters["chase_rate_here"] - hitters["chase_rate"]).abs()
    if (rate_gap > 100 * MAX_OPPORTUNITY_GAP).any():
        raise SystemExit(f"{season}: chase rates do not match the leaderboard.")
    if hitters[PROXIES].isna().any().any():
        raise SystemExit(f"{season}: a proxy is missing for some hitter.")
    if (hitters["unrated_cell_share"] > 0.01).any():
        raise SystemExit(
            f"{season}: a hitter has over 1% of his cells seen by nobody else."
        )

    slope, intercept = fit_line(hitters["chase_rate"], hitters["xchase_plus"])
    hitters["xchase_residual"] = (
        hitters["xchase_plus"] - (intercept + slope * hitters["chase_rate"])
    )

    rows = summarise(hitters, str(season))
    summary_rows.extend(rows)
    season_tables.append(hitters)

    # ---- odd against even games ----
    league_cost = float(league_scale.loc[season])
    if not np.allclose(hitters["league_chase_cost_per_600_pa"], league_cost):
        raise SystemExit(
            f"{season}: the cost leaderboard's league cost per 600 PA is not "
            "the scale file's."
        )

    halves = {}
    for half in (1, 0):
        part = one_season[one_season["half"] == half]
        one_half = hitter_proxies(part, cell_rates).set_index("batter")
        one_half = one_half.join(
            part.groupby("batter")["runs_saved"].agg(
                runs_saved="sum", priced_pitches="count"
            ),
            how="left",
        )
        one_half = one_half.join(
            plate_appearances_by_half.xs((season, half), level=("game_year", "half")),
            how="left",
        )
        one_half = one_half.reindex(hitters["batter"])
        name = "odd" if half == 1 else "even"
        if (
            one_half["opportunities_here"].isna().any()
            or (one_half["priced_pitches"].fillna(0) == 0).any()
            or (one_half["plate_appearances"].fillna(0) == 0).any()
        ):
            raise SystemExit(
                f"{season}: a qualified hitter has no {name}-game pitches, "
                "prices or plate appearances."
            )
        if one_half[PROXIES].isna().any().any():
            raise SystemExit(f"{season}: a proxy is missing for a hitter's {name} games.")
        if (one_half["unrated_cell_share"] > 0.01).any():
            raise SystemExit(
                f"{season}: a hitter has over 1% of his {name}-game cells seen "
                "by nobody else."
            )
        one_half["points"] = (
            100
            * (one_half["runs_saved"] / one_half["plate_appearances"]
               * PLATE_APPEARANCES_PER_SEASON)
            / league_cost
        )
        halves[half] = one_half
    odd, even = halves[1], halves[0]

    # The halves must add back to the season: plate appearances exactly,
    # opportunities exactly, and runs saved per 600 PA (and so the unshrunk
    # xChase+) to rounding.
    season_pa = hitters["plate_appearances"].to_numpy()
    if ((odd["plate_appearances"] + even["plate_appearances"]).to_numpy() != season_pa).any():
        raise SystemExit(
            f"{season}: odd and even plate appearances do not add up to the "
            "leaderboard's."
        )
    if (
        (odd["opportunities_here"] + even["opportunities_here"]).to_numpy()
        != hitters["opportunities_here"].to_numpy()
    ).any():
        raise SystemExit(f"{season}: odd and even pitches do not add up to the season's.")
    both_runs_per_600 = (
        (odd["runs_saved"] + even["runs_saved"]).to_numpy()
        / season_pa * PLATE_APPEARANCES_PER_SEASON
    )
    if not np.allclose(both_runs_per_600, hitters["runs_saved_per_600_pa"],
                       rtol=1e-6, atol=1e-6):
        raise SystemExit(
            f"{season}: the halves' runs saved do not add up to step 04's "
            "runs_saved_per_600_pa."
        )
    if not np.allclose(100 + 100 * both_runs_per_600 / league_cost,
                       hitters["xchase_plus_raw"], rtol=1e-6, atol=1e-6):
        raise SystemExit(f"{season}: 100 + the halves' points is not xchase_plus_raw.")

    # The SD an independent draw of his own season's pitches would put on
    # each odd-minus-even difference: per-pitch variance over his season,
    # times 1/n_odd + 1/n_even.
    per_pitch = attach_pitch_cell_rates(one_season, cell_rates)
    per_pitch = per_pitch[per_pitch["batter"].isin(hitters["batter"])]
    per_pitch_variance = (
        per_pitch.groupby("batter")[list(PER_PITCH.values())]
        .var(ddof=1)
        .reindex(hitters["batter"])
    )
    draws = (1 / odd["opportunities_here"] + 1 / even["opportunities_here"]).to_numpy()

    diffs = pd.DataFrame({
        "batter": hitters["batter"].to_numpy(),
        "game_year": season,
        "pitches_per_half": (
            (odd["opportunities_here"] + even["opportunities_here"]) / 2
        ).to_numpy(),
        # 1 / (1/n_odd + 1/n_even): the weight the pitch-weighted within-
        # hitter fit gives him, the inverse of how his outcome variance
        # scales with his pitches (about half a half's pitches).
        "weight": 1 / draws,
    })
    for proxy in PROXIES:
        diffs["diff_" + proxy] = (odd[proxy] - even[proxy]).to_numpy()
        diffs["sampling_sd_" + proxy] = np.sqrt(
            per_pitch_variance[PER_PITCH[proxy]].to_numpy() * draws
        )
    diffs["diff_points"] = (odd["points"] - even["points"]).to_numpy()
    diffs["diff_chase_rate"] = (odd["chase_rate_here"] - even["chase_rate_here"]).to_numpy()
    if diffs.drop(columns=["batter", "game_year"]).isna().any().any():
        raise SystemExit(f"{season}: an odd-minus-even difference is missing.")

    within_rows.extend(within_summary(hitters, diffs, str(season)))
    difference_tables.append(diffs)

    by_proxy = {row["proxy"]: row for row in rows}
    print(
        f"{season:>6} {len(hitters):>7} "
        f"{by_proxy['non_fastball_share']['r_xchase_plus']:>16.2f} "
        f"{by_proxy['cell_chase_rate']['r_xchase_plus']:>22.2f} "
        f"{by_proxy['cell_chase_rate_beyond_baseline']['r_residual']:>17.2f} "
        f"{by_proxy['cell_chase_rate']['implied_spread_points']:>11.1f} "
        f"{by_proxy['cell_chase_rate_beyond_baseline']['implied_spread_points']:>13.1f} "
        f"{by_proxy['all_proxies']['implied_spread_points']:>10.1f}"
    )


# --------------------------------------------------
# POOLED, CENTRED ON EACH SEASON
# --------------------------------------------------

everyone = pd.concat(season_tables, ignore_index=True)
pooled = everyone.copy()
for column in PROXIES + ["xchase_plus", "xchase_plus_raw", "chase_rate"]:
    pooled[column] = pooled[column] - pooled.groupby("game_year")[column].transform("mean")
# The residual is already within-season (a straight line per season).

pooled_rows = summarise(pooled, "pooled")
summary_rows.extend(pooled_rows)

summary = pd.DataFrame(summary_rows)
summary = summary[[
    "season", "proxy", "units", "centred", "hitters", "proxy_mean", "proxy_sd",
    "proxy_p10", "proxy_p90", "r_xchase_plus", "r_chase_rate", "r_residual",
    "r_squared_xchase_plus", "slope_points_per_unit", "slope_points_per_unit_se",
    "implied_spread_points", "implied_spread_points_se",
    "residual_implied_spread_points",
]]

single = summary[summary["proxy"] != "all_proxies"].drop(
    columns=["season", "proxy", "units", "centred"]
)
if not np.isfinite(single.to_numpy(dtype=float)).all():
    raise SystemExit("A summary number is missing.")

XCHASE_DIR.mkdir(parents=True, exist_ok=True)
summary.to_csv(OUTPUT_CSV, index=False)


# --------------------------------------------------
# WITHIN HITTERS, POOLED
#
# The odd-minus-even differences centred on their season (they average
# about 0 in every season already; this removes any season-wide odd/even
# asymmetry the same way the cross-section removes league drift), fit
# against the season-centred cross-section.
# --------------------------------------------------

differences = pd.concat(difference_tables, ignore_index=True)
pooled_differences = differences.copy()
for column in [name for name in differences.columns if name.startswith("diff_")]:
    pooled_differences[column] = (
        pooled_differences[column]
        - pooled_differences.groupby("game_year")[column].transform("mean")
    )
if not (pooled["batter"].to_numpy() == pooled_differences["batter"].to_numpy()).all():
    raise SystemExit("The pooled cross-section and the pooled halves list different hitters.")

within_pooled_rows = within_summary(pooled, pooled_differences, "pooled")
within_rows.extend(within_pooled_rows)

within = pd.DataFrame(within_rows)
if not np.isfinite(
    within.drop(columns=["season", "proxy", "units", "centred"]).to_numpy(dtype=float)
).all():
    raise SystemExit("A within-hitter number is missing.")
within.to_csv(OUTPUT_WITHIN_CSV, index=False)

print()
print("Within hitters, odd minus even games: points per unit of proxy")
print("(se = HC1 robust, se_cl = classical; wtd = weighted by 1 / (1/n_odd + 1/n_even))")
print(
    f"{'season':>6} {'proxy':<32} {'cross (raw)':>11} {'se':>6} {'within':>8} "
    f"{'se':>6} {'se_cl':>6} {'wtd':>8} {'se':>6} {'ratio':>6} {'r':>6} | "
    f"{'chase rate: cross':>17} {'within':>8} {'se':>6} {'se_cl':>6}"
)
for row in within_rows:
    if row["proxy"] not in ("non_fastball_share", "cell_chase_rate_beyond_baseline",
                            "mean_distance", "mean_release_speed"):
        continue
    print(
        f"{row['season']:>6} {row['proxy']:<32} {row['slope_cross_raw_points']:>11.2f} "
        f"{row['se_cross_raw_points']:>6.2f} "
        f"{row['slope_within_points']:>8.2f} {row['se_within_points']:>6.2f} "
        f"{row['se_within_points_classical']:>6.2f} "
        f"{row['slope_within_points_weighted']:>8.2f} {row['se_within_points_weighted']:>6.2f} "
        f"{row['within_over_cross_points']:>6.2f} {row['r_within_points']:>6.2f} | "
        f"{row['slope_cross_chase_rate']:>17.3f} {row['slope_within_chase_rate']:>8.3f} "
        f"{row['se_within_chase_rate']:>6.3f} {row['se_within_chase_rate_classical']:>6.3f}"
    )


# --------------------------------------------------
# THE FINDING IN WORDS
# --------------------------------------------------

pooled_by_proxy = {row["proxy"]: row for row in pooled_rows}
xchase_sd = everyone.groupby("game_year")["xchase_plus"].std().mean()


def points_apart(value):
    """A signed spread as '16.0 points below' or '3.2 points above'."""

    return f"{abs(value):.1f} points {'below' if value < 0 else 'above'}"


def per_season(column, proxy, digits=2):
    values = [
        row[column] for row in summary_rows
        if row["proxy"] == proxy and row["season"] != "pooled"
    ]
    return ", ".join(f"{value:.{digits}f}" for value in values)


mix = pooled_by_proxy["non_fastball_share"]
cell = pooled_by_proxy["cell_chase_rate"]
beyond = pooled_by_proxy["cell_chase_rate_beyond_baseline"]
distance = pooled_by_proxy["mean_distance"]
speed = pooled_by_proxy["mean_release_speed"]
joint = pooled_by_proxy["all_proxies"]

lines = []
lines.append("# Does xChase+ depend on the pitches a hitter was shown?")
lines.append("")
lines.append(
    f"Qualified hitter-seasons, {seasons[0]}-{seasons[-1]} "
    f"({len(everyone)} in all), from `scripts/22_check_pitch_mix_confound.py`. "
    "xChase+ prices chases against the league on the same season, count "
    "and distance bucket, but not the same pitch type. This asks how much "
    "of a hitter's xChase+ follows from the kind of off-zone pitches he "
    "happened to see."
)
lines.append("")
lines.append("## The finding")
lines.append("")
lines.append(
    f"Pooled over the six seasons (each centred on its own season), the share "
    f"of breaking and offspeed pitches a hitter saw off the zone correlates "
    f"{mix['r_xchase_plus']:+.2f} with his xChase+ "
    f"(by season: {per_season('r_xchase_plus', 'non_fastball_share')}) and "
    f"{mix['r_residual']:+.2f} with the part of xChase+ chase rate does not "
    f"explain. Read as a straight line, a hitter at the 90th percentile of "
    f"non-fastball share sits {points_apart(mix['implied_spread_points'])} "
    f"one at the 10th, in xChase+ points."
)
lines.append("")
lines.append(
    f"The league's chase rate on the cells he saw (pitch group x distance "
    f"bucket x count x pitcher hand, each cell rated without his own "
    f"pitches) correlates {cell['r_xchase_plus']:+.2f} with xChase+ and "
    f"{cell['r_residual']:+.2f} with the residual; the 90th percentile "
    f"hitter in that rate sits {points_apart(cell['implied_spread_points'])} "
    f"the 10th. Most of that is count and distance, which the baseline already "
    f"removes: the part of the cell rate beyond step 04's count x distance "
    f"cell correlates {beyond['r_xchase_plus']:+.2f} with xChase+ "
    f"(by season: {per_season('r_xchase_plus', 'cell_chase_rate_beyond_baseline')}), "
    f"{beyond['r_residual']:+.2f} with the residual, and puts the 90th "
    f"percentile hitter {points_apart(beyond['implied_spread_points'])} the "
    f"10th. One caveat on that proxy: it is a chase rate, while step 04's "
    f"baseline is a chase cost (the rate times the cost of a chase, with the "
    f"called-strike model pricing the take), so a pitch group with the same "
    f"chase rate as its count x distance cell but costlier chases (more "
    f"whiffs, weaker contact) is a confound the proxy cannot see."
)
lines.append("")
lines.append(
    f"Mean distance outside the zone correlates {distance['r_xchase_plus']:+.2f} "
    f"with xChase+ (the 90th percentile hitter "
    f"{points_apart(distance['implied_spread_points'])} the 10th) and mean "
    f"release speed {speed['r_xchase_plus']:+.2f} "
    f"({points_apart(speed['implied_spread_points'])}). All the proxies fit "
    f"at once reach a multiple correlation of "
    f"{joint['r_xchase_plus']:.2f} with xChase+ (adjusted R² = "
    f"{joint['r_squared_xchase_plus']:.2f}) and a 10th to 90th percentile "
    f"spread of {joint['implied_spread_points']:.1f} points in the fitted "
    f"value, {joint['residual_implied_spread_points']:.1f} points of the "
    f"residual. For scale, xChase+ has a standard deviation of about "
    f"{xchase_sd:.0f} points across qualified hitters in a season, and each "
    f"card's ± is 7-10 points."
)
lines.append("")
lines.append(
    "These are ceilings on the confound, not the confound itself, because two "
    "other things put the same relation in a cross-section. Targeting: "
    "pitchers choose what to throw, so a hitter who chases breaking balls is "
    "shown more of them off the plate, and part of any relation is his own "
    "habit being targeted. Hitter type: strikeout-prone hitters both see more "
    "breaking balls and chase more, so the share marks the kind of hitter he "
    "is as much as the pitches he was shown. A pitch-quality baseline would "
    "remove all three."
)
lines.append("")
lines.append("## Pooled, by proxy")
lines.append("")
lines.append(
    "| Proxy | Units | Mean | 10th-90th pct | r with xChase+ | r with chase rate "
    "| r with residual | Spread, xChase+ points | Spread, residual points |"
)
lines.append("|---|---|---|---|---|---|---|---|---|")
for proxy in PROXIES:
    row = pooled_by_proxy[proxy]
    plain = everyone[proxy]
    p_low, p_high = np.percentile(plain, PERCENTILES)
    digits = 1 if proxy != "mean_distance" else 2
    lines.append(
        f"| {proxy} | {PROXY_UNITS[proxy]} | {plain.mean():.{digits}f} | "
        f"{p_low:.{digits}f} to {p_high:.{digits}f} | {row['r_xchase_plus']:+.2f} | "
        f"{row['r_chase_rate']:+.2f} | {row['r_residual']:+.2f} | "
        f"{row['implied_spread_points']:+.1f} | "
        f"{row['residual_implied_spread_points']:+.1f} |"
    )
lines.append(
    f"| all proxies at once | | | | {joint['r_xchase_plus']:.2f} (multiple, adjusted) | | "
    f"{joint['r_residual']:.2f} (multiple, adjusted) | {joint['implied_spread_points']:.1f} | "
    f"{joint['residual_implied_spread_points']:.1f} |"
)
lines.append("")
lines.append(
    "The spread is xChase+ fit as a straight line on the proxy, read at the "
    "90th percentile hitter minus the 10th; for all proxies at once (every "
    "proxy but non_fastball_share, the sum of the two shares) it is the 10th "
    "to 90th percentile of the fitted values. Pooled rows centre every "
    "value on its season first."
)
lines.append("")
lines.append("## By season")
lines.append("")
lines.append(
    "| Season | Hitters | r(non-fastball share, xChase+) | r(cell rate, xChase+) "
    "| r(beyond baseline, xChase+) | r(beyond baseline, residual) | Spread: "
    "non-fastball | Spread: cell rate | Spread: beyond baseline | Spread: all |"
)
lines.append("|---|---|---|---|---|---|---|---|---|---|")
for season in seasons:
    rows = {
        row["proxy"]: row for row in summary_rows if row["season"] == str(season)
    }
    lines.append(
        f"| {season} | {rows['all_proxies']['hitters']} | "
        f"{rows['non_fastball_share']['r_xchase_plus']:+.2f} | "
        f"{rows['cell_chase_rate']['r_xchase_plus']:+.2f} | "
        f"{rows['cell_chase_rate_beyond_baseline']['r_xchase_plus']:+.2f} | "
        f"{rows['cell_chase_rate_beyond_baseline']['r_residual']:+.2f} | "
        f"{rows['non_fastball_share']['implied_spread_points']:+.1f} | "
        f"{rows['cell_chase_rate']['implied_spread_points']:+.1f} | "
        f"{rows['cell_chase_rate_beyond_baseline']['implied_spread_points']:+.1f} | "
        f"{rows['all_proxies']['implied_spread_points']:.1f} |"
    )
lines.append("")
rows_2021 = {row["proxy"]: row for row in summary_rows if row["season"] == str(seasons[0])}
later = [
    row["r_xchase_plus"] for row in summary_rows
    if row["proxy"] == "cell_chase_rate" and row["season"] not in (str(seasons[0]), "pooled")
]
lines.append(
    f"{seasons[0]} is the weakest season on every proxy, and the cells' league "
    f"chase rate does not relate to xChase+ at all there "
    f"(r = {rows_2021['cell_chase_rate']['r_xchase_plus']:+.2f} against "
    f"{min(later):+.2f} to {max(later):+.2f} after); the check does not say why."
)
lines.append("")
# ---- within hitters ----

within_by_proxy = {row["proxy"]: row for row in within_pooled_rows}
within_by_season = {
    season: {row["proxy"]: row for row in within_rows if row["season"] == str(season)}
    for season in seasons
}


def claim(holds, sentence):
    """
    The prose below reads the numbers a particular way. If a rerun moves
    them off that reading, stop here so the wording is revisited rather
    than printed over numbers that no longer say it.
    """

    if not holds:
        raise SystemExit(f"The markdown's wording no longer holds: {sentence}.")


def plus_minus(value, error, digits=1):
    return f"{value:+.{digits}f} ± {error:.{digits}f}"


def plain_range(proxy, digits=1):
    low, high = np.percentile(everyone[proxy], PERCENTILES)
    return f"{low:.{digits}f} to {high:.{digits}f}"


share = within_by_proxy["non_fastball_share"]
beyond_w = within_by_proxy["cell_chase_rate_beyond_baseline"]
distance_w = within_by_proxy["mean_distance"]
speed_w = within_by_proxy["mean_release_speed"]

share_from_zero = abs(share["slope_within_points"] / share["se_within_points"])
share_from_cross = abs(
    (share["slope_within_points"] - share["slope_cross_raw_points"])
    / share["se_within_points"]
)
beyond_from_zero = abs(beyond_w["slope_within_points"] / beyond_w["se_within_points"])
claim(
    0.1 < share["within_over_cross_points"] < 0.5
    and share_from_zero > 2.5 and share_from_cross > 3,
    "the share's within-hitter slope on points is a fraction of the "
    "cross-section's, clear of zero and clear of the cross-section",
)
claim(
    0.1 < share["within_over_cross_chase_rate"] < 0.5,
    "the share's within-hitter slope on chase rate is a fraction of the cross-section's",
)
claim(
    0.1 < beyond_w["within_over_cross_points"] < 0.5 and beyond_from_zero > 2.5,
    "the beyond-baseline slope on points is a fraction of the cross-section's "
    "and clear of zero",
)
claim(
    0.5 < beyond_w["slope_within_chase_rate"] < 1.1
    and beyond_w["slope_cross_chase_rate"] > 2 * beyond_w["slope_within_chase_rate"],
    "the beyond-baseline chase-rate slope is near one within hitters and over "
    "twice that across them",
)
claim(
    abs(speed_w["slope_within_points"]) < 2 * speed_w["se_within_points"],
    "release speed shows nothing within hitters on points",
)
claim(
    abs(distance_w["slope_within_points"]) < 2 * distance_w["se_within_points"],
    "distance shows nothing within hitters on points",
)
claim(
    distance_w["slope_within_chase_rate"] < -3 * distance_w["se_within_chase_rate"]
    and distance_w["slope_cross_chase_rate"] > 0,
    "distance reverses sign on chase rate within hitters",
)
season_share = [within_by_season[season]["non_fastball_share"] for season in seasons]
claim(
    all(row["slope_within_points"] < 0 for row in season_share),
    "every season's within-hitter slope on the share is negative",
)
largest = max(season_share, key=lambda row: abs(row["slope_within_points"]))
largest_from_pooled = (
    abs(largest["slope_within_points"] - share["slope_within_points"])
    / largest["se_within_points"]
)
claim(largest_from_pooled < 2, "the largest season is within two standard errors of the pooled slope")

# The headline: "about X points, possibly Y". X is the pooled within-hitter
# spread on the share; Y is its upper two-standard-error edge (the larger
# of the share's and the cell rate's), which is also about where 2026
# alone sits. Y reaches the edge of a card's ± of 7-10 points, not past it.
about_points = round(abs(share["spread_within_points"]))
upper_edges = [
    abs(row["spread_within_points"]) + 2 * row["spread_within_points_se"]
    for row in (share, beyond_w)
]
lower_edge = abs(share["spread_within_points"]) - 2 * share["spread_within_points_se"]
possible_points = round(max(upper_edges))
last_season = within_by_season[seasons[-1]]
last_share, last_beyond = (
    last_season["non_fastball_share"], last_season["cell_chase_rate_beyond_baseline"]
)
claim(
    about_points == round(abs(beyond_w["spread_within_points"])) and 4 <= about_points <= 6,
    "the share and the cell rate agree on the within-hitter spread, about 5 points",
)
claim(
    7 <= possible_points <= 9 and 1 <= lower_edge <= 3,
    "the pooled spread's two-standard-error range runs from about 2 to about 8 points",
)
claim(
    all(
        abs(abs(row["spread_within_points"]) - possible_points) < 2
        for row in (last_share, last_beyond)
    ),
    f"{seasons[-1]} alone sits about where the pooled upper edge does",
)
claim(possible_points <= 10, "the possible spread reaches the edge of a card's ±, not past it")
claim(
    abs(share["slope_within_points_weighted"]) > abs(share["slope_within_points"])
    and abs(beyond_w["slope_within_points_weighted"]) > abs(beyond_w["slope_within_points"])
    and all(
        abs(row["slope_within_points_weighted"] - row["slope_within_points"])
        < row["se_within_points"]
        for row in (share, beyond_w)
    ),
    "the pitch-weighted slopes are a little larger than the unweighted ones and "
    "within one standard error of them",
)

# 2026's ratios are the highest because its cross-sectional slope is the
# smallest of the six seasons (the ABS box flattened the cross-section),
# so the denominator moved; its within-hitter slope is near the pooled one.
cross_by_season = {
    season: within_by_season[season]["non_fastball_share"]["slope_cross_raw_points"]
    for season in seasons
}
claim(
    abs(cross_by_season[seasons[-1]]) == min(abs(v) for v in cross_by_season.values())
    and last_share["within_over_cross_points"]
    == max(row["within_over_cross_points"] for row in season_share),
    f"{seasons[-1]} has the smallest cross-sectional slope on the share and the "
    "highest within / cross ratio",
)
last_from_pooled = (
    abs(last_share["slope_within_points"] - share["slope_within_points"])
    / last_share["se_within_points"]
)
claim(last_from_pooled < 2, f"{seasons[-1]}'s within-hitter slope is near the pooled one")
middle_seasons = [s for s in seasons if 2022 <= s <= 2024]
claim(
    all(abs(cross_by_season[s]) > 1.5 * abs(cross_by_season[seasons[-1]]) for s in middle_seasons),
    f"2022-2024's cross-sectional slopes are well over {seasons[-1]}'s",
)

share_structure_sd = np.sqrt(
    max(share["proxy_diff_sd"] ** 2 - share["proxy_diff_sampling_sd"] ** 2, 0.0)
)

lines.append("## Within hitters: odd against even games")
lines.append("")
lines.append(
    "A cross-section cannot say whether the mix is a confound (sliders off "
    "the plate are hard to take, so a hitter shown more of them loses points "
    "he did not earn) or targeting (pitchers throw sliders off the plate to "
    "hitters who chase them, so the mix follows the habit). This splits every "
    "qualified hitter-season into odd and even games by game_pk (the split "
    "step 15 uses; odd and even games interleave, so a slump or a mid-season "
    "change sits in both halves), recomputes each proxy on each half (the "
    "leave-one-hitter-out cell rates stay those of the full season), and "
    "takes two outcomes per half: his chase rate, and the runs saved over "
    "that half's priced pitches per 600 plate appearances in xChase+ points "
    "(100 × runs saved per 600 PA / the league's chase cost per 600 PA; "
    "plate appearances per half are counted from the pitch file the way step "
    "04 counts a season's, and the two halves add back to the leaderboard's "
    "PA, runs saved per 600 PA and unshrunk xChase+ exactly). The odd-minus-"
    "even difference in the outcome is then fit on the odd-minus-even "
    "difference in the proxy across hitter-seasons. Scouting is the same in "
    "both halves, so most of the half-to-half variation in the mix is which "
    "pitchers and pitches he happened to draw: a within-hitter slope near the "
    "cross-sectional slope says confound, a slope near zero says targeting or "
    "hitter type, with two caveats that pull opposite ways (below). The "
    "half-season points are unshrunk, so the cross-sectional slope to compare "
    "is the one on the unshrunk full-season points (xchase_plus_raw); on "
    "xChase+ itself the cross-sectional slopes are about 0.8 times as large, "
    "the shrinkage. Every standard error here is HC1, robust to the unequal "
    "noise across hitters (a hitter near the plate-appearance floor carries "
    "about twice the odd-minus-even outcome variance of a regular)."
)
lines.append("")
lines.append(
    f"**The within-hitter slopes sit much nearer zero than the cross-section's, "
    f"but not at zero for the pitch mix.** Pooled over the six seasons, the "
    f"within-hitter slope of points on non-fastball share is "
    f"{plus_minus(share['slope_within_points'], share['se_within_points'], 2)} "
    f"points per percentage point against {share['slope_cross_raw_points']:+.2f} "
    f"across hitters ({share['slope_cross_xchase_plus']:+.2f} on xChase+): "
    f"{share['within_over_cross_points']:.0%} of the cross-sectional slope, "
    f"{share_from_zero:.1f} standard errors from zero and {share_from_cross:.0f} "
    f"from the cross-section. Over the cross-section's 10th to 90th percentile "
    f"range of the share ({plain_range('non_fastball_share')}%), that is "
    f"{plus_minus(share['spread_within_points'], share['spread_within_points_se'])} "
    f"points within hitters against {share['spread_cross_raw_points']:+.1f} "
    f"across them ({share['spread_cross_xchase_plus']:+.1f} on xChase+). "
    f"Weighting each hitter by his pitches (1 / (1/n_odd + 1/n_even), so a "
    f"regular counts for more than a hitter at the floor) moves the slope to "
    f"{plus_minus(share['slope_within_points_weighted'], share['se_within_points_weighted'], 2)} "
    f"({plus_minus(share['spread_within_points_weighted'], share['spread_within_points_weighted_se'])} "
    f"over the range). Chase rate reads the same: "
    f"{plus_minus(share['slope_within_chase_rate'], share['se_within_chase_rate'], 3)} "
    f"chase-rate points per percentage point within hitters against "
    f"{share['slope_cross_chase_rate']:+.3f} across them "
    f"({share['within_over_cross_chase_rate']:.0%}). The part of the cell chase "
    f"rate beyond the baseline cell gives the same picture: "
    f"{beyond_w['within_over_cross_points']:.0%} of its cross-sectional slope on "
    f"points ({plus_minus(beyond_w['spread_within_points'], beyond_w['spread_within_points_se'])} "
    f"against {beyond_w['spread_cross_raw_points']:+.1f} points over its 10th to "
    f"90th range; "
    f"{plus_minus(beyond_w['spread_within_points_weighted'], beyond_w['spread_within_points_weighted_se'])} "
    f"weighted), {beyond_w['within_over_cross_chase_rate']:.0%} on chase rate. "
    f"Its within-hitter chase-rate slope, "
    f"{plus_minus(beyond_w['slope_within_chase_rate'], beyond_w['se_within_chase_rate'], 2)}, "
    f"is close to the 1.0 an additive cell effect would give (his chase rate "
    f"moving one for one with the league's rate on the cells he saw), while "
    f"the cross-sectional {beyond_w['slope_cross_chase_rate']:.2f} is more than "
    f"twice that: the cells are as hard as the league says, and the hitters "
    f"who see the hard ones chase more than the cells explain."
)
lines.append("")
lines.append(
    f"Mean release speed and mean distance show nothing within hitters on "
    f"points: "
    f"{plus_minus(speed_w['spread_within_points'], speed_w['spread_within_points_se'])} "
    f"points over the speed range against {speed_w['spread_cross_raw_points']:+.1f} "
    f"across hitters, and "
    f"{plus_minus(distance_w['spread_within_points'], distance_w['spread_within_points_se'])} "
    f"over the distance range against {distance_w['spread_cross_raw_points']:+.1f}. "
    f"On chase rate, distance reverses sign: within a hitter, a half with "
    f"pitches further off the plate has the lower chase rate "
    f"({plus_minus(distance_w['spread_within_chase_rate'], distance_w['spread_within_chase_rate_se'])} "
    f"chase-rate points over the range), while across hitters the ones pitched "
    f"further off the plate chase more ({distance_w['spread_cross_chase_rate']:+.1f}). "
    f"That is targeting in its plainest form, pitchers going further off the "
    f"plate against hitters who will chase, and the baseline already prices "
    f"the distance, so it leaves no mark on points."
)
lines.append("")
lines.append(
    f"Read together: about {share['within_over_cross_points']:.0%} to "
    f"{beyond_w['within_over_cross_points']:.0%} of the cross-sectional relation "
    f"between the pitch mix and xChase+ survives within hitters, so most of "
    f"what the cross-section shows is targeting or hitter type, and the "
    f"confound a pitch-quality baseline would remove is about {about_points} "
    f"points between the 10th and 90th percentile hitters in the mix, possibly "
    f"{possible_points}: the pooled spread runs from about {lower_edge:.0f} to "
    f"{max(upper_edges):.0f} points at two standard errors "
    f"({plus_minus(share['spread_within_points'], share['spread_within_points_se'])} "
    f"on the share, "
    f"{plus_minus(beyond_w['spread_within_points'], beyond_w['spread_within_points_se'])} "
    f"by the cell rate), and {seasons[-1]} alone reads "
    f"{plus_minus(last_share['spread_within_points'], last_share['spread_within_points_se'])} "
    f"and "
    f"{plus_minus(last_beyond['spread_within_points'], last_beyond['spread_within_points_se'])}. "
    f"That reaches the edge of a card's ± of 7-10 points rather than sitting "
    f"inside it."
)
lines.append("")
lines.append(
    "The within-hitter slope is an estimate of the confound, not a bound on "
    "it, because two biases of unknown size pull it opposite ways. Same-half "
    "targeting pushes it toward the cross-section: a pitcher who sees a hitter "
    "chase a slider in the second inning throws him more in the sixth, and "
    "both land in the same half, so part of a half's extra sliders is the "
    "half's own chasing. Lagged targeting pulls it toward zero: a hitter who "
    "chases sliders in an odd game is thrown more of them in the next, even, "
    "game, which ties the halves' mixes to each other's outcomes and "
    "attenuates the odd-minus-even relation. The check cannot size either, so "
    "the slope sits somewhere between them."
)
lines.append("")
lines.append(
    f"Every season's within-hitter slope on the share is negative "
    f"({', '.join(f'{row['slope_within_points']:+.2f}' for row in season_share)}, "
    f"standard errors {min(row['se_within_points'] for row in season_share):.2f} "
    f"to {max(row['se_within_points'] for row in season_share):.2f}); "
    f"{largest['season']} is the largest and sits {largest_from_pooled:.1f} "
    f"standard errors from the pooled value, so no season stands apart. "
    f"{seasons[-1]}'s within / cross ratios "
    f"({last_share['within_over_cross_points']:.2f} on the share, "
    f"{last_beyond['within_over_cross_points']:.2f} by the cell rate) are the "
    f"highest mainly because the denominator moved, not the numerator: its "
    f"cross-sectional slope on the share, "
    f"{plus_minus(cross_by_season[seasons[-1]], last_share['se_cross_raw_points'], 2)} "
    f"points per percentage point, is the smallest of the six seasons against "
    f"{max(cross_by_season[s] for s in middle_seasons):+.2f} to "
    f"{min(cross_by_season[s] for s in middle_seasons):+.2f} in "
    f"{middle_seasons[0]}-{middle_seasons[-1]}, most likely the ABS box "
    f"flattening the cross-section (the shorter zone made more takes "
    f"chases on every pitch type), while its within-hitter slope is the "
    f"ordinary {last_from_pooled:.1f} standard errors from the pooled value."
)
lines.append("")
lines.append(
    f"Noise in the differences. The odd-minus-even difference in non-fastball "
    f"share has a standard deviation of {share['proxy_diff_sd']:.1f} percentage "
    f"points across hitter-seasons, against {share['proxy_sd_cross']:.1f} for "
    f"the share itself across hitters, and {share['proxy_diff_sampling_sd']:.1f} "
    f"of it is what an independent draw of his own season's pitches would give "
    f"(the rest, about {share_structure_sd:.1f}, is which pitchers he drew). The "
    f"within-hitter range is the narrower, so the within-hitter slope is the "
    f"less precise, and its standard error is what the spreads above carry. But "
    f"the pitches a half happened to hold are the pitches he had to take or "
    f"chase, so that variation is the treatment itself, not measurement error "
    f"in it, and the slope is not attenuated by it; the same holds for the "
    f"other proxies (SDs in the last table). The outcome side is noisier for "
    f"some hitters than others (its variance scales with 1/n_odd + 1/n_even), "
    f"so the standard errors are HC1, heteroskedasticity-robust; on the pooled "
    f"share they come to {share['se_within_points']:.3f} against a classical "
    f"{share['se_within_points_classical']:.3f} ({beyond_w['se_within_points']:.2f} "
    f"against {beyond_w['se_within_points_classical']:.2f} by the cell rate), "
    f"and the classical ones stay in the CSV."
)
lines.append("")
lines.append("### Pooled, by proxy")
lines.append("")
lines.append(
    "| Proxy | 10th-90th pct | Cross spread, xChase+ | Cross spread, unshrunk ± SE | "
    "Within spread ± SE | Weighted within spread ± SE | Within / cross | "
    "Cross chase-rate spread | Within chase-rate spread ± SE | Within / cross |"
)
lines.append("|---|---|---|---|---|---|---|---|---|---|")
for proxy in PROXIES:
    row = within_by_proxy[proxy]
    digits = 1 if proxy != "mean_distance" else 2
    ratio_points = (
        f"{row['within_over_cross_points']:.2f}"
        if abs(row["spread_cross_raw_points"]) >= 5 else "–"
    )
    ratio_rate = (
        f"{row['within_over_cross_chase_rate']:.2f}"
        if abs(row["spread_cross_chase_rate"]) >= 2 else "–"
    )
    lines.append(
        f"| {proxy} | {plain_range(proxy, digits)} | "
        f"{row['spread_cross_xchase_plus']:+.1f} | "
        f"{plus_minus(row['spread_cross_raw_points'], row['spread_cross_raw_points_se'])} | "
        f"{plus_minus(row['spread_within_points'], row['spread_within_points_se'])} | "
        f"{plus_minus(row['spread_within_points_weighted'], row['spread_within_points_weighted_se'])} | "
        f"{ratio_points} | {row['spread_cross_chase_rate']:+.1f} | "
        f"{plus_minus(row['spread_within_chase_rate'], row['spread_within_chase_rate_se'])} | "
        f"{ratio_rate} |"
    )
lines.append("")
share_span = share["proxy_p90_cross"] - share["proxy_p10_cross"]
lines.append(
    f"Spreads are the slope times the cross-section's 10th to 90th percentile "
    f"range of the proxy, in xChase+ points (chase-rate points in the last "
    f"three columns); the ratio is the within-hitter slope over the cross-"
    f"sectional slope on the unshrunk points (on chase rate), left blank where "
    f"the cross-sectional spread is under 5 points (2 chase-rate points) and "
    f"the ratio would mean nothing. Standard errors are HC1; the weighted "
    f"column fits with weight 1 / (1/n_odd + 1/n_even) per hitter. Note that "
    f"the within-hitter spread reads a straight line well past the data: the "
    f"share's cross-sectional range is {share_span:.1f} percentage points "
    f"while its odd-minus-even difference has a standard deviation of "
    f"{share['proxy_diff_sd']:.1f}, so the spread extrapolates the within-"
    f"hitter slope about {share_span / share['proxy_diff_sd']:.0f} SDs out "
    f"from where the differences sit, and linearity is doing that work. "
    f"Pooled rows centre every difference on its season."
)
lines.append("")
lines.append("### By season")
lines.append("")
lines.append(
    "| Season | Hitters | Pitches per half | Share: cross slope ± SE | "
    "Share: within slope ± SE | Share: within / cross | "
    "Beyond baseline: cross slope ± SE | Beyond baseline: within slope ± SE | "
    "Beyond baseline: within / cross | Share, chase rate: within / cross | "
    "Beyond baseline, chase rate: within / cross |"
)
lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
for season in seasons:
    rows = within_by_season[season]
    s_row = rows["non_fastball_share"]
    b_row = rows["cell_chase_rate_beyond_baseline"]
    lines.append(
        f"| {season} | {s_row['hitters']} | {s_row['pitches_per_half']:.0f} | "
        f"{plus_minus(s_row['slope_cross_raw_points'], s_row['se_cross_raw_points'], 2)} | "
        f"{plus_minus(s_row['slope_within_points'], s_row['se_within_points'], 2)} | "
        f"{s_row['within_over_cross_points']:.2f} | "
        f"{plus_minus(b_row['slope_cross_raw_points'], b_row['se_cross_raw_points'], 1)} | "
        f"{plus_minus(b_row['slope_within_points'], b_row['se_within_points'], 1)} | "
        f"{b_row['within_over_cross_points']:.2f} | "
        f"{s_row['within_over_cross_chase_rate']:.2f} | "
        f"{b_row['within_over_cross_chase_rate']:.2f} |"
    )
lines.append("")
lines.append(
    "Slopes are xChase+ points per percentage point of the proxy (the cross "
    "slope on the unshrunk points), standard errors HC1; the ratios are the "
    "within slope over that season's cross slope (on chase rate)."
)
lines.append("")
lines.append("### How much the proxies move between halves")
lines.append("")
lines.append(
    "| Proxy | Units | SD across hitters | SD of odd minus even | Of which the "
    "pitch draw alone |"
)
lines.append("|---|---|---|---|---|")
for proxy in PROXIES:
    row = within_by_proxy[proxy]
    digits = 2 if proxy != "mean_distance" else 3
    lines.append(
        f"| {proxy} | {PROXY_UNITS[proxy]} | {row['proxy_sd_cross']:.{digits}f} | "
        f"{row['proxy_diff_sd']:.{digits}f} | {row['proxy_diff_sampling_sd']:.{digits}f} |"
    )
lines.append("")
lines.append(
    "The last column is the SD an independent draw of each hitter's own "
    "season's pitches would put on his odd-minus-even difference (his per-"
    "pitch variance times 1/n_odd + 1/n_even, root-mean-squared over "
    "hitters); what the middle column has beyond it is which pitchers the "
    "halves happened to hold."
)
lines.append("")
lines.append(
    "Full numbers, every proxy and season, in `pitch_mix_confound.csv` "
    "(the cross-section) and `pitch_mix_confound_within.csv` (the within-"
    "hitter test)."
)
lines.append("")

OUTPUT_MD.write_text("\n".join(lines))

print()
print("Pooled (centred on each season):")
for proxy in PROXIES + ["all_proxies"]:
    row = pooled_by_proxy[proxy]
    print(
        f"  {proxy:<32} r(xChase+) {row['r_xchase_plus']:+.2f}  "
        f"r(residual) {row['r_residual']:+.2f}  "
        f"spread {row['implied_spread_points']:+.1f} pts  "
        f"(residual {row['residual_implied_spread_points']:+.1f})"
    )
print()
print(f"Saved {OUTPUT_CSV.relative_to(PROJECT_DIR)}")
print(f"Saved {OUTPUT_WITHIN_CSV.relative_to(PROJECT_DIR)}")
print(f"Saved {OUTPUT_MD.relative_to(PROJECT_DIR)}")
