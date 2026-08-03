"""Safe rendering surface for custom Word report templates.

Custom templates are attacker-controllable Jinja (Enterprise/PRO), rendered by
docxtpl through a ``SandboxedEnvironment``. The sandbox only blocks
underscore-prefixed and internal attributes, so a live Django ORM object placed
in the template context lets a template walk an all-public path to the raw
database connection (``obj.<manager>.all().query.get_compiler(db).connection
.connection.load_extension(...)``) and execute native code.

Two complementary defenses live here:

* ``ReadOnlyModelProxy`` — an allowlist-gated view over a model instance. Only
  explicitly listed scalar fields and relations are reachable; managers,
  querysets, callables, ``.query``/``.connection``/``.path`` and everything else
  raise ``AttributeError`` (rendered as empty by Jinja). This keeps live ORM
  objects out of the template context entirely.
* ``HardenedReportSandbox`` — defense in depth: refuses attribute access on any
  Django ``Model``/``Manager``/``QuerySet`` or DB wrapper/connection instance,
  regardless of attribute name, in case such an object ever reaches the context.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.db.models import Manager, Model
from django.db.models.query import QuerySet
from jinja2.sandbox import SandboxedEnvironment

_SCALAR_TYPES = (str, bool, int, float, Decimal, UUID, datetime.date, datetime.datetime)


def _sanitize(value: Any) -> Any:
    """Coerce an allowlisted attribute value into an inert, template-safe form.

    Primitives pass through; lists/tuples/dicts are sanitized element-wise;
    anything else is stringified so no live object can leak through even if a
    relation spec is misconfigured.
    """
    if value is None or isinstance(value, _SCALAR_TYPES):
        return value
    if isinstance(value, (list, tuple)):
        return [_sanitize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    return str(value)


class ReadOnlyModelProxy:
    """Read-only, allowlist-gated view over a Django model instance.

    ``spec`` is a mapping with two keys:

    * ``fields``: iterable of scalar attribute names that may be read
    * ``relations``: mapping of related-attribute name -> nested spec

    Any attribute not in the spec, and any callable, raises ``AttributeError``.
    """

    __slots__ = ("_obj", "_spec")

    def __init__(self, obj: Model, spec: dict):
        object.__setattr__(self, "_obj", obj)
        object.__setattr__(self, "_spec", spec)

    def __getattr__(self, name: str) -> Any:
        spec = object.__getattribute__(self, "_spec")
        fields = spec.get("fields", ())
        relations = spec.get("relations", {})
        if name not in fields and name not in relations:
            raise AttributeError(name)

        value = getattr(object.__getattribute__(self, "_obj"), name)
        if callable(value):
            # No callables ever cross the template boundary.
            raise AttributeError(name)

        if name in relations:
            if value is None:
                return None
            return ReadOnlyModelProxy(value, relations[name])
        return _sanitize(value)

    def __str__(self) -> str:
        return str(object.__getattribute__(self, "_obj"))

    def __repr__(self) -> str:
        return f"<ReadOnlyModelProxy {self.__str__()!r}>"


# Attributes a report template may read from the audit (ComplianceAssessment)
# and its shallow relations. Deliberately excludes managers, m2m fields,
# scores JSON with internals, and anything that returns a live object.
AUDIT_TEMPLATE_SPEC: dict = {
    "fields": {
        "id",
        "name",
        "description",
        "ref_id",
        "version",
        "status",
        "observation",
        "eta",
        "due_date",
        "created_at",
        "updated_at",
        "min_score",
        "max_score",
        "target_score",
        "is_locked",
        "selected_implementation_groups",
    },
    "relations": {
        "framework": {
            "fields": {
                "name",
                "ref_id",
                "description",
                "urn",
                "min_score",
                "max_score",
            },
            "relations": {},
        },
        "perimeter": {
            "fields": {"name", "ref_id", "description"},
            "relations": {},
        },
        "folder": {
            "fields": {"name", "description"},
            "relations": {},
        },
    },
}


def audit_proxy(audit: Model) -> ReadOnlyModelProxy:
    """Wrap a ComplianceAssessment for safe use in a report template."""
    return ReadOnlyModelProxy(audit, AUDIT_TEMPLATE_SPEC)


class HardenedReportSandbox(SandboxedEnvironment):
    """SandboxedEnvironment that additionally refuses to expose any attribute of
    a live Django ORM object or database connection.

    This is defense in depth behind :func:`audit_proxy`: even if a live model,
    manager, queryset, database wrapper or DB-API connection ever reaches the
    template context, no attribute traversal on it is permitted, which severs
    the ``...query.get_compiler(db).connection.connection`` gadget chain.
    """

    def is_safe_attribute(self, obj: Any, attr: str, value: Any) -> bool:
        if isinstance(obj, (Model, Manager, QuerySet)):
            return False
        if _looks_like_db_object(obj):
            return False
        return super().is_safe_attribute(obj, attr, value)


def _looks_like_db_object(obj: Any) -> bool:
    """Best-effort structural check for a DB wrapper / DB-API connection / cursor
    without importing backend-specific classes."""
    module = type(obj).__module__ or ""
    if module.startswith("django.db.backends") or module.startswith(
        "django.db.models.sql"
    ):
        return True
    # DB-API connection / cursor surface (sqlite3.Connection, psycopg, etc.)
    for marker in ("execute", "cursor", "load_extension", "enable_load_extension"):
        if hasattr(obj, marker):
            # Only treat as a DB object when it is not one of our safe types.
            if not isinstance(obj, (str, bytes, dict, list, tuple)):
                return True
    return False
