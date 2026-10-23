<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/HarperZ9/studio-engine/main/docs/art/hero-dark.svg">
  <img src="https://raw.githubusercontent.com/HarperZ9/studio-engine/main/docs/art/hero-light.svg" alt="studio-engine: Generate replayable shaders, sound, and motion, each with a receipt. Streamlines of fine lines spiral inward around a bright core." width="100%">
</picture>

# studio-engine

Generate replayable shaders, sound and motion from a seed, in plain Python.

[![version: 0.3.0](https://img.shields.io/badge/version-0.3.0-e6e1d6?style=flat-square&labelColor=1a1712)](https://github.com/HarperZ9/studio-engine/releases/latest)
[![CI](https://github.com/HarperZ9/studio-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/HarperZ9/studio-engine/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-FSL--1.1--MIT-e6e1d6?style=flat-square&labelColor=1a1712)](https://github.com/HarperZ9/studio-engine/blob/main/LICENSE)
![python 3.10+](https://img.shields.io/badge/python-3.10%2B-e6e1d6?style=flat-square&labelColor=1a1712)

studio-engine turns a seed and a generator name into a generative "world": a WebGL fragment shader, a Web Audio synth graph with a matching WAV, a looping motion timeline, a six-colour palette and an SVG preview. It can also render PNG frames on the CPU, with no GPU or browser. Each generator is one math expression. The engine tunes its parameters against scoring rules, so a run reports a score and whether it met its target.

Everything is saved as JSON with SHA-256 hashes of the outputs, so you can rebuild a world from its seed and check the result. It runs on Python 3.10+ with no third-party packages. You get a command line, a local HTTP API, and two browser pages that compile the shader live.

It suits creative coders who want seeded, scriptable shader and sound output from Python, and front-end developers who want a small local API that hands back ready-to-compile GLSL.

## Quickstart

No install step. From a clone:

```bash
git clone https://github.com/HarperZ9/studio-engine
cd studio-engine
python -m studio_engine --render-frames 7 gyroid
```

Output on a fresh clone:

```
world 1e1312cf579e9deb | 'Gyroid #7'
  steps=8 converged=False final_score=0.8922
  render=glsl-fragment expr_sha=528f4a81a82a6ea2
  timeline period=0.628319 continuity=verified
  palette=['#7375cb', '#8e7fd8', '#a88ae3', '#c295ec', '#dca1f3', '#f5adf9']
  wrote studio-out/world-7.json (+ svg preview + render program)
  rendered 8 PNG frame(s) -> studio-out/frames-7/ (+ frames.json)
```

`studio-out/` now holds the world JSON, an SVG preview, the GLSL source, eight 256 by 256 PNG frames across one loop, and `frames.json`, which records each frame's SHA-256.

Run the same command again and the numbers change. The engine keeps a novelty record of every world it has made (`studio_engine/_corpus.json`, git-ignored) and scores each new world against it. Delete that file to get the first-run output back.

To see the shader in a browser, start the API and serve the `handoff/` pages:

```bash
python -m studio_engine.server 8777
python -m http.server 8000 --directory handoff
```

Open `http://127.0.0.1:8000/reference-chamber.html` and press **simulate**. The page compiles the engine's GLSL with WebGL, plays the synth graph, and stacks composites. `watch-it-think.html` in the same folder plots each tuning step live and lets you steer parameters with sliders.

To install it as a package (it is not on PyPI):

```bash
pip install git+https://github.com/HarperZ9/studio-engine
```

This adds a `studio-engine` command that starts the API on port 8777.

## What it can do

- **Ten generators.** `phyllotaxis`, `gyroid`, `quasicrystal`, `attractor`, `harmonograph`, `flowfield`, `metaballs`, `turbulence`, `rings` and `moire`. Field generators are one expression each; adding one means writing an expression and a scoring rule.
- **One expression, several outputs.** The engine emits GLSL from the expression, parses the GLSL back, and tests that both evaluate the same to 1e-6 for every generator. The same expression is sampled on the CPU for scoring and swept over time for the motion loop. The audio graph and the WAV come from one shared parameter set, and tests check that they agree.
- **CPU rendering.** `--render-frames` draws PNG frames with a pure-Python rasterizer. It re-hashes the expression before drawing and refuses to render if the hash does not match.
- **Tuning with a score.** Each run adjusts parameters inside their bounds to raise a combined score (the harmonic mean of the generator's scoring axes plus novelty). It stops at 16 steps or when it converges.
- **Layering.** `POST /compose` stacks several generators into one world with one shared OKLCh palette.
- **Live sessions.** The HTTP API can create a session, take parameter changes, and return the updated shader each step.

Limits:

- Results are reproducible for a fixed novelty record. The same seed on a machine with a different `_corpus.json` gives a different world.
- With an empty novelty record at seed 7, 2 of the 10 generators converge (`phyllotaxis` and `quasicrystal`). The others stop at their best score and say so (`converged=False`).
- Point generators (`phyllotaxis`, `attractor`, `harmonograph`) and `metaballs` have no motion loop.
- CPU frames are 256 by 256. The PNG renderer is for checking and previews; the browser shader is the full-quality output.
- The optional native C++ renderer is a separate project. Without its binary, `POST /native/render` reports that it is missing.
- Version 0.3.0. APIs may change before 1.0.

## How it compares

- **Shadertoy, The Book of Shaders editor.** These are where you write GLSL by hand and see it live. studio-engine writes the GLSL for you from a small library of expressions and tunes the parameters, with far less range than hand-written shaders.
- **p5.js, Processing, Hydra.** Sketching tools with large communities, many examples and drawing APIs. studio-engine has ten generators and no drawing API. It adds seeded tuning, matching audio and a saved record of each output.
- **TouchDesigner, Cables.gl.** Node-based visual editors for live visuals. studio-engine has no visual editor; it is a Python package and an HTTP API you script.

![Eight stages of turning a seed into a witnessed generative world: seed, palette, generate, measure, critique, reflect, refine, and witness. The seed drives a fixed integer hash, so one seed with the same generator, colour scheme and novelty corpus rebuilds the same world every time. The corpus grows with each world it grounds, which is why it is named alongside the seed rather than left implicit. The palette is six perceptual swatches from OKLCh, an even lightness ramp across a hue spread the scheme chooses. Parameters start perturbed inside their declared bounds and are clamped there. Measurement samples the generator over a twenty by twenty grid and reduces it to five features: coverage, centroid offset, contrast, entropy and hue. Critique scores each of the generator's axes from zero to one, adds novelty against a persistent corpus of everything made before, and combines them by harmonic mean, so one weak axis pulls the whole score down instead of being averaged away. Reflection picks the single weakest axis. Refinement is bounded coordinate descent: it tries one step up and one step down on every parameter and keeps the single move that improves cohesion most, halving its reach whenever a whole pass fails to improve. Witnessing keeps the best candidate the run ever saw and records whether it converged, which needs cohesion at the target and every axis above the floor. Three outcomes: converged, best effort, and uncertified.](docs/art/refine-loop.svg)

## HTTP API

`python -m studio_engine.server [port]` serves on 127.0.0.1 (default port 8777). It sends `Access-Control-Allow-Origin: *`, so any page open in your browser can call it while it runs:

| Route | What it does |
| :-- | :-- |
| `POST /simulate` | run the loop, return a World |
| `GET /simulate/stream` | SSE: per-step events, then the world |
| `POST /compose` | layered composite World |
| `GET /generators`, `/library`, `/gallery` | discovery: generators, organs, pre-built scenes |
| `GET /scene/{id}`, `/scene/{id}/program`, `/scene/{id}/filmstrip` | cached worlds, drop-in render programs, per-step replay |
| `GET /audio/{id}.wav` | baked sonification |
| `POST /session`, `/session/{id}/inject`, `/session/{id}/render` | interactive steering and re-render |
| `POST /native/render` | native renderer bridge (reports when the binary is absent) |

The `handoff/` directory is the frontend integration package: [INTEGRATION.md](handoff/INTEGRATION.md), `types.ts`, `openapi.json`, `ENDPOINTS.md`, examples, and both runnable chambers.

## Generators

| Generator | Channel | Scored on |
| :-- | :-- | :-- |
| `phyllotaxis` | points | golden-angle packing |
| `gyroid` | field | clean tiling (integer frequency) |
| `quasicrystal` | field | 5-fold aperiodic order |
| `attractor`, `harmonograph` | points | balance / coverage / complexity |
| `flowfield`, `metaballs`, `turbulence`, `rings`, `moire` | field | contrast / complexity |

Each entry in the registry is a declarative binding: parameter seed and bounds, criteria axes, a preview render, and a strand expression (fields) or a point recipe (points). Adding a generator means writing one expression.

## The strand substrate

The engine generates the shader the browser compiles. It holds each field as a frozen AST, emits the GLSL `field()` body from it, and tests the round trip without a GPU: emit GLSL, parse it back, and check that the reparsed AST evaluates to the original within 1e-6 for every generator. The same AST is sampled on the CPU to compute the features the scoring rules use, and swept over `t` to build the motion timeline.

![Eight stages of taking one expression to every backend without letting the backends drift: expression, emit, parse back, compare, ship, rehash, raster, and frame hash. A generator is one frozen closed-form tree over the variables u, v, t, x, y and i, with twelve operations and no control flow or state. Emitting it produces a GLSL fragment whose division is guarded by a helper that mirrors the Python evaluator's own guard exactly, so the two agree on every input. A recursive-descent parser reads that GLSL back into a tree, and the round trip has to evaluate equal to the original, which is what keeps the emitter honest. The shipped program carries the tree, the source, the uniforms and the sha256 of the canonical expression. Before a single pixel is drawn, the rasterizer rebuilds the tree from the shipped structure, re-hashes it, and refuses to render when the hash no longer matches, so a tampered shader is refused rather than drawn. Rasterizing samples the same u and v range the shader does and maps values through the same piecewise-linear palette ramp, with the top scanline sampling v equals plus one so the headless frame is not flipped against the browser. Each frame's own sha256 is folded back into the receipt. Three outcomes: rendered, refused, and not renderable.](docs/art/strand-lane.svg)

## What's in the box

```
studio_engine/            the engine (stdlib only)
  strand/                 expr.py (frozen AST), glsl.py (emit + parse-back proof)
                          recipe.py (point recipes), webaudio.py (synth graph)
  model.py                the contract: World / Layer / RenderProgram / AudioProgram / Timeline
  engine.py               the loop          registry.py    the 10-generator data table
  compose.py              the compositor    temporal.py    the witnessed motion timeline
  criteria.py             composable criteria + cohesion   corpus.py   novelty grounding
  raster_renderer.py      headless software rasterizer (PNG frames)
  native_render.py        bridge to the optional native C++ renderer
  certify.py              optional outside check (needs coherence-membrane)
  session.py              interactive steering              server.py   the HTTP API
  organs/                 generators, OKLab palettes, sonify, raster
handoff/                  frontend package: INTEGRATION.md, types.ts, openapi.json,
                          reference-chamber.html, watch-it-think.html, examples/
showcase/                 static showcase with its own fixtures and Node tests
```

## See it work, step by step

The [animated explainer](https://harperz9.github.io/repo-explainers/studio-engine.html)
walks through a gyroid refined over eight steps, the outside certificate, one expression as shader, timeline and synth, PNG frames and a refused tampered program, and how the novelty corpus changes a rerun. Every value on it is output from this repository. Its
source is [docs/explainer/index.html](docs/explainer/index.html).

## Walkthrough

Each command below was run on a fresh clone, and the output is what it printed.

1. **Get it.** Clone it. Python 3.10 or newer, no install step.

   ```text
   $ git clone https://github.com/HarperZ9/studio-engine && cd studio-engine
   ```

2. **First run: a world with frames.** Generate the gyroid at seed 7 and render PNG frames with no GPU.

   ```text
   $ python -m studio_engine --render-frames 7 gyroid
   world 1e1312cf579e9deb | 'Gyroid #7'
     steps=8 converged=False final_score=0.8922
     render=glsl-fragment expr_sha=528f4a81a82a6ea2
     timeline period=0.628319 continuity=verified
     rendered 8 PNG frame(s) -> studio-out/frames-7/ (+ frames.json)
   ```

3. **Open the chamber.** Start the API, then open `handoff/reference-chamber.html` to see the shader and hear the synth.

   ```text
   $ python -m studio_engine.server 8777
   ```

## What a world records

A world keeps the shader program, sound graph, motion timeline and scoring rules together, so you can re-render it, steer it, or check it later.

`(seed, generator, scheme)` determines a world for a fixed novelty record: same input, same id and SHA-256 hashes. Every world carries each tuning step, the scoring rules it was judged against, and a `receipt` block whose hashes cover the JSON, the audio, and any rendered frames.

## Every number, and where it comes from

![Twelve rows covering every number a world reports and where it comes from. Ten generators ship: phyllotaxis, gyroid, quasicrystal, attractor, harmonograph, flowfield, metaballs, turbulence, rings and moire. Seven criteria axes are available, three judging a parameter against a constant the engine did not author and four judging measured features of the output. Cohesion is the harmonic mean of the axes, so one weak axis pulls the whole score down instead of averaging itself away. Convergence needs cohesion at or above the target and every single axis at or above the floor, and either condition alone is not enough. The loop caps at sixteen steps by default, stopping earlier on convergence or when the step size shrinks past two hundredths of a parameter range. That step size starts at a third of each range and multiplies by just over a half whenever a full pass fails to improve. Measurement runs over a twenty by twenty grid, four hundred cells reduced to coverage, centroid offset, contrast, entropy and hue. Novelty is nearest-neighbour distance in that five-feature unit cube over its diagonal, so a first of its kind scores one, and the corpus grows with every world it grounds. The palette is six OKLCh swatches at fixed chroma with lightness ramped across a fixed span and hue spread chosen by the scheme. The algebra is twelve operations over six variables with no control flow and no state, so a shader and a software rasterizer derive from one frozen tree. The accented row is the external verdict, which comes from an independent oracle with its own tolerance and reads unverifiable when that oracle is not installed rather than passing itself. The last row is rendered frames: a deterministic strip of eight across the loop period, or a single still, each frame's own sha256 folded into the receipt.](docs/art/engine-table.svg)

## Scope and maturity

Version 0.3.0. The engine emits render programs and records; browsers, GPUs and audio hosts play them. The immersive chamber is the frontend's build, from `handoff/`. The dependency-free native GPU renderer is a separate project that this engine bridges to optionally. APIs may still move before 1.0.

## Docs and related projects

- [USAGE.md](USAGE.md): the full local workflow, including the showcase.
- [docs/INTRODUCTION.md](docs/INTRODUCTION.md): concepts and a first-ten-minutes walkthrough.
- [handoff/INTEGRATION.md](handoff/INTEGRATION.md): build a frontend against the API.
- [docs/design/SUBSTRATE-MAP.md](docs/design/SUBSTRATE-MAP.md): the strand substrate design.
- Peers: [forum](https://github.com/HarperZ9/forum) (multi-agent orchestration), [accountable-surface](https://github.com/HarperZ9/accountable-surface) (permission checks for AI agent actions).

## For developers

```bash
python -m pip install -e .
python -m pip install coherence-membrane   # only for tests/test_certify.py
python -m unittest discover -s tests        # 190 tests
node --test showcase/tests/*.test.mjs
python test_forward_delivery_contract.py
```

See [AGENTS.md](AGENTS.md) for the repo operating boundary and [CHANGELOG.md](CHANGELOG.md) for delivery history.

## License

From v0.3.0, code is licensed FSL-1.1-MIT. Earlier releases remain under AGPL-3.0-or-later. FSL-1.1-MIT is the Functional Source License, Version 1.1, with MIT as the future licence: each release becomes available under MIT two years after it is made available. See [LICENSE](LICENSE). Every commit in this repository is by the author, who retains copyright; other terms are available from the author.

**Zain Dana Harper**, small tools with explicit edges. Built with Claude Code; reviewed, tested, owned.

## What this believes

This tool is one lane of a family that holds a single belief steady across
every surface: knowledge open to anyone who can attain the means; acceptance
decided by external checks, never reputation; every result re-runnable;
honest nulls first-class; ownership earned by comprehension; learning woven
into the work. The full text lives in [CREDO.md](CREDO.md).
The long form of this belief: [The Unbundling](https://github.com/HarperZ9/flywheel/blob/main/docs/essays/2026-07-13-the-unbundling.md).

---

Built by **[Zain Dana Harper](https://harperz9.github.io)** in Seattle: evidence-first tools that leave a re-checkable artifact behind. The full workbench is at [Project Telos](https://harperz9.github.io).
