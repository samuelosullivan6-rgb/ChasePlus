"""
A check of every card's plan against the lines and numbers beside it
(step 17), the way coach_notes.check checks the coach's notes.

The plan's sentences are generated, but a sentence written for one case
can land on a card where the numbers next to it say the opposite: the
2026-10-17 evaluation found 111 of 229 plans whose first printed line
was not the first thing to do, and 137 where a sentence beside the plan
undercut it ("you are already about at the league's rate" under a line
quoting 71% against 43%). Each kind below is one of those patterns,
tested on the card's own data: the plan items, the leaks, the count
table, the header numbers and the target. Step 17 runs it on every
card and stops listing what failed.

A card has one plan. The 2026-10-18 audit found that pitcher-hand tabs
which rebuilt their own plans from one hand's pitches gave the opposite
instruction on the same pitch (22 cards), dropped the line the plan
named for that hand (52) and said "on this card" about a different plan
(143). The tabs now show the plan unchanged with each pitch line's
pitches from that hand under it, so the checks below also make sure no
second plan comes back, the hand notes add up to the line's leak, and a
leak on a hand tab carries the card's number for the same pitch.

The same audit found the plan picking the wrong first pitch and leaving
things out with no word: 39 first lines on fewer than 20 pitches, 14 on
a pitch chased at the league's rate, 54 cards leaving a bigger leak out
and 86 a costly count, under "the only changes on this card". It found
the no-target sentence saying "below the league" under leaks printed
above it (8 cards), and a hand label that counted who threw the pitches,
not where the extra chasing was. Those have kinds too, checked on the
outcome a reader sees rather than by running step 17's rules again.

The second round of fixes from that audit added kinds for what was left:
a sentence and the row beside it rounding the same number apart, a take
on a small sample with no word of it, video wording off the card's 4-inch
rule, the plus-count reason missing on a second line, a contact sentence
that misstates the miss rates or speaks for a hitter whose loss is not
contact, a "Nothing to change" line quoting the season's contact instead
of its counts', a loss called "about average", an ASCII minus, and a
number to beat on a different scale from the rows with no word of it.

A review of Jake Mangum's 2026 card (2026-10-20) found a take line in a
count where his chases pay for themselves: with two strikes his choices
cost −9.2 runs and what he hit on those chases +11.3, and the plan said
"let fastballs above the zone go" with no word of it. 34 of 261 cards
had a line like that. Such a line now says the count pays and what the
pitch itself gets back of its cost (it never pays: the leak rule leaves
out a pitch whose contact covers its choices), and a kind checks it.
The same day it was extended to counts costing under a run: J. T.
Realmuto's 2026 two-strike choices print −0.8 against contact +5.1, and
95 lines over six seasons (16 in 2026) were in a count like that with no
word of it. Any count whose choices print as a loss now counts.

Run on a built page it counts each kind without stopping, which is how
the before and after counts were taken:

    python scripts/plan_checks.py results/xchase/player_cards/2026/index.html
"""

import json
import math
import re
import sys

CLEARLY_OFF_IN = 4              # step 17's CLEARLY_OFF_IN: under it a leak is a video item
COUNT_PHRASES = {"first": "on the first pitch", "ahead": "when you're ahead in the count",
                 "even": "at 0-1 or 1-1", "two": "with two strikes"}
# Step 17's rules, which step 17 checks are the same here
RULES = {
    "RATE_GAP_MIN_PTS": 5,          # under this printed gap a leak is at the league's rate
    "PLAN_LEAD_MIN_PITCHES": 20,    # a take before two strikes goes first only on this many
    "NEXT_MIN_RATIO": 1.25,         # a leak left off that costs this many times a plan line is named
    "COSTLY_COUNT_RUNS": 1.0,       # a count costing this much is named
    "TARGET_MIN_PTS": 2,            # the no-target forecast band
    "HAND_CARRY_SHARE": 0.5,        # a named hand carries more than this of the extra chases and cost
    "PLUS_COUNT_MIN_RUNS": 1.0,     # a count at or over this is "a plus overall", under it "about even"
    "CONTACT_LED_RUNS": 3.0,        # contact is the card's subject from this loss up
    "WHIFF_GAP_MIN_PTS": 5,         # the miss rates print this far apart to be "more" or "less"
    "TARGET_SCALE_NOTE_PTS": 3,     # a number to beat this far from the rows' gap says so
}

KINDS = {
    # The first printed line is the first thing to do (finding 1)
    "contact first": "a plan with a take line opens with the contact line",
    "frame first": "a plan with a take line opens with a framing line",
    "numbers backwards": "a higher number prints above a lower one in the plan",
    "numbers skip": "the plan's numbers are not 1, 2 down the page",
    "video only, nobody named": "a plan of video items only does not say the staff takes it",
    "biggest, but not": "a framing line calls the plan's pitches the biggest pieces, and they are not",
    # The card does not argue with its plan (finding 2)
    "no target says already": "the no-target sentence says 'already' (it is about next season's forecast)",
    "fastball strength over a fastball line": "the closing line calls fastball decisions a strength "
                                              "under a fastball plan line",
    "fastball strength beside a fastball leak": "the closing line calls fastball decisions a strength "
                                                "on a card that lists a fastball leak, on any tab",
    "header 0.0 unexplained": "the header's far-off cost prints 0.0 over a plan of pitch lines "
                              "and nothing says why",
    "good chooser unframed": "a hitter whose choices are better than average gets pitch lines "
                             "and nothing says so",
    "plus count, no why": "a pitch line in a count the table shows as a plus, with no line above it in "
                          "that count, does not say why",
    # Sentences that quote a number must quote the one beside them
    "rates misquoted": "a pitch line's two rates are not its leak's",
    "inches misquoted": "a take line's inches off the zone are not its leak's",
    "framing misquoted": "a framing line's runs or level are not the hitter's",
    "plus count misquoted": "a plus-count sentence's runs are not the count table's, or it calls a count "
                            "under a run 'a plus overall' (or one over it 'about even')",
    "keep line miscounts": "the closing line's 'pitch above' / 'pitches above' is not the plan's",
    # The target can be read and tracked (evaluation item 4)
    "target without unit or leaks": "the target sentence does not say it is points above the league's "
                                    "chase rate, or which leaks it covers",
    "retrospective target as a forecast": "a target set after the season reads as a forecast, or does "
                                          "not say how the next season came out",
    "number on a video-only card": "a card whose every leak is a video item prints a number to beat",
    "target result misquoted": "the next season's number on a retrospective card is not step 20's",
    # Labels a staff can trust (evaluation items 5 and 7)
    "start line quotes near-identical rates": "the roster's start line quotes two rates under 5 points apart",
    "hand overstated": "a line or leak name gives one pitcher hand for pitches the other hand threw too",
    # One plan on every tab (the 2026-10-18 audit)
    "two plans": "the card carries a separate plan for a pitcher-hand tab",
    "hand note does not add up": "a plan line's pitches from right- and left-handers are not its leak's",
    "hand leak misnumbered": "a leak on a pitcher-hand tab does not carry the card's number for the same "
                             "pitch, or carries one the card does not list",
    # The target agrees with the rows above it (the 2026-10-18 audit, issues 6, 12, 13)
    "no target off the card's rows": "the no-target sentence's points are not what the card's own leak rows "
                                     "add up to (it said 'below the league' under leaks printed above it)",
    "no target 'about at' a forecast below": "the no-target sentence says 'about at' the league for a "
                                             "forecast more than 2 points under it, or 'at or under' for "
                                             "one that is not",
    # Which pitch leads, and what the plan leaves out (issues 10, 11, 16, 17)
    "small take leads": "the first line is a take before two strikes on under 20 pitches, put ahead of a "
                        "costlier take only by the take-first order",
    "league rate ahead of a real gap": "a take chased at about the league's rate is ahead of, or keeps off "
                                       "the plan, a take chased well above it",
    "bigger leak left out unnamed": "a leak off the plan costs 1.25 times a plan line or more, on 20+ "
                                    "pitches, and no line names it",
    "costly count unaddressed": "a count costing 1 run or more has no pitch line and no sentence names it",
    "only changes, with more left": "the closing line says 'the only change(s)' while a leak or a costly "
                                    "count is left for later",
    # The hand and side a leak is drawn and named for (issues 2, 21)
    "hand named without its extra chases": "a leak is named for a pitcher hand that does not carry most of "
                                           "its extra chases and cost",
    "switch leak on the quieter side": "a switch hitter's leak is drawn on the side with less of its extra "
                                       "chases",
    # The rest of the audit (issues 10, 12, 18, 24, 27, 28, 33, 38, 39)
    "small sample unflagged": "a take line rests on fewer than 20 pitches and does not say so",
    "video item off the 4-inch rule": "a video line does not give the card's own reason, under 4 inches off",
    "contact miss rate misstated": "a contact sentence's miss rates are not the hitter's, or 'more', 'less' or "
                                   "'about as often' does not fit them as printed",
    "contact sentence off the contact flag": "a contact sentence on a card whose contact loss is not its "
                                             "subject, or none on one whose is",
    "nothing to change misquoted": "a 'Nothing to change' line quotes runs its counts' chases did not produce, "
                                   "or a count whose chases did not pay",
    "loss called average": "a fallback calls a choices loss of a run or more 'about average'",
    "ascii minus": "a sentence prints a negative number with a hyphen, where the page's tables use a minus sign",
    "target scale or unit unsaid": "a number to beat several points from what the leak rows add up to does "
                                   "not say it is on another league rate, or its forecast has no unit",
    # A count whose chases pay for themselves (the 2026-10-20 review of Mangum's card)
    "paying count unsaid": "a pitch line in a count whose choices print as a loss, where the count table's "
                           "contact covers them, does not say so with the table's runs and what the pitch "
                           "gets back of its own, or a line says it of a count that does not pay",
    "take on a pitch that pays": "a pitch line's own chases produce at least what its choices cost",
}


def fmt_runs(v):
    v = shown(v)
    return "0.0" if v == 0 else ("+" if v > 0 else "−") + f"{abs(v):.1f}"


def stored(v):
    """A value as the built page stores it, four decimals (step 17's
    to_json_safe): the page prints run values from this."""

    return round(float(v), 4)


def page_whole(v, scale=1):
    """How the page prints v * scale as a whole number: JavaScript's
    Math.round (half up) on the stored value."""

    return math.floor(stored(v) * scale + 0.5)


def shown(v):
    """A run value to one decimal, as the page's runs() prints it."""

    return page_whole(v, 10) / 10


def whole_runs(v):
    return math.floor(abs(shown(v)) + 0.5)


def printed(v, scale=1):
    """How v prints as a whole number, as a one-element set: step 17 rounds
    every quoted number the way the page does, so a sentence and its row
    agree exactly."""

    return {page_whole(v, scale)}


def is_video(it):
    return it.get("video", "video room" in it["text"])


def printed_number(it):
    """The number a pitch line prints in front of it: its step in the
    order to work on them (before 2026-10-17, its leak's number)."""

    return it.get("step", it["n"])


def plan_problems(items, leaks, rows, player):
    """(kind, detail) for one plan: the items, the leaks they are
    numbered to, the count table rows by group, and the hitter's summary."""

    out = []
    pitches = [it for it in items if it["kind"] == "pitch"]
    takes = [it for it in pitches if not is_video(it)]
    texts = " ".join(it["text"] for it in items)
    if not pitches:
        return out
    first = items[0]
    if takes and first["kind"] == "contact":
        out.append(("contact first", first["text"][:60]))
    if takes and first["kind"] == "frame":
        out.append(("frame first", first["text"][:60]))
    numbers = [printed_number(it) for it in pitches]
    if numbers != sorted(numbers):
        out.append(("numbers backwards", " then ".join(map(str, numbers))))
    elif numbers != list(range(1, len(pitches) + 1)):
        out.append(("numbers skip", " then ".join(map(str, numbers))))
    if not takes and "the staff takes" not in texts:
        out.append(("video only, nobody named", pitches[0]["text"][:60]))
    leak_n = sorted(it["n"] for it in pitches)
    biggest = leak_n == list(range(1, len(pitches) + 1))
    for it in items:
        if it["kind"] == "frame" and "biggest single piece" in it["text"] and not biggest:
            out.append(("biggest, but not", f"leaks {leak_n}"))
    fastball_line = any(tuple(it["cell"])[1] == "fastball" for it in pitches)
    keep = next((it for it in items if it["kind"] == "keep"), None)
    if keep and fastball_line and "fastball decisions are a strength" in keep["text"]:
        out.append(("fastball strength over a fastball line", keep["text"][:60]))
    elif (keep and "fastball decisions are a strength" in keep["text"]
          and any(lk["pitch_group"] == "fastball" for view in player["leaks"].values() for lk in view)):
        out.append(("fastball strength beside a fastball leak", keep["text"][:60]))
    if keep:
        says_one = "the pitch above" in keep["text"].lower()
        if says_one != (len(pitches) == 1):
            out.append(("keep line miscounts", f"{len(pitches)} pitch lines"))

    # framing: a good chooser, and the header's 0.0
    c = stored(player["choices"])
    frames = [it["text"] for it in items if it["kind"] == "frame" and it["text"].startswith("Overall your")]
    if c > 0 and not any(("better than average" in f or "about average" in f) for f in frames):
        out.append(("good chooser unframed", f"choices {fmt_runs(c)}"))
    for f in frames:
        if c <= -1:
            ok = f"cost you {whole_runs(-c)} run" in f
        else:
            level = "better than average" if c >= 1 else "about average"
            ok = f"are {level} ({fmt_runs(c)} runs a season)" in f
        if not ok:
            out.append(("framing misquoted", f"choices {fmt_runs(c)}: {f[:70]}"))
    zero = shown(player["runs_at_stake"]) == 0
    if zero and "nothing net" not in texts:
        out.append(("header 0.0 unexplained", f"{len(pitches)} pitch lines"))
    if "nothing net" in texts and not zero:
        out.append(("framing misquoted", f"far-off cost {player['runs_at_stake']:.1f}, not 0.0"))

    # every line in a count the table calls a plus says why, once a count
    explained = set()
    for it in pitches:
        g = tuple(it["cell"])[0]
        v = shown(rows[g]["choices"])
        m = re.search(r"In this count your choices (are a plus overall|come out about even) \(([^ ]+) runs",
                      it["text"])
        if v > 0 and g not in explained and not m:
            out.append(("plus count, no why", f"{g} {fmt_runs(v)}"))
        if m:
            want = "are a plus overall" if v >= RULES["PLUS_COUNT_MIN_RUNS"] else "come out about even"
            if m.group(1) != want or m.group(2) != fmt_runs(v) or g in explained:
                out.append(("plus count misquoted", f"{m.group(1)} {m.group(2)} vs {fmt_runs(v)}"))
            explained.add(g)

    # numbers quoted in the pitch lines
    for it in pitches:
        lk = leaks[it["n"] - 1]
        if lk["hand"]:
            share = lk["share_rhp"] if lk["hand"] == "R" else 1 - lk["share_rhp"]
            opener = re.split(r", let | are one", it["text"])[0]
            if share < 1 and "mostly" not in opener:
                out.append(("hand overstated", opener))
        if tuple(it["cell"]) != (lk["count_group"], lk["pitch_group"], lk["region"]):
            out.append(("rates misquoted", f"line {it['n']} is not its leak's cell"))
            continue
        m = re.search(r"You swung at (\d+)% of them; hitters on average swing at (\d+)%", it["text"])
        if m and not (int(m.group(1)) in printed(lk["rate"], 100)
                      and int(m.group(2)) in printed(lk["league"], 100)):
            out.append(("rates misquoted", m.group(0)))
        m = re.search(r"typically (\d+) inches off the zone", it["text"])
        if m and int(m.group(1)) not in printed(lk["depth_in"]):
            out.append(("inches misquoted", m.group(0)))
        if is_video(it) != (lk["depth_in"] < CLEARLY_OFF_IN):
            out.append(("inches misquoted", "take or video item against its depth"))
        if is_video(it) and f"typically under {CLEARLY_OFF_IN} inches off the zone" not in it["text"]:
            out.append(("video item off the 4-inch rule", it["text"][:60]))
        if (not is_video(it) and lk["pitches"] < RULES["PLAN_LEAD_MIN_PITCHES"]
                and f"Only {lk['pitches']} of these pitches so far" not in it["text"]):
            out.append(("small sample unflagged", f"{lk['pitches']} pitches: {lk['phrase']}"))
    return out


def sentence_problems(items, rows, player):
    """Sentences on any plan, with pitch lines or not: the contact sentence,
    the 'Nothing to change' line, the fallback's level, and how a negative
    number prints."""

    out = []
    texts = " ".join(it["text"] for it in items)
    # the contact sentence fits the miss rates as they print, and only a contact card has one
    mine, theirs = page_whole(player["whiff"], 100), page_whole(player["whiff_league"], 100)
    more = re.search(r"you miss on (\d+)% of your chases, against (\d+)%", texts)
    less = re.search(r"you miss less often than other hitters \((\d+)% of your chases against (\d+)%\)", texts)
    same = "you miss about as often as other hitters" in texts
    gap, wide = mine - theirs, RULES["WHIFF_GAP_MIN_PTS"]
    if ((more and (gap < wide or (int(more.group(1)), int(more.group(2))) != (mine, theirs)))
            or (less and (-gap < wide or (int(less.group(1)), int(less.group(2))) != (mine, theirs)))
            or (same and abs(gap) >= wide)):
        out.append(("contact miss rate misstated", f"{mine}% vs {theirs}%"))
    says_contact = "contact is your bigger cost" in texts or "issue is contact" in texts
    if says_contact != bool(player.get("contact_led")):
        out.append(("contact sentence off the contact flag", f"contact {fmt_runs(player['contact'])}, "
                                                            f"choices {fmt_runs(player['choices'])}"))
    for it in items:
        text = it["text"]
        if text.startswith("Nothing to change."):
            named = [g for g, phrase in COUNT_PHRASES.items() if phrase in text]
            m = re.search(r"those swings have paid: (\d+) runs? more", text)
            paid = sum(rows[g]["contact"] for g in named)
            if (not m or int(m.group(1)) != whole_runs(paid)
                    or any(stored(rows[g]["contact"]) < -stored(rows[g]["choices"]) for g in named)):
                out.append(("nothing to change misquoted", text[:70]))
        m = re.search(r"about average overall \(([^ ]+) runs", text)
        if m and shown(rows["total"]["choices"]) <= -RULES["COSTLY_COUNT_RUNS"]:
            out.append(("loss called average", m.group(0)))
    for text in [it["text"] for it in items] + [player.get("target_text") or "", player.get("coach_note") or ""]:
        if re.search(r"[(\s]-\d", text):
            out.append(("ascii minus", re.search(r"[(\s]-\d[^ ]*", text).group(0)))
    return out


def rate_gaps(lk):
    """The gap between a leak's two rates as its row prints them: on a
    built page a rate that sits on a half point can print either way
    (printed), so both are kept."""

    return {r - lg for r in printed(lk["rate"], 100) for lg in printed(lk["league"], 100)}


def leak_video(lk):
    return lk["depth_in"] < CLEARLY_OFF_IN


def at_league_rate(lk):
    """Surely under step 17's gap for quoting two rates."""

    return max(rate_gaps(lk)) < RULES["RATE_GAP_MIN_PTS"]


def real_gap(lk):
    """Surely at or over it."""

    return min(rate_gaps(lk)) >= RULES["RATE_GAP_MIN_PTS"]


def order_problems(items, leaks, rows, player):
    """Which leaks lead and which the plan leaves for later. Tested on
    the outcome, not by running step 17's sort again: a small early take
    ahead of a costlier take it is otherwise level with, a league-rate take
    ahead of a real gap, a bigger leak left off with no line naming it, a
    costly count with no line or sentence, and a closing line that calls
    the plan the only changes while any of this is left. The note's lead
    is exempt from the order: the staff chose it."""

    out = []
    pitches = [it for it in items if it["kind"] == "pitch"]
    if not pitches:
        return out
    start = tuple(player["note_start"]) if player.get("note_start") else None
    cell = lambda lk: (lk["count_group"], lk["pitch_group"], lk["region"])
    on = [it["n"] for it in pitches]
    plan = [leaks[n - 1] for n in on]
    off = [(n, lk) for n, lk in enumerate(leaks, start=1) if n not in on]
    words = " ".join(it["text"] for it in items if it["kind"] != "pitch")

    first = plan[0]
    if (not leak_video(first) and first["count_group"] != "two"
            and first["pitches"] < RULES["PLAN_LEAD_MIN_PITCHES"] and cell(first) != start
            and any(not leak_video(lk) and (real_gap(lk) or at_league_rate(first))
                    and lk["choices"] < first["choices"] for lk in leaks if lk is not first)):
        out.append(("small take leads", f"{first['pitches']} pitches: {first['phrase']}"))

    takes = [lk for lk in plan if not leak_video(lk)]
    for i, lk in enumerate(takes):
        later = takes[i + 1:] + [o for _, o in off if not leak_video(o)]
        if (at_league_rate(lk) and cell(lk) != start
                and any(real_gap(o) for o in later)):
            out.append(("league rate ahead of a real gap", f"{max(rate_gaps(lk))} pts: {lk['phrase']}"))
            break

    for n, lk in off:
        if (lk["pitches"] >= RULES["PLAN_LEAD_MIN_PITCHES"]
                and any(-lk["choices"] >= RULES["NEXT_MIN_RATIO"] * -c["choices"] for c in plan)
                and f"Leak {n} (" not in words):
            out.append(("bigger leak left out unnamed", f"leak {n}, {lk['choices']:.1f}: {lk['phrase']}"))

    named = {leaks[int(n) - 1]["count_group"] for n in re.findall(r"Leak (\d) \(", words)}
    lines = {lk["count_group"] for lk in plan}
    left = []
    for g, phrase in COUNT_PHRASES.items():
        if rows[g]["choices"] <= -RULES["COSTLY_COUNT_RUNS"] and g not in lines:
            left.append(g)
            if g not in named and phrase not in words.lower() and "across every count" not in words:
                out.append(("costly count unaddressed", f"{g} {fmt_runs(rows[g]['choices'])}"))
    keep = next((it for it in items if it["kind"] == "keep"), None)
    if keep and "The only change" in keep["text"] and (off or left):
        out.append(("only changes, with more left", f"{len(off)} leaks off, counts {left}"))
    return out


def count_pays(row):
    """The count table's contact in this count covers its choices: what
    the hitter hit on his chases there paid for his decisions to chase."""

    return row["contact"] > 0 and stored(row["contact"]) >= -stored(row["choices"])


def gets_back_holds(text, lk):
    """The pitch half of a paying-count sentence quotes the leak's cost as
    its row prints it (whole, or to one decimal) and its contact rounded the
    same way, and never says the pitch gets back all of it. Read from the
    words, whichever form they take, not by running step 17's choice of
    form again."""

    cost, back = abs(shown(lk["choices"])), shown(lk["contact"])
    m = re.search(r"you get back about (\d+) of the (\d+) runs it costs", text)
    if m:
        return (int(m.group(1)), int(m.group(2))) == (whole_runs(lk["contact"]), whole_runs(lk["choices"])) \
            and back > 0 and int(m.group(1)) < int(m.group(2))
    m = re.search(r"you get back (\d+\.\d) of the (\d+\.\d) runs it costs", text)
    if m:
        return (float(m.group(1)), float(m.group(2))) == (back, cost) and 0 < back < cost
    m = re.search(r"you get back nearly all of the (\d+\.\d) runs it costs, but not all", text)
    if m:
        return float(m.group(1)) == cost and back >= cost
    m = re.search(r"it costs about (\d+) runs?, and what you hit on these chases (gets none of it back|"
                  r"loses about (\d+) more|loses a little more)", text)
    if m:
        if int(m.group(1)) != whole_runs(lk["choices"]):
            return False
        if m.group(2) == "gets none of it back":
            return back == 0
        if m.group(3):
            return back < 0 and int(m.group(3)) == whole_runs(lk["contact"]) > 0
        return back < 0 and whole_runs(lk["contact"]) == 0
    return False


def paying_problems(items, leaks, rows):
    """A pitch line in a count whose choices print as a loss and whose
    chases pay for themselves says so: the first line in the count with
    the count table's two numbers, and every line in it with what its own
    pitch gets back of what it costs. Jake Mangum's 2026 card told him to
    take two-strike fastballs above the zone with no word that his
    two-strike chases pay (+11.3 against −9.2), the first thing a staff
    that knows him would object to; J. T. Realmuto's said nothing of his
    two-strike +5.1 because the choices beside it cost under a run
    (−0.8). A line in a count that does not pay, or whose choices print
    0.0 or a plus, says none of it, and no line is on a pitch whose own
    chases pay for themselves."""

    out = []
    said = set()
    for it in (it for it in items if it["kind"] == "pitch"):
        g, lk, text = tuple(it["cell"])[0], leaks[it["n"] - 1], it["text"]
        row = rows[g]
        if stored(lk["contact"]) >= -stored(lk["choices"]):
            out.append(("take on a pitch that pays", f"{fmt_runs(lk['contact'])} against "
                                                     f"{fmt_runs(lk['choices'])}: {lk['phrase']}"))
        count_says = re.search(r"In this count your chases pay for themselves overall \(contact ([^ ]+) "
                               r"against choices ([^ ]+) in the count table\); this pitch is where they "
                               r"don't: ", text)
        either = "This pitch doesn't pay for itself either: " in text
        if not (shown(row["choices"]) < 0 and count_pays(row)):
            if count_says or either:
                out.append(("paying count unsaid", f"said of {g} {fmt_runs(row['choices'])}, "
                                                   f"contact {fmt_runs(row['contact'])}"))
            continue
        ok = (count_says and g not in said
              and (count_says.group(1), count_says.group(2)) == (fmt_runs(row["contact"]), fmt_runs(row["choices"]))
              ) or (either and g in said and not count_says)
        if not ok or not gets_back_holds(text, lk):
            out.append(("paying count unsaid", f"{g} contact {fmt_runs(row['contact'])} against "
                                               f"{fmt_runs(row['choices'])}, line {it.get('step')}"))
        said.add(g)
    return out


def card_gap(leaks):
    """The leaks' pooled rate less their pooled league rate, in points,
    each rounded as a leak row prints it: for one leak, its row's two
    numbers apart. Taken from the leaks' chases, pitches and league
    rates, not from step 17's function."""

    n = sum(lk["pitches"] for lk in leaks)
    rate = sum(lk["chases"] for lk in leaks) / n
    league = sum(stored(lk["league"]) * lk["pitches"] for lk in leaks) / n
    return {r - lg for r in printed(rate, 100) for lg in printed(league, 100)}


def leaks_named(n):
    """Step 17's names for the leaks a target covers."""

    return "leak 1" if n == 1 else ("leaks 1 and 2" if n == 2 else f"leaks 1 to {n}")


def all_video(player):
    leaks = player["leaks"]["all"]
    return bool(leaks) and all(lk["depth_in"] < CLEARLY_OFF_IN for lk in leaks)


def target_problems(player):
    text = player.get("target_text") or ""
    out = []
    if ("No target" in text or "No chase target" in text) and "already" in text:
        out.append(("no target says already", text[:60]))
    t = player.get("target")
    if not t or not text:
        return out
    if all_video(player):
        if "Under" in text:
            out.append(("number on a video-only card", text[:60]))
        return out
    if (not any(w in text for w in ("points above the league's chase rate", "point above the league's chase rate",
                                    "about at the league's chase rate"))
            or leaks_named(len(player["leaks"]["all"])) not in text.lower()):
        out.append(("target without unit or leaks", text[:60]))
    if text.startswith(("No target", "No chase target")):
        x = card_gap(player["leaks"]["all"])
        says = re.search(r"(?:were|was) (\d+) points? above the league's chase rate", text)
        quoted = int(says.group(1)) if says else 0 if "about at the league's chase rate" in text else None
        if "below the league" in text or quoted not in x:
            out.append(("no target off the card's rows", f"rows add up to {sorted(x)}: {text[:70]}"))
        low = round(t["predicted"] * 100) < -RULES["TARGET_MIN_PTS"]
        if low != (" at or under " in text):
            out.append(("no target 'about at' a forecast below",
                        f"forecast {t['predicted'] * 100:+.1f}: {text[-60:]}"))
    if text.startswith(("No target", "No chase target")):
        xf = round(t["excess"] * 100)
        if (min(abs(r - xf) for r in card_gap(player["leaks"]["all"])) >= RULES["TARGET_SCALE_NOTE_PTS"]
                and "simpler league rate" not in text):
            out.append(("target scale or unit unsaid", text[:70]))
    if not text.startswith(("No target", "No chase target", "No number")):
        x = round(t["excess"] * 100)
        far = min(abs(r - x) for r in card_gap(player["leaks"]["all"])) >= RULES["TARGET_SCALE_NOTE_PTS"]
        if (far and "on the rows above" not in text) or not re.search(r"about \d+ points? above it", text):
            out.append(("target scale or unit unsaid", text[:70]))
    if t.get("out_of_sample") == "no":
        if "you'd be" in text or "afterward" not in text or ("You were at" not in text
                                                             and "Not scored" not in text
                                                             and t.get("actual", 0) is not None):
            out.append(("retrospective target as a forecast", text[:60]))
        a = t.get("actual")
        said = [f"You were at {a * 100:{w}}".replace("-", "−") for w in (".0f", ".1f")] if a is not None else []
        if a is not None and not any(s in text for s in said):
            out.append(("target result misquoted", f"actual {a * 100:.1f}: {text[-50:]}"))
    return out


def label_problems(player):
    """The roster's start line and the hand in the leak names."""

    out = []
    m = re.search(r"\((\d+)% vs (\d+)%", player.get("start_with") or "")
    if m and abs(int(m.group(1)) - int(m.group(2))) < 5:
        out.append(("start line quotes near-identical rates", m.group(0)))
    for lk in player["leaks"]["all"]:
        share = lk["share_rhp"] if lk["hand"] == "R" else 1 - lk["share_rhp"]
        if lk["hand"] and share < 1 and "mostly" not in lk.get("phrase", "mostly"):
            out.append(("hand overstated", lk["phrase"]))
        if lk["hand"] and "extra_rhp" in lk:
            carry = [v if lk["hand"] == "R" else 1 - v for v in (lk["extra_rhp"], lk["cost_rhp"])]
            if min(carry) <= RULES["HAND_CARRY_SHARE"]:
                out.append(("hand named without its extra chases",
                            f"{lk['phrase']}: {carry[0]:.0%} of the extra chases, {carry[1]:.0%} of the cost"))
        if player["bats"] == "S" and lk.get("side_extra"):
            other = max(lk["side_extra"].values())
            if lk["side_extra"].get(lk["side"], 0) < other:
                out.append(("switch leak on the quieter side", f"batting {lk['side']}: {lk['phrase']}"))
    return out


def hand_problems(player):
    """The pitcher-hand tabs: the note each pitch line gets for a hand,
    which splits the line's pitches by the pitcher's hand and so adds up
    to its leak's, and each hand leak's number, which is the card's number
    for the same pitch or none when the card does not list it."""

    out = []
    leaks = player["leaks"]["all"]
    cells = [(lk["count_group"], lk["pitch_group"], lk["region"]) for lk in leaks]
    for it in player["plan_items"]:
        if it["kind"] != "pitch":
            continue
        lk, notes = leaks[it["n"] - 1], it.get("by_hand") or {}
        if (set(notes) != {"R", "L"} or sum(c["pitches"] for c in notes.values()) != lk["pitches"]
                or sum(c["chases"] for c in notes.values()) != lk["chases"]):
            out.append(("hand note does not add up", f"vs tabs: line {it.get('step')}"))
    for h in ("R", "L"):
        for lk in player["leaks"].get(h) or []:
            cell = (lk["count_group"], lk["pitch_group"], lk["region"])
            if lk.get("all_n", "none given") != (cells.index(cell) + 1 if cell in cells else None):
                out.append(("hand leak misnumbered", f"vs {h}HP: {lk['phrase']}"))
    return out


def problems(player):
    """Every problem on one card: its plan, the target and the labels,
    and the pitcher-hand tabs' notes and leak numbers. A plan without a
    pitch line has no plan problems, but its target and labels are
    checked."""

    rows = {r["group"]: r for r in player["tables"]["all"]}
    out = plan_problems(player["plan_items"], player["leaks"]["all"], rows, player)
    out += order_problems(player["plan_items"], player["leaks"]["all"], rows, player)
    out += sentence_problems(player["plan_items"], rows, player)
    out += paying_problems(player["plan_items"], player["leaks"]["all"], rows)
    out += target_problems(player) + label_problems(player) + hand_problems(player)
    if player.get("plan_items_by_hand"):
        out.append(("two plans", "plan_items_by_hand"))
    return out


def counts(players):
    """{kind: [names]} over the all-pitchers plans, and the union."""

    found = {k: [] for k in KINDS}
    for p in players:
        for kind in {k for k, d in problems(p) if not d.startswith("vs ")}:
            found[kind].append(p["name"])
    return found


def check(players):
    """Stops the build, listing each contradiction, when any plan has one.
    Returns the number of plans checked."""

    failed = [(p["name"], kind, detail) for p in players for kind, detail in problems(p)]
    if failed:
        by_kind = {}
        for name, kind, detail in failed:
            by_kind.setdefault(kind, []).append(f"{name} ({detail})")
        lines = [f"  {kind}: {KINDS[kind]}. {len(v)}: " + "; ".join(v[:5]) + (" ..." if len(v) > 5 else "")
                 for kind, v in by_kind.items()]
        raise SystemExit(f"{len(failed)} contradictions in the plans (scripts/plan_checks.py):\n"
                         + "\n".join(lines))
    return len(players)


def load_page(path):
    html = open(path, encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="card-data">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))["players"]


if __name__ == "__main__":
    players = load_page(sys.argv[1])
    planned = [p for p in players if any(it["kind"] == "pitch" for it in p["plan_items"])]
    found = counts(players)
    print(f"{len(players)} cards, {len(planned)} with a pitch line")
    for kind, names in found.items():
        print(f"  {len(names):4d}  {kind}" + (f"   e.g. {', '.join(names[:3])}" if names else ""))
    first = {"contact first", "frame first", "numbers backwards", "video only, nobody named"}
    argue = {"no target says already", "fastball strength over a fastball line",
             "header 0.0 unexplained", "plus count, no why"}
    for label, kinds in (("first line not the instruction", first), ("card argues with its plan", argue)):
        print(f"  {len(set().union(*(found[k] for k in kinds))):4d}  union: {label}")
    hand = sum(1 for p in players for k, d in problems(p) if d.startswith("vs "))
    print(f"  {hand:4d}  problems on the pitcher-hand tabs (hand notes and leak numbers)")
