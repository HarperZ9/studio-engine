// showcase.js — orchestration for The Shared Frame.
//
// A shared substrate two witnesses actuate together. The engine (engine.js) generates+judges+certifies
// a frame CLIENT-SIDE from live parameters; the human moves those parameters (sliders), the model moves
// them too (a real coordinate-descent refine step), and after every change a REAL coherence-membrane
// certificate re-derives — re-checkable in the browser. You can talk to the model about the frame
// (dialogue.js): it answers only what the witnessed structure licenses, and narrates its own moves.
import { renderFrame, renderReasoning, describe } from "./render.js";
import { recheckCertificate } from "./verdict.js";
import { synthesize, refineStep } from "./engine.js";
import { answer, reaction, freeText, QUESTIONS } from "./dialogue.js";

const $ = id => document.getElementById(id);
const FIXTURES = { gyroid: "./worlds/gyroid.json", quasicrystal: "./worlds/quasicrystal.json", phyllotaxis: "./worlds/phyllotaxis.json" };

// The human's actuation surface, per generator: the real engine parameters and their bounds.
const CONTROLS = {
  gyroid: [{ k: "freq", min: 3, max: 10, step: 0.1, label: "frequency" }, { k: "z", min: 0.05, max: 0.95, step: 0.01, label: "z-slice" }],
  quasicrystal: [{ k: "waves", min: 3, max: 9, step: 1, label: "waves" }, { k: "scale", min: 4, max: 14, step: 0.1, label: "scale" }],
  phyllotaxis: [{ k: "angle", min: 110, max: 165, step: 0.05, label: "divergence angle °" }, { k: "scale", min: 5, max: 16, step: 0.1, label: "scale" }],
};

const reducedMotion = () => !!window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

let current = null;     // { world, stop }
let liveCert = null;    // the certificate on the card (always the live, engine-computed one)
let motionOn = !reducedMotion();
let gen = "gyroid";
let params = {};        // the live parameters both witnesses actuate
const palettes = {}, startParams = {};

function announce(msg) { $("status").textContent = msg; }

// ---- the binding: the certificate card (one place writes it) ----
function showCertificate(cert) {
  liveCert = cert || null;
  $("recheck-out").hidden = true;
  if (!cert) { $("cert-claim").textContent = "this frame carries no certificate"; return; }
  $("cert-claim").textContent = cert.claim || "—";
  const v = $("cert-verdict"); v.textContent = cert.verdict || "—"; v.className = "tag " + (cert.verdict || "unverifiable");
  $("cert-oracle").textContent = cert.oracle || "—";
  $("cert-evidence").innerHTML = (cert.evidence || []).map(([k, val]) =>
    `<div class="ev"><span class="ek">${k}</span><span class="ev-v">${val}</span></div>`).join("");
}

// Re-derive a certificate (the card's, or a chat message's snapshot) purely from its own evidence.
function recheckInto(outEl, cert) {
  if (!cert) return;
  const r = recheckCertificate(cert);
  const rel = r.deviation <= r.tolerance ? "≤" : ">";
  outEl.hidden = false;
  outEl.innerHTML = `<div class="rc-line">re-derived in your browser: deviation <span class="rc-num">${r.deviation}</span> ${rel} `
    + `tolerance <span class="rc-num">${r.tolerance}</span> → <span class="tag ${r.verdict}">${r.verdict}</span></div>`
    + `<div class="rc-match ${r.matches ? "ok" : "bad"}">${r.matches ? "✓ reproduces the certificate — you didn't have to trust it" : "✗ does not match"}</div>`;
  announce(`Re-checked: deviation ${r.deviation} ${rel} tolerance ${r.tolerance}, verdict ${r.verdict}, ${r.matches ? "reproduces" : "does not match"}.`);
}

// ---- render a World through both apertures + the certificate ----
function showWorld(world) {
  if (current && current.stop) current.stop();
  const stage = $("stage");
  stage.setAttribute("aria-busy", "false");
  stage.setAttribute("aria-label", describe(world));
  const handle = renderFrame(stage, world, { motion: motionOn });
  current = { world, stop: handle.stop };
  $("swatches").innerHTML = (world.palette || []).map(c => `<i style="background:${c}"></i>`).join("");
  $("badge").textContent = world.layers.map(l => l.organ_id + "·" + l.render_program.target.split("-")[0]).join("  +  ");
  renderReasoning({ params: $("params"), axes: $("axes"), trajectory: $("trajectory") }, world);
  showCertificate(world.certificate);
  $("cert-mode").innerHTML = `computed live from the frame you and the model are shaping — cohesion <b>${world.receipt.final_score.toFixed(4)}</b>, re-derive it →`;
  window.__world = world;
}

function repaint() { if (current) { if (current.stop) current.stop(); current.stop = renderFrame($("stage"), current.world, { motion: motionOn }).stop; } }

// ---- actuation: rebuild the World from the live params and witness it ----
function synth() { return synthesize(gen, params, palettes[gen]); }

function renderParamControls() {
  $("param-controls").innerHTML = CONTROLS[gen].map(c =>
    `<label class="pc"><span class="pc-label">${c.label}<span class="pc-val" id="pv-${c.k}">${(+params[c.k]).toFixed(2)}</span></span>`
    + `<input type="range" id="pc-${c.k}" min="${c.min}" max="${c.max}" step="${c.step}" value="${params[c.k]}" aria-label="${c.label}"></label>`).join("");
  for (const c of CONTROLS[gen]) $("pc-" + c.k).addEventListener("input", e => onParam(c.k, parseFloat(e.target.value)));
}

// YOU actuate: move a parameter; the frame and a real certificate update; the model reacts honestly.
function onParam(k, v) {
  const prev = current.world;
  params[k] = v;
  $("pv-" + k).textContent = v.toFixed(2);
  const world = synth();
  showWorld(world);
  say(reaction("human", world, { param: k, value: v, prevScore: prev.receipt.final_score, prevVerdict: prev.certificate.verdict }), liveCert);
}

// The MODEL actuates: the single bounded move that most improves cohesion (the engine's own refine).
function modelImprove() {
  const prev = current.world;
  const r = refineStep(gen, params);
  if (r.improved) {
    params = r.params;
    renderParamControls();
    const world = synth();
    showWorld(world);
    say(reaction("model", world, { moved: r.moved, prevScore: prev.receipt.final_score }), liveCert);
  } else {
    say(reaction("model", prev, { moved: null }), liveCert);
  }
}

function selectGenerator(name) {
  if (!FIXTURES[name]) return;
  gen = name; params = { ...startParams[name] };
  renderParamControls();
  const world = synth();
  showWorld(world);
  document.querySelectorAll("#gen-switch button").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.gen === name)));
  say(reaction("switch", world), liveCert);
}

// ---- the conversation ----
function chip(label, onClick) { const b = document.createElement("button"); b.className = "chip"; b.type = "button"; b.textContent = label; b.addEventListener("click", onClick); return b; }

function appendUser(text) {
  const log = $("chat-log");
  const el = document.createElement("div"); el.className = "msg you"; el.innerHTML = `<span class="who">you</span><span class="body"></span>`;
  el.querySelector(".body").textContent = text;
  log.appendChild(el); log.scrollTop = log.scrollHeight;
}

// Render a model message: grounded text, evidence chips, and an inline re-derive of THIS message's
// certificate snapshot — a claim turned into a check in one click.
function say(payload, certSnapshot) {
  const log = $("chat-log");
  const el = document.createElement("div"); el.className = "msg model";
  const grounds = (payload.grounds || []).map(g => `<span class="ground"><span class="gk">${g.k}</span> ${g.v}</span>`).join("");
  el.innerHTML = `<span class="who">model</span><span class="body"></span>`
    + (grounds ? `<div class="grounds">${grounds}</div>` : "")
    + (payload.recheck ? `<div class="msg-recheck"><button type="button" class="chip recheck-chip">↻ re-derive this verdict</button><div class="rc-inline" hidden></div></div>` : "");
  const body = el.querySelector(".body");
  log.appendChild(el); log.scrollTop = log.scrollHeight;
  if (payload.recheck) {
    const snap = certSnapshot;
    el.querySelector(".recheck-chip").addEventListener("click", () => { recheckInto(el.querySelector(".rc-inline"), snap); log.scrollTop = log.scrollHeight; });
  }
  stream(body, payload.text, log);
}

// Type the model's words in (alive); instant under reduced-motion.
function stream(el, text, log) {
  if (reducedMotion()) { el.textContent = text; return; }
  let i = 0; (function tick() { el.textContent = text.slice(0, i); log.scrollTop = log.scrollHeight; if (i++ < text.length) setTimeout(tick, 8); })();
}

function askQuestion(id, label) { appendUser(label); say(answer(id, current.world), liveCert); }
function sendFree() { const inp = $("chat-input"); const v = inp.value.trim(); if (!v) return; appendUser(v); inp.value = ""; say(freeText(v, current.world), liveCert); }

async function loadFixture(name) { const r = await fetch(FIXTURES[name]); if (!r.ok) throw new Error(`${name} -> ${r.status}`); return r.json(); }

// engine-relevant params only (drop any extra baked keys the engine doesn't actuate, e.g. 'dot').
function paramsFrom(world) {
  const acc = world.trajectory.steps[world.trajectory.accepted_index] || world.trajectory.steps.slice(-1)[0];
  const out = {}; for (const c of CONTROLS[world.layers[0].render_program.generator]) out[c.k] = acc.params[c.k];
  return out;
}

(async function boot() {
  $("recheck-btn").addEventListener("click", () => recheckInto($("recheck-out"), liveCert));
  $("gen-switch").addEventListener("click", e => { const b = e.target.closest("button[data-gen]"); if (b) selectGenerator(b.dataset.gen); });
  $("model-improve").addEventListener("click", modelImprove);
  const motion = $("motion-toggle"); motion.checked = motionOn; motion.addEventListener("change", e => { motionOn = e.target.checked; repaint(); });
  const chips = $("chat-chips"); QUESTIONS.forEach(q => chips.appendChild(chip(q.q, () => askQuestion(q.id, q.q))));
  $("chat-send").addEventListener("click", sendFree);
  $("chat-input").addEventListener("keydown", e => { if (e.key === "Enter") sendFree(); });

  try {
    for (const name of Object.keys(FIXTURES)) { const w = await loadFixture(name); palettes[name] = w.palette; startParams[name] = paramsFrom(w); }
    selectGenerator("gyroid");
    say({ text: "I'm the witness on the right. Move a slider, ask me to improve the frame, or just ask me what I see — and re-derive anything I claim. I can't move my own bar.", grounds: [{ k: "loop", v: "perceive · judge · prove" }], recheck: false });
  } catch (e) {
    announce("Failed to load the frame: " + e.message);
    $("stage").setAttribute("aria-label", "the frame failed to load");
    console.error(e);
  }
})();

export { showWorld, selectGenerator, onParam, modelImprove };
