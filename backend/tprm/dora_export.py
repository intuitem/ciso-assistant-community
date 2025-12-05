"""
DORA (Digital Operational Resilience Act) ROI (Register of Information) export utilities.

This module contains functions to generate various CSV reports required by DORA regulations.
Each function generates a specific report and writes it to a ZIP file.
"""

import csv
import io
import json
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


def generate_b_01_01_main_entity(
    zip_file, main_entity: Entity, folder_prefix: str = ""
) -> None:
    """
    Generate b_01.01.csv - Main entity information.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        folder_prefix: Optional folder prefix to prepend to file path
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

    # Add CSV to zip with folder prefix
    path = (
        f"{folder_prefix}/reports/b_01.01.csv"
        if folder_prefix
        else "reports/b_01.01.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_01_02_entities(
    zip_file, main_entity: Entity, all_entities: List[Entity], folder_prefix: str = ""
) -> None:
    """
    Generate b_01.02.csv - Entity register with all entity details.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        all_entities: List of entities (main entity + subsidiaries only, no branches)
        folder_prefix: Optional folder prefix to prepend to file path
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
    path = (
        f"{folder_prefix}/reports/b_01.02.csv"
        if folder_prefix
        else "reports/b_01.02.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_01_03_branches(
    zip_file, branches: List[Entity], folder_prefix: str = ""
) -> None:
    """
    Generate b_01.03.csv - Branches register.

    Branches are entities with dora_provider_person_type not set.
    Subsidiaries (with dora_provider_person_type set) are NOT included in this report.

    For each branch, the LEI of its parent entity (head office) is reported in c0020.

    Columns:
    - c0010: Identification code of the branch
    - c0020: LEI of the financial entity head office of the branch (parent entity)
    - c0030: Name of the branch
    - c0040: Country of the branch

    Args:
        zip_file: ZIP file object to write to
        branches: List of branch entities (dora_provider_person_type not set)
        folder_prefix: Optional folder prefix to prepend to file path
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030", "c0040"])

    # Write branch data (one row per branch)
    for branch in branches:
        # c0010: Identification code of the branch
        branch_code, _ = get_entity_identifier(branch)

        # c0020: LEI of the financial entity head office (parent entity)
        head_office_lei = ""
        if branch.parent_entity:
            head_office_lei, _ = get_entity_identifier(
                branch.parent_entity, priority=["LEI"]
            )

        # c0030: Name of the branch
        branch_name = branch.name

        # c0040: Country of the branch
        branch_country = ""
        if branch.country:
            branch_country = f"eba_GA:{branch.country}"

        csv_writer.writerow([branch_code, head_office_lei, branch_name, branch_country])

    path = (
        f"{folder_prefix}/reports/b_01.03.csv"
        if folder_prefix
        else "reports/b_01.03.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_02_01_contracts(
    zip_file, contracts: QuerySet, folder_prefix: str = ""
) -> None:
    """
    Generate b_02.01.csv - Contractual arrangements – General Information.

    Only includes contracts associated with solutions that are linked to business function assets.

    Columns:
    - b_02.01.0010: Contractual arrangement reference number
    - b_02.01.0020: Type of contractual arrangement
    - b_02.01.0030: Overarching contractual arrangement reference number
    - b_02.01.0040: Currency of the amount reported in RT.02.01.0050
    - b_02.01.0050: Annual expense or estimated cost

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(
        [
            "c0010",  # Contractual arrangement reference number
            "c0020",  # Type of contractual arrangement
            "c0030",  # Overarching contractual arrangement reference number
            "c0040",  # Currency
            "c0050",  # Annual expense
        ]
    )

    # Filter contracts: only those with solutions linked to business function assets
    filtered_contracts = (
        contracts.filter(
            solutions__isnull=False, solutions__assets__is_business_function=True
        )
        .distinct()
        .select_related("overarching_contract")
    )

    # Write contract data
    for contract in filtered_contracts:
        # b_02.01.0010: Contractual arrangement reference number
        contract_ref = contract.ref_id or str(contract.id)

        # b_02.01.0020: Type of contractual arrangement
        arrangement_type = contract.dora_contractual_arrangement or ""

        # b_02.01.0030: Overarching contractual arrangement reference number
        overarching_ref = ""
        if contract.overarching_contract:
            overarching_ref = contract.overarching_contract.ref_id or str(
                contract.overarching_contract.id
            )

        # b_02.01.0040: Currency
        currency = ""
        if contract.currency:
            currency = f"eba_CU:{contract.currency}"

        # b_02.01.0050: Annual expense
        annual_expense = (
            contract.annual_expense if contract.annual_expense is not None else ""
        )

        csv_writer.writerow(
            [
                contract_ref,
                arrangement_type,
                overarching_ref,
                currency,
                annual_expense,
            ]
        )

    path = (
        f"{folder_prefix}/reports/b_02.01.csv"
        if folder_prefix
        else "reports/b_02.01.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_02_02_ict_services(
    zip_file,
    contracts: QuerySet,
    folder_prefix: str = "",
    business_function_asset_ids: set = None,
) -> None:
    """
    Generate b_02.02.csv - ICT services supporting functions.

    Only includes contracts associated with solutions that are linked to business function assets
    or their child assets.
    One row per contract-function combination.

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects with solutions
        folder_prefix: Optional folder prefix to prepend to file path
        business_function_asset_ids: Set of asset IDs related to business functions (including children)
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers (18 columns)
    csv_writer.writerow(
        [
            "c0010",  # Contractual arrangement reference number
            "c0020",  # LEI of the entity making use of the ICT service(s)
            "c0030",  # Identification code of the ICT third-party service provider
            "c0040",  # Type of code to identify the ICT third-party service provider
            "c0050",  # Function identifier
            "c0060",  # Type of ICT services
            "c0070",  # Start date of the contractual arrangement
            "c0080",  # End date of the contractual arrangement
            "c0090",  # Reason of the termination or ending
            "c0100",  # Notice period for the financial entity
            "c0110",  # Notice period for the ICT third-party service provider
            "c0120",  # Country of the governing law
            "c0130",  # Country of provision of the ICT services
            "c0140",  # Storage of data
            "c0150",  # Location of the data at rest (storage)
            "c0160",  # Location of management of the data (processing)
            "c0170",  # Sensitiveness of the data stored
            "c0180",  # Level of reliance on the ICT service
        ]
    )

    # Filter contracts: only those with solutions linked to business function assets or their children
    if business_function_asset_ids:
        filtered_contracts = (
            contracts.filter(
                solutions__isnull=False,
                solutions__assets__id__in=business_function_asset_ids,
            )
            .distinct()
            .select_related("provider_entity", "beneficiary_entity")
            .prefetch_related("solutions__assets")
        )
    else:
        # Fallback to old behavior if business_function_asset_ids not provided
        filtered_contracts = (
            contracts.filter(
                solutions__isnull=False, solutions__assets__is_business_function=True
            )
            .distinct()
            .select_related("provider_entity", "beneficiary_entity")
            .prefetch_related("solutions__assets")
        )

    # Write contract-solution-function data
    for contract in filtered_contracts:
        # Iterate through all solutions in this contract
        for solution in contract.solutions.all():
            # Get business functions associated with this solution (directly or through children)
            if business_function_asset_ids:
                business_functions = solution.assets.filter(is_business_function=True)
            else:
                business_functions = solution.assets.filter(is_business_function=True)

            for function in business_functions:
                # c0010: Contract reference
                contract_ref = contract.ref_id or str(contract.id)

                # c0020: LEI of entity using the service (beneficiary entity)
                entity_lei = ""
                if contract.beneficiary_entity:
                    entity_lei, _ = get_entity_identifier(
                        contract.beneficiary_entity, priority=["LEI"]
                    )

                # c0030, c0040: Provider identification
                provider_code, provider_code_type = "", ""
                if contract.provider_entity:
                    provider_code, provider_code_type = get_entity_identifier(
                        contract.provider_entity,
                        priority=["LEI", "EUID", "VAT", "DUNS"],
                    )

                # c0050: Function identifier
                function_id = function.ref_id or str(function.id)

                # c0060: Type of ICT services
                ict_service_type = solution.dora_ict_service_type or ""

                # c0070: Start date
                start_date = (
                    format_date(contract.start_date) if contract.start_date else ""
                )

                # c0080: End date (use placeholder if not set)
                end_date = (
                    format_date(contract.end_date)
                    if contract.end_date
                    else "2999-12-31"
                )

                # c0090: Termination reason
                termination_reason = contract.termination_reason or ""

                # c0100: Notice period for entity (days)
                notice_period_entity = (
                    contract.notice_period_entity
                    if contract.notice_period_entity is not None
                    else ""
                )

                # c0110: Notice period for provider (days)
                notice_period_provider = (
                    contract.notice_period_provider
                    if contract.notice_period_provider is not None
                    else ""
                )

                # c0120: Country of governing law
                governing_law_country = ""
                if contract.governing_law_country:
                    governing_law_country = f"eba_GA:{contract.governing_law_country}"

                # c0130: Country of provision of ICT services (provider country)
                provider_country = ""
                if contract.provider_entity and contract.provider_entity.country:
                    provider_country = f"eba_GA:{contract.provider_entity.country}"

                # c0140: Storage of data (Yes/No)
                storage_of_data = (
                    "eba_BT:x28" if solution.storage_of_data else "eba_BT:x29"
                )

                # c0150: Location of data at rest
                data_location_storage = ""
                if solution.data_location_storage:
                    data_location_storage = f"eba_GA:{solution.data_location_storage}"

                # c0160: Location of data processing
                data_location_processing = ""
                if solution.data_location_processing:
                    data_location_processing = (
                        f"eba_GA:{solution.data_location_processing}"
                    )

                # c0170: Data sensitiveness
                data_sensitiveness = solution.dora_data_sensitiveness or ""

                # c0180: Level of reliance
                reliance_level = solution.dora_reliance_level or ""

                csv_writer.writerow(
                    [
                        contract_ref,
                        entity_lei,
                        provider_code,
                        provider_code_type,
                        function_id,
                        ict_service_type,
                        start_date,
                        end_date,
                        termination_reason,
                        notice_period_entity,
                        notice_period_provider,
                        governing_law_country,
                        provider_country,
                        storage_of_data,
                        data_location_storage,
                        data_location_processing,
                        data_sensitiveness,
                        reliance_level,
                    ]
                )

    path = (
        f"{folder_prefix}/reports/b_02.02.csv"
        if folder_prefix
        else "reports/b_02.02.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_02_03_intragroup_contracts(
    zip_file, contracts: QuerySet, folder_prefix: str = ""
) -> None:
    """
    Generate b_02.03.csv - Intra-group contractual arrangements.

    Only includes intra-group contracts with an overarching contract.

    Columns:
    - c0010: Subordinate contractual arrangement reference number
    - c0020: Overarching contractual arrangement reference number
    - c0030: Link (always "true" for populated rows)

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects
        folder_prefix: Optional folder prefix to prepend to file path
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
        # c0010: Subordinate contractual arrangement reference number
        subordinate_ref = contract.ref_id or str(contract.id)

        # c0020: Overarching contractual arrangement reference number
        overarching_ref = contract.overarching_contract.ref_id or str(
            contract.overarching_contract.id
        )

        # c0030: Link (always "true" for populated rows)
        link = "true"

        csv_writer.writerow([subordinate_ref, overarching_ref, link])

    path = (
        f"{folder_prefix}/reports/b_02.03.csv"
        if folder_prefix
        else "reports/b_02.03.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_03_01_signing_entities(
    zip_file, main_entity: Entity, contracts: QuerySet, folder_prefix: str = ""
) -> None:
    """
    Generate b_03.01.csv - Signing entities (main entity for all contracts).

    Columns:
    - c0010: Contractual arrangement reference number
    - c0020: LEI of the entity signing the contractual arrangement
    - c0030: Link (always "true" for populated rows)

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        contracts: QuerySet of Contract objects
        folder_prefix: Optional folder prefix to prepend to file path
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030"])

    # Get main entity identifier
    main_code, _ = get_entity_identifier(main_entity)

    # Write contract-entity data (main entity signs all contracts)
    for contract in contracts:
        # c0010: Contract reference
        contract_ref = contract.ref_id or str(contract.id)

        # c0020: LEI of signing entity (main entity)
        signing_entity_lei = main_code

        # c0030: Link (always "true" for populated rows)
        link = "true"

        csv_writer.writerow([contract_ref, signing_entity_lei, link])

    path = (
        f"{folder_prefix}/reports/b_03.01.csv"
        if folder_prefix
        else "reports/b_03.01.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_03_02_ict_providers(
    zip_file, contracts: QuerySet, folder_prefix: str = ""
) -> None:
    """
    Generate b_03.02.csv - ICT third-party service providers.

    Columns:
    - c0010: Contractual arrangement reference number
    - c0020: Identification code of ICT third-party service provider
    - c0030: Type of code to identify the ICT third-party service provider
    - c0045: Link (fill with "true" for each populated row)

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects with providers
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030", "c0045"])

    # Get third-party contracts with providers
    third_party_contracts = contracts.filter(
        is_intragroup=False, provider_entity__isnull=False
    ).select_related("provider_entity")

    # Write provider data
    for contract in third_party_contracts:
        contract_ref = contract.ref_id or str(contract.id)
        provider = contract.provider_entity

        # Get provider identifier (prioritize LEI)
        provider_code, code_type = get_entity_identifier(
            provider, priority=["LEI", "EUID", "VAT", "DUNS"]
        )

        csv_writer.writerow([contract_ref, provider_code, code_type, "true"])

    path = (
        f"{folder_prefix}/reports/b_03.02.csv"
        if folder_prefix
        else "reports/b_03.02.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_03_03_intragroup_providers(
    zip_file, main_entity: Entity, contracts: QuerySet, folder_prefix: str = ""
) -> None:
    """
    Generate b_03.03.csv - Entities signing the Contractual arrangements for providing ICT service(s)
    to other entity within the scope of consolidation.

    Columns:
    - b_03.03.0010 (c0010): Contractual arrangement reference number
    - b_03.03.0020 (c0020): LEI of the entity providing ICT services
    - b_03.03.0031 (c0031): Link (fill with "true" for each populated row)

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        contracts: QuerySet of Contract objects
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0031"])

    # Get main entity LEI
    main_lei, _ = get_entity_identifier(main_entity, priority=["LEI"])

    # Get intra-group contracts
    intragroup_contracts = contracts.filter(is_intragroup=True)

    # Write provider data (main entity provides intra-group services)
    for contract in intragroup_contracts:
        contract_ref = contract.ref_id or str(contract.id)
        csv_writer.writerow([contract_ref, main_lei, "true"])

    path = (
        f"{folder_prefix}/reports/b_03.03.csv"
        if folder_prefix
        else "reports/b_03.03.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_04_01_service_users(
    zip_file,
    branches: List[Entity],
    contracts: QuerySet,
    folder_prefix: str = "",
) -> None:
    """
    Generate b_04.01.csv - Entities using ICT services.

    For each contract, reports which entities use the service.
    - One row per contract for the beneficiary entity (branch code empty, nature = "not a branch")
    - Additional rows for each branch that uses the contract (branch code filled, nature = "branch")

    Columns:
    - c0010: Contractual arrangement reference number
    - c0020: LEI of the entity making use of the ICT service(s) (beneficiary entity)
    - c0030: Nature of the entity (branch or not branch)
    - c0040: Identification code of the branch

    Args:
        zip_file: ZIP file object to write to
        branches: List of branch entities
        contracts: QuerySet of Contract objects
        folder_prefix: Optional folder prefix to prepend to file path
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["c0010", "c0020", "c0030", "c0040"])

    # Select related beneficiary_entity for performance
    contracts = contracts.select_related("beneficiary_entity")

    # Track written combinations to avoid duplicates
    written_combinations = set()

    # Write user data for each contract
    for contract in contracts:
        # c0010: Contract reference
        contract_ref = contract.ref_id or str(contract.id)

        # c0020: LEI of beneficiary entity
        beneficiary_lei = ""
        if contract.beneficiary_entity:
            beneficiary_lei, _ = get_entity_identifier(
                contract.beneficiary_entity, priority=["LEI"]
            )

        # Write row for beneficiary entity (not a branch)
        combination = (contract_ref, beneficiary_lei, "")
        if combination not in written_combinations:
            # c0030: Nature of entity (not a branch)
            entity_nature = "eba_ZZ:x839"  # not a branch
            # c0040: Branch code (empty for non-branch)
            branch_code = ""

            csv_writer.writerow(
                [contract_ref, beneficiary_lei, entity_nature, branch_code]
            )
            written_combinations.add(combination)

        # Write rows for branches
        for branch in branches:
            branch_code, _ = get_entity_identifier(branch)
            combination = (contract_ref, beneficiary_lei, branch_code)
            if combination not in written_combinations:
                # c0030: Nature of entity (branch of a financial entity)
                entity_nature = "eba_ZZ:x838"  # branch of a financial entity

                csv_writer.writerow(
                    [contract_ref, beneficiary_lei, entity_nature, branch_code]
                )
                written_combinations.add(combination)

    path = (
        f"{folder_prefix}/reports/b_04.01.csv"
        if folder_prefix
        else "reports/b_04.01.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_05_01_provider_details(
    zip_file, main_entity: Entity, contracts: QuerySet, folder_prefix: str = ""
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
            "c0010",  # Identification code of ICT third-party service provider
            "c0020",  # Type of code
            "c0030",  # Name of the ICT third-party service provider
            "c0040",  # Type of person
            "c0050",  # Country
            "c0060",  # Currency
            "c0070",  # Total annual expense
            "c0080",  # Identification code of parent undertaking
            "c0090",  # Type of code for parent undertaking
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

        # c0010, c0020: Provider identifier (prioritize LEI)
        provider_code, code_type = get_entity_identifier(
            provider, priority=["LEI", "EUID", "VAT", "DUNS"]
        )

        # c0030: Provider name
        provider_name = provider.name

        # c0040: Type of person
        person_type = provider.dora_provider_person_type or ""

        # c0050: Country with eba_GA prefix
        country = ""
        if provider.country:
            country = f"eba_GA:{provider.country}"

        # c0060: Currency with eba_CU prefix
        currency = ""
        if data["currency"]:
            currency = f"eba_CU:{data['currency']}"

        # c0070: Total annual expense
        total_expense = data["total_expense"]

        # c0080, c0090: Parent entity identifier (prioritize LEI)
        parent_code, parent_code_type = "", ""
        if provider.parent_entity:
            parent_code, parent_code_type = get_entity_identifier(
                provider.parent_entity, priority=["LEI", "EUID", "VAT", "DUNS"]
            )

        csv_writer.writerow(
            [
                provider_code,
                code_type,
                provider_name,
                person_type,
                country,
                currency,
                total_expense,
                parent_code,
                parent_code_type,
            ]
        )

    path = (
        f"{folder_prefix}/reports/b_05.01.csv"
        if folder_prefix
        else "reports/b_05.01.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_05_02_supply_chains(
    zip_file, contracts: QuerySet, folder_prefix: str = ""
) -> None:
    """
    Generate b_05.02.csv - ICT service supply chains.

    Columns:
    - c0010: Contractual arrangement reference number
    - c0020: Type of ICT services
    - c0030: Identification code of the ICT third-party service provider
    - c0040: Type of code to identify the provider
    - c0050: Rank (criticality)
    - c0060: Identification code of the recipient (beneficiary entity)
    - c0070: Type of code to identify the recipient

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects with solutions
        folder_prefix: Optional folder prefix to prepend to file path
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

    # Get contracts with both provider and solutions
    supply_chain_contracts = (
        contracts.filter(
            is_intragroup=False,
            provider_entity__isnull=False,
            solutions__isnull=False,
        )
        .select_related("provider_entity", "beneficiary_entity")
        .prefetch_related("solutions")
    )

    # Write supply chain data
    for contract in supply_chain_contracts:
        # Iterate through all solutions in this contract
        for solution in contract.solutions.all():
            # c0010: Contract reference
            contract_ref = contract.ref_id or str(contract.id)

            # c0020: ICT service type
            ict_service_type = solution.dora_ict_service_type or ""

            # c0030, c0040: Provider identification
            provider_code, provider_code_type = get_entity_identifier(
                contract.provider_entity
            )

            # c0050: Rank (criticality)
            rank = solution.criticality if solution.criticality else ""

            # c0060, c0070: Recipient identification (beneficiary entity)
            recipient_code, recipient_code_type = "", ""
            if contract.beneficiary_entity:
                recipient_code, recipient_code_type = get_entity_identifier(
                    contract.beneficiary_entity
                )

            csv_writer.writerow(
                [
                    contract_ref,
                    ict_service_type,
                    provider_code,
                    provider_code_type,
                    rank,
                    recipient_code,
                    recipient_code_type,
                ]
            )

    path = (
        f"{folder_prefix}/reports/b_05.02.csv"
        if folder_prefix
        else "reports/b_05.02.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_06_01_functions(
    zip_file, main_entity: Entity, business_functions: QuerySet, folder_prefix: str = ""
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

    path = (
        f"{folder_prefix}/reports/b_06.01.csv"
        if folder_prefix
        else "reports/b_06.01.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_07_01_assessment(
    zip_file, contracts: QuerySet, folder_prefix: str = ""
) -> None:
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

    # Get contracts with both provider and solutions
    assessment_contracts = (
        contracts.filter(
            is_intragroup=False,
            provider_entity__isnull=False,
            solutions__isnull=False,
        )
        .select_related("provider_entity")
        .prefetch_related("solutions")
    )

    # Write assessment data
    for contract in assessment_contracts:
        # Iterate through all solutions in this contract
        for solution in contract.solutions.all():
            contract_ref = contract.ref_id or str(contract.id)

            provider_code, provider_code_type = get_entity_identifier(
                contract.provider_entity
            )

            ict_service_type = solution.dora_ict_service_type or ""
            substitutability = solution.dora_substitutability or ""
            non_substitutability_reason = (
                solution.dora_non_substitutability_reason or ""
            )
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

    path = (
        f"{folder_prefix}/reports/b_07.01.csv"
        if folder_prefix
        else "reports/b_07.01.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_b_99_01_aggregation(
    zip_file, contracts: QuerySet, business_functions: QuerySet, folder_prefix: str = ""
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

    path = (
        f"{folder_prefix}/reports/b_99.01.csv"
        if folder_prefix
        else "reports/b_99.01.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_filing_indicators(zip_file, folder_prefix: str = "") -> None:
    """
    Generate FilingIndicators.csv - Indicates which templates are included in the report.

    This file lists all the DORA ROI template IDs with a "reported" flag set to TRUE,
    indicating that each template has been included in the export.

    Args:
        zip_file: ZIP file object to write to
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["templateID", "reported"])

    # List of all DORA ROI template IDs
    template_ids = [
        "B_01.01",
        "B_01.02",
        "B_01.03",
        "B_02.01",
        "B_02.02",
        "B_02.03",
        "B_03.01",
        "B_03.02",
        "B_03.03",
        "B_04.01",
        "B_05.01",
        "B_05.02",
        "B_06.01",
        "B_07.01",
        "B_99.01",
    ]

    # Write each template ID with reported=true
    for template_id in template_ids:
        csv_writer.writerow([template_id, "true"])

    path = (
        f"{folder_prefix}/reports/FilingIndicators.csv"
        if folder_prefix
        else "reports/FilingIndicators.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_parameters(zip_file, main_entity: Entity, folder_prefix: str = "") -> None:
    """
    Generate parameters.csv - Report metadata and configuration parameters.

    This file contains key metadata about the DORA ROI report including entity
    identification, reporting period, base currency, and decimal formatting rules.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["name", "value"])

    # Get LEI for entityID
    lei, _ = get_entity_identifier(main_entity, priority=["LEI"])
    entity_id = f"rs:{lei}.CON" if lei else "rs:UNKNOWN.CON"

    # Get currency for baseCurrency
    base_currency = (
        f"iso4217:{main_entity.currency}" if main_entity.currency else "iso4217:EUR"
    )

    # Write parameters
    parameters = [
        ("entityID", entity_id),
        ("refPeriod", "2025-03-31"),  # Placeholder - can be made dynamic later
        ("baseCurrency", base_currency),
        ("decimalsInteger", "0"),
        ("decimalsMonetary", "-3"),
    ]

    for name, value in parameters:
        csv_writer.writerow([name, value])

    path = (
        f"{folder_prefix}/reports/parameters.csv"
        if folder_prefix
        else "reports/parameters.csv"
    )
    zip_file.writestr(path, csv_buffer.getvalue().encode("utf-8"))


def generate_report_package_json(zip_file, folder_prefix: str = "") -> None:
    """
    Generate META-INF/reportPackage.json - Report package metadata.

    This file contains metadata about the XBRL report package format.

    Args:
        zip_file: ZIP file object to write to
    """
    report_package = {
        "documentInfo": {"documentType": "https://xbrl.org/report-package/2023"}
    }

    json_content = json.dumps(report_package, indent=2)
    path = (
        f"{folder_prefix}/META-INF/reportPackage.json"
        if folder_prefix
        else "META-INF/reportPackage.json"
    )
    zip_file.writestr(path, json_content)


def generate_report_json(zip_file, folder_prefix: str = "") -> None:
    """
    Generate reports/report.json - Report metadata and XBRL CSV configuration.

    This file contains metadata about the XBRL CSV format and references to
    the DORA taxonomy.

    Args:
        zip_file: ZIP file object to write to
    """
    report_metadata = {
        "documentInfo": {
            "documentType": "https://xbrl.org/2021/xbrl-csv",
            "extends": [
                "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/dora/4.0/mod/dora.json"
            ],
        }
    }

    json_content = json.dumps(report_metadata, indent=2)
    path = (
        f"{folder_prefix}/reports/report.json"
        if folder_prefix
        else "reports/report.json"
    )
    zip_file.writestr(path, json_content)
