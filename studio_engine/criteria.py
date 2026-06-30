"""Composable criteria + cohesion -- the verification half, advanced to multi-axis.

Each criterion scores a candidate (`features` dict + generator `params`) in 0..1, higher =
better, judged against a property it did NOT author. Cohesion = harmonic mean: a candidate
must be good on EVERY axis (imbalance is punished), per the refine primitive -- CORRECT, not
merely good-on-average.
"""
from __future__ import annotations

GOLDEN_ANGLE = 137.50776405003785


# --- objective (structural) criteria: judged on the parameter vs an unauthored constant ---
def _golden_angle(f: dict, p: dict) -> float:
    d = abs(((p.get("angle", GOLDEN_ANGLE) - GOLDEN_ANGLE + 180) % 360) - 180)
    return max(0.0, 1.0 - d / 15.0)


def _clean_freq(f: dict, p: dict) -> float:
    v = p.get("freq", 6.0)
    return max(0.0, 1.0 - min(0.5, abs(v - round(v))) / 0.5)


def _fivefold(f: dict, p: dict) -> float:
    w = int(round(p.get("waves", 5)))
    return max(0.0, 1.0 - abs(w - 5) * 0.2)


# --- subjective (aesthetic) criteria: judged on measured features of the output ---
def _balance(f: dict, p: dict) -> float:      # centered mass / radial symmetry
    return max(0.0, 1.0 - f.get("centroid_offset", 1.0))


def _coverage(f: dict, p: dict) -> float:     # even fill of the canvas (not sparse/clumped)
    return f.get("coverage", 0.0)


def _contrast(f: dict, p: dict) -> float:     # dynamic range
    return f.get("contrast", 0.0)


def _complexity(f: dict, p: dict) -> float:   # entropy in the sweet spot (not flat, not noise)
    e = f.get("entropy", 0.0)
    return max(0.0, 1.0 - abs(e - 0.80) / 0.80)


REGISTRY: dict[str, tuple[str, object]] = {
    "golden_angle": ("objective", _golden_angle),
    "clean_freq": ("objective", _clean_freq),
    "fivefold": ("objective", _fivefold),
    "balance": ("subjective", _balance),
    "coverage": ("subjective", _coverage),
    "contrast": ("subjective", _contrast),
    "complexity": ("subjective", _complexity),
}


def score(axis: str, features: dict, params: dict) -> float:
    e = REGISTRY.get(axis)
    return float(e[1](features, params)) if e else 0.0  # type: ignore[operator]


def kind(axis: str) -> str:
    e = REGISTRY.get(axis)
    return e[0] if e else "objective"


def tag(s: float, target: float = 0.9, floor: float = 0.55) -> str:
    return "verified" if s >= target else ("unverifiable" if s >= floor else "refuted")


def cohesion(scores: list[float]) -> float:
    """Harmonic mean -- one bad axis tanks the whole. The opposite of averaging away a flaw."""
    vals = [max(1e-6, min(1.0, s)) for s in scores]
    return len(vals) / sum(1.0 / s for s in vals) if vals else 0.0
