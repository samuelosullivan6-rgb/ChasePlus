"""
The pieces of the chase method that more than one script needs, in one
place so they cannot drift apart:

  - the plate geometry (HALF_PLATE_PLUS_BALL, BALL_RADIUS) that scripts
    02, 04, 12, 13, the card surfaces and the TrackMan adapter all draw
    the zone edge with;
  - the pitch groups (fastball / breaking / offspeed) the coaching
    scripts and the pitch-group baseline in step 04 share;
  - the called-strike model of step 04: which side of the zone a take
    missed on, the feature columns, and the monotone logistic model with
    one distance curve per side, plus the two comparison models;
  - the DerSimonian-Laird estimator every shrinkage in the project uses.

Step 04 imports from here and the college path (college_method.py) does
too, so the college build prices a take exactly as the MLB build does.
07_check_chase_invariants.py reads the literal settings below with the
ast module; keep them as plain top-level NAME = <literal> assignments.

tests/test_chase_model.py exercises everything here on a synthetic
season.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit as log_odds
from scipy.sparse import csr_matrix
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler


# --------------------------------------------------
# GEOMETRY
# --------------------------------------------------

# Horizontally the zone edge is 0.83 ft from the middle of the plate:
# half the plate (8.5 in) plus a ball radius (1.45 in). Vertically the
# zone is the hitter's own sz_top / sz_bot, with no ball radius added.
HALF_PLATE_PLUS_BALL = 0.83

# A baseball's radius in feet. Statcast's out-of-zone flag counts a
# ball's width above and below the zone.
BALL_RADIUS = 0.121


# --------------------------------------------------
# PITCH GROUPS
# --------------------------------------------------

FASTBALLS = ["FF", "SI", "FC", "FA"]
BREAKING = ["SL", "ST", "CU", "KC", "SV", "CS"]
OFFSPEED = ["CH", "FS", "FO", "EP", "KN"]

PITCH_GROUPS = ["fastball", "breaking", "offspeed"]


def pitch_group(pitch_type):
    """fastball / breaking / offspeed, or other (unknown or rare types)."""

    pitch_type = pd.Series(pitch_type)

    return pd.Series(
        np.select(
            [
                pitch_type.isin(FASTBALLS),
                pitch_type.isin(BREAKING),
                pitch_type.isin(OFFSPEED),
            ],
            PITCH_GROUPS,
            "other",
        ),
        index=pitch_type.index,
    )


# --------------------------------------------------
# CALLED-STRIKE MODEL SETTINGS
# --------------------------------------------------

# Knots of the called-strike distance spline, in feet outside the zone.
# Past the last knot the curve is linear in log-odds. Knots beyond 0.7 ft
# let the thin tail bend back up past about 1.15 ft (a pitch four feet off
# more likely to be a called strike than one a foot off), so they stop
# at 0.7.
CALLED_STRIKE_DISTANCE_KNOTS = [0.0, 0.10, 0.20, 0.30, 0.45, 0.70]

# Ridge penalty on every coefficient of the called-strike model but the
# intercept. Enough to keep the fit unique where a side of the zone has no
# called strikes far out; at scikit-learn's default (1.0) it held the
# tails up, so takes nowhere near the zone came out a little over-called
# (by 0.1 to 0.4 per 1,000) above and below.
CALLED_STRIKE_PENALTY = 0.01

COUNTS_IN_ORDER = [
    (balls, strikes)
    for balls in range(4)
    for strikes in range(3)
]

# The sides of the zone in the model, the first one the reference.
ZONE_SIDES = ["side", "above", "below", "corner"]


# --------------------------------------------------
# WHICH SIDE OF THE ZONE A PITCH MISSED ON
# --------------------------------------------------

def label_zone_side(frame):
    """
    Two columns for a frame of out-of-zone pitches with plate_x, plate_z,
    sz_top, sz_bot and distance_outside_zone:

      miss_direction  side / above / below / corner / on the edge /
                      unknown, from the raw geometry
      zone_side       the model's version: on the edge joins side, a take
                      above or below but within a ball's radius of the
                      recorded edge joins corner (it was flagged out by
                      the side edge), unknown is missing

    Same geometry as distance_outside_zone in script 02.
    """

    sideways_miss = (
        frame["plate_x"].abs() - HALF_PLATE_PLUS_BALL
    ).clip(lower=0)

    above_miss = (frame["plate_z"] - frame["sz_top"]).clip(lower=0)
    below_miss = (frame["sz_bot"] - frame["plate_z"]).clip(lower=0)

    miss_direction = pd.Series(
        np.select(
            [
                frame[["plate_x", "plate_z", "sz_top", "sz_bot"]]
                .isna()
                .any(axis=1),
                (sideways_miss > 0) & ((above_miss > 0) | (below_miss > 0)),
                sideways_miss > 0,
                above_miss > 0,
                below_miss > 0,
            ],
            ["unknown", "corner", "side", "above", "below"],
            default="on the edge",
        ),
        index=frame.index,
    )

    zone_side = miss_direction.replace({"on the edge": "side", "unknown": np.nan})

    zone_side = zone_side.mask(
        zone_side.isin(["above", "below"])
        & (frame["distance_outside_zone"] < BALL_RADIUS),
        "corner",
    )

    return miss_direction, zone_side


# --------------------------------------------------
# FEATURE COLUMNS
# --------------------------------------------------

def distance_only_features(frame):
    """Distance alone. Only used as the comparison model in the check."""

    return pd.DataFrame(
        {
            "distance_outside_zone": (
                frame["distance_outside_zone"].astype(float)
            )
        },
        index=frame.index
    )


def no_side_features(frame):
    """
    Distance and the count indicators, without the side of the zone. The
    model before October 2026; kept as the comparison in the check.
    """

    features = distance_only_features(frame)

    balls = frame["balls"].to_numpy()
    strikes = frame["strikes"].to_numpy()

    for count_balls, count_strikes in COUNTS_IN_ORDER[1:]:

        features[f"count_{count_balls}_{count_strikes}"] = (
            (balls == count_balls)
            & (strikes == count_strikes)
        ).astype(float)

    return features


def called_strike_features(frame):
    """
    Raw distance (the splines are built inside the model), one 0/1 column
    per side of the zone, and one 0/1 column for every count except 0-0.
    The columns are the same for any slice of pitches, so a model fit on
    one set can score another.
    """

    features = no_side_features(frame)

    zone_side = frame["zone_side"].to_numpy()

    for position, side in enumerate(ZONE_SIDES):
        features.insert(
            1 + position,
            f"side_{side}",
            (zone_side == side).astype(float)
        )

    return features


def distance_spline(knots=None):
    """The cubic spline of distance, with fixed knots."""

    if knots is None:
        knots = CALLED_STRIKE_DISTANCE_KNOTS

    return SplineTransformer(
        knots=np.array(knots).reshape(-1, 1),
        degree=3,
        extrapolation="linear",
        include_bias=False
    )


# --------------------------------------------------
# THE MODEL
# --------------------------------------------------

class MonotoneCalledStrikeModel(BaseEstimator, ClassifierMixin):
    """
    Logistic regression with one distance curve per side of the zone, each
    unable to rise with distance, plus the count indicators.

    Each side's curve is a weighted sum of the cubic spline's tail sums
    (the basis functions from the k-th on, added up), which never fall
    with distance and stay flat past the last knot, plus the distance
    past the last knot, which keeps the curve falling in the tail. Every
    weight is held at or above zero and enters with a minus sign, so no
    side's curve can rise with distance, in any count. The side and count
    terms are free. Fit by maximum likelihood with a light ridge penalty
    (penalty) on every term but the intercept.

    Takes called_strike_features' columns.
    """

    def __init__(self, knots=None, penalty=CALLED_STRIKE_PENALTY):
        self.knots = list(CALLED_STRIKE_DISTANCE_KNOTS if knots is None else knots)
        self.penalty = penalty

    def fit(self, X, y):

        design, names, is_curve = self._design(X)
        design_transposed = design.T.tocsr()
        outcomes = np.asarray(y, dtype=float)
        penalty = self.penalty

        def loss_and_gradient(theta):

            linear = design @ theta
            loss = np.sum(np.logaddexp(0, linear) - outcomes * linear)
            gradient = design_transposed @ (expit(linear) - outcomes)

            penalized = theta.copy()
            penalized[0] = 0.0

            loss += 0.5 * penalty * penalized @ penalized
            gradient += penalty * penalized

            return loss, gradient

        start = np.zeros(design.shape[1])
        start[0] = log_odds(np.clip(outcomes.mean(), 1e-6, 1 - 1e-6))

        result = minimize(
            loss_and_gradient,
            start,
            jac=True,
            method="L-BFGS-B",
            bounds=[
                (0.0, None) if curve else (None, None)
                for curve in is_curve
            ],
            options={"maxiter": 20000, "ftol": 1e-13, "gtol": 1e-7},
        )

        self.coef_ = result.x
        self.feature_names_ = names
        self.converged_ = bool(result.success)
        self.n_iter_ = int(result.nit)

        return self

    def coefficient(self, name):

        return float(self.coef_[self.feature_names_.index(name)])

    def decision_function(self, X):

        design, _, _ = self._design(X)

        return design @ self.coef_

    def predict_proba(self, X):

        chance = expit(self.decision_function(X))

        return np.column_stack([1 - chance, chance])

    def _design(self, X):
        """
        The model's columns: intercept, one 0/1 column per side but the
        reference, the count indicators, then each side's curve columns
        (negative tail sums and negative distance past the last knot,
        zero off that side). Also returns the names and which columns
        are curve weights.
        """

        knots = self.knots
        distance = X["distance_outside_zone"].to_numpy(dtype=float)
        last_knot = knots[-1]

        basis = SplineTransformer(
            knots=np.array(knots).reshape(-1, 1),
            degree=3,
            extrapolation="constant",
            include_bias=True
        ).fit([[0.0], [last_knot]]).transform(
            np.clip(distance, 0, last_knot).reshape(-1, 1)
        )

        # The first tail sum is the whole basis, 1 everywhere, so it is
        # left out.
        tail_sums = np.cumsum(basis[:, ::-1], axis=1)[:, ::-1][:, 1:]
        past_last_knot = np.clip(distance - last_knot, 0, None)

        curve = np.column_stack([tail_sums, past_last_knot])

        sides = {
            side: X[f"side_{side}"].to_numpy(dtype=float)
            for side in ZONE_SIDES
        }

        count_columns = [
            column for column in X.columns if column.startswith("count_")
        ]

        columns = [np.ones(len(X))]
        names = ["intercept"]
        is_curve = [False]

        for side in ZONE_SIDES[1:]:
            columns.append(sides[side])
            names.append(f"side_{side}")
            is_curve.append(False)

        for column in count_columns:
            columns.append(X[column].to_numpy(dtype=float))
            names.append(column)
            is_curve.append(False)

        for side in ZONE_SIDES:
            for position in range(curve.shape[1]):
                columns.append(-curve[:, position] * sides[side])
                names.append(
                    f"{side}_past_last_knot"
                    if position == curve.shape[1] - 1
                    else f"{side}_tail_sum_{position + 1}"
                )
                is_curve.append(True)

        # Each row is non-zero in about 11 of the 47 columns.
        return csr_matrix(np.column_stack(columns)), names, is_curve


def new_called_strike_model(knots=None, penalty=CALLED_STRIKE_PENALTY):
    """
    The model used for pricing: a distance curve per side of the zone
    that cannot rise with distance, plus count. Each season fits its own.
    """

    return MonotoneCalledStrikeModel(knots=knots, penalty=penalty)


def new_no_side_model(knots=None):
    """
    The model without the side of the zone: one distance spline for every
    take, any other columns (the count indicators) passed straight
    through. Only used as a comparison in the check.
    """

    distance_curve = Pipeline([
        ("spline", distance_spline(knots)),
        ("scale", StandardScaler()),
    ])

    features = ColumnTransformer(
        [("distance", distance_curve, ["distance_outside_zone"])],
        remainder="passthrough",
        verbose_feature_names_out=False
    )

    return Pipeline([
        ("features", features),
        ("logit", LogisticRegression(max_iter=1000)),
    ])


def curve_never_rises(model, zone_side, distances=None, balls=0, strikes=0):
    """
    True if the fitted called-strike chance never rises with distance on
    one side of the zone, checked on a grid (0 to 10 ft by default).
    """

    if distances is None:
        distances = np.linspace(0, 10, 4001)

    grid = pd.DataFrame({
        "distance_outside_zone": np.asarray(distances, dtype=float),
        "zone_side": zone_side,
        "balls": balls,
        "strikes": strikes,
    })

    curve = model.predict_proba(called_strike_features(grid))[:, 1]

    return not (np.diff(curve) > 1e-12).any()


# --------------------------------------------------
# SHRINKAGE
# --------------------------------------------------

def estimate_between_hitter_variance(effects, standard_errors):
    """
    DerSimonian-Laird. Returns tau squared (the real spread between
    hitters, with measurement noise removed, floored at zero), the
    inverse-variance-weighted mean, and Cochran's Q.
    """

    effects = np.asarray(effects, dtype=float)
    standard_errors = np.asarray(standard_errors, dtype=float)

    weights = 1.0 / (standard_errors ** 2)

    weighted_mean = (
        np.sum(weights * effects)
        / np.sum(weights)
    )

    q_statistic = np.sum(
        weights * (effects - weighted_mean) ** 2
    )

    k = len(effects)

    scaling = (
        np.sum(weights)
        - np.sum(weights ** 2) / np.sum(weights)
    )

    tau_squared = (q_statistic - (k - 1)) / scaling

    return max(tau_squared, 0.0), weighted_mean, q_statistic


def shrink(effects, standard_errors, tau_squared, toward):
    """
    Pull each effect toward `toward` by SE^2 / (SE^2 + tau^2). Returns the
    shrunk effects and the factors. With tau^2 = 0 everything collapses
    to `toward`.
    """

    effects = np.asarray(effects, dtype=float)
    variance = np.asarray(standard_errors, dtype=float) ** 2

    if tau_squared > 0:
        factor = variance / (variance + tau_squared)
    else:
        factor = np.ones_like(variance)

    return effects - factor * (effects - toward), factor
