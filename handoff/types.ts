// studio-engine — frontend contract types.  schema: "studio-engine/2"
// Mirrors studio_engine/model.py exactly. Import these in the chamber frontend.
//
// The engine now emits a `World` (schema "studio-engine/2") with self-describing
// render programs — the visual half is data the frontend runs directly (a complete
// WebGL1 fragment shader, or a point recipe), no longer prose to re-derive.
// `Scene`/`SceneLayer` are kept as a legacy projection (World.as_scene()).
//
// JSON note: any field whose value is null is omitted from the wire (a `_clean` step
// drops None). So `audio_program`, `timeline`, `composition`, and `Layer.preview` may
// be ABSENT rather than null. Treat "absent" and "null" the same.

export type ArtifactKind = "svg" | "png" | "audio_wav" | "audio_params" | "data";
export type VerdictTag = "verified" | "refuted" | "unverifiable";
export type GeneratorId =
  | "phyllotaxis" | "gyroid" | "quasicrystal" | "attractor" | "harmonograph"
  | "flowfield" | "metaballs" | "turbulence" | "rings" | "moire";
export type Scheme = "analogous" | "triadic" | "complementary" | "wide";
export type Phase = "perceive" | "generate" | "critique" | "refine" | "witness";
export type RenderTarget = "glsl-fragment" | "point-recipe";
export type BlendMode = "normal" | "add" | "screen" | "multiply";

/** One rendered output. `content` is inline: SVG markup, base64 (png/wav), or a JSON string. */
export interface Artifact {
  kind: ArtifactKind;
  content: string;
  width: number;
  height: number;
  mime: string;
  label: string;
  sha256: string;
}

/** A criterion's judgement on an artifact — the verification half of the loop. */
export interface Verdict {
  criterion: string;
  tag: VerdictTag;
  score: number; // 0..1, higher = better fit
  detail: string;
}

/** A re-checkable coherence-membrane verdict — an EXTERNAL criterion the engine did not author
 *  (the anti-self-grading oracle). Wire shape matches coherence_membrane Certificate.to_dict(). */
export interface Certificate {
  claim: string;
  verdict: VerdictTag;            // "verified" | "refuted" | "unverifiable"
  oracle: string;                 // e.g. "structural-fitness-v1"
  evidence: [string, string][];   // ordered (key, value) pairs
}

/** One iteration of the loop: params tried, per-axis margins, cohesion, the weakest axis. */
export interface Step {
  index: number;
  phase: Phase;
  params: Record<string, number | string>;
  verdicts: Verdict[];        // one per axis (incl. "novelty")
  score: number;              // cohesion = harmonic mean of the margins
  margins: Record<string, number>; // per-axis scores 0..1 — plot these as the convergence
  weakest: string;            // axis the next refine reflected on
  note: string;
}

/** The witnessed path from rough draft to accepted result — replayable reasoning. */
export interface Trajectory {
  steps: Step[];
  accepted_index: number;
  converged: boolean;
}

/** Proof-before-trust: provenance + integrity, re-checkable. */
export interface Receipt {
  scene_id: string;
  seed: number;
  organ_ids: string[];
  artifact_shas: string[];
  final_score: number;
  schema_version: string;
  author: string;
  producer: string;
}

// ---- World: the live contract (schema "studio-engine/2") ----

/** A uniform declaration in a RenderProgram. `value` present where the engine fixed it. */
export interface UniformSpec {
  type: "float" | "vec2" | "vec3" | "vec3[]" | string;
  default?: number;
  value?: unknown; // u_palette -> hex string[]; u_value_range -> [lo, hi]
}

/**
 * A drop-in live render, emitted as data — the eye reads the engine's verified math.
 *
 * `glsl-fragment`: `source` is a COMPLETE WebGL1 (GLSL ES 1.00) fragment shader.
 *   Compile it VERBATIM. The host sets `u_resolution` (vec2), `u_time` (float),
 *   `u_palette` (vec3[]; parse the hex strings in `uniforms.u_palette.value`),
 *   and `u_value_range` (vec2; from `value_range`). Animate `u_time` in [0, domain.period).
 * `point-recipe`: `recipe` reproduces the engine's verified points; run it and color by index.
 */
export interface RenderProgram {
  target: RenderTarget;
  generator: string;
  source: string;                 // complete WebGL1 fragment shader (glsl-fragment only)
  recipe: RenderRecipe | Record<string, never>; // the point recipe (point-recipe only); {} otherwise
  uniforms: Record<string, UniformSpec>;
  domain: {
    u?: [number, number];
    v?: [number, number];
    t?: [number, number];         // [0, period]
    animatable: boolean;
    period?: number;
  };
  value_range: [number, number];  // [lo, hi] the field was sampled over — feeds u_value_range
  color: { mode: "ramp" | "index" | string; stops: number };
  expr_sha256: string;            // receipts the canonical strand expr / recipe
  notes: string;
}

/** A point-recipe (RenderProgram.recipe). One of three modes; color_by is the palette index. */
export type RenderRecipe =
  | { mode: "spiral"; angle_deg: number; scale: number; count: number; color_by: string }
  // update_x/update_y and x/y are GLSL-ish expression strings over the named vars.
  | { mode: "iterated"; update_x: string; update_y: string; init: [number, number];
      transient: number; count: number; color_by: string }
  | { mode: "parametric"; x: string; y: string; t_max: number; count: number; color_by: string };

/** The ear's drop-in synth graph: one oscillator per partial + a frequency-automation curve. */
export interface AudioProgram {
  oscillators: { harmonic: number; gain: number; phase: number }[];
  base_freq: number;
  pitch_curve: number[];          // automate each oscillator's frequency along this
  envelope: Record<string, number>;
  waveform: string;               // e.g. "additive-sine"
  expr_sha256: string;
  wav_url: string;                // baked WAV, e.g. "/audio/{id}.wav"
}

/** The witnessed choreography: a loop period + verdicts that ground the motion. */
export interface Timeline {
  period: number;
  channels: { target: string; kind: string; from: number; to: number }[];
  continuity: Verdict;     // bounded frame-to-frame delta (no popping)
  on_criterion: Verdict;   // stays in-band across the whole loop
}

/** One depth-ordered station in the composed room: a render program + an optional SVG fallback. */
export interface Layer {
  organ_id: string;
  title: string;
  role: string;                   // the live visual layer is role "render"
  z: number;                      // stack ascending; fields tend to sit behind points
  render_program: RenderProgram;
  blend: BlendMode;
  preview?: Artifact;             // ABSENT if none; an SVG fallback when the client can't render live
}

/** The full witnessed experience the chamber renders. Supersedes `Scene`. */
export interface World {
  id: string;
  title: string;
  layers: Layer[];                // pick the one with role "render"; stack by z/blend for composites
  audio_program?: AudioProgram;   // ABSENT if none
  timeline?: Timeline;            // ABSENT for non-animatable visuals (e.g. point recipes)
  trajectory: Trajectory;
  receipt: Receipt;
  palette: string[];              // hex swatches — theme the chamber from these
  composition?: Verdict;          // ABSENT for single-organ worlds; present from /compose
  certificate?: Certificate;      // external structural-fitness verdict (coherence-membrane oracle)
  schema_version: string;         // "studio-engine/2"
}

// ---- legacy projection (schema "studio-engine/1"): kept for back-compat ----

/** LEGACY projection. One station in the older Scene shape (World.as_scene()). Prefer `Layer`. */
export interface SceneLayer {
  organ_id: string;
  title: string;
  artifact: Artifact;
  role: "params" | "geometry" | "raster" | "audio" | "critique-overlay" | string;
  z: number;
}

/** LEGACY projection of a `World` (World.as_scene()). The live endpoints return `World`. */
export interface Scene {
  id: string;
  title: string;
  layers: SceneLayer[];
  audio: Artifact | null;
  trajectory: Trajectory;
  receipt: Receipt;
  palette: string[];
  schema_version: string;
}

/** A resource-library entry (GET /library). */
export interface OrganInfo {
  id: string;
  name: string;
  kind: "generator" | "criterion" | "sonifier" | "compositor";
  summary: string;
  params_schema: Record<string, string>;
  lineage: string;
}

// ---- API ----
export interface SimulateRequest {
  seed?: number;            // default 0
  generator?: GeneratorId;  // default "phyllotaxis"
  scheme?: Scheme;          // default "analogous"
}

export interface ComposeRequest {
  seed?: number;            // default 0
  organs?: GeneratorId[];   // default ["gyroid","phyllotaxis"]; also accepts "organ_set"
  scheme?: Scheme;          // default "analogous"
}

export interface GallerySummary {
  id: string;
  title: string;
  seed: number;
  generator: string;
  score: number;
  converged: boolean;
  palette: string[];
  layers: { role: string; organ_id: string; z: number; blend: BlendMode; target: RenderTarget }[];
  audio: string | null;     // the audio_program waveform, or null
  animatable: boolean;      // true when the world carries a timeline
}

export interface Health { ok: boolean; service: string; version: string; }
export interface GeneratorsResponse { generators: GeneratorId[]; }
export interface LibraryResponse { organs: OrganInfo[]; }
export interface GalleryResponse { scenes: GallerySummary[]; }
/** GET /scene/{id}/program — drop-in render programs, one per layer. */
export interface ProgramResponse { scene_id: string; programs: RenderProgram[]; }

// ---- live + interactive (advanced) ----
export interface SessionEntry {  // one row of the cross-examine history
  index: number; phase: Phase; params: Record<string, number>;
  margins: Record<string, number>; cohesion: number; weakest: string;
  note: string; converged: boolean;
}
export interface SessionState {
  generator: GeneratorId; seed: number;
  params: Record<string, number>; palette: string[];
  margins: Record<string, number>; cohesion: number; weakest: string;
  converged: boolean; steps: number; history: SessionEntry[];
  program: RenderProgram;   // the current steered candidate, ready to render live
}
export interface SessionCreated { session_id: string; state: SessionState; }
export interface SessionStepResponse { session_id: string; step: SessionEntry; state: SessionState; }
export interface Explanation {
  axis: string; score: number; kind: string; tag: VerdictTag;
  cohesion: number; why: string; all_margins: Record<string, number>;
}
export interface FilmstripFrame {
  index: number; phase: Phase; params: Record<string, number>;
  margins: Record<string, number>; score: number; weakest: string;
}
export interface Filmstrip {
  scene_id: string; generator: string; palette: string[]; frames: FilmstripFrame[];
}

// Endpoints:
//   GET  /health                -> Health
//   GET  /generators            -> GeneratorsResponse
//   GET  /library               -> LibraryResponse
//   GET  /gallery               -> GalleryResponse
//   POST /simulate (SimulateRequest) -> World
//   POST /compose  (ComposeRequest)  -> World            (multi-layer; carries `composition`)
//   GET  /scene/{id}            -> World
//   GET  /scene/{id}/program    -> ProgramResponse
//   GET  /scene/{id}/filmstrip  -> Filmstrip
//   GET  /audio/{id}.wav        -> audio/wav (binary)
//   GET  /simulate/stream       -> SSE; 'step' events = Step, 'world' = World, then 'done'
//   POST /session (SimulateRequest)        -> SessionCreated
//   POST /session/{id}/step                -> SessionStepResponse
//   POST /session/{id}/inject {params}     -> SessionStepResponse
//   GET  /session/{id}/explain?axis=       -> Explanation
//   GET  /session/{id}                     -> SessionState (incl. `program`)
