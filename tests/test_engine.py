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


class TestRenderFramesIntegration(unittest.TestCase):
    """render_frames=True drives the headless renderer and grounds frames in the receipt."""

    def test_frames_stream_and_ground_receipt(self):
        import base64
        import hashlib
        items = list(engine.run(SEED, generator="gyroid", corpus_path=None, render_frames=True))
        kinds = [k for k, _ in items]
        # Order: steps..., frames..., then exactly one world (the terminal item).
        self.assertEqual(kinds[-1], "world")
        self.assertEqual(kinds.count("world"), 1)
        frames = [o for k, o in items if k == "frame"]
        self.assertGreater(len(frames), 0)
        world = items[-1][1]
        # Every frame's short sha is carried in the receipt's artifact_shas, and the renderer
        # organ is registered. Re-hashing the shipped PNG reproduces the receipted sha.
        self.assertIn("raster.native-render", world.receipt.organ_ids)
        for fr in frames:
            png = base64.b64decode(fr["png_base64"])
            self.assertTrue(png.startswith(b"\x89PNG"))
            self.assertEqual(hashlib.sha256(png).hexdigest()[:16], fr["sha256"])
            self.assertIn(fr["sha256"], world.receipt.artifact_shas)
            self.assertEqual(fr["delivery_receipt"]["expr_sha256"],
                             world.layers[0].render_program.expr_sha256)

    def test_frames_are_deterministic_across_runs(self):
        a = [o["sha256"] for k, o in
             engine.run(SEED, "gyroid", corpus_path=None, render_frames=True) if k == "frame"]
        b = [o["sha256"] for k, o in
             engine.run(SEED, "gyroid", corpus_path=None, render_frames=True) if k == "frame"]
        self.assertEqual(a, b)

    def test_animatable_strip_spans_the_loop(self):
        frames = [o for k, o in
                  engine.run(SEED, "gyroid", corpus_path=None, render_frames=True) if k == "frame"]
        # Gyroid is animatable -> a multi-frame strip whose frames are not all identical.
        self.assertGreater(len(frames), 1)
        self.assertGreater(len({f["sha256"] for f in frames}), 1)

    def test_point_generator_renders_one_frame(self):
        frames = [o for k, o in
                  engine.run(SEED, "phyllotaxis", corpus_path=None, render_frames=True)
                  if k == "frame"]
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0]["delivery_receipt"]["target"], "point-recipe")

    def test_render_frames_false_yields_no_frames_and_stable_id(self):
        with_flag = engine.simulate(SEED, "gyroid", corpus_path=None, render_frames=True)
        without = engine.simulate(SEED, "gyroid", corpus_path=None, render_frames=False)
        # The world id (scene identity) is independent of whether frames were rendered.
        self.assertEqual(with_flag.id, without.id)
        self.assertNotIn("raster.native-render", without.receipt.organ_ids)


class TestLibrary(unittest.TestCase):
    def test_library_returns_organ_info_entries(self):
        lib = engine.library()
        self.assertGreater(len(lib), 0)
        ids = [o.id for o in lib]
        self.assertEqual(len(ids), len(set(ids)))  # ids are unique


if __name__ == "__main__":
    unittest.main()
