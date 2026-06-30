"""Metaballs / distance-field generator. Stdlib only.

Generator organ, in the same shape as fields.py / attractor.py: deterministically
place a handful of charged "balls", then sample their summed potential field over a
grid into an SVG. The blobby threshold-ish shape is a property of where the seeds land
and how steeply the potential falls off -- the caller normalizes the raw potential
(>=0, unbounded) per grid before coloring.
"""
from __future__ import annotations

import math

from ..strand import expr as ex

PARAMS0 = {"count": 5.0, "spread": 0.32, "falloff": 0.06}
BOUNDS = {"count": (3.0, 9.0), "spread": (0.15, 0.5), "falloff": (0.02, 0.15)}

# 32-bit linear-congruential constants (Numerical Recipes), used for our own cheap PRNG
# so seed placement is deterministic without importing `random`.
_LCG_A = 1664525
_LCG_C = 1013904223
_LCG_M = 0x100000000  # 2**32


def _palette_index(value: float, lo: float, hi: float, n: int) -> int:
    """Map a field value in [lo, hi] onto a palette index in [0, n-1]."""
    if n <= 1 or hi <= lo:
        return 0
    t = (value - lo) / (hi - lo)
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return min(n - 1, int(t * n))


def _seeds(params: dict) -> list[tuple[float, float, float]]:
    """Deterministically place `count` balls as (cx, cy, r) tuples.

    A self-rolled 32-bit LCG seeded by int(count*1000 + spread*100) drives placement,
    so the same params always yield the same seeds (no `random` module). Centers land
    in [-0.7, 0.7]; each radius is `spread` modulated by +/-25% from the PRNG.
    """
    count = int(round(params["count"]))
    spread = float(params["spread"])
    state = (int(count * 1000 + spread * 100)) % _LCG_M

    def _next() -> float:
        # advance the LCG and return a float in [0, 1)
        nonlocal state
        state = (_LCG_A * state + _LCG_C) % _LCG_M
        return state / _LCG_M

    out: list[tuple[float, float, float]] = []
    for _ in range(max(0, count)):
        cx = (_next() * 2.0 - 1.0) * 0.7
        cy = (_next() * 2.0 - 1.0) * 0.7
        r = spread * (0.75 + 0.5 * _next())
        out.append((cx, cy, r))
    return out


# Not animatable in v1: animating baked centers is more than a phase term (spec §6).
ANIMATABLE = False


def expr(params: dict) -> ex.Expr:
    """Summed metaball potential as a strand expr, balls baked as constants at build time.

    sum_balls (r*r / ((u-cx)^2 + (v-cy)^2 + 1e-3)) * falloff. The +1e-3 matches the strand
    div guard exactly, so eval(expr) == the original value() to the bit.
    """
    falloff = float(params["falloff"])
    u, v = ex.var("u"), ex.var("v")
    terms = []
    for (cx, cy, r) in _seeds(params):
        du, dv = ex.sub(u, cx), ex.sub(v, cy)
        denom = ex.add(ex.mul(du, du), ex.mul(dv, dv), 1e-3)
        terms.append(ex.div(r * r, denom))
    total = ex.add(*terms) if terms else ex.const(0.0)
    return ex.mul(total, falloff)


def value(params: dict, u: float, v: float) -> float:
    """Summed metaball potential at (u, v) -- the expr sampled (t unused). >= 0, may exceed 1."""
    return ex.eval_expr(expr(params), {"u": u, "v": v, "t": 0.0})


def period(params: dict) -> float:
    return 0.0


def svg(params: dict, palette: list[str], size: int = 720, samples: int = 64,
        bg: str = "#0e1116") -> str:
    """Sample `value` over a samples x samples grid on [-1, 1]^2, one colored <rect> per cell.

    The grid is normalized to [0, 1] across its own min/max, then each cell is colored
    from palette by its normalized potential -- a threshold-ish blob look. Dark bg.
    """
    n = max(1, samples)
    cell = size / n

    # first pass: compute the raw potential grid and its range for normalization
    grid: list[list[float]] = []
    lo = float("inf")
    hi = float("-inf")
    for gy in range(n):
        v = (gy / (n - 1)) * 2.0 - 1.0 if n > 1 else 0.0
        row: list[float] = []
        for gx in range(n):
            u = (gx / (n - 1)) * 2.0 - 1.0 if n > 1 else 0.0
            p = value(params, u, v)
            row.append(p)
            if p < lo:
                lo = p
            if p > hi:
                hi = p
        grid.append(row)

    pal = palette if palette else ["#e8e8f0"]
    body = []
    for gy in range(n):
        for gx in range(n):
            col = pal[_palette_index(grid[gy][gx], lo, hi, len(pal))]
            body.append(f'<rect x="{gx * cell:.2f}" y="{gy * cell:.2f}" '
                        f'width="{cell:.2f}" height="{cell:.2f}" fill="{col}"/>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{bg}"/>' + "".join(body) + "</svg>")
