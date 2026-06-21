// studio-engine — frontend contract types.  schema: "studio-engine/1"
// Mirrors studio_engine/model.py exactly. Import these in the chamber frontend.

export type ArtifactKind = "svg" | "png" | "audio_wav" | "audio_params" | "data";
export type VerdictTag = "verified" | "refuted" | "unverifiable";
export type GeneratorId = "phyllotaxis" | "gyroid" | "quasicrystal";
export type Scheme = "analogous" | "triadic" | "complementary" | "wide";
export type Phase = "perceive" | "generate" | "critique" | "refine" | "witness";

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

/** One station/exhibit in the chamber: an artifact + its role + a depth hint. */
export interface SceneLayer {
  organ_id: string;
  title: string;
  artifact: Artifact;
  role: "params" | "geometry" | "raster" | "audio" | "critique-overlay" | string;
  z: number; // render order / depth hint. The `params` layer is z=-1: render this LIVE.
}

/** The full experience the chamber renders. */
export interface Scene {
  id: string;
  title: string;
  layers: SceneLayer[];
  audio: Artifact | null; // kind "audio_params": JSON.parse(content) -> AudioParams
  trajectory: Trajectory;
  receipt: Receipt;
  palette: string[]; // hex swatches — theme the chamber from these
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

/** The `params` layer's artifact.content (kind "data"), JSON-parsed: render this LIVE. */
export interface RenderParams {
  generator: GeneratorId;
  params: Record<string, number>; // the converged vector: {angle,scale,dot} | {freq,z} | {waves,scale}
  palette: string[];
  margins: Record<string, number>; // final per-axis scores (structural + aesthetic + novelty)
  cohesion: number;               // 0..1, harmonic mean of margins
  scores: number[];               // cohesion per refine step (for an animated convergence)
  converged: boolean;
}

/** The `audio` artifact.content (kind "audio_params"), JSON-parsed: drive Web Audio. */
export interface AudioParams {
  base_freq: number;
  partials: { harmonic: number; weight: number }[];
  envelope: Record<string, number>;
  pitch_steps: number[]; // one target pitch per refine step
  scores: number[];
  [k: string]: unknown; // forward-compatible (palette stats, waveform, etc.)
}

// ---- API ----
export interface SimulateRequest {
  seed?: number;            // default 0
  generator?: GeneratorId;  // default "phyllotaxis"
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
  layers: { role: string; organ_id: string; kind: ArtifactKind; sha256: string }[];
  audio: string | null;
}

export interface Health { ok: boolean; service: string; version: string; }
export interface GeneratorsResponse { generators: GeneratorId[]; }
export interface LibraryResponse { organs: OrganInfo[]; }
export interface GalleryResponse { scenes: GallerySummary[]; }

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
//   POST /simulate (SimulateRequest) -> Scene
//   GET  /scene/{id}            -> Scene
//   GET  /scene/{id}/filmstrip  -> Filmstrip
//   GET  /audio/{id}.wav        -> audio/wav (binary)
//   GET  /simulate/stream       -> SSE; 'step' events = Step, 'scene' = Scene, then 'done'
//   POST /session (SimulateRequest)        -> SessionCreated
//   POST /session/{id}/step                -> SessionStepResponse
//   POST /session/{id}/inject {params}     -> SessionStepResponse
//   GET  /session/{id}/explain?axis=       -> Explanation
//   GET  /session/{id}                     -> SessionState
