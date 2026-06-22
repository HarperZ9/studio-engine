"""Engine: per-generator World contract, determinism, and run()/simulate() parity.

Every test passes ``corpus_path=None`` so the persistent corpus is never touched
and results stay deterministic.
"""
from __future__ import annotations

import json
import unittest

from studio_engine import engine
from studio_engine.model import World, Scene, Step


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
    """For EVERY generator the emitted World must satisfy the full contract."""

    def test_world_contract(self):
        for gen in engine.generators():
            with self.subTest(generator=gen):
                world = engine.simulate(SEED, generator=gen, corpus_path=None)
                self.assertIsInstance(world, World)

                d = world.to_json()
                json.dumps(d)  # JSON-serializable
                self.assertEqual(d["schema_version"], "studio-engine/2")

                # >= 1 render layer, each carrying a render program with a known target.
                self.assertGreaterEqual(len(d["layers"]), 1)
                self.assertIn("render", [lyr["role"] for lyr in d["layers"]])
                for lyr in d["layers"]:
                    self.assertIn(lyr["render_program"]["target"],
                                  ("glsl-fragment", "point-recipe"))

                # The ear's synth graph is present.
                self.assertIn("audio_program", d)

                # Non-empty trajectory with an accepted step carrying margins.
                steps = d["trajectory"]["steps"]
                self.assertTrue(steps, "trajectory.steps must be non-empty")
                ai = d["trajectory"]["accepted_index"]
                self.assertGreaterEqual(ai, 0)
                self.assertLess(ai, len(steps))
                self.assertTrue(steps[ai].get("margins"), "accepted step must carry margins")

    def test_scene_projection_is_valid(self):
        for gen in engine.generators():
            with self.subTest(generator=gen):
                sc = engine.simulate_scene(SEED, generator=gen, corpus_path=None)
                self.assertIsInstance(sc, Scene)
                json.dumps(sc.to_json())


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
    def test_run_yields_steps_then_single_world(self):
        for gen in engine.generators():
            with self.subTest(generator=gen):
                items = list(engine.run(SEED, generator=gen, corpus_path=None))
                kinds = [k for k, _ in items]

                self.assertEqual(kinds.count("world"), 1)
                self.assertEqual(kinds[-1], "world")
                self.assertGreaterEqual(kinds.count("step"), 1)
                self.assertTrue(all(k == "step" for k in kinds[:-1]))

                for kind, obj in items[:-1]:
                    self.assertEqual(kind, "step")
                    self.assertIsInstance(obj, Step)
                self.assertIsInstance(items[-1][1], World)

    def test_run_world_id_matches_simulate(self):
        for gen in engine.generators():
            with self.subTest(generator=gen):
                items = list(engine.run(SEED, generator=gen, corpus_path=None))
                world = items[-1][1]
                self.assertEqual(world.id, engine.simulate(SEED, generator=gen, corpus_path=None).id)


class TestLibrary(unittest.TestCase):
    def test_library_returns_organ_info_entries(self):
        lib = engine.library()
        self.assertGreater(len(lib), 0)
        ids = [o.id for o in lib]
        self.assertEqual(len(ids), len(set(ids)))  # ids are unique


if __name__ == "__main__":
    unittest.main()
