"""
Step 16: when a hitter fixes the leaks on his card, does it pay?

Step 14 asked whether cutting far-off chases in general goes with better
results. This asks the narrower question the cards raise: a hitter's
card names his worst leaks. When he stops chasing in exactly those
spots, what happens to his xChase+ and his offense, and does it matter
whether he was struggling in those counts (step 15)?

PAIRS
  season    one qualified season to the next (2021-22 ... 2025-26)
  half      first half to second half of one qualified season, split at
            the hitter's own plate-appearance midpoint by game date, so
            both halves are the same size

LEAKS
  The first period's leaks by the card rule (leak_rules.leak_cells, top
  3, all pitchers). Each pitch's league expectation is the league's
  chase rate in the same season, count, distance bucket, pitch group and
  side of the zone missed. The cards use a smoother, matchup-adjusted
  version of the same thing; the two pick the same top leak for most
  hitters (printed below for the latest season).

  Leak chasing = chases minus that expectation, per pitch, over the leak
  cells: how many points above the league the hitter chases there. It is
  measured in the first period and in the same cells in the second.

REGRESSION TO THE MEAN
  Leaks are the worst-looking cells of the first period, so part of
  every leak is bad luck and shrinks next period whatever the hitter
  does. The "fix" is the second period's leak chasing minus what the
  first period's predicts (a straight line fit across all pairs of that
  kind). Negative = cut more than expected. Every outcome regression
  also holds the first period's level fixed.

OUTCOMES (second period minus first)
  xChase+ (unshrunk), offense runs per 600 PA from xwOBA, the same from
  wOBA, BB%, K%, zone swing rate and far-off chase rate.

  Offense runs = (xwOBA - league xwOBA) / wOBA scale x 600. This is
  batting runs above average built on xwOBA rather than results, in the
  same units as xChase+'s runs. Each season's wOBA scale is fit from
  Savant's wOBA weights against this project's own run values (it comes
  out 1.20-1.23). wRC+ would add park factors this data doesn't carry
  and the luck xwOBA leaves out; OPS weights on-base and slugging wrong.

TESTS (standard errors clustered by hitter: the same hitter appears in
several pairs)
  1. Payoff: each change regressed on the fix, the first period's leak
     chasing and the first period's level of the outcome. Reported per
     10-point cut beyond expected.
  2. Run accounting: the change in offense runs against the change in
     the leaks' choices (step 13's decision runs), both per 600 PA. A
     slope of 1 means each run the card puts on a leak shows up as a run
     of offense when the leak is fixed.
  3. The count check: does the payoff depend on how the hitter did in
     the leak's counts in the first period (step 15's shrunk estimate)?
     An interaction term, and the payoff for struggling / average /
     productive hitters separately.

OUTPUTS, in results/xchase/coaching/
  leak_backtest_pairs.csv     one row per hitter pair of periods
  leak_backtest_summary.csv   every number quoted in the README and on
                              the cards

Run after step 04 (--expected-contact) and step 15.
"""

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
MIN_SECOND_PERIOD_PITCHES = 10     # in the first period's leak cells
GROUP_CUTOFF = 0.08                # fix of 8+ points either way, for the group table
WOBA_WEIGHTS = {"walk": 0.7, "hit_by_pitch": 0.7, "single": 0.9, "double": 1.25,
                "triple": 1.6, "home_run": 2.0}   # Savant's, every season 2021-2026
OUT_EVENTS = ["field_out", "strikeout", "force_out", "grounded_into_double_play",
              "double_play", "fielders_choice_out", "strikeout_double_play"]
KEYS = ["game_pk", "at_bat_number", "pitch_number", "batter", "game_year"]

# --------------------------------------------------
# LOAD
# --------------------------------------------------

print("Loading pitches...")
base = pd.read_parquet(CLEAN / "baseline_chase_pitches.parquet", columns=KEYS + [
    "game_date", "pitch_type", "description", "events", "balls", "strikes", "woba_value",
    "woba_denom", "estimated_woba_using_speedangle", "is_analyzable", "is_in_zone",
    "is_outside_zone", "is_swing", "distance_outside_zone", "plate_x_batter",
    "plate_z_normalized", "sz_top", "sz_bot"])
costs = pd.read_parquet(CLEAN / "xchase_costs_by_pitch.parquet")
boards = pd.concat([pd.read_csv(p)[["batter", "game_year", "player"]]
                    for p in sorted(XCHASE.glob("xchase_leaderboard_20??.csv"))], ignore_index=True)
scale = (pd.read_csv(XCHASE / "chase_plus_league_scale.csv")
         .set_index("game_year")["league_chase_cost_per_600_pa"])
run_values = pd.read_csv(PROJECT_DIR / "results" / "run_values" / "run_value_by_event.csv")

# Halves: each qualified hitter-season split at his plate-appearance
# midpoint, whole games only, in date order.
plate_apps = (base[base["is_analyzable"] == 1][["batter", "game_year", "game_pk", "game_date",
                                                "at_bat_number"]]
              .drop_duplicates(["game_pk", "at_bat_number", "batter"]))
games = (plate_apps.groupby(["batter", "game_year", "game_pk", "game_date"]).size()
         .rename("pa").reset_index().sort_values(["batter", "game_year", "game_date", "game_pk"]))
games["before"] = games.groupby(["batter", "game_year"])["pa"].cumsum() - games["pa"]
games["total"] = games.groupby(["batter", "game_year"])["pa"].transform("sum")
games["half"] = np.where(games["before"] + games["pa"] / 2 <= games["total"] / 2, "h1", "h2")
half_of = games.set_index(["batter", "game_pk"])["half"]


def tag_half(frame):
    idx = pd.MultiIndex.from_arrays([frame["batter"], frame["game_pk"]])
    frame["half"] = half_of.reindex(idx).to_numpy()
    return frame


# Priced out-of-zone pitches with the card's labels
df = costs.merge(base.drop(columns=["balls", "strikes", "distance_outside_zone"]), on=KEYS,
                 how="left", validate="one_to_one")
df = df[df["plate_x_batter"].notna() & df["plate_z_normalized"].notna()]
parts = []
for season, g in df.groupby("game_year"):
    g = lr.add_labels(g.copy(), float((g["sz_top"] - g["sz_bot"]).mean()))
    parts.append(lr.add_choices_contact(g))
df = tag_half(pd.concat(parts, ignore_index=True))
expect_cell = ["game_year", "count_state", "distance_bucket", "pitch_group", "region"]
df["e"] = df.groupby(expect_cell)["is_chase"].transform("mean")

pas = tag_half(lr.plate_appearances(base))
tracked = base[base["is_analyzable"] == 1]
zone = tag_half(tracked[tracked["is_in_zone"] == 1][["batter", "game_year", "game_pk", "is_swing"]].copy())
far = tag_half(tracked[(tracked["is_outside_zone"] == 1)
                       & (tracked["distance_outside_zone"] > FAR_OFF_FT)]
               [["batter", "game_year", "game_pk", "is_swing"]].copy())
plate_apps = tag_half(plate_apps)
base = tag_half(base)

# wOBA scale: Savant's weights against this project's run values above an out
woba_scale = {}
for season, r in run_values.groupby("game_year"):
    r = r.set_index("event")
    outs = r.loc[[e for e in OUT_EVENTS if e in r.index]]
    out_value = (outs["run_value"] * outs["occurrences"]).sum() / outs["occurrences"].sum()
    above = np.array([r.loc[e, "run_value"] - out_value for e in WOBA_WEIGHTS])
    freq = np.array([r.loc[e, "occurrences"] for e in WOBA_WEIGHTS])
    weight = np.array(list(WOBA_WEIGHTS.values()))
    woba_scale[season] = (freq * weight * above).sum() / (freq * above * above).sum()
woba_scale = pd.Series(woba_scale)
in_woba = pas[pas["in_woba"]]
league_x = in_woba.groupby("game_year")["x"].mean()
league_w = in_woba.groupby("game_year")["w"].mean()

# --------------------------------------------------
# EVERY HITTER-PERIOD: OUTCOMES, LEAKS, COUNT CHECK
# --------------------------------------------------

print("Building hitter-periods...")


def pick(frame, season, period):
    frame = frame[frame["game_year"] == season]
    return frame if period == "full" else frame[frame["half"] == period]


stats, leaks, checks, cells = [], [], [], {}
for season in sorted(boards["game_year"].unique()):
    hitters = set(boards.loc[boards["game_year"] == season, "batter"])
    for period in ("full", "h1", "h2"):
        d = pick(df, season, period)
        p = pick(pas, season, period)
        pw = p[p["in_woba"]]
        st = pd.DataFrame({"pa": pick(plate_apps, season, period).groupby("batter").size()})
        st = st[st.index.isin(hitters)]
        st["runs_saved"] = d.groupby("batter")["runs_saved"].sum()
        st["xwoba"] = pw.groupby("batter")["x"].mean()
        st["woba"] = pw.groupby("batter")["w"].mean()
        st["k_rate"] = p.groupby("batter")["strikeout"].mean()
        st["bb_rate"] = p.groupby("batter")["walk"].mean()
        st["zone_swing_rate"] = pick(zone, season, period).groupby("batter")["is_swing"].mean()
        st["far_off_chase_rate"] = pick(far, season, period).groupby("batter")["is_swing"].mean()
        st["xchase_plus"] = 100 + 100 * (st["runs_saved"] * PA_SCALE / st["pa"]) / scale[season]
        st["offense_runs"] = (st["xwoba"] - league_x[season]) / woba_scale[season] * PA_SCALE
        st["woba_runs"] = (st["woba"] - league_w[season]) / woba_scale[season] * PA_SCALE
        st["game_year"], st["period"] = season, period
        stats.append(st.reset_index())

        for batter, mine in d[d["batter"].isin(st.index)].groupby("batter"):
            lk = lr.leak_cells(mine, PA_SCALE / st.loc[batter, "pa"], "e").head(lr.LEAK_TOP)
            lk["batter"], lk["game_year"], lk["period"] = batter, season, period
            leaks.append(lk)
        cells[(season, period)] = d.groupby(["batter"] + lr.LEAK_CELL).agg(
            n=("is_chase", "size"), chases=("is_chase", "sum"), expected=("e", "sum"),
            choices=("choices", "sum"))

        through = lr.through_counts(pick(base, season, period), p)
        cc = lr.count_check(through, hitters)
        cc["game_year"], cc["period"] = season, period
        checks.append(cc)

stats = pd.concat(stats, ignore_index=True).set_index(["game_year", "period", "batter"])
leaks = pd.concat(leaks, ignore_index=True)
checks = (pd.concat(checks, ignore_index=True)
          .set_index(["game_year", "period", "batter", "count_group"])["gap"])

# --------------------------------------------------
# PAIRS
# --------------------------------------------------

print("Pairing periods...")
OUTCOMES = ["xchase_plus", "offense_runs", "woba_runs", "bb_rate", "k_rate",
            "zone_swing_rate", "far_off_chase_rate"]
specs = ([(s, "full", s + 1, "full", "season") for s in range(2021, 2026)]
         + [(s, "h1", s, "h2", "half") for s in range(2021, 2027)])
pairs = []
for s1, p1, s2, p2, kind in specs:
    if (s1, p1) not in cells or (s2, p2) not in cells:
        continue
    a = stats.loc[(s1, p1)]
    b = stats.loc[(s2, p2)]
    both = a.index.intersection(b.index)
    lk = leaks[(leaks["game_year"] == s1) & (leaks["period"] == p1) & leaks["batter"].isin(both)]
    if lk.empty:
        continue
    at = ["batter"] + lr.LEAK_CELL
    lk = (lk.join(cells[(s1, p1)].add_suffix("_1"), on=at)
            .join(cells[(s2, p2)].add_suffix("_2"), on=at))
    for c in ("n_2", "chases_2", "expected_2", "choices_2"):
        lk[c] = lk[c].fillna(0.0)
    lk["count_gap"] = checks.reindex(pd.MultiIndex.from_arrays(
        [np.full(len(lk), s1), np.full(len(lk), p1), lk["batter"], lk["count_group"]])).to_numpy()
    g = lk.groupby("batter").agg(
        leaks=("n_1", "size"), pitches_1=("n_1", "sum"), chases_1=("chases_1", "sum"),
        expected_1=("expected_1", "sum"), choices_1=("choices_1", "sum"),
        pitches_2=("n_2", "sum"), chases_2=("chases_2", "sum"),
        expected_2=("expected_2", "sum"), choices_2=("choices_2", "sum"))
    g["leak_count_gap"] = (lk.assign(w=lk["n_1"] * lk["count_gap"]).groupby("batter")["w"].sum()
                           / g["pitches_1"])
    top = lk.sort_values("choices").groupby("batter").head(1).set_index("batter")
    g["top_leak"] = top["count_group"] + " / " + top["pitch_group"] + " / " + top["region"]
    g["top_leak_count_group"] = top["count_group"]
    g["leak_excess_1"] = (g["chases_1"] - g["expected_1"]) / g["pitches_1"]
    g["leak_excess_2"] = (g["chases_2"] - g["expected_2"]) / g["pitches_2"].where(g["pitches_2"] > 0)
    g["leak_chase_rate_1"] = g["chases_1"] / g["pitches_1"]
    g["leak_chase_rate_2"] = g["chases_2"] / g["pitches_2"].where(g["pitches_2"] > 0)
    g["leak_choices_per_600_1"] = g["choices_1"] * PA_SCALE / a.loc[g.index, "pa"]
    g["leak_choices_per_600_2"] = g["choices_2"] * PA_SCALE / b.loc[g.index, "pa"]
    for m in OUTCOMES + ["pa"]:
        g[m + "_1"] = a.loc[g.index, m]
        g[m + "_2"] = b.loc[g.index, m]
        g["change_" + m] = g[m + "_2"] - g[m + "_1"]
    g["kind"], g["season_1"], g["period_1"], g["season_2"], g["period_2"] = kind, s1, p1, s2, p2
    pairs.append(g.reset_index())
pairs = pd.concat(pairs, ignore_index=True)
pairs = pairs[pairs["pitches_2"] >= MIN_SECOND_PERIOD_PITCHES].copy()
pairs = pairs.merge(boards.rename(columns={"game_year": "season_1"}), on=["batter", "season_1"])
pairs["change_leak_choices"] = pairs["leak_choices_per_600_2"] - pairs["leak_choices_per_600_1"]

# --------------------------------------------------
# TESTS
# --------------------------------------------------


def ols(y, columns, cluster):
    """OLS with an intercept; standard errors clustered by `cluster`."""

    X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in columns])
    y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    bread = np.linalg.inv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    for c in np.unique(cluster):
        s = X[cluster == c].T @ resid[cluster == c]
        meat += np.outer(s, s)
    groups = len(np.unique(cluster))
    cov = bread @ meat @ bread * groups / (groups - 1)
    return beta, np.sqrt(np.diag(cov))


summary = []


def record(kind, measure, test, value, se, n, hitters):
    summary.append({"pair_kind": kind, "measure": measure, "test": test, "value": value,
                    "se": se, "n_pairs": n, "n_hitters": hitters})


fits = {}
for kind, P in pairs.groupby("kind"):
    P = P.dropna(subset=["leak_excess_1", "leak_excess_2"]).copy()
    n, hitters = len(P), P["batter"].nunique()
    cluster = P["batter"].to_numpy()

    slope, intercept = np.polyfit(P["leak_excess_1"], P["leak_excess_2"], 1)
    P["fix"] = P["leak_excess_2"] - (intercept + slope * P["leak_excess_1"])
    fits[kind] = (intercept, slope)
    record(kind, "leak_excess", "first period mean", P["leak_excess_1"].mean(), np.nan, n, hitters)
    record(kind, "leak_excess", "second period mean", P["leak_excess_2"].mean(), np.nan, n, hitters)
    record(kind, "leak_excess", "carried over (slope)", slope, np.nan, n, hitters)
    record(kind, "leak_chase_rate", "first period mean", P["leak_chase_rate_1"].mean(), np.nan, n, hitters)
    record(kind, "leak_chase_rate", "second period mean", P["leak_chase_rate_2"].mean(), np.nan, n, hitters)

    # 1. payoff per 10-point cut beyond expected
    for m in OUTCOMES:
        ok = P["change_" + m].notna() & P[m + "_1"].notna()
        Q = P[ok]
        beta, se = ols(Q["change_" + m], [Q["fix"], Q["leak_excess_1"], Q[m + "_1"]],
                       Q["batter"].to_numpy())
        record(kind, m, "per 10-pt cut beyond expected", -0.1 * beta[1], 0.1 * se[1], len(Q),
               Q["batter"].nunique())

    # 2. run accounting
    for m in ("offense_runs", "woba_runs", "xchase_plus"):
        beta, se = ols(P["change_" + m], [P["change_leak_choices"], P["leak_choices_per_600_1"],
                                          P[m + "_1"]], cluster)
        record(kind, m, "per run of leak choices recovered", beta[1], se[1], n, hitters)

    # 3. does the count check change the payoff?
    Q = P.dropna(subset=["leak_count_gap"])
    beta, se = ols(Q["change_offense_runs"],
                   [Q["fix"], Q["fix"] * Q["leak_count_gap"], Q["leak_count_gap"],
                    Q["leak_excess_1"], Q["offense_runs_1"]], Q["batter"].to_numpy())
    # payoff per 10-pt cut, and how much it moves per +20 pts of xwOBA in the leak's counts
    record(kind, "offense_runs", "count check: payoff at league average in the counts",
           -0.1 * beta[1], 0.1 * se[1], len(Q), Q["batter"].nunique())
    record(kind, "offense_runs", "count check: payoff change per +20 pts xwOBA in the counts",
           -0.1 * beta[2] * 0.020, 0.1 * se[2] * 0.020, len(Q), Q["batter"].nunique())
    P["count_status"] = np.select([P["leak_count_gap"] <= -lr.COUNT_MARGIN,
                                   P["leak_count_gap"] >= lr.COUNT_MARGIN],
                                  ["struggling", "productive"], "average")
    for status, S in P.groupby("count_status"):
        for m in ("offense_runs", "xchase_plus"):
            beta, se = ols(S["change_" + m], [S["fix"], S["leak_excess_1"], S[m + "_1"]],
                           S["batter"].to_numpy())
            record(kind, m, f"per 10-pt cut beyond expected, {status} in the counts",
                   -0.1 * beta[1], 0.1 * se[1], len(S), S["batter"].nunique())

    # groups: change relative to the "as expected" group, first-period levels held fixed
    P["group"] = np.select([P["fix"] <= -GROUP_CUTOFF, P["fix"] >= GROUP_CUTOFF],
                           ["cut more than expected", "chased more than expected"], "as expected")
    for m in OUTCOMES:
        Q = P.dropna(subset=["change_" + m, m + "_1"])
        dummies = [(Q["group"] == g).astype(float) for g in
                   ("cut more than expected", "chased more than expected")]
        beta, se = ols(Q["change_" + m], dummies + [Q["leak_excess_1"], Q[m + "_1"]],
                       Q["batter"].to_numpy())
        for k, g in enumerate(("cut more than expected", "chased more than expected"), start=1):
            Gq = Q[Q["group"] == g]
            record(kind, m, f"group vs as expected: {g}", beta[k], se[k], len(Gq),
                   Gq["batter"].nunique())
    pairs.loc[P.index, "fix"] = P["fix"]
    pairs.loc[P.index, "group"] = P["group"]
    pairs.loc[P.index, "count_status"] = P["count_status"]

summary = pd.DataFrame(summary)

# --------------------------------------------------
# WRITE
# --------------------------------------------------

OUT.mkdir(parents=True, exist_ok=True)
keep = (["kind", "player", "batter", "season_1", "period_1", "season_2", "period_2", "leaks",
         "top_leak", "top_leak_count_group", "pitches_1", "pitches_2", "leak_chase_rate_1",
         "leak_chase_rate_2", "leak_excess_1", "leak_excess_2", "fix", "group",
         "leak_choices_per_600_1", "leak_choices_per_600_2", "leak_count_gap", "count_status"]
        + [f"{m}_{i}" for m in OUTCOMES + ["pa"] for i in (1, 2)]
        + [f"change_{m}" for m in OUTCOMES])
pairs = pairs.dropna(subset=["fix"])
pairs[keep].sort_values(["kind", "season_1", "player"]).to_csv(
    OUT / "leak_backtest_pairs.csv", index=False, float_format="%.4f")
summary.to_csv(OUT / "leak_backtest_summary.csv", index=False, float_format="%.5f")

# --------------------------------------------------
# REPORT
# --------------------------------------------------

latest = int(boards["game_year"].max())
card_file = CLEAN / f"card_players_{latest}.json"
if card_file.exists():
    import json
    card = json.loads(card_file.read_text())["players"]
    mine = leaks[(leaks["game_year"] == latest) & (leaks["period"] == "full")]
    same = total = 0
    for p in card:
        ours = mine[mine["batter"] == p["id"]]
        if p["leaks"]["all"] and len(ours):
            total += 1
            top = p["leaks"]["all"][0]
            same += tuple(ours.iloc[0][lr.LEAK_CELL]) == (top["count_group"], top["pitch_group"],
                                                         top["region"])
    print(f"\n{latest}: the backtest's top leak matches the card's for {same} of {total} hitters.")

S = summary.set_index(["pair_kind", "measure", "test"])
for kind, label in (("season", "Season to next season"), ("half", "First half to second half")):
    n = int(S.loc[(kind, "xchase_plus", "per 10-pt cut beyond expected"), "n_pairs"])
    h = int(S.loc[(kind, "xchase_plus", "per 10-pt cut beyond expected"), "n_hitters"])
    i, s = fits[kind]
    print(f"\n{label}: {n} pairs, {h} hitters")
    print(f"  leak chasing, points above the league: "
          f"{S.loc[(kind, 'leak_excess', 'first period mean'), 'value'] * 100:.1f} -> "
          f"{S.loc[(kind, 'leak_excess', 'second period mean'), 'value'] * 100:.1f} "
          f"(next = {i * 100:+.1f} + {s:.2f} x first)")
    print("  per 10-point cut beyond expected:")
    for m, lab, k, unit in [("xchase_plus", "xChase+", 1, "pts"),
                            ("offense_runs", "offense (xwOBA)", 1, "runs / 600 PA"),
                            ("woba_runs", "offense (wOBA)", 1, "runs / 600 PA"),
                            ("bb_rate", "BB%", 100, "pts"), ("k_rate", "K%", 100, "pts"),
                            ("zone_swing_rate", "zone swing rate", 100, "pts"),
                            ("far_off_chase_rate", "far-off chase rate", 100, "pts")]:
        r = S.loc[(kind, m, "per 10-pt cut beyond expected")]
        print(f"    {lab:20s} {r['value'] * k:+6.2f} ± {r['se'] * k:4.2f} {unit}")
    r = S.loc[(kind, "offense_runs", "per run of leak choices recovered")]
    print(f"  offense runs per run of leak choices recovered: {r['value']:+.2f} ± {r['se']:.2f}")
    r = S.loc[(kind, "offense_runs", "count check: payoff change per +20 pts xwOBA in the counts")]
    print(f"  payoff change per +20 pts xwOBA in the leak's counts: {r['value']:+.2f} ± {r['se']:.2f} runs")
    for status in ("struggling", "average", "productive"):
        r = S.loc[(kind, "offense_runs", f"per 10-pt cut beyond expected, {status} in the counts")]
        print(f"    {status:10s} in the counts ({int(r['n_pairs']):4d} pairs): "
              f"{r['value']:+.2f} ± {r['se']:.2f} runs per 10-pt cut")
print(f"\nWrote leak_backtest_pairs.csv and leak_backtest_summary.csv to "
      f"{OUT.relative_to(PROJECT_DIR)}/")
