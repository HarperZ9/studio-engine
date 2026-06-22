# studio-engine — frontend integration guide

A package for the frontend dev/agent to build the **experience chamber** against. The backend
is zero-dependency Python (stdlib only). You build the immersive visual-auditory room; the
engine is its honest, deterministic source — every world is a *witnessed creative act*.

## 1. Run the backend (zero install)

```bash
cd studio-engine
python -m studio_engine.server 8777        # http://127.0.0.1:8777  (CORS open: *)
```
No pip install, no deps. It pre-builds the gallery on start. (Demo a world to disk without
the server: `python -m studio_engine 7`.)

## 2. The mental model (read this once)

Every response is a **`World`** (schema `studio-engine/2`) — the result of a loop:
**perceive → generate → critique → refine → witness**. The engine generates art, judges it
against a criterion it did *not* author, refines toward "correct," and records the whole path.
A world carries three things the chamber shows, and — this is the change in v2 — **the visual half
is now a self-describing program you run directly, not prose to re-derive**:

1. **Visuals** — `world.layers[]`. Pick the layer with **`role: "render"`**; its
   **`render_program`** is a drop-in renderer (a complete WebGL1 fragment shader, or a point
   recipe). You compile/run it as-is — see §3. An optional `layer.preview` (SVG) is a fallback.
2. **Audio** — `world.audio_program` (may be **absent**). One oscillator per partial, a frequency
   automation curve (`pitch_curve`), and an `envelope` — drive Web Audio so the room *sounds* the
   refinement. A baked WAV is also at `GET /audio/{id}.wav`. See §4.
3. **Reasoning** — `world.trajectory.steps[]`. Each step's `score` + per-axis `margins` + verdict
   `tag` (`verified|refuted|unverifiable`) is the cross-examination, replayable — visualize it as
   the "thinking" the chamber surfaces (the two-way telos: the viewer watches the machine reason).

Theme everything from `world.palette` (hex). **Absent vs null:** the wire drops null fields, so
`audio_program`, `timeline`, `composition`, and `layer.preview` may simply be missing — guard for it.

## 2b. The loop is multi-axis (advanced)

Each candidate is judged on several criteria at once — **structural** (golden-angle / clean
frequency / 5-fold order / contrast), **aesthetic** (balance, coverage, complexity), and
**novelty** (distance from everything the engine has made) — combined by **cohesion** (harmonic
mean, so one weak axis tanks the score). On each `step`: `margins` is the per-axis 0..1 map,
`score` is the cohesion, `weakest` is the axis the next step reflected on. **Plot `margins`
across `trajectory.steps`** (radar / parallel-coords that tightens as it refines) — the chamber's
reasoning made visible, the two-way "watch it think."

`trajectory.converged` is `true` only when cohesion ≥ target **and every axis ≥ floor** — CORRECT
on every axis, not good-on-average; an unconverged world is honest best-effort (its `weakest` axis
says why). **Novelty is intentionally path-dependent:** the backend grounds it against a persistent
corpus, so repeated `/simulate` calls don't repeat outputs (novelty drops, the refine diverges) —
a living gallery. Determinism holds for a fixed corpus; disable the corpus for fully reproducible runs.

## 3. Rendering the layer live (the gorgeous path)

Find the render layer and read its program — **no equation reconstruction, ever**:

```ts
const layer = world.layers.find(l => l.role === "render")!;
const prog  = layer.render_program;          // RenderProgram
```

### 3a. `target: "glsl-fragment"` (the fields)
`prog.source` is a **complete WebGL1 (GLSL ES 1.00) fragment shader** — its `field(u,v,t)` body
*is* the engine's verified expression, and it already contains its own helpers + palette ramp.
**Compile `prog.source` verbatim** against a full-screen triangle/quad. Set these uniforms:

- `u_resolution` (`vec2`) — your canvas pixel size.
- `u_value_range` (`vec2`) — `prog.value_range` (i.e. `[lo, hi]`); the shader normalizes the field
  into the palette with it.
- `u_palette` (`vec3[]`) — parse the **hex strings** in `prog.uniforms.u_palette.value`
  (`["#7375cb", …]`, length = `prog.color.stops`, here 6) into linear-ish `vec3`s (`r/255,g/255,b/255`).
  The shader declares `uniform vec3 u_palette[N]` with that exact N — upload all N.
- `u_time` (`float`) — animate within **`[0, prog.domain.period)`** when `prog.domain.animatable`
  is true (start from `prog.uniforms.u_time.default`); otherwise hold it at the default.

That is the whole contract: upload those four uniforms each frame and the field renders. Example
`prog.source` for gyroid (verbatim — compiles as-is):

```glsl
precision highp float;
uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_value_range;
uniform vec3 u_palette[6];
float safediv(float a, float b){ float d = abs(b) > 1e-3 ? b : (b >= 0.0 ? 1e-3 : -1e-3); return a / d; }
float field(float u, float v, float t){ return ((sin((u * 10.0)) * cos((v * 10.0))) + (sin((v * 10.0)) * cos((t * 10.0))) + (sin((t * 10.0)) * cos((u * 10.0)))); }
vec3 ramp(float x){ /* constant-bound loop over u_palette */ }
void main(){
  vec2 uv = (gl_FragCoord.xy / u_resolution) * 2.0 - 1.0;
  float val = field(uv.x, uv.y, u_time);
  float n = (val - u_value_range.x) / max(1e-6, (u_value_range.y - u_value_range.x));
  gl_FragColor = vec4(ramp(n), 1.0);
}
```

### 3b. `target: "point-recipe"` (the point clouds)
`prog.recipe.mode` tells you how to generate the points; color each point by its index across the
palette (`prog.uniforms.u_palette.value`, `color_by: "index"`). Draw as canvas dots or WebGL points.

- **`spiral`** `{angle_deg, scale, count}` — for `i` in `0..count`: `r = scale·√i`,
  `θ = i·angle_deg` (degrees), `x = r·cos θ`, `y = r·sin θ`. (phyllotaxis)
- **`iterated`** `{update_x, update_y, init:[x,y], transient, count}` — start at `init`, iterate the
  map `x' = update_x(x,y)`, `y' = update_y(x,y)` (the values are GLSL-ish expression strings over
  `x,y` — evaluate them), discard the first `transient` points, then plot `count`. (attractor)
- **`parametric`** `{x, y, t_max, count}` — sample `t` uniformly over `[0, t_max]` `count` times and
  plot `(x(t), y(t))` (the `x`/`y` values are expression strings over `t`). (harmonograph)

If you don't (yet) have a renderer for a layer, fall back to `layer.preview` (SVG markup), which is
present on single-organ worlds.

## 4. Audio (`world.audio_program`)

When present, build an additive synth: one `OscillatorNode` per entry in `oscillators`
(`{harmonic, gain, phase}`) at `base_freq · harmonic`, summed through a gain set by `gain`.
Automate frequency along **`pitch_curve`** (one target per refine step — the pitch tracks the
convergence) and shape amplitude with **`envelope`**. `wav_url` (`/audio/{id}.wav`) is the same
sonification baked to a WAV for download/preview.

## 5. Composites (`POST /compose`)

`POST /compose {seed, organs:[...], scheme}` returns a multi-layer `World`: several render programs
stacked into one room. Render each layer as in §3, **sorted ascending by `layer.z`** (fields sit
behind, points in front), compositing with `layer.blend` (`normal | add | screen | multiply`).
`world.composition` is a `Verdict` scoring how the layers cohere (palette harmony, depth
complementarity, contrast balance) — surface it so the *combination* is accountable too.

## 6. Motion is witnessed (`world.timeline`)

For animatable fields, `world.timeline` carries the loop `period`, the animation `channels`
(e.g. `u_time` from `0` → `period`), and two grounding verdicts: **`continuity`** (no pop at the
loop seam) and **`on_criterion`** (the field stays legible across the whole loop). Animate `u_time`
within `[0, period)`; show those verdicts so the chamber can say *the motion is witnessed*, not
improvised. Absent when the visual isn't animatable (e.g. point recipes).

## 7. Minimal consume (vanilla fetch)

```ts
const API = "http://127.0.0.1:8777";
const gallery = (await (await fetch(`${API}/gallery`)).json()).scenes;        // GallerySummary[]
const world = await (await fetch(`${API}/scene/${gallery[0].id}`)).json();    // World

const layer = world.layers.find(l => l.role === "render");
const prog  = layer.render_program;                                           // RenderProgram
const palette = prog.uniforms.u_palette.value;                               // hex string[]
if (prog.target === "glsl-fragment") {
  // compile prog.source VERBATIM; set u_resolution, u_value_range=prog.value_range,
  // u_palette (parsed hex -> vec3[]), animate u_time in [0, prog.domain.period)
} else {
  // run prog.recipe (spiral|iterated|parametric); color by index across palette
}
const audio = world.audio_program; // may be absent — guard before building oscillators

// POST a fresh one:
const fresh = await (await fetch(`${API}/simulate`, {
  method: "POST", headers: {"Content-Type":"application/json"},
  body: JSON.stringify({ seed: 99, generator: "quasicrystal", scheme: "wide" }),
})).json();                                                                   // World
// Or stack several: POST /compose { seed, organs:["gyroid","phyllotaxis"] } -> World
```

See `reference-chamber.html` for a runnable single-file consumer. Types in `types.ts`. Machine spec
in `openapi.json`. Live example payloads in `examples/` (`world.gyroid.json`, `world.phyllotaxis.json`,
`world.composite.json`, `program.gyroid.json`).

## 8. Determinism + receipts

`(seed, generator, scheme)` fully determines a world — same input, same `world.id` and `expr_sha256`s.
Show `world.receipt` (seed, organ_ids, artifact_shas, final_score) so the experience is
*accountable*: a viewer can reproduce and re-check what they saw. That honesty is the thesis.

## 9. Honest scope (what this is / isn't)

This is the **generation + verification** engine that *feeds* the chamber — real render programs,
real audio params, real witnessed reasoning. The **dependency-free native GPU renderer** (no
DirectX/driver) is raw's separate telos, not this package. The shaders here are standard WebGL1 you
run in the browser. Build the chamber as the experiential front; the engine guarantees every frame in
it is grounded and reproducible.
