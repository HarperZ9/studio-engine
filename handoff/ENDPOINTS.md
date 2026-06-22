# studio-engine API — endpoint reference

Base: `http://127.0.0.1:8777` · CORS: `*` · responses JSON unless noted. Types: `types.ts`.

Responses are **`World`** (schema `studio-engine/2`). Null-valued fields
(`audio_program`, `timeline`, `composition`, `layer.preview`) are **omitted** from the JSON.

| Method | Path | Body | → |
|---|---|---|---|
| GET | `/health` | — | `Health` |
| GET | `/generators` | — | `GeneratorsResponse` (10 generators) |
| GET | `/library` | — | `LibraryResponse` (15 organs) |
| GET | `/gallery` | — | `GalleryResponse` (pre-built world summaries) |
| POST | `/simulate` | `SimulateRequest` | `World` |
| POST | `/compose` | `ComposeRequest` | `World` (multi-layer; carries `composition`) |
| GET | `/scene/{id}` | — | `World` \| 404 |
| GET | `/scene/{id}/program` | — | `ProgramResponse` \| 404 |
| GET | `/scene/{id}/filmstrip` | — | `Filmstrip` \| 404 |
| GET | `/audio/{id}.wav` | — | `audio/wav` binary \| 404 |

(`/scene/{id}` is the route for any cached world id — from `/simulate`, `/compose`, or the gallery.)

### GET /health
```json
{ "ok": true, "service": "studio-engine", "version": "0.2.0" }
```

### GET /generators
```json
{ "generators": ["phyllotaxis","gyroid","quasicrystal","attractor","harmonograph",
  "flowfield","metaballs","turbulence","rings","moire"] }
```
Fields (`glsl-fragment`): `gyroid, quasicrystal, flowfield, metaballs, turbulence, rings, moire`.
Points (`point-recipe`): `phyllotaxis, attractor, harmonograph`.

### GET /library → the resource library
```json
{ "organs": [ { "id": "fields.gyroid", "name": "Gyroid field", "kind": "generator",
  "summary": "Gyroid implicit slice.", "params_schema": {"freq":"float","z":"float"},
  "lineage": "sensory-transform-algebra Field" }, "...(15)" ] }
```

### GET /gallery → pre-built showcase set (summaries)
```json
{ "scenes": [ { "id": "1e1312cf...", "title": "Gyroid #7", "seed": 7,
  "generator": "gyroid", "score": 0.8922, "converged": false,
  "palette": ["#7375cb","..."],
  "layers": [{"role":"render","organ_id":"gyroid","z":0,"blend":"normal","target":"glsl-fragment"}],
  "audio": "additive-sine", "animatable": true } ] }
```
`audio` is the world's `audio_program.waveform` (or `null`); `animatable` is true when the world carries a `timeline`. Fetch the full world with `GET /scene/{id}`.

### POST /simulate → run the loop
Request (all fields optional):
```json
{ "seed": 99, "generator": "quasicrystal", "scheme": "wide" }
```
- `seed`: int (default 0) — determines the rough draft + palette.
- `generator`: one of the 10 ids above (default `phyllotaxis`).
- `scheme`: `"analogous" | "triadic" | "complementary" | "wide"` (default `analogous`).

`200` → a full `World`. `400` → `{ "error": "unknown generator 'x'; have [...]" }` or invalid JSON.

### POST /compose → layered composite
Request (all fields optional):
```json
{ "seed": 7, "organs": ["gyroid", "phyllotaxis"], "scheme": "analogous" }
```
- `organs`: generator ids to stack (default `["gyroid","phyllotaxis"]`); the key `organ_set` is also accepted.
- Layers are depth-ordered (fields behind, points in front) over one shared palette and blended
  (`normal` for the first, `screen` for the rest).

`200` → a multi-layer `World` whose `composition` `Verdict` scores how the layers cohere
(palette harmony, depth complementarity, contrast balance). `400` on an unknown generator / bad JSON.

### GET /scene/{id}
`id` from a gallery summary, `/simulate`, or `/compose`. Cached for the server's lifetime. `404` if unknown.

### GET /scene/{id}/program → drop-in render programs
```json
{ "scene_id": "1e1312cf...", "programs": [ { "target": "glsl-fragment", "generator": "gyroid",
  "source": "precision highp float; ...", "uniforms": {...}, "domain": {...},
  "value_range": [-1.41, 1.42], "color": {"mode":"ramp","stops":6}, "expr_sha256": "...", "notes": "..." } ] }
```
One `RenderProgram` per layer — the same programs carried inline on `world.layers[].render_program`,
exposed standalone for clients that only want the renderable math. `404` if the world isn't cached.

### GET /audio/{id}.wav
The baked WAV sonification of world `{id}` (`Content-Type: audio/wav`). Or synthesize live in the
browser from `world.audio_program` (oscillators + `pitch_curve` + `envelope`). `404` if not cached.

**Errors** are `{ "error": "...", "path"?: "..." }` with HTTP `400`/`404`.
**Determinism:** identical `(seed, generator, scheme)` → identical `world.id` and `expr_sha256`s
(for a fixed corpus; novelty is intentionally path-dependent — see INTEGRATION.md §2b).

## Live & interactive (advanced)

| Method | Path | Body | → |
|---|---|---|---|
| GET | `/simulate/stream?seed=&generator=&scheme=` | — | **SSE**: `event: step` ×N, then `event: world`, then `event: done` |
| GET | `/scene/{id}/filmstrip` | — | `{scene_id, generator, palette, frames:[{index,phase,params,margins,score,weakest}]}` |
| POST | `/session` | `{seed,generator,scheme}` | `{session_id, state}` |
| POST | `/session/{id}/step` | — | `{session_id, step, state}` — auto-refine one iteration |
| POST | `/session/{id}/inject` | `{params:{...}}` | `{session_id, step, state}` — operator steers parameters |
| GET | `/session/{id}/explain?axis=` | — | `{axis, score, kind, tag, cohesion, why, all_margins}` |
| GET | `/session/{id}` | — | session `state` (incl. `history` and `program`) |

- **SSE** — consume `/simulate/stream` with `EventSource`. Each `step` event is a `Step` (params +
  margins + cohesion); render the convergence live. The final `world` event carries the full `World`
  (parse it exactly like a `/simulate` response), then a terminal `done` event closes the stream.
- **Filmstrip** — per-step params/margins for replaying/animating a finished world's convergence.
- **Sessions** — the two-way cross-examine: `step` to auto-refine, `inject` to steer a parameter,
  `explain` to ask why an axis scores what it does; `state.history` is the witnessed exchange.
  **`state.program`** is a full `RenderProgram` of the *current steered candidate* — render it live to
  see the world change as you cross-examine (re-fetch after each `step`/`inject`).
