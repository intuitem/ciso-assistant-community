"""Domain export / import helpers extracted from FolderViewSet.

Exposes the logic used by the three DRF actions on FolderViewSet
(`export`, `import_domain`, `import_dummy_domain`) as module-level
functions so the ViewSet stays thin.
"""

from __future__ import annotations

import io
import json
import os
import re
import uuid
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Any, Dict, List, Tuple
from uuid import UUID

import structlog
from django.apps import apps
from django.contrib.auth.models import Permission
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.db.models import Q, QuerySet
from django.forms import ValidationError
from django.http import HttpResponse
from django.utils import timezone
from django.utils.text import slugify
from rest_framework.exceptions import PermissionDenied

from core.models import (
    AppliedControl,
    Asset,
    ComplianceAssessment,
    Evidence,
    EvidenceRevision,
    FindingsAssessment,
    Framework,
    LoadedLibrary,
    OrganisationObjective,
    Perimeter,
    Question,
    QuestionChoice,
    ReferenceControl,
    RequirementAssessment,
    RequirementNode,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    SecurityException,
    StoredLibrary,
    TaskTemplate,
    Terminology,
    Threat,
    Vulnerability,
)
from core.utils import compare_schema_versions
from ebios_rm.models import (
    AttackPath,
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    Stakeholder,
    StrategicScenario,
)
from iam.models import Folder, RoleAssignment, User
from tprm.models import Entity

from .serializers import ExportSerializer
from .utils import (
    build_dependency_graph,
    get_domain_export_objects,
    get_self_referencing_field,
    import_export_serializer_class,
    sort_objects_by_self_reference,
    topological_sort,
)

logger = structlog.get_logger(__name__)

BATCH_SIZE = 100  # Batch size for domain import validation / creation


# --------------------------------------------------------------------------- #
# Export                                                                      #
# --------------------------------------------------------------------------- #


def export_domain(
    instance: Folder, user: User, include_attachments: bool = True
) -> HttpResponse:
    """Build the domain export zip (JSON dump + evidence attachments)."""
    logger.info(
        "Starting domain export",
        domain_id=instance.id,
        domain_name=instance.name,
        include_attachments=include_attachments,
        user=user.username,
    )

    objects = get_domain_export_objects(instance)

    for model in objects.keys():
        if not RoleAssignment.is_access_allowed(
            user=user,
            perm=Permission.objects.get(codename=f"view_{model}"),
            folder=instance,
        ):
            logger.error(
                "User does not have permission to export object",
                user=user,
                model=model,
            )
            raise PermissionDenied({"error": "userDoesNotHavePermissionToExportDomain"})

    logger.debug(
        "Retrieved domain objects for export",
        object_types=list(objects.keys()),
        total_objects=sum(len(queryset) for queryset in objects.values()),
        objects_per_model={model: len(queryset) for model, queryset in objects.items()},
    )

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        if include_attachments:
            revisions = objects.get(
                "evidencerevision", EvidenceRevision.objects.none()
            ).filter(attachment__isnull=False)
            logger.info(
                "Processing evidence attachments",
                total_revisions=revisions.count(),
                domain_id=instance.id,
            )

            for revision in revisions:
                if revision.attachment and default_storage.exists(
                    revision.attachment.name
                ):
                    with default_storage.open(revision.attachment.name) as file:
                        file_content = file.read()
                        zipf.writestr(
                            os.path.join(
                                "attachments",
                                "evidence-revisions",
                                f"{revision.evidence_id}_v{revision.version}_"
                                f"{os.path.basename(revision.attachment.name)}",
                            ),
                            file_content,
                        )

        dumpfile_name = (
            f"ciso-assistant-{slugify(instance.name)}-domain-{timezone.now()}"
        )
        dump_data = ExportSerializer.dump_data(scope=[*objects.values()])

        logger.debug(
            "Adding JSON dump to zip",
            json_size=len(json.dumps(dump_data).encode("utf-8")),
            filename=f"{dumpfile_name}.json",
        )

        zipf.writestr("data.json", json.dumps(dump_data).encode("utf-8"))

    zip_buffer.seek(0)
    final_size = len(zip_buffer.getvalue())

    response = HttpResponse(zip_buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{dumpfile_name}.zip"'

    logger.info(
        "Domain export completed successfully",
        domain_id=instance.id,
        domain_name=instance.name,
        zip_size=final_size,
        filename=f"{dumpfile_name}.zip",
    )

    return response


# --------------------------------------------------------------------------- #
# Import                                                                      #
# --------------------------------------------------------------------------- #


def process_uploaded_file(dump_file: str | Path) -> Any:
    """Parse an uploaded domain zip and return its JSON payload."""
    if not zipfile.is_zipfile(dump_file):
        logger.error("Invalid ZIP file format")
        raise ValidationError({"file": "invalidZipFileFormat"})

    with zipfile.ZipFile(dump_file, mode="r") as zipf:
        if "data.json" not in zipf.namelist():
            logger.error(
                "No data.json file found in uploaded file", files=zipf.namelist()
            )
            raise ValidationError({"file": "noDataJsonFileFound"})
        infolist = zipf.infolist()
        directories = list(set([Path(f.filename).parent.name for f in infolist]))
        decompressed_data = zipf.read("data.json")
        if isinstance(decompressed_data, bytes):
            decompressed_data = decompressed_data.decode("utf-8")
        try:
            json_dump = json.loads(decompressed_data)
            import_version = json_dump["meta"]["media_version"]
            schema_version = json_dump["meta"].get("schema_version")
        except json.JSONDecodeError:
            logger.error("Invalid JSON format in uploaded file", exc_info=True)
            raise
        if "objects" not in json_dump:
            raise ValidationError("badly formatted json")

        try:
            schema_version_int = int(schema_version)
        except (ValueError, TypeError) as e:
            logger.error(
                "Invalid schema version format",
                schema_version=schema_version,
                exc_info=e,
            )
            raise ValidationError({"error": "invalidSchemaVersionFormat"})
        compare_schema_versions(schema_version_int, import_version)

        # Collect every file living under `attachments/` (including the
        # evidence-revisions/ subdir used by the current exporter).
        attachments = [
            f
            for f in infolist
            if not f.is_dir() and "attachments" in Path(f.filename).parts
        ]
        if attachments:
            logger.info(
                "Attachments found in uploaded file",
                attachments_count=len(attachments),
            )
            revision_re = re.compile(r"^([0-9a-fA-F\-]{36})_v(\d+)_(.+)$")
            for attachment in attachments:
                try:
                    content = zipf.read(attachment)
                    parts = Path(attachment.filename).parts
                    zip_name = parts[-1]

                    if "evidence-revisions" in parts:
                        # Exporter path: attachments/evidence-revisions/
                        #   {evidence_uuid}_v{version}_{basename}
                        m = revision_re.match(zip_name)
                        if not m:
                            logger.warning(
                                "Skipping attachment with unrecognized filename",
                                filename=zip_name,
                            )
                            continue
                        evidence_uuid, version_str, basename = m.groups()
                        new_name = default_storage.save(basename, io.BytesIO(content))
                        evidence_hash = sha256(str(evidence_uuid).encode()).hexdigest()[
                            :12
                        ]
                        version = int(version_str)
                        for x in json_dump["objects"]:
                            if (
                                x["model"] == "core.evidencerevision"
                                and x["fields"].get("evidence") == evidence_hash
                                and int(x["fields"].get("version", 0)) == version
                            ):
                                x["fields"]["attachment"] = new_name
                    else:
                        # Legacy layout: attachments/<basename> tied to
                        # core.evidence.attachment
                        new_name = default_storage.save(zip_name, io.BytesIO(content))
                        if new_name != zip_name:
                            for x in json_dump["objects"]:
                                if (
                                    x["model"] == "core.evidence"
                                    and x["fields"].get("attachment") == zip_name
                                ):
                                    x["fields"]["attachment"] = new_name

                except Exception:
                    logger.error("Error extracting attachment", exc_info=True)

    return json_dump


def get_models_map(objects: List[dict]) -> Dict[str, type[models.Model]]:
    """Build a map of model names to model classes."""
    model_names = {obj["model"] for obj in objects}
    return {name: apps.get_model(name) for name in model_names}


def resolve_dependencies(
    all_models: List[type[models.Model]],
) -> List[type[models.Model]]:
    """Resolve model dependencies and detect cycles."""
    logger.debug("Resolving model dependencies", all_models=all_models)

    graph = build_dependency_graph(all_models)

    logger.debug("Dependency graph", graph=graph)

    try:
        return topological_sort(graph)
    except ValueError as e:
        logger.error("Cyclic dependency detected", error=str(e))
        raise ValidationError({"error": "Cyclic dependency detected"})


def import_terminologies(
    names: str | List[str] | None,
    field_path: Terminology.FieldPath,
) -> QuerySet[Terminology] | Terminology | None:
    """Ensure requested terminologies exist and are visible."""
    if not names:
        return None

    single_value = False
    if isinstance(names, str):
        names = [names]
        single_value = True

    existing = Terminology.objects.filter(name__in=names, field_path=field_path)
    existing_names = set(existing.values_list("name", flat=True))

    missing_names = set(names) - existing_names
    if missing_names:
        Terminology.objects.bulk_create(
            [
                Terminology(name=name, field_path=field_path, is_visible=True)
                for name in missing_names
            ],
            ignore_conflicts=True,
        )

    Terminology.objects.filter(
        name__in=names, field_path=field_path, is_visible=False
    ).update(is_visible=True)

    result_qs = Terminology.objects.filter(name__in=names, field_path=field_path)

    if single_value:
        return result_qs.first()
    return result_qs


def import_objects(
    parsed_data: dict,
    domain_name: str,
    load_missing_libraries: bool,
    user: User,
) -> dict[str, str]:
    """Import and validate domain objects using their ImportExport serializers."""
    validation_errors: list = []
    required_libraries: list = []
    missing_libraries: list = []
    link_dump_database_ids: dict = {}

    objects = parsed_data.get("objects")
    if not objects:
        logger.error("No objects found in the dump")
        raise ValidationError({"error": "No objects found in the dump"})

    try:
        models_map = get_models_map(objects)
        if Folder in models_map.values():
            logger.error("Dump contains a domain")
            raise ValidationError({"error": "Dump contains a domain"})

        error_dict = {}
        for model in filter(
            lambda x: x not in [RequirementAssessment], models_map.values()
        ):
            if not RoleAssignment.is_access_allowed(
                user=user,
                perm=Permission.objects.get(codename=f"add_{model._meta.model_name}"),
                folder=Folder.get_root_folder(),
            ):
                error_dict[model._meta.model_name] = "permission_denied"
        if error_dict:
            logger.error(
                "User does not have permission to import objects",
                error_dict=error_dict,
            )
            raise PermissionDenied()

        creation_order = resolve_dependencies(list(models_map.values()))

        logger.debug("Resolved creation order", creation_order=creation_order)
        logger.debug("Starting objects validation", objects_count=len(objects))

        for model in creation_order:
            validate_model_objects(
                model=model,
                objects=objects,
                validation_errors=validation_errors,
                required_libraries=required_libraries,
            )

        logger.debug("required_libraries", required_libraries=required_libraries)

        if validation_errors:
            logger.error(
                "Failed to validate objects", validation_errors=validation_errors
            )
            raise ValidationError({"validation_errors": validation_errors})

        with transaction.atomic():
            base_folder = Folder.objects.create(
                name=domain_name,
                content_type=Folder.ContentType.DOMAIN,
                create_iam_groups=True,
            )
            link_dump_database_ids["base_folder"] = base_folder
            Folder.create_default_ug_and_ra(base_folder)

            for library in required_libraries:
                if not LoadedLibrary.objects.filter(
                    urn=library["urn"], version=library["version"]
                ).exists():
                    if (
                        StoredLibrary.objects.filter(
                            urn=library["urn"], version__gte=library["version"]
                        ).exists()
                        and load_missing_libraries
                    ):
                        StoredLibrary.objects.get(
                            urn=library["urn"], version__gte=library["version"]
                        ).load()
                    else:
                        missing_libraries.append(library)

            logger.debug("missing_libraries", missing_libraries=missing_libraries)

            if missing_libraries:
                logger.warning(f"Missing libraries: {missing_libraries}")
                raise ValidationError({"missing_libraries": missing_libraries})

            logger.info(
                "Starting objects creation",
                objects_count=len(objects),
                creation_order=creation_order,
            )

            for model in creation_order:
                create_model_objects(
                    model=model,
                    objects=objects,
                    link_dump_database_ids=link_dump_database_ids,
                )

            resolve_security_exception_m2m(objects, link_dump_database_ids)

        return {"message": "Import successful"}

    except ValidationError as e:
        logger.error(f"error: {e}")
        raise
    except Exception as e:
        logger.exception(f"Failed to import objects: {str(e)}")
        raise ValidationError({"non_field_errors": "errorOccuredDuringImport"})


def validate_model_objects(
    model: type[models.Model],
    objects: List[dict],
    validation_errors: list,
    required_libraries: list,
) -> None:
    """Validate all objects for a model before creation."""
    model_name = f"{model._meta.app_label}.{model._meta.model_name}"
    model_objects = [obj for obj in objects if obj["model"] == model_name]

    if not model_objects:
        return

    for i in range(0, len(model_objects), BATCH_SIZE):
        batch = model_objects[i : i + BATCH_SIZE]
        validate_batch(
            model=model,
            batch=batch,
            validation_errors=validation_errors,
            required_libraries=required_libraries,
        )


def validate_batch(
    model: type[models.Model],
    batch: List[dict],
    validation_errors: list,
    required_libraries: list,
) -> None:
    """Validate a batch of objects."""
    model_name = f"{model._meta.app_label}.{model._meta.model_name}"

    for obj in batch:
        obj_id = obj.get("id")
        fields = obj.get("fields", {}).copy()

        try:
            if model == LoadedLibrary:
                required_libraries.append(
                    {"urn": fields["urn"], "version": fields["version"]}
                )
                logger.info("Adding library to required libraries", urn=fields["urn"])
                continue
            if fields.get("library"):
                continue

            serializer_class = import_export_serializer_class(model)
            serializer = serializer_class(data=fields)

            if not serializer.is_valid():
                validation_errors.append(
                    {
                        "model": model_name,
                        "id": obj_id,
                        "errors": serializer.errors,
                    }
                )

        except Exception as e:
            logger.error(
                f"Error validating object {obj_id} in {model_name}: {str(e)}",
                exc_info=True,
            )
            validation_errors.append(
                {
                    "model": model_name,
                    "id": obj_id,
                    "errors": [str(e)],
                }
            )


def create_model_objects(
    model: type[models.Model],
    objects: List[dict],
    link_dump_database_ids: dict[str, Any],
) -> None:
    """Create all objects for a model after validation."""
    logger.debug("Creating objects for model", model=model)

    model_name = f"{model._meta.app_label}.{model._meta.model_name}"
    model_objects = [obj for obj in objects if obj["model"] == model_name]

    logger.debug("Model objects", model=model, count=len(model_objects))

    if not model_objects:
        return

    self_ref_field = get_self_referencing_field(model)
    if self_ref_field:
        try:
            model_objects = sort_objects_by_self_reference(
                model_objects, self_ref_field
            )
        except ValueError as e:
            logger.error(f"Cyclic dependency detected in {model_name}: {str(e)}")
            raise ValidationError(
                {"error": f"Cyclic dependency detected in {model_name}"}
            )

    for i in range(0, len(model_objects), BATCH_SIZE):
        batch = model_objects[i : i + BATCH_SIZE]
        create_batch(
            model=model,
            batch=batch,
            link_dump_database_ids=link_dump_database_ids,
        )


def create_batch(
    model: type[models.Model],
    batch: List[dict],
    link_dump_database_ids: dict[str, Any],
) -> None:
    """Create a batch of objects with proper relationship handling."""
    with transaction.atomic():
        try:
            objects_creation_data = []

            for obj in batch:
                obj_id = obj.get("id")
                fields = obj.get("fields", {}).copy()

                if fields.get("library") or model == LoadedLibrary:
                    logger.info(f"Skipping creation of library object {obj_id}")
                    link_dump_database_ids[obj_id] = fields.get("urn")
                    continue

                if fields.get("folder"):
                    fields["folder"] = link_dump_database_ids.get("base_folder")

                many_to_many_map_ids: dict = {}
                fields = process_model_relationships(
                    model=model,
                    fields=fields,
                    link_dump_database_ids=link_dump_database_ids,
                    many_to_many_map_ids=many_to_many_map_ids,
                )

                try:
                    model(**fields).clean()
                except ValidationError as e:
                    for field, error in e.error_dict.items():
                        fields[field] = f"{fields[field]} {uuid.uuid4()}"

                logger.debug("Creating object", fields=fields)
                objects_creation_data.append(
                    {
                        "id": obj_id,
                        "fields": fields,
                        "many_to_many_map_ids": many_to_many_map_ids,
                    }
                )

            is_requirement_assessment = model is RequirementAssessment
            has_save_override = model.save is not models.Model.save

            if has_save_override and not is_requirement_assessment:
                created_objects = []
                for object_creation_data in objects_creation_data:
                    obj_created = model.objects.create(**object_creation_data["fields"])
                    created_objects.append(obj_created)
            else:
                objects_to_create = [
                    model(**ocd["fields"]) for ocd in objects_creation_data
                ]
                created_objects = model.objects.bulk_create(objects_to_create)

            if is_requirement_assessment:
                seen_cas = set()
                for ra in created_objects:
                    ca_id = ra.compliance_assessment_id
                    if ca_id not in seen_cas:
                        seen_cas.add(ca_id)
                        ra.trigger_compliance_assessment_update_hooks()

            for obj_created, object_creation_data in zip(
                created_objects, objects_creation_data
            ):
                if obj_created.id is None:
                    obj_created.refresh_from_db()

                obj_id = object_creation_data["id"]
                link_dump_database_ids[obj_id] = obj_created.id

                many_to_many_map_ids = object_creation_data["many_to_many_map_ids"]
                set_many_to_many_relations(
                    model=model,
                    obj=obj_created,
                    many_to_many_map_ids=many_to_many_map_ids,
                )

        except Exception as e:
            logger.error(
                "Error creating object batch",
                model=model._meta.model_name,
                exc_info=True,
            )
            raise ValidationError(f"Error creating {model._meta.model_name}: {str(e)}")


def process_model_relationships(
    model: type[models.Model],
    fields: dict[str, Any],
    link_dump_database_ids: dict[str, Any],
    many_to_many_map_ids: dict[str, QuerySet | List[UUID | str] | None],
) -> dict[str, Any]:
    """Resolve FK references and split out M2M fields for post-create handling."""

    def get_mapped_ids(
        ids: List[str], link_dump_database_ids: Dict[str, str]
    ) -> List[str]:
        return [
            link_dump_database_ids[id] for id in ids if id in link_dump_database_ids
        ]

    model_name = model._meta.model_name
    _fields = fields.copy()

    logger.debug("Processing model relationships", model=model_name, _fields=_fields)

    match model_name:
        case "asset":
            many_to_many_map_ids["parent_ids"] = get_mapped_ids(
                _fields.pop("parent_assets", []), link_dump_database_ids
            )

        case "riskassessment":
            _fields["perimeter"] = Perimeter.objects.filter(
                id=link_dump_database_ids.get(_fields["perimeter"])
            ).first()
            _fields["risk_matrix"] = RiskMatrix.objects.get(
                urn=_fields.get("risk_matrix")
            )
            _fields["ebios_rm_study"] = (
                EbiosRMStudy.objects.get(
                    id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                )
                if _fields.get("ebios_rm_study")
                else None
            )

        case "complianceassessment":
            _fields["perimeter"] = Perimeter.objects.get(
                id=link_dump_database_ids.get(_fields["perimeter"])
            )
            _fields["framework"] = Framework.objects.get(urn=_fields["framework"])

        case "appliedcontrol":
            many_to_many_map_ids["evidence_ids"] = get_mapped_ids(
                _fields.pop("evidences", []), link_dump_database_ids
            )
            many_to_many_map_ids["objective_ids"] = get_mapped_ids(
                _fields.pop("objectives", []), link_dump_database_ids
            )
            ref_control_id = link_dump_database_ids.get(_fields["reference_control"])
            _fields["reference_control"] = ReferenceControl.objects.filter(
                urn=ref_control_id
            ).first()

        case "evidence":
            many_to_many_map_ids["owner_ids"] = get_mapped_ids(
                _fields.pop("owner", []), link_dump_database_ids
            )

        case "evidencerevision":
            _fields.pop("size", None)
            _fields.pop("attachment_hash", None)
            _fields["evidence"] = Evidence.objects.get(
                id=link_dump_database_ids.get(_fields["evidence"])
            )

        case "requirementassessment":
            logger.debug("Looking for requirement", urn=_fields.get("requirement"))
            _fields["requirement"] = RequirementNode.objects.get(
                urn=_fields.get("requirement")
            )
            _fields["compliance_assessment"] = ComplianceAssessment.objects.get(
                id=link_dump_database_ids.get(_fields["compliance_assessment"])
            )
            _fields.pop("answers", None)
            many_to_many_map_ids.update(
                {
                    "applied_controls": get_mapped_ids(
                        _fields.pop("applied_controls", []), link_dump_database_ids
                    ),
                    "evidence_ids": get_mapped_ids(
                        _fields.pop("evidences", []), link_dump_database_ids
                    ),
                }
            )

        case "answer":
            _fields["requirement_assessment"] = RequirementAssessment.objects.get(
                id=link_dump_database_ids.get(_fields["requirement_assessment"])
            )
            question = Question.objects.get(urn=_fields.get("question"))
            ra = _fields["requirement_assessment"]
            if question.requirement_node_id != ra.requirement_id:
                raise ValidationError(
                    f"Question {question.urn} does not belong to requirement {ra.requirement_id}"
                )
            _fields["question"] = question

            choice_urns = _fields.pop("selected_choices_urns", None)
            if choice_urns:
                many_to_many_map_ids["selected_choices_urns"] = choice_urns

        case "vulnerability":
            many_to_many_map_ids["applied_controls"] = get_mapped_ids(
                _fields.pop("applied_controls", []), link_dump_database_ids
            )

        case "riskscenario":
            _fields["risk_assessment"] = RiskAssessment.objects.get(
                id=link_dump_database_ids.get(_fields["risk_assessment"])
            )
            _fields["risk_origin"] = import_terminologies(
                _fields.get("risk_origin"), Terminology.FieldPath.ROTO_RISK_ORIGIN
            )
            # Keys here must match those read in set_many_to_many_relations.
            # (Previously derived with `.rstrip('s')`, which strips *chars*,
            # not the suffix — silently dropping vulnerabilities /
            # applied_controls / existing_applied_controls.)
            related_fields = {
                "threats": "threat_ids",
                "vulnerabilities": "vulnerability_ids",
                "assets": "asset_ids",
                "applied_controls": "applied_control_ids",
                "existing_applied_controls": "existing_applied_control_ids",
                "qualifications": "qualification_ids",
            }
            for field, map_key in related_fields.items():
                if field == "qualifications":
                    many_to_many_map_ids[map_key] = import_terminologies(
                        _fields.pop(field, []), Terminology.FieldPath.QUALIFICATIONS
                    )
                else:
                    many_to_many_map_ids[map_key] = get_mapped_ids(
                        _fields.pop(field, []), link_dump_database_ids
                    )

        case "entity":
            _fields.pop("owned_folders", None)
            many_to_many_map_ids["relationship_ids"] = import_terminologies(
                _fields.pop("relationship", []),
                Terminology.FieldPath.ENTITY_RELATIONSHIP,
            )

        case "ebiosrmstudy":
            _fields.update(
                {
                    "risk_matrix": RiskMatrix.objects.get(
                        urn=_fields.get("risk_matrix")
                    ),
                    "reference_entity": Entity.objects.get(
                        id=link_dump_database_ids.get(_fields["reference_entity"])
                    ),
                }
            )
            many_to_many_map_ids.update(
                {
                    "asset_ids": get_mapped_ids(
                        _fields.pop("assets", []), link_dump_database_ids
                    ),
                    "compliance_assessment_ids": get_mapped_ids(
                        _fields.pop("compliance_assessments", []),
                        link_dump_database_ids,
                    ),
                }
            )

        case "fearedevent":
            _fields["ebios_rm_study"] = EbiosRMStudy.objects.get(
                id=link_dump_database_ids.get(_fields["ebios_rm_study"])
            )
            many_to_many_map_ids.update(
                {
                    "qualification_ids": import_terminologies(
                        _fields.pop("qualifications", []),
                        Terminology.FieldPath.QUALIFICATIONS,
                    ),
                    "asset_ids": get_mapped_ids(
                        _fields.pop("assets", []), link_dump_database_ids
                    ),
                }
            )

        case "roto":
            _fields["ebios_rm_study"] = EbiosRMStudy.objects.get(
                id=link_dump_database_ids.get(_fields["ebios_rm_study"])
            )
            many_to_many_map_ids["feared_event_ids"] = get_mapped_ids(
                _fields.pop("feared_events", []), link_dump_database_ids
            )
            _fields["risk_origin"] = import_terminologies(
                _fields["risk_origin"],
                Terminology.FieldPath.ROTO_RISK_ORIGIN,
            )

        case "stakeholder":
            _fields.update(
                {
                    "ebios_rm_study": EbiosRMStudy.objects.get(
                        id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                    ),
                    "entity": Entity.objects.get(
                        id=link_dump_database_ids.get(_fields["entity"])
                    ),
                }
            )
            _fields["category"] = import_terminologies(
                _fields["category"],
                Terminology.FieldPath.ENTITY_RELATIONSHIP,
            )
            many_to_many_map_ids["applied_controls"] = get_mapped_ids(
                _fields.pop("applied_controls", []), link_dump_database_ids
            )

        case "strategicscenario":
            _fields.update(
                {
                    "ebios_rm_study": EbiosRMStudy.objects.get(
                        id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                    ),
                    "ro_to_couple": RoTo.objects.get(
                        id=link_dump_database_ids.get(_fields["ro_to_couple"])
                    ),
                }
            )

        case "attackpath":
            _fields.update(
                {
                    "ebios_rm_study": EbiosRMStudy.objects.get(
                        id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                    ),
                    "strategic_scenario": StrategicScenario.objects.get(
                        id=link_dump_database_ids.get(_fields["strategic_scenario"])
                    ),
                }
            )
            many_to_many_map_ids["stakeholder_ids"] = get_mapped_ids(
                _fields.pop("stakeholders", []), link_dump_database_ids
            )

        case "operationalscenario":
            _fields.update(
                {
                    "ebios_rm_study": EbiosRMStudy.objects.get(
                        id=link_dump_database_ids.get(_fields["ebios_rm_study"])
                    ),
                    "attack_path": AttackPath.objects.get(
                        id=link_dump_database_ids.get(_fields["attack_path"])
                    ),
                }
            )
            many_to_many_map_ids["threat_ids"] = get_mapped_ids(
                _fields.pop("threats", []), link_dump_database_ids
            )

        case "findingsassessment":
            perimeter_id = link_dump_database_ids.get(_fields.get("perimeter"))
            _fields["perimeter"] = (
                Perimeter.objects.filter(id=perimeter_id).first()
                if perimeter_id
                else None
            )
            many_to_many_map_ids["evidence_ids"] = get_mapped_ids(
                _fields.pop("evidences", []), link_dump_database_ids
            )

        case "finding":
            _fields["findings_assessment"] = FindingsAssessment.objects.get(
                id=link_dump_database_ids.get(_fields["findings_assessment"])
            )
            for field in (
                "threats",
                "vulnerabilities",
                "reference_controls",
                "applied_controls",
                "evidences",
            ):
                many_to_many_map_ids[f"{field}_ids"] = get_mapped_ids(
                    _fields.pop(field, []), link_dump_database_ids
                )

        case "riskacceptance":
            many_to_many_map_ids["risk_scenarios_ids"] = get_mapped_ids(
                _fields.pop("risk_scenarios", []), link_dump_database_ids
            )

        case "incident":
            for field in ("threats", "assets", "entities"):
                many_to_many_map_ids[f"{field}_ids"] = get_mapped_ids(
                    _fields.pop(field, []), link_dump_database_ids
                )

        case "campaign":
            many_to_many_map_ids["framework_urns"] = _fields.pop("frameworks", [])
            many_to_many_map_ids["perimeters_ids"] = get_mapped_ids(
                _fields.pop("perimeters", []), link_dump_database_ids
            )

        case "tasktemplate":
            for field in (
                "evidences",
                "assets",
                "applied_controls",
                "compliance_assessments",
                "risk_assessments",
                "findings_assessment",
            ):
                many_to_many_map_ids[f"{field}_ids"] = get_mapped_ids(
                    _fields.pop(field, []), link_dump_database_ids
                )

        case "tasknode":
            tt_id = link_dump_database_ids.get(_fields.get("task_template"))
            _fields["task_template"] = (
                TaskTemplate.objects.filter(id=tt_id).first() if tt_id else None
            )
            many_to_many_map_ids["evidences_ids"] = get_mapped_ids(
                _fields.pop("evidences", []), link_dump_database_ids
            )

        case "securityexception":
            # Reverse M2M targets (Asset/AppliedControl/etc.) may be created
            # after SecurityException in the topo sort, so we only drop the
            # hash lists here and resolve them in a post-pass once every
            # object exists. See resolve_security_exception_m2m.
            for field in (
                "assets",
                "applied_controls",
                "vulnerabilities",
                "risk_scenarios",
                "requirement_assessments",
            ):
                _fields.pop(field, None)

    return _fields


def set_many_to_many_relations(
    model: type[models.Model],
    obj: models.Model,
    many_to_many_map_ids: dict[str, QuerySet | List[UUID | str] | None],
) -> None:
    """Set M2M relations on a freshly-created object."""
    model_name = model._meta.model_name

    match model_name:
        case "asset":
            if parent_ids := many_to_many_map_ids.get("parent_ids"):
                logger.debug("Setting parent assets", asset=obj, parent_ids=parent_ids)
                obj.parent_assets.set(Asset.objects.filter(id__in=parent_ids))

        case "appliedcontrol":
            if evidence_ids := many_to_many_map_ids.get("evidence_ids"):
                obj.evidences.set(Evidence.objects.filter(id__in=evidence_ids))

            if objectives_ids := many_to_many_map_ids.get("objective_ids"):
                obj.objectives.set(
                    OrganisationObjective.objects.filter(id__in=objectives_ids)
                )

        case "requirementassessment":
            if applied_control_ids := many_to_many_map_ids.get("applied_controls"):
                obj.applied_controls.set(
                    AppliedControl.objects.filter(id__in=applied_control_ids)
                )
            if evidence_ids := many_to_many_map_ids.get("evidence_ids"):
                obj.evidences.set(Evidence.objects.filter(id__in=evidence_ids))

        case "vulnerability":
            if applied_control_ids := many_to_many_map_ids.get("applied_controls"):
                obj.applied_controls.set(
                    AppliedControl.objects.filter(id__in=applied_control_ids)
                )

        case "riskscenario":
            if threat_ids := many_to_many_map_ids.get("threat_ids"):
                uuids, urns = split_uuids_urns(threat_ids)
                obj.threats.set(
                    Threat.objects.filter(Q(id__in=uuids) | Q(urn__in=urns))
                )
            if qualification_ids := many_to_many_map_ids.get("qualification_ids"):
                obj.qualifications.set(qualification_ids)

            for field, model_class in {
                "vulnerability_ids": (Vulnerability, "vulnerabilities"),
                "asset_ids": (Asset, "assets"),
                "applied_control_ids": (AppliedControl, "applied_controls"),
                "existing_applied_control_ids": (
                    AppliedControl,
                    "existing_applied_controls",
                ),
            }.items():
                if ids := many_to_many_map_ids.get(field):
                    getattr(obj, model_class[1]).set(
                        model_class[0].objects.filter(id__in=ids)
                    )

        case "ebiosrmstudy":
            if asset_ids := many_to_many_map_ids.get("asset_ids"):
                obj.assets.set(Asset.objects.filter(id__in=asset_ids))
            if compliance_assessment_ids := many_to_many_map_ids.get(
                "compliance_assessment_ids"
            ):
                obj.compliance_assessments.set(
                    ComplianceAssessment.objects.filter(
                        id__in=compliance_assessment_ids
                    )
                )

        case "fearedevent":
            if qualification_ids := many_to_many_map_ids.get("qualification_ids"):
                obj.qualifications.set(qualification_ids)

            if asset_ids := many_to_many_map_ids.get("asset_ids"):
                obj.assets.set(Asset.objects.filter(id__in=asset_ids))

        case "roto":
            if feared_event_ids := many_to_many_map_ids.get("feared_event_ids"):
                obj.feared_events.set(
                    FearedEvent.objects.filter(id__in=feared_event_ids)
                )

        case "stakeholder":
            if applied_control_ids := many_to_many_map_ids.get("applied_controls"):
                obj.applied_controls.set(
                    AppliedControl.objects.filter(id__in=applied_control_ids)
                )

        case "attackpath":
            if stakeholder_ids := many_to_many_map_ids.get("stakeholder_ids"):
                obj.stakeholders.set(Stakeholder.objects.filter(id__in=stakeholder_ids))

        case "operationalscenario":
            if threat_ids := many_to_many_map_ids.get("threat_ids"):
                uuids, urns = split_uuids_urns(threat_ids)
                obj.threats.set(
                    Threat.objects.filter(Q(id__in=uuids) | Q(urn__in=urns))
                )

        case "answer":
            if urns := many_to_many_map_ids.get("selected_choices_urns"):
                if obj.question.type not in (
                    Question.Type.UNIQUE_CHOICE,
                    Question.Type.MULTIPLE_CHOICE,
                ):
                    logger.warning(
                        "Answer import: choice identifiers (selected_choices_ref_ids/selected_choices_urns) "
                        "provided for non-choice question %s",
                        obj.question.urn,
                    )
                else:
                    choices = list(
                        QuestionChoice.objects.filter(
                            question=obj.question, urn__in=urns
                        )
                    )
                    found_urns = {c.urn for c in choices}
                    missing = set(urns) - found_urns
                    if missing:
                        logger.warning(
                            "Answer import: could not resolve choice urns %s "
                            "for question %s",
                            missing,
                            obj.question.urn,
                        )
                    if (
                        obj.question.type == Question.Type.UNIQUE_CHOICE
                        and len(choices) > 1
                    ):
                        logger.warning(
                            "Answer import: multiple choices provided for "
                            "unique_choice question %s, keeping only first",
                            obj.question.urn,
                        )
                        choices = choices[:1]
                    obj.selected_choices.set(choices)

        case "entity":
            if relationship_ids := many_to_many_map_ids.get("relationship_ids"):
                obj.relationship.set(relationship_ids)

        case "findingsassessment":
            if evidence_ids := many_to_many_map_ids.get("evidence_ids"):
                obj.evidences.set(Evidence.objects.filter(id__in=evidence_ids))

        case "finding":
            if threat_ids := many_to_many_map_ids.get("threats_ids"):
                uuids, urns = split_uuids_urns(threat_ids)
                obj.threats.set(
                    Threat.objects.filter(Q(id__in=uuids) | Q(urn__in=urns))
                )
            if rc_ids := many_to_many_map_ids.get("reference_controls_ids"):
                uuids, urns = split_uuids_urns(rc_ids)
                obj.reference_controls.set(
                    ReferenceControl.objects.filter(Q(id__in=uuids) | Q(urn__in=urns))
                )
            if vuln_ids := many_to_many_map_ids.get("vulnerabilities_ids"):
                obj.vulnerabilities.set(Vulnerability.objects.filter(id__in=vuln_ids))
            if ac_ids := many_to_many_map_ids.get("applied_controls_ids"):
                obj.applied_controls.set(AppliedControl.objects.filter(id__in=ac_ids))
            if evidence_ids := many_to_many_map_ids.get("evidences_ids"):
                obj.evidences.set(Evidence.objects.filter(id__in=evidence_ids))

        case "riskacceptance":
            if rs_ids := many_to_many_map_ids.get("risk_scenarios_ids"):
                obj.risk_scenarios.set(RiskScenario.objects.filter(id__in=rs_ids))

        case "incident":
            if threat_ids := many_to_many_map_ids.get("threats_ids"):
                uuids, urns = split_uuids_urns(threat_ids)
                obj.threats.set(
                    Threat.objects.filter(Q(id__in=uuids) | Q(urn__in=urns))
                )
            if asset_ids := many_to_many_map_ids.get("assets_ids"):
                obj.assets.set(Asset.objects.filter(id__in=asset_ids))
            if entity_ids := many_to_many_map_ids.get("entities_ids"):
                obj.entities.set(Entity.objects.filter(id__in=entity_ids))

        case "campaign":
            if framework_urns := many_to_many_map_ids.get("framework_urns"):
                obj.frameworks.set(Framework.objects.filter(urn__in=framework_urns))
            if perimeter_ids := many_to_many_map_ids.get("perimeters_ids"):
                obj.perimeters.set(Perimeter.objects.filter(id__in=perimeter_ids))

        case "tasktemplate":
            for key, mcls, attr in (
                ("evidences_ids", Evidence, "evidences"),
                ("assets_ids", Asset, "assets"),
                ("applied_controls_ids", AppliedControl, "applied_controls"),
                (
                    "compliance_assessments_ids",
                    ComplianceAssessment,
                    "compliance_assessments",
                ),
                ("risk_assessments_ids", RiskAssessment, "risk_assessments"),
                (
                    "findings_assessment_ids",
                    FindingsAssessment,
                    "findings_assessment",
                ),
            ):
                if ids := many_to_many_map_ids.get(key):
                    getattr(obj, attr).set(mcls.objects.filter(id__in=ids))

        case "tasknode":
            if evidence_ids := many_to_many_map_ids.get("evidences_ids"):
                obj.evidences.set(Evidence.objects.filter(id__in=evidence_ids))


def resolve_security_exception_m2m(
    objects: List[dict], link_dump_database_ids: dict[str, Any]
) -> None:
    """Post-pass: set SecurityException reverse M2Ms once every target exists.

    These relations (assets, applied_controls, vulnerabilities, risk_scenarios,
    requirement_assessments) are defined on the other side, so the topological
    sort doesn't guarantee SE is created last; we resolve them here instead.
    """
    se_model_name = "core.securityexception"
    reverse_m2m = (
        ("assets", Asset),
        ("applied_controls", AppliedControl),
        ("vulnerabilities", Vulnerability),
        ("risk_scenarios", RiskScenario),
        ("requirement_assessments", RequirementAssessment),
    )
    for obj in objects:
        if obj["model"] != se_model_name:
            continue
        se_db_id = link_dump_database_ids.get(obj["id"])
        if not se_db_id:
            continue
        try:
            se = SecurityException.objects.get(id=se_db_id)
        except SecurityException.DoesNotExist:
            continue
        fields = obj.get("fields", {})
        for field_name, model_cls in reverse_m2m:
            hash_ids = fields.get(field_name) or []
            ids = [
                link_dump_database_ids[h]
                for h in hash_ids
                if h in link_dump_database_ids
            ]
            if ids:
                getattr(se, field_name).set(model_cls.objects.filter(id__in=ids))


def split_uuids_urns(ids: List[str]) -> Tuple[List[UUID], List[str]]:
    """Split a list of strings into UUIDs and URNs."""
    uuids: list[UUID] = []
    urns: list[str] = []
    for item in ids:
        try:
            uuids.append(UUID(str(item)))
        except ValueError:
            urns.append(item)
    return uuids, urns
