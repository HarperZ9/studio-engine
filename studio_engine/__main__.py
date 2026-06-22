"""Demo CLI: run a simulation, write world.json + the SVG preview + the render program.

    python -m studio_engine [seed] [generator]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .engine import simulate


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    seed = int(args[0]) if args else 7
    generator = args[1] if len(args) > 1 else "phyllotaxis"
    world = simulate(seed=seed, generator=generator)

    out = Path("studio-out")
    out.mkdir(exist_ok=True)
    (out / f"world-{seed}.json").write_text(json.dumps(world.to_json(), indent=2), encoding="utf-8")
    layer = world.layers[0]
    if layer.preview:
        (out / f"artifact-{seed}.svg").write_text(layer.preview.content, encoding="utf-8")
    rp = layer.render_program
    (out / f"program-{seed}.txt").write_text(
        rp.source or json.dumps(rp.recipe, indent=2), encoding="utf-8")

    t = world.trajectory
    print(f"world {world.id} | '{world.title}'")
    print(f"  steps={len(t.steps)} converged={t.converged} final_score={world.receipt.final_score}")
    print(f"  render={rp.target} expr_sha={rp.expr_sha256}")
    if world.timeline:
        print(f"  timeline period={world.timeline.period} "
              f"continuity={world.timeline.continuity.tag}")
    print(f"  palette={world.palette}")
    print(f"  wrote studio-out/world-{seed}.json (+ svg preview + render program)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
