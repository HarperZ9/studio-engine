"""Demo CLI: run a simulation, write world.json + the SVG preview + the render program.

    python -m studio_engine [seed] [generator]
    python -m studio_engine --render-frames [seed] [generator]

With ``--render-frames`` the headless RasterRenderer turns the emitted program into actual PNG
frames the user can SEE (a strip across the loop for animatable fields), plus a frames.json
receipt binding each frame's sha256 to the program's expr_sha256.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from .engine import run


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    do_frames = False
    if "--render-frames" in args:
        do_frames = True
        args.remove("--render-frames")
    seed = int(args[0]) if args else 7
    generator = args[1] if len(args) > 1 else "phyllotaxis"

    out = Path("studio-out")
    out.mkdir(exist_ok=True)

    world = None
    frames: list[dict] = []
    for kind, obj in run(seed=seed, generator=generator, render_frames=do_frames):
        if kind == "frame":
            frames.append(obj)
        elif kind == "world":
            world = obj
    assert world is not None

    (out / f"world-{seed}.json").write_text(json.dumps(world.to_json(), indent=2), encoding="utf-8")
    layer = world.layers[0]
    if layer.preview:
        (out / f"artifact-{seed}.svg").write_text(layer.preview.content, encoding="utf-8")
    rp = layer.render_program
    (out / f"program-{seed}.txt").write_text(
        rp.source or json.dumps(rp.recipe, indent=2), encoding="utf-8")

    if do_frames:
        _write_frames(out, seed, generator, frames)

    t = world.trajectory
    print(f"world {world.id} | '{world.title}'")
    print(f"  steps={len(t.steps)} converged={t.converged} final_score={world.receipt.final_score}")
    print(f"  render={rp.target} expr_sha={rp.expr_sha256}")
    if world.timeline:
        print(f"  timeline period={world.timeline.period} "
              f"continuity={world.timeline.continuity.tag}")
    print(f"  palette={world.palette}")
    print(f"  wrote studio-out/world-{seed}.json (+ svg preview + render program)")
    if do_frames:
        print(f"  rendered {len(frames)} PNG frame(s) -> studio-out/frames-{seed}/ (+ frames.json)")
    return 0


def _write_frames(out: Path, seed: int, generator: str, frames: list[dict]) -> None:
    """Materialize the streamed frames as real PNG files + a re-checkable receipt."""
    fdir = out / f"frames-{seed}"
    fdir.mkdir(exist_ok=True)
    manifest = []
    for fr in frames:
        name = f"{generator}-{seed}-f{fr['frame']:03d}.png"
        (fdir / name).write_bytes(base64.b64decode(fr["png_base64"]))
        manifest.append({"file": name, "t": fr["t"], "sha256": fr["sha256"],
                         "delivery_receipt": fr["delivery_receipt"]})
    (fdir / "frames.json").write_text(
        json.dumps({"seed": seed, "generator": generator, "frames": manifest}, indent=2),
        encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
