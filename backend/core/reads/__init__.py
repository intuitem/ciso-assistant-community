"""Reading objects through a declared surface.

``READABLE_MODELS`` says which models may be read and how; the filter tree
says which rows; ``ReadScope`` says where the caller may look. The workflow
engine's ``read_objects`` action is one consumer; derived metrics are another.
"""

from .entries import BASE_READ_FIELDS, READABLE_MODELS, ReadEntry
from .filters import (
    MAX_FILTER_DEPTH,
    OP_LOOKUPS,
    ReadError,
    allowed_ops,
    condition_to_q,
    filters_to_q,
    get_model_field,
    group_to_q,
    validate_filter_tree,
    walk_conditions,
)
from .query import (
    READ_DEFAULT_LIMIT,
    READ_MODES,
    ReadScope,
    accessible_folder_ids,
    build_queryset,
    effective_computed,
    page_limit,
    read_max_limit,
    scoped_prefetches,
    serialize_row,
    subtree_folder_ids,
    validate_read_config,
)

__all__ = [
    "BASE_READ_FIELDS",
    "MAX_FILTER_DEPTH",
    "OP_LOOKUPS",
    "READABLE_MODELS",
    "READ_DEFAULT_LIMIT",
    "READ_MODES",
    "ReadEntry",
    "ReadError",
    "ReadScope",
    "accessible_folder_ids",
    "allowed_ops",
    "build_queryset",
    "condition_to_q",
    "effective_computed",
    "filters_to_q",
    "get_model_field",
    "group_to_q",
    "page_limit",
    "read_max_limit",
    "scoped_prefetches",
    "serialize_row",
    "subtree_folder_ids",
    "validate_filter_tree",
    "validate_read_config",
    "walk_conditions",
]
