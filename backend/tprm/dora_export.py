"""
DORA (Digital Operational Resilience Act) ROI (Register of Information) export utilities.

This module contains functions to generate various CSV reports required by DORA regulations.
Each function generates a specific report and writes it to a ZIP file.
"""

import csv
import io
import json
from datetime import date, datetime
from typing import Dict, List, Optional, Any

from django.db.models import QuerySet
from tprm.models import Entity, Contract, Solution
from core.models import Asset


# Helper Functions

IDENTIFIER_PRIORITY = ["LEI", "EUID", "KBO", "CRN", "VAT", "PNR", "NIN", "DUNS"]


def get_dora_export_metadata(
    main_entity: Entity,
    identifier_type: str = None,
    level: str = "IND",
    naming_convention: str = "nbb",
) -> dict:
    """
    Compute metadata for DORA RoI export.

    Args:
        main_entity: The main financial entity
        identifier_type: Explicit identifier key to use (e.g. "LEI", "KBO"). If None, uses priority list.
        level: Consolidation level — "IND" (individual) or "CON" (consolidated). Defaults to "IND".
        naming_convention: "nbb" for NBB format, "eba" for EBA FAQ #24 format.

    Returns:
        Dictionary with:
        - folder_prefix: The prefix for files inside the ZIP
        - filename: The name of the ZIP file
        - entity_id: The identifier for parameters.csv
        - competent_authority: The authority name used in naming
    """
    if level not in ("IND", "CON"):
        raise ValueError(f"Invalid level '{level}'. Must be 'IND' or 'CON'.")

    priority = [identifier_type] if identifier_type else None
    code, xbrl_type, key_name = get_entity_identifier(main_entity, priority=priority)
    if not code or (identifier_type and key_name != identifier_type):
        missing = identifier_type or "legal identifier"
        raise ValueError(
            f"Cannot generate DORA RoI export: main entity has no {missing}. "
            f"Please set a {missing} in the main entity's legal identifiers before exporting."
        )

    authority = main_entity.dora_competent_authority or "UNKNOWN"
    folder_prefix = f"{key_name}_{code}.{level}_{authority}_DOR_DORA_ROI"
    entity_id = f"rs:{code}.{level}"

    if naming_convention == "eba":
        country = getattr(main_entity, "country", None) or "XX"
        if len(country) > 2:
            country = country[:2].upper()
        ref_date = f"{date.today().year - 1}-12-31"
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%Sz")
        filename = f"{key_name}_{code}.{level}_{country}_DORA010100_DORA_{ref_date}_{timestamp}.zip"
    else:
        filename = f"{folder_prefix}.zip"

    return {
        "folder_prefix": folder_prefix,
        "filename": filename,
        "entity_id": entity_id,
        "competent_authority": authority,
    }


def get_ultimate_parent(entity):
    """Walk parent_entity chain to the root. Returns None if no parent."""
    current = entity.parent_entity
    seen = {entity.pk}
    while current is not None:
        if current.pk in seen:
            break  # cycle guard
        seen.add(current.pk)
        if current.parent_entity is None:
            return current
        current = current.parent_entity
    return current


def get_provider_chain(entity):
    """
    Walk parent_entity from entity to root.
    Returns list from root to leaf, e.g. [A, B, C] where A is root.
    If entity has no parent, returns [entity].
    """
    chain = [entity]
    seen = {entity.pk}
    current = entity
    while current.parent_entity is not None:
        parent = current.parent_entity
        if parent.pk in seen:
            break  # cycle guard
        seen.add(parent.pk)
        chain.append(parent)
        current = parent
    chain.reverse()  # root first
    return chain


def get_entity_identifier(
    entity: Entity, priority: List[str] = None
) -> tuple[str, str, str]:
    """
    Extract identification code, type, and key name from entity's legal_identifiers.

    Args:
        entity: Entity object with legal_identifiers
        priority: List of identifier types in priority order (default: LEI, EUID, KBO, VAT, DUNS)

    Returns:
        Tuple of (identifier_code, identifier_type, key_name)
    """
    if priority is None:
        priority = IDENTIFIER_PRIORITY

    if not entity or not entity.legal_identifiers:
        return "", "", ""

    def map_identifier_type(key: str) -> str:
        key_upper = key.upper()
        if key_upper == "LEI":
            return "eba_qCO:qx2000"
        elif key_upper == "EUID":
            return "eba_qCO:qx2002"
        elif key_upper in ("KBO", "CRN"):
            return "eba_qCO:qx2003"
        elif key_upper == "VAT":
            return "eba_qCO:qx2004"
        elif key_upper in ("PNR", "NIN"):
            return "eba_qCO:qx2005"
        else:
            return "eba_qCO:qx2001"

    # Try priority identifiers first
    for id_type in priority:
        if id_type in entity.legal_identifiers and entity.legal_identifiers[id_type]:
            return (
                entity.legal_identifiers[id_type],
                map_identifier_type(id_type),
                id_type,
            )

    # Use first available identifier if we couldn't find any of the priority ones
    for key, value in entity.legal_identifiers.items():
        if value:
            return value, map_identifier_type(key), key

    return "", "", ""


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

        # Format dates, use 9999-12-31 as default for mandatory fields
        last_update = (
            format_date(entity.updated_at) if entity.updated_at else "9999-12-31"
        )
        integration_date = (
            format_date(entity.created_at) if entity.created_at else "9999-12-31"
        )
        deletion_date = "9999-12-31"  # Empty for active entities

        # LEI of parent entity
        parent_entity_lei = ""
        if entity.parent_entity and entity.parent_entity.legal_identifiers:
            parent_entity_lei = entity.parent_entity.legal_identifiers.get("LEI", "")

        if not parent_entity_lei:
            # If no parent or parent has no LEI, use entity's own LEI for c0060 as per EBA rules
            parent_entity_lei = lei

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
        # c0010: Identification code of the branch (typed dimension eba_typ:IS — use "0" if empty)
        branch_code, _, _ = get_entity_identifier(branch)
        branch_code = branch_code or "0"

        # c0020: LEI of the financial entity head office (typed dimension eba_typ:LE — use "0" if empty)
        head_office_lei = ""
        if branch.parent_entity:
            head_office_lei, _, _ = get_entity_identifier(
                branch.parent_entity, priority=["LEI"]
            )
        head_office_lei = head_office_lei or "0"

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

    Includes all contracts — RT.02.01 is the parent table referenced by RT.02.03,
    RT.03.01–03.03, RT.04.01, RT.05.02, and RT.07.01 via foreign key.

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

    # RT.02.01 must include ALL contracts — other tabs reference it via FK (Rule 807)
    filtered_contracts = contracts.select_related("overarching_contract")

    # Write contract data
    for contract in filtered_contracts:
        # b_02.01.0010: Contractual arrangement reference number
        contract_ref = contract.ref_id or str(contract.id)

        # b_02.01.0020: Type of contractual arrangement
        arrangement_type = contract.dora_contractual_arrangement or ""

        # b_02.01.0030: Overarching contractual arrangement reference number
        # FAQ #124: c0030 is a FK and cannot be blank. When there is no
        # overarching contract, type "Not Applicable" (no dropdown exists).
        if contract.overarching_contract:
            overarching_ref = contract.overarching_contract.ref_id or str(
                contract.overarching_contract.id
            )
        else:
            overarching_ref = "Not Applicable"

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
    # Track written dimension keys to avoid XBRL duplicate fact errors.
    # The XBRL key for b_02.02 is (c0010, c0020, c0030, c0050, c0060, c0130, c0150, c0160).
    seen_keys = set()

    for contract in filtered_contracts:
        # Iterate through all solutions in this contract
        for solution in contract.solutions.all():
            # Get business functions associated with this solution (directly or through children)
            if business_function_asset_ids:
                business_functions = solution.assets.filter(
                    id__in=business_function_asset_ids, is_business_function=True
                )
            else:
                business_functions = solution.assets.filter(is_business_function=True)

            for function in business_functions:
                # c0010: Contract reference
                contract_ref = contract.ref_id or str(contract.id)

                # c0020: LEI of entity using the service (typed dimension eba_typ:LE — use "0" if empty)
                entity_lei = ""
                if contract.beneficiary_entity:
                    entity_lei, _, _ = get_entity_identifier(
                        contract.beneficiary_entity, priority=["LEI"]
                    )
                entity_lei = entity_lei or "0"

                # c0030, c0040: Provider identification
                # c0030 is typed dimension eba_typ:IS — use "0" if empty
                # c0040 is enumeration metric — keep empty when c0030 has no real value
                provider_code, provider_code_type = "", ""
                if contract.provider_entity:
                    provider_code, provider_code_type, _ = get_entity_identifier(
                        contract.provider_entity
                    )
                provider_code = provider_code or "0"

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
                    else "9999-12-31"
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
                provider_country = "eba_GA:qx2007"  # "Not applicable" — key field, cannot be empty (Rule 805)
                if contract.provider_entity and contract.provider_entity.country:
                    provider_country = f"eba_GA:{contract.provider_entity.country}"

                # c0140: Storage of data (Yes/No)
                storage_of_data = (
                    "eba_BT:x28" if solution.storage_of_data else "eba_BT:x29"
                )

                # c0150: Location of data at rest
                data_location_storage = (
                    "eba_GA:qx2007"  # Key field, cannot be empty (Rule 805)
                )
                if solution.data_location_storage:
                    data_location_storage = f"eba_GA:{solution.data_location_storage}"

                # c0160: Location of data processing
                data_location_processing = (
                    "eba_GA:qx2007"  # Key field, cannot be empty (Rule 805)
                )
                if solution.data_location_processing:
                    data_location_processing = (
                        f"eba_GA:{solution.data_location_processing}"
                    )

                # c0170: Data sensitiveness
                data_sensitiveness = solution.dora_data_sensitiveness or ""

                # c0180: Level of reliance
                reliance_level = solution.dora_reliance_level or ""

                key = (
                    contract_ref,
                    entity_lei,
                    provider_code,
                    function_id,
                    ict_service_type,
                    provider_country,
                    data_location_storage,
                    data_location_processing,
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)

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
    main_code, _, _ = get_entity_identifier(main_entity)

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

        # Get provider identifier (prioritize LEI)
        # c0020 is typed dimension eba_typ:IS — use "0" if empty
        # c0030 is enumeration metric — keep empty when c0020 has no real value
        provider_code, code_type, _ = get_entity_identifier(provider)
        provider_code = provider_code or "0"

        csv_writer.writerow([contract_ref, provider_code, code_type])

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

    # Get intra-group contracts
    intragroup_contracts = contracts.filter(is_intragroup=True).select_related(
        "provider_entity"
    )

    # Write provider data for each intra-group contract
    for contract in intragroup_contracts:
        contract_ref = contract.ref_id or str(contract.id)
        # c0020 is typed dimension eba_typ:LE — use "0" if empty
        provider_lei, _, _ = get_entity_identifier(
            contract.provider_entity, priority=["LEI"]
        )
        provider_lei = provider_lei or "0"
        csv_writer.writerow([contract_ref, provider_lei, "true"])

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

        # c0020: LEI of beneficiary entity (typed dimension eba_typ:LE — use "0" if empty)
        beneficiary_lei = ""
        if contract.beneficiary_entity:
            beneficiary_lei, _, _ = get_entity_identifier(
                contract.beneficiary_entity, priority=["LEI"]
            )
        beneficiary_lei = beneficiary_lei or "0"

        # Write row for beneficiary entity (not a branch)
        combination = (contract_ref, beneficiary_lei, "0")
        if combination not in written_combinations:
            # c0030: Nature of entity (not a branch)
            entity_nature = "eba_ZZ:x839"  # not a branch
            # c0040: Branch code (typed dimension eba_typ:IS — use "0" for non-branch)
            branch_code = "0"

            csv_writer.writerow(
                [contract_ref, beneficiary_lei, entity_nature, branch_code]
            )
            written_combinations.add(combination)

        # Write rows for branches of the beneficiary entity only
        for branch in branches:
            if branch.parent_entity_id != getattr(
                contract.beneficiary_entity, "id", None
            ):
                continue
            # c0040: Branch code (typed dimension eba_typ:IS — use "0" if empty)
            branch_code, _, _ = get_entity_identifier(branch)
            branch_code = branch_code or "0"
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

    # Write CSV headers (DORA 4.0 Layout)
    csv_writer.writerow(
        [
            "c0010",  # Identification code of ICT third-party service provider
            "c0020",  # Type of code to identify the ICT third-party service provider
            "c0030",  # Additional identification code of ICT third-party service provider
            "c0040",  # Type of additional identification code of the ICT third-party service provider
            "c0050",  # Legal name of the ICT third-party service provider
            "c0060",  # Name of the ICT third-party service provider in Latin alphabet
            "c0070",  # Type of person of the ICT third-party service provider
            "c0080",  # Country of the ICT third-party service provider’s headquarters
            "c0090",  # Currency of the amount reported in RT.05.01.0070
            "c0100",  # Total annual expense or estimated cost of the ICT third-party service provider
            "c0110",  # Identification code of the ICT third-party service provider’s ultimate parent undertaking
            "c0120",  # Type of code to identify the ICT third-party service provider’s ultimate parent undertaking
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
        # c0010 is typed dimension eba_typ:IS — use "0" if empty
        # c0020 is enumeration metric — keep empty when c0010 has no real value
        provider_code, code_type, _ = get_entity_identifier(provider)
        provider_code = provider_code or "0"

        # c0050: Provider legal name
        provider_name = provider.name

        # c0070: Type of person
        person_type = provider.dora_provider_person_type or ""

        # c0080: Country with eba_GA prefix
        country = ""
        if provider.country:
            country = f"eba_GA:{provider.country}"

        # c0090: Currency with eba_CU prefix
        currency = ""
        if data["currency"]:
            currency = f"eba_CU:{data['currency']}"

        # c0100: Total annual expense
        total_expense = data["total_expense"]

        # c0110, c0120: Ultimate parent undertaking identifier (prioritize LEI)
        # FK constraint: c0110 must reference a valid c0010 in B_05.01
        # If no parent, self-reference the provider (it IS its own ultimate parent)
        parent_code, parent_code_type = "", ""
        ultimate_parent = get_ultimate_parent(provider)
        if ultimate_parent:
            parent_code, parent_code_type, _ = get_entity_identifier(ultimate_parent)
        if not parent_code:
            parent_code = provider_code
            parent_code_type = code_type

        # Write provider detail row (12 columns for DORA 4.0)
        csv_writer.writerow(
            [
                provider_code,  # c0010
                code_type,  # c0020
                "0",  # c0030: Additional identification code (typed dimension eba_typ:IS — "0" = not applicable)
                "",  # c0040: Type of additional identification code (enumeration metric — empty)
                provider_name,  # c0050
                provider_name,  # c0060: Name in Latin alphabet TODO: add Entity.latin_name DB column, equals Entity.name by default, to be displayed in EntityForm if name contains non-Latin characters
                person_type,  # c0070
                country,  # c0080
                currency,  # c0090
                total_expense,  # c0100
                parent_code,  # c0110
                parent_code_type,  # c0120
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
            "c0050",  # Rank in supply chain
            "c0060",  # Recipient code
            "c0070",  # Recipient code type
        ]
    )

    # Get contracts with both provider and solutions
    # NOTE: intragroup providers ARE included per EBA FAQ #70, #82, #84
    supply_chain_contracts = (
        contracts.filter(
            provider_entity__isnull=False,
            solutions__isnull=False,
        )
        .select_related("provider_entity", "beneficiary_entity")
        .prefetch_related("solutions__provider_entity")
    )

    # Write supply chain data
    # Track written dimension keys to avoid XBRL duplicate fact errors.
    # The XBRL key for b_05.02 is (contract_ref, ict_service_type, provider_code, rank, recipient_code).
    seen_keys = set()

    for contract in supply_chain_contracts:
        for solution in contract.solutions.all():
            contract_ref = contract.ref_id or str(contract.id)
            ict_service_type = solution.dora_ict_service_type
            if not ict_service_type:
                continue

            # Build supply chain from solution's provider
            chain = get_provider_chain(solution.provider_entity)

            for rank, provider in enumerate(chain, start=1):
                # c0030 is typed dimension eba_typ:IS — use "0" if empty
                # c0040 is enumeration metric — keep empty when c0030 has no real value
                provider_code, provider_code_type, _ = get_entity_identifier(provider)
                provider_code = provider_code or "0"

                # c0060/c0070: recipient = previous entity in chain (the one that sub-contracted)
                # CHECK_C0050: when rank=1, recipient must equal provider (direct service relationship)
                # When rank>1, recipient is the previous entity in the chain
                if rank == 1:
                    recipient_code, recipient_code_type = (
                        provider_code,
                        provider_code_type,
                    )
                else:
                    recipient = chain[rank - 2]
                    recipient_code, recipient_code_type, _ = get_entity_identifier(
                        recipient
                    )
                    recipient_code = recipient_code or "0"

                key = (
                    contract_ref,
                    ict_service_type,
                    provider_code,
                    rank,
                    recipient_code,
                )
                if key in seen_keys:
                    continue
                seen_keys.add(key)

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
    main_lei, _, _ = get_entity_identifier(main_entity, priority=["LEI"])

    # Write function data
    for function in business_functions:
        function_id = function.ref_id or str(function.id)
        licensed_activity = function.dora_licenced_activity or ""
        function_name = function.name
        entity_lei = main_lei
        criticality = function.dora_criticality_assessment or ""
        criticality_reasons = function.dora_criticality_justification or ""
        last_assessment_date = (
            format_date(function.updated_at) if function.updated_at else "9999-12-31"
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
    # NOTE: intragroup providers ARE included per EBA FAQ #70, #82, #84
    assessment_contracts = (
        contracts.filter(
            provider_entity__isnull=False,
            solutions__isnull=False,
        )
        .select_related("provider_entity")
        .prefetch_related("solutions")
    )

    # Write assessment data
    # Track written dimension keys to avoid XBRL duplicate fact errors.
    # The XBRL key for b_07.01 is (contract_ref, provider_code, ict_service_type).
    seen_keys = set()

    for contract in assessment_contracts:
        # Iterate through all solutions in this contract
        for solution in contract.solutions.all():
            contract_ref = contract.ref_id or str(contract.id)

            # c0020 is typed dimension eba_typ:IS — use "0" if empty
            # c0030 is enumeration metric — keep empty when c0020 has no real value
            provider_code, provider_code_type, _ = get_entity_identifier(
                contract.provider_entity
            )
            provider_code = provider_code or "0"

            ict_service_type = solution.dora_ict_service_type or ""

            key = (contract_ref, provider_code, ict_service_type)
            if key in seen_keys:
                continue
            seen_keys.add(key)

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
    Generate b_99.01.csv - Definitions from Entities making use of ICT Services.

    Single-row aggregation table with counts of contracts, solutions and business
    functions grouped by their DORA classification attributes.

    Args:
        zip_file: ZIP file object to write to
        contracts: QuerySet of Contract objects with solutions
        business_functions: QuerySet of Asset objects with is_business_function=True
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    csv_writer.writerow(
        [
            "c0010",  # Contracts: services (eba_CO:x1)
            "c0020",  # Contracts: goods (eba_CO:x2)
            "c0030",  # Contracts: goods and services (eba_CO:x3)
            "c0040",  # Data sensitiveness: normal (eba_ZZ:x791)
            "c0050",  # Data sensitiveness: sensitive (eba_ZZ:x792)
            "c0060",  # Data sensitiveness: highly sensitive (eba_ZZ:x793)
            "c0070",  # Discontinuing impact (functions): low (eba_ZZ:x791)
            "c0080",  # Discontinuing impact (functions): medium (eba_ZZ:x792)
            "c0090",  # Discontinuing impact (functions): high (eba_ZZ:x793)
            "c0100",  # Substitutability: easily substitutable (eba_ZZ:x959)
            "c0110",  # Substitutability: substitutable (eba_ZZ:x960)
            "c0120",  # Substitutability: difficult to substitute (eba_ZZ:x961)
            "c0130",  # Substitutability: not substitutable (eba_ZZ:x962)
            "c0140",  # Reintegration: easy (eba_ZZ:x798)
            "c0150",  # Reintegration: difficult (eba_ZZ:x966)
            "c0160",  # Reintegration: not possible (eba_ZZ:x967)
            "c0170",  # Discontinuing impact (ICT services): low (eba_ZZ:x791)
            "c0180",  # Discontinuing impact (ICT services): medium (eba_ZZ:x792)
            "c0190",  # Discontinuing impact (ICT services): high (eba_ZZ:x793)
        ]
    )

    # c0010-c0030: Count contracts by type
    c0010 = contracts.filter(dora_contractual_arrangement="eba_CO:x1").count()
    c0020 = contracts.filter(dora_contractual_arrangement="eba_CO:x2").count()
    c0030 = contracts.filter(dora_contractual_arrangement="eba_CO:x3").count()

    # Get distinct solutions linked to these contracts
    solutions = Solution.objects.filter(contracts__in=contracts).distinct()

    # c0040-c0060: Data sensitiveness (solutions)
    c0040 = solutions.filter(dora_data_sensitiveness="eba_ZZ:x791").count()
    c0050 = solutions.filter(dora_data_sensitiveness="eba_ZZ:x792").count()
    c0060 = solutions.filter(dora_data_sensitiveness="eba_ZZ:x793").count()

    # c0070-c0090: Impact of discontinuing function (business functions)
    c0070 = business_functions.filter(dora_discontinuing_impact="eba_ZZ:x791").count()
    c0080 = business_functions.filter(dora_discontinuing_impact="eba_ZZ:x792").count()
    c0090 = business_functions.filter(dora_discontinuing_impact="eba_ZZ:x793").count()

    # c0100-c0130: Substitutability (solutions)
    c0100 = solutions.filter(dora_substitutability="eba_ZZ:x959").count()
    c0110 = solutions.filter(dora_substitutability="eba_ZZ:x960").count()
    c0120 = solutions.filter(dora_substitutability="eba_ZZ:x961").count()
    c0130 = solutions.filter(dora_substitutability="eba_ZZ:x962").count()

    # c0140-c0160: Reintegration possibility (solutions)
    c0140 = solutions.filter(dora_reintegration_possibility="eba_ZZ:x798").count()
    c0150 = solutions.filter(dora_reintegration_possibility="eba_ZZ:x966").count()
    c0160 = solutions.filter(dora_reintegration_possibility="eba_ZZ:x967").count()

    # c0170-c0190: Impact of discontinuing ICT services (solutions)
    c0170 = solutions.filter(dora_discontinuing_impact="eba_ZZ:x791").count()
    c0180 = solutions.filter(dora_discontinuing_impact="eba_ZZ:x792").count()
    c0190 = solutions.filter(dora_discontinuing_impact="eba_ZZ:x793").count()

    csv_writer.writerow(
        [
            c0010,
            c0020,
            c0030,
            c0040,
            c0050,
            c0060,
            c0070,
            c0080,
            c0090,
            c0100,
            c0110,
            c0120,
            c0130,
            c0140,
            c0150,
            c0160,
            c0170,
            c0180,
            c0190,
        ]
    )

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


def _compute_ref_period() -> str:
    """Compute the DORA RoI reference period based on the current year.

    Per EBA Q&A 2025_7387:
    - 2025 reporting: 2025-03-31
    - 2026+ reporting: December 31 of the preceding year
    """
    current_year = date.today().year
    if current_year <= 2025:
        return "2025-03-31"
    return f"{current_year - 1}-12-31"


def generate_parameters(
    zip_file, main_entity: Entity, folder_prefix: str = "", entity_id: str = ""
) -> None:
    """
    Generate parameters.csv - Report metadata and configuration parameters.

    This file contains key metadata about the DORA ROI report including entity
    identification, reporting period, base currency, and decimal formatting rules.

    Args:
        zip_file: ZIP file object to write to
        main_entity: The main builtin entity
        folder_prefix: Optional folder prefix to prepend to file path
        entity_id: The identifier for the report (optional, will be computed if not provided)
    """
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write CSV headers
    csv_writer.writerow(["name", "value"])

    # If entityID not provided, compute it (default to IND)
    if not entity_id:
        code, _, key_name = get_entity_identifier(main_entity)
        if not code:
            raise ValueError(
                "Cannot generate DORA RoI export: main entity has no legal identifier. "
                "The entityID parameter requires a valid identifier (EBA Filing Rules v5.5). "
                "Please set a legal identifier in the main entity before exporting."
            )
        entity_id = f"rs:{code}.IND"

    # Get currency for baseCurrency
    base_currency = (
        f"iso4217:{main_entity.currency}" if main_entity.currency else "iso4217:EUR"
    )

    # Write parameters (7 parameters per OneGate XBRL Protocol v1.2, section 3.2)
    parameters = [
        ("entityID", entity_id),
        ("refPeriod", _compute_ref_period()),
        ("baseCurrency", base_currency),
        ("decimalsInteger", "0"),
        ("decimalsMonetary", "-3"),
        ("decimalsPercentage", "4"),
        ("decimalsDecimal", "2"),
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
