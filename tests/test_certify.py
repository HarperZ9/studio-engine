"""The external oracle: a real coherence-membrane Certificate for a World's cohesion.

studio-engine self-grades cohesion via its own tag(); this routes the converged cohesion through
cm's structural_fitness_criterion (an INDEPENDENT criterion the engine did not author) -> a real
cm Certificate. The verdict authority is cm's, not the engine's -- the anti-self-grading fix."""
import unittest

from coherence_membrane.certificate import Verdict
from studio_engine.certify import world_certificate


class TestWorldCertificate(unittest.TestCase):
    def test_high_cohesion_is_verified(self):
        cert = world_certificate(0.92)
        self.assertIs(cert.verdict, Verdict.VERIFIED)
        self.assertEqual(cert.oracle, "structural-fitness-v1")   # cm's criterion, not studio-engine's tag

    def test_low_cohesion_is_refuted(self):
        self.assertIs(world_certificate(0.40).verdict, Verdict.REFUTED)

    def test_boundary_at_cm_tolerance(self):
        self.assertIs(world_certificate(0.60).verdict, Verdict.VERIFIED)   # cohesion >= 0.6 (tolerance 0.4)
        self.assertIs(world_certificate(0.59).verdict, Verdict.REFUTED)

    def test_certificate_shaped(self):
        d = world_certificate(0.92).to_dict()
        self.assertEqual(set(d), {"claim", "verdict", "oracle", "evidence"})

    def test_simulate_world_carries_the_external_certificate(self):
        from studio_engine import engine
        world = engine.simulate(seed=1, generator="phyllotaxis", max_steps=8)
        self.assertEqual(world.certificate["oracle"], "structural-fitness-v1")
        self.assertIn(world.certificate["verdict"], {"verified", "refuted", "unverifiable"})


class TestSpineOptional(unittest.TestCase):
    """A fresh ``pip install studio-engine`` without the coherence-membrane spine on the path must
    not break on import or on certification: the engine still produces a World, and the external
    verdict degrades to an honest ``unverifiable`` rather than raising ImportError."""

    def test_missing_spine_yields_unverifiable_not_import_error(self):
        import builtins

        from studio_engine.certify import OracleUnavailable, world_certificate

        real_import = builtins.__import__

        def blocked(name, *args, **kwargs):
            if name.startswith("coherence_membrane"):
                raise ImportError("coherence_membrane not installed")
            return real_import(name, *args, **kwargs)

        builtins.__import__ = blocked
        try:
            cert = world_certificate(0.8)
        finally:
            builtins.__import__ = real_import

        self.assertIsInstance(cert, OracleUnavailable)
        payload = cert.to_dict()
        self.assertEqual(payload["verdict"], "unverifiable")
        self.assertEqual(payload["oracle"], "structural-fitness-v1")
        self.assertIn("coherence_membrane", payload["reason"])


if __name__ == "__main__":
    unittest.main()
