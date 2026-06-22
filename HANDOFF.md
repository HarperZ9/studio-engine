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
Witnessed `World`s (schema `studio-engine/2`), deterministic per `(seed, generator, scheme)` for a
fixed corpus. Each layer carries a **`render_program`** you run directly:
- **field generators → `glsl-fragment`**: `render_program.source` is a COMPLETE WebGL fragment shader
  whose `field()` body *is* the verified expression — compile it verbatim, set `u_palette` /
  `u_value_range`, animate `u_time` within `[0, domain.period)`.
- **point generators → `point-recipe`**: a `recipe` (spiral / iterated / parametric) you run on canvas.

Plus an **`audio_program`** (a Web-Audio synth graph: oscillators + a pitch-sweep curve), a witnessed
**`timeline`** (continuity + on-criterion verdicts — the motion is grounded, not improvised), the
multi-axis refine **`trajectory`** (per-axis `margins` + `cohesion`), an SVG **preview** fallback per
layer, and a re-checkable **receipt**. **10 generators** (phyllotaxis · gyroid · quasicrystal ·
attractor · harmonograph · flowfield · metaballs · turbulence · rings · moire).
- **Compose:** `POST /compose {seed,organs[],scheme}` — layered Worlds + a composition verdict.
- **Programs:** `GET /scene/{id}/program` — the drop-in render programs for a cached World.
- **Live:** SSE `GET /simulate/stream` — `step` events then `world`; watch the loop think.
- **Interactive:** `POST /session` → `step` / `inject` / `explain`; the state carries a live
  `program` of the steered candidate — render it as you cross-examine.
- **Animate:** `GET /scene/{id}/filmstrip` — per-step params for replaying convergence.

## Your task
Build the chamber: compile the `render_program` live (WebGL for fields, canvas for point recipes),
play the `audio_program`, visualize the `trajectory` + `timeline` as the reasoning, theme from the
palette, and wire gallery + simulate + compose + (optionally) the live stream and a cross-examine
session. Make it mind-blowing — the engine guarantees every frame is grounded and reproducible.

## Honest scope (don't oversell)
This is the **engine that FEEDS the chamber**. The dependency-free **native GPU renderer**
(no DirectX/driver) is a separate telos (the `raw` project) — **not** in this package. The chamber
is your realization of an immersive room over the engine's grounded stream. Don't claim the unbuilt.

---
Repo: `github.com/HarperZ9/studio-engine` · License: **AGPL-3.0** (don't relicense; commercial terms
via the author) · Tests: `python -m unittest discover -s tests` (111, green).
