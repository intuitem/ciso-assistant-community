"""Questions that point at an object already in the platform."""

import uuid

from django.apps import apps
from django.db.models import Q

#: Widening this widens what a requester may enumerate.
REFERENCEABLE = {
    "applied_control": {"model": "core.AppliedControl", "label": "name"},
    "asset": {"model": "core.Asset", "label": "name"},
    "risk_scenario": {"model": "core.RiskScenario", "label": "name"},
    "vulnerability": {"model": "core.Vulnerability", "label": "name"},
    "perimeter": {"model": "core.Perimeter", "label": "name"},
    "entity": {"model": "tprm.Entity", "label": "name"},
}


class ReferenceError_(Exception):
    """`code` goes in the response, `detail` in the log — never exception text."""

    def __init__(self, code: str, detail: str = ""):
        self.code = code
        self.detail = detail
        super().__init__(detail or code)


def config_for(question):
    config = question.config if isinstance(question.config, dict) else {}
    key = config.get("model")
    entry = REFERENCEABLE.get(key)
    if entry is None:
        raise ReferenceError_(
            "unknownReferenceModel", f"unknown reference model '{key}'"
        )
    return key, entry, bool(config.get("multiple"))


def _queryset(entry, folder, user=None):
    """Bounded by the folder chain and by what the caller may already view."""
    from iam.models import RoleAssignment

    model = apps.get_model(entry["model"])
    ancestors = [folder] + list(folder.get_parent_folders())
    qs = model.objects.filter(folder__in=ancestors)
    if user is None:
        return qs
    viewable = RoleAssignment.get_viewable_object_ids(user, model)
    return qs.filter(Q(id__in=viewable) | Q(folder=folder))


def options_for(question, folder, search="", limit=50, user=None):
    key, entry, _multiple = config_for(question)
    qs = _queryset(entry, folder, user)
    label_field = entry["label"]
    if search:
        qs = qs.filter(**{f"{label_field}__icontains": search})
    rows = qs.order_by(label_field)[:limit]
    return {"model": key, "results": [_row(o, label_field) for o in rows]}


def _row(obj, label_field):
    ref_id = getattr(obj, "ref_id", None)
    label = getattr(obj, label_field, "") or str(obj)
    return {
        "id": str(obj.id),
        "label": f"{ref_id} - {label}" if ref_id else label,
        "folder": obj.folder.name if getattr(obj, "folder_id", None) else None,
    }


def validate_ids(question, folder, ids, user=None):
    """Reject ids the caller could not have been offered."""
    key, entry, multiple = config_for(question)
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
        raise ReferenceError_(
            "referenceMustBeListOfIds", "object references must be a list of ids"
        )
    # Parsed before the query: a malformed value reaching a UUID `id__in` lookup raises
    # Django's ValidationError, which callers of this function do not catch.
    for i in ids:
        try:
            uuid.UUID(i)
        except ValueError, AttributeError, TypeError:
            raise ReferenceError_(
                "referenceMustBeListOfIds", f"not a uuid: {i}"
            ) from None
    if not multiple and len(ids) > 1:
        raise ReferenceError_(
            "onlyOneObjectAllowed", "this question accepts a single object"
        )
    if not ids:
        return []
    found = set(
        str(pk)
        for pk in _queryset(entry, folder, user)
        .filter(id__in=ids)
        .values_list("id", flat=True)
    )
    unknown = [i for i in ids if i not in found]
    if unknown:
        raise ReferenceError_(
            "unreachableObjectReference", f"unreachable object reference: {unknown[0]}"
        )
    return ids


def labels_for(question, folder, ids, user=None):
    """Ids back to labels, scoped like the options: an out-of-reach id stops resolving."""
    if not ids:
        return []
    _key, entry, _multiple = config_for(question)
    label_field = entry["label"]
    by_id = {str(o.id): o for o in _queryset(entry, folder, user).filter(id__in=ids)}
    return [
        _row(by_id[i], label_field)
        if i in by_id
        else {"id": i, "label": i, "folder": None}
        for i in ids
    ]
