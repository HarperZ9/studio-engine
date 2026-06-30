"""Implicit-field generators (gyroid, quasicrystal) defined as strand exprs + their criteria.

Each field is ONE strand expr f(u,v,t) -- the single source the engine samples for features, the
GLSL backend renders, and the preview SVG draws. `t` is the animatable axis (the gyroid's z-slice,
the quasicrystal's phase). This canonicalizes the field: the preview now samples the *verified*
expr (domain u,v in [-1,1]), not a separate inlined formula -- killing the old preview/feature drift.
Stdlib + strand only.
"""
from __future__ import annotations

import math

from ..strand import expr as ex

DEFAULT_PALETTE = ['#2dd4bf', '#7a5cff', '#fbbf24', '#ff7a5c']
BG = "#0e1116"


def _palette_index(value: float, lo: float, hi: float, n: int) -> int:
    """Map a field value in [lo, hi] onto a palette index in [0, n-1]."""
    if n <= 1 or hi <= lo:
        return 0
    t = (value - lo) / (hi - lo)
    t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
    return min(n - 1, int(t * n))


# --- gyroid: sin(u f)cos(v f) + sin(v f)cos(t f) + sin(t f)cos(u f); t = z-slice (animatable) ---
GYROID_ANIMATABLE = True


def gyroid_expr(params: dict) -> ex.Expr:
    f = float(params["freq"])
    u, v, t = ex.var("u"), ex.var("v"), ex.var("t")
    uf, vf, tf = ex.mul(u, f), ex.mul(v, f), ex.mul(t, f)
    return ex.add(
        ex.mul(ex.sin(uf), ex.cos(vf)),
        ex.mul(ex.sin(vf), ex.cos(tf)),
        ex.mul(ex.sin(tf), ex.cos(uf)),
    )


def gyroid_t0(params: dict) -> float:
    return float(params.get("z", 0.0))


def gyroid_value(params: dict, u: float, v: float) -> float:
    return ex.eval_expr(gyroid_expr(params), {"u": u, "v": v, "t": gyroid_t0(params)})


def gyroid_period(params: dict) -> float:
    return 2.0 * math.pi / max(1e-6, float(params["freq"]))


# --- quasicrystal: sum_k cos(cos(2pi k/w) u s + sin(2pi k/w) v s + t); t = phase (animatable) ---
QUASICRYSTAL_ANIMATABLE = True


def quasicrystal_expr(params: dict) -> ex.Expr:
    w = max(1, int(round(params["waves"])))
    s = float(params["scale"])
    u, v, t = ex.var("u"), ex.var("v"), ex.var("t")
    terms = []
    for k in range(w):
        ang = 2.0 * math.pi * k / w
        inner = ex.add(ex.mul(u, math.cos(ang) * s), ex.mul(v, math.sin(ang) * s), t)
        terms.append(ex.cos(inner))
    return ex.add(*terms)


def quasicrystal_t0(params: dict) -> float:
    return 0.0


def quasicrystal_value(params: dict, u: float, v: float) -> float:
    return ex.eval_expr(quasicrystal_expr(params), {"u": u, "v": v, "t": 0.0})


def quasicrystal_period(params: dict) -> float:
    return 2.0 * math.pi


# --- shared preview sampler: any field expr -> colored-rect SVG (a fallback for the live GLSL) ---
def _field_svg(e: ex.Expr, palette, size: int = 720, samples: int = 64, t: float = 0.0,
               value_range=None, bg: str = BG) -> str:
    pal = palette if palette else DEFAULT_PALETTE
    n = max(1, samples)
    cell = size / n
    vals = []
    lo, hi = float("inf"), float("-inf")
    for gy in range(n):
        v = 2.0 * ((gy + 0.5) / n) - 1.0
        for gx in range(n):
            u = 2.0 * ((gx + 0.5) / n) - 1.0
            val = ex.eval_expr(e, {"u": u, "v": v, "t": t})
            vals.append(val)
            lo, hi = min(lo, val), max(hi, val)
    if value_range:
        lo, hi = value_range
    body = []
    idx = 0
    for gy in range(n):
        for gx in range(n):
            col = pal[_palette_index(vals[idx], lo, hi, len(pal))]
            idx += 1
            body.append(f'<rect x="{gx * cell:.2f}" y="{gy * cell:.2f}" '
                        f'width="{cell:.2f}" height="{cell:.2f}" fill="{col}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 {size} {size}">'
            f'<rect width="{size}" height="{size}" fill="{bg}"/>' + "".join(body) + "</svg>")


def gyroid_field_svg(size: int = 720, freq: float = 6.0, z: float = 0.0,
                     palette=None, samples: int = 120, bg: str = BG) -> str:
    """Preview of the gyroid field at z-slice `z`, sampled from the verified expr."""
    return _field_svg(gyroid_expr({"freq": freq}), palette, size=size, samples=samples, t=z, bg=bg)


def quasicrystal_svg(size: int = 720, waves: int = 5, scale: float = 8.0,
                     palette=None, samples: int = 140, bg: str = BG) -> str:
    """Preview of the quasicrystal interference field, sampled from the verified expr."""
    return _field_svg(quasicrystal_expr({"waves": waves, "scale": scale}),
                      palette, size=size, samples=samples, t=0.0, bg=bg)


def gyroid_symmetry(freq: float) -> float:
    """Fitness in 0..1: rewards integer-ish freq (the field tiles cleanly)."""
    return 1.0 - min(0.5, abs(freq - round(freq))) / 0.5


def quasicrystal_order(waves: int) -> float:
    """Fitness in 0..1: rewards 5-fold aperiodic order, peaking at waves == 5."""
    return max(0.0, 1.0 - abs(waves - 5) * 0.2)
