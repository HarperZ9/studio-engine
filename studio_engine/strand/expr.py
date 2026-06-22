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


def _lift(a) -> "Expr":
    return a if isinstance(a, Expr) else const(float(a))


def const(x: float) -> "Expr":
    return Expr("const", (float(x),))


def var(name: str) -> "Expr":
    if name not in VARS:
        raise ValueError(f"unknown var {name!r}; have {VARS}")
    return Expr("var", (name,))


def sin(a) -> "Expr": return Expr("sin", (_lift(a),))
def cos(a) -> "Expr": return Expr("cos", (_lift(a),))
def exp(a) -> "Expr": return Expr("exp", (_lift(a),))
def absx(a) -> "Expr": return Expr("abs", (_lift(a),))
def neg(a) -> "Expr": return Expr("neg", (_lift(a),))
def sqrt(a) -> "Expr": return Expr("sqrt", (_lift(a),))
def add(*a) -> "Expr": return Expr("add", tuple(_lift(x) for x in a))
def mul(*a) -> "Expr": return Expr("mul", tuple(_lift(x) for x in a))
def sub(a, b) -> "Expr": return Expr("sub", (_lift(a), _lift(b)))
def div(a, b) -> "Expr": return Expr("div", (_lift(a), _lift(b)))


def eval_expr(e: "Expr", env: dict) -> float:
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


def _canon(e: "Expr") -> str:
    if e.op == "const":
        return f"({e.args[0]!r})"
    if e.op == "var":
        return e.args[0]
    return e.op + "(" + ",".join(_canon(a) for a in e.args) + ")"


def sha(e: "Expr") -> str:
    return hashlib.sha256(_canon(e).encode("utf-8")).hexdigest()[:16]


def sample_field(e: "Expr", n: int, t: float = 0.0) -> list:
    """Row-major n*n samples over u,v in [-1,1] (cell centers), at fixed t."""
    n = max(1, n)
    out = []
    for gy in range(n):
        v = 2.0 * ((gy + 0.5) / n) - 1.0
        for gx in range(n):
            u = 2.0 * ((gx + 0.5) / n) - 1.0
            out.append(eval_expr(e, {"u": u, "v": v, "t": t}))
    return out
