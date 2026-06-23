// showcase.js — orchestration for The Shared Frame.
//
// Loads a baked, Certificate-bearing World, renders it through both apertures (the human eye
// via render.js's WebGL/Canvas renderer; the model's eye as witnessed structure), and shows the
// binding — the coherence-membrane Certificate — between them. Later increments wire the live
// re-check, the cohesion slider, and the generator switch into the same showWorld() spine.
import { renderFrame, renderReasoning, describe } from "./render.js";
import { recheckCertificate, issueCertificate } from "./verdict.js";

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
let activeName = "gyroid";
let motionOn = !reducedMotion();
let engineCohesion = 0.9;   // the active world's witnessed cohesion (1 - deviation)

function announce(msg) { $("status").textContent = msg; }

// The witnessed cohesion the engine actually scored this frame at (1 - the certificate's deviation).
function cohesionOf(world) {
  const cert = world && world.certificate;
  if (!cert) return 0.9;
  const ev = Object.fromEntries((cert.evidence || []).map(([k, v]) => [k, v]));
  const d = parseFloat(ev.deviation);
  return Number.isFinite(d) ? Math.round((1 - d) * 100) / 100 : 0.9;
}

// Make plain WHICH certificate is on the card: the engine's witnessed one, or one you re-issued by
// tampering with the score. Honesty about provenance is the whole exercise.
function setCertMode(mode, cohesion) {
  const el = $("cert-mode");
  if (!el) return;
  if (mode === "tamper") {
    el.className = "cert-mode tamper";
    el.innerHTML = `you re-issued this certificate at cohesion <b>${cohesion.toFixed(2)}</b> — ` +
      `this is your hypothetical, not the engine's witnessed score (<b>${engineCohesion.toFixed(2)}</b>)`;
  } else {
    el.className = "cert-mode";
    el.innerHTML = `this is the engine's <b>witnessed</b> certificate for the frame — re-check it, or tamper with the score above`;
  }
}

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

  const handle = renderFrame(stage, world, { motion: motionOn });
  current = { world, stop: handle.stop };

  const pal = world.palette || [];
  $("swatches").innerHTML = pal.map(c => `<i style="background:${c}"></i>`).join("");
  $("badge").textContent = world.layers
    .map(l => l.organ_id + "·" + l.render_program.target.split("-")[0]).join("  +  ");

  renderReasoning({ params: $("params"), axes: $("axes"), trajectory: $("trajectory") }, world);
  showCertificate(world.certificate);

  engineCohesion = cohesionOf(world);
  setCertMode("engine");
  const verdict = world.certificate ? world.certificate.verdict : "none";
  announce(`${describe(world)} Certificate: ${verdict}.`);
  window.__world = world; // exposed for tests / re-check wiring
}

async function loadWorld(name) {
  const r = await fetch(FIXTURES[name]);
  if (!r.ok) throw new Error(`${name} -> ${r.status}`);
  return r.json();
}

// Re-render ONLY the human-eye frame (e.g. on a motion toggle) without disturbing the certificate
// the user may have tampered with — the frame and the verdict are independent surfaces.
function repaint() {
  if (!current) return;
  if (current.stop) current.stop();
  current.stop = renderFrame($("stage"), current.world, { motion: motionOn }).stop;
}

// The liquid switch: swap the frame; both apertures AND the engine's certificate move in lockstep,
// and the slider resets to the new frame's witnessed cohesion.
async function selectGenerator(name) {
  if (!FIXTURES[name]) return;
  try {
    const world = await loadWorld(name);
    activeName = name;
    showWorld(world);
    const s = $("cohesion");
    if (s) { s.value = String(engineCohesion); $("cohesion-val").textContent = engineCohesion.toFixed(2); }
    document.querySelectorAll("#gen-switch button").forEach(b =>
      b.setAttribute("aria-pressed", String(b.dataset.gen === name)));
  } catch (e) {
    announce(`Failed to load ${name}: ${e.message}`);
    console.error(e);
  }
}

// Tamper: re-issue the certificate at a chosen cohesion (deviation = 1 - cohesion) and re-bind it.
// The frame is untouched — only the claimed score changes, so the viewer can watch the verdict flip
// at the engine's own 0.60 bar and then re-check that the flip is mechanical, not asserted.
function onSlider(v) {
  $("cohesion-val").textContent = v.toFixed(2);
  showCertificate(issueCertificate(v));
  setCertMode("tamper", v);
  announce(`Re-issued at cohesion ${v.toFixed(2)}: verdict ${liveCert.verdict}.`);
}

(async function boot() {
  $("recheck-btn").addEventListener("click", recheck);

  $("gen-switch").addEventListener("click", e => {
    const btn = e.target.closest("button[data-gen]");
    if (btn) selectGenerator(btn.dataset.gen);
  });

  const slider = $("cohesion");
  slider.addEventListener("input", e => onSlider(parseFloat(e.target.value)));

  const motion = $("motion-toggle");
  motion.checked = motionOn;
  motion.addEventListener("change", e => { motionOn = e.target.checked; repaint(); });

  try {
    await selectGenerator("gyroid");
  } catch (e) {
    announce("Failed to load the frame: " + e.message);
    $("stage").setAttribute("aria-label", "the frame failed to load");
    console.error(e);
  }
})();

// exposed so tests / future increments can drive the same spine
export { showWorld, loadWorld, showCertificate, selectGenerator, onSlider };
