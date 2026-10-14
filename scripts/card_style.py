"""
Shared colors for the player cards (step 17) and the 3D terrain (step 18):
the project's chart palette in light and dark, and the OKLab arithmetic
behind the diverging (gap to league) and sequential (raw rate) scales.
templates/card_surfaces.js repeats the same scales for the HTML page.
"""

import numpy as np

import card_surfaces as cs

THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
              "hair": "#e1e0d9", "axis": "#c3c2b7", "mid": "#f0efec",
              "blue": "#2a78d6", "red": "#e34948", "league": "#898781",
              # raw chase rate, surface to deep red: the same red as "chases more"
              # on a player card, so the average card and a player card read alike
              "ramp": ["#fcfcfb", "#fbe1e0", "#f6bfbd", "#ef9c9a", "#e67775", "#d7514f", "#b83a39", "#8f2726"]},
    "dark": {"surface": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#898781",
             "hair": "#2c2c2a", "axis": "#383835", "mid": "#383835",
             "blue": "#3987e5", "red": "#e66767", "league": "#898781",
             "ramp": ["#1a1a19", "#4a1d1d", "#7a2a29", "#a83837", "#cf4f4e", "#e67775", "#f3a3a1", "#fbd0ce"]},
}


def hex_rgb(c):
    c = c.lstrip("#")
    return np.array([int(c[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def _lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _gam(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def to_oklab(rgb):
    r, g, b = np.moveaxis(_lin(np.asarray(rgb, float)), -1, 0)
    l = np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], -1)


def from_oklab(lab):
    L, a, b = np.moveaxis(lab, -1, 0)
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = np.stack([4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
                    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
                    -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s], -1)
    return _gam(rgb)


def diverging(values, theme):
    """Gray midpoint to blue (negative) or red (positive), in OKLab."""

    t = np.clip(values / cs.GAP_LIMIT, -1, 1)[..., None]
    mid = to_oklab(hex_rgb(theme["mid"]))
    pos = to_oklab(hex_rgb(theme["red"]))
    neg = to_oklab(hex_rgb(theme["blue"]))
    lab = np.where(t >= 0, mid + t * (pos - mid), mid + (-t) * (neg - mid))
    return from_oklab(lab)


def sequential(values, theme, top=0.7):
    stops = np.array([hex_rgb(c) for c in theme["ramp"]])
    lab = to_oklab(stops)
    t = np.clip(values / top, 0, 1) * (len(stops) - 1)
    lo = np.floor(t).astype(int).clip(0, len(stops) - 2)
    f = (t - lo)[..., None]
    return from_oklab(lab[lo] * (1 - f) + lab[lo + 1] * f)
