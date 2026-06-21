"""Stdlib-only unittest suite for studio-engine.

Run from the repo root with PYTHONPATH set to it, e.g.::

    PYTHONPATH=. python -m unittest discover -s tests -v

Zero third-party dependencies (no pytest). Every test that touches the engine
passes ``corpus_path=None`` so it never mutates the persistent ``_corpus.json``,
keeping runs deterministic and side-effect-free.
"""
