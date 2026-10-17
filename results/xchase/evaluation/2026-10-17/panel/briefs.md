# The four reviewers' briefs

Each reviewer was a separate agent, run in parallel without sight of the others, of my own read or of the 2026-10-16 review, and told to read only its own packet folder (copies of the files named below, taken from the committed build 53dc8a5). Every brief opened with the shared text below, then its lens.

### What this is

A baseball analytics project builds a "decision card" for every qualified MLB hitter of the 2026 season (261 hitters): where the hitter swings at pitches outside the strike zone more than other hitters do, what it costs in runs, and a short plan written to the player. Seventeen hitters are "noted": their cards also carry a coach's note for the staff, a printable two-page PDF and a write-up, and they are discussed in two staff reports. A roster page lists every hitter side by side. Today is 2026-10-17: the 2026 season is over and 2027 has not started.

You are one of four independent reviewers. You review the documents as coaching instruments: structure, wording, consistency, visual design and helpfulness, and how likely each document is to get a hitter to change what he does. Every number is already checked by code; do not re-verify figures against data. You may and should say when two documents, or two parts of one document, say different things.

### Rules

- Read only the files in your packet folder. Do not open any other path on this machine: not the project repository, not anything under ~/.claude, not other folders in the scratchpad, and no web or browser access. If something you need is not in the packet, say so as a finding; do not go looking for it.
- Do not write or change any file. Return your review as your final message.
- These constraints stand and are not to be recommended against: one card per player, with no separate staff copy; a fix is one pitch; a three-ball count group on the card and an in-season readout are planned but wait until after the 2027 season is scored. You may point out where their absence shows, as long as you label it as waiting.
- Mark every issue "seen" (you saw it in a named file at a named place) or "inferred" (you are reasoning beyond what you saw). For a pattern, give the count you observed and three named examples. Never state a count you did not make; say "in N of the M I read".

### The sample

Every reviewer works the same 12 hitters (2026 cards), plus any others you choose; name the others you used.

1. José Caballero (noted, "easiest to improve")
2. Angel Martínez (noted, "easiest to improve")
3. Zach Neto (noted, "biggest losses")
4. Colson Montgomery (noted, "biggest losses")
5. Curtis Mead
6. Samuel Basallo
7. Wade Meckler
8. Konnor Griffin
9. Nolan Gorman
10. Miguel Vargas
11. Nick Loftin
12. Yainer Diaz

### Standard output, in this order

1. **Verdict**: exactly 3 sentences.
2. **Scores**, 1 to 5, each with a one-line reason: clarity, actionability, consistency, visual design, coaching value, trust.
3. **Strengths**.
4. **Issues**, numbered, each tagged [high|medium|low], each with the exact artifact (file name) and location (section, line, or element), marked "seen" or "inferred", and for a pattern the count and three named examples.
5. **Top 3 changes**.
6. **Would use**: yes or no, from when, as what, and what would stop you.

## Lens 1: the player reading alone

Packet: print_<hitter>_p1.png, card_<hitter>_desktop_light.png and card_<hitter>_page_text.txt for the 12. "You are a major-league hitter. Your hitting coach has handed you your card and walked away. ... No code, no reports, no roster, no one to ask. You know baseball deeply; you do not know statistics jargon unless the card explains it." Before any scoring, for each of the 12, exactly two sentences: "What I am being told to do first: ..." and "What I do not understand: ...", not softened; say so if the card or the print page and web card give two different first actions. Then the standard output, "Would use" answered as the player.

## Lens 2: the hitting coach

Packet: the 12 cards (desktop screenshot, page text, print pages 1 and 2), the noted README with the 17 card PNGs, both staff reports, the roster (two screenshots and its full text), leak_pitches_2026.csv; no code. Choose 6 of the 12 including the four noted; for each, what you would say in the meeting (at most four sentences), what you would pull on video, and every place two documents disagreed or made that harder, quoting both. Then the standard output, "Would use" answered as a staff.

## Lens 3: the information designer

Packet: for Caballero, Martínez, Neto and Montgomery, the card at 1440 px light and dark, at 375 px light and dark in screen-height segments (2x), the opened 3D view, print pages 1 and 2 and the static PNG light and dark; the roster at 1440 and 375, light and dark, and filtered to one team. Every issue cites a screenshot file by name and place; claim only what is visible. Then the standard output.

## Lens 4: the front-office analyst

Packet: the generators (17, 21, coach_notes, the template, leak_rules, card_site, 12, 13, 15, 16, 19, 20), card_players_2026.json and the 2026, 2023 and roster CSVs, the README, both reports, the 12 cards' page text, the roster text, three 2023 cards. Tasks: (A) over all 261 plans, sentences that do not follow from the numbers beside them or contradict another sentence on the card, classified and counted with three examples each; (B) for 5 of the 12, every sentence about the hitter from every document side by side, with vocabulary and baseline differences; (C) the 2023 target sentence read by someone who does not know how it was made, then what it actually is from the code. Then the standard output.
