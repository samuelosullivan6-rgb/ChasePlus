"""
Unit tests for scripts/chase_model.py on a synthetic season: the pieces of
the chase method that are shared between step 04 and the college path.

Run with:  .venv/bin/python -m unittest tests.test_chase_model -v
(no pytest needed; pytest also finds them.)
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import chase_model as cm  # noqa: E402


def synthetic_takes(n=40000, seed=0):
    """
    Out-of-zone takes with a known called-strike law: log-odds fall
    linearly with distance at a rate that depends on the side, 0-2 is
    called tighter, 3-0 looser.
    """

    rng = np.random.default_rng(seed)
    distance = rng.exponential(0.35, n)
    side = rng.choice(cm.ZONE_SIDES, n, p=[0.45, 0.2, 0.25, 0.1])
    balls = rng.integers(0, 4, n)
    strikes = rng.integers(0, 3, n)

    side_slope = {"side": -9.0, "above": -6.0, "below": -12.0, "corner": -15.0}
    side_level = {"side": 0.0, "above": 0.6, "below": -0.4, "corner": -0.8}
    count_shift = np.where((balls == 0) & (strikes == 2), -1.0,
                           np.where((balls == 3) & (strikes == 0), 0.7, 0.0))

    logit = (
        -0.5
        + np.array([side_level[s] for s in side])
        + np.array([side_slope[s] for s in side]) * distance
        + count_shift
    )
    called = rng.random(n) < 1 / (1 + np.exp(-logit))

    return pd.DataFrame({
        "distance_outside_zone": distance,
        "zone_side": side,
        "balls": balls,
        "strikes": strikes,
        "was_called_strike": called.astype(int),
    })


class TestGeometry(unittest.TestCase):

    def test_zone_edge_is_half_plate_plus_a_ball(self):
        self.assertAlmostEqual(cm.HALF_PLATE_PLUS_BALL, (8.5 + 1.45) / 12, places=2)
        self.assertAlmostEqual(cm.BALL_RADIUS, 1.45 / 12, places=2)

    def test_label_zone_side(self):
        frame = pd.DataFrame({
            "plate_x": [1.2, 0.0, 0.0, 1.2, 0.0, np.nan, 0.0],
            "plate_z": [2.5, 4.0, 1.0, 4.0, 3.55, 2.5, 3.6],
            "sz_top": [3.5] * 7,
            "sz_bot": [1.5] * 7,
            "distance_outside_zone": [0.37, 0.5, 0.5, 0.62, 0.05, np.nan, 0.15],
        })
        direction, side = cm.label_zone_side(frame)
        self.assertEqual(list(direction), ["side", "above", "below", "corner", "above", "unknown", "above"])
        # within a ball's radius above the top joins the corners; unknown is missing
        self.assertEqual(list(side[:4]), ["side", "above", "below", "corner"])
        self.assertEqual(side.iloc[4], "corner")
        self.assertTrue(pd.isna(side.iloc[5]))
        self.assertEqual(side.iloc[6], "above")

    def test_on_the_edge_joins_the_side_curve(self):
        frame = pd.DataFrame({"plate_x": [0.5], "plate_z": [2.5], "sz_top": [3.5], "sz_bot": [1.5],
                              "distance_outside_zone": [0.0]})
        direction, side = cm.label_zone_side(frame)
        self.assertEqual(direction.iloc[0], "on the edge")
        self.assertEqual(side.iloc[0], "side")


class TestPitchGroups(unittest.TestCase):

    def test_groups_are_disjoint_and_cover_the_common_types(self):
        self.assertFalse(set(cm.FASTBALLS) & set(cm.BREAKING))
        self.assertFalse(set(cm.FASTBALLS) & set(cm.OFFSPEED))
        self.assertFalse(set(cm.BREAKING) & set(cm.OFFSPEED))
        groups = cm.pitch_group(pd.Series(["FF", "SL", "CH", "XX", None]))
        self.assertEqual(list(groups), ["fastball", "breaking", "offspeed", "other", "other"])


class TestFeatures(unittest.TestCase):

    def test_feature_columns_are_stable_across_slices(self):
        takes = synthetic_takes(500)
        full = cm.called_strike_features(takes)
        part = cm.called_strike_features(takes[takes["balls"] == 3])
        self.assertEqual(list(full.columns), list(part.columns))
        self.assertEqual(len(full.columns), 1 + 4 + 11)
        self.assertTrue((full[[f"side_{s}" for s in cm.ZONE_SIDES]].sum(axis=1) == 1).all())


class TestMonotoneModel(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.takes = synthetic_takes()
        cls.model = cm.new_called_strike_model().fit(
            cm.called_strike_features(cls.takes), cls.takes["was_called_strike"]
        )

    def test_converges(self):
        self.assertTrue(self.model.converged_)

    def test_no_curve_rises_with_distance_in_any_count(self):
        for side in cm.ZONE_SIDES:
            for balls, strikes in cm.COUNTS_IN_ORDER:
                self.assertTrue(
                    cm.curve_never_rises(self.model, side, balls=balls, strikes=strikes),
                    f"{side} rises at {balls}-{strikes}",
                )

    def test_recovers_the_count_effects(self):
        two_strikes = self.model.coefficient("count_0_2")
        three_balls = self.model.coefficient("count_3_0")
        self.assertLess(two_strikes, -0.6)
        self.assertGreater(three_balls, 0.3)
        # a count with no true shift: within sampling noise of zero
        self.assertLess(abs(self.model.coefficient("count_1_1")), 0.35)

    def test_calibrated_overall_and_by_side(self):
        predicted = self.model.predict_proba(cm.called_strike_features(self.takes))[:, 1]
        actual = self.takes["was_called_strike"].to_numpy()
        self.assertAlmostEqual(predicted.mean(), actual.mean(), places=3)
        for side in cm.ZONE_SIDES:
            mask = (self.takes["zone_side"] == side).to_numpy()
            self.assertLess(abs(predicted[mask].mean() - actual[mask].mean()), 0.01, side)

    def test_sides_differ_in_the_right_order(self):
        grid = pd.DataFrame({"distance_outside_zone": [0.2] * 4, "zone_side": cm.ZONE_SIDES,
                             "balls": 0, "strikes": 0})
        rate = self.model.predict_proba(cm.called_strike_features(grid))[:, 1]
        by_side = dict(zip(cm.ZONE_SIDES, rate))
        # the synthetic law: above is called most, corner least, at 0.2 ft
        self.assertGreater(by_side["above"], by_side["side"])
        self.assertLess(by_side["corner"], by_side["side"])

    def test_scores_pitches_it_did_not_fit(self):
        fresh = synthetic_takes(2000, seed=1)
        predicted = self.model.predict_proba(cm.called_strike_features(fresh))[:, 1]
        self.assertAlmostEqual(predicted.mean(), fresh["was_called_strike"].mean(), delta=0.01)

    def test_no_side_comparison_model_fits(self):
        model = cm.new_no_side_model().fit(
            cm.no_side_features(self.takes), self.takes["was_called_strike"]
        )
        predicted = model.predict_proba(cm.no_side_features(self.takes))[:, 1]
        self.assertAlmostEqual(predicted.mean(), self.takes["was_called_strike"].mean(), places=2)


class TestShrinkage(unittest.TestCase):

    def test_dersimonian_laird_recovers_the_spread(self):
        rng = np.random.default_rng(0)
        true_sd, n = 4.0, 3000
        truth = rng.normal(0, true_sd, n)
        se = rng.uniform(2.0, 6.0, n)
        observed = truth + rng.normal(0, se)
        tau_squared, mean, q = cm.estimate_between_hitter_variance(observed, se)
        self.assertAlmostEqual(np.sqrt(tau_squared), true_sd, delta=0.3)
        self.assertAlmostEqual(mean, 0.0, delta=0.3)
        self.assertGreater(q, n - 1)

    def test_tau_squared_is_floored_at_zero(self):
        rng = np.random.default_rng(1)
        se = np.full(500, 5.0)
        observed = rng.normal(0, 1.0, 500)        # far less spread than the SE says
        tau_squared, _, _ = cm.estimate_between_hitter_variance(observed, se)
        self.assertEqual(tau_squared, 0.0)

    def test_shrink_pulls_toward_the_mean_and_never_past_it(self):
        effects = np.array([10.0, -10.0, 0.0])
        se = np.array([2.0, 8.0, 1.0])
        shrunk, factor = cm.shrink(effects, se, tau_squared=16.0, toward=1.0)
        self.assertTrue(np.all(factor > 0) and np.all(factor < 1))
        self.assertTrue(factor[1] > factor[0] > factor[2])       # more SE, more shrinkage
        self.assertTrue(1.0 < shrunk[0] < 10.0)
        self.assertTrue(-10.0 < shrunk[1] < 1.0)
        shrunk0, factor0 = cm.shrink(effects, se, tau_squared=0.0, toward=1.0)
        self.assertTrue(np.allclose(shrunk0, 1.0) and np.allclose(factor0, 1.0))


if __name__ == "__main__":
    unittest.main()
