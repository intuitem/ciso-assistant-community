"""Packages a live portal as a library document, so a design travels through the
existing library store rather than a transport of its own."""

import re

from .references import URN_TARGET_FIELDS, dereference, _iter_items

DEFAULT_PACKAGER = "personal"
_LEAF_FORBIDDEN = re.compile(r"[^0-9a-z\-\._]+")


def _urn_leaf(value: str) -> str:
    return _LEAF_FORBIDDEN.sub("-", str(value).lower().strip()).strip("-") or "portal"


def _referenced_library_urns(content):
    """Read off the DEREFERENCED content, so a dropped reference adds no dependency."""
    by_field = {
        f"{field}_urn": model
        for fields in URN_TARGET_FIELDS.values()
        for field, model in fields
    }
    wanted = {model: set() for model in by_field.values()}
    for item in _iter_items(content):
        target = item.get("target") or {}
        for key, model in by_field.items():
            if target.get(key):
                wanted[model].add(str(target[key]).lower())
    urns = set()
    for model, target_urns in wanted.items():
        if not target_urns:
            continue
        urns.update(
            u
            for u in model.objects.filter(urn__in=target_urns).values_list(
                "library__urn", flat=True
            )
            if u
        )
    return sorted(urns)


def build_preset_library(portal, packager=DEFAULT_PACKAGER):
    """Returns (document, unwired). The document is always produced."""
    content, unwired = dereference(portal.content or {})
    leaf = _urn_leaf(portal.name)
    document = {
        "urn": f"urn:{packager}:risk:library:portal-{leaf}",
        "locale": "en",
        "ref_id": f"portal-{leaf}",
        "name": portal.name,
        "description": portal.description
        or f"Portal design exported from {portal.name}",
        "version": 1,
        "provider": packager,
        "packager": packager,
        "objects": {
            "portal_presets": [
                {
                    "urn": f"urn:{packager}:risk:portal_preset:{leaf}",
                    "ref_id": leaf,
                    "name": portal.name,
                    "description": portal.description or "",
                    "content": content,
                }
            ]
        },
    }
    if dependencies := _referenced_library_urns(content):
        document["dependencies"] = dependencies
    return document, unwired
