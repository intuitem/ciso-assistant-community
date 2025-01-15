from typing import Iterable

import django.apps
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from django.db.models import Model, Q
from django.db.models.deletion import Collector

from iam.models import Folder

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
        Framework: FrameworkImportExportSerializer,
        RiskMatrix: RiskMatrixImportExportSerializer,
        LoadedLibrary: LoadedLibraryImportExportSerializer,
    }

    return model_serializer_map.get(model, None)


def get_domain_export_objects(domain: Folder):
    folders = Folder.objects.filter(
        Q(id=domain.id) | Q(id__in=[f.id for f in domain.get_sub_folders()])
    ).distinct()

    projects = Project.objects.filter(folder__in=folders).distinct()

    risk_assessments = RiskAssessment.objects.filter(
        Q(project__in=projects) | Q(folder__in=folders)
    ).distinct()
    risk_scenarios = RiskScenario.objects.filter(
        risk_assessment__in=risk_assessments
    ).distinct()

    ebios_rm_studies = EbiosRMStudy.objects.filter(
        folder__in=folders).distinct()
    feared_events = FearedEvent.objects.filter(
        ebios_rm_study__in=ebios_rm_studies
    ).distinct()
    ro_tos = RoTo.objects.filter(
        ebios_rm_study__in=ebios_rm_studies).distinct()
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
        "folder": folders,
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
