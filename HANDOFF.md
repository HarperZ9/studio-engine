# studio-engine → frontend handoff

**You are building the experience chamber** — an immersive visual-auditory room — on top of this
engine. The engine is done, zero-dependency, tested, and runs with no install; you build the front.

## Start in 3 steps
1. `python -m studio_engine.server 8777`   — the API (zero install; CORS open: `*`)
2. Read **`handoff/INTEGRATION.md`** — the mental model + the gorgeous-rendering path.
3. Open **`handoff/reference-chamber.html`** in a browser — a runnable reference consumer; crib from it.

## Your contract (`handoff/`)
- **`types.ts`** — TypeScript types (the exact shapes).
- **`openapi.json`** — machine spec (codegen-ready).
- **`ENDPOINTS.md`** — every endpoint (incl. live SSE + interactive sessions).
- **`examples/`** — real request/response payloads.

## What the engine gives you
Witnessed `Scene`s, deterministic per `(seed, generator, scheme)`: a **live-render `params` layer**
(render natively — canvas for point generators, WebGL for field generators), an SVG/PNG preview,
**audio params** (drive Web Audio), the multi-axis refine **trajectory** (the machine's reasoning —
per-axis `margins` + `cohesion`), and a **receipt** (reproducible). **8 generators**
(phyllotaxis · gyroid · quasicrystal · attractor · harmonograph · flowfield · metaballs · turbulence).
- **Live:** SSE `GET /simulate/stream` — watch the loop think, step by step.
- **Interactive:** `POST /session` → `step` / `inject` (steer a parameter) / `explain` (ask why an axis
  scores what it does) — the two-way cross-examine.
- **Animate:** `GET /scene/{id}/filmstrip` — per-step params for replaying convergence.

## Your task
Build the chamber: render the `params` layer live, sonify from the audio params, visualize the
trajectory as the reasoning, theme from the palette, and wire the gallery + simulate + (optionally)
the live stream and a cross-examine session. Make it mind-blowing — the engine guarantees every
frame is grounded and reproducible.

## Honest scope (don't oversell)
This is the **engine that FEEDS the chamber**. The dependency-free **native GPU renderer**
(no DirectX/driver) is a separate telos (the `raw` project) — **not** in this package. The chamber
is your realization of an immersive room over the engine's grounded stream. Don't claim the unbuilt.

---
Repo: `github.com/HarperZ9/studio-engine` · License: **AGPL-3.0** (don't relicense; commercial terms
via the author) · Tests: `python -m unittest discover -s tests` (56, green).
