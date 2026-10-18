# Every 2026 card, audited for issues

18 October 2026. Scope: all 261 hitter cards on the 2026 season page, each in its three views
(All pitchers, vs RHP, vs LHP: 783 views), the two reference cards, the roster view, the page's
labels and controls, and the layout at 390 to 1920 px in light and dark. Built from
`results/xchase/player_cards/2026/index.html` at 0d64764, the build GitHub Pages serves.
`scripts/plan_checks.py` passes on this build: 0 cards in every kind it guards. Everything below
gets past it.

## How it was done

1. Every card was rendered in headless Chrome (`method/extract_in_page.js`, `method/drive.mjs`).
   For each card the script recorded the visible text in each view, the roster row, the Zone
   numbers panel, and where each leak's number is drawn on the pictures, with what the picture
   shows at that spot. `method/format_dossiers.py` turned this into one dossier per card.
2. Sixteen reviewers worked independently from `method/BRIEF.md`:
   - 13 read about 20 cards each, every view, as player, coach and analyst.
   - One swept all 261 cards with scripts.
   - One read the page and the roster.
   - One took screenshots (`method/shot.mjs`).

   Together they reported 523 findings.
3. The findings were merged into 40 issue types. Each type then went to a separate skeptic who
   tried to disprove it, counted it across all 261 cards, found the code it comes from, and
   proposed a fix. Claims that did not hold are listed under "What did not hold up". The full
   record, with quotes, counts, code lines and fixes for all 40, is `issues.json`.

The numbers themselves were not recomputed from raw pitches; the code checks those. This audit
checks whether what the card prints agrees with itself, with the roster and with the plan's rules,
and whether a reader can act on it.

## Verdict

The All pitchers plan is in good shape:
- No card with a listed leak lacks a plan line.
- Every leak row's rate and "N of M" match.
- The step numbers run 1, 2.
- The picture each card opens on is the plan's first line on all 229 cards with a plan.
- Nothing prints "undefined" or "NaN", and every hitter is on the roster.

Most of what is wrong comes from five sources:

1. **The pitcher-hand tabs are half rebuilt.** Each tab rebuilds its plan from that hand's
   pitches, but the following stay as they were:
   - the closing line ("on this card");
   - the framing, contact and fastball sentences (all-pitchers numbers);
   - the pictures and their numbers;
   - the coach's note.

   Result: on 143 cards a tab speaks for the whole card while saying something different, and on
   22 a tab gives the opposite instruction to the main plan. A coach opening "vs RHP" before a
   right-handed starter is the reader most likely to be misled.
2. **The plan sometimes picks the wrong first pitch.** The take-before-two-strikes order moves
   small pre-two-strike cells to the top:
   - 39 first lines (and roster Start-with lines) rest on fewer than 20 pitches.
   - 14 first lines are pitches he chases at the league's rate.
   - 54 cards leave out a bigger leak with no word.
   - 86 cards say "the only changes" while a count costing a run or more gets no line.
3. **The hand label ("mostly against right-handers") counts who threw the pitches, not where the
   extra chasing was.** On Vaughn Grissom's card it points the first line at the wrong hand.
4. **The target is on a different scale from the leak rows above it.**
   - On 8 cards it says "points below the league" under leaks printed above the league.
   - On 70 cards it is 5 or more points off what the rows add up to.
5. **The pictures and the layout.**
   - 73 leak numbers sit on gray or blue spots.
   - The By count table loses its Contact column at most laptop widths.
   - The roster's Start with and Beat columns are off-screen at every desktop width.

## No plan where there should be one

This answers the question directly; details are under the issues it belongs to.

| Case | Cards | Example |
|---|---:|---|
| All pitchers view: a listed leak but no pitch line | **0** | — |
| All pitchers view: no take at all (16 video-only, 28 "Nothing stands out", 2 "Nothing to change", 2 contact-only) | 48 | the 32 non-video cards have no leaks, by design |
| The plan's first line names a hand ("mostly against left-handers"), and that hand's own tab says "Nothing stands out" or "Nothing to change" | 8 | Grissom, Hoerner, Goldschmidt, France, Wood, Vaughn, Jung Hoo Lee, Vivas |
| The All view has no take, but a hand tab prints one and calls it "the only change on this card" | 6 | Guerrero (R), Bohm (R), Walker (R), Moreno (L), Antonacci (L), Butler (L) |
| A count costing 1+ run of choices gets no line and no mention, under "The only change(s) on this card" | 86 (36 where it is the costliest count) | Michael Harris, Salvador Pérez, Tovar, Merrill |
| A bigger leak (1.25x+, 20+ pitches) left off the plan, never named | 54 | Yordan Álvarez, Olson, José Ramírez, Cowser, Carroll |
| vs LHP tab: "Nothing stands out ... about league average in every count" beside a table showing a clear gap | 14 (another 13 on under 150 pitches) | Jesús Sánchez (54% vs 28% over 57 pitches) |
| 'Mixed' hitters losing 3+ runs on contact, their bigger cost, with no contact word | 30 (8 read "Nothing stands out") | Torkelson, Reynolds, Stephenson |

## Issues, by severity

Counts are cards out of 261 unless stated. "Design" means step 17 does this on purpose, though the
reader is still misled.

| # | Issue | Severity | Cards | Design |
|---:|---|---|---:|:---:|
| 1 | Hand-tab closing line says "on this card" about a different plan | high | 143 | |
| 2 | "Mostly vs RHP/LHP" names who threw the pitches, not where the extra chasing was | high (Grissom), else medium | 141 | yes |
| 3 | A hand-named leak or plan line is missing from that hand's tab | high | 52 | yes |
| 4 | "Your fastball decisions are a strength" beside a fastball the card says to work on | high | 26 | |
| 5 | All view and a hand tab give opposite instructions on the same pitch | high | 22 | yes |
| 6 | No-target sentence says "below the league" under leaks printed above it | high | 8 | yes |
| 7 | Hand-tab sentences quote all-pitchers numbers the tab's table contradicts | medium | 126 | |
| 8 | Hand-tab "leak N" tags point at a different pitch's marker | medium | 117 | |
| 9 | A hand tab leads with a leak the All view never lists or draws | medium | 115 | yes |
| 10 | Plan lines on small samples | medium | 119 | yes |
| 11 | Costly count left unaddressed under "the only changes" | medium | 86 | yes |
| 12 | Target points differ from what the card's leak rows add up to | medium | 70 of 213 | yes |
| 13 | Target sentence argues with the plan ("about at it" for −9; grades leaks off the plan) | medium | 182 | yes |
| 14 | Leak markers on gray or blue spots | medium | 64 | |
| 15 | Hover, 3D, Zone numbers and leak row give four different rates for one spot | medium | 216 | |
| 16 | Bigger leak left out, unexplained | medium | 54 | yes |
| 17 | Take line for a pitch chased at the league's rate | medium | 49 | yes |
| 18 | Contact treatment flips at a net of zero (step 13 archetype) | medium | 35 | yes |
| 19 | Roster's leak columns describe leak 1; Start with is another leak | medium | 92 | yes |
| 20 | Far-off cost tile: opposite sign to Choices, 0.0 beside 5-10-inch takes | medium | 82 | yes |
| 21 | Switch hitters: leak drawn on the side with less of its excess | medium | 29 | yes |
| 22 | "Nothing stands out" beside a table that shows a gap (vs LHP) | medium | 27 | yes |
| 23 | Framing and spread lines misfire ("the biggest piece" for 12-21%) | medium | 32 | yes |
| 24 | Contact sentence misfires ("miss about as often" at 32% vs 42%) | medium | 22 | |
| 25 | Coach's note repeated on hand tabs, naming lines the tab does not have | medium | 15 of 17 | |
| 26 | Coach's notes with numbers the card cannot back | medium | 12 of 17 | |
| 27 | Fallback calls a 1.4-2.9 run loss "about average", with an ASCII "-" | medium | 12 | |
| 28 | "Nothing to change ... those swings have paid: N runs" quotes the wrong N | medium | 10 | |
| 29 | By count table clipped (Contact cut at 1101-1470 px and phones) | medium | all | yes |
| 30 | Phone and one-column layout | medium | all | |
| 31 | Page labels: xChase+, noted, no target undefined; guide hidden | medium | all | |
| 32 | Roster layout and navigation | medium | page | |
| 33 | Target wording ("1 points", no unit, "Target: No target:") | low | 229 | |
| 34 | Pictures and filters (numbers vanish with any filter; 12 overlapping pairs) | low | 229 | |
| 35 | Boilerplate and long lines (up to 113 words) | low | 153 | |
| 36 | Good choosers wrapped in three hedges | low | 115 | yes |
| 37 | Plus-count "why" only on line 1; fires on +0.1 | low | 67 | yes |
| 38 | Video-item wording ("within a ball" vs the 4-inch rule) | low | 55 | |
| 39 | Same number rounded differently by Python and the page | low | 20 | |
| 40 | Table and chart oddities | low | all | yes |

## The high-severity issues

### 1. Hand-tab closing lines speak for the whole card (143 cards)

Every hand-tab closing line says "on this card", from `keep_line()` (step 17:785-800, which has no
view argument). On 143 cards that tab's pitch lines are not the All pitchers plan. About 50 of these
contradict the main instruction outright:

- **10 tabs say "Nothing on this card is a take rule" while the main plan has takes.** Trea Turner
  vs RHP closes "Nothing on this card is a take rule for you yet". His All pitchers line 1 is "On the
  first pitch, let breaking balls below the zone go", and 67% of those pitches came from
  right-handers. The same happens for Gonzales, Jung, Heliot Ramos, France and Goldschmidt (vs RHP),
  and for Bell, Karros, Adell and Lindor (vs LHP).
- **30 cards drop a main-plan line named "mostly against" that tab's hand and still say "the only
  change".**

**Fix:** pass the view into `keep_line`. On a tab, say "Against right-handers, start with the pitch
above", never "on this card", and add "The All pitchers plan still stands" when the main plan has a
take the tab lacks.

### 2-3. The hand label, and hand-named leaks missing from their tab (141 and 52 cards)

A leak is labeled "mostly vs RHP" when 80% of its pitches came from right-handers, or "mostly vs LHP"
at 55% from left-handers (step 17:417, :460-463). The label never checks:
- whether that hand carries the extra chasing;
- whether the leak survives on that hand's own pitches.

Its rates still pool both hands, so on 151 of 158 such leaks the tab prints different rates.

- **Vaughn Grissom.** Line 1 and his roster Start with read "With two strikes, mostly against
  left-handers, let breaking balls below the zone go. You swung at 63%...". His vs LHP tab says
  "Nothing stands out". His vs RHP tab plans the same pitch at "84% vs 53% · 16 of 19". Right-handers
  carry about 75% of the cost, so the label sends him to the wrong matchup.
- **8 first lines name a hand whose own tab clears it.** On 52 cards a hand-named leak or plan line
  is missing from its hand's tab, for five reasons:
  - 18 fall under 0.75 runs on one hand;
  - 10 drop past the top-3 cut;
  - 7 have under 12 pitches;
  - 6 are LHP labels where left-handers carry under half the cost;
  - 5 are chases on that hand that pay for themselves.

**Fix:** name a hand only when its slice carries most of the extra chases and the cost, and the cell
passes the leak rule on that hand's pitches. Otherwise drop the label, and the number moves to the
All pitchers row. A rough rule on card data keeps 151 of 202 labels and drops 51, among them 20
first lines.

### 4. "Your fastball decisions are a strength" beside a fastball to work on (26 cards)

The clause tests the all-pitchers fastball choices and only the same view's plan lines (step
17:797-798).
- On Nolan Schanuel's and David Hamilton's vs RHP tabs, it prints while the card's first instruction
  is "With two strikes, mostly against right-handers, let fastballs above the zone go".
- Austin Wells's vs RHP tab prints it a few lines above "(1) Two strikes vs RHP, fastballs above the
  zone 81% vs 62% avg · 21 of 26 −2.0".
- 16 views on 14 cards print it beside a costed fastball leak on the same list.

**Fix:** use the view's own fastball choices, and drop the clause when any plan on the card or any
leak on that view's list is a fastball.

### 5. The views give opposite instructions (22 cards)

Every threshold is reapplied to each hand's subset with no reference to the All view:
- **The 4-inch take/video cut.** On 12 pitches (11 cards) the same pitch is a take in one view and
  "not a take rule" in another. Brice Turang's only take ("With two strikes, let fastballs above the
  zone go", median 4.02 in) is "one to go over on video ... not a take rule" on his vs RHP tab (3.57
  in), where 76% of those pitches came from.
- **The leak rule itself.** On 6 cards the All view has no take but a tab prints one.
- **Fallbacks on the named hand.** On 7 cards a hand-named line 1 meets "Nothing to change" or
  "Nothing stands out" on that hand's tab.

Several of these flips come from medians within 0.5 in of the cut, or from 7 or 8 chased pitches:
noise, not a real difference between hands.

**Fix:** make the take/video call once per pitch, on the All view, with a dead band of about 0.5 in.

### 6. "Points below the league" under leaks above it (8 cards)

Adley Rutschman's line 1 and leak row both read 49% vs 43%. His Target reads "No target: leak 1 was 3
points below the league's chase rate in 2026, and with no change should be about at it in 2027."
The same flip appears on Alonso, Torkelson, Perdomo, Maikel García, Chapman, Okamoto and McMahon.

The number is step 19's frozen excess, measured against a coarser league baseline (no matchup, no
spot smoothing, `leak_rules.BACKTEST_LEAGUE_CELL`). Against that baseline these two-strike breaking
balls come out below the league. The same sentence says "about at it" for forecasts 4 to 9 points
below the league.

**Fix:** the no-target branch prints no number to beat, so it can take its 2026 points from the
card's own leak rows (+1 to +6 on all 8 cards), or say only the forecast. It should also say "at or
under it" when the forecast is below −2. Add a plan_checks kind for "below" over leaks printed above.

## The medium-severity issues

**The hand tabs, continued.**

- **7. Tab sentences quote all-pitchers numbers (126 cards).** `plan_items` gets the all-pitchers
  summary on every tab (step 17:1067), so the framing, contact and fastball sentences quote card-wide
  numbers. On 23 cards the verdict is the opposite of the tab's own table.
  - Cam Smith vs LHP: "Your bigger issue is contact: you miss on 49% of your chases, against 42%",
    over a tab reading misses 40%/40% and contact +3.0.
  - Rengifo vs LHP: "better than average" over a −4.7 table.
- **8. Tags point at the wrong marker (117 cards).** On a tab, "leak N" numbers that hand's list, but
  the pictures never redraw (template:664, :1181). On 166 of 456 tab lines, the marker with that
  number is a different pitch, or there is none. Brandon Marsh vs RHP: the tag says leak 3, and the
  3 on the pictures is a different pitch. **Fix:** redraw `zones()` from `p.leaks[state.hand]` on a
  tab change.
- **9. Tabs lead with a leak the All view never shows (115 cards; 51 lead with it).** Nathan Lukes
  vs RHP plans "changeups and splitters below the zone, 83%, 24 of 29, −3.3", the biggest leak
  anywhere on his card. The All list never names it and no picture marks it.
- **25. The coach's note is printed on every tab (15 of 17 noted hitters).** It says "the plan's
  first line" under a tab whose first line is a different pitch on 13 tabs, and under no pitch line
  at all on 7. **Fix:** show the note only on All pitchers (template:931). The print card already
  does this.
- **22, 27, 28. Fallback lines on thin vs LHP tabs.**
  - "Nothing stands out ... in every count" sits beside clear gaps on 14 tabs.
  - "about average overall (-2.9 runs a season)" on Marsh, with a hyphen; 12 views have the hyphen.
  - "Nothing to change ... those swings have paid: 2 runs" quotes the tab's total contact, not the
    named count's. It is false on Church and Freeman vs LHP.

**Which pitch the plan picks.**

- **10. Small samples (119 cards).**
  - 39 of 229 first lines rest on fewer than 20 pitches; 21 on fewer than 10 chases.
  - 31 of those 39 are pre-two-strike cells that the take-first order moved up. In 20 cards, this
    pushes off a leak with twice the pitches. Carroll leads with "11 of 19" and drops leak 1, "31 of
    41, −2.8".
  - The project's backtest says leaks under 20 pitches are mostly noise; 20-25 hold up.

  **Fix:** let a pre-two-strike leak lead only with 20+ pitches, and print the sample on lines under
  20.
- **11, 16. Costly counts and bigger leaks left out with no word (86 and 54 cards).** The closing
  then says "The only changes on this card". **Fix:** one line naming what was left out and why, and
  "the changes to start with".
- **17. League-rate pitches as takes (49 cards; step 1 on 14).** Curtis Mead's only line is
  "about as often as other hitters", and his Target says the leak was at the league's rate. The
  leak rule has no minimum rate gap.
- **18. The contact edge at a net of zero (35 cards).**
  - Norby (+8.8 / −9.1) reads "Your issue is contact, not choices".
  - Reynolds (+9.0 / −8.7) never hears the word contact.
  - 30 'mixed' hitters lose 3+ runs on contact with no contact sentence.
  - The roster's "contact" filter matches 0 hitters.
- **21. Switch hitters (29 cards).** A leak is drawn on the side where he chased most often, not the
  side where he chased more than other hitters. On 8 cards the card opens on the wrong side; for
  Perdomo and Nuñez that side is at the league's rate.
- **23, 24. Framing, spread and contact lines.**
  - "The pitch above is the biggest piece of it" appears for 12-21% of a loss, on 14 tab views.
  - "You miss about as often as other hitters" appears beside 5+ point gaps in either direction on
    9 cards, including Mullins at 32% vs 42%.
  - "So a pitch that is clearly off is a take" is followed by "Nothing on this card is a take rule"
    on 5 cards.

**The target (12, 13).**

- The target and the roster's "(was N)" are 5+ points below what the card's own leak rows add up to
  on 70 of 213 cards, up to 14 points (Yandy Díaz).
- 103 of 140 numbered targets count a leak the plan leaves out, under "The only changes on this
  card". On 17 cards those leaks carry half or more of the points.

**The pictures (14, 15).**

- **Markers on gray or blue spots.** 73 of 547 leak numbers (64 cards) sit where the picture shows
  he chases no more than average.
  - 22 of those markers (20 cards) are visibly blue.
  - On 28 cards it is the plan's first line, on the picture the card opens on.
  - Cause: the pictures pool every pitch type, while the leak is one pitch type. Filtering to the
    leak's type turns 524 of 547 spots red, but the filter hides the numbers.
- **Four different rates for one spot.** Luis García's leak 1 reads 79/21 in the plan, 94/23 "+50"
  in the hover, 73/23 in 3D and 74/26 in Zone numbers. The flat hover prints a shrunk gap over
  unshrunk rates (template:719-721).

**The header, roster and page (19, 20, 29-32).**

- **Far-off cost tile.** It prints a loss as a positive number, opposite to Choices and Contact, and
  nothing says so. On 82 cards it reads 0.0, and the plan adds "on far-off pitches they cost you
  nothing net (the 0.0 at the top)" right under take lines for pitches 5 to 10 inches off.
- **By count table.** It is wider than its column at 1101-1470 px with the Mac font and on phones.
  At 1440 the Contact header reads "Cont", with no scrollbar or hint. 1512 px and wider is fine.
- **Roster.**
  - Start with is past the right edge at every desktop width, and Beat is cut. Scrolling to them
    hides the names.
  - On 88 rows, Top leak, Leak runs, Inches off and Count check describe leak 1 while Start with is
    a different leak.
  - Count check appears on no card.
  - `#roster` lands past the controls, and returning from a card loses your place.
  - A mis-cased link says the hitter "did not qualify" (`#Salvador_Perez`).
- **Page labels.**
  - xChase+, "noted", "no target" and the blank Beat are never defined.
  - The only reading guide is on the two reference cards, and nothing links to them.
  - 27 hitters have xChase+ over 100 while the header says they chase more than the league (by
    design, but unexplained).
- **Phone.**
  - The plan heading is below the first screen on every card.
  - The pictures sit 1,000 to 2,100 px under the plan, after the footer line.
  - Leak markers are 8.6 px circles with 5 px digits.

**The coach's notes (26).** 12 of 17 carry a number or claim the card cannot back:
- Neto's "290, up from 184" counts all-count sliders and names the wrong prior season.
- García's and Peraza's three-ball rules sit beside a plan that says its pitches are the only
  changes.
- Several give runs with no unit.

`coach_notes.py` checks each value but not its scope, unit or season.

## Low severity (33-40)

- **Target wording.**
  - "The target counts all pitchers" prints on all 89 hand tabs of cards with no number.
  - "1 points" on 6 cards.
  - "you'd be about 11 in 2027. Under 11 is a fix" with no unit on all 140.
  - "Target: No target:".
- **Picture filters.**
  - Any Pitches filter or Misses view removes every leak number, while the tags still say "leak ②".
  - 12 marker pairs overlap.
- **Boilerplate and long text.**
  - The leak caption "...so it can leave a bigger one out" prints under "None worth 0.75 runs" on
    265 views.
  - First lines run up to 113 words.
  - The plus-count clause repeats the line's own count phrase 73 times.
- **Good choosers.** 115 good choosers get the plus-count, framing, fastball and no-target hedges
  around one instruction.
- **Plus-count "why".** It is missing on 65 second lines in plus counts (Trout +11.4), and fires on
  +0.1.
- **Video items.** "Most of the ones you swung at were within a ball of the zone" is not the card's
  4-inch rule. Mack's take at 4.02 in sits beside a video item at 3.99 in.
- **Rounding.**
  - Python and the page round half-points differently. Caissie's line 1 says 62%, his leak row
    says 63%, and his roster row says 62%.
  - This affects 16 plan lines and 6 roster rows.
- **Table and chart oddities.**
  - The First pitch xwOBA always equals the All counts xwOBA, by design and unexplained.
  - 38 vs LHP Misses rates come from 1 to 4 chases.
  - 15 trend lines are drawn straight across seasons the hitter did not qualify.

## What did not hold up

The skeptics threw these out:
- **The roster's "hitting well" against the card's "productive".** No card prints a count-status
  word. "productive" came from this audit's dossier, which printed the data column.
- **Markers "half inside" the zone box.** No marker's centre is inside it. 75 touch the zone line,
  mostly video items at 1-4 in.
- **The Rafaela coach's note contradicting the season chart.** The chart is all counts, the note is
  early counts, and its "about 4 runs" is right.
- **The By count table clipped at 1600 and 1920 px.** It fits at 1512 and up.
- **Several reported cards in most clusters.** Each is listed in `issues.json` under
  `refuted_items`. Examples: Machado's fastball clause, Bichette and Adell as "bigger leak left
  out", and the sweep's "65 of 73" no-target count, which is 52.

One finding was set aside as not an issue: Daulton Varsho's two vs RHP leak rows print identical
numbers by coincidence (.677/.515 and .677/.521).

## Recommended order of work

1. **Decide what a hand tab is for.** It causes or worsens issues 1, 3, 4, 5, 7, 8, 9, 22, 25, 27
   and 28. Two ways to settle it:
   - **(a) Keep the separate plans** and scope everything on the tab:
     - the closing line;
     - the summary numbers;
     - a single take/video call per pitch;
     - redrawn pictures;
     - the note on All pitchers only.
   - **(b) The bigger option:** every tab shows the All pitchers plan, marking the lines that apply
     to that hand, with the leak list and table for the hand beneath. Hand-only lines are labeled as
     such.

   (b) removes the competing plans rather than patching each sentence, and it is what a coach
   preparing for a starter actually needs. Either way, add cross-view checks to `plan_checks.py`:
   - the same cell gets the same take/video call in every view;
   - no "Nothing ... take rule" on a tab while the All plan has a take;
   - a hand-named All line appears on its hand's tab.
2. **The no-target sentence (6, 12, 13).** Print the card's own points, or none, and make "about at
   it" sign-aware. It is wording only; the frozen numbers stay as step 20 scores them.
3. **Which pitch leads (10, 11, 16, 17).** A pre-two-strike lead needs 20+ pitches, and a real-gap
   take goes ahead of a league-rate leak. Add one line naming a left-out bigger leak or costly count,
   and say "the changes to start with" in place of "the only changes".
4. **The hand label and switch-hitter side by where the excess is (2, 21).**
5. **The pictures (14, 15, 34).** Draw a leak's number when Pitches is its own type, snap markers to
   a red spot in the leak's region, and make the hover agree with 3D.
6. **Layout (29, 30, 32).** Stack you/avg in the By count table, move Start with and Beat left on
   the roster, and put the pictures right after the plan on one column.
7. **The coach's notes' wording (26)**, then the low-severity wording.

Every fix above is described with its code location in `issues.json`. The audit itself made none of
them; the section below records what was fixed afterward.

## Fixed the same day: one plan on every tab

Of the two hand-tab options, (b) was chosen and built. Every season was rebuilt with step 22, and
`plan_checks.py` passes on all six.

- **Step 17 writes one plan per card.** A tab no longer rebuilds its own plan. Each pitch line
  carries its pitches split by pitcher hand (`by_hand`), with no leak rule applied again to a slice.
  Each hand leak carries the card's number for the same pitch (`all_n`), or none when the leak shows
  up against that hand only.
- **The page shows that plan word for word on vs RHP and vs LHP.** Under each pitch line it adds a
  gray note, for example "Against left-handers: you swung at 11 of 24 of these (46%); hitters on
  average swing at 39%."
  - The tab's leak list uses the card's numbers, the same as the pictures and the plan tags. A leak
    that shows up against one hand only gets a dashed circle and "against right-handers only".
  - The control is now "Leaks and table".
  - The leak caption no longer prints under an empty list.
- **"Your fastball decisions are a strength" is left out whenever any leak on the card is a
  fastball,** on any tab, planned or not. That changed 17 plans in 2026 and 133 across 2021-2026.
- **New `plan_checks.py` kinds:**
  - "two plans": a separate hand plan coming back;
  - "hand note does not add up": the R and L notes must sum to the line's leak;
  - "hand leak misnumbered";
  - "fastball strength beside a fastball leak".

Re-counted on the rebuilt 2026 page with the audit's own extraction (`method/`):

| On the 2026 page | Audited build | Rebuilt |
|---|---:|---:|
| Cards whose hand tab shows a different plan from All pitchers | 234 | 0 |
| ...and says "on this card" about it (issue 1) | 216 | 0 |
| Cards with a take on one view and "not a take rule" on another (issue 5, the 'Nothing ... take rule' form) | 14 | 0 |
| Cards with the fastball clause beside a fastball leak (issue 4) | 28 | 0 |
| Noted hitters whose note sits under a different plan on a tab (issue 25) | 17 | 0 |
| Hand-tab tags pointing at a different pitch's marker (issue 8) | 166 lines | 0 |
| Hand-list numbers that are not the card's number for the pitch | 213 rows | 0 |
| Leak caption under an empty list (issue 35, item 1) | 233 views | 0 |
| "about average overall (-N" fallbacks (issue 27) | 12 | 0 |

How each listed issue stands now:

- **Resolved:** 1, 4, 5, 7, 8, 25 and 27.
- **Changed in kind:**
  - Issues 3 and 9: a hand-named plan line now shows on its hand's tab with that hand's own numbers,
    and a hand-only leak is listed and marked rather than planned.
  - Issues 22 and 28 apply only to the All pitchers plan, now repeated on the tabs. The two false
    "Nothing to change" lines (Church and Freeman vs LHP) are gone.
- **Still open:**
  - Issue 2. The hand note makes a wrong label visible: Grissom's vs LHP tab now reads 11 of 24,
    46% vs 39%, under the line that names left-handers. The label rule itself is unchanged.
  - Issues 6, 10 to 21, 23, 24, 26 and 29 to 40, apart from the parts named above.
