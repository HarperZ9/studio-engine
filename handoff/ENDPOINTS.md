# studio-engine API — endpoint reference

Base: `http://127.0.0.1:8777` · CORS: `*` · responses JSON unless noted. Types: `types.ts`.

| Method | Path | Body | → |
|---|---|---|---|
| GET | `/health` | — | `Health` |
| GET | `/generators` | — | `GeneratorsResponse` |
| GET | `/library` | — | `LibraryResponse` (9 organs) |
| GET | `/gallery` | — | `GalleryResponse` (6 pre-built scenes) |
| POST | `/simulate` | `SimulateRequest` | `Scene` |
| GET | `/scene/{id}` | — | `Scene` \| 404 |
| GET | `/audio/{id}.wav` | — | `audio/wav` binary \| 404 |

### GET /health
```json
{ "ok": true, "service": "studio-engine", "version": "0.1.0" }
```

### GET /generators
```json
{ "generators": ["phyllotaxis", "gyroid", "quasicrystal"] }
```

### GET /library → the resource library
```json
{ "organs": [ { "id": "geometry.phyllotaxis", "name": "Phyllotaxis", "kind": "generator",
  "summary": "...", "params_schema": {"angle_deg":"float"}, "lineage": "..." }, "...(9)" ] }
```

### GET /gallery → pre-built showcase set
```json
{ "scenes": [ { "id": "a48fb47f...", "title": "Phyllotaxis #7", "seed": 7,
  "generator": "phyllotaxis", "score": 0.9925, "converged": true,
  "palette": ["#7375cb","..."], "layers": [{"role":"params","kind":"data","sha256":"..."}],
  "audio": "audio_params" } ] }
```

### POST /simulate → run the loop
Request (all fields optional):
```json
{ "seed": 99, "generator": "quasicrystal", "scheme": "wide" }
```
- `seed`: int (default 0) — determines the rough draft + palette.
- `generator`: `"phyllotaxis" | "gyroid" | "quasicrystal"` (default `phyllotaxis`).
- `scheme`: `"analogous" | "triadic" | "complementary" | "wide"` (default `analogous`).

`200` → a full `Scene`. `400` → `{ "error": "unknown generator 'x'; have [...]" }` or invalid JSON.

### GET /scene/{id}
`id` from a gallery summary or a prior `/simulate`. Cached for the server's lifetime. `404` if unknown.

### GET /audio/{id}.wav
The baked WAV sonification of scene `{id}` (`Content-Type: audio/wav`). Or synthesize live in the
browser from `scene.audio` (`audio_params`). `404` if the scene isn't cached.

**Errors** are `{ "error": "...", "path"?: "..." }` with HTTP `400`/`404`.
**Determinism:** identical `(seed, generator, scheme)` → identical `scene.id` and artifact `sha256`s.
