// verdict.js — the proof, in the browser.
//
// A faithful JS port of coherence_membrane.structural_fitness: the SAME criterion the engine
// used to judge the frame, so a viewer can re-derive the verdict themselves instead of trusting
// the baked one. VERIFIED iff `deviation <= tolerance`, REFUTED beyond, UNVERIFIABLE when the
// deviation isn't a finite number ("can't measure" is not "unfit"). Oracle "structural-fitness-v1".
//
// This is also the first browser-JS arm of the coherence-membrane Certificate — Python until now.
export const ORACLE = "structural-fitness-v1";
export const DEFAULT_TOLERANCE = 0.4; // the engine's bar: cohesion >= 0.6

export function structuralFitnessVerdict(deviation, tolerance) {
  if (typeof deviation !== "number" || !Number.isFinite(deviation)) return "unverifiable";
  return deviation <= tolerance ? "verified" : "refuted";
}

// Re-derive a certificate's verdict PURELY from its own evidence (deviation, tolerance) — nothing
// smuggled in. Returns the re-derived verdict, the numbers it used, and whether it matches the
// verdict the certificate carries. `matches: true` is the proof reproducing itself.
export function recheckCertificate(cert) {
  const ev = Object.fromEntries((cert.evidence || []).map(([k, v]) => [k, v]));
  const deviation = parseFloat(ev.deviation);
  const tolerance = parseFloat(ev.tolerance);
  const verdict = structuralFitnessVerdict(deviation, tolerance);
  return { verdict, deviation, tolerance, matches: verdict === cert.verdict };
}

// Issue a fresh certificate for a cohesion score — mirrors world_certificate ->
// structural_fitness_criterion(deviation = 1 - cohesion, tolerance). The claim text and evidence
// order match the Python wire shape (the verdict, not the claim wording, carries the decision).
export function issueCertificate(cohesion, tolerance = DEFAULT_TOLERANCE) {
  const deviation = 1 - cohesion;
  const verdict = structuralFitnessVerdict(deviation, tolerance);
  return {
    claim: `structurally fit: deviation ${deviation} <= tolerance ${tolerance}`,
    verdict,
    oracle: ORACLE,
    evidence: [["deviation", String(deviation)], ["tolerance", String(tolerance)]],
  };
}
