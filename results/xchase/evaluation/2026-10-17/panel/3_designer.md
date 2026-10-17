# Reviewer 3: the information designer (raw)

Packet: screenshots of the card at 375 px and 1440 px, light and dark, the opened 3D view, the roster page, print pages 1 and 2 and the static PNG, for Caballero, Martínez, Neto and Montgomery, from the committed build 53dc8a5 (all in ../screenshots/). Brief: panel/briefs.md. Report as returned, unedited. The reviewer disclosed writing and deleting two crop images in a scratchpad folder against the no-write rule; nothing in the project was touched.

---

Reviewer 3 of 4, the information designer. I worked the 4 hitters in my packet (José Caballero, Angel Martínez, Zach Neto, Colson Montgomery) plus the roster screenshots. The other 8 sample hitters were not in my packet. One process note: early on I made two crop images in a new scratchpad subfolder. That broke the no-write rule, so I deleted them straight away, and the whole review below comes from the full packet images only.

## 1. Verdict
The plan lines are good coaching copy. Each opens with one concrete cue ("With two strikes, let fastballs above the zone go") and comes with a "keep swinging at strikes" guardrail, and print page 1 lays this out in the right order. Around that copy, the system says different things in different places: the coach's note and the plan use different words on all 4 cards, Montgomery's card contradicts itself, and the print and web cards put leaks on different pictures. The phone card, which is where a player will open his link, overflows the screen, opens with a full screen of filters, and puts the pictures two screens below the words that point to them.

## 2. Scores
- **Clarity: 3.** The plan sentences are plain and lead with the cue. Too many run figures compete around them (hero cost, choices, leak runs, target "points"), and xChase+ and "points" are never explained.
- **Actionability: 3.** Each line is a single take cue with a count, a pitch and a distance. The plan/note mismatches and Montgomery's mixed, out-of-order plan undercut that.
- **Consistency: 2.** Web, print and PNG differ in legend wording, where the target sits, whether the coach's note appears, which picture carries a marker, and for Martínez the pictures themselves. The roster renames the hero number.
- **Visual design: 3.** Restrained palette, good type and a well-ordered print page 1. Against that: phone overflow and reading order, a dark-mode scale whose "gray" is black, and a text collision on one print page.
- **Coaching value: 3.** The cues and the guardrail are right and the numbered markers link pictures to leaks. The pictures are small and blurred, and the 3D view adds little.
- **Trust: 3.** A sharp coach will catch the self-contradicting Montgomery card, the leak markers that move between print and web, and two values that differ between the roster and the card.

## 3. Strengths
- Plan lines put the instruction first and the evidence after it, in player language: count, hand, pitch group, "let it go", and how far off his swings were. "Keep swinging at strikes. The only changes on this card are the pitches above." appears on every card.
- Print page 1 has the best order of the three formats. Name, plan, target, then four large all-pitchers pictures with numbered markers, then the leaks with matching numbers (print_jose_caballero_p1.png, print_zach_neto_p1.png).
- One diverging red/blue scale and neutral grays for everything else. Bold "you" against light "avg" reads fast, and numbers are right-aligned.
- The +15 outlines give the blurred maps a hard edge, and the numbered markers tie leaks to spots.
- Orientation is stated in words and with Inside/Away labels, including the switch-hitter rows (card_angel_martinez_desktop_light.png, row labels).
- The roster becomes stacked blocks on phone instead of a squeezed table, and adds a "Start with" line (roster_phone375_light_01.png).
- The desktop web light and dark themes share one layout. Dark mode is complete apart from the color scale.

## 4. Issues

1. **[high] Montgomery's card contradicts itself. Seen.**
   - In card_colson_montgomery_desktop_light.png, "What to work on" (right column, top) reads: an unnumbered bullet, then ②, then ①.
   - The bullet says contact is the bigger issue. Plan ① says he swings at those pitches "about as often as other hitters do".
   - "Target" (right column, middle) says "No chase target here".
   - The coach's note says "with two strikes he cannot afford to chase at all".
   - The hero is a chase cost of 3.1, while "Where the runs go" shows Contact −13.0.
   - The same order and text appear in print_colson_montgomery_p1.png (top) and png_colson_montgomery_light.png (right column, top).
   - The bullet is not one pitch, which breaks the card's own rule "The plan is one pitch per line" (print_colson_montgomery_p2.png, item 4).
   - A player gets four messages here: contact, two takes, no target, and don't chase at all.

2. **[high] The coach's note uses different words from the plan. Seen, 4 of 4.**
   - **Caballero** (card_jose_caballero_desktop_light.png, Coach's note under the plan): "One pitch… the fastball above the belt", against a two-line plan. "Above the belt" includes the upper half of the zone, which the line just above tells him to keep swinging at.
   - **Martínez** (card_angel_martinez_desktop_light.png, Coach's note): "right-hander, soft stuff that starts at the knees". The plan says "breaking balls" and "changeups and splitters" "below the zone" and names no hand.
   - **Neto** (card_zach_neto_desktop_light.png, Coach's note): "Sliders" where the plan says "breaking balls", and it adds "Sit fastball", which is not on the plan.
   - **Montgomery:** see issue 1.
   - If the coach speaks the note and the player reads the plan, he hears two different cues.

3. **[high] Text collides on Montgomery's print page 1. Seen.**
   - At the bottom of print_colson_montgomery_p1.png, the "Does fixing a leak pay?" footnote prints over the season chart's year labels and over the legend line "White: too few pitches to say".
   - The other three print page 1 files are clean (print_jose_caballero_p1.png, print_angel_martinez_p1.png, print_zach_neto_p1.png, bottom).
   - Inferred: the longer three-line plan pushed the page content down, so other long plans may collide the same way.

4. **[high] On phone, the page is wider than the screen. Seen, 4 of 4.**
   - The By count footnote ("Choices: what the swing decisions cost…") runs past the card border and is cut at the screen edge, and the xwOBA column is cut mid-number.
   - Where: card_jose_caballero_phone375_light_03.png bottom, card_angel_martinez_phone375_light_03.png bottom, card_zach_neto_phone375_light_03.png bottom and _04 top, card_colson_montgomery_phone375_light_04.png top. The dark versions match (card_jose_caballero_phone375_dark_03.png).
   - Inferred: because a paragraph overflows, the whole page scrolls sideways.

5. **[high] On phone, the pictures are far from the words that point to them, and the first screen is all controls. Seen, 4 of 4.**
   - The zone grid comes after the plan, leaks, target, table, season chart and "Does fixing a leak pay?".
   - So "Numbered on the pictures" (card_jose_caballero_phone375_light_03.png, middle) points to tiles on card_jose_caballero_phone375_light_04.png, lower half. Martínez, Neto and Montgomery follow the same pattern (_03 points to _04 or _05).
   - On every card_*_phone375_light_01.png, the filters fill the screen. The name starts about three-quarters of the way down, and "What to work on" first appears on _02.

6. **[medium] Print and web put leaks on different pictures. Seen, 3 of 4.**
   - **Neto:** print_zach_neto_p1.png ("Where you chase, all pitchers", Two strikes tile) carries markers 2 and 3. Both are named "vs RHP" leaks. The web places them on the vs RHP row (card_zach_neto_desktop_light.png, vs RHP × Two strikes), following its own rule "on the row of the hand a leak names".
   - **Montgomery:** print_colson_montgomery_p1.png puts both vs-RHP markers on all-pitchers tiles.
   - **Martínez:** print_angel_martinez_p1.png calls the row "all pitchers" and fixes Away/Inside for batting left. The web shows the leaks on the "Batting left" row.
   - **Martínez, the pictures themselves:** the batting-left first-pitch tile has an outline on png_angel_martinez_light.png and on print page 1, but none on the default web card (card_angel_martinez_desktop_light.png, Batting left × First pitch). I can't tell which comparison base each format uses.

7. **[medium] Two run figures with opposite signs sit side by side in every header. Seen, 4 of 4.**
   - The hero "Cost of far-off chases" is positive and sits next to a negative "Where the runs go · all chases" figure:
     - Caballero 11.7 vs −13.5 (card_jose_caballero_desktop_light.png, header)
     - Martínez 12.6 vs −17.8 (card_angel_martinez_desktop_light.png)
     - Neto 10.5 vs −13.1 (card_zach_neto_desktop_light.png)
     - Montgomery 3.1 vs −3.6 and −13.0 (card_colson_montgomery_desktop_light.png)
   - Every other cost on the card is negative.
   - The roster calls the hero figure "Runs at stake" (roster_desktop_light.png, column header).
   - For Montgomery, the hero gives the most weight to his smaller problem.

8. **[medium] Dark mode breaks the color key. Seen.**
   - The scale's midpoint is near black, so "Gray: about average" is wrong, and "too few pitches" background looks the same as "average" (card_jose_caballero_phone375_dark_04.png, legend bar; card_jose_caballero_desktop_dark.png, legend).
   - All 4 dark PNGs say "White: too few pitches to say", though nothing on them is white (png_jose_caballero_dark.png, png_angel_martinez_dark.png and png_zach_neto_dark.png, bottom legend text).
   - The home-plate line under each tile nearly disappears in dark (card_jose_caballero_desktop_dark.png, tiles).

9. **[medium] The target moves between formats, and its unit is undefined. Seen, 4 of 4.**
   - Placement: after Biggest leaks on the web (card_jose_caballero_desktop_light.png, right column middle), directly under the plan in print (print_jose_caballero_p1.png, top), and bottom right next to the season chart on the PNG (png_jose_caballero_light.png).
   - Wording: "chased 24 points above the league… about 14 in 2027. Under 14 is a fix" never says points of what. Martínez (28/16) and Neto (16/7) read the same way.

10. **[medium] The coach's note is on the web card and the PNG but not in print. Seen, 4 of 4.**
   - It is absent from print_jose_caballero_p1.png/_p2.png, print_angel_martinez_p1.png/_p2.png, print_zach_neto_p1.png/_p2.png and print_colson_montgomery_p1.png/_p2.png.
   - With one card per player, the three formats need one rule.
   - On the PNG the note is the smallest text in the image (png_jose_caballero_light.png, right column under the plan).

11. **[medium] On desktop the 12-tile grid leads and the plan comes second. Seen, 4 of 4.**
   - The grid fills the left half and is read first. Below "Zone numbers" the left column runs empty for roughly 400 px while the right column continues (card_jose_caballero_desktop_light.png, card_angel_martinez_desktop_light.png and card_zach_neto_desktop_light.png, left column lower third).
   - The default selected tile and the default 3D picture are "All pitchers, Two strikes". For Montgomery that tile is mostly blue and carries no marker (card_colson_montgomery_desktop_light.png, grid top right; terrain_colson_montgomery_desktop_light.png, caption).
   - The plan's cue has no typographic weight. On phone each plan line is 5 to 7 lines of equal weight (card_angel_martinez_phone375_light_02.png).

12. **[medium] Markers crowd on desktop and shrink to unreadable on phone. Seen.**
   - **Martínez:** markers 2, 1 and 3 touch on one tile (card_angel_martinez_desktop_light.png, Batting left × Two strikes) and can't be read on phone (card_angel_martinez_phone375_light_04.png, middle).
   - **Neto:** 3 and 2 stack on the tile edge (card_zach_neto_desktop_light.png, vs RHP × Two strikes; card_zach_neto_phone375_light_04.png).
   - **Montgomery:** markers are tiny on phone (card_colson_montgomery_phone375_light_04.png, bottom).

13. **[medium] The roster hides its coaching columns on desktop and confuses on phone. Seen.**
   - At 1440 px the table is cut at the right. In roster_desktop_light.png only a leading "u" shows past "Count check". roster_team_NYY_desktop_light.png (right edge) shows "under 14 (wa…", which is the Beat column.
   - The "Start with" column that the footnote describes isn't visible (inferred: it sits further right).
   - On phone, "Top leak" and "Start with" name a different count or pitch in 5 of the 10 blocks I read, with no explanation:
     - Pérez (roster_phone375_light_01.png)
     - Mangum, Clement and Moniak (roster_phone375_light_02.png)
     - Church (roster_phone375_light_03.png)

14. **[medium] xChase+ is never explained. Seen.**
   - The header shows "xChase+ 79, 246th of 261" (card_jose_caballero_desktop_light.png, under the name), and the same line is on every card.
   - Nothing on the web card, and none of the six "How to read your card" items (print_jose_caballero_p2.png), says what it is or which direction is good.

15. **[medium] The roster and the card print different values. Seen.**
   - Caballero's Choices is −13.4 on the roster (roster_desktop_light.png, NYY row; roster_team_NYY_desktop_light.png) and −13.5 on the card (card_jose_caballero_desktop_light.png, header and By count).
   - Martínez's top-leak runs are −4.0 on the roster (roster_desktop_light.png, CLE row) and −3.9 on the card (card_angel_martinez_desktop_light.png, Biggest leaks ①).
   - I didn't check which value is right. It may be rounding or a different comparison base, but a coach moving between the pages will see it.

16. **[low] "How to read" describes a rule the plans don't show. Seen.**
   - print_jose_caballero_p2.png, item 4, says "a take before two strikes comes first". Caballero's plan is two two-strike lines, and his leak ③ "Ahead in the count, fastballs above the zone" is left out (print_jose_caballero_p1.png). Martínez's and Neto's plans are also all two-strike lines.
   - The "video room" mark that item 4 promises appears on none of my four cards. Inferred that the reader never sees one.

17. **[low] A phone column header breaks badly. Seen, 4 of 4.** "0-1 or 1-1" wraps to "0-1 or 1-" over "1" (card_jose_caballero_phone375_light_04.png, card_angel_martinez_phone375_light_04.png, card_zach_neto_phone375_light_04.png, grid headers).

18. **[low] The 3D view has cut and overprinted labels. Seen.**
   - On phone the swing-rate labels are cut at the left and the x-axis title reads "…er's view, ft" (terrain_jose_caballero_phone375_light.png, terrain_angel_martinez_phone375_light.png; 2 of 2).
   - On desktop the lowest swing-rate tick overprints into a "B"-like glyph (terrain_jose_caballero_desktop_light.png, terrain_zach_neto_desktop_light.png, terrain_colson_montgomery_desktop_light.png, left axis; 4 of 4).
   - It has no leak numbers, and it stacks three encodings: height, color and mesh. In dark the blue nearly vanishes (terrain_jose_caballero_desktop_dark.png).
   - It is collapsed by default, so it doesn't compete with the plan, but it doesn't carry it either.

19. **[low] Print page 2's heaviest image is the average hitter. Seen.**
   - The dark ring is the heaviest mass on either page (print_jose_caballero_p2.png, lower left). It looks the same and nearly symmetric for all four hitters (print_angel_martinez_p2.png, print_colson_montgomery_p2.png).
   - Its caption says the average hitter chases most "below and away". That isn't visible in the picture, and "away" is on opposite sides for a left-handed and a right-handed batter. Inferred: it is one generic image.
   - The "How to read" list reuses the leak markers' circled numerals (print_jose_caballero_p2.png, top), so a circled number means two things.

20. **[low] Montgomery's misses row has a second color scale with no bar. Seen.**
   - The purple/green key lives only in the small row label on desktop (card_colson_montgomery_desktop_light.png, "Misses on chases") and is gone on phone (card_colson_montgomery_phone375_light_05.png, top).
   - The row is absent from print (print_colson_montgomery_p1.png), though his plan's first line is about misses.

21. **[low] Legend wording drifts between formats. Seen.**
   - The web says "average" and "Background: too few pitches" (card_jose_caballero_desktop_light.png, legend).
   - Print and PNG say "league" and "White" (print_jose_caballero_p1.png, png_jose_caballero_light.png).
   - The print legend sits beside the season chart, a section away from the pictures it explains (4 of 4 print page 1 files).

22. **[low] PNG layout gaps and a changed header. Seen.**
   - There is a dead band of about 330 px between the grid and the right-hand text (png_colson_montgomery_light.png, middle).
   - That PNG's column header is shortened to "Ahead"; the others say "Ahead in the count" (png_jose_caballero_light.png).

23. **[low] The desktop table runs past its column. Seen, 4 of 4.** The By count "Contact" column ends about 20 px right of everything else and nearly touches the card border (card_jose_caballero_desktop_light.png, card_zach_neto_desktop_light.png and card_colson_montgomery_desktop_light.png, right edge).

24. **[low] Process jargon and roster labels. Seen.**
   - "Built by step 17 of the Chase Leaderboard project" is in every card footer (card_jose_caballero_desktop_light.png, bottom). The roster footnote cites steps 13, 19 and 21 (roster_team_NYY_desktop_light.png, bottom).
   - The roster is titled "by team" but defaults to all teams (roster_desktop_light.png, top).
   - In the phone blocks the team code is the boldest element, and the name jumps between centered (with a "noted" pill) and right-aligned (without): roster_phone375_light_02.png, Clement vs Mangum.
   - The "noted" pill is barely visible in dark (roster_desktop_dark.png).

## 5. Top 3 changes
1. **One message per card, worded the same everywhere.**
   - The coach's note restates plan line 1 in the plan's own words (count, hand, pitch group, above or below the zone) and adds no new cue.
   - Number plan lines 1 to n in the order shown, with the leak number as a small tag.
   - Give contact-first hitters like Montgomery a contact-first header, and no take lines that the target then disowns.
   - Put the note in all three formats or in none.
2. **Rebuild the phone card around the plan.**
   - Put the name and plan on the first screen and fold the filters into one row.
   - Follow each plan line with its single tile, enlarged and marked.
   - Keep the table inside its own scroll box, and fix the overflow, the header wrap and the 3D axes.
   - A bigger option, which touches every page: on all surfaces show only the tiles the plan names and put the 12-tile grid behind a toggle. Print page 1 already shows the shorter layout works.
3. **Make web, print and PNG one system.**
   - Use the same legend words, and fix the dark-mode midpoint and the dark PNG "White".
   - Give the target one fixed place, and say what its points are.
   - Put markers on the row of the hand they name, or label the hand on print, and use the same comparison base for the pictures.
   - Use one name for the hero number on the card and the roster.
   - Add a print overflow check (Montgomery page 1).

## 6. Would use
- **Players, today: no.** Staff can use the desktop card now as a working view.
- **From when:** once issues 1 to 5 are fixed, which is in time for the offseason one-on-ones before 2027 spring training.
- **As what:** print page 1 as the one-page handout in a hitting coach's meeting with the player, the web card as the staff's working view, and the PNG for the write-up only.
- **What would stop me:** a player hearing one cue from the coach's note and reading another on the plan, any card that contradicts itself the way Montgomery's does, or a phone page that looks broken when the player opens his link.
- **Not checked:** I could not test interactions (toggles, tile clicks, hover), and I judged heatmap legibility only from static screenshots.
