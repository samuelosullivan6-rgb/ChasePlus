"""
Step 18: the decision surfaces in 3D, as still images.

The player cards (step 17) draw each hitter's chase decisions as a flat
picture. Here the same surfaces are lifted into a terrain: the floor is
the plate area from the catcher's view, and height is the swing rate.
The flat card is still where the numbers are read; the terrain is for
seeing the shape at a glance (in the README and the video).

  terrain_average_rhb_<theme>.png
      the average right-handed hitter in each count group: how the walls
      of chasing rise around the zone as the count moves on
  terrain_<hitter>_<theme>.png
      one hitter's costliest panel (the count group and side of their
      biggest leak), colored by the gap to the average hitter, over a gray
      color for the gap to the average hitter on the same pitches (the
      interactive page also draws that average hitter as a mesh, which
      matplotlib cannot depth-sort against a surface)

Reads data/cleaned/card_pitches_<season>.parquet and
card_players_<season>.json, which step 17 writes. Uses the same smoothing
(card_surfaces.py) and colors (card_style.py) as the cards, so a terrain
and its flat picture are the same numbers.

Options: --season (default 2026), --players NAME [NAME ...] (default:
Salvador Pérez, the README example).
"""

import argparse
import json
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import card_surfaces as cs  # noqa: E402
from card_style import THEMES, diverging, hex_rgb, sequential  # noqa: E402

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
CLEAN = PROJECT_DIR / "data" / "cleaned"
OUT = PROJECT_DIR / "results" / "xchase" / "player_cards" / "terrain"

parser = argparse.ArgumentParser(description="3D chase terrain figures.")
parser.add_argument("--season", type=int, default=2026)
parser.add_argument("--players", nargs="*", default=["Salvador Pérez"])
args = parser.parse_args()

pitches = pd.read_parquet(CLEAN / f"card_pitches_{args.season}.parquet")
meta = json.loads((CLEAN / f"card_players_{args.season}.json").read_text())
players = {p["name"]: p for p in meta["players"]}
AVERAGE_ZONE = meta["average_zone"]

XS, ZS = cs.grid()
GX, GZ = np.meshgrid(XS, ZS)
COUNT_LABELS = {"first": "First pitch", "ahead": "Ahead in the count",
                "even": "Even or behind", "two": "Two strikes"}
COUNT_DETAIL = {"first": "0-0", "ahead": "1-0  2-0  3-0  2-1  3-1",
                "even": "0-1  1-1", "two": "0-2  1-2  2-2  3-2"}
REGION_WORDS = {"up": "above the zone", "down": "below the zone", "in": "inside",
                "away": "away", "up-in": "up and in", "up-away": "up and away",
                "down-in": "down and in", "down-away": "down and away"}
PITCH_WORDS = {"fastball": "fastballs", "breaking": "breaking balls",
               "offspeed": "changeups and splitters"}

W, H, DPI = 1920, 1080, 100
FONT = ["Avenir Next", "Helvetica Neue", "Arial", "DejaVu Sans"]
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": FONT,
                     "axes.unicode_minus": True})


def px(p):
    return p * 72 / DPI


def slug(name):
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return "".join(c if c.isalnum() else "_" for c in plain.lower()).strip("_")


def style_axes(ax, t, zlabel, elev=34, zoom=1.0):
    for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
        axis.set_pane_color((0, 0, 0, 0))
        axis._axinfo["grid"].update(color=hex_rgb(t["hair"]), linewidth=0.6)
        axis.line.set_color(t["axis"])
    ax.tick_params(colors=t["muted"], labelsize=px(12), pad=0)
    ax.set_xlim(XS[0], XS[-1])
    ax.set_ylim(ZS[0], ZS[-1])
    ax.set_zlim(0, 100)
    ax.set_xticks([-2, -1, 0, 1, 2])
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_zticks([0, 25, 50, 75, 100])
    ax.set_zticklabels(["0%", "", "50%", "", "100%"])
    ax.set_xlabel("catcher's view, ft", color=t["muted"], fontsize=px(13), labelpad=2)
    ax.set_ylabel("height, ft", color=t["muted"], fontsize=px(13), labelpad=2)
    ax.set_zlabel(zlabel, color=t["muted"], fontsize=px(13), labelpad=0)
    ax.set_box_aspect((XS[-1] - XS[0], ZS[-1] - ZS[0], 3.2), zoom=zoom)
    ax.view_init(elev=elev, azim=-62)


def rim_height(height, mask):
    """Average height of the terrain just outside the zone, in %."""
    from scipy.ndimage import binary_dilation
    ring = binary_dilation(mask, iterations=2) & ~mask
    return float(np.nanmean(np.where(ring, height, np.nan)))


def floor(ax, t, zone, rim):
    """The zone outlined at the crater's rim, on posts from the ground, so
    the hole in the terrain lines up with it; home plate on the ground."""
    x = [-0.83, 0.83, 0.83, -0.83, -0.83]
    z = [zone[0], zone[0], zone[1], zone[1], zone[0]]
    ax.plot(x, z, [rim] * 5, color=t["ink"], lw=px(2), zorder=10)
    for cx, cz in zip(x[:4], z[:4]):
        ax.plot([cx, cx], [cz, cz], [0, rim], color=t["ink2"], lw=px(1), alpha=0.6, zorder=10)
    ax.plot([-0.708, 0.708], [0, 0], [0, 0], color=t["axis"], lw=px(5), zorder=10)


def surface(ax, height, colors, t):
    """height in %, NaN where nothing is drawn; colors (rows, cols, 3)."""
    z = np.ma.masked_invalid(height)
    rgba = np.concatenate([colors, np.ones(colors.shape[:2] + (1,))], axis=-1)
    rgba[np.isnan(height)] = 0
    ax.plot_surface(GX, GZ, z, facecolors=rgba, rstride=1, cstride=1, linewidth=0,
                    antialiased=False, shade=False)


def figure(t):
    fig = plt.figure(figsize=(W / DPI, H / DPI), dpi=DPI)
    fig.patch.set_facecolor(t["surface"])
    return fig


def text(fig, x, y, s, t, size=18, color="ink", weight="normal", ha="left"):
    fig.text(x / W, 1 - y / H, s, fontsize=px(size), color=t.get(color, color),
             fontweight=weight, ha=ha, va="baseline")


# --------------------------------------------------
# THE AVERAGE HITTER, ALL FOUR COUNT GROUPS
# --------------------------------------------------

def average_terrain(theme):
    t = THEMES[theme]
    lg = pitches[pitches["stand"] == "R"]
    zone = AVERAGE_ZONE["R"]
    mask = cs.in_zone_mask(XS, ZS, *zone)
    fig = figure(t)
    text(fig, 64, 76, "The average right-handed hitter's chase terrain", t, 40, weight="bold")
    text(fig, 64, 118, "Height and color are how often a pitch outside the zone gets a swing. "
         "The walls rise with every strike and are steepest right next to the zone.", t, 20, "ink2")
    peaks = {}
    for k, g in enumerate(["first", "ahead", "even", "two"]):
        frame = lg[lg["count_group"] == g]
        s = cs.surface(frame["xq"] / 100, frame["zq_avg"] / 100, frame["is_chase"].to_numpy(float),
                       np.zeros(len(frame)), XS, ZS)
        rate = np.where(mask | (s["weight"] < 5), np.nan, s["player_rate"])
        peaks[g] = np.nanmax(rate)
        ax = fig.add_axes([0.01 + k * 0.245, 0.06, 0.245, 0.78], projection="3d")
        ax.set_facecolor(t["surface"])
        surface(ax, rate * 100, sequential(np.nan_to_num(rate), t), t)
        floor(ax, t, zone, rim_height(rate * 100, mask))
        style_axes(ax, t, "chase rate")
        cx = (0.01 + k * 0.245 + 0.1225) * W
        text(fig, cx, 196, COUNT_LABELS[g], t, 20, weight="bold", ha="center")
        text(fig, cx, 222, f"{COUNT_DETAIL[g]}   ·   peak {peaks[g] * 100:.0f}%", t, 14,
             "muted", ha="center")
    text(fig, 64, H - 26, "Catcher's view, around the average right-handed hitter's zone "
         f"(outlined at the rim of the hole in the middle); the bar is home plate. Statcast {args.season}, "
         f"{len(lg):,} pitches outside the zone.", t, 13, "muted")
    path = OUT / f"terrain_average_rhb_{theme}.png"
    fig.savefig(path, dpi=DPI, facecolor=t["surface"])
    plt.close(fig)
    return path


# --------------------------------------------------
# ONE HITTER'S COSTLIEST PANEL
# --------------------------------------------------

def hitter_terrain(name, theme):
    t = THEMES[theme]
    p = players[name]
    leak = p["leaks"]["all"][0] if p["leaks"]["all"] else None
    group = leak["count_group"] if leak else "two"
    side = leak["side"] if leak else (p["bats"] if p["bats"] != "S" else "L")
    frame = pitches[(pitches["batter"] == p["id"]) & (pitches["count_group"] == group)
                    & (pitches["stand"] == side)]
    s = cs.surface(frame["xq"] / 100, frame["zq"] / 100, frame["is_chase"].to_numpy(float),
                   frame["e_match_q"].to_numpy(float) / 255, XS, ZS)
    mask = cs.in_zone_mask(XS, ZS, *p["zone"])
    hide = mask | (s["evidence"] < 0.25) | ~np.isfinite(s["league_rate"])
    league = np.where(hide, np.nan, s["league_rate"])
    you = np.where(hide, np.nan, np.clip(s["league_rate"] + s["gap"], 0, 1))

    fig = figure(t)
    ax = fig.add_axes([0.30, 0.02, 0.70, 0.96], projection="3d")
    ax.set_facecolor(t["surface"])
    surface(ax, you * 100, diverging(np.nan_to_num(s["gap"]), t), t)
    floor(ax, t, p["zone"], rim_height(you * 100, mask))
    style_axes(ax, t, "swing rate", elev=52, zoom=0.95)

    # the strongest point, where the evidence is solid
    solid = np.where(hide | (s["evidence"] < 0.6), -np.inf, s["gap"])
    j = np.unravel_index(np.argmax(solid), solid.shape)
    peak_you, peak_avg = you[j], league[j]

    where = (f"{PITCH_WORDS[leak['pitch_group']]} {REGION_WORDS[leak['region']]}"
             if leak else "pitches outside the zone")
    text(fig, 64, 86, name, t, 44, weight="bold")
    text(fig, 64, 128, f"{COUNT_LABELS[group]}, batting {'right' if side == 'R' else 'left'}", t, 22, "ink2")
    y = 210
    lines = [
        "Height is how often each pitch outside the zone",
        "gets a swing. Color is the gap to the average",
        "hitter on the same pitches: red is more swings,",
        "blue is fewer, gray is about average.",
    ]
    for ln in lines:
        text(fig, 64, y, ln, t, 18, "ink2")
        y += 28
    y += 30
    text(fig, 64, y, "WHERE THE GAP IS BIGGEST", t, 13, "muted", weight="bold")
    text(fig, 64, y + 56, f"{peak_you * 100:.0f}%", t, 52, weight="bold")
    text(fig, 64, y + 92, f"swing rate, against {peak_avg * 100:.0f}% for the average hitter", t, 17, "ink2")
    if leak:
        y += 150
        text(fig, 64, y, "BIGGEST LEAK", t, 13, "muted", weight="bold")
        text(fig, 64, y + 32, f"{COUNT_LABELS[group]}, {where}", t, 18)
        text(fig, 64, y + 60, f"{leak['rate'] * 100:.0f}% swings vs {leak['league'] * 100:.0f}% for the "
             f"average hitter, {abs(leak['choices']):.1f} runs per 600 PA", t, 15, "ink2")
    text(fig, 64, H - 26, "Catcher's view, around the hitter's own zone (outlined at the rim of the hole in the middle); "
         f"the bar is home plate. Statcast {args.season}. The interactive page adds the average hitter "
         "as a mesh; the flat card has the numbers.", t, 13, "muted")
    path = OUT / f"terrain_{slug(name)}_{theme}.png"
    fig.savefig(path, dpi=DPI, facecolor=t["surface"])
    plt.close(fig)
    return path


OUT.mkdir(parents=True, exist_ok=True)
written = []
for theme in THEMES:
    written.append(average_terrain(theme))
    for name in args.players:
        if name not in players:
            print(f"  not a qualified {args.season} hitter, skipped: {name}")
            continue
        written.append(hitter_terrain(name, theme))
for path in written:
    print(f"  wrote {path.relative_to(PROJECT_DIR)}")
