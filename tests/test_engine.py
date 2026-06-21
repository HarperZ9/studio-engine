"""Engine: per-generator Scene contract, determinism, and run()/simulate() parity.

Every test passes ``corpus_path=None`` so the persistent corpus is never touched
and results stay deterministic.
"""
from __future__ import annotations

import json
import unittest

from studio_engine import engine
from studio_engine.model import Scene, Step


SEED = 7


class TestGenerators(unittest.TestCase):
    def test_generators_nonempty(self):
        gens = engine.generators()
        self.assertIsInstance(gens, list)
        self.assertGreater(len(gens), 0)

    def test_unknown_generator_raises(self):
        with self.assertRaises(ValueError):
            engine.simulate(SEED, generator="not_a_generator", corpus_path=None)


class TestSimulateContractPerGenerator(unittest.TestCase):
    """For EVERY generator the emitted Scene must satisfy the full contract."""

    def test_scene_contract(self):
        for gen in engine.generators():
            with self.subTest(generator=gen):
                scene = engine.simulate(SEED, generator=gen, corpus_path=None)
                self.assertIsInstance(scene, Scene)

                d = scene.to_json()
                # JSON-serializable.
                json.dumps(d)
                self.assertIsInstance(d, dict)

                # >= 2 layers, including a role=="params" layer.
                self.assertGreaterEqual(len(d["layers"]), 2)
                roles = [layer["role"] for layer in d["layers"]]
                self.assertIn("params", roles)

                # Non-empty trajectory steps.
                steps = d["trajectory"]["steps"]
                self.assertTrue(steps, "trajectory.steps must be non-empty")

                # An accepted step exists and carries non-empty margins.
                accepted_index = d["trajectory"]["accepted_index"]
                self.assertGreaterEqual(accepted_index, 0)
                self.assertLess(accepted_index, len(steps))
                accepted = steps[accepted_index]
                self.assertTrue(
                    accepted.get("margins"),
                    "accepted step must carry non-empty margins",
                )


class TestDeterminism(unittest.TestCase):
    def test_simulate_is_deterministic_with_no_corpus(self):
        for gen in engine.generators():
            with self.subTest(generator=gen):
                a = engine.simulate(SEED, generator=gen, corpus_path=None)
                b = engine.simulate(SEED, generator=gen, corpus_path=None)
                self.assertEqual(a.id, b.id)

    def test_distinct_seeds_differ(self):
        a = engine.simulate(1, generator="phyllotaxis", corpus_path=None)
        b = engine.simulate(2, generator="phyllotaxis", corpus_path=None)
        self.assertNotEqual(a.id, b.id)


class TestRunStream(unittest.TestCase):
    def test_run_yields_steps_then_single_scene(self):
        for gen in engine.generators():
            with self.subTest(generator=gen):
                items = list(engine.run(SEED, generator=gen, corpus_path=None))
                kinds = [k for k, _ in items]

                # One-or-more ("step", Step) then exactly one ("scene", Scene).
                self.assertEqual(kinds.count("scene"), 1)
                self.assertEqual(kinds[-1], "scene")
                self.assertGreaterEqual(kinds.count("step"), 1)
                # The scene is the final item; everything before it is a step.
                self.assertTrue(all(k == "step" for k in kinds[:-1]))

                for kind, obj in items[:-1]:
                    self.assertEqual(kind, "step")
                    self.assertIsInstance(obj, Step)
                self.assertIsInstance(items[-1][1], Scene)

    def test_run_scene_id_matches_simulate(self):
        for gen in engine.generators():
            with self.subTest(generator=gen):
                items = list(engine.run(SEED, generator=gen, corpus_path=None))
                scene = items[-1][1]
                self.assertEqual(scene.id, engine.simulate(SEED, generator=gen, corpus_path=None).id)


class TestLibrary(unittest.TestCase):
    def test_library_returns_organ_info_entries(self):
        lib = engine.library()
        self.assertGreater(len(lib), 0)
        ids = [o.id for o in lib]
        self.assertEqual(len(ids), len(set(ids)))  # ids are unique


if __name__ == "__main__":
    unittest.main()
