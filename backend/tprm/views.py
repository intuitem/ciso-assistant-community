from rest_framework.response import Response
from iam.models import Folder, RoleAssignment, UserGroup
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from core.models import Asset
from tprm.models import Entity, Representative, Solution, EntityAssessment, Contract
from rest_framework.decorators import action
import structlog

from rest_framework.request import Request
from rest_framework.response import Response

from django.utils.formats import date_format
from django.http import HttpResponse
from django.db.models import Sum

from core.constants import COUNTRY_CHOICES, CURRENCY_CHOICES
from core.dora import (
    DORA_ENTITY_TYPE_CHOICES,
    DORA_ENTITY_HIERARCHY_CHOICES,
    DORA_CONTRACTUAL_ARRANGEMENT_CHOICES,
    TERMINATION_REASON_CHOICES,
    DORA_ICT_SERVICE_CHOICES,
    DORA_SENSITIVENESS_CHOICES,
    DORA_RELIANCE_CHOICES,
    DORA_PROVIDER_PERSON_TYPE_CHOICES,
    DORA_SUBSTITUTABILITY_CHOICES,
    DORA_NON_SUBSTITUTABILITY_REASON_CHOICES,
    DORA_BINARY_CHOICES,
    DORA_REINTEGRATION_POSSIBILITY_CHOICES,
    DORA_DISCONTINUING_IMPACT_CHOICES,
)

import csv
import io
import zipfile
from datetime import datetime

logger = structlog.get_logger(__name__)


class BaseModelViewSet(AbstractBaseModelViewSet):
    serializers_module = "tprm.serializers"


# Create your views here.
class EntityViewSet(BaseModelViewSet):
    """
    API endpoint that allows entities to be viewed or edited.
    """

    model = Entity
    filterset_fields = [
        "name",
        "folder",
        "parent_entity",
        "relationship",
        "relationship__name",
        "contracts",
        "country",
        "currency",
        "dora_entity_type",
        "dora_entity_hierarchy",
        "dora_competent_authority",
    ]

    @action(detail=False, methods=["get"], name="Generate DORA ROI")
    def generate_dora_roi(self, request):
        """
        Generate DORA Register of Information (ROI) as a zip file containing CSV data.
        """
        # Get the main entity
        main_entity = Entity.get_main_entity()

        if not main_entity:
            return HttpResponse("No main entity found", status=400)

        # Create zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Create b_01.01.csv - Main entity information
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

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_01.01.csv", csv_buffer.getvalue().encode("utf-8")
            )

            # Create b_01.02.csv - Entity register
            csv_buffer_02 = io.StringIO()
            csv_writer_02 = csv.writer(csv_buffer_02)

            # Write CSV headers
            csv_writer_02.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                    "c0040",
                    "c0050",
                    "c0060",
                    "c0070",
                    "c0080",
                    "c0090",
                    "c0100",
                    "c0110",
                ]
            )

            # Get all entities to include in register (main entity + branches)
            entities_to_export = [main_entity] + list(
                Entity.objects.filter(parent_entity=main_entity)
            )

            # Write entity data for each entity
            for entity in entities_to_export:
                lei_02 = ""
                if entity.legal_identifiers:
                    lei_02 = entity.legal_identifiers.get("LEI", "")

                country_02 = ""
                if entity.country:
                    country_02 = f"eba_GA:{entity.country}"

                # Format currency with eba_CU: prefix
                currency_02 = ""
                if entity.currency:
                    currency_02 = f"eba_CU:{entity.currency}"

                # Format dates, use 2999-12-31 as default for mandatory fields
                last_update = (
                    entity.updated_at.strftime("%Y-%m-%d")
                    if entity.updated_at
                    else "2999-12-31"
                )
                integration_date = (
                    entity.created_at.strftime("%Y-%m-%d")
                    if entity.created_at
                    else "2999-12-31"
                )
                deletion_date = (
                    "2999-12-31"  # Empty for active entities, use far future date
                )

                # LEI of parent entity
                parent_entity_lei = ""
                if entity.parent_entity and entity.parent_entity.legal_identifiers:
                    parent_entity_lei = entity.parent_entity.legal_identifiers.get(
                        "LEI", ""
                    )

                csv_writer_02.writerow(
                    [
                        lei_02,
                        entity.name,
                        country_02,
                        entity.dora_entity_type or "",
                        entity.dora_entity_hierarchy or "",
                        parent_entity_lei,
                        last_update,
                        integration_date,
                        deletion_date,
                        currency_02,
                        entity.dora_assets_value
                        if entity.dora_assets_value is not None
                        else "",
                    ]
                )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_01.02.csv", csv_buffer_02.getvalue().encode("utf-8")
            )

            # Create b_01.03.csv - Branches register
            csv_buffer_03 = io.StringIO()
            csv_writer_03 = csv.writer(csv_buffer_03)

            # Write CSV headers
            csv_writer_03.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                    "c0040",
                ]
            )

            # Get main entity LEI for parent reference
            main_entity_lei = ""
            if main_entity.legal_identifiers:
                main_entity_lei = main_entity.legal_identifiers.get("LEI", "")

            # Query all branches (entities with parent_entity = main_entity)
            branches = Entity.objects.filter(parent_entity=main_entity)

            # Write branch data
            for branch in branches:
                # Branch identification code (LEI)
                branch_lei = ""
                if branch.legal_identifiers:
                    branch_lei = branch.legal_identifiers.get("LEI", "")

                # Parent entity LEI (main entity)
                parent_lei = main_entity_lei

                # Branch name
                branch_name = branch.name

                # Branch country with eba_GA: prefix
                branch_country = ""
                if branch.country:
                    branch_country = f"eba_GA:{branch.country}"

                csv_writer_03.writerow(
                    [
                        branch_lei,
                        parent_lei,
                        branch_name,
                        branch_country,
                    ]
                )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_01.03.csv", csv_buffer_03.getvalue().encode("utf-8")
            )

            # Create b_02.01.csv - Contractual arrangements register
            csv_buffer_0201 = io.StringIO()
            csv_writer_0201 = csv.writer(csv_buffer_0201)

            # Write CSV headers
            csv_writer_0201.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                    "c0040",
                    "c0050",
                ]
            )

            # Get viewable contracts for the current user
            (viewable_contracts, _, _) = RoleAssignment.get_accessible_object_ids(
                folder=Folder.get_root_folder(),
                user=request.user,
                object_type=Contract,
            )

            # Write contract data
            for contract in Contract.objects.filter(
                id__in=viewable_contracts
            ).select_related("overarching_contract"):
                # Contract reference number
                contract_ref = contract.ref_id or str(contract.id)

                # Type of contractual arrangement
                arrangement_type = contract.dora_contractual_arrangement or ""

                # Overarching contract reference
                overarching_ref = ""
                if contract.overarching_contract:
                    overarching_ref = contract.overarching_contract.ref_id or str(
                        contract.overarching_contract.id
                    )

                # Currency with eba_CU: prefix
                currency_contract = ""
                if contract.currency:
                    currency_contract = f"eba_CU:{contract.currency}"

                # Annual expense
                annual_expense = (
                    contract.annual_expense
                    if contract.annual_expense is not None
                    else ""
                )

                csv_writer_0201.writerow(
                    [
                        contract_ref,
                        arrangement_type,
                        overarching_ref,
                        currency_contract,
                        annual_expense,
                    ]
                )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_02.01.csv", csv_buffer_0201.getvalue().encode("utf-8")
            )

            # Create b_02.02.csv - Contractual arrangements details
            csv_buffer_0202 = io.StringIO()
            csv_writer_0202 = csv.writer(csv_buffer_0202)

            # Write CSV headers
            csv_writer_0202.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                    "c0040",
                    "c0050",
                    "c0060",
                    "c0070",
                    "c0080",
                    "c0090",
                    "c0100",
                    "c0110",
                    "c0120",
                    "c0130",
                    "c0140",
                    "c0150",
                    "c0160",
                    "c0170",
                    "c0180",
                ]
            )

            # Get main entity LEI
            main_entity_lei = ""
            if main_entity.legal_identifiers:
                main_entity_lei = main_entity.legal_identifiers.get("LEI", "")

            # Write contract-solution relationship data
            for contract in Contract.objects.filter(
                id__in=viewable_contracts
            ).select_related("solution__provider_entity"):
                # For the solution in the contract
                solution = contract.solution
                if solution:
                    # Contract reference number
                    contract_ref = contract.ref_id or str(contract.id)

                    # Provider entity LEI
                    provider_lei = ""
                    provider_country = ""
                    if solution.provider_entity:
                        if solution.provider_entity.legal_identifiers:
                            provider_lei = (
                                solution.provider_entity.legal_identifiers.get(
                                    "LEI", ""
                                )
                            )
                        if solution.provider_entity.country:
                            provider_country = (
                                f"eba_GA:{solution.provider_entity.country}"
                            )

                    # Type of code (determine from legal identifiers)
                    code_type = "LEI" if provider_lei else ""

                    # Function identifier - using criticality as placeholder
                    function_id = ""

                    # ICT service type
                    ict_service_type = solution.dora_ict_service_type or ""

                    # Dates
                    start_date = (
                        contract.start_date.strftime("%Y-%m-%d")
                        if contract.start_date
                        else "2999-12-31"
                    )
                    end_date = (
                        contract.end_date.strftime("%Y-%m-%d")
                        if contract.end_date
                        else "2999-12-31"
                    )

                    # Termination reason
                    termination_reason = contract.termination_reason or ""

                    # Notice periods
                    notice_period_entity = (
                        contract.notice_period_entity
                        if contract.notice_period_entity is not None
                        else ""
                    )
                    notice_period_provider = (
                        contract.notice_period_provider
                        if contract.notice_period_provider is not None
                        else ""
                    )

                    # Governing law country
                    governing_law = ""
                    if contract.governing_law_country:
                        governing_law = f"eba_GA:{contract.governing_law_country}"

                    # Data storage and processing from solution
                    storage_of_data = (
                        "eba_BT:x28" if solution.storage_of_data else "eba_BT:x29"
                    )

                    data_location_storage = ""
                    if solution.data_location_storage:
                        data_location_storage = (
                            f"eba_GA:{solution.data_location_storage}"
                        )

                    data_location_processing = ""
                    if solution.data_location_processing:
                        data_location_processing = (
                            f"eba_GA:{solution.data_location_processing}"
                        )

                    data_sensitiveness = solution.dora_data_sensitiveness or ""
                    reliance_level = solution.dora_reliance_level or ""

                    csv_writer_0202.writerow(
                        [
                            contract_ref,
                            main_entity_lei,
                            provider_lei,
                            code_type,
                            function_id,
                            ict_service_type,
                            start_date,
                            end_date,
                            termination_reason,
                            notice_period_entity,
                            notice_period_provider,
                            governing_law,
                            provider_country,
                            storage_of_data,
                            data_location_storage,
                            data_location_processing,
                            data_sensitiveness,
                            reliance_level,
                        ]
                    )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_02.02.csv", csv_buffer_0202.getvalue().encode("utf-8")
            )

            # Create b_02.03.csv - List of intra-group contractual arrangements
            csv_buffer_0203 = io.StringIO()
            csv_writer_0203 = csv.writer(csv_buffer_0203)

            # Write CSV headers
            csv_writer_0203.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                ]
            )

            # Query intra-group contracts that have an overarching contract
            # Only include contracts the user has access to
            intragroup_contracts = Contract.objects.filter(
                id__in=viewable_contracts,
                is_intragroup=True,
                overarching_contract__isnull=False,
            ).select_related("overarching_contract")

            # Write intra-group contract relationships
            for contract in intragroup_contracts:
                # Subordinate contract reference
                subordinate_ref = contract.ref_id or str(contract.id)

                # Overarching contract reference
                overarching_ref = ""
                if contract.overarching_contract:
                    overarching_ref = contract.overarching_contract.ref_id or str(
                        contract.overarching_contract.id
                    )

                # Link indicator (always "true" for populated rows)
                link_indicator = "true"

                csv_writer_0203.writerow(
                    [
                        subordinate_ref,
                        overarching_ref,
                        link_indicator,
                    ]
                )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_02.03.csv", csv_buffer_0203.getvalue().encode("utf-8")
            )

            # Create b_03.01.csv - Entities signing the contractual arrangements
            csv_buffer_0301 = io.StringIO()
            csv_writer_0301 = csv.writer(csv_buffer_0301)

            # Write CSV headers
            csv_writer_0301.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                ]
            )

            # Get main entity LEI for signing entity
            main_entity_lei = ""
            if main_entity.legal_identifiers:
                main_entity_lei = main_entity.legal_identifiers.get("LEI", "")

            # Write contract-signing entity relationships
            # For each contract, the main entity is the signing entity
            for contract in Contract.objects.filter(id__in=viewable_contracts):
                # Contract reference number
                contract_ref = contract.ref_id or str(contract.id)

                # LEI of the signing entity (main entity)
                signing_entity_lei = main_entity_lei

                # Link indicator (always "true" for populated rows)
                link_indicator = "true"

                csv_writer_0301.writerow(
                    [
                        contract_ref,
                        signing_entity_lei,
                        link_indicator,
                    ]
                )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_03.01.csv", csv_buffer_0301.getvalue().encode("utf-8")
            )

            # Create b_03.02.csv - ICT third-party service providers signing the contractual arrangements
            csv_buffer_0302 = io.StringIO()
            csv_writer_0302 = csv.writer(csv_buffer_0302)

            # Write CSV headers
            csv_writer_0302.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                    "c0045",
                ]
            )

            # Write contract-provider relationships
            for contract in Contract.objects.filter(
                id__in=viewable_contracts
            ).select_related("provider_entity"):
                # Contract reference number
                contract_ref = contract.ref_id or str(contract.id)

                # Get provider entity
                provider = contract.provider_entity
                if provider:
                    # Extract identification code from legal_identifiers
                    # Priority order: LEI, EUID, VAT, DUNS, others
                    provider_code = ""
                    code_type = ""

                    if provider.legal_identifiers:
                        # Try to get LEI first (preferred for DORA)
                        if (
                            "LEI" in provider.legal_identifiers
                            and provider.legal_identifiers["LEI"]
                        ):
                            provider_code = provider.legal_identifiers["LEI"]
                            code_type = "LEI"
                        # Then try other identifiers
                        elif (
                            "EUID" in provider.legal_identifiers
                            and provider.legal_identifiers["EUID"]
                        ):
                            provider_code = provider.legal_identifiers["EUID"]
                            code_type = "EUID"
                        elif (
                            "VAT" in provider.legal_identifiers
                            and provider.legal_identifiers["VAT"]
                        ):
                            provider_code = provider.legal_identifiers["VAT"]
                            code_type = "VAT"
                        elif (
                            "DUNS" in provider.legal_identifiers
                            and provider.legal_identifiers["DUNS"]
                        ):
                            provider_code = provider.legal_identifiers["DUNS"]
                            code_type = "DUNS"
                        else:
                            # Use first available identifier
                            for key, value in provider.legal_identifiers.items():
                                if value:
                                    provider_code = value
                                    code_type = key
                                    break

                    # Link indicator (always "true" for populated rows)
                    link_indicator = "true"

                    csv_writer_0302.writerow(
                        [
                            contract_ref,
                            provider_code,
                            code_type,
                            link_indicator,
                        ]
                    )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_03.02.csv", csv_buffer_0302.getvalue().encode("utf-8")
            )

            # Create b_03.03.csv - Entities signing the contractual arrangements for providing ICT services within the group
            csv_buffer_0303 = io.StringIO()
            csv_writer_0303 = csv.writer(csv_buffer_0303)

            # Write CSV headers
            csv_writer_0303.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0031",
                ]
            )

            # Get main entity LEI for intra-group provider
            main_entity_lei = ""
            if main_entity.legal_identifiers:
                main_entity_lei = main_entity.legal_identifiers.get("LEI", "")

            # Write intra-group contract-provider relationships
            # Focus on contracts where main entity provides services to other entities in the group
            for contract in Contract.objects.filter(
                id__in=viewable_contracts, is_intragroup=True
            ):
                # Contract reference number
                contract_ref = contract.ref_id or str(contract.id)

                # LEI of the entity providing services (main entity)
                provider_lei = main_entity_lei

                # Link indicator (always "true" for populated rows)
                link_indicator = "true"

                csv_writer_0303.writerow(
                    [
                        contract_ref,
                        provider_lei,
                        link_indicator,
                    ]
                )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_03.03.csv", csv_buffer_0303.getvalue().encode("utf-8")
            )

            # Create b_04.01.csv - Entities making use of the ICT services
            csv_buffer_0401 = io.StringIO()
            csv_writer_0401 = csv.writer(csv_buffer_0401)

            # Write CSV headers
            csv_writer_0401.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                    "c0040",
                ]
            )

            # Get all entities (main entity + branches)
            entities_using_services = [main_entity] + list(
                Entity.objects.filter(parent_entity=main_entity)
            )

            # For each contract, list the main entity and its branches as users
            for contract in Contract.objects.filter(id__in=viewable_contracts):
                contract_ref = contract.ref_id or str(contract.id)

                # For each entity in the group (main entity + branches)
                for entity in entities_using_services:
                    # LEI of the entity using the service
                    entity_lei = ""
                    if entity.legal_identifiers:
                        entity_lei = entity.legal_identifiers.get("LEI", "")

                    # Nature of the entity (DORA entity type)
                    entity_nature = entity.dora_entity_type or ""

                    # Branch identification code
                    # Empty for main entity, branch LEI for branches
                    branch_code = ""
                    if entity.parent_entity:  # This is a branch
                        if entity.legal_identifiers:
                            branch_code = entity.legal_identifiers.get("LEI", "")

                    csv_writer_0401.writerow(
                        [
                            contract_ref,
                            entity_lei,
                            entity_nature,
                            branch_code,
                        ]
                    )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_04.01.csv", csv_buffer_0401.getvalue().encode("utf-8")
            )

            # Create b_05.01.csv - ICT third-party service providers
            csv_buffer_0501 = io.StringIO()
            csv_writer_0501 = csv.writer(csv_buffer_0501)

            # Write CSV headers
            csv_writer_0501.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                    "c0040",
                    "c0050",
                    "c0060",
                    "c0070",
                    "c0080",
                    "c0090",
                ]
            )

            # Get unique third-party providers from contracts (excluding intragroup)
            # Group by provider and calculate total expenses
            third_party_contracts = Contract.objects.filter(
                id__in=viewable_contracts,
                is_intragroup=False,
                provider_entity__isnull=False,
            ).select_related("provider_entity", "provider_entity__parent_entity")

            # Aggregate expenses by provider
            providers_data = {}
            for contract in third_party_contracts:
                provider = contract.provider_entity
                provider_id = provider.id

                if provider_id not in providers_data:
                    providers_data[provider_id] = {
                        "provider": provider,
                        "total_expense": 0,
                        "currency": contract.currency or main_entity.currency or "",
                    }

                # Add annual expense if available
                if contract.annual_expense:
                    providers_data[provider_id]["total_expense"] += (
                        contract.annual_expense
                    )

            # Write provider data
            for provider_id, data in providers_data.items():
                provider = data["provider"]

                # c0010: Identification code of provider
                # c0020: Type of code
                provider_code = ""
                code_type = ""

                if provider.legal_identifiers:
                    # Priority: LEI, EUID, VAT, DUNS, others
                    if (
                        "LEI" in provider.legal_identifiers
                        and provider.legal_identifiers["LEI"]
                    ):
                        provider_code = provider.legal_identifiers["LEI"]
                        code_type = "LEI"
                    elif (
                        "EUID" in provider.legal_identifiers
                        and provider.legal_identifiers["EUID"]
                    ):
                        provider_code = provider.legal_identifiers["EUID"]
                        code_type = "EUID"
                    elif (
                        "VAT" in provider.legal_identifiers
                        and provider.legal_identifiers["VAT"]
                    ):
                        provider_code = provider.legal_identifiers["VAT"]
                        code_type = "VAT"
                    elif (
                        "DUNS" in provider.legal_identifiers
                        and provider.legal_identifiers["DUNS"]
                    ):
                        provider_code = provider.legal_identifiers["DUNS"]
                        code_type = "DUNS"
                    else:
                        # Use first available identifier
                        for key, value in provider.legal_identifiers.items():
                            if value:
                                provider_code = value
                                code_type = key
                                break

                # c0030: Name of provider
                provider_name = provider.name

                # c0040: Type of person (DORA provider person type)
                type_of_person = provider.dora_provider_person_type or ""

                # c0050: Country of headquarters
                provider_country = ""
                if provider.country:
                    provider_country = f"eba_GA:{provider.country}"

                # c0060: Currency
                currency = ""
                if data["currency"]:
                    currency = f"eba_CU:{data['currency']}"

                # c0070: Total annual expense
                total_expense = data["total_expense"] if data["total_expense"] else ""

                # c0080: Ultimate parent undertaking identification code
                # c0090: Type of code for parent
                parent_code = ""
                parent_code_type = ""

                if provider.parent_entity:
                    if provider.parent_entity.legal_identifiers:
                        # Same priority as provider code
                        if (
                            "LEI" in provider.parent_entity.legal_identifiers
                            and provider.parent_entity.legal_identifiers["LEI"]
                        ):
                            parent_code = provider.parent_entity.legal_identifiers[
                                "LEI"
                            ]
                            parent_code_type = "LEI"
                        elif (
                            "EUID" in provider.parent_entity.legal_identifiers
                            and provider.parent_entity.legal_identifiers["EUID"]
                        ):
                            parent_code = provider.parent_entity.legal_identifiers[
                                "EUID"
                            ]
                            parent_code_type = "EUID"
                        elif (
                            "VAT" in provider.parent_entity.legal_identifiers
                            and provider.parent_entity.legal_identifiers["VAT"]
                        ):
                            parent_code = provider.parent_entity.legal_identifiers[
                                "VAT"
                            ]
                            parent_code_type = "VAT"
                        elif (
                            "DUNS" in provider.parent_entity.legal_identifiers
                            and provider.parent_entity.legal_identifiers["DUNS"]
                        ):
                            parent_code = provider.parent_entity.legal_identifiers[
                                "DUNS"
                            ]
                            parent_code_type = "DUNS"
                        else:
                            # Use first available identifier
                            for (
                                key,
                                value,
                            ) in provider.parent_entity.legal_identifiers.items():
                                if value:
                                    parent_code = value
                                    parent_code_type = key
                                    break

                csv_writer_0501.writerow(
                    [
                        provider_code,
                        code_type,
                        provider_name,
                        type_of_person,
                        provider_country,
                        currency,
                        total_expense,
                        parent_code,
                        parent_code_type,
                    ]
                )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_05.01.csv", csv_buffer_0501.getvalue().encode("utf-8")
            )

            # Create b_05.02.csv - ICT service supply chains
            csv_buffer_0502 = io.StringIO()
            csv_writer_0502 = csv.writer(csv_buffer_0502)

            # Write CSV headers
            csv_writer_0502.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                    "c0040",
                    "c0050",
                    "c0060",
                    "c0070",
                ]
            )

            # Get main entity LEI for recipient
            main_entity_lei = ""
            main_entity_code_type = ""
            if main_entity.legal_identifiers:
                # Get main entity identifier with priority: LEI, EUID, VAT, DUNS
                if (
                    "LEI" in main_entity.legal_identifiers
                    and main_entity.legal_identifiers["LEI"]
                ):
                    main_entity_lei = main_entity.legal_identifiers["LEI"]
                    main_entity_code_type = "LEI"
                elif (
                    "EUID" in main_entity.legal_identifiers
                    and main_entity.legal_identifiers["EUID"]
                ):
                    main_entity_lei = main_entity.legal_identifiers["EUID"]
                    main_entity_code_type = "EUID"
                elif (
                    "VAT" in main_entity.legal_identifiers
                    and main_entity.legal_identifiers["VAT"]
                ):
                    main_entity_lei = main_entity.legal_identifiers["VAT"]
                    main_entity_code_type = "VAT"
                elif (
                    "DUNS" in main_entity.legal_identifiers
                    and main_entity.legal_identifiers["DUNS"]
                ):
                    main_entity_lei = main_entity.legal_identifiers["DUNS"]
                    main_entity_code_type = "DUNS"
                else:
                    # Use first available identifier
                    for key, value in main_entity.legal_identifiers.items():
                        if value:
                            main_entity_lei = value
                            main_entity_code_type = key
                            break

            # Write contract-solution-provider supply chain data
            for contract in Contract.objects.filter(
                id__in=viewable_contracts,
                is_intragroup=False,
                provider_entity__isnull=False,
                solution__isnull=False,
            ).select_related("provider_entity", "solution"):
                # c0010: Contract reference
                contract_ref = contract.ref_id or str(contract.id)

                # c0020: Type of ICT services
                ict_service_type = ""
                if contract.solution:
                    ict_service_type = contract.solution.dora_ict_service_type or ""

                # c0030: Provider identification code
                # c0040: Provider code type
                provider_code = ""
                provider_code_type = ""
                provider = contract.provider_entity
                if provider and provider.legal_identifiers:
                    # Priority: LEI, EUID, VAT, DUNS, others
                    if (
                        "LEI" in provider.legal_identifiers
                        and provider.legal_identifiers["LEI"]
                    ):
                        provider_code = provider.legal_identifiers["LEI"]
                        provider_code_type = "LEI"
                    elif (
                        "EUID" in provider.legal_identifiers
                        and provider.legal_identifiers["EUID"]
                    ):
                        provider_code = provider.legal_identifiers["EUID"]
                        provider_code_type = "EUID"
                    elif (
                        "VAT" in provider.legal_identifiers
                        and provider.legal_identifiers["VAT"]
                    ):
                        provider_code = provider.legal_identifiers["VAT"]
                        provider_code_type = "VAT"
                    elif (
                        "DUNS" in provider.legal_identifiers
                        and provider.legal_identifiers["DUNS"]
                    ):
                        provider_code = provider.legal_identifiers["DUNS"]
                        provider_code_type = "DUNS"
                    else:
                        # Use first available identifier
                        for key, value in provider.legal_identifiers.items():
                            if value:
                                provider_code = value
                                provider_code_type = key
                                break

                # c0050: Rank (criticality)
                rank = ""
                if contract.solution:
                    rank = (
                        contract.solution.criticality
                        if contract.solution.criticality
                        else ""
                    )

                # c0060: Recipient identification (main entity)
                recipient_code = main_entity_lei

                # c0070: Recipient code type
                recipient_code_type = main_entity_code_type

                csv_writer_0502.writerow(
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

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_05.02.csv", csv_buffer_0502.getvalue().encode("utf-8")
            )

            # Create b_06.01.csv - Critical or important functions register
            csv_buffer_0601 = io.StringIO()
            csv_writer_0601 = csv.writer(csv_buffer_0601)

            # Write CSV headers
            csv_writer_0601.writerow(
                [
                    "c0010",
                    "c0020",
                    "c0030",
                    "c0040",
                    "c0050",
                    "c0060",
                    "c0070",
                    "c0080",
                    "c0090",
                    "c0100",
                ]
            )

            # Get main entity LEI for function association
            main_entity_lei = ""
            if main_entity.legal_identifiers:
                main_entity_lei = main_entity.legal_identifiers.get("LEI", "")

            # Get viewable business functions for the current user
            (viewable_assets, _, _) = RoleAssignment.get_accessible_object_ids(
                folder=Folder.get_root_folder(),
                user=request.user,
                object_type=Asset,
            )

            # Query all business functions
            business_functions = Asset.objects.filter(
                id__in=viewable_assets, is_business_function=True
            )

            # Write function data
            for function in business_functions:
                # Function identifier
                function_id = function.ref_id or str(function.id)

                # Licensed activity
                licensed_activity = function.dora_licenced_activity or ""

                # Function name
                function_name = function.name

                # LEI of financial entity
                entity_lei = main_entity_lei

                # Criticality assessment
                criticality = function.dora_criticality_assessment or ""

                # Reasons for criticality
                criticality_reasons = function.dora_criticality_justification or ""

                # Date of last assessment
                last_assessment_date = (
                    function.updated_at.strftime("%Y-%m-%d")
                    if function.updated_at
                    else "2999-12-31"
                )

                # Recovery time objective (RTO) - extract from disaster_recovery_objectives JSON
                rto = ""
                if function.disaster_recovery_objectives:
                    objectives = function.disaster_recovery_objectives.get(
                        "objectives", {}
                    )
                    rto_obj = objectives.get("rto", {})
                    if rto_obj and "value" in rto_obj:
                        rto = rto_obj["value"]

                # Recovery point objective (RPO) - extract from disaster_recovery_objectives JSON
                rpo = ""
                if function.disaster_recovery_objectives:
                    objectives = function.disaster_recovery_objectives.get(
                        "objectives", {}
                    )
                    rpo_obj = objectives.get("rpo", {})
                    if rpo_obj and "value" in rpo_obj:
                        rpo = rpo_obj["value"]

                # Impact of discontinuing
                discontinuing_impact = function.dora_discontinuing_impact or ""

                csv_writer_0601.writerow(
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

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_06.01.csv", csv_buffer_0601.getvalue().encode("utf-8")
            )

            # Create b_07.01.csv - Assessment of ICT services
            csv_buffer_0701 = io.StringIO()
            csv_writer_0701 = csv.writer(csv_buffer_0701)

            # Write CSV headers
            csv_writer_0701.writerow(
                [
                    "c0010",  # Contract reference
                    "c0020",  # Provider ID code
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

            # Get contracts with both provider and solution for assessment
            for contract in Contract.objects.filter(
                id__in=viewable_contracts,
                is_intragroup=False,
                provider_entity__isnull=False,
                solution__isnull=False,
            ).select_related("provider_entity", "solution"):
                # c0010: Contract reference
                contract_ref = contract.ref_id or str(contract.id)

                # c0020: Provider identification code
                # c0030: Provider code type
                provider_code = ""
                provider_code_type = ""
                provider = contract.provider_entity
                if provider and provider.legal_identifiers:
                    # Priority: LEI, EUID, VAT, DUNS, others
                    if (
                        "LEI" in provider.legal_identifiers
                        and provider.legal_identifiers["LEI"]
                    ):
                        provider_code = provider.legal_identifiers["LEI"]
                        provider_code_type = "LEI"
                    elif (
                        "EUID" in provider.legal_identifiers
                        and provider.legal_identifiers["EUID"]
                    ):
                        provider_code = provider.legal_identifiers["EUID"]
                        provider_code_type = "EUID"
                    elif (
                        "VAT" in provider.legal_identifiers
                        and provider.legal_identifiers["VAT"]
                    ):
                        provider_code = provider.legal_identifiers["VAT"]
                        provider_code_type = "VAT"
                    elif (
                        "DUNS" in provider.legal_identifiers
                        and provider.legal_identifiers["DUNS"]
                    ):
                        provider_code = provider.legal_identifiers["DUNS"]
                        provider_code_type = "DUNS"
                    else:
                        # Use first available identifier
                        for key, value in provider.legal_identifiers.items():
                            if value:
                                provider_code = value
                                provider_code_type = key
                                break

                solution = contract.solution

                # c0040: ICT service type
                ict_service_type = solution.dora_ict_service_type or ""

                # c0050: Substitutability
                substitutability = solution.dora_substitutability or ""

                # c0060: Non-substitutability reason
                non_substitutability_reason = (
                    solution.dora_non_substitutability_reason or ""
                )

                # c0070: Last audit date (use solution updated_at as placeholder)
                last_audit_date = (
                    solution.updated_at.strftime("%Y-%m-%d")
                    if solution.updated_at
                    else ""
                )

                # c0080: Exit plan
                exit_plan = solution.dora_has_exit_plan or ""

                # c0090: Reintegration possibility
                reintegration_possibility = (
                    solution.dora_reintegration_possibility or ""
                )

                # c0100: Discontinuing impact
                discontinuing_impact = solution.dora_discontinuing_impact or ""

                # c0110: Alternative providers identified
                alternative_providers_identified = (
                    solution.dora_alternative_providers_identified or ""
                )

                # c0120: Alternative provider IDs
                alternative_providers = solution.dora_alternative_providers or ""

                csv_writer_0701.writerow(
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

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_07.01.csv", csv_buffer_0701.getvalue().encode("utf-8")
            )

            # Create b_99.01.csv - Aggregation report
            csv_buffer_9901 = io.StringIO()
            csv_writer_9901 = csv.writer(csv_buffer_9901)

            # Write CSV headers
            csv_writer_9901.writerow(
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

            # Get all third-party contracts with solutions for aggregation
            contracts_for_aggregation = Contract.objects.filter(
                id__in=viewable_contracts,
                is_intragroup=False,
                provider_entity__isnull=False,
                solution__isnull=False,
            ).select_related("solution")

            # Initialize counters
            # Contractual arrangement counts
            standalone_count = 0
            overarching_count = 0
            subsequent_count = 0

            # Data sensitiveness counts
            sensitiveness_low = 0
            sensitiveness_medium = 0
            sensitiveness_high = 0

            # Impact of discontinuing function (from assets)
            function_impact_low = 0
            function_impact_medium = 0
            function_impact_high = 0

            # Substitutability counts
            substitutability_not = 0
            substitutability_highly_complex = 0
            substitutability_medium = 0
            substitutability_easy = 0

            # Reintegration possibility counts
            reintegration_easy = 0
            reintegration_difficult = 0
            reintegration_highly_complex = 0

            # Impact of discontinuing ICT services counts
            ict_impact_low = 0
            ict_impact_medium = 0
            ict_impact_high = 0

            # Count contracts by each dimension
            for contract in contracts_for_aggregation:
                # Count by contractual arrangement
                if contract.dora_contractual_arrangement == "eba_CO:x1":
                    standalone_count += 1
                elif contract.dora_contractual_arrangement == "eba_CO:x2":
                    overarching_count += 1
                elif contract.dora_contractual_arrangement == "eba_CO:x3":
                    subsequent_count += 1

                solution = contract.solution

                # Count by data sensitiveness
                if solution.dora_data_sensitiveness == "eba_ZZ:x791":
                    sensitiveness_low += 1
                elif solution.dora_data_sensitiveness == "eba_ZZ:x792":
                    sensitiveness_medium += 1
                elif solution.dora_data_sensitiveness == "eba_ZZ:x793":
                    sensitiveness_high += 1

                # Count by substitutability
                if solution.dora_substitutability == "eba_ZZ:x959":
                    substitutability_not += 1
                elif solution.dora_substitutability == "eba_ZZ:x960":
                    substitutability_highly_complex += 1
                elif solution.dora_substitutability == "eba_ZZ:x961":
                    substitutability_medium += 1
                elif solution.dora_substitutability == "eba_ZZ:x962":
                    substitutability_easy += 1

                # Count by reintegration possibility
                if solution.dora_reintegration_possibility == "eba_ZZ:x798":
                    reintegration_easy += 1
                elif solution.dora_reintegration_possibility == "eba_ZZ:x966":
                    reintegration_difficult += 1
                elif solution.dora_reintegration_possibility == "eba_ZZ:x967":
                    reintegration_highly_complex += 1

                # Count by impact of discontinuing ICT services
                if solution.dora_discontinuing_impact == "eba_ZZ:x791":
                    ict_impact_low += 1
                elif solution.dora_discontinuing_impact == "eba_ZZ:x792":
                    ict_impact_medium += 1
                elif solution.dora_discontinuing_impact == "eba_ZZ:x793":
                    ict_impact_high += 1

            # Count business functions by impact of discontinuing
            business_functions = Asset.objects.filter(
                id__in=viewable_assets, is_business_function=True
            )

            for function in business_functions:
                if function.dora_discontinuing_impact == "eba_ZZ:x791":
                    function_impact_low += 1
                elif function.dora_discontinuing_impact == "eba_ZZ:x792":
                    function_impact_medium += 1
                elif function.dora_discontinuing_impact == "eba_ZZ:x793":
                    function_impact_high += 1

            # Write aggregation row
            csv_writer_9901.writerow(
                [
                    standalone_count,
                    overarching_count,
                    subsequent_count,
                    sensitiveness_low,
                    sensitiveness_medium,
                    sensitiveness_high,
                    function_impact_low,
                    function_impact_medium,
                    function_impact_high,
                    substitutability_not,
                    substitutability_highly_complex,
                    substitutability_medium,
                    substitutability_easy,
                    reintegration_easy,
                    reintegration_difficult,
                    reintegration_highly_complex,
                    ict_impact_low,
                    ict_impact_medium,
                    ict_impact_high,
                ]
            )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_99.01.csv", csv_buffer_9901.getvalue().encode("utf-8")
            )

        # Prepare response
        zip_buffer.seek(0)

        # Extract LEI for filename
        lei = ""
        if main_entity.legal_identifiers:
            lei = main_entity.legal_identifiers.get("LEI", "")

        # Use LEI in filename, fallback to timestamp if no LEI
        if lei:
            filename = f"LEI_{lei}_DORA_ROI.zip"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DORA_ROI_{timestamp}.zip"

        response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    @action(detail=False, name="Get country choices")
    def country(self, request):
        return Response(dict(COUNTRY_CHOICES))

    @action(detail=False, name="Get currency choices")
    def currency(self, request):
        return Response(dict(CURRENCY_CHOICES))

    @action(detail=False, name="Get DORA entity type choices")
    def dora_entity_type(self, request):
        return Response(dict(DORA_ENTITY_TYPE_CHOICES))

    @action(detail=False, name="Get DORA entity hierarchy choices")
    def dora_entity_hierarchy(self, request):
        return Response(dict(DORA_ENTITY_HIERARCHY_CHOICES))

    @action(detail=False, name="Get DORA provider person type choices")
    def dora_provider_person_type(self, request):
        return Response(dict(DORA_PROVIDER_PERSON_TYPE_CHOICES))


class EntityAssessmentViewSet(BaseModelViewSet):
    """
    API endpoint that allows entity assessments to be viewed or edited.
    """

    model = EntityAssessment
    filterset_fields = [
        "name",
        "status",
        "perimeter",
        "perimeter__folder",
        "folder",
        "authors",
        "entity",
        "criticality",
        "conclusion",
        "genericcollection",
    ]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.compliance_assessment:
            folder = instance.compliance_assessment.folder
            instance.compliance_assessment.delete()
            if folder.content_type == Folder.ContentType.ENCLAVE:
                folder.delete()
            else:
                logger.warning("Compliance assessment folder is not an Enclave", folder)

        return super().destroy(request, *args, **kwargs)

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(EntityAssessment.Status.choices))

    @action(detail=False, name="Get conclusion choices")
    def conclusion(self, request):
        return Response(dict(EntityAssessment.Conclusion.choices))

    @action(detail=False, name="Get TPRM metrics")
    def metrics(self, request):
        assessments_data = []

        (viewable_items, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=EntityAssessment,
        )

        for ea in EntityAssessment.objects.filter(id__in=viewable_items):
            entry = {
                "entity_assessment_id": ea.id,
                "provider": ea.entity.name,
                "solutions": ",".join([sol.name for sol in ea.solutions.all()])
                if len(ea.solutions.all()) > 0
                else "-",
                "baseline": ea.compliance_assessment.framework.name
                if ea.compliance_assessment
                else "-",
                "due_date": ea.due_date.strftime("%Y-%m-%d") if ea.due_date else "-",
                "last_update": ea.updated_at.strftime("%Y-%m-%d")
                if ea.updated_at
                else "-",
                "conclusion": ea.conclusion if ea.conclusion else "ongoing",
                "compliance_assessment_id": ea.compliance_assessment.id
                if ea.compliance_assessment
                else "#",
                "reviewers": ",".join([re.email for re in ea.reviewers.all()])
                if len(ea.reviewers.all())
                else "-",
                "observation": ea.observation if ea.observation else "-",
                "has_questions": ea.compliance_assessment.has_questions
                if ea.compliance_assessment
                else False,
            }

            completion = (
                ea.compliance_assessment.answers_progress
                if ea.compliance_assessment
                else 0
            )
            entry.update({"completion": completion})

            review_progress = (
                ea.compliance_assessment.get_progress()
                if ea.compliance_assessment
                else 0
            )
            entry.update({"review_progress": review_progress})
            assessments_data.append(entry)

        return Response(assessments_data)


class RepresentativeViewSet(BaseModelViewSet):
    """
    API endpoint that allows representatives to be viewed or edited.
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user:
            instance.user.delete()

        return super().destroy(request, *args, **kwargs)

    model = Representative
    filterset_fields = ["entity"]
    search_fields = ["email"]


class SolutionViewSet(BaseModelViewSet):
    """
    API endpoint that allows solutions to be viewed or edited.
    """

    model = Solution
    filterset_fields = [
        "name",
        "provider_entity",
        "assets",
        "criticality",
        "contracts",
        "dora_ict_service_type",
        "storage_of_data",
        "data_location_storage",
        "data_location_processing",
        "dora_data_sensitiveness",
        "dora_reliance_level",
        "dora_substitutability",
        "dora_non_substitutability_reason",
        "dora_has_exit_plan",
        "dora_reintegration_possibility",
        "dora_discontinuing_impact",
        "dora_alternative_providers_identified",
    ]

    @action(detail=False, name="Get data location storage choices")
    def data_location_storage(self, request):
        return Response(dict(COUNTRY_CHOICES))

    @action(detail=False, name="Get data location processing choices")
    def data_location_processing(self, request):
        return Response(dict(COUNTRY_CHOICES))

    @action(detail=False, name="Get data sensitiveness choices")
    def dora_data_sensitiveness(self, request):
        return Response(dict(DORA_SENSITIVENESS_CHOICES))

    @action(detail=False, name="Get reliance level choices")
    def dora_reliance_level(self, request):
        return Response(dict(DORA_RELIANCE_CHOICES))

    @action(detail=False, name="Get substitutability choices")
    def dora_substitutability(self, request):
        return Response(dict(DORA_SUBSTITUTABILITY_CHOICES))

    @action(detail=False, name="Get non-substitutability reason choices")
    def dora_non_substitutability_reason(self, request):
        return Response(dict(DORA_NON_SUBSTITUTABILITY_REASON_CHOICES))

    @action(detail=False, name="Get exit plan choices")
    def dora_has_exit_plan(self, request):
        return Response(dict(DORA_BINARY_CHOICES))

    @action(detail=False, name="Get reintegration possibility choices")
    def dora_reintegration_possibility(self, request):
        return Response(dict(DORA_REINTEGRATION_POSSIBILITY_CHOICES))

    @action(detail=False, name="Get discontinuing impact choices")
    def dora_discontinuing_impact(self, request):
        return Response(dict(DORA_DISCONTINUING_IMPACT_CHOICES))

    @action(detail=False, name="Get alternative providers identified choices")
    def dora_alternative_providers_identified(self, request):
        return Response(dict(DORA_BINARY_CHOICES))

    def perform_create(self, serializer):
        serializer.save()
        solution = serializer.instance
        solution.recipient_entity = Entity.objects.get(builtin=True)
        solution.save()

    @action(detail=False, name="Get DORA ICT service type choices")
    def dora_ict_service_type(self, request):
        return Response(dict(DORA_ICT_SERVICE_CHOICES))


class ContractViewSet(BaseModelViewSet):
    """
    API endpoint that allows contracts to be viewed or edited.
    """

    model = Contract
    filterset_fields = [
        "name",
        "folder",
        "provider_entity",
        "solution",
        "status",
        "owner",
        "dora_contractual_arrangement",
        "currency",
        "termination_reason",
        "is_intragroup",
        "overarching_contract",
        "governing_law_country",
        "notice_period_entity",
        "notice_period_provider",
    ]

    @action(detail=False, name="Get status choices")
    def status(self, request):
        return Response(dict(Contract.Status.choices))

    @action(detail=False, name="Get currency choices")
    def currency(self, request):
        return Response(dict(CURRENCY_CHOICES))

    @action(detail=False, name="Get DORA contractual arrangement choices")
    def dora_contractual_arrangement(self, request):
        return Response(dict(DORA_CONTRACTUAL_ARRANGEMENT_CHOICES))

    @action(detail=False, name="Get termination reason choices")
    def termination_reason(self, request):
        return Response(dict(TERMINATION_REASON_CHOICES))

    @action(detail=False, name="Get governing law country choices")
    def governing_law_country(self, request):
        return Response(dict(COUNTRY_CHOICES))
