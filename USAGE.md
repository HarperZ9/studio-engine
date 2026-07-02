# Studio Engine Usage

## Generate A World

```sh
python -m studio_engine 7 gyroid
```

This writes a deterministic world packet under `studio-out/` with JSON, preview,
program, audio, and receipt material derived from the same generator state.

## See The World (Live Renderer)

```sh
python -m studio_engine --render-frames 7 gyroid
```

This drives the headless software rasterizer over the emitted render program and
writes actual PNG frames the user can see under `studio-out/frames-7/`, plus a
`frames.json` receipt. The renderer consumes the same witnessed program: it
reconstructs the strand expression from the shipped AST, re-hashes it, and refuses
to render if the hash no longer matches the program's `expr_sha256` (tamper
detection). Each frame is byte-deterministic, so its `sha256` is a re-checkable
link in the world's provenance chain (folded into the receipt's `artifact_shas`).
For animatable fields the strip sweeps the loop period; point recipes emit one
frame.

## Run The Local API

```sh
python -m studio_engine.server 8777
```

Then open `handoff/reference-chamber.html` in a browser. The chamber consumes the
engine's world and program payloads instead of reimplementing the verified math.

## Run The Static Showcase

```sh
cd showcase
python -m http.server 8000
```

Open `http://127.0.0.1:8000/` and use the shared frame to inspect generated
fixtures, bring your own image/video frame, re-derive certificates, and test the
human/model surface.

## Verify Locally

```sh
python -m unittest discover -s tests
node --test showcase/tests/*.test.mjs
python test_forward_delivery_contract.py
```

Use these commands before changing public docs, handoff contracts, render/audio
payloads, or the showcase.
