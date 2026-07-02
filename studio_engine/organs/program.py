"""Assemble RenderProgram / AudioProgram from strand -- the portable, drop-in render the chamber runs.

Fields become a self-contained WebGL1 fragment whose `field()` body IS the emitted strand expr
(so the pixels are the verified math); points become a JSON recipe. Audio becomes a synth graph
from the same sonify params that bake the WAV. value_range is engine-sampled so coloring matches
the witnessed range.
"""
from __future__ import annotations

import json

from ..model import RenderProgram, AudioProgram, _sha
from ..strand import expr as ex
from ..strand import glsl
from ..strand import webaudio
from . import sonify as snd


def fragment_source(expr_src: str, n_colors: int) -> str:
    """A complete WebGL1 (GLSL ES 1.00) fragment: field() == the expr, mapped onto the palette ramp.

    Dynamic palette indexing is done via a constant-bound loop (portable on WebGL1), so the
    shipped shader compiles as-is. The host sets u_resolution / u_time / u_palette / u_value_range.
    """
    n = max(2, n_colors)
    return f"""precision highp float;
uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_value_range;
uniform vec3 u_palette[{n}];
{glsl.GLSL_HELPERS}
float field(float u, float v, float t){{ return {expr_src}; }}
vec3 ramp(float x){{
  x = clamp(x, 0.0, 1.0);
  float s = x * float({n} - 1);
  int idx = int(floor(s));
  float f = fract(s);
  vec3 a = u_palette[0];
  vec3 b = u_palette[0];
  for (int k = 0; k < {n}; k++) {{
    if (k == idx) a = u_palette[k];
    if (k == idx + 1) b = u_palette[k];
  }}
  return mix(a, b, f);
}}
void main(){{
  vec2 uv = (gl_FragCoord.xy / u_resolution) * 2.0 - 1.0;
  float val = field(uv.x, uv.y, u_time);
  float n = (val - u_value_range.x) / max(1e-6, (u_value_range.y - u_value_range.x));
  gl_FragColor = vec4(ramp(n), 1.0);
}}"""


def field_program(generator: str, e: ex.Expr, palette: list, t0: float,
                  animatable: bool, period: float, samples: int = 24) -> RenderProgram:
    """Build a glsl-fragment RenderProgram from a field expr.

    value_range is sampled across the WHOLE loop (every K-th frame over [0, period)) for animatable
    fields, so the shipped coloring covers what the chamber actually renders as u_time sweeps -- not
    just a single t0 slice. Non-animatable fields sample at t0.
    """
    src = glsl.emit_glsl(e)
    if animatable and period > 0:
        vals = [v for k in range(8) for v in ex.sample_field(e, samples, period * k / 8)]
    else:
        vals = ex.sample_field(e, samples, t0)
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        hi = lo + 1e-6
    return RenderProgram(
        target="glsl-fragment", generator=generator,
        source=fragment_source(src, len(palette)),
        uniforms={
            "u_time": {"type": "float", "default": round(t0, 6)},
            "u_resolution": {"type": "vec2"},
            "u_palette": {"type": "vec3[]", "value": palette},
            "u_value_range": {"type": "vec2", "value": [round(lo, 6), round(hi, 6)]},
        },
        domain={"u": [-1.0, 1.0], "v": [-1.0, 1.0], "t": [0.0, round(period, 6)],
                "animatable": animatable, "period": round(period, 6)},
        value_range=[round(lo, 6), round(hi, 6)],
        color={"mode": "ramp", "stops": len(palette)},
        expr_sha256=ex.sha(e),
        expr_ast=ex.to_dict(e),   # exact tree so a headless renderer can re-hash + tamper-check
        notes="WebGL1 fragment; field() is the verified strand expr; animate u_time in [0, period).",
    )


def point_program(generator: str, recipe: dict, palette: list) -> RenderProgram:
    """Build a point-recipe RenderProgram; the recipe reproduces the engine's verified points."""
    return RenderProgram(
        target="point-recipe", generator=generator, recipe=recipe,
        uniforms={"u_palette": {"type": "vec3[]", "value": palette}},
        domain={"animatable": False},
        color={"mode": "index", "stops": len(palette)},
        expr_sha256=_sha(json.dumps(recipe, sort_keys=True)),
        notes="run the recipe (spiral|iterated|parametric); color each point by index across palette.",
    )


def audio_program(seed: int, palette: list, scores: list, wav_url: str = "") -> AudioProgram:
    """Build the ear's synth graph from the same sonify params that bake the WAV."""
    ap = json.loads(snd.audio_params(seed, palette, scores).content)
    g = webaudio.emit_webaudio(ap)
    return AudioProgram(
        oscillators=g["oscillators"], base_freq=g["base_freq"], pitch_curve=g["pitch_curve"],
        envelope=g["envelope"], waveform=g["waveform"],
        expr_sha256=_sha(json.dumps(ap, sort_keys=True)), wav_url=wav_url,
    )
