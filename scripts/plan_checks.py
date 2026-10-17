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
table, the header numbers and the target. Step 17 runs it on every plan,
all pitchers and each pitcher-hand tab, and stops listing what failed.

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


def plan_problems(items, leaks, rows, player, all_pitchers=True):
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
    if all_pitchers and zero and "nothing net" not in texts:
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
        if all_pitchers and lk["hand"]:
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
    if (not any(w in text for w in ("points above the league's chase rate", "about at the league's chase rate",
                                    "points below the league's chase rate"))
            or leaks_named(len(player["leaks"]["all"])) not in text.lower()):
        out.append(("target without unit or leaks", text[:60]))
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
    return out


def problems(player):
    """Every problem on one card: the all-pitchers plan, the target and
    the labels, and each pitcher-hand tab's plan. A plan without a pitch
    line has no plan problems, but its target and labels are checked."""

    rows = {r["group"]: r for r in player["tables"]["all"]}
    out = plan_problems(player["plan_items"], player["leaks"]["all"], rows, player)
    out += target_problems(player) + label_problems(player)
    for h, items in (player.get("plan_items_by_hand") or {}).items():
        hrows = {r["group"]: r for r in player["tables"][h]}
        out += [(kind, f"vs {h}HP: {detail}")
                for kind, detail in plan_problems(items, player["leaks"][h], hrows, player, False)]
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
    return sum(1 + len(p.get("plan_items_by_hand") or {}) for p in players)


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
    print(f"  {hand:4d}  problems on the pitcher-hand tabs")
