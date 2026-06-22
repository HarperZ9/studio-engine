import math
import unittest

from studio_engine.strand import expr as ex


class TestExpr(unittest.TestCase):
    def test_const_and_var(self):
        self.assertEqual(ex.eval_expr(ex.const(3.0), {}), 3.0)
        self.assertEqual(ex.eval_expr(ex.var("u"), {"u": 0.5}), 0.5)

    def test_unary_and_binary(self):
        e = ex.add(ex.sin(ex.const(0.0)), ex.cos(ex.const(0.0)))  # 0 + 1
        self.assertAlmostEqual(ex.eval_expr(e, {}), 1.0)
        self.assertAlmostEqual(ex.eval_expr(ex.mul(ex.const(2), ex.const(3)), {}), 6.0)
        self.assertAlmostEqual(ex.eval_expr(ex.sub(ex.const(5), ex.const(2)), {}), 3.0)

    def test_variadic(self):
        self.assertAlmostEqual(ex.eval_expr(ex.add(1, 2, 3, 4), {}), 10.0)
        self.assertAlmostEqual(ex.eval_expr(ex.mul(2, 3, 4), {}), 24.0)

    def test_float_lift(self):
        self.assertAlmostEqual(ex.eval_expr(ex.sin(0.0), {}), 0.0)  # bare float ok

    def test_div_guard(self):
        # division stays finite (matches metaballs' +eps style guard)
        self.assertTrue(math.isfinite(ex.eval_expr(ex.div(1.0, 0.0), {})))

    def test_sha_stable_and_distinct(self):
        a = ex.mul(ex.var("u"), ex.const(2.0))
        b = ex.mul(ex.var("u"), ex.const(2.0))
        c = ex.mul(ex.var("u"), ex.const(3.0))
        self.assertEqual(ex.sha(a), ex.sha(b))
        self.assertNotEqual(ex.sha(a), ex.sha(c))

    def test_sample_field_shape(self):
        grid = ex.sample_field(ex.var("u"), n=4, t=0.0)
        self.assertEqual(len(grid), 16)
        self.assertLess(grid[0], grid[3])  # u increases left->right within a row

    def test_unknown_var_raises(self):
        with self.assertRaises(ValueError):
            ex.var("zzz")


if __name__ == "__main__":
    unittest.main()
