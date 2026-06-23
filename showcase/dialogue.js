// dialogue.js — the model's voice, grounded. You can talk to it about the frame; it can only say what
// the witnessed structure licenses, and every claim is a number you can re-derive. This is the honest
// core of "talk to the model": not a chatbot improvising, but a witness reporting what it measured —
// its criteria, their margins, the cohesion, and the certificate's own deviation/tolerance. The verdict
// bar comes from verdict.js (single source). Pure + node-testable; the UI in showcase.js renders it.
import { structuralFitnessVerdict } from "./verdict.js";

const fmt = (v, n = 3) => (typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(n)) : String(v));

// What each criterion actually means, in plain words — so "weakest axis" is teachable, not jargon.
const AXIS_MEANING = {
  golden_angle: "how close the spiral's divergence angle sits to the golden angle (137.5°), which packs florets with no gaps or seams",
  clean_freq: "whether the field's frequency lands near a whole number, so the pattern tiles without tearing",
  fivefold: "how close the interference is to true five-fold (aperiodic) symmetry",
  balance: "how evenly the form's mass sits around its centre",
  coverage: "how much of the frame the structure actually fills — not sparse, not clumped",
  contrast: "the spread between the field's light and dark — how legible the structure is",
  complexity: "whether the structure is rich enough to be interesting without collapsing into noise",
  novelty: "how far this sits from frames I've already seen (no corpus is loaded, so I read it as maximal)",
};

// Read everything answerable straight off the current World — nothing invented.
export function readCtx(world) {
  const rp = (world.layers[0] || {}).render_program || {};
  const t = world.trajectory || { steps: [] };
  const acc = t.steps[t.accepted_index] || t.steps[t.steps.length - 1] || { margins: {}, params: {} };
  const margins = acc.margins || {};
  let weakest = null, lo = Infinity, strongest = null, hi = -Infinity;
  for (const [k, v] of Object.entries(margins)) { if (+v < lo) { lo = +v; weakest = k; } if (+v > hi) { hi = +v; strongest = k; } }
  const cert = world.certificate || {};
  const ev = Object.fromEntries((cert.evidence || []).map(([k, v]) => [k, v]));
  return {
    title: world.title, generator: rp.generator || "?", isField: rp.target === "glsl-fragment",
    params: acc.params || {}, margins, weakest, weakestVal: lo, strongest, strongestVal: hi,
    score: world.receipt ? world.receipt.final_score : null, palette: world.palette || [],
    period: (world.timeline || {}).period,
    deviation: parseFloat(ev.deviation), tolerance: parseFloat(ev.tolerance),
    verdict: cert.verdict || "unverifiable", oracle: cert.oracle || "",
  };
}

const axisList = c => c.generator && c.margins ? Object.entries(c.margins).map(([k, v]) => `${k} ${fmt(v)}`).join(", ") : "—";

export const QUESTIONS = [
  { id: "look", q: "What are you looking at?" },
  { id: "judge", q: "How did you judge it?" },
  { id: "why", q: "Why this verdict?" },
  { id: "weak", q: "What's your weakest axis?" },
  { id: "trust", q: "Should I trust you?" },
  { id: "meta", q: "What is this tool doing?" },
];

// Each answer returns { text, grounds:[{k,v}], recheck:bool }. `grounds` are the exact numbers behind
// the words (rendered as evidence chips); `recheck` offers the inline re-derivation of the verdict.
export function answer(id, world) {
  const c = readCtx(world);
  switch (id) {
    case "look":
      return { text: `I'm looking at ${c.title} — a ${c.isField ? "continuous field" : "point cloud"} from the `
          + `${c.generator} generator${c.period ? `, breathing on a ${fmt(c.period)}s loop` : ""}, over a `
          + `${c.palette.length}-colour palette. I never saw your screen; I built this from a closed-form rule and read its structure directly.`,
        grounds: [{ k: "generator", v: c.generator }, { k: "form", v: c.isField ? "field" : "points" }, { k: "palette", v: c.palette.length }], recheck: false };
    case "judge":
      return { text: `I scored it on named criteria I didn't get to pick: ${axisList(c)}. Cohesion is the harmonic mean `
          + `(${fmt(c.score)}), so a single weak axis drags the whole frame down — I converge only when it's good on every axis, not on average.`,
        grounds: Object.entries(c.margins).map(([k, v]) => ({ k, v: fmt(v) })), recheck: false };
    case "why":
      return { text: `My bar is fixed: a frame is structurally fit when its deviation from perfect cohesion is at most `
          + `${fmt(c.tolerance, 2)}. Here deviation is ${fmt(c.deviation, 4)} ${c.deviation <= c.tolerance ? "≤" : ">"} `
          + `${fmt(c.tolerance, 2)}, so I read it as ${c.verdict}. I didn't choose that bar for this frame — it's the same `
          + `${c.oracle} rule for every frame. Don't take my word: re-derive it.`,
        grounds: [{ k: "deviation", v: fmt(c.deviation, 4) }, { k: "tolerance", v: fmt(c.tolerance, 2) }, { k: "verdict", v: c.verdict }], recheck: true };
    case "weak": {
      const m = AXIS_MEANING[c.weakest] || "a criterion I measure on this frame";
      return { text: `${c.weakest}, at ${fmt(c.weakestVal)} — ${m}. It's my least-satisfied axis, so it's what's holding the cohesion `
          + `down. Ask me to improve it and watch which parameter I move, or push it lower yourself and watch me refuse to pretend.`,
        grounds: [{ k: c.weakest, v: fmt(c.weakestVal) }, { k: "strongest", v: `${c.strongest} ${fmt(c.strongestVal)}` }], recheck: false };
    }
    case "trust":
      return { text: `No — don't. That's the whole point. Everything I just told you is a number you can recompute. Press "re-derive" `
          + `and your own browser reproduces my verdict from this certificate's own evidence. If I'm wrong, you'll catch me — and you should.`,
        grounds: [{ k: "oracle", v: c.oracle }], recheck: true };
    case "meta":
      return { text: `Three moves, and you can audit each one. I perceive this frame into a witnessed form — the structure on the right. `
          + `I check it against criteria I didn't author. And I hand you a certificate (verdict, oracle, evidence) you re-derive yourself. `
          + `Perceive, judge, prove. Move a slider or ask me to improve it: we're both changing the same frame, and the verdict stays honest.`,
        grounds: [{ k: "loop", v: "perceive · judge · prove" }], recheck: false };
    default:
      return { text: `I can only speak to what I witnessed in this frame — its structure, my criteria, and the certificate between us. `
          + `Ask me what I'm looking at, how I judged it, why this verdict, or what's weakest — and re-derive whatever I claim.`,
        grounds: [], recheck: false };
  }
}

// A spoken reaction to an actuation — by you (a slider) or by the model (a refine step). The frame
// changed; the witness reports the new reading honestly, including a flip across the bar.
export function reaction(kind, world, extra = {}) {
  const c = readCtx(world);
  if (kind === "switch")
    return { text: `New frame: ${c.title}. I read it as ${c.verdict} at cohesion ${fmt(c.score)}. Ask me anything about it — and check what I say.`,
      grounds: [{ k: "verdict", v: c.verdict }, { k: "cohesion", v: fmt(c.score) }], recheck: true };
  if (kind === "human") {
    const flip = extra.prevVerdict && extra.prevVerdict !== c.verdict;
    return { text: `You set ${extra.param} to ${fmt(extra.value, 2)}. I re-read the frame: cohesion ${fmt(extra.prevScore)} → ${fmt(c.score)}, `
        + `so I now call it ${c.verdict}${flip ? ` — it flipped, and I won't pretend otherwise` : ""}. My bar didn't move; the frame did. Re-derive it.`,
      grounds: [{ k: extra.param, v: fmt(extra.value, 2) }, { k: "deviation", v: fmt(c.deviation, 4) }, { k: "verdict", v: c.verdict }], recheck: true };
  }
  if (kind === "model") {
    if (!extra.moved)
      return { text: `I can't improve it further on these axes — this is the best I can witness: cohesion ${fmt(c.score)}, ${c.verdict}. `
          + `It's converged. Push it off-balance yourself if you want to see me recover it.`,
        grounds: [{ k: "cohesion", v: fmt(c.score) }, { k: "verdict", v: c.verdict }], recheck: true };
    return { text: `I moved ${extra.moved.param} from ${fmt(extra.moved.from, 2)} to ${fmt(extra.moved.to, 2)} — the single change that most `
        + `improved cohesion (${fmt(extra.prevScore)} → ${fmt(c.score)}), lifting my weakest criterion. See the field change on the left and the `
        + `axes shift on the right. I only ever keep a move that improves the score; check it.`,
      grounds: [{ k: extra.moved.param, v: `${fmt(extra.moved.from, 2)} → ${fmt(extra.moved.to, 2)}` }, { k: "cohesion", v: `${fmt(extra.prevScore)} → ${fmt(c.score)}` }, { k: "verdict", v: c.verdict }], recheck: true };
  }
  return answer("meta", world);
}

// Route free text to the nearest grounded answer; honest fallback otherwise.
export function freeText(input, world) {
  const s = (input || "").toLowerCase();
  const has = (...ks) => ks.some(k => s.includes(k));
  if (has("trust", "believe", "lie", "fool", "honest")) return answer("trust", world);
  if (has("why", "verdict", "refut", "verif", "pass", "fail", "deviation", "bar")) return answer("why", world);
  if (has("weak", "worst", "improve", "better", "lowest", "fix")) return answer("weak", world);
  if (has("judge", "score", "criteri", "axis", "axes", "cohesion", "how")) return answer("judge", world);
  if (has("look", "see", "what", "this", "frame", "show")) return answer("look", world);
  if (has("tool", "doing", "the point", "purpose", "demo")) return answer("meta", world);
  return answer("__fallback__", world);
}

export { structuralFitnessVerdict };
