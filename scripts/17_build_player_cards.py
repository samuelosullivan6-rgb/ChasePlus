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
  - a short plan in plain language, written to the player: one pitch per
    line from the leaks, numbered 1 and 2 in the order to work on them
    and tagged with the leak's number (a pitch chased well above the
    league's rate before one chased at about it; a take before two
    strikes first when it rests on 20 or more pitches, since it costs
    nothing in strikeouts; the rest by runs; a pitch the hitter chases at
    the league's rate explains why it is there, and a first line in a
    count where his choices are a plus says why; a borderline pitch is a
    video item, not a take), a line naming a bigger leak or a costly
    count the plan leaves for later and why, then a line that says to
    keep swinging at strikes, and calls the plan's pitches the only
    changes only when nothing is left. The first printed line is the first
    thing to do: when no single pitch explains the loss, or the hitter's
    choices are average or better, a line after the pitch lines says so,
    and a hitter whose problem is contact reads the reason in his first
    take line. Every sentence is written from the count table next to
    it, so a plan is empty only when that table agrees, and
    plan_checks.py stops the build when a sentence contradicts the lines
    or numbers beside it. For the 17 noted hitters the coach's note
    names the leak the plan must lead with, so the player and the staff
    start in the same place. The card has one plan: the vs RHP and vs LHP
    tabs show it unchanged, with each pitch line's pitches from that hand
    under it, and switch only the leaks and the count table to that hand
    (a tab that rebuilt its own plan from one hand's pitches could give
    the opposite instruction on the same pitch). At the foot of the card,
    what step 16 found when hitters fixed their leaks, in one plain
    sentence.

The leak rule, the labels and the choices / contact split come from
leak_rules.py, which steps 15 and 16 share. The coach's notes for the 17
noted hitters are in coach_notes.py, each next to the facts it states;
every fact is checked against the data before a card is drawn, and the
run stops if one no longer holds.

Hitters whose problem is contact rather than choices also get a whiff
picture: how often they miss when they do chase, against the league on
the same pitches. That is decided on the card's own numbers (contact_led:
chases that lost CONTACT_LED_RUNS or more on what they produced, more than
the choices lost and more than the far-off tile), not on step 13's
archetype, which exists only for a net loss and so split hitters at a net
of zero (+8.8 / -9.1 heard about contact, +9.0 / -8.7 never did). The
roster's Problem column still shows step 13's archetype.

TEAM
  Statcast's pitch file has no batter team, only the home and away
  teams of each game (in the raw files from step 01). A hitter's team
  on a pitch is the home team when he bats in the bottom of the inning
  and the away team otherwise. His team for the season is the one he
  had the most plate appearances for; a traded hitter lists every team,
  most plate appearances first, and appears under each of them in the
  page's team filter.

OUTPUTS
  results/xchase/player_cards/<season>/index.html
      every qualified hitter plus the average right- and left-handed
      hitter, interactive, in two views. Card: one hitter's pictures,
      leaks, plan and tables (#<hitter>). Roster: every hitter on one
      page, by team, sorted by the runs at stake, with the top leak,
      the count check, the number to beat and the plan's first pitch
      line, each name opening the card (#roster, or #roster/NYY for one
      team). One page per season; the season switcher on the page moves
      between them with the view, the hitter or the team kept in the URL.
  results/xchase/player_cards/<season>/pitches.bin
      the season's pitches, one 9-byte record each, which the page
      fetches when it first shows a card, so the roster opens without
      them. Kept out of the HTML so that a change to the wording
      re-commits the page (about 2.5 MB) and not the pitches. Browsers
      will not load it from a file:// address: open the page from the
      hosted site or a local web server (python -m http.server from the
      project folder).
  results/xchase/player_cards/<season>/reference/*.png
      the average right- and left-handed hitter, for comparison
  results/xchase/player_cards/index.html, teams.html and seasons.js,
  results/xchase/player_cards/<season>/teams.html
      the old addresses, sent on to the page (index.html to the newest
      season with the hitter kept; teams.html, the roster's old page,
      into the roster view with its ?team= kept), and the list of
      seasons with a page (card_site.py)
  results/xchase/noted_players/
      README.md, a card and a short write-up for the 17 hitters named in
      the step 12 and 13 reports, and cards/*.png (light and dark); for
      2026 only, the season the coach's notes describe
  results/xchase/player_cards/player_cards_<season>.csv
      one row per hitter: the team and the numbers behind the header
      and plan
  results/xchase/player_cards/team_view_<season>.csv
      the roster's columns, one row per hitter, sorted by runs at stake

Each leak also says how far off the zone the chased pitches were (the
median, in inches), so "let it go" is never read as "take borderline
pitches". When step 19 has frozen this season's predictions, each card
carries its target: how far above the league's chase rate, in points,
the hitter chased in all his leaks together, and what the line expects
next season with no change, since leaks shrink on their own. Beating
that number is what counts as a fix. An earlier season's target was set
afterward (step 22 freezes it retrospectively), so its card says so and
shows how the next season came out (step 20's leak_scores file); a card
whose leaks are all video items prints no number.

The 17 noted hitters also get a printable card: the web card on a
two-page letter-size PDF in noted_players/print/, for the player and the
staff together. Page 1 has the plan, the target and the coach's note,
the pictures the leaks are numbered on, the key and the leaks. Its
picture rows are the web card's that carry a leak, so every number sits
where the web puts it: a leak named for a pitcher hand on that hand's
row, a switch hitter's leaks on the side they came from (both sides
drawn and named), the misses row for a hitter whose problem is contact,
and the all-pitchers row for the rest. The pictures take the room the
text leaves (a plan long enough to squeeze them is set a size smaller),
and the build stops if a page would run into its footer.
Page 2 has a guide to the card in the player's own words, the average
hitter's two-strike picture, the season chart and what fixing a leak
paid. --print NAME [NAME ...] draws the same for any hitter into
player_cards/<season>/print/ (not committed).

Options: --season (default 2026), --static NAME [NAME ...] to also draw
PNG cards for any hitters by name, --static-all to draw every hitter
(into player_cards/<season>/static/, which is not committed), --print NAME
[NAME ...] for printable PDFs, --data-only to
write just the card data (card_players_<season>.json, the CSV) for an
earlier season, so step 19 can freeze it retrospectively and step 20
score it. The coach's notes are for 2026 only.

Needs steps 04 (--expected-contact), 13, 15 and 16 first, and the raw
Statcast files from step 01 for the teams. Step 22 runs this step for
every season, so the pages agree.
"""

import argparse
import base64
import json
import math
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter
from scipy.interpolate import RegularGridInterpolator
from scipy.optimize import brentq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import card_surfaces as cs  # noqa: E402
import leak_rules as lr  # noqa: E402
from coach_notes import NOTED  # noqa: E402
import coach_notes  # noqa: E402
import plan_checks  # noqa: E402
import card_site  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW = PROJECT_DIR / "data" / "raw"
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
parser.add_argument("--print", nargs="*", default=[], dest="print_names",
                    help="also write printable two-page PDFs for these hitters (by name)")
parser.add_argument("--skip-png", action="store_true",
                    help="build the data and the HTML page only")
parser.add_argument("--data-only", action="store_true",
                    help="write card_players_<season>.json and the CSV only: no page, no PNGs, "
                         "no noted report (for freezing an earlier season retrospectively)")
args = parser.parse_args()
SEASON = args.season
SEASON_DIR = CARDS_DIR / str(SEASON)    # this season's page, pitches and reference cards
NOTED_SEASON = 2026             # the coach's notes describe the 2026 cards
NOTES = NOTED if SEASON == NOTED_SEASON else {}
NO_NOTE = (None, None, None)

PA_SCALE = 600
FAR_OFF_FT = 0.35
SWITCH_SHARE = 0.15             # bats from each side on 15%+ of pitches
ABS_TOP_SHARE = 0.535           # 2026 zone top = 53.5% of the batter's height
ABS_FIRST_SEASON = 2026         # Statcast's zone is the ABS box from here on
# Every rate on a card is measured against Statcast's recorded zone. From
# 2026 that is the ABS box set from the hitter's height, 2.86 inches
# shorter on average than the same hitters' 2025 stance zones, so a trend
# that reaches 2026 and a 2026 target say so.
ABS_TREND_NOTE = (f"From {ABS_FIRST_SEASON} Statcast measures the zone as the ABS box set from the "
                  "hitter's height, about 3 inches shorter than the zones before, so the "
                  f"{ABS_FIRST_SEASON} point is not on the same box as the earlier ones.")
ABS_TARGET_NOTE = ("These rates are measured against the ABS box set from your height, not the "
                   "zone of the seasons before.")
TREND_MIN_FAR_PITCHES = 150

COUNT_GROUPS = ["first", "ahead", "even", "two"]
COUNT_LABELS = {
    "first": "First pitch",
    "ahead": "Ahead in the count",
    "even": "0-1 or 1-1",
    "two": "Two strikes",
}
COUNT_SHORT = {"first": "First pitch", "ahead": "Ahead", "even": "0-1 or 1-1", "two": "Two strikes"}
COUNT_DETAIL = {
    "first": "0-0",
    "ahead": "1-0  2-0  3-0  2-1  3-1",
    "even": "even or behind",
    "two": "0-2  1-2  2-2  3-2",
}
HANDS = ["all", "R", "L"]
PITCH_GROUPS = ["fastball", "breaking", "offspeed"]

# The 17 noted hitters and their coach's notes live in coach_notes.py,
# next to the claims step 17 checks before drawing their cards.
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

missing = [n for n in NOTES if n not in set(board["player"])]
if missing:
    raise SystemExit(f"Noted hitters not on the {SEASON} leaderboard: {missing}")

sides = df.groupby(["batter", "stand"]).size().unstack(fill_value=0)
sides["share_min"] = sides.min(axis=1) / sides.sum(axis=1)
switch = set(sides.index[sides["share_min"] >= SWITCH_SHARE])
main_side = sides[["L", "R"]].idxmax(axis=1)

# Each hitter's teams, from the raw files: the home team when he bats in
# the bottom of the inning, else the away team, most plate appearances first.
raw_files = sorted(RAW.glob(f"statcast_{SEASON}-*.parquet"))
if not raw_files:
    raise SystemExit(f"No raw Statcast files for {SEASON} in data/raw/ (run step 01); "
                     "the cards need them for each hitter's team.")
raw = pd.concat([pd.read_parquet(f, columns=["batter", "game_pk", "at_bat_number", "home_team",
                                             "away_team", "inning_topbot"]) for f in raw_files],
                ignore_index=True)
raw = raw[raw["batter"].isin(board["batter"])].drop_duplicates(["game_pk", "at_bat_number", "batter"])
raw["team"] = raw["home_team"].where(raw["inning_topbot"] == "Bot", raw["away_team"])
by_team = raw.groupby(["batter", "team"]).size().rename("pa").reset_index()
by_team = by_team.sort_values(["batter", "pa"], ascending=[True, False])
TEAMS = by_team.groupby("batter")["team"].agg(list)
no_team = [n for b, n in zip(board["batter"], board["player"]) if b not in TEAMS.index]
if no_team:
    raise SystemExit(f"No team in the raw files for {len(no_team)} hitters on the {SEASON} "
                     f"leaderboard: {no_team[:5]}")
print(f"  teams from {len(raw_files)} raw files: {by_team['team'].nunique()} teams, "
      f"{int((TEAMS.str.len() > 1).sum())} hitters with more than one")

league_chase = df["is_chase"].mean()
league_whiff = df.loc[df["is_chase"] == 1, "whiff"].mean()
league_far = df.loc[df["far_off"], "is_chase"].mean()

# One vocabulary for a leak, in the list, the plan, the roster and the
# report: the count group by its column name, the pitcher hand when the
# leak is one hand's, the pitch group, the side of the zone.
GROUP_WORDS = {
    "first": "On the first pitch",
    "ahead": "When you're ahead in the count",
    "even": "At 0-1 or 1-1",
    "two": "With two strikes",
}
PITCH_WORDS = {"fastball": "fastballs", "breaking": "breaking balls",
               "offspeed": "changeups and splitters"}
REGION_WORDS = {
    "up": "above the zone", "down": "below the zone", "in": "off the plate inside",
    "away": "off the plate away", "up-in": "up and in", "up-away": "up and away",
    "down-in": "down and in", "down-away": "down and away",
}
LEAK_PITCH = {"fastball": "fastballs", "breaking": "breaking balls", "offspeed": "changeups / splitters"}
LEAK_REGION = {"up": "above the zone", "down": "below the zone", "in": "inside", "away": "away",
               "up-in": "up and in", "up-away": "up and away", "down-in": "down and in",
               "down-away": "down and away"}
HAND_WORDS = {"R": " against right-handers", "L": " against left-handers", None: ""}
HAND_SHORT = {"R": " vs RHP", "L": " vs LHP", None: ""}
HAND_RHP_SHARE, HAND_LHP_SHARE = 0.8, 0.45   # a leak is one hand's when that hand threw this share
HAND_CARRY_SHARE = 0.5          # ...and carries more than this share of its extra chases and cost


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
            "chases": int(len(ch)),     # so the page can say a miss rate rests on a few chases
            "whiff": ch["whiff"].mean() if len(ch) else None,
            "whiff_league": ch["w_match"].mean() if len(ch) else None,
            "choices": s["choices"].sum() * scale,
            "contact": s["contact"].sum() * scale,
            "xwoba": cc.xwoba if cc is not None else None,
            "xwoba_league": cc.league_xwoba if cc is not None else None,
            # the shrunk verdict exists for all pitchers only
            "status": (cc.status if cc is not None and isinstance(cc.status, str) else None),
        })
    return rows


def leaks(p, scale, batter):
    """The card's leaks from these pitches (all pitchers, or one hand's
    for a tab's list). A leak is named for a pitcher hand when that hand
    threw most of its pitches and also carries most of its extra chases
    and of what they cost: Grissom's two-strike breaking balls, 2026, came
    56% from left-handers, but right-handers carried three quarters of the
    cost, so naming left-handers sent him to the wrong matchup. A switch
    hitter's leak is drawn on the side where its extra chases came from,
    not the side he chased on most."""

    out = []
    cells = lr.leak_cells(p, scale, "e_match").head(lr.LEAK_TOP)
    for lk in cells.itertuples():
        s = p[(p["count_group"] == lk.count_group) & (p["pitch_group"] == lk.pitch_group)
              & (p["region"] == lk.region)]
        s = s.assign(_x=s["is_chase"] - s["e_match"])
        rhp = (s["p_throws"] == "R").mean()
        extra_rhp = float(s.loc[s["p_throws"] == "R", "_x"].sum() / s["_x"].sum())
        cost_rhp = float(s.loc[s["p_throws"] == "R", "choices"].sum() / s["choices"].sum())
        hand = ("R" if rhp >= HAND_RHP_SHARE and min(extra_rhp, cost_rhp) > HAND_CARRY_SHARE else
                "L" if rhp <= HAND_LHP_SHARE and max(extra_rhp, cost_rhp) < 1 - HAND_CARRY_SHARE else
                None)
        chased = s[s["is_chase"] == 1]
        side_extra = {k: float(v) for k, v in s.groupby("stand")["_x"].sum().items()}
        side = (max(side_extra, key=side_extra.get) if batter in switch
                else chased["stand"].mode().iloc[0])
        on_side = chased[chased["stand"] == side]
        # Is the hitter struggling once the count gets there? All pitchers,
        # whatever the hand of the leak list.
        cc = COUNTS[(batter, "all", lk.count_group)]
        # The counts inside the cell that carry the extra swings, so a plan
        # line can say why a cell at the league's rate is on the card.
        by_count = s.assign(_x=s["is_chase"] - s["e_match"]).groupby("count_state")["_x"].sum()
        by_count = by_count[by_count > 0].sort_values(ascending=False)
        top = by_count.iloc[:2]
        excess_counts = list(top.index) if len(top) and top.sum() >= 0.5 * max(lk.extra_chases, 1e-9) else []
        out.append({
            "count_group": lk.count_group, "pitch_group": lk.pitch_group, "region": lk.region,
            "pitches": int(lk.pitches), "chases": int(lk.chases),
            "rate": lk.rate, "league": lk.league,
            "extra_chases": float(lk.extra_chases), "choices": lk.choices, "contact": lk.contact,
            "share_rhp": float(rhp), "hand": hand, "excess_counts": excess_counts,
            # the right-handers' share of the extra chases and of the cost, for the hand label
            "extra_rhp": extra_rhp, "cost_rhp": cost_rhp,
            "side": side, "side_extra": side_extra,
            "x": float(on_side["xd"].median()), "z": float(on_side["zd"].median()),
            # how far off the zone the chased pitches were, so the plan can say it
            "depth_in": float(chased["distance_outside_zone"].median() * 12),
            "count_xwoba": cc.xwoba, "count_xwoba_league": cc.league_xwoba,
            "count_xwoba_shrunk": cc.xwoba_shrunk, "count_status": cc.status,
        })
    return out


def hand_share(lk):
    """The share of the leak's pitches thrown by the hand it is named for."""

    return lk["share_rhp"] if lk["hand"] == "R" else 1 - lk["share_rhp"]


def hand_phrase(lk):
    """The pitcher hand in a plan line. A leak is named for a hand when 80%
    or more of its pitches came from it (55% for left-handers) and that hand
    carries most of its extra chases and cost (leaks), and its rates count
    every pitch, so it says "mostly" unless that hand threw them all."""

    if not lk["hand"]:
        return ""
    return HAND_WORDS[lk["hand"]] if hand_share(lk) >= 1 else "," + " mostly" + HAND_WORDS[lk["hand"]]


def leak_cell(lk):
    return (lk["count_group"], lk["pitch_group"], lk["region"])


def leak_phrase(lk, short=False):
    """The leak's name, used verbatim in the list, the roster and the
    report: "Two strikes, mostly vs RHP, breaking balls away" ("vs RHP"
    alone when that hand threw every pitch, as on a pitcher-hand tab)."""

    group = (COUNT_SHORT if short else COUNT_LABELS)[lk["count_group"]]
    hand = HAND_SHORT[lk["hand"]]
    if lk["hand"] and hand_share(lk) < 1:
        hand = ", mostly" + hand
    return f"{group}{hand}, {LEAK_PITCH[lk['pitch_group']]} {LEAK_REGION[lk['region']]}"


GROUP_WORDS_SHORT = {"first": "On the first pitch", "ahead": "When you're ahead",
                     "even": "At 0-1 or 1-1", "two": "With two strikes"}


CLEARLY_OFF_IN = 4              # a take rule needs the chased pitches typically this far
                                # off: the card's own far-off line (0.35 ft). Under it, a
                                # leak is a video item, since a ball off the edge is a
                                # called strike often enough with two strikes.


# The plan: the pitch lines come from the leaks, in the order to work on
# them, not the order of their runs: a take the hitter chases well above
# the league's rate ahead of one he chases at about the league's rate, a
# take before two strikes first (it costs nothing in strikeouts and the
# league rate there is low) when it rests on enough pitches to repeat,
# everything else by its runs, and a borderline pitch (a video item, not
# a take) never ahead of a take. For a noted hitter the coach's note names
# the leak to lead with. A pitch line quotes the hitter's chase rate
# against the league's only when the two print well apart; otherwise it
# says which counts the extra swings came in and what they cost. A line in
# a count the table shows as a plus says why it is there anyway, and one in
# a count whose choices print a loss (any loss, not only a costly count)
# but whose chases pay for themselves says so, and what this pitch gets
# back of what it costs. After the pitch lines: a line naming a
# bigger leak the order left for later, or a costly count no line or
# sentence covers; a framing line when the loss is spread thin or the
# hitter's choices are average or better; and a closing line that says to
# keep swinging at strikes. A hitter whose problem is contact reads why in
# his first take line, or as the plan's one line when it has no take.
# "Nothing stands out" is said only when the count table agrees.
PLAN_LINES = 2                  # pitch lines in a plan
PLAN_LEAD_MIN_PITCHES = 20      # a take before two strikes goes first only on this many
                                # pitches: in step 16's backtest, leaks on fewer kept 15%
                                # of their excess the next period, on 20 to 25 about half
NEXT_MIN_RATIO = 1.25           # a leak left off the plan is named when it costs this many
                                # times a plan line, on PLAN_LEAD_MIN_PITCHES or more
RATE_GAP_MIN_PTS = 5            # a pitch line quotes the two chase rates only
                                # when they print this many points apart
WHIFF_GAP_MIN_PTS = 5           # the contact line quotes the miss rate only when it
                                # is this far above the league's
COSTLY_COUNT_RUNS = 1.0         # a count group costing this much is named
CONTACT_LED_RUNS = 3.0          # contact is the card's subject from this loss up
SPREAD_MIN_RUNS = 3.0           # a choices loss this big...
SPREAD_SHARE = 0.25             # ...that the plan's pitches cover less than a
                                # quarter of gets the framing line first

COUNT_PHRASES = {"first": "on the first pitch", "ahead": "when you're ahead in the count",
                 "even": "at 0-1 or 1-1", "two": "with two strikes"}


def join_words(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def fmt_runs(v):
    v = page_runs(v)
    if v == 0:
        return "0.0"
    return ("+" if v > 0 else "−") + f"{abs(v):.1f}"


def stored(v):
    """A value as the page stores it (to_json_safe keeps four decimals). A
    sentence that depends on how a run value prints decides on this, so a
    value a hair under a half cannot print as +0.1 in the page's table
    beside a line that treated it as 0.0."""

    return round(float(v), 4)


# Every number a sentence quotes is rounded the way the page rounds the
# same number in its rows and tables: JavaScript's Math.round (half up) on
# the stored value. Python's round goes half to even, so a leak at exactly
# 30 of 48 chases once printed 62% in the plan and 63% in the leak row.
def page_whole(v, scale=1):
    return math.floor(stored(v) * scale + 0.5)


def page_pct(v):
    return page_whole(v, 100)


def page_runs(v):
    """A run value as the page's runs() prints it, to one decimal."""

    return page_whole(v, 10) / 10


def whole_runs(runs):
    """A run amount as a whole number, from its one-decimal print."""

    return math.floor(abs(page_runs(runs)) + 0.5)


def runs_phrase(runs):
    n = whole_runs(runs)
    return f"{n} run" + ("" if n == 1 else "s")


def chases_more(row):
    return row["chase"] is not None and row["chase"] >= row["chase_league"] + 0.01


def rate_gap(lk):
    """The gap as it prints, so the line never shows the same rounded rate
    for the hitter and the league."""

    return page_pct(lk["rate"]) - page_pct(lk["league"])


def rate_clause(lk):
    """Why this pitch is on the plan. The leak rule asks for more chases
    than the league expects in sum, so a costly cell can sit a point or two
    above the league rate when the extra swings come on its costlier
    pitches; there the line says which counts they came in and what they
    cost, instead of two near-identical percentages."""

    if rate_gap(lk) >= RATE_GAP_MIN_PTS:
        return (f"You swung at {page_pct(lk['rate'])}% of them; hitters on average swing at "
                f"{page_pct(lk['league'])}%.")
    where = (f" at {join_words(lk['excess_counts'])}" if lk["excess_counts"]
             else " on the costlier pitches")
    return (f"You swung at these about as often as other hitters do, but more of yours "
            f"came{where}, and over a season they cost you {abs(page_runs(lk['choices'])):.1f} runs.")


def is_video(lk):
    return lk["depth_in"] < CLEARLY_OFF_IN


VIDEO_DEPTH = f"typically under {CLEARLY_OFF_IN} inches off the zone"


def small_sample(lk):
    """A leak on fewer pitches than step 16's backtest trusts to repeat."""

    return lk["pitches"] < PLAN_LEAD_MIN_PITCHES


def pitch_line(lk):
    """One pitch, written to the player. A video item says why in the
    card's own unit, the 4 inches that make a take rule; a take on fewer
    than PLAN_LEAD_MIN_PITCHES pitches says it is a small sample."""

    hand = hand_phrase(lk)
    opener = (GROUP_WORDS_SHORT if hand else GROUP_WORDS)[lk["count_group"]]
    what = f"{PITCH_WORDS[lk['pitch_group']]} {REGION_WORDS[lk['region']]}"
    if is_video(lk):
        return (f"{opener}{hand}, {what} are one to go over on video with your coaches, not a "
                f"take rule. {rate_clause(lk)} The ones you swung at were {VIDEO_DEPTH}, too "
                "close for a take rule.")
    line = (f"{opener}{hand}, let {what} go. {rate_clause(lk)} The ones you swung at were "
            f"typically {page_whole(lk['depth_in'])} inches off the zone.")
    if small_sample(lk):
        line += (f" Only {lk['pitches']} of these pitches so far, a small sample: go over them on "
                 "video with your coaches before you make it a rule.")
    return line


def at_league_rate(lk):
    return rate_gap(lk) < RATE_GAP_MIN_PTS


def early_take(lk):
    """A take before two strikes on enough pitches to lead the plan."""

    return lk["count_group"] != "two" and lk["pitches"] >= PLAN_LEAD_MIN_PITCHES


def plan_order(lk):
    """The sort key of the order to work on the leaks: takes before video
    items, a real gap before the league's rate, a well-sampled take before
    two strikes, then the runs."""

    return (is_video(lk), at_league_rate(lk), not early_take(lk), lk["choices"])


def plan_pitch_items(leak_list, start=None):
    """Which leaks make the plan, in the order to work on them. The order
    also chooses: a take before two strikes can put a smaller leak on the
    plan ahead of a bigger two-strike one, and a real gap a smaller leak
    ahead of a bigger one at the league's rate. The note's lead stays first
    among the takes."""

    items = list(enumerate(leak_list, start=1))
    lead = [it for it in items if start and leak_cell(it[1]) == tuple(start)]
    rest = sorted((it for it in items if it not in lead), key=lambda it: plan_order(it[1]))
    ordered = sorted(lead + rest, key=lambda it: is_video(it[1]))
    return ordered[:PLAN_LINES]


def pays_back(rows, costly):
    """In every costly count, the hitter's chases produced at least what
    his choices there cost."""

    return bool(costly) and all(stored(rows[g]["contact"]) >= -stored(rows[g]["choices"])
                                for g in costly)


def count_pays(row):
    """In this count group what the hitter hit on his chases produced at
    least what his choices there cost, as the page stores both."""

    return row["contact"] > 0 and stored(row["contact"]) >= -stored(row["choices"])


def productive_line(rows, costly):
    """The costly counts are counts where the hitter's chases have produced
    more than his choices cost (the leak rule never names such a pitch).
    It quotes what the chases in those counts produced, not the season's."""

    cost = sum(-rows[g]["choices"] for g in costly)
    paid = sum(rows[g]["contact"] for g in costly)
    where = join_words([COUNT_PHRASES[g] for g in costly])
    if all(chases_more(rows[g]) for g in costly):
        what = f"You chase more than most hitters {where}"
        if len(costly) == 1:
            r = rows[costly[0]]
            what += f" ({page_pct(r['chase'])}% against {page_pct(r['chase_league'])}%)"
    else:
        what = f"Your chase choices cost {runs_phrase(cost)} a season {where}"
    return (f"Nothing to change. {what}, but those swings have paid: {runs_phrase(paid)} more "
            "than an average hitter's chases there, more than the extra swings cost.")


def spread_line(rows, loss, contact, costly, n_pitches, biggest=False):
    """No one pitch explains the loss: say so without denying the pitch
    lines above it, and call them the biggest pieces only when they are
    (the order to work on them can put a smaller leak on the plan). The
    rates in each count are in the table beside the plan, so the line does
    not repeat them. A hitter whose chases produce more than his choices
    cost, with no pitch worth a take rule, is told so instead."""

    if n_pitches == 0 and contact > 0 and contact >= loss and pays_back(rows, costly):
        return productive_line(rows, costly)
    # the counts that cost a run or more, as the table prints them; a count
    # at a fraction of a run is not where the loss is
    neg = [g for g in COUNT_GROUPS if page_runs(rows[g]["choices"]) <= -COSTLY_COUNT_RUNS]
    if len(neg) == 4:
        where = "across every count"
    elif not neg:
        where = "spread thin across the counts"
    else:
        where = "the most " + join_words([COUNT_PHRASES[g] for g in neg])
    cost = f"Your chase choices cost {runs_phrase(loss)} a season, {where}"
    if n_pitches > 1:
        return (f"{cost}; the two pitches above are its biggest single pieces, and the rest is spread "
                "thin." if biggest else
                f"{cost}; the two pitches above are two of the pieces, the ones to work on first.")
    if n_pitches == 1:
        return (f"{cost}; the pitch above is its biggest single piece, and the rest is spread thin."
                if biggest else
                f"{cost}; the pitch above is one of the pieces, the one to work on first.")
    worst = min(COUNT_GROUPS, key=lambda g: rows[g]["choices"])
    line = f"No single pitch here is a clear take. {cost}; the count table shows where."
    if rows[worst].get("status") != "productive":
        line += f" Start {COUNT_PHRASES[worst]}, where it costs the most."
    return line


def fallback_line(rows, costly):
    """What the plan says when no leak makes it."""

    choices, contact = rows["total"]["choices"], rows["total"]["contact"]
    c = page_runs(choices)
    if not costly:
        if c >= 1:
            return (f"Nothing stands out: your chase choices are better than average ({fmt_runs(c)} "
                    "runs a season), and no count costs you a full run.")
        return ("Nothing stands out. No count costs you a full run, and your chase choices are "
                + ("about league average or better." if c >= 0 else
                   f"about league average overall ({fmt_runs(c)} runs a season)."))
    cost = sum(-rows[g]["choices"] for g in costly)
    if contact > 0 and pays_back(rows, costly):
        return productive_line(rows, costly)
    where = join_words([COUNT_PHRASES[g] for g in costly])
    if c <= -COSTLY_COUNT_RUNS:
        return (f"No single pitch stands out. Your chase choices cost you {runs_phrase(-c)} a season, "
                f"spread across many pitches; the most, about {runs_phrase(cost)}, {where}.")
    level = "better than average" if c >= 1 else "about average"
    return (f"No single pitch stands out. Your chase choices are {level} overall "
            f"({fmt_runs(c)} runs a season); you give back about {runs_phrase(cost)} "
            f"a season {where}.")


def contact_why(summary):
    """Why contact is the issue, decided on the miss rates as they print:
    the miss rate when he misses more; otherwise what the chases produced,
    saying whether he misses about as often as other hitters or less."""

    mine, theirs = page_pct(summary["whiff"]), page_pct(summary["whiff_league"])
    cost = (f"over a season your chases cost you {runs_phrase(-summary['contact'])} more than an "
            "average hitter's would")
    if mine - theirs >= WHIFF_GAP_MIN_PTS:
        return (f"you miss on {mine}% of your chases, against {theirs}% for other hitters on the "
                "same pitches")
    if theirs - mine >= WHIFF_GAP_MIN_PTS:
        return (f"you miss less often than other hitters ({mine}% of your chases against {theirs}%), "
                f"but what you hit on a chase does little ({cost})")
    return f"you miss about as often as other hitters do, but what you hit on a chase goes nowhere ({cost})"


def contact_line(summary):
    """For a hitter whose loss is contact more than choices and whose plan
    has no take line: the plan's one line. With a take line the same
    reason is folded into it (contact_clause), so the card never gives a
    second first instruction."""

    head = ("Your issue is contact, not choices" if summary["choices"] >= 0
            else "Your bigger issue is contact")
    return (f"{head}: {contact_why(summary)}. So a pitch that is clearly off is a take even when "
            "you could reach it.")


def contact_clause(summary):
    why = contact_why(summary)
    return (f"{why[0].upper()}{why[1:]}: contact is your bigger cost, so this one is a take even "
            "when you could reach it.")


PLUS_COUNT_MIN_RUNS = 1.0       # a count at or over this is "a plus overall"; under it,
                                # "about even", the line framing_line draws for a hitter


def strength_clause(rows, lk):
    """A pitch line in a count where the count table shows the hitter's
    choices as a plus, or as 0.0, says why it is there, so the table does
    not argue with it: "a plus overall" from a run up, "about even" under
    that. A 0.0 needs it as much as a +0.4: Trevor Larnach's 2026
    two-strike choices print 0.0 beside a line to let fastballs above the
    zone go. The line has already named its count, so the clause says "in
    this count". None when the count's choices print as a loss
    (pays_clause speaks for those)."""

    v = page_runs(rows[lk["count_group"]]["choices"])
    if v < 0:
        return None
    level = "are a plus overall" if v >= PLUS_COUNT_MIN_RUNS else "come out about even"
    return (f"In this count your choices {level} ({fmt_runs(v)} runs in the count table); this "
            "pitch is where they give some back.")


def gets_back(lk):
    """What the hitter's contact on a leak's chases gets back of what his
    choices on it cost: in whole runs, the 4 of the leak row's −4.1; to one
    decimal, as the row prints it, when the two would print the same whole
    number or the contact rounds to none. The leak rule (leak_rules.py)
    never names a pitch whose contact covers its choices, so this is always
    less than all of it; a one-decimal tie says "nearly all". The cost is
    rounded from the signed value, as the row prints it."""

    cost, back = lk["choices"], lk["contact"]
    k, c = abs(page_runs(cost)), page_runs(back)
    if c < 0:
        more = f"about {whole_runs(back)}" if whole_runs(back) else "a little"
        return (f"it costs about {runs_phrase(cost)}, and what you hit on these chases loses "
                f"{more} more")
    if c == 0:
        return f"it costs about {runs_phrase(cost)}, and what you hit on these chases gets none of it back"
    if c >= k:
        return f"you get back nearly all of the {k:.1f} runs it costs, but not all"
    if whole_runs(back) and whole_runs(back) < whole_runs(cost):
        return f"you get back about {whole_runs(back)} of the {whole_runs(cost)} runs it costs"
    return f"you get back {c:.1f} of the {k:.1f} runs it costs"


def pays_clause(rows, lk, first):
    """A pitch line in a count whose choices print as a loss, where what
    the hitter hits on his chases pays for his choices there, says so,
    and that this pitch is the exception. Jake Mangum, 2026: with two
    strikes his choices cost −9.2 and his contact adds +11.3, so a staff
    that knows him as a two-strike contact hitter would object to "let
    fastballs above the zone go" with no word of it; on that pitch he
    gets back about 3 of the 4 runs. A count costing under a run needs it
    as much: J. T. Realmuto's two-strike choices print −0.8 against +5.1,
    and "come out about even" would leave the +5.1 unsaid. The advice
    stays on the one pitch, the count's runs are its context. The first
    line in the count quotes the count table; a second line in the same
    count says only its own runs. None when the count does not pay or its
    choices do not print as a loss (strength_clause speaks for a count
    the table shows as a plus or 0.0)."""

    row = rows[lk["count_group"]]
    if page_runs(row["choices"]) >= 0 or not count_pays(row):
        return None
    if not first:
        return f"This pitch doesn't pay for itself either: {gets_back(lk)}."
    return (f"In this count your chases pay for themselves overall (contact {fmt_runs(row['contact'])} "
            f"against choices {fmt_runs(row['choices'])} in the count table); this pitch is where they "
            f"don't: {gets_back(lk)}.")


def far_off_zero(summary):
    """The header's far-off cost prints 0.0."""

    return round(stored(summary["runs_at_stake"]), 1) == 0


FAR_OFF_ZERO = "on far-off pitches as a whole they cost you nothing net (the 0.0 at the top)"


def framing_line(summary, chosen):
    """For a hitter whose chase choices are average or better overall (or
    whose header says far-off chases cost nothing): the pitch lines are
    one spot in a good approach, not a new one. A hitter whose choices
    cost runs but whose header prints 0.0 is told where the cost is
    instead. None otherwise."""

    c = stored(summary["choices"])
    if not chosen or not (c > 0 or far_off_zero(summary)):
        return None
    if c <= -1:
        return (f"Overall your chase choices cost you {runs_phrase(-c)} a season, but {FAR_OFF_ZERO}: "
                "the pitches above are among the spots that cost the most.")
    level = "better than average" if c >= 1 else "about average"
    line = f"Overall your chase choices are {level} ({fmt_runs(c)} runs a season)"
    if far_off_zero(summary):
        line += f", and {FAR_OFF_ZERO}"
    videos = sum(is_video(lk) for _, lk in chosen)
    verb = "look at" if videos == len(chosen) else ("work on" if videos else "tighten")
    which = "the pitch above is one spot" if len(chosen) == 1 else "the pitches above are spots"
    return f"{line}: {which} to {verb}, not a new approach."


def left_off(leak_list, chosen):
    """The leaks on the list that the plan leaves off, with their numbers."""

    on = {n for n, _ in chosen}
    return [(n, lk) for n, lk in enumerate(leak_list, start=1) if n not in on]


def bigger_left_off(leak_list, chosen):
    """A leak the order left off the plan that costs NEXT_MIN_RATIO times
    a plan line or more, on enough pitches to repeat (the costliest when
    there are two), or None."""

    return next(((n, lk) for n, lk in left_off(leak_list, chosen)
                 if lk["pitches"] >= PLAN_LEAD_MIN_PITCHES
                 and any(-lk["choices"] >= NEXT_MIN_RATIO * -c["choices"] for _, c in chosen)), None)


def uncovered_counts(chosen, costly):
    """The costly counts no pitch line sits in."""

    return [g for g in costly if g not in {lk["count_group"] for _, lk in chosen}]


def lines_ref(steps, chosen):
    return "both lines above" if len(steps) == len(chosen) > 1 else f"line {steps[0]}"


def next_line(leak_list, chosen, rows, costly, start=None):
    """What the plan leaves for later, in one line, so a bigger leak on the
    list or a costly row of the count table is never left with no word: a
    leak bigger than a plan line (bigger_left_off), named by its number and
    the list's name for it, with the rule that put the plan's lines ahead
    of it; then each costly count with no pitch line, by what is in it (a
    leak left off, or many pitches with no one take), or that the hitter's
    contact there pays for the choices. The caller passes no costly counts
    when the spread line already names every count with a loss. None when
    nothing is left."""

    steps = {n: step for step, (n, _) in enumerate(chosen, start=1)}
    parts = []
    covered = {lk["count_group"] for _, lk in chosen}
    big = bigger_left_off(leak_list, chosen)
    if big:
        n, lk = big
        covered.add(lk["count_group"])
        name = leak_phrase(lk)
        ref = f"Leak {n} ({name[0].lower()}{name[1:]})"
        than = lines_ref([steps[m] for m, c in chosen if c["choices"] > lk["choices"]], chosen)
        # the plan line it out-costs most, and the rule that put that one
        # ahead of it; only when no rule does is it the note's lead
        small = max((c for _, c in chosen), key=lambda c: c["choices"])
        if is_video(lk):
            parts.append(f"{ref} costs more than {than}, but the ones you swung at were {VIDEO_DEPTH}: "
                         "one to go over on video with your coaches.")
        elif at_league_rate(lk) and not at_league_rate(small):
            ahead = [steps[j] for j, c in chosen if not at_league_rate(c)]
            who = "the lines above are" if len(ahead) > 1 else f"line {ahead[0]} is"
            parts.append(f"{ref} costs more than {than}, but you swing at those about as often as other "
                         f"hitters do, and {who} where you chase more than they do.")
        elif early_take(small) and not early_take(lk):
            ahead = [steps[j] for j, c in chosen if early_take(c)]
            who = "they go" if len(ahead) > 1 else f"line {ahead[0]} goes"
            parts.append(f"{ref} costs more than {than}, but a take before two strikes costs you no "
                         f"strikeouts, so {who} first.")
        else:
            parts.append(f"{ref} costs more than {than} and comes next"
                         + (", after the line your coaches start you with." if start else "."))
    out = [(n, lk) for n, lk in left_off(leak_list, chosen) if not big or n != big[0]]
    left = [g for g in costly if g not in covered]
    paid = [g for g in left if count_pays(rows[g])]
    # one sentence for the counts that cost: those holding a leak left off
    # say what it is, the rest are spread over many pitches
    held, spread = [], []
    for g in (g for g in left if g not in paid):
        inside = next(((n, lk) for n, lk in out if lk["count_group"] == g), None)
        (held if inside else spread).append((g, inside))
    pieces = []
    for g, inside in held + spread:
        cost = -rows[g]["choices"]
        amount = f"{runs_phrase(cost)} a season" if not pieces else f"{whole_runs(cost)}"
        pieces.append(f"{amount} {COUNT_PHRASES[g]}")
        if inside:
            pieces[-1] += (f", where leak {inside[0]} is "
                           + ("one for video with your coaches" if is_video(inside[1]) else "next after these"))
    if pieces:
        held_part = pieces[:len(held)]
        spread_part = [join_words(pieces[len(held):]) + ", spread over many pitches rather than one take"] \
            if spread else []
        parts.append("Your choices also cost about " + ", and about ".join(held_part + spread_part) + ".")
    if paid:
        where = join_words([COUNT_PHRASES[g] for g in paid])
        cost = runs_phrase(sum(-rows[g]["choices"] for g in paid))
        parts.append(f"{where[0].upper()}{where[1:]} your choices cost about {cost} a season, but what "
                     "you hit on those chases pays for them.")
    return " ".join(parts) or None


def keep_line(summary, chosen, left_out=False):
    """Every other line is a take; this one says what to keep doing. The
    fastball clause is left out when any leak on the card is a fastball,
    on the plan or not and on any pitcher-hand tab's list, and a plan of
    video items only says the staff takes it from here. A plan that leaves
    a leak on the list or a costly count for later says its pitches are the
    changes to start with, never the only ones."""

    one = len(chosen) == 1
    videos = [is_video(lk) for _, lk in chosen]
    if all(videos):
        only = ("The pitch above is not a take rule yet: the staff takes it to video with you first."
                if one else
                "The pitches above are not take rules yet: the staff takes them to video with you first.")
    elif any(videos):
        # video items come last, so with one of each the take is the first line
        only = (("The change to start with is the first pitch above" if left_out
                 else "The only take on this card is the first pitch above")
                + "; the staff takes the second to video with you first.")
    elif left_out:
        only = ("The change to start with is the pitch above." if one
                else "The changes to start with are the pitches above.")
    else:
        only = ("The only change on this card is the pitch above." if one
                else "The only changes on this card are the pitches above.")
    fastball_leak = any(lk["pitch_group"] == "fastball" for view in summary["leaks"].values() for lk in view)
    if summary["fastball_choices"] >= 1 and not fastball_leak:
        return f"Keep swinging at strikes; your fastball decisions are a strength. {only}"
    return f"Keep swinging at strikes. {only}"


def plan_items(leak_list, summary, table, start=None):
    """The card's one plan, from the all-pitchers leaks and table, as a
    list of items: kind (pitch / next / frame / contact / keep / fallback),
    and for a pitch line its step in the order to work on them (printed as
    1, 2), the leak's number on the list and the pictures (n, printed as a
    small tag), its cell, whether it is a video item, and the text. The
    pitcher-hand tabs show this same plan, with each pitch line's pitches
    from that hand under it (hand_counts), so the card never gives two
    plans.

    The first printed line is the first thing to do: the pitch lines come
    first, then what they leave for later (next_line), the framing line
    after them, and a contact hitter's reason is folded into his first
    take line. Only a plan with no take line opens on something else (the
    contact line, or a video item)."""

    rows = {r["group"]: r for r in table}
    loss = -rows["total"]["choices"]
    costly = [g for g in COUNT_GROUPS if rows[g]["choices"] <= -COSTLY_COUNT_RUNS]
    chosen = plan_pitch_items(leak_list, start)
    items = [{"kind": "pitch", "n": n, "step": step, "cell": leak_cell(lk), "video": is_video(lk),
              "text": pitch_line(lk)}
             for step, (n, lk) in enumerate(chosen, start=1)]
    takes = [it for it in items if not it["video"]]
    contact_led = summary["contact_led"]
    if contact_led and takes:
        takes[0]["text"] += " " + contact_clause(summary)
    # each line in a count the table shows as a plus or 0.0 says why, once a count;
    # each line in a count whose choices print a loss but whose chases pay
    # for themselves says so, the count's runs on the first line in it
    explained, paying = set(), set()
    for it, (_, lk) in zip(items, chosen):
        g = lk["count_group"]
        why = None if g in explained else strength_clause(rows, lk)
        if why:
            it["text"] += " " + why
            explained.add(g)
        why = pays_clause(rows, lk, first=g not in paying)
        if why:
            it["text"] += " " + why
            paying.add(g)
    named = sum(-lk["choices"] for _, lk in chosen)
    spread = loss >= SPREAD_MIN_RUNS and named < SPREAD_SHARE * loss
    if spread:
        biggest = sorted(n for n, _ in chosen) == list(range(1, len(chosen) + 1))
        frame = spread_line(rows, loss, rows["total"]["contact"], costly, len(chosen), biggest)
        if chosen and far_off_zero(summary):
            frame += f" {FAR_OFF_ZERO[0].upper()}{FAR_OFF_ZERO[1:]}."
    else:
        frame = framing_line(summary, chosen)
    later = next_line(leak_list, chosen, rows, [] if spread else costly, start) if chosen else None
    if later:
        items.append({"kind": "next", "n": None, "cell": None, "text": later})
    if frame:
        items.append({"kind": "frame", "n": None, "cell": None, "text": frame})
    if contact_led and not takes:
        items.insert(0, {"kind": "contact", "n": None, "cell": None, "text": contact_line(summary)})
    if not items:
        items.append({"kind": "fallback", "n": None, "cell": None, "text": fallback_line(rows, costly)})
    if chosen:
        left_out = bool(left_off(leak_list, chosen) or uncovered_counts(chosen, costly))
        items.append({"kind": "keep", "n": None, "cell": None,
                      "text": keep_line(summary, chosen, left_out)})
    return items


def plan_lines(leak_list, summary, table, start=None):
    return [it["text"] for it in plan_items(leak_list, summary, table, start)]


def hand_counts(p, cell, scale):
    """A plan line's pitches from one pitcher hand: how many, how many he
    chased, the league's rate on the same pitches and what the choices
    cost, for the line's note on that hand's tab. The rule that made the
    line a leak is not applied again to the slice, so a tab can never
    turn the card's take into something else."""

    s = p[(p["count_group"] == cell[0]) & (p["pitch_group"] == cell[1]) & (p["region"] == cell[2])]
    return {"pitches": int(len(s)), "chases": int(s["is_chase"].sum()),
            "rate": float(s["is_chase"].mean()) if len(s) else None,
            "league": float(s["e_match"].mean()) if len(s) else None,
            "choices": float(s["choices"].sum() * scale)}


def start_with(items, leak_list):
    """The roster's one line: the first pitch line's instruction, with the
    numbers that make the case: the two rates when they print well apart,
    as on the plan line; otherwise what the swings cost."""

    first = next((it for it in items if it["kind"] == "pitch"), None)
    if first is None:
        return ""
    lk = leak_list[first["n"] - 1]
    clause = first["text"].split(". ")[0].rstrip(".")
    depth = (f"{page_whole(lk['depth_in'])} in off" if not is_video(lk)
             else f"under {CLEARLY_OFF_IN} in off")
    if small_sample(lk) and not is_video(lk):
        depth += f", only {lk['pitches']} pitches"
    if rate_gap(lk) >= RATE_GAP_MIN_PTS:
        return f"{clause} ({page_pct(lk['rate'])}% vs {page_pct(lk['league'])}%, {depth})"
    return (f"{clause} (about as often as other hitters, but costing "
            f"{abs(page_runs(lk['choices'])):.1f} runs; {depth})")


# What step 16 found when hitters fixed their card's leaks, as a range
# over its two kinds of pairs (season to season, first half to second).
payoff = backtest[backtest["test"] == "per 10-pt cut beyond expected"].groupby("measure")["value"]


def span(measure, k=1.0):
    lo, hi = sorted(abs(payoff.get_group(measure)) * k)
    return f"{lo:.1f} to {hi:.1f}"


# ...and the two directions separately, season to season: most of the
# payoff is runs not lost by hitters who chased more, not runs gained by
# those who cut more. The card says so rather than promise a better line.
groups = backtest[backtest["test"].str.startswith("group vs as expected")].set_index(
    ["pair_kind", "measure", "test"])["value"]
lost = -groups[("season", "offense_runs", "group vs as expected: chased more than expected")]
gained = groups[("season", "offense_runs", "group vs as expected: cut more than expected")]
gained_x = groups[("season", "xchase_plus", "group vs as expected: cut more than expected")]
group_se = backtest[backtest["test"].str.startswith("group vs as expected")].set_index(
    ["pair_kind", "measure", "test"])["se"]
half_gained = groups[("half", "offense_runs", "group vs as expected: cut more than expected")]
half_lost = -groups[("half", "offense_runs", "group vs as expected: chased more than expected")]

EVIDENCE_QUESTION = "Does fixing a leak pay?"
# The card's footer, in plain words a hitter can read last: what the
# backtest found, without the arithmetic. The numbers behind it are in
# EVIDENCE_DETAIL (the noted report) and the README, and the sentence is
# checked here against the backtest so it cannot drift from them.
_per10 = backtest[backtest["test"] == "per 10-pt cut beyond expected"].set_index(["pair_kind", "measure"])["value"]
if not ((_per10[("season", "bb_rate")] > 0 and _per10[("half", "bb_rate")] > 0)
        and (_per10[("season", "k_rate")] <= 0.001 and _per10[("half", "k_rate")] <= 0.001)
        and (_per10[("season", "zone_swing_rate")] > -0.01 and _per10[("half", "zone_swing_rate")] > -0.01)
        and lost > gained):
    raise SystemExit("The backtest no longer says what the card's footer says; rewrite EVIDENCE_LINE.")
EVIDENCE_LINE = (
    f"{EVIDENCE_QUESTION} Hitters who cut their leak chasing more than expected stopped giving "
    "counts away: more walks, no more strikeouts, still swinging at strikes. The gain was mostly "
    "runs not lost; hits come later, if they come.")
EVIDENCE_DETAIL = (
    f"Hitters who cut their leak chasing 10 points more than their numbers predicted gained "
    f"{span('offense_runs')} runs per 600 PA (xwOBA) and {span('xchase_plus')} xChase+ points, "
    f"with only {span('zone_swing_rate', 100)} pts fewer swings at strikes. It paid about the "
    "same whether or not they hit well in those counts. Two cautions before promising a "
    "player anything. Season to season, most of the payoff came from the other direction: "
    f"hitters who chased more than predicted lost {lost:.1f} ± "
    f"{group_se[('season', 'offense_runs', 'group vs as expected: chased more than expected')]:.1f} "
    f"runs of offense, while those who cut more gained {gained_x:.1f} xChase+ points but only "
    f"{gained:.1f} ± "
    f"{group_se[('season', 'offense_runs', 'group vs as expected: cut more than expected')]:.1f} "
    f"runs (half to half, both sides show it: +{half_gained:.1f} and −{half_lost:.1f}). So the "
    "first promise to a hitter is fewer wasted counts, not a better slash line. And leaks "
    "shrink on their own: how far above the league a hitter chases in his leaks halves the "
    "next season with nobody doing anything, so the target under each plan is the number "
    "to beat, not the hitter's current rate.")
if len(textwrap.wrap(EVIDENCE_LINE, 118)) > 2:
    raise SystemExit("The card's footer line no longer fits in two lines; shorten EVIDENCE_LINE.")

# The target (step 19): this season's leak chasing on the backtest's scale
# and what its line predicts for next season with no change. Read from the
# frozen file, so the number on the card is the number step 20 will score.
PRED_FILE = XCHASE / "coaching" / f"leak_predictions_{SEASON}.csv"
TARGETS = {}
if PRED_FILE.exists():
    frozen = pd.read_csv(PRED_FILE)
    frozen_leaks = {b: list(map(tuple, g.sort_values("row")[lr.LEAK_CELL].itertuples(index=False)))
                    for b, g in frozen[frozen["row"] != "hitter"].groupby("batter")}
    for r in frozen[(frozen["row"] == "hitter") & (frozen["leaks"] > 0)].itertuples():
        TARGETS[int(r.batter)] = {
            "season": SEASON, "next_season": SEASON + 1,
            "excess": float(getattr(r, f"excess_{SEASON}")),
            "predicted": float(getattr(r, f"predicted_excess_{SEASON + 1}")),
            "cells": frozen_leaks.get(int(r.batter), []),
            "freeze_date": str(r.freeze_date),
            "out_of_sample": str(getattr(r, "out_of_sample", "yes")),
            "actual": None,
        }
# A retrospective freeze (out_of_sample = no) was set after the next season
# was played, so its card shows how that season came out, from step 20's
# score of the frozen file. A real forecast has no result until step 20 runs.
SCORE_FILE = XCHASE / "coaching" / f"leak_scores_{SEASON + 1}.csv"
if TARGETS and SCORE_FILE.exists():
    scored = pd.read_csv(SCORE_FILE)
    if "period" in scored:              # files from before the --period option are full-season
        scored = scored[scored["period"] == "full"]
    for r in scored.itertuples():
        if int(r.batter) in TARGETS:
            TARGETS[int(r.batter)]["actual"] = float(getattr(r, f"actual_excess_{SEASON + 1}"))

TARGET_MIN_PTS = 2              # no target when the no-change forecast rounds to this or less
TARGET_SCALE_NOTE_PTS = 3       # a number to beat this far from the leak rows' own gap says so


def frozen_spots(cells):
    """The frozen cells of a target whose card now lists other leaks, by
    name and without a pitcher hand: "two strikes, breaking balls below the
    zone; 0-1 or 1-1, fastballs above the zone"."""

    return "; ".join(f"{COUNT_LABELS[g][0].lower() + COUNT_LABELS[g][1:]}, {LEAK_PITCH[pg]} "
                     f"{LEAK_REGION[r]}" for g, pg, r in cells)


def leaks_named(n):
    """The leaks a target covers: every leak on the card, not only the plan's."""

    return "Leak 1" if n == 1 else ("Leaks 1 and 2 together" if n == 2 else f"Leaks 1 to {n} together")


def points(n):
    return f"{n} point" + ("" if abs(n) == 1 else "s")


def minus(text):
    """A number as the page prints a negative one, with a minus sign."""

    return text.replace("-", "−")


def card_gap(leak_list):
    """How far above the league the hitter chased in these leaks, pooled,
    in points on the card's own rates (the "avg" in the leak rows): the
    pooled rate less the pooled league rate, each rounded as a row prints
    it, so one leak's points are its row's two numbers apart. Every leak
    has more chases than the league expects, so it is never below the
    league."""

    n = sum(lk["pitches"] for lk in leak_list)
    rate = sum(lk["chases"] for lk in leak_list) / n
    league = sum(stored(lk["league"]) * lk["pitches"] for lk in leak_list) / n   # as the page stores it
    return page_pct(rate) - page_pct(league)


def target_text(summary):
    """The target as one sentence, the same on every surface: the card's
    leaks it covers (all of them, not only the plan's), how far above the
    league's chase rate the hitter chased in them this season, in points,
    what the frozen line expects next season with no change, and that only
    below that counts. A retrospective freeze says it was set afterward and
    how the next season came out; a forecast at about the league's rate
    says there is no number to beat, about the forecast, never this season;
    a card whose every leak is a video item prints no number. None when the
    hitter has no frozen target.

    A number to beat is on step 19's scale, the one step 20 scores. The
    no-target sentence has none to beat, so its 2026 points are the card's
    own (card_gap), the ones a reader can check against the leak rows: on
    step 19's coarser league baseline a two-strike breaking ball the rows
    print above the league can come out below it (Rutschman, 2026: 49% vs
    43% in the row, 3 points below on that scale). Its forecast says "at
    or under it" when it is more than TARGET_MIN_PTS below the league."""

    t = summary["target"]
    if not t:
        return None
    leaks_all = summary["leaks"]["all"]
    # A target frozen on spots the card no longer lists all of (the leaks
    # were re-ranked after the freeze) is still the one step 20 scores, so
    # it stays, named for its own spots; the leak rows say nothing about it.
    spots = t.get("frozen_cells")
    lead = (f"Frozen on {t['freeze_date']} for spots the re-ranked leaks above no longer all cover "
            f"({frozen_spots(spots)})" if spots else "")
    if not spots and all(is_video(lk) for lk in leaks_all):
        return (f"No number to beat: the one leak on this card was {VIDEO_DEPTH}, one for video, "
                "not a take rule." if len(leaks_all) == 1 else
                f"No number to beat: every leak on this card was {VIDEO_DEPTH}: video items, not "
                "take rules.")
    which = leaks_named(len(leaks_all))
    season, nxt = t["season"], t["next_season"]
    pred = round(t["predicted"] * 100)
    retro = t["out_of_sample"] == "no"
    if pred <= TARGET_MIN_PTS:
        head = "No chase target" if summary["contact_led"] else "No target"
        verb = "was" if len(leaks_all) == 1 else "were"
        xf = round(t["excess"] * 100)
        x = xf if spots else card_gap(leaks_all)
        where = (f"{points(x)} above the league's chase rate" if x > 0 else
                 "about at the league's chase rate")
        # the forecast is on step 19's league rate; when the rows add up to something
        # else, say what the forecast starts from
        scale = ("" if spots or abs(x - xf) < TARGET_SCALE_NOTE_PTS else
                 f" ({xf} on the simpler league rate the target uses)" if xf > 0 else
                 " (at or under it on the simpler league rate the target uses)")
        at = "at or under" if pred < -TARGET_MIN_PTS else "about at"
        line = (f"{head}: {lead}. There you were {where} in {season}, and " if spots else
                f"{head}: {which.lower()} {verb} {where} in {season}{scale}, and ")
        line += (f"a line fit afterward on seasons through {season} put {nxt} {at} the "
                 "league's rate." if retro else f"with no change should be {at} it in {nxt}.")
        if retro and t["actual"] is not None:
            line += f" You were at {minus(f'{t['actual'] * 100:.0f}')}."
        if summary["contact_led"]:
            line += " The number to move is contact on chases."
        if season >= ABS_FIRST_SEASON:
            line += f" {ABS_TARGET_NOTE}"
        return line
    # The number to beat is on step 19's scale, which the leak rows do not
    # use; when the rows add up to something else, the sentence says so.
    x = round(t["excess"] * 100)
    rows_x = x if spots else card_gap(leaks_all)
    scale = ("" if abs(rows_x - x) < TARGET_SCALE_NOTE_PTS else
             f" ({rows_x} on the rows above; the target uses a simpler league rate, the one it is "
             "scored on)")
    now = (f"{lead}: you chased {points(x)} above the league's chase rate there in {season}."
           if spots else
           f"{which}: you chased {points(x)} above the league's chase rate in {season}{scale}.")
    if not retro:
        return (f"{now} Those spots get better on their own, so with no change you'd be about "
                f"{points(pred)} above it in {nxt}. Under {pred} is a fix."
                + (f" {ABS_TARGET_NOTE}" if season >= ABS_FIRST_SEASON else ""))
    line = (f"{now} Set afterward from seasons through {season}, the line put {nxt} at about "
            f"{points(pred)} above it with no change.")
    a = t["actual"]
    if a is None:
        return line + f" Not scored in {nxt}: too few of these pitches, or not qualified."
    under = a < t["predicted"]
    if round(a * 100) != pred:
        return line + f" You were at {minus(f'{a * 100:.0f}')}: " + ("under it, a fix." if under else "not under it.")
    return (line + f" You were at {minus(f'{a * 100:.1f}')} against its {minus(f'{t['predicted'] * 100:.1f}')}: "
            + ("just under, a fix." if under else "not under it."))


def target_beat(summary):
    """The roster's Beat column: the number to get under and this season's
    beside it, or why there is none."""

    t = summary["target"]
    if not t:
        return ""
    if not t["frozen_cells"] and all(is_video(lk) for lk in summary["leaks"]["all"]):
        return "none: video only"
    if round(t["predicted"] * 100) <= TARGET_MIN_PTS:
        return "no target"
    return f"under {round(t['predicted'] * 100)} (was {round(t['excess'] * 100)})"


print("Building hitter summaries...")
players = []
for _, row in board.sort_values("xchase_plus", ascending=False).iterrows():
    bid = int(row["batter"])
    p = df[df["batter"] == bid]
    scale = PA_SCALE / row["plate_appearances"]
    ch = p[p["is_chase"] == 1]
    summary = {
        "id": bid, "name": row["player"],
        "team": TEAMS[bid][0], "teams": list(TEAMS[bid]),
        "bats": "S" if bid in switch else main_side.get(bid, "R"),
        "rank": int(row["xchase_plus_rank"]), "of": n_qualified,
        "pa": int(row["plate_appearances"]), "xchase_plus": float(row["xchase_plus"]),
        "chase": float(p["is_chase"].mean()), "chase_league": float(p["e_match"].mean()),
        "whiff": float(ch["whiff"].mean()), "whiff_league": float(ch["w_match"].mean()),
        "choices": float(p["choices"].sum() * scale), "contact": float(p["contact"].sum() * scale),
        "runs_at_stake": float(max(row["far_off_recoverable"], 0.0)) + 0.0,   # never -0.0
        "archetype": row["archetype"],
        "noted": NOTES.get(row["player"], NO_NOTE)[0],
        "coach_note": NOTES.get(row["player"], NO_NOTE)[1],
        "note_start": NOTES.get(row["player"], NO_NOTE)[2],
        "fastball_choices": float(p.loc[p["pitch_group"] == "fastball", "choices"].sum() * scale),
    }
    c, ch = stored(summary["contact"]), stored(summary["choices"])
    summary["contact_led"] = bool(c <= -CONTACT_LED_RUNS and -c > max(-ch, 0)
                                  and -c >= stored(summary["runs_at_stake"]))
    summary["tables"] = {h: count_table(hand_view(p, h), scale, bid, h) for h in HANDS}
    summary["leaks"] = {h: leaks(hand_view(p, h), scale, bid) for h in HANDS}
    all_cells = [leak_cell(lk) for lk in summary["leaks"]["all"]]
    for h in HANDS:
        for lk in summary["leaks"][h]:
            lk["phrase"] = leak_phrase(lk)
            # a hand tab's leak carries the card's number for the same pitch (the
            # one on the pictures and the plan), or none when the leak shows up
            # against that hand only
            if h != "all":
                lk["all_n"] = all_cells.index(leak_cell(lk)) + 1 if leak_cell(lk) in all_cells else None
    summary["plan_items"] = plan_items(summary["leaks"]["all"], summary, summary["tables"]["all"],
                                       start=summary["note_start"])
    # The hand tabs show this plan, with each pitch line's pitches from that
    # hand under it (for a switch hitter the hand is also mostly his side).
    for it in summary["plan_items"]:
        if it["kind"] == "pitch":
            it["by_hand"] = {h: hand_counts(hand_view(p, h), it["cell"], scale) for h in ("R", "L")}
    summary["plan"] = [it["text"] for it in summary["plan_items"]]
    summary["start_with"] = start_with(summary["plan_items"], summary["leaks"]["all"])
    target = TARGETS.get(bid)
    cells = {(lk["count_group"], lk["pitch_group"], lk["region"]) for lk in summary["leaks"]["all"]}
    # The frozen target is what step 20 scores, so it stays on the card even
    # when the card's leaks have moved since the freeze; it then names its
    # own spots (frozen_cells) instead of the leak rows.
    summary["target"] = ({k: target[k] for k in ("season", "next_season", "excess", "predicted",
                                                   "out_of_sample", "actual", "freeze_date")}
                         | {"frozen_cells": (None if set(target["cells"]) == cells
                                             else [list(c) for c in target["cells"]])}
                         if target else None)
    summary["target_text"] = target_text(summary)
    summary["target_beat"] = target_beat(summary)
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
if TARGETS:
    with_target = sum(1 for p in players if p["target"])
    stale = sum(1 for p in players if p["target"] and p["target"]["frozen_cells"])
    print(f"  targets from {PRED_FILE.name}: {with_target} hitters"
          + (f"; {stale} whose frozen spots are not all the card's leaks (named for the spots)"
             if stale else ""))
if (plan_checks.CLEARLY_OFF_IN, plan_checks.COUNT_PHRASES) != (CLEARLY_OFF_IN, COUNT_PHRASES):
    raise SystemExit("plan_checks.py's CLEARLY_OFF_IN or COUNT_PHRASES differ from step 17's.")
if plan_checks.RULES != {k: globals()[k] for k in plan_checks.RULES}:
    raise SystemExit("plan_checks.py's RULES differ from step 17's constants of the same names.")
n_plans = plan_checks.check(players)
print(f"  checked {n_plans} plans, their pitcher-hand notes and the hand tabs' leak numbers against "
      "the lines and numbers beside them: no contradictions")
if NOTES:
    n_claims, n_noted = coach_notes.check(players)
    print(f"  checked {n_claims} claims in the coach's notes for {n_noted} hitters: all hold")

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


def pct(v):
    return "–" if v is None or not np.isfinite(v) else f"{page_pct(v)}%"


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
    def __init__(self, theme_name, w=None, h=None):
        self.t = THEMES[theme_name]
        self.theme_name = theme_name
        self.w, self.h = w or W, h or H
        self.fig = plt.figure(figsize=(self.w / DPI, self.h / DPI), dpi=DPI)
        self.fig.patch.set_facecolor(self.t["surface"])
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, self.w)
        self.ax.set_ylim(self.h, 0)
        self.ax.axis("off")

    def text(self, x, y, s, size=18, color="ink", weight="normal", ha="left", va="baseline", **kw):
        return self.ax.text(x, y, s, fontsize=px(size), color=self.t.get(color, color),
                            fontweight=weight, ha=ha, va=va, **kw)

    def wrapped(self, x, y, s, width_chars, size=18, line=26, color="ink", weight="normal"):
        lines = textwrap.wrap(s, width_chars, break_on_hyphens=False)
        for i, ln in enumerate(lines):
            self.text(x, y + i * line, ln, size=size, color=color, weight=weight)
        return y + len(lines) * line

    def plan_mark(self, x, y, it, r, size, tag_right):
        """A plan line's mark: a pitch line's step in the order to work on
        them (filled, so it is never read as a leak number), and at the
        right edge a small tag with its leak's number as on the pictures;
        a dot for any other line."""

        if it["kind"] != "pitch":
            self.ax.add_patch(Circle((x, y), r * 0.4, fc=self.t["ink"], ec="none"))
            return
        self.ax.add_patch(Circle((x, y), r, fc=self.t["ink"], ec="none"))
        self.text(x, y + 1, str(it["step"]), size=size, weight="bold", ha="center", va="center",
                  color="surface")
        tr = r * 0.8
        self.ax.add_patch(Circle((tag_right - tr, y), tr, fc=self.t["surface"], ec=self.t["muted"],
                                 lw=px(1.2)))
        self.text(tag_right - tr, y + 1, str(it["n"]), size=size - 2, weight="bold", ha="center",
                  va="center", color="ink2")
        self.text(tag_right - 2 * tr - 6, y + 1, "leak", size=size - 1, ha="right", va="center",
                  color="muted")

    def hline(self, x0, x1, y, color="hair", lw=1):
        self.ax.plot([x0, x1], [y, y], color=self.t[color], lw=px(lw), solid_capstyle="butt")

    def panel(self, x, y, w, h):
        a = self.fig.add_axes([x / self.w, 1 - (y + h) / self.h, w / self.w, h / self.h])
        a.set_facecolor(self.t["surface"])
        a.axis("off")
        return a

    def zone(self, a, rgb, zone, mask, gap=None, evidence=None, markers=(), marker_r=0.2):
        """marker_r: the leak markers' radius in feet (larger on a small picture,
        so the number still fits inside)."""

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
            a.add_patch(Circle((mx, mz), marker_r, fc=self.t["surface"], ec=self.t["ink"],
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

    def save_page(self, pdf):
        pdf.savefig(self.fig, facecolor=self.t["surface"])
        plt.close(self.fig)


PANEL_ASPECT = (ZS[-1] - ZS[0]) / (XS[-1] - XS[0])
GRID_LEFT, GRID_TOP = 64, 196
GRID_BOTTOM = 960               # the pictures end here; the key sits under them
PANEL_W = 165                   # a picture's width at most: two or three rows reach it, four rows
                                # are set by the height; what the pictures leave is the right column's
BOTTOM_BLOCK = 896              # y where the trend + target block starts
COLUMN_END = BOTTOM_BLOCK - 22  # the By count table's last line stays above this
ROW_LABEL_W = 118
RIGHT_X, RIGHT_W = 1026, 830    # the right column: the plan, the leaks, the table, the trend
KEY_CHARS = 92                  # the key's words beside the ramp stop short of the right column


def draw_grid(card, rows, cells, zone, markers=None, orient=None, whiff_row=None):
    """rows: list of (label, sublabel). cells(row_index, group) -> (rgb, gap, evidence).
    markers: {(row_index, group): [(number, (x, z)), ...]}. orient: the side the
    batter stands on ("R" or "L") for the Inside / Away labels, or None.
    whiff_row: the index of the misses row, drawn apart from the chase rows."""

    n = len(rows)
    avail_h = GRID_BOTTOM - (GRID_TOP + 46)
    w = min(PANEL_W, (avail_h - (n - 1) * 14) / n / PANEL_ASPECT)
    h = w * PANEL_ASPECT
    x0 = GRID_LEFT + ROW_LABEL_W
    labels = COUNT_LABELS if w >= PANEL_W else COUNT_SHORT
    if orient:
        side = "left" if orient == "R" else "right"
        card.text(GRID_LEFT, GRID_TOP - 6, f"Catcher's view, to scale. Inside is on the {side}.",
                  size=13, color="muted")
    for j, g in enumerate(COUNT_GROUPS):
        cx = x0 + j * (w + 14) + w / 2
        card.text(cx, GRID_TOP + 18, labels[g], size=19 if w >= PANEL_W else 17, weight="bold", ha="center")
        card.text(cx, GRID_TOP + 40, COUNT_DETAIL[g], size=14, color="muted", ha="center")
    for i, (label, sub) in enumerate(rows):
        y = GRID_TOP + 52 + i * (h + 14)
        if i == whiff_row:
            card.hline(GRID_LEFT, x0 + 4 * (w + 14) - 14, y - 7, color="axis", lw=1.2)
        card.wrapped(GRID_LEFT, y + h / 2 - 6, label, 12, size=17, line=22, weight="bold")
        if sub:
            card.wrapped(GRID_LEFT, y + h / 2 + 38, sub, 14, size=13, line=17, color="muted")
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


# What the key calls the scale's midpoint and the faded-out background in
# each theme: the dark midpoint is a dark gray and nothing on a dark card is white.
KEY_WORDS = {"light": {"avg": "Gray", "none": "White"},
             "dark": {"avg": "Dark gray", "none": "Background"}}


def draw_key(card, x, y, whiff=False):
    """The color key, directly under the pictures: the ramp and the words."""

    draw_legend(card, x, y, "gap")
    words = ("Blue: takes more than the average hitter at that spot and count. Red: chases more. "
             f"{KEY_WORDS[card.theme_name]['avg']}: about average. "
             f"{KEY_WORDS[card.theme_name]['none']}: too few pitches to say. Outline: 15 points or more over.")
    if whiff:
        words += " Misses row: purple, more misses than the average hitter on the same chases; green, fewer."
    card.wrapped(x + 330, y + 10, words, KEY_CHARS, size=12, line=15, color="ink2")


def draw_legend(card, x, y, kind="gap", label_left="", label_right=""):
    w, h = 300, 14
    if kind == "rate":
        values = np.linspace(0, 0.7, 300)
        colors = sequential(values, card.t)
    else:
        values = np.linspace(-cs.GAP_LIMIT, cs.GAP_LIMIT, 300)
        colors = diverging(values, card.t, kind)
    a = card.fig.add_axes([x / card.w, 1 - (y + h) / card.h, w / card.w, h / card.h])
    a.imshow(colors[None, :, :], aspect="auto", extent=[0, 1, 0, 1])
    a.axis("off")
    if kind == "rate":
        card.text(x, y + h + 20, "0%", size=13, color="muted")
        card.text(x + w, y + h + 20, "70%+", size=13, color="muted", ha="right")
    else:
        card.text(x, y + h + 20, "−30 pts", size=13, color="muted")
        card.text(x + w / 2, y + h + 20, "league", size=13, color="muted", ha="center")
        card.text(x + w, y + h + 20, "+30 pts", size=13, color="muted", ha="right")
    if label_left:
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
    # there, next to the league's, across the right column. The average card
    # keeps the narrow table. What the columns mean (GLOSSARY) is on the
    # page, folded away, not on the card. Returns the last row's line.
    if league_only:
        at = {"pitches": 190, "chase": 290, "far": 400, "whiff": 510}
    else:
        at = {"pitches": 200, "chase": 290, "far": 380, "whiff": 470, "xwoba": 580,
              "choices": 700, "contact": RIGHT_W}
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
    card.hline(x, x + RIGHT_W if not league_only else x + 520, y + 4)
    names = dict(COUNT_LABELS, total="All counts")
    for r in rows:
        y += 22
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
    return y


GLOSSARY = ("Choices: what the swing decisions cost. Contact: what the chases produced vs an average "
            "hitter's. Far-off: 4+ inches off the plate. Misses: swing-and-miss on a chase. xwOBA: how "
            "plate appearances reaching these counts turn out vs the league's. 600 PA is a season.")
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
    for yr in years:        # the card's own season in bold: older cards show later seasons too
        card.text(sx(yr), y + h + 20, str(yr), size=12, color="ink" if yr == SEASON else "muted",
                  ha="center", weight="bold" if yr == SEASON else "normal")
    card.ax.plot([sx(yr) for yr in years], [sy(league[yr]) for yr in years],
                 color=card.t["league"], lw=px(2), solid_capstyle="round")
    avg_y = sy(league[years[-1]]) + 5
    if series and abs(sy(series[-1][1]) - sy(league[years[-1]])) < 14:
        avg_y = max(sy(series[-1][1]), sy(league[years[-1]])) + 18
    card.text(sx(years[-1]) + 10, avg_y, "avg", size=13, color="muted")
    if series:
        xs_ = [sx(yr) for yr, _ in series]
        ys_ = [sy(v) for _, v in series]
        if len(series) >= 3:    # two points are not a trend; draw them as dots
            card.ax.plot(xs_, ys_, color=card.t["ink"], lw=px(2.4), solid_capstyle="round")
        card.ax.scatter(xs_, ys_, s=px(9) ** 2, color=card.t["ink"], zorder=4,
                        edgecolors=card.t["surface"], linewidths=px(2))
        card.text(xs_[-1] + 10, ys_[-1] + 5, "you", size=13, color="ink", weight="bold")


def trend_title(series, every=False):
    title = "Far-off chase rate by season" + (", every hitter" if every else "")
    if 0 < len(series) < 3:
        title += f" ({len(series)} season{'s' if len(series) > 1 else ''})"
    return title


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
    if summary["contact_led"]:
        side = summary["bats"] if summary["bats"] != "S" else max(
            summary["side_pitches"], key=summary["side_pitches"].get)
        rows.append(("Misses on chases", "swing-and-miss per chase, vs the average hitter: "
                     "purple more, green fewer", side, "all", "whiff"))
    return rows


MARKER_GAP = 0.7                # ft between marker centers on one picture (a marker is about 0.6 ft across)
SNAP_FT, MARK_MIN_GAP = 1.0, 0.05    # a number on a spot under +5 pts moves to the nearest +5 spot within a foot


def place_marker(spot, taken, gap=MARKER_GAP):
    """The marker's spot, nudged until it is clear of the others on the picture."""

    for dx, dz in ((0, 0), (1, 0), (-1, 0), (0, -1), (0, 1), (1, -1), (-1, -1)):
        cand = spot + gap * np.array([dx, dz])
        if all(np.hypot(*(cand - np.array(o))) >= gap for o in taken):
            return cand
    return spot


def batter_region(x, z, side, zone):
    """The region off the zone a spot is in, batter-relative, as the page's
    Zone numbers name it (inside is the side the batter stands on)."""

    xb = -x if side == "L" else x
    vert = "up" if z > zone[1] else ("down" if z < zone[0] else "")
    horiz = "in" if xb < -cs.HALF_PLATE_PLUS_BALL else ("away" if xb > cs.HALF_PLATE_PLUS_BALL else "")
    return "-".join(w for w in (vert, horiz) if w)


def marker_spot(lk, surf, side, zone, mask):
    """Where a leak's number goes on its picture: the median of its chased
    pitches, unless the picture, which counts every pitch type, reads under
    +5 points there; then the nearest spot at +5 or more within SNAP_FT, in
    the same region off the zone, with enough pitches to color (on 2026 the
    median move is under 3 inches). The page's placeMarkers does the same,
    so the web card and the printed one put it in one place."""

    ix = lambda arr, v: int(np.clip(np.rint((v - arr[0]) / cs.GRID_STEP), 0, len(arr) - 1))
    x, z = lk["x"], lk["z"]
    if surf["gap"][ix(ZS, z), ix(XS, x)] >= MARK_MIN_GAP:
        return np.array([x, z])
    best = None
    for b in range(ix(ZS, z - SNAP_FT), ix(ZS, z + SNAP_FT) + 1):
        for a in range(ix(XS, x - SNAP_FT), ix(XS, x + SNAP_FT) + 1):
            d = np.hypot(XS[a] - x, ZS[b] - z)
            if (d > SNAP_FT or mask[b, a] or surf["evidence"][b, a] < 0.5 or surf["gap"][b, a] < MARK_MIN_GAP
                    or batter_region(XS[a], ZS[b], side, zone) != lk["region"]):
                continue
            if best is None or d < best[0]:
                best = (d, XS[a], ZS[b])
    return np.array([best[1], best[2]]) if best else np.array([x, z])


def leak_markers(summary, specs, p, gap=MARKER_GAP):
    """Numbered leak markers: on the row of the pitcher hand the leak names,
    or the first row showing that leak's side, at marker_spot on that row's
    picture for the leak's count."""

    markers = {}
    mask = cs.in_zone_mask(XS, ZS, *summary["zone"])
    for n, lk in enumerate(summary["leaks"]["all"], start=1):
        hand = lk["hand"] or "all"
        row = next((i for i, sp in enumerate(specs)
                    if sp[2] == lk["side"] and sp[3] == hand and sp[4] == "chase"), None)
        if row is None:
            row = next((i for i, sp in enumerate(specs) if sp[2] == lk["side"] and sp[4] == "chase"), None)
        if row is None:
            continue
        key = (row, lk["count_group"])
        _, _, side, hand, _ = specs[row]
        frame = p[(p["count_group"] == lk["count_group"]) & (p["stand"] == side)]
        if hand != "all":
            frame = frame[frame["p_throws"] == hand]
        spot = marker_spot(lk, player_surface(frame), side, summary["zone"], mask)
        spot = place_marker(spot, [o for _, o in markers.get(key, [])], gap)
        markers.setdefault(key, []).append((n, tuple(spot)))
    return markers


def spec_cell(p, spec, g, t, mask):
    """One picture of a row from row_specs, for count group g: (rgb, gap, evidence)."""

    _, _, side, hand, metric = spec
    frame = p[(p["count_group"] == g) & (p["stand"] == side)]
    if hand != "all":
        frame = frame[frame["p_throws"] == hand]
    s = player_surface(frame, metric)
    return compose(diverging(s["gap"], t, metric), s["evidence"], t, mask), s["gap"], s["evidence"]


LEAK_NAME_CHARS = 64             # a leak's name in the card's list fits in this many characters at size 15
# The PNG plan's size, line, gap under a line and wrap, then the wraps of a line
# with no leak tag, of the keep line and of the coach's note (both 13 px), each
# wrap the most characters whose widest line over six seasons' cards stays inside
# the column (a tagged line stops short of its leak tag). One or two lines take
# the first set; three or more the second, set tighter so the column keeps its
# place. A column that would still run into the trend and target under it takes
# the third, a size tighter again; no card in six seasons needs it (Jeremy Peña's
# 2026 card, the longest, ends 5 px above the line at 15 px), and the build warns
# when a column would not fit at it.
PNG_PLAN_SETS = ((16, 22, 4, 97, 104, 136, 134),
                 (15, 19, 2, 104, 111, 136, 134),
                 (14, 17, 2, 111, 119, 136, 134))
# The target beside the trend: its left edge in the column, the trend's width, and
# the target's size, line and wrap. A target over five lines at 13 px (about 280
# characters, most 2022-2025 targets) is set a size smaller; the last set, wider
# with the trend narrower, is for a longer one still, which no card in six seasons
# had until a target named its frozen spots (José Caballero's 2026 card, set a size
# smaller again), and the build warns when a target would not fit at the last.
PNG_TARGET_SETS = ((470, 360, 13, 17, 56),
                   (470, 360, 12, 15, 61),
                   (410, 300, 12, 15, 73),
                   (410, 300, 11, 13, 79))


def plan_column(card, summary, plan_set):
    """The right column above the trend: the plan, each line tagged with its
    leak's number, the coach's note, the leaks and the By count table. card
    may be a Measure, to find where the table would end before anything is
    drawn. Returns the table's last line."""

    t = card.t
    y = 214
    card.text(RIGHT_X, y, "What to work on", size=22, weight="bold")
    y += 32
    size, lead, gap, chars, untagged_chars, keep_chars, note_chars = plan_set
    for it in summary["plan_items"]:
        if it["kind"] == "keep":
            y += 2
            y = card.wrapped(RIGHT_X + 22, y, it["text"], keep_chars, size=13, line=17, color="ink2")
            continue
        card.plan_mark(RIGHT_X + 10, y - 6, it, 10, 12, RIGHT_X + RIGHT_W)
        y = card.wrapped(RIGHT_X + 30, y, it["text"], chars if it["kind"] == "pitch" else untagged_chars,
                         size=size, line=lead) + gap
    if summary["coach_note"]:
        y += 4
        card.text(RIGHT_X, y, "COACH'S NOTE, FOR THE STAFF", size=12, color="muted", weight="bold")
        y = card.wrapped(RIGHT_X, y + 19, summary["coach_note"], note_chars, size=13, line=17,
                         color="ink2")
    y += 16
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    card.text(RIGHT_X, y + 20, "Biggest leaks", size=19, weight="bold")
    card.text(RIGHT_X + RIGHT_W, y + 20, "numbered on the pictures  ·  ranked by runs; the plan "
              "takes up to two, in the order to work on them", size=12, color="muted", ha="right")
    y += 26
    if not summary["leaks"]["all"]:
        y += 24
        card.text(RIGHT_X, y, "None worth 0.75 runs per 600 PA.", size=16, color="ink2")
    worst = max((abs(lk["choices"]) for lk in summary["leaks"]["all"]), default=1.0)
    for n, lk in enumerate(summary["leaks"]["all"], start=1):
        y += 28
        card.ax.add_patch(Circle((RIGHT_X + 12, y - 6), 12, fc=t["surface"], ec=t["ink"], lw=px(1.6)))
        card.text(RIGHT_X + 12, y - 5, str(n), size=14, weight="bold", ha="center", va="center")
        # a long name ("mostly vs RHP", changeups / splitters) is set smaller so it clears the bar
        card.text(RIGHT_X + 34, y, lk["phrase"], size=min(15, 15 * LEAK_NAME_CHARS / len(lk["phrase"])))
        # the bar is the run cost, which is what ranks the list
        tx0, tw = RIGHT_X + RIGHT_W - 304, 84
        card.ax.add_patch(Rectangle((tx0, y - 9), tw, 6, fc=t["hair"], ec="none", zorder=2))
        card.ax.add_patch(Rectangle((tx0, y - 9), tw * abs(lk["choices"]) / worst, 6,
                                    fc=t["ink2"], ec="none", zorder=3))
        card.text(tx0 + tw + 12, y, f"{lk['rate'] * 100:.0f}% vs {lk['league'] * 100:.0f}%  ·  "
                  f"{lk['chases']} of {lk['pitches']}", size=13, color="ink2")
        card.text(RIGHT_X + RIGHT_W, y, fmt_runs(lk["choices"]), size=16, weight="bold",
                  ha="right")
    y += 22
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    return draw_table(card, RIGHT_X, y + 14, summary["tables"]["all"])


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

    # Header tiles: the cost of far-off chases, and where all the runs go
    tx = 1196
    card.text(tx, 60, "COST OF FAR-OFF CHASES", size=13, color="muted", weight="bold")
    card.text(tx, 112, f"{summary['runs_at_stake']:.1f}", size=44, weight="bold")
    card.text(tx, 136, "runs per 600 PA from your choices on", size=12, color="ink2")
    card.text(tx, 152, "pitches at least 4 inches off the plate", size=12, color="ink2")
    bx = 1470
    card.text(bx, 60, "WHERE THE RUNS GO · ALL CHASES", size=13, color="muted", weight="bold")
    card.text(W - 64, 60, "per 600 PA", size=13, color="muted", ha="right")
    zero, half = bx + 215, 95
    for k, (label, v) in enumerate([("Choices", summary["choices"]), ("Contact", summary["contact"])]):
        yy = 96 + k * 38
        card.text(bx, yy + 6, label, size=16, color="ink2")
        length = np.clip(v, -25, 25) / 25 * half
        card.ax.add_patch(Rectangle((zero + min(0, length), yy - 8), abs(length), 16,
                                    fc=t["ink2"], ec="none"))
        card.text(W - 64, yy + 6, fmt_runs(v), size=17, weight="bold", ha="right")
    card.ax.plot([zero, zero], [80, 150], color=t["axis"], lw=px(1.2))

    # Zone pictures
    specs = row_specs(summary)
    rows = [(label, sub) for label, sub, _, _, _ in specs]
    mask = cs.in_zone_mask(XS, ZS, *summary["zone"])

    def cells(i, g):
        return spec_cell(p, specs[i], g, t, mask)

    markers = leak_markers(summary, specs, p)
    whiff_row = next((i for i, sp in enumerate(specs) if sp[4] == "whiff"), None)
    bottom = draw_grid(card, rows, cells, summary["zone"], markers,
                       None if summary["bats"] == "S" else summary["bats"], whiff_row)
    draw_key(card, GRID_LEFT + ROW_LABEL_W, bottom + 44, whiff=whiff_row is not None)

    # Right column: the plan, numbered to the leaks it comes from, then the
    # leaks and the By count table, at the first plan set whose column ends
    # above the trend, measured before anything is drawn
    first = 1 if sum(1 for it in summary["plan_items"] if it["kind"] != "keep") >= 3 else 0
    plan_set = next((s for s in PNG_PLAN_SETS[first:]
                     if plan_column(Measure(), summary, s) <= COLUMN_END), PNG_PLAN_SETS[-1])
    y = plan_column(card, summary, plan_set)
    if y > COLUMN_END:
        print(f"  warning: {summary['name']} right column runs to y={y:.0f}")
    y = BOTTOM_BLOCK
    foot = 1040
    tgt = summary["target_text"] or ""

    def target_end(t_set):
        # the target's last line, which stays as far above the footer's rule as the
        # column's last line does above the trend's
        return y + 36 + (len(textwrap.wrap(tgt, t_set[4], break_on_hyphens=False)) - 1) * t_set[3]

    t_set = next((s for s in PNG_TARGET_SETS if target_end(s) <= foot - 28), PNG_TARGET_SETS[-1])
    if target_end(t_set) > foot - 28:
        print(f"  warning: {summary['name']} target runs to y={target_end(t_set):.0f}")
    tgt_x, trend_w, tgt_size, tgt_line, tgt_chars = t_set
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    card.text(RIGHT_X, y + 16, trend_title(summary["trend"]), size=16, weight="bold")
    draw_trend(card, RIGHT_X + 44, y + 32, trend_w, 46, summary["trend"], league_trend)
    if tgt:
        card.text(RIGHT_X + tgt_x, y + 16, "TARGET", size=12, color="muted", weight="bold")
        card.wrapped(RIGHT_X + tgt_x, y + 36, tgt, tgt_chars, size=tgt_size, line=tgt_line,
                     color="ink2")
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, foot - 24)
    card.wrapped(RIGHT_X, foot - 6, EVIDENCE_LINE, 118, size=12, line=15, color="muted")
    card.text(W - 64, H - 14, f"xChase+ 1.1  ·  Statcast {SEASON}  ·  catcher's view, "
              "each hitter's own zone", size=12, color="muted", ha="right")
    card.save(out_path)


# --------------------------------------------------
# THE PRINTABLE CARD: the web card on two letter-size pages
# --------------------------------------------------
# Page 1 is the card: the plan, with the target and the coach's note for a
# noted hitter beside it, the pictures the leaks are numbered on, the key
# and the leaks.
# Page 2 is the guide in the player's words, the average hitter's
# two-strike picture, the season chart and what fixing a leak paid.

PRINT_W, PRINT_H = 1275, 1650      # letter, 150 px per inch
PRINT_MARGIN = 72
PRINT_END = PRINT_H - 70           # a page's content ends above this; the page footer is under it
PRINT_LABEL_W = 132                # the row names, left of the pictures
PRINT_GAP = 14                     # px between pictures
PRINT_HEAD = 50                    # the count names over the first row
PRINT_MIN_W = 96                   # a picture narrower than this is a layout to fix, not to print
PRINT_PLAN_W = 740                 # page 1's plan column, from the margin; the target and the
PRINT_COL_GAP = 30                 # coach's note stand beside it, this far right, to the margin
PRINT_PLAN_SETS = ((18, 26, 76),   # the plan's size, line and wrap; the tighter second set, as
                   (16, 23, 86))   # wide, only when the first leaves the pictures under PRINT_MIN_W
PRINT_KEEP_CHARS = 100             # the keep line, 15 px, runs to the plan column's edge
PRINT_NOTE_CHARS = 49              # the target and the note, 15 px, fill the right column (each
                                   # wrap the most characters whose widest line over six seasons fits)
PRINT_MARKER_PX = 10.5             # a leak marker's smallest radius, so its number fits inside
PRINT_KEY_CHARS = 196              # the key under the pictures wraps at this many characters

PLAYER_GUIDE = [
    "Red is where you swing at balls more than other hitters do at the same spot and in the "
    "same count. Blue is where you take more than they do. Gray is about average. White means "
    "you haven't seen enough pitches there to say.",
    "The box is your strike zone, seen from the catcher. The line under it is home plate. "
    "Everyone chases more with two strikes, so the comparison is always with hitters in the "
    "same count. Nobody is judged for a two-strike swing everyone makes.",
    "The numbers on the pictures are your biggest leaks, ranked by what your swing choices "
    "cost over a full season, each on the row of pictures its pitches are in ({rows}). Each "
    "plan line is tagged with its leak's number.",
    "The plan is one pitch per line, numbered 1 and 2 in the order to work on them: a take "
    "before two strikes comes first, because it costs nothing in strikeouts, when you have "
    "seen enough of those pitches to trust the number, unless your coaches picked where to "
    "start. A line under them names a bigger leak "
    "or a costly count that comes later. A take rule is "
    "for the pitch that is clearly a ball; each line says how far off the plate the ones you "
    "swung at were, and a pitch that was mostly borderline is one to go over on video with "
    "your coaches, not a take. Keep swinging at strikes.",
    "The target covers every leak on the card, together, in points above the league's chase "
    "rate. Everyone's worst spots look better the next season by themselves, and that is the "
    "numbers settling, not you improving. The second number is where you would land doing "
    "nothing. Under it is a fix. Matching it is not.",
    "The cost of far-off chases is what your choices on pitches at least 4 inches off the "
    "plate cost over 600 plate appearances, compared with an average hitter. Hitters who cut "
    "their leak chasing mostly stopped losing runs; the walks come first, the hits come "
    "later if they come.",
]
GUIDE_ROWS = {"S": "batting left or batting right",
              None: "a leak against right-handers is on the vs RHP row"}


def print_row_specs(summary):
    """The printable card's picture rows: the web card's rows that carry a
    leak, so every number sits on a picture of the pitches it counts, as on
    the web card (a leak named for a pitcher hand on that hand's row, never
    on all pitchers). A switch hitter keeps both sides, labeled, a hitter
    with no leak the all-pitchers row, and a hitter whose problem is
    contact the misses row."""

    specs = row_specs(summary)
    chase = [sp for sp in specs if sp[4] == "chase"]
    if summary["bats"] != "S":
        hands = {lk["hand"] or "all" for lk in summary["leaks"]["all"]} or {"all"}
        chase = [sp for sp in chase if sp[3] in hands]
    return chase + [sp for sp in specs if sp[4] == "whiff"]


def print_key(specs):
    words = ("Red: you chase more than the average hitter at that spot and count. Blue: you take "
             "more. Gray: about average. White: too few pitches to say. Outline: 15 points or more over.")
    if any(sp[4] == "whiff" for sp in specs):
        words += " Misses row: purple, more misses than the average hitter on the same chases; green, fewer."
    return words


class Measure:
    """Stands in for a Card to find where text would end, drawing nothing."""

    class _Axes:
        def add_patch(self, *args, **kwargs):
            pass

    ax = _Axes()
    t = THEMES["light"]

    def text(self, *args, **kwargs):
        pass

    def plan_mark(self, *args, **kwargs):
        pass

    def hline(self, *args, **kwargs):
        pass

    def wrapped(self, x, y, s, width_chars, size=18, line=26, **kwargs):
        return y + len(textwrap.wrap(s, width_chars, break_on_hyphens=False)) * line


def print_cell_w(n_rows, height):
    """One picture's width when n_rows rows and the count names share height px."""

    by_height = (height - PRINT_HEAD - (n_rows - 1) * PRINT_GAP) / n_rows / PANEL_ASPECT
    by_width = (PRINT_W - 2 * PRINT_MARGIN - PRINT_LABEL_W - 3 * PRINT_GAP) / 4
    return min(by_height, by_width)


def print_grid(card, p, summary, specs, markers, top, w, marker_r):
    """The pictures of page 1: a row per spec, each picture w px wide, under
    the count names at top. Returns the pictures' bottom edge and right edge."""

    t = card.t
    mask = cs.in_zone_mask(XS, ZS, *summary["zone"])
    x0 = PRINT_MARGIN + PRINT_LABEL_W
    h = w * PANEL_ASPECT
    names = COUNT_LABELS if w >= 160 else COUNT_SHORT
    for j, g in enumerate(COUNT_GROUPS):
        cx = x0 + j * (w + PRINT_GAP) + w / 2
        card.text(cx, top + 20, names[g], size=16, weight="bold", ha="center")
        card.text(cx, top + 38, COUNT_DETAIL[g], size=12, color="muted", ha="center")
    right = x0 + 4 * w + 3 * PRINT_GAP
    y = top + PRINT_HEAD
    for i, spec in enumerate(specs):
        label, sub, _, _, metric = spec
        if metric == "whiff":
            card.hline(PRINT_MARGIN, right, y - PRINT_GAP / 2, color="axis", lw=1.2)
        ly = card.wrapped(PRINT_MARGIN, y + 18, label, 13, size=15, line=19, weight="bold")
        if sub:
            card.wrapped(PRINT_MARGIN, ly + 2, sub, 19, size=12, line=15, color="muted")
        for j, g in enumerate(COUNT_GROUPS):
            a = card.panel(x0 + j * (w + PRINT_GAP), y, w, h)
            rgb, gap, ev = spec_cell(p, spec, g, t, mask)
            card.zone(a, rgb, summary["zone"], mask, gap, ev, markers.get((i, g), []), marker_r)
        y += h + PRINT_GAP
    return y - PRINT_GAP, right


def print_notes(card, x, y, summary):
    """The target and the coach's note, one under the other in page 1's
    right column, beside the plan. Returns the y under them."""

    notes = [(label, text) for label, text in (("TARGET", summary["target_text"]),
                                               ("COACH'S NOTE, FOR THE STAFF", summary["coach_note"]))
             if text]
    for k, (label, text) in enumerate(notes):
        if k:
            y += 20
        card.text(x, y, label, size=12, color="muted", weight="bold")
        y = card.wrapped(x, y + 24, text, PRINT_NOTE_CHARS, size=15, line=21, color="ink2")
    return y


def print_pages(summary, out_pdf, theme_name="light"):
    from matplotlib.backends.backend_pdf import PdfPages

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    p = df[df["batter"] == summary["id"]]
    switch = summary["bats"] == "S"
    side = (summary["bats"] if not switch
            else max(summary["side_pitches"], key=summary["side_pitches"].get))
    x0, xr = PRINT_MARGIN, PRINT_W - PRINT_MARGIN
    mask = cs.in_zone_mask(XS, ZS, *summary["zone"])
    rank = summary["rank"]
    suffix = "th" if 10 <= rank % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    bats = {"R": "Bats right", "L": "Bats left", "S": "Switch hitter"}[summary["bats"]]
    footer = f"xChase+ 1.1  ·  Statcast {SEASON}  ·  catcher's view, your own strike zone"
    leak_list = summary["leaks"]["all"]

    def header(card, page):
        t = card.t
        card.text(x0, 108, summary["name"], size=42, weight="bold")
        card.text(x0, 144, f"{bats}   ·   {SEASON}   ·   {summary['pa']} PA   ·   "
                  f"xChase+ {summary['xchase_plus']:.0f}, {rank}{suffix} of {summary['of']}",
                  size=16, color="ink2")
        card.text(x0, 172, f"Swings at {summary['chase'] * 100:.0f}% of pitches outside the zone. "
                  f"Hitters on average swing at {summary['chase_league'] * 100:.0f}% of the same "
                  "pitches.", size=16, color="ink2")
        card.text(xr, 92, "COST OF FAR-OFF CHASES", size=12, color="muted", weight="bold", ha="right")
        card.text(xr, 146, f"{summary['runs_at_stake']:.1f}", size=48, weight="bold", ha="right")
        card.text(xr, 172, "runs per 600 PA from your choices on pitches 4+ inches off the plate",
                  size=12, color="ink2", ha="right")
        card.hline(x0, xr, 200)
        card.text(xr, PRINT_H - 36, f"{footer}  ·  page {page} of 2", size=11, color="muted",
                  ha="right")
        return t

    def check_end(y, page):
        # nothing runs into the page footer: the layout fits the pictures
        # to the room the text leaves, so this is a layout bug, not data
        if round(y) > PRINT_END:
            raise SystemExit(f"printable card for {summary['name']}: page {page} runs to "
                             f"y={y:.0f}, past {PRINT_END}")

    with PdfPages(out_pdf) as pdf:
        # ---- page 1: the plan, the pictures it points at, the leaks
        card = Card(theme_name, PRINT_W, PRINT_H)
        t = header(card, 1)
        y = 252
        card.text(x0, y, "What to work on", size=24, weight="bold")
        y += 38

        def plan_block(c, y, plan_set):
            # the plan in its column on the left, the target and the coach's
            # note beside it on the right; the block ends under the longer
            size, line, chars = plan_set
            top = y
            for it in summary["plan_items"]:
                if it["kind"] == "keep":
                    y = c.wrapped(x0 + 24, y, it["text"], PRINT_KEEP_CHARS, size=15, line=21,
                                  color="ink2") + 6
                    continue
                c.plan_mark(x0 + 11, y - 7, it, 11, 13, x0 + PRINT_PLAN_W)
                y = c.wrapped(x0 + 32, y, it["text"], chars, size=size, line=line) + 8
            return max(y, print_notes(c, x0 + PRINT_PLAN_W + PRINT_COL_GAP, top, summary)) + 20

        # Under the pictures, from their bottom edge: the side labels and the
        # key (46 to the key's first line, 16 a line), then 34 to "Biggest
        # leaks", 34 a leak, 30 to the caption and 6 under it.
        specs = print_row_specs(summary)
        key = print_key(specs)
        key_lines = len(textwrap.wrap(key, PRINT_KEY_CHARS, break_on_hyphens=False))
        below = 46 + 16 * key_lines + 34 + 34 * max(len(leak_list), 1) + 30 + 6
        # the pictures take the room the plan leaves; a plan long enough to
        # squeeze them under PRINT_MIN_W is set tighter (Kyle Stowers, 2026)
        plan_set = next((s for s in PRINT_PLAN_SETS
                         if print_cell_w(len(specs), PRINT_END - below - (plan_block(Measure(), y, s) + 54))
                         >= PRINT_MIN_W), PRINT_PLAN_SETS[-1])
        y = plan_block(card, y, plan_set)
        card.hline(x0, xr, y)
        y += 40
        card.text(x0, y, "Where you chase", size=22, weight="bold")
        top = y + 14
        w = print_cell_w(len(specs), PRINT_END - below - top)
        if w < PRINT_MIN_W:
            raise SystemExit(f"printable card for {summary['name']}: {len(specs)} rows of pictures "
                             f"leave {w:.0f} px each, under {PRINT_MIN_W}")
        marker_r = max(0.2, PRINT_MARKER_PX * (XS[-1] - XS[0]) / w)
        markers = leak_markers(summary, specs, p, max(MARKER_GAP, 2.4 * marker_r))
        gb, right = print_grid(card, p, summary, specs, markers, top, w, marker_r)
        draw_legend(card, right - 300, top - 40, "gap")
        if not switch:         # a switch hitter's rows say where inside is
            inside, away = ("Inside", "Away") if side == "R" else ("Away", "Inside")
            card.text(x0 + PRINT_LABEL_W + 4, gb + 20, inside, size=13, color="muted")
            card.text(x0 + PRINT_LABEL_W + w - 4, gb + 20, away, size=13, color="muted", ha="right")
        card.text(right, gb + 20, "catcher's view, to scale", size=13, color="muted", ha="right")
        y = card.wrapped(x0, gb + 46, key, PRINT_KEY_CHARS, size=12, line=16, color="ink2")
        card.hline(x0, xr, y - 4)
        y += 34
        card.text(x0, y, "Biggest leaks", size=22, weight="bold")
        card.text(xr, y, "numbered on the pictures  ·  runs per 600 PA", size=12, color="muted",
                  ha="right")
        if not leak_list:
            y += 34
            card.text(x0, y, "None worth 0.75 runs per 600 PA.", size=16, color="ink2")
        for n, lk in enumerate(leak_list, start=1):
            y += 34
            card.ax.add_patch(Circle((x0 + 12, y - 6), 12, fc=t["surface"], ec=t["ink"], lw=px(1.6)))
            card.text(x0 + 12, y - 5, str(n), size=14, weight="bold", ha="center", va="center")
            card.text(x0 + 34, y, lk["phrase"], size=16)
            card.text(xr - 110, y, f"{lk['rate'] * 100:.0f}% vs {lk['league'] * 100:.0f}%  ·  "
                      f"{lk['chases']} of {lk['pitches']}", size=14, color="ink2", ha="right")
            card.text(xr, y, fmt_runs(lk["choices"]), size=16, weight="bold", ha="right")
        y += 30
        card.text(x0, y, "You vs the average hitter on the same pitches; the runs are what "
                  "the swing choices cost. Ranked by runs; the plan takes up to two, in the order "
                  "to work on them.", size=12, color="muted")
        check_end(y + 6, 1)
        dump_page(card, summary, 1)
        card.save_page(pdf)

        # ---- page 2: how to read it, in the player's words, and the seasons
        card = Card(theme_name, PRINT_W, PRINT_H)
        t = header(card, 2)
        y = 252
        card.text(x0, y, "How to read your card", size=24, weight="bold")
        y += 40
        rows = GUIDE_ROWS["S" if switch else None]
        for n, line in enumerate(PLAYER_GUIDE, start=1):
            card.ax.add_patch(Circle((x0 + 12, y - 6), 12, fc=t["surface"], ec=t["ink"], lw=px(1.6)))
            card.text(x0 + 12, y - 5, str(n), size=13, weight="bold", ha="center", va="center")
            y = card.wrapped(x0 + 36, y, line.format(rows=rows), 100, size=16, line=23) + 12
        y += 4
        card.hline(x0, xr, y)
        y += 40
        title = "What normal looks like, with two strikes"
        if switch:
            title += f", batting {'left' if side == 'L' else 'right'}"
        card.text(x0, y, title, size=22, weight="bold")
        gy = y + 24
        # The season chart under the pictures takes 34 to its rule, 44 to its
        # title and 150 for the chart and its years.
        h = min(340 * PANEL_ASPECT, PRINT_END - (gy + 40) - (34 + 44 + 150))
        w = h / PANEL_ASPECT
        lg = df[(df["stand"] == side) & (df["count_group"] == "two")]
        srf = cs.surface(lg["xq"] / 100, lg["zq_avg"] / 100, lg["is_chase"].to_numpy(float),
                         np.zeros(len(lg)), XS, ZS)
        rate = np.nan_to_num(srf["player_rate"])
        avg_mask = cs.in_zone_mask(XS, ZS, *AVERAGE_ZONE[side])
        a = card.panel(x0, gy + 40, w, h)
        card.zone(a, compose(sequential(rate, t), np.ones_like(rate), t, avg_mask),
                  AVERAGE_ZONE[side], avg_mask)
        card.text(x0 + w / 2, gy + 20, "The average hitter: how often they swing",
                  size=14, weight="bold", ha="center")
        # the leaks this picture holds on page 1 (all pitchers, this side)
        you_row = next((i for i, sp in enumerate(specs)
                        if sp[2] == side and sp[3] == "all" and sp[4] == "chase"), None)
        mine = p[(p["count_group"] == "two") & (p["stand"] == side)]
        srf = player_surface(mine, "chase")
        a = card.panel(x0 + w + 40, gy + 40, w, h)
        card.zone(a, compose(diverging(srf["gap"], t), srf["evidence"], t, mask), summary["zone"],
                  mask, srf["gap"], srf["evidence"], markers.get((you_row, "two"), []))
        card.text(x0 + w + 40 + w / 2, gy + 20, "You: more (red) or less (blue) than that",
                  size=14, weight="bold", ha="center")
        lx = x0 + 2 * w + 80
        draw_legend(card, lx, gy + 60, "rate", "Average hitter's chase rate")
        draw_legend(card, lx, gy + 140, "gap", "You vs the average hitter")
        card.wrapped(lx, gy + 222, "The average hitter chases most with two strikes, below and "
                     "away. Your card only shows where you differ from that.", 34, size=13,
                     line=18, color="ink2")
        y = gy + 40 + h + 34
        card.hline(x0, xr, y)
        y += 44
        card.text(x0, y, trend_title(summary["trend"]), size=22, weight="bold")
        card.text(x0 + 600, y, "Pitches at least 4 inches off the plate: you against every hitter.",
                  size=12, color="muted")
        draw_trend(card, x0 + 48, y + 30, 460, 90, summary["trend"], league_trend)
        card.wrapped(x0 + 600, y + 40, EVIDENCE_LINE, 64, size=14, line=20, color="ink2")
        check_end(y + 150, 2)
        dump_page(card, summary, 2)
        card.save_page(pdf)


def dump_page(card, summary, n):
    """With PRINT_PNG=<dir> in the environment, also save each printable
    page as a PNG there (for checking the layout; PDFs are hard to view)."""

    import os
    d = os.environ.get("PRINT_PNG")
    if d:
        Path(d).mkdir(parents=True, exist_ok=True)
        card.fig.savefig(Path(d) / f"{slug(summary['name'])}_p{n}.png", dpi=DPI,
                         facecolor=card.t["surface"])


GUIDE = [
    "This card shows the raw chase rate of an average hitter: {more} means more swings. "
    "Every player card shows the difference from this instead, in red and blue, so nobody "
    "is judged on a pitch everyone swings at.",
    "Every card is the catcher's view at true scale. The rectangle is that hitter's own "
    "strike zone, set from their height, and the line at the bottom is home plate. A "
    "left-handed batter stands on the right, so their inside is on the right.",
    "On a player card, red is where the player swings more than this average at the same "
    "spot, count and matchup, and blue is where they take more. {avg} is about average.",
    "{none} means too few pitches there to say. An outline marks spots where the player "
    "chases 15 points or more above average.",
    "Numbers on the pictures match the leaks list, ranked by what the swing choices cost per "
    "600 plate appearances. The plan's lines are numbered in the order to work on them, a take "
    "before two strikes first on 20+ pitches (a noted hitter's plan starts where his coach's "
    "note says), each tagged with its leak's number.",
    "Choices is what the swing decisions cost. Contact is what the chases produced compared "
    "with an average hitter's chases. A contact problem needs a different fix.",
    "In the table, far-off means at least 4 inches off the plate, a pitch almost never called "
    "a strike. Misses is how often a chase is a swing and miss.",
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
    steps = [g.replace("{more}", "darker" if theme_name == "light" else "brighter")
             .replace("{avg}", KEY_WORDS[theme_name]["avg"])
             .replace("{none}", "White" if theme_name == "light" else "The background showing through")
             for g in GUIDE]
    for n, s in enumerate(steps, start=1):
        card.ax.add_patch(Circle((RIGHT_X + 12, y - 6), 12, fc=t_surface(card), ec=card.t["ink"],
                                 lw=px(1.6)))
        card.text(RIGHT_X + 12, y - 5, str(n), size=14, weight="bold", ha="center", va="center")
        y = card.wrapped(RIGHT_X + 34, y, s, 96, size=15, line=20) + 8
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
    card.text(RIGHT_X, y + 16, trend_title([], every=True), size=16, weight="bold")
    draw_trend(card, RIGHT_X + 44, y + 32, 360, 46, [], league_trend)
    draw_legend(card, RIGHT_X + 470, y + 36, "rate", "Chase rate at each spot")
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
    pitch_bytes = records.tobytes()

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

    seasons = card_site.write_seasons_js(SEASON)
    default = README_EXAMPLE if any(p["name"] == README_EXAMPLE for p in players) else players[0]["name"]
    data = {
        "season": SEASON, "seasons": seasons, "pitchFile": "pitches.bin", "gridStep": cs.GRID_STEP,
        "xs": XS.tolist(), "zs": ZS.tolist(), "recordBytes": RECORD.itemsize,
        "countGroups": [{"key": g, "label": COUNT_LABELS[g], "detail": COUNT_DETAIL[g]}
                        for g in COUNT_GROUPS],
        "leagueTrend": [[int(y), float(r)] for y, r in league_trend.items()],
        "trendNote": ABS_TREND_NOTE if league_trend.index.max() >= ABS_FIRST_SEASON else "",
        "players": page_players, "references": references,
        "defaultSlug": slug(default), "guide": GUIDE, "evidence": EVIDENCE_LINE,
        "countNote": (GLOSSARY + " Every plate appearance starts at 0-0, so the First pitch "
                      "xwOBA is the whole season's. With a pitcher-hand tab, both sides face that hand."),
        "footer": (f"xChase+ 1.1 · Statcast {SEASON} · {len(players)} qualified hitters. "
                   "xChase+ is what a hitter's chase decisions saved or cost in runs, counting what "
                   "his chases produced: 100 is league average, higher is better. Every picture compares a hitter with the average hitter on pitches at the "
                   "same spot and count; “Same side and hand” also matches batter side and "
                   "pitcher hand. Runs are per 600 plate appearances. Built by step 17 of the "
                   "Chase Leaderboard project."),
    }
    template = (TEMPLATE_DIR / "player_cards.html").read_text()
    math_js = (TEMPLATE_DIR / "card_surfaces.js").read_text()
    payload = json.dumps(to_json_safe(data), ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    page = (template.replace("/*__CARD_MATH__*/", math_js)
            .replace("/*__DATA__*/", payload))
    SEASON_DIR.mkdir(parents=True, exist_ok=True)
    (SEASON_DIR / "index.html").write_text(page)
    (SEASON_DIR / "pitches.bin").write_bytes(pitch_bytes)
    print(f"  wrote player_cards/{SEASON}/index.html ({len(page) / 1e6:.1f} MB, {len(page_players)} hitters) "
          f"and pitches.bin ({len(pitch_bytes) / 1e6:.1f} MB, {len(qualified):,} pitches)")
    newest = max(seasons)
    card_site.write_redirect("index.html", newest, "Chase Decision Cards")
    # the roster's old page, this season's and the root one, into the roster view
    card_site.write_roster_redirect(SEASON_DIR / "teams.html", "index.html")
    card_site.write_roster_redirect(CARDS_DIR / "teams.html", f"{newest}/index.html")
    print(f"  seasons with a page: {', '.join(map(str, seasons))}; player_cards/index.html sends to {newest}, "
          f"teams.html into its roster view")
    return qualified


def check_javascript(qualified):
    """Parse the page's scripts in Node, so a quote or bracket out of place
    in the template stops the build instead of blanking the page; then run
    the page's math on one hitter and compare with Python."""

    node = shutil.which("node")
    if node is None:
        print("  node not found; skipped the JavaScript check")
        return
    page = (SEASON_DIR / "index.html").read_text()
    code = "\n;\n".join(m.group(1) for m in re.finditer(r"<script>(.*?)</script>", page, re.S))
    parse = subprocess.run([node, "-e", "new (require('vm').Script)(require('fs').readFileSync(0, 'utf8'))"],
                           input=code, capture_output=True, text=True)
    if parse.returncode:
        raise SystemExit("The page's JavaScript does not parse (scripts/templates/player_cards.html):\n"
                         + parse.stderr[-800:])
    hitter = next((p for p in players if p["name"] == README_EXAMPLE), players[0])
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
    print(f"  the page's scripts parse; JavaScript matches Python on {hitter['name']}'s two-strike surface "
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


CIRCLED = "①②③"


def write_leak_pitches():
    """Every chased pitch in the noted hitters' leaks, for the video room:
    the date, the pitcher, the count, the pitch, how far off it was."""

    noted = [p for p in players if p["noted"]]
    extra = pd.read_parquet(CLEAN / "baseline_chase_pitches.parquet",
                            columns=keys + ["game_date", "player_name", "pitch_name",
                                            "release_speed", "events"])
    extra = extra[(extra["game_year"] == SEASON) & extra["batter"].isin([p["id"] for p in noted])]
    rows = []
    for p in noted:
        mine = df[df["batter"] == p["id"]].merge(extra, on=keys, how="left")
        for n, lk in enumerate(p["leaks"]["all"], start=1):
            cell = mine[(mine["count_group"] == lk["count_group"]) & (mine["pitch_group"] == lk["pitch_group"])
                        & (mine["region"] == lk["region"]) & (mine["is_chase"] == 1)]
            for r in cell.sort_values(["game_date", "game_pk", "at_bat_number", "pitch_number"]).itertuples():
                rows.append({
                    "player": p["name"], "leak": n, "leak_phrase": lk["phrase"],
                    "date": str(r.game_date)[:10], "pitcher": r.player_name, "pitcher_hand": r.p_throws,
                    # a leak named for a hand counts the other hand's pitches too
                    "from_leak_hand": "" if not lk["hand"] else ("yes" if r.p_throws == lk["hand"] else "no"),
                    "count": r.count_state, "pitch": r.pitch_name, "mph": r.release_speed,
                    "inches_off_zone": round(r.distance_outside_zone * 12, 1),
                    "result": r.description, "pa_result": r.events if isinstance(r.events, str) else "",
                    "game_pk": r.game_pk, "at_bat": r.at_bat_number, "pitch_number": r.pitch_number,
                })
    out = NOTED_DIR / f"leak_pitches_{SEASON}.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"  wrote noted_players/{out.name} ({len(rows)} chased pitches in {len(noted)} hitters' leaks)")


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
        f"`results/xchase/player_cards/{SEASON}/index.html` (hosted at",
        f"[samuelosullivan6-rgb.github.io/ChasePlus](https://samuelosullivan6-rgb.github.io/ChasePlus/results/xchase/player_cards/{SEASON}/index.html),",
        "with a switcher to every other season). Each hitter below also has a printable",
        "two-page card in `print/`: the plan, the target, the coach's note, the pictures the",
        "leaks are numbered on (a leak named for a pitcher hand on that hand's row, as on the",
        "web card) and the leaks, then a guide to the card in the player's own words and the",
        "season chart. Every chased pitch in these hitters'",
        "leaks, with the date, the pitcher, the count, the pitch and how far off it was, is in",
        f"[`leak_pitches_{SEASON}.csv`](leak_pitches_{SEASON}.csv), for the video room. A leak",
        "named for a pitcher hand (\"mostly vs RHP\": that hand threw most of its pitches and",
        "carries most of its extra chases and their cost) counts the other hand's pitches too, as",
        "its rates do; the `from_leak_hand` column marks which are which, so a reel can be cut",
        "to the named hand.",
        "",
        "Each card is drawn from the catcher's view, to scale, around the hitter's own",
        "strike zone; nobody is mirrored, so a left-handed batter's inside is on the right.",
        "It compares the hitter with the average hitter on pitches at the same spot",
        "relative to their zone, in the same count and the same batter-side and",
        "pitcher-hand matchup.",
        "Red is where they swing more, blue where they take more, gray is about average,",
        "and the background shows through where there are too few pitches to say. The",
        "plan is written to the player, one pitch per",
        "line, numbered in the order to work on them (a pitch chased well above the league's",
        "rate before one chased at about it, and a take before two strikes first when it rests on",
        "20 or more pitches, since it costs nothing in strikeouts), each tagged with its leak on",
        "the list, which is ranked by runs; the order can put a smaller leak on the plan ahead of",
        "a bigger one, and a line under the plan then names the bigger one and why it comes",
        "later, as it does a count costing a run or more that no line covers. The",
        "coach's note underneath is for the staff, and names the leak the plan leads with. A",
        "card says where a hitter chases, not why:",
        "the same leak can be pitch recognition, timing or a two-strike approach, and the",
        "drill is different for each, so the card says where to point the camera. For",
        "what a normal card looks like, compare with the average hitter:",
        "",
        picture(f"../player_cards/{SEASON}/reference/average_rhb_light.png",
                f"../player_cards/{SEASON}/reference/average_rhb_dark.png",
                "The average right-handed hitter's chase rate by location and count, with a guide to reading the cards"),
        "",
        f"**{EVIDENCE_QUESTION}** " + EVIDENCE_DETAIL,
        "(Step 16; see the main README for the method.)",
        "",
        "**The target.** Under each plan, how far above the league's chase rate, in points,",
        f"the hitter chased in all of his card's leaks together in {SEASON} (on the backtest's",
        f"scale, so it need not match any one leak's rates), and what the season-to-season line",
        f"predicts for {SEASON + 1} if he changes nothing (step 19, frozen before the season).",
        "Leaks are a hitter's worst-looking spots, so about half of the excess goes away by",
        "itself. A fix is a number under the prediction, not under this season's rate; that is",
        "also how step 20 will score the card. A hitter whose prediction for next season is",
        "about at the league's rate gets no target, and one whose leaks are all video items",
        "gets no number."
        + (f" {SEASON} rates are measured against the ABS box set from the hitter's height, about "
           "3 inches shorter than the zones before, so the trend's last point and the target "
           "are not on the same box as the earlier seasons." if SEASON >= ABS_FIRST_SEASON else ""),
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
                 "pattern repeats across seasons, so a take rule is most of the adjustment; where "
                 "contact may be part of it, the coach's note says so."),
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
                f"Far-off chases cost {p['runs_at_stake']:.1f} runs per 600 PA. "
                f"Choices {fmt_runs(p['choices'])}, contact {fmt_runs(p['contact'])}.",
                "",
                picture(f"cards/{sl}_light.png", f"cards/{sl}_dark.png",
                        f"{p['name']} decision card"),
                "",
                f"[Printable card, two pages (PDF)](print/{sl}.pdf)",
                "",
                "**What to work on**",
                "",
            ]
            for it in p["plan_items"]:
                lines.append(f"{it['step']}. {it['text']} (leak {CIRCLED[it['n'] - 1]})"
                             if it["kind"] == "pitch" else f"- {it['text']}")
            check = count_check_line(p)
            if check:
                lines += ["", f"**Count check.** {check}"]
            if p["target_text"]:
                lines += ["", f"**Target.** {p['target_text']}"]
            lines += ["", f"**Coach's note, for the staff.** {p['coach_note']}", ""]
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
    "players": [{k: p[k] for k in ("id", "name", "team", "teams", "bats", "rank", "of", "pa", "xchase_plus",
                                   "archetype", "noted", "runs_at_stake", "choices", "contact",
                                   "zone", "height_in", "side_pitches", "leaks", "target",
                                   "target_text", "target_beat", "plan_items", "start_with")}
                for p in players]}), ensure_ascii=False))
print(f"  saved card_pitches_{SEASON}.parquet and card_players_{SEASON}.json for step 18")
if not args.data_only:
    qualified_pitches = build_page()
    check_javascript(qualified_pitches)

summary_rows = []
for p in players:
    t = {r["group"]: r for r in p["tables"]["all"]}
    top = p["leaks"]["all"][0] if p["leaks"]["all"] else None
    summary_rows.append({
        "player": p["name"], "batter": p["id"], "team": p["team"], "teams": ", ".join(p["teams"]),
        "bats": p["bats"], "xchase_plus_rank": p["rank"],
        "xchase_plus": round(p["xchase_plus"], 1), "plate_appearances": p["pa"],
        "archetype": p["archetype"], "noted": p["noted"] or "",
        "chase_rate": round(p["chase"], 4), "league_chase_rate_same_pitches": round(p["chase_league"], 4),
        "whiff_per_chase": round(p["whiff"], 4), "league_whiff_per_chase_same_pitches": round(p["whiff_league"], 4),
        "choices_runs_per_600": round(p["choices"], 2), "contact_runs_per_600": round(p["contact"], 2),
        "runs_at_stake_far_off": round(p["runs_at_stake"], 2),
        "two_strike_chase_rate": round(t["two"]["chase"], 4),
        "league_two_strike_chase_rate_same_pitches": round(t["two"]["chase_league"], 4),
        "top_leak": top["phrase"] if top else "",
        "top_leak_runs": round(top["choices"], 2) if top else None,
        "top_leak_count_xwoba": round(top["count_xwoba"], 4) if top else None,
        "top_leak_count_league_xwoba": round(top["count_xwoba_league"], 4) if top else None,
        "top_leak_count_xwoba_shrunk": round(top["count_xwoba_shrunk"], 4) if top else None,
        "top_leak_count_status": top["count_status"] if top else "",
        "top_leak_chase_depth_in": round(top["depth_in"], 1) if top else None,
        "leak_excess_vs_league": round(p["target"]["excess"], 4) if p["target"] else None,
        "leak_excess_predicted_next": round(p["target"]["predicted"], 4) if p["target"] else None,
        "target_text": p["target_text"] or "",
        "start_with": p["start_with"],
        "plan": " ".join(p["plan"]),
    })
cards_csv = pd.DataFrame(summary_rows)
cards_csv.to_csv(CARDS_DIR / f"player_cards_{SEASON}.csv", index=False)
# the roster's columns, sorted the way the roster view opens
roster_csv = cards_csv.assign(slug=cards_csv["player"].map(slug)).sort_values("runs_at_stake_far_off", ascending=False)
roster_csv = roster_csv[["team", "teams", "player", "batter", "slug", "bats", "xchase_plus", "xchase_plus_rank",
                         "plate_appearances", "runs_at_stake_far_off", "choices_runs_per_600",
                         "contact_runs_per_600", "archetype", "noted", "chase_rate",
                         "league_chase_rate_same_pitches", "top_leak", "top_leak_runs",
                         "top_leak_count_status", "top_leak_chase_depth_in", "leak_excess_vs_league",
                         "leak_excess_predicted_next", "target_text", "start_with", "plan"]]
roster_csv.to_csv(CARDS_DIR / f"team_view_{SEASON}.csv", index=False)
print(f"  wrote player_cards/player_cards_{SEASON}.csv and team_view_{SEASON}.csv "
      f"({len(cards_csv)} hitters, {cards_csv['team'].nunique()} teams)")

if args.data_only:
    print("  --data-only: no page, PNGs or noted report")
elif not args.skip_png:
    by_name = {p["name"]: p for p in players}
    for stand, word in (("R", "rhb"), ("L", "lhb")):
        for theme in THEMES:
            league_card(stand, theme, SEASON_DIR / "reference" / f"average_{word}_{theme}.png")
    noted = [p for p in players if p["noted"]]
    for p in noted:
        for theme in THEMES:
            player_card(p, theme, NOTED_DIR / "cards" / f"{slug(p['name'])}_{theme}.png")
    print(f"  drew {len(noted)} noted cards and 2 reference cards, light and dark")
    for p in noted:
        print_pages(p, NOTED_DIR / "print" / f"{slug(p['name'])}.pdf")
    print(f"  wrote {len(noted)} printable cards into noted_players/print/")
    for name in args.print_names:
        if name in by_name:
            print_pages(by_name[name], SEASON_DIR / "print" / f"{slug(name)}.pdf")
        else:
            print(f"  not found, no printable card: {name}")
    extra = players if args.static_all else [by_name[n] for n in args.static if n in by_name]
    unknown = [n for n in args.static if n not in by_name]
    if unknown:
        print(f"  not found, skipped: {unknown}")
    for p in extra:
        for theme in THEMES:
            player_card(p, theme, SEASON_DIR / "static" / f"{slug(p['name'])}_{theme}.png")
    if extra:
        print(f"  drew {len(extra)} more cards into player_cards/{SEASON}/static/")
    if NOTES:
        write_leak_pitches()
        write_noted_report()
    else:
        print(f"  no noted report: the coach's notes are for {NOTED_SEASON}")
