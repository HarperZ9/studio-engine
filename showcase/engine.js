// engine.js -- the engine, in the browser. The shared substrate both witnesses can actuate.
//
// A faithful JS port of studio-engine's generate -> judge -> certify loop, for the three showcase
// generators. The point: a human (param sliders) and the model (a real coordinate-descent refine
// step) can BOTH change the same generated frame and watch a REAL coherence-membrane certificate
// re-derive -- not a mock. Faithfulness is gated by tests/engine.test.mjs: this code must reproduce
// each baked Python World's cohesion and per-axis margins at the same params. The verdict bar is
// imported from verdict.js (single source -- the engine invents no rule of its own).
//
// Ports: studio_engine.engine._features / _entropy / _refine, studio_engine.criteria, and the field
// exprs / point recipe. Stdlib/browser only.
import { structuralFitnessVerdict, ORACLE, DEFAULT_TOLERANCE } from "./verdict.js";

const G = 20;                                  // feature grid resolution (engine._G)
export const GOLDEN_ANGLE = 137.50776405003785;
const TWO_PI = 2 * Math.PI;
const round6 = x => Math.round(x * 1e6) / 1e6;

// ---- substrate: the field exprs (animatable in t) and the point recipe ----
const gyroidAt = (p, t) => (u, v) =>
  Math.sin(u * p.freq) * Math.cos(v * p.freq) +
  Math.sin(v * p.freq) * Math.cos(t * p.freq) +
  Math.sin(t * p.freq) * Math.cos(u * p.freq);

const quasiAt = (p, t) => {
  const w = Math.max(1, Math.round(p.waves)), angs = [];
  for (let k = 0; k < w; k++) angs.push(TWO_PI * k / w);
  return (u, v) => { let a = 0; for (const ang of angs) a += Math.cos(Math.cos(ang) * p.scale * u + Math.sin(ang) * p.scale * v + t); return a; };
};

function phyllotaxisPoints(p, n = 700) {
  const a = p.angle * Math.PI / 180, out = [];
  for (let i = 0; i < n; i++) { const r = p.scale * Math.sqrt(i); out.push([r * Math.cos(i * a), r * Math.sin(i * a), i]); }
  return out;
}

// ---- the generators: axes, substrate kind, bounds, animation period ----
export const GEN = {
  gyroid: { kind: "field", axes: ["clean_freq", "contrast", "complexity"],
    bounds: { freq: [3, 10], z: [0.05, 0.95] }, t0: p => p.z, period: p => TWO_PI / Math.max(1e-6, p.freq),
    field: p => gyroidAt(p, p.z), fieldAt: gyroidAt, glsl: p => gyroidGLSL(p) },
  quasicrystal: { kind: "field", axes: ["fivefold", "contrast", "complexity"],
    bounds: { waves: [3, 9], scale: [4, 14] }, t0: _ => 0, period: _ => TWO_PI,
    field: p => quasiAt(p, 0), fieldAt: quasiAt, glsl: p => quasiGLSL(p) },
  phyllotaxis: { kind: "points", axes: ["golden_angle", "balance", "coverage", "complexity"],
    bounds: { angle: [110, 165], scale: [5, 16] }, points: phyllotaxisPoints },
};

// ---- features (engine._features), measured from the substrate on a G x G grid ----
function entropyOf(counts) {
  const tot = counts.reduce((a, b) => a + b, 0);
  if (tot <= 0) return 0;
  const ps = counts.filter(c => c > 0).map(c => c / tot);
  if (ps.length <= 1) return 0;
  const h = -ps.reduce((a, p) => a + p * Math.log(p), 0);
  return Math.max(0, Math.min(1, h / Math.log(counts.length)));
}

function fieldFeatures(field) {
  const vals = [];
  for (let j = 0; j < G; j++) for (let i = 0; i < G; i++) vals.push(field((i / (G - 1)) * 2 - 1, (j / (G - 1)) * 2 - 1));
  const vmin = Math.min(...vals), vmax = Math.max(...vals), rng = (vmax - vmin) || 1e-9;
  const norm = vals.map(v => (v - vmin) / rng);
  const contrast = Math.min(1, (vmax - vmin) / 4);
  const coverage = norm.filter(v => v > 0.5).length / norm.length;
  let left = 0, right = 0, top = 0, bot = 0;
  for (let j = 0; j < G; j++) for (let i = 0; i < G; i++) {
    const v = norm[j * G + i]; if (i < G / 2) left += v; else right += v; if (j < G / 2) top += v; else bot += v;
  }
  const tot = norm.reduce((a, b) => a + b, 0) || 1e-9;
  const centroid_offset = Math.min(1, (Math.abs(left - right) + Math.abs(top - bot)) / tot);
  const hist = new Array(10).fill(0);
  for (const v of norm) hist[Math.min(9, Math.floor(v * 10))] += 1;
  return { coverage, centroid_offset, contrast, entropy: entropyOf(hist) };
}

function pointFeatures(pts) {
  let maxr = 0; for (const [x, y] of pts) { const r = Math.hypot(x, y); if (r > maxr) maxr = r; } maxr = maxr || 1;
  const cells = new Array(G * G).fill(0); let sx = 0, sy = 0;
  for (const [x, y] of pts) {
    const nx = x / maxr, ny = y / maxr; sx += nx; sy += ny;
    const gx = Math.min(G - 1, Math.max(0, Math.floor((nx + 1) / 2 * G)));
    const gy = Math.min(G - 1, Math.max(0, Math.floor((ny + 1) / 2 * G)));
    cells[gy * G + gx] += 1;
  }
  const n = pts.length || 1;
  const coverage = cells.filter(c => c > 0).length / (G * G);
  const centroid_offset = Math.min(1, Math.hypot(sx / n, sy / n));
  const mean = n / (G * G);
  const variance = cells.reduce((a, c) => a + (c - mean) ** 2, 0) / cells.length;
  const contrast = Math.min(1, (Math.sqrt(variance) / (mean + 1e-9)) / 3);
  return { coverage, centroid_offset, contrast, entropy: entropyOf(cells) };
}

// ---- criteria (studio_engine.criteria): each axis -> [0,1], judged on a property it didn't author ----
function axisScore(axis, f, p) {
  switch (axis) {
    case "golden_angle": { const d = Math.abs((((p.angle ?? GOLDEN_ANGLE) - GOLDEN_ANGLE + 180) % 360) - 180); return Math.max(0, 1 - d / 15); }
    case "clean_freq": { const v = p.freq ?? 6; return Math.max(0, 1 - Math.min(0.5, Math.abs(v - Math.round(v))) / 0.5); }
    case "fivefold": { const w = Math.round(p.waves ?? 5); return Math.max(0, 1 - Math.abs(w - 5) * 0.2); }
    case "balance": return Math.max(0, 1 - (f.centroid_offset ?? 1));
    case "coverage": return f.coverage ?? 0;
    case "contrast": return f.contrast ?? 0;
    case "complexity": { const e = f.entropy ?? 0; return Math.max(0, 1 - Math.abs(e - 0.8) / 0.8); }
    default: return 0;
  }
}

function cohesion(scores) {
  const vals = scores.map(s => Math.max(1e-6, Math.min(1, s)));
  return vals.length ? vals.length / vals.reduce((a, s) => a + 1 / s, 0) : 0;
}

// Evaluate a candidate: measure features, score every axis (+ novelty = 1.0, no corpus loaded),
// return the harmonic-mean cohesion. This is the engine's judgement, reproduced.
export function evaluate(gen, params) {
  const g = GEN[gen];
  const feats = g.kind === "field" ? fieldFeatures(g.field(params)) : pointFeatures(g.points(params));
  const margins = {};
  for (const ax of g.axes) margins[ax] = axisScore(ax, feats, params);
  margins.novelty = 1.0;                       // corpus off -> maximally novel (matches the fixtures)
  return { feats, margins, cohesion: cohesion(Object.values(margins)) };
}

function clampParams(gen, params) {
  const out = { ...params };
  for (const [k, [lo, hi]] of Object.entries(GEN[gen].bounds)) out[k] = Math.max(lo, Math.min(hi, out[k]));
  return out;
}

// The model's actuation: the single bounded param move that most improves cohesion (engine._refine,
// one coordinate-descent step). Returns the move it made so the model can SAY what it did and why.
export function refineStep(gen, params, frac = 0.12) {
  const base = evaluate(gen, params).cohesion;
  let best = params, bestCoh = base, moved = null;
  for (const [k, [lo, hi]] of Object.entries(GEN[gen].bounds)) {
    const delta = (hi - lo) * frac;
    for (const d of [delta, -delta]) {
      const trial = clampParams(gen, { ...params, [k]: params[k] + d });
      const coh = evaluate(gen, trial).cohesion;
      if (coh > bestCoh + 1e-6) { best = trial; bestCoh = coh; moved = { param: k, from: params[k], to: trial[k] }; }
    }
  }
  return { params: best, cohesion: bestCoh, base, improved: bestCoh > base + 1e-6, moved };
}

// ---- certificate (coherence-membrane structural_fitness, via verdict.js -- the single bar) ----
export function certify(coh, tolerance = DEFAULT_TOLERANCE) {
  const deviation = 1 - coh;
  return {
    claim: `structurally fit: deviation ${deviation} <= tolerance ${tolerance}`,
    verdict: structuralFitnessVerdict(deviation, tolerance),
    oracle: ORACLE,
    evidence: [["deviation", String(deviation)], ["tolerance", String(tolerance)]],
  };
}

// ---- GLSL emit (mirrors strand.glsl + program.fragment_source) so render.js can paint live params ----
const GLSL_HELPERS = "float safediv(float a, float b){ float d = abs(b) > 1e-3 ? b : (b >= 0.0 ? 1e-3 : -1e-3); return a / d; }";
const fmtF = x => { const r = String(x); return (r.includes(".") || r.includes("e") || r.includes("E")) ? r : r + ".0"; };

function gyroidGLSL(p) {
  const f = fmtF(p.freq);
  return `((sin((u * ${f})) * cos((v * ${f}))) + (sin((v * ${f})) * cos((t * ${f}))) + (sin((t * ${f})) * cos((u * ${f}))))`;
}
function quasiGLSL(p) {
  const w = Math.max(1, Math.round(p.waves)), terms = [];
  for (let k = 0; k < w; k++) { const a = TWO_PI * k / w; terms.push(`cos(((u * ${fmtF(Math.cos(a) * p.scale)}) + (v * ${fmtF(Math.sin(a) * p.scale)}) + t))`); }
  return "(" + terms.join(" + ") + ")";
}
function fragmentSource(exprSrc, nColors) {
  const n = Math.max(2, nColors);
  return `precision highp float;
uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_value_range;
uniform vec3 u_palette[${n}];
${GLSL_HELPERS}
float field(float u, float v, float t){ return ${exprSrc}; }
vec3 ramp(float x){
  x = clamp(x, 0.0, 1.0);
  float s = x * float(${n} - 1);
  int idx = int(floor(s));
  float f = fract(s);
  vec3 a = u_palette[0];
  vec3 b = u_palette[0];
  for (int k = 0; k < ${n}; k++) {
    if (k == idx) a = u_palette[k];
    if (k == idx + 1) b = u_palette[k];
  }
  return mix(a, b, f);
}
void main(){
  vec2 uv = (gl_FragCoord.xy / u_resolution) * 2.0 - 1.0;
  float val = field(uv.x, uv.y, u_time);
  float n = (val - u_value_range.x) / max(1e-6, (u_value_range.y - u_value_range.x));
  gl_FragColor = vec4(ramp(n), 1.0);
}`;
}

function valueRange(gen, params) {
  const g = GEN[gen];
  if (g.kind !== "field") throw new Error("valueRange: fields only");
  const period = g.period(params), vals = [];
  for (let s = 0; s < 8; s++) {
    const t = g === GEN.gyroid ? period * s / 8 : (gen === "quasicrystal" ? period * s / 8 : 0);
    const f = g.fieldAt(params, gen === "gyroid" ? t : (gen === "quasicrystal" ? t : g.t0(params)));
    for (let j = 0; j < G; j++) for (let i = 0; i < G; i++) vals.push(f((i / (G - 1)) * 2 - 1, (j / (G - 1)) * 2 - 1));
  }
  let lo = Math.min(...vals), hi = Math.max(...vals); if (hi <= lo) hi = lo + 1e-6;
  return [lo, hi];
}

function titleFor(gen, params) {
  const pretty = { gyroid: "Gyroid", quasicrystal: "Quasicrystal", phyllotaxis: "Phyllotaxis" }[gen] || gen;
  const ps = Object.entries(params).map(([k, v]) => `${k} ${typeof v === "number" ? (Number.isInteger(v) ? v : v.toFixed(2)) : v}`).join(", ");
  return `${pretty} · ${ps}`;
}

// Build a full, render-ready World from live params -- same shape render.js + showcase.js consume for a
// baked fixture, carrying a REAL certificate. This is the actuated substrate, witnessed.
export function synthesize(gen, params, palette) {
  const g = GEN[gen], ev = evaluate(gen, params), coh = ev.cohesion;
  let layer, timeline = null;
  if (g.kind === "field") {
    const t0 = g.t0(params), period = g.period(params), [lo, hi] = valueRange(gen, params);
    layer = { organ_id: gen, title: gen, role: "field", z: 0, blend: "normal", render_program: {
      target: "glsl-fragment", generator: gen, source: fragmentSource(g.glsl(params), palette.length),
      uniforms: { u_palette: { type: "vec3[]", value: palette }, u_time: { type: "float", default: round6(t0) } },
      domain: { u: [-1, 1], v: [-1, 1], t: [0, round6(period)], animatable: true, period: round6(period) },
      value_range: [round6(lo), round6(hi)] } };
    timeline = { period: round6(period), channels: [] };
  } else {
    layer = { organ_id: gen, title: gen, role: "geometry", z: 0, blend: "normal", render_program: {
      target: "point-recipe", generator: gen,
      recipe: { mode: "spiral", angle_deg: params.angle, scale: params.scale, count: 700, color_by: "index" },
      uniforms: { u_palette: { type: "vec3[]", value: palette } }, domain: { animatable: false } } };
  }
  return {
    id: "live", title: titleFor(gen, params), layers: [layer], audio_program: null, timeline,
    trajectory: { steps: [{ index: 0, phase: "witness", params: { ...params }, margins: ev.margins,
      score: coh, weakest: "", note: "live re-evaluation" }], accepted_index: 0, converged: false },
    receipt: { scene_id: "live", seed: 0, organ_ids: [gen], artifact_shas: [], final_score: coh },
    palette, certificate: certify(coh),
  };
}
