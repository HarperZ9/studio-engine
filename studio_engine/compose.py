"""Compositor: layer several organs into one witnessed World, judged by a composition criterion.

The reconcile's compose() at the scene level. Layers share one palette (depth-ordered: fields
behind, points in front) and are scored on three axes -- palette harmony, depth complementarity
(layers occupy different coverage bands so they don't fully occlude), and contrast balance --
combined by cohesion. A composite is itself an (organ-graph, composition-criterion) binding.
Stdlib + engine internals only.
"""
from __future__ import annotations

import math

from . import engine
from . import criteria as crit
from .model import World, Verdict, Receipt, _sha
from .organs import palette as pal
from .organs.sonify import _hex_to_rgb, _rgb_to_hue_light
from .certify import world_certificate


def _palette_harmony(palette: list) -> float:
    """Circular concentration of palette hues (0..1): clustered hues read as harmonious."""
    hues = [_rgb_to_hue_light(*_hex_to_rgb(c))[0] for c in palette if c]
    if len(hues) < 2:
        return 1.0
    sx = sum(math.cos(2 * math.pi * h) for h in hues)
    sy = sum(math.sin(2 * math.pi * h) for h in hues)
    return math.hypot(sx, sy) / len(hues)


def composition_axes(layer_feats: list, palette: list) -> dict:
    """Score how a set of layers coheres: palette harmony, depth complementarity, contrast balance."""
    covs = [f.get("coverage", 0.0) for f in layer_feats]
    contrasts = [f.get("contrast", 0.0) for f in layer_feats]
    depth = min(1.0, (max(covs) - min(covs)) / 0.6) if len(covs) > 1 else 0.5
    mc = (sum(contrasts) / len(contrasts)) if contrasts else 0.0
    balance = max(0.0, 1.0 - abs(mc - 0.5) * 2.0)
    return {"palette_harmony": round(_palette_harmony(palette), 4),
            "depth_complementarity": round(depth, 4),
            "contrast_balance": round(balance, 4)}


def compose(seed: int = 0, organ_set: list | None = None, scheme: str = "analogous",
            corpus_path=None) -> World:
    """Build a layered composite World over `organ_set`, scored by the composition criterion."""
    organ_set = organ_set or ["gyroid", "phyllotaxis"]
    gens = engine._gens()
    for name in organ_set:
        if name not in gens:
            raise ValueError(f"unknown generator {name!r}; have {list(gens)}")
    palette = pal.generate_palette(seed, n=6, scheme=scheme)

    layers, layer_feats, shas = [], [], []
    first = None
    for i, name in enumerate(organ_set):
        world = engine.simulate(seed, generator=name, scheme=scheme, corpus_path=corpus_path)
        first = first or world
        spec = gens[name]
        acc = world.trajectory.steps[world.trajectory.accepted_index]
        layer_feats.append(engine._features(spec, dict(acc.params), palette))
        lyr = world.layers[0]
        lyr.z = (i - 10) if spec["field"] is not None else (i + 10)  # fields behind, points front
        lyr.blend = "normal" if i == 0 else "screen"
        lyr.title = f"{name.title()} (layer {i})"
        layers.append(lyr)
        shas.append(lyr.render_program.expr_sha256)
    layers.sort(key=lambda lyr: lyr.z)

    axes = composition_axes(layer_feats, palette)
    score = crit.cohesion(list(axes.values()))
    comp = Verdict("composition", crit.tag(score), round(score, 4),
                   "; ".join(f"{k}={v}" for k, v in axes.items()))
    sid = _sha("compose:" + ":".join(organ_set) + f":{seed}:{scheme}:" + ":".join(shas))
    return World(id=sid, title="Composite: " + " + ".join(organ_set), layers=layers,
                 audio_program=first.audio_program, timeline=first.timeline,
                 trajectory=first.trajectory,
                 receipt=Receipt(sid, seed, list(organ_set) + ["compose"], shas, round(score, 4)),
                 palette=palette, composition=comp,
                 certificate=world_certificate(score).to_dict())
