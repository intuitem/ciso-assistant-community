"""Questions that point at an object already in the platform.

A derogation that does not say what it derogates from produces an exception attached to
nothing. The reverse `security_exceptions` relation lives on AppliedControl,
RequirementAssessment, Asset, RiskScenario and Vulnerability, so the form has to capture
which one — and it has to capture it as an id, not as prose a reviewer retypes.

The hard part is authorisation. A requester filing through a publication holds no role on
the domain their request lands in, so the ordinary autocomplete endpoints are closed to
them. Options are therefore served from a narrow, deliberate surface: only the model the
author's question names, only within the folder the request lands in and its ancestors.
Asking the question is what discloses the list; nothing else widens.
"""

from django.apps import apps
from django.db.models import Q

#: What a question may point at. Deliberately short: every entry is something a
#: SecurityException can hang off, plus the two scoping objects a framing request needs.
#: Adding a model here widens what a requester can enumerate, so it is a decision.
REFERENCEABLE = {
    "applied_control": {"model": "core.AppliedControl", "label": "name"},
    "asset": {"model": "core.Asset", "label": "name"},
    "risk_scenario": {"model": "core.RiskScenario", "label": "name"},
    "vulnerability": {"model": "core.Vulnerability", "label": "name"},
    "perimeter": {"model": "core.Perimeter", "label": "name"},
    "entity": {"model": "tprm.Entity", "label": "name"},
}


class ReferenceError_(Exception):
    """Raised for a question whose config names something we will not resolve."""


def config_for(question):
    config = question.config if isinstance(question.config, dict) else {}
    key = config.get("model")
    entry = REFERENCEABLE.get(key)
    if entry is None:
        raise ReferenceError_(f"unknown reference model '{key}'")
    return key, entry, bool(config.get("multiple"))


def _queryset(entry, folder, user=None):
    """Objects this caller may point at from a request in `folder`.

    Two rules, and the second one matters more than it looks. The folder chain bounds
    the answer to things the request could plausibly concern. The caller's own view
    permission then bounds it to things they were already entitled to see — without
    that, asking a question would hand a requester the names of every object in every
    ancestor folder up to the root, which is a disclosure the author never made.

    The request's own folder is always included: whatever lives there belongs to the
    request, and a personal space would otherwise offer nothing at all.
    """
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
    """Every id must name an object of the configured model within reach of the request.

    Without this an answer is an arbitrary UUID, and the label lookup that renders it
    would happily read back rows the requester was never entitled to see.
    """
    key, entry, multiple = config_for(question)
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
        raise ReferenceError_("object references must be a list of ids")
    if not multiple and len(ids) > 1:
        raise ReferenceError_("this question accepts a single object")
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
        raise ReferenceError_(f"unreachable object reference: {unknown[0]}")
    return ids


def labels_for(question, folder, ids, user=None):
    """Resolve stored ids back to something a human reads. Scoped the same way as the
    options, so a stale id that has since moved out of reach simply stops resolving."""
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
