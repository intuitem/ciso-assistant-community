"""
DORA ROI Linting Module

This module provides validation functions for DORA Register of Information (ROI) exports.
It checks for mandatory and recommended fields before generating the actual report.
"""

from typing import List, Dict, Any
from tprm.models import Entity
from core.models import Asset
from django.db.models import Q
import re


def lint_main_entity(entity: Entity) -> List[Dict[str, Any]]:
    """
    Validate the main entity for DORA ROI requirements.

    Args:
        entity: The main Entity instance to validate

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Check legal identifiers (mandatory)
    has_legal_identifier = False
    if entity.legal_identifiers:
        # Check for any of the accepted identifiers: LEI, EUID, VAT, DUNS
        identifier_types = ["LEI", "EUID", "VAT", "DUNS"]
        for id_type in identifier_types:
            if entity.legal_identifiers.get(id_type):
                has_legal_identifier = True
                break

    if has_legal_identifier:
        results.append(
            {
                "severity": "ok",
                "category": "Main Entity",
                "message": "Legal identifier found",
                "field": "legal_identifiers",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )
    else:
        results.append(
            {
                "severity": "error",
                "category": "Main Entity",
                "message": "Main entity must have at least one legal identifier (LEI, EUID, VAT, or DUNS)",
                "field": "legal_identifiers",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )

    # Check country (mandatory)
    if entity.country:
        results.append(
            {
                "severity": "ok",
                "category": "Main Entity",
                "message": "Country is set",
                "field": "country",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )
    else:
        results.append(
            {
                "severity": "error",
                "category": "Main Entity",
                "message": "Main entity must have a country set",
                "field": "country",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )

    # Check DORA entity type (mandatory)
    if entity.dora_entity_type:
        results.append(
            {
                "severity": "ok",
                "category": "Main Entity",
                "message": "Entity type is set",
                "field": "dora_entity_type",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )
    else:
        results.append(
            {
                "severity": "error",
                "category": "Main Entity",
                "message": "Main entity must have a DORA entity type set",
                "field": "dora_entity_type",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )

    # Check DORA competent authority (mandatory)
    if entity.dora_competent_authority:
        results.append(
            {
                "severity": "ok",
                "category": "Main Entity",
                "message": "Competent authority is set",
                "field": "dora_competent_authority",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )
    else:
        results.append(
            {
                "severity": "error",
                "category": "Main Entity",
                "message": "Main entity must have a DORA competent authority set",
                "field": "dora_competent_authority",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )

    # Check currency (mandatory)
    if entity.currency:
        results.append(
            {
                "severity": "ok",
                "category": "Main Entity",
                "message": "Currency is set",
                "field": "currency",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )
    else:
        results.append(
            {
                "severity": "error",
                "category": "Main Entity",
                "message": "Main entity must have a currency set",
                "field": "currency",
                "object_type": "entities",
                "object_id": str(entity.id),
                "object_name": entity.name,
            }
        )

    return results


def lint_subsidiaries(main_entity: Entity) -> List[Dict[str, Any]]:
    """
    Validate subsidiaries for DORA ROI requirements.

    Subsidiaries are entities with the main entity as parent and dora_provider_person_type set.

    Args:
        main_entity: The main Entity instance

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get all subsidiaries (entities with parent=main_entity and dora_provider_person_type set)
    subsidiaries = Entity.objects.filter(
        parent_entity=main_entity, dora_provider_person_type__isnull=False
    ).exclude(dora_provider_person_type="")

    if not subsidiaries.exists():
        # No subsidiaries found - this is OK, not an error
        return results

    # Check each subsidiary
    for subsidiary in subsidiaries:
        # Check legal identifiers (mandatory)
        has_legal_identifier = False
        if subsidiary.legal_identifiers:
            identifier_types = ["LEI", "EUID", "VAT", "DUNS"]
            for id_type in identifier_types:
                if subsidiary.legal_identifiers.get(id_type):
                    has_legal_identifier = True
                    break

        if not has_legal_identifier:
            results.append(
                {
                    "severity": "error",
                    "category": "Subsidiaries",
                    "message": f"Subsidiary '{subsidiary.name}' must have at least one legal identifier (LEI, EUID, VAT, or DUNS)",
                    "field": "legal_identifiers",
                    "object_type": "entities",
                    "object_id": str(subsidiary.id),
                    "object_name": subsidiary.name,
                }
            )

        # Check country (mandatory)
        if not subsidiary.country:
            results.append(
                {
                    "severity": "error",
                    "category": "Subsidiaries",
                    "message": f"Subsidiary '{subsidiary.name}' must have a country set",
                    "field": "country",
                    "object_type": "entities",
                    "object_id": str(subsidiary.id),
                    "object_name": subsidiary.name,
                }
            )

        # Check DORA entity type (mandatory)
        if not subsidiary.dora_entity_type:
            results.append(
                {
                    "severity": "error",
                    "category": "Subsidiaries",
                    "message": f"Subsidiary '{subsidiary.name}' must have a DORA entity type set",
                    "field": "dora_entity_type",
                    "object_type": "entities",
                    "object_id": str(subsidiary.id),
                    "object_name": subsidiary.name,
                }
            )

        # Check DORA entity hierarchy (mandatory)
        if not subsidiary.dora_entity_hierarchy:
            results.append(
                {
                    "severity": "error",
                    "category": "Subsidiaries",
                    "message": f"Subsidiary '{subsidiary.name}' must have a DORA entity hierarchy set",
                    "field": "dora_entity_hierarchy",
                    "object_type": "entities",
                    "object_id": str(subsidiary.id),
                    "object_name": subsidiary.name,
                }
            )

    # If we have subsidiaries and no errors, add a success message
    if subsidiaries.exists() and not results:
        results.append(
            {
                "severity": "ok",
                "category": "Subsidiaries",
                "message": f"All {subsidiaries.count()} subsidiaries have required fields set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    return results


def lint_business_functions() -> List[Dict[str, Any]]:
    """
    Validate that business function assets exist in the system.

    DORA ROI requires at least one asset with is_business_function flag set.
    Additionally checks that ref_id follows the pattern 'F' + number (e.g., F1, F2, F100).

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Check if there are any business function assets
    business_functions = Asset.objects.filter(is_business_function=True)

    if not business_functions.exists():
        results.append(
            {
                "severity": "error",
                "category": "Business Functions",
                "message": "At least one asset with 'Business Function' flag must be defined",
                "field": "is_business_function",
                "object_type": "assets",
                "object_id": None,
                "object_name": None,
            }
        )
        return results

    # Pattern for ref_id: F followed by one or more digits
    ref_id_pattern = re.compile(r"^F\d+$")

    # Check each business function's ref_id
    invalid_ref_ids = []
    valid_count = 0

    for bf in business_functions:
        if not bf.ref_id or not ref_id_pattern.match(bf.ref_id):
            invalid_ref_ids.append(bf)
        else:
            valid_count += 1

    # Report results
    if invalid_ref_ids:
        for bf in invalid_ref_ids:
            ref_id_display = bf.ref_id if bf.ref_id else "(empty)"
            results.append(
                {
                    "severity": "warning",
                    "category": "Business Functions",
                    "message": f"Business function '{bf.name}' has ref_id '{ref_id_display}' that doesn't match pattern 'F' + number (e.g., F1, F2)",
                    "field": "ref_id",
                    "object_type": "assets",
                    "object_id": str(bf.id),
                    "object_name": bf.name,
                }
            )

    # Add success message if all business functions have valid ref_ids
    if valid_count == business_functions.count():
        results.append(
            {
                "severity": "ok",
                "category": "Business Functions",
                "message": f"All {business_functions.count()} business function(s) have valid ref_id pattern",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )
    elif valid_count > 0:
        results.append(
            {
                "severity": "ok",
                "category": "Business Functions",
                "message": f"{valid_count} of {business_functions.count()} business function(s) have valid ref_id pattern",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    return results


def lint_dora_roi() -> Dict[str, Any]:
    """
    Perform comprehensive linting for DORA ROI export.

    Returns:
        Dictionary containing validation results and summary
    """
    results = []

    # Get the main entity
    main_entity = Entity.get_main_entity()

    if not main_entity:
        return {
            "results": [
                {
                    "severity": "error",
                    "category": "Main Entity",
                    "message": "No main entity found in the system",
                    "field": None,
                    "object_type": None,
                    "object_id": None,
                    "object_name": None,
                }
            ],
            "summary": {"errors": 1, "warnings": 0, "ok": 0},
        }

    # Run all validation checks
    results.extend(lint_main_entity(main_entity))
    results.extend(lint_subsidiaries(main_entity))
    results.extend(lint_business_functions())

    # Calculate summary
    summary = {
        "errors": sum(1 for r in results if r["severity"] == "error"),
        "warnings": sum(1 for r in results if r["severity"] == "warning"),
        "ok": sum(1 for r in results if r["severity"] == "ok"),
    }

    return {"results": results, "summary": summary}
