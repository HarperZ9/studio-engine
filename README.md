# studio-engine

> A native, **zero-dependency** creative-verification simulation engine. It composes generative
> + verification organs into one witnessed loop and emits **Scenes** — visuals + audio + the
> reasoning trajectory — for an **experience-chamber** frontend to render.

![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![deps: none](https://img.shields.io/badge/deps-none-success.svg)
![license: AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)

Every scene is a *witnessed creative act*: **perceive → generate → critique → refine → witness**.
The engine generates art, judges it against a criterion it did **not** author, refines toward
"correct," and records the whole replayable path with a re-checkable receipt. Grounded creativity
and verification as one loop — the accountability spine, turned toward making things.

## Quick start (no install, stdlib only)

```bash
python -m studio_engine 7                 # run the loop, write studio-out/scene-7.json + .svg
python -m studio_engine.server 8777       # serve the API at http://127.0.0.1:8777 (CORS *)
```

Then open `handoff/reference-chamber.html` in a browser — a runnable reference experience chamber.

## What's in the box

```
studio_engine/            the engine (zero-dep, stdlib only)
  model.py                the contract: Scene / Artifact / Verdict / Trajectory / Receipt
  engine.py               the loop + generator registry (phyllotaxis / gyroid / quasicrystal)
  organs/                 the resource library
    geometry.py           phyllotaxis + the golden-angle criterion
    fields.py             gyroid + quasicrystal generators + their criteria
    palette.py            OKLab/OKLCh perceptual palettes
    raster.py             native PNG writer (zlib only)
    sonify.py             WAV synthesis + live Web-Audio params
  server.py               the HTTP API (http.server)
handoff/                  >>> the frontend package <<<
  INTEGRATION.md          read this first — how to build the chamber
  types.ts                TypeScript contract types
  openapi.json            OpenAPI 3.0 spec (codegen-ready)
  ENDPOINTS.md            endpoint reference
  examples/               real example payloads (scene, library, gallery, request)
  reference-chamber.html  runnable single-file reference consumer
```

## Generators (extensible)

| Generator | Parameter | Criterion (it didn't author) |
|---|---|---|
| `phyllotaxis` | `angle_deg` | golden-angle packing |
| `gyroid` | `freq` | clean tiling (integer frequency) |
| `quasicrystal` | `waves` | 5-fold aperiodic order |

Each generator is `{initial, fit, refine, render}` — add one and it's in the API + the chamber.

## Determinism + receipts

`(seed, generator, scheme)` fully determines a scene — same input, same `scene.id` and `sha256`s.
The receipt makes every experience reproducible and re-checkable. That honesty is the point.

## Honest scope

This is the **generation + verification** engine that *feeds* an experience chamber — real
visuals, real audio params, real witnessed reasoning. The chamber (the immersive room) is the
frontend's realization, built from `handoff/`. The dependency-free **native GPU renderer** (no
DirectX/driver) is `raw`'s separate telos — not this package; named as the horizon this engine is
built to later sit on.

## License

AGPL-3.0-or-later, dual-license-ready (the author retains copyright; commercial licenses
available). Matures the shipped sensory-algebra organs (contour/SVG, OKLab, render-critic,
reconcile/refine) into a composable, witnessed engine.

**Zain Dana Harper** — small tools with explicit edges. Built with Claude Code; reviewed, tested, owned.
