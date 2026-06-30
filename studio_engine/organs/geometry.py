"""Phyllotaxis geometry generator + the golden-angle fitness criterion. Stdlib only.

Generator + criterion organs. Matures the shipped contour/SVG + phyllotaxis work:
generate a spiral, then judge it against a criterion it did not author (the golden angle).
"""
from __future__ import annotations

import math

from ..strand import recipe as rc

GOLDEN_ANGLE = 137.50776405003785  # 360 * (1 - 1/phi); tightest non-overlapping packing


def phyllotaxis(n: int = 600, angle_deg: float = GOLDEN_ANGLE, scale: float = 9.0):
    """Vogel's model: point i at radius scale*sqrt(i), angle i*angle_deg."""
    a = math.radians(angle_deg)
    return [(scale * math.sqrt(i) * math.cos(i * a),
             scale * math.sqrt(i) * math.sin(i * a), i) for i in range(n)]


def recipe(params: dict, count: int = 700) -> dict:
    """Spiral recipe reproducing phyllotaxis(count, angle, scale) -- the point channel."""
    return rc.spiral(angle_deg=params["angle"], scale=params["scale"], count=count)


def to_svg(pts, palette: list[str], size: int = 720, dot: float = 4.0,
           bg: str = "#0e1116") -> str:
    cx = cy = size / 2
    n = max(1, len(pts))
    body = []
    for (x, y, i) in pts:
        col = palette[int((i / n) * len(palette)) % len(palette)] if palette else "#e8e8f0"
        rad = dot * (0.4 + 0.6 * (i / n))
        body.append(f'<circle cx="{cx + x:.2f}" cy="{cy + y:.2f}" r="{rad:.2f}" fill="{col}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{bg}"/>' + "".join(body) + "</svg>")


def golden_angle_deviation(angle_deg: float) -> float:
    """Fitness in 0..1: how close the spiral's divergence angle is to the golden angle.

    The criterion the generator did NOT author -- packing quality is a property of nature,
    not of the chosen angle. Circular distance, graded within 15 degrees.
    """
    d = abs(((angle_deg - GOLDEN_ANGLE + 180) % 360) - 180)
    return max(0.0, 1.0 - d / 15.0)
