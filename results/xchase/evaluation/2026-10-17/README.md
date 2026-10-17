# The 2026 decision cards and coaching reports, evaluated again

17 October 2026. Scope: the interactive card and roster, the static and printable cards,
the noted-hitters write-up, the 17 coach's notes, the two staff reports, every 2026 plan,
and the 2023 card read as an old card. Judged as coaching instruments: structure, wording,
consistency, helpfulness, and how likely each document is to get a hitter to change. No
figure was re-checked against the data.

Method. A sample of 12 hitters drawn first ([sample.md](sample.md)), my own read of the
generators and all 261 plans ([own_read.md](own_read.md)), then four independent reviewers
who never saw each other, my read or the previous review, each given only what its reader
would have ([panel/](panel/), briefs in [panel/briefs.md](panel/briefs.md)). Every panel
claim used below was checked against the data, the code or the images; the ones that did
not hold are listed near the end. Screenshots are in screenshots/ (about 50 MB, kept
locally and out of git; every one cited here is named, and they were taken from 53dc8a5
apart from screenshots/a57e964/).

Material: the committed build 53dc8a5, which is also what GitHub Pages serves. During the
review another session committed a57e964, which folds the roster into the cards page and
retires step 21. The plan text, start lines and targets are identical in the two (0 of 261
differ, and 0 on the 2023 cards), so everything about wording holds for both; where a
design finding changed in a57e964 it says so.

## Verdict

The pitch line is still the best thing in the project, and the 2026-10-16 reorder did what
it was asked to do. What would now stop a hitter from changing is the card around that
line. Fix these three first:

1. **Make the first line the first thing to do.** On 111 of the 229 cards with a plan, the
   first printed line is a framing or contact sentence, the circled numbers run backwards,
   or the only lines are video items. In the cold read, 5 of 12 players could not name one
   first action.
2. **Stop the card from arguing with itself.** On 137 of 229 cards a sentence beside the
   plan undercuts it: "No target: ... you are already about at the league's rate" under
   "71% vs 43%" (80 cards), "your fastball decisions are a strength" under a fastball take
   (42), a header that says the far-off chases cost 0.0 (82). A hitter looking for a
   reason not to change finds one on the card itself.
3. **Make the coach's note and the staff reports say what the plan says.** 8 of the 17
   notes name a pitch word, a pitcher hand or a starting point the plan line does not.
   Five passages in the two staff reports start a hitter somewhere other than his card or
   contradict each other, and one of them, Peña's, now describes his card wrongly.

The rest is the target sentence nobody can use, the phone layout, the print card's
differences from the web card, and labels. Every reviewer would use the cards as a staff
tool now. None would hand them to players before the first two items are done.

## Scorecard

Scores 1 to 5, one column per reviewer. The 2026-10-16 panel's scores are in brackets.

| Criterion | Player | Coach | Designer | Analyst |
|---|---:|---:|---:|---:|
| Clarity | 3 (3) | 3 (3) | 3 (3) | 3 (3) |
| Actionability | 3 (2) | 4 (3) | 3 (4) | 4 (3) |
| Consistency | 2 (2) | 2 (2) | 2 (2) | 2 (2) |
| Visual design | 3 (3) | 4 (4) | 3 (3) | 4 (4) |
| Coaching value | 3 (3) | 4 (3) | 3 (4) | 3 (3) |
| Trust | 2 (2) | 3 (3) | 3 (3) | 2 (3) |

Consistency is 2 from every reviewer for the second day running, and again it is one
finding seen four ways. Actionability went up for three of the four: the order rule and
the video items were noticed. The designer's actionability and coaching value went down,
mostly on the phone layout and the Montgomery card.

## What works and should not be touched

- **The pitch line.** Count, hand, pitch, side of the zone, the hitter's rate against the
  league's, and how far off his swings were. All four reviewers named it first. The player:
  "a distance I can set a machine to."
- **"Keep swinging at strikes. The only changes on this card are the pitches above."** Both
  the player and the coach called it the line that heads off going passive.
- **Video items kept apart from take rules.** The coach and the analyst both credited the
  card for not making a take rule out of a pitch that was mostly within a ball of the zone.
  The distinction is right. Where it sits, in the player's plan, is finding 1.
- **The order rule itself.** A take before two strikes comes first wherever one exists; the
  noted start cell forces the plan and the note to lead with the same leak, checked on
  every build, and it holds on all 17.
- **Print page 1's order and print page 2's "What normal looks like, with two strikes."**
  The designer called page 1 the best of the three formats and the coach called page 2 the
  best teaching panel in the set.
- **The footer.** "The gain was mostly runs not lost; hits come later, if they come." No
  reviewer thought it oversold.
- **Frozen targets with a date and a commit, scored out of sample.** The analyst called it
  the right accountability design. The sentence that carries it is the problem (finding 4).
- **leak_pitches_2026.csv.** The coach built every video reel from it, with game, at-bat and
  pitch ids. Its hand labels need fixing (finding 7).
- **Saying nothing when there is nothing.** Miguel Vargas's card does not invent a fix.

## Findings, ranked by how much they would change a hitter's behavior

### 1. The first line is often not the first thing to do (111 of 229 cards)

A hitter does the first thing he reads. On these cards that is not a pitch:

| What the hitter reads first | Cards | Examples |
|---|---:|---|
| The contact line ("So with two strikes, a pitch that is clearly off is a take even when you could reach it") above the pitch lines | 41 | Colson Montgomery, Nolan Gorman, Jarren Duran |
| The spread line ("the two pitches below are the biggest pieces of it. Start with the first") | 7 | Yainer Diaz, Ernie Clement, Mickey Moniak |
| A higher circled number above a lower one (② then ①, ③ then ①) | 74 | Konnor Griffin, Mike Trout, Bryson Stott |
| Only video items ("one for the video room, not a take rule") | 16 | Nick Loftin, James Wood, Fernando Tatís |

(Cards can be in more than one row; 111 is the union.)

- **The contact line gives a second first instruction.** It is a two-strike rule, and on 25 of
  the 41 the pitch line under it, which the roster shows as "Start with", is not a
  two-strike line. On 34 of the 43 contact-line cards the hitter
  already chases less than the league with two strikes (Montgomery 37% against 40%), so the
  line asks him to fix what he does better than average. The player read Montgomery and
  Gorman as "two different first things".
- **The spread line is false on all 7 cards that carry it.** The order rule changed which
  leaks make the plan, so the two lines under "the two pitches below are the biggest
  pieces" are never the two biggest. Diaz's plan takes ③ (−1.0) and skips ② (−1.6); Javier
  Sanoja's leaves ① out. On 5 of the 7, "the first" is ③.
- **The order rule chooses as well as orders.** 72 of the 181 two-line plans are not the two
  biggest leaks, and 16 leave ① out entirely (Travis Bazzana, Yordan Álvarez, Corbin
  Carroll). Neither the card nor the README says so.
- **The page's selected picture follows leak ①, not the plan.** On 84 cards the picture that
  opens selected, and the default 3D view, is a different count from the plan's first line
  (template, the `state.sel` default). Montgomery's opens on a mostly blue two-strike tile.
- **Video-only plans give the player nothing to do.** "Who will be in that video room with
  me?" (player, on Loftin). 9 of the 16 still print "Under N is a fix".

Seen by: player (4 of 11 plans out of order, two-first-thing cards, Loftin, Diaz),
designer (Montgomery, phone order), coach (numbering, Diaz), analyst (A4, A6, A9).

### 2. The card argues with its own plan (137 of 229 cards)

| Sentence | Cards | Examples |
|---|---:|---|
| "No target: in these spots you are already about at the league's rate", or the contact version, under one or two take lines | 80 | Konnor Griffin (71% vs 43%), Colson Montgomery (57% vs 25%), Elly De La Cruz (83% vs 40%) |
| "Your fastball decisions are a strength" under a fastball take line | 42 (58 with fastball video items) | Curtis Mead, Wade Meckler, Ben Rice |
| Header "Cost of far-off chases 0.0" over a plan of takes | 82 | J. P. Crawford, Lars Nootbaar, Nick Loftin |
| First line in a count the count table shows as a net plus for the hitter | 82 | Crawford two strikes +8.4, Nootbaar +6.7, Curtis Mead +7.0 |

- On the 80 no-target cards, 73 print a plan line with a gap of 5 points or more beside the
  sentence (53 at 10 or more, 14 at 20 or more). The sentence is triggered by the 2027
  forecast, not the 2026 rate; on 55 of the 80 the hitter's own 2026 excess is 3 points or
  more on the target's scale. "Already" is the false word.
- The fastball clause tests all of the hitter's out-of-zone fastballs, not the pitch on the
  plan; it appears on 154 of the 229 closing lines.
- The header is far-off choices on step 13's baseline; the plan's leaks are on the card's.
  On 62 cards whose take lines cost 2 runs or more, the header is under half of that.
- 115 of the 229 plans belong to hitters whose chase choices are better than average
  overall (Geraldo Perdomo, 2nd of 261; J. P. Crawford, 6th; Curtis Mead, 40th). Nothing on
  those cards says the hitter is good at this and the line is a small one. The player on
  Mead: "why I'm told to change a pitch I swing at about as often as everyone else."

Seen by all four. The analyst counted the no-target and fastball kinds over all 261; the
player and coach found them on the sample cards.

### 3. The note and the staff reports send a different message from the plan

Under the one-card rule the player reads the coach's note too. It is written about "he".

**Notes that say something the plan line does not: 8 of 17.**

| Hitter | Plan's first line | Note |
|---|---|---|
| José Caballero | two strikes, fastballs above the zone; two lines | "One pitch ... the fastball above the belt" (the belt is in the zone) |
| Angel Martínez | two strikes, breaking balls below; no hand | "Two strikes, right-hander, soft stuff" |
| Zach Neto | two strikes, breaking balls below; no hand | "Sliders below the zone from right-handers ... Sit fastball" (40% of those pitches came from left-handers) |
| Oswald Peraza | two strikes, breaking balls below | "Three-ball counts first" |
| Luis García | ahead, fastballs above the zone | three balls is "the big one" |
| Andrés Giménez | two strikes vs RHP, fastballs above | "the counts to look at are 0-1 and 1-1" |
| Jeremy Peña | two strikes, fastballs above | adds the first pitch as "the other early-count piece" |
| Mickey Moniak | ahead vs RHP, changeups below | adds early high fastballs |

Peraza's and García's three-ball counts are the waiting item; the rest can be fixed now.

**Staff report passages that start the hitter elsewhere: 5.**

- **Peña**, bottom-10 report: "the plan leads with the slider away and the early counts
  instead". The plan leads with the two-strike fastball above the zone, and his note calls
  the slider away a video item. This is the sentence added on 2026-10-16 to reconcile the
  two, and it now describes the card wrongly.
- **Pérez**, actionable report: "the same rule as the bottom-10 report and his card ... the
  first pitch is where to start". The card starts at 0-1 or 1-1.
- **Tovar**, bottom-10: "Two cheap places to start are 0-0 ... and 3-2". The card starts with two
  strikes.
- **Moniak**, bottom-10: early, "take the fastball above the letters". The card's early line is
  changeups and splitters below the zone.
- **Neto**: the actionable report puts him among hitters with "no single pattern to drill";
  the bottom-10 report says "right-handed slider below the zone, period."

**The same pitch carries different rates.** Caballero's two-strike high fastball is 81% vs
51% on the card and 77% vs 39% in the actionable report. Neto's two-strike breaking ball is
69% vs 47% and 69.5% vs 56%. Goodman's early breaking ball is 62% vs 28% on the plan line
and 48% vs 30% in his note. Each report says its baseline differs. None says by how much,
and in the room the player holds the card while the coach holds the report.

The staff reports are hand-written. No step writes or checks them, so nothing caught the
Peña sentence going stale. The coach: "Until then a coach has to reconcile every packet
before a hitter sees it."

### 4. The target cannot be read or tracked (149 cards with a number, plus every earlier season)

- **No unit.** "You'd be about 14 in 2027. Under 14 is a fix": 14 of what is never said. The
  player: "14 what, on which pitches?"
- **"These spots" are not the plan's spots.** 105 of the 149 pool a leak that is not on the
  plan, 22 include a video item, and on 9 every leak is a video item.
- **It cannot be found in the numbers beside it.** It is on step 19's baseline, so on 46 of 149
  cards the number lies outside every gap the leak list prints (Wyatt Langford: 13 beside a
  24-point gap).
- **Old cards read as forecasts made at the time.** Every target on the 2022 to 2025 cards is a
  retrospective freeze (231, 241, 229 and 235 cards, stamped out_of_sample = no). The card
  says "with no change you'd be about 10 in 2024" in the future tense, never says it was fit
  after the fact, and never shows the result, which step 20 has already scored. Nolan
  Gorman's 2023 card says "Under 10 is a fix"; his 2024 number was 13. Yainer Diaz's says
  "Under 22" (2024: 22, not under); Michael Harris's says "Under 15" (2024: 17). A reader of the 2023
  page would take it for a prediction that is still open.
- The in-season readout that would let a hitter track it waits for the 2027 score.

### 5. The phone, where a player opens his link

Seen on all four cards at 375 px, light and dark:

- The first screen is all controls; the name starts three-quarters of the way down
  (card_jose_caballero_phone375_light_01.png).
- The pictures come after the plan, the leaks, the target, the table, the season chart and
  the footer, two screens below "Numbered on the pictures" (..._03 against ..._04).
- The page is 529 px wide at a 375 px viewport, so it scrolls sideways; the By count
  section runs off the card and the xwOBA column is cut mid-number (..._03 bottom). This is
  still there in a57e964, at 532 px.
- On the picture grid, "0-1 or 1-1" wraps to "0-1 or 1-" over "1", and the markers are too
  small to read (..._04).

### 6. The print card is not the web card

- **Hand-named leaks sit on the all-pitchers pictures.** On 6 of the 12 sample print pages
  (Neto, Montgomery, Basallo, Meckler, Gorman, Diaz), a leak named "vs RHP" is numbered on
  a picture titled "all pitchers". The code draws every leak on that row
  (`print_markers`). The web puts it on the hand's row. 146 of the 261 hitters have a
  hand-named leak.
- **A switch hitter gets one side, unlabeled.** Martínez's print shows his left-handed side
  only, with no side named; the web labels "Batting left / Batting right".
- **Contact hitters lose their contact picture.** The "Misses on chases" row is web only
  (Montgomery, Gorman).
- **The footer prints over the season chart on three-item contact plans.** Seen on Montgomery,
  Duran and Gorman. García's and Moniak's three-item pages clear it by a few pixels.
- **"-0.0"** in the print header on 4 of the 12 (Mead, Meckler, Vargas, Loftin); the web
  prints 0.0.
- **The coach's note is on the web card and the PNG but not on the print card.** That is the
  one place where the note's wording does not reach the player, and nothing says which
  format is meant for whom.

### 7. "Against right-handers" includes left-handers

A leak is labeled with a hand when 80% or more of its pitches came from that hand
(`HAND_RHP_SHARE` in step 17). The rates on the line still count every pitch: 202 of the
230 hand-named leaks include the other hand's pitches. The video list follows the label:
leak_pitches_2026.csv has 45 left-handers' pitches inside "vs RHP" leaks across 8 noted
hitters (Duran 13, Giménez 11, Montgomery 6) and 10 right-handers' inside Goodman's "vs
LHP" leak. A reel cut by leak gets the wrong pitchers (coach, seen; cause from the code).

### 8. Labels a staff will trip on

- **Roster "Problem" column.** 172 of 261 hitters are "mixed", including 58 whose choices and
  contact are both positive (Steven Kwan +17.6 / +4.7). The filter barely filters.
- **The roster says Choices is measured "against an average hitter at the same spot, count and
  matchup".** It is count by distance bucket (`leak_rules.add_choices_contact`). The
  sentence is still there in a57e964.
- **At 1440 px the roster hides "Beat" and "Start with".** In a57e964 the table is 1761 px
  wide in a 1390 px box; 53dc8a5 cuts it the same way (roster_desktop_light.png, right
  edge).
- **xChase+ is never explained**, on any of the 12 cards or the print guide, though it is the
  second line of every card and the notes lean on it ("his xChase+ was 109").
- **Two cost numbers with opposite signs in every header**: a positive far-off cost beside a
  negative Choices bar (Caballero 11.7 and −13.5), and on Diaz's card a third, "14 runs", in
  the plan.
- **The roster and the card disagreed by a tenth or an inch on 50 hitters** (the roster rounded
  the CSV's rounded values: Caballero −13.4 against −13.5). Fixed in a57e964, which draws the
  roster from the card's data.

### 9. Smaller items

- **Dark mode.** The color scale's midpoint is near black, so the legend's "Gray: about average"
  is wrong. The dark PNGs say "White: too few pitches to say" with nothing white on them
  (png_zach_neto_dark.png).
- **The 3D view** cuts its axis labels on the phone and overprints the bottom tick on desktop.
  It is collapsed by default, so it costs little.
- **The guide is slightly wrong.** Print page 2 says "a take before two strikes comes first",
  which describes fewer than half the plans: 113 open with a two-strike take, 100 of them
  because every line is two-strike.
- **The roster start line** quotes near-identical rates on 14 hitters ("52% vs 51%" for Mead),
  where the card's line was reworded on 2026-10-16 to stop doing that.
- **Leak markers crowd** on Martínez's and Neto's two-strike tiles.

## The cold read of the 12

What the player said he was told to do first, against the roster's "Start with" and, for
the four noted, the coach's note. A mismatch is a finding in itself.

| Hitter | Player's first action | Roster "Start with" | Coach's note | Result |
|---|---|---|---|---|
| José Caballero | two strikes, take the fastball above the zone | same | same pitch as "above the belt"; "One pitch" on a two-line plan | matches the plan; the note's word does not |
| Angel Martínez | two strikes, take breaking balls below | same | adds "right-hander" | matches; note narrower |
| Zach Neto | print: two-strike breaking balls below; web note: "sit fastball", sliders from righties | two-strike breaking balls below | sliders, right-handers, sit fastball | split: print and web send him different ways |
| Colson Montgomery | two first things: the contact rule, and the ahead breaking ball | ahead vs RHP, breaking balls below | ahead breaking ball first | split: the card's first line is not the start |
| Curtis Mead | two strikes, take fastballs above | same, "(52% vs 51%)" | none | matches, but he does not believe it |
| Samuel Basallo | two strikes vs RHP, take fastballs above | same | none | matches |
| Wade Meckler | 0-1 or 1-1, take fastballs above | same | none | matches; "fastball decisions are a strength" puzzled him |
| Konnor Griffin | 0-1 or 1-1, breaking balls below, after decoding ② before ① | same | none | matches, with effort |
| Nolan Gorman | two first things: the contact rule, and the ahead changeup | ahead vs RHP, changeups below | none | split |
| Miguel Vargas | nothing | none | none | matches |
| Nick Loftin | nothing to do himself; "the video room" | the video item | none | no action |
| Yainer Diaz | unsure; guesses the ③ line | 0-1 or 1-1, breaking balls below (③) | none | guessed right, unsure |

Seven of 12 matched cleanly (Caballero, Martínez, Mead, Basallo, Meckler, Griffin, Vargas).
Five did not give one first action. On the noted four, every note differs from the plan in
some way: Caballero by a word, Martínez by a hand, Neto by pitch, hand and an extra cue, and
Montgomery's agrees with the start but not with the card's first printed line.

The "what I do not understand" sentences cluster:
- a sentence beside the plan contradicting it, on 5 (Mead, Meckler, Griffin, Loftin, Diaz);
- which side or which hand a print picture shows, on 2 (Martínez, Basallo);
- the contact rule against the take lines, on 2 (Montgomery, Gorman);
- the target's unit and spots, on Caballero's;
- whether Neto's two low breaking-ball lines are one pitch or two;
- what "-0.0" and the ranking language mean, on Vargas's.

None questioned what a pitch line asked him to do.

## Progress since 2026-10-16

The previous review was not at results/xchase/evaluation/2026-10-16.md. It is a scratchpad
file of session 2cefb682 (card_and_report_evaluation_2026-10-16.md, an identical copy in
session e2ca16c2); I read it only after the panel reported and my checks were done.

| 2026-10-16 finding | Now | Evidence |
|---|---|---|
| 1. Plan ordered by runs, leads with the hardest take (187 of 229) | **Resolved**, with side effects | The order rule works wherever there is a pre-two-strike take; 113 still open with two strikes, 100 of them because every plan line is two-strike. The rule also changes which leaks make the plan (72 plans, 16 without ①) and reverses the circled numbers (74), unexplained (finding 1). |
| 2. Player and coach given different first steps (9 of 17) | **Partly resolved** | Every plan now leads with its note's start cell. 8 notes still say something the plan line does not (finding 3). The staff copy was rejected; the note stays on the player's card. |
| 3a. Contact line quotes the wrong evidence (6) | **Resolved** (0) | A new contradiction in its place: a two-strike rule above lines in other counts, for hitters who already take more than the league with two strikes (34 of 43). |
| 3b. "About as many ... but those swings cost you" | **Resolved on the card**, open on the roster | The card says which counts the swings came in; the roster still prints "52% vs 51%" (14). |
| 3c. "No single pitch is the problem" above a lopsided line | **Regressed** | Replaced by the sentence the review proposed, "the two pitches below are the biggest pieces of it", which the new order makes false on all 7 cards. |
| 3d. Take rules on borderline pitches (32) | **Resolved** (0) | They are now video items, 44 lines, which puts staff instructions in the player's plan (16 plans are only that). |
| 4. Target misnames its number; negative targets (52) | **Resolved as asked, one regression** | One sentence, no negatives. The suppression sentence, "you are already about at the league's rate", is false or contradicted on most of the 80 cards it replaced (finding 2). The unit and "these spots" are still undefined, and "the goal in each leak's own units" was not done. |
| 5. Header and footer | **Mostly resolved** | Footer is one plain sentence; the header names "far-off" and "all chases". Two opposite-signed costs remain, xChase+ is unexplained, "-0.0" prints, and the rank stays (one card). |
| 6. Four vocabularies, three baselines | **Partly resolved** | One leak phrase with the hand, "0-1 or 1-1" everywhere, a mapping line and a baseline footnote in each report. Still: decision/execution in the report bodies, five problem labels on the roster, the notes' own words, and different rates for the same pitch across documents. The hand-tab repetition is fixed. |
| 7. Things the card cannot say | **Resolved where allowed** | Keep line, pitch counts and the video list are done (the keep line's fastball clause is finding 2). The three-ball group and the in-season readout wait for the 2027 score. |
| 8. The visual system | **Mostly resolved** | Neutral gray, the misses palette, a legend under the grid, bars for runs, numbered plan lines are all in. Dark mode's midpoint and the dark PNG's "White" are new; the print legend still sits by the trend chart; markers still crowd. |
| 9. Page and roster on a phone | **Partly resolved** | The plan comes before the pictures on phones, 3D is collapsed, and the roster has short phone rows. The count table no longer clips but now widens the page (529 px); the controls fill the first screen; the roster hides two columns at 1440 px. |
| 10. Staff reports | **Partly resolved, one regression** | The ceiling column is named as not a forecast, and Montgomery and Duran are framed as staff decisions. Pérez still has two starting rules. Peña's reconciling sentence is now wrong. Neto, Tovar and Moniak are new conflicts. |
| 11. Smaller items | **Resolved** | "Nothing to change ... those swings have paid", the README blurb and "Same side and hand" are all fixed. |

Of the three numbers fixed that day, two hold (0 contact lines against their numbers, 0
negative targets) and one moved by two (115 to 113 two-strike openers, explained above).

## What I checked and what I set aside

**Checked, on the committed build.**
- Every count in this write-up comes from a script over the 261 plans in the page's own
  embedded data, or from the code.
- Every visual claim used was looked at in the screenshot it names.
- The 8 non-noted print cards were built from the committed code in a scratch copy, whose
  page, CSV, PNG and README came out byte-identical to the committed ones. They are not in
  the repo.
- Screenshots were taken headless through Chrome from a frozen copy of the committed site:
  1440 px and a 375 px phone viewport at 2x, both themes.
- The a57e964 roster view and one card are in screenshots/a57e964/ for the carry-over checks.

**Panel claims that did not survive.**
1. "The default picture is always Two strikes" (coach). The page opens on leak ①'s count. On
   the four cards he named, ① happens to be a two-strike leak.
2. "68 cards" with the header under half the plan's cost (analyst). I count 62 on the plan's
   take lines. The pattern holds; the count did not reproduce.
3. "The coach's note uses different words from the plan, 4 of 4" (designer). Montgomery's
   note uses the plan's words, so it is 3 of 4.
4. The roster-against-card mismatch: "41 hitters" (analyst), "3 of 12" (coach). On five
   fields it is 50, and a57e964 fixed it.
5. "Step 17 --data-only rebuilt the 2023 cards" (analyst). The 2023 page is a full step 17 run
   through step 22; --data-only is for freezing. The point stands: current code, a
   retrospective target.
6. "Caballero's note says 'every year' against a chart that dips in 2025" (coach). There is no
   contradiction: the note's series is two-strike far-off high fastballs, the chart is every
   far-off pitch. It survives only as a reading problem.

**Not verified, so not used.**
- The designer's claim that Martínez's first-pitch outline differs between the PNG and the
  web card.
- The designer's claim that print page 2's average-hitter caption ("below and away") is not
  visible in its picture.
- The player's line-wrap "9 / of 21".

**Set aside.**
- The 3D view's worth beyond its labels.
- The terrain stills.
- Anything that would need a figure re-checked.

**Process notes.**
- I drew the sample after surveying the material and parsing the plans, with a fixed seed
  (random.Random(20261017)) and strata set by plan type and archetype, so the read did not
  choose a hitter. The draw script is beside the sample.
- The designer wrote two crop images into a scratchpad folder against its brief, deleted
  them and said so; nothing in the project was touched.
- The analyst's packet JSON had no count tables (they are only in the page's data), which is
  why its count-table check covers the 12 sample cards only; I ran it on all 261 (82).

## Recommended order of work

Items 1 to 6 are wording, layout and code checks: no change to the leak rule or the frozen
2026 predictions, so they can ship before 2027. After any of 1, 2, 4 or 6, run step 22 (all
seasons), not step 17 alone.

1. **Make the first printed line the instruction.** In `plan_items` in
   scripts/17_build_player_cards.py:
   - Fold the contact line into the pitch line it explains, or make it the only line.
   - Number plan lines 1, 2 in work order with the leak number as a small tag.
   - Make `spread_line` name its pieces truthfully ("two of the pieces", or no "biggest").
   - Say on video-only plans that the staff takes it.

   In scripts/templates/player_cards.html, open the selected picture on the plan's first
   line, not leak ①.
2. **Stop the card arguing with itself.** In step 17:
   - `target_text`: "next season, with no change, about at the league's rate; no number to
     beat" instead of "already".
   - `keep_line`: drop the fastball clause when a plan line is a fastball.
   - Frame a plan for a hitter whose choices are better than average ("You're 40th of 261
     at this; one small thing").
   - Say why a first line sits in a count the table calls a strength, or move it.

   Then add a check over all 261 plans, the way coach_notes.check works, that stops the
   build when a summary sentence contradicts the lines or numbers beside it. These kinds
   are cheap to test.
3. **Make the notes and reports follow the card.**
   - In scripts/coach_notes.py, reword the 8 notes in the plan's words and add a claim that
     the note's first sentence names the plan line's pitch, count and hand.
   - In results/xchase/coaching/bottom10_2026_coaching_notes.md and
     actionable_hitters_2026.md, fix Peña, Pérez, Tovar, Moniak and Neto.

   A bigger option, worth deciding now: the per-hitter sections of the two reports
   duplicate the noted README and the notes, are checked by nothing, and hold all five
   report conflicts. Cut them to the group-level analysis and point to the README entries,
   or have step 17 write them with the README. The cost is the scouting detail the coach
   valued (velocities, pitch types), which could move into the notes.
4. **Rewrite the target sentence**, in `target_text` in step 17 and its uses in the template
   and README:
   - name the unit and the leak numbers it covers;
   - on a retrospective card, say it was fit after the season and print step 20's result
     from leak_scores_<next season>.csv;
   - drop the number where every leak is a video item.

   The line it scores against stays frozen.
5. **The phone and the roster**, in scripts/templates/player_cards.html:
   - name and plan on the first screen, with the controls folded into one row;
   - the count table in its own scroll box, which fixes the 529 px page;
   - the "0-1 or 1-1" header;
   - the dark-mode midpoint and the dark PNG legend (card_style);
   - the roster's Beat and Start with visible at 1440 px, its Choices sentence corrected,
     and its start line carrying "about as often".

   A bigger option the designer raised: show only the tiles the plan names on every
   surface, with the 12-tile grid behind a toggle. Print page 1 already shows the shorter
   card works.
6. **The print card**, in `print_pages` and `print_markers` in step 17:
   - hand-named leaks drawn on a labeled hand picture;
   - the switch hitter's side named;
   - the misses row for contact hitters;
   - a check that the footer clears the chart;
   - "0.0", not "-0.0".
7. **Hand labels.** Now: word a leak with 80% or more of its pitches from one hand as "mostly
   from right-handers", and filter leak_pitches_2026.csv to match. After the 2027 score:
   compute hand-named leaks on that hand's pitches only, since that changes the card's rates
   against the frozen file.
8. **Wait for the 2027 score** (step 20 on leak_predictions_2026.csv):
   - the three-ball count group, which touches leak_rules and the frozen file and resolves
     the Peraza and García notes;
   - the in-season readout beside the target;
   - whether leaks in counts where the hitter hits well move down the plan (94 of 229 first
     lines are in such a count).
