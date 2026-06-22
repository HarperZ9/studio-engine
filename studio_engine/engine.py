"""The simulation engine: perceive -> generate -> critique(multi-axis) -> refine -> witness.

Advanced loop. Each candidate is judged on several criteria PLUS novelty, combined by
cohesion (harmonic mean — every axis must hold). The loop reflects on the weakest axis and
refines the parameter VECTOR toward it (bounded coordinate descent), converging only when
CORRECT on every axis, not merely good on average. Novelty is grounded against a persistent
corpus, so output is novel AND structured. Emits a Scene the chamber renders; deterministic
for (seed, generator, scheme).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from .model import (Artifact, Verdict, Step, Trajectory, Receipt, Scene, SceneLayer, OrganInfo, _sha)
from .organs import (geometry as geo, palette as pal, fields as fld, raster as ras, sonify as snd,
                     attractor as att, harmonograph as harm, flowfield as flow,
                     metaballs as mb, turbulence as turb)
from . import criteria as crit
from .corpus import Corpus

_CORPUS_PATH = Path(__file__).resolve().parent / "_corpus.json"
_G = 20  # feature grid resolution


def _init(p0: dict, bounds: dict, rng: int) -> dict:
    """Seed a rough-draft parameter vector: each param perturbed around its base, in bounds."""
    out: dict[str, float] = {}
    for i, (k, (lo, hi)) in enumerate(bounds.items()):
        base = float(p0.get(k, (lo + hi) / 2))
        frac = (((rng >> (i * 5)) % 1000) / 1000.0 - 0.5)  # -0.5..0.5
        out[k] = max(lo, min(hi, base + frac * (hi - lo) * 0.6))
    return out


def _gens() -> dict[str, dict[str, Any]]:
    return {
        "phyllotaxis": {
            "params0": lambda rng: {"angle": crit.GOLDEN_ANGLE + (((rng % 2000) / 1000.0) - 1.0) * 9.0,
                                    "scale": 7.0 + (rng >> 8) % 7, "dot": 3.0 + ((rng >> 16) % 30) / 10.0},
            "bounds": {"angle": (110.0, 165.0), "scale": (5.0, 16.0), "dot": (2.5, 6.5)},
            "axes": ["golden_angle", "balance", "coverage", "complexity"],
            "render": lambda p, pl: geo.to_svg(geo.phyllotaxis(700, p["angle"], p["scale"]), pl, dot=p["dot"]),
            "points": lambda p: geo.phyllotaxis(700, p["angle"], p["scale"]),
            "field": None, "recipe": geo.recipe, "animatable": False, "period": lambda p: 0.0,
        },
        "gyroid": {
            "params0": lambda rng: {"freq": round(4.0 + (rng % 500) / 100.0, 3),
                                    "z": round(0.2 + (rng >> 9) % 60 / 100.0, 3)},
            "bounds": {"freq": (3.0, 10.0), "z": (0.05, 0.95)},
            "axes": ["clean_freq", "contrast", "complexity"],
            "render": lambda p, pl: fld.gyroid_field_svg(freq=p["freq"], z=p["z"], palette=pl, samples=64),
            "points": None,
            "field": lambda p, u, v: fld.gyroid_value(p, u, v),
            "expr": fld.gyroid_expr, "t0": fld.gyroid_t0,
            "animatable": fld.GYROID_ANIMATABLE, "period": fld.gyroid_period,
        },
        "quasicrystal": {
            "params0": lambda rng: {"waves": float(3 + (rng % 5)), "scale": 6.0 + (rng >> 10) % 8},
            "bounds": {"waves": (3.0, 9.0), "scale": (4.0, 14.0)},
            "axes": ["fivefold", "contrast", "complexity"],
            "render": lambda p, pl: fld.quasicrystal_svg(waves=int(round(p["waves"])), scale=p["scale"], palette=pl, samples=72),
            "points": None,
            "field": lambda p, u, v: fld.quasicrystal_value(p, u, v),
            "expr": fld.quasicrystal_expr, "t0": fld.quasicrystal_t0,
            "animatable": fld.QUASICRYSTAL_ANIMATABLE, "period": fld.quasicrystal_period,
        },
        "attractor": {
            "params0": lambda rng: _init(att.PARAMS0, att.BOUNDS, rng), "bounds": att.BOUNDS,
            "axes": ["balance", "coverage", "complexity"],
            "render": lambda p, pl: att.svg(p, pl), "points": lambda p: att.points(p), "field": None,
            "recipe": att.recipe, "animatable": False, "period": lambda p: 0.0,
        },
        "harmonograph": {
            "params0": lambda rng: _init(harm.PARAMS0, harm.BOUNDS, rng), "bounds": harm.BOUNDS,
            "axes": ["balance", "coverage", "complexity"],
            "render": lambda p, pl: harm.svg(p, pl), "points": lambda p: harm.points(p), "field": None,
            "recipe": harm.recipe, "animatable": False, "period": lambda p: 0.0,
        },
        "flowfield": {
            "params0": lambda rng: _init(flow.PARAMS0, flow.BOUNDS, rng), "bounds": flow.BOUNDS,
            "axes": ["contrast", "complexity"],
            "render": lambda p, pl: flow.svg(p, pl, samples=64), "points": None,
            "field": lambda p, u, v: flow.value(p, u, v),
            "expr": flow.expr, "t0": lambda p: 0.0,
            "animatable": flow.ANIMATABLE, "period": flow.period,
        },
        "metaballs": {
            "params0": lambda rng: _init(mb.PARAMS0, mb.BOUNDS, rng), "bounds": mb.BOUNDS,
            "axes": ["contrast", "complexity"],
            "render": lambda p, pl: mb.svg(p, pl, samples=64), "points": None,
            "field": lambda p, u, v: mb.value(p, u, v),
            "expr": mb.expr, "t0": lambda p: 0.0,
            "animatable": mb.ANIMATABLE, "period": mb.period,
        },
        "turbulence": {
            "params0": lambda rng: _init(turb.PARAMS0, turb.BOUNDS, rng), "bounds": turb.BOUNDS,
            "axes": ["contrast", "complexity"],
            "render": lambda p, pl: turb.svg(p, pl, samples=64), "points": None,
            "field": lambda p, u, v: turb.value(p, u, v),
            "expr": turb.expr, "t0": lambda p: 0.0,
            "animatable": turb.ANIMATABLE, "period": turb.period,
        },
    }


def _hue(palette: list[str]) -> float:
    if not palette:
        return 0.5
    h = palette[len(palette) // 2].lstrip("#")
    r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return 0.0
    if mx == r:
        hh = ((g - b) / (mx - mn)) % 6
    elif mx == g:
        hh = (b - r) / (mx - mn) + 2
    else:
        hh = (r - g) / (mx - mn) + 4
    return (hh / 6.0) % 1.0


def _entropy(counts: list[float]) -> float:
    tot = sum(counts)
    if tot <= 0:
        return 0.0
    ps = [c / tot for c in counts if c > 0]
    if len(ps) <= 1:
        return 0.0
    h = -sum(p * math.log(p) for p in ps)
    return max(0.0, min(1.0, h / math.log(len(counts))))


def _features(spec: dict, params: dict, palette: list[str]) -> dict:
    hue = _hue(palette)
    if spec["points"]:
        pts = spec["points"](params)
        maxr = max((math.hypot(x, y) for x, y, _ in pts), default=1.0) or 1.0
        cells = [0.0] * (_G * _G)
        sx = sy = 0.0
        for x, y, _ in pts:
            nx, ny = x / maxr, y / maxr
            sx += nx
            sy += ny
            gx = min(_G - 1, max(0, int((nx + 1) / 2 * _G)))
            gy = min(_G - 1, max(0, int((ny + 1) / 2 * _G)))
            cells[gy * _G + gx] += 1
        n = len(pts) or 1
        coverage = sum(1 for c in cells if c > 0) / (_G * _G)
        centroid_offset = min(1.0, math.hypot(sx / n, sy / n))
        mean = n / (_G * _G)
        contrast = min(1.0, (math.sqrt(sum((c - mean) ** 2 for c in cells) / len(cells)) / (mean + 1e-9)) / 3.0)
        entropy = _entropy(cells)
    else:
        f = spec["field"]
        vals = [f(params, (i / (_G - 1)) * 2 - 1, (j / (_G - 1)) * 2 - 1)
                for j in range(_G) for i in range(_G)]
        vmin, vmax = min(vals), max(vals)
        rng = (vmax - vmin) or 1e-9
        norm = [(v - vmin) / rng for v in vals]
        contrast = min(1.0, (vmax - vmin) / 4.0)
        coverage = sum(1 for v in norm if v > 0.5) / len(norm)
        # asymmetry across the two axes -> centroid_offset (for the novelty vector)
        left = sum(norm[j * _G + i] for j in range(_G) for i in range(_G // 2))
        right = sum(norm[j * _G + i] for j in range(_G) for i in range(_G // 2, _G))
        top = sum(norm[j * _G + i] for j in range(_G // 2) for i in range(_G))
        bot = sum(norm[j * _G + i] for j in range(_G // 2, _G) for i in range(_G))
        tot = sum(norm) or 1e-9
        centroid_offset = min(1.0, (abs(left - right) + abs(top - bot)) / tot)
        hist = [0.0] * 10
        for v in norm:
            hist[min(9, int(v * 10))] += 1
        entropy = _entropy(hist)
    return {"coverage": coverage, "centroid_offset": centroid_offset,
            "contrast": contrast, "entropy": entropy, "hue": hue}


def _evaluate(spec: dict, params: dict, palette: list[str], corpus: Corpus):
    feats = _features(spec, params, palette)
    margins = {ax: crit.score(ax, feats, params) for ax in spec["axes"]}
    margins["novelty"] = corpus.novelty(feats)
    return feats, margins, crit.cohesion(list(margins.values()))


def _clamp(spec: dict, params: dict) -> dict:
    out = dict(params)
    for k, (lo, hi) in spec["bounds"].items():
        out[k] = max(lo, min(hi, out[k]))
    return out


def _refine(spec: dict, params: dict, palette: list[str], corpus: Corpus, frac: float):
    """Bounded coordinate descent: the single param move that best improves cohesion."""
    _, _, base = _evaluate(spec, params, palette, corpus)
    best, best_coh = params, base
    for k, (lo, hi) in spec["bounds"].items():
        delta = (hi - lo) * frac
        for d in (delta, -delta):
            trial = _clamp(spec, {**params, k: params[k] + d})
            _, _, coh = _evaluate(spec, trial, palette, corpus)
            if coh > best_coh + 1e-6:
                best, best_coh = trial, coh
    return best, best_coh > base + 1e-6


def library() -> list[OrganInfo]:
    return [
        OrganInfo("geometry.phyllotaxis", "Phyllotaxis", "generator",
                  "Vogel spiral; params angle/scale/dot.", {"angle": "float", "scale": "float", "dot": "float"},
                  "coherence-membrane contour/SVG"),
        OrganInfo("fields.gyroid", "Gyroid field", "generator", "Gyroid implicit slice.",
                  {"freq": "float", "z": "float"}, "sensory-transform-algebra Field"),
        OrganInfo("fields.quasicrystal", "Quasicrystal", "generator", "Plane-wave interference.",
                  {"waves": "int", "scale": "float"}, "sensory-transform-algebra Field"),
        OrganInfo("attractor.dejong", "de Jong attractor", "generator", "Strange-attractor point cloud.",
                  {"a": "float", "b": "float", "c": "float", "d": "float"}, "dynamical systems"),
        OrganInfo("harmonograph", "Harmonograph", "generator", "Damped-Lissajous curve.",
                  {"f1": "float", "f2": "float", "f3": "float", "f4": "float"}, "harmonic motion"),
        OrganInfo("flowfield", "Flow field", "generator", "Domain-warped curl flow.",
                  {"scale": "float", "warp": "float"}, "sensory-transform-algebra Field"),
        OrganInfo("metaballs", "Metaballs", "generator", "Distance-field potential.",
                  {"count": "int", "spread": "float", "falloff": "float"}, "implicit surfaces"),
        OrganInfo("turbulence", "Turbulence (fBm)", "generator", "Fractal sinusoidal turbulence.",
                  {"freq": "float", "octaves": "int", "gain": "float"}, "fractal noise"),
        OrganInfo("palette.oklch", "OKLCh palette", "generator", "Perceptual color ramp.",
                  {"scheme": "str"}, "coherence-membrane color/OKLab"),
        OrganInfo("raster.png", "Native PNG", "compositor", "Zero-dep PNG raster.", {"size": "int"}, "raw eye"),
        OrganInfo("sonify.params", "Sonifier", "sonifier", "Trajectory + palette -> Web-Audio params + WAV.",
                  {"duration": "float"}, "creativity sensory algebra"),
        OrganInfo("criteria.multi_axis", "Multi-axis cohesion", "criterion",
                  "Harmonic-mean of structural + aesthetic margins; converge only when correct on every axis.",
                  {}, "refine primitive"),
        OrganInfo("criteria.novelty", "Novelty vs corpus", "criterion",
                  "Distance from prior work in feature space; grounds creativity (novel AND structured).",
                  {}, "single-thread-reconcile binding #1"),
    ]


def generators() -> list[str]:
    return list(_gens().keys())


def run(seed: int = 0, generator: str = "phyllotaxis", max_steps: int = 16,
        target: float = 0.9, floor: float = 0.6, scheme: str = "analogous",
        corpus_path: str | Path | None = _CORPUS_PATH):
    """Generator form: yields ('step', Step) per iteration, then ('scene', Scene).
    Powers live streaming + interactive sessions; simulate() is the collected form."""
    gens = _gens()
    if generator not in gens:
        raise ValueError(f"unknown generator {generator!r}; have {list(gens)}")
    spec = gens[generator]
    rng = (seed * 2654435761 + 12345) & 0xFFFFFFFF
    palette = pal.generate_palette(seed, n=6, scheme=scheme)
    corpus = Corpus.load(corpus_path)

    params = _clamp(spec, spec["params0"](rng))
    steps: list[Step] = []
    best: tuple[float, dict, dict, dict] | None = None
    frac = 0.34
    for k in range(max_steps):
        feats, margins, coh = _evaluate(spec, params, palette, corpus)
        weakest = min(margins, key=lambda a: margins[a])
        steps.append(Step(
            k, "critique", {p: round(v, 4) for p, v in params.items()},
            [Verdict(ax, crit.tag(s, target, floor), round(s, 4), crit.kind(ax) if ax != "novelty" else "novelty")
             for ax, s in margins.items()],
            round(coh, 4), {ax: round(s, 4) for ax, s in margins.items()}, weakest,
            f"cohesion={coh:.4f}; weakest={weakest}={margins[weakest]:.3f}"))
        yield ("step", steps[-1])
        if best is None or coh > best[0]:
            best = (coh, dict(params), feats, margins)
        if coh >= target and all(s >= floor for s in margins.values()):
            break
        nxt, improved = _refine(spec, params, palette, corpus, frac)
        if not improved:
            frac *= 0.55
            if frac < 0.02:
                break
        params = nxt

    coh, params, feats, margins = best  # type: ignore[misc]
    converged = coh >= target and all(s >= floor for s in margins.values())
    scores = [s.score for s in steps] or [coh]

    params_art = Artifact("data", json.dumps({
        "generator": generator, "params": {p: round(v, 4) for p, v in params.items()},
        "palette": palette, "margins": {a: round(v, 4) for a, v in margins.items()},
        "cohesion": round(coh, 4), "scores": scores, "converged": converged,
    }), label="render-params").finalize()
    layers = [SceneLayer(f"{generator}.params", "Live params", params_art, role="params", z=-1)]
    artifact_shas = [params_art.sha256]

    svg = Artifact("svg", spec["render"](params, palette).strip(), 720, 720, label=f"{generator}.svg").finalize()
    layers.append(SceneLayer(generator, "Geometry", svg, role="geometry", z=0))
    artifact_shas.append(svg.sha256)
    if spec["points"]:
        png = ras.render_phyllotaxis_png(spec["points"](params), palette, size=720)
        layers.append(SceneLayer("raster.png", "Raster", png, role="raster", z=1))
        artifact_shas.append(png.sha256)

    audio = snd.audio_params(seed, palette, scores)
    steps.append(Step(len(steps), "witness", {p: round(v, 4) for p, v in params.items()},
                      score=round(coh, 4), margins={a: round(v, 4) for a, v in margins.items()},
                      note="accepted" if converged else "best-effort (unconverged)"))
    yield ("step", steps[-1])
    traj = Trajectory(steps, accepted_index=len(steps) - 1, converged=converged)

    corpus.add(feats)  # ground future novelty in what we just made
    sid = _sha(f"{seed}:{generator}:{json.dumps(params, sort_keys=True)}:{svg.sha256}")
    organ_ids = [generator, "palette.oklch", "criteria.multi_axis", "criteria.novelty", "sonify.params"]
    if spec["points"]:
        organ_ids.append("raster.png")
    receipt = Receipt(sid, seed, organ_ids, artifact_shas, round(coh, 4))
    yield ("scene", Scene(id=sid, title=f"{generator.title()} #{seed}", layers=layers,
                          audio=audio, trajectory=traj, receipt=receipt, palette=palette))


def simulate(seed: int = 0, generator: str = "phyllotaxis", max_steps: int = 16,
             target: float = 0.9, floor: float = 0.6, scheme: str = "analogous",
             corpus_path: str | Path | None = _CORPUS_PATH) -> Scene:
    """Collected form of run() — the full witnessed Scene."""
    scene: Scene | None = None
    for _kind, _obj in run(seed, generator, max_steps, target, floor, scheme, corpus_path):
        if _kind == "scene":
            scene = _obj  # type: ignore[assignment]
    assert scene is not None
    return scene
