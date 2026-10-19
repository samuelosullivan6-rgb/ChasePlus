"""Re-measure the audit's open issues on two extractions: the audited build and the rebuilt one."""
import json, math, re, sys
def pw(v, s=100): return math.floor(round(float(v), 4) * s + 0.5)
def load(f):
    d = json.load(open(f)); P = {p["slug"]: p for p in d["data"]["players"]}
    return d, P, [c for c in d["cards"] if not c["reference"]]
def plan(c, h="all"): return c["aside"][h].split("Biggest leaks")[0]
def measure(f):
    d, P, cards = load(f); m = {}
    pitch = lambda p: [it for it in p["plan_items"] if it["kind"] == "pitch"]
    # 10 small samples
    m["10 take lines on <20 pitches with no word of it"] = sum(1 for c in cards for it in pitch(P[c["slug"]])
        if not it["video"] and P[c["slug"]]["leaks"]["all"][it["n"]-1]["pitches"] < 20 and "of these pitches so far" not in it["text"])
    # 12 numbered targets 5+ off the rows with no label
    def gap(lks):
        n = sum(l["pitches"] for l in lks); return pw(sum(l["chases"] for l in lks)/n) - pw(sum(l["league"]*l["pitches"] for l in lks)/n)
    m["12 targets 5+ points off their rows, unlabeled"] = sum(1 for c in cards for p in [P[c["slug"]]] if p.get("target") and p["target_text"]
        and not p["target_text"].startswith("No number") and abs(gap(p["leaks"]["all"]) - round(p["target"]["excess"]*100)) >= 5
        and "simpler league rate" not in p["target_text"])
    # 14 markers on a spot at or under average
    mk = [mm for c in cards for mm in c.get("markers", []) if mm.get("drawn")]
    m["14 leak numbers on a spot at or under average (of %d)" % len(mk)] = sum(1 for mm in mk if mm["at_marker"]["gap"] <= 0)
    m["14 ...visibly blue (-5 or less)"] = sum(1 for mm in mk if mm["at_marker"]["gap"] <= -5)
    m["14 plan first lines whose number is on such a spot"] = sum(1 for c in cards for p in [P[c["slug"]]] for its in [pitch(p)] if its
        and c["markers"][its[0]["n"]-1]["drawn"] and c["markers"][its[0]["n"]-1]["at_marker"]["gap"] <= 0)
    # 18 contact
    says = lambda c: "contact is your bigger cost" in plan(c) or "issue is contact" in plan(c)
    m["18 contact the bigger cost (3+ runs) with no contact word"] = sum(1 for c in cards for p in [P[c["slug"]]]
        if p["contact"] <= -3 and -p["contact"] > max(-p["choices"], 0) and -p["contact"] >= p["runs_at_stake"] and not says(c))
    m["18 contact word on a contact loss under 3 runs"] = sum(1 for c in cards for p in [P[c["slug"]]] if says(c) and p["contact"] > -3)
    # 24 "miss about as often" beside a 5+ point gap
    m["24 'miss about as often' beside rates 5+ apart"] = sum(1 for c in cards for p in [P[c["slug"]]]
        if "miss about as often" in plan(c) and abs(pw(p["whiff"]) - pw(p["whiff_league"])) >= 5)
    # 19 roster
    head = [h.rstrip("▼▲") for h in d["roster"]["head"]]
    rows = {re.sub(r" noted$", "", r[head.index("Hitter")]): dict(zip(head, r)) for r in d["roster"]["rows"]}
    sw = "Start with"
    m["19 roster Start with is another leak than Top leak, unmarked"] = sum(1 for c in cards for p in [P[c["slug"]]] for its in [pitch(p)]
        if its and its[0]["n"] != 1 and not rows[p["name"]][sw].startswith("Leak "))
    m["19 roster Inches off '4' for a video item"] = sum(1 for c in cards for p in [P[c["slug"]]] if p["leaks"]["all"]
        and p["leaks"]["all"][0]["depth_in"] < 4 and rows[p["name"]]["Inches off"] == "4")
    # 27, 28, 33, 37, 38, 39
    allplan = lambda c: " ".join(plan(c, h) for h in ("all", "R", "L"))
    m["27 'about average overall (-'"] = sum(1 for c in cards if "about average overall (-" in allplan(c) or "about average overall (−" in allplan(c))
    m["33 '1 points'"] = sum(1 for c in cards if re.search(r"\b1 points\b", P[c["slug"]].get("target_text") or ""))
    m["33 'Target: No' prefix"] = sum(1 for c in cards if "Target: No" in c["aside"]["all"])
    m["33 numbered forecast with no unit"] = sum(1 for c in cards for t in [P[c["slug"]].get("target_text") or ""]
        if "you'd be about" in t and not re.search(r"you'd be about \d+ points? above it", t))
    m["35 count phrase said twice by the plus clause"] = sum(1 for c in cards if re.search(r", your choices are a plus overall", plan(c)))
    m["35 leak caption under an empty list (views)"] = sum(1 for c in cards for h in ("all", "R", "L")
        if "None worth 0.75" in c["aside"][h] and "so it can leave a bigger one out" in c["aside"][h].split("None worth 0.75")[1][:300])
    m["37 second line in a different plus count with no why"] = 0
    for c in cards:
        p = P[c["slug"]]; rws = {r["group"]: r for r in p["tables"]["all"]}; seen = set()
        for it in pitch(p):
            g = it["cell"][0]
            why = ("your choices are a plus overall" in it["text"]) or ("your choices come out about even" in it["text"])
            if pw(rws[g]["choices"], 10) > 0 and g not in seen and not why: m["37 second line in a different plus count with no why"] += 1
            if why: seen.add(g)
    m["38 'within a ball' on a card"] = sum(1 for c in cards if "within a ball" in c["aside"]["all"])
    m["39 plan rates one point off their leak row"] = sum(1 for c in cards for p in [P[c["slug"]]] for it in pitch(p)
        for mm in [re.search(r"You swung at (\d+)% of them; hitters on average swing at (\d+)%", it["text"])]
        if mm and (int(mm.group(1)), int(mm.group(2))) != (pw(p["leaks"]["all"][it["n"]-1]["rate"]), pw(p["leaks"]["all"][it["n"]-1]["league"])))
    # 29 table fits at the extraction width (1440)
    ov = [c.get("table_overflow") for c in cards if c.get("table_overflow") is not None]
    if ov: m["29 By count tables wider than their box at 1440 px (of %d)" % len(ov)] = sum(1 for v in ov if v > 2)
    return m
fs = sys.argv[1:]
res = [measure(f) for f in fs]
keys = list(dict.fromkeys(k for r in res for k in r))
print("| Issue | " + " | ".join(fs) + " |")
for k in keys: print("| " + k + " | " + " | ".join(str(r.get(k, "")) for r in res) + " |")
