"""
Step 20: score a frozen prediction file (step 19) against the season
that followed it.

Step 19 writes down, for every card, the hitter's leak cells, how far
above the league he chased there, and what the season-to-season line
predicts for next season with no change. This step waits for that next
season and asks two questions on exactly those cells:

  1. CENTERING. Was the actual excess next season centered on the
     prediction? Mean of actual minus predicted, with its standard
     error, for every scored hitter and for the main group (hitters
     whose card leaks the backtest's rule would also have listed) and
     the rest. A calibration line, actual = a + b x predicted, should
     come out near a = 0, b = 1.

  2. PAYOFF. Against actual minus predicted ("the fix": negative = cut
     more than the line expected), with the first season's leak chasing
     and outcome level held fixed, how did xChase+ and xwOBA offense
     change? Reported per 10-point cut, next to the frozen payoffs the
     file was written against. When a file is retrospective
     (out_of_sample = no), the reference payoffs are refit on the
     backtest's season pairs that end by the frozen season, with their
     own line, so the season being scored is in neither the line nor
     the reference.

  Also the run accounting (offense runs per run of leak choices
  recovered) and the other outcomes step 16 reports.

WHO IS SCORED
  Every hitter in the file with at least one leak who qualified the
  next season and saw at least MIN_NEXT_PITCHES pitches in his frozen
  cells. The cells are the frozen ones, never the hitter's new leaks.

THE SCALE
  The backtest's (leak_rules.BACKTEST_LEAGUE_CELL): the league's chase
  rate in the same season, count, distance bucket, pitch group and side
  of the zone, measured within each season. The frozen numbers are on
  this scale, so next season's are too.

OUTPUTS, in results/xchase/coaching/
  leak_scores_<next>.csv          one row per scored hitter
  leak_scores_summary_<next>.csv  every number printed below

Options: --season (default 2026; the frozen season, scored on the next),
--period full | h1 | h2 (default full): score on one half of the next
season instead, split at each hitter's plate-appearance midpoint by game
date as step 16 does. --period h1 is the midseason check: the spring's
frozen cells scored on the first half, with the half-to-half backtest
as the reference (the closest yardstick; the pairs it was fit on are
halves of one season, not a season and the next half). Outputs get the
period as a suffix (leak_scores_<next>_h1.csv).

Run after step 19 for that season, once the next season is in the data
(steps 02-04 with --expected-contact, so the leaderboard and priced
pitches exist for it).
"""

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leak_rules as lr  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
CLEAN = PROJECT_DIR / "data" / "cleaned"
XCHASE = PROJECT_DIR / "results" / "xchase"
OUT = XCHASE / "coaching"

PA_SCALE = 600
FAR_OFF_FT = 0.35
MIN_NEXT_PITCHES = 10           # in the frozen cells, as step 16 requires
KEYS = ["game_pk", "at_bat_number", "pitch_number", "batter", "game_year"]
OUTCOMES = ["xchase_plus", "offense_runs", "woba_runs", "bb_rate", "k_rate",
            "zone_swing_rate", "far_off_chase_rate"]
UNITS = {"xchase_plus": ("xChase+", 1, "pts"), "offense_runs": ("offense (xwOBA)", 1, "runs / 600 PA"),
         "woba_runs": ("offense (wOBA)", 1, "runs / 600 PA"), "bb_rate": ("BB%", 100, "pts"),
         "k_rate": ("K%", 100, "pts"), "zone_swing_rate": ("zone swing rate", 100, "pts"),
         "far_off_chase_rate": ("far-off chase rate", 100, "pts")}

parser = argparse.ArgumentParser(description="Score a frozen prediction file on the next season.")
parser.add_argument("--season", type=int, default=2026, help="the frozen season")
parser.add_argument("--period", choices=["full", "h1", "h2"], default="full",
                    help="score on the whole next season (default) or one half of it")
args = parser.parse_args()
SEASON = args.season
NEXT = SEASON + 1
PERIOD = args.period
SUFFIX = f"_{NEXT}" + ("" if PERIOD == "full" else f"_{PERIOD}")

# --------------------------------------------------
# LOAD
# --------------------------------------------------

pred_file = OUT / f"leak_predictions_{SEASON}.csv"
if not pred_file.exists():
    raise SystemExit(f"No frozen file for {SEASON}: run step 19 --season {SEASON} first.")
frozen = pd.read_csv(pred_file)
out_of_sample = str(frozen["out_of_sample"].iloc[0]) if "out_of_sample" in frozen else "yes"
hitters = frozen[(frozen["row"] == "hitter") & (frozen["leaks"] > 0)].set_index("batter")
cells_frozen = frozen[frozen["row"] != "hitter"][["batter"] + lr.LEAK_CELL]
intercept = float(hitters["line_intercept"].iloc[0])
slope = float(hitters["line_slope"].iloc[0])

seasons = pd.read_parquet(CLEAN / "baseline_chase_pitches.parquet", columns=["game_year"])
if not (seasons["game_year"] == NEXT).any():
    raise SystemExit(f"No {NEXT} pitches in the data yet; nothing to score {SEASON}'s "
                     f"predictions on.")
board_file = XCHASE / f"xchase_leaderboard_{NEXT}.csv"
if not board_file.exists():
    raise SystemExit(f"No {NEXT} leaderboard ({board_file.name}); run step 04 "
                     f"--expected-contact and step 09 first.")
board_next = pd.read_csv(board_file)
qualified_next = set(board_next["batter"])

print(f"Loading {SEASON} and {NEXT} pitches...")
base = pd.read_parquet(CLEAN / "baseline_chase_pitches.parquet", columns=KEYS + [
    "game_date", "pitch_type", "description", "events", "balls", "strikes", "woba_value", "woba_denom",
    "estimated_woba_using_speedangle", "is_analyzable", "is_in_zone", "is_outside_zone",
    "is_swing", "distance_outside_zone", "plate_x_batter", "plate_z_normalized", "sz_top",
    "sz_bot"], filters=[("game_year", "in", [SEASON, NEXT])])
costs = pd.read_parquet(CLEAN / "xchase_costs_by_pitch.parquet",
                        filters=[("game_year", "in", [SEASON, NEXT])])
scale = (pd.read_csv(XCHASE / "chase_plus_league_scale.csv")
         .set_index("game_year")["league_chase_cost_per_600_pa"])
run_values = pd.read_csv(PROJECT_DIR / "results" / "run_values" / "run_value_by_event.csv")
woba_scale = lr.woba_scale(run_values)

# Priced out-of-zone pitches with the backtest's labels and expectation,
# season by season
df = costs.merge(base.drop(columns=["balls", "strikes", "distance_outside_zone"]), on=KEYS,
                 how="left", validate="one_to_one")
df = df[df["plate_x_batter"].notna() & df["plate_z_normalized"].notna()]
parts = []
for season, g in df.groupby("game_year"):
    g = lr.add_labels(g.copy(), float((g["sz_top"] - g["sz_bot"]).mean()))
    parts.append(lr.add_choices_contact(g))
df = pd.concat(parts, ignore_index=True)
df["e"] = df.groupby(lr.BACKTEST_LEAGUE_CELL)["is_chase"].transform("mean")

# --------------------------------------------------
# HITTER-SEASON OUTCOMES, AS STEP 16 BUILDS THEM
# --------------------------------------------------

pas = lr.plate_appearances(base)
in_woba = pas[pas["in_woba"]]
league_x = in_woba.groupby("game_year")["x"].mean()
league_w = in_woba.groupby("game_year")["w"].mean()
tracked = base[base["is_analyzable"] == 1]
zone = tracked[tracked["is_in_zone"] == 1]
far = tracked[(tracked["is_outside_zone"] == 1) & (tracked["distance_outside_zone"] > FAR_OFF_FT)]
plate_apps = tracked.drop_duplicates(["game_pk", "at_bat_number", "batter"])

# Halves of the next season, as step 16 cuts them: each hitter's games in
# date order, split at his plate-appearance midpoint, whole games only.
games = (base[(base["is_analyzable"] == 1) & (base["game_year"] == NEXT)]
         .drop_duplicates(["game_pk", "at_bat_number", "batter"])
         .groupby(["batter", "game_pk", "game_date"]).size().rename("pa").reset_index()
         .sort_values(["batter", "game_date", "game_pk"]))
games["before"] = games.groupby("batter")["pa"].cumsum() - games["pa"]
games["total"] = games.groupby("batter")["pa"].transform("sum")
games["half"] = np.where(games["before"] + games["pa"] / 2 <= games["total"] / 2, "h1", "h2")
half_of = games.set_index(["batter", "game_pk"])["half"]


def in_period(frame, season):
    """The rows of `frame` in `season`, cut to PERIOD when it is the next season."""

    frame = frame[frame["game_year"] == season]
    if season != NEXT or PERIOD == "full":
        return frame
    idx = pd.MultiIndex.from_arrays([frame["batter"], frame["game_pk"]])
    return frame[half_of.reindex(idx).to_numpy() == PERIOD]


def outcomes(season):
    d = in_period(df, season)
    p = in_period(pas, season)
    pw = p[p["in_woba"]]
    st = pd.DataFrame({"pa": in_period(plate_apps, season).groupby("batter").size()})
    st["runs_saved"] = d.groupby("batter")["runs_saved"].sum()
    st["xwoba"] = pw.groupby("batter")["x"].mean()
    st["woba"] = pw.groupby("batter")["w"].mean()
    st["k_rate"] = p.groupby("batter")["strikeout"].mean()
    st["bb_rate"] = p.groupby("batter")["walk"].mean()
    st["zone_swing_rate"] = in_period(zone, season).groupby("batter")["is_swing"].mean()
    st["far_off_chase_rate"] = in_period(far, season).groupby("batter")["is_swing"].mean()
    st["xchase_plus"] = 100 + 100 * (st["runs_saved"] * PA_SCALE / st["pa"]) / scale[season]
    st["offense_runs"] = (st["xwoba"] - league_x[season]) / woba_scale[season] * PA_SCALE
    st["woba_runs"] = (st["woba"] - league_w[season]) / woba_scale[season] * PA_SCALE
    return st


first, second = outcomes(SEASON), outcomes(NEXT)

# --------------------------------------------------
# THE FROZEN CELLS, NEXT SEASON
# --------------------------------------------------

print("Measuring the frozen cells...")
cells = {}
for season in (SEASON, NEXT):
    d = in_period(df, season)
    cells[season] = d.groupby(["batter"] + lr.LEAK_CELL).agg(
        n=("is_chase", "size"), chases=("is_chase", "sum"), expected=("e", "sum"),
        choices=("choices", "sum"))

at = ["batter"] + lr.LEAK_CELL
lk = (cells_frozen.join(cells[SEASON].add_suffix("_1"), on=at)
      .join(cells[NEXT].add_suffix("_2"), on=at))
for c in ("n_2", "chases_2", "expected_2", "choices_2"):
    lk[c] = lk[c].fillna(0.0)
g = lk.groupby("batter").agg(
    leaks=("n_1", "size"), pitches_1=("n_1", "sum"), chases_1=("chases_1", "sum"),
    expected_1=("expected_1", "sum"), choices_1=("choices_1", "sum"),
    pitches_2=("n_2", "sum"), chases_2=("chases_2", "sum"),
    expected_2=("expected_2", "sum"), choices_2=("choices_2", "sum"))
g = g.loc[g.index.isin(hitters.index)]

# The frozen numbers must be reproducible on today's data
check = g.join(hitters[[f"pitches_{SEASON}", f"chases_{SEASON}", f"excess_{SEASON}"]])
off = check[(check["pitches_1"] != check[f"pitches_{SEASON}"])
            | (check["chases_1"] != check[f"chases_{SEASON}"])]
if len(off):
    raise SystemExit(f"{len(off)} hitters' frozen cells count different {SEASON} pitches or chases "
                     f"today than when frozen. The data has changed; the file can't be scored.")
excess_1 = (g["chases_1"] - g["expected_1"]) / g["pitches_1"]
drift = (excess_1 - check[f"excess_{SEASON}"]).abs().max()
if drift > 0.002:
    raise SystemExit(f"The {SEASON} league expectation has drifted (max {drift:.4f} in excess); "
                     f"the frozen scale no longer matches today's.")

g["excess_1"] = hitters.loc[g.index, f"excess_{SEASON}"]
g["predicted_2"] = hitters.loc[g.index, f"predicted_excess_{NEXT}"]
g["excess_2"] = (g["chases_2"] - g["expected_2"]) / g["pitches_2"].where(g["pitches_2"] > 0)
g["fix"] = g["excess_2"] - g["predicted_2"]
g["leak_chase_rate_1"] = g["chases_1"] / g["pitches_1"]
g["leak_chase_rate_2"] = g["chases_2"] / g["pitches_2"].where(g["pitches_2"] > 0)
g["leak_choices_per_600_1"] = g["choices_1"] * PA_SCALE / first.loc[g.index, "pa"]
g["leak_choices_per_600_2"] = g["choices_2"] * PA_SCALE / second["pa"].reindex(g.index)
g["change_leak_choices"] = g["leak_choices_per_600_2"] - g["leak_choices_per_600_1"]
g["also_a_backtest_leak"] = hitters.loc[g.index, "also_a_backtest_leak"]
g["count_status"] = hitters.loc[g.index, f"count_status_{SEASON}"]
g["player"] = hitters.loc[g.index, "player"]
for m in OUTCOMES + ["pa"]:
    g[m + "_1"] = first[m].reindex(g.index)
    g[m + "_2"] = second[m].reindex(g.index)
    g["change_" + m] = g[m + "_2"] - g[m + "_1"]

frozen_n = len(g)
g["qualified_next"] = g.index.isin(qualified_next)
scored = g[g["qualified_next"] & (g["pitches_2"] >= MIN_NEXT_PITCHES)].copy()
scored = scored.dropna(subset=["excess_2", "fix"])
print(f"  {frozen_n} hitters with frozen leaks; {int(g['qualified_next'].sum())} qualified in "
      f"{NEXT}; {len(scored)} with {MIN_NEXT_PITCHES}+ pitches in their frozen cells"
      + ("" if PERIOD == "full" else f" in {PERIOD}"))

# --------------------------------------------------
# REFERENCE PAYOFFS
# --------------------------------------------------

summary = []


def record(test, measure, value, se, n, group="all"):
    summary.append({"season": SEASON, "scored_on": NEXT, "group": group, "measure": measure,
                    "test": test, "value": value, "se": se, "n_hitters": n})


REF_KIND = "season" if PERIOD == "full" else "half"
if out_of_sample == "yes":
    ref = pd.read_csv(OUT / "leak_backtest_summary.csv")
    ref = ref[(ref["pair_kind"] == REF_KIND) & (ref["test"] == "per 10-pt cut beyond expected")]
    reference = {r.measure: (r.value, r.se) for r in ref.itertuples()}
    acc = pd.read_csv(OUT / "leak_backtest_summary.csv")
    acc = acc[(acc["pair_kind"] == REF_KIND) & (acc["measure"] == "offense_runs")
              & (acc["test"] == "per run of leak choices recovered")].iloc[0]
    reference["accounting"] = (acc["value"], acc["se"])
    ref_from = (f"leak_backtest_summary.csv ({REF_KIND} pairs, frozen before the season)")
else:
    # Retrospective file: the reference is the backtest on pairs that end
    # by the frozen season, with its own line, so the scored season is
    # in neither.
    pairs = pd.read_csv(OUT / "leak_backtest_pairs.csv")
    pairs = pairs[(pairs["kind"] == REF_KIND) & (pairs["season_2"] <= SEASON)]
    pairs = pairs.dropna(subset=["leak_excess_1", "leak_excess_2"]).copy()
    s_, i_ = np.polyfit(pairs["leak_excess_1"], pairs["leak_excess_2"], 1)
    if REF_KIND == "season" and (abs(s_ - slope) > 1e-3 or abs(i_ - intercept) > 1e-3):
        raise SystemExit("The frozen file's line does not match a refit on the pairs ending by "
                         f"{SEASON} (file {intercept:+.4f} + {slope:.4f} x, refit {i_:+.4f} + "
                         f"{s_:.4f} x). Rebuild step 16 and refreeze with --retrospective.")
    pairs["fix"] = pairs["leak_excess_2"] - (i_ + s_ * pairs["leak_excess_1"])
    reference = {}
    for m in OUTCOMES:
        Q = pairs.dropna(subset=["change_" + m, m + "_1"])
        beta, se = lr.ols(Q["change_" + m], [Q["fix"], Q["leak_excess_1"], Q[m + "_1"]],
                          Q["batter"].to_numpy())
        reference[m] = (-0.1 * beta[1], 0.1 * se[1])
    pairs["change_leak_choices"] = pairs["leak_choices_per_600_2"] - pairs["leak_choices_per_600_1"]
    beta, se = lr.ols(pairs["change_offense_runs"],
                      [pairs["change_leak_choices"], pairs["leak_choices_per_600_1"],
                       pairs["offense_runs_1"]], pairs["batter"].to_numpy())
    reference["accounting"] = (beta[1], se[1])
    ref_from = f"the backtest refit on {len(pairs)} {REF_KIND} pairs ending by {SEASON}"
for m, (v, se) in reference.items():
    record("reference payoff per 10-pt cut" if m != "accounting"
           else "reference offense runs per run of leak choices recovered", m, v, se, np.nan)

# --------------------------------------------------
# TESTS
# --------------------------------------------------


def centering(S, group):
    n = len(S)
    diff = S["excess_2"] - S["predicted_2"]
    record("mean excess, frozen season", "leak_excess", S["excess_1"].mean(), np.nan, n, group)
    record("mean predicted excess", "leak_excess", S["predicted_2"].mean(), np.nan, n, group)
    record("mean actual excess", "leak_excess", S["excess_2"].mean(),
           S["excess_2"].std(ddof=1) / np.sqrt(n), n, group)
    record("actual minus predicted", "leak_excess", diff.mean(), diff.std(ddof=1) / np.sqrt(n),
           n, group)
    if n >= 5:
        beta, se = lr.ols(S["excess_2"], [S["predicted_2"]], S.index.to_numpy())
        record("calibration intercept (actual on predicted)", "leak_excess", beta[0], se[0], n, group)
        record("calibration slope (actual on predicted)", "leak_excess", beta[1], se[1], n, group)


centering(scored, "all")
for answer, label in (("yes", "main: every leak also a backtest leak"), ("no", "some leak not")):
    S = scored[scored["also_a_backtest_leak"] == answer]
    if len(S):
        centering(S, label)

payoff = {}
for m in OUTCOMES:
    Q = scored.dropna(subset=["change_" + m, m + "_1"])
    beta, se = lr.ols(Q["change_" + m], [Q["fix"], Q["excess_1"], Q[m + "_1"]], Q.index.to_numpy())
    payoff[m] = (-0.1 * beta[1], 0.1 * se[1], len(Q))
    record("payoff per 10-pt cut beyond predicted", m, -0.1 * beta[1], 0.1 * se[1], len(Q))
beta, se = lr.ols(scored["change_offense_runs"],
                  [scored["change_leak_choices"], scored["leak_choices_per_600_1"],
                   scored["offense_runs_1"]], scored.index.to_numpy())
accounting = (beta[1], se[1])
record("offense runs per run of leak choices recovered", "offense_runs", beta[1], se[1], len(scored))

for status, S in scored.groupby("count_status"):
    for m in ("offense_runs", "xchase_plus"):
        if len(S) < 10:
            continue
        beta, se = lr.ols(S["change_" + m], [S["fix"], S["excess_1"], S[m + "_1"]], S.index.to_numpy())
        record(f"payoff per 10-pt cut beyond predicted, {status} in the counts", m,
               -0.1 * beta[1], 0.1 * se[1], len(S))

# --------------------------------------------------
# WRITE
# --------------------------------------------------

OUT.mkdir(parents=True, exist_ok=True)
keep = (["player", "leaks", "also_a_backtest_leak", "count_status", "pitches_1", "pitches_2",
         "leak_chase_rate_1", "leak_chase_rate_2", "excess_1", "predicted_2", "excess_2", "fix",
         "leak_choices_per_600_1", "leak_choices_per_600_2"]
        + [f"{m}_{i}" for m in OUTCOMES + ["pa"] for i in (1, 2)]
        + [f"change_{m}" for m in OUTCOMES])
out = scored[keep].rename(columns={"pitches_1": f"pitches_{SEASON}", "pitches_2": f"pitches_{NEXT}",
                                   "excess_1": f"excess_{SEASON}", "predicted_2": f"predicted_excess_{NEXT}",
                                   "excess_2": f"actual_excess_{NEXT}"})
out.insert(0, "scored_on", NEXT)
out.insert(0, "season", SEASON)
out.insert(2, "out_of_sample", out_of_sample)
out.insert(2, "period", PERIOD)
out.reset_index().sort_values("fix").to_csv(OUT / f"leak_scores{SUFFIX}.csv", index=False,
                                             float_format="%.4f")
summary = pd.DataFrame(summary)
summary.insert(2, "out_of_sample", out_of_sample)
summary.insert(2, "period", PERIOD)
summary.to_csv(OUT / f"leak_scores_summary{SUFFIX}.csv", index=False, float_format="%.5f")

# --------------------------------------------------
# REPORT
# --------------------------------------------------

S = summary.set_index(["group", "measure", "test"])
print(f"\nScoring {pred_file.name} on {NEXT}" + ("" if PERIOD == "full" else f" ({PERIOD}, the "
      + ("first" if PERIOD == "h1" else "second") + " half at each hitter's PA midpoint)")
      + (" (RETROSPECTIVE: the file was not frozen before the season)" if out_of_sample == "no"
         else " (frozen before the season)"))
print(f"Line in the file: next = {intercept * 100:+.1f} + {slope:.2f} x {SEASON}")
for group in ["all", "main: every leak also a backtest leak", "some leak not"]:
    if (group, "leak_excess", "actual minus predicted") not in S.index:
        continue
    n = int(S.loc[(group, "leak_excess", "actual minus predicted"), "n_hitters"])
    r = S.loc[(group, "leak_excess", "actual minus predicted")]
    print(f"\n{group} ({n} hitters): leak chasing, points above the league")
    print(f"  {SEASON}: {S.loc[(group, 'leak_excess', 'mean excess, frozen season'), 'value'] * 100:5.1f}   "
          f"predicted {NEXT}: {S.loc[(group, 'leak_excess', 'mean predicted excess'), 'value'] * 100:5.1f}   "
          f"actual {NEXT}: {S.loc[(group, 'leak_excess', 'mean actual excess'), 'value'] * 100:5.1f}")
    print(f"  actual minus predicted: {r['value'] * 100:+.1f} ± {r['se'] * 100:.1f} pts")
    if (group, "leak_excess", "calibration slope (actual on predicted)") in S.index:
        a = S.loc[(group, "leak_excess", "calibration intercept (actual on predicted)")]
        b = S.loc[(group, "leak_excess", "calibration slope (actual on predicted)")]
        print(f"  actual = {a['value'] * 100:+.1f} (± {a['se'] * 100:.1f}) + "
              f"{b['value']:.2f} (± {b['se']:.2f}) x predicted")

print(f"\nPayoff per 10-point cut beyond predicted ({len(scored)} hitters), next to the "
      f"reference from {ref_from}:")
print(f"  {'':20s} {'scored':>16s}   {'reference':>16s}")
for m in OUTCOMES:
    lab, k, unit = UNITS[m]
    v, se, n = payoff[m]
    rv, rse = reference[m]
    print(f"  {lab:20s} {v * k:+6.2f} ± {se * k:4.2f}   {rv * k:+6.2f} ± {rse * k:4.2f}  {unit}")
rv, rse = reference["accounting"]
print(f"  offense runs per run of leak choices recovered: {accounting[0]:+.2f} ± {accounting[1]:.2f}"
      f"   (reference {rv:+.2f} ± {rse:.2f})")
for status in ("struggling", "average", "productive"):
    key = ("all", "offense_runs", f"payoff per 10-pt cut beyond predicted, {status} in the counts")
    if key in S.index:
        r = S.loc[key]
        print(f"    {status:10s} in the counts ({int(r['n_hitters']):3d} hitters): "
              f"{r['value']:+.2f} ± {r['se']:.2f} runs per 10-pt cut")
print(f"\nWrote leak_scores{SUFFIX}.csv and leak_scores_summary{SUFFIX}.csv to "
      f"{OUT.relative_to(PROJECT_DIR)}/")
