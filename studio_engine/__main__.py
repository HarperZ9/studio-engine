"""Demo CLI: run a simulation, write scene.json + the SVG artifact, print the trajectory.

    python -m studio_engine [seed]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .engine import simulate


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    seed = int(args[0]) if args else 7
    scene = simulate(seed=seed)
    out = Path("studio-out")
    out.mkdir(exist_ok=True)
    (out / f"scene-{seed}.json").write_text(json.dumps(scene.to_json(), indent=2), encoding="utf-8")
    (out / f"artifact-{seed}.svg").write_text(scene.layers[0].artifact.content, encoding="utf-8")

    t = scene.trajectory
    print(f"scene {scene.id} | '{scene.title}'")
    print(f"  steps={len(t.steps)} converged={t.converged} final_score={scene.receipt.final_score}")
    for s in t.steps:
        v = (s.verdicts[0].tag if s.verdicts else "-")
        print(f"   [{s.index}] {s.phase:<8} angle={s.params.get('angle','-')} score={s.score} {v}")
    print(f"  palette={scene.palette}")
    print(f"  wrote studio-out/scene-{seed}.json + artifact-{seed}.svg "
          f"(svg sha {scene.layers[0].artifact.sha256})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
