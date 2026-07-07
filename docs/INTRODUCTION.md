# Introduction to Studio Engine

Studio Engine is a zero-dependency Python engine that generates creative worlds:
procedural shaders, sound, and motion, packaged so they can be replayed, rendered,
and checked anywhere. You give it a seed and a generator name; it runs a refine
loop and hands back a self-describing World: a WebGL fragment shader for the eye,
a Web-Audio synth graph for the ear, a motion timeline with time as a first-class
axis, an SVG preview, and the full trajectory of how it got there.

It runs on Python 3.10+ from a plain checkout, no pip install and no third-party
packages. The surfaces are a CLI, a local HTTP API, and two runnable browser
chambers shipped in `handoff/`.

## Why it exists

Generated art is usually a dead end: an image with no structure a person or a
later program can inspect. Studio Engine keeps the program, the criteria, and the
evidence together, so a generated world is an artifact you can re-render, steer,
and re-check rather than a one-off output. That is the whole doorway; the rest of
this document is about what it does.

## Core concepts

### World

The unit of output. A World (schema `studio-engine/2`) bundles one or more
Layers, a palette, an optional Timeline, the refine trajectory, and a receipt.
`(seed, generator, scheme)` determines a World for a fixed novelty corpus: same
input, same id and same content hashes.

### Strand: one expression, many backends

Every field generator is a single closed-form expression in the `strand` algebra,
held as a frozen AST. That one AST is:

- emitted as the GLSL `field()` body the browser compiles (the eye),
- sampled on CPU to compute the features the criteria score (the judge),
- swept over `t` to build the motion timeline (the clock),
- paired with a Web-Audio synth graph grounded against a baked WAV (the ear).

The emit step is proven round-trip: the engine parses its own GLSL back into an
AST and checks it eval-matches the original to 1e-6 for every generator. So the
shader a frontend compiles is the exact math the engine verified.

Point generators (phyllotaxis, attractor, harmonograph) emit a replayable point
recipe instead of a fragment shader.

### The loop

Each run is perceive, generate, critique, refine, witness. The engine drafts
parameters from the seed, scores the draft against a criterion the generator did
not author (golden-angle packing for phyllotaxis, clean tiling for gyroid, and so
on), nudges the weakest axis, and repeats until converged or out of steps. The
whole path is recorded in the World's trajectory.

### Generators

Ten ship in the registry: `phyllotaxis`, `gyroid`, `quasicrystal`, `attractor`,
`harmonograph`, `flowfield`, `metaballs`, `turbulence`, `rings`, `moire`. Each
registry entry is declarative data: parameter bounds, criteria axes, a preview
render, and the expression or recipe. Adding one means writing one expression.

### Renderers

- **Browser**: `handoff/reference-chamber.html` compiles the shipped GLSL live
  and plays the synth graph.
- **Headless**: `studio_engine/raster_renderer.py` is a software rasterizer that
  turns the same render program into deterministic PNG files, no GPU and no
  dependencies. It re-hashes the shipped AST first and refuses to render on a
  mismatch.
- **Native (optional)**: `studio_engine/native_render.py` bridges to a separate
  native C++ CLI when one is built and reports honestly when it is not.

## Your first ten minutes

From a clone of the repo:

**1. Generate a world (about 10 seconds).**

```bash
python -m studio_engine 7 gyroid
```

You get a summary line with the world id, step count, final score, the render
target (`glsl-fragment`), the timeline period, and the palette. Three files land
in `studio-out/`: `world-7.json` (the full World), `artifact-7.svg` (a preview
you can open now), and `program-7.txt` (the GLSL fragment as text).

**2. Render real pixels, no GPU.**

```bash
python -m studio_engine --render-frames 7 gyroid
```

Same loop, then the headless rasterizer writes PNG frames sweeping the loop
period to `studio-out/frames-7/`, plus a `frames.json` manifest with a sha256
per frame. Open them in any image viewer.

**3. Start the API and open a chamber.**

```bash
python -m studio_engine.server 8777
```

The server pre-builds a gallery on start. Open `handoff/reference-chamber.html`
in a browser: it fetches worlds from the API, compiles the GLSL live, stacks
composites, and plays audio.

**4. Watch it think.**

Open `handoff/watch-it-think.html` with the server still running. It subscribes
to `GET /simulate/stream` (Server-Sent Events) and plots per-axis criterion
margins as the loop converges, weakest axis highlighted. Move a slider to steer
a parameter mid-run: values outside the generator's bounds come back as visible
rejections, never silently clamped in.

**5. Try the other generators.**

```bash
python -m studio_engine 12 quasicrystal
python -m studio_engine 3 moire
```

Or list everything over HTTP: `GET /generators`, `GET /library`,
`GET /gallery`. Layer organs into one world with `POST /compose`.

## Where to go next

- [../USAGE.md](../USAGE.md): the full local workflow, including the static
  showcase and the verification commands.
- [../handoff/INTEGRATION.md](../handoff/INTEGRATION.md): build your own
  frontend chamber against the API; includes `types.ts` and `openapi.json`.
- [design/SUBSTRATE-MAP.md](design/SUBSTRATE-MAP.md) and
  [design/2026-06-21-strand-substrate.md](design/2026-06-21-strand-substrate.md):
  how the strand substrate is put together.
- [../CHANGELOG.md](../CHANGELOG.md): delivery history.
- Tests are the sharpest reference: `tests/` covers the expression algebra, the
  GLSL round trip, the rasterizer, the server contract, and the SSE stream
  (169 tests, `python -m unittest discover -s tests`).

A closing note on receipts: every World carries its trajectory, its criteria,
and content hashes for its artifacts, so anything this engine makes can be
replayed and checked later. That guarantee rides along with every feature above;
it is not a separate mode.
