import math
import unittest

from studio_engine.strand import expr as ex
from studio_engine.strand import recipe as rc
from studio_engine.organs import geometry


class TestRecipe(unittest.TestCase):
    def test_spiral_reproduces_phyllotaxis(self):
        r = rc.spiral(angle_deg=geometry.GOLDEN_ANGLE, scale=9.0, count=200)
        pts = rc.eval_recipe(r)
        ref = geometry.phyllotaxis(200, geometry.GOLDEN_ANGLE, 9.0)
        self.assertEqual(len(pts), len(ref))
        for (a, b) in zip(pts[:50], ref[:50]):
            self.assertAlmostEqual(a[0], b[0], places=9)
            self.assertAlmostEqual(a[1], b[1], places=9)
            self.assertEqual(a[2], b[2])

    def test_iterated_matches_manual_dejong(self):
        a, b, c, d = 1.7, 1.7, 0.6, 1.2
        ux = ex.sub(ex.sin(ex.mul(a, ex.var("y"))), ex.cos(ex.mul(b, ex.var("x"))))
        uy = ex.sub(ex.sin(ex.mul(c, ex.var("x"))), ex.cos(ex.mul(d, ex.var("y"))))
        r = rc.iterated(ux, uy, init=[0.1, 0.1], transient=20, count=200)
        pts = rc.eval_recipe(r)
        # manual reference
        x, y = 0.1, 0.1
        ref = []
        i = 0
        for step in range(200):
            x, y = math.sin(a * y) - math.cos(b * x), math.sin(c * x) - math.cos(d * y)
            if step < 20:
                continue
            ref.append((x, y, i))
            i += 1
        self.assertEqual(len(pts), len(ref))
        for (p, q) in zip(pts[:50], ref[:50]):
            self.assertAlmostEqual(p[0], q[0], places=9)
            self.assertAlmostEqual(p[1], q[1], places=9)

    def test_parametric_matches_manual_curve(self):
        xe = ex.sin(ex.var("t"))
        ye = ex.cos(ex.var("t"))
        r = rc.parametric(xe, ye, t_max=2 * math.pi, count=64)
        pts = rc.eval_recipe(r)
        self.assertEqual(len(pts), 64)
        for i in range(64):
            t = 2 * math.pi * i / 63
            self.assertAlmostEqual(pts[i][0], math.sin(t), places=9)
            self.assertAlmostEqual(pts[i][1], math.cos(t), places=9)

    def test_recipe_is_json_serializable(self):
        import json
        r = rc.iterated(ex.var("x"), ex.var("y"), [0.1, 0.1], 0, 10)
        json.dumps(r)  # must not raise


if __name__ == "__main__":
    unittest.main()
