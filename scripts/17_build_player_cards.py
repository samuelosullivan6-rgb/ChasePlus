"""
Step 17: a decision card for every qualified hitter.

Each card answers "where do I swing at balls more than other hitters do,
and what is it costing me?" for one hitter-season:

  - a zone picture for each count group (first pitch / ahead / even or
    behind / two strikes), for all pitchers and split by pitcher hand,
    colored by how much more (red) or less (blue) often the hitter chases than
    an average hitter at the same spot, count and matchup. Where they saw
    few pitches the color fades out (see card_surfaces.py);
  - the biggest leaks, numbered on the pictures, in runs per 600 PA;
  - a count table with the hitter's rates next to the league's, and the
    count check from step 15: his xwOBA once the count gets there, next
    to the league's in the same counts;
  - the far-off chase rate by season against the league's;
  - a short plan in plain language, written to the player, and at the
    foot of the card what step 16 found when hitters fixed their leaks.

The leak rule, the labels and the choices / contact split come from
leak_rules.py, which steps 15 and 16 share.

Hitters whose problem is contact rather than choices (the execution-led
group from step 13) also get a whiff picture: how often they miss when
they do chase, against the league on the same pitches.

OUTPUTS
  results/xchase/player_cards/index.html
      every qualified hitter plus the average right- and left-handed
      hitter, interactive and self-contained (open it in a browser)
  results/xchase/noted_players/
      README.md, a card and a short write-up for the 17 hitters named in
      the step 12 and 13 reports, and cards/*.png (light and dark)
  results/xchase/player_cards/reference/*.png
      the average right- and left-handed hitter, for comparison
  results/xchase/player_cards/player_cards_<season>.csv
      one row per hitter: the numbers behind the header and plan

Options: --season (default 2026), --static NAME [NAME ...] to also draw
PNG cards for any hitters by name, --static-all to draw every hitter
(into player_cards/static/, which is not committed).

Needs steps 04 (--expected-contact), 13, 15 and 16 first.
"""

import argparse
import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import brentq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import card_surfaces as cs  # noqa: E402
import leak_rules as lr  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
CLEAN = PROJECT_DIR / "data" / "cleaned"
XCHASE = PROJECT_DIR / "results" / "xchase"
CARDS_DIR = XCHASE / "player_cards"
NOTED_DIR = XCHASE / "noted_players"
TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

parser = argparse.ArgumentParser(description="Player decision cards.")
parser.add_argument("--season", type=int, default=2026)
parser.add_argument("--static", nargs="*", default=[],
                    help="also draw PNG cards for these hitters (by name)")
parser.add_argument("--static-all", action="store_true",
                    help="draw a PNG card for every qualified hitter")
parser.add_argument("--skip-png", action="store_true",
                    help="build the data and the HTML page only")
args = parser.parse_args()
SEASON = args.season

PA_SCALE = 600
FAR_OFF_FT = 0.35
SWITCH_SHARE = 0.15             # bats from each side on 15%+ of pitches
ABS_TOP_SHARE = 0.535           # 2026 zone top = 53.5% of the batter's height
TREND_MIN_FAR_PITCHES = 150

COUNT_GROUPS = ["first", "ahead", "even", "two"]
COUNT_LABELS = {
    "first": "First pitch",
    "ahead": "Ahead in the count",
    "even": "Even or behind",
    "two": "Two strikes",
}
COUNT_DETAIL = {
    "first": "0-0",
    "ahead": "1-0  2-0  3-0  2-1  3-1",
    "even": "0-1  1-1",
    "two": "0-2  1-2  2-2  3-2",
}
HANDS = ["all", "R", "L"]
PITCH_GROUPS = ["fastball", "breaking", "offspeed"]

# The 17 hitters named in the step 12 and 13 reports, with a coach's
# note condensed from those reports. Everything else on their cards is
# computed, the same as for every other hitter.
NOTED = {
    # Easiest to improve (step 13): decision-only, persistent pattern
    "Salvador Pérez": ("easiest", "Volume, not contact: these chases turn out better than the league's, which softens every leak but erases none. Start with breaking balls before two strikes, where the take costs nothing in strikeouts."),
    "Michael Harris": ("easiest", "One pitch type: soft stuff below the zone with two strikes, mostly from right-handers, about half his net loss. His contact is among the best in this group, so nothing else needs to change."),
    "Ernie Clement": ("easiest", "The high fastball before two strikes. He puts 44% of those chases in play (league 18%), so it never looks like a mistake, but it is weak contact (.173 xwOBA vs .283) that gives away a hitter's count."),
    "Angel Martínez": ("easiest", "Two strikes, right-hander, soft stuff that starts at the knees: take it. The contact is there on the swings that stay."),
    "Ceddanne Rafaela": ("easiest", "The high fastball with two strikes first. His early-count chasing came down in 2025 (35% to 28% of far-off pitches) but is still well above the league's 17% and costs about 4 runs; it is next."),
    "José Caballero": ("easiest", "One pitch with two strikes: the fastball above the belt. He has chased more of the far-off ones every year (55%, 65%, 77% since 2024), even in 2025, when his xChase+ was 109."),
    "Ozzie Albies": ("easiest", "Changeups and splitters that dive below the knees, in every count, from both hands. Against left-handers he chases far-off pitches of every kind more (35% vs 19%)."),
    "Luis García": ("easiest", "With three balls, swing only at strikes: that is the big one, about 5 runs. With two strikes he chases nine high fastballs in ten, but his contact there pays for it, so leave that pitch alone."),
    "Hunter Goodman": ("easiest", "The free part is the breaking ball below the zone before two strikes (48% vs 30%, about 5 runs). The high fastball looks worse than it is: his contact nearly pays for it. The two-strike breaking ball may be contact as much as choice."),
    # Biggest losses (step 12): the bottom 10 not already listed
    "Mickey Moniak": ("biggest", "Two separate leaks: high fastballs early, low breaking balls with two strikes. Fix the early one first; it costs nothing in strikeouts."),
    "Ezequiel Tovar": ("biggest", "Breaking balls that start at the knees and keep dropping are a take in every count, and the changeup below the zone is the second piece. The fastball decisions are fine."),
    "Andrés Giménez": ("biggest", "Not new: xChase+ 69 and 74 in 2022-23, then 95 and 105, and back to 67. Find out what made 2024-25 work before changing anything; the target is 0-1 and 1-1."),
    "Jarren Duran": ("biggest", "A contact problem: six chases in ten are misses. The two-strike take line should be stricter than league norms, especially below the knees against right-handers."),
    "Colson Montgomery": ("biggest", "A contact problem: two chases in three are misses, so a chase is close to a sure strike. Start by taking the first-strike pitch below the zone."),
    "Zach Neto": ("biggest", "Sliders below the zone from right-handers. He chased them well above league in 2024 and 2025 too; in 2026 pitchers threw him far more (290, up from 184). Sit fastball; the fastball decisions are a strength."),
    "Oswald Peraza": ("biggest", "Three-ball counts first: swing only at strikes (62% chase against about 40%, about 5 runs in 45 pitches). Then two-strike soft stuff down, the bigger loss. Smallest sample of the group."),
    "Jeremy Peña": ("biggest", "The first pitch, and the two-strike slider away from right-handers. Keep the aggression up in the zone; that is where the damage comes from."),
}
README_EXAMPLE = "Salvador Pérez"

# --------------------------------------------------
# LOAD
# --------------------------------------------------

print(f"Loading {SEASON} pitches...")
costs = pd.read_parquet(CLEAN / "xchase_costs_by_pitch.parquet")
pitch_cols = ["game_pk", "at_bat_number", "pitch_number", "batter", "game_year",
              "stand", "p_throws", "pitch_type", "description", "plate_x_batter",
              "plate_z_normalized", "sz_top", "sz_bot"]
base = pd.read_parquet(CLEAN / "baseline_chase_pitches.parquet", columns=pitch_cols
                       + ["is_analyzable", "is_outside_zone", "is_swing",
                          "distance_outside_zone"])
keys = ["game_pk", "at_bat_number", "pitch_number", "batter", "game_year"]

# Far-off chase rate by season, every season (for the trend strip)
far_all = base[(base["is_analyzable"] == 1) & (base["is_outside_zone"] == 1)
               & (base["distance_outside_zone"] > FAR_OFF_FT)]
trend = (far_all.groupby(["batter", "game_year"])["is_swing"]
         .agg(["mean", "size"]).reset_index()
         .rename(columns={"mean": "far_off_chase_rate", "size": "far_off_pitches"}))
trend = trend[trend["far_off_pitches"] >= TREND_MIN_FAR_PITCHES]
league_trend = far_all.groupby("game_year")["is_swing"].mean()

df = costs[costs["game_year"] == SEASON].merge(
    base[base["game_year"] == SEASON][pitch_cols], on=keys, how="left",
    validate="one_to_one")
if df["pitch_type"].isna().mean() > 0.01:
    raise SystemExit("More than 1% of priced pitches did not join to the pitch file.")
df = df[df["plate_x_batter"].notna() & df["plate_z_normalized"].notna()].reset_index(drop=True)

ZONE_HEIGHT = float((df["sz_top"] - df["sz_bot"]).mean())
df["x"] = df["plate_x_batter"]
df["z"] = df["plate_z_normalized"] * ZONE_HEIGHT
# What the card draws: the catcher's view (nobody is mirrored) and real
# height above the ground, around each hitter's own zone. x and z above
# stay batter-relative for the league comparison and the zone regions.
df["xd"] = np.where(df["stand"] == "L", -df["x"], df["x"])
df["zd"] = df["sz_bot"] + df["plate_z_normalized"] * (df["sz_top"] - df["sz_bot"])
df["whiff"] = df["description"].isin(lr.WHIFFS).astype(int)
df["count_state"] = df["balls"].astype(str) + "-" + df["strikes"].astype(str)
df = lr.add_labels(df, ZONE_HEIGHT)          # count_group, pitch_group, region
df["far_off"] = df["distance_outside_zone"] > FAR_OFF_FT

# Choices and contact: the decision / execution split from steps 12-13
df = lr.add_choices_contact(df)

# --------------------------------------------------
# LEAGUE EXPECTATION FOR EVERY PITCH
#
# A fine location surface for each exact count (all hitters), a matchup
# adjustment from coarser surfaces per count group x batter side x
# pitcher hand, then a log-odds shift per cell so the expectation adds up
# exactly to the league's own rates in the cells step 04 uses.
# --------------------------------------------------

print("Fitting league expectations...")
LX = np.arange(-3.5, 3.5 + 1e-9, 0.05)
LZ = np.arange(-3.0, 4.6 + 1e-9, 0.05)
EDGES = (np.append(LX - 0.025, LX[-1] + 0.025), np.append(LZ - 0.025, LZ[-1] + 0.025))


def smooth_rate(sub, ycol, sigma_ft):
    xs = np.clip(sub["x"].to_numpy(), LX[0], LX[-1])
    zs = np.clip(sub["z"].to_numpy(), LZ[0], LZ[-1])
    n, _, _ = np.histogram2d(xs, zs, bins=EDGES)
    c, _, _ = np.histogram2d(xs, zs, bins=EDGES, weights=sub[ycol].to_numpy(float))
    s = sigma_ft / 0.05
    n = gaussian_filter(n, s, mode="nearest")
    c = gaussian_filter(c, s, mode="nearest")
    guard = 0.02
    return (c + guard * sub[ycol].mean()) / (n + guard)


def at_pitches(surface_grid, sub):
    f = RegularGridInterpolator((LX, LZ), surface_grid, bounds_error=False, fill_value=None)
    pts = np.column_stack([np.clip(sub["x"].to_numpy(), LX[0], LX[-1]),
                           np.clip(sub["z"].to_numpy(), LZ[0], LZ[-1])])
    return f(pts)


def logit(p):
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def calibrate(p, y, group_frame):
    out = p.copy()
    base_logit = logit(p)
    for _, idx in group_frame.groupby(list(group_frame.columns)).groups.items():
        ii = np.asarray(idx)
        target = y[ii].mean()
        if len(ii) < 30 or target <= 0 or target >= 1:
            continue
        shift = brentq(lambda c: (1 / (1 + np.exp(-(base_logit[ii] + c)))).mean() - target, -6, 6)
        out[ii] = 1 / (1 + np.exp(-(base_logit[ii] + shift)))
    return np.clip(out, 0.002, 0.998)


def expectation(frame, ycol, fine_by, fine_sigma, coarse_sigma, calib_all, calib_match):
    """League expectation of ycol for each row of frame: (full league, same matchup)."""

    full = np.full(len(frame), np.nan)
    for _, sub in frame.groupby(fine_by):
        idx = frame.index.get_indexer(sub.index)
        full[idx] = at_pitches(smooth_rate(sub, ycol, fine_sigma), sub)
    adjust = np.zeros(len(frame))
    for _, sub in frame.groupby("count_group"):
        everyone = smooth_rate(sub, ycol, coarse_sigma)
        for _, side in sub.groupby(["stand", "p_throws"]):
            idx = frame.index.get_indexer(side.index)
            adjust[idx] = (at_pitches(smooth_rate(side, ycol, coarse_sigma), side)
                           - at_pitches(everyone, side))
    y = frame[ycol].to_numpy(float)
    full = calibrate(np.clip(full, 0.002, 0.998), y, frame[calib_all].reset_index(drop=True))
    match = calibrate(np.clip(full + adjust, 0.002, 0.998), y,
                      frame[calib_match].reset_index(drop=True))
    return full, match


df["e_all"], df["e_match"] = expectation(
    df, "is_chase", "count_state", 0.08, 0.12,
    ["count_state", "distance_bucket"],
    ["count_group", "distance_bucket", "stand", "p_throws"])

chases = df[df["is_chase"] == 1].copy().reset_index()
w_all, w_match = expectation(
    chases.set_index("index"), "whiff", "count_group", 0.12, 0.18,
    ["count_group", "distance_bucket"],
    ["count_group", "distance_bucket", "stand", "p_throws"])
df["w_all"] = np.nan
df["w_match"] = np.nan
df.loc[chases["index"], "w_all"] = w_all
df.loc[chases["index"], "w_match"] = w_match

for col, y in [("e_all", "is_chase"), ("e_match", "is_chase")]:
    worst = (df.groupby(["count_group", "distance_bucket"])
             .apply(lambda g: abs(g[col].mean() - g[y].mean())).max())
    print(f"  {col}: worst cell miss {worst * 100:.2f} pts")

# --------------------------------------------------
# HITTERS
# --------------------------------------------------

board = pd.read_csv(XCHASE / f"xchase_leaderboard_{SEASON}.csv")
action = pd.read_csv(XCHASE / "coaching" / f"actionability_{SEASON}.csv")
backtest = pd.read_csv(XCHASE / "coaching" / "leak_backtest_summary.csv")
count_check = pd.read_csv(XCHASE / "coaching" / f"count_check_{SEASON}.csv")
board = board.merge(action[["batter", "archetype", "far_off_recoverable",
                            "runs_saved_per_600", "decision_per_600", "execution_per_600"]],
                    on="batter", how="left")
n_qualified = len(board)

missing = [n for n in NOTED if n not in set(board["player"])]
if missing:
    raise SystemExit(f"Noted hitters not on the {SEASON} leaderboard: {missing}")

sides = df.groupby(["batter", "stand"]).size().unstack(fill_value=0)
sides["share_min"] = sides.min(axis=1) / sides.sum(axis=1)
switch = set(sides.index[sides["share_min"] >= SWITCH_SHARE])
main_side = sides[["L", "R"]].idxmax(axis=1)

league_chase = df["is_chase"].mean()
league_whiff = df.loc[df["is_chase"] == 1, "whiff"].mean()
league_far = df.loc[df["far_off"], "is_chase"].mean()

GROUP_WORDS = {
    "first": "On the first pitch",
    "ahead": "When you're ahead in the count",
    "even": "Early in the count, at 0-1 or 1-1",
    "two": "With two strikes",
}
PITCH_WORDS = {"fastball": "fastballs", "breaking": "breaking balls",
               "offspeed": "changeups and splitters"}
REGION_WORDS = {
    "up": "above the zone", "down": "below the zone", "in": "inside off the plate",
    "away": "off the outer edge", "up-in": "up and in", "up-away": "up and away",
    "down-in": "down and in", "down-away": "down and away",
}


def hand_view(frame, hand):
    return frame if hand == "all" else frame[frame["p_throws"] == hand]


# The count check (step 15): xwOBA once the count gets there, by hitter,
# pitcher hand and count group. The shrunk estimate and its status are
# for all pitchers only.
COUNTS = {(int(r.batter), r.hand, r.count_group): r for r in count_check.itertuples()}


def count_table(p, scale, batter, hand):
    rows = []
    for g in COUNT_GROUPS + ["total"]:
        s = p if g == "total" else p[p["count_group"] == g]
        ch = s[s["is_chase"] == 1]
        far = s[s["far_off"]]
        # every plate appearance passes through 0-0, so "first" is the total
        cc = COUNTS.get((batter, hand, "first" if g == "total" else g))
        rows.append({
            "group": g, "pitches": int(len(s)),
            "chase": s["is_chase"].mean() if len(s) else None,
            "chase_league": s["e_match"].mean() if len(s) else None,
            "far": far["is_chase"].mean() if len(far) else None,
            "far_league": far["e_match"].mean() if len(far) else None,
            "whiff": ch["whiff"].mean() if len(ch) else None,
            "whiff_league": ch["w_match"].mean() if len(ch) else None,
            "choices": s["choices"].sum() * scale,
            "contact": s["contact"].sum() * scale,
            "xwoba": cc.xwoba if cc is not None else None,
            "xwoba_league": cc.league_xwoba if cc is not None else None,
        })
    return rows


def leaks(p, scale, batter):
    out = []
    cells = lr.leak_cells(p, scale, "e_match").head(lr.LEAK_TOP)
    for lk in cells.itertuples():
        s = p[(p["count_group"] == lk.count_group) & (p["pitch_group"] == lk.pitch_group)
              & (p["region"] == lk.region)]
        rhp = (s["p_throws"] == "R").mean()
        chased = s[s["is_chase"] == 1]
        side = chased["stand"].mode().iloc[0]
        on_side = chased[chased["stand"] == side]
        # Is the hitter struggling once the count gets there? All pitchers,
        # whatever the hand of the leak list.
        cc = COUNTS[(batter, "all", lk.count_group)]
        out.append({
            "count_group": lk.count_group, "pitch_group": lk.pitch_group, "region": lk.region,
            "pitches": int(lk.pitches), "chases": int(lk.chases),
            "rate": lk.rate, "league": lk.league,
            "extra_chases": float(lk.extra_chases), "choices": lk.choices, "contact": lk.contact,
            "share_rhp": float(rhp),
            "side": side, "x": float(on_side["xd"].median()), "z": float(on_side["zd"].median()),
            "count_xwoba": cc.xwoba, "count_xwoba_league": cc.league_xwoba,
            "count_xwoba_shrunk": cc.xwoba_shrunk, "count_status": cc.status,
        })
    return out


def hand_phrase(share_rhp):
    if share_rhp >= 0.8:
        return " against right-handers"
    if share_rhp <= 0.45:
        return " against left-handers"
    return ""


GROUP_WORDS_SHORT = {"first": "On the first pitch", "ahead": "When you're ahead",
                     "even": "At 0-1 or 1-1", "two": "With two strikes"}


def plan_lines(leak_list, summary):
    lines = []
    for lk in [lk for lk in leak_list if lk["choices"] <= -lr.PLAN_MIN_RUNS][:2]:
        hand = hand_phrase(lk["share_rhp"])
        opener = (GROUP_WORDS_SHORT if hand else GROUP_WORDS)[lk["count_group"]]
        lines.append(
            f"{opener}{hand}, let {PITCH_WORDS[lk['pitch_group']]} "
            f"{REGION_WORDS[lk['region']]} go. "
            f"You swung at {lk['rate'] * 100:.0f}% of them; hitters on average swing at "
            f"{lk['league'] * 100:.0f}%.")
    if summary["archetype"] == "execution-led":
        lines.append(
            f"Your bigger issue is contact: you miss on {summary['whiff'] * 100:.0f}% of your "
            f"chases, against {summary['whiff_league'] * 100:.0f}% for other hitters on the "
            "same pitches. Your chases rarely turn into anything, so your take line with two "
            "strikes can be stricter than most hitters'.")
    if not lines:
        lines.append("Nothing stands out. Your chase choices are about league average "
                     "or better in every count.")
    return lines


# What step 16 found when hitters fixed their card's leaks, as a range
# over its two kinds of pairs (season to season, first half to second).
payoff = backtest[backtest["test"] == "per 10-pt cut beyond expected"].groupby("measure")["value"]


def span(measure, k=1.0):
    lo, hi = sorted(abs(payoff.get_group(measure)) * k)
    return f"{lo:.1f} to {hi:.1f}"


EVIDENCE_QUESTION = "Does fixing a leak pay?"
EVIDENCE_LINE = (
    f"{EVIDENCE_QUESTION} Hitters who chased 10 points less on their leak pitches than their "
    f"numbers predicted gained {span('offense_runs')} runs per 600 PA (xwOBA) and "
    f"{span('xchase_plus')} xChase+ points, with only {span('zone_swing_rate', 100)} pts "
    "fewer swings at strikes. It paid about the same whether or not they hit well in "
    "those counts.")

print("Building hitter summaries...")
players = []
for _, row in board.sort_values("xchase_plus", ascending=False).iterrows():
    bid = int(row["batter"])
    p = df[df["batter"] == bid]
    scale = PA_SCALE / row["plate_appearances"]
    ch = p[p["is_chase"] == 1]
    summary = {
        "id": bid, "name": row["player"],
        "bats": "S" if bid in switch else main_side.get(bid, "R"),
        "rank": int(row["xchase_plus_rank"]), "of": n_qualified,
        "pa": int(row["plate_appearances"]), "xchase_plus": float(row["xchase_plus"]),
        "chase": float(p["is_chase"].mean()), "chase_league": float(p["e_match"].mean()),
        "whiff": float(ch["whiff"].mean()), "whiff_league": float(ch["w_match"].mean()),
        "choices": float(p["choices"].sum() * scale), "contact": float(p["contact"].sum() * scale),
        "runs_at_stake": float(max(row["far_off_recoverable"], 0.0)),
        "archetype": row["archetype"],
        "noted": NOTED.get(row["player"], (None, None))[0],
        "coach_note": NOTED.get(row["player"], (None, None))[1],
    }
    summary["tables"] = {h: count_table(hand_view(p, h), scale, bid, h) for h in HANDS}
    summary["leaks"] = {h: leaks(hand_view(p, h), scale, bid) for h in HANDS}
    summary["plan"] = plan_lines(summary["leaks"]["all"], summary)
    t = trend[trend["batter"] == bid]
    summary["trend"] = [[int(y), float(r)] for y, r in zip(t["game_year"], t["far_off_chase_rate"])]
    summary["side_pitches"] = {s: int((p["stand"] == s).sum()) for s in ("L", "R")}
    # The hitter's own zone. From 2026 (ABS) it is fixed per hitter and set
    # from their measured height, so the height can be read back from it.
    summary["zone"] = [float(p["sz_bot"].mean()), float(p["sz_top"].mean())]
    summary["height_in"] = (round(summary["zone"][1] / ABS_TOP_SHARE * 12)
                            if p["sz_top"].std() < 0.01 else None)
    players.append(summary)

print(f"  {len(players)} hitters, {len(switch & set(board['batter']))} switch hitters")

# --------------------------------------------------
# SURFACES FOR ONE HITTER
#
# Location and outcome are quantized once (the same values the HTML page
# gets), so the static images and the page compute from identical inputs.
# --------------------------------------------------

XS, ZS = cs.grid()

df["xq"] = np.round(df["xd"].clip(-3.2, 3.2) * 100).astype(int)
df["zq"] = np.round(df["zd"].clip(-1.0, 6.5) * 100).astype(int)

# The average-hitter cards have no single zone: they are drawn around the
# average zone of all hitters on that side, at each pitch's height
# relative to its own hitter's zone.
AVERAGE_ZONE = {s: [float(g["sz_bot"].mean()), float(g["sz_top"].mean())]
                for s, g in df.groupby("stand")}
df["zq_avg"] = np.round((df["stand"].map(lambda s: AVERAGE_ZONE[s][0])
                         + df["plate_z_normalized"]
                         * df["stand"].map(lambda s: AVERAGE_ZONE[s][1] - AVERAGE_ZONE[s][0]))
                        .clip(-1.0, 6.5) * 100).astype(int)


def feet_inches(inches):
    return f"{inches // 12}'{inches % 12}\""
for col in ("e_all", "e_match", "w_all", "w_match"):
    df[col + "_q"] = np.round(df[col].fillna(0) * 255).astype(int)


def player_surface(frame, metric="chase", baseline="match"):
    if metric == "whiff":
        frame = frame[frame["is_chase"] == 1]
        y = frame["whiff"].to_numpy(float)
        e = frame[f"w_{baseline}_q"].to_numpy(float) / 255
    else:
        y = frame["is_chase"].to_numpy(float)
        e = frame[f"e_{baseline}_q"].to_numpy(float) / 255
    return cs.surface(frame["xq"] / 100, frame["zq"] / 100, y, e, XS, ZS)


# --------------------------------------------------
# DRAWING
# --------------------------------------------------

import textwrap  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Circle, Rectangle  # noqa: E402

W, H = 1920, 1080
DPI = 100
FONT = ["Avenir Next", "Helvetica Neue", "Arial", "DejaVu Sans"]
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": FONT,
                     "axes.unicode_minus": True})

def px(p):
    return p * 72 / DPI



from card_style import THEMES, hex_rgb, to_oklab, from_oklab, diverging, sequential  # noqa: E402


def compose(color, evidence, theme, mask):
    surface = hex_rgb(theme["surface"])
    a = np.clip(evidence, 0, 1)[..., None]
    rgb = color * a + surface * (1 - a)
    rgb[mask] = surface
    return rgb


def fmt_runs(v):
    v = round(v, 1)
    if v == 0:
        return "0.0"
    return ("+" if v > 0 else "−") + f"{abs(v):.1f}"


def pct(v):
    return "–" if v is None or not np.isfinite(v) else f"{v * 100:.0f}%"


def outline_paths(gap, evidence, mask):
    """The +15 outline, without the specks: closed loops smaller than
    OUTLINE_MIN_AREA square feet and open lines shorter than
    OUTLINE_MIN_LENGTH feet are dropped (they are a few pitches, not a
    pattern)."""

    import contourpy
    shown = np.ma.masked_where((evidence < cs.CONTOUR_MIN_EVIDENCE) | mask, gap)
    if shown.count() == 0 or shown.max() < cs.CONTOUR_GAP:
        return []
    lines = contourpy.contour_generator(XS, ZS, shown).lines(cs.CONTOUR_GAP)
    keep = []
    for ln in lines:
        if len(ln) < 3:
            continue
        seg = np.diff(ln, axis=0)
        length = np.hypot(seg[:, 0], seg[:, 1]).sum()
        closed = np.allclose(ln[0], ln[-1])
        if closed:
            x, z = ln[:, 0], ln[:, 1]
            area = 0.5 * abs(np.dot(x, np.roll(z, 1)) - np.dot(z, np.roll(x, 1)))
            if area >= OUTLINE_MIN_AREA:
                keep.append(ln)
        elif length >= OUTLINE_MIN_LENGTH:
            keep.append(ln)
    return keep


OUTLINE_MIN_AREA = 0.35
OUTLINE_MIN_LENGTH = 1.6


class Card:
    def __init__(self, theme_name):
        self.t = THEMES[theme_name]
        self.fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
        self.fig.patch.set_facecolor(self.t["surface"])
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)
        self.ax.axis("off")

    def text(self, x, y, s, size=18, color="ink", weight="normal", ha="left", va="baseline", **kw):
        return self.ax.text(x, y, s, fontsize=px(size), color=self.t.get(color, color),
                            fontweight=weight, ha=ha, va=va, **kw)

    def wrapped(self, x, y, s, width_chars, size=18, line=26, color="ink", weight="normal"):
        lines = textwrap.wrap(s, width_chars, break_on_hyphens=False)
        for i, ln in enumerate(lines):
            self.text(x, y + i * line, ln, size=size, color=color, weight=weight)
        return y + len(lines) * line

    def hline(self, x0, x1, y, color="hair", lw=1):
        self.ax.plot([x0, x1], [y, y], color=self.t[color], lw=px(lw), solid_capstyle="butt")

    def panel(self, x, y, w, h):
        a = self.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])
        a.set_facecolor(self.t["surface"])
        a.axis("off")
        return a

    def zone(self, a, rgb, zone, mask, gap=None, evidence=None, markers=()):
        step = cs.GRID_STEP / 2
        a.imshow(rgb, origin="lower", interpolation="bilinear",
                 extent=[XS[0] - step, XS[-1] + step, ZS[0] - step, ZS[-1] + step])
        if gap is not None:
            for line in outline_paths(gap, evidence, mask):
                a.plot(line[:, 0], line[:, 1], color=self.t["ink"], lw=px(1.3),
                       solid_capstyle="round", solid_joinstyle="round")
        a.add_patch(Rectangle((-cs.HALF_PLATE_PLUS_BALL, zone[0]), 2 * cs.HALF_PLATE_PLUS_BALL,
                              zone[1] - zone[0], fill=False, ec=self.t["ink2"], lw=px(1.6)))
        # home plate edge on the ground, for scale
        a.plot([-0.708, 0.708], [0, 0], color=self.t["axis"], lw=px(3), solid_capstyle="butt")
        for number, (mx, mz) in markers:
            a.add_patch(Circle((mx, mz), 0.2, fc=self.t["surface"], ec=self.t["ink"],
                               lw=px(1.6), zorder=5))
            a.text(mx, mz - 0.01, str(number), ha="center", va="center", zorder=6,
                   fontsize=px(15), fontweight="bold", color=self.t["ink"])
        a.set_xlim(XS[0], XS[-1])
        a.set_ylim(ZS[0], ZS[-1])
        a.set_aspect("equal")

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fig.savefig(path, dpi=DPI, facecolor=self.t["surface"])
        plt.close(self.fig)


PANEL_ASPECT = (ZS[-1] - ZS[0]) / (XS[-1] - XS[0])
GRID_LEFT, GRID_TOP = 64, 196
BOTTOM_BLOCK = 866              # y where the trend + legend block starts
ROW_LABEL_W = 118
RIGHT_X, RIGHT_W = 1086, 770


def draw_grid(card, rows, cells, zone, markers=None, orient=None):
    """rows: list of (label, sublabel). cells(row_index, group) -> (rgb, gap, evidence).
    markers: {(row_index, group): [(number, (x, z)), ...]}. orient: the side the
    batter stands on ("R" or "L") for the Inside / Away labels, or None."""

    n = len(rows)
    avail_h = 1046 - (GRID_TOP + 46)
    w = min(196, (avail_h - (n - 1) * 14) / n / PANEL_ASPECT)
    h = w * PANEL_ASPECT
    x0 = GRID_LEFT + ROW_LABEL_W
    for j, g in enumerate(COUNT_GROUPS):
        cx = x0 + j * (w + 14) + w / 2
        card.text(cx, GRID_TOP + 18, COUNT_LABELS[g], size=19, weight="bold", ha="center")
        card.text(cx, GRID_TOP + 40, COUNT_DETAIL[g], size=14, color="muted", ha="center")
    for i, (label, sub) in enumerate(rows):
        y = GRID_TOP + 52 + i * (h + 14)
        card.wrapped(GRID_LEFT, y + h / 2 - 6, label, 12, size=17, line=22, weight="bold")
        if sub:
            card.wrapped(GRID_LEFT, y + h / 2 + 38, sub, 14, size=14, line=18, color="muted")
        for j, g in enumerate(COUNT_GROUPS):
            a = card.panel(x0 + j * (w + 14), y, w, h)
            rgb, gap, ev = cells(i, g)
            mask = cs.in_zone_mask(XS, ZS, *zone)
            card.zone(a, rgb, zone, mask, gap, ev, (markers or {}).get((i, g), []))
    bottom = GRID_TOP + 52 + n * (h + 14) - 14
    if orient:
        left, right = ("Inside", "Away") if orient == "R" else ("Away", "Inside")
        card.text(x0 + 4, bottom + 22, left, size=14, color="muted")
        card.text(x0 + w - 4, bottom + 22, right, size=14, color="muted", ha="right")
    card.text(x0 + 4 * (w + 14) - 14, bottom + 22, "catcher's view, to scale", size=14,
              color="muted", ha="right")
    return bottom


def draw_legend(card, x, y, kind="gap", label_left="", label_right=""):
    w, h = 300, 14
    values = np.linspace(-cs.GAP_LIMIT, cs.GAP_LIMIT, 300) if kind == "gap" else np.linspace(0, 0.7, 300)
    colors = diverging(values, card.t) if kind == "gap" else sequential(values, card.t)
    a = card.fig.add_axes([x / W, 1 - (y + h) / H, w / W, h / H])
    a.imshow(colors[None, :, :], aspect="auto", extent=[0, 1, 0, 1])
    a.axis("off")
    if kind == "gap":
        card.text(x, y + h + 20, "−30 pts", size=13, color="muted")
        card.text(x + w / 2, y + h + 20, "league", size=13, color="muted", ha="center")
        card.text(x + w, y + h + 20, "+30 pts", size=13, color="muted", ha="right")
    else:
        card.text(x, y + h + 20, "0%", size=13, color="muted")
        card.text(x + w, y + h + 20, "70%+", size=13, color="muted", ha="right")
    card.text(x, y - 8, label_left, size=14, color="ink2")


def draw_header(card, title, line1, line2):
    card.text(64, 76, title, size=46, weight="bold")
    card.text(64, 116, line1, size=20, color="ink2")
    card.text(64, 146, line2, size=20, color="ink2")
    card.hline(64, W - 64, 172)


def xw(v):
    return "–" if v is None or not np.isfinite(v) else f"{v:.3f}".lstrip("0")


def draw_table(card, x, y, rows, league_only=False):
    # A player's table adds the count check: xwOBA once the count gets
    # there, next to the league's. The average card keeps the narrow table.
    if league_only:
        at = {"pitches": 190, "chase": 290, "far": 400, "whiff": 510}
    else:
        at = {"pitches": 190, "chase": 275, "far": 360, "whiff": 445, "xwoba": 550,
              "choices": 660, "contact": 760}
    cols = [("", 0, "left"), ("Pitches", at["pitches"], "right"), ("Chases", at["chase"], "right"),
            ("Far-off", at["far"], "right"), ("Misses", at["whiff"], "right")]
    if not league_only:
        cols += [("xwOBA", at["xwoba"], "right"), ("Choices", at["choices"], "right"),
                 ("Contact", at["contact"], "right")]
    for label, cx, ha in cols:
        card.text(x + cx, y, label, size=14, color="muted", ha=ha, weight="bold")
    sub = "you / avg" if not league_only else "rate"
    for label, cx, ha in cols[2:6]:
        card.text(x + cx, y + 17, sub, size=12, color="muted", ha=ha)
    if not league_only:
        card.text(x + (at["choices"] + at["contact"]) / 2 - 22, y + 17, "runs per 600 PA",
                  size=12, color="muted", ha="center")
    y += 26
    card.hline(x, x + 770 if not league_only else x + 520, y + 4)
    names = dict(COUNT_LABELS, total="All counts")
    for r in rows:
        y += 23
        bold = "bold" if r["group"] == "total" else "normal"
        card.text(x, y, names[r["group"]], size=15, weight=bold)
        card.text(x + at["pitches"], y, f"{r['pitches']:,}", size=15, ha="right", color="ink2")
        for key in ("chase", "far", "whiff"):
            cx = at[key]
            if league_only:
                card.text(x + cx, y, pct(r[key]), size=15, ha="right", weight=bold)
            else:
                card.text(x + cx - 44, y, pct(r[key]), size=15, ha="right", weight="bold")
                card.text(x + cx, y, pct(r[key + "_league"]), size=15, ha="right", color="muted")
        if not league_only:
            card.text(x + at["xwoba"] - 48, y, xw(r["xwoba"]), size=15, ha="right", weight="bold")
            card.text(x + at["xwoba"], y, xw(r["xwoba_league"]), size=15, ha="right", color="muted")
            for key in ("choices", "contact"):
                v = r[key]
                card.text(x + at[key], y, fmt_runs(v), size=15, ha="right",
                          color="ink" if abs(v) >= 1 else "ink2", weight=bold)
    if not league_only:
        y += 24
        card.text(x, y, COUNT_CHECK_NOTE, size=12, color="muted")
    return y


COUNT_CHECK_NOTE = ("xwOBA: every plate appearance that reached those counts, against the "
                    "league's in the same counts.")


def draw_trend(card, x, y, w, h, series, league):
    years = sorted(league.index)
    span = (years[0] - 0.4, years[-1] + 0.4)
    values = [v for _, v in series] + list(league.values)
    top = max(0.4, np.ceil(max(values) * 10) / 10)
    sx = lambda yr: x + (yr - span[0]) / (span[1] - span[0]) * w  # noqa: E731
    sy = lambda v: y + h - v / top * h  # noqa: E731
    for tick in np.arange(0, top + 1e-9, 0.1):
        card.hline(x, x + w, sy(tick), color="hair")
        if round(tick * 10) % 2 == 0:
            card.text(x - 8, sy(tick) + 5, f"{tick * 100:.0f}%", size=12, color="muted", ha="right")
    for yr in years:
        card.text(sx(yr), y + h + 20, str(yr), size=12, color="muted", ha="center")
    card.ax.plot([sx(yr) for yr in years], [sy(league[yr]) for yr in years],
                 color=card.t["league"], lw=px(2), solid_capstyle="round")
    avg_y = sy(league[years[-1]]) + 5
    if series and abs(sy(series[-1][1]) - sy(league[years[-1]])) < 14:
        avg_y = max(sy(series[-1][1]), sy(league[years[-1]])) + 18
    card.text(sx(years[-1]) + 10, avg_y, "avg", size=13, color="muted")
    if series:
        xs_ = [sx(yr) for yr, _ in series]
        ys_ = [sy(v) for _, v in series]
        card.ax.plot(xs_, ys_, color=card.t["blue"], lw=px(2.4), solid_capstyle="round")
        card.ax.scatter(xs_, ys_, s=px(9) ** 2, color=card.t["blue"], zorder=4,
                        edgecolors=card.t["surface"], linewidths=px(2))
        card.text(xs_[-1] + 10, ys_[-1] + 5, "you", size=13, color="ink", weight="bold")


LEAK_PITCH = {"fastball": "fastballs", "breaking": "breaking balls", "offspeed": "changeups / splitters"}
LEAK_REGION = {"up": "above the zone", "down": "below the zone", "in": "inside", "away": "away",
               "up-in": "up and in", "up-away": "up and away", "down-in": "down and in",
               "down-away": "down and away"}


def row_specs(summary):
    """(label, sublabel, batting side, pitcher hand, metric) for each picture row.

    Pictures are never mirrored, so one row only ever holds pitches seen
    from one side of the plate. A switch hitter's rows are the two sides,
    which are also, almost pitch for pitch, the pitcher-hand split."""

    if summary["bats"] == "S":
        rows = [("Batting left", "mostly vs RHP; inside is on the right", "L", "all", "chase"),
                ("Batting right", "mostly vs LHP; inside is on the left", "R", "all", "chase")]
    else:
        side = summary["bats"]
        rows = [("All pitchers", None, side, "all", "chase"),
                ("vs RHP", "right-handed pitchers", side, "R", "chase"),
                ("vs LHP", "left-handed pitchers", side, "L", "chase")]
    if summary["archetype"] == "execution-led":
        side = summary["bats"] if summary["bats"] != "S" else max(
            summary["side_pitches"], key=summary["side_pitches"].get)
        rows.append(("Misses on chases", "how often a chase is a swing and miss, vs avg",
                     side, "all", "whiff"))
    return rows


def leak_markers(summary, specs):
    """Numbered leak markers, on the first row showing that leak's side."""

    markers = {}
    for n, lk in enumerate(summary["leaks"]["all"], start=1):
        row = next((i for i, sp in enumerate(specs) if sp[2] == lk["side"] and sp[4] == "chase"), None)
        if row is None:
            continue
        key = (row, lk["count_group"])
        spot = np.array([lk["x"], lk["z"]])
        for _, other in markers.get(key, []):
            if np.hypot(*(spot - np.array(other))) < 0.45:
                spot = spot + np.array([0.48 if spot[0] <= 0 else -0.48, 0.0])
        markers.setdefault(key, []).append((n, tuple(spot)))
    return markers


def player_card(summary, theme_name, out_path):
    card = Card(theme_name)
    t = card.t
    p = df[df["batter"] == summary["id"]]
    bats = {"R": "Bats right", "L": "Bats left", "S": "Switch hitter"}[summary["bats"]]
    if summary["height_in"]:
        bats += f"   \u00b7   {feet_inches(summary['height_in'])}"
    rank = summary["rank"]
    suffix = "th" if 10 <= rank % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    draw_header(
        card, summary["name"],
        f"{bats}   ·   {SEASON}   ·   {summary['pa']} PA   ·   "
        f"xChase+ {summary['xchase_plus']:.0f}, {rank}{suffix} of {summary['of']}",
        f"Swings at {summary['chase'] * 100:.0f}% of pitches outside the zone. "
        f"Hitters on average swing at {summary['chase_league'] * 100:.0f}% of the same pitches.")

    # Header tiles: runs at stake, and where the runs go
    tx = 1196
    card.text(tx, 60, "RUNS AT STAKE", size=13, color="muted", weight="bold")
    card.text(tx, 116, f"{summary['runs_at_stake']:.1f}", size=54, weight="bold")
    card.text(tx, 146, "per 600 PA, on far-off pitches", size=14, color="ink2")
    bx = 1470
    card.text(bx, 60, "WHERE THE RUNS GO", size=13, color="muted", weight="bold")
    card.text(W - 64, 60, "per 600 PA", size=13, color="muted", ha="right")
    zero, half = bx + 215, 95
    for k, (label, v) in enumerate([("Choices", summary["choices"]), ("Contact", summary["contact"])]):
        yy = 96 + k * 38
        card.text(bx, yy + 6, label, size=16, color="ink2")
        length = np.clip(v, -25, 25) / 25 * half
        card.ax.add_patch(Rectangle((zero + min(0, length), yy - 8), abs(length), 16,
                                    fc=t["red"] if v < 0 else t["blue"], ec="none"))
        card.text(W - 64, yy + 6, fmt_runs(v), size=17, weight="bold", ha="right")
    card.ax.plot([zero, zero], [80, 150], color=t["axis"], lw=px(1.2))

    # Zone pictures
    specs = row_specs(summary)
    rows = [(label, sub) for label, sub, _, _, _ in specs]
    mask = cs.in_zone_mask(XS, ZS, *summary["zone"])

    def cells(i, g):
        _, _, side, hand, metric = specs[i]
        frame = p[(p["count_group"] == g) & (p["stand"] == side)]
        if hand != "all":
            frame = frame[frame["p_throws"] == hand]
        s = player_surface(frame, metric)
        return compose(diverging(s["gap"], t), s["evidence"], t, mask), s["gap"], s["evidence"]

    markers = leak_markers(summary, specs)
    draw_grid(card, rows, cells, summary["zone"], markers,
              None if summary["bats"] == "S" else summary["bats"])

    # Right column
    y = 214
    card.text(RIGHT_X, y, "What to work on", size=22, weight="bold")
    y += 32
    for line in summary["plan"]:
        card.ax.add_patch(Circle((RIGHT_X + 6, y - 6), 4, fc=t["ink"], ec="none"))
        y = card.wrapped(RIGHT_X + 22, y, line, 80, size=16, line=22) + 6
    if summary["coach_note"]:
        y += 4
        card.text(RIGHT_X, y, "COACH'S NOTE", size=12, color="muted", weight="bold")
        y = card.wrapped(RIGHT_X, y + 20, summary["coach_note"], 90, size=14, line=19, color="ink2")
    y += 18
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    card.text(RIGHT_X, y + 20, "Biggest leaks", size=19, weight="bold")
    card.text(RIGHT_X + RIGHT_W, y + 20, "numbered on the zone, all pitchers", size=13,
              color="muted", ha="right")
    y += 30
    if not summary["leaks"]["all"]:
        y += 24
        card.text(RIGHT_X, y, "None worth a run per 600 PA.", size=16, color="ink2")
    for n, lk in enumerate(summary["leaks"]["all"], start=1):
        y += 32
        card.ax.add_patch(Circle((RIGHT_X + 12, y - 6), 12, fc=t["surface"], ec=t["ink"], lw=px(1.6)))
        card.text(RIGHT_X + 12, y - 5, str(n), size=14, weight="bold", ha="center", va="center")
        label = (f"{COUNT_LABELS[lk['count_group']]}, {LEAK_PITCH[lk['pitch_group']]} "
                 f"{LEAK_REGION[lk['region']]}")
        card.text(RIGHT_X + 34, y, label, size=16)
        # you vs league on a 0-100% track
        tx0, tw = RIGHT_X + 470, 150
        card.hline(tx0, tx0 + tw, y - 6, color="axis", lw=2)
        card.ax.plot([tx0 + lk["league"] * tw] * 2, [y - 14, y + 2], color=t["league"], lw=px(2.2))
        card.ax.scatter([tx0 + lk["rate"] * tw], [y - 6], s=px(11) ** 2, color=t["red"],
                        edgecolors=t["surface"], linewidths=px(2), zorder=5)
        card.text(tx0 + tw + 12, y, f"{lk['rate'] * 100:.0f}% vs {lk['league'] * 100:.0f}%",
                  size=14, color="ink2")
        card.text(RIGHT_X + RIGHT_W, y, fmt_runs(lk["choices"]), size=16, weight="bold",
                  ha="right")
    y += 26
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    y = draw_table(card, RIGHT_X, y + 16, summary["tables"]["all"])
    if y > BOTTOM_BLOCK - 20:
        print(f"  warning: {summary['name']} right column runs to y={y:.0f}")
    y = BOTTOM_BLOCK
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    card.text(RIGHT_X, y + 16, "Far-off chase rate by season", size=16, weight="bold")
    draw_trend(card, RIGHT_X + 44, y + 32, 360, 58, summary["trend"], league_trend)
    draw_legend(card, RIGHT_X + 470, y + 38, "gap",
                "Chases vs average hitter, same spot and count")
    card.text(RIGHT_X + 470, y + 92, "Blue: takes more. Red: chases more.", size=13, color="ink2")
    card.text(RIGHT_X + 470, y + 110, "Faded: too few pitches to say. Outline: +15 pts.",
              size=13, color="ink2")
    foot = 1028
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, foot - 24)
    card.wrapped(RIGHT_X, foot - 6, EVIDENCE_LINE, 118, size=12, line=15, color="muted")
    card.text(W - 64, H - 14, f"xChase+ 1.1  ·  Statcast {SEASON}  ·  catcher's view, "
              "each hitter's own zone", size=12, color="muted", ha="right")
    card.save(out_path)


GUIDE = [
    "This card shows the raw chase rate of an average hitter: {more} blue means more swings. "
    "Every player card shows the difference from this instead, so nobody is judged on a "
    "pitch everyone swings at.",
    "Every card is the catcher's view at true scale. The rectangle is that hitter's own "
    "strike zone, set from their height, and the line at the bottom is home plate. A "
    "left-handed batter stands on the right, so their inside is on the right.",
    "On a player card, red is where the player swings more than this average at the same "
    "spot, count and matchup, and blue is where they take more. Gray is about average.",
    "Faded color means too few pitches there to say. An outline marks spots where the player "
    "chases 15 points or more above average.",
    "Numbers on the zone match the leaks list: the pitches whose swing choices cost the "
    "most runs, per 600 plate appearances.",
    "Choices is what the swing decisions cost. Contact is what the chases produced compared "
    "with an average hitter's chases. A contact problem needs a different fix.",
    "In the table, far-off means at least 4 inches off the plate, a pitch almost never "
    "called a strike. Misses is how often a chase is a swing and miss.",
]


def league_card(stand, theme_name, out_path):
    card = Card(theme_name)
    lg = df[df["stand"] == stand]
    word = {"R": "right", "L": "left"}[stand]
    draw_header(
        card, f"The average {word}-handed hitter",
        f"Every {word}-handed hitter in {SEASON}   ·   {len(lg):,} pitches outside the zone",
        f"Swings at {lg['is_chase'].mean() * 100:.0f}% of pitches outside the zone. "
        "This is the baseline every player card is compared against.")

    zone = AVERAGE_ZONE[stand]
    mask = cs.in_zone_mask(XS, ZS, *zone)

    def cells(i, g):
        frame = lg[lg["count_group"] == g]
        if i in (1, 2):
            frame = frame[frame["p_throws"] == ("R" if i == 1 else "L")]
        s = cs.surface(frame["xq"] / 100, frame["zq_avg"] / 100, frame["is_chase"].to_numpy(float),
                       np.zeros(len(frame)), XS, ZS)
        rate = np.nan_to_num(s["player_rate"])
        return compose(sequential(rate, card.t), np.ones_like(rate), card.t, mask), None, None

    rows = [("All pitchers", None), ("vs RHP", "right-handed pitchers"),
            ("vs LHP", "left-handed pitchers")]
    draw_grid(card, rows, cells, zone, None, stand)

    y = 214
    card.text(RIGHT_X, y, "How to read a player card", size=22, weight="bold")
    y += 34
    # The ramp runs light-to-dark on a light card and dark-to-bright on a
    # dark one, so the word for "more" follows the theme.
    steps = [g.replace("{more}", "darker" if theme_name == "light" else "brighter") for g in GUIDE]
    for n, s in enumerate(steps, start=1):
        card.ax.add_patch(Circle((RIGHT_X + 12, y - 6), 12, fc=t_surface(card), ec=card.t["ink"],
                                 lw=px(1.6)))
        card.text(RIGHT_X + 12, y - 5, str(n), size=14, weight="bold", ha="center", va="center")
        y = card.wrapped(RIGHT_X + 34, y, s, 88, size=15, line=20) + 8
    y += 8
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    rows_t = []
    scale = 0
    for g in COUNT_GROUPS + ["total"]:
        s = lg if g == "total" else lg[lg["count_group"] == g]
        far = s[s["far_off"]]
        rows_t.append({"group": g, "pitches": len(s), "chase": s["is_chase"].mean(),
                       "far": far["is_chase"].mean(),
                       "whiff": s.loc[s["is_chase"] == 1, "whiff"].mean()})
    draw_table(card, RIGHT_X, y + 16, rows_t, league_only=True)
    y = BOTTOM_BLOCK
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    card.text(RIGHT_X, y + 16, "Far-off chase rate by season, every hitter", size=16, weight="bold")
    draw_trend(card, RIGHT_X + 44, y + 32, 360, 58, [], league_trend)
    draw_legend(card, RIGHT_X + 470, y + 38, "rate", "Chase rate at each spot")
    card.text(W - 64, H - 14, f"xChase+ 1.1  ·  Statcast {SEASON}  ·  catcher's view, "
              "each hitter's own zone", size=12, color="muted", ha="right")
    card.save(out_path)


def t_surface(card):
    return card.t["surface"]


def slug(name):
    import unicodedata
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "_" for c in plain.lower()).strip("_")


# --------------------------------------------------
# THE INTERACTIVE PAGE
# --------------------------------------------------

GROUP_INDEX = {g: i for i, g in enumerate(COUNT_GROUPS)}
PITCH_INDEX = {g: i for i, g in enumerate(PITCH_GROUPS)}
RECORD = np.dtype([("x", "<i2"), ("z", "<i2"), ("flags", "u1"), ("e_all", "u1"),
                   ("e_match", "u1"), ("w_all", "u1"), ("w_match", "u1")])


def to_json_safe(o):
    if isinstance(o, dict):
        return {k: to_json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [to_json_safe(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 4)
    if isinstance(o, np.integer):
        return int(o)
    return o


def build_page():
    order = [p["id"] for p in players]
    qualified = df[df["batter"].isin(order)].copy()
    qualified["order"] = qualified["batter"].map({b: i for i, b in enumerate(order)})
    qualified = qualified.sort_values(["order", "count_group", "game_pk", "at_bat_number", "pitch_number"])
    records = np.zeros(len(qualified), dtype=RECORD)
    records["x"] = qualified["xq"]
    records["z"] = qualified["zq"]
    bits = lambda series: series.to_numpy().astype(np.uint8)  # noqa: E731
    records["flags"] = (bits(qualified["is_chase"])
                        | (bits(qualified["whiff"]) << 1)
                        | (bits(qualified["p_throws"] == "R") << 2)
                        | (bits(qualified["count_group"].map(GROUP_INDEX)) << 3)
                        | (bits(qualified["pitch_group"].map(PITCH_INDEX)) << 5)
                        | (bits(qualified["stand"] == "L") << 7))
    for col in ("e_all", "e_match", "w_all", "w_match"):
        records[col] = qualified[col + "_q"]
    blob = base64.b64encode(records.tobytes()).decode()

    offsets = qualified.groupby("batter", sort=False).size()
    start = 0
    page_players = []
    for summary in players:
        n = int(offsets.get(summary["id"], 0))
        page_players.append(dict(summary, slug=slug(summary["name"]), off=start, n=n))
        start += n

    references = []
    for stand, word in (("R", "right"), ("L", "left")):
        lg = df[df["stand"] == stand]
        grids = {}
        for hand in HANDS:
            grids[hand] = {}
            for g in COUNT_GROUPS:
                frame = hand_view(lg[lg["count_group"] == g], hand)
                srf = cs.surface(frame["xq"] / 100, frame["zq_avg"] / 100,
                                 frame["is_chase"].to_numpy(float), np.zeros(len(frame)), XS, ZS)
                rate = np.nan_to_num(srf["player_rate"])
                grids[hand][g] = base64.b64encode(
                    np.round(np.clip(rate, 0, 1) * 255).astype(np.uint8).tobytes()).decode()
        table = []
        for g in COUNT_GROUPS + ["total"]:
            sub = lg if g == "total" else lg[lg["count_group"] == g]
            table.append({"group": g, "pitches": int(len(sub)), "chase": sub["is_chase"].mean(),
                          "far": sub.loc[sub["far_off"], "is_chase"].mean(),
                          "whiff": sub.loc[sub["is_chase"] == 1, "whiff"].mean()})
        references.append({"reference": True, "slug": f"average-{word}-handed-hitter",
                           "name": f"The average {word}-handed hitter", "word": word,
                           "bats": stand, "zone": AVERAGE_ZONE[stand],
                           "pitches": int(len(lg)), "chase": lg["is_chase"].mean(),
                           "table": table, "grids": grids})

    data = {
        "season": SEASON, "gridStep": cs.GRID_STEP,
        "xs": XS.tolist(), "zs": ZS.tolist(), "recordBytes": RECORD.itemsize,
        "countGroups": [{"key": g, "label": COUNT_LABELS[g], "detail": COUNT_DETAIL[g]}
                        for g in COUNT_GROUPS],
        "leagueTrend": [[int(y), float(r)] for y, r in league_trend.items()],
        "players": page_players, "references": references,
        "defaultSlug": slug(README_EXAMPLE), "guide": GUIDE, "evidence": EVIDENCE_LINE,
        "countNote": COUNT_CHECK_NOTE + " With a pitcher-hand tab, both sides face that hand.",
        "footer": (f"xChase+ 1.1 · Statcast {SEASON} · {len(players)} qualified hitters. "
                   "Every surface compares a hitter with the average hitter on pitches at the "
                   "same spot and count; “Same matchup” also matches batter side and "
                   "pitcher hand. Runs are per 600 plate appearances. Built by step 17 of the "
                   "Chase Leaderboard project."),
    }
    template = (TEMPLATE_DIR / "player_cards.html").read_text()
    math_js = (TEMPLATE_DIR / "card_surfaces.js").read_text()
    payload = json.dumps(to_json_safe(data), ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    page = (template.replace("/*__CARD_MATH__*/", math_js)
            .replace("/*__DATA__*/", payload)
            .replace("/*__BLOB__*/", blob))
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    (CARDS_DIR / "index.html").write_text(page)
    print(f"  wrote player_cards/index.html ({len(page) / 1e6:.1f} MB, "
          f"{len(qualified):,} pitches, {len(page_players)} hitters)")
    return qualified


def check_javascript(qualified):
    """Run the page's math in Node on one hitter and compare with Python."""

    node = shutil.which("node")
    if node is None:
        print("  node not found; skipped the JavaScript check")
        return
    hitter = next(p for p in players if p["name"] == README_EXAMPLE)
    frame = qualified[(qualified["batter"] == hitter["id"]) & (qualified["count_group"] == "two")]
    inputs = {"x": (frame["xq"] / 100).tolist(), "z": (frame["zq"] / 100).tolist(),
              "y": frame["is_chase"].astype(float).tolist(),
              "e": (frame["e_match_q"] / 255).tolist(), "xs": XS.tolist(), "zs": ZS.tolist()}
    script = (
        "const M = require(process.argv[1]); const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "const s = M.surface(d.x, d.z, d.y, d.e, d.xs, d.zs);"
        "process.stdout.write(JSON.stringify({gap: Array.from(s.gap), evidence: Array.from(s.evidence)}));"
    )
    run = subprocess.run([node, "-e", script, str(TEMPLATE_DIR / "card_surfaces.js")],
                         input=json.dumps(inputs), capture_output=True, text=True, check=True)
    js = json.loads(run.stdout)
    py = cs.surface(inputs["x"], inputs["z"], inputs["y"], inputs["e"], XS, ZS)
    worst = max(np.abs(np.array(js["gap"]).reshape(py["gap"].shape) - py["gap"]).max(),
                np.abs(np.array(js["evidence"]).reshape(py["evidence"].shape) - py["evidence"]).max())
    if worst > 1e-9:
        raise SystemExit(f"JavaScript and Python surfaces disagree by {worst:.2e}")
    print(f"  JavaScript matches Python on {README_EXAMPLE}'s two-strike surface "
          f"(largest difference {worst:.1e})")


# --------------------------------------------------
# THE NOTED-PLAYERS REPORT
# --------------------------------------------------

def picture(rel_light, rel_dark, alt, width=900):
    return (f'<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="{rel_dark}">\n'
            f'  <img alt="{alt}" src="{rel_light}" width="{width}">\n</picture>')


STATUS_WORDS = {"struggling": "struggling", "average": "about average",
                "productive": "hitting well"}


def count_check_line(p):
    """One sentence per count group the hitter's leaks are in."""

    parts, seen = [], []
    for lk in p["leaks"]["all"]:
        g = lk["count_group"]
        if g in seen:
            continue
        seen.append(g)
        parts.append(
            f"{COUNT_LABELS[g]}: {xw(lk['count_xwoba'])} xwOBA once there, league "
            f"{xw(lk['count_xwoba_league'])}; allowing for noise, "
            f"{STATUS_WORDS[lk['count_status']]} ({xw(lk['count_xwoba_shrunk'])}).")
    return " ".join(parts)


def write_noted_report():
    by_name = {p["name"]: p for p in players}
    lines = [
        f"# Noted hitters, {SEASON}",
        "",
        "Decision cards for the 17 hitters named in the two coaching reports:",
        "the nine whose chase losses look easiest to fix",
        "([actionable_hitters_2026.md](../coaching/actionable_hitters_2026.md)) and the",
        "bottom 10 by xChase+",
        "([bottom10_2026_coaching_notes.md](../coaching/bottom10_2026_coaching_notes.md)).",
        "Every other qualified hitter has the same card in the interactive page,",
        "`results/xchase/player_cards/index.html` (download it and open it in a browser).",
        "",
        "Each card is drawn from the catcher's view, to scale, around the hitter's own",
        "strike zone; nobody is mirrored, so a left-handed batter's inside is on the right.",
        "It compares the hitter with the average hitter on pitches at the same spot",
        "relative to their zone, in the same count and the same batter-side and",
        "pitcher-hand matchup.",
        "Red is where they swing more, blue where they take more, and faded color",
        "means too few pitches to say. The plan is written to the player; the coach's",
        "note underneath is for the staff. For what a normal card looks like, compare",
        "with the average hitter:",
        "",
        picture("../player_cards/reference/average_rhb_light.png",
                "../player_cards/reference/average_rhb_dark.png",
                "The average right-handed hitter's chase rate by location and count, with a guide to reading the cards"),
        "",
        f"**{EVIDENCE_QUESTION}** " + EVIDENCE_LINE.replace(EVIDENCE_QUESTION + " ", ""),
        "(Step 16; see the main README for the method.)",
        "",
        "**The count check.** Under each plan, how the hitter does once the count",
        "reaches the counts his leaks are in: the xwOBA of every plate appearance",
        "that got there, against the league's in the same counts (step 15). The",
        "verdict uses an estimate shrunk for noise, so a small sample or a split that",
        "doesn't repeat from year to year (being ahead in the count) can't swing it.",
        "It is context, not a filter: step 16 found that hitters gained about as much",
        "from fixing a leak whether they were hitting well in those counts or not.",
        "",
    ]
    sections = [("easiest", "Easiest to improve",
                 "Their chases turn out about as well as an average hitter's or better, and the "
                 "pattern repeats across seasons, so a take rule is the whole adjustment."),
                ("biggest", "Biggest losses",
                 "The rest of the bottom 10 by xChase+. Larger losses, but spread wider, and for "
                 "two of them the problem is contact as much as choice.")]
    for key, title, blurb in sections:
        lines += [f"## {title}", "", blurb, ""]
        group = sorted((p for p in players if p["noted"] == key), key=lambda p: -p["runs_at_stake"])
        for p in group:
            sl = slug(p["name"])
            lines += [
                f"### {p['name']}",
                "",
                f"xChase+ {p['xchase_plus']:.0f} ({p['rank']} of {p['of']}). "
                f"Runs at stake on far-off pitches: {p['runs_at_stake']:.1f} per 600 PA. "
                f"Choices {fmt_runs(p['choices'])}, contact {fmt_runs(p['contact'])}.",
                "",
                picture(f"cards/{sl}_light.png", f"cards/{sl}_dark.png",
                        f"{p['name']} decision card"),
                "",
                "**What to work on**",
                "",
            ]
            lines += [f"- {line}" for line in p["plan"]]
            check = count_check_line(p)
            if check:
                lines += ["", f"**Count check.** {check}"]
            lines += ["", f"**Coach's note.** {p['coach_note']}", ""]
    (NOTED_DIR / "README.md").write_text("\n".join(lines))
    print(f"  wrote noted_players/README.md ({sum(1 for p in players if p['noted'])} hitters)")


# --------------------------------------------------
# WRITE EVERYTHING
# --------------------------------------------------

print("Writing outputs...")
keep = ["batter", "stand", "p_throws", "count_group", "pitch_group", "region", "far_off",
        "xq", "zq", "zq_avg", "is_chase", "whiff", "e_all_q", "e_match_q", "w_all_q", "w_match_q"]
df[keep].to_parquet(CLEAN / f"card_pitches_{SEASON}.parquet", index=False)
(CLEAN / f"card_players_{SEASON}.json").write_text(json.dumps(to_json_safe({
    "season": SEASON, "zone_height": ZONE_HEIGHT, "average_zone": AVERAGE_ZONE,
    "players": [{k: p[k] for k in ("id", "name", "bats", "rank", "of", "pa", "xchase_plus",
                                   "archetype", "noted", "runs_at_stake", "choices", "contact",
                                   "zone", "height_in", "side_pitches", "leaks")}
                for p in players]}), ensure_ascii=False))
print(f"  saved card_pitches_{SEASON}.parquet and card_players_{SEASON}.json for step 18")
qualified_pitches = build_page()
check_javascript(qualified_pitches)

summary_rows = []
for p in players:
    t = {r["group"]: r for r in p["tables"]["all"]}
    top = p["leaks"]["all"][0] if p["leaks"]["all"] else None
    summary_rows.append({
        "player": p["name"], "batter": p["id"], "bats": p["bats"], "xchase_plus_rank": p["rank"],
        "xchase_plus": round(p["xchase_plus"], 1), "plate_appearances": p["pa"],
        "archetype": p["archetype"], "noted": p["noted"] or "",
        "chase_rate": round(p["chase"], 4), "league_chase_rate_same_pitches": round(p["chase_league"], 4),
        "whiff_per_chase": round(p["whiff"], 4), "league_whiff_per_chase_same_pitches": round(p["whiff_league"], 4),
        "choices_runs_per_600": round(p["choices"], 2), "contact_runs_per_600": round(p["contact"], 2),
        "runs_at_stake_far_off": round(p["runs_at_stake"], 2),
        "two_strike_chase_rate": round(t["two"]["chase"], 4),
        "league_two_strike_chase_rate_same_pitches": round(t["two"]["chase_league"], 4),
        "top_leak": (f"{COUNT_LABELS[top['count_group']]} / {top['pitch_group']} / {top['region']}"
                     if top else ""),
        "top_leak_runs": round(top["choices"], 2) if top else None,
        "top_leak_count_xwoba": round(top["count_xwoba"], 4) if top else None,
        "top_leak_count_league_xwoba": round(top["count_xwoba_league"], 4) if top else None,
        "top_leak_count_xwoba_shrunk": round(top["count_xwoba_shrunk"], 4) if top else None,
        "top_leak_count_status": top["count_status"] if top else "",
        "plan": " ".join(p["plan"]),
    })
pd.DataFrame(summary_rows).to_csv(CARDS_DIR / f"player_cards_{SEASON}.csv", index=False)
print(f"  wrote player_cards/player_cards_{SEASON}.csv")

if not args.skip_png:
    by_name = {p["name"]: p for p in players}
    for stand, word in (("R", "rhb"), ("L", "lhb")):
        for theme in THEMES:
            league_card(stand, theme, CARDS_DIR / "reference" / f"average_{word}_{theme}.png")
    noted = [p for p in players if p["noted"]]
    for p in noted:
        for theme in THEMES:
            player_card(p, theme, NOTED_DIR / "cards" / f"{slug(p['name'])}_{theme}.png")
    print(f"  drew {len(noted)} noted cards and 2 reference cards, light and dark")
    extra = players if args.static_all else [by_name[n] for n in args.static if n in by_name]
    unknown = [n for n in args.static if n not in by_name]
    if unknown:
        print(f"  not found, skipped: {unknown}")
    for p in extra:
        for theme in THEMES:
            player_card(p, theme, CARDS_DIR / "static" / f"{slug(p['name'])}_{theme}.png")
    if extra:
        print(f"  drew {len(extra)} more cards into player_cards/static/")
    write_noted_report()
