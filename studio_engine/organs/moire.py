"""Moire field -- two rotated sinusoidal gratings multiplied. Strand-native. Stdlib + strand only.

expr: sin(f*(u) + t) * sin(f*(u*cos(a) + v*sin(a)) + t). The angle between the gratings sets the
moire beat; t slides the fringes (animatable). Another one-expr generator on the substrate.
"""
from __future__ import annotations

import math

from ..strand import expr as ex
from . import fields as fld

PARAMS0 = {"freq": 8.0, "angle": 0.4}
BOUNDS = {"freq": (3.0, 16.0), "angle": (0.1, 1.4)}
ANIMATABLE = True


def expr(params: dict) -> ex.Expr:
    f = float(params["freq"])
    a = float(params["angle"])
    u, v, t = ex.var("u"), ex.var("v"), ex.var("t")

    def grating(theta: float) -> ex.Expr:
        proj = ex.add(ex.mul(u, math.cos(theta)), ex.mul(v, math.sin(theta)))
        return ex.sin(ex.add(ex.mul(proj, f), t))

    return ex.mul(grating(0.0), grating(a))


def value(params: dict, u: float, v: float) -> float:
    return ex.eval_expr(expr(params), {"u": u, "v": v, "t": 0.0})


def period(params: dict) -> float:
    return 2.0 * math.pi


def svg(params: dict, palette: list, size: int = 720, samples: int = 64) -> str:
    return fld._field_svg(expr(params), palette, size=size, samples=samples, t=0.0)
