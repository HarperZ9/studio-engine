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
from .organs import geometry as geo, palette as pal, fields as fld, raster as ras, sonify as snd
from . import criteria as crit
from .corpus import Corpus

_CORPUS_PATH = Path(__file__).resolve().parent / "_corpus.json"
_G = 20  # feature grid resolution


def _gens() -> dict[str, dict[str, Any]]:
    return {
        "phyllotaxis": {
            "params0": lambda rng: {"angle": crit.GOLDEN_ANGLE + (((rng % 2000) / 1000.0) - 1.0) * 9.0,
                                    "scale": 7.0 + (rng >> 8) % 7, "dot": 3.0 + ((rng >> 16) % 30) / 10.0},
            "bounds": {"angle": (110.0, 165.0), "scale": (5.0, 16.0), "dot": (2.5, 6.5)},
            "axes": ["golden_angle", "balance", "coverage", "complexity"],
            "render": lambda p, pl: geo.to_svg(geo.phyllotaxis(700, p["angle"], p["scale"]), pl, dot=p["dot"]),
            "points": lambda p: geo.phyllotaxis(700, p["angle"], p["scale"]),
            "field": None,
        },
        "gyroid": {
            "params0": lambda rng: {"freq": round(4.0 + (rng % 500) / 100.0, 3),
                                    "z": round(0.2 + (rng >> 9) % 60 / 100.0, 3)},
            "bounds": {"freq": (3.0, 10.0), "z": (0.05, 0.95)},
            "axes": ["clean_freq", "contrast", "complexity"],
            "render": lambda p, pl: fld.gyroid_field_svg(freq=p["freq"], palette=pl, samples=64),
            "points": None,
            "field": lambda p, u, v: (math.sin(u * p["freq"]) * math.cos(v * p["freq"])
                                      + math.sin(v * p["freq"]) * math.cos(p["z"] * p["freq"])
                                      + math.sin(p["z"] * p["freq"]) * math.cos(u * p["freq"])),
        },
        "quasicrystal": {
            "params0": lambda rng: {"waves": float(3 + (rng % 5)), "scale": 6.0 + (rng >> 10) % 8},
            "bounds": {"waves": (3.0, 9.0), "scale": (4.0, 14.0)},
            "axes": ["fivefold", "contrast", "complexity"],
            "render": lambda p, pl: fld.quasicrystal_svg(waves=int(round(p["waves"])), palette=pl, samples=72),
            "points": None,
            "field": lambda p, u, v: sum(
                math.cos(math.cos(2 * math.pi * k / max(1, int(round(p["waves"]))) ) * u * p["scale"]
                         + math.sin(2 * math.pi * k / max(1, int(round(p["waves"]))) ) * v * p["scale"])
                for k in range(max(1, int(round(p["waves"]))))),
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


def simulate(seed: int = 0, generator: str = "phyllotaxis", max_steps: int = 16,
             target: float = 0.9, floor: float = 0.6, scheme: str = "analogous",
             corpus_path: str | Path | None = _CORPUS_PATH) -> Scene:
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
    traj = Trajectory(steps, accepted_index=len(steps) - 1, converged=converged)

    corpus.add(feats)  # ground future novelty in what we just made
    sid = _sha(f"{seed}:{generator}:{json.dumps(params, sort_keys=True)}:{svg.sha256}")
    organ_ids = [generator, "palette.oklch", "criteria.multi_axis", "criteria.novelty", "sonify.params"]
    if spec["points"]:
        organ_ids.append("raster.png")
    receipt = Receipt(sid, seed, organ_ids, artifact_shas, round(coh, 4))
    return Scene(id=sid, title=f"{generator.title()} #{seed}", layers=layers,
                 audio=audio, trajectory=traj, receipt=receipt, palette=palette)
