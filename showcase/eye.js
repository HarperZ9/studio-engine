// eye.js — the eye, in the browser. The shared perception of WHATEVER you plug in.
//
// A faithful JS port of coherence-membrane's perceptual hash (phash.py): Rec.601 luma -> box-downscale
// to 9x8 -> 64 adjacency bits (dHash). The browser decodes any media you drop in (png/jpg/gif/webp/
// video frame) onto a canvas; this reads those real pixels and witnesses them exactly as the Python
// eye would — gated bit-for-bit in tests/eye.test.mjs against reference hashes computed by the engine.
// So when the model says "I perceive this", it's a number you can recompute. Plus drift (did it change?)
// and honest descriptive features for discussion. The identity SHA-256 is computed via SubtleCrypto.
const HASH_W = 8, HASH_H = 8;

function toGrayscale(px, w, h, ch) {
  const n = w * h, gray = new Array(n);
  if (ch === 1) for (let i = 0; i < n; i++) gray[i] = px[i];
  else if (ch === 2) for (let i = 0; i < n; i++) gray[i] = px[i * 2];
  else for (let i = 0; i < n; i++) { const b = i * ch; gray[i] = Math.floor((px[b] * 299 + px[b + 1] * 587 + px[b + 2] * 114) / 1000); }
  return gray;
}

function downscale(gray, w, h, tw, th) {
  const out = new Array(tw * th).fill(0);
  for (let ty = 0; ty < th; ty++) {
    const y0 = Math.floor(ty * h / th), y1 = Math.max(y0 + 1, Math.floor((ty + 1) * h / th));
    for (let tx = 0; tx < tw; tx++) {
      const x0 = Math.floor(tx * w / tw), x1 = Math.max(x0 + 1, Math.floor((tx + 1) * w / tw));
      let total = 0, count = 0;
      for (let yy = y0; yy < y1; yy++) { const row = yy * w; for (let xx = x0; xx < x1; xx++) { total += gray[row + xx]; count++; } }
      out[ty * tw + tx] = count ? Math.floor(total / count) : 0;
    }
  }
  return out;
}

function dhashBits(gray, w, h) {
  const small = downscale(gray, w, h, HASH_W + 1, HASH_H);
  let bits = 0n;
  for (let y = 0; y < HASH_H; y++) {
    const row = y * (HASH_W + 1);
    for (let x = 0; x < HASH_W; x++) { bits <<= 1n; if (small[row + x] > small[row + x + 1]) bits |= 1n; }
  }
  return bits;
}

// 64-bit dHash of pixels (ch channels per pixel; 4 = RGBA from a canvas) -> 16-hex string.
export function perceptualHash(px, w, h, ch = 4) {
  return dhashBits(toGrayscale(px, w, h, ch), w, h).toString(16).padStart(16, "0");
}

export function hamming(aHex, bHex) {
  let x = BigInt("0x" + aHex) ^ BigInt("0x" + bHex), c = 0;
  while (x) { c += Number(x & 1n); x >>= 1n; }
  return c;
}

// The drift verdict (phash.compare_drift), fail-closed: MATCH on identical bytes, DRIFT with distance,
// UNVERIFIABLE if either side couldn't be hashed. The re-checkable "did it actually change, and by how much?"
export function compareDrift(baseSha, curSha, basePhash, curPhash) {
  if (!baseSha || !curSha) return { verdict: "UNVERIFIABLE", distance: null, reason: "a SHA-256 identity is missing on one side" };
  if (baseSha === curSha) return { verdict: "MATCH", distance: 0, reason: "identical bytes (sha256 equal)" };
  if (basePhash == null || curPhash == null) return { verdict: "UNVERIFIABLE", distance: null, reason: "bytes differ but a perceptual hash is missing" };
  const dist = hamming(basePhash, curPhash);
  return { verdict: "DRIFT", distance: dist, reason: `bytes differ; perceptual distance ${dist}/64` };
}

// Honest descriptive features measured from the pixels — advisory, for the model to DISCUSS what it
// sees (contrast, coverage, structure/entropy, balance, dominant hue). Not a certificate; the
// re-checkable claims are the identity SHA-256 and the perceptual hash above.
export function features(px, w, h, ch = 4) {
  const gray = toGrayscale(px, w, h, ch), n = gray.length;
  let mn = 255, mx = 0, sum = 0, bright = 0;
  for (const g of gray) { if (g < mn) mn = g; if (g > mx) mx = g; sum += g; if (g > 127) bright++; }
  const contrast = (mx - mn) / 255;
  const coverage = bright / n;
  const hist = new Array(16).fill(0);
  for (const g of gray) hist[Math.min(15, Math.floor(g / 16))]++;
  let H = 0; for (const c of hist) { if (c > 0) { const p = c / n; H -= p * Math.log(p); } }
  const entropy = H / Math.log(16);
  // brightness asymmetry across the two axes -> balance (1 = centred)
  let left = 0, right = 0, top = 0, bot = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const g = gray[y * w + x]; if (x < w / 2) left += g; else right += g; if (y < h / 2) top += g; else bot += g;
  }
  const tot = sum || 1;
  const balance = 1 - Math.min(1, (Math.abs(left - right) + Math.abs(top - bot)) / tot);
  // dominant hue from the average colour (0..1), if colour is present
  let hue = 0;
  if (ch >= 3) {
    let R = 0, G = 0, B = 0; for (let i = 0; i < n; i++) { const b = i * ch; R += px[b]; G += px[b + 1]; B += px[b + 2]; }
    R /= n; G /= n; B /= n; const mxc = Math.max(R, G, B), mnc = Math.min(R, G, B), d = mxc - mnc;
    if (d > 0) { hue = mxc === R ? (((G - B) / d) % 6) : mxc === G ? ((B - R) / d + 2) : ((R - G) / d + 4); hue = ((hue / 6) % 1 + 1) % 1; }
  }
  return { contrast, coverage, entropy, balance, hue, width: w, height: h };
}

// Compute the SHA-256 identity of the original file bytes (re-derivable by anyone). Async (SubtleCrypto).
export async function identitySha256(bytes) {
  const buf = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}
