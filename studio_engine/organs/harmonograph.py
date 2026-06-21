"""Harmonograph (damped Lissajous) generator organ. Stdlib only.

Generator organ in the same shape as geometry.py / fields.py: trace a damped
two-pendulum harmonograph deterministically into points, then render an auto-fit,
palette-along-the-curve polyline over a dark background. Pure math.sin/exp -- no
external dependencies.

A harmonograph is two damped sinusoids per axis:
    x = sin(f1*t + p1)*exp(-d1*t) + sin(f2*t + p2)*exp(-d2*t)
    y = sin(f3*t + p3)*exp(-d1*t) + sin(f4*t + p4)*exp(-d2*t)
The decay envelopes spiral the figure inward; near-integer frequency ratios give
the classic closed Lissajous-like knots. Phases p1..p4 are derived deterministically
from the frequencies plus a single "phase" offset, so the figure is reproducible
from the parameter dict alone.
"""
from __future__ import annotations

import math

T = 60.0  # total trace time; the decay envelope tames the tail

PARAMS0 = {"f1": 2.0, "f2": 3.0, "f3": 3.0, "f4": 2.0,
           "d1": 0.02, "d2": 0.0285, "phase": 0.5}

BOUNDS = {"f1": (1.0, 5.0), "f2": (1.0, 5.0), "f3": (1.0, 5.0), "f4": (1.0, 5.0),
          "d1": (0.005, 0.06), "d2": (0.005, 0.06), "phase": (0.0, 3.14)}

DEFAULT_PALETTE = ['#2dd4bf', '#7a5cff', '#fbbf24', '#ff7a5c']


def _phases(f1: float, f2: float, f3: float, f4: float, phase: float):
    """Derive four phases deterministically from the frequencies + a single offset.

    Reproducible from the parameter dict alone -- no randomness. Each phase is the
    base offset stepped by quarter-turn increments, nudged by its own frequency so
    the two axes do not stay locked in phase.
    """
    half_pi = math.pi / 2.0
    return (phase,
            phase + half_pi + 0.1 * f2,
            phase + math.pi + 0.1 * f3,
            phase + 3.0 * half_pi + 0.1 * f4)


def points(params: dict, n: int = 4000) -> list[tuple[float, float, int]]:
    """Trace the damped harmonograph: n samples of (x, y, i) over t in [0, T].

    x = sin(f1*t + p1)*exp(-d1*t) + sin(f2*t + p2)*exp(-d2*t)
    y = sin(f3*t + p3)*exp(-d1*t) + sin(f4*t + p4)*exp(-d2*t)

    Frequencies f1..f4 (~1-5), damping d1,d2 (~0.005-0.06), phases p1..p4 derived
    from the frequencies and the "phase" offset. Coordinates land in roughly
    [-2, 2] (sum of two unit sinusoids). i is the sample index in [0, n-1].
    """
    f1 = float(params.get("f1", PARAMS0["f1"]))
    f2 = float(params.get("f2", PARAMS0["f2"]))
    f3 = float(params.get("f3", PARAMS0["f3"]))
    f4 = float(params.get("f4", PARAMS0["f4"]))
    d1 = float(params.get("d1", PARAMS0["d1"]))
    d2 = float(params.get("d2", PARAMS0["d2"]))
    phase = float(params.get("phase", PARAMS0["phase"]))
    p1, p2, p3, p4 = _phases(f1, f2, f3, f4, phase)

    count = max(2, n)
    out: list[tuple[float, float, int]] = []
    for i in range(count):
        t = T * i / (count - 1)
        e1 = math.exp(-d1 * t)
        e2 = math.exp(-d2 * t)
        x = math.sin(f1 * t + p1) * e1 + math.sin(f2 * t + p2) * e2
        y = math.sin(f3 * t + p3) * e1 + math.sin(f4 * t + p4) * e2
        out.append((x, y, i))
    return out


def svg(params: dict, palette: list[str], size: int = 720) -> str:
    """Render the harmonograph as an auto-fit, centered, multi-color polyline.

    The curve is split into one <polyline> segment per palette color so the hue
    sweeps along the trace from start to finish. Points are scaled to fit the
    square with a uniform margin and centered. Dark #0e1116 background.
    """
    bg = "#0e1116"
    pal = palette if palette else DEFAULT_PALETTE
    pts = points(params, 4000)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    spanx = maxx - minx or 1.0
    spany = maxy - miny or 1.0

    margin = size * 0.06
    avail = size - 2.0 * margin
    scale = avail / max(spanx, spany)
    # center the (possibly non-square) bounding box inside the square viewBox
    offx = margin + (avail - spanx * scale) / 2.0
    offy = margin + (avail - spany * scale) / 2.0

    screen = [((px - minx) * scale + offx, (py - miny) * scale + offy)
              for (px, py, _i) in pts]

    nseg = max(1, len(pal))
    total = len(screen)
    body: list[str] = []
    for s in range(nseg):
        lo = (s * total) // nseg
        hi = ((s + 1) * total) // nseg
        # overlap by one point so consecutive segments connect with no gap
        seg = screen[lo:hi + 1] if hi < total else screen[lo:hi]
        if len(seg) < 2:
            continue
        col = pal[s % len(pal)]
        coords = " ".join(f"{x:.2f},{y:.2f}" for (x, y) in seg)
        body.append(f'<polyline points="{coords}" fill="none" stroke="{col}" '
                    f'stroke-width="1.4" stroke-linecap="round" '
                    f'stroke-linejoin="round"/>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{bg}"/>'
            + "".join(body) + "</svg>")
