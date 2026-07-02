"""The live renderer: turn the emitted RenderProgram into pixels the user can SEE.

The renderer consumes the EXACT SAME witnessed RenderProgram the browser chamber would --
it reparses the shipped GLSL field() body back to a strand Expr, re-hashes it, and refuses to
render if that hash no longer matches the receipt's expr_sha256 (tamper detection). Field
programs sample the verified expr over a grid; point programs replay the verified recipe. Output
is a deterministic PNG (same world + params -> byte-identical frame -> identical sha), so a
rendered frame is both the merit artifact AND a re-checkable accountability receipt.
"""
from __future__ import annotations

import hashlib
import re
import unittest

from studio_engine import engine
from studio_engine.raster_renderer import RasterRenderer, FrameError


def _gyroid_world():
    return engine.simulate(7, "gyroid", corpus_path=None)


def _phyllotaxis_world():
    return engine.simulate(7, "phyllotaxis", corpus_path=None)


class TestFieldRasterization(unittest.TestCase):
    def test_render_field_outputs_png_bytes(self):
        """A glsl-fragment RenderProgram renders to valid PNG bytes."""
        prog = _gyroid_world().layers[0].render_program
        self.assertEqual(prog.target, "glsl-fragment")
        png = RasterRenderer().render_field(prog, width=64, height=64, t=0.0)
        self.assertIsInstance(png, (bytes, bytearray))
        self.assertTrue(bytes(png).startswith(b"\x89PNG"))

    def test_frame_dimensions_honored(self):
        """The rendered PNG carries the requested width/height in its IHDR."""
        prog = _gyroid_world().layers[0].render_program
        png = RasterRenderer().render_field(prog, width=48, height=32, t=0.0)
        # IHDR width/height are the two big-endian uint32s right after the 8-byte sig + 8-byte
        # (length+type) chunk header.
        w = int.from_bytes(png[16:20], "big")
        h = int.from_bytes(png[20:24], "big")
        self.assertEqual((w, h), (48, 32))

    def test_frame_hash_is_deterministic(self):
        """Same world + params -> byte-identical PNG -> identical sha."""
        prog = _gyroid_world().layers[0].render_program
        r = RasterRenderer()
        f1 = r.render_field(prog, 64, 64, t=0.0)
        f2 = r.render_field(prog, 64, 64, t=0.0)
        self.assertEqual(hashlib.sha256(f1).hexdigest(), hashlib.sha256(f2).hexdigest())

    def test_animatable_field_moves_across_period(self):
        """An animatable field renders distinct frames as t sweeps the loop."""
        prog = _gyroid_world().layers[0].render_program
        if not prog.domain.get("animatable"):
            self.skipTest("gyroid not animatable in this build")
        period = prog.domain["period"]
        self.assertGreater(period, 0.0)
        r = RasterRenderer()
        f0 = r.render_field(prog, 64, 64, t=0.0)
        fmid = r.render_field(prog, 64, 64, t=period / 2)
        self.assertNotEqual(f0, fmid)  # not a frozen frame

    def test_distinct_worlds_render_distinct_frames(self):
        """A different verified expr yields a different frame hash (pixels track the math)."""
        p1 = engine.simulate(7, "gyroid", corpus_path=None).layers[0].render_program
        p2 = engine.simulate(8, "gyroid", corpus_path=None).layers[0].render_program
        r = RasterRenderer()
        h1 = hashlib.sha256(r.render_field(p1, 64, 64, t=0.0)).hexdigest()
        h2 = hashlib.sha256(r.render_field(p2, 64, 64, t=0.0)).hexdigest()
        self.assertNotEqual(h1, h2)


class TestPointRasterization(unittest.TestCase):
    def test_point_recipe_renders_png(self):
        """A point-recipe RenderProgram rasterizes to valid PNG."""
        world = _phyllotaxis_world()
        prog = world.layers[0].render_program
        self.assertEqual(prog.target, "point-recipe")
        png = RasterRenderer().render_points(prog, 128, 128, world.palette)
        self.assertTrue(png.startswith(b"\x89PNG"))

    def test_point_frame_is_deterministic(self):
        world = _phyllotaxis_world()
        prog = world.layers[0].render_program
        r = RasterRenderer()
        f1 = r.render_points(prog, 128, 128, world.palette)
        f2 = r.render_points(prog, 128, 128, world.palette)
        self.assertEqual(f1, f2)


class TestPointTamperDetection(unittest.TestCase):
    """The can-it-FAIL negative for the point path: a tampered recipe (whose hash no longer
    matches expr_sha256) is refused BEFORE any pixel -- symmetric with the field path."""

    def test_tampered_recipe_is_rejected(self):
        """Mutating a recipe field (e.g. count) so its hash != expr_sha256 fails before rasterizing."""
        world = _phyllotaxis_world()
        prog = world.layers[0].render_program
        self.assertEqual(prog.target, "point-recipe")
        # Corrupt the recipe while leaving the receipted expr_sha256 intact.
        prog.recipe["count"] = int(prog.recipe.get("count", 0)) + 1
        r = RasterRenderer()
        with self.assertRaises(FrameError) as ctx:
            r.render_points(prog, 128, 128, world.palette)
        self.assertIn("expr_sha256 mismatch", str(ctx.exception))

    def test_tampered_recipe_sha_is_rejected(self):
        """Corrupting the claimed expr_sha256 (recipe intact) is also caught."""
        world = _phyllotaxis_world()
        prog = world.layers[0].render_program
        prog.expr_sha256 = "0000000000000000"
        r = RasterRenderer()
        with self.assertRaises(FrameError) as ctx:
            r.render_points(prog, 128, 128, world.palette)
        self.assertIn("expr_sha256 mismatch", str(ctx.exception))

    def test_verified_point_program_renders(self):
        """The untampered point program passes verification and produces pixels."""
        world = _phyllotaxis_world()
        prog = world.layers[0].render_program
        png = RasterRenderer().render_points(prog, 64, 64, world.palette)
        self.assertTrue(png.startswith(b"\x89PNG"))


class TestFieldOrientation(unittest.TestCase):
    """The PNG's row order must match WebGL's gl_FragCoord.y origin (bottom-left): the TOP row of
    the emitted PNG must sample v=+1, so the headless frame matches what the browser shader draws."""

    def test_top_row_maps_to_v_plus_one(self):
        """A vertical-gradient field ( field==v ) must be brightest at the TOP of the PNG.

        In WebGL, gl_FragCoord.y increases upward, so v=+1 is the top of the viewport. If the
        renderer wrote v=-1 at the top (a vertical flip), the gradient would be inverted relative
        to the browser. We build a program whose field is exactly `v`, render it, and assert the
        top scanline is brighter than the bottom scanline.
        """
        from studio_engine.model import RenderProgram
        from studio_engine.organs import program as prog_mod
        from studio_engine.strand import expr as ex

        e = ex.var("v")
        rp = prog_mod.field_program("vgrad", e, ["#000000", "#ffffff"], 0.0,
                                    animatable=False, period=0.0)
        self.assertEqual(rp.target, "glsl-fragment")
        self.assertIsInstance(rp, RenderProgram)
        png = RasterRenderer().render_field(rp, 8, 8, t=0.0)
        top, bottom = _row_luma(png, 8, 8, 0), _row_luma(png, 8, 8, 7)
        # v=+1 (bright) at the top row, v=-1 (dark) at the bottom row.
        self.assertGreater(top, bottom)


def _row_luma(png: bytes, w: int, h: int, row: int) -> int:
    """Decode a bare no-filter RGB PNG and return the summed luma of one scanline."""
    import zlib
    # IDAT is the chunk after IHDR; parse chunks to find it.
    i = 8
    idat = b""
    while i < len(png):
        length = int.from_bytes(png[i:i + 4], "big")
        tag = png[i + 4:i + 8]
        data = png[i + 8:i + 8 + length]
        if tag == b"IDAT":
            idat += data
        i += 12 + length
    raw = zlib.decompress(idat)
    stride = w * 3 + 1  # +1 filter byte per scanline
    start = row * stride + 1  # skip the filter byte
    scan = raw[start:start + w * 3]
    return sum(scan)


class TestTamperDetection(unittest.TestCase):
    """The can-it-FAIL negative test: the renderer validates the shipped program against the
    receipt BEFORE producing pixels, so a tampered AST/shader/hash is rejected, not rendered."""

    def test_tampered_ast_is_rejected(self):
        """Mutating a constant in expr_ast so its hash != expr_sha256 fails before rasterizing."""
        prog = _gyroid_world().layers[0].render_program
        node = prog.expr_ast
        # Walk to the first const leaf and corrupt its value.
        _corrupt_first_const(node)
        r = RasterRenderer()
        with self.assertRaises(FrameError) as ctx:
            r.render_field(prog, 64, 64, t=0.0)
        self.assertIn("expr_sha256 mismatch", str(ctx.exception))

    def test_tampered_sha_is_rejected(self):
        """Corrupting the claimed expr_sha256 (AST intact) is also caught."""
        prog = _gyroid_world().layers[0].render_program
        prog.expr_sha256 = "0000000000000000"
        r = RasterRenderer()
        with self.assertRaises(FrameError) as ctx:
            r.render_field(prog, 64, 64, t=0.0)
        self.assertIn("expr_sha256 mismatch", str(ctx.exception))

    def test_missing_ast_is_rejected(self):
        """A program with no expr_ast cannot be honestly rendered."""
        prog = _gyroid_world().layers[0].render_program
        prog.expr_ast = None
        r = RasterRenderer()
        with self.assertRaises(FrameError):
            r.render_field(prog, 32, 32, t=0.0)

    def test_tampered_shader_source_is_rejected(self):
        """AST + hash agree, but a mutated GLSL field() body is caught by the eval cross-check."""
        prog = _gyroid_world().layers[0].render_program
        # Rewrite ONLY the field() body, inserting a wrong constant term.
        prog.source = re.sub(
            r"(float field\(float u, float v, float t\)\{ return )(.+?)(; \})",
            r"\g<1>(99.0 + \g<2>)\g<3>", prog.source, count=1)
        r = RasterRenderer()
        with self.assertRaises(FrameError) as ctx:
            r.render_field(prog, 64, 64, t=0.0)
        self.assertIn("does not match the verified expr_ast", str(ctx.exception))

    def test_verified_program_renders(self):
        """The untampered program passes verification and produces pixels."""
        prog = _gyroid_world().layers[0].render_program
        png = RasterRenderer().render_field(prog, 32, 32, t=0.0)
        self.assertTrue(png.startswith(b"\x89PNG"))


def _corrupt_first_const(node: dict) -> bool:
    if node.get("op") == "const":
        node["arg"] = node["arg"] + 99.0
        return True
    for child in node.get("args", []):
        if _corrupt_first_const(child):
            return True
    return False


if __name__ == "__main__":
    unittest.main()
