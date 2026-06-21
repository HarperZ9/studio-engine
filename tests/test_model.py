"""Model contract: Artifact.finalize() and Scene.to_json() round-tripping."""
from __future__ import annotations

import json
import unittest

from studio_engine.model import (
    Artifact,
    Scene,
    SceneLayer,
    Trajectory,
    Step,
    Verdict,
    Receipt,
    SCHEMA_VERSION,
)


class TestArtifactFinalize(unittest.TestCase):
    def test_finalize_sets_sha256_and_mime_for_svg(self):
        art = Artifact("svg", "<svg></svg>")
        self.assertEqual(art.sha256, "")
        self.assertEqual(art.mime, "")
        returned = art.finalize()
        # finalize mutates in place AND returns self (fluent).
        self.assertIs(returned, art)
        self.assertTrue(art.sha256)
        self.assertEqual(len(art.sha256), 16)  # truncated hex digest
        self.assertEqual(art.mime, "image/svg+xml")

    def test_finalize_mime_per_kind(self):
        cases = {
            "svg": "image/svg+xml",
            "png": "image/png",
            "audio_wav": "audio/wav",
            "audio_params": "application/json",
            "data": "application/json",
        }
        for kind, expected_mime in cases.items():
            with self.subTest(kind=kind):
                art = Artifact(kind, "payload").finalize()
                self.assertEqual(art.mime, expected_mime)

    def test_finalize_is_deterministic_for_same_content(self):
        a = Artifact("data", "identical").finalize()
        b = Artifact("data", "identical").finalize()
        self.assertEqual(a.sha256, b.sha256)

    def test_finalize_distinguishes_content(self):
        a = Artifact("data", "one").finalize()
        b = Artifact("data", "two").finalize()
        self.assertNotEqual(a.sha256, b.sha256)

    def test_finalize_preserves_preset_sha_and_mime(self):
        art = Artifact("svg", "<svg/>", sha256="preset", mime="custom/mime").finalize()
        self.assertEqual(art.sha256, "preset")
        self.assertEqual(art.mime, "custom/mime")


def _minimal_scene() -> Scene:
    art = Artifact("svg", "<svg></svg>").finalize()
    layer = SceneLayer("organ.x", "Layer", art, role="geometry", z=0)
    step = Step(
        0,
        "critique",
        {"angle": 137.5},
        [Verdict("golden_angle", "verified", 0.97, "objective")],
        0.9,
        {"golden_angle": 0.97},
        "golden_angle",
        "note",
    )
    traj = Trajectory([step], accepted_index=0, converged=True)
    receipt = Receipt("sid", 0, ["organ.x"], [art.sha256], 0.9)
    return Scene(
        id="sid",
        title="Test",
        layers=[layer],
        audio=None,
        trajectory=traj,
        receipt=receipt,
        palette=["#7375cb", "#95e194"],
    )


class TestSceneToJson(unittest.TestCase):
    def test_to_json_returns_dict(self):
        d = _minimal_scene().to_json()
        self.assertIsInstance(d, dict)

    def test_to_json_round_trips_through_json_dumps(self):
        d = _minimal_scene().to_json()
        encoded = json.dumps(d)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["id"], "sid")
        self.assertEqual(decoded["schema_version"], SCHEMA_VERSION)
        self.assertEqual(len(decoded["layers"]), 1)
        self.assertEqual(decoded["layers"][0]["role"], "geometry")

    def test_to_json_drops_none_audio(self):
        # _clean() strips None values for compact frontend JSON.
        d = _minimal_scene().to_json()
        self.assertNotIn("audio", d)

    def test_to_json_keeps_audio_when_present(self):
        scene = _minimal_scene()
        scene.audio = Artifact("audio_wav", "QQ==").finalize()
        d = scene.to_json()
        self.assertIn("audio", d)
        self.assertEqual(d["audio"]["mime"], "audio/wav")


if __name__ == "__main__":
    unittest.main()
