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
from decimal import ROUND_HALF_UP, Decimal

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
    "_?_:_": "?:",
}
_OVERLOAD_RE = re.compile(
    r"found no matching overload for (?:Token\('RULE', '(\w+)'\)|(\S+)) applied to"
)
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


def _int_only_mod(left, right):
    """`%` is int-only in CEL and celpy has no double overload, so a mixed or
    double modulo gets a message that says what to do rather than a generic
    overload failure."""
    if _kind(left) == "int" and _kind(right) == "int":
        return operator.mod(left, right)
    raise ValueError("'%' takes two ints — wrap the operands with int(...)")


OPERATORS = {
    "_+_": _promoting(operator.add),
    "_-_": _promoting(operator.sub),
    "_*_": _promoting(operator.mul),
    "_/_": _promoting(operator.truediv),
    "_%_": _int_only_mod,
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
    if kind == "double" and not math.isfinite(float(value)):
        raise ValueError(f"{name}() of a non-finite number")
    return kind


def _round(value, digits=None):
    """Half up, not Python's banker's rounding: a 2.5 score rounds to 3 and
    0.125 to 0.13, which is what an author reading a risk or maturity score
    expects."""
    _number(value, "round")
    places = 0
    if digits is not None:
        if _kind(digits) != "int":
            raise ValueError("round() digits must be an int")
        places = int(digits)
    quantum = Decimal(1).scaleb(-places)
    rounded = Decimal(str(float(value))).quantize(quantum, rounding=ROUND_HALF_UP)
    if digits is None:
        return celtypes.IntType(int(rounded))
    return celtypes.DoubleType(float(rounded))


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
    exc_class = args[1] if len(args) > 1 and isinstance(args[1], type) else None
    if len(args) >= 3 and isinstance(args[2], tuple) and args[2]:
        inner = str(args[2][0])
    if isinstance(error, ArithmeticError):
        # Raised directly (not wrapped by celpy): a single-arg exception.
        inner = str(error) or type(error).__name__
    match = _OVERLOAD_RE.search(message)
    if match:
        rule = match.group(1) or match.group(2)
        operator = _RULE_LABELS.get(rule, rule)
        types = [_TYPE_NAMES.get(name, name) for name in _CLASS_RE.findall(message)]
        if "CELEvalError" in types:
            # celpy evaluates a ternary's branches eagerly and hands the
            # failing one to the operator as an error value.
            return (
                f"a sub-expression of '{operator}' failed — a variable it uses "
                "does not exist yet, or a type does not match"
            )
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
        if exc_class is None or issubclass(
            exc_class, (ArithmeticError, ValueError, IndexError)
        ):
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


# A macro nested in another's body multiplies iterations: three levels over
# 500-item lists is 125M evaluations, from a 2000-character expression.
MACROS = {"map", "filter", "all", "exists", "exists_one"}
MAX_MACRO_DEPTH = 2


def compile_expression(expression):
    """Parse only; raises ExpressionError with celpy's caret diagram."""
    if not isinstance(expression, str) or not expression.strip():
        raise ExpressionError("the expression is empty")
    try:
        ast = _environment().compile(expression)
    except celpy.CELParseError as e:
        raise ExpressionError(f"syntax error: {_describe(e)}")
    if _macro_depth(ast) > MAX_MACRO_DEPTH:
        raise ExpressionError(
            f"map/filter/all/exists can be nested at most {MAX_MACRO_DEPTH} deep"
        )
    return ast


def _macro_depth(tree):
    if not isinstance(tree, Tree):
        return 0
    if (
        tree.data == "member_dot_arg"
        and len(tree.children) >= 2
        and str(tree.children[1]) in MACROS
    ):
        # A chained receiver (`a.map(...).filter(...)`) runs before, not inside.
        body = max((_macro_depth(c) for c in tree.children[2:]), default=0)
        return max(_macro_depth(tree.children[0]), 1 + body)
    return max((_macro_depth(c) for c in tree.children), default=0)


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
    return _finite(from_cel(result))


def _finite(value):
    """inf and NaN cannot be stored: Django serializes them as Infinity/NaN,
    which PostgreSQL's jsonb rejects and strict JSON renderers refuse."""
    if isinstance(value, float) and not math.isfinite(value):
        raise ExpressionError("the result is not a finite number")
    if isinstance(value, list):
        for item in value:
            _finite(item)
    elif isinstance(value, dict):
        for item in value.values():
            _finite(item)
    return value


def referenced_paths(expression):
    """Dotted paths the expression reads, as maximal chains: `nodes.fetch.count`
    and `weight`, not their prefixes. `nodes["fetch"].count` yields the same
    path as `nodes.fetch.count`; an index that is not a string literal becomes
    a `*` segment (`nodes.*`), which the provenance walk treats as reading
    every step. Function names are excluded; macro-bound names (the `x` in
    `items.filter(x, ...)`) are included, an over-approximation that only
    matters to the AI provenance walk. Returns an empty set for an expression
    that does not parse: the syntax error is reported elsewhere."""
    try:
        ast = compile_expression(expression)
    except ExpressionError:
        return set()
    paths = set()
    for subtree in ast.iter_subtrees():
        path = _path_of(subtree)
        if path:
            paths.add(path)
    # Every chain also produced its prefixes; keep the longest ones only.
    return {
        p for p in paths if not any(q != p and q.startswith(p + ".") for q in paths)
    }


def _string_literal(tree):
    """The text of a plain quoted string literal, or None for anything else.
    Escapes, raw/bytes prefixes and triple quotes are decoded by CEL at
    evaluation time, so their raw text is not the key: None makes the caller
    treat the index as computed."""
    node = tree
    while isinstance(node, Tree) and node.data != "literal":
        if len(node.children) != 1:
            return None
        node = node.children[0]
    if not isinstance(node, Tree) or not node.children:
        return None
    token = str(node.children[0])
    if (
        len(token) >= 2
        and token[0] == token[-1]
        and token[0] in "'\""
        and "\\" not in token
        and not token.startswith(token[0] * 3)
    ):
        return token[1:-1]
    return None


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
    if tree.data == "member_index" and len(tree.children) >= 2:
        base = _path_of(tree.children[0])
        if not base:
            return None
        key = _string_literal(tree.children[1])
        # A computed index can reach any member: `*` marks it so the
        # provenance walk treats `nodes[key]` as reading every step.
        return f"{base}.{key}" if key is not None else f"{base}.*"
    return None
