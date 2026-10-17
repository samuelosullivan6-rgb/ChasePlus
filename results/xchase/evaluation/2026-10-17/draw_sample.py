import json, random, re, unicodedata
D = json.load(open("data/cleaned/card_players_2026.json"))
P = D["players"]
def slug(name):
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "_" for c in plain.lower()).strip("_")
def opening(p):
    it = p["plan_items"][0]; leaks = p["leaks"]["all"]
    if it["kind"] == "pitch":
        lk = leaks[it["n"]-1]
        if "video room" in it["text"]: return "pitch: video item"
        return "pitch: two-strike take" if lk["count_group"] == "two" else "pitch: take before two strikes"
    if it["kind"] == "fallback":
        return "nothing to change" if it["text"].startswith("Nothing to change") else "nothing stands out"
    return {"contact": "contact line", "frame": "spread line"}[it["kind"]]
rng = random.Random(20261017)
easiest = sorted(p["name"] for p in P if p.get("noted") == "easiest")
biggest = sorted(p["name"] for p in P if p.get("noted") == "biggest")
rest = [p for p in P if not p.get("noted")]
strata = [
    ("pitch: two-strike take", {"mixed"}),
    ("pitch: two-strike take", {"decision-only", "decision-led"}),
    ("pitch: take before two strikes", {"mixed"}),
    ("pitch: take before two strikes", {"decision-only"}),
    ("contact line", {"execution-led"}),
    ("nothing stands out|nothing to change", {"mixed"}),
    ("pitch: video item", {"mixed"}),
    ("spread line", {"mixed", "decision-only"}),
]
picks = [("noted: easiest", n) for n in rng.sample(easiest, 2)] + [("noted: biggest", n) for n in rng.sample(biggest, 2)]
for op, arch in strata:
    pool = sorted(p["name"] for p in rest if re.fullmatch(op, opening(p)) and p["archetype"] in arch)
    picks.append((f"random: {op} x {'/'.join(sorted(arch))} (pool {len(pool)})", rng.choice(pool)))
by = {p["name"]: p for p in P}
lines = ["# Evaluation sample, 2026 cards", "",
         "Drawn 2026-10-17 with Python's random.Random(20261017), by the script beside this file",
         "(draw_sample.py). Two noted 'easiest' and two noted 'biggest' at random from their groups;",
         "eight from the other 244 hitters, one from each stratum of opening line type x archetype",
         "below, which together cover every opening line type and every archetype outside the",
         "noted group. Every reviewer works these 12 and names any others.", "",
         "| # | Hitter | How drawn | Archetype | xChase+ (rank) | Plan opens with | start_with (roster) | Card |",
         "|---|---|---|---|---|---|---|---|"]
for k, (how, name) in enumerate(picks, 1):
    p = by[name]
    lines.append(f"| {k} | {name} | {how} | {p['archetype']} | {round(p['xchase_plus'])} ({p['rank']}) | {opening(p)} | "
                 f"{p.get('start_with') or '(none)'} | http://localhost:8765/2026/index.html#{slug(name)} |")
open("results/xchase/evaluation/2026-10-17/sample.md", "w").write("\n".join(lines) + "\n")
json.dump([{"how": h, "name": n, "slug": slug(n)} for h, n in picks],
          open("results/xchase/evaluation/2026-10-17/sample.json", "w"), indent=1, ensure_ascii=False)
print("\n".join(lines))
