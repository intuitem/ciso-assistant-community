"""CEL evaluation for the compute action.

The `{{path}}` templating in actions.py is substitution only: it resolves a
dotted lookup and stringifies it. Anything that needs an operator (a risk
score, a ratio between two counts, a loop counter, a due date picked by
severity) goes through here instead. CEL is the expression language the
product already uses for compliance outcomes and quick forms, so authors learn
one syntax.

The evaluator is pure: no side effects, guaranteed termination, no access to
anything but the render context handed to it.

Numbers: the product types a variable as `number` without saying int or
double, and a payload or a step output decides which one arrives at runtime.
So unlike canonical CEL, mixing the two is not an error here: when one side of
an arithmetic or comparison operator is a double, the other is promoted. An
all-int expression stays int, so `7 / 2` is `3` as in CEL, and counters and
list indexes keep working. Every valid CEL expression returns the same value
as in CEL; only expressions that would have failed on a type mix now succeed.
"""

from __future__ import annotations

import math
import operator
import re

import celpy
import celpy.celtypes as celtypes
from celpy.evaluation import bool_eq, bool_ge, bool_gt, bool_le, bool_lt, bool_ne
from lark import Token, Tree


class ExpressionError(Exception):
    """A CEL expression that cannot be compiled or evaluated. The message is
    author-facing and already mentions the expression key when known."""


# celpy reports a missing overload with the grammar rule name; translate the
# ones an author will actually hit into the operator they wrote.
_RULE_LABELS = {
    "addition_add": "+",
    "addition_sub": "-",
    "multiplication_mul": "*",
    "multiplication_div": "/",
    "multiplication_mod": "%",
    "relation_lt": "<",
    "relation_le": "<=",
    "relation_gt": ">",
    "relation_ge": ">=",
    "relation_eq": "==",
    "relation_ne": "!=",
}
_OVERLOAD_RE = re.compile(r"found no matching overload for Token\('RULE', '(\w+)'\)")
_CLASS_RE = re.compile(r"<class '(?:[\w.]*\.)?(\w+)'>")
_UNDECLARED_RE = re.compile(r"undeclared reference to '([^']+)'")
_NO_MEMBER_RE = re.compile(r"no such member in mapping: '([^']+)'")
_TYPE_NAMES = {
    "IntType": "int",
    "UintType": "uint",
    "DoubleType": "double",
    "StringType": "string",
    "BoolType": "bool",
    "BytesType": "bytes",
    "ListType": "list",
    "MapType": "map",
    "TimestampType": "timestamp",
    "DurationType": "duration",
    "NoneType": "null",
    "float": "double",
    "str": "string",
    "int": "int",
}


def to_cel(value):
    """JSON-shaped Python (what instance.variables and node_outputs hold) to
    CEL types. None stays None so `x == null` and `has()` behave; bool is
    checked before int because bool subclasses int."""
    if value is None:
        return None
    if isinstance(value, bool):
        return celtypes.BoolType(value)
    if isinstance(value, int):
        return celtypes.IntType(value)
    if isinstance(value, float):
        return celtypes.DoubleType(value)
    if isinstance(value, str):
        return celtypes.StringType(value)
    if isinstance(value, dict):
        return celtypes.MapType(
            {celtypes.StringType(str(k)): to_cel(v) for k, v in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return celtypes.ListType([to_cel(v) for v in value])
    return celtypes.StringType(str(value))


def from_cel(value):
    """CEL result back to JSON-shaped Python for instance.variables. celpy
    returns plain float/str for some operations, so both are handled."""
    if value is None:
        return None
    if isinstance(value, celtypes.BoolType):
        return bool(value)
    if isinstance(value, (celtypes.IntType, celtypes.UintType)):
        return int(value)
    if isinstance(value, celtypes.DoubleType):
        return float(value)
    if isinstance(value, celtypes.StringType):
        return str(value)
    if isinstance(value, celtypes.BytesType):
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, celtypes.TimestampType):
        return value.isoformat()
    if isinstance(value, celtypes.DurationType):
        return value.total_seconds()
    if isinstance(value, celtypes.MapType):
        return {str(k): from_cel(v) for k, v in value.items()}
    if isinstance(value, celtypes.ListType):
        return [from_cel(v) for v in value]
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(k): from_cel(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [from_cel(v) for v in value]
    return str(value)


# ---------- number promotion ----------
#
# celpy resolves every operator through the program's function table, so the
# promotion is scoped to compute programs: the compliance evaluator in
# core.cel_service keeps canonical strictness.

_INTS = (celtypes.IntType, celtypes.UintType, int)
_DOUBLES = (celtypes.DoubleType, float)


def _kind(value):
    """'int', 'double', 'string', 'timestamp' or None. celpy hands intermediate
    results to functions as plain int/float/str as often as the CEL types, so
    both spellings count; bool is excluded because it subclasses int."""
    if isinstance(value, (bool, celtypes.BoolType)):
        return None
    if isinstance(value, _INTS):
        return "int"
    if isinstance(value, _DOUBLES):
        return "double"
    if isinstance(value, (celtypes.StringType, str)):
        return "string"
    if isinstance(value, celtypes.TimestampType):
        return "timestamp"
    return None


def _promoting(op):
    """`op` with int/double promotion: when exactly one operand is a double,
    both become doubles. Anything else is passed through untouched, so string,
    list, timestamp and error semantics are celpy's own."""

    def apply(left, right):
        left_kind, right_kind = _kind(left), _kind(right)
        if {left_kind, right_kind} == {"int", "double"}:
            return op(
                celtypes.DoubleType(float(left)), celtypes.DoubleType(float(right))
            )
        return op(left, right)

    return apply


OPERATORS = {
    "_+_": _promoting(operator.add),
    "_-_": _promoting(operator.sub),
    "_*_": _promoting(operator.mul),
    "_/_": _promoting(operator.truediv),
    # Comparisons wrap celpy's own, which return BoolType and keep CEL's
    # equality semantics for everything that is not a promoted number pair.
    "_<_": _promoting(bool_lt),
    "_<=_": _promoting(bool_le),
    "_>_": _promoting(bool_gt),
    "_>=_": _promoting(bool_ge),
    "_==_": _promoting(bool_eq),
    "_!=_": _promoting(bool_ne),
}


# ---------- helper functions CEL lacks ----------
#
# sum/avg take a list of numbers with the same promotion as the operators: an
# all-int list yields an int, any double makes the result a double. avg always
# yields a double. min/max also accept a homogeneous list of strings (ISO dates
# sort lexically) or of timestamps.


def _wrap(value, kind):
    if kind == "double":
        return celtypes.DoubleType(float(value))
    if kind == "int":
        return celtypes.IntType(int(value))
    if kind == "string":
        return celtypes.StringType(str(value))
    return value


def _items(values, name):
    if not isinstance(values, (celtypes.ListType, list, tuple)):
        raise ValueError(f"{name}() takes a list")
    items = list(values)
    kinds = {_kind(item) for item in items}
    if None in kinds:
        raise ValueError(f"{name}() takes a list of numbers, strings or timestamps")
    if kinds <= {"int", "double"}:
        return items, ("double" if "double" in kinds else "int")
    if len(kinds) > 1:
        raise ValueError(
            f"{name}() takes a list of one kind — this one mixes "
            f"{' and '.join(sorted(kinds))}"
        )
    return items, kinds.pop()


def _numbers(values, name):
    items, kind = _items(values, name)
    if kind not in ("int", "double"):
        raise ValueError(f"{name}() takes a list of numbers")
    return items, kind


def _sum(values):
    items, kind = _numbers(values, "sum")
    if kind == "double":
        return celtypes.DoubleType(sum(float(x) for x in items))
    return celtypes.IntType(sum(int(x) for x in items))


def _avg(values):
    items, _ = _numbers(values, "avg")
    if not items:
        raise ValueError("avg() of an empty list")
    return celtypes.DoubleType(sum(float(x) for x in items) / len(items))


def _extreme(values, name, pick):
    items, kind = _items(values, name)
    if not items:
        raise ValueError(f"{name}() of an empty list")
    if kind == "double":
        return celtypes.DoubleType(pick(float(x) for x in items))
    if kind == "int":
        return celtypes.IntType(pick(int(x) for x in items))
    return _wrap(pick(items), kind)


def _min(values):
    return _extreme(values, "min", min)


def _max(values):
    return _extreme(values, "max", max)


def _number(value, name):
    kind = _kind(value)
    if kind not in ("int", "double"):
        raise ValueError(f"{name}() takes a number")
    return kind


def _round(value, digits=None):
    _number(value, "round")
    if digits is None:
        return celtypes.IntType(round(float(value)))
    if _kind(digits) != "int":
        raise ValueError("round() digits must be an int")
    return celtypes.DoubleType(round(float(value), int(digits)))


def _floor(value):
    _number(value, "floor")
    return celtypes.IntType(math.floor(float(value)))


def _ceil(value):
    _number(value, "ceil")
    return celtypes.IntType(math.ceil(float(value)))


def _abs(value):
    kind = _number(value, "abs")
    return _wrap(abs(value), kind)


FUNCTIONS = {
    "sum": _sum,
    "avg": _avg,
    "min": _min,
    "max": _max,
    "round": _round,
    "floor": _floor,
    "ceil": _ceil,
    "abs": _abs,
}

_env = None


def _environment():
    global _env
    if _env is None:
        _env = celpy.Environment()
    return _env


def _describe(error):
    """celpy's messages are tuples with class names in them; keep the part an
    author can act on."""
    args = error.args
    message = args[0] if args else str(error)
    if not isinstance(message, str):
        message = str(message)
    # celpy wraps an exception raised inside evaluation as
    # (label, exception class, exception args); the label is generic
    # ("return error for overflow" covers every ValueError) and the real
    # message, including the ones FUNCTIONS raise, sits in the third slot.
    inner = None
    if len(args) >= 3 and isinstance(args[2], tuple) and args[2]:
        inner = str(args[2][0])
    if isinstance(error, ArithmeticError):
        inner = str(error)
    match = _OVERLOAD_RE.search(message)
    if match:
        rule = match.group(1)
        operator = _RULE_LABELS.get(rule, rule)
        types = [_TYPE_NAMES.get(name, name) for name in _CLASS_RE.findall(message)]
        if types:
            return f"'{operator}' cannot combine {' and '.join(types)}"
        return f"'{operator}' has no overload for these types"
    if "does not support field selection" in message:
        return "a null value has no fields — check it with has(...) or == null first"
    if inner:
        if inner == "overflow":
            return "integer overflow"
        if inner == "list index out of range":
            return "list index out of range"
        if isinstance(args[1], type) and issubclass(args[1], ArithmeticError):
            return inner
        if isinstance(args[1], type) and issubclass(args[1], (ValueError, IndexError)):
            return inner
    match = _UNDECLARED_RE.search(message)
    if match:
        return f"'{match.group(1)}' is not a variable, a node output or a loop item"
    match = _NO_MEMBER_RE.search(message)
    if match:
        return f"no field '{match.group(1)}' at this path — check has(...) first"
    if "divide by zero" in message or "division by zero" in message:
        return "division by zero"
    if "overflow" in message:
        return "integer overflow"
    return message.strip()


def compile_expression(expression):
    """Parse only; raises ExpressionError with celpy's caret diagram."""
    if not isinstance(expression, str) or not expression.strip():
        raise ExpressionError("the expression is empty")
    try:
        return _environment().compile(expression)
    except celpy.CELParseError as e:
        raise ExpressionError(f"syntax error: {_describe(e)}")


def evaluate(expression, context):
    """Evaluate `expression` against a JSON-shaped `context`; the result is
    JSON-shaped too. Every failure is an ExpressionError."""
    ast = compile_expression(expression)
    cel_context = {str(k): to_cel(v) for k, v in context.items()}
    program = _environment().program(ast, functions={**OPERATORS, **FUNCTIONS})
    try:
        result = program.evaluate(cel_context)
    except celpy.CELEvalError as e:
        raise ExpressionError(_describe(e))
    except (ArithmeticError, ValueError, TypeError, KeyError, IndexError) as e:
        raise ExpressionError(_describe(e))
    if isinstance(result, celpy.CELEvalError):
        raise ExpressionError(_describe(result))
    return from_cel(result)


def referenced_paths(expression):
    """Dotted paths the expression reads (`nodes.fetch.count`, `weight`),
    including their prefixes. Function names are excluded; macro-bound names
    (the `x` in `items.filter(x, ...)`) are included, an over-approximation
    that only matters to the AI provenance walk. Returns an empty set for an
    expression that does not parse: the syntax error is reported elsewhere."""
    try:
        ast = compile_expression(expression)
    except ExpressionError:
        return set()
    paths = set()
    for subtree in ast.iter_subtrees():
        path = _path_of(subtree)
        if path:
            paths.add(path)
    return paths


def _path_of(tree):
    if not isinstance(tree, Tree):
        return None
    if tree.data == "primary":
        child = tree.children[0] if tree.children else None
        if isinstance(child, Tree) and child.data == "ident" and child.children:
            return str(child.children[0])
        return None
    if tree.data == "member" and len(tree.children) == 1:
        return _path_of(tree.children[0])
    if tree.data == "member_dot" and len(tree.children) >= 2:
        base = _path_of(tree.children[0])
        name = tree.children[1]
        if base and isinstance(name, Token):
            return f"{base}.{name}"
        return base
    if tree.data == "member_dot_arg" and tree.children:
        # A method call: the receiver is what's referenced, not the method.
        return _path_of(tree.children[0])
    return None
