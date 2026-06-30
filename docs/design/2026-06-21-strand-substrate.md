# strand -- a witnessed expression substrate for studio-engine

- **Date:** 2026-06-21
- **Status:** approved (design); spec under review
- **Version target:** studio-engine `0.2.0`, schema `studio-engine/2`
- **Scope:** the engine that *feeds* the chamber. No GPU renderer, no production DSP engine (raw's telos). Zero third-party deps (Python stdlib + the chamber's native Canvas/WebGL/Web-Audio).

---

## 1. Motivation -- one substrate, not four features

studio-engine today emits a witnessed **frame**: one generator, one static SVG/params blob, a fixed
additive-sine audio recipe, single-axis-per-generator reasoning. The "gorgeous path" asks the
frontend to *re-derive* each field's shader from prose -- so the chamber's pixels are a
re-implementation, not the math the engine verified. Motion is improvised. Scenes are flat. The
audio is thin. And the contract already drifted (`types.ts` lists 3 of 8 generators; the gyroid
*preview* samples a different field than the *verified* one).

The expansion is **not** four bolted-on systems. It is **one primitive** -- a tiny closed-form
**expression algebra (`strand`)** -- from which the engine derives every rendering, in every sense,
composed in depth and choreographed in time, each piece carrying a re-checkable proof. This is the
single-thread/reconcile thesis made into a buildable artifact:

> One verified expression, woven into every sense, composed in depth, choreographed in time, and
> re-checkable by anyone.

Every organ becomes an `(expr, criterion)` binding. Visual and audio organs become the *same shape*.
The four chosen pillars fall out of the one primitive:

| Pillar | Is just… |
|---|---|
| Render-IR (eye) | `expr → GLSL` backend |
| Audio-IR (ear) | a self-describing **synth-graph** program (partials + pitch curve + envelope), grounded against the baked WAV |
| Compositor | a composition algebra over exprs (blend in space, layer in depth) + a composition criterion |
| Temporal | `t` as a first-class var + a continuity criterion; a timeline = exprs over `t` |
| Interactive | the session steers the live `expr`-graph, not just scalars |

The `Scene` graduates to a **`World`**: a graph of witnessed `(expr, criterion)` bindings across
eye / ear / space / time, emitted as portable, hashable, reproducible data.

---

## 2. The `strand` algebra

A frozen, hashable AST. One node type; a small op set; pure functions over typed channels.

### 2.1 Node

```
Expr = (op: str, args: tuple[Expr | float | str, ...])
```

- **Leaves:** `var(name)` with `name ∈ {u, v, t, x, y, i}`; `const(value: float)`.
- **Unary:** `sin, cos, exp, abs, neg, sqrt`.
- **Binary / variadic:** `add, sub, mul, div` (`add`/`mul` accept ≥2 args for clean sums/products).

That op set spans every shipped generator (proven in §3). No control flow, no state -- pure
closed form. Parametric structure (a sum whose term-count depends on a param) is **unrolled at emit
time**, because params are already converged when a `World` is built.

### 2.2 Channels

The same `Expr` type, three channel conventions:

- **`field`** -- `f(u, v, t) → scalar`, `u,v ∈ [-1,1]`, `t` = loop time. Backends: GLSL, Python-eval, SVG-sample.
- **`points`** -- a recipe `{mode, exprs…, count, color_by}` where coordinate exprs range over `x,y` (state) and `i`/`t` (index/sample). Backends: JS recipe (frontend), Python-eval (engine points + features).
- **`audio`** -- a **synth-graph spec**, *not* the closed-form AST. The baked WAV uses phase-integrated frequency sweeps (continuous phase, no clicks), so it is not a pure `Σ sin(2πft)`. The program carries `{partials[], base_freq, pitch_curve, envelope}` derived from `sonify` -- the *same source* that bakes the WAV. The Web-Audio backend instantiates oscillators per partial + automates frequency along `pitch_curve`. Grounded against the WAV by shared source (§2.4), not by AST round-trip.

### 2.3 Operations on the algebra

- `eval(expr, env: dict) -> float` -- reference evaluator (Python `math`).
- `sha(expr) -> str` -- canonical hash (stable repr → sha256[:16]); receipted.
- `emit_glsl(expr) -> str` -- fragment-expression source.
- `parse_glsl(src) -> Expr` -- recursive-descent over the emitted subset (for the proof; not user input).
- `emit_webaudio(audio_spec) -> dict` -- `sonify` params → `{oscillators:[{harmonic,gain,phase}], base_freq, pitch_curve, envelope}` (audio channel only; raises on non-additive input).
- `eval_samples(expr, grid) -> list[float]` -- vectorized sampling for features + tests.

### 2.4 The grounding proof (what makes it a substrate)

**Success criterion (GPU-free, the keystone test):** for every organ's expr,

```
eval(expr) == eval(parse_glsl(emit_glsl(expr)))         # eye backend is the verified math
emit_webaudio(spec).params ≡ wav.synthesis_params       # ear backend == baked artifact (shared sonify source)
features(engine)  == features(sample(shipped_program.expr))  # what's judged == what's shipped
```

to ≤ 1e-6 across a sample grid. The round-trip *is* the grounding: it proves the emitted program
**is** the witnessed expression on CPU. **Honest bound:** GPU/driver float precision and Web-Audio
hardware variance are out of scope (raw's telos); we prove identity of the *program*, not of the
silicon.

---

## 3. The eight generators as exprs (de-risking table)

`f`, `s`, `w`, etc. are the converged param values, inlined as `const` at emit. `rad = π/180`.

| Generator | Channel | Expression | Animate (`t`) | Value range |
|---|---|---|---|---|
| **gyroid** | field | `sin(u·f)·cos(v·f) + sin(v·f)·cos(t·f) + sin(t·f)·cos(u·f)` | z-slice → `t` | ~[-3,3] |
| **quasicrystal** | field | `Σ_{k<w} cos( cos(2πk/w)·u·s + sin(2πk/w)·v·s + t )` (unroll k) | phase `+t` | ~[-w,w] |
| **flowfield** | field | `sin(s·u + w·sin(s·v) + t) · cos(s·v + w·cos(s·u) + t)` | drift `+t` | [-1,1] |
| **turbulence** | field | `(Σ_{o<oct} g^o · sin(f₀2^o·u + sin(f₀2^o·v) + t) · cos(f₀2^o·v)) / Σg^o` (unroll o) | evolve `+t` | [-1,1] |
| **metaballs** | field | `Σ_balls (r²/((u-cx)² + (v-cy)² + ε)) · falloff` (balls baked at emit) | v1 **not** animatable | engine-sampled |
| **phyllotaxis** | points | spiral: `x=scale·√i·cos(i·angle·rad)`, `y=…sin…`; color_by=index | param drift (deferred) | -- |
| **attractor** | points | iterated: `x'=sin(a·y)−cos(b·x)`, `y'=sin(c·x)−cos(d·y)`; init (0.1,0.1), transient 20 | param drift (deferred) | -- |
| **harmonograph** | points | parametric over τ∈[0,T]: damped Lissajous (per organ); color_by=index | -- | -- |

Canonicalization note: today's gyroid/quasicrystal *preview SVG* uses a different field (`z=0`,
domain `[0,1]·2π·freq`) than the *verified* features lambda (`z=param`, domain `[-1,1]`). The IR
adopts the **verified** field as canonical and regenerates the preview from it -- killing the drift.
This changes gallery `sha256`s (acceptable: pre-handoff, schema bumped).

---

## 4. The `World` contract (schema `studio-engine/2`)

New/changed dataclasses (`model.py`), mirrored in `types.ts` + `openapi.json`:

```
RenderProgram:                      # one visual layer's drop-in render
  target: "glsl-fragment" | "point-recipe"
  generator: str
  source: str                       # GLSL fragment (glsl-fragment); "" for recipe
  recipe: dict                      # {mode, exprs, count, color_by} (point-recipe); {} for glsl
  uniforms: dict                    # u_time, u_resolution, u_palette[], u_value_range
  domain: {u:[lo,hi], v:[lo,hi], t:[0,period], animatable: bool, period: float}
  value_range: [float, float]       # engine-sampled, for coloring that matches the witnessed range
  color: {mode:"ramp", stops:int}
  expr_sha256: str                  # receipted

AudioProgram:                       # the ear's drop-in synth graph
  oscillators: [{harmonic:int, freq:float, gain:float, phase:float}]
  envelope: {attack, release, curve}
  pitch_steps: [float]              # per refine step (the trajectory, audible)
  expr_sha256: str
  wav_url: str                      # GET /audio/{id}.wav fallback

Layer:                              # a station in the composed room
  organ_id, title, role, z, blend   # blend: "normal"|"add"|"screen"|"multiply"
  render_program: RenderProgram

Timeline:                           # the witnessed choreography
  period: float
  channels: [{layer_id|"palette", kind:"phase"|"keyframe", ...}]
  continuity: Verdict               # bounded frame-to-frame delta
  on_criterion: Verdict             # stays in-band across the period

World:                              # supersedes Scene (single-organ = 1 visual layer)
  id, title
  layers: [Layer]                   # visual layers, depth-ordered
  audio_program: AudioProgram | None
  timeline: Timeline | None
  trajectory: Trajectory            # unchanged (the refine reasoning)
  composition: Verdict | None       # palette harmony + depth complementarity
  receipt: Receipt                  # + layer expr_sha256s, composition score
  palette: [str]
  schema_version: "studio-engine/2"
```

Back-compat: `Scene` is retained as the single-layer projection of a `World` for any existing
consumer; new consumers read `World`. `GeneratorId` widened 3 → 8.

---

## 5. Composition algebra + criterion

`organs/compose.py`. A composite `World` layers 2--3 organs that *cohere*:

- **palette harmony** -- layers share/relate hue (analogous or complementary), not clash.
- **depth complementarity** -- layers occupy *different* coverage bands (a dense field backdrop
  behind a sparse point system), so they don't fully occlude -- measured from each layer's features.
- **contrast balance** -- combined contrast in a legible band.

`compose(seed, organ_set, scheme) -> World`: builds each layer's program, scores the set with the
composition criterion, assigns `z`/`blend`, emits one `Verdict`. Cohesion (harmonic mean) over the
composition axes -- a composite is itself `(expr-graph, composition-criterion)`.

---

## 6. Temporal choreography + continuity criterion

`temporal.py`. For each animatable field layer, sample its expr across `t ∈ [0, period]` at K steps:

- **continuity** -- `max |frame_{k+1} − frame_k|` (mean over the grid) below a bound → no popping.
- **on-criterion** -- per-frame features stay within the layer's criterion band across the loop.

Emit a `Timeline {period, continuity: Verdict, on_criterion: Verdict}`. `period` per generator
(e.g. gyroid `2π/f`) so the chamber loops seamlessly. Metaballs honestly `animatable:false` in v1.
**Non-goal v1:** full param-keyframe choreography (noted fast-follow).

---

## 7. Interactive + breadth

- **session.py**: `inject` targets a layer's expr param; new `compose` (add/remove a layer) and
  `animate` (set period) actions; `explain` covers composition + temporal axes.
- **breadth**: +2 algebra-native field generators (`rings`: `sin(√(u²+v²)·f + t)`; `moire`: product
  of two rotated gratings) and +criteria axes (`symmetry`, general `palette_harmony`). Kept light.

---

## 8. Module layout (zero-dep; files < 300 lines, functions < 50)

```
studio_engine/strand/
  __init__.py
  expr.py        # Expr type, constructors, eval, sha, eval_samples        (~180)
  glsl.py        # emit_glsl + parse_glsl (round-trip proof)               (~170)
  webaudio.py    # emit_webaudio + additive match + reconstruct            (~140)
  recipe.py      # point-recipe build + Python eval                         (~120)
studio_engine/organs/
  *.py           # refactor each generator to expose .expr()/.recipe(); svg via sampling
  program.py     # assemble RenderProgram / AudioProgram from strand        (~170)
  compose.py     # composition algebra + criterion                         (~150)
studio_engine/
  temporal.py    # timeline + continuity criterion                         (~120)
  model.py       # World, RenderProgram, AudioProgram, Timeline, Layer
  engine.py      # emit World (layers + audio program + timeline)
  session.py     # extended interactive surface
  server.py      # + GET /scene/{id}/program ; World on /simulate, /scene
handoff/         # types.ts, openapi.json, ENDPOINTS.md, INTEGRATION.md, examples/, reference-chamber.html
tests/           # see §9
```

---

## 9. Test plan (explicit, meaningful success criteria)

Keep all existing 56 green (update where shapes changed). Add:

- **test_strand_expr** -- eval of known inputs → known outputs; sha stability; var-env coverage.
- **test_strand_glsl** -- **round-trip**: `parse(emit(expr))` eval == `eval(expr)` over a 12×12 grid at `t ∈ {0, period/2}`, |Δ| ≤ 1e-6, **for all field + point-coord exprs**. Emitted GLSL: balanced parens, only allowed idents/funcs.
- **test_strand_webaudio** -- emitted graph's partial weights + base_freq + pitch_steps + envelope == the baked WAV's synthesis params (shared `sonify` source), ≤1e-6; `emit_webaudio` raises on non-additive input.
- **test_program** -- engine features == features from sampling the shipped `RenderProgram.expr` (every field); first 50 recipe points == engine points (≤1e-9); `value_range` == engine sampling.
- **test_compose** -- composition criterion scores a known-harmonious pair > a known-clashing pair; `World` has ≥1 layer; layers carry distinct `z`.
- **test_temporal** -- animatable fields pass continuity + on-criterion across the period; metaballs `animatable:false`.
- **test_world_contract** -- all 8 generators in types/openapi; `schema_version == "studio-engine/2"`; `World` JSON round-trips; `Scene` projection still valid.

---

## 10. Reference chamber (the performable proof)

`handoff/reference-chamber.html` upgraded to a single-file proof that the substrate *performs*:

1. compiles the shipped **GLSL** in a WebGL canvas with `u_time` animating (the eye, grounded);
2. instantiates the shipped **Web-Audio graph** (the ear, grounded);
3. renders a **2-layer composite** (field backdrop + point system, blended by `z`/`blend`);
4. plots the **trajectory** + **timeline** verdicts (the reasoning + the witnessed motion);
5. shows the **receipt** (re-checkable provenance).

Crib-able, vanilla, zero-build.

---

## 11. Increments (each ships green) + parallelization

1. **strand core** (`expr/glsl/webaudio/recipe` + round-trip proof) -- *spine; built first, by me.*
2. **visual organs → strand** (eye) -- *parallel across agents once core lands.*
3. **audio organ → strand** (ear) -- *parallel with 2.*
4. **compositor** (composition algebra + criterion) -- depends on 2.
5. **temporal** (timeline + continuity) -- depends on 2; parallel with 4.
6. **interactive + breadth** -- after 4/5.
7. **World contract + handoff** (model/types/openapi/docs + reference-chamber) -- integrates all.

Cross-backend verification, the `World` contract, and integration stay with the lead; independent
organ refactors, per-generator tests, and docs fan out to parallel agents.

---

## 12. Non-goals / scope guardrails

- **No GPU renderer / rasterization** -- the engine emits a shader *as data* and verifies it on CPU.
- **No production audio-DSP engine** -- emits an additive synth *graph as data*; bakes a WAV as today.
- **No general shading/synthesis language** -- the algebra covers exactly the closed-form organs; stated as a bound.
- **No param-keyframe choreography in v1** -- one verified `time` channel + stability verdicts.
- **No new third-party dependencies** -- stdlib + the chamber's native browser APIs only.

---

## 13. Risks

- **GLSL parser scope creep** -- mitigate: parser handles *only* the subset `emit_glsl` produces (closed set), not arbitrary GLSL.
- **Audio additive restriction** -- a general expr can't become a finite oscillator graph; the audio channel is *defined* as additive form, enforced by `emit_webaudio` (raises on non-additive).
- **Gallery sha churn** -- expected from canonicalization; covered by bumping schema `/2` pre-handoff.
- **metaballs `div` in GLSL** -- guarded by the same `+ε` the Python field uses; tested in round-trip.

---

## 14. Post-review reconciliation (deltas from the spec as built)

Adversarial whole-branch review surfaced these; recorded here so spec and code agree:

- **`value_range` is sampled across the whole loop**, not a single `t0`, for animatable fields -- so
  the shipped coloring covers every frame the chamber renders as `u_time` sweeps. (`organs/program.py`;
  guarded by `tests/test_program.py::test_value_range_covers_animation`.) Honest claim: every frame's
  *geometry* is the verified expression; the color range brackets the loop.
- **`compose.py` is top-level** (`studio_engine/compose.py`), not `organs/compose.py` as §8 sketched --
  to avoid shadowing the package-level `compose` name; matches `temporal.py`'s placement.
- **The generator table lives in `registry.py`** (extracted from `engine.py`) to keep `engine.py`
  under the 300-line gate; `engine._gens` re-exports `registry.gens`.
- **Breadth criteria descoped:** `symmetry` would duplicate `balance` (both `1 − centroid_offset`), so
  it was not added; `palette_harmony` exists as a *composition* axis in `compose.py`, not a per-artifact
  criterion. The breadth pillar is met by +2 generators (`rings`, `moire`) and the interactive `program()`.
- **Grounding test is non-circular through the shipped artifact:** `test_program.py::
  test_shipped_glsl_body_is_the_engine_field` parses the `field()` body out of the emitted fragment and
  confirms it evaluates to the engine's verified field; `test_organ_exprs.py` checks each field against an
  independent reference. (The earlier same-function-vs-itself checks were removed.)
- **Contract drift is guarded:** `tests/test_world_contract.py` parses `types.ts` + `openapi.json` and
  fails if any generator or the schema version is missing -- the regression guard for the original wound.
