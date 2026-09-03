"""The drawings in the README, held against the code they describe.

The art gate settles whether a drawing fits its columns and matches the spec it
was rendered from. Both sides of that check read the same JSON, so it cannot
settle whether a drawing is TRUE. That is what this file is for: every count,
threshold and rule the three drawings put on the page is asserted here against
the code that produces it, so a claim that stops holding fails the suite rather
than staying on the page. The engine already has its own tests beside it, and
nothing here repeats them.

Writing these caught one false claim. The refine lane said one seed rebuilds the
same world with no mention of the novelty corpus, and seed 7 on gyroid produces
two different worlds when the corpus grows between the runs. The drawing was
corrected; the check was not loosened.
"""
from __future__ import annotations

import inspect
import json
import math
import re
import sys
import tempfile
import unittest
from pathlib import Path

from studio_engine import certify, criteria, engine, raster_renderer
from studio_engine.corpus import FEATURE_KEYS, Corpus
from studio_engine.organs import palette as pal
from studio_engine.registry import _GENS
from studio_engine.strand import expr as sx
from studio_engine.strand import glsl

ROOT = Path(__file__).resolve().parents[1]
DRAWINGS = ("studio-engine-header.svg", "refine-loop.svg", "strand-lane.svg",
            "engine-table.svg")


def spec() -> dict:
    return json.loads((ROOT / "docs/art/studio-engine.art.json").read_text(encoding="utf-8"))


def readme() -> str:
    return (ROOT / "README.md").read_text(encoding="utf-8")


def build(**kwargs):
    """The collected form of the loop, which is what the CLI and the server hold."""
    return engine.simulate(**kwargs)


class DrawingsReachThePage(unittest.TestCase):
    def test_every_drawing_is_committed_and_embedded(self):
        """A rendered file nobody embeds is a file nobody sees, so both are checked."""
        page = readme()
        for name in DRAWINGS:
            self.assertTrue((ROOT / "docs/art" / name).is_file(), name)
            self.assertIn("docs/art/%s" % name, page, name)

    def test_the_alt_text_on_the_page_is_the_alt_text_in_the_spec(self):
        """A screen reader gets the alt text, not the picture, so the two are pinned."""
        page = readme()
        drawn = spec()["flows"] + spec()["cards"]
        for drawing in drawn:
            self.assertIn("![%s](docs/art/%s)" % (drawing["alt"], drawing["file"]), page)
        self.assertEqual(len(drawn), 3)

    def test_the_art_gate_passes_on_this_checkout(self):
        """The gate as a receipt, so the delivery suite covers the front page too."""
        sys.path.insert(0, str(ROOT / "tools"))
        import check_repo_art

        receipt = check_repo_art.receipt()
        failed = [item["name"] for item in receipt["checks"] if not item["passed"]]
        self.assertEqual(failed, [])
        self.assertEqual(len(receipt["outputs"]), len(DRAWINGS))


class TheRefineLane(unittest.TestCase):
    def test_ten_generators_ship_and_the_card_names_them_all(self):
        """The card lists them by name, so the list is held to the registry."""
        self.assertEqual(len(_GENS), 10)
        row = [f for f in spec()["cards"][0]["fields"] if f["key"] == "generators"][0]
        named = {w.strip(" .") for w in row["note"].lower().replace(" and ", ", ").split(",")}
        self.assertEqual(named, set(_GENS))

    def test_one_seed_against_one_corpus_rebuilds_the_same_world(self):
        """The return edge on the refine lane, checked by building it twice."""
        first = build(seed=7, generator="gyroid", corpus_path=None)
        second = build(seed=7, generator="gyroid", corpus_path=None)
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.layers[0].render_program.expr_sha256,
                         second.layers[0].render_program.expr_sha256)
        self.assertNotEqual(first.id, build(seed=8, generator="gyroid", corpus_path=None).id)

    def test_a_corpus_that_grew_moves_the_world_the_same_seed_makes(self):
        """Why the return edge names the corpus: novelty is measured against history."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "corpus.json"
            first = build(seed=7, generator="gyroid", corpus_path=path)
            second = build(seed=7, generator="gyroid", corpus_path=path)
            self.assertEqual(len(Corpus.load(path)), 2)
            self.assertNotEqual(first.id, second.id)

    def test_the_loop_keeps_the_best_candidate_not_the_last_one(self):
        """The footnote's claim, checked against the scores the trajectory carries."""
        trajectory = build(seed=3, generator="turbulence", corpus_path=None).trajectory
        witness = trajectory.steps[-1]
        self.assertEqual(witness.phase, "witness")
        self.assertEqual(trajectory.accepted_index, len(trajectory.steps) - 1)
        judged = [s.score for s in trajectory.steps if s.phase == "critique"]
        self.assertEqual(witness.score, max(judged))
        source = inspect.getsource(engine.run)
        self.assertIn("if best is None or coh > best[0]:", source)
        self.assertIn("coh, params, feats, margins = best", source)

    def test_converging_needs_the_target_and_every_axis_over_the_floor(self):
        """The bar row draws a conjunction, so the conjunction is what gets checked."""
        world = build(seed=7, generator="gyroid", corpus_path=None)
        witness = world.trajectory.steps[-1]
        expected = witness.score >= 0.9 and all(v >= 0.6 for v in witness.margins.values())
        self.assertEqual(world.trajectory.converged, expected)

    def test_the_defaults_the_card_draws_are_the_run_defaults(self):
        """Sixteen steps, a target of nine tenths, a floor of six tenths."""
        params = inspect.signature(engine.run).parameters
        self.assertEqual(params["max_steps"].default, 16)
        self.assertEqual(params["target"].default, 0.9)
        self.assertEqual(params["floor"].default, 0.6)
        self.assertEqual(params["scheme"].default, "analogous")

    def test_a_stalled_pass_shrinks_the_step_and_the_loop_stops(self):
        """The second return edge. The schedule lives as literals inside the loop."""
        source = inspect.getsource(engine.run)
        self.assertIn("frac = 0.34", source)
        self.assertIn("frac *= 0.55", source)
        self.assertIn("frac < 0.02", source)
        shrinks, frac = 0, 0.34
        while frac >= 0.02:
            frac *= 0.55
            shrinks += 1
        self.assertEqual(shrinks, 5)


class TheCriteria(unittest.TestCase):
    def test_seven_axes_split_three_objective_and_four_subjective(self):
        """The count and the split, both drawn on the card."""
        kinds = [k for k, _ in criteria.REGISTRY.values()]
        self.assertEqual(len(criteria.REGISTRY), 7)
        self.assertEqual(kinds.count("objective"), 3)
        self.assertEqual(kinds.count("subjective"), 4)

    def test_an_objective_axis_reads_the_parameter_and_ignores_the_output(self):
        """The card says the split is about WHAT is judged, so that is what is tested."""
        blank, full = {}, {k: 0.9 for k in FEATURE_KEYS}
        for axis, (kind, _) in criteria.REGISTRY.items():
            with self.subTest(axis=axis):
                if kind == "objective":
                    self.assertEqual(criteria.score(axis, blank, {}),
                                     criteria.score(axis, full, {}))
                else:
                    self.assertEqual(criteria.score(axis, blank, {}),
                                     criteria.score(axis, blank, {"angle": 1.0, "freq": 3.3}))

    def test_an_objective_axis_is_graded_against_a_constant_it_did_not_author(self):
        """Golden angle is the clearest case: perfect at the constant, falling away."""
        exact = criteria.score("golden_angle", {}, {"angle": criteria.GOLDEN_ANGLE})
        near = criteria.score("golden_angle", {}, {"angle": criteria.GOLDEN_ANGLE + 5})
        far = criteria.score("golden_angle", {}, {"angle": criteria.GOLDEN_ANGLE + 40})
        self.assertEqual(exact, 1.0)
        self.assertTrue(exact > near > far == 0.0)

    def test_cohesion_is_the_harmonic_mean_so_one_weak_axis_tanks_it(self):
        """The row says an arithmetic mean would average a flaw away. It would."""
        scores = [1.0, 1.0, 1.0, 0.1]
        self.assertAlmostEqual(criteria.cohesion(scores), 4 / (1 + 1 + 1 + 10))
        self.assertLess(criteria.cohesion(scores), sum(scores) / len(scores))
        self.assertAlmostEqual(criteria.cohesion([0.5, 0.5, 0.5]), 0.5)

    def test_the_sample_grid_is_twenty_squared_over_five_features(self):
        """Four hundred cells, five features. Both numbers reach the page."""
        self.assertEqual(engine._G, 20)
        self.assertEqual(engine._G * engine._G, 400)
        self.assertEqual(FEATURE_KEYS,
                         ["coverage", "centroid_offset", "contrast", "entropy", "hue"])

    def test_novelty_is_one_on_an_empty_corpus_and_falls_toward_a_neighbour(self):
        """The row's claim: first of its kind scores one, normalized by the diagonal."""
        empty = Corpus([])
        self.assertEqual(empty.novelty({k: 0.5 for k in FEATURE_KEYS}), 1.0)
        seeded = Corpus([[0.0] * len(FEATURE_KEYS)])
        self.assertEqual(seeded.novelty({k: 0.0 for k in FEATURE_KEYS}), 0.0)
        far = seeded.novelty({k: 1.0 for k in FEATURE_KEYS})
        self.assertAlmostEqual(far, 1.0)
        self.assertAlmostEqual(math.sqrt(len(FEATURE_KEYS)), math.dist([0] * 5, [1] * 5))


class ThePaletteAndTheAlgebra(unittest.TestCase):
    def test_six_swatches_from_four_schemes_at_the_drawn_spreads(self):
        """The palette row: six swatches, hue spread set by the scheme."""
        self.assertEqual(pal.SCHEMES,
                         {"analogous": 44.0, "triadic": 120.0,
                          "complementary": 180.0, "wide": 300.0})
        for scheme in pal.SCHEMES:
            with self.subTest(scheme=scheme):
                swatches = pal.generate_palette(3, scheme=scheme)
                self.assertEqual(len(swatches), 6)
                self.assertTrue(all(re.fullmatch(r"#[0-9a-f]{6}", s) for s in swatches))
        self.assertNotEqual(pal.generate_palette(3, scheme="analogous"),
                            pal.generate_palette(3, scheme="wide"))

    def test_the_algebra_is_twelve_operations_over_six_variables(self):
        """Both counts are drawn, and both are one collection each."""
        self.assertEqual(len(sx.OPS), 12)
        self.assertEqual(sx.VARS, ("u", "v", "t", "x", "y", "i"))
        self.assertEqual(sx.OPS,
                         {"var", "const", "sin", "cos", "exp", "abs", "neg", "sqrt",
                          "add", "mul", "sub", "div"})

    def test_the_shader_guards_division_the_way_the_evaluator_does(self):
        """The lane says the two agree on every input. The guard is why."""
        self.assertEqual(sx._EPS, 1e-3)
        self.assertIn("safediv", glsl.GLSL_HELPERS)
        self.assertIn("1e-3", glsl.GLSL_HELPERS)
        guarded = sx.eval_expr(sx.div(sx.const(1.0), sx.const(0.0)), {})
        self.assertEqual(guarded, 1.0 / sx._EPS)
        self.assertTrue(math.isfinite(guarded))

    def test_the_round_trip_through_glsl_evaluates_equal(self):
        """The first return edge on the strand lane, checked on the shipped program.

        Equal VALUES, not an equal tree. The emitter writes a flat variadic add and the
        parser rebuilds it as left-nested binary adds, which is why the drawing says the
        round trip has to evaluate equal and the renderer compares numbers.
        """
        program = build(seed=7, generator="gyroid", corpus_path=None).layers[0].render_program
        witnessed = sx.from_dict(program.expr_ast)
        body = re.search(r"float field\(float u, float v, float t\)\{ return (.+?); \}",
                         program.source)
        self.assertIsNotNone(body)
        recovered = glsl.parse_glsl(body.group(1))
        for u, v, t in ((-0.6, 0.3, 0.0), (0.2, -0.5, 0.4), (0.8, 0.8, 0.9)):
            env = {"u": u, "v": v, "t": t}
            self.assertAlmostEqual(sx.eval_expr(recovered, env),
                                   sx.eval_expr(witnessed, env), places=9)
        self.assertEqual(sx.sha(witnessed), program.expr_sha256)


class TheRenderPath(unittest.TestCase):
    def test_a_tampered_program_is_refused_before_any_pixel(self):
        """The second return edge on the strand lane, and the REFUSED outcome."""
        import dataclasses

        world = build(seed=7, generator="gyroid", corpus_path=None)
        program = world.layers[0].render_program
        frames = raster_renderer.render_frames(program, ["#101010", "#f0f0f0"], 1.0, n_frames=1,
                                               size=16)
        self.assertEqual(len(frames), 1)
        tampered = dataclasses.replace(program, expr_sha256="0" * 16)
        with self.assertRaises(raster_renderer.FrameError):
            raster_renderer.render_frames(tampered, ["#101010", "#f0f0f0"], 1.0, n_frames=1,
                                          size=16)

    def test_the_strip_is_eight_frames_at_two_hundred_and_fifty_six(self):
        """The last row of the card, read off the signature it is drawn from."""
        params = inspect.signature(raster_renderer.render_frames).parameters
        self.assertEqual(params["n_frames"].default, 8)
        self.assertEqual(params["size"].default, 256)

    def test_a_frame_carries_its_own_hash(self):
        """The row says each frame's sha256 goes into the receipt, so each has one."""
        world = build(seed=7, generator="gyroid", corpus_path=None)
        frames = raster_renderer.render_frames(world.layers[0].render_program,
                                               ["#101010", "#f0f0f0"], 1.0, n_frames=2, size=16)
        self.assertEqual(len(frames), 2)
        for frame in frames:
            self.assertTrue(re.fullmatch(r"[0-9a-f]{16,64}", frame["sha256"]))


class TheExternalVerdict(unittest.TestCase):
    def test_an_absent_oracle_records_unverifiable_rather_than_a_pass(self):
        """The accented row, and the UNCERTIFIED outcome on the refine lane."""
        record = certify.OracleUnavailable(0.95).to_dict()
        self.assertEqual(record["verdict"], "unverifiable")
        self.assertEqual(record["oracle"], "structural-fitness-v1")
        self.assertEqual(record["cohesion"], 0.95)

    def test_the_tolerance_belongs_to_the_oracle_not_to_the_engine_floor(self):
        """The row says the outside bar is its own. It is a different number."""
        self.assertEqual(certify._TOLERANCE, 0.4)
        self.assertNotEqual(certify._TOLERANCE,
                            inspect.signature(engine.run).parameters["floor"].default)


if __name__ == "__main__":
    unittest.main()
