"""
Step 19: write down, before the 2027 season, what the cards' leaks should
do next.

Step 16's backtest is retrospective: every season it scores was played
before the method was built. This step freezes a prediction for every
2026 qualified hitter's card leaks before any 2027 pitch is thrown, so a
run of step 16 after 2027 can score the cards out of sample.

THE LEAKS
  The top 3 leaks on each 2026 card, against all pitchers (count group x
  pitch group x side of the zone missed), read from
  data/cleaned/card_players_2026.json (step 17). These are what the
  hitter was told, so they are frozen as they are, not re-picked. Hitters
  whose card lists no leak get a hitter row and nothing to predict.

2026 LEAK CHASING, ON THE BACKTEST'S SCALE
  The card prices its leaks against a smoothed, matchup-adjusted league
  baseline. Step 16 measures against a simpler one: the league's chase
  rate in the same season, count, distance bucket, pitch group and side
  of the zone (leak_rules.BACKTEST_LEAGUE_CELL). The frozen numbers use
  step 16's, on step 16's own pitches, so the 2027 run compares like with
  like:

      excess = (chases - the league's chases on the same pitches) / pitches

  For the hitter row it is pooled over his leaks, exactly as step 16's
  leak_excess. The card's own league rate rides along for reference.

  The backtest picks leaks with the same rule on its simpler baseline, so
  its top 3 can differ from the card's. Each leak row says whether the
  backtest's rule would also have listed it, and the hitter row whether
  it would have listed all of them. A card leak it would not list usually
  sits at or below the league on the simpler baseline, so it was not
  picked for chasing above the league on the scale the line below
  regresses, and the line may not fit it.

THE PREDICTION
  Leaks are a hitter's worst-looking spots, so part of each one is bad
  luck and shrinks next season with nobody doing anything. Step 16's
  season-to-season line says by how much:

      2027 excess = intercept + slope x 2026 excess

  read from leak_backtest_summary.csv and saved on every hitter row,
  because step 16 will refit the line once 2027 is in. The line was fit
  on a hitter's leaks together, so the prediction is on the hitter row
  only: a single leak is noisier and would shrink more.

THE COUNT CHECK
  Each leak's 2026 count check (step 15, as the card shows it): the shrunk
  xwOBA once a plate appearance reaches the leak's counts, against the
  league's. The hitter row weights his leaks by pitches, as step 16 does.

OUTPUT, in results/xchase/coaching/
  leak_predictions_2026.csv   one hitter row and up to three leak rows per
                              2026 qualified hitter, each stamped with the
                              freeze date and the commit it was made from

A frozen file is not rewritten. Run again, this step rebuilds the
predictions and checks them against the file: if they match (the stamps
aside) the file is left alone, and if they don't it stops rather than
change a prediction after the fact. It also refuses to write once the
pitch file has 2027 pitches in it.

Options: --freeze-date (default today), --commit (default this
checkout's HEAD, marked -dirty when a tracked file has changed), and
--overwrite to replace a frozen file whose predictions differ.

Run after steps 16 and 17.
"""

import argparse
from datetime import date
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import leak_rules as lr  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
CLEAN = PROJECT_DIR / "data" / "cleaned"
OUT = PROJECT_DIR / "results" / "xchase" / "coaching"

SEASON = 2026
PA_SCALE = 600
OUT_FILE = OUT / f"leak_predictions_{SEASON}.csv"
STAMPS = ["freeze_date", "made_from_commit"]
KEYS = ["game_pk", "at_bat_number", "pitch_number", "batter", "game_year"]


def head_commit():
    """This checkout's commit, marked -dirty when a tracked file other than
    the frozen file itself differs from it."""

    def git(*a):
        return subprocess.run(["git", *a], cwd=PROJECT_DIR, capture_output=True, text=True)

    sha = git("rev-parse", "--short", "HEAD")
    if sha.returncode != 0:
        raise SystemExit("Not a git checkout; pass --commit.")
    changed = git("status", "--porcelain", "--untracked-files=no", "--", ".",
                  f":(exclude){OUT_FILE.relative_to(PROJECT_DIR)}").stdout.strip()
    return sha.stdout.strip() + ("-dirty" if changed else "")


parser = argparse.ArgumentParser(description="Freeze the 2026 card leaks' predictions for 2027.")
parser.add_argument("--freeze-date", default=date.today().isoformat(),
                    help="date written on every row (default: today)")
parser.add_argument("--commit", default=None,
                    help="commit written on every row (default: this checkout's HEAD)")
parser.add_argument("--overwrite", action="store_true",
                    help="replace the frozen file even if its predictions differ")
args = parser.parse_args()
commit = args.commit or head_commit()

# --------------------------------------------------
# LOAD: step 16's pitches and league expectation, 2026 only
# --------------------------------------------------

print(f"Loading {SEASON} pitches...")
seasons = pd.read_parquet(CLEAN / "baseline_chase_pitches.parquet", columns=["game_year"])
later = int((seasons["game_year"] > SEASON).sum())
base = pd.read_parquet(CLEAN / "baseline_chase_pitches.parquet",
                       columns=KEYS + ["pitch_type", "is_analyzable", "plate_x_batter",
                                       "plate_z_normalized", "sz_top", "sz_bot"],
                       filters=[("game_year", "==", SEASON)])
costs = pd.read_parquet(CLEAN / "xchase_costs_by_pitch.parquet",
                        filters=[("game_year", "==", SEASON)])
card = json.loads((CLEAN / f"card_players_{SEASON}.json").read_text())
summary = pd.read_csv(OUT / "leak_backtest_summary.csv").set_index(["pair_kind", "measure", "test"])
intercept = float(summary.loc[("season", "leak_excess", "carried over (intercept)"), "value"])
slope = float(summary.loc[("season", "leak_excess", "carried over (slope)"), "value"])

# The same rows and labels as step 16: priced out-of-zone pitches with a
# location, labelled with the season's average zone height.
df = costs.merge(base, on=KEYS, how="left", validate="one_to_one")
df = df[df["plate_x_batter"].notna() & df["plate_z_normalized"].notna()].copy()
df = lr.add_labels(df, float((df["sz_top"] - df["sz_bot"]).mean()))
df = lr.add_choices_contact(df)
df["e"] = df.groupby(lr.BACKTEST_LEAGUE_CELL)["is_chase"].transform("mean")

cells = df.groupby(["batter"] + lr.LEAK_CELL).agg(
    pitches=("is_chase", "size"), chases=("is_chase", "sum"), expected=("e", "sum"))

# Plate appearances as step 16 counts them, for its leak rule's runs per 600
pa = (base[base["is_analyzable"] == 1].drop_duplicates(["game_pk", "at_bat_number", "batter"])
      .groupby("batter").size())

# --------------------------------------------------
# THE CARD'S LEAKS, MEASURED ON THE BACKTEST'S SCALE
# --------------------------------------------------

print("Measuring the card leaks...")
hitters = pd.DataFrame([{"batter": p["id"], "player": p["name"], "rank_2026": p["rank"],
                         "leaks": len(p["leaks"]["all"])} for p in card["players"]])
leaks = pd.DataFrame([
    {"batter": p["id"], "row": f"leak {n}",
     **{c: lk[c] for c in lr.LEAK_CELL},
     "card_pitches": lk["pitches"], "card_chases": lk["chases"],
     "card_league_rate_2026": lk["league"], "choices_runs_per_600_2026": lk["choices"],
     "count_xwoba_gap_2026": lk["count_xwoba_shrunk"] - lk["count_xwoba_league"],
     "count_status_2026": lk["count_status"]}
    for p in card["players"] for n, lk in enumerate(p["leaks"]["all"], start=1)])
leaks = leaks.join(cells, on=["batter"] + lr.LEAK_CELL)

# The card and the backtest must be counting the same pitches
off = leaks[(leaks["pitches"] != leaks["card_pitches"]) | (leaks["chases"] != leaks["card_chases"])]
if len(off):
    raise SystemExit(f"{len(off)} card leaks have different pitches or chases on step 16's "
                     f"pitches than on the card. Rebuild step 17 from the same data first.")

# Would step 16's own rule (its simpler baseline) also list each leak?
backtest_leaks = set()
for batter, mine in df[df["batter"].isin(hitters["batter"])].groupby("batter"):
    top = lr.leak_cells(mine, PA_SCALE / pa[batter], "e").head(lr.LEAK_TOP)
    backtest_leaks |= {(batter, *cell) for cell in top[lr.LEAK_CELL].itertuples(index=False)}
leaks["also_a_backtest_leak"] = np.where(
    [k in backtest_leaks for k in leaks[["batter"] + lr.LEAK_CELL].itertuples(index=False)],
    "yes", "no")

# The hitter row: his leaks pooled, as step 16's leak_excess
pooled = leaks.assign(
    card_expected=leaks["card_league_rate_2026"] * leaks["pitches"],
    count_gap_x_pitches=leaks["count_xwoba_gap_2026"] * leaks["pitches"],
).groupby("batter")[["pitches", "chases", "expected", "card_expected",
                     "choices_runs_per_600_2026", "count_gap_x_pitches"]].sum()
pooled["card_league_rate_2026"] = pooled["card_expected"] / pooled["pitches"]
pooled["count_xwoba_gap_2026"] = pooled["count_gap_x_pitches"] / pooled["pitches"]
pooled["count_status_2026"] = np.select(
    [pooled["count_xwoba_gap_2026"] <= -lr.COUNT_MARGIN,
     pooled["count_xwoba_gap_2026"] >= lr.COUNT_MARGIN], ["struggling", "productive"], "average")
hitters = hitters.join(pooled.drop(columns=["card_expected", "count_gap_x_pitches"]), on="batter")
hitters["row"] = "hitter"
every = leaks.groupby("batter")["also_a_backtest_leak"].agg(lambda v: "yes" if (v == "yes").all() else "no")
hitters["also_a_backtest_leak"] = hitters["batter"].map(every)

for frame in (hitters, leaks):
    frame["chase_rate_2026"] = frame["chases"] / frame["pitches"]
    frame["league_rate_2026"] = frame["expected"] / frame["pitches"]
    frame["excess_2026"] = (frame["chases"] - frame["expected"]) / frame["pitches"]

# --------------------------------------------------
# THE PREDICTION
# --------------------------------------------------

hitters["predicted_excess_2027"] = intercept + slope * hitters["excess_2026"]
has_leaks = hitters["leaks"] > 0
hitters.loc[has_leaks, "line_intercept"] = intercept
hitters.loc[has_leaks, "line_slope"] = slope

# --------------------------------------------------
# WRITE (or check against the frozen file)
# --------------------------------------------------

leaks = leaks.join(hitters.set_index("batter")[["player", "rank_2026"]], on="batter")
rows = pd.concat([hitters, leaks], ignore_index=True)
rows["season"] = SEASON
rows["freeze_date"] = args.freeze_date
rows["made_from_commit"] = commit
for c in ("leaks", "pitches", "chases"):
    rows[c] = rows[c].astype("Int64")
rows = rows.rename(columns={"pitches": "pitches_2026", "chases": "chases_2026"})
columns = ["season", "rank_2026", "player", "batter", "row", "leaks", "count_group",
           "pitch_group", "region", "pitches_2026", "chases_2026", "chase_rate_2026",
           "league_rate_2026", "excess_2026", "predicted_excess_2027", "line_intercept",
           "line_slope", "card_league_rate_2026", "choices_runs_per_600_2026",
           "also_a_backtest_leak", "count_xwoba_gap_2026", "count_status_2026"] + STAMPS
rows = rows.sort_values(["rank_2026", "batter", "row"])[columns]
text = rows.to_csv(index=False, float_format="%.4f", lineterminator="\n")

if OUT_FILE.exists():
    frozen = pd.read_csv(OUT_FILE, dtype=str, keep_default_na=False)
    fresh = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    if frozen.drop(columns=STAMPS).equals(fresh.drop(columns=STAMPS)):
        print(f"\nThe predictions match {OUT_FILE.relative_to(PROJECT_DIR)}, frozen on "
              f"{frozen['freeze_date'].iloc[0]} from commit {frozen['made_from_commit'].iloc[0]}."
              + (" Rewriting its stamps (--overwrite)." if args.overwrite else
                 " Left as it is."))
        write = args.overwrite
    elif args.overwrite:
        print("\nThe predictions differ from the frozen file; replacing it (--overwrite).")
        write = True
    else:
        raise SystemExit(f"The predictions differ from {OUT_FILE.relative_to(PROJECT_DIR)}, "
                         f"frozen on {frozen['freeze_date'].iloc[0]}. A frozen prediction is not "
                         f"changed after the fact; pass --overwrite only to replace it before "
                         f"any 2027 pitch is in the data.")
else:
    write = True

if write and later:
    raise SystemExit(f"The pitch file already has {later:,} pitches from after {SEASON}, so "
                     f"predictions written now would not be out of sample. Not writing.")
if write:
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(text)

# --------------------------------------------------
# REPORT
# --------------------------------------------------

h = hitters[has_leaks]
top = leaks[leaks["row"] == "leak 1"]
print(f"\n{len(hitters)} qualified hitters, {has_leaks.sum()} with leaks on the card "
      f"({len(leaks)} leaks).")
print(f"Card leaks the backtest's rule also lists: {(leaks['also_a_backtest_leak'] == 'yes').sum()} "
      f"of {len(leaks)} (top leak: {(top['also_a_backtest_leak'] == 'yes').sum()} of {len(top)}).")
print(f"Leak chasing, points above the league: {h['excess_2026'].mean() * 100:.1f} in {SEASON}, "
      f"predicted {h['predicted_excess_2027'].mean() * 100:.1f} in {SEASON + 1} "
      f"(next = {intercept * 100:+.1f} + {slope:.2f} x {SEASON}).")
for answer, label in (("yes", "every leak also a backtest leak"), ("no", "some leak not")):
    g = h[h["also_a_backtest_leak"] == answer]
    print(f"  {label:32s} {len(g):3d} hitters: {g['excess_2026'].mean() * 100:5.1f} -> "
          f"{g['predicted_excess_2027'].mean() * 100:5.1f}")
print("Count check in the leaks' counts: "
      + ", ".join(f"{s} {(h['count_status_2026'] == s).sum()}"
                  for s in ("struggling", "average", "productive")))
if write:
    print(f"\nWrote {OUT_FILE.relative_to(PROJECT_DIR)} (frozen {args.freeze_date}, commit {commit}).")
