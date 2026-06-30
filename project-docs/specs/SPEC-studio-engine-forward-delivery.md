# Spec: Studio Engine Forward Delivery Contract

## Objective

Bring Studio Engine to the shared Project Telos public/developer delivery floor
while preserving its existing creative engine behavior.

## Requirements

- [x] Add root `AGENTS.md`, `USAGE.md`, `CHANGELOG.md`, CI workflow, and
  delivery regression test.
- [x] Keep README focused on public use while linking deeper usage and developer
  status docs.
- [x] Keep the engine deterministic and host-agnostic: no behavior changes to
  generators, world schemas, render programs, audio graph generation, or receipt
  logic.
- [x] Normalize forward-facing punctuation so the public surface scanner reports
  a clean public/developer boundary.
- [x] Use current Node 24-compatible GitHub Actions in the CI workflow.

## Technical Approach

Use a documentation, metadata, CI, and test-only patch. Add a stdlib delivery
contract test, update root docs, add package URLs, and normalize punctuation that
the scanner treats as public-delivery drift. Existing Python and browser tests
remain the behavioral authority for the engine.

## Files Modified

- `AGENTS.md` - repo-specific operating boundary.
- `USAGE.md` - public and developer command path.
- `CHANGELOG.md` - current status and delivery history.
- `.github/workflows/ci.yml` - Python and browser test workflow.
- `test_forward_delivery_contract.py` - executable delivery contract.
- `README.md` and `pyproject.toml` - public/developer links and metadata.
- Existing docs/source comments/UI copy - punctuation normalization only.

## Success Criteria

- [x] `python test_forward_delivery_contract.py` passes.
- [x] `python -m unittest discover -s tests` passes.
- [x] `node --test showcase/tests/*.test.mjs` passes.
- [x] `python -m public_surface_sweeper . --workspace --json` reports
  `MATCH`.
- [x] `git diff --check` exits 0.

## Blockers

None identified.

## Status: IMPLEMENTED
