"""What an editor needs to offer the readable models: fields with their
kinds, annotations, computed values and the aggregate function catalog.
One payload for every builder (workflow read steps, derived metrics)."""

from __future__ import annotations

from .aggregates import function_catalog
from .entries import READABLE_MODELS
from .filters import field_kind


def registry_payload():
    """One entry per readable model. The function catalog is the same for
    every model; it travels on each entry so a builder reads one list."""
    functions = function_catalog()
    return [
        {
            "key": key,
            "fields": entry.readable_fields(),
            # What each field holds: decides the operators a filter and the
            # functions an aggregate may use.
            "kinds": {
                name: field_kind(entry, name) for name in entry.readable_fields()
            },
            # Fields with a fixed set of values: what a derived metric may
            # group by.
            "categorical": entry.categorical_fields(),
            # Database-side values among the fields.
            "annotations": sorted(entry.annotations),
            # Output-only values; not filterable/orderable, but a worker-side
            # aggregate can run over them.
            "computed": sorted(entry.computed.keys()),
            # Same, but only resolved when a read names them in `include`:
            # they cost too much to return by default.
            "includable": sorted(entry.optional_computed.keys()),
            "aggregates": functions,
        }
        for key, entry in READABLE_MODELS.items()
    ]
