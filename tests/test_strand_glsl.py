import unittest

from studio_engine.strand import expr as ex
from studio_engine.strand import glsl


def _roundtrip_equal(e, samples=((-0.7, 0.3, 0.0), (0.2, -0.5, 1.1), (0.9, 0.9, 0.4))):
    back = glsl.parse_glsl(glsl.emit_glsl(e))
    for (u, v, t) in samples:
        env = {"u": u, "v": v, "t": t}
        if abs(ex.eval_expr(e, env) - ex.eval_expr(back, env)) > 1e-6:
            return False
    return True


class TestGlsl(unittest.TestCase):
    def test_emit_basic(self):
        src = glsl.emit_glsl(ex.add(ex.sin(ex.var("u")), ex.var("v")))
        self.assertIn("sin(u)", src)
        self.assertEqual(src.count("("), src.count(")"))  # balanced

    def test_roundtrip_arith(self):
        e = ex.sub(ex.mul(ex.var("u"), 2.0), ex.div(ex.var("v"), 3.0))
        self.assertTrue(_roundtrip_equal(e))

    def test_roundtrip_nested(self):
        e = ex.mul(ex.sin(ex.add(ex.mul(4.0, ex.var("u")), ex.sin(ex.mul(4.0, ex.var("v"))))),
                   ex.cos(ex.var("t")))
        self.assertTrue(_roundtrip_equal(e))

    def test_roundtrip_div_guard(self):
        e = ex.div(ex.const(1.0), ex.add(ex.mul(ex.var("u"), ex.var("u")), ex.const(0.0)))
        self.assertTrue(_roundtrip_equal(e))

    def test_roundtrip_negative_const(self):
        e = ex.add(ex.mul(ex.const(-2.5), ex.var("u")), ex.const(-1.0))
        self.assertTrue(_roundtrip_equal(e))

    def test_roundtrip_variadic(self):
        e = ex.add(ex.sin(ex.var("u")), ex.cos(ex.var("v")), ex.sin(ex.var("t")))
        self.assertTrue(_roundtrip_equal(e))

    def test_only_allowed_tokens(self):
        src = glsl.emit_glsl(ex.exp(ex.neg(ex.absx(ex.var("u")))))
        for tok in ("exp", "abs", "u"):
            self.assertIn(tok, src)


if __name__ == "__main__":
    unittest.main()
