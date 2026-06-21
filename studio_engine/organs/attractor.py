"""De Jong strange-attractor generator. Stdlib only.

Generator organ, in the same shape as geometry.py / fields.py: iterate the de Jong
map deterministically into a point cloud, then render it as a scaled+centered dot field.
The orbit's shape is a property of the chosen (a, b, c, d) parameters, not authored by
the renderer -- the caller normalizes the raw [-2, 2] coordinates.
"""
from __future__ import annotations

import math

PARAMS0 = {"a": 1.7, "b": 1.7, "c": 0.6, "d": 1.2}
BOUNDS = {"a": (-2.5, 2.5), "b": (-2.5, 2.5), "c": (-2.5, 2.5), "d": (-2.5, 2.5)}

_TRANSIENT = 20  # discard the first ~20 iterations while the orbit settles


def points(params: dict, n: int = 3000) -> list[tuple[float, float, int]]:
    """Iterate the de Jong map for `n` steps, returning (x, y, i) per kept step.

    x, y = sin(a*y) - cos(b*x), sin(c*x) - cos(d*y), from (0.1, 0.1). The first
    ~20 steps are skipped as transient; `i` is the kept-step index from 0.
    Coordinates land roughly in [-2, 2] -- the caller normalizes.
    """
    a, b, c, d = params["a"], params["b"], params["c"], params["d"]
    x, y = 0.1, 0.1
    out: list[tuple[float, float, int]] = []
    i = 0
    for step in range(n):
        x, y = math.sin(a * y) - math.cos(b * x), math.sin(c * x) - math.cos(d * y)
        if step < _TRANSIENT:
            continue
        out.append((x, y, i))
        i += 1
    return out


def svg(params: dict, palette: list[str], size: int = 720, n: int = 3000,
        dot: float = 1.4, bg: str = "#0e1116") -> str:
    """Render the de Jong orbit as small dots, auto-fit and centered to the canvas.

    Points are scaled by the tighter of the two axis fits (preserving aspect) and
    centered, leaving a small margin. Dot color is chosen from palette by kept-step
    index i, so the orbit grades across the palette over time.
    """
    pts = points(params, n)
    if not pts:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
                f'viewBox="0 0 {size} {size}">'
                f'<rect width="{size}" height="{size}" fill="{bg}"/></svg>')

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max(max_x - min_x, 1e-9)
    span_y = max(max_y - min_y, 1e-9)

    margin = size * 0.06
    avail = size - 2 * margin
    scale = min(avail / span_x, avail / span_y)
    # center the scaled bounding box within the canvas
    off_x = (size - span_x * scale) / 2.0 - min_x * scale
    off_y = (size - span_y * scale) / 2.0 - min_y * scale

    n_pal = max(1, len(pts))
    body = []
    for (x, y, i) in pts:
        col = (palette[int((i / n_pal) * len(palette)) % len(palette)]
               if palette else "#e8e8f0")
        cx = off_x + x * scale
        cy = off_y + y * scale
        body.append(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{dot:.2f}" fill="{col}"/>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{bg}"/>' + "".join(body) + "</svg>")
