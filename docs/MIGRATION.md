# Migration: where studio-engine's features live now

studio-engine is deprecated. It dates from the period when Telos was the only flagship, and most of what it does has since moved into other repositories. This page maps each feature to its current home, marks what has not moved, and plans the move for the parts worth keeping. The repository stays up and is not archived. Archiving waits until the planned work below lands and the author agrees.

## Successors

| Repository | What it is now |
|---|---|
| [reconcile](https://github.com/HarperZ9/reconcile) | The JavaScript port of this engine's core: generators, expression algebra, criteria, refine loop, compositor, timeline, receipts. Runs in Node and the browser. |
| [telos](https://github.com/HarperZ9/telos) | The workbench. Its creative engine holds deterministic kernels (harmonograph, ordered dither, pixel sort, clustered light), a pure-JS raster backend and DFT-backed sound generation. |
| [raw-native](https://github.com/HarperZ9/raw-native) | The native C++23 renderer. It replaces the renderer that `native_render.py` bridged to. |
| [superstack](https://github.com/HarperZ9/superstack) | The shared contract for renderers and sound engines: canonical bytes, seed rule, receipts. |
| [The Shared Frame](https://harperz9.github.io/shared-frame/) and the [Retro Engine](https://harperz9.github.io/retro.html) | Browser surfaces on the main site. The Shared Frame descends from `showcase/`. The Retro Engine is the GLSL preset library and live shader runner. |

The closest matches for a shader suite are the Retro Engine's preset library and runner on the main site and the raw-native renderer. Both are separate code from the strand expression algebra. Correct this table if a shader suite repository turns up.

## Feature map

Status values: migrated (a working equivalent exists elsewhere), partly migrated (some of the feature exists), missing (the feature lives in this repository alone). This survey compared module names, generator ids and public behavior, so "migrated" means present. Output parity gets its check in the golden-vector step below, which is still to run.

| Feature in studio-engine | Status | Where it lives now | Gap |
|---|---|---|---|
| Ten generators (phyllotaxis, gyroid, quasicrystal, attractor, harmonograph, flowfield, metaballs, turbulence, rings, moire) | migrated | reconcile `src/organs/fields.js` (seven fields) and `forms.js` (three point organs); a copy is vendored in the main site | Parameter bounds and criteria not compared |
| Strand expression algebra, GLSL emit, parse-back proof | migrated | reconcile `src/expr.js` | None found |
| Criteria, novelty corpus, cohesion, bounded refine loop | migrated | reconcile `criteria.js`, `corpus.js`, `refine.js` | Corpus file format not compared |
| Compositor (`/compose`) | migrated, library only | reconcile `compose.js` | No HTTP route, no UI |
| Witnessed motion timeline | migrated | reconcile `temporal.js` | None found |
| OKLab and OKLCh palettes | migrated | reconcile `palette.js` | None found |
| Replayable world and receipt | partly migrated | reconcile `world.js` | JSON schema not confirmed identical to `handoff/types.ts` |
| CLI (`python -m studio_engine 7 gyroid`) | migrated | `node cli.js create gyroid --seed 7` in reconcile | Output ids not compared |
| Showcase page and fixtures | migrated | The Shared Frame on the main site, with its own ports of the engine, eye and verdict code | None found |
| External structural-fitness oracle | migrated | coherence-membrane, used by the Shared Frame | Optional in both |
| Reference chamber (`handoff/reference-chamber.html`) | partly migrated | reconcile `web/index.html` renders a world in the browser | No audio, no composite button, no live API |
| Web Audio synth graph and baked WAV (`strand/webaudio.py`, `organs/sonify.py`, `/audio/{id}.wav`) | partly migrated | telos `render-sound` generates sound; reconcile leaves audio to the host; superstack defines the sound contract | Nothing turns a world into an `audio_program` outside this repository |
| Headless software rasterizer, PNG frames, hash refusal (`raster_renderer.py`) | partly migrated | telos `render-nd` has a pure-JS RGBA raster backend; raw-native renders on the CPU with certificates | Nothing rasterizes a strand program to PNG and refuses on an expression-hash mismatch |
| Native renderer bridge (`native_render.py`) | partly migrated | raw-native is the renderer it bridged to | The bridge client exists only here |
| HTTP API (`/simulate`, `/simulate/stream`, `/gallery`, `/scene/*`, `/session`) and `handoff/openapi.json` | missing | none | No server in reconcile or telos exposes these routes |
| Interactive sessions: inject parameters, clamped-steer rejection | partly migrated | The Shared Frame lets a visitor move parameters and run one refine step in the browser | Rejected steers are not surfaced; no session object for agents |
| Watch it think (`handoff/watch-it-think.html`, SSE trajectory plot) | missing | none | The only live view of the refine loop |
| OpenAPI, TypeScript types, example payloads | missing | none | Tied to the HTTP API |

## Plan for what is missing

This is a plan; the code comes next. Each item names a target, an acceptance check and, where one exists, an open question.

### 1. Audio program emitter

Move `strand/webaudio.py` and `organs/sonify.py` into reconcile as `src/audio.js`, emitting the same `audio_program` data (oscillators, pitch curve, envelope) from a world. Playback stays with the host. For the WAV bake, use the superstack sound-scene contract so the bytes can be checked across engines.

Acceptance: for the worlds in `handoff/examples/` and `showcase/worlds/`, the JavaScript `audio_program` equals the Python one field for field, and the baked PCM matches under a superstack receipt.

Open question: whether the telos `render-sound` DFT code or reconcile should own the bake.

### 2. Frame rasterizer with the hash check

Port `raster_renderer.py` to a pure-JS backend. Prefer extending the telos `render-nd` raster backend over writing a third rasterizer. Keep the three behaviors that matter. Sample the same u and v range as the shader. Rebuild the expression from the shipped structure and re-hash it before drawing. Write a `frames.json` that binds each frame hash to the expression hash.

Acceptance: eight frames of gyroid seed 7 hash to the same sha256 values as the Python output, and a program with an edited expression is refused.

### 3. Live trajectory and steering without a server

reconcile already runs in the browser, so streaming the refine loop needs no HTTP. Expose the loop as an async generator that yields each step. Port `watch-it-think.html` to reconcile's `web/` directory on top of it, with bounds-clamped sliders and visible rejected steers. For agents, offer the same stepper as a tool in the telos creative engine, which avoids a new server.

Acceptance: the plotted per-axis margins equal the persisted trajectory for all ten generators, the check that `tests/test_sse_step_contract.py` makes today.

### 4. Composite and audio controls in the reconcile page

Add the composite action and a play button to reconcile's browser page once items 1 and 3 land, so the reference chamber has a full successor.

### 5. HTTP API

Decide this first. A consumer of `handoff/openapi.json` is still to be found. If one exists, put a thin Node server in reconcile that reuses item 3's stepper. Otherwise drop the API and keep `handoff/types.ts` and the example payloads as the world schema in reconcile.

Open question for the author: does any outside consumer depend on the API?

### 6. Golden vectors

Before any port is declared done, copy `handoff/examples/*.json` and the unit-test expectations into reconcile as fixtures. This step turns "migrated" in the table above into a checked claim.

### 7. Native bridge

Keep `native_render.py` as a reference for the channel-certificate format. Port it once raw-native gains a parameterized loop that something calls. Low priority.

## What retiring this repository needs

1. Items 1, 2, 3 and 6 land, or the author drops them.
2. The main site's studio-engine explainer and the Shared Frame README carry a deprecation line pointing here.
3. The author agrees to archive.

Until then this repository takes fixes and migration work.
