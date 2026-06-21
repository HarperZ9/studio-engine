"""The simulation engine: perceive -> generate -> critique -> refine -> witness.

The reconcile/refine spine applied to generation, across multiple generator organs. It
produces a Scene: layered visual artifacts (SVG + native PNG), live audio params, the
refine trajectory (replayable reasoning), and a re-checkable receipt. The frontend
"experience chamber" renders this stream; the engine is its honest, deterministic source.
"""
from __future__ import annotations

import json
from typing import Any

from .model import (Artifact, Verdict, Step, Trajectory, Receipt, Scene, SceneLayer, OrganInfo, _sha)
from .organs import geometry as geo, palette as pal, fields as fld, raster as ras, sonify as snd


# Each generator: an initial (rough-draft) parameter, a criterion it did NOT author,
# a refine step toward that criterion, and a render to SVG. `points` enables PNG raster.
def _gens() -> dict[str, dict[str, Any]]:
    return {
        "phyllotaxis": {
            "param": "angle_deg", "criterion": "criterion.golden_angle",
            "initial": lambda rng: geo.GOLDEN_ANGLE + (((rng % 2000) / 1000.0) - 1.0) * 9.0,
            "fit": lambda p: geo.golden_angle_deviation(p),
            "refine": lambda p: p + (geo.GOLDEN_ANGLE - p) * 0.6,
            "render": lambda p, pl: geo.to_svg(geo.phyllotaxis(600, p), pl),
            "points": lambda p: geo.phyllotaxis(600, p),
        },
        "gyroid": {
            "param": "freq", "criterion": "criterion.gyroid_symmetry",
            "initial": lambda rng: round(4.0 + (rng % 500) / 100.0, 3),
            "fit": lambda p: fld.gyroid_symmetry(p),
            "refine": lambda p: p + (round(p) - p) * 0.6,
            "render": lambda p, pl: fld.gyroid_field_svg(freq=p, palette=pl, samples=64),
            "points": None,
        },
        "quasicrystal": {
            "param": "waves", "criterion": "criterion.quasicrystal_order",
            "initial": lambda rng: float(3 + (rng % 5)),
            "fit": lambda p: fld.quasicrystal_order(int(round(p))),
            "refine": lambda p: p + (5.0 - p) * 0.5,
            "render": lambda p, pl: fld.quasicrystal_svg(waves=int(round(p)), palette=pl, samples=72),
            "points": None,
        },
    }


def library() -> list[OrganInfo]:
    """The resource library the engine composes (the frontend lists these)."""
    return [
        OrganInfo("geometry.phyllotaxis", "Phyllotaxis", "generator",
                  "Vogel-model spiral; golden-angle packing.", {"angle_deg": "float"},
                  "coherence-membrane contour/SVG + phyllotaxis"),
        OrganInfo("fields.gyroid", "Gyroid field", "generator",
                  "2D slice of the gyroid implicit surface.", {"freq": "float"},
                  "sensory-transform-algebra Field plane"),
        OrganInfo("fields.quasicrystal", "Quasicrystal", "generator",
                  "Sum of plane waves; aperiodic interference.", {"waves": "int"},
                  "sensory-transform-algebra Field plane"),
        OrganInfo("palette.oklch", "OKLCh palette", "generator",
                  "Perceptually-even color ramp from a seed.", {"scheme": "str"},
                  "coherence-membrane color/OKLab"),
        OrganInfo("raster.png", "Native PNG render", "compositor",
                  "Zero-dep PNG raster of a point field (zlib only).", {"size": "int"},
                  "raw eye.raw_rendering (rasterization)"),
        OrganInfo("sonify.params", "Sonifier", "sonifier",
                  "Maps the refine trajectory + palette to live Web-Audio params (and WAV).",
                  {"duration": "float"}, "creativity-invention sensory algebra"),
        OrganInfo("criterion.golden_angle", "Golden-angle fitness", "criterion",
                  "Packing vs the golden angle — a criterion the generator didn't author.", {}, ""),
        OrganInfo("criterion.gyroid_symmetry", "Gyroid symmetry", "criterion",
                  "Clean tiling (integer frequency).", {}, ""),
        OrganInfo("criterion.quasicrystal_order", "Quasicrystal order", "criterion",
                  "5-fold aperiodic order.", {}, ""),
    ]


def generators() -> list[str]:
    return list(_gens().keys())


def simulate(seed: int = 0, generator: str = "phyllotaxis", max_steps: int = 8,
             target: float = 0.985, scheme: str = "analogous") -> Scene:
    """Run the loop from a rough draft to an accepted result, witnessing every step."""
    gens = _gens()
    if generator not in gens:
        raise ValueError(f"unknown generator {generator!r}; have {list(gens)}")
    spec = gens[generator]
    rng = (seed * 2654435761 + 12345) & 0xFFFFFFFF
    palette = pal.generate_palette(seed, n=6, scheme=scheme)

    param = spec["initial"](rng)          # perceive: the rough draft
    steps: list[Step] = []
    best: tuple[float, float] | None = None
    for k in range(max_steps):
        fit = spec["fit"](param)          # critique vs the unauthored criterion
        tag = "verified" if fit >= target else ("unverifiable" if fit > 0.4 else "refuted")
        v = Verdict(spec["criterion"], tag, round(fit, 4),
                    f"{spec['param']}={param:.4f}; deviation-graded")
        steps.append(Step(k, "critique", {spec["param"]: round(param, 4)}, [v], round(fit, 4),
                          f"fit={fit:.4f} -> {tag}"))
        if best is None or fit > best[0]:
            best = (fit, param)
        if fit >= target:
            break
        param = spec["refine"](param)     # refine toward the criterion

    fit, param = best  # type: ignore[misc]
    converged = fit >= target
    scores = [s.score for s in steps] or [fit]

    # live-render params (z=-1): the chamber renders this generator natively (WebGL/canvas)
    # from here — light, always present. SVG/PNG below are previews/fallbacks.
    params_art = Artifact("data", json.dumps({
        "generator": generator, spec["param"]: round(param, 4), "palette": palette,
        "criterion": spec["criterion"], "scores": scores, "converged": converged,
    }), label="render-params").finalize()
    layers = [SceneLayer(f"{generator}.params", "Live params", params_art, role="params", z=-1)]
    artifact_shas = [params_art.sha256]

    # accepted visual artifacts: an SVG preview always; a native PNG when the generator has points
    svg = Artifact("svg", spec["render"](param, palette).strip(), 720, 720,
                   label=f"{generator}.svg").finalize()
    layers.append(SceneLayer(f"{generator}", "Geometry", svg, role="geometry", z=0))
    artifact_shas.append(svg.sha256)
    if spec["points"]:
        png = ras.render_phyllotaxis_png(spec["points"](param), palette, size=720)
        layers.append(SceneLayer("raster.png", "Raster", png, role="raster", z=1))
        artifact_shas.append(png.sha256)

    audio = snd.audio_params(seed, palette, scores)   # live Web-Audio params; WAV via API

    steps.append(Step(len(steps), "witness", {spec["param"]: round(param, 4)}, score=round(fit, 4),
                      note="accepted" if converged else "best-effort (unconverged)"))
    traj = Trajectory(steps, accepted_index=len(steps) - 1, converged=converged)

    sid = _sha(f"{seed}:{generator}:{param:.6f}:{svg.sha256}")
    organ_ids = [generator, "palette.oklch", spec["criterion"], "sonify.params"]
    if spec["points"]:
        organ_ids.append("raster.png")
    receipt = Receipt(sid, seed, organ_ids, artifact_shas, round(fit, 4))
    return Scene(id=sid, title=f"{generator.title()} #{seed}", layers=layers,
                 audio=audio, trajectory=traj, receipt=receipt, palette=palette)
