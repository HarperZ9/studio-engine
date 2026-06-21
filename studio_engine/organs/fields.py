"""Implicit-field generators (gyroid, quasicrystal) + their fitness criteria. Stdlib only.

Generator + criterion organs, in the same shape as geometry.py: sample an implicit
field deterministically into an SVG, then judge the chosen parameters against a property
the generator did NOT author (clean tiling for the gyroid, 5-fold order for the
quasicrystal).
"""
from __future__ import annotations

import math

DEFAULT_PALETTE = ['#2dd4bf', '#7a5cff', '#fbbf24', '#ff7a5c']


def _palette_index(value: float, lo: float, hi: float, n: int) -> int:
    """Map a field value in [lo, hi] onto a palette index in [0, n-1]."""
    if n <= 1 or hi <= lo:
        return 0
    t = (value - lo) / (hi - lo)
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return min(n - 1, int(t * n))


def gyroid_field_svg(size: int = 720, freq: float = 6.0,
                     palette: list[str] | None = None, samples: int = 120,
                     bg: str = "#0e1116") -> str:
    """Sample the gyroid implicit field over a grid, one colored <rect> per cell.

    Field: sin(x)cos(y) + sin(y)cos(z) + sin(z)cos(x), evaluated at fixed z over a
    samples x samples grid scaled by freq. Cell color is chosen from palette by the
    field value (range -3..3).
    """
    pal = palette if palette else DEFAULT_PALETTE
    n = max(1, samples)
    cell = size / n
    z = 0.0
    cz, sz = math.cos(z), math.sin(z)
    body = []
    for gy in range(n):
        y = (gy / n) * freq * 2.0 * math.pi
        cy, sy = math.cos(y), math.sin(y)
        for gx in range(n):
            x = (gx / n) * freq * 2.0 * math.pi
            v = math.sin(x) * cy + sy * cz + sz * math.cos(x)
            col = pal[_palette_index(v, -3.0, 3.0, len(pal))]
            body.append(f'<rect x="{gx * cell:.2f}" y="{gy * cell:.2f}" '
                        f'width="{cell:.2f}" height="{cell:.2f}" fill="{col}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{bg}"/>' + "".join(body) + "</svg>")


def quasicrystal_svg(size: int = 720, waves: int = 5,
                     palette: list[str] | None = None, samples: int = 140,
                     bg: str = "#0e1116") -> str:
    """Sum `waves` plane waves at evenly spaced angles into an interference field.

    Each cell's value is the sum over k of cos(angle_k . position), angles at
    2*pi*k/waves. Cell color is chosen from palette by the interference value
    (range -waves..waves). The classic quasicrystal pattern.
    """
    pal = palette if palette else DEFAULT_PALETTE
    n = max(1, samples)
    w = max(1, waves)
    cell = size / n
    freq = 2.0 * math.pi * 6.0
    angles = [(2.0 * math.pi * k / w) for k in range(w)]
    dirs = [(math.cos(a), math.sin(a)) for a in angles]
    body = []
    for gy in range(n):
        py = gy / n
        for gx in range(n):
            px = gx / n
            v = 0.0
            for (dx, dy) in dirs:
                v += math.cos(freq * (dx * px + dy * py))
            col = pal[_palette_index(v, -float(w), float(w), len(pal))]
            body.append(f'<rect x="{gx * cell:.2f}" y="{gy * cell:.2f}" '
                        f'width="{cell:.2f}" height="{cell:.2f}" fill="{col}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{bg}"/>' + "".join(body) + "</svg>")


def gyroid_symmetry(freq: float) -> float:
    """Fitness in 0..1: rewards integer-ish freq (the field tiles cleanly).

    Cleanliness of the tiling is a property the generator did not author -- it falls
    out of the field's 2*pi periodicity, not the chosen freq.
    """
    return 1.0 - min(0.5, abs(freq - round(freq))) / 0.5


def quasicrystal_order(waves: int) -> float:
    """Fitness in 0..1: rewards 5-fold aperiodic order, peaking at waves == 5.

    Five plane waves give the canonical aperiodic (Penrose-like) interference; the
    aperiodicity is a property of that count, not authored by the generator.
    """
    return max(0.0, 1.0 - abs(waves - 5) * 0.2)
