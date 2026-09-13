"""Portal tile targets point at local rows by pk; a packaged design names them by
URN instead. Neither direction fails: an unresolvable reference leaves its tile
unwired, which the editor already flags."""

import copy

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


def dereference(content):
    """Portal content -> preset content. Returns (content, unwired)."""
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
            value = target.pop(field, None)
            if not value:
                continue
            urn = model.objects.filter(pk=value).values_list("urn", flat=True).first()
            if not urn:
                unwired.append(
                    f"'{title}' travels unwired: its {field.replace('_', ' ')} is not "
                    "library-backed, so it has no URN to travel under."
                )
                continue
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
                unwired.append(
                    f"'{title}' stays unwired: {urn} is not loaded. Load the library "
                    "it comes from, or pick a replacement in the editor."
                )
                continue
            target[field] = str(obj.id)
    return out, unwired
