// The eye's faithfulness gate. The browser perceptual hash must be BIT-IDENTICAL to coherence-membrane's
// phash.py for the same pixels — otherwise "I perceive this image, here's the hash, re-check it" is a lie.
// The reference hexes below were computed by the Python eye (perceptual_hash_raw) on these exact buffers.
//
// Run: node --test showcase/tests/eye.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { perceptualHash, hamming, compareDrift } from "../eye.js";

test("RGB dHash reproduces the Python eye bit-for-bit", () => {
  const W = 32, H = 24, px = new Uint8Array(W * H * 3);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const i = (y * W + x) * 3;
    px[i] = (x * 8 + y * 3) % 256; px[i + 1] = (x * x + y * 7) % 256; px[i + 2] = (x * 5 + y * y) % 256;
  }
  assert.equal(perceptualHash(px, W, H, 3), "0919151515352722");   // <- from coherence_membrane.phash
});

test("grayscale dHash reproduces the Python eye bit-for-bit", () => {
  const W = 20, H = 20, px = new Uint8Array(W * H);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) px[y * W + x] = (x * 12 + y * 5) % 256;
  assert.equal(perceptualHash(px, W, H, 1), "0000010101030306");
});

test("RGBA ignores alpha — same luma, same hash as RGB", () => {
  const W = 32, H = 24, rgb = new Uint8Array(W * H * 3), rgba = new Uint8Array(W * H * 4);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const r = (x * 8 + y * 3) % 256, g = (x * x + y * 7) % 256, b = (x * 5 + y * y) % 256;
    const i3 = (y * W + x) * 3, i4 = (y * W + x) * 4;
    rgb[i3] = r; rgb[i3 + 1] = g; rgb[i3 + 2] = b;
    rgba[i4] = r; rgba[i4 + 1] = g; rgba[i4 + 2] = b; rgba[i4 + 3] = (x * 17) % 256;  // varied alpha, must not matter
  }
  assert.equal(perceptualHash(rgba, W, H, 4), perceptualHash(rgb, W, H, 3));
});

test("drift: identical -> MATCH 0; a real change -> DRIFT with distance; missing -> UNVERIFIABLE", () => {
  assert.deepEqual(compareDrift("abc", "abc", "0919151515352722", "0919151515352722"),
    { verdict: "MATCH", distance: 0, reason: "identical bytes (sha256 equal)" });
  const d = compareDrift("abc", "def", "0919151515352722", "0000010101030306");
  assert.equal(d.verdict, "DRIFT");
  assert.ok(d.distance > 0 && d.distance <= 64);
  assert.equal(d.distance, hamming("0919151515352722", "0000010101030306"));
  assert.equal(compareDrift("abc", "def", "0919151515352722", null).verdict, "UNVERIFIABLE");
});
