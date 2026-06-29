"""The two-way native render bridge: param -> subprocess -> channels round-trip,
honest absence when the binary is not built, and the certificate landing in a
session step. The native CLI is MOCKED so these tests need no compiled binary.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from studio_engine.native_render import (
    RenderParams, native_render, build_argv, locate_binary, ENV_BINARY,
)
from studio_engine.session import Session

# A REAL file standing in for the compiled CLI. native_render verifies the binary
# exists (honesty), but actual execution is via the injected `runner`, so the file
# contents are irrelevant. Created once for the module.
_BIN_DIR: tempfile.TemporaryDirectory | None = None
FAKE_BIN = ""


def setUpModule():
    global _BIN_DIR, FAKE_BIN
    _BIN_DIR = tempfile.TemporaryDirectory(prefix="raw_native_bin_")
    FAKE_BIN = str(Path(_BIN_DIR.name) / "raw_native_cli")
    Path(FAKE_BIN).write_text("#!stub\n", encoding="utf-8")


def tearDownModule():
    if _BIN_DIR is not None:
        _BIN_DIR.cleanup()


# A representative channels.json shaped exactly like the raw-native CLI emits.
def _channels_doc(headroom=0.88, motion_valid=2378, motion_total=2378):
    return {
        "schema": "raw-channels/1",
        "frame": {"width": 64, "height": 64, "files": {"ppm": "frame.ppm"}},
        "camera": {"eye": [4, 4, 6], "target": [0, 1, 0], "up": [0, 1, 0],
                   "fovy": 0.9, "aspect": 1.0, "prev": None},
        "certificate": {
            "claim": "screen-space AO matches ray-traced ground truth within tolerance",
            "verdict": "verified", "oracle": "raw-rt-ao-v1",
            "evidence": [["pixels", "2378"], ["rmse", "0.0912"]],
            "channels": {"ao_fidelity": 0.9164, "motion_coherence": 1, "hdr_headroom": headroom},
        },
        "channels": {
            "coverage": 0.58,
            "depth": {"min": 6.2, "max": 13.5, "mean": 10.1},
            "normal": {"mean": [0.07, 0.99, 0.13]},
            "motion": {"valid": motion_valid, "total": motion_total, "coherence": 1,
                       "max_magnitude": 0.0, "mean_magnitude": 0.0},
            "hdr": {"headroom": headroom, "clipping_fraction": 0.0},
            "ao": {"rmse": 0.0912, "max_error": 0.39, "fidelity": 0.9164, "within_tolerance": True},
            "readout": {"kind": "luminance", "width": 8, "height": 8, "rows": [[0.0] * 8] * 8},
        },
    }


def _fake_runner(returncode=0, doc=None, write=True):
    """Build a runner(argv, ...) stand-in that emulates the CLI: it writes a
    channels.json into the --out dir (if write) and returns a CompletedProcess-like."""
    doc = doc if doc is not None else _channels_doc()
    calls: list[list[str]] = []

    def runner(argv, capture_output=True, text=True, timeout=None):
        calls.append(list(argv))
        out_dir = argv[argv.index("--out") + 1]
        if write and returncode == 0:
            Path(out_dir, "channels.json").write_text(json.dumps(doc), encoding="utf-8")
        return SimpleNamespace(returncode=returncode, stdout="param error: boom\n", stderr="")

    runner.calls = calls  # type: ignore[attr-defined]
    return runner


class TestParamMapping(unittest.TestCase):
    def test_build_argv_maps_params_to_flags(self):
        p = RenderParams(width=80, height=40, eye=(1, 2, 3), target=(0, 0.5, 0),
                         up=(0, 1, 0), fovy=0.75)
        argv = build_argv("CLI", p, "OUT")
        self.assertEqual(argv[0], "CLI")
        self.assertIn("--out", argv)
        self.assertEqual(argv[argv.index("--out") + 1], "OUT")
        self.assertEqual(argv[argv.index("--width") + 1], "80")
        self.assertEqual(argv[argv.index("--height") + 1], "40")
        self.assertEqual(argv[argv.index("--eye") + 1], "1.0,2.0,3.0")
        self.assertEqual(argv[argv.index("--target") + 1], "0.0,0.5,0.0")
        self.assertNotIn("--prev-eye", argv)  # absent prev camera -> no flag (honest static)

    def test_build_argv_includes_prev_camera_when_set(self):
        p = RenderParams(prev_eye=(3, 4, 6), prev_target=(0, 1, 0))
        argv = build_argv("CLI", p, "OUT")
        self.assertEqual(argv[argv.index("--prev-eye") + 1], "3.0,4.0,6.0")
        self.assertIn("--prev-target", argv)

    def test_from_dict_parses_view(self):
        p = RenderParams.from_dict({"width": 48, "eye": [-4, 4, 6], "fovy": 0.8})
        self.assertEqual(p.width, 48)
        self.assertEqual(p.eye, (-4.0, 4.0, 6.0))
        self.assertEqual(p.fovy, 0.8)

    def test_from_dict_rejects_bad_vector(self):
        with self.assertRaises(ValueError):
            RenderParams.from_dict({"eye": [1, 2]})  # not a 3-vector


class TestSubprocessInvocation(unittest.TestCase):
    def test_param_drives_subprocess_and_channels_round_trip(self):
        runner = _fake_runner()
        res = native_render({"width": 64, "height": 64, "eye": [4, 4, 6]},
                            binary=FAKE_BIN, runner=runner)
        # the subprocess was invoked with our mapped argv
        self.assertEqual(len(runner.calls), 1)  # type: ignore[attr-defined]
        self.assertIn("--width", runner.calls[0])  # type: ignore[attr-defined]
        # the channels + certificate round-tripped back honestly
        self.assertTrue(res.available)
        self.assertTrue(res.ok)
        self.assertEqual(res.certificate["verdict"], "verified")
        self.assertEqual(res.channels["hdr"]["headroom"], 0.88)
        self.assertEqual(res.camera["eye"], [4, 4, 6])

    def test_temp_output_dir_is_cleaned_up(self):
        captured = {}

        def runner(argv, capture_output=True, text=True, timeout=None):
            out_dir = argv[argv.index("--out") + 1]
            captured["dir"] = out_dir
            Path(out_dir, "channels.json").write_text(json.dumps(_channels_doc()), encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        native_render({}, binary=FAKE_BIN, runner=runner)
        self.assertFalse(Path(captured["dir"]).exists())  # temp dir removed


class TestHonestAbsence(unittest.TestCase):
    def test_absent_binary_is_honest_never_fake(self):
        old = os.environ.pop(ENV_BINARY, None)
        try:
            res = native_render({"width": 64}, binary=None)  # nothing configured
        finally:
            if old is not None:
                os.environ[ENV_BINARY] = old
        self.assertFalse(res.available)
        self.assertFalse(res.ok)
        self.assertIsNone(res.certificate)   # NEVER a fabricated channel
        self.assertIsNone(res.channels)
        self.assertIn("not built", res.reason)

    def test_locate_binary_none_when_missing(self):
        self.assertIsNone(locate_binary("C:/no/such/raw_native_cli_xyz.exe"))

    def test_nonzero_exit_is_honest_failure(self):
        runner = _fake_runner(returncode=2, write=False)
        res = native_render({}, binary=FAKE_BIN, runner=runner)
        self.assertTrue(res.available)   # the binary exists / ran
        self.assertFalse(res.ok)         # but failed
        self.assertIsNone(res.channels)
        self.assertIn("exited 2", res.reason)

    def test_missing_channels_file_is_honest_failure(self):
        runner = _fake_runner(returncode=0, write=False)  # success exit, but no file
        res = native_render({}, binary=FAKE_BIN, runner=runner)
        self.assertFalse(res.ok)
        self.assertIn("no channels.json", res.reason)


class TestSessionRoundTrip(unittest.TestCase):
    def _patch_session_native(self, runner):
        """Point the session's native_render at our mocked runner + binary."""
        import studio_engine.session as sess_mod

        def patched(params=None, *, binary=None):
            from studio_engine.native_render import native_render as nr
            return nr(params, binary=FAKE_BIN, runner=runner)

        self._orig = sess_mod.native_render
        sess_mod.native_render = patched
        self.addCleanup(lambda: setattr(sess_mod, "native_render", self._orig))

    def test_render_step_lands_certificate_in_session(self):
        runner = _fake_runner()
        self._patch_session_native(runner)
        s = Session(seed=7, generator="gyroid", corpus_path=None)
        step = s.render_step({"width": 64, "height": 64, "eye": [4, 4, 6]})
        self.assertEqual(step["kind"], "native-render")
        self.assertTrue(step["ok"])
        self.assertEqual(step["verdict"], "verified")
        self.assertEqual(step["channels"]["hdr"]["headroom"], 0.88)
        # the native render is recorded in the session state, alongside refine history
        st = s.state()
        self.assertEqual(len(st["native_renders"]), 1)
        self.assertEqual(st["last_camera"]["eye"], [4, 4, 6])
        self.assertIn(step, st["history"])

    def test_second_render_feeds_prev_camera_for_motion(self):
        runner = _fake_runner()
        self._patch_session_native(runner)
        s = Session(seed=7, generator="gyroid", corpus_path=None)
        s.render_step({"eye": [4, 4, 6]})            # first view -> sets last_camera
        s.render_step({"eye": [-4, 4, 6]})           # steer -> should reuse prev camera
        # the SECOND invocation carried a --prev-eye derived from the first view
        second = runner.calls[-1]  # type: ignore[attr-defined]
        self.assertIn("--prev-eye", second)
        self.assertEqual(second[second.index("--prev-eye") + 1], "4.0,4.0,6.0")

    def test_existing_step_inject_still_work(self):
        # the additive native loop must not disturb the original two-way cross-examine
        s = Session(seed=7, generator="gyroid", corpus_path=None)
        before = s.n
        s.step()
        s.inject({"freq": 4.0})
        self.assertEqual(s.n, before + 2)
        self.assertIn("axis", s.explain())


if __name__ == "__main__":
    unittest.main()
