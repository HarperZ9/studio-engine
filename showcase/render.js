// render.js — the human eye.
//
// Logic lifted verbatim from studio-engine's handoff/reference-chamber.html: it compiles a
// World's `render_program` CLIENT-SIDE with no backend — WebGL1 for `glsl-fragment` fields,
// Canvas2D for `point-recipe` clouds — so the same shipped math the engine verified is what
// paints the pixels. Adapted into an ES module that renders into a supplied stage element and
// returns a `stop()` handle so a fixture switch can cancel the previous animation cleanly.

const VERT = "attribute vec2 p;void main(){gl_Position=vec4(p,0.0,1.0);}";

export function hexToRGB(h) {
  h = h.replace("#", "");
  return [parseInt(h.slice(0, 2), 16) / 255, parseInt(h.slice(2, 4), 16) / 255, parseInt(h.slice(4, 6), 16) / 255];
}

function compile(gl, type, src) {
  const sh = gl.createShader(type); gl.shaderSource(sh, src); gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(sh));
  return sh;
}

// a tiny evaluator for the recipe's GLSL-subset expression strings (sin/cos/exp/abs/sqrt, +-*, safe /)
export function makeEval(src) {
  const s = src.replace(/\s+/g, ""); let i = 0;
  const peek = () => s[i] || "";
  const F = { sin: Math.sin, cos: Math.cos, exp: Math.exp, abs: Math.abs, sqrt: x => x > 0 ? Math.sqrt(x) : 0 };
  function sum(env) { let v = term(env); while (peek() === "+" || peek() === "-") { const o = s[i++]; const r = term(env); v = o === "+" ? v + r : v - r; } return v; }
  function term(env) { let v = atom(env); while (peek() === "*") { i++; v *= atom(env); } return v; }
  function atom(env) {
    const c = peek();
    if (c === "(") { i++; let neg = false; if (peek() === "-") { i++; neg = true; } const v = sum(env); i++; return neg ? -v : v; }
    if (/[a-z]/i.test(c)) {
      let j = i; while (/[a-z0-9]/i.test(peek())) i++; const id = s.slice(j, i);
      if (peek() === "(") { i++; const a = sum(env); if (peek() === ",") { i++; const b = sum(env); i++; const d = Math.abs(b) > 1e-3 ? b : (b >= 0 ? 1e-3 : -1e-3); return a / d; } i++; return F[id](a); }
      return env[id] || 0;
    }
    let j = i; while (/[0-9.eE+\-]/.test(peek())) { if ((peek() === "+" || peek() === "-") && i > j && !/[eE]/.test(s[i - 1])) break; i++; }
    return parseFloat(s.slice(j, i));
  }
  return env => { i = 0; return sum(env); };
}

// WebGL1 field render: compile render_program.source VERBATIM. Returns { stop } (cancels the RAF loop).
export function renderField(canvas, rp, motionOn) {
  const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
  if (!gl) throw new Error("no WebGL");
  const prog = gl.createProgram();
  gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VERT));
  gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, rp.source));
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
  gl.useProgram(prog);
  const buf = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, "p"); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const pal = ((rp.uniforms.u_palette && rp.uniforms.u_palette.value) || []).flatMap(hexToRGB);
  const vr = rp.value_range || [-1, 1];
  const period = (rp.domain && rp.domain.period) || 1.0, anim = motionOn && !(rp.domain && rp.domain.animatable === false);
  const U = n => gl.getUniformLocation(prog, n);
  let raf = 0;
  function draw(t) {
    const w = canvas.clientWidth, h = canvas.clientHeight; if (canvas.width !== w) { canvas.width = w; canvas.height = h; }
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.uniform2f(U("u_resolution"), canvas.width, canvas.height);
    gl.uniform2f(U("u_value_range"), vr[0], vr[1]);
    if (pal.length) gl.uniform3fv(U("u_palette[0]"), new Float32Array(pal));
    gl.uniform1f(U("u_time"), t);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  if (anim) { const frame = ts => { draw((ts / 1000) % period); raf = requestAnimationFrame(frame); }; raf = requestAnimationFrame(frame); }
  else { requestAnimationFrame(() => draw(0)); }
  return { stop: () => { if (raf) cancelAnimationFrame(raf); raf = 0; } };
}

function recipePoints(r) {
  const out = []; const m = r.mode;
  if (m === "spiral") { const a = r.angle_deg * Math.PI / 180; for (let i = 0; i < r.count; i++) { const rr = r.scale * Math.sqrt(i); out.push([rr * Math.cos(i * a), rr * Math.sin(i * a), i]); } }
  else if (m === "iterated") {
    const ux = makeEval(r.update_x), uy = makeEval(r.update_y); let x = r.init[0], y = r.init[1], idx = 0;
    for (let step = 0; step < r.count; step++) { const nx = ux({ x, y }), ny = uy({ x, y }); x = nx; y = ny; if (step < r.transient) continue; out.push([x, y, idx++]); }
  }
  else if (m === "parametric") {
    const ex = makeEval(r.x), ey = makeEval(r.y), n = Math.max(2, r.count);
    for (let i = 0; i < n; i++) { const t = r.t_max * i / (n - 1); out.push([ex({ t }), ey({ t }), i]); }
  }
  return out;
}

export function renderPoints(canvas, rp, palette) {
  const g = canvas.getContext("2d"); const W = canvas.width = canvas.clientWidth, H = canvas.height = canvas.clientHeight;
  g.clearRect(0, 0, W, H);
  const pts = recipePoints(rp.recipe); if (!pts.length) return;
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...ys), maxy = Math.max(...ys);
  const sp = Math.max(maxx - minx, maxy - miny, 1e-6), pad = W * 0.08, sc = (W - 2 * pad) / sp;
  const ox = (W - (maxx - minx) * sc) / 2 - minx * sc, oy = (H - (maxy - miny) * sc) / 2 - miny * sc;
  for (const [x, y, i] of pts) {
    g.fillStyle = palette[Math.floor(i / pts.length * palette.length) % palette.length] || "#e8e8f0";
    g.beginPath(); g.arc(ox + x * sc, oy + y * sc, 1.5, 0, 7); g.fill();
  }
}

function blendCSS(b) { return b === "add" ? "lighten" : (["screen", "multiply", "normal"].includes(b) ? b : "normal"); }

// Render the visual layers (the human eye) into stageEl. Returns { stop } to cancel animation.
export function renderFrame(stageEl, world, opts = {}) {
  const motionOn = opts.motion !== false;
  [...stageEl.querySelectorAll("canvas,.svgwrap")].forEach(n => n.remove());
  const pal = world.palette || [];
  const stops = [];
  [...world.layers].sort((a, b) => a.z - b.z).forEach(layer => {
    const rp = layer.render_program;
    const c = document.createElement("canvas"); c.className = "render-canvas"; c.style.mixBlendMode = blendCSS(layer.blend);
    stageEl.appendChild(c);
    if (rp.target === "glsl-fragment") {
      try { const h = renderField(c, rp, motionOn); if (h && h.stop) stops.push(h.stop); }
      catch (e) {
        c.remove();
        if (layer.preview) { const d = document.createElement("div"); d.className = "svgwrap"; d.innerHTML = layer.preview.content; stageEl.appendChild(d); }
      }
    } else {
      requestAnimationFrame(() => renderPoints(c, rp, pal));
    }
  });
  return { stop: () => stops.forEach(s => s()) };
}

// A plain-language description of the frame — the render's accessible alt text.
export function describe(world) {
  const kinds = world.layers.map(l => l.render_program.target === "glsl-fragment" ? (l.organ_id + " field") : (l.organ_id + " point cloud"));
  const motion = world.timeline ? `animating, ${world.timeline.period}s loop` : "static";
  return `${world.title}: ${kinds.join(" composited with ")}; ${motion}; ` +
    `${world.layers.length} layer${world.layers.length > 1 ? "s" : ""}; palette of ${world.palette.length} colours; ` +
    `${world.trajectory.converged ? "converged" : "best-effort (unconverged)"}, score ${world.receipt.final_score}.`;
}

function fmtNum(v) { return typeof v === "number" ? (Number.isInteger(v) ? String(v) : v.toFixed(4)) : String(v); }

// Render the model's eye — the witnessed structure: the derived form (params), the per-axis
// margins (with the weakest axis marked), and the reasoning trajectory that produced the frame.
export function renderReasoning(els, world) {
  const t = world.trajectory;
  const acc = t.steps[t.accepted_index] || t.steps[t.steps.length - 1] || { margins: {}, params: {} };
  const margins = acc.margins || {};
  // The accepted (witness) step carries no `weakest` — it accepted. Fall back to the least-satisfied
  // axis: the argmin of the very margins shown, so the panel always names the axis the form meets
  // least, derived transparently from what's on screen (not fabricated).
  let weakest = acc.weakest;
  if (!weakest) {
    let lo = Infinity;
    for (const [k, v] of Object.entries(margins)) { if (+v < lo) { lo = +v; weakest = k; } }
  }
  if (els.params) {
    els.params.innerHTML = Object.entries(acc.params || {}).map(([k, v]) =>
      `<div class="kv"><span class="k">${k}</span><span class="v">${fmtNum(v)}</span></div>`).join("") || "<div class=dim>—</div>";
  }
  if (els.axes) {
    els.axes.innerHTML = Object.entries(margins).map(([k, v]) =>
      `<div class="axis ${k === weakest ? "weak" : ""}"><span class="name">${k}${k === weakest ? " ◀" : ""}</span>` +
      `<span class="bar"><span class="fill" style="width:${Math.round(v * 100)}%"></span></span>` +
      `<span class="val">${(+v).toFixed(3)}</span></div>`).join("") || "<div class=dim>—</div>";
  }
  if (els.trajectory) {
    els.trajectory.innerHTML = (t.steps || []).map(s =>
      `<div class="tstep"><span class="ti">${s.index}</span><span class="tp">${s.phase}</span>` +
      `<span class="tbar"><span class="tfill" style="width:${Math.round((+s.score || 0) * 100)}%"></span></span>` +
      `<span class="tc">${(+s.score || 0).toFixed(3)}</span><span class="tw">${s.weakest || ""}</span></div>`).join("");
  }
}
