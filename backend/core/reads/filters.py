"""The filter tree: the one way a read names the rows it wants.

A tree is a group ``{"operator": "and"|"or"|"not", "conditions": [...],
"children": [...]}`` whose conditions are ``{"field", "op", "value"}``.
``validate_filter_tree`` checks the shape; ``filters_to_q`` compiles a tree
against a ReadEntry into a Django ``Q``, refusing any field outside the
entry's whitelist and any operator its column type cannot carry.

Every lookup here must behave the same on SQLite and PostgreSQL. The
operator table is deliberately short: ``icontains`` on a boolean, for one,
compiles on both databases with different rows, so the column type decides
which operators are even offered.
"""

from __future__ import annotations

import json

from django.db.models import (
    BooleanField,
    DateField,
    DecimalField,
    Field,
    FloatField,
    ForeignKey,
    IntegerField,
    Model,
    Q,
    UUIDField,
)


class ReadError(ValueError):
    """A read configuration that cannot be compiled or served. The message is
    author-facing and never names the caller (a workflow node prefixes it)."""


MAX_FILTER_DEPTH = 5

OP_LOOKUPS = {
    "eq": "exact",
    "neq": "exact",
    "gt": "gt",
    "lt": "lt",
    "gte": "gte",
    "lte": "lte",
    "in": "in",
    "not_in": "in",
    "contains": "icontains",
    "is_null": "isnull",
}

GROUP_OPERATORS = ("and", "or", "not")

# What a column (or an annotation) holds, as far as filtering and
# aggregating are concerned. The kind decides the operators and the
# aggregate functions a field may carry.
KIND_BOOL = "bool"
KIND_RELATION = "relation"
KIND_NUMERIC = "numeric"
KIND_DATE = "date"
KIND_TEXT = "text"
KINDS = (KIND_BOOL, KIND_RELATION, KIND_NUMERIC, KIND_DATE, KIND_TEXT)

_KIND_OPS = {
    KIND_BOOL: {"eq", "neq", "is_null"},
    KIND_RELATION: {"eq", "neq", "in", "not_in", "is_null"},
    KIND_NUMERIC: set(OP_LOOKUPS) - {"contains"},
    KIND_DATE: set(OP_LOOKUPS) - {"contains"},
    KIND_TEXT: set(OP_LOOKUPS),
}


# ---------- shape ----------


def validate_filter_tree(tree, *, ops=None):
    """Shape-check a boolean filter tree. Raises ValueError on bad shape.
    ``ops`` is the set of operator names a condition may carry; the read
    operators by default."""
    if tree in (None, {}):
        return
    _validate_group(tree, depth=0, ops=set(OP_LOOKUPS) if ops is None else ops)


def _validate_group(group, depth, ops):
    if depth > MAX_FILTER_DEPTH:
        raise ValueError("filter tree too deep")
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping")
    if group.get("operator", "and") not in GROUP_OPERATORS:
        raise ValueError("invalid operator")
    conditions = group.get("conditions", [])
    children = group.get("children", [])
    if not isinstance(conditions, list) or not isinstance(children, list):
        raise ValueError("conditions and children must be lists")
    for condition in conditions:
        if (
            not isinstance(condition, dict)
            or not isinstance(condition.get("field"), str)
            or not condition.get("field")
            or condition.get("op", "eq") not in ops
            or not isinstance(condition.get("changed", False), bool)
        ):
            raise ValueError("invalid condition")
    for child in children:
        _validate_group(child, depth + 1, ops)


def walk_conditions(group):
    """Every condition of a tree, depth first."""
    yield from group.get("conditions", [])
    for child in group.get("children", []):
        yield from walk_conditions(child)


# ---------- columns, kinds and operators ----------


def get_model_field(model: type[Model], name: str) -> Field | None:
    """Return the concrete column named ``name`` on ``model``, or None."""
    for field in model._meta.concrete_fields:
        if field.name == name:
            return field
    return None


def column_kind(field: Field | None) -> str | None:
    """The kind of a concrete column; None for an unknown column (fail
    closed). Boolean before integer: BooleanField is not an IntegerField in
    Django, but the order documents the intent."""
    if isinstance(field, BooleanField):
        return KIND_BOOL
    if isinstance(field, (ForeignKey, UUIDField)):
        return KIND_RELATION
    if isinstance(field, (IntegerField, FloatField, DecimalField)):
        return KIND_NUMERIC
    if isinstance(field, DateField):  # DateTimeField subclasses DateField
        return KIND_DATE
    if isinstance(field, Field):
        return KIND_TEXT
    return None


def field_kind(entry, name: str) -> str | None:
    """The kind of a readable field of ``entry``: a concrete column's, or an
    annotation's declared one. None when the entry has no such field."""
    annotation = entry.annotations.get(name)
    if annotation is not None:
        return annotation.kind
    return column_kind(get_model_field(entry.model, name))


def ops_for_kind(kind: str | None) -> set[str]:
    """The operators a kind can carry; none for an unknown kind. An untyped
    op either crashes at query time or — worse — compiles on both databases
    with different rows: 'contains' on a boolean LIKEs against 'true'/'false'
    on PostgreSQL (casts to text) but against 0/1 on SQLite."""
    return set(_KIND_OPS.get(kind, ()))


def allowed_ops(field: Field | None) -> set[str]:
    """The operators valid for a concrete column."""
    return ops_for_kind(column_kind(field))


# ---------- compilation ----------

_UNRATED_GUARDED_OPS = ("neq", "not_in", "gt", "lt", "gte", "lte")


def _guard_unrated(query, op, field, entry):
    """AND the >= 0 guard AFTER any negation so negating can't flip it into
    'OR level < 0': ranges and negations must not sweep unrated (-1) rows in."""
    if op in _UNRATED_GUARDED_OPS and field in entry.skip_unrated:
        query &= Q(**{f"{field}__gte": 0})
    return query


def _sentinel_fields_in(group, sentinels):
    fields = {
        condition.get("field")
        for condition in group.get("conditions", [])
        if condition.get("field") in sentinels
    }
    for child in group.get("children", []):
        fields |= _sentinel_fields_in(child, sentinels)
    return fields


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("true", "1", "yes")


def _as_list(value):
    """A list value as given, or parsed from a JSON array or a comma-separated
    string (what a templated ``{{...}}`` renders to)."""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except TypeError, ValueError:
            parsed = None
        return (
            parsed
            if isinstance(parsed, list)
            else [item.strip() for item in value.split(",") if item.strip()]
        )
    return value


def _identity(value):
    return value


def condition_to_q(condition, entry, allowed_fields, resolve=_identity):
    """One condition as a ``Q``. ``resolve`` maps the stored value to the
    value compared at run time (a workflow renders ``{{templates}}`` here)."""
    field = condition.get("field")
    if field not in allowed_fields:
        raise ReadError(f"'{field}' is not a filterable field")
    op = condition.get("op", "eq")
    lookup = OP_LOOKUPS.get(op)
    if lookup is None:
        raise ReadError(f"unknown operator {op!r}")
    if op not in ops_for_kind(field_kind(entry, field)):
        raise ReadError(f"operator {op!r} is not valid for field {field!r}")
    value = resolve(condition.get("value"))
    if op == "is_null":
        return Q(
            **{f"{field}__isnull": _as_bool(value) if value not in (None, "") else True}
        )
    if op in ("in", "not_in"):
        value = _as_list(value)
        if not isinstance(value, list):
            raise ReadError(f"'{op}' needs a list value")
        query = Q(**{f"{field}__in": value})
        if op == "not_in":
            query = ~query
        return _guard_unrated(query, op, field, entry)
    query = Q(**{f"{field}__{lookup}": value})
    if op == "neq":
        query = ~query
    return _guard_unrated(query, op, field, entry)


def group_to_q(group, entry, allowed_fields, resolve=_identity):
    operator = group.get("operator", "and")
    parts = [
        condition_to_q(condition, entry, allowed_fields, resolve)
        for condition in group.get("conditions", [])
    ]
    parts += [
        group_to_q(child, entry, allowed_fields, resolve)
        for child in group.get("children", [])
    ]
    if not parts:
        return Q()
    if operator == "or":
        combined = parts[0]
        for part in parts[1:]:
            combined |= part
        return combined
    combined = parts[0]
    for part in parts[1:]:
        combined &= part
    # Same semantics as event filters: NOT(all(results)).
    if operator == "not":
        combined = ~combined
        # The negation above just flipped every per-condition guard inside;
        # re-assert it for each sentinel field the subtree touches.
        for field in _sentinel_fields_in(group, entry.skip_unrated):
            combined &= Q(**{f"{field}__gte": 0})
    return combined


def filters_to_q(tree, entry, allowed_fields, resolve=_identity):
    """A whole tree as a ``Q``; an empty tree matches everything."""
    if tree in (None, {}):
        return Q()
    return group_to_q(tree, entry, allowed_fields, resolve)


def referenced_fields(tree) -> set[str]:
    """The field names a tree reads, so a caller can annotate only what a
    read actually touches."""
    if tree in (None, {}):
        return set()
    return {
        condition.get("field")
        for condition in walk_conditions(tree)
        if condition.get("field")
    }
