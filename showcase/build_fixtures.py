"""Regenerate the showcase's baked World fixtures — provenance for the frame.

Each fixture is a real, witnessed `World` carrying a genuine coherence-membrane Certificate
emitted by the unified engine. Deterministic (corpus off) so the baked frame can be
re-derived and re-checked by anyone.

Run from the repo root with coherence-membrane on the path:

    PYTHONPATH="<repo>;<...>/coherence-membrane/src" python showcase/build_fixtures.py
"""
from __future__ import annotations

import json
from pathlib import Path

from studio_engine import engine

# (generator, seed) -> fixture file. Gyroid is the hero (glsl, animatable); the other two
# feed the "liquid" generator switch — one more glsl field + the iconic point spiral.
FIXTURES = {
    "gyroid": 7,
    "quasicrystal": 7,
    "phyllotaxis": 7,
}

OUT = Path(__file__).resolve().parent / "worlds"


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for generator, seed in FIXTURES.items():
        world = engine.simulate(seed, generator=generator, scheme="analogous", corpus_path=None)
        cert = world.certificate or {}
        path = OUT / f"{generator}.json"
        path.write_text(json.dumps(world.to_json(), indent=2), encoding="utf-8")
        print(f"{generator:14s} score={world.receipt.final_score:.4f}  "
              f"verdict={cert.get('verdict','?')}  -> {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
