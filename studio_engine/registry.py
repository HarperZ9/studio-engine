"""The generator registry: one declarative (organ, criterion, render, expr/recipe) binding each.

A pure data table — each entry wires a generator's parameter seed/bounds, its criteria axes, its
preview render, and (for fields) its strand expr / (for points) its recipe, plus animation metadata.
Extracted from engine.py to keep that module focused on the loop. Data, not logic.
"""
from __future__ import annotations

from .organs import (geometry as geo, fields as fld, attractor as att, harmonograph as harm,
                     flowfield as flow, metaballs as mb, turbulence as turb, rings, moire)
from . import criteria as crit


def _init(p0: dict, bounds: dict, rng: int) -> dict:
    """Seed a rough-draft parameter vector: each param perturbed around its base, in bounds."""
    out: dict[str, float] = {}
    for i, (k, (lo, hi)) in enumerate(bounds.items()):
        base = float(p0.get(k, (lo + hi) / 2))
        frac = (((rng >> (i * 5)) % 1000) / 1000.0 - 0.5)  # -0.5..0.5
        out[k] = max(lo, min(hi, base + frac * (hi - lo) * 0.6))
    return out


_GENS = {
    "phyllotaxis": {
        "params0": lambda rng: {"angle": crit.GOLDEN_ANGLE + (((rng % 2000) / 1000.0) - 1.0) * 9.0,
                                "scale": 7.0 + (rng >> 8) % 7, "dot": 3.0 + ((rng >> 16) % 30) / 10.0},
        "bounds": {"angle": (110.0, 165.0), "scale": (5.0, 16.0), "dot": (2.5, 6.5)},
        "axes": ["golden_angle", "balance", "coverage", "complexity"],
        "render": lambda p, pl: geo.to_svg(geo.phyllotaxis(700, p["angle"], p["scale"]), pl, dot=p["dot"]),
        "points": lambda p: geo.phyllotaxis(700, p["angle"], p["scale"]),
        "field": None, "recipe": geo.recipe, "animatable": False, "period": lambda p: 0.0,
    },
    "gyroid": {
        "params0": lambda rng: {"freq": round(4.0 + (rng % 500) / 100.0, 3),
                                "z": round(0.2 + (rng >> 9) % 60 / 100.0, 3)},
        "bounds": {"freq": (3.0, 10.0), "z": (0.05, 0.95)},
        "axes": ["clean_freq", "contrast", "complexity"],
        "render": lambda p, pl: fld.gyroid_field_svg(freq=p["freq"], z=p["z"], palette=pl, samples=64),
        "points": None,
        "field": lambda p, u, v: fld.gyroid_value(p, u, v),
        "expr": fld.gyroid_expr, "t0": fld.gyroid_t0,
        "animatable": fld.GYROID_ANIMATABLE, "period": fld.gyroid_period,
    },
    "quasicrystal": {
        "params0": lambda rng: {"waves": float(3 + (rng % 5)), "scale": 6.0 + (rng >> 10) % 8},
        "bounds": {"waves": (3.0, 9.0), "scale": (4.0, 14.0)},
        "axes": ["fivefold", "contrast", "complexity"],
        "render": lambda p, pl: fld.quasicrystal_svg(waves=int(round(p["waves"])), scale=p["scale"], palette=pl, samples=72),
        "points": None,
        "field": lambda p, u, v: fld.quasicrystal_value(p, u, v),
        "expr": fld.quasicrystal_expr, "t0": fld.quasicrystal_t0,
        "animatable": fld.QUASICRYSTAL_ANIMATABLE, "period": fld.quasicrystal_period,
    },
    "attractor": {
        "params0": lambda rng: _init(att.PARAMS0, att.BOUNDS, rng), "bounds": att.BOUNDS,
        "axes": ["balance", "coverage", "complexity"],
        "render": lambda p, pl: att.svg(p, pl), "points": lambda p: att.points(p), "field": None,
        "recipe": att.recipe, "animatable": False, "period": lambda p: 0.0,
    },
    "harmonograph": {
        "params0": lambda rng: _init(harm.PARAMS0, harm.BOUNDS, rng), "bounds": harm.BOUNDS,
        "axes": ["balance", "coverage", "complexity"],
        "render": lambda p, pl: harm.svg(p, pl), "points": lambda p: harm.points(p), "field": None,
        "recipe": harm.recipe, "animatable": False, "period": lambda p: 0.0,
    },
    "flowfield": {
        "params0": lambda rng: _init(flow.PARAMS0, flow.BOUNDS, rng), "bounds": flow.BOUNDS,
        "axes": ["contrast", "complexity"],
        "render": lambda p, pl: flow.svg(p, pl, samples=64), "points": None,
        "field": lambda p, u, v: flow.value(p, u, v),
        "expr": flow.expr, "t0": lambda p: 0.0,
        "animatable": flow.ANIMATABLE, "period": flow.period,
    },
    "metaballs": {
        "params0": lambda rng: _init(mb.PARAMS0, mb.BOUNDS, rng), "bounds": mb.BOUNDS,
        "axes": ["contrast", "complexity"],
        "render": lambda p, pl: mb.svg(p, pl, samples=64), "points": None,
        "field": lambda p, u, v: mb.value(p, u, v),
        "expr": mb.expr, "t0": lambda p: 0.0,
        "animatable": mb.ANIMATABLE, "period": mb.period,
    },
    "turbulence": {
        "params0": lambda rng: _init(turb.PARAMS0, turb.BOUNDS, rng), "bounds": turb.BOUNDS,
        "axes": ["contrast", "complexity"],
        "render": lambda p, pl: turb.svg(p, pl, samples=64), "points": None,
        "field": lambda p, u, v: turb.value(p, u, v),
        "expr": turb.expr, "t0": lambda p: 0.0,
        "animatable": turb.ANIMATABLE, "period": turb.period,
    },
    "rings": {
        "params0": lambda rng: _init(rings.PARAMS0, rings.BOUNDS, rng), "bounds": rings.BOUNDS,
        "axes": ["contrast", "complexity"],
        "render": lambda p, pl: rings.svg(p, pl, samples=64), "points": None,
        "field": lambda p, u, v: rings.value(p, u, v),
        "expr": rings.expr, "t0": lambda p: 0.0,
        "animatable": rings.ANIMATABLE, "period": rings.period,
    },
    "moire": {
        "params0": lambda rng: _init(moire.PARAMS0, moire.BOUNDS, rng), "bounds": moire.BOUNDS,
        "axes": ["contrast", "complexity"],
        "render": lambda p, pl: moire.svg(p, pl, samples=64), "points": None,
        "field": lambda p, u, v: moire.value(p, u, v),
        "expr": moire.expr, "t0": lambda p: 0.0,
        "animatable": moire.ANIMATABLE, "period": moire.period,
    },
}


def gens() -> dict:
    """The generator registry (a stable table; callers read, never mutate)."""
    return _GENS
