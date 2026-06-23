# The Shared Frame

> One frame, two witnesses, one re-checkable verdict.

A single self-contained page where a model and a human look at the **same** generated frame
through their two native apertures — you see an image, the model sees witnessed structure — bound
by a [coherence-membrane](https://github.com/HarperZ9/coherence-membrane) `Certificate` you can
re-derive in your own browser. Proof, not assertion.

## What you're looking at

- **Your eye** (left) — the frame as pixels. `glsl-fragment` fields render in WebGL1; `point-recipe`
  clouds render in Canvas2D. The same shipped math the engine verified is what paints the screen.
- **The model's eye** (right) — the same frame as the structure the engine derived: the criteria axes
  it was judged on, how well each was met, and the reasoning trajectory that produced it.
- **The binding** (center) — the `Certificate`. Not an opinion: a number (how far the frame sits from
  the bar) plus a fixed rule (`deviation <= tolerance` → `verified`). Oracle `structural-fitness-v1`.

## Try it

- **Switch the frame** — gyroid / quasicrystal / phyllotaxis. Both apertures and the certificate move
  in lockstep; the slider resets to the new frame's witnessed cohesion.
- **Tamper with the score** — re-issue the certificate at any cohesion. Below **0.60** the verdict flips
  to `refuted` — at the engine's own bar, not where anyone would prefer it.
- **Re-check** — your browser re-derives the verdict purely from the certificate's own evidence
  (`deviation`, `tolerance`). `✓ reproduces the certificate` is the proof reproducing itself. You don't
  have to trust either of us.

## Run it

Static — no backend at view time. Any static server:

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
  reference-chamber renderer) is encouraged — one organism.
- **The verdict authority is external.** The re-check reproduces coherence-membrane's bar exactly
  (tolerance `0.4`); the page invents no bar of its own and re-derives purely from the certificate.
- **Accessible.** The render carries a live `aria-label` description; the verdict announces via
  `aria-live`; controls are keyboard-operable; `prefers-reduced-motion` is honored, with a motion toggle.

| File | Role |
|------|------|
| `index.html` | the page — dual aperture, certificate card, controls, narrative (self-contained shell) |
| `showcase.js` | orchestration: load fixture, render both eyes, wire re-check / slider / switch / motion |
| `render.js` | the human eye — WebGL field + Canvas2D points + reasoning DOM (lifted from `reference-chamber.html`) |
| `verdict.js` | the proof — faithful `structural_fitness` JS port + Certificate factory (node-testable, pure) |
| `worlds/*.json` | baked, Certificate-bearing `World` fixtures |
| `build_fixtures.py` | regenerates the fixtures deterministically (provenance) |
| `tests/verdict.test.mjs` | node gate: the re-check reproduces the baked verdicts and the boundary |

---

witnessed by studio-engine · judged by coherence-membrane · re-checkable by you
