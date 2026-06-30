"""studio-engine -- a native, zero-dependency creative-verification simulation engine.

Composes generative + verification organs into one witnessed loop
(perceive -> generate -> critique -> refine -> witness) and emits a `World` -- layered
self-describing render programs (GLSL for the eye, a synth graph for the ear), a witnessed
motion timeline, and the reasoning trajectory -- that the "experience chamber" frontend renders.
Built on the `strand` expression substrate: one closed-form algebra every backend derives from.
Stdlib only.
"""
from __future__ import annotations

from .engine import simulate, simulate_scene, run, library, generators
from .model import (Scene, World, Artifact, Receipt, Trajectory, OrganInfo,
                    RenderProgram, AudioProgram, Layer, Timeline, SCHEMA_VERSION)
# note: `studio_engine.compose` is the compositor MODULE (compose.compose(...)); we deliberately
# do not re-export the function at package level, to avoid shadowing that submodule.

__all__ = ["simulate", "simulate_scene", "run", "library", "generators",
           "Scene", "World", "Artifact", "Receipt", "Trajectory", "OrganInfo",
           "RenderProgram", "AudioProgram", "Layer", "Timeline", "SCHEMA_VERSION"]
__version__ = "0.2.0"
