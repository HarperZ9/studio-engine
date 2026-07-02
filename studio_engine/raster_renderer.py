"""The live renderer: turn an emitted RenderProgram into pixels the user can SEE. Stdlib only.

Where organs/program.py stops at emitting the render as DATA (a GLSL fragment or a point recipe)
for some other host to draw, this closes the loop headlessly: it consumes the EXACT SAME witnessed
RenderProgram and produces a deterministic PNG frame -- so the merit artifact (the picture) and the
accountability artifact (a re-checkable frame hash tied to expr_sha256) are one thing.

Honest by construction. Before a single pixel, `render_field` reparses the shipped GLSL `field()`
body back to a strand Expr, re-hashes it, and refuses (FrameError) if that hash no longer matches
the program's expr_sha256. So a tampered shader -- or a tampered receipt -- is caught, not rendered.
The Python sampling mirrors the shader's own math: `field(u,v,t)` over the same u,v in [-1,1] grid,
normalized by value_range, mapped through the SAME piecewise-linear palette ramp the GLSL emits.
"""
from __future__ import annotations

import base64
import hashlib
import re

from .model import RenderProgram
from .organs.raster import write_png, _parse_hex
from .strand import expr as ex
from .strand import glsl
from .strand import recipe as rc

# Matches the field() line organs/program.fragment_source emits verbatim.
_FIELD_RE = re.compile(r"float field\(float u, float v, float t\)\{ return (.+?); \}")


class FrameError(ValueError):
    """A render was refused because the program failed verification (tamper) or was malformed."""


class RasterRenderer:
    """Headless software rasterizer over the witnessed RenderProgram AST.

    Pure and deterministic: identical (program, size, t) -> byte-identical PNG. No wall clock,
    no randomness, no external process. `render_field` handles glsl-fragment programs; `render_points`
    handles point-recipe programs.
    """

    def field_expr(self, program: RenderProgram) -> ex.Expr:
        """Recover the verified strand Expr and check it against the receipt BEFORE any pixel.

        Primary binding: reconstruct the EXACT tree from the shipped `expr_ast` and re-hash it; it
        must equal `program.expr_sha256`. Because expr_ast preserves n-ary associativity, this
        round-trips byte-for-byte -- so a mutated AST, or a tampered claimed hash, is caught.

        Secondary cross-check (when the GLSL `field()` body is present): the emitted shader must
        evaluate identically to the recovered expr on a fixed sample grid, proving the pixels the
        shader would draw ARE the witnessed math -- not just that the AST is self-consistent.

        Raises FrameError on any mismatch; the renderer never draws an unverified program.
        """
        if program.target != "glsl-fragment":
            raise FrameError(f"render_field needs a glsl-fragment program, got {program.target!r}")
        if not program.expr_ast:
            raise FrameError("program carries no expr_ast to verify (cannot render honestly)")
        try:
            e = ex.from_dict(program.expr_ast)
        except (ValueError, TypeError, KeyError) as exc:
            raise FrameError(f"expr_ast did not deserialize: {exc}") from exc
        got = ex.sha(e)
        if got != program.expr_sha256:
            raise FrameError(
                f"expr_sha256 mismatch: shipped expr_ast hashes to {got!r} "
                f"but program claims {program.expr_sha256!r} (tampered program or receipt)")
        self._cross_check_source(program, e)
        return e

    @staticmethod
    def _cross_check_source(program: RenderProgram, e: ex.Expr) -> None:
        """If a GLSL field() body is shipped, confirm it evaluates to the verified expr on a grid."""
        m = _FIELD_RE.search(program.source or "")
        if not m:
            return
        try:
            shader_e = glsl.parse_glsl(m.group(1))
        except ValueError as exc:
            raise FrameError(f"shipped field() body did not parse: {exc}") from exc
        for (u, v, t) in ((-0.6, 0.3, 0.0), (0.2, -0.5, 0.4), (0.8, 0.8, 0.9)):
            env = {"u": u, "v": v, "t": t}
            if abs(ex.eval_expr(shader_e, env) - ex.eval_expr(e, env)) > 1e-6:
                raise FrameError(
                    "shipped GLSL field() does not match the verified expr_ast "
                    "(tampered shader source)")

    def render_field(self, program: RenderProgram, width: int, height: int,
                     t: float = 0.0) -> bytes:
        """Render a verified glsl-fragment program to a `width`x`height` RGB PNG at time `t`.

        Samples the recovered expr over u,v in [-1,1] (pixel centers, matching the shader's
        gl_FragCoord mapping), normalizes each sample by value_range, and maps it through the same
        piecewise-linear palette ramp the emitted GLSL uses. Returns raw PNG bytes (hash them for a
        re-checkable frame receipt).
        """
        e = self.field_expr(program)
        w = max(1, int(width))
        h = max(1, int(height))
        palette = _program_palette(program)
        ramp = [_parse_hex(c) for c in palette] or [(232, 232, 240)]
        lo, hi = _value_range(program)
        span = (hi - lo) or 1e-6

        fb = bytearray(w * h * 3)
        o = 0
        for py in range(h):
            # gl_FragCoord.xy / u_resolution * 2 - 1, sampled at pixel centers.
            v = ((py + 0.5) / h) * 2.0 - 1.0
            env = {"v": v, "t": t}
            for px in range(w):
                u = ((px + 0.5) / w) * 2.0 - 1.0
                env["u"] = u
                val = ex.eval_expr(e, env)
                n = (val - lo) / span
                r, g, b = _ramp(ramp, n)
                fb[o] = r
                fb[o + 1] = g
                fb[o + 2] = b
                o += 3
        return write_png(w, h, bytes(fb))

    def render_points(self, program: RenderProgram, width: int, height: int,
                      palette: list[str], bg: tuple[int, int, int] = (14, 17, 22)) -> bytes:
        """Render a point-recipe program to a `width`x`height` RGB PNG.

        Replays the verified recipe (spiral | iterated | parametric) via strand.recipe.eval_recipe --
        the exact points the engine witnessed -- fits them to the canvas, and rasterizes each as a
        filled disc colored by index across the palette. Deterministic.
        """
        if program.target != "point-recipe":
            raise FrameError(f"render_points needs a point-recipe program, got {program.target!r}")
        w = max(1, int(width))
        h = max(1, int(height))
        try:
            pts = rc.eval_recipe(program.recipe)
        except (KeyError, ValueError) as exc:
            raise FrameError(f"recipe did not evaluate: {exc}") from exc

        br, bgc, bb = bg
        fb = bytearray(w * h * 3)
        for off in range(0, len(fb), 3):
            fb[off] = br
            fb[off + 1] = bgc
            fb[off + 2] = bb
        if not pts:
            return write_png(w, h, bytes(fb))

        # Fit the point extent into the canvas with a small margin, preserving aspect.
        maxr = max((max(abs(x), abs(y)) for x, y, _ in pts), default=1.0) or 1.0
        scale = (min(w, h) / 2.0) * 0.92 / maxr
        cx, cy = w / 2.0, h / 2.0
        radius = max(1, min(w, h) // 200)
        r2 = radius * radius
        n = len(pts)
        np_ = max(1, len(palette))

        for (x, y, i) in pts:
            col = palette[int((i / n) * np_) % np_] if palette else "#e8e8f0"
            pr, pg, pb = _parse_hex(col)
            ipx = int(round(cx + x * scale))
            ipy = int(round(cy + y * scale))
            for dy in range(-radius, radius + 1):
                yy = ipy + dy
                if yy < 0 or yy >= h:
                    continue
                row = yy * w * 3
                dy2 = dy * dy
                for dx in range(-radius, radius + 1):
                    if dx * dx + dy2 > r2:
                        continue
                    xx = ipx + dx
                    if xx < 0 or xx >= w:
                        continue
                    off = row + xx * 3
                    fb[off] = pr
                    fb[off + 1] = pg
                    fb[off + 2] = pb
        return write_png(w, h, bytes(fb))


def render_frames(program: RenderProgram, palette: list[str], period: float,
                  n_frames: int = 8, size: int = 256) -> list[dict]:
    """Render a deterministic strip of frames from a render program -- the eye's delivery.

    For an animatable glsl-fragment the strip sweeps t over [0, period); otherwise it is a single
    static frame. Point-recipe programs render one frame (recipes are not time-parameterized here).
    Each entry carries the frame's t, its full sha256, and a delivery_receipt binding the frame to
    the program's expr_sha256 -- so anyone can re-render and confirm the hash. Returns [] for an
    unrenderable program rather than fabricating a frame.
    """
    r = RasterRenderer()
    out: list[dict] = []
    if program.target == "glsl-fragment":
        animatable = bool(program.domain.get("animatable")) and period > 0
        ts = [period * k / n_frames for k in range(n_frames)] if animatable else [0.0]
        for k, t in enumerate(ts):
            png = r.render_field(program, size, size, t)
            out.append(_frame_entry(program, k, round(t, 6), png))
    elif program.target == "point-recipe":
        png = r.render_points(program, size, size, palette)
        out.append(_frame_entry(program, 0, 0.0, png))
    return out


def _frame_entry(program: RenderProgram, k: int, t: float, png: bytes) -> dict:
    full = hashlib.sha256(png).hexdigest()
    return {
        "frame": k,
        "t": t,
        "png_base64": base64.b64encode(png).decode("ascii"),
        "sha256": full[:16],
        "delivery_receipt": {
            "expr_sha256": program.expr_sha256,
            "frame_sha256": full,
            "rendered_from": program.generator,
            "target": program.target,
        },
    }


def _program_palette(program: RenderProgram) -> list[str]:
    """The palette the emitted program carries (u_palette uniform value)."""
    up = (program.uniforms or {}).get("u_palette", {})
    val = up.get("value") if isinstance(up, dict) else None
    return list(val) if val else []


def _value_range(program: RenderProgram) -> tuple[float, float]:
    if program.value_range and len(program.value_range) == 2:
        lo, hi = float(program.value_range[0]), float(program.value_range[1])
    else:
        lo, hi = 0.0, 1.0
    if hi <= lo:
        hi = lo + 1e-6
    return lo, hi


def _ramp(stops: list[tuple[int, int, int]], x: float) -> tuple[int, int, int]:
    """Piecewise-linear palette lookup mirroring the emitted GLSL `ramp()` (clamped, n-1 segments)."""
    if not stops:
        return (232, 232, 240)
    if len(stops) == 1:
        return stops[0]
    x = 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
    s = x * (len(stops) - 1)
    idx = int(s)
    if idx >= len(stops) - 1:
        return stops[-1]
    f = s - idx
    a = stops[idx]
    b = stops[idx + 1]
    return (round(a[0] + (b[0] - a[0]) * f),
            round(a[1] + (b[1] - a[1]) * f),
            round(a[2] + (b[2] - a[2]) * f))
