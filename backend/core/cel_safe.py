"""Shared CEL evaluation helpers.

The one thing the outcome and rating evaluators need in common is a program
whose ``||`` / ``&&`` cannot blow up. celpy's default ``logical_or`` /
``logical_and`` raise ``TypeError(f"{x!r} or {y!r}")`` when both operands are
errors, and celpy wraps that text into a new error value, so a chain of failing
``||`` — a rule reading answers that are not in play, e.g. out of the audit's
implementation-group scope or on a hidden requirement — builds a message whose
size, and memory, doubles with every term. A couple dozen terms is enough to OOM
the worker while re-evaluating a framework's audits on publish.

The wrappers below keep celpy's exact semantics for every case where at least one
operand is a boolean, and simply propagate one operand's error (instead of
combining both reprs) when neither is. The result of a failing chain stays a
single ``no such key`` instead of a megabyte of nested text.
"""

from __future__ import annotations

import celpy
import celpy.celtypes as celtypes


def _logical_or(x, y):
    x_bool = isinstance(x, celtypes.BoolType)
    y_bool = isinstance(y, celtypes.BoolType)
    if not x_bool and not y_bool:
        # Both errored: propagate one, do not combine their reprs.
        return x
    if not x_bool and y_bool:
        return y if y else x  # _ || true == true ; _ || false == _
    if x_bool and not y_bool:
        return x if x else y  # true || _ == true ; false || _ == _
    return celtypes.BoolType(bool(x) or bool(y))


def _logical_and(x, y):
    x_bool = isinstance(x, celtypes.BoolType)
    y_bool = isinstance(y, celtypes.BoolType)
    if not x_bool and not y_bool:
        # Both errored: propagate one, do not combine their reprs.
        return x
    if not x_bool and y_bool:
        return x if y else y  # _ && true == _ ; _ && false == false
    if x_bool and not y_bool:
        return y if x else x  # true && _ == _ ; false && _ == false
    return celtypes.BoolType(bool(x) and bool(y))


_SAFE_FUNCTIONS = {"_||_": _logical_or, "_&&_": _logical_and}


def safe_program(env: celpy.Environment, ast):
    """``env.program(ast)`` with the bounded ``||`` / ``&&`` above.

    Use it for every CEL program that evaluates authored expressions over audit
    or response data, so one failing rule cannot exhaust memory.
    """
    return env.program(ast, functions=_SAFE_FUNCTIONS)
