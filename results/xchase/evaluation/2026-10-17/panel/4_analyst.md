# Reviewer 4: the front-office analyst (raw)

Packet: the generators at 53dc8a5 (17, 21, coach_notes, the template, leak_rules, card_site, 12, 13, 15, 16, 19, 20), card_players_2026.json with all 261 plans, the 2026 and 2023 CSVs, the roster CSV, the noted README, both staff reports, the 12 sample cards' page text, the roster page text and three 2023 cards. Brief: panel/briefs.md. Report as returned, unedited. The packet's card_players_2026.json had no count tables (the reviewer flagged it); those live only in the page's embedded data.

---

Reviewer 4 of 4, front-office analyst. I read only the packet folder and wrote no files. The counts below come from Python run over data/card_players_2026.json, player_cards_2026.csv, team_view_2026.csv and the 2023 JSON.

Packet gaps (seen): card_players_2026.json has no `tables` key, even though the brief lists it, so I could check the count table only on the 12 sample page texts. The packet also has no leak_predictions_*.csv, no step-20 output and no plan_items_by_hand.

# A. Sentences that do not follow from the numbers beside them (2026, 261 plans)

**A1. The no-target sentence claims something false about the present.** Seen.
- 80 cards say "No target: in these spots you are already about at the league's rate", or the contact version of it.
- The trigger is the 2027 forecast rounding to 2 points or less (17, `target_text`, lines 763-768). It is not the 2026 rate.
- In 55 of the 80, the frozen 2026 excess on the target's own scale is 3 points or more (41 are at 5 or more).
- In 73 of the 80, a plan line printed beside it shows a gap of 5 points or more (53 at 10 or more, 14 at 20 or more).
- Examples:
  - Konnor Griffin: "71% vs 43%" on the plan; frozen excess 7 points.
  - Colson Montgomery: "57% vs 25%"; frozen excess 4 points.
  - Elly De La Cruz: "83% vs 40%"; frozen excess 8 points.

**A2. The target number cannot be found among the numbers it summarises.** Seen.
- It is measured on a different baseline (step 19's simpler league cell) and pools all three leaks.
- 46 of 149 number targets lie outside the range of the gaps the leak list prints. Examples:
  - Alejandro Kirk: target 39; his only leak prints 86/58, a 28-point gap.
  - Masyn Winn: 9 against 19.
  - Wyatt Langford: 13 against 24.

**A3. The target covers spots the plan does not tell the player to work on, or tells him not to make take rules.** Seen.
- 105 of 149 number targets pool a leak that is not on the plan (Jonathan Aranda, Bryson Stott, José Caballero, whose leak 3 is a video item).
- 22 include a "video room, not a take rule" line.
- On 9, every leak is a video item, yet the card still says "Under N is a fix" (Nick Loftin, Vladimir Guerrero, Alejandro Kirk).

**A4. "The two pitches below are the biggest pieces of it. Start with the first." is false on all 7 cards that carry it.** Seen.
- Each plan skips a costlier leak:
  - Yainer Diaz: plan shows ③ and ①; ② at −1.6 is skipped.
  - Ernie Clement: ② at −1.3 skipped, ③ at −1.1 shown.
  - Mickey Moniak: ② at −2.4 skipped.
  - Javier Sanoja: leak ① is not on the plan at all.
- "The first" is then the smallest of the pieces shown.
- On Luis García's card, the coach's note calls the three-ball counts "the big one", which contradicts this line on the same card.

**A5. "Your fastball decisions are a strength" sits on 58 cards whose plan includes a fastball line.** Seen.
- Examples: Curtis Mead, Wade Meckler, Nick Loftin. Ten more cards have a fastball leak that is not on the plan.
- The clause tests all out-of-zone fastballs netting at least +1 run (`keep_line`), not the pitch on the plan.

**A6. The contact line adds a rule, then the closing line denies it.** Seen.
- On 41 cards, "So with two strikes, a pitch that is clearly off is a take even when you could reach it" sits above "The only changes on this card are the pitches above" (Colson Montgomery, Nolan Gorman, Jarren Duran).
- On 34 of the 43 contact-line cards, the hitter's two-strike chase rate is already below the league's (Montgomery 37 vs 40, Riley Greene 34 vs 41, Connor Norby 31 vs 40). The line then tells him to fix something he already does better than average.

**A7. The header "Cost of far-off chases" reads against the plan.** Number seen; reader confusion inferred.
- On 68 cards the header is under half the runs of the leaks the plan says were "typically 4+ inches off" (minimum 2 runs). Examples:
  - Mike Trout: 0.0 against 4.9.
  - Nolan Gorman: 0.2 against 4.7.
  - Jonathan Aranda: 0.0 against 6.1.
- The header is a net over all far-off pitches, and nothing on the card says so.

**A8. The stated order rule is broken.** Seen.
- The README and the printed card's page 2 promise "a take before two strikes first".
- 3 plans (all noted) put a two-strike take first because the coach's note forces where the plan starts: Ceddanne Rafaela, Ozzie Albies, Jarren Duran.

**A9. Plan numbers are shown out of order (③ or ② above ①).** Seen. 74 cards (Konnor Griffin, Colson Montgomery, Yainer Diaz). It is explained only in a gray caption.

**A10. The roster's start line quotes rates that do not make the case.** Seen.
- 14 hitters, e.g. "(52% vs 51%, 4 in off)" for Curtis Mead, Geraldo Perdomo 49 vs 46, JJ Bleday 42 vs 39.
- The card words these lines "about as often"; the roster drops that.

**A11. On the 12 sample cards only (tables missing from the JSON): a plan line in a count group whose Choices total is positive.** Seen, 4 of the 11 cards that have plan lines.
- Curtis Mead: two strikes, +7.0.
- Colson Montgomery: +1.5.
- Nolan Gorman: +0.4.
- Wade Meckler: 0-1 or 1-1, +0.9.

**A12. The coach's note against the plan on the same card (17 noted).** Seen.
- "One pitch" on a two-line plan: Caballero and Harris.
- A hand the plan line does not carry:
  - Neto: "from right-handers", but 40% of the 95 pitches in his first plan line came from left-handers.
  - Martínez: "right-hander" (he is a switch hitter).
  - Harris: "mostly from right-handers".
- A different place to start:
  - Oswald Peraza: "Three-ball counts first", but the plan leads with the two-strike breaking ball.
  - Andrés Giménez: "the counts to look at are 0-1 and 1-1", but both plan lines are two-strike.
- Changes not on the plan, against "the only changes": García and Peraza (three-ball counts), Peña (first pitch), Moniak (early high fastballs).

# B. Five hitters side by side

The five are José Caballero, Angel Martínez, Zach Neto, Colson Montgomery (all noted) and Konnor Griffin.

**José Caballero**
- **Card plan:** ① "With two strikes, let fastballs above the zone go… 81%… 51%… 6 inches"; ② the two-strike breaking ball below, 77 vs 51.
- **Leaks:** ③ "Ahead in the count, fastballs above the zone 52% vs 30%" (a video item, not on the plan).
- **Target:** "chased 24 points above the league… about 14 in 2027".
- **Roster:** choices −13.4 (the card says −13.5); "under 14 (was 24)"; start line "(81% vs 51%, 6 in off)".
- **Count check (README):** two strikes, struggling; ahead in the count, struggling. The ahead check is for a leak that is not on the plan.
- **Coach's note:** "One pitch with two strikes: the fastball above the belt… far-off ones… 55%, 65%, 77%".
- **Actionable report:** "37 of 48 fastballs above the zone (77% vs 39%… −4.9 runs, the single worst cell for any hitter in the group)". The same report gives Harris −5.0 from one cell, so it contradicts itself. It also says "With fewer than two strikes he is a league-average taker", which conflicts with card leak ③. Its table gives a two-strike far-off series of .36/.29/.47.
- **Bottom-10 report:** not covered.

**Angel Martínez**
- **Card plan:** ① two-strike breaking balls below, 76 vs 50; ② two-strike "changeups and splitters below", 70 vs 44. Neither line names a hand.
- **Leak list:** "changeups / splitters"; ③ breaking balls down and in, 79 vs 21.
- **Target:** 28 → 16.
- **Roster:** top-leak runs −4.0 (the card says −3.9).
- **Coach's note:** "Two strikes, right-hander, soft stuff that starts at the knees: take it."
- **Actionable report:** against right-handers only, "breaking (70% vs 47%), offspeed (64% vs 39%)… down-and-in (77% vs 24%)"; "anything soft that starts at the knees".

**Zach Neto**
- **Card plan:** ① two-strike breaking balls below, 69 vs 47; ② two strikes against right-handers, breaking balls down and away, 43 vs 23; "your fastball decisions are a strength".
- **Target:** 16 → 7.
- **Roster:** "mostly choices".
- **Coach's note:** "Sliders below the zone from right-handers… (290, up from 184). Sit fastball". The 290 is right-handers' sliders below the zone in all counts, which matches no cell on the card.
- **Actionable report:** puts Neto among hitters whose loss is "spread across every count, pitch group and side of the zone. There is no single pattern to drill."
- **Bottom-10 report:** "Two-strike breaking balls below the zone: 69.5% chase vs 56%"; "right-handed slider below the zone, period". It contradicts the actionable report. The note's "well above league in 2024 and 2025" matches gaps of 9 and 5 points in this report.

**Colson Montgomery**
- **Card plan:** contact line first ("68%… against 45%"); then ② ahead against right-handers, 57 vs 25; then ① two strikes, "about as often… cost you 1.9 runs".
- **Target:** "No chase target here: … already about at the league's rate".
- **Roster:** "mostly contact", "no target".
- **Coach's note:** "Start with the breaking ball below the zone when he is ahead, the plan's first take; with two strikes he cannot afford to chase at all."
- **Actionable report:** whiff rate against a league 42%; "a different and slower conversation".
- **Bottom-10 report:** "Chase rate 32.7% vs 30.5%" (the card says 33 vs 29); whiffs against a league 43%. It says "0-strike chase rate 27% vs 19%" where the card uses "ahead". It calls the pitch below the zone before two strikes "his card's first line", but the card's first line is the contact line.
- **README blurb:** "contact as much as choice", although contact is −13.0 against choices −3.6.

**Konnor Griffin**
- **Card plan:** ② 0-1 or 1-1, 71 vs 43; ① two strikes, 61 vs 47. Trend strip "(1 season)".
- **Target:** "No target: … already about at the league's rate". The frozen excess is 7 points.
- **Roster:** choices −11.1 (the card says −11.0); "choices"; "no target".
- **Actionable report:** a rookie, "Worth tracking, not yet worth a verdict." The card gives him a full plan with no such caveat.

**Vocabulary differences**
- **Pitch:**
  - fastballs above the zone / fastball above the belt (Caballero's note and the actionable report) / above the letters / high heater;
  - breaking balls / sliders / sliders and sweepers / soft stuff / anything that breaks;
  - below the zone / below the knees / starts at the knees.
  - "Above the belt" includes strikes, against "keep swinging at strikes".
- **Count:** ahead in the count (1-0 2-0 3-0 2-1 3-1) / 0-strike / early / before two strikes / three balls.
- **Hand:** right-handers on a note but no hand on the plan line (Martínez, Neto).
- **Problem type:** choices / mostly choices / mostly contact (roster); decision-only, decision-led, execution-led (actionable report); "Volume chaser", "Normal chase rate, can't make contact" (bottom-10 report); "contact problem" (notes).
- **The header number:** Cost of far-off chases (card) = Runs at stake (roster) = "Far-off chases cost" (README) = Far-off recoverable (actionable report).
- **Runs:** Choices/Contact versus Decision/Execution.

**Baseline differences**
- **Card plan and leak list, "hitters on average":** a smoothed rate at the same spot and exact count, matched on batter side and pitcher hand.
- **Target, "the league":** season × count × distance bucket × pitch group × side of the zone.
- **Runs (Choices):** count × distance bucket. The roster's note misdescribes this as "same spot, count and matchup".
- **Coach's notes:** the target's cell.
- **Actionable report:** strikes × pitch group × side, far-off pitches only.
- **Bottom-10 report:** count × distance.
- **Count check:** every plate appearance that reached those counts.
- **Result:** the same cell prints a league rate of 47% on Neto's card and 56% in the bottom-10 report. Caballero's two-strike high fastball is 81/51 on the card, 77/39 in the actionable report and 77 in the note.
- Only the two staff reports say their baseline differs from the card. The card itself never names one.
- Rafaela's note compares his 2025 rate (28%) with the 2026 league (17%) (coach_notes.py, lines 215-217).

# C. The 2023 target

**What a reader would believe.** "In these spots you chased 19 points above the league in 2023… you'd be about 10 in 2024. Under 10 is a fix." (Gorman; Diaz 34→22, Harris 26→15.) It reads as a forecast made at the end of 2023 by whoever issued the card, handed to the player for 2024, and never checked. The future tense makes it look still open.

**What it actually is.**
- Step 17 `--data-only` rebuilt the 2023 cards with 2026 code (xChase+ 1.1, today's leak rule and thresholds).
- Step 19 `--retrospective` froze the prediction after 2024-26 were already in the data. The line was refit on pairs ending by 2023, and the file is stamped out_of_sample = "no": 241 of 280 cards, 154 of them with a number target.
- Step 20 scores it against 2024, but there is no score in the packet.
- `target_text()` ignores out_of_sample, the freeze date and the commit, and the template prints only `Target: …`. The card never says it was made after the fact or whether it was beaten.
- The card's trend strip shows 2024-26 (hindsight), but for all far-off pitches, so it cannot settle the target.
- The footer's evidence sentence comes from a backtest that includes the 2023→24 pair (inferred: step 17 reads the backtest summary with no season filter).

**Earlier seasons in general** (inferred from code).
- Any target before 2026 can only be retrospective: step 19 refuses an out-of-sample freeze once later pitches exist (lines 289-292).
- 2021 cannot have one, because no pairs end by 2021.
- The 2025 card would forecast 2026, a season the reader has already seen.
- The roster's "Beat… in {season+1}" wording has the same problem.

# Standard output

## 1. Verdict
The plan lines are good coaching sentences: one pitch, a count, a location and how far off. The sentences around them (target, framing line, closing line, roster summary) often contradict the numbers printed beside them. The documents disagree on where several noted hitters should start and what "the league" means. I would not put these in front of players until the target sentence and the summary lines are fixed and checked by code, and the earlier-season targets are labelled as retrospective.

## 2. Scores
- **Clarity: 3.** The plan lines are plain, but there are four baselines, numbers out of order, and a target sentence a reader cannot decode.
- **Actionability: 4.** Each line names count, pitch, location and depth, and separates video items from take rules.
- **Consistency: 2.** The kinds in A recur on 7 to 105 cards each, there are cross-document conflicts on the start, and 41 hitters print a value differently on the roster than on the card.
- **Visual design: 4.** Clean, to-scale catcher's view with numbered markers tied to the leaks. Dense, and the target is styled as a gray caption.
- **Coaching value: 3.** The plan lines and the honest evidence footer help. Conflicting start points and a target detached from the plan undercut them.
- **Trust: 2.** The figures are code-checked, but sentences assert things their own numbers refute, and the staff reports are unchecked.

## 3. Strengths
- Plan lines give the count, hand, pitch group, side of the zone and median inches off.
- Borderline pitches are marked "video room, not a take rule" (37 cards).
- "Keep swinging at strikes" is on every card.
- The rate clause avoids printing two near-identical percentages.
- The coach's notes are fact-checked in code, and each note's starting leak is forced to be the plan's first pitch line. This holds on all 17.
- Frozen targets carry the date and commit, cannot be overwritten, and are scored out of sample. That is the right accountability design.
- The evidence footer and the README's two cautions do not oversell the payoff.
- The same leak phrase appears in the leak list, the roster and the README.

## 4. Issues
1. **[high]** The no-target sentence asserts the hitter is "already" at the league's rate. card_players_2026.json `target_text`; 17, lines 763-768; seen. 80 cards, 55 false on the target's own scale, 73 next to a printed gap of 5 points or more. Griffin, Montgomery, De La Cruz.
2. **[high]** The staff reports contradict the card on where to start. Seen.
   - bottom10_2026_coaching_notes.md, Peña: "the plan leads with the slider away and the early counts", but the card's plan starts with the two-strike fastball.
   - actionable_hitters_2026.md says Neto and Tovar have "no single pattern to drill"; the bottom-10 report says "right-handed slider below the zone, period" and "one rule".
   - The Peraza and Giménez notes, in coach_notes.py and the README, point to a different starting place than the plan.
3. **[high]** Earlier-season targets read as forecasts made in time. Seen.
   - 241 of 280 cards in card_players_2023.json are retrospective with no label; card2023_*.png and the page texts show the same.
4. **[high]** The target number does not follow from the leak list. Seen.
   - Its value lies outside the printed gaps on 46 of 149 cards (Kirk, Winn, Langford).
   - It pools a leak that is not on the plan on 105 cards.
   - It sets a number on video-only leaks on 9 cards (Loftin, Guerrero, Kirk).
5. **[medium]** The "biggest pieces… start with the first" framing line is false on 7 of 7 cards. 17, `spread_line`; seen. Diaz, Clement, Moniak.
6. **[medium]** "Your fastball decisions are a strength" appears with a fastball plan line on 58 cards. 17, `keep_line`; seen. Mead, Meckler, Loftin.
7. **[medium]** The contact line adds a rule and the closing line says there are no other changes (41 cards). On 34 of 43 contact-line cards the hitter already chases less than the league with two strikes. 17, `contact_line`; seen. Montgomery, Gorman, Duran.
8. **[medium]** The coach's notes narrow or widen the plan:
   - "One pitch" on a two-line plan: Caballero, Harris.
   - A hand the plan line lacks: Neto, Martínez.
   - "Above the belt": Caballero.
   - Changes that are not on the plan: García, Peraza, Peña.
   - coach_notes.py; seen.
9. **[medium]** Undeclared baselines, and one wrong declaration. The roster's note says Choices is measured "against an average hitter at the same spot, count and matchup"; leak_rules.add_choices_contact uses count × distance bucket. 21 footer note; seen.
10. **[medium]** The header far-off cost is under half the runs of the leaks the plan calls 4+ inches off on 68 cards. Seen. Trout, Gorman, Aranda.
11. **[medium]** The two staff reports are hand-written and not regenerated or checked. 12 and 13 write CSVs only; seen. One internal contradiction: Caballero's "single worst cell" (−4.9) against Harris's −5.0 in the same report.
12. **[medium]** The stated order rule is broken by the forced starts on 3 cards (Rafaela, Albies, Duran). Seen. Inferred, not checkable here: the pitcher-hand tabs ignore the note's start (17, line 808), so a noted hitter's vs-RHP plan could lead elsewhere.
13. **[low]** Plan numbers shown out of order on 74 cards. Seen.
14. **[low]** Roster and card print different values for 41 hitters (double rounding through the CSV). team_view_2026.csv; seen. Caballero −13.5/−13.4, Moniak −18.5/−18.6, Martínez −3.9/−4.0.
15. **[low]** The roster start line quotes near-identical rates on 14 hitters. Seen. Mead, Perdomo, Bleday.
16. **[low]** Wording problems. Seen.
    - Neto's note says "well above league" for a 5-point gap.
    - The README calls Montgomery's problem "contact as much as choice" when contact is 3.6 times choices.
    - xChase+ is not explained on the card ("100, 157th").
    - Footer: "the gain was mostly runs not lost" is unclear to a player.
17. **[low]** On the interactive page the target is a gray caption under the leak list. player_cards_template.html, line 819; seen.
18. **[waiting]** The three-ball group's absence shows: the García and Peraza notes make three-ball counts the first or biggest fix, with no plan line for it.

## 5. Top 3 changes
1. **Rewrite the target in one generator for all surfaces.**
   - Name the leak numbers it covers, and show it against the plan's baseline or print both.
   - Say "next season, with no change, about at the league's rate", not "already".
   - On retrospective cards, state that it is retrospective, give the freeze date and the scored result, or drop the target.
2. **Derive every summary line from the items it introduces, and add a check over all 261 plans like coach_notes.check.**
   - The framing line names its pieces only when they are the costliest.
   - The fastball clause only when no fastball line is on the plan.
   - The contact line reconciled with "the only changes".
   - The roster's start line carries "about as often" when that is how the card words it.
3. **Make the staff reports follow the card.**
   - Generate or check each hitter's paragraph from the card data: the plan's first line, the card's rates, one named baseline.
   - Fix Peña, Neto/Tovar, Peraza and Giménez now.
   - Publish one glossary: one name per number, one definition of "the league".

## 6. Would use
- **No, for players today. Yes, for staff, with conditions.**
- **Staff, from now (offseason):** as an internal worksheet for the 17 noted hitters, after the Peña, Neto, Peraza and Giménez conflicts and the no-target sentence are fixed.
- **Players, from spring training 2027, before the first 2027 pitch so the frozen target stays honest:** as the printed one-page plan handed over in a coach meeting, not as a self-serve page. This depends on the summary-line check running clean on all 261.
- **Earlier-season cards:** not under my name while their targets are unlabelled.
- **What would stop me:**
  - A player or agent seeing "already about at the league's rate" next to "57% vs 25%".
  - A coach reading a staff report that starts him somewhere other than the card.
  - Under the one-card rule, every coach's note is read by the player, so absolutes like "he cannot afford to chase at all" have to be fit for the player to see.
