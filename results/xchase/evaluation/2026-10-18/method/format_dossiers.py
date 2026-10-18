import json, re, math, sys
from pathlib import Path
d = json.load(open("dump_2026.json"))
P = {p["slug"]: p for p in d["data"]["players"]}
cards = {c["slug"]: c for c in d["cards"]}
GL = {g["key"]: g["label"] for g in d["groups"]}
GL["total"] = "All counts"
head = d["roster"]["head"]
roster = {}
for r in d["roster"]["rows"]:
    name = re.sub(r" noted$", "", r[1])
    roster[name] = dict(zip([h.rstrip("▼▲") for h in head], r))

def pct(v): return "–" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{round(v*100)}%"
def xw(v): return "–" if v is None else f"{v:.3f}".lstrip("0")
def runs(v):
    r = round(v * 10) / 10
    return "0.0" if r == 0 else ("+" if r > 0 else "−") + f"{abs(r):.1f}"

def table(rows):
    out = ["| count | pitches | chases you/avg | far-off you/avg | misses you/avg | xwOBA you/avg | choices | contact | count status |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {GL[r['group']]} | {r['pitches']:,} | {pct(r['chase'])} / {pct(r['chase_league'])} | {pct(r['far'])} / {pct(r['far_league'])} | {pct(r['whiff'])} / {pct(r['whiff_league'])} | {xw(r['xwoba'])} / {xw(r['xwoba_league'])} | {runs(r['choices'])} | {runs(r['contact'])} | {r.get('status') or ''} |")
    return "\n".join(out)

CONST = [d["countNote"], d["evidence"]]
def aside_top(text):
    """The aside's text down to the count table (plan, coach's note, leaks, target), tidied."""
    t = text.split("\nBy count\n")[0]
    t = re.sub(r"\nleak\n(\d+)\n", r"  [leak tag \1]\n", t)
    t = re.sub(r"\n(\d)\n(?=[A-Z])", r"\n(\1) ", t)       # step / leak numbers onto their line
    t = re.sub(r"\n{2,}", "\n", t).strip()
    return t

def leak_fact(k, lk):
    keys = ["count_group", "pitch_group", "region", "hand", "share_rhp", "side", "pitches", "chases", "rate", "league", "extra_chases", "choices", "contact", "depth_in", "excess_counts", "count_status", "count_xwoba", "count_xwoba_league", "count_xwoba_shrunk", "from_leak_hand"]
    f = {k2: lk.get(k2) for k2 in keys if k2 in lk}
    for k2 in ["rate", "league", "share_rhp", "extra_chases", "choices", "contact", "depth_in", "count_xwoba", "count_xwoba_league", "count_xwoba_shrunk"]:
        if isinstance(f.get(k2), float): f[k2] = round(f[k2], 3)
    return f"  leak {k}: " + json.dumps(f, ensure_ascii=False)

def dossier(slug, idx):
    c, p = cards[slug], P[slug]
    L = [f"## CARD {idx}: {p['name']}  (#{slug})", ""]
    L.append(f"HEADER: {p['name']} | {c['line1']} | {c['line2']}")
    L.append("TILES: " + c["tiles"].replace("\n", " | "))
    if c["notice"]: L.append("NOTICE: " + c["notice"])
    L.append("PICTURE ROWS: " + " / ".join(c["rowheads"]) + "  (columns: First pitch, Ahead, 0-1 or 1-1, Two strikes)")
    L.append("PICTURE SELECTED WHEN THE CARD OPENS: " + str(c["selected"]))
    for m in c.get("markers", []):
        if not m["drawn"]:
            L.append(f"  marker {m['n']}: NOT DRAWN on any picture row"); continue
        a = m["at_marker"]
        L.append(f"  marker {m['n']}: row '{m['row']}'{' (fallback row)' if m['row_fallback'] else ''}, {GL[m['group']]} picture; picture at the marker: you {a['you']}% vs avg {a['avg']}% (gap {a['gap']:+d} pts, color strength {a['evidence']}){'; marker nudged off the leak spot to avoid another' if m['moved'] else ''}{'; MARKER INSIDE THE ZONE BOX' if m['in_zone_box'] else ''}; {m['panel_pitches']} pitches in that picture")
    L.append("")
    for h, lab in [("all", "ALL PITCHERS (default view)"), ("R", "vs RHP tab"), ("L", "vs LHP tab")]:
        L.append(f"### {lab}: right-hand column as printed")
        L.append(aside_top(c["aside"][h]))
        L.append(f"By count ({lab}):")
        L.append(table(p["tables"][h]))
        L.append("")
    L.append("FAR-OFF CHASE RATE BY SEASON: you " + ", ".join(f"{y}: {pct(v)}" for y, v in p["trend"]) + " | league " + ", ".join(f"{y}: {pct(v)}" for y, v in d["data"]["leagueTrend"]))
    L.append("ZONE NUMBERS (details panel, all pitchers, chase rate you / avg (pitches)):")
    L.extend("  " + r for r in c["numbers"])
    rr = roster.get(p["name"])
    L.append("ROSTER ROW: " + (json.dumps(rr, ensure_ascii=False) if rr else "MISSING FROM ROSTER"))
    L.append("UNDERLYING DATA (not printed; for checking the sentences):")
    L.append("  " + json.dumps({k: (round(p[k], 4) if isinstance(p[k], float) else p[k]) for k in ["archetype", "noted", "note_start", "chase", "chase_league", "whiff", "whiff_league", "choices", "contact", "runs_at_stake", "fastball_choices", "xchase_plus", "rank", "side_pitches", "target", "target_beat"] if k in p}, ensure_ascii=False))
    for k, lk in enumerate(p["leaks"]["all"], 1): L.append(leak_fact(k, lk))
    for h in ["R", "L"]:
        for k, lk in enumerate(p["leaks"].get(h) or [], 1): L.append(leak_fact(f"{h}{k}", lk))
    L.append("  plan_items (all): " + json.dumps([{k: it.get(k) for k in ['kind','n','step','cell','video']} for it in p["plan_items"]], ensure_ascii=False))
    L.append("")
    return "\n".join(L)

order = [p["slug"] for p in d["data"]["players"]]           # page order: by xChase+ rank
Path("dossiers").mkdir(exist_ok=True)
all_text = []
for i, s in enumerate(order, 1):
    all_text.append(dossier(s, i))
Path("dossiers/all_cards.md").write_text("\n".join(all_text))
# batches
nb = int(sys.argv[1]) if len(sys.argv) > 1 else 10
size = math.ceil(len(order) / nb)
for b in range(nb):
    part = all_text[b*size:(b+1)*size]
    Path(f"dossiers/batch_{b+1:02d}.md").write_text("\n".join(part))
    print(b+1, len(part), sum(len(x) for x in part))
# references and page-level
ref = [c for c in d["cards"] if c["reference"]]
pg = ["# Page-level text (2026 page)", "", "FOOTER: " + d["footer"], "COUNT NOTE: " + d["countNote"], "EVIDENCE LINE: " + d["evidence"], "",
      "ROSTER TITLE: " + d["roster"]["title"], "ROSTER LEDE: " + d["roster"]["lede"], "ROSTER GLOSSARY: " + d["roster"]["glossary"], "ROSTER STATE LINE: " + d["roster"]["state"], "ROSTER COLUMNS: " + " | ".join(head), ""]
pg.append("Every card's legend: " + cards[order[0]]["legend"]); pg.append("Orientation (RHB): " + next(c["orient"] for c in d["cards"] if not c["reference"] and P[c["slug"]]["bats"]=="R"))
pg.append("State line: " + cards[order[0]]["state"]); pg.append("Zone numbers note: " + cards[order[0]]["numbers_note"]); pg.append("")
for c in ref:
    pg.append(f"## REFERENCE CARD: {c['name']}"); pg += [c["line1"], c["line2"], "ROWS: " + " / ".join(c["rowheads"]), "SELECTED: " + str(c["selected"]), "ORIENT: " + c["orient"], "LEGEND: " + c["legend"], c["aside"]["all"], ""]
pg.append("## FULL ROSTER TABLE (as shown, default sort)")
pg.append("| " + " | ".join(head) + " |"); pg.append("|" + "---|" * len(head))
for r in d["roster"]["rows"]: pg.append("| " + " | ".join(r) + " |")
Path("dossiers/page_and_roster.md").write_text("\n".join(pg))
print("page", len("\n".join(pg)))
