"""Witnessed motion: ground a field's animation instead of improvising it.

A field's `t` is its loop time. Over one `period` we check two things and emit them as verdicts:
  * continuity   — the loop has no pop at the seam (max frame-to-frame delta ~ the mean delta);
  * on_criterion — the field stays legible across the loop (its dynamic range never collapses).
The chamber animates u_time within [0, period); these verdicts say the motion is safe to play.
Stdlib + strand only; no engine import (so the engine can import this).
"""
from __future__ import annotations

from .model import Timeline, Verdict
from .strand import expr as ex
from . import criteria as crit


def _frames(e: ex.Expr, period: float, k: int, n: int) -> list:
    return [ex.sample_field(e, n, period * j / k) for j in range(k)]


def continuity(e: ex.Expr, period: float, k: int = 16, n: int = 12) -> Verdict:
    """No popping: the wrap-around (seam) delta should be no larger than the interior deltas.

    A discontinuous loop (wrong period) spikes at the seam — one delta far above the others; a
    seamless loop's seam is just another smooth step. We score the seam against the largest
    interior step, so smooth periodic fields land at ~1.0 and a seam jump is penalized by its size.
    """
    frames = _frames(e, period, k, n)
    allvals = [v for fr in frames for v in fr]
    rng = (max(allvals) - min(allvals)) or 1e-6
    deltas = []
    for j in range(k):
        a, b = frames[j], frames[(j + 1) % k]  # wrap the seam
        deltas.append(sum(abs(x - y) for x, y in zip(a, b)) / len(a))
    seam = deltas[-1]
    interior = deltas[:-1]
    typ = max(interior) if interior else seam
    score = 1.0 if seam <= typ else max(0.0, 1.0 - (seam - typ) / rng)
    return Verdict("temporal.continuity", crit.tag(score), round(score, 4),
                   "seam delta vs largest interior delta: no pop across the loop")


def on_criterion(e: ex.Expr, period: float, k: int = 16, n: int = 12) -> Verdict:
    """Stays legible: every frame keeps a comparable dynamic range (none collapses to flat)."""
    frames = _frames(e, period, k, n)
    ranges = [max(fr) - min(fr) for fr in frames]
    mn, mx = min(ranges), max(ranges)
    score = (mn / mx) if mx > 1e-6 else 0.0
    return Verdict("temporal.on_criterion", crit.tag(score), round(score, 4),
                   "min/max per-frame dynamic range across the loop: stays legible throughout")


def build_timeline(spec: dict, params: dict) -> Timeline | None:
    """Build the witnessed Timeline for an animatable field; None when not animatable."""
    if not spec.get("animatable"):
        return None
    e = spec["expr"](params)
    period = float(spec["period"](params))
    return Timeline(
        period=round(period, 6),
        channels=[{"target": "u_time", "kind": "phase", "from": 0.0, "to": round(period, 6)}],
        continuity=continuity(e, period),
        on_criterion=on_criterion(e, period),
    )
