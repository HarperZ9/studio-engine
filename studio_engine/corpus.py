"""A persistent feature corpus — grounds NOVELTY: how unlike everything made before.

Novelty = normalized nearest-neighbour distance in feature space. Without a corpus an engine
repeats itself; with one, "novel" is a checkable claim, not a vibe (the Cell-Patterns antidote).
Stdlib only; JSON-backed; safe to delete.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

FEATURE_KEYS = ["coverage", "centroid_offset", "contrast", "entropy", "hue"]
_DIAG = math.sqrt(len(FEATURE_KEYS))  # max distance in the unit hypercube


class Corpus:
    def __init__(self, vectors: list[list[float]] | None = None, path: Path | None = None):
        self.vectors = vectors or []
        self.path = path

    @classmethod
    def load(cls, path: str | Path | None) -> "Corpus":
        if path is None:
            return cls([], None)
        p = Path(path)
        if p.exists():
            try:
                return cls(json.loads(p.read_text(encoding="utf-8")), p)
            except Exception:
                pass
        return cls([], p)

    def _vec(self, features: dict) -> list[float]:
        return [max(0.0, min(1.0, float(features.get(k, 0.0)))) for k in FEATURE_KEYS]

    def novelty(self, features: dict) -> float:
        """0..1: distance to the nearest prior work (1.0 = first of its kind / far from all)."""
        if not self.vectors:
            return 1.0
        v = self._vec(features)
        dmin = min(math.dist(v, u) for u in self.vectors)
        return max(0.0, min(1.0, dmin / _DIAG))

    def add(self, features: dict) -> None:
        self.vectors.append(self._vec(features))
        if self.path is not None:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_text(json.dumps(self.vectors), encoding="utf-8")
            except Exception:
                pass

    def __len__(self) -> int:
        return len(self.vectors)
