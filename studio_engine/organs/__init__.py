"""Organs -- the resource library the engine composes.

generators: geometry (phyllotaxis), fields (gyroid/quasicrystal), attractor (de Jong),
harmonograph, flowfield, metaballs, turbulence, rings, moire -- each defines itself as a strand
expr/recipe. color: palette (OKLab). render: raster (standalone PNG). sonifier: sonify.
program: assembles RenderProgram/AudioProgram from strand. Stdlib + strand only; returns the
contract types in `studio_engine.model`.
"""
from __future__ import annotations

from . import (geometry, palette, fields, raster, sonify, program,
               attractor, harmonograph, flowfield, metaballs, turbulence, rings, moire)

__all__ = ["geometry", "palette", "fields", "raster", "sonify", "program",
           "attractor", "harmonograph", "flowfield", "metaballs", "turbulence", "rings", "moire"]
