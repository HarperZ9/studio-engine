"""RenderProgram/AudioProgram assembly: the shipped program IS the verified strand math."""
from __future__ import annotations

import json
import unittest
from dataclasses import asdict

from studio_engine import engine
from studio_engine.organs import program as prog
from studio_engine.strand import expr as ex
from studio_engine.strand import glsl
from studio_engine.strand import recipe as rc

FIELDS = ["gyroid", "quasicrystal", "flowfield", "metaballs", "turbulence"]
POINTS = ["phyllotaxis", "attractor", "harmonograph"]
PAL = ["#101418", "#2dd4bf", "#7a5cff", "#fbbf24", "#ff7a5c", "#e8e8f0"]


def _params(spec, seed=7):
    rng = (seed * 2654435761 + 12345) & 0xFFFFFFFF
    return engine._clamp(spec, spec["params0"](rng))


class TestFieldPrograms(unittest.TestCase):
    def test_field_program_is_grounded(self):
        gens = engine._gens()
        for name in FIELDS:
            spec = gens[name]
            P = _params(spec)
            e, t0 = spec["expr"](P), spec["t0"](P)
            rp = prog.field_program(name, e, PAL, t0, spec["animatable"], spec["period"](P))
            with self.subTest(field=name):
                self.assertEqual(rp.target, "glsl-fragment")
                self.assertIn("field(", rp.source)
                self.assertIn(glsl.emit_glsl(e), rp.source)  # the body IS the verified expr
                self.assertIn("safediv", rp.source)
                self.assertLess(rp.value_range[0], rp.value_range[1])
                self.assertEqual(rp.expr_sha256, ex.sha(e))
                json.dumps(asdict(rp))  # fully serializable

    def test_value_range_matches_sampling(self):
        gens = engine._gens()
        for name in FIELDS:
            spec = gens[name]
            P = _params(spec)
            e, t0 = spec["expr"](P), spec["t0"](P)
            rp = prog.field_program(name, e, PAL, t0, spec["animatable"], spec["period"](P))
            vals = ex.sample_field(e, 24, t0)
            self.assertAlmostEqual(rp.value_range[0], round(min(vals), 6), places=6)
            self.assertAlmostEqual(rp.value_range[1], round(max(vals), 6), places=6)


class TestPointPrograms(unittest.TestCase):
    def test_point_program_reproduces(self):
        gens = engine._gens()
        for name in POINTS:
            spec = gens[name]
            r = spec["recipe"](_params(spec))
            rp = prog.point_program(name, r, PAL)
            with self.subTest(gen=name):
                self.assertEqual(rp.target, "point-recipe")
                self.assertIn(rp.recipe["mode"], ("spiral", "iterated", "parametric"))
                self.assertTrue(rc.eval_recipe(rp.recipe))
                json.dumps(asdict(rp))


class TestAudioProgram(unittest.TestCase):
    def test_audio_program(self):
        ap = prog.audio_program(7, PAL, [0.2, 0.5, 0.8, 0.95])
        self.assertTrue(ap.oscillators)
        self.assertGreater(ap.base_freq, 0.0)
        self.assertTrue(ap.expr_sha256)
        json.dumps(asdict(ap))


if __name__ == "__main__":
    unittest.main()
