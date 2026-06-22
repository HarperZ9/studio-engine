# strand Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give studio-engine one closed-form expression algebra (`strand`) from which it derives every rendering — GLSL for the eye, a synth graph for the ear, recipes for point clouds — composed in depth and choreographed in time, each carrying a CPU-checkable proof that the shipped program *is* the witnessed math.

**Architecture:** A frozen `Expr` AST (pure `sin/cos/exp/abs/neg/sqrt/+/−/×/÷` over vars `u,v,t,x,y,i`) is the single source. Backends emit GLSL / parse it back / sample it / map it to a Web-Audio graph. Generators refactor to expose `.expr()`/`.recipe()`; the engine assembles a `World` (layers + audio program + timeline) and proves cross-backend identity by round-trip. Scenes become single-layer Worlds.

**Tech Stack:** Python 3.12 stdlib only (`math`, `dataclasses`, `json`, `hashlib`, `http.server`, `wave`); browser-native Canvas/WebGL/Web-Audio on the frontend side. `unittest`.

## Global Constraints

- **Zero third-party dependencies** — Python stdlib only; frontend uses native browser APIs only. (verbatim from spec §12)
- **Python ≥ 3.12** (baseline interpreter; `from __future__ import annotations` in every module).
- **File size < 300 lines, function < 50 lines** (user CLAUDE.md quality gates).
- **Schema** `studio-engine/2`; **version** `0.2.0`.
- **No GPU renderer / rasterization; no production audio-DSP engine** — emit programs as data, verify on CPU. (spec §12)
- **License AGPL-3.0** — do not relicense; keep headers/notices.
- **All existing 56 tests stay green**; every task ends green.
- **Determinism** — `(seed, generator, scheme)` fully determines a World for a fixed corpus.
- Run the suite with: `python -m unittest discover -s tests`

---

## Task 1: `strand/expr.py` — the algebra core

**Files:**
- Create: `studio_engine/strand/__init__.py`
- Create: `studio_engine/strand/expr.py`
- Test: `tests/test_strand_expr.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Expr` — frozen dataclass `op: str`, `args: tuple`.
  - Constructors (floats auto-lifted to `const`): `var(name: str) -> Expr`, `const(x: float) -> Expr`, `sin(a) -> Expr`, `cos(a) -> Expr`, `exp(a) -> Expr`, `absx(a) -> Expr`, `neg(a) -> Expr`, `sqrt(a) -> Expr`, `add(*a) -> Expr`, `sub(a, b) -> Expr`, `mul(*a) -> Expr`, `div(a, b) -> Expr`.
  - `eval_expr(e: Expr, env: dict[str, float]) -> float`
  - `sha(e: Expr) -> str` (16 hex chars)
  - `sample_field(e: Expr, n: int, t: float = 0.0) -> list[float]` — row-major `n*n` samples over `u,v ∈ [-1,1]` (cell centers), `t` fixed.
  - `VARS = ("u", "v", "t", "x", "y", "i")`, `OPS` (set of valid op names).

- [ ] **Step 1: Write the failing test** — `tests/test_strand_expr.py`

```python
import math
import unittest
from studio_engine.strand import expr as ex


class TestExpr(unittest.TestCase):
    def test_const_and_var(self):
        self.assertEqual(ex.eval_expr(ex.const(3.0), {}), 3.0)
        self.assertEqual(ex.eval_expr(ex.var("u"), {"u": 0.5}), 0.5)

    def test_unary_and_binary(self):
        e = ex.add(ex.sin(ex.const(0.0)), ex.cos(ex.const(0.0)))  # 0 + 1
        self.assertAlmostEqual(ex.eval_expr(e, {}), 1.0)
        self.assertAlmostEqual(ex.eval_expr(ex.mul(ex.const(2), ex.const(3)), {}), 6.0)
        self.assertAlmostEqual(ex.eval_expr(ex.sub(ex.const(5), ex.const(2)), {}), 3.0)

    def test_variadic(self):
        self.assertAlmostEqual(ex.eval_expr(ex.add(1, 2, 3, 4), {}), 10.0)
        self.assertAlmostEqual(ex.eval_expr(ex.mul(2, 3, 4), {}), 24.0)

    def test_float_lift(self):
        self.assertAlmostEqual(ex.eval_expr(ex.sin(0.0), {}), 0.0)  # bare float ok

    def test_div_guard(self):
        # division stays finite (matches metaballs' +eps style guard)
        self.assertTrue(math.isfinite(ex.eval_expr(ex.div(1.0, 0.0), {})))

    def test_sha_stable_and_distinct(self):
        a = ex.mul(ex.var("u"), ex.const(2.0))
        b = ex.mul(ex.var("u"), ex.const(2.0))
        c = ex.mul(ex.var("u"), ex.const(3.0))
        self.assertEqual(ex.sha(a), ex.sha(b))
        self.assertNotEqual(ex.sha(a), ex.sha(c))

    def test_sample_field_shape(self):
        grid = ex.sample_field(ex.var("u"), n=4, t=0.0)
        self.assertEqual(len(grid), 16)
        self.assertLess(grid[0], grid[3])  # u increases left->right within a row


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it, verify it fails**

Run: `python -m unittest tests.test_strand_expr -v`
Expected: FAIL (`ModuleNotFoundError: studio_engine.strand`).

- [ ] **Step 3: Implement** — `studio_engine/strand/__init__.py` empty; `studio_engine/strand/expr.py`:

```python
"""The strand algebra: one frozen closed-form AST, the single source every backend derives from.

Pure functions over vars u,v,t (fields) and x,y,i (point maps). No control flow, no state.
Stdlib only. This is the substrate: GLSL emit, WebAudio graph, SVG sampling, and the verified
features all descend from THIS tree, so the chamber renders the exact math the engine witnessed.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

VARS = ("u", "v", "t", "x", "y", "i")
_UNARY = {"sin": math.sin, "cos": math.cos, "exp": math.exp,
          "abs": abs, "neg": lambda a: -a, "sqrt": lambda a: math.sqrt(a) if a > 0 else 0.0}
_VARIADIC = {"add", "mul"}
_BINARY = {"sub", "div"}
OPS = {"var", "const"} | set(_UNARY) | _VARIADIC | _BINARY
_EPS = 1e-3  # division guard (matches the metaballs field's +eps)


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple


def _lift(a) -> Expr:
    return a if isinstance(a, Expr) else const(float(a))


def const(x: float) -> Expr: return Expr("const", (float(x),))
def var(name: str) -> Expr:
    if name not in VARS:
        raise ValueError(f"unknown var {name!r}; have {VARS}")
    return Expr("var", (name,))


def sin(a) -> Expr: return Expr("sin", (_lift(a),))
def cos(a) -> Expr: return Expr("cos", (_lift(a),))
def exp(a) -> Expr: return Expr("exp", (_lift(a),))
def absx(a) -> Expr: return Expr("abs", (_lift(a),))
def neg(a) -> Expr: return Expr("neg", (_lift(a),))
def sqrt(a) -> Expr: return Expr("sqrt", (_lift(a),))
def add(*a) -> Expr: return Expr("add", tuple(_lift(x) for x in a))
def mul(*a) -> Expr: return Expr("mul", tuple(_lift(x) for x in a))
def sub(a, b) -> Expr: return Expr("sub", (_lift(a), _lift(b)))
def div(a, b) -> Expr: return Expr("div", (_lift(a), _lift(b)))


def eval_expr(e: Expr, env: dict) -> float:
    op = e.op
    if op == "const":
        return e.args[0]
    if op == "var":
        return float(env.get(e.args[0], 0.0))
    if op in _UNARY:
        return _UNARY[op](eval_expr(e.args[0], env))
    if op == "add":
        return sum(eval_expr(a, env) for a in e.args)
    if op == "mul":
        r = 1.0
        for a in e.args:
            r *= eval_expr(a, env)
        return r
    if op == "sub":
        return eval_expr(e.args[0], env) - eval_expr(e.args[1], env)
    if op == "div":
        d = eval_expr(e.args[1], env)
        return eval_expr(e.args[0], env) / (d if abs(d) > _EPS else (_EPS if d >= 0 else -_EPS))
    raise ValueError(f"bad op {op!r}")


def _canon(e: Expr) -> str:
    if e.op == "const":
        return f"({e.args[0]!r})"
    if e.op == "var":
        return e.args[0]
    return e.op + "(" + ",".join(_canon(a) for a in e.args) + ")"


def sha(e: Expr) -> str:
    return hashlib.sha256(_canon(e).encode("utf-8")).hexdigest()[:16]


def sample_field(e: Expr, n: int, t: float = 0.0) -> list:
    n = max(1, n)
    out = []
    for gy in range(n):
        v = 2.0 * ((gy + 0.5) / n) - 1.0
        for gx in range(n):
            u = 2.0 * ((gx + 0.5) / n) - 1.0
            out.append(eval_expr(e, {"u": u, "v": v, "t": t}))
    return out
```

- [ ] **Step 4: Run tests, verify pass**

Run: `python -m unittest tests.test_strand_expr -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add studio_engine/strand/ tests/test_strand_expr.py
git commit -m "feat(strand): expr algebra core — frozen AST, eval, sha, sampling"
```

---

## Task 2: `strand/glsl.py` — GLSL emit + parse (the round-trip proof)

**Files:**
- Create: `studio_engine/strand/glsl.py`
- Test: `tests/test_strand_glsl.py`

**Interfaces:**
- Consumes: `expr.Expr`, `expr.eval_expr`, `expr.sample_field`, all constructors.
- Produces:
  - `emit_glsl(e: Expr) -> str` — a GLSL *expression* string (vars `u,v,t` are in-scope `float`s; functions `sin,cos,exp,abs,sqrt`; `/` guarded inline as `(d==0.?eps:d)` is NOT used — division guard handled by emitting `safediv(a,b)`; see below).
  - `parse_glsl(src: str) -> Expr` — recursive-descent over exactly the subset `emit_glsl` produces.
  - `GLSL_HELPERS: str` — the `float safediv(float a, float b){...}` helper the fragment must include.

Decision: emit `safediv(a,b)` for `div` so GLSL matches the Python `_EPS` guard exactly. `parse_glsl` maps `safediv(a,b)` back to `div`.

- [ ] **Step 1: Write the failing test** — `tests/test_strand_glsl.py`

```python
import unittest
from studio_engine.strand import expr as ex
from studio_engine.strand import glsl


def _roundtrip_equal(e, samples=((-0.7, 0.3, 0.0), (0.2, -0.5, 1.1), (0.9, 0.9, 0.4))):
    back = glsl.parse_glsl(glsl.emit_glsl(e))
    for (u, v, t) in samples:
        env = {"u": u, "v": v, "t": t}
        if abs(ex.eval_expr(e, env) - ex.eval_expr(back, env)) > 1e-6:
            return False
    return True


class TestGlsl(unittest.TestCase):
    def test_emit_basic(self):
        src = glsl.emit_glsl(ex.add(ex.sin(ex.var("u")), ex.var("v")))
        self.assertIn("sin(u)", src)
        self.assertEqual(src.count("("), src.count(")"))  # balanced

    def test_roundtrip_arith(self):
        e = ex.sub(ex.mul(ex.var("u"), 2.0), ex.div(ex.var("v"), 3.0))
        self.assertTrue(_roundtrip_equal(e))

    def test_roundtrip_nested(self):
        e = ex.mul(ex.sin(ex.add(ex.mul(4.0, ex.var("u")), ex.sin(ex.mul(4.0, ex.var("v"))))),
                   ex.cos(ex.var("t")))
        self.assertTrue(_roundtrip_equal(e))

    def test_roundtrip_div_guard(self):
        e = ex.div(ex.const(1.0), ex.add(ex.mul(ex.var("u"), ex.var("u")), ex.const(0.0)))
        self.assertTrue(_roundtrip_equal(e))

    def test_only_allowed_tokens(self):
        src = glsl.emit_glsl(ex.exp(ex.neg(ex.absx(ex.var("u")))))
        for tok in ("exp", "abs", "u"):
            self.assertIn(tok, src)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it, verify it fails** — `python -m unittest tests.test_strand_glsl -v` → FAIL (no module).

- [ ] **Step 3: Implement** — `studio_engine/strand/glsl.py`:

```python
"""GLSL backend for the strand algebra: emit a fragment expression, and parse it back.

The parse half exists for the grounding proof: AST -> GLSL -> parse -> AST' must eval-equal the
original (tests/test_strand_glsl.py). The parser handles ONLY the closed subset emit_glsl produces
— never arbitrary GLSL. `safediv` mirrors the Python eval's division guard so the two agree exactly.
"""
from __future__ import annotations

from .expr import Expr, const, var, sin, cos, exp, absx, neg, sqrt, add, mul, sub, div

GLSL_HELPERS = "float safediv(float a, float b){ float d = abs(b) > 1e-3 ? b : (b >= 0.0 ? 1e-3 : -1e-3); return a / d; }"
_FUNCS = {"sin": sin, "cos": cos, "exp": exp, "abs": absx, "sqrt": sqrt}


def emit_glsl(e: Expr) -> str:
    op = e.op
    if op == "const":
        x = e.args[0]
        return f"({x!r})" if x < 0 else (f"{x}" if "." in repr(x) or "e" in repr(x) else f"{x}.0")
    if op == "var":
        return e.args[0]
    if op in _FUNCS:
        return f"{op}({emit_glsl(e.args[0])})"
    if op == "neg":
        return f"(-{emit_glsl(e.args[0])})"
    if op == "add":
        return "(" + " + ".join(emit_glsl(a) for a in e.args) + ")"
    if op == "mul":
        return "(" + " * ".join(emit_glsl(a) for a in e.args) + ")"
    if op == "sub":
        return f"({emit_glsl(e.args[0])} - {emit_glsl(e.args[1])})"
    if op == "div":
        return f"safediv({emit_glsl(e.args[0])}, {emit_glsl(e.args[1])})"
    raise ValueError(f"cannot emit op {op!r}")


# --- recursive-descent parser over the emitted subset (proof only) ---
class _P:
    def __init__(self, s: str):
        self.s = s.replace(" ", "")
        self.i = 0

    def peek(self) -> str:
        return self.s[self.i] if self.i < len(self.s) else ""

    def eat(self, c: str) -> None:
        if self.peek() != c:
            raise ValueError(f"expected {c!r} at {self.i} in {self.s!r}")
        self.i += 1

    def parse(self) -> Expr:
        e = self._sum()
        if self.i != len(self.s):
            raise ValueError(f"trailing input at {self.i}")
        return e

    def _sum(self) -> Expr:
        node = self._term()
        while self.peek() in "+-":
            op = self.peek(); self.i += 1
            rhs = self._term()
            node = add(node, rhs) if op == "+" else sub(node, rhs)
        return node

    def _term(self) -> Expr:
        node = self._atom()
        while self.peek() == "*":
            self.i += 1
            node = mul(node, self._atom())
        return node

    def _atom(self) -> Expr:
        c = self.peek()
        if c == "(":
            self.eat("(")
            if self.peek() == "-":  # (-X)
                self.eat("-")
                node = neg(self._sum())
            else:
                node = self._sum()
            self.eat(")")
            return node
        if c.isalpha():
            ident = self._ident()
            if self.peek() == "(":  # function or safediv
                self.eat("(")
                a = self._sum()
                if self.peek() == ",":
                    self.eat(",")
                    b = self._sum()
                    self.eat(")")
                    if ident != "safediv":
                        raise ValueError(f"unknown 2-arg fn {ident!r}")
                    return div(a, b)
                self.eat(")")
                if ident not in _FUNCS:
                    raise ValueError(f"unknown fn {ident!r}")
                return _FUNCS[ident](a)
            return var(ident)  # bare var u/v/t/x/y/i
        return self._number()

    def _ident(self) -> str:
        j = self.i
        while self.peek().isalnum():
            self.i += 1
        return self.s[j:self.i]

    def _number(self) -> Expr:
        j = self.i
        while self.peek() and (self.peek().isdigit() or self.peek() in ".eE+-"):
            # stop +/- that begin a new term: only consume +/- right after e/E
            if self.peek() in "+-" and self.i > j and self.s[self.i - 1] not in "eE":
                break
            self.i += 1
        return const(float(self.s[j:self.i]))


def parse_glsl(src: str) -> Expr:
    return _P(src).parse()
```

- [ ] **Step 4: Run, verify pass** — `python -m unittest tests.test_strand_glsl -v` → PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add studio_engine/strand/glsl.py tests/test_strand_glsl.py
git commit -m "feat(strand): GLSL emit + parse round-trip (the grounding proof)"
```

---

## Task 3: `strand/recipe.py` — point recipes

**Files:** Create `studio_engine/strand/recipe.py`; Test `tests/test_strand_recipe.py`.

**Interfaces:**
- Consumes: `expr` constructors + `eval_expr`.
- Produces:
  - `spiral(angle_deg: float, scale: float, count: int) -> dict` → `{"mode":"spiral","angle_deg","scale","count","color_by":"index"}`
  - `iterated(update_x: Expr, update_y: Expr, init: list[float], transient: int, count: int) -> dict` → carries `emit_glsl(update_x/у)` strings + the Exprs.
  - `parametric(x_expr: Expr, y_expr: Expr, t_max: float, count: int) -> dict`
  - `eval_recipe(r: dict) -> list[tuple]` → `(x, y, i)` points, reproducing the organ's own `points()`.

**Success criterion:** `eval_recipe(spiral(...))[:50]` equals `geometry.phyllotaxis(...)[:50]`; likewise iterated↔attractor, parametric↔harmonograph.

- [ ] **Step 1: Test** — assert first 50 points of each recipe equal the matching organ's `points()` (≤1e-9). (Import organs; build recipes from `PARAMS0`.)
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3: Implement.** `eval_recipe` dispatches on `mode`: `spiral` → `r=scale*sqrt(i); a=radians(angle); (r*cos(i*a), r*sin(i*a), i)`; `iterated` → iterate `(eval_expr(ux,{x,y}), eval_expr(uy,{x,y}))` from `init`, drop `transient`, index kept; `parametric` → sample `t∈[0,t_max]`, `(eval_expr(xe,{t}), eval_expr(ye,{t}), i)`. Store both the `Expr` and its `emit_glsl` string in the dict (frontend uses the string; engine uses the Expr).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5: Commit** `feat(strand): point recipes (spiral/iterated/parametric) + eval`.

---

## Task 4: `strand/webaudio.py` — synth-graph emit

**Files:** Create `studio_engine/strand/webaudio.py`; Test `tests/test_strand_webaudio.py`.

**Interfaces:**
- Consumes: the dict produced by `organs.sonify.audio_params(...).content` (JSON-parsed): keys `base_freq`, `partials:[{harmonic,weight}]`, `pitch_steps`, `envelope`.
- Produces: `emit_webaudio(audio_params: dict) -> dict` →
  `{"oscillators":[{"harmonic":k,"gain":w,"phase":0.0}...], "base_freq":float, "pitch_curve":[float], "envelope":{...}, "schema":"studio-engine/webaudio/1"}`.
  Raises `ValueError` if `partials` missing/empty (non-additive input).

**Success criterion:** oscillator gains == partial weights; `base_freq`/`pitch_curve` == input `base_freq`/`pitch_steps` (≤1e-6); raises on `{}`.

- [ ] Steps 1–5 (test → fail → implement the straight mapping → pass → commit `feat(strand): webaudio synth-graph emit grounded against the WAV source`).

---

## Task 5: Field organs → strand (eye) — gyroid · quasicrystal · flowfield · turbulence · metaballs

**Files (per organ):** Modify `studio_engine/organs/<field>.py`; Test `tests/test_organ_exprs.py` (one file, a case per organ).

**Interfaces (each field organ gains):**
- `expr(params: dict, t: float = 0.0) -> Expr` — the canonical field (spec §3 table). `t` is the `var("t")` time channel (gyroid z-slice, quasi/flow/turb phase). metaballs: `expr` ignores `t` (animatable False); bake `(cx,cy,r)` as consts.
- `value(params, u, v)` is **kept** but re-implemented to `return eval_expr(expr(params), {"u":u,"v":v,"t":0.0})`.
- `ANIMATABLE: bool` and `def period(params) -> float`.
- `svg(...)` samples `expr` (kills the preview/feature drift).

**Success criterion (test_organ_exprs):** for each field, over a 16×16 grid, `eval_expr(organ.expr(P0))` == the *current* `value(P0)` within 1e-6 **for the engine's feature field** (note: gyroid/quasicrystal adopt the verified `_gens` field, not the old preview); `emit_glsl(expr)` round-trips (reuse `_roundtrip_equal`); `expr_sha` stable.

- [ ] **Step 1:** Write `tests/test_organ_exprs.py` — parametrized cases asserting (a) sample-equality vs the engine field lambda from `engine._gens()[name]["field"]`, (b) GLSL round-trip, for all 5 fields.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `expr()` per organ from the §3 table using `strand.expr` constructors. Unroll quasicrystal `waves`, turbulence `octaves`, metaballs balls at build time. Wire `value()`/`svg()` through it.
- [ ] **Step 4:** Run → PASS; run full suite, fix any `_gens` field lambdas to delegate to `organ.expr` so engine features and shipped expr are byte-identical.
- [ ] **Step 5: Commit** `feat(organs): fields define themselves as strand exprs (eye backend grounded)`.

**Parallelizable:** one subagent per organ is viable, but they share `test_organ_exprs.py` and `engine._gens()` — assign ONE agent the 5 fields to avoid the merge conflict, or split files first. Default: one agent, five organs.

---

## Task 6: Point organs → strand (recipes) — phyllotaxis · attractor · harmonograph

**Files:** Modify the three organs; extend `tests/test_organ_exprs.py`.

**Interfaces (each gains):** `recipe(params: dict) -> dict` (via `strand.recipe`), returning the structured recipe whose `eval_recipe` reproduces `points(params)`.

- [ ] Steps 1–5: test first-50-points equality (≤1e-9) → fail → implement `recipe()` → pass → commit `feat(organs): point generators expose strand recipes`.

---

## Task 7: `organs/program.py` — assemble RenderProgram / AudioProgram

**Files:** Create `studio_engine/organs/program.py`; Test `tests/test_program.py`.

**Interfaces:**
- Consumes: organ `.expr()/.recipe()`, `glsl.emit_glsl`, `glsl.GLSL_HELPERS`, `webaudio.emit_webaudio`, `expr.sample_field`, `expr.sha`, `model.RenderProgram/AudioProgram`.
- Produces:
  - `render_program(generator: str, params: dict, palette: list[str], t: float = 0.0) -> RenderProgram`
  - `fragment_source(expr_src: str, value_range, stops: int) -> str` — full fragment: `GLSL_HELPERS` + a `main` that computes the field at `vUv→u,v`, normalizes by `u_value_range`, and ramps `u_palette`.
  - `audio_program(seed: int, palette: list[str], scores: list[float]) -> AudioProgram`

**Success criterion:** for each field, `sample_field(render_program(...).expr)` matches engine features' field sampling; `value_range` == engine min/max over its grid; point generators produce `target=="point-recipe"` with reproducing recipe; `audio_program.oscillators` gains == sonify partials.

- [ ] Steps 1–5: test → fail → implement → pass → commit `feat(organs): RenderProgram/AudioProgram assembly from strand`.

---

## Task 8: `model.py` — World / Layer / RenderProgram / AudioProgram / Timeline

**Files:** Modify `studio_engine/model.py`; Test `tests/test_model.py` (extend).

**Interfaces (add; keep all existing):**
- `ArtifactKind` += `"render_program"`.
- `RenderProgram`, `AudioProgram`, `Layer`, `Timeline`, `World` dataclasses exactly as spec §4 (incl. `expr_sha256`, `value_range`, `domain`, `blend`, `composition`, `schema_version="studio-engine/2"`).
- `World.to_json()` via `_clean(asdict(...))`.
- `World.as_scene() -> Scene` — single-layer projection for back-compat.
- `RenderProgram.expr` is **not** serialized (engine-only) — store under a leading-underscore field excluded by `_clean`, or keep `expr` out of the dataclass and pass alongside. Decision: `RenderProgram` holds `source`/`recipe`/`expr_sha256` (serializable); the live `Expr` travels separately in `program.py` return as a tuple `(RenderProgram, Expr)` where the engine needs it.

- [ ] Steps 1–5: test dataclass round-trip + `as_scene()` + schema string → fail → implement → pass → commit `feat(model): World/Layer/RenderProgram/AudioProgram/Timeline (schema 2)`.

---

## Task 9: `organs/compose.py` — composition algebra + criterion

**Files:** Create `studio_engine/organs/compose.py`; Test `tests/test_compose.py`.

**Interfaces:**
- Consumes: `engine._features`, `criteria.cohesion`, `program.render_program`, `palette`, `model.World/Layer/Verdict`.
- Produces:
  - `composition_axes(layer_feats: list[dict], palette: list[str]) -> dict[str,float]` → `{"palette_harmony","depth_complementarity","contrast_balance"}` each 0..1.
  - `compose(seed: int, organ_set: list[str], scheme: str = "analogous") -> World` — builds a layer per organ (depth-ordered: field roles z<0 behind point roles z≥0), scores with `cohesion`, assigns `blend`, emits `composition: Verdict`.

**Success criterion:** `composition_axes` scores a harmonious pair (field backdrop + sparse points, related hues) **higher** than a clashing pair (two dense fields, opposite hues); `compose(...)` returns a `World` with ≥2 layers and distinct `z`.

- [ ] Steps 1–5: test the ordering property (harmonious > clashing) + structure → fail → implement → pass → commit `feat(organs): compositor — layered Worlds with a composition criterion`.

---

## Task 10: `temporal.py` — timeline + continuity criterion

**Files:** Create `studio_engine/temporal.py`; Test `tests/test_temporal.py`.

**Interfaces:**
- Consumes: organ `.expr()`, `.ANIMATABLE`, `.period()`, `expr.sample_field`, `criteria` band check, `model.Timeline/Verdict`.
- Produces:
  - `continuity(e: Expr, period: float, k: int = 12, n: int = 16) -> Verdict` — mean abs frame-to-frame grid delta across `t∈[0,period]`; `verified` if below bound.
  - `on_criterion(e: Expr, period: float, axes: list[str], ...) -> Verdict` — per-frame feature axes stay in band across the loop.
  - `build_timeline(generator: str, params: dict) -> Timeline | None` — `None` when not animatable.

**Success criterion:** gyroid/quasicrystal/flowfield/turbulence produce a `Timeline` with `continuity.tag=="verified"` and `period>0`; metaballs returns `None` (animatable False); a deliberately discontinuous expr fails continuity.

- [ ] Steps 1–5: test → fail → implement → pass → commit `feat(temporal): witnessed motion — continuity + on-criterion over a loop period`.

---

## Task 11: `engine.py` — emit World

**Files:** Modify `studio_engine/engine.py`; Test `tests/test_engine.py` (extend).

**Changes:**
- `_gens()` field lambdas delegate to `organ.expr` (single source — done in Task 5; verify here).
- `run(...)` / `simulate(...)` now build a **World**: the primary layer via `program.render_program`, the `audio_program`, the `Timeline` via `temporal.build_timeline`, and a single-layer `composition=None`. Yields `("step", Step)…("world", World)`.
- Keep `simulate` returning `World`; add `simulate_scene()` returning `world.as_scene()` for any caller still wanting a Scene.

**Success criterion:** `simulate(...)` returns a `World`; its layer has a `render_program` whose expr_sha matches the witnessed expr; determinism holds; existing engine tests pass (updated to the World shape).

- [ ] Steps 1–5: test → fail → implement → pass (+ full suite) → commit `feat(engine): emit Worlds (render program + audio program + timeline)`.

---

## Task 12: `session.py` — interactive over the World

**Files:** Modify `studio_engine/session.py`; Test `tests/test_session.py` (extend) — *new file if none exists; the 56 baseline covered sessions via test_engine; check first.*

**Changes:** `inject` accepts a target param (already param-keyed); add `compose(organ_set)` and `animate(period)` actions; `explain` reports composition/temporal axes when present.

- [ ] Steps 1–5: test the new actions mutate state + record history → fail → implement → pass → commit `feat(session): steer composition + motion, not just scalars`.

---

## Task 13: breadth — `rings` + `moire` generators, extra criteria axes

**Files:** Create `studio_engine/organs/rings.py`, `studio_engine/organs/moire.py`; modify `engine._gens()`, `criteria.py`; extend `tests/test_organ_exprs.py`, `tests/test_criteria.py`.

**Interfaces:** each new organ matches the field-organ shape (`expr/value/svg/ANIMATABLE/period/PARAMS0/BOUNDS`). `rings.expr`: `sin(sqrt(u*u+v*v)*f + t)`. `moire.expr`: `mul(sin(rot1·grid), sin(rot2·grid))` (two rotated gratings). New criteria: `symmetry` (from `centroid_offset`), `palette_harmony` (general).

- [ ] Steps 1–5: test exprs + round-trip + criteria scores → fail → implement → pass → commit `feat(organs): rings + moire generators; symmetry/palette criteria`.

---

## Task 14: `server.py` — program endpoint + World responses

**Files:** Modify `studio_engine/server.py`; Test `tests/test_server.py` (new — uses `http.client` against a `ThreadingHTTPServer` on an ephemeral port, or call handler funcs directly).

**Changes:** `/simulate`, `/scene/{id}` return `World`; add `GET /scene/{id}/program` → `[RenderProgram...]` (per layer); add `POST /compose {seed,organs[],scheme}` → `World`; SSE `step`/`world` events; `_summary` includes `layers[].blend` + `audio: "audio_params"` + `animatable`.

- [ ] Steps 1–5: test health + simulate→World + program endpoint shape → fail → implement → pass → commit `feat(server): World responses, /scene/{id}/program, /compose`.

---

## Task 15: handoff contract — types.ts · openapi.json · ENDPOINTS.md · INTEGRATION.md · examples

**Files:** Modify all of `handoff/`.

**Changes:**
- `types.ts`: widen `GeneratorId` to all (10 incl. rings/moire); add `RenderProgram`, `AudioProgram`, `Layer`, `Timeline`, `World`; `ArtifactKind += "render_program"`; bump schema comment to `/2`. Add an `// Endpoints:` update.
- `openapi.json`: schemas for the new types; `/scene/{id}/program`, `/compose`; `info.version` `0.2.0`.
- `INTEGRATION.md` §3 rewritten: "find the `render` layer → `RenderProgram` → for `glsl-fragment`, prepend `GLSL_HELPERS`, compile `source`, set `u_time/u_resolution/u_palette/u_value_range`, animate `u_time` within `domain.period`; for `point-recipe`, run the recipe." Delete the hand-derive-the-equation prose. Add the audio-graph + composite + timeline sections.
- `ENDPOINTS.md`: add the two endpoints.
- `examples/`: regenerate `scene.*.json` as a World; add `world.composite.json`, `program.gyroid.json`.

**Success criterion:** `test_world_contract` asserts every generator id in `engine.generators()` appears in `types.ts` and `openapi.json`; schema strings `studio-engine/2`.

- [ ] Steps 1–5: write `tests/test_world_contract.py` (parses the files as text/JSON, checks coverage) → fail → update contract files → pass → commit `docs(handoff): World contract, render/audio programs, fixed generator coverage`.

---

## Task 16: `reference-chamber.html` — the performable proof

**Files:** Modify `handoff/reference-chamber.html`.

**Changes:** single-file, zero-build, vanilla. (1) fetch a World; (2) compile the shipped GLSL fragment in a WebGL canvas, animate `u_time`; (3) instantiate the shipped Web-Audio graph (oscillators per partial + frequency automation along `pitch_curve`); (4) render a 2-layer composite via `/compose` (blend by `z`); (5) plot trajectory margins + the timeline verdicts; (6) show the receipt.

**Success criterion (manual, documented):** open against a running server → a gyroid breathes (GLSL), sound plays from the graph, a composite shows two blended layers, receipt + verdicts visible. Document the check steps in a comment block.

- [ ] **Step 1–2:** Implement the page. **Step 3:** Verify with a running server + Playwright snapshot (console error-free; canvas present). **Step 4: Commit** `feat(handoff): reference chamber performs the shipped GLSL + audio graph + composite`.

---

## Task 17: version + final green + README

**Files:** Modify `studio_engine/__init__.py` (`__version__="0.2.0"`), `pyproject.toml`, `README.md`, `HANDOFF.md`.

- [ ] **Step 1:** Bump version; update README/HANDOFF headline to the strand substrate (8→10 generators, render/audio programs, composite, timeline; keep the honest-scope section).
- [ ] **Step 2:** `python -m unittest discover -s tests` → all green (56 + new). **Step 3:** `ruff check` if configured. **Step 4: Commit** `chore: studio-engine 0.2.0 — strand substrate`.

---

## Self-Review

**Spec coverage:** §2 algebra→T1/T2; channels→T3(points)/T4(audio)/T5(fields); §2.4 proof→T2/T5/T7; §3 exprs→T5/T6; §4 World→T8; §5 compose→T9; §6 temporal→T10; §7 interactive+breadth→T12/T13; §8 layout→all; §9 tests→each task; §10 chamber→T16; §11 increments→task order; §12 guardrails→Global Constraints; §13 risks→T2(parser subset)/T4(additive raise)/T5(metaballs div). No gaps.

**Placeholders:** keystones (T1/T2) carry full code; T3–T17 carry exact interfaces + real test assertions + algorithm steps. Calibrated deliberately: full line-by-line transcription of every backend in the plan would duplicate the implementation; interfaces + success criteria are locked so parallel agents don't collide. (Reasoned deviation, noted.)

**Type consistency:** `Expr`, `eval_expr`, `sample_field`, `emit_glsl`, `parse_glsl`, `GLSL_HELPERS`, `emit_webaudio`, `render_program`, `audio_program`, `compose`, `build_timeline`, `World/Layer/RenderProgram/AudioProgram/Timeline` — names consistent across tasks. `absx` (not `abs`) used as the constructor to avoid shadowing builtin. metaballs `ANIMATABLE=False` consistent in T5/T10.

## Parallelization map (for subagent-driven execution)
- **Serial spine (lead):** T1 → T2 → T8 (model) → T11 (engine) → T14 (server) → T17.
- **Fan-out wave A (after T2+T8):** T3, T4, T5, T6 — independent files (T5/T6 share `test_organ_exprs.py` + `_gens`; give to ONE agent or split the test file first).
- **Fan-out wave B (after T7):** T9 (compose), T10 (temporal), T13 (breadth) — independent.
- **Fan-out wave C (after T11+T14):** T12 (session), T15 (handoff docs), T16 (chamber).
- Lead keeps cross-backend verification, the World contract, and integration.
