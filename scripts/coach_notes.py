"""
The coach's notes on the 17 noted cards (step 17), and a check of every
fact they state.

Everything else on a card is computed. These notes are written by hand,
condensed from the step 12 and 13 reports, so they can go stale or be
wrong: an audit on 2026-10-14 found ten of the seventeen stating
something the data didn't support. So each note sits next to its claims,
and step 17 checks them all against the data before it draws a card. It
stops, listing what broke, when a quoted number has drifted or a stated
pattern no longer holds.

A claim is a sentence from the note and a test. Percentages quoted as
whole numbers must round to what the note says (within 0.75 points);
"about N runs" must land within 0.75 runs of N; an xwOBA must match to
the third decimal. Patterns ("in every count", "his contact pays for
it") are tested directly.

Measures follow the cards and steps 13-16:
  runs     choices / contact per 600 PA of that season (leak_rules)
  league   the league's chase rate on the same pitches: same season,
           count, distance bucket, pitch group and side of the zone
           (leak_rules.BACKTEST_LEAGUE_CELL)
  far-off  pitches at least 0.35 ft off the zone (the "clearly off" and
           "nowhere near" buckets)
"""

from pathlib import Path
import re

import numpy as np
import pandas as pd

import leak_rules as lr

PROJECT_DIR = Path(__file__).resolve().parents[1]
CLEAN = PROJECT_DIR / "data" / "cleaned"
XCHASE = PROJECT_DIR / "results" / "xchase"
PITCH_SEASONS = [2024, 2025, 2026]
FAR = {"clearly off", "nowhere near"}
KEYS = ["game_pk", "at_bat_number", "pitch_number", "batter", "game_year"]

# The 17 hitters named in the step 12 and 13 reports, with a coach's
# note condensed from those reports and the leak the note says to start
# with (count group, pitch group, side of the zone): step 17 makes that
# leak the plan's first line, so the player's plan and the staff's note
# open in the same place. Everything else on their cards is computed, the
# same as for every other hitter.
NOTED = {
    # Easiest to improve (step 13): decision-only, persistent pattern
    "Salvador Pérez": ("easiest", "At 0-1 or 1-1, breaking balls below the zone: the plan's first line, where the take costs nothing in strikeouts. Volume, not contact: these chases turn out better than the league's, which softens every leak but erases none.", ("even", "breaking", "down")),
    "Michael Harris": ("easiest", "With two strikes, breaking balls below the zone: the plan's first line. The breaking balls, changeups and splitters below the zone that right-handers throw him with two strikes are about half of what his chases cost him; the changeups and splitters among them are the plan's second line. His contact is among the best in this group, so nothing else needs to change.", ("two", "breaking", "down")),
    "Ernie Clement": ("easiest", "On the first pitch, fastballs above the zone: the plan's first line. Before two strikes he puts 44% of his chased fastballs above the zone in play (league 18%), so it never looks like a mistake, but it is weak contact (.173 xwOBA vs .283) that gives away a hitter's count.", ("first", "fastball", "up")),
    "Angel Martínez": ("easiest", "With two strikes, breaking balls below the zone, then changeups and splitters below the zone: the plan's two lines. More of what they cost him comes from right-handers than from left-handers, and the contact is there on the swings that stay.", ("two", "breaking", "down")),
    "Ceddanne Rafaela": ("easiest", "With two strikes, fastballs above the zone: the plan's first line. His early-count chasing came down in 2025 (35% to 28% of far-off pitches) but is still well above the league's 17% and costs about 4 runs; it is next.", ("two", "fastball", "up")),
    "José Caballero": ("easiest", "With two strikes, fastballs above the zone: the plan's first line, then breaking balls below the zone. He has chased more of the far-off fastballs above the zone every year (55%, 65%, 77% since 2024), even in 2025, when his xChase+ was 109.", ("two", "fastball", "up")),
    "Ozzie Albies": ("easiest", "With two strikes, changeups and splitters below the zone: the plan's first line and his biggest leak. He chases them in every count and from both hands, and at 0-1 or 1-1 they are the plan's second line. Against left-handers he chases far-off pitches of every kind more (35% vs 19%).", ("two", "offspeed", "down")),
    "Luis García": ("easiest", "When he is ahead in the count, fastballs above the zone: the plan's first line. Three-ball counts sit inside it, and with three balls his choices cost about 5 runs, so swing only at strikes there; the card cannot show those counts on their own yet. With two strikes he chases nine fastballs above the zone in ten, but his contact there pays for it, so don't coach that one.", ("ahead", "fastball", "up")),
    "Hunter Goodman": ("easiest", "When he is ahead in the count, breaking balls below the zone: the plan's first line, and the free part, since the take costs nothing in strikeouts. Across every count before two strikes, not only ahead, he chases them 48% of the time against 30% on the same pitches, about 5 runs. Fastballs above the zone before two strikes look worse than they are: his contact nearly pays for them. The two-strike breaking ball, the plan's second line, may be contact as much as choice.", ("ahead", "breaking", "down")),
    # Biggest losses (step 12): the bottom 10 not already listed
    "Mickey Moniak": ("biggest", "When he is ahead against right-handers, changeups and splitters below the zone: the plan's first line, a take that costs nothing in strikeouts. The second line, breaking balls below the zone with two strikes against right-handers, is the bigger leak; fix the early one first.", ("ahead", "offspeed", "down")),
    "Ezequiel Tovar": ("biggest", "With two strikes, breaking balls below the zone: the plan's first line, and a take in every count, so the earlier counts come next. With two strikes, changeups and splitters below the zone are the plan's second line. The fastball decisions are fine.", ("two", "breaking", "down")),
    "Andrés Giménez": ("biggest", "With two strikes against right-handers, fastballs above the zone, then breaking balls below the zone: the plan's two lines, the cheap rules while the staff looks into the rest. Not new: xChase+ 69 and 74 in 2022-23, then 95 and 105, and back to 67, so find out what made 2024-25 work before any mechanical change. His biggest net loss by count is at 0-1 and 1-1, where none of his three biggest leaks sits, which is why the plan starts with two strikes.", ("two", "fastball", "up")),
    "Jarren Duran": ("biggest", "With two strikes against right-handers, breaking balls below the zone: the plan's first line, a take even when he could reach it, since six chases in ten are misses. A contact problem, so his two-strike take line should be stricter than league norms.", ("two", "breaking", "down")),
    "Colson Montgomery": ("biggest", "When he is ahead against right-handers, breaking balls below the zone: the plan's first take. A contact problem: two chases in three are misses, so a chase is close to a sure strike. With two strikes, the same pitch from right-handers is the plan's second line.", ("ahead", "breaking", "down")),
    "Zach Neto": ("biggest", "With two strikes, breaking balls below the zone: the plan's first line, from either hand. The sliders among them from right-handers are the steady part: he chased those well above league in 2024 and 2025 too, and in 2026 pitchers threw him far more (290, up from 184). The fastball decisions are a strength.", ("two", "breaking", "down")),
    "Oswald Peraza": ("biggest", "With two strikes, breaking balls below the zone: the plan's first line and his biggest leak. The second line is breaking balls down and away from right-handers. Three-ball counts are a separate piece the card cannot show on its own yet (62% chase against about 40%, about 5 runs in 45 pitches; they sit inside 'Ahead in the count' and the 3-2 part of 'Two strikes'): swing only at strikes there. Fewest plate appearances of the 17, so flag the sample on anything beyond these.", ("two", "breaking", "down")),
    "Jeremy Peña": ("biggest", "With two strikes, fastballs above the zone: the plan's first line and the one clear take on his card. His contact pays for most of his chases on fastballs above the zone, so keep him swinging at strikes at the top of it. The two-strike slider away and the breaking ball below the zone at 0-1 or 1-1, both from right-handers, were mostly within a ball of the zone: video items, not take rules.", ("two", "fastball", "up")),
}


# --------------------------------------------------
# THE DATA THE CLAIMS ARE CHECKED ON
# --------------------------------------------------

class Data:
    def __init__(self, players):
        costs = pd.read_parquet(CLEAN / "xchase_costs_by_pitch.parquet")
        costs = costs[costs["game_year"].isin(PITCH_SEASONS)]
        base = pd.read_parquet(CLEAN / "baseline_chase_pitches.parquet", columns=KEYS + [
            "p_throws", "pitch_type", "description", "events", "estimated_woba_using_speedangle",
            "plate_x_batter", "plate_z_normalized", "sz_top", "sz_bot", "is_analyzable",
            "is_in_zone", "is_swing"])
        base = base[base["game_year"].isin(PITCH_SEASONS)]
        df = costs.merge(base, on=KEYS, how="left")
        df = df[df["plate_x_batter"].notna() & df["plate_z_normalized"].notna()]
        parts = []
        for _, g in df.groupby("game_year"):
            g = lr.add_labels(g.copy(), float((g["sz_top"] - g["sz_bot"]).mean()))
            g = lr.add_choices_contact(g)
            g["e"] = g.groupby(lr.BACKTEST_LEAGUE_CELL)["is_chase"].transform("mean")
            parts.append(g)
        df = pd.concat(parts, ignore_index=True)
        df["far"] = df["distance_bucket"].isin(FAR)
        df["up"] = df["region"].str.startswith("up")
        df["down"] = df["region"].str.startswith("down")
        df["whiff"] = df["description"].isin(lr.WHIFFS)
        df["in_play"] = df["description"] == "hit_into_play"
        self.df = df
        self.zone = base[(base["is_analyzable"] == 1) & (base["is_in_zone"] == 1)]
        self.boards = {int(p.stem[-4:]): pd.read_csv(p)
                       for p in sorted(XCHASE.glob("xchase_leaderboard_20??.csv"))}
        self.action = pd.read_csv(XCHASE / "coaching" / "actionability_2026.csv")
        self.players = players
        self.ids = {p["name"]: p["id"] for p in players}

    def me(self, name, year=2026):
        return self.df[(self.df["batter"] == self.ids[name]) & (self.df["game_year"] == year)]

    def league(self, year=2026):
        return self.df[self.df["game_year"] == year]

    def pa(self, name, year=2026):
        b = self.boards[year]
        return float(b.loc[b["batter"] == self.ids[name], "plate_appearances"].iloc[0])

    def xchase(self, name, year):
        b = self.boards[year]
        r = b[b["batter"] == self.ids.get(name, -1)]
        if r.empty:
            r = b[b["player"] == name]
        return float(r["xchase_plus"].iloc[0])

    def net(self, frame, name, year=2026):
        return (frame["choices"].sum() + frame["contact"].sum()) * 600 / self.pa(name, year)

    def choices(self, frame, name, year=2026):
        return frame["choices"].sum() * 600 / self.pa(name, year)


def pct(v, quoted):
    return abs(100 * v - quoted) <= 0.75, f"{100 * v:.1f}%"


def about(v, quoted, tol=0.75):
    return abs(v - quoted) <= tol, f"{v:+.2f}"


def xwoba(v, quoted):
    return abs(v - quoted) <= 0.0015, f"{v:.4f}"


def holds(ok, shown):
    return bool(ok), shown


def every_count(frame):
    gaps = frame.groupby("count_group").apply(lambda g: g["is_chase"].mean() - g["e"].mean(),
                                              include_groups=False)
    return holds(len(gaps) == 4 and (gaps > 0).all(), " ".join(f"{k} {v:+.2f}" for k, v in gaps.items()))


# --------------------------------------------------
# THE CLAIMS, NOTE BY NOTE
# --------------------------------------------------

def soft(f):
    return f["pitch_group"].isin(["breaking", "offspeed"])


COUNT_KEYS = {"first": "first pitch", "ahead": "ahead", "even": "0-1 or 1-1", "two": "two strikes"}
HAND_KEYS = {"R": "right-handers", "L": "left-handers"}


def plan_pitches(player):
    return [it for it in player["plan_items"] if it["kind"] == "pitch"]


def first_sentence_names(note, player):
    """The note's first sentence names the plan's first line in the plan's
    own words: the count, the pitch and its side of the zone as the line
    prints them, and the pitcher hand when the line names one (and none
    when it does not)."""

    first = plan_pitches(player)[0]
    lk = player["leaks"]["all"][first["n"] - 1]
    sentence = note.split(". ")[0].lower()
    line = first["text"].lower()
    what = re.match(r"[^,]+, (?:let )?(.+?) (?:go\.|are one)", line).group(1)
    count = COUNT_KEYS[lk["count_group"]]
    missing = [w for w in (count, what) if w not in sentence or w not in line]
    if lk["hand"]:
        if HAND_KEYS[lk["hand"]] not in sentence:
            missing.append(HAND_KEYS[lk["hand"]])
    elif "right-hand" in sentence or "left-hand" in sentence:
        missing.append("no hand (the line names none)")
    return holds(not missing, "missing: " + ", ".join(missing) if missing else f"{count}; {what}")


def claims(d):
    p = {x["name"]: x for x in d.players}
    easiest = [n for n, (group, *_) in NOTED.items() if group == "easiest"]
    out = []

    def add(name, text, result):
        out.append((name, text, *result))

    def line_cell(name, k):
        pitches = plan_pitches(p[name])
        return tuple(pitches[k]["cell"]) if len(pitches) > k else None

    def second_line(name, text, cell):
        add(name, text, holds(line_cell(name, 1) == cell, str(line_cell(name, 1))))

    def biggest_leak(name, text):
        top = p[name]["leaks"]["all"][0]
        add(name, text, holds(line_cell(name, 0) == (top["count_group"], top["pitch_group"], top["region"]),
                              f"leak 1 is {top['phrase']}"))

    # Every note: its first sentence is the plan's first line
    for name, (_, note, _) in NOTED.items():
        add(name, "the first sentence names the plan's first line: count, pitch, side and hand",
            first_sentence_names(note, p[name]))

    # Salvador Pérez
    add("Salvador Pérez", "these chases turn out better than the league's",
        holds(p["Salvador Pérez"]["contact"] > 0, f"{p['Salvador Pérez']['contact']:+.1f}"))
    add("Salvador Pérez", "which softens every leak but erases none",
        holds(all(lk["contact"] > 0 and lk["choices"] + lk["contact"] < 0
                  for lk in p["Salvador Pérez"]["leaks"]["all"]), "per-leak contact and net"))
    m = d.me("Salvador Pérez")
    pre2k = d.net(m[(m["strikes"] < 2) & (m["pitch_group"] == "breaking")], "Salvador Pérez")
    two = d.net(m[(m["strikes"] == 2) & (m["pitch_group"] == "breaking")], "Salvador Pérez")
    add("Salvador Pérez", "at 0-1 or 1-1, breaking balls below the zone first: before two strikes they cost more",
        holds(pre2k < two, f"before two strikes {pre2k:+.1f}, with two {two:+.1f}"))

    # Michael Harris
    m = d.me("Michael Harris")
    rhp = d.net(m[(m["strikes"] == 2) & soft(m) & m["down"] & (m["p_throws"] == "R")], "Michael Harris")
    share = rhp / d.net(m, "Michael Harris")
    add("Michael Harris", "the breaking balls, changeups and splitters below the zone that right-handers "
        "throw him with two strikes are about half of what his chases cost him",
        holds(0.4 <= share <= 0.6, f"{share:.0%}"))
    second_line("Michael Harris", "the changeups and splitters among them are the plan's second line",
                ("two", "offspeed", "down"))
    rank = sorted((-p[n]["contact"], n) for n in easiest).index(
        (-p["Michael Harris"]["contact"], "Michael Harris")) + 1
    add("Michael Harris", "his contact is among the best in this group", holds(rank <= 2, f"rank {rank}"))

    # Ernie Clement
    m = d.me("Ernie Clement")
    lg = d.league()
    sel = lambda f: f[(f["strikes"] < 2) & (f["pitch_group"] == "fastball") & f["up"] & (f["is_chase"] == 1)]  # noqa: E731
    mine, theirs = sel(m), sel(lg)
    add("Ernie Clement", "before two strikes he puts 44% of his chased fastballs above the zone in play",
        pct(mine["in_play"].mean(), 44))
    add("Ernie Clement", "(league 18%)", pct(theirs["in_play"].mean(), 18))
    bip = lambda f: f.loc[f["in_play"], "estimated_woba_using_speedangle"].mean()  # noqa: E731
    add("Ernie Clement", "weak contact (.173 xwOBA", xwoba(bip(mine), 0.173))
    add("Ernie Clement", "vs .283)", xwoba(bip(theirs), 0.283))

    # Angel Martínez
    m = d.me("Angel Martínez")
    k = m[(m["strikes"] == 2) & soft(m) & m["down"]]
    r, l_ = d.net(k[k["p_throws"] == "R"], "Angel Martínez"), d.net(k[k["p_throws"] == "L"], "Angel Martínez")
    add("Angel Martínez", "more of what they cost him comes from right-handers than from left-handers",
        holds(r < 0 and r < l_, f"vs RHP {r:+.1f}, vs LHP {l_:+.1f}"))
    second_line("Angel Martínez", "then changeups and splitters below the zone", ("two", "offspeed", "down"))
    add("Angel Martínez", "the contact is there", holds(p["Angel Martínez"]["contact"] > 0,
                                                       f"{p['Angel Martínez']['contact']:+.1f}"))

    # Ceddanne Rafaela
    for year, q in ((2024, 35), (2025, 28)):
        m = d.me("Ceddanne Rafaela", year)
        add("Ceddanne Rafaela", f"early-count chasing {q}% of far-off pitches in {year}",
            pct(m.loc[m["far"] & (m["strikes"] < 2), "is_chase"].mean(), q))
    lg = d.league()
    add("Ceddanne Rafaela", "well above the league's 17%",
        pct(lg.loc[lg["far"] & (lg["strikes"] < 2), "is_chase"].mean(), 17))
    a = d.action.loc[d.action["batter"] == d.ids["Ceddanne Rafaela"], "decision_A_early_far"].iloc[0]
    add("Ceddanne Rafaela", "and costs about 4 runs", about(a, -4))

    # José Caballero
    for year, q in ((2024, 55), (2025, 65), (2026, 77)):
        m = d.me("José Caballero", year)
        f = m[(m["strikes"] == 2) & (m["pitch_group"] == "fastball") & (m["region"] == "up") & m["far"]]
        add("José Caballero", f"chased {q}% of the far-off fastballs above the zone with two strikes in {year}",
            pct(f["is_chase"].mean(), q))
    second_line("José Caballero", "then breaking balls below the zone", ("two", "breaking", "down"))
    add("José Caballero", "in 2025, when his xChase+ was 109", about(d.xchase("José Caballero", 2025), 109, 0.5))

    # Ozzie Albies
    m = d.me("Ozzie Albies")
    biggest_leak("Ozzie Albies", "the plan's first line and his biggest leak")
    add("Ozzie Albies", "he chases them in every count",
        every_count(m[(m["pitch_group"] == "offspeed") & m["down"]]))
    second_line("Ozzie Albies", "at 0-1 or 1-1 they are the plan's second line", ("even", "offspeed", "down"))
    f = m[(m["pitch_group"] == "offspeed") & m["down"]]
    gap = {h: g["is_chase"].mean() - g["e"].mean() for h, g in f.groupby("p_throws")}
    add("Ozzie Albies", "from both hands", holds(min(gap.values()) > 0.15, " ".join(f"{h} {v:+.2f}" for h, v in gap.items())))
    f = m[m["far"] & (m["p_throws"] == "L")]
    add("Ozzie Albies", "against left-handers he chases far-off pitches 35%", pct(f["is_chase"].mean(), 35))
    add("Ozzie Albies", "vs 19%", pct(f["e"].mean(), 19))

    # Luis García
    m = d.me("Luis García")
    add("Luis García", "with three balls his choices cost about 5 runs",
        about(d.choices(m[m["balls"] == 3], "Luis García"), -5))
    add("Luis García", "three-ball counts sit inside it (ahead in the count)",
        holds(line_cell("Luis García", 0)[0] == "ahead", str(line_cell("Luis García", 0))))
    f = m[(m["strikes"] == 2) & (m["pitch_group"] == "fastball") & (m["region"] == "up")]
    add("Luis García", "with two strikes he chases nine fastballs above the zone in ten",
        holds(0.85 <= f["is_chase"].mean() <= 0.95, f"{f['is_chase'].mean():.0%}"))
    f = m[(m["strikes"] == 2) & (m["pitch_group"] == "fastball") & m["up"]]
    add("Luis García", "but his contact there pays for it", holds(d.net(f, "Luis García") > 0,
                                                                 f"{d.net(f, 'Luis García'):+.1f}"))

    # Hunter Goodman
    m = d.me("Hunter Goodman")
    f = m[(m["strikes"] < 2) & (m["pitch_group"] == "breaking") & m["down"]]
    add("Hunter Goodman", "across every count before two strikes, he chases them 48%", pct(f["is_chase"].mean(), 48))
    add("Hunter Goodman", "vs 30%", pct(f["e"].mean(), 30))
    add("Hunter Goodman", "about 5 runs)", about(d.net(f, "Hunter Goodman"), -5))
    f = m[(m["strikes"] < 2) & (m["pitch_group"] == "fastball") & m["up"]]
    add("Hunter Goodman", "fastballs above the zone before two strikes: his contact nearly pays for them",
        holds(-1.5 <= d.net(f, "Hunter Goodman") < 0, f"{d.net(f, 'Hunter Goodman'):+.1f}"))
    f = m[(m["strikes"] == 2) & (m["pitch_group"] == "breaking") & m["down"]]
    second_line("Hunter Goodman", "the two-strike breaking ball, the plan's second line", ("two", "breaking", "down"))
    add("Hunter Goodman", "the two-strike breaking ball may be contact as much as choice",
        holds(f["contact"].sum() < 0, f"contact {f['contact'].sum() * 600 / d.pa('Hunter Goodman'):+.1f}"))

    # Mickey Moniak
    second_line("Mickey Moniak", "the second line, breaking balls below the zone with two strikes against "
                "right-handers", ("two", "breaking", "down"))
    pitches = plan_pitches(p["Mickey Moniak"])
    costs = [p["Mickey Moniak"]["leaks"]["all"][it["n"] - 1]["choices"] for it in pitches]
    add("Mickey Moniak", "is the bigger leak", holds(costs[1] < costs[0], " vs ".join(f"{c:+.1f}" for c in costs)))

    # Ezequiel Tovar
    m = d.me("Ezequiel Tovar")
    add("Ezequiel Tovar", "breaking balls ... below the zone are a take in every count",
        every_count(m[(m["pitch_group"] == "breaking") & m["down"]]))
    second_line("Ezequiel Tovar", "with two strikes, changeups and splitters below the zone are the plan's "
                "second line", ("two", "offspeed", "down"))
    add("Ezequiel Tovar", "the fastball decisions are fine",
        holds(d.choices(m[m["pitch_group"] == "fastball"], "Ezequiel Tovar") > -1,
              f"{d.choices(m[m['pitch_group'] == 'fastball'], 'Ezequiel Tovar'):+.1f}"))

    # Andrés Giménez
    for year, q in ((2022, 69), (2023, 74), (2024, 95), (2025, 105), (2026, 67)):
        add("Andrés Giménez", f"xChase+ {q} in {year}", about(d.xchase("Andrés Giménez", year), q, 0.5))
    m = d.me("Andrés Giménez")
    nets = {g: d.net(f, "Andrés Giménez") for g, f in m.groupby("count_group")}
    add("Andrés Giménez", "his biggest net loss by count is at 0-1 and 1-1",
        holds(min(nets, key=nets.get) == "even", " ".join(f"{g} {v:+.1f}" for g, v in nets.items())))
    groups = [lk["count_group"] for lk in p["Andrés Giménez"]["leaks"]["all"]]
    add("Andrés Giménez", "where none of his three biggest leaks sits, which is why the plan starts with two strikes",
        holds("even" not in groups and line_cell("Andrés Giménez", 0)[0] == "two", " ".join(groups)))
    second_line("Andrés Giménez", "then breaking balls below the zone", ("two", "breaking", "down"))

    # Jarren Duran, Colson Montgomery
    m = d.me("Jarren Duran")
    w = m.loc[m["is_chase"] == 1, "whiff"].mean()
    add("Jarren Duran", "six chases in ten are misses", holds(round(w * 10) == 6, f"{w:.1%}"))
    add("Jarren Duran", "breaking balls below the zone against right-handers",
        holds(all(lk["share_rhp"] >= 0.8 for lk in p["Jarren Duran"]["leaks"]["all"]
                  if lk["region"].startswith("down")), "down leaks' RHP share"))
    m = d.me("Colson Montgomery")
    w = m.loc[m["is_chase"] == 1, "whiff"].mean()
    add("Colson Montgomery", "two chases in three are misses", holds(abs(w - 2 / 3) <= 0.03, f"{w:.1%}"))
    f = m[(m["count_group"] == "ahead") & (m["pitch_group"] == "breaking") & m["down"]]
    add("Colson Montgomery", "start with the breaking ball below the zone when he is ahead",
        holds(d.choices(f, "Colson Montgomery") < -1, f"{d.choices(f, 'Colson Montgomery'):+.1f}"))
    second_line("Colson Montgomery", "with two strikes, the same pitch is the plan's second line",
                ("two", "breaking", "down"))

    # Zach Neto
    first = p["Zach Neto"]["leaks"]["all"][plan_pitches(p["Zach Neto"])[0]["n"] - 1]
    add("Zach Neto", "the plan's first line, from either hand", holds(first["hand"] is None, f"{first['share_rhp']:.0%} RHP"))
    for year, q in ((2024, None), (2025, None), (2026, 290)):
        m = d.me("Zach Neto", year)
        f = m[m["pitch_type"].isin(["SL", "ST"]) & m["down"] & (m["p_throws"] == "R")]
        if q is None:
            add("Zach Neto", f"he chased them well above league in {year}",
                holds(f["is_chase"].mean() - f["e"].mean() >= 0.04,
                      f"{f['is_chase'].mean():.0%} vs {f['e'].mean():.0%}"))
        else:
            add("Zach Neto", "pitchers threw him far more (290", holds(len(f) == q, str(len(f))))
    m = d.me("Zach Neto", 2024)
    n24 = len(m[m["pitch_type"].isin(["SL", "ST"]) & m["down"] & (m["p_throws"] == "R")])
    add("Zach Neto", "up from 184)", holds(n24 == 184, str(n24)))
    m = d.me("Zach Neto")
    add("Zach Neto", "the fastball decisions are a strength",
        holds(d.choices(m[m["pitch_group"] == "fastball"], "Zach Neto") > 0,
              f"{d.choices(m[m['pitch_group'] == 'fastball'], 'Zach Neto'):+.1f}"))

    # Oswald Peraza
    m = d.me("Oswald Peraza")
    t = m[m["balls"] == 3]
    add("Oswald Peraza", "three-ball counts: 62% chase", pct(t["is_chase"].mean(), 62))
    add("Oswald Peraza", "against about 40%", about(t["e"].mean(), 0.40, 0.03))
    add("Oswald Peraza", "about 5 runs", about(d.net(t, "Oswald Peraza"), -5))
    add("Oswald Peraza", "in 45 pitches", holds(len(t) == 45, str(len(t))))
    biggest_leak("Oswald Peraza", "the plan's first line and his biggest leak")
    second_line("Oswald Peraza", "the second line is breaking balls down and away from right-handers",
                ("two", "breaking", "down-away"))
    smallest = min(p[n]["pa"] for n in NOTED)
    add("Oswald Peraza", "fewest plate appearances of the 17", holds(p["Oswald Peraza"]["pa"] == smallest,
                                                             f"{p['Oswald Peraza']['pa']} PA"))

    # Jeremy Peña
    m = d.me("Jeremy Peña")
    f = m[(m["strikes"] == 2) & (m["pitch_group"] == "breaking") & m["region"].str.contains("away")]
    add("Jeremy Peña", "the two-strike slider away from right-handers",
        holds((f["p_throws"] == "R").mean() >= 0.9 and f["pitch_type"].isin(["SL", "ST"]).mean() >= 0.7,
              f"RHP {(f['p_throws'] == 'R').mean():.0%}, sliders {f['pitch_type'].isin(['SL', 'ST']).mean():.0%}"))
    z = d.zone[d.zone["game_year"] == 2026]
    mine = z[z["batter"] == d.ids["Jeremy Peña"]]

    def zone_damage(f):
        bip = f[(f["is_swing"] == 1) & (f["description"] == "hit_into_play")]
        return f["is_swing"].mean(), bip["estimated_woba_using_speedangle"].mean()

    (ms, mx), (ls, lx) = zone_damage(mine), zone_damage(z)
    add("Jeremy Peña", "keep him swinging at strikes at the top of it",
        holds(ms > ls and mx > lx, f"swing {ms:.0%} vs {ls:.0%}, xwOBA {mx:.3f} vs {lx:.3f}"))
    takes = [it for it in p["Jeremy Peña"]["plan_items"] if it["kind"] == "pitch" and not it["video"]]
    add("Jeremy Peña", "the one clear take on his card", holds(len(takes) == 1, f"{len(takes)} take lines"))
    videos = [it for it in p["Jeremy Peña"]["plan_items"] if it["kind"] == "pitch" and it["video"]]
    add("Jeremy Peña", "the breaking ball below the zone at 0-1 or 1-1 ... a video item",
        holds(any(tuple(it["cell"]) == ("even", "breaking", "down") for it in videos), "plan video items"))
    f = m[(m["pitch_group"] == "fastball") & m["up"]]
    c, ch = f["contact"].sum(), f["choices"].sum()
    add("Jeremy Peña", "his contact pays for most of his chases on fastballs above the zone",
        holds(c > 0 and c >= 0.5 * -ch, f"contact {c * 600 / d.pa('Jeremy Peña'):+.1f} vs choices "
              f"{ch * 600 / d.pa('Jeremy Peña'):+.1f}"))
    return out


def check(players):
    """Every claim in the notes, tested. Returns the number checked;
    raises SystemExit listing the ones that fail."""

    missing = [n for n in NOTED if n not in {p["name"] for p in players}]
    if missing:
        raise SystemExit(f"Noted hitters missing from the cards: {missing}")
    # The note's starting leak must be on the card and lead the plan, so
    # the player's first line and the staff's first sentence agree.
    by_name = {p["name"]: p for p in players}
    for name, (_, _, start) in NOTED.items():
        p = by_name[name]
        cells = [(lk["count_group"], lk["pitch_group"], lk["region"]) for lk in p["leaks"]["all"]]
        if tuple(start) not in cells:
            raise SystemExit(f"{name}: the note's starting leak {start} is not among the card's "
                             f"leaks {cells} (scripts/coach_notes.py)")
        first = next((it for it in p["plan_items"] if it["kind"] == "pitch"), None)
        if first is None or tuple(first["cell"]) != tuple(start):
            raise SystemExit(f"{name}: the plan's first pitch line is "
                             f"{first and first['cell']}, not the note's {start}")
    results = claims(Data(players))
    failed = [r for r in results if not r[2]]
    if failed:
        lines = [f"  {name}: \"{text}\" -> data says {shown}" for name, text, ok, shown in failed]
        raise SystemExit(f"{len(failed)} of {len(results)} claims in the coach's notes no longer "
                         "hold (scripts/coach_notes.py):\n" + "\n".join(lines))
    covered = {name for name, *_ in results}
    return len(results) + len(NOTED), len(covered)
