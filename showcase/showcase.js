// showcase.js — orchestration for The Shared Frame.
//
// Loads a baked, Certificate-bearing World, renders it through both apertures (the human eye
// via render.js's WebGL/Canvas renderer; the model's eye as witnessed structure), and shows the
// binding — the coherence-membrane Certificate — between them. Later increments wire the live
// re-check, the cohesion slider, and the generator switch into the same showWorld() spine.
import { renderFrame, renderReasoning, describe } from "./render.js";

const $ = id => document.getElementById(id);

const FIXTURES = {
  gyroid: "./worlds/gyroid.json",
  quasicrystal: "./worlds/quasicrystal.json",
  phyllotaxis: "./worlds/phyllotaxis.json",
};

const reducedMotion = () =>
  !!window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let current = null; // { world, stop }

function announce(msg) { $("status").textContent = msg; }

// Paint the binding: the certificate, exactly as the engine emitted it (no re-derivation here).
function showCertificate(cert) {
  if (!cert) {
    $("cert-claim").textContent = "this frame carries no certificate";
    const v = $("cert-verdict"); v.textContent = "—"; v.className = "tag unverifiable";
    $("cert-oracle").textContent = "—"; $("cert-evidence").innerHTML = "";
    return;
  }
  $("cert-claim").textContent = cert.claim || "—";
  const v = $("cert-verdict");
  v.textContent = cert.verdict || "—";
  v.className = "tag " + (cert.verdict || "unverifiable");
  $("cert-oracle").textContent = cert.oracle || "—";
  $("cert-evidence").innerHTML = (cert.evidence || []).map(([k, val]) =>
    `<div class="ev"><span class="ek">${k}</span><span class="ev-v">${val}</span></div>`).join("");
}

function showWorld(world) {
  if (current && current.stop) current.stop();
  const stage = $("stage");
  stage.setAttribute("aria-busy", "false");
  stage.setAttribute("aria-label", describe(world));

  const handle = renderFrame(stage, world, { motion: !reducedMotion() });
  current = { world, stop: handle.stop };

  const pal = world.palette || [];
  $("swatches").innerHTML = pal.map(c => `<i style="background:${c}"></i>`).join("");
  $("badge").textContent = world.layers
    .map(l => l.organ_id + "·" + l.render_program.target.split("-")[0]).join("  +  ");

  renderReasoning({ params: $("params"), axes: $("axes"), trajectory: $("trajectory") }, world);
  showCertificate(world.certificate);

  const verdict = world.certificate ? world.certificate.verdict : "none";
  announce(`${describe(world)} Certificate: ${verdict}.`);
  window.__world = world; // exposed for tests / re-check wiring
}

async function loadWorld(name) {
  const r = await fetch(FIXTURES[name]);
  if (!r.ok) throw new Error(`${name} -> ${r.status}`);
  return r.json();
}

(async function boot() {
  try {
    showWorld(await loadWorld("gyroid"));
  } catch (e) {
    announce("Failed to load the frame: " + e.message);
    $("stage").setAttribute("aria-label", "the frame failed to load");
    console.error(e);
  }
})();

// exposed so later increments (re-check / slider / switch) can drive the same spine
export { showWorld, loadWorld, showCertificate };
