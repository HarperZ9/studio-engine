# The Shared Frame — showcase design + plan

> One frame, two witnesses, one re-checkable verdict.
> Build home: `studio-engine/showcase/` (self-contained, portable to the portfolio as a gated follow-on).

**Goal:** A single self-contained page that shows a model and a human looking at the *same*
generated frame through their two native apertures — pixels and witnessed structure — bound by a
coherence-membrane Certificate the viewer can re-derive in their own browser. Proof, not assertion.

**Architecture:** Zero-build, zero third-party dependency, fully client-side (must run on GitHub
Pages static hosting). The human-eye renderer is lifted verbatim from the shipped
`handoff/reference-chamber.html` (WebGL1 fields + Canvas2D point recipes + the witnessed-reasoning
DOM). The proof half is a small, faithful JS port of `coherence_membrane.structural_fitness` plus a
Certificate factory — the **first browser-JS arm of the Certificate**. The frame is a real, regenerable
`World` baked to JSON, carrying a genuine cm Certificate emitted by the unified engine (`simulate`).

**Tech stack:** Vanilla ES modules (matches `reference-chamber.html`), WebGL1, Canvas2D. Tests:
`node --check` + a node assertion test on the verdict module + Playwright browser checks.

## Global Constraints

- **Zero third-party deps.** Stdlib / browser built-ins only. Internal reuse (the engine, the
  reference-chamber renderer) is encouraged — one organism.
- **Static-hostable.** No backend at view time. All data baked as JSON fixtures.
- **The verdict authority is external.** The re-check reproduces `structural_fitness`
  (`deviation <= tolerance` → verified, else refuted; tolerance 0.4; oracle `structural-fitness-v1`)
  exactly as coherence-membrane defines it — the page must not invent its own bar.
- **Re-derivable purely from the certificate.** The re-check reads `deviation` + `tolerance` from the
  certificate's own `evidence` and recomputes the verdict — nothing smuggled in.
- **Portfolio skin from the start.** `--void #0d1b1c` / `--bone #e9e2d0` / `--orange #df5e00` /
  `--ember #efab30`; EB Garamond (body) + Schibsted Grotesk (display) + Spline Sans Mono (mono).
- **Voice:** first-person, plain, serious. "You don't have to trust either of us — check it."
- **Accessibility:** `role="img"` + live `aria-label` description on the render, `aria-live` on the
  verdict, keyboard-operable controls, `prefers-reduced-motion` honored (reuse the chamber's pattern).

## File structure

```
showcase/
  index.html          # the page: dual aperture + certificate card + controls (self-contained shell)
  showcase.js         # orchestration: load fixture, render both eyes, wire re-check + slider + switch
  render.js           # lifted-from-reference-chamber renderer (WebGL field + Canvas2D points + reasoning DOM)
  verdict.js          # faithful structural_fitness JS port + Certificate factory  (node-testable, pure)
  worlds/
    gyroid.json       # hero — glsl-fragment, animatable, verified  (the breathing frame)
    quasicrystal.json # liquid switch — glsl-fragment, verified
    phyllotaxis.json  # liquid switch — point-recipe, verified
  build_fixtures.py   # regenerates worlds/*.json deterministically (corpus off) — provenance
  tests/
    verdict.test.mjs  # node: re-check reproduces the baked verdict; flips at the 0.6 boundary
README.md             # (showcase/README.md) what it is, how to run, how to re-check
```

## Increments (TDD; commit after each green step)

### Increment 1 — Spine: the frame + the dual aperture
- `build_fixtures.py`: import `engine.simulate(7, generator=…, corpus_path=None)`, write `to_json()`
  for gyroid / quasicrystal / phyllotaxis into `worlds/*.json`. Run it; commit the fixtures.
- `render.js`: lift `hexToRGB`, `compile`, `renderField`, `makeEval`, `recipePoints`, `renderPoints`,
  `renderLayer`, and the reasoning-DOM bits (`#axes` margin bars + weakest highlight) from
  `handoff/reference-chamber.html`; export `renderWorld(els, world)`.
- `index.html`: the shell — left panel "Your eye" (a `<canvas>`), center "The binding" (certificate
  card placeholder), right panel "The model's eye" (params + axes + trajectory containers). Portfolio
  skin (CSS variables + fonts).
- `showcase.js`: fetch `worlds/gyroid.json`, call `renderWorld`, populate the model's-eye panel and
  the certificate card from `world.certificate`.
- **Verify:** Playwright — the WebGL canvas paints (non-blank), the certificate card shows
  `oracle=structural-fitness-v1` + `verdict=verified`, the axes bars render with a weakest marker.

### Increment 2 — The proof bites: client-side re-check
- `verdict.js`: `structuralFitnessVerdict(deviation, tolerance)` → `"verified"|"refuted"`;
  `recheckCertificate(cert)` parses `evidence` → {deviation, tolerance}, recomputes the verdict,
  returns `{verdict, deviation, tolerance, matches}`; `issueCertificate(cohesion, tolerance=0.4)`
  → a full Certificate object (claim/verdict/oracle/evidence) matching the Python wire shape.
- `tests/verdict.test.mjs` (write first, RED): for each `worlds/*.json`, `recheckCertificate(world.certificate)`
  reproduces `world.certificate.verdict` and `matches === true`; `structuralFitnessVerdict` flips at the
  boundary (dev 0.40 → verified, 0.4001 → refuted). Implement to GREEN.
- `showcase.js`: a **Re-check** button runs `recheckCertificate` on the live cert and reveals the
  re-derived verdict + deviation ≤ tolerance, with a "✓ reproduces the certificate" confirmation.
- **Verify:** node test green; Playwright — clicking Re-check reveals the reproduced verdict text.

### Increment 3 — The oracle is real: tamper + liquid switch
- A **cohesion slider** (1.0 → 0.3): on input, `issueCertificate(value)` re-issues the cert live; the
  card + verdict update; crossing 0.6 flips verified→refuted, with the boundary marked on the track.
- A **generator switch** (gyroid / quasicrystal / phyllotaxis): swaps the fixture, re-renders both
  eyes + re-derives the certificate in lockstep (the "liquid" beat).
- **Verify:** Playwright — drag slider below 0.6 → verdict reads `refuted`; switch generator → canvas
  + axes + certificate all change together.

### Increment 4 — Voice, polish, accessibility
- The narrative copy (portfolio voice), responsive two-column→stacked layout, focus styles.
- Accessibility: `role="img"` + descriptive `aria-label` (reuse `describe()`), `aria-live="polite"`
  on the verdict, full keyboard operation, `prefers-reduced-motion` + a motion toggle.
- `showcase/README.md`.
- **Verify:** Playwright across a mobile viewport; `node --check` on every `.js`; reduced-motion path.

### Increment 5 — Talk to the model (the final presentable)
The page becomes a *conversation* with the witness, not a static proof. The model speaks **only what
the frame's witnessed structure licenses** — every line is grounded in real numbers (criteria margins,
cohesion, the certificate's deviation/tolerance/verdict) and re-derivable in one click. This is the
astonishing-yet-honest core: a model you can talk to that *cannot say anything it can't prove*, that
*changes its verdict honestly under challenge*, and whose every word you can check yourself.

- `dialogue.js` (pure, node-testable): `answer(id, world, state)` → `{text, grounds[], action}` for a
  fixed question set (what are you looking at / how did you judge it / why this verdict / weakest axis /
  should I trust you / what is this tool doing); `axisAnswer`, `greeting`, `reaction`, `freeText`. The
  verdict bar is imported from `verdict.js` (single source — the model invents no rule of its own).
- A chat panel: question chips + free-text; the model replies in first person, grounded; each claim that
  rests on the certificate carries an inline **↻ re-derive** that runs the real `recheckCertificate` and
  appends the reproduced result — a claim turned into a check in one click. Grounds render as evidence chips.
- **Live, unprompted accountability:** tampering the slider posts a spontaneous model message ("you pushed
  my score below my bar — I have to call this refuted now; I can't move my own bar — re-check me"); switching
  frames posts a greeting; clicking an axis asks the model about that axis. Streamed reveal (reduced-motion safe).
- **Verify:** node test — each fixture's `answer('why')` reproduces the baked verdict, `answer('judge')`
  names the real least-satisfied axis, tamper-mode reproduces the flipped verdict, free-text falls back
  honestly. Playwright — chips reply grounded; ↻ re-derive reproduces; tamper posts the honest reaction.

## Verification strategy

- Pure logic (`verdict.js`) — node assertions (RED→GREEN), the re-check's correctness gate.
- Rendering + DOM + interaction — Playwright, real assertions (canvas non-blank, verdict text flips,
  lockstep update), the way `reference-chamber.html` was proven.
- A reviewer subagent reviews each increment's diff (honest critic; findings delivered against the
  artifact) before it's considered done.

## Out of scope / deferred

- Live in-browser engine (generating Worlds client-side) — fixtures are baked; the reconcile repo's
  JS engine is a later enhancement if we want unbaked frames.
- SSE / live-server "watch it think" — the static page shows the witnessed trajectory from the fixture.
- Portfolio integration (copy → `portfolio-site/shared-perception.html`, ES5 re-style, nav link) —
  a separate, operator-gated deploy step after this artifact is approved.
