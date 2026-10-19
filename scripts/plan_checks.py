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

Run on a built page it counts each kind without stopping, which is how
the before and after counts were taken:

    python scripts/plan_checks.py results/xchase/player_cards/2026/index.html
"""

import json
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
    "first line in a plus count, no why": "the first pitch line is in a count the table shows as a "
                                          "plus and does not say why",
    # Sentences that quote a number must quote the one beside them
    "rates misquoted": "a pitch line's two rates are not its leak's",
    "inches misquoted": "a take line's inches off the zone are not its leak's",
    "framing misquoted": "a framing line's runs or level are not the hitter's",
    "plus count misquoted": "a plus-count sentence's runs are not the count table's",
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
}


def fmt_runs(v):
    v = round(stored(v), 1)
    return "0.0" if v == 0 else ("+" if v > 0 else "−") + f"{abs(v):.1f}"


def stored(v):
    """A value as the built page stores it, four decimals (step 17's
    to_json_safe): the page prints run values from this."""

    return round(float(v), 4)


def shown(v):
    return round(stored(v), 1)


def printed(v, scale=1):
    """How v prints as a whole number. A built page stores values to four
    decimals, which can move a rate that sits on a half point by one, so
    both neighbors of the stored value count."""

    return {int(f"{(v + d) * scale:.0f}") for d in (-5e-5, 0, 5e-5)}


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
        if it["kind"] == "frame" and "biggest piece" in it["text"] and not biggest:
            out.append(("biggest, but not", f"leaks {leak_n}"))
    fastball_line = any(tuple(it["cell"])[1] == "fastball" for it in pitches)
    keep = next((it for it in items if it["kind"] == "keep"), None)
    if keep and fastball_line and "fastball decisions are a strength" in keep["text"]:
        out.append(("fastball strength over a fastball line", keep["text"][:60]))
    elif (keep and "fastball decisions are a strength" in keep["text"]
          and any(lk["pitch_group"] == "fastball" for view in player["leaks"].values() for lk in view)):
        out.append(("fastball strength beside a fastball leak", keep["text"][:60]))
    if keep:
        says_one = "the pitch above" in keep["text"]
        if says_one != (len(pitches) == 1):
            out.append(("keep line miscounts", f"{len(pitches)} pitch lines"))

    # framing: a good chooser, and the header's 0.0
    c = stored(player["choices"])
    frames = [it["text"] for it in items if it["kind"] == "frame" and it["text"].startswith("Overall your")]
    if c > 0 and not any(("better than average" in f or "about average" in f) for f in frames):
        out.append(("good chooser unframed", f"choices {fmt_runs(c)}"))
    for f in frames:
        if c <= -1:
            ok = f"cost you {round(-c):.0f} run" in f
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

    # the first line in a count the table calls a plus
    g = tuple(pitches[0]["cell"])[0]
    v = rows[g]["choices"]
    why = f"{COUNT_PHRASES[g]}, your choices are a plus overall"
    if shown(v) > 0 and why.lower() not in pitches[0]["text"].lower():
        out.append(("first line in a plus count, no why", f"{g} {fmt_runs(v)}"))
    for it in pitches:
        m = re.search(r"\. ([^.]+?), your choices are a plus overall \(([^ ]+) runs", it["text"])
        if m:
            gg = tuple(it["cell"])[0]
            if m.group(1).lower() != COUNT_PHRASES[gg] or m.group(2) != fmt_runs(rows[gg]["choices"]):
                out.append(("plus count misquoted", f"{m.group(2)} vs {fmt_runs(rows[gg]['choices'])}"))

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


def card_gap(leaks):
    """The leaks' pooled rate less their pooled league rate, in points,
    each rounded as a leak row prints it: for one leak, its row's two
    numbers apart. Taken from the leaks' chases, pitches and league
    rates, not from step 17's function."""

    n = sum(lk["pitches"] for lk in leaks)
    rate = sum(lk["chases"] for lk in leaks) / n
    league = sum(lk["league"] * lk["pitches"] for lk in leaks) / n
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
    if t.get("out_of_sample") == "no":
        if "you'd be" in text or "afterward" not in text or ("You were at" not in text
                                                             and "Not scored" not in text
                                                             and t.get("actual", 0) is not None):
            out.append(("retrospective target as a forecast", text[:60]))
        a = t.get("actual")
        if a is not None and f"You were at {a * 100:.0f}" not in text and f"You were at {a * 100:.1f}" not in text:
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
             "header 0.0 unexplained", "first line in a plus count, no why"}
    for label, kinds in (("first line not the instruction", first), ("card argues with its plan", argue)):
        print(f"  {len(set().union(*(found[k] for k in kinds))):4d}  union: {label}")
    hand = sum(1 for p in players for k, d in problems(p) if d.startswith("vs "))
    print(f"  {hand:4d}  problems on the pitcher-hand tabs (hand notes and leak numbers)")
