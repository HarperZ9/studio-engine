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

    def test_inject_rejection_surfaced(self):
        """CAN-IT-FAIL #2: a steered value the session clamps must be SURFACED,
        not silently applied. The returned step carries a `rejected` map of
        param -> [user_value, clamped_value] so the UI can warn the operator."""
        s = _sess("gyroid")
        step = s.inject({"freq": 999.0})  # gyroid freq bound is (3.0, 10.0)
        self.assertIn("rejected", step, "inject step must carry a 'rejected' key")
        self.assertIn("freq", step["rejected"], "out-of-bounds freq must be reported")
        user_val, clamped_val = step["rejected"]["freq"]
        self.assertEqual(user_val, 999.0)
        self.assertLessEqual(clamped_val, 10.0)
        self.assertEqual(clamped_val, s.params["freq"])

    def test_inject_in_bounds_not_rejected(self):
        """An in-bounds steer must NOT be flagged as rejected (no false alarm)."""
        s = _sess("gyroid")
        step = s.inject({"freq": 6.0})
        self.assertEqual(step.get("rejected", {}), {}, "in-bounds value must not be rejected")

    def test_state_carries_bounds_for_sliders(self):
        """The frontend slider panel needs each param's (lo, hi) bounds; state must expose them."""
        st = _sess("gyroid").state()
        self.assertIn("bounds", st)
        self.assertIn("freq", st["bounds"])
        lo, hi = st["bounds"]["freq"]
        self.assertEqual([lo, hi], [3.0, 10.0])

    def test_step_and_explain(self):
        s = _sess("gyroid")
        s.step()
        e = s.explain()
        self.assertIn("axis", e)
        self.assertIn("why", e)


if __name__ == "__main__":
    unittest.main()
