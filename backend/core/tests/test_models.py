from uuid import UUID
from django.core.exceptions import ValidationError

import pytest
from ciso_assistant.settings import BASE_DIR
from core.models import (
    Policy,
    Project,
    RiskAssessment,
    ComplianceAssessment,
    RiskScenario,
    RequirementNode,
    RequirementAssessment,
    AppliedControl,
    ReferenceControl,
    Evidence,
    RiskAcceptance,
    Asset,
    Threat,
    RiskMatrix,
    Library,
    Framework,
)
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from iam.models import Folder
from library.utils import import_library_view, get_library

User = get_user_model()

SAMPLE_640x480_JPG = BASE_DIR / "app_tests" / "sample_640x480.jpg"


@pytest.fixture
def domain_project_fixture():
    folder = Folder.objects.create(
        name="test folder", description="test folder description"
    )
    project = Project.objects.create(name="test project", folder=folder)
    return project


@pytest.fixture
def risk_matrix_fixture():
    library = get_library("urn:intuitem:risk:library:critical_risk_matrix_5x5")
    assert library is not None
    import_library_view(library)


@pytest.mark.django_db
class TestEvidence:
    pytestmark = pytest.mark.django_db

    def test_evidence_parameters(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        applied_control = AppliedControl.objects.create(
            name="test applied control",
            description="test applied control description",
            folder=folder,
        )
        with open(SAMPLE_640x480_JPG, "rb") as f:
            evidence = Evidence.objects.create(
                name="test evidence",
                description="test evidence description",
                attachment=SimpleUploadedFile(SAMPLE_640x480_JPG.name, f.read()),
                folder=folder,
            )
            evidence.applied_controls.add(applied_control)  # pyright: ignore[reportAttributeAccessIssue]

        assert evidence.name == "test evidence"
        assert evidence.description == "test evidence description"
        assert list(evidence.applied_controls.all()) == [applied_control]  # pyright: ignore[reportAttributeAccessIssue]
        assert evidence.attachment.name.startswith(
            SAMPLE_640x480_JPG.name.split(".")[0]
        )
        assert evidence.attachment.name.endswith(".jpg")
        assert evidence.attachment.size == 106_201

    def test_evidence_with_no_attachment(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        applied_control = AppliedControl.objects.create(
            name="test applied control",
            description="test applied control description",
            folder=folder,
        )
        evidence = Evidence.objects.create(
            folder=folder,
            name="test evidence",
            description="test evidence description",
        )
        evidence.applied_controls.add(applied_control)  # pyright: ignore[reportAttributeAccessIssue]
        assert not evidence.attachment


@pytest.mark.django_db
class TestRiskAssessment:
    pytestmark = pytest.mark.django_db

    def test_risk_assessment_parameters(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.create(
            name="test risk matrix",
            description="test risk matrix description",
            json_definition="{}",
            folder=folder,
        )
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )

        assert risk_assessment.name == "test risk_assessment"
        assert risk_assessment.description == "test risk_assessment description"
        assert risk_assessment.project == Project.objects.get(name="test project")
        assert risk_assessment.risk_matrix == RiskMatrix.objects.get(
            name="test risk matrix"
        )

    def test_risk_assessment_get_scenario_count_null_when_no_scenario_inside_risk_assessment(
        self,
    ):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.create(
            name="test risk matrix",
            description="test risk matrix description",
            json_definition="{}",
            folder=folder,
        )
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )

        assert risk_assessment.get_scenario_count() == 0

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_assessment_get_scenario_count_one_when_one_scenario_inside_risk_assessment(
        self,
    ):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )

        assert risk_assessment.get_scenario_count() == 1

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_assessment_get_scenario_count_is_decremented_when_child_scenario_is_deleted(
        self,
    ):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )

        assert risk_assessment.get_scenario_count() == 1

        scenario.delete()

        assert risk_assessment.get_scenario_count() == 0

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_assessment_get_scenario_count_is_incremented_when_child_scenario_is_created(
        self,
    ):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )

        assert risk_assessment.get_scenario_count() == 0

        RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )

        assert risk_assessment.get_scenario_count() == 1

    def test_risk_assessment_id_is_of_type_uuid(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.create(
            name="test risk matrix",
            description="test risk matrix description",
            json_definition="{}",
            folder=folder,
        )
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )

        assert isinstance(risk_assessment.id, UUID)

    def test_risk_assessment_is_unique_in_project(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.create(
            name="test risk matrix",
            description="test risk matrix description",
            json_definition="{}",
            folder=folder,
        )
        project = Project.objects.create(name="test project", folder=folder)
        RiskAssessment.objects.create(
            name="test risk assessment",
            description="test risk assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        with pytest.raises(ValidationError):
            RiskAssessment.objects.create(
                name="test risk assessment",
                description="test risk assessment description",
                project=project,
                risk_matrix=risk_matrix,
            )

    def test_risk_assessment_can_have_same_name_but_different_version(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.create(
            name="test risk matrix",
            description="test risk matrix description",
            json_definition="{}",
            folder=folder,
        )
        project = Project.objects.create(name="test project", folder=folder)
        RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
            version="1",
        )
        RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
            version="2",
        )

    def test_risk_assessment_can_have_same_name_and_version_in_a_different_project(
        self,
    ):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.create(
            name="test risk matrix",
            description="test risk matrix description",
            json_definition="{}",
            folder=folder,
        )
        project = Project.objects.create(name="test project", folder=folder)
        RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
            version="1",
        )

        project2 = Project.objects.create(name="test project 2", folder=folder)
        RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project2,
            risk_matrix=risk_matrix,
            version="1",
        )

    def test_risk_assessment_scope_is_risk_assessments_in_project(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.create(
            name="test risk matrix",
            description="test risk matrix description",
            json_definition="{}",
            folder=folder,
        )
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        risk_assessment2 = RiskAssessment.objects.create(
            name="test risk_assessment 2",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        risk_assessment3 = RiskAssessment.objects.create(
            name="test risk_assessment 3",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )

        project2 = Project.objects.create(name="test project 2", folder=folder)
        RiskAssessment.objects.create(
            name="test risk_assessment 4",
            description="test risk_assessment description",
            project=project2,
            risk_matrix=risk_matrix,
        )
        RiskAssessment.objects.create(
            name="test risk_assessment 5",
            description="test risk_assessment description",
            project=project2,
            risk_matrix=risk_matrix,
        )

        assert list(risk_assessment.get_scope()) == [
            risk_assessment,
            risk_assessment2,
            risk_assessment3,
        ]


@pytest.mark.django_db
class TestRiskScenario:
    pytestmark = pytest.mark.django_db

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_scenario_parameters(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        threat = Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )
        scenario.threats.add(threat)

        assert scenario.name == "test scenario"
        assert scenario.description == "test scenario description"
        assert scenario.risk_assessment == RiskAssessment.objects.get(
            name="test risk_assessment"
        )
        assert Threat.objects.get(name="test threat") in scenario.threats.all()

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_scenario_parent_project(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )

        assert scenario.parent_project() == Project.objects.get(name="test project")

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_scenario_is_deleted_when_risk_assessment_is_deleted(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )

        queryset = RiskScenario.objects.filter(id=scenario.id)

        assert queryset.exists()

        risk_assessment.delete()

        assert not queryset.exists()

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_scenario_is__not_deleted_when_threat_is_deleted(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        threat = Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )
        scenario.threats.add(threat)

        queryset = RiskScenario.objects.filter(id=scenario.id)

        assert queryset.exists()

        threat.delete()

        assert queryset.exists()

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_scenario_id_is_of_type_uuid(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )

        assert isinstance(scenario.id, UUID)

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_scenario_scope_is_scenarios_in_risk_assessment(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )
        scenario2 = RiskScenario.objects.create(
            name="test scenario 2",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )
        scenario3 = RiskScenario.objects.create(
            name="test scenario 3",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )

        risk_assessment2 = RiskAssessment.objects.create(
            name="test risk_assessment 2",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        RiskScenario.objects.create(
            name="test scenario 4",
            description="test scenario description",
            risk_assessment=risk_assessment2,
        )
        RiskScenario.objects.create(
            name="test scenario 5",
            description="test scenario description",
            risk_assessment=risk_assessment2,
        )

        assert list(scenario.get_scope()) == [scenario, scenario2, scenario3]

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_risk_scenario_rid_is_deterministic(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )
        scenario2 = RiskScenario.objects.create(
            name="test scenario 2",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )
        scenario3 = RiskScenario.objects.create(
            name="test scenario 3",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )

        assert scenario.rid == "R.1"
        assert scenario2.rid == "R.2"
        assert scenario3.rid == "R.3"


@pytest.mark.django_db
class TestRiskMatrix:
    pytestmark = pytest.mark.django_db

    ...


@pytest.mark.django_db
class TestAppliedControl:
    pytestmark = pytest.mark.django_db

    def test_measure_creation(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        measure = AppliedControl.objects.create(name="Measure", folder=root_folder)
        assert measure.name == "Measure"
        assert measure.folder == root_folder

    def test_measure_creation_same_name(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        AppliedControl.objects.create(name="Measure", folder=root_folder)
        with pytest.raises(ValidationError):
            AppliedControl.objects.create(name="Measure", folder=root_folder)

    def test_measure_creation_same_name_different_folder(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(name="Parent", folder=root_folder)
        measure1 = AppliedControl.objects.create(name="Measure", folder=root_folder)
        measure2 = AppliedControl.objects.create(name="Measure", folder=folder)
        assert measure1.name == "Measure"
        assert measure2.name == "Measure"
        assert measure1.folder == root_folder
        assert measure2.folder == folder

    def test_measure_category_inherited_from_function(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(name="Parent", folder=root_folder)
        function = ReferenceControl.objects.create(
            name="Function", folder=root_folder, category="technical"
        )
        measure = AppliedControl.objects.create(
            name="Measure", folder=folder, reference_control=function
        )
        assert measure.category == "technical"


@pytest.mark.django_db
class TestPolicy:
    pytestmark = pytest.mark.django_db

    def test_policy_creation(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        policy = Policy.objects.create(name="Policy", folder=root_folder)
        assert Policy.objects.count() == 1
        assert AppliedControl.objects.count() == 1
        assert policy.name == "Policy"
        assert policy.folder == root_folder
        assert policy.category == "policy"

    def test_policy_does_not_inherit_category_from_reference_control(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(name="Parent", folder=root_folder)
        function = ReferenceControl.objects.create(
            name="Function", folder=root_folder, category="technical"
        )
        policy = Policy.objects.create(
            name="Policy", folder=folder, reference_control=function
        )
        assert policy.category == "policy"

    def test_policy_creation_same_name(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        Policy.objects.create(name="Policy", folder=root_folder)
        with pytest.raises(ValidationError):
            Policy.objects.create(name="Policy", folder=root_folder)

    def test_policy_creation_same_name_different_folder(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(name="Parent", folder=root_folder)
        policy1 = Policy.objects.create(name="Policy", folder=root_folder)
        policy2 = Policy.objects.create(name="Policy", folder=folder)
        assert policy1.name == "Policy"
        assert policy2.name == "Policy"
        assert policy1.folder == root_folder
        assert policy2.folder == folder


@pytest.mark.django_db
class TestRiskAcceptance:
    pytestmark = pytest.mark.django_db

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_acceptance_creation(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )
        acceptance = RiskAcceptance.objects.create(
            name="test acceptance",
            description="test acceptance description",
            folder=folder,
        )
        acceptance.risk_scenarios.add(scenario)
        acceptance.save()

        assert isinstance(acceptance.id, UUID)
        assert acceptance.name == "test acceptance"
        assert acceptance.description == "test acceptance description"
        assert acceptance.folder == folder
        assert acceptance.risk_scenarios.count() == 1
        assert acceptance.risk_scenarios.all()[0] == scenario

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_acceptance_creation_same_name_different_folder(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        folder2 = Folder.objects.create(
            name="test folder 2", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )
        acceptance = RiskAcceptance.objects.create(
            name="test acceptance",
            description="test acceptance description",
            folder=folder,
        )
        acceptance.risk_scenarios.add(scenario)
        acceptance.save()

        acceptance2 = RiskAcceptance.objects.create(
            name="test acceptance",
            description="test acceptance description",
            folder=folder2,
        )
        acceptance2.risk_scenarios.add(scenario)
        acceptance2.save()

        assert isinstance(acceptance2.id, UUID)
        assert acceptance2.name == "test acceptance"
        assert acceptance2.description == "test acceptance description"
        assert acceptance2.folder == folder2
        assert acceptance2.risk_scenarios.count() == 1
        assert acceptance2.risk_scenarios.all()[0] == scenario

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_acceptance_creation_same_name_same_folder(self):
        folder = Folder.objects.create(
            name="test folder", description="test folder description"
        )
        risk_matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        risk_assessment = RiskAssessment.objects.create(
            name="test risk_assessment",
            description="test risk_assessment description",
            project=project,
            risk_matrix=risk_matrix,
        )
        Threat.objects.create(
            name="test threat", description="test threat description", folder=folder
        )
        scenario = RiskScenario.objects.create(
            name="test scenario",
            description="test scenario description",
            risk_assessment=risk_assessment,
        )
        acceptance = RiskAcceptance.objects.create(
            name="test acceptance",
            description="test acceptance description",
            folder=folder,
        )
        acceptance.risk_scenarios.add(scenario)
        acceptance.save()

        with pytest.raises(ValidationError):
            acceptance2 = RiskAcceptance.objects.create(
                name="test acceptance",
                description="test acceptance description",
                folder=folder,
            )
            acceptance2.risk_scenarios.add(scenario)
            acceptance2.save()


@pytest.mark.django_db
class TestAsset:
    pytestmark = pytest.mark.django_db

    def test_asset_creation(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        asset = Asset.objects.create(name="Asset", folder=root_folder)
        assert asset.name == "Asset"
        assert asset.folder == root_folder
        assert asset.type == Asset.Type.SUPPORT

    def test_asset_creation_same_name(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        Asset.objects.create(name="Asset", folder=root_folder)
        with pytest.raises(ValidationError):
            Asset.objects.create(name="Asset", folder=root_folder)

    def test_asset_creation_same_name_different_folder(self):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(name="Parent", folder=root_folder)

        asset1 = Asset.objects.create(name="Asset", folder=root_folder)
        asset2 = Asset.objects.create(name="Asset", folder=folder)
        assert asset1.name == "Asset"
        assert asset2.name == "Asset"
        assert asset1.type == Asset.Type.SUPPORT
        assert asset2.type == Asset.Type.SUPPORT
        assert asset1.folder == root_folder
        assert asset2.folder == folder


@pytest.mark.django_db
class TestLibrary:
    pytestmark = pytest.mark.django_db

    def test_library_creation(self):
        library = Library.objects.create(
            name="Library",
            description="Library description",
            folder=Folder.get_root_folder(),
            locale="en",
            version=1,
        )
        assert library.name == "Library"
        assert library.description == "Library description"
        assert library.locale == "en"
        assert library.version == 1
        assert library.folder == Folder.get_root_folder()

    def test_library_reference_count_zero_if_unused(self):
        library = Library.objects.create(
            name="Library",
            description="Library description",
            folder=Folder.get_root_folder(),
            locale="en",
            version=1,
        )
        assert library.reference_count == 0

    @pytest.mark.usefixtures("domain_project_fixture")
    def test_library_reference_count_incremented_when_framework_is_referenced_by_compliance_assessment_and_decremented_when_compliance_assessment_is_deleted(
        self,
    ):
        library = Library.objects.create(
            name="Library",
            description="Library description",
            folder=Folder.get_root_folder(),
            locale="en",
            version=1,
        )
        framework = Framework.objects.create(
            name="Framework",
            description="Framework description",
            folder=Folder.get_root_folder(),
            library=library,
        )

        assert library.reference_count == 0

        compliance_assessment = ComplianceAssessment.objects.create(
            name="ComplianceAssessment",
            description="ComplianceAssessment description",
            project=Project.objects.last(),
            framework=framework,
        )

        assert library.reference_count == 1

        compliance_assessment.delete()

        assert library.reference_count == 0

    @pytest.mark.usefixtures("domain_project_fixture")
    def test_library_reference_count_incremented_when_reference_control_is_referenced_by_complance_assessment_and_decremented_when_compliance_assessment_is_deleted(
        self,
    ):
        library = Library.objects.create(
            name="Library",
            description="Library description",
            folder=Folder.get_root_folder(),
            locale="en",
            version=1,
        )
        framework = Framework.objects.create(
            name="Framework",
            description="Framework description",
            folder=Folder.get_root_folder(),
            library=library,
        )
        requirement_node = RequirementNode.objects.create(
            name="RequirementNode",
            description="RequirementNode description",
            folder=Folder.get_root_folder(),
            framework=framework,
            assessable=True,
        )
        assert library.reference_count == 0
        compliance_assessment = ComplianceAssessment.objects.create(
            name="ComplianceAssessment",
            description="ComplianceAssessment description",
            project=Project.objects.last(),
            framework=framework,
        )

        requirement_assessment = RequirementAssessment.objects.create(
            requirement=requirement_node,
            compliance_assessment=compliance_assessment,
            folder=Folder.get_root_folder(),
        )

        reference_control = ReferenceControl.objects.create(
            name="ReferenceControl",
            description="ReferenceControl description",
            folder=Folder.get_root_folder(),
            library=library,
        )
        applied_control = AppliedControl.objects.create(
            name="AppliedControl",
            description="AppliedControl description",
            folder=Folder.get_root_folder(),
            reference_control=reference_control,
        )

        requirement_assessment.applied_controls.add(applied_control)

        assert library.reference_count == 1
        compliance_assessment.delete()
        assert library.reference_count == 0

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_library_reference_count_incremented_when_risk_matrix_is_referenced_by_risk_assessment_and_decremented_when_risk_assessment_is_deleted(
        self,
    ):
        domain = Folder.objects.create(name="Domain", description="Domain description")
        project = Project.objects.create(name="Project", folder=domain)

        library = Library.objects.get()
        risk_matrix = RiskMatrix.objects.get()

        assert library.reference_count == 0

        risk_assessment = RiskAssessment.objects.create(
            name="RiskAssessment",
            description="RiskAssessment description",
            project=project,
            risk_matrix=risk_matrix,
        )

        assert library.reference_count == 1

        risk_assessment.delete()

        assert library.reference_count == 0

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_library_reference_count_incremented_when_threat_is_referenced_by_risk_scenario_and_decremented_when_risk_scenario_is_deleted(
        self,
    ):
        domain = Folder.objects.create(name="Domain", description="Domain description")
        project = Project.objects.create(name="Project", folder=domain)

        risk_matrix = RiskMatrix.objects.get()

        library = Library.objects.create(
            name="Library",
            description="Library description",
            folder=Folder.get_root_folder(),
            locale="en",
            version=1,
        )
        threat = Threat.objects.create(
            name="Threat",
            description="Threat description",
            folder=Folder.get_root_folder(),
            library=library,
        )

        risk_assessment = RiskAssessment.objects.create(
            name="RiskAssessment",
            description="RiskAssessment description",
            project=project,
            risk_matrix=risk_matrix,
        )

        assert library.reference_count == 0

        risk_scenario = RiskScenario.objects.create(
            name="RiskScenario",
            description="RiskScenario description",
            risk_assessment=risk_assessment,
        )
        risk_scenario.threats.add(threat)

        assert library.reference_count == 1

        risk_scenario.delete()

        assert library.reference_count == 0

    @pytest.mark.usefixtures("risk_matrix_fixture")
    def test_library_reference_count_incremented_when_reference_control_is_referenced_by_risk_scenario_and_decremented_when_risk_scenario_is_deleted(
        self,
    ):
        domain = Folder.objects.create(name="Domain", description="Domain description")
        project = Project.objects.create(name="Project", folder=domain)

        risk_matrix = RiskMatrix.objects.get()

        library = Library.objects.create(
            name="Library",
            description="Library description",
            folder=Folder.get_root_folder(),
            locale="en",
            version=1,
        )
        reference_control = ReferenceControl.objects.create(
            name="ReferenceControl",
            description="ReferenceControl description",
            folder=Folder.get_root_folder(),
            library=library,
        )
        applied_control = AppliedControl.objects.create(
            name="AppliedControl",
            description="AppliedControl description",
            folder=Folder.get_root_folder(),
            reference_control=reference_control,
        )

        risk_assessment = RiskAssessment.objects.create(
            name="RiskAssessment",
            description="RiskAssessment description",
            project=project,
            risk_matrix=risk_matrix,
        )

        assert library.reference_count == 0

        risk_scenario = RiskScenario.objects.create(
            name="RiskScenario",
            description="RiskScenario description",
            risk_assessment=risk_assessment,
        )
        risk_scenario.applied_controls.add(applied_control)

        assert library.reference_count == 1

        risk_scenario.delete()

        assert library.reference_count == 0

    @pytest.mark.usefixtures("domain_project_fixture")
    def test_library_reference_count_must_be_zero_for_library_deletion(
        self,
    ):
        library = Library.objects.create(
            name="Library",
            description="Library description",
            folder=Folder.get_root_folder(),
            locale="en",
            version=1,
        )
        framework = Framework.objects.create(
            name="Framework",
            description="Framework description",
            folder=Folder.get_root_folder(),
            library=library,
        )
        compliance_assessment = ComplianceAssessment.objects.create(
            name="ComplianceAssessment",
            description="ComplianceAssessment description",
            project=Project.objects.last(),
            framework=framework,
        )

        assert library.reference_count == 1

        with pytest.raises(ValueError):
            library.delete()

        compliance_assessment.delete()

        assert library.reference_count == 0

        library.delete()

        assert Library.objects.count() == 0

    @pytest.mark.usefixtures("domain_project_fixture")
    def test_library_cannot_be_deleted_if_it_is_a_dependency_of_other_libraries(self):
        dependency_library = Library.objects.create(
            name="Dependency Library",
            description="Dependency Library description",
            folder=Folder.get_root_folder(),
            locale="en",
            version=1,
        )
        library = Library.objects.create(
            name="Library",
            description="Library description",
            folder=Folder.get_root_folder(),
            locale="en",
            version=1,
        )
        library.dependencies.add(dependency_library)

        with pytest.raises(ValueError):
            dependency_library.delete()

        library.delete()
        assert Library.objects.count() == 1

        dependency_library.delete()
        assert Library.objects.count() == 0
