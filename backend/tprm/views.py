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

        This generates a comprehensive DORA ROI export containing multiple CSV reports:
        - b_01.01: Main entity information
        - b_01.02: Entity register (main entity + branches)
        - b_01.03: Branches register
        - b_02.01-03: Contractual arrangements
        - b_03.01-03: Signing entities and providers
        - b_04.01: Entities using ICT services
        - b_05.01-02: Provider details and supply chains
        - b_06.01: Critical functions register
        - b_07.01: Assessment of ICT services
        - b_99.01: Aggregation report
        """
        from tprm import dora_export

        # Get the main entity
        main_entity = Entity.get_main_entity()

        if not main_entity:
            return HttpResponse("No main entity found", status=400)

        # Get accessible objects for the current user
        (viewable_entities, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Entity,
        )

        (viewable_contracts, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Contract,
        )

        (viewable_assets, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Asset,
        )

        # Prepare entity lists
        # Subsidiaries: entities with main entity as parent AND dora_provider_person_type set (legal person)
        # Branches: entities with main entity as parent AND dora_provider_person_type not set
        subsidiaries = list(
            Entity.objects.filter(
                id__in=viewable_entities,
                parent_entity=main_entity,
                dora_provider_person_type__isnull=False,
            ).exclude(dora_provider_person_type="")
        )
        branches = list(
            Entity.objects.filter(
                id__in=viewable_entities,
                parent_entity=main_entity,
                dora_provider_person_type__isnull=True,
            )
            | Entity.objects.filter(
                id__in=viewable_entities,
                parent_entity=main_entity,
                dora_provider_person_type="",
            )
        )
        # b_01.02 includes only main entity and subsidiaries (not branches)
        entities_for_b_01_02 = [main_entity] + subsidiaries

        # Prepare contract QuerySets
        contracts = Contract.objects.filter(id__in=viewable_contracts)

        # Prepare business functions
        business_functions = Asset.objects.filter(
            id__in=viewable_assets, is_business_function=True
        )

        # Create zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Generate all DORA ROI reports
            dora_export.generate_b_01_01_main_entity(zip_file, main_entity)
            dora_export.generate_b_01_02_entities(
                zip_file, main_entity, entities_for_b_01_02
            )
            dora_export.generate_b_01_03_branches(zip_file, main_entity, branches)

            dora_export.generate_b_02_01_contracts(zip_file, contracts)
            dora_export.generate_b_02_02_ict_services(zip_file, contracts)
            dora_export.generate_b_02_03_intragroup_contracts(zip_file, contracts)

            dora_export.generate_b_03_01_signing_entities(
                zip_file, main_entity, contracts
            )
            dora_export.generate_b_03_02_ict_providers(zip_file, contracts)
            dora_export.generate_b_03_03_intragroup_providers(
                zip_file, main_entity, contracts
            )

            dora_export.generate_b_04_01_service_users(
                zip_file, main_entity, branches, contracts
            )

            dora_export.generate_b_05_01_provider_details(
                zip_file, main_entity, contracts
            )
            dora_export.generate_b_05_02_supply_chains(zip_file, main_entity, contracts)

            dora_export.generate_b_06_01_functions(
                zip_file, main_entity, business_functions
            )

            dora_export.generate_b_07_01_assessment(zip_file, contracts)

            dora_export.generate_b_99_01_aggregation(
                zip_file, contracts, business_functions
            )

        # Prepare response
        zip_buffer.seek(0)

        # Extract LEI for filename
        lei, _ = dora_export.get_entity_identifier(main_entity, priority=["LEI"])

        # Use LEI in filename, fallback to timestamp if no LEI
        if lei:
            filename = f"LEI_{lei}_DORA_ROI.zip"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"DORA_ROI_{timestamp}.zip"

        response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response

    @action(detail=False, methods=["get"], name="Lint DORA ROI")
    def dora_roi_lint(self, request):
        """
        Validate DORA ROI requirements and return linting results.
        """
        from tprm import dora_linter

        lint_results = dora_linter.lint_dora_roi()
        return Response(lint_results)

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
        "beneficiary_entity",
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
