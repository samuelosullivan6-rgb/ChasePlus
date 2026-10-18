"""
The college path's version of steps 03 and 04: run values, the wOBA
weights, expected contact, and the price of every chase decision, built
from the pitches in the files alone.

The arithmetic is step 03's and step 04's, line for line, with the
settings a college season needs passed in (MLB_SETTINGS and
COLLEGE_SETTINGS below). Run with MLB_SETTINGS on the 2026 Statcast
pitches it reproduces step 04's 2026 numbers exactly; trackman_roundtrip.py
checks that every run, so a difference on the college path is a choice
made here, never a slip in copying.

WHAT CHANGES FOR A COLLEGE SEASON, AND WHY

  A college team's TrackMan season is about 15,000-20,000 pitches (55-60
  games of both teams), against step 04's 730,000 a season. The study in
  trackman_roundtrip.py priced each MLB team's first 60 games of 2026
  (17,200-18,300 pitches) as a league on its own, every way below, and
  compared each hitter with the MLB build's price of the same pitches.

  League        Everyone in the files: the team's hitters and every
                opponent's. The baseline, the called-strike model, the
                run values and the xwOBA model are all fit on them.
  Baseline      Kept as step 04's: the league's average cost in the same
  cells         count and distance bucket, 12 counts x 4 buckets, 48 cells
                of about 190 pitches each at college size. Coarser cells
                were tried and were worse: merging the buckets into three,
                two or none put the hitters 3.39, 3.40 and 3.49 runs per 600
                PA from the MLB build (RMSE), against 3.25 for step 04's own
                cells, and the cards' four count groups in place of the 12
                counts 4.2. A pitch nowhere near the zone and one just off
                it are too different to share a baseline, and a chase at
                3-1 costs four times one at 0-1; the noise of a 190-pitch
                cell costs less than either.
  Count run     The value of each plate appearance's result (its event's
  values        average RE24 value), averaged over the counts it passed
                through, where step 03 averages each plate appearance's own
                RE24 value. With runners rebuilt from TrackMan's results,
                the result's value is less sensitive to a runner put on the
                wrong base. In the study the two give the same hitters
                (3.25 against 3.26 runs); on 2026 MLB they differ by at
                most 0.006 runs in any count (3-0).
  Half innings  Step 03 calls a game's last half inning complete by the
                9th-inning rule. College has 7-inning games and run rules,
                so a last half inning counts as complete when it recorded
                three outs.
  Called        Step 04's model (a distance curve plus the count, fit on
  strikes       the season's takes). With 6,000 takes its thin tail can
                bend back up past a foot or two off the plate; a pitch
                farther off is never likelier to be called a strike, so the
                curve is held at its lowest point from there on (step 04's
                MLB curves never rise, so its numbers are unchanged).
  xwOBA         Not Savant's. Fit on the files' own batted balls (college
                bats are metal): each ball's expected wOBA value from its
                exit speed and launch angle, the average of its nearest
                neighbors in the files, the number of neighbors chosen by
                cross-validation. Bunts, and balls with no tracking, get
                the average of their hit type.
  wOBA weights  From the files' run values, the way Savant builds them:
                each hit's value above an out, scaled so the league's wOBA
                equals its on-base percentage.
  Qualifying    A college regular gets about 240 plate appearances. The
                floors are 100 plate appearances and 200 out-of-zone
                pitches, about 40% of a regular's season (step 04's 300 and
                600 are about 45% of an MLB regular's).
  Shrinkage     Step 04 fits the spread between hitters on its 260
                qualified hitters. A college team has a dozen, too few to
                measure a spread on, so the college path fits it on every
                hitter in the files with at least 40 out-of-zone pitches
                (the opponents included, each weighted by his own standard
                error) and shrinks toward that group's average. Of the
                pools tried (the qualified only, 20, 40, 80 or 150
                pitches), 40 predicted the same hitters' next 100 games
                best: 10.1 runs per 600 PA, against 10.0 for the MLB build
                on the same pitches with the whole league behind it.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

import leak_rules as lr


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

MLB_SETTINGS = {
    # step 03
    "final_half_rule": "ninth_inning",
    "earliest_regulation_final_inning": 9,
    "count_values_from": "plate_appearance",
    # step 04
    "distance_bins": [-0.001, 0.15, 0.35, 0.70, 100],
    "distance_labels": ["borderline", "just off", "clearly off", "nowhere near"],
    "baseline_counts": "count",
    "minimum_opportunities": 600,
    "minimum_plate_appearances": 300,
    "minimum_chases_for_cost_per_chase": 120,
    "minimum_chases_in_play_with_xwoba": 1000,
    "called_strike_knots": [0.0, 0.10, 0.20, 0.30, 0.45, 0.70],
    "shrink_pool_minimum_opportunities": None,      # None: the qualified hitters
}

COLLEGE_SETTINGS = {
    **MLB_SETTINGS,
    "final_half_rule": "three_outs",
    "count_values_from": "event",
    "minimum_opportunities": 200,
    "minimum_plate_appearances": 100,
    "minimum_chases_in_play_with_xwoba": 200,
    "shrink_pool_minimum_opportunities": 40,
}

PLATE_APPEARANCES_PER_SEASON = 600
HALF_PLATE_PLUS_BALL = 0.83
IN_PLAY_HIT_EVENTS = ["single", "double", "triple", "home_run"]
COUNTS_IN_ORDER = [(b, s) for b in range(4) for s in range(3)]

STRIKE_DESCRIPTIONS = {"swinging_strike", "swinging_strike_blocked", "foul_tip"}
FOUL_DESCRIPTIONS = {"foul"}
IN_PLAY_DESCRIPTIONS = {"hit_into_play"}

# The wOBA events and the outs they are measured against (lr.woba_scale's
# lists, so the college weights are built the way the backtest's scale is).
WOBA_EVENTS = ["walk", "hit_by_pitch", "single", "double", "triple", "home_run"]
NOT_IN_WOBA = {"intent_walk", "sac_bunt", "sac_bunt_double_play", "truncated_pa"}


# --------------------------------------------------
# RUN VALUES (step 03)
# --------------------------------------------------

def base_state_label(on_first, on_second, on_third):
    return (np.where(on_first == 1, "1", "_") + np.where(on_second == 1, "2", "_")
            + np.where(on_third == 1, "3", "_"))


def run_value_tables(pitches, settings):
    """Step 03's three tables from one set of pitches: base-out run
    expectancy, run value by event, run value by count, and the plate
    appearance values step 04 prices against. pitches needs Statcast's
    columns (runners as on_1b / on_2b / on_3b or runner_on_1b ...)."""

    df = pitches.copy()
    for base in ("1b", "2b", "3b"):
        if f"runner_on_{base}" not in df.columns:
            df[f"runner_on_{base}"] = df[f"on_{base}"].notna().astype(int)
    if "count_state" not in df.columns:
        df["count_state"] = df["balls"].astype(str) + "-" + df["strikes"].astype(str)
    df = df.sort_values(["game_pk", "at_bat_number", "pitch_number"]).reset_index(drop=True)
    df["half_inning_id"] = (df["game_pk"].astype(str) + "_" + df["inning"].astype(str) + "_"
                            + df["inning_topbot"].astype(str))

    # A game's last half inning: complete or cut short?
    finals = set(df.groupby("game_pk")["half_inning_id"].last())
    last = df[df["half_inning_id"].isin(finals)]
    if settings["final_half_rule"] == "three_outs":
        ends = last.groupby("half_inning_id").tail(1)
        outs_at_end = ends["outs_when_up"].astype(float) + ends["outs_on_pitch"].astype(float)
        incomplete = set(ends.loc[outs_at_end < 3, "half_inning_id"])
    else:
        summary = last.groupby("half_inning_id").agg(
            inning=("inning", "first"), half=("inning_topbot", "first"),
            batting_final_score=("post_bat_score", "max"),
            fielding_final_score=("fld_score", "max"))
        complete_top = ((summary["half"] == "Top")
                        & (summary["inning"] >= settings["earliest_regulation_final_inning"]))
        complete_bottom = ((summary["half"] == "Bot")
                           & (summary["batting_final_score"] <= summary["fielding_final_score"]))
        incomplete = set(summary.index[~(complete_top | complete_bottom)])
    df = df[~df["half_inning_id"].isin(incomplete)].copy()

    pas = (df.sort_values(["game_pk", "at_bat_number", "pitch_number"])
           .groupby(["game_pk", "at_bat_number"], as_index=False)
           .agg(half_inning_id=("half_inning_id", "first"), inning=("inning", "first"),
                batter=("batter", "first"), pitcher=("pitcher", "first"),
                game_year=("game_year", "first"), outs_when_up=("outs_when_up", "first"),
                runner_on_1b=("runner_on_1b", "first"), runner_on_2b=("runner_on_2b", "first"),
                runner_on_3b=("runner_on_3b", "first"), score_at_start=("bat_score", "first"),
                score_after=("post_bat_score", "last"), event=("events", "last")))
    pas["base_state"] = base_state_label(pas["runner_on_1b"], pas["runner_on_2b"],
                                         pas["runner_on_3b"])
    final_score = pas.groupby("half_inning_id")["score_after"].transform("max")
    pas["runs_rest_of_inning"] = final_score - pas["score_at_start"]
    if (pas["runs_rest_of_inning"] < 0).any():
        raise SystemExit("Some plate appearances have negative runs to come: the scores do "
                         "not line up.")

    base_out = (pas.groupby(["game_year", "base_state", "outs_when_up"])
                .agg(occurrences=("runs_rest_of_inning", "size"),
                     run_expectancy=("runs_rest_of_inning", "mean")).reset_index())
    lookup = base_out.set_index(["game_year", "base_state", "outs_when_up"])["run_expectancy"]
    pas["run_expectancy_before"] = pd.MultiIndex.from_arrays(
        [pas["game_year"], pas["base_state"], pas["outs_when_up"]]).map(lookup)
    pas = pas.sort_values(["half_inning_id", "at_bat_number"]).reset_index(drop=True)
    pas["run_expectancy_after"] = (pas.groupby("half_inning_id")["run_expectancy_before"]
                                   .shift(-1).fillna(0.0))
    pas["runs_on_play"] = pas["score_after"] - pas["score_at_start"]
    pas["run_value"] = (pas["run_expectancy_after"] - pas["run_expectancy_before"]
                        + pas["runs_on_play"])

    events = (pas.groupby(["game_year", "event"])
              .agg(occurrences=("run_value", "size"), run_value=("run_value", "mean"))
              .reset_index().sort_values(["game_year", "occurrences"], ascending=[True, False]))

    through = df[["game_pk", "at_bat_number", "count_state"]].drop_duplicates().merge(
        pas[["game_pk", "at_bat_number", "game_year", "run_value", "event"]],
        on=["game_pk", "at_bat_number"], how="inner")
    if settings["count_values_from"] == "event":
        event_value = events.set_index(["game_year", "event"])["run_value"]
        through["run_value"] = pd.MultiIndex.from_arrays(
            [through["game_year"], through["event"]]).map(event_value)
    counts = (through.groupby(["game_year", "count_state"])
              .agg(occurrences=("run_value", "size"), run_value=("run_value", "mean"))
              .reset_index())
    counts["balls"] = counts["count_state"].str[0].astype(int)
    counts["strikes"] = counts["count_state"].str[-1].astype(int)
    counts = counts.sort_values(["game_year", "balls", "strikes"]).reset_index(drop=True)
    return {"base_out": base_out, "events": events, "counts": counts, "plate_appearances": pas,
            "incomplete_half_innings": len(incomplete)}


def woba_weights(events):
    """wOBA weights from these run values, built the way Savant's are:
    each event's value above the average out, times one scale that makes
    the league's wOBA equal its on-base percentage. One season."""

    r = events.set_index("event")
    outs = r.loc[[e for e in lr.OUT_EVENTS if e in r.index]]
    out_value = (outs["run_value"] * outs["occurrences"]).sum() / outs["occurrences"].sum()
    above = {e: r.loc[e, "run_value"] - out_value if e in r.index else 0.0 for e in WOBA_EVENTS}
    n = {e: r.loc[e, "occurrences"] if e in r.index else 0 for e in WOBA_EVENTS}
    total = r["occurrences"].sum()
    excluded = r.loc[[e for e in NOT_IN_WOBA | {"catcher_interf"} if e in r.index], "occurrences"].sum()
    denominator = total - excluded
    on_base = sum(n[e] for e in WOBA_EVENTS)
    raw = sum(above[e] * n[e] for e in WOBA_EVENTS) / denominator
    scale = (on_base / denominator) / raw
    return {e: float(scale * above[e]) for e in WOBA_EVENTS}


def woba_columns(pitches, weights):
    """woba_value and woba_denom on every pitch that ends a plate
    appearance, as Savant fills them (errors and fielder's choices count
    as outs, the standard wOBA)."""

    ev = pitches["events"]
    value = ev.map(weights).where(ev.notna())
    value = value.fillna(0.0).where(ev.notna())
    denom = pd.Series(np.where(ev.isin(NOT_IN_WOBA), 0.0, 1.0), index=pitches.index).where(ev.notna())
    return value, denom


# --------------------------------------------------
# EXPECTED CONTACT (the files' own xwOBA)
# --------------------------------------------------

KNN_NEIGHBORS = [20, 30, 50, 80, 120, 200]
KNN_ANGLE_WEIGHTS = [0.5, 1.0, 2.0]
KNN_FOLDS = 5
KNN_SEED = 0


def fit_xwoba(bip, value_col="woba_value"):
    """Expected wOBA value of a batted ball from its exit speed and launch
    angle: the average value of its k nearest neighbors among the files'
    batted balls (bunts left out), on exit speed and launch angle scaled by
    their spread, with k and the angle's weight chosen by 5-fold
    cross-validated squared error. Returns a predict(frame) function and
    the chosen settings."""

    fit = bip[(bip["is_bunt"] == 0) & bip["launch_speed"].notna()
              & bip["launch_angle"].notna() & bip[value_col].notna()]
    ev_sd = fit["launch_speed"].std()
    la_sd = fit["launch_angle"].std()
    y = fit[value_col].to_numpy(float)

    def features(frame, angle_weight):
        return np.column_stack([frame["launch_speed"].to_numpy(float) / ev_sd,
                                angle_weight * frame["launch_angle"].to_numpy(float) / la_sd])

    folds = KFold(KNN_FOLDS, shuffle=True, random_state=KNN_SEED)
    scores = []
    for weight in KNN_ANGLE_WEIGHTS:
        X = features(fit, weight)
        for k in KNN_NEIGHBORS:
            if k >= 0.8 * len(fit):
                continue
            err = 0.0
            for train, test in folds.split(X):
                model = KNeighborsRegressor(n_neighbors=k).fit(X[train], y[train])
                err += ((model.predict(X[test]) - y[test]) ** 2).sum()
            scores.append((err / len(y), k, weight))
    mse, k, weight = min(scores)
    model = KNeighborsRegressor(n_neighbors=k).fit(features(fit, weight), y)

    # Balls with no tracking, and bunts: the average value of their hit type
    # (bunts on their own, sacrifices included at an out's value) among the
    # files' balls in play.
    group = lambda f: np.where(f["is_bunt"] == 1, "bunt", f["bb_type"].fillna("unknown"))
    by_type = pd.Series(bip[value_col].to_numpy(float), index=group(bip)).groupby(level=0).mean()
    fallback = float(bip[value_col].mean())

    def predict(frame):
        out = pd.Series(np.nan, index=frame.index)
        tracked = (frame["is_bunt"] == 0) & frame["launch_speed"].notna() & frame["launch_angle"].notna()
        if tracked.any():
            out[tracked] = model.predict(features(frame[tracked], weight))
        rest = ~tracked
        out[rest] = pd.Series(group(frame[rest]), index=frame.index[rest]).map(by_type).fillna(fallback)
        return out

    chosen = {"neighbors": int(k), "angle_weight": float(weight), "cv_mse": float(mse),
              "batted_balls": int(len(fit)), "exit_speed_sd": float(ev_sd),
              "launch_angle_sd": float(la_sd)}
    return predict, chosen


# --------------------------------------------------
# PRICING (step 04)
# --------------------------------------------------

def called_strike_features(frame):
    features = pd.DataFrame({"distance_outside_zone": frame["distance_outside_zone"].astype(float)},
                            index=frame.index)
    balls = frame["balls"].to_numpy()
    strikes = frame["strikes"].to_numpy()
    for b, s in COUNTS_IN_ORDER[1:]:
        features[f"count_{b}_{s}"] = ((balls == b) & (strikes == s)).astype(float)
    return features


def new_called_strike_model(knots):
    distance_curve = Pipeline([
        ("spline", SplineTransformer(knots=np.array(knots).reshape(-1, 1), degree=3,
                                     extrapolation="linear", include_bias=False)),
        ("scale", StandardScaler()),
    ])
    features = ColumnTransformer([("distance", distance_curve, ["distance_outside_zone"])],
                                 remainder="passthrough", verbose_feature_names_out=False)
    return Pipeline([("features", features), ("logit", LogisticRegression(max_iter=1000))])


def in_play_outcome(events):
    return pd.Series(np.where(events.isin(IN_PLAY_HIT_EVENTS), events, "out"), index=events.index)


def price(pitches, run_values, settings, expected_contact, swap=None):
    """Every out-of-zone pitch priced as step 04 prices it: called-strike
    chance, value if taken, value of the swing, chase cost, the league's
    expected cost in the same cell, and runs saved.

    pitches     step 02's cleaned pitches (one or more seasons)
    run_values  run_value_tables()'s result for the same pitches
    swap        for the round-trip test only: replace one ingredient with
                someone else's, keyed on the pitch. Any of
                  "count_values", "event_values", "in_play_values"  (tables)
                  "xwoba_line"           {season: (slope, intercept)}
                  "called_strike_rate", "xwoba", "expected_cost_per_pitch"
                                                         (Series on the pitch key)
    Returns (priced opportunities, diagnostics)."""

    swap = swap or {}
    keys = ["game_pk", "at_bat_number", "pitch_number"]
    diagnostics = {}

    counts = swap.get("count_values", run_values["counts"])
    events = swap.get("event_values", run_values["events"])
    count_lookup = {(int(r.game_year), int(r.balls), int(r.strikes)): float(r.run_value)
                    for r in counts.itertuples()}

    def event_value(season, name):
        match = events[(events["game_year"] == season) & (events["event"] == name)]
        if len(match) != 1:
            raise SystemExit(f"No single {season} run value for '{name}'.")
        return float(match["run_value"].iloc[0])

    seasons = sorted(int(s) for s in counts["game_year"].unique())
    walk = {s: event_value(s, "walk") for s in seasons}
    strikeout = {s: event_value(s, "strikeout") for s in seasons}

    def value_at(season, balls, strikes):
        if balls >= 4:
            return walk[season]
        if strikes >= 3:
            return strikeout[season]
        return count_lookup[(season, balls, strikes)]

    opp = pitches[(pitches["is_analyzable"] == 1) & (pitches["is_outside_zone"] == 1)].copy()
    opp["balls"] = opp["balls"].astype(int)
    opp["strikes"] = opp["strikes"].astype(int)
    opp["distance_bucket"] = pd.cut(opp["distance_outside_zone"], bins=settings["distance_bins"],
                                    labels=settings["distance_labels"]).astype(str)

    pa_lookup = run_values["plate_appearances"][["game_pk", "at_bat_number", "run_value"]].rename(
        columns={"run_value": "plate_appearance_value"})
    opp = opp.merge(pa_lookup, on=["game_pk", "at_bat_number"], how="left")
    diagnostics["unpriceable_share"] = float(opp["plate_appearance_value"].isna().mean())
    opp = opp[opp["plate_appearance_value"].notna()].copy()

    # What a ball in play is worth, context neutral
    if "in_play_values" in swap:
        in_play_values = swap["in_play_values"]
    else:
        bip = (pitches.loc[pitches["description"] == "hit_into_play",
                           ["game_pk", "at_bat_number", "game_year", "events"]]
               .merge(pa_lookup, on=["game_pk", "at_bat_number"], how="inner"))
        bip["outcome"] = in_play_outcome(bip["events"])
        in_play_values = (bip.groupby(["game_year", "outcome"])
                          .agg(balls_in_play=("plate_appearance_value", "size"),
                               run_value=("plate_appearance_value", "mean")).reset_index())
    in_play_lookup = {(int(r.game_year), r.outcome): float(r.run_value)
                      for r in in_play_values.itertuples()}
    diagnostics["in_play_values"] = in_play_values

    # The called-strike model, one per season, on the takes
    takes = opp[opp["is_swing"] == 0].copy()
    takes["was_called_strike"] = (takes["description"] == "called_strike").astype(int)
    inputs = ["distance_outside_zone", "balls", "strikes"]
    takes = takes.dropna(subset=inputs)
    opp["called_strike_rate"] = np.nan
    models = {}
    rises = {}
    for year in sorted(takes["game_year"].unique()):
        year_takes = takes[takes["game_year"] == year]
        model = new_called_strike_model(settings["called_strike_knots"])
        model.fit(called_strike_features(year_takes), year_takes["was_called_strike"])
        models[year] = model
        mask = (opp["game_year"] == year) & opp[inputs].notna().all(axis=1)
        opp.loc[mask, "called_strike_rate"] = model.predict_proba(
            called_strike_features(opp.loc[mask]))[:, 1]
        grid = np.linspace(0, 10, 4001)
        curve = model.decision_function(called_strike_features(pd.DataFrame({
            "distance_outside_zone": grid, "balls": 0, "strikes": 0})))
        if (np.diff(curve) > 1e-12).any():
            # A small season's thin tail can bend the curve back up (step 04
            # warns; its MLB curves never do). A pitch farther off is never
            # likelier to be called a strike, so the distance curve is held
            # at its lowest point so far wherever it would rise. The count
            # terms shift the whole curve, so they are untouched.
            rises[int(year)] = float(grid[int(np.argmax(np.diff(curve) > 1e-12)) + 1])
            held = np.minimum.accumulate(curve)
            d = opp.loc[mask, "distance_outside_zone"].to_numpy(float)
            at_zero = called_strike_features(opp.loc[mask].assign(distance_outside_zone=0.0))
            count_term = model.decision_function(at_zero) - curve[0]
            logit = np.interp(np.clip(d, 0, 10), grid, held) + count_term
            opp.loc[mask, "called_strike_rate"] = 1 / (1 + np.exp(-logit))
    diagnostics["called_strike_curve_held_from_ft"] = rises
    unscored = opp["called_strike_rate"].isna()
    if unscored.any():
        rate = takes.groupby(["game_year", "balls", "strikes"])["was_called_strike"].mean().rename("r")
        opp.loc[unscored, "called_strike_rate"] = (
            opp.loc[unscored, ["game_year", "balls", "strikes"]].join(rate, on=["game_year", "balls", "strikes"])["r"]
            .fillna(takes["was_called_strike"].mean()).to_numpy())
    diagnostics["called_strike_models"] = models
    diagnostics["takes"] = len(takes)
    if "called_strike_rate" in swap:
        theirs = opp.set_index(keys).index.map(swap["called_strike_rate"])
        opp["called_strike_rate"] = np.where(pd.notna(theirs), theirs, opp["called_strike_rate"])

    seasons_col = opp["game_year"].astype(int).to_numpy()
    b = opp["balls"].to_numpy()
    s = opp["strikes"].to_numpy()
    ball_value = np.array([value_at(y, x + 1, z) for y, x, z in zip(seasons_col, b, s)])
    strike_value = np.array([value_at(y, x, z + 1) for y, x, z in zip(seasons_col, b, s)])
    foul_value = np.array([value_at(y, x, min(z + 1, 2)) for y, x, z in zip(seasons_col, b, s)])
    opp["value_if_taken"] = (opp["called_strike_rate"] * strike_value
                             + (1 - opp["called_strike_rate"]) * ball_value)

    opp["value_if_swung"] = np.nan
    whiff = opp["description"].isin(STRIKE_DESCRIPTIONS).to_numpy()
    foul = opp["description"].isin(FOUL_DESCRIPTIONS).to_numpy()
    in_play = opp["description"].isin(IN_PLAY_DESCRIPTIONS).to_numpy()
    opp.loc[whiff, "value_if_swung"] = strike_value[whiff]
    opp.loc[foul, "value_if_swung"] = foul_value[foul]
    opp.loc[in_play, "value_if_swung"] = [
        in_play_lookup[(int(y), o)] for y, o in zip(opp.loc[in_play, "game_year"],
                                                    in_play_outcome(opp.loc[in_play, "events"]))]

    if expected_contact:
        opp["xwoba"] = pd.to_numeric(opp["estimated_woba_using_speedangle"], errors="coerce")
        if "xwoba" in swap:
            # Savant's gaps stay gaps: those balls keep their actual outcome, as in step 04
            opp["xwoba"] = pd.to_numeric(opp.set_index(keys).index.map(swap["xwoba"]), errors="coerce")
        rows = []
        for season in sorted(opp["game_year"].unique()):
            season_in_play = in_play & (opp["game_year"] == season).to_numpy()
            has_x = season_in_play & opp["xwoba"].notna().to_numpy()
            if has_x.sum() < settings["minimum_chases_in_play_with_xwoba"]:
                raise SystemExit(f"{season}: only {int(has_x.sum())} chases put in play have an "
                                 f"xwOBA (needs {settings['minimum_chases_in_play_with_xwoba']}).")
            x = opp.loc[has_x, "xwoba"].to_numpy(float)
            actual = opp.loc[has_x, "value_if_swung"].to_numpy(float)
            if "xwoba_line" in swap:
                slope, intercept = swap["xwoba_line"][int(season)]
            else:
                slope, intercept = np.polyfit(x, actual, 1)
            if slope <= 0:
                raise SystemExit(f"{season}: the xwOBA line slopes down ({slope:.4f}).")
            opp.loc[has_x, "value_if_swung"] = intercept + slope * x
            rows.append({"game_year": int(season), "chases_in_play": int(season_in_play.sum()),
                         "without_xwoba": int(season_in_play.sum() - has_x.sum()),
                         "intercept": intercept, "slope": slope, "implied_woba_scale": 1 / slope,
                         "r_squared": np.corrcoef(x, actual)[0, 1] ** 2})
        diagnostics["xwoba_line"] = pd.DataFrame(rows)

    opp["chase_cost"] = opp["value_if_taken"] - opp["value_if_swung"]
    opp.loc[opp["is_chase"] == 0, "chase_cost"] = 0.0
    unpriced = (opp["is_chase"] == 1) & opp["chase_cost"].isna()
    if unpriced.any():
        print(f"WARNING: {int(unpriced.sum())} chases could not be priced "
              f"({opp.loc[unpriced, 'description'].value_counts().to_dict()}); dropped.")
        opp = opp[~unpriced].copy()

    # The league baseline: same season, count (or count group) and bucket
    if settings["baseline_counts"] == "count_group":
        opp["baseline_count"] = lr.count_group(opp["balls"], opp["strikes"])
    else:
        opp["baseline_count"] = opp["balls"].astype(str) + "-" + opp["strikes"].astype(str)
    cell = ["game_year", "baseline_count", "distance_bucket"]
    league = (opp.groupby(cell).agg(expected_cost_per_pitch=("chase_cost", "mean"),
                                    league_chase_rate=("is_chase", "mean"),
                                    league_pitches=("is_chase", "size")).reset_index())
    by_count = (opp.groupby(["game_year", "balls", "strikes"])
                .agg(expected_cost_count_only=("chase_cost", "mean")).reset_index())
    opp = opp.merge(league[cell + ["expected_cost_per_pitch"]], on=cell, how="left")
    opp = opp.merge(by_count, on=["game_year", "balls", "strikes"], how="left")
    no_distance = opp["distance_outside_zone"].isna()
    opp.loc[no_distance, "expected_cost_per_pitch"] = opp.loc[no_distance, "expected_cost_count_only"]
    if "expected_cost_per_pitch" in swap:
        theirs = opp.set_index(keys).index.map(swap["expected_cost_per_pitch"])
        opp["expected_cost_per_pitch"] = np.where(pd.notna(theirs), theirs,
                                                  opp["expected_cost_per_pitch"])
    opp["runs_saved"] = opp["expected_cost_per_pitch"] - opp["chase_cost"]
    # One season and no anchor: the anchored columns are the season's own.
    opp["expected_cost_anchor"] = opp["expected_cost_per_pitch"]
    opp["runs_saved_vs_anchor"] = opp["runs_saved"]
    diagnostics["baseline_cells"] = league
    return opp, diagnostics


def dersimonian_laird(effects, standard_errors):
    """Step 04's estimator: tau^2, the weighted mean, Cochran's Q."""

    effects = np.asarray(effects, float)
    w = 1.0 / np.asarray(standard_errors, float) ** 2
    mean = np.sum(w * effects) / np.sum(w)
    q = np.sum(w * (effects - mean) ** 2)
    scaling = np.sum(w) - np.sum(w ** 2) / np.sum(w)
    return max((q - (len(effects) - 1)) / scaling, 0.0), mean, q


def hitter_seasons(opp, pitches, settings):
    """Step 04's per-hitter season table, Chase+ scale and shrinkage.
    Returns (qualified hitters, every hitter, the season's scale rows)."""

    opp = opp.copy()
    opp["chase_cost_squared"] = opp["chase_cost"] ** 2
    floors = opp.groupby("game_year").agg(games=("game_pk", "nunique")).reset_index()
    floors["season_share"] = floors["games"] / floors["games"].max()
    floors["minimum_opportunities"] = np.round(settings["minimum_opportunities"]
                                               * floors["season_share"]).astype(int)
    floors["minimum_plate_appearances"] = np.round(settings["minimum_plate_appearances"]
                                                   * floors["season_share"]).astype(int)

    pa_counts = (pitches[pitches["is_analyzable"] == 1][["batter", "game_year", "game_pk", "at_bat_number"]]
                 .drop_duplicates().groupby(["batter", "game_year"]).size()
                 .rename("plate_appearances").reset_index())
    h = (opp.groupby(["batter", "game_year"])
         .agg(opportunities=("is_chase", "size"), chases=("is_chase", "sum"),
              chase_rate=("is_chase", "mean"), total_cost=("chase_cost", "sum"),
              chase_cost_squared=("chase_cost_squared", "sum"),
              expected_cost=("expected_cost_per_pitch", "sum"),
              expected_cost_count_only=("expected_cost_count_only", "sum"),
              expected_cost_anchor=("expected_cost_anchor", "sum"),
              mean_runs_saved=("runs_saved", "mean"), standard_deviation=("runs_saved", "std"))
         .reset_index().merge(pa_counts, on=["batter", "game_year"], how="left"))
    h["chase_rate"] *= 100
    chases = h["chases"].astype(float)
    h["cost_per_chase"] = h["total_cost"] / chases.where(chases > 0)
    var = ((h["chase_cost_squared"] - h["total_cost"] ** 2 / chases.where(chases > 0))
           / (chases - 1).where(chases > 1))
    h["cost_per_chase_se"] = np.sqrt(var.clip(lower=0) / chases.where(chases > 0))
    few = chases < settings["minimum_chases_for_cost_per_chase"]
    h.loc[few, ["cost_per_chase", "cost_per_chase_se"]] = np.nan
    h["scale_to_600_pa"] = h["opportunities"] / h["plate_appearances"] * PLATE_APPEARANCES_PER_SEASON
    h["runs_saved_per_600_pa"] = h["mean_runs_saved"] * h["scale_to_600_pa"]
    h["runs_saved_vs_anchor_per_600_pa"] = ((h["expected_cost_anchor"] - h["total_cost"])
                                            / h["plate_appearances"] * PLATE_APPEARANCES_PER_SEASON)
    h["runs_saved_count_only_per_600_pa"] = ((h["expected_cost_count_only"] - h["total_cost"])
                                             / h["plate_appearances"] * PLATE_APPEARANCES_PER_SEASON)
    h["standard_error_per_600_pa"] = (h["standard_deviation"] / np.sqrt(h["opportunities"])
                                      * h["scale_to_600_pa"])

    league = h.groupby("game_year").agg(league_plate_appearances=("plate_appearances", "sum"),
                                        league_total_cost=("total_cost", "sum")).reset_index()
    league["league_chase_cost_per_600_pa"] = (league["league_total_cost"]
                                              / league["league_plate_appearances"]
                                              * PLATE_APPEARANCES_PER_SEASON)
    h = h.merge(league[["game_year", "league_chase_cost_per_600_pa"]], on="game_year", how="left")
    h["chase_plus_raw"] = 100 + 100 * h["runs_saved_per_600_pa"] / h["league_chase_cost_per_600_pa"]
    h["chase_plus_se"] = 100 * h["standard_error_per_600_pa"] / h["league_chase_cost_per_600_pa"]

    h = h.merge(floors[["game_year", "minimum_opportunities", "minimum_plate_appearances"]],
                on="game_year", how="left")
    measured = (h["standard_error_per_600_pa"] > 0) & h["standard_error_per_600_pa"].notna()
    meets = (measured & (h["opportunities"] >= h["minimum_opportunities"])
             & (h["plate_appearances"] >= h["minimum_plate_appearances"]))
    q = h[meets].copy()

    shrunk, scale_rows = [], []
    for season in sorted(q["game_year"].unique()):
        one = q[q["game_year"] == season].copy()
        pool_min = settings["shrink_pool_minimum_opportunities"]
        pool = (one if pool_min is None else
                h[(h["game_year"] == season) & measured & (h["opportunities"] >= pool_min)])
        tau2, mean, _ = dersimonian_laird(pool["runs_saved_per_600_pa"],
                                          pool["standard_error_per_600_pa"])
        var = one["standard_error_per_600_pa"] ** 2
        one["shrinkage_factor"] = var / (var + tau2) if tau2 > 0 else 1.0
        one["runs_saved_shrunk"] = (one["runs_saved_per_600_pa"]
                                    - one["shrinkage_factor"] * (one["runs_saved_per_600_pa"] - mean))
        one["runs_saved_vs_anchor_shrunk"] = (one["runs_saved_shrunk"]
                                              + one["runs_saved_vs_anchor_per_600_pa"]
                                              - one["runs_saved_per_600_pa"])
        one["chase_rate_rank"] = one["chase_rate"].rank(ascending=True)
        one["value_rank"] = one["runs_saved_shrunk"].rank(ascending=False)
        one["rank_gap"] = one["chase_rate_rank"] - one["value_rank"]
        shrunk.append(one)
        everyone = h[h["game_year"] == season]
        scale = float(everyone["league_chase_cost_per_600_pa"].iloc[0])
        scale_rows.append({
            "game_year": int(season),
            "league_plate_appearances": int(everyone["plate_appearances"].sum()),
            "opportunities_per_pa": everyone["opportunities"].sum() / everyone["plate_appearances"].sum(),
            "league_chase_rate": 100 * everyone["chases"].sum() / everyone["opportunities"].sum(),
            "league_cost_per_chase": everyone["total_cost"].sum() / everyone["chases"].sum(),
            "league_chase_cost_per_600_pa": scale,
            "chase_plus_points_per_run": 100 / scale,
            "runs_saved_for_110": 0.10 * scale, "runs_saved_for_130": 0.30 * scale,
            "league_average_chase_plus": np.average(everyone["chase_plus_raw"],
                                                    weights=everyone["plate_appearances"]),
            "qualified": len(one),
            "shrinkage_pool": len(pool),
            "talent_sd_chase_plus": 100 * np.sqrt(tau2) / scale,
            "shrink_target_chase_plus": 100 + 100 * mean / scale,
            "true_spread": float(np.sqrt(tau2)), "pooled_mean": float(mean),
        })
    q = pd.concat(shrunk, ignore_index=True)
    q["chase_plus"] = 100 + 100 * q["runs_saved_shrunk"] / q["league_chase_cost_per_600_pa"]
    q["chase_plus_posterior_sd"] = q["chase_plus_se"] * np.sqrt(1 - q["shrinkage_factor"])
    return q, h, pd.DataFrame(scale_rows)


# The step 04 files, in step 04's column order.
LEADERBOARD_COLUMNS = [
    "batter", "player", "game_year", "plate_appearances", "opportunities", "chases", "chase_rate",
    "cost_per_chase", "cost_per_chase_se", "runs_saved_per_600_pa", "runs_saved_shrunk",
    "standard_error_per_600_pa", "chase_plus", "chase_plus_raw", "chase_plus_se",
    "chase_plus_posterior_sd", "league_chase_cost_per_600_pa", "runs_saved_vs_anchor_per_600_pa",
    "runs_saved_vs_anchor_shrunk", "runs_saved_count_only_per_600_pa", "shrinkage_factor",
    "chase_rate_rank", "value_rank", "rank_gap", "total_cost", "expected_cost",
    "expected_cost_anchor", "mean_runs_saved", "standard_deviation", "scale_to_600_pa",
]

PITCH_COST_COLUMNS = [
    "game_pk", "at_bat_number", "pitch_number", "batter", "pitcher", "game_year", "count_state",
    "balls", "strikes", "distance_outside_zone", "distance_bucket", "is_chase",
    "called_strike_rate", "value_if_taken", "value_if_swung", "chase_cost",
    "expected_cost_per_pitch", "expected_cost_count_only", "expected_cost_anchor", "runs_saved",
    "runs_saved_vs_anchor",
]


def for_saving(table, expected_contact):
    """Step 04's renaming: the xChase+ files say xchase_plus."""

    if not expected_contact:
        return table
    return table.rename(columns=lambda c: c.replace("chase_plus", "xchase_plus"))
