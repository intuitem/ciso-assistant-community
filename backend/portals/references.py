"""Portal tile targets point at local rows by pk; a packaged design names them by
URN instead. Neither direction fails: an unresolvable reference leaves its tile
unwired, which the editor already flags."""

import copy

from django.core.exceptions import ValidationError

from core.models import Framework, QuickForm

URN_TARGET_FIELDS = {
    "assessment": [("framework", Framework)],
    "quickForm": [("quick_form", QuickForm)],
}

# Dropping these costs a default, not a capability: an absent domain means the
# clicker picks one, an absent reviewer means the requester reviews their own.
LOCAL_ONLY_FIELDS = ("folder", "reviewers")


# (field, why) per tile kind, for targets with no catalog counterpart to name.
UNPORTABLE_TARGET_FIELDS = {
    "framework": ("snapshot", "a framework snapshot is a frozen view of a local audit"),
    "certificationDocument": (
        "token",
        "an uploaded document cannot travel with a preset",
    ),
}


def _iter_items(content):
    for section in (content or {}).get("sections", []) or []:
        for item in section.get("items", []) or []:
            if isinstance(item, dict):
                yield item


def _urn_of(model, pk):
    """The URN behind a local id, or None. Content is author-written JSON, so the
    id may not even be a UUID; that is "not found", not a crash."""
    try:
        return model.objects.filter(pk=pk).values_list("urn", flat=True).first()
    except ValidationError, ValueError:
        return None


def dereference(content, keep_local_ids=False):
    """Portal content -> preset content. Returns (content, unwired).

    `keep_local_ids` is for a preset that stays on this instance: a target with no
    URN keeps its local id so the design still works here. An export drops it, since
    a foreign id would only make the tile look wired."""
    out = copy.deepcopy(content or {})
    unwired = []
    for item in _iter_items(out):
        title = item.get("title") or item.get("kind") or "tile"
        target = item.get("target")
        if not isinstance(target, dict):
            continue
        unportable = UNPORTABLE_TARGET_FIELDS.get(item.get("kind"))
        if unportable and target.pop(unportable[0], None):
            unwired.append(f"'{title}' travels unwired: {unportable[1]}.")
        for field, model in URN_TARGET_FIELDS.get(item.get("kind"), []):
            value = target.get(field)
            if not value:
                target.pop(field, None)
                continue
            urn = _urn_of(model, value)
            if not urn:
                if not keep_local_ids:
                    target.pop(field, None)
                    unwired.append(
                        f"'{title}' travels unwired: its {field.replace('_', ' ')} is "
                        "not library-backed, so it has no URN to travel under."
                    )
                continue
            target.pop(field, None)
            target[f"{field}_urn"] = urn
        # The quick form itself travels, so the tile survives losing its publication.
        target.pop("publication", None)
        for field in LOCAL_ONLY_FIELDS:
            target.pop(field, None)
    return out, unwired


def resolve(content):
    """Preset content -> portal content. Returns (content, unwired). The URN is
    kept alongside the resolved id, so the design stays re-exportable."""
    out = copy.deepcopy(content or {})
    unwired = []
    for item in _iter_items(out):
        target = item.get("target")
        if not isinstance(target, dict):
            continue
        title = item.get("title") or item.get("kind") or "tile"
        for field, model in URN_TARGET_FIELDS.get(item.get("kind"), []):
            urn = target.get(f"{field}_urn")
            if not urn:
                continue
            obj = model.objects.filter(urn=str(urn).lower()).first()
            if obj is None:
                # Whatever id travelled with the URN points at a row this instance
                # does not have; a dangling id would only make the tile look wired.
                target.pop(field, None)
                unwired.append(
                    f"'{title}' stays unwired: {urn} is not loaded. Load the library "
                    "it comes from, or pick a replacement in the editor."
                )
                continue
            target[field] = str(obj.id)
    return out, unwired
