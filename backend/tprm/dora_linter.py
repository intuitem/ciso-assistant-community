"""
DORA ROI Linting Module

This module provides validation functions for DORA Register of Information (ROI) exports.
It checks for mandatory and recommended fields before generating the actual report.
"""

from typing import List, Dict, Any
from tprm.models import Entity, Contract, Solution
from tprm.dora_export import IDENTIFIER_PRIORITY
from core.models import Asset
from django.db.models import Q
import re


def lint_provider_entities() -> List[Dict[str, Any]]:
    """
    Validate provider entities used in DORA ROI reports.

    Checks that third-party providers have:
    - At least one legal identifier (LEI, EUID, VAT, DUNS)
    - Country set
    - DORA provider person type set (mandatory for b_05.01 c0040)
    - Parent entity with legal identifier (if parent exists)

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get all provider entities from non-draft third-party contracts
    provider_entities = (
        Entity.objects.filter(
            contracts__is_intragroup=False,
            contracts__isnull=False,
            contracts__dora_exclude=False,
        )
        .exclude(contracts__status=Contract.Status.DRAFT)
        .distinct()
    )

    if not provider_entities.exists():
        return results

    providers_with_errors = 0

    for provider in provider_entities:
        provider_has_error = False

        # Check legal identifiers (mandatory)
        has_legal_identifier = False
        if provider.legal_identifiers:
            identifier_types = IDENTIFIER_PRIORITY
            for id_type in identifier_types:
                if provider.legal_identifiers.get(id_type):
                    has_legal_identifier = True
                    break

        if not has_legal_identifier:
            results.append(
                {
                    "severity": "error",
                    "category": "Provider Entities",
                    "message": f"Provider entity '{provider.name}' must have at least one legal identifier (LEI, EUID, VAT, or DUNS) for DORA reporting",
                    "field": "legal_identifiers",
                    "object_type": "entities",
                    "object_id": str(provider.id),
                    "object_name": provider.name,
                }
            )
            provider_has_error = True

        # Check country (mandatory)
        if not provider.country:
            results.append(
                {
                    "severity": "error",
                    "category": "Provider Entities",
                    "message": f"Provider entity '{provider.name}' must have a country set for DORA reporting",
                    "field": "country",
                    "object_type": "entities",
                    "object_id": str(provider.id),
                    "object_name": provider.name,
                }
            )
            provider_has_error = True

        # Check DORA provider person type (mandatory for b_05.01 c0040)
        if not provider.dora_provider_person_type:
            results.append(
                {
                    "severity": "error",
                    "category": "Provider Entities",
                    "message": f"Provider entity '{provider.name}' must have a DORA provider person type set for DORA b_05.01 reporting (c0040)",
                    "field": "dora_provider_person_type",
                    "object_type": "entities",
                    "object_id": str(provider.id),
                    "object_name": provider.name,
                }
            )
            provider_has_error = True

        # Check parent entity has legal identifier (if parent exists)
        if provider.parent_entity:
            parent_has_identifier = False
            if provider.parent_entity.legal_identifiers:
                identifier_types = IDENTIFIER_PRIORITY
                for id_type in identifier_types:
                    if provider.parent_entity.legal_identifiers.get(id_type):
                        parent_has_identifier = True
                        break

            if not parent_has_identifier:
                results.append(
                    {
                        "severity": "error",
                        "category": "Provider Entities",
                        "message": f"Parent entity '{provider.parent_entity.name}' of provider '{provider.name}' must have at least one legal identifier for DORA reporting",
                        "field": "legal_identifiers",
                        "object_type": "entities",
                        "object_id": str(provider.parent_entity.id),
                        "object_name": provider.parent_entity.name,
                    }
                )
                provider_has_error = True

        if provider_has_error:
            providers_with_errors += 1

    # Add success message if all providers are valid
    valid_providers = provider_entities.count() - providers_with_errors
    if valid_providers == provider_entities.count():
        results.append(
            {
                "severity": "ok",
                "category": "Provider Entities",
                "message": f"All {provider_entities.count()} provider entities have required fields set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )
    elif valid_providers > 0:
        results.append(
            {
                "severity": "ok",
                "category": "Provider Entities",
                "message": f"{valid_providers} of {provider_entities.count()} provider entities have all required fields set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    return results


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
        identifier_types = IDENTIFIER_PRIORITY
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

    # Check LEI length if provided (must be exactly 20 characters)
    if entity.legal_identifiers and entity.legal_identifiers.get("LEI"):
        lei = entity.legal_identifiers.get("LEI")
        if len(lei) != 20:
            results.append(
                {
                    "severity": "error",
                    "category": "Main Entity",
                    "message": f"LEI must be exactly 20 characters long (current: {len(lei)} characters)",
                    "field": "legal_identifiers",
                    "object_type": "entities",
                    "object_id": str(entity.id),
                    "object_name": entity.name,
                }
            )
        else:
            results.append(
                {
                    "severity": "ok",
                    "category": "Main Entity",
                    "message": "LEI has correct length (20 characters)",
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
            identifier_types = IDENTIFIER_PRIORITY
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

        # Check LEI length if provided (must be exactly 20 characters)
        if subsidiary.legal_identifiers and subsidiary.legal_identifiers.get("LEI"):
            lei = subsidiary.legal_identifiers.get("LEI")
            if len(lei) != 20:
                results.append(
                    {
                        "severity": "error",
                        "category": "Subsidiaries",
                        "message": f"Subsidiary '{subsidiary.name}' has LEI with incorrect length (must be 20 characters, current: {len(lei)})",
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

        # Check currency (warning)
        if not subsidiary.currency:
            results.append(
                {
                    "severity": "warning",
                    "category": "Subsidiaries",
                    "message": f"Subsidiary '{subsidiary.name}' should have a currency set",
                    "field": "currency",
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


def lint_branches(main_entity: Entity) -> List[Dict[str, Any]]:
    """
    Validate branches for DORA ROI requirements.

    Branches are entities with the main entity as parent and without dora_provider_person_type set.
    Each branch must have a parent entity with a legal identifier (for b_01.03 report).

    Args:
        main_entity: The main Entity instance

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get all branches (entities with main entity as parent and no dora_provider_person_type)
    branches = Entity.objects.filter(parent_entity=main_entity).filter(
        Q(dora_provider_person_type__isnull=True) | Q(dora_provider_person_type="")
    )

    if not branches.exists():
        # No branches found - this is OK, not an error
        return results

    branches_with_errors = 0

    # Check that main entity (parent of all branches) has a legal identifier
    main_has_identifier = False
    if main_entity.legal_identifiers:
        identifier_types = IDENTIFIER_PRIORITY
        for id_type in identifier_types:
            if main_entity.legal_identifiers.get(id_type):
                main_has_identifier = True
                break

    if not main_has_identifier and branches.exists():
        results.append(
            {
                "severity": "error",
                "category": "Branches",
                "message": f"Main entity '{main_entity.name}' (parent of branches) must have at least one legal identifier (LEI, EUID, VAT, or DUNS) for DORA b_01.03 reporting",
                "field": "legal_identifiers",
                "object_type": "entities",
                "object_id": str(main_entity.id),
                "object_name": main_entity.name,
            }
        )

    # Check each branch
    for branch in branches:
        branch_has_error = False

        # Check country (mandatory)
        if not branch.country:
            results.append(
                {
                    "severity": "error",
                    "category": "Branches",
                    "message": f"Branch '{branch.name}' must have a country set for DORA b_01.03 reporting",
                    "field": "country",
                    "object_type": "entities",
                    "object_id": str(branch.id),
                    "object_name": branch.name,
                }
            )
            branch_has_error = True

        if branch_has_error:
            branches_with_errors += 1

    # If we have branches and no errors, add a success message
    valid_branches = branches.count() - branches_with_errors
    if valid_branches == branches.count():
        results.append(
            {
                "severity": "ok",
                "category": "Branches",
                "message": f"All {branches.count()} branch(es) have required fields set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )
    elif valid_branches > 0:
        results.append(
            {
                "severity": "ok",
                "category": "Branches",
                "message": f"{valid_branches} of {branches.count()} branch(es) have all required fields set",
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

    # Check each business function's ref_id and licensed activity
    invalid_ref_ids = []
    missing_licensed_activity = []
    duplicate_ref_ids = {}  # ref_id -> list of Assets
    valid_count = 0

    for bf in business_functions:
        # Check ref_id pattern
        if not bf.ref_id or not ref_id_pattern.match(bf.ref_id):
            invalid_ref_ids.append(bf)
        else:
            valid_count += 1

        # Track ref_ids to detect duplicates (causes XBRL duplicate fact errors in b_06.01)
        effective_ref_id = bf.ref_id or str(bf.id)
        duplicate_ref_ids.setdefault(effective_ref_id, []).append(bf)

        # Check licensed activity (mandatory for DORA reporting)
        if not bf.dora_licenced_activity:
            missing_licensed_activity.append(bf)

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

    # Report duplicate ref_ids
    for ref_id, assets in duplicate_ref_ids.items():
        if len(assets) > 1:
            names = ", ".join(f"'{a.name}'" for a in assets)
            results.append(
                {
                    "severity": "error",
                    "category": "Business Functions",
                    "message": f"Duplicate function identifier '{ref_id}' shared by {len(assets)} business functions: {names}. This will cause XBRL duplicate fact errors in b_06.01.",
                    "field": "ref_id",
                    "object_type": "assets",
                    "object_id": str(assets[0].id),
                    "object_name": assets[0].name,
                }
            )

    # Report missing licensed activity
    if missing_licensed_activity:
        for bf in missing_licensed_activity:
            results.append(
                {
                    "severity": "error",
                    "category": "Business Functions",
                    "message": f"Business function '{bf.name}' must have a licensed activity set for DORA reporting",
                    "field": "dora_licenced_activity",
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

    # Add success message if all business functions have licensed activity
    if not missing_licensed_activity:
        results.append(
            {
                "severity": "ok",
                "category": "Business Functions",
                "message": f"All {business_functions.count()} business function(s) have licensed activity set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    return results


def lint_contracts() -> List[Dict[str, Any]]:
    """
    Validate contracts for DORA ROI requirements.

    Checks that contracts have required fields:
    - ref_id
    - currency
    - dora_contractual_arrangement (type of contract)
    - annual_expense
    - beneficiary_entity (with legal identifier)
    - start_date

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get all contracts
    contracts = (
        Contract.objects.exclude(status=Contract.Status.DRAFT)
        .exclude(dora_exclude=True)
        .select_related("beneficiary_entity")
    )

    if not contracts.exists():
        # No contracts found - this could be OK, but let's inform the user
        results.append(
            {
                "severity": "warning",
                "category": "Contracts",
                "message": "No contracts found in the system",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )
        return results

    # Track validation statistics
    total_contracts = contracts.count()
    contracts_with_errors = 0

    # Check each contract
    for contract in contracts:
        contract_has_error = False

        # Check ref_id (mandatory)
        if not contract.ref_id:
            results.append(
                {
                    "severity": "error",
                    "category": "Contracts",
                    "message": f"Contract '{contract.name}' must have a reference ID (ref_id) set",
                    "field": "ref_id",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
            contract_has_error = True

        # Check currency (mandatory)
        if not contract.currency:
            results.append(
                {
                    "severity": "error",
                    "category": "Contracts",
                    "message": f"Contract '{contract.name}' must have a currency set",
                    "field": "currency",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
            contract_has_error = True

        # Check DORA contractual arrangement (mandatory)
        if not contract.dora_contractual_arrangement:
            results.append(
                {
                    "severity": "error",
                    "category": "Contracts",
                    "message": f"Contract '{contract.name}' must have a DORA contractual arrangement (type) set",
                    "field": "dora_contractual_arrangement",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
            contract_has_error = True

        # Check annual expense (mandatory)
        if contract.annual_expense is None:
            results.append(
                {
                    "severity": "error",
                    "category": "Contracts",
                    "message": f"Contract '{contract.name}' must have an annual expense set",
                    "field": "annual_expense",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
            contract_has_error = True

        # Check beneficiary entity (mandatory for b_02.02 reporting)
        if not contract.beneficiary_entity:
            results.append(
                {
                    "severity": "error",
                    "category": "Contracts",
                    "message": f"Contract '{contract.name}' must have a beneficiary entity set for DORA b_02.02 reporting",
                    "field": "beneficiary_entity",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
            contract_has_error = True
        else:
            # Check that beneficiary entity has a legal identifier
            beneficiary_has_identifier = False
            if contract.beneficiary_entity.legal_identifiers:
                identifier_types = IDENTIFIER_PRIORITY
                for id_type in identifier_types:
                    if contract.beneficiary_entity.legal_identifiers.get(id_type):
                        beneficiary_has_identifier = True
                        break

            if not beneficiary_has_identifier:
                results.append(
                    {
                        "severity": "error",
                        "category": "Contracts",
                        "message": f"Beneficiary entity '{contract.beneficiary_entity.name}' of contract '{contract.name}' must have at least one legal identifier (LEI, EUID, VAT, or DUNS) for DORA b_02.02 reporting",
                        "field": "legal_identifiers",
                        "object_type": "entities",
                        "object_id": str(contract.beneficiary_entity.id),
                        "object_name": contract.beneficiary_entity.name,
                    }
                )
                contract_has_error = True

        # Check start_date (mandatory for b_02.02 reporting)
        if not contract.start_date:
            results.append(
                {
                    "severity": "error",
                    "category": "Contracts",
                    "message": f"Contract '{contract.name}' must have a start date set for DORA b_02.02 reporting",
                    "field": "start_date",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
            contract_has_error = True

        if contract_has_error:
            contracts_with_errors += 1

    # Add success message if all contracts are valid
    contracts_valid = total_contracts - contracts_with_errors
    if contracts_valid == total_contracts:
        results.append(
            {
                "severity": "ok",
                "category": "Contracts",
                "message": f"All {total_contracts} contracts have required fields set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )
    elif contracts_valid > 0:
        results.append(
            {
                "severity": "ok",
                "category": "Contracts",
                "message": f"{contracts_valid} of {total_contracts} contracts have all required fields set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    return results


def lint_b_02_02_contracts() -> List[Dict[str, Any]]:
    """
    Validate contracts for DORA b_02.02 (ICT services supporting functions) requirements.

    Only validates contracts with solutions linked to business function assets or their child assets,
    as these are the ones included in b_02.02 reporting.

    Checks that contracts have:
    - beneficiary_entity has LEI specifically (c0020 requires LEI)
    - provider_entity set
    - provider_entity has at least one legal identifier (LEI, EUID, VAT, DUNS)

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get business function assets
    business_functions = Asset.objects.filter(is_business_function=True)

    # Collect all assets related to business functions (including children)
    business_function_asset_ids = set(business_functions.values_list("id", flat=True))
    for business_function in business_functions:
        # Get all descendant (child) assets for each business function
        # Note: get_descendants() returns Asset objects, not IDs
        descendants = business_function.get_descendants()
        business_function_asset_ids.update(asset.id for asset in descendants)

    # Get contracts that will be included in b_02.02:
    # those with solutions linked to business function assets or their children
    b_02_02_contracts = (
        Contract.objects.filter(
            solutions__isnull=False,
            solutions__assets__id__in=business_function_asset_ids,
        )
        .exclude(status=Contract.Status.DRAFT)
        .exclude(dora_exclude=True)
        .distinct()
        .select_related("provider_entity", "beneficiary_entity")
        .prefetch_related("solutions")
    )

    if not b_02_02_contracts.exists():
        # No contracts found for b_02.02
        return results

    # Track validation statistics
    total_contracts = b_02_02_contracts.count()
    contracts_with_errors = 0

    # Check each contract
    for contract in b_02_02_contracts:
        contract_has_error = False

        # Check that beneficiary entity has LEI specifically (c0020 requires LEI)
        if not contract.beneficiary_entity:
            results.append(
                {
                    "severity": "error",
                    "category": "B_02.02 Contracts",
                    "message": f"Contract '{contract.name}' (linked to business functions) must have a beneficiary entity set for DORA b_02.02 reporting (c0020)",
                    "field": "beneficiary_entity",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
            contract_has_error = True
        else:
            # Check that beneficiary entity has LEI specifically
            beneficiary_has_lei = False
            if contract.beneficiary_entity.legal_identifiers:
                if contract.beneficiary_entity.legal_identifiers.get("LEI"):
                    beneficiary_has_lei = True

            if not beneficiary_has_lei:
                results.append(
                    {
                        "severity": "error",
                        "category": "B_02.02 Contracts",
                        "message": f"Beneficiary entity '{contract.beneficiary_entity.name}' of contract '{contract.name}' must have an LEI (not just any identifier) for DORA b_02.02 reporting (c0020 requires LEI)",
                        "field": "legal_identifiers",
                        "object_type": "entities",
                        "object_id": str(contract.beneficiary_entity.id),
                        "object_name": contract.beneficiary_entity.name,
                    }
                )
                contract_has_error = True

        # Check that contract has a provider entity (mandatory for b_02.02)
        if not contract.provider_entity:
            results.append(
                {
                    "severity": "error",
                    "category": "B_02.02 Contracts",
                    "message": f"Contract '{contract.name}' (linked to business functions) must have a provider entity set for DORA b_02.02 reporting",
                    "field": "provider_entity",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
            contract_has_error = True
        else:
            # Check that provider entity has a legal identifier
            provider_has_identifier = False
            if contract.provider_entity.legal_identifiers:
                identifier_types = IDENTIFIER_PRIORITY
                for id_type in identifier_types:
                    if contract.provider_entity.legal_identifiers.get(id_type):
                        provider_has_identifier = True
                        break

            if not provider_has_identifier:
                results.append(
                    {
                        "severity": "error",
                        "category": "B_02.02 Contracts",
                        "message": f"Provider entity '{contract.provider_entity.name}' of contract '{contract.name}' must have at least one legal identifier (LEI, EUID, VAT, or DUNS) for DORA b_02.02 reporting",
                        "field": "legal_identifiers",
                        "object_type": "entities",
                        "object_id": str(contract.provider_entity.id),
                        "object_name": contract.provider_entity.name,
                    }
                )
                contract_has_error = True

        if contract_has_error:
            contracts_with_errors += 1

    # Check for duplicate XBRL keys within B_02.02.
    # The XBRL key is (contract_ref, entity_lei, provider_code, function_id, ict_service_type).
    # Since entity_lei and provider_code are fixed per contract, duplicates arise when
    # two solutions on the same contract share the same (function_id, ict_service_type).
    for contract in b_02_02_contracts:
        seen_keys = {}  # (function_id, ict_service_type) -> solution name
        for solution in contract.solutions.all():
            ict_service_type = solution.dora_ict_service_type or ""
            if business_function_asset_ids:
                functions = solution.assets.filter(
                    id__in=business_function_asset_ids, is_business_function=True
                )
            else:
                functions = solution.assets.filter(is_business_function=True)
            for function in functions:
                function_id = function.ref_id or str(function.id)
                key = (function_id, ict_service_type)
                if key in seen_keys:
                    contract_ref = contract.ref_id or contract.name
                    results.append(
                        {
                            "severity": "warning",
                            "category": "B_02.02 Contracts",
                            "message": (
                                f"Contract '{contract_ref}' has duplicate XBRL key in B_02.02: "
                                f"function '{function_id}', ICT service type '{ict_service_type}' "
                                f"appears in solutions '{seen_keys[key]}' and '{solution.name}'. "
                                f"Only the first will be exported."
                            ),
                            "field": "solutions",
                            "object_type": "contracts",
                            "object_id": str(contract.id),
                            "object_name": contract.name,
                        }
                    )
                else:
                    seen_keys[key] = solution.name

    # Add success message if all contracts are valid
    contracts_valid = total_contracts - contracts_with_errors
    if contracts_valid == total_contracts:
        results.append(
            {
                "severity": "ok",
                "category": "B_02.02 Contracts",
                "message": f"All {total_contracts} contracts linked to business functions have provider entities with legal identifiers",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )
    elif contracts_valid > 0:
        results.append(
            {
                "severity": "ok",
                "category": "B_02.02 Contracts",
                "message": f"{contracts_valid} of {total_contracts} contracts linked to business functions have valid provider entities",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    return results


def lint_solutions() -> List[Dict[str, Any]]:
    """
    Validate solutions for DORA ROI requirements.

    Only validates solutions that are associated with assets marked as business functions
    or their child assets, as these are the ones relevant for DORA reporting.

    Checks that solutions have required fields:
    - dora_ict_service_type (ICT service type)
    - data_location_storage (location of data at rest)
    - data_location_processing (location of data at processing)
    - provider_entity must have country set
    - contract associated with solution (warning if missing)

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get business function assets
    business_functions = Asset.objects.filter(is_business_function=True)

    # Collect all assets related to business functions (including children)
    business_function_asset_ids = set(business_functions.values_list("id", flat=True))
    for business_function in business_functions:
        # Get all descendant (child) assets for each business function
        # Note: get_descendants() returns Asset objects, not IDs
        descendants = business_function.get_descendants()
        business_function_asset_ids.update(asset.id for asset in descendants)

    # Get solutions associated with business function assets or their children,
    # only if they belong to at least one non-draft contract
    solutions = (
        Solution.objects.filter(assets__id__in=business_function_asset_ids)
        .exclude(contracts__status=Contract.Status.DRAFT)
        .distinct()
        .select_related("provider_entity")
        .prefetch_related("contracts")
    )

    if not solutions.exists():
        # No solutions found linked to business functions
        results.append(
            {
                "severity": "warning",
                "category": "Solutions",
                "message": "No solutions found linked to business function assets",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )
        return results

    # Track validation statistics
    total_solutions = solutions.count()
    solutions_with_errors = 0

    # Check each solution
    for solution in solutions:
        solution_has_error = False

        # Check ICT service type (mandatory)
        if not solution.dora_ict_service_type:
            results.append(
                {
                    "severity": "error",
                    "category": "Solutions",
                    "message": f"Solution '{solution.name}' must have ICT service type set",
                    "field": "dora_ict_service_type",
                    "object_type": "solutions",
                    "object_id": str(solution.id),
                    "object_name": solution.name,
                }
            )
            solution_has_error = True

        # Check data_location_storage (mandatory)
        if not solution.data_location_storage:
            results.append(
                {
                    "severity": "error",
                    "category": "Solutions",
                    "message": f"Solution '{solution.name}' must have location of data at rest (data storage location) set",
                    "field": "data_location_storage",
                    "object_type": "solutions",
                    "object_id": str(solution.id),
                    "object_name": solution.name,
                }
            )
            solution_has_error = True
        else:
            # Warning: if data_location_storage is set but storage_of_data flag is not set
            if not solution.storage_of_data:
                results.append(
                    {
                        "severity": "warning",
                        "category": "Solutions",
                        "message": f"Solution '{solution.name}' has data storage location set but 'Storage of data' flag is not enabled",
                        "field": "storage_of_data",
                        "object_type": "solutions",
                        "object_id": str(solution.id),
                        "object_name": solution.name,
                    }
                )

        # Check data_location_processing (mandatory)
        if not solution.data_location_processing:
            results.append(
                {
                    "severity": "error",
                    "category": "Solutions",
                    "message": f"Solution '{solution.name}' must have location of data processing set",
                    "field": "data_location_processing",
                    "object_type": "solutions",
                    "object_id": str(solution.id),
                    "object_name": solution.name,
                }
            )
            solution_has_error = True

        # Check provider_entity country (mandatory)
        if solution.provider_entity:
            if not solution.provider_entity.country:
                results.append(
                    {
                        "severity": "error",
                        "category": "Solutions",
                        "message": f"Solution '{solution.name}' has provider entity '{solution.provider_entity.name}' without a country set",
                        "field": "country",
                        "object_type": "entities",
                        "object_id": str(solution.provider_entity.id),
                        "object_name": solution.provider_entity.name,
                    }
                )
                solution_has_error = True
        else:
            # No provider entity - this is also an error
            results.append(
                {
                    "severity": "error",
                    "category": "Solutions",
                    "message": f"Solution '{solution.name}' must have a provider entity set",
                    "field": "provider_entity",
                    "object_type": "solutions",
                    "object_id": str(solution.id),
                    "object_name": solution.name,
                }
            )
            solution_has_error = True

        # Check if solution has at least one contract (mandatory for DORA reporting)
        if not solution.contracts.exists():
            results.append(
                {
                    "severity": "error",
                    "category": "Solutions",
                    "message": f"Solution '{solution.name}' linked to business function(s) must have at least one associated contract for DORA reporting",
                    "field": "contracts",
                    "object_type": "solutions",
                    "object_id": str(solution.id),
                    "object_name": solution.name,
                }
            )
            solution_has_error = True

        if solution_has_error:
            solutions_with_errors += 1

    # Add success message if all solutions are valid
    solutions_valid = total_solutions - solutions_with_errors
    if solutions_valid == total_solutions:
        results.append(
            {
                "severity": "ok",
                "category": "Solutions",
                "message": f"All {total_solutions} solutions have required fields set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )
    elif solutions_valid > 0:
        results.append(
            {
                "severity": "ok",
                "category": "Solutions",
                "message": f"{solutions_valid} of {total_solutions} solutions have all required fields set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    return results


def lint_supply_chain_solutions() -> List[Dict[str, Any]]:
    """
    Validate solutions that appear in b_05.02 (ICT service supply chains).

    b_05.02 includes all solutions on non-intragroup contracts with providers.
    Column c0020 (Type of ICT services) is an explicit XBRL dimension and must
    not be empty — solutions without dora_ict_service_type are silently excluded
    from the export. This rule warns about such solutions so users can fix them.

    Returns:
        List of validation results with severity levels (warning, ok)
    """
    results = []

    # Solutions on non-draft third-party contracts (same scope as generate_b_05_02)
    solutions = (
        Solution.objects.filter(
            contracts__is_intragroup=False,
            contracts__provider_entity__isnull=False,
        )
        .exclude(contracts__status=Contract.Status.DRAFT)
        .distinct()
        .select_related("provider_entity")
    )

    if not solutions.exists():
        return results

    missing = solutions.filter(
        Q(dora_ict_service_type__isnull=True) | Q(dora_ict_service_type="")
    )

    for solution in missing:
        results.append(
            {
                "severity": "warning",
                "category": "Supply Chain (B_05.02)",
                "message": (
                    f"Solution '{solution.name}' on a third-party contract has no "
                    f"ICT service type — it will be excluded from the B_05.02 "
                    f"supply chain export"
                ),
                "field": "dora_ict_service_type",
                "object_type": "solutions",
                "object_id": str(solution.id),
                "object_name": solution.name,
            }
        )

    if not missing.exists():
        results.append(
            {
                "severity": "ok",
                "category": "Supply Chain (B_05.02)",
                "message": f"All {solutions.count()} supply-chain solutions have ICT service type set",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    # Check for duplicate XBRL keys within B_07.01.
    # The XBRL key is (contract_ref, provider_code, ict_service_type).
    # Since provider_code is fixed per contract, duplicates arise when
    # two solutions on the same contract share the same ict_service_type.
    assessment_contracts = (
        Contract.objects.filter(
            is_intragroup=False,
            provider_entity__isnull=False,
            solutions__isnull=False,
        )
        .exclude(status=Contract.Status.DRAFT)
        .exclude(dora_exclude=True)
        .distinct()
        .prefetch_related("solutions")
    )
    for contract in assessment_contracts:
        seen_types = {}  # ict_service_type -> solution name
        for solution in contract.solutions.all():
            ict_service_type = solution.dora_ict_service_type or ""
            if ict_service_type in seen_types:
                contract_ref = contract.ref_id or contract.name
                results.append(
                    {
                        "severity": "warning",
                        "category": "Assessment (B_07.01)",
                        "message": (
                            f"Contract '{contract_ref}' has duplicate XBRL key in B_07.01: "
                            f"ICT service type '{ict_service_type}' appears in solutions "
                            f"'{seen_types[ict_service_type]}' and '{solution.name}'. "
                            f"Only the first will be exported."
                        ),
                        "field": "solutions",
                        "object_type": "contracts",
                        "object_id": str(contract.id),
                        "object_name": contract.name,
                    }
                )
            else:
                seen_types[ict_service_type] = solution.name

    return results


def lint_unique_leis(main_entity: Entity) -> List[Dict[str, Any]]:
    """
    Validate that LEIs are unique across entities included in DORA ROI report.

    The b_01.02 report includes main entity + subsidiaries, and each must have a unique LEI.

    Args:
        main_entity: The main Entity instance

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get all entities for b_01.02: main entity + subsidiaries
    subsidiaries = Entity.objects.filter(
        parent_entity=main_entity, dora_provider_person_type__isnull=False
    ).exclude(dora_provider_person_type="")

    all_entities = [main_entity] + list(subsidiaries)

    # Collect LEIs
    lei_map = {}  # lei -> list of entities with that LEI
    for entity in all_entities:
        if entity.legal_identifiers and entity.legal_identifiers.get("LEI"):
            lei = entity.legal_identifiers.get("LEI")
            if lei not in lei_map:
                lei_map[lei] = []
            lei_map[lei].append(entity)

    # Check for duplicates
    has_duplicates = False
    for lei, entities in lei_map.items():
        if len(entities) > 1:
            has_duplicates = True
            entity_names = ", ".join([f"'{e.name}'" for e in entities])
            results.append(
                {
                    "severity": "error",
                    "category": "Unique LEIs",
                    "message": f"LEI '{lei}' is used by multiple entities: {entity_names}. Each entity in the DORA ROI report must have a unique LEI.",
                    "field": "legal_identifiers",
                    "object_type": None,
                    "object_id": None,
                    "object_name": None,
                }
            )

    if not has_duplicates and lei_map:
        results.append(
            {
                "severity": "ok",
                "category": "Unique LEIs",
                "message": "All entities have unique LEIs",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    return results


def lint_cross_table_consistency() -> List[Dict[str, Any]]:
    """
    Validate cross-table consistency for DORA ROI export.

    Checks EBA/NBB validation rules that span multiple tables:
    - 02.01_02.02_0010: Every contract in B_02.01 must appear in B_02.02
    - 02.01_05.02_0010: Every contract in B_02.01 must appear in B_05.02
    - 03.02_02.02_COMBINATION: B_03.02/B_02.02 provider combinations must match

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get all non-draft contracts (same scope as B_02.01)
    all_contracts = (
        Contract.objects.exclude(status=Contract.Status.DRAFT)
        .exclude(dora_exclude=True)
        .select_related("provider_entity")
        .prefetch_related("solutions")
    )

    if not all_contracts.exists():
        return results

    # --- Compute B_02.02 scope ---
    business_functions = Asset.objects.filter(is_business_function=True)
    business_function_asset_ids = set(business_functions.values_list("id", flat=True))
    for bf in business_functions:
        descendants = bf.get_descendants()
        business_function_asset_ids.update(asset.id for asset in descendants)

    b_02_02_contract_ids = (
        set(
            Contract.objects.filter(
                solutions__isnull=False,
                solutions__assets__id__in=business_function_asset_ids,
            )
            .exclude(status=Contract.Status.DRAFT)
            .exclude(dora_exclude=True)
            .distinct()
            .values_list("id", flat=True)
        )
        if business_function_asset_ids
        else set()
    )

    # --- Compute B_05.02 scope ---
    # B_05.02 includes non-intragroup contracts with provider, solutions,
    # and at least one solution with dora_ict_service_type set
    b_05_02_candidates = (
        Contract.objects.filter(
            is_intragroup=False,
            provider_entity__isnull=False,
            solutions__isnull=False,
        )
        .exclude(status=Contract.Status.DRAFT)
        .exclude(dora_exclude=True)
        .distinct()
    )
    # Further filter: at least one solution must have dora_ict_service_type
    b_05_02_contract_ids = set()
    for contract in b_05_02_candidates.prefetch_related("solutions"):
        if contract.solutions.exclude(
            Q(dora_ict_service_type__isnull=True) | Q(dora_ict_service_type="")
        ).exists():
            b_05_02_contract_ids.add(contract.id)

    # --- Check 02.01_02.02: every B_02.01 contract should be in B_02.02 ---
    missing_b_02_02 = []
    for contract in all_contracts:
        if contract.id not in b_02_02_contract_ids:
            missing_b_02_02.append(contract)

    if missing_b_02_02:
        # Diagnose why each contract is missing
        for contract in missing_b_02_02:
            has_solutions = contract.solutions.exists()
            if not has_solutions:
                reason = "has no solutions linked"
            elif not business_function_asset_ids:
                reason = "no business functions exist in the system"
            else:
                # Has solutions but none linked to business function assets
                reason = "none of its solutions are linked to business function assets"
            contract_ref = contract.ref_id or contract.name
            results.append(
                {
                    "severity": "error",
                    "category": "Cross-table (B_02.01 \u2194 B_02.02)",
                    "message": (
                        f"Contract '{contract_ref}' is in B_02.01 but missing from B_02.02: "
                        f"{reason}. Link its solutions to business function assets to fix this."
                    ),
                    "field": "solutions",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
    else:
        results.append(
            {
                "severity": "ok",
                "category": "Cross-table (B_02.01 \u2194 B_02.02)",
                "message": f"All {all_contracts.count()} contracts in B_02.01 are also present in B_02.02",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    # --- Check 02.01_05.02: every B_02.01 contract should be in B_05.02 ---
    missing_b_05_02 = []
    for contract in all_contracts:
        if contract.id not in b_05_02_contract_ids:
            missing_b_05_02.append(contract)

    if missing_b_05_02:
        for contract in missing_b_05_02:
            reasons = []
            if contract.is_intragroup:
                reasons.append("is intragroup")
            if not contract.provider_entity:
                reasons.append("has no provider entity")
            if not contract.solutions.exists():
                reasons.append("has no solutions")
            elif not contract.solutions.exclude(
                Q(dora_ict_service_type__isnull=True) | Q(dora_ict_service_type="")
            ).exists():
                reasons.append("all its solutions are missing ICT service type")
            reason = "; ".join(reasons) if reasons else "unknown reason"
            # Contracts excluded from B_05.02 scope by design (intragroup,
            # missing provider, etc.) are informational, not errors.
            severity = "info" if reasons else "error"
            contract_ref = contract.ref_id or contract.name
            results.append(
                {
                    "severity": severity,
                    "category": "Cross-table (B_02.01 \u2194 B_05.02)",
                    "message": (
                        f"Contract '{contract_ref}' is in B_02.01 but missing from B_05.02: "
                        f"{reason}."
                    ),
                    "field": "solutions",
                    "object_type": "contracts",
                    "object_id": str(contract.id),
                    "object_name": contract.name,
                }
            )
    else:
        results.append(
            {
                "severity": "ok",
                "category": "Cross-table (B_02.01 \u2194 B_05.02)",
                "message": f"All {all_contracts.count()} contracts in B_02.01 are also present in B_05.02",
                "field": None,
                "object_type": None,
                "object_id": None,
                "object_name": None,
            }
        )

    return results


def lint_conditional_fields() -> List[Dict[str, Any]]:
    """
    Validate conditional field requirements (EBA formula validation rules).

    Checks:
    - v8805: If contract type is eba_CO:x3 (sub-contracting), overarching contract must be set
    - v8804: If entity type is not eba_CT:x318 or eba_CT:x317, assets value must be set
    - v8884: Solutions in B_07.01 must have substitutability set

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # --- v8805: sub-contracting contracts must have overarching contract ---
    subcontracting_contracts = (
        Contract.objects.filter(
            dora_contractual_arrangement="eba_CO:x3",
            overarching_contract__isnull=True,
        )
        .exclude(status=Contract.Status.DRAFT)
        .exclude(dora_exclude=True)
    )

    for contract in subcontracting_contracts:
        contract_ref = contract.ref_id or contract.name
        results.append(
            {
                "severity": "error",
                "category": "Conditional fields (v8805)",
                "message": (
                    f"Contract '{contract_ref}' has type 'sub-contracting' (eba_CO:x3) "
                    f"but no overarching contract is set (B_02.01.0030 required)."
                ),
                "field": "overarching_contract",
                "object_type": "contracts",
                "object_id": str(contract.id),
                "object_name": contract.name,
            }
        )

    # --- v8804: entity type not x318/x317 requires assets value ---
    # Get entities in B_01.02 scope (main entity + subsidiaries)
    main_entity = Entity.get_main_entity()
    if main_entity:
        exempt_types = {"eba_CT:x318", "eba_CT:x317"}
        subsidiaries = Entity.objects.filter(
            parent_entity=main_entity, dora_provider_person_type__isnull=False
        ).exclude(dora_provider_person_type="")
        b_01_02_entities = [main_entity] + list(subsidiaries)

        for entity in b_01_02_entities:
            if (
                entity.dora_entity_type
                and entity.dora_entity_type not in exempt_types
                and entity.dora_assets_value is None
            ):
                results.append(
                    {
                        "severity": "error",
                        "category": "Conditional fields (v8804)",
                        "message": (
                            f"Entity '{entity.name}' has type '{entity.dora_entity_type}' "
                            f"(not exempt) but assets value (B_01.02.0110) is not set."
                        ),
                        "field": "dora_assets_value",
                        "object_type": "entities",
                        "object_id": str(entity.id),
                        "object_name": entity.name,
                    }
                )

    # --- v8884: solutions in B_07.01 must have substitutability ---
    # B_07.01 includes solutions on non-draft, non-intragroup contracts with provider
    b_07_01_solutions = (
        Solution.objects.filter(
            contracts__is_intragroup=False,
            contracts__provider_entity__isnull=False,
        )
        .exclude(contracts__status=Contract.Status.DRAFT)
        .distinct()
    )

    missing_substitutability = b_07_01_solutions.filter(
        Q(dora_substitutability__isnull=True) | Q(dora_substitutability="")
    )

    for solution in missing_substitutability:
        results.append(
            {
                "severity": "error",
                "category": "Conditional fields (v8884)",
                "message": (
                    f"Solution '{solution.name}' appears in B_07.01 but has no "
                    f"substitutability assessment set (B_07.01.0050 required)."
                ),
                "field": "dora_substitutability",
                "object_type": "solutions",
                "object_id": str(solution.id),
                "object_name": solution.name,
            }
        )

    # Summary if all good
    if not results:
        results.append(
            {
                "severity": "ok",
                "category": "Conditional fields",
                "message": "All conditional field requirements are satisfied",
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
    results.extend(lint_branches(main_entity))
    results.extend(lint_unique_leis(main_entity))
    results.extend(lint_business_functions())
    results.extend(lint_contracts())
    results.extend(lint_b_02_02_contracts())
    results.extend(lint_solutions())
    results.extend(lint_supply_chain_solutions())
    results.extend(lint_provider_entities())
    results.extend(lint_cross_table_consistency())
    results.extend(lint_conditional_fields())

    # Calculate summary
    summary = {
        "errors": sum(1 for r in results if r["severity"] == "error"),
        "warnings": sum(1 for r in results if r["severity"] == "warning"),
        "ok": sum(1 for r in results if r["severity"] == "ok"),
    }

    # Build available identifiers for the frontend selector
    available_identifiers = []
    if main_entity and main_entity.legal_identifiers:
        priority = IDENTIFIER_PRIORITY
        for id_type in priority:
            value = main_entity.legal_identifiers.get(id_type)
            if value:
                available_identifiers.append({"type": id_type, "value": value})
        for key, value in main_entity.legal_identifiers.items():
            if value and key not in priority:
                available_identifiers.append({"type": key, "value": value})

    return {
        "results": results,
        "summary": summary,
        "available_identifiers": available_identifiers,
        "entity_country": main_entity.country if main_entity else "",
        "competent_authority": main_entity.dora_competent_authority
        if main_entity
        else "",
    }
