from uuid import UUID
from core.models import *
from core.models import *
from iam.models import *
from library.utils import *
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def root_folder_fixture():
    Folder.objects.create(
                name="Global", content_type=Folder.ContentType.ROOT, builtin=True)

@pytest.fixture
def matrix_fixture():
    Folder.objects.create(
                name="Global", content_type=Folder.ContentType.ROOT, builtin=True)
    import_library(get_library('Critical matrix 5x5'))


@pytest.mark.django_db
class TestAnalysis:
    pytestmark = pytest.mark.django_db

    def test_analysis_parameters(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.create(name="test matrix", description="test matrix description", json_definition="{}", folder=folder)
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)

        assert analysis.name == "test analysis"
        assert analysis.description == "test analysis description"
        assert analysis.project == Project.objects.get(name="test project")
        assert analysis.rating_matrix == RiskMatrix.objects.get(name="test matrix")

    def test_analysis_get_scenario_count_null_when_no_scenario_inside_analysis(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.create(name="test matrix", description="test matrix description", json_definition="{}", folder=folder)
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)

        assert analysis.get_scenario_count() == 0

    @pytest.mark.usefixtures("matrix_fixture")
    def test_analysis_get_scenario_count_one_when_one_scenario_inside_analysis(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)

        assert analysis.get_scenario_count() == 1

    @pytest.mark.usefixtures("matrix_fixture")
    def test_analysis_get_scenario_count_is_decremented_when_child_scenario_is_deleted(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)

        assert analysis.get_scenario_count() == 1

        scenario.delete()

        assert analysis.get_scenario_count() == 0

    @pytest.mark.usefixtures("matrix_fixture")
    def test_analysis_get_scenario_count_is_incremented_when_child_scenario_is_created(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)

        assert analysis.get_scenario_count() == 0

        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)

        assert analysis.get_scenario_count() == 1
        
    def test_analysis_id_is_of_type_uuid(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.create(name="test matrix", description="test matrix description", json_definition="{}", folder=folder)
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)

        assert isinstance(analysis.id, UUID)

    def test_analysis_is_unique_in_project(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.create(name="test matrix", description="test matrix description", json_definition="{}", folder=folder)
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)

        with pytest.raises(ValidationError):
            Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)

    def test_analysis_can_have_same_name_but_different_version(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.create(name="test matrix", description="test matrix description", json_definition="{}", folder=folder)
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix, version=1)

        Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix, version=2)
    
    def test_analysis_can_have_same_name_and_version_in_a_different_project(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.create(name="test matrix", description="test matrix description", json_definition="{}", folder=folder)
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix, version=1)

        project2 = Project.objects.create(name="test project 2", folder=folder)
        Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project2, rating_matrix=matrix, version=1)

    def test_analysis_scope_is_analyses_in_project(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.create(name="test matrix", description="test matrix description", json_definition="{}", folder=folder)
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        analysis2 = Analysis.objects.create(name="test analysis 2", description="test analysis description",
                project=project, rating_matrix=matrix)
        analysis3 = Analysis.objects.create(name="test analysis 3", description="test analysis description",
                project=project, rating_matrix=matrix)

        project2 = Project.objects.create(name="test project 2", folder=folder)
        analysis4 = Analysis.objects.create(name="test analysis 4", description="test analysis description",
                project=project2, rating_matrix=matrix)
        analysis5 = Analysis.objects.create(name="test analysis 5", description="test analysis description",
                project=project2, rating_matrix=matrix)


        assert list(analysis.get_scope()) == [analysis, analysis2, analysis3]



@pytest.mark.django_db
class TestRiskScenario:
    pytestmark = pytest.mark.django_db

    @pytest.mark.usefixtures("matrix_fixture")
    def test_risk_scenario_parameters(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)

        assert scenario.name == "test scenario"
        assert scenario.description == "test scenario description"
        assert scenario.analysis == Analysis.objects.get(name="test analysis")
        assert scenario.threat == Threat.objects.get(name="test threat")

    @pytest.mark.usefixtures("matrix_fixture")
    def test_risk_scenario_parent_project(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)

        assert scenario.parent_project() == Project.objects.get(name="test project")

    @pytest.mark.usefixtures("matrix_fixture")
    def test_risk_scenario_is_deleted_when_analysis_is_deleted(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)

        queryset = RiskScenario.objects.filter(id=scenario.id)

        assert queryset.exists()

        analysis.delete()

        assert not queryset.exists()

    @pytest.mark.usefixtures("matrix_fixture")
    def test_risk_scenario_is_deleted_when_threat_is_deleted(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)

        queryset = RiskScenario.objects.filter(id=scenario.id)

        assert queryset.exists()

        threat.delete()

        assert not queryset.exists()

    @pytest.mark.usefixtures("matrix_fixture")
    def test_risk_scenario_id_is_of_type_uuid(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)

        assert isinstance(scenario.id, UUID)

    @pytest.mark.usefixtures("matrix_fixture")
    def test_risk_scenario_scope_is_scenarios_in_analysis(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)
        scenario2 = RiskScenario.objects.create(name="test scenario 2", description="test scenario description", analysis=analysis,
                threat=threat)
        scenario3 = RiskScenario.objects.create(name="test scenario 3", description="test scenario description", analysis=analysis,
                threat=threat)

        analysis2 = Analysis.objects.create(name="test analysis 2", description="test analysis description",
                project=project, rating_matrix=matrix)
        scenario4 = RiskScenario.objects.create(name="test scenario 4", description="test scenario description", analysis=analysis2,
                threat=threat)
        scenario5 = RiskScenario.objects.create(name="test scenario 5", description="test scenario description", analysis=analysis2,
                threat=threat)

        assert list(scenario.get_scope()) == [scenario, scenario2, scenario3]

    @pytest.mark.usefixtures("matrix_fixture")
    def test_risk_scenario_rid_is_deterministic(self):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)
        scenario2 = RiskScenario.objects.create(name="test scenario 2", description="test scenario description", analysis=analysis,
                threat=threat)
        scenario3 = RiskScenario.objects.create(name="test scenario 3", description="test scenario description", analysis=analysis,
                threat=threat)

        assert scenario.rid == "R.1"
        assert scenario2.rid == "R.2"
        assert scenario3.rid == "R.3"



@pytest.mark.django_db
class TestRiskMatrix:
    pytestmark = pytest.mark.django_db

    ...


@pytest.mark.django_db
class TestSecurityMeasure:
    pytestmark = pytest.mark.django_db

    ...


@pytest.mark.django_db
class TestRiskAcceptance:
    pytestmark = pytest.mark.django_db
    
    def test_acceptance_creation(self, matrix_fixture):
        folder = Folder.objects.create(name="test folder", description="test folder description")
        matrix = RiskMatrix.objects.all()[0]
        project = Project.objects.create(name="test project", folder=folder)
        analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                project=project, rating_matrix=matrix)
        threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
        scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                threat=threat)
        acceptance = RiskAcceptance.objects.create(name="test acceptance", description="test acceptance description", folder=folder)
        acceptance.risk_scenarios.add(scenario)
        acceptance.save()

        assert isinstance(acceptance.id, UUID)
        assert acceptance.name == "test acceptance"
        assert acceptance.description == "test acceptance description"
        assert acceptance.folder == folder
        assert acceptance.risk_scenarios.count() == 1
        assert acceptance.risk_scenarios.all()[0] == scenario

    def test_acceptance_creation_same_name_different_folder(self, matrix_fixture):
            folder = Folder.objects.create(name="test folder", description="test folder description")
            folder2 = Folder.objects.create(name="test folder 2", description="test folder description")
            matrix = RiskMatrix.objects.all()[0]
            project = Project.objects.create(name="test project", folder=folder)
            analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                    project=project, rating_matrix=matrix)
            threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
            scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                    threat=threat)
            acceptance = RiskAcceptance.objects.create(name="test acceptance", description="test acceptance description", folder=folder)
            acceptance.risk_scenarios.add(scenario)
            acceptance.save()

            acceptance2 = RiskAcceptance.objects.create(name="test acceptance", description="test acceptance description", folder=folder2)
            acceptance2.risk_scenarios.add(scenario)
            acceptance2.save()

            assert isinstance(acceptance2.id, UUID)
            assert acceptance2.name == "test acceptance"
            assert acceptance2.description == "test acceptance description"
            assert acceptance2.folder == folder2
            assert acceptance2.risk_scenarios.count() == 1
            assert acceptance2.risk_scenarios.all()[0] == scenario

    def test_acceptance_creation_same_name_same_folder(self, matrix_fixture):
            folder = Folder.objects.create(name="test folder", description="test folder description")
            matrix = RiskMatrix.objects.all()[0]
            project = Project.objects.create(name="test project", folder=folder)
            analysis = Analysis.objects.create(name="test analysis", description="test analysis description",
                    project=project, rating_matrix=matrix)
            threat = Threat.objects.create(name="test threat", description="test threat description", folder=folder)
            scenario = RiskScenario.objects.create(name="test scenario", description="test scenario description", analysis=analysis,
                    threat=threat)
            acceptance = RiskAcceptance.objects.create(name="test acceptance", description="test acceptance description", folder=folder)
            acceptance.risk_scenarios.add(scenario)
            acceptance.save()

            with pytest.raises(ValidationError):
                    acceptance2 = RiskAcceptance.objects.create(name="test acceptance", description="test acceptance description", folder=folder)
                    acceptance2.risk_scenarios.add(scenario)
                    acceptance2.save()



@pytest.mark.django_db
class TestAsset:
    pytestmark = pytest.mark.django_db

    def test_asset_creation(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        asset = Asset.objects.create(name="Asset", folder=root_folder)
        assert asset.name == "Asset"
        assert asset.folder == root_folder
        assert asset.type == Asset.Type.PRIMARY

    def test_asset_creation_same_name(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        Asset.objects.create(name="Asset", folder=root_folder)
        with pytest.raises(ValidationError):
            Asset.objects.create(name="Asset", folder=root_folder)

    def test_asset_creation_same_name_different_folder(self, root_folder_fixture):
        root_folder = Folder.objects.get(content_type=Folder.ContentType.ROOT)
        folder = Folder.objects.create(name="Parent", folder=root_folder)

        asset1 = Asset.objects.create(name="Asset", folder=root_folder)
        asset2 = Asset.objects.create(name="Asset", folder=folder)
        assert asset1.name == "Asset"
        assert asset2.name == "Asset"
        assert asset1.type == Asset.Type.PRIMARY
        assert asset2.type == Asset.Type.PRIMARY
        assert asset1.folder == root_folder
        assert asset2.folder == folder

# Note: no validation can be done at model level for m2m fields. This is done at form level.