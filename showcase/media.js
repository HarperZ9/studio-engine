// media.js — Bring Your Own Frame. The shared surface over YOUR subject matter.
//
// You plug in a photograph, a gif, or a video. The browser decodes it onto a canvas; the eye (eye.js)
// perceives those real pixels — identity SHA-256 + a faithful perceptual hash + measured features — and
// witnesses it. Then BOTH of you actuate it: you apply a transform, the model takes its own turn, and
// every change is re-perceived and witnessed with a drift distance. You discuss it together, and the
// model speaks only what it measured — re-derivable in your browser. Self-contained: owns its section.
import { perceptualHash, hamming, compareDrift, features, identitySha256 } from "./eye.js";

const $ = id => document.getElementById(id);
const reduced = () => !!window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// ---- the transforms both witnesses can apply (pure ImageData -> ImageData) ----
const TRANSFORMS = {
  grayscale: { label: "grayscale", fn: d => { for (let i = 0; i < d.length; i += 4) { const g = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000; d[i] = d[i + 1] = d[i + 2] = g; } } },
  invert: { label: "invert", fn: d => { for (let i = 0; i < d.length; i += 4) { d[i] = 255 - d[i]; d[i + 1] = 255 - d[i + 1]; d[i + 2] = 255 - d[i + 2]; } } },
  threshold: { label: "threshold", fn: d => { for (let i = 0; i < d.length; i += 4) { const g = (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000 > 127 ? 255 : 0; d[i] = d[i + 1] = d[i + 2] = g; } } },
  posterize: { label: "posterize", fn: d => { const q = v => Math.round(v / 85) * 85; for (let i = 0; i < d.length; i += 4) { d[i] = q(d[i]); d[i + 1] = q(d[i + 1]); d[i + 2] = q(d[i + 2]); } } },
  mirror: { label: "mirror", whole: true },     // handled on canvas (geometry)
  edges: { label: "edges", kernel: true },      // sobel, needs neighbourhood
};

let canvas, ctx, w = 0, h = 0;
let originalSha = null;          // identity of the bytes you plugged in
let baselineHash = null;         // hash of the frame as first perceived (drift origin)
let prevHash = null;             // hash before the last actuation (for step drift)
let lastObs = null;              // the current perception (for the discussion)
let turn = "you";                // whose turn it is to actuate
let videoEl = null;

function imageData() { return ctx.getImageData(0, 0, w, h); }

function applyKernelEdges(src) {
  const out = new Uint8ClampedArray(src.data.length);
  const gx = [-1, 0, 1, -2, 0, 2, -1, 0, 1], gy = [-1, -2, -1, 0, 0, 0, 1, 2, 1], d = src.data;
  const lum = i => (d[i] * 299 + d[i + 1] * 587 + d[i + 2] * 114) / 1000;
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    let sx = 0, sy = 0, k = 0;
    for (let j = -1; j <= 1; j++) for (let i = -1; i <= 1; i++) { const p = lum(((y + j) * w + (x + i)) * 4); sx += p * gx[k]; sy += p * gy[k]; k++; }
    const m = Math.min(255, Math.hypot(sx, sy)), o = (y * w + x) * 4;
    out[o] = out[o + 1] = out[o + 2] = m; out[o + 3] = 255;
  }
  return new ImageData(out, w, h);
}

// Perceive the current canvas: the eye witnesses the real pixels. Returns the observation.
function perceive() {
  const img = imageData();
  const phash = perceptualHash(img.data, w, h, 4);
  const f = features(img.data, w, h, 4);
  return { identity: originalSha, width: w, height: h, phash, features: f };
}

function fmt(v, n = 3) { return typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(n)) : String(v); }

function renderObservation(obs, drift) {
  $("media-cert").hidden = false;
  $("mc-identity").textContent = obs.identity ? obs.identity.slice(0, 16) + "…" : "—";
  $("mc-dims").textContent = `${obs.width}×${obs.height}`;
  $("mc-phash").textContent = obs.phash;
  const f = obs.features;
  $("mc-feats").innerHTML = [["contrast", f.contrast], ["coverage", f.coverage], ["structure", f.entropy], ["balance", f.balance], ["hue", f.hue]]
    .map(([k, v]) => `<span class="ground"><span class="gk">${k}</span> ${fmt(v)}</span>`).join("");
  const dl = $("mc-drift");
  if (drift) { dl.hidden = false; dl.className = "mc-drift " + (drift.verdict === "MATCH" ? "ok" : "chg");
    dl.innerHTML = `since the last change: <b>${drift.verdict}</b>${drift.distance != null ? ` · perceptual distance <b>${drift.distance}/64</b>` : ""}`; }
  else dl.hidden = true;
}

// ---- the conversation about your media (grounded only in what was measured) ----
function bubble(role, text, grounds, rederive) {
  const log = $("media-log"); const el = document.createElement("div"); el.className = "msg " + role;
  el.innerHTML = `<span class="who">${role === "you" ? "you" : "model"}</span><span class="body"></span>`
    + (grounds && grounds.length ? `<div class="grounds">${grounds.map(g => `<span class="ground"><span class="gk">${g.k}</span> ${g.v}</span>`).join("")}</div>` : "")
    + (rederive ? `<div class="msg-recheck"><button type="button" class="chip recheck-chip">↻ re-derive the hash from the pixels</button><div class="rc-inline" hidden></div></div>` : "");
  const body = el.querySelector(".body");
  log.appendChild(el); log.scrollTop = log.scrollHeight;
  if (rederive) el.querySelector(".recheck-chip").addEventListener("click", () => {
    const again = perceptualHash(imageData().data, w, h, 4);
    const rc = el.querySelector(".rc-inline"); rc.hidden = false;
    const ok = again === rederive.phash;
    rc.innerHTML = `<div class="rc-line">re-read the canvas pixels → hash <span class="rc-num">${again}</span></div>`
      + `<div class="rc-match ${ok ? "ok" : "bad"}">${ok ? "✓ reproduces the witnessed perception — you didn't have to trust it" : "✗ differs from the witnessed hash"}</div>`;
    log.scrollTop = log.scrollHeight;
  });
  if (role === "model" && !reduced()) { let i = 0; (function t() { body.textContent = text.slice(0, i); log.scrollTop = log.scrollHeight; if (i++ < text.length) setTimeout(t, 7); })(); }
  else body.textContent = text;
}

const HUE_NAME = h => ["red", "orange", "yellow", "green", "teal", "blue", "violet", "magenta"][Math.min(7, Math.floor(h * 8))];

function describeText(obs) {
  const f = obs.features;
  const adj = f.contrast > 0.66 ? "high-contrast" : f.contrast < 0.33 ? "soft, low-contrast" : "moderately contrasted";
  const fill = f.coverage > 0.6 ? "mostly bright" : f.coverage < 0.4 ? "mostly dark" : "evenly lit";
  const sym = f.balance > 0.85 ? "well-centred" : "off-balance";
  const str = f.entropy > 0.8 ? "richly textured" : f.entropy < 0.45 ? "flat and simple" : "moderately structured";
  return `I'm looking at the ${obs.width}×${obs.height} frame you gave me — I never assumed what it is, I measured it: ${adj}, `
    + `${fill}, ${str}, ${sym}, with a ${HUE_NAME(f.hue)} cast. My perceptual fingerprint of it is ${obs.phash} — recompute it from the pixels and you'll get the same.`;
}

function mediaAnswer(id) {
  if (!lastObs) return { text: "Plug in a photo, gif, or video first — then I can tell you what I actually see.", grounds: [] };
  const f = lastObs.features, g = k => ({ k, v: fmt(f[k]) });
  if (id === "see" || id === "describe") return { text: describeText(lastObs), grounds: [{ k: "phash", v: lastObs.phash }, g("contrast"), g("entropy")], rederive: lastObs };
  if (id === "structure") return { text: `Structurally I read entropy ${fmt(f.entropy)} (${f.entropy > 0.8 ? "rich detail" : f.entropy < 0.45 ? "large flat regions" : "middling texture"}) and balance ${fmt(f.balance)} `
    + `(${f.balance > 0.85 ? "mass sits near the centre" : "the mass leans to one side"}). That's measured off the luminance, not guessed.`, grounds: [g("entropy"), g("balance"), g("coverage")] };
  if (id === "trust") return { text: `Don't. My only hard claims are the identity SHA-256 of your file and the perceptual hash of the pixels — both recomputable right here. `
    + `Everything else (contrast, structure, hue) is a measurement I show you the number for. Re-derive the hash and check me.`, grounds: [{ k: "phash", v: lastObs.phash }], rederive: lastObs };
  return { text: `I can only speak to what I measured in your frame — its size, its perceptual hash, its contrast/structure/balance/hue. Ask me what I see, or to describe its structure — and re-derive the hash.`, grounds: [] };
}

// The model's measured choice of transform: pick the move that most reveals what it's unsure of.
function modelChoice(f) {
  if (f.entropy < 0.5) return { key: "edges", why: "the frame reads flat to me, so I'll run edge detection to expose whatever structure is hiding in it" };
  if (f.contrast > 0.7) return { key: "posterize", why: "it's very high-contrast, so I'll posterize it to see how much of that is a few dominant tones" };
  if (f.coverage > 0.6) return { key: "threshold", why: "it's mostly bright, so I'll threshold it to find where the real mass sits" };
  return { key: "invert", why: "I'll invert it — sometimes the negative makes the structure I'm reading easier to see" };
}

// Apply a transform (by you or the model), re-perceive, witness the drift, and let the model react.
function actuate(key, who) {
  if (!lastObs) return;
  const t = TRANSFORMS[key]; prevHash = lastObs.phash;
  if (t.whole && key === "mirror") { const tmp = ctx.getImageData(0, 0, w, h); ctx.save(); ctx.scale(-1, 1); ctx.putImageData(tmp, 0, 0); ctx.translate(-w, 0); ctx.drawImage(canvas, 0, 0); ctx.restore();
    // simplest correct mirror: rebuild via a flipped draw
    const off = document.createElement("canvas"); off.width = w; off.height = h; const oc = off.getContext("2d"); oc.putImageData(tmp, 0, 0);
    ctx.clearRect(0, 0, w, h); ctx.save(); ctx.translate(w, 0); ctx.scale(-1, 1); ctx.drawImage(off, 0, 0); ctx.restore(); }
  else if (t.kernel) ctx.putImageData(applyKernelEdges(imageData()), 0, 0);
  else { const img = imageData(); t.fn(img.data); ctx.putImageData(img, 0, 0); }

  lastObs = perceive();
  const drift = compareDrift(originalSha, originalSha + ":" + lastObs.phash, baselineHash, lastObs.phash); // bytes changed -> DRIFT vs baseline
  const stepDist = hamming(prevHash, lastObs.phash);
  renderObservation(lastObs, { verdict: stepDist === 0 ? "MATCH" : "DRIFT", distance: stepDist });
  bubble(who, `${who === "you" ? "I" : "the model"} applied ${TRANSFORMS[key].label}.`, null, null);
  const verb = stepDist === 0 ? "didn't move the perceptual hash at all" : `moved the perceptual hash by ${stepDist}/64 bits`;
  bubble("model", `${who === "you" ? "You" : "I"} applied ${TRANSFORMS[key].label}; that ${verb} (now ${lastObs.phash}). `
    + `${stepDist > 20 ? "A big change — the low-frequency structure really shifted." : stepDist === 0 ? "Visually, that left the structure I read unchanged." : "A modest change to the structure."} Re-derive it.`,
    [{ k: "Δ", v: `${stepDist}/64` }, { k: "phash", v: lastObs.phash }], lastObs);
  setTurn(who === "you" ? "model" : "you");
}

function setTurn(next) { turn = next; const el = $("media-turn"); if (el) el.innerHTML = next === "you" ? "your turn — apply a transform" : `the model's turn — <button type="button" id="model-turn" class="chip">let it take its turn ▶</button>`;
  if (next === "model") $("model-turn").addEventListener("click", () => { const c = modelChoice(lastObs.features); bubble("model", `My turn. ${c.why}.`, null, null); actuate(c.key, "model"); }); }

async function loadFile(file) {
  const buf = new Uint8Array(await file.arrayBuffer());
  originalSha = await identitySha256(buf);
  const url = URL.createObjectURL(file);
  $("media-empty").hidden = true; $("media-stage").hidden = false;
  if (file.type.startsWith("video")) { setupVideo(url); return; }
  const img = new Image();
  img.onload = () => { drawSource(img, img.naturalWidth, img.naturalHeight); firstPerceive(`I perceive your image.`); URL.revokeObjectURL(url); };
  img.onerror = () => bubble("model", "I couldn't decode that file — try a png, jpg, gif, or webp.", null, null);
  img.src = url;
}

function setupVideo(url) {
  videoEl = $("media-video"); videoEl.hidden = false; videoEl.src = url;
  $("media-canvas").hidden = true;
  videoEl.addEventListener("loadeddata", () => bubble("model", "Video loaded. Play it, then press “perceive this frame” to witness a frame — or sample while it plays and we watch it change together.", null, null), { once: true });
}

function sampleVideoFrame() {
  if (!videoEl) return;
  $("media-canvas").hidden = false;
  drawSource(videoEl, videoEl.videoWidth, videoEl.videoHeight);
  if (!baselineHash) firstPerceive(`I perceived this frame.`);
  else { lastObs = perceive(); const dist = hamming(prevHash || baselineHash, lastObs.phash); prevHash = lastObs.phash;
    renderObservation(lastObs, { verdict: dist === 0 ? "MATCH" : "DRIFT", distance: dist });
    bubble("model", `This frame: ${lastObs.phash} — ${dist}/64 bits from the last one I saw. ${dist > 15 ? "The scene moved." : "Nearly the same frame."}`, [{ k: "Δ", v: `${dist}/64` }, { k: "phash", v: lastObs.phash }], lastObs); }
}

function drawSource(src, sw, sh) {
  const MAX = 360; const scale = Math.min(1, MAX / Math.max(sw, sh));
  w = Math.max(1, Math.round(sw * scale)); h = Math.max(1, Math.round(sh * scale));
  canvas = $("media-canvas"); canvas.width = w; canvas.height = h; canvas.hidden = false;
  ctx = canvas.getContext("2d", { willReadFrequently: true });
  ctx.clearRect(0, 0, w, h); ctx.drawImage(src, 0, 0, w, h);
}

function firstPerceive(intro) {
  lastObs = perceive(); baselineHash = lastObs.phash; prevHash = lastObs.phash;
  renderObservation(lastObs, null);
  bubble("model", `${intro} ${describeText(lastObs)} Now we can both change it — apply a transform, then it's my turn. I'll only ever tell you what I measure.`, [{ k: "phash", v: lastObs.phash }, { k: "size", v: `${w}×${h}` }], lastObs);
  setTurn("you");
}

const QUESTIONS = [{ id: "see", q: "What do you see?" }, { id: "structure", q: "What's the structure?" }, { id: "describe", q: "Describe it" }, { id: "trust", q: "Should I trust you?" }];

export function initMedia() {
  const input = $("media-file");
  $("media-drop").addEventListener("click", () => input.click());
  $("media-drop").addEventListener("dragover", e => { e.preventDefault(); $("media-drop").classList.add("over"); });
  $("media-drop").addEventListener("dragleave", () => $("media-drop").classList.remove("over"));
  $("media-drop").addEventListener("drop", e => { e.preventDefault(); $("media-drop").classList.remove("over"); if (e.dataTransfer.files[0]) loadFile(e.dataTransfer.files[0]); });
  input.addEventListener("change", e => { if (e.target.files[0]) loadFile(e.target.files[0]); });

  const pal = $("media-transforms");
  Object.entries(TRANSFORMS).forEach(([k, t]) => { const b = document.createElement("button"); b.className = "chip"; b.type = "button"; b.textContent = t.label;
    b.addEventListener("click", () => { if (!lastObs) return; if (turn !== "you") bubble("you", "(taking another turn)", null, null); actuate(k, "you"); }); pal.appendChild(b); });

  const chips = $("media-chips");
  QUESTIONS.forEach(q => { const b = document.createElement("button"); b.className = "chip"; b.type = "button"; b.textContent = q.q; b.addEventListener("click", () => { bubble("you", q.q, null, null); bubble("model", "", [], null); const log = $("media-log"); log.lastChild.remove(); const a = mediaAnswer(q.id); bubble("model", a.text, a.grounds, a.rederive); }); chips.appendChild(b); });
  $("media-sample").addEventListener("click", sampleVideoFrame);
}
