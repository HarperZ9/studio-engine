"""Interactive sessions -- the two-way, real-time cross-examination of the loop.

A Session holds live state (the parameter vector + corpus) and lets a human or a model
*steer* the refinement: take an auto step, inject parameters, or ask why an axis scores
what it does. This is the loop turned bidirectional -- the operator and the engine examine
the same candidate together, in real time. Stdlib only; reuses the engine's helpers.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .engine import _gens, _evaluate, _refine, _clamp, _CORPUS_PATH
from .organs import palette as pal, program as prog
from . import criteria as crit
from .corpus import Corpus
from .native_render import RenderParams, native_render

_WHY = {
    "novelty": "distance from the corpus -- vary the parameters or palette to differ from prior work",
    "objective": "a structural property -- the parameter must approach the criterion it did not author",
    "subjective": "a measured feature of the output -- adjust the parameters to shape it",
}


class Session:
    def __init__(self, seed: int = 0, generator: str = "phyllotaxis", scheme: str = "analogous",
                 target: float = 0.9, floor: float = 0.6, corpus_path: str | Path | None = _CORPUS_PATH):
        gens = _gens()
        if generator not in gens:
            raise ValueError(f"unknown generator {generator!r}; have {list(gens)}")
        self.seed = seed
        self.generator = generator
        self.spec = gens[generator]
        self.target = target
        self.floor = floor
        rng = (seed * 2654435761 + 12345) & 0xFFFFFFFF
        self.palette = pal.generate_palette(seed, n=6, scheme=scheme)
        self.corpus = Corpus.load(corpus_path)
        self.params = _clamp(self.spec, self.spec["params0"](rng))
        self.history: list[dict] = []
        self.n = 0
        self.frac = 0.34
        # Two-way NATIVE render loop (afferent superhuman channels). last_camera
        # is the previous view; the next re-render reuses it as prev_* so the
        # native motion channel is real. None until the first render.
        self.last_camera: dict | None = None
        self.render_history: list[dict] = []
        self._record("perceive", "rough draft")

    def _eval(self):
        return _evaluate(self.spec, self.params, self.palette, self.corpus)

    def _record(self, phase: str, note: str) -> dict:
        _, margins, coh = self._eval()
        weakest = min(margins, key=lambda a: margins[a])
        entry = {
            "index": self.n, "phase": phase,
            "params": {p: round(v, 4) for p, v in self.params.items()},
            "margins": {a: round(v, 4) for a, v in margins.items()},
            "cohesion": round(coh, 4), "weakest": weakest, "note": note,
            "converged": coh >= self.target and all(s >= self.floor for s in margins.values()),
        }
        self.history.append(entry)
        self.n += 1
        return entry

    def step(self) -> dict:
        """Auto-refine one iteration toward the weakest axis."""
        nxt, improved = _refine(self.spec, self.params, self.palette, self.corpus, self.frac)
        if not improved:
            self.frac *= 0.55
        self.params = nxt
        return self._record("refine", "auto-refine toward weakest" if improved else "no gain; step shrunk")

    def inject(self, overrides: dict | None) -> dict:
        """Operator steers: override one or more parameters (clamped to bounds)."""
        ov = {k: float(v) for k, v in (overrides or {}).items() if k in self.spec["bounds"]}
        self.params = _clamp(self.spec, {**self.params, **ov})
        return self._record("generate", f"operator inject: {sorted(ov) or 'none'}")

    def render_step(self, params: dict | None = None, *, binary: str | None = None) -> dict:
        """The ACTIVE two-way render: the model requests a native re-render with
        a chosen view, receives the superhuman channels + witnessed certificate,
        and can steer the next one. If the previous render's camera is known and
        the caller did not pass an explicit previous camera, we feed it as prev_*
        so the native motion channel reflects the real view change.

        Returns a step dict carrying the native result (certificate + channel
        summaries). Honest: when the binary is absent the step says so and no
        channels are fabricated. Records into the session history so the
        certificate round-trips alongside the refine trajectory.
        """
        rp = RenderParams.from_dict(params)
        if self.last_camera and rp.prev_eye is None and rp.prev_target is None and rp.prev_up is None:
            rp.prev_eye = tuple(self.last_camera["eye"])
            rp.prev_target = tuple(self.last_camera["target"])
            rp.prev_up = tuple(self.last_camera["up"])
        res = native_render(rp, binary=binary)
        if res.ok and res.camera:
            self.last_camera = {"eye": res.camera["eye"], "target": res.camera["target"],
                                "up": res.camera["up"]}
        verdict = (res.certificate or {}).get("verdict")
        note = "native channels perceived" if res.ok else f"native render unavailable: {res.reason}"
        entry = {
            "index": self.n, "phase": "perceive", "kind": "native-render",
            "params": rp.to_dict(), "available": res.available, "ok": res.ok,
            "reason": res.reason, "verdict": verdict,
            "certificate": res.certificate, "channels": res.channels,
            "camera": res.camera, "note": note,
        }
        self.render_history.append(entry)
        self.history.append(entry)
        self.n += 1
        return entry

    def explain(self, axis: str | None = None) -> dict:
        """Cross-examine: why does this axis score what it does, and what would move it?"""
        _, margins, coh = self._eval()
        ax = axis if axis in margins else min(margins, key=lambda a: margins[a])
        k = "novelty" if ax == "novelty" else crit.kind(ax)
        return {"axis": ax, "score": round(margins[ax], 4), "kind": k,
                "tag": crit.tag(margins[ax], self.target, self.floor), "cohesion": round(coh, 4),
                "why": _WHY.get(k, ""), "all_margins": {a: round(v, 4) for a, v in margins.items()}}

    def program(self):
        """The current candidate's live RenderProgram -- render the steered candidate as you examine it."""
        spec = self.spec
        if spec["field"] is not None:
            return prog.field_program(self.generator, spec["expr"](self.params), self.palette,
                                      spec["t0"](self.params), spec["animatable"], spec["period"](self.params))
        return prog.point_program(self.generator, spec["recipe"](self.params), self.palette)

    def state(self) -> dict:
        _, margins, coh = self._eval()
        return {
            "generator": self.generator, "seed": self.seed,
            "params": {p: round(v, 4) for p, v in self.params.items()}, "palette": self.palette,
            "margins": {a: round(v, 4) for a, v in margins.items()}, "cohesion": round(coh, 4),
            "weakest": min(margins, key=lambda a: margins[a]),
            "converged": coh >= self.target and all(s >= self.floor for s in margins.values()),
            "steps": self.n, "history": self.history,
            "program": asdict(self.program()),
            "native_renders": self.render_history, "last_camera": self.last_camera,
        }
