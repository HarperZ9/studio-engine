import json
import unittest

from studio_engine.organs import sonify
from studio_engine.strand import webaudio


class TestWebAudio(unittest.TestCase):
    def setUp(self):
        palette = ["#2dd4bf", "#7a5cff", "#fbbf24", "#ff7a5c", "#e8e8f0", "#101418"]
        scores = [0.2, 0.45, 0.7, 0.85, 0.92]
        self.params = json.loads(sonify.audio_params(7, palette, scores).content)
        self.graph = webaudio.emit_webaudio(self.params)

    def test_oscillator_gains_match_partials(self):
        self.assertEqual(len(self.graph["oscillators"]), len(self.params["partials"]))
        for osc, par in zip(self.graph["oscillators"], self.params["partials"]):
            self.assertEqual(osc["harmonic"], par["harmonic"])
            self.assertAlmostEqual(osc["gain"], par["weight"], places=6)

    def test_base_freq_and_pitch_curve_match(self):
        self.assertAlmostEqual(self.graph["base_freq"], self.params["base_freq"], places=6)
        self.assertEqual(len(self.graph["pitch_curve"]), len(self.params["pitch_steps"]))
        for a, b in zip(self.graph["pitch_curve"], self.params["pitch_steps"]):
            self.assertAlmostEqual(a, b, places=6)

    def test_envelope_preserved(self):
        self.assertEqual(self.graph["envelope"], self.params["envelope"])

    def test_graph_is_json_serializable(self):
        json.dumps(self.graph)

    def test_raises_on_non_additive(self):
        with self.assertRaises(ValueError):
            webaudio.emit_webaudio({})


if __name__ == "__main__":
    unittest.main()
