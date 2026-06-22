"""Witnessed motion: animatable fields loop seamlessly + stay legible; metaballs is honest about not."""
from __future__ import annotations

import math
import unittest

from studio_engine import engine
from studio_engine import temporal
from studio_engine.strand import expr as ex

ANIM = ["gyroid", "quasicrystal", "flowfield", "turbulence"]


def _params(spec, seed=7):
    rng = (seed * 2654435761 + 12345) & 0xFFFFFFFF
    return engine._clamp(spec, spec["params0"](rng))


class TestTemporal(unittest.TestCase):
    def test_animatable_fields_build_seamless_timeline(self):
        gens = engine._gens()
        for name in ANIM:
            spec = gens[name]
            tl = temporal.build_timeline(spec, _params(spec))
            with self.subTest(field=name):
                self.assertIsNotNone(tl)
                self.assertGreater(tl.period, 0.0)
                self.assertEqual(tl.continuity.tag, "verified")
                self.assertIsNotNone(tl.on_criterion)

    def test_metaballs_not_animatable(self):
        gens = engine._gens()
        self.assertIsNone(temporal.build_timeline(gens["metaballs"], _params(gens["metaballs"])))

    def test_discontinuity_detected(self):
        e = ex.add(ex.sin(ex.var("t")), ex.mul(ex.var("u"), 0.0))  # depends on t, flat in u,v
        good = temporal.continuity(e, 2 * math.pi)   # the true period -> seamless
        bad = temporal.continuity(e, 1.0)            # wrong period -> seam jump
        self.assertGreater(good.score, bad.score)
        self.assertEqual(good.tag, "verified")
        self.assertNotEqual(bad.tag, "verified")


if __name__ == "__main__":
    unittest.main()
