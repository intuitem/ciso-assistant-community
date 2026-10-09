"""Aggregate mode: a read that returns numbers about rows instead of rows.

A read config in aggregate mode carries an ``aggregates`` list::

    [{"fn": "count"},
     {"fn": "avg", "field": "priority", "as": "avg_priority"},
     {"fn": "count", "group_by": "status"},
     {"fn": "median", "field": "progress"}]

and answers one flat map keyed by alias: ``{"count": 12, "avg_priority":
2.4, "by_status": {"active": 8, "to_do": 4}, "median_progress": 60.0}``.

Each function runs in one fixed place, decided here and not by the author.
Database functions collapse into a fixed number of queries whatever the row
count. Worker functions (median, percentile, standard deviation, and any
function over a value the product computes in Python) stream the rows up to
a hard ceiling and fail the read when it is reached. They never truncate:
a number computed over some of the rows would be a wrong number.
"""

from __future__ import annotations

import datetime
import decimal
import math
import re
import statistics
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field as dataclass_field

from django.conf import settings
from django.db.models import Avg, Count, Max, Min, Sum

from .filters import (
    KIND_DATE,
    KIND_NUMERIC,
    KINDS,
    ReadError,
    field_kind,
    get_model_field,
)

ENGINE_DB = "db"
ENGINE_PYTHON = "python"

ALIAS_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MAX_AGGREGATES = 20
NULL_KEY = "null"


def aggregate_max_rows():
    """Ceiling on rows a worker-side aggregate may scan, read at call time."""
    return int(getattr(settings, "WORKFLOW_AGGREGATE_MAX_ROWS", 10000))


# ---------- the functions ----------


def _percentile(values, p):
    """Linear interpolation between closest ranks, the same definition as
    numpy's default, with no dependency."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * p / 100
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(ordered[low])
    return float(ordered[low]) + (float(ordered[high]) - float(ordered[low])) * (
        rank - low
    )


@dataclass(frozen=True)
class AggregateFn:
    """One function an aggregate may name.

    ``engine`` is where it runs. ``needs_field`` says whether it takes a
    field. ``accepts`` is the set of field kinds it takes (empty: any).
    ``build`` makes the Django aggregate for a database function; ``fold``
    reduces a list of non-null Python values when the function runs in the
    worker, which every function can, over a computed value.
    ``params`` names the extra keys the spec may carry.
    """

    name: str
    engine: str
    needs_field: bool
    accepts: frozenset = frozenset()
    build: Callable | None = None
    fold: Callable | None = None
    params: tuple = ()


NUMERIC_ONLY = frozenset({KIND_NUMERIC})
ORDERABLE = frozenset({KIND_NUMERIC, KIND_DATE})

AGGREGATES: dict[str, AggregateFn] = {
    "count": AggregateFn(
        "count", ENGINE_DB, False, build=lambda f: Count("pk"), fold=len
    ),
    "count_distinct": AggregateFn(
        "count_distinct",
        ENGINE_DB,
        True,
        build=lambda f: Count(f, distinct=True),
        fold=lambda values: len(set(values)),
    ),
    "sum": AggregateFn(
        "sum", ENGINE_DB, True, NUMERIC_ONLY, build=lambda f: Sum(f), fold=sum
    ),
    "avg": AggregateFn(
        "avg",
        ENGINE_DB,
        True,
        NUMERIC_ONLY,
        build=lambda f: Avg(f),
        fold=lambda values: statistics.fmean(values),
    ),
    "min": AggregateFn(
        "min", ENGINE_DB, True, ORDERABLE, build=lambda f: Min(f), fold=min
    ),
    "max": AggregateFn(
        "max", ENGINE_DB, True, ORDERABLE, build=lambda f: Max(f), fold=max
    ),
    "median": AggregateFn(
        "median", ENGINE_PYTHON, True, NUMERIC_ONLY, fold=statistics.median
    ),
    "percentile": AggregateFn(
        "percentile",
        ENGINE_PYTHON,
        True,
        NUMERIC_ONLY,
        fold=_percentile,
        params=("p",),
    ),
    "stddev": AggregateFn(
        "stddev", ENGINE_PYTHON, True, NUMERIC_ONLY, fold=statistics.pstdev
    ),
}


def function_catalog():
    """What the editor needs to offer the functions."""
    return [
        {
            "name": fn.name,
            "engine": fn.engine,
            "needs_field": fn.needs_field,
            "accepts": sorted(fn.accepts) or sorted(KINDS),
            "params": list(fn.params),
        }
        for fn in AGGREGATES.values()
    ]


# ---------- the specs ----------


@dataclass(frozen=True)
class AggregateSpec:
    """One normalized aggregate: what to compute, over which field, grouped
    how, under which alias, and where it runs."""

    fn: AggregateFn
    field: str | None
    group_by: str | None
    alias: str
    engine: str
    params: dict = dataclass_field(default_factory=dict)
    #: For a worker aggregate over a computed value: the computed value's
    #: name and the dotted path inside it (``scores.global`` ->
    #: ``("scores", ["global"])``).
    computed: tuple[str, list[str]] | None = None


def _default_alias(fn_name, field, group_by):
    base = fn_name if field is None else f"{fn_name}_{field.replace('.', '_')}"
    if group_by is None:
        return base
    return f"by_{group_by}" if fn_name == "count" else f"{base}_by_{group_by}"


def _computed_target(entry, field, config):
    """``(name, path)`` when ``field`` reaches a computed value of the entry
    (always-on, or opt-in through ``include``), else None."""
    name, _dot, rest = field.partition(".")
    requested = config.get("include") or []
    if isinstance(requested, str):
        requested = [requested]
    if name in entry.computed or (
        name in requested and name in entry.optional_computed
    ):
        return name, [part for part in rest.split(".") if part]
    return None


def normalize_aggregate(spec, entry, config, taken=()):
    """One raw spec to an AggregateSpec. Raises ReadError with the message an
    author needs; ``taken`` holds the aliases already used by earlier specs."""
    if not isinstance(spec, dict):
        raise ReadError("an aggregate must be a mapping with 'fn'")
    fn = AGGREGATES.get(spec.get("fn"))
    if fn is None:
        raise ReadError(f"unknown aggregate function '{spec.get('fn')}'")
    field = spec.get("field") or None
    group_by = spec.get("group_by") or None
    readable = set(entry.readable_fields())

    computed = None
    engine = fn.engine
    if fn.needs_field:
        if not isinstance(field, str) or not field:
            raise ReadError(f"'{fn.name}' needs a field")
        if field in readable:
            kind = field_kind(entry, field)
            if fn.accepts and kind not in fn.accepts:
                raise ReadError(
                    f"'{fn.name}' cannot run on '{field}' ({kind or 'unknown'} field)"
                )
        else:
            computed = _computed_target(entry, field, config)
            if computed is None:
                raise ReadError(f"'{field}' is not a field '{fn.name}' can run on")
            if fn.name == "count_distinct":
                raise ReadError(
                    "'count_distinct' runs on a column, not a computed value"
                )
            # A computed value is a Python value: the function runs in the
            # worker whatever its own engine.
            engine = ENGINE_PYTHON
    elif field:
        raise ReadError(f"'{fn.name}' takes no field")

    if group_by is not None:
        if not isinstance(group_by, str) or group_by not in readable:
            raise ReadError(f"'{group_by}' is not a field to group by")
        if group_by in entry.annotations:
            raise ReadError(f"'{group_by}' is an annotation and cannot group rows")

    params = {}
    for name in fn.params:
        if name not in spec:
            raise ReadError(f"'{fn.name}' needs '{name}'")
        params[name] = spec[name]
    if fn.name == "percentile":
        try:
            p = float(params["p"])
        except TypeError, ValueError:
            p = -1.0
        if not 0 <= p <= 100:
            raise ReadError("'percentile' needs 'p' between 0 and 100")
        params["p"] = p
    unknown = set(spec) - {"fn", "field", "group_by", "as", *fn.params}
    if unknown:
        raise ReadError(f"unknown aggregate key '{min(unknown)}'")

    alias = spec.get("as") or _default_alias(fn.name, field, group_by)
    if not isinstance(alias, str) or not ALIAS_RE.match(alias):
        raise ReadError(f"'{alias}' is not a valid alias (letters, digits, _)")
    if alias in taken:
        raise ReadError(f"alias '{alias}' is used twice")
    if alias in readable or get_model_field(entry.model, alias):
        raise ReadError(f"alias '{alias}' is the name of a field; pick another")
    return AggregateSpec(fn, field, group_by, alias, engine, params, computed)


def normalize_aggregates(raw, entry, config):
    """The whole list, in order, aliases unique."""
    if not isinstance(raw, list) or not raw:
        raise ReadError("aggregate mode needs at least one aggregate")
    if len(raw) > MAX_AGGREGATES:
        raise ReadError(f"at most {MAX_AGGREGATES} aggregates per read")
    specs = []
    for spec in raw:
        specs.append(normalize_aggregate(spec, entry, config, [s.alias for s in specs]))
    return specs


def referenced_fields(specs) -> set[str]:
    """Fields the specs read from the row (columns and annotations), so the
    caller annotates only what is needed."""
    names = set()
    for spec in specs:
        if spec.field is not None and spec.computed is None:
            names.add(spec.field)
        if spec.group_by is not None:
            names.add(spec.group_by)
    return names


# ---------- running ----------


def _json_number(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _group_key(value):
    """A group value as a map key: strings only, since the expression layer
    and JSON both key maps by string."""
    if value is None:
        return NULL_KEY
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return str(value)


def _choice_keys(entry, field):
    """Every value a choice column can hold, so a count breakdown has a
    stable shape: each key present, zeroes included."""
    column = get_model_field(entry.model, field)
    choices = getattr(column, "choices", None) or []
    return [_group_key(value) for value, _label in choices]


def _empty_result(spec, entry):
    if spec.group_by is None:
        return 0 if spec.fn.name == "count" else None
    if spec.fn.name == "count":
        return dict.fromkeys(_choice_keys(entry, spec.group_by), 0)
    return {}


def _run_db(entry, queryset, specs):
    results = {}
    scalars = [s for s in specs if s.group_by is None]
    if scalars:
        row = queryset.order_by().aggregate(
            **{s.alias: s.fn.build(s.field) for s in scalars}
        )
        for spec in scalars:
            value = _json_number(row[spec.alias])
            results[spec.alias] = (
                0 if spec.fn.name == "count" and value is None else value
            )
    grouped = [s for s in specs if s.group_by is not None]
    for group_by in dict.fromkeys(s.group_by for s in grouped):
        members = [s for s in grouped if s.group_by == group_by]
        rows = (
            queryset.order_by()
            .values(group_by)
            .annotate(**{s.alias: s.fn.build(s.field) for s in members})
        )
        for spec in members:
            results[spec.alias] = _empty_result(spec, entry)
        for row in rows:
            key = _group_key(row[group_by])
            for spec in members:
                results[spec.alias][key] = _json_number(row[spec.alias])
    return results


def _dig(value, path):
    for part in path:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value


def _number(value, spec):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return value
    raise ReadError(
        f"'{spec.alias}': '{spec.field}' holds a non-numeric value ({value!r})"
    )


def _fold(spec, values):
    if not values:
        return None
    if spec.fn.name == "percentile":
        return _json_number(spec.fn.fold(values, spec.params["p"]))
    return _json_number(spec.fn.fold(values))


def _run_python(entry, queryset, specs, computed):
    """One pass over the rows for every worker aggregate at once."""
    count = queryset.count()
    ceiling = aggregate_max_rows()
    if count > ceiling:
        raise ReadError(
            f"{count} rows exceed the ceiling of {ceiling} for "
            f"'{specs[0].fn.name}': narrow the filters"
        )
    buckets = {spec.alias: ({} if spec.group_by else []) for spec in specs}
    needs_objects = any(spec.computed is not None for spec in specs)
    columns = sorted(
        {spec.field for spec in specs if spec.computed is None}
        | {spec.group_by for spec in specs if spec.group_by}
    )

    # The stored value, as values_list and the database path read it: a
    # relation column is its id (`framework_id`), not the related object.
    attnames = {
        name: getattr(get_model_field(entry.model, name), "attname", name)
        for name in columns
    }

    def rows():
        if needs_objects:
            for obj in queryset.order_by().iterator(chunk_size=500):
                yield (
                    obj,
                    {name: getattr(obj, attnames[name], None) for name in columns},
                )
        else:
            for row in (
                queryset.order_by().values_list(*columns).iterator(chunk_size=2000)
            ):
                yield None, dict(zip(columns, row))

    memo = {}
    for obj, row in rows():
        memo.clear()
        for spec in specs:
            if spec.computed is None:
                value = row[spec.field]
            else:
                name, path = spec.computed
                if name not in memo:
                    memo[name] = computed[name](obj)
                value = _dig(memo[name], path)
            value = _number(value, spec)
            if value is None:
                continue
            if spec.group_by is None:
                buckets[spec.alias].append(value)
            else:
                buckets[spec.alias].setdefault(
                    _group_key(row[spec.group_by]), []
                ).append(value)
    results = {}
    for spec in specs:
        if spec.group_by is None:
            results[spec.alias] = _fold(spec, buckets[spec.alias])
        else:
            results[spec.alias] = {
                key: _fold(spec, values) for key, values in buckets[spec.alias].items()
            }
    return results


def run_aggregates(entry, queryset, specs, computed=None):
    """Every spec over ``queryset``, as ``{alias: value}`` in spec order."""
    db_specs = [s for s in specs if s.engine == ENGINE_DB]
    py_specs = [s for s in specs if s.engine == ENGINE_PYTHON]
    results = {}
    if db_specs:
        results.update(_run_db(entry, queryset, db_specs))
    if py_specs:
        results.update(_run_python(entry, queryset, py_specs, computed or {}))
    return {spec.alias: results[spec.alias] for spec in specs}
