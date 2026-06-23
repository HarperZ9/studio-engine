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

test("'why this verdict' reproduces the baked verdict and offers re-derivation", () => {
  for (const g of ["gyroid", "quasicrystal", "phyllotaxis"]) {
    const w = load(g);
    const a = answer("why", w);
    assert.ok(a.text.includes(w.certificate.verdict), `${g}: the model states the baked verdict (${w.certificate.verdict})`);
    assert.equal(a.recheck, true, `${g}: it invites re-derivation`);
    const dev = a.grounds.find(x => x.k === "deviation");
    assert.ok(dev && Math.abs(parseFloat(dev.v) - parseFloat(Object.fromEntries(w.certificate.evidence).deviation)) < 1e-3,
      `${g}: cites the certificate's real deviation`);
  }
});

test("'what's weakest' names the actual least-satisfied axis", () => {
  const w = load("gyroid");
  const c = readCtx(w);
  const a = answer("weak", w);
  assert.ok(a.text.startsWith(c.weakest), `names the real argmin axis (${c.weakest})`);
  assert.ok(a.grounds.some(x => x.k === c.weakest), "grounds it in that axis's margin");
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

test("a human actuation that flips the verdict is reported as a flip, not hidden", () => {
  const verified = synthesize("gyroid", { freq: 6.0, z: 0.5 }, load("gyroid").palette);
  const refuted = synthesize("gyroid", { freq: 6.5, z: 0.5 }, verified.palette);   // off-integer -> clean_freq ~0
  const r = reaction("human", refuted, { param: "freq", value: 6.5, prevScore: verified.receipt.final_score, prevVerdict: verified.certificate.verdict });
  assert.notEqual(verified.certificate.verdict, refuted.certificate.verdict, "the verdict genuinely flipped");
  assert.ok(r.text.includes(refuted.certificate.verdict), "the model states the new (flipped) verdict");
});

test("free text routes to a grounded answer, with an honest fallback", () => {
  const w = load("gyroid");
  assert.ok(freeText("should I trust you?", w).text.includes("don't"), "trust question routed");
  assert.ok(freeText("why is it verified?", w).recheck === true, "why question routed to re-derivable answer");
  const fb = freeText("tell me a joke about cats", w);
  assert.ok(fb.text.includes("only speak to what I witnessed"), "off-topic falls back honestly");
});
