// dialogue.js -- the model's voice, grounded. You can talk to it about the frame; it can only say what
// the witnessed structure licenses, and every claim is a number you can re-derive. This is the honest
// core of "talk to the model": not a chatbot improvising, but a witness reporting what it measured --
// its criteria, their margins, the cohesion, and the certificate's own deviation/tolerance. The verdict
// bar comes from verdict.js (single source). Pure + node-testable; the UI in showcase.js renders it.
import { structuralFitnessVerdict } from "./verdict.js";

const fmt = (v, n = 3) => (typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(n)) : String(v));

// What each criterion actually means, in plain words -- so "weakest axis" is teachable, not jargon.
const AXIS_MEANING = {
  golden_angle: "how close the spiral's divergence angle sits to the golden angle (137.5°), which packs florets with no gaps or seams",
  clean_freq: "whether the field's frequency lands near a whole number, so the pattern tiles without tearing",
  fivefold: "how close the interference is to true five-fold (aperiodic) symmetry",
  balance: "how evenly the form's mass sits around its centre",
  coverage: "how much of the frame the structure actually fills -- not sparse, not clumped",
  contrast: "the spread between the field's light and dark -- how legible the structure is",
  complexity: "whether the structure is rich enough to be interesting without collapsing into noise",
  novelty: "how far this sits from frames I've already seen (no corpus is loaded, so I read it as maximal)",
};

// Read everything answerable straight off the current World -- nothing invented.
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

const axisList = c => c.generator && c.margins ? Object.entries(c.margins).map(([k, v]) => `${k} ${fmt(v)}`).join(", ") : "--";

export const QUESTIONS = [
  { id: "look", q: "What do you see?" },
  { id: "judge", q: "How does it hold together?" },
  { id: "weak", q: "Where could it be better?" },
  { id: "idea", q: "What could we try?" },
  { id: "why", q: "How are you judging it?" },
  { id: "meta", q: "What is this place?" },
];

// Each answer returns { text, grounds:[{k,v}], recheck:bool }. `grounds` are the exact numbers behind
// the words (rendered as evidence chips); `recheck` offers the inline re-derivation of the verdict.
export function answer(id, world) {
  const c = readCtx(world);
  switch (id) {
    case "look":
      return { text: `I'm looking at ${c.title} -- a ${c.isField ? "flowing field" : "spray of points"} from the `
          + `${c.generator} generator${c.period ? `, breathing on a ${fmt(c.period)}s loop` : ""}, over a `
          + `${c.palette.length}-colour palette. We can pull it in any direction from here -- tell me what you'd like to see, or let me try something.`,
        grounds: [{ k: "generator", v: c.generator }, { k: "form", v: c.isField ? "field" : "points" }, { k: "palette", v: c.palette.length }], recheck: false };
    case "judge":
      return { text: `I'm reading it on a few qualities at once: ${axisList(c)}. They fold into one feel for how well it's holding `
          + `together (${fmt(c.score)}) -- and because it's the harmonic mean, one weak quality pulls the whole thing down, which is exactly `
          + `what makes it worth improving together.`,
        grounds: Object.entries(c.margins).map(([k, v]) => ({ k, v: fmt(v) })), recheck: false };
    case "why":
      return { text: `I'm scoring it on a few named qualities and folding them together into one number -- cohesion, ${fmt(c.score)} `
          + `right now. Whether that reads as a clean "yes" comes down to a single fixed line, the same for every frame, so right now I'd `
          + `call it ${c.verdict}. If you ever want to see exactly how the number becomes that call, you can open it up -- but you don't have to.`,
        grounds: [{ k: "cohesion", v: fmt(c.score) }, { k: "deviation", v: fmt(c.deviation, 4) }, { k: "reads as", v: c.verdict }], recheck: true };
    case "weak": {
      const m = AXIS_MEANING[c.weakest] || "a quality I measure on this frame";
      return { text: `If we want to push it further, ${c.weakest} (at ${fmt(c.weakestVal)}) is where there's most room -- ${m}. `
          + `Ask me to take a turn and watch which parameter I move toward it, or grab a slider and chase it yourself.`,
        grounds: [{ k: c.weakest, v: fmt(c.weakestVal) }, { k: "strongest", v: `${c.strongest} ${fmt(c.strongestVal)}` }], recheck: false };
    }
    case "idea":
      return { text: `A few things we could try: let me take a turn and nudge it toward its weakest quality (${c.weakest}); or you grab a `
          + `parameter and pull it somewhere unexpected and I'll react; or switch the generator and we start from a completely different shape. `
          + `What are you in the mood to make?`,
        grounds: [{ k: "next", v: `improve ${c.weakest}` }, { k: "or", v: "switch the frame" }], recheck: false };
    case "meta":
      return { text: `It's a place to make something with me, instead of just asking me for it. Bring your own image or generate one here; `
          + `we both look at the same thing and we both get to change it. I'll tell you what I actually see, and if you're ever curious how I `
          + `know, you can check -- but mostly, let's just make something. Move something, or let me take a turn.`,
        grounds: [{ k: "you", v: "shape it" }, { k: "me", v: "shape it too" }], recheck: false };
    default:
      return { text: `I can tell you what I actually see in this frame -- what it's made of, how it holds together, where it could go next. `
          + `Ask me what I see, where it could be better, or what we could try.`,
        grounds: [], recheck: false };
  }
}

// A spoken reaction to an actuation -- by you (a slider) or by the model (a refine step). The frame
// changed; the model reports what it now sees and keeps the collaboration moving.
export function reaction(kind, world, extra = {}) {
  const c = readCtx(world);
  if (kind === "switch")
    return { text: `New frame: ${c.title}. Holding together nicely (${fmt(c.score)}). What do you want to do with it -- change something, or want me to take a turn?`,
      grounds: [{ k: "cohesion", v: fmt(c.score) }], recheck: true };
  if (kind === "human") {
    return { text: `You moved ${extra.param} to ${fmt(extra.value, 2)} -- nice. It shifted how the frame reads (${fmt(extra.prevScore)} → ${fmt(c.score)}); `
        + `${c.score >= extra.prevScore ? "that brought it together a little more" : "that loosened it a bit, which can be exactly what you want"}. Keep going, or hand it to me.`,
      grounds: [{ k: extra.param, v: fmt(extra.value, 2) }, { k: "cohesion", v: `${fmt(extra.prevScore)} → ${fmt(c.score)}` }], recheck: true };
  }
  if (kind === "model") {
    if (!extra.moved)
      return { text: `I've taken it about as far as I can from here -- it's sitting at ${fmt(c.score)} and I can't find a move that helps. `
          + `Your turn: pull it somewhere unexpected and I'll pick it back up.`,
        grounds: [{ k: "cohesion", v: fmt(c.score) }], recheck: true };
    return { text: `My turn -- I nudged ${extra.moved.param} from ${fmt(extra.moved.from, 2)} to ${fmt(extra.moved.to, 2)}, the move that did the `
        + `most for it (${fmt(extra.prevScore)} → ${fmt(c.score)}). Watch the field shift on the left and the qualities on the right. Where should we take it next?`,
      grounds: [{ k: extra.moved.param, v: `${fmt(extra.moved.from, 2)} → ${fmt(extra.moved.to, 2)}` }, { k: "cohesion", v: `${fmt(extra.prevScore)} → ${fmt(c.score)}` }], recheck: true };
  }
  return answer("meta", world);
}

// Route free text to the nearest grounded answer; friendly fallback otherwise.
export function freeText(input, world) {
  const s = (input || "").toLowerCase();
  const has = (...ks) => ks.some(k => s.includes(k));
  if (has("try", "could", "idea", "next", "do with", "make")) return answer("idea", world);
  if (has("weak", "worst", "improve", "better", "lowest", "fix")) return answer("weak", world);
  if (has("trust", "believe", "lie", "honest", "know", "prove", "check")) return answer("why", world);
  if (has("why", "verdict", "reads")) return answer("why", world);
  if (has("judge", "score", "criteri", "axis", "axes", "cohesion", "hold", "how")) return answer("judge", world);
  if (has("look", "see", "what", "this", "frame", "show")) return answer("look", world);
  if (has("tool", "doing", "the point", "purpose", "place", "demo")) return answer("meta", world);
  return answer("__fallback__", world);
}

export { structuralFitnessVerdict };
