# Changelog

## 2026-07-02 - Live Headless Renderer

- Added `studio_engine/raster_renderer.py`: a zero-dependency software rasterizer
  that turns an emitted `RenderProgram` into actual PNG pixels, consuming the same
  witnessed program the browser chamber would (glsl-fragment fields sampled over
  the u,v grid through the palette ramp; point recipes replayed and rasterized).
- Verified-before-pixels: the renderer reconstructs the strand expression from a
  new `RenderProgram.expr_ast` field, re-hashes it, and refuses to render on any
  `expr_sha256` mismatch (tamper detection), plus an eval cross-check against the
  shipped GLSL `field()` body.
- Extended `engine.run(..., render_frames=True)` to stream deterministic
  `("frame", ...)` entries and fold each frame's `sha256` into the receipt's
  `artifact_shas` with a new `raster.native-render` organ, making a rendered frame
  a re-checkable link in the provenance chain.
- Added `python -m studio_engine --render-frames` to write PNG frames + a
  `frames.json` receipt under `studio-out/`.
- Kept world schemas, existing render programs, audio graphs, and receipt logic
  backward-compatible; `expr_ast` is additive and optional.

## 2026-06-29 - Forward Delivery Contract

- Added a root delivery contract test covering public documentation, developer
  instructions, CI metadata, funding metadata, and brand asset references.
- Added `AGENTS.md`, `USAGE.md`, and Node 24-compatible GitHub Actions CI.
- Added `project-docs/specs/SPEC-studio-engine-forward-delivery.md` as the
  implementation receipt for the delivery pass.
- Normalized forward-facing punctuation for public-surface scanner
  compatibility.
- Kept engine behavior, world schemas, render programs, audio graph generation,
  and receipt logic unchanged.

## Current Status

- Runtime: Python 3.10+ with stdlib-only core engine.
- Surfaces: CLI, local HTTP server, handoff package, browser reference chamber,
  WebGL shader payloads, WebAudio graph data, showcase fixtures, and replayable
  world receipts.
- Verification: Python unit tests, browser JavaScript node tests, and the root
  delivery contract.
