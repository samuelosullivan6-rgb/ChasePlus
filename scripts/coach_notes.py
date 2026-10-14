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
# note condensed from those reports. Everything else on their cards is
# computed, the same as for every other hitter.
NOTED = {
    # Easiest to improve (step 13): decision-only, persistent pattern
    "Salvador Pérez": ("easiest", "Volume, not contact: these chases turn out better than the league's, which softens every leak but erases none. Start with breaking balls before two strikes, where the take costs nothing in strikeouts."),
    "Michael Harris": ("easiest", "One pitch type: soft stuff below the zone with two strikes, mostly from right-handers, about half his net loss. His contact is among the best in this group, so nothing else needs to change."),
    "Ernie Clement": ("easiest", "The high fastball before two strikes. He puts 44% of those chases in play (league 18%), so it never looks like a mistake, but it is weak contact (.173 xwOBA vs .283) that gives away a hitter's count."),
    "Angel Martínez": ("easiest", "Two strikes, right-hander, soft stuff that starts at the knees: take it. The contact is there on the swings that stay."),
    "Ceddanne Rafaela": ("easiest", "The high fastball with two strikes first. His early-count chasing came down in 2025 (35% to 28% of far-off pitches) but is still well above the league's 17% and costs about 4 runs; it is next."),
    "José Caballero": ("easiest", "One pitch with two strikes: the fastball above the belt. He has chased more of the far-off ones every year (55%, 65%, 77% since 2024), even in 2025, when his xChase+ was 109."),
    "Ozzie Albies": ("easiest", "Changeups and splitters that dive below the knees, in every count, from both hands. Against left-handers he chases far-off pitches of every kind more (35% vs 19%)."),
    "Luis García": ("easiest", "With three balls, swing only at strikes: that is the big one, about 5 runs. With two strikes he chases nine high fastballs in ten, but his contact there pays for it, so leave that pitch alone."),
    "Hunter Goodman": ("easiest", "The free part is the breaking ball below the zone before two strikes (48% vs 30%, about 5 runs). The high fastball looks worse than it is: his contact nearly pays for it. The two-strike breaking ball may be contact as much as choice."),
    # Biggest losses (step 12): the bottom 10 not already listed
    "Mickey Moniak": ("biggest", "Two separate leaks: high fastballs early, low breaking balls with two strikes. Fix the early one first; it costs nothing in strikeouts."),
    "Ezequiel Tovar": ("biggest", "Breaking balls that start at the knees and keep dropping are a take in every count, and the changeup below the zone is the second piece. The fastball decisions are fine."),
    "Andrés Giménez": ("biggest", "Not new: xChase+ 69 and 74 in 2022-23, then 95 and 105, and back to 67. Find out what made 2024-25 work before changing anything; the target is 0-1 and 1-1."),
    "Jarren Duran": ("biggest", "A contact problem: six chases in ten are misses. The two-strike take line should be stricter than league norms, especially below the knees against right-handers."),
    "Colson Montgomery": ("biggest", "A contact problem: two chases in three are misses, so a chase is close to a sure strike. Start by taking the first-strike pitch below the zone."),
    "Zach Neto": ("biggest", "Sliders below the zone from right-handers. He chased them well above league in 2024 and 2025 too; in 2026 pitchers threw him far more (290, up from 184). Sit fastball; the fastball decisions are a strength."),
    "Oswald Peraza": ("biggest", "Three-ball counts first: swing only at strikes (62% chase against about 40%, about 5 runs in 45 pitches). Then two-strike soft stuff down, the bigger loss. Smallest sample of the group."),
    "Jeremy Peña": ("biggest", "The first pitch, and the two-strike slider away from right-handers. Keep the aggression up in the zone; that is where the damage comes from."),
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


def claims(d):
    p = {x["name"]: x for x in d.players}
    easiest = [n for n, (group, _) in NOTED.items() if group == "easiest"]
    out = []

    def add(name, text, result):
        out.append((name, text, *result))

    # Salvador Pérez
    add("Salvador Pérez", "these chases turn out better than the league's",
        holds(p["Salvador Pérez"]["contact"] > 0, f"{p['Salvador Pérez']['contact']:+.1f}"))
    add("Salvador Pérez", "which softens every leak but erases none",
        holds(all(lk["contact"] > 0 and lk["choices"] + lk["contact"] < 0
                  for lk in p["Salvador Pérez"]["leaks"]["all"]), "per-leak contact and net"))
    m = d.me("Salvador Pérez")
    pre2k = d.net(m[(m["strikes"] < 2) & (m["pitch_group"] == "breaking")], "Salvador Pérez")
    two = d.net(m[(m["strikes"] == 2) & (m["pitch_group"] == "breaking")], "Salvador Pérez")
    add("Salvador Pérez", "start with breaking balls before two strikes",
        holds(pre2k < two, f"before two strikes {pre2k:+.1f}, with two {two:+.1f}"))

    # Michael Harris
    m = d.me("Michael Harris")
    rhp = d.net(m[(m["strikes"] == 2) & soft(m) & m["down"] & (m["p_throws"] == "R")], "Michael Harris")
    share = rhp / d.net(m, "Michael Harris")
    add("Michael Harris", "soft stuff below the zone with two strikes, mostly from right-handers, "
        "about half his net loss", holds(0.4 <= share <= 0.6, f"{share:.0%}"))
    rank = sorted((-p[n]["contact"], n) for n in easiest).index(
        (-p["Michael Harris"]["contact"], "Michael Harris")) + 1
    add("Michael Harris", "his contact is among the best in this group", holds(rank <= 2, f"rank {rank}"))

    # Ernie Clement
    m = d.me("Ernie Clement")
    lg = d.league()
    sel = lambda f: f[(f["strikes"] < 2) & (f["pitch_group"] == "fastball") & f["up"] & (f["is_chase"] == 1)]  # noqa: E731
    mine, theirs = sel(m), sel(lg)
    add("Ernie Clement", "he puts 44% of those chases in play", pct(mine["in_play"].mean(), 44))
    add("Ernie Clement", "(league 18%)", pct(theirs["in_play"].mean(), 18))
    bip = lambda f: f.loc[f["in_play"], "estimated_woba_using_speedangle"].mean()  # noqa: E731
    add("Ernie Clement", "weak contact (.173 xwOBA", xwoba(bip(mine), 0.173))
    add("Ernie Clement", "vs .283)", xwoba(bip(theirs), 0.283))

    # Angel Martínez
    m = d.me("Angel Martínez")
    k = m[(m["strikes"] == 2) & soft(m) & m["down"]]
    r, l_ = d.net(k[k["p_throws"] == "R"], "Angel Martínez"), d.net(k[k["p_throws"] == "L"], "Angel Martínez")
    add("Angel Martínez", "two strikes, right-hander, soft stuff that starts at the knees",
        holds(r < 0 and r < l_, f"vs RHP {r:+.1f}, vs LHP {l_:+.1f}"))
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
        add("José Caballero", f"chased {q}% of the far-off high fastballs with two strikes in {year}",
            pct(f["is_chase"].mean(), q))
    add("José Caballero", "in 2025, when his xChase+ was 109", about(d.xchase("José Caballero", 2025), 109, 0.5))

    # Ozzie Albies
    m = d.me("Ozzie Albies")
    add("Ozzie Albies", "changeups and splitters that dive below the knees, in every count",
        every_count(m[(m["pitch_group"] == "offspeed") & m["down"]]))
    f = m[(m["pitch_group"] == "offspeed") & m["down"]]
    gap = {h: g["is_chase"].mean() - g["e"].mean() for h, g in f.groupby("p_throws")}
    add("Ozzie Albies", "from both hands", holds(min(gap.values()) > 0.15, " ".join(f"{h} {v:+.2f}" for h, v in gap.items())))
    f = m[m["far"] & (m["p_throws"] == "L")]
    add("Ozzie Albies", "against left-handers he chases far-off pitches 35%", pct(f["is_chase"].mean(), 35))
    add("Ozzie Albies", "vs 19%", pct(f["e"].mean(), 19))

    # Luis García
    m = d.me("Luis García")
    add("Luis García", "with three balls ... about 5 runs", about(d.choices(m[m["balls"] == 3], "Luis García"), -5))
    f = m[(m["strikes"] == 2) & (m["pitch_group"] == "fastball") & (m["region"] == "up")]
    add("Luis García", "with two strikes he chases nine high fastballs in ten",
        holds(0.85 <= f["is_chase"].mean() <= 0.95, f"{f['is_chase'].mean():.0%}"))
    f = m[(m["strikes"] == 2) & (m["pitch_group"] == "fastball") & m["up"]]
    add("Luis García", "but his contact there pays for it", holds(d.net(f, "Luis García") > 0,
                                                                 f"{d.net(f, 'Luis García'):+.1f}"))

    # Hunter Goodman
    m = d.me("Hunter Goodman")
    f = m[(m["strikes"] < 2) & (m["pitch_group"] == "breaking") & m["down"]]
    add("Hunter Goodman", "the breaking ball below the zone before two strikes (48%", pct(f["is_chase"].mean(), 48))
    add("Hunter Goodman", "vs 30%", pct(f["e"].mean(), 30))
    add("Hunter Goodman", "about 5 runs)", about(d.net(f, "Hunter Goodman"), -5))
    f = m[(m["strikes"] < 2) & (m["pitch_group"] == "fastball") & m["up"]]
    add("Hunter Goodman", "his contact nearly pays for [the high fastball]",
        holds(-1.5 <= d.net(f, "Hunter Goodman") < 0, f"{d.net(f, 'Hunter Goodman'):+.1f}"))
    f = m[(m["strikes"] == 2) & (m["pitch_group"] == "breaking") & m["down"]]
    add("Hunter Goodman", "the two-strike breaking ball may be contact as much as choice",
        holds(f["contact"].sum() < 0, f"contact {f['contact'].sum() * 600 / d.pa('Hunter Goodman'):+.1f}"))

    # Mickey Moniak
    m = d.me("Mickey Moniak")
    early = d.net(m[(m["strikes"] < 2) & (m["pitch_group"] == "fastball") & m["up"]], "Mickey Moniak")
    late = d.net(m[(m["strikes"] == 2) & (m["pitch_group"] == "breaking") & m["down"]], "Mickey Moniak")
    add("Mickey Moniak", "two separate leaks: high fastballs early, low breaking balls with two strikes",
        holds(early < -1 and late < -1, f"early {early:+.1f}, two strikes {late:+.1f}"))

    # Ezequiel Tovar
    m = d.me("Ezequiel Tovar")
    add("Ezequiel Tovar", "breaking balls ... below the zone are a take in every count",
        every_count(m[(m["pitch_group"] == "breaking") & m["down"]]))
    add("Ezequiel Tovar", "the changeup below the zone is the second piece",
        holds(d.choices(m[(m["pitch_group"] == "offspeed") & m["down"]], "Ezequiel Tovar") < -2,
              f"{d.choices(m[(m['pitch_group'] == 'offspeed') & m['down']], 'Ezequiel Tovar'):+.1f}"))
    add("Ezequiel Tovar", "the fastball decisions are fine",
        holds(d.choices(m[m["pitch_group"] == "fastball"], "Ezequiel Tovar") > -1,
              f"{d.choices(m[m['pitch_group'] == 'fastball'], 'Ezequiel Tovar'):+.1f}"))

    # Andrés Giménez
    for year, q in ((2022, 69), (2023, 74), (2024, 95), (2025, 105), (2026, 67)):
        add("Andrés Giménez", f"xChase+ {q} in {year}", about(d.xchase("Andrés Giménez", year), q, 0.5))
    m = d.me("Andrés Giménez")
    nets = {g: d.net(f, "Andrés Giménez") for g, f in m.groupby("count_group")}
    add("Andrés Giménez", "the target is 0-1 and 1-1", holds(min(nets, key=nets.get) == "even",
                                                           " ".join(f"{g} {v:+.1f}" for g, v in nets.items())))

    # Jarren Duran, Colson Montgomery
    m = d.me("Jarren Duran")
    w = m.loc[m["is_chase"] == 1, "whiff"].mean()
    add("Jarren Duran", "six chases in ten are misses", holds(round(w * 10) == 6, f"{w:.1%}"))
    add("Jarren Duran", "below the knees against right-handers",
        holds(all(lk["share_rhp"] >= 0.8 for lk in p["Jarren Duran"]["leaks"]["all"]
                  if lk["region"].startswith("down")), "down leaks' RHP share"))
    m = d.me("Colson Montgomery")
    w = m.loc[m["is_chase"] == 1, "whiff"].mean()
    add("Colson Montgomery", "two chases in three are misses", holds(abs(w - 2 / 3) <= 0.03, f"{w:.1%}"))
    f = m[m["down"] & (m["strikes"] == 0)]
    add("Colson Montgomery", "taking the first-strike pitch below the zone",
        holds(d.choices(f, "Colson Montgomery") < -1, f"{d.choices(f, 'Colson Montgomery'):+.1f}"))

    # Zach Neto
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
    big = d.net(m[(m["strikes"] == 2) & soft(m) & m["down"]], "Oswald Peraza")
    add("Oswald Peraza", "then two-strike soft stuff down, the bigger loss",
        holds(big < d.net(t, "Oswald Peraza"), f"{big:+.1f}"))
    smallest = min(p[n]["pa"] for n in NOTED)
    add("Oswald Peraza", "smallest sample of the group", holds(p["Oswald Peraza"]["pa"] == smallest,
                                                             f"{p['Oswald Peraza']['pa']} PA"))

    # Jeremy Peña
    m = d.me("Jeremy Peña")
    add("Jeremy Peña", "the first pitch", holds(d.net(m[m["count_group"] == "first"], "Jeremy Peña") < -2,
                                               f"{d.net(m[m['count_group'] == 'first'], 'Jeremy Peña'):+.1f}"))
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
    add("Jeremy Peña", "keep the aggression up in the zone; that is where the damage comes from",
        holds(ms > ls and mx > lx, f"swing {ms:.0%} vs {ls:.0%}, xwOBA {mx:.3f} vs {lx:.3f}"))
    return out


def check(players):
    """Every claim in the notes, tested. Returns the number checked;
    raises SystemExit listing the ones that fail."""

    missing = [n for n in NOTED if n not in {p["name"] for p in players}]
    if missing:
        raise SystemExit(f"Noted hitters missing from the cards: {missing}")
    results = claims(Data(players))
    failed = [r for r in results if not r[2]]
    if failed:
        lines = [f"  {name}: \"{text}\" -> data says {shown}" for name, text, ok, shown in failed]
        raise SystemExit(f"{len(failed)} of {len(results)} claims in the coach's notes no longer "
                         "hold (scripts/coach_notes.py):\n" + "\n".join(lines))
    covered = {name for name, *_ in results}
    return len(results), len(covered)
