// showcase.js — orchestration for The Shared Frame.
//
// Loads a baked, Certificate-bearing World, renders it through both apertures (the human eye
// via render.js's WebGL/Canvas renderer; the model's eye as witnessed structure), and shows the
// binding — the coherence-membrane Certificate — between them. Later increments wire the live
// re-check, the cohesion slider, and the generator switch into the same showWorld() spine.
import { renderFrame, renderReasoning, describe } from "./render.js";
import { recheckCertificate } from "./verdict.js";

const $ = id => document.getElementById(id);

const FIXTURES = {
  gyroid: "./worlds/gyroid.json",
  quasicrystal: "./worlds/quasicrystal.json",
  phyllotaxis: "./worlds/phyllotaxis.json",
};

const reducedMotion = () =>
  !!window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let current = null;   // { world, stop }
let liveCert = null;  // the certificate currently on the card (the engine's, or one re-issued live)

function announce(msg) { $("status").textContent = msg; }

// Paint the binding: the certificate currently bound to the frame. `showCertificate` is the single
// place the card is written, so the re-check, slider, and switch all share one source of truth.
function showCertificate(cert) {
  liveCert = cert || null;
  $("recheck-out").hidden = true; // a new certificate invalidates the previous re-check
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

// The proof bites: re-derive the verdict in the browser, purely from the certificate's own
// evidence, and show whether it reproduces what the card claims. Trust nothing — check it.
function recheck() {
  const out = $("recheck-out");
  if (!liveCert) return;
  const r = recheckCertificate(liveCert);
  const rel = r.deviation <= r.tolerance ? "≤" : ">";
  out.hidden = false;
  out.innerHTML =
    `<div class="rc-line">re-derived in your browser: deviation ` +
    `<span class="rc-num">${r.deviation}</span> ${rel} tolerance ` +
    `<span class="rc-num">${r.tolerance}</span> → <span class="tag ${r.verdict}">${r.verdict}</span></div>` +
    `<div class="rc-match ${r.matches ? "ok" : "bad"}">` +
    (r.matches ? "✓ reproduces the certificate — you didn't have to trust it"
               : "✗ does not match the certificate") + `</div>`;
  announce(`Re-checked independently: deviation ${r.deviation} ${rel} tolerance ${r.tolerance}, ` +
    `verdict ${r.verdict}, ${r.matches ? "reproduces" : "does not match"} the certificate.`);
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
  $("recheck-btn").addEventListener("click", recheck);
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
