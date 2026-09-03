<p align="center"><img src="docs/art/studio-engine-header.svg" alt="studio-engine: generative worlds, with a re-checkable receipt." width="100%"></p>

**A native simulation and render engine: generate, critique, refine, and keep the scene.**

![version](https://img.shields.io/badge/version-0.2.0-26dfe8?style=flat-square&labelColor=14041b)
![license](https://img.shields.io/badge/license-AGPL--3.0--or--later-8f8095?style=flat-square&labelColor=14041b)

Studio Engine generates shaders, sound, and motion as replayable creative worlds. A single expression algebra drives everything: each field ships as a WebGL fragment shader for the eye, a portable Web-Audio synth graph for the ear, and a motion timeline with time as a first-class axis. It runs on Python 3.10+ with zero third-party dependencies, exposing a CLI, a local HTTP API, and a reference browser chamber that compiles the shipped GLSL live. Every world writes a receipt you can re-check.

![Eight stages of turning a seed into a witnessed generative world: seed, palette, generate, measure, critique, reflect, refine, and witness. The seed drives a fixed integer hash, so one seed with the same generator, colour scheme and novelty corpus rebuilds the same world every time. The corpus grows with each world it grounds, which is why it is named alongside the seed rather than left implicit. The palette is six perceptual swatches from OKLCh, an even lightness ramp across a hue spread the scheme chooses. Parameters start perturbed inside their declared bounds and are clamped there. Measurement samples the generator over a twenty by twenty grid and reduces it to five features: coverage, centroid offset, contrast, entropy and hue. Critique scores each of the generator's axes from zero to one, adds novelty against a persistent corpus of everything made before, and combines them by harmonic mean, so one weak axis pulls the whole score down instead of being averaged away. Reflection picks the single weakest axis. Refinement is bounded coordinate descent: it tries one step up and one step down on every parameter and keeps the single move that improves cohesion most, halving its reach whenever a whole pass fails to improve. Witnessing keeps the best candidate the run ever saw and records whether it converged, which needs cohesion at the target and every axis above the floor. Three outcomes: converged, best effort, and uncertified.](docs/art/refine-loop.svg)

## Highlights

- **One algebra, every backend.** Each generator is a single `strand` expression. The engine emits it as a WebGL fragment shader, samples it to score criteria, sweeps it over time for motion, and grounds a Web-Audio synth graph against a baked WAV. The chamber renders the exact math the engine checked, not a re-implementation.
- **Real pixels without a GPU.** `--render-frames` drives a zero-dependency software rasterizer over the emitted program and writes deterministic PNG frames to disk, a strip across the loop period for animatable fields.
- **Watch it think, live.** `handoff/watch-it-think.html` streams the refine loop over Server-Sent Events and plots per-axis margins as they converge, with bounds-clamped sliders that steer parameters mid-run. Rejected steers are shown, never silently applied.
- **10 generators, one line each to extend.** phyllotaxis, gyroid, quasicrystal, attractor, harmonograph, flowfield, metaballs, turbulence, rings, moire. Field generators are one expression plus a criterion; `rings` and `moire` are each one line of algebra.
- **A compositor.** `POST /compose` layers multiple organs into one world under a shared composition criterion, with OKLab/OKLCh perceptual palettes across layers.
- **Motion as a first-class axis.** Every animatable world carries a Timeline with a witnessed verdict that the loop is seamless at the wrap point and stays legible across the period.
- **Interactive sessions.** Create a session over HTTP, inject parameter changes, and get the updated render program back each step. An optional bridge to a native C++ renderer reports honestly when the binary is not built.
- **Zero third-party dependencies.** The core engine is Python stdlib only. No pip install is needed to run it from a checkout.

## Try it

No install required from a clone:

```bash
python -m studio_engine 7 gyroid
```

Expected output (ids vary with the novelty corpus):

```
world e97b2c91d927bcaa | 'Gyroid #7'
  steps=7 converged=False final_score=0.0649
  render=glsl-fragment expr_sha=8a94af6a2eba5cb6
  timeline period=0.707566 continuity=verified
  palette=['#7375cb', '#8e7fd8', ...]
  wrote studio-out/world-7.json (+ svg preview + render program)
```

Or install the package, which adds a `studio-engine` command that starts the API server:

```bash
python -m pip install -e .
studio-engine
```

Start the API directly and open the reference chamber:

```bash
python -m studio_engine.server 8777
```

Then open `handoff/reference-chamber.html` in a browser. It compiles the shipped GLSL live, runs point recipes, stacks composites, and plays the synth graph. For live convergence plots and parameter steering, open `handoff/watch-it-think.html` instead.

## Worked example: from seed to PNG frames

```bash
python -m studio_engine --render-frames 7 gyroid
```

This runs the full loop, then rasterizes the emitted render program headlessly:

```
  rendered 8 PNG frame(s) -> studio-out/frames-7/ (+ frames.json)
```

`studio-out/` now holds the world JSON, an SVG preview, the GLSL render program as text, eight PNG frames sweeping the loop period, and a `frames.json` manifest binding each frame's sha256 to the program's `expr_sha256`. Before rendering, the rasterizer reconstructs the expression from the shipped AST, re-hashes it, and refuses to render on a hash mismatch. Open the PNGs in any viewer; the frames tile seamlessly across the period because the timeline verdict says they do.

## HTTP API

`python -m studio_engine.server [port]` serves on 127.0.0.1 (default port 8777, CORS open):

| Route | What it does |
|---|---|
| `POST /simulate` | run the loop, return a World |
| `GET /simulate/stream` | SSE: per-step events, then the world |
| `POST /compose` | layered composite World |
| `GET /generators`, `/library`, `/gallery` | discovery: generators, organs, pre-built scenes |
| `GET /scene/{id}`, `/scene/{id}/program`, `/scene/{id}/filmstrip` | cached worlds, drop-in render programs, per-step replay |
| `GET /audio/{id}.wav` | baked sonification |
| `POST /session`, `/session/{id}/inject`, `/session/{id}/render` | interactive steering and re-render |
| `POST /native/render` | direct native render bridge (reports honestly if the binary is absent) |

The `handoff/` directory is the frontend integration package: [INTEGRATION.md](handoff/INTEGRATION.md), `types.ts`, `openapi.json`, `ENDPOINTS.md`, examples, and both runnable chambers.

## Generators

| Generator | Channel | Criterion (it did not author) |
|---|---|---|
| `phyllotaxis` | points | golden-angle packing |
| `gyroid` | field | clean tiling (integer frequency) |
| `quasicrystal` | field | 5-fold aperiodic order |
| `attractor`, `harmonograph` | points | balance / coverage / complexity |
| `flowfield`, `metaballs`, `turbulence`, `rings`, `moire` | field | contrast / complexity |

Each entry in the registry is a declarative binding: parameter seed and bounds, criteria axes, a preview render, and a strand expression (fields) or a point recipe (points). Adding a generator means writing one expression.

## The strand substrate

The shader the browser compiles is not hand-written. The engine holds each field as a frozen AST, emits the GLSL `field()` body from it, and proves the round trip GPU-free: emit GLSL, parse it back, and check that the reparsed AST eval-matches the original to 1e-6 across every generator. The same AST is sampled on CPU to compute the features the criteria judge, and swept over `t` to build the motion timeline. One source of truth, four consumers.

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
  certify.py              external structural-fitness oracle (coherence-membrane)
  session.py              interactive steering              server.py   the HTTP API
  organs/                 generators, OKLab palettes, sonify, raster
handoff/                  frontend package: INTEGRATION.md, types.ts, openapi.json,
                          reference-chamber.html, watch-it-think.html, examples/
showcase/                 static showcase with its own fixtures and Node tests
```

## Why it matters

Generated art is usually a dead end: pixels with no structure a person or a later program can inspect. Studio Engine keeps the shader program, sound graph, motion timeline, criteria, and receipt together, so a generated world can be re-rendered, steered, and checked instead of admired once and lost.

`(seed, generator, scheme)` determines a world for a fixed novelty corpus: same input, same id and sha256s. Every world carries its full refine trajectory, the criteria it was judged against, and a receipt whose artifact hashes cover the JSON, the audio, and any rendered frames, so an experience can be replayed and re-checked later.

## Every number, and where it comes from

![Twelve rows covering every number a world reports and where it comes from. Ten generators ship: phyllotaxis, gyroid, quasicrystal, attractor, harmonograph, flowfield, metaballs, turbulence, rings and moire. Seven criteria axes are available, three judging a parameter against a constant the engine did not author and four judging measured features of the output. Cohesion is the harmonic mean of the axes, so one weak axis pulls the whole score down instead of averaging itself away. Convergence needs cohesion at or above the target and every single axis at or above the floor, and either condition alone is not enough. The loop caps at sixteen steps by default, stopping earlier on convergence or when the step size shrinks past two hundredths of a parameter range. That step size starts at a third of each range and multiplies by just over a half whenever a full pass fails to improve. Measurement runs over a twenty by twenty grid, four hundred cells reduced to coverage, centroid offset, contrast, entropy and hue. Novelty is nearest-neighbour distance in that five-feature unit cube over its diagonal, so a first of its kind scores one, and the corpus grows with every world it grounds. The palette is six OKLCh swatches at fixed chroma with lightness ramped across a fixed span and hue spread chosen by the scheme. The algebra is twelve operations over six variables with no control flow and no state, so a shader and a software rasterizer derive from one frozen tree. The accented row is the external verdict, which comes from an independent oracle with its own tolerance and reads unverifiable when that oracle is not installed rather than passing itself. The last row is rendered frames: a deterministic strip of eight across the loop period, or a single still, each frame's own sha256 folded into the receipt.](docs/art/engine-table.svg)

## Scope and maturity

This is a 0.2.0 engine, not a finished product. It emits render programs and evidence packets; browsers, GPUs, and audio hosts realize them. The immersive chamber is the frontend's build, from `handoff/`. The dependency-free native GPU renderer is a separate project that this engine bridges to optionally. APIs may still move before 1.0.

## Docs and related projects

- [USAGE.md](USAGE.md): the full local workflow, including the showcase.
- [docs/INTRODUCTION.md](docs/INTRODUCTION.md): concepts and a first-ten-minutes walkthrough.
- [handoff/INTEGRATION.md](handoff/INTEGRATION.md): build a frontend against the API.
- [docs/design/SUBSTRATE-MAP.md](docs/design/SUBSTRATE-MAP.md): the strand substrate design.
- Peers: [forum](https://github.com/HarperZ9/forum) (multi-agent orchestration), [accountable-surface](https://github.com/HarperZ9/accountable-surface) (live perceive/gate/actuate surface).

## For developers

```bash
python -m pip install -e .
python -m unittest discover -s tests        # 169 tests
node --test showcase/tests/*.test.mjs
python test_forward_delivery_contract.py
```

See [AGENTS.md](AGENTS.md) for the repo operating boundary and [CHANGELOG.md](CHANGELOG.md) for delivery history.

## License

AGPL-3.0-or-later, dual-license ready: the author retains copyright and commercial licenses are available.

**Zain Dana Harper**, small tools with explicit edges. Built with Claude Code; reviewed, tested, owned.

## What this believes

This tool is one lane of a family that holds a single belief steady across
every surface: knowledge open to anyone who can attain the means; acceptance
decided by external checks, never reputation; every result re-runnable;
honest nulls first-class; ownership earned by comprehension; learning woven
into the work. The full text lives in [CREDO.md](CREDO.md).
The long form of this belief: [The Unbundling](https://github.com/HarperZ9/flywheel/blob/fix/release-model-identity/docs/essays/2026-07-13-the-unbundling.md).

---

**[Zentropy Labs](https://github.com/ZentropyLabs-ai)** · order out of entropy. An independent lab building evidence-first tools that leave a re-checkable artifact behind. Built by Zain Dana Harper in Seattle. The full workbench is at [Project Telos](https://harperz9.github.io).
