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
from django.db.models import Sum, F, FloatField, Case, When, Value
from django.db.models.functions import Cast, Greatest, Coalesce, Round

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
        "ref_id",
        "is_active",
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
        "filtering_labels",
        "default_dependency",
        "default_penetration",
        "default_maturity",
        "default_trust",
    ]

    def get_queryset(self):
        """Add annotation for default_criticality to enable sorting"""
        qs = super().get_queryset()

        # Annotate with default_criticality calculation
        # Formula: (default_dependency * default_penetration) / (default_maturity * default_trust)
        # Handle division by zero by using Case/When
        # Rounded to 2 decimal places by multiplying by 100, rounding, then dividing by 100
        qs = qs.annotate(
            default_criticality=Cast(
                Round(
                    Case(
                        # If maturity or trust is 0, return 0.0
                        When(default_maturity=0, then=Value(0.0)),
                        When(default_trust=0, then=Value(0.0)),
                        # Otherwise, calculate criticality * 100
                        default=Cast(
                            (F("default_dependency") * F("default_penetration") * 100.0)
                            / (F("default_maturity") * F("default_trust")),
                            output_field=FloatField(),
                        ),
                        output_field=FloatField(),
                    )
                )
                / 100.0,
                output_field=FloatField(),
            )
        )

        return qs

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
        - FilingIndicators.csv: Template inclusion indicators
        - parameters.csv: Report metadata and configuration
        - META-INF/reportPackage.json: XBRL report package metadata
        - reports/report.json: XBRL CSV configuration and taxonomy references
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

        # Collect all assets related to business functions (including child assets)
        # This ensures that solutions linked to child assets are also captured in DORA reports
        business_function_asset_ids = set(
            business_functions.values_list("id", flat=True)
        )
        for business_function in business_functions:
            # Get all descendant (child) assets for each business function
            # Note: get_descendants() returns Asset objects, not IDs
            descendants = business_function.get_descendants()
            business_function_asset_ids.update(asset.id for asset in descendants)

        # Get all solutions related to business functions and their child assets
        # These are the ICT services that support critical business functions
        related_solutions = Solution.objects.filter(
            assets__id__in=business_function_asset_ids
        ).distinct()

        # Filter contracts to only those with solutions related to business functions
        # This subset is used for reports that focus on ICT services supporting critical functions
        # (b_02.02, b_07.01, b_99.01)
        related_solution_ids = set(related_solutions.values_list("id", flat=True))
        business_function_contracts = contracts.filter(
            solutions__id__in=related_solution_ids
        )

        # Calculate folder name for the ZIP structure (without .zip extension)
        lei, _ = dora_export.get_entity_identifier(main_entity, priority=["LEI"])
        competent_authority = main_entity.dora_competent_authority or "UNKNOWN"

        if lei:
            base_folder_name = f"LEI_{lei}.CON_{competent_authority}_DOR_DORA_ROI"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_folder_name = f"DORA_ROI_{timestamp}"

        # Create zip file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            # Generate all DORA ROI reports (with folder prefix)
            dora_export.generate_b_01_01_main_entity(
                zip_file, main_entity, base_folder_name
            )
            dora_export.generate_b_01_02_entities(
                zip_file, main_entity, entities_for_b_01_02, base_folder_name
            )
            dora_export.generate_b_01_03_branches(zip_file, branches, base_folder_name)

            dora_export.generate_b_02_01_contracts(
                zip_file, contracts, base_folder_name
            )
            dora_export.generate_b_02_02_ict_services(
                zip_file, contracts, base_folder_name, business_function_asset_ids
            )
            dora_export.generate_b_02_03_intragroup_contracts(
                zip_file, contracts, base_folder_name
            )

            dora_export.generate_b_03_01_signing_entities(
                zip_file, main_entity, contracts, base_folder_name
            )
            dora_export.generate_b_03_02_ict_providers(
                zip_file, contracts, base_folder_name
            )
            dora_export.generate_b_03_03_intragroup_providers(
                zip_file, main_entity, contracts, base_folder_name
            )

            dora_export.generate_b_04_01_service_users(
                zip_file, branches, contracts, base_folder_name
            )

            dora_export.generate_b_05_01_provider_details(
                zip_file, main_entity, contracts, base_folder_name
            )
            dora_export.generate_b_05_02_supply_chains(
                zip_file, contracts, base_folder_name
            )

            dora_export.generate_b_06_01_functions(
                zip_file, main_entity, business_functions, base_folder_name
            )

            dora_export.generate_b_07_01_assessment(
                zip_file, business_function_contracts, base_folder_name
            )

            dora_export.generate_b_99_01_aggregation(
                zip_file,
                business_function_contracts,
                business_functions,
                base_folder_name,
            )

            # Generate FilingIndicators.csv
            dora_export.generate_filing_indicators(zip_file, base_folder_name)

            # Generate parameters.csv
            dora_export.generate_parameters(zip_file, main_entity, base_folder_name)

            # Generate JSON metadata files
            dora_export.generate_report_package_json(zip_file, base_folder_name)
            dora_export.generate_report_json(zip_file, base_folder_name)

        # Prepare response
        zip_buffer.seek(0)

        # Use the same base folder name for the ZIP filename
        filename = f"{base_folder_name}.zip"

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

    @action(detail=False, methods=["get"], name="Get entities graph")
    def graph(self, request):
        """
        Generate graph data for entities, showing:
        - Entity hierarchy (parent-child relationships)
        - Solutions provided by entities
        - Contracts between entities
        - Assets linked to solutions
        - Asset hierarchy (parent-child asset relationships)
        """
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

        (viewable_solutions, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Solution,
        )

        (viewable_assets, _, _) = RoleAssignment.get_accessible_object_ids(
            folder=Folder.get_root_folder(),
            user=request.user,
            object_type=Asset,
        )

        # Get entities, solutions, contracts, and assets
        entities = Entity.objects.filter(id__in=viewable_entities)
        solutions = Solution.objects.filter(id__in=viewable_solutions).select_related(
            "provider_entity"
        )
        contracts = (
            Contract.objects.filter(id__in=viewable_contracts)
            .select_related("provider_entity", "beneficiary_entity")
            .prefetch_related("solutions")
        )
        assets = Asset.objects.filter(id__in=viewable_assets)

        # Build nodes and links
        nodes = []
        links = []
        categories = []
        category_map = {}
        node_index = 0

        # Create entity nodes
        entity_node_map = {}
        for entity in entities:
            nodes.append(
                {
                    "name": entity.name,
                    "category": 0,  # Entities category
                    "symbol": "roundRect",
                    "symbolSize": 35,
                    "value": f"Entity: {entity.name}",
                }
            )
            entity_node_map[entity.id] = node_index
            node_index += 1

        # Add entity hierarchy links (parent-child relationships)
        for entity in entities:
            if entity.parent_entity and entity.parent_entity.id in entity_node_map:
                links.append(
                    {
                        "source": entity_node_map[entity.parent_entity.id],
                        "target": entity_node_map[entity.id],
                        "value": "parent of",
                    }
                )

        # Create solution nodes
        solution_node_map = {}
        for solution in solutions:
            nodes.append(
                {
                    "name": solution.name,
                    "category": 1,  # Solutions category
                    "symbol": "diamond",
                    "symbolSize": 30,
                    "value": f"Solution: {solution.name}",
                }
            )
            solution_node_map[solution.id] = node_index

            # Link solution to provider entity
            if (
                solution.provider_entity
                and solution.provider_entity.id in entity_node_map
            ):
                links.append(
                    {
                        "source": entity_node_map[solution.provider_entity.id],
                        "target": node_index,
                        "value": "provides",
                    }
                )

            node_index += 1

        # Create contract nodes
        contract_node_map = {}
        for contract in contracts:
            nodes.append(
                {
                    "name": contract.name,
                    "category": 2,  # Contracts category
                    "symbol": "circle",
                    "symbolSize": 25,
                    "value": f"Contract: {contract.name}",
                }
            )
            contract_node_map[contract.id] = node_index

            # Link contract to provider entity
            if (
                contract.provider_entity
                and contract.provider_entity.id in entity_node_map
            ):
                links.append(
                    {
                        "source": entity_node_map[contract.provider_entity.id],
                        "target": node_index,
                        "value": "provider",
                    }
                )

            # Link contract to beneficiary entity
            if (
                contract.beneficiary_entity
                and contract.beneficiary_entity.id in entity_node_map
            ):
                links.append(
                    {
                        "source": node_index,
                        "target": entity_node_map[contract.beneficiary_entity.id],
                        "value": "beneficiary",
                    }
                )

            # Link contract to solutions
            for solution in contract.solutions.all():
                if solution.id in solution_node_map:
                    links.append(
                        {
                            "source": node_index,
                            "target": solution_node_map[solution.id],
                            "value": "frames",
                        }
                    )

            node_index += 1

        # Create asset nodes (only those with connections)
        asset_node_map = {}
        for asset in assets:
            # Check if asset has any connections (to solutions or other assets)
            linked_solutions = solutions.filter(assets=asset)
            parent_assets = asset.parent_assets.filter(id__in=viewable_assets)
            child_assets = assets.filter(parent_assets=asset)

            has_connections = (
                linked_solutions.exists()
                or parent_assets.exists()
                or child_assets.exists()
            )

            # Only create node if asset has connections
            if has_connections:
                nodes.append(
                    {
                        "name": asset.name,
                        "category": 3,  # Assets category
                        "symbol": "triangle",
                        "symbolSize": 20,
                        "value": f"Asset: {asset.name}",
                    }
                )
                asset_node_map[asset.id] = node_index

                # Link asset to solutions
                for solution in linked_solutions:
                    if solution.id in solution_node_map:
                        links.append(
                            {
                                "source": node_index,
                                "target": solution_node_map[solution.id],
                                "value": "uses",
                            }
                        )

                node_index += 1

        # Add asset hierarchy links (parent-child relationships)
        for asset in assets:
            if asset.id in asset_node_map:
                # Get parent assets for this asset
                parent_assets = asset.parent_assets.filter(id__in=viewable_assets)
                for parent_asset in parent_assets:
                    if parent_asset.id in asset_node_map:
                        links.append(
                            {
                                "source": asset_node_map[parent_asset.id],
                                "target": asset_node_map[asset.id],
                                "value": "relies on",
                            }
                        )

        # Define categories
        categories = [
            {"name": "Entities"},
            {"name": "Solutions"},
            {"name": "Contracts"},
            {"name": "Assets"},
        ]

        return Response(
            {
                "nodes": nodes,
                "links": links,
                "categories": categories,
                "meta": {"display_name": "Entities Graph"},
            }
        )

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

    @action(detail=False, methods=["post"], url_path="batch-create")
    def batch_create(self, request):
        """
        Batch create multiple entities from a text list.
        Expected format:
        {
            "entities_text": "Entity 1\\nEntity 2\\nREF-001:Entity 3",
            "folder": "folder-uuid"
        }
        Lines can optionally have a ref_id prefix (REF-001:Entity Name).
        Entities with the same name in the folder will be skipped.
        """
        from rest_framework import status
        from tprm.serializers import EntityWriteSerializer

        try:
            entities_text = request.data.get("entities_text", "")
            folder_id = request.data.get("folder")

            if not entities_text:
                return Response(
                    {"error": "entities_text is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not folder_id:
                return Response(
                    {"error": "folder is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify folder exists and user has access
            if not RoleAssignment.is_object_readable(request.user, Folder, folder_id):
                return Response(
                    {"error": "Folder not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            folder = Folder.objects.get(id=folder_id)

            # Parse the entities text
            lines = [line.strip() for line in entities_text.split("\n") if line.strip()]
            created_entities = []
            skipped_entities = []
            errors = []

            for line in lines:
                # Check for ref_id prefix (REF-001:Entity Name)
                ref_id = ""
                entity_name = line

                if ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2 and parts[0].strip():
                        ref_id = parts[0].strip()
                        entity_name = parts[1].strip()

                if not entity_name:
                    errors.append({"line": line, "error": "Empty entity name"})
                    continue

                # Check if entity already exists in the folder
                existing_entity = Entity.objects.filter(
                    name=entity_name, folder=folder_id
                ).first()

                if existing_entity:
                    # Skip existing entity
                    skipped_entities.append(
                        {
                            "id": str(existing_entity.id),
                            "name": existing_entity.name,
                            "ref_id": existing_entity.ref_id,
                        }
                    )
                    continue

                # Create new entity using the serializer to respect IAM
                entity_data = {
                    "name": entity_name,
                    "folder": folder_id,
                }

                if ref_id:
                    entity_data["ref_id"] = ref_id

                serializer = EntityWriteSerializer(
                    data=entity_data, context={"request": request}
                )

                if serializer.is_valid():
                    entity = serializer.save()

                    created_entities.append(
                        {
                            "id": str(entity.id),
                            "name": entity.name,
                            "ref_id": entity.ref_id,
                        }
                    )
                else:
                    errors.append(
                        {
                            "line": line,
                            "errors": serializer.errors,
                        }
                    )

            return Response(
                {
                    "created": len(created_entities),
                    "skipped": len(skipped_entities),
                    "entities": created_entities,
                    "skipped_entities": skipped_entities,
                    "errors": errors,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error("Error in batch create entities", error=str(e))
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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
            if folder.content_type == Folder.ContentType.ENCLAVE:
                logger.info(
                    "deleting_compliance_assessment_folder",
                    folder_id=str(folder.id),
                    content_type=str(folder.content_type),
                )
                folder.delete()
            else:
                logger.warning(
                    "Compliance assessment folder is not an Enclave, skipping deletion",
                    folder=folder,
                )

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
    filterset_fields = ["entity", "ref_id", "filtering_labels"]
    search_fields = ["email"]


class SolutionViewSet(BaseModelViewSet):
    """
    API endpoint that allows solutions to be viewed or edited.
    """

    model = Solution
    filterset_fields = [
        "name",
        "ref_id",
        "is_active",
        "provider_entity",
        "assets",
        "criticality",
        "contracts",
        "owner",
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
        "filtering_labels",
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
        "solutions",
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
