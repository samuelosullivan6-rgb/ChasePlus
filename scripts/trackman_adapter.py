"""
TrackMan to Statcast: the adapter behind the college path.

Reads TrackMan game CSVs (one row per pitch, TrackMan's own column names
and units) and writes the same pitches with the Statcast column names,
codes and units that steps 02-04 and 17 read. Nothing downstream needs to
know the pitches came from TrackMan; college_build.py runs steps 02, 13,
15 and 17 unchanged on what this writes.

WHAT MAPS STRAIGHT ACROSS

  TrackMan                     Statcast
  Balls, Strikes               balls, strikes (the count before the pitch)
  PlateLocSide, PlateLocHeight plate_x, plate_z (feet; see the sign below)
  PitchCall (+ TaggedHitType)  description
  KorBB, PlayResult, PitchCall events, on the pitch that ends the PA
  Outs (next pitch's), and     the outs on each play, which the runners
    OutsOnPlay on a game's       are rebuilt from (below)
    last pitch
  ExitSpeed, Angle             launch_speed, launch_angle
  TaggedHitType                bb_type
  TaggedPitchType, else        pitch_type, as Statcast's two-letter codes
    AutoPitchType
  PitcherThrows, BatterSide    p_throws, stand (R / L)
  Batter, BatterId, ...        batter (id), the name register, teams
  Inning, Top/Bottom, Outs     inning, inning_topbot (Top / Bot), outs_when_up
  GameUID or GameID, PAofInning, game_pk, at_bat_number (counted within the
    PitchofPA, PitchNo           game), pitch_number

THE SIGN OF PLATELOCSIDE

  Statcast's plate_x is from the catcher's view: negative toward third
  base, positive toward first. TrackMan does not say which way its
  PlateLocSide runs in the CSV itself, so the adapter reads it off the
  files: a hit-by-pitch is inside by definition, so on the plate_x scale
  it is negative for a right-handed batter and positive for a left-handed
  one. --plate-side-sign auto (the default) picks the sign that puts at
  least 80% of the files' hit-by-pitches inside and stops if neither does
  (or there are fewer than 10); +1 or -1 sets it by hand. A right-handed
  pitcher's release point (RelSide) is printed as a second check.

WHAT TRACKMAN DOES NOT HAVE, AND WHAT FILLS IN

  Strike zone   No per-pitch zone. Each hitter's zone is set from his
                height, as MLB's 2026 zone is: top 53.5% and bottom 27%
                of his height (ZONE_TOP_SHARE, ZONE_BOTTOM_SHARE below),
                heights from a roster CSV. A hitter missing from the
                roster gets the roster's median height, and is listed.
  zone          Savant's zone number, from the location and that zone:
                1-9 inside, 11-14 outside. Inside means the ball touches
                the zone: within 0.83 ft of the middle of the plate (half
                the plate plus a ball's radius) and within a ball's radius
                (0.121 ft) of its top and bottom. That rule reproduces
                Savant's zone on 99.9% of 2025-2026 pitches.
  Runners       TrackMan has no runners on base. They are rebuilt one
                plate appearance at a time from the result, the outs on
                the play and the runs scored, with the usual advancement
                (a single moves everyone up one, a double two, ...) and
                the recorded runs and outs taking precedence: if two runs
                scored on a single, the two lead runners scored. Stolen
                bases and extra bases taken leave no trace and are missed.
                On the 2026 Statcast round trip the rebuilt bases are
                exactly right at the start of 90% to 94% of plate
                appearances (by team), and run values built on them
                are as close to MLB's as run values built on the true
                bases (trackman_roundtrip.py).
  No decision   A pitch with no call (PitchCall Undefined) or no pitch type
                is kept, so the plate appearance stays whole, but step 02
                does not read it as a swing decision.
  Score         bat_score, fld_score and post_bat_score, summed from
                RunsScored.
  xwOBA         Not here: college_build.py fits it on the files' own
                batted balls and fills estimated_woba_using_speedangle.
  Win and run   delta_home_win_exp and delta_run_exp are left empty;
  expectancy    only step 03's printed cross-check reads them.

Run on its own it writes the adapted pitches to a parquet file, for a
look before the full build:

    python scripts/trackman_adapter.py --trackman <folder or CSVs> \\
        --heights <roster.csv> --out <file.parquet>
"""

import argparse
import re
import sys
import zlib
from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

# MLB's 2026 zone, as a share of the batter's height (step 17 reads the
# same 53.5% back off the 2026 cards).
ZONE_TOP_SHARE = 0.535
ZONE_BOTTOM_SHARE = 0.27

# Inside the zone: the ball touches it (feet).
HALF_PLATE_PLUS_BALL = 0.83
BALL_RADIUS = 0.121

# The sign check on PlateLocSide.
MIN_HBP_FOR_SIGN = 10
HBP_INSIDE_SHARE = 0.80

# Columns the adapter cannot do without. Everything else is optional.
REQUIRED = [
    "Date", "Inning", "Top/Bottom", "PAofInning", "Outs", "Balls", "Strikes",
    "Batter", "BatterSide", "Pitcher", "PitcherThrows", "PitchCall", "KorBB",
    "PlayResult", "PlateLocSide", "PlateLocHeight", "RunsScored",
]

PITCH_TYPES = {
    "fastball": "FF", "fourseamfastball": "FF", "fourseam": "FF", "4seam": "FF",
    "twoseamfastball": "SI", "twoseam": "SI", "2seam": "SI", "sinker": "SI",
    "cutter": "FC",
    "slider": "SL", "sweeper": "ST", "slurve": "SV",
    "curveball": "CU", "knucklecurve": "KC",
    "changeup": "CH",
    "splitter": "FS", "forkball": "FO",
    "knuckleball": "KN", "screwball": "SC", "eephus": "EP",
}

PITCH_NAMES = {
    "FF": "4-Seam Fastball", "SI": "Sinker", "FC": "Cutter", "SL": "Slider",
    "ST": "Sweeper", "SV": "Slurve", "CU": "Curveball", "KC": "Knuckle Curve",
    "CH": "Changeup", "FS": "Split-Finger", "FO": "Forkball", "KN": "Knuckleball",
    "SC": "Screwball", "EP": "Eephus",
}

# PitchCall -> description. Fouls and whiffs on a bunt are relabelled
# below from TaggedHitType, so step 02 leaves them out like Statcast's.
DESCRIPTIONS = {
    "ballcalled": "ball",
    "ballindirt": "blocked_ball",
    "ballintentional": "intent_ball",
    "strikecalled": "called_strike",
    "strikeswinging": "swinging_strike",
    "foulball": "foul",
    "foulballnotfieldable": "foul",
    "foulballfieldable": "foul",
    "foultip": "foul_tip",
    "inplay": "hit_into_play",
    "hitbypitch": "hit_by_pitch",
}

HIT_TYPES = {
    "groundball": "ground_ball", "linedrive": "line_drive",
    "flyball": "fly_ball", "popup": "popup", "bunt": "ground_ball",
}

HITS = {"single": "single", "double": "double", "triple": "triple", "homerun": "home_run"}


def key(text):
    """A TrackMan code reduced to lower-case letters and digits."""

    if not isinstance(text, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


# --------------------------------------------------
# READING THE FILES
# --------------------------------------------------

def find_csvs(paths):
    """Every .csv under the given files and folders, sorted."""

    found = []
    for path in map(Path, paths):
        if path.is_dir():
            found += sorted(p for p in path.rglob("*.csv") if not p.name.startswith("."))
        elif path.suffix.lower() == ".csv":
            found.append(path)
        else:
            raise SystemExit(f"Not a CSV or a folder: {path}")
    if not found:
        raise SystemExit(f"No TrackMan CSVs found in {', '.join(map(str, paths))}.")
    return found


def read_trackman(paths):
    """All the files as one table, TrackMan's column names kept (matched
    without regard to case or spaces), one row per pitch."""

    frames = []
    for path in find_csvs(paths):
        frame = pd.read_csv(path, low_memory=False)
        frame["source_file"] = path.name
        frames.append(frame)
    tm = pd.concat(frames, ignore_index=True)

    # One spelling per column, TrackMan's.
    wanted = REQUIRED + [
        "PitchNo", "PitchofPA", "Time", "GameID", "GameUID", "BatterId", "BatterTeam",
        "PitcherId", "PitcherTeam", "HomeTeam", "AwayTeam", "TaggedPitchType",
        "AutoPitchType", "TaggedHitType", "OutsOnPlay", "ExitSpeed", "Angle",
        "RelSpeed", "RelSide", "RelHeight", "Extension", "HorzBreak", "InducedVertBreak",
        "PitchUID",
    ]
    by_key = {key(c): c for c in wanted}
    tm = tm.rename(columns={c: by_key[key(c)] for c in tm.columns if key(c) in by_key})

    missing = [c for c in REQUIRED if c not in tm.columns]
    if not ({"GameUID", "GameID"} & set(tm.columns)):
        missing.append("GameUID or GameID")
    if not ({"TaggedPitchType", "AutoPitchType"} & set(tm.columns)):
        missing.append("TaggedPitchType or AutoPitchType")
    if missing:
        raise SystemExit(f"The TrackMan files are missing columns the adapter needs: {missing}")
    return tm


def load_heights(path):
    """A roster CSV with each hitter's height: an id column (BatterId,
    batter_id, id or TrackMan's PlayerId) and/or a name column (Batter,
    name, player, "Last, First" or "First Last"), and a height column
    (height_in in inches, or height as 6-2, 6'2" or 74). Returns batter
    id or name -> height in inches."""

    roster = pd.read_csv(path)
    cols = {key(c): c for c in roster.columns}
    id_col = next((cols[k] for k in ("batterid", "batter_id", "playerid", "id") if k in cols), None)
    name_col = next((cols[k] for k in ("batter", "name", "player", "playername") if k in cols), None)
    height_col = next((cols[k] for k in ("heightin", "heightinches", "inches", "height", "ht")
                       if k in cols), None)
    if height_col is None or (id_col is None and name_col is None):
        raise SystemExit(f"{path}: needs a height column and an id or name column; "
                         f"found {list(roster.columns)}.")

    def inches(value):
        if pd.isna(value):
            return np.nan
        text = str(value).strip()
        m = re.fullmatch(r"(\d)\s*(?:-|'|ft|\s)\s*(\d{1,2}(?:\.\d+)?)\s*(?:\"|in)?", text)
        if m:
            return int(m.group(1)) * 12 + float(m.group(2))
        try:
            number = float(text)
        except ValueError:
            return np.nan
        return number * 12 if number < 8 else number

    heights = roster.assign(height_in=roster[height_col].map(inches))
    bad = heights["height_in"].isna() | ~heights["height_in"].between(60, 84)
    if bad.any():
        print(f"WARNING: {int(bad.sum())} roster rows have no usable height (60-84 in); ignored.")
    heights = heights[~bad]
    by_id = ({int(i): h for i, h in zip(heights[id_col], heights["height_in"]) if pd.notna(i)}
             if id_col else {})
    by_name = ({normal_name(n): h for n, h in zip(heights[name_col], heights["height_in"])}
               if name_col else {})
    return by_id, by_name, float(heights["height_in"].median())


def normal_name(name):
    """'Last, First' and 'First Last' compare equal."""

    if not isinstance(name, str):
        return ""
    if "," in name:
        last, first = name.split(",", 1)
        name = f"{first} {last}"
    return " ".join(name.lower().replace(".", " ").split())


def stable_id(name):
    """An id for a player with no TrackMan id: the same name gets the same
    number in every run, well clear of TrackMan's own ids."""

    return 9_000_000_000 + zlib.crc32(normal_name(name).encode())


# --------------------------------------------------
# THE PLATELOCSIDE SIGN
# --------------------------------------------------

def plate_side_sign(tm, requested="auto"):
    """+1 if PlateLocSide already runs like plate_x, -1 if it is mirrored,
    and the evidence for it."""

    hbp = tm[(tm["PitchCall"].map(key) == "hitbypitch") & tm["PlateLocSide"].notna()]
    side = hbp["BatterSide"].map(lambda s: {"r": 1.0, "l": -1.0}.get(key(s)[:1], np.nan))
    hbp = hbp[side.notna()]
    side = side[side.notna()]
    inside_if_plus = float((hbp["PlateLocSide"] * side < 0).mean()) if len(hbp) else np.nan

    rhp = tm[tm["PitcherThrows"].map(key).str.startswith("r")]
    rel = rhp["RelSide"].median() if "RelSide" in tm.columns else np.nan

    print(f"PlateLocSide sign check: {len(hbp)} hit-by-pitches; with PlateLocSide taken as "
          f"plate_x, {inside_if_plus:.0%} of them are inside" if len(hbp) else
          "PlateLocSide sign check: no hit-by-pitches with a location")
    if pd.notna(rel):
        print(f"  right-handed pitchers' median RelSide: {rel:+.2f} ft "
              "(Statcast's release_pos_x is negative for them)")

    evidence = {"hit_by_pitches": int(len(hbp)),
                "inside_if_plus": None if pd.isna(inside_if_plus) else round(inside_if_plus, 3),
                "rhp_median_relside": None if pd.isna(rel) else round(float(rel), 2)}
    if requested != "auto":
        sign = float(requested)
        if len(hbp) >= MIN_HBP_FOR_SIGN:
            inside = inside_if_plus if sign > 0 else 1 - inside_if_plus
            if inside < 0.5:
                print(f"WARNING: --plate-side-sign {requested} puts only {inside:.0%} of "
                      "hit-by-pitches inside. Check the sign.")
        return sign, evidence

    if len(hbp) < MIN_HBP_FOR_SIGN:
        raise SystemExit(f"Only {len(hbp)} hit-by-pitch{'' if len(hbp) == 1 else 'es'} with a location, too few to read "
                         "PlateLocSide's sign. Pass --plate-side-sign +1 (catcher's view, "
                         "first-base side positive) or -1.")
    if inside_if_plus >= HBP_INSIDE_SHARE:
        sign = 1.0
    elif inside_if_plus <= 1 - HBP_INSIDE_SHARE:
        sign = -1.0
    else:
        raise SystemExit(f"Hit-by-pitches land {inside_if_plus:.0%} on one side: PlateLocSide's "
                         "sign is unclear. Pass --plate-side-sign +1 or -1.")
    print(f"  so plate_x = {'+' if sign > 0 else '-'}PlateLocSide")
    return sign, evidence


# --------------------------------------------------
# RUNNERS AND SCORE
#
# One half inning at a time, pitch by pitch. Before each pitch the state
# (runners, runs) is recorded as Statcast records it; then the pitch is
# applied. The outs come from TrackMan's own Outs column: the outs on a
# pitch are the next pitch's Outs minus this one's (OutsOnPlay only for
# the last pitch of a game, where there is no next pitch). That keeps the
# rebuild on the file's outs even where OutsOnPlay was left blank, and
# catches outs on the bases (a caught stealing on the pitch, a pickoff
# after it): a runner is removed for each, the one on first before the
# one on second. Runs scored on a pitch that does not end the plate
# appearance (a wild pitch, a balk, a steal of home) come off third.
# --------------------------------------------------

def place_runners(runners, batter_base, advance, runs, outs_on_play, batter_out):
    """Where everybody ends up after the play that ends a plate appearance.

    runners       bases occupied before the play, e.g. [1, 3]
    batter_base   the batter's base by the play's rule (0 if he is out,
                  4 for a home run)
    advance       bases every runner moves by the play's rule; a forced
                  runner moves at least one
    runs          runs scored on the play, from the file
    outs_on_play  outs on the play, from the file

    The file's runs and outs take precedence over the rule: more runs
    than the rule gives come from the lead runners still on base, fewer
    hold the trailing scorer at third (or make him an out, if the outs
    say a runner was out); outs beyond the batter take the runner who
    started on first, then second (a double play, a force at second)."""

    dest = {r: min(r + advance, 4) for r in runners}
    if batter_base >= 1:                      # the force: 1, then 1-2, then 1-2-3
        base = 1
        while base in dest:
            dest[base] = max(dest[base], base + 1)
            base += 1

    def scored():
        return sum(d >= 4 for d in dest.values()) + (batter_base == 4)

    for r in sorted((r for r in runners if dest[r] < 4), key=lambda r: -dest[r]):
        if scored() >= runs:
            break
        dest[r] = 4
    if scored() < runs and 1 <= batter_base <= 3:
        batter_base = 4                       # an error lets him come around

    extra_outs = max(outs_on_play - int(batter_out), 0)
    out = set()
    for r in sorted(r for r in runners if dest[r] >= 4):
        if scored() <= runs:
            break
        if extra_outs > 0:
            out.add(r)
            extra_outs -= 1
        dest[r] = 3 if r not in out else 0
    for r in sorted(runners):
        if extra_outs <= 0:
            break
        if r not in out and dest[r] < 4:
            out.add(r)
            extra_outs -= 1

    taken = {batter_base} if 1 <= batter_base <= 3 else set()
    for r in sorted(runners, reverse=True):   # lead runner first
        if r in out or dest[r] >= 4:
            continue
        d = min(dest[r], 3)
        while d in taken and d > 1:
            d -= 1
        if d not in taken:
            taken.add(d)
    return sorted(taken)


def play_rule(event, outs_on_play):
    """(batter's base, runners' advance, batter out) for the event that
    ends a plate appearance (Statcast's name for it)."""

    if event == "home_run":
        return 4, 4, False
    if event == "triple":
        return 3, 3, False
    if event == "double":
        return 2, 2, False
    if event in ("single", "field_error"):
        return 1, 1, False
    if event in ("walk", "intent_walk", "hit_by_pitch", "catcher_interf",
                 "fielders_choice", "fielders_choice_out", "force_out"):
        return 1, 0, False
    if event in ("strikeout", "strikeout_double_play"):
        # a dropped third strike with no out on the play: he reached
        return (1, 0, False) if outs_on_play == 0 else (0, 0, True)
    if event == "sac_bunt":
        return 0, 1, True
    return 0, 0, True                         # outs in play, sac flies included


def outs_on_each_pitch(p):
    """Outs recorded on each pitch: the next pitch's Outs minus this one's
    within a half inning, three minus this one's when the game goes on to
    another half inning, and the file's OutsOnPlay (or the result's own
    out) on a game's last pitch."""

    same_half = ((p["game_pk"] == p["game_pk"].shift(-1))
                 & (p["inning"] == p["inning"].shift(-1))
                 & (p["inning_topbot"] == p["inning_topbot"].shift(-1)))
    same_game = p["game_pk"] == p["game_pk"].shift(-1)
    nxt = p["tm_outs"].shift(-1)
    by_rule = p["events"].map(lambda e: int(play_rule(e, 1)[2]) if isinstance(e, str)
                              and e != "truncated_pa" else 0)
    last = p["outs_on_play_file"].fillna(by_rule)
    outs = np.where(same_half, nxt - p["tm_outs"],
                    np.where(same_game, 3 - p["tm_outs"], last))
    return pd.Series(np.clip(np.nan_to_num(outs), 0, 3).astype(int), index=p.index)


def rebuild_bases_and_score(p):
    """on_1b / on_2b / on_3b (1 or NaN, as Statcast's runner ids test),
    bat_score, fld_score and post_bat_score for every pitch, and the outs
    recorded on it. p must be in game and pitch order and carry game_pk,
    inning, inning_topbot, tm_outs, runs_on_pitch, outs_on_play_file,
    pa_end and events."""

    n = len(p)
    on = np.full((n, 3), np.nan)
    bat_score = np.zeros(n)
    post_score = np.zeros(n)
    fld_score = np.zeros(n)

    outs_on = outs_on_each_pitch(p).to_numpy()
    games = p["game_pk"].to_numpy()
    halves = (p["inning"].astype(str) + p["inning_topbot"]).to_numpy()
    tops = (p["inning_topbot"] == "Top").to_numpy()
    runs = p["runs_on_pitch"].fillna(0).astype(int).to_numpy()
    ends = p["pa_end"].to_numpy()
    events = p["events"].to_numpy()

    score = {}
    runners = []
    for i in range(n):
        if i == 0 or games[i] != games[i - 1]:
            score = {"Top": 0, "Bot": 0}
        if i == 0 or games[i] != games[i - 1] or halves[i] != halves[i - 1]:
            runners = []
        batting = "Top" if tops[i] else "Bot"
        fielding = "Bot" if tops[i] else "Top"

        for b in runners:
            on[i, b - 1] = 1.0
        bat_score[i] = score[batting]
        fld_score[i] = score[fielding]

        if ends[i] and isinstance(events[i], str) and events[i] != "truncated_pa":
            batter_base, advance, batter_out = play_rule(events[i], outs_on[i])
            runners = place_runners(runners, batter_base, advance, runs[i], outs_on[i],
                                    batter_out)
        else:
            for _ in range(runs[i]):
                if runners:
                    runners.remove(max(runners))
            for _ in range(outs_on[i]):
                if runners:
                    runners.remove(min(runners))
        score[batting] += runs[i]
        post_score[i] = score[batting]

    cols = {"on_1b": on[:, 0], "on_2b": on[:, 1], "on_3b": on[:, 2],
            "bat_score": bat_score, "fld_score": fld_score, "post_bat_score": post_score,
            "outs_on_pitch": outs_on}
    return pd.DataFrame(cols, index=p.index)


# --------------------------------------------------
# THE ADAPTER
# --------------------------------------------------

def side_code(value):
    k = key(value)
    return "R" if k.startswith("r") else ("L" if k.startswith("l") else None)


def pitch_code(tagged, auto):
    code = PITCH_TYPES.get(key(tagged))
    return code if code else PITCH_TYPES.get(key(auto))


def adapt(tm, heights, sign="auto", zone_top_share=ZONE_TOP_SHARE,
          zone_bottom_share=ZONE_BOTTOM_SHARE, season=None):
    """TrackMan rows -> Statcast-named pitches, one row per pitch, in game
    and pitch order. `heights` is load_heights()'s result. Returns the
    pitches and a short dict of what was filled in, for the build log."""

    tm = tm.copy()
    report = {}

    # Games and their order
    game_key = tm["GameUID"] if "GameUID" in tm.columns else tm["GameID"]
    if "GameUID" in tm.columns and "GameID" in tm.columns:
        game_key = tm["GameUID"].fillna(tm["GameID"])
    tm["game_key"] = game_key.astype(str)
    tm["game_date"] = pd.to_datetime(tm["Date"], errors="coerce", format="mixed")
    if tm["game_date"].isna().any():
        raise SystemExit(f"{int(tm['game_date'].isna().sum())} rows have no readable Date.")
    order = (tm.groupby("game_key")["game_date"].min().reset_index()
             .sort_values(["game_date", "game_key"]).reset_index(drop=True))
    tm["game_pk"] = tm["game_key"].map(dict(zip(order["game_key"], order.index + 1)))

    tm["inning_topbot"] = tm["Top/Bottom"].map(lambda v: "Top" if key(v).startswith("t") else "Bot")
    tm["inning"] = pd.to_numeric(tm["Inning"], errors="coerce").astype("Int64")
    if "PitchNo" not in tm.columns and "Time" not in tm.columns:
        raise SystemExit("Need PitchNo (or Time) to put each game's pitches in order.")
    sort_cols = ["game_pk", "PitchNo"] if "PitchNo" in tm.columns else ["game_pk", "inning", "Time"]
    tm = tm.sort_values(sort_cols, kind="stable").reset_index(drop=True)

    # Plate appearances: a new one whenever the half inning or PAofInning
    # changes, or after any pitch with a result (in play, a hit batter, a
    # strikeout or walk), counted from 1 within the game.
    pa_id = (tm["inning"].astype(str) + tm["inning_topbot"] + "-" + tm["PAofInning"].astype(str))
    has_result = (tm["PitchCall"].map(key).isin(["inplay", "hitbypitch"])
                  | tm["KorBB"].map(key).isin(["strikeout", "walk"]))
    new_pa = ((pa_id != pa_id.shift()) | (tm["game_pk"] != tm["game_pk"].shift())
              | has_result.shift(fill_value=False))
    tm["at_bat_number"] = new_pa.astype(int).groupby(tm["game_pk"]).cumsum()
    tm["pitch_number"] = tm.groupby(["game_pk", "at_bat_number"]).cumcount() + 1
    tm["pa_end"] = (tm["at_bat_number"] != tm["at_bat_number"].shift(-1)) | (
        tm["game_pk"] != tm["game_pk"].shift(-1))

    out = pd.DataFrame(index=tm.index)
    out["game_pk"] = tm["game_pk"].astype("int64")
    out["game_date"] = tm["game_date"].dt.strftime("%Y-%m-%d")
    out["game_year"] = int(season) if season else tm["game_date"].dt.year.astype(int)
    out["game_type"] = "R"
    out["at_bat_number"] = tm["at_bat_number"].astype("int64")
    out["pitch_number"] = tm["pitch_number"].astype("int64")

    # People
    def ids(id_col, name_col):
        named = tm[name_col].astype(str).str.strip()
        if id_col in tm.columns:
            raw = pd.to_numeric(tm[id_col], errors="coerce")
            return raw.where(raw.notna(), named.map(stable_id)).astype("int64"), named
        return named.map(stable_id).astype("int64"), named

    out["batter"], batter_name = ids("BatterId", "Batter")
    out["pitcher"], pitcher_name = ids("PitcherId", "Pitcher")
    out["player_name"] = pitcher_name.to_numpy()
    out["batter_name"] = batter_name.to_numpy()
    out["stand"] = tm["BatterSide"].map(side_code)
    out["p_throws"] = tm["PitcherThrows"].map(side_code)
    # A side the operator left blank: the side that hitter (or pitcher)
    # used most in the files.
    for col, who in (("stand", "batter"), ("p_throws", "pitcher")):
        blank = out[col].isna()
        if blank.any():
            usual = out[~blank].groupby(who)[col].agg(lambda s: s.mode().iloc[0])
            out.loc[blank, col] = out.loc[blank, who].map(usual).fillna("R")
            report[f"{col}_filled"] = int(blank.sum())

    # Teams: Top means the away team bats.
    home = tm["HomeTeam"] if "HomeTeam" in tm.columns else None
    away = tm["AwayTeam"] if "AwayTeam" in tm.columns else None
    if home is None or away is None:
        bt = tm.get("BatterTeam")
        pt = tm.get("PitcherTeam")
        if bt is None or pt is None:
            raise SystemExit("Need HomeTeam and AwayTeam, or BatterTeam and PitcherTeam.")
        home = pt.where(tm["inning_topbot"] == "Top", bt)
        away = bt.where(tm["inning_topbot"] == "Top", pt)
    out["home_team"] = home.astype(str).to_numpy()
    out["away_team"] = away.astype(str).to_numpy()

    # The pitch
    out["pitch_type"] = [pitch_code(t, a) for t, a in zip(
        tm.get("TaggedPitchType", pd.Series(index=tm.index, dtype=object)),
        tm.get("AutoPitchType", pd.Series(index=tm.index, dtype=object)))]
    out["pitch_name"] = out["pitch_type"].map(PITCH_NAMES)
    call = tm["PitchCall"].map(key)
    hit_type = tm.get("TaggedHitType", pd.Series(index=tm.index, dtype=object)).map(key)
    description = call.map(DESCRIPTIONS)
    bunt = hit_type == "bunt"
    description = description.mask(bunt & (description == "foul"), "foul_bunt")
    description = description.mask(bunt & (description == "swinging_strike"), "missed_bunt")
    korbb = tm["KorBB"].map(key)
    # A two-strike foul bunt is a strikeout; TrackMan has it as a foul.
    description = description.mask((korbb == "strikeout") & (description == "foul"), "foul_bunt")
    out["description"] = description
    report["pitches_without_a_call"] = int(description.isna().sum())
    # A pitch with no call, or no pitch type, cannot be read as a decision.
    out.loc[description.isna(), "pitch_type"] = None
    report["pitches_without_a_type"] = int(out["pitch_type"].isna().sum())

    # Location: plate_x from the catcher's view
    s, evidence = plate_side_sign(tm, sign)
    report["plate_side_sign"] = s
    report["plate_side_evidence"] = evidence
    out["plate_x"] = pd.to_numeric(tm["PlateLocSide"], errors="coerce") * s
    out["plate_z"] = pd.to_numeric(tm["PlateLocHeight"], errors="coerce")
    typical = out["plate_z"].median(), out["plate_x"].abs().median()
    if not (1.0 <= typical[0] <= 4.0 and typical[1] <= 1.5):
        raise SystemExit(f"PlateLocHeight / PlateLocSide do not look like feet "
                         f"(median height {typical[0]:.2f}, median |side| {typical[1]:.2f}).")

    for src, dst, scale in (("RelSpeed", "release_speed", 1.0), ("RelHeight", "release_pos_z", 1.0),
                            ("Extension", "release_extension", 1.0),
                            ("InducedVertBreak", "pfx_z", 1 / 12)):
        out[dst] = pd.to_numeric(tm[src], errors="coerce") * scale if src in tm.columns else np.nan
    out["release_pos_x"] = (pd.to_numeric(tm["RelSide"], errors="coerce") * s
                            if "RelSide" in tm.columns else np.nan)
    out["pfx_x"] = (pd.to_numeric(tm["HorzBreak"], errors="coerce") * s / 12
                    if "HorzBreak" in tm.columns else np.nan)

    # The hitter's zone, from his height
    by_id, by_name, median_height = heights
    height = pd.to_numeric(out["batter"].map(by_id), errors="coerce").astype(float)
    height = height.fillna(pd.to_numeric(
        out["batter_name"].map(lambda n: by_name.get(normal_name(n), np.nan)), errors="coerce"))
    no_height = out.loc[height.isna(), ["batter", "batter_name"]].drop_duplicates("batter")
    report["hitters_without_height"] = no_height["batter_name"].tolist()
    if len(no_height):
        print(f"WARNING: {len(no_height)} hitters are not in the heights roster; they get its "
              f"median height ({median_height:.0f} in): "
              + ", ".join(no_height["batter_name"].head(12))
              + (" ..." if len(no_height) > 12 else ""))
    height_ft = height.fillna(median_height) / 12
    out["sz_top"] = zone_top_share * height_ft
    out["sz_bot"] = zone_bottom_share * height_ft

    out["zone"] = zone_number(out["plate_x"], out["plate_z"], out["sz_top"], out["sz_bot"])
    out["balls"] = pd.to_numeric(tm["Balls"], errors="coerce").astype("Int64")
    out["strikes"] = pd.to_numeric(tm["Strikes"], errors="coerce").astype("Int64")
    bad_count = ~(out["balls"].between(0, 3) & out["strikes"].between(0, 2)).fillna(False)
    if bad_count.any():
        print(f"WARNING: {int(bad_count.sum())} pitches have an impossible count; they are "
              "kept out of the analysis.")
        out.loc[bad_count, "pitch_type"] = None
        out["balls"] = out["balls"].clip(0, 3)
        out["strikes"] = out["strikes"].clip(0, 2)

    # Contact
    out["launch_speed"] = pd.to_numeric(tm.get("ExitSpeed"), errors="coerce")
    out["launch_angle"] = pd.to_numeric(tm.get("Angle"), errors="coerce")
    out["bb_type"] = hit_type.map(HIT_TYPES).where(description == "hit_into_play")
    out["is_bunt"] = (bunt & (description == "hit_into_play")).astype(int)

    # The result, on the pitch that ends the plate appearance. Outs on
    # the play come from the Outs column (outs_on_each_pitch); the file's
    # OutsOnPlay is used only on a game's last pitch, and how often the two
    # agree is reported.
    outs_file = (pd.to_numeric(tm["OutsOnPlay"], errors="coerce") if "OutsOnPlay" in tm.columns
                 else pd.Series(np.nan, index=tm.index))
    result = tm["PlayResult"].map(key)
    in_play = description == "hit_into_play"

    def results(outs_n):
        events = pd.Series(None, index=tm.index, dtype=object)
        events[in_play] = result[in_play].map(HITS)
        is_out = in_play & events.isna()
        events[is_out & (result == "error")] = "field_error"
        fc = is_out & (result == "fielderschoice")
        events[fc] = np.where(outs_n[fc] >= 1, "fielders_choice_out", "fielders_choice")
        sac = is_out & (result == "sacrifice")
        events[sac] = np.where(bunt[sac], "sac_bunt", "sac_fly")
        plain = is_out & events.isna()
        events[plain] = np.select(
            [outs_n[plain] >= 3, (outs_n[plain] == 2) & (hit_type[plain] == "groundball"),
             outs_n[plain] == 2],
            ["triple_play", "grounded_into_double_play", "double_play"], "field_out")
        k = korbb == "strikeout"
        events[k] = np.where(outs_n[k] >= 2, "strikeout_double_play", "strikeout")
        bb = korbb == "walk"
        events[bb] = np.where(call[bb] == "ballintentional", "intent_walk", "walk")
        events[call == "hitbypitch"] = "hit_by_pitch"
        # Only the last pitch of a plate appearance carries a result. One
        # that ends with none (the third out on the bases) is Statcast's
        # truncated_pa.
        events[~tm["pa_end"]] = None
        events[tm["pa_end"] & events.isna()] = "truncated_pa"
        return events

    out["inning"] = tm["inning"].astype("int64")
    out["inning_topbot"] = tm["inning_topbot"]
    work = out[["game_pk", "inning", "inning_topbot"]].assign(
        tm_outs=pd.to_numeric(tm["Outs"], errors="coerce"),
        runs_on_pitch=pd.to_numeric(tm["RunsScored"], errors="coerce").fillna(0).clip(0, 4),
        outs_on_play_file=outs_file.clip(0, 3),
        pa_end=tm["pa_end"],
        events=results(outs_file.fillna(1)))
    outs_n = outs_on_each_pitch(work)
    work["events"] = results(outs_n)
    out["events"] = work["events"]
    report["truncated_plate_appearances"] = int((out["events"] == "truncated_pa").sum())
    ends = tm["pa_end"] & outs_file.notna()
    if ends.any():
        report["outs_on_play_agree_with_outs_column"] = round(
            float((outs_file[ends] == outs_n[ends]).mean()), 4)

    rebuilt = rebuild_bases_and_score(work)
    out["outs_when_up"] = pd.to_numeric(tm["Outs"], errors="coerce").clip(0, 2).astype("Int64")
    for col in ("on_1b", "on_2b", "on_3b", "bat_score", "fld_score", "post_bat_score"):
        out[col] = rebuilt[col]
    out["outs_on_pitch"] = rebuilt["outs_on_pitch"]

    for col in ("delta_home_win_exp", "delta_run_exp", "estimated_woba_using_speedangle",
                "woba_value", "woba_denom"):
        out[col] = np.nan
    out["trackman_file"] = tm["source_file"].to_numpy()
    out["trackman_pitch_uid"] = (tm["PitchUID"].astype(str).to_numpy() if "PitchUID" in tm.columns
                                 else None)

    report["games"] = int(out["game_pk"].nunique())
    report["pitches"] = int(len(out))
    report["plate_appearances"] = int(out.groupby(["game_pk", "at_bat_number"]).ngroups)
    report["hitters"] = int(out["batter"].nunique())
    report["untracked_location"] = int(out["plate_x"].isna().sum())
    return out, report


def zone_number(x, z, top, bottom):
    """Savant's zone number: 1-9 inside (3 x 3 from the catcher's view,
    top row first), 11-14 outside (up-left, up-right, down-left,
    down-right). NaN without a location."""

    x, z, top, bottom = (pd.to_numeric(v, errors="coerce").astype(float) for v in (x, z, top, bottom))
    inside = ((x.abs() <= HALF_PLATE_PLUS_BALL) & (z <= top + BALL_RADIUS)
              & (z >= bottom - BALL_RADIUS))
    col = np.clip(np.floor((x + HALF_PLATE_PLUS_BALL) / (2 * HALF_PLATE_PLUS_BALL / 3)), 0, 2)
    row = np.clip(np.floor((top - z) / ((top - bottom) / 3)), 0, 2)
    middle_x, middle_z = 0.0, (top + bottom) / 2
    outside = np.where(z >= middle_z, np.where(x < middle_x, 11, 12), np.where(x < middle_x, 13, 14))
    zone = np.where(inside, 1 + 3 * row + col, outside).astype(float)
    return pd.Series(np.where(x.isna() | z.isna(), np.nan, zone), index=x.index)


def name_register(pitches):
    """The Chadwick-register stand-in step 04's name lookup reads:
    key_mlbam (the batter id here), name_first, name_last."""

    names = (pitches.groupby("batter")["batter_name"]
             .agg(lambda s: s.mode().iloc[0]).reset_index())
    first, last = [], []
    for name in names["batter_name"]:
        if "," in name:
            l, f = name.split(",", 1)
        else:
            parts = name.split()
            f, l = " ".join(parts[:-1]), parts[-1] if parts else ""
        first.append(f.strip())
        last.append(l.strip())
    return pd.DataFrame({"key_mlbam": names["batter"].astype("int64"),
                         "name_first": first, "name_last": last})


def main():
    parser = argparse.ArgumentParser(description="TrackMan CSVs -> Statcast-named pitches.")
    parser.add_argument("--trackman", nargs="+", required=True,
                        help="TrackMan CSV files, or folders of them")
    parser.add_argument("--heights", required=True, help="roster CSV with each hitter's height")
    parser.add_argument("--out", required=True, help="parquet file to write")
    parser.add_argument("--plate-side-sign", default="auto", choices=["auto", "+1", "-1"])
    parser.add_argument("--season", type=int, default=None)
    args = parser.parse_args()
    pitches, report = adapt(read_trackman(args.trackman), load_heights(args.heights),
                            args.plate_side_sign, season=args.season)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pitches.to_parquet(args.out, index=False)
    for k, v in report.items():
        print(f"  {k}: {v}")
    print(f"Wrote {len(pitches):,} pitches to {args.out}")


if __name__ == "__main__":
    sys.exit(main())
