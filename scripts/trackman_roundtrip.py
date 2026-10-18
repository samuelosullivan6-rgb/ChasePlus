"""
The college path, tested without college data: 2026 Statcast pitches
written as TrackMan files, run through the adapter and the college build,
and compared with the MLB build on the same pitches.

    python scripts/trackman_roundtrip.py            # all three parts, KC's first 60 games
    python scripts/trackman_roundtrip.py --team NYY --skip-study

THREE PARTS

  1. Parity. college_method.py with step 03's and step 04's settings on
     all 2026 MLB pitches must reproduce steps 03 and 04 exactly (count and
     event run values, every pitch's price, every hitter's xChase+). It
     stops if anything differs by more than 1e-9, so every difference
     below is a college choice, not a copying slip.
  2. The settings study. Every team's first 60 games of 2026 (about
     17,500 pitches, a college season's worth) priced as a college league
     on its own, for each choice of baseline cells and count run values,
     and compared with the MLB build's price of the same pitches; then the
     shrinkage choices, scored on how well each slice predicts the same
     hitters' next 100 games. This is what picked COLLEGE_SETTINGS.
  3. The round trip. One team's 60 games converted to TrackMan CSVs
     (statcast_to_trackman.py), built by college_build.py exactly as a
     college season would be, and compared with the MLB build: how
     faithfully the adapter rebuilt the pitches, each pitch's price, each
     hitter's xChase+ and leaks, and how much of the difference each
     ingredient explains (each one swapped for the MLB build's in turn).

Writes results/trackman_roundtrip/ (README.md and the CSVs behind it).
Those are MLB data and are committed; the college build it runs lives in
college/roundtrip_<team>/, which is not.

Needs the 2026 raw Statcast files (step 01), step 02's cleaned pitches,
step 03's tables, step 04's xChase+ files and step 17's 2026 card data.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))
import college_build as cb  # noqa: E402
import college_method as cm  # noqa: E402
import leak_rules as lr  # noqa: E402
import statcast_to_trackman as st  # noqa: E402
import trackman_adapter as ta  # noqa: E402

SEASON = 2026
CLEAN = PROJECT_DIR / "data" / "cleaned"
RESULTS = PROJECT_DIR / "results"
OUT = RESULTS / "trackman_roundtrip"
KEYS = ["game_pk", "at_bat_number", "pitch_number"]
PA = 600

PITCH_COLUMNS = [
    "game_pk", "at_bat_number", "pitch_number", "batter", "pitcher", "game_year", "description",
    "events", "balls", "strikes", "count_state", "is_analyzable", "is_outside_zone", "is_swing",
    "is_chase", "distance_outside_zone", "plate_x", "plate_z", "sz_top", "sz_bot", "inning",
    "inning_topbot", "outs_when_up", "bat_score", "post_bat_score", "fld_score", "runner_on_1b",
    "runner_on_2b", "runner_on_3b", "estimated_woba_using_speedangle", "stand", "p_throws",
    "pitch_type", "plate_x_batter", "plate_z_normalized", "is_in_zone", "home_team", "away_team",
]

# The study's choices. Baseline cells: (counts, distance bins, labels).
BASELINES = {
    "12 counts x 4 buckets (MLB)": ("count", [-0.001, 0.15, 0.35, 0.70, 100],
                                    ["borderline", "just off", "clearly off", "nowhere near"]),
    "12 counts x 3 buckets": ("count", [-0.001, 0.15, 0.35, 100],
                              ["borderline", "just off", "clearly off"]),
    "12 counts x 2 buckets": ("count", [-0.001, 0.35, 100], ["just off", "clearly off"]),
    "12 counts, no buckets": ("count", [-0.001, 100], ["off"]),
    "4 count groups x 4 buckets": ("count_group", [-0.001, 0.15, 0.35, 0.70, 100],
                                   ["borderline", "just off", "clearly off", "nowhere near"]),
    "4 count groups x 2 buckets": ("count_group", [-0.001, 0.35, 100], ["just off", "clearly off"]),
}
COUNT_VALUE_CHOICES = ["event", "plate_appearance"]
SHRINK_POOLS = [None, 20, 40, 80, 150]          # None: the qualified hitters only
STUDY_GAMES = 60


def log(*values):
    print(*values, flush=True)


# --------------------------------------------------
# THE MLB BUILD, 2026
# --------------------------------------------------

def load_mlb():
    log("Loading the 2026 MLB build...")
    pitches = pd.read_parquet(CLEAN / "baseline_chase_pitches.parquet",
                              columns=[c for c in PITCH_COLUMNS if c not in ("home_team", "away_team")])
    pitches = pitches[pitches["game_year"] == SEASON].reset_index(drop=True)
    raw = st.load_statcast(SEASON)
    contact = raw[KEYS + ["launch_speed", "launch_angle", "bb_type", "des", "home_team",
                          "away_team"]]
    pitches = pitches.merge(contact, on=KEYS, how="left", validate="one_to_one")
    pitches["is_bunt"] = ((pitches["description"] == "hit_into_play")
                          & (pitches["des"].fillna("").str.contains("bunt", case=False)
                             | (pitches["events"] == "sac_bunt"))).astype(int)

    costs = pd.read_parquet(CLEAN / "xchase_costs_by_pitch.parquet")
    costs = costs[costs["game_year"] == SEASON].reset_index(drop=True)
    scale = pd.read_csv(RESULTS / "xchase" / "chase_plus_league_scale.csv").set_index("game_year").loc[SEASON]
    board = pd.read_csv(RESULTS / "xchase" / "chase_cost_leaderboard_2026.csv")
    counts = pd.read_csv(RESULTS / "run_values" / "run_value_by_count.csv")
    events = pd.read_csv(RESULTS / "run_values" / "run_value_by_event.csv")
    league_cost = float(scale["league_chase_cost_per_600_pa"])
    tau = float(scale["talent_sd_xchase_plus"]) / 100 * league_cost
    mean = (float(scale["shrink_target_xchase_plus"]) - 100) / 100 * league_cost

    # Step 17's per-pitch labels and league expectation, in step 17's row
    # order (its df is step 04's costs joined to step 02's pitches), and
    # the choices / contact split on the whole league.
    card = pd.read_parquet(CLEAN / f"card_pitches_{SEASON}.parquet")
    order = costs.merge(pitches[KEYS + ["batter", "game_year", "plate_x_batter", "plate_z_normalized",
                                        "description"]],
                        on=KEYS + ["batter", "game_year"], how="left", validate="one_to_one")
    order = order[order["plate_x_batter"].notna() & order["plate_z_normalized"].notna()].reset_index(drop=True)
    if len(order) != len(card) or not (order["batter"].to_numpy() == card["batter"].to_numpy()).all() \
            or not (order["is_chase"].to_numpy() == card["is_chase"].to_numpy()).all():
        raise SystemExit("Step 17's card pitches no longer line up with step 04's costs; rerun step 17.")
    for col in ("count_group", "pitch_group", "region", "stand", "p_throws"):
        order[col] = card[col].to_numpy()
    order["e_match"] = card["e_match_q"].to_numpy() / 255
    order = lr.add_choices_contact(order)
    players = json.loads((CLEAN / f"card_players_{SEASON}.json").read_text())["players"]
    register = pd.read_parquet(PROJECT_DIR / "data" / "raw" / "chadwick_register.parquet")
    register = register.dropna(subset=["key_mlbam"]).drop_duplicates("key_mlbam")
    names = pd.Series((register["name_first"].str.strip() + " " + register["name_last"].str.strip()).to_numpy(),
                      index=register["key_mlbam"].astype("int64").to_numpy())
    return {"pitches": pitches, "costs": costs, "board": board, "league_cost": league_cost,
            "tau2": tau ** 2, "mean": mean, "counts": counts[counts["game_year"] == SEASON],
            "events": events[events["game_year"] == SEASON], "card": order, "players": players,
            "raw": raw, "names": names}


def parity(mlb):
    """college_method with MLB settings == steps 03 and 04, 2026."""

    log("\nPart 1: parity with steps 03 and 04 on every 2026 pitch...")
    rv = cm.run_value_tables(mlb["pitches"], cm.MLB_SETTINGS)
    gaps = {}
    c = rv["counts"].merge(mlb["counts"], on=["game_year", "count_state"], suffixes=("", "_mlb"))
    gaps["count run values"] = (c["run_value"] - c["run_value_mlb"]).abs().max()
    e = rv["events"].merge(mlb["events"], on=["game_year", "event"], suffixes=("", "_mlb"))
    gaps["event run values"] = (e["run_value"] - e["run_value_mlb"]).abs().max()
    opp, diag = cm.price(mlb["pitches"], rv, cm.MLB_SETTINGS, expected_contact=True)
    m = opp.merge(mlb["costs"], on=KEYS, suffixes=("", "_mlb"))
    for col in ("called_strike_rate", "chase_cost", "expected_cost_per_pitch", "runs_saved"):
        gaps[col] = (m[col] - m[col + "_mlb"]).abs().max()
    q, _, scale = cm.hitter_seasons(opp, mlb["pitches"], cm.MLB_SETTINGS)
    b = q.merge(mlb["board"], on="batter", suffixes=("", "_mlb"))
    gaps["xChase+"] = (b["chase_plus"] - b["xchase_plus"]).abs().max()
    rows = [{"check": k, "max_abs_difference": float(v)} for k, v in gaps.items()]
    rows.append({"check": "pitches priced (college method / step 04)",
                 "max_abs_difference": float(len(opp) - len(mlb["costs"]))})
    rows.append({"check": "qualified hitters (college method / step 04)",
                 "max_abs_difference": float(len(q) - len(mlb["board"]))})
    table = pd.DataFrame(rows)
    log(table.to_string(index=False))
    if (table["max_abs_difference"].abs() > 1e-9).any():
        raise SystemExit("college_method.py no longer reproduces steps 03 and 04.")
    line = diag["xwoba_line"].iloc[0]
    return table, {"in_play_values": diag["in_play_values"],
                   "xwoba_line": {SEASON: (float(line["slope"]), float(line["intercept"]))}}


# --------------------------------------------------
# ONE SLICE PRICED AS ITS OWN LEAGUE
# --------------------------------------------------

def slice_games(mlb, team, games=STUDY_GAMES):
    p = mlb["pitches"]
    played = p[(p["home_team"] == team) | (p["away_team"] == team)]
    dates = mlb["raw"].drop_duplicates("game_pk").set_index("game_pk")["game_date"]
    first = (pd.Series(played["game_pk"].unique()).to_frame("game_pk")
             .assign(date=lambda f: f["game_pk"].map(dates))
             .sort_values(["date", "game_pk"], kind="stable").head(games)["game_pk"])
    return set(first)


def college_inputs(p, settings):
    """A slice's run values, wOBA weights and xwOBA, as college_build fits
    them (the slice's own plate appearances and batted balls)."""

    rv = cm.run_value_tables(p, settings)
    weights = cm.woba_weights(rv["events"])
    p = p.copy()
    p["woba_value"], p["woba_denom"] = cm.woba_columns(p, weights)
    in_play = p["description"] == "hit_into_play"
    predict, fit = cm.fit_xwoba(p[in_play])
    p["savant_xwoba"] = p["estimated_woba_using_speedangle"]
    p.loc[in_play, "estimated_woba_using_speedangle"] = predict(p[in_play]).to_numpy()
    return p, rv, fit


def hitters_vs_mlb(q, opp, mlb, team_pitches, rest_pitches):
    """Each qualified slice hitter next to the MLB build on the same
    pitches (raw, and shrunk with the MLB season's own prior), on his
    other games (rest of season), and over the full season."""

    costs = mlb["costs"]
    same = costs.merge(team_pitches[KEYS], on=KEYS)
    rest = costs.merge(rest_pitches[KEYS], on=KEYS)

    def per_600(c, pitches):
        pa = (pitches[pitches["is_analyzable"] == 1].drop_duplicates(["game_pk", "at_bat_number"])
              .groupby("batter").size().rename("pa"))
        g = c.groupby("batter")["runs_saved"].agg(["sum", "std", "size"]).join(pa)
        g["runs"] = g["sum"] / g["pa"] * PA
        g["se"] = g["std"] / np.sqrt(g["size"]) * g["size"] / g["pa"] * PA
        return g

    s = per_600(same, team_pitches)
    s["shrunk"] = s["runs"] - s["se"] ** 2 / (s["se"] ** 2 + mlb["tau2"]) * (s["runs"] - mlb["mean"])
    r = per_600(rest, rest_pitches)
    full = mlb["board"].set_index("batter")
    out = q[["batter", "plate_appearances", "runs_saved_per_600_pa", "runs_saved_shrunk",
             "chase_plus", "chase_plus_raw", "league_chase_cost_per_600_pa",
             "standard_error_per_600_pa"]].copy()
    out.insert(1, "player", out["batter"].map(mlb["names"]))
    out["mlb_same_runs"] = out["batter"].map(s["runs"])
    out["mlb_same_shrunk"] = out["batter"].map(s["shrunk"])
    out["mlb_rest_runs"] = out["batter"].map(r["runs"])
    out["mlb_rest_pa"] = out["batter"].map(r["pa"])
    out["mlb_full_xchase_plus"] = out["batter"].map(full["xchase_plus"])
    lc = mlb["league_cost"]
    out["xchase_plus_mlb_same_raw"] = 100 + 100 * out["mlb_same_runs"] / lc
    out["xchase_plus_mlb_same"] = 100 + 100 * out["mlb_same_shrunk"] / lc
    return out


def rmse(a, b):
    d = (pd.Series(a) - pd.Series(b)).dropna()
    return float(np.sqrt((d ** 2).mean())) if len(d) else np.nan


# --------------------------------------------------
# PART 2: THE SETTINGS STUDY
# --------------------------------------------------

def study(mlb, teams):
    log(f"\nPart 2: the settings study, {len(teams)} teams' first {STUDY_GAMES} games...")
    raw_rows, shrink_rows = [], []
    p_all = mlb["pitches"]
    for i, team in enumerate(teams, 1):
        t0 = time.time()
        games = slice_games(mlb, team)
        p = p_all[p_all["game_pk"].isin(games)]
        team_games_all = p_all[(p_all["home_team"] == team) | (p_all["away_team"] == team)]
        rest = team_games_all[~team_games_all["game_pk"].isin(games)]
        for count_values in COUNT_VALUE_CHOICES:
            base = {**cm.COLLEGE_SETTINGS, "count_values_from": count_values,
                    "final_half_rule": "ninth_inning"}
            pp, rv, _ = college_inputs(p, base)
            for label, (counts, bins, labels) in BASELINES.items():
                settings = {**base, "baseline_counts": counts, "distance_bins": bins,
                            "distance_labels": labels}
                opp, _ = cm.price(pp, rv, settings, expected_contact=True)
                q, h, _ = cm.hitter_seasons(opp, pp, settings)
                team_q = q[q["batter"].isin(p.loc[np.where(p["inning_topbot"] == "Top",
                                                           p["away_team"], p["home_team"]) == team,
                                                  "batter"])]
                cmp = hitters_vs_mlb(team_q, opp, mlb, p, rest)
                for r in cmp.itertuples():
                    raw_rows.append({"team": team, "count_values": count_values, "baseline": label,
                                     "batter": r.batter, "player": r.player,
                                     "plate_appearances": r.plate_appearances,
                                     "college_runs": r.runs_saved_per_600_pa,
                                     "mlb_same_runs": r.mlb_same_runs,
                                     "college_xchase_plus_raw": r.chase_plus_raw,
                                     "mlb_same_xchase_plus_raw": r.xchase_plus_mlb_same_raw})
                chosen = cm.COLLEGE_SETTINGS
                if (count_values == chosen["count_values_from"] and counts == chosen["baseline_counts"]
                        and bins == chosen["distance_bins"]):
                    for pool in SHRINK_POOLS:
                        sq, _, sscale = cm.hitter_seasons(
                            opp, pp, {**settings, "shrink_pool_minimum_opportunities": pool})
                        sq = sq[sq["batter"].isin(team_q["batter"])]
                        c2 = hitters_vs_mlb(sq, opp, mlb, p, rest)
                        for r in c2.itertuples():
                            shrink_rows.append({
                                "team": team, "pool": "qualified only" if pool is None else f"{pool}+ out-of-zone pitches",
                                "batter": r.batter, "college_shrunk": r.runs_saved_shrunk,
                                "college_raw": r.runs_saved_per_600_pa,
                                "mlb_same_shrunk": r.mlb_same_shrunk, "mlb_same_raw": r.mlb_same_runs,
                                "rest_runs": r.mlb_rest_runs, "rest_pa": r.mlb_rest_pa,
                                "talent_sd_xchase_plus": float(sscale["talent_sd_chase_plus"].iloc[0]),
                                "pool_size": int(sscale["shrinkage_pool"].iloc[0])})
        log(f"  {i:2d}/{len(teams)} {team}: {len(p):,} pitches, {len(team_q)} qualified "
            f"({time.time() - t0:.0f}s)")
    raw = pd.DataFrame(raw_rows)
    shrink = pd.DataFrame(shrink_rows)

    summary = (raw.groupby(["baseline", "count_values"], sort=False)
               .apply(lambda g: pd.Series({
                   "hitters": len(g),
                   "rmse_runs_per_600": rmse(g["college_runs"], g["mlb_same_runs"]),
                   "mean_gap_runs_per_600": float((g["college_runs"] - g["mlb_same_runs"]).mean()),
                   "correlation": float(g["college_runs"].corr(g["mlb_same_runs"])),
                   "rmse_xchase_plus_raw": rmse(g["college_xchase_plus_raw"], g["mlb_same_xchase_plus_raw"]),
               }), include_groups=False).reset_index())
    pools = (shrink.groupby("pool", sort=False)
             .apply(lambda g: pd.Series({
                 "hitters": len(g),
                 "median_pool_size": float(g.drop_duplicates("team")["pool_size"].median()),
                 "median_talent_sd_xchase_plus": float(g.drop_duplicates("team")["talent_sd_xchase_plus"].median()),
                 "rmse_vs_rest_of_season": rmse(g["college_shrunk"], g["rest_runs"]),
                 "rmse_vs_mlb_same_pitches_shrunk": rmse(g["college_shrunk"], g["mlb_same_shrunk"]),
             }), include_groups=False).reset_index())
    first = shrink[shrink["pool"] == shrink["pool"].iloc[0]]
    references = pd.DataFrame([
        {"pool": "no shrinkage (raw slice)", "hitters": len(first),
         "rmse_vs_rest_of_season": rmse(first["college_raw"], first["rest_runs"]),
         "rmse_vs_mlb_same_pitches_shrunk": rmse(first["college_raw"], first["mlb_same_shrunk"])},
        {"pool": "MLB build on the same pitches, its own prior", "hitters": len(first),
         "rmse_vs_rest_of_season": rmse(first["mlb_same_shrunk"], first["rest_runs"]),
         "rmse_vs_mlb_same_pitches_shrunk": 0.0},
    ])
    pools = pd.concat([pools, references], ignore_index=True)
    log(summary.round(3).to_string(index=False))
    log(pools.round(3).to_string(index=False))
    return raw, shrink, summary, pools


# --------------------------------------------------
# PART 3: THE ROUND TRIP
# --------------------------------------------------

def key_map(raw_college):
    """College pitch keys -> the Statcast pitch they came from (the round
    trip writes the Statcast pitch into TrackMan's PitchUID)."""

    sk = raw_college["trackman_pitch_uid"].str.split("-", expand=True).astype("int64")
    return pd.DataFrame({"game_pk": raw_college["game_pk"], "at_bat_number": raw_college["at_bat_number"],
                         "pitch_number": raw_college["pitch_number"], "sc_game_pk": sk[0],
                         "sc_at_bat_number": sk[1], "sc_pitch_number": sk[2]})


def to_statcast_keys(frame, km):
    out = frame.merge(km, on=KEYS, how="left", validate="one_to_one")
    return out.drop(columns=KEYS).rename(columns={"sc_" + k: k for k in KEYS})


RESULT_GROUPS = {"single": "single", "double": "double", "triple": "triple", "home_run": "home run",
                 "walk": "walk", "intent_walk": "walk", "hit_by_pitch": "hit by pitch",
                 "strikeout": "strikeout", "strikeout_double_play": "strikeout"}


def adapter_fidelity(mlb, raw_c, clean_c, km, facts, games):
    """How faithfully the adapter rebuilt the pitches, as numbers."""

    p = mlb["pitches"][mlb["pitches"]["game_pk"].isin(games)]
    c = to_statcast_keys(clean_c, km).merge(p, on=KEYS, suffixes=("", "_sc"), validate="one_to_one")
    r = to_statcast_keys(raw_c, km).merge(p, on=KEYS, suffixes=("", "_sc"), validate="one_to_one")
    first = r[r["pitch_number"] == 1]
    rebuilt = (first["on_1b"].notna().astype(int).astype(str) + first["on_2b"].notna().astype(int).astype(str)
               + first["on_3b"].notna().astype(int).astype(str))
    truth = (first["runner_on_1b"].astype(str) + first["runner_on_2b"].astype(str)
             + first["runner_on_3b"].astype(str))
    ends = r[r["events_sc"].notna()]
    bip = c[(c["description_sc"] == "hit_into_play") & c["estimated_woba_using_speedangle_sc"].notna()]
    analyzable = c["is_analyzable_sc"] == 1
    return {
        "sign_found": facts["adapter"]["plate_side_sign"],
        "pitches": len(raw_c), "pitches_statcast": len(p),
        "analyzable_same": float((c["is_analyzable"] == c["is_analyzable_sc"]).mean()),
        "zone_same": float((c.loc[analyzable, "is_in_zone"] == c.loc[analyzable, "is_in_zone_sc"]).mean()),
        "zone_gap_in": float(12 * max((c["sz_top"] - c["sz_top_sc"]).abs().max(),
                                      (c["sz_bot"] - c["sz_bot_sc"]).abs().max())),
        "results_same": float((ends["events"].map(RESULT_GROUPS).fillna("out")
                               == ends["events_sc"].map(RESULT_GROUPS).fillna("out")).mean()),
        "plate_appearances": len(first),
        "bases_exact": float((rebuilt == truth).mean()),
        "first_right": float((first["on_1b"].notna().astype(int) == first["runner_on_1b"]).mean()),
        "second_right": float((first["on_2b"].notna().astype(int) == first["runner_on_2b"]).mean()),
        "third_right": float((first["on_3b"].notna().astype(int) == first["runner_on_3b"]).mean()),
        "score_right": float((r["bat_score"] == r["bat_score_sc"]).mean()),
        "xwoba_correlation": float(bip["estimated_woba_using_speedangle"].corr(
            bip["estimated_woba_using_speedangle_sc"])),
        "xwoba_mean": float(bip["estimated_woba_using_speedangle"].mean()),
        "xwoba_mean_savant": float(bip["estimated_woba_using_speedangle_sc"].mean()),
        "batted_balls": len(bip),
    }


PITCH_MEASURES = [("called_strike_rate", "called-strike chance if taken", False),
                  ("value_if_taken", "value if taken", False),
                  ("value_if_swung", "value of the swing (chases)", True),
                  ("chase_cost", "chase cost (chases)", True),
                  ("expected_cost_per_pitch", "the league's expected cost (baseline)", False),
                  ("runs_saved", "runs saved", False)]


def pitch_level(matched):
    rows = []
    for col, label, chases_only in PITCH_MEASURES:
        f = matched[matched["is_chase"] == 1] if chases_only else matched
        rows.append({"per pitch": label, "pitches": len(f), "college_mean": f[col].mean(),
                     "mlb_mean": f[col + "_mlb"].mean(), "correlation": f[col].corr(f[col + "_mlb"]),
                     "mean_abs_difference": (f[col] - f[col + "_mlb"]).abs().mean()})
    return pd.DataFrame(rows)


INGREDIENT_WORDS = {
    "run values": "run values (step 03's tables)",
    "expected contact": "expected contact (Savant's xwOBA and its line to runs)",
    "called strikes": "called-strike chance",
}


def decomposition(clean_c, km, rv_c, mlb, bits, games, qualified):
    """Each qualified hitter's raw runs saved per 600 PA, priced again with
    one pricing ingredient at a time taken from the MLB build, then all
    three, then the whole league's baseline on top (the MLB build itself),
    next to the MLB build's on the same pitches."""

    mapped = clean_c[KEYS].merge(km, on=KEYS, how="left")
    sc_index = pd.MultiIndex.from_frame(mapped[["sc_" + k for k in KEYS]].set_axis(KEYS, axis=1))
    college_index = pd.MultiIndex.from_frame(mapped[KEYS])

    def on_college_keys(series_by_sc_key):
        return pd.Series(series_by_sc_key.reindex(sc_index).to_numpy(), index=college_index)

    costs = mlb["costs"].set_index(KEYS)
    savant = mlb["pitches"].set_index(KEYS)["estimated_woba_using_speedangle"]
    swaps = {
        "run values": {"count_values": mlb["counts"], "event_values": mlb["events"],
                       "in_play_values": bits["in_play_values"]},
        "expected contact": {"xwoba": on_college_keys(savant), "xwoba_line": bits["xwoba_line"]},
        "called strikes": {"called_strike_rate": on_college_keys(costs["called_strike_rate"])},
        "league baseline": {"expected_cost_per_pitch": on_college_keys(costs["expected_cost_per_pitch"])},
    }
    p = mlb["pitches"][mlb["pitches"]["game_pk"].isin(games)]
    same = mlb["costs"].merge(p[KEYS], on=KEYS)
    pa = qualified.set_index("batter")["plate_appearances"]

    def runs(swap):
        opp, _ = cm.price(clean_c, rv_c, cm.COLLEGE_SETTINGS, expected_contact=True, swap=swap)
        return (opp.groupby("batter")["runs_saved"].sum().reindex(pa.index) / pa * PA).to_numpy()

    out = pd.DataFrame({"batter": pa.index,
                        "mlb_same": (same.groupby("batter")["runs_saved"].sum().reindex(pa.index) / pa * PA).to_numpy(),
                        "college": runs({})})
    # The league baseline is not swapped on its own: it is the league's
    # average price, so it only means something next to costs priced the
    # same way. Swapping run values, contact or called strikes reprices the
    # 60 games' league too; the whole league's baseline comes in last, on
    # top of all three, and that is the MLB build.
    pricing = {k: v for name in ("run values", "expected contact", "called strikes")
               for k, v in swaps[name].items()}
    for name in ("run values", "expected contact", "called strikes"):
        out[f"with MLB {name}"] = runs(swaps[name])
    out["with all three"] = runs(pricing)
    out["all MLB"] = runs({**pricing, **swaps["league baseline"]})
    return out


def shift_and_spread(a, b, team):
    """A gap's RMSE, split into the team's average gap (one number for every
    hitter on a team: the league) and what is left within the team."""

    gap = pd.Series(np.asarray(a, float) - np.asarray(b, float))
    team = pd.Series(np.asarray(team))
    shift = gap.groupby(team).transform("mean")
    return (float(np.sqrt((gap ** 2).mean())), float(np.sqrt((shift ** 2).mean())),
            float(np.sqrt(((gap - shift) ** 2).mean())))


def decomposition_table(per_hitter):
    def row(label, col):
        total, shift, within = shift_and_spread(per_hitter[col], per_hitter["mlb_same"], per_hitter["team"])
        return {"priced with": label, "rmse_runs_per_600": total, "team_wide": shift, "within_team": within}

    rows = [row("the college build as it is", "college")]
    for name in ("run values", "expected contact", "called strikes"):
        rows.append(row(f"the college build with the MLB build's {INGREDIENT_WORDS[name]}", f"with MLB {name}"))
    rows.append(row("the college build with all three: every pitch priced as the MLB build prices it, "
                    "against the 60 games' own league", "with all three"))
    rows.append(row("...and against the whole MLB league's baseline: the MLB build", "all MLB"))
    return pd.DataFrame(rows)


CELL_WORDS = ({"first": "first pitch", "ahead": "ahead", "even": "0-1 or 1-1", "two": "two strikes"},
              {"fastball": "fastballs", "breaking": "breaking balls", "offspeed": "changeups"},
              {"up": "above", "down": "below", "in": "inside", "away": "away", "up-in": "up and in",
               "up-away": "up and away", "down-in": "down and in", "down-away": "down and away"})


def cell_name(cell):
    group, pitch, region = cell
    return f"{CELL_WORDS[0][group]}, {CELL_WORDS[1][pitch]} {CELL_WORDS[2][region]}"


def leak_rebuild_check(mlb):
    """Step 17's leaks rebuilt here from its stored (quantized) expectation
    must be its cards' leaks, before the rebuild is used on a slice."""

    full = {p["id"]: [tuple(l[k] for k in lr.LEAK_CELL) for l in p["leaks"]["all"]] for p in mlb["players"]}
    pa = mlb["board"].set_index("batter")["plate_appearances"]
    same = []
    for b, g in mlb["card"][mlb["card"]["batter"].isin(pa.index)].groupby("batter"):
        cells = lr.leak_cells(g, PA / pa[b], "e_match").head(lr.LEAK_TOP)
        same.append(list(map(tuple, cells[lr.LEAK_CELL].itertuples(index=False))) == full.get(b, []))
    return float(np.mean(same)), len(same)


def leaks(mlb, cards_c, games, qualified):
    """Each qualified hitter's card leaks (up to three): the college card,
    the MLB build on the same pitches (step 17's expectation and labels,
    the slice's pitches only) and his MLB card for the full season."""

    full = {p["id"]: [tuple(l[k] for k in lr.LEAK_CELL) for l in p["leaks"]["all"]] for p in mlb["players"]}
    in_games = mlb["card"][mlb["card"]["game_pk"].isin(games)]
    college = {p["id"]: [tuple(l[k] for k in lr.LEAK_CELL) for l in p["leaks"]["all"]]
               for p in cards_c["players"]}
    rows = []
    for r in qualified.itertuples():
        g = in_games[in_games["batter"] == r.batter]
        same = lr.leak_cells(g, PA / r.plate_appearances, "e_match").head(lr.LEAK_TOP)
        same = list(map(tuple, same[lr.LEAK_CELL].itertuples(index=False)))
        mine = college.get(r.batter, [])
        season = full.get(r.batter)
        rows.append({
            "batter": r.batter, "player": mlb["names"].get(r.batter, str(r.batter)),
            "college_leaks": "; ".join(map(cell_name, mine)),
            "mlb_same_pitches_leaks": "; ".join(map(cell_name, same)),
            "mlb_full_season_leaks": "; ".join(map(cell_name, season)) if season is not None else "",
            "college_n": len(mine), "mlb_same_n": len(same),
            "both_have_leaks": bool(mine and same),
            "top_same": bool(mine and same and mine[0] == same[0]),
            "college_top_in_mlb_same": bool(mine and mine[0] in same),
            "shared": len(set(mine) & set(same)),
            "has_full_season_card": season is not None,
            "college_top_in_full_season": bool(mine and season and mine[0] in season),
            "mlb_same_top_in_full_season": bool(same and season and same[0] in season),
        })
    return pd.DataFrame(rows)


def round_trip(mlb, bits, team, games_n, keep=True):
    name = f"roundtrip_{team}"
    workspace = cb.COLLEGE_DIR / name
    log(f"\nRound trip: {team}'s first {games_n} games as TrackMan files, built as a college season...")
    sc = st.team_games(mlb["raw"], team, games_n)
    register = pd.read_parquet(PROJECT_DIR / "data" / "raw" / "chadwick_register.parquet")
    st.write_games(st.to_trackman(sc, register, sign=-1.0), workspace / "trackman")
    st.heights_roster(sc).to_csv(workspace / "heights.csv", index=False)
    cb.build(name, [workspace / "trackman"], workspace / "heights.csv")

    facts = json.loads((workspace / "build_facts.json").read_text())
    raw_c = pd.read_parquet(workspace / "data" / "raw" / f"statcast_{SEASON}-trackman.parquet")
    clean_c = pd.read_parquet(workspace / "data" / "cleaned" / "baseline_chase_pitches.parquet")
    xcost_c = pd.read_parquet(workspace / "data" / "cleaned" / "xchase_costs_by_pitch.parquet")
    q_c = pd.read_csv(workspace / "results" / "xchase" / f"chase_cost_leaderboard_{SEASON}.csv")
    cards_c = json.loads((workspace / "data" / "cleaned" / f"card_players_{SEASON}.json").read_text())
    rv_c = {"counts": pd.read_csv(workspace / "results" / "run_values" / "run_value_by_count.csv"),
            "events": pd.read_csv(workspace / "results" / "run_values" / "run_value_by_event.csv"),
            "plate_appearances": pd.read_parquet(workspace / "data" / "cleaned" / "plate_appearance_run_values.parquet")}
    km = key_map(raw_c)
    games = set(km["sc_game_pk"])

    fidelity = adapter_fidelity(mlb, raw_c, clean_c, km, facts, games)
    matched = to_statcast_keys(xcost_c, km).merge(mlb["costs"], on=KEYS, suffixes=("", "_mlb"))
    fidelity["priced_college"], fidelity["priced_mlb"] = len(xcost_c), int(
        mlb["costs"]["game_pk"].isin(games).sum())

    p = mlb["pitches"]
    team_all = p[(p["home_team"] == team) | (p["away_team"] == team)]
    q = q_c.rename(columns={c: c.replace("xchase_plus", "chase_plus") for c in q_c.columns})
    hitters = hitters_vs_mlb(q, None, mlb, p[p["game_pk"].isin(games)],
                             team_all[~team_all["game_pk"].isin(games)])
    hitters["mlb_full_rank"] = hitters["batter"].map(
        mlb["board"].set_index("batter")["runs_saved_shrunk"].rank(ascending=False))
    hitters["college_sd"] = hitters["batter"].map(q.set_index("batter")["chase_plus_posterior_sd"])
    decomp = decomposition(clean_c, km, rv_c, mlb, bits, games, q)
    leak_table = leaks(mlb, cards_c, games, q)
    for frame in (hitters, decomp, leak_table):
        frame.insert(0, "team", team)
    matched.insert(0, "team", team)
    fidelity = {"team": team, **fidelity, "qualified": len(q), "games": games_n,
                "xwoba_neighbors": facts["xwoba"]["neighbors"],
                "talent_sd_xchase_plus": facts["talent_sd_xchase_plus"],
                "league_chase_cost_per_600_pa": facts["league_chase_cost_per_600_pa"],
                "woba_weights": facts["woba_weights"]}
    if not keep:
        import shutil
        shutil.rmtree(workspace)
    return {"fidelity": fidelity, "matched": matched, "hitters": hitters, "decomposition": decomp,
            "leaks": leak_table}


# --------------------------------------------------
# THE WRITE-UP
# --------------------------------------------------

README_INTRO = """\
Written by `scripts/trackman_roundtrip.py`. The college path
(`scripts/college_build.py`) turns a college team's TrackMan files into
xChase+ and decision cards. There is no college data here to test it on,
so this test makes some: 2026 Statcast games written out as TrackMan game
CSVs, with only what a TrackMan file carries (no strike zone, no runners
on base, no xwOBA, no score; PlateLocSide mirrored). Each team's first
{games} games is about 17,500 pitches, a college season's worth. The
college build runs on those files exactly as it would on a college
team's, and its numbers are compared with the MLB build's for the same
pitches. {team} is shown in detail; the round trip ran on all {n} teams,
{hitters} qualified hitters in all.

These are MLB data, so this folder is committed. The college builds the
test makes live in `college/`, which is not."""

README_PARITY = """\
`scripts/college_method.py` is the college path's copy of steps 03 and 04,
with the settings a small league needs passed in. Given step 03's and step
04's own settings, on every 2026 pitch, it gives their numbers back. The
test stops if it ever does not, so every difference further down is a
choice the college path makes, not a slip in copying."""

README_STUDY = """\
Each team's first 60 games of 2026 ({low:,} to {high:,} pitches: the team
and its opponents) was priced as a league of its own: its own run values,
xwOBA, called-strike model and baseline, with the college floors (100 PA,
200 out-of-zone pitches). Each of the {hitters} qualified hitters (the
team's own; an opponent never reaches 100 PA in 60 games) is compared with
the MLB build's price of the same pitches, against the whole league. The
question for each setting: how far from the MLB build does a college-sized
league put a hitter's raw runs saved?"""

README_STUDY_BASELINE = """\
A college season is small, so the obvious move is coarser cells. They came
out worse, not better, so the college path keeps step 04's: 12 counts x 4 distance buckets, 48 cells of
about 190 pitches each at this size. Merging the buckets lets a pitch
nowhere near the zone share a baseline with one just off it, and the
four count groups put a 3-1 chase (expensive) with a 1-0 one (cheap);
both biases cost more than a 190-pitch cell's noise. Averaging the result's
run value over the counts (the college choice) or each plate appearance's
own (step 03's) makes no difference here."""

README_STUDY_SHRINK = """\
Shrinkage, priced with the chosen settings. Step 04 fits the spread
between hitters on its qualified hitters; a slice has about ten, so the
college path fits it on everyone in the files with 40 or more out-of-zone
pitches (a median of {pool} a slice, the opponents included) and shrinks
toward their average. Each choice is scored on how well the slice predicts the same
hitter's raw runs saved over the team's next 100 games (priced by the MLB
build), and on how close it comes to the MLB build's own shrunk number for
the same pitches. 40 does best on both, and predicts the next 100 games
nearly as well as the MLB build does with the whole league behind it (the
last row): a college-sized league loses little."""

README_TRIP = """\
Each team's 60 games written as TrackMan CSVs (`scripts/statcast_to_trackman.py`,
one file per game, PlateLocSide mirrored so the adapter must read the
sign off the files), a heights roster read back off the 2026 zones, and
`college_build.py` run on them: the adapter, step 02, the college pricing,
steps 13 and 15, and step 17's card page. Every number in this section
comes from what that build wrote."""

README_ADAPTER = """\
The adapter finds what TrackMan does not carry. The sign of PlateLocSide
comes from the hit-by-pitches, which are inside by definition. The
zones come from the roster's heights, and they match Savant's to a few
thousandths of an inch (the roster lists heights to a hundredth of an
inch). The runners on base are rebuilt play by play from the result, the
outs and the runs scored. They are exactly right at the start of {bases}
of plate appearances (the range over the {n} teams); a wrong base is mostly
a runner who took an extra base on a hit, moved up on an out or stole a
base, none of which a TrackMan row records. Run values built on the rebuilt
bases come out as close to the MLB build's as run values built on the true
ones. The college xwOBA (the average of the {k} nearest batted balls
in the files, the number chosen by cross-validation in each build) tracks
Savant's closely without using it. The wOBA weights the build fits
from the files' own run values come out near Savant's (medians across the
teams: {weights}; Savant's are 0.70, 0.70, 0.90, 1.25, 1.60 and 2.00)."""

README_PITCHES = """\
Every out-of-zone pitch the two builds both price, side by side. The
college build's league is the team and its opponents in 60 games, so its
called-strike model, run values and baseline are fit on 2% of the MLB
build's pitches; each pitch's price still follows the MLB build's closely."""

README_HITTERS = """\
Across all {teams} teams, the college build's xChase+ is {x_rmse:.1f} points from
the MLB build's on the same pitches (RMSE; correlation {x_corr:.2f}; {x_within_10:.0%} of
hitters within 10 points, the largest gap {x_max:.0f}). Of that, {x_shift:.1f} points
(RMSE) is a shift every hitter on a team shares (see where the
differences come from, below), and {x_spread:.1f} is left within a team. So the
college build orders each team's hitters nearly as the MLB build does:
rank correlation {x_within:.2f} within a team, on average. Before shrinkage the two
are {raw_rmse:.1f} runs per 600 PA apart (correlation {raw_corr:.2f}). The two also shrink
a little differently, the MLB build toward its qualified hitters and the
college build toward the average of everyone in its files with 40 or more
out-of-zone pitches, which moves the college number {prior_pts:+.1f} points on
average.

Two checks on what the gap means. Against each hitter's MLB card for the
full season (162 games, a bigger and different sample), the college
xChase+ correlates {full_corr_college:.2f}, and the MLB build's for the same 60 games
{full_corr_mlb_same:.2f}. Predicting the same hitters' raw runs saved over the team's
next 100 games, the college build is off by {rest_rmse_college:.1f} runs per 600 PA (RMSE)
and the MLB build on the same 60 games by {rest_rmse_mlb_same:.1f}. Most of the distance
to the full season is the 60-game sample, which a college season has too;
the college pricing adds little to it. {team_note}"""

README_LEAKS = """\
A card's leaks are its three costliest spots where the hitter chases more
than the league would on the same pitches, by step 17's own rule, and the
college card's come from step 17 itself, run on the college build. The MLB
build's for the same pitches are rebuilt here with step 17's per-pitch
expectation and labels from the 2026 page (that rebuild reproduces the MLB
cards' leaks for {check} of {check_n} hitters over the full season). The two
agree on whether a hitter has a leak at all for {leak_agree} of {leak_hitters}. Of the
{leak_both} both find one for, the college card names the same top leak as the
MLB build on the same pitches for {leak_top_same:.0%}, and its top leak is among the
MLB build's three for {leak_top_in:.0%}. How much a leak moves with the sample: for hitters with a
full-season MLB card, the college top leak is among the full season's three
for {season_college:.0%} and the MLB build's 60-game top leak for {season_mlb_same:.0%}.
Sixty games is a small sample for a leak, whoever prices it; the college
pricing adds little to that."""

README_DECOMP = """\
Each hitter's raw runs saved per 600 PA, priced again with ingredients
taken from the MLB build: run values, expected contact and the
called-strike chance, each on its own and then all three. Each time the
league baseline is recomputed from the 60 games' pitches at the new prices,
because a baseline is the league's average price and means nothing next to
costs priced another way. The last row adds the whole league's baseline on
top, and that is the MLB build itself; what is left ({total_5:.2f} runs) is the
0.1% of pitches whose zone call differs. Each gap is split into its team's
average gap, one number shared by every hitter on the team, and what is
left within the team.

The two parts have different causes. The part a team shares is the
league. Priced exactly as the MLB build prices them, a team's hitters
still sit {shift_4:.2f} runs above or below the MLB build together, until the
baseline is the whole league's ({shift_5:.2f}). Sixty games of one team are a
different league from all 30 teams: half its plate appearances are the
team's own hitters, and a 190-pitch cell has noise of its own. A shift
every hitter on a team shares does not change which of them chases most,
or where, so the order of a team's hitters and their leaks come through it
(above). The part within a team is the pricing: {within_0:.2f} runs as built,
{within_4:.2f} with all three ingredients from the MLB build. Expected contact
matters most (the college xwOBA is fit on about 3,000 batted balls; with
Savant's, the within-team gap is {within_2:.2f}), then the run values ({within_1:.2f});
the called-strike model makes no difference ({within_3:.2f}).

In college the part a team shares is the point, not a flaw. A Clemson
hitter is measured against the pitchers and hitters in Clemson's games,
not against a league he never sees."""

README_LIMITS = """\
- **How a TrackMan operator records a play.** The files here were written
  from Statcast, so every play is recorded the way the adapter expects. A
  real file can differ: foul tips may or may not be marked, a bunt may or
  may not be tagged, an out on the bases may be on the pitch or between
  pitches, and some rows may be blank. The adapter reads the outs from the
  Outs column rather than trusting OutsOnPlay, treats a pitch with no call
  or type as no decision, and reports what it filled in (BUILD.md); the
  first real files should be read with that report open.
- **PlateLocSide's sign.** Found from the files' hit-by-pitches in both
  directions here (the round trip writes it mirrored; written unmirrored,
  the adapter reads +1). A real season has plenty of hit batters; with
  fewer than ten, it stops and asks.
- **College batted balls and umpires.** The xwOBA, run values and
  called-strike model are refit on the files, so they follow metal bats and
  college umpires whatever those do. What the round trip shows is that the
  fits work on 17,500 pitches; it cannot show what they look like on college
  pitches.
- **Missing exit speeds.** Statcast tracks every ball in play; TrackMan
  misses some. A ball with no exit speed gets its hit type's average value.
  How many there are is in BUILD.md.
- **The schedule.** Here the opponents are a cross-section of MLB. A
  college team's are its schedule: a weak midweek opponent and a strong
  conference one are in the same league baseline, which is the league the
  team's hitters actually faced.
- **The card's footer.** "Does fixing a leak pay?" quotes the MLB backtest
  (step 16 needs back-to-back seasons), and a college card says the finding
  is from MLB hitters until there are two college seasons to test it on."""

README_FILES = """\
| File | What it is |
|---|---|
| `parity.csv` | Part 1: the college method against steps 03 and 04 |
| `settings_study_baselines.csv`, `settings_study_hitters.csv` | Part 2: each baseline and count-value choice, summed up and hitter by hitter |
| `settings_study_shrinkage.csv`, `settings_study_shrinkage_hitters.csv` | Part 2: each shrinkage pool |
| `adapter_fidelity.csv`, `woba_weights.csv` | Part 3: what the adapter rebuilt and the wOBA weights each build fit, by team |
| `pitches.csv` | Part 3: per-pitch prices, {team} and all teams |
| `hitters.csv` | Part 3: every qualified hitter, the college build next to the MLB build |
| `decomposition.csv` | Part 3: every hitter priced with each ingredient swapped |
| `leaks.csv` | Part 3: every hitter's leaks, the college card, the MLB build on the same pitches and the full season |
| `leak_rebuild_check.csv` | The check on the MLB leaks rebuilt for the comparison |

Rerun it all with `python scripts/trackman_roundtrip.py` (about 15
minutes; `--skip-study` keeps the last settings study, `--teams KC NYY`
limits the round trips). {team}'s college build stays in
`college/roundtrip_{team}/`, cards page included."""


def md_table(header, rows, align=None):
    align = align or ["---"] + ["---:"] * (len(header) - 1)
    out = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def pct(x, digits=1):
    return f"{100 * x:.{digits}f}%"


def summarize(h, d, l):
    """The pooled numbers the write-up quotes."""

    s = {}
    s["hitters"] = len(h)
    s["teams"] = h["team"].nunique()
    s["raw_rmse"] = rmse(h["runs_saved_per_600_pa"], h["mlb_same_runs"])
    s["raw_gap"] = float((h["runs_saved_per_600_pa"] - h["mlb_same_runs"]).mean())
    s["raw_corr"] = float(h["runs_saved_per_600_pa"].corr(h["mlb_same_runs"]))
    s["x_rmse"], s["x_shift"], s["x_spread"] = shift_and_spread(
        h["chase_plus"], h["xchase_plus_mlb_same"], h["team"])
    s["x_gap"] = float((h["chase_plus"] - h["xchase_plus_mlb_same"]).mean())
    s["x_corr"] = float(h["chase_plus"].corr(h["xchase_plus_mlb_same"]))
    per_team = h.groupby("team").apply(lambda g: rmse(g["chase_plus"], g["xchase_plus_mlb_same"]),
                                       include_groups=False)
    s["team_lo"], s["team_hi"] = float(per_team.min()), float(per_team.max())
    s["per_team"] = per_team
    s["x_within"] = float(h.groupby("team").apply(
        lambda g: g["chase_plus"].corr(g["xchase_plus_mlb_same"], method="spearman"),
        include_groups=False).mean())
    s["x_max"] = float((h["chase_plus"] - h["xchase_plus_mlb_same"]).abs().max())
    s["x_within_10"] = float(((h["chase_plus"] - h["xchase_plus_mlb_same"]).abs() <= 10).mean())
    full = h[h["mlb_full_xchase_plus"].notna()]
    s["full_hitters"] = len(full)
    s["full_corr_college"] = float(full["chase_plus"].corr(full["mlb_full_xchase_plus"]))
    s["full_corr_mlb_same"] = float(full["xchase_plus_mlb_same"].corr(full["mlb_full_xchase_plus"]))
    rest = h[h["mlb_rest_pa"] >= 100]
    s["rest_hitters"] = len(rest)
    s["rest_rmse_college"] = rmse(rest["runs_saved_shrunk"], rest["mlb_rest_runs"])
    s["rest_rmse_mlb_same"] = rmse(rest["mlb_same_shrunk"], rest["mlb_rest_runs"])
    s["prior_pts"] = float((h["chase_plus"] - h["chase_plus_raw"]).mean()
                           - (h["xchase_plus_mlb_same"] - h["xchase_plus_mlb_same_raw"]).mean())
    both = l[l["both_have_leaks"]]
    s["leak_hitters"] = len(l)
    s["leak_both"] = len(both)
    s["leak_top_same"] = float(both["top_same"].mean())
    s["leak_top_in"] = float(both["college_top_in_mlb_same"].mean())
    s["leak_shared"] = float(both["shared"].mean())
    s["leak_n_college"] = float(l["college_n"].mean())
    s["leak_n_mlb"] = float(l["mlb_same_n"].mean())
    s["leak_neither"] = int(((l["college_n"] == 0) & (l["mlb_same_n"] == 0)).sum())
    s["leak_college_only"] = int(((l["college_n"] > 0) & (l["mlb_same_n"] == 0)).sum())
    s["leak_mlb_only"] = int(((l["college_n"] == 0) & (l["mlb_same_n"] > 0)).sum())
    card = l[l["has_full_season_card"] & (l["college_n"] > 0) & (l["mlb_same_n"] > 0)]
    s["season_hitters"] = len(card)
    s["season_college"] = float(card["college_top_in_full_season"].mean())
    s["season_mlb_same"] = float(card["mlb_same_top_in_full_season"].mean())
    s["decomp"] = decomposition_table(d)
    return s


def team_note(team, h, d, s):
    """What the shown team's biggest gaps come from, from its own numbers."""

    k = d[d["team"] == team].merge(h[h["team"] == team], on=["team", "batter"])
    k["points"] = k["chase_plus"] - k["xchase_plus_mlb_same"]
    k["raw"] = k["college"] - k["mlb_same"]
    k["league"] = k["with all three"] - k["all MLB"]
    k["contact"] = k["college"] - k["with MLB expected contact"]
    where = (f"{team}, shown above, is {s['per_team'][team]:.1f} points from the MLB build (RMSE; the "
             f"{s['teams']} teams run from {s['team_lo']:.1f} to {s['team_hi']:.1f}).")
    big = k[k["points"].abs() >= 10].sort_values("points")
    if big.empty:
        return where + " Every one of its hitters lands within 10 points."
    names = [n.split()[-1] for n in big["player"]]
    names = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    sizes = big["points"].abs().round().astype(int)
    lo, hi = int(sizes.min()), int(sizes.max())
    way = "lower" if (big["points"] < 0).all() else ("higher" if (big["points"] > 0).all() else "away")
    league = float((big["league"] / big["raw"]).clip(0, 1).mean())
    contact = float((big["contact"] / big["raw"]).clip(0, 1).mean())
    span = f"{lo}-{hi}" if lo != hi else f"{lo}"
    return (f"{where} {names} come out {span} points {way} than on the MLB build: about "
            f"{league:.0%} of their raw gap is the shift {team}'s hitters share (the league), and about "
            f"{contact:.0%} their contact on chases, which the college xwOBA values differently from "
            "Savant's.")


def write_readme(team):
    """results/trackman_roundtrip/README.md from the CSVs beside it."""

    parity_t = pd.read_csv(OUT / "parity.csv")
    base = pd.read_csv(OUT / "settings_study_baselines.csv")
    pools = pd.read_csv(OUT / "settings_study_shrinkage.csv")
    fid = pd.read_csv(OUT / "adapter_fidelity.csv")
    weights = pd.read_csv(OUT / "woba_weights.csv")
    pitches = pd.read_csv(OUT / "pitches.csv")
    h = pd.read_csv(OUT / "hitters.csv")
    d = pd.read_csv(OUT / "decomposition.csv")
    l = pd.read_csv(OUT / "leaks.csv")
    check = pd.read_csv(OUT / "leak_rebuild_check.csv").iloc[0]
    s = summarize(h, d, l)
    me = fid[fid["team"] == team].iloc[0]
    n = len(fid)
    lines = []
    add = lines.append

    def span(col, f=lambda v: f"{v:.1%}"):
        return f"{f(fid[col].min())} to {f(fid[col].max())}"

    add("# The college path, tested on MLB data")
    add("")
    add(README_INTRO.format(team=team, n=n, games=int(me["games"]), hitters=s["hitters"]))
    add("")
    add("## 1. The college method reproduces steps 03 and 04")
    add("")
    add(README_PARITY)
    add("")
    add(md_table(["Check, all 2026 MLB pitches", "Largest difference"],
                 [[r.check, f"{r.max_abs_difference:.1e}" if abs(r.max_abs_difference) > 0 else "0"]
                  for r in parity_t.itertuples()], ["---", "---:"]))
    add("")
    add("## 2. Settings for a league of 17,500 pitches")
    add("")
    add(README_STUDY.format(n=n, hitters=int(base["hitters"].iloc[0]),
                            low=int(fid["pitches"].min()), high=int(fid["pitches"].max())))
    add("")
    piv = base.pivot(index="baseline", columns="count_values", values="rmse_runs_per_600")
    order = list(dict.fromkeys(base["baseline"]))
    corr = base[base["count_values"] == "event"].set_index("baseline")
    add(md_table(["League baseline cells", "Runs per 600 PA from the MLB build (RMSE)",
                  "Same, step 03's count values", "Correlation", "xChase+ points (RMSE)"],
                 [[("**" + b + "**") if b.endswith("(MLB)") else b, f"{piv.loc[b, 'event']:.2f}",
                   f"{piv.loc[b, 'plate_appearance']:.2f}", f"{corr.loc[b, 'correlation']:.3f}",
                   f"{corr.loc[b, 'rmse_xchase_plus_raw']:.1f}"] for b in order],
                 ["---", "---:", "---:", "---:", "---:"]))
    add("")
    add(README_STUDY_BASELINE)
    add("")
    add(md_table(["Spread between hitters fit on", "Hitters in the fit (median)",
                  "Talent SD, xChase+ points (median)", "Error predicting the next 100 games",
                  "Gap to the MLB build, same pitches"],
                 [[r.pool, "" if pd.isna(r.median_pool_size) else f"{r.median_pool_size:.0f}",
                   "" if pd.isna(r.median_talent_sd_xchase_plus) else f"{r.median_talent_sd_xchase_plus:.1f}",
                   f"{r.rmse_vs_rest_of_season:.2f}", f"{r.rmse_vs_mlb_same_pitches_shrunk:.2f}"]
                  for r in pools.itertuples()], ["---", "---:", "---:", "---:", "---:"]))
    add("")
    add(README_STUDY_SHRINK.format(pool=int(pools.loc[pools["pool"] == "40+ out-of-zone pitches",
                                                        "median_pool_size"].iloc[0])))
    add("")
    add("## 3. The round trip")
    add("")
    add(README_TRIP.format(team=team, n=n))
    add("")
    add("### What the adapter rebuilt")
    add("")
    rows = [
        ["PlateLocSide's sign, read off the hit-by-pitches", "mirrored, found" if me["sign_found"] < 0 else "found",
         f"{int((fid['sign_found'] < 0).sum())} of {n} found"],
        ["Pitches read as a decision the same way as step 02 on Statcast", pct(me["analyzable_same"], 2), span("analyzable_same", lambda v: pct(v, 2))],
        ["Inside or outside the zone the same way as Savant", pct(me["zone_same"], 2), span("zone_same", lambda v: pct(v, 2))],
        ["Zone top and bottom from the heights roster, largest gap", f"{me['zone_gap_in']:.3f} in", f"up to {fid['zone_gap_in'].max():.3f} in"],
        ["Plate appearance results in the same group", pct(me["results_same"], 2), span("results_same", lambda v: pct(v, 2))],
        ["Runners on base exactly right, start of each plate appearance", pct(me["bases_exact"]), span("bases_exact")],
        ["Runner on first / second / third right", f"{pct(me['first_right'])} / {pct(me['second_right'])} / {pct(me['third_right'])}",
         f"{pct(fid['first_right'].mean())} / {pct(fid['second_right'].mean())} / {pct(fid['third_right'].mean())} (average)"],
        ["Score before every pitch right", pct(me["score_right"], 2), span("score_right", lambda v: pct(v, 2))],
        ["College xwOBA against Savant's, same batted balls (correlation)", f"{me['xwoba_correlation']:.3f}", span("xwoba_correlation", lambda v: f"{v:.3f}")],
    ]
    add(md_table(["", team, f"All {n} teams"], rows, ["---", "---:", "---:"]))
    add("")
    w = weights.drop(columns="team")
    add(README_ADAPTER.format(
        bases=f"{fid['bases_exact'].min():.0%} to {fid['bases_exact'].max():.0%}", n=n,
        k=f"{int(fid['xwoba_neighbors'].min())} to {int(fid['xwoba_neighbors'].max())}",
        weights=", ".join(f"{c.replace('_', ' ')} {w[c].median():.2f}" for c in w.columns)))
    add("")
    add("### Pitch by pitch")
    add("")
    ptab = pitches[pitches["teams"] == team]
    pall = pitches[pitches["teams"] != team]
    add(md_table(["Per pitch", "Pitches", "College mean", "MLB build mean", "Correlation",
                  f"Correlation, all {n} teams"],
                 [[r["per pitch"], f"{int(r['pitches']):,}", f"{r['college_mean']:+.4f}", f"{r['mlb_mean']:+.4f}",
                   f"{r['correlation']:.3f}", f"{pall.iloc[i]['correlation']:.3f}"]
                  for i, (_, r) in enumerate(ptab.iterrows())],
                 ["---", "---:", "---:", "---:", "---:", "---:"]))
    add("")
    add(README_PITCHES)
    add("")
    add(f"### The hitters: {team}")
    add("")
    mine = h[h["team"] == team].sort_values("chase_plus", ascending=False)
    lk = l.set_index(["team", "batter"])
    rows = []
    for r in mine.itertuples():
        leak = lk.loc[(team, r.batter)]
        first = lambda text: text.split("; ")[0] if isinstance(text, str) and text else "none"
        full = "" if pd.isna(r.mlb_full_xchase_plus) else f"{r.mlb_full_xchase_plus:.0f}"
        rows.append([r.player, int(r.plate_appearances), f"**{r.chase_plus:.0f}** ± {r.college_sd:.0f}",
                     f"{r.xchase_plus_mlb_same:.0f}", full, first(leak["college_leaks"]),
                     first(leak["mlb_same_pitches_leaks"])])
    add(md_table(["Hitter", "PA", "xChase+, college build", "MLB build, same pitches",
                  "MLB build, full season", "Top leak, college card", "Top leak, MLB build, same pitches"],
                 rows, ["---", "---:", "---:", "---:", "---:", "---", "---"]))
    add("")
    add(README_HITTERS.format(**{k: v for k, v in s.items() if k not in ("decomp", "per_team")},
                              team=team, team_note=team_note(team, h, d, s)))
    add("")
    add("### Leaks")
    add("")
    add(md_table(["Leaks, college card against the MLB build on the same pitches", f"All {n} teams"],
                 [["Hitters with a leak on both", f"{s['leak_both']} of {s['leak_hitters']}"],
                  ["Hitters with no leak on either", f"{s['leak_neither']}"],
                  ["A leak on one only (college / MLB build)",
                   f"{s['leak_college_only']} / {s['leak_mlb_only']}"],
                  ["Same top leak, of those with a leak on both", pct(s["leak_top_same"], 0)],
                  ["College top leak among the MLB build's three, same", pct(s["leak_top_in"], 0)],
                  ["Leaks the two lists share, of up to three, same", f"{s['leak_shared']:.1f}"],
                  ["Leaks per card, college / MLB build", f"{s['leak_n_college']:.1f} / {s['leak_n_mlb']:.1f}"]],
                 ["---", "---:"]))
    add("")
    add(README_LEAKS.format(**{k: v for k, v in s.items() if k not in ("decomp", "per_team")},
                            leak_agree=s["leak_both"] + s["leak_neither"],
                            check=pct(check["share"], 0), check_n=int(check["hitters"])))
    add("")
    add("### Where the differences come from")
    add("")
    dec = s["decomp"]
    add(md_table(["Priced with", "Runs per 600 PA from the MLB build (RMSE)",
                  "Shared by the team", "Within the team"],
                 [[r["priced with"], f"{r['rmse_runs_per_600']:.2f}", f"{r['team_wide']:.2f}",
                   f"{r['within_team']:.2f}"] for _, r in dec.iterrows()],
                 ["---", "---:", "---:", "---:"]))
    add("")
    add(README_DECOMP.format(**{f"{k}_{i}": dec[c].iloc[i] for i in range(len(dec))
                                for k, c in (("total", "rmse_runs_per_600"), ("shift", "team_wide"),
                                             ("within", "within_team"))}))
    add("")
    add("## What the round trip cannot test")
    add("")
    add(README_LIMITS)
    add("")
    add("## Files")
    add("")
    add(README_FILES.format(team=team))
    (OUT / "README.md").write_text("\n".join(lines) + "\n")
    log(f"Wrote {(OUT / 'README.md').relative_to(PROJECT_DIR)}")


# --------------------------------------------------
# RUN AND WRITE
# --------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="The college path's round-trip test on 2026 Statcast.")
    parser.add_argument("--team", default="KC", help="the team shown in detail (Statcast code)")
    parser.add_argument("--games", type=int, default=STUDY_GAMES)
    parser.add_argument("--teams", nargs="*", default=["all"],
                        help="teams to run the round trip on (default all 30); the --team "
                             "one keeps its college/roundtrip_<team>/ build")
    parser.add_argument("--skip-study", action="store_true", help="keep the last settings study")
    parser.add_argument("--readme-only", action="store_true",
                        help="rewrite README.md from the CSVs already in results/trackman_roundtrip/")
    args = parser.parse_args()
    if args.readme_only:
        write_readme(args.team)
        return

    OUT.mkdir(parents=True, exist_ok=True)
    mlb = load_mlb()
    parity_table, bits = parity(mlb)
    parity_table.to_csv(OUT / "parity.csv", index=False)
    all_teams = sorted(mlb["pitches"]["home_team"].dropna().unique())
    if not args.skip_study:
        raw, shrink, summary, pools = study(mlb, all_teams)
        summary.to_csv(OUT / "settings_study_baselines.csv", index=False)
        pools.to_csv(OUT / "settings_study_shrinkage.csv", index=False)
        raw.to_csv(OUT / "settings_study_hitters.csv", index=False, float_format="%.4f")
        shrink.to_csv(OUT / "settings_study_shrinkage_hitters.csv", index=False, float_format="%.4f")

    share, n = leak_rebuild_check(mlb)
    pd.DataFrame([{"check": "step 17's leaks rebuilt from its stored expectation match its cards",
                   "share": share, "hitters": n}]).to_csv(OUT / "leak_rebuild_check.csv", index=False)
    teams = all_teams if args.teams == ["all"] else args.teams
    teams = [args.team] + [t for t in teams if t != args.team]
    trips = [round_trip(mlb, bits, t, args.games, keep=(t == args.team)) for t in teams]

    pd.DataFrame([{k: v for k, v in t["fidelity"].items() if k != "woba_weights"} for t in trips]).to_csv(
        OUT / "adapter_fidelity.csv", index=False)
    weights = pd.DataFrame([{"team": t["fidelity"]["team"], **t["fidelity"]["woba_weights"]} for t in trips])
    weights.to_csv(OUT / "woba_weights.csv", index=False, float_format="%.3f")
    matched = pd.concat([t["matched"] for t in trips], ignore_index=True)
    pitch_rows = [pitch_level(matched[matched["team"] == args.team]).assign(teams=args.team),
                  pitch_level(matched).assign(teams=f"all {len(trips)}")]
    pd.concat(pitch_rows, ignore_index=True).to_csv(OUT / "pitches.csv", index=False)
    pd.concat([t["hitters"] for t in trips], ignore_index=True).to_csv(
        OUT / "hitters.csv", index=False, float_format="%.4f")
    pd.concat([t["decomposition"] for t in trips], ignore_index=True).to_csv(
        OUT / "decomposition.csv", index=False, float_format="%.4f")
    pd.concat([t["leaks"] for t in trips], ignore_index=True).to_csv(OUT / "leaks.csv", index=False)
    write_readme(args.team)


if __name__ == "__main__":
    sys.exit(main())
