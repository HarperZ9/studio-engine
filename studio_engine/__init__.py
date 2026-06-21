"""studio-engine — a native, zero-dependency creative-verification simulation engine.

Composes generative + verification organs into one witnessed loop
(perceive -> generate -> critique -> refine -> witness) and emits a `Scene` the
frontend "experience chamber" renders. Stdlib only.
"""
from __future__ import annotations

from .engine import simulate, run, library, generators
from .model import Scene, Artifact, Receipt, Trajectory, OrganInfo, SCHEMA_VERSION

__all__ = ["simulate", "run", "library", "generators", "Scene", "Artifact", "Receipt",
           "Trajectory", "OrganInfo", "SCHEMA_VERSION"]
__version__ = "0.1.0"
