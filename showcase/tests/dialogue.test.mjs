// The model speaks only what the frame licenses. Each answer must reproduce the witnessed numbers —
// the baked verdict, the real least-satisfied axis, the actual cohesion — and offer re-derivation
// where it rests on the certificate. If the model could say something the structure doesn't support,
// the whole "talk to it, then check it" promise breaks. This gates that.
//
// Run: node --test showcase/tests/dialogue.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { answer, reaction, freeText, readCtx, QUESTIONS } from "../dialogue.js";
import { synthesize } from "../engine.js";

const here = dirname(fileURLToPath(import.meta.url));
const worldsDir = join(here, "..", "worlds");
const load = g => JSON.parse(readFileSync(join(worldsDir, g + ".json"), "utf8"));

test("'how are you judging it' reports the real reading and stays re-derivable", () => {
  for (const g of ["gyroid", "quasicrystal", "phyllotaxis"]) {
    const w = load(g);
    const a = answer("why", w);
    assert.ok(a.text.includes(w.certificate.verdict), `${g}: the model states how it reads (${w.certificate.verdict})`);
    assert.equal(a.recheck, true, `${g}: the answer stays checkable (the affordance is there, not preached)`);
    const dev = a.grounds.find(x => x.k === "deviation");
    assert.ok(dev && Math.abs(parseFloat(dev.v) - parseFloat(Object.fromEntries(w.certificate.evidence).deviation)) < 1e-3,
      `${g}: grounded in the certificate's real deviation`);
  }
});

test("'where could it be better' names the actual least-satisfied quality", () => {
  const w = load("gyroid");
  const c = readCtx(w);
  const a = answer("weak", w);
  assert.ok(a.text.includes(c.weakest), `names the real argmin quality (${c.weakest})`);
  assert.ok(a.grounds.some(x => x.k === c.weakest), "grounds it in that quality's margin");
});

test("every question answers with grounded text", () => {
  const w = load("quasicrystal");
  for (const { id } of QUESTIONS) {
    const a = answer(id, w);
    assert.ok(a.text && a.text.length > 20, `${id}: produces real text`);
    assert.ok(Array.isArray(a.grounds), `${id}: carries grounds`);
  }
});

test("the model narrates its own actuation honestly (a real refine move)", () => {
  // off a clean frequency -> the model should move freq and SAY so, with the cohesion delta.
  const before = synthesize("gyroid", { freq: 6.4, z: 0.5 }, load("gyroid").palette);
  const after = synthesize("gyroid", { freq: 6.0, z: 0.5 }, before.palette);
  const r = reaction("model", after, { moved: { param: "freq", from: 6.4, to: 6.0 }, prevScore: before.receipt.final_score });
  assert.ok(r.text.includes("freq"), "states which parameter it moved");
  assert.ok(after.receipt.final_score > before.receipt.final_score, "the move really improved cohesion");
  assert.equal(r.recheck, true, "offers re-derivation of the new verdict");
});

test("a human actuation that changes the frame is reported honestly, not hidden", () => {
  const verified = synthesize("gyroid", { freq: 6.0, z: 0.5 }, load("gyroid").palette);
  const refuted = synthesize("gyroid", { freq: 6.5, z: 0.5 }, verified.palette);   // off-integer -> clean_freq ~0
  const r = reaction("human", refuted, { param: "freq", value: 6.5, prevScore: verified.receipt.final_score, prevVerdict: verified.certificate.verdict });
  assert.notEqual(verified.certificate.verdict, refuted.certificate.verdict, "the frame genuinely changed how it reads");
  const coh = r.grounds.find(g => g.k === "cohesion");
  assert.ok(coh && coh.v.includes("→"), "the reaction surfaces the real cohesion change, not a hidden one");
  assert.ok(r.text.includes("freq"), "it names what you moved");
});

test("free text routes to a grounded answer, with a friendly fallback", () => {
  const w = load("gyroid");
  assert.equal(freeText("how do you know?", w).recheck, true, "a 'how do you know' question routes to a checkable answer");
  assert.ok(freeText("what could we try?", w).text.length > 20, "an idea question routes to a real suggestion");
  const fb = freeText("tell me a joke about cats", w);
  assert.ok(fb.text.includes("what I actually see"), "off-topic falls back to what it can actually offer");
});
