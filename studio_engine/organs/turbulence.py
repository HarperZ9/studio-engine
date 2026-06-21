"""Fractal turbulence (fBm of sinusoids) FIELD generator organ. Stdlib only.

A generator organ in the same shape as fields.py: sum several octaves of a
sinusoidal basis into a smooth fractal scalar field, then sample it deterministically
into an SVG. `value` is a pure function of (params, u, v) with u, v in [-1, 1]; `svg`
samples it on a grid and colors each cell from the palette.
"""
from __future__ import annotations

import math

PARAMS0 = {"freq": 3.0, "octaves": 4.0, "gain": 0.55}
BOUNDS = {"freq": (1.5, 6.0), "octaves": (2.0, 6.0), "gain": (0.35, 0.7)}

DEFAULT_PALETTE = ['#2dd4bf', '#7a5cff', '#fbbf24', '#ff7a5c']
BG = "#0e1116"


def value(params: dict, u: float, v: float) -> float:
    """Fractal turbulence (fBm of sinusoids) at (u, v), u, v in [-1, 1]. PURE.

    Sums `octaves` octaves of a sinusoidal basis; each octave doubles the frequency
    and scales the amplitude by `gain`**o. The accumulator is normalized by the sum of
    amplitudes, yielding a smooth fractal field in roughly [-1, 1].
    """
    freq0 = params["freq"]
    octaves = int(round(params["octaves"]))
    gain = params["gain"]
    acc = 0.0
    amp_sum = 0.0
    for o in range(octaves):
        freq = freq0 * (2 ** o)
        amp = gain ** o
        acc += amp * math.sin(freq * u + math.sin(freq * v)) * math.cos(freq * v)
        amp_sum += amp
    if amp_sum == 0.0:
        return 0.0
    return acc / amp_sum


def _palette_index(val: float, lo: float, hi: float, n: int) -> int:
    """Map a field value in [lo, hi] onto a palette index in [0, n-1]."""
    if n <= 1 or hi <= lo:
        return 0
    t = (val - lo) / (hi - lo)
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return min(n - 1, int(t * n))


def svg(params: dict, palette: list[str], size: int = 720, samples: int = 64) -> str:
    """Sample `value` over a samples x samples grid in u, v in [-1, 1] into an SVG.

    One colored <rect> per cell; cell color is chosen from `palette` by the field
    value (range -1..1) over a dark background. Square viewBox.
    """
    pal = palette if palette else DEFAULT_PALETTE
    n = max(1, samples)
    cell = size / n
    body = []
    for gy in range(n):
        v = -1.0 + 2.0 * (gy + 0.5) / n
        for gx in range(n):
            u = -1.0 + 2.0 * (gx + 0.5) / n
            val = value(params, u, v)
            col = pal[_palette_index(val, -1.0, 1.0, len(pal))]
            body.append(f'<rect x="{gx * cell:.2f}" y="{gy * cell:.2f}" '
                        f'width="{cell:.2f}" height="{cell:.2f}" fill="{col}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{BG}"/>' + "".join(body) + "</svg>")
