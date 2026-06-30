"""Concentric interference rings field -- a strand-native generator. Stdlib + strand only.

Adding a generator to the substrate is now just writing one expr: sin(sqrt(u^2+v^2)*freq + t).
The radius term makes circular contours; t pulses them outward (animatable).
"""
from __future__ import annotations

import math

from ..strand import expr as ex
from . import fields as fld

PARAMS0 = {"freq": 5.0}
BOUNDS = {"freq": (2.0, 12.0)}
ANIMATABLE = True


def expr(params: dict) -> ex.Expr:
    f = float(params["freq"])
    u, v, t = ex.var("u"), ex.var("v"), ex.var("t")
    r = ex.sqrt(ex.add(ex.mul(u, u), ex.mul(v, v)))
    return ex.sin(ex.add(ex.mul(r, f), t))


def value(params: dict, u: float, v: float) -> float:
    return ex.eval_expr(expr(params), {"u": u, "v": v, "t": 0.0})


def period(params: dict) -> float:
    return 2.0 * math.pi


def svg(params: dict, palette: list, size: int = 720, samples: int = 64) -> str:
    return fld._field_svg(expr(params), palette, size=size, samples=samples, t=0.0)
