"""Compositor: the composition criterion ranks coherence; compose() builds a layered World."""
from __future__ import annotations

import json
import unittest

from studio_engine import compose
from studio_engine.criteria import cohesion
from studio_engine.model import World

PAL = ["#101418", "#1a2a3a", "#2dd4bf", "#7a5cff", "#fbbf24", "#e8e8f0"]


class TestCompositionCriterion(unittest.TestCase):
    def test_harmonious_beats_clashing(self):
        harmonious = [{"coverage": 0.85, "contrast": 0.5}, {"coverage": 0.2, "contrast": 0.45}]
        clashing = [{"coverage": 0.9, "contrast": 0.95}, {"coverage": 0.88, "contrast": 0.92}]
        h = cohesion(list(compose.composition_axes(harmonious, PAL).values()))
        c = cohesion(list(compose.composition_axes(clashing, PAL).values()))
        self.assertGreater(h, c)

    def test_axes_present(self):
        a = compose.composition_axes([{"coverage": 0.5, "contrast": 0.5}], PAL)
        self.assertEqual(set(a), {"palette_harmony", "depth_complementarity", "contrast_balance"})


class TestCompose(unittest.TestCase):
    def test_compose_returns_multilayer_world(self):
        w = compose.compose(7, ["gyroid", "phyllotaxis"], corpus_path=None)
        self.assertIsInstance(w, World)
        self.assertEqual(len(w.layers), 2)
        self.assertEqual(len({lyr.z for lyr in w.layers}), 2)  # distinct depth
        self.assertIsNotNone(w.composition)
        json.dumps(w.to_json())

    def test_unknown_generator_raises(self):
        with self.assertRaises(ValueError):
            compose.compose(0, ["not_a_generator"], corpus_path=None)


if __name__ == "__main__":
    unittest.main()
