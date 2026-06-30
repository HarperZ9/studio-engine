# AGENTS.md -- Studio Engine

## Project Boundary

Studio Engine is the Project Telos creative engine surface. It emits replayable
creative worlds: render programs, audio graph data, motion timelines, criteria,
and receipts. Keep the engine deterministic, inspectable, and host-agnostic.

## Public Delivery Rules

- Keep `README.md`, `USAGE.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `AUTHORS.md`,
  `LICENSE`, `.github/FUNDING.yml`, and `.github/workflows/ci.yml` present.
- Public claims must be backed by runnable commands, fixtures, or committed
  artifacts.
- Do not commit generated `studio-out/`, caches, package build output, purchased
  fonts, private media, credentials, or local-only research packets.
- Use ASCII punctuation in forward-facing docs unless a file or protocol
  requires otherwise.

## Developer Verification

Run the targeted local gates before publishing:

```sh
python -m unittest discover -s tests
node --test showcase/tests/*.test.mjs
python test_forward_delivery_contract.py
```

For browser-facing changes, also serve `showcase/` or
`handoff/reference-chamber.html` locally and check console output.
