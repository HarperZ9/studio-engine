"""Field organs define themselves as strand exprs (the eye backend, grounded).

Three assertions per field: (1) the shipped expr encodes the verified field math (vs an
independent reference, including the time channel t); (2) the engine samples that same expr to
compute the features its criteria judge; (3) the emitted GLSL round-trips to the expr.
"""
from __future__ import annotations

import math
import unittest

from studio_engine import engine
from studio_engine.organs import metaballs as mb
from studio_engine.strand import expr as ex
from studio_engine.strand import glsl

FIELDS = ["gyroid", "quasicrystal", "flowfield", "metaballs", "turbulence", "rings", "moire"]
_SAMPLES = [(-0.7, 0.3), (0.2, -0.5), (0.9, 0.9), (0.0, 0.0), (-0.4, -0.8)]


def _params(spec, seed):
    rng = (seed * 2654435761 + 12345) & 0xFFFFFFFF
    return engine._clamp(spec, spec["params0"](rng))


def _ref(name, P, u, v, t):
    """Independent reference implementation of each verified field (incl. time channel)."""
    if name == "gyroid":
        f = P["freq"]
        return (math.sin(u * f) * math.cos(v * f) + math.sin(v * f) * math.cos(t * f)
                + math.sin(t * f) * math.cos(u * f))
    if name == "quasicrystal":
        w = max(1, int(round(P["waves"])))
        s = P["scale"]
        return sum(math.cos(math.cos(2 * math.pi * k / w) * u * s
                            + math.sin(2 * math.pi * k / w) * v * s + t) for k in range(w))
    if name == "flowfield":
        s, w = P["scale"], P["warp"]
        return math.sin(s * u + w * math.sin(s * v) + t) * math.cos(s * v + w * math.cos(s * u) + t)
    if name == "turbulence":
        f0, octs, g = P["freq"], int(round(P["octaves"])), P["gain"]
        acc, amp = 0.0, 0.0
        for o in range(octs):
            fr, a = f0 * (2 ** o), g ** o
            amp += a
            acc += a * math.sin(fr * u + math.sin(fr * v) + t) * math.cos(fr * v)
        return acc / (amp if amp else 1.0)
    if name == "metaballs":
        tot = 0.0
        for (cx, cy, r) in mb._seeds(P):
            tot += (r * r) / ((u - cx) ** 2 + (v - cy) ** 2 + 1e-3)
        return tot * P["falloff"]
    if name == "rings":
        return math.sin(math.sqrt(u * u + v * v) * P["freq"] + t)
    if name == "moire":
        f, a = P["freq"], P["angle"]
        return math.sin(u * f + t) * math.sin((u * math.cos(a) + v * math.sin(a)) * f + t)
    raise AssertionError(name)


class TestFieldExprs(unittest.TestCase):
    def test_expr_encodes_verified_field(self):
        gens = engine._gens()
        for name in FIELDS:
            spec = gens[name]
            for seed in (1, 7, 42):
                P = _params(spec, seed)
                e = spec["expr"](P)
                for (u, v) in _SAMPLES:
                    for t in (0.0, 0.6, 1.7):
                        with self.subTest(field=name, seed=seed, u=u, v=v, t=t):
                            self.assertAlmostEqual(
                                ex.eval_expr(e, {"u": u, "v": v, "t": t}),
                                _ref(name, P, u, v, t), places=9)

    def test_engine_field_is_verified_math(self):
        # Non-circular: the engine's feature-field (the values its criteria judge) equals the
        # independent reference at the static slice -- NOT eval(expr) compared against eval(expr).
        gens = engine._gens()
        for name in FIELDS:
            spec = gens[name]
            P = _params(spec, 7)
            t0 = spec["t0"](P)
            for (u, v) in _SAMPLES:
                with self.subTest(field=name, u=u, v=v):
                    self.assertAlmostEqual(spec["field"](P, u, v),
                                           _ref(name, P, u, v, t0), places=9)

    def test_glsl_roundtrip(self):
        gens = engine._gens()
        for name in FIELDS:
            spec = gens[name]
            e = spec["expr"](_params(spec, 7))
            back = glsl.parse_glsl(glsl.emit_glsl(e))
            for (u, v) in _SAMPLES:
                for t in (0.0, 0.5, 1.7):
                    with self.subTest(field=name, u=u, v=v, t=t):
                        env = {"u": u, "v": v, "t": t}
                        self.assertAlmostEqual(ex.eval_expr(e, env), ex.eval_expr(back, env), places=6)

    def test_animatable_flags(self):
        gens = engine._gens()
        self.assertFalse(gens["metaballs"]["animatable"])
        for name in ("gyroid", "quasicrystal", "flowfield", "turbulence"):
            self.assertTrue(gens[name]["animatable"])
            self.assertGreater(gens[name]["period"](_params(gens[name], 7)), 0.0)


if __name__ == "__main__":
    unittest.main()
