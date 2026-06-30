// The faithfulness gate. The browser engine must reproduce the Python engine: re-evaluating each
// baked World at its OWN witnessed params must yield the same cohesion and the same per-axis margins
// (within float tolerance). If this passes, the live certificate the page issues after a human or the
// model actuates the substrate is REAL -- the same verdict studio-engine would have reached.
//
// Run: node --test showcase/tests/engine.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { evaluate, synthesize, refineStep, certify } from "../engine.js";
import { recheckCertificate } from "../verdict.js";

const here = dirname(fileURLToPath(import.meta.url));
const worldsDir = join(here, "..", "worlds");
const CASES = ["gyroid", "quasicrystal", "phyllotaxis"];
const EPS = 1e-6;

function bakedParams(world) {
  const t = world.trajectory;
  const acc = t.steps[t.accepted_index] || t.steps[t.steps.length - 1];
  return acc.params;
}

test("JS engine reproduces each baked World's cohesion and margins at its own params", () => {
  // Cohesion is the certificate-determining quantity -- the real faithfulness claim -- asserted strict.
  // The engine stores params AND margins rounded to 4 decimals (engine.py:190,224). Smooth field axes
  // reproduce to rounding; phyllotaxis's point-binning entropy is DISCONTINUOUS in the angle, so it
  // can't be reproduced exactly from rounded params (a bounded ~3e-4 drift). Field axes: strict (1e-4).
  // Point axes: within the documented binning/rounding bound (1e-3). A truly wrong port would blow past
  // both -- cohesion would diverge far more than 1e-4 and the smooth field axes would not match at all.
  for (const gen of CASES) {
    const world = JSON.parse(readFileSync(join(worldsDir, gen + ".json"), "utf8"));
    const params = bakedParams(world);
    const ev = evaluate(gen, params);
    const isField = gen === "gyroid" || gen === "quasicrystal";

    assert.ok(Math.abs(ev.cohesion - world.receipt.final_score) < 1e-4,
      `${gen}: JS cohesion ${ev.cohesion} reproduces baked final_score ${world.receipt.final_score}`);

    const baked = (world.trajectory.steps[world.trajectory.accepted_index] || {}).margins || {};
    const tol = isField ? 1e-4 : 1e-3;
    for (const [axis, val] of Object.entries(baked)) {
      assert.ok(Math.abs(ev.margins[axis] - val) < tol,
        `${gen}: axis ${axis} JS ${ev.margins[axis]} reproduces baked ${val} (tol ${tol})`);
    }
  }
});

test("a synthesized live World carries a certificate that re-checks true", () => {
  for (const gen of CASES) {
    const world = JSON.parse(readFileSync(join(worldsDir, gen + ".json"), "utf8"));
    const live = synthesize(gen, bakedParams(world), world.palette);
    assert.equal(live.certificate.oracle, "structural-fitness-v1");
    assert.equal(recheckCertificate(live.certificate).matches, true, `${gen}: live cert re-derives its own verdict`);
    // the synthesized World has the render-ready shape the page consumes
    assert.ok(live.layers[0].render_program.target);
    assert.equal(typeof live.receipt.final_score, "number");
  }
});

test("the model's refine step only ever improves cohesion (monotone), and can converge", () => {
  // gyroid pushed off a clean frequency: clean_freq drops, cohesion drops -- the model should recover it.
  let params = { freq: 6.4, z: 0.5 };
  let coh = evaluate("gyroid", params).cohesion;
  let moves = 0;
  for (let i = 0; i < 12; i++) {
    const r = refineStep("gyroid", params);
    if (!r.improved) break;
    assert.ok(r.cohesion >= coh - EPS, "refine never decreases cohesion");
    params = r.params; coh = r.cohesion; moves++;
  }
  assert.ok(moves >= 1, "the model made at least one improving move");
  assert.ok(refineStep("gyroid", params).improved === false, "it reaches a point where it cannot improve (converged)");
});

test("tampering the real substrate can drive a genuine refutation", () => {
  // a far-off frequency makes clean_freq ~0; harmonic mean collapses -> a REAL refuted verdict.
  const ev = evaluate("gyroid", { freq: 6.5, z: 0.5 });
  assert.ok(ev.margins.clean_freq < 0.05, "freq 6.5 is maximally far from an integer -> clean_freq ~0");
  const cert = certify(ev.cohesion);
  assert.equal(recheckCertificate(cert).matches, true, "the refutation re-checks true too -- the bar is mechanical");
});
