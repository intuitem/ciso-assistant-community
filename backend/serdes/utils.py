from typing import Iterable

import django.apps
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from django.db.models import Model
from django.db.models.deletion import Collector
from collections import defaultdict

from iam.models import Folder

from core.models import (
    Asset,
    AppliedControl,
    Evidence,
    Project,
    RiskAssessment,
    RiskScenario,
    ComplianceAssessment,
    RequirementAssessment,
    Vulnerability,
    Threat,
    ReferenceControl,
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


def get_objects_from_folder(folder: Folder) -> set:
    """
    Collates all objects in a folder.

    Parameters:
    -----------
    folder: Folder
        Folder to get objects from.

    Returns:
    --------
    objects: list
        List of objects in the folder.
    """
    objects = set()
    # NOTE: This is a hack to get all objects in a folder.
    #       As all objects contained in a folder are deleted
    #       when the folder is deleted, we can use the Django
    #       deletion collector to get all the objects in a folder.
    collector = Collector(using="default")
    collector.collect([folder])

    for model, model_instances in collector.data.items():
        objects.update(model_instances)

    return objects


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
    }

    return model_serializer_map.get(model, None)

def get_model_dependencies(model, all_models):
    """
    Retrieve the models that the given model depends on via required relationships.
    """
    dependencies = []
    for field in model._meta.get_fields():
        # Include only relations
        if field.is_relation and field.related_model in all_models:
            # Include only mandatory relationships
            if isinstance(field, models.ForeignKey) or isinstance(field, models.OneToOneField) or isinstance(field, models.ManyToManyField):
                dependencies.append(field.related_model)
    return dependencies

def build_dependency_graph(models):
    """
    Build a dependency graph from a list of models, considering only internal dependencies.
    """
    graph = defaultdict(list)
    for model in models:
        dependencies = get_model_dependencies(model, models)
        graph[model].extend(dependencies)
    return graph

def topological_sort(graph):
    """
    Perform a topological sort on the dependency graph.
    Return a list of models in the correct creation order.
    """
    visited = set()
    result = []

    def visit(node):
        if node not in visited:
            visited.add(node)
            for neighbor in graph[node]:
                visit(neighbor)
            result.append(node)

    for node in graph:
        visit(node)

    return result