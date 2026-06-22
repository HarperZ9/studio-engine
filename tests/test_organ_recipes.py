"""Point organs expose strand recipes that reproduce their own verified points exactly."""
from __future__ import annotations

import json
import unittest

from studio_engine import engine
from studio_engine.strand import recipe as rc
from studio_engine.organs import geometry, attractor, harmonograph

POINTS = {
    "phyllotaxis": lambda P: geometry.phyllotaxis(700, P["angle"], P["scale"]),
    "attractor": lambda P: attractor.points(P, 3000),
    "harmonograph": lambda P: harmonograph.points(P, 4000),
}


def _params(spec, seed):
    rng = (seed * 2654435761 + 12345) & 0xFFFFFFFF
    return engine._clamp(spec, spec["params0"](rng))


class TestPointRecipes(unittest.TestCase):
    def test_recipe_reproduces_points(self):
        gens = engine._gens()
        for name, pts_fn in POINTS.items():
            spec = gens[name]
            for seed in (1, 7, 42):
                P = _params(spec, seed)
                rpts = rc.eval_recipe(spec["recipe"](P))
                opts = pts_fn(P)
                with self.subTest(gen=name, seed=seed):
                    self.assertEqual(len(rpts), len(opts))
                    for (a, b) in zip(rpts[:50], opts[:50]):
                        self.assertAlmostEqual(a[0], b[0], places=8)
                        self.assertAlmostEqual(a[1], b[1], places=8)
                        self.assertEqual(a[2], b[2])

    def test_recipe_is_json(self):
        gens = engine._gens()
        for name in POINTS:
            json.dumps(gens[name]["recipe"](_params(gens[name], 7)))


if __name__ == "__main__":
    unittest.main()
