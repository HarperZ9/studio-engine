# The Shared Frame

> One frame, two witnesses, one re-checkable verdict.

A single self-contained page where a model and a human look at the **same** generated frame
through their two native apertures -- you see an image, the model sees witnessed structure -- bound
by a [coherence-membrane](https://github.com/HarperZ9/coherence-membrane) `Certificate` you can
re-derive in your own browser. Proof, not assertion.

## What you're looking at

- **Your eye** (left) -- the frame as pixels. `glsl-fragment` fields render in WebGL1; `point-recipe`
  clouds render in Canvas2D. The same shipped math the engine verified is what paints the screen.
- **The model's eye** (right) -- the same frame as the structure the engine derived: the criteria axes
  it was judged on, how well each was met, and the reasoning trajectory that produced it.
- **The binding** (center) -- the `Certificate`. Not an opinion: a number (how far the frame sits from
  the bar) plus a fixed rule (`deviation <= tolerance` → `verified`). Oracle `structural-fitness-v1`.

## Bring your own frame (the heart)

Plug in **your own** photograph, gif, or video and perceive it *together* with the model:

- **Shared perception** -- the browser decodes your media to a canvas; the eye (`eye.js`, a faithful port
  of coherence-membrane's perceptual hash, gated bit-for-bit in `tests/eye.test.mjs`) witnesses the real
  pixels: an identity SHA-256, a 64-bit perceptual hash, and measured features (contrast, structure,
  balance, hue). The hash is re-derivable -- recompute it from the pixels and check the model.
- **Both actuate, taking turns** -- apply a transform (grayscale, invert, threshold, posterize, mirror,
  edge-detect); then the model takes *its* turn, choosing a transform from what it measured and saying
  why. Every change re-perceives the frame and witnesses the **drift** (perceptual distance /64).
- **Discuss it** -- ask what it sees, its structure, whether to trust it. It answers only what it
  measured, every claim carrying the number behind it.
- **Video** -- load a video/gif, play, and "perceive this frame" to witness frames as they change.

## A shared substrate, two witnesses actuate (generated mode)

The frame is not fixed -- it is a substrate **both the human and the model change**, with a real
certificate re-deriving after every move.

- **You actuate** -- move a real generator parameter (gyroid `freq`/`z`, quasicrystal `waves`/`scale`,
  phyllotaxis `angle`/`scale`). The frame regenerates, the model re-judges it, and the certificate
  updates live. Push a value off a clean point and the verdict turns `refuted` -- at the engine's bar.
- **The model actuates** -- "Let the model improve this frame" runs the engine's own coordinate-descent
  refine step: the single bounded move that most increases cohesion. Watch it recover a tampered frame.
- **Talk to it** -- ask what it sees, how it judged, why this verdict, what's weakest. It answers only
  what the witnessed structure licenses; every claim carries the numbers behind it and an inline
  **↻ re-derive** that reproduces the verdict from the certificate's own evidence.
- **Switch the frame** -- gyroid / quasicrystal / phyllotaxis; both apertures, the controls, and the
  certificate move in lockstep.

The whole generate → judge → certify → refine loop runs **client-side** in `engine.js` -- a faithful
port of studio-engine, gated against the Python fixtures (`tests/engine.test.mjs`). So the verdict you
see and re-derive is the one studio-engine would have reached. You don't have to trust either of us.

## Run it

Static -- no backend at view time. Any static server:

```sh
cd showcase && python -m http.server 8000   # then open http://localhost:8000/
```

## Re-derive the proof

The verdict logic is a faithful JS port of `coherence_membrane.structural_fitness`
([`verdict.js`](verdict.js)). It is gated against the Python definition by a node test:

```sh
node --test showcase/tests/verdict.test.mjs
```

The test asserts each baked certificate re-derives its own verdict from its own evidence, and that
`structuralFitnessVerdict` flips at the inclusive `deviation <= tolerance` boundary.

## Regenerate the frames

The `worlds/*.json` fixtures are real, regenerable `World`s carrying genuine certificates emitted by
the unified engine (corpus off, deterministic seed):

```sh
python showcase/build_fixtures.py
```

## How it's built

- **Zero third-party dependencies.** Browser built-ins only. Internal reuse (the engine, the
  reference-chamber renderer) is encouraged -- one organism.
- **The verdict authority is external.** The re-check reproduces coherence-membrane's bar exactly
  (tolerance `0.4`); the page invents no bar of its own and re-derives purely from the certificate.
- **Accessible.** The render carries a live `aria-label` description; the verdict announces via
  `aria-live`; controls are keyboard-operable; `prefers-reduced-motion` is honored, with a motion toggle.

| File | Role |
|------|------|
| `index.html` | the page -- dual aperture, certificate card, controls, narrative (self-contained shell) |
| `showcase.js` | orchestration: load fixture, render both eyes, wire re-check / slider / switch / motion |
| `render.js` | the human eye -- WebGL field + Canvas2D points + reasoning DOM (lifted from `reference-chamber.html`) |
| `verdict.js` | the proof -- faithful `structural_fitness` JS port + Certificate factory (node-testable, pure) |
| `worlds/*.json` | baked, Certificate-bearing `World` fixtures |
| `build_fixtures.py` | regenerates the fixtures deterministically (provenance) |
| `tests/verdict.test.mjs` | node gate: the re-check reproduces the baked verdicts and the boundary |

---

witnessed by studio-engine · judged by coherence-membrane · re-checkable by you
