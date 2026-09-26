"""Packages a live portal as a library document, so a design travels through the
existing library store rather than a transport of its own.

Identity follows the portal, not its name: the library and preset URNs are minted
from the portal's id, so a rename or a namesake elsewhere never forks or collides
with what a design already shipped as. The version goes up whenever what ships
changes, so a new export of an edited portal loads as an update of the last one.

References are soft: the document declares no `dependencies`. Tiles name their
frameworks and quick forms by URN and are wired when a portal is cloned from the
preset; one whose library is not loaded stays unwired instead of failing the load
(or silently upgrading that library, which a declared dependency would do)."""

import hashlib
import json
import re

from django.db import transaction

from .models import Portal
from .references import dereference

DEFAULT_PACKAGER = "personal"
_LEAF_FORBIDDEN = re.compile(r"[^0-9a-z\-\._]+")


def _urn_leaf(value: str) -> str:
    return _LEAF_FORBIDDEN.sub("-", str(value).lower().strip()).strip("-") or "portal"


def _stamp_version(portal, shipped) -> int:
    """The version this export ships as: the last one if nothing that ships changed
    since, the next one otherwise. Locked so two exports of one edit agree."""
    fingerprint = hashlib.sha256(
        json.dumps(shipped, sort_keys=True, default=str).encode()
    ).hexdigest()
    with transaction.atomic():
        row = (
            Portal.objects.select_for_update()
            .only("export_version", "export_fingerprint")
            .get(pk=portal.pk)
        )
        version = row.export_version
        if not version or row.export_fingerprint != fingerprint:
            version += 1
            Portal.objects.filter(pk=portal.pk).update(
                export_version=version, export_fingerprint=fingerprint
            )
    portal.export_version, portal.export_fingerprint = version, fingerprint
    return version


def build_preset_library(portal, packager=DEFAULT_PACKAGER):
    """Returns (document, unwired). The document is always produced."""
    content, unwired = dereference(portal.content or {})
    leaf = str(portal.id)
    urn = f"urn:{packager}:risk:library:portal-{leaf}"
    description = portal.description or f"Portal design exported from {portal.name}"
    preset = {
        "urn": f"urn:{packager}:risk:portal_preset:{leaf}",
        "ref_id": leaf,
        "name": portal.name,
        "description": portal.description or "",
        "content": content,
    }
    version = _stamp_version(
        portal,
        {"urn": urn, "name": portal.name, "description": description, "preset": preset},
    )
    document = {
        "urn": urn,
        "locale": "en",
        "ref_id": f"portal-{leaf}",
        "name": portal.name,
        "description": description,
        "version": version,
        "provider": packager,
        "packager": packager,
        "objects": {"portal_presets": [preset]},
    }
    return document, unwired
