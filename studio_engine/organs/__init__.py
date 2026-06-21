"""Organs — the resource library the engine composes.

generators (geometry, fields), color (palette), renderer (raster→PNG), sonifier (sonify).
Each is stdlib-only and returns the contract types in `studio_engine.model`.
"""
from __future__ import annotations

from . import geometry, palette, fields, raster, sonify

__all__ = ["geometry", "palette", "fields", "raster", "sonify"]
