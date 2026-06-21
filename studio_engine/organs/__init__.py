"""Organs — the resource library the engine composes.

generators: geometry (phyllotaxis), fields (gyroid/quasicrystal), attractor (de Jong),
harmonograph, flowfield, metaballs, turbulence. color: palette (OKLab). render: raster (PNG).
sonifier: sonify. Each is stdlib-only and returns the contract types in `studio_engine.model`.
"""
from __future__ import annotations

from . import (geometry, palette, fields, raster, sonify,
               attractor, harmonograph, flowfield, metaballs, turbulence)

__all__ = ["geometry", "palette", "fields", "raster", "sonify",
           "attractor", "harmonograph", "flowfield", "metaballs", "turbulence"]
