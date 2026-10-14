"""
Shared rules for the coaching steps: the labels a card's leaks are built
on, the leak rule itself, and the count check.

Steps 15 (count check), 16 (leak backtest), 17 (player cards) and 19
(frozen predictions) all import from here, so a leak means the same
thing in all of them.

LABELS
  count_group   first (0-0), ahead (1-0 2-0 3-0 2-1 3-1),
                even (0-1 1-1), two (any two-strike count)
  pitch_group   fastball / breaking / offspeed
  region        side of the zone missed (card_surfaces.zone_region),
                measured against each season's average zone height

THE LEAK RULE (one hitter, one count group x pitch group x region)
  at least LEAK_MIN_PITCHES pitches; choices cost at least LEAK_MIN_RUNS
  per 600 PA; more chases than the league would make on the same
  pitches; and the chases there lose runs overall (choices + contact
  < 0), so a pitch the hitter does damage on is never called a leak.

THE COUNT CHECK
  How a hitter does once a plate appearance reaches a count group: the
  xwOBA of every plate appearance that passed through one of its counts,
  against the league's in the same counts. Raw count splits are mostly
  the count itself (the league's xwOBA after reaching a hitter's count is
  far above its xwOBA after two strikes) and mostly noise beyond the
  hitter's overall level, so the estimate is built in two shrunk parts:

      league in these counts
      + the hitter's overall level           (shrunk, DerSimonian-Laird)
      + how much better or worse he does in  (shrunk the same way, on its
        these counts than his overall level   own, much smaller spread)

  Each part is shrunk by how much hitters really differ in it that
  season, so a count split that does not repeat (being ahead in the count)
  collapses to the hitter's overall level, and one that does (two
  strikes) keeps most of its signal.
"""

import numpy as np
import pandas as pd

import card_surfaces as cs

FASTBALLS = {"FF", "SI", "FC", "FA"}
BREAKING = {"SL", "ST", "CU", "KC", "SV", "CS"}
WHIFFS = {"swinging_strike", "swinging_strike_blocked", "foul_tip"}

COUNT_GROUPS = ["first", "ahead", "even", "two"]
LEAK_CELL = ["count_group", "pitch_group", "region"]
LEAK_MIN_PITCHES = 12
LEAK_MIN_RUNS = 0.75            # runs per 600 PA, to be listed as a leak
PLAN_MIN_RUNS = 1.0             # ...and to make the plan
LEAK_TOP = 3

# The backtest's league expectation for a pitch (steps 16 and 19): the
# league's chase rate in the same season, count, distance bucket, pitch
# group and side of the zone. The 2026 predictions are frozen on this
# scale, so the 2027 run of step 16 that scores them must keep it.
BACKTEST_LEAGUE_CELL = ["game_year", "count_state", "distance_bucket", "pitch_group", "region"]

# The count check: a count group's verdict, in xwOBA points against the
# league in the same counts (shrunk estimate).
COUNT_MARGIN = 0.010

PA_KEY = ["game_pk", "at_bat_number"]

HITS = {"single": 1, "double": 2, "triple": 3, "home_run": 4}
WALKS = {"walk", "intent_walk"}
SAC_FLIES = {"sac_fly", "sac_fly_double_play"}
NOT_AT_BATS = WALKS | SAC_FLIES | {"hit_by_pitch", "sac_bunt", "sac_bunt_double_play",
                                   "catcher_interf", "truncated_pa"}


def count_group(balls, strikes):
    balls = np.asarray(balls)
    strikes = np.asarray(strikes)
    return np.select([(balls == 0) & (strikes == 0), strikes == 2, balls > strikes],
                     ["first", "two", "ahead"], "even")


def pitch_group(pitch_type):
    pitch_type = pd.Series(pitch_type)
    return np.select([pitch_type.isin(FASTBALLS), pitch_type.isin(BREAKING)],
                     ["fastball", "breaking"], "offspeed")


def add_labels(df, zone_height):
    """count_group, pitch_group and region, in place. zone_height is one
    number per call (the season's average zone height, as step 17 draws it)."""

    df["count_group"] = count_group(df["balls"], df["strikes"])
    df["pitch_group"] = pitch_group(df["pitch_type"].to_numpy())
    df["region"] = cs.zone_region(df["plate_x_batter"],
                                  df["plate_z_normalized"] * zone_height, zone_height)
    return df


def add_choices_contact(df, cell=("balls", "strikes", "distance_bucket")):
    """The decision / execution split of steps 12-13, named as the cards
    name it: choices + contact = runs_saved on every pitch. The league
    cost per chase comes from the rows passed in, within `cell`."""

    cell = list(cell)
    cost = (df[df["is_chase"] == 1].groupby(cell)["chase_cost"].mean()
            .rename("league_cost_per_chase"))
    df = df.drop(columns="league_cost_per_chase", errors="ignore").join(cost, on=cell)
    df["league_cost_per_chase"] = df["league_cost_per_chase"].fillna(0.0)
    df["choices"] = df["expected_cost_per_pitch"] - df["is_chase"] * df["league_cost_per_chase"]
    df["contact"] = df["is_chase"] * (df["league_cost_per_chase"] - df["chase_cost"])
    if not np.allclose(df["choices"] + df["contact"], df["runs_saved"]):
        raise SystemExit("choices + contact does not reproduce runs_saved.")
    return df


def leak_cells(p, scale, expected):
    """Every cell of one hitter's pitches that passes the leak rule,
    costliest first. `expected` names the column holding the league's
    chance of a chase on each pitch; `scale` is 600 / plate appearances."""

    p = p[p["region"] != "edge"]
    if p.empty:
        return pd.DataFrame(columns=LEAK_CELL + ["pitches", "chases", "rate", "league",
                                                 "extra_chases", "choices", "contact"])
    g = p.assign(_extra=p["is_chase"] - p[expected]).groupby(LEAK_CELL)
    t = pd.DataFrame({
        "pitches": g.size(),
        "chases": g["is_chase"].sum(),
        "rate": g["is_chase"].mean(),
        "league": g[expected].mean(),
        "extra_chases": g["_extra"].sum(),
        "choices": g["choices"].sum() * scale,
        "contact": g["contact"].sum() * scale,
    })
    keep = ((t["pitches"] >= LEAK_MIN_PITCHES) & (t["choices"] <= -LEAK_MIN_RUNS)
            & (t["extra_chases"] > 0) & (t["choices"] + t["contact"] < 0))
    return t[keep].sort_values("choices", kind="stable").reset_index()


# --------------------------------------------------
# PLATE APPEARANCES AND THE COUNT CHECK
# --------------------------------------------------

def plate_appearances(pitches):
    """One row per plate appearance that ends in the pitch file, with its
    xwOBA value (Savant's: the expected value of a ball in play, the actual
    wOBA value of everything else) and wOBA value. Only plate appearances
    in the wOBA denominator are kept (no intentional walks, sacrifice
    bunts or truncated PAs). OPS pieces ride along for display."""

    ends = pitches[pitches["events"].notna()].copy()
    ends = ends[ends["events"] != "truncated_pa"]
    in_play = ends["description"] == "hit_into_play"
    has_x = ends["estimated_woba_using_speedangle"].notna()
    ends["x"] = np.where(in_play & has_x, ends["estimated_woba_using_speedangle"],
                         ends["woba_value"]).astype(float)
    ends["w"] = ends["woba_value"].astype(float)
    ends["in_woba"] = (ends["woba_denom"] == 1).fillna(False).astype(bool)
    ev = ends["events"]
    ends["bases"] = ev.map(HITS).fillna(0).astype(int)
    ends["hit"] = (ends["bases"] > 0).astype(int)
    ends["on_base"] = (ends["hit"] + ev.isin(WALKS | {"hit_by_pitch"})).astype(int)
    ends["obp_denom"] = (~ev.isin({"sac_bunt", "sac_bunt_double_play", "catcher_interf"})).astype(int)
    ends["at_bat"] = (~ev.isin(NOT_AT_BATS)).astype(int)
    ends["strikeout"] = ev.isin({"strikeout", "strikeout_double_play"}).astype(int)
    ends["walk"] = (ev == "walk").astype(int)
    keep = PA_KEY + ["batter", "game_year", "x", "w", "in_woba", "bases", "hit", "on_base",
                     "obp_denom", "at_bat", "strikeout", "walk"]
    return ends[keep].reset_index(drop=True)


def through_counts(pitches, pas):
    """One row per plate appearance and count group it passed through,
    carrying the plate appearance's outcome. Plate appearances outside the
    wOBA denominator are dropped (they have no xwOBA)."""

    seen = pitches[PA_KEY + ["balls", "strikes"]].copy()
    seen["count_group"] = count_group(seen["balls"], seen["strikes"])
    seen = seen[PA_KEY + ["count_group"]].drop_duplicates()
    out = seen.merge(pas[pas["in_woba"]], on=PA_KEY, how="inner")
    return out


def dersimonian_laird(y, s2):
    """Pooled mean and between-unit variance (tau^2) of estimates y with
    sampling variances s2."""

    y = np.asarray(y, float)
    w = 1.0 / np.asarray(s2, float)
    mu = (w * y).sum() / w.sum()
    q = (w * (y - mu) ** 2).sum()
    denom = w.sum() - (w ** 2).sum() / w.sum()
    tau2 = max(0.0, (q - (len(y) - 1)) / denom) if denom > 0 else 0.0
    return mu, tau2


def count_check(through, hitters):
    """The count check for every hitter in `hitters` (a set of batter ids)
    in one period (one season, or one half of one). `through` is that
    period's through_counts() for every hitter; the league in each count
    group is everyone, the shrinkage is fit across `hitters`.

    Returns one row per hitter and count group: plate appearances, raw
    xwOBA, the league's, the shrunk estimate and its gap to the league,
    plus raw wOBA and OPS (over the same plate appearances) for reference."""

    league = through.groupby("count_group").agg(lg_x=("x", "mean"), lg_var=("x", "var"),
                                                lg_w=("w", "mean"))
    league["lg_ops"] = ops(through, ["count_group"])
    mine = through[through["batter"].isin(hitters)]
    raw = mine.groupby(["batter", "count_group"]).agg(pa=("x", "size"), x=("x", "mean"),
                                                      w=("w", "mean"))
    raw["ops"] = ops(mine, ["batter", "count_group"])
    raw = raw.join(league, on="count_group").reset_index()

    # Overall level: every plate appearance passes through 0-0.
    overall = raw[raw["count_group"] == "first"].set_index("batter")
    dev = overall["x"] - overall["lg_x"]
    s2 = overall["lg_var"] / overall["pa"]
    mu, tau2 = dersimonian_laird(dev, s2)
    level = mu + (dev - mu) * tau2 / (tau2 + s2)
    shrink = {"first": tau2 / (tau2 + s2)}

    raw = raw.join(overall[["x", "pa"]].rename(columns={"x": "x_all", "pa": "pa_all"}), on="batter")
    raw["level"] = raw["batter"].map(level)
    raw["extra"] = 0.0
    raw["extra_weight"] = np.nan
    for group in COUNT_GROUPS[1:]:
        rows = raw["count_group"] == group
        r = raw[rows]
        # these counts minus the hitter's overall level; the plate
        # appearances are a subset of his total, hence the variance
        resid = (r["x"] - r["lg_x"]) - (r["x_all"] - overall["lg_x"].iloc[0])
        rs2 = r["lg_var"] * (1.0 / r["pa"] - 1.0 / r["pa_all"]).clip(lower=1e-6)
        mu_g, tau2_g = dersimonian_laird(resid, rs2)
        weight = tau2_g / (tau2_g + rs2)
        raw.loc[rows, "extra"] = mu_g + (resid - mu_g) * weight
        raw.loc[rows, "extra_weight"] = weight
    raw["x_shrunk"] = raw["lg_x"] + raw["level"] + raw["extra"]
    raw["gap"] = raw["x_shrunk"] - raw["lg_x"]
    raw["status"] = np.select([raw["gap"] <= -COUNT_MARGIN, raw["gap"] >= COUNT_MARGIN],
                              ["struggling", "productive"], "average")
    raw["level_weight"] = raw["batter"].map(shrink["first"])
    return raw[["batter", "count_group", "pa", "x", "lg_x", "x_shrunk", "gap", "status",
                "level", "extra", "level_weight", "extra_weight", "w", "lg_w", "ops", "lg_ops"]]


def ops(frame, by):
    """OPS by group, over the plate appearances in `frame`."""

    t = frame.groupby(by)[["on_base", "obp_denom", "bases", "at_bat"]].sum()
    return (t["on_base"] / t["obp_denom"].where(t["obp_denom"] > 0)
            + t["bases"] / t["at_bat"].where(t["at_bat"] > 0))


# --------------------------------------------------
# THE BACKTEST'S TOOLS (steps 16 and 20 share them, so a payoff means
# the same thing when it is scored out of sample as when it was fit)
# --------------------------------------------------

WOBA_WEIGHTS = {"walk": 0.7, "hit_by_pitch": 0.7, "single": 0.9, "double": 1.25,
                "triple": 1.6, "home_run": 2.0}   # Savant's, every season 2021-2026
OUT_EVENTS = ["field_out", "strikeout", "force_out", "grounded_into_double_play",
              "double_play", "fielders_choice_out", "strikeout_double_play"]


def woba_scale(run_values):
    """Each season's wOBA scale: Savant's weights fit against this
    project's run values above an average out. One number per season."""

    scale = {}
    for season, r in run_values.groupby("game_year"):
        r = r.set_index("event")
        outs = r.loc[[e for e in OUT_EVENTS if e in r.index]]
        out_value = (outs["run_value"] * outs["occurrences"]).sum() / outs["occurrences"].sum()
        above = np.array([r.loc[e, "run_value"] - out_value for e in WOBA_WEIGHTS])
        freq = np.array([r.loc[e, "occurrences"] for e in WOBA_WEIGHTS])
        weight = np.array(list(WOBA_WEIGHTS.values()))
        scale[season] = (freq * weight * above).sum() / (freq * above * above).sum()
    return pd.Series(scale)


def ols(y, columns, cluster):
    """OLS with an intercept; standard errors clustered by `cluster`.
    Returns (coefficients, standard errors), the intercept first."""

    X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in columns])
    y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    bread = np.linalg.inv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    cluster = np.asarray(cluster)
    for c in np.unique(cluster):
        s = X[cluster == c].T @ resid[cluster == c]
        meat += np.outer(s, s)
    groups = len(np.unique(cluster))
    cov = bread @ meat @ bread * groups / (groups - 1)
    return beta, np.sqrt(np.diag(cov))
