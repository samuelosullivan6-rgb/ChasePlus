"""
Invariant checks for the chase leaderboard outputs.

Checks what has to be true if every part of 04_build_chase_leaderboard.py agrees
with every other part. It only reads what that script wrote (plus the
cleaned pitch file for plate appearance counts), and rebuilds the key
numbers from the pitch level instead of trusting the leaderboard's own
arithmetic.

    python scripts/07_check_chase_invariants.py           run all checks
    python scripts/07_check_chase_invariants.py --rerun   also rerun the
        leaderboard script and check it writes byte-identical files
    python scripts/07_check_chase_invariants.py --expected-contact
        the same checks on the xChase+ run (results/xchase/ and
        data/cleaned/xchase_costs_by_pitch.parquet); add --rerun too to
        rerun 04_build_chase_leaderboard.py --expected-contact

Every check is a plain function named test_..., so pytest can collect this
file too, but pytest is not required.

The settings (floors, the cost-per-chase minimum, bucket names, ...) are
read straight out of 04_build_chase_leaderboard.py with the ast module, so the
two files can never disagree about the rules.
"""

import ast
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

SCRIPT_DIR = Path(__file__).resolve().parent
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
RESULTS_DIR = PROJECT_DIR / "results"

LEADERBOARD_SCRIPT = SCRIPT_DIR / "04_build_chase_leaderboard.py"

# Which run to check. The xChase+ run keeps its outputs in results/xchase/
# and its pitch table in xchase_costs_by_pitch.parquet; the run value
# tables and the cleaned pitch file are shared by both runs.
EXPECTED_CONTACT = "--expected-contact" in sys.argv

if EXPECTED_CONTACT:
    OUTPUT_DIR = RESULTS_DIR / "xchase"
    PITCH_COSTS = CLEAN_DIR / "xchase_costs_by_pitch.parquet"
else:
    OUTPUT_DIR = RESULTS_DIR
    PITCH_COSTS = CLEAN_DIR / "chase_costs_by_pitch.parquet"

PITCH_FILE = CLEAN_DIR / "baseline_chase_pitches.parquet"
PA_VALUE_FILE = CLEAN_DIR / "plate_appearance_run_values.parquet"
HITTER_VALUE = OUTPUT_DIR / "hitter_value_leaderboard.csv"
RELIABILITY = OUTPUT_DIR / "chase_value_reliability.csv"
BY_SEASON = OUTPUT_DIR / "chase_cost_leaderboard_by_season.csv"
CAREER = OUTPUT_DIR / "chase_cost_leaderboard.csv"
SCALE = OUTPUT_DIR / "chase_plus_league_scale.csv"
CALLED_STRIKE_CHECK = OUTPUT_DIR / "called_strike_model_check.csv"
COUNT_VALUES = RESULTS_DIR / "run_value_by_count.csv"
EVENT_VALUES = RESULTS_DIR / "run_value_by_event.csv"

# Floating point slack for "equal"
TOLERANCE = 1e-8


def read_results(path):
    """
    Read a results CSV. The xChase+ run saves its Chase+ columns as
    xchase_plus, xchase_plus_se, ...; they are read back under the
    chase_plus names so every check below works on either run.
    """

    table = pd.read_csv(path)

    if EXPECTED_CONTACT:
        table = table.rename(
            columns=lambda name: name.replace("xchase_plus", "chase_plus")
        )

    return table


def read_settings(names):
    """
    Read top-level literal assignments (NAME = <literal>) out of the
    leaderboard script without running it.
    """

    tree = ast.parse(LEADERBOARD_SCRIPT.read_text())
    found = {}

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in names:
                found[target.id] = ast.literal_eval(node.value)

    missing = set(names) - set(found)

    if missing:
        raise RuntimeError(
            f"Could not find {sorted(missing)} in {LEADERBOARD_SCRIPT.name}"
        )

    return found


SETTINGS = read_settings([
    "MINIMUM_OPPORTUNITIES_PER_SEASON",
    "MINIMUM_PLATE_APPEARANCES_PER_SEASON",
    "MINIMUM_CHASES_FOR_COST_PER_CHASE",
    "PRORATE_FLOORS_BY_SEASON_LENGTH",
    "PLATE_APPEARANCES_PER_SEASON",
    "DISTANCE_LABELS",
    "ANCHOR_SEASON",
    "RUN_OUT_OF_FOLD_CHECK",
    "CALLED_STRIKE_DISTANCE_KNOTS",
    "OUT_OF_FOLD_SPLITS",
    "OUT_OF_FOLD_SEED",
    "OUT_OF_FOLD_GAP_SHARE_OF_OPTIMISM",
])

PER_PA = SETTINGS["PLATE_APPEARANCES_PER_SEASON"]


# --------------------------------------------------
# LOADING, ONCE
# --------------------------------------------------

_cache = {}


def pitches():
    if "pitches" not in _cache:
        _cache["pitches"] = pd.read_parquet(PITCH_COSTS)
    return _cache["pitches"]


def plate_appearances():
    """Analyzable plate appearances per (batter, game_year)."""

    if "pa" not in _cache:
        raw = pd.read_parquet(
            PITCH_FILE,
            columns=["batter", "game_year", "game_pk", "at_bat_number", "is_analyzable"]
        )
        _cache["pa"] = (
            raw[raw["is_analyzable"] == 1][["batter", "game_year", "game_pk", "at_bat_number"]]
            .drop_duplicates()
            .groupby(["batter", "game_year"])
            .size()
            .rename("plate_appearances")
            .reset_index()
        )
    return _cache["pa"]


def by_season():
    if "by_season" not in _cache:
        _cache["by_season"] = read_results(BY_SEASON)
    return _cache["by_season"]


def career():
    if "career" not in _cache:
        _cache["career"] = read_results(CAREER)
    return _cache["career"]


def rebuilt_hitter_seasons():
    """
    Every hitter-season rebuilt from the pitch level: totals, runs saved,
    standard error, and the league scale for Chase+.
    """

    if "rebuilt" in _cache:
        return _cache["rebuilt"]

    table = pitches().assign(
        runs_saved_check=lambda frame: frame["expected_cost_per_pitch"] - frame["chase_cost"]
    )

    hitters = (
        table
        .groupby(["batter", "game_year"])
        .agg(
            opportunities=("is_chase", "size"),
            chases=("is_chase", "sum"),
            total_cost=("chase_cost", "sum"),
            expected_cost=("expected_cost_per_pitch", "sum"),
            expected_cost_count_only=("expected_cost_count_only", "sum"),
            spread=("runs_saved_check", "std"),
        )
        .reset_index()
    )

    hitters = hitters.merge(plate_appearances(), on=["batter", "game_year"], how="left")

    hitters["runs_saved_per_600_pa"] = (
        (hitters["expected_cost"] - hitters["total_cost"]) / hitters["plate_appearances"] * PER_PA
    )

    hitters["runs_saved_count_only_per_600_pa"] = (
        (hitters["expected_cost_count_only"] - hitters["total_cost"])
        / hitters["plate_appearances"] * PER_PA
    )

    hitters["standard_error_per_600_pa"] = (
        hitters["spread"] / np.sqrt(hitters["opportunities"])
        * hitters["opportunities"] / hitters["plate_appearances"] * PER_PA
    )

    league = (
        hitters
        .groupby("game_year")
        .agg(total_cost=("total_cost", "sum"), plate_appearances=("plate_appearances", "sum"))
    )

    league["scale"] = league["total_cost"] / league["plate_appearances"] * PER_PA

    hitters = hitters.merge(
        league[["scale"]].reset_index(),
        on="game_year",
        how="left"
    )

    hitters["chase_plus_raw"] = 100 + 100 * hitters["runs_saved_per_600_pa"] / hitters["scale"]

    _cache["rebuilt"] = hitters
    return hitters


def dersimonian_laird(effects, standard_errors):
    """Between-hitter variance and the inverse-variance-weighted mean."""

    effects = np.asarray(effects, dtype=float)
    weights = 1.0 / np.asarray(standard_errors, dtype=float) ** 2

    mean = np.sum(weights * effects) / np.sum(weights)
    q = np.sum(weights * (effects - mean) ** 2)
    scaling = np.sum(weights) - np.sum(weights ** 2) / np.sum(weights)

    return max((q - (len(effects) - 1)) / scaling, 0.0), mean


def fingerprint_of(paths):
    """Same hash 04_build_chase_leaderboard.py writes into its diagnostic tables."""

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


def close(a, b, tolerance=TOLERANCE):
    """Equal within a relative tolerance, treating two blanks as equal."""

    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    both_blank = np.isnan(a) & np.isnan(b)
    return bool(np.all(both_blank | (np.abs(a - b) <= tolerance * np.maximum(1, np.abs(b)))))


# --------------------------------------------------
# THE PITCH TABLE
# --------------------------------------------------

def test_pitch_table_basics():
    table = pitches()

    assert table["is_chase"].isin([0, 1]).all(), "is_chase is not 0/1"
    assert (table.loc[table["is_chase"] == 0, "chase_cost"] == 0).all(), "a take has a nonzero cost"
    assert table["called_strike_rate"].between(0, 1).all(), "called_strike_rate outside 0-1"

    # a pitch with a distance must sit in one of the named buckets
    has_distance = table["distance_outside_zone"].notna()
    assert table.loc[has_distance, "distance_bucket"].isin(SETTINGS["DISTANCE_LABELS"]).all(), (
        "a pitch with a distance is outside every bucket"
    )

    needed = [
        "chase_cost", "called_strike_rate", "value_if_taken",
        "expected_cost_per_pitch", "expected_cost_count_only",
        "expected_cost_anchor", "runs_saved", "runs_saved_vs_anchor",
    ]
    assert not table[needed].isna().any().any(), "missing values in the pitch table"
    assert table["balls"].between(0, 3).all() and table["strikes"].between(0, 2).all(), (
        "impossible count"
    )


def test_called_strike_rate_never_rises_with_distance():
    table = pitches().dropna(subset=["distance_outside_zone"])
    table = table.sort_values(["game_year", "balls", "strikes", "distance_outside_zone"])
    steps = table.groupby(["game_year", "balls", "strikes"])["called_strike_rate"].diff()
    assert (steps.dropna() <= 1e-12).all(), "called-strike rate rises with distance somewhere"


def test_taking_a_pitch_is_always_worth_more_after_a_ball():
    counts = pd.read_csv(COUNT_VALUES)
    events = pd.read_csv(EVENT_VALUES)
    value = {(int(r.balls), int(r.strikes)): float(r.run_value) for r in counts.itertuples()}
    walk = float(events.loc[events["event"] == "walk", "run_value"].iloc[0])
    strikeout = float(events.loc[events["event"] == "strikeout", "run_value"].iloc[0])

    for balls in range(4):
        for strikes in range(3):
            after_ball = walk if balls == 3 else value[(balls + 1, strikes)]
            after_strike = strikeout if strikes == 2 else value[(balls, strikes + 1)]
            assert after_strike < after_ball, f"{balls}-{strikes}: a strike is not worse than a ball"


def test_runs_saved_add_to_zero_each_season():
    table = pitches()

    for year, season in table.groupby("game_year"):
        scale = season["chase_cost"].abs().sum()
        cell = (season["expected_cost_per_pitch"] - season["chase_cost"]).sum()
        count_only = (season["expected_cost_count_only"] - season["chase_cost"]).sum()
        assert abs(cell) <= 1e-9 * scale, f"{year}: runs saved add to {cell}"
        assert abs(count_only) <= 1e-9 * scale, f"{year}: count-only runs saved add to {count_only}"


def test_baselines_are_the_league_cell_averages():
    table = pitches()

    cell_mean = table.groupby(
        ["game_year", "balls", "strikes", "distance_bucket"]
    )["chase_cost"].transform("mean")

    count_mean = table.groupby(["game_year", "balls", "strikes"])["chase_cost"].transform("mean")

    assert close(table["expected_cost_per_pitch"], cell_mean), "cell baseline is not the cell average"
    assert close(table["expected_cost_count_only"], count_mean), (
        "count baseline is not the count average"
    )


# --------------------------------------------------
# HITTER-SEASONS
# --------------------------------------------------

def test_leaderboard_matches_pitch_level_rebuild():
    rebuilt = rebuilt_hitter_seasons()
    board = by_season().merge(rebuilt, on=["batter", "game_year"], suffixes=("", "_rebuilt"))

    assert len(board) == len(by_season()), "some leaderboard rows have no pitches behind them"

    for column in [
        "opportunities", "chases", "plate_appearances", "total_cost", "expected_cost",
        "runs_saved_per_600_pa", "runs_saved_count_only_per_600_pa",
        "standard_error_per_600_pa", "chase_plus_raw",
    ]:
        assert close(board[column], board[f"{column}_rebuilt"], 1e-7), (
            f"{column} does not match the pitch level"
        )

    assert close(board["league_chase_cost_per_600_pa"], board["scale"]), "league scale does not match"


def test_counts_make_sense():
    board = by_season()
    assert (board["opportunities"] >= 0).all(), "negative opportunities"
    assert (board["chases"] >= 0).all(), "negative chases"
    assert (board["chases"] <= board["opportunities"]).all(), "more chases than opportunities"
    assert (board["plate_appearances"] > 0).all(), "a row with no plate appearances"
    assert close(board["chase_rate"], 100 * board["chases"] / board["opportunities"]), (
        "chase_rate is not 100 * chases / opportunities"
    )


def test_league_average_chase_plus_is_100():
    rebuilt = rebuilt_hitter_seasons()

    for year, season in rebuilt.groupby("game_year"):
        average = np.average(season["chase_plus_raw"], weights=season["plate_appearances"])
        assert abs(average - 100) < 1e-6, f"{year}: league Chase+ is {average}"

    scale_file = read_results(SCALE)
    assert (scale_file["league_average_chase_plus"] - 100).abs().max() < 1e-6, (
        "the scale file does not report a league Chase+ of 100"
    )

    scales = rebuilt.groupby("game_year")["scale"].first()
    assert close(scale_file.set_index("game_year")["league_chase_cost_per_600_pa"], scales), (
        "the scale file disagrees with the pitch-level league scale"
    )


def test_qualification_follows_the_documented_rule():
    rebuilt = rebuilt_hitter_seasons().copy()

    games = pitches().groupby("game_year")["game_pk"].nunique()
    share = games / games.max() if SETTINGS["PRORATE_FLOORS_BY_SEASON_LENGTH"] else games * 0 + 1

    floors = pd.DataFrame({
        "game_year": share.index,
        "minimum_opportunities": np.round(
            SETTINGS["MINIMUM_OPPORTUNITIES_PER_SEASON"] * share.values
        ).astype(int),
        "minimum_plate_appearances": np.round(
            SETTINGS["MINIMUM_PLATE_APPEARANCES_PER_SEASON"] * share.values
        ).astype(int),
    })

    rebuilt = rebuilt.merge(floors, on="game_year")

    should_qualify = rebuilt[
        (rebuilt["opportunities"] >= rebuilt["minimum_opportunities"])
        & (rebuilt["plate_appearances"] >= rebuilt["minimum_plate_appearances"])
        & (rebuilt["standard_error_per_600_pa"] > 0)
    ]

    expected = set(zip(should_qualify["batter"], should_qualify["game_year"]))
    actual = set(zip(by_season()["batter"], by_season()["game_year"]))

    assert expected == actual, (
        f"{len(expected - actual)} hitter-seasons missing, "
        f"{len(actual - expected)} that should not be there"
    )


def test_cost_per_chase_blank_below_the_minimum():
    minimum = SETTINGS["MINIMUM_CHASES_FOR_COST_PER_CHASE"]

    for table in [by_season(), career()]:
        too_few = table["chases"] < minimum
        assert table.loc[too_few, ["cost_per_chase", "cost_per_chase_se"]].isna().all().all(), (
            f"cost_per_chase shown for someone under {minimum} chases"
        )
        assert table.loc[~too_few, ["cost_per_chase", "cost_per_chase_se"]].notna().all().all(), (
            f"cost_per_chase blank for someone with {minimum}+ chases"
        )
        shown = table[~too_few]
        assert close(shown["cost_per_chase"], shown["total_cost"] / shown["chases"]), (
            "cost_per_chase is not total_cost / chases"
        )
        assert (shown["cost_per_chase_se"] > 0).all(), "a cost_per_chase_se is not positive"


def shrinkage_matches_dersimonian_laird(table, label):
    """Rebuild the shrinkage from scratch and compare it with the table."""

    raw = table["runs_saved_per_600_pa"]
    se = table["standard_error_per_600_pa"]

    tau_squared, mean = dersimonian_laird(raw, se)

    if tau_squared > 0:
        factor = se ** 2 / (se ** 2 + tau_squared)
    else:
        factor = pd.Series(1.0, index=table.index)

    assert close(table["shrinkage_factor"], factor), (
        f"{label}: shrinkage factor is not SE^2 / (SE^2 + tau^2)"
    )
    assert close(table["runs_saved_shrunk"], raw - factor * (raw - mean)), (
        f"{label}: runs_saved_shrunk is not pulled toward the weighted mean"
    )

    return tau_squared, mean


def test_shrinkage_behaves():
    board = by_season()

    assert board["shrinkage_factor"].between(0, 1).all(), "shrinkage factor outside 0-1"

    for year, season in board.groupby("game_year"):
        tau_squared, target = shrinkage_matches_dersimonian_laird(season, str(year))

        raw = season["runs_saved_per_600_pa"]
        shrunk = season["runs_saved_shrunk"]
        factor = season["shrinkage_factor"]

        assert ((shrunk - target).abs() <= (raw - target).abs() + 1e-9).all(), (
            f"{year}: shrinkage overshoots"
        )

        if tau_squared == 0:
            # nobody really differs: everyone sits on the mean, nothing to order
            continue

        # more sampling error must mean more shrinkage, never less
        ranks = season["standard_error_per_600_pa"].corr(factor, method="spearman")
        assert ranks > 0.999, f"{year}: shrinkage is not ordered by standard error"

        # and more data must mean less shrinkage on the whole
        assert season["opportunities"].corr(factor) < 0, (
            f"{year}: more opportunities, more shrinkage"
        )

    shrinkage_matches_dersimonian_laird(career(), "career")


def test_chase_plus_is_runs_saved_on_the_league_scale():
    for table in [by_season(), career()]:
        scale = table["league_chase_cost_per_600_pa"]
        assert (scale > 0).all(), "league scale is not positive"
        assert close(table["chase_plus"], 100 + 100 * table["runs_saved_shrunk"] / scale), (
            "chase_plus is not 100 + 100 * runs_saved_shrunk / scale"
        )
        assert close(table["chase_plus_raw"], 100 + 100 * table["runs_saved_per_600_pa"] / scale), (
            "chase_plus_raw is not 100 + 100 * runs_saved_per_600_pa / scale"
        )
        assert close(table["chase_plus_se"], 100 * table["standard_error_per_600_pa"] / scale), (
            "chase_plus_se is not 100 * standard_error / scale"
        )
        assert ((table["chase_plus"] - 100) * table["runs_saved_shrunk"] >= -1e-9).all(), (
            "Chase+ and runs saved disagree on which side of average a hitter is"
        )

    board = by_season()
    assert close(
        board["chase_plus_posterior_sd"],
        board["chase_plus_se"] * np.sqrt(1 - board["shrinkage_factor"])
    ), "chase_plus_posterior_sd is not se * sqrt(1 - shrinkage_factor)"

    for year, season in board.groupby("game_year"):
        ordered = season.sort_values("runs_saved_shrunk")["chase_plus"]
        assert ordered.is_monotonic_increasing, f"{year}: Chase+ and runs saved disagree on order"


def test_career_chase_plus_is_the_weighted_season_average():
    board = by_season()
    weights = board["plate_appearances"] * board["league_chase_cost_per_600_pa"]

    expected = (
        (board["chase_plus_raw"] * weights).groupby(board["batter"]).sum()
        / weights.groupby(board["batter"]).sum()
    )

    got = career().set_index("batter")["chase_plus_raw"]
    assert close(got, expected.loc[got.index]), (
        "career Chase+ is not the weighted average of its seasons"
    )


def test_anchor_column():
    board = by_season()

    anchor = SETTINGS["ANCHOR_SEASON"] or int(board["game_year"].min())
    in_anchor = board[board["game_year"] == anchor]

    assert close(in_anchor["runs_saved_vs_anchor_per_600_pa"], in_anchor["runs_saved_per_600_pa"]), (
        "anchor season: anchored and own-season runs saved differ"
    )
    assert close(in_anchor["runs_saved_vs_anchor_shrunk"], in_anchor["runs_saved_shrunk"]), (
        "anchor season: the two shrunk columns differ"
    )

    # only the hitter's decisions get shrunk; the yardstick swap is carried over whole
    assert close(
        board["runs_saved_vs_anchor_shrunk"] - board["runs_saved_shrunk"],
        board["runs_saved_vs_anchor_per_600_pa"] - board["runs_saved_per_600_pa"],
        1e-7
    ), "the anchor re-pricing term was shrunk"


def test_keys_are_unique_and_tables_agree():
    board = by_season()

    assert not board.duplicated(["batter", "game_year"]).any(), "a hitter-season appears twice"
    assert not career()["batter"].duplicated().any(), "a hitter appears twice in the career table"
    assert set(career()["batter"]) == set(board["batter"]), (
        "career and season tables have different hitters"
    )

    scale_counts = read_results(SCALE).set_index("game_year")["qualified"]
    assert (scale_counts == board.groupby("game_year").size()).all(), (
        "the scale file counts a different number of qualified hitters"
    )

    if HITTER_VALUE.exists():
        offense = read_results(HITTER_VALUE)
        assert not offense.duplicated(["batter", "game_year"]).any(), (
            "a hitter-season appears twice in hitter_value_leaderboard.csv"
        )


def test_outputs_match_this_script_and_data():
    current = fingerprint_of([
        LEADERBOARD_SCRIPT, PITCH_FILE, PA_VALUE_FILE, COUNT_VALUES, EVENT_VALUES,
    ])

    scale_prints = set(pd.read_csv(SCALE)["run_fingerprint"])
    assert scale_prints == {current}, (
        "the results were not written by the current script and data "
        "-- rerun 04_build_chase_leaderboard.py"
    )

    if SETTINGS["RUN_OUT_OF_FOLD_CHECK"]:
        assert CALLED_STRIKE_CHECK.exists(), "RUN_OUT_OF_FOLD_CHECK is on but there is no check file"
        check_prints = set(pd.read_csv(CALLED_STRIKE_CHECK)["run_fingerprint"])
        assert check_prints == {current}, "the called-strike check file is from a different run"
    else:
        assert not CALLED_STRIKE_CHECK.exists(), (
            "a called-strike check file exists although the check is off"
        )


def test_distance_term_only_depends_on_the_pitches_seen():
    table = pitches()

    # rebuild the league averages from chase costs alone
    cell = table.groupby(
        ["game_year", "balls", "strikes", "distance_bucket"]
    )["chase_cost"].transform("mean")
    count = table.groupby(["game_year", "balls", "strikes"])["chase_cost"].transform("mean")

    shift = (
        (cell - count)
        .groupby([table["batter"], table["game_year"]])
        .sum()
        .rename("shift")
        .reset_index()
    )

    board = by_season().merge(shift, on=["batter", "game_year"])
    term = board["runs_saved_per_600_pa"] - board["runs_saved_count_only_per_600_pa"]

    assert close(term, board["shift"] / board["plate_appearances"] * PER_PA, 1e-7), (
        "the distance term does not match its rebuild from pitch counts"
    )


def test_per_season_files_match_the_stacked_file():
    stacked = by_season()

    pieces = pd.concat(
        [
            read_results(OUTPUT_DIR / f"chase_cost_leaderboard_{int(year)}.csv")
            for year in sorted(stacked["game_year"].unique())
        ],
        ignore_index=True
    )

    assert pieces.shape == stacked.shape, (
        "the per-season files and the stacked file have different sizes"
    )
    numeric = stacked.select_dtypes("number").columns
    assert close(pieces[numeric], stacked[numeric]), (
        "the per-season files and the stacked file disagree"
    )


def test_one_season_careers_match_their_season():
    one_season = career()[career()["seasons_qualified"] == 1]
    board = by_season()

    merged = one_season.merge(
        board,
        left_on=["batter", "first_season"],
        right_on=["batter", "game_year"],
        suffixes=("_career", "_season")
    )

    assert len(merged) == len(one_season), "a one-season career has no matching season row"

    for column in [
        "plate_appearances", "opportunities", "chases", "chase_rate", "cost_per_chase",
        "cost_per_chase_se", "runs_saved_per_600_pa", "standard_error_per_600_pa",
        "chase_plus_raw", "chase_plus_se", "league_chase_cost_per_600_pa",
        "runs_saved_vs_anchor_per_600_pa", "runs_saved_count_only_per_600_pa",
    ]:
        assert close(merged[f"{column}_career"], merged[f"{column}_season"]), f"{column} differs"


def test_column_names_match_the_run():
    """
    Chase+ files use chase_plus names, xChase+ files xchase_plus names, so
    the two can't be mixed up. (Read raw here, without read_results.)
    """

    for path in [BY_SEASON, CAREER, SCALE, HITTER_VALUE]:
        if not path.exists():
            continue

        columns = pd.read_csv(path, nrows=0).columns
        plus_columns = [name for name in columns if "chase_plus" in name]

        # "xchase_plus" can sit anywhere in a name (qualified_mean_xchase_plus)
        if EXPECTED_CONTACT:
            wrong = [name for name in plus_columns if "xchase_plus" not in name]
        else:
            wrong = [name for name in plus_columns if "xchase_plus" in name]

        assert plus_columns, f"{path.name} has no Chase+ columns at all"
        assert not wrong, f"{path.name} has columns from the other run: {wrong}"


def test_downstream_files_match_the_leaderboard():
    """
    The fingerprint only covers the leaderboard script's own files, so the
    two downstream scripts are checked against what they read.
    """

    board = by_season()

    assert HITTER_VALUE.exists(), (
        "hitter_value_leaderboard.csv is missing -- rerun 05_build_hitter_value_leaderboard.py"
    )
    assert RELIABILITY.exists(), (
        "chase_value_reliability.csv is missing -- rerun 06_build_chase_reliability.py"
    )

    offense = read_results(HITTER_VALUE)
    joined = offense.merge(board, on=["batter", "game_year"], how="inner", suffixes=("", "_board"))
    with_chase = offense["runs_saved_shrunk"].notna().sum()
    assert len(joined) == len(board) == with_chase, (
        "hitter_value_leaderboard.csv does not carry exactly the qualified chase hitter-seasons "
        "-- rerun 05_build_hitter_value_leaderboard.py"
    )
    for column in ["chase_rate", "chases", "cost_per_chase", "cost_per_chase_se", "runs_saved_shrunk",
                   "chase_plus", "runs_saved_vs_anchor_shrunk"]:
        assert close(joined[column], joined[f"{column}_board"]), (
            f"hitter_value_leaderboard.csv has a stale {column} -- rerun 05_build_hitter_value_leaderboard.py"
        )

    pairs = pd.read_csv(RELIABILITY)

    seasons = sorted(board["game_year"].unique())
    expected_pairs = {(a, b) for a, b in zip(seasons, seasons[1:])}
    assert set(zip(pairs["first_season"], pairs["second_season"])) == expected_pairs, (
        "chase_value_reliability.csv does not cover every pair of consecutive seasons "
        "-- rerun 06_build_chase_reliability.py"
    )

    for _, row in pairs.iterrows():
        first = board[board["game_year"] == row["first_season"]]
        second = board[board["game_year"] == row["second_season"]]
        both = first.merge(second, on="batter", suffixes=("_1", "_2"))
        assert len(both) == row["hitters"], (
            "chase_value_reliability.csv has a stale hitter count -- rerun 06_build_chase_reliability.py"
        )
        value_r = both["runs_saved_per_600_pa_1"].corr(both["runs_saved_per_600_pa_2"])
        rate_r = both["chase_rate_1"].corr(both["chase_rate_2"])
        assert abs(value_r - row["value_correlation"]) < 1e-9, (
            "chase_value_reliability.csv is stale -- rerun 06_build_chase_reliability.py"
        )
        assert abs(rate_r - row["chase_rate_correlation"]) < 1e-9, (
            "chase_value_reliability.csv is stale -- rerun 06_build_chase_reliability.py"
        )
        value_rho = both["runs_saved_per_600_pa_1"].corr(
            both["runs_saved_per_600_pa_2"], method="spearman"
        )
        assert abs(value_rho - row["value_spearman"]) < 1e-9, (
            "chase_value_reliability.csv has a stale value_spearman "
            "-- rerun 06_build_chase_reliability.py"
        )
        # Spearman-Brown for twice the data, the way the script writes it
        projected = value_r if value_r <= 0 else 2 * value_r / (1 + value_r)
        assert abs(projected - row["value_projected_two_seasons"]) < 1e-9, (
            "chase_value_reliability.csv has a stale value_projected_two_seasons "
            "-- rerun 06_build_chase_reliability.py"
        )


def test_called_strike_check_was_written_and_count_helps():
    if not SETTINGS["RUN_OUT_OF_FOLD_CHECK"]:
        # nothing to read; test_outputs_match_this_script_and_data covers the rest
        return

    check = pd.read_csv(CALLED_STRIKE_CHECK)
    summary = check[check["check"] == "summary"]

    for year, season in summary.groupby("game_year"):
        used = season[season["group"].str.startswith("distance + count")].iloc[0]
        comparison = season[season["group"].str.startswith("distance only")].iloc[0]
        assert used["log_loss"] < comparison["log_loss"], f"{year}: count does not help out of fold"
        assert abs(used["calibration_slope"] - 1) < 0.05, (
            f"{year}: calibration slope {used['calibration_slope']}"
        )
        assert abs(used["calibration_intercept"]) < 0.05, (
            f"{year}: calibration intercept {used['calibration_intercept']}"
        )

        # How the folds were made, as the script recorded it
        assert int(used["fold_splits"]) == SETTINGS["OUT_OF_FOLD_SPLITS"], f"{year}: fold count changed"
        assert int(used["fold_seed"]) == SETTINGS["OUT_OF_FOLD_SEED"], f"{year}: fold seed changed"
        assert used["fold_groups"] == "game_pk", f"{year}: the folds were not grouped by game"

        # Leaky folds (fold models that saw their own test takes) score
        # like the in-sample fit, so out of fold must be worse than in
        # sample by at least the margin the script documents.
        #
        # That margin depends on how many numbers each model fitted, which
        # is recomputed here from the settings rather than trusted from the
        # check file: a spline basis of len(knots) + degree - 2 columns, an
        # intercept, and for the used model one dummy per count except the
        # reference (4 ball states x 3 strike states = 12).
        spline_columns = len(SETTINGS["CALLED_STRIKE_DISTANCE_KNOTS"]) + 3 - 2
        expected_coefficients = {
            "distance + count": spline_columns + (4 * 3 - 1) + 1,
            "distance only": spline_columns + 1,
        }

        for row in (used, comparison):
            for label, count in expected_coefficients.items():
                if row["group"].startswith(label):
                    assert int(row["model_coefficients"]) == count, (
                        f"{year} {row['group']}: the check file says {int(row['model_coefficients'])} "
                        f"fitted numbers, the model specification gives {count}"
                    )

            expected_gap = (
                SETTINGS["OUT_OF_FOLD_GAP_SHARE_OF_OPTIMISM"] * row["model_coefficients"] / row["takes"]
            )
            assert abs(row["minimum_out_of_fold_gap"] - expected_gap) < 1e-12, (
                f"{year} {row['group']}: the recorded minimum gap is not the rule the settings give"
            )
            assert row["log_loss"] - row["in_sample_log_loss"] > row["minimum_out_of_fold_gap"], (
                f"{year} {row['group']}: out-of-fold log loss is not enough worse than in-sample "
                "-- the folds look leaky"
            )

    # and the in-sample number in the file has to be the one the pitch table implies
    takes = pitches()[pitches()["is_chase"] == 0][
        ["game_pk", "at_bat_number", "pitch_number", "game_year", "called_strike_rate",
         "distance_outside_zone"]
    ]
    calls = pd.read_parquet(
        PITCH_FILE,
        columns=["game_pk", "at_bat_number", "pitch_number", "description", "is_swing"]
    )
    takes = takes.merge(calls, on=["game_pk", "at_bat_number", "pitch_number"], how="left")
    assert (takes["is_swing"] == 0).all(), "a take in the pitch table is a swing in the pitch file"

    # The model is fit on takes that have a distance, so those are the ones
    # the recorded number covers. (Only the used model can be checked this
    # way: its rates are the ones in the pitch table.)
    for year, season in takes.dropna(subset=["distance_outside_zone"]).groupby("game_year"):
        outcome = (season["description"] == "called_strike").astype(float)
        rate = season["called_strike_rate"].clip(1e-15, 1 - 1e-15)
        in_sample = -np.mean(outcome * np.log(rate) + (1 - outcome) * np.log(1 - rate))
        recorded = summary[
            (summary["game_year"] == year) & summary["group"].str.startswith("distance + count")
        ]["in_sample_log_loss"].iloc[0]
        assert abs(in_sample - recorded) < 1e-9, (
            f"{year}: the recorded in-sample log loss does not match the pitch table"
        )
        for _, row in summary[summary["game_year"] == year].iterrows():
            assert int(row["takes"]) == len(season), (
                f"{year} {row['group']}: the check file counts {int(row['takes'])} takes, "
                f"the pitch table has {len(season)}"
            )


# --------------------------------------------------
# REPRODUCIBILITY (only with --rerun)
# --------------------------------------------------

OUTPUTS_TO_HASH = [
    BY_SEASON,
    CAREER,
    SCALE,
    CALLED_STRIKE_CHECK,
    PITCH_COSTS,
] + sorted(OUTPUT_DIR.glob("chase_cost_leaderboard_20*.csv"))


def fingerprint():
    """SHA-256 of every leaderboard output file that exists."""

    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in OUTPUTS_TO_HASH
        if path.exists()
    }


def rerun_is_identical():
    before = fingerprint()
    command = [sys.executable, str(LEADERBOARD_SCRIPT)]

    if EXPECTED_CONTACT:
        command.append("--expected-contact")

    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
    after = fingerprint()
    changed = [name for name in before if before[name] != after.get(name)]
    assert not changed, f"a rerun changed {changed}"


# --------------------------------------------------
# RUN EVERYTHING
# --------------------------------------------------

if __name__ == "__main__":

    # Every test_ function, in the order it is defined above
    checks = [
        (name, function)
        for name, function in list(globals().items())
        if name.startswith("test_") and callable(function)
    ]

    if "--rerun" in sys.argv:
        checks.append(("rerun_is_identical", rerun_is_identical))

    if EXPECTED_CONTACT:
        print("Checking the xChase+ run (results/xchase/).")
        print()

    failures = 0

    for name, function in checks:
        try:
            function()
            print(f"PASS  {name}")
        except Exception as error:
            failures += 1
            print(f"FAIL  {name}: {error}")

    print()
    print(f"{len(checks) - failures} of {len(checks)} checks passed.")

    sys.exit(1 if failures else 0)
