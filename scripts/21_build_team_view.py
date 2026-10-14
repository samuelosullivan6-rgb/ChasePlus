"""
Step 21: the roster on one page.

Every other report is one hitter at a time. A staff needs its hitters
side by side: who loses the most to chasing, what kind of problem it is,
the one pitch to start with, and the target. This step puts every
qualified hitter on one page with a team filter, sorted by runs at
stake, each row linking to the hitter's decision card.

TEAM
  Statcast's pitch file has no batter team, only the home and away
  teams of each game. A hitter's team on a pitch is the home team when
  he bats in the bottom of the inning and the away team otherwise. His
  team for the season is the one he had the most plate appearances for;
  a traded hitter lists every team, most plate appearances first, and
  appears under each of them in the filter.

COLUMNS (from player_cards_<season>.csv, step 17, plus the team)
  team, player, bats, xChase+ and rank, PA, runs at stake (choices on
  far-off pitches), choices, contact, archetype, the top leak and its
  runs, the count check in that leak's counts, the target (this season's
  leak excess and next season's with no change) and the plan.

OUTPUTS, in results/xchase/player_cards/
  team_view_<season>.csv   one row per qualified hitter, with team
  teams.html               the page: filter by team, sort any column,
                           search by name; each name links to the
                           hitter's card in index.html

Options: --season (default 2026).

Run after step 17. Needs the raw Statcast files in data/raw/ for the
season (step 01), for the team columns.
"""

import argparse
import json
from pathlib import Path
import re
import unicodedata

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
RAW = PROJECT_DIR / "data" / "raw"
CARDS_DIR = PROJECT_DIR / "results" / "xchase" / "player_cards"

parser = argparse.ArgumentParser(description="The roster on one page.")
parser.add_argument("--season", type=int, default=2026)
args = parser.parse_args()
SEASON = args.season


def slug(name):
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "_" for c in plain.lower()).strip("_")


# --------------------------------------------------
# TEAMS, FROM THE RAW PITCH FILES
# --------------------------------------------------

files = sorted(RAW.glob(f"statcast_{SEASON}-*.parquet"))
if not files:
    raise SystemExit(f"No raw Statcast files for {SEASON} in data/raw/ (run step 01).")
print(f"Reading teams from {len(files)} raw files...")
cols = ["batter", "game_pk", "at_bat_number", "home_team", "away_team", "inning_topbot"]
raw = pd.concat([pd.read_parquet(f, columns=cols) for f in files], ignore_index=True)
raw = raw.drop_duplicates(["game_pk", "at_bat_number", "batter"])
raw["team"] = raw["home_team"].where(raw["inning_topbot"] == "Bot", raw["away_team"])
by_team = raw.groupby(["batter", "team"]).size().rename("pa").reset_index()
by_team = by_team.sort_values(["batter", "pa"], ascending=[True, False])
teams = by_team.groupby("batter")["team"].agg(list)

# --------------------------------------------------
# THE ROWS
# --------------------------------------------------

cards = pd.read_csv(CARDS_DIR / f"player_cards_{SEASON}.csv")
cards["team"] = cards["batter"].map(lambda b: teams.get(b, ["?"])[0])
cards["teams"] = cards["batter"].map(lambda b: ", ".join(teams.get(b, ["?"])))
cards["slug"] = cards["player"].map(slug)
cards = cards.sort_values("runs_at_stake_far_off", ascending=False)
missing = int((cards["team"] == "?").sum())
if missing:
    print(f"  {missing} hitters with no team found in the raw files")

keep = ["team", "teams", "player", "batter", "slug", "bats", "xchase_plus", "xchase_plus_rank",
        "plate_appearances", "runs_at_stake_far_off", "choices_runs_per_600",
        "contact_runs_per_600", "archetype", "noted", "chase_rate",
        "league_chase_rate_same_pitches", "top_leak", "top_leak_runs",
        "top_leak_count_status", "top_leak_chase_depth_in", "leak_excess_vs_league",
        "leak_excess_predicted_next", "plan"]
out = cards[keep]
out.to_csv(CARDS_DIR / f"team_view_{SEASON}.csv", index=False)
print(f"  wrote player_cards/team_view_{SEASON}.csv ({len(out)} hitters, "
      f"{out['team'].nunique()} teams)")

# --------------------------------------------------
# THE PAGE
# --------------------------------------------------

# The plan's first line (the table shows one pitch to start with; the
# full plan is on the card and in the CSV). Lines are joined with a space
# in the CSV, so split where the next line's opener begins.
OPENERS = ("With two strikes", "On the first pitch", "When you're ahead", "Early in the count",
           "At 0-1 or 1-1", "Your bigger issue", "Nothing stands out")
SPLIT = re.compile(r"(?= (?:" + "|".join(re.escape(o) for o in OPENERS) + "))")


def first_line(plan):
    return SPLIT.split(plan, maxsplit=1)[0].strip() if isinstance(plan, str) else ""


ARCHETYPE_WORDS = {"decision-only": "choices", "decision-led": "mostly choices", "mixed": "mixed",
                   "execution-led": "mostly contact", "execution-only": "contact"}
STATUS_WORDS = {"struggling": "struggling", "average": "average", "productive": "hitting well"}


def num(v, digits=1, plus=False):
    if pd.isna(v):
        return ""
    s = f"{v:+.{digits}f}" if plus else f"{v:.{digits}f}"
    return s.replace("-", "−")


rows = []
for r in out.itertuples(index=False):
    target = ("" if pd.isna(r.leak_excess_vs_league) else
              f"{r.leak_excess_vs_league * 100:.0f} → {r.leak_excess_predicted_next * 100:.0f}")
    rows.append({
        "team": r.team, "teams": r.teams, "player": r.player, "slug": r.slug, "bats": r.bats,
        "xchase": round(float(r.xchase_plus)), "rank": int(r.xchase_plus_rank),
        "pa": int(r.plate_appearances), "stake": round(float(r.runs_at_stake_far_off), 1),
        "choices": round(float(r.choices_runs_per_600), 1),
        "contact": round(float(r.contact_runs_per_600), 1),
        "kind": ARCHETYPE_WORDS.get(r.archetype, r.archetype),
        "noted": bool(r.noted) and r.noted == r.noted,
        "leak": r.top_leak if isinstance(r.top_leak, str) else "",
        "leak_runs": None if pd.isna(r.top_leak_runs) else round(float(r.top_leak_runs), 1),
        "check": STATUS_WORDS.get(r.top_leak_count_status, "") if isinstance(r.top_leak_count_status, str) else "",
        "depth": None if pd.isna(r.top_leak_chase_depth_in) else round(float(r.top_leak_chase_depth_in)),
        "target": target,
        "excess": None if pd.isna(r.leak_excess_vs_league) else round(float(r.leak_excess_vs_league) * 100),
        "plan": first_line(r.plan),
    })
team_list = sorted({t for r in rows for t in r["teams"].split(", ")})

page = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Chase Team View {SEASON}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito+Sans:opsz,wght@6..12,400;6..12,600;6..12,800&display=swap">
<style>
:root {{
  --surface: #fcfcfb; --plane: #f4f3ef; --ink: #0b0b0b; --ink2: #52514e; --muted: #76746e;
  --hair: #e1e0d9; --axis: #c3c2b7; --blue: #2a78d6; --red: #e34948; --focus: #2a78d6;
  --font: "Avenir Next", "Nunito Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  color-scheme: light;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --surface: #1a1a19; --plane: #121211; --ink: #ffffff; --ink2: #c3c2b7; --muted: #959389;
    --hair: #2c2c2a; --axis: #383835; --blue: #3987e5; --red: #e66767; --focus: #6da7ec;
    color-scheme: dark;
  }}
}}
:root[data-theme="dark"] {{
  --surface: #1a1a19; --plane: #121211; --ink: #ffffff; --ink2: #c3c2b7; --muted: #959389;
  --hair: #2c2c2a; --axis: #383835; --blue: #3987e5; --red: #e66767; --focus: #6da7ec;
  color-scheme: dark;
}}
* {{ box-sizing: border-box; }}
body {{ background: var(--plane); color: var(--ink); font-family: var(--font); font-size: 14px;
       line-height: 1.4; margin: 0; padding: 20px 16px 48px; }}
.wrap {{ max-width: 1440px; margin: 0 auto; display: grid; gap: 14px; }}
h1 {{ margin: 0; font-size: 26px; }}
p {{ margin: 0; }}
.lede {{ color: var(--ink2); max-width: 90ch; }}
a {{ color: var(--blue); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.controls {{ display: flex; flex-wrap: wrap; gap: 10px 20px; align-items: end; }}
.control {{ display: grid; gap: 4px; }}
.control label {{ font-size: 11px; color: var(--muted); font-weight: 700; letter-spacing: .06em; text-transform: uppercase; }}
input, select {{ font: inherit; color: inherit; background: var(--surface); border: 1px solid var(--axis);
                 border-radius: 6px; padding: 6px 10px; }}
:focus-visible {{ outline: 2px solid var(--focus); outline-offset: 2px; }}
.card {{ background: var(--surface); border: 1px solid var(--hair); border-radius: 10px; overflow: auto; }}
table {{ border-collapse: collapse; width: 100%; min-width: 1560px; }}
th, td {{ padding: 7px 10px; text-align: left; border-bottom: 1px solid var(--hair); vertical-align: top; white-space: nowrap; }}
th {{ font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; cursor: pointer;
      position: sticky; top: 0; background: var(--surface); user-select: none; }}
th.sorted {{ color: var(--ink); }}
th .dir {{ font-size: 10px; margin-left: 3px; }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
td.plan {{ white-space: normal; min-width: 34ch; max-width: 44ch; color: var(--ink2); font-size: 13px; }}
td.leak {{ white-space: normal; min-width: 22ch; max-width: 28ch; }}
/* phones: each hitter as a stacked card instead of a 16-column row */
@media (max-width: 720px) {{
  table {{ min-width: 0; }}
  thead {{ display: none; }}
  tbody tr {{ display: block; padding: 10px 12px; border-bottom: 1px solid var(--hair); }}
  tbody td {{ display: flex; justify-content: space-between; gap: 12px; border: 0; padding: 2px 0; white-space: normal; text-align: left; }}
  tbody td::before {{ content: attr(data-label); color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; flex: 0 0 auto; padding-top: 3px; }}
  tbody td.num {{ text-align: right; }}
  tbody td.plan {{ display: block; min-width: 0; max-width: none; padding-top: 6px; }}
  tbody td.plan::before {{ display: block; margin-bottom: 2px; }}
  tbody td.leak {{ min-width: 0; max-width: none; }}
  tbody td:first-child {{ font-weight: 700; }}
}}
.neg {{ color: var(--red); }}
.pos {{ color: var(--blue); }}
.tag {{ display: inline-block; font-size: 11px; padding: 1px 6px; border-radius: 10px; background: var(--plane); color: var(--ink2); }}
.note {{ color: var(--muted); font-size: 12px; max-width: 110ch; }}
.count {{ color: var(--muted); font-size: 12px; }}
</style>
<div class="wrap">
  <h1>Chase decisions by team, {SEASON}</h1>
  <p class="lede">Every qualified hitter, sorted by the runs his swing choices on far-off pitches cost per 600 plate appearances. Click a name for his decision card. The target is how far above the league he chased in his card's leaks this season and what the frozen line expects next season with no change; below that is a fix.</p>
  <div class="controls">
    <div class="control"><label for="team">Team</label><select id="team"><option value="">All teams</option>{"".join(f'<option value="{t}">{t}</option>' for t in team_list)}</select></div>
    <div class="control"><label for="q">Search</label><input id="q" type="search" placeholder="Hitter name" autocomplete="off"></div>
    <div class="control"><label for="kind">Problem</label><select id="kind"><option value="">Any</option><option>choices</option><option>mostly choices</option><option>mixed</option><option>mostly contact</option><option>contact</option></select></div>
    <p class="count" id="count"></p>
  </div>
  <div class="card"><table id="t"><thead><tr></tr></thead><tbody></tbody></table></div>
  <p class="note">Runs are per 600 plate appearances. Choices is what the swing decisions cost against an average hitter at the same spot, count and matchup; contact is what the chases produced compared with the average hitter's chases. Problem: the share of the loss that is choices (step 13). Top leak: the costliest count, pitch group and side of the zone, with the hitter's rate against the league's and how far off the zone the chased pitches were (median inches). Count check: how he hits once the count reaches the leak's counts, shrunk for noise, against the league in the same counts. Target: leak chasing in points above the league, this season → next season with no change (step 19). Start with: the first line of the plan; the rest is on the card. Built by step 21 of the Chase Leaderboard project; the cards themselves are <a href="index.html">index.html</a>.</p>
</div>
<script>
const ROWS = {json.dumps(rows, ensure_ascii=False)};
const COLS = [
  ["team", "Team", false], ["player", "Hitter", false], ["bats", "Bats", false],
  ["xchase", "xChase+", true], ["rank", "Rank", true], ["pa", "PA", true],
  ["stake", "Runs at stake", true], ["choices", "Choices", true], ["contact", "Contact", true],
  ["kind", "Problem", false], ["leak", "Top leak", false], ["leak_runs", "Leak runs", true],
  ["depth", "Off zone, in", true], ["check", "Count check", false], ["target", "Target", true],
  ["plan", "Start with", false],
];
const state = {{ sort: "stake", dir: -1, team: "", q: "", kind: "" }};
const el = (tag, attrs = {{}}, ...kids) => {{ const e = document.createElement(tag); for (const [k, v] of Object.entries(attrs)) {{ if (k === "text") e.textContent = v; else e.setAttribute(k, v); }} kids.forEach((k) => e.append(k)); return e; }};
const fmt = (k, v) => {{
  if (v === null || v === undefined || v === "") return "";
  if (k === "choices" || k === "contact" || k === "leak_runs") return (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v).toFixed(1);
  if (k === "stake") return v.toFixed(1);
  return String(v);
}};
function render() {{
  const head = document.querySelector("#t thead tr"); head.replaceChildren();
  for (const [k, label, num] of COLS) {{
    const th = el("th", {{ class: (num ? "num " : "") + (state.sort === k ? "sorted" : ""), text: label }});
    if (state.sort === k) th.append(el("span", {{ class: "dir", text: state.dir < 0 ? "▼" : "▲" }}));
    th.addEventListener("click", () => {{ if (state.sort === k) state.dir = -state.dir; else {{ state.sort = k; state.dir = num ? -1 : 1; }} render(); }});
    head.append(th);
  }}
  const q = state.q.toLowerCase();
  let rows = ROWS.filter((r) => (!state.team || r.teams.split(", ").includes(state.team)) && (!q || r.player.toLowerCase().includes(q)) && (!state.kind || r.kind === state.kind));
  const key = state.sort === "target" ? "excess" : state.sort;
  rows = rows.slice().sort((a, b) => {{
    const x = a[key], y = b[key];
    if (x === null || x === undefined || x === "") return 1;
    if (y === null || y === undefined || y === "") return -1;
    return (typeof x === "number" ? x - y : String(x).localeCompare(String(y))) * state.dir;
  }});
  const body = document.querySelector("#t tbody"); body.replaceChildren();
  for (const r of rows) {{
    const tr = el("tr");
    for (const [k, label, num] of COLS) {{
      const td = el("td", {{ class: (num ? "num" : "") + (k === "plan" ? " plan" : "") + (k === "leak" ? " leak" : ""), "data-label": label }});
      if (k === "player") {{ td.append(el("a", {{ href: "index.html#" + r.slug, text: r.player }})); if (r.noted) td.append(" ", el("span", {{ class: "tag", text: "noted" }})); }}
      else if (k === "team") td.textContent = r.teams;
      else if (k === "choices" || k === "contact" || k === "leak_runs") {{ td.textContent = fmt(k, r[k]); if (r[k] < -0.05) td.classList.add("neg"); else if (r[k] > 0.05) td.classList.add("pos"); }}
      else td.textContent = fmt(k, r[k]);
      tr.append(td);
    }}
    body.append(tr);
  }}
  document.getElementById("count").textContent = `${{rows.length}} of ${{ROWS.length}} hitters`;
}}
document.getElementById("team").addEventListener("change", (e) => {{ state.team = e.target.value; render(); }});
document.getElementById("q").addEventListener("input", (e) => {{ state.q = e.target.value; render(); }});
document.getElementById("kind").addEventListener("change", (e) => {{ state.kind = e.target.value; render(); }});
try {{ const t = new URLSearchParams(location.search).get("team"); if (t) {{ state.team = t; document.getElementById("team").value = t; }} }} catch (e) {{}}
render();
</script>
</html>
"""
(CARDS_DIR / "teams.html").write_text(page)
print(f"  wrote player_cards/teams.html ({len(page) / 1e3:.0f} KB)")
