"""Additive-sine sonification of the refine trajectory. Stdlib only.

Sonifier organ. Turns a rising sequence of refine scores into a short ambient/melodic
piece: scores (0..1, rising) drive rising pitch + brightness across the duration, while
the palette's hue/lightness derive the base frequency and overtone weights. Two surfaces:

  * ``sonify``       -> a finished mono 16-bit WAV (``kind='audio_wav'``), base64-encoded,
                        synthesized here so any client can just play the bytes.
  * ``audio_params`` -> the recipe (``kind='audio_params'``, JSON) so a Web Audio frontend
                        can re-synthesize the same piece live.

Both are deterministic for a given (seed, palette, scores). No third-party imports:
only ``wave``, ``struct``, ``math``, ``io``, ``base64``, ``json`` from the stdlib.
"""
from __future__ import annotations

import base64
import io
import json
import math
import struct
import wave

from studio_engine.model import Artifact

# Pitch range the trajectory sweeps across (Hz). A2-ish floor to a bright ~C6 ceiling;
# the palette nudges the actual base within this band.
_FREQ_LO = 110.0
_FREQ_HI = 1046.5
_MAX_PARTIALS = 6


def _hex_to_rgb(hexstr: str) -> tuple[float, float, float]:
    """'#rrggbb' (or 'rrggbb') -> (r, g, b) each in 0..1. Tolerant of bad input."""
    h = hexstr.strip().lstrip("#")
    if len(h) == 3:  # short form #abc
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return (0.5, 0.5, 0.5)
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
    except ValueError:
        return (0.5, 0.5, 0.5)
    return (r, g, b)


def _rgb_to_hue_light(r: float, g: float, b: float) -> tuple[float, float]:
    """RGB (0..1) -> (hue 0..1, lightness 0..1). HSL-style; hue 0 when achromatic."""
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2.0
    delta = mx - mn
    if delta < 1e-9:
        return (0.0, light)
    if mx == r:
        hue = ((g - b) / delta) % 6.0
    elif mx == g:
        hue = (b - r) / delta + 2.0
    else:
        hue = (r - g) / delta + 4.0
    return ((hue / 6.0) % 1.0, light)


def _palette_stats(palette: list[str]) -> tuple[float, float]:
    """Average (hue, lightness) over a palette, both 0..1. Empty -> neutral midpoint."""
    if not palette:
        return (0.0, 0.5)
    # Average hue on the circle so wrap-around (red ~0 and ~1) doesn't cancel.
    sx = sy = light_sum = 0.0
    for hx in palette:
        hue, light = _rgb_to_hue_light(*_hex_to_rgb(hx))
        ang = hue * 2.0 * math.pi
        sx += math.cos(ang)
        sy += math.sin(ang)
        light_sum += light
    mean_hue = (math.atan2(sy, sx) / (2.0 * math.pi)) % 1.0
    return (mean_hue, light_sum / len(palette))


def _partial_weights(seed: int, lightness: float, hue: float) -> list[float]:
    """Overtone amplitudes (sum-normalized). Lighter palettes = brighter (more upper
    partials); hue + seed add a deterministic, reproducible shimmer per partial."""
    brightness = 0.35 + 0.6 * max(0.0, min(1.0, lightness))  # decay base
    weights: list[float] = []
    for k in range(1, _MAX_PARTIALS + 1):
        # Geometric-ish rolloff, brighter when 'brightness' is high.
        base = brightness ** (k - 1)
        # Deterministic per-partial wobble from seed+hue, bounded to [0.7, 1.3].
        phase = (seed * 2654435761 + k * 40503 + int(hue * 9973)) & 0xFFFF
        wob = 0.7 + 0.6 * (phase / 65535.0)
        weights.append(base * wob / k)  # /k keeps highs from screeching
    total = sum(weights) or 1.0
    return [w / total for w in weights]


def _score_curve(scores: list[float]) -> list[float]:
    """Clamp scores to 0..1; guarantee at least two control points so we can interpolate."""
    if not scores:
        return [0.0, 1.0]
    clamped = [max(0.0, min(1.0, float(s))) for s in scores]
    if len(clamped) == 1:
        return [clamped[0], clamped[0]]
    return clamped


def _sample_curve(curve: list[float], t: float) -> float:
    """Linearly interpolate the (rising) score curve at normalized time t in [0, 1]."""
    if t <= 0.0:
        return curve[0]
    if t >= 1.0:
        return curve[-1]
    span = len(curve) - 1
    pos = t * span
    i = int(pos)
    frac = pos - i
    return curve[i] * (1.0 - frac) + curve[i + 1] * frac


def _envelope(t: float, total: float) -> float:
    """Gentle attack/decay over the whole piece. t and total in seconds."""
    if total <= 0.0:
        return 0.0
    attack = min(0.18 * total, 0.6)
    release = min(0.30 * total, 1.2)
    if t < attack:
        return t / attack
    if t > total - release:
        return max(0.0, (total - t) / release)
    return 1.0


def _step_freqs(palette: list[str], scores: list[float]) -> tuple[float, list[float]]:
    """Base frequency (from palette) + the per-step target frequency the curve sweeps to."""
    hue, light = _palette_stats(palette)
    # Hue picks where in the band the base sits; lighter palettes ride a touch higher.
    base_t = 0.10 + 0.45 * hue + 0.15 * light
    base_t = max(0.0, min(0.7, base_t))
    base_freq = _FREQ_LO * (_FREQ_HI / _FREQ_LO) ** base_t
    curve = _score_curve(scores)
    # Each step maps its score to a multiplier from base (1x) up toward ~3x at score 1.
    step_freqs = [base_freq * (1.0 + 2.0 * s) for s in curve]
    return base_freq, step_freqs


def sonify(seed: int, palette: list[str], scores: list[float],
           duration: float = 6.0, sample_rate: int = 44100) -> Artifact:
    """Additive-sine WAV that sonifies the refine trajectory.

    scores (0..1, rising) sweep pitch + brightness across ``duration``; the palette's
    mean hue/lightness set the base frequency and overtone weights. Mono int16, written
    via the ``wave`` module and base64-encoded. Returns a finalized ``audio_wav`` Artifact.
    """
    duration = max(0.1, float(duration))
    sample_rate = max(8000, int(sample_rate))
    hue, light = _palette_stats(palette)
    weights = _partial_weights(seed, light, hue)
    base_freq, _ = _step_freqs(palette, scores)
    curve = _score_curve(scores)

    n_samples = int(duration * sample_rate)
    # Phase accumulators per partial so a sweeping frequency stays continuous (no clicks).
    phases = [0.0] * len(weights)
    raw: list[float] = []
    peak = 1e-9
    for i in range(n_samples):
        t = i / sample_rate
        norm_t = i / max(1, n_samples - 1)
        s = _sample_curve(curve, norm_t)
        # Pitch rises with the score: base..~3x base.
        f0 = base_freq * (1.0 + 2.0 * s)
        # Brightness rises with the score too: lean on upper partials as we climb.
        bright = 0.5 + 0.5 * s
        sample = 0.0
        for k, w in enumerate(weights, start=1):
            fk = f0 * k
            if fk >= sample_rate / 2.0:  # past Nyquist -> skip (anti-alias)
                continue
            phases[k - 1] += 2.0 * math.pi * fk / sample_rate
            amp = w * (bright ** (k - 1))
            sample += amp * math.sin(phases[k - 1])
        sample *= _envelope(t, duration)
        raw.append(sample)
        a = abs(sample)
        if a > peak:
            peak = a

    # Normalize to int16 with a little headroom.
    norm = 0.92 / peak
    frames = bytearray()
    for sample in raw:
        v = int(max(-32767, min(32767, sample * norm * 32767)))
        frames += struct.pack("<h", v)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return Artifact("audio_wav", b64, label="sonification").finalize()


def audio_params(seed: int, palette: list[str], scores: list[float]) -> Artifact:
    """The synthesis recipe as JSON so a Web Audio frontend can re-synthesize live.

    Carries base_freq, partial weights, envelope timings, and a per-step pitch list that
    mirrors what ``sonify`` renders. Returns a finalized ``audio_params`` Artifact.
    """
    hue, light = _palette_stats(palette)
    weights = _partial_weights(seed, light, hue)
    base_freq, step_freqs = _step_freqs(palette, scores)
    curve = _score_curve(scores)
    params = {
        "schema": "studio-engine/sonify-params/1",
        "seed": int(seed),
        "base_freq": round(base_freq, 4),
        "partials": [
            {"harmonic": k, "weight": round(w, 6)}
            for k, w in enumerate(weights, start=1)
        ],
        "envelope": {"attack": 0.18, "release": 0.30, "curve": "linear"},
        "pitch_steps": [round(f, 4) for f in step_freqs],
        "scores": [round(s, 6) for s in curve],
        "palette": {"mean_hue": round(hue, 6), "mean_lightness": round(light, 6)},
        "waveform": "additive-sine",
    }
    return Artifact("audio_params", json.dumps(params), label="sonification-params").finalize()
