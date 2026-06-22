"""Interactive session: live RenderProgram of the steered candidate + the existing cross-examine."""
from __future__ import annotations

import unittest

from studio_engine.session import Session


def _sess(gen="gyroid"):
    return Session(seed=7, generator=gen, corpus_path=None)


class TestSession(unittest.TestCase):
    def test_state_carries_glsl_program_for_fields(self):
        st = _sess("gyroid").state()
        self.assertIn("program", st)
        self.assertEqual(st["program"]["target"], "glsl-fragment")
        self.assertIn("field(", st["program"]["source"])

    def test_state_carries_recipe_program_for_points(self):
        st = _sess("phyllotaxis").state()
        self.assertEqual(st["program"]["target"], "point-recipe")
        self.assertIn(st["program"]["recipe"]["mode"], ("spiral", "iterated", "parametric"))

    def test_program_updates_as_you_steer(self):
        s = _sess("gyroid")
        s.inject({"freq": 4.0})
        a = s.state()["program"]["expr_sha256"]
        s.inject({"freq": 9.0})
        b = s.state()["program"]["expr_sha256"]
        self.assertNotEqual(a, b)  # steering the param changes the live program

    def test_inject_clamps_to_bounds(self):
        s = _sess("gyroid")
        s.inject({"freq": 9999.0})
        self.assertLessEqual(s.params["freq"], 10.0)

    def test_step_and_explain(self):
        s = _sess("gyroid")
        s.step()
        e = s.explain()
        self.assertIn("axis", e)
        self.assertIn("why", e)


if __name__ == "__main__":
    unittest.main()
