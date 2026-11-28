"""Shared CEL evaluation helpers.

The one thing the outcome and rating evaluators need in common is a program
whose ``||`` / ``&&`` cannot blow up. When both operands are errors, celpy's
``logical_or`` / ``logical_and`` raise ``TypeError(f"{x!r} or {y!r}")``, which
celpy wraps into a new error value; so a chain of failing ``||`` — a rule reading
answers that are not in play, e.g. out of the audit's implementation-group scope
or on a hidden requirement — builds an error whose repr, and memory, doubles with
every term. A couple dozen terms is enough to OOM the worker re-evaluating a
framework's audits on publish.

The wrappers below change exactly one case: when BOTH operands are already CEL
errors, they propagate one of them instead of combining both reprs (``error ||
error == error`` and ``error && error == error`` in CEL anyway). Every other case
is delegated to celpy unchanged, so the operators keep CEL semantics — in
particular two non-boolean, non-error operands (``"a" || "b"``) still raise, as
the CEL spec requires: https://github.com/cel-expr/cel-spec/blob/master/doc/langdef.md#logical-operators-1
"""

from __future__ import annotations

import celpy
from celpy import CELEvalError, celtypes


def _logical_or(x, y):
    if isinstance(x, CELEvalError) and isinstance(y, CELEvalError):
        return x  # error || error == error: propagate one, don't combine reprs
    return celtypes.logical_or(x, y)


def _logical_and(x, y):
    if isinstance(x, CELEvalError) and isinstance(y, CELEvalError):
        return x  # error && error == error: propagate one, don't combine reprs
    return celtypes.logical_and(x, y)


_SAFE_FUNCTIONS = {"_||_": _logical_or, "_&&_": _logical_and}


def safe_program(env: celpy.Environment, ast):
    """``env.program(ast)`` with the bounded ``||`` / ``&&`` above.

    Use it for every CEL program that evaluates authored expressions over audit
    or response data, so one failing rule cannot exhaust memory.
    """
    return env.program(ast, functions=_SAFE_FUNCTIONS)
