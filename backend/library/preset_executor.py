import structlog
from django.db import transaction
from django.utils.translation import get_language

from core.models import (
    StoredLibrary,
    LoadedLibrary,
    Framework,
    RiskMatrix,
    Perimeter,
    RiskAssessment,
    RiskScenario,
    Asset,
    Threat,
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
    RiskScenarioWriteSerializer,
    AssetWriteSerializer,
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

    def _tr(self, item: dict, field: str) -> str:
        """Resolve a translated field from an item's inline translations block.

        Falls back to the item's primary-language value if no translation exists
        for the current locale.
        """
        locale = get_language() or "en"
        # Strip region suffix (e.g. "fr-fr" -> "fr")
        locale = locale.split("-")[0]
        translated = item.get("translations", {}).get(locale, {}).get(field)
        if translated:
            return translated
        return item.get(field, "")

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

        # Resolve translated library name/description
        locale = get_language() or "en"
        locale = locale.split("-")[0]
        lib_translations = self._stored_library.translations or {}
        locale_tr = lib_translations.get(locale, {})
        journey_name = locale_tr.get("name", self._stored_library.name)
        journey_description = locale_tr.get(
            "description", self._stored_library.description or ""
        )

        journey = PresetJourney.objects.create(
            name=journey_name,
            description=journey_description,
            folder=folder,
            urn=self._stored_library.urn,
            version=self._stored_library.version,
            object_refs=object_refs,
            applied_by=self._user,
        )
        self._create_steps(journey, object_refs)
        return journey

    @transaction.atomic
    def upgrade_journey(self, journey: PresetJourney) -> PresetJourney:
        """Non-destructive upgrade of an existing journey to the current preset version.

        - Re-runs dependency loading and feature flags
        - Creates any new scaffolded objects (idempotent)
        - Syncs steps: adds new, removes orphaned, updates metadata, preserves user state
        """
        self._load_dependencies()
        self._apply_feature_flags()

        folder = journey.folder
        perimeter = self._create_default_perimeter(folder)
        new_object_refs = self._create_objects(folder, perimeter)

        # Merge: keep old refs, add/overwrite with new
        merged_refs = dict(journey.object_refs or {})
        merged_refs.update(new_object_refs)

        self._sync_steps(journey, merged_refs)

        # Update journey metadata
        locale = get_language() or "en"
        locale = locale.split("-")[0]
        lib_translations = self._stored_library.translations or {}
        locale_tr = lib_translations.get(locale, {})

        journey.name = locale_tr.get("name", self._stored_library.name)
        journey.description = locale_tr.get(
            "description", self._stored_library.description or ""
        )
        journey.version = self._stored_library.version
        journey.object_refs = merged_refs
        journey.save()

        return journey

    def _sync_steps(self, journey: PresetJourney, object_refs: dict):
        """Reconcile journey steps with the current preset definition.

        - Existing steps (matched by key): update order, title, description, target_model, target_ref.
          Preserves status, notes, completed_at, completed_by.
        - New keys: create new steps with NOT_STARTED status.
        - Removed keys: delete orphaned steps.
        """
        steps_config = self._preset_content.get("journey", {}).get("steps", [])
        existing_steps = {step.key: step for step in journey.steps.all()}
        new_keys = set()
        to_update = []

        for order, step_def in enumerate(steps_config):
            key = step_def["key"]
            new_keys.add(key)
            target_ref_key = step_def.get("target_ref")
            resolved_ref = object_refs.get(target_ref_key) if target_ref_key else None

            if key in existing_steps:
                step = existing_steps[key]
                step.order = order
                step.title = self._tr(step_def, "title")
                step.description = self._tr(step_def, "description")
                step.target_model = step_def.get("target_model")
                step.target_ref = resolved_ref
                to_update.append(step)
            else:
                PresetJourneyStep.objects.create(
                    journey=journey,
                    key=key,
                    order=order,
                    title=self._tr(step_def, "title"),
                    description=self._tr(step_def, "description"),
                    target_model=step_def.get("target_model"),
                    target_ref=resolved_ref,
                    status=PresetJourneyStep.Status.NOT_STARTED,
                )

        if to_update:
            PresetJourneyStep.objects.bulk_update(
                to_update,
                ["order", "title", "description", "target_model", "target_ref"],
            )

        # Delete orphaned steps
        orphaned_keys = set(existing_steps.keys()) - new_keys
        if orphaned_keys:
            journey.steps.filter(key__in=orphaned_keys).delete()

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

        from global_settings.serializers import FeatureFlagsSerializer

        settings_obj, _ = GlobalSettings.objects.get_or_create(
            name="feature-flags",
            defaults={"value": {}},
        )

        # Build the full set of known flags from the serializer
        all_flags = {
            field.source.split(".")[-1]
            for field in FeatureFlagsSerializer().fields.values()
            if hasattr(field, "source") and field.source.startswith("value.")
        }

        # Start from current value, then set all known flags to False
        value = dict(settings_obj.value or {})
        for flag in all_flags:
            value[flag] = False

        # Enable only the flags the preset requests
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

    # Maps object type -> model class for reuse lookups
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
        "asset": Asset,
        "risk_scenario": RiskScenario,
    }

    def _find_existing(self, folder: Folder, obj_type: str, name: str):
        """Return an existing object if one with the same name already exists in the folder."""
        model_class = self._TYPE_MODEL_MAP.get(obj_type)
        if not model_class:
            return None
        return model_class.objects.filter(folder=folder, name=name).first()

    def _create_objects(self, folder: Folder, default_perimeter: Perimeter) -> dict:
        scaffolded = self._preset_content.get("scaffolded_objects", [])
        object_refs = {}
        deferred_scenarios = []
        context = {"request": self._request} if self._request else {}

        for item in scaffolded:
            obj_type = item["type"]
            ref = item.get("ref")
            name = self._tr(item, "name")
            description = self._tr(item, "description")

            # Reuse existing object if one with the same name exists in this folder
            existing = self._find_existing(folder, obj_type, name)
            if existing:
                logger.info(
                    "Reusing existing object",
                    type=obj_type,
                    name=name,
                    id=str(existing.id),
                )
                if ref:
                    object_refs[ref] = str(existing.id)
                continue

            if obj_type == "perimeter":
                data = {
                    "folder": str(folder.id),
                    "name": name,
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
                    "name": name,
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
                    "name": name,
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
                    "name": name,
                    "description": description,
                    "is_recurrent": item.get("is_recurrent", False),
                    "schedule": item.get("schedule"),
                }
                serializer = TaskTemplateWriteSerializer(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "organisation_objective":
                data = {
                    "folder": str(folder.id),
                    "name": name,
                    "description": description,
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
                    "name": name,
                    "description": description,
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
                    "name": name,
                    "description": description,
                    "status": item.get("status", "privacy_draft"),
                }
                serializer = ProcessingWriteSerializer(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "entity":
                data = {
                    "folder": str(folder.id),
                    "name": name,
                    "description": description,
                }
                serializer = EntityWriteSerializer(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "findings_assessment":
                data = {
                    "folder": str(folder.id),
                    "perimeter": str(default_perimeter.id),
                    "name": name,
                    "category": item.get("category", "pentest"),
                }
                serializer = FindingsAssessmentWriteSerializer(
                    data=data, context=context
                )
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "asset":
                data = {
                    "folder": str(folder.id),
                    "name": name,
                    "description": description,
                    "type": item.get("asset_type", "SP"),
                }
                serializer = AssetWriteSerializer(data=data, context=context)
                serializer.is_valid(raise_exception=True)
                obj = serializer.save()

            elif obj_type == "risk_scenario":
                # Deferred — processed in the second pass below
                deferred_scenarios.append(item)
                continue

            else:
                logger.warning("Unknown scaffolded object type", type=obj_type)
                continue

            if ref:
                object_refs[ref] = str(obj.id)

        # Second pass: create risk scenarios (they reference assets and risk assessments by ref)
        for item in deferred_scenarios:
            ref = item.get("ref")
            name = self._tr(item, "name")
            description = self._tr(item, "description")

            existing = self._find_existing(folder, "risk_scenario", name)
            if existing:
                logger.info(
                    "Reusing existing object",
                    type="risk_scenario",
                    name=name,
                    id=str(existing.id),
                )
                if ref:
                    object_refs[ref] = str(existing.id)
                continue

            ra_ref = item.get("risk_assessment_ref")
            ra_id = object_refs.get(ra_ref) if ra_ref else None
            if not ra_id:
                logger.warning(
                    "Risk scenario skipped: risk_assessment_ref not resolved",
                    name=name,
                    ref=ra_ref,
                )
                continue

            data = {
                "risk_assessment": ra_id,
                "name": name,
                "description": description,
                "treatment": item.get("treatment", "open"),
            }
            serializer = RiskScenarioWriteSerializer(data=data, context=context)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()

            # Link assets by ref
            asset_refs = item.get("asset_refs", [])
            asset_ids = [object_refs[r] for r in asset_refs if r in object_refs]
            if asset_ids:
                obj.assets.set(Asset.objects.filter(id__in=asset_ids))

            # Link threats by URN
            threat_urns = item.get("threat_urns", [])
            if threat_urns:
                threats = Threat.objects.filter(urn__in=threat_urns)
                obj.threats.set(threats)

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
                title=self._tr(step_def, "title"),
                description=self._tr(step_def, "description"),
                target_model=step_def.get("target_model"),
                target_ref=resolved_ref,
                status=PresetJourneyStep.Status.NOT_STARTED,
            )
