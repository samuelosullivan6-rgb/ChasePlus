"""Re-measure the audit's issues 2, 6, 10, 11, 12, 13, 16, 17 and 21 on built 2026 pages,
from the card data each page carries (plan_checks.load_page), printing one column per page.
Run from the repository root, with a label before each page:

    git show 0d64764:results/xchase/player_cards/2026/index.html > /tmp/audited.html
    python results/xchase/evaluation/2026-10-18/method/remeasure_order_target_hand.py \
        audited /tmp/audited.html rebuilt results/xchase/player_cards/2026/index.html

Issue 2 needs the plan lines' per-hand notes and issue 21 the leaks' side totals, so on a page
built before them those rows count 0."""
import sys, re, json
sys.path.insert(0, "scripts")
import plan_checks as pc

G = ["first", "ahead", "even", "two"]
def rg(lk): return int(f"{lk['rate']*100:.0f}") - int(f"{lk['league']*100:.0f}")
def video(lk): return lk["depth_in"] < 4
def cell(lk): return (lk["count_group"], lk["pitch_group"], lk["region"])
def pooled_raw(leaks):  # the audit's pooled card gap
    return 100 * sum(lk["chases"] - lk["league"] * lk["pitches"] for lk in leaks) / sum(lk["pitches"] for lk in leaks)

def measure(path):
    P = pc.load_page(path)
    m = {}
    def add(k, name):
        m.setdefault(k, set()).add(name)
    for p in P:
        L = p["leaks"]["all"]
        items = p["plan_items"]
        pitches = [it for it in items if it["kind"] == "pitch"]
        t = p.get("target_text") or ""
        notarget = t.startswith(("No target", "No chase target"))
        # issue 6: "points below" under leaks all printed above the league
        if "points below the league's chase rate" in t and all(lk["rate"] > lk["league"] for lk in L):
            add("6 'below the league' under leaks printed above it", p["name"])
        # issue 12: printed points 5+ off the card's pooled rows
        if p.get("target") and L and not all(video(lk) for lk in L):
            mm = re.search(r"(\d+) points? (above|below)", t)
            if mm:
                x = int(mm.group(1)) * (1 if mm.group(2) == "above" else -1)
            elif "about at the league's chase rate" in t:
                x = 0
            else:
                x = None
            if x is not None and abs(x - pooled_raw(L)) >= 5:
                add("12 target points 5+ off the rows: no-target" if notarget else
                    "12 target points 5+ off the rows: numbered", p["name"])
            # issue 13 (1): "about at it" for a forecast below -2
            if notarget and round(p["target"]["predicted"] * 100) < -2 and "about at" in t:
                add("13 'about at it' for a forecast below -2", p["name"])
        if not pitches:
            continue
        keep = next((it["text"] for it in items if it["kind"] == "keep"), "")
        only = "The only change" in keep
        on = {it["n"] for it in pitches}
        # issue 13 (2): numbered target counting a leak off the plan, under "the only changes"
        if p.get("target") and "Under" in t and any(n not in on for n in range(1, len(L) + 1)) and only:
            add("13 numbered target counts a leak off the plan, under 'the only changes'", p["name"])
        first = L[pitches[0]["n"] - 1]
        # issue 10
        if first["pitches"] < 20:
            add("10 first line on under 20 pitches", p["name"])
            if first["count_group"] != "two" and pitches[0]["n"] != 1:
                add("10 ...a pre-two-strike cell moved ahead of leak 1", p["name"])
            if any(lk["pitches"] >= 2 * first["pitches"] and n not in on for n, lk in enumerate(L, 1)):
                add("10 ...while a leak with twice its pitches is off the plan", p["name"])
        # issue 17
        if rg(first) < 5:
            add("17 step 1 at the league's rate", p["name"])
            if any(rg(lk) >= 5 and not video(lk) for lk in L if lk is not first) and not video(first):
                add("17 ...with a real-gap take on the list", p["name"])
        # issue 16: a leak off the plan, 1.25x a plan line, 20+ pitches, not named
        words = " ".join(it["text"] for it in items if it["kind"] != "pitch")
        for n, lk in enumerate(L, 1):
            if n in on:
                continue
            if lk["pitches"] >= 20 and any(-lk["choices"] >= 1.25 * -L[k - 1]["choices"] for k in on):
                add("16 bigger leak off the plan (1.25x, 20+ pitches)", p["name"])
                if f"Leak {n} (" not in words:
                    add("16 ...and no line names it", p["name"])
            if n == 1 and all(-lk["choices"] >= 2 * -L[k - 1]["choices"] for k in on):
                add("16 leak 1 off the plan at 2x every plan line", p["name"])
        # issue 11: costly count with no pitch line and no sentence naming it
        rows = {r["group"]: r for r in p["tables"]["all"]}
        named_counts = {L[int(n) - 1]["count_group"] for n in re.findall(r"Leak (\d) \(", words)}
        lines = {L[k - 1]["count_group"] for k in on}
        for g in G:
            if rows[g]["choices"] <= -1.0 and g not in lines:
                if g not in named_counts and pc.COUNT_PHRASES[g] not in words.lower() and "across every count" not in words:
                    add("11 costly count with no line and no word", p["name"])
                    if only:
                        add("11 ...under 'the only change(s)'", p["name"])
        if only and (len(on) < len(L) or any(rows[g]["choices"] <= -1.0 and g not in lines for g in G)):
            add("11/16 'the only change(s)' with a leak or costly count left", p["name"])
        # issue 2: plan lines naming a hand that carries half or less of the line's extra chases or cost
        for it in pitches:
            lk = L[it["n"] - 1]
            bh = it.get("by_hand")
            if lk["hand"] and bh:
                h = bh[lk["hand"]]
                x_h = h["chases"] - h["league"] * h["pitches"] if h["pitches"] else 0
                x = lk["chases"] - lk["league"] * lk["pitches"]
                if x_h / x <= 0.5 or h["choices"] / lk["choices"] <= 0.5:
                    add("2 plan line names a hand carrying half or less of its extra chases or cost", p["name"])
                    if it is pitches[0]:
                        add("2 ...on the first line", p["name"])
        # issue 21: switch hitters (rebuilt page only has side_extra)
        if p["bats"] == "S":
            for n, lk in enumerate(L, 1):
                se = lk.get("side_extra")
                if se and se.get(lk["side"], 0) < max(se.values()):
                    add("21 switch leak drawn on the side with less of its extra chases", p["name"])
                    if n == pitches[0]["n"]:
                        add("21 ...the plan's first line, so the card opens on it", p["name"])
    return {k: len(v) for k, v in sorted(m.items())}, m

if __name__ == "__main__":
    out = {}
    for label, path in zip(sys.argv[1::2], sys.argv[2::2]):
        out[label] = measure(path)[0]
    keys = sorted(set().union(*out.values()))
    print(f"{'':78s}" + "".join(f"{l:>10s}" for l in out))
    for k in keys:
        print(f"{k:78s}" + "".join(f"{out[l].get(k, 0):10d}" for l in out))
