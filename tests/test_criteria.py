"""Criteria + cohesion: harmonic-mean behavior, score bounds, verdict tagging."""
from __future__ import annotations

import unittest

from studio_engine import criteria as crit


class TestCohesion(unittest.TestCase):
    def test_all_perfect_is_one(self):
        self.assertEqual(crit.cohesion([1.0, 1.0]), 1.0)

    def test_single_value(self):
        self.assertAlmostEqual(crit.cohesion([0.5]), 0.5, places=6)

    def test_one_low_axis_tanks_the_whole(self):
        # Harmonic mean is dominated by the smallest term; one bad axis collapses it.
        self.assertLess(crit.cohesion([1.0, 0.1]), 0.2)

    def test_harmonic_mean_value(self):
        # HM(1.0, 0.1) = 2 / (1 + 10) = 0.1818...
        self.assertAlmostEqual(crit.cohesion([1.0, 0.1]), 2.0 / 11.0, places=6)

    def test_below_average(self):
        # Harmonic mean never exceeds the arithmetic mean of the same values.
        vals = [0.9, 0.6, 0.3]
        arithmetic = sum(vals) / len(vals)
        self.assertLessEqual(crit.cohesion(vals), arithmetic + 1e-9)

    def test_empty_is_zero(self):
        self.assertEqual(crit.cohesion([]), 0.0)

    def test_clamps_into_unit_range(self):
        # Values are clamped to [1e-6, 1.0]; out-of-range inputs do not blow up.
        result = crit.cohesion([2.0, 5.0])
        self.assertLessEqual(result, 1.0)
        self.assertGreater(result, 0.0)


class TestScore(unittest.TestCase):
    def test_every_registered_axis_returns_unit_interval(self):
        features = {
            "centroid_offset": 0.2,
            "coverage": 0.6,
            "contrast": 0.5,
            "entropy": 0.8,
        }
        params = {"angle": crit.GOLDEN_ANGLE, "freq": 6.0, "waves": 5}
        for axis in crit.REGISTRY:
            with self.subTest(axis=axis):
                s = crit.score(axis, features, params)
                self.assertIsInstance(s, float)
                self.assertGreaterEqual(s, 0.0)
                self.assertLessEqual(s, 1.0)

    def test_golden_angle_peaks_at_constant(self):
        s = crit.score("golden_angle", {}, {"angle": crit.GOLDEN_ANGLE})
        self.assertAlmostEqual(s, 1.0, places=6)

    def test_golden_angle_degrades_off_target(self):
        on = crit.score("golden_angle", {}, {"angle": crit.GOLDEN_ANGLE})
        off = crit.score("golden_angle", {}, {"angle": crit.GOLDEN_ANGLE + 30.0})
        self.assertLess(off, on)

    def test_unknown_axis_is_zero(self):
        self.assertEqual(crit.score("does_not_exist", {}, {}), 0.0)


class TestTag(unittest.TestCase):
    def test_high_score_verified(self):
        self.assertEqual(crit.tag(0.95), "verified")
        self.assertEqual(crit.tag(0.90), "verified")  # boundary == target

    def test_mid_score_unverifiable(self):
        self.assertEqual(crit.tag(0.7), "unverifiable")
        self.assertEqual(crit.tag(0.55), "unverifiable")  # boundary == floor

    def test_low_score_refuted(self):
        self.assertEqual(crit.tag(0.2), "refuted")
        self.assertEqual(crit.tag(0.0), "refuted")

    def test_custom_thresholds(self):
        self.assertEqual(crit.tag(0.5, target=0.8, floor=0.4), "unverifiable")
        self.assertEqual(crit.tag(0.3, target=0.8, floor=0.4), "refuted")
        self.assertEqual(crit.tag(0.85, target=0.8, floor=0.4), "verified")


class TestKind(unittest.TestCase):
    def test_objective_and_subjective_split(self):
        self.assertEqual(crit.kind("golden_angle"), "objective")
        self.assertEqual(crit.kind("balance"), "subjective")

    def test_unknown_axis_defaults_objective(self):
        self.assertEqual(crit.kind("nope"), "objective")


if __name__ == "__main__":
    unittest.main()
