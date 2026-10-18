"""
Statcast to TrackMan: 2026 MLB pitches written as TrackMan game CSVs, so
the college path can be tested end to end without any college data.

The opposite of trackman_adapter.py. One CSV per game, TrackMan's column
names, codes and units, and only what a TrackMan file carries: no strike
zone, no runners on base, no xwOBA, no score (only the runs scored on
each pitch). trackman_roundtrip.py runs these files through the adapter
and the college path and compares the result with the MLB build on the
same pitches.

Where TrackMan's vocabulary is coarser than Statcast's, the CSV is
coarser too: a foul tip is a StrikeSwinging, a knuckle curve a Curveball,
a force out a FieldersChoice, and so on (see the maps below).
PlateLocSide, RelSide and HorzBreak are written mirrored (pitcher's
view, third-base side positive) by default, so the adapter has to read
the sign off the files as it would on real ones; --plate-side-sign +1
writes them on Statcast's side instead.

    python scripts/statcast_to_trackman.py --team KC --games 60 \\
        --out college/roundtrip_KC/trackman --heights college/roundtrip_KC/heights.csv
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW = PROJECT_DIR / "data" / "raw"

PITCH_CALLS = {
    "ball": "BallCalled", "blocked_ball": "BallinDirt", "intent_ball": "BallIntentional",
    "pitchout": "BallIntentional", "automatic_ball": "BallCalled",
    "called_strike": "StrikeCalled", "automatic_strike": "StrikeCalled",
    "swinging_strike": "StrikeSwinging", "swinging_strike_blocked": "StrikeSwinging",
    "foul_tip": "StrikeSwinging", "swinging_pitchout": "StrikeSwinging",
    "missed_bunt": "StrikeSwinging", "bunt_foul_tip": "StrikeSwinging",
    "foul": "FoulBallNotFieldable", "foul_pitchout": "FoulBallNotFieldable",
    "foul_bunt": "FoulBall",
    "hit_into_play": "InPlay", "hit_by_pitch": "HitByPitch",
}
BUNT_CALLS = {"foul_bunt", "missed_bunt", "bunt_foul_tip"}
# Pitch-timer violations have no pitch: no type, no location.
NO_PITCH = {"automatic_ball", "automatic_strike"}

TAGGED = {
    "FF": "Fastball", "FA": "Fastball", "SI": "Sinker", "FC": "Cutter", "SL": "Slider",
    "ST": "Sweeper", "SV": "Slider", "CU": "Curveball", "KC": "Curveball", "CS": "Curveball",
    "CH": "ChangeUp", "FS": "Splitter", "FO": "Splitter", "KN": "Knuckleball",
    "EP": "ChangeUp", "SC": "ChangeUp",
}
AUTO = {
    "FF": "Four-Seam", "FA": "Four-Seam", "SI": "Sinker", "FC": "Cutter", "SL": "Slider",
    "ST": "Slider", "SV": "Slider", "CU": "Curveball", "KC": "Curveball", "CS": "Curveball",
    "CH": "Changeup", "FS": "Splitter", "FO": "Splitter", "KN": "Knuckleball",
    "EP": "Changeup", "SC": "Changeup",
}
RESULTS = {
    "single": "Single", "double": "Double", "triple": "Triple", "home_run": "HomeRun",
    "field_error": "Error", "fielders_choice": "FieldersChoice",
    "fielders_choice_out": "FieldersChoice", "force_out": "FieldersChoice",
    "sac_fly": "Sacrifice", "sac_bunt": "Sacrifice",
}
OUT_RESULTS = {"field_out", "grounded_into_double_play", "double_play", "triple_play",
               "sac_fly_double_play", "sac_bunt_double_play"}
HIT_TYPES = {"ground_ball": "GroundBall", "line_drive": "LineDrive", "fly_ball": "FlyBall",
             "popup": "Popup"}
OUTS_ON_EVENT = {"grounded_into_double_play": 2, "double_play": 2, "strikeout_double_play": 2,
                 "sac_fly_double_play": 2, "sac_bunt_double_play": 2, "triple_play": 3}
OUT_EVENTS = OUT_RESULTS | {"strikeout", "strikeout_double_play", "force_out",
                            "fielders_choice_out", "sac_fly", "sac_bunt"}

RAW_COLUMNS = [
    "game_pk", "game_date", "game_year", "game_type", "at_bat_number", "pitch_number", "batter",
    "pitcher", "stand", "p_throws", "home_team", "away_team", "inning", "inning_topbot",
    "outs_when_up", "balls", "strikes", "pitch_type", "description", "events", "des", "bb_type",
    "plate_x", "plate_z", "sz_top", "sz_bot", "release_speed", "release_pos_x", "release_pos_z",
    "release_extension", "pfx_x", "pfx_z", "launch_speed", "launch_angle", "bat_score",
    "post_bat_score",
]


def load_statcast(season=2026):
    """The season's regular-season pitches from step 01's raw files, one
    row per pitch, as step 02 dedupes them."""

    files = sorted(RAW.glob(f"statcast_{season}-*.parquet"))
    if not files:
        raise SystemExit(f"No raw Statcast files for {season} in data/raw/.")
    raw = pd.concat([pd.read_parquet(f, columns=RAW_COLUMNS) for f in files], ignore_index=True)
    raw = raw.drop_duplicates(["game_pk", "at_bat_number", "pitch_number"])
    return raw[(raw["game_type"] == "R") & (raw["game_year"] == season)].reset_index(drop=True)


def team_games(raw, team, games):
    """The team's first `games` games of the season, every pitch of both teams."""

    played = raw[(raw["home_team"] == team) | (raw["away_team"] == team)]
    first = (played.groupby("game_pk")["game_date"].first().sort_values(kind="stable")
             .head(games).index)
    return raw[raw["game_pk"].isin(first)].copy()


def to_trackman(sc, register, sign=-1.0):
    """Statcast pitches -> TrackMan rows. register: Chadwick (key_mlbam,
    name_first, name_last). sign multiplies plate_x, release_pos_x and
    pfx_x into PlateLocSide, RelSide and HorzBreak."""

    sc = sc.sort_values(["game_pk", "at_bat_number", "pitch_number"]).reset_index(drop=True)
    names = (register.dropna(subset=["key_mlbam"]).drop_duplicates("key_mlbam")
             .assign(key_mlbam=lambda r: r["key_mlbam"].astype("int64"))
             .set_index("key_mlbam"))
    names = (names["name_last"].str.strip() + ", " + names["name_first"].str.strip())

    def name_of(ids):
        return ids.map(names).fillna("Player " + ids.astype(str))

    top = sc["inning_topbot"] == "Top"
    tm = pd.DataFrame(index=sc.index)
    tm["PitchNo"] = sc.groupby("game_pk").cumcount() + 1
    tm["Date"] = pd.to_datetime(sc["game_date"]).dt.strftime("%Y-%m-%d")
    half = sc["game_pk"].astype(str) + sc["inning"].astype(str) + sc["inning_topbot"]
    tm["PAofInning"] = sc.groupby(half)["at_bat_number"].rank(method="dense").astype(int)
    tm["PitchofPA"] = sc["pitch_number"]
    tm["Pitcher"] = name_of(sc["pitcher"])
    tm["PitcherId"] = sc["pitcher"]
    tm["PitcherThrows"] = sc["p_throws"].map({"R": "Right", "L": "Left"})
    tm["PitcherTeam"] = np.where(top, sc["home_team"], sc["away_team"])
    tm["Batter"] = name_of(sc["batter"])
    tm["BatterId"] = sc["batter"]
    tm["BatterSide"] = sc["stand"].map({"R": "Right", "L": "Left"})
    tm["BatterTeam"] = np.where(top, sc["away_team"], sc["home_team"])
    tm["Inning"] = sc["inning"]
    tm["Top/Bottom"] = np.where(top, "Top", "Bottom")
    tm["Outs"] = sc["outs_when_up"]
    tm["Balls"] = sc["balls"]
    tm["Strikes"] = sc["strikes"]

    no_pitch = sc["description"].isin(NO_PITCH)
    tm["TaggedPitchType"] = sc["pitch_type"].map(TAGGED).fillna("Undefined").where(~no_pitch, "Undefined")
    tm["AutoPitchType"] = sc["pitch_type"].map(AUTO).fillna("Undefined").where(~no_pitch, "Undefined")
    tm["PitchCall"] = sc["description"].map(PITCH_CALLS).fillna("Undefined")

    ev = sc["events"]
    tm["KorBB"] = np.select([ev.isin(["strikeout", "strikeout_double_play"]),
                             ev.isin(["walk", "intent_walk"])], ["Strikeout", "Walk"], "Undefined")
    in_play = sc["description"] == "hit_into_play"
    result = ev.map(RESULTS)
    result = result.where(~ev.isin(OUT_RESULTS), "Out")
    tm["PlayResult"] = result.where(in_play).fillna("Undefined")

    bunt = (sc["description"].isin(BUNT_CALLS)
            | (in_play & sc["des"].fillna("").str.contains("bunt", case=False))
            | (ev == "sac_bunt"))
    tm["TaggedHitType"] = np.where(bunt, "Bunt", sc["bb_type"].map(HIT_TYPES).fillna("Undefined"))
    tm.loc[~in_play & ~bunt, "TaggedHitType"] = "Undefined"

    # Outs on the play from the outs before the next pitch; three minus
    # the outs on the last pitch of a half inning the game goes on from;
    # the result's own outs on a game's last pitch.
    same_half = (half == half.shift(-1)).fillna(False).to_numpy(bool)
    same_game = (sc["game_pk"] == sc["game_pk"].shift(-1)).fillna(False).to_numpy(bool)
    by_event = ev.map(lambda e: OUTS_ON_EVENT.get(e, 1 if e in OUT_EVENTS else 0)
                      if isinstance(e, str) else 0)
    now = sc["outs_when_up"].astype(float).to_numpy()
    nxt = sc["outs_when_up"].astype(float).shift(-1).to_numpy()
    outs = np.where(same_half, nxt - now,
                    np.where(same_game, 3 - now, np.minimum(by_event.to_numpy(), 3 - now)))
    tm["OutsOnPlay"] = np.clip(np.nan_to_num(outs), 0, 3).astype(int)
    # Runs on the play the same way: up to the next pitch's score within the
    # half inning (Statcast sometimes moves the score between pitches, on a
    # balk or a pickoff throw that no pitch records), and the pitch's own
    # post_bat_score on the last pitch of a half inning.
    score = sc["bat_score"].astype(float).to_numpy()
    runs = np.where(same_half, sc["bat_score"].astype(float).shift(-1).to_numpy() - score,
                    sc["post_bat_score"].astype(float).to_numpy() - score)
    tm["RunsScored"] = np.clip(np.nan_to_num(runs), 0, 4).astype(int)

    tm["RelSpeed"] = sc["release_speed"]
    tm["RelHeight"] = sc["release_pos_z"]
    tm["RelSide"] = sc["release_pos_x"] * sign
    tm["Extension"] = sc["release_extension"]
    tm["InducedVertBreak"] = sc["pfx_z"] * 12
    tm["HorzBreak"] = sc["pfx_x"] * 12 * sign
    tm["PlateLocHeight"] = sc["plate_z"].where(~no_pitch)
    tm["PlateLocSide"] = (sc["plate_x"] * sign).where(~no_pitch)
    tm["ExitSpeed"] = sc["launch_speed"].where(in_play)
    tm["Angle"] = sc["launch_angle"].where(in_play)
    tm["HomeTeam"] = sc["home_team"]
    tm["AwayTeam"] = sc["away_team"]
    tm["GameID"] = tm["Date"].str.replace("-", "") + "-" + sc["away_team"] + "-" + sc["home_team"] \
        + "-" + sc["game_pk"].astype(str)
    tm["GameUID"] = sc["game_pk"].astype(str)
    # Not a TrackMan id: the Statcast pitch, so the round trip can match
    # every pitch back to the MLB build.
    tm["PitchUID"] = (sc["game_pk"].astype(str) + "-" + sc["at_bat_number"].astype(str) + "-"
                      + sc["pitch_number"].astype(str))
    return tm


def heights_roster(sc):
    """Each hitter's height, read back off his 2026 zone (top = 53.5% of
    his height), as a roster CSV would list it. A hitter Statcast has no
    zone for is left off, as a roster can miss a player."""

    top = sc.dropna(subset=["sz_top"]).groupby("batter")["sz_top"].agg(lambda s: s.mode().iloc[0])
    return pd.DataFrame({"BatterId": top.index, "HeightIn": (top * 12 / 0.535).round(2).to_numpy()})


def write_games(tm, folder):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.csv"):
        old.unlink()
    for game_id, rows in tm.groupby("GameID", sort=False):
        rows.to_csv(folder / f"{game_id}.csv", index=False)
    return tm["GameID"].nunique()


def main():
    parser = argparse.ArgumentParser(description="2026 Statcast games as TrackMan CSVs.")
    parser.add_argument("--team", required=True, help="Statcast team code, e.g. KC")
    parser.add_argument("--games", type=int, default=60)
    parser.add_argument("--out", required=True, help="folder for the game CSVs")
    parser.add_argument("--heights", required=True, help="roster CSV to write")
    parser.add_argument("--plate-side-sign", type=float, default=-1.0)
    args = parser.parse_args()
    sc = team_games(load_statcast(), args.team, args.games)
    register = pd.read_parquet(RAW / "chadwick_register.parquet")
    tm = to_trackman(sc, register, args.plate_side_sign)
    n = write_games(tm, args.out)
    Path(args.heights).parent.mkdir(parents=True, exist_ok=True)
    heights_roster(sc).to_csv(args.heights, index=False)
    print(f"Wrote {n} games ({len(tm):,} pitches) to {args.out} and heights to {args.heights}")


if __name__ == "__main__":
    sys.exit(main())
