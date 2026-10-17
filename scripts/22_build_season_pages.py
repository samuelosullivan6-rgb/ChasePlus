"""
Step 22: the card site, every season.

Step 17 builds one season's page, results/xchase/player_cards/<season>/
(the decision cards and the roster view, their pitches and the reference
cards). This step runs it for every season, so the pages agree: the same
wording on every card and the same season list in every switcher. A
change to the plan's wording in step 17 is a run of this step, not of step
17 alone; the 2025 card data once went stale because only 2026 had been
rebuilt.

For each season, oldest first:

  1. THE TARGET. A card's target comes from the season's frozen prediction
     file (step 19). When results/xchase/coaching/leak_predictions_<season>.csv
     is missing and a later season is already in the data, it is frozen
     retrospectively here: step 17 --data-only for the card leaks, then
     step 19 --retrospective, stamped out_of_sample = no, with its line fit
     only on season pairs that end by that season. The oldest season has no
     such pairs, so its cards carry no target. The newest season is never
     frozen here: that is step 19 run by hand before the next season starts,
     and a frozen file is never rewritten.
  2. step 17 --season <season>: the page (cards and roster), pitches.bin,
     the reference cards, and for 2026 the noted hitters' cards and report.

The season switcher on every page reads player_cards/seasons.js, which
step 17 rewrites from the folders on disk, so a season built later
appears in every page's switcher without rebuilding the others.

Options: --seasons 2024 2025 (default: every season with an xChase+
leaderboard), --skip-freeze (build the pages with whatever frozen files
exist), --skip-png (passed to step 17: no reference or noted cards).

Needs the inputs of step 17 for each season: steps 04
(--expected-contact), 13, 15 and 16, and the raw Statcast files (step 01)
for the teams.
"""

import argparse
from pathlib import Path
import re
import subprocess
import sys
import time

PROJECT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
XCHASE = PROJECT_DIR / "results" / "xchase"
COACHING = XCHASE / "coaching"

parser = argparse.ArgumentParser(description="The card site for every season.")
parser.add_argument("--seasons", nargs="*", type=int, default=None,
                    help="seasons to build (default: every season with an xChase+ leaderboard)")
parser.add_argument("--skip-freeze", action="store_true",
                    help="do not freeze a missing prediction file; build with what exists")
parser.add_argument("--skip-png", action="store_true", help="passed to step 17")
args = parser.parse_args()

available = sorted(int(m.group(1)) for f in XCHASE.glob("xchase_leaderboard_????.csv")
                   if (m := re.fullmatch(r"xchase_leaderboard_(\d{4})", f.stem)))
if not available:
    raise SystemExit("No xchase_leaderboard_<season>.csv in results/xchase/ (run step 04).")
seasons = sorted(args.seasons) if args.seasons else available
unknown = [s for s in seasons if s not in available]
if unknown:
    raise SystemExit(f"No leaderboard for {unknown}; seasons with one: {available}")
newest_in_data = max(available)


def run(step, *options, capture=False):
    """Run one step with this interpreter; print how long it took."""
    script = next(SCRIPTS.glob(f"{step}_*.py"))
    cmd = [sys.executable, str(script), *options]
    print(f"\n$ python {' '.join(Path(c).name if c.endswith('.py') else c for c in cmd[1:])}", flush=True)
    t0 = time.time()
    result = subprocess.run(cmd, cwd=PROJECT_DIR, text=True, capture_output=capture)
    print(f"  ({step} took {time.time() - t0:.0f} s)", flush=True)
    return result


started = time.time()
for season in seasons:
    print(f"\n{'=' * 24} {season} {'=' * 24}")
    frozen = COACHING / f"leak_predictions_{season}.csv"
    if frozen.exists():
        print(f"targets: {frozen.name} is frozen; the cards carry it")
    elif args.skip_freeze:
        print(f"targets: {frozen.name} is missing (--skip-freeze): no target on these cards")
    elif season >= newest_in_data:
        print(f"targets: {frozen.name} is missing. The newest season is frozen by hand "
              f"(step 19, before the next season starts), not here: no target on these cards")
    else:
        print(f"targets: {frozen.name} is missing; freezing it retrospectively")
        if run("17", "--season", str(season), "--data-only").returncode:
            raise SystemExit(f"step 17 --data-only failed for {season}")
        r = run("19", "--season", str(season), "--retrospective", capture=True)
        sys.stdout.write(r.stdout)
        if r.returncode:
            if "No season pairs end by" in (r.stderr or "") + (r.stdout or ""):
                print(f"  no season pairs end by {season}, so there is no line to predict "
                      f"with: no target on the {season} cards")
            else:
                sys.stderr.write(r.stderr or "")
                raise SystemExit(f"step 19 --retrospective failed for {season}")
    if run("17", "--season", str(season), *(["--skip-png"] if args.skip_png else [])).returncode:
        raise SystemExit(f"step 17 failed for {season}")

print(f"\nBuilt {len(seasons)} season{'s' if len(seasons) != 1 else ''} "
      f"({', '.join(map(str, seasons))}) in {(time.time() - started) / 60:.1f} min. "
      f"player_cards/index.html sends to the newest; teams.html into its roster view.")
