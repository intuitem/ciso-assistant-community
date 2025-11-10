from rest_framework.response import Response
from iam.models import Folder, RoleAssignment, UserGroup
from core.views import BaseModelViewSet as AbstractBaseModelViewSet
from tprm.models import Entity, Representative, Solution, EntityAssessment, Contract
from rest_framework.decorators import action
import structlog

from rest_framework.request import Request
from rest_framework.response import Response

from django.utils.formats import date_format
from django.http import HttpResponse

from core.constants import COUNTRY_CHOICES, CURRENCY_CHOICES
from core.dora import (
    DORA_ENTITY_TYPE_CHOICES,
    DORA_ENTITY_HIERARCHY_CHOICES,
    DORA_CONTRACTUAL_ARRANGEMENT_CHOICES,
    TERMINATION_REASON_CHOICES,
    DORA_ICT_SERVICE_CHOICES,
    DORA_SENSITIVENESS_CHOICES,
    DORA_RELIANCE_CHOICES,
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

            # Write main entity data
            lei_02 = ""
            if main_entity.legal_identifiers:
                lei_02 = main_entity.legal_identifiers.get("LEI", "")

            country_02 = ""
            if main_entity.country:
                country_02 = f"eba_GA:{main_entity.country}"

            # Format currency with eba_CU: prefix
            currency_02 = ""
            if main_entity.currency:
                currency_02 = f"eba_CU:{main_entity.currency}"

            # Format dates, use 2999-12-31 as default for mandatory fields
            last_update = (
                main_entity.updated_at.strftime("%Y-%m-%d")
                if main_entity.updated_at
                else "2999-12-31"
            )
            integration_date = (
                main_entity.created_at.strftime("%Y-%m-%d")
                if main_entity.created_at
                else "2999-12-31"
            )
            deletion_date = (
                "2999-12-31"  # Empty for active entities, use far future date
            )

            csv_writer_02.writerow(
                [
                    lei_02,
                    main_entity.name,
                    country_02,
                    main_entity.dora_entity_type or "",
                    main_entity.dora_entity_hierarchy or "",
                    "",  # LEI of parent entity - not yet implemented
                    last_update,
                    integration_date,
                    deletion_date,
                    currency_02,
                    main_entity.dora_assets_value
                    if main_entity.dora_assets_value is not None
                    else "",
                ]
            )

            # Add CSV to zip in reports folder
            zip_file.writestr(
                "reports/b_01.02.csv", csv_buffer_02.getvalue().encode("utf-8")
            )

            # Create b_01.03.csv - Branches register (placeholder)
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

            # Placeholder - no branch data yet
            # Future implementation will include branches

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
            ).prefetch_related("solutions__provider_entity"):
                # For each solution in the contract
                for solution in contract.solutions.all():
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
        "entities",
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
