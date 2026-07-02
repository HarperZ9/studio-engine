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


def to_dict(e: "Expr") -> dict:
    """JSON-safe serialization preserving the EXACT tree (including n-ary associativity).

    A leaf ('const'/'var') carries its single scalar/name arg; every other op carries its child
    exprs. Round-trips through from_dict to a byte-identical canonical form, so sha(from_dict(
    to_dict(e))) == sha(e). This is what lets a headless renderer re-hash the shipped AST and
    catch tampering without depending on the lossy GLSL emit/parse associativity.
    """
    if e.op in ("const", "var"):
        return {"op": e.op, "arg": e.args[0]}
    return {"op": e.op, "args": [to_dict(a) for a in e.args]}


def from_dict(d: dict) -> "Expr":
    """Inverse of to_dict. Validates the op and shape; raises ValueError on anything malformed."""
    if not isinstance(d, dict) or "op" not in d:
        raise ValueError(f"not an expr node: {d!r}")
    op = d["op"]
    if op not in OPS:
        raise ValueError(f"unknown op {op!r}")
    if op == "const":
        return Expr("const", (float(d["arg"]),))
    if op == "var":
        name = d["arg"]
        if name not in VARS:
            raise ValueError(f"unknown var {name!r}")
        return Expr("var", (name,))
    args = d.get("args")
    if not isinstance(args, list) or not args:
        raise ValueError(f"op {op!r} needs a non-empty args list")
    children = tuple(from_dict(a) for a in args)
    if op in _UNARY and len(children) != 1:
        raise ValueError(f"unary op {op!r} needs exactly 1 arg, got {len(children)}")
    if op in _BINARY and len(children) != 2:
        raise ValueError(f"binary op {op!r} needs exactly 2 args, got {len(children)}")
    return Expr(op, children)


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
