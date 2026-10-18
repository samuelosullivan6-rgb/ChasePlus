# Audit brief: the 2026 chase decision cards

## What these pages are

`results/xchase/player_cards/2026/index.html` in the project at
`/Users/samsullivan/Desktop/Personal Projects/Baseball/Chase Leaderboard` is one web page with two
views:

- **Card view** (`#<hitter_slug>`): one card per qualified 2026 MLB hitter (261), plus two
  reference cards (the average right- and left-handed hitter). A card tells a hitter where he swings
  at balls more than other hitters do and what it costs, and gives him a short plan. **The plan is
  written to the player ("you").** The coach's note (17 "noted" hitters only) is written for the staff
  ("he"). Coaches use the card with the player in the room.
- **Roster view** (`#roster`): every hitter in one sortable table with the top leak, the target
  ("Beat") and the plan's first line ("Start with").

It is served at http://localhost:8765/2026/index.html (a local server is running; e.g.
`http://localhost:8765/2026/index.html#colson_montgomery`). The page is built by
`scripts/17_build_player_cards.py` from `scripts/templates/player_cards.html`; the plan sentences are
written by `plan_items()` and helpers in step 17 (around lines 520-1030). `scripts/plan_checks.py`
checks plans on every build.

## What is on a card (top to bottom)

1. **Header**: name; bats, height, team(s), PA, xChase+ and its rank; the hitter's chase rate vs the
   league's on the same pitches. Two tiles: "Cost of far-off chases" (runs per 600 PA from choices on
   pitches 4+ inches off the plate, a positive number = a cost) and "Where the runs go" bars, Choices
   and Contact (all chases; negative = runs lost).
2. **Zone pictures**: rows (All pitchers / vs RHP / vs LHP; a switch hitter gets Batting left /
   Batting right instead; a hitter whose problem is contact, "execution-led", gets an extra "Misses
   on chases" row) by four count columns (First pitch, Ahead, 0-1 or 1-1, Two strikes). Red = he chases
   more than the average hitter at that spot and count, blue = less, gray = about average, faded =
   too few pitches. Each leak's number is drawn as a circled marker on the picture for its count, on
   the row of the hand it names (or the all-pitchers row). One picture opens selected (outlined).
3. **Right column**, which changes with the "Plan, leaks and table" control (All pitchers / vs RHP /
   vs LHP):
   - **What to work on**: the plan. Pitch lines are numbered 1, 2 (filled circles) in the order to
     work on them, each tagged with its leak's number ("leak ②"). Then possibly a framing line (dot),
     then a closing "Keep swinging at strikes..." line. Or one fallback line ("Nothing stands out...",
     "No single pitch stands out...", "Nothing to change...", "No single pitch here is a clear take..."),
     or a contact line ("Your issue is contact...").
   - **Coach's note, for the staff** (noted hitters only).
   - **Biggest leaks**: numbered list; each row = count, pitch group, side of the zone (and "mostly vs
     RHP/LHP" when 80%+ of its pitches came from one hand), his chase rate vs the league's, chases of
     pitches, and what the choices cost in runs per 600 PA. A leak needs to be worth 0.75 runs.
   - **Target** (all-pitchers view only): the frozen number to beat in 2027 (step 19), or why there
     is none.
   - **By count** table: per count group, his rates vs the league's (chases, far-off chases, misses
     per chase, xwOBA of PAs that reach those counts), Choices runs, Contact runs.
   - Far-off chase rate by season chart; the footer line "Does fixing a leak pay?..."
4. **Zone numbers** (a closed details panel under the pictures): chase rate you / avg (pitches) by
   region and count, all pitchers.

## The plan rules (what step 17 intends)

- Pitch lines come from the leaks; at most 2. Order: a take before two strikes first (it costs no
  strikeouts), then two-strike takes; a video item (a leak whose chased pitches were typically under
  4 inches off the zone) never ahead of a take. For a noted hitter, the coach's note names the leak
  the plan leads with. The order also chooses, so the plan can leave the biggest leak out; the card
  says so under the leak list.
- A pitch line quotes "You swung at X%; hitters on average swing at Y%" only when the two print 5+
  points apart; otherwise it says the swings were about as often as other hitters but came in
  costlier counts, and what they cost.
- A take line says how far off the zone the chased pitches typically were. A video item says "one to
  go over on video with your coaches, not a take rule".
- A contact hitter (execution-led) reads the contact reason folded into his first take line, or a
  contact line as the plan's one line when there is no take.
- If the first pitch line sits in a count the table shows as a plus for his choices, the line says
  why ("your choices are a plus overall... this pitch is where they give some back").
- A framing line after the pitch lines when the loss is spread thin (choices loss of 3+ runs, plan's
  pitches cover under a quarter of it) or the hitter's choices are average or better, or the header's
  far-off cost prints 0.0.
- Closing line: "Keep swinging at strikes" (+ "your fastball decisions are a strength" when his
  fastball choices are +1 run or better and no plan line is a fastball) + "The only change(s) on this
  card is/are the pitch(es) above", or for video-only plans, "the staff takes ... to video with you
  first".
- "Nothing stands out" only when no count group costs 1+ run of choices. Other fallbacks name the
  costly counts.
- On a pitcher-hand tab, the plan is rebuilt from that hand's leaks and table only.
- Target: points above the league's chase rate in ALL the card's leaks together (not only the plan's),
  and what a line expects in 2027 with no change; "Under N is a fix". No target when the forecast is
  2 points or less, or every leak is a video item.

## Already guarded by `scripts/plan_checks.py` (all pass on this build: 0 cards each)

contact line or framing line printed first when there is a take line; plan numbers backwards or
skipping; video-only plan without saying the staff takes it; framing line calling the pitches "the
biggest pieces" when they are not; "already" in the no-target sentence; fastball-strength clause
under a fastball line; header 0.0 unexplained; good chooser unframed; first line in a plus count
without a why; a pitch line's rates or inches not its leak's; framing or plus-count runs misquoted;
"pitch above"/"pitches above" miscounted; target without unit or leaks; retrospective target issues;
a number to beat on a video-only card; roster start line quoting near-identical rates; hand
overstated in a leak name.

Report one of these only if you actually see it (it would mean the check is wrong). Spend your time
on everything else.

## Known open items from earlier reviews (still report if you see them, mark known=true)

- Phone layout: first screen is all controls; pictures far below the plan.
- A leak named "mostly vs RHP" still counts the other hand's pitches in its rates.
- The no-target sentence's points (target scale) can differ from the leak list's rates.
- 115 or so plans belong to hitters whose chase choices are better than average overall.

## What counts as an issue (report all of them)

Anything that would make a reader (player, coach, analyst) confused, misled, or unsure what to do, or
that is simply wrong or broken:

- **No plan when there should be one**, or a plan when there should not be: e.g., leaks worth runs
  but the plan says nothing stands out; a costly count with no line and no explanation; a hand tab
  with a leak but no plan line, or a plan line with no leak; a fallback line whose claim the table
  contradicts.
- **Contradictions** anywhere on the card or between the card and the roster: plan vs leak list,
  plan vs By count table, plan vs header tiles, target vs leak list, coach's note vs plan, all-pitchers
  view vs the hand tabs (e.g., a leak "mostly vs RHP" that the vs RHP tab does not show), picture
  markers vs the leak list (a leak's marker drawn where the picture shows he chases LESS than average,
  i.e. a negative gap; a marker not drawn; the selected picture not the plan's first line), roster row
  vs card.
- **Numbers that do not add up as printed** (rounding that makes a sentence false, signs, "-0.0",
  sums, shares, percentages over 100, rates vs counts "12 of 21" vs "57%").
- **Sentences that do not fit the case**: wrong pronoun or voice (staff "he" in player text, or "you"
  in staff text), grammar, repeated or contradictory clauses, an instruction a hitter cannot act on,
  advice built on a tiny sample (a plan line from a leak of 15 to 25 pitches), a line that tells a
  hitter to fix something he does better than average, jargon never explained.
- **Labels and page text** that are wrong, inconsistent, or unclear.
- **Anything broken**: missing text, "undefined", "NaN", "–" where a number should be, duplicated
  sections, a hitter missing from the roster, wrong team.

Do NOT recompute statistics from raw pitch data: the numbers are produced and checked by code. DO check
whether numbers printed in different places agree with each other and with the sentences next to them,
and whether the words are right for the numbers.

## How to read a dossier (`dossiers/batch_NN.md`)

Each card is a `## CARD <rank>: <name>` block, rendered from the real page in headless Chrome:
`HEADER`, `TILES`, `PICTURE ROWS`, `PICTURE SELECTED WHEN THE CARD OPENS`, one line per leak
`marker` (which row and picture it is drawn on and what the picture says at the marker's spot: "you X%
vs avg Y% (gap ±N pts)", a negative gap = a blue spot, and color strength 0 to 1), then the right
column as printed for each of the three views (All pitchers, vs RHP tab, vs LHP tab), each followed by
its By count table (the count-status column is the count check; only the all-pitchers table carries
it). `(1)`/`(2)` at a plan line's start are the step numbers and `[leak tag N]` is the leak number tag;
in the leaks list `(N)` is the leak number. Then the season trend, the Zone numbers panel, the
hitter's ROSTER ROW, and UNDERLYING DATA (not printed on the page; use it to check sentences: e.g.,
`depth_in`, `excess_counts`, `share_rhp`, `archetype`, `fastball_choices`, the raw target).

The full extraction is `dump_2026.json` in the same folder (cards, roster rows, the page's data) if
you want to check something with a script; `page_and_roster.md` has the page-level text and the full
roster table.
