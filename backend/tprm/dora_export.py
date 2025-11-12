"""
DORA (Digital Operational Resilience Act) ROI (Register of Information) export utilities.

This module contains functions to generate various CSV reports required by DORA regulations.
Each function generates a specific report and writes it to a ZIP file.
"""

import csv
import io
from typing import Dict, List, Optional, Any

from django.db.models import QuerySet
from tprm.models import Entity, Contract, Solution
from core.models import Asset


# Helper Functions


def get_entity_identifier(
    entity: Entity, priority: List[str] = None
) -> tuple[str, str]:
    """
    Extract identification code and type from entity's legal_identifiers.

    Args:
        entity: Entity object with legal_identifiers
        priority: List of identifier types in priority order (default: LEI, EUID, VAT, DUNS)

    Returns:
        Tuple of (identifier_code, identifier_type)
    """
    if priority is None:
        priority = ["LEI", "EUID", "VAT", "DUNS"]

    if not entity or not entity.legal_identifiers:
        return "", ""

    # Try priority identifiers first
    for id_type in priority:
        if id_type in entity.legal_identifiers and entity.legal_identifiers[id_type]:
            return entity.legal_identifiers[id_type], id_type

    # Use first available identifier
    for key, value in entity.legal_identifiers.items():
        if value:
            return value, key

    return "", ""


def format_date(date_obj) -> str:
    """Format date object to YYYY-MM-DD string."""
    if date_obj:
        return date_obj.strftime("%Y-%m-%d")
    return ""


# Report Generation Functions


def generate_b_01_01_main_entity(zip_file, main_entity: Entity) -> None:
    """
    Generate b_01.01.csv - Main entity information.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
    """
    from datetime import datetime

    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030", "c0040", "c0050", "c0060"])

    # Extract LEI from legal identifiers
    lei = ""
    if main_entity.legal_identifiers:
        lei = main_entity.legal_identifiers.get("LEI", "")

    # Format country with eba_GA: prefix
    country = ""
    if main_entity.country:
        country = f"eba_GA:{main_entity.country}"

    # Get current date for report
    report_date = datetime.now().strftime("%Y-%m-%d")

    # Write entity data
    csv_writer.writerow(
        [
            lei,
            main_entity.name,
            country,
            main_entity.dora_entity_type or "",
            main_entity.dora_competent_authority or "",
            report_date,
        ]
    )

    # Add CSV to zip
    zip_file.writestr("reports/b_01.01.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_01_02_entities(
    zip_file, main_entity: Entity, all_entities: List[Entity]
) -> None:
    """
    Generate b_01.02.csv - Entity register with all entity details.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        all_entities: List of entities (main entity + subsidiaries only, no branches)
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(
        [
            "c0010",  # LEI
            "c0020",  # Name
            "c0030",  # Country
            "c0040",  # Entity type
            "c0050",  # Entity hierarchy
            "c0060",  # Parent entity LEI
            "c0070",  # Last update
            "c0080",  # Integration date
            "c0090",  # Deletion date
            "c0100",  # Currency
            "c0110",  # Assets value
        ]
    )

    # Write entity data for each entity
    for entity in all_entities:
        lei = ""
        if entity.legal_identifiers:
            lei = entity.legal_identifiers.get("LEI", "")

        country = ""
        if entity.country:
            country = f"eba_GA:{entity.country}"

        currency = ""
        if entity.currency:
            currency = f"eba_CU:{entity.currency}"

        # Format dates, use 2999-12-31 as default for mandatory fields
        last_update = (
            format_date(entity.updated_at) if entity.updated_at else "2999-12-31"
        )
        integration_date = (
            format_date(entity.created_at) if entity.created_at else "2999-12-31"
        )
        deletion_date = "2999-12-31"  # Empty for active entities

        # LEI of parent entity
        parent_entity_lei = ""
        if entity.parent_entity and entity.parent_entity.legal_identifiers:
            parent_entity_lei = entity.parent_entity.legal_identifiers.get("LEI", "")

        csv_writer.writerow(
            [
                lei,
                entity.name,
                country,
                entity.dora_entity_type or "",
                entity.dora_entity_hierarchy or "",
                parent_entity_lei,
                last_update,
                integration_date,
                deletion_date,
                currency,
                entity.dora_assets_value
                if entity.dora_assets_value is not None
                else "",
            ]
        )

    # Add CSV to zip
    zip_file.writestr("reports/b_01.02.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_01_03_branches(
    zip_file, main_entity: Entity, branches: List[Entity]
) -> None:
    """
    Generate b_01.03.csv - Branches of the main entity.

    Branches are entities with the main entity as parent and dora_provider_person_type not set.
    Subsidiaries (with dora_provider_person_type set) are NOT included in this report.

    Each row represents a branch with:
    - c0010: Main entity LEI
    - c0020: Main entity legal identifier
    - c0030: Main entity identifier type

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        branches: List of branch entities (dora_provider_person_type not set)
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030"])

    # Get main entity identifiers
    main_lei, _ = get_entity_identifier(main_entity, priority=["LEI"])
    main_code, code_type = get_entity_identifier(main_entity)

    # Write branch data (one row per branch, with main entity identifiers)
    for branch in branches:
        csv_writer.writerow([main_lei, main_code, code_type])

    zip_file.writestr("reports/b_01.03.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_02_01_contracts(zip_file, contracts: QuerySet) -> None:
    """
    Generate b_02.01.csv - Contractual arrangements for ICT services.

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(
        [
            "c0010",  # Contract reference
            "c0020",  # Type of contractual arrangement
            "c0030",  # Start date
            "c0040",  # End date
            "c0050",  # Notice period for entity
            "c0060",  # Notice period for provider
            "c0070",  # Governing law country
            "c0080",  # Currency
            "c0090",  # Annual expense
        ]
    )

    # Write contract data
    for contract in contracts:
        contract_ref = contract.ref_id or str(contract.id)
        arrangement_type = contract.dora_contractual_arrangement or ""
        start_date = format_date(contract.start_date)
        end_date = format_date(contract.end_date)
        notice_entity = contract.notice_period_entity or ""
        notice_provider = contract.notice_period_provider or ""
        governing_law = contract.governing_law_country or ""
        currency = contract.currency or ""
        annual_expense = contract.annual_expense or ""

        csv_writer.writerow(
            [
                contract_ref,
                arrangement_type,
                start_date,
                end_date,
                notice_entity,
                notice_provider,
                governing_law,
                currency,
                annual_expense,
            ]
        )

    zip_file.writestr("reports/b_02.01.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_02_02_ict_services(zip_file, contracts: QuerySet) -> None:
    """
    Generate b_02.02.csv - ICT services supporting functions.

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects with solutions
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020"])

    # Write contract-solution data
    for contract in contracts.filter(solution__isnull=False).select_related("solution"):
        contract_ref = contract.ref_id or str(contract.id)
        ict_service_type = contract.solution.dora_ict_service_type or ""

        csv_writer.writerow([contract_ref, ict_service_type])

    zip_file.writestr("reports/b_02.02.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_02_03_intragroup_contracts(zip_file, contracts: QuerySet) -> None:
    """
    Generate b_02.03.csv - Intra-group contractual arrangements.

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030"])

    # Filter intragroup contracts with overarching contract
    intragroup_contracts = contracts.filter(
        is_intragroup=True, overarching_contract__isnull=False
    ).select_related("overarching_contract")

    # Write intra-group contract relationships
    for contract in intragroup_contracts:
        subordinate_ref = contract.ref_id or str(contract.id)
        overarching_ref = contract.overarching_contract.ref_id or str(
            contract.overarching_contract.id
        )
        arrangement_type = contract.dora_contractual_arrangement or ""

        csv_writer.writerow([subordinate_ref, overarching_ref, arrangement_type])

    zip_file.writestr("reports/b_02.03.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_03_01_signing_entities(
    zip_file, main_entity: Entity, contracts: QuerySet
) -> None:
    """
    Generate b_03.01.csv - Signing entities (main entity for all contracts).

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        contracts: QuerySet of Contract objects
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030"])

    # Get main entity identifier
    main_code, code_type = get_entity_identifier(main_entity)

    # Write contract-entity data (main entity signs all contracts)
    for contract in contracts:
        contract_ref = contract.ref_id or str(contract.id)
        csv_writer.writerow([contract_ref, main_code, code_type])

    zip_file.writestr("reports/b_03.01.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_03_02_ict_providers(zip_file, contracts: QuerySet) -> None:
    """
    Generate b_03.02.csv - ICT third-party service providers.

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects with providers
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030"])

    # Get third-party contracts with providers
    third_party_contracts = contracts.filter(
        is_intragroup=False, provider_entity__isnull=False
    ).select_related("provider_entity")

    # Write provider data
    for contract in third_party_contracts:
        contract_ref = contract.ref_id or str(contract.id)
        provider = contract.provider_entity

        provider_code, code_type = get_entity_identifier(provider)

        csv_writer.writerow([contract_ref, provider_code, code_type])

    zip_file.writestr("reports/b_03.02.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_03_03_intragroup_providers(
    zip_file, main_entity: Entity, contracts: QuerySet
) -> None:
    """
    Generate b_03.03.csv - ICT intra-group service providers.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        contracts: QuerySet of Contract objects
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030"])

    # Get main entity identifier
    main_code, code_type = get_entity_identifier(main_entity)

    # Get intra-group contracts
    intragroup_contracts = contracts.filter(is_intragroup=True)

    # Write provider data (main entity provides intra-group services)
    for contract in intragroup_contracts:
        contract_ref = contract.ref_id or str(contract.id)
        csv_writer.writerow([contract_ref, main_code, code_type])

    zip_file.writestr("reports/b_03.03.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_04_01_service_users(
    zip_file, main_entity: Entity, branches: List[Entity], contracts: QuerySet
) -> None:
    """
    Generate b_04.01.csv - Entities using ICT services.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        branches: List of branch entities
        contracts: QuerySet of Contract objects
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030", "c0040"])

    # Combine main entity and branches
    all_entities = [main_entity] + list(branches)

    # Get main entity identifier
    main_code, main_code_type = get_entity_identifier(main_entity)

    # Write user data for each contract
    for contract in contracts:
        contract_ref = contract.ref_id or str(contract.id)

        for entity in all_entities:
            entity_code, code_type = get_entity_identifier(entity)

            # Determine if this is a branch
            branch_code = ""
            if entity.parent_entity:
                branch_code = entity_code

            csv_writer.writerow([contract_ref, main_code, main_code_type, branch_code])

    zip_file.writestr("reports/b_04.01.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_05_01_provider_details(
    zip_file, main_entity: Entity, contracts: QuerySet
) -> None:
    """
    Generate b_05.01.csv - Details of ICT third-party service providers.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        contracts: QuerySet of Contract objects with providers
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(
        [
            "c0010",  # Provider code
            "c0020",  # Provider code type
            "c0030",  # Country
            "c0040",  # Type of person
            "c0050",  # Expense currency
            "c0060",  # Total annual expense
            "c0070",  # Competent authority
            "c0080",  # Parent code
            "c0090",  # Parent code type
        ]
    )

    # Aggregate expenses by provider
    providers_data = {}

    third_party_contracts = contracts.filter(
        is_intragroup=False, provider_entity__isnull=False
    ).select_related("provider_entity")

    for contract in third_party_contracts:
        provider = contract.provider_entity
        provider_id = provider.id

        if provider_id not in providers_data:
            providers_data[provider_id] = {
                "provider": provider,
                "total_expense": 0,
                "currency": contract.currency or main_entity.currency or "",
            }

        if contract.annual_expense:
            providers_data[provider_id]["total_expense"] += contract.annual_expense

    # Write provider data
    for provider_id, data in providers_data.items():
        provider = data["provider"]

        provider_code, code_type = get_entity_identifier(provider)
        country = provider.country or ""
        person_type = provider.dora_provider_person_type or ""
        currency = data["currency"]
        total_expense = data["total_expense"]
        competent_authority = provider.dora_competent_authority or ""

        # Get parent entity identifier
        parent_code, parent_code_type = "", ""
        if provider.parent_entity:
            parent_code, parent_code_type = get_entity_identifier(
                provider.parent_entity
            )

        csv_writer.writerow(
            [
                provider_code,
                code_type,
                country,
                person_type,
                currency,
                total_expense,
                competent_authority,
                parent_code,
                parent_code_type,
            ]
        )

    zip_file.writestr("reports/b_05.01.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_05_02_supply_chains(
    zip_file, main_entity: Entity, contracts: QuerySet
) -> None:
    """
    Generate b_05.02.csv - ICT service supply chains.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        contracts: QuerySet of Contract objects with solutions
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(
        [
            "c0010",  # Contract reference
            "c0020",  # ICT service type
            "c0030",  # Provider code
            "c0040",  # Provider code type
            "c0050",  # Rank (criticality)
            "c0060",  # Recipient code
            "c0070",  # Recipient code type
        ]
    )

    # Get main entity identifier
    main_code, main_code_type = get_entity_identifier(main_entity)

    # Get contracts with both provider and solution
    supply_chain_contracts = contracts.filter(
        is_intragroup=False,
        provider_entity__isnull=False,
        solution__isnull=False,
    ).select_related("provider_entity", "solution")

    # Write supply chain data
    for contract in supply_chain_contracts:
        contract_ref = contract.ref_id or str(contract.id)
        ict_service_type = contract.solution.dora_ict_service_type or ""

        provider_code, provider_code_type = get_entity_identifier(
            contract.provider_entity
        )

        rank = contract.solution.criticality if contract.solution.criticality else ""

        csv_writer.writerow(
            [
                contract_ref,
                ict_service_type,
                provider_code,
                provider_code_type,
                rank,
                main_code,
                main_code_type,
            ]
        )

    zip_file.writestr("reports/b_05.02.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_06_01_functions(
    zip_file, main_entity: Entity, business_functions: QuerySet
) -> None:
    """
    Generate b_06.01.csv - Critical or important functions register.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        business_functions: QuerySet of Asset objects with is_business_function=True
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(
        [
            "c0010",  # Function identifier
            "c0020",  # Licensed activity
            "c0030",  # Function name
            "c0040",  # Entity LEI
            "c0050",  # Criticality assessment
            "c0060",  # Criticality reasons
            "c0070",  # Last assessment date
            "c0080",  # RTO
            "c0090",  # RPO
            "c0100",  # Impact of discontinuing
        ]
    )

    # Get main entity LEI
    main_lei, _ = get_entity_identifier(main_entity, priority=["LEI"])

    # Write function data
    for function in business_functions:
        function_id = function.ref_id or str(function.id)
        licensed_activity = function.dora_licenced_activity or ""
        function_name = function.name
        entity_lei = main_lei
        criticality = function.dora_criticality_assessment or ""
        criticality_reasons = function.dora_criticality_justification or ""
        last_assessment_date = (
            format_date(function.updated_at) if function.updated_at else "2999-12-31"
        )

        # Extract RTO from disaster_recovery_objectives JSON
        rto = ""
        if function.disaster_recovery_objectives:
            objectives = function.disaster_recovery_objectives.get("objectives", {})
            rto_obj = objectives.get("rto", {})
            if rto_obj and "value" in rto_obj:
                rto = rto_obj["value"]

        # Extract RPO from disaster_recovery_objectives JSON
        rpo = ""
        if function.disaster_recovery_objectives:
            objectives = function.disaster_recovery_objectives.get("objectives", {})
            rpo_obj = objectives.get("rpo", {})
            if rpo_obj and "value" in rpo_obj:
                rpo = rpo_obj["value"]

        discontinuing_impact = function.dora_discontinuing_impact or ""

        csv_writer.writerow(
            [
                function_id,
                licensed_activity,
                function_name,
                entity_lei,
                criticality,
                criticality_reasons,
                last_assessment_date,
                rto,
                rpo,
                discontinuing_impact,
            ]
        )

    zip_file.writestr("reports/b_06.01.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_07_01_assessment(zip_file, contracts: QuerySet) -> None:
    """
    Generate b_07.01.csv - Assessment of ICT services.

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects with solutions
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(
        [
            "c0010",  # Contract reference
            "c0020",  # Provider code
            "c0030",  # Provider code type
            "c0040",  # ICT service type
            "c0050",  # Substitutability
            "c0060",  # Non-substitutability reason
            "c0070",  # Last audit date
            "c0080",  # Exit plan
            "c0090",  # Reintegration possibility
            "c0100",  # Discontinuing impact
            "c0110",  # Alternative providers identified
            "c0120",  # Alternative provider IDs
        ]
    )

    # Get contracts with both provider and solution
    assessment_contracts = contracts.filter(
        is_intragroup=False,
        provider_entity__isnull=False,
        solution__isnull=False,
    ).select_related("provider_entity", "solution")

    # Write assessment data
    for contract in assessment_contracts:
        contract_ref = contract.ref_id or str(contract.id)

        provider_code, provider_code_type = get_entity_identifier(
            contract.provider_entity
        )

        solution = contract.solution
        ict_service_type = solution.dora_ict_service_type or ""
        substitutability = solution.dora_substitutability or ""
        non_substitutability_reason = solution.dora_non_substitutability_reason or ""
        last_audit_date = (
            format_date(solution.updated_at) if solution.updated_at else ""
        )
        exit_plan = solution.dora_has_exit_plan or ""
        reintegration_possibility = solution.dora_reintegration_possibility or ""
        discontinuing_impact = solution.dora_discontinuing_impact or ""
        alternative_providers_identified = (
            solution.dora_alternative_providers_identified or ""
        )
        alternative_providers = solution.dora_alternative_providers or ""

        csv_writer.writerow(
            [
                contract_ref,
                provider_code,
                provider_code_type,
                ict_service_type,
                substitutability,
                non_substitutability_reason,
                last_audit_date,
                exit_plan,
                reintegration_possibility,
                discontinuing_impact,
                alternative_providers_identified,
                alternative_providers,
            ]
        )

    zip_file.writestr("reports/b_07.01.csv", csv_buffer.getvalue().encode("utf-8"))


def generate_b_99_01_aggregation(
    zip_file, contracts: QuerySet, business_functions: QuerySet
) -> None:
    """
    Generate b_99.01.csv - Aggregation report placeholder (standard not yet finalized).

    This currently only generates headers as the DORA standard for this report
    is not yet properly defined.

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects with solutions
        business_functions: QuerySet of Asset objects with is_business_function=True
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(
        [
            "c0010",  # Standalone arrangement
            "c0020",  # Overarching arrangement
            "c0030",  # Subsequent or associated arrangement
            "c0040",  # Data sensitiveness: Low
            "c0050",  # Data sensitiveness: Medium
            "c0060",  # Data sensitiveness: High
            "c0070",  # Impact discontinuing function: Low
            "c0080",  # Impact discontinuing function: Medium
            "c0090",  # Impact discontinuing function: High
            "c0100",  # Substitutability: Not substitutable
            "c0110",  # Substitutability: Highly complex
            "c0120",  # Substitutability: Medium complexity
            "c0130",  # Substitutability: Easily substitutable
            "c0140",  # Reintegration: Easy
            "c0150",  # Reintegration: Difficult
            "c0160",  # Reintegration: Highly complex
            "c0170",  # Impact discontinuing ICT: Low
            "c0180",  # Impact discontinuing ICT: Medium
            "c0190",  # Impact discontinuing ICT: High
        ]
    )

    # TODO: Add data rows once DORA standard is properly defined

    zip_file.writestr("reports/b_99.01.csv", csv_buffer.getvalue().encode("utf-8"))
