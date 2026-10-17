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
    line from the leaks, in the order to work on them (a take before two
    strikes first, since it costs nothing in strikeouts; two-strike
    takes after; a pitch the hitter chases at the league's rate explains
    why it is there; a borderline pitch is a video item, not a take),
    then a line that says to keep swinging at strikes. When no single
    pitch explains the loss, a first line says so. A hitter whose
    problem is contact reads that first. Every sentence is written from
    the count table next to it, so a plan is empty only when that table
    agrees. For the 17 noted hitters the coach's note names the leak the
    plan must lead with, so the player and the staff start in the same
    place. At the foot of the card, what step 16 found when hitters
    fixed their leaks, in one plain sentence.

The leak rule, the labels and the choices / contact split come from
leak_rules.py, which steps 15 and 16 share. The coach's notes for the 17
noted hitters are in coach_notes.py, each next to the facts it states;
every fact is checked against the data before a card is drawn, and the
run stops if one no longer holds.

Hitters whose problem is contact rather than choices (the execution-led
group from step 13) also get a whiff picture: how often they miss when
they do chase, against the league on the same pitches.

OUTPUTS
  results/xchase/player_cards/<season>/index.html
      every qualified hitter plus the average right- and left-handed
      hitter, interactive. One page per season; the season switcher on
      the page moves between them with the hitter kept in the URL.
  results/xchase/player_cards/<season>/pitches.bin
      the season's pitches, one 9-byte record each, which the page loads
      when it opens. Kept out of the HTML so that a change to the wording
      re-commits the page (about 2.5 MB) and not the pitches. Browsers
      will not load it from a file:// address: open the page from the
      hosted site or a local web server (python -m http.server from the
      project folder).
  results/xchase/player_cards/<season>/reference/*.png
      the average right- and left-handed hitter, for comparison
  results/xchase/player_cards/index.html and seasons.js
      the old address, sent on to the newest season's page with the
      hitter kept, and the list of seasons with a page (card_site.py)
  results/xchase/noted_players/
      README.md, a card and a short write-up for the 17 hitters named in
      the step 12 and 13 reports, and cards/*.png (light and dark); for
      2026 only, the season the coach's notes describe
  results/xchase/player_cards/player_cards_<season>.csv
      one row per hitter: the numbers behind the header and plan

Each leak also says how far off the zone the chased pitches were (the
median, in inches), so "let it go" is never read as "take borderline
pitches". When step 19 has frozen this season's predictions, each card
carries its target: how far above the league the hitter chased in his
leaks, and what the line expects next season with no change, since
leaks shrink on their own. Beating that number is what counts as a fix.

The 17 noted hitters also get a printable card: a two-page letter-size
PDF in noted_players/print/ with the plan, the target, the all-pitchers
pictures and the leaks on page 1, and on page 2 a guide to the card in
the player's own words next to the average hitter's two-strike picture.
--print NAME [NAME ...] draws the same for any hitter into
player_cards/<season>/print/ (not committed).

Options: --season (default 2026), --static NAME [NAME ...] to also draw
PNG cards for any hitters by name, --static-all to draw every hitter
(into player_cards/<season>/static/, which is not committed), --print NAME
[NAME ...] for printable PDFs, --data-only to
write just the card data (card_players_<season>.json, the CSV) for an
earlier season, so step 19 can freeze it retrospectively and step 20
score it. The coach's notes are for 2026 only.

Needs steps 04 (--expected-contact), 13, 15 and 16 first. Step 22 runs
this step and step 21 for every season, so the pages agree.
"""

import argparse
import base64
import json
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
import card_site  # noqa: E402

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
            # the shrunk verdict exists for all pitchers only
            "status": (cc.status if cc is not None and isinstance(cc.status, str) else None),
        })
    return rows


def leaks(p, scale, batter):
    out = []
    cells = lr.leak_cells(p, scale, "e_match").head(lr.LEAK_TOP)
    for lk in cells.itertuples():
        s = p[(p["count_group"] == lk.count_group) & (p["pitch_group"] == lk.pitch_group)
              & (p["region"] == lk.region)]
        rhp = (s["p_throws"] == "R").mean()
        hand = "R" if rhp >= HAND_RHP_SHARE else ("L" if rhp <= HAND_LHP_SHARE else None)
        chased = s[s["is_chase"] == 1]
        side = chased["stand"].mode().iloc[0]
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
            "side": side, "x": float(on_side["xd"].median()), "z": float(on_side["zd"].median()),
            # how far off the zone the chased pitches were, so the plan can say it
            "depth_in": float(chased["distance_outside_zone"].median() * 12),
            "count_xwoba": cc.xwoba, "count_xwoba_league": cc.league_xwoba,
            "count_xwoba_shrunk": cc.xwoba_shrunk, "count_status": cc.status,
        })
    return out


def hand_phrase(lk):
    return HAND_WORDS[lk["hand"]]


def leak_cell(lk):
    return (lk["count_group"], lk["pitch_group"], lk["region"])


def leak_phrase(lk, short=False):
    """The leak's name, used verbatim in the list, the roster and the
    report: "Two strikes vs RHP, breaking balls away"."""

    group = (COUNT_SHORT if short else COUNT_LABELS)[lk["count_group"]]
    return f"{group}{HAND_SHORT[lk['hand']]}, {LEAK_PITCH[lk['pitch_group']]} {LEAK_REGION[lk['region']]}"


GROUP_WORDS_SHORT = {"first": "On the first pitch", "ahead": "When you're ahead",
                     "even": "At 0-1 or 1-1", "two": "With two strikes"}


CLEARLY_OFF_IN = 4              # a take rule needs the chased pitches typically this far
                                # off: the card's own far-off line (0.35 ft). Under it, a
                                # leak is a video item, since a ball off the edge is a
                                # called strike often enough with two strikes.


# The plan: the pitch lines come from the leaks, in the order to work on
# them, not the order of their runs: a take before two strikes first (it
# costs nothing in strikeouts and the league rate there is low), two-strike
# takes after, and a borderline pitch (a video item, not a take) never
# ahead of a take. For a noted hitter the coach's note names the leak to
# lead with. A pitch line quotes the hitter's chase rate against the
# league's only when the two print well apart; otherwise it says which
# counts the extra swings came in and what they cost. Around the pitch
# lines: a framing line when the loss is spread thin, the contact line
# first for a hitter whose problem is contact, and a closing line that says
# to keep swinging at strikes. "Nothing stands out" is said only when the
# count table agrees.
PLAN_LINES = 2                  # pitch lines in a plan
RATE_GAP_MIN_PTS = 5            # a pitch line quotes the two chase rates only
                                # when they print this many points apart
WHIFF_GAP_MIN_PTS = 5           # the contact line quotes the miss rate only when it
                                # is this far above the league's
COSTLY_COUNT_RUNS = 1.0         # a count group costing this much is named
SPREAD_MIN_RUNS = 3.0           # a choices loss this big...
SPREAD_SHARE = 0.25             # ...that the plan's pitches cover less than a
                                # quarter of gets the framing line first

COUNT_PHRASES = {"first": "on the first pitch", "ahead": "when you're ahead in the count",
                 "even": "at 0-1 or 1-1", "two": "with two strikes"}


def join_words(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def runs_phrase(runs):
    n = round(runs)
    return f"{n:.0f} run" + ("" if n == 1 else "s")


def chases_more(row):
    return row["chase"] is not None and row["chase"] >= row["chase_league"] + 0.01


def rate_gap(lk):
    """The gap as it prints, so the line never shows the same rounded rate
    for the hitter and the league."""

    return int(f"{lk['rate'] * 100:.0f}") - int(f"{lk['league'] * 100:.0f}")


def rate_clause(lk):
    """Why this pitch is on the plan. The leak rule asks for more chases
    than the league expects in sum, so a costly cell can sit a point or two
    above the league rate when the extra swings come on its costlier
    pitches; there the line says which counts they came in and what they
    cost, instead of two near-identical percentages."""

    mine, theirs = f"{lk['rate'] * 100:.0f}", f"{lk['league'] * 100:.0f}"
    if rate_gap(lk) >= RATE_GAP_MIN_PTS:
        return f"You swung at {mine}% of them; hitters on average swing at {theirs}%."
    where = (f" at {join_words(lk['excess_counts'])}" if lk["excess_counts"]
             else " on the costlier pitches")
    return (f"You swung at these about as often as other hitters do, but more of yours "
            f"came{where}, and over a season they cost you {-lk['choices']:.1f} runs.")


def pitch_line(lk, view="all"):
    """One pitch, written to the player. On a pitcher-hand tab the hand is
    the tab's, so the line does not repeat it."""

    hand = hand_phrase(lk) if view == "all" else ""
    opener = (GROUP_WORDS_SHORT if hand else GROUP_WORDS)[lk["count_group"]]
    what = f"{PITCH_WORDS[lk['pitch_group']]} {REGION_WORDS[lk['region']]}"
    if lk["depth_in"] < CLEARLY_OFF_IN:
        return (f"{opener}{hand}, {what} are one for the video room, not a take rule. "
                f"{rate_clause(lk)} Most of the ones you swung at were within a ball of the zone.")
    return (f"{opener}{hand}, let {what} go. {rate_clause(lk)} The ones you swung at were "
            f"typically {lk['depth_in']:.0f} inches off the zone.")


def plan_pitch_items(leak_list, start=None):
    """Which leaks make the plan, in the order to work on them."""

    items = list(enumerate(leak_list, start=1))
    lead = [it for it in items if start and leak_cell(it[1]) == tuple(start)]
    rest = [it for it in items if it not in lead]
    rest.sort(key=lambda it: (it[1]["count_group"] == "two", it[1]["choices"]))
    ordered = sorted(lead + rest, key=lambda it: it[1]["depth_in"] < CLEARLY_OFF_IN)
    return ordered[:PLAN_LINES]


def productive_line(rows, costly, contact):
    """The costly counts are counts where the hitter's chases have produced
    more than his choices cost (the leak rule never names such a pitch)."""

    cost = sum(-rows[g]["choices"] for g in costly)
    where = join_words([COUNT_PHRASES[g] for g in costly])
    if all(chases_more(rows[g]) for g in costly):
        what = f"You chase more than most hitters {where}"
        if len(costly) == 1:
            r = rows[costly[0]]
            what += f" ({r['chase'] * 100:.0f}% against {r['chase_league'] * 100:.0f}%)"
    else:
        what = f"Your chase choices cost {runs_phrase(cost)} a season {where}"
    return (f"Nothing to change. {what}, but those swings have paid: {contact:.0f} runs more "
            "than an average hitter's chases, more than the extra swings cost.")


def spread_line(rows, loss, contact, costly, n_pitches):
    """No one pitch explains the loss: say so without denying the pitch
    lines under it. The rates in each count are in the table beside the
    plan, so the line does not repeat them. A hitter whose chases produce
    more than his choices cost, with no pitch worth a take rule, is told
    so instead."""

    if (n_pitches == 0 and contact > 0 and contact >= loss and costly
            and contact >= sum(-rows[g]["choices"] for g in costly)):
        return productive_line(rows, costly, contact)
    neg = [g for g in COUNT_GROUPS if rows[g]["choices"] < 0]
    if len(neg) == 4:
        where = "across every count"
    elif len(neg) == 1:
        where = f"nearly all of it {COUNT_PHRASES[neg[0]]}"
    else:
        where = join_words([COUNT_PHRASES[g] for g in neg]) + " rather than in one spot"
    cost = f"Your chase choices cost {runs_phrase(loss)} a season, {where}"
    if n_pitches > 1:
        return f"{cost}; the two pitches below are the biggest pieces of it. Start with the first."
    if n_pitches == 1:
        return f"{cost}; the pitch below is the biggest piece of it. Start there."
    worst = min(COUNT_GROUPS, key=lambda g: rows[g]["choices"])
    line = f"No single pitch here is a clear take. {cost}; the count table shows where."
    if rows[worst].get("status") != "productive":
        line += f" Start {COUNT_PHRASES[worst]}, where it costs the most."
    return line


def fallback_line(rows, costly):
    """What the plan says when no leak makes it."""

    choices, contact = rows["total"]["choices"], rows["total"]["contact"]
    if not costly:
        return ("Nothing stands out. Your chase choices are about league average"
                + (" or better" if choices >= 0 else "") + " in every count.")
    cost = sum(-rows[g]["choices"] for g in costly)
    if contact > 0 and contact >= cost and contact >= -choices:
        return productive_line(rows, costly, contact)
    level = "better than average" if choices >= 1 else "about average"
    where = join_words([COUNT_PHRASES[g] for g in costly])
    return (f"No single pitch stands out. Your chase choices are {level} overall "
            f"({choices:+.1f} runs a season); you give back about {runs_phrase(cost)} "
            f"a season {where}.")


def contact_line(summary, only):
    """For a hitter whose loss is contact more than choices. It quotes the
    miss rate only when that is the evidence; otherwise what the chases
    produced, which is what put him in this group."""

    gap = (summary["whiff"] - summary["whiff_league"]) * 100
    head = "Your issue is contact, not choices" if only else "Your bigger issue is contact"
    if gap >= WHIFF_GAP_MIN_PTS:
        why = (f"you miss on {summary['whiff'] * 100:.0f}% of your chases, against "
               f"{summary['whiff_league'] * 100:.0f}% for other hitters on the same pitches")
    else:
        why = ("you miss about as often as other hitters do, but what you hit on a chase goes "
               f"nowhere: over a season your chases cost you {runs_phrase(-summary['contact'])} more "
               "than an average hitter's would")
    return (f"{head}: {why}. So with two strikes, a pitch that is clearly off is a take even "
            "when you could reach it.")


def keep_line(summary, n_pitches):
    """Every other line is a take; this one says what to keep doing."""

    only = ("The only change on this card is the pitch above." if n_pitches == 1
            else "The only changes on this card are the pitches above.")
    if summary["fastball_choices"] >= 1:
        return f"Keep swinging at strikes; your fastball decisions are a strength. {only}"
    return f"Keep swinging at strikes. {only}"


def plan_items(leak_list, summary, table, view="all", start=None):
    """The plan for one view (all pitchers, or one pitcher hand) as a list
    of items: kind (pitch / frame / contact / keep / fallback), the leak's
    number and cell for a pitch line, and the text."""

    rows = {r["group"]: r for r in table}
    loss = -rows["total"]["choices"]
    costly = [g for g in COUNT_GROUPS if rows[g]["choices"] <= -COSTLY_COUNT_RUNS]
    chosen = plan_pitch_items(leak_list, start)
    items = [{"kind": "pitch", "n": n, "cell": leak_cell(lk), "text": pitch_line(lk, view)}
             for n, lk in chosen]
    named = sum(-lk["choices"] for _, lk in chosen)
    if loss >= SPREAD_MIN_RUNS and named < SPREAD_SHARE * loss:
        items.insert(0, {"kind": "frame", "n": None, "cell": None,
                         "text": spread_line(rows, loss, rows["total"]["contact"], costly, len(chosen))})
    if summary["archetype"] == "execution-led":
        items.insert(0, {"kind": "contact", "n": None, "cell": None,
                         "text": contact_line(summary, only=not items)})
    if not items:
        items.append({"kind": "fallback", "n": None, "cell": None, "text": fallback_line(rows, costly)})
    if chosen:
        items.append({"kind": "keep", "n": None, "cell": None, "text": keep_line(summary, len(chosen))})
    return items


def plan_lines(leak_list, summary, table, view="all", start=None):
    return [it["text"] for it in plan_items(leak_list, summary, table, view, start)]


def start_with(items, leak_list):
    """The roster's one line: the first pitch line's instruction, with the
    numbers that make the case."""

    first = next((it for it in items if it["kind"] == "pitch"), None)
    if first is None:
        return ""
    lk = leak_list[first["n"] - 1]
    clause = first["text"].split(". ")[0].rstrip(".")
    depth = (f"{lk['depth_in']:.0f} in off" if lk["depth_in"] >= CLEARLY_OFF_IN
             else "within a ball of the zone")
    return f"{clause} ({lk['rate'] * 100:.0f}% vs {lk['league'] * 100:.0f}%, {depth})"


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
    frozen_leaks = {b: set(map(tuple, g[lr.LEAK_CELL].itertuples(index=False)))
                    for b, g in frozen[frozen["row"] != "hitter"].groupby("batter")}
    for r in frozen[(frozen["row"] == "hitter") & (frozen["leaks"] > 0)].itertuples():
        TARGETS[int(r.batter)] = {
            "season": SEASON, "next_season": SEASON + 1,
            "excess": float(getattr(r, f"excess_{SEASON}")),
            "predicted": float(getattr(r, f"predicted_excess_{SEASON + 1}")),
            "cells": frozen_leaks.get(int(r.batter), set()),
            "out_of_sample": str(getattr(r, "out_of_sample", "yes")),
        }

TARGET_MIN_PTS = 2              # no target when the no-change forecast rounds to this or less


def target_text(summary):
    """The target as one sentence, the same on every surface: this
    season's leak chasing above the league, what the frozen line expects
    next season with no change, and that only below that counts. None
    when the hitter has no frozen target; a different sentence when the
    forecast is already at the league's rate."""

    t = summary["target"]
    if not t:
        return None
    if round(t["predicted"] * 100) <= TARGET_MIN_PTS:
        if summary["archetype"] == "execution-led":
            return ("No chase target here: in these spots you are already about at the "
                    "league's rate, and the number to move is contact on chases, which this "
                    "card does not score.")
        return "No target: in these spots you are already about at the league's rate."
    return (f"In these spots you chased {t['excess'] * 100:.0f} points above the league in "
            f"{t['season']}. Those spots get better on their own, so with no change you'd be "
            f"about {t['predicted'] * 100:.0f} in {t['next_season']}. Under "
            f"{t['predicted'] * 100:.0f} is a fix.")


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
        "noted": NOTES.get(row["player"], NO_NOTE)[0],
        "coach_note": NOTES.get(row["player"], NO_NOTE)[1],
        "note_start": NOTES.get(row["player"], NO_NOTE)[2],
        "fastball_choices": float(p.loc[p["pitch_group"] == "fastball", "choices"].sum() * scale),
    }
    summary["tables"] = {h: count_table(hand_view(p, h), scale, bid, h) for h in HANDS}
    summary["leaks"] = {h: leaks(hand_view(p, h), scale, bid) for h in HANDS}
    for h in HANDS:
        for lk in summary["leaks"][h]:
            lk["phrase"] = leak_phrase(lk)
    summary["plan_items"] = plan_items(summary["leaks"]["all"], summary, summary["tables"]["all"],
                                       start=summary["note_start"])
    summary["plan"] = [it["text"] for it in summary["plan_items"]]
    summary["start_with"] = start_with(summary["plan_items"], summary["leaks"]["all"])
    # the same plan for one pitcher hand (the page shows it on the hand tabs;
    # for a switch hitter the hand tab is also his side of the plate)
    summary["plan_items_by_hand"] = {h: plan_items(summary["leaks"][h], summary, summary["tables"][h], view=h)
                                     for h in ("R", "L")}
    summary["plan_by_hand"] = {h: [it["text"] for it in summary["plan_items_by_hand"][h]]
                               for h in ("R", "L")}
    target = TARGETS.get(bid)
    cells = {(lk["count_group"], lk["pitch_group"], lk["region"]) for lk in summary["leaks"]["all"]}
    summary["target"] = ({k: target[k] for k in ("season", "next_season", "excess", "predicted",
                                                   "out_of_sample")}
                         if target and target["cells"] == cells else None)
    summary["target_text"] = target_text(summary)
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
    stale = sum(1 for p in players if p["id"] in TARGETS and not p["target"])
    print(f"  targets from {PRED_FILE.name}: {with_target} hitters"
          + (f"; {stale} whose frozen leaks are not the card's leaks (no target shown)"
             if stale else ""))
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
    def __init__(self, theme_name, w=None, h=None):
        self.t = THEMES[theme_name]
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

    def hline(self, x0, x1, y, color="hair", lw=1):
        self.ax.plot([x0, x1], [y, y], color=self.t[color], lw=px(lw), solid_capstyle="butt")

    def panel(self, x, y, w, h):
        a = self.fig.add_axes([x / self.w, 1 - (y + h) / self.h, w / self.w, h / self.h])
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

    def save_page(self, pdf):
        pdf.savefig(self.fig, facecolor=self.t["surface"])
        plt.close(self.fig)


PANEL_ASPECT = (ZS[-1] - ZS[0]) / (XS[-1] - XS[0])
GRID_LEFT, GRID_TOP = 64, 196
GRID_BOTTOM = 960               # the pictures end here; the key sits under them
BOTTOM_BLOCK = 896              # y where the trend + target block starts
ROW_LABEL_W = 118
RIGHT_X, RIGHT_W = 1086, 770


def draw_grid(card, rows, cells, zone, markers=None, orient=None, whiff_row=None):
    """rows: list of (label, sublabel). cells(row_index, group) -> (rgb, gap, evidence).
    markers: {(row_index, group): [(number, (x, z)), ...]}. orient: the side the
    batter stands on ("R" or "L") for the Inside / Away labels, or None.
    whiff_row: the index of the misses row, drawn apart from the chase rows."""

    n = len(rows)
    avail_h = GRID_BOTTOM - (GRID_TOP + 46)
    w = min(196, (avail_h - (n - 1) * 14) / n / PANEL_ASPECT)
    h = w * PANEL_ASPECT
    x0 = GRID_LEFT + ROW_LABEL_W
    labels = COUNT_LABELS if w >= 165 else COUNT_SHORT
    if orient:
        side = "left" if orient == "R" else "right"
        card.text(GRID_LEFT, GRID_TOP - 6, f"Catcher's view, to scale. Inside is on the {side}.",
                  size=13, color="muted")
    for j, g in enumerate(COUNT_GROUPS):
        cx = x0 + j * (w + 14) + w / 2
        card.text(cx, GRID_TOP + 18, labels[g], size=19 if w >= 165 else 17, weight="bold", ha="center")
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


def draw_key(card, x, y, whiff=False):
    """The color key, directly under the pictures: the ramp and the words."""

    draw_legend(card, x, y, "gap")
    words = ("Blue: takes more than the average hitter at that spot and count. Red: chases more. "
             "Gray: about average. White: too few pitches to say. Outline: 15 points or more over.")
    if whiff:
        words += " Misses row: purple, more misses than the average hitter on the same chases; green, fewer."
    card.wrapped(x + 330, y + 10, words, 100, size=12, line=15, color="ink2")


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
    if not league_only:
        y += 24
        y = card.wrapped(x, y, GLOSSARY, 132, size=12, line=15, color="muted") - 15
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
    if summary["archetype"] == "execution-led":
        side = summary["bats"] if summary["bats"] != "S" else max(
            summary["side_pitches"], key=summary["side_pitches"].get)
        rows.append(("Misses on chases", "swing-and-miss per chase, vs the average hitter: "
                     "purple more, green fewer", side, "all", "whiff"))
    return rows


MARKER_GAP = 0.5                # ft between marker centers on one picture


def place_marker(spot, taken):
    """The marker's spot, nudged until it is clear of the others on the picture."""

    for dx, dz in ((0, 0), (0.5, 0), (-0.5, 0), (0, -0.5), (0, 0.5), (0.5, -0.5), (-0.5, -0.5)):
        cand = spot + np.array([dx, dz])
        if all(np.hypot(*(cand - np.array(o))) >= MARKER_GAP for o in taken):
            return cand
    return spot


def leak_markers(summary, specs):
    """Numbered leak markers: on the row of the pitcher hand the leak names,
    or the first row showing that leak's side."""

    markers = {}
    for n, lk in enumerate(summary["leaks"]["all"], start=1):
        hand = lk["hand"] or "all"
        row = next((i for i, sp in enumerate(specs)
                    if sp[2] == lk["side"] and sp[3] == hand and sp[4] == "chase"), None)
        if row is None:
            row = next((i for i, sp in enumerate(specs) if sp[2] == lk["side"] and sp[4] == "chase"), None)
        if row is None:
            continue
        key = (row, lk["count_group"])
        spot = place_marker(np.array([lk["x"], lk["z"]]), [o for _, o in markers.get(key, [])])
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
        _, _, side, hand, metric = specs[i]
        frame = p[(p["count_group"] == g) & (p["stand"] == side)]
        if hand != "all":
            frame = frame[frame["p_throws"] == hand]
        s = player_surface(frame, metric)
        return (compose(diverging(s["gap"], t, metric), s["evidence"], t, mask),
                s["gap"], s["evidence"])

    markers = leak_markers(summary, specs)
    whiff_row = next((i for i, sp in enumerate(specs) if sp[4] == "whiff"), None)
    bottom = draw_grid(card, rows, cells, summary["zone"], markers,
                       None if summary["bats"] == "S" else summary["bats"], whiff_row)
    draw_key(card, GRID_LEFT + ROW_LABEL_W, bottom + 44, whiff=whiff_row is not None)

    # Right column: the plan, numbered to the leaks it comes from
    y = 214
    card.text(RIGHT_X, y, "What to work on", size=22, weight="bold")
    y += 32
    n_lines = sum(1 for it in summary["plan_items"] if it["kind"] != "keep")
    dense = n_lines >= 3          # a three-line plan is set tighter so the column keeps its place
    size, lead = (15, 19) if dense else (16, 22)
    for it in summary["plan_items"]:
        if it["kind"] == "keep":
            y += 2
            y = card.wrapped(RIGHT_X + 22, y, it["text"], 90, size=13, line=17, color="ink2")
            continue
        if it["kind"] == "pitch":
            card.ax.add_patch(Circle((RIGHT_X + 10, y - 6), 10, fc=t["surface"], ec=t["ink"], lw=px(1.4)))
            card.text(RIGHT_X + 10, y - 5, str(it["n"]), size=12, weight="bold", ha="center", va="center")
        else:
            card.ax.add_patch(Circle((RIGHT_X + 10, y - 6), 4, fc=t["ink"], ec="none"))
        y = card.wrapped(RIGHT_X + 30, y, it["text"], 78, size=size, line=lead) + (2 if dense else 4)
    if summary["coach_note"]:
        y += 4
        card.text(RIGHT_X, y, "COACH'S NOTE, FOR THE STAFF", size=12, color="muted", weight="bold")
        y = card.wrapped(RIGHT_X, y + 19, summary["coach_note"], 98, size=13, line=17, color="ink2")
    y += 18
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    card.text(RIGHT_X, y + 20, "Biggest leaks", size=19, weight="bold")
    card.text(RIGHT_X + RIGHT_W, y + 20, "numbered on the pictures  ·  ranked by runs; the plan "
              "is in the order to work on them", size=12, color="muted", ha="right")
    y += 30
    if not summary["leaks"]["all"]:
        y += 24
        card.text(RIGHT_X, y, "None worth 0.75 runs per 600 PA.", size=16, color="ink2")
    worst = max((abs(lk["choices"]) for lk in summary["leaks"]["all"]), default=1.0)
    for n, lk in enumerate(summary["leaks"]["all"], start=1):
        y += 28
        card.ax.add_patch(Circle((RIGHT_X + 12, y - 6), 12, fc=t["surface"], ec=t["ink"], lw=px(1.6)))
        card.text(RIGHT_X + 12, y - 5, str(n), size=14, weight="bold", ha="center", va="center")
        card.text(RIGHT_X + 34, y, lk["phrase"], size=15)
        # the bar is the run cost, which is what ranks the list
        tx0, tw = RIGHT_X + 466, 84
        card.ax.add_patch(Rectangle((tx0, y - 9), tw, 6, fc=t["hair"], ec="none", zorder=2))
        card.ax.add_patch(Rectangle((tx0, y - 9), tw * abs(lk["choices"]) / worst, 6,
                                    fc=t["ink2"], ec="none", zorder=3))
        card.text(tx0 + tw + 12, y, f"{lk['rate'] * 100:.0f}% vs {lk['league'] * 100:.0f}%  ·  "
                  f"{lk['chases']} of {lk['pitches']}", size=13, color="ink2")
        card.text(RIGHT_X + RIGHT_W, y, fmt_runs(lk["choices"]), size=16, weight="bold",
                  ha="right")
    y += 26
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    y = draw_table(card, RIGHT_X, y + 16, summary["tables"]["all"])
    if y > BOTTOM_BLOCK - 12:
        print(f"  warning: {summary['name']} right column runs to y={y:.0f}")
    y = BOTTOM_BLOCK
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, y - 8)
    card.text(RIGHT_X, y + 16, trend_title(summary["trend"]), size=16, weight="bold")
    draw_trend(card, RIGHT_X + 44, y + 32, 360, 46, summary["trend"], league_trend)
    tgt = summary["target_text"]
    if tgt:
        card.text(RIGHT_X + 470, y + 16, "TARGET", size=12, color="muted", weight="bold")
        card.wrapped(RIGHT_X + 470, y + 36, tgt, 46, size=13, line=17, color="ink2")
    foot = 1040
    card.hline(RIGHT_X, RIGHT_X + RIGHT_W, foot - 24)
    card.wrapped(RIGHT_X, foot - 6, EVIDENCE_LINE, 118, size=12, line=15, color="muted")
    card.text(W - 64, H - 14, f"xChase+ 1.1  ·  Statcast {SEASON}  ·  catcher's view, "
              "each hitter's own zone", size=12, color="muted", ha="right")
    card.save(out_path)


# --------------------------------------------------
# THE PRINTABLE CARD: two letter-size pages for a locker
# --------------------------------------------------

PRINT_W, PRINT_H = 1275, 1650      # letter, 150 px per inch
PRINT_MARGIN = 72

PLAYER_GUIDE = [
    "Red is where you swing at balls more than other hitters do at the same spot and in the "
    "same count. Blue is where you take more than they do. Gray is about average. White means "
    "you haven't seen enough pitches there to say.",
    "The box is your strike zone, seen from the catcher. The line under it is home plate. "
    "Everyone chases more with two strikes, so the comparison is always with hitters in the "
    "same count. Nobody is judged for a two-strike swing everyone makes.",
    "The numbers on the pictures are your biggest leaks, ranked by what your swing choices "
    "cost over a full season. The plan's lines carry the same numbers.",
    "The plan is one pitch per line, in the order to work on them: a take before two strikes "
    "comes first, because it costs nothing in strikeouts. A take rule is for the pitch that "
    "is clearly a ball; each line says how far off the plate the ones you swung at were, and "
    "a pitch that was mostly borderline is marked as one for the video room, not a take. "
    "Keep swinging at strikes.",
    "The target: everyone's worst spots look better the next season by themselves, and that "
    "is the numbers settling, not you improving. The second number is where you would land "
    "doing nothing. Under it is a fix. Matching it is not.",
    "The cost of far-off chases is what your choices on pitches at least 4 inches off the "
    "plate cost over 600 plate appearances, compared with an average hitter. Hitters who cut "
    "their leak chasing mostly stopped losing runs; the walks come first, the hits come "
    "later if they come.",
]


def print_markers(summary, side):
    """Numbered leak markers for the all-pitchers row on one side of the plate."""

    markers = {}
    for n, lk in enumerate(summary["leaks"]["all"], start=1):
        if lk["side"] != side:
            continue
        spot = place_marker(np.array([lk["x"], lk["z"]]),
                            [o for _, o in markers.get(lk["count_group"], [])])
        markers.setdefault(lk["count_group"], []).append((n, tuple(spot)))
    return markers


def print_pages(summary, out_pdf, theme_name="light"):
    from matplotlib.backends.backend_pdf import PdfPages

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    p = df[df["batter"] == summary["id"]]
    side = (summary["bats"] if summary["bats"] != "S"
            else max(summary["side_pitches"], key=summary["side_pitches"].get))
    x0, xr = PRINT_MARGIN, PRINT_W - PRINT_MARGIN
    mask = cs.in_zone_mask(XS, ZS, *summary["zone"])
    rank = summary["rank"]
    suffix = "th" if 10 <= rank % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
    bats = {"R": "Bats right", "L": "Bats left", "S": "Switch hitter"}[summary["bats"]]
    footer = f"xChase+ 1.1  ·  Statcast {SEASON}  ·  catcher's view, your own strike zone"

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

    with PdfPages(out_pdf) as pdf:
        # ---- page 1: the plan, the pictures, the leaks
        card = Card(theme_name, PRINT_W, PRINT_H)
        t = header(card, 1)
        y = 252
        card.text(x0, y, "What to work on", size=24, weight="bold")
        y += 38
        for it in summary["plan_items"]:
            if it["kind"] == "keep":
                y = card.wrapped(x0 + 24, y, it["text"], 96, size=15, line=21, color="ink2") + 6
                continue
            if it["kind"] == "pitch":
                card.ax.add_patch(Circle((x0 + 11, y - 7), 11, fc=t["surface"], ec=t["ink"], lw=px(1.5)))
                card.text(x0 + 11, y - 6, str(it["n"]), size=13, weight="bold", ha="center", va="center")
            else:
                card.ax.add_patch(Circle((x0 + 11, y - 7), 4.5, fc=t["ink"], ec="none"))
            y = card.wrapped(x0 + 32, y, it["text"], 86, size=18, line=26) + 8
        if summary["target_text"]:
            y += 8
            card.text(x0, y, "TARGET", size=12, color="muted", weight="bold")
            y = card.wrapped(x0, y + 24, summary["target_text"], 92, size=16, line=22, color="ink2")
        y += 26
        card.hline(x0, xr, y)
        y += 42
        card.text(x0, y, "Where you chase, all pitchers", size=22, weight="bold")
        card.text(xr, y, "red: more than the average hitter at that spot and count; blue: less",
                  size=12, color="muted", ha="right")
        gy = y + 16
        gap = 16
        w = (xr - x0 - 3 * gap) / 4
        h = w * PANEL_ASPECT
        markers = print_markers(summary, side)
        for j, g in enumerate(COUNT_GROUPS):
            left = x0 + j * (w + gap)
            card.text(left + w / 2, gy + 20, COUNT_LABELS[g], size=16, weight="bold", ha="center")
            card.text(left + w / 2, gy + 38, COUNT_DETAIL[g], size=12, color="muted", ha="center")
            frame = p[(p["count_group"] == g) & (p["stand"] == side)]
            srf = player_surface(frame, "chase")
            rgb = compose(diverging(srf["gap"], t), srf["evidence"], t, mask)
            a = card.panel(left, gy + 48, w, h)
            card.zone(a, rgb, summary["zone"], mask, srf["gap"], srf["evidence"], markers.get(g, []))
        gb = gy + 48 + h
        inside, away = ("Inside", "Away") if side == "R" else ("Away", "Inside")
        card.text(x0 + 4, gb + 20, inside, size=13, color="muted")
        card.text(x0 + w - 4, gb + 20, away, size=13, color="muted", ha="right")
        card.text(xr, gb + 20, "catcher's view, to scale", size=13, color="muted", ha="right")
        y = gb + 64
        card.text(x0, y, "Biggest leaks", size=22, weight="bold")
        card.text(xr, y, "numbered on the pictures  ·  runs per 600 PA", size=12, color="muted",
                  ha="right")
        if not summary["leaks"]["all"]:
            y += 34
            card.text(x0, y, "None worth 0.75 runs per 600 PA.", size=16, color="ink2")
        for n, lk in enumerate(summary["leaks"]["all"], start=1):
            y += 34
            card.ax.add_patch(Circle((x0 + 12, y - 6), 12, fc=t["surface"], ec=t["ink"], lw=px(1.6)))
            card.text(x0 + 12, y - 5, str(n), size=14, weight="bold", ha="center", va="center")
            card.text(x0 + 34, y, lk["phrase"], size=16)
            card.text(xr - 110, y, f"{lk['rate'] * 100:.0f}% vs {lk['league'] * 100:.0f}%  ·  "
                      f"{lk['chases']} of {lk['pitches']}", size=14, color="ink2", ha="right")
            card.text(xr, y, fmt_runs(lk["choices"]), size=16, weight="bold", ha="right")
        y += 30
        card.text(x0, y + 14, "You vs the average hitter on the same pitches; the runs are what "
                  "the swing choices cost. Ranked by runs; the plan is in the order to work on them.",
                  size=12, color="muted")
        y += 56
        card.hline(x0, xr, y)
        y += 44
        card.text(x0, y, trend_title(summary["trend"]), size=22, weight="bold")
        card.text(x0 + 560, y, "Pitches at least 4 inches off the plate: you against every hitter.",
                  size=12, color="muted")
        draw_trend(card, x0 + 48, y + 30, 460, 90, summary["trend"], league_trend)
        draw_legend(card, x0 + 600, y + 40, "gap", "Chases vs the average hitter, same spot and count")
        card.text(x0 + 600, y + 96, "Blue: you take more. Red: you chase more. Gray: about average.",
                  size=13, color="ink2")
        card.text(x0 + 600, y + 116, "White: too few pitches to say. Outline: 15 points or more.",
                  size=13, color="ink2")
        card.wrapped(x0, PRINT_H - 92, EVIDENCE_LINE, 150, size=11, line=14, color="muted")
        dump_page(card, summary, 1)
        card.save_page(pdf)

        # ---- page 2: how to read it, in the player's words
        card = Card(theme_name, PRINT_W, PRINT_H)
        t = header(card, 2)
        y = 252
        card.text(x0, y, "How to read your card", size=24, weight="bold")
        y += 40
        for n, line in enumerate(PLAYER_GUIDE, start=1):
            card.ax.add_patch(Circle((x0 + 12, y - 6), 12, fc=t["surface"], ec=t["ink"], lw=px(1.6)))
            card.text(x0 + 12, y - 5, str(n), size=13, weight="bold", ha="center", va="center")
            y = card.wrapped(x0 + 36, y, line, 100, size=16, line=23) + 12
        y += 16
        card.hline(x0, xr, y)
        y += 42
        card.text(x0, y, "What normal looks like, with two strikes", size=22, weight="bold")
        gy = y + 24
        w = 340
        h = w * PANEL_ASPECT
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
        mine = p[(p["count_group"] == "two") & (p["stand"] == side)]
        srf = player_surface(mine, "chase")
        a = card.panel(x0 + w + 40, gy + 40, w, h)
        card.zone(a, compose(diverging(srf["gap"], t), srf["evidence"], t, mask), summary["zone"],
                  mask, srf["gap"], srf["evidence"], markers.get("two", []))
        card.text(x0 + w + 40 + w / 2, gy + 20, "You: more (red) or less (blue) than that",
                  size=14, weight="bold", ha="center")
        lx = x0 + 2 * w + 80
        draw_legend(card, lx, gy + 60, "rate", "Average hitter's chase rate")
        draw_legend(card, lx, gy + 140, "gap", "You vs the average hitter")
        card.wrapped(lx, gy + 222, "The average hitter chases most with two strikes, below and "
                     "away. Your card only shows where you differ from that.", 34, size=13,
                     line=18, color="ink2")
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
    "spot, count and matchup, and blue is where they take more. Gray is about average.",
    "White means too few pitches there to say. An outline marks spots where the player "
    "chases 15 points or more above average.",
    "Numbers on the pictures match the leaks list, ranked by what the swing choices cost per "
    "600 plate appearances. The plan is in the order to work on them: a take before two "
    "strikes first.",
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
        "players": page_players, "references": references,
        "defaultSlug": slug(default), "guide": GUIDE, "evidence": EVIDENCE_LINE,
        "countNote": GLOSSARY + " With a pitcher-hand tab, both sides face that hand.",
        "footer": (f"xChase+ 1.1 · Statcast {SEASON} · {len(players)} qualified hitters. "
                   "Every picture compares a hitter with the average hitter on pitches at the "
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
    print(f"  seasons with a page: {', '.join(map(str, seasons))}; player_cards/index.html sends to {newest}")
    return qualified


def check_javascript(qualified):
    """Run the page's math in Node on one hitter and compare with Python."""

    node = shutil.which("node")
    if node is None:
        print("  node not found; skipped the JavaScript check")
        return
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
    print(f"  JavaScript matches Python on {hitter['name']}'s two-strike surface "
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
        "two-page card in `print/`: the plan, the target, the pictures and the leaks, then a",
        "guide to the card in the player's own words. Every chased pitch in these hitters'",
        "leaks, with the date, the pitcher, the count, the pitch and how far off it was, is in",
        f"[`leak_pitches_{SEASON}.csv`](leak_pitches_{SEASON}.csv), for the video room.",
        "",
        "Each card is drawn from the catcher's view, to scale, around the hitter's own",
        "strike zone; nobody is mirrored, so a left-handed batter's inside is on the right.",
        "It compares the hitter with the average hitter on pitches at the same spot",
        "relative to their zone, in the same count and the same batter-side and",
        "pitcher-hand matchup.",
        "Red is where they swing more, blue where they take more, gray is about average,",
        "and the background shows through where there are too few pitches to say. The",
        "plan is written to the player, one pitch per",
        "line in the order to work on them (a take before two strikes first, since it costs",
        "nothing in strikeouts), numbered to the leaks list, which is ranked by runs. The",
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
        "**The target.** Under each plan, how far above the league the hitter chased in",
        f"his leaks in {SEASON} (on the backtest's scale), and what the season-to-season",
        f"line predicts for {SEASON + 1} if he changes nothing (step 19, frozen before the",
        "season). Leaks are a hitter's worst-looking spots, so about half of the excess",
        "goes away by itself. A fix is a number under the prediction, not under this",
        "season's rate; that is also how step 20 will score the card. A hitter whose",
        "prediction is already at the league's rate gets no target.",
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
                mark = f"{CIRCLED[it['n'] - 1]} " if it["kind"] == "pitch" else ""
                lines.append(f"- {mark}{it['text']}")
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
    "players": [{k: p[k] for k in ("id", "name", "bats", "rank", "of", "pa", "xchase_plus",
                                   "archetype", "noted", "runs_at_stake", "choices", "contact",
                                   "zone", "height_in", "side_pitches", "leaks", "target",
                                   "target_text", "plan_items", "start_with")}
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
        "player": p["name"], "batter": p["id"], "bats": p["bats"], "xchase_plus_rank": p["rank"],
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
pd.DataFrame(summary_rows).to_csv(CARDS_DIR / f"player_cards_{SEASON}.csv", index=False)
print(f"  wrote player_cards/player_cards_{SEASON}.csv")

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
