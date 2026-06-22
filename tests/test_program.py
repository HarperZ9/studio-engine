"""RenderProgram/AudioProgram assembly: the shipped program IS the verified strand math."""
from __future__ import annotations

import json
import re
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

    def test_value_range_covers_animation(self):
        # The shipped value_range must bracket the field across every frame the chamber renders
        # (the whole loop for animatable fields), so coloring never clips/washes mid-animation.
        gens = engine._gens()
        for name in FIELDS:
            spec = gens[name]
            P = _params(spec)
            e = spec["expr"](P)
            period = spec["period"](P)
            rp = prog.field_program(name, e, PAL, spec["t0"](P), spec["animatable"], period)
            lo, hi = rp.value_range
            ts = [period * k / 8 for k in range(8)] if (spec["animatable"] and period > 0) \
                else [spec["t0"](P)]
            for t in ts:
                vals = ex.sample_field(e, 24, t)
                self.assertGreaterEqual(min(vals), lo - 1e-6, f"{name} t={t}")
                self.assertLessEqual(max(vals), hi + 1e-6, f"{name} t={t}")

    def test_shipped_glsl_body_is_the_engine_field(self):
        # The keystone, through the SHIPPED artifact: parse the field() body out of the emitted
        # fragment source and confirm it evaluates to the engine's verified field. Non-circular.
        gens = engine._gens()
        for name in FIELDS:
            spec = gens[name]
            P = _params(spec)
            e, t0 = spec["expr"](P), spec["t0"](P)
            rp = prog.field_program(name, e, PAL, t0, spec["animatable"], spec["period"](P))
            m = re.search(r"float field\(float u, float v, float t\)\{ return (.+?); \}", rp.source)
            self.assertIsNotNone(m, f"{name}: field() body not found in shipped source")
            body = glsl.parse_glsl(m.group(1))
            for (u, v) in [(-0.6, 0.3), (0.2, -0.5), (0.8, 0.8)]:
                with self.subTest(field=name, u=u, v=v):
                    self.assertAlmostEqual(ex.eval_expr(body, {"u": u, "v": v, "t": t0}),
                                           spec["field"](P, u, v), places=6)


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
