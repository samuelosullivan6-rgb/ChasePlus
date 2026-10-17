# My own read, before the panel

Written 2026-10-17, before any reviewer reported and before opening the 2026-10-16
review. Material: the committed build (HEAD 53dc8a5, which is also what GitHub Pages
serves), the generators at that commit (step 17, step 21 from git since the working
tree deletes it, coach_notes.py, the page template), and all 261 plans from
card_players_2026.json, whose plan text, start lines and targets are identical to the
committed player_cards_2026.csv (checked: 0 of 261 differ). Every count below is from a
script over those 261 plans; nothing is estimated.

## The three numbers fixed on 2026-10-16

| Measure | 2026-10-16 | Now |
|---|---|---|
| Plans whose first pitch line is a two-strike take | 115 of 229 | 113 of 229 |
| Contact lines that contradict their own numbers | 0 | 0 |
| Negative targets | 0 | 0 |

The first number barely moved because the ordering rule works where it can and has little
to work on: 100 of the 113 plans have only two-strike lines, and 27 of the other 13 had a
pre-two-strike leak that is a video item (the rule keeps those last). The rest are noted
hitters whose coach's note names a two-strike lead. So 113 is the shape of the leaks, not a
failure of the fix. What it does mean is that page 2 of the print card ("a take before two
strikes comes first") describes the opening of fewer than half the plans.

## Shape of the 261 plans

- 229 have at least one pitch line (181 two, 48 one); 29 say "Nothing stands out", 2 say
  "Nothing to change", 2 are a contact line alone, 1 is a frame line alone.
- First item: pitch line 181, contact line 43, fallback 29, frame line 8.
- First pitch line by count group: two strikes 115 (113 takes, 2 video items), ahead 67,
  0-1 or 1-1 40, first pitch 7. 16 plans open with a video item.
- 410 pitch lines: 163 name a pitcher hand, 44 are video items, 28 use the "about as often
  as other hitters" wording.

## Patterns, counted

1. **The plan says change, the target says there is nothing to beat: 80 of 229.** Every
   card with a "No target" sentence also has one or two pitch lines (56 "No target: in
   these spots you are already about at the league's rate", 24 "No chase target here").
   Examples: J. P. Crawford ("let breaking balls below the zone go ... 56% vs 50%"), Mike
   Trout, Isaac Paredes. On those 80, the hitter's 2026 excess in his leaks runs from −7 to
   +9 points, so for the upper end "you are already about at the league's rate" is true of
   the forecast, not of 2026.
2. **"Let fastballs above the zone go" next to "your fastball decisions are a strength":
   42 plans** (58 counting fastball video items). The closing clause is on 154 of the 229
   keep lines. Examples: Ben Rice, Bryce Eldridge, Lars Nootbaar; Curtis Mead in the
   sample.
3. **The card's first line is not the roster's "Start with": 48 cards.** 41 execution-led
   cards open with the contact line ("So with two strikes, a pitch that is clearly off is a
   take"), and in 25 of those the first pitch line, which the roster shows, is not a
   two-strike line (Nolan Gorman, Riley Greene, Colson Montgomery). 7 cards open with the
   spread line (Yainer Diaz, Ernie Clement, Mickey Moniak).
4. **Plans the player cannot act on: 16 plans are video items only** (James Wood, Nick
   Loftin, Fernando Tatís). "One for the video room, not a take rule" is an instruction to
   the staff in the player's plan. 9 of the 16 still print a number to beat ("Under 11 is a
   fix" on Loftin's).
5. **Plans that open with a smaller leak: 88 of 229** open with ② or ③ ahead of ①. The
   order is deliberate, but the plan never says why in the player's words; the reason is
   in small print under the leak list. On 5 of the 7 spread-line plans the line says "the
   two pitches below are the biggest pieces of it. Start with the first" and the first is
   ③ (Ernie Clement, Mickey Moniak, Yainer Diaz).
6. **Good choosers get the same imperative: 115 of 229 plans belong to hitters whose chase
   choices are better than average overall** (Geraldo Perdomo, 2nd, +15.7; J. P. Crawford,
   6th, +17.3; Mike Trout, 21st, +16.1). Nothing in the plan tells a top-20 chooser that
   his line is a small one.
7. **The roster quotes two near-identical rates: 14 start lines** with the hitter and the
   league under 5 points apart (Curtis Mead "52% vs 51%", Geraldo Perdomo "49% vs 46%"),
   where the plan line itself was reworded on 2026-10-16 to stop doing that.
8. **The target counts spots the plan does not name: 137 cards** list three leaks, take two
   into the plan, and put "In these spots" under the list of three.
9. **First line in a count where the hitter hits well: 94 of 229** (count status
   "productive"). This is the split the 2027 score is meant to settle; it waits.

## Added while the panel ran (before any reviewer reported)

10. **The spread line is false on all 7 cards that carry it with pitch lines.** "Your chase
    choices cost N runs a season, across every count; the two pitches below are the biggest
    pieces of it" sits above two lines that are not the two biggest leaks on the list
    beside it: Yainer Diaz (③ and ①, skipping ② at −1.6 for ③ at −1.0), Javier Sanoja (③
    and ②, skipping ①), Ernie Clement, Mickey Moniak, Luis García, Trea Turner, Michael
    Massey.
11. **The order rule also changes which leaks make the plan: 72 of the 181 two-line plans
    are not the two biggest leaks, and 16 plans leave leak ① out entirely** (Travis
    Bazzana, Yordan Álvarez, Corbin Carroll). The README and the card say the plan is "in
    the order to work on them"; neither says the order also chooses.
12. **The biggest number on the card says zero: 82 of 229 plans sit under a header "Cost of
    far-off chases 0.0"** (Geraldo Perdomo, J. P. Crawford, Lars Nootbaar; Nick Loftin in
    the sample). The header uses step 13's far-off baseline; the plan uses the card's.
13. **The first line is in a count where the count table shows the hitter's choices as a
    net plus: 82 of 229** (J. P. Crawford, two strikes +8.4; Lars Nootbaar, two strikes
    +6.7; Jakob Marsee, two strikes +7.5). The table beside the plan says the count is a
    strength while the plan's first line asks for a change in it.

## The noted hitters: card against reports

The plan's first line is the leak each coach's note names on all 17 (the 2026-10-16 fix),
though the notes for Peraza and García open with something else (below). The staff
reports do not always follow:

- Jeremy Peña: bottom10 says "the plan leads with the slider away and the early counts
  instead"; the plan leads with the two-strike fastball above the zone, as his coach's
  note says.
- Salvador Pérez: actionable says "the same rule as the bottom-10 report and his card ...
  the first pitch is where to start"; the card starts at 0-1 or 1-1.
- Ezequiel Tovar: bottom10 says "Two cheap places to start are 0-0 and 3-2"; the card and
  note start with two strikes.
- Mickey Moniak: bottom10 says early in counts "take the fastball above the letters"; the
  card's early line is changeups and splitters below the zone from right-handers.
- Oswald Peraza and Luis García: note and reports lead with three-ball counts, which the
  card cannot show until the three-ball group (waits).
- Andrés Giménez: the note says "the counts to look at are 0-1 and 1-1"; both plan lines
  are two-strike.
- Hunter Goodman: the note quotes "48% vs 30%" for the pre-two-strike breaking ball, the
  card line "62% vs 28%": different cells and baselines for what reads as the same pitch.
- Vocabulary: "changeups and splitters" (card), "offspeed", "soft stuff", "splitters/
  changeups"; "above the zone", "above the letters", "above the belt", "high heater";
  "0-1 or 1-1" (card), "one-strike counts", "1-strike", "early counts"; choices/contact on
  the card, decision/execution in the reports, five problem labels on the roster. Four
  league baselines: the card's (same spot, count and matchup), the notes' (count, distance,
  pitch group, side), bottom10's (count by distance), actionable's (strikes by pitch group
  by side, far-off only). Each report says it differs; none says by how much.

## The 2023 card

The 2023 target reads as a forecast made in 2023 ("with no change you'd be about 10 in
2024. Under 10 is a fix."). All 241 targets on 2023 cards are retrospective freezes
(out_of_sample = no), fit on pairs that include seasons after 2023; nothing on the card
says so, and the 2024 outcome, which step 20 has scored, is not shown. The same holds for
2022 (231), 2024 (229) and 2025 (235).

## Seen in passing

- At 375 px the card is 529 px wide: the "By count" section overflows the phone screen
  (committed page; the overflowing element is the count table's section).
- Page 1 of the print card has no coach's note; the interactive card shows the note to
  anyone, the player included (the one-card constraint stands).
- During this review another session rebuilt every season's page in the main checkout
  with an uncommitted change that folds the roster into the cards page and deletes step 21.
  This review is of the committed build; the plan text is the same in both.
