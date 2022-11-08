from uuid import UUID
from core.models import *
from back_office.models import *
from iam.models import *
from library.utils import *
from django.utils.translation import gettext as _
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def matrix_fixture():
    Folder.objects.create(
                name="Global", content_type=Folder.ContentType.ROOT, builtin=True)
    import_package(get_package('Critical matrix 5x5'))


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

    ...

