import structlog
from django.db import transaction

from core.models import (
    StoredLibrary,
    LoadedLibrary,
    Framework,
    RiskMatrix,
    Perimeter,
    RiskAssessment,
    ComplianceAssessment,
    FindingsAssessment,
    TaskTemplate,
    OrganisationObjective,
    OrganisationIssue,
    PresetJourney,
    PresetJourneyStep,
)
from core.serializers import (
    FolderWriteSerializer,
    PerimeterWriteSerializer,
    RiskAssessmentWriteSerializer,
    ComplianceAssessmentWriteSerializer,
    FindingsAssessmentWriteSerializer,
    TaskTemplateWriteSerializer,
    OrganisationObjectiveWriteSerializer,
    OrganisationIssueWriteSerializer,
)
from privacy.models import Processing
from privacy.serializers import ProcessingWriteSerializer
from tprm.models import Entity
from tprm.serializers import EntityWriteSerializer
from global_settings.models import GlobalSettings
from iam.models import Folder, User

logger = structlog.get_logger(__name__)


class PresetExecutor:
    """Applies a preset definition, creating all scaffolded objects and a trackable journey."""

    def __init__(self, stored_library: StoredLibrary, user: User, request=None):
        self._stored_library = stored_library
        self._preset_content = stored_library.content["preset"]
        self._user = user
        self._request = request

    @transaction.atomic
    def apply(
        self,
        folder_name: str | None = None,
        folder_id: str | None = None,
    ) -> PresetJourney:
        self._load_dependencies()
        self._apply_feature_flags()
        if folder_id:
            folder = Folder.objects.get(id=folder_id)
        else:
            folder = self._create_folder(folder_name)
        perimeter = self._create_default_perimeter(folder)
        object_refs = self._create_objects(folder, perimeter)
        journey = PresetJourney.objects.create(
            name=self._stored_library.name,
            description=self._stored_library.description or "",
            folder=folder,
            urn=self._stored_library.urn,
            object_refs=object_refs,
            applied_by=self._user,
        )
        self._create_steps(journey, object_refs)
        return journey

    def _load_dependencies(self):
        dependencies = self._stored_library.dependencies or []
        for dep_urn in dependencies:
            if LoadedLibrary.objects.filter(urn=dep_urn).exists():
                continue
            try:
                stored_lib = StoredLibrary.objects.get(urn=dep_urn)
                stored_lib.load()
            except StoredLibrary.DoesNotExist:
                logger.warning("Dependency not found in store", urn=dep_urn)
            except Exception as e:
                logger.error("Failed to load dependency", urn=dep_urn, error=e)
                raise

    def _apply_feature_flags(self):
        flags_config = self._preset_content.get("feature_flags")
        if not flags_config:
            return

        settings_obj, _ = GlobalSettings.objects.get_or_create(
            name="feature-flags",
            defaults={"value": {}},
        )

        value = dict(settings_obj.value or {})
        for flag in flags_config.get("enable", []):
            value[flag] = True
        for flag in flags_config.get("disable", []):
            value[flag] = False

        settings_obj.value = value
        settings_obj.save()

    def _create_folder(self, folder_name: str | None) -> Folder:
        name = folder_name or self._stored_library.name
        context = {"request": self._request} if self._request else {}
        folder_data = {
            "content_type": Folder.ContentType.DOMAIN,
            "name": name,
            "create_iam_groups": True,
        }
        serializer = FolderWriteSerializer(data=folder_data, context=context)
        serializer.is_valid(raise_exception=True)
        folder = serializer.save()
        Folder.create_default_ug_and_ra(folder)
        return folder

    def _create_default_perimeter(self, folder: Folder) -> Perimeter:
        """Create a default perimeter for the preset's folder, or reuse an existing one."""
        existing = Perimeter.objects.filter(
            folder=folder, name=self._stored_library.name
        ).first()
        if existing:
            return existing

        context = {"request": self._request} if self._request else {}
        perimeter_data = {
            "folder": str(folder.id),
            "name": self._stored_library.name,
        }
        serializer = PerimeterWriteSerializer(data=perimeter_data, context=context)
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    # Maps object type → model class for reuse lookups
    _TYPE_MODEL_MAP = {
        "perimeter": Perimeter,
        "risk_assessment": RiskAssessment,
        "compliance_assessment": ComplianceAssessment,
        "task_template": TaskTemplate,
        "organisation_objective": OrganisationObjective,
        "organisation_issue": OrganisationIssue,
        "processing": Processing,
        "entity": Entity,
        "findings_assessment": FindingsAssessment,
    }

    def _find_existing(self, folder: Folder, item: dict):
        """Return an existing object if one with the same name already exists in the folder."""
        model_class = self._TYPE_MODEL_MAP.get(item["type"])
        if not model_class:
            return None
        return model_class.objects.filter(folder=folder, name=item["name"]).first()

    def _create_objects(self, folder: Folder, default_perimeter: Perimeter) -> dict:
        scaffolded = self._preset_content.get("scaffolded_objects", [])
        object_refs = {}
        context = {"request": self._request} if self._request else {}

        for item in scaffolded:
            obj_type = item["type"]
            ref = item.get("ref")

            # Reuse existing object if one with the same name exists in this folder
            existing = self._find_existing(folder, item)
            if existing:
                logger.info(
                    "Reusing existing object",
                    type=obj_type,
                    name=item["name"],
                    id=str(existing.id),
                )
                if ref:
                    object_refs[ref] = str(existing.id)
                continue

            if obj_type == "perimeter":
                data = {
                    "folder": str(folder.id),
                    "name": item["name"],
                }
                serializer = PerimeterWriteSerializer(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "risk_assessment":
                matrix = self._resolve_library_object(item["risk_matrix"], RiskMatrix)
                data = {
                    "folder": str(folder.id),
                    "perimeter": str(default_perimeter.id),
                    "risk_matrix": str(matrix.id),
                    "name": item["name"],
                }
                serializer = RiskAssessmentWriteSerializer(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "compliance_assessment":
                framework = self._resolve_library_object(item["framework"], Framework)
                data = {
                    "folder": str(folder.id),
                    "perimeter": str(default_perimeter.id),
                    "framework": str(framework.id),
                    "name": item["name"],
                }
                serializer = ComplianceAssessmentWriteSerializer(
                    data=data, context=context
                )
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()
                obj.create_requirement_assessments()

                if item.get("create_suggested_controls"):
                    assessments = obj.requirement_assessments.all().prefetch_related(
                        "requirement__reference_controls"
                    )
                    for ra in assessments:
                        ra.create_applied_controls_from_suggestions()

            elif obj_type == "task_template":
                data = {
                    "folder": str(folder.id),
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "is_recurrent": item.get("is_recurrent", False),
                    "schedule": item.get("schedule"),
                }
                serializer = TaskTemplateWriteSerializer(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "organisation_objective":
                data = {
                    "folder": str(folder.id),
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "status": item.get("status", "draft"),
                }
                serializer = OrganisationObjectiveWriteSerializer(
                    data=data, context=context
                )
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "organisation_issue":
                data = {
                    "folder": str(folder.id),
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "category": item.get("category"),
                    "origin": item.get("origin"),
                    "status": item.get("status", "draft"),
                }
                serializer = OrganisationIssueWriteSerializer(
                    data=data, context=context
                )
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "processing":
                data = {
                    "folder": str(folder.id),
                    "name": item["name"],
                    "description": item.get("description", ""),
                    "status": item.get("status", "privacy_draft"),
                }
                serializer = ProcessingWriteSerializer(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "entity":
                data = {
                    "folder": str(folder.id),
                    "name": item["name"],
                    "description": item.get("description", ""),
                }
                serializer = EntityWriteSerializer(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "findings_assessment":
                data = {
                    "folder": str(folder.id),
                    "perimeter": str(default_perimeter.id),
                    "name": item["name"],
                    "category": item.get("category", "pentest"),
                }
                serializer = FindingsAssessmentWriteSerializer(
                    data=data, context=context
                )
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            else:
                logger.warning("Unknown scaffolded object type", type=obj_type)
                continue

            if ref:
                object_refs[ref] = str(obj.id)

        return object_refs

    def _resolve_library_object(self, urn: str, model_class):
        """Resolve a library URN to a loaded object (Framework, RiskMatrix, etc.)."""
        loaded_lib = LoadedLibrary.objects.filter(urn=urn).first()
        if not loaded_lib:
            raise ValueError(f"Library {urn} is not loaded. Check dependencies.")
        return model_class.objects.get(library=loaded_lib)

    def _create_steps(self, journey: PresetJourney, object_refs: dict):
        steps_config = self._preset_content.get("journey", {}).get("steps", [])
        for order, step_def in enumerate(steps_config):
            target_ref = step_def.get("target_ref")
            resolved_ref = object_refs.get(target_ref) if target_ref else None

            PresetJourneyStep.objects.create(
                journey=journey,
                key=step_def["key"],
                order=order,
                title=step_def["title"],
                description=step_def.get("description", ""),
                target_model=step_def.get("target_model"),
                target_ref=resolved_ref,
                status=PresetJourneyStep.Status.NOT_STARTED,
            )
