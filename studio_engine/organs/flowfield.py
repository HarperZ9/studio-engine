"""Flow / curl-noise field generator organ. Stdlib only (math).

A smooth domain-warped flow field: a pure scalar potential `value(params, u, v)`
sampled over a square grid into an SVG, one colored <rect> per cell. The warp term
folds each axis through a sinusoid of the other, giving the swirling, curl-like
contours of a flow field without any noise tables or dependencies.

Same shape as the other generator organs (fields.py): a deterministic field, a
`_palette_index` mapping the value range onto the palette, a square viewBox, and a
dark #0e1116 background.
"""
from __future__ import annotations

import math

PARAMS0 = {"scale": 4.5, "warp": 1.2}
BOUNDS = {"scale": (2.0, 9.0), "warp": (0.0, 3.0)}

BG = "#0e1116"
DEFAULT_PALETTE = ['#2dd4bf', '#7a5cff', '#fbbf24', '#ff7a5c']


def value(params: dict, u: float, v: float) -> float:
    """Pure flow potential at (u, v), u,v in [-1, 1]; smooth, in roughly [-1, 1].

    Each axis is warped by a sinusoid of the other (the domain warp), then the two
    warped waves are multiplied. The product of two cosines/sines stays bounded in
    [-1, 1] and varies smoothly, reading as the swirling contours of a flow field.
    """
    s = params["scale"]
    w = params["warp"]
    a = math.sin(s * u + w * math.sin(s * v))
    b = math.cos(s * v + w * math.cos(s * u))
    return a * b


def _palette_index(val: float, lo: float, hi: float, n: int) -> int:
    """Map a field value in [lo, hi] onto a palette index in [0, n-1]."""
    if n <= 1 or hi <= lo:
        return 0
    t = (val - lo) / (hi - lo)
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return min(n - 1, int(t * n))


def svg(params: dict, palette: list[str], size: int = 720, samples: int = 64) -> str:
    """Sample `value` on a samples x samples grid over u,v in [-1, 1].

    Each cell becomes a colored <rect>, its color chosen from `palette` by the field
    value (range -1..1). Square viewBox over a dark background.
    """
    pal = palette if palette else DEFAULT_PALETTE
    n = max(1, samples)
    cell = size / n
    body = []
    for gy in range(n):
        # cell center -> u,v in [-1, 1]
        v = 2.0 * ((gy + 0.5) / n) - 1.0
        for gx in range(n):
            u = 2.0 * ((gx + 0.5) / n) - 1.0
            val = value(params, u, v)
            col = pal[_palette_index(val, -1.0, 1.0, len(pal))]
            body.append(f'<rect x="{gx * cell:.2f}" y="{gy * cell:.2f}" '
                        f'width="{cell:.2f}" height="{cell:.2f}" fill="{col}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{BG}"/>' + "".join(body) + "</svg>")
