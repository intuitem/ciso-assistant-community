from typing import Iterable

import django.apps
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from django.db.models import Model, Q
from django.db.models.deletion import Collector
from collections import defaultdict

from iam.models import Folder
from rest_framework.exceptions import ValidationError
from typing import List, Type, Set, Dict, Optional

from core.models import (
    Asset,
    AppliedControl,
    Evidence,
    Framework,
    Project,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    ComplianceAssessment,
    RequirementAssessment,
    Vulnerability,
    Threat,
    ReferenceControl,
    LoadedLibrary,
)

from ebios_rm.models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    OperationalScenario,
    Stakeholder,
    StrategicScenario,
    AttackPath,
)

from tprm.models import Entity

from core.serializers import (
    FolderImportExportSerializer,
    AssetImportExportSerializer,
    AppliedControlImportExportSerializer,
    EvidenceImportExportSerializer,
    ProjectImportExportSerializer,
    RiskAssessmentImportExportSerializer,
    RiskScenarioImportExportSerializer,
    ComplianceAssessmentImportExportSerializer,
    RequirementAssessmentImportExportSerializer,
    VulnerabilityImportExportSerializer,
    ThreatImportExportSerializer,
    ReferenceControlImportExportSerializer,
    FrameworkImportExportSerializer,
    RiskMatrixImportExportSerializer,
)

from ebios_rm.serializers import (
    EbiosRMStudyImportExportSerializer,
    FearedEventImportExportSerializer,
    RoToImportExportSerializer,
    OperationalScenarioImportExportSerializer,
    StakeholderImportExportSerializer,
    StrategicScenarioImportExportSerializer,
    AttackPathImportExportSerializer,
)

from tprm.serializers import EntityImportExportSerializer

from django.db import models
from library.serializers import LoadedLibraryImportExportSerializer

from core.models import (
    Asset,
    AppliedControl,
    Evidence,
    Framework,
    Project,
    RiskAssessment,
    RiskMatrix,
    RiskScenario,
    ComplianceAssessment,
    RequirementAssessment,
    Vulnerability,
    Threat,
    ReferenceControl,
    LoadedLibrary,
)

from ebios_rm.models import (
    EbiosRMStudy,
    FearedEvent,
    RoTo,
    OperationalScenario,
    Stakeholder,
    StrategicScenario,
    AttackPath,
)

from tprm.models import Entity

from core.serializers import (
    FolderImportExportSerializer,
    AssetImportExportSerializer,
    AppliedControlImportExportSerializer,
    EvidenceImportExportSerializer,
    ProjectImportExportSerializer,
    RiskAssessmentImportExportSerializer,
    RiskScenarioImportExportSerializer,
    ComplianceAssessmentImportExportSerializer,
    RequirementAssessmentImportExportSerializer,
    VulnerabilityImportExportSerializer,
    ThreatImportExportSerializer,
    ReferenceControlImportExportSerializer,
    FrameworkImportExportSerializer,
    RiskMatrixImportExportSerializer,
)

from ebios_rm.serializers import (
    EbiosRMStudyImportExportSerializer,
    FearedEventImportExportSerializer,
    RoToImportExportSerializer,
    OperationalScenarioImportExportSerializer,
    StakeholderImportExportSerializer,
    StrategicScenarioImportExportSerializer,
    AttackPathImportExportSerializer,
)

from tprm.serializers import EntityImportExportSerializer

from library.serializers import LoadedLibraryImportExportSerializer

import structlog

logger = structlog.get_logger(__name__)


def get_all_objects():
    """
    Get all objects in the database.

    Returns:
    --------
    objects: list
        List of objects in the database.
    """
    objects = list()
    for app in django.apps.apps.get_app_configs():
        for model in app.get_models():
            objects.extend(model.objects.all())
    return objects


def dump_objects(queryset: Iterable[Model], path: str, format: str = "json"):
    """
    Dump objects to a file.

    Parameters:
    -----------
    queryset: Iterable[Model]
        Queryset of objects to dump.
    path: str
        Path to the file to dump to.
    format: str
        Format to dump to. Default is 'json'.
    """
    serialized_objects = serializers.serialize(format, queryset)
    if path == "-":
        print(serialized_objects)
    else:
        with open(path, "w") as outfile:
            outfile.write(serialized_objects)
    return path


def restore_objects(path: str, format: str = "json"):
    """
    Restore objects from a file.

    Parameters:
    -----------
    path: str
        Path to the file to restore from.
    format: str
        Format to restore from. Default is 'json'.
    """
    with open(path, "r") as infile:
        serialized_objects = infile.read()
    objects = serializers.deserialize(format, serialized_objects)
    for obj in objects:
        obj.save()
    return path


def app_dot_model(model: Model) -> str:
    """
    Get the app label and model name of a model.
    e.g. 'app_label.model_name'
    """
    content_type = ContentType.objects.get_for_model(model)
    return f"{content_type.app_label}.{content_type.model}"


def import_export_serializer_class(model: Model) -> serializers.Serializer:
    model_serializer_map = {
        Folder: FolderImportExportSerializer,
        Asset: AssetImportExportSerializer,
        AppliedControl: AppliedControlImportExportSerializer,
        Evidence: EvidenceImportExportSerializer,
        Project: ProjectImportExportSerializer,
        RiskAssessment: RiskAssessmentImportExportSerializer,
        RiskScenario: RiskScenarioImportExportSerializer,
        ComplianceAssessment: ComplianceAssessmentImportExportSerializer,
        RequirementAssessment: RequirementAssessmentImportExportSerializer,
        Vulnerability: VulnerabilityImportExportSerializer,
        Threat: ThreatImportExportSerializer,
        ReferenceControl: ReferenceControlImportExportSerializer,
        EbiosRMStudy: EbiosRMStudyImportExportSerializer,
        FearedEvent: FearedEventImportExportSerializer,
        RoTo: RoToImportExportSerializer,
        OperationalScenario: OperationalScenarioImportExportSerializer,
        Stakeholder: StakeholderImportExportSerializer,
        Entity: EntityImportExportSerializer,
        StrategicScenario: StrategicScenarioImportExportSerializer,
        AttackPath: AttackPathImportExportSerializer,
        Framework: FrameworkImportExportSerializer,
        RiskMatrix: RiskMatrixImportExportSerializer,
        LoadedLibrary: LoadedLibraryImportExportSerializer,
    }

    return model_serializer_map.get(model, None)


def get_model_dependencies(
    model: Type[models.Model], all_models: Set[Type[models.Model]]
) -> List[Type[models.Model]]:
    """
    Get all required dependencies for a model.

    Args:
        model: The model to analyze
        all_models: Set of models to consider as valid dependencies

    Returns:
        List of model classes that this model depends on
    """
    dependencies = []

    logger.debug("Getting model dependencies", model=model)
    for field in model._meta.get_fields():
        if not field.is_relation or field.related_model not in all_models:
            continue

        # Check if the relationship is required
        is_required = (
            isinstance(field, (models.ForeignKey, models.OneToOneField))
        ) or isinstance(field, models.ManyToManyField)

        if is_required:
            dependencies.append(field.related_model)

    return dependencies


def build_dependency_graph(
    models: List[Type[models.Model]],
) -> Dict[Type[models.Model], List[Type[models.Model]]]:
    """
    Build a dependency graph from a list of models.

    Args:
        models: List of model classes to analyze

    Returns:
        Dictionary mapping models to their dependencies
    """
    models_set = set(models + [Folder])
    graph = defaultdict(list)

    logger.debug("Building dependency graph", models=models)

    for model in models:
        dependencies = get_model_dependencies(model, models_set)

        logger.debug("Model dependencies", model=model, dependencies=dependencies)

        if dependencies:
            graph[model].extend(dependencies)

    logger.debug("Dependency graph", graph=graph)
    return graph


def topological_sort(
    graph: Dict[Type[models.Model], List[Type[models.Model]]],
) -> List[Type[models.Model]]:
    """
    Perform a topological sort with cycle detection.

    Args:
        graph: Dependency graph

    Returns:
        List of models in dependency order

    Raises:
        ValidationError: If a dependency cycle is detected
    """
    result = []
    permanent_marks = set()
    temporary_marks = set()

    def visit(node):
        if node in temporary_marks:
            cycle_path = " -> ".join(m.__name__ for m in temporary_marks)
            raise ValidationError(f"Circular dependency detected: {cycle_path}")

        if node not in permanent_marks:
            temporary_marks.add(node)

            for neighbor in graph.get(node, []):
                if neighbor == node:
                    continue
                visit(neighbor)

            temporary_marks.remove(node)
            permanent_marks.add(node)
            result.append(node)

    for node in graph:
        if node not in permanent_marks:
            visit(node)

    return result


def get_self_referencing_field(model: Type[models.Model]) -> Optional[str]:
    """
    Find self-referencing field in a model.

    Args:
        model: Model class to analyze

    Returns:
        Field name if found, None otherwise
    """
    return next(
        (
            field.field.name
            for field in model._meta.get_fields()
            if field.related_model == model
        ),
        None,
    )


def sort_objects_by_self_reference(
    objects: List[dict], self_ref_field: str
) -> List[dict]:
    """
    Sort objects by their hierarchical relationship when the self-referencing field
    can contain multiple parent IDs. Missing parents are ignored.

    Args:
        objects: List of object dictionaries.
        self_ref_field: Name of the self-referencing field, which may contain a single
                        parent ID or a list of parent IDs.

    Returns:
        List[dict]: Sorted list of objects.

    Raises:
        ValidationError: If circular references are detected.
    """
    object_map = {obj["id"]: obj for obj in objects}

    # Build dependency graph
    graph = defaultdict(list)
    roots = set(object_map.keys())

    for obj in objects:
        parent_ids = obj["fields"].get(self_ref_field, [])
        if isinstance(parent_ids, str) or isinstance(parent_ids, int):
            parent_ids = [parent_ids]  # Ensure it's a list

        for parent_id in parent_ids:
            if parent_id in object_map:
                graph[parent_id].append(obj["id"])
                roots.discard(obj["id"])  # Remove this ID from root candidates

    # Sort with cycle detection
    sorted_ids = []
    visited = set()
    temp_visited = set()

    def visit(obj_id):
        if obj_id in temp_visited:
            path = " -> ".join(str(id) for id in temp_visited)
            raise ValidationError(f"Circular reference detected: {path}")

        if obj_id not in visited:
            temp_visited.add(obj_id)

            for child_id in graph.get(obj_id, []):
                visit(child_id)

            temp_visited.remove(obj_id)
            visited.add(obj_id)
            sorted_ids.append(obj_id)

    # Process from roots
    for root_id in roots:
        visit(root_id)

    # Ensure all objects were processed
    if len(visited) != len(objects):
        raise ValidationError("Detected objects unreachable from root")

    return [object_map[obj_id] for obj_id in reversed(sorted_ids)]


def get_domain_export_objects(domain: Folder):
    folders = (
        Folder.objects.filter(
            Q(id=domain.id) | Q(id__in=[f.id for f in domain.get_sub_folders()])
        )
        .filter(content_type=Folder.ContentType.DOMAIN)
        .distinct()
    )
    projects = Project.objects.filter(folder__in=folders).distinct()

    risk_assessments = RiskAssessment.objects.filter(
        Q(project__in=projects) | Q(folder__in=folders)
    ).distinct()
    risk_scenarios = RiskScenario.objects.filter(
        risk_assessment__in=risk_assessments
    ).distinct()

    ebios_rm_studies = EbiosRMStudy.objects.filter(folder__in=folders).distinct()
    feared_events = FearedEvent.objects.filter(
        ebios_rm_study__in=ebios_rm_studies
    ).distinct()
    ro_tos = RoTo.objects.filter(ebios_rm_study__in=ebios_rm_studies).distinct()
    strategic_scenarios = StrategicScenario.objects.filter(
        ebios_rm_study__in=ebios_rm_studies
    ).distinct()
    attack_paths = AttackPath.objects.filter(
        ebios_rm_study__in=ebios_rm_studies
    ).distinct()
    operational_scenarios = OperationalScenario.objects.filter(
        ebios_rm_study__in=ebios_rm_studies
    ).distinct()
    stakeholders = Stakeholder.objects.filter(
        ebios_rm_study__in=ebios_rm_studies
    ).distinct()

    risk_matrices = RiskMatrix.objects.filter(
        Q(folder__in=folders)
        | Q(riskassessment__in=risk_assessments)
        | Q(ebios_rm_studies__in=ebios_rm_studies)
    ).distinct()

    compliance_assessments = ComplianceAssessment.objects.filter(
        Q(project__in=projects)
        | Q(folder__in=folders)
        | Q(ebios_rm_studies__in=ebios_rm_studies)
    ).distinct()
    requirement_assessments = RequirementAssessment.objects.filter(
        compliance_assessment__in=compliance_assessments
    ).distinct()
    frameworks = Framework.objects.filter(
        Q(folder__in=folders) | Q(complianceassessment__in=compliance_assessments)
    ).distinct()

    entities = Entity.objects.filter(
        Q(folder__in=folders)
        | Q(stakeholders__in=stakeholders)
        | Q(ebios_rm_studies__in=ebios_rm_studies)
    ).distinct()

    assets = Asset.objects.filter(
        Q(folder__in=folders)
        | Q(risk_scenarios__in=risk_scenarios)
        | Q(ebios_rm_studies__in=ebios_rm_studies)
        | Q(feared_events__in=feared_events)
    ).distinct()

    vulnerabilities = Vulnerability.objects.filter(
        Q(folder__in=folders) | Q(risk_scenarios__in=risk_scenarios)
    ).distinct()

    applied_controls = AppliedControl.objects.filter(
        Q(folder__in=folders)
        | Q(risk_scenarios__in=risk_scenarios)
        | Q(risk_scenarios_e__in=risk_scenarios)
        | Q(requirement_assessments__in=requirement_assessments)
        | Q(stakeholders__in=stakeholders)
        | Q(vulnerabilities__in=vulnerabilities)
    ).distinct()

    reference_controls = ReferenceControl.objects.filter(
        Q(folder__in=folders) | Q(appliedcontrol__in=applied_controls)
    ).distinct()

    threats = Threat.objects.filter(
        Q(folder__in=folders)
        | Q(risk_scenarios__in=risk_scenarios)
        | Q(operational_scenarios__in=operational_scenarios)
    ).distinct()

    evidences = Evidence.objects.filter(
        Q(folder__in=folders)
        | Q(applied_controls__in=applied_controls)
        | Q(requirement_assessments__in=requirement_assessments)
    ).distinct()

    loaded_libraries = LoadedLibrary.objects.filter(
        Q(folder__in=folders)
        | Q(threats__in=threats)
        | Q(reference_controls__in=reference_controls)
        | Q(risk_matrices__in=risk_matrices)
        | Q(frameworks__in=frameworks)
    ).distinct()

    return {
        # "folder": folders,
        "loadedlibrary": loaded_libraries,
        "vulnerability": vulnerabilities,
        "framework": frameworks,
        "riskmatrix": risk_matrices,
        "referencecontrol": reference_controls,
        "threat": threats,
        "asset": assets,
        "appliedcontrol": applied_controls,
        "entity": entities,
        "evidence": evidences,
        "project": projects,
        "complianceassessment": compliance_assessments,
        "requirementassessment": requirement_assessments,
        "ebiosrmstudy": ebios_rm_studies,
        "riskassessment": risk_assessments,
        "riskscenario": risk_scenarios,
        "fearedevent": feared_events,
        "roto": ro_tos,
        "operationalscenario": operational_scenarios,
        "stakeholder": stakeholders,
        "strategicscenario": strategic_scenarios,
        "attackpath": attack_paths,
    }
