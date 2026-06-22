"""Web-Audio backend for the ear: turn the sonify recipe into a portable synth graph.

The baked WAV (organs.sonify) is an additive-sine sweep with phase integration, so it is NOT a
single closed-form expr — the audio channel is a *synth-graph spec*, not the strand AST. This
emitter maps the SAME sonify params that bake the WAV into oscillator nodes + a frequency
automation curve a Web-Audio frontend instantiates. Grounded by shared source: the graph's
partials/curve come from the very dict that renders the WAV (tests assert they agree).
"""
from __future__ import annotations

SCHEMA = "studio-engine/webaudio/1"


def emit_webaudio(audio_params: dict) -> dict:
    """sonify params -> {oscillators, base_freq, pitch_curve, envelope, schema}.

    `audio_params` is organs.sonify.audio_params(...).content, JSON-parsed. Raises ValueError on
    non-additive input (no partials) — the channel is defined as additive form (spec §13).
    """
    partials = audio_params.get("partials")
    if not partials:
        raise ValueError("non-additive audio_params: no partials to map to oscillators")
    oscillators = [
        {"harmonic": int(p["harmonic"]), "gain": float(p["weight"]), "phase": 0.0}
        for p in partials
    ]
    return {
        "schema": SCHEMA,
        "base_freq": float(audio_params.get("base_freq", 0.0)),
        "oscillators": oscillators,
        "pitch_curve": [float(f) for f in audio_params.get("pitch_steps", [])],
        "envelope": dict(audio_params.get("envelope", {})),
        "waveform": audio_params.get("waveform", "additive-sine"),
    }
