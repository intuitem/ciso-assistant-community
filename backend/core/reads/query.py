"""Turning a read configuration into rows.

A read configuration is ``{"model", "filters", "order_by", "mode", "limit",
"offset", "include"}``. ``build_queryset`` compiles it against a
``ReadScope`` — where the caller may look — into a queryset; ``serialize_row``
turns a row into the JSON shape every consumer sees. The scope is explicit so
the same code serves a workflow run (its folder subtree, narrowed to what its
identity may view) and a system-side consumer with no identity at all.
"""

from __future__ import annotations

import datetime
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from django.conf import settings
from django.db.models import Model, Prefetch, Q

from .entries import READABLE_MODELS, ReadEntry
from .filters import (
    OP_LOOKUPS,
    ReadError,
    allowed_ops,
    filters_to_q,
    get_model_field,
    validate_filter_tree,
    walk_conditions,
)

READ_DEFAULT_LIMIT = 25
READ_MODES = ("list", "first")


def read_max_limit():
    """Ceiling on rows a single read returns. A deployment setting rather than
    a graph option, read at call time."""
    return int(getattr(settings, "WORKFLOW_READ_MAX_LIMIT", 500))


def page_limit(config):
    """The page size a read config asks for, clamped to the deployment cap."""
    return min(
        max(int(config.get("limit") or READ_DEFAULT_LIMIT), 1),
        read_max_limit(),
    )


# ---------- scope ----------


def subtree_folder_ids(folder):
    """The folder and its whole subtree: where a read looks. Deliberately
    excludes ancestors, so a child-domain consumer never sees parent-domain
    rows."""
    return set(folder.get_sub_folders(include_self=True).values_list("id", flat=True))


def accessible_folder_ids(folder):
    """The folder, its ancestors (global referentials live in root) and its
    subtree. Where a related object may legitimately live: a control or an
    evidence in a parent domain is the normal shape."""
    ids = {folder.id}
    ids |= {f.id for f in folder.get_parent_folders()}
    ids |= {f.id for f in folder.get_sub_folders()}
    return ids


@dataclass(frozen=True)
class ReadScope:
    """Where a read may look.

    ``folder_ids``: rows must live in one of these folders. Required: there
    is no unscoped read.
    ``viewable``: ``callable(model) -> queryset of ids`` the acting identity may
    view, or None when the consumer has no identity and the folder scope is
    the whole answer.
    ``related_folder_ids``: folders a scoped prefetch may reach; defaults to
    ``folder_ids``. Wider for a workflow, which may follow a row to related
    objects in ancestor domains.
    """

    folder_ids: frozenset
    viewable: Callable[[type[Model]], object] | None = None
    related_folder_ids: frozenset | None = None

    def __post_init__(self):
        object.__setattr__(self, "folder_ids", frozenset(self.folder_ids))
        if self.related_folder_ids is not None:
            object.__setattr__(
                self, "related_folder_ids", frozenset(self.related_folder_ids)
            )

    def narrow(self, model, queryset):
        """``queryset`` restricted to what this scope may see of ``model``."""
        if self.viewable is not None:
            queryset = queryset.filter(id__in=self.viewable(model))
        if get_model_field(model, "folder"):
            queryset = queryset.filter(folder_id__in=self.folder_ids)
        return queryset

    def narrow_related(self, model, queryset):
        """Same, for objects hanging off a row already in scope."""
        folders = (
            self.related_folder_ids
            if self.related_folder_ids is not None
            else self.folder_ids
        )
        if self.viewable is not None:
            queryset = queryset.filter(id__in=self.viewable(model))
        if get_model_field(model, "folder"):
            queryset = queryset.filter(folder_id__in=folders)
        return queryset


# ---------- computed values and prefetches ----------


def effective_computed(entry: ReadEntry, config):
    """Always-on computed values, plus the optional ones this read asked for.

    Opt-in because an optional value may cost a query storm per row: a quality
    check walks a whole audit, which no unrelated read of that model should pay
    for. Unknown names fail loudly rather than returning a row that silently
    lacks the field a downstream condition branches on.
    """
    requested = config.get("include") or []
    if isinstance(requested, str):
        requested = [requested]
    unknown = [name for name in requested if name not in entry.optional_computed]
    if unknown:
        raise ReadError(
            f"'{unknown[0]}' is not includable for model '{config.get('model')}'"
        )
    return {
        **entry.computed,
        **{name: entry.optional_computed[name] for name in requested},
    }


def scoped_prefetches(entry: ReadEntry, scope: ReadScope, computed):
    """`prefetch_scoped` as Prefetch objects, each narrowed to what the scope
    may read. Nested paths reuse the parent's scoped queryset so the narrowing
    is not undone a level down. Only the groups whose computed value this read
    asked for."""
    wanted = {
        path: model
        for name, group in entry.prefetch_scoped.items()
        if name in computed
        for path, model in group.items()
    }
    built = {}
    # Deepest first, so a child is built before the parent that nests it, and
    # named relative to that parent. Only the roots are returned: a nested path
    # belongs inside its parent's queryset, and Django rejects the same lookup
    # arriving twice.
    for path in sorted(wanted, key=lambda p: -p.count("__")):
        queryset = scope.narrow_related(wanted[path], wanted[path].objects.all())
        for child in wanted:
            if child.rpartition("__")[0] == path:
                queryset = queryset.prefetch_related(built[child])
        built[path] = Prefetch(path.rpartition("__")[2] or path, queryset=queryset)
    return [built[path] for path in wanted if "__" not in path]


def serialize_row(obj, fields, computed=None):
    """One row as JSON-shaped values: ids as strings, dates as ISO text, a
    related object as ``{"id", "str"}``, computed values JSON-coerced."""
    row = {}
    for field in fields:
        value = getattr(obj, field, None)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, (datetime.datetime, datetime.date)):
            value = value.isoformat()
        elif isinstance(value, Model):
            # A row, not an instance: the id is what a downstream action can use.
            value = {"id": str(value.pk), "str": str(value)}
        row[field] = value
    if computed:
        for name, resolve in computed.items():
            row[name] = json.loads(json.dumps(resolve(obj), default=str))
    return row


# ---------- the queryset ----------


def _identity(value):
    return value


def build_queryset(config, scope: ReadScope, resolve=_identity):
    """``(entry, fields, queryset)`` for a read config within ``scope``.
    ``resolve`` maps a stored filter value to the one compared at run time.
    Raises ReadError for anything the config gets wrong. A value a column
    cannot hold is Django's to refuse, which it does while the filter is
    applied here or when the queryset evaluates; callers wrap both."""
    entry = READABLE_MODELS.get(config.get("model"))
    if entry is None:
        raise ReadError(f"unknown model '{config.get('model')}'")
    fields = entry.readable_fields()
    computed = effective_computed(entry, config)
    query = filters_to_q(config.get("filters"), entry, set(fields), resolve)

    order_by = config.get("order_by") or "-created_at"
    if order_by.lstrip("-") not in fields:
        raise ReadError(f"'{order_by}' is not an orderable field")

    queryset = (
        scope.narrow(entry.model, entry.model.objects.filter(entry.base_filter or Q()))
        .filter(query)
        .order_by(order_by, "id")  # id tie-break keeps pagination stable
    )
    # Computed callables dereference these per row otherwise.
    if entry.prefetch_scoped:
        queryset = queryset.prefetch_related(*scoped_prefetches(entry, scope, computed))
    if entry.select_related:
        queryset = queryset.select_related(*entry.select_related)
    if entry.prefetch_related:
        queryset = queryset.prefetch_related(*entry.prefetch_related)
    return entry, fields, queryset


# ---------- validation ----------


def validate_read_config(config, *, ops=None, modes=READ_MODES):
    """Save-time checks of a read config, as ``(code, message)`` tuples. Pure:
    nothing here touches the database. ``ops`` widens the operator set the
    shape check accepts (an unknown operator is then reported per condition);
    ``modes`` is the set of modes the caller supports."""
    entry = READABLE_MODELS.get(config.get("model"))
    if entry is None:
        return [
            (
                "action_read_unknown_model",
                f"Unknown readable model '{config.get('model')}'",
            )
        ]
    fields = set(entry.readable_fields())
    errors = []

    tree = config.get("filters")
    try:
        validate_filter_tree(tree, ops=ops)
    except ValueError as e:
        errors.append(("action_read_invalid_filters", f"Invalid filters: {e}"))
    else:
        for condition in walk_conditions(tree or {}):
            field = condition.get("field")
            op = condition.get("op", "eq")
            if field not in fields:
                errors.append(
                    (
                        "action_read_invalid_filters",
                        (
                            f"'{field}' is not a filterable field of "
                            f"'{config.get('model')}'"
                        ),
                    )
                )
            elif op not in OP_LOOKUPS:
                errors.append(
                    ("action_read_invalid_filters", f"Unknown operator {op!r}")
                )
            elif op not in allowed_ops(get_model_field(entry.model, field)):
                errors.append(
                    (
                        "action_read_invalid_filters",
                        f"Operator {op!r} is not valid for {field!r}",
                    )
                )
            if condition.get("changed"):
                errors.append(
                    (
                        "action_read_invalid_filters",
                        "'changed' only applies to event-trigger filters",
                    )
                )

    if config.get("mode", "list") not in modes:
        errors.append(
            ("action_read_invalid_mode", f"Unknown mode '{config.get('mode')}'")
        )
    order_by = config.get("order_by") or "-created_at"
    if not isinstance(order_by, str) or order_by.lstrip("-") not in fields:
        errors.append(
            (
                "action_read_invalid_order",
                f"'{order_by}' is not an orderable field of '{config.get('model')}'",
            )
        )
    limit = config.get("limit")
    if limit is not None:
        try:
            valid_limit = 1 <= int(limit) <= read_max_limit()
        except TypeError, ValueError:
            valid_limit = False
        if not valid_limit:
            errors.append(
                (
                    "action_read_invalid_limit",
                    f"Limit must be between 1 and {read_max_limit()}",
                )
            )
    return errors
