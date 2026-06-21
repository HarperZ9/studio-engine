"""OKLab / OKLCh perceptual palette generation. Stdlib only.

Generator organ. Matures the shipped color/OKLab organ into a reusable palette unit:
perceptually-even ramps the chamber can theme from.
"""
from __future__ import annotations

import math


def _linear_to_srgb(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def oklch_to_hex(L: float, C: float, h_deg: float) -> str:
    """OKLCh (lightness, chroma, hue°) -> sRGB hex. Ottosson's OKLab inverse."""
    h = math.radians(h_deg)
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    R, G, B = (round(_linear_to_srgb(x) * 255) for x in (r, g, bl))
    return "#%02x%02x%02x" % (max(0, min(255, R)), max(0, min(255, G)), max(0, min(255, B)))


SCHEMES = {"analogous": 44.0, "triadic": 120.0, "complementary": 180.0, "wide": 300.0}


def generate_palette(seed: int, n: int = 6, base_hue: float | None = None,
                     L: float = 0.72, C: float = 0.13, scheme: str = "analogous") -> list[str]:
    """Deterministic perceptual palette from a seed: an even lightness ramp across a hue spread."""
    rng = (seed * 2654435761) & 0xFFFFFFFF
    if base_hue is None:
        base_hue = float(rng % 360)
    spread = SCHEMES.get(scheme, 44.0)
    out: list[str] = []
    for i in range(n):
        t = i / max(1, n - 1)
        h = (base_hue + (t - 0.5) * spread) % 360
        Li = max(0.18, min(0.94, L + (t - 0.5) * 0.24))
        out.append(oklch_to_hex(Li, C, h))
    return out
