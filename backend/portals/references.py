"""Portal tile targets point at local rows by pk; a packaged design names them by
URN instead. Neither direction fails: an unresolvable reference leaves its tile
unwired, which the editor already flags.

A target holds one reference per field, never both: live portal content holds the
local id (`framework`), preset content holds the URN (`framework_urn`) wherever the
row has one. A URN kept next to an id would go stale as soon as the author picks
another target in the editor, and then win over the author's pick."""

import copy

from django.core.exceptions import ValidationError

from core.models import Framework, QuickForm, QuickFormPublication

URN_TARGET_FIELDS = {
    "assessment": [("framework", Framework)],
    "quickForm": [("quick_form", QuickForm)],
}

# Dropped on export only: they name rows of this instance. Dropping them costs a
# default, not a capability: an absent domain means the clicker picks one, an
# absent reviewer means the requester reviews their own.
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


def _first(queryset, field, pk):
    """One column of the row behind a local id, or None. Content is author-written
    JSON, so the id may not even be a UUID; that is "not found", not a crash."""
    try:
        return queryset.filter(pk=pk).values_list(field, flat=True).first()
    except ValidationError, ValueError:
        return None


def _urn_of(model, pk):
    return _first(model.objects, "urn", pk)


def _carry_publication_form(target, title, unwired, keep_local_ids):
    """A quick form tile may be wired through a publication alone. The publication
    is local (audience, submission folder), but the form behind it can travel, so
    the tile leaves as `quick_form` and is rewired to the form on arrival.

    The publication decides the form, as it does when the tile is clicked: a
    `quick_form` next to it is a leftover the editor hides, not the author's pick."""
    publication = target.get("publication")
    if not publication:
        target.pop("publication", None)
        return
    form_id = _first(QuickFormPublication.objects, "quick_form_id", publication)
    if form_id is not None:
        target["quick_form"] = str(form_id)
    elif not target.get("quick_form"):
        if not keep_local_ids:
            target.pop("publication", None)
            unwired.append(
                f"'{title}' travels unwired: its publication is not on this "
                "instance, so there is no quick form to travel under."
            )
        return
    if not keep_local_ids:
        target.pop("publication", None)


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
        if item.get("kind") == "quickForm":
            _carry_publication_form(target, title, unwired, keep_local_ids)
        for field, model in URN_TARGET_FIELDS.get(item.get("kind"), []):
            value = target.get(field)
            if not value:
                # Nothing picked here: a URN that never resolved on this instance
                # is the only record of the intended target, so it travels on.
                target.pop(field, None)
                continue
            # The id is what the tile runs on, so it alone decides what travels.
            target.pop(f"{field}_urn", None)
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
        if not keep_local_ids:
            for field in LOCAL_ONLY_FIELDS:
                target.pop(field, None)
    return out, unwired


def resolve(content):
    """Preset content -> portal content. Returns (content, unwired). A resolved URN
    is replaced by the local id (dereference derives it back on export); one that
    does not resolve stays, so the tile can still be wired once its library is."""
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
            target.pop(f"{field}_urn", None)
    return out, unwired
