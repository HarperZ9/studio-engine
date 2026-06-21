"""Organ smoke tests: geometry, fields, the param-driven generators, palette, sonify, raster.

Scope note on the param-driven generator organs:
  * value(PARAMS0, u, v)  -> flowfield, metaballs, turbulence  (expose PARAMS0 + value)
  * points(PARAMS0, n)    -> attractor, harmonograph           (expose PARAMS0 + points)
  * svg(PARAMS0, palette) -> all five of the above
gyroid/quasicrystal live in fields.py and expose *_svg(...) builders instead of the
PARAMS0/value/points organ shape (their fields are inlined in the engine), so they are
smoke-tested through their dedicated SVG functions.
"""
from __future__ import annotations

import math
import unittest

from studio_engine.organs import (
    geometry,
    fields,
    palette as pal,
    sonify,
    raster,
    attractor,
    harmonograph,
    flowfield,
    metaballs,
    turbulence,
)

PALETTE = ["#7375cb", "#95e194"]

# Organs exposing the field shape: PARAMS0 + value(params, u, v).
FIELD_ORGANS = [
    ("flowfield", flowfield),
    ("metaballs", metaballs),
    ("turbulence", turbulence),
]

# Organs exposing the point-cloud shape: PARAMS0 + points(params, n).
POINT_ORGANS = [
    ("attractor", attractor),
    ("harmonograph", harmonograph),
]

# Every organ that exposes svg(PARAMS0, palette).
SVG_ORGANS = FIELD_ORGANS + POINT_ORGANS


def _is_svg(s) -> bool:
    return isinstance(s, str) and s.startswith("<svg")


class TestGeometry(unittest.TestCase):
    def test_phyllotaxis_returns_points(self):
        pts = geometry.phyllotaxis(50)
        self.assertEqual(len(pts), 50)
        x, y, i = pts[0]
        self.assertIsInstance(x, float)
        self.assertIsInstance(y, float)
        self.assertEqual(i, 0)

    def test_to_svg_starts_with_svg_tag(self):
        pts = geometry.phyllotaxis(50)
        svg = geometry.to_svg(pts, PALETTE)
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.rstrip().endswith("</svg>"))


class TestFieldSvgBuilders(unittest.TestCase):
    """gyroid/quasicrystal SVG builders in fields.py."""

    def test_gyroid_field_svg(self):
        svg = fields.gyroid_field_svg(palette=PALETTE, samples=16)
        self.assertTrue(svg.startswith("<svg"))

    def test_quasicrystal_svg(self):
        svg = fields.quasicrystal_svg(palette=PALETTE, samples=16)
        self.assertTrue(svg.startswith("<svg"))


class TestFieldOrgans(unittest.TestCase):
    def test_value_is_finite_float(self):
        for name, organ in FIELD_ORGANS:
            with self.subTest(organ=name):
                v = organ.value(organ.PARAMS0, 0.1, -0.2)
                self.assertIsInstance(v, float)
                self.assertTrue(math.isfinite(v))


class TestPointOrgans(unittest.TestCase):
    def test_points_returns_tuples(self):
        for name, organ in POINT_ORGANS:
            with self.subTest(organ=name):
                pts = organ.points(organ.PARAMS0, 200)
                self.assertTrue(pts, "points() must return a non-empty sequence")
                first = pts[0]
                self.assertIsInstance(first, tuple)
                self.assertEqual(len(first), 3)
                x, y, _i = first
                self.assertIsInstance(x, float)
                self.assertIsInstance(y, float)


class TestOrganSvg(unittest.TestCase):
    def test_every_organ_svg_starts_with_svg(self):
        for name, organ in SVG_ORGANS:
            with self.subTest(organ=name):
                svg = organ.svg(organ.PARAMS0, PALETTE)
                self.assertTrue(_is_svg(svg), f"{name}.svg did not start with <svg")


class TestPalette(unittest.TestCase):
    def test_generate_palette_shape_and_hex(self):
        colors = pal.generate_palette(7, n=6)
        self.assertEqual(len(colors), 6)
        for c in colors:
            self.assertTrue(c.startswith("#"))
            self.assertEqual(len(c), 7)  # #rrggbb

    def test_generate_palette_deterministic(self):
        self.assertEqual(pal.generate_palette(7, n=6), pal.generate_palette(7, n=6))

    def test_oklch_to_hex_format(self):
        hexstr = pal.oklch_to_hex(0.72, 0.13, 120.0)
        self.assertTrue(hexstr.startswith("#"))
        self.assertEqual(len(hexstr), 7)


class TestSonify(unittest.TestCase):
    def test_audio_params_is_json_artifact(self):
        art = sonify.audio_params(7, PALETTE, [0.2, 0.5, 0.9])
        self.assertEqual(art.kind, "audio_params")
        self.assertEqual(art.mime, "application/json")
        self.assertTrue(art.sha256)

    def test_sonify_produces_wav_artifact(self):
        # Tiny duration to keep the synthesis fast.
        art = sonify.sonify(7, PALETTE, [0.2, 0.9], duration=0.1)
        self.assertEqual(art.kind, "audio_wav")
        self.assertEqual(art.mime, "audio/wav")
        self.assertTrue(art.content)  # base64 payload


class TestRaster(unittest.TestCase):
    def test_render_phyllotaxis_png_artifact(self):
        pts = geometry.phyllotaxis(50)
        art = raster.render_phyllotaxis_png(pts, PALETTE, size=64)
        self.assertEqual(art.kind, "png")
        self.assertEqual(art.mime, "image/png")
        self.assertTrue(art.content)

    def test_write_png_has_signature(self):
        size = 2
        rgb = bytes([10, 20, 30]) * (size * size)
        png = raster.write_png(size, size, rgb)
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"))


if __name__ == "__main__":
    unittest.main()
