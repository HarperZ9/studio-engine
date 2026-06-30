"""Point-cloud recipes for the strand substrate: the ear/eye's point-channel.

A recipe is a JSON-portable description the frontend runs to draw a point cloud, and that the
engine evaluates (via the same parser) to reproduce the exact points it verified. Coordinate maps
are carried as emitted-GLSL strings (parsed back with strand.glsl) so the recipe stays pure data
yet re-evaluable. Three modes cover every shipped point generator:

  spiral      -- i -> (scale*sqrt(i)*cos(i*a), ...)            (phyllotaxis)
  iterated    -- (x,y) -> (update_x, update_y), drop transient (de Jong attractor)
  parametric  -- t in [0,t_max] -> (x(t), y(t))               (harmonograph)
"""
from __future__ import annotations

import math

from .expr import Expr, eval_expr
from .glsl import emit_glsl, parse_glsl


def spiral(angle_deg: float, scale: float, count: int, color_by: str = "index") -> dict:
    return {"mode": "spiral", "angle_deg": float(angle_deg), "scale": float(scale),
            "count": int(count), "color_by": color_by}


def iterated(update_x: Expr, update_y: Expr, init, transient: int, count: int,
             color_by: str = "index") -> dict:
    return {"mode": "iterated", "update_x": emit_glsl(update_x), "update_y": emit_glsl(update_y),
            "init": [float(init[0]), float(init[1])], "transient": int(transient),
            "count": int(count), "color_by": color_by}


def parametric(x_expr: Expr, y_expr: Expr, t_max: float, count: int,
               color_by: str = "index") -> dict:
    return {"mode": "parametric", "x": emit_glsl(x_expr), "y": emit_glsl(y_expr),
            "t_max": float(t_max), "count": int(count), "color_by": color_by}


def eval_recipe(r: dict) -> list:
    """Reproduce (x, y, i) points from a recipe -- the engine-side render of the point channel."""
    mode = r["mode"]
    if mode == "spiral":
        return _eval_spiral(r)
    if mode == "iterated":
        return _eval_iterated(r)
    if mode == "parametric":
        return _eval_parametric(r)
    raise ValueError(f"unknown recipe mode {mode!r}")


def _eval_spiral(r: dict) -> list:
    a = math.radians(r["angle_deg"])
    s = r["scale"]
    out = []
    for i in range(int(r["count"])):
        rad = s * math.sqrt(i)
        out.append((rad * math.cos(i * a), rad * math.sin(i * a), i))
    return out


def _eval_iterated(r: dict) -> list:
    ux, uy = parse_glsl(r["update_x"]), parse_glsl(r["update_y"])
    x, y = r["init"]
    transient = int(r["transient"])
    out = []
    idx = 0
    for step in range(int(r["count"])):
        nx = eval_expr(ux, {"x": x, "y": y})
        ny = eval_expr(uy, {"x": x, "y": y})
        x, y = nx, ny
        if step < transient:
            continue
        out.append((x, y, idx))
        idx += 1
    return out


def _eval_parametric(r: dict) -> list:
    xe, ye = parse_glsl(r["x"]), parse_glsl(r["y"])
    n = max(2, int(r["count"]))
    t_max = r["t_max"]
    out = []
    for i in range(n):
        t = t_max * i / (n - 1)
        out.append((eval_expr(xe, {"t": t}), eval_expr(ye, {"t": t}), i))
    return out
