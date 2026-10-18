"""
The college path: TrackMan game CSVs in, xChase+ and decision cards out.

    python scripts/college_build.py --name clemson_2026 \\
        --trackman college/clemson_2026/trackman --heights college/clemson_2026/heights.csv

Everything goes into college/<name>/, which .gitignore keeps out of the
repository, so a team's data is never committed and GitHub Pages (which
serves only what is committed) never publishes it. Nothing is written
into results/ or data/ of the MLB build.

WHAT IT DOES, IN ORDER

  1. trackman_adapter.py: the TrackMan rows as Statcast pitches, the
     hitters' zones from the heights roster, runners and score rebuilt.
  2. college_method.py: run values from the files' own plate
     appearances (step 03's tables), wOBA weights from those run values,
     and an xwOBA fit on the files' own batted balls.
  3. Step 02, unchanged: the pitches written as a Statcast raw file in
     college/<name>/data/raw/ and cleaned and labelled exactly as the MLB
     build cleans them.
  4. college_method.py: every chase decision priced as step 04 prices it,
     with the college settings (see that file), for Chase+ and xChase+,
     written in step 04's and step 09's file formats.
  5. Steps 13, 15 and 17, unchanged: the choices / contact split and
     archetypes, the count check, and the cards page with its roster
     view, college/<name>/results/xchase/player_cards/<season>/index.html.
     Step 17 checks every plan against the numbers beside it before it
     draws a card, as it does for MLB.

Steps 02, 13, 15 and 17 run from copies in college/<name>/scripts/, so
their folders are the college build's. A copy that differs from the MLB
script lists what differs at its top: step 02 keeps the college season
(SEASONS_TO_KEEP); step 17 has no coach's notes (NOTED_SEASON), reads
heights back with the adapter's zone share (ABS_TOP_SHARE, 53.5% as in
MLB), says TrackMan, not Statcast, in its page footer, and says the card
footer's "Does fixing a leak pay?" finding is from MLB hitters (step 16
needs the same hitters in back-to-back seasons). The copy of its page
template (templates/player_cards.html) leaves out the roster's Beat
column and the sentences about the target: step 19 freezes the target,
and a college build never has one. Steps 13 and 15 are copied as they
are.

The page needs a web server, not a double-click (it fetches its pitches):

    cd college/<name> && python -m http.server 8000
    open http://localhost:8000/results/xchase/player_cards/<season>/index.html

college/<name>/BUILD.md lists what the build found and chose.
"""

import argparse
import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
COLLEGE_DIR = PROJECT_DIR / "college"
sys.path.insert(0, str(SCRIPTS_DIR))
import college_method as cm  # noqa: E402
import trackman_adapter as ta  # noqa: E402

MLB_BACKTEST = PROJECT_DIR / "results" / "xchase" / "coaching" / "leak_backtest_summary.csv"

# The college path's own files, which the copies of the MLB steps never need.
NOT_COPIED = ("college_*.py", "trackman_*.py", "statcast_to_trackman.py", "__pycache__")

# The card footer (step 17's EVIDENCE_LINE) is the MLB backtest's finding:
# step 16 needs the same hitters in back-to-back seasons, so a college card
# says whose finding it is.
MLB_EVIDENCE = '''\
    f"{EVIDENCE_QUESTION} Hitters who cut their leak chasing more than expected stopped giving "
    "counts away: more walks, no more strikeouts, still swinging at strikes. The gain was mostly "
    "runs not lost; hits come later, if they come.")'''
COLLEGE_EVIDENCE = '''\
    f"{EVIDENCE_QUESTION} In MLB, hitters who cut their leak chasing more than expected walked "
    "more, struck out no more and still swung at strikes; the gain was mostly runs not lost. "
    "Testing it on these hitters takes a second season.")'''

# The target is what step 19's frozen line expects next season with no
# change. A college build has one season and no line to freeze, so its
# page drops the roster's Beat column and every sentence about the target.
NO_TARGET = [
    (" Beat is the number to get under in ${D.season + 1}: what the frozen line expects with no "
     "change at all, with this season's number beside it.", ""),
    (" Beat: how far above the league's chase rate, in points, the frozen line expects the hitter "
     "to chase in all of the card's leaks next season with no change, with this season's number "
     "beside it (step 19); a fix is anything under it, and a card whose leaks are all video items "
     "has none.", ""),
    (' ["target", "Beat", true],', ""),
    (" The target counts all pitchers.", ""),
]


# --------------------------------------------------
# RUNNING AN MLB STEP ON THE COLLEGE FILES
# --------------------------------------------------

def override_settings(source, settings, label):
    """Replace top-level NAME = <literal> assignments (step 07 reads the
    same assignments with ast). Each name must be assigned exactly once."""

    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    starts = np.cumsum([0] + [len(line.encode()) for line in lines])
    data = source.encode()
    spans = []
    for name, value in settings.items():
        nodes = [n for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name]
        if len(nodes) != 1:
            raise SystemExit(f"{label}: expected one top-level {name} = ..., found {len(nodes)}. "
                             "The MLB script changed; update college_build.py.")
        v = nodes[0].value
        # ast offsets are UTF-8 byte columns
        spans.append((starts[v.lineno - 1] + v.col_offset,
                      starts[v.end_lineno - 1] + v.end_col_offset, repr(value)))
    for start, end, text in sorted(spans, reverse=True):
        data = data[:start] + text.encode() + data[end:]
    return data.decode()


def replace_once(source, old, new, label):
    if source.count(old) != 1:
        raise SystemExit(f"{label}: expected the text {old!r} once, found {source.count(old)}. "
                         "The MLB script changed; update college_build.py.")
    return source.replace(old, new)


def copy_steps(workspace, changes):
    """scripts/ into college/<name>/scripts/, with `changes` (file under
    scripts/ -> {"settings": {...}, "replace": [(old, new), ...]}) applied
    and listed at the top of each changed copy: a comment in a script, an
    HTML comment in a page template ("settings" is for scripts only)."""

    target = workspace / "scripts"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(SCRIPTS_DIR, target, ignore=shutil.ignore_patterns(*NOT_COPIED))
    for name, change in changes.items():
        path = target / name
        text = path.read_text()
        if change.get("settings"):
            if path.suffix != ".py":
                raise SystemExit(f"{name}: settings are for scripts; change a template with replace.")
            text = override_settings(text, change["settings"], name)
        for old, new in change.get("replace", []):
            text = replace_once(text, old, new, name)
        listed = [f"{k} = {v!r}" for k, v in change.get("settings", {}).items()]
        listed += [f"text {old!r} -> {new!r}" for old, new in change.get("replace", [])]
        if path.suffix == ".html":
            if any("--" in line for line in listed):
                raise SystemExit(f"{name}: a change listed in an HTML comment cannot contain '--'.")
            header = ("<!-- College copy, written by college_build.py from scripts/" + name
                      + ". Changed from the MLB file:\n"
                      + "".join(f"       {line}\n" for line in listed) + "-->\n")
        else:
            header = ("# College copy, written by college_build.py from scripts/" + name
                      + ". Changed from the MLB script:\n"
                      + "".join(f"#   {line}\n" for line in listed) + "\n")
        path.write_text(header + text)


def run_step(workspace, script, *args, log):
    """Run one copied step in the college workspace, its output kept in
    the build log and the last lines shown."""

    command = [sys.executable, str(workspace / "scripts" / script), *map(str, args)]
    print(f"\n--- {script} {' '.join(map(str, args))}".rstrip())
    run = subprocess.run(command, cwd=workspace, capture_output=True, text=True)
    log.write(f"\n\n===== {script} {' '.join(map(str, args))} =====\n{run.stdout}{run.stderr}")
    shown = (run.stdout + run.stderr).strip().splitlines()
    for line in shown[-12:]:
        print(f"    {line}")
    if run.returncode:
        raise SystemExit(f"{script} failed in {workspace} (exit {run.returncode}); "
                         f"the full output is in {log.name}.")
    return run.stdout


# --------------------------------------------------
# THE BUILD
# --------------------------------------------------

# What a build writes in college/<name>/. A rebuild clears these first, so
# nothing from an earlier build lingers; the TrackMan files and the roster
# are never in them.
BUILT = ("data", "results", "scripts")


def build(name, trackman, heights, season=None, sign="auto"):
    workspace = COLLEGE_DIR / name
    inputs = [Path(p).resolve() for p in list(trackman) + [heights]]
    for folder in BUILT:
        target = (workspace / folder).resolve()
        if any(target == p or target in p.parents for p in inputs):
            raise SystemExit(f"Keep the TrackMan files and the roster out of college/{name}/{folder}/: "
                             "a build rewrites that folder.")
    if (workspace / "build_log.txt").exists():
        for folder in BUILT:
            shutil.rmtree(workspace / folder, ignore_errors=True)
    for folder in ("data/raw", "data/cleaned", "results/run_values", "results/xchase/coaching",
                   "results/xchase/player_cards", "results/chase"):
        (workspace / folder).mkdir(parents=True, exist_ok=True)
    log = open(workspace / "build_log.txt", "w")
    facts = {"name": name}

    # 1. The adapter
    print("Reading the TrackMan files...")
    pitches, report = ta.adapt(ta.read_trackman(trackman), ta.load_heights(heights), sign,
                               season=season)
    seasons = sorted(pitches["game_year"].unique())
    if len(seasons) != 1:
        raise SystemExit(f"The files span seasons {seasons}; build one season at a time "
                         "(--season, or one season's files).")
    season = int(seasons[0])
    facts.update(season=season, adapter=report)
    print(f"  {report['games']} games, {report['pitches']:,} pitches, "
          f"{report['plate_appearances']:,} plate appearances, {report['hitters']} hitters")

    # 2. Run values, wOBA weights, xwOBA
    print("Run values from the files' plate appearances...")
    settings = cm.COLLEGE_SETTINGS
    rv = cm.run_value_tables(pitches, settings)
    weights = cm.woba_weights(rv["events"])
    pitches["woba_value"], pitches["woba_denom"] = cm.woba_columns(pitches, weights)
    in_play = pitches["description"] == "hit_into_play"
    predict, xfit = cm.fit_xwoba(pitches[in_play])
    pitches.loc[in_play, "estimated_woba_using_speedangle"] = predict(pitches[in_play]).to_numpy()
    tracked = in_play & pitches["launch_speed"].notna() & pitches["launch_angle"].notna()
    facts.update(woba_weights={k: round(v, 3) for k, v in weights.items()}, xwoba=xfit,
                 balls_in_play=int(in_play.sum()), tracked_share=round(float(tracked.sum() / max(in_play.sum(), 1)), 3))
    print(f"  wOBA weights: " + ", ".join(f"{k} {v:.2f}" for k, v in weights.items()))
    print(f"  xwOBA: {xfit['neighbors']} nearest of {xfit['batted_balls']:,} tracked batted balls "
          f"(launch angle weight {xfit['angle_weight']})")

    # 3. Step 02, unchanged
    raw_file = workspace / "data" / "raw" / f"statcast_{season}-trackman.parquet"
    pitches.to_parquet(raw_file, index=False)
    ta.name_register(pitches).to_parquet(workspace / "data" / "raw" / "chadwick_register.parquet",
                                         index=False)
    changes = {
        "02_build_chase_dataset.py": {"settings": {"SEASONS_TO_KEEP": [season]}},
        "17_build_player_cards.py": {
            "settings": {"NOTED_SEASON": None, "ABS_TOP_SHARE": ta.ZONE_TOP_SHARE},
            "replace": [('f"xChase+ 1.1 · Statcast {SEASON} · ',
                         'f"xChase+ 1.1, college path · TrackMan {SEASON} · '),
                        (MLB_EVIDENCE, COLLEGE_EVIDENCE)],
        },
        "templates/player_cards.html": {"replace": NO_TARGET},
    }
    copy_steps(workspace, changes)
    run_step(workspace, "02_build_chase_dataset.py", log=log)
    clean = pd.read_parquet(workspace / "data" / "cleaned" / "baseline_chase_pitches.parquet")

    # 4. Pricing, step 04's way with the college settings
    print("\nPricing every chase decision...")
    rv["base_out"].to_csv(workspace / "results" / "run_values" / "run_expectancy_base_out.csv", index=False)
    rv["events"].to_csv(workspace / "results" / "run_values" / "run_value_by_event.csv", index=False)
    rv["counts"].to_csv(workspace / "results" / "run_values" / "run_value_by_count.csv", index=False)
    rv["plate_appearances"].to_parquet(workspace / "data" / "cleaned" / "plate_appearance_run_values.parquet",
                                       index=False)
    tables = {}
    for expected, folder, stem in ((False, "chase", "chase"), (True, "xchase", "xchase")):
        opp, diag = cm.price(clean, rv, settings, expected_contact=expected)
        q, everyone, scale = cm.hitter_seasons(opp, clean, settings)
        q = q.merge(register_names(workspace), on="batter", how="left")
        out = workspace / "results" / folder
        cm.for_saving(q[cm.LEADERBOARD_COLUMNS].sort_values("runs_saved_shrunk", ascending=False),
                      expected).to_csv(out / f"chase_cost_leaderboard_{season}.csv", index=False)
        cm.for_saving(scale.assign(stat_version=f"{'xChase+ 1.1' if expected else 'Chase+ 2.0'}, college path"),
                      expected).to_csv(out / "chase_plus_league_scale.csv", index=False)
        opp[cm.PITCH_COST_COLUMNS].to_parquet(workspace / "data" / "cleaned" / f"{stem}_costs_by_pitch.parquet",
                                             index=False)
        tables[stem] = (opp, diag, q, everyone, scale)
    xopp, xdiag, xq, xeveryone, xscale = tables["xchase"]
    cq = tables["chase"][2]
    board = xq[["batter", "player", "game_year", "plate_appearances", "chase_rate", "chase_plus",
                "chase_plus_posterior_sd", "chases"]].rename(
        columns={"chase_plus": "xchase_plus", "chase_plus_posterior_sd": "xchase_plus_posterior_sd"})
    board = board.merge(cq[["batter", "chase_plus", "chase_plus_posterior_sd"]], on="batter", how="left")
    in_play_chases = (xopp[(xopp["is_chase"] == 1) & (xopp["description"] == "hit_into_play")]
                      .groupby("batter").size().rename("chases_in_play"))
    board = board.join(in_play_chases, on="batter")
    board["chases_in_play"] = board["chases_in_play"].fillna(0).astype(int)
    board["luck"] = board["chase_plus"] - board["xchase_plus"]
    board["xchase_plus_rank"] = board["xchase_plus"].rank(ascending=False, method="first")
    board["chase_plus_rank"] = board["chase_plus"].rank(ascending=False, method="first")
    board["rank_move"] = board["xchase_plus_rank"] - board["chase_plus_rank"]
    board = board.sort_values("xchase_plus_rank")[
        ["xchase_plus_rank", "player", "batter", "game_year", "plate_appearances", "chase_rate",
         "xchase_plus", "xchase_plus_posterior_sd", "chase_plus", "chase_plus_posterior_sd",
         "chase_plus_rank", "rank_move", "luck", "chases", "chases_in_play"]]
    board.to_csv(workspace / "results" / "xchase" / f"xchase_leaderboard_{season}.csv", index=False)
    s = xscale.iloc[0]
    facts.update(qualified=int(s["qualified"]), shrinkage_pool=int(s["shrinkage_pool"]),
                 league_chase_rate=round(float(s["league_chase_rate"]), 1),
                 league_chase_cost_per_600_pa=round(float(s["league_chase_cost_per_600_pa"]), 2),
                 talent_sd_xchase_plus=round(float(s["talent_sd_chase_plus"]), 1),
                 takes_for_called_strike_model=int(xdiag["takes"]),
                 xwoba_line=xdiag["xwoba_line"].round(4).to_dict("records"),
                 baseline_cells=int(len(xdiag["baseline_cells"])),
                 smallest_baseline_cell=int(xdiag["baseline_cells"]["league_pitches"].min()))
    print(f"  {int(s['qualified'])} qualified hitters (floors {settings['minimum_plate_appearances']} PA, "
          f"{settings['minimum_opportunities']} out-of-zone pitches); the league lost "
          f"{s['league_chase_cost_per_600_pa']:.1f} runs per 600 PA to chasing")
    if not len(board):
        raise SystemExit("No hitter cleared the floors, so there are no cards to draw.")

    # 5. Steps 13, 15 and 17, unchanged
    shutil.copy(MLB_BACKTEST, workspace / "results" / "xchase" / "coaching" / MLB_BACKTEST.name)
    run_step(workspace, "13_build_actionability_profiles.py", log=log)
    run_step(workspace, "15_build_count_check.py", log=log)
    run_step(workspace, "17_build_player_cards.py", "--season", season, "--skip-png", log=log)
    log.close()

    cards = pd.read_csv(workspace / "results" / "xchase" / "player_cards" / f"player_cards_{season}.csv")
    write_report(workspace, facts, settings, board, cards)
    (workspace / "build_facts.json").write_text(json.dumps(facts, indent=2, default=str))
    page = workspace / "results" / "xchase" / "player_cards" / str(season) / "index.html"
    print(f"\nDone. Cards: {page.relative_to(PROJECT_DIR)}  (serve college/{name} with "
          f"python -m http.server; see BUILD.md)")
    return workspace


def register_names(workspace):
    reg = pd.read_parquet(workspace / "data" / "raw" / "chadwick_register.parquet")
    return pd.DataFrame({"batter": reg["key_mlbam"].astype("int64"),
                         "player": (reg["name_first"].str.strip() + " " + reg["name_last"].str.strip()).str.strip()})


def sign_evidence(a):
    e = a.get("plate_side_evidence", {})
    if not e.get("hit_by_pitches"):
        return "No hit-by-pitches with a location: the sign was set by hand."
    inside = e["inside_if_plus"] if a["plate_side_sign"] > 0 else 1 - e["inside_if_plus"]
    text = f"With it, {inside:.0%} of the files' {e['hit_by_pitches']} hit-by-pitches are inside."
    if e.get("rhp_median_relside") is not None:
        text += (f" Right-handed pitchers' median RelSide is {e['rhp_median_relside']:+.2f} ft "
                 f"({a['plate_side_sign'] * e['rhp_median_relside']:+.2f} on Statcast's side, "
                 "where it should be negative).")
    return text


def write_report(workspace, facts, settings, board, cards):
    a = facts["adapter"]
    lines = [
        f"# College build: {facts['name']}, {facts['season']}",
        "",
        "Built by `scripts/college_build.py`. Team data: this folder is in .gitignore and is "
        "never committed or published.",
        "",
        "## What was in the files",
        "",
        f"- {a['games']} games, {a['pitches']:,} pitches, {a['plate_appearances']:,} plate "
        f"appearances, {a['hitters']} hitters (the team's and every opponent's: the league).",
        f"- PlateLocSide sign: plate_x = {'+' if a['plate_side_sign'] > 0 else '-'}PlateLocSide. "
        + sign_evidence(a),
        f"- Outs on each play are read from the Outs column; where the file also has OutsOnPlay, "
        f"the two agree on {a.get('outs_on_play_agree_with_outs_column', float('nan')):.1%} of "
        f"the pitches that end a plate appearance. {a['truncated_plate_appearances']} plate "
        "appearances end with no result (the third out on the bases).",
        f"- {a['untracked_location']} pitches with no location and {a['pitches_without_a_type']} "
        "with no pitch call or type: not read as decisions.",
        f"- Hitters missing from the heights roster (median height used): "
        f"{', '.join(a['hitters_without_height']) or 'none'}.",
        f"- Balls in play: {facts['balls_in_play']:,}, {facts['tracked_share']:.0%} with exit "
        "speed and launch angle.",
        "",
        "## What the build fit on them",
        "",
        "- wOBA weights from the files' run values: "
        + ", ".join(f"{k.replace('_', ' ')} {v:.2f}" for k, v in facts["woba_weights"].items()) + ".",
        f"- xwOBA: the average of the {facts['xwoba']['neighbors']} nearest of "
        f"{facts['xwoba']['batted_balls']:,} tracked batted balls in exit speed and launch angle.",
        f"- Called-strike model on {facts['takes_for_called_strike_model']:,} out-of-zone takes.",
        f"- League baseline: {facts['baseline_cells']} cells (12 counts x "
        f"{len(settings['distance_labels'])} distance buckets: "
        f"{', '.join(settings['distance_labels'])}); the smallest has "
        f"{facts['smallest_baseline_cell']} pitches.",
        f"- The league chased {facts['league_chase_rate']}% of pitches outside the zone and lost "
        f"{facts['league_chase_cost_per_600_pa']} runs per 600 PA to it.",
        f"- {facts['qualified']} hitters qualified ({settings['minimum_plate_appearances']} PA and "
        f"{settings['minimum_opportunities']} out-of-zone pitches); the spread between hitters was "
        f"fit on {facts['shrinkage_pool']} hitters with {settings['shrink_pool_minimum_opportunities']}+ "
        f"out-of-zone pitches: {facts['talent_sd_xchase_plus']} xChase+ points.",
        "",
        "## Hitters",
        "",
        "| Rank | Hitter | PA | Chase% | xChase+ ± 1 SD | Top leak | Start with |",
        "|---:|---|---:|---:|---|---|---|",
    ]
    c = cards.set_index("batter")
    for r in board.itertuples():
        top = c.loc[r.batter, "top_leak"] if r.batter in c.index else ""
        start = c.loc[r.batter, "start_with"] if r.batter in c.index else ""
        lines.append(f"| {int(r.xchase_plus_rank)} | {r.player} | {int(r.plate_appearances)} | "
                     f"{r.chase_rate:.1f}% | **{r.xchase_plus:.0f}** ± {r.xchase_plus_posterior_sd:.0f} | "
                     f"{top if isinstance(top, str) else ''} | {start if isinstance(start, str) else ''} |")
    lines += ["", "## The cards", "",
              f"`results/xchase/player_cards/{facts['season']}/index.html`, with the roster view at "
              "`#roster`. Serve this folder (`python -m http.server 8000`) and open "
              f"`http://localhost:8000/results/xchase/player_cards/{facts['season']}/index.html`.",
              "", "Every step's full output is in `build_log.txt`."]
    (workspace / "BUILD.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="TrackMan CSVs -> xChase+ and decision cards.")
    parser.add_argument("--name", required=True, help="the build's folder under college/")
    parser.add_argument("--trackman", nargs="+", required=True, help="TrackMan CSVs, or folders")
    parser.add_argument("--heights", required=True, help="roster CSV with each hitter's height")
    parser.add_argument("--season", type=int, default=None, help="if the files' dates span two")
    parser.add_argument("--plate-side-sign", default="auto", choices=["auto", "+1", "-1"])
    args = parser.parse_args()
    build(args.name, args.trackman, args.heights, args.season, args.plate_side_sign)


if __name__ == "__main__":
    sys.exit(main())
