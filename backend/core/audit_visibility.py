"""
Consistency checker for RBAC visibility.

`audit_visibility_leaks` walks every “reference” object (assessments, threats,
controls, assets, incidents…) and reports related objects that readers of the
reference object may not see.
"""

from __future__ import annotations

from typing import Iterable

from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    FindingsAssessment,
    Folder,
    Incident,
    RiskAssessment,
    Threat,
    RequirementAssessment,
    RiskScenario,
)
from iam.models import RoleAssignment

REFERENCE_MODEL_RELATIONS = {
    AppliedControl: [
        "assets",
        "evidences",
        "findings",
        "risk_scenarios",
        "security_exceptions",
        "requirement_assessments",
    ],
    Threat: ["risk_scenarios"],
    Asset: ["parent_assets", "risk_scenarios", "applied_controls"],
}


def _iter_related(value) -> Iterable:
    """Uniformise l’itération sur un champ FK vs ManyToMany."""
    if value is None:
        return ()
    return value.all() if hasattr(value, "all") else (value,)


def _allowed_folder_ids(folder: Folder) -> set:
    """Dossier + sous-arbre. À enrichir plus tard avec les liens de visibilité."""
    allowed = {folder.id}
    allowed.update(f.id for f in folder.get_sub_folders())
    return allowed


def _accessible_ids(folder: Folder, admin, model: type):
    """Return the set of IDs accessible to the admin for a given model, from folder."""
    try:
        view_ids, _, _ = RoleAssignment.get_accessible_object_ids(folder, admin, model)
    except NotImplementedError:
        return None
    return set(view_ids)


def audit_visibility_leaks(user) -> list[dict]:
    """
    return RBAC inconsistencies
    """

    leaks: list[dict] = []

    for scope_folder in Folder.objects.all():
        print("parsing", scope_folder)

        for model, relations in REFERENCE_MODEL_RELATIONS.items():
            for relation in relations:
                field = model._meta.get_field(relation)
                related_model = getattr(field, "related_model", None) or getattr(
                    field.remote_field, "model", None
                )
                accessible_refs = _accessible_ids(scope_folder, user, related_model)
                for instance in model.objects.all():
                    if Folder.get_folder(instance) != scope_folder:
                        continue
                    related_values = getattr(instance, relation, None)
                    for related in _iter_related(related_values):
                        if related is None:
                            continue

                        related_folder = Folder.get_folder(related)

                        if accessible_refs is not None:
                            if related.id in accessible_refs:
                                continue

                        leaks.append(
                            {
                                "scope_folder_id": scope_folder.id,
                                "scope_folder_name": scope_folder.name,
                                "reference_model": model.__name__,
                                "reference_id": instance.id,
                                "reference_name": getattr(
                                    instance, "name", str(instance)
                                ),
                                "reference_folder": instance.folder_id,
                                "reference_folder_name": getattr(
                                    getattr(instance, "folder", None), "name", None
                                ),
                                "relation": relation,
                                "secondary_model": related.__class__.__name__,
                                "secondary_id": related.id,
                                "secondary_name": getattr(
                                    related, "name", str(related)
                                ),
                                "secondary_folder": getattr(related_folder, "id", None),
                                "secondary_folder_name": getattr(
                                    related_folder, "name", None
                                ),
                            }
                        )

    return leaks
