"""
DORA ROI Linting Module

This module provides validation functions for DORA Register of Information (ROI) exports.
It checks for mandatory and recommended fields before generating the actual report.
"""

from typing import List, Dict, Any
from tprm.models import Entity, Contract, Solution
from core.models import Asset
from django.db.models import Q
import re


def lint_provider_entities() -> List[Dict[str, Any]]:
    """
    Validate provider entities used in DORA ROI reports.

    Checks that third-party providers have:
    - At least one legal identifier (LEI, EUID, VAT, DUNS)
    - Country set
    - Parent entity with legal identifier (if parent exists)

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get all provider entities from third-party contracts
    provider_entities = Entity.objects.filter(
        contracts__is_intragroup=False, contracts__isnull=False
    ).distinct()

    if not provider_entities.exists():
        return results

    providers_with_errors = 0

    for provider in provider_entities:
        provider_has_error = False

        # Check legal identifiers (mandatory)
        has_legal_identifier = False
        if provider.legal_identifiers:
            identifier_types = ["LEI", "EUID", "VAT", "DUNS"]
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

        # Check parent entity has legal identifier (if parent exists)
        if provider.parent_entity:
            parent_has_identifier = False
            if provider.parent_entity.legal_identifiers:
                identifier_types = ["LEI", "EUID", "VAT", "DUNS"]
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


def lint_branches() -> List[Dict[str, Any]]:
    """
    Validate branches for DORA ROI requirements.

    Branches are entities without dora_provider_person_type set.
    Each branch must have a parent entity with a legal identifier (for b_01.03 report).

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get all branches (entities with no dora_provider_person_type)
    branches = Entity.objects.filter(
        Q(dora_provider_person_type__isnull=True) | Q(dora_provider_person_type="")
    ).exclude(builtin=True)

    if not branches.exists():
        # No branches found - this is OK, not an error
        return results

    branches_with_errors = 0

    # Check each branch
    for branch in branches:
        branch_has_error = False

        # Check that branch has a parent entity
        if not branch.parent_entity:
            results.append(
                {
                    "severity": "error",
                    "category": "Branches",
                    "message": f"Branch '{branch.name}' must have a parent entity set for DORA b_01.03 reporting",
                    "field": "parent_entity",
                    "object_type": "entities",
                    "object_id": str(branch.id),
                    "object_name": branch.name,
                }
            )
            branch_has_error = True
        else:
            # Check that parent entity has a legal identifier
            parent_has_identifier = False
            if branch.parent_entity.legal_identifiers:
                identifier_types = ["LEI", "EUID", "VAT", "DUNS"]
                for id_type in identifier_types:
                    if branch.parent_entity.legal_identifiers.get(id_type):
                        parent_has_identifier = True
                        break

            if not parent_has_identifier:
                results.append(
                    {
                        "severity": "error",
                        "category": "Branches",
                        "message": f"Parent entity '{branch.parent_entity.name}' of branch '{branch.name}' must have at least one legal identifier (LEI, EUID, VAT, or DUNS) for DORA b_01.03 reporting",
                        "field": "legal_identifiers",
                        "object_type": "entities",
                        "object_id": str(branch.parent_entity.id),
                        "object_name": branch.parent_entity.name,
                    }
                )
                branch_has_error = True

        # Check branch itself has legal identifier
        branch_has_identifier = False
        if branch.legal_identifiers:
            identifier_types = ["LEI", "EUID", "VAT", "DUNS"]
            for id_type in identifier_types:
                if branch.legal_identifiers.get(id_type):
                    branch_has_identifier = True
                    break

        if not branch_has_identifier:
            results.append(
                {
                    "severity": "error",
                    "category": "Branches",
                    "message": f"Branch '{branch.name}' must have at least one legal identifier (LEI, EUID, VAT, or DUNS) for DORA b_01.03 reporting",
                    "field": "legal_identifiers",
                    "object_type": "entities",
                    "object_id": str(branch.id),
                    "object_name": branch.name,
                }
            )
            branch_has_error = True

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
    valid_count = 0

    for bf in business_functions:
        # Check ref_id pattern
        if not bf.ref_id or not ref_id_pattern.match(bf.ref_id):
            invalid_ref_ids.append(bf)
        else:
            valid_count += 1

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

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get all contracts
    contracts = Contract.objects.all()

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


def lint_solutions() -> List[Dict[str, Any]]:
    """
    Validate solutions for DORA ROI requirements.

    Only validates solutions that are associated with assets marked as business functions,
    as these are the ones relevant for DORA reporting.

    Checks that solutions have required fields:
    - dora_ict_service_type (ICT service type)
    - data_location_storage (location of data at rest)
    - data_location_processing (location of data at processing)
    - provider_entity must have country set

    Returns:
        List of validation results with severity levels (error, warning, ok)
    """
    results = []

    # Get only solutions associated with business function assets
    solutions = (
        Solution.objects.filter(assets__is_business_function=True)
        .distinct()
        .select_related("provider_entity")
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
    results.extend(lint_branches())
    results.extend(lint_unique_leis(main_entity))
    results.extend(lint_business_functions())
    results.extend(lint_contracts())
    results.extend(lint_solutions())
    results.extend(lint_provider_entities())

    # Calculate summary
    summary = {
        "errors": sum(1 for r in results if r["severity"] == "error"),
        "warnings": sum(1 for r in results if r["severity"] == "warning"),
        "ok": sum(1 for r in results if r["severity"] == "ok"),
    }

    return {"results": results, "summary": summary}
