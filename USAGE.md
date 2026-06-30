# Studio Engine Usage

## Generate A World

```sh
python -m studio_engine 7 gyroid
```

This writes a deterministic world packet under `studio-out/` with JSON, preview,
program, audio, and receipt material derived from the same generator state.

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
