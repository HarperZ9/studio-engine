"""GLSL backend for the strand algebra: emit a fragment expression, and parse it back.

The parse half exists for the grounding proof: AST -> GLSL -> parse -> AST' must eval-equal the
original (tests/test_strand_glsl.py). The parser handles ONLY the closed subset emit_glsl produces
-- never arbitrary GLSL. `safediv` mirrors the Python eval's division guard so the two agree exactly.
"""
from __future__ import annotations

from .expr import Expr, const, var, sin, cos, exp, absx, neg, sqrt, add, mul, sub, div

GLSL_HELPERS = ("float safediv(float a, float b){ float d = abs(b) > 1e-3 ? b : "
                "(b >= 0.0 ? 1e-3 : -1e-3); return a / d; }")
_FUNCS = {"sin": sin, "cos": cos, "exp": exp, "abs": absx, "sqrt": sqrt}


def emit_glsl(e: Expr) -> str:
    op = e.op
    if op == "const":
        x = e.args[0]
        r = repr(x)
        if x < 0:
            return f"({r})"
        return r if ("." in r or "e" in r or "E" in r) else f"{r}.0"
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
            raise ValueError(f"trailing input at {self.i} in {self.s!r}")
        return e

    def _sum(self) -> Expr:
        node = self._term()
        while self.peek() and self.peek() in "+-":
            op = self.peek()
            self.i += 1
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
            # stop a +/- that begins a new term: only consume it inside exponents (after e/E)
            if self.peek() in "+-" and self.i > j and self.s[self.i - 1] not in "eE":
                break
            self.i += 1
        return const(float(self.s[j:self.i]))


def parse_glsl(src: str) -> Expr:
    return _P(src).parse()
