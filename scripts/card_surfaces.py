"""
Shared geometry and smoothing for the player decision cards (step 17).

Everything a card's zone picture shows comes from two functions here,
and templates/player_cards.html repeats the same arithmetic in
JavaScript so the interactive page and the static images agree. If you
change a constant or a formula here, change it there too; step 17 checks
the two against each other on one hitter every run.

COORDINATES (what the card draws)
  x  feet from the middle of the plate, from the catcher's view:
     negative = third-base side, positive = first-base side. Nobody is
     mirrored, so a left-handed batter's inside is on the right.
  z  feet above the ground, with the hitter's own strike zone drawn at
     its real height. Every card shares one scale, so a tall hitter's
     zone sits visibly higher than a short hitter's.
  The league comparison is still made relative to each hitter's own zone
  (step 17 fits it on plate_x_batter and plate_z_normalized), so nobody
  is judged on the height of their zone.

THE LEAGUE EXPECTATION (per pitch, built in step 17)
  For every out-of-zone pitch, the chance an average hitter swings at a
  pitch in that exact spot and count (and, for the "same matchup"
  baseline, the same batter side and pitcher hand). Fit on the whole
  league, then calibrated so it adds up exactly to the league's chase
  rate in each count x distance cell that step 04 prices against.

THE PLAYER SURFACE
  At each point g on the grid, with Gaussian weights K_i = K(g, pitch_i):

      gap(g)   = sum K_i (y_i - e_i) / (sum K_i + PRIOR_PITCHES)

  y_i is 1 for a chase, e_i the league expectation for that pitch. The
  numerator is the player's extra chases near g; the PRIOR_PITCHES term
  pulls the estimate to zero (league average) where the hitter saw few pitches.
  The same formula with y = whiff and e = the league's whiff chance on
  that chase gives the contact surface.

      evidence(g) = sum K_i / (sum K_i + EVIDENCE_PITCHES)

  sets the color's opacity, so where the hitter saw few pitches the picture
  fades to the background instead of claiming anything.
"""

import numpy as np

HALF_PLATE_PLUS_BALL = 0.83     # ft; same zone edge as steps 02-04

# Card grid (ft). x spans both sides of the plate; z runs from the
# ground to well above the tallest hitter's zone.
X_MIN, X_MAX = -2.0, 2.0
Z_MIN, Z_MAX = -0.1, 5.0
GRID_STEP = 0.05

BANDWIDTH = 0.28                # ft; Gaussian sd of the player smoother
KERNEL_REACH = 3.0              # in bandwidths; weights beyond are 0
PRIOR_PITCHES = 3.0             # shrink toward league with this many pitches' weight
EVIDENCE_PITCHES = 1.5          # opacity half-point, in kernel-weighted pitches

GAP_LIMIT = 0.30                # color scale runs from -30 to +30 points
CONTOUR_GAP = 0.15              # outline where the hitter chases 15+ points more
CONTOUR_MIN_EVIDENCE = 0.5      # ...but only where the evidence is solid


def grid():
    xs = np.round(np.arange(X_MIN, X_MAX + 1e-9, GRID_STEP), 4)
    zs = np.round(np.arange(Z_MIN, Z_MAX + 1e-9, GRID_STEP), 4)
    return xs, zs


def in_zone_mask(xs, zs, bottom, top):
    """True inside the hitter's own zone (bottom and top in feet)."""

    gx, gz = np.meshgrid(xs, zs)   # shape (len zs, len xs): rows = z
    return (np.abs(gx) < HALF_PLATE_PLUS_BALL) & (gz > bottom) & (gz < top)


def surface(x, z, y, e, xs, zs):
    """gap, evidence, weight, player rate and league rate on the grid.

    Arrays come back with rows = z (bottom to top) and columns = x.
    The Gaussian is separable, so the weight of pitch i at grid point
    (a, b) is kx[i, a] * kz[i, b].
    """

    x = np.asarray(x, float)
    z = np.asarray(z, float)
    y = np.asarray(y, float)
    e = np.asarray(e, float)
    reach = KERNEL_REACH * BANDWIDTH

    def k1(points, grid_values):
        d = grid_values[None, :] - points[:, None]
        k = np.exp(-0.5 * (d / BANDWIDTH) ** 2)
        k[np.abs(d) > reach] = 0.0
        return k

    kx = k1(x, xs)                  # (n, len xs)
    kz = k1(z, zs)                  # (n, len zs)
    weight = kz.T @ kx              # sum_i K_i
    extra = kz.T @ (kx * (y - e)[:, None])
    observed = kz.T @ (kx * y[:, None])
    expected = kz.T @ (kx * e[:, None])

    gap = extra / (weight + PRIOR_PITCHES)
    evidence = weight / (weight + EVIDENCE_PITCHES)
    with np.errstate(invalid="ignore", divide="ignore"):
        player_rate = np.where(weight > 1e-6, observed / weight, np.nan)
        league_rate = np.where(weight > 1e-6, expected / weight, np.nan)
    return {
        "gap": gap, "evidence": evidence, "weight": weight,
        "player_rate": player_rate, "league_rate": league_rate,
    }


def zone_region(x, z, zone_height):
    """Side of the zone missed: up / down / in / away and the corners.

    Takes batter-relative x (negative = inside) and z measured from the
    bottom of the zone, so "inside" means the same thing for both sides."""

    x = np.asarray(x, float)
    z = np.asarray(z, float)
    vertical = np.where(z > zone_height, "up", np.where(z < 0, "down", ""))
    horizontal = np.where(x < -HALF_PLATE_PLUS_BALL, "in",
                          np.where(x > HALF_PLATE_PLUS_BALL, "away", ""))
    return np.array([(v + "-" + h).strip("-") or "edge"
                     for v, h in zip(vertical, horizontal)])
