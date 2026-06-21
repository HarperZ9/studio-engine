# studio-engine — frontend integration guide

A package for the frontend dev/agent to build the **experience chamber** against. The backend
is zero-dependency Python (stdlib only). You build the immersive visual-auditory room; the
engine is its honest, deterministic source — every scene is a *witnessed creative act*.

## 1. Run the backend (zero install)

```bash
cd studio-engine
python -m studio_engine.server 8777        # http://127.0.0.1:8777  (CORS open: *)
```
No pip install, no deps. It pre-builds a 6-scene gallery on start. (Demo a scene to disk without
the server: `python -m studio_engine 7`.)

## 2. The mental model (read this once)

Every `Scene` is the result of a loop: **perceive → generate → critique → refine → witness**.
The engine generates art, judges it against a criterion it did *not* author, refines toward
"correct," and records the whole path. A scene therefore carries three things the chamber shows:

1. **Visuals** — `scene.layers[]`. The **`params` layer (`role:"params"`, `z:-1`) is the one you
   render LIVE** (parse `artifact.content` as JSON → `RenderParams`): draw the generator natively
   (canvas/WebGL) for smooth, gorgeous, resolution-independent output. The `geometry` (SVG) and
   `raster` (PNG) layers are previews/fallbacks if you don't render live.
2. **Audio** — `scene.audio` (`kind:"audio_params"`). `JSON.parse(content)` → `AudioParams`; drive
   Web Audio (additive oscillators) so the room *sounds* the refinement. A baked WAV is also at
   `GET /audio/{id}.wav` for download/preview.
3. **Reasoning** — `scene.trajectory.steps[]`. Each step's `score` + `verdict.tag`
   (`verified|refuted|unverifiable`) is the cross-examination, replayable — visualize it as the
   "thinking" the chamber surfaces (the two-way telos: the viewer watches the machine reason).

Theme everything from `scene.palette` (hex).

## 2b. The loop is multi-axis (advanced)

Each candidate is judged on several criteria at once — **structural** (golden-angle / clean
frequency / 5-fold order), **aesthetic** (balance, coverage, contrast, complexity), and
**novelty** (distance from everything the engine has made) — combined by **cohesion** (harmonic
mean, so one weak axis tanks the score). On each `step`: `margins` is the per-axis 0..1 map,
`score` is the cohesion, `weakest` is the axis the next step reflected on. **Plot `margins`
across `trajectory.steps`** (radar / parallel-coords that tightens as it refines) — the chamber's
reasoning made visible, the two-way "watch it think."

`trajectory.converged` is `true` only when cohesion ≥ target **and every axis ≥ floor** — CORRECT
on every axis, not good-on-average; an unconverged scene is honest best-effort (its `weakest` axis
says why). **Novelty is intentionally path-dependent:** the backend grounds it against a persistent
corpus, so repeated `/simulate` calls don't repeat outputs (novelty drops, the refine diverges) —
a living gallery. Determinism holds for a fixed corpus; disable the corpus for fully reproducible runs.

## 3. Rendering the `params` layer live (the gorgeous path)

`RenderParams.generator` tells you which to draw; the parameter is the converged value:

- **phyllotaxis** (`angle_deg`): points at `r = c·√i`, `θ = i·angle_deg`. Draw N dots, color by
  `i` across `palette`. Canvas or instanced WebGL points.
- **gyroid** (`freq`): a WebGL fragment shader of `sin(x)cos(y)+sin(y)cos(z)+sin(z)cos(x)` (z as
  time → it breathes); map the field to `palette`. This is where the chamber gets mind-blowing.
- **quasicrystal** (`waves`): sum `waves` plane waves at angles `2πk/waves` in a fragment shader;
  threshold/var to `palette`. Animate the phase → living interference.

Fall back to the SVG/PNG layers where you don't (yet) have a shader.

## 4. Minimal consume (vanilla fetch)

```ts
const API = "http://127.0.0.1:8777";
const gallery = (await (await fetch(`${API}/gallery`)).json()).scenes;        // GallerySummary[]
const scene = await (await fetch(`${API}/scene/${gallery[0].id}`)).json();    // Scene
const params = JSON.parse(scene.layers.find(l => l.role === "params")!.artifact.content);
const audio = scene.audio && JSON.parse(scene.audio.content);                 // AudioParams
// POST a fresh one:
const fresh = await (await fetch(`${API}/simulate`, {
  method: "POST", headers: {"Content-Type":"application/json"},
  body: JSON.stringify({ seed: 99, generator: "quasicrystal", scheme: "wide" }),
})).json();                                                                   // Scene
```

See `reference-chamber.html` for a runnable single-file consumer (gallery → render params →
play audio → show the trajectory). Types in `types.ts`. Machine spec in `openapi.json`. Live
example payloads in `examples/`.

## 5. Determinism + receipts

`(seed, generator, scheme)` fully determines a scene — same input, same `scene.id` and `sha256`s.
Show `scene.receipt` (seed, organ_ids, artifact_shas, final_score) so the experience is
*accountable*: a viewer can reproduce and re-check what they saw. That honesty is the thesis.

## 6. Honest scope (what this is / isn't)

This is the **generation + verification** engine that *feeds* the chamber — real visuals, real
audio params, real witnessed reasoning. The **dependency-free native GPU renderer** (no
DirectX/driver) is raw's separate telos, not this package. Build the chamber as the experiential
front; the engine guarantees every frame in it is grounded and reproducible.
