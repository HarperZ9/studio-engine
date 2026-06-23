// Node-side gate for the browser re-check: the verdict logic the page runs client-side must
// reproduce coherence-membrane's structural_fitness exactly, and re-derive each baked
// certificate's verdict purely from that certificate's own evidence.
//
// Run: node --test showcase/tests/verdict.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  structuralFitnessVerdict, recheckCertificate, issueCertificate, ORACLE,
} from "../verdict.js";

const here = dirname(fileURLToPath(import.meta.url));
const worldsDir = join(here, "..", "worlds");
const FIXTURES = ["gyroid", "quasicrystal", "phyllotaxis"];

test("re-check reproduces each baked certificate's verdict from its own evidence", () => {
  for (const name of FIXTURES) {
    const world = JSON.parse(readFileSync(join(worldsDir, name + ".json"), "utf8"));
    const cert = world.certificate;
    assert.ok(cert, `${name} carries a certificate`);
    const r = recheckCertificate(cert);
    assert.equal(r.verdict, cert.verdict, `${name}: re-derived verdict equals the baked verdict`);
    assert.equal(r.matches, true, `${name}: matches === true`);
  }
});

test("structuralFitnessVerdict flips at the tolerance boundary (d <= tol)", () => {
  assert.equal(structuralFitnessVerdict(0.0, 0.4), "verified");
  assert.equal(structuralFitnessVerdict(0.4, 0.4), "verified");     // boundary is inclusive
  assert.equal(structuralFitnessVerdict(0.4001, 0.4), "refuted");   // just over -> refuted
  assert.equal(structuralFitnessVerdict(1.0, 0.4), "refuted");
});

test("structuralFitnessVerdict is unverifiable on a non-finite deviation", () => {
  assert.equal(structuralFitnessVerdict(NaN, 0.4), "unverifiable");
  assert.equal(structuralFitnessVerdict(Infinity, 0.4), "unverifiable");
});

test("issueCertificate mirrors the engine wire shape and round-trips through re-check", () => {
  const hi = issueCertificate(0.9);          // deviation ~0.1 <= 0.4 -> verified
  assert.equal(hi.verdict, "verified");
  assert.equal(hi.oracle, ORACLE);
  assert.deepEqual(hi.evidence.map(e => e[0]), ["deviation", "tolerance"]);
  assert.equal(recheckCertificate(hi).matches, true);

  const lo = issueCertificate(0.5);          // deviation 0.5 > 0.4 -> refuted
  assert.equal(lo.verdict, "refuted");
  assert.equal(recheckCertificate(lo).matches, true);
});
